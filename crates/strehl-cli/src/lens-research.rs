//! Default-off, hash-bound nonlinear lens research. No calibration/quality claim.
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use crate::align_cmd::{CoverFit, CoverMode, CropRect};
use anyhow::{Context, Result, ensure};
use clap::{Args as ClapArgs, Subcommand, ValueEnum};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use strehl_core::align::{Resampler, Similarity};
use strehl_core::plane::PlaneGeometry;
use strehl_core::warpmap::{StackIdentity, WarpMap};

#[cfg(test)]
use crate::align_cmd::EdgeReceipt;
pub(crate) use crate::align_cmd::{
    FramePull, NativeSimilarity, RadialCurve, ResearchPull, SolveReceipt, native_placement,
    native_similarity,
};

pub(crate) const ENV: &str = "STREHL_RESEARCH_LENS_MAP";
const MAGIC: &str = "strehl-lens-warp-research";
const VERSION: u32 = 1;
const CONVENTION: &str = "signed16-linear-radius-16384-forward-native-v1";
const ARITHMETIC: &str = "f32-compensated-chain-guide-center-half-pixel-v2";
const MARGIN: f32 = 6.0;
const GUIDE_POLICY: &str = "green-luma; native-center=2*(u+crop)+.5; CatmullRom; common symmetric certified crop; no extension";

#[derive(ClapArgs)]
pub(crate) struct Args {
    #[command(subcommand)]
    action: Action,
}
#[derive(Subcommand)]
enum Action {
    /// Emit exact runtime f32 bits for independent numerical commissioning; no RAW reads.
    NumericProjection {
        #[arg(long)]
        input: PathBuf,
    },
    /// Validate an external optical manifest and fit new virtual-guide geometry.
    Prepare {
        dir: PathBuf,
        #[arg(long)]
        manifest: PathBuf,
        #[arg(long)]
        out: PathBuf,
        #[arg(long, value_enum)]
        arm: Arm,
        #[arg(long, default_value_t = 4)]
        threads: usize,
    },
    /// Certify one common crop and write new envelopes outside the input corpora.
    CommonCrop {
        #[arg(long, num_args = 2..)]
        maps: Vec<PathBuf>,
        #[arg(long)]
        out_dir: PathBuf,
    },
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize, ValueEnum)]
#[serde(rename_all = "kebab-case")]
pub(crate) enum Arm {
    ForcedZero,
    AnchorFixed,
    PerFrame,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct CurveSpec {
    center: [f32; 2],
    reference_radius: f32,
    input_scale: f32,
    output_scale: f32,
    max_input_radius: f32,
    knots: [i16; 16],
}
impl CurveSpec {
    fn curve(&self) -> RadialCurve {
        RadialCurve {
            center: self.center,
            reference_radius: self.reference_radius,
            input_scale: self.input_scale,
            output_scale: self.output_scale,
            max_input_radius: self.max_input_radius,
            knots: self.knots,
        }
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Source {
    filename: String,
    bytes: u64,
    modified_unix_ns: u128,
    sha256: String,
    body: String,
    firmware: String,
    lens_type3: u16,
    active_origin: [usize; 2],
    active_size: [usize; 2],
    default_crop: [usize; 4],
    cfa: String,
    black: f32,
    white: f32,
    iso: Option<f32>,
    distortion_setting: i32,
    curve: CurveSpec,
}
/// External metadata is trusted only as an explicit, immutable hypothesis bound
/// to complete source hashes. The prototype does not pretend to parse/calibrate it.
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Manifest {
    magic: String,
    version: u32,
    convention: String,
    radial_center_convention: String,
    placement_status: String,
    metadata_extractor: String,
    metadata_evidence: String,
    sources: Vec<Source>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Payload {
    manifest: Manifest,
    manifest_sha256: String,
    arm: Arm,
    build: String,
    binary_sha256: String,
    input_root: PathBuf,
    warp_text: String,
    solve: SolveReceipt,
    ca: Vec<[[f64; 4]; 3]>,
    crop: Option<[usize; 4]>,
    crop_peer_payloads: Vec<String>,
    crop_peer_arms: Vec<Arm>,
    coverage: String,
    arithmetic: String,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope {
    magic: String,
    version: u32,
    payload: Payload,
    payload_sha256: String,
    complete: String,
}

pub(crate) struct RuntimeMap {
    map: WarpMap,
    manifest: Manifest,
    pulls: Vec<FramePull>,
    crop: CropRect,
    envelope: serde_json::Value,
}
impl RuntimeMap {
    pub(crate) fn map(&self) -> &WarpMap {
        &self.map
    }
    pub(crate) fn envelope(&self) -> &serde_json::Value {
        &self.envelope
    }
    pub(crate) fn pull(&self, index: usize) -> Result<&FramePull> {
        self.pulls.get(index).context("research pull index missing")
    }
    pub(crate) fn fit(&self) -> CoverFit {
        CoverFit::Cropped {
            k: self.crop.width as f64 / self.map.geometry().width as f64,
            rect: self.crop,
        }
    }
    pub(crate) fn validate_frame(&self, index: usize, frame: &strehl_raw::Frame) -> Result<()> {
        self.manifest.validate_frame(index, frame)
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn digest(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}
fn file_digest(path: &Path) -> Result<String> {
    let mut f = fs::File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1024 * 1024];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(hex(&h.finalize()))
}
fn payload_digest(p: &Payload) -> Result<String> {
    Ok(digest(&serde_json::to_vec(p)?))
}
fn valid_digest(s: &str) -> bool {
    s.len() == 64
        && s.bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
impl Manifest {
    pub(crate) fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.sources[0].active_size[0] / 2,
            height: self.sources[0].active_size[1] / 2,
        }
    }
    fn validate(&self) -> Result<()> {
        ensure!(
            self.magic == "strehl-lens-optical-manifest" && self.version == VERSION,
            "unsupported research optical manifest"
        );
        ensure!(
            self.convention == CONVENTION,
            "unsupported radial convention"
        );
        ensure!(
            self.radial_center_convention == "default-crop-pixel-center-midpoint",
            "unsupported radial center convention"
        );
        ensure!(
            self.placement_status == "unverified",
            "prototype cannot assert verified placement"
        );
        ensure!(
            !self.metadata_extractor.is_empty() && !self.metadata_evidence.is_empty(),
            "manifest must identify its metadata extraction and evidence"
        );
        ensure!(
            self.sources.len() >= 3,
            "manifest requires a cyclic stack of at least three sources"
        );
        let first = &self.sources[0];
        let mut names = std::collections::BTreeSet::new();
        for (i, s) in self.sources.iter().enumerate() {
            ensure!(
                Path::new(&s.filename).file_name().and_then(|v| v.to_str())
                    == Some(s.filename.as_str())
                    && names.insert(&s.filename),
                "invalid/duplicate source filename {i}"
            );
            ensure!(
                s.bytes > 0 && valid_digest(&s.sha256),
                "invalid source hash/size {i}"
            );
            ensure!(
                s.body == "ILCE-7CM2" && !s.firmware.is_empty() && s.lens_type3 != 0,
                "unsupported/missing body, firmware or lens identity {i}"
            );
            ensure!(
                s.active_size == first.active_size
                    && s.active_size.iter().all(|v| *v >= 16 && v % 2 == 0)
                    && s.cfa == "RGGB",
                "unsupported active geometry/CFA {i}"
            );
            ensure!(
                s.black.is_finite()
                    && s.white.is_finite()
                    && s.white > s.black
                    && s.iso.is_some_and(|v| v.is_finite() && v > 0.0),
                "missing/invalid levels/ISO {i}"
            );
            ensure!(
                s.black == first.black
                    && s.white == first.white
                    && s.iso == first.iso
                    && s.firmware == first.firmware
                    && s.lens_type3 == first.lens_type3,
                "research bracket requires identical sensor levels, known ISO, firmware and lens {i}"
            );
            let [x, y, w, h] = s.default_crop;
            ensure!(
                w > 0
                    && h > 0
                    && x.checked_add(w).is_some_and(|v| v <= s.active_size[0])
                    && y.checked_add(h).is_some_and(|v| v <= s.active_size[1]),
                "invalid default crop {i}"
            );
            ensure!(
                s.curve.center
                    == [
                        x as f32 + (w - 1) as f32 * 0.5,
                        y as f32 + (h - 1) as f32 * 0.5
                    ],
                "radial center does not match declared crop center {i}"
            );
            s.curve
                .curve()
                .validate()
                .map_err(anyhow::Error::msg)
                .with_context(|| format!("radial curve {i}"))?;
        }
        Ok(())
    }
    fn bind_files(&self, paths: &[PathBuf]) -> Result<()> {
        self.validate()?;
        ensure!(
            paths.len() == self.sources.len(),
            "manifest/source count mismatch"
        );
        for (i, (s, p)) in self.sources.iter().zip(paths).enumerate() {
            ensure!(
                p.file_name().and_then(|v| v.to_str()) == Some(s.filename.as_str()),
                "source order mismatch {i}"
            );
            let md = fs::metadata(p)?;
            ensure!(
                md.len() == s.bytes
                    && md.modified()?.duration_since(UNIX_EPOCH)?.as_nanos() == s.modified_unix_ns,
                "source stat identity changed {i}"
            );
            ensure!(file_digest(p)? == s.sha256, "source SHA256 mismatch {i}");
        }
        Ok(())
    }
    fn bind(&self, paths: &[PathBuf]) -> Result<()> {
        self.bind_files(paths)?;
        for (i, (s, p)) in self.sources.iter().zip(paths).enumerate() {
            let id = strehl_raw::identity(p);
            ensure!(
                id.model.as_deref() == Some(s.body.as_str()) && id.lens_type3 == Some(s.lens_type3),
                "source body/lens metadata mismatch {i}"
            );
        }
        Ok(())
    }
    pub(crate) fn validate_frame(&self, index: usize, f: &strehl_raw::Frame) -> Result<()> {
        let s = self
            .sources
            .get(index)
            .context("missing decoded frame identity")?;
        ensure!(
            [f.active.x, f.active.y] == s.active_origin
                && [f.active.width, f.active.height] == s.active_size,
            "decoded active area differs from manifest at {index}"
        );
        ensure!(
            f.levels.black == s.black && f.levels.white == s.white && f.iso == s.iso,
            "decoded levels/ISO differ from manifest at {index}"
        );
        Ok(())
    }
    fn curves(&self, arm: Arm) -> Result<Vec<RadialCurve>> {
        let curves = self
            .sources
            .iter()
            .map(|s| s.curve.curve())
            .collect::<Vec<_>>();
        curves_for_arm(&curves, self.sources.len() / 2, arm)
    }
    fn guide_crop_array(&self) -> Result<[usize; 4]> {
        let r = self.guide_crop()?;
        Ok([r.x, r.y, r.width, r.height])
    }
    pub(crate) fn guide_crop(&self) -> Result<CropRect> {
        guide_crop_for_curves(self.geometry(), &self.curves(Arm::PerFrame)?)
    }
    fn ca(&self) -> Result<Vec<[[f64; 4]; 3]>> {
        use strehl_core::optics::{OpticalProfile, cfa_site_channel, profile_for_capture_env};
        self.sources
            .iter()
            .map(|s| {
                let p = profile_for_capture_env(Some(&s.body), Some(s.lens_type3))?;
                Ok([(0, 0), (1, 0), (1, 1)].map(|(x, y)| {
                    let t =
                        OpticalProfile::compose(p, cfa_site_channel(x, y), Similarity::IDENTITY)
                            .to_params();
                    [t.ax, t.ay, t.g, t.rot]
                }))
            })
            .collect()
    }
}

/// Common guide support across original per-frame curves and forced zero.
/// Anchor-fixed uses one of the same original curves, so it is already covered.
pub(crate) fn guide_crop_for_curves(g: PlaneGeometry, curves: &[RadialCurve]) -> Result<CropRect> {
    ensure!(
        g.width > 0 && g.height > 0 && !curves.is_empty(),
        "empty research guide geometry/curves"
    );
    let identity = RadialCurve {
        center: [g.width as f32, g.height as f32],
        reference_radius: 1.0,
        input_scale: 1.0,
        output_scale: 1.0,
        max_input_radius: (2 * (g.width + g.height)) as f32,
        knots: [0; 16],
    };
    let t = native_similarity(Similarity::IDENTITY, g);
    let curves =
        curves
            .iter()
            .copied()
            .chain(curves_for_arm(curves, curves.len() / 2, Arm::ForcedZero)?);
    let pulls: Vec<_> = curves
        .map(|source| ResearchPull {
            anchor: identity,
            source,
            placement: t,
        })
        .collect();
    let rect = |inset| CropRect {
        x: inset,
        y: inset,
        width: g.width - 2 * inset,
        height: g.height - 2 * inset,
    };
    let admitted = |r: CropRect| {
        let native = [
            (2 * r.x) as f32 + 0.5,
            (2 * r.y) as f32 + 0.5,
            (2 * (r.x + r.width - 1)) as f32 + 0.5,
            (2 * (r.y + r.height - 1)) as f32 + 0.5,
        ];
        pulls
            .iter()
            .all(|p| p.covers(native, [2 * g.width, 2 * g.height], 4.0, t))
    };
    let mut lo = 0;
    let mut hi = (g.width.min(g.height) - 1) / 2;
    ensure!(
        admitted(rect(hi)),
        "no conservative common virtual-guide crop"
    );
    while lo < hi {
        let mid = (lo + hi) / 2;
        if admitted(rect(mid)) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    Ok(rect(lo))
}

/// The actual experiment-arm dispatch, shared by preparation and its controls.
pub(crate) fn curves_for_arm(
    curves: &[RadialCurve],
    reference: usize,
    arm: Arm,
) -> Result<Vec<RadialCurve>> {
    ensure!(reference < curves.len(), "research curve anchor is missing");
    for curve in curves {
        curve.validate().map_err(anyhow::Error::msg)?;
    }
    curves
        .iter()
        .map(|curve| {
            let selected = match arm {
                Arm::PerFrame => *curve,
                Arm::AnchorFixed => curves[reference],
                Arm::ForcedZero => RadialCurve {
                    knots: [0; 16],
                    input_scale: 1.0,
                    output_scale: 1.0,
                    ..*curve
                },
            };
            selected.validate().map_err(anyhow::Error::msg)?;
            Ok(selected)
        })
        .collect()
}

fn load(path: &Path) -> Result<Envelope> {
    parse_envelope(&fs::read(path)?)
        .with_context(|| format!("reading research envelope {}", path.display()))
}
fn parse_envelope(bytes: &[u8]) -> Result<Envelope> {
    let e: Envelope = serde_json::from_slice(bytes)?;
    ensure!(
        e.magic == MAGIC && e.version == VERSION && e.complete == "end",
        "unsupported/incomplete research envelope"
    );
    ensure!(
        valid_digest(&e.payload_sha256) && payload_digest(&e.payload)? == e.payload_sha256,
        "research envelope checksum mismatch"
    );
    e.payload.manifest.validate()?;
    ensure!(
        e.payload.manifest_sha256 == digest(&serde_json::to_vec(&e.payload.manifest)?)
            && valid_digest(&e.payload.binary_sha256)
            && !e.payload.build.is_empty()
            && e.payload.input_root.is_absolute(),
        "research source/build identity is incomplete"
    );
    ensure!(
        e.payload.binary_sha256 == file_digest(&std::env::current_exe()?)?
            && e.payload.build == env!("STREHL_BUILD_ID"),
        "research envelope requires the exact preparing executable"
    );
    ensure!(
        e.payload.arithmetic == ARITHMETIC
            && e.payload.coverage == "radial-bound-ca-after-pull-margin6-v1",
        "unsupported research arithmetic/coverage version"
    );
    Ok(e)
}
fn save(path: &Path, payload: Payload) -> Result<()> {
    let e = Envelope {
        magic: MAGIC.into(),
        version: VERSION,
        payload_sha256: payload_digest(&payload)?,
        payload,
        complete: "end".into(),
    };
    let mut f = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .with_context(|| format!("creating new research envelope {}", path.display()))?;
    f.write_all(&serde_json::to_vec_pretty(&e)?)?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
fn outside_corpus(out: &Path, dir: &Path) -> Result<()> {
    let parent = out
        .parent()
        .context("research output needs a parent directory")?
        .canonicalize()?;
    ensure!(
        !parent.starts_with(dir.canonicalize()?),
        "research output must be outside capture corpus"
    );
    Ok(())
}
pub(crate) fn validate_solve(s: &SolveReceipt, n: usize) -> Result<()> {
    ensure!(
        n >= 3
            && s.reference == n / 2
            && s.threads > 0
            && s.smooth == 1.0
            && s.smooth_huber == 1.0
            && s.weighting == "unit"
            && s.guide_policy == GUIDE_POLICY,
        "unsupported research solver/gauge policy"
    );
    let mut expected = Vec::new();
    for span in crate::align_cmd::DEFAULT_SPANS {
        for i in 0..n.saturating_sub(span) {
            expected.push([i, i + span]);
        }
    }
    expected.sort_unstable();
    expected.dedup();
    ensure!(
        s.requested_pairs == expected,
        "research receipt changed the requested direct-pair ladder"
    );
    let mut accepted = std::collections::BTreeSet::new();
    let mut connected = vec![false; n];
    connected[s.reference] = true;
    for e in &s.accepted_edges {
        ensure!(
            e.pair[0] < e.pair[1]
                && e.pair[1] < n
                && expected.binary_search(&e.pair).is_ok()
                && accepted.insert(e.pair),
            "invalid, duplicate or unrequested research edge"
        );
        ensure!(
            e.transform.iter().all(|v| v.is_finite())
                && e.rms.is_finite()
                && e.rms >= 0.0
                && e.lever.is_finite()
                && e.lever > 0.0
                && e.used > 0,
            "invalid research edge diagnostics"
        );
    }
    loop {
        let mut changed = false;
        for [i, j] in &accepted {
            if connected[*i] != connected[*j] {
                connected[*i] = true;
                connected[*j] = true;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    ensure!(
        connected.iter().all(|v| *v)
            && accepted.len() >= n
            && s.cycle_rank == accepted.len() + 1 - n,
        "research graph is disconnected or not cyclic"
    );
    let [_, _, width, height] = s.guide_crop;
    let mut opts = strehl_core::align::GlobalOptions::new(PlaneGeometry { width, height });
    opts.weighting = strehl_core::align::Weighting::Unit;
    opts.smooth = 1.0;
    opts.smooth_huber_px = Some(1.0);
    ensure!(
        s.pair_config == format!("{:?}", strehl_core::align::AlignConfig::deep())
            && s.global_config == format!("{opts:?}"),
        "research solver configuration changed since preparation"
    );
    Ok(())
}
fn reconstruct(p: &Payload) -> Result<(WarpMap, Vec<FramePull>)> {
    let map = WarpMap::from_text(&p.warp_text)?;
    let n = p.manifest.sources.len();
    ensure!(
        map.len() == n
            && map.geometry() == p.manifest.geometry()
            && map.resampler() == Resampler::CatmullRom
            && map.provenance().reference == n / 2
            && p.solve.reference == n / 2
            && p.ca.len() == n,
        "research envelope map/source/gauge mismatch"
    );
    validate_solve(&p.solve, n)?;
    ensure!(
        p.solve.guide_crop == p.manifest.guide_crop_array()?,
        "research guide crop changed"
    );
    ensure!(
        map.placement(n / 2)? == Similarity::IDENTITY,
        "research anchor is not exact identity"
    );
    let curves = p.manifest.curves(p.arm)?;
    let geom = map.geometry();
    let [x, y, width, height] = p.crop.unwrap_or([0, 0, geom.width, geom.height]);
    ensure!(
        width > 0
            && height > 0
            && x.checked_add(width).is_some_and(|v| v <= geom.width)
            && y.checked_add(height).is_some_and(|v| v <= geom.height),
        "invalid research crop"
    );
    let crop = CropRect {
        x,
        y,
        width,
        height,
    };
    let mut pulls = Vec::with_capacity(n);
    for i in 0..n {
        let geometry = ResearchPull {
            anchor: curves[n / 2],
            source: curves[i],
            placement: native_placement(map.placement(i)?, geom),
        };
        geometry.validate().map_err(anyhow::Error::msg)?;
        let ca = p.ca[i].map(|v| {
            native_similarity(
                Similarity::from_params(strehl_core::align::SimilarityParams {
                    ax: v[0],
                    ay: v[1],
                    g: v[2],
                    rot: v[3],
                }),
                geom,
            )
        });
        for c in ca {
            c.validate().map_err(anyhow::Error::msg)?;
        }
        pulls.push(FramePull::new(geometry, ca, crop)?);
    }
    Ok((map, pulls))
}
fn rect_native(r: CropRect) -> [f32; 4] {
    [
        (2 * r.x) as f32,
        (2 * r.y) as f32,
        (2 * (r.x + r.width) - 1) as f32,
        (2 * (r.y + r.height) - 1) as f32,
    ]
}
fn covered(pulls: &[FramePull], r: CropRect, geom: PlaneGeometry) -> bool {
    pulls.iter().all(|p| {
        p.ca.iter().all(|&ca| {
            p.geometry.covers(
                rect_native(r),
                [2 * geom.width, 2 * geom.height],
                MARGIN,
                ca,
            )
        })
    })
}

fn validate_modes(
    backend: crate::merge_cmd::MergeBackend,
    cover: CoverMode,
    resampler: Resampler,
    repairs: bool,
    subset: bool,
    fullres: bool,
) -> Result<()> {
    ensure!(
        backend == crate::merge_cmd::MergeBackend::Pyramid && cover == CoverMode::Crop,
        "research lens map requires normal CPU pyramid with --cover crop"
    );
    ensure!(
        resampler == Resampler::CatmullRom && !repairs && !subset,
        "research lens map refuses alternate resamplers, source repairs and source subsets"
    );
    ensure!(
        fullres,
        "research lens map requires fullres source reconstruction"
    );
    Ok(())
}
fn validate_defects(request: &crate::stack::DefectRequest) -> Result<()> {
    ensure!(
        matches!(request, crate::stack::DefectRequest::Off),
        "research lens map refuses sensor-defect repair, including map-only requests"
    );
    Ok(())
}
fn validate_overrides(get: impl Fn(&str) -> Option<std::ffi::OsString>) -> Result<()> {
    for key in [
        "STREHL_DIRECT_PLANES",
        "STREHL_GPU_GATHER",
        "STREHL_LOCAL_PLACEMENT_FILE",
        "STREHL_TEMPORAL_ENERGY",
        "STREHL_SPATIAL_NOISE_FLOOR",
        "STREHL_RESTORE",
        "STREHL_ONLY_FRAME",
        "STREHL_GATE_FLOOR_SCALE",
        "STREHL_GATE_FLOOR",
        "STREHL_ALIGN",
        "STREHL_ACUITY",
        "STREHL_FIX_HALO",
        "STREHL_VEIL",
        "STREHL_EDGE_AWARE",
        "STREHL_SMOOTH",
        "STREHL_SMOOTH_HUBER",
    ] {
        if let Some(v) = get(key) {
            ensure!(
                matches!(v.to_str(), Some("off" | "0"))
                    && key != "STREHL_ALIGN"
                    && key != "STREHL_GATE_FLOOR"
                    && key != "STREHL_GATE_FLOOR_SCALE"
                    && key != "STREHL_ONLY_FRAME"
                    && key != "STREHL_LOCAL_PLACEMENT_FILE"
                    && key != "STREHL_SMOOTH"
                    && key != "STREHL_SMOOTH_HUBER",
                "research lens map refuses {key}={v:?}"
            );
        }
    }
    Ok(())
}
pub(crate) fn preflight(opts: &crate::merge_cmd::MergeOptions) -> Result<()> {
    if std::env::var_os(ENV).is_none() {
        return Ok(());
    }
    validate_modes(
        opts.backend,
        opts.cover,
        opts.resampler,
        opts.region_recipe.is_some(),
        opts.limit.is_some(),
        crate::align_cmd::fullres_gather_enabled(),
    )?;
    validate_defects(&crate::stack::defect_request_from_env()?)?;
    validate_overrides(|key| std::env::var_os(key))?;
    ensure!(
        !cfg!(feature = "native-green-cue") && !cfg!(feature = "native-boundary-radiance"),
        "research lens prototype refuses green-cue/boundary-radiance feature builds"
    );
    Ok(())
}
fn validate_common_crop(p: &Payload) -> Result<()> {
    ensure!(
        p.crop.is_some(),
        "research envelope needs an explicitly certified common crop"
    );
    let peers = &p.crop_peer_payloads;
    let arms = &p.crop_peer_arms;
    ensure!(
        peers.len() >= 2
            && peers.len() == arms.len()
            && peers.iter().all(|h| valid_digest(h))
            && peers
                .iter()
                .collect::<std::collections::BTreeSet<_>>()
                .len()
                == peers.len()
            && arms.iter().collect::<std::collections::BTreeSet<_>>().len() == arms.len(),
        "research common-crop receipt requires distinct bound arms"
    );
    let mut original = p.clone();
    original.crop = None;
    original.crop_peer_payloads.clear();
    original.crop_peer_arms.clear();
    let own_digest = payload_digest(&original)?;
    ensure!(
        peers
            .iter()
            .zip(arms)
            .any(|(h, a)| h == &own_digest && *a == p.arm),
        "research common-crop receipt does not bind this original arm"
    );
    Ok(())
}
pub(crate) fn load_for_render(paths: &[PathBuf]) -> Result<Option<RuntimeMap>> {
    let Some(path) = std::env::var_os(ENV) else {
        return Ok(None);
    };
    let path = PathBuf::from(path);
    let legacy = std::env::var_os("STREHL_WARPMAP")
        .context("research envelope must also be named by STREHL_WARPMAP")?;
    ensure!(
        path.canonicalize()? == PathBuf::from(legacy).canonicalize()?,
        "research and legacy map environment paths disagree"
    );
    let e = load(&path)?;
    validate_common_crop(&e.payload)?;
    ensure!(
        paths
            .first()
            .and_then(|p| p.parent())
            .context("empty research stack")?
            .canonicalize()?
            == e.payload.input_root,
        "research map corpus root differs from current input"
    );
    e.payload.manifest.bind(paths)?;
    ensure!(
        e.payload.manifest.ca()? == e.payload.ca,
        "fixed CA profile changed since solve"
    );
    let (map, pulls) = reconstruct(&e.payload)?;
    let crop = pulls[0].crop;
    ensure!(
        covered(&pulls, crop, map.geometry()),
        "common crop no longer has a coverage certificate"
    );
    let name = paths[0]
        .parent()
        .and_then(Path::file_name)
        .context("input directory name")?
        .to_string_lossy();
    map.check_stack(&strehl_core::warpmap::StackIdentity::from_paths(
        &name, paths,
    )?)?;
    eprintln!(
        "research lens   : {:?}; placement UNVERIFIED; f32 pull; {} source hashes; envelope {}",
        e.payload.arm,
        paths.len(),
        e.payload_sha256
    );
    let envelope = serde_json::to_value(&e)?;
    Ok(Some(RuntimeMap {
        map,
        manifest: e.payload.manifest,
        pulls,
        crop,
        envelope,
    }))
}

fn curve_bits(curve: RadialCurve) -> serde_json::Value {
    serde_json::json!({
        "center_bits":curve.center.map(f32::to_bits),
        "reference_radius_bits":curve.reference_radius.to_bits(),
        "input_scale_bits":curve.input_scale.to_bits(),
        "output_scale_bits":curve.output_scale.to_bits(),
        "max_input_radius_bits":curve.max_input_radius.to_bits(),
        "knots":curve.knots,
    })
}
fn similarity_bits(t: NativeSimilarity) -> serde_json::Value {
    serde_json::json!({"a":t.a.map(f32::to_bits),"b":t.b.map(f32::to_bits),"center":t.center.map(f32::to_bits)})
}
fn numeric_projection(bytes: &[u8]) -> Result<serde_json::Value> {
    let header: serde_json::Value = serde_json::from_slice(bytes)?;
    let (kind, manifest, arms) = match header.get("magic").and_then(serde_json::Value::as_str) {
        Some("strehl-lens-optical-manifest") => {
            let manifest: Manifest = serde_json::from_slice(bytes)?;
            manifest.validate()?;
            let reference = manifest.sources.len() / 2;
            let arms = [Arm::ForcedZero, Arm::AnchorFixed, Arm::PerFrame]
                .into_iter()
                .map(|arm| {
                    Ok(serde_json::json!({"arm":arm,"reference":reference,
                    "curves":manifest.curves(arm)?.into_iter().map(curve_bits).collect::<Vec<_>>(),
                    "pulls":[]}))
                })
                .collect::<Result<Vec<_>>>()?;
            ("manifest", manifest, arms)
        }
        Some(MAGIC) => {
            let envelope = parse_envelope(bytes)?;
            let p = &envelope.payload;
            let (map, pulls) = reconstruct(p)?;
            if p.crop.is_some() {
                validate_common_crop(p)?;
                ensure!(
                    covered(&pulls, pulls[0].crop, map.geometry()),
                    "numeric projection crop has no coverage certificate"
                );
            }
            let native_rect = p.crop.map(|_| rect_native(pulls[0].crop).map(f32::to_bits));
            let projected = pulls
                .iter()
                .enumerate()
                .map(|(index, pull)| {
                    serde_json::json!({
                        "source_index":index,
                        "placement_bits":similarity_bits(pull.geometry.placement),
                        "ca_bits":pull.ca.map(similarity_bits),
                        "rect_bits":native_rect,
                        "source_size":p.manifest.sources[index].active_size,
                        "margin_bits":MARGIN.to_bits(),
                    })
                })
                .collect::<Vec<_>>();
            let arm = serde_json::json!({"arm":p.arm,"reference":map.provenance().reference,
                "curves":p.manifest.curves(p.arm)?.into_iter().map(curve_bits).collect::<Vec<_>>(),
                "pulls":projected});
            ("envelope", envelope.payload.manifest, vec![arm])
        }
        _ => anyhow::bail!("numeric projection requires a supported manifest or research envelope"),
    };
    Ok(serde_json::json!({
        "schema":"strehl-lens-numeric-projection-v1","kind":kind,"arithmetic":ARITHMETIC,
        "input_sha256":digest(bytes),"input_bytes":bytes.len(),
        "geometry_source_sha256":digest(include_bytes!("lens-research-geometry.rs")),
        "integration_source_sha256":digest(include_bytes!("lens-research.rs")),
        "alignment_source_sha256":digest(include_bytes!("align_cmd.rs")),
        "binary_sha256":file_digest(&std::env::current_exe()?)?,"build":env!("STREHL_BUILD_ID"),
        "ordered_source_sha256":manifest.sources.iter().map(|s|&s.sha256).collect::<Vec<_>>(),
        "active_size":manifest.sources[0].active_size,"arms":arms,
    }))
}

/// Research-only fresh direct-pair/global refit in virtual undistorted guides.
/// No legacy cache is read or written. All frames must have measured cyclic support.
#[cfg(feature = "research-lens-warp")]
pub(crate) fn solve_lens_research(
    dir: &Path,
    paths: &[PathBuf],
    manifest: &Manifest,
    curves: &[RadialCurve],
    threads: usize,
) -> Result<(WarpMap, SolveReceipt)> {
    ensure!(
        !crate::align_cmd::is_tilted_subject(dir),
        "research lens solve refuses known tilted subjects"
    );
    let n = paths.len();
    ensure!(
        n >= 3 && curves.len() == n,
        "research solve needs at least three bound sources"
    );
    let full = manifest.geometry();
    let crop = manifest.guide_crop()?;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let planes = pool.install(|| {
        paths
            .par_iter()
            .enumerate()
            .map(|(index, path)| {
                let raw = strehl_raw::decode(path)?;
                manifest.validate_frame(index, &raw)?;
                crate::align_cmd::lens_guide(&raw, curves[index], full, crop)
            })
            .collect::<Result<Vec<_>>>()
    })?;
    let name = dir
        .file_name()
        .context("research input has no directory name")?
        .to_string_lossy();
    crate::align_cmd::solve_lens_guides(
        StackIdentity::from_paths(&name, paths)?,
        full,
        crop,
        planes,
        threads,
    )
}

pub(crate) fn run(args: &Args) -> Result<()> {
    match &args.action {
        Action::NumericProjection { input } => {
            let bytes = fs::read(input)?;
            println!(
                "{}",
                serde_json::to_string_pretty(&numeric_projection(&bytes)?)?
            );
        }
        Action::Prepare {
            dir,
            manifest,
            out,
            arm,
            threads,
        } => {
            ensure!(*threads > 0, "threads must be positive");
            ensure!(
                std::env::var_os(ENV).is_none() && std::env::var_os("STREHL_WARPMAP").is_none(),
                "prepare refuses preexisting map environment selectors"
            );
            for key in ["STREHL_SMOOTH", "STREHL_SMOOTH_HUBER"] {
                ensure!(
                    std::env::var_os(key).is_none(),
                    "research solver has frozen defaults; unset {key}"
                );
            }
            outside_corpus(out, dir)?;
            ensure!(!out.exists(), "research map output already exists");
            let bytes = fs::read(manifest)?;
            let manifest: Manifest = serde_json::from_slice(&bytes)?;
            let paths = crate::raw_paths(dir, None)?;
            manifest.bind(&paths)?;
            let curves = manifest.curves(*arm)?;
            let ca = manifest.ca()?;
            let (map, solve) = solve_lens_research(dir, &paths, &manifest, &curves, *threads)?;
            let manifest_sha256 = digest(&serde_json::to_vec(&manifest)?);
            save(
                out,
                Payload {
                    manifest,
                    manifest_sha256,
                    arm: *arm,
                    build: env!("STREHL_BUILD_ID").into(),
                    binary_sha256: file_digest(&std::env::current_exe()?)?,
                    input_root: dir.canonicalize()?,
                    warp_text: map.to_text(),
                    solve,
                    ca,
                    crop: None,
                    crop_peer_payloads: Vec::new(),
                    crop_peer_arms: Vec::new(),
                    coverage: "radial-bound-ca-after-pull-margin6-v1".into(),
                    arithmetic: ARITHMETIC.into(),
                },
            )?;
        }
        Action::CommonCrop { maps, out_dir } => {
            ensure!(maps.len() >= 2, "common crop needs at least two maps");
            let envelopes = maps.iter().map(|p| load(p)).collect::<Result<Vec<_>>>()?;
            ensure!(
                envelopes.iter().all(|e| e.payload.crop.is_none()
                    && e.payload.crop_peer_payloads.is_empty()
                    && e.payload.crop_peer_arms.is_empty()),
                "common crop requires original unsealed maps"
            );
            ensure!(
                envelopes
                    .iter()
                    .map(|e| e.payload.arm)
                    .collect::<std::collections::BTreeSet<_>>()
                    .len()
                    == envelopes.len()
                    && envelopes
                        .iter()
                        .map(|e| &e.payload_sha256)
                        .collect::<std::collections::BTreeSet<_>>()
                        .len()
                        == envelopes.len(),
                "common crop refuses duplicate payloads or arm identities"
            );
            let mut all = Vec::new();
            let mut geom = None;
            let identity = serde_json::to_vec(&envelopes[0].payload.manifest)?;
            let input_root = &envelopes[0].payload.input_root;
            let ca = &envelopes[0].payload.ca;
            for e in &envelopes {
                ensure!(
                    serde_json::to_vec(&e.payload.manifest)? == identity
                        && &e.payload.ca == ca
                        && &e.payload.input_root == input_root,
                    "common-crop arms differ in source/optical identity or fixed CA"
                );
                let (m, p) = reconstruct(&e.payload)?;
                geom = Some(m.geometry());
                all.extend(p);
            }
            let g = geom.context("no common-crop geometry")?;
            let rect = |inset: usize| CropRect {
                x: inset,
                y: inset,
                width: g.width - 2 * inset,
                height: g.height - 2 * inset,
            };
            let mut lo = 0;
            let mut hi = (g.width.min(g.height) - 1) / 2;
            ensure!(
                covered(&all, rect(hi), g),
                "no conservative nonempty common crop"
            );
            while lo < hi {
                let mid = (lo + hi) / 2;
                if covered(&all, rect(mid), g) {
                    hi = mid;
                } else {
                    lo = mid + 1;
                }
            }
            let r = rect(lo);
            ensure!(
                covered(&all, r, g),
                "internal common crop certificate failed"
            );
            // Resolve against the nearest existing ancestor before creating any directory.
            let absolute = if out_dir.is_absolute() {
                out_dir.clone()
            } else {
                std::env::current_dir()?.join(out_dir)
            };
            let mut ancestor = absolute.as_path();
            let mut suffix = Vec::new();
            while !ancestor.exists() {
                suffix.push(
                    ancestor
                        .file_name()
                        .context("invalid research output directory")?
                        .to_os_string(),
                );
                ancestor = ancestor
                    .parent()
                    .context("research output has no existing ancestor")?;
            }
            let mut resolved = ancestor.canonicalize()?;
            for part in suffix.iter().rev() {
                resolved.push(part);
            }
            ensure!(
                !resolved.starts_with(input_root),
                "common-crop output must be outside capture corpus"
            );
            let mut names = std::collections::BTreeSet::new();
            for path in maps {
                let name = path.file_name().context("map filename")?;
                ensure!(
                    names.insert(name) && !out_dir.join(name).exists(),
                    "duplicate/existing common-crop output"
                );
            }
            fs::create_dir_all(out_dir)?;
            ensure!(
                !out_dir.canonicalize()?.starts_with(input_root),
                "common-crop output resolved inside capture corpus"
            );
            let peers = envelopes
                .iter()
                .map(|e| e.payload_sha256.clone())
                .collect::<Vec<_>>();
            let arms = envelopes.iter().map(|e| e.payload.arm).collect::<Vec<_>>();
            for (path, e) in maps.iter().zip(envelopes) {
                let mut p = e.payload;
                p.crop = Some([r.x, r.y, r.width, r.height]);
                p.crop_peer_payloads = peers.clone();
                p.crop_peer_arms = arms.clone();
                save(&out_dir.join(path.file_name().context("map filename")?), p)?;
            }
            eprintln!(
                "research common crop: {},{} {}x{} plane pixels; conservative coverage only; placement UNVERIFIED",
                r.x, r.y, r.width, r.height
            );
        }
    }
    Ok(())
}

#[cfg(test)]
mod artifact_tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    struct Scratch {
        path: PathBuf,
        root: PathBuf,
    }
    impl Scratch {
        fn new() -> Self {
            static NEXT: AtomicU64 = AtomicU64::new(0);
            let root = std::env::temp_dir().canonicalize().unwrap();
            let path = root.join(format!(
                "strehl-lens-guard-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&path).unwrap();
            Self { path, root }
        }
    }
    impl Drop for Scratch {
        fn drop(&mut self) {
            let resolved = self.path.canonicalize().unwrap();
            assert!(resolved.starts_with(&self.root) && resolved != self.root);
            assert!(
                resolved
                    .file_name()
                    .unwrap()
                    .to_string_lossy()
                    .starts_with("strehl-lens-guard-")
            );
            fs::remove_dir_all(resolved).unwrap();
        }
    }
    fn fixture(root: &Path) -> (Payload, Vec<PathBuf>) {
        let input = root.join("synthetic-corpus");
        fs::create_dir(&input).unwrap();
        let mut sources = Vec::new();
        let mut paths = Vec::new();
        for i in 0..3 {
            let filename = format!("generated-source-{i}.dat");
            let path = input.join(&filename);
            fs::write(
                &path,
                format!("generated structural fixture {i}; no RAW pixels"),
            )
            .unwrap();
            let md = fs::metadata(&path).unwrap();
            sources.push(Source {
                filename,
                bytes: md.len(),
                modified_unix_ns: md
                    .modified()
                    .unwrap()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
                sha256: file_digest(&path).unwrap(),
                body: "ILCE-7CM2".into(),
                firmware: "2.00".into(),
                lens_type3: u16::MAX,
                active_origin: [0, 0],
                active_size: [128, 128],
                default_crop: [0, 0, 128, 128],
                cfa: "RGGB".into(),
                black: 512.0,
                white: 16383.0,
                iso: Some(100.0),
                distortion_setting: 0,
                curve: CurveSpec {
                    center: [63.5, 63.5],
                    reference_radius: 90.0,
                    input_scale: 1.0,
                    output_scale: 1.0,
                    max_input_radius: 200.0,
                    knots: [0; 16],
                },
            });
            paths.push(path);
        }
        let manifest = Manifest {
            magic: "strehl-lens-optical-manifest".into(),
            version: VERSION,
            convention: CONVENTION.into(),
            radial_center_convention: "default-crop-pixel-center-midpoint".into(),
            placement_status: "unverified".into(),
            metadata_extractor: "generated test fixture".into(),
            metadata_evidence: "No camera/placement claim".into(),
            sources,
        };
        manifest.validate().unwrap();
        let full = manifest.geometry();
        let crop = manifest.guide_crop().unwrap();
        let map = WarpMap::new(
            strehl_core::warpmap::Provenance {
                stack: strehl_core::warpmap::StackIdentity::from_paths("synthetic-corpus", &paths)
                    .unwrap(),
                strategy: "research-lens-direct-global-f32-v1".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: 1,
                note: "generated structural fixture, not measured alignment".into(),
            },
            full,
            Resampler::CatmullRom,
            vec![strehl_core::warpmap::FrameWarp::Placed(Similarity::IDENTITY); 3],
        );
        let pairs = vec![[0, 1], [0, 2], [1, 2]];
        let mut opts = strehl_core::align::GlobalOptions::new(crop.geometry());
        opts.weighting = strehl_core::align::Weighting::Unit;
        opts.smooth = 1.0;
        opts.smooth_huber_px = Some(1.0);
        let solve = SolveReceipt {
            requested_pairs: pairs.clone(),
            accepted_edges: pairs
                .into_iter()
                .map(|pair| EdgeReceipt {
                    pair,
                    transform: [0.0; 4],
                    rms: 0.0,
                    used: 16,
                    lever: 10.0,
                })
                .collect(),
            guide_crop: [crop.x, crop.y, crop.width, crop.height],
            cycle_rank: 1,
            reference: 1,
            threads: 1,
            smooth: 1.0,
            smooth_huber: 1.0,
            weighting: "unit".into(),
            pair_config: format!("{:?}", strehl_core::align::AlignConfig::deep()),
            global_config: format!("{opts:?}"),
            guide_policy: GUIDE_POLICY.into(),
        };
        let manifest_sha256 = digest(&serde_json::to_vec(&manifest).unwrap());
        (
            Payload {
                manifest,
                manifest_sha256,
                arm: Arm::ForcedZero,
                build: env!("STREHL_BUILD_ID").into(),
                binary_sha256: file_digest(&std::env::current_exe().unwrap()).unwrap(),
                input_root: input.canonicalize().unwrap(),
                warp_text: map.to_text(),
                solve,
                ca: vec![[[0.0; 4]; 3]; 3],
                crop: None,
                crop_peer_payloads: Vec::new(),
                crop_peer_arms: Vec::new(),
                coverage: "radial-bound-ca-after-pull-margin6-v1".into(),
                arithmetic: ARITHMETIC.into(),
            },
            paths,
        )
    }
    fn message<T>(result: Result<T>) -> String {
        result
            .err()
            .map(|e| format!("{e:#}"))
            .expect("expected actual refusal")
    }
    fn save_variant(root: &Path, name: &str, p: Payload) -> PathBuf {
        let path = root.join(name);
        save(&path, p).unwrap();
        path
    }

    #[test]
    fn actual_envelope_roundtrip_rejects_legacy_and_protects_existing_output() {
        let tmp = Scratch::new();
        let (p, _) = fixture(&tmp.path);
        let path = save_variant(&tmp.path, "original.json", p.clone());
        let bytes = fs::read(&path).unwrap();
        let loaded = load(&path).unwrap();
        reconstruct(&loaded.payload).unwrap();
        assert!(matches!(
            WarpMap::from_text(std::str::from_utf8(&bytes).unwrap()),
            Err(strehl_core::warpmap::WarpMapError::BadMagic { .. })
        ));
        assert!(save(&path, p).is_err());
        assert_eq!(bytes, fs::read(&path).unwrap());
        assert!(
            outside_corpus(
                &tmp.path.join("synthetic-corpus/forbidden.json"),
                &tmp.path.join("synthetic-corpus")
            )
            .is_err()
        );
        outside_corpus(
            &tmp.path.join("allowed.json"),
            &tmp.path.join("synthetic-corpus"),
        )
        .unwrap();
    }
    #[test]
    fn actual_parser_refuses_magic_version_end_unknown_fields_checksum_and_truncation() {
        let tmp = Scratch::new();
        let (p, _) = fixture(&tmp.path);
        let path = save_variant(&tmp.path, "good.json", p);
        let bytes = fs::read(path).unwrap();
        let base: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        for (name, key, value) in [
            ("magic", "magic", serde_json::json!("strehl-warpmap")),
            ("version", "version", serde_json::json!(999)),
            ("end", "complete", serde_json::json!("unfinished")),
            ("unknown", "unexpected", serde_json::json!(true)),
            (
                "checksum",
                "payload_sha256",
                serde_json::json!("0".repeat(64)),
            ),
        ] {
            let mut v = base.clone();
            v[key] = value;
            let path = tmp.path.join(format!("{name}.json"));
            fs::write(&path, serde_json::to_vec(&v).unwrap()).unwrap();
            assert!(load(&path).is_err(), "{name}");
        }
        let truncated = tmp.path.join("truncated.json");
        fs::write(&truncated, &bytes[..bytes.len() / 2]).unwrap();
        assert!(load(&truncated).is_err());
        let mut v = base;
        v["payload"]["arm"] = serde_json::json!("per-frame");
        let path = tmp.path.join("changed-payload.json");
        fs::write(&path, serde_json::to_vec(&v).unwrap()).unwrap();
        assert!(message(load(&path)).contains("checksum"));
    }
    #[test]
    fn checksum_valid_artifacts_still_refuse_wrong_binary_manifest_count_and_anchor() {
        let tmp = Scratch::new();
        let (p, _) = fixture(&tmp.path);
        let mut wrong = p.clone();
        wrong.binary_sha256 = "0".repeat(64);
        assert!(
            message(load(&save_variant(&tmp.path, "wrong-binary.json", wrong)))
                .contains("preparing executable")
        );
        let mut wrong = p.clone();
        wrong.manifest_sha256 = "0".repeat(64);
        assert!(
            message(load(&save_variant(&tmp.path, "wrong-manifest.json", wrong)))
                .contains("source/build identity")
        );
        let mut wrong = p.clone();
        let mut extra = wrong.manifest.sources[0].clone();
        extra.filename = "extra.dat".into();
        wrong.manifest.sources.push(extra);
        wrong.manifest_sha256 = digest(&serde_json::to_vec(&wrong.manifest).unwrap());
        let parsed = load(&save_variant(&tmp.path, "wrong-count.json", wrong)).unwrap();
        assert!(message(reconstruct(&parsed.payload)).contains("map/source/gauge"));
        let mut wrong = p;
        let map = WarpMap::from_text(&wrong.warp_text).unwrap();
        let mut warps = map.warps().to_vec();
        warps[1] = strehl_core::warpmap::FrameWarp::Placed(Similarity::from_params(
            strehl_core::align::SimilarityParams {
                ax: 0.25,
                ..Default::default()
            },
        ));
        wrong.warp_text = WarpMap::new(
            map.provenance().clone(),
            map.geometry(),
            map.resampler(),
            warps,
        )
        .to_text();
        let parsed = load(&save_variant(&tmp.path, "wrong-anchor.json", wrong)).unwrap();
        assert!(message(reconstruct(&parsed.payload)).contains("anchor is not exact identity"));
    }
    #[test]
    fn actual_source_binding_requires_order_count_stat_and_full_content_hash() {
        let tmp = Scratch::new();
        let (p, paths) = fixture(&tmp.path);
        let mut m = p.manifest;
        m.bind_files(&paths).unwrap();
        assert!(message(m.bind(&paths)).contains("body/lens metadata mismatch"));
        assert!(m.bind_files(&paths[..2]).is_err());
        let mut reordered = paths.clone();
        reordered.swap(0, 1);
        assert!(message(m.bind_files(&reordered)).contains("source order"));
        fs::write(&paths[0], b"changed generated fixture payload").unwrap();
        assert!(message(m.bind_files(&paths)).contains("source stat"));
        let md = fs::metadata(&paths[0]).unwrap();
        m.sources[0].bytes = md.len();
        m.sources[0].modified_unix_ns = md
            .modified()
            .unwrap()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        assert!(message(m.bind_files(&paths)).contains("SHA256"));
    }
    #[test]
    fn manifest_admission_refuses_missing_or_nonuniform_noise_and_capture_identity() {
        let tmp = Scratch::new();
        let (p, _) = fixture(&tmp.path);
        let good = p.manifest;
        for case in 0..8 {
            let mut m = good.clone();
            let source = &mut m.sources[1];
            match case {
                0 => source.iso = None,
                1 => source.iso = Some(200.0),
                2 => source.black += 1.0,
                3 => source.white -= 1.0,
                4 => source.firmware = "different".into(),
                5 => source.lens_type3 -= 1,
                6 => source.curve.center[0] += 0.5,
                _ => source.cfa = "BGGR".into(),
            }
            assert!(m.validate().is_err(), "case {case}");
        }
        let mut v = serde_json::to_value(&good).unwrap();
        v["sources"][0]["invented_tag"] = serde_json::json!(1);
        assert!(serde_json::from_value::<Manifest>(v).is_err());
        let mut missing = serde_json::to_value(&good).unwrap();
        missing["sources"][0]["curve"]
            .as_object_mut()
            .unwrap()
            .remove("knots");
        assert!(
            serde_json::from_value::<Manifest>(missing).is_err(),
            "missing table must not become zero"
        );
    }
    #[test]
    fn actual_shared_mode_and_override_guards_refuse_unsupported_consumers() {
        use crate::merge_cmd::MergeBackend;
        validate_modes(
            MergeBackend::Pyramid,
            CoverMode::Crop,
            Resampler::CatmullRom,
            false,
            false,
            true,
        )
        .unwrap();
        for (backend, cover, resampler, repair, subset, fullres) in [
            (
                MergeBackend::Estimator,
                CoverMode::Crop,
                Resampler::CatmullRom,
                false,
                false,
                true,
            ),
            (
                MergeBackend::Pyramid,
                CoverMode::Scale,
                Resampler::CatmullRom,
                false,
                false,
                true,
            ),
            (
                MergeBackend::Pyramid,
                CoverMode::Crop,
                Resampler::Bilinear,
                false,
                false,
                true,
            ),
            (
                MergeBackend::Pyramid,
                CoverMode::Crop,
                Resampler::CatmullRom,
                true,
                false,
                true,
            ),
            (
                MergeBackend::Pyramid,
                CoverMode::Crop,
                Resampler::CatmullRom,
                false,
                true,
                true,
            ),
            (
                MergeBackend::Pyramid,
                CoverMode::Crop,
                Resampler::CatmullRom,
                false,
                false,
                false,
            ),
        ] {
            assert!(validate_modes(backend, cover, resampler, repair, subset, fullres).is_err());
        }
        validate_overrides(|_| None).unwrap();
        for (key, value) in [
            ("STREHL_SPATIAL_NOISE_FLOOR", "on"),
            ("STREHL_TEMPORAL_ENERGY", "on"),
            ("STREHL_GATE_FLOOR", "white"),
            ("STREHL_LOCAL_PLACEMENT_FILE", "off"),
            ("STREHL_ONLY_FRAME", "0"),
            ("STREHL_DIRECT_PLANES", "float"),
            ("STREHL_GPU_GATHER", "on"),
        ] {
            assert!(
                validate_overrides(|asked| (asked == key).then(|| value.into())).is_err(),
                "{key}"
            );
        }
    }
    #[test]
    fn map_only_defect_selector_is_refused_without_mutating_the_test_environment() {
        for (mode, defect) in [
            ("map-only", None),
            ("explicit-off", Some("off")),
            ("invalid-zero", Some("0")),
        ] {
            let mut cmd = std::process::Command::new(std::env::current_exe().unwrap());
            cmd.args([
                "--exact",
                "lens_research::artifact_tests::defect_environment_child",
                "--nocapture",
                "--test-threads=1",
            ])
            .env("STREHL_LENS_TEST_CHILD", mode)
            .env("STREHL_DEFECT_MAP", "generated-sidecar-not-opened.json");
            if let Some(value) = defect {
                cmd.env("STREHL_DEFECT", value);
            } else {
                cmd.env_remove("STREHL_DEFECT");
            }
            let result = cmd.output().unwrap();
            let stdout = String::from_utf8_lossy(&result.stdout);
            assert!(
                result.status.success(),
                "{mode}: {} {}",
                stdout,
                String::from_utf8_lossy(&result.stderr)
            );
            assert!(
                stdout.contains("running 1 test")
                    && stdout.contains("1 passed; 0 failed")
                    && stdout.contains("lens_research::artifact_tests::defect_environment_child"),
                "the selected child guard must actually run exactly once: {mode}: {stdout}"
            );
        }
    }
    #[test]
    fn defect_environment_child() {
        let Ok(mode) = std::env::var("STREHL_LENS_TEST_CHILD") else {
            return;
        };
        let request = crate::stack::defect_request_from_env();
        if mode == "invalid-zero" {
            assert!(request.is_err());
            return;
        }
        let guarded = validate_defects(&request.unwrap());
        if mode == "explicit-off" {
            guarded.unwrap();
        } else {
            assert!(guarded.is_err());
        }
    }
    #[test]
    fn actual_common_crop_refuses_duplicate_arms_and_capture_writes_then_seals_distinct_peers() {
        let tmp = Scratch::new();
        let (p, _) = fixture(&tmp.path);
        let zero = save_variant(&tmp.path, "zero.json", p.clone());
        let duplicate = save_variant(&tmp.path, "copy.json", p.clone());
        let duplicate_out = tmp.path.join("duplicate-out");
        assert!(
            message(run(&Args {
                action: Action::CommonCrop {
                    maps: vec![zero.clone(), duplicate],
                    out_dir: duplicate_out.clone()
                }
            }))
            .contains("duplicate")
        );
        assert!(!duplicate_out.exists());
        let mut fixed = p.clone();
        fixed.arm = Arm::AnchorFixed;
        let fixed = save_variant(&tmp.path, "fixed.json", fixed);
        let forbidden = p.input_root.join("forbidden-output");
        assert!(
            message(run(&Args {
                action: Action::CommonCrop {
                    maps: vec![zero.clone(), fixed.clone()],
                    out_dir: forbidden.clone()
                }
            }))
            .contains("outside capture corpus")
        );
        assert!(!forbidden.exists());
        let output = tmp.path.join("sealed");
        run(&Args {
            action: Action::CommonCrop {
                maps: vec![zero, fixed],
                out_dir: output.clone(),
            },
        })
        .unwrap();
        let sealed = load(&output.join("zero.json")).unwrap();
        validate_common_crop(&sealed.payload).unwrap();
        let (map, pulls) = reconstruct(&sealed.payload).unwrap();
        assert!(covered(&pulls, pulls[0].crop, map.geometry()));
        let projected = numeric_projection(&fs::read(output.join("zero.json")).unwrap()).unwrap();
        assert!(!projected["arms"][0]["pulls"][0]["rect_bits"].is_null());
        let mut bad = sealed.payload.clone();
        bad.crop = Some([0, 0, 64, 64]);
        let path = save_variant(&tmp.path, "checksummed-uncovered-crop.json", bad);
        assert!(
            message(numeric_projection(&fs::read(path).unwrap()))
                .contains("no coverage certificate")
        );
        let mut bad = sealed.payload.clone();
        bad.crop_peer_payloads[1] = bad.crop_peer_payloads[0].clone();
        assert!(validate_common_crop(&bad).is_err());
        let path = save_variant(&tmp.path, "checksummed-duplicate-peers.json", bad);
        assert!(
            message(numeric_projection(&fs::read(path).unwrap())).contains("distinct bound arms")
        );
        let mut bad = sealed.payload.clone();
        bad.crop_peer_arms[1] = bad.crop_peer_arms[0];
        assert!(validate_common_crop(&bad).is_err());
        let mut bad = sealed.payload;
        bad.crop_peer_payloads[0] = "1".repeat(64);
        assert!(message(validate_common_crop(&bad)).contains("does not bind"));
    }
    #[test]
    fn actual_parser_refuses_previous_split_arithmetic_with_current_binary_checksum() {
        let tmp = Scratch::new();
        let (mut payload, _) = fixture(&tmp.path);
        assert_eq!(payload.arithmetic, ARITHMETIC);
        payload.arithmetic = "f32-native-pull-guide-center-half-pixel-v1".into();
        let path = save_variant(&tmp.path, "old-split-arithmetic.json", payload);
        assert!(message(load(&path)).contains("arithmetic/coverage version"));
        assert!(
            message(numeric_projection(&fs::read(path).unwrap()))
                .contains("arithmetic/coverage version")
        );
    }
    #[test]
    fn numeric_projection_uses_actual_selected_curves_and_reconstructed_pull_bits() {
        let tmp = Scratch::new();
        let (mut p, _) = fixture(&tmp.path);
        p.manifest.sources[0].curve.input_scale = 1.0004;
        p.manifest.sources[0].curve.knots = [7; 16];
        let bytes = serde_json::to_vec(&p.manifest).unwrap();
        let projection = numeric_projection(&bytes).unwrap();
        assert_eq!(projection["arithmetic"], ARITHMETIC);
        assert_eq!(projection["input_sha256"], digest(&bytes));
        assert_eq!(projection["input_bytes"], bytes.len());
        assert_eq!(
            projection["geometry_source_sha256"],
            digest(include_bytes!("lens-research-geometry.rs"))
        );
        assert_eq!(
            projection["integration_source_sha256"],
            digest(include_bytes!("lens-research.rs"))
        );
        assert_eq!(
            projection["arms"][0]["curves"][0]["knots"],
            serde_json::to_value([0i16; 16]).unwrap()
        );
        assert_eq!(
            projection["arms"][2]["curves"][0]["knots"],
            serde_json::to_value([7i16; 16]).unwrap()
        );
        assert_eq!(
            projection["arms"][2]["curves"][0]["input_scale_bits"],
            1.0004_f32.to_bits()
        );
        assert!(
            projection["arms"][0]["pulls"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        // The unsealed envelope has no admitted consumed output rectangle.
        p.manifest.sources[0].curve.input_scale = 1.0;
        p.manifest.sources[0].curve.knots = [0; 16];
        let path = save_variant(&tmp.path, "projection-envelope.json", p);
        let bytes = fs::read(path).unwrap();
        let projection = numeric_projection(&bytes).unwrap();
        assert_eq!(projection["kind"], "envelope");
        let pull = &projection["arms"][0]["pulls"][0];
        assert_eq!(
            pull["placement_bits"]["center"],
            serde_json::to_value([64.5_f32.to_bits(); 2]).unwrap()
        );
        assert_eq!(
            pull["ca_bits"][0]["center"],
            serde_json::to_value([64.0_f32.to_bits(); 2]).unwrap()
        );
        assert!(pull["rect_bits"].is_null());
        assert_eq!(pull["margin_bits"], 6.0_f32.to_bits());
    }
}

#[cfg(test)]
#[path = "lens-research-compensated-tests.rs"]
mod compensated_tests;
