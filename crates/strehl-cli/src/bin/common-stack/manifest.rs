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
    pub inputs: Vec<Input>,
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

#[derive(Clone, Copy)]
pub struct Layout {
    pub width: u32,
    pub height: u32,
    pub pixels: usize,
    pub frames: usize,
    pub tiff_cap: u64,
    pub output_cap: usize,
    pub report_cap: usize,
    pub v2: bool,
}
impl Manifest {
    pub fn layout(&self) -> Result<Layout> {
        let v2 = match self.schema.as_str() {
            "common-tiff-stack-v1" => false,
            "common-tiff-stack-v2" => true,
            _ => return Err("unsupported manifest schema".into()),
        };
        let frames = self.inputs.len();
        if v2 {
            require((2..=8).contains(&frames), "v2 requires two to eight inputs")?;
        } else {
            require(frames == 3, "v1 requires exactly three inputs")?;
        }
        let (width, height) = (self.grid.width, self.grid.height);
        require(
            self.grid.channels == "RGB"
                && self.grid.coordinates == GEOMETRY
                && if v2 {
                    (64..=512).contains(&width) && (64..=512).contains(&height)
                } else {
                    width == WIDTH && height == HEIGHT
                },
            "unsupported common grid",
        )?;
        // Bounds reject huge axes first. This checked product is defensive, not
        // an independently exercised overflow branch under the admitted domain.
        let pixels = width
            .checked_mul(height)
            .ok_or("common grid extent overflow")?;
        require(pixels <= 262144, "common grid pixel capacity")?;
        let payload = u64::from(pixels)
            .checked_mul(6)
            .ok_or("RGB16 payload overflow")?;
        let tiff_cap = if v2 {
            payload.checked_add(65536).ok_or("TIFF capacity overflow")?
        } else {
            TIFF_CAP
        };
        let output_cap = if v2 { tiff_cap as usize } else { 128 << 10 };
        Ok(Layout {
            width,
            height,
            pixels: pixels as usize,
            frames,
            tiff_cap,
            output_cap,
            report_cap: if v2 { 192 << 10 } else { 64 << 10 },
            v2,
        })
    }
}

pub struct Resolved {
    pub manifest: Manifest,
    pub inputs: Vec<PathBuf>,
    pub layout: Layout,
    pub profile: PathBuf,
    pub output: PathBuf,
}

pub fn parse(raw: &[u8], base: &Path, report: &Path, incomplete: &FileRef) -> Result<Resolved> {
    let m: Manifest = serde_json::from_slice(raw).map_err(|e| format!("manifest JSON: {e}"))?;
    let layout = m.layout()?;
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
    let mut inputs = Vec::with_capacity(layout.frames);
    let mut input_bytes = 0u64;
    let input_capacity = layout
        .tiff_cap
        .checked_mul(layout.frames as u64)
        .ok_or("aggregate input capacity overflow")?;
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
                && input.tiff.bytes <= layout.tiff_cap
                && files::valid_hash(&input.tiff.sha256)
                && files::valid_hash(&input.pixel_sha256),
            "typed bounded input identity",
        )?;
        input_bytes = input_bytes
            .checked_add(input.tiff.bytes)
            .ok_or("aggregate input extent overflow")?;
        require(input_bytes <= input_capacity, "aggregate input capacity")?;
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
    let mut outputs = vec![
        report.to_path_buf(),
        report.with_extension("incomplete.json"),
    ];
    outputs.extend((0..layout.frames).map(|i| report.with_extension(format!("frame-{i}.json"))));
    outputs.extend([
        report.with_extension("stage.json"),
        output.clone(),
        output.with_extension("tiff-stage"),
    ]);
    for p in outputs {
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
        inputs,
        layout,
        profile,
        output,
    })
}

pub fn preflight(raw: &[u8], layout: &Layout) -> Result<()> {
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
                u32_at(entry + 8)? == [layout.width, layout.height][slot],
                "TIFF dimensions do not match common grid",
            )?;
            seen[slot] = true;
        }
    }
    require(seen == [true, true], "TIFF dimensions absent")
}
