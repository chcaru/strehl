//! Per-tile, per-frame outlier detection for a focus stack.
//!
//! # The problem, and why the standard answer does not survive contact with it
//!
//! The reference shape is Wronski et al., *Handheld Multi-Frame
//! Super-Resolution* (HDR+), which measures per-tile disagreement against a
//! reference and normalises it by predicted noise. This project is unusually
//! well equipped for that half: [`NoiseModel`] is a calibrated, type-enforced
//! `sigma^2(S) = g*S + (RN*g)^2`, so "disagrees by more than noise explains" is
//! a measurable statement rather than a tuned constant.
//!
//! **But HDR+ assumes every frame is the same scene at the same focus, and a
//! focus stack is the one case where that is false by construction.** Every
//! frame legitimately disagrees with the reference wherever it is differently
//! focused, and that disagreement *is the signal the stack exists to harvest*.
//! A naive port fires hardest exactly where the merge is doing its job, masks
//! the in-focus detail, and looks like a principled robust estimator while
//! destroying the render.
//!
//! So the discriminator has to be **blind to focus difference and sensitive to
//! motion**. This module implements **four**, and is built so they can be
//! measured against each other rather than assumed. **Three of the four are
//! measured failures, and the fourth does not survive real captures.** Read the
//! enum before believing any of them; each variant carries its own verdict.
//!
//! - [`Discriminator::Raw`] — disagreement on the samples as they are. The
//!   naive port. It is included **because it is the thing that must fail**: a
//!   null from any other arm means nothing unless `Raw` fires on the same
//!   input. It is the inertness control, not a candidate.
//! - [`Discriminator::LowFreq`] — disagreement after both planes are low-pass
//!   filtered. **MEASURED FAILURE.** The intuition is that defocus is a
//!   low-pass so it should cancel; it does reduce the residual, but it reduces
//!   the *noise* far more, and the statistic is their ratio. M97r W3 derives
//!   that the ratio is independent of the filter radius, so **no radius helps.**
//! - [`Discriminator::Shift`] — displacement significance. **MEASURED
//!   FAILURE.** The symmetry argument holds for a straight edge and fails for a
//!   curved one; a disc genuinely shrinks under blur, so pure defocus reads as
//!   motion.
//! - [`Discriminator::ShiftFree`] — displacement with the defocus direction
//!   fitted out as an explicit nuisance parameter via a Schur complement. It
//!   survives every **synthetic** control. **It does not survive real
//!   captures** — see the enum and [`DEFAULT_MIN_SHIFT_PX`].
//!
//! A fifth form — comparing against the running estimate re-blurred to the
//! frame's own focus — is the only one where focus difference is absent from
//! the data term by construction. It is not implemented here; it needs the
//! merge's running estimate, and this module is deliberately free of the merge.
//!
//! **Do not read the paragraphs above as a recommendation to wire any of this
//! into the merge.** Five reports have now asked that question on real data —
//! M28, M60, M89, M123 and M97e — and none of them concluded yes. M89:
//! *"The metric works and should be adopted. The mask, as specified, should not
//! ship."* That header claim used to say the module "implements two" and
//! described `LowFreq` as an arm where defocus "largely cancels", forty lines
//! above an enum that said the opposite. A commissioning brief was written from
//! it. A stale header is not a cosmetic defect; it is the part of the file a
//! reader hits first.
//!
//! # The statistic
//!
//! Per tile, the **reduced chi-square** of the difference:
//!
//! ```text
//! chi2 = (1/N) * sum over the tile of  (a - b)^2 / (var_a + var_b)
//! ```
//!
//! This is the whole reason the threshold can be principled. Under the null —
//! same scene, same focus, independent noise — `Var(a - b) = var_a + var_b`
//! exactly, so **`E[chi2] = 1` regardless of signal level, tile size, exposure
//! or scene**. The unit is "times the noise the model predicts", never DN.
//!
//! Its null spread is `sqrt(2 / N_eff)`, so [`Params::threshold_k`] is a number
//! of null standard deviations and a tile fires when
//! `chi2 > 1 + k * sqrt(2 / N_eff)`.
//!
//! **A DN constant here would be the waxy-blob defect again** — an absolute
//! tolerance compared against a response that ranges over two orders of
//! magnitude across the corpus.
//!
//! # Noise propagation through the low-pass, which is not optional
//!
//! Box-averaging `m = (2r+1)^2 ` independent samples divides the noise variance
//! by `m`. If the low-pass is applied to the data without dividing the
//! predicted variance by `m`, `chi2` reads about `1/m` instead of 1 — at
//! `r = 6` that is 1/169, so **every tile passes and the mask is silently
//! inert**. That failure is invisible: it looks exactly like a clean stack.
//! `the_low_pass_variance_must_be_propagated_or_the_statistic_collapses` is a
//! planted control for precisely it.
//!
//! Averaging also correlates neighbouring outputs, so the tile's independent
//! sample count falls by the same factor: `N_eff = N / m`. Both corrections are
//! applied in [`chi2_map`].
//!
//! **Two approximations are declared rather than hidden.** [`box_mean`] clamps
//! its window at the plane edge, so edge pixels average fewer than `m` samples
//! and their variance is under-stated; and `N_eff = N / m` treats the box as
//! rectangular support, which is exact for the mean but approximate for the
//! correlation length. Both make the statistic slightly *conservative* in the
//! interior-dominated case and both are measurable by the calibration test.

use crate::boxfilter::box_mean;
use crate::noise::NoiseModel;
use crate::plane::PlaneGeometry;

/// Which disagreement to measure.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Discriminator {
    /// Compare the samples directly. The naive HDR+ port: it cannot tell a
    /// differently-focused frame from a moved one, and it is here to be shown
    /// failing on defocus so a `LowFreq` null is not vacuous.
    Raw,
    /// Compare after low-pass filtering both planes.
    ///
    /// **MEASURED FAILURE — this arm does not work, and it is kept because the
    /// reason is worth having in the tree.** The intuition is that defocus is a
    /// low-pass, so filtering both sides should make a differently-focused
    /// frame agree. It does reduce the residual — but it reduces the *noise*
    /// far more, and the statistic is a ratio of the two. Box-averaging
    /// `m = (2r+1)^2` samples divides the noise variance by `m`, while a
    /// spatially extended defocus residual survives almost intact.
    ///
    /// Asymptotically the two effects cancel exactly. For a step edge the
    /// residual between focus levels differing by `r_d` has amplitude of order
    /// `C * r_d / R` after filtering at radius `R`, and the filtered noise is of
    /// order `sigma / R`; the ratio is `C * r_d / sigma`, **independent of
    /// `R`**. Filtering cannot buy defocus-blindness because it rescales signal
    /// and noise together. Motion behaves identically, so the arm separates
    /// nothing.
    ///
    /// `low_pass_filtering_does_not_discriminate_defocus_it_amplifies_it`
    /// measures this: it fires on *more* tiles than [`Discriminator::Raw`].
    LowFreq,
    /// Local Lucas-Kanade displacement, normalised by its own predicted
    /// standard error.
    ///
    /// **This is the arm that works, and it works by construction rather than
    /// by tuning.** Defocus by a symmetric kernel preserves the local first
    /// moment: to first order it adds a Laplacian-like, locally even residual
    /// and contributes no displacement. Motion is a displacement by
    /// definition. So estimating the displacement and asking whether it is
    /// significant tests exactly the thing that separates the two, instead of
    /// testing overall disagreement and hoping focus cancels.
    ///
    /// The estimate solves the noise-weighted normal equations over the tile,
    /// and the statistic is `s^T G s / 2`, which is a reduced chi-square on two
    /// degrees of freedom: mean 1 and standard deviation 1 under the null, in
    /// units of predicted noise and never DN.
    ///
    /// **MEASURED FAILURE — this arm is not the one to ship.** The symmetry
    /// argument holds for a straight edge and fails for a curved one. Writing
    /// the Laplacian in edge-normal coordinates, `lap(s) = d2s/dn2 + k * ds/dn`
    /// where `k` is the curvature: the second term is **collinear with the
    /// gradient**, so blurring a curved feature genuinely displaces it. A disc
    /// shrinks under blur. That is real image formation, not an artefact, and
    /// it makes pure defocus read as motion --
    /// `the_unconditional_shift_arm_is_fooled_by_curvature` measures it firing
    /// on 90%+ of tiles of a stationary scene.
    Shift,
    /// Local displacement with the defocus direction fitted out as an explicit
    /// nuisance parameter. **This is the arm that survives every control.**
    ///
    /// The residual is regressed on three predictors instead of two — the two
    /// gradients and the Laplacian of the reference — and the statistic is the
    /// significance of the displacement pair *conditional* on the Laplacian
    /// coefficient, via the Schur complement. Any residual lying in the defocus
    /// direction is absorbed by the third parameter and cannot inflate the
    /// displacement statistic.
    ///
    /// This is blind to defocus **by construction rather than by tuning**, and
    /// it degrades honestly: where curvature makes "blurred more" and "moved"
    /// genuinely indistinguishable, the gradient and Laplacian predictors are
    /// collinear, the Schur complement shrinks, the standard error inflates and
    /// the statistic stops firing. It abstains exactly where the ambiguity is
    /// real, which is the correct behaviour and not something that had to be
    /// special-cased.
    ///
    /// **MEASURED ON REAL CAPTURES, AND IT DOES NOT SURVIVE THEM (M123).**
    /// Everything above is true of the four synthetic cases it was designed
    /// against, and M97r §6 says so: *"The gate configuration is in-sample."*
    /// On real frames the arm fires **29.55%** on a stationary tripod trap
    /// (`109MSDCF`, focus changing, nothing moving) against **6.87%** on `foam`,
    /// a stack with independently measured motion — **it fires 4.3x harder on
    /// the stack that did not move.** The positive control is worse: a planted
    /// translation on a real defocus pair reads **24.51% gated at 0.00 px
    /// planted**, so a quarter of the tiles fire on no motion at all.
    ///
    /// Do not read "survives every control" as "ready". It survived every
    /// control that existed when it was written, all of which it also chose.
    ShiftFree,
}

/// Tunables. `tile` and `blur_radius` are in plane pixels.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Params {
    /// Tile edge. The statistic is pooled over `tile * tile` samples, so this
    /// sets both the spatial resolution of the mask and its null spread.
    pub tile: usize,
    /// Low-pass radius, ignored by [`Discriminator::Raw`]. Should exceed the
    /// largest defocus blur difference the bracket contains, or defocus will
    /// survive the filter and be read as motion.
    pub blur_radius: usize,
    /// Threshold in **null standard deviations** of the reduced chi-square.
    pub threshold_k: f32,
}

impl Default for Params {
    fn default() -> Self {
        Self {
            tile: 32,
            blur_radius: 6,
            threshold_k: 6.0,
        }
    }
}

/// The tiling of a plane. Partial tiles at the right and bottom edges are
/// included and carry fewer samples, which widens their null spread; that is
/// accounted for per tile rather than globally.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TileGrid {
    pub cols: usize,
    pub rows: usize,
    pub tile: usize,
    pub width: usize,
    pub height: usize,
}

impl TileGrid {
    pub fn new(geom: PlaneGeometry, tile: usize) -> Self {
        assert!(tile > 0, "tile edge must be positive");
        Self {
            cols: geom.width.div_ceil(tile),
            rows: geom.height.div_ceil(tile),
            tile,
            width: geom.width,
            height: geom.height,
        }
    }

    pub fn len(&self) -> usize {
        self.cols * self.rows
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Scratch buffers, reused across frames so the per-frame cost is arithmetic
/// rather than allocation.
#[derive(Debug, Clone)]
pub struct Scratch {
    a: Vec<f32>,
    b: Vec<f32>,
    tmp: Vec<f32>,
}

impl Scratch {
    pub fn new(geom: PlaneGeometry) -> Self {
        let n = geom.pixels();
        Self {
            a: vec![0.0; n],
            b: vec![0.0; n],
            tmp: vec![0.0; n],
        }
    }
}

/// Reduced chi-square per tile between two black-subtracted green-luma planes.
///
/// `a` is the frame under test and `b` the reference. Both are in DN and both
/// must be `geom.pixels()` long. The returned vector is `grid.len()` long in
/// row-major tile order; a tile with no samples reads `0.0`.
///
/// Values are "times the noise the model predicts": 1.0 is agreement, and the
/// unit does not depend on signal level.
pub fn chi2_map(
    a: &[f32],
    b: &[f32],
    geom: PlaneGeometry,
    noise: &NoiseModel,
    params: Params,
    disc: Discriminator,
    scratch: &mut Scratch,
) -> Vec<f32> {
    assert_eq!(a.len(), geom.pixels(), "a must be plane-sized");
    assert_eq!(b.len(), geom.pixels(), "b must be plane-sized");

    if matches!(disc, Discriminator::Shift | Discriminator::ShiftFree) {
        return shift_map(a, b, geom, noise, params, disc == Discriminator::ShiftFree);
    }

    // `m` is the number of independent samples each filtered output averages,
    // and it divides the predicted variance. For `Raw` it is 1, which is what
    // makes the two arms share one code path and therefore one calibration.
    let (sa, sb, m) = match disc {
        Discriminator::Raw => (a, b, 1.0f32),
        Discriminator::LowFreq => {
            let r = params.blur_radius;
            box_mean(a, geom, r, &mut scratch.tmp, &mut scratch.a);
            box_mean(b, geom, r, &mut scratch.tmp, &mut scratch.b);
            let side = 2 * r + 1;
            (
                scratch.a.as_slice(),
                scratch.b.as_slice(),
                (side * side) as f32,
            )
        }
        Discriminator::Shift | Discriminator::ShiftFree => unreachable!("handled above"),
    };

    let grid = TileGrid::new(geom, params.tile);
    let mut out = vec![0.0f32; grid.len()];
    for ty in 0..grid.rows {
        let y0 = ty * grid.tile;
        let y1 = (y0 + grid.tile).min(geom.height);
        for tx in 0..grid.cols {
            let x0 = tx * grid.tile;
            let x1 = (x0 + grid.tile).min(geom.width);
            let mut acc = 0.0f64;
            let mut n = 0u32;
            for y in y0..y1 {
                let row = y * geom.width;
                for x in x0..x1 {
                    let i = row + x;
                    let (av, bv) = (sa[i], sb[i]);
                    // Variance is evaluated at each frame's own level, so a
                    // photometric or exposure difference widens the denominator
                    // honestly instead of being read as disagreement.
                    let va = luma_variance(noise, av) / m;
                    let vb = luma_variance(noise, bv) / m;
                    let d = f64::from(av - bv);
                    let den = f64::from(va + vb);
                    if den > 0.0 {
                        acc += d * d / den;
                        n += 1;
                    }
                }
            }
            out[ty * grid.cols + tx] = if n == 0 {
                0.0
            } else {
                (acc / f64::from(n)) as f32
            };
        }
    }
    out
}

/// Minimum smaller eigenvalue of the noise-weighted gradient matrix for a tile
/// to carry a usable displacement estimate.
///
/// The unit is not arbitrary: `G` is a sum of `grad^2 / variance`, so
/// `s^T G s` is the squared significance a displacement `s` would produce.
/// Requiring the smaller eigenvalue to reach 1.0 says "a one-pixel shift in the
/// worst-constrained direction must produce at least a one-sigma signal". A
/// flat, gradient-free tile carries no information about displacement, and this
/// makes it abstain instead of dividing by an almost-singular matrix.
const MIN_GRADIENT_INFO: f64 = 1.0;

/// Per-tile displacement significance, as a reduced chi-square on two degrees
/// of freedom.
///
/// Solves the noise-weighted normal equations `G s = rhs` over each tile, where
/// `G = sum grad(b) grad(b)^T / var` and `rhs = sum grad(b) * (a - b) / var`,
/// then reports `s^T G s / 2 = s . rhs / 2`.
///
/// Under the null — no displacement, independent noise — `rhs` is distributed
/// `N(0, G)` by construction, so `s^T G s` is exactly chi-square on two degrees
/// of freedom and the reported value has mean 1 and standard deviation 1. **The
/// degrees of freedom are two however many pixels the tile pools**: a larger
/// tile buys a better displacement estimate, not a tighter null.
///
/// Gradients are central differences on the reference, so the outermost ring of
/// the plane is skipped.
/// A tile's displacement estimate and its significance.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TileShift {
    /// Estimated displacement in plane pixels.
    pub sx: f32,
    pub sy: f32,
    /// `s^T G s / 2` — a reduced chi-square on two degrees of freedom.
    pub chi2: f32,
    /// The estimator's own standard error, in plane pixels, along its
    /// worst-constrained direction.
    ///
    /// This is what makes the abstention rule self-describing: a tile is only
    /// worth believing about a displacement of `d` px if it can actually
    /// resolve `d` px. Infinite when the tile carries no usable gradient.
    pub sigma_px: f32,
    /// False when the tile carried too little gradient to estimate anything.
    /// An abstaining tile reads zero everywhere and must never be counted as
    /// evidence of agreement.
    pub informative: bool,
}

/// Per-tile displacement estimates, with significance.
///
/// Exposed separately from [`chi2_map`] because the magnitude and the
/// significance answer different questions and the difference turned out to
/// matter: a sub-pixel bias can be overwhelmingly significant and still be
/// harmless.
pub fn shift_tiles(
    a: &[f32],
    b: &[f32],
    geom: PlaneGeometry,
    noise: &NoiseModel,
    params: Params,
    nuisance: bool,
) -> Vec<TileShift> {
    let (w, h) = (geom.width, geom.height);
    let grid = TileGrid::new(geom, params.tile);
    let blank = TileShift {
        sx: 0.0,
        sy: 0.0,
        chi2: 0.0,
        sigma_px: f32::INFINITY,
        informative: false,
    };
    let mut out = vec![blank; grid.len()];
    for ty in 0..grid.rows {
        let y0 = ty * grid.tile;
        let y1 = (y0 + grid.tile).min(h);
        for tx in 0..grid.cols {
            let x0 = tx * grid.tile;
            let x1 = (x0 + grid.tile).min(w);
            let (mut gxx, mut gxy, mut gyy) = (0.0f64, 0.0f64, 0.0f64);
            let (mut gxl, mut gyl, mut gll) = (0.0f64, 0.0f64, 0.0f64);
            let (mut rx, mut ry, mut rl) = (0.0f64, 0.0f64, 0.0f64);
            for y in y0..y1 {
                if y == 0 || y + 1 >= h {
                    continue;
                }
                for x in x0..x1 {
                    if x == 0 || x + 1 >= w {
                        continue;
                    }
                    let i = y * w + x;
                    let gx = f64::from(0.5 * (b[i + 1] - b[i - 1]));
                    let gy = f64::from(0.5 * (b[i + w] - b[i - w]));
                    // Five-point Laplacian: the direction a symmetric defocus
                    // kernel moves the samples in, to first order.
                    let lap =
                        f64::from(b[i + 1] + b[i - 1] + b[i + w] + b[i - w] - 4.0 * b[i]);
                    let d = f64::from(a[i] - b[i]);
                    let var =
                        f64::from(luma_variance(noise, a[i]) + luma_variance(noise, b[i]));
                    if var <= 0.0 {
                        continue;
                    }
                    let iv = 1.0 / var;
                    // The gradients are measured from noisy samples, so their
                    // squares are biased upward by the noise's own variance:
                    // E[gx_meas^2] = gx_true^2 + Var(gx_noise). Left
                    // uncorrected this inflates the information matrix with
                    // pure noise -- on a low-contrast tile it dominates it 48x
                    // -- which shrinks the estimate toward zero (regression
                    // dilution) and makes the abstention guard measure noise
                    // instead of signal. Having a calibrated noise model is
                    // exactly what makes the correction available rather than
                    // guessed.
                    //
                    // Var(0.5*(n[i+1] - n[i-1]))       = 0.5  * var_b
                    // Var(n[i+1]+n[i-1]+n[i+w]+n[i-w] - 4n[i]) = 20 * var_b
                    // Cov(gx_noise, gy_noise) = 0      (disjoint samples)
                    // Cov(g_noise, lap_noise) = 0      (the +-1 terms cancel)
                    // Cov(lap_noise, d_noise) = 4 * var_b   (both touch n[i])
                    let vb = f64::from(luma_variance(noise, b[i]));
                    gxx += (gx * gx - 0.5 * vb) * iv;
                    gxy += gx * gy * iv;
                    gyy += (gy * gy - 0.5 * vb) * iv;
                    gxl += gx * lap * iv;
                    gyl += gy * lap * iv;
                    gll += (lap * lap - 20.0 * vb) * iv;
                    rx += gx * d * iv;
                    ry += gy * d * iv;
                    rl += (lap * d - 4.0 * vb) * iv;
                }
            }
            // Project the defocus direction out of both the information matrix
            // and the right-hand side. This is the Schur complement of the
            // Laplacian block, and it is what makes the statistic conditional
            // on defocus rather than merely hoping defocus cancels.
            let (mut axx, mut axy, mut ayy) = (gxx, gxy, gyy);
            let (mut sx_r, mut sy_r) = (rx, ry);
            if nuisance && gll > 0.0 {
                axx -= gxl * gxl / gll;
                axy -= gxl * gyl / gll;
                ayy -= gyl * gyl / gll;
                sx_r -= gxl * rl / gll;
                sy_r -= gyl * rl / gll;
            }
            let det = axx * ayy - axy * axy;
            let tr = axx + ayy;
            let gap = (tr * tr - 4.0 * det).max(0.0).sqrt();
            let l_min = 0.5 * (tr - gap);
            if det <= 0.0 || l_min < MIN_GRADIENT_INFO {
                continue;
            }
            // `a(x) ~ b(x - s)` gives `a - b ~ -s . grad(b)`, so the solution of
            // the normal equations is the NEGATIVE of the displacement. The
            // statistic is quadratic and does not care; the reported vector
            // does.
            let sx = (ayy * sx_r - axy * sy_r) / det;
            let sy = (axx * sy_r - axy * sx_r) / det;
            out[ty * grid.cols + tx] = TileShift {
                sx: -sx as f32,
                sy: -sy as f32,
                chi2: (0.5 * (sx * sx_r + sy * sy_r)) as f32,
                sigma_px: (1.0 / l_min.sqrt()) as f32,
                informative: true,
            };
        }
    }
    out
}

fn shift_map(
    a: &[f32],
    b: &[f32],
    geom: PlaneGeometry,
    noise: &NoiseModel,
    params: Params,
    nuisance: bool,
) -> Vec<f32> {
    shift_tiles(a, b, geom, noise, params, nuisance)
        .into_iter()
        .map(|t| t.chi2)
        .collect()
}

/// Predicted variance in DN^2 of one green-luma sample at level `luma_dn`.
fn luma_variance(noise: &NoiseModel, luma_dn: f32) -> f32 {
    let s = noise.averaged_green_luma_sigma(luma_dn, 1, 0.0);
    s * s
}

/// Null standard deviation of the reduced chi-square over `n_eff` samples.
fn null_sd(n_eff: f64) -> f64 {
    if n_eff <= 0.0 {
        return f64::INFINITY;
    }
    (2.0 / n_eff).sqrt()
}

/// Per-tile threshold, in the same units as [`chi2_map`].
///
/// Each tile gets its own bar because partial edge tiles pool fewer samples and
/// therefore have a wider null. A single global threshold would make the frame
/// border fire first on every stack.
pub fn thresholds(
    geom: PlaneGeometry,
    params: Params,
    disc: Discriminator,
) -> Vec<f32> {
    let grid = TileGrid::new(geom, params.tile);
    if matches!(disc, Discriminator::Shift | Discriminator::ShiftFree) {
        // Two degrees of freedom whatever the tile pools, so the null spread is
        // 1.0 and the bar is the same everywhere. Edge tiles need no widening
        // here; they lose estimator precision, not degrees of freedom.
        return vec![1.0 + params.threshold_k; grid.len()];
    }
    let m = match disc {
        Discriminator::Raw => 1.0,
        Discriminator::LowFreq => {
            let side = 2 * params.blur_radius + 1;
            (side * side) as f64
        }
        Discriminator::Shift | Discriminator::ShiftFree => unreachable!("handled above"),
    };
    let mut out = vec![0.0f32; grid.len()];
    for ty in 0..grid.rows {
        let h = ((ty + 1) * grid.tile).min(geom.height) - ty * grid.tile;
        for tx in 0..grid.cols {
            let w = ((tx + 1) * grid.tile).min(geom.width) - tx * grid.tile;
            let n_eff = (w * h) as f64 / m;
            out[ty * grid.cols + tx] =
                (1.0 + f64::from(params.threshold_k) * null_sd(n_eff)) as f32;
        }
    }
    out
}

/// Tiles whose disagreement exceeds their own threshold.
pub fn mask(chi2: &[f32], thresholds: &[f32]) -> Vec<bool> {
    assert_eq!(chi2.len(), thresholds.len(), "chi2 and thresholds must agree");
    chi2.iter()
        .zip(thresholds)
        .map(|(c, t)| *c > *t)
        .collect()
}

/// Default minimum displacement, in plane pixels, for a tile to be called
/// motion.
///
/// **MEASURED, and it is a geometric bar rather than an intensity one.** A
/// tolerance in DN would be the waxy-blob defect; a tolerance in pixels is the
/// natural unit of the thing being detected, and it does not move when the
/// exposure, the gain or the scene brightness does.
///
/// `m97-outlier` measures, on a scene differing only in focus, an apparent
/// displacement of 0.0497 px mean and **0.1385 px worst tile** — real, because
/// blurring a curved edge moves it — against 0.9939 px mean for a planted
/// one-pixel translation. This default sits 2.5x above the worst defocus tile
/// and 2.8x below typical motion, near the geometric mean of the two.
///
/// **It is a default, not a constant of nature.** The defocus-induced shift
/// scales with the curvature of the scene and with how far apart in focus the
/// two frames are, so a bracket with finer focus steps could tolerate a smaller
/// bar and a coarser one may need a larger.
///
/// **IT HAS NOW BEEN MEASURED ON REAL FRAMES, AND THE BAR DOES NOT SAVE THE
/// ARM (M123).** This doc previously ended *"It has not yet been measured on
/// real frames"*; that is what the measurement was commissioned against. A
/// planted-translation sweep on a real `109MSDCF` defocus pair reads:
///
/// ```text
/// planted px   gated%    mean |s|
///     0.00     24.51%     0.9521
///     0.35     23.54%     1.2153
///     1.00     34.77%     1.9326
///     2.00     34.57%     3.6231
/// ```
///
/// The firing rate at **zero** planted motion is 24.51%, and planting a
/// displacement six times the bar moves it to 34.57%. **The bar separates
/// almost nothing on real data**, because real defocus already produces a mean
/// `|s|` of 0.95 px — nearly 3x this constant — before anything moves. Raising
/// the bar does not fix that; it deletes the plant along with the trap.
pub const DEFAULT_MIN_SHIFT_PX: f32 = 0.35;

/// How many times better than the magnitude bar a tile must be able to resolve
/// a displacement before its estimate is believed.
///
/// **MEASURED.** With no resolution requirement, a low-contrast static scene
/// produced spurious displacements up to 2.15 px — 6x the magnitude bar — from
/// noise alone, on tiles whose own standard error was comparable to the bar.
/// The significance gate vetoed most but not all of them: 18 tiles cleared the
/// magnitude bar, 4 cleared both. Requiring the tile to resolve the bar 3x over
/// takes that to zero without touching any other case.
///
/// This is a ratio between two quantities the module already computes, not a
/// new free parameter: it says "only ask a tile a question it can answer".
pub const RESOLUTION_MARGIN: f32 = 3.0;

/// Tiles the displacement arms reject, gated on significance, magnitude **and**
/// the tile's ability to resolve the bar it is being judged against.
///
/// The three gates guard three different failure modes and none is redundant —
/// each was added because a measurement showed the others let something
/// through:
///
/// - `chi2 > 1 + k` keeps **noise** from inventing a displacement. Measured
///   vetoing 14 of 18 noise-driven tiles on a low-contrast static scene.
/// - `|s| > min_shift_px` keeps **defocus curvature** from being read as
///   motion. Without it the mask fires on 34.4% of a stationary,
///   differently-focused scene, because a 0.027 px bias is overwhelmingly
///   significant when the noise is 4 DN and the gradients are large.
/// - `sigma_px * RESOLUTION_MARGIN <= min_shift_px` discards tiles whose
///   estimate is too imprecise to be evidence either way. This is what caught
///   the remaining 4 of those 18.
///
/// An abstaining tile — one with too little gradient to estimate anything —
/// never fires. That is deliberate: no information is not the same as
/// agreement, and a mask that treated it as agreement would be silently blind
/// exactly where it cannot see.
pub fn mask_tiles(tiles: &[TileShift], min_shift_px: f32, threshold_k: f32) -> Vec<bool> {
    let bar = 1.0 + threshold_k;
    tiles
        .iter()
        .map(|t| {
            t.informative
                && t.sigma_px.is_finite()
                && t.sigma_px * RESOLUTION_MARGIN <= min_shift_px
                && t.chi2 > bar
                && (t.sx * t.sx + t.sy * t.sy).sqrt() > min_shift_px
        })
        .collect()
}

/// Fraction of tiles the mask rejects. The placebo number: on a stack with no
/// motion this must stay near zero, or the discriminator is reading defocus.
pub fn fired_fraction(mask: &[bool]) -> f64 {
    if mask.is_empty() {
        return 0.0;
    }
    mask.iter().filter(|&&b| b).count() as f64 / mask.len() as f64
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::noise::{Levels, PlaneNoise, Provenance};

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// Read noise only, so the predicted sigma is a known constant and the
    /// calibration test does not depend on the shot term.
    fn model(sigma_dn: f32) -> NoiseModel {
        let gain = 1e-6;
        let p = PlaneNoise {
            gain_dn_per_e: gain,
            // luma sigma is sqrt(0.25 * 2 * var_plane) = sigma_plane / sqrt(2)
            read_noise_e: sigma_dn * std::f32::consts::SQRT_2 / gain,
            levels: Levels {
                black: 0.0,
                white: 16383.0,
            },
        };
        NoiseModel::new([p; 4], 100.0, Provenance::Measured)
    }

    /// SplitMix64 + Box-Muller. Deterministic, so a failure is reproducible.
    struct Rng(u64);
    impl Rng {
        fn next_u64(&mut self) -> u64 {
            self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = self.0;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            z ^ (z >> 31)
        }
        fn unit(&mut self) -> f64 {
            (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
        }
        fn normal(&mut self) -> f32 {
            let u1 = self.unit().max(1e-12);
            let u2 = self.unit();
            ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
        }
    }

    /// A scene with large-scale structure: a bright disc on a dim field. Chosen
    /// because translation must move LOW frequencies for `LowFreq` to see it,
    /// and a disc has them.
    fn disc(w: usize, h: usize, cx: f32, cy: f32, r: f32, lo: f32, hi: f32) -> Vec<f32> {
        (0..h)
            .flat_map(|y| (0..w).map(move |x| (x, y)))
            .map(|(x, y)| {
                let (dx, dy) = (x as f32 - cx, y as f32 - cy);
                if (dx * dx + dy * dy).sqrt() <= r { hi } else { lo }
            })
            .collect()
    }

    /// A scene with gradient everywhere, in both axes. The displacement arm
    /// abstains on flat tiles by design, so a test that wants every tile to
    /// carry an estimate has to give every tile something to measure.
    fn textured(w: usize, h: usize, dx: f32) -> Vec<f32> {
        let base = disc(w, h, w as f32 / 2.0 + dx, h as f32 / 2.0, 30.0, 200.0, 900.0);
        base.iter()
            .enumerate()
            .map(|(i, v)| {
                let (x, y) = ((i % w) as f32 - dx, (i / w) as f32);
                let k = std::f32::consts::TAU / 16.0;
                v + 120.0 * ((k * x).sin() + (k * y).sin())
            })
            .collect()
    }

    fn add_noise(v: &[f32], sigma: f32, seed: u64) -> Vec<f32> {
        let mut r = Rng(seed);
        v.iter().map(|s| s + sigma * r.normal()).collect()
    }

    fn blur(v: &[f32], g: PlaneGeometry, radius: usize) -> Vec<f32> {
        let mut tmp = vec![0.0; g.pixels()];
        let mut out = vec![0.0; g.pixels()];
        box_mean(v, g, radius, &mut tmp, &mut out);
        out
    }

    fn run(a: &[f32], b: &[f32], g: PlaneGeometry, p: Params, d: Discriminator) -> Vec<f32> {
        let n = model(SIGMA);
        let mut s = Scratch::new(g);
        chi2_map(a, b, g, &n, p, d, &mut s)
    }

    const SIGMA: f32 = 4.0;

    /// CALIBRATION. Two independent noisy realisations of the same scene at the
    /// same focus must read 1.0, because `Var(a-b) = var_a + var_b` exactly.
    /// If this drifts, every threshold in the module is quietly wrong.
    #[test]
    fn independent_noise_on_the_same_scene_reads_one() {
        let g = geom(128, 128);
        let scene = disc(128, 128, 64.0, 64.0, 30.0, 200.0, 900.0);
        let a = add_noise(&scene, SIGMA, 1);
        let b = add_noise(&scene, SIGMA, 2);
        let p = Params {
            tile: 32,
            blur_radius: 6,
            threshold_k: 6.0,
        };
        for d in [Discriminator::Raw, Discriminator::LowFreq] {
            let c = run(&a, &b, g, p, d);
            let mean = c.iter().sum::<f32>() / c.len() as f32;
            assert!(
                (mean - 1.0).abs() < 0.25,
                "{d:?} reduced chi-square must be ~1 on pure noise, got {mean}"
            );
        }
    }

    /// PLANT for the propagation. Dividing the predicted variance by `m` is
    /// what keeps `LowFreq` calibrated. Without it the statistic reads about
    /// `1/m` and NOTHING ever fires -- a silently inert mask that looks like a
    /// clean stack. Here the same collapse is produced deliberately, by asking
    /// `Raw` to read an already-blurred pair, so the failure is visible.
    #[test]
    fn the_low_pass_variance_must_be_propagated_or_the_statistic_collapses() {
        let g = geom(128, 128);
        let scene = disc(128, 128, 64.0, 64.0, 30.0, 200.0, 900.0);
        let a = add_noise(&scene, SIGMA, 3);
        let b = add_noise(&scene, SIGMA, 4);
        let p = Params {
            tile: 32,
            blur_radius: 6,
            threshold_k: 6.0,
        };
        let propagated = run(&a, &b, g, p, Discriminator::LowFreq);
        // Blur first, then measure with m = 1: the un-propagated arithmetic.
        let (ab, bb) = (blur(&a, g, 6), blur(&b, g, 6));
        let unpropagated = run(&ab, &bb, g, p, Discriminator::Raw);

        let mp = propagated.iter().sum::<f32>() / propagated.len() as f32;
        let mu = unpropagated.iter().sum::<f32>() / unpropagated.len() as f32;
        assert!(
            (mp - 1.0).abs() < 0.25,
            "propagated must be calibrated, got {mp}"
        );
        assert!(
            mu < 0.2,
            "un-propagated must collapse toward 1/m, got {mu} (this is the \
             silently-inert failure the propagation prevents)"
        );
        assert!(mp > mu * 4.0, "the two arms must be distinguishable");
    }

    /// MEASURED NEGATIVE RESULT. The low-pass arm was the first candidate
    /// discriminator and it does not work: on a purely defocus difference it
    /// fires on **more** tiles than the naive arm it was supposed to improve.
    ///
    /// Filtering shrinks the defocus residual, but it shrinks the noise faster,
    /// and the statistic is their ratio. This test exists so that the failure
    /// is a standing measurement rather than a remembered argument.
    #[test]
    fn low_pass_filtering_does_not_discriminate_defocus_it_amplifies_it() {
        let g = geom(128, 128);
        let scene = textured(128, 128, 0.0);
        let sharp = add_noise(&scene, SIGMA, 5);
        // Frame b is the SAME scene, merely out of focus.
        let soft = add_noise(&blur(&scene, g, 3), SIGMA, 6);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };

        let raw = run(&sharp, &soft, g, p, Discriminator::Raw);
        let lf = run(&sharp, &soft, g, p, Discriminator::LowFreq);
        let raw_fired = fired_fraction(&mask(&raw, &thresholds(g, p, Discriminator::Raw)));
        let lf_fired = fired_fraction(&mask(&lf, &thresholds(g, p, Discriminator::LowFreq)));

        assert!(
            raw_fired > 0.5,
            "the naive port must be shown failing on defocus, got {raw_fired}"
        );
        assert!(
            lf_fired >= raw_fired,
            "low-pass was expected to suppress defocus and measurably does not: \
             {lf_fired} vs {raw_fired}. If this ever inverts, the module header's \
             derivation is wrong and the arm deserves re-pricing."
        );
    }

    /// MEASURED FAILURE of the unconditional displacement arm. A stationary
    /// scene, differing only in focus, reads as motion nearly everywhere --
    /// because blurring a curved edge really does move it. This is the reason
    /// [`Discriminator::ShiftFree`] carries a nuisance parameter, recorded as a
    /// measurement so the reason cannot quietly rot into folklore.
    #[test]
    fn the_unconditional_shift_arm_is_fooled_by_curvature() {
        let g = geom(128, 128);
        let scene = textured(128, 128, 0.0);
        let sharp = add_noise(&scene, SIGMA, 11);
        let soft = add_noise(&blur(&scene, g, 3), SIGMA, 12);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };
        let sh = run(&sharp, &soft, g, p, Discriminator::Shift);
        let fired = fired_fraction(&mask(&sh, &thresholds(g, p, Discriminator::Shift)));
        assert!(
            fired > 0.5,
            "the unconditional arm is expected to be fooled by defocus and \
             measurably is not: {fired}. If this ever falls, re-price the arm."
        );
    }

    /// THE WHOLE POINT, and the arm that survives it. The same defocus
    /// difference that saturates the naive arm *and* fools the unconditional
    /// displacement arm must leave the conditional one silent. Both other arms
    /// are measured on the identical input in the same test, so this null
    /// cannot be the quiet kind: the input demonstrably contains something two
    /// other instruments do find.
    #[test]
    fn the_conditional_shift_arm_is_blind_to_defocus_that_fools_both_others() {
        let g = geom(128, 128);
        let scene = textured(128, 128, 0.0);
        let sharp = add_noise(&scene, SIGMA, 11);
        let soft = add_noise(&blur(&scene, g, 3), SIGMA, 12);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };
        let fire = |d| fired_fraction(&mask(&run(&sharp, &soft, g, p, d), &thresholds(g, p, d)));
        let raw = fire(Discriminator::Raw);
        let uncond = fire(Discriminator::Shift);
        assert!(
            raw > 0.5 && uncond > 0.5,
            "the plant must be expressible: raw {raw}, unconditional {uncond}"
        );
        let tiles = shift_tiles(&sharp, &soft, g, &model(SIGMA), p, true);
        let cond = fired_fraction(&mask_tiles(&tiles, DEFAULT_MIN_SHIFT_PX, p.threshold_k));
        assert_eq!(
            cond, 0.0,
            "defocus must not read as motion once it is fitted out and gated on \
             magnitude, against raw {raw} and unconditional {uncond}"
        );
        let worst = tiles
            .iter()
            .filter(|t| t.informative)
            .map(|t| (t.sx * t.sx + t.sy * t.sy).sqrt())
            .fold(0.0f32, f32::max);
        assert!(
            worst < DEFAULT_MIN_SHIFT_PX,
            "the worst defocus tile {worst} must sit below the {DEFAULT_MIN_SHIFT_PX} px bar"
        );
    }

    /// Both gates are load-bearing, and this plants the failure each one
    /// prevents.
    ///
    /// The magnitude gate is what stops defocus curvature (measured in the test
    /// above). The significance gate is what stops **noise** inventing a
    /// displacement: on a scene whose contrast is comparable to its noise, the
    /// estimator's standard error approaches the magnitude bar and the
    /// magnitude gate alone starts firing on a perfectly static stack. The
    /// conjunction holds where either alone does not.
    #[test]
    fn the_significance_gate_stops_noise_inventing_a_displacement() {
        let g = geom(256, 256);
        // Contrast barely above the noise: enough gradient to pass the
        // information guard, not enough to pin the displacement down.
        let k = std::f32::consts::TAU / 16.0;
        let faint: Vec<f32> = (0..256)
            .flat_map(|y| (0..256).map(move |x| (x, y)))
            .map(|(x, y)| 400.0 + 1.5 * ((k * x as f32).sin() + (k * y as f32).sin()))
            .collect();
        let a = add_noise(&faint, SIGMA, 21);
        let b = add_noise(&faint, SIGMA, 22);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };
        let tiles = shift_tiles(&a, &b, g, &model(SIGMA), p, true);
        let live: Vec<&TileShift> = tiles.iter().filter(|t| t.informative).collect();
        assert!(
            live.len() > 4,
            "the plant must reach the estimator, got {} informative tiles",
            live.len()
        );
        // Magnitude alone: noise alone pushes some tiles past the pixel bar.
        let magnitude_only = live
            .iter()
            .filter(|t| (t.sx * t.sx + t.sy * t.sy).sqrt() > DEFAULT_MIN_SHIFT_PX)
            .count();
        assert!(
            magnitude_only > 0,
            "the plant must be expressible: magnitude alone must fire on this \
             static scene, or this test proves nothing about the second gate"
        );
        // The conjunction refuses, because none of it is significant.
        let both = mask_tiles(&tiles, DEFAULT_MIN_SHIFT_PX, p.threshold_k);
        assert_eq!(
            fired_fraction(&both),
            0.0,
            "the significance and resolution gates must veto all \
             {magnitude_only} noise-driven tiles"
        );
    }

    /// PLANT for motion on the arm that ships. A translation of one pixel --
    /// far smaller than the defocus difference the previous test ignores --
    /// must fire.
    #[test]
    fn the_conditional_shift_arm_sees_a_one_pixel_translation() {
        let g = geom(128, 128);
        let a = add_noise(&textured(128, 128, 0.0), SIGMA, 13);
        let b = add_noise(&textured(128, 128, 1.0), SIGMA, 14);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };
        let sh = run(&a, &b, g, p, Discriminator::ShiftFree);
        let fired = fired_fraction(&mask(&sh, &thresholds(g, p, Discriminator::ShiftFree)));
        assert!(
            fired > 0.5,
            "a one-pixel translation must be visible to the shipping arm, got {fired}"
        );
        let tiles = shift_tiles(&a, &b, g, &model(SIGMA), p, true);
        let gated = fired_fraction(&mask_tiles(&tiles, DEFAULT_MIN_SHIFT_PX, p.threshold_k));
        assert!(
            gated > 0.5,
            "the magnitude gate must not throw away real motion, got {gated}"
        );
    }

    /// PLACEBO for the arm that ships. Same scene, same focus, only noise: the
    /// mask must be inert. A discriminator that fires here is reading defocus
    /// or is miscalibrated, and either way must not ship. The informative-tile
    /// count is asserted too, so an inert probe cannot pass as a clean null.
    #[test]
    fn the_conditional_shift_arm_is_inert_on_a_static_stack() {
        let g = geom(128, 128);
        let scene = textured(128, 128, 0.0);
        let a = add_noise(&scene, SIGMA, 15);
        let b = add_noise(&scene, SIGMA, 16);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };
        let sh = run(&a, &b, g, p, Discriminator::ShiftFree);
        let fired = fired_fraction(&mask(&sh, &thresholds(g, p, Discriminator::ShiftFree)));
        assert_eq!(fired, 0.0, "a static stack must not fire at all");
        let informative: Vec<f32> = sh.iter().copied().filter(|v| *v > 0.0).collect();
        assert!(
            informative.len() > 8,
            "the placebo must run on tiles that could have fired, got {}",
            informative.len()
        );
        let mean = informative.iter().sum::<f32>() / informative.len() as f32;
        assert!(
            mean < 3.0,
            "the null statistic has mean 1 on two degrees of freedom, got {mean}"
        );
    }

    /// PLANT for motion. A translated object must still fire under `LowFreq`,
    /// or the filter has bought its defocus-blindness by going blind entirely.
    #[test]
    fn a_translated_object_still_fires_under_low_pass() {
        let g = geom(128, 128);
        let a = add_noise(&disc(128, 128, 64.0, 64.0, 30.0, 200.0, 900.0), SIGMA, 7);
        let b = add_noise(&disc(128, 128, 72.0, 64.0, 30.0, 200.0, 900.0), SIGMA, 8);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };
        let lf = run(&a, &b, g, p, Discriminator::LowFreq);
        let fired = fired_fraction(&mask(&lf, &thresholds(g, p, Discriminator::LowFreq)));
        assert!(
            fired > 0.05,
            "an 8 px translation must be visible to the low-pass arm, got {fired}"
        );
    }

    /// PLACEBO. Same scene, same focus, only noise: the mask must be inert.
    #[test]
    fn a_static_stack_does_not_fire() {
        let g = geom(128, 128);
        let scene = disc(128, 128, 64.0, 64.0, 30.0, 200.0, 900.0);
        let a = add_noise(&scene, SIGMA, 9);
        let b = add_noise(&scene, SIGMA, 10);
        let p = Params {
            tile: 32,
            blur_radius: 12,
            threshold_k: 6.0,
        };
        let lf = run(&a, &b, g, p, Discriminator::LowFreq);
        let fired = fired_fraction(&mask(&lf, &thresholds(g, p, Discriminator::LowFreq)));
        assert_eq!(fired, 0.0, "a static stack must not fire at all");
    }

    /// The threshold must be a number of null standard deviations, so a bigger
    /// tile -- which pools more samples -- must get a TIGHTER absolute bar.
    #[test]
    fn the_threshold_tightens_as_the_tile_pools_more_samples() {
        let g = geom(128, 128);
        let small = thresholds(
            g,
            Params {
                tile: 16,
                blur_radius: 0,
                threshold_k: 6.0,
            },
            Discriminator::Raw,
        );
        let big = thresholds(
            g,
            Params {
                tile: 64,
                blur_radius: 0,
                threshold_k: 6.0,
            },
            Discriminator::Raw,
        );
        assert!(
            big[0] < small[0],
            "64px tile bar {} must be tighter than 16px bar {}",
            big[0],
            small[0]
        );
        assert!(small[0] > 1.0 && big[0] > 1.0, "both bars sit above the null mean");
    }

    /// Partial edge tiles pool fewer samples, so they must carry their own
    /// wider bar. A global threshold would make the border fire first.
    #[test]
    fn partial_edge_tiles_get_their_own_wider_threshold() {
        let g = geom(100, 100); // 100 = 3*32 + 4, so the last column is 4 wide
        let p = Params {
            tile: 32,
            blur_radius: 0,
            threshold_k: 6.0,
        };
        let t = thresholds(g, p, Discriminator::Raw);
        let grid = TileGrid::new(g, 32);
        let interior = t[0];
        let edge = t[grid.cols - 1];
        assert!(
            edge > interior,
            "edge bar {edge} must exceed interior bar {interior}"
        );
    }
}
