//! M94 — how decisively does the focus election win?
//!
//! Not a product path. This is the instrument for
//! `docs/research/M94-election-margin.md`, pre-registered at
//! `experiments/M94-election-margin/PREREGISTRATION.md`.
//!
//! It is a **second implementation of the election**, written against the public
//! `strehl-core` API without editing `merge.rs` — the file is contended, and
//! fact 1205 established that an external reimplementation is admissible as
//! evidence when it is bit-exact. `F1`/`F2` below are what buy that admissibility.
//!
//! The corpus already knows *how many* frames are competitive with the winner
//! (`Estimator::n_eff`, M85's 1.000 -> 60.860 ladder). It does not know **where
//! they sit in frame index**. `n_eff = 61` is benign if they are 61 contiguous
//! neighbours and pathological if they are scattered across the bracket. This
//! measures that.
//!
//! ```text
//! cargo run --release -p strehl-cli --example m94-election-margin -- <DIR> [flags]
//! cargo run --release -p strehl-cli --example m94-election-margin -- <DIR> --plant 1.0
//! ```
//!
//! **Reads only.** It never writes to a stack directory. Renders go where
//! `--out` says and nowhere else.

use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::FocusField;
use strehl_core::merge::{Estimator, FOCUS_NOISE_SD, FocusStats, Gate, regularise};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;
use tiff::encoder::{TiffEncoder, colortype};

/// Gate thresholds the confusion radius is reported over, in the same units
/// `Gate::new` takes. `4.0` is `DEFAULT_GATE`; the ladder brackets it by a
/// factor of 8 either side so the headline can be read as a sweep rather than as
/// a number resting on `FOCUS_NOISE_SD` (pre-registration §1.1(b)).
const TOL_C: [f32; 5] = [0.5, 1.0, 2.0, 4.0, 8.0];

/// Index of the shipped gate inside [`TOL_C`].
const SHIPPED: usize = 3;

/// Frame-index distances the margin is reported at. `d = 0` is the trivial
/// placebo (`N4`): the winner against itself, which must return exactly zero.
const DIST: [u16; 7] = [0, 1, 2, 4, 8, 16, 32];

/// Index of `d = 8` inside [`DIST`], the distance bar `B3` is written against.
const D8: usize = 4;

/// M2 §3.1's speckle threshold, kept exactly so the number is comparable with
/// its 34.381% on the retired ring-difference operator.
const SPECKLE_ABS: i32 = 2;

/// Radius of the window the **independent** detail axis is measured over
/// (pre-registration §4.3). It is a plain local standard deviation of one
/// frame's luma — not the focus measure, and it never sees the argmax.
const DETAIL_RADIUS: usize = 16;

/// Quantiles printed for every distribution, so the tail is visible.
const QUANTILES: [f64; 7] = [0.01, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99];

/// Mean black-subtracted green luma of the synthetic plant base, in DN.
/// Chosen to sit in the middle of the A7C II's well away from both the read
/// floor and clipping, so the noise model returns an ordinary photon sigma.
const PLANT_MEAN_DN: f32 = 2000.0;

/// Peak-to-sigma contrast of the synthetic plant base, in DN. Large enough that
/// the in-focus response is far above the noise -- the control is supposed to be
/// easy, since its job is to show the instrument reporting DECISIVE at all.
const PLANT_AMP_DN: f32 = 700.0;

/// Deterministic standard normals: SplitMix64 feeding Box-Muller.
///
/// The generator choice is load-bearing and `merge.rs`'s own test module records
/// why: a plain LCG made `FOCUS_NOISE_SD` vary by **1.30x across seeds**, because
/// consecutive LCG outputs lie on lattice planes and filling a raster grid with
/// them lays that lattice out spatially, where the box windows alias against it.
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
    fn normal(&mut self) -> f32 {
        let (u1, u2) = (self.uniform(), self.uniform());
        ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
    }
    /// Uniform integer in `[0, n)`.
    fn below(&mut self, n: u64) -> u64 {
        self.next_u64() % n
    }
}

/// The shipped tie-break, restated here so the mirror can be sabotaged without
/// touching `merge.rs`.
///
/// `FocusStats::beats` is `focus > cur_focus || (focus == cur_focus && index <
/// cur_index)`. `F3` inverts the second clause and requires `F1` to fail.
#[inline]
fn beats(focus: f32, index: u16, cur_focus: f32, cur_index: u16, inverted: bool) -> bool {
    if inverted {
        focus > cur_focus || (focus == cur_focus && index > cur_index)
    } else {
        focus > cur_focus || (focus == cur_focus && index < cur_index)
    }
}

/// Separable box mean of radius `r`, clamped at the plane edges.
///
/// Used only by the plant's blur ladder and by the independent detail axis. The
/// merge's own regulariser is `strehl_core::merge::regularise` and is not
/// reimplemented here.
fn box_mean(src: &[f32], geom: PlaneGeometry, r: usize, scratch: &mut [f32], dst: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        let out = &mut scratch[y * w..(y + 1) * w];
        let mut acc = 0.0f64;
        for v in row.iter().take(r.min(w - 1) + 1) {
            acc += f64::from(*v);
        }
        let mut lo = 0usize;
        let mut hi = r.min(w - 1);
        for (x, o) in out.iter_mut().enumerate() {
            *o = (acc / (hi - lo + 1) as f64) as f32;
            // advance the window to be centred on x + 1
            let want_lo = (x + 1).saturating_sub(r);
            let want_hi = (x + 1 + r).min(w - 1);
            while lo < want_lo {
                acc -= f64::from(row[lo]);
                lo += 1;
            }
            while hi < want_hi {
                hi += 1;
                acc += f64::from(row[hi]);
            }
        }
    }
    for x in 0..w {
        let mut acc = 0.0f64;
        for y in 0..=r.min(h - 1) {
            acc += f64::from(scratch[y * w + x]);
        }
        let mut lo = 0usize;
        let mut hi = r.min(h - 1);
        for y in 0..h {
            dst[y * w + x] = (acc / (hi - lo + 1) as f64) as f32;
            let want_lo = (y + 1).saturating_sub(r);
            let want_hi = (y + 1 + r).min(h - 1);
            while lo < want_lo {
                acc -= f64::from(scratch[lo * w + x]);
                lo += 1;
            }
            while hi < want_hi {
                hi += 1;
                acc += f64::from(scratch[hi * w + x]);
            }
        }
    }
}

fn quantile(sorted: &[f32], q: f64) -> f32 {
    if sorted.is_empty() {
        return f32::NAN;
    }
    sorted[(((sorted.len() - 1) as f64) * q).round() as usize]
}

fn quantile_u16(sorted: &[u16], q: f64) -> u16 {
    if sorted.is_empty() {
        return 0;
    }
    sorted[(((sorted.len() - 1) as f64) * q).round() as usize]
}

/// Turbo-like 8-anchor colour map. Only used for renders; no number depends on it.
fn turbo(t: f32) -> [u8; 3] {
    const A: [[f32; 3]; 8] = [
        [0.19, 0.07, 0.23],
        [0.28, 0.35, 0.86],
        [0.10, 0.71, 0.92],
        [0.15, 0.92, 0.62],
        [0.62, 0.99, 0.23],
        [0.96, 0.83, 0.20],
        [0.98, 0.47, 0.13],
        [0.73, 0.10, 0.03],
    ];
    let t = t.clamp(0.0, 1.0) * 7.0;
    let i = (t.floor() as usize).min(6);
    let f = t - i as f32;
    let mut o = [0u8; 3];
    for c in 0..3 {
        let v = A[i][c] * (1.0 - f) + A[i + 1][c] * f;
        o[c] = (v.clamp(0.0, 1.0) * 255.0).round() as u8;
    }
    o
}

fn write_rgb8(path: &Path, w: usize, h: usize, rgb: &[u8]) -> Result<()> {
    if let Some(p) = path.parent() {
        std::fs::create_dir_all(p).with_context(|| format!("creating {}", p.display()))?;
    }
    let f = File::create(path).with_context(|| format!("creating {}", path.display()))?;
    TiffEncoder::new(BufWriter::new(f))
        .with_context(|| format!("tiff header for {}", path.display()))?
        .write_image::<colortype::RGB8>(w as u32, h as u32, rgb)
        .with_context(|| format!("writing {}", path.display()))?;
    Ok(())
}

/// Render a scalar field through the colour map, plus a 1:1 centre crop, because
/// salt-and-pepper structure is invisible once the plane is scaled to fit.
fn render(
    dir: &Path,
    stem: &str,
    geom: PlaneGeometry,
    vals: &[f32],
    lo: f32,
    hi: f32,
    crop: usize,
) -> Result<()> {
    let (w, h) = (geom.width, geom.height);
    let span = if (hi - lo).abs() < 1e-12 {
        1.0
    } else {
        hi - lo
    };
    let mut rgb = vec![0u8; w * h * 3];
    for (i, &v) in vals.iter().enumerate() {
        let c = turbo((v - lo) / span);
        rgb[3 * i..3 * i + 3].copy_from_slice(&c);
    }
    write_rgb8(&dir.join(format!("{stem}.tif")), w, h, &rgb)?;

    let cw = crop.min(w);
    let ch = crop.min(h);
    let x0 = (w - cw) / 2;
    let y0 = (h - ch) / 2;
    let mut sub = vec![0u8; cw * ch * 3];
    for y in 0..ch {
        let s = ((y0 + y) * w + x0) * 3;
        sub[y * cw * 3..(y + 1) * cw * 3].copy_from_slice(&rgb[s..s + cw * 3]);
    }
    write_rgb8(&dir.join(format!("{stem}-crop.tif")), cw, ch, &sub)?;
    Ok(())
}

/// Elected-index speckle: fraction of interior pixels whose index differs from
/// the median of its 3x3 neighbourhood by more than `thresh` frames.
///
/// M2 §3.1's definition, kept exactly at `thresh = 2` so the number is
/// comparable with its 34.381% — measured there on the **retired** ring
/// difference. `merge.rs`'s own `Gate::admits` doc says no corpus row publishes a
/// regularised-Tenengrad speckle.
///
/// **This is used descriptively, against measured endpoints on the same stack —
/// never as a bar on an intervention.** M93 `P6`/`D-b`: a speckle bar scores
/// *change*, not correctness, and fails in the wrong direction.
fn speckle(idx: &[u16], geom: PlaneGeometry, thresh: i32) -> f64 {
    let (w, h) = (geom.width, geom.height);
    let mut hits = 0u64;
    let mut n = 0u64;
    let mut buf = [0u16; 9];
    for y in 1..h - 1 {
        for x in 1..w - 1 {
            let mut k = 0;
            for dy in 0..3 {
                let base = (y + dy - 1) * w + x - 1;
                for dx in 0..3 {
                    buf[k] = idx[base + dx];
                    k += 1;
                }
            }
            buf.sort_unstable();
            let med = i32::from(buf[4]);
            if (i32::from(idx[y * w + x]) - med).abs() > thresh {
                hits += 1;
            }
            n += 1;
        }
    }
    hits as f64 / n as f64
}

/// Everything pass one produces, plus the volume it produced it from.
struct Volume {
    geom: PlaneGeometry,
    /// One regularised focus plane per frame, in frame order.
    reg: Vec<Vec<f32>>,
    /// Luma of the middle frame, for the independent detail axis.
    mid_luma: Vec<f32>,
}

impl Volume {
    fn frames(&self) -> usize {
        self.reg.len()
    }
}

/// Decode a real stack and build the regularised focus volume.
fn load_real(paths: &[PathBuf]) -> Result<Volume> {
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let geom = first.geometry();
    let levels = first.levels;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let black = levels.black;
    println!("plane           : {} x {}", geom.width, geom.height);
    println!("iso / black     : {:?} / {black}", first.iso);
    drop(first);

    let px = geom.pixels();
    let bytes = (paths.len() as u64) * (px as u64) * 4;
    println!(
        "focus volume    : {:.2} GB resident ({} frames x {:.1} MB)",
        bytes as f64 / 1e9,
        paths.len(),
        px as f64 * 4.0 / 1e6
    );

    let mut field = FocusField::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut scratch = vec![0.0f32; px];
    let mut reg: Vec<Vec<f32>> = Vec::with_capacity(paths.len());
    let mut mid_luma = Vec::new();
    let mid = paths.len() / 2;

    for (i, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        if frame.geometry() != geom {
            bail!("{} has a different plane geometry", p.display());
        }
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        if i == mid {
            mid_luma = luma.clone();
        }
        field.compute(&luma, &noise);
        let mut dst = vec![0.0f32; px];
        regularise(field.values(), geom, &mut scratch, &mut dst);
        reg.push(dst);
        if i % 25 == 0 || i + 1 == paths.len() {
            println!("  decoded {}/{}", i + 1, paths.len());
        }
    }
    Ok(Volume {
        geom,
        reg,
        mid_luma,
    })
}

/// The positive control (pre-registration §4.1, discipline 594).
///
/// One real, sharp frame is blurred by a Gaussian-ish box ladder whose radius is
/// `delta * |k - k*(x)|`, with `k*` a smooth left-to-right ramp, plus sensor
/// noise drawn from the real `NoiseModel`. The truth is known by construction and
/// `delta` walks the plant continuously from decisive to arbitrary, so the
/// stimulus can express the failure the metric is meant to detect (rule 13).
/// How the plant's in-focus base image is made.
///
/// The positive control's whole job is to be a stack whose election is *known*
/// to be well-determined. A real frame is not that: a crop of real text is
/// mostly featureless paper, and on featureless paper the elected index really
/// is arbitrary, so the control cannot separate "the instrument is broken" from
/// "this region is genuinely undetermined". `Synth` removes that confound by
/// making a base with fine-scale power at every pixel. `Ramp` adds a known
/// vertical contrast gradient so the detail split (B4) has a ground truth.
#[derive(Clone, Copy, PartialEq, Eq)]
enum PlantBase {
    Real,
    Synth,
    Ramp,
}

fn load_plant(
    src: &Path,
    frames: usize,
    delta: f32,
    seed: u64,
    limit_side: usize,
    base_kind: PlantBase,
) -> Result<Volume> {
    let frame = strehl_raw::decode(src).with_context(|| format!("decoding {}", src.display()))?;
    let full = frame.geometry();
    let levels = frame.levels;
    let noise = profile::noise_model_for(&frame.camera, frame.iso, levels);
    let mut luma_full = vec![0.0f32; full.pixels()];
    let mut clip_full = vec![false; full.pixels()];
    green_luma_with_clip(
        &frame,
        levels.black,
        CONTAINER_MAX_DN,
        &mut luma_full,
        &mut clip_full,
    );
    drop(frame);

    // A square crop keeps the plant cheap enough to sweep `delta`.
    let side = limit_side.min(full.width).min(full.height);
    let geom = PlaneGeometry::from_active(side * 2, side * 2);
    assert_eq!(geom.width, side);
    let x0 = (full.width - side) / 2;
    let y0 = (full.height - side) / 2;
    let px = geom.pixels();
    let mut base = vec![0.0f32; px];
    let mut scratch = vec![0.0f32; px];
    match base_kind {
        PlantBase::Real => {
            for y in 0..side {
                let s = (y0 + y) * full.width + x0;
                base[y * side..(y + 1) * side].copy_from_slice(&luma_full[s..s + side]);
            }
        }
        PlantBase::Synth | PlantBase::Ramp => {
            // Band-limited noise: white noise smoothed by a 3x3 box, so the
            // power sits at 2-3 px -- the scale a macro subject carries at best
            // focus -- and every pixel has it.
            let mut trng = Rng::new(seed ^ 0x7E47_0000_0000_0001);
            let mut w = vec![0.0f32; px];
            for v in w.iter_mut() {
                *v = trng.normal();
            }
            box_mean(&w, geom, 1, &mut scratch, &mut base);
            let mean = f64::from(base.iter().copied().sum::<f32>()) / px as f64;
            let var = base
                .iter()
                .map(|v| (f64::from(*v) - mean).powi(2))
                .sum::<f64>()
                / px as f64;
            let inv = 1.0 / var.sqrt().max(1e-12) as f32;
            for (i, v) in base.iter_mut().enumerate() {
                let y = (i / side) as f32 / (side - 1).max(1) as f32;
                // `Ramp` runs the contrast from full at the top row to 1/64 at
                // the bottom, geometrically, so every decile of contrast is
                // populated and the detail split has a known truth.
                let amp = match base_kind {
                    PlantBase::Ramp => PLANT_AMP_DN * (0.015_625f32).powf(y),
                    _ => PLANT_AMP_DN,
                };
                *v = (PLANT_MEAN_DN + amp * ((*v - mean as f32) * inv)).max(1.0);
            }
        }
    }
    drop(luma_full);
    drop(clip_full);

    // Blur ladder. Radius 0 is the sharp original.
    let max_r = ((frames as f32) * delta).ceil() as usize + 1;
    let max_r = max_r.min(48);
    let mut ladder: Vec<Vec<f32>> = Vec::with_capacity(max_r + 1);
    ladder.push(base.clone());
    for r in 1..=max_r {
        let mut d = vec![0.0f32; px];
        box_mean(&base, geom, r, &mut scratch, &mut d);
        ladder.push(d);
    }

    // Truth: a smooth left-to-right ramp of the in-focus frame index.
    let kstar: Vec<f32> = (0..px)
        .map(|i| {
            let x = (i % side) as f32 / (side - 1).max(1) as f32;
            x * (frames - 1) as f32
        })
        .collect();

    let mut rng = Rng::new(seed);
    let mut field = FocusField::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut reg: Vec<Vec<f32>> = Vec::with_capacity(frames);
    for k in 0..frames {
        for i in 0..px {
            let r = (delta * (k as f32 - kstar[i]).abs()).round() as usize;
            let v = ladder[r.min(max_r)][i];
            let s = noise.green_luma_sigma(v);
            luma[i] = (v + s * rng.normal()).max(0.0);
        }
        field.compute(&luma, &noise);
        let mut dst = vec![0.0f32; px];
        regularise(field.values(), geom, &mut scratch, &mut dst);
        reg.push(dst);
    }
    let mid_luma = ladder[0].clone();
    let kind = match base_kind {
        PlantBase::Real => "real-frame crop",
        PlantBase::Synth => "synthetic band-limited texture, uniform contrast",
        PlantBase::Ramp => "synthetic band-limited texture, vertical contrast ramp",
    };
    println!("plant           : {side} x {side}, {frames} frames, delta {delta}, seed {seed}");
    println!("plant base      : {kind}");
    Ok(Volume {
        geom,
        reg,
        mid_luma,
    })
}

/// The measurement, computed entirely from a resident focus volume.
struct Election {
    win_idx: Vec<u16>,
    win_val: Vec<f32>,
    min_val: Vec<f32>,
    /// `n(t)`, `lo(t)`, `hi(t)` per tolerance rung.
    n: Vec<Vec<u16>>,
    lo: Vec<Vec<u16>>,
    hi: Vec<Vec<u16>>,
    /// `max R_k` over `|k - k_win| >= d`, per distance rung. `-inf` where the
    /// stack is too short for that distance to exist at that pixel.
    far: Vec<Vec<f32>>,
    /// Mean of the squared frame-axis fourth difference, per pixel.
    d4_sq: Vec<f64>,
    d4_n: u32,
}

fn elect(vol: &Volume, inverted_tiebreak: bool) -> Election {
    let px = vol.geom.pixels();
    let n_frames = vol.frames();
    let mut win_idx = vec![0u16; px];
    let mut win_val = vec![f32::NEG_INFINITY; px];
    let mut min_val = vec![f32::INFINITY; px];

    for (k, plane) in vol.reg.iter().enumerate() {
        let k = k as u16;
        for i in 0..px {
            let f = plane[i];
            if beats(f, k, win_val[i], win_idx[i], inverted_tiebreak) || win_val[i].is_infinite() {
                win_val[i] = f;
                win_idx[i] = k;
            }
            if f < min_val[i] {
                min_val[i] = f;
            }
        }
    }

    let tols: Vec<f32> = TOL_C.iter().map(|c| Gate::new(*c).tolerance()).collect();
    let mut n = vec![vec![0u16; px]; TOL_C.len()];
    let mut lo = vec![vec![u16::MAX; px]; TOL_C.len()];
    let mut hi = vec![vec![0u16; px]; TOL_C.len()];
    let mut far = vec![vec![f32::NEG_INFINITY; px]; DIST.len()];

    for (k, plane) in vol.reg.iter().enumerate() {
        let ku = k as u16;
        for i in 0..px {
            let f = plane[i];
            let dist = (i32::from(ku) - i32::from(win_idx[i])).unsigned_abs() as u16;
            for (r, &d) in DIST.iter().enumerate() {
                if dist >= d && f > far[r][i] {
                    far[r][i] = f;
                }
            }
            for (r, &t) in tols.iter().enumerate() {
                // Exactly `Gate::admits(f, best)`: `best - f <= tolerance`.
                if win_val[i] - f <= t {
                    n[r][i] += 1;
                    if ku < lo[r][i] {
                        lo[r][i] = ku;
                    }
                    if ku > hi[r][i] {
                        hi[r][i] = ku;
                    }
                }
            }
        }
    }

    // Frame-axis fourth difference, `[1,-4,6,-4,1]/6`. Under white noise its
    // variance is `sigma^2 * 70/36` **by algebra**, so the scale needs no fitted
    // constant. It annihilates any cubic in `k`, which is why it can be applied
    // to a smooth through-focus curve at all (M89, fact 1186).
    let mut d4_sq = vec![0.0f64; px];
    let mut d4_n = 0u32;
    if n_frames >= 5 {
        for k in 2..n_frames - 2 {
            for (i, acc) in d4_sq.iter_mut().enumerate() {
                let d = (f64::from(vol.reg[k - 2][i]) - 4.0 * f64::from(vol.reg[k - 1][i])
                    + 6.0 * f64::from(vol.reg[k][i])
                    - 4.0 * f64::from(vol.reg[k + 1][i])
                    + f64::from(vol.reg[k + 2][i]))
                    / 6.0;
                *acc += d * d;
            }
            d4_n += 1;
        }
        for v in &mut d4_sq {
            *v /= f64::from(d4_n);
        }
    }

    Election {
        win_idx,
        win_val,
        min_val,
        n,
        lo,
        hi,
        far,
        d4_sq,
        d4_n,
    }
}

/// Local standard deviation of one frame's luma over a `(2R+1)^2` window.
///
/// Rule 17: this is the **independent** detail axis. It is not the focus
/// measure, it never touches the argmax, and it comes from a single frame, so a
/// fluctuation in the focus response cannot manufacture its own bin.
fn detail_axis(luma: &[f32], geom: PlaneGeometry) -> Vec<f32> {
    let px = geom.pixels();
    let sq: Vec<f32> = luma.iter().map(|v| v * v).collect();
    let mut scratch = vec![0.0f32; px];
    let mut m1 = vec![0.0f32; px];
    let mut m2 = vec![0.0f32; px];
    box_mean(luma, geom, DETAIL_RADIUS, &mut scratch, &mut m1);
    box_mean(&sq, geom, DETAIL_RADIUS, &mut scratch, &mut m2);
    (0..px)
        .map(|i| (m2[i] - m1[i] * m1[i]).max(0.0).sqrt())
        .collect()
}

#[derive(Clone)]
struct Args {
    dir: Option<PathBuf>,
    limit: Option<usize>,
    out: PathBuf,
    plant: Option<f32>,
    plant_frames: usize,
    plant_side: usize,
    plant_src: PathBuf,
    plant_base: PlantBase,
    seeds: Vec<u64>,
    permute: bool,
    with_placebo: bool,
    invert_tiebreak: bool,
    check_neff: bool,
    render: bool,
    tag: String,
}

fn parse() -> Result<Args> {
    let mut a = Args {
        dir: None,
        limit: None,
        out: PathBuf::from(r"C:\dev\strehl-out\M94-election-margin"),
        plant: None,
        plant_frames: 60,
        plant_side: 512,
        plant_src: PathBuf::new(),
        plant_base: PlantBase::Real,
        seeds: Vec::new(),
        permute: false,
        with_placebo: false,
        invert_tiebreak: false,
        check_neff: false,
        render: false,
        tag: String::new(),
    };
    let mut it = std::env::args().skip(1);
    while let Some(s) = it.next() {
        match s.as_str() {
            "--limit" => a.limit = Some(it.next().context("--limit")?.parse()?),
            "--out" => a.out = PathBuf::from(it.next().context("--out")?),
            "--plant" => a.plant = Some(it.next().context("--plant")?.parse()?),
            "--plant-frames" => a.plant_frames = it.next().context("--plant-frames")?.parse()?,
            "--plant-side" => a.plant_side = it.next().context("--plant-side")?.parse()?,
            "--plant-src" => a.plant_src = PathBuf::from(it.next().context("--plant-src")?),
            "--plant-synth" => a.plant_base = PlantBase::Synth,
            "--plant-ramp" => a.plant_base = PlantBase::Ramp,
            "--seed" => a.seeds.push(it.next().context("--seed")?.parse()?),
            "--permute" => a.permute = true,
            "--with-placebo" => a.with_placebo = true,
            "--invert-tiebreak" => a.invert_tiebreak = true,
            "--check-neff" => a.check_neff = true,
            "--render" => a.render = true,
            "--tag" => a.tag = it.next().context("--tag")?,
            other => a.dir = Some(PathBuf::from(other)),
        }
    }
    if a.seeds.is_empty() {
        a.seeds.push(0x5EED_0001);
    }
    Ok(a)
}

fn arw_paths(dir: &Path, limit: Option<usize>) -> Result<Vec<PathBuf>> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    if paths.len() < 5 {
        bail!(
            "{} holds {} ARW files; need at least 5",
            dir.display(),
            paths.len()
        );
    }
    Ok(paths)
}

fn main() -> Result<()> {
    let args = parse()?;
    let dir = args
        .dir
        .clone()
        .context("usage: m94-election-margin <DIR> [--plant DELTA] [--limit N] [--render] ...")?;

    let label = if args.tag.is_empty() {
        dir.file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_else(|| "stack".into())
    } else {
        args.tag.clone()
    };

    println!("=== M94 election margin =========================================");
    println!("stack           : {}", dir.display());
    println!("label           : {label}");

    let mut vol = if let Some(delta) = args.plant {
        let src = if args.plant_src.as_os_str().is_empty() {
            arw_paths(&dir, None)?[0].clone()
        } else {
            args.plant_src.clone()
        };
        load_plant(
            &src,
            args.plant_frames,
            delta,
            args.seeds[0],
            args.plant_side,
            args.plant_base,
        )?
    } else {
        let paths = arw_paths(&dir, args.limit)?;
        println!("frames          : {}", paths.len());
        let v = load_real(&paths)?;
        // F2 needs a second decode pass, so it is opt-in.
        if args.check_neff {
            check_neff(&paths, &v)?;
        }
        v
    };

    // --- N3: the frame-axis permutation placebo -------------------------
    // Registered invariants: `R_win`, `R_min` and `m_1` are unchanged **to the
    // bit**, because the per-pixel multiset of responses is unchanged. Anything
    // index-shaped must move to its maximum-disorder value. A wiring error shows
    // up as an invariant moving, which is recognisable rather than merely wrong.
    if args.permute {
        // A DIFFERENT stream from the paired placebo below, so that running both
        // flags together gives two INDEPENDENT permutations. Sharing the seed
        // made the second arm sigma^2 of the first, which is not a null: the
        // square of a uniform random permutation is biased toward fixed points.
        let mut rng = Rng::new(args.seeds[0] ^ 0x1234_5678_9ABC_DEF0);
        let n = vol.reg.len();
        for i in (1..n).rev() {
            let j = rng.below((i + 1) as u64) as usize;
            vol.reg.swap(i, j);
        }
        println!("PLACEBO         : frame axis permuted (N3)");
    }
    if args.invert_tiebreak {
        println!("PLANT           : tie-break inverted (F3)");
    }

    let e = elect(&vol, args.invert_tiebreak);

    // --- F1: the mirror must be the shipped election --------------------
    let mut stats = FocusStats::new(vol.geom);
    for (k, plane) in vol.reg.iter().enumerate() {
        stats.fold(k as u16, plane)?;
    }
    let px = vol.geom.pixels();
    let same = (0..px)
        .filter(|&i| stats.best_index()[i] == e.win_idx[i])
        .count();
    let val_same = (0..px)
        .filter(|&i| stats.best_focus()[i].to_bits() == e.win_val[i].to_bits())
        .count();
    println!();
    println!("--- F1 faithfulness (bar: exactly 100.000000%) ---");
    println!(
        "  winner index  : {:.6}%  ({} of {} pixels)",
        100.0 * same as f64 / px as f64,
        same,
        px
    );
    println!(
        "  winner value  : {:.6}%  (f32 bit-identical)",
        100.0 * val_same as f64 / px as f64
    );
    let f1 = same == px && val_same == px;
    println!("  F1            : {}", if f1 { "PASS" } else { "FAIL" });

    report(&label, &vol, &e, &args, f1)?;

    // --- the paired permutation placebo, on the same resident volume -----
    //
    // Registered as N3 as a stand-alone run; promoted here to a paired arm
    // because the placebo turned out to be the only honest *floor* for `q_d`.
    // A global frame permutation leaves every pixel's multiset of responses
    // untouched, so `R_win`, `R_min`, `m_0` and `m_1` are invariant to the bit,
    // while every index-shaped quantity must go to maximum disorder. The
    // difference between the real arm and this arm is the part of the margin
    // that the frame *ordering* -- that is, focus -- actually explains.
    if args.with_placebo {
        // Permute in place: the real arm's report has already been written and
        // `Election` owns its data, so the original frame order is dead. A clone
        // would double a 9.9 GB resident volume on the owner's 299-frame stacks.
        let saved = std::mem::take(&mut vol.mid_luma);
        drop(saved);
        let mut rng = Rng::new(args.seeds[0] ^ 0xA5A5_A5A5);
        for i in (1..vol.reg.len()).rev() {
            let j = rng.below((i + 1) as u64) as usize;
            vol.reg.swap(i, j);
        }
        let pe = elect(&vol, false);
        println!();
        println!("=== PAIRED PLACEBO: frame axis permuted (N3, same volume) =========");
        let mut pargs = args.clone();
        pargs.render = false;
        report(&format!("{label}-permuted"), &vol, &pe, &pargs, f1)?;
        paired(&e, &pe, vol.geom);
    }
    Ok(())
}

/// The paired real-vs-placebo comparison.
///
/// This is the one statement in the milestone that rests on no constant, no
/// normalisation and no chosen bar. The same pixel is compared against itself
/// with the frame *order* destroyed and nothing else changed; the per-pixel
/// multiset of responses is bit-identical between the two arms. Under the null
/// "the frame order carries no information about this pixel", the real arm wins
/// exactly half the time. Whatever it wins above half is what focus explains.
fn paired(e: &Election, pe: &Election, geom: PlaneGeometry) {
    let interior = interior_of(geom);
    println!();
    println!("=== PAIRED real vs permuted, same pixels, same multiset ===========");
    println!("    null: win rate 50.000%, and identical `arbitrary` fractions.");
    println!("    `arbitrary` = m_d below the permuted arm's OWN median m_d, a");
    println!("    per-stack floor that needs no FOCUS_NOISE_SD.");
    for (r, &d) in DIST.iter().enumerate() {
        let both: Vec<usize> = interior
            .iter()
            .copied()
            .filter(|&i| e.far[r][i].is_finite() && pe.far[r][i].is_finite())
            .collect();
        if both.is_empty() {
            continue;
        }
        let mr: Vec<f32> = both.iter().map(|&i| e.win_val[i] - e.far[r][i]).collect();
        let mut mp: Vec<f32> = both.iter().map(|&i| pe.win_val[i] - pe.far[r][i]).collect();
        let wins = mr.iter().zip(&mp).filter(|(a, b)| a > b).count();
        let ties = mr.iter().zip(&mp).filter(|(a, b)| a == b).count();
        let losses = both.len() - wins - ties;
        mp.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let floor = quantile(&mp, 0.50);
        let arb_r = mr.iter().filter(|v| **v <= floor).count();
        let arb_p = mp.iter().filter(|v| **v <= floor).count();
        println!(
            "  d={d:<3} n={:9}  real-wins {:7.3}%  ties {:7.3}%  w/(w+l) {:7.3}%  | arbitrary: real {:7.3}%  permuted {:7.3}%",
            both.len(),
            100.0 * wins as f64 / both.len() as f64,
            100.0 * ties as f64 / both.len() as f64,
            100.0 * wins as f64 / (wins + losses).max(1) as f64,
            100.0 * arb_r as f64 / both.len() as f64,
            100.0 * arb_p as f64 / both.len() as f64
        );
    }
}

/// `F2`: my `n(t)` at the shipped gate must equal `Estimator::n_eff()` exactly.
fn check_neff(paths: &[PathBuf], vol: &Volume) -> Result<()> {
    let geom = vol.geom;
    let first = strehl_raw::decode(&paths[0])?;
    let black = first.levels.black;
    drop(first);
    let mut stats = FocusStats::new(geom);
    for (k, plane) in vol.reg.iter().enumerate() {
        stats.fold(k as u16, plane)?;
    }
    let mut est = Estimator::new(&stats, Gate::new(TOL_C[SHIPPED]));
    let mut luma = vec![0.0f32; geom.pixels()];
    let mut clipped = vec![false; geom.pixels()];
    let _ = (&mut luma, &mut clipped, black);
    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p)?;
        est.fold_censored(k as u16, &frame, &vol.reg[k], CONTAINER_MAX_DN)?;
    }
    let tol = Gate::new(TOL_C[SHIPPED]).tolerance();
    let mut mine = vec![0u16; geom.pixels()];
    for plane in &vol.reg {
        for i in 0..geom.pixels() {
            if stats.best_focus()[i] - plane[i] <= tol {
                mine[i] += 1;
            }
        }
    }
    let same = (0..geom.pixels())
        .filter(|&i| mine[i] == est.n_eff()[i])
        .count();
    println!();
    println!("--- F2 n_eff faithfulness (bar: exactly 100.000000%) ---");
    println!(
        "  n_eff         : {:.6}%  ({} of {})",
        100.0 * same as f64 / geom.pixels() as f64,
        same,
        geom.pixels()
    );
    println!(
        "  F2            : {}",
        if same == geom.pixels() {
            "PASS"
        } else {
            "FAIL"
        }
    );
    Ok(())
}

#[allow(clippy::too_many_lines)]
/// Interior pixels: the focus operator's support plus the regulariser's radius
/// is a partial window at the border, so those pixels are excluded everywhere.
fn interior_of(geom: PlaneGeometry) -> Vec<usize> {
    let border = strehl_core::focus::SUPPORT_RADIUS + strehl_core::merge::REGULARISER_RADIUS;
    (0..geom.pixels())
        .filter(|&i| {
            let (x, y) = (i % geom.width, i / geom.width);
            x >= border && y >= border && x + border < geom.width && y + border < geom.height
        })
        .collect()
}

fn report(label: &str, vol: &Volume, e: &Election, args: &Args, f1: bool) -> Result<()> {
    let geom = vol.geom;
    let px = geom.pixels();
    let n_frames = vol.frames() as f64;

    let border = strehl_core::focus::SUPPORT_RADIUS + strehl_core::merge::REGULARISER_RADIUS;
    let interior = interior_of(geom);
    println!();
    println!(
        "--- scope: {} interior pixels of {} ({:.2}%), border {} px excluded ---",
        interior.len(),
        px,
        100.0 * interior.len() as f64 / px as f64,
        border
    );

    // --- the confusion radius, over the tolerance ladder -----------------
    println!();
    println!("--- rho(t): furthest competitive frame, in frames and as a fraction of N ---");
    println!("    t = c * sqrt(2) * FOCUS_NOISE_SD; c = 4.0 is DEFAULT_GATE");
    let mut rho_shipped: Vec<u16> = Vec::new();
    let mut b1 = f64::NAN;
    for (r, &c) in TOL_C.iter().enumerate() {
        let mut rho: Vec<u16> = interior
            .iter()
            .map(|&i| {
                let w = i32::from(e.win_idx[i]);
                let a = (i32::from(e.hi[r][i]) - w).unsigned_abs() as u16;
                let b = (w - i32::from(e.lo[r][i])).unsigned_abs() as u16;
                a.max(b)
            })
            .collect();
        let mut gaps = 0u64;
        let mut gsum = 0u64;
        for &i in &interior {
            let span = i32::from(e.hi[r][i]) - i32::from(e.lo[r][i]) + 1;
            let g = span - i32::from(e.n[r][i]);
            if g > 0 {
                gaps += 1;
                gsum += g as u64;
            }
        }
        let n_mean: f64 =
            interior.iter().map(|&i| f64::from(e.n[r][i])).sum::<f64>() / interior.len() as f64;
        rho.sort_unstable();
        let med = quantile_u16(&rho, 0.50);
        if r == SHIPPED {
            b1 = f64::from(med) / n_frames;
            rho_shipped = rho.clone();
        }
        print!(
            "  c={c:<4} tol {:.6}  n_eff {n_mean:7.3}  rho med {med:5} ({:6.3} N)  p90 {:5}  p99 {:5}",
            Gate::new(c).tolerance(),
            f64::from(med) / n_frames,
            quantile_u16(&rho, 0.90),
            quantile_u16(&rho, 0.99),
        );
        println!(
            "  gap>0 {:6.3}%  mean gap {:.2}",
            100.0 * gaps as f64 / interior.len() as f64,
            gsum as f64 / gaps.max(1) as f64
        );
    }

    // --- B2, at the shipped gate ---
    let r = SHIPPED;
    let gaps = interior
        .iter()
        .filter(|&&i| i32::from(e.hi[r][i]) - i32::from(e.lo[r][i]) + 1 - i32::from(e.n[r][i]) > 0)
        .count();
    let b2 = 100.0 * gaps as f64 / interior.len() as f64;

    // --- the margin ladder, unit-free and in FOCUS_NOISE_SD units --------
    println!();
    println!("--- margin m_d = R_win - max R_k over |k - k_win| >= d ---");
    println!("    q_d = m_d / (R_win - R_min): fraction of the pixel's OWN through-focus range");
    println!("    s_d = m_d / FOCUS_NOISE_SD: the shipped constant, reported for reference only");
    let mut b3 = f64::NAN;
    let mut q8: Vec<f32> = Vec::new();
    for (r, &d) in DIST.iter().enumerate() {
        let defined: Vec<usize> = interior
            .iter()
            .copied()
            .filter(|&i| e.far[r][i].is_finite() && e.win_val[i] - e.min_val[i] > 0.0)
            .collect();
        if defined.is_empty() {
            println!("  d={d:<3} (no pixel has a rival at this distance)");
            continue;
        }
        let mut m: Vec<f32> = defined
            .iter()
            .map(|&i| e.win_val[i] - e.far[r][i])
            .collect();
        let mut q: Vec<f32> = defined
            .iter()
            .map(|&i| (e.win_val[i] - e.far[r][i]) / (e.win_val[i] - e.min_val[i]))
            .collect();
        m.sort_by(|a, b| a.partial_cmp(b).unwrap());
        q.sort_by(|a, b| a.partial_cmp(b).unwrap());
        if r == D8 {
            b3 = f64::from(quantile(&q, 0.50));
            q8 = q.clone();
        }
        print!(
            "  d={d:<3} n={:9}  q med {:8.5}",
            defined.len(),
            quantile(&q, 0.50)
        );
        for qq in QUANTILES {
            print!("  q{qq:<4.2}={:.5}", quantile(&q, qq));
        }
        println!();
        println!(
            "        s_d med {:9.4}   frac(m_d < 1 sigma_F) {:6.3}%   frac(m_d < gate tol) {:6.3}%",
            quantile(&m, 0.50) / FOCUS_NOISE_SD,
            100.0 * m.iter().filter(|v| **v < FOCUS_NOISE_SD).count() as f64 / m.len() as f64,
            100.0
                * m.iter()
                    .filter(|v| **v < Gate::new(TOL_C[SHIPPED]).tolerance())
                    .count() as f64
                / m.len() as f64
        );
    }

    // --- the directly measured response scale (context only) -------------
    if e.d4_n > 0 {
        let mut sig: Vec<f32> = interior
            .iter()
            .map(|&i| ((e.d4_sq[i] / (70.0 / 36.0)).sqrt()) as f32)
            .collect();
        sig.sort_by(|a, b| a.partial_cmp(b).unwrap());
        println!();
        println!(
            "--- sigma_R_hat: frame-axis 4th-difference scale, analytic null, no fitted constant ---"
        );
        println!(
            "    UPPER BOUND on the response noise (it also absorbs motion and under-sampling),"
        );
        println!(
            "    hence a LOWER bound on the margin in noise units. Context only; carries no headline."
        );
        print!("  sigma_R_hat  ");
        for qq in QUANTILES {
            print!("  q{qq:<4.2}={:.6}", quantile(&sig, qq));
        }
        println!();
        println!(
            "  median sigma_R_hat / FOCUS_NOISE_SD = {:.4}   (n windows = {})",
            quantile(&sig, 0.50) / FOCUS_NOISE_SD,
            e.d4_n
        );
    }

    // --- B4: the detail split, on an INDEPENDENT axis --------------------
    println!();
    println!("--- B4: q_8 by detail decile ---");
    println!("    axis A (independent): local sd of ONE frame's luma over a 33x33 window.");
    println!("    axis B (CIRCULAR, reported labelled): the winner's own focus response R_win.");
    let mut b4 = f64::NAN;
    if !vol.mid_luma.is_empty() {
        let det = detail_axis(&vol.mid_luma, geom);
        b4 = decile_split(&interior, &det, e, "A independent luma sd");
        let rwin: Vec<f32> = e.win_val.clone();
        decile_split(&interior, &rwin, e, "B CIRCULAR R_win");
    }

    // --- B5: coherence, against measured endpoints -----------------------
    println!();
    println!("--- B5: elected-index speckle (M2 3.1's definition, |k - median3x3| > 2) ---");
    println!("    Descriptive only, against endpoints measured on this same stack.");
    println!(
        "    M93 P6/D-b: speckle as a BAR ON AN INTERVENTION measures churn, not correctness."
    );
    let s_real = speckle(&e.win_idx, geom, SPECKLE_ABS);
    let mut hist = vec![0u64; vol.frames()];
    for &i in &interior {
        hist[e.win_idx[i] as usize] += 1;
    }
    let total: u64 = hist.iter().sum();
    let mut cum: Vec<u64> = Vec::with_capacity(hist.len());
    let mut acc = 0u64;
    for h in &hist {
        acc += h;
        cum.push(acc);
    }
    let mut rng = Rng::new(0xC0FF_EE01);
    let iid: Vec<u16> = (0..px)
        .map(|_| {
            let r = rng.below(total);
            cum.partition_point(|&c| c <= r) as u16
        })
        .collect();
    let s_iid = speckle(&iid, geom, SPECKLE_ABS);
    let unif: Vec<u16> = (0..px)
        .map(|_| rng.below(vol.frames() as u64) as u16)
        .collect();
    let s_unif = speckle(&unif, geom, SPECKLE_ABS);
    let b5 = s_real / s_iid;
    println!("  real election        : {:.4}%", 100.0 * s_real);
    println!("  N1 i.i.d. from own histogram : {:.4}%", 100.0 * s_iid);
    println!("  N2 uniform random    : {:.4}%", 100.0 * s_unif);
    println!("  B5 = real / iid      : {b5:.4}");

    // --- verdict against the pre-registered bars -------------------------
    println!();
    println!("--- pre-registered bars ---");
    verdict("B1 median rho / N   ", b1, 0.05, 0.20, true);
    verdict("B2 frac gap > 0 (%) ", b2, 5.0, 25.0, true);
    verdict("B3 median q_8       ", b3, 0.10, 0.02, false);
    println!(
        "  B4 q_8 decile ratio (top/bottom, independent axis) : {b4:.4}   (no bar; registered prediction >= 3x)"
    );
    verdict("B5 speckle / iid    ", b5, 0.20, 0.80, true);
    println!("  F1 : {}", if f1 { "PASS" } else { "FAIL" });

    // --- renders ---------------------------------------------------------
    if args.render {
        let dir = args.out.join(label);
        println!();
        println!("--- renders -> {} ---", dir.display());
        let idx: Vec<f32> = e.win_idx.iter().map(|&k| f32::from(k)).collect();
        render(
            &dir,
            "elected-index",
            geom,
            &idx,
            0.0,
            (vol.frames() - 1) as f32,
            1024,
        )?;
        let iidf: Vec<f32> = iid.iter().map(|&k| f32::from(k)).collect();
        render(
            &dir,
            "elected-index-null-iid",
            geom,
            &iidf,
            0.0,
            (vol.frames() - 1) as f32,
            1024,
        )?;
        let mut rho_map = vec![0.0f32; px];
        for (i, m) in rho_map.iter_mut().enumerate() {
            let w = i32::from(e.win_idx[i]);
            let a = (i32::from(e.hi[SHIPPED][i]) - w).abs();
            let b = (w - i32::from(e.lo[SHIPPED][i])).abs();
            *m = a.max(b) as f32 / (vol.frames() - 1).max(1) as f32;
        }
        render(&dir, "confusion-radius", geom, &rho_map, 0.0, 1.0, 1024)?;
        let mut qmap = vec![0.0f32; px];
        for (i, m) in qmap.iter_mut().enumerate() {
            let den = e.win_val[i] - e.min_val[i];
            *m = if e.far[D8][i].is_finite() && den > 0.0 {
                (e.win_val[i] - e.far[D8][i]) / den
            } else {
                0.0
            };
        }
        render(&dir, "margin-q8", geom, &qmap, 0.0, 0.30, 1024)?;
        println!(
            "  wrote elected-index, elected-index-null-iid, confusion-radius, margin-q8 (+ 1:1 crops)"
        );

        let mut j = BufWriter::new(File::create(dir.join("summary.json"))?);
        writeln!(
            j,
            "{{\"label\":\"{label}\",\"frames\":{},\"B1\":{b1},\"B2\":{b2},\"B3\":{b3},\"B4\":{b4},\"B5\":{b5},\"speckle_real\":{s_real},\"speckle_iid\":{s_iid},\"speckle_unif\":{s_unif}}}",
            vol.frames()
        )?;
    }
    let _ = (&rho_shipped, &q8);
    Ok(())
}

fn decile_split(interior: &[usize], axis: &[f32], e: &Election, name: &str) -> f64 {
    let mut keys: Vec<(f32, usize)> = interior
        .iter()
        .copied()
        .filter(|&i| e.far[D8][i].is_finite() && e.win_val[i] - e.min_val[i] > 0.0)
        .map(|i| (axis[i], i))
        .collect();
    if keys.len() < 100 {
        println!("  {name}: too few pixels");
        return f64::NAN;
    }
    keys.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let n = keys.len();
    let mut meds = Vec::with_capacity(10);
    print!("  {name:<24}");
    for b in 0..10 {
        let lo = n * b / 10;
        let hi = n * (b + 1) / 10;
        let mut q: Vec<f32> = keys[lo..hi]
            .iter()
            .map(|&(_, i)| (e.win_val[i] - e.far[D8][i]) / (e.win_val[i] - e.min_val[i]))
            .collect();
        q.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let m = quantile(&q, 0.50);
        meds.push(f64::from(m));
        print!(" {m:.4}");
    }
    println!();
    meds[9] / meds[0].max(1e-12)
}

/// Print a bar against its two pre-registered sides.
///
/// `high_is_bad = true` means the "decisive" side is `<= good` and the
/// "arbitrary" side is `>= bad`.
fn verdict(name: &str, v: f64, good: f64, bad: f64, high_is_bad: bool) {
    let s = if v.is_nan() {
        "NO DATA"
    } else if high_is_bad {
        if v <= good {
            "DECISIVE"
        } else if v >= bad {
            "NEARLY ARBITRARY"
        } else {
            "INTERMEDIATE"
        }
    } else if v >= good {
        "DECISIVE"
    } else if v <= bad {
        "NEARLY ARBITRARY"
    } else {
        "INTERMEDIATE"
    };
    println!("  {name}: {v:10.5}   -> {s}");
}
#[cfg(test)]
mod tests {
    use super::*;

    /// A hand-built through-focus fibre with a known answer, so the definitions
    /// are checked against arithmetic rather than against themselves.
    fn fibre() -> Vec<f32> {
        // peak at k = 3; a decoy at k = 8 that is close but strictly lower.
        vec![0.10, 0.20, 0.60, 1.00, 0.55, 0.18, 0.12, 0.30, 0.95, 0.25]
    }

    fn m_d(v: &[f32], d: usize) -> Option<f32> {
        let kw = (0..v.len()).max_by(|&a, &b| v[a].partial_cmp(&v[b]).unwrap())?;
        let far = (0..v.len())
            .filter(|&k| k.abs_diff(kw) >= d)
            .map(|k| v[k])
            .fold(f32::NEG_INFINITY, f32::max);
        far.is_finite().then(|| v[kw] - far)
    }

    #[test]
    fn the_trivial_placebo_is_exactly_zero_and_the_ladder_is_monotone() {
        // N4: `d = 0` includes the winner itself, so the margin must be 0 -- not
        // "small", exactly 0. Anything else means the far-set is mis-masked.
        let v = fibre();
        assert_eq!(m_d(&v, 0), Some(0.0));
        // Widening `d` can only remove rivals, so `m_d` is non-decreasing. This
        // is the property the report leans on when it reads the distance ladder.
        let mut prev = f32::NEG_INFINITY;
        for d in 0..v.len() {
            let m = m_d(&v, d).unwrap_or(f32::INFINITY);
            assert!(m >= prev, "m_{d} = {m} < previous {prev}");
            prev = m;
        }
        // The decoy at k = 8 is 5 away from the peak at k = 3, so it is the
        // binding rival at every d <= 5 and vanishes at d = 6.
        assert!((m_d(&v, 1).unwrap() - (1.00 - 0.95)).abs() < 1e-6);
        assert!((m_d(&v, 5).unwrap() - (1.00 - 0.95)).abs() < 1e-6);
        assert!((m_d(&v, 6).unwrap() - (1.00 - 0.25)).abs() < 1e-6);
    }

    /// The measured headline is that `m_1` cannot tell a focus stack from a
    /// shuffled one. That is not an empirical accident, it is algebra: `m_1` is
    /// the gap between the first and second order statistics of the per-pixel
    /// multiset, and permuting the frame axis does not change a multiset.
    #[test]
    fn the_naive_top_two_margin_is_invariant_to_any_frame_permutation() {
        let v = fibre();
        let mut rng = Rng::new(0xC0FF_EE01);
        for _ in 0..64 {
            let mut p = v.clone();
            for i in (1..p.len()).rev() {
                let j = rng.below((i + 1) as u64) as usize;
                p.swap(i, j);
            }
            assert_eq!(m_d(&p, 0), m_d(&v, 0));
            assert_eq!(m_d(&p, 1), m_d(&v, 1));
        }
    }

    /// Power for the test above: the same permutation must move `m_8`, or the
    /// invariance result is vacuous (discipline 594, applied to a unit test).
    #[test]
    fn but_the_distance_ladder_is_not_invariant() {
        let v: Vec<f32> = (0..40i16)
            .map(|k| 1.0 - (f32::from(k) - 17.0).abs() / 40.0)
            .collect();
        let mut rng = Rng::new(0xC0FF_EE02);
        let mut moved = 0;
        for _ in 0..64 {
            let mut p = v.clone();
            for i in (1..p.len()).rev() {
                let j = rng.below((i + 1) as u64) as usize;
                p.swap(i, j);
            }
            if m_d(&p, 8) != m_d(&v, 8) {
                moved += 1;
            }
        }
        assert!(moved > 32, "m_8 moved in only {moved} of 64 shuffles");
    }

    /// The mirror's comparator must be `FocusStats::beats`, and `--invert-tiebreak`
    /// must actually differ from it -- otherwise `F3` could never fail.
    #[test]
    fn the_tiebreak_plant_really_inverts_the_shipped_rule() {
        assert!(beats(1.0, 5, 0.5, 3, false));
        assert!(beats(1.0, 5, 0.5, 3, true));
        assert!(
            beats(0.5, 2, 0.5, 7, false),
            "shipped rule: lower index wins ties"
        );
        assert!(
            !beats(0.5, 2, 0.5, 7, true),
            "inverted rule must disagree on ties"
        );
        assert!(!beats(0.5, 9, 0.5, 7, false));
        assert!(beats(0.5, 9, 0.5, 7, true));
    }

    /// `box_mean` is the plant's blur ladder and the detail axis's window, so a
    /// bug in it would corrupt both the positive control and B4. Its mean over a
    /// constant field must be that constant, exactly, including at the borders.
    #[test]
    fn the_box_mean_preserves_a_constant_field_everywhere() {
        let geom = PlaneGeometry::from_active(64, 64);
        let px = geom.pixels();
        let src = vec![7.25f32; px];
        let mut scratch = vec![0.0f32; px];
        let mut dst = vec![0.0f32; px];
        for r in [1usize, 3, 8] {
            box_mean(&src, geom, r, &mut scratch, &mut dst);
            for (i, v) in dst.iter().enumerate() {
                assert!((v - 7.25).abs() < 1e-4, "r={r} i={i} v={v}");
            }
        }
    }
}
