//! M90 — PRNU in the noise model: the correction, its identity proof, and its
//! blast radius.
//!
//! Not a product path. This is the instrument for
//! `docs/research/M90-prnu-noise-model.md`.
//!
//! # Subcommands
//!
//! ```text
//! cargo run --release -p strehl-cli --example m90-prnu -- identity [--out PATH] [--stack DIR] [--limit N]
//! ```
//!
//! `identity` writes a deterministic binary blob summarising **everything the
//! default path computes** from the noise model: a dense per-plane variance and
//! sigma table over the whole container range at eleven ISOs, the green-luma
//! sigma over the same range, and a full synthetic two-pass merge — focus field,
//! regulariser, election, gate, `n_eff`, the four merged planes,
//! `predicted_sigma` and `disagreement`. Hash the blob before and after a change
//! to `noise.rs` or `profile.rs`; an unchanged hash is the bit-identity proof
//! Deliverable A requires.
//!
//! **This subcommand deliberately uses only API that existed before M90.** It is
//! written and run *first*, at the pre-change revision, so the baseline hash is
//! produced by code that cannot know what the change will be.
//!
//! The synthetic plant supplies its **own** noise constants rather than drawing
//! them from [`strehl_core::noise`] — AGENTS rule 34: a plant that draws its
//! noise from the constant under test is scale-invariant in it and cannot detect
//! it being wrong.
//!
//! **Reads only.** It never writes to a stack directory.

use std::io::Write;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::CfaPlane;
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::FocusField;
use strehl_core::merge::{DEFAULT_GATE, Estimator, FocusStats, Gate, regularise};
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Reference levels for the A7C II, as `M1` measured them.
const BLACK: f32 = 512.0;
const WHITE: f32 = 15360.0;

/// Every ISO the profile can distinguish, including both sides of the dual-gain
/// switch and the extended-ISO floor.
const ISOS: [f32; 11] = [
    50.0, 100.0, 160.0, 200.0, 400.0, 500.0, 640.0, 800.0, 1000.0, 1600.0, 2000.0,
];

/// Signal sweep for the identity table: every integer DN the container can hold.
const SWEEP_MAX: u32 = 16_383;

// ---------------------------------------------------------------------------
// a deterministic synthetic stack
// ---------------------------------------------------------------------------

/// SplitMix64. Copied rather than imported so the plant's stream is fixed by
/// this file and cannot drift with a library change.
struct Rng(u64);

impl Rng {
    fn new(seed: u64) -> Self {
        Rng(seed)
    }
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn uniform(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64 + 1.0) / (1u64 << 53) as f64
    }
    fn normal(&mut self) -> f64 {
        let (u1, u2) = (self.uniform(), self.uniform());
        (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
    }
}

/// A synthetic mosaiced frame, `2*width x 2*height` samples with no padding.
struct SynthFrame {
    geom: PlaneGeometry,
    rows: Vec<u16>,
}

impl QuadSource for SynthFrame {
    fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
        let w = 2 * self.geom.width;
        let base = 2 * py * w;
        let (a, b) = self.rows[base..base + 2 * w].split_at(w);
        (a, b)
    }
}

/// Plant geometry. Small enough to run in a second, large enough that the
/// 27-box focus window and the 17-box regulariser both have interior.
const PLANT_W: usize = 192;
const PLANT_H: usize = 144;
const PLANT_FRAMES: u16 = 9;

/// The plant's own gain and read noise, in DN. **Not** read from the profile —
/// rule 34.
const PLANT_GAIN_DN_PER_E: f64 = 0.2290;
const PLANT_READ_DN: f64 = 0.9615;

/// Build frame `k` of the synthetic stack.
///
/// The scene is a horizontal signal ramp from near-black to near-clipping, so a
/// single frame spans the whole working range of the noise model, crossed with a
/// vertical sweep of the in-focus frame index. Detail is a fixed high-frequency
/// block pattern whose amplitude follows the defocus envelope.
fn synth_frame(k: u16) -> SynthFrame {
    let geom = PlaneGeometry {
        width: PLANT_W,
        height: PLANT_H,
    };
    let w = 2 * PLANT_W;
    let mut rows = vec![0u16; w * 2 * PLANT_H];
    // One stream per frame, seeded by frame index: reproducible, and different
    // frames get genuinely different noise.
    let mut rng = Rng::new(0x4D39_0000 ^ u64::from(k));
    for py in 0..PLANT_H {
        let kfoc = (py as f64 / (PLANT_H - 1) as f64) * f64::from(PLANT_FRAMES - 1);
        let d = (f64::from(k) - kfoc) / 1.25;
        let contrast = (-0.5 * d * d).exp();
        for px in 0..PLANT_W {
            let ramp = px as f64 / (PLANT_W - 1) as f64;
            let base = 60.0 + ramp * 11_940.0;
            let block = if ((px / 3) + (py / 3)) % 2 == 0 {
                1.0
            } else {
                -1.0
            };
            for plane in CfaPlane::ALL {
                // Per-plane offsets so the four planes are not the same number
                // four times; the merge stores them separately.
                let tint = match plane {
                    CfaPlane::R => 0.86,
                    CfaPlane::G1 => 1.00,
                    CfaPlane::B => 0.74,
                    CfaPlane::G2 => 1.00,
                };
                let s = base * tint * (1.0 + 0.25 * contrast * block);
                let sigma = (PLANT_GAIN_DN_PER_E * s + PLANT_READ_DN * PLANT_READ_DN)
                    .max(0.0)
                    .sqrt();
                let v = f64::from(BLACK) + s + sigma * rng.normal();
                let (sx, sy) = geom.sensor_coord(plane, px, py);
                rows[sy * w + sx] = v.clamp(0.0, f64::from(CONTAINER_MAX_DN)).round() as u16;
            }
        }
    }
    SynthFrame { geom, rows }
}

// ---------------------------------------------------------------------------
// blob writing
// ---------------------------------------------------------------------------

/// An append-only little-endian byte blob.
struct Blob(Vec<u8>);

impl Blob {
    fn new() -> Self {
        Blob(Vec::with_capacity(1 << 22))
    }
    fn tag(&mut self, s: &str) {
        self.0.extend_from_slice(&(s.len() as u32).to_le_bytes());
        self.0.extend_from_slice(s.as_bytes());
    }
    fn f32(&mut self, v: f32) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn f64(&mut self, v: f64) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn u16(&mut self, v: u16) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn u32(&mut self, v: u32) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
}

/// FNV-1a 64, printed alongside the file so a run is self-describing even
/// without an external hasher. The **authoritative** identity check is
/// `Get-FileHash -Algorithm SHA256` over the blob itself.
fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in bytes {
        h ^= u64::from(*b);
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
    }
    h
}

// ---------------------------------------------------------------------------
// the identity probe
// ---------------------------------------------------------------------------

/// Every number `noise.rs` and `profile.rs` produce on the default path, at
/// every ISO the profile distinguishes and every DN the container can hold.
fn model_tables(blob: &mut Blob) {
    let levels = Levels {
        black: BLACK,
        white: WHITE,
    };
    blob.tag("model-tables-v1");
    for iso in ISOS {
        let m = profile::noise_model_for("ILCE-7CM2", Some(iso), levels);
        blob.f32(m.iso);
        blob.u32(m.provenance as u32);
        for p in CfaPlane::ALL {
            let pn = m.plane(p);
            blob.f32(pn.gain_dn_per_e);
            blob.f32(pn.read_noise_e);
            blob.f32(pn.levels.black);
            blob.f32(pn.levels.white);
            for s in 0..=SWEEP_MAX {
                blob.f32(m.variance(p, s as f32));
                blob.f32(m.sigma(p, s as f32));
            }
        }
        for s in 0..=SWEEP_MAX {
            blob.f32(m.green_luma_sigma(s as f32));
        }
        // Sub-DN and below-black behaviour, which the integer sweep cannot see.
        for t in [-1000.0f32, -1.0, -0.5, 0.0, 0.25, 0.5, 1e-6, 1e6] {
            blob.f32(m.green_luma_sigma(t));
            blob.f32(m.sigma(CfaPlane::G1, t));
        }
    }
    // The fallback path is part of the default path's contract too.
    let f = profile::fallback(0.0, levels);
    blob.tag("fallback");
    blob.u32(f.provenance as u32);
    for s in 0..=SWEEP_MAX {
        blob.f32(f.green_luma_sigma(s as f32));
    }
}

/// The full two-pass merge, on the deterministic plant, at the shipped gate.
fn synthetic_merge(blob: &mut Blob, noise: &NoiseModel) -> Result<()> {
    let geom = PlaneGeometry {
        width: PLANT_W,
        height: PLANT_H,
    };
    let px = geom.pixels();
    let mut field = FocusField::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut scratch = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];

    let frames: Vec<SynthFrame> = (0..PLANT_FRAMES).map(synth_frame).collect();

    blob.tag("synthetic-merge-v1");
    let mut stats = FocusStats::new(geom);
    for (k, f) in frames.iter().enumerate() {
        green_luma_with_clip(f, BLACK, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, noise);
        // The focus field itself is a direct consumer of green_luma_sigma.
        for v in field.values() {
            blob.f32(*v);
        }
        regularise(field.values(), geom, &mut scratch, &mut reg);
        stats.fold(k as u16, &reg)?;
    }
    for v in stats.best_focus() {
        blob.f32(*v);
    }
    for v in stats.best_index() {
        blob.u16(*v);
    }

    let mut est = Estimator::new(&stats, Gate::new(DEFAULT_GATE));
    est.track_disagreement();
    for (k, f) in frames.iter().enumerate() {
        green_luma_with_clip(f, BLACK, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, noise);
        regularise(field.values(), geom, &mut scratch, &mut reg);
        est.fold_censored(k as u16, f, &reg, CONTAINER_MAX_DN)?;
    }

    for v in est.n_eff() {
        blob.u16(*v);
    }
    for p in CfaPlane::ALL {
        for i in 0..px {
            blob.f32(est.value(p, i));
        }
    }
    for i in 0..px {
        blob.f32(est.predicted_sigma(noise, i, BLACK));
        blob.f64(est.disagreement(noise, i, BLACK).unwrap_or(f64::NAN));
    }
    blob.f64(est.mean_n_eff());
    blob.f64(est.mean_predicted_sigma_gain(noise, BLACK));
    blob.f64(est.disagreement_exposure());
    Ok(())
}

/// The same two-pass merge on a real stack, so the identity claim is made on the
/// product's own data and not only on a plant.
///
/// Written to its own file because a full-plane dump is ~130 MB and the model
/// tables are meant to stay cheap to re-hash.
fn real_merge(blob: &mut Blob, dir: &Path, limit: Option<usize>) -> Result<()> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    if paths.len() < 2 {
        bail!(
            "{} holds {} ARW files; need at least 2",
            dir.display(),
            paths.len()
        );
    }

    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let geom = first.geometry();
    let levels = first.levels;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let black = levels.black;
    drop(first);
    let px = geom.pixels();

    let mut field = FocusField::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut scratch = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];

    blob.tag("real-merge-v1");
    blob.tag(&dir.display().to_string());
    blob.u32(paths.len() as u32);

    let mut stats = FocusStats::new(geom);
    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, &noise);
        regularise(field.values(), geom, &mut scratch, &mut reg);
        stats.fold(k as u16, &reg)?;
    }
    let mut est = Estimator::new(&stats, Gate::new(DEFAULT_GATE));
    est.track_disagreement();
    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, &noise);
        regularise(field.values(), geom, &mut scratch, &mut reg);
        est.fold_censored(k as u16, &frame, &reg, CONTAINER_MAX_DN)?;
    }

    for v in est.n_eff() {
        blob.u16(*v);
    }
    for p in CfaPlane::ALL {
        for i in 0..px {
            blob.f32(est.value(p, i));
        }
    }
    blob.f64(est.mean_n_eff());
    blob.f64(est.mean_predicted_sigma_gain(&noise, black));
    println!(
        "real stack      : {} frames from {}, mean n_eff {:.6}, sigma gain {:.6}",
        paths.len(),
        dir.display(),
        est.mean_n_eff(),
        est.mean_predicted_sigma_gain(&noise, black)
    );
    Ok(())
}

fn cmd_identity(out: &Path, stack: Option<&Path>, limit: Option<usize>) -> Result<()> {
    let levels = Levels {
        black: BLACK,
        white: WHITE,
    };
    let mut blob = Blob::new();
    model_tables(&mut blob);
    let noise = profile::noise_model_for("ILCE-7CM2", Some(100.0), levels);
    synthetic_merge(&mut blob, &noise)?;
    write_blob(out, &blob, "model+synthetic")?;
    if let Some(dir) = stack {
        let mut rblob = Blob::new();
        real_merge(&mut rblob, dir, limit)?;
        let mut real_out = out.to_path_buf();
        let stem = out
            .file_stem()
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_else(|| "identity".to_string());
        real_out.set_file_name(format!("{stem}-real.bin"));
        write_blob(&real_out, &rblob, "real-stack")?;
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// PR-4 / the four residual curves: an independent measurement of g and kappa
//
// M71 measured both in Python via rawpy, with a between-group photon transfer
// for g and a matched-pair split-half covariance for kappa. Re-using its
// constants to score the "both" arm would make that arm true by construction and
// its residual identically zero, which is definitional and not evidence. So the
// numbers scored here come out of the pixels, in Rust, through this crate's own
// decoder, by estimators that fail differently from M71's:
//
//   - g from a **temporal** photon transfer. The variance of a difference of two
//     frames at the same exposure contains no fixed pattern and no illumination
//     structure, both cancelling exactly. That makes the slope immune to the very
//     term being measured, which the between-group estimator is not.
//   - kappa by subtracting that temporal variance from the high-passed spatial
//     variance of the pair mean. What is left is fixed.
//
// And the four curves are scored against `V_single`, the high-passed spatial
// variance of one real frame -- which is precisely the quantity
// `NoiseModel::variance` claims to predict, taken from the sensor rather than
// from anybody's fit.
// ---------------------------------------------------------------------------

/// Box radius for the spatial high pass, in plane pixels. M71 used a 61-wide box
/// (radius 30); the same width is kept so the two are comparable, and
/// `--hp-radius` exists so the choice can be shown not to matter.
const HP_RADIUS: usize = 30;

/// A rectangle of one CFA plane, black-subtracted, in DN.
struct PlaneRoi {
    w: usize,
    h: usize,
    v: Vec<f32>,
}

impl PlaneRoi {
    fn extract(frame: &strehl_raw::Frame, plane: CfaPlane, side: usize) -> PlaneRoi {
        let geom = frame.geometry();
        let (pw, ph) = (geom.width, geom.height);
        let w = side.min(pw);
        let h = side.min(ph);
        let x0 = (pw - w) / 2;
        let y0 = (ph - h) / 2;
        let (dx, dy) = plane.rggb_offset();
        let black = frame.levels.black;
        let mut v = Vec::with_capacity(w * h);
        for py in y0..y0 + h {
            let (top, bot) = frame.quad_rows(py);
            let row = if dy == 0 { top } else { bot };
            for px in x0..x0 + w {
                v.push(row[2 * px + dx] as f32 - black);
            }
        }
        PlaneRoi { w, h, v }
    }

    fn mean(&self) -> f64 {
        self.v.iter().map(|&x| x as f64).sum::<f64>() / self.v.len() as f64
    }

    fn max(&self) -> f32 {
        self.v.iter().copied().fold(f32::MIN, f32::max)
    }
}

/// Mean of an `r`-radius box around every pixel, clamped at the edges.
///
/// Separable running sums, so it is O(pixels) and independent of `r`. The
/// per-pixel divisor is the true clamped count, not the nominal box area, so the
/// border does not manufacture an edge artefact that would then read as extra
/// variance.
fn box_mean(v: &[f32], w: usize, h: usize, r: usize, tmp: &mut [f32], out: &mut [f32]) {
    for y in 0..h {
        let row = &v[y * w..(y + 1) * w];
        let mut acc = 0.0f64;
        for &x in row.iter().take((r + 1).min(w)) {
            acc += x as f64;
        }
        for x in 0..w {
            let lo = x.saturating_sub(r);
            let hi = (x + r).min(w - 1);
            tmp[y * w + x] = (acc / (hi - lo + 1) as f64) as f32;
            if x + r + 1 < w {
                acc += row[x + r + 1] as f64;
            }
            if x >= r {
                acc -= row[x - r] as f64;
            }
        }
    }
    for x in 0..w {
        let mut acc = 0.0f64;
        for y in 0..(r + 1).min(h) {
            acc += tmp[y * w + x] as f64;
        }
        for y in 0..h {
            let lo = y.saturating_sub(r);
            let hi = (y + r).min(h - 1);
            out[y * w + x] = (acc / (hi - lo + 1) as f64) as f32;
            if y + r + 1 < h {
                acc += tmp[(y + r + 1) * w + x] as f64;
            }
            if y >= r {
                acc -= tmp[(y - r) * w + x] as f64;
            }
        }
    }
}

/// Variance of `v` after removing its local box mean.
///
/// White noise loses a known fraction of itself to the box, so the raw number is
/// biased low by `1 - 1/N` for an `N`-pixel box. The correction is applied here
/// and is tiny at radius 30 (N = 3721, so 0.027%), but it is applied to **every**
/// arm identically, so it cannot change a comparison between them.
fn highpass_var(v: &[f32], w: usize, h: usize, r: usize, tmp: &mut [f32], bm: &mut [f32]) -> f64 {
    box_mean(v, w, h, r, tmp, bm);
    let n = v.len();
    let mut s = 0.0f64;
    let mut ss = 0.0f64;
    for i in 0..n {
        let d = (v[i] - bm[i]) as f64;
        s += d;
        ss += d * d;
    }
    let mean = s / n as f64;
    let raw = ss / n as f64 - mean * mean;
    let area = (2 * r + 1) * (2 * r + 1);
    raw / (1.0 - 1.0 / area as f64)
}

/// One matched pair at one exposure, reduced to the three variances that matter.
struct FlatLevel {
    /// Mean black-subtracted level, DN.
    s: f64,
    /// Temporal variance per frame, DN^2. Fixed pattern cancelled by differencing.
    v_temp: f64,
    /// Fixed-pattern variance, DN^2. What is left in the pair mean.
    v_fixed: f64,
    /// High-passed spatial variance of a single real frame, DN^2. This is the
    /// quantity `NoiseModel::variance` claims to predict, and the four residual
    /// curves are scored against it.
    v_single: f64,
    /// Fraction of the ROI at or above the container ceiling in either frame.
    clipped: f64,
    plane: CfaPlane,
}

fn measure_pair(
    a: &strehl_raw::Frame,
    b: &strehl_raw::Frame,
    plane: CfaPlane,
    side: usize,
    r: usize,
) -> FlatLevel {
    let ra = PlaneRoi::extract(a, plane, side);
    let rb = PlaneRoi::extract(b, plane, side);
    let (w, h) = (ra.w, ra.h);
    let n = w * h;
    let mut tmp = vec![0.0f32; n];
    let mut bm = vec![0.0f32; n];

    // A global rescale removes illumination drift between the two exposures
    // without touching per-pixel structure. M71 carried the same factors as
    // A1/A2 and found them within 5% of unity.
    let (ma, mb) = (ra.mean(), rb.mean());
    let k = if mb > 0.0 { ma / mb } else { 1.0 } as f32;

    let ceiling = f32::from(CONTAINER_MAX_DN) - a.levels.black;
    let mut clipped = 0usize;
    let mut diff = vec![0.0f32; n];
    let mut mid = vec![0.0f32; n];
    for i in 0..n {
        let (x, y) = (ra.v[i], rb.v[i] * k);
        if ra.v[i] >= ceiling || rb.v[i] >= ceiling {
            clipped += 1;
        }
        diff[i] = x - y;
        mid[i] = 0.5 * (x + y);
    }

    // Var(a - b) = 2 * V_temp when the two frames are independent draws.
    let v_temp = highpass_var(&diff, w, h, r, &mut tmp, &mut bm) / 2.0;
    // The pair mean averages the temporal part down by two and leaves the fixed
    // part untouched, which is the whole basis of the separation.
    let v_mid = highpass_var(&mid, w, h, r, &mut tmp, &mut bm);
    let v_fixed = v_mid - v_temp / 2.0;
    let v_single = highpass_var(&ra.v, w, h, r, &mut tmp, &mut bm);

    FlatLevel {
        s: 0.5 * (ma + mb),
        v_temp,
        v_fixed,
        v_single,
        clipped: clipped as f64 / n as f64,
        plane,
    }
}

/// Ordinary least squares slope and intercept of `y` on `x`, with the standard
/// error of the slope.
fn ols(x: &[f64], y: &[f64]) -> (f64, f64, f64) {
    let n = x.len() as f64;
    let mx = x.iter().sum::<f64>() / n;
    let my = y.iter().sum::<f64>() / n;
    let sxx: f64 = x.iter().map(|&v| (v - mx) * (v - mx)).sum();
    let sxy: f64 = x.iter().zip(y).map(|(&a, &b)| (a - mx) * (b - my)).sum();
    let slope = sxy / sxx;
    let inter = my - slope * mx;
    let sse: f64 = x
        .iter()
        .zip(y)
        .map(|(&a, &b)| {
            let e = b - (inter + slope * a);
            e * e
        })
        .sum();
    let se = if n > 2.0 {
        (sse / (n - 2.0) / sxx).sqrt()
    } else {
        f64::NAN
    };
    (slope, inter, se)
}

fn cmd_flats(dir: &Path, side: usize, r: usize, limit: Option<usize>) -> Result<()> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    println!("flats: {} ARW under {}", paths.len(), dir.display());

    // Pass 1: mean green level per frame, so the exposure groups can be found
    // without depending on a shutter tag this decoder does not surface.
    let mut census: Vec<(PathBuf, f64, f32)> = Vec::new();
    for p in &paths {
        let f = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        let roi = PlaneRoi::extract(&f, CfaPlane::G1, side);
        census.push((p.clone(), roi.mean(), roi.max()));
    }
    census.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());

    // Group frames whose means agree within 2%. Flats one stop apart differ by
    // 100%, so the clustering is not a close call.
    let mut groups: Vec<Vec<usize>> = Vec::new();
    for i in 0..census.len() {
        match groups.last_mut() {
            Some(g) if census[i].1 <= census[g[0]].1 * 1.02 + 1.0 => g.push(i),
            _ => groups.push(vec![i]),
        }
    }
    println!("flats: {} exposure groups by mean level", groups.len());

    let ceiling = f64::from(CONTAINER_MAX_DN) - BLACK as f64;
    let mut levels: Vec<FlatLevel> = Vec::new();
    for g in &groups {
        if g.len() < 2 {
            continue;
        }
        // Two frames from opposite ends of the group, so a slow illumination
        // drift within the group shows up as a failure rather than hiding.
        let (ia, ib) = (g[0], g[g.len() - 1]);
        if census[ia].2 as f64 >= ceiling * 0.98 {
            println!("  skip level {:.1} DN: saturated", census[ia].1);
            continue;
        }
        let fa = strehl_raw::decode(&census[ia].0)?;
        let fb = strehl_raw::decode(&census[ib].0)?;
        for plane in [CfaPlane::G1, CfaPlane::G2] {
            let l = measure_pair(&fa, &fb, plane, side, r);
            if l.clipped > 0.001 {
                println!(
                    "  skip {:?} at {:.1} DN: {:.3}% clipped",
                    l.plane,
                    l.s,
                    l.clipped * 100.0
                );
                continue;
            }
            levels.push(l);
        }
    }

    if levels.len() < 4 {
        bail!(
            "only {} usable levels; need at least 4 for a photon transfer",
            levels.len()
        );
    }

    // --- g, from the temporal photon transfer ---------------------------------
    let xs: Vec<f64> = levels.iter().map(|l| l.s).collect();
    let ys: Vec<f64> = levels.iter().map(|l| l.v_temp).collect();
    let (g, intercept, g_se) = ols(&xs, &ys);

    // --- kappa, from what the difference could not remove ---------------------
    // Fit V_fixed = (kappa*S)^2 through the origin in S^2, which weights the
    // bright levels where the term is actually measurable.
    let sx4: f64 = levels.iter().map(|l| l.s.powi(4)).sum();
    let sx2y: f64 = levels.iter().map(|l| l.s.powi(2) * l.v_fixed).sum();
    let kappa2 = sx2y / sx4;
    let kappa = if kappa2 > 0.0 {
        kappa2.sqrt()
    } else {
        f64::NAN
    };
    // Per-level kappa, so the spread is visible rather than smoothed away.
    let per_level: Vec<f64> = levels
        .iter()
        .filter(|l| l.s > 500.0 && l.v_fixed > 0.0)
        .map(|l| l.v_fixed.sqrt() / l.s)
        .collect();
    let k_mean = per_level.iter().sum::<f64>() / per_level.len() as f64;
    let k_sd = (per_level.iter().map(|v| (v - k_mean).powi(2)).sum::<f64>()
        / (per_level.len().max(2) - 1) as f64)
        .sqrt();

    println!();
    println!(
        "--- PR-4: independent measurement, {} levels ---",
        levels.len()
    );
    println!(
        "g (temporal PTC slope) = {:.6} +/- {:.6} DN/e-   intercept {:.3} DN^2",
        g, g_se, intercept
    );
    println!(
        "  M71 between-group     = 0.224103   ratio mine/M71 = {:.5} ({:+.2}%)",
        g / 0.224103,
        (g / 0.224103 - 1.0) * 100.0
    );
    println!(
        "  shipped 100/436.8     = 0.228938   ratio mine/shipped = {:.5} ({:+.2}%)",
        g / 0.228938,
        (g / 0.228938 - 1.0) * 100.0
    );
    println!(
        "kappa (S^2 fit)        = {:.6} ({:.4}%)",
        kappa,
        kappa * 100.0
    );
    println!(
        "kappa (per-level mean) = {:.6} +/- {:.6} ({:.4}% +/- {:.4}%), n = {}",
        k_mean,
        k_sd,
        k_mean * 100.0,
        k_sd * 100.0,
        per_level.len()
    );
    println!(
        "  M71 matched-pair      = 0.003096   ratio mine/M71 = {:.4} ({:+.1}%)",
        kappa / 0.003096,
        (kappa / 0.003096 - 1.0) * 100.0
    );
    println!(
        "  read floor from intercept: {:.4} DN",
        intercept.max(0.0).sqrt()
    );

    // --- the four residual curves --------------------------------------------
    // Scored against v_single: the high-passed spatial variance of one real
    // frame, which is what the model claims to predict.
    let lv = Levels {
        black: BLACK,
        white: WHITE,
    };
    let p = profile::by_model("ILCE-7CM2").context("no A7C II profile")?;
    let arms: [(&str, profile::Corrections); 4] = [
        ("shipped", profile::Corrections::SHIPPED),
        ("gain-only", profile::Corrections::GAIN_ONLY),
        ("prnu-only", profile::Corrections::PRNU_ONLY),
        ("both", profile::Corrections::BOTH),
    ];
    println!();
    println!("--- the four residual curves (sigma_model / sigma_measured - 1) ---");
    println!(
        "{:>9} {:>7} {:>10} {:>10} {:>10} {:>10} {:>10}",
        "S_DN", "plane", "sigma_meas", "shipped", "gain-only", "prnu-only", "both"
    );
    let mut rows: Vec<(f64, [f64; 4])> = Vec::new();
    for l in &levels {
        let meas = l.v_single.max(0.0).sqrt();
        let mut r4 = [0.0f64; 4];
        for (j, (_, c)) in arms.iter().enumerate() {
            let m = p.noise_model_with(100.0, lv, *c);
            let pred = m.sigma_with_fixed_pattern(l.plane, l.s as f32) as f64;
            r4[j] = pred / meas - 1.0;
        }
        println!(
            "{:>9.1} {:>7} {:>10.4} {:>+9.2}% {:>+9.2}% {:>+9.2}% {:>+9.2}%",
            l.s,
            format!("{:?}", l.plane),
            meas,
            r4[0] * 100.0,
            r4[1] * 100.0,
            r4[2] * 100.0,
            r4[3] * 100.0
        );
        rows.push((l.s, r4));
    }

    println!();
    println!("--- arm scores over the measured range ---");
    println!(
        "{:>10} {:>10} {:>10} {:>10}",
        "arm", "rms", "worst", "median"
    );
    for (j, (name, _)) in arms.iter().enumerate() {
        let mut v: Vec<f64> = rows.iter().map(|(_, r)| r[j]).collect();
        let rms = (v.iter().map(|x| x * x).sum::<f64>() / v.len() as f64).sqrt();
        let worst = v.iter().cloned().fold(0.0f64, |a, b| a.max(b.abs()));
        v.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let med = v[v.len() / 2];
        println!(
            "{:>10} {:>+9.2}% {:>+9.2}% {:>+9.2}%",
            name,
            rms * 100.0,
            worst * 100.0,
            med * 100.0
        );
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Deliverable B: the blast radius
//
// The noise model reaches the merge through exactly two doors, and they are not
// the same door:
//
//   1. `FocusField::compute` divides the Tenengrad response by the model's
//      green-luma sigma. That normalisation decides the focus field, which the
//      regulariser smooths, which `FocusStats` reduces to a winner, which `Gate`
//      turns into an admitted set. **This is a selection path**: it changes which
//      frames contribute, and therefore changes the pixels.
//   2. `Estimator::predicted_sigma` reports the confidence of the merged value.
//      **This is a reporting path**: it changes what the merge says about itself
//      and not one output pixel.
//
// Both are measured here, separately, because a correction that moves only the
// second is cheap and a correction that moves the first is not.
//
// All arms are folded inside one decode pass. Decoding dominates the cost at
// ~0.91 s/frame and the focus computation does not, so four arms cost barely
// more than one and no arm can differ because it saw a different decode.
// ---------------------------------------------------------------------------

/// Octave bins of merged green luma, DN above black. The error is quadratic in
/// signal, so a linear bin would put nearly every pixel in one cell and a
/// whole-image mean would report the dark end of the frame.
const OCTAVES: [f32; 8] = [0.0, 64.0, 128.0, 256.0, 512.0, 1024.0, 2048.0, 4096.0];

fn octave_of(luma: f32) -> usize {
    let mut b = 0;
    for (i, edge) in OCTAVES.iter().enumerate() {
        if luma >= *edge {
            b = i;
        }
    }
    b
}

struct ArmRun {
    name: &'static str,
    corrections: profile::Corrections,
    noise: NoiseModel,
    field: FocusField,
    stats: FocusStats,
    est: Option<Estimator>,
}

/// Everything one arm is compared on, per pixel, after the merge.
struct ArmResult {
    name: &'static str,
    n_eff: Vec<u16>,
    best: Vec<u16>,
    green: Vec<f32>,
    sigma: Vec<f32>,
    mean_n_eff: f64,
    mean_sigma_gain: f64,
}

#[allow(clippy::too_many_arguments)]
fn cmd_blast(dir: &Path, limit: Option<usize>, gate_threshold: f32, tiles: usize) -> Result<()> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    if paths.len() < 2 {
        bail!("{} holds {} ARW files", dir.display(), paths.len());
    }

    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let geom = first.geometry();
    let levels = first.levels;
    let black = levels.black;
    let camera = first.camera.clone();
    let iso = first.iso;
    drop(first);
    let px = geom.pixels();

    println!(
        "=== blast: {} | {} frames | {} | ISO {} | gate {} ===",
        dir.display(),
        paths.len(),
        camera,
        iso.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
        gate_threshold
    );

    let specs: [(&str, profile::Corrections); 4] = [
        ("shipped", profile::Corrections::SHIPPED),
        ("gain-only", profile::Corrections::GAIN_ONLY),
        ("prnu-only", profile::Corrections::PRNU_ONLY),
        ("both", profile::Corrections::BOTH),
    ];
    let mut arms: Vec<ArmRun> = specs
        .iter()
        .map(|(name, c)| ArmRun {
            name,
            corrections: *c,
            noise: profile::noise_model_for_with(&camera, iso, levels, *c),
            field: FocusField::new(geom),
            stats: FocusStats::new(geom),
            est: None,
        })
        .collect();

    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut scratch = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];

    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        for a in arms.iter_mut() {
            a.field.compute(&luma, &a.noise);
            regularise(a.field.values(), geom, &mut scratch, &mut reg);
            a.stats.fold(k as u16, &reg)?;
        }
    }
    for a in arms.iter_mut() {
        let mut e = Estimator::new(&a.stats, Gate::new(gate_threshold));
        e.track_disagreement();
        a.est = Some(e);
    }
    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        for a in arms.iter_mut() {
            a.field.compute(&luma, &a.noise);
            regularise(a.field.values(), geom, &mut scratch, &mut reg);
            a.est.as_mut().expect("estimator built").fold_censored(
                k as u16,
                &frame,
                &reg,
                CONTAINER_MAX_DN,
            )?;
        }
    }

    let mut results: Vec<ArmResult> = Vec::new();
    for a in &arms {
        let e = a.est.as_ref().expect("estimator built");
        let mut green = vec![0.0f32; px];
        let mut sigma = vec![0.0f32; px];
        for i in 0..px {
            green[i] = e.green_mean(i) - black;
            // The corrected arms report their confidence through the
            // fixed-pattern entry point; the shipped arm cannot, because it has
            // no pattern attached. That asymmetry is the correction.
            sigma[i] = predicted_sigma_for(e, &a.noise, i, black, a.corrections, RHO_WARP_BOUND);
        }
        results.push(ArmResult {
            name: a.name,
            n_eff: e.n_eff().to_vec(),
            best: e.best_index().to_vec(),
            green,
            sigma,
            mean_n_eff: e.mean_n_eff(),
            mean_sigma_gain: e.mean_predicted_sigma_gain(&a.noise, black),
        });
    }

    report_blast(&results, geom, tiles);

    // --- the rho_warp sweep ---------------------------------------------------
    // Everything above is quoted at rho_warp = 1, the conservative bound. rho is
    // unmeasured (M71 §11 names it as the blocking measurement), and it is the
    // single largest lever on the answer, so the whole interval is shown rather
    // than one end of it.
    //
    // Fact 230 measures adjacent-frame warp at 0.07-0.22 green px, which is
    // sub-pixel, and the merge admits precisely the adjacent frames. That argues
    // for the top of the interval, but arguing is not measuring.
    let base_arm = &arms[0];
    let both_arm = arms.last().expect("four arms");
    let eb = base_arm.est.as_ref().expect("estimator");
    let ec = both_arm.est.as_ref().expect("estimator");
    println!();
    println!("--- rho_warp sweep on the 'both' arm's reported confidence ---");
    println!(
        "{:>10} {:>14} {:>14} {:>14} {:>14}",
        "rho_warp", "mean d sigma", "median", "p99", "max"
    );
    let mut sweep: Vec<f32> = vec![0.0, 0.25, 0.5, 0.75, 0.9, 1.0];
    sweep.extend(RHO_SWEEP.lock().expect("rho sweep").iter().copied());
    sweep.sort_by(|a, b| a.partial_cmp(b).expect("finite rho"));
    for rho in sweep {
        let mut rel: Vec<f64> = Vec::with_capacity(px);
        for i in 0..px {
            let b = eb.predicted_sigma(&base_arm.noise, i, black);
            if b <= 0.0 {
                continue;
            }
            let c = predicted_sigma_for(ec, &both_arm.noise, i, black, both_arm.corrections, rho);
            rel.push((c / b) as f64 - 1.0);
        }
        let mean = rel.iter().sum::<f64>() / rel.len() as f64;
        rel.sort_by(|a, b| a.partial_cmp(b).unwrap());
        println!(
            "{:>10.2} {:>+13.2}% {:>+13.2}% {:>+13.2}% {:>+13.2}%",
            rho,
            mean * 100.0,
            rel[rel.len() / 2] * 100.0,
            rel[(rel.len() as f64 * 0.99) as usize] * 100.0,
            rel[rel.len() - 1] * 100.0
        );
    }
    Ok(())
}

/// `Estimator::predicted_sigma` with the fixed-pattern term folded in when the
/// arm carries one.
///
/// `predicted_sigma` is `sigma(green_mean) * sqrt(gain)` where `gain` is the
/// selection penalty. The pattern does not average down over the admitted
/// frames, so it is added at full strength to the single-frame variance rather
/// than being divided by anything, which is the `rho_warp = 1` limit and the
/// conservative one. `rho_warp` is unmeasured (M71 §11), so the bound is quoted
/// rather than a point estimate, and the `rho_warp = 0` limit is what
/// `predicted_sigma` already returns.
fn predicted_sigma_for(
    e: &Estimator,
    noise: &NoiseModel,
    i: usize,
    black: f32,
    c: profile::Corrections,
    rho_warp: f32,
) -> f32 {
    let base = e.predicted_sigma(noise, i, black);
    if !c.prnu {
        return base;
    }
    let luma = (e.green_mean(i) - black).max(0.0);
    let plain = noise.green_luma_sigma(luma);
    let with = noise.green_luma_sigma_with_fixed_pattern(luma);
    let excess = (with * with - plain * plain).max(0.0);
    if plain <= 0.0 {
        return base;
    }
    // `base` already carries the selection penalty, so recover it rather than
    // re-deriving n_eff: gain = (base / single-frame sigma)^2.
    let gain = (base / plain).powi(2);
    // The decorrelated share averages down with everything else; the correlated
    // share does not average at all. That second term is the whole distinction.
    (base * base + (1.0 - rho_warp) * excess * gain + rho_warp * excess).sqrt()
}

fn report_blast(results: &[ArmResult], geom: strehl_core::plane::PlaneGeometry, tiles: usize) {
    let px = results[0].n_eff.len();
    let base = &results[0];

    println!();
    println!("--- whole-image ---");
    println!(
        "{:>10} {:>12} {:>12} {:>14} {:>14}",
        "arm", "mean n_eff", "d n_eff", "sigma gain", "mean sigma"
    );
    for r in results {
        let ms: f64 = r.sigma.iter().map(|&v| v as f64).sum::<f64>() / px as f64;
        println!(
            "{:>10} {:>12.6} {:>+12.6} {:>14.6} {:>14.4}",
            r.name,
            r.mean_n_eff,
            r.mean_n_eff - base.mean_n_eff,
            r.mean_sigma_gain,
            ms
        );
    }

    println!();
    println!("--- selection: does the correction change which frames are used? ---");
    println!(
        "{:>10} {:>14} {:>14} {:>14} {:>14}",
        "arm", "n_eff moved", "winner moved", "max |d n_eff|", "mean d n_eff"
    );
    for r in results.iter().skip(1) {
        let mut moved = 0usize;
        let mut winner = 0usize;
        let mut maxd = 0i32;
        let mut sumd = 0i64;
        for i in 0..px {
            let d = r.n_eff[i] as i32 - base.n_eff[i] as i32;
            if d != 0 {
                moved += 1;
            }
            if r.best[i] != base.best[i] {
                winner += 1;
            }
            maxd = maxd.max(d.abs());
            sumd += d as i64;
        }
        println!(
            "{:>10} {:>13.4}% {:>13.4}% {:>14} {:>+14.6}",
            r.name,
            moved as f64 * 100.0 / px as f64,
            winner as f64 * 100.0 / px as f64,
            maxd,
            sumd as f64 / px as f64
        );
    }

    println!();
    println!("--- reporting: how much does the stated confidence move? ---");
    println!(
        "{:>10} {:>14} {:>14} {:>14}",
        "arm", "mean d sigma", "median d sigma", "p99 d sigma"
    );
    for r in results.iter().skip(1) {
        let mut rel: Vec<f64> = (0..px)
            .filter(|&i| base.sigma[i] > 0.0)
            .map(|i| (r.sigma[i] / base.sigma[i]) as f64 - 1.0)
            .collect();
        let mean = rel.iter().sum::<f64>() / rel.len() as f64;
        rel.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let med = rel[rel.len() / 2];
        let p99 = rel[(rel.len() as f64 * 0.99) as usize];
        println!(
            "{:>10} {:>+13.3}% {:>+13.3}% {:>+13.3}%",
            r.name,
            mean * 100.0,
            med * 100.0,
            p99 * 100.0
        );
    }

    // --- signal-resolved ------------------------------------------------------
    println!();
    println!("--- signal-resolved, by octave of merged green luma (DN above black) ---");
    let mut counts = [0usize; OCTAVES.len()];
    for i in 0..px {
        counts[octave_of(base.green[i])] += 1;
    }
    print!("{:>10} {:>12}", "octave", "pixels");
    for r in results.iter().skip(1) {
        print!(" {:>11} {:>11}", format!("{} ds", r.name), "n_eff mv");
    }
    println!();
    for (b, edge) in OCTAVES.iter().enumerate() {
        if counts[b] == 0 {
            continue;
        }
        let hi = OCTAVES.get(b + 1).copied().unwrap_or(f32::INFINITY);
        print!(
            "{:>10} {:>11.2}%",
            format!("{:.0}-{:.0}", edge, hi.min(16383.0)),
            counts[b] as f64 * 100.0 / px as f64
        );
        for r in results.iter().skip(1) {
            let mut s = 0.0f64;
            let mut n = 0usize;
            let mut moved = 0usize;
            for i in 0..px {
                if octave_of(base.green[i]) == b {
                    if base.sigma[i] > 0.0 {
                        s += (r.sigma[i] / base.sigma[i]) as f64 - 1.0;
                        n += 1;
                    }
                    if r.n_eff[i] != base.n_eff[i] {
                        moved += 1;
                    }
                }
            }
            print!(
                " {:>+10.2}% {:>10.3}%",
                s / n.max(1) as f64 * 100.0,
                moved as f64 * 100.0 / counts[b] as f64
            );
        }
        println!();
    }

    // --- spatially resolved ---------------------------------------------------
    let last = results.last().expect("at least one arm");
    println!();
    println!(
        "--- spatially resolved: '{}' vs shipped, {}x{} tiles ---",
        last.name, tiles, tiles
    );
    let (w, h) = (geom.width, geom.height);
    let (tw, th) = (w.div_ceil(tiles), h.div_ceil(tiles));
    let mut tile: Vec<(f64, f64, usize, usize)> = vec![(0.0, 0.0, 0, 0); tiles * tiles];
    for y in 0..h {
        for x in 0..w {
            let i = y * w + x;
            let t = (y / th).min(tiles - 1) * tiles + (x / tw).min(tiles - 1);
            let e = &mut tile[t];
            e.0 += base.green[i] as f64;
            if base.sigma[i] > 0.0 {
                e.1 += (last.sigma[i] / base.sigma[i]) as f64 - 1.0;
            }
            if last.n_eff[i] != base.n_eff[i] {
                e.3 += 1;
            }
            e.2 += 1;
        }
    }
    println!("  mean merged luma (DN) per tile:");
    for ty in 0..tiles {
        let row: Vec<String> = (0..tiles)
            .map(|tx| {
                format!(
                    "{:>7.0}",
                    tile[ty * tiles + tx].0 / tile[ty * tiles + tx].2 as f64
                )
            })
            .collect();
        println!("    {}", row.join(""));
    }
    println!("  mean sigma change (%) per tile:");
    for ty in 0..tiles {
        let row: Vec<String> = (0..tiles)
            .map(|tx| {
                format!(
                    "{:>+7.2}",
                    tile[ty * tiles + tx].1 / tile[ty * tiles + tx].2 as f64 * 100.0
                )
            })
            .collect();
        println!("    {}", row.join(""));
    }

    // Correlation of the sigma move with tile brightness: the claim that the
    // correction "matters in the bright regions" is exactly this number.
    let n = tile.len() as f64;
    let xs: Vec<f64> = tile.iter().map(|t| t.0 / t.2 as f64).collect();
    let ys: Vec<f64> = tile.iter().map(|t| t.1 / t.2 as f64).collect();
    let mx = xs.iter().sum::<f64>() / n;
    let my = ys.iter().sum::<f64>() / n;
    let sxy: f64 = xs.iter().zip(&ys).map(|(a, b)| (a - mx) * (b - my)).sum();
    let sxx: f64 = xs.iter().map(|a| (a - mx) * (a - mx)).sum();
    let syy: f64 = ys.iter().map(|b| (b - my) * (b - my)).sum();
    println!(
        "  Pearson r(tile mean luma, tile sigma change) = {:+.4} over {} tiles",
        sxy / (sxx * syy).sqrt(),
        tile.len()
    );
    let (bright, dark) = (
        xs.iter().cloned().fold(f64::MIN, f64::max),
        xs.iter().cloned().fold(f64::MAX, f64::min),
    );
    let ib = xs.iter().position(|&v| v == bright).unwrap();
    let id = xs.iter().position(|&v| v == dark).unwrap();
    println!(
        "  brightest tile {:.0} DN -> {:+.2}% sigma;  darkest tile {:.0} DN -> {:+.2}% sigma",
        bright,
        ys[ib] * 100.0,
        dark,
        ys[id] * 100.0
    );
}

/// The correlation between two admitted frames' fixed pattern at the same output
/// The `rho_warp` values the sweep reports.
///
/// Round 2 measured `rho_warp` (see `M90-prnu-noise-model.md` §R2), so the
/// sweep is no longer a pure bound: `--rho <v>` adds a measured point to it.
/// The default list is retained unchanged so every round 1 number in the
/// corpus can still be reproduced from this binary.
static RHO_SWEEP: std::sync::Mutex<Vec<f32>> = std::sync::Mutex::new(Vec::new());

/// pixel, after warping. **Unmeasured** (M71 §11). 1.0 is the conservative end:
/// the pattern does not average down at all. Every headline here is quoted at
/// this value and the `--rho` sweep shows the whole interval.
const RHO_WARP_BOUND: f32 = 1.0;

// ---------------------------------------------------------------------------
// The instrument's own placebo and planted defect
//
// `measure_pair` separates a fixed pattern from temporal noise by subtracting
// half the difference variance from the pair-mean variance. That subtraction is
// where a broken instrument would manufacture kappa out of nothing, so it is
// checked against synthetic pairs whose kappa is known because it was planted.
//
// The plant supplies its **own** constants and never reads the profile or M71
// (AGENTS rule 34): an instrument handed the number it is meant to recover
// cannot demonstrate that it would notice the number being wrong.
// ---------------------------------------------------------------------------

const SELFTEST_GAIN: f64 = 0.2137;
const SELFTEST_READ_DN: f64 = 1.0413;

/// A synthetic flat pair at one level with a planted kappa.
fn synth_flat_pair(
    w: usize,
    h: usize,
    s: f64,
    kappa: f64,
    pattern_seed: u64,
    seed: u64,
) -> (Vec<f32>, Vec<f32>) {
    // The pattern is drawn once from a fixed seed and is the *same* in both
    // frames -- that is what makes it fixed.
    let mut pr = Rng(pattern_seed);
    let pattern: Vec<f64> = (0..w * h).map(|_| pr.normal()).collect();
    let mut rng = Rng(seed);
    let mut a = vec![0.0f32; w * h];
    let mut b = vec![0.0f32; w * h];
    let sd_temporal = (SELFTEST_GAIN * s + SELFTEST_READ_DN * SELFTEST_READ_DN).sqrt();
    for i in 0..w * h {
        let fixed = s * (1.0 + kappa * pattern[i]);
        a[i] = (fixed + sd_temporal * rng.normal()) as f32;
        b[i] = (fixed + sd_temporal * rng.normal()) as f32;
    }
    (a, b)
}

/// Run the real estimator over a synthetic pair.
fn measure_synth(a: &[f32], b: &[f32], w: usize, h: usize, r: usize) -> (f64, f64, f64) {
    let n = w * h;
    let mut tmp = vec![0.0f32; n];
    let mut bm = vec![0.0f32; n];
    let mut diff = vec![0.0f32; n];
    let mut mid = vec![0.0f32; n];
    for i in 0..n {
        diff[i] = a[i] - b[i];
        mid[i] = 0.5 * (a[i] + b[i]);
    }
    let v_temp = highpass_var(&diff, w, h, r, &mut tmp, &mut bm) / 2.0;
    let v_mid = highpass_var(&mid, w, h, r, &mut tmp, &mut bm);
    let v_fixed = v_mid - v_temp / 2.0;
    let mean = a.iter().map(|&x| x as f64).sum::<f64>() / n as f64;
    (mean, v_temp, v_fixed)
}

fn cmd_selftest(r: usize) -> Result<()> {
    const W: usize = 512;
    const H: usize = 512;
    let sweep = [200.0f64, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 12000.0];

    println!("=== flats instrument self-test ===");
    println!("plant: g = {SELFTEST_GAIN}, read = {SELFTEST_READ_DN} DN, {W}x{H}, hp radius {r}");
    println!("(constants belong to the plant, not to the profile or to M71)");

    // Three arms. The first must show no effect: it is the placebo.
    let arms: [(&str, f64); 3] = [
        ("placebo kappa=0", 0.0),
        ("kappa=0.31%", 0.0031),
        ("planted 10x", 0.031),
    ];
    let mut verdicts: Vec<(String, bool, String)> = Vec::new();
    for (name, planted) in arms {
        let mut xs = Vec::new();
        let mut ys = Vec::new();
        let mut ks = Vec::new();
        for (j, s) in sweep.iter().enumerate() {
            let (a, b) = synth_flat_pair(W, H, *s, planted, 0xA57E_1234, 0xBEEF_0000 + j as u64);
            let (mean, v_temp, v_fixed) = measure_synth(&a, &b, W, H, r);
            xs.push(mean);
            ys.push(v_temp);
            if *s >= 500.0 {
                ks.push(if v_fixed > 0.0 {
                    v_fixed.sqrt() / mean
                } else {
                    0.0
                });
            }
        }
        let (g, inter, _) = ols(&xs, &ys);
        let k = ks.iter().sum::<f64>() / ks.len() as f64;
        println!();
        println!("  {name}");
        println!(
            "    g recovered     {:.5}  (planted {:.5}, {:+.2}%)",
            g,
            SELFTEST_GAIN,
            (g / SELFTEST_GAIN - 1.0) * 100.0
        );
        println!(
            "    read recovered  {:.4} DN (planted {:.4})",
            inter.max(0.0).sqrt(),
            SELFTEST_READ_DN
        );
        println!(
            "    kappa recovered {:.5} ({:.4}%)  planted {:.5} ({:.4}%)",
            k,
            k * 100.0,
            planted,
            planted * 100.0
        );

        let g_ok = (g / SELFTEST_GAIN - 1.0).abs() < 0.01;
        let k_ok = if planted == 0.0 {
            k < 0.0004
        } else {
            (k / planted - 1.0).abs() < 0.10
        };
        println!(
            "    g within 1%: {}   kappa bar: {}",
            if g_ok { "PASS" } else { "FAIL" },
            if k_ok { "PASS" } else { "FAIL" }
        );
        verdicts.push((
            name.to_string(),
            g_ok && k_ok,
            format!("g {g:.5}, kappa {k:.5}"),
        ));
    }

    println!();
    println!("--- self-test verdict ---");
    let mut all = true;
    for (n, ok, d) in &verdicts {
        println!("  {:<18} {}   {}", n, if *ok { "PASS" } else { "FAIL" }, d);
        all &= ok;
    }
    if !all {
        bail!("the flats instrument failed its own self-test; every kappa it reports is void");
    }
    println!("  instrument is sound on synthetic data with a known answer.");
    Ok(())
}

fn write_blob(out: &Path, blob: &Blob, label: &str) -> Result<()> {
    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let mut fh =
        std::fs::File::create(out).with_context(|| format!("writing {}", out.display()))?;
    fh.write_all(&blob.0)?;
    fh.flush()?;
    println!(
        "{label:<16}: {} ({} bytes) fnv1a64 {:016x}",
        out.display(),
        blob.0.len(),
        fnv1a64(&blob.0)
    );
    Ok(())
}

// ---------------------------------------------------------------------------

fn usage() -> ! {
    eprintln!(
        "usage:\n  \
         m90-prnu identity [--out PATH] [--stack DIR] [--limit N]\n  \
         m90-prnu flats --dir DIR [--side N] [--hp-radius N] [--limit N]\n  \
         m90-prnu blast --dir DIR [--limit N] [--gate F] [--tiles N]\n  \
         m90-prnu selftest [--hp-radius N]"
    );
    std::process::exit(2)
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let cmd = args.next().unwrap_or_default();
    let mut out = PathBuf::from("experiments/M90-prnu/out/cache/identity.bin");
    let mut stack: Option<PathBuf> = None;
    let mut dir: Option<PathBuf> = None;
    let mut limit: Option<usize> = None;
    let mut side: usize = 1536;
    let mut hp_radius: usize = HP_RADIUS;
    let mut gate_threshold: f32 = DEFAULT_GATE;
    let mut tiles: usize = 6;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--out" => out = PathBuf::from(args.next().context("--out needs a value")?),
            "--stack" => stack = Some(PathBuf::from(args.next().context("--stack needs a value")?)),
            "--dir" => dir = Some(PathBuf::from(args.next().context("--dir needs a value")?)),
            "--side" => side = args.next().context("--side")?.parse().context("--side")?,
            "--gate" => {
                gate_threshold = args.next().context("--gate")?.parse().context("--gate")?
            }
            "--rho" => {
                let v: f32 = args.next().context("--rho")?.parse().context("--rho")?;
                RHO_SWEEP.lock().expect("rho sweep").push(v);
            }
            "--tiles" => tiles = args.next().context("--tiles")?.parse().context("--tiles")?,
            "--hp-radius" => {
                hp_radius = args
                    .next()
                    .context("--hp-radius")?
                    .parse()
                    .context("--hp-radius")?
            }
            "--limit" => {
                limit = Some(
                    args.next()
                        .context("--limit needs a value")?
                        .parse()
                        .context("--limit value")?,
                )
            }
            _ => usage(),
        }
    }
    match cmd.as_str() {
        "identity" => cmd_identity(&out, stack.as_deref(), limit),
        "flats" => cmd_flats(&dir.context("flats needs --dir")?, side, hp_radius, limit),
        "blast" => cmd_blast(
            &dir.context("blast needs --dir")?,
            limit,
            gate_threshold,
            tiles,
        ),
        "selftest" => cmd_selftest(hp_radius),
        _ => usage(),
    }
}
