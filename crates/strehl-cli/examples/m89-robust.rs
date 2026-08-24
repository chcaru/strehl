//! M89 — how much of a real focus bracket disagrees with the focus-only
//! assumption, and what a noise-normalised robustness mask costs and buys.
//!
//! Not a product path. This is the instrument for
//! `docs/research/M89-robustness-mask.md`, kept beside the shipped code so it
//! goes stale loudly rather than quietly. **Library integration is deliberately
//! deferred** — M85 holds `lib.rs`, `main.rs`, `merge_cmd.rs` and the output
//! pipeline and M86 holds `align.rs`, so nothing here edits any of them.
//!
//! # The separator
//!
//! Every prior attempt in this corpus foundered on the same rock: **defocus is
//! itself a disagreement**, so a frame-to-estimate residual lights up wherever
//! there is detail and says nothing about motion. M60's merge-time statistic
//! rose **5.11x** with detail on a clean stack, and 76–84% of its apparent
//! cross-stack signal was detail composition (M60 F5/F6).
//!
//! The separator used here is that **defocus is a low-order function of the
//! frame index and motion is not**. Focus sweeps smoothly, breathing is smooth,
//! photometric drift is smooth, and hot pixels and dust are *constant*. A
//! twitch, a bursting bubble or a cosmic ray is a step, a spike or a kink.
//!
//! So the statistic is a **leave-one-out local polynomial predictor along the
//! frame axis**, normalised by the calibrated noise model:
//!
//! ```text
//! z_f = (L_f − Σ_{j≠f} k_j·L_j) / sqrt( Σ_j r_j²·σ²(L_j) )
//! ```
//!
//! where `k` is the order-`p` least-squares fit over the `w−1` neighbours
//! evaluated at `f`, and `r` is the residual kernel (`r_f = 1`, `r_j = −k_j`).
//! Under *"the scene is static, `L_f` is locally order-`p` in `f`, and the
//! samples differ by independent sensor noise"*, **`E[z²] = 1` exactly**, for
//! every `w`, `p`, ISO and signal level. There is no fitted threshold and no
//! calibration stack, which is what lets a clean stack be a *test* rather than
//! the calibration set.
//!
//! ```text
//! cargo run --release -p strehl-cli --example m89-robust -- survey <DIR> [--stride N] [--limit N]
//! cargo run --release -p strehl-cli --example m89-robust -- plant  <DIR> [--limit N]
//! cargo run --release -p strehl-cli --example m89-robust -- mask   <DIR> [--gate G] [--limit N]
//! ```
//!
//! **Reads only.** It never writes to the stack directory.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::CfaPlane;
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::{FocusField, gradient_magnitude};
use strehl_core::merge::{DEFAULT_GATE, Estimator, FocusStats, Gate, regularise};
use strehl_core::noise::NoiseModel;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Widest window any operator in the sweep uses. The frame ring is sized from
/// this so one decode pass serves every `(w, p)` at once.
const WMAX: usize = 13;

/// The operator sweep. `p = 0` is the **negative-control operator**: a
/// leave-one-out local *mean*, focus-unaware, the temporal analogue of M60's
/// statistic. It exists so criterion A2 has the power to fail — if `p = 0` and
/// `p = 2` behave alike, the separator does nothing.
const OPERATORS: [(usize, usize); 6] = [(5, 0), (5, 2), (7, 2), (9, 2), (9, 4), (13, 4)];

/// Pre-registered primary: the smallest window that admits through-focus
/// curvature, so the least breathing accumulates inside it.
const PRIMARY: (usize, usize) = (5, 2);

/// Tail cuts, in sigmas of the calibrated noise model. `8` is the cut criteria
/// A4, A5 and B3 are written against.
const TAILS: [f32; 4] = [3.0, 5.0, 8.0, 12.0];

/// Detail and radial strata. Ten, so the axis matches M60's decile reporting.
const STRATA: usize = 10;

/// Box radius, in plane pixels, for the detail axis. 9x9 plane px = 18x18
/// sensor px — wide enough that a compact single-pixel transient cannot
/// manufacture the bucket it is then scored in (rule 17).
const DETAIL_RADIUS: usize = 4;

/// Mask ramp, **in sigmas of the calibrated noise model**. Not DN: a threshold
/// in DN would be a regression against this project's whole thesis.
///
/// The flat region below `Z0` is what makes the clean-data no-op structural
/// rather than lucky — under a Gaussian null `P(|z| > 4) = 6.3e-5`. A Welsch or
/// Geman-McClure `exp(−z²/2c²)`, the obvious design, has no flat region and
/// down-weights roughly 5% of *clean* samples at `c = 3`.
const MASK_Z0: f32 = 4.0;
const MASK_Z1: f32 = 8.0;

/// A frame is eligible to win the focus election when its mask weight is at
/// least this. Fixed at implementation time, before any measurement run.
const ELECTION_ELIGIBLE: f32 = 0.5;

// ---------------------------------------------------------------------------
// The operator
// ---------------------------------------------------------------------------

/// Residual kernel of the leave-one-out order-`p` local polynomial over a window
/// of `w` frames: `r[centre] = 1`, `r[j] = −k_j`.
///
/// `k` is row 0 of `(XᵀX)⁻¹Xᵀ` over the design `x ∈ {−h..h} \ {0}` — the weights
/// the least-squares polynomial gives the centre when the centre is *not* in the
/// fit. Asserted to reproduce a constant exactly, which is the property that
/// makes `E[z] = 0` under the null.
fn loo_residual_kernel(w: usize, p: usize) -> Vec<f64> {
    assert!(w >= 3 && w % 2 == 1, "window must be odd and at least 3");
    let h = (w - 1) / 2;
    assert!(
        p + 1 <= w - 1,
        "order {p} needs {} neighbours, window {w} has {}",
        p + 1,
        w - 1
    );
    let xs: Vec<f64> = (0..w)
        .filter(|&j| j != h)
        .map(|j| j as f64 - h as f64)
        .collect();
    let m = p + 1;
    // Normal equations A v = e0, with A[a][b] = Σ x^(a+b), augmented.
    let mut a = vec![vec![0.0f64; m + 1]; m];
    for (row, ar) in a.iter_mut().enumerate() {
        for (col, cell) in ar.iter_mut().enumerate().take(m) {
            *cell = xs.iter().map(|x| x.powi((row + col) as i32)).sum();
        }
        ar[m] = f64::from(u8::from(row == 0));
    }
    // Gauss-Jordan with partial pivoting. m <= 5, so this is not a hot path.
    for col in 0..m {
        let piv = (col..m)
            .max_by(|&i, &j| {
                a[i][col]
                    .abs()
                    .partial_cmp(&a[j][col].abs())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .expect("non-empty");
        a.swap(col, piv);
        let d = a[col][col];
        assert!(d.abs() > 1e-12, "singular design for w={w} p={p}");
        for v in a[col].iter_mut() {
            *v /= d;
        }
        for row in 0..m {
            if row != col {
                let f = a[row][col];
                if f != 0.0 {
                    for k in col..=m {
                        a[row][k] -= f * a[col][k];
                    }
                }
            }
        }
    }
    let v: Vec<f64> = (0..m).map(|i| a[i][m]).collect();
    let mut r = vec![0.0f64; w];
    let mut ksum = 0.0f64;
    let mut n = 0usize;
    for (j, rj) in r.iter_mut().enumerate() {
        if j == h {
            *rj = 1.0;
            continue;
        }
        let x = xs[n];
        n += 1;
        let kj: f64 = (0..m).map(|q| v[q] * x.powi(q as i32)).sum();
        ksum += kj;
        *rj = -kj;
    }
    // The fit must reproduce a constant, or the residual carries a DC term and
    // the "static scene" null is violated by construction rather than by data.
    assert!(
        (ksum - 1.0).abs() < 1e-9,
        "LOO weights for w={w} p={p} sum to {ksum}, not 1"
    );
    r
}

/// One operator, pre-flattened for the hot loop.
struct Op {
    w: usize,
    p: usize,
    h: usize,
    r: Vec<f32>,
    /// `r_j²`, so the variance sum is one more dot product rather than a square
    /// per tap.
    r2: Vec<f32>,
    r2_sum: f32,
}

impl Op {
    fn new(w: usize, p: usize) -> Self {
        let r = loo_residual_kernel(w, p);
        let r32: Vec<f32> = r.iter().map(|&v| v as f32).collect();
        let r2: Vec<f32> = r32.iter().map(|v| v * v).collect();
        Self {
            w,
            p,
            h: (w - 1) / 2,
            r2_sum: r2.iter().sum(),
            r: r32,
            r2,
        }
    }
    fn label(&self) -> String {
        format!("w={} p={}", self.w, self.p)
    }
}

/// Green-luma noise variance as an affine function of signal, `var(L) = A·L + B`,
/// **extracted from the calibrated model itself** rather than restated from
/// constants.
///
/// This lets the inner loop evaluate `Σ r_j²·σ²(L_j)` as
/// `A·Σ r_j²·L_j + B·Σ r_j²` — two dot products instead of `w` model calls per
/// pixel per operator per frame. The extraction is verified against the model at
/// three further points, so a change to a non-affine model breaks loudly here
/// instead of silently rescaling every `z` in this milestone.
struct AffineVar {
    a: f32,
    b: f32,
}

impl AffineVar {
    fn from(noise: &NoiseModel) -> Self {
        let b = noise.green_luma_sigma(0.0).powi(2);
        let a = noise.green_luma_sigma(1.0).powi(2) - b;
        let v = Self { a, b };
        for probe in [10.0f32, 1000.0, 8000.0] {
            let want = noise.green_luma_sigma(probe).powi(2);
            let got = v.a * probe + v.b;
            assert!(
                (got - want).abs() <= 1e-3 * want.max(1.0),
                "green_luma_sigma is not affine in signal at {probe}: model {want}, affine {got}. \
                 The whole of M89's inner loop assumes it is."
            );
        }
        v
    }
}

/// The z of one sample, from a ring of luma planes and a window's slot list.
#[inline]
fn z_at(ring: &[Vec<f32>], slots: &[usize], op: &Op, av: &AffineVar, i: usize) -> f32 {
    let mut num = 0.0f32;
    let mut vs = 0.0f32;
    for (j, &s) in slots.iter().enumerate() {
        let l = ring[s][i];
        num += op.r[j] * l;
        vs += op.r2[j] * l;
    }
    num / (av.a * vs + av.b * op.r2_sum).sqrt()
}

// ---------------------------------------------------------------------------
// Decode plumbing
// ---------------------------------------------------------------------------

struct Loader {
    geom: PlaneGeometry,
    noise: NoiseModel,
    black: f32,
    iso: Option<f32>,
    paths: Vec<PathBuf>,
}

/// Per-frame planes the passes consume. `luma` is black-subtracted and clamped
/// (the plane the noise model is denominated in); `graw` is the raw green mean
/// `(G1+G2)/2` in DN, which is what `Estimator::value` averages, so criterion B0
/// is an exact comparison rather than an approximate one.
struct Planes {
    luma: Vec<f32>,
    graw: Vec<f32>,
    clipped: Vec<bool>,
}

impl Loader {
    fn open(dir: &Path, limit: Option<usize>) -> Result<Self> {
        Self::open_every(dir, limit, 1)
    }

    /// Open a stack taking every `every`-th frame.
    ///
    /// This exists for one diagnostic and it is the strongest one available
    /// here. Defocus is smooth in frame index, so a fourth difference of it
    /// scales as `h^4` in the focus step: subsampling by two must multiply any
    /// *defocus leakage* by `2^4 = 16` in `z`, and so by **256** in `z^2 - 1`.
    /// A discrete disturbance obeys no such law. The prediction is large,
    /// signed and made in advance, which is what makes the answer worth having.
    fn open_every(dir: &Path, limit: Option<usize>, every: usize) -> Result<Self> {
        let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
            .with_context(|| format!("reading {}", dir.display()))?
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
            .collect();
        paths.sort();
        if let Some(n) = limit {
            paths.truncate(n);
        }
        if every > 1 {
            paths = paths.into_iter().step_by(every).collect();
        }
        if paths.len() < WMAX {
            bail!(
                "{} holds {} ARW files; need at least {WMAX}",
                dir.display(),
                paths.len()
            );
        }
        let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
        let geom = first.geometry();
        let levels = first.levels;
        let noise = profile::noise_model_for(&first.camera, first.iso, levels);
        Ok(Self {
            geom,
            noise,
            black: levels.black,
            iso: first.iso,
            paths,
        })
    }

    fn n(&self) -> usize {
        self.paths.len()
    }

    fn blank(&self) -> Planes {
        Planes {
            luma: vec![0.0; self.geom.pixels()],
            graw: vec![0.0; self.geom.pixels()],
            clipped: vec![false; self.geom.pixels()],
        }
    }

    /// Decode frame `f` into `out`, returning the decoded frame so a caller that
    /// needs the mosaic (the `Estimator` control) can keep it.
    fn load(&self, f: usize, out: &mut Planes) -> Result<strehl_raw::Frame> {
        let frame = strehl_raw::decode(&self.paths[f])
            .with_context(|| format!("decoding {}", self.paths[f].display()))?;
        if frame.geometry() != self.geom {
            bail!("{} has a different plane geometry", self.paths[f].display());
        }
        green_luma_with_clip(
            &frame,
            self.black,
            CONTAINER_MAX_DN,
            &mut out.luma,
            &mut out.clipped,
        );
        // The raw green mean, read from the same two samples the luma came from
        // so the two planes cannot drift apart.
        let g1o = CfaPlane::G1.rggb_offset();
        let g2o = CfaPlane::G2.rggb_offset();
        for py in 0..self.geom.height {
            let (row0, row1) = frame.quad_rows(py);
            let r1 = if g1o.1 == 0 { row0 } else { row1 };
            let r2 = if g2o.1 == 0 { row0 } else { row1 };
            let base = py * self.geom.width;
            for px in 0..self.geom.width {
                out.graw[base + px] =
                    0.5 * (f32::from(r1[2 * px + g1o.0]) + f32::from(r2[2 * px + g2o.0]));
            }
        }
        Ok(frame)
    }
}

/// Separable box mean, radius `rad`, edge-clamped. Local because `box_mean` in
/// `focus.rs` is private to that crate's internals.
fn box_mean(src: &[f32], geom: PlaneGeometry, rad: usize, scratch: &mut [f32], dst: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    let inv = 1.0 / (2 * rad + 1) as f32;
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        let mut acc = row[0] * rad as f32;
        for x in 0..=rad.min(w - 1) {
            acc += row[x];
        }
        for x in 0..w {
            scratch[y * w + x] = acc * inv;
            acc += row[(x + rad + 1).min(w - 1)] - row[x.saturating_sub(rad)];
        }
    }
    for x in 0..w {
        let mut acc = scratch[x] * rad as f32;
        for y in 0..=rad.min(h - 1) {
            acc += scratch[y * w + x];
        }
        for y in 0..h {
            dst[y * w + x] = acc * inv;
            acc += scratch[(y + rad + 1).min(h - 1) * w + x] - scratch[y.saturating_sub(rad) * w + x];
        }
    }
}

/// The detail axis: `max` over a **strided** subset of frames of the box-averaged
/// gradient magnitude.
///
/// Strided on purpose. A max over *every* frame would let a compact transient
/// raise the very bucket it is then scored in (rule 17); a max over every
/// `stride`-th frame, box-averaged over 9x9 plane pixels, cannot.
fn detail_axis(ld: &Loader, stride: usize) -> Result<(Vec<f32>, Vec<f32>, usize)> {
    let px = ld.geom.pixels();
    let mut detail = vec![0.0f32; px];
    let mut level = vec![0.0f32; px];
    let mut p = ld.blank();
    let mut grad = vec![0.0f32; px];
    let mut sc = vec![0.0f32; px];
    let mut bl = vec![0.0f32; px];
    let mut used = 0;
    for f in (0..ld.n()).step_by(stride) {
        drop(ld.load(f, &mut p)?);
        gradient_magnitude(&p.luma, ld.geom, &mut grad);
        box_mean(&grad, ld.geom, DETAIL_RADIUS, &mut sc, &mut bl);
        for (d, &b) in detail.iter_mut().zip(&bl) {
            if b > *d {
                *d = b;
            }
        }
        box_mean(&p.luma, ld.geom, DETAIL_RADIUS, &mut sc, &mut bl);
        for (l, &b) in level.iter_mut().zip(&bl) {
            *l += b;
        }
        used += 1;
    }
    let inv = 1.0 / used as f32;
    for l in &mut level {
        *l *= inv;
    }
    Ok((detail, level, used))
}

/// Fixed, absolute bin edges for the cross-stack detail axis.
///
/// The per-stack decile strata answer "within this stack, does the statistic
/// track detail?". They cannot answer "is `foam` worse than the null at the
/// *same* detail?", because decile 9 of one stack is not decile 9 of another.
/// These edges are absolute and, being in units of the predicted noise sigma at
/// the local signal level, they are comparable across ISO and exposure --
/// which raw DN gradient is not.
const SNR_EDGES: [f32; 10] = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0];

/// Local gradient magnitude expressed in sigmas of the calibrated noise model.
fn detail_snr(detail: &[f32], level: &[f32], model: &NoiseModel) -> Vec<f32> {
    detail
        .iter()
        .zip(level)
        .map(|(&d, &l)| {
            let s = model.green_luma_sigma(l.max(0.0));
            if s > 0.0 { d / s } else { 0.0 }
        })
        .collect()
}

/// Fixed signal-level bins, DN above black.
///
/// This axis is the mechanism discriminator, and it is the one axis that can
/// tell three otherwise identical inflations apart. Write the per-frame level as
/// `L_f = a_f * S + e_f`. A residual operator with `sum r = 0` annihilates `S`
/// and leaves `S * sum(r_j a_j) + sum(r_j e_j)`. Divided by the predicted
/// variance `~ g*S` at high signal, that gives
///
/// * **photometric drift** (`a_f` varying): `z^2 - 1` grows **linearly in S**,
///   because the numerator is proportional to `S` and the denominator to `S`
///   only under the square root;
/// * **a gain error** in the model: `z^2` is **flat in S** at high signal;
/// * **a read-noise error**: `z^2 - 1` decays as **1/S**.
///
/// So the shape of this row names the cause without a second capture.
const LEVEL_EDGES: [f32; 10] = [
    0.0, 32.0, 64.0, 128.0, 256.0, 512.0, 1024.0, 2048.0, 4096.0, 8192.0,
];

// ---------------------------------------------------------------------------
// Strata
// ---------------------------------------------------------------------------

/// Equal-count strata edges for a per-pixel axis, taken from a subsample so the
/// buckets are populated by construction (rule 36 — a fixture that produces a
/// constant where the test needs a spread ships permanently green).
fn strata_edges(values: &[f32], k: usize) -> Vec<f32> {
    let step = (values.len() / 400_000).max(1);
    let mut s: Vec<f32> = values.iter().step_by(step).copied().collect();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    (0..k).map(|b| s[(s.len() - 1) * b / k]).collect()
}

/// The stratum of every pixel, precomputed once.
///
/// Both axes are static functions of pixel position, so resolving them inside
/// the hot loop would cost twenty comparisons per sample per operator per frame
/// and dominate the run. This is a speed change with no effect on any number.
fn strata_map(values: &[f32], edges: &[f32]) -> Vec<u8> {
    values
        .iter()
        .map(|v| {
            edges
                .iter()
                .rposition(|e| *v >= *e)
                .unwrap_or(0)
                .min(u8::MAX as usize) as u8
        })
        .collect()
}

/// Normalised elliptical radius of every plane pixel, for the breathing check.
fn radius_map(geom: PlaneGeometry) -> Vec<f32> {
    let (cx, cy) = (
        (geom.width - 1) as f32 * 0.5,
        (geom.height - 1) as f32 * 0.5,
    );
    let mut out = vec![0.0f32; geom.pixels()];
    for y in 0..geom.height {
        for x in 0..geom.width {
            let dx = (x as f32 - cx) / cx;
            let dy = (y as f32 - cy) / cy;
            out[y * geom.width + x] = dx.mul_add(dx, dy * dy).sqrt();
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Accumulators
// ---------------------------------------------------------------------------

#[derive(Clone, Default)]
struct Cell {
    n: u64,
    sum_z2: f64,
    tails: [u64; 4],
}

impl Cell {
    #[inline]
    fn push(&mut self, z: f32) {
        self.n += 1;
        self.sum_z2 += f64::from(z) * f64::from(z);
        let a = z.abs();
        for (t, c) in TAILS.iter().zip(self.tails.iter_mut()) {
            if a > *t {
                *c += 1;
            }
        }
    }
    fn mean_z2(&self) -> f64 {
        if self.n == 0 {
            f64::NAN
        } else {
            self.sum_z2 / self.n as f64
        }
    }
    fn tail(&self, k: usize) -> f64 {
        if self.n == 0 {
            f64::NAN
        } else {
            self.tails[k] as f64 / self.n as f64
        }
    }
}

struct OpStats {
    all: Cell,
    by_detail: Vec<Cell>,
    by_snr: Vec<Cell>,
    by_level: Vec<Cell>,
    by_radius: Vec<Cell>,
    by_frame: BTreeMap<usize, Cell>,
    /// Per-pixel `Σ 1[|z| > 8]`, primary operator only. The map that localises
    /// *where* contamination is.
    hits: Vec<u32>,
    keep_maps: bool,
}

impl OpStats {
    fn new(px: usize, keep_maps: bool) -> Self {
        Self {
            all: Cell::default(),
            by_detail: vec![Cell::default(); STRATA],
            by_snr: vec![Cell::default(); SNR_EDGES.len()],
            by_level: vec![Cell::default(); LEVEL_EDGES.len()],
            by_radius: vec![Cell::default(); STRATA],
            by_frame: BTreeMap::new(),
            hits: if keep_maps { vec![0; px] } else { Vec::new() },
            keep_maps,
        }
    }
}

// ---------------------------------------------------------------------------
// survey
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_lines)]
fn survey(dir: &Path, limit: Option<usize>, stride: usize, sweep: bool, every: usize) -> Result<()> {
    let ld = Loader::open_every(dir, limit, every)?;
    let geom = ld.geom;
    let px = geom.pixels();
    let av = AffineVar::from(&ld.noise);
    println!("stack           : {}", dir.display());
    println!("frames          : {}", ld.n());
    println!("plane           : {} x {}", geom.width, geom.height);
    println!("iso / black     : {:?} / {}", ld.iso, ld.black);
    println!(
        "green var model : var(L) = {:.6}*L + {:.4}   (extracted from NoiseModel, verified affine)",
        av.a, av.b
    );

    let (detail, level, used) = detail_axis(&ld, stride)?;
    println!(
        "detail axis     : max of box{} |grad| over {used} frames (stride {stride})",
        2 * DETAIL_RADIUS + 1
    );
    let snr = detail_snr(&detail, &level, &ld.noise);
    let dedges = strata_edges(&detail, STRATA);
    let rmap = radius_map(geom);
    let redges = strata_edges(&rmap, STRATA);
    let dstrat = strata_map(&detail, &dedges);
    let rstrat = strata_map(&rmap, &redges);
    let sstrat = strata_map(&snr, &SNR_EDGES);
    let lstrat = strata_map(&level, &LEVEL_EDGES);
    drop(level);
    let mut snr_n = vec![0u64; SNR_EDGES.len()];
    for &s in &sstrat {
        snr_n[s as usize] += 1;
    }
    println!(
        "detail SNR bins : {}",
        snr_n
            .iter()
            .map(|n| format!("{:.4}", *n as f64 / px as f64))
            .collect::<Vec<_>>()
            .join(" ")
    );
    drop(rmap);
    drop(snr);

    let ops: Vec<Op> = OPERATORS
        .iter()
        .filter(|&&(w, p)| sweep || (w, p) == PRIMARY)
        .map(|&(w, p)| Op::new(w, p))
        .collect();
    let primary = ops
        .iter()
        .position(|o| (o.w, o.p) == PRIMARY)
        .expect("primary operator must be in the sweep");
    let mut stats: Vec<OpStats> = (0..ops.len())
        .map(|i| OpStats::new(px, i == primary))
        .collect();
    let mut ring: Vec<Vec<f32>> = (0..WMAX).map(|_| vec![0.0f32; px]).collect();
    let mut p = ld.blank();
    let t0 = std::time::Instant::now();
    for f in 0..ld.n() {
        drop(ld.load(f, &mut p)?);
        ring[f % WMAX].copy_from_slice(&p.luma);
        for (oi, op) in ops.iter().enumerate() {
            if f + 1 < op.w {
                continue;
            }
            let c = f - op.h;
            let slots: Vec<usize> = (0..op.w).map(|j| (f + 1 - op.w + j) % WMAX).collect();
            let st = &mut stats[oi];
            let mut fcell = Cell::default();
            for i in 0..px {
                let z = z_at(&ring, &slots, op, &av, i);
                st.all.push(z);
                fcell.push(z);
                st.by_detail[dstrat[i] as usize].push(z);
                st.by_snr[sstrat[i] as usize].push(z);
                st.by_level[lstrat[i] as usize].push(z);
                st.by_radius[rstrat[i] as usize].push(z);
                if st.keep_maps && z.abs() > TAILS[2] {
                    st.hits[i] += 1;
                }
            }
            st.by_frame.insert(c, fcell);
        }
        if f % 50 == 0 {
            println!(
                "  .. frame {f}/{} ({:.1}s)",
                ld.n(),
                t0.elapsed().as_secs_f32()
            );
        }
    }

    println!();
    println!("--- A1/A2/A3: the operator sweep (MEASURED) ---");
    println!(
        "E[z^2] = 1 exactly under 'static scene, locally order-p in f, independent sensor noise'."
    );
    println!(
        "{:<10} {:>10} {:>13} {:>12} {:>11} {:>11} {:>11}",
        "operator", "mean z^2", "detail hi/lo", "radial o/i", ">3sig", ">5sig", ">8sig"
    );
    for (op, st) in ops.iter().zip(&stats) {
        println!(
            "{:<10} {:>10.4} {:>13.3} {:>12.3} {:>11.3e} {:>11.3e} {:>11.3e}",
            op.label(),
            st.all.mean_z2(),
            st.by_detail[STRATA - 1].mean_z2() / st.by_detail[0].mean_z2(),
            st.by_radius[STRATA - 1].mean_z2() / st.by_radius[0].mean_z2(),
            st.all.tail(0),
            st.all.tail(1),
            st.all.tail(2),
        );
    }
    println!();
    for (op, st) in ops.iter().zip(&stats) {
        print!("{:<10} z^2 by detail :", op.label());
        for c in &st.by_detail {
            print!(" {:8.3}", c.mean_z2());
        }
        println!();
        print!("{:<10} z^2 by radius :", op.label());
        for c in &st.by_radius {
            print!(" {:8.3}", c.mean_z2());
        }
        println!();
        print!("{:<10} >8sig by det  :", op.label());
        for c in &st.by_detail {
            print!(" {:8.2e}", c.tail(2));
        }
        println!();
        print!("{:<10} z^2 by SNR    :", op.label());
        for c in &st.by_snr {
            print!(" {:8.3}", c.mean_z2());
        }
        println!();
        print!("{:<10} >8sig by SNR  :", op.label());
        for c in &st.by_snr {
            print!(" {:8.2e}", c.tail(2));
        }
        println!();
        print!("{:<10} z^2 by level  :", op.label());
        for c in &st.by_level {
            print!(" {:8.3}", c.mean_z2());
        }
        println!();
        print!("{:<10} n   by level  :", op.label());
        for c in &st.by_level {
            print!(" {:8.2e}", c.n as f64);
        }
        println!();
    }

    let st = &stats[primary];
    println!();
    println!(
        "--- primary operator {} : localisation (MEASURED) ---",
        ops[primary].label()
    );
    println!(
        "samples         : {}   mean z^2 {:.4}   >3sig {:.4e}  >5sig {:.4e}  >8sig {:.4e}  >12sig {:.4e}",
        st.all.n,
        st.all.mean_z2(),
        st.all.tail(0),
        st.all.tail(1),
        st.all.tail(2),
        st.all.tail(3),
    );
    let flagged = st.hits.iter().filter(|&&h| h > 0).count();
    let flagged2 = st.hits.iter().filter(|&&h| h > 1).count();
    println!(
        "pixels flagged  : {:.4}% of the frame at |z|>8 in >=1 frame, {:.4}% in >=2 frames",
        100.0 * flagged as f64 / px as f64,
        100.0 * flagged2 as f64 / px as f64
    );
    let mut fr: Vec<(usize, f64, f64)> = st
        .by_frame
        .iter()
        .map(|(&k, c)| (k, c.tail(2), c.mean_z2()))
        .collect();
    fr.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    let med = fr[fr.len() / 2].1;
    println!("worst frames    : (frame, frac|z|>8, mean z^2); median frame frac {med:.4e}");
    for (k, t, m) in fr.iter().take(8) {
        println!(
            "   frame {k:>4}   {t:.4e}   {m:9.3}   {:.1}x the median frame",
            if med > 0.0 { t / med } else { f64::NAN }
        );
    }
    let tw = 64usize;
    let mut tiles: Vec<f64> = Vec::new();
    for ty in (0..geom.height).step_by(tw) {
        for tx in (0..geom.width).step_by(tw) {
            let (mut n, mut hit) = (0u64, 0u64);
            for y in ty..(ty + tw).min(geom.height) {
                for x in tx..(tx + tw).min(geom.width) {
                    n += 1;
                    if st.hits[y * geom.width + x] > 0 {
                        hit += 1;
                    }
                }
            }
            tiles.push(hit as f64 / n as f64);
        }
    }
    tiles.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
    println!(
        "spatial ({tw}px tiles, n={}) : worst {:.4} p99 {:.4} p90 {:.4} median {:.4}",
        tiles.len(),
        tiles[0],
        tiles[tiles.len() / 100],
        tiles[tiles.len() / 10],
        tiles[tiles.len() / 2]
    );
    println!();
    println!(
        "JSON {{\"stack\":\"{}\",\"n\":{},\"iso\":{:?},\"mean_z2\":{:.6},\"tail3\":{:.6e},\
         \"tail5\":{:.6e},\"tail8\":{:.6e},\"tail12\":{:.6e},\"pixels_flagged\":{:.6},\
         \"detail_hi_lo\":{:.4},\"radial_out_in\":{:.4},\"worst_frame\":{},\"worst_frame_frac\":{:.6e},\
         \"median_frame_frac\":{:.6e},\"worst_tile\":{:.6},\"p99_tile\":{:.6},\
         \"z2_by_detail\":[{}],\"tail8_by_detail\":[{}],\"n_by_snr\":[{}],\
         \"z2_by_snr\":[{}],\"tail8_by_snr\":[{}],\"n_by_level\":[{}],\"z2_by_level\":[{}],\
         \"sweep\":[{}]}}",
        dir.file_name().unwrap_or_default().to_string_lossy(),
        ld.n(),
        ld.iso,
        st.all.mean_z2(),
        st.all.tail(0),
        st.all.tail(1),
        st.all.tail(2),
        st.all.tail(3),
        flagged as f64 / px as f64,
        st.by_detail[STRATA - 1].mean_z2() / st.by_detail[0].mean_z2(),
        st.by_radius[STRATA - 1].mean_z2() / st.by_radius[0].mean_z2(),
        fr[0].0,
        fr[0].1,
        med,
        tiles[0],
        tiles[tiles.len() / 100],
        st.by_detail
            .iter()
            .map(|c| format!("{:.4}", c.mean_z2()))
            .collect::<Vec<_>>()
            .join(","),
        st.by_detail
            .iter()
            .map(|c| format!("{:.6e}", c.tail(2)))
            .collect::<Vec<_>>()
            .join(","),
        st.by_snr
            .iter()
            .map(|c| c.n.to_string())
            .collect::<Vec<_>>()
            .join(","),
        st.by_snr
            .iter()
            .map(|c| format!("{:.4}", c.mean_z2()))
            .collect::<Vec<_>>()
            .join(","),
        st.by_snr
            .iter()
            .map(|c| format!("{:.6e}", c.tail(2)))
            .collect::<Vec<_>>()
            .join(","),
        st.by_level
            .iter()
            .map(|c| c.n.to_string())
            .collect::<Vec<_>>()
            .join(","),
        st.by_level
            .iter()
            .map(|c| format!("{:.4}", c.mean_z2()))
            .collect::<Vec<_>>()
            .join(","),
        ops.iter()
            .zip(&stats)
            .map(|(o, s)| format!(
                "{{\"w\":{},\"p\":{},\"mean_z2\":{:.4},\"detail_hi_lo\":{:.4},\"radial_out_in\":{:.4},\"tail8\":{:.4e}}}",
                o.w,
                o.p,
                s.all.mean_z2(),
                s.by_detail[STRATA - 1].mean_z2() / s.by_detail[0].mean_z2(),
                s.by_radius[STRATA - 1].mean_z2() / s.by_radius[0].mean_z2(),
                s.all.tail(2)
            ))
            .collect::<Vec<_>>()
            .join(","),
    );
    Ok(())
}

// ---------------------------------------------------------------------------
// the plant
// ---------------------------------------------------------------------------

/// Morphology of a planted disturbance. All three move **real frame content**
/// (M28's design): a tile replaced by the same tile taken `s` plane pixels away
/// *in the same frame*, so noise, defocus, illumination and sensor position are
/// correct by construction and nothing is synthesised. Rule 34 forbids a plant
/// generated by scaling `sigma_pred`, because `z` divides by it.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Morphology {
    /// One frame displaced. The easy case, and the one A4's monotonicity bar is
    /// written against.
    Transient,
    /// Displaced from frame `at` onward and staying there. An antenna that moves
    /// once. Low-order everywhere except at the step.
    Step,
    /// Displacement growing linearly across the whole stack. A hair drifting in
    /// a draught. This is the operator's **declared blind spot** and the number
    /// is reported whatever it is.
    Ramp,
}

#[derive(Clone, Copy)]
struct Plant {
    morph: Morphology,
    shift: isize,
    x0: usize,
    y0: usize,
    size: usize,
    at: usize,
}

impl Plant {
    /// Displacement this morphology applies at frame `f` of `n`.
    fn shift_at(&self, f: usize, n: usize) -> isize {
        match self.morph {
            Morphology::Transient => isize::from(f == self.at) * self.shift,
            Morphology::Step => isize::from(f >= self.at) * self.shift,
            Morphology::Ramp => {
                ((self.shift as f64) * (f as f64) / ((n - 1) as f64)).round() as isize
            }
        }
    }

    /// Replace the tile by the same tile taken `s` plane pixels away in this
    /// frame. `s = 0` is the placebo and still traverses every line here.
    fn apply(&self, f: usize, n: usize, geom: PlaneGeometry, luma: &mut [f32], buf: &mut [f32]) {
        let s = self.shift_at(f, n);
        for dy in 0..self.size {
            for dx in 0..self.size {
                let sx = ((self.x0 + dx) as isize + s).clamp(0, geom.width as isize - 1) as usize;
                let sy = (self.y0 + dy).min(geom.height - 1);
                buf[dy * self.size + dx] = luma[sy * geom.width + sx];
            }
        }
        for dy in 0..self.size {
            let row = (self.y0 + dy) * geom.width + self.x0;
            luma[row..row + self.size].copy_from_slice(&buf[dy * self.size..(dy + 1) * self.size]);
        }
    }
}

/// Run one plant and return
/// `(tile fraction over 8 sigma, background fraction, fraction inside the tile
/// at the planted frame only)`.
fn plant_score(
    ld: &Loader,
    av: &AffineVar,
    op: &Op,
    pl: &Plant,
) -> Result<(f64, f64, f64)> {
    let geom = ld.geom;
    let px = geom.pixels();
    let mut ring: Vec<Vec<f32>> = (0..op.w).map(|_| vec![0.0f32; px]).collect();
    let mut p = ld.blank();
    let mut buf = vec![0.0f32; pl.size * pl.size];
    let (mut ti, mut tn) = (0u64, 0u64);
    let (mut bi, mut bn) = (0u64, 0u64);
    let (mut ai, mut an) = (0u64, 0u64);
    for f in 0..ld.n() {
        drop(ld.load(f, &mut p)?);
        pl.apply(f, ld.n(), geom, &mut p.luma, &mut buf);
        ring[f % op.w].copy_from_slice(&p.luma);
        if f + 1 < op.w {
            continue;
        }
        let c = f - op.h;
        let slots: Vec<usize> = (0..op.w).map(|j| (f + 1 - op.w + j) % op.w).collect();
        for y in 0..geom.height {
            let in_rows = y >= pl.y0 && y < pl.y0 + pl.size;
            for x in 0..geom.width {
                let i = y * geom.width + x;
                let hit = u64::from(z_at(&ring, &slots, op, av, i).abs() > TAILS[2]);
                if in_rows && x >= pl.x0 && x < pl.x0 + pl.size {
                    ti += hit;
                    tn += 1;
                    if c == pl.at {
                        ai += hit;
                        an += 1;
                    }
                } else {
                    bi += hit;
                    bn += 1;
                }
            }
        }
    }
    Ok((
        ti as f64 / tn.max(1) as f64,
        bi as f64 / bn.max(1) as f64,
        ai as f64 / an.max(1) as f64,
    ))
}

/// A4: planted sensitivity, its `s = 0` placebo, and a flat-ROI control.
fn plant_run(dir: &Path, limit: Option<usize>) -> Result<()> {
    let ld = Loader::open(dir, limit)?;
    let geom = ld.geom;
    let av = AffineVar::from(&ld.noise);
    let op = Op::new(PRIMARY.0, PRIMARY.1);
    let size = 128usize;
    let (detail, _, _) = detail_axis(&ld, 8)?;

    // Choose the tile from the detail axis, not by eye. Rule 13: a plant on a
    // flat region is mathematically incapable of expressing a *displacement*
    // failure, so the detailed tile is what the sensitivity bar is written
    // against and the flat tile is the control proving the metric responds to
    // displaced content rather than to the act of planting.
    let margin = size + 64;
    let mut best = (f64::NEG_INFINITY, 0usize, 0usize);
    let mut worst = (f64::INFINITY, 0usize, 0usize);
    for y in (margin..geom.height - margin).step_by(64) {
        for x in (margin..geom.width - margin).step_by(64) {
            let mut acc = 0.0f64;
            for dy in (0..size).step_by(4) {
                for dx in (0..size).step_by(4) {
                    acc += f64::from(detail[(y + dy) * geom.width + x + dx]);
                }
            }
            if acc > best.0 {
                best = (acc, x, y);
            }
            if acc < worst.0 {
                worst = (acc, x, y);
            }
        }
    }
    println!("stack           : {}", dir.display());
    println!("frames          : {}   operator {}", ld.n(), op.label());
    println!(
        "detailed tile   : ({}, {}) mean box|grad| {:.2}",
        best.1,
        best.2,
        best.0 / (32.0 * 32.0)
    );
    println!(
        "flat tile       : ({}, {}) mean box|grad| {:.2}   <- rule 9's flat control",
        worst.1,
        worst.2,
        worst.0 / (32.0 * 32.0)
    );

    let at = ld.n() / 2;
    let cases: Vec<(Morphology, isize)> = [0isize, 1, 2, 4, 8, 16, 32]
        .iter()
        .map(|&s| (Morphology::Transient, s))
        .chain([0isize, 4, 16].iter().map(|&s| (Morphology::Step, s)))
        .chain([4isize, 16, 64].iter().map(|&s| (Morphology::Ramp, s)))
        .collect();
    println!();
    println!(
        "{:<7} {:<10} {:>4} {:>13} {:>13} {:>13}",
        "roi", "morphology", "s", "tile>8sig", "bkgd>8sig", "at-frame>8sig"
    );
    let mut json: Vec<String> = Vec::new();
    for detailed in [true, false] {
        let (x0, y0) = if detailed {
            (best.1, best.2)
        } else {
            (worst.1, worst.2)
        };
        for &(morph, shift) in &cases {
            if !detailed && morph != Morphology::Transient {
                continue;
            }
            let pl = Plant {
                morph,
                shift,
                x0,
                y0,
                size,
                at,
            };
            let (inside, outside, at_frame) = plant_score(&ld, &av, &op, &pl)?;
            println!(
                "{:<7} {:<10} {shift:>4} {inside:>13.4e} {outside:>13.4e} {at_frame:>13.4e}",
                if detailed { "detail" } else { "flat" },
                format!("{morph:?}")
            );
            json.push(format!(
                "{{\"roi\":\"{}\",\"morph\":\"{morph:?}\",\"s\":{shift},\"tile\":{inside:.6e},\
                 \"bkgd\":{outside:.6e},\"at_frame\":{at_frame:.6e}}}",
                if detailed { "detail" } else { "flat" }
            ));
        }
    }
    println!();
    println!(
        "JSON {{\"stack\":\"{}\",\"n\":{},\"at\":{at},\"rows\":[{}]}}",
        dir.file_name().unwrap_or_default().to_string_lossy(),
        ld.n(),
        json.join(",")
    );
    Ok(())
}

// ---------------------------------------------------------------------------
// levels -- the independent route to the photometric number
// ---------------------------------------------------------------------------

/// Per-frame global mean level, and the fourth difference of it.
///
/// This exists to check the survey's *inference* against a direct measurement
/// (rule 12: the author does not get to verify their own work). The survey can
/// only say "the inflation grows with signal level, which is what a
/// multiplicative per-frame fluctuation would do, and here is the implied
/// amplitude". This mode measures that amplitude a second way, from the frame
/// means alone, touching none of the survey's machinery: no residual kernel
/// applied to pixels, no noise model, no strata. If the two disagree, the
/// inference was wrong.
///
/// The mean is taken over the pixels that are neither near black nor near the
/// container maximum in **every** frame, so a subject drifting into or out of
/// clipping cannot masquerade as a gain change.
fn levels_run(dir: &Path, limit: Option<usize>) -> Result<()> {
    let ld = Loader::open(dir, limit)?;
    let geom = ld.geom;
    let px = geom.pixels();
    let n = ld.n();
    let mut p = ld.blank();

    let mut usable = vec![true; px];
    let mut sums = vec![0.0f64; n];
    for f in 0..n {
        drop(ld.load(f, &mut p)?);
        for ((u, &l), &c) in usable.iter_mut().zip(&p.luma).zip(&p.clipped) {
            *u &= !c && l > 16.0;
        }
    }
    let keep = usable.iter().filter(|u| **u).count();
    for (f, s) in sums.iter_mut().enumerate() {
        drop(ld.load(f, &mut p)?);
        let mut t = 0.0f64;
        for (v, u) in p.luma.iter().zip(&usable) {
            if *u {
                t += f64::from(*v);
            }
        }
        *s = t / keep as f64;
    }

    let grand = sums.iter().sum::<f64>() / n as f64;
    let a: Vec<f64> = sums.iter().map(|s| s / grand).collect();
    let (lo, hi) = a
        .iter()
        .fold((f64::MAX, f64::MIN), |(l, h), &v| (l.min(v), h.max(v)));

    // The same residual kernel the survey uses, applied to the frame means
    // rather than to pixels.
    let op = Op::new(PRIMARY.0, PRIMARY.1);
    let mut d4: Vec<f64> = Vec::new();
    for c in op.h..n - op.h {
        let mut acc = 0.0f64;
        for (j, r) in op.r.iter().enumerate() {
            acc += f64::from(*r) * a[c - op.h + j];
        }
        d4.push(acc);
    }
    let rms = (d4.iter().map(|v| v * v).sum::<f64>() / d4.len() as f64).sqrt();
    let peak = d4.iter().fold(0.0f64, |m, v| m.max(v.abs()));

    println!("stack           : {}", dir.display());
    println!("frames          : {n}   usable pixels {keep} ({:.2}%)", 100.0 * keep as f64 / px as f64);
    println!("mean level      : {grand:.2} DN above black");
    println!(
        "photometric p-p : {:.4}%   (max {:.6} / min {:.6} of the stack mean)",
        100.0 * (hi - lo),
        hi,
        lo
    );
    println!(
        "4th-difference  : rms {rms:.6}  peak {peak:.6}   (operator {} applied to frame means)",
        op.label()
    );
    println!(
        "JSON {{\"stack\":\"{}\",\"n\":{n},\"mean_level\":{grand:.4},\"pp\":{:.6},\
         \"d4_rms\":{rms:.6e},\"d4_peak\":{peak:.6e}}}",
        dir.file_name().unwrap_or_default().to_string_lossy(),
        hi - lo
    );
    Ok(())
}

// ---------------------------------------------------------------------------
// the mask
// ---------------------------------------------------------------------------

/// The robustness weight. **Sigmas of the calibrated noise model, never DN.**
#[inline]
fn mask_weight(z: f32) -> f32 {
    let a = z.abs();
    if a <= MASK_Z0 {
        1.0
    } else if a >= MASK_Z1 {
        0.0
    } else {
        let t = (MASK_Z1 - a) / (MASK_Z1 - MASK_Z0);
        t * t
    }
}

/// One election: per-pixel best regularised focus response and its frame.
struct Election {
    best: Vec<f32>,
    idx: Vec<u16>,
}

impl Election {
    fn new(px: usize) -> Self {
        Self {
            best: vec![f32::NEG_INFINITY; px],
            idx: vec![u16::MAX; px],
        }
    }
    /// The shipped tie-break, copied from `FocusStats::beats`: strictly greater,
    /// or equal with a lower frame index, so the fold is order-independent.
    #[inline]
    fn fold(&mut self, i: usize, f: u16, v: f32) {
        if v > self.best[i] || (v == self.best[i] && f < self.idx[i]) {
            self.best[i] = v;
            self.idx[i] = f;
        }
    }
}

/// One merged image: a weighted mean of the raw green means.
struct Acc {
    sum: Vec<f32>,
    wsum: Vec<f32>,
    /// Highest weight seen among admitted frames, and that frame's value. B1's
    /// fallback: if the mask drove total weight below 1, top it back up with the
    /// best-surviving frame so the estimate can never have a higher predicted
    /// variance than a single frame.
    bestw: Vec<f32>,
    bestg: Vec<f32>,
    removed: f64,
    total: f64,
    /// Admitted samples whose own `|z|` exceeded 8 sigma and which nonetheless
    /// carried full weight (arm 0) or were down-weighted (arms 1, 2).
    hot_admitted: u64,
    /// Pixels whose *elected winner* was itself over 8 sigma.
    hot_winner: u64,
    fallbacks: u64,
}

impl Acc {
    fn new(px: usize) -> Self {
        Self {
            sum: vec![0.0; px],
            wsum: vec![0.0; px],
            bestw: vec![-1.0; px],
            bestg: vec![0.0; px],
            removed: 0.0,
            total: 0.0,
            hot_admitted: 0,
            hot_winner: 0,
            fallbacks: 0,
        }
    }
    fn finish(&mut self) {
        for i in 0..self.sum.len() {
            if self.wsum[i] < 1.0 {
                let deficit = 1.0 - self.wsum[i];
                self.sum[i] += deficit * self.bestg[i];
                self.wsum[i] = 1.0;
                self.fallbacks += 1;
            }
        }
    }
    #[inline]
    fn value(&self, i: usize) -> f32 {
        self.sum[i] / self.wsum[i]
    }
}

/// Arms. 0 = mask off; 1 = mask on the average only; 2 = mask on both the
/// election and the average.
const ARMS: usize = 3;
/// Sub-stacks. 0 = all frames; 1 = even; 2 = odd. The split halves are the
/// ground-truth-free improvement metric (B4): a transient contaminates one half
/// and not the other.
const SUBS: usize = 3;

#[inline]
fn in_sub(f: usize, s: usize) -> bool {
    match s {
        0 => true,
        1 => f % 2 == 0,
        _ => f % 2 == 1,
    }
}

#[allow(clippy::too_many_lines)]
fn mask_run(dir: &Path, limit: Option<usize>, gate: f32) -> Result<()> {
    let ld = Loader::open(dir, limit)?;
    let geom = ld.geom;
    let px = geom.pixels();
    let av = AffineVar::from(&ld.noise);
    let op = Op::new(PRIMARY.0, PRIMARY.1);
    let g = Gate::new(gate);
    println!("stack           : {}", dir.display());
    println!(
        "frames          : {}   gate {gate}   tolerance {:.6}",
        ld.n(),
        g.tolerance()
    );
    println!(
        "operator        : {}   mask ramp |z| {MASK_Z0}..{MASK_Z1} sigma   election eligible w>={ELECTION_ELIGIBLE}",
        op.label()
    );

    let mut elect: Vec<Vec<Election>> = (0..2)
        .map(|_| (0..SUBS).map(|_| Election::new(px)).collect())
        .collect();
    let mut ref_stats = FocusStats::new(geom);
    let mut field = FocusField::new(geom);
    let mut boxsc = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];
    let mut lring: Vec<Vec<f32>> = (0..op.w).map(|_| vec![0.0f32; px]).collect();
    let mut rring: Vec<Vec<f32>> = (0..op.w).map(|_| vec![0.0f32; px]).collect();
    let mut gring: Vec<Vec<f32>> = (0..op.w).map(|_| vec![0.0f32; px]).collect();
    let mut p = ld.blank();
    let t0 = std::time::Instant::now();

    // ---- pass one: the elections -------------------------------------------
    let mut ineligible = 0u64;
    for f in 0..ld.n() {
        drop(ld.load(f, &mut p)?);
        field.compute(&p.luma, &ld.noise);
        regularise(field.values(), geom, &mut boxsc, &mut reg);
        ref_stats.fold(f as u16, &reg)?;
        lring[f % op.w].copy_from_slice(&p.luma);
        rring[f % op.w].copy_from_slice(&reg);
        for s in 0..SUBS {
            if in_sub(f, s) {
                for i in 0..px {
                    elect[0][s].fold(i, f as u16, reg[i]);
                }
            }
        }
        // The masked election lags by h frames: z_c is only known once the
        // window closes. Frames within h of either end are unmaskable and are
        // folded unmasked below — reported, not hidden.
        if f + 1 >= op.w {
            let c = f - op.h;
            let cslot = c % op.w;
            let slots: Vec<usize> = (0..op.w).map(|j| (f + 1 - op.w + j) % op.w).collect();
            for i in 0..px {
                if mask_weight(z_at(&lring, &slots, &op, &av, i)) >= ELECTION_ELIGIBLE {
                    for s in 0..SUBS {
                        if in_sub(c, s) {
                            elect[1][s].fold(i, c as u16, rring[cslot][i]);
                        }
                    }
                } else {
                    ineligible += 1;
                }
            }
        }
        if f % 50 == 0 {
            println!(
                "  pass1 frame {f}/{} ({:.1}s)",
                ld.n(),
                t0.elapsed().as_secs_f32()
            );
        }
    }
    // The 2h unmaskable end frames enter the masked election at full weight, so
    // it is not silently missing them.
    for f in (0..op.h).chain(ld.n() - op.h..ld.n()) {
        drop(ld.load(f, &mut p)?);
        field.compute(&p.luma, &ld.noise);
        regularise(field.values(), geom, &mut boxsc, &mut reg);
        for s in 0..SUBS {
            if in_sub(f, s) {
                for i in 0..px {
                    elect[1][s].fold(i, f as u16, reg[i]);
                }
            }
        }
    }
    let ref_idx = ref_stats.best_index();
    let elect_match = (0..px).filter(|&i| elect[0][0].idx[i] == ref_idx[i]).count();
    println!();
    println!("--- B0: faithfulness of this file's merge to the shipped one ---");
    println!(
        "B0a election    : {}/{} pixels ({:.6}%) match FocusStats::best_index exactly",
        elect_match,
        px,
        100.0 * elect_match as f64 / px as f64
    );
    let changed = (0..px)
        .filter(|&i| elect[0][0].idx[i] != elect[1][0].idx[i])
        .count();
    println!(
        "election shift  : masking the election changes the winner at {:.4}% of pixels \
         ({ineligible} frame-samples were ruled ineligible)",
        100.0 * changed as f64 / px as f64
    );

    // ---- pass two: the arms -------------------------------------------------
    let mut acc: Vec<Vec<Acc>> = (0..ARMS)
        .map(|_| (0..SUBS).map(|_| Acc::new(px)).collect())
        .collect();
    let mut refest = Estimator::new(&ref_stats, Gate::new(gate));
    let mut zbuf = vec![0.0f32; px];
    let mut clipped_any = vec![false; px];
    for f in 0..ld.n() {
        let frame = ld.load(f, &mut p)?;
        field.compute(&p.luma, &ld.noise);
        regularise(field.values(), geom, &mut boxsc, &mut reg);
        refest.fold(f as u16, &frame, &reg)?;
        drop(frame);
        for (c, &cl) in clipped_any.iter_mut().zip(&p.clipped) {
            *c |= cl;
        }
        lring[f % op.w].copy_from_slice(&p.luma);
        rring[f % op.w].copy_from_slice(&reg);
        gring[f % op.w].copy_from_slice(&p.graw);
        // Head frames never become a window centre; fold them unmasked.
        if f < op.h {
            fold_frame(&mut acc, &elect, &g, f, &p.graw, &reg, None, px);
        }
        if f + 1 >= op.w {
            let c = f - op.h;
            let cslot = c % op.w;
            let slots: Vec<usize> = (0..op.w).map(|j| (f + 1 - op.w + j) % op.w).collect();
            for (i, zb) in zbuf.iter_mut().enumerate() {
                *zb = z_at(&lring, &slots, &op, &av, i);
            }
            let (gc, rc) = (&gring[cslot], &rring[cslot]);
            fold_frame(&mut acc, &elect, &g, c, gc, rc, Some(&zbuf), px);
        }
        // Tail frames are all still in the ring at the last step.
        if f + 1 == ld.n() {
            for t in ld.n() - op.h..ld.n() {
                let slot = t % op.w;
                let (gc, rc) = (&gring[slot], &rring[slot]);
                fold_frame(&mut acc, &elect, &g, t, gc, rc, None, px);
            }
        }
        if f % 50 == 0 {
            println!(
                "  pass2 frame {f}/{} ({:.1}s)",
                ld.n(),
                t0.elapsed().as_secs_f32()
            );
        }
    }
    for arm in acc.iter_mut() {
        for a in arm.iter_mut() {
            a.finish();
        }
    }

    // ---- B0b / B0c ----------------------------------------------------------
    let neff = refest.n_eff();
    let mut nmatch = 0usize;
    let (mut dmax, mut dsq) = (0.0f64, 0.0f64);
    for i in 0..px {
        if (acc[0][0].wsum[i] - f32::from(neff[i])).abs() < 1e-6 {
            nmatch += 1;
        }
        let d = f64::from(acc[0][0].value(i) - refest.green_mean(i));
        dmax = dmax.max(d.abs());
        dsq += d * d;
    }
    println!(
        "B0b n_eff       : {}/{} pixels ({:.6}%) match Estimator::n_eff exactly",
        nmatch,
        px,
        100.0 * nmatch as f64 / px as f64
    );
    println!(
        "B0c green value : max |delta| {dmax:.6} DN, rms {:.6} DN vs Estimator::green_mean \
         (both f32 accumulations, so a small residue is float order, not logic)",
        (dsq / px as f64).sqrt()
    );
    println!(
        "clipping        : {:.4}% of pixels had at least one green at the container max \
         (this file does not model censoring; B0 is against Estimator::fold)",
        100.0 * clipped_any.iter().filter(|c| **c).count() as f64 / px as f64
    );

    // ---- B1 / B2 / B3 / B4 --------------------------------------------------
    println!();
    println!("--- B1/B2/B3: what the mask costs (MEASURED) ---");
    for (arm, label) in ["off", "average only", "election+average"].iter().enumerate() {
        let a = &acc[arm][0];
        println!(
            "arm {arm} ({label:<16}) weight removed {:.6}% of admitted   fallbacks {} ({:.6}% of px)   \
             min total weight {:.3}",
            100.0 * a.removed / a.total.max(1.0),
            a.fallbacks,
            100.0 * a.fallbacks as f64 / px as f64,
            a.wsum.iter().copied().fold(f32::INFINITY, f32::min)
        );
    }
    let sig1: Vec<f32> = (0..px)
        .map(|i| {
            let l = acc[0][0].value(i) - ld.black;
            (av.a * l.max(0.0) + av.b).sqrt()
        })
        .collect();
    for arm in 1..ARMS {
        let (mut s2, mut mx, mut moved) = (0.0f64, 0.0f64, 0u64);
        for i in 0..px {
            let d = f64::from((acc[arm][0].value(i) - acc[0][0].value(i)) / sig1[i]);
            s2 += d * d;
            mx = mx.max(d.abs());
            if d.abs() > 0.01 {
                moved += 1;
            }
        }
        println!(
            "arm {arm} vs arm 0 : merged green moved rms {:.6} sigma, max {mx:.3} sigma, \
             {:.4}% of pixels moved > 0.01 sigma",
            (s2 / px as f64).sqrt(),
            100.0 * moved as f64 / px as f64
        );
    }
    println!(
        "hot winners     : arm0 {} pixels ({:.5}%), arm2 {} ({:.5}%)  \
         [elected winner's own |z| > 8]",
        acc[0][0].hot_winner,
        100.0 * acc[0][0].hot_winner as f64 / px as f64,
        acc[2][0].hot_winner,
        100.0 * acc[2][0].hot_winner as f64 / px as f64
    );
    println!(
        "hot admitted    : arm0 {} samples, arm1 {} (down-weighted), arm2 {}",
        acc[0][0].hot_admitted, acc[1][0].hot_admitted, acc[2][0].hot_admitted
    );

    println!();
    println!("--- B4: split-half disagreement H, in sigmas (MEASURED) ---");
    println!("Pure noise gives E[H] = sqrt(2/pi) = 0.7979. Contamination inflates it.");
    let mut hs = Vec::new();
    for arm in 0..ARMS {
        let (mut sum, mut n) = (0.0f64, 0u64);
        let mut vals: Vec<f32> = Vec::with_capacity(px);
        for i in 0..px {
            let (me, mo) = (acc[arm][1].value(i), acc[arm][2].value(i));
            let (we, wo) = (acc[arm][1].wsum[i], acc[arm][2].wsum[i]);
            if !(me.is_finite() && mo.is_finite() && we > 0.0 && wo > 0.0) {
                continue;
            }
            let lbar = (0.5 * (me + mo) - ld.black).max(0.0);
            let var = av.a * lbar + av.b;
            let denom = (var * (1.0 / we + 1.0 / wo)).sqrt();
            let h = (me - mo).abs() / denom;
            sum += f64::from(h);
            n += 1;
            vals.push(h);
        }
        vals.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let mean = sum / n as f64;
        let q = |f: f64| f64::from(vals[((vals.len() - 1) as f64 * f) as usize]);
        println!(
            "arm {arm}  H mean {mean:.5}  median {:.5}  p99 {:.4}  p999 {:.4}  max {:.2}  \
             frac H>5 {:.5e}",
            q(0.5),
            q(0.99),
            q(0.999),
            q(1.0),
            vals.iter().filter(|v| **v > 5.0).count() as f64 / vals.len() as f64
        );
        hs.push((mean, q(0.5), q(0.99), q(0.999)));
    }
    println!(
        "B4 change       : arm1 {:+.4}% on mean H, {:+.4}% on p999 H;  arm2 {:+.4}% on mean H, {:+.4}% on p999 H",
        100.0 * (hs[1].0 - hs[0].0) / hs[0].0,
        100.0 * (hs[1].3 - hs[0].3) / hs[0].3,
        100.0 * (hs[2].0 - hs[0].0) / hs[0].0,
        100.0 * (hs[2].3 - hs[0].3) / hs[0].3,
    );
    println!();
    println!(
        "JSON {{\"stack\":\"{}\",\"n\":{},\"gate\":{gate},\"b0a\":{:.8},\"b0b\":{:.8},\"b0c_max\":{dmax:.6},\
         \"election_shift\":{:.6},\"removed_arm1\":{:.8},\"removed_arm2\":{:.8},\
         \"fallbacks_arm2\":{},\"hot_winner_arm0\":{},\"hot_winner_arm2\":{},\
         \"h_mean\":[{:.6},{:.6},{:.6}],\"h_p999\":[{:.4},{:.4},{:.4}],\
         \"rms_move_arm1\":{:.8},\"rms_move_arm2\":{:.8}}}",
        dir.file_name().unwrap_or_default().to_string_lossy(),
        ld.n(),
        elect_match as f64 / px as f64,
        nmatch as f64 / px as f64,
        changed as f64 / px as f64,
        acc[1][0].removed / acc[1][0].total.max(1.0),
        acc[2][0].removed / acc[2][0].total.max(1.0),
        acc[2][0].fallbacks,
        acc[0][0].hot_winner,
        acc[2][0].hot_winner,
        hs[0].0,
        hs[1].0,
        hs[2].0,
        hs[0].3,
        hs[1].3,
        hs[2].3,
        rms_move(&acc, 1, &sig1, px),
        rms_move(&acc, 2, &sig1, px),
    );
    Ok(())
}

fn rms_move(acc: &[Vec<Acc>], arm: usize, sig1: &[f32], px: usize) -> f64 {
    let mut s2 = 0.0f64;
    for i in 0..px {
        let d = f64::from((acc[arm][0].value(i) - acc[0][0].value(i)) / sig1[i]);
        s2 += d * d;
    }
    (s2 / px as f64).sqrt()
}

/// Fold one frame into every arm and sub-stack it belongs to.
///
/// `z` is `None` for the `2h` frames at the ends of the stack, which never
/// become a window centre and therefore carry full weight.
#[allow(clippy::too_many_arguments)]
fn fold_frame(
    acc: &mut [Vec<Acc>],
    elect: &[Vec<Election>],
    g: &Gate,
    f: usize,
    graw: &[f32],
    reg: &[f32],
    z: Option<&[f32]>,
    px: usize,
) {
    let fi = f as u16;
    for arm in 0..ARMS {
        let ei = usize::from(arm == 2);
        for s in 0..SUBS {
            if !in_sub(f, s) {
                continue;
            }
            let el = &elect[ei][s];
            let a = &mut acc[arm][s];
            for i in 0..px {
                let winner = el.idx[i] == fi;
                if !winner && !g.admits(reg[i], el.best[i]) {
                    continue;
                }
                let zz = z.map_or(0.0, |zs| zs[i]);
                let wt = if arm == 0 { 1.0 } else { mask_weight(zz) };
                let hot = zz.abs() > TAILS[2];
                if hot {
                    a.hot_admitted += 1;
                    if winner {
                        a.hot_winner += 1;
                    }
                }
                a.total += 1.0;
                a.removed += f64::from(1.0 - wt);
                a.sum[i] += wt * graw[i];
                a.wsum[i] += wt;
                if wt > a.bestw[i] {
                    a.bestw[i] = wt;
                    a.bestg[i] = graw[i];
                }
            }
        }
    }
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let mode = args
        .next()
        .context("usage: m89-robust <survey|plant|mask> <DIR> [opts]")?;
    let mut dir: Option<PathBuf> = None;
    let mut limit: Option<usize> = None;
    let mut stride = 8usize;
    let mut gate = DEFAULT_GATE;
    let mut sweep = false;
    let mut every = 1usize;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--limit" => limit = Some(args.next().context("--limit")?.parse()?),
            "--stride" => stride = args.next().context("--stride")?.parse()?,
            "--gate" => gate = args.next().context("--gate")?.parse()?,
            "--every" => every = args.next().context("--every")?.parse()?,
            "--sweep" => sweep = true,
            other => dir = Some(PathBuf::from(other)),
        }
    }
    let dir = dir.context("a stack directory is required")?;
    match mode.as_str() {
        "survey" => survey(&dir, limit, stride, sweep, every),
        "levels" => levels_run(&dir, limit),
        "plant" => plant_run(&dir, limit),
        "mask" => mask_run(&dir, limit, gate),
        other => bail!("unknown mode {other}"),
    }
}
