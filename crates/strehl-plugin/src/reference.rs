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
//!    **`examples/calibration-survey` measures 10.27x here** (M58, 512² x 12
//!    seeds), so the spread reproduces — but **fact 635 scopes what it means**:
//!    it is partly a statement about the stencil constants written in *this
//!    repository*, not about operator shape. Rescale the Laplacian family by
//!    the same 1/8 `focus.rs` folds into its Sobel, Brenner by 1/2, and take
//!    the SD rather than the variance for local variance, and the span falls to
//!    **2.12x** (fact 635, corpus number, not re-measured here). That sharpens
//!    the argument rather than weakening it: `k` belongs to a specific written
//!    stencil, so a contributor implementing the same textbook operator with a
//!    different constant folded in gets a different `k`, which is precisely why
//!    the host must **measure** it and not accept a declaration.
//!    [`tests::rescaling_a_stencil_moves_its_k_by_exactly_that_scale`] shows the
//!    mechanism on this crate's own path.
//! 3. [`SumModifiedLaplacian`] is the fault-5 demonstration: `k` = 6.68, the
//!    likeliest third-party contribution there is, and the one that reverts
//!    **89.02%** of pixels to pure selection if it inherits the host's constant
//!    (M58, MEASURED on 109MSDCF at SML's own effective gate of 0.150 — *not*
//!    the 87.76% this line used to carry, which belongs to gate 0.168 and to a
//!    different `k`; fact 722).
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
#[cfg(test)]
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
/// **The shipped operator, and it is re-exported from
/// [`strehl_core::focus`] rather than defined here.** It moved into the core
/// crate in BUILD-PLUGIN so that `strehl stack --focus <id>` and the default
/// path run the same object: while this crate owned the type, "the shipped
/// operator" existed twice — once as `FocusField::compute`'s inlined stages and
/// once as this struct — and the two agreed only by test. The core type also
/// resolves [`shipped`](strehl_core::focus::Tenengrad::shipped) through
/// `window_radius()` rather than the `WINDOW_RADIUS` constant, so
/// `STREHL_WINDOW_RADIUS` cannot make them different operators.
pub use strehl_core::focus::Tenengrad;

/// `Gx^2 + Gy^2` — "Tenengrad" as the literature usually means it.
///
/// **This is the operator M17 and M42 propose to ship, and fact 509 measured
/// the edit at `k` = 1.528 against the current constant** — but read fact 662
/// before quoting that as the calibration the pending change needs, because it
/// is not.
///
/// Fact 583 and fact 662: `strehl-cli/Cargo.toml` does **not** depend on
/// `strehl-plugin`, so the shipped binary reaches
/// [`strehl_core::focus::FocusField::compute`] and nothing else. The pending
/// edit therefore necessarily lands on the **core** path. Fact 632 then prices
/// the difference: `Gx^2 + Gy^2` is homogeneous of degree 2, this crate handles
/// that with [`Normalisation::LumaSigma`]`{ degree: 2 }`, and `focus.rs` has a
/// single divide and no degree concept at all. So `k` = 1.528 is the
/// **plugin-path** correction and understates the core path by roughly the
/// local sigma (8.6-24.6 DN on this corpus). **Change (c) must not be applied
/// as specified**; question 147 is where the path gets recorded.
///
/// What this type is still for: it is the degree-2 worked example, and it is
/// the reason the degree concept exists in [`Normalisation`] at all. It is
/// **not** a calibration record for the pending edit — a doc comment that
/// claimed to be one, and was wrong by the local sigma, is what fact 723
/// caught here.
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
/// Laplacian magnitude. Fact 439 puts it at `k` = 6.590 **as the stencil is
/// written here, with no constant folded in**; fact 635 scopes that — fold in
/// the same 1/8 `focus.rs` applies to its Sobel and the same operator reads
/// `k` = 0.824. The name does not fix the number.
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
/// which at a declared `--gate 1.0` is an effective gate of **0.150**, at which
/// **89.02%** of pixels revert to pure selection against the **41.66%** the
/// same stack gives at a correctly calibrated gate 1.0.
///
/// Both figures are MEASURED by M58 on `109MSDCF`, 22 frames, by running the
/// shipped binary at those gates and reading its own `n_eff=1 %` column. This
/// line previously read 87.76%, which is **M43's row for gate 0.168 and for
/// `k` = 5.94** — a different configuration's pixel fraction pinned to this
/// configuration's gate. Both numbers were individually correct and the pairing
/// was not; that is fact 722, and it is what a citation-*number* check cannot
/// see.
///
/// `k` = 6.680 is this stencil as written, with no constant folded in. Under
/// fact 635's single consistent convention it is 0.835 — see the module docs.
/// The fault-5 argument does not depend on which convention is chosen, only on
/// the host and the plugin having chosen the *same* one, which is the whole
/// point: nothing in the trait can make them.
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
/// `k` = 0.644. It stays the low end under fact 635's alternative convention
/// too, because it has no folded-in stencil constant for that convention to
/// change: it is a difference of two means, already normalised by construction.
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
    use strehl_core::noise::NoiseModel;

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

    /// A test-only wrapper that folds a scalar constant into another operator's
    /// stencil, the way `focus.rs` folds 1/8 into its Sobel.
    ///
    /// It exists for exactly one claim — fact 635's — and is not part of the
    /// contribution surface.
    struct Rescaled {
        inner: Box<dyn FocusMeasure>,
        id: String,
        scale: f32,
    }

    impl FocusMeasure for Rescaled {
        fn id(&self) -> &str {
            &self.id
        }
        fn stencil_radius(&self) -> usize {
            self.inner.stencil_radius()
        }
        fn window(&self) -> Window {
            self.inner.window()
        }
        fn normalisation(&self) -> Normalisation {
            self.inner.normalisation()
        }
        fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
            self.inner.respond(luma, geom, out);
            for o in out.iter_mut() {
                *o *= self.scale;
            }
        }
        fn aggregate(
            &self,
            response: &[f32],
            geom: PlaneGeometry,
            scratch: &mut [f32],
            out: &mut [f32],
        ) {
            self.inner.aggregate(response, geom, scratch, out);
        }
        fn normalise(&self, field: &mut [f32], luma: &[f32], noise: &NoiseModel) {
            self.inner.normalise(field, luma, noise);
        }
    }

    /// **Fact 635's mechanism, on this crate's own path: `k` is a property of a
    /// written stencil, not of an operator's name.**
    ///
    /// SML measures `k` = 6.61 here and sits at the top of fact 439's 10.4x
    /// spread. Fold in the same 1/8 `focus.rs` folds into its Sobel — the same
    /// textbook operator, a different written constant — and it lands at 0.83,
    /// *below* the shipped operator. Nothing about the operator changed; the
    /// only thing that moved was a constant a contributor is free to choose.
    ///
    /// That is why fact 439's span is scoped by fact 635 to **2.12x** under one
    /// consistent convention, and why the host must measure the scale instead
    /// of accepting a declaration: there is no declaration a contributor could
    /// write that is right for both conventions.
    ///
    /// Rule 20 — the pipeline is linear in the response, so exact
    /// proportionality is close to arithmetic and this test's power is not in
    /// the ratio. What it does reject: a calibrator that acquired **any**
    /// scale-dependent term (a fitted floor, an absolute epsilon compared
    /// against the response rather than against sigma, a fixed-point stage), and
    /// the [`crate::calibrate::CalibrationError::DegenerateResponse`] refusal
    /// firing on a legitimately small but non-degenerate operator. Both are
    /// reachable and both would break the seam's central promise.
    ///
    /// Rule 35 — the assertion's object is fact 439's published 6.680 divided
    /// by the convention constant, not anything measured in this test.
    #[test]
    fn rescaling_a_stencil_moves_its_k_by_exactly_that_scale() {
        use crate::calibrate::{CalibrationPlan, calibrate};

        // The full host plan: the ratio is far better conditioned than either
        // constant, but the second assertion is against fact 439's *absolute*
        // 6.680, and 192^2 carries the ~2% small-plane bias
        // `CalibrationPlan::host_default` documents.
        let plan = CalibrationPlan::host_default();
        let plain = calibrate(
            &SumModifiedLaplacian::at_radius(WINDOW_RADIUS),
            FieldConfig::SHIPPED,
            &plan,
        )
        .expect("sml calibrates");
        let folded = calibrate(
            &Rescaled {
                inner: Box::new(SumModifiedLaplacian::at_radius(WINDOW_RADIUS)),
                id: "sml-w13-over-8".to_string(),
                scale: 0.125,
            },
            FieldConfig::SHIPPED,
            &plan,
        )
        .expect("the rescaled stencil calibrates");

        let ratio = f64::from(folded.response_sd()) / f64::from(plain.response_sd());
        println!(
            "sml k = {:.4}, same operator with 1/8 folded in = {:.4}, ratio {ratio:.6}",
            plain.k_against_host_constant(),
            folded.k_against_host_constant(),
        );

        assert!(
            (ratio - 0.125).abs() < 1e-4,
            "folding 1/8 into the stencil must scale the measured constant by \
             exactly 1/8; got {ratio}"
        );
        // Fact 635's consequence, stated against fact 439's published 6.680:
        // the canonical SFF operator crosses from the top of the spread to
        // below the shipped operator on a convention change alone.
        let folded_k = f64::from(folded.k_against_host_constant());
        assert!(
            (folded_k - 6.680 / 8.0).abs() / (6.680 / 8.0) < 0.05,
            "fact 635 puts the folded stencil at 6.680/8 = 0.835; got {folded_k:.4}"
        );
        assert!(
            folded_k < 1.0 && f64::from(plain.k_against_host_constant()) > 5.5,
            "the two must land on opposite sides of the shipped operator, or the \
             claim that the span is a convention has no demonstration here"
        );
    }
}
