//! The `FocusMeasure` contract — and the one method it deliberately does not
//! have.
//!
//! **The trait itself now lives in [`strehl_core::focus`] and this module
//! re-exports it.** It moved there in BUILD-PLUGIN, and the move is the
//! architectural point rather than a tidy-up: a contribution surface the host
//! cannot reach is not a contribution surface. While the trait lived here,
//! `strehl-cli` — which did not depend on this crate at all (facts 583, 632,
//! 662) — could not accept a contributed operator without the pipeline being
//! written a second time, and it *was* written a second time. `strehl stack
//! --focus <id>` now dispatches through
//! [`strehl_core::focus::FocusField::compute_with_measure`], which is the same
//! [`run_measure`](strehl_core::focus::run_measure) the shipped operator goes
//! through.
//!
//! What stays here is everything the *host measuring* half needs: this module
//! is the contract, [`crate::calibrate`] is the instrument, and
//! [`crate::registry`] is the seam that refuses to hand out a gate without one.
//!
//! # What is missing from the trait, and why
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
//!    detectable, because there is no place in the trait to put a wrong number.
//! 2. **A declared constant is under-determined in principle.** The response SD
//!    depends on the operator, on the operator own window, *and* on the
//!    host regulariser radius — which the plugin cannot know. Fact 500 is
//!    this repository dividing two of its own constants that differed in
//!    exactly that and overstating a ratio by 3.27x.
//! 3. Changing [`REGULARISER_RADIUS`](strehl_core::merge::REGULARISER_RADIUS)
//!    would silently stale every declared constant in the ecosystem. A measured
//!    one re-derives.
//!
//! # The shape the trait has to fit
//!
//! Every operator in fact 439 survey decomposes into the same three stages,
//! and the trait is that decomposition:
//!
//! ```text
//! respond()    pointwise stencil, replicate-clamped   e.g. sqrt(Gx^2 + Gy^2)
//! aggregate()  the operator OWN window                e.g. a 27x27 box mean
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
//! divide. They exist because the survey seven operators are all separable
//! and pointwise, which is a fact about textbook focus measures rather than a
//! constraint anyone should inherit from them.

pub use strehl_core::focus::{FocusMeasure, Normalisation, SIGMA_EPS, Window, tap};

#[cfg(test)]
use strehl_core::noise::NoiseModel;
#[cfg(test)]
use strehl_core::plane::PlaneGeometry;
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
