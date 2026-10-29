//! Import completed CLI sessions as immutable external results, without reading RAWs.
use crate::{
    session_workspace::{SessionDraft, SessionMode},
    workspace_history::{Run, SourceIdentity},
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    io::Read,
    path::Path,
    sync::atomic::{AtomicBool, Ordering},
};
const JSON_LIMIT: u64 = 64 * 1024 * 1024;
const FILE_LIMIT: u64 = 2 * 1024 * 1024 * 1024;
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ImportedSession {
    pub imported_at: u64,
    pub renderer_bound: bool,
    pub renderer_build: Option<String>,
    pub files: BTreeMap<String, String>,
    pub diagnostic_warnings: Vec<String>,
}
impl ImportedSession {
    pub fn scope(&self) -> &'static str {
        if self.renderer_bound {
            "Imported CLI result · renderer output bindings verified. Original capture previews are not loaded."
        } else {
            "Imported CLI result · current-file identity only; original output binding unavailable. Original capture previews are not loaded."
        }
    }
}
fn hash(path: &Path, cancelled: &AtomicBool) -> Result<String> {
    let mut f = std::fs::File::open(path)
        .with_context(|| format!("Reading imported {}", path.display()))?;
    ensure!(
        f.metadata()?.is_file() && f.metadata()?.len() <= FILE_LIMIT,
        "Imported artifact exceeds the 2 GiB file bound"
    );
    let mut h = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Session import cancelled"
        );
        let n = f.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        h.update(&buffer[..n]);
    }
    Ok(h.finalize().iter().map(|v| format!("{v:02x}")).collect())
}
fn read(root: &Path, name: &str, files: &mut BTreeMap<String, String>) -> Result<Value> {
    ensure!(
        root.join(name).canonicalize()?.starts_with(root),
        "Imported artifact escapes its directory"
    );
    let file =
        std::fs::File::open(root.join(name)).with_context(|| format!("Reading imported {name}"))?;
    ensure!(
        file.metadata()?.len() <= JSON_LIMIT,
        "Imported JSON exceeds 64 MiB"
    );
    let mut bytes = Vec::new();
    file.take(JSON_LIMIT + 1).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() as u64 <= JSON_LIMIT,
        "Imported JSON grew beyond its bound"
    );
    let value = serde_json::from_slice(&bytes)?;
    let digest: String = Sha256::digest(&bytes)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect();
    if let Some(previous) = files.insert(name.into(), digest.clone()) {
        ensure!(
            previous == digest,
            "Imported JSON changed while reading: {name}"
        );
    }
    Ok(value)
}
fn valid_digest(value: &Value) -> Result<&str> {
    let digest = value.as_str().context("Renderer binding hash missing")?;
    ensure!(
        digest.len() == 64 && digest.bytes().all(|v| v.is_ascii_hexdigit()),
        "Invalid renderer binding hash"
    );
    Ok(digest)
}
fn bind(
    root: &Path,
    name: &str,
    expected: Option<&str>,
    files: &mut BTreeMap<String, String>,
    cancelled: &AtomicBool,
) -> Result<()> {
    let path = Path::new(name);
    ensure!(
        !path.is_absolute()
            && !name.contains(['\\', ':'])
            && path
                .components()
                .all(|c| matches!(c, std::path::Component::Normal(_))),
        "Invalid imported relative artifact name"
    );
    ensure!(
        root.join(path).canonicalize()?.starts_with(root),
        "Imported artifact escapes its directory"
    );
    let actual = hash(&root.join(path), cancelled)?;
    ensure!(
        expected.is_none_or(|v| actual.eq_ignore_ascii_case(v)),
        "Renderer output binding mismatch: {name}"
    );
    if let Some(previous) = files.insert(name.into(), actual.clone()) {
        ensure!(
            previous == actual,
            "Imported artifact changed while reading: {name}"
        );
    }
    Ok(())
}
pub(crate) fn verify(
    root: &Path,
    provenance: &ImportedSession,
    cancelled: &AtomicBool,
) -> Result<()> {
    ensure!(
        !provenance.files.is_empty() && provenance.files.len() <= 8192,
        "Invalid imported artifact census"
    );
    for (name, expected) in &provenance.files {
        let mut scratch = BTreeMap::new();
        bind(root, name, Some(expected), &mut scratch, cancelled)?;
    }
    Ok(())
}
#[derive(Deserialize)]
struct NativeSensorMaster {
    schema: String,
    file: String,
    stage: String,
    cfa: String,
    storage: String,
    reconstruction_applied: bool,
}
fn native_sensor_declared(report: &Value) -> Result<bool> {
    let Some(value) = report.get("native_sensor_master") else {
        return Ok(false);
    };
    let native: NativeSensorMaster = serde_json::from_value(value.clone())
        .context("Invalid native sensor master declaration")?;
    ensure!(
        native.schema == "strehl.session-native-sensor-master.v1"
            && native.file == "sensor-master.tiff"
            && native.stage == "native-merge-before-demosaic"
            && native.cfa == "RGGB"
            && native.storage == "signed-f32"
            && !native.reconstruction_applied,
        "Unsupported native sensor master declaration"
    );
    Ok(true)
}
fn bindings(
    root: &Path,
    completion: &Value,
    outputs: &[String],
    mode: SessionMode,
    files: &mut BTreeMap<String, String>,
    cancelled: &AtomicBool,
) -> Result<bool> {
    let Some(bindings) = completion.get("render_bindings") else {
        // A partial new-format publication is not silently downgraded to legacy.
        ensure!(
            outputs.iter().all(|prefix| !root
                .join(format!("{prefix}render-completion.json"))
                .exists()),
            "Renderer receipts exist but session completion does not bind them"
        );
        if mode != SessionMode::Mosaic {
            for prefix in outputs {
                let report = read(root, &format!("{prefix}render-report.json"), files)?;
                ensure!(
                    !native_sensor_declared(&report)?
                        && !root.join(format!("{prefix}sensor-master.tiff")).exists(),
                    "Native sensor master requires a renderer output binding"
                );
            }
        }
        return Ok(false);
    };
    let bindings = bindings
        .as_object()
        .context("Invalid session renderer bindings")?;
    ensure!(
        !bindings.is_empty() && bindings.len() <= 130,
        "Invalid renderer binding count"
    );
    for prefix in outputs {
        ensure!(
            bindings.contains_key(&format!("{prefix}render-completion.json")),
            "Session completion omits a photograph binding"
        );
    }
    for (name, digest) in bindings {
        let components: Vec<_> = name.split('/').collect();
        ensure!(
            components.len() <= 2
                && components.last() == Some(&"render-completion.json")
                && (components.len() == 1
                    || components[0].starts_with("layer-")
                    || components[0].starts_with("independent-pass-")),
            "Unsupported renderer binding path"
        );
        bind(root, name, Some(valid_digest(digest)?), files, cancelled)?;
        let receipt = read(root, name, files)?;
        ensure!(
            receipt["schema"] == "strehl.session-render-completion.v1",
            "Unknown renderer completion schema"
        );
        let mosaic = mode == SessionMode::Mosaic;
        let kind = receipt.get("geometry_kind").and_then(Value::as_str);
        ensure!(
            if mosaic {
                kind == Some("mosaic")
            } else {
                kind.is_none() && receipt.get("geometry_kind").is_none()
                    || kind == Some("session-alignment")
            },
            "Renderer geometry kind differs from session mode"
        );
        ensure!(
            !mosaic || components.len() == 1,
            "Mosaic renderer binding must describe its root output"
        );
        let dir = if components.len() == 1 {
            String::new()
        } else {
            format!("{}/", components[0])
        };
        let payload = receipt["files"]
            .as_object()
            .context("Renderer output files missing")?;
        let native_sensor = if mosaic {
            false
        } else {
            let report_name = format!("{dir}render-report.json");
            bind(
                root,
                &report_name,
                Some(valid_digest(
                    payload
                        .get("render-report.json")
                        .context("Renderer report binding missing")?,
                )?),
                files,
                cancelled,
            )?;
            let report = read(root, &report_name, files)?;
            let declared = native_sensor_declared(&report)?;
            ensure!(
                declared == payload.contains_key("sensor-master.tiff")
                    && declared == root.join(format!("{dir}sensor-master.tiff")).exists(),
                "Native sensor master declaration, file and binding differ"
            );
            declared
        };
        let expected: &[&str] = if mosaic {
            &[
                "master.tiff",
                "photograph.tiff",
                "render-report.json",
                "sensor-master.tiff",
                "coverage.tiff",
                "join-confidence.tiff",
                "view-owner.tiff",
                "mosaic-report.json",
            ]
        } else if native_sensor {
            &[
                "master.tiff",
                "photograph.tiff",
                "render-report.json",
                "sensor-master.tiff",
            ]
        } else {
            &["master.tiff", "photograph.tiff", "render-report.json"]
        };
        ensure!(
            payload.len() == expected.len(),
            "Renderer completion output census differs"
        );
        for &leaf in expected {
            bind(
                root,
                &format!("{dir}{leaf}"),
                Some(valid_digest(
                    payload
                        .get(leaf)
                        .context("Renderer output binding missing")?,
                )?),
                files,
                cancelled,
            )?;
        }
        let session_files = receipt["session_files"]
            .as_object()
            .context("Renderer session files missing")?;
        ensure!(
            session_files.len() == 3,
            "Renderer completion session census differs"
        );
        let geometry = if mosaic {
            "mosaic-geometry.json"
        } else {
            "alignment.json"
        };
        for leaf in ["session.json", "source-identities.json", geometry] {
            bind(
                root,
                leaf,
                Some(valid_digest(&session_files[leaf])?),
                files,
                cancelled,
            )?;
        }
    }
    Ok(true)
}
pub(crate) fn load(directory: &Path, cancelled: &AtomicBool) -> Result<Run> {
    let root = std::fs::canonicalize(directory)?;
    ensure!(root.is_dir(), "Choose a completed CLI session directory");
    let mut files = BTreeMap::new();
    let completion = read(&root, "completed.json", &mut files)?;
    ensure!(
        completion["schema"] == "strehl.session-completion.v1",
        "No supported session completion receipt"
    );
    let resolved = read(&root, "session.json", &mut files)?;
    let spec: strehl_cli::session_input::SessionSpec =
        serde_json::from_value(resolved["spec"].clone())?;
    spec.validate()?;
    ensure!(
        !spec.passes.is_empty() && spec.passes.len() <= 64,
        "Imported session pass count exceeds desktop support"
    );
    let identities: Vec<strehl_cli::session_input::SourceIdentity> =
        serde_json::from_value(read(&root, "source-identities.json", &mut files)?)?;
    let frames = resolved["frames"]
        .as_array()
        .context("Resolved source census missing")?;
    ensure!(
        !frames.is_empty() && frames.len() <= u16::MAX as usize && frames.len() == identities.len(),
        "Imported source count differs"
    );
    ensure!(
        completion["frames"].as_u64() == Some(frames.len() as u64)
            && completion["passes"].as_u64() == Some(spec.passes.len() as u64)
            && completion["primary_pass"] == serde_json::to_value(spec.primary_pass)?,
        "Session completion does not match its source census"
    );
    let mut counts = vec![0usize; spec.passes.len()];
    let mut seen = std::collections::BTreeSet::new();
    for (i, (frame, id)) in frames.iter().zip(&identities).enumerate() {
        id.validate()?;
        ensure!(
            seen.insert(id.sha256.clone()),
            "Imported source photons are duplicated"
        );
        let pass = frame["pass_index"].as_u64().context("Frame pass missing")? as usize;
        ensure!(
            pass < spec.passes.len()
                && frame["global_index"].as_u64() == Some(i as u64)
                && frame["path"] == serde_json::to_value(&id.path)?
                && frame["bytes"].as_u64() == Some(id.bytes)
                && frame["modified_unix_nanos"] == serde_json::to_value(id.modified_unix_nanos)?
                && id
                    .path
                    .parent()
                    .is_some_and(|p| spec.passes[pass].directories.iter().any(|d| d == p)),
            "Imported ordered source identity differs"
        );
        ensure!(
            pass == 0 || counts[..pass].iter().all(|&n| n > 0),
            "Imported pass order is incomplete"
        );
        if i > 0 {
            ensure!(
                frame["pass_index"].as_u64() >= frames[i - 1]["pass_index"].as_u64(),
                "Imported pass order reversed"
            );
        }
        counts[pass] += 1;
    }
    ensure!(
        counts.iter().all(|&n| n > 0),
        "An imported pass has no captures"
    );
    let passes = resolved["passes"]
        .as_array()
        .context("Resolved passes missing")?;
    ensure!(
        passes.len() == spec.passes.len(),
        "Resolved pass count differs"
    );
    let mut cursor = 0;
    for (p, ((pass, declared), count)) in passes.iter().zip(&spec.passes).zip(&counts).enumerate() {
        ensure!(
            pass["name"] == declared.name
                && pass["directories"] == serde_json::to_value(&declared.directories)?
                && pass["global_range"] == serde_json::json!({"start":cursor,"end":cursor+count}),
            "Resolved pass ranges differ"
        );
        let segments = pass["segment_ranges"]
            .as_array()
            .context("Resolved segments missing")?;
        ensure!(
            segments.len() == declared.directories.len(),
            "Resolved segment count differs"
        );
        let pass_start = cursor;
        for (j, (range, folder)) in segments.iter().zip(&declared.directories).enumerate() {
            ensure!(
                range["start"].as_u64() == Some(cursor as u64),
                "Resolved segment start differs"
            );
            let end = usize::try_from(range["end"].as_u64().context("Segment end missing")?)?;
            ensure!(
                end > cursor && end <= pass_start + count,
                "Invalid resolved segment extent"
            );
            for (k, frame) in frames[cursor..end].iter().enumerate() {
                ensure!(
                    frame["pass_index"].as_u64() == Some(p as u64)
                        && frame["segment_index"].as_u64() == Some(j as u64)
                        && frame["pass_frame_index"].as_u64()
                            == Some((cursor + k - pass_start) as u64)
                        && frame["segment_frame_index"].as_u64() == Some(k as u64)
                        && identities[cursor + k].path.parent() == Some(folder.as_path()),
                    "Resolved segment identity/order differs"
                );
            }
            cursor = end;
        }
        ensure!(
            cursor == pass_start + count,
            "Resolved segment ranges do not cover pass"
        );
    }
    if spec.mode == SessionMode::IndependentViews {
        return views::load(
            &root,
            &completion,
            &resolved,
            spec,
            &identities,
            files,
            cancelled,
        );
    }
    let outputs: Vec<String> = if spec.mode == SessionMode::Layers {
        (0..spec.passes.len())
            .map(|i| format!("layer-{:02}/", i + 1))
            .collect()
    } else {
        vec![String::new()]
    };
    ensure!(
        completion["outputs"].as_u64() == Some(outputs.len() as u64),
        "Imported photograph count differs"
    );
    let bound = bindings(
        &root,
        &completion,
        &outputs,
        spec.mode,
        &mut files,
        cancelled,
    )?;
    let mut first_report = None;
    let mut diagnostic_warnings = Vec::new();
    for prefix in &outputs {
        let report = read(&root, &format!("{prefix}render-report.json"), &mut files)?;
        let photo = root.join(format!("{prefix}photograph.tiff"));
        let master = root.join(format!("{prefix}master.tiff"));
        let dimensions = image::image_dimensions(&photo)?;
        let master_dimensions = image::image_dimensions(&master)?;
        ensure!(
            dimensions == master_dimensions
                && dimensions.0 > 0
                && dimensions.1 > 0
                && u64::from(dimensions.0) * u64::from(dimensions.1) <= 40_000_000,
            "Imported photograph exceeds 40 million pixels or master dimensions differ"
        );
        if spec.mode != SessionMode::Mosaic {
            let canvas = report["canvas"]
                .as_array()
                .context("Imported render canvas missing")?;
            ensure!(
                canvas.len() == 4
                    && canvas[2].as_u64().and_then(|v| v.checked_mul(2))
                        == Some(u64::from(dimensions.0))
                    && canvas[3].as_u64().and_then(|v| v.checked_mul(2))
                        == Some(u64::from(dimensions.1)),
                "Imported canvas differs from photograph"
            );
        }
        crate::preview::validate_tiff(&photo)?;
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Session import cancelled"
        );
        let linear = strehl_edit::load_tiff(&master)?;
        ensure!(
            linear.origin == strehl_edit::ImageOrigin::SceneLinear
                && linear.baseline.is_some()
                && dimensions == (linear.width, linear.height),
            "Imported photograph and scene-linear master differ or lack baseline"
        );
        let size = [linear.width, linear.height];
        drop(linear);
        if spec.mode == SessionMode::Mosaic {
            crate::photo_coverage::Coverage::load(&photo, size)?
                .context("Mosaic final coverage unavailable")?;
        }
        for leaf in ["photograph.tiff", "master.tiff"] {
            bind(
                &root,
                &format!("{prefix}{leaf}"),
                None,
                &mut files,
                cancelled,
            )?;
        }
        for map in crate::session_diagnostics::import_artifacts(&photo, &mut diagnostic_warnings)? {
            let name = map
                .path
                .strip_prefix(&root)?
                .to_string_lossy()
                .replace('\\', "/");
            bind(&root, &name, map.sha256.as_deref(), &mut files, cancelled)?;
            ensure!(
                !cancelled.load(Ordering::Relaxed),
                "Session import cancelled"
            );
            // One scalar map at a time; no image stack or map volume is retained.
            drop(strehl_edit::read_scalar_tiff(
                &map.path,
                map.size,
                160_000_000,
                map.sha256.as_deref(),
            )?);
        }
        if first_report.is_none() {
            first_report = Some(report);
        }
    }
    for name in [
        "alignment.json",
        "mosaic-geometry.json",
        "mosaic-report.json",
        "photometry.json",
        "calibration.json",
        "focus/focus-evidence.json",
        "reproducibility/reproducibility.json",
        "reconstruction/geometry.json",
    ] {
        if root.join(name).is_file() {
            let _ = read(&root, name, &mut files)?;
        }
    }
    for prefix in &outputs {
        let name = format!("{prefix}contributions/index.json");
        if root.join(&name).is_file() {
            let _ = read(&root, &name, &mut files)?;
        }
    }
    let report = first_report.unwrap();
    let recipe = &report["recipe"];
    for (key, lo, hi) in [
        ("bands", 1., 12.),
        ("exponent", 0.5, 8.),
        ("sharpen_per_octave", 1., 2.),
        ("gate", 0., 8.),
        ("exposure_ev", -12., 12.),
        ("memory_limit_gib", 0.1, 1024.),
        ("workers", 1., 1024.),
    ] {
        let value = recipe[key]
            .as_f64()
            .with_context(|| format!("Missing imported recipe {key}"))?;
        ensure!(
            value.is_finite() && (lo..=hi).contains(&value),
            "Unsupported imported recipe {key}"
        );
    }
    let resampler: crate::jobs::Resampler = serde_json::from_value(recipe["resampler"].clone())
        .context("Unknown imported resampler")?;
    let source = spec.passes[0].directories[0].clone();
    let sources = identities
        .iter()
        .map(|id| SourceIdentity {
            path: id.path.clone(),
            bytes: id.bytes,
            modified_ns: id.modified_unix_nanos.map(u128::from),
        })
        .collect::<Vec<_>>();
    let draft = SessionDraft {
        manifest: spec,
        memory_limit_gib: recipe["memory_limit_gib"].as_f64().unwrap_or(16.),
        precision_weights: recipe["precision_weights"].as_bool().unwrap_or(false),
        contribution_maps: recipe["contribution_maps"].as_bool().unwrap_or(false),
        focus_evidence: root.join("focus/focus-evidence.json").is_file(),
        reproducibility: root.join("reproducibility/reproducibility.json").is_file(),
        original_cfa_reconstruction: recipe["original_cfa_reconstruction"]
            .as_bool()
            .unwrap_or(false),
        sources: sources.clone(),
    };
    // Mosaic's inherent exports do not enable non-Mosaic command switches.
    let mut draft = draft;
    if draft.manifest.mode == SessionMode::Mosaic {
        draft.focus_evidence = false;
        draft.contribution_maps = false;
        draft.reproducibility = false;
    }
    draft.validate()?;
    let summary =
        crate::session_workspace::SessionSummary::load_imported(&root, &draft, "import validation");
    ensure!(
        summary.completed && summary.report_error.is_none(),
        "Imported session geometry/census invalid: {:?}",
        summary.report_error
    );
    let settings = crate::jobs::RenderSettings {
        session: Some(draft.clone()),
        pyramid_bands: recipe["bands"].as_u64().map(|v| v as usize),
        pyramid_exponent: recipe["exponent"].as_f64().map(|v| v as f32),
        pyramid_sharpen: recipe["sharpen_per_octave"].as_f64().map(|v| v as f32),
        resampler,
        confidence_map: false,
        correct_lateral_ca: false,
        ..Default::default()
    };
    let provenance = ImportedSession {
        imported_at: crate::workspace_history::timestamp(),
        renderer_bound: bound,
        renderer_build: report["build"].as_str().map(str::to_owned),
        files,
        diagnostic_warnings,
    };
    verify(&root, &provenance, cancelled)?;
    let selected = if draft.manifest.mode == SessionMode::Layers {
        draft.manifest.primary_pass.unwrap_or(0)
    } else {
        0
    };
    Ok(Run {
        directory: root.clone(),
        source,
        output: root.join(format!("{}photograph.tiff", outputs[selected])),
        log: root.join("completed.json"),
        label: format!(
            "Imported CLI · {}",
            root.file_name().unwrap_or_default().to_string_lossy()
        ),
        created: provenance.imported_at,
        status: "Saved".into(),
        frames: frames.len(),
        sources,
        settings,
        exposure: recipe["exposure_ev"].as_f64().map(|v| v as f32),
        gate: recipe["gate"].as_f64().map(|v| v as f32),
        workers: recipe["workers"].as_u64().unwrap_or(1).min(1024) as usize,
        pinned: false,
        imported: Some(provenance),
    })
}

#[cfg(test)]
#[path = "session-import-tests.rs"]
mod tests;

#[path = "session-import-views.rs"]
mod views;

#[path = "session-bundle-export.rs"]
mod bundle_export;
pub(crate) use bundle_export::export as export_view_bundle;

/// Recheck only the selected photograph's retained output binding before switching.
/// Imported legacy sessions retain their import-time identity; no RAW is opened.
pub(crate) fn validate_selected_output(
    run: &Run,
    output: &Path,
    cancelled: &AtomicBool,
) -> Result<()> {
    ensure!(
        run.owns_output(output),
        "Selected output does not belong to this run"
    );
    let root = if run.imported.is_some() {
        run.directory.clone()
    } else {
        run.directory.join("session-output")
    }
    .canonicalize()?;
    let canonical_output = output.canonicalize()?;
    ensure!(
        canonical_output.starts_with(&root),
        "Selected photograph escapes its saved run"
    );
    // Retain the declared child name for provenance lookup. A symlink to a
    // different view must not borrow that target view's expected hash.
    let parent = output
        .parent()
        .context("Selected output directory missing")?;
    ensure!(
        parent.starts_with(&root),
        "Selected output parent escapes its run"
    );
    if let Some(provenance) = &run.imported {
        for leaf in ["photograph.tiff", "master.tiff", "render-report.json"] {
            let path = parent.join(leaf);
            let name = path
                .strip_prefix(&root)?
                .to_string_lossy()
                .replace('\\', "/");
            let expected = provenance
                .files
                .get(&name)
                .context("Selected artifact lacks imported provenance")?;
            bind(
                &root,
                &name,
                Some(expected),
                &mut BTreeMap::new(),
                cancelled,
            )?;
        }
    } else {
        let receipt = parent.join("render-completion.json");
        if receipt.is_file() {
            let relative = receipt
                .strip_prefix(&root)?
                .to_string_lossy()
                .replace('\\', "/");
            let mut files = BTreeMap::new();
            let completion = read(&root, "completed.json", &mut files)?;
            bind(
                &root,
                &relative,
                Some(valid_digest(&completion["render_bindings"][&relative])?),
                &mut files,
                cancelled,
            )?;
            let binding = read(&root, &relative, &mut files)?;
            for leaf in ["photograph.tiff", "master.tiff", "render-report.json"] {
                let name = parent
                    .join(leaf)
                    .strip_prefix(&root)?
                    .to_string_lossy()
                    .replace('\\', "/");
                bind(
                    &root,
                    &name,
                    Some(valid_digest(&binding["files"][leaf])?),
                    &mut files,
                    cancelled,
                )?;
            }
        } else {
            ensure!(
                run.settings
                    .session
                    .as_ref()
                    .is_some_and(|s| s.manifest.mode == SessionMode::Layers),
                "Independent view renderer binding is missing"
            );
        }
    }
    Ok(())
}
#[cfg(test)]
pub(crate) use views::tests::fixture as independent_views_fixture;
