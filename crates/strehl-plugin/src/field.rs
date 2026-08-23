//! The host's field pipeline: operator, the operator's own window, the
//! normaliser, then **the host's regulariser**.
//!
//! ```text
//! respond()  ->  aggregate()  ->  normalise()  ->  regularise (radius 8)
//! ```
//!
//! That order is not a preference. It is the order
//! [`strehl_core::focus::FocusField::compute`] and
//! [`strehl_core::merge::regularise`] execute in, and
//! [`tests::the_shipped_operator_reproduces_focus_field_bit_for_bit`] pins it
//! against the shipped code path rather than against a description of it.
//! Swapping `aggregate` and `normalise` moves the constant this crate exists to
//! measure, and nothing else in the system would notice.
//!
//! # Why the regulariser belongs to the host and not to the plugin
//!
//! Fact 500. `FOCUS_NOISE_SD` (0.015214) is measured **with** the 17x17
//! regulariser; `FINE_FOCUS_NOISE_SD` (0.090400) is measured **without** it.
//! They are not the same kind of quantity and must never be divided by one
//! another — this repository did exactly that and overstated a ratio by 3.27x.
//! A plugin cannot know the host's regulariser radius, which is why a
//! plugin-declared noise constant is under-determined *in principle* and not
//! merely in practice.

use strehl_core::boxfilter::box_mean;
use strehl_core::merge::REGULARISER_RADIUS;
use strehl_core::noise::NoiseModel;
use strehl_core::plane::PlaneGeometry;

use crate::measure::FocusMeasure;

/// The half of the field configuration that belongs to the host.
///
/// `Copy`, and carried inside every
/// [`Registered`](crate::registry::Registered) entry, so a calibrated operator
/// cannot be run under a configuration it was not calibrated for.
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
    /// What [`strehl_core::merge`] does: a 17x17 box over the focus field
    /// before a winner is elected.
    pub const SHIPPED: FieldConfig = FieldConfig {
        regulariser_radius: Some(REGULARISER_RADIUS),
    };

    /// No regulariser. What `through_focus.rs`'s fine field does, and the
    /// second of the two calibration targets in [`crate::calibrate::self_check`].
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

    /// Margin discarded from every edge before the calibration SD is taken.
    ///
    /// `max(stencil_radius + 1, 2) + window_radius + regulariser_radius`.
    ///
    /// The box filter is **replicate-clamped**, so pixels within one combined
    /// support of the edge see a smaller, differently-weighted window and are
    /// not stationary. Including them biases the SD, and the bias moves with
    /// the plane size, which is exactly the drift `merge.rs`'s own measurement
    /// documents at 192x192.
    ///
    /// For a 3x3 stencil this is `window_radius + 2 + regulariser_radius` —
    /// 23 for the shipped configuration, 4 for the fine one — which is the
    /// margin both in-crate measurements and M43's reference instrument use.
    /// The `stencil_radius + 1` term generalises it: M43's instrument used
    /// `radius + 2` for **every** operator including Brenner (stencil 2) and
    /// `ring(1,3)` (stencil 3), which under-margins those two by 1-2 px. The
    /// generalisation is the reason the `k` values this crate reports for those
    /// two operators are not expected to match fact 439 to the last digit.
    #[must_use]
    pub fn calibration_margin(self, op: &dyn FocusMeasure) -> usize {
        let stencil = (op.stencil_radius() + 1).max(2);
        stencil + op.window().radius() + self.regulariser_radius()
    }
}

/// Reusable buffers for one plane, so a field can be computed per frame without
/// allocating.
///
/// **Three f32 planes**, the same footprint as
/// [`strehl_core::focus::FocusField`]. That is deliberate: M8's measured memory
/// ratchet prices the per-worker term, and a fourth plane here would move it by
/// 33% for nothing.
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
        assert_eq!(
            luma.len(),
            self.geom.pixels(),
            "luma plane is {} samples, workspace geometry is {}",
            luma.len(),
            self.geom.pixels()
        );
        op.respond(luma, self.geom, &mut self.response);
        op.aggregate(
            &self.response,
            self.geom,
            &mut self.scratch,
            &mut self.windowed,
        );
        op.normalise(&mut self.windowed, luma, noise);
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

    /// Multiply the field in place — the one operation the *pre-normalised*
    /// path in [`crate::registry::Registered::field`] needs beyond
    /// [`run`](Self::run).
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
