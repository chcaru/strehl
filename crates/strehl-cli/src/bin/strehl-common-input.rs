#[path = "common-stack/mod.rs"]
mod common_stack;

use std::path::{Path, PathBuf};

use strehl_core::pyramid::{BandMerge, FrameWorkspace, MergeConfig, Workspace, level_sizes};
use strehl_raw::common_tiff::{CommonTiffFrame, ExpectedIdentity};

#[derive(Debug)]
struct Args {
    tiff: PathBuf,
    report: PathBuf,
    expected: ExpectedIdentity,
    exercise_core_merge: bool,
}

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    if argv.iter().any(|value| value == "--stack-manifest") {
        std::process::exit(common_stack::entry(&argv));
    }
    let fallback_report = option_value(&argv, "--report").map(PathBuf::from);
    let outcome = std::panic::catch_unwind(|| run(&argv));
    let (code, report_path, body) = match outcome {
        Ok(Ok((path, body))) => (0, Some(path), body),
        Ok(Err(message)) => (1, fallback_report, failure_json(&message, "ERROR_RETURN")),
        Err(_) => (
            1,
            fallback_report,
            failure_json(
                "unexpected panic caught at verifier boundary",
                "PANIC_CAUGHT",
            ),
        ),
    };

    let wrote = report_path
        .as_deref()
        .map(|path| write_report(path, &body))
        .transpose();
    if let Err(error) = wrote {
        eprintln!("{}", failure_json(&error, "REPORT_WRITE_FAILED"));
        std::process::exit(1);
    }
    println!("{body}");
    std::process::exit(code);
}

fn run(argv: &[String]) -> Result<(PathBuf, String), String> {
    let args = parse_args(argv)?;
    let frame = CommonTiffFrame::read(&args.tiff).map_err(|e| e.to_string())?;
    frame.verify(&args.expected).map_err(|e| e.to_string())?;
    let planes = frame.merge_planes();
    let merge_hash = CommonTiffFrame::hash_merge_planes(&planes).map_err(|e| e.to_string())?;
    if merge_hash != frame.pixel_payload_sha256 {
        return Err(format!(
            "merge-facing sample hash diverged: payload {} merge {}",
            frame.pixel_payload_sha256, merge_hash
        ));
    }
    if args.exercise_core_merge {
        exercise_core_merge(frame.width as usize, frame.height as usize, &planes)?;
    }
    let report = format!(
        concat!(
            "{{",
            "\"schema\":\"m165-strehl-common-input-identity-v1\",",
            "\"status\":\"PASS\",",
            "\"tiff\":\"{}\",",
            "\"width\":{},\"height\":{},",
            "\"bits_per_sample\":[16,16,16],",
            "\"sample_format\":[1,1,1],",
            "\"compression\":1,",
            "\"photometric\":2,",
            "\"planar_configuration\":1,",
            "\"strip_count\":{},",
            "\"file_sha256\":\"{}\",",
            "\"pixel_payload_sha256\":\"{}\",",
            "\"internal_premerge_sha256\":\"{}\",",
            "\"merge_sample_sha256\":\"{}\",",
            "\"core_merge_exercised\":{},",
            "\"icc_sha256\":\"{}\",",
            "\"provenance\":\"{}\"",
            "}}"
        ),
        json_escape(&args.tiff.display().to_string()),
        frame.width,
        frame.height,
        frame.strips.len(),
        frame.file_sha256,
        frame.pixel_payload_sha256,
        frame.internal_pixel_sha256,
        merge_hash,
        args.exercise_core_merge,
        frame.icc_sha256,
        json_escape(&frame.provenance),
    );
    Ok((args.report, report))
}

fn parse_args(argv: &[String]) -> Result<Args, String> {
    if argv.len() == 2 && matches!(argv[1].as_str(), "-h" | "--help") {
        return Err(usage());
    }
    let required = |name: &str| {
        option_value(argv, name)
            .map(str::to_string)
            .ok_or_else(|| format!("missing {name}; {}", usage()))
    };
    Ok(Args {
        tiff: PathBuf::from(required("--tiff")?),
        report: PathBuf::from(required("--report")?),
        expected: ExpectedIdentity {
            file_sha256: Some(required("--file-sha256")?),
            pixel_payload_sha256: Some(required("--pixel-sha256")?),
            icc_sha256: Some(required("--icc-sha256")?),
            source_sha256: Some(required("--source-sha256")?),
            converter_sha256: Some(required("--converter-sha256")?),
            settings_sha256: Some(required("--settings-sha256")?),
            pattern_map_sha256: Some(required("--pattern-map-sha256")?),
            pattern_manifest_sha256: Some(required("--pattern-manifest-sha256")?),
        },
        exercise_core_merge: argv.iter().any(|value| value == "--exercise-core-merge"),
    })
}

fn option_value<'a>(argv: &'a [String], name: &str) -> Option<&'a str> {
    argv.windows(2)
        .find(|pair| pair[0] == name)
        .map(|pair| pair[1].as_str())
}

fn usage() -> String {
    "usage: strehl-common-input --tiff PATH --report PATH --file-sha256 HEX \
     --pixel-sha256 HEX --icc-sha256 HEX --source-sha256 HEX \
     --converter-sha256 HEX --settings-sha256 HEX --pattern-map-sha256 HEX \
     --pattern-manifest-sha256 HEX [--exercise-core-merge]"
        .to_string()
}

fn exercise_core_merge(width: usize, height: usize, planes: &[Vec<f32>]) -> Result<(), String> {
    let pixels = width
        .checked_mul(height)
        .ok_or_else(|| "core-merge dimensions overflow".to_string())?;
    if planes.len() != 3 || planes.iter().any(|plane| plane.len() != pixels) {
        return Err("core-merge plane geometry mismatch".to_string());
    }
    let mut luma = Vec::with_capacity(pixels);
    for i in 0..pixels {
        luma.push((planes[0][i] + 2.0 * planes[1][i] + planes[2][i]) * 0.25);
    }
    let variance = vec![1.0f32; pixels];
    let cfg = MergeConfig::default();
    let sizes = level_sizes(width, height, cfg.bands);
    let mut merge = BandMerge::new(width, height, 3, cfg);
    let mut frame_workspace = FrameWorkspace::new(&sizes, 3);
    let refs: Vec<&[f32]> = planes.iter().map(Vec::as_slice).collect();
    frame_workspace.next_frame();
    merge.add_frame(&refs, &luma, &variance, &mut frame_workspace);
    let output = merge.finish(&mut Workspace::new(&sizes));
    if output.len() != 3
        || output
            .iter()
            .any(|plane| plane.len() != pixels || plane.iter().any(|sample| !sample.is_finite()))
    {
        return Err("core merge returned invalid RGB plane geometry or samples".to_string());
    }
    Ok(())
}

fn write_report(path: &Path, body: &str) -> Result<(), String> {
    if let Some(parent) = path.parent()
        && !parent.as_os_str().is_empty()
    {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("creating report directory {}: {e}", parent.display()))?;
    }
    std::fs::write(path, format!("{body}\n"))
        .map_err(|e| format!("writing report {}: {e}", path.display()))
}

fn failure_json(message: &str, failure_class: &str) -> String {
    format!(
        "{{\"schema\":\"m165-strehl-common-input-identity-v1\",\"status\":\"FAIL\",\
         \"failure_class\":\"{}\",\"reason\":\"{}\"}}",
        json_escape(failure_class),
        json_escape(message)
    )
}

fn json_escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c <= '\u{1f}' => {
                use std::fmt::Write as _;
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out
}
