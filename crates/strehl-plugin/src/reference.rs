//! The seven operators of SYNTHESIS fact 439, expressed against the trait.
//!
//! # These are calibration references, not shipping operators
//!
//! Exactly one of them — [`Tenengrad::shipped`] — is what `strehl` runs, and it
//! is expressed by **delegating to
//! [`strehl_core::focus::gradient_magnitude`]**, not by re-implementing it. The
//! other six exist for three reasons and no others:
//!
//! 1. They are the worked examples a contributor reads before writing their
//!    own, and they cover the shapes that matter: a wider stencil
//!    ([`Brenner`], stencil 2), a stencil that is itself two box means
//!    ([`Ring`], stencil 3), a squared response ([`TenengradSquared`],
//!    [`LocalVariance`]), and the canonical shape-from-focus operator
//!    ([`SumModifiedLaplacian`]).
//! 2. They let fact 439's 10.4x spread be reproduced *inside the crate*, on the
//!    host's own code path, rather than from a Python model of it.
//! 3. [`SumModifiedLaplacian`] is the fault-5 demonstration: `k` = 6.68, the
//!    likeliest third-party contribution there is, and the one that reverts
//!    87.76% of pixels to pure selection if it inherits the host's constant.
//!
//! **[`Ring`] must not be revived as a shipping operator.** `focus.rs` says so
//! and M11 measured why: `ring(1,3)` ranks 26-27th of 36, dominated on both
//! axes of the Pareto front, and no setting of its two radii closes the gap. It
//! is here because it is the *other* end of fact 439's spread — this project's
//! own first shipped operator, erring at `k` = 0.644 — and a survey with only
//! the over-noisy direction populated would be a weaker argument.
//!
//! # Definitions
//!
//! Taken from M43's reference instrument
//! (`experiments/m43-plugin-seam/02b-operator-noise-spread.py`) so that the
//! `k` values are comparable to fact 439's, and stated here because a focus
//! operator's name does not determine its formula — M14's whole (a) finding is
//! that "Tenengrad" in the literature usually means `Gx^2 + Gy^2` while the
//! number this project published belongs to the *magnitude*.
//!
//! ```text
//! tenengrad            sqrt(Gx^2 + Gy^2),  3x3 Sobel scaled by 1/8
//! tenengrad-squared    Gx^2 + Gy^2
//! brenner              |I(x+2,y) - I(x,y)|          (absolute, NOT squared)
//! laplacian            |4I - I(x+-1,y) - I(x,y+-1)|
//! sml                  |2I - I(x-1,y) - I(x+1,y)| + |2I - I(x,y-1) - I(x,y+1)|
//! ring(a,b)            |box_mean(I,a) - box_mean(I,b)|
//! local-variance       box_mean(I^2,1) - box_mean(I,1)^2
//! ```

use strehl_core::boxfilter::box_mean;
use strehl_core::focus::{WINDOW_RADIUS, gradient_magnitude};
use strehl_core::plane::PlaneGeometry;

use crate::measure::{FocusMeasure, Normalisation, Window, tap};

/// 3x3 Sobel components, scaled by 1/8, replicate-clamped.
///
/// The 1/8 is cosmetic to the ranking but is applied because it is what
/// `focus.rs` and M11's bake-off both did, and because it puts the response in
/// DN/px.
fn sobel(luma: &[f32], geom: PlaneGeometry, out: &mut [f32], f: impl Fn(f32, f32) -> f32) {
    let (w, h) = (geom.width, geom.height);
    for (i, o) in out.iter_mut().enumerate() {
        let (x, y) = ((i % w) as isize, (i / w) as isize);
        let at = |dx: isize, dy: isize| tap(luma, w, h, x + dx, y + dy);
        let gx = at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1);
        let gy = at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1);
        *o = f(0.125 * gx, 0.125 * gy);
    }
}

/// `sqrt(Gx^2 + Gy^2)` under a box window, divided by the luma sigma.
///
/// **The shipped operator.** [`Tenengrad::respond`] calls
/// [`strehl_core::focus::gradient_magnitude`] directly, so there is exactly one
/// implementation of the Sobel in this repository and the calibration measures
/// the real one.
#[derive(Debug, Clone)]
pub struct Tenengrad {
    id: String,
    radius: usize,
}

impl Tenengrad {
    /// `|grad|` at [`WINDOW_RADIUS`] — the operator at `HEAD`.
    #[must_use]
    pub fn shipped() -> Self {
        Self::at_radius(WINDOW_RADIUS)
    }

    /// `|grad|` at an arbitrary window radius.
    ///
    /// Fact 510: a radius change alone is a **12.5% gate shift** (w13 -> w11
    /// gives `k` = 1.125), so the radius is part of the identity, not a
    /// decoration on it.
    #[must_use]
    pub fn at_radius(radius: usize) -> Self {
        Self {
            id: format!("tenengrad-w{radius}"),
            radius,
        }
    }
}

impl FocusMeasure for Tenengrad {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        strehl_core::focus::SOBEL_RADIUS
    }
    fn window(&self) -> Window {
        Window::Box {
            radius: self.radius,
        }
    }
    fn normalisation(&self) -> Normalisation {
        Normalisation::LumaSigma { degree: 1 }
    }
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
        gradient_magnitude(luma, geom, out);
    }
}

/// `Gx^2 + Gy^2` — "Tenengrad" as the literature usually means it.
///
/// **This is the operator M17 and M42 propose to ship, and fact 509 measured
/// the edit at `k` = 1.528 against the current constant.** It is here so that
/// the pending change can be calibrated before it lands rather than after.
#[derive(Debug, Clone)]
pub struct TenengradSquared {
    id: String,
    radius: usize,
}

impl TenengradSquared {
    #[must_use]
    pub fn at_radius(radius: usize) -> Self {
        Self {
            id: format!("tenengrad-sq-w{radius}"),
            radius,
        }
    }
}

impl FocusMeasure for TenengradSquared {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        strehl_core::focus::SOBEL_RADIUS
    }
    fn window(&self) -> Window {
        Window::Box {
            radius: self.radius,
        }
    }
    fn normalisation(&self) -> Normalisation {
        Normalisation::LumaSigma { degree: 2 }
    }
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
        sobel(luma, geom, out, |gx, gy| gx * gx + gy * gy);
    }
}

/// `|I(x+2,y) - I(x,y)|`. Brenner's 1976 gradient, in the absolute form M43's
/// instrument used.
///
/// The **only asymmetric** operator in the set: it reads horizontally and not
/// vertically. Fact 90 is the reason that is worth flagging rather than
/// quietly fixing — this corpus carries 14-22x more vertical gradient energy
/// than horizontal, so an axis-asymmetric operator has a scene-dependent bias
/// that has nothing to do with its noise scale.
#[derive(Debug, Clone)]
pub struct Brenner {
    id: String,
    radius: usize,
}

impl Brenner {
    #[must_use]
    pub fn at_radius(radius: usize) -> Self {
        Self {
            id: format!("brenner-w{radius}"),
            radius,
        }
    }
}

impl FocusMeasure for Brenner {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        2
    }
    fn window(&self) -> Window {
        Window::Box {
            radius: self.radius,
        }
    }
    fn normalisation(&self) -> Normalisation {
        Normalisation::LumaSigma { degree: 1 }
    }
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
        let (w, h) = (geom.width, geom.height);
        for (i, o) in out.iter_mut().enumerate() {
            let (x, y) = ((i % w) as isize, (i / w) as isize);
            *o = (tap(luma, w, h, x + 2, y) - tap(luma, w, h, x, y)).abs();
        }
    }
}

/// `|4I - I(x-1,y) - I(x+1,y) - I(x,y-1) - I(x,y+1)|`, the 4-neighbour
/// Laplacian magnitude. Fact 439 puts it at `k` = 6.590.
#[derive(Debug, Clone)]
pub struct Laplacian {
    id: String,
    radius: usize,
}

impl Laplacian {
    #[must_use]
    pub fn at_radius(radius: usize) -> Self {
        Self {
            id: format!("laplacian-w{radius}"),
            radius,
        }
    }
}

impl FocusMeasure for Laplacian {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        1
    }
    fn window(&self) -> Window {
        Window::Box {
            radius: self.radius,
        }
    }
    fn normalisation(&self) -> Normalisation {
        Normalisation::LumaSigma { degree: 1 }
    }
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
        let (w, h) = (geom.width, geom.height);
        for (i, o) in out.iter_mut().enumerate() {
            let (x, y) = ((i % w) as isize, (i / w) as isize);
            let at = |dx: isize, dy: isize| tap(luma, w, h, x + dx, y + dy);
            *o = (4.0 * at(0, 0) - at(-1, 0) - at(1, 0) - at(0, -1) - at(0, 1)).abs();
        }
    }
}

/// Nayar & Nakagawa's sum-modified-Laplacian, step 1, threshold 0.
///
/// **This is fault 5 of workstream E §F4.6 made concrete.** SML is *the*
/// canonical shape-from-focus operator, so it is the single likeliest
/// third-party contribution there is — and fact 439 measures it at `k` = 6.680,
/// which at a declared `--gate 1.0` is an effective gate of **0.150** and
/// reverts **87.76%** of pixels to pure selection.
///
/// It passes every property workstream E §F4 proposes. The only thing that
/// catches it is the host refusing to take its noise scale on trust.
#[derive(Debug, Clone)]
pub struct SumModifiedLaplacian {
    id: String,
    radius: usize,
}

impl SumModifiedLaplacian {
    #[must_use]
    pub fn at_radius(radius: usize) -> Self {
        Self {
            id: format!("sml-w{radius}"),
            radius,
        }
    }
}

impl FocusMeasure for SumModifiedLaplacian {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        1
    }
    fn window(&self) -> Window {
        Window::Box {
            radius: self.radius,
        }
    }
    fn normalisation(&self) -> Normalisation {
        Normalisation::LumaSigma { degree: 1 }
    }
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
        let (w, h) = (geom.width, geom.height);
        for (i, o) in out.iter_mut().enumerate() {
            let (x, y) = ((i % w) as isize, (i / w) as isize);
            let at = |dx: isize, dy: isize| tap(luma, w, h, x + dx, y + dy);
            let c = 2.0 * at(0, 0);
            *o = (c - at(-1, 0) - at(1, 0)).abs() + (c - at(0, -1) - at(0, 1)).abs();
        }
    }
}

/// `|box_mean(I, inner) - box_mean(I, outer)|` — the ring difference the
/// walking skeleton shipped with, and the low end of fact 439's spread at
/// `k` = 0.644.
///
/// **Do not revive this as a shipping operator.** M11 ranks `ring(1,3)`
/// 26-27th of 36 and M14 replaced it; `focus.rs` keeps a copy in its own tests
/// solely so the replacement can be measured against it.
///
/// Its `respond` allocates two temporary planes per call, because the trait
/// hands out `&self` and a scratch plane sized for the *stencil*, not for an
/// operator that wants two of them. That is a real cost this design imposes on
/// multi-pass stencils and it is called out in the M45 report rather than
/// hidden.
#[derive(Debug, Clone)]
pub struct Ring {
    id: String,
    inner: usize,
    outer: usize,
    radius: usize,
}

impl Ring {
    #[must_use]
    pub fn new(inner: usize, outer: usize, radius: usize) -> Self {
        Self {
            id: format!("ring-{inner}-{outer}-w{radius}"),
            inner,
            outer,
            radius,
        }
    }
}

impl FocusMeasure for Ring {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        self.outer.max(self.inner)
    }
    fn window(&self) -> Window {
        Window::Box {
            radius: self.radius,
        }
    }
    fn normalisation(&self) -> Normalisation {
        Normalisation::LumaSigma { degree: 1 }
    }
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut inner = vec![0.0f32; geom.pixels()];
        box_mean(luma, geom, self.inner, &mut scratch, &mut inner);
        box_mean(luma, geom, self.outer, &mut scratch, out);
        for (o, i) in out.iter_mut().zip(&inner) {
            *o = (*i - *o).abs();
        }
    }
}

/// `box_mean(I^2, 1) - box_mean(I, 1)^2` — the 3x3 local variance, `k` = 2.475.
///
/// Note that this response is **not rectified**: f32 cancellation can put it
/// very slightly below zero on a flat region. That is left alone rather than
/// clamped, because clamping would change the operator M43 surveyed.
#[derive(Debug, Clone)]
pub struct LocalVariance {
    id: String,
    stencil: usize,
    radius: usize,
}

impl LocalVariance {
    #[must_use]
    pub fn new(stencil: usize, radius: usize) -> Self {
        Self {
            id: format!(
                "local-variance-{}x{}-w{radius}",
                2 * stencil + 1,
                2 * stencil + 1
            ),
            stencil,
            radius,
        }
    }
}

impl FocusMeasure for LocalVariance {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        self.stencil
    }
    fn window(&self) -> Window {
        Window::Box {
            radius: self.radius,
        }
    }
    fn normalisation(&self) -> Normalisation {
        Normalisation::LumaSigma { degree: 2 }
    }
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut mean = vec![0.0f32; geom.pixels()];
        let squares: Vec<f32> = luma.iter().map(|v| v * v).collect();
        box_mean(luma, geom, self.stencil, &mut scratch, &mut mean);
        box_mean(&squares, geom, self.stencil, &mut scratch, out);
        for (o, m) in out.iter_mut().zip(&mean) {
            *o -= *m * *m;
        }
    }
}

/// Every operator of fact 439's survey, in the shipped window, in the order the
/// fact lists them.
///
/// Boxed rather than returned by value because they are different types and the
/// registry holds `Arc<dyn FocusMeasure>`.
#[must_use]
pub fn survey(radius: usize) -> Vec<Box<dyn FocusMeasure>> {
    vec![
        Box::new(Ring::new(1, 3, radius)),
        Box::new(Tenengrad::at_radius(radius)),
        Box::new(TenengradSquared::at_radius(radius)),
        Box::new(Brenner::at_radius(radius)),
        Box::new(LocalVariance::new(1, radius)),
        Box::new(Laplacian::at_radius(radius)),
        Box::new(SumModifiedLaplacian::at_radius(radius)),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::field::{FieldConfig, FieldWorkspace};
    use crate::rng::{NoiseSource, unit_sigma_model};

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    fn textured(w: usize, h: usize) -> Vec<f32> {
        (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                2400.0
                    + 500.0 * (x * 1.61).sin() * (y * 1.37).cos()
                    + 300.0 * (x * 0.53 - y * 0.71).sin()
            })
            .collect()
    }

    #[test]
    fn the_local_sobel_agrees_with_the_cores_gradient_magnitude() {
        // There must be exactly one Sobel in the repository that anything is
        // measured against, and this is what proves the squared arm is the
        // square of that one rather than of a second, subtly different stencil.
        let g = geom(41, 37);
        let luma = textured(41, 37);
        let mut want = vec![0.0f32; g.pixels()];
        gradient_magnitude(&luma, g, &mut want);
        let mut got = vec![0.0f32; g.pixels()];
        sobel(&luma, g, &mut got, |gx, gy| (gx * gx + gy * gy).sqrt());
        assert_eq!(got, want);
    }

    #[test]
    fn every_survey_operator_is_flat_on_a_flat_plane() {
        // Rule 20: an operator with a zero-padded border or a live centre tap
        // on a constant would show a rim here. `local-variance` is the one that
        // can legitimately go very slightly negative through f32 cancellation,
        // so the band is two-sided.
        let g = geom(64, 48);
        let luma = vec![4000.0f32; g.pixels()];
        let noise = unit_sigma_model();
        let mut ws = FieldWorkspace::new(g);
        for op in survey(3) {
            let f = ws.run(op.as_ref(), FieldConfig::SHIPPED, &luma, &noise);
            let worst = f.iter().fold(0.0f32, |a, v| a.max(v.abs()));
            assert!(
                worst < 1e-2,
                "{}: a flat plane produced a response of {worst:e}",
                op.id()
            );
        }
    }

    #[test]
    fn every_survey_operator_prefers_resolved_texture_to_the_same_texture_blurred() {
        // Rule 9's flat-ROI companion, in the direction that matters for a
        // focus measure: if any of these did not discriminate, its calibrated
        // constant would still be perfectly well defined and perfectly
        // useless. `sensitivity` is workstream E's P2, and this is it.
        let (w, h) = (96usize, 96usize);
        let g = geom(w, h);
        let sharp = textured(w, h);
        let mut scratch = vec![0.0f32; g.pixels()];
        let mut soft = vec![0.0f32; g.pixels()];
        box_mean(&sharp, g, 2, &mut scratch, &mut soft);
        let noise = unit_sigma_model();
        let mut ws = FieldWorkspace::new(g);
        let margin = 24;
        let interior = |v: &[f32]| -> f64 {
            let mut s = 0.0f64;
            let mut n = 0usize;
            for y in margin..h - margin {
                for x in margin..w - margin {
                    s += f64::from(v[y * w + x]);
                    n += 1;
                }
            }
            s / n as f64
        };
        for op in survey(3) {
            let a = interior(ws.run(op.as_ref(), FieldConfig::SHIPPED, &sharp, &noise));
            let b = interior(ws.run(op.as_ref(), FieldConfig::SHIPPED, &soft, &noise));
            assert!(
                a > 1.2 * b,
                "{}: sharp {a:.5} must beat blurred {b:.5}",
                op.id()
            );
        }
    }

    #[test]
    fn the_survey_covers_the_stencil_shapes_the_trait_has_to_express() {
        let ops = survey(WINDOW_RADIUS);
        assert_eq!(ops.len(), 7);
        let radii: Vec<usize> = ops.iter().map(|o| o.stencil_radius()).collect();
        // Not all the same: if the trait could only express a 3x3 stencil it
        // would not be a plugin interface, it would be a Sobel with options.
        assert!(radii.contains(&1), "3x3 stencils: {radii:?}");
        assert!(radii.contains(&2), "Brenner's +2 reach: {radii:?}");
        assert!(radii.contains(&3), "ring(1,3)'s outer box: {radii:?}");
        let ids: Vec<&str> = ops.iter().map(|o| o.id()).collect();
        let mut sorted = ids.clone();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(sorted.len(), ids.len(), "ids must be distinct: {ids:?}");
        for id in &ids {
            assert!(
                id.contains(&format!("w{WINDOW_RADIUS}")),
                "{id} must carry its window radius (fact 152)"
            );
        }
    }

    #[test]
    fn a_pure_noise_plane_gives_every_operator_a_finite_non_zero_response() {
        let g = geom(96, 96);
        let mut plane = vec![0.0f32; g.pixels()];
        NoiseSource::SplitMixBoxMuller.fill(11, &mut plane);
        let noise = unit_sigma_model();
        let mut ws = FieldWorkspace::new(g);
        for op in survey(5) {
            let f = ws.run(op.as_ref(), FieldConfig::SHIPPED, &plane, &noise);
            assert!(f.iter().all(|v| v.is_finite()), "{}", op.id());
            assert!(
                f.iter().any(|v| *v != 0.0),
                "{} responded identically zero to noise",
                op.id()
            );
        }
    }
}
