// Bounded, cache-only photographic pilot. No RAW decoder is called by this harness.
#![allow(dead_code)]
#![recursion_limit = "256"]
#[cfg(test)]
#[path = "chart-geometry-signal-commission-controls.rs"]
mod chart_geometry_signal_commission_controls;
#[path = "focus-artifact.rs"]
mod focus_artifact;
#[path = "focus-census.rs"]
mod focus_census;
#[path = "heldout-original-prediction.rs"]
mod heldout_original_prediction;
#[path = "historical-cache.rs"]
mod historical_cache;
#[path = "kernel-reconstruction.rs"]
mod kernel_reconstruction;
// Compile the exact current core operators into this research executable;
// Frozen, hash-bound CLI libraries supply cache/guide/alignment primitives only.
// This prevents reporting a live operator hash while calling an older rlib copy.
#[cfg(test)]
pub use strehl_cli::{session_reconstruction_sampling, session_sampling};
pub use strehl_core::{align, noise, optics, plane};
#[path = "../../../../crates/strehl-core/src/reconstruction.rs"]
mod reconstruction;
use reconstruction::registration_global as local_registration_global;
use reconstruction::{
    registration as local_registration, registration_graph as local_registration_graph,
};
#[path = "../../../../crates/strehl-cli/src/session-reconstruction-motion.rs"]
mod coherent_motion;
#[path = "local-registration-pilot.rs"]
mod local_registration_pilot;
use anyhow::{Context, Result, ensure};
use clap::Parser;
use focus_artifact::FocusSlice;
use rayon::prelude::*;
use reconstruction::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeSet,
    fs,
    io::Write,
    path::{Path, PathBuf},
    sync::Arc,
    time::Instant,
};
use strehl_cli::session_cache::{CacheStats, CachedSource, SourceCache};
use strehl_cli::session_focus::complete_support;
use strehl_cli::session_input::{ResolvedSession, SourceIdentity};
use strehl_cli::session_sampling::{NativeSampler, SamplingDomain};
use strehl_core::{
    align::Similarity,
    boxfilter::box_mean,
    color,
    focus::{FINE_WINDOW_RADIUS, FocusField, window_radius},
    focus_evidence::{FocusEvidenceBuilder, FocusEvidencePolicy, FocusFrame},
    merge::{REGULARISER_RADIUS, regularise},
    noise::{Levels, NoiseModel, PlaneNoise, Provenance},
    optics::{OpticalProfile, profile_for_capture_env},
    plane::PlaneGeometry,
    warpmap::WarpMap,
};
use strehl_edit::{ImageOrigin, LinearImage};

// Chosen from saved full-track focus and exact-taper phase census, never
// from candidate image appearance. Four separate acquisitions form the guide.
const TARGETS: [usize; 14] = [
    107, 108, 109, 110, 111, 112, 113, 397, 398, 399, 400, 401, 402, 403,
];
const GUIDES: [usize; 4] = [106, 114, 396, 404];
const CACHE_BUDGET: usize = 1080 << 20;
const TOTAL_LIMIT: usize = 2 << 30;

#[derive(Parser)]
struct Args {
    #[arg(long)]
    render_dir: PathBuf,
    #[arg(long)]
    cache: PathBuf,
    /// Explicit read-only research use of the independently audited ef655050 cache.
    #[arg(long)]
    historical_cache: bool,
    #[arg(long)]
    out: PathBuf,
    #[arg(long, default_value_t = 192)]
    size: usize,
    /// Full active sensor coordinates; defaults to image centre +300 sensels vertically.
    #[arg(long)]
    x: Option<usize>,
    #[arg(long)]
    y: Option<usize>,
    #[arg(long, default_value_t = 16)]
    workers: usize,
    /// Diagnostic assumed uncertainty, never a measured registration certificate.
    #[arg(long)]
    assumed_registration_sigma_sensor: f32,
    /// Focus-only streaming census at up to three explicit x,y sensor origins.
    #[arg(long, value_delimiter = ',')]
    census_rois: Vec<usize>,
    /// Explicit completed research focus artifact, avoiding a repeated full track.
    #[arg(long, requires = "focus_seal")]
    focus_census: Option<PathBuf>,
    #[arg(long, requires = "focus_census")]
    focus_seal: Option<PathBuf>,
    #[arg(long, default_value_t = 0)]
    focus_roi: usize,
    /// Measure direct native-CFA local pair/cycle evidence using selected originals.
    #[arg(long)]
    measure_registration: bool,
    /// Geometry-only Gaussian sigma in original same-color quad pixels; zero retains raw NCC.
    #[arg(long, default_value_t = 0.0, requires = "measure_registration")]
    registration_geometry_sigma_quad: f32,
    /// Fixed original-plane geometry tile size;46 with grid3 is a separately commissioned arm.
    #[arg(long, default_value_t = 24, requires = "measure_registration")]
    registration_tile_quad: usize,
    #[arg(long, default_value_t = 4, requires = "measure_registration")]
    registration_grid_axis: usize,
    /// Explicit original-plane geometry context; output/focus ROI stays fixed.
    #[arg(long, default_value_t = 192, requires = "measure_registration")]
    registration_window_quad: usize,
    /// Experimental local-affine original-CFA regression, default remains local constant.
    #[arg(long)]
    affine_reconstruction: bool,
    /// Score omitted original sensels against direct and matched CFA-to-MHC predictors.
    #[arg(long, conflicts_with = "registration_only")]
    heldout_prediction: bool,
    /// Explicit4..14 target indices selected from a completed focus census.
    #[arg(long, value_delimiter = ',')]
    targets: Vec<usize>,
    /// Two to four distinct guide acquisitions, excluded from every target.
    #[arg(long, value_delimiter = ',')]
    guides: Vec<usize>,
    #[arg(long, requires = "measure_registration")]
    registration_only: bool,
    /// Measure geometry without running sweep focus; cannot render a candidate.
    #[arg(long, requires = "registration_only", conflicts_with_all = ["focus_census", "census_rois"])]
    geometry_without_focus: bool,
    #[arg(
        long,
        requires = "measure_registration",
        conflicts_with = "registration_only"
    )]
    require_registration: bool,
    #[arg(long, requires = "measure_registration")]
    refine_registration: bool,
    #[arg(long)]
    matched_comparator: bool,
    /// Use the exact product RGB appearance gate; omitted preserves old pilots.
    #[arg(long)]
    coherent_color_motion: bool,
    /// Post-estimator census of all predefined patches; never used by fits.
    #[arg(long, requires = "measure_registration")]
    registration_patch_diagnostics: bool,
    /// Export unresampled original CFA patches for a descriptive spectrum census.
    #[arg(long)]
    original_patch_diagnostics: bool,
}
enum OriginalCache {
    Current(SourceCache),
    Historical(historical_cache::HistoricalCache),
}
impl OriginalCache {
    fn load(&mut self, id: &SourceIdentity) -> Result<Option<Arc<CachedSource>>> {
        match self {
            Self::Current(c) => Ok(c.load(id)?),
            Self::Historical(c) => c.load(id),
        }
    }
    fn cache_path(&self, id: &SourceIdentity) -> Result<PathBuf> {
        match self {
            Self::Current(c) => Ok(c.cache_path(id)?),
            Self::Historical(c) => c.path(id),
        }
    }
    fn stats(&self) -> CacheStats {
        match self {
            Self::Current(c) => c.stats(),
            Self::Historical(c) => c.stats(),
        }
    }
}

fn json_read(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
fn err(e: impl std::fmt::Display) -> anyhow::Error {
    anyhow::anyhow!(e.to_string())
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|v| format!("{v:02x}")).collect()
}
fn hash(path: &Path) -> Result<String> {
    use std::io::Read;
    let mut f = fs::File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(hex(&h.finalize()))
}
fn write_new(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    f.write_all(bytes)?;
    f.sync_all()?;
    Ok(())
}
fn write_f32(path: &Path, values: impl IntoIterator<Item = f32>) -> Result<()> {
    let mut f = std::io::BufWriter::new(
        fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)?,
    );
    for v in values {
        f.write_all(&v.to_le_bytes())?;
    }
    f.flush()?;
    Ok(())
}
fn inverse(m: [[f32; 3]; 3]) -> Result<[[f32; 3]; 3]> {
    let a = m.map(|r| r.map(f64::from));
    let det = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
    ensure!(
        det.is_finite() && det.abs() > 1e-10,
        "noninvertible camera matrix"
    );
    let mut inv = [[0.0; 3]; 3];
    for (i, row) in inv.iter_mut().enumerate() {
        for (j, v) in row.iter_mut().enumerate() {
            let rows: Vec<_> = (0..3).filter(|x| *x != j).collect();
            let cols: Vec<_> = (0..3).filter(|x| *x != i).collect();
            *v = (((a[rows[0]][cols[0]] * a[rows[1]][cols[1]]
                - a[rows[0]][cols[1]] * a[rows[1]][cols[0]])
                / det)
                * if (i + j) % 2 == 0 { 1.0 } else { -1.0 }) as f32;
        }
    }
    Ok(inv)
}
fn multiply(m: [[f32; 3]; 3], v: [f32; 3]) -> [f32; 3] {
    m.map(|r| r[0] * v[0] + r[1] * v[1] + r[2] * v[2])
}
/// Only invert the common linear segment. Nonlinear display pixels remain
/// useful native output, but are not invented camera-DN observations.
fn native_camera_pixel(
    rgb: [f32; 3],
    render: &color::Render,
    inv: [[f32; 3]; 3],
    wb: [f32; 3],
    levels: Levels,
    knee: f32,
) -> Option<([f32; 3], f32)> {
    let camera = multiply(inv, rgb);
    if !camera
        .iter()
        .zip(render.ceiling())
        .all(|(v, c)| v.is_finite() && *v / c < knee - 0.02)
    {
        return None;
    }
    let back = render.develop(camera);
    let error = back
        .into_iter()
        .zip(rgb)
        .map(|(a, b)| (a - b).abs())
        .fold(0f32, f32::max);
    if !error.is_finite() || error >= 2e-6 {
        return None;
    }
    Some((
        std::array::from_fn(|c| camera[c] * levels.range() / wb[c]),
        error,
    ))
}
fn coherent_output(eligible: bool, reason: [Reason; 3]) -> bool {
    eligible && reason.iter().all(|r| *r == Reason::Reconstructed)
}
fn final_scene_pixel(
    native: [f32; 3],
    eligible: bool,
    camera: [f32; 3],
    reason: [Reason; 3],
    render: &color::Render,
    wb: [f32; 3],
    levels: Levels,
) -> [f32; 3] {
    if !coherent_output(eligible, reason) {
        native
    } else {
        render.develop(std::array::from_fn(|c| camera[c] * wb[c] / levels.range()))
    }
}
fn interp(plane: &[f32], g: PlaneGeometry, x: f64, y: f64) -> f32 {
    let x = x.clamp(0.0, (g.width - 1) as f64);
    let y = y.clamp(0.0, (g.height - 1) as f64);
    let ix = x.floor() as usize;
    let iy = y.floor() as usize;
    let jx = (ix + 1).min(g.width - 1);
    let jy = (iy + 1).min(g.height - 1);
    let dx = (x - ix as f64) as f32;
    let dy = (y - iy as f64) as f32;
    (1.0 - dy) * ((1.0 - dx) * plane[iy * g.width + ix] + dx * plane[iy * g.width + jx])
        + dy * ((1.0 - dx) * plane[jy * g.width + ix] + dx * plane[jy * g.width + jx])
}
fn green(planes: &[Vec<f32>; 4], dst: &mut [f32]) {
    for (i, v) in dst.iter_mut().enumerate() {
        *v = 0.5 * (planes[1][i] + planes[3][i]);
    }
}

// Same two streaming passes as the shared focus export, but cache-only load is
// mandatory here. Full original track ordinals and support flags are preserved.
#[allow(clippy::too_many_arguments)]
fn focus_pass(
    session: &ResolvedSession,
    ids: &[SourceIdentity],
    pass: usize,
    map: &WarpMap,
    cache: &mut OriginalCache,
    domain: SamplingDomain,
    noise: &NoiseModel,
    profile: Option<&OpticalProfile>,
) -> Result<FocusSlice> {
    let frames: Vec<_> = session.passes[pass]
        .global_range
        .clone()
        .map(|global_index| FocusFrame {
            acquisition: global_index as u64,
            global_index,
        })
        .collect();
    let geom = PlaneGeometry {
        width: domain.width,
        height: domain.height,
    };
    let n = geom.pixels();
    let mut builder = FocusEvidenceBuilder::new(
        geom,
        frames.clone(),
        FocusEvidencePolicy::default(),
        64 << 20,
    )?;
    let mut sampler = NativeSampler::new(domain)?;
    let mut field = FocusField::new(geom);
    let mut g = vec![0.; n];
    let mut fine = vec![0.; n];
    let mut reg = vec![0.; n];
    let mut scratch = vec![0.; n];
    let mut masks = vec![0u32; n];
    let mut valid = vec![false; n];
    let halo = window_radius() + 1 + REGULARISER_RADIUS;
    for phase in 0..2 {
        if phase == 1 {
            builder.begin_shape_pass()?;
        }
        for (ordinal, &f) in frames.iter().enumerate() {
            if let Some(t) = map.warps()[f.global_index].placed() {
                let source = cache.load(&ids[f.global_index])?.with_context(|| {
                    format!("cache miss {}, RAW decode prohibited", f.global_index)
                })?;
                let s = sampler.gather(
                    source.as_ref(),
                    source.levels(),
                    t,
                    profile,
                    map.resampler(),
                )?;
                green(&s.planes, &mut g);
                complete_support(&s.support, geom, halo, &mut masks, &mut valid)?;
                field.compute_with_fine(&g, noise, FINE_WINDOW_RADIUS, &mut fine);
                regularise(field.values(), geom, &mut scratch, &mut reg);
            } else {
                valid.fill(false);
                fine.fill(0.);
                reg.fill(0.);
            }
            if phase == 0 {
                builder.observe_anchor(ordinal, f, &reg, &valid)?;
            } else {
                builder.observe_shape(ordinal, f, &fine, &reg, &valid)?;
            }
            if ordinal % 50 == 0 || ordinal + 1 == frames.len() {
                eprintln!(
                    "cache-only focus pass {pass} phase {phase}: {}/{}",
                    ordinal + 1,
                    frames.len()
                );
            }
        }
    }
    Ok(builder.finish()?.into())
}
struct OwnedAdmission {
    focus: Vec<f32>,
    motion: Vec<f32>,
    valid: Vec<bool>,
    sigma: Vec<f32>,
}
struct Inputs {
    config: Config,
    acquisitions: Vec<usize>,
    gains: Vec<f32>,
    lattice: OutputLattice,
    originals: Vec<Arc<CachedSource>>,
    pulls: Vec<[Similarity; 3]>,
    noise: [PlaneNoise; 4],
    fields: Vec<OwnedAdmission>,
    expected: Vec<[f32; 3]>,
    tensor: Vec<[f32; 3]>,
    fallback: Vec<[f32; 3]>,
    fallback_valid: Vec<bool>,
}
impl Inputs {
    fn tile(&self, y: usize, rows: usize) -> Result<TileResult> {
        let start = y * self.lattice.width;
        let end = (y + rows) * self.lattice.width;
        let views: Vec<_> = self
            .originals
            .iter()
            .zip(&self.fields)
            .enumerate()
            .map(|(s, (src, a))| SourceView {
                acquisition_id: self.acquisitions[s] as u64,
                source: src.as_ref(),
                source_pull: self.pulls[s],
                noise: self.noise,
                gain: self.gains[s],
                admission: Admission {
                    focus: &a.focus[start..end],
                    motion: &a.motion[start..end],
                    valid: &a.valid[start..end],
                    registration_sigma_sensor: &a.sigma[start..end],
                },
            })
            .collect();
        let mut l = self.lattice;
        l.origin_sensor[1] += y as f64 * l.step_sensor[1];
        l.height = rows;
        reconstruct_tile(
            l,
            &views,
            FrozenGuide {
                expected_rgb: &self.expected[start..end],
                tensor: &self.tensor[start..end],
                fallback_rgb: &self.fallback[start..end],
                fallback_variance: None,
                fallback_valid: &self.fallback_valid[start..end],
            },
            self.config,
        )
        .map_err(err)
    }
}
fn render_source_gains(report: &Value, count: usize) -> Result<Vec<f32>> {
    let frames = report["frames"]
        .as_array()
        .context("render source gain records missing")?;
    ensure!(frames.len() == count, "render source census differs");
    let mut gains = vec![f32::NAN; count];
    for frame in frames {
        let i = frame["frame"].as_u64().context("gain frame index")? as usize;
        let gain = frame["photometric_gain"]
            .as_f64()
            .context("source photometric gain")? as f32;
        ensure!(
            i < count && gain.is_finite() && gain > 0. && gain <= 64.,
            "invalid source gain binding"
        );
        ensure!(gains[i].is_nan(), "duplicate source gain binding");
        gains[i] = gain;
    }
    ensure!(
        gains.iter().all(|v| v.is_finite()),
        "incomplete source gain binding"
    );
    Ok(gains)
}
fn validate_selection(targets: &[usize], guides: &[usize], sources: usize) -> Result<()> {
    ensure!(
        (4..=14).contains(&targets.len()) && (2..=4).contains(&guides.len()),
        "bounded pilot requires4..14 targets and2..4 disjoint guides"
    );
    let unique: BTreeSet<_> = targets.iter().chain(guides).copied().collect();
    ensure!(
        unique.len() == targets.len() + guides.len() && unique.iter().all(|i| *i < sources),
        "duplicate, overlapping or out-of-range target/guide selection"
    );
    Ok(())
}
fn main() -> Result<()> {
    let args = Args::parse();
    let started = Instant::now();
    ensure!(
        (16..=256).contains(&args.size) && args.size % 2 == 0,
        "size must be even in 16..256"
    );
    ensure!((1..=16).contains(&args.workers), "workers outside 1..16");
    rayon::ThreadPoolBuilder::new()
        .num_threads(args.workers)
        .build_global()?;
    ensure!(
        args.assumed_registration_sigma_sensor.is_finite()
            && args.assumed_registration_sigma_sensor >= 0.,
        "invalid diagnostic assumed sigma"
    );
    ensure!(args.cache.is_dir(), "existing source cache required");
    let session: ResolvedSession =
        serde_json::from_slice(&fs::read(args.render_dir.join("session.json"))?)?;
    let ids: Vec<SourceIdentity> =
        serde_json::from_slice(&fs::read(args.render_dir.join("source-identities.json"))?)?;
    ensure!(
        ids.len() == session.len() && session.passes.len() == 2,
        "expected recorded two-pass session"
    );
    ensure!(
        session
            .frames
            .iter()
            .zip(&ids)
            .all(|(frame, id)| frame.path == id.path
                && frame.bytes == id.bytes
                && frame.modified_unix_nanos == id.modified_unix_nanos),
        "session frames differ from original identities"
    );
    let digests: BTreeSet<_> = ids.iter().map(|v| &v.sha256).collect();
    ensure!(digests.len() == ids.len(), "duplicate original bytes");
    let alignment = json_read(&args.render_dir.join("alignment.json"))?;
    ensure!(
        serde_json::to_value(&ids)? == alignment["binding"]["sources"],
        "source bindings differ"
    );
    ensure!(
        serde_json::to_value(&session.spec)? == alignment["binding"]["session"],
        "session specification differs from alignment binding"
    );
    let map = WarpMap::from_text(
        alignment["warpmap"]
            .as_str()
            .context("warpmap text missing")?,
    )?;
    let report = json_read(&args.render_dir.join("render-report.json"))?;
    let calibration = json_read(&args.render_dir.join("calibration.json"))?;
    let reference_pass = report["development_reference_pass"]
        .as_u64()
        .context("missing development reference")? as usize;
    let cal = calibration
        .get(reference_pass)
        .context("development reference outside calibration")?;
    ensure!(
        calibration
            .as_array()
            .context("calibration array")?
            .iter()
            .all(|c| c["noise_planes"] == cal["noise_planes"]),
        "pilot requires identical calibrated sensor noise; source exposure gains are applied separately"
    );
    ensure!(
        report["recipe"]["exposure_ev"].as_f64() == Some(0.),
        "ROI inversion currently requires zero additional output exposure"
    );
    let source_gains = render_source_gains(&report, session.len())?;
    let pn: Vec<PlaneNoise> = cal["noise_planes"]
        .as_array()
        .context("missing noise planes")?
        .iter()
        .map(|v| PlaneNoise {
            gain_dn_per_e: v["gain_dn_per_e"].as_f64().unwrap() as f32,
            read_noise_e: v["read_noise_e"].as_f64().unwrap() as f32,
            levels: Levels {
                black: v["black"].as_f64().unwrap() as f32,
                white: v["white"].as_f64().unwrap() as f32,
            },
        })
        .collect();
    let pn: [PlaneNoise; 4] = pn
        .try_into()
        .map_err(|_| anyhow::anyhow!("four planes required"))?;
    let noise = NoiseModel::new(
        pn,
        cal["iso"].as_f64().context("ISO")? as f32,
        Provenance::Profile,
    );
    let meta = session.frames[session.passes[reference_pass].global_range.start].read_metadata()?;
    let profile = profile_for_capture_env(meta.camera_model.as_deref(), meta.lens_type3)?;
    ensure!(
        profile.map(|p| p.key) == cal["optical_profile"]["key"].as_str(),
        "applied optics profile differs"
    );
    if !args.census_rois.is_empty() {
        return focus_census::run(
            &args,
            &session,
            &ids,
            &map,
            &noise,
            profile,
            &calibration,
            &alignment,
        );
    }
    let targets = if args.targets.is_empty() {
        TARGETS.to_vec()
    } else {
        args.targets.clone()
    };
    let guides = if args.guides.is_empty() {
        GUIDES.to_vec()
    } else {
        args.guides.clone()
    };
    validate_selection(&targets, &guides, session.len())?;
    let g = map.geometry();
    let ox = args.x.unwrap_or(g.width - args.size / 2);
    let oy = args.y.unwrap_or(g.height + 300 - args.size / 2);
    let l = OutputLattice {
        full: g,
        origin_sensor: [ox as f64, oy as f64],
        step_sensor: [1.; 2],
        width: args.size,
        height: args.size,
    };
    let n = args.size * args.size;
    let halo = window_radius() + 1 + REGULARISER_RADIUS + 3;
    ensure!(ox / 2 >= halo && oy / 2 >= halo, "ROI lacks focus halo");
    let domain = SamplingDomain {
        full: g,
        x: ox / 2 - halo,
        y: oy / 2 - halo,
        width: args.size / 2 + 2 * halo + 2,
        height: args.size / 2 + 2 * halo + 2,
    };
    domain.validate()?;
    ensure!(
        domain.width * 2 <= 384 && domain.height * 2 <= 384,
        "expanded focus ROI exceeds authorized 384 sensor-pixel side"
    );
    let reserved = CACHE_BUDGET
        + (512 << 20)
        + if args.measure_registration {
            64 << 20
        } else {
            0
        };
    ensure!(reserved <= TOTAL_LIMIT, "resident reservation above 2 GiB");
    let out = session.ensure_fresh_output(&args.out)?;
    fs::create_dir(&out)?;
    let setup = Instant::now();
    // Master is read and dropped before original handles are pinned. It is a
    // dependent native fallback, never truth or an independent noise reference.
    let master = strehl_edit::load_tiff(&args.render_dir.join("master.tiff"))?;
    ensure!(
        master.origin == ImageOrigin::SceneLinear,
        "native fallback is not scene linear"
    );
    let crop = report["canvas"].as_array().context("canvas missing")?;
    let mx = 2 * crop[0].as_u64().unwrap() as usize;
    let my = 2 * crop[1].as_u64().unwrap() as usize;
    ensure!(
        ox >= mx
            && oy >= my
            && ox + args.size <= mx + master.width as usize
            && oy + args.size <= my + master.height as usize,
        "ROI outside native master"
    );
    let wb: [f32; 3] = serde_json::from_value(cal["white_balance"].clone())?;
    let matrix: [[f32; 3]; 3] = serde_json::from_value(cal["color_matrix"][0].clone())?;
    let render = color::camera_to_srgb(matrix)
        .context("invalid camera matrix")?
        .with_saturation(pn[0].levels, wb, 1.);
    let inv = inverse(*render.matrix())?;
    let knee = strehl_core::highlight::knee().unwrap_or(1.0);
    let mut fallback = Vec::with_capacity(n);
    let mut native = Vec::with_capacity(n * 3);
    let mut native_eligible = Vec::with_capacity(n);
    let mut roundtrip_max = 0f32;
    for y in 0..args.size {
        for x in 0..args.size {
            let i = ((oy - my + y) * master.width as usize + (ox - mx + x)) * 3;
            let rgb: [f32; 3] = master.pixels[i..i + 3].try_into().unwrap();
            match native_camera_pixel(rgb, &render, inv, wb, pn[0].levels, knee) {
                Some((camera, error)) => {
                    fallback.push(camera);
                    native_eligible.push(true);
                    roundtrip_max = roundtrip_max.max(error);
                }
                None => {
                    fallback.push([0.; 3]);
                    native_eligible.push(false);
                }
            }
            native.extend(rgb);
        }
    }
    ensure!(
        roundtrip_max < 2e-6,
        "native common-transform inversion failed"
    );
    let baseline = master.baseline;
    drop(master);
    let historical_binding = if args.historical_cache {
        Some(historical_cache::binding()?)
    } else {
        None
    };
    let mut cache = if args.historical_cache {
        OriginalCache::Historical(historical_cache::HistoricalCache::new(
            &args.cache,
            &ids,
            CACHE_BUDGET,
            g,
        )?)
    } else {
        OriginalCache::Current(SourceCache::new(&args.cache, &session, CACHE_BUDGET)?)
    };
    // Refuse before any work if an original entry is missing. load() below still
    // validates its header/digest and source stamp, and cannot call a decoder.
    for id in &ids {
        ensure!(
            cache.cache_path(id)?.is_file(),
            "missing original cache: {}",
            id.path.display()
        );
    }
    let focus_start = Instant::now();
    let focus = if args.geometry_without_focus {
        // These deliberately empty fields cannot qualify a source. This mode
        // returns at the geometry-only boundary before any reconstruction.
        session
            .passes
            .iter()
            .map(|pass| FocusSlice {
                frames: pass
                    .global_range
                    .clone()
                    .map(|global_index| FocusFrame {
                        acquisition: global_index as u64,
                        global_index,
                    })
                    .collect(),
                ordinal: vec![f32::NAN; domain.width * domain.height],
                width_frames: vec![0.; domain.width * domain.height],
                flags: vec![32; domain.width * domain.height],
                usable: vec![false; domain.width * domain.height],
            })
            .collect()
    } else if let (Some(census), Some(seal)) = (&args.focus_census, &args.focus_seal) {
        for id in &ids {
            id.check_unchanged()?;
        }
        let ranges: Vec<_> = session
            .passes
            .iter()
            .map(|p| p.global_range.clone())
            .collect();
        focus_artifact::load(
            census,
            seal,
            focus_artifact::Binding {
                domain,
                roi_sensor: [ox, oy, args.size, args.size],
                roi_index: args.focus_roi,
                pass_ranges: &ranges,
                alignment_path: &args.render_dir.join("alignment.json"),
                calibration_path: &args.render_dir.join("calibration.json"),
                identities_path: &args.render_dir.join("source-identities.json"),
            },
        )?
    } else {
        let mut focus = Vec::new();
        for pass in 0..2 {
            focus.push(focus_pass(
                &session, &ids, pass, &map, &mut cache, domain, &noise, profile,
            )?);
        }
        focus
    };
    for (pass, field) in focus
        .iter()
        .enumerate()
        .filter(|_| !args.geometry_without_focus)
    {
        write_f32(
            &out.join(format!("focus-pass-{pass}-ordinal.f32")),
            field.ordinal.iter().copied(),
        )?;
        write_f32(
            &out.join(format!("focus-pass-{pass}-width.f32")),
            field.width_frames.iter().copied(),
        )?;
        write_new(
            &out.join(format!("focus-pass-{pass}-flags.u8")),
            &field.flags,
        )?;
    }
    let focus_seconds = focus_start.elapsed().as_secs_f64();
    let dg = PlaneGeometry {
        width: domain.width,
        height: domain.height,
    };
    let dn = dg.pixels();
    let mut originals = Vec::new();
    for &i in &targets {
        originals.push(cache.load(&ids[i])?.context("target cache miss")?);
    }
    let mut sampler = NativeSampler::new(domain)?;
    let mut scratch = vec![0.; dn];
    let mut blur = vec![0.; dn];
    let mut green_buf = vec![0.; dn];
    let mut guide_planes: [Vec<f32>; 3] = std::array::from_fn(|_| vec![0.; dn]);
    let mut guide_valid = vec![true; dn];
    for &i in &guides {
        let source = cache.load(&ids[i])?.context("guide cache miss")?;
        let sampled = sampler.gather(
            source.as_ref(),
            source.levels(),
            map.placement(i)?,
            profile,
            map.resampler(),
        )?;
        for c in 0..3 {
            let plane = match c {
                0 => &sampled.planes[0],
                2 => &sampled.planes[2],
                _ => {
                    green(&sampled.planes, &mut green_buf);
                    &green_buf
                }
            };
            box_mean(plane, dg, 3, &mut scratch, &mut blur);
            for p in 0..dn {
                guide_planes[c][p] += blur[p] * source_gains[i] / guides.len() as f32;
            }
        }
        let mut masks = vec![0u32; dn];
        let mut supported = vec![false; dn];
        complete_support(&sampled.support, dg, 6, &mut masks, &mut supported)?;
        for p in 0..dn {
            guide_valid[p] &= supported[p];
        }
    }
    let coords: Vec<_> = (0..n)
        .map(|i| {
            let p = l.position(i % args.size, i / args.size);
            [
                (p[0] - 0.5) * 0.5 - domain.x as f64,
                (p[1] - 0.5) * 0.5 - domain.y as f64,
            ]
        })
        .collect();
    let nearest: Vec<_> = coords
        .iter()
        .map(|p| p[1].round() as usize * dg.width + p[0].round() as usize)
        .collect();
    let mut expected: Vec<_> = coords
        .iter()
        .map(|p| std::array::from_fn(|c| interp(&guide_planes[c], dg, p[0], p[1])))
        .collect();
    let mut tensor: Vec<_> = coords
        .iter()
        .map(|p| {
            let dx = (interp(&guide_planes[1], dg, p[0] + 1., p[1])
                - interp(&guide_planes[1], dg, p[0] - 1., p[1]))
                * 0.25;
            let dy = (interp(&guide_planes[1], dg, p[0], p[1] + 1.)
                - interp(&guide_planes[1], dg, p[0], p[1] - 1.))
                * 0.25;
            // Numerical diagonal cushion keeps the rounded outer product PSD.
            let jitter = (dx * dx + dy * dy) * 1e-6 + 1e-6;
            [dx * dx + jitter, dx * dy, dy * dy + jitter]
        })
        .collect();
    for p in 0..n {
        if !native_eligible[p] {
            expected[p] = [0.; 3];
            tensor[p] = [0.; 3];
        }
    }
    let mut fields = Vec::new();
    let mut source_reports = Vec::new();
    let guide_calibrations: Vec<_> = guides
        .iter()
        .map(|&i| coherent_motion::Calibration {
            noise: pn,
            gain: source_gains[i],
        })
        .collect();
    for (s, &i) in targets.iter().enumerate() {
        ensure!(
            originals[s].levels() == pn[0].levels,
            "target levels mismatch"
        );
        let sampled = sampler.gather(
            originals[s].as_ref(),
            originals[s].levels(),
            map.placement(i)?,
            profile,
            map.resampler(),
        )?;
        green(&sampled.planes, &mut green_buf);
        box_mean(&green_buf, dg, 3, &mut scratch, &mut blur);
        let mut motion_mask_scratch = vec![0u32; dn];
        let mut motion_support = vec![false; dn];
        complete_support(
            &sampled.support,
            dg,
            4,
            &mut motion_mask_scratch,
            &mut motion_support,
        )?;
        let pass = session.frames[i].pass_index;
        let ordinal = i - session.passes[pass].global_range.start;
        let f = &focus[pass];
        let mut a = OwnedAdmission {
            focus: vec![0.; n],
            motion: vec![0.; n],
            valid: vec![false; n],
            sigma: vec![args.assumed_registration_sigma_sensor; n],
        };
        for p in 0..n {
            let q = nearest[p];
            let xy = coords[p];
            a.focus[p] =
                focus_mode_response(ordinal as f32, f.ordinal[q], f.width_frames[q], f.usable[q]);
            a.valid[p] =
                native_eligible[p] && guide_valid[q] && motion_support[q] && a.focus[p] > 0.;
            let gain = source_gains[i];
            let measured = interp(&blur, dg, xy[0], xy[1]) * gain;
            let variance = 2. * pn[1].variance(expected[p][1] / gain) * gain * gain;
            // Conservative unfiltered calibrated variance, plus frozen gradient
            // structure allowance; policy confidence, not calibrated probability.
            let structure = (tensor[p][0] + tensor[p][2]) * 4.;
            a.motion[p] =
                guide_motion_confidence(measured - expected[p][1], variance, structure, 4.);
        }
        if args.coherent_color_motion {
            a.motion = coherent_motion::confidences(
                &sampled.planes,
                coherent_motion::Calibration {
                    noise: pn,
                    gain: source_gains[i],
                },
                coherent_motion::Guide {
                    geometry: dg,
                    planes: &guide_planes,
                    coords: &coords,
                    expected: &expected,
                    calibrations: &guide_calibrations,
                },
            );
        }
        source_reports.push(json!({"global_index":i,"pass":pass,"source":ids[i],"photometric_gain":source_gains[i],"focus_usable_pixels":a.valid.iter().filter(|v|**v).count(),"motion_positive_pixels":a.motion.iter().filter(|v|**v>0.).count(),"focus_weight_sum":a.focus.iter().map(|v|f64::from(*v)).sum::<f64>()}));
        fields.push(a);
    }
    drop(sampler);
    let cache_stats = cache.stats();
    ensure!(cache_stats.decodes == 0, "RAW decode occurred");
    drop(cache);
    let pulls = targets
        .iter()
        .map(|&i| map.placement(i).map(|p| channel_pulls(p, profile)))
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let mut inputs = Inputs {
        acquisitions: targets.clone(),
        gains: targets.iter().map(|&i| source_gains[i]).collect(),
        config: Config {
            model: if args.affine_reconstruction {
                RegressionModel::LocalAffine
            } else {
                RegressionModel::LocalConstant
            },
            ..Config::default()
        },
        lattice: l,
        originals,
        pulls,
        noise: pn,
        fields,
        expected,
        tensor,
        fallback,
        fallback_valid: native_eligible.clone(),
    };
    if args.original_patch_diagnostics {
        original_patch_diagnostics::export(&inputs, &out)?;
    }
    ensure!(
        !args.refine_registration || args.registration_only || args.require_registration,
        "corrected reconstruction requires its measured registration admission"
    );
    let mut local_registration_report = None;
    if args.measure_registration {
        let measured = local_registration_pilot::measure(
            &inputs,
            args.registration_window_quad,
            local_registration::Policy {
                geometry_lowpass_sigma_quad: args.registration_geometry_sigma_quad,
                tile_quad: args.registration_tile_quad,
                grid_axis: args.registration_grid_axis,
                ..Default::default()
            },
            args.refine_registration,
            args.registration_patch_diagnostics,
        )?;
        let envelope = json!({"command":std::env::args().collect::<Vec<_>>(),"build":env!("STREHL_BUILD_ID"),"source_identities":source_reports,"alignment_sha256":hash(&args.render_dir.join("alignment.json"))?,"focus_seal_sha256":args.focus_seal.as_ref().map(|p|hash(p)).transpose()?,"cache_disk_hits":cache_stats.disk_hits,"raw_decodes":cache_stats.decodes,"measurement":measured.report,"focus_not_evaluated_geometry_only":args.geometry_without_focus});
        write_new(
            &out.join("local-registration-report.json"),
            &serde_json::to_vec_pretty(&envelope)?,
        )?;
        if args.registration_only {
            println!("{}", serde_json::to_string_pretty(&envelope)?);
            return Ok(());
        }
        if args.require_registration {
            inputs.pulls = measured.consuming_pulls.clone();
            if args.refine_registration {
                // Re-evaluate source-dependent motion/support on the exact pulls
                // the direct CFA estimator consumes. Independent guide and full
                // track focus evidence remain frozen, explicitly conditional.
                let mut corrected_sampler =
                    strehl_cli::session_reconstruction_sampling::RegionSampler::new(
                        domain,
                        64 << 20,
                    )?;
                for (s, original) in inputs.originals.iter().enumerate() {
                    let sampled = corrected_sampler.gather_pulls(
                        original.as_ref(),
                        original.levels(),
                        inputs.pulls[s],
                        map.resampler(),
                    )?;
                    green(&sampled.planes, &mut green_buf);
                    box_mean(&green_buf, dg, 3, &mut scratch, &mut blur);
                    let mut masks = vec![0u32; dn];
                    let mut support = vec![false; dn];
                    complete_support(&sampled.support, dg, 4, &mut masks, &mut support)?;
                    let field = &mut inputs.fields[s];
                    let gain = inputs.gains[s];
                    for p in 0..n {
                        let q = nearest[p];
                        let xy = coords[p];
                        field.valid[p] = native_eligible[p]
                            && guide_valid[q]
                            && support[q]
                            && field.focus[p] > 0.;
                        let value = interp(&blur, dg, xy[0], xy[1]) * gain;
                        let variance =
                            2. * pn[1].variance(inputs.expected[p][1] / gain) * gain * gain;
                        let structure = (inputs.tensor[p][0] + inputs.tensor[p][2]) * 4.;
                        field.motion[p] = guide_motion_confidence(
                            value - inputs.expected[p][1],
                            variance,
                            structure,
                            4.,
                        );
                    }
                    if args.coherent_color_motion {
                        field.motion = coherent_motion::confidences(
                            &sampled.planes,
                            coherent_motion::Calibration { noise: pn, gain },
                            coherent_motion::Guide {
                                geometry: dg,
                                planes: &guide_planes,
                                coords: &coords,
                                expected: &inputs.expected,
                                calibrations: &guide_calibrations,
                            },
                        );
                    }
                }
            }
            for (i, field) in inputs.fields.iter_mut().enumerate() {
                if !measured.admitted[i] {
                    field.valid.fill(false);
                }
                // Historical field name; observed local consistency only,
                // neither statistical sigma nor guaranteed true-error bound.
                field.sigma.fill(measured.bound_sensor[i]);
            }
        }
        local_registration_report = Some(envelope);
    }
    if args.heldout_prediction {
        let prediction = heldout_original_prediction::evaluate(&inputs, wb)?;
        write_new(
            &out.join("heldout-original-prediction.json"),
            &serde_json::to_vec_pretty(&prediction)?,
        )?;
    }
    let preparation_seconds = setup.elapsed().as_secs_f64();
    let scalar_start = Instant::now();
    let scalar = inputs.tile(0, args.size)?;
    let scalar_seconds = scalar_start.elapsed().as_secs_f64();
    let rows = args.size.div_ceil(args.workers);
    let tiles: Vec<_> = (0..args.size)
        .step_by(rows)
        .map(|y| (y, rows.min(args.size - y)))
        .collect();
    let parallel_start = Instant::now();
    let parallel = tiles
        .par_iter()
        .map(|&(y, h)| inputs.tile(y, h))
        .collect::<Result<Vec<_>>>()?;
    let parallel_seconds = parallel_start.elapsed().as_secs_f64();
    let mut cursor = 0;
    for tile in &parallel {
        for p in 0..tile.rgb.len() {
            let q = cursor + p;
            ensure!(
                tile.rgb[p].map(f32::to_bits) == scalar.rgb[q].map(f32::to_bits)
                    && tile.variance[p].map(f32::to_bits) == scalar.variance[q].map(f32::to_bits)
                    && tile.variance_valid[p] == scalar.variance_valid[q]
                    && tile.reason[p] == scalar.reason[q]
                    && tile.phase_condition[p].map(f32::to_bits)
                        == scalar.phase_condition[q].map(f32::to_bits)
                    && tile.independent_acquisitions[p] == scalar.independent_acquisitions[q]
                    && tile.accepted_samples[p] == scalar.accepted_samples[q]
                    && tile.clipped_samples[p] == scalar.clipped_samples[q]
                    && tile.valid[p] == scalar.valid[q],
                "scalar/parallel bits differ at {q}"
            );
        }
        cursor += tile.rgb.len();
    }
    ensure!(
        cursor == n
            && scalar
                .valid
                .iter()
                .zip(&native_eligible)
                .all(|(valid, eligible)| *valid || !*eligible),
        "invalid pilot output"
    );
    let coherent: Vec<_> = (0..n)
        .map(|i| coherent_output(native_eligible[i], scalar.reason[i]))
        .collect();
    let mut developed = Vec::with_capacity(n * 3);
    let mut reason_counts = [[0usize; 7]; 3];
    let mut unknown = [0usize; 3];
    for i in 0..n {
        let original: [f32; 3] = native[3 * i..3 * i + 3].try_into().unwrap();
        let rgb = final_scene_pixel(
            original,
            native_eligible[i],
            scalar.rgb[i],
            scalar.reason[i],
            &render,
            wb,
            pn[0].levels,
        );
        if !native_eligible[i] {
            ensure!(
                rgb.map(f32::to_bits) == original.map(f32::to_bits),
                "nonlinear native pixel changed"
            );
        }
        developed.extend(rgb);
        for c in 0..3 {
            reason_counts[c][scalar.reason[i][c] as usize] += 1;
            unknown[c] += usize::from(!coherent[i] || !scalar.variance_valid[i][c]);
        }
    }
    let mut matched_count = 0usize;
    if args.matched_comparator {
        let predictions = heldout_original_prediction::matched_roi(&inputs, &coherent, wb);
        let mut matched = Vec::with_capacity(n * 3);
        for (i, prediction) in predictions.iter().enumerate() {
            let original = native[3 * i..3 * i + 3].try_into().unwrap();
            let rgb = if let Some(prediction) = prediction {
                matched_count += 1;
                final_scene_pixel(
                    original,
                    true,
                    *prediction,
                    [Reason::Reconstructed; 3],
                    &render,
                    wb,
                    pn[0].levels,
                )
            } else {
                original
            };
            matched.extend(rgb);
        }
        strehl_edit::save_linear_tiff(
            &out.join("matched-cfa-mhc.tiff"),
            &LinearImage {
                width: args.size as u32,
                height: args.size as u32,
                pixels: matched,
                origin: ImageOrigin::SceneLinear,
                baseline,
                baked_recipe: None,
            },
        )?;
        write_new(
            &out.join("matched-cfa-mhc-support.u8"),
            &predictions
                .iter()
                .map(|p| u8::from(p.is_some()))
                .collect::<Vec<_>>(),
        )?;
    }
    for (name, pixels) in [("candidate.tiff", developed), ("native.tiff", native)] {
        let image = LinearImage {
            width: args.size as u32,
            height: args.size as u32,
            pixels,
            origin: ImageOrigin::SceneLinear,
            baseline,
            baked_recipe: None,
        };
        strehl_edit::save_linear_tiff(&out.join(name), &image)?;
    }
    write_new(
        &out.join("native-linear-eligible.u8"),
        &native_eligible
            .iter()
            .map(|v| u8::from(*v))
            .collect::<Vec<_>>(),
    )?;
    write_f32(
        &out.join("channel-candidate-rgb.f32"),
        scalar.rgb.iter().flatten().copied(),
    )?;
    write_f32(
        &out.join("channel-candidate-conditional-variance.f32"),
        scalar.variance.iter().flatten().copied(),
    )?;
    write_f32(
        &out.join("phase-condition.f32"),
        scalar.phase_condition.iter().flatten().copied(),
    )?;
    write_new(
        &out.join("reason.u8"),
        &scalar
            .reason
            .iter()
            .flatten()
            .map(|r| *r as u8)
            .collect::<Vec<_>>(),
    )?;
    write_new(
        &out.join("channel-candidate-variance-valid.u8"),
        &scalar
            .variance_valid
            .iter()
            .flatten()
            .map(|v| u8::from(*v))
            .collect::<Vec<_>>(),
    )?;
    write_new(
        &out.join("coherent-rgb-mask.u8"),
        &coherent.iter().map(|v| u8::from(*v)).collect::<Vec<_>>(),
    )?;
    write_f32(
        &out.join("camera-rgb.f32"),
        (0..n).flat_map(|i| {
            if coherent[i] {
                scalar.rgb[i]
            } else if native_eligible[i] {
                inputs.fallback[i]
            } else {
                [f32::NAN; 3]
            }
        }),
    )?;
    write_f32(
        &out.join("conditional-variance.f32"),
        (0..n).flat_map(|i| {
            if coherent[i] {
                scalar.variance[i]
            } else {
                [f32::NAN; 3]
            }
        }),
    )?;
    write_new(
        &out.join("variance-valid.u8"),
        &(0..n)
            .flat_map(|i| scalar.variance_valid[i].map(|v| u8::from(v && coherent[i])))
            .collect::<Vec<_>>(),
    )?;
    let focus_report:Vec<_>=focus.iter().enumerate().map(|(pass,f)|{let flags:Vec<_>=(0..7).map(|b|nearest.iter().filter(|&&i|f.flags[i]&(1<<b)!=0).count()).collect();json!({"pass":pass,"full_track_frames":f.frames.len(),"usable_pixels":nearest.iter().filter(|&&i|f.usable[i]).count(),"flag_bits_1_2_4_8_16_32_64":flags})}).collect();
    let result = json!({"schema":"strehl.sr-roi-pilot.v1","command":std::env::args().collect::<Vec<_>>(),"build":env!("STREHL_BUILD_ID"),"source_sha256":hex(&Sha256::digest(include_bytes!("roi-pilot.rs"))),"reconstruction_sha256":hex(&Sha256::digest(include_bytes!("../../../../crates/strehl-core/src/reconstruction.rs"))),"affine_sha256":hex(&Sha256::digest(include_bytes!("../../../../crates/strehl-core/src/reconstruction-affine.rs"))),"regression_model":format!("{:?}",inputs.config.model),"input_render":args.render_dir,"alignment_sha256":hash(&args.render_dir.join("alignment.json"))?,"warpmap_sha256":alignment["warpmap_sha256"],"full_guide_geometry":[g.width,g.height],"roi_sensor":[ox,oy,args.size,args.size],"focus_domain_quad":[domain.x,domain.y,domain.width,domain.height],"focus":focus_report,"sources":source_reports,"guide_acquisitions":guides.iter().map(|&i|json!({"global_index":i,"source":ids[i],"photometric_gain":source_gains[i]})).collect::<Vec<_>>(),"noise_planes":cal["noise_planes"],"common_color_transform_inverse_max_error":roundtrip_max,"highlight_knee":knee,"white_balance":wb,"relative_to_native_variance_gate_available":false,"phase_weight_policy":"exact Gaussian/precision/admission design; affine additionally requires actual absolute-influence phase support","kernel_sigma_sensor":Config::default().sigma_sensor,"focus_policy":"qualified full-track mode, abs(ordinal-mode)<=one measured width; absolute normalized response floor exp(-1/2)","coherent_rgb_policy":"replace native pixel only when all three channels independently reconstruct; retain per-channel diagnostic reasons","coherent_rgb_reconstructed_pixels":coherent.iter().filter(|v|**v).count(),"matched_cfa_mhc_comparator_pixels":matched_count,"matched_comparator_policy":"same target acquisitions and point-frozen focus/motion/geometry; bilinear original CFA into local final mosaic then one MHC, common candidate support; retains exact native elsewhere; different kernel footprint is intentional placebo","saved_array_policy":"channel-candidate-* and reason.u8 are per-component diagnostics; camera-rgb/conditional-variance/variance-valid describe coherent delivered output; noninvertible camera RGB and unknown variance use NaN","noninvertible_native_pixels":native_eligible.iter().filter(|v|!**v).count(),"noninvertible_native_policy":"no camera-DN candidate or prediction; exact existing scene-linear native RGB retained","noninvertible_native_output_bits_unchanged":true,"variance_unknown_channels":unknown,"reason_order":["reconstructed","too_few_acquisitions","ill_conditioned","rejected_or_missing","excess_variance","missing_fallback","kernel_overshoot"],"reason_counts_rgb":reason_counts,"source_gains":inputs.gains,"development_reference_pass":reference_pass,"assumed_registration_sigma_sensor":args.assumed_registration_sigma_sensor,"corrected_motion_policy":if args.refine_registration {"original green gathered at returned consuming pulls; full-track focus and withheld guide stay frozen in original output gauge"} else {"saved pulls"},"registration_policy":if args.require_registration {"measured local anchor-relative heldout pair/cycle consistency; observed consistency threshold, not calibrated sigma or a true-error guarantee"} else {"oracle-assumed diagnostic only; no measured local registration certificate"},"local_registration":local_registration_report,"variance_scope":"conditional on frozen guide and admission; adaptive focus/motion uses target photons; local-constant guide shot-noise approximation","guide_scope":"independent acquisition photons, held-out nearby focus; motion/focus admission is adaptive; native master is dependent fallback, not truth","memory_reserved_bytes":reserved,"resident_original_target_handles":targets.len(),"maximum_external_source_handles":targets.len()+1,"maximum_resident_originals_from_budget":18,"historical_cache_binding":historical_binding,"raw_decodes":cache_stats.decodes,"cache_disk_hits":cache_stats.disk_hits,"cache_peak_cfa_bytes":cache_stats.peak_resident_cfa_bytes,"workers":args.workers,"scalar_seconds":scalar_seconds,"parallel_seconds":parallel_seconds,"scalar_parallel_all_bits_equal":true,"preparation_seconds":preparation_seconds,"whole_track_focus_seconds":focus_seconds,"reused_focus_census":args.focus_census,"reused_focus_seal_sha256":args.focus_seal.as_ref().map(|p|hash(p)).transpose()?,"total_seconds":started.elapsed().as_secs_f64(),"photographic_gain":"unverified; native ROI review only, complete-scene review still required"});
    let mut result = result;
    result["coherent_color_motion"] = json!(args.coherent_color_motion);
    result["appearance_admission_source_sha256"] = json!(hex(&Sha256::digest(include_bytes!(
        "../../../../crates/strehl-cli/src/session-reconstruction-motion.rs"
    ))));
    if args.coherent_color_motion {
        result["corrected_motion_policy"] = json!(if args.refine_registration {
            "exact product RGB confidence at corrected consuming pulls; guide and full-track focus remain frozen"
        } else {
            "exact product RGB confidence at saved pulls; guide and full-track focus remain frozen"
        });
    }
    write_new(
        &out.join("report.json"),
        &serde_json::to_vec_pretty(&result)?,
    )?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    Ok(())
}

#[cfg(test)]
#[path = "gauge-integration-tests.rs"]
mod gauge_integration_tests;

#[cfg(test)]
mod native_fallback_tests {
    use super::*;
    #[test]
    fn nonlinear_pixel_retains_exact_native_without_disabling_eligible_neighbors() {
        let levels = Levels {
            black: 512.,
            white: 15360.,
        };
        let wb = [1.6, 1., 2.7];
        let render = color::Render::new([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
            .with_saturation(levels, wb, 1.);
        let inv = inverse(*render.matrix()).unwrap();
        let knee = strehl_core::highlight::knee().unwrap_or(1.);
        let native = [
            render.develop([0.08, 0.12, 0.04]),
            render.develop(render.ceiling().map(|v| 0.99 * v)),
            render.develop([0.04, 0.07, 0.09]),
        ];
        let decoded: Vec<_> = native
            .iter()
            .map(|&rgb| native_camera_pixel(rgb, &render, inv, wb, levels, knee))
            .collect();
        assert!(decoded[0].is_some() && decoded[1].is_none() && decoded[2].is_some());
        for i in 0..3 {
            let result = final_scene_pixel(
                native[i],
                decoded[i].is_some(),
                [777.; 3],
                [Reason::Reconstructed; 3],
                &render,
                wb,
                levels,
            );
            if i == 1 {
                assert_eq!(result.map(f32::to_bits), native[i].map(f32::to_bits));
            } else {
                assert_ne!(result.map(f32::to_bits), native[i].map(f32::to_bits));
            }
        }
    }
    #[test]
    fn partial_channel_reconstruction_retains_whole_native_rgb_bits() {
        let levels = Levels {
            black: 512.,
            white: 15360.,
        };
        let wb = [1.6, 1., 2.7];
        let render = color::Render::new([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
            .with_saturation(levels, wb, 1.);
        let native = [0.08, -0.0, 0.04];
        for mask in 0..8 {
            let reasons = std::array::from_fn(|c| {
                if mask & (1 << c) != 0 {
                    Reason::Reconstructed
                } else {
                    Reason::IllConditioned
                }
            });
            let out = final_scene_pixel(native, true, [777.; 3], reasons, &render, wb, levels);
            if mask == 7 {
                assert_ne!(out.map(f32::to_bits), native.map(f32::to_bits));
            } else {
                assert_eq!(out.map(f32::to_bits), native.map(f32::to_bits));
            }
        }
    }
}

#[cfg(test)]
mod source_selection_tests {
    use super::*;
    #[test]
    fn geometry_without_focus_cannot_enable_a_render_or_claim_census() {
        let mut args = vec![
            "roi",
            "--render-dir",
            ".",
            "--cache",
            ".",
            "--out",
            ".",
            "--assumed-registration-sigma-sensor",
            "0.1",
            "--geometry-without-focus",
        ];
        assert!(Args::try_parse_from(&args).is_err());
        args.extend(["--measure-registration", "--registration-only"]);
        assert!(Args::try_parse_from(&args).unwrap().geometry_without_focus);
        let mut with_prediction = args.clone();
        with_prediction.push("--heldout-prediction");
        assert!(Args::try_parse_from(&with_prediction).is_err());
        args.extend(["--focus-census", "c", "--focus-seal", "s"]);
        assert!(Args::try_parse_from(&args).is_err());
    }
    #[test]
    fn recorded_source_gain_binding_is_complete_unique_and_exact() {
        let report = json!({"frames":[{"frame":1,"photometric_gain":1.0},{"frame":0,"photometric_gain":2.533541440963745}]});
        let gains = render_source_gains(&report, 2).unwrap();
        assert_eq!(gains[0].to_bits(), 2.5335414_f32.to_bits());
        assert_eq!(gains[1], 1.);
        for bad in [
            json!({"frames":[{"frame":0,"photometric_gain":1.}]}),
            json!({"frames":[{"frame":0,"photometric_gain":1.},{"frame":0,"photometric_gain":1.}]}),
            json!({"frames":[{"frame":0,"photometric_gain":0.},{"frame":1,"photometric_gain":1.}]}),
        ] {
            assert!(render_source_gains(&bad, 2).is_err());
        }
    }
    #[test]
    fn bounded_target_and_guide_sets_cannot_overlap_or_exceed_source_census() {
        let targets: Vec<_> = (0..14).collect();
        let guides: Vec<_> = (14..18).collect();
        validate_selection(&targets, &guides, 18).unwrap();
        assert!(validate_selection(&targets, &[13, 15, 16, 17], 18).is_err());
        assert!(validate_selection(&targets, &guides, 17).is_err());
        validate_selection(&targets[..7], &guides[..2], 18).unwrap();
        assert!(validate_selection(&targets[..3], &guides, 18).is_err());
        assert!(validate_selection(&targets, &guides[..1], 18).is_err());
    }
}

#[path = "original-patch-diagnostics.rs"]
mod original_patch_diagnostics;
