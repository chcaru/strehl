//! Spatial repeated-structure inspection of independently reconstructed passes.
//! Published source identities and the common warp map bind the comparison;
//! correlation is not converted into a resolution or optimization score.
use crate::session_input::{ResolvedSession, SessionMode, SourceIdentity};
use anyhow::{Context, Result, ensure};
use clap::Args;
use rayon::prelude::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeSet,
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    path::{Path, PathBuf},
};
use strehl_core::reproducibility::{IndependentPair, Qualification, ReproducibilityWorkspace};

#[derive(Args, Clone, Debug)]
pub(crate) struct CompareArgs {
    /// Completed session render directory (or one of its layer directories).
    pub first: PathBuf,
    pub second: PathBuf,
    #[arg(long)]
    pub out_dir: PathBuf,
    /// Fourier patch side in sensor pixels: a power of two in 16..128.
    #[arg(long, default_value_t = 64)]
    pub patch_size: usize,
    #[arg(long, default_value_t = 4.0)]
    pub memory_limit_gib: f64,
    /// Independent patch workers; each patch retains the same reduction order.
    #[arg(long, default_value_t = 16)]
    pub threads: usize,
    /// Per-pass focus evidence directories, when available.
    #[arg(long)]
    pub focus_first: Option<PathBuf>,
    #[arg(long)]
    pub focus_second: Option<PathBuf>,
}

struct Input {
    root: PathBuf,
    directory: PathBuf,
    session: ResolvedSession,
    report: Value,
    alignment: Value,
    ids: Vec<SourceIdentity>,
    used: Vec<usize>,
}
fn read(path: &Path) -> Result<Value> {
    let file = File::open(path).with_context(|| format!("reading {}", path.display()))?;
    ensure!(
        file.metadata()?.len() <= 64 << 20,
        "diagnostic receipt exceeds 64MiB"
    );
    Ok(serde_json::from_reader(BufReader::new(file))?)
}
fn hash(path: &Path) -> Result<String> {
    let mut reader = BufReader::new(File::open(path)?);
    let mut hash = Sha256::new();
    let mut bytes = [0; 65536];
    loop {
        let n = reader.read(&mut bytes)?;
        if n == 0 {
            break;
        }
        hash.update(&bytes[..n]);
    }
    Ok(crate::session_input::hex(&hash.finalize()))
}

fn native_sensor_master_declared(report: &Value) -> Result<bool> {
    let Some(master) = report.get("native_sensor_master") else {
        return Ok(false);
    };
    ensure!(
        master["schema"] == "strehl.session-native-sensor-master.v1"
            && master["file"] == "sensor-master.tiff"
            && master["stage"] == "native-merge-before-demosaic"
            && master["cfa"] == "RGGB"
            && master["storage"] == "signed-f32"
            && master["reconstruction_applied"] == false,
        "unknown native sensor master contract"
    );
    Ok(true)
}

/// Seal files produced by one render before it can be called independent. The
/// session completion subsequently binds this receipt after the source recheck.
pub(crate) fn publish_render_binding(directory: &Path) -> Result<()> {
    let root = if directory.join("session.json").is_file() {
        directory
    } else {
        directory
            .parent()
            .context("render has no session directory")?
    };
    let (geometry_kind, geometry_file) = binding_geometry(root)?;
    let mut names = vec!["master.tiff", "photograph.tiff", "render-report.json"];
    if geometry_kind == "mosaic" {
        names.extend([
            "sensor-master.tiff",
            "coverage.tiff",
            "join-confidence.tiff",
            "view-owner.tiff",
            "mosaic-report.json",
        ]);
    } else {
        let native_sensor =
            native_sensor_master_declared(&read(&directory.join("render-report.json"))?)?;
        ensure!(
            native_sensor == directory.join("sensor-master.tiff").exists(),
            "native sensor master declaration and file differ"
        );
        if native_sensor {
            names.push("sensor-master.tiff");
        }
    }
    let mut files = serde_json::Map::new();
    for name in names {
        files.insert(name.into(), json!(hash(&directory.join(name))?));
    }
    let mut session_files = serde_json::Map::new();
    for name in ["session.json", "source-identities.json", geometry_file] {
        session_files.insert(name.into(), json!(hash(&root.join(name))?));
    }
    crate::session_cmd::write_json_new(
        &directory.join("render-completion.json"),
        &json!({"schema":"strehl.session-render-completion.v1","geometry_kind":geometry_kind,"files":files,"session_files":session_files}),
    )
}

fn binding_geometry(root: &Path) -> Result<(&'static str, &'static str)> {
    let session = read(&root.join("session.json"))?;
    let mode: SessionMode = serde_json::from_value(session["spec"]["mode"].clone())
        .context("render binding requires an explicit session mode")?;
    Ok(if mode == SessionMode::Mosaic {
        ("mosaic", "mosaic-geometry.json")
    } else {
        ("session-alignment", "alignment.json")
    })
}

pub(crate) fn completion_bindings(root: &Path) -> Result<Value> {
    let mut paths = vec![root.to_owned()];
    for entry in std::fs::read_dir(root)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            paths.push(entry.path());
        }
    }
    let mut bindings = serde_json::Map::new();
    for path in paths {
        let receipt = path.join("render-completion.json");
        if receipt.is_file() {
            let relative = if path == root {
                "render-completion.json".to_owned()
            } else {
                format!(
                    "{}/render-completion.json",
                    path.file_name()
                        .context("render directory has no name")?
                        .to_string_lossy()
                )
            };
            bindings.insert(relative, json!(hash(&receipt)?));
        }
    }
    ensure!(
        !bindings.is_empty(),
        "session has no bound rendered outputs"
    );
    Ok(Value::Object(bindings))
}

fn validate_render_binding(directory: &Path, root: &Path, require_completion: bool) -> Result<()> {
    let path = directory.join("render-completion.json");
    let receipt =
        read(&path).context("comparison requires output bindings; rerender this legacy result")?;
    ensure!(
        receipt["schema"] == "strehl.session-render-completion.v1",
        "unknown render binding schema"
    );
    let (geometry_kind, geometry_file) = binding_geometry(root)?;
    ensure!(
        receipt["geometry_kind"].as_str() == Some(geometry_kind)
            || (geometry_kind == "session-alignment" && receipt.get("geometry_kind").is_none()),
        "render geometry binding differs from session mode"
    );
    for name in ["master.tiff", "photograph.tiff", "render-report.json"] {
        ensure!(
            receipt["files"][name].as_str() == Some(hash(&directory.join(name))?.as_str()),
            "rendered output binding differs: {name}"
        );
    }
    let native_sensor = geometry_kind != "mosaic"
        && native_sensor_master_declared(&read(&directory.join("render-report.json"))?)?;
    ensure!(
        receipt["files"].as_object().is_some_and(|files| files.len()
            == if geometry_kind == "mosaic" {
                8
            } else if native_sensor {
                4
            } else {
                3
            }),
        "rendered output census differs"
    );
    ensure!(
        geometry_kind == "mosaic" || native_sensor == directory.join("sensor-master.tiff").exists(),
        "native sensor master declaration and file differ"
    );
    if native_sensor {
        ensure!(
            receipt["files"]["sensor-master.tiff"].as_str()
                == Some(hash(&directory.join("sensor-master.tiff"))?.as_str()),
            "rendered output binding differs: sensor-master.tiff"
        );
    }
    if geometry_kind == "mosaic" {
        for name in [
            "sensor-master.tiff",
            "coverage.tiff",
            "join-confidence.tiff",
            "view-owner.tiff",
            "mosaic-report.json",
        ] {
            ensure!(
                receipt["files"][name].as_str() == Some(hash(&directory.join(name))?.as_str()),
                "rendered mosaic binding differs: {name}"
            );
        }
    }
    for name in ["session.json", "source-identities.json", geometry_file] {
        ensure!(
            receipt["session_files"][name].as_str() == Some(hash(&root.join(name))?.as_str()),
            "rendered session binding differs: {name}"
        );
    }
    if require_completion {
        let relative = if directory == root {
            "render-completion.json".to_owned()
        } else {
            format!(
                "{}/render-completion.json",
                directory
                    .file_name()
                    .context("render directory has no name")?
                    .to_string_lossy()
            )
        };
        let completion = read(&root.join("completed.json"))?;
        ensure!(
            completion["render_bindings"][&relative].as_str() == Some(hash(&path)?.as_str()),
            "session completion does not bind this rendered output"
        );
    }
    Ok(())
}
fn input(directory: &Path, require_completion: bool) -> Result<Input> {
    let directory = directory.canonicalize()?;
    let root = if directory.join("session.json").is_file() {
        directory.clone()
    } else {
        directory
            .parent()
            .context("layer has no session")?
            .to_owned()
    };
    ensure!(
        !require_completion || root.join("completed.json").is_file(),
        "comparison requires completed session renders"
    );
    validate_render_binding(&directory, &root, require_completion)?;
    let session: ResolvedSession = serde_json::from_value(read(&root.join("session.json"))?)?;
    ensure!(
        session.spec.mode != SessionMode::Mosaic,
        "independent-pass comparison requires a common single-view canvas"
    );
    let ids: Vec<SourceIdentity> =
        serde_json::from_value(read(&root.join("source-identities.json"))?)?;
    ensure!(
        ids.len() == session.len(),
        "comparison source census differs"
    );
    ensure!(
        ids.iter()
            .zip(&session.frames)
            .all(|(id, frame)| id.path == frame.path
                && id.bytes == frame.bytes
                && id.modified_unix_nanos == frame.modified_unix_nanos),
        "comparison source order differs"
    );
    let report = read(&directory.join("render-report.json"))?;
    ensure!(
        report["invalid_output_pixels"].as_u64() == Some(0),
        "comparison needs covered independent-pass outputs"
    );
    let used = report["frames"]
        .as_array()
        .context("missing rendered acquisition list")?
        .iter()
        .map(|v| {
            v["frame"]
                .as_u64()
                .and_then(|v| usize::try_from(v).ok())
                .context("invalid rendered acquisition")
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        !used.is_empty() && used.iter().all(|&i| i < ids.len()),
        "rendered acquisition outside census"
    );
    let unique: BTreeSet<_> = used.iter().collect();
    ensure!(unique.len() == used.len(), "duplicate rendered acquisition");
    let alignment = read(&root.join("alignment.json"))?;
    Ok(Input {
        root,
        directory,
        session,
        report,
        alignment,
        ids,
        used,
    })
}
fn independent(a: &Input, b: &Input) -> Result<IndependentPair> {
    let aa: BTreeSet<_> = a.used.iter().map(|&i| &a.ids[i].sha256).collect();
    let bb: BTreeSet<_> = b.used.iter().map(|&i| &b.ids[i].sha256).collect();
    ensure!(
        aa.len() == a.used.len() && bb.len() == b.used.len() && aa.is_disjoint(&bb),
        "comparison repeats original acquisition content"
    );
    // Full hashes refuse repeated file content under the recorded acquisition
    // provenance. They cannot prove physical photon independence (e.g. copies
    // rewritten by another program); that limitation remains in the report.
    IndependentPair::new(
        &(0..aa.len() as u64).collect::<Vec<_>>(),
        &(aa.len() as u64..(aa.len() + bb.len()) as u64).collect::<Vec<_>>(),
    )
    .map_err(anyhow::Error::msg)
}
fn dimensions(path: &Path) -> Result<(u32, u32)> {
    Ok(tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?.dimensions()?)
}
fn focus(
    path: Option<&Path>,
    input: &Input,
    width: usize,
    height: usize,
) -> Result<Option<Vec<u8>>> {
    let Some(path) = path else {
        return Ok(None);
    };
    let report = read(&path.join("geometry.json"))?;
    ensure!(
        report["dimensions"] == json!([width / 2, height / 2])
            && report["origin_quad"]
                == json!([input.report["canvas"][0], input.report["canvas"][1]]),
        "focus map domain differs from compared photograph"
    );
    let root = read(
        &path
            .parent()
            .context("focus directory has no parent")?
            .join("focus-evidence.json"),
    )?;
    ensure!(
        root["alignment_binding"] == input.alignment["report"]["binding_sha256"],
        "focus map alignment differs"
    );
    let census: Vec<SourceIdentity> = serde_json::from_value(root["sources"].clone())?;
    ensure!(census == input.ids, "focus evidence source census differs");
    ensure!(
        root["session"] == serde_json::to_value(&input.session)?,
        "focus session differs"
    );
    validate_focus_mapping(&report, &input.session, &input.used)?;
    let receipt = report["files"]
        .as_array()
        .context("missing focus file receipts")?
        .iter()
        .find(|v| v["file"] == "usable.tiff")
        .context("missing focus support receipt")?;
    let map = path.join("usable.tiff");
    ensure!(
        receipt["sha256"].as_str() == Some(hash(&map)?.as_str()),
        "focus map hash differs"
    );
    let mut decoder = tiff::decoder::Decoder::new(BufReader::new(File::open(&map)?))?;
    ensure!(
        decoder.dimensions()? == ((width / 2) as u32, (height / 2) as u32),
        "focus map dimensions differ"
    );
    let tiff::decoder::DecodingResult::U8(values) = decoder.read_image()? else {
        anyhow::bail!("focus support must be Gray8")
    };
    ensure!(
        values.len() == width / 2 * (height / 2),
        "focus support samples differ"
    );
    Ok(Some(values))
}

fn validate_focus_mapping(
    report: &Value,
    session: &ResolvedSession,
    rendered: &[usize],
) -> Result<()> {
    let pass = report["pass"]
        .as_u64()
        .and_then(|v| usize::try_from(v).ok())
        .and_then(|v| session.passes.get(v))
        .context("focus pass outside session")?;
    let mapping = report["ordinal_mapping"]
        .as_array()
        .context("missing focus ordinal mapping")?;
    ensure!(
        mapping.len() == pass.global_range.len(),
        "focus mapping omits intended acquisitions"
    );
    // Refused/unplaced originals retain their ordinal and missing support. A
    // compacted mapping changes the meaning of every later focus coordinate.
    for (ordinal, global) in pass.global_range.clone().enumerate() {
        ensure!(
            mapping[ordinal]
                == json!({"ordinal":ordinal,"global_index":global,"acquisition":global}),
            "focus ordinal mapping differs from the complete intended pass"
        );
        ensure!(
            session
                .frames
                .get(global)
                .is_some_and(|f| f.global_index == global && f.pass_frame_index == ordinal),
            "focus pass source order differs"
        );
    }
    ensure!(
        !rendered.is_empty() && rendered.iter().all(|i| pass.global_range.contains(i)),
        "focus evidence belongs to another pass"
    );
    Ok(())
}
pub(crate) fn run(args: &CompareArgs) -> Result<()> {
    compare(args, true)
}
/// The session orchestrator owns both freshly rendered passes and publishes its
/// completion receipt only after this diagnostic and its source recheck finish.
pub(crate) fn compare_generated(args: &CompareArgs) -> Result<()> {
    compare(args, false)
}
fn compare(args: &CompareArgs, require_completion: bool) -> Result<()> {
    let stage_start = std::time::Instant::now();
    ensure!(
        (1..=256).contains(&args.threads),
        "comparison threads must be 1..256"
    );
    ensure!(
        args.memory_limit_gib.is_finite() && (1.0..=4096.0).contains(&args.memory_limit_gib),
        "invalid comparison memory budget"
    );
    let patch_bytes =
        ReproducibilityWorkspace::reservation_bytes(args.patch_size).map_err(anyhow::Error::msg)?;
    let a = input(&args.first, require_completion)?;
    let b = input(&args.second, require_completion)?;
    let input_binding_seconds = stage_start.elapsed().as_secs_f64();
    let pair = independent(&a, &b)?;
    ensure!(
        a.alignment["warpmap_sha256"].as_str().is_some()
            && a.alignment["warpmap_sha256"] == b.alignment["warpmap_sha256"],
        "comparison requires the same measured alignment gauge"
    );
    ensure!(
        a.report["canvas"] == b.report["canvas"],
        "comparison canvases differ"
    );
    let output = a.session.ensure_fresh_output(&args.out_dir)?;
    b.session.ensure_output_outside_sources(&output)?;
    let ma = a.directory.join("master.tiff");
    let mb = b.directory.join("master.tiff");
    let (width, height) = dimensions(&ma)?;
    ensure!(
        dimensions(&mb)? == (width, height),
        "comparison master dimensions differ"
    );
    let (width, height) = (width as usize, height as usize);
    let n = width
        .checked_mul(height)
        .context("comparison size overflow")?;
    let reserved = n
        .checked_mul(60)
        .and_then(|v| {
            v.checked_add(
                (patch_bytes + args.patch_size * args.patch_size * 9).checked_mul(args.threads)?,
            )
        })
        .and_then(|v| v.checked_add(64 << 20))
        .context("comparison memory overflow")?;
    ensure!(
        reserved as f64 <= args.memory_limit_gib * (1_u64 << 30) as f64,
        "comparison needs {:.2}GiB",
        reserved as f64 / (1_u64 << 30) as f64
    );
    let stage_start = std::time::Instant::now();
    let sources = [hash(&ma)?, hash(&mb)?];
    let pre_decode_hash_seconds = stage_start.elapsed().as_secs_f64();
    let stage_start = std::time::Instant::now();
    let first = strehl_edit::load_tiff(&ma)?;
    let second = strehl_edit::load_tiff(&mb)?;
    let master_decode_seconds = stage_start.elapsed().as_secs_f64();
    ensure!(
        first.origin == strehl_edit::ImageOrigin::SceneLinear
            && second.origin == strehl_edit::ImageOrigin::SceneLinear,
        "comparison requires scene-linear masters"
    );
    let stage_start = std::time::Instant::now();
    let fa = focus(args.focus_first.as_deref(), &a, width, height)?;
    let fb = focus(args.focus_second.as_deref(), &b, width, height)?;
    let focus_evidence_seconds = stage_start.elapsed().as_secs_f64();
    let side = args.patch_size;
    let cols = width / side;
    let rows = height / side;
    ensure!(
        cols > 0 && rows > 0,
        "comparison image is smaller than one patch"
    );
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(args.threads)
        .build()?;
    let compute_start = std::time::Instant::now();
    let evidence: Vec<_> = pool.install(|| {
        (0..rows * cols)
            .into_par_iter()
            .map_init(
                || {
                    (
                        ReproducibilityWorkspace::new(side, patch_bytes)
                            .expect("validated patch reservation"),
                        vec![0.; side * side],
                        vec![0.; side * side],
                        vec![true; side * side],
                    )
                },
                |(workspace, pa, pb, valid), index| -> Result<_> {
                    let (tx, ty) = (index % cols, index / cols);
                    let (x0, y0) = (tx * side, ty * side);
                    let mut focus_ok = fa.is_some() && fb.is_some();
                    for y in 0..side {
                        for x in 0..side {
                            let i = (y0 + y) * width + x0 + x;
                            let k = y * side + x;
                            let luma = |p: &[f32]| 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2];
                            pa[k] = luma(&first.pixels[i * 3..i * 3 + 3]);
                            pb[k] = luma(&second.pixels[i * 3..i * 3 + 3]);
                            let qi = ((y0 + y) / 2) * (width / 2) + (x0 + x) / 2;
                            focus_ok &= fa.as_ref().is_some_and(|v| v[qi] != 0)
                                && fb.as_ref().is_some_and(|v| v[qi] != 0);
                        }
                    }
                    workspace
                        .compare(pa, pb, valid, valid, focus_ok, &pair, [0.08, 0.4])
                        .map_err(anyhow::Error::msg)
                },
            )
            .collect::<Result<Vec<_>>>()
    })?;
    let compute_seconds = compute_start.elapsed().as_secs_f64();
    let publication_start = std::time::Instant::now();
    let mut tiles = Vec::new();
    let mut correlation = Vec::new();
    let mut disagreement = Vec::new();
    let mut amplitude = Vec::new();
    let mut qualified = Vec::new();
    for (index, evidence) in evidence.into_iter().enumerate() {
        let (tx, ty) = (index % cols, index / cols);
        let (x0, y0) = (tx * side, ty * side);
        correlation.push(evidence.band_correlation.unwrap_or(f32::NAN));
        disagreement.push(evidence.relative_rms_difference.unwrap_or(f32::NAN));
        amplitude.push(evidence.band_amplitude_ratio.unwrap_or(f32::NAN));
        qualified.push(match evidence.qualification {
            Qualification::Supported => 1,
            Qualification::MissingCoverage => 2,
            Qualification::FocusUnverified => 3,
            Qualification::NoStructure => 4,
        });
        let rings:Vec<_>=evidence.rings.iter().map(|r|json!({"frequency":r.frequency,"samples":r.samples,"power_first":r.power_a,"power_second":r.power_b,"correlation":r.correlation})).collect();
        tiles.push(json!({"tile":[tx,ty],"origin_sensor":[x0,y0],"qualification":qualified.last(),"band_correlation":evidence.band_correlation,"relative_rms_difference":evidence.relative_rms_difference,"band_amplitude_ratio":evidence.band_amplitude_ratio,"rings":rings}));
    }
    std::fs::create_dir_all(&output)?;
    let mut files = Vec::new();
    for (name, values) in [
        ("correlation", &correlation),
        ("relative-disagreement", &disagreement),
        ("amplitude-ratio", &amplitude),
    ] {
        let path = output.join(format!("{name}.tiff"));
        let mut writer = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&path)?,
        );
        tiff::encoder::TiffEncoder::new(&mut writer)?
            .write_image::<tiff::encoder::colortype::Gray32Float>(
                cols.try_into()?,
                rows.try_into()?,
                values,
            )?;
        writer.flush()?;
        writer.get_ref().sync_all()?;
        files.push(json!({"file":path.file_name().context("comparison filename missing")?.to_string_lossy(),"sha256":hash(&path)?}));
    }
    let path = output.join("qualification.tiff");
    let mut writer = BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)?,
    );
    tiff::encoder::TiffEncoder::new(&mut writer)?.write_image::<tiff::encoder::colortype::Gray8>(
        cols.try_into()?,
        rows.try_into()?,
        &qualified,
    )?;
    writer.flush()?;
    writer.get_ref().sync_all()?;
    drop(writer);
    files.push(json!({"file":"qualification.tiff","sha256":hash(&path)?}));
    let map_publication_seconds = publication_start.elapsed().as_secs_f64();
    let stage_start = std::time::Instant::now();
    ensure!(
        sources == [hash(&ma)?, hash(&mb)?],
        "comparison inputs changed during inspection"
    );
    let final_hash_seconds = stage_start.elapsed().as_secs_f64();
    let report = json!({"schema":"strehl.session-reproducibility.v1","first":a.directory,"second":b.directory,"source_sessions":[a.root,b.root],"master_sha256":sources,"warpmap_sha256":a.alignment["warpmap_sha256"],"canvas_quad":a.report["canvas"],"sensor_dimensions":[width,height],"tile_dimensions":[cols,rows],"tile_step_sensor":side,"patch_side_sensor":side,"frequency_band_cycles_per_sensor_pixel":[0.08,0.4],"independent_acquisitions":[a.used.len(),b.used.len()],"first_acquisition_hashes":a.used.iter().map(|&i|&a.ids[i].sha256).collect::<Vec<_>>(),"second_acquisition_hashes":b.used.iter().map(|&i|&b.ids[i].sha256).collect::<Vec<_>>(),"first_recipe":a.report["recipe"],"second_recipe":b.report["recipe"],"focus_evidence":[args.focus_first,args.focus_second],"qualification_codes":{"1":"both passes have an unambiguous interior focus peak","2":"missing coverage","3":"focus compatibility unverified","4":"no spectral structure"},"scope":"Descriptive repeated structure on scene-linear independently reconstructed passes. Distinct original-file content is checked under recorded acquisition provenance, not proof of physical photon independence. Shared processing, common blur and sensor fixed pattern can correlate without true detail. Focus peak shape does not prove surface correspondence. No noise calibration, resolution cutoff or tuning score is inferred.","boundary_policy":"Only complete nonoverlapping patches are measured; right and bottom remainder strips have no result.","memory_reserved_bytes":reserved,"algorithm_sha256":crate::session_input::hex(&Sha256::digest([include_bytes!("session-reproducibility.rs").as_slice(),include_bytes!("../../strehl-core/src/reproducibility.rs").as_slice()].concat())),"files":files,"tiles":tiles});
    let mut report = report;
    report["threads"] = json!(args.threads);
    report["patch_compute_seconds"] = json!(compute_seconds);
    report["stage_seconds"] = json!({"input_binding":input_binding_seconds,"pre_decode_hash":pre_decode_hash_seconds,
        "master_decode":master_decode_seconds,"focus_evidence":focus_evidence_seconds,"patch_compute":compute_seconds,
        "map_publication":map_publication_seconds,"final_hash":final_hash_seconds});
    let publication_start = std::time::Instant::now();
    crate::session_cmd::write_json_new(&output.join("reproducibility.json"), &report)?;
    let report_publication_seconds = publication_start.elapsed().as_secs_f64();
    crate::session_cmd::write_json_new(
        &output.join("completed.json"),
        &json!({"schema":"strehl.reproducibility-completion.v1","patches":tiles.len(),
            "report_publication_seconds":report_publication_seconds}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session_input::{PassSpec, SessionSpec};
    #[test]
    fn optional_native_master_is_typed_bound_and_backward_compatible() {
        let root = std::env::temp_dir().join(format!(
            "strehl-native-master-binding-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        std::fs::write(root.join("session.json"), r#"{"spec":{"mode":"repeat"}}"#).unwrap();
        for name in [
            "master.tiff",
            "photograph.tiff",
            "source-identities.json",
            "alignment.json",
        ] {
            std::fs::write(root.join(name), name).unwrap();
        }
        let write_report = |report: &Value| {
            std::fs::write(
                root.join("render-report.json"),
                serde_json::to_vec(report).unwrap(),
            )
            .unwrap();
        };
        let bind_completion = || {
            std::fs::write(
                root.join("completed.json"),
                serde_json::to_vec(&json!({"render_bindings":completion_bindings(&root).unwrap()}))
                    .unwrap(),
            )
            .unwrap();
        };
        write_report(&json!({}));
        publish_render_binding(&root).unwrap();
        bind_completion();
        validate_render_binding(&root, &root, true).unwrap();
        assert_eq!(
            read(&root.join("render-completion.json")).unwrap()["files"]
                .as_object()
                .unwrap()
                .len(),
            3
        );
        std::fs::remove_file(root.join("render-completion.json")).unwrap();
        let typed = json!({"native_sensor_master":{
            "schema":"strehl.session-native-sensor-master.v1", "file":"sensor-master.tiff",
            "stage":"native-merge-before-demosaic", "cfa":"RGGB", "storage":"signed-f32",
            "reconstruction_applied":false
        }});
        write_report(&typed);
        assert!(publish_render_binding(&root).is_err()); // Declared but missing.
        std::fs::write(root.join("sensor-master.tiff"), "signed-native-sites").unwrap();
        publish_render_binding(&root).unwrap();
        bind_completion();
        validate_render_binding(&root, &root, true).unwrap();
        let receipt = read(&root.join("render-completion.json")).unwrap();
        assert_eq!(receipt["files"].as_object().unwrap().len(), 4);
        std::fs::write(root.join("sensor-master.tiff"), "changed").unwrap();
        assert!(
            validate_render_binding(&root, &root, true)
                .unwrap_err()
                .to_string()
                .contains("sensor-master.tiff")
        );
        std::fs::write(root.join("sensor-master.tiff"), "signed-native-sites").unwrap();
        let mut unbound = receipt.clone();
        unbound["files"]
            .as_object_mut()
            .unwrap()
            .remove("sensor-master.tiff");
        std::fs::write(
            root.join("render-completion.json"),
            serde_json::to_vec(&unbound).unwrap(),
        )
        .unwrap();
        bind_completion();
        assert!(
            validate_render_binding(&root, &root, true)
                .unwrap_err()
                .to_string()
                .contains("census")
        );
        write_report(&json!({}));
        let mut unexpected = receipt.clone();
        unexpected["files"]["render-report.json"] =
            json!(hash(&root.join("render-report.json")).unwrap());
        std::fs::write(
            root.join("render-completion.json"),
            serde_json::to_vec(&unexpected).unwrap(),
        )
        .unwrap();
        bind_completion();
        assert!(
            validate_render_binding(&root, &root, true)
                .unwrap_err()
                .to_string()
                .contains("census")
        );
        for field in [
            "schema",
            "file",
            "stage",
            "cfa",
            "storage",
            "reconstruction_applied",
        ] {
            let mut invalid = typed.clone();
            invalid["native_sensor_master"][field] = json!("wrong");
            assert!(native_sensor_master_declared(&invalid).is_err(), "{field}");
        }
        assert!(native_sensor_master_declared(&json!({"native_sensor_master":null})).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn session_mosaic_binding_seals_geometry_and_visibility_without_ordinary_alignment() {
        let root = std::env::temp_dir().join(format!(
            "strehl-mosaic-binding-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        crate::session_cmd::write_json_new(
            &root.join("session.json"),
            &json!({"spec":{"mode":"mosaic"}}),
        )
        .unwrap();
        for name in [
            "master.tiff",
            "photograph.tiff",
            "render-report.json",
            "sensor-master.tiff",
            "coverage.tiff",
            "join-confidence.tiff",
            "view-owner.tiff",
            "mosaic-report.json",
            "source-identities.json",
            "mosaic-geometry.json",
        ] {
            std::fs::write(root.join(name), name).unwrap();
        }
        publish_render_binding(&root).unwrap();
        let bindings = completion_bindings(&root).unwrap();
        crate::session_cmd::write_json_new(
            &root.join("completed.json"),
            &json!({"render_bindings":bindings}),
        )
        .unwrap();
        validate_render_binding(&root, &root, true).unwrap();
        assert!(!root.join("alignment.json").exists());
        let receipt = read(&root.join("render-completion.json")).unwrap();
        assert_eq!(receipt["geometry_kind"], "mosaic");
        assert!(receipt["session_files"].get("alignment.json").is_none());
        std::fs::write(root.join("coverage.tiff"), "changed visibility").unwrap();
        assert!(
            validate_render_binding(&root, &root, true)
                .unwrap_err()
                .to_string()
                .contains("coverage.tiff")
        );
        std::fs::write(root.join("coverage.tiff"), "coverage.tiff").unwrap();
        std::fs::write(root.join("mosaic-geometry.json"), "changed geometry").unwrap();
        assert!(
            validate_render_binding(&root, &root, true)
                .unwrap_err()
                .to_string()
                .contains("mosaic-geometry.json")
        );
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn focus_mapping_preserves_refused_original_ordinals_and_rejects_compaction() {
        use crate::session_input::{ResolvedPass, SourceFrame};
        let session = ResolvedSession {
            spec: SessionSpec::default(),
            manifest_path: None,
            passes: vec![
                ResolvedPass {
                    name: "first".into(),
                    directories: vec![],
                    global_range: 0..3,
                    segment_ranges: std::iter::once(0..3).collect(),
                },
                ResolvedPass {
                    name: "second".into(),
                    directories: vec![],
                    global_range: 3..4,
                    segment_ranges: std::iter::once(3..4).collect(),
                },
            ],
            frames: (0..4)
                .map(|i| SourceFrame {
                    global_index: i,
                    pass_index: usize::from(i == 3),
                    segment_index: 0,
                    pass_frame_index: if i == 3 { 0 } else { i },
                    segment_frame_index: i,
                    path: PathBuf::from(format!("{i}.ARW")),
                    bytes: 1,
                    modified_unix_nanos: None,
                })
                .collect(),
        };
        let mut report = json!({"pass":0,"ordinal_mapping":(0..3).map(|i|json!({"ordinal":i,"global_index":i,"acquisition":i})).collect::<Vec<_>>()});
        // Original 1 was unplaced; ordinal 2 must remain ordinal 2.
        validate_focus_mapping(&report, &session, &[0, 2]).unwrap();
        assert!(validate_focus_mapping(&report, &session, &[0, 3]).is_err());
        let full = report.clone();
        report["ordinal_mapping"].as_array_mut().unwrap().remove(1);
        assert!(validate_focus_mapping(&report, &session, &[0, 2]).is_err());
        report = full.clone();
        report["ordinal_mapping"][2]["ordinal"] = json!(1);
        assert!(validate_focus_mapping(&report, &session, &[0, 2]).is_err());
        report = full;
        report["ordinal_mapping"][2]["acquisition"] = json!(1);
        assert!(validate_focus_mapping(&report, &session, &[0, 2]).is_err());
    }
    #[test]
    fn session_comparison_publishes_actual_curves_and_rejects_shared_photons_or_gauge() {
        let root = std::env::temp_dir().join(format!(
            "strehl-compare-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        let mut dirs = Vec::new();
        for arm in 0..2 {
            let raw = root.join(format!("source-{arm}"));
            std::fs::create_dir(&raw).unwrap();
            std::fs::write(raw.join("one.ARW"), [arm as u8 + 1]).unwrap();
            let spec = SessionSpec {
                passes: vec![PassSpec {
                    name: format!("pass{arm}"),
                    directories: vec![raw],
                }],
                ..SessionSpec::default()
            };
            let session = spec.resolve_from(&root).unwrap();
            let ids = session.hash_sources(true).unwrap();
            let dir = root.join(format!("render-{arm}"));
            std::fs::create_dir(&dir).unwrap();
            let write = |name: &str, v: &Value| {
                crate::session_cmd::write_json_new(&dir.join(name), v).unwrap()
            };
            write("session.json", &serde_json::to_value(session).unwrap());
            write(
                "source-identities.json",
                &serde_json::to_value(ids).unwrap(),
            );
            write(
                "alignment.json",
                &json!({"warpmap_sha256":"fixture-shared-map"}),
            );
            write(
                "render-report.json",
                &json!({"invalid_output_pixels":0,"canvas":[0,0,64,64],"frames":[{"frame":0}],"recipe":{}}),
            );
            let mut pixels = Vec::new();
            for y in 0..128 {
                for x in 0..128 {
                    let v = 0.3 + 0.1 * (x as f32 * 0.7).sin() + 0.07 * (y as f32 * 0.5).cos();
                    pixels.extend_from_slice(&[v * (1. + 0.02 * arm as f32); 3]);
                }
            }
            strehl_edit::save_linear_tiff(
                &dir.join("master.tiff"),
                &strehl_edit::LinearImage {
                    width: 128,
                    height: 128,
                    pixels,
                    origin: strehl_edit::ImageOrigin::SceneLinear,
                    baseline: None,
                    baked_recipe: None,
                },
            )
            .unwrap();
            std::fs::copy(dir.join("master.tiff"), dir.join("photograph.tiff")).unwrap();
            publish_render_binding(&dir).unwrap();
            write(
                "completed.json",
                &json!({"schema":"strehl.session-completion.v1","render_bindings":completion_bindings(&dir).unwrap()}),
            );
            dirs.push(dir);
        }
        let mut args = CompareArgs {
            first: dirs[0].clone(),
            second: dirs[1].clone(),
            out_dir: root.join("comparison"),
            patch_size: 64,
            memory_limit_gib: 1.,
            threads: 1,
            focus_first: None,
            focus_second: None,
        };
        run(&args).unwrap();
        let report = read(&args.out_dir.join("reproducibility.json")).unwrap();
        assert_eq!(report["tiles"].as_array().unwrap().len(), 4);
        for tile in report["tiles"].as_array().unwrap() {
            assert!(tile["band_correlation"].as_f64().unwrap() > 0.999);
            assert!(tile["relative_rms_difference"].as_f64().unwrap() > 0.01);
            assert_eq!(tile["qualification"], 3);
            assert!(!tile["rings"].as_array().unwrap().is_empty());
        }
        args.threads = 4;
        args.out_dir = root.join("parallel");
        run(&args).unwrap();
        let parallel = read(&args.out_dir.join("reproducibility.json")).unwrap();
        assert_eq!(report["tiles"], parallel["tiles"]);
        assert_eq!(report["files"], parallel["files"]);
        assert!(
            report["files"]
                .as_array()
                .unwrap()
                .iter()
                .all(|v| v["file"].is_string())
        );
        let original = std::fs::read(dirs[1].join("master.tiff")).unwrap();
        std::fs::copy(dirs[0].join("master.tiff"), dirs[1].join("master.tiff")).unwrap();
        args.out_dir = root.join("replaced-master-refusal");
        assert!(
            run(&args)
                .unwrap_err()
                .to_string()
                .contains("output binding differs: master.tiff")
        );
        assert!(!args.out_dir.exists());
        std::fs::write(dirs[1].join("master.tiff"), original).unwrap();
        args.second = args.first.clone();
        args.out_dir = root.join("duplicate-refusal");
        assert!(
            run(&args)
                .unwrap_err()
                .to_string()
                .contains("original acquisition")
        );
        assert!(!args.out_dir.exists());
        args.second = dirs[1].clone();
        std::fs::write(
            dirs[1].join("alignment.json"),
            "{\"warpmap_sha256\":\"another-map\"}",
        )
        .unwrap();
        assert!(
            run(&args)
                .unwrap_err()
                .to_string()
                .contains("session binding")
        );
        assert!(!args.out_dir.exists());
        std::fs::remove_dir_all(root).unwrap();
    }
}
