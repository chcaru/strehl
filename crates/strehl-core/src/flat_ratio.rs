//! ACCEPTANCE INVARIANT 1's noise statistic: a box high-pass residual sd,
//! referenced to the distribution over **every** frame.
//!
//! # What this replaces, and why
//!
//! Invariant 1 used to be `stacked_sigma / single_sigma`, a ratio of two **raw
//! spatial** sds taken over a "flat" ROI, with the denominator supplied by one
//! arbitrarily chosen frame (`frames.len() / 2`). It had two independent
//! defects and a fix for either one alone is not a fix.
//!
//! 1. **It is structure-dominated.** Fact 469: on `109MSDCF`'s flat ROI the raw
//!    spatial sd is 76.272 DN against a modelled per-sample sigma of 8.77 DN,
//!    so ~99 % of the variance is residual scene, and the raw ratio
//!    under-reported a real noise explosion by **6.3x** (22.767x raw against
//!    144.391x high-pass). Fact 455: that ROI is not even detail-free —
//!    per-frame corrected detail spans 5.31-18.66 DN. Fact 442: the reference
//!    frames of the four flat ROIs are 53.3 %, 50.9 %, 90.0 % and 86.1 % scene
//!    structure by variance.
//! 2. **The denominator was one privileged frame.** Fact 441: holding the merge
//!    fixed and sweeping which frame occupies the denominator moves the printed
//!    ratio 1.0245x-1.3252x on `109MSDCF` and **1.0000x-1.5989x** on
//!    `119MSDCF`. A single published number that moves 1.60x over an unstated
//!    choice is not a measurement.
//!
//! Defect 1 is answered by [`highpass_sd`], defect 2 by [`FlatReference`],
//! which keeps the whole per-frame distribution and refuses to name one
//! denominator.
//!
//! # The kernel, and its reconciliation with fact 469
//!
//! The operator is `x - box_w(x)` at `w = `[`HP_BOX_SIDE`]` = 9`, which is
//! exactly the kernel that produced fact 469 — M41's
//! `hp_sd(a, w=9) = (a - scipy.ndimage.uniform_filter(a, 9)).std()`. Two
//! conventions differ and the difference was measured rather than assumed
//! (`experiments/m53-flat-ratio/out/a1_reconcile.log`, on `109MSDCF` frame 11,
//! plane ROI 1356,32,512,512 — the exact input behind fact 469's denominator):
//!
//! | statistic | M41 (reflect border, sd over the whole ROI) | here (valid interior) |
//! | --- | --- | --- |
//! | raw spatial sd | 76.2716 DN (M41 log: 76.272) | same |
//! | high-pass sd | 11.7696 DN (M41 log: **11.770**, 0.0038 % apart) | 11.1181 DN |
//!
//! so the two conventions sit **0.9447x** apart on real structured data, and
//! the same white-noise gain falls out of both (0.9944 measured against
//! 0.993808 derived). The valid interior is shipped because it is the one with
//! an exact closed-form gain: reflecting the border duplicates samples and
//! manufactures an edge one radius in, which inflates the residual on precisely
//! the ROIs this statistic is supposed to read as quiet.
//!
//! # The derived noise gain
//!
//! For white noise of per-sample sd `sigma`, with `N = w * w` samples in the
//! box, the residual at an interior pixel is
//!
//! ```text
//! r_i = x_i - (1/N) * sum_{j in W} x_j
//!     = (1 - 1/N) x_i - (1/N) sum_{j in W, j != i} x_j
//! ```
//!
//! whose terms are independent, so
//!
//! ```text
//! Var(r_i) = (1 - 1/N)^2 sigma^2 + (N - 1)/N^2 sigma^2
//!          = sigma^2 (N - 1) [ (N - 1) + 1 ] / N^2
//!          = sigma^2 (1 - 1/N)
//! ```
//!
//! and therefore `sd(r) = sigma * sqrt(1 - 1/w^2)` — [`HP_NOISE_GAIN`], which is
//! `0.993808` at `w = 9`. That is the whole reason the border ring is dropped:
//! the identity above needs the full window, and it is what makes the printed
//! sd readable against the calibrated noise model instead of being in arbitrary
//! units. [`structure_contamination`] is that reading.
//!
//! # Which direction it can be fooled in (rule 18)
//!
//! Upward-blind, never upward-fooled. `hp_sd` still contains whatever scene
//! structure survives the box's stop band, so it is an **upper bound on the
//! noise and a lower bound on any noise ratio**: a ratio of two contaminated
//! sds under-reports a large explosion by exactly the reference's
//! [`structure_contamination`] factor. Measured on the two corpus flat ROIs
//! (`experiments/m53-flat-ratio/out/a2_kernel_sweep.log`) that factor is
//! **1.2756x** (`109MSDCF`) and **1.9101x** (`119MSDCF`, at the stale ISO-50
//! gain; ~1.35x at the M25-corrected gain), against the legacy raw statistic's
//! **8.70x** and **19.07x**. So the replacement does not remove the
//! under-report, it shrinks it by 6.8x / 14.1x and — unlike the raw ratio —
//! **prints the residual bound next to the number**.
//!
//! A narrower box shrinks it further: `w = 3` measures 1.0234x on `109MSDCF`
//! and still separates the detail ROI from the flat one by 2.23x, so it has not
//! gone blind. `w = 9` ships anyway, because it is the kernel fact 469 was
//! measured with and swapping in an unmeasured one at the exact moment the
//! project is deleting a statistic for being an unmeasured choice would be the
//! same mistake in a new place. The sweep is recorded so the swap is a
//! one-constant change with evidence already behind it.

use crate::plane::PlaneGeometry;

/// Side of the box whose mean is subtracted. M41's `w = 9`; see the module
/// docs for the reconciliation and for the measured `w = 3` alternative.
pub const HP_BOX_SIDE: usize = 9;

/// Radius of [`HP_BOX_SIDE`], in the sense [`crate::boxfilter::box_mean`] uses.
pub const HP_BOX_RADIUS: usize = HP_BOX_SIDE / 2;

/// White-noise gain of the shipped high-pass: `sqrt(1 - 1 / HP_BOX_SIDE^2)`.
///
/// DERIVED in the module docs and MEASURED against it in
/// `white_noise_comes_out_at_sigma_times_the_derived_gain`.
pub const HP_NOISE_GAIN: f64 = 0.993_807_989_999_906_5;

/// `sqrt(1 - 1/side^2)`: what white noise of sd `sigma` becomes after
/// `x - box_side(x)` on a full window.
#[must_use]
pub fn highpass_noise_gain(side: usize) -> f64 {
    let n = (side * side) as f64;
    (1.0 - 1.0 / n).sqrt()
}

/// Population mean and sd of a slice, accumulated in `f64`.
///
/// Duplicated deliberately rather than shared with the CLI's `mean_and_sigma`:
/// this crate must not depend on the binary, and the two agreeing is checked in
/// `strehl-cli` (`the_core_and_cli_moment_helpers_agree`).
#[must_use]
pub fn mean_and_sd(v: &[f32]) -> (f64, f64) {
    if v.is_empty() {
        return (0.0, 0.0);
    }
    let n = v.len() as f64;
    let mean = v.iter().map(|x| f64::from(*x)).sum::<f64>() / n;
    let var = v
        .iter()
        .map(|x| (f64::from(*x) - mean).powi(2))
        .sum::<f64>()
        / n;
    (mean, var.sqrt())
}

/// `roi - box_side(roi)`, evaluated only where the whole `side x side` window
/// lies inside the buffer.
///
/// Returns an empty vector when the ROI is not wider or taller than the box.
/// `side` must be odd; an even side has no centre pixel and the identity in the
/// module docs does not hold for it.
///
/// # Panics
///
/// If `roi.len() != width * height`, or if `side` is even or zero.
#[must_use]
pub fn highpass_residual(roi: &[f32], width: usize, height: usize, side: usize) -> Vec<f32> {
    assert_eq!(
        roi.len(),
        width * height,
        "high-pass input is {} samples for a {width}x{height} ROI",
        roi.len()
    );
    assert!(side % 2 == 1 && side > 0, "box side {side} must be odd");
    let radius = side / 2;
    if width <= 2 * radius || height <= 2 * radius {
        return Vec::new();
    }
    let geom = PlaneGeometry { width, height };
    let mut scratch = vec![0.0f32; roi.len()];
    let mut mean = vec![0.0f32; roi.len()];
    // `box_mean` clamps its window to the buffer, so its border values are
    // means over a truncated support. Every pixel kept below is at least
    // `radius` from every edge, where the clamp is inactive and the value is
    // the exact full-window mean the gain derivation assumes.
    crate::boxfilter::box_mean(roi, geom, radius, &mut scratch, &mut mean);
    (radius..height - radius)
        .flat_map(|y| (radius..width - radius).map(move |x| y * width + x))
        .map(|i| roi[i] - mean[i])
        .collect()
}

/// Spatial sd of the high-pass residual over the ROI's valid interior, in DN.
///
/// `None` when the ROI is too small to contain one whole box.
#[must_use]
pub fn highpass_sd_with_side(roi: &[f32], width: usize, height: usize, side: usize) -> Option<f64> {
    let hp = highpass_residual(roi, width, height, side);
    if hp.is_empty() {
        return None;
    }
    Some(mean_and_sd(&hp).1)
}

/// [`highpass_sd_with_side`] at the shipped [`HP_BOX_SIDE`].
#[must_use]
pub fn highpass_sd(roi: &[f32], width: usize, height: usize) -> Option<f64> {
    highpass_sd_with_side(roi, width, height, HP_BOX_SIDE)
}

/// How much of a high-pass sd is *not* accounted for by the calibrated noise
/// model: `hp_sd / (gain * model_sigma)`.
///
/// **Rule 10.** `model_sigma` is a TEMPORAL per-sample sigma and `hp_sd` is a
/// SPATIAL sd, so this is deliberately not an equality claim. It is a one-sided
/// reading: a spatial sd cannot be below the noise it contains, so a value of
/// 1.0 means the ROI is noise-dominated and anything above 1.0 is residual
/// scene structure. That excess is also, exactly, the factor by which a ratio
/// of two such sds under-reports a large noise explosion — so printing it
/// discloses the statistic's own blind spot next to the statistic.
///
/// Returns `f64::INFINITY` for a non-positive `model_sigma`, which is what a
/// caller should print rather than a silently plausible number.
#[must_use]
pub fn structure_contamination(hp_sd: f64, model_sigma: f64) -> f64 {
    if model_sigma > 0.0 {
        hp_sd / (HP_NOISE_GAIN * model_sigma)
    } else {
        f64::INFINITY
    }
}

/// The three numbers one frame's flat ROI contributes.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FrameFlat {
    /// Black-subtracted mean over the ROI, DN.
    pub mean: f64,
    /// Raw spatial sd, DN. **Legacy.** Kept only so that the number the corpus
    /// published for years stays readable; it is structure-dominated and must
    /// never be used for a noise ratio (fact 469).
    pub raw_sd: f64,
    /// High-pass residual sd over the valid interior, DN. The noise statistic.
    /// `None` when the ROI is smaller than one box.
    pub hp_sd: Option<f64>,
}

/// Reduce one frame's flat ROI to the numbers the reference distribution needs.
#[must_use]
pub fn frame_flat(roi: &[f32], width: usize, height: usize) -> FrameFlat {
    let (mean, raw_sd) = mean_and_sd(roi);
    FrameFlat {
        mean,
        raw_sd,
        hp_sd: highpass_sd(roi, width, height),
    }
}

/// A ratio against the whole per-frame reference distribution.
///
/// `median` is the point estimate; `lo` and `hi` are what the same merge would
/// have scored against the noisiest and quietest single frame in the stack.
/// They exist so that fact 441's 1.60x cannot hide inside an unstated choice:
/// a reader sees the range the number could have taken, beside the number.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct HpRatio {
    pub median: f64,
    /// `merged / max(reference)` — the most flattering denominator available.
    pub lo: f64,
    /// `merged / min(reference)` — the least flattering.
    pub hi: f64,
}

impl HpRatio {
    /// `hi / lo`: how far this ratio could be moved by choosing a reference
    /// frame. Equals the reference distribution's own [`FlatReference::spread`].
    #[must_use]
    pub fn range(&self) -> f64 {
        if self.lo > 0.0 {
            self.hi / self.lo
        } else {
            f64::INFINITY
        }
    }
}

/// Every frame's flat-ROI high-pass sd, sorted, with the frame each came from.
///
/// **This type exists to make fact 441 unrepresentable.** There is no
/// `reference()` accessor returning a single denominator, and no constructor
/// that takes one frame; a caller that wants a ratio gets [`HpRatio`], which
/// carries the spread with it.
#[derive(Debug, Clone, PartialEq)]
pub struct FlatReference {
    /// `(hp_sd, frame index)`, ascending by `hp_sd`.
    sorted: Vec<(f64, u16)>,
}

impl FlatReference {
    /// Build from `(frame index, hp_sd)` pairs. `None` if empty or if any
    /// entry is not finite and positive — a zero reference makes every ratio
    /// infinite, which is worse than refusing.
    #[must_use]
    pub fn new(per_frame: &[(u16, f64)]) -> Option<Self> {
        if per_frame.is_empty() || !per_frame.iter().all(|(_, v)| v.is_finite() && *v > 0.0) {
            return None;
        }
        let mut sorted: Vec<(f64, u16)> = per_frame.iter().map(|(i, v)| (*v, *i)).collect();
        sorted.sort_by(|a, b| a.0.total_cmp(&b.0));
        Some(Self { sorted })
    }

    #[must_use]
    pub fn frames(&self) -> usize {
        self.sorted.len()
    }

    /// The upper of the two middle values when the count is even — the same
    /// convention `flat_roi_stats` already uses for its median winner index, so
    /// the two medians in one report are not two different definitions.
    #[must_use]
    pub fn median(&self) -> f64 {
        self.sorted[self.sorted.len() / 2].0
    }

    /// The frame supplying [`FlatReference::median`].
    #[must_use]
    pub fn median_frame(&self) -> u16 {
        self.sorted[self.sorted.len() / 2].1
    }

    #[must_use]
    pub fn min(&self) -> f64 {
        self.sorted[0].0
    }

    #[must_use]
    pub fn min_frame(&self) -> u16 {
        self.sorted[0].1
    }

    #[must_use]
    pub fn max(&self) -> f64 {
        self.sorted[self.sorted.len() - 1].0
    }

    #[must_use]
    pub fn max_frame(&self) -> u16 {
        self.sorted[self.sorted.len() - 1].1
    }

    /// `max / min`: fact 441's quantity, computed rather than assumed absent.
    #[must_use]
    pub fn spread(&self) -> f64 {
        self.max() / self.min()
    }

    /// The merged field's high-pass sd as a ratio against this distribution.
    #[must_use]
    pub fn ratio(&self, merged_hp_sd: f64) -> HpRatio {
        HpRatio {
            median: merged_hp_sd / self.median(),
            lo: merged_hp_sd / self.max(),
            hi: merged_hp_sd / self.min(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// splitmix64, the same generator `merge.rs` and `focus.rs` use for their
    /// noise fixtures. Seeded per test so a failure is reproducible.
    struct Rng(u64);
    impl Rng {
        fn new(seed: u64) -> Self {
            Rng(seed)
        }
        fn next_u64(&mut self) -> u64 {
            self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = self.0;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            z ^ (z >> 31)
        }
        fn uniform(&mut self) -> f64 {
            ((self.next_u64() >> 11) as f64 + 1.0) / (1u64 << 53) as f64
        }
        fn normal(&mut self) -> f32 {
            let (u1, u2) = (self.uniform(), self.uniform());
            ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
        }
    }

    fn noise_field(seed: u64, n: usize, sigma: f32) -> Vec<f32> {
        let mut rng = Rng::new(seed);
        (0..n * n).map(|_| sigma * rng.normal()).collect()
    }

    /// Low-frequency scene structure with no noise in it at all. Amplitudes and
    /// periods are chosen to land the raw sd near the corpus's own flat ROI
    /// (76.272 DN on `109MSDCF`, fact 469) so the fixture is arguing about the
    /// regime the statistic actually runs in.
    fn structure(n: usize) -> Vec<f32> {
        (0..n)
            .flat_map(|y| (0..n).map(move |x| (x as f32, y as f32)))
            .map(|(x, y)| {
                400.0
                    + 90.0 * (x / 61.0).sin()
                    + 70.0 * (y / 43.0).cos()
                    + 40.0 * ((x + y) / 97.0).sin()
            })
            .collect()
    }

    fn add(a: &[f32], b: &[f32]) -> Vec<f32> {
        a.iter().zip(b).map(|(p, q)| p + q).collect()
    }

    #[test]
    fn the_shipped_gain_constant_equals_its_closed_form() {
        // Rule 35: the assertion's other term is the closed form derived in the
        // module docs, not the constant restated.
        let closed = (1.0 - 1.0 / ((HP_BOX_SIDE * HP_BOX_SIDE) as f64)).sqrt();
        assert!(
            (HP_NOISE_GAIN - closed).abs() < 1e-15,
            "{HP_NOISE_GAIN} vs {closed}"
        );
        assert!((highpass_noise_gain(HP_BOX_SIDE) - HP_NOISE_GAIN).abs() < 1e-15);
        // ... and the closed form is not 1.0, so the test below has something
        // to reject.
        assert!(closed < 0.9939 && closed > 0.9937, "{closed}");
    }

    /// **The gain test.** White noise of known sd, pushed through the shipped
    /// high-pass, must come out at `sigma * gain`.
    ///
    /// # Why the tolerance is derived and not chosen
    ///
    /// The residuals are very nearly uncorrelated — for adjacent pixels
    /// `Cov(r_i, r_j) = sigma^2 (-2/N + overlap/N^2) ~ -0.014 sigma^2` — so an
    /// sd estimated from `M` valid pixels carries a relative error near
    /// `1/sqrt(2M)`, which is 0.285 % at `M = 248^2`. Averaging `K = 8` seeds
    /// divides that by `sqrt(8)`, giving 0.101 %. The assertion below is 5
    /// standard errors on the mean and 5 standard deviations on any one seed;
    /// both were confirmed against a 64-draw scipy Monte Carlo at two ROI sizes
    /// (`experiments/m53-flat-ratio`, offsets -0.02 and -0.39 SE from theory).
    ///
    /// Several seeds, not one, because `merge.rs`'s own noise fixture found
    /// consecutive splitmix outputs laid out on a raster alias against a box
    /// filter differently for every seed, worth 30 % there.
    #[test]
    fn white_noise_comes_out_at_sigma_times_the_derived_gain() {
        const N: usize = 256;
        const SIGMA: f32 = 40.0;
        const SEEDS: u64 = 8;
        for side in [3usize, 5, 9, 15] {
            let m = (N - (side / 2) * 2).pow(2) as f64;
            let per_seed = 1.0 / (2.0 * m).sqrt();
            let on_mean = per_seed / (SEEDS as f64).sqrt();
            let gain = highpass_noise_gain(side);
            let mut sum = 0.0;
            for seed in 0..SEEDS {
                let field = noise_field(0x5153_0000 + seed, N, SIGMA);
                let sd = highpass_sd_with_side(&field, N, N, side).expect("ROI fits the box");
                let got = sd / f64::from(SIGMA);
                assert!(
                    (got - gain).abs() < 5.0 * per_seed * gain,
                    "side {side} seed {seed}: gain {got:.6} vs derived {gain:.6}, \
                     tolerance {:.6}",
                    5.0 * per_seed * gain
                );
                sum += got;
            }
            let mean = sum / SEEDS as f64;
            assert!(
                (mean - gain).abs() < 5.0 * on_mean * gain,
                "side {side}: mean gain {mean:.6} vs derived {gain:.6}, tolerance {:.6}",
                5.0 * on_mean * gain
            );
        }
    }

    /// The same fixture, read the other way: an implementation that forgot the
    /// gain would report `1.0`, and at `side = 3` the derived gain is 0.9428, so
    /// the test above has 20 standard errors of room to reject it. Stated as its
    /// own assertion because rule 20 asks for the input that makes a check fail.
    #[test]
    fn a_gainless_implementation_would_fail_the_gain_test_at_side_three() {
        const N: usize = 256;
        let field = noise_field(0x5153_00FF, N, 40.0);
        let sd = highpass_sd_with_side(&field, N, N, 3).expect("ROI fits the box");
        let got = sd / 40.0;
        let per_seed = 1.0 / (2.0 * ((N - 2) as f64).powi(2)).sqrt();
        assert!(
            (got - 1.0).abs() > 10.0 * per_seed,
            "side-3 gain {got:.6} is indistinguishable from 1.0, so the gain \
             assertion has no power"
        );
        assert!((got - highpass_noise_gain(3)).abs() < 5.0 * per_seed);
    }

    #[test]
    fn a_constant_field_and_a_plane_ramp_both_high_pass_to_zero() {
        const N: usize = 64;
        let flat = vec![1234.5f32; N * N];
        assert!(highpass_sd(&flat, N, N).expect("fits") < 1e-2);
        // A box mean of a plane is the centre value exactly, so a ramp is in the
        // kernel of the operator. This is the structure rejection the raw sd
        // does not have: the ramp's own raw sd is enormous.
        let ramp: Vec<f32> = (0..N)
            .flat_map(|y| (0..N).map(move |x| 3.0 * x as f32 - 2.0 * y as f32 + 500.0))
            .collect();
        assert!(
            mean_and_sd(&ramp).1 > 50.0,
            "the fixture must have structure"
        );
        assert!(highpass_sd(&ramp, N, N).expect("fits") < 1e-2);
    }

    /// Fact 469's mechanism, in a unit test: on a structured ROI the raw sd
    /// reads many times the noise while the high-pass sd reads the noise.
    #[test]
    fn the_raw_sd_is_structure_dominated_where_the_high_pass_sd_is_not() {
        const N: usize = 256;
        const SIGMA: f32 = 8.77; // fact 469's modelled sigma on 109MSDCF
        let field = add(&structure(N), &noise_field(0xBEEF_0001, N, SIGMA));
        let (_, raw) = mean_and_sd(&field);
        let hp = highpass_sd(&field, N, N).expect("fits");

        // The fixture has to reproduce the regime, or the test proves nothing
        // (rule 36). 109MSDCF measured raw/sigma = 8.70x.
        let raw_over_sigma = raw / f64::from(SIGMA);
        assert!(
            (5.0..15.0).contains(&raw_over_sigma),
            "fixture raw sd is {raw:.3} DN = {raw_over_sigma:.2}x sigma; the real \
             flat ROI is 8.70x and the test is only about that regime"
        );
        // And the statistic under test reads the noise, to within the residual
        // structure the box's stop band cannot remove.
        let contamination = structure_contamination(hp, f64::from(SIGMA));
        assert!(
            contamination < 1.05,
            "high-pass sd {hp:.3} DN is {contamination:.4}x the modelled sigma"
        );
    }

    /// **The negative control, in-crate.** A known noise explosion is planted on
    /// a structured ROI. The legacy raw ratio must miss it and the shipped
    /// high-pass ratio must not.
    ///
    /// The plant is an added white field of sd `p`, so the true per-sample noise
    /// ratio is `sqrt(sigma^2 + p^2) / sigma` — obtained from the noise model,
    /// which is independent of both statistics being scored (rule 35). The
    /// larger real-data version of this control lives in
    /// `experiments/m53-flat-ratio/src/a3_negative_control.py`.
    #[test]
    fn the_high_pass_ratio_catches_a_planted_explosion_the_raw_ratio_misses() {
        const N: usize = 256;
        const SIGMA: f32 = 8.77;
        const K: f64 = 10.0; // planted noise multiplier
        let scene = structure(N);
        let single = add(&scene, &noise_field(0xBEEF_0002, N, SIGMA));
        // sqrt(K^2 - 1) more noise in quadrature makes the total noise K x.
        let extra = (K * K - 1.0).sqrt() as f32 * SIGMA;
        let merged = add(&single, &noise_field(0xBEEF_0003, N, extra));

        let (_, raw_ref) = mean_and_sd(&single);
        let (_, raw_merged) = mean_and_sd(&merged);
        let legacy_ratio = raw_merged / raw_ref;

        let hp_ref = highpass_sd(&single, N, N).expect("fits");
        let hp_merged = highpass_sd(&merged, N, N).expect("fits");
        let hp_ratio = hp_merged / hp_ref;

        // (a) the legacy statistic under-reports, badly. Assert the direction and
        //     the size, because "it is worse" with no number is not a finding.
        assert!(
            legacy_ratio < 0.35 * K,
            "the legacy raw ratio read {legacy_ratio:.3}x for a planted {K}x — if it \
             ever reads close to {K} this control has lost its power and the \
             comparison below is vacuous"
        );
        // (b) the shipped statistic recovers most of it. The shortfall is the
        //     reference's own structure contamination and nothing else, so it is
        //     asserted against that measured quantity rather than a round number.
        let contamination = structure_contamination(hp_ref, f64::from(SIGMA));
        let predicted = K / contamination;
        assert!(
            (hp_ratio - predicted).abs() < 0.05 * predicted,
            "high-pass ratio {hp_ratio:.3}x against a predicted {predicted:.3}x \
             (= planted {K}x / contamination {contamination:.4}x)"
        );
        assert!(
            hp_ratio > 4.0 * legacy_ratio,
            "high-pass {hp_ratio:.3}x vs legacy {legacy_ratio:.3}x: the replacement \
             must be a large multiple better, not a rounding better"
        );
    }

    /// Fact 441, made unrepresentable. The fixture is fact 441's own measured
    /// range on `119MSDCF` — 1.0000x to 1.5989x over the choice of denominator —
    /// so the assertion's other term is a number in `SYNTHESIS.md` a human can
    /// go and read.
    #[test]
    fn the_reference_is_the_whole_frame_distribution_not_one_frame() {
        let per_frame: Vec<(u16, f64)> = vec![
            (0, 10.0),
            (1, 12.4),
            (2, 11.1),
            (3, 15.989), // fact 441's 1.5989x, against frame 0's 1.0000x
            (4, 13.0),
        ];
        let r = FlatReference::new(&per_frame).expect("five valid frames");
        assert_eq!(r.frames(), 5);
        assert_eq!(r.min_frame(), 0);
        assert_eq!(r.max_frame(), 3);
        assert!((r.min() - 10.0).abs() < 1e-12);
        assert!((r.max() - 15.989).abs() < 1e-12);
        assert!((r.median() - 12.4).abs() < 1e-12);
        assert_eq!(r.median_frame(), 1);
        assert!(
            (r.spread() - 1.5989).abs() < 1e-4,
            "spread {:.4} should reproduce fact 441's 119MSDCF range",
            r.spread()
        );

        // A merge is scored against all of it at once.
        let got = r.ratio(24.8);
        assert!((got.median - 2.0).abs() < 1e-9);
        assert!((got.lo - 24.8 / 15.989).abs() < 1e-9);
        assert!((got.hi - 24.8 / 10.0).abs() < 1e-9);
        assert!(got.lo < got.median && got.median < got.hi);
        assert!(
            (got.range() - r.spread()).abs() < 1e-9,
            "the ratio's range must be exactly the reference's spread"
        );
    }

    #[test]
    fn a_reference_refuses_to_be_built_from_nothing_or_from_a_zero() {
        assert!(FlatReference::new(&[]).is_none());
        assert!(FlatReference::new(&[(0, 0.0)]).is_none());
        assert!(FlatReference::new(&[(0, f64::NAN)]).is_none());
        assert!(FlatReference::new(&[(0, 1.0), (1, -2.0)]).is_none());
        assert!(FlatReference::new(&[(7, 3.5)]).is_some());
    }

    #[test]
    fn an_roi_smaller_than_the_box_has_no_high_pass_statistic() {
        let small = vec![1.0f32; 9 * 8];
        assert!(highpass_sd(&small, 9, 8).is_none());
        assert!(highpass_residual(&small, 9, 8, HP_BOX_SIDE).is_empty());
        // Exactly one whole box fits at 9x9, giving exactly one residual sample.
        let one = vec![1.0f32; 9 * 9];
        assert_eq!(highpass_residual(&one, 9, 9, HP_BOX_SIDE).len(), 1);
        assert!(highpass_sd(&one, 9, 9).is_some());
    }

    #[test]
    fn the_residual_keeps_only_the_valid_interior() {
        const W: usize = 40;
        const H: usize = 30;
        let field = noise_field(0x1234, W.max(H), 5.0);
        let field = field[..W * H].to_vec();
        let hp = highpass_residual(&field, W, H, HP_BOX_SIDE);
        assert_eq!(hp.len(), (W - 2 * HP_BOX_RADIUS) * (H - 2 * HP_BOX_RADIUS));
    }

    #[test]
    fn a_dc_offset_does_not_move_the_high_pass_sd() {
        const N: usize = 64;
        let field = add(&structure(N), &noise_field(0x77, N, 6.0));
        let lifted: Vec<f32> = field.iter().map(|v| v + 5000.0).collect();
        let a = highpass_sd(&field, N, N).expect("fits");
        let b = highpass_sd(&lifted, N, N).expect("fits");
        assert!((a - b).abs() < 1e-3 * a, "{a} vs {b}");
        // The raw sd is invariant too; it is the *ratio* that structure moves,
        // which is why this is not the property that was broken.
        let (_, ra) = mean_and_sd(&field);
        let (_, rb) = mean_and_sd(&lifted);
        assert!((ra - rb).abs() < 1e-3 * ra);
    }

    #[test]
    fn frame_flat_reports_all_three_numbers_together() {
        const N: usize = 128;
        let field = add(&structure(N), &noise_field(0x99, N, 9.0));
        let f = frame_flat(&field, N, N);
        let (mean, raw) = mean_and_sd(&field);
        assert!((f.mean - mean).abs() < 1e-9);
        assert!((f.raw_sd - raw).abs() < 1e-9);
        assert_eq!(f.hp_sd, highpass_sd(&field, N, N));
        // The legacy and the shipped numbers are not the same quantity, and the
        // whole milestone is that gap.
        assert!(f.raw_sd > 4.0 * f.hp_sd.expect("fits"));
    }

    #[test]
    fn structure_contamination_is_one_on_pure_noise_and_above_one_with_structure() {
        const N: usize = 256;
        const SIGMA: f32 = 9.0;
        let pure = noise_field(0xAA_0001, N, SIGMA);
        let c_pure =
            structure_contamination(highpass_sd(&pure, N, N).expect("fits"), f64::from(SIGMA));
        assert!((c_pure - 1.0).abs() < 0.02, "pure noise read {c_pure:.4}x");

        let structured = add(&structure(N), &pure);
        let c_struct = structure_contamination(
            highpass_sd(&structured, N, N).expect("fits"),
            f64::from(SIGMA),
        );
        assert!(c_struct > c_pure, "{c_struct:.4} vs {c_pure:.4}");
        assert!(structure_contamination(1.0, 0.0).is_infinite());
    }
}
