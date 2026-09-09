use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use strehl_core::pyramid::{AdmissionMode, BaseBand, Fallback, Hull, MergeConfig, SelectMode};

use super::files::{self, FileRef, Result, require};

pub const WIDTH: u32 = 128;
pub const HEIGHT: u32 = 96;
pub const ICC_SHA: &str = "16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef";
pub const SPACE: &str = "linear-prophoto-d50";
pub const GEOMETRY: &str = "identity-common-rgb-pixels";
pub const TIFF_CAP: u64 = 256 << 10;

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema: String,
    pub grid: Grid,
    pub color: Color,
    pub noise: Noise,
    pub merge: Merge,
    pub inputs: [Input; 3],
    pub output: Output,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Grid {
    pub width: u32,
    pub height: u32,
    pub channels: String,
    pub coordinates: String,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Color {
    pub space: String,
    pub icc: FileRef,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Noise {
    pub model: String,
    pub units: String,
    pub rgb_covariance: [[f32; 3]; 3],
    pub proxy_variance: f32,
    pub band_transfer: String,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Input {
    pub id: String,
    pub tiff: FileRef,
    pub pixel_sha256: String,
    pub provenance: Provenance,
}
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Provenance {
    pub schema: String,
    pub id: String,
    pub fixture_sha256: String,
    pub color_space: String,
    pub noise_model: String,
    pub geometry: String,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Output {
    pub path: String,
    pub space: String,
    pub sample_format: String,
    pub quantization: String,
}
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Merge {
    pub bands: usize,
    pub gate: f32,
    pub exponent: f32,
    pub sharpen_per_octave: f32,
    pub select: String,
    pub admission: String,
    pub base: String,
    pub mean_coarse: usize,
    pub hull: String,
    pub hull_lambda: f32,
    pub hull_low_only: bool,
    pub fallback: String,
    pub fallback_k: usize,
    pub fallback_power: f32,
    pub hull_from_level: usize,
    pub significance_scale: f32,
}
impl Merge {
    pub fn fixed() -> Self {
        Self {
            bands: 3,
            gate: 2.0,
            exponent: 2.0,
            sharpen_per_octave: 1.4,
            select: "SoftPower".into(),
            admission: "HardFloor".into(),
            base: "Mean".into(),
            mean_coarse: 0,
            hull: "InputRange".into(),
            hull_lambda: 2.0,
            hull_low_only: false,
            fallback: "Mean".into(),
            fallback_k: 3,
            fallback_power: 4.0,
            hull_from_level: 1,
            significance_scale: 0.0,
        }
    }
    pub fn core(&self) -> Result<MergeConfig> {
        require(*self == Self::fixed(), "unsupported merge configuration")?;
        // Every field is literal: never consult MergeConfig::default/environment.
        Ok(MergeConfig {
            bands: 3,
            gate: 2.0,
            exponent: 2.0,
            sharpen_per_octave: 1.4,
            select: SelectMode::SoftPower,
            admission: AdmissionMode::HardFloor,
            base: BaseBand::Mean,
            mean_coarse: 0,
            hull: Hull::InputRange,
            hull_lambda: 2.0,
            hull_low_only: false,
            fallback: Fallback::Mean,
            fallback_k: 3,
            fallback_power: 4.0,
            hull_from_level: 1,
            significance_scale: 0.0,
        })
    }
}

pub struct Resolved {
    pub manifest: Manifest,
    pub inputs: [PathBuf; 3],
    pub profile: PathBuf,
    pub output: PathBuf,
}

pub fn parse(raw: &[u8], base: &Path, report: &Path, incomplete: &FileRef) -> Result<Resolved> {
    let m: Manifest = serde_json::from_slice(raw).map_err(|e| format!("manifest JSON: {e}"))?;
    require(
        m.schema == "common-tiff-stack-v1",
        "unsupported manifest schema",
    )?;
    require(
        m.grid.width == WIDTH
            && m.grid.height == HEIGHT
            && m.grid.channels == "RGB"
            && m.grid.coordinates == GEOMETRY,
        "unsupported common grid",
    )?;
    require(
        m.color.space == SPACE && m.color.icc.bytes == 548 && m.color.icc.sha256 == ICC_SHA,
        "unadmitted input profile",
    )?;
    require(
        m.output.space == SPACE
            && m.output.sample_format == "RGB16"
            && m.output.quantization == "finite-clamp-round-half-away-v1",
        "unsupported output semantics",
    )?;
    m.merge.core()?;
    let variance = match m.noise.model.as_str() {
        "synthetic-noiseless-v1" => 0.0,
        "synthetic-independent-rademacher8-v1" => 64.0,
        _ => return Err("unsupported noise provenance".into()),
    };
    let expected = [
        [variance, 0.0, 0.0],
        [0.0, variance, 0.0],
        [0.0, 0.0, variance],
    ];
    require(
        m.noise.units == "rgb16-code-squared"
            && m.noise.band_transfer == "core-white-bandgain-v1"
            && m.noise.rgb_covariance == expected
            && m.noise.proxy_variance == variance * 0.375,
        "unsupported noise covariance or proxy variance",
    )?;
    let profile = files::path(base, &m.color.icc.path, false)?;
    let output = files::path(base, &m.output.path, true)?;
    require(
        output.parent() == report.parent(),
        "output and report must share one plain run directory",
    )?;
    let mut names = BTreeSet::new();
    let mut paths = BTreeSet::new();
    let mut hashes = BTreeSet::new();
    let mut inputs = Vec::new();
    for input in &m.inputs {
        require(
            !input.id.is_empty()
                && input.id.len() <= 48
                && input
                    .id
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_'),
            "bounded input id",
        )?;
        require(names.insert(input.id.clone()), "duplicate input id")?;
        require(
            input.tiff.bytes > 0
                && input.tiff.bytes <= TIFF_CAP
                && files::valid_hash(&input.tiff.sha256)
                && files::valid_hash(&input.pixel_sha256),
            "typed bounded input identity",
        )?;
        require(
            hashes.insert(input.tiff.sha256.clone()),
            "duplicate whole-input identity",
        )?;
        let p = &input.provenance;
        require(
            p.schema == "common-tiff-stack-input-v1"
                && p.id == input.id
                && files::valid_hash(&p.fixture_sha256)
                && p.color_space == SPACE
                && p.noise_model == m.noise.model
                && p.geometry == GEOMETRY,
            "unsupported input provenance",
        )?;
        // This is path/metadata validation only. TIFF content is opened on its visit.
        let path = files::path(base, &input.tiff.path, false)?;
        require(paths.insert(files::key(&path)), "duplicate input path")?;
        inputs.push(path);
    }
    let mut all = paths;
    require(all.insert(files::key(&profile)), "profile/input alias")?;
    for p in [
        report.to_path_buf(),
        report.with_extension("incomplete.json"),
        report.with_extension("frame-0.json"),
        report.with_extension("frame-1.json"),
        report.with_extension("frame-2.json"),
        report.with_extension("stage.json"),
        output.clone(),
        output.with_extension("tiff-stage"),
    ] {
        require(
            all.insert(files::key(&p)),
            "input/output/receipt path collision",
        )?;
        if p == report.with_extension("incomplete.json") {
            require(
                files::key(&p) == files::key(Path::new(&incomplete.path)),
                "own incomplete path association",
            )?;
            files::read(&p, 4096, Some(incomplete))?;
        } else {
            require(!p.exists(), "declared receipt or output already exists")?;
        }
    }
    Ok(Resolved {
        manifest: m,
        inputs: inputs.try_into().map_err(|_| "three inputs")?,
        profile,
        output,
    })
}

pub fn preflight(raw: &[u8]) -> Result<()> {
    require(
        raw.len() >= 8 && &raw[..4] == b"II*\0",
        "classic little-endian TIFF header",
    )?;
    let u16_at = |at: usize| -> Result<u16> {
        Ok(u16::from_le_bytes(
            raw.get(at..at + 2)
                .ok_or("bounded TIFF SHORT")?
                .try_into()
                .unwrap(),
        ))
    };
    let u32_at = |at: usize| -> Result<u32> {
        Ok(u32::from_le_bytes(
            raw.get(at..at + 4)
                .ok_or("bounded TIFF LONG")?
                .try_into()
                .unwrap(),
        ))
    };
    let at = u32_at(4)? as usize;
    let count = u16_at(at)? as usize;
    require(
        count <= 32
            && at
                .checked_add(2 + count * 12 + 4)
                .is_some_and(|end| end <= raw.len()),
        "bounded TIFF IFD",
    )?;
    let mut seen = [false; 2];
    for i in 0..count {
        let entry = at + 2 + i * 12;
        let tag = u16_at(entry)?;
        if tag == 256 || tag == 257 {
            let slot = usize::from(tag == 257);
            require(
                !seen[slot] && u16_at(entry + 2)? == 4 && u32_at(entry + 4)? == 1,
                "unique LONG/count1 TIFF dimensions",
            )?;
            require(
                u32_at(entry + 8)? == [WIDTH, HEIGHT][slot],
                "TIFF dimensions do not match common grid",
            )?;
            seen[slot] = true;
        }
    }
    require(seen == [true, true], "TIFF dimensions absent")
}
