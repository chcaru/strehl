//! The focus measures under test, and the one thing they all have in common.
//!
//! Every measure computes a **raw response** `r(p)` from the black-subtracted
//! green luma and then returns `focus(p) = r(p) / max(sigma(L(p)), EPS)^degree`,
//! i.e. sigma-multiples, exactly as `strehl-core`'s shipped `FocusField` does
//! (which is the `degree = 1` case). `degree` is 2 for responses that are
//! quadratic in luma — Brenner, the structure tensor, variance-of-Laplacian,
//! local variance and DCT band energy — so that every family is normalised in
//! the same units of noise and "is it noise-normalised" is not a confound.
//!
//! Two measures deliberately opt out via [`Norm`], because the normalisation is
//! itself a term in the quantity M9 says drives argmax's noise excess: dividing
//! by `sigma(L(p))` puts a small centre tap on an operator whose response has
//! none. `tenengrad-w2-nonorm` and `tenengrad-w2-boxnorm` exist to measure that
//! term in isolation.
//!
//! # Support radius, and the unit it is in
//!
//! `support_radius` is in **plane pixels** and is a *radius*: the furthest luma
//! sample the response at `p` reads, measured from `p`. The diameter is
//! `2 * support_radius + 1`. Both are reported.

use crate::boxmax::{box_max_with, window_percentile, MaxScratch};
use strehl_core::boxfilter::box_mean;
use strehl_core::noise::NoiseModel;
use strehl_core::plane::PlaneGeometry;

/// Divisor floor, in DN. Identical to `strehl-core`'s `focus::SIGMA_EPS`, which
/// is private.
const SIGMA_EPS: f32 = 1e-3;

/// How the raw response is turned into sigma-multiples.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Norm {
    /// `sigma(L(p))` — the shipped convention. Reads the centre pixel.
    Pointwise,
    /// `sigma(box_mean_r(L)(p))` — the same noise model evaluated at a locally
    /// averaged signal level. Reads the centre pixel with weight
    /// `1/(2r+1)^2`, so it very nearly removes the normalisation's own centre
    /// tap without changing what the operator measures.
    BoxMean(usize),
    /// No normalisation at all. Exactly zero centre tap if the operator has
    /// none.
    None,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Family {
    Ring,
    Tenengrad,
    Sml,
    DilatedSml,
    Brenner,
    StructureTensor,
    VarLaplacian,
    LocalVariance,
    DctBand,
    MultiScaleBand,
    Control,
}

impl Family {
    pub fn as_str(self) -> &'static str {
        match self {
            Family::Ring => "ring",
            Family::Tenengrad => "tenengrad",
            Family::Sml => "sml",
            Family::DilatedSml => "dsml",
            Family::Brenner => "brenner",
            Family::StructureTensor => "stensor",
            Family::VarLaplacian => "varlap",
            Family::LocalVariance => "localvar",
            Family::DctBand => "dct",
            Family::MultiScaleBand => "msband",
            Family::Control => "control",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Role {
    /// A candidate for the default.
    Treatment,
    /// Must land at the null value of every statistic.
    NullControl,
    /// Must land at the extreme of a statistic by construction.
    PositiveControl,
    /// Added **after** the registered set was scored, to test whether the
    /// front is truncated by the registered sweep's edge. Reported separately
    /// and never used to resolve the registered decision rule.
    Extension,
}

impl Role {
    pub fn as_str(self) -> &'static str {
        match self {
            Role::Treatment => "treatment",
            Role::NullControl => "null",
            Role::PositiveControl => "positive",
            Role::Extension => "extension",
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub enum Kind {
    /// `|mean_inner - mean_outer|`. The shipped operator is `inner=1, outer=3`.
    Ring { inner: usize, outer: usize },
    /// 3x3 Sobel gradient, then a summation window. `squared` selects
    /// `Gx^2+Gy^2` (classical Tenengrad) over `sqrt(Gx^2+Gy^2)`.
    Tenengrad { window: usize, squared: bool },
    /// Nayar & Nakagawa's sum-modified Laplacian, then a summation window.
    Sml { window: usize },
    /// SML with the taps pushed `step` px apart and **no** summation window:
    /// large support, ~1 px of internal averaging, centre-tap fraction held
    /// roughly constant. M9's discriminator between "reads far" and "averages".
    DilatedSml { step: usize },
    /// Brenner gradient, squared, then a summation window. `symmetric` selects
    /// the central difference `L(+s) - L(-s)` (**zero centre tap**) over the
    /// classical forward difference `L(+s) - L(0)`.
    Brenner {
        step: usize,
        symmetric: bool,
        window: usize,
    },
    /// Largest eigenvalue of the window-averaged Sobel structure tensor.
    /// Quadratic in a zero-centre-tap derivative, so **zero centre tap**.
    StructureTensor { window: usize },
    /// Variance of the 4-neighbour Laplacian over a window.
    VarLaplacian { window: usize },
    /// Variance of the luma itself over a window.
    LocalVariance { window: usize },
    /// Energy of an 8x8 DCT-II outside its 4x4 low-frequency quadrant,
    /// evaluated at every pixel on a sliding window.
    DctBand,
    /// `sum_j |box_{r_j}(L) - box_{r_{j+1}}(L)|` over a dyadic radius ladder —
    /// an undecimated multi-scale band energy. `radii[0] == 0` makes the finest
    /// band read the bare pixel, which is what puts this family at both ends of
    /// the centre-tap axis.
    MultiScaleBand { radii: &'static [usize] },
    /// `r = L`. Centre-tap fraction 1 by construction, no focus content.
    CtlLuma,
    /// `r = 0`. Every frame ties, so the shipped tie-break elects frame 0.
    CtlConst,
    /// `r = hash(x, y, frame)`. Uniform random winner, zero coupling to the
    /// pixel's own noise — M2's placebo, generalised.
    CtlRandom,

    // ------------------------------------------------------------- M17 arms
    //
    // Every M17 arm shares the shipped operator's Sobel magnitude field `g`
    // and differs *only* in how `g` is aggregated over the window. That is
    // deliberate: fact 73's null is a property of the aggregator (the mean is
    // total-variation-conserving), not of the gradient, so an arm that also
    // changed the derivative would confound the two.
    /// Sobel magnitude, then a non-mean window aggregator. `Agg::Max` at
    /// `window = 13` is the reviewer's proposal.
    GradAgg { window: usize, agg: Agg },
    /// Sobel magnitude, then **both** `box_mean` and `box_max` over the same
    /// window, combined by `rule`. The dual proper.
    GradDual { window: usize, rule: DualRule },
    /// Sobel magnitude, then `box_mean` at **two** radii, combined by `rule`.
    /// SYNTHESIS question 19 candidate (b), "dual-radius".
    GradDualRadius {
        narrow: usize,
        wide: usize,
        rule: DualRule,
    },
    /// `sqrt(box_mean(|grad|^2))` — the **root mean square** gradient, degree 1.
    ///
    /// Exists as an internal consistency check, not as a separate candidate.
    /// At regulariser width 1 the winner map depends only on the ordering of
    /// the focus field across frames at each pixel, and
    /// `box_mean(g^2)/sigma^2 = (sqrt(box_mean(g^2))/sigma)^2` is a monotone
    /// map of this, so `tgrms-wN` must elect the **same** winners as
    /// `tenengrad-sq-wN` and produce bit-identical `excess_dn`. If it does not,
    /// the claim that candidate (c) is "the RMS gradient in disguise" is wrong.
    GradRms { window: usize },
}

/// A window aggregator that is not the mean.
#[derive(Clone, Copy, Debug)]
pub enum Agg {
    /// O(1) per pixel via van Herk / Gil-Werman. Not TV-conserving.
    Max,
    /// Exact `q`-quantile. **Not** O(1) — see `boxmax::window_percentile`.
    Pct(f32),
}

/// How two response fields are folded into one.
///
/// `Geo` and a plain product are the *same candidate*: `sqrt(ab)` is a
/// monotone map of `ab`, so at width 1 they elect bit-identical winners and
/// only the geometric mean is registered. `Geo` is the one carried because it
/// keeps the units of a gradient rather than squaring them, which keeps the
/// `degree = 1` sigma normalisation honest.
#[derive(Clone, Copy, Debug)]
pub enum DualRule {
    /// `sqrt(a * b)` — geometric mean. Zero if either term is zero.
    Geo,
    /// `a + b` — arithmetic sum, max-dominated wherever the max is large.
    Sum,
    /// `a + w * b` — the mean with the max as a small tie-break term. `w`
    /// small keeps the noise-quiet mean in charge except where the mean is
    /// flat, which is exactly the blind spot.
    Tie(f32),
    /// `max(a, b)` — pointwise larger of the two fields.
    Larger,
}

impl DualRule {
    fn fold(self, a: f32, b: f32) -> f32 {
        match self {
            DualRule::Geo => (a * b).max(0.0).sqrt(),
            DualRule::Sum => a + b,
            DualRule::Tie(w) => a + w * b,
            DualRule::Larger => a.max(b),
        }
    }
}

impl Kind {
    /// Power of sigma the raw response is divided by.
    pub fn degree(self) -> i32 {
        match self {
            Kind::Brenner { .. }
            | Kind::StructureTensor { .. }
            | Kind::VarLaplacian { .. }
            | Kind::LocalVariance { .. }
            | Kind::DctBand
            | Kind::Tenengrad { squared: true, .. } => 2,
            Kind::CtlConst | Kind::CtlRandom => 0,
            _ => 1,
        }
    }
}

#[derive(Clone, Debug)]
pub struct Measure {
    pub name: String,
    pub family: Family,
    pub role: Role,
    /// The measure's real spatial support radius, in plane px.
    pub support_radius: usize,
    pub kind: Kind,
    pub norm: Norm,
}

impl Measure {
    fn new(name: &str, family: Family, role: Role, support: usize, kind: Kind) -> Self {
        Self {
            name: name.to_string(),
            family,
            role,
            support_radius: support,
            kind,
            norm: Norm::Pointwise,
        }
    }

    fn with_norm(mut self, norm: Norm) -> Self {
        self.norm = norm;
        self
    }

    pub fn support_px(&self) -> usize {
        2 * self.support_radius + 1
    }

    pub fn norm_str(&self) -> String {
        match self.norm {
            Norm::Pointwise => "sigma".into(),
            Norm::BoxMean(r) => format!("sigma-box{}", 2 * r + 1),
            Norm::None => "none".into(),
        }
    }

    /// Focus field, in sigma-multiples, over the whole tile.
    ///
    /// The border policy is whatever `box_mean` and the replicate-clamped
    /// stencils do at the tile edge. That is deliberately *not* corrected for:
    /// the caller guarantees the region it reads back is inset from the tile
    /// edge by at least `support_radius + regulariser radius`, so no value it
    /// consumes was computed from a clamped window.
    pub fn compute(
        &self,
        luma: &[f32],
        geom: PlaneGeometry,
        noise: &NoiseModel,
        frame: usize,
        scratch: &mut Scratch,
        out: &mut [f32],
    ) {
        assert_eq!(luma.len(), geom.pixels());
        assert_eq!(out.len(), geom.pixels());
        scratch.ensure(geom.pixels());
        match self.kind {
            Kind::Ring { inner, outer } => {
                ring_response(
                    luma,
                    geom,
                    inner,
                    outer,
                    &mut scratch.a,
                    &mut scratch.b,
                    out,
                );
            }
            Kind::Tenengrad { window, squared } => {
                sobel(luma, geom, &mut scratch.a, &mut scratch.b);
                for (o, (gx, gy)) in scratch
                    .c
                    .iter_mut()
                    .zip(scratch.a.iter().zip(scratch.b.iter()))
                {
                    let e = gx * gx + gy * gy;
                    *o = if squared { e } else { e.sqrt() };
                }
                window_mean(&scratch.c, geom, window, &mut scratch.a, out);
            }
            Kind::Sml { window } => {
                modified_laplacian(luma, geom, 1, &mut scratch.a);
                window_mean(&scratch.a, geom, window, &mut scratch.b, out);
            }
            Kind::DilatedSml { step } => {
                modified_laplacian(luma, geom, step, out);
            }
            Kind::Brenner {
                step,
                symmetric,
                window,
            } => {
                brenner(luma, geom, step, symmetric, &mut scratch.a);
                window_mean(&scratch.a, geom, window, &mut scratch.b, out);
            }
            Kind::StructureTensor { window } => {
                structure_tensor(luma, geom, window, scratch, out);
            }
            Kind::VarLaplacian { window } => {
                let mut lap = vec![0.0f32; geom.pixels()];
                laplacian4(luma, geom, &mut lap);
                window_variance(&lap, geom, window, &mut scratch.a, &mut scratch.b, out);
            }
            Kind::LocalVariance { window } => {
                window_variance(luma, geom, window, &mut scratch.a, &mut scratch.b, out);
            }
            Kind::DctBand => dct8_band(luma, geom, out),
            Kind::MultiScaleBand { radii } => {
                multiscale_band(luma, geom, radii, scratch, out);
            }
            Kind::CtlLuma => out.copy_from_slice(luma),
            Kind::CtlConst => out.fill(0.0),
            Kind::CtlRandom => {
                for (i, o) in out.iter_mut().enumerate() {
                    *o = unit_hash(i as u64, frame as u64);
                }
            }
            Kind::GradAgg { window, agg } => {
                sobel_magnitude(luma, geom, &mut scratch.a, &mut scratch.b, &mut scratch.c);
                match agg {
                    Agg::Max => box_max_with(
                        &mut scratch.maxstate,
                        &scratch.c,
                        geom,
                        window,
                        &mut scratch.a,
                        out,
                    ),
                    Agg::Pct(q) => window_percentile(&scratch.c, geom, window, q, out),
                }
            }
            Kind::GradDual { window, rule } => {
                sobel_magnitude(luma, geom, &mut scratch.a, &mut scratch.b, &mut scratch.c);
                window_mean(&scratch.c, geom, window, &mut scratch.a, out);
                box_max_with(
                    &mut scratch.maxstate,
                    &scratch.c,
                    geom,
                    window,
                    &mut scratch.a,
                    &mut scratch.d,
                );
                for (o, mx) in out.iter_mut().zip(scratch.d.iter()) {
                    *o = rule.fold(*o, *mx);
                }
            }
            Kind::GradDualRadius { narrow, wide, rule } => {
                sobel_magnitude(luma, geom, &mut scratch.a, &mut scratch.b, &mut scratch.c);
                window_mean(&scratch.c, geom, narrow, &mut scratch.a, out);
                window_mean(&scratch.c, geom, wide, &mut scratch.a, &mut scratch.d);
                for (o, wf) in out.iter_mut().zip(scratch.d.iter()) {
                    *o = rule.fold(*o, *wf);
                }
            }
            Kind::GradRms { window } => {
                sobel(luma, geom, &mut scratch.a, &mut scratch.b);
                for (o, (gx, gy)) in scratch
                    .c
                    .iter_mut()
                    .zip(scratch.a.iter().zip(scratch.b.iter()))
                {
                    *o = gx * gx + gy * gy;
                }
                window_mean(&scratch.c, geom, window, &mut scratch.a, out);
                for o in out.iter_mut() {
                    *o = o.max(0.0).sqrt();
                }
            }
        }

        let degree = self.kind.degree();
        if degree == 0 {
            return;
        }
        match self.norm {
            Norm::None => {}
            Norm::Pointwise => {
                for (o, l) in out.iter_mut().zip(luma) {
                    let s = noise.green_luma_sigma(*l).max(SIGMA_EPS);
                    *o /= if degree == 2 { s * s } else { s };
                }
            }
            Norm::BoxMean(r) => {
                box_mean(luma, geom, r, &mut scratch.a, &mut scratch.b);
                for (o, l) in out.iter_mut().zip(scratch.b.iter()) {
                    let s = noise.green_luma_sigma(*l).max(SIGMA_EPS);
                    *o /= if degree == 2 { s * s } else { s };
                }
            }
        }
    }
}

/// Reusable f32 buffers, so a sweep does not allocate per frame.
#[derive(Default)]
pub struct Scratch {
    a: Vec<f32>,
    b: Vec<f32>,
    c: Vec<f32>,
    /// M17's second response field, for the arms that hold two at once.
    d: Vec<f32>,
    /// M17's vHGW block arrays, hoisted so a max costs no allocation per frame.
    maxstate: MaxScratch,
}

impl Scratch {
    fn ensure(&mut self, n: usize) {
        for v in [&mut self.a, &mut self.b, &mut self.c, &mut self.d] {
            if v.len() != n {
                v.resize(n, 0.0);
            }
        }
    }
}

/// `sqrt(Gx^2 + Gy^2)` from the same 3x3 Sobel the shipped operator uses.
///
/// Factored out so every M17 arm demonstrably shares one gradient field with
/// `Kind::Tenengrad { squared: false }`; `gradient_field_is_shared_with_the_status_quo`
/// pins that by equality rather than by inspection.
fn sobel_magnitude(
    luma: &[f32],
    geom: PlaneGeometry,
    gx: &mut [f32],
    gy: &mut [f32],
    out: &mut [f32],
) {
    sobel(luma, geom, gx, gy);
    for (o, (x, y)) in out.iter_mut().zip(gx.iter().zip(gy.iter())) {
        *o = (x * x + y * y).sqrt();
    }
}

// ------------------------------------------------------------------ operators

fn ring_response(
    luma: &[f32],
    geom: PlaneGeometry,
    inner: usize,
    outer: usize,
    tmp: &mut [f32],
    outer_mean: &mut [f32],
    out: &mut [f32],
) {
    box_mean(luma, geom, inner, tmp, out);
    box_mean(luma, geom, outer, tmp, outer_mean);
    for (o, a) in out.iter_mut().zip(outer_mean.iter()) {
        *o = (*o - *a).abs();
    }
}

/// `mean` over a `(2*radius+1)^2` window, or the identity at radius 0.
fn window_mean(
    src: &[f32],
    geom: PlaneGeometry,
    radius: usize,
    scratch: &mut [f32],
    out: &mut [f32],
) {
    if radius == 0 {
        out.copy_from_slice(src);
    } else {
        box_mean(src, geom, radius, scratch, out);
    }
}

/// `E[x^2] - E[x]^2` over a `(2*radius+1)^2` window. Zero at radius 0.
fn window_variance(
    src: &[f32],
    geom: PlaneGeometry,
    radius: usize,
    tmp: &mut [f32],
    mean: &mut [f32],
    out: &mut [f32],
) {
    if radius == 0 {
        out.fill(0.0);
        return;
    }
    box_mean(src, geom, radius, tmp, mean);
    let sq: Vec<f32> = src.iter().map(|v| v * v).collect();
    box_mean(&sq, geom, radius, tmp, out);
    for (o, m) in out.iter_mut().zip(mean.iter()) {
        *o = (*o - m * m).max(0.0);
    }
}

#[inline]
fn clamped(luma: &[f32], geom: PlaneGeometry, x: isize, y: isize) -> f32 {
    let x = x.clamp(0, geom.width as isize - 1) as usize;
    let y = y.clamp(0, geom.height as isize - 1) as usize;
    luma[y * geom.width + x]
}

/// 3x3 Sobel components, replicate-clamped at the border.
///
/// The `/8` normalisation is cosmetic: the merge only ever compares a measure
/// against *itself* on other frames at the same pixel, and both the regulariser
/// and the argmax are invariant to a positive constant scale. It is applied so
/// that the response is in DN/px and the `degree = 2` normalisation is in the
/// same units as everything else.
fn sobel(luma: &[f32], geom: PlaneGeometry, gx_out: &mut [f32], gy_out: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            let at = |dx: isize, dy: isize| clamped(luma, geom, xi + dx, yi + dy);
            let gx =
                at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1);
            let gy =
                at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1);
            gx_out[y * w + x] = 0.125 * gx;
            gy_out[y * w + x] = 0.125 * gy;
        }
    }
}

/// Nayar & Nakagawa's modified Laplacian with the taps `step` px out:
/// `|2L - L(-s,0) - L(+s,0)| + |2L - L(0,-s) - L(0,+s)|`.
fn modified_laplacian(luma: &[f32], geom: PlaneGeometry, step: usize, out: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    let s = step as isize;
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            let c = 2.0 * clamped(luma, geom, xi, yi);
            let hx = (c - clamped(luma, geom, xi - s, yi) - clamped(luma, geom, xi + s, yi)).abs();
            let hy = (c - clamped(luma, geom, xi, yi - s) - clamped(luma, geom, xi, yi + s)).abs();
            out[y * w + x] = hx + hy;
        }
    }
}

/// The 4-neighbour Laplacian `4L - sum of the 4-neighbours`.
fn laplacian4(luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            out[y * w + x] = 4.0 * clamped(luma, geom, xi, yi)
                - clamped(luma, geom, xi - 1, yi)
                - clamped(luma, geom, xi + 1, yi)
                - clamped(luma, geom, xi, yi - 1)
                - clamped(luma, geom, xi, yi + 1);
        }
    }
}

/// Brenner's squared gradient. `symmetric` makes it a central difference, which
/// removes the centre tap exactly.
fn brenner(luma: &[f32], geom: PlaneGeometry, step: usize, symmetric: bool, out: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    let s = step as isize;
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            let (dx, dy) = if symmetric {
                (
                    clamped(luma, geom, xi + s, yi) - clamped(luma, geom, xi - s, yi),
                    clamped(luma, geom, xi, yi + s) - clamped(luma, geom, xi, yi - s),
                )
            } else {
                (
                    clamped(luma, geom, xi + s, yi) - clamped(luma, geom, xi, yi),
                    clamped(luma, geom, xi, yi + s) - clamped(luma, geom, xi, yi),
                )
            };
            out[y * w + x] = dx * dx + dy * dy;
        }
    }
}

/// Largest eigenvalue of the window-averaged Sobel structure tensor.
fn structure_tensor(
    luma: &[f32],
    geom: PlaneGeometry,
    window: usize,
    scratch: &mut Scratch,
    out: &mut [f32],
) {
    sobel(luma, geom, &mut scratch.a, &mut scratch.b);
    let n = geom.pixels();
    let mut jxx = vec![0.0f32; n];
    let mut jxy = vec![0.0f32; n];
    let mut jyy = vec![0.0f32; n];
    for i in 0..n {
        let (gx, gy) = (scratch.a[i], scratch.b[i]);
        jxx[i] = gx * gx;
        jxy[i] = gx * gy;
        jyy[i] = gy * gy;
    }
    let mut sxx = vec![0.0f32; n];
    let mut sxy = vec![0.0f32; n];
    let mut syy = vec![0.0f32; n];
    window_mean(&jxx, geom, window, &mut scratch.c, &mut sxx);
    window_mean(&jxy, geom, window, &mut scratch.c, &mut sxy);
    window_mean(&jyy, geom, window, &mut scratch.c, &mut syy);
    for i in 0..n {
        let m = 0.5 * (sxx[i] + syy[i]);
        let d = 0.5 * (sxx[i] - syy[i]);
        out[i] = m + (d * d + sxy[i] * sxy[i]).sqrt();
    }
}

/// `sum_j |box_{r_j}(L) - box_{r_{j+1}}(L)|`.
fn multiscale_band(
    luma: &[f32],
    geom: PlaneGeometry,
    radii: &[usize],
    scratch: &mut Scratch,
    out: &mut [f32],
) {
    assert!(radii.len() >= 2);
    out.fill(0.0);
    let n = geom.pixels();
    let mut fine = vec![0.0f32; n];
    let mut coarse = vec![0.0f32; n];
    window_mean(luma, geom, radii[0], &mut scratch.a, &mut fine);
    for r in &radii[1..] {
        window_mean(luma, geom, *r, &mut scratch.a, &mut coarse);
        for ((o, f), c) in out.iter_mut().zip(fine.iter()).zip(coarse.iter()) {
            *o += (f - c).abs();
        }
        fine.copy_from_slice(&coarse);
    }
}

/// 8x8 orthonormal DCT-II basis vector `u`, sampled at `n = 0..8`.
fn dct8_basis(u: usize, n: usize) -> f32 {
    let a = if u == 0 {
        (1.0f64 / 8.0).sqrt()
    } else {
        (2.0f64 / 8.0).sqrt()
    };
    (a * ((std::f64::consts::PI * (2 * n + 1) as f64 * u as f64) / 16.0).cos()) as f32
}

/// Separable 8-tap correlation on the window `[-4, +3]` in both axes.
fn sep8(src: &[f32], geom: PlaneGeometry, row: &[f32; 8], col: &[f32; 8], out: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    let mut tmp = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut s = 0.0f32;
            for (m, t) in row.iter().enumerate() {
                s += t * clamped(src, geom, x as isize + m as isize - 4, y as isize);
            }
            tmp[y * w + x] = s;
        }
    }
    for y in 0..h {
        for x in 0..w {
            let mut s = 0.0f32;
            for (n, t) in col.iter().enumerate() {
                s += t * clamped(&tmp, geom, x as isize, y as isize + n as isize - 4);
            }
            out[y * w + x] = s;
        }
    }
}

/// Energy of the 8x8 DCT outside its 4x4 low-frequency quadrant, per pixel.
///
/// Parseval for an orthonormal DCT gives `sum_uv X_uv^2 = sum_window L^2`, so
/// the band energy is the total minus the low quadrant. That costs 17 separable
/// passes instead of 64 coefficients.
fn dct8_band(luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
    let n = geom.pixels();
    let ones = [1.0f32; 8];
    let sq: Vec<f32> = luma.iter().map(|v| v * v).collect();
    sep8(&sq, geom, &ones, &ones, out);

    let mut coeff = vec![0.0f32; n];
    for u in 0..4 {
        let bu: [f32; 8] = std::array::from_fn(|m| dct8_basis(u, m));
        for v in 0..4 {
            let bv: [f32; 8] = std::array::from_fn(|m| dct8_basis(v, m));
            sep8(luma, geom, &bu, &bv, &mut coeff);
            for (o, c) in out.iter_mut().zip(coeff.iter()) {
                *o -= c * c;
            }
        }
    }
    for o in out.iter_mut() {
        *o = o.max(0.0);
    }
}

/// A deterministic uniform in `[0, 1)` from two integers. `splitmix64`.
fn unit_hash(a: u64, b: u64) -> f32 {
    let mut z = a
        .wrapping_mul(0x9E37_79B9_7F4A_7C15)
        .wrapping_add(b.wrapping_mul(0xBF58_476D_1CE4_E5B9))
        .wrapping_add(0x94D0_49BB_1331_11EB);
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^= z >> 31;
    ((z >> 11) as f64 / (1u64 << 53) as f64) as f32
}

// -------------------------------------------------------------------- design

const MSBAND_LO: [usize; 4] = [1, 2, 4, 8];
const MSBAND_HI: [usize; 4] = [0, 1, 2, 4];

/// Every operator in the bake-off.
///
/// The set spans the centre-tap axis M9 identified from `phi ~ 0` (Sobel,
/// structure tensor, symmetric Brenner) to `phi = 1` (the luma control), and
/// spans the support axis from 1 px to 12 px inside several families, so that
/// neither axis is confounded with the other.
pub fn design() -> Vec<Measure> {
    let mut v = Vec::new();

    // Ring family: the incumbent's own two-parameter grid, so the
    // INNER_RADIUS / OUTER_RADIUS question is answered on its own terms.
    for (inner, outer) in [
        (0usize, 1usize),
        (0, 3),
        (1, 2),
        (1, 3),
        (1, 5),
        (2, 4),
        (2, 6),
        (3, 8),
        (4, 12),
    ] {
        v.push(Measure::new(
            &format!("ring-{inner}-{outer}"),
            Family::Ring,
            Role::Treatment,
            outer,
            Kind::Ring { inner, outer },
        ));
    }

    // Sum-modified Laplacian, and the dilated variant that holds phi roughly
    // fixed while support sweeps.
    for window in [0usize, 2, 5] {
        v.push(Measure::new(
            &format!("sml-w{window}"),
            Family::Sml,
            Role::Treatment,
            1 + window,
            Kind::Sml { window },
        ));
    }
    for step in [1usize, 3, 6] {
        v.push(Measure::new(
            &format!("dsml-s{step}"),
            Family::DilatedSml,
            Role::Treatment,
            step,
            Kind::DilatedSml { step },
        ));
    }

    // Tenengrad / Sobel: the zero-centre-tap end of the axis.
    for window in [0usize, 2, 5] {
        v.push(Measure::new(
            &format!("tenengrad-w{window}"),
            Family::Tenengrad,
            Role::Treatment,
            1 + window,
            Kind::Tenengrad {
                window,
                squared: false,
            },
        ));
    }
    v.push(Measure::new(
        "tenengrad-sq-w2",
        Family::Tenengrad,
        Role::Treatment,
        3,
        Kind::Tenengrad {
            window: 2,
            squared: true,
        },
    ));

    // Brenner, both signs of the centre-tap question in one family.
    for (step, symmetric, window) in [
        (2usize, false, 2usize),
        (1, true, 2),
        (2, true, 2),
        (2, true, 5),
    ] {
        let tag = if symmetric { "sym" } else { "fwd" };
        v.push(Measure::new(
            &format!("brenner-{tag}-s{step}-w{window}"),
            Family::Brenner,
            Role::Treatment,
            step + window,
            Kind::Brenner {
                step,
                symmetric,
                window,
            },
        ));
    }

    // Structure tensor: zero centre tap, but a genuinely different statistic
    // from gradient energy — it is orientation-selective.
    for window in [2usize, 5] {
        v.push(Measure::new(
            &format!("stensor-w{window}"),
            Family::StructureTensor,
            Role::Treatment,
            1 + window,
            Kind::StructureTensor { window },
        ));
    }

    // Variance families and band energies.
    v.push(Measure::new(
        "varlap-w2",
        Family::VarLaplacian,
        Role::Treatment,
        3,
        Kind::VarLaplacian { window: 2 },
    ));
    v.push(Measure::new(
        "varlap-w5",
        Family::VarLaplacian,
        Role::Treatment,
        6,
        Kind::VarLaplacian { window: 5 },
    ));
    v.push(Measure::new(
        "localvar-w2",
        Family::LocalVariance,
        Role::Treatment,
        2,
        Kind::LocalVariance { window: 2 },
    ));
    v.push(Measure::new(
        "dct8-hi",
        Family::DctBand,
        Role::Treatment,
        4,
        Kind::DctBand,
    ));
    v.push(Measure::new(
        "msband-lo",
        Family::MultiScaleBand,
        Role::Treatment,
        8,
        Kind::MultiScaleBand { radii: &MSBAND_LO },
    ));
    v.push(Measure::new(
        "msband-hi",
        Family::MultiScaleBand,
        Role::Treatment,
        4,
        Kind::MultiScaleBand { radii: &MSBAND_HI },
    ));

    // Normalisation variants. The operator is held fixed and only the divisor
    // changes, so any movement is attributable to the normalisation alone.
    v.push(
        Measure::new(
            "ring-1-3-nonorm",
            Family::Ring,
            Role::Treatment,
            3,
            Kind::Ring { inner: 1, outer: 3 },
        )
        .with_norm(Norm::None),
    );
    v.push(
        Measure::new(
            "tenengrad-w2-nonorm",
            Family::Tenengrad,
            Role::Treatment,
            3,
            Kind::Tenengrad {
                window: 2,
                squared: false,
            },
        )
        .with_norm(Norm::None),
    );
    v.push(
        Measure::new(
            "tenengrad-w2-boxnorm",
            Family::Tenengrad,
            Role::Treatment,
            3,
            Kind::Tenengrad {
                window: 2,
                squared: false,
            },
        )
        .with_norm(Norm::BoxMean(2)),
    );

    // Amendment A1 (pre-registration §8): the strictly-zero-phi operators.
    //
    // Every other zero-centre-tap candidate above is either windowed or
    // pointwise-normalised, and **both of those re-introduce a centre tap** --
    // the window mean because it averages neighbours' responses, each of which
    // does depend on the centre pixel, and the `sigma(L(p))` divisor because it
    // is a function of the centre pixel by definition. These two are the only
    // members of the set with phi identically 0 by construction, and they are
    // what the "is a zero-centre-tap operator viable as the default?" question
    // actually rests on.
    v.push(
        Measure::new(
            "tenengrad-w0-nonorm",
            Family::Tenengrad,
            Role::Treatment,
            1,
            Kind::Tenengrad {
                window: 0,
                squared: false,
            },
        )
        .with_norm(Norm::None),
    );
    v.push(
        Measure::new(
            "brenner-sym-s2-w0-nonorm",
            Family::Brenner,
            Role::Treatment,
            2,
            Kind::Brenner {
                step: 2,
                symmetric: true,
                window: 0,
            },
        )
        .with_norm(Norm::None),
    );

    // Amendment A4 (pre-registration §8): the support axis was truncated.
    //
    // On the registered set the best-selectivity operators all sat at the
    // widest window sampled (w5), i.e. at the **edge of the sweep** -- exactly
    // the failure mode SYNTHESIS fact 36 warns about. These extend the axis so
    // the front can be seen to turn over, or seen not to. They are POST-HOC:
    // the registered ruling is resolved on the registered set alone and these
    // are reported separately.
    for window in [8usize, 11] {
        v.push(Measure::new(
            &format!("tenengrad-w{window}"),
            Family::Tenengrad,
            Role::Extension,
            1 + window,
            Kind::Tenengrad {
                window,
                squared: false,
            },
        ));
        v.push(Measure::new(
            &format!("stensor-w{window}"),
            Family::StructureTensor,
            Role::Extension,
            1 + window,
            Kind::StructureTensor { window },
        ));
        v.push(Measure::new(
            &format!("brenner-sym-s2-w{window}"),
            Family::Brenner,
            Role::Extension,
            2 + window,
            Kind::Brenner {
                step: 2,
                symmetric: true,
                window,
            },
        ));
        v.push(Measure::new(
            &format!("sml-w{window}"),
            Family::Sml,
            Role::Extension,
            1 + window,
            Kind::Sml { window },
        ));
    }

    // Controls.
    v.push(Measure::new(
        "ctl-const",
        Family::Control,
        Role::NullControl,
        0,
        Kind::CtlConst,
    ));
    v.push(Measure::new(
        "ctl-random",
        Family::Control,
        Role::NullControl,
        0,
        Kind::CtlRandom,
    ));
    v.push(Measure::new(
        "ctl-luma",
        Family::Control,
        Role::PositiveControl,
        0,
        Kind::CtlLuma,
    ));

    v
}

/// The largest support radius in a measure set, which sets the tile margin.
pub fn max_support(measures: &[Measure]) -> usize {
    measures.iter().map(|m| m.support_radius).max().unwrap_or(0)
}

// ------------------------------------------------------- M13: dynamic windows
//
// M11's `design()` is a fixed list, because M11 was comparing operator families
// at a handful of windows. M13 is sweeping *one* operator's window over a range
// whose whole point is to be extended until the objective turns over, so the
// window can no longer be baked into a literal list.
//
// `parse()` builds any member of the sweep from its M11 name, so every operator
// M13 measures carries the *same* name and the *same* kernel as M11's, and the
// two milestones' CSVs can be joined on the `measure` column without a mapping
// table. Names M11 already defines resolve to M11's own entry, so nothing that
// existed can silently change meaning.

/// Build a measure from its name, extending M11's naming scheme to any window.
///
/// Recognised: everything in [`design`] by exact name, plus `tenengrad-wN`,
/// `tenengrad-wN-nonorm`, `stensor-wN`, `sml-wN`, `brenner-sym-sS-wN`,
/// `varlap-wN`, `localvar-wN` and `ring-I-O` for arbitrary N, S, I, O.
pub fn parse(name: &str) -> Option<Measure> {
    if let Some(m) = design().into_iter().find(|m| m.name == name) {
        return Some(m);
    }
    let (stem, norm) = match name.strip_suffix("-nonorm") {
        Some(s) => (s, Norm::None),
        None => (name, Norm::Pointwise),
    };
    let win = |s: &str| -> Option<usize> { s.strip_prefix('w')?.parse().ok() };

    let parts: Vec<&str> = stem.split('-').collect();
    let m = match parts.as_slice() {
        ["tenengrad", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Tenengrad,
                Role::Extension,
                1 + window,
                Kind::Tenengrad {
                    window,
                    squared: false,
                },
            )
        }
        ["stensor", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::StructureTensor,
                Role::Extension,
                1 + window,
                Kind::StructureTensor { window },
            )
        }
        ["sml", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Sml,
                Role::Extension,
                1 + window,
                Kind::Sml { window },
            )
        }
        ["varlap", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::VarLaplacian,
                Role::Extension,
                1 + window,
                Kind::VarLaplacian { window },
            )
        }
        ["localvar", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::LocalVariance,
                Role::Extension,
                window,
                Kind::LocalVariance { window },
            )
        }
        ["brenner", tag, s, w] => {
            let symmetric = match *tag {
                "sym" => true,
                "fwd" => false,
                _ => return None,
            };
            let step: usize = s.strip_prefix('s')?.parse().ok()?;
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Brenner,
                Role::Extension,
                step + window,
                Kind::Brenner {
                    step,
                    symmetric,
                    window,
                },
            )
        }
        ["ring", i, o] => {
            let inner: usize = i.parse().ok()?;
            let outer: usize = o.parse().ok()?;
            Measure::new(
                stem,
                Family::Ring,
                Role::Extension,
                outer,
                Kind::Ring { inner, outer },
            )
        }

        // ------------------------------------------------------ M17 arms
        //
        // Named `tg*` rather than `tenengrad-*` on purpose: the `tenengrad-wN`
        // namespace is M11's and M13's and its rows are joined across
        // milestones on the `measure` column, so an M17 arm must not be able
        // to collide with one. `tenengrad-w13` still resolves to exactly the
        // shipped operator, and that is what the gates check.
        // `tgmax-wN` — box max of |grad|.
        ["tgmax", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Tenengrad,
                Role::Extension,
                1 + window,
                Kind::GradAgg {
                    window,
                    agg: Agg::Max,
                },
            )
        }
        // `tgpQQ-wN` — exact QQ-th percentile of |grad|, e.g. `tgp95-w13`.
        [p, w] if p.starts_with("tgp") => {
            let q: f32 = p.strip_prefix("tgp")?.parse::<f32>().ok()? / 100.0;
            if !(0.0..=1.0).contains(&q) {
                return None;
            }
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Tenengrad,
                Role::Extension,
                1 + window,
                Kind::GradAgg {
                    window,
                    agg: Agg::Pct(q),
                },
            )
        }
        // `tgdual-RULE-wN` — mean and max over the same window.
        ["tgdual", rule, w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Tenengrad,
                Role::Extension,
                1 + window,
                Kind::GradDual {
                    window,
                    rule: dual_rule(rule)?,
                },
            )
        }
        // `tgrad-RULE-wN-wM` — mean at two radii. Question 19 candidate (b).
        ["tgrad", rule, n, w] => {
            let narrow = win(n)?;
            let wide = win(w)?;
            Measure::new(
                stem,
                Family::Tenengrad,
                Role::Extension,
                1 + narrow.max(wide),
                Kind::GradDualRadius {
                    narrow,
                    wide,
                    rule: dual_rule(rule)?,
                },
            )
        }
        // `tenengrad-sq-wN` — question 19 candidate (c). `degree() == 2`.
        ["tenengrad", "sq", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Tenengrad,
                Role::Extension,
                1 + window,
                Kind::Tenengrad {
                    window,
                    squared: true,
                },
            )
        }
        // `tgrms-wN` — consistency arm for candidate (c). `degree() == 1`.
        ["tgrms", w] => {
            let window = win(w)?;
            Measure::new(
                stem,
                Family::Tenengrad,
                Role::Extension,
                1 + window,
                Kind::GradRms { window },
            )
        }
        _ => return None,
    };
    let mut m = m.with_norm(norm);
    m.name = name.to_string();
    Some(m)
}

/// `geo` / `sum` / `tieWW` / `larger`, where `WW` is the weight in percent.
fn dual_rule(s: &str) -> Option<DualRule> {
    match s {
        "geo" => Some(DualRule::Geo),
        "sum" => Some(DualRule::Sum),
        "larger" => Some(DualRule::Larger),
        _ => {
            let pct: f32 = s.strip_prefix("tie")?.parse().ok()?;
            Some(DualRule::Tie(pct / 100.0))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_agrees_with_the_registered_design_where_they_overlap() {
        for m in design() {
            let p = parse(&m.name).expect("every designed name must parse");
            assert_eq!(p.name, m.name);
            assert_eq!(p.support_radius, m.support_radius);
            assert_eq!(p.norm, m.norm);
        }
    }

    #[test]
    fn parse_extends_the_window_axis_consistently() {
        for w in [0usize, 1, 5, 11, 17, 40, 64] {
            let m = parse(&format!("tenengrad-w{w}")).unwrap();
            assert_eq!(m.support_radius, 1 + w);
            assert!(matches!(m.kind, Kind::Tenengrad { window, .. } if window == w));
        }
        assert_eq!(parse("tenengrad-w7-nonorm").unwrap().norm, Norm::None);
        assert!(parse("nonsense-w3").is_none());
    }
}
