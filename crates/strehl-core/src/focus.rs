//! Noise-normalised Tenengrad focus measure: Sobel gradient magnitude under a
//! 27x27 box window.
//!
//! ```text
//! g(p)     = sqrt(Gx(p)^2 + Gy(p)^2)            3x3 Sobel, scaled by 1/8
//! focus(p) = box_mean_13(g)(p) / max(sigma_L(p), EPS)
//! ```
//!
//! # This operator is a measurement result, not a preference
//!
//! It replaces `|mean_3x3 - mean_7x7| / sigma`, the ring difference the walking
//! skeleton shipped with. Two milestones decided it:
//!
//! - **M11** (`docs/research/M11-focus-bakeoff-measured.md`) ran a 47-operator
//!   pre-registered bake-off on two real stacks and scored it on a Pareto front
//!   of selectivity against merged-noise excess. `ring(1,3)` came **26-27th of
//!   36**: N = 1.3475x at 41-49% of the best selectivity. Tenengrad under a box
//!   window dominates it on **both** axes, and no setting of the ring's two
//!   radii closes the gap (SYNTHESIS fact 41).
//! - **M13** (`docs/research/M13-window-depth-measured.md`) set the window.
//!   M11 recommended 11x11; that is dominated. Over 36 occluding-edge cells the
//!   argmin of both mean and worst-case regret is **radius 13**, stable in all
//!   three noise seeds (SYNTHESIS fact 60).
//!
//! Neither says the operator is noise-free. **No operator measured is**: 0 of
//! 36 reached N <= 1.02x (fact 37). The escape from selection's noise penalty
//! is estimation, not a better selector — this measure only makes the selector
//! that the skeleton still is as good as a selector gets.
//!
//! # Why the magnitude and not the energy
//!
//! "Tenengrad" in the literature is usually `Gx^2 + Gy^2`. **The number M11
//! published is not that one.** `tenengrad-w5` in
//! `experiments/m11-focus-bakeoff/src/measures.rs` is `Kind::Tenengrad {
//! squared: false }` — the gradient *magnitude*, `degree = 1`, divided by
//! `sigma^1` — and the squared arm is a separate entry, `tenengrad-sq-w2`.
//! M13's `tenengrad-w13` is the same magnitude form. So is this. See
//! `docs/research/M14-tenengrad-implemented.md` for how that was established
//! from the committed CSVs rather than assumed.
//!
//! # The normalisation is a proxy, and this is where that is admitted
//!
//! `sigma_L` is the noise standard deviation of a **single** luma sample at
//! that signal level, from the injected noise model. It is **not** the standard
//! deviation of the windowed gradient magnitude, which is smaller by roughly
//! the window's tap count and is not even centred at zero, since `|grad|` is a
//! rectified quantity with a positive noise floor.
//!
//! It is kept anyway, and deliberately, because it is what was measured. M11
//! scored an un-normalised arm (`tenengrad-w2-nonorm`) and a box-normalised arm
//! (`tenengrad-w2-boxnorm`) precisely so the divisor would not be a confound,
//! and the published `N = 1.1324x` belongs to the pointwise-`sigma(L(p))` arm.
//! Substituting a "better" divisor here would silently invalidate that number.
//!
//! The reason it is adequate is unchanged from the ring: the merge consumes
//! only the *ranking* of `focus` across frames at a fixed pixel, and every
//! frame at that pixel divides by a sigma computed from nearly the same signal
//! level, so the omitted factor very nearly cancels out of the comparison.
//! **The divisor is not free, though** — it is a term in the centre-tap
//! fraction `phi`, and it is the whole reason `phi` is 0.139 here instead of
//! 0.0013 (fact 39, M13 §1.4).

use crate::boxfilter::box_mean;
use crate::noise::NoiseModel;
use crate::plane::PlaneGeometry;

/// Box-window radius, in plane pixels: a `27x27` mean of the gradient
/// magnitude.
///
/// **MEASURED, M13** (`docs/research/M13-window-depth-measured.md` §6.1,
/// SYNTHESIS fact 60): argmin of both mean regret (3.171 DN) and worst-case
/// regret (12.111 DN) over 36 occluding-edge cells, and argmin independently in
/// each of three noise seeds. Read it as the centre of the basin `w11-w15`,
/// which is flat to 0.87 DN against a 0.193 DN seed noise floor — not as a
/// value precise to the pixel.
///
/// **It may still move narrower.** Every one of M13's 7,200 measurements ran
/// with the merge regulariser off (`width = 1`), and SYNTHESIS open question 17
/// asks whether the optimum survives switching it on; if the regulariser is
/// already buying the variance reduction, the wide window's benefit shrinks
/// while its occlusion-halo cost does not. That is why this is one named
/// constant and not a number woven through the code.
pub const WINDOW_RADIUS: usize = 13;

/// Environment override for [`WINDOW_RADIUS`]. **Diagnostic only.**
///
/// M121 established that the occlusion halo carries the focus window's length
/// scale (`w50 = 10.0 px`, cutoff `13.25 px`, against `WINDOW_RADIUS = 13`) and
/// matches none of the three physical alternatives checked. That is a *match*,
/// not a dose-response: one point on one curve is consistent with the window
/// setting the width and equally consistent with a coincidence at 13.
///
/// This exists so the ladder can be run without five builds, which is the only
/// way to tell those apart. It is read **once** per process, and it is read by
/// [`window_radius`] rather than substituted for the constant, so the shipped
/// default is bit-identical when the variable is unset.
///
/// **A malformed value panics rather than falling back to 13.** A dose-response
/// that silently rendered every rung at the default would look like a flat
/// curve and would refute the mechanism it was built to test.
pub const WINDOW_RADIUS_ENV: &str = "STREHL_WINDOW_RADIUS";

/// The selection window radius actually in force, honouring [`WINDOW_RADIUS_ENV`].
///
/// Returns [`WINDOW_RADIUS`] unless the environment overrides it. Cached, so the
/// per-frame focus pass does not touch the environment 299 times.
#[must_use]
pub fn window_radius() -> usize {
    static CACHED: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *CACHED.get_or_init(|| match std::env::var(WINDOW_RADIUS_ENV) {
        Err(_) => WINDOW_RADIUS,
        Ok(raw) => {
            let r: usize = raw.trim().parse().unwrap_or_else(|_| {
                panic!("{WINDOW_RADIUS_ENV}={raw:?} is not a non-negative integer")
            });
            assert!(
                (1..=64).contains(&r),
                "{WINDOW_RADIUS_ENV}={r} is outside the supported range 1..=64"
            );
            r
        }
    })
}

/// Box-window radius for the **statistics** field: 2, a `5x5` mean.
///
/// **MEASURED, M21** (SYNTHESIS fact 152). This is not a second opinion about
/// the focus measure and it never elects a winner or moves the gate. It exists
/// because occlusion bimodality is *invisible at the selection scale*: at
/// [`WINDOW_RADIUS`] = 13 — 27 CFA px, **54 sensor px** — multi-peak enrichment
/// at depth steps measures **0.36x**, i.e. depleted, because the window averages
/// the foreground and background layers together and destroys the structure
/// being looked for. At radius 2 the same detector measures **4.38x** against a
/// frame-permutation placebo reading 1.01x.
///
/// M21 states the consequence as an architectural constraint on the fold seam:
/// *"the per-pixel sufficient statistics must be carried at a finer scale than
/// the focus measure, or a second pass must recompute them."* This constant is
/// the first half of that choice; [`crate::merge::ThroughFocus`] is the second.
///
/// **The two scales are not interchangeable and must never be swapped.** The
/// selection scale is wide because a wide window buys contrast localisation at
/// an occluding boundary (fact 82); the statistics scale is narrow because
/// anything wider cannot see a second layer at all.
pub const FINE_WINDOW_RADIUS: usize = 2;

/// Radius of the gradient stencil. A 3x3 Sobel, so 1.
pub const SOBEL_RADIUS: usize = 1;

/// The furthest luma sample the focus value at a pixel reads, in plane pixels.
///
/// `SOBEL_RADIUS + WINDOW_RADIUS = 14`, so the read extent is a `29x29` square
/// and the sensitivity kernel has `29^2 = 841` taps. **Anything that sizes a
/// tile margin, or the `halo()` rectangle expansion of SYNTHESIS fact 32, from
/// the focus operator must use this** — M13 §6.3. It is 4.7x the ring's, so a
/// margin that was correct before is not correct now.
pub const SUPPORT_RADIUS: usize = SOBEL_RADIUS + WINDOW_RADIUS;

/// Divisor floor, in DN. Guards the case where the noise model returns zero or
/// something denormal; it is far below any real sensor's read-noise floor.
///
/// **Public because it is part of the operator contract.** It used to be
/// private, and `strehl-plugin`'s `measure.rs` carried a copy with a comment
/// admitting the copy. A contributed operator that normalises itself has to
/// divide by the same floor the shipped one does, or its calibrated constant
/// describes a different pipeline from the one the merge runs.
pub const SIGMA_EPS: f32 = 1e-3;

/// 3x3 Sobel gradient magnitude, `sqrt(Gx^2 + Gy^2)`, replicate-clamped at the
/// border.
///
/// The `1/8` on each component is cosmetic — the merge only compares a measure
/// against itself on other frames at the same pixel, and both the argmax and
/// any positive-scaled regulariser are invariant to it — but it is applied
/// because it puts the response in DN/px, and because it is what
/// `experiments/m11-focus-bakeoff/src/measures.rs::sobel` did when the ruling
/// numbers were measured.
///
/// # Precision
///
/// `f32` throughout, and that is safe here. At the A7C II's 15360 DN white
/// level and 512 DN black the largest possible component is
/// `0.125 * 4 * 14848 = 7424` DN/px, so `Gx^2 + Gy^2 <= 1.10e8` — well inside
/// f32's range, but past `2^24`, so the squares are inexact. The error is
/// **relative** (<= 2^-23 each, halved again by the square root), which puts
/// the worst-case absolute error on `g` near `1e-3` DN — three orders below the
/// DN quantisation of the input. Accumulating 841 of these is the part that
/// needs care, and that happens in [`box_mean`], which keeps an f64 sum.
pub fn gradient_magnitude(luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
    assert_eq!(luma.len(), geom.pixels());
    assert_eq!(out.len(), geom.pixels());
    let (w, h) = (geom.width, geom.height);
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            let at = |dx: isize, dy: isize| {
                let sx = (xi + dx).clamp(0, w as isize - 1) as usize;
                let sy = (yi + dy).clamp(0, h as isize - 1) as usize;
                luma[sy * w + sx]
            };
            let gx =
                at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1);
            let gy =
                at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1);
            let (gx, gy) = (0.125 * gx, 0.125 * gy);
            out[y * w + x] = (gx * gx + gy * gy).sqrt();
        }
    }
}

/// Reusable buffers plus the computed focus field for one plane.
///
/// Allocated once per worker and reused for every frame that worker folds. At
/// 8.2 MP this is 99 MB, so allocating per frame would dominate the run.
pub struct FocusField {
    geom: PlaneGeometry,
    /// Holds the windowed gradient mean, then is overwritten in place with the
    /// focus value. The normalisation is elementwise and reads each element
    /// once, so no fourth full-plane buffer is needed.
    focus: Vec<f32>,
    grad: Vec<f32>,
    scratch: Vec<f32>,
    /// The multi-scale ladder, `LEVEL_RADII.len()` planes laid end to end.
    ///
    /// **Empty unless [`FocusField::compute_scaled`] is called**, so the
    /// shipped two-pass merge allocates exactly the three planes M8's ratchet
    /// prices and the edge-aware path pays for its own ladder.
    level_buf: Vec<f32>,
}

impl FocusField {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            focus: vec![0.0; geom.pixels()],
            grad: vec![0.0; geom.pixels()],
            scratch: vec![0.0; geom.pixels()],
            level_buf: Vec::new(),
        }
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }

    /// Bytes of scratch this holds, for the memory budget report.
    ///
    /// **Three f32 planes, unchanged by M14.** The ring held `inner`, `outer`
    /// and a box-filter `scratch`; Tenengrad holds `grad`, the same `scratch`
    /// and the output. The per-worker term in `strehl-cli`'s `WorkerPlan` and
    /// M8's measured ratchet (SYNTHESIS §5, fact 33) are therefore untouched.
    pub fn allocated_bytes(&self) -> usize {
        3 * self.geom.pixels() * std::mem::size_of::<f32>()
    }

    /// Compute the focus field for one frame's black-subtracted green luma.
    ///
    /// Cost is **O(1) in [`WINDOW_RADIUS`]**, because [`box_mean`] is a
    /// separable running sum. M13 measured the whole operator flat in the
    /// radius to within 2.53% over w1-w40; a naive `(2w+1)^2` gather at radius
    /// 13 would be 841x the taps and would invalidate that result.
    pub fn compute(&mut self, luma: &[f32], noise: &NoiseModel) {
        self.compute_at_radius(luma, noise, window_radius());
    }

    /// [`compute`](Self::compute) at an explicit radius.
    ///
    /// The edge-aware election's *guide* pass needs a deliberately narrow
    /// window. It cannot get one from [`WINDOW_RADIUS_ENV`], which is process-
    /// wide and cached, and it must not get one from the shipped radius: the
    /// winner field the shipped merge elects has its own depth step displaced
    /// outward by exactly one window radius (that displacement IS the halo), so
    /// a guide elected at radius 13 cannot locate the silhouettes the support
    /// has to avoid. Measured: the rim cutoff tracks the window radius 1:1 over
    /// radii 9-26, slope 1.07, intercept 1.08.
    pub fn compute_at_radius(&mut self, luma: &[f32], noise: &NoiseModel, radius: usize) {
        self.compute_with_measure(&Tenengrad::at_radius(radius), luma, noise);
    }

    /// Compute the focus field with a **contributed** operator, through the
    /// same three buffers and the same pipeline the shipped one uses.
    ///
    /// This is the method that makes the plugin seam real: `strehl stack
    /// --focus <id>` reaches the merge through here, and
    /// [`compute_at_radius`](Self::compute_at_radius) reaches it through here
    /// too, with [`Tenengrad`]. There is one pipeline, so a contributed
    /// operator cannot be running through a second copy of the stage order that
    /// `FOCUS_NOISE_SD` was measured against.
    ///
    /// The host's regulariser is **not** applied here, exactly as for
    /// [`compute`](Self::compute) — `merge::regularise` is the next stage and
    /// the merge owns it.
    pub fn compute_with_measure(
        &mut self,
        op: &dyn FocusMeasure,
        luma: &[f32],
        noise: &NoiseModel,
    ) {
        run_measure(
            op,
            self.geom,
            luma,
            noise,
            &mut self.grad,
            &mut self.scratch,
            &mut self.focus,
        );
    }

    /// Compute the selection field **and** a second, finer field from the same
    /// gradient pass.
    ///
    /// `fine` receives `box_mean(|grad|, fine_radius) / sigma(luma)` — the same
    /// operator as [`compute`](Self::compute), differing only in the window
    /// radius. It is the field [`crate::merge::ThroughFocus`] gathers its
    /// per-pixel statistics from, and it exists because M21 measured occlusion
    /// bimodality *depleted* at the selection radius (see
    /// [`FINE_WINDOW_RADIUS`]).
    ///
    /// The gradient magnitude is computed **once** and both box means read it,
    /// so the marginal cost of the second field is one extra separable running
    /// sum plus one divide — both O(1) in their radii and independent of the
    /// frame count. `compute` and this method agree exactly on
    /// [`values`](Self::values); the second field is strictly additional and
    /// **cannot move the selection**.
    pub fn compute_with_fine(
        &mut self,
        luma: &[f32],
        noise: &NoiseModel,
        fine_radius: usize,
        fine: &mut [f32],
    ) {
        assert_eq!(luma.len(), self.geom.pixels());
        assert_eq!(fine.len(), self.geom.pixels());
        gradient_magnitude(luma, self.geom, &mut self.grad);
        box_mean(
            &self.grad,
            self.geom,
            window_radius(),
            &mut self.scratch,
            &mut self.focus,
        );
        box_mean(&self.grad, self.geom, fine_radius, &mut self.scratch, fine);
        normalise_by_luma_sigma(&mut self.focus, luma, noise);
        normalise_by_luma_sigma(fine, luma, noise);
    }

    pub fn values(&self) -> &[f32] {
        &self.focus
    }

    /// Compute the focus field with a **per-pixel** support radius.
    ///
    /// `scale` supplies, for each pixel, an index into
    /// [`LEVEL_RADII`](crate::edgeaware::LEVEL_RADII); the field at that pixel
    /// is the box mean of the gradient magnitude at that radius. It is the same
    /// operator as [`compute`](Self::compute) everywhere `scale` asks for
    /// [`FULL_LEVEL`](crate::edgeaware::FULL_LEVEL), and
    /// `SelectionScale::uniform(geom, FULL_LEVEL)` reproduces it **exactly** —
    /// same gradient pass, same `box_mean`, same divisor — which is what the
    /// `uniform_full_scale_is_the_shipped_operator` test pins.
    ///
    /// # Why the levels are all-plane rather than per-pixel gathers
    ///
    /// A spatially varying radius is not separable, so a direct evaluation is
    /// `(2r+1)^2` taps per pixel and would cost 841 at the widest — the exact
    /// cost [`box_mean`]'s running sum exists to avoid, and the thing that
    /// makes M13's flat-in-radius cost measurement valid. Instead each of the
    /// five radii is evaluated over the whole plane by running sum, O(1) in the
    /// radius, and the per-pixel choice is one gather. That is five separable
    /// passes rather than one, and nothing that scales with the radius.
    ///
    /// The normalisation is applied **after** the gather, so every level
    /// divides by the same `sigma(L(p))` and the choice of level cannot leak
    /// into the divisor.
    pub fn compute_scaled(
        &mut self,
        luma: &[f32],
        noise: &NoiseModel,
        scale: &crate::edgeaware::SelectionScale,
    ) {
        self.compute_scaled_with_measure(&Tenengrad::shipped(), luma, noise, scale);
    }

    /// [`compute_scaled`](Self::compute_scaled) with a **contributed**
    /// operator supplying the response and the normaliser.
    ///
    /// Delegated to by `compute_scaled` so there is one implementation, and
    /// bit-identical for [`Tenengrad::shipped`] because
    /// [`Tenengrad::respond`](FocusMeasure::respond) *is* [`gradient_magnitude`]
    /// and [`Tenengrad::normalise`](FocusMeasure::normalise) *is*
    /// [`normalise_by_luma_sigma`] — no second copy of either.
    ///
    /// # What this does to the operator's own window, and what that costs
    ///
    /// The operator's [`window`](FocusMeasure::window) is **overridden**: the
    /// per-pixel level replaces it, exactly as it already replaces
    /// [`WINDOW_RADIUS`] on the shipped path. That is not free and it is not
    /// hidden. A calibrated response SD is measured at a *fixed* window (fact
    /// 500 — the scale is a property of the operator AND its window AND the
    /// host regulariser), so wherever `scale` asks for a level below
    /// [`FULL_LEVEL`](crate::edgeaware::FULL_LEVEL) the field's true SD is
    /// larger than the measured one and the gate there is effectively looser
    /// than its nominal value.
    ///
    /// This is a **pre-existing** property of the shipped path, not something
    /// the plugin seam introduces: `FOCUS_NOISE_SD` is likewise measured at
    /// radius 13 and likewise applied to a field whose radius varies. The
    /// plugin seam inherits the approximation with the operator's OWN measured
    /// scale rather than a foreign one, which is strictly better than the
    /// alternative of refusing to run and strictly worse than a per-level
    /// calibration ladder, which nothing in this repository has yet.
    ///
    /// # Panics
    ///
    /// As [`compute_scaled`](Self::compute_scaled), plus on an operator whose
    /// [`support_radius`](FocusMeasure::support_radius) the levels cannot
    /// express — [`Window::Custom`] has no radius to ladder over, so it is
    /// refused here rather than silently run at its own fixed window while the
    /// caller believes the election adapted.
    pub fn compute_scaled_with_measure(
        &mut self,
        op: &dyn FocusMeasure,
        luma: &[f32],
        noise: &NoiseModel,
        scale: &crate::edgeaware::SelectionScale,
    ) {
        assert_eq!(luma.len(), self.geom.pixels());
        assert_eq!(scale.geometry(), self.geom);
        assert!(
            !matches!(op.window(), Window::Custom { .. }),
            "focus operator `{}` has a custom window, which the per-pixel \
             selection scale cannot ladder over; run it with STREHL_EDGE_AWARE=0",
            op.id()
        );
        op.respond(luma, self.geom, &mut self.grad);
        let levels = scale.levels();
        let px = self.geom.pixels();
        if self.level_buf.len() != crate::edgeaware::LEVEL_RADII.len() * px {
            self.level_buf = vec![0.0; crate::edgeaware::LEVEL_RADII.len() * px];
        }
        for (l, &r) in crate::edgeaware::LEVEL_RADII.iter().enumerate() {
            let (_, tail) = self.level_buf.split_at_mut(l * px);
            box_mean(
                &self.grad,
                self.geom,
                r,
                &mut self.scratch,
                &mut tail[..px],
            );
        }
        for (i, f) in self.focus.iter_mut().enumerate() {
            *f = self.level_buf[levels[i] as usize * px + i];
        }
        op.normalise(&mut self.focus, luma, noise);
    }


    /// Bytes the multi-scale ladder adds once [`compute_scaled`](Self::compute_scaled)
    /// has been called, for the memory report.
    /// Compute the focus field with **depth-layer masked support** at the full
    /// shipped radius.
    ///
    /// Identical to [`FocusField::compute`] at every untreated pixel, by
    /// construction: the full-window box mean is computed first and
    /// [`LayerSupport::apply`] only overwrites the treated minority. That is
    /// what lets the feature ship dark.
    pub fn compute_layered(
        &mut self,
        luma: &[f32],
        noise: &NoiseModel,
        support: &crate::edgeaware::LayerSupport,
    ) {
        assert_eq!(luma.len(), self.geom.pixels());
        assert_eq!(support.geometry(), self.geom);
        let px = self.geom.pixels();
        let support_radius = window_radius();
        gradient_magnitude(luma, self.geom, &mut self.grad);
        box_mean(
            &self.grad,
            self.geom,
            support_radius,
            &mut self.scratch,
            &mut self.focus,
        );
        if self.level_buf.len() != 2 * px {
            self.level_buf = vec![0.0; 2 * px];
        }
        let (tmp, acc) = self.level_buf.split_at_mut(px);
        support.apply_at(
            &self.grad,
            support_radius,
            &mut self.scratch,
            tmp,
            acc,
            &mut self.focus,
        );
        normalise_by_luma_sigma(&mut self.focus, luma, noise);
    }

    pub fn scaled_extra_bytes(&self) -> usize {
        self.level_buf.len() * std::mem::size_of::<f32>()
    }
}

/// Divide a windowed gradient response by the per-pixel luma noise sigma.
///
/// Factored out so that [`FocusField::compute`] and
/// [`FocusField::compute_with_fine`] cannot drift apart in the normalisation —
/// the divisor is the whole of M11's ruling and a silent difference between the
/// two fields would put the statistics on a different scale from the selection
/// without any test noticing.
fn normalise_by_luma_sigma(field: &mut [f32], luma: &[f32], noise: &NoiseModel) {
    for (f, l) in field.iter_mut().zip(luma) {
        let sigma = noise.green_luma_sigma(*l).max(SIGMA_EPS);
        *f /= sigma;
    }
}

// ---------------------------------------------------------------------------
// The contribution surface: one operator abstraction, one pipeline.
// ---------------------------------------------------------------------------

/// Replicate-clamped tap. Every stencil in the ecosystem reads through this.
///
/// Replicate rather than zero-pad: a zero-padded gradient manufactures a bright
/// rim one stencil in from the edge and hands it to the merge as detail.
/// [`box_mean`] clamps for the same reason.
#[inline]
#[must_use]
pub fn tap(luma: &[f32], w: usize, h: usize, x: isize, y: isize) -> f32 {
    let sx = x.clamp(0, w as isize - 1) as usize;
    let sy = y.clamp(0, h as isize - 1) as usize;
    luma[sy * w + sx]
}

/// The operator's own aggregation window — the stage between the stencil and
/// the normaliser.
///
/// This is **not** the host's regulariser. The two are separate boxes applied
/// in sequence, and conflating them is the fault fact 500 records: the
/// project's two published noise constants differ in whether the second box was
/// present, and were then divided by one another.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Window {
    /// The stencil response is the field.
    None,
    /// Separable running-sum box mean of the given radius, via [`box_mean`].
    /// **O(1) in the radius**, which is what makes M13's window ruling valid
    /// (cost flat to 2.53% over w1-w40).
    Box { radius: usize },
    /// The operator aggregates itself over a `radius`-wide support and **must**
    /// override [`FocusMeasure::aggregate`]. The host cannot assume the cost is
    /// O(1) in the radius here.
    Custom { radius: usize },
}

impl Window {
    /// Half-width of the aggregation support, in plane pixels.
    #[must_use]
    pub const fn radius(self) -> usize {
        match self {
            Window::None => 0,
            Window::Box { radius } | Window::Custom { radius } => radius,
        }
    }

    /// Whether the host may assume the aggregation is a separable running sum,
    /// and therefore free in the radius.
    #[must_use]
    pub const fn is_separable(self) -> bool {
        matches!(self, Window::None | Window::Box { .. })
    }
}

/// How a windowed response is put into units.
///
/// The shipped operator divides by the injected noise model's per-pixel luma
/// sigma. This module's header is explicit that the divisor is a **proxy** — it
/// is the sigma of a single luma sample, not of the windowed response — and it
/// is kept because it is what M11 scored. Nothing here is entitled to improve
/// on it silently.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Normalisation {
    /// Leave the response as it is. M11's `Norm::None` arm.
    None,
    /// Divide pointwise by `max(sigma_L(p), SIGMA_EPS)^degree`.
    ///
    /// `degree` follows M11's parameterisation: a response homogeneous of
    /// degree `d` in the luma divides by `sigma^d`, so `|grad|` uses 1 and
    /// `|grad|^2` uses 2. **This is a convention, not a measurement** — M11
    /// scored the `degree = 1` arm and that is the only one with a published
    /// number behind it.
    LumaSigma { degree: u32 },
    /// The operator normalises itself and **must** override
    /// [`FocusMeasure::normalise`].
    Custom,
}

/// A focus measure: the replaceable component the merge elects on.
///
/// Implementors supply the three stages and the two radii. They do **not**
/// supply a noise constant, a tolerance, or a gate — see
/// `strehl_plugin::calibrate`, where the host measures it instead. There is no
/// `fn noise_sd`, no field to put one in, and no default to fall back to.
///
/// # Why this lives in `strehl-core` and not in the plugin crate
///
/// Because the *host* is the thing that has to run it. This trait used to sit
/// in `strehl-plugin`, which meant the shipped merge could not accept a
/// contributed operator without the pipeline being written a second time — and
/// it was: `FocusField::compute` and `strehl_plugin::FieldWorkspace::run` were
/// two spellings of `respond -> aggregate -> normalise` whose agreement was
/// held together by a test rather than by construction. Both now call
/// [`run_measure`].
///
/// `Send + Sync` because the merge folds frames across a rayon worker pool and
/// every worker holds the same operator.
pub trait FocusMeasure: Send + Sync {
    /// Stable identity, used as the registry key and printed in reports.
    ///
    /// Include the window radius. Fact 152: the operator and its window are one
    /// object, and fact 510 measured a **12.5% gate shift** from a radius
    /// change alone, so `tenengrad` and `tenengrad-w11` are different things
    /// and must not share a name.
    fn id(&self) -> &str;

    /// Half-width of the pointwise stencil, in plane pixels. A 3x3 Sobel is 1;
    /// Brenner's `|I(x+2) - I(x)|` is 2; `ring(1,3)` is 3.
    fn stencil_radius(&self) -> usize;

    /// The operator's own aggregation window.
    fn window(&self) -> Window;

    /// How the windowed response is put into units.
    fn normalisation(&self) -> Normalisation;

    /// Pointwise stencil response over a whole plane, **replicate-clamped** at
    /// the border.
    ///
    /// `out` is `geom.pixels()` long and may contain anything on entry.
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]);

    /// Apply the operator's own window. Defaulted for [`Window::None`] and
    /// [`Window::Box`].
    ///
    /// # Panics
    ///
    /// The default implementation panics for [`Window::Custom`], which is the
    /// contract: declaring a custom window and not overriding this is a
    /// programming error, and a silent identity here would be a silently
    /// mis-scaled gate.
    fn aggregate(
        &self,
        response: &[f32],
        geom: PlaneGeometry,
        scratch: &mut [f32],
        out: &mut [f32],
    ) {
        match self.window() {
            Window::None => out.copy_from_slice(response),
            Window::Box { radius } => box_mean(response, geom, radius, scratch, out),
            Window::Custom { .. } => panic!(
                "focus measure `{}` declares Window::Custom but does not override \
                 FocusMeasure::aggregate",
                self.id()
            ),
        }
    }

    /// Put the windowed response into units. Defaulted for
    /// [`Normalisation::None`] and [`Normalisation::LumaSigma`].
    ///
    /// # Panics
    ///
    /// As [`FocusMeasure::aggregate`], for [`Normalisation::Custom`].
    fn normalise(&self, field: &mut [f32], luma: &[f32], noise: &NoiseModel) {
        match self.normalisation() {
            Normalisation::None => {}
            // `degree == 1` routes through the module's own
            // `normalise_by_luma_sigma` rather than through `powi(1)`, so the
            // shipped operator and every degree-1 contribution divide by
            // literally the same code.
            Normalisation::LumaSigma { degree: 1 } => normalise_by_luma_sigma(field, luma, noise),
            Normalisation::LumaSigma { degree } => {
                for (f, l) in field.iter_mut().zip(luma) {
                    let sigma = noise.green_luma_sigma(*l).max(SIGMA_EPS);
                    *f /= sigma.powi(degree as i32);
                }
            }
            Normalisation::Custom => panic!(
                "focus measure `{}` declares Normalisation::Custom but does not \
                 override FocusMeasure::normalise",
                self.id()
            ),
        }
    }

    /// Furthest luma sample the response at a pixel reads, in plane pixels:
    /// `stencil_radius + window radius`. For the shipped operator this is
    /// `1 + 13 = 14`, which is [`SUPPORT_RADIUS`].
    ///
    /// This is **not** the plugin halo — the host's regulariser adds to it. See
    /// [`FieldConfig::plugin_halo`]. (Rule 15: "plugin halo", the rectangle
    /// expansion, never the bare word.)
    fn support_radius(&self) -> usize {
        self.stencil_radius() + self.window().radius()
    }
}

/// **The one implementation of the focus pipeline**, `respond -> aggregate ->
/// normalise`, over caller-supplied buffers.
///
/// Every field in this project is produced by this function:
/// [`FocusField::compute_at_radius`] calls it with [`Tenengrad`], and
/// [`FieldWorkspace::run`] calls it with whatever was contributed. That is not
/// tidiness — the order of the stages is what `FOCUS_NOISE_SD` is a measurement
/// *of*, and two spellings of it are two constants waiting to disagree.
///
/// `response` and `scratch` are working space; the finished field lands in
/// `out`. All four slices must be `geom.pixels()` long.
///
/// # Panics
///
/// If any slice is the wrong length.
pub fn run_measure(
    op: &dyn FocusMeasure,
    geom: PlaneGeometry,
    luma: &[f32],
    noise: &NoiseModel,
    response: &mut [f32],
    scratch: &mut [f32],
    out: &mut [f32],
) {
    let px = geom.pixels();
    assert_eq!(luma.len(), px, "luma plane is not {px} samples");
    assert_eq!(response.len(), px, "response plane is not {px} samples");
    assert_eq!(scratch.len(), px, "scratch plane is not {px} samples");
    assert_eq!(out.len(), px, "out plane is not {px} samples");
    op.respond(luma, geom, response);
    op.aggregate(response, geom, scratch, out);
    op.normalise(out, luma, noise);
}

/// `sqrt(Gx^2 + Gy^2)` under a box window, divided by the luma sigma — **the
/// shipped operator**, as a [`FocusMeasure`].
///
/// [`respond`](FocusMeasure::respond) calls [`gradient_magnitude`] and
/// [`aggregate`](FocusMeasure::aggregate) calls [`box_mean`], so this is not a
/// re-implementation of the shipped operator: it *is* the shipped operator,
/// named so the merge can be handed a different one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Tenengrad {
    id: std::borrow::Cow<'static, str>,
    radius: usize,
}

impl Tenengrad {
    /// `|grad|` at the radius actually in force — [`window_radius`], not the
    /// [`WINDOW_RADIUS`] constant.
    ///
    /// The distinction is load-bearing and was previously wrong. `strehl-plugin`
    /// built its "shipped" operator from the constant while
    /// [`FocusField::compute`] resolved [`WINDOW_RADIUS_ENV`], so under an
    /// override the two were different operators and the crate's bit-identity
    /// test would have failed for a reason neither crate mentions.
    #[must_use]
    pub fn shipped() -> Self {
        Self::at_radius(window_radius())
    }

    /// `|grad|` at an arbitrary window radius.
    ///
    /// Fact 510: a radius change alone is a **12.5% gate shift** (w13 -> w11
    /// gives `k` = 1.125), so the radius is part of the identity, not a
    /// decoration on it.
    #[must_use]
    pub fn at_radius(radius: usize) -> Self {
        // The two radii the shipped binary actually uses are borrowed, so the
        // per-frame path allocates nothing.
        let id = match radius {
            WINDOW_RADIUS => std::borrow::Cow::Borrowed("tenengrad-w13"),
            FINE_WINDOW_RADIUS => std::borrow::Cow::Borrowed("tenengrad-w2"),
            r => std::borrow::Cow::Owned(format!("tenengrad-w{r}")),
        };
        Self { id, radius }
    }

    /// The window radius this instance aggregates over.
    #[must_use]
    pub fn radius(&self) -> usize {
        self.radius
    }
}

impl FocusMeasure for Tenengrad {
    fn id(&self) -> &str {
        &self.id
    }
    fn stencil_radius(&self) -> usize {
        SOBEL_RADIUS
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

/// The half of the field configuration that belongs to the **host**: whether
/// the merge's regulariser is in the path, and at what radius.
///
/// `Copy`, and carried inside every calibrated registry entry, so a calibrated
/// operator cannot be run under a configuration it was not calibrated for.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FieldConfig {
    /// Radius of the host's regulariser box, or `None` for no regulariser.
    ///
    /// `Some(8)` is the shipped merge (fact 84: -35% absolute reconstruction
    /// error at width 17). `None` is the statistics scale, which is
    /// deliberately *not* regularised.
    pub regulariser_radius: Option<usize>,
}

impl FieldConfig {
    /// What [`crate::merge`] does: a 17x17 box over the focus field before a
    /// winner is elected.
    pub const SHIPPED: FieldConfig = FieldConfig {
        regulariser_radius: Some(crate::merge::REGULARISER_RADIUS),
    };

    /// No regulariser. What `through_focus.rs`'s fine field does, and the
    /// second of the two calibration targets in `strehl_plugin::self_check`.
    pub const BARE: FieldConfig = FieldConfig {
        regulariser_radius: None,
    };

    /// The regulariser radius as a number, with `None` reading 0.
    #[must_use]
    pub const fn regulariser_radius(self) -> usize {
        match self.regulariser_radius {
            Some(r) => r,
            None => 0,
        }
    }

    /// The **plugin halo**: the rectangle expansion, in plane pixels, that a
    /// tile of output needs beyond its own bounds under this operator and this
    /// regulariser.
    ///
    /// Rule 15 — this is the SYNTHESIS fact 32 sense of the word (a margin),
    /// never the occlusion-halo sense (an artifact at an occluding edge).
    #[must_use]
    pub fn plugin_halo(self, op: &dyn FocusMeasure) -> usize {
        op.support_radius() + self.regulariser_radius()
    }

    /// Margin discarded from every edge before a calibration SD is taken.
    ///
    /// `max(stencil_radius + 1, 2) + window_radius + regulariser_radius`.
    ///
    /// The box filter is **replicate-clamped**, so pixels within one combined
    /// support of the edge see a smaller, differently-weighted window and are
    /// not stationary. Including them biases the SD, and the bias moves with
    /// the plane size.
    ///
    /// For a 3x3 stencil this is `window_radius + 2 + regulariser_radius` — 23
    /// for the shipped configuration, 4 for the fine one.
    #[must_use]
    pub fn calibration_margin(self, op: &dyn FocusMeasure) -> usize {
        let stencil = (op.stencil_radius() + 1).max(2);
        stencil + op.window().radius() + self.regulariser_radius()
    }
}

/// Reusable buffers for one plane, so a contributed operator's field can be
/// computed per frame without allocating.
///
/// **Three f32 planes**, the same footprint as [`FocusField`]. That is
/// deliberate: M8's measured memory ratchet prices the per-worker term, and a
/// fourth plane here would move it by 33% for nothing.
pub struct FieldWorkspace {
    geom: PlaneGeometry,
    response: Vec<f32>,
    windowed: Vec<f32>,
    scratch: Vec<f32>,
    /// Which of `response` / `windowed` holds the finished field.
    out_in_response: bool,
}

impl FieldWorkspace {
    #[must_use]
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            response: vec![0.0; geom.pixels()],
            windowed: vec![0.0; geom.pixels()],
            scratch: vec![0.0; geom.pixels()],
            out_in_response: false,
        }
    }

    #[must_use]
    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }

    /// Bytes of scratch held, for the memory budget report.
    #[must_use]
    pub fn allocated_bytes(&self) -> usize {
        3 * self.geom.pixels() * std::mem::size_of::<f32>()
    }

    /// Run one operator over one plane, through the host's own configuration,
    /// and return the finished field.
    ///
    /// # Panics
    ///
    /// If `luma` is not `geom.pixels()` long.
    pub fn run(
        &mut self,
        op: &dyn FocusMeasure,
        cfg: FieldConfig,
        luma: &[f32],
        noise: &NoiseModel,
    ) -> &[f32] {
        run_measure(
            op,
            self.geom,
            luma,
            noise,
            &mut self.response,
            &mut self.scratch,
            &mut self.windowed,
        );
        match cfg.regulariser_radius {
            Some(r) => {
                box_mean(
                    &self.windowed,
                    self.geom,
                    r,
                    &mut self.scratch,
                    &mut self.response,
                );
                self.out_in_response = true;
            }
            None => self.out_in_response = false,
        }
        self.values()
    }

    /// The field produced by the last [`run`](Self::run).
    #[must_use]
    pub fn values(&self) -> &[f32] {
        if self.out_in_response {
            &self.response
        } else {
            &self.windowed
        }
    }

    /// Multiply the field in place — the one operation a *pre-normalised* field
    /// needs beyond [`run`](Self::run).
    ///
    /// Kept here rather than in the registry so the buffer never leaves the
    /// workspace: a caller cannot hold a `&mut [f32]` into the field and
    /// rescale it twice.
    pub fn scale_in_place(&mut self, scale: f32) -> &[f32] {
        let buf = if self.out_in_response {
            &mut self.response
        } else {
            &mut self.windowed
        };
        for v in buf.iter_mut() {
            *v *= scale;
        }
        if self.out_in_response {
            &self.response
        } else {
            &self.windowed
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::noise::{Levels, NoiseModel, PlaneNoise, Provenance};

    fn model() -> NoiseModel {
        let p = PlaneNoise {
            gain_dn_per_e: 0.229,
            read_noise_e: 1.47,
            levels: Levels {
                black: 512.0,
                white: 15360.0,
            },
        };
        NoiseModel::new([p; 4], 100.0, Provenance::Profile)
    }

    fn geometry(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// **The plugin seam does not fork the pipeline.**
    ///
    /// Both entry points a contributed operator can reach --
    /// [`FocusField::compute_with_measure`] and
    /// [`FocusField::compute_scaled_with_measure`] -- must reproduce their
    /// shipped counterparts bit-for-bit when handed [`Tenengrad::shipped`].
    /// That is not a courtesy: it is the reason `--focus` can exist at all
    /// without re-baselining `crates/strehl-cli/tests/byte-freezes.tsv`. If
    /// this test can fail, the default path has TWO implementations and one of
    /// them is unmeasured.
    ///
    /// The plane deliberately carries a hard luma step, because the step is
    /// what makes the normaliser's divisor vary across the window and is the
    /// input under which an off-by-one in the aggregate/normalise ORDER would
    /// show up. A flat plane cannot fail this.
    #[test]
    fn the_shipped_operator_through_the_plugin_entry_points_is_bit_identical() {
        use crate::edgeaware::SelectionScale;
        let (w, h) = (101, 83);
        let g = geometry(w, h);
        let luma: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = (i % w, i / w);
                700.0 + 250.0 * ((x * 7 + y * 3) % 13) as f32 + if y > 40 { 3000.0 } else { 0.0 }
            })
            .collect();
        let noise = model();

        let mut a = FocusField::new(g);
        a.compute(&luma, &noise);
        let want = a.values().to_vec();
        let mut b = FocusField::new(g);
        b.compute_with_measure(&Tenengrad::shipped(), &luma, &noise);
        assert_eq!(
            b.values().iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            want.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            "compute_with_measure(Tenengrad::shipped()) is not compute()"
        );

        // And the same for the per-pixel-radius path, at a level BELOW the
        // full window, so the ladder's gather is actually exercised rather
        // than collapsing to the case above. `assert_ne!` at the end is what
        // makes that claim rather than assuming it.
        let scale = SelectionScale::uniform(g, 1);
        let mut c = FocusField::new(g);
        c.compute_scaled(&luma, &noise, &scale);
        let want_scaled = c.values().to_vec();
        let mut d = FocusField::new(g);
        d.compute_scaled_with_measure(&Tenengrad::shipped(), &luma, &noise, &scale);
        assert_eq!(
            d.values().iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            want_scaled.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            "compute_scaled_with_measure(Tenengrad::shipped()) is not compute_scaled()"
        );
        assert_ne!(
            want_scaled.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            want.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            "the non-uniform scale collapsed to the full window; this test proves nothing"
        );
    }

    /// The edge-aware path must be the shipped operator when it is asked for
    /// the shipped radius — **bit for bit**, not to a tolerance.
    ///
    /// This is the whole safety argument for `compute_scaled`. M13's window
    /// ruling, `FOCUS_NOISE_SD`, the gate calibration and the byte-freeze all
    /// describe `compute`; if the multi-scale ladder rounded differently at
    /// `FULL_LEVEL` then every pixel away from a silhouette — which is most of
    /// every frame — would quietly stop being the thing those numbers were
    /// measured on.
    #[test]
    fn uniform_full_scale_is_the_shipped_operator() {
        use crate::edgeaware::{FULL_LEVEL, SelectionScale};
        let (w, h) = (61, 47);
        let g = geometry(w, h);
        let luma: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = (i % w, i / w);
                600.0 + 300.0 * ((x * 3 + y * 5) % 17) as f32 + if x > 30 { 2000.0 } else { 0.0 }
            })
            .collect();
        let mut a = FocusField::new(g);
        a.compute(&luma, &model());
        let want = a.values().to_vec();

        let mut b = FocusField::new(g);
        b.compute_scaled(&luma, &model(), &SelectionScale::uniform(g, FULL_LEVEL));

        assert_eq!(
            b.values(),
            &want[..],
            "the multi-scale path is not bit-identical to compute() at the full radius"
        );
    }

    /// A narrower level must actually narrow the support, or the scale map is
    /// decorative. Read at a pixel far enough from the step that the wide
    /// window straddles it and the narrow one cannot.
    #[test]
    fn a_narrow_level_excludes_content_the_wide_window_reaches() {
        use crate::edgeaware::{LEVEL_RADII, SelectionScale};
        let (w, h) = (81, 81);
        let g = geometry(w, h);
        // Flat everywhere except a single high-contrast column at x = 40.
        let luma: Vec<f32> = (0..w * h)
            .map(|i| if i % w == 40 { 9000.0 } else { 700.0 })
            .collect();

        let probe = 40 - 6; // 6 px from the only gradient in the plane
        let mut wide = FocusField::new(g);
        wide.compute(&luma, &model());
        let wide_v = wide.values()[40 * w + probe];

        let narrow_level = 1u8; // radius 2
        assert!(LEVEL_RADII[narrow_level as usize] < 6);
        let mut narrow = FocusField::new(g);
        narrow.compute_scaled(&luma, &model(), &SelectionScale::uniform(g, narrow_level));
        let narrow_v = narrow.values()[40 * w + probe];

        assert!(
            wide_v > 0.0,
            "the wide window should see the column from 6 px away"
        );
        assert_eq!(
            narrow_v, 0.0,
            "a radius-2 window 6 px from the only edge in the plane must see \
             nothing, got {narrow_v}"
        );
    }

    fn field(w: usize, h: usize, luma: &[f32]) -> Vec<f32> {
        let mut f = FocusField::new(geometry(w, h));
        f.compute(luma, &model());
        f.values().to_vec()
    }

    /// A per-frame photometric gain moves the normalised focus response by
    /// `sqrt(g)`, not by `g` and not by nothing.
    ///
    /// This is the claim M18's photometric-sensitivity report is built on, and
    /// it is the reason a gain drift is not photometrically neutral to the gate:
    /// the response is `box_mean(|grad L|) / sigma(L)`, so scaling `L` by `g`
    /// scales the numerator by exactly `g`, while in the shot-noise-limited
    /// regime `sigma ~ sqrt(S)` scales the denominator by `sqrt(g)`.
    ///
    /// **What would make this fail:** normalising by something that is not the
    /// signal-dependent sigma (a constant divisor would give `g`, no divisor
    /// would give `g`), or running it at a level where read noise dominates and
    /// sigma is flat (which would also give `g`). Both are real, reachable
    /// states of this code, so this is evidence and not arithmetic. The level is
    /// chosen deep in the shot-limited regime on purpose: at 8000 DN with
    /// gain 0.229 the shot term is ~1832 against a read term of ~0.11.
    #[test]
    fn a_per_frame_gain_scales_the_normalised_response_by_its_square_root() {
        let (w, h) = (64usize, 64usize);
        let base: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                8000.0
                    + 900.0 * (x * 1.9).sin() * (y * 1.7).cos()
                    + 500.0 * (x * 0.83 + y * 0.61).sin()
            })
            .collect();
        let g = 1.44f32;
        let scaled: Vec<f32> = base.iter().map(|v| v * g).collect();

        let interior_mean = |v: &[f32]| -> f64 {
            let m = SUPPORT_RADIUS;
            let mut s = 0.0f64;
            let mut n = 0usize;
            for y in m..h - m {
                for x in m..w - m {
                    s += v[y * w + x] as f64;
                    n += 1;
                }
            }
            s / n as f64
        };
        let a = interior_mean(&field(w, h, &base));
        let b = interior_mean(&field(w, h, &scaled));
        let ratio = b / a;
        let expected = (g as f64).sqrt();
        assert!(
            (ratio - expected).abs() < 0.01,
            "a gain of {g} must move the response by sqrt(g) = {expected:.4}, got {ratio:.4}"
        );
        // And the positive control that separates sqrt(g) from g: the
        // UNNORMALISED response must move by the full g, so the test is
        // discriminating between the two hypotheses rather than accepting both.
        let ua = interior_mean(&unnormalised(w, h, &base, WINDOW_RADIUS));
        let ub = interior_mean(&unnormalised(w, h, &scaled, WINDOW_RADIUS));
        let uratio = ub / ua;
        assert!(
            (uratio - g as f64).abs() < 1e-3,
            "the unnormalised response must move by the full g = {g}, got {uratio:.4}"
        );
    }

    fn unnormalised(w: usize, h: usize, luma: &[f32], radius: usize) -> Vec<f32> {
        let geom = geometry(w, h);
        let (mut grad, mut scratch, mut out) = (
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
        );
        gradient_magnitude(luma, geom, &mut grad);
        if radius == 0 {
            return grad;
        }
        box_mean(&grad, geom, radius, &mut scratch, &mut out);
        out
    }

    /// The retired ring difference, `|mean_3x3 - mean_7x7| / sigma`, kept only
    /// so the two regression tests below can measure the replacement against
    /// the thing it replaced on the axes M11 scored. This is a verbatim copy of
    /// the operator `focus.rs` shipped before M14 and must not be revived.
    fn ring_field(w: usize, h: usize, luma: &[f32]) -> Vec<f32> {
        let geom = geometry(w, h);
        let (mut scratch, mut inner, mut outer) = (
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
        );
        box_mean(luma, geom, 1, &mut scratch, &mut inner);
        box_mean(luma, geom, 3, &mut scratch, &mut outer);
        let noise = model();
        for i in 0..geom.pixels() {
            let ring = (inner[i] - outer[i]).abs();
            inner[i] = ring / noise.green_luma_sigma(luma[i]).max(SIGMA_EPS);
        }
        inner
    }

    #[test]
    fn a_flat_plane_has_zero_focus_everywhere_including_the_border() {
        // The border policy is load-bearing twice over: a zero-padded box would
        // leave a bright rim here, and so would a zero-padded Sobel.
        let luma = vec![4000.0f32; 61 * 45];
        let got = field(61, 45, &luma);
        assert!(
            got.iter().all(|v| *v < 1e-3),
            "max was {:?}",
            got.iter().cloned().fold(f32::MIN, f32::max)
        );
    }

    #[test]
    fn resolved_texture_scores_higher_than_the_same_texture_blurred() {
        // NOTE for anyone restoring the pre-M14 version of this test: a single
        // monotone step will NOT discriminate here. The mean of |grad| over a
        // window wider than the blur is the total variation across the window
        // divided by its area, and blurring a monotone edge conserves total
        // variation exactly. Texture is what defocus actually destroys, because
        // texture's gradients change sign and cancel; use texture.
        let (w, h) = (64usize, 64usize);
        let sharp: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                2000.0
                    + 400.0 * (x * 1.9).sin() * (y * 1.7).cos()
                    + 250.0 * (x * 0.83 + y * 0.61).sin()
            })
            .collect();
        let mut scratch = vec![0.0f32; w * h];
        let mut soft = vec![0.0f32; w * h];
        box_mean(&sharp, geometry(w, h), 2, &mut scratch, &mut soft);

        let a = field(w, h, &sharp);
        let b = field(w, h, &soft);
        let interior = |v: &[f32]| -> f64 {
            let m = SUPPORT_RADIUS;
            let mut s = 0.0f64;
            let mut n = 0usize;
            for y in m..h - m {
                for x in m..w - m {
                    s += v[y * w + x] as f64;
                    n += 1;
                }
            }
            s / n as f64
        };
        let (sh, so) = (interior(&a), interior(&b));
        assert!(sh > 1.5 * so, "sharp {sh:.4} vs soft {so:.4}");
    }

    #[test]
    fn normalisation_penalises_the_same_contrast_at_a_higher_signal_level() {
        // Shot noise grows with signal, so an equal-DN feature is less evidence
        // of detail on a bright background than on a dark one. That is the
        // whole point of dividing by sigma.
        let (w, h) = (41usize, 41usize);
        let build = |base: f32| {
            let mut v = vec![base; w * h];
            for y in 0..h {
                v[y * w + 20] = base + 100.0;
            }
            v
        };
        let dark = field(w, h, &build(200.0));
        let bright = field(w, h, &build(12000.0));
        let peak = |v: &[f32]| v.iter().cloned().fold(f32::MIN, f32::max);
        assert!(peak(&dark) > peak(&bright));
    }

    #[test]
    fn focus_is_finite_and_non_negative_at_zero_signal() {
        // Below the read-noise floor sigma is small but never zero.
        let luma = vec![0.0f32; 33 * 33];
        let got = field(33, 33, &luma);
        assert!(got.iter().all(|v| v.is_finite() && *v >= 0.0));
    }

    #[test]
    fn the_running_sum_agrees_with_a_naive_gather_of_the_same_operator() {
        // The cost result (M13 §5, flat in radius) depends entirely on the box
        // being a running sum. This pins the two forms together so the fast
        // path cannot drift from the definition it is standing in for.
        let (w, h) = (37usize, 29usize);
        let luma: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                3000.0 + 900.0 * (x * 0.7).sin() * (y * 1.3).cos() + 40.0 * ((i * 7919) % 13) as f32
            })
            .collect();
        let got = field(w, h, &luma);

        let geom = geometry(w, h);
        let mut grad = vec![0.0f32; geom.pixels()];
        gradient_magnitude(&luma, geom, &mut grad);
        let noise = model();
        for y in 0..h {
            for x in 0..w {
                let (x0, x1) = (
                    x.saturating_sub(WINDOW_RADIUS),
                    (x + WINDOW_RADIUS).min(w - 1),
                );
                let (y0, y1) = (
                    y.saturating_sub(WINDOW_RADIUS),
                    (y + WINDOW_RADIUS).min(h - 1),
                );
                let (mut sum, mut n) = (0.0f64, 0u32);
                for yy in y0..=y1 {
                    for xx in x0..=x1 {
                        sum += grad[yy * w + xx] as f64;
                        n += 1;
                    }
                }
                let i = y * w + x;
                let want = (sum / n as f64) as f32 / noise.green_luma_sigma(luma[i]).max(SIGMA_EPS);
                let tol = 1e-3 * want.abs().max(1e-3);
                assert!(
                    (got[i] - want).abs() <= tol,
                    "at ({x},{y}): got {} want {want}",
                    got[i]
                );
            }
        }
    }

    // ---------------------------------------------------------------- plants

    /// SplitMix64, so both plants below are byte-reproducible on any machine.
    struct Rng(u64);

    impl Rng {
        fn next_u64(&mut self) -> u64 {
            self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = self.0;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            z ^ (z >> 31)
        }

        fn unit(&mut self) -> f32 {
            (self.next_u64() >> 40) as f32 / 16_777_216.0
        }

        /// Irwin-Hall(12) - 6: mean 0, variance 1, bounded at +/-6 sigma.
        fn normal(&mut self) -> f32 {
            (0..12).map(|_| self.unit()).sum::<f32>() - 6.0
        }
    }

    /// Winner index per pixel by argmax over frames, with the same lowest-index
    /// tie-break `Selection::beats` uses.
    fn winners(fields: &[Vec<f32>]) -> Vec<usize> {
        let n = fields[0].len();
        (0..n)
            .map(|i| {
                let mut best = 0usize;
                for k in 1..fields.len() {
                    if fields[k][i] > fields[best][i] {
                        best = k;
                    }
                }
                best
            })
            .collect()
    }

    /// A selector with no coupling to the pixel's own noise at all: M2's
    /// placebo, and the control every claim below is quoted against.
    fn random_fields(frames: usize, pixels: usize) -> Vec<Vec<f32>> {
        (0..frames)
            .map(|k| {
                (0..pixels)
                    .map(|i| Rng(0xF10C ^ (i as u64) << 20 ^ (k as u64)).unit())
                    .collect()
            })
            .collect()
    }

    fn sd_interior(v: &[f32], w: usize, h: usize, margin: usize) -> f64 {
        let mut s = Vec::with_capacity((w - 2 * margin) * (h - 2 * margin));
        for y in margin..h - margin {
            for x in margin..w - margin {
                s.push(v[y * w + x] as f64);
            }
        }
        let mean = s.iter().sum::<f64>() / s.len() as f64;
        (s.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / s.len() as f64).sqrt()
    }

    #[test]
    fn tenengrad_elects_less_of_the_pixels_own_noise_than_the_ring_did() {
        // M11's noise axis, in miniature: N = sd(argmax-merged flat region) /
        // sd(the same region in one frame). MEASURED on real frames, N is
        // 1.3475x for ring(1,3) and 1.1324x for tenengrad-w5 (SYNTHESIS fact
        // 41); M13 measures 1.0864x at the w13 shipped here. This plant is
        // synthetic and its absolute numbers are its own, but the ORDERING is
        // the published claim and it is what this pins.
        //
        // Rule 11's placebo is the third arm: a selector with an identical
        // winner histogram but no coupling to the pixel's own noise must land
        // at 1.0. Without it, any ratio above 1 could be the plant's fault.
        let (w, h, frames) = (128usize, 128usize, 22usize);
        let noise = model();
        let level = 2000.0f32;
        let sigma = noise.green_luma_sigma(level);
        let mut rng = Rng(0x5EED_0001);
        let planes: Vec<Vec<f32>> = (0..frames)
            .map(|_| (0..w * h).map(|_| level + sigma * rng.normal()).collect())
            .collect();

        let merged = |fields: &[Vec<f32>]| -> f64 {
            let win = winners(fields);
            let out: Vec<f32> = (0..w * h).map(|i| planes[win[i]][i]).collect();
            sd_interior(&out, w, h, 24)
        };
        let single = sd_interior(&planes[frames / 2], w, h, 24);

        let ten: Vec<Vec<f32>> = planes.iter().map(|p| field(w, h, p)).collect();
        let ring: Vec<Vec<f32>> = planes.iter().map(|p| ring_field(w, h, p)).collect();
        let placebo = random_fields(frames, w * h);

        let (n_ten, n_ring, n_placebo) = (
            merged(&ten) / single,
            merged(&ring) / single,
            merged(&placebo) / single,
        );
        println!(
            "flat plant: N(tenengrad-w{WINDOW_RADIUS}) = {n_ten:.4}, N(ring-1-3) = {n_ring:.4}, \
             N(placebo) = {n_placebo:.4}, single sd = {single:.3} DN"
        );

        assert!(
            (n_placebo - 1.0).abs() < 0.03,
            "the placebo must not manufacture an excess, got {n_placebo:.4}"
        );
        assert!(
            n_ring > 1.10,
            "the ring's defect must reproduce on this plant, got {n_ring:.4}"
        );
        assert!(
            n_ten < n_ring,
            "tenengrad {n_ten:.4} must elect less noise than the ring {n_ring:.4}"
        );
        // The measured gap on real frames is 1.3475 -> 1.0864, i.e. the excess
        // falls by 74%. Require most of that here, not merely a sign.
        assert!(
            (n_ten - 1.0) < 0.5 * (n_ring - 1.0),
            "tenengrad excess {:.4} must be less than half the ring's {:.4}",
            n_ten - 1.0,
            n_ring - 1.0
        );
    }

    #[test]
    fn tenengrad_picks_the_correct_frame_far_more_often_than_the_ring_did() {
        // M11's selectivity axis. The plant is FRONTO-PARALLEL: one true frame
        // everywhere. That is deliberate and it is also a limit -- SYNTHESIS
        // fact 62 says such a plant cannot produce a window optimum, so this
        // test may never be quoted as evidence about WINDOW_RADIUS. It compares
        // two fixed operators, which is a question a flat plant can answer.
        let (w, h, frames) = (96usize, 96usize, 15usize);
        let truth = 7usize;
        let geom = geometry(w, h);
        let sharp: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                2400.0
                    + 500.0 * (x * 1.61).sin() * (y * 1.37).cos()
                    + 300.0 * (x * 0.53 - y * 0.71).sin()
                    + 200.0 * (x * 2.31 + y * 0.19).cos()
            })
            .collect();

        let mut rng = Rng(0x5EED_0002);
        let noise = model();
        let mut scratch = vec![0.0f32; w * h];
        let planes: Vec<Vec<f32>> = (0..frames)
            .map(|k| {
                let blur = k.abs_diff(truth);
                let mut plane = vec![0.0f32; w * h];
                if blur == 0 {
                    plane.copy_from_slice(&sharp);
                } else {
                    box_mean(&sharp, geom, blur, &mut scratch, &mut plane);
                }
                for v in plane.iter_mut() {
                    *v += noise.green_luma_sigma(*v) * rng.normal();
                }
                plane
            })
            .collect();

        let hit_rate = |fields: &[Vec<f32>]| -> f64 {
            let win = winners(fields);
            let m = SUPPORT_RADIUS + 2;
            let (mut hit, mut n) = (0usize, 0usize);
            for y in m..h - m {
                for x in m..w - m {
                    if win[y * w + x] == truth {
                        hit += 1;
                    }
                    n += 1;
                }
            }
            hit as f64 / n as f64
        };

        let ten: Vec<Vec<f32>> = planes.iter().map(|p| field(w, h, p)).collect();
        let ring: Vec<Vec<f32>> = planes.iter().map(|p| ring_field(w, h, p)).collect();
        let placebo = random_fields(frames, w * h);
        let (a_ten, a_ring, a_placebo) = (hit_rate(&ten), hit_rate(&ring), hit_rate(&placebo));
        println!(
            "planted plant: exact-hit tenengrad-w{WINDOW_RADIUS} = {a_ten:.4}, ring-1-3 = \
             {a_ring:.4}, placebo = {a_placebo:.4}, chance = {:.4}",
            1.0 / frames as f64
        );

        let chance = 1.0 / frames as f64;
        assert!(
            (a_placebo - chance).abs() < 0.02,
            "the placebo must sit at chance {chance:.4}, got {a_placebo:.4}"
        );
        assert!(
            a_ring > chance,
            "the ring must beat chance or the plant is broken, got {a_ring:.4}"
        );
        assert!(
            a_ten > a_ring,
            "tenengrad {a_ten:.4} must beat the ring {a_ring:.4}"
        );
        assert!(
            a_ten > 0.9,
            "tenengrad should be near-perfect on a fronto-parallel plant, got {a_ten:.4}"
        );
    }

    // ------------------------------------------------------- centre-tap probe

    /// How much of this measure's response at a pixel comes from that pixel's
    /// own value, by finite difference on the shipped code path.
    ///
    /// Shift invariance away from the border makes `d focus(q) / d luma(p)` a
    /// function of `q - p` alone, so perturbing one pixel yields the whole
    /// sensitivity kernel and `phi = |dr(0)| / sum |dr(d)|` falls straight out.
    ///
    /// `probe` selects the stage: the shipped normalised operator, or M11's
    /// `Norm::None` arm at a given radius. The distinction matters — fact 39 is
    /// that windowing and normalisation each contribute a centre tap, so phi is
    /// a property of the **configured stage**, never of the kernel.
    fn centre_tap_fraction(
        delta: f32,
        amplitude: f32,
        reach: usize,
        probe: impl Fn(usize, usize, &[f32]) -> Vec<f32>,
    ) -> (f64, usize) {
        // Big enough that every window the probe touches is unclamped: a pixel
        // `reach` away reads a further SUPPORT_RADIUS, so the centre needs that
        // much clear space on all sides.
        let side = 2 * (reach + SUPPORT_RADIUS) + 3;
        let (w, h) = (side, side);
        // Deterministic textured field. A flat field will not do: the response
        // is identically zero there and the finite difference would measure the
        // rectification kink instead of the operator.
        let luma: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                3000.0
                    + amplitude * (x * 1.31).sin() * (y * 1.07).cos()
                    + 0.5 * amplitude * (x * 0.37 + y * 0.29).sin()
            })
            .collect();
        let base = probe(w, h, &luma);
        let mut bumped = luma.clone();
        let centre = (h / 2) * w + w / 2;
        bumped[centre] += delta;
        let bump = probe(w, h, &bumped);

        let (mut at_centre, mut total, mut taps) = (0.0f64, 0.0f64, 0usize);
        for dy in 0..2 * reach + 1 {
            for dx in 0..2 * reach + 1 {
                let q = (h / 2 + dy - reach) * w + (w / 2 + dx - reach);
                let d = ((bump[q] - base[q]) as f64 / delta as f64).abs();
                if d > 1e-6 {
                    taps += 1;
                }
                if dx == reach && dy == reach {
                    at_centre = d;
                }
                total += d;
            }
        }
        (at_centre / total, taps)
    }

    #[test]
    fn centre_tap_fraction_and_read_extent_are_what_m13_specified() {
        // Successor to `centre_tap_fraction_is_the_value_m9_measured`, which
        // pinned phi = 1/18 and 49 taps for ring(1,3). M11 and M13 §6.4 both
        // said this test must be UPDATED, not deleted: phi is the quantity M9
        // measured argmax's noise excess to track (rho = +0.918 / +0.894
        // against support radius's -0.170 / -0.243, SYNTHESIS fact 35), so a
        // regression in it means the merge's noise-election behaviour changed.
        //
        // What can and cannot be pinned is different now, and that difference
        // is the point:
        //
        //   - The TAP COUNT is analytic. `(2*(SOBEL_RADIUS + WINDOW_RADIUS)+1)^2
        //     = 29^2 = 841`. It pins both radii exactly and it is asserted
        //     exactly.
        //   - phi ITSELF IS NOT. For ring(1,3), phi = 1/(2*(2*inner+1)^2) is a
        //     property of the kernel alone. Under a box window plus pointwise
        //     sigma normalisation it is texture- and probe-dependent: M13 §1.4
        //     measures 0.1390 at w13 on 109MSDCF texture at delta = 8 DN, and
        //     0.1321 / 0.1107 at delta = 1 / 32 DN on the SAME ROI. Pinning
        //     0.1390 to 4 dp would pin a property of one ROI and one probe
        //     amplitude. Step 2 below shows it moving 47x on this plant alone.
        //   - The un-normalised arm IS analytic, and it is asserted, because it
        //     is the half of fact 39 that does not depend on the scene. So are
        //     the two structural relations phi does obey: the divisor dominates
        //     the centre tap, and phi tracks texture contrast.

        // 1. Read extent, on the shipped operator. Analytic, exact.
        let reach = SUPPORT_RADIUS + 2;
        let (phi, taps) = centre_tap_fraction(8.0, 120.0, reach, field);
        let analytic_taps = (2 * SUPPORT_RADIUS + 1).pow(2);
        assert_eq!(analytic_taps, 841);
        assert_eq!(
            taps,
            analytic_taps,
            "read extent must be the {}x{} square that a {}x{} Sobel under a \
             {}x{} box implies, got {taps} taps",
            2 * SUPPORT_RADIUS + 1,
            2 * SUPPORT_RADIUS + 1,
            2 * SOBEL_RADIUS + 1,
            2 * SOBEL_RADIUS + 1,
            2 * WINDOW_RADIUS + 1,
            2 * WINDOW_RADIUS + 1,
        );

        // 2. phi on the whole configured stage. NOT pinned to a number, and
        // this is the evidence for why not. M13 §6.4 suggested a bracket of
        // `0.10 < phi < 0.18` around its measured 0.1390. **That bracket does
        // not survive off 109MSDCF texture.** On this synthetic probe phi is a
        // near-linear function of texture contrast, spanning 47x over a 64x
        // amplitude range while the operator does not change at all:
        //
        //     amplitude   30     60    120    240    480    960   1920
        //     phi     0.0085 0.0228 0.0516 0.1036 0.1864 0.2959 0.3987
        //
        // (delta = 8 DN; measured by this same probe.) Landing inside
        // 0.10-0.18 needs an amplitude near 330 DN, chosen to match one ROI.
        // Asserting the bracket would therefore pin the plant, which is the
        // exact failure M13 §6.4 said to avoid. What IS operator-intrinsic is
        // asserted instead, below.
        println!(
            "phi(tenengrad-w{WINDOW_RADIUS}, sigma-normalised) = {phi:.5} on synthetic \
             texture at amplitude 120 DN (M13: 0.1390 on real 109MSDCF texture)"
        );
        assert!(
            (0.005..0.30).contains(&phi),
            "phi {phi:.5} left even the loose sanity band; something structural changed"
        );

        // 3. The analytic anchors, on M11's Norm::None arm.
        //
        // (a) At window 0 the un-normalised response is the bare Sobel
        //     magnitude, and BOTH Sobel kernels have a zero centre weight, so a
        //     perturbation at p cannot change the response AT p. phi is exactly
        //     zero, not approximately -- this is a derivation, and M13's
        //     phi-nonorm CSV measures 0.0000000000 for it. The 8 taps are the
        //     8 neighbours that do respond; a 3x3 stencil with a live centre
        //     would report 9.
        let (phi_w0, taps_w0) = centre_tap_fraction(8.0, 120.0, SOBEL_RADIUS + 2, |w, h, l| {
            unnormalised(w, h, l, 0)
        });
        assert_eq!(phi_w0, 0.0, "the Sobel centre weight is 0 in Gx and Gy");
        assert_eq!(
            taps_w0, 8,
            "a 3x3 stencil with a dead centre has 8 live taps"
        );

        // (b) At window 13 the box mean dilutes that single live tap over its
        //     own area, so phi_nonorm -> 1/(2w+1)^2 from below. M13 §1.4
        //     measures the ratio climbing 0.62 -> 0.978 across w1 -> w40, and
        //     0.94 at w13 (0.00128784 measured against 0.00137174 analytic).
        //     The shortfall is the Sobel's own 3x3 support, which is not a
        //     point.
        let (phi_nonorm, taps_nonorm) = centre_tap_fraction(8.0, 120.0, reach, |w, h, l| {
            unnormalised(w, h, l, WINDOW_RADIUS)
        });
        assert_eq!(taps_nonorm, analytic_taps);
        let analytic = 1.0 / ((2 * WINDOW_RADIUS + 1) as f64).powi(2);
        assert!((analytic - 1.0 / 729.0).abs() < 1e-12);
        let ratio = phi_nonorm / analytic;
        println!(
            "phi(tenengrad-w{WINDOW_RADIUS}, un-normalised) = {phi_nonorm:.8}, analytic \
             1/{}^2 = {analytic:.8}, ratio {ratio:.4} (M13 measured 0.94)",
            2 * WINDOW_RADIUS + 1
        );
        assert!(
            (0.88..1.0).contains(&ratio),
            "un-normalised phi {phi_nonorm:.8} is {ratio:.4} of the analytic \
             {analytic:.8}; M13 §1.4 measures 0.94 at w13 and the limit is 1.0 \
             from below"
        );

        // 4. Fact 39, on this code path: windowing and pointwise normalisation
        //    each re-introduce a centre tap, and at this window the DIVISOR is
        //    the one that matters. The operator's own diluted tap is 1/729 of
        //    its response; the configured stage's is tens of times larger. If
        //    the divisor were ever dropped or moved off the centre pixel, this
        //    ratio would collapse to 1 and the merge's noise-election
        //    behaviour would change with it.
        assert!(
            phi > 20.0 * phi_nonorm,
            "the sigma divisor must dominate the centre tap: phi {phi:.5} vs \
             un-normalised {phi_nonorm:.8}"
        );

        // 5. And the texture dependence itself, asserted rather than asserted
        //    around. Quadrupling the probe's contrast must move phi several
        //    fold, because the divisor's centre tap scales with the response
        //    while the operator's does not. This is the property that makes a
        //    4-dp pin meaningless, so it is the property the test states.
        let (phi_hi, _) = centre_tap_fraction(8.0, 480.0, reach, field);
        println!("phi at amplitude 480 DN = {phi_hi:.5}, at 120 DN = {phi:.5}");
        assert!(
            phi_hi > 2.5 * phi,
            "phi must track texture contrast: {phi_hi:.5} at 480 DN against \
             {phi:.5} at 120 DN"
        );

        // 6. Discrimination. The tap count is what pins WINDOW_RADIUS, and it
        //    does so exactly: a one-step change moves it by 4*SUPPORT_RADIUS+4
        //    = 60 taps.
        assert_ne!(analytic_taps, (2 * (SUPPORT_RADIUS - 1) + 1).pow(2));
        assert_ne!(analytic_taps, (2 * (SUPPORT_RADIUS + 1) + 1).pow(2));
    }
}
