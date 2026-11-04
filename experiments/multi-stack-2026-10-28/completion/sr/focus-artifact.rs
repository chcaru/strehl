//! Hash-bound reuse of completed research focus fields. No RAW/cache adoption.
use anyhow::{Context, Result, ensure};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    fs,
    ops::Range,
    path::{Component, Path},
};
use strehl_cli::session_sampling::SamplingDomain;
use strehl_core::focus_evidence::{FocusEvidence, FocusFrame};
// Explicit research imports accept only these completed, hash-bound artifacts.
// Each retains its own binary/archive/source identity; none is relabeled as
// the currently compiled focus implementation after unrelated receipt changes.
const APPROVED_SEALS: [&[u8]; 3] = [
    include_bytes!("focus-census-01-seal.json"),
    include_bytes!("chart-focus-census-02-seal.json"),
    include_bytes!("tilted-focus-census-01-seal.json"),
];
const CENSUS_SOURCE_PATH: &str = "experiments/multi-stack-2026-10-28/completion/sr/focus-census.rs";
fn hex(b: &[u8]) -> String {
    b.iter().map(|v| format!("{v:02x}")).collect()
}
fn digest(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}
#[derive(Debug)]
pub struct FocusSlice {
    pub frames: Vec<FocusFrame>,
    pub ordinal: Vec<f32>,
    pub width_frames: Vec<f32>,
    pub flags: Vec<u8>,
    pub usable: Vec<bool>,
}
impl From<FocusEvidence> for FocusSlice {
    fn from(f: FocusEvidence) -> Self {
        Self {
            frames: f.frames,
            ordinal: f.ordinal,
            width_frames: f.width_frames,
            flags: f.flags,
            usable: f.usable,
        }
    }
}
pub struct Binding<'a> {
    pub domain: SamplingDomain,
    pub roi_sensor: [usize; 4],
    pub roi_index: usize,
    pub pass_ranges: &'a [Range<usize>],
    pub alignment_path: &'a Path,
    pub calibration_path: &'a Path,
    pub identities_path: &'a Path,
}
fn bounded(path: &Path, max: usize) -> Result<Vec<u8>> {
    ensure!(
        fs::metadata(path)?.len() <= max as u64,
        "focus artifact exceeds bounded length"
    );
    let bytes = fs::read(path)?;
    ensure!(bytes.len() <= max, "focus artifact grew past bound");
    Ok(bytes)
}
fn verified(root: &Path, relative: &str, seal: &Value) -> Result<Vec<u8>> {
    let path = Path::new(relative);
    ensure!(
        path.components().all(|v| matches!(v, Component::Normal(_))),
        "invalid focus artifact relative path"
    );
    let actual = fs::canonicalize(root.join(path))?;
    ensure!(actual.starts_with(root), "focus artifact escapes its root");
    let bytes = bounded(&actual, 4 << 20)?;
    ensure!(
        seal["files"][relative].as_str() == Some(digest(&bytes).as_str()),
        "focus artifact digest mismatch: {relative}"
    );
    Ok(bytes)
}
fn floats(bytes: &[u8], n: usize) -> Result<Vec<f32>> {
    ensure!(
        bytes.len() == n.checked_mul(4).context("focus raster byte overflow")?,
        "wrong focus raster length"
    );
    Ok(bytes
        .chunks_exact(4)
        .map(|b| f32::from_le_bytes(b.try_into().unwrap()))
        .collect())
}
pub fn load(root: &Path, seal_path: &Path, binding: Binding<'_>) -> Result<Vec<FocusSlice>> {
    let selected = bounded(seal_path, 1 << 20)?;
    let approved = APPROVED_SEALS
        .into_iter()
        .find(|bytes| digest(bytes) == digest(&selected))
        .context("focus seal is not an explicitly approved completed artifact")?;
    load_checked(root, seal_path, binding, approved)
}
fn load_checked(
    root: &Path,
    seal_path: &Path,
    binding: Binding<'_>,
    approved: &[u8],
) -> Result<Vec<FocusSlice>> {
    let root = fs::canonicalize(root)?;
    let seal_bytes = bounded(seal_path, 1 << 20)?;
    ensure!(
        digest(&seal_bytes) == digest(approved),
        "focus artifact seal is not the explicitly approved historical artifact"
    );
    let seal: Value = serde_json::from_slice(&seal_bytes)?;
    ensure!(
        seal["schema"] == "strehl.sr-focus-artifact-seal.v1",
        "unsupported focus artifact seal"
    );
    for (name, path) in [
        ("alignment_sha256", binding.alignment_path),
        ("calibration_sha256", binding.calibration_path),
        ("source_identities_sha256", binding.identities_path),
    ] {
        let bytes = bounded(path, 8 << 20)?;
        ensure!(
            seal[name].as_str() == Some(digest(&bytes).as_str()),
            "focus input binding differs: {name}"
        );
    }
    let report_bytes = verified(&root, "report.json", &seal)?;
    ensure!(
        seal["census_report_sha256"].as_str() == Some(digest(&report_bytes).as_str()),
        "focus report identity mismatch"
    );
    let report: Value = serde_json::from_slice(&report_bytes)?;
    ensure!(
        report["schema"] == "strehl.sr-focus-census.v1" && report["raw_decodes"] == 0,
        "invalid completed focus census"
    );
    ensure!(
        report["alignment_sha256"] == seal["alignment_sha256"],
        "focus report alignment mismatch"
    );
    ensure!(
        report["source_sha256"] == seal["producer_sources"][CENSUS_SOURCE_PATH],
        "focus source record mismatch"
    );
    let d = binding.domain;
    d.validate()?;
    ensure!(
        report["full_guide_geometry"] == serde_json::json!([d.full.width, d.full.height]),
        "focus full geometry mismatch"
    );
    let roi = report["rois"]
        .as_array()
        .context("focus regions missing")?
        .iter()
        .find(|r| r["index"].as_u64() == Some(binding.roi_index as u64))
        .context("focus region absent")?;
    ensure!(
        roi["roi_sensor"] == serde_json::json!(binding.roi_sensor)
            && roi["focus_domain_quad"] == serde_json::json!([d.x, d.y, d.width, d.height]),
        "focus ROI/domain mismatch"
    );
    let passes = roi["passes"].as_array().context("focus passes missing")?;
    ensure!(
        passes.len() == binding.pass_ranges.len(),
        "focus pass count mismatch"
    );
    // Verify the entire sealed artifact (including retained multimode diagnostics),
    // then hash each consumed read again so data cannot change between validation and use.
    for relative in seal["files"]
        .as_object()
        .context("focus files absent")?
        .keys()
    {
        verified(&root, relative, &seal)?;
    }
    let n = d
        .width
        .checked_mul(d.height)
        .context("focus pixel overflow")?;
    let mut out = Vec::new();
    for (pass, range) in binding.pass_ranges.iter().enumerate() {
        ensure!(
            range.len() >= 3 && range.len() < usize::from(u16::MAX),
            "invalid focus frame range"
        );
        ensure!(
            passes[pass]["pass_index"] == serde_json::json!(pass)
                && passes[pass]["global_range"] == serde_json::json!([range.start, range.end]),
            "focus ordinal identity mismatch"
        );
        let prefix = format!("roi-{}/focus-pass-{pass}", binding.roi_index);
        let ordinal = floats(
            &verified(&root, &format!("{prefix}-ordinal.f32"), &seal)?,
            n,
        )?;
        let width_frames = floats(&verified(&root, &format!("{prefix}-width.f32"), &seal)?, n)?;
        let flags = verified(&root, &format!("{prefix}-flags.u8"), &seal)?;
        ensure!(flags.len() == n, "focus flags shape mismatch");
        ensure!(
            flags.iter().all(|v| *v <= 127),
            "unknown focus quality flag"
        );
        let usable: Vec<_> = flags.iter().map(|v| *v == 0).collect();
        for i in 0..n {
            if usable[i] {
                ensure!(
                    ordinal[i].is_finite()
                        && ordinal[i] >= 0.
                        && ordinal[i] < range.len() as f32
                        && width_frames[i].is_finite()
                        && width_frames[i] > 0.,
                    "invalid qualified focus fit"
                );
            }
        }
        // The sealed producer marks missing observations with flag32; therefore
        // flags==0 implies complete track coverage, not a guessed coverage value.
        out.push(FocusSlice {
            frames: range
                .clone()
                .map(|global_index| FocusFrame {
                    acquisition: global_index as u64,
                    global_index,
                })
                .collect(),
            ordinal,
            width_frames,
            flags,
            usable,
        });
    }
    Ok(out)
}
#[cfg(test)]
#[path = "focus-artifact-tests.rs"]
mod tests;
