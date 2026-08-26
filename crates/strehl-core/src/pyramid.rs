//! Laplacian-pyramid (multi-band) merging.
//!
//! # Why this module exists
//!
//! The shipped merge is a **per-pixel selection followed by a gather**: a focus
//! measure is computed in a fixed window, one winner frame is elected per
//! pixel, the winner field is regularised, and the output pixel is taken from
//! the elected frame. That has one structural property which no amount of
//! tuning removes:
//!
//! > wherever the elected frame changes, the output has a **discontinuity at
//! > every spatial frequency at once**, including the low frequencies.
//!
//! A step in the low frequencies is exactly what a "cut-out sticker" rim is,
//! and it is what the eye finds first in a print. The subject detail can be
//! perfect and the frame is still unusable.
//!
//! A multi-band merge cannot produce that artefact, for a reason that is
//! structural rather than empirical:
//!
//! * the image is split into octave bands, and each band is merged separately;
//! * the **weights are themselves band-limited**, because they are formed from
//!   a smoothed statistic at that band's own scale and, at coarse levels, live
//!   on a grid that is 2^k times coarser than the output;
//! * so a selection error at level `k` can only inject an error whose spatial
//!   extent and amplitude are those of level `k`. A wrong choice in the finest
//!   band is a faint, high-frequency blemish. There is **no path** by which it
//!   becomes a hard low-frequency step.
//!
//! This is the most widely deployed anti-seam technique in image compositing
//! (Burt & Adelson 1983, "A multiresolution spline with application to image
//! mosaics") and it is what focus-stacking products mean by "pyramid" or
//! "PMax" methods.
//!
//! # What this module adds over a textbook pyramid stacker
//!
//! A naive pyramid stacker takes, at each coefficient, the frame with the
//! largest `|L|`. That is a maximum over `n` noisy numbers, so **in a flat
//! region it reliably selects the frame whose noise happened to be largest**.
//! The result is the blotchy, high-contrast mottle that this project has been
//! burned by before, and it is worse the deeper the stack.
//!
//! This module refuses to select on evidence the calibrated sensor noise model
//! says is not there. Every band coefficient is compared against the noise
//! floor **at that band's scale**, propagated from the same per-pixel
//! `sigma^2(S) = g*S + (RN*g)^2` relation that gates the shipped merge. Where
//! no frame's band energy clears the floor, the merge falls back to the plain
//! mean across frames — which is not a compromise but the *correct* estimator
//! when there is no information: it is the only operation that gets below
//! single-frame noise.
//!
//! # Streaming
//!
//! Real stacks here are 20-300 frames at 33 MP. Holding every frame's pyramid
//! is not an option. Every accumulator in [`BandMerge`] is a **sum**, so the
//! merge is a fold: build one frame's pyramid, accumulate, drop it. [`BandMerge::absorb`]
//! makes it a monoid, so a caller can run several accumulators over disjoint
//! frame chunks in parallel and combine them, and the result is the same
//! merge.
//!
//! This crate has no `rayon` dependency and this module is therefore
//! single-threaded by construction. Parallelism belongs to the caller, which is
//! why the chunk/absorb shape is part of the API rather than an internal
//! detail.

use std::sync::{Mutex, OnceLock};

use crate::noise::NoiseModel;

/// The 5-tap binomial generating kernel, `[1, 4, 6, 4, 1] / 16`.
///
/// Burt & Adelson's `a = 0.4` member of the generating-kernel family, which is
/// the one that is exactly binomial. It is chosen here for the usual reasons —
/// separable, non-negative (so no ringing is manufactured by the operator
/// itself), unit DC gain — plus one that matters specifically for this
/// application: it is the widest kernel whose support is still small enough
/// that a level's coefficients depend on a genuinely *local* neighbourhood, so
/// a depth boundary cannot influence a coefficient many pixels away.
pub const KERNEL: [f32; 5] = [1.0 / 16.0, 4.0 / 16.0, 6.0 / 16.0, 4.0 / 16.0, 1.0 / 16.0];

/// Dimensions of one pyramid level.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LevelSize {
    pub width: usize,
    pub height: usize,
}

impl LevelSize {
    pub const fn pixels(&self) -> usize {
        self.width * self.height
    }

    /// The size of the next coarser level. Ceiling division, so an odd
    /// dimension keeps its last sample rather than dropping it.
    pub const fn reduced(&self) -> LevelSize {
        LevelSize {
            width: self.width.div_ceil(2),
            height: self.height.div_ceil(2),
        }
    }
}

/// The size of every level of a pyramid with `bands` Laplacian levels.
///
/// Returns `bands + 1` entries: levels `0..bands` are the Laplacian bands and
/// the last is the base (coarsest Gaussian residual).
///
/// Levels stop early if a further reduction would take a dimension below
/// [`MIN_LEVEL_EXTENT`], because a 3-pixel-wide band carries no usable
/// selection signal and its border handling would dominate it.
pub fn level_sizes(width: usize, height: usize, bands: usize) -> Vec<LevelSize> {
    let mut out = vec![LevelSize { width, height }];
    for _ in 0..bands {
        let next = out[out.len() - 1].reduced();
        if next.width < MIN_LEVEL_EXTENT || next.height < MIN_LEVEL_EXTENT {
            break;
        }
        out.push(next);
    }
    out
}

/// Smallest dimension a pyramid level may have.
///
/// The 5-tap kernel reads two samples either side, so below this the level is
/// mostly border-replicated and its statistics stop meaning anything.
pub const MIN_LEVEL_EXTENT: usize = 8;

/// Default number of Laplacian bands.
///
/// Seven octaves takes a 3516 x 2344 quad plane down to a 28 x 19 base. That is
/// deliberately deep: the whole point of the exercise is that the **low**
/// frequencies must be blended rather than switched, and stopping at four or
/// five levels leaves a band at ~100 px scale still being selected, which is
/// visible as exactly the halo this is meant to remove.
pub const DEFAULT_BANDS: usize = 7;

// ---------------------------------------------------------------------------
// the two operators
// ---------------------------------------------------------------------------

/// `REDUCE`: blur with [`KERNEL`] and decimate by two.
///
/// Borders replicate. Replication is the right choice here rather than
/// reflection or zero-padding: the merge runs on registered frames whose
/// outermost pixels are already the least trustworthy, and zero-padding would
/// manufacture a huge artificial gradient all the way round the frame that the
/// selection statistic would then treat as detail.
///
/// `scratch` must hold at least `dst_size.width * src_size.height` floats.
pub fn reduce(src: &[f32], src_size: LevelSize, dst: &mut [f32], scratch: &mut [f32]) {
    let dst_size = src_size.reduced();
    assert_eq!(src.len(), src_size.pixels(), "reduce: source is not level-sized");
    assert_eq!(dst.len(), dst_size.pixels(), "reduce: destination is not level-sized");
    let (sw, sh) = (src_size.width, src_size.height);
    let (dw, dh) = (dst_size.width, dst_size.height);
    assert!(scratch.len() >= dw * sh, "reduce: scratch is too small");

    // Horizontal: sw -> dw, all sh rows.
    for y in 0..sh {
        let row = &src[y * sw..y * sw + sw];
        let out = &mut scratch[y * dw..y * dw + dw];
        for (x, o) in out.iter_mut().enumerate() {
            let c = 2 * x;
            let mut acc = 0.0f32;
            for (t, k) in KERNEL.iter().enumerate() {
                let sx = clamp_tap(c, t, sw);
                acc += k * row[sx];
            }
            *o = acc;
        }
    }
    // Vertical: sh -> dh.
    for y in 0..dh {
        let c = 2 * y;
        let out = &mut dst[y * dw..y * dw + dw];
        out.fill(0.0);
        for (t, k) in KERNEL.iter().enumerate() {
            let sy = clamp_tap(c, t, sh);
            let row = &scratch[sy * dw..sy * dw + dw];
            for (o, v) in out.iter_mut().zip(row) {
                *o += k * v;
            }
        }
    }
}

/// Index of tap `t` (of 5, centred) at centre `c`, clamped into `0..n`.
#[inline]
fn clamp_tap(c: usize, t: usize, n: usize) -> usize {
    let i = c as isize + t as isize - 2;
    i.clamp(0, n as isize - 1) as usize
}

/// `EXPAND`: upsample by two and interpolate with [`KERNEL`].
///
/// Implemented as an explicit two-phase filter rather than "insert zeros,
/// convolve, multiply by four", because that form makes the two properties this
/// merge depends on checkable by inspection:
///
/// * the **even** phase is `[1, 6, 1] / 8` and the **odd** phase is
///   `[1, 1] / 2`. Both sum to one, so a constant expands to itself exactly and
///   no DC step can be introduced by the operator.
/// * both phases reproduce a linear ramp exactly, so the operator adds no
///   curvature of its own to a smooth region.
///
/// `dst_size` must be either `2 * src` or `2 * src - 1` per axis — i.e. it must
/// be a size whose [`LevelSize::reduced`] is `src_size`.
///
/// `scratch` must hold at least `dst_size.width * src_size.height` floats.
pub fn expand(
    src: &[f32],
    src_size: LevelSize,
    dst: &mut [f32],
    dst_size: LevelSize,
    scratch: &mut [f32],
) {
    assert_eq!(src.len(), src_size.pixels(), "expand: source is not level-sized");
    assert_eq!(dst.len(), dst_size.pixels(), "expand: destination is not level-sized");
    assert_eq!(
        dst_size.reduced(),
        src_size,
        "expand: destination does not reduce to the source size"
    );
    let (sw, sh) = (src_size.width, src_size.height);
    let (dw, dh) = (dst_size.width, dst_size.height);
    assert!(scratch.len() >= dw * sh, "expand: scratch is too small");

    for y in 0..sh {
        let row = &src[y * sw..y * sw + sw];
        let out = &mut scratch[y * dw..y * dw + dw];
        for (x, o) in out.iter_mut().enumerate() {
            *o = expand_tap(row, sw, x);
        }
    }
    for y in 0..dh {
        let out = &mut dst[y * dw..y * dw + dw];
        if y % 2 == 0 {
            let c = y / 2;
            let a = &scratch[clamp_idx(c as isize - 1, sh) * dw..][..dw];
            let b = &scratch[c * dw..][..dw];
            let d = &scratch[clamp_idx(c as isize + 1, sh) * dw..][..dw];
            for (i, o) in out.iter_mut().enumerate() {
                *o = 0.125 * a[i] + 0.75 * b[i] + 0.125 * d[i];
            }
        } else {
            let c = y / 2;
            let a = &scratch[c * dw..][..dw];
            let b = &scratch[clamp_idx(c as isize + 1, sh) * dw..][..dw];
            for (i, o) in out.iter_mut().enumerate() {
                *o = 0.5 * (a[i] + b[i]);
            }
        }
    }
}

#[inline]
fn clamp_idx(i: isize, n: usize) -> usize {
    i.clamp(0, n as isize - 1) as usize
}

#[inline]
fn expand_tap(row: &[f32], n: usize, x: usize) -> f32 {
    let c = x / 2;
    if x % 2 == 0 {
        0.125 * row[clamp_idx(c as isize - 1, n)] + 0.75 * row[c] + 0.125 * row[clamp_idx(c as isize + 1, n)]
    } else {
        0.5 * (row[c] + row[clamp_idx(c as isize + 1, n)])
    }
}

// ---------------------------------------------------------------------------
// pyramids
// ---------------------------------------------------------------------------

/// A Laplacian pyramid: `bands` difference levels plus a base residual.
///
/// `data[k]` is level `k`; the last entry is the base. [`Pyramid::collapse`]
/// inverts the decomposition exactly (to float rounding).
#[derive(Debug, Clone)]
pub struct Pyramid {
    sizes: Vec<LevelSize>,
    data: Vec<Vec<f32>>,
}

impl Pyramid {
    /// An all-zero pyramid with the given level sizes.
    pub fn zeros(sizes: &[LevelSize]) -> Self {
        Self {
            sizes: sizes.to_vec(),
            data: sizes.iter().map(|s| vec![0.0; s.pixels()]).collect(),
        }
    }

    pub fn sizes(&self) -> &[LevelSize] {
        &self.sizes
    }

    /// Number of levels, Laplacian bands **plus** the base.
    pub fn levels(&self) -> usize {
        self.sizes.len()
    }

    /// Number of Laplacian bands, i.e. every level except the base.
    pub fn bands(&self) -> usize {
        self.sizes.len() - 1
    }

    pub fn level(&self, k: usize) -> &[f32] {
        &self.data[k]
    }

    pub fn level_mut(&mut self, k: usize) -> &mut [f32] {
        &mut self.data[k]
    }

    /// Total float count across every level. `~4/3` of the base image.
    pub fn floats(&self) -> usize {
        self.sizes.iter().map(LevelSize::pixels).sum()
    }

    /// Decompose `src` into this pyramid, reusing its allocation.
    pub fn build(&mut self, src: &[f32], ws: &mut Workspace) {
        assert_eq!(src.len(), self.sizes[0].pixels(), "pyramid: source is not level-0 sized");
        let n = self.levels();
        // Gaussian levels first, into the pyramid's own storage.
        self.data[0].copy_from_slice(src);
        for k in 1..n {
            let (lo, hi) = self.data.split_at_mut(k);
            reduce(&lo[k - 1], self.sizes[k - 1], &mut hi[0], &mut ws.scratch);
        }
        // Then the differences, **fine to coarse**, so that when level `k` is
        // differenced its source `k+1` is still a Gaussian. Running this the
        // other way round expands an already-differenced level and silently
        // produces a pyramid that does not reconstruct.
        for k in 0..n - 1 {
            let px = self.sizes[k].pixels();
            expand(
                &self.data[k + 1],
                self.sizes[k + 1],
                &mut ws.expanded[..px],
                self.sizes[k],
                &mut ws.scratch,
            );
            for (d, e) in self.data[k].iter_mut().zip(&ws.expanded[..px]) {
                *d -= e;
            }
        }
    }

    /// Rebuild the level-0 image from the bands and the base.
    pub fn collapse(&self, ws: &mut Workspace) -> Vec<f32> {
        let n = self.levels();
        let mut acc = self.data[n - 1].clone();
        for k in (0..n - 1).rev() {
            let px = self.sizes[k].pixels();
            expand(
                &acc,
                self.sizes[k + 1],
                &mut ws.expanded[..px],
                self.sizes[k],
                &mut ws.scratch,
            );
            acc = ws.expanded[..px].to_vec();
            for (a, l) in acc.iter_mut().zip(&self.data[k]) {
                *a += l;
            }
        }
        acc
    }

    /// Build the **Gaussian** pyramid of `src` in place — every level holds a
    /// blurred, decimated copy rather than a difference.
    ///
    /// Used for fields that are not images and must not be differenced: the
    /// per-pixel noise variance, and any weight field a caller wants carried to
    /// coarser grids.
    pub fn build_gaussian(&mut self, src: &[f32], ws: &mut Workspace) {
        assert_eq!(src.len(), self.sizes[0].pixels(), "pyramid: source is not level-0 sized");
        self.data[0].copy_from_slice(src);
        for k in 1..self.levels() {
            let (lo, hi) = self.data.split_at_mut(k);
            reduce(&lo[k - 1], self.sizes[k - 1], &mut hi[0], &mut ws.scratch);
        }
    }
}

/// Reusable scratch for the pyramid operators, so a per-frame fold allocates
/// once rather than 300 times.
#[derive(Debug, Clone)]
pub struct Workspace {
    scratch: Vec<f32>,
    expanded: Vec<f32>,
}

impl Workspace {
    pub fn new(sizes: &[LevelSize]) -> Self {
        let n = sizes[0].pixels();
        Self {
            scratch: vec![0.0; n + sizes[0].width],
            expanded: vec![0.0; n],
        }
    }
}

// ---------------------------------------------------------------------------
// the band noise floor
// ---------------------------------------------------------------------------

/// How much of a white-noise input's variance survives into each Laplacian
/// band, MEASURED on the operators in this module rather than assumed.
///
/// # Why this is measured and not derived
///
/// The tempting derivation is "the kernel's squared weights sum to `70/256`, so
/// each reduction cuts the variance by `0.0748` per axis". That is right for
/// the *first* reduction and wrong for every one after it, because after one
/// blur the samples are no longer independent and the second reduction removes
/// much less than the formula claims. Compounding a wrong factor over seven
/// octaves is how a noise floor ends up an order of magnitude too low, at which
/// point the gate stops gating and the merge is a naive argmax again — the
/// exact failure this module exists to avoid.
///
/// So `beta[k] = E[L_k^2] / sigma_0^2` is obtained by pushing a deterministic
/// unit-variance white field through the real [`Pyramid::build`] and reading
/// the answer off. It is a property of the operators, so it is the same for
/// every stack and every camera; only the per-pixel `sigma_0^2` it multiplies
/// is scene dependent.
#[derive(Debug, Clone)]
pub struct BandGain {
    beta: Vec<f32>,
}

impl BandGain {
    /// Measure the per-band variance gain for a pyramid of the given depth.
    ///
    /// Deterministic: the probe fields come from fixed-seed LCGs, so two runs
    /// of the same binary produce the same floor and a render is reproducible.
    /// Memoised per band count, so the cost is paid once per process however
    /// many workers ask for it.
    pub fn measure(bands: usize) -> Self {
        static CACHE: OnceLock<Mutex<Vec<(usize, BandGain)>>> = OnceLock::new();
        let cache = CACHE.get_or_init(|| Mutex::new(Vec::new()));
        if let Ok(c) = cache.lock() {
            if let Some((_, g)) = c.iter().find(|(b, _)| *b == bands) {
                return g.clone();
            }
        }
        let g = Self::measure_uncached(bands);
        if let Ok(mut c) = cache.lock() {
            c.push((bands, g.clone()));
        }
        g
    }

    fn measure_uncached(bands: usize) -> Self {
        // The probe must be big enough that it actually *reaches* the requested
        // depth: `level_sizes` truncates below `MIN_LEVEL_EXTENT`, so a probe
        // that bottoms out early returns a short `beta` and the merge indexes
        // off the end of it. Size the probe from the depth, do not assume a
        // fixed 256.
        let n = (MIN_LEVEL_EXTENT << bands.min(12)).max(256);
        let sizes = level_sizes(n, n, bands);
        debug_assert_eq!(sizes.len(), bands + 1, "the probe is too small for {bands} bands");
        let mut ws = Workspace::new(&sizes);
        let mut pyr = Pyramid::zeros(&sizes);

        // The coarsest level of a single probe has only a handful of interior
        // samples -- at `bands` deep it is `MIN_LEVEL_EXTENT` across, so ~16 of
        // them, and an `E[X^2]` estimate from 16 samples carries a ~35%
        // standard error. That is far too loose for something the gate
        // multiplies. Pool independent realisations instead of growing the
        // probe: pooling costs the same arithmetic but keeps only one field
        // resident, where a probe wide enough to give the coarsest level 512
        // samples would be 32x the memory.
        const REALISATIONS: usize = 32;
        let mut acc = vec![0.0f64; sizes.len()];
        let mut counts = vec![0usize; sizes.len()];
        for r in 0..REALISATIONS {
            let mut state: u64 = 0x2545_F491_4F6C_DD1D ^ (r as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15);
            let mut field: Vec<f32> = (0..n * n)
                .map(|_| {
                    // The band gain of a linear operator depends on the input's
                    // variance and its whiteness, not on its distribution, so a
                    // uniform field is as good as a Gaussian one here.
                    state = state
                        .wrapping_mul(6364136223846793005)
                        .wrapping_add(1442695040888963407);
                    ((state >> 33) as f32) / ((1u64 << 31) as f32) - 1.0
                })
                .collect();
            // Centred and normalised to exactly unit sample variance, so the
            // ratio below is not itself a noisy estimate of the input variance.
            let mean = field.iter().sum::<f32>() / field.len() as f32;
            for v in field.iter_mut() {
                *v -= mean;
            }
            let var = field.iter().map(|v| v * v).sum::<f32>() / field.len() as f32;
            let s = var.sqrt().recip();
            for v in field.iter_mut() {
                *v *= s;
            }

            pyr.build(&field, &mut ws);
            for (k, sz) in sizes.iter().enumerate() {
                // Interior only. The replicated border is correlated with
                // itself and would bias the estimate downward.
                let m = 4usize.min(sz.width / 4).min(sz.height / 4);
                let lv = pyr.level(k);
                for y in m..sz.height.saturating_sub(m) {
                    for x in m..sz.width.saturating_sub(m) {
                        let v = f64::from(lv[y * sz.width + x]);
                        acc[k] += v * v;
                        counts[k] += 1;
                    }
                }
            }
        }
        let beta = (0..sizes.len())
            .map(|k| {
                if counts[k] == 0 {
                    1.0
                } else {
                    (acc[k] / counts[k] as f64) as f32
                }
            })
            .collect();
        Self { beta }
    }

    /// `E[L_k^2] / sigma_0^2` for band `k`.
    pub fn beta(&self, k: usize) -> f32 {
        self.beta[k]
    }

    pub fn all(&self) -> &[f32] {
        &self.beta
    }
}

/// The per-pixel green-luma **variance** of one frame, in DN^2, from the
/// calibrated noise model.
///
/// This is the level-0 input to the band noise floor. It is a variance and not
/// a sigma on purpose: variances are what add, and what the pyramid's linear
/// operators act on.
pub fn luma_variance(luma: &[f32], noise: &NoiseModel, dst: &mut [f32]) {
    assert_eq!(luma.len(), dst.len());
    for (d, l) in dst.iter_mut().zip(luma) {
        let s = noise.green_luma_sigma(*l);
        *d = s * s;
    }
}

// ---------------------------------------------------------------------------
// the merge
// ---------------------------------------------------------------------------

/// How a band coefficient is chosen across frames.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SelectMode {
    /// Weighted mean, weight `= excess_band_power^exponent`.
    ///
    /// **This is the default and it should stay the default.** Two independent
    /// reasons:
    ///
    /// 1. *Sign coherence comes free.* The classic failure of coefficient-wise
    ///    argmax-of-magnitude is that adjacent coefficients get taken from
    ///    frames whose detail has opposite sign, which is ringing. A weighted
    ///    mean cannot do that: it is a convex combination, so its output is
    ///    bounded by the inputs and neighbouring outputs move continuously.
    /// 2. *It degrades to averaging.* Where several frames are genuinely
    ///    indistinguishable the weights are equal and the merge averages them,
    ///    which is the only operation that gets below single-frame noise. A
    ///    hard maximum inherits one frame's noise everywhere, and because the
    ///    pick is made using that same frame's noise the two are correlated and
    ///    the noise is *amplified* rather than merely retained.
    SoftPower,
    /// Take the coefficient of the frame with the largest excess band power.
    ///
    /// Present as a **control arm**, not as an option to ship. This is the
    /// textbook "PMax" rule, and having it reachable is what makes the claim
    /// that the soft rule is better a measurement rather than an assertion.
    HardMax,
}

/// How the coarsest residual — the band that carries overall tone — is merged.
///
/// This was the one design decision here taken on argument rather than
/// measurement, and the argument lost. Measured on `flower-bud-alone-cpl`
/// (205 frames, linear camera-native, differenced against a `STREHL_ONLY_FRAME`
/// render of the alignment reference, which performs no election at all):
///
/// | base band            | far-field offset | spatial structure, subject-free quadrant |
/// |----------------------|------------------|------------------------------------------|
/// | `WeightedFromCoarsest` | −475.0 DN      | 835.0 DN                                 |
/// | `Mean`                 | **+11.0 DN**   | **45.0 DN**                              |
/// | shipped selection merge (for scale) | +9.3 DN | 29.7 DN                     |
///
/// Both blend arms removed the shipped merge's broad aura equally well, so the
/// base band is not what buys that. What it decides is whether the frame's
/// overall level is allowed to drift, and weighting it let the level follow
/// whichever frames won locally — a −2.5% global error with a further ~4% of
/// position-dependent structure on top. `Mean` cannot do that, because it does
/// not depend on position at all.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BaseBand {
    /// Plain mean across frames. The conservative choice: it cannot introduce a
    /// low-frequency discontinuity of any kind, because it does not depend on
    /// position at all.
    ///
    /// The default, on the measurement above.
    Mean,
    /// Weighted by the coarsest Laplacian band's weight, reduced once onto the
    /// base grid.
    ///
    /// The argument for this was that the base grid is 2^bands coarser than the
    /// output, so even a hard mask on it is, after the collapse, a transition
    /// spread over ~2^bands output pixels — smooth by construction — and that
    /// what it buys is local tone: at a depth boundary the in-focus frame's low
    /// frequencies win locally instead of being averaged with every defocused
    /// frame's veil.
    ///
    /// The first half of that is true and the second half is the problem. The
    /// weights are a function of position, so the merged level is too, and on a
    /// featureless backdrop — where there is no focus signal to justify any
    /// particular weighting — that shows up as the level wandering. Kept as a
    /// control arm, because a default chosen by measurement needs the arm it
    /// beat to remain reachable.
    WeightedFromCoarsest,
}

/// Number of coarsest **Laplacian** bands merged as a plain mean across frames
/// rather than by selection. The base residual is not counted here; it has its
/// own control in [`BaseBand`].
///
/// # Why this exists, and why it is not the base band
///
/// ORCH measured a broad shallow depression in the background around the
/// subject -- deeper than the control from `d ~ 175 px` out to `d ~ 550 px`,
/// about 1.2% of level, never converging inside the frame -- and identified it
/// as the Burt-Adelson coarse-level halo: blending at a level whose support is
/// hundreds of pixels wide smears subject luminance into the surrounding
/// background over exactly that support.
///
/// **The mechanism is right and the prescribed address was not.** The fix
/// proposed was to take the base band from the mean instead of the blend.
/// [`BaseBand::Mean`] is already the default, and it already routes every base
/// coefficient through the unweighted fallback, so the base band is a plain
/// mean across frames today. The `BaseBand` table records the measurement that
/// settles it: *both* base arms removed the broad aura equally well, so the
/// base band is not what carries it.
///
/// The level that does carry it is the coarsest few **Laplacian** bands. On a
/// 7040 px frame with 7 bands, level 6 sits on a 110 px grid, so one coefficient
/// spans 64 output pixels and the 5x5 binomial kernel that forms it reaches
/// about 320 output pixels. That is the measured scale of the bowl. Those bands
/// are still *selected* -- [`MergeConfig::exponent_at`] gives the coarsest band
/// `exponent` itself, 2.0 by default, which is gentler than the fine bands but
/// is not an average.
///
/// So this applies the principle at the level that shows the defect: at low
/// spatial frequencies there is nothing for selection to add, because defocus is
/// a low-pass and leaves the low frequencies of every frame near MTF 1.0. There
/// is only position-dependent bias to introduce, which is what a bowl is.
///
/// Implemented with the same mechanism [`BaseBand::Mean`] uses -- zero the
/// weight field for those bands, which routes every coefficient through the
/// unweighted fallback in [`BandMerge::finish_level`]. It is therefore exactly a
/// mean, not a very soft selection.
///
/// `0` restores the previous behaviour bit-for-bit.
pub const DEFAULT_MEAN_COARSE: usize = 0;

/// Environment override for [`DEFAULT_MEAN_COARSE`].
///
/// Exists so the ladder that chooses this value can be run without one build
/// per rung. Read once per process.
///
/// **A malformed value panics rather than falling back.** A sweep that silently
/// rendered every rung at the default would look like a flat curve and would
/// refute the very effect it was built to measure -- the same reasoning as
/// [`crate::focus::WINDOW_RADIUS_ENV`].
pub const MEAN_COARSE_ENV: &str = "STREHL_PYRAMID_MEAN_COARSE";

/// The number of coarsest Laplacian bands averaged, honouring
/// [`MEAN_COARSE_ENV`].
#[must_use]
pub fn mean_coarse_default() -> usize {
    static CACHED: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *CACHED.get_or_init(|| match std::env::var(MEAN_COARSE_ENV) {
        Err(_) => DEFAULT_MEAN_COARSE,
        Ok(raw) => {
            let n: usize = raw.trim().parse().unwrap_or_else(|_| {
                panic!("{MEAN_COARSE_ENV}={raw:?} is not a non-negative integer")
            });
            assert!(
                n <= 16,
                "{MEAN_COARSE_ENV}={n} is outside the supported range 0..=16"
            );
            n
        }
    })
}

/// Whether the reconstruction is confined to the range of values the input
/// frames actually support at each pixel.
///
/// # The safety property this exists to restore
///
/// This module's selection is a convex combination *within a band*, and that
/// was stated in the preflight log every run as though it protected the
/// output. It does not, and the gap is structural: **each band computes its own
/// weight field**. Band 0 may be dominated by frame 12 while band 5 is
/// dominated by frame 80, and a sum of convex combinations taken under
/// *different* weightings is not a convex combination of the original pixels.
/// Per-band convexity is true and does not imply reconstruction convexity.
///
/// ORCH established this by construction rather than by reading the code — a
/// 1-D pyramid over 8 frames each sharp in a different region, scored against
/// the per-pixel hull `[min_k, max_k]`:
///
/// | case | violating | worst excursion |
/// |---|---:|---:|
/// | control: one weighting shared by every band | 0 / 102,400 | 0.000 |
/// | measured: independent per-band weights | 7 / 102,400 | 0.140 × span |
///
/// The rate is driven by the selection exponent, not the gate: 0 violations at
/// exponent ≤ 1, 72 at exponent 8, 511 at 16. The shipped per-band ramp is
/// `2 3 4 5 8 8 8`, so **the three finest bands sit exactly where this turns
/// severe**.
///
/// In a real render the excursion is downward into darkness, where the hull
/// sits near zero and crossing it clips: on `flower-bud-alone-cpl` the
/// unclamped merge emitted **122,416 exact-zero pixels (0.371%)** in a region
/// the shipped merge renders at median 3117 DN, blue leading red 3.7×, because
/// blue carries the least signal and so its hull is nearest zero.
///
/// # Why clamping cannot cost anything real
///
/// The argument is not aesthetic. A merge that claims to combine N observations
/// has no basis for emitting a value none of them support, so anything outside
/// `[min_k, max_k]` is unsupported by the data *by definition* and the clamp
/// can only remove excursions that were never justified. It degrades gracefully
/// in both directions: where the frames agree the hull is tight and the clamp
/// binds constantly while changing nothing, and where they disagree it is loose
/// and never binds.
///
/// It also cannot introduce a seam of its own, which matters in a module whose
/// entire purpose is not printing hard boundaries. `min(max(x, lo), hi)` is
/// continuous in all three arguments and `lo`/`hi` are themselves order
/// statistics of smooth images, so the clamped result is continuous — it agrees
/// with the reconstruction where it does not bind, and the two are equal at the
/// crossing. The clamp costs a gradient discontinuity, never a step.
///
/// The alternative fix — lowering the exponent until the violations stop —
/// trades a localised artifact for a diffuse one, because loss is monotone in
/// selectivity. That is the wrong trade and this is not it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hull {
    /// Clamp each output pixel to `[min_k, max_k]` over the aligned input
    /// frames at that pixel. The default.
    InputRange,
    /// [`InputRange`](Self::InputRange), plus the same bound applied to the
    /// **partial reconstruction at every pyramid level** during collapse.
    ///
    /// # Why bounding only the final sum is not enough
    ///
    /// Collapse runs coarse to fine, and at each step
    ///
    /// ```text
    ///   acc_k     = expand(acc_k+1)     + merged_Lap_k
    ///   Gauss_f,k = expand(Gauss_f,k+1) + Lap_f,k        for a single frame f
    /// ```
    ///
    /// [`SelectMode::SoftPower`] makes `merged_Lap_k` a convex combination
    /// *within* band `k`, so it lies inside the frames' Laplacian hull there.
    /// Bounding the band itself is therefore a no-op — the coefficient is
    /// already inside. The leak is in the **sum**: because
    /// `min(a + b) >= min a + min b`, the admissible range of `acc_k` is
    /// strictly wider than `[min_f Gauss_f,k, max_f Gauss_f,k]`, and that slack
    /// compounds through every remaining expand. Clamping once at level 0 lets
    /// the excursion born at the coarsest level ride all the way down.
    ///
    /// # Why this is aimed at the coarse end
    ///
    /// Measured, not assumed. A 2x2 factorial separating the two things a band
    /// count change does at once (see `docs/research/BUILD-BLEND.md` s18)
    /// attributes the excursion to the newly *selected* coarsest band, not to
    /// the exponent ramp that shifts with it: the new band alone explains 56%
    /// of the effect and the ramp alone 3%. Independently, a risk map binned on
    /// control-arm luminance and gradient finds the clipped population is dark
    /// and **flat**, not dark and edgy — risk falls 5.5x as gradient rises. Both
    /// point at broad, low-frequency, flat-region excursion, which is what a
    /// coarse-band inconsistency produces and what this bounds.
    ///
    /// Bounding every level rather than only the coarse ones is the cheaper
    /// choice to justify: at fine levels the bound is nearly inactive precisely
    /// because little slack has accumulated yet, so it costs almost nothing to
    /// include them and removes a free parameter that would otherwise have to be
    /// tuned.
    ///
    /// # What it does not do
    ///
    /// It does not touch selection. The exponent ramp, the band count and
    /// `sharpen_per_octave` are all unchanged, which matters because every one
    /// of those is a way to make the excursion disappear by turning the stacker
    /// off: `--sharpen 0` scores a perfect zero clip count and renders the
    /// subject as a featureless grey smudge. A bound is not a softener.
    PerLevel,
    /// Emit the reconstruction as-is.
    ///
    /// Kept reachable because a fix whose defect can no longer be reproduced
    /// cannot be measured interventionally, and because the excursion is the
    /// only direct evidence that the clamp is doing anything.
    Unclamped,
}

impl Hull {
    /// Whether this mode maintains the level-0 hull of the input frames.
    ///
    /// Both clamping modes need it: [`Hull::PerLevel`] is a strict tightening
    /// of [`Hull::InputRange`] and still applies the level-0 bound, so every
    /// site that asks "am I accumulating a hull?" must accept both. Writing it
    /// as a method rather than repeating `== InputRange || == PerLevel` at each
    /// site exists because that comparison is load-bearing in five places and a
    /// missed one would silently leave a hull unaccumulated, which reads as a
    /// merge that simply has no clamp.
    #[must_use]
    pub fn bounds(self) -> bool {
        matches!(self, Hull::InputRange | Hull::PerLevel)
    }

    /// Whether the partial reconstruction is bounded at every pyramid level.
    #[must_use]
    pub fn bounds_each_level(self) -> bool {
        matches!(self, Hull::PerLevel)
    }
}

/// Everything the multi-band merge is parameterised by.
#[derive(Debug, Clone, Copy)]
pub struct MergeConfig {
    /// Number of Laplacian bands. See [`DEFAULT_BANDS`].
    pub bands: usize,
    /// How many multiples of the modelled band-noise power a coefficient's
    /// local energy must exceed before it is allowed to influence the
    /// selection.
    ///
    /// The energy statistic is a smoothed mean of ~13 squared samples, so under
    /// pure noise it fluctuates by about 39% of its mean. `2.0` therefore sits
    /// roughly 2.6 of its own standard deviations above the noise expectation:
    /// high enough that noise essentially never wins a selection, low enough
    /// that real low-contrast detail is not thrown away.
    pub gate: f32,
    /// Exponent on the noise-corrected band power, at the COARSEST band.
    ///
    /// `1.0` is a Wiener-like weighting and blends generously; `2.0` is sharply
    /// selective while remaining a convex combination. The trade is real: with
    /// a 300-frame stack, twenty defocused frames each carrying 5% of the
    /// in-focus frame's band power contribute 45% of the weight at exponent 1
    /// and 3% at exponent 2. Defocus is a low-pass, so that contamination is
    /// *blur*, and 45% of it is visible. Hence the default of 2.
    ///
    /// See [`exponent_at`](MergeConfig::exponent_at): this is the floor of a
    /// ramp, not a single global value.
    pub exponent: f32,
    /// How much sharper the selection is at the finest band than at the
    /// coarsest, in multiplicative steps per octave.
    ///
    /// # Why the sharpness must depend on scale
    ///
    /// The whole argument for a multi-band merge is that **a selection error at
    /// a fine scale injects only a small-amplitude, high-frequency error, while
    /// a selection error at a coarse scale is a visible step**. That is an
    /// asymmetry, and a single global exponent throws it away by treating every
    /// band with the same caution.
    ///
    /// Read it in each direction:
    ///
    /// * **Fine bands: be aggressive.** Acuity lives here, and it is precisely
    ///   here that being wrong is cheap. Blending a fine band across frames is
    ///   a low-pass of the sharpest information in the stack -- it is exactly
    ///   the softness that a conservative merge is criticised for. Near-argmax
    ///   costs nothing a viewer can see and buys all the acuity.
    /// * **Coarse bands: be gentle.** A hard mask edge in a coarse band, once
    ///   expanded through the collapse, is a step spanning many output pixels
    ///   at the low frequencies the eye is most sensitive to. That is what a
    ///   "cut-out sticker" rim *is*, and it is the defect this module exists to
    ///   remove. Softness here costs nothing: the low frequencies of a scene
    ///   barely differ between adjacent focus slices anyway.
    ///
    /// `1.0` disables the ramp and restores a single global exponent.
    pub sharpen_per_octave: f32,
    pub select: SelectMode,
    pub base: BaseBand,
    /// See [`DEFAULT_MEAN_COARSE`]. Number of coarsest Laplacian bands merged
    /// as a plain mean instead of by selection. The base residual is separate.
    pub mean_coarse: usize,
    /// See [`Hull`]. Confines the reconstruction to what the inputs support.
    pub hull: Hull,
    /// Margin on the per-level hull, in units of the calibrated noise sigma at
    /// that level. Only meaningful under [`Hull::PerLevel`].
    ///
    /// # Why a margin is required rather than optional
    ///
    /// Measured. A hard per-level projection (`hull_lambda = 0`) removes the
    /// excursion but costs 4.7% of edge acuity and 8.3% of fine-band energy on
    /// `dry-erase-marker-head-cpl` -- it confiscates genuine resolution along
    /// with the artifact. That is the trade this project exists to refuse: the
    /// merge is *supposed* to be able to beat any single frame, and a bound that
    /// forbids it from leaving the frames' range at a coarse scale forbids the
    /// deconvolution gain that makes stacking worth doing.
    ///
    /// # Why noise sets it, and not taste
    ///
    /// The excursion distribution is bimodal: the bulk sits near 1 sigma, which
    /// is indistinguishable from recovered detail, and the destructive tail runs
    /// 20-200 sigma. A threshold in sigma therefore separates the two
    /// populations on their own scale, adapting to exposure, ISO and the local
    /// signal level without a hand-tuned DN anywhere. An absolute epsilon would
    /// have to be re-chosen per capture and would be wrong for both tails.
    pub hull_lambda: f32,
}

impl MergeConfig {
    /// The selection exponent for band `k`, `k = 0` finest.
    ///
    /// A geometric ramp: `exponent * sharpen_per_octave^(bands - 1 - k)`, so
    /// the coarsest Laplacian band gets exactly `exponent` and each octave finer
    /// is `sharpen_per_octave` times more selective. Geometric rather than
    /// linear because band power itself falls geometrically with scale, so a
    /// fixed *ratio* per octave is the scale-free choice and the only one that
    /// does not privilege whatever band count happens to be configured.
    pub fn exponent_at(&self, k: usize, bands: usize) -> f32 {
        if self.sharpen_per_octave == 1.0 || bands == 0 {
            return self.exponent;
        }
        let steps = (bands.saturating_sub(1)).saturating_sub(k.min(bands.saturating_sub(1)));
        // Capped so a deep pyramid plus an aggressive ramp cannot produce an
        // exponent that overflows `powf` or makes the weights denormal.
        (self.exponent * self.sharpen_per_octave.powi(steps as i32)).min(MAX_EXPONENT)
    }
}

/// Ceiling on the per-band selection exponent.
///
/// Set by what `f32` can actually represent, not by taste. The weight spans
/// `(snr/SNR_REF)^p`, and a real stack contains coefficients from around the
/// noise floor up to `snr ~ 1e5` on a bright, sharp edge — a log range of about
/// 7.4 either side of the reference. The overflow-safe bound on `p * ln(r)` is
/// 80, so `p` above about 10 can no longer rank the sharpest coefficients
/// against each other: they all pin to the ceiling and get averaged.
///
/// `8` leaves real headroom and is already close to winner-take-all — a frame
/// with twice another's band energy gets 256 times the weight. If more
/// selectivity than this is ever wanted, the right answer is
/// [`SelectMode::HardMax`], which is exact and cannot overflow, not a larger
/// exponent.
pub const MAX_EXPONENT: f32 = 8.0;

impl Default for MergeConfig {
    fn default() -> Self {
        Self {
            bands: DEFAULT_BANDS,
            gate: 2.0,
            exponent: 2.0,
            // 1.4x per octave. Over a 7-band pyramid this runs 2, 3, 4, 5, 8,
            // 8, 8 from coarsest to finest, so the fine bands -- where all the
            // acuity is, and where a wrong pick is a single high-frequency
            // coefficient nobody can see -- are near winner-take-all, while the
            // coarse bands, where a wrong pick is the rim, stay gently blended.
            //
            // Chosen by sweeping 1.0 / 1.4 / 2.0 on an 80-frame subsample of
            // `couch-fibers-cpl` (acuity) and `flower-bud-with-background-fern`
            // (rim) and looking at the frames. 1.4 and 2.0 were
            // indistinguishable on both; 1.0 was visibly softer than either on
            // couch-fibers. The gentler of two equals wins, because the risk
            // being traded against sits in the coarse bands.
            sharpen_per_octave: 1.4,
            select: SelectMode::SoftPower,
            // Measured, not argued -- see `BaseBand`. Weighting the base band
            // cost -475 DN of global level and 835 DN of position-dependent
            // structure on flower-bud-alone-cpl, against +11 DN and 45 DN for
            // the mean, with no difference in aura removal between them.
            base: BaseBand::Mean,
            // See `DEFAULT_MEAN_COARSE`. 0 until the ladder that chooses it has
            // been run, so this field cannot move a byte until it is measured.
            mean_coarse: mean_coarse_default(),
            // A merge has no basis for emitting a value none of its inputs
            // support. Per-band convexity does not imply reconstruction
            // convexity -- see `Hull`.
            hull: Hull::InputRange,
            // See `MergeConfig::hull_lambda`. Chosen by the ladder in
            // `docs/research/BUILD-BLEND.md`; inert unless `hull` is `PerLevel`.
            hull_lambda: 2.0,
        }
    }
}

/// A streaming multi-band merge over any number of frames and colour planes.
///
/// Every field is a sum over frames, which is what makes this a fold and makes
/// [`absorb`](Self::absorb) exact.
#[derive(Debug, Clone)]
pub struct BandMerge {
    cfg: MergeConfig,
    sizes: Vec<LevelSize>,
    planes: usize,
    /// `sum(w * L)`, indexed `[level * planes + plane]`.
    num: Vec<Vec<f32>>,
    /// `sum(L)`, same indexing. The fallback numerator where no frame cleared
    /// the noise floor.
    usum: Vec<Vec<f32>>,
    /// `sum(w)`, per level. Shared by every plane, because the selection is
    /// made on green luma only — the same rule the shipped election uses, and
    /// for the same reason: letting a colour plane's own noise drive the
    /// decision is how chroma noise becomes structure.
    den: Vec<Vec<f32>>,
    /// For [`SelectMode::HardMax`]: the best weight seen so far, per level.
    best: Vec<Vec<f32>>,
    /// Running per-pixel minimum and maximum of the aligned inputs, indexed by
    /// plane, at level-0 size. Empty under [`Hull::Unclamped`].
    ///
    /// Both are folds — `min` and `max` are associative and commutative — so
    /// they stream over any number of frames and [`absorb`](Self::absorb)
    /// stays exact.
    lo: Vec<Vec<f32>>,
    hi: Vec<Vec<f32>>,
    /// Per-level hulls of the frames' **Gaussian** pyramids for levels
    /// `1..sizes.len()`, indexed `(k - 1) * planes + c`. See [`Hull::PerLevel`].
    /// Empty in every other mode.
    lo_lv: Vec<Vec<f32>>,
    hi_lv: Vec<Vec<f32>>,
    /// Per-level noise sigma, same indexing as `lo_lv`. Held as a running
    /// maximum over frames, which is the conservative direction: a wider margin
    /// permits more genuine gain and clamps less, so an error here costs
    /// artifact suppression rather than resolution.
    sig_lv: Vec<Vec<f32>>,
    frames: u32,
    /// Frames whose contribution was entirely below the noise floor at every
    /// level. Reported, because a stack where this is large is one where the
    /// gate is wrong.
    gain: BandGain,
}

impl BandMerge {
    pub fn new(width: usize, height: usize, planes: usize, cfg: MergeConfig) -> Self {
        assert!(planes > 0, "a merge needs at least one plane");
        let sizes = level_sizes(width, height, cfg.bands);
        let nl = sizes.len();
        let per_level = || -> Vec<Vec<f32>> { sizes.iter().map(|s| vec![0.0; s.pixels()]).collect() };
        Self {
            cfg,
            planes,
            num: (0..nl * planes).map(|i| vec![0.0; sizes[i / planes].pixels()]).collect(),
            usum: (0..nl * planes).map(|i| vec![0.0; sizes[i / planes].pixels()]).collect(),
            den: per_level(),
            best: match cfg.select {
                SelectMode::HardMax => per_level(),
                SelectMode::SoftPower => Vec::new(),
            },
            // Seeded at the identities so the first frame sets both, rather
            // than seeding from frame 0 and special-casing it.
            lo: match cfg.hull.bounds() {
                true => (0..planes).map(|_| vec![f32::INFINITY; sizes[0].pixels()]).collect(),
                false => Vec::new(),
            },
            hi: match cfg.hull.bounds() {
                true => {
                    (0..planes).map(|_| vec![f32::NEG_INFINITY; sizes[0].pixels()]).collect()
                }
                false => Vec::new(),
            },
            // Coarser-level hulls, indexed `(k - 1) * planes + c` for
            // `k` in `1..sizes.len()`. Level 0 is already `lo`/`hi` and is not
            // duplicated here. Allocated only under [`Hull::PerLevel`], so the
            // default configuration carries no extra memory at all.
            lo_lv: if cfg.hull.bounds_each_level() {
                let mut v = Vec::with_capacity((sizes.len() - 1) * planes);
                for k in 1..sizes.len() {
                    for _ in 0..planes {
                        v.push(vec![f32::INFINITY; sizes[k].pixels()]);
                    }
                }
                v
            } else {
                Vec::new()
            },
            hi_lv: if cfg.hull.bounds_each_level() {
                let mut v = Vec::with_capacity((sizes.len() - 1) * planes);
                for k in 1..sizes.len() {
                    for _ in 0..planes {
                        v.push(vec![f32::NEG_INFINITY; sizes[k].pixels()]);
                    }
                }
                v
            } else {
                Vec::new()
            },
            sig_lv: if cfg.hull.bounds_each_level() {
                let mut v = Vec::with_capacity((sizes.len() - 1) * planes);
                for k in 1..sizes.len() {
                    for _ in 0..planes {
                        v.push(vec![0.0f32; sizes[k].pixels()]);
                    }
                }
                v
            } else {
                Vec::new()
            },
            frames: 0,
            // Measured for the depth this plane geometry ACTUALLY reaches, not
            // for `cfg.bands`: `level_sizes` truncates a shallow plane, and a
            // gain vector measured for the requested depth would then be longer
            // or shorter than the pyramid it gates.
            gain: BandGain::measure(sizes.len() - 1),
            sizes,
        }
    }

    pub fn sizes(&self) -> &[LevelSize] {
        &self.sizes
    }

    pub fn frames(&self) -> u32 {
        self.frames
    }

    pub fn band_gain(&self) -> &BandGain {
        &self.gain
    }

    /// Peak resident floats held by this accumulator. For an honest memory
    /// report rather than a guess.
    pub fn accumulator_floats(&self) -> usize {
        let per_level: usize = self.sizes.iter().map(LevelSize::pixels).sum();
        per_level * (2 * self.planes + 1 + usize::from(!self.best.is_empty()))
            + self.lo.iter().chain(&self.hi).map(Vec::len).sum::<usize>()
    }

    /// Fold one frame in.
    ///
    /// `planes` are the frame's colour planes, black-subtracted, all at level-0
    /// size. `luma` is the plane the selection is made on — green luma, so that
    /// the decision is the same one the shipped election makes. `variance` is
    /// the per-pixel level-0 noise variance of `luma`, from [`luma_variance`].
    pub fn add_frame(
        &mut self,
        planes: &[&[f32]],
        luma: &[f32],
        variance: &[f32],
        ws: &mut FrameWorkspace,
    ) {
        assert_eq!(planes.len(), self.planes, "wrong number of planes");
        let n0 = self.sizes[0].pixels();
        assert_eq!(luma.len(), n0);
        assert_eq!(variance.len(), n0);

        // 1. The selection pyramid, and the noise pyramid beside it.
        ws.luma.build(luma, &mut ws.ws);
        ws.var.build_gaussian(variance, &mut ws.ws);

        // 2. Per band, a noise-corrected local energy, then a weight.
        let nb = self.sizes.len() - 1;
        for k in 0..nb {
            let sz = self.sizes[k];
            let px = sz.pixels();
            let lv = ws.luma.level(k);
            let sq = &mut ws.sq[..px];
            for (s, l) in sq.iter_mut().zip(lv) {
                *s = l * l;
            }
            // Smooth the squared coefficients with the same binomial kernel,
            // at the same scale. An unsmoothed |L| is a single noisy sample and
            // makes the weight field as noisy as the data.
            smooth5(sq, sz, &mut ws.smooth_scratch);
            // The coarsest `mean_coarse` bands are averaged, not selected: see
            // `DEFAULT_MEAN_COARSE`. Zeroing the weight routes every coefficient
            // through the unweighted fallback in `finish_level`, which is the
            // same mechanism `BaseBand::Mean` uses -- so this is exactly a mean,
            // not a very soft selection.
            //
            // Interaction with `BaseBand::WeightedFromCoarsest`, stated because
            // it is silent otherwise: that arm reduces `ws.weight` from band
            // `nb - 1` onto the base grid, so if that band is averaged the base
            // weight it derives is zero and the base becomes a mean too. That is
            // the consistent reading -- a base weighted by a band that carries
            // no selection is not weighted -- and it affects only the non-default
            // arm.
            let averaged = k + self.cfg.mean_coarse >= nb;
            let w = &mut ws.weight[..px];
            if averaged {
                w.fill(0.0);
            } else {
                let beta = self.gain.beta(k);
                let gate = self.cfg.gate;
                // Sharper toward the fine bands: see `MergeConfig::sharpen_per_octave`.
                let p = self.cfg.exponent_at(k, nb);
                let vv = ws.var.level(k);
                for ((w, e), v) in w.iter_mut().zip(sq.iter()).zip(vv) {
                    // The floor at this band's scale: the level-0 variance
                    // carried down to this grid, times the measured band gain.
                    let floor = gate * beta * v.max(0.0);
                    let excess = (*e - floor).max(0.0);
                    *w = select_weight(excess, floor, p);
                }
            }
            self.accumulate_level(k, planes, &mut ws.plane, w);
        }

        // 3. The base band.
        //
        // `ws.weight` still holds the coarsest Laplacian band's weight from the
        // loop above, so the base weight is that field reduced once onto the
        // base grid — carried through the same operator, so it is band-limited
        // in exactly the way every other level's weight is. Under
        // [`BaseBand::Mean`] it is simply zero everywhere, which routes every
        // base coefficient through the unweighted fallback.
        let kb = nb;
        let szb = self.sizes[kb];
        match self.cfg.base {
            BaseBand::Mean => ws.coarse[..szb.pixels()].fill(0.0),
            BaseBand::WeightedFromCoarsest => {
                let prev = self.sizes[nb - 1];
                reduce(
                    &ws.weight[..prev.pixels()],
                    prev,
                    &mut ws.coarse[..szb.pixels()],
                    &mut ws.smooth_scratch,
                );
            }
        }
        Self::accumulate_level(self, kb, planes, &mut ws.plane, &ws.coarse[..szb.pixels()]);

        // 4. The hull of the aligned inputs, which the reconstruction will be
        //    confined to. Taken from the frames as supplied — before any
        //    decomposition — because it is a statement about the observations,
        //    not about the representation.
        if self.cfg.hull.bounds() {
            for c in 0..self.planes {
                let (lo, hi) = (&mut self.lo[c][..n0], &mut self.hi[c][..n0]);
                for ((l, h), v) in lo.iter_mut().zip(hi.iter_mut()).zip(planes[c]) {
                    *l = l.min(*v);
                    *h = h.max(*v);
                }
            }
        }
        // 4b. The same statement about the observations, made at every coarser
        //     scale. See [`Hull::PerLevel`]. The frame's GAUSSIAN pyramid is the
        //     right object here, not its Laplacian: during collapse the partial
        //     reconstruction at level `k` is an estimate of the frames' Gaussian
        //     at level `k`, so that is what it has to be confined to. Bounding
        //     the Laplacian band instead would be a no-op, because SoftPower
        //     already makes each band a convex combination within itself.
        if self.cfg.hull.bounds_each_level() {
            for c in 0..self.planes {
                ws.ghull.build_gaussian(planes[c], &mut ws.ws);
                for k in 1..self.sizes.len() {
                    let idx = (k - 1) * self.planes + c;
                    let g = ws.ghull.level(k);
                    let (lo, hi) = (&mut self.lo_lv[idx], &mut self.hi_lv[idx]);
                    for ((l, h), v) in lo.iter_mut().zip(hi.iter_mut()).zip(g) {
                        *l = l.min(*v);
                        *h = h.max(*v);
                    }
                    // The margin's scale. `gain.beta(k) * var` is the module's
                    // own calibrated statement of noise power at level `k` --
                    // the identical quantity the selection gate thresholds on --
                    // so the bound and the gate cannot disagree about what
                    // counts as noise. Reusing it rather than deriving a second
                    // estimate is deliberate: two noise models in one merge is
                    // two things to keep in step.
                    let beta = self.gain.beta(k.min(self.sizes.len() - 2));
                    let vv = ws.var.level(k);
                    let sig = &mut self.sig_lv[idx];
                    for (s, v) in sig.iter_mut().zip(vv) {
                        let cur = (beta * v.max(0.0)).sqrt();
                        *s = s.max(cur);
                    }
                }
            }
        }

        self.frames += 1;
    }

    /// Decompose each colour plane and fold level `k` of it into the
    /// accumulators with the shared weight `w`.
    ///
    /// The plane pyramids are rebuilt per level, which looks wasteful and is
    /// not: `ws.plane` holds them for the whole frame and is built once, on the
    /// first level touched.
    fn accumulate_level(&mut self, k: usize, planes: &[&[f32]], cache: &mut PlaneCache, w: &[f32]) {
        cache.ensure(planes, &self.sizes);
        let px = self.sizes[k].pixels();
        let den = &mut self.den[k][..px];
        match self.cfg.select {
            SelectMode::SoftPower => {
                for (d, wv) in den.iter_mut().zip(w) {
                    *d += wv;
                }
                for c in 0..self.planes {
                    let lv = cache.pyramids[c].level(k);
                    let num = &mut self.num[k * self.planes + c][..px];
                    let usum = &mut self.usum[k * self.planes + c][..px];
                    for i in 0..px {
                        num[i] += w[i] * lv[i];
                        usum[i] += lv[i];
                    }
                }
            }
            SelectMode::HardMax => {
                let best = &mut self.best[k][..px];
                for c in 0..self.planes {
                    let lv = cache.pyramids[c].level(k);
                    let num = &mut self.num[k * self.planes + c][..px];
                    let usum = &mut self.usum[k * self.planes + c][..px];
                    for i in 0..px {
                        if w[i] > best[i] {
                            num[i] = lv[i];
                        }
                        usum[i] += lv[i];
                    }
                }
                for (b, wv) in best.iter_mut().zip(w) {
                    if wv > b {
                        *b = *wv;
                    }
                }
                for (d, wv) in den.iter_mut().zip(w) {
                    *d = d.max(*wv);
                }
            }
        }
    }

    /// Combine another accumulator's frames into this one.
    ///
    /// Exact for [`SelectMode::SoftPower`], because every field is a sum. For
    /// [`SelectMode::HardMax`] it is exact too — a maximum is associative —
    /// **except** for ties, where which frame wins depends on the order frames
    /// were folded. Ties on a continuous statistic are measure-zero and only
    /// arise where both weights are exactly zero, in which case the fallback
    /// mean is used and the tie does not reach the output.
    pub fn absorb(&mut self, other: &BandMerge) {
        assert_eq!(self.sizes, other.sizes, "cannot absorb a differently shaped merge");
        assert_eq!(self.planes, other.planes, "cannot absorb a different plane count");
        if self.cfg.hull.bounds() {
            assert_eq!(
                other.cfg.hull, self.cfg.hull,
                "cannot absorb a merge with a different hull mode"
            );
            for c in 0..self.planes {
                for ((a, b), (x, y)) in self.lo[c]
                    .iter_mut()
                    .zip(&other.lo[c])
                    .zip(self.hi[c].iter_mut().zip(&other.hi[c]))
                {
                    *a = a.min(*b);
                    *x = x.max(*y);
                }
            }
            // The coarser-level hulls are min/max folds exactly as level 0 is,
            // so they absorb identically. Missing this is the failure mode the
            // `Hull::bounds` helper exists to prevent: a chunked render would
            // then clamp each chunk to its OWN per-level hull and produce a
            // result no serial render could, which is precisely the seam this
            // module exists to remove.
            for i in 0..self.lo_lv.len() {
                for ((a, b), (x, y)) in self.lo_lv[i]
                    .iter_mut()
                    .zip(&other.lo_lv[i])
                    .zip(self.hi_lv[i].iter_mut().zip(&other.hi_lv[i]))
                {
                    *a = a.min(*b);
                    *x = x.max(*y);
                }
                for (a, b) in self.sig_lv[i].iter_mut().zip(&other.sig_lv[i]) {
                    *a = a.max(*b);
                }
            }
        }
        match self.cfg.select {
            SelectMode::SoftPower => {
                for k in 0..self.sizes.len() {
                    for (a, b) in self.den[k].iter_mut().zip(&other.den[k]) {
                        *a += b;
                    }
                    for c in 0..self.planes {
                        let i = k * self.planes + c;
                        for (a, b) in self.num[i].iter_mut().zip(&other.num[i]) {
                            *a += b;
                        }
                        for (a, b) in self.usum[i].iter_mut().zip(&other.usum[i]) {
                            *a += b;
                        }
                    }
                }
            }
            SelectMode::HardMax => {
                for k in 0..self.sizes.len() {
                    for c in 0..self.planes {
                        let i = k * self.planes + c;
                        let (bs, os) = (&other.best[k], &other.num[i]);
                        for j in 0..self.num[i].len() {
                            if bs[j] > self.best[k][j] {
                                self.num[i][j] = os[j];
                            }
                        }
                        for (a, b) in self.usum[i].iter_mut().zip(&other.usum[i]) {
                            *a += b;
                        }
                    }
                    for (a, b) in self.best[k].iter_mut().zip(&other.best[k]) {
                        if *b > *a {
                            *a = *b;
                        }
                    }
                    for (a, b) in self.den[k].iter_mut().zip(&other.den[k]) {
                        *a = a.max(*b);
                    }
                }
            }
        }
        self.frames += other.frames;
    }

    /// Fraction of coefficients, per level, where no frame cleared the noise
    /// floor and the merge therefore averaged.
    ///
    /// This is the single most informative diagnostic this merge produces. Near
    /// 1.0 at the fine levels means the gate is refusing everything and the
    /// output is a plain average — soft, but honest. Near 0.0 everywhere means
    /// the gate is not gating and this has become a naive pyramid stacker.
    pub fn averaged_fraction(&self) -> Vec<f64> {
        self.den
            .iter()
            .map(|d| d.iter().filter(|v| **v <= 0.0).count() as f64 / d.len().max(1) as f64)
            .collect()
    }

    /// Resolve the accumulators into one merged Laplacian pyramid per plane and
    /// collapse each to a level-0 image.
    ///
    /// Returns `planes` images at level-0 size, in the order they were supplied
    /// to [`add_frame`](Self::add_frame).
    pub fn finish(&self, ws: &mut Workspace) -> Vec<Vec<f32>> {
        assert!(self.frames > 0, "cannot finish a merge with no frames");
        let inv_n = 1.0 / self.frames as f32;
        (0..self.planes)
            .map(|c| {
                let mut pyr = Pyramid::zeros(&self.sizes);
                for k in 0..self.sizes.len() {
                    let i = k * self.planes + c;
                    let den = &self.den[k];
                    let num = &self.num[i];
                    let usum = &self.usum[i];
                    let out = pyr.level_mut(k);
                    match self.cfg.select {
                        SelectMode::SoftPower => {
                            for j in 0..out.len() {
                                out[j] = if den[j] > 0.0 {
                                    num[j] / den[j]
                                } else {
                                    usum[j] * inv_n
                                };
                            }
                        }
                        SelectMode::HardMax => {
                            for j in 0..out.len() {
                                out[j] = if den[j] > 0.0 { num[j] } else { usum[j] * inv_n };
                            }
                        }
                    }
                }
                let mut img = if self.cfg.hull.bounds_each_level() {
                    // Bound the partial reconstruction at every level on the way
                    // down, so an excursion born in a coarse band cannot be
                    // carried through the remaining expands and amplified. See
                    // [`Hull::PerLevel`] for why the final clamp alone is not
                    // sufficient.
                    self.collapse_bounded(&pyr, c, ws)
                } else {
                    pyr.collapse(ws)
                };
                // Confine the reconstruction to what the inputs support. See
                // [`Hull`]: per-band convexity does not imply reconstruction
                // convexity, so this is the only stage that can make the
                // module's stated safety property true of its output.
                //
                // Still applied under `PerLevel`: the per-level pass bounds
                // levels `1..n`, and this is level 0. Together they bound every
                // level, and running this unconditionally means `PerLevel` is a
                // strict tightening of `InputRange` rather than a replacement
                // whose weaker cases would have to be argued separately.
                if self.cfg.hull.bounds() {
                    for ((p, l), h) in img.iter_mut().zip(&self.lo[c]).zip(&self.hi[c]) {
                        *p = p.clamp(*l, *h);
                    }
                }
                img
            })
            .collect()
    }

    /// [`Pyramid::collapse`], with the partial reconstruction clamped to the
    /// frames' Gaussian hull at each level before it is expanded again.
    ///
    /// Mirrors `collapse` exactly apart from the clamp, deliberately: any
    /// divergence in the reconstruction arithmetic itself would show up as a
    /// difference between hull modes and be misread as an effect of the bound.
    fn collapse_bounded(&self, pyr: &Pyramid, c: usize, ws: &mut Workspace) -> Vec<f32> {
        let n = pyr.levels();
        let mut acc = pyr.level(n - 1).to_vec();
        // The coarsest level is the base residual. It is a convex combination of
        // the frames' Gaussians there, so this clamp is very nearly inactive --
        // but it is applied anyway rather than assumed inactive, because "nearly"
        // is not a property and the unweighted fallback is a mean whose
        // membership of the hull deserves to be enforced rather than reasoned
        // about.
        if n - 1 >= 1 {
            let idx = (n - 2) * self.planes + c;
            let lam = self.cfg.hull_lambda;
            for (((p, l), h), s) in acc
                .iter_mut()
                .zip(&self.lo_lv[idx])
                .zip(&self.hi_lv[idx])
                .zip(&self.sig_lv[idx])
            {
                *p = p.clamp(l - lam * s, h + lam * s);
            }
        }
        for k in (0..n - 1).rev() {
            let px = pyr.sizes()[k].pixels();
            let mut up = vec![0.0; px];
            expand(&acc, pyr.sizes()[k + 1], &mut up, pyr.sizes()[k], &mut ws.scratch);
            for (u, b) in up.iter_mut().zip(pyr.level(k)) {
                *u += b;
            }
            if k >= 1 {
                let idx = (k - 1) * self.planes + c;
                let lam = self.cfg.hull_lambda;
                for (((p, l), h), s) in up
                    .iter_mut()
                    .zip(&self.lo_lv[idx])
                    .zip(&self.hi_lv[idx])
                    .zip(&self.sig_lv[idx])
                {
                    *p = p.clamp(l - lam * s, h + lam * s);
                }
            }
            acc = up;
        }
        acc
    }

    /// Fraction of output pixels, per plane, where the hull clamp moved the
    /// value by more than `tol`.
    ///
    /// `tol` is explicit and not defaulted because the answer at `tol = 0` is
    /// not the one anybody wants: a stack of identical frames has a *point*
    /// hull, so every float error in the collapse is formally outside it and
    /// the honest reading of "0 excursions" would be drowned in dust. In DN, a
    /// fraction of a DN is the right order.
    ///
    /// Reported rather than inferred. Near zero means the reconstruction was
    /// already inside the range its inputs support and the clamp is inert;
    /// large means the merge is routinely emitting values no frame observed,
    /// which is a statement about the selection exponent and not about the
    /// clamp. Empty under [`Hull::Unclamped`].
    pub fn clamped_fraction(&self, ws: &mut Workspace, tol: f32) -> Vec<f64> {
        if !self.cfg.hull.bounds() {
            return Vec::new();
        }
        let unclamped = BandMerge {
            cfg: MergeConfig { hull: Hull::Unclamped, ..self.cfg },
            lo: Vec::new(),
            hi: Vec::new(),
            lo_lv: Vec::new(),
            hi_lv: Vec::new(),
            ..self.clone()
        };
        unclamped
            .finish(ws)
            .iter()
            .enumerate()
            .map(|(c, img)| {
                let n = img.len().max(1) as f64;
                img.iter()
                    .zip(&self.lo[c])
                    .zip(&self.hi[c])
                    .filter(|((p, l), h)| **p < **l - tol || **p > **h + tol)
                    .count() as f64
                    / n
            })
            .collect()
    }
}

/// Per-frame reusable buffers. One of these per worker, not per frame.
#[derive(Debug, Clone)]
pub struct FrameWorkspace {
    ws: Workspace,
    luma: Pyramid,
    var: Pyramid,
    /// Gaussian pyramid of one plane, reused plane-by-plane to fold the
    /// per-level hulls under [`Hull::PerLevel`]. Allocated always (it is one
    /// pyramid per worker, not per frame) but only written in that mode.
    ghull: Pyramid,
    plane: PlaneCache,
    sq: Vec<f32>,
    weight: Vec<f32>,
    coarse: Vec<f32>,
    smooth_scratch: Vec<f32>,
}

impl FrameWorkspace {
    pub fn new(sizes: &[LevelSize], planes: usize) -> Self {
        let n0 = sizes[0].pixels();
        Self {
            ws: Workspace::new(sizes),
            luma: Pyramid::zeros(sizes),
            var: Pyramid::zeros(sizes),
            ghull: Pyramid::zeros(sizes),
            plane: PlaneCache::new(sizes, planes),
            sq: vec![0.0; n0],
            weight: vec![0.0; n0],
            coarse: vec![0.0; n0],
            smooth_scratch: vec![0.0; n0 + sizes[0].width],
        }
    }

    /// Floats held by this workspace, for the memory report.
    pub fn floats(&self) -> usize {
        self.ws.scratch.len()
            + self.ws.expanded.len()
            + self.luma.floats()
            + self.var.floats()
            + self.plane.pyramids.iter().map(Pyramid::floats).sum::<usize>()
            + self.sq.len()
            + self.weight.len()
            + self.coarse.len()
            + self.smooth_scratch.len()
    }

    /// Drop the memoised plane pyramids, so the next frame rebuilds them.
    pub fn next_frame(&mut self) {
        self.plane.valid = false;
    }
}

#[derive(Debug, Clone)]
struct PlaneCache {
    pyramids: Vec<Pyramid>,
    ws: Workspace,
    valid: bool,
}

impl PlaneCache {
    fn new(sizes: &[LevelSize], planes: usize) -> Self {
        Self {
            pyramids: (0..planes).map(|_| Pyramid::zeros(sizes)).collect(),
            ws: Workspace::new(sizes),
            valid: false,
        }
    }

    fn ensure(&mut self, planes: &[&[f32]], _sizes: &[LevelSize]) {
        if self.valid {
            return;
        }
        for (p, src) in self.pyramids.iter_mut().zip(planes) {
            p.build(src, &mut self.ws);
        }
        self.valid = true;
    }
}

/// In-place separable 5-tap binomial smoothing at one level's own scale.
fn smooth5(data: &mut [f32], size: LevelSize, scratch: &mut [f32]) {
    let (w, h) = (size.width, size.height);
    assert!(scratch.len() >= w * h + w, "smooth5: scratch is too small");
    for y in 0..h {
        let row = &data[y * w..y * w + w];
        let out = &mut scratch[..w];
        for (x, o) in out.iter_mut().enumerate() {
            let mut acc = 0.0f32;
            for (t, k) in KERNEL.iter().enumerate() {
                acc += k * row[clamp_tap(x, t, w)];
            }
            *o = acc;
        }
        data[y * w..y * w + w].copy_from_slice(&scratch[..w]);
    }
    // Vertical needs a full copy, because a row is read after it is written.
    let col = &mut scratch[..w * h];
    col.copy_from_slice(&data[..w * h]);
    for y in 0..h {
        let out = &mut data[y * w..y * w + w];
        out.fill(0.0);
        for (t, k) in KERNEL.iter().enumerate() {
            let sy = clamp_tap(y, t, h);
            let row = &col[sy * w..sy * w + w];
            for (o, v) in out.iter_mut().zip(row) {
                *o += k * v;
            }
        }
    }
}

/// The signal-to-noise ratio at which a coefficient is considered plainly real.
///
/// Only a *reference point*: the weight is `(snr / SNR_REF)^p`, and since every
/// weight at a level is divided by the same constant, the merge is
/// mathematically unchanged by it. What it buys is dynamic range. Without it,
/// weights at the fine-band exponents are all astronomically large and, once
/// clamped, all astronomically large *and equal* — see [`select_weight`].
const SNR_REF: f32 = 64.0;

/// Turn a noise-corrected band energy into a selection weight, safely.
///
/// The weight is `(excess / floor / SNR_REF)^p` — a **signal-to-noise ratio**
/// raised to the exponent, not the raw energy. Two reasons, and the first is a
/// correctness bug the scale-dependent exponent would otherwise introduce:
///
/// 1. **`excess` is in DN^2 and reaches ~1e7.** At the fine-band exponents the
///    ramp produces, `excess^p` overflows `f32` outright (`1e7^8 = 1e56`), and
///    every weight becomes `inf`. `inf/inf` is `NaN`, and a single NaN
///    coefficient propagates through the collapse into a black hole in the
///    output.
/// 2. **A ratio is the meaningful quantity anyway.** "This coefficient is 40x
///    its own noise floor" is scene-independent; "this coefficient is 900000"
///    is not, and would make the selection behave differently in bright and
///    dark parts of the same frame purely through the units.
///
/// # The clamp has to be centred, and that is not a detail
///
/// A clamp on `p * ln(snr)` alone is worse than useless at high `p`. With
/// `p = 16` and a bound of 60, everything above `snr = 42` saturates, so every
/// frame that is clearly in focus receives the *same* weight and the merge
/// silently averages all of them — maximum blur, produced by the parameter
/// meant to maximise acuity. This was observed: it turned a sharp render into a
/// glowing mush.
///
/// Dividing by `SNR_REF` first centres the log near zero, so the weights
/// straddle 1 instead of piling up against the ceiling, and the clamp becomes
/// what it was meant to be — an overflow guard that never binds in practice
/// rather than a silent averaging switch.
#[inline]
fn select_weight(excess: f32, floor: f32, p: f32) -> f32 {
    if excess <= 0.0 {
        return 0.0;
    }
    // `floor` is zero only where the noise model says this pixel has no noise
    // at all, which cannot happen physically but can happen at a clamped black
    // pixel. Treat it as "one DN^2" rather than dividing by zero.
    let r = excess / floor.max(1.0) / SNR_REF;
    if p == 1.0 {
        r
    } else if p == 2.0 {
        r * r
    } else {
        // `exp(+-80)` spans `[2e-35, 6e34]`; summed over even a 1000-frame
        // stack that stays inside `f32`, so this bound cannot overflow and,
        // being centred, effectively never binds.
        (p * r.ln()).clamp(-80.0, 80.0).exp()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ramp(w: usize, h: usize) -> Vec<f32> {
        (0..w * h).map(|i| (i % 97) as f32 * 0.37 + (i / 97) as f32 * 0.11).collect()
    }

    #[test]
    fn the_generating_kernel_is_binomial_and_sums_to_one() {
        assert_eq!(KERNEL, [1.0 / 16.0, 4.0 / 16.0, 6.0 / 16.0, 4.0 / 16.0, 1.0 / 16.0]);
        assert!((KERNEL.iter().sum::<f32>() - 1.0).abs() < 1e-7);
    }

    #[test]
    fn reduce_and_expand_preserve_a_constant_exactly() {
        let size = LevelSize { width: 37, height: 23 };
        let src = vec![4.25f32; size.pixels()];
        let ds = size.reduced();
        let mut small = vec![0.0; ds.pixels()];
        let mut scratch = vec![0.0; size.pixels() + size.width];
        reduce(&src, size, &mut small, &mut scratch);
        for v in &small {
            assert!((v - 4.25).abs() < 1e-5, "reduce moved a constant: {v}");
        }
        let mut back = vec![0.0; size.pixels()];
        expand(&small, ds, &mut back, size, &mut scratch);
        for v in &back {
            assert!((v - 4.25).abs() < 1e-5, "expand moved a constant: {v}");
        }
    }

    #[test]
    fn expand_reproduces_a_linear_ramp() {
        // Both phases are exact on a ramp, which is what keeps the operator
        // from adding curvature of its own inside a smooth region. A kernel
        // that failed this would put a low-amplitude checkerboard into every
        // flat gradient in the frame.
        let ss = LevelSize { width: 16, height: 1 };
        let src: Vec<f32> = (0..16).map(|i| i as f32).collect();
        let ds = LevelSize { width: 32, height: 1 };
        let mut out = vec![0.0; 32];
        let mut scratch = vec![0.0; 64];
        expand(&src, ss, &mut out, ds, &mut scratch);
        // Interior only: the ends are clamped, which is correct behaviour and
        // is not a ramp.
        for x in 4..28 {
            let want = x as f32 * 0.5;
            assert!(
                (out[x] - want).abs() < 1e-4,
                "expand is not exact on a ramp at {x}: {} vs {want}",
                out[x]
            );
        }
    }

    #[test]
    fn a_laplacian_pyramid_reconstructs_its_input() {
        // The property everything else rests on. If the decomposition is not
        // invertible then every "improvement" measured through it is confounded
        // with a reconstruction error.
        for (w, h) in [(64usize, 64usize), (37, 23), (129, 71)] {
            let sizes = level_sizes(w, h, 4);
            let mut ws = Workspace::new(&sizes);
            let mut pyr = Pyramid::zeros(&sizes);
            let src = ramp(w, h);
            pyr.build(&src, &mut ws);
            let back = pyr.collapse(&mut ws);
            let err = src
                .iter()
                .zip(&back)
                .map(|(a, b)| (a - b).abs())
                .fold(0.0f32, f32::max);
            assert!(err < 1e-2, "{w}x{h}: reconstruction error {err}");
        }
    }

    #[test]
    fn a_constant_image_has_zero_detail_bands() {
        let sizes = level_sizes(64, 64, 4);
        let mut ws = Workspace::new(&sizes);
        let mut pyr = Pyramid::zeros(&sizes);
        pyr.build(&vec![7.0; 64 * 64], &mut ws);
        for k in 0..pyr.bands() {
            let m = pyr.level(k).iter().fold(0.0f32, |a, v| a.max(v.abs()));
            assert!(m < 1e-4, "band {k} of a constant image is not zero: {m}");
        }
        let base = pyr.level(pyr.bands());
        for v in base {
            assert!((v - 7.0).abs() < 1e-4);
        }
    }

    #[test]
    fn levels_stop_before_a_band_becomes_meaningless() {
        let sizes = level_sizes(3516, 2344, 7);
        assert_eq!(sizes.len(), 8, "7 bands plus a base");
        assert_eq!(sizes[0], LevelSize { width: 3516, height: 2344 });
        assert!(sizes[7].width >= MIN_LEVEL_EXTENT && sizes[7].height >= MIN_LEVEL_EXTENT);
        // And a small plane truncates rather than producing 2x1 levels.
        let small = level_sizes(40, 40, 7);
        assert!(small.len() < 8);
        assert!(small.last().unwrap().width >= MIN_LEVEL_EXTENT);
    }

    #[test]
    fn the_band_noise_gain_falls_with_scale_and_is_never_zero() {
        // The number the gate multiplies. If this were computed by compounding
        // the kernel's squared-weight sum it would read 0.0748^k and be an
        // order of magnitude too small by level 3, at which point the gate
        // stops gating. These are the operators' real numbers.
        let g = BandGain::measure(5);
        assert_eq!(g.all().len(), 6);
        for (k, b) in g.all().iter().enumerate() {
            assert!(*b > 0.0 && b.is_finite(), "beta[{k}] = {b}");
        }
        assert!(g.beta(0) > g.beta(1), "the finest band must carry the most noise");
        assert!(g.beta(1) > g.beta(2));
        // Level 0 keeps most of a white input: REDUCE removes almost all of it,
        // so the difference keeps almost all of it.
        assert!(g.beta(0) > 0.5, "beta[0] = {}", g.beta(0));
        // And it is deterministic.
        let again = BandGain::measure(5);
        assert_eq!(g.all(), again.all(), "the band gain probe is not reproducible");
    }

    #[test]
    fn the_band_gain_probe_reaches_the_depth_it_is_asked_for() {
        // Regression. The probe was a fixed 256 x 256, which truncates at five
        // bands, so a real 3520 x 2344 plane merged at the default seven bands
        // indexed off the end of `beta` and panicked mid-render. The probe size
        // must be derived from the depth.
        for bands in 1..=DEFAULT_BANDS + 1 {
            let g = BandGain::measure(bands);
            assert_eq!(
                g.all().len(),
                bands + 1,
                "beta is {} long for {bands} bands",
                g.all().len()
            );
        }
        // And a real plane geometry merges without indexing off the end.
        let cfg = MergeConfig::default();
        let m = BandMerge::new(3520, 2344, 4, cfg);
        assert_eq!(m.sizes().len(), DEFAULT_BANDS + 1);
        assert_eq!(m.band_gain().all().len(), m.sizes().len());
    }

    #[test]
    fn the_band_gain_is_a_property_of_the_operators_not_the_probe_size() {
        // `beta` is the variance gain of a fixed linear cascade on white noise,
        // so it must not depend on how big a field it was measured on. If it
        // did, the floor would be an artefact of the probe and the gate would
        // mean something different on every image size.
        let small = BandGain::measure(3);
        let deep = BandGain::measure(6);
        for k in 0..=3 {
            let (a, b) = (small.beta(k), deep.beta(k));
            // The base band is excluded: level 3 is a Laplacian band in the
            // 6-band pyramid but the *base* residual in the 3-band one, and
            // those are genuinely different operators.
            if k == 3 {
                continue;
            }
            assert!(
                (a - b).abs() / b < 0.05,
                "beta[{k}] is {a} measured at depth 3 but {b} at depth 6"
            );
        }
    }

    #[test]
    fn the_selection_sharpens_toward_the_fine_bands() {
        let cfg = MergeConfig::default();
        let nb = DEFAULT_BANDS;
        // Coarsest Laplacian band gets exactly `exponent`.
        assert_eq!(cfg.exponent_at(nb - 1, nb), cfg.exponent);
        // And it is monotonically sharper toward fine.
        for k in 0..nb - 1 {
            assert!(
                cfg.exponent_at(k, nb) >= cfg.exponent_at(k + 1, nb),
                "band {k} is not at least as selective as band {}",
                k + 1
            );
        }
        assert!(
            cfg.exponent_at(0, nb) > cfg.exponent_at(nb - 1, nb),
            "the ramp is flat, so the fine bands get no more acuity than the coarse ones"
        );
        // Never past the ceiling, at any depth.
        for k in 0..nb {
            assert!(cfg.exponent_at(k, nb) <= MAX_EXPONENT);
        }
        // And `1.0` restores a single global exponent, so the ramp is opt-out.
        let flat = MergeConfig { sharpen_per_octave: 1.0, ..MergeConfig::default() };
        for k in 0..nb {
            assert_eq!(flat.exponent_at(k, nb), flat.exponent);
        }
    }

    #[test]
    fn a_large_band_energy_does_not_overflow_the_weight() {
        // Regression, and the reason the weight is an SNR rather than a raw
        // energy. Band energies are in DN^2 and reach ~1e7 on a bright subject;
        // `1e7^8` is `1e56`, which is `inf` in f32. Every weight becomes `inf`,
        // `inf/inf` is `NaN`, and one NaN coefficient spreads through the
        // collapse into a black hole in the output image.
        for p in [1.0, 2.0, 4.0, 8.0, MAX_EXPONENT] {
            for excess in [1e-8f32, 1.0, 1e4, 1e7, 1e12] {
                for floor in [0.0f32, 1.0, 1e3] {
                    let w = select_weight(excess, floor, p);
                    assert!(
                        w.is_finite() && w >= 0.0,
                        "weight {w} for excess {excess}, floor {floor}, p {p}"
                    );
                }
            }
        }
        // Ordering is still strictly preserved where it matters -- a stronger
        // coefficient must always outweigh a weaker one at the same floor.
        let p = 8.0;
        assert!(select_weight(1e5, 100.0, p) > select_weight(1e4, 100.0, p));
        assert!(select_weight(1e4, 100.0, p) > select_weight(1e3, 100.0, p));
        // And nothing below the floor may carry any weight at all.
        assert_eq!(select_weight(0.0, 100.0, p), 0.0);
    }

    #[test]
    fn a_high_exponent_still_discriminates_between_sharp_frames() {
        // The bug this is here to stop, which shipped a render of glowing mush:
        // an UNCENTRED log clamp saturates at high `p`, so every frame above a
        // modest SNR gets an identical weight and the merge averages all of
        // them. The parameter meant to maximise acuity produced maximum blur.
        //
        // The property that matters is not "no overflow" -- the buggy version
        // did not overflow either -- it is that the weight keeps ORDERING
        // frames across the whole range of sharpness a real stack contains.
        for p in [2.0, 4.0, 8.0, MAX_EXPONENT] {
            let floor = 100.0;
            // Two clearly-in-focus frames a factor of 2 apart in band energy.
            // A 300-frame bracket has many such pairs, and telling them apart
            // is the entire job.
            for snr in [10.0f32, 100.0, 1_000.0, 10_000.0, 100_000.0] {
                let lo = select_weight(snr * floor, floor, p);
                let hi = select_weight(2.0 * snr * floor, floor, p);
                assert!(
                    hi > lo * 1.5,
                    "at p={p}, snr={snr}: doubling the band energy moved the weight from \
                     {lo:e} to only {hi:e}. The clamp is averaging frames it should be \
                     ranking."
                );
                assert!(hi.is_finite(), "weight {hi:e} at p={p}, snr={snr}");
            }
        }
    }

    #[test]
    fn the_weight_sum_cannot_overflow_over_a_long_stack() {
        // 300 frames is a real bracket here, and every weight is summed into
        // one f32 accumulator. If that sum saturates to `inf`, the normalised
        // output is NaN everywhere the sum saturated.
        let mut sum = 0.0f32;
        for _ in 0..1000 {
            sum += select_weight(1e9, 1.0, MAX_EXPONENT);
        }
        assert!(sum.is_finite(), "the weight sum overflowed to {sum}");
    }

    #[test]
    fn a_sharpened_merge_still_reconstructs_a_single_frame_exactly() {
        // The ramp changes the weights, so it must not change the one case
        // where the answer is known: with every frame identical, any convex
        // combination has to return that frame. If the sharpening had broken
        // normalisation this would drift.
        let (w, h) = (96, 72);
        let img = ramp(w, h);
        let cfg = MergeConfig { sharpen_per_octave: 2.0, ..MergeConfig::default() };
        let mut m = BandMerge::new(w, h, 1, cfg);
        let sizes = level_sizes(w, h, cfg.bands);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        let var = vec![4.0f32; w * h];
        for _ in 0..5 {
            fws.next_frame();
            m.add_frame(&[&img], &img, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = m.finish(&mut ws);
        for (i, (a, b)) in out[0].iter().zip(&img).enumerate() {
            assert!(
                (a - b).abs() < 0.05,
                "pixel {i}: merged {a} but every input frame was {b}"
            );
        }
    }

    /// Build a frame that is sharp on the left and blurred on the right, and
    /// its mirror image. This is a synthetic depth boundary with a known right
    /// answer.
    fn split_focus(w: usize, h: usize, sharp_left: bool) -> Vec<f32> {
        let mut v = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                // A fine texture on a smooth background, so there is genuine
                // detail to select and a genuine low frequency to blend.
                let bg = 1000.0 + 400.0 * ((x as f32 / w as f32) * 3.0).sin();
                let fine = 120.0 * (((x * 7 + y * 5) % 11) as f32 / 11.0 - 0.5);
                let is_sharp = (x < w / 2) == sharp_left;
                v[y * w + x] = if is_sharp { bg + fine } else { bg };
            }
        }
        v
    }

    #[test]
    fn the_merge_recovers_detail_from_both_frames() {
        let (w, h) = (128usize, 96usize);
        let a = split_focus(w, h, true);
        let b = split_focus(w, h, false);
        let cfg = MergeConfig { bands: 4, ..Default::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        // A tiny, uniform variance: the synthetic detail is far above it.
        let var = vec![4.0f32; w * h];
        for f in [&a, &b] {
            fws.next_frame();
            merge.add_frame(&[f.as_slice()], f, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = merge.finish(&mut ws)[0].clone();

        // Detail amplitude, measured well away from the seam so this is about
        // selection and not about the transition.
        let amp = |img: &[f32], x0: usize, x1: usize| -> f32 {
            let mut acc = 0.0f64;
            let mut n = 0;
            for y in 8..h - 8 {
                for x in x0..x1 {
                    let c = img[y * w + x];
                    let m = 0.25 * (img[y * w + x - 1] + img[y * w + x + 1] + img[(y - 1) * w + x] + img[(y + 1) * w + x]);
                    acc += f64::from((c - m) * (c - m));
                    n += 1;
                }
            }
            (acc / n as f64).sqrt() as f32
        };
        let left_a = amp(&a, 8, w / 2 - 8);
        let right_b = amp(&b, w / 2 + 8, w - 8);
        let left_out = amp(&out, 8, w / 2 - 8);
        let right_out = amp(&out, w / 2 + 8, w - 8);
        assert!(
            left_out > 0.75 * left_a,
            "left detail lost: {left_out} vs {left_a}"
        );
        assert!(
            right_out > 0.75 * right_b,
            "right detail lost: {right_out} vs {right_b}"
        );
    }

    #[test]
    fn the_merge_does_not_step_across_the_seam() {
        // THE structural claim. A per-pixel selection followed by a gather puts
        // a discontinuity into the LOW frequencies wherever the elected frame
        // changes; a multi-band merge cannot. Both frames here share the same
        // smooth background, so any low-frequency step at the seam was
        // manufactured by the merge.
        let (w, h) = (128usize, 96usize);
        let a = split_focus(w, h, true);
        let b = split_focus(w, h, false);
        let cfg = MergeConfig { bands: 4, ..Default::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        let var = vec![4.0f32; w * h];
        for f in [&a, &b] {
            fws.next_frame();
            merge.add_frame(&[f.as_slice()], f, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = merge.finish(&mut ws)[0].clone();

        // Low-pass both the input and the output the same way, then compare
        // near the seam. Working on the low-passed image is the point: a rim is
        // a LOW-frequency step, and measuring the raw pixels would just find
        // the fine texture.
        let lowpass = |img: &[f32]| -> Vec<f32> {
            let s = LevelSize { width: w, height: h };
            let mut p = Pyramid::zeros(&sizes);
            let mut lws = Workspace::new(&sizes);
            p.build_gaussian(img, &mut lws);
            // Expand the coarsest level back to full size.
            let mut cur = p.level(sizes.len() - 1).to_vec();
            for k in (0..sizes.len() - 1).rev() {
                let mut up = vec![0.0; sizes[k].pixels()];
                expand(&cur, sizes[k + 1], &mut up, sizes[k], &mut lws.scratch);
                cur = up;
            }
            assert_eq!(cur.len(), s.pixels());
            cur
        };
        let lo_in = lowpass(&a);
        let lo_out = lowpass(&out);
        // The residual of the output's low frequencies against a frame that has
        // the same low frequencies everywhere. A selection seam shows up here
        // as a localised spike at x = w/2.
        let seam = (0..h)
            .map(|y| (lo_out[y * w + w / 2] - lo_in[y * w + w / 2]).abs())
            .fold(0.0f32, f32::max);
        let away = (0..h)
            .map(|y| (lo_out[y * w + 12] - lo_in[y * w + 12]).abs())
            .fold(0.0f32, f32::max);
        let bg = 400.0f32; // the background's own peak-to-peak swing
        assert!(
            seam < 0.02 * bg,
            "a low-frequency step appeared at the seam: {seam} DN against a {bg} DN background"
        );
        assert!(seam < away + 0.01 * bg, "the seam is worse than a non-seam column");
    }

    #[test]
    fn pure_noise_is_averaged_not_selected() {
        // The failure mode of every naive pyramid stacker: argmax over n noisy
        // coefficients reliably picks the largest noise excursion, so a flat
        // region gains contrast instead of losing it. The noise gate is what
        // stops that, and this is the test that says it works.
        let (w, h) = (96usize, 96usize);
        let n = 16usize;
        let sigma = 10.0f32;
        let var = vec![sigma * sigma; w * h];
        let mut state: u64 = 12345;
        let mut rnd = move || {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            (((state >> 33) as f32) / ((1u64 << 31) as f32) - 1.0) * sigma * 1.732
        };
        let frames: Vec<Vec<f32>> = (0..n)
            .map(|_| (0..w * h).map(|_| 500.0 + rnd()).collect())
            .collect();
        let cfg = MergeConfig { bands: 4, ..Default::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        for f in &frames {
            fws.next_frame();
            merge.add_frame(&[f.as_slice()], f, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = merge.finish(&mut ws)[0].clone();

        let sd = |img: &[f32]| -> f32 {
            let inner: Vec<f32> = (8..h - 8)
                .flat_map(|y| (8..w - 8).map(move |x| (y, x)))
                .map(|(y, x)| img[y * w + x])
                .collect();
            let m = inner.iter().sum::<f32>() / inner.len() as f32;
            (inner.iter().map(|v| (v - m) * (v - m)).sum::<f32>() / inner.len() as f32).sqrt()
        };
        let single = sd(&frames[0]);
        let merged = sd(&out);
        let ideal = single / (n as f32).sqrt();
        // A selector would land at or ABOVE `single`. Averaging lands at
        // `ideal`. Allow generous slack for the fact that the gate lets a few
        // coefficients through, but the answer must be on the averaging side by
        // a wide margin.
        assert!(
            merged < 0.35 * single,
            "pure noise was selected, not averaged: merged sd {merged}, single {single}, ideal {ideal}"
        );
    }

    #[test]
    fn chunked_folding_gives_the_same_merge() {
        // The streaming property, asserted rather than assumed. A 300-frame
        // stack at 33 MP cannot be merged any other way, and a fold that is not
        // associative would make the render depend on the worker count.
        let (w, h) = (64usize, 48usize);
        let cfg = MergeConfig { bands: 3, ..Default::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let var = vec![9.0f32; w * h];
        let frames: Vec<Vec<f32>> = (0..6)
            .map(|i| {
                let mut v = split_focus(w, h, i % 2 == 0);
                for (j, x) in v.iter_mut().enumerate() {
                    *x += ((i * 31 + j * 17) % 13) as f32;
                }
                v
            })
            .collect();

        let run = |chunks: usize| -> Vec<f32> {
            let per = frames.len().div_ceil(chunks);
            let mut acc: Option<BandMerge> = None;
            for c in frames.chunks(per) {
                let mut m = BandMerge::new(w, h, 1, cfg);
                let mut fws = FrameWorkspace::new(&sizes, 1);
                for f in c {
                    fws.next_frame();
                    m.add_frame(&[f.as_slice()], f, &var, &mut fws);
                }
                match &mut acc {
                    Some(a) => a.absorb(&m),
                    None => acc = Some(m),
                }
            }
            let mut ws = Workspace::new(&sizes);
            acc.unwrap().finish(&mut ws)[0].clone()
        };
        let one = run(1);
        let three = run(3);
        let err = one.iter().zip(&three).map(|(a, b)| (a - b).abs()).fold(0.0f32, f32::max);
        let scale = one.iter().fold(0.0f32, |a, v| a.max(v.abs()));
        assert!(err < 1e-3 * scale, "chunking changed the merge: {err} on a scale of {scale}");
    }

    #[test]
    fn the_selection_is_shared_across_planes() {
        // Colour planes must be gathered by the SAME decision the green luma
        // made. If each plane elected for itself, chroma noise would drive the
        // selection and the merge would manufacture colour speckle.
        let (w, h) = (64usize, 64usize);
        let cfg = MergeConfig { bands: 3, ..Default::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let var = vec![4.0f32; w * h];
        let mut merge = BandMerge::new(w, h, 2, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 2);
        for sharp_left in [true, false] {
            let luma = split_focus(w, h, sharp_left);
            // Second plane is the first scaled by 3. A shared selection must
            // reproduce that ratio exactly in the output.
            let scaled: Vec<f32> = luma.iter().map(|v| v * 3.0).collect();
            fws.next_frame();
            merge.add_frame(&[luma.as_slice(), scaled.as_slice()], &luma, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = merge.finish(&mut ws);
        let err = out[0]
            .iter()
            .zip(&out[1])
            .map(|(a, b)| (a * 3.0 - b).abs())
            .fold(0.0f32, f32::max);
        let scale = out[1].iter().fold(0.0f32, |a, v| a.max(v.abs()));
        assert!(err < 1e-3 * scale, "planes did not share one selection: {err} of {scale}");
    }

    #[test]
    fn a_merge_of_identical_frames_returns_the_frame() {
        // The identity a merge must satisfy: if every frame is the same
        // photograph, the merge is that photograph. Any pyramid bug -- a
        // mis-sized level, a border that does not replicate, a collapse that
        // does not invert the build -- shows up here as a difference.
        let (w, h) = (100usize, 60usize);
        let cfg = MergeConfig::default();
        let sizes = level_sizes(w, h, cfg.bands);
        let src = ramp(w, h);
        let var = vec![25.0f32; w * h];
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        for _ in 0..5 {
            fws.next_frame();
            merge.add_frame(&[src.as_slice()], &src, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = merge.finish(&mut ws)[0].clone();
        let err = src.iter().zip(&out).map(|(a, b)| (a - b).abs()).fold(0.0f32, f32::max);
        assert!(err < 1e-2, "merging a frame with itself moved it by {err} DN");
    }

    #[test]
    fn hard_max_is_reachable_as_a_control() {
        // Kept honest: the soft rule is only defensibly better than the
        // textbook one if the textbook one can actually be run.
        let (w, h) = (64usize, 64usize);
        let cfg = MergeConfig { bands: 3, select: SelectMode::HardMax, ..Default::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let var = vec![4.0f32; w * h];
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        for sharp_left in [true, false] {
            let f = split_focus(w, h, sharp_left);
            fws.next_frame();
            merge.add_frame(&[f.as_slice()], &f, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = merge.finish(&mut ws)[0].clone();
        assert!(out.iter().all(|v| v.is_finite()));
        assert_eq!(merge.frames(), 2);
    }

    #[test]
    fn the_averaged_fraction_reports_where_the_gate_refused() {
        let (w, h) = (64usize, 64usize);
        let cfg = MergeConfig { bands: 3, ..Default::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let flat = vec![800.0f32; w * h];
        // A huge declared noise floor: nothing can clear it, so every level
        // must report that it averaged.
        let var = vec![1.0e6f32; w * h];
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        for _ in 0..3 {
            fws.next_frame();
            merge.add_frame(&[flat.as_slice()], &flat, &var, &mut fws);
        }
        let frac = merge.averaged_fraction();
        for (k, f) in frac.iter().enumerate().take(sizes.len() - 1) {
            assert!(*f > 0.999, "level {k} claims it selected on pure noise: {f}");
        }
    }

    /// The base band default is a measurement, so pin it.
    ///
    /// It was flipped from [`BaseBand::WeightedFromCoarsest`] to
    /// [`BaseBand::Mean`] on `flower-bud-alone-cpl`: weighting cost −475 DN of
    /// global level and 835 DN of position-dependent structure against +11 DN
    /// and 45 DN for the mean, with no difference in aura removal. Nothing in
    /// the suite noticed that change when it was made, which is exactly the
    /// condition this test exists to remove.
    /// Frames engineered so that different bands prefer different frames at the
    /// same pixel — the precondition for a hull violation.
    ///
    /// Frame `f` carries fine texture in one vertical stripe and a coarse blob
    /// in a *different* stripe, so the finest band's weight field and the
    /// coarsest band's weight field are dominated by different frames over the
    /// same ground. Part of the field is dark, because that is where an
    /// excursion crosses zero and clips.
    fn disagreeing_bands(w: usize, h: usize, nf: usize, f: usize) -> Vec<f32> {
        let mut v = vec![0.0f32; w * h];
        let stripe = w / nf;
        let fine_lo = f * stripe;
        let coarse_lo = ((f + nf / 2) % nf) * stripe;
        for y in 0..h {
            for x in 0..w {
                // A dark left third, so the hull sits near zero there.
                let bg = if x < w / 3 { 60.0 } else { 900.0 };
                let coarse = if x >= coarse_lo && x < coarse_lo + stripe { 700.0 } else { 0.0 };
                let fine = if x >= fine_lo && x < fine_lo + stripe {
                    260.0 * (((x * 5 + y * 3) % 7) as f32 / 7.0 - 0.5)
                } else {
                    0.0
                };
                v[y * w + x] = bg + coarse + fine;
            }
        }
        v
    }

    /// Merge `nf` disagreeing frames and count output pixels outside the
    /// per-pixel hull of the inputs.
    fn hull_violations(hull: Hull) -> (usize, usize, f32) {
        let (w, h, nf) = (192usize, 144usize, 8usize);
        let frames: Vec<Vec<f32>> = (0..nf).map(|f| disagreeing_bands(w, h, nf, f)).collect();
        let cfg = MergeConfig { hull, ..MergeConfig::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        let var = vec![4.0f32; w * h];
        for f in &frames {
            fws.next_frame();
            merge.add_frame(&[f.as_slice()], f, &var, &mut fws);
        }
        let out = merge.finish(&mut Workspace::new(&sizes))[0].clone();

        let (mut bad, mut worst) = (0usize, 0.0f32);
        for i in 0..out.len() {
            let lo = frames.iter().fold(f32::INFINITY, |a, f| a.min(f[i]));
            let hi = frames.iter().fold(f32::NEG_INFINITY, |a, f| a.max(f[i]));
            let d = (lo - out[i]).max(out[i] - hi);
            if d > 1e-3 {
                bad += 1;
                worst = worst.max(d / (hi - lo).max(1.0));
            }
        }
        (bad, out.len(), worst)
    }

    #[test]
    fn unclamped_the_reconstruction_leaves_the_hull_of_its_inputs() {
        // The negative control, and it is the load-bearing half of this pair.
        // A clamp that is never asked to do anything passes its own test
        // trivially, so this asserts the defect is genuinely present in the
        // construction before the next test asserts it is gone.
        let (bad, n, worst) = hull_violations(Hull::Unclamped);
        assert!(
            bad > 0,
            "no hull violation to clamp: the construction does not exercise the defect, \
             so the clamp test below would be vacuous ({n} px)"
        );
        // Not a hair outside: a violation at the noise level would not be the
        // phenomenon ORCH measured.
        assert!(worst > 0.01, "violations are trivially small (worst {worst} of span)");
    }

    #[test]
    fn the_reconstruction_never_leaves_the_hull_of_its_inputs() {
        let (bad, n, worst) = hull_violations(Hull::InputRange);
        assert_eq!(bad, 0, "{bad}/{n} output pixels outside the input hull, worst {worst} of span");
    }

    #[test]
    fn per_level_also_never_leaves_the_hull_of_its_inputs() {
        // `PerLevel` is a strict tightening of `InputRange`, so it inherits the
        // safety property rather than trading it away.
        let (bad, n, worst) = hull_violations(Hull::PerLevel);
        assert_eq!(bad, 0, "{bad}/{n} output pixels outside the input hull, worst {worst} of span");
    }

    /// Pixels the FINAL level-0 clamp had to rescue, i.e. sitting exactly on the
    /// hull boundary in the output.
    ///
    /// This is the statistic that separates the two clamping modes. Both end up
    /// inside the hull, so counting violations cannot tell them apart -- both
    /// read zero. What `PerLevel` claims is that the excursion is caught at the
    /// coarse level where it is born, so that by the time the reconstruction
    /// reaches level 0 there is far less for the last clamp to do. A pixel
    /// pinned exactly at `lo` or `hi` is one the last clamp rescued.
    fn pinned_to_hull(hull: Hull) -> (usize, usize) {
        let (w, h, nf) = (192usize, 144usize, 8usize);
        let frames: Vec<Vec<f32>> = (0..nf).map(|f| disagreeing_bands(w, h, nf, f)).collect();
        let cfg = MergeConfig { hull, ..MergeConfig::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        let var = vec![4.0f32; w * h];
        for f in &frames {
            fws.next_frame();
            merge.add_frame(&[f.as_slice()], f, &var, &mut fws);
        }
        let out = merge.finish(&mut Workspace::new(&sizes))[0].clone();
        let mut pinned = 0usize;
        for i in 0..out.len() {
            let lo = frames.iter().fold(f32::INFINITY, |a, f| a.min(f[i]));
            let hi = frames.iter().fold(f32::NEG_INFINITY, |a, f| a.max(f[i]));
            if (out[i] - lo).abs() < 1e-3 || (out[i] - hi).abs() < 1e-3 {
                pinned += 1;
            }
        }
        (pinned, out.len())
    }

    #[test]
    fn per_level_leaves_the_final_clamp_less_to_do() {
        // The whole claim of `Hull::PerLevel`, stated as something that can
        // fail. If bounding each level did nothing, the last clamp would rescue
        // the same pixels it always did and these two counts would match.
        let (pinned_flat, n) = pinned_to_hull(Hull::InputRange);
        let (pinned_deep, _) = pinned_to_hull(Hull::PerLevel);
        assert!(
            pinned_flat > 0,
            "the fixture does not exercise the clamp at all ({n} px), so this \
             comparison would be vacuous"
        );
        assert!(
            pinned_deep < pinned_flat,
            "bounding every level did not reduce the work left to the final clamp: \
             {pinned_deep} pinned vs {pinned_flat} of {n} px"
        );
    }

    #[test]
    fn per_level_is_exact_when_every_frame_agrees() {
        // The do-no-harm case. With identical frames the hull is a point at
        // every level, so a correct bound is inert and the output must be the
        // frame itself. A bound that damaged this would be clamping to
        // something other than what the frames actually support.
        let (w, h) = (96usize, 72usize);
        let frame = disagreeing_bands(w, h, 4, 1);
        let cfg = MergeConfig { hull: Hull::PerLevel, ..MergeConfig::default() };
        let sizes = level_sizes(w, h, cfg.bands);
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        let var = vec![4.0f32; w * h];
        for _ in 0..5 {
            fws.next_frame();
            merge.add_frame(&[frame.as_slice()], &frame, &var, &mut fws);
        }
        let out = merge.finish(&mut Workspace::new(&sizes))[0].clone();
        let worst = out
            .iter()
            .zip(&frame)
            .fold(0.0f32, |a, (o, f)| a.max((o - f).abs()));
        assert!(worst < 1e-2, "identical frames did not reconstruct themselves: worst {worst} DN");
    }

    #[test]
    fn the_clamp_is_exact_on_a_single_frame() {
        // The clamp must be inert where the answer is known. With one frame the
        // hull is the frame itself, so `[lo, hi]` is a point and clamping to it
        // is either exact or catastrophic -- there is no middle.
        let (w, h) = (96, 72);
        let img = ramp(w, h);
        let sizes = level_sizes(w, h, MergeConfig::default().bands);
        let mut m = BandMerge::new(w, h, 1, MergeConfig::default());
        let mut fws = FrameWorkspace::new(&sizes, 1);
        m.add_frame(&[&img], &img, &vec![4.0f32; w * h], &mut fws);
        let out = m.finish(&mut Workspace::new(&sizes));
        for (i, (a, b)) in out[0].iter().zip(&img).enumerate() {
            assert_eq!(*a, *b, "pixel {i}: clamped to {a} from a single input of {b}");
        }
    }

    #[test]
    fn the_hull_survives_chunked_folding() {
        // `absorb` must fold the hull as exactly as it folds the sums, or a
        // chunked render and a serial one are different merges.
        let (w, h, nf) = (128usize, 96usize, 8usize);
        let frames: Vec<Vec<f32>> = (0..nf).map(|f| disagreeing_bands(w, h, nf, f)).collect();
        let cfg = MergeConfig::default();
        let sizes = level_sizes(w, h, cfg.bands);
        let var = vec![4.0f32; w * h];
        let fold = |range: std::ops::Range<usize>| {
            let mut m = BandMerge::new(w, h, 1, cfg);
            let mut fws = FrameWorkspace::new(&sizes, 1);
            for f in range {
                fws.next_frame();
                m.add_frame(&[frames[f].as_slice()], &frames[f], &var, &mut fws);
            }
            m
        };
        let serial = fold(0..nf);
        let mut chunked = fold(0..3);
        chunked.absorb(&fold(3..nf));
        for i in 0..w * h {
            assert_eq!(serial.lo[0][i], chunked.lo[0][i], "hull floor differs at {i}");
            assert_eq!(serial.hi[0][i], chunked.hi[0][i], "hull ceiling differs at {i}");
        }
    }

    #[test]
    fn the_clamped_fraction_reports_what_the_clamp_did() {
        // The diagnostic must move with the phenomenon, not merely exist.
        let (w, h, nf) = (192usize, 144usize, 8usize);
        let frames: Vec<Vec<f32>> = (0..nf).map(|f| disagreeing_bands(w, h, nf, f)).collect();
        let sizes = level_sizes(w, h, MergeConfig::default().bands);
        let mut m = BandMerge::new(w, h, 1, MergeConfig::default());
        let mut fws = FrameWorkspace::new(&sizes, 1);
        let var = vec![4.0f32; w * h];
        for f in &frames {
            fws.next_frame();
            m.add_frame(&[f.as_slice()], f, &var, &mut fws);
        }
        let frac = m.clamped_fraction(&mut Workspace::new(&sizes), 1.0);
        assert_eq!(frac.len(), 1);
        assert!(frac[0] > 0.0, "the clamp bound on this stack but reported {}", frac[0]);

        // And it is silent where nothing is wrong: identical frames have a
        // POINT hull, so the collapse's own float error is formally outside it.
        // That dust is why `clamped_fraction` takes a tolerance -- assert it is
        // dust, then assert the diagnostic is not fooled by it.
        let img = ramp(w, h);
        let mut flat = BandMerge::new(w, h, 1, MergeConfig::default());
        for _ in 0..4 {
            fws.next_frame();
            flat.add_frame(&[&img], &img, &var, &mut fws);
        }
        let raw = flat.clamped_fraction(&mut Workspace::new(&sizes), 0.0);
        let worst = flat
            .finish(&mut Workspace::new(&sizes))[0]
            .iter()
            .zip(&img)
            .fold(0.0f32, |a, (p, b)| a.max((p - b).abs()));
        assert!(worst < 1.0, "identical frames reconstructed {worst} DN off, which is not dust");
        assert!(raw[0] > 0.0, "no dust at tol=0, so this test is not exercising the tolerance");
        let q = flat.clamped_fraction(&mut Workspace::new(&sizes), 1.0);
        assert_eq!(q[0], 0.0, "the clamp bound on identical frames, reporting {}", q[0]);
    }

    #[test]
    fn the_hull_is_on_by_default() {
        assert_eq!(MergeConfig::default().hull, Hull::InputRange);
    }

    #[test]
    fn the_base_band_default_is_the_measured_one() {
        assert_eq!(MergeConfig::default().base, BaseBand::Mean);
    }

    /// The arm the default was measured against has to stay reachable and has
    /// to actually differ, or the comparison that chose the default was between
    /// a thing and itself.
    #[test]
    fn the_two_base_bands_are_not_the_same_merge() {
        let (w, h) = (64usize, 64usize);
        let sizes = level_sizes(w, h, 3);
        let var = vec![1.0f32; w * h];
        // Two frames that differ in overall LEVEL, and a detail patch that
        // gives the weighting something to prefer on one side of the frame.
        let mut a = vec![500.0f32; w * h];
        let mut b = vec![900.0f32; w * h];
        for y in 0..h {
            for x in 0..w / 2 {
                a[y * w + x] += if (x + y) % 2 == 0 { 300.0 } else { -300.0 };
            }
            for x in w / 2..w {
                b[y * w + x] += if (x + y) % 2 == 0 { 300.0 } else { -300.0 };
            }
        }
        let run = |base: BaseBand| {
            let cfg = MergeConfig { bands: 3, base, ..Default::default() };
            let mut merge = BandMerge::new(w, h, 1, cfg);
            let mut fws = FrameWorkspace::new(&sizes, 1);
            for f in [&a, &b] {
                fws.next_frame();
                merge.add_frame(&[f.as_slice()], f, &var, &mut fws);
            }
            merge.finish(&mut Workspace::new(&sizes))[0].clone()
        };
        let mean = run(BaseBand::Mean);
        let weighted = run(BaseBand::WeightedFromCoarsest);
        let diff: f32 = mean
            .iter()
            .zip(&weighted)
            .map(|(m, w)| (m - w).abs())
            .fold(0.0, f32::max);
        assert!(
            diff > 1.0,
            "the two base bands produced the same image (max |diff| = {diff}), \
             so the measurement that chose between them compared nothing"
        );
    }

    /// `mean_coarse` must ship at 0 until a ladder has chosen it, because any
    /// other value changes every rendered byte.
    #[test]
    fn the_mean_coarse_default_cannot_move_a_byte_unmeasured() {
        assert_eq!(MergeConfig::default().mean_coarse, DEFAULT_MEAN_COARSE);
        assert_eq!(DEFAULT_MEAN_COARSE, 0);
    }

    /// A knob that does not change the picture is not a knob. Without this, a
    /// sweep over `mean_coarse` that came back flat would be indistinguishable
    /// from the setting never having been plumbed through at all -- which is
    /// the exact failure this project has shipped three times.
    #[test]
    fn averaging_the_coarse_bands_is_not_the_same_merge() {
        let (w, h, bands) = (64usize, 64usize, 3usize);
        let (a, b) = two_frames_differing_in_level_and_detail(w, h);
        let run = |mean_coarse: usize| {
            run_merge(w, h, bands, &a, &b, MergeConfig {
                bands,
                mean_coarse,
                ..Default::default()
            })
        };
        let selected = run(0);
        let averaged = run(2);
        let diff: f32 = selected
            .iter()
            .zip(&averaged)
            .map(|(s, a)| (s - a).abs())
            .fold(0.0, f32::max);
        assert!(
            diff > 1.0,
            "averaging the two coarsest bands produced the same image as \
             selecting them (max |diff| = {diff}), so the knob is not wired"
        );
    }

    /// The claim in `DEFAULT_MEAN_COARSE` is that zeroing the weight yields
    /// *exactly* a mean rather than a very soft selection. That is a checkable
    /// property, so check it: average every Laplacian band, leave the base at
    /// its default `Mean`, and the reconstruction must be the arithmetic mean
    /// of the input frames to within round-trip error.
    ///
    /// If this ever fails, the fallback is not the fallback it is documented to
    /// be and every conclusion drawn from a `mean_coarse` sweep is void.
    #[test]
    fn averaging_every_band_reconstructs_the_plain_frame_mean() {
        let (w, h, bands) = (64usize, 64usize, 3usize);
        let (a, b) = two_frames_differing_in_level_and_detail(w, h);
        let got = run_merge(w, h, bands, &a, &b, MergeConfig {
            bands,
            // Every Laplacian band averaged; the base is `Mean` by default.
            mean_coarse: bands,
            ..Default::default()
        });
        let worst = got
            .iter()
            .enumerate()
            .map(|(i, g)| (g - 0.5 * (a[i] + b[i])).abs())
            .fold(0.0, f32::max);
        assert!(
            worst < 1e-2,
            "averaging every band did not reconstruct the frame mean \
             (max |diff| = {worst}), so the unweighted fallback is not a mean"
        );
    }

    /// Two frames that differ in overall LEVEL and carry detail on opposite
    /// halves, so both a level-sensitive and a selection-sensitive difference
    /// exist for a merge to get wrong.
    fn two_frames_differing_in_level_and_detail(w: usize, h: usize) -> (Vec<f32>, Vec<f32>) {
        let mut a = vec![500.0f32; w * h];
        let mut b = vec![900.0f32; w * h];
        for y in 0..h {
            for x in 0..w / 2 {
                a[y * w + x] += if (x + y) % 2 == 0 { 300.0 } else { -300.0 };
            }
            for x in w / 2..w {
                b[y * w + x] += if (x + y) % 2 == 0 { 300.0 } else { -300.0 };
            }
        }
        (a, b)
    }

    fn run_merge(
        w: usize,
        h: usize,
        bands: usize,
        a: &[f32],
        b: &[f32],
        cfg: MergeConfig,
    ) -> Vec<f32> {
        let sizes = level_sizes(w, h, bands);
        let var = vec![1.0f32; w * h];
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        for f in [a, b] {
            fws.next_frame();
            merge.add_frame(&[f], f, &var, &mut fws);
        }
        merge.finish(&mut Workspace::new(&sizes))[0].clone()
    }
}
