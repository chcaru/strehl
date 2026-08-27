//! The host field pipeline: operator, the operator own window, the
//! normaliser, then **the host regulariser**.
//!
//! ```text
//! respond()  ->  aggregate()  ->  normalise()  ->  regularise (radius 8)
//! ```
//!
//! **[`FieldConfig`] and [`FieldWorkspace`] now live in [`strehl_core::focus`]
//! and this module re-exports them.** They moved in BUILD-PLUGIN, together with
//! the trait, because the claim this module header used to make —
//! *"bit-identical to [`strehl_core::focus::FocusField::compute`] followed by
//! the merge regulariser"* — was a claim about two separate
//! implementations agreeing, held together by a test. It is now a claim about
//! one implementation: both sides call
//! [`strehl_core::focus::run_measure`], and
//! [`FocusField::compute_at_radius`](strehl_core::focus::FocusField::compute_at_radius)
//! passes it [`strehl_core::focus::Tenengrad`].
//!
//! **The claim was verified before it was made structural**, on real frames
//! rather than on this crate own synthetic planes:
//! `strehl-cli/examples/build-plugin-field.rs` ran both paths over three
//! decoded `wrapped-text-1` frames at 3516x2344 through
//! `profile::noise_model_for` at ISO 100 and found **0 differing samples of
//! 8,241,504** in both the bare and the regularised configuration, worst
//! absolute difference `0e0`. See `docs/research/BUILD-PLUGIN.md`.
//!
//! The tests below are kept, and they are no longer independent evidence — they
//! are a **structural** regression test that the two entry points still share
//! the pipeline. That is worth saying out loud: a test that once falsified a
//! duplication now only pins that the duplication has not come back.
//!
//! # Why the regulariser belongs to the host and not to the plugin
//!
//! Fact 500. `FOCUS_NOISE_SD` (0.015214) is measured **with** the 17x17
//! regulariser; `FINE_FOCUS_NOISE_SD` (0.090400) is measured **without** it.
//! They are not the same kind of quantity and must never be divided by one
//! another — this repository did exactly that and overstated a ratio by 3.27x.
//! A plugin cannot know the host regulariser radius, which is why a
//! plugin-declared noise constant is under-determined *in principle* and not
//! merely in practice.

pub use strehl_core::focus::{FieldConfig, FieldWorkspace};

#[cfg(test)]
use strehl_core::focus::FocusMeasure;
#[cfg(test)]
use strehl_core::merge::REGULARISER_RADIUS;
#[cfg(test)]
use strehl_core::plane::PlaneGeometry;
#[cfg(test)]
mod tests {
    use super::*;
    use crate::reference::{Ring, Tenengrad};
    use crate::rng::{NoiseSource, unit_sigma_model};
    use strehl_core::focus::{FINE_WINDOW_RADIUS, FocusField, SUPPORT_RADIUS, WINDOW_RADIUS};

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// **The check that the trait expresses the shipped operator without
    /// contortion**, and it is spelled as bit-identity rather than as
    /// "approximately agrees".
    ///
    /// Rule 20 — inputs that make this fail, all of them reachable:
    /// normalising before windowing instead of after; using `powi(1)` instead
    /// of a bare divide; a different `SIGMA_EPS`; a different border policy in
    /// the Sobel; the box radius off by one. Every one of those moves
    /// `FOCUS_NOISE_SD` and none of them would show up anywhere else.
    #[test]
    fn the_shipped_operator_reproduces_focus_field_bit_for_bit() {
        let g = geom(97, 71);
        let noise = unit_sigma_model();
        let mut plane = vec![0.0f32; g.pixels()];
        NoiseSource::SplitMixBoxMuller.fill(0xC0FFEE, &mut plane);
        // Put it on a realistic DN pedestal so the sigma divisor is exercised
        // rather than sitting at 1.0.
        for v in plane.iter_mut() {
            *v = 3000.0 + 400.0 * *v;
        }

        let mut want = FocusField::new(g);
        want.compute(&plane, &noise);

        let mut ws = FieldWorkspace::new(g);
        let got = ws.run(&Tenengrad::shipped(), FieldConfig::BARE, &plane, &noise);

        assert_eq!(
            got,
            want.values(),
            "the plugin pipeline must reproduce FocusField::compute exactly"
        );
        assert_eq!(ws.allocated_bytes(), want.allocated_bytes());
    }

    #[test]
    fn the_regularised_path_reproduces_focus_field_plus_merge_regularise() {
        let g = geom(101, 83);
        let noise = unit_sigma_model();
        let mut plane = vec![0.0f32; g.pixels()];
        NoiseSource::SplitMixBoxMuller.fill(7, &mut plane);
        for v in plane.iter_mut() {
            *v = 2200.0 + 300.0 * *v;
        }

        let mut field = FocusField::new(g);
        field.compute(&plane, &noise);
        let mut scratch = vec![0.0f32; g.pixels()];
        let mut want = vec![0.0f32; g.pixels()];
        strehl_core::merge::regularise(field.values(), g, &mut scratch, &mut want);

        let mut ws = FieldWorkspace::new(g);
        let got = ws.run(&Tenengrad::shipped(), FieldConfig::SHIPPED, &plane, &noise);
        assert_eq!(got, want.as_slice());
    }

    #[test]
    fn the_shipped_support_radius_and_plugin_halo_are_the_crates_own_numbers() {
        let op = Tenengrad::shipped();
        assert_eq!(op.support_radius(), SUPPORT_RADIUS);
        assert_eq!(op.window().radius(), WINDOW_RADIUS);
        assert_eq!(
            FieldConfig::SHIPPED.plugin_halo(&op),
            SUPPORT_RADIUS + REGULARISER_RADIUS
        );
        assert_eq!(FieldConfig::SHIPPED.plugin_halo(&op), 22);
    }

    /// The margin formula must reproduce, for a 3x3 stencil, exactly the two
    /// margins the crate's own measurements use — 23 coarse and 4 fine — and
    /// must widen for a wider stencil.
    #[test]
    fn the_calibration_margin_matches_both_in_crate_measurements() {
        let coarse = Tenengrad::shipped();
        assert_eq!(
            FieldConfig::SHIPPED.calibration_margin(&coarse),
            WINDOW_RADIUS + 2 + REGULARISER_RADIUS
        );
        assert_eq!(FieldConfig::SHIPPED.calibration_margin(&coarse), 23);

        let fine = Tenengrad::at_radius(FINE_WINDOW_RADIUS);
        assert_eq!(
            FieldConfig::BARE.calibration_margin(&fine),
            FINE_WINDOW_RADIUS + 2
        );
        assert_eq!(FieldConfig::BARE.calibration_margin(&fine), 4);

        // A wider stencil must widen the margin; M43's reference instrument
        // did not do this and under-margined `ring(1,3)` by 2 px.
        let ring = Ring::new(1, 3, WINDOW_RADIUS);
        assert_eq!(ring.stencil_radius(), 3);
        assert_eq!(
            FieldConfig::SHIPPED.calibration_margin(&ring),
            4 + WINDOW_RADIUS + REGULARISER_RADIUS
        );
    }

    #[test]
    fn a_bare_config_and_a_regularised_config_do_not_produce_the_same_field() {
        // Rule 20's sanity clause for the config itself: if these agreed, the
        // regulariser would not be in the path and the coarse calibration
        // target would be measuring the fine configuration.
        let g = geom(64, 64);
        let noise = unit_sigma_model();
        let mut plane = vec![0.0f32; g.pixels()];
        NoiseSource::SplitMixBoxMuller.fill(3, &mut plane);
        let mut ws = FieldWorkspace::new(g);
        let bare = ws
            .run(&Tenengrad::shipped(), FieldConfig::BARE, &plane, &noise)
            .to_vec();
        let reg = ws
            .run(&Tenengrad::shipped(), FieldConfig::SHIPPED, &plane, &noise)
            .to_vec();
        assert_ne!(bare, reg);
    }
}
