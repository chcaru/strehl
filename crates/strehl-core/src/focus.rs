//! Noise-normalised ring-difference focus measure.
//!
//! ```text
//! inner = mean of L over 3x3
//! outer = mean of L over 7x7
//! focus = |inner - outer| / max(sigma_L, EPS)
//! ```
//!
//! The difference of two box means is a bandpass: it keeps what the 3x3 sees
//! and the 7x7 does not. Ring difference, not Laplacian — the Laplacian's
//! winner-margin goes *negative* at sigma >= 0.01, meaning it actively prefers
//! the wrong frame, while ring difference stays highest at every noise level
//! (SYNTHESIS §4 fact #6, MEASURED).
//!
//! # The normalisation is a proxy, and this is where that is admitted
//!
//! `sigma_L` is the noise standard deviation of a **single** luma sample at that
//! signal level, from the injected noise model. It is **not** the standard
//! deviation of `(inner - outer)`. The true value is smaller and
//! signal-correlated: both terms are means over many samples, the two windows
//! overlap so their errors are correlated, and the correct expression involves
//! the window sizes and the overlap count.
//!
//! The skeleton only consumes the *ranking* of `focus` across frames at a fixed
//! pixel. Every frame at that pixel divides by a sigma computed from nearly the
//! same signal level, so the omitted factor is very nearly common to all frames
//! and very nearly cancels out of the comparison. That makes the proxy adequate
//! **here** and nowhere else. The focus-measure bake-off (SYNTHESIS §8
//! experiment 3) scores measures by winner-margin versus sigma and must derive
//! the variance of the difference properly.

use crate::boxfilter::box_mean;
use crate::noise::NoiseModel;
use crate::plane::PlaneGeometry;

/// Inner box radius: a 3x3 mean.
pub const INNER_RADIUS: usize = 1;
/// Outer box radius: a 7x7 mean.
pub const OUTER_RADIUS: usize = 3;

/// Divisor floor, in DN. Guards the case where the noise model returns zero or
/// something denormal; it is far below any real sensor's read-noise floor.
const SIGMA_EPS: f32 = 1e-3;

/// Reusable buffers plus the computed focus field for one plane.
///
/// Allocated once per worker and reused for every frame that worker folds. At
/// 8.2 MP this is 99 MB, so allocating per frame would dominate the run.
pub struct FocusField {
    geom: PlaneGeometry,
    /// Holds the 3x3 mean, then is overwritten in place with the focus value.
    /// The combine is elementwise and reads each element once, so no third
    /// full-plane buffer is needed.
    focus: Vec<f32>,
    outer: Vec<f32>,
    scratch: Vec<f32>,
}

impl FocusField {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            focus: vec![0.0; geom.pixels()],
            outer: vec![0.0; geom.pixels()],
            scratch: vec![0.0; geom.pixels()],
        }
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }

    /// Bytes of scratch this holds, for the memory budget report.
    pub fn allocated_bytes(&self) -> usize {
        3 * self.geom.pixels() * std::mem::size_of::<f32>()
    }

    /// Compute the focus field for one frame's black-subtracted green luma.
    pub fn compute(&mut self, luma: &[f32], noise: &NoiseModel) {
        assert_eq!(luma.len(), self.geom.pixels());
        box_mean(
            luma,
            self.geom,
            INNER_RADIUS,
            &mut self.scratch,
            &mut self.focus,
        );
        box_mean(
            luma,
            self.geom,
            OUTER_RADIUS,
            &mut self.scratch,
            &mut self.outer,
        );
        for ((focus, outer), l) in self.focus.iter_mut().zip(&self.outer).zip(luma) {
            let ring = (*focus - *outer).abs();
            let sigma = noise.green_luma_sigma(*l).max(SIGMA_EPS);
            *focus = ring / sigma;
        }
    }

    pub fn values(&self) -> &[f32] {
        &self.focus
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

    fn field(w: usize, h: usize, luma: &[f32]) -> Vec<f32> {
        let geom = PlaneGeometry {
            width: w,
            height: h,
        };
        let mut f = FocusField::new(geom);
        f.compute(luma, &model());
        f.values().to_vec()
    }

    #[test]
    fn a_flat_plane_has_zero_focus_everywhere_including_the_border() {
        // The border policy is load-bearing: a zero-padded box would leave a
        // bright rim here and the argmax would chase it.
        let luma = vec![4000.0f32; 21 * 15];
        let got = field(21, 15, &luma);
        assert!(got.iter().all(|v| *v < 1e-3), "max was {:?}", got);
    }

    #[test]
    fn a_sharper_edge_scores_higher_than_a_blurred_one_at_equal_signal() {
        let (w, h) = (21usize, 21usize);
        let mut sharp = vec![2000.0f32; w * h];
        let mut soft = vec![2000.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                // Step at x = 10, and the same step spread over 5 columns.
                sharp[y * w + x] = if x >= 10 { 3000.0 } else { 2000.0 };
                let t = ((x as f32 - 8.0) / 4.0).clamp(0.0, 1.0);
                soft[y * w + x] = 2000.0 + 1000.0 * t;
            }
        }
        let a = field(w, h, &sharp);
        let b = field(w, h, &soft);
        let peak = |v: &[f32]| v.iter().cloned().fold(f32::MIN, f32::max);
        assert!(
            peak(&a) > peak(&b),
            "sharp {} vs soft {}",
            peak(&a),
            peak(&b)
        );
    }

    #[test]
    fn normalisation_penalises_the_same_contrast_at_a_higher_signal_level() {
        // Shot noise grows with signal, so an equal-DN ring is less evidence of
        // detail on a bright background than on a dark one. That is the whole
        // point of dividing by sigma.
        let (w, h) = (15usize, 15usize);
        let build = |base: f32| {
            let mut v = vec![base; w * h];
            for y in 0..h {
                v[y * w + 7] = base + 100.0;
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
        let luma = vec![0.0f32; 9 * 9];
        let got = field(9, 9, &luma);
        assert!(got.iter().all(|v| v.is_finite() && *v >= 0.0));
    }

    /// How much of this measure's response at a pixel comes from that pixel's
    /// own value, by finite difference on the shipped code path.
    ///
    /// Shift invariance away from the border makes `d focus(q) / d luma(p)` a
    /// function of `q - p` alone, so perturbing one pixel yields the whole
    /// sensitivity kernel and `phi = |dr(0)| / sum |dr(d)|` falls straight out.
    fn centre_tap_fraction(delta: f32, amplitude: f32) -> (f64, usize) {
        let (w, h) = (65usize, 65usize);
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
        let base = field(w, h, &luma);
        let mut bumped = luma.clone();
        let centre = (h / 2) * w + w / 2;
        bumped[centre] += delta;
        let bump = field(w, h, &bumped);

        let reach = OUTER_RADIUS + 2;
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
    fn centre_tap_fraction_is_the_value_m9_measured() {
        // M9 (docs/research/M9-support-coupling-measured.md) established that
        // the naive-argmax noise excess a merge has to regularise away is
        // driven by this number and NOT by the measure's spatial support:
        // Spearman rho = +0.92 against the centre-tap fraction, -0.21 against
        // the support radius, on two stacks. It measured phi = 0.0550 for this
        // operator on real A7C II frames.
        //
        // A ring difference `|mean(2i+1) - mean(2o+1)| / sigma` has, ignoring
        // the sigma term, centre coefficient `1/a - 1/b` and total absolute
        // coefficient `2(1 - a/b)` for `a = (2i+1)^2`, `b = (2o+1)^2`, so
        //
        //     phi = 1 / (2a) = 1 / (2 * (2*INNER_RADIUS + 1)^2) = 1/18
        //
        // which depends on INNER_RADIUS alone. The tap count pins OUTER_RADIUS,
        // so the two assertions together pin both constants.
        //
        // A regression here means the shipped measure's noise-election
        // behaviour has changed, which invalidates M9's headline and the ruling
        // that took `support_px()` off the plugin interface.
        let analytic = 1.0 / (2.0 * ((2 * INNER_RADIUS + 1) as f64).powi(2));
        assert!((analytic - 1.0 / 18.0).abs() < 1e-12);

        // Low contrast: the sigma normalisation moves with the centre pixel
        // too, and its contribution scales with |response|, so the operator's
        // own coefficient is only recovered cleanly near zero response.
        let (phi_lo, taps) = centre_tap_fraction(1.0, 4.0);
        assert_eq!(
            taps, 49,
            "read extent must be the 7x7 outer box, got {taps} taps"
        );
        assert!(
            (phi_lo - analytic).abs() < 0.0015,
            "low-contrast centre-tap fraction was {phi_lo:.5}, analytic is {analytic:.5}"
        );

        // A realistic operating point, pinned tightly. This is the number that
        // would move if either radius or the normalisation changed.
        let (phi, _) = centre_tap_fraction(8.0, 120.0);
        assert!(
            (phi - 0.0507).abs() < 0.0015,
            "centre-tap fraction was {phi:.5}; M9 measured 0.0550 on real frames, \
             this synthetic operating point gives 0.0507, analytic is {analytic:.5}"
        );

        // Discrimination: the neighbouring inner radii are 1/2 and 1/50, both
        // an order of magnitude away, so this band cannot be satisfied by a
        // different operator that merely happens to read a 7x7 box.
        let (lo, hi) = (1.0 / 50.0, 1.0 / 2.0);
        assert!(
            phi_lo > 2.0 * lo && phi_lo < hi / 4.0,
            "phi {phi_lo:.5} must sit clear of INNER_RADIUS 2 ({lo:.5}) and 0 ({hi:.5})"
        );
    }
}
