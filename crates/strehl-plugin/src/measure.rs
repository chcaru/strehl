//! The `FocusMeasure` contract — and the one method it deliberately does not
//! have.
//!
//! # What is missing, and why
//!
//! There is no `fn noise_sd(&self) -> f32`, no `NoiseCalibration` field, and no
//! way for an implementor to tell the host how noisy its response is. That
//! omission is the whole design (workstream E §F5.3 option A, SYNTHESIS
//! fact 502). The host measures it instead — see [`crate::calibrate`].
//!
//! Three reasons, in increasing order of how much they bind:
//!
//! 1. A declaration can be wrong; a measurement cannot be wrong in the same
//!    way. Fault 5 of §F4.6 becomes **unrepresentable** rather than merely
//!    detectable, because there is no place in this file to put a wrong number.
//! 2. **A declared constant is under-determined in principle.** The response SD
//!    depends on the operator, on the operator's own window, *and* on the
//!    host's regulariser radius — which the plugin cannot know. Fact 500 is
//!    this repository dividing two of its own constants that differed in
//!    exactly that and overstating a ratio by 3.27x.
//! 3. Changing [`REGULARISER_RADIUS`](strehl_core::merge::REGULARISER_RADIUS)
//!    would silently stale every declared constant in the ecosystem. A measured
//!    one re-derives.
//!
//! # The shape the trait has to fit
//!
//! Every operator in fact 439's survey decomposes into the same three stages,
//! and this trait is that decomposition:
//!
//! ```text
//! respond()    pointwise stencil, replicate-clamped   e.g. sqrt(Gx^2 + Gy^2)
//! aggregate()  the operator's OWN window              e.g. a 27x27 box mean
//! normalise()  into units                             e.g. / sigma_L(p)
//! ```
//!
//! The host then applies its own regulariser on top (see [`crate::field`]).
//! The split is not cosmetic: the calibrator needs the stencil radius and the
//! window radius **separately** to size the margin it discards, and fact 152
//! is the standing reminder that an operator and its window are one object
//! rather than two independent parameters.
//!
//! [`Window::Custom`] and [`Normalisation::Custom`] are the escape hatches for
//! operators that are not separable and normalisers that are not a pointwise
//! divide. They exist because the survey's seven operators are all separable
//! and pointwise, which is a fact about textbook focus measures rather than a
//! constraint anyone should inherit from them.

use strehl_core::boxfilter::box_mean;
use strehl_core::noise::NoiseModel;
use strehl_core::plane::PlaneGeometry;

/// Divisor floor for [`Normalisation::LumaSigma`], in DN.
///
/// Mirrors the private `SIGMA_EPS` in `strehl-core`'s `focus.rs`. It is not
/// re-exported there, so this is a copy — and
/// `crate::field::tests::the_shipped_operator_reproduces_focus_field_bit_for_bit`
/// is what stops the copy drifting: if `focus.rs` changed its floor, the
/// bit-identity test against `FocusField::compute` would go red.
pub const SIGMA_EPS: f32 = 1e-3;

/// The operator's own aggregation window — the stage between the stencil and
/// the normaliser.
///
/// This is **not** the host's regulariser. The two are separate boxes applied
/// in sequence, and conflating them is the fault fact 500 records: the
/// project's two published noise constants differ in whether the second box
/// was present, and were then divided by one another.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Window {
    /// The stencil response is the field. `ring(1,3)` as originally shipped was
    /// this; under fact 439's survey configuration it is not.
    None,
    /// Separable running-sum box mean of the given radius, via
    /// [`strehl_core::boxfilter::box_mean`]. **O(1) in the radius**, which is
    /// what makes M13's window ruling valid (cost flat to 2.53% over w1-w40).
    Box { radius: usize },
    /// The operator aggregates itself over a `radius`-wide support and **must**
    /// override [`FocusMeasure::aggregate`].
    ///
    /// The host cannot assume the cost is O(1) in the radius here, which is the
    /// case §F5.3 flags as degrading option A back to option B: an operator
    /// with an expensive aggregation is one whose load-time calibration is no
    /// longer bounded by fact 525's measured 5.02 ms per plane. (Fact 505's
    /// ~1.7 ms bound is refuted and must not be quoted; 5.02 ms is the measured
    /// figure that replaces it.)
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
/// sigma. `focus.rs` is explicit that this divisor is a **proxy** — it is the
/// sigma of a single luma sample, not of the windowed response — and is kept
/// because it is what M11 scored. Nothing here is entitled to improve on it
/// silently.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Normalisation {
    /// Leave the response as it is. M11's `Norm::None` arm.
    None,
    /// Divide pointwise by `max(sigma_L(p), SIGMA_EPS)^degree`.
    ///
    /// `degree` follows M11's parameterisation: a response that is homogeneous
    /// of degree `d` in the luma divides by `sigma^d`, so `|grad|` uses 1 and
    /// `|grad|^2` uses 2. **This is a convention, not a measurement** — M11
    /// scored the `degree = 1` arm and that is the only one with a published
    /// number behind it.
    LumaSigma { degree: u32 },
    /// The operator normalises itself and **must** override
    /// [`FocusMeasure::normalise`].
    Custom,
}

/// A contributed focus measure.
///
/// Implementors supply the three stages and the two radii. They do **not**
/// supply a noise constant, a tolerance, or a gate; see the module docs.
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
    /// Replicate rather than zero-pad: a zero-padded gradient manufactures a
    /// bright rim one stencil in from the edge and hands it to the merge as
    /// detail. `strehl-core`'s box filter clamps for the same reason.
    ///
    /// `out` is `geom.pixels()` long and may contain anything on entry.
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]);

    /// Apply the operator's own window. Defaulted for
    /// [`Window::None`] and [`Window::Box`].
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
            Normalisation::LumaSigma { degree } => {
                for (f, l) in field.iter_mut().zip(luma) {
                    let sigma = noise.green_luma_sigma(*l).max(SIGMA_EPS);
                    // `degree == 1` is spelled out rather than routed through
                    // powi(1) so that the shipped operator is bit-identical to
                    // `focus.rs`'s `normalise_by_luma_sigma`, which the field
                    // module asserts.
                    *f /= if degree == 1 {
                        sigma
                    } else {
                        sigma.powi(degree as i32)
                    };
                }
            }
            Normalisation::Custom => panic!(
                "focus measure `{}` declares Normalisation::Custom but does not \
                 override FocusMeasure::normalise",
                self.id()
            ),
        }
    }

    /// Furthest luma sample the response at a pixel reads, in plane pixels.
    ///
    /// `stencil_radius + window radius`. For the shipped operator this is
    /// `1 + 13 = 14`, which is exactly
    /// [`strehl_core::focus::SUPPORT_RADIUS`]; the field module asserts that.
    ///
    /// This is **not** the plugin halo — the host's regulariser adds to it. See
    /// [`crate::field::FieldConfig::plugin_halo`]. (Rule 15: "plugin halo", the
    /// rectangle expansion, never the bare word.)
    fn support_radius(&self) -> usize {
        self.stencil_radius() + self.window().radius()
    }
}

/// Replicate-clamped tap. Every reference operator reads through this.
#[inline]
#[must_use]
pub(crate) fn tap(luma: &[f32], w: usize, h: usize, x: isize, y: isize) -> f32 {
    let sx = x.clamp(0, w as isize - 1) as usize;
    let sy = y.clamp(0, h as isize - 1) as usize;
    luma[sy * w + sx]
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::noise::{Levels, PlaneNoise, Provenance};

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    struct Identity;

    impl FocusMeasure for Identity {
        fn id(&self) -> &str {
            "identity"
        }
        fn stencil_radius(&self) -> usize {
            0
        }
        fn window(&self) -> Window {
            Window::None
        }
        fn normalisation(&self) -> Normalisation {
            Normalisation::None
        }
        fn respond(&self, luma: &[f32], _geom: PlaneGeometry, out: &mut [f32]) {
            out.copy_from_slice(luma);
        }
    }

    struct DeclaresCustom;

    impl FocusMeasure for DeclaresCustom {
        fn id(&self) -> &str {
            "declares-custom"
        }
        fn stencil_radius(&self) -> usize {
            0
        }
        fn window(&self) -> Window {
            Window::Custom { radius: 4 }
        }
        fn normalisation(&self) -> Normalisation {
            Normalisation::Custom
        }
        fn respond(&self, luma: &[f32], _geom: PlaneGeometry, out: &mut [f32]) {
            out.copy_from_slice(luma);
        }
    }

    #[test]
    fn support_radius_is_the_stencil_plus_the_operators_own_window() {
        struct Op;
        impl FocusMeasure for Op {
            fn id(&self) -> &str {
                "op"
            }
            fn stencil_radius(&self) -> usize {
                1
            }
            fn window(&self) -> Window {
                Window::Box { radius: 13 }
            }
            fn normalisation(&self) -> Normalisation {
                Normalisation::LumaSigma { degree: 1 }
            }
            fn respond(&self, _l: &[f32], _g: PlaneGeometry, _o: &mut [f32]) {}
        }
        // Pinned against the crate's own analytic constant, so a change to
        // either side breaks loudly rather than shifting a tile margin.
        assert_eq!(Op.support_radius(), strehl_core::focus::SUPPORT_RADIUS);
        assert_eq!(Op.support_radius(), 14);
    }

    #[test]
    fn a_declared_custom_window_that_is_not_overridden_panics_rather_than_passing_through() {
        // Rule 20: the input that makes this fail is an implementation whose
        // default `aggregate` silently returned the response unchanged. That
        // would be a mis-scaled gate with nothing to say so, which is the
        // entire class of defect this crate exists to close.
        let g = geom(8, 8);
        let src = vec![1.0f32; g.pixels()];
        let mut scratch = vec![0.0f32; g.pixels()];
        let mut out = vec![0.0f32; g.pixels()];
        let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            DeclaresCustom.aggregate(&src, g, &mut scratch, &mut out);
        }));
        assert!(r.is_err(), "Window::Custom must not silently pass through");

        let noise = NoiseModel::new(
            [PlaneNoise {
                gain_dn_per_e: 0.229,
                read_noise_e: 1.47,
                levels: Levels {
                    black: 0.0,
                    white: 16383.0,
                },
            }; 4],
            100.0,
            Provenance::Measured,
        );
        let mut field = vec![1.0f32; g.pixels()];
        let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            DeclaresCustom.normalise(&mut field, &src, &noise);
        }));
        assert!(r.is_err(), "Normalisation::Custom must not silently no-op");
    }

    #[test]
    fn window_none_aggregates_to_the_response_itself() {
        let g = geom(5, 4);
        let src: Vec<f32> = (0..g.pixels()).map(|i| i as f32).collect();
        let mut scratch = vec![0.0f32; g.pixels()];
        let mut out = vec![0.0f32; g.pixels()];
        Identity.aggregate(&src, g, &mut scratch, &mut out);
        assert_eq!(out, src);
        assert_eq!(Identity.support_radius(), 0);
        assert!(Window::Box { radius: 8 }.is_separable());
        assert!(!Window::Custom { radius: 8 }.is_separable());
    }

    #[test]
    fn the_trait_is_object_safe_and_send_sync() {
        // The merge folds frames across a rayon pool, so a registry of
        // `Arc<dyn FocusMeasure>` has to cross threads. If this stops
        // compiling the registry design is dead.
        fn assert_send_sync<T: Send + Sync + ?Sized>() {}
        assert_send_sync::<dyn FocusMeasure>();
        let boxed: Box<dyn FocusMeasure> = Box::new(Identity);
        assert_eq!(boxed.id(), "identity");
    }

    #[test]
    fn replicate_clamping_reads_the_edge_and_never_leaves_the_buffer() {
        let v: Vec<f32> = (0..12).map(|i| i as f32).collect();
        assert_eq!(tap(&v, 4, 3, -5, -5), 0.0);
        assert_eq!(tap(&v, 4, 3, 99, 99), 11.0);
        assert_eq!(tap(&v, 4, 3, 1, 1), 5.0);
    }
}
