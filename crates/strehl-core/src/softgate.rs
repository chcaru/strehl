//! A soft admission weight for the merge's second pass.
//!
//! # What is wrong with the boolean gate
//!
//! [`crate::merge::Gate`] admits a frame when the winner beats it by no more
//! than [`Gate::tolerance`](crate::merge::Gate::tolerance), and rejects it
//! otherwise. The comparison is sound; the **step** is not. Admission is an
//! all-or-nothing decision taken on a continuous quantity, so two adjacent
//! pixels whose response gaps straddle the tolerance receive completely
//! different frame sets, and the output jumps between them.
//!
//! That step is the merge's seam. M111 measured its two ends on
//! `dry-erase-marker-head-cpl`, 299 frames:
//!
//! | population | median gap to the runner-up | boolean weight |
//! | --- | --- | --- |
//! | seams in the flat, elected population | **0.467 x tolerance** | 1 (admitted) |
//! | genuinely textured regions | **2.187 x tolerance** | 0 (rejected) |
//!
//! The **4.7x separation** between those two is the whole argument for a soft
//! weight. Where the merge draws a seam the frames are very nearly tied, and
//! nothing about a 0.467-tolerance gap justifies choosing one and discarding
//! the other. Where there is real texture the winner leads by more than two
//! tolerances and deserves to win outright. A weight that decays smoothly over
//! the tolerance keeps the second behaviour while removing the first.
//!
//! # The weight
//!
//! ```text
//! w(focus, best) = exp(-0.5 * ((best - focus) / tolerance)^2)
//! ```
//!
//! [`SoftGate::tolerance`] is **bit-identical** to [`Gate::tolerance`], the same
//! `threshold * sqrt(2) * FOCUS_NOISE_SD`. This is deliberate and it is a
//! constraint, not a convenience: `FOCUS_NOISE_SD` is a calibrated quantity
//! (`crates/strehl-plugin/src/calibrate.rs`) and the soft gate must express its
//! admission in the same unit or that calibration no longer applies to it. M81
//! attempted a texture-qualified correction that changed the unit and scored
//! 0 of 5 stacks; keeping the unit is why this is a different proposal rather
//! than the same one again.
//!
//! # What the weight is, mathematically
//!
//! `best - focus` is a difference of two responses. Each carries noise of
//! standard deviation `FOCUS_NOISE_SD`, so the difference carries
//! `sqrt(2) * FOCUS_NOISE_SD`, and
//!
//! ```text
//! z = (best - focus) / (sqrt(2) * FOCUS_NOISE_SD)
//! ```
//!
//! is exactly the standardised gap -- the z-score for "this frame ties the
//! winner". Since `tolerance = threshold * sqrt(2) * FOCUS_NOISE_SD`,
//!
//! ```text
//! w = exp(-0.5 * (z / threshold)^2)
//! ```
//!
//! so the weight is the Gaussian likelihood of the observed gap under the null
//! that the frame ties the winner, with `threshold` acting as a **temperature**.
//! Normalised by [`SoftGate::posterior`] the weights sum to one and are a
//! posterior over frame-of-best-focus under a flat prior and that noise model.
//! `threshold -> 0` recovers the hard argmax (the MAP estimate);
//! `threshold -> inf` recovers the unweighted mean.
//!
//! **Both gates are kernels over the same z.** The boolean gate is a top-hat;
//! this is a Gaussian. That framing is the honest one and it says plainly what
//! is and is not being claimed: the soft gate does not use any information the
//! boolean gate lacks, and it will not resolve detail the boolean gate cannot.
//! It removes a discontinuity. See `docs/research/M111-waxy-blobs.md`.
//!
//! # Effective sample size
//!
//! With weights the count `n` is no longer the right noise bookkeeping, and
//! [`n_eff`] replaces it with Kish's effective sample size
//! `(sum w)^2 / sum w^2`. That choice is forced rather than free: it is the
//! **exact** generalisation, returning the integer count whenever the weights
//! are 0 or 1, so a soft-gated merge reduces bit-for-bit to the boolean one on
//! any pixel where the weights happen to be boolean. `the_kish_estimator_is_the_
//! exact_generalisation_of_the_boolean_count` pins that.
//!
//! # Status
//!
//! **Opt-in and not wired.** Nothing in this module is reachable from the
//! default merge path, and building it changes no output byte. The boolean gate
//! remains the default, so no `stack`/`merge` byte-freeze moves, `DEFAULT_GATE`
//! needs no re-solve, and fact 19's `0.534x` continues to describe the shipped
//! merge. `docs/research/M111-waxy-blobs.md` section 15 specifies the
//! integration point exactly, for routing into `merge.rs` when that lane frees.

use crate::merge::FOCUS_NOISE_SD;

/// Weights below this cannot move a 16-bit output sample and are set to zero.
///
/// The Gaussian has infinite support. On a 299-frame stack, summing 299
/// arbitrarily small weights costs time and adds a bias made entirely of frames
/// that are nowhere near focus, so the tail is truncated at the level where a
/// frame stops being able to change the result: one part in `2^16`.
pub const WEIGHT_FLOOR: f32 = 1.0 / 65536.0;

/// The gap, in tolerances, at which the weight reaches [`WEIGHT_FLOOR`].
///
/// `exp(-0.5 z^2) = 2^-16` gives `z = sqrt(32 ln 2) = 4.7096...`. Derived here
/// rather than written down so it cannot drift away from [`WEIGHT_FLOOR`].
pub fn cutoff_tolerances() -> f32 {
    (-2.0 * (WEIGHT_FLOOR as f64).ln()).sqrt() as f32
}

/// A Gaussian admission weight over the standardised response gap.
///
/// Constructed with the same `threshold` as [`crate::merge::Gate`] and yielding
/// the same [`tolerance`](Self::tolerance); the two differ only in the shape of
/// the kernel.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SoftGate {
    /// Admission scale, in standard deviations of the response difference.
    pub threshold: f32,
}

impl SoftGate {
    /// # Panics
    ///
    /// If `threshold` is negative or non-finite, matching
    /// [`Gate::new`](crate::merge::Gate::new) rather than silently inverting.
    pub fn new(threshold: f32) -> Self {
        assert!(
            threshold >= 0.0 && threshold.is_finite(),
            "soft gate threshold must be finite and non-negative, got {threshold}"
        );
        Self { threshold }
    }

    /// The admission scale in response units.
    ///
    /// Identical by construction to [`Gate::tolerance`](crate::merge::Gate::tolerance).
    #[inline]
    pub fn tolerance(&self) -> f32 {
        self.threshold * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
    }

    /// The weight a frame with response `focus` earns against a winner at `best`.
    ///
    /// Returns a value in `[0, 1]`, `1.0` at a tie. Argument order matches
    /// [`Gate::admits`](crate::merge::Gate::admits) so the integration is a
    /// one-line substitution and the two can be diffed against each other.
    ///
    /// * A non-finite `focus` earns `0.0`, matching `admits`, where every
    ///   comparison against NaN is false.
    /// * A frame at least as good as the winner earns `1.0`. The gap is clamped
    ///   at zero rather than squared, because the Gaussian is symmetric and
    ///   would otherwise **penalise** a frame for scoring above the winner.
    ///   The regularised field makes this unreachable from `merge.rs`, but a
    ///   weight function that is wrong off its documented domain is a trap for
    ///   whoever calls it next.
    /// * `threshold == 0` degenerates to the hard argmax: `1.0` on an exact
    ///   tie, `0.0` otherwise. This mirrors `Gate::new(0.0)`, which admits only
    ///   the winner, and avoids a division by zero.
    #[inline]
    pub fn weight(&self, focus: f32, best: f32) -> f32 {
        if !focus.is_finite() || !best.is_finite() {
            return 0.0;
        }
        let gap = best - focus;
        if gap <= 0.0 {
            return 1.0;
        }
        let tol = self.tolerance();
        if tol <= 0.0 {
            return 0.0;
        }
        let z = gap / tol;
        if z >= cutoff_tolerances() {
            return 0.0;
        }
        let w = (-0.5 * z * z).exp();
        if w < WEIGHT_FLOOR { 0.0 } else { w }
    }

    /// Normalised weights over a frame's worth of responses: a posterior over
    /// frame-of-best-focus under a flat prior.
    ///
    /// Sums to `1.0` whenever any response is finite, and to `0.0` when none is
    /// -- an all-NaN pixel has no posterior and is reported as such rather than
    /// as a uniform one.
    pub fn posterior(&self, responses: &[f32]) -> Vec<f32> {
        let best = responses
            .iter()
            .copied()
            .filter(|r| r.is_finite())
            .fold(f32::NEG_INFINITY, f32::max);
        if !best.is_finite() {
            return vec![0.0; responses.len()];
        }
        let mut w: Vec<f32> = responses.iter().map(|r| self.weight(*r, best)).collect();
        let total: f32 = w.iter().sum();
        if total > 0.0 {
            for v in &mut w {
                *v /= total;
            }
        }
        w
    }
}

/// Kish's effective sample size, `(sum w)^2 / sum w^2`.
///
/// Returns `0.0` for an empty or all-zero weight set. This is the quantity that
/// replaces the boolean gate's integer `n` in the noise bookkeeping, and it is
/// the *exact* generalisation of it -- see the module docs.
pub fn n_eff(weights: &[f32]) -> f32 {
    let mut s = 0.0f64;
    let mut s2 = 0.0f64;
    for w in weights {
        let w = f64::from(*w);
        s += w;
        s2 += w * w;
    }
    if s2 <= 0.0 { 0.0 } else { (s * s / s2) as f32 }
}

/// Shannon entropy of a weight set, in nats, after normalising.
///
/// Reported because it is the natural read-out of the posterior interpretation:
/// `0` when one frame carries everything, `ln(n)` when `n` frames are tied. A
/// merge that wants to know whether a pixel is genuinely resolved or merely
/// undecided can ask this instead of thresholding `n_eff`.
pub fn entropy(weights: &[f32]) -> f32 {
    let total: f64 = weights.iter().map(|w| f64::from(*w)).sum();
    if total <= 0.0 {
        return 0.0;
    }
    let mut h = 0.0f64;
    for w in weights {
        let p = f64::from(*w) / total;
        if p > 0.0 {
            h -= p * p.ln();
        }
    }
    h as f32
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::merge::{DEFAULT_GATE, Gate};

    /// M111's measured median gap to the runner-up, in tolerances, at seams in
    /// the flat elected population and in genuinely textured regions.
    const SEAM_GAP_TOL: f32 = 0.467;
    const TEXTURE_GAP_TOL: f32 = 2.187;

    fn approx(a: f32, b: f32, eps: f32, what: &str) {
        assert!((a - b).abs() <= eps, "{what}: {a} vs {b} (eps {eps})");
    }

    // ---- the unit is preserved (constraint: FOCUS_NOISE_SD's calibration) ----

    #[test]
    fn the_tolerance_is_bit_identical_to_the_boolean_gates() {
        for t in [0.0f32, 0.25, 0.5, 1.0, 2.0, DEFAULT_GATE, 16.0, 64.0, 1e5] {
            assert_eq!(
                SoftGate::new(t).tolerance(),
                Gate::new(t).tolerance(),
                "tolerance diverged at threshold {t}; FOCUS_NOISE_SD's calibration \
                 no longer transfers to the soft gate"
            );
        }
    }

    #[test]
    fn the_shipped_tolerance_is_the_value_m111_measured_against() {
        approx(
            SoftGate::new(DEFAULT_GATE).tolerance(),
            0.086_063,
            1e-6,
            "gate 4 tolerance",
        );
    }

    // ---- the premise: 4.7x separation becomes 9.8x in weight ----

    /// The entire argument for the soft gate, as a test rather than a sentence.
    ///
    /// A seam is a near-tie and must stay nearly tied in weight; a textured
    /// winner leads by more than two tolerances and must keep its lead. If this
    /// separation ever collapses, the fix no longer does what it was built for.
    #[test]
    fn the_measured_seam_and_texture_gaps_separate_by_almost_ten_times_in_weight() {
        let g = SoftGate::new(DEFAULT_GATE);
        let tol = g.tolerance();
        let w_seam = g.weight(1.0 - SEAM_GAP_TOL * tol, 1.0);
        let w_texture = g.weight(1.0 - TEXTURE_GAP_TOL * tol, 1.0);

        approx(w_seam, 0.896_688, 1e-4, "weight at a seam gap");
        approx(w_texture, 0.091_477, 1e-4, "weight at a texture gap");

        let separation = w_seam / w_texture;
        approx(separation, 9.802, 2e-2, "seam/texture weight separation");
        assert!(
            separation > 9.0,
            "the 4.7x separation in tolerance units must remain a large \
             separation in weight, got {separation}x"
        );
        // A seam neighbour keeps most of its say; a texture runner-up loses most.
        assert!(w_seam > 0.85, "seam neighbour nearly silenced: {w_seam}");
        assert!(w_texture < 0.10, "texture runner-up too loud: {w_texture}");
    }

    /// The defect, isolated: the boolean gate's response to an arbitrarily small
    /// change in the gap is a full unit of weight. That step is the seam.
    #[test]
    fn the_boolean_gate_steps_by_one_across_the_tolerance_and_the_soft_gate_does_not() {
        let hard = Gate::new(DEFAULT_GATE);
        let soft = SoftGate::new(DEFAULT_GATE);
        let tol = soft.tolerance();
        let (inside, outside) = (1.0 - 0.99 * tol, 1.0 - 1.01 * tol);

        assert!(hard.admits(inside, 1.0));
        assert!(!hard.admits(outside, 1.0));
        let hard_step = 1.0f32; // admitted -> rejected

        let soft_step = soft.weight(inside, 1.0) - soft.weight(outside, 1.0);
        approx(soft_step, 0.012_13, 1e-3, "soft step across the tolerance");
        assert!(
            hard_step / soft_step > 50.0,
            "the soft gate must be at least an order of magnitude smoother \
             across the admission boundary; got {}x",
            hard_step / soft_step
        );
    }

    // ---- Kish n_eff is the exact generalisation, not an approximation ----

    #[test]
    fn the_kish_estimator_is_the_exact_generalisation_of_the_boolean_count() {
        for n in [1usize, 2, 5, 13, 299] {
            let boolean = vec![1.0f32; n];
            approx(n_eff(&boolean), n as f32, 1e-3, "all-admitted n_eff");
        }
        // Mixed 0/1, as the boolean gate actually produces.
        let mixed = [1.0f32, 0.0, 1.0, 1.0, 0.0, 1.0];
        approx(n_eff(&mixed), 4.0, 1e-4, "mixed boolean n_eff");
        assert_eq!(n_eff(&[]), 0.0);
        assert_eq!(n_eff(&[0.0, 0.0]), 0.0);
    }

    #[test]
    fn a_single_dominant_frame_gives_n_eff_near_one_however_long_the_tail() {
        let mut w = vec![1.0f32];
        w.extend(std::iter::repeat_n(1e-4f32, 298));
        assert!(n_eff(&w) < 1.2, "n_eff {} should be near 1", n_eff(&w));
    }

    /// Kish is not the sum, and every test above this one is satisfied by
    /// `sum(w)` as well -- found by asking what a mutation would survive rather
    /// than by running one. Fractional weights are where the two separate, and
    /// they are the only weights the soft gate actually produces.
    #[test]
    fn n_eff_is_kish_and_not_the_plain_sum_of_the_weights() {
        // sum = 2.0, Kish = 4 / 1.5 = 2.6667.
        approx(n_eff(&[1.0, 0.5, 0.5]), 8.0 / 3.0, 1e-4, "three-frame Kish");
        // sum = 1.25, Kish = 1.5625 / 1.0625 = 1.4706.
        approx(n_eff(&[1.0, 0.25]), 1.470_588, 1e-4, "two-frame Kish");
        // Kish exceeds the sum whenever the weights are unequal and sub-unit,
        // which is the whole reason it is the right noise bookkeeping.
        for w in [
            vec![1.0f32, 0.5, 0.5],
            vec![0.9f32, 0.8, 0.7, 0.6],
            vec![1.0f32, 0.25],
        ] {
            let s: f32 = w.iter().sum();
            assert!(
                (n_eff(&w) - s).abs() > 1e-3,
                "n_eff coincided with the plain sum on {w:?}; this test cannot \
                 tell Kish from a sum and neither can the rest of the suite"
            );
        }
    }

    // ---- the n_eff prediction the fix makes, before any image is rendered ----

    /// The falsifiable consequence: a soft weight must raise `n_eff` where the
    /// merge draws seams, and leave it near 1 where there is real texture.
    #[test]
    fn the_soft_gate_raises_n_eff_at_seams_and_not_in_texture() {
        let hard = Gate::new(DEFAULT_GATE);
        let soft = SoftGate::new(DEFAULT_GATE);
        let tol = soft.tolerance();

        // A seam: a handful of frames clustered inside half a tolerance, which
        // is what M111 measured there (median gap 0.467 x tolerance).
        let seam: Vec<f32> = (0..8).map(|k| 1.0 - (k as f32) * 0.06 * tol).collect();
        // Texture: one clear winner, the rest beyond two tolerances.
        let texture: Vec<f32> = (0..8)
            .map(|k| if k == 0 { 1.0 } else { 1.0 - (2.0 + k as f32) * tol })
            .collect();

        let count = |rs: &[f32], best: f32| {
            rs.iter().filter(|r| hard.admits(**r, best)).count() as f32
        };
        let soft_n = |rs: &[f32], best: f32| {
            n_eff(&rs.iter().map(|r| soft.weight(*r, best)).collect::<Vec<_>>())
        };

        let (seam_hard, seam_soft) = (count(&seam, 1.0), soft_n(&seam, 1.0));
        let (tex_hard, tex_soft) = (count(&texture, 1.0), soft_n(&texture, 1.0));

        assert_eq!(seam_hard, 8.0, "all eight seam frames are inside tolerance");
        assert_eq!(tex_hard, 1.0, "only the winner survives in texture");

        // In texture the soft gate must not start averaging: the runner-up at
        // 3 tolerances earns exp(-4.5) = 1.1%, so n_eff stays essentially 1.
        assert!(
            tex_soft < 1.05,
            "soft gate began averaging in texture: n_eff {tex_soft}"
        );
        // At a seam it must, and by much more than it does in texture.
        assert!(
            seam_soft > 7.0,
            "soft gate failed to average a near-tied seam: n_eff {seam_soft}"
        );
        assert!(
            seam_soft / tex_soft > 6.0,
            "the seam/texture n_eff separation is the prediction; got {}x",
            seam_soft / tex_soft
        );
    }

    // ---- shape, domain and degenerate cases ----

    #[test]
    fn the_kernel_agrees_with_the_python_that_computed_the_field_prediction() {
        // M111's n_eff prediction (report S15) was evaluated in Python, from
        // the gap CDF read off a fourteen-rung gate ladder, while the fix
        // ships here in Rust. Nothing structural keeps the two in step, so
        // the kernel is pinned at exactly the ladder edges the prediction
        // integrated over. If this test ever fails, the published interval
        // (seam 1.59-2.14, texture 1.07-1.29) is stale and must be re-run --
        // it does not silently become approximate.
        let soft = SoftGate::new(DEFAULT_GATE);
        let tol = soft.tolerance();
        let rungs: [(f32, f32); 15] = [
            (0.0625, 0.998_048_78),
            (0.25, 0.969_233_23),
            (0.5, 0.882_496_90),
            (0.75, 0.754_839_60),
            (1.0, 0.606_530_66),
            (1.25, 0.457_833_36),
            (1.5, 0.324_652_47),
            (2.0, 0.135_335_28),
            (2.5, 0.043_936_93),
            (3.0, 0.011_108_997),
            (3.5, 0.002_187_491),
            (4.0, 0.000_335_463),
            // 4.7096 is just BELOW the cutoff sqrt(32 ln 2) = 4.709_626, so it
            // is still tapered, not truncated. Rust reads 0.000_015_261_641
            // and Python 0.000_015_262 -- seven significant figures of
            // agreement between two independent implementations.
            (4.7096, 0.000_015_262),
            (4.71, 0.0), // just above the cutoff: truncated, not tapered
            (16.0, 0.0),
        ];
        for (z, want) in rungs {
            let got = soft.weight(1.0 - z * tol, 1.0);
            approx(got, want, 2e-6, &format!("kernel at z = {z} tolerances"));
        }
    }

    #[test]
    fn the_weight_is_one_at_a_tie_and_monotone_decreasing_in_the_gap() {
        let g = SoftGate::new(DEFAULT_GATE);
        approx(g.weight(1.0, 1.0), 1.0, 1e-7, "weight at a tie");
        let tol = g.tolerance();
        let mut prev = f32::INFINITY;
        for k in 0..50 {
            let w = g.weight(1.0 - 0.1 * k as f32 * tol, 1.0);
            assert!(w <= prev, "weight rose at step {k}: {w} > {prev}");
            assert!((0.0..=1.0).contains(&w), "weight out of range at {k}: {w}");
            prev = w;
        }
        assert_eq!(prev, 0.0, "the tail must reach exactly zero");
    }

    #[test]
    fn a_frame_scoring_above_the_winner_is_not_penalised() {
        let g = SoftGate::new(DEFAULT_GATE);
        approx(g.weight(1.5, 1.0), 1.0, 1e-7, "above-winner weight");
    }

    #[test]
    fn a_non_finite_response_earns_no_weight() {
        let g = SoftGate::new(DEFAULT_GATE);
        assert_eq!(g.weight(f32::NAN, 1.0), 0.0);
        assert_eq!(g.weight(f32::NEG_INFINITY, 1.0), 0.0);
        assert_eq!(g.weight(1.0, f32::NAN), 0.0);
    }

    #[test]
    fn a_zero_threshold_is_the_hard_argmax() {
        let g = SoftGate::new(0.0);
        assert_eq!(g.weight(1.0, 1.0), 1.0);
        assert_eq!(g.weight(1.0 - 1e-6, 1.0), 0.0);
    }

    #[test]
    #[should_panic(expected = "non-negative")]
    fn a_negative_threshold_is_rejected() {
        SoftGate::new(-1.0);
    }

    #[test]
    fn the_tail_is_truncated_where_a_frame_can_no_longer_move_a_u16() {
        let g = SoftGate::new(DEFAULT_GATE);
        let tol = g.tolerance();
        let z = cutoff_tolerances();
        approx(z, 4.7096, 1e-3, "cutoff in tolerances");
        assert!(g.weight(1.0 - 0.99 * z * tol, 1.0) > 0.0);
        assert_eq!(g.weight(1.0 - 1.01 * z * tol, 1.0), 0.0);
    }

    // ---- the posterior reading ----

    #[test]
    fn the_posterior_sums_to_one_and_degenerates_correctly() {
        let g = SoftGate::new(DEFAULT_GATE);
        let tol = g.tolerance();
        let rs: Vec<f32> = (0..12).map(|k| 1.0 - (k as f32) * 0.3 * tol).collect();
        let p = g.posterior(&rs);
        approx(p.iter().sum::<f32>(), 1.0, 1e-5, "posterior mass");
        assert!(p[0] >= p[1] && p[1] >= p[2], "posterior must be ordered");

        // No finite response: no posterior, rather than a uniform one.
        let none = g.posterior(&[f32::NAN, f32::NAN]);
        approx(none.iter().sum::<f32>(), 0.0, 1e-7, "all-NaN posterior mass");
    }

    #[test]
    fn entropy_reads_zero_when_one_frame_wins_and_ln_n_when_all_tie() {
        approx(entropy(&[1.0, 0.0, 0.0, 0.0]), 0.0, 1e-6, "decided entropy");
        approx(
            entropy(&[1.0, 1.0, 1.0, 1.0]),
            4.0f32.ln(),
            1e-6,
            "tied entropy",
        );
        assert_eq!(entropy(&[]), 0.0);
    }

    /// The posterior is a *tempered* one: `threshold` is a temperature, so the
    /// same responses are read as more or less decided depending on the gate.
    /// Anyone reading `posterior` as a calibrated probability needs this.
    #[test]
    fn the_threshold_acts_as_a_temperature_on_the_posterior() {
        let tol4 = SoftGate::new(DEFAULT_GATE).tolerance();
        let rs: Vec<f32> = (0..8).map(|k| 1.0 - (k as f32) * 0.5 * tol4).collect();
        let mut prev = f32::NEG_INFINITY;
        for t in [0.5f32, 1.0, 2.0, DEFAULT_GATE, 16.0] {
            let h = entropy(&SoftGate::new(t).posterior(&rs));
            assert!(h >= prev, "entropy fell as the gate opened: {h} < {prev}");
            prev = h;
        }
        assert!(
            prev < 8.0f32.ln() + 1e-6,
            "entropy exceeded the uniform bound"
        );
    }
}
