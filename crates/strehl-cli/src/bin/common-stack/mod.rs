mod files;
mod manifest;
mod writer;

use std::io::Write;
use std::panic::{AssertUnwindSafe, catch_unwind};
use std::path::{Path, PathBuf};

use serde_json::{Value, json};
use strehl_core::pyramid::{BandMerge, FrameWorkspace, Workspace, level_sizes};
use strehl_raw::common_tiff::{CommonTiffFrame, ExpectedIdentity};

use files::{FileRef, Result, require};
use manifest::{HEIGHT, WIDTH};

const REPORT_CAP: usize = 64 << 10;

struct Args {
    manifest: PathBuf,
    manifest_sha: String,
    report: PathBuf,
    observer: String,
}
struct State {
    receipt: Value,
    report: PathBuf,
    incomplete: FileRef,
}

fn args(argv: &[String]) -> Result<Args> {
    require(
        argv.iter().all(|v| v.is_ascii() && v.len() <= 512)
            && argv.iter().map(String::len).sum::<usize>() <= 4096,
        "bounded command record",
    )?;
    require(
        argv.len() == 9,
        "stack mode requires exactly four option/value pairs",
    )?;
    let mut values = std::collections::BTreeMap::new();
    for pair in argv[1..].chunks_exact(2) {
        require(
            matches!(
                pair[0].as_str(),
                "--stack-manifest" | "--manifest-sha256" | "--report" | "--observer"
            ),
            "unknown or mixed stack-mode argument",
        )?;
        require(
            values.insert(pair[0].as_str(), pair[1].as_str()).is_none(),
            "duplicate stack argument",
        )?;
    }
    let get = |key| {
        values
            .get(key)
            .copied()
            .ok_or_else(|| format!("missing {key}"))
    };
    let cwd = std::env::current_dir().map_err(|e| format!("current directory: {e}"))?;
    let manifest = files::path(&cwd, get("--stack-manifest")?, false)?;
    let report = files::path(&cwd, get("--report")?, true)?;
    let manifest_sha = get("--manifest-sha256")?.to_string();
    require(files::valid_hash(&manifest_sha), "manifest SHA256 format")?;
    let observer = get("--observer")?.to_string();
    require(
        matches!(observer.as_str(), "off" | "on" | "placebo"),
        "unsupported observer mode",
    )?;
    require(
        files::key(&manifest) != files::key(&report),
        "manifest/report collision",
    )?;
    Ok(Args {
        manifest,
        manifest_sha,
        report,
        observer,
    })
}

fn initialize(args: &Args, argv: &[String]) -> Result<State> {
    for p in [
        args.report.with_extension("incomplete.json"),
        args.report.with_extension("stage.json"),
        args.report.with_extension("frame-0.json"),
        args.report.with_extension("frame-1.json"),
        args.report.with_extension("frame-2.json"),
    ] {
        require(!p.exists(), "receipt companion already exists")?;
    }
    let body = json!({"schema":"common-tiff-stack-incomplete-v1","status":"INITIAL_INCOMPLETE",
        "subject_complete":false,"manifest_path":args.manifest,"manifest_sha256":args.manifest_sha,
        "report":args.report,"scope":"Only a complete final receipt paired with actual process success admits output."});
    let incomplete = files::write_new(
        &args.report.with_extension("incomplete.json"),
        &files::encoded(&body, 4096)?,
        4096,
    )?;
    Ok(State {
        receipt: json!({"schema":"common-tiff-stack-result-v1","status":"REFUSED",
        "subject_complete":false,"stage":"initialized","command":argv,"observer_mode":args.observer,
        "incomplete":incomplete,"manifest":null,"binary":null,"consumed":[],"frame_receipts":[],
        "output":null,"scope":"Software integration only. Simulation noise declaration; identity common-RGB grid. No physical calibration, placement, comparator or quality admission."}),
        report: args.report.clone(),
        incomplete,
    })
}

fn environment() -> Result<()> {
    require(
        cfg!(target_endian = "little"),
        "little-endian common TIFF output host",
    )?;
    for (key, _) in std::env::vars_os() {
        let key = key.to_string_lossy().to_ascii_uppercase();
        require(
            !key.starts_with("STREHL_") && !key.starts_with("M194H_"),
            "stack mode rejects STREHL_/M194H_ environment overrides",
        )?;
    }
    Ok(())
}

#[derive(Clone, serde::Serialize)]
struct GateRow {
    level: usize,
    kind: &'static str,
    width: usize,
    height: usize,
    sites: usize,
    averaged_fraction: f64,
    zero_denominator: usize,
    positive_denominator: usize,
}

fn gate(mode: &str, merge: &BandMerge) -> Result<Value> {
    if mode == "off" {
        return Ok(
            json!({"called":true,"mode":"off","visited_levels":0,"allocated_rows":0,"levels":null}),
        );
    }
    if mode == "placebo" {
        let rows = vec![
            GateRow {
                level: 0,
                kind: "placebo",
                width: 0,
                height: 0,
                sites: 0,
                averaged_fraction: 0.0,
                zero_denominator: 0,
                positive_denominator: 0
            };
            4
        ];
        return Ok(
            json!({"called":true,"mode":"placebo","visited_levels":0,"allocated_rows":rows.len(),
            "levels":null,"placebo_rows_sha256":files::hash(&files::encoded(&rows,4096)?)}),
        );
    }
    require(mode == "on", "gate observer mode")?;
    let fractions = merge.averaged_fraction();
    require(
        fractions.len() == 4 && merge.sizes().len() == 4,
        "four actual denominator levels",
    )?;
    let mut levels = Vec::with_capacity(4);
    for (k, (fraction, size)) in fractions.iter().zip(merge.sizes()).enumerate() {
        let count = size.width * size.height;
        require(
            fraction.is_finite() && (0.0..=1.0).contains(fraction),
            "finite denominator fraction",
        )?;
        let product = *fraction * count as f64;
        let zero = product.round() as usize;
        require(
            zero <= count && (product - zero as f64).abs() <= 1e-7,
            "integer denominator count",
        )?;
        levels.push(GateRow {
            level: k,
            kind: if k < 3 { "Laplacian" } else { "mean-base" },
            width: size.width,
            height: size.height,
            sites: count,
            averaged_fraction: *fraction,
            zero_denominator: zero,
            positive_denominator: count - zero,
        });
    }
    Ok(
        json!({"called":true,"mode":"on","visited_levels":4,"allocated_rows":levels.len(),
        "scope":"One accumulated selection denominator shared across RGB per level; not per-frame threshold classification.",
        "frames":merge.frames(),"levels":levels}),
    )
}

fn observe(mode: &str, planes: &[Vec<f32>]) -> Result<Value> {
    let count = (WIDTH * HEIGHT * 3) as usize;
    require(
        planes.len() == 3 && planes.iter().all(|p| p.len() * 3 == count),
        "observer geometry",
    )?;
    match mode {
        "off" => Ok(json!({"called":true,"mode":"off","visited_samples":0,"allocated_samples":0})),
        "on" => {
            let shadow: Vec<f32> = planes.iter().flatten().copied().collect();
            let digest = files::f32_hash(shadow.iter().copied());
            Ok(
                json!({"called":true,"mode":"on","visited_samples":count,"allocated_samples":count,
                "plane_major_f32_sha256":digest}),
            )
        }
        "placebo" => {
            let shadow = vec![0.0f32; count];
            let digest = files::f32_hash(shadow.iter().copied());
            Ok(
                json!({"called":true,"mode":"placebo","visited_samples":0,"allocated_samples":count,
                "placebo_f32_sha256":digest}),
            )
        }
        _ => Err("observer mode".into()),
    }
}

fn process(args: &Args, state: &mut State) -> Result<()> {
    state.receipt["stage"] = json!("manifest");
    environment()?;
    let (raw, pin) = files::read(&args.manifest, 64 << 10, None)?;
    require(pin.sha256 == args.manifest_sha, "manifest hash mismatch")?;
    state.receipt["manifest"] = json!(pin);
    let base = args.manifest.parent().ok_or("manifest directory")?;
    let resolved = manifest::parse(&raw, base, &args.report, &state.incomplete)?;
    // Manifest is authenticated before any TIFF or profile read.
    let m = &resolved.manifest;
    state.receipt["plan"] = json!(m);
    let executable = std::env::current_exe().map_err(|e| format!("current executable: {e}"))?;
    let binary = files::hash_file(&executable, 128 << 20)?;
    state.receipt["binary"] = json!(binary);
    let (icc, profile) = files::read(&resolved.profile, 548, Some(&m.color.icc))?;
    require(
        files::hash(&icc) == manifest::ICC_SHA,
        "actual admitted ICC bytes",
    )?;
    state.receipt["profile"] = json!(profile);
    let sizes = level_sizes(WIDTH as usize, HEIGHT as usize, 3);
    require(sizes.len() == 4, "exact three-band geometry")?;
    let mut merge = BandMerge::new(WIDTH as usize, HEIGHT as usize, 3, m.merge.core()?);
    let mut workspace = FrameWorkspace::new(&sizes, 3);
    let all_beta = merge.band_gain().all().to_vec();
    require(
        all_beta.len() == 4 && all_beta.iter().all(|v| v.is_finite() && *v > 0.0),
        "actual white band gains",
    )?;
    let frame_beta = all_beta[..3].to_vec();
    state.receipt["runtime"] = json!({"rayon_threads":rayon::current_num_threads(),
        "actual_core_white_band_gain":all_beta,"passed_frame_beta":frame_beta,
        "band_gain_scope":"Core deterministic white-noise operator probe, not scene-derived or physical calibration.",
        "proxy":"(R+2G+B)/4 in RGB16 code values","variance_units":"RGB16-code squared"});
    require(rayon::current_num_threads() == 2, "fixed local Rayon pool")?;
    let mut consumed = Vec::new();
    let mut frame_receipts = Vec::new();
    for (ordinal, (input, path)) in m.inputs.iter().zip(&resolved.inputs).enumerate() {
        state.receipt["stage"] = json!(format!("input-{ordinal}"));
        let (bytes, actual) = files::read(path, manifest::TIFF_CAP, Some(&input.tiff))?;
        manifest::preflight(&bytes)?;
        let frame = CommonTiffFrame::parse(&bytes).map_err(|e| format!("TIFF parser: {e}"))?;
        frame
            .verify(&ExpectedIdentity {
                file_sha256: Some(actual.sha256.clone()),
                pixel_payload_sha256: Some(input.pixel_sha256.clone()),
                icc_sha256: Some(profile.sha256.clone()),
                ..ExpectedIdentity::default()
            })
            .map_err(|e| format!("TIFF identity: {e}"))?;
        require(
            frame.width == WIDTH && frame.height == HEIGHT,
            "actual parsed grid",
        )?;
        let provenance: manifest::Provenance = serde_json::from_str(&frame.provenance)
            .map_err(|e| format!("strict input provenance: {e}"))?;
        require(
            provenance == input.provenance,
            "actual input provenance mismatch",
        )?;
        let planes = frame.merge_planes();
        let before = CommonTiffFrame::hash_merge_planes(&planes).map_err(|e| e.to_string())?;
        require(before == input.pixel_sha256, "actual merge-facing payload")?;
        let n = (WIDTH * HEIGHT) as usize;
        let proxy: Vec<f32> = (0..n)
            .map(|i| (planes[0][i] + 2.0 * planes[1][i] + planes[2][i]) * 0.25)
            .collect();
        let variance = vec![m.noise.proxy_variance; n];
        let proxy_before = files::f32_hash(proxy.iter().copied());
        let variance_before = files::f32_hash(variance.iter().copied());
        let variance_before_value = variance[0];
        workspace.next_frame();
        let refs: Vec<&[f32]> = planes.iter().map(Vec::as_slice).collect();
        merge.add_frame_with_gain(&refs, &proxy, &variance, Some(&frame_beta), &mut workspace);
        let after = CommonTiffFrame::hash_merge_planes(&planes).map_err(|e| e.to_string())?;
        let proxy_after = files::f32_hash(proxy.iter().copied());
        let variance_after = files::f32_hash(variance.iter().copied());
        require(
            before == after && proxy_before == proxy_after && variance_before == variance_after,
            "input tensor mutation during fold",
        )?;
        require(
            merge.frames() as usize == ordinal + 1,
            "exact actual frame count",
        )?;
        let row = json!({"ordinal":ordinal,"id":input.id,"file":actual,"width":frame.width,"height":frame.height,
            "strip_count":frame.strips.len(),"pixel_sha256":frame.pixel_payload_sha256,
            "icc_sha256":frame.icc_sha256,"provenance":provenance,"merge_sha256_before":before,"merge_sha256_after":after,
            "proxy_f32_sha256_before":proxy_before,"proxy_f32_sha256_after":proxy_after,
            "variance_f32_sha256_before":variance_before,"variance_f32_sha256_after":variance_after,
            "variance_value_before":variance_before_value,"variance_value_after":variance[0],"variance_sites":n,
            "passed_frame_beta":frame_beta,"merge_frames":merge.frames(),"gate":gate(&args.observer,&merge)?});
        consumed.push(row.clone());
        state.receipt["consumed"] = json!(consumed);
        let path = args.report.with_extension(format!("frame-{ordinal}.json"));
        let receipt = files::write_new(
            &path,
            &files::encoded(
                &json!({
            "schema":"common-tiff-stack-frame-v1","manifest":pin,"fold":row}),
                16 << 10,
            )?,
            16 << 10,
        )?;
        frame_receipts.push(receipt);
        state.receipt["frame_receipts"] = json!(frame_receipts);
        // The encoded TIFF, u16 frame and f32 planes/proxy/variance drop here.
    }
    state.receipt["stage"] = json!("finish");
    require(
        consumed.len() == 3 && merge.frames() == 3,
        "complete three-input population",
    )?;
    let output = merge.finish(&mut Workspace::new(&sizes));
    let before_observer = files::f32_hash(output.iter().flatten().copied());
    let observer = observe(&args.observer, &output)?;
    let after_observer = files::f32_hash(output.iter().flatten().copied());
    require(
        before_observer == after_observer,
        "output observer mutation",
    )?;
    state.receipt["observer"] = json!({"observation":observer,"output_f32_sha256_before":before_observer,
        "output_f32_sha256_after":after_observer,"scope":"One actual after-finish observer call only."});
    state.receipt["final_gate"] = consumed.last().ok_or("missing final fold")?["gate"].clone();
    state.receipt["stage"] = json!("encode");
    let encoded = writer::encode(&output, &icc)?;
    state.receipt["encoding"] = json!(encoded);
    // Recheck all input/profile/manifest bytes and the actual executable before publication.
    for (input, path) in m.inputs.iter().zip(&resolved.inputs) {
        files::read(path, manifest::TIFF_CAP, Some(&input.tiff))?;
    }
    files::read(&resolved.profile, 548, Some(&profile))?;
    files::read(&args.manifest, 64 << 10, Some(&pin))?;
    require(
        files::hash_file(&executable, 128 << 20)? == binary,
        "actual executable changed",
    )?;
    files::read(
        &args.report.with_extension("incomplete.json"),
        4096,
        Some(&state.incomplete),
    )?;
    state.receipt["inputs_rechecked"] = json!(true);
    state.receipt["stage"] = json!("publish-output");
    let output_pin = files::staged(
        &resolved.output,
        &resolved.output.with_extension("tiff-stage"),
        &encoded.bytes,
        writer::CAP,
    )?;
    state.receipt["output"] = json!(output_pin);
    state.receipt["stage"] = json!("complete");
    state.receipt["status"] = json!("COMPLETE");
    state.receipt["subject_complete"] = json!(true);
    Ok(())
}

pub fn entry(argv: &[String]) -> i32 {
    let result = (|| -> Result<bool> {
        let args = args(argv)?;
        let mut state = initialize(&args, argv)?;
        let execution = catch_unwind(AssertUnwindSafe(|| -> Result<()> {
            let pool = rayon::ThreadPoolBuilder::new()
                .num_threads(2)
                .build()
                .map_err(|e| format!("local Rayon pool: {e}"))?;
            pool.install(|| process(&args, &mut state))
        }));
        let error = match execution {
            Ok(Ok(())) => None,
            Ok(Err(error)) => Some(error),
            Err(_) => Some("panic caught at common-stack boundary".into()),
        };
        if let Some(error) = error {
            state.receipt["status"] = json!("REFUSED");
            state.receipt["subject_complete"] = json!(false);
            state.receipt["error"] = json!(error.chars().take(2048).collect::<String>());
        }
        let raw = files::encoded(&state.receipt, REPORT_CAP)?;
        files::staged(
            &state.report,
            &state.report.with_extension("stage.json"),
            &raw,
            REPORT_CAP,
        )?;
        // Final stdout is exactly the raw report bytes; outer exit still controls admission.
        let mut stdout = std::io::stdout().lock();
        stdout
            .write_all(&raw)
            .map_err(|e| format!("stdout write: {e}"))?;
        stdout.flush().map_err(|e| format!("stdout flush: {e}"))?;
        Ok(state.receipt["subject_complete"] == json!(true))
    })();
    match result {
        Ok(true) => 0,
        Ok(false) => 1,
        Err(error) => {
            eprintln!(
                "common-tiff-stack refused: {}",
                error.chars().take(2048).collect::<String>()
            );
            1
        }
    }
}
