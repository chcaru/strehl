//! The focus measures under test, and the one thing they all have in common.
//!
//! Every measure here computes a **raw response** `r(p)` from the black-
//! subtracted green luma and then returns `focus(p) = r(p) / max(sigma(L(p)),
//! EPS)`, i.e. sigma-multiples, exactly as `strehl-core`'s shipped
//! `FocusField` does and as SYNTHESIS §3.4.1 B4 requires. Normalising every
//! family the same way removes "is it noise-normalised" as a confound, leaving
//! only the two axes M9 is sweeping: **spatial support** and **operator
//! family**.
//!
//! # Support radius, and the unit it is in
//!
//! `support_radius` is in **plane pixels** and is a *radius*: the furthest
//! luma sample the response at `p` reads, measured from `p`. The diameter,
//! which is what a `support_px()` method would most naturally return, is
//! `2 * support_radius + 1`. Both are reported in the CSV, because this
//! project has already published a radius as a diameter once (SYNTHESIS §3.4.1
//! B1's "39 px", which was a Euclidean displacement quoted as a rectangle
//! halo).

use strehl_core::boxfilter::box_mean;
use strehl_core::noise::NoiseModel;
use strehl_core::plane::PlaneGeometry;

/// Divisor floor, in DN. Identical to `strehl-core`'s `focus::SIGMA_EPS`, which
/// is private.
const SIGMA_EPS: f32 = 1e-3;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Family {
    /// Difference of two box means. The shipped operator.
    Ring,
    /// Sobel gradient magnitude, then a summation window.
    Tenengrad,
    /// Sum-modified Laplacian, then a summation window.
    Sml,
    /// Sum-modified Laplacian with the taps pushed `step` px apart and **no**
    /// summation window: large declared support, ~1 px of internal averaging.
    DilatedSml,
}

impl Family {
    pub fn as_str(self) -> &'static str {
        match self {
            Family::Ring => "ring",
            Family::Tenengrad => "tenengrad",
            Family::Sml => "sml",
            Family::DilatedSml => "dsml",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Role {
    /// Part of the 4 x 4 crossed design that answers the question.
    Treatment,
    /// Same operator, different *declared* support. The statistic must not
    /// manufacture a correlation out of the declaration alone.
    NullControl,
    /// Support-dependence planted by construction. The statistic must fire.
    PositiveControl,
}

impl Role {
    pub fn as_str(self) -> &'static str {
        match self {
            Role::Treatment => "treatment",
            Role::NullControl => "null",
            Role::PositiveControl => "positive",
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub enum Kind {
    /// `|mean_inner - mean_outer|`. Support radius = `outer`.
    Ring { inner: usize, outer: usize },
    /// `mean_window(|grad|)` from a 3x3 Sobel. Support radius = `1 + window`.
    Tenengrad { window: usize },
    /// `mean_window(ML)`. Support radius = `1 + window`.
    Sml { window: usize },
    /// `ML` with taps at +/- `step`, no window. Support radius = `step`.
    DilatedSml { step: usize },
    /// `mean_extra(|mean_inner - mean_outer|)`. Support radius = `outer +
    /// extra`. The positive control: internal averaging is dialled directly.
    RingSmoothed {
        inner: usize,
        outer: usize,
        extra: usize,
    },
}

#[derive(Clone, Debug)]
pub struct Measure {
    pub name: String,
    pub family: Family,
    pub role: Role,
    /// The measure's real spatial support radius, in plane px.
    pub support_radius: usize,
    /// What `support_px()` would report, as a radius. Equal to
    /// `support_radius` for everything except the null control, which is
    /// deliberately mislabelled.
    pub declared_radius: usize,
    pub kind: Kind,
}

impl Measure {
    fn new(name: &str, family: Family, role: Role, support: usize, kind: Kind) -> Self {
        Self {
            name: name.to_string(),
            family,
            role,
            support_radius: support,
            declared_radius: support,
            kind,
        }
    }

    pub fn support_px(&self) -> usize {
        2 * self.support_radius + 1
    }

    pub fn declared_px(&self) -> usize {
        2 * self.declared_radius + 1
    }

    /// Focus field, in sigma-multiples, over the whole tile.
    ///
    /// The border policy is whatever `box_mean` and the replicate-clamped
    /// stencils do at the tile edge. That is deliberately *not* corrected for:
    /// the caller guarantees the region it reads back is inset from the tile
    /// edge by at least `support_radius + regulariser radius`, so no value it
    /// consumes was computed from a clamped window. `Tile::margin` is what
    /// enforces it.
    pub fn compute(
        &self,
        luma: &[f32],
        geom: PlaneGeometry,
        noise: &NoiseModel,
        scratch: &mut Scratch,
        out: &mut [f32],
    ) {
        assert_eq!(luma.len(), geom.pixels());
        assert_eq!(out.len(), geom.pixels());
        scratch.ensure(geom.pixels());
        let Scratch { a, b, c } = scratch;
        match self.kind {
            Kind::Ring { inner, outer } => {
                ring_response(luma, geom, inner, outer, a, b, out);
            }
            Kind::Tenengrad { window } => {
                tenengrad_magnitude(luma, geom, a);
                window_mean(a, geom, window, b, out);
            }
            Kind::Sml { window } => {
                modified_laplacian(luma, geom, 1, a);
                window_mean(a, geom, window, b, out);
            }
            Kind::DilatedSml { step } => {
                modified_laplacian(luma, geom, step, out);
            }
            Kind::RingSmoothed {
                inner,
                outer,
                extra,
            } => {
                ring_response(luma, geom, inner, outer, a, b, c);
                window_mean(c, geom, extra, a, out);
            }
        }
        for (o, l) in out.iter_mut().zip(luma) {
            *o /= noise.green_luma_sigma(*l).max(SIGMA_EPS);
        }
    }
}

/// Reusable f32 buffers, so a sweep does not allocate per frame.
#[derive(Default)]
pub struct Scratch {
    a: Vec<f32>,
    b: Vec<f32>,
    c: Vec<f32>,
}

impl Scratch {
    fn ensure(&mut self, n: usize) {
        for v in [&mut self.a, &mut self.b, &mut self.c] {
            if v.len() != n {
                v.resize(n, 0.0);
            }
        }
    }
}

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

/// 3x3 Sobel gradient magnitude, replicate-clamped at the border.
///
/// The `/8` normalisation is cosmetic: the merge only ever compares this
/// measure against *itself* on other frames at the same pixel, and both the
/// regulariser and the argmax are invariant to a positive constant scale.
fn tenengrad_magnitude(luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    let at = |x: isize, y: isize| -> f32 {
        let x = x.clamp(0, w as isize - 1) as usize;
        let y = y.clamp(0, h as isize - 1) as usize;
        luma[y * w + x]
    };
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            let gx = at(xi + 1, yi - 1) + 2.0 * at(xi + 1, yi) + at(xi + 1, yi + 1)
                - at(xi - 1, yi - 1)
                - 2.0 * at(xi - 1, yi)
                - at(xi - 1, yi + 1);
            let gy = at(xi - 1, yi + 1) + 2.0 * at(xi, yi + 1) + at(xi + 1, yi + 1)
                - at(xi - 1, yi - 1)
                - 2.0 * at(xi, yi - 1)
                - at(xi + 1, yi - 1);
            out[y * w + x] = 0.125 * (gx * gx + gy * gy).sqrt();
        }
    }
}

/// Nayar & Nakagawa's modified Laplacian with the taps `step` px out:
/// `|2L - L(-s,0) - L(+s,0)| + |2L - L(0,-s) - L(0,+s)|`.
fn modified_laplacian(luma: &[f32], geom: PlaneGeometry, step: usize, out: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    let s = step as isize;
    let at = |x: isize, y: isize| -> f32 {
        let x = x.clamp(0, w as isize - 1) as usize;
        let y = y.clamp(0, h as isize - 1) as usize;
        luma[y * w + x]
    };
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            let c = 2.0 * at(xi, yi);
            let hx = (c - at(xi - s, yi) - at(xi + s, yi)).abs();
            let hy = (c - at(xi, yi - s) - at(xi, yi + s)).abs();
            out[y * w + x] = hx + hy;
        }
    }
}

/// The 4 x 4 crossed design, plus both controls.
///
/// **The crossing is the whole point.** A sweep over support alone cannot tell
/// "the optimum tracks support" apart from "the optimum tracks whatever else
/// changed with it", so every support radius appears in four operator families
/// and every family appears at four support radii.
///
/// `dsml` is the discriminator that the other three cannot supply: it has a
/// large *declared* support and ~1 px of internal averaging, so it separates
/// "reads far away" from "averages a lot" — the two things `support_px()`
/// silently conflates.
pub fn design() -> Vec<Measure> {
    let mut v = Vec::new();

    for (inner, outer) in [(0usize, 1usize), (1, 3), (2, 6), (4, 12)] {
        v.push(Measure::new(
            &format!("ring-{inner}-{outer}"),
            Family::Ring,
            Role::Treatment,
            outer,
            Kind::Ring { inner, outer },
        ));
    }
    for window in [0usize, 2, 5, 11] {
        v.push(Measure::new(
            &format!("tenengrad-w{window}"),
            Family::Tenengrad,
            Role::Treatment,
            1 + window,
            Kind::Tenengrad { window },
        ));
        v.push(Measure::new(
            &format!("sml-w{window}"),
            Family::Sml,
            Role::Treatment,
            1 + window,
            Kind::Sml { window },
        ));
    }
    for step in [1usize, 3, 6, 12] {
        v.push(Measure::new(
            &format!("dsml-s{step}"),
            Family::DilatedSml,
            Role::Treatment,
            step,
            Kind::DilatedSml { step },
        ));
    }

    // Null control: one operator, five different declared supports. Any
    // apparent support-dependence here is a leak in the harness or the
    // statistic, not a property of the merge.
    for declared in [1usize, 3, 6, 12, 24] {
        let mut m = Measure::new(
            &format!("nullctl-d{declared}"),
            Family::Ring,
            Role::NullControl,
            3,
            Kind::Ring { inner: 1, outer: 3 },
        );
        m.declared_radius = declared;
        v.push(m);
    }

    // Positive control: the shipped ring operator with its focus field
    // pre-smoothed by a known radius, so the measure's own internal averaging
    // — the mechanism B3 says the regulariser has to match — is dialled
    // directly over a 14x range of support.
    for extra in [0usize, 4, 10, 20, 38] {
        v.push(Measure::new(
            &format!("posctl-e{extra}"),
            Family::Ring,
            Role::PositiveControl,
            3 + extra,
            Kind::RingSmoothed {
                inner: 1,
                outer: 3,
                extra,
            },
        ));
    }

    v
}

/// The largest support radius in a measure set, which sets the tile margin.
pub fn max_support(measures: &[Measure]) -> usize {
    measures.iter().map(|m| m.support_radius).max().unwrap_or(0)
}
