//! The calibrated sensor noise model.
//!
//! This is injected into every stage that needs a noise floor. Nothing
//! downstream is allowed to invent its own estimate — see `AGENTS.md` rule 3.
//!
//! The model is the standard affine photon-transfer relation, in DN:
//!
//! ```text
//! sigma^2(S) = g * S + (RN_e * g)^2
//! ```
//!
//! where `S` is the black-subtracted signal in DN, `g` is the gain in DN per
//! electron, and `RN_e` is the read noise in electrons. Shot noise is Poisson so
//! its variance in DN scales linearly with signal; read noise is signal
//! independent.
//!
//! # The missing third term, and why it is opt-in
//!
//! There is a measured third term: **photo-response non-uniformity**, a fixed
//! multiplicative per-photosite pattern of `kappa = 0.3096%` on the greens
//! (SYNTHESIS fact 1062, `docs/research/M71-flat-fields.md`). With it the
//! relation is
//!
//! ```text
//! sigma^2(S) = g * S + (RN_e * g)^2 + (kappa * S)^2
//! ```
//!
//! and the shipped model without it is **over-confident above S = 504 DN,
//! reaching -12.8% at S = 8000** (fact 1064), because the profile gain is 2.16%
//! high and the two errors cancel at exactly one signal level.
//!
//! **The term is nevertheless not in the default path**, and the reason is
//! coupling rather than physics. `PlaneNoise::variance` is a shared normaliser
//! with several consumers, and PRNU is a *fixed pattern* while the rest of this
//! model is *temporal*. Those are not interchangeable: a consumer that forms a
//! **between-frame difference** sees the fixed pattern cancel, and a consumer
//! that forms an **across-frame average** does not. So the term is exposed here
//! as [`Prnu`] and applied only by the `*_with_fixed_pattern` and
//! [`NoiseModel::averaged_green_luma_sigma`] entry points, which no shipped
//! stage calls. See `docs/research/M90-prnu-noise-model.md` for which consumer
//! is which and why, and for the byte-identity proof that turning this on by
//! default is a one-line change and turning it off changes nothing.
//!
//! # Provenance, and why a runtime estimator is needed
//!
//! The A7C II coefficients were originally inferred by reproducing the camera's
//! own white level to 0.23%. That is a consistency check on one relation, **not
//! a photon-transfer measurement**. A wrong noise floor does not raise an error;
//! it silently mis-gates the merge and quietly degrades the output.
//!
//! So a runtime estimator belongs on the v1 path, not on a list of future
//! niceties, and a profiled body should be validated against what its own
//! frames actually show.
//!
//! **It does not exist.** This paragraph read "So `NoiseModel::estimated`
//! exists on the v1 path ... and profiled bodies are validated against it",
//! naming a function that was never written. There is no runtime estimator and
//! nothing cross-checks a profiled body against a measured one. [`Provenance`]
//! recording which of `Profile`, `Measured` or `Fallback` a model came from is
//! the whole of the safeguard today, and it labels the gap rather than closing
//! it. Stated here as an open gap because a promise in the present tense reads
//! as a shipped feature to everyone who did not write it.

use crate::CfaPlane;

/// Black and white levels for one CFA plane, in DN.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Levels {
    pub black: f32,
    /// Usable white level. For the A7C II this is 15360, **not** 16383 —
    /// confirmed by measurement, see `docs/research/M1-decode-measured.md`.
    pub white: f32,
}

impl Levels {
    pub fn range(&self) -> f32 {
        self.white - self.black
    }
}

/// Where a set of coefficients came from. Carried at runtime so that a stage can
/// report, and a test can assert, that it was not silently running on a guess.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Provenance {
    /// Read from a camera profile data file.
    Profile,
    /// Fitted from the frames of this stack.
    Measured,
    /// Neither available. Gating decisions made against this are untrustworthy.
    Fallback,
}

/// Per-plane noise coefficients.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PlaneNoise {
    /// Gain, DN per electron.
    pub gain_dn_per_e: f32,
    /// Read noise, electrons.
    pub read_noise_e: f32,
    pub levels: Levels,
}

impl PlaneNoise {
    /// Noise variance in DN^2 at a black-subtracted signal level.
    ///
    /// Clamps negative signal to zero: sensor noise straddles the black level,
    /// so individual samples legitimately land below it, and a negative variance
    /// is meaningless.
    ///
    /// **This is the temporal variance only.** It deliberately excludes the
    /// measured PRNU term — see the module header and [`Prnu`]. Nothing was
    /// added here, so every threshold calibrated against this function is
    /// untouched.
    pub fn variance(&self, signal_dn: f32) -> f32 {
        let s = signal_dn.max(0.0);
        let read_dn = self.read_noise_e * self.gain_dn_per_e;
        self.gain_dn_per_e * s + read_dn * read_dn
    }

    /// Noise standard deviation in DN at a black-subtracted signal level.
    pub fn sigma(&self, signal_dn: f32) -> f32 {
        self.variance(signal_dn).sqrt()
    }

    /// Read-noise floor in DN, `RN_e * g`.
    ///
    /// **This product, not either factor, is what was measured.**
    /// `profile.rs`'s `read_noise_e` was fitted to dark sigma in DN *through*
    /// that profile's own gain, so scaling the gain without scaling
    /// `read_noise_e` inversely silently moves the model away from the measured
    /// dark frames. [`crate::profile::Corrections`] preserves this product by
    /// construction, and `the_measured_gain_correction_preserves_the_dark_floor`
    /// asserts it.
    pub fn read_floor_dn(&self) -> f32 {
        self.read_noise_e * self.gain_dn_per_e
    }
}

/// Photo-response non-uniformity: the **fixed** multiplicative per-photosite
/// pattern, as a fraction of signal.
///
/// MEASURED by M71 from 484 flat fields (SYNTHESIS fact 1062): `kappa` =
/// **0.3096%** per green photosite, spread +/-0.0159% over five matched pairs,
/// with the paper-texture confound bounded by measurement at 0.09-0.14% of the
/// PRNU variance. Per plane: R 0.3102%, greens 0.3096%, B 0.2528% (M71 §8.1).
///
/// # This is not temporal noise, and the difference decides where it belongs
///
/// Every other term in this module fluctuates from frame to frame and averages
/// down as `1/sqrt(n)`. PRNU does not: it is the same pattern in every frame at
/// the same photosite. Three consequences, and they point in different
/// directions for different consumers:
///
/// * A statistic formed as a **difference between two frames** at one pixel
///   (`focus.rs`'s gate comparison, [`crate::merge::Estimator::disagreement`])
///   sees the fixed pattern **cancel**. Adding `kappa` to its denominator makes
///   it anti-conservative.
/// * A statistic formed as an **average across frames**
///   ([`crate::merge::Estimator::predicted_sigma`]) sees the fixed pattern
///   **survive undiminished**. Leaving `kappa` out of it makes it
///   over-confident, and increasingly so with signal.
/// * A **single-sample** prediction — one photosite in one frame — sees the
///   whole of it. That is [`NoiseModel::sigma_with_fixed_pattern`].
///
/// The fraction that survives a warp, `rho_warp`, is the free parameter in the
/// averaging case and it is **not measured anywhere in this corpus**; M71 §11
/// names it as the blocking measurement. [`NoiseModel::averaged_green_luma_sigma`]
/// takes it as an argument rather than assuming one.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Prnu {
    /// Per-plane `kappa` as a fraction of signal, indexed as
    /// `[R, G1, B, G2]` — [`CfaPlane::ALL`] order.
    kappa: [f32; 4],
}

impl Prnu {
    /// M71's per-plane measurement on the A7C II (fact 1062, M71 §8.1).
    pub const A7C2_MEASURED: Prnu = Prnu {
        kappa: [0.003_102, 0.003_096, 0.002_528, 0.003_096],
    };

    /// No fixed pattern. The placebo arm: switching the machinery on with this
    /// must reproduce the default path exactly.
    pub const NONE: Prnu = Prnu { kappa: [0.0; 4] };

    /// The same `kappa` on every plane.
    pub const fn uniform(kappa: f32) -> Prnu {
        Prnu {
            kappa: [kappa; 4],
        }
    }

    /// Per-plane, in [`CfaPlane::ALL`] order.
    pub const fn per_plane(r: f32, g1: f32, b: f32, g2: f32) -> Prnu {
        Prnu {
            kappa: [r, g1, b, g2],
        }
    }

    /// `kappa` for one plane, as a fraction of signal.
    #[inline]
    pub fn kappa(&self, p: CfaPlane) -> f32 {
        self.kappa[plane_slot(p)]
    }

    /// True when this carries no pattern at all, so a consumer can assert that
    /// its placebo arm really is one.
    pub fn is_none(&self) -> bool {
        self.kappa.iter().all(|k| *k == 0.0)
    }
}

#[inline]
const fn plane_slot(p: CfaPlane) -> usize {
    match p {
        CfaPlane::R => 0,
        CfaPlane::G1 => 1,
        CfaPlane::B => 2,
        CfaPlane::G2 => 3,
    }
}

/// The calibrated noise model for one stack, at one ISO.
#[derive(Debug, Clone)]
pub struct NoiseModel {
    planes: [PlaneNoise; 4],
    /// The measured fixed pattern, when a caller has opted in. `None` on the
    /// default path, and every pre-M90 method ignores it either way.
    prnu: Option<Prnu>,
    pub iso: f32,
    pub provenance: Provenance,
}

impl NoiseModel {
    pub fn new(planes: [PlaneNoise; 4], iso: f32, provenance: Provenance) -> Self {
        Self {
            planes,
            prnu: None,
            iso,
            provenance,
        }
    }

    /// Attach the measured fixed pattern.
    ///
    /// **This changes nothing on its own.** No pre-M90 method reads it; only
    /// the `*_with_fixed_pattern` entry points and
    /// [`Self::averaged_green_luma_sigma`] do. Flipping the default means
    /// changing the call sites, not this constructor — deliberately, so the
    /// change is one visible line per consumer rather than an invisible global.
    #[must_use]
    pub fn with_prnu(mut self, prnu: Prnu) -> Self {
        self.prnu = Some(prnu);
        self
    }

    /// The attached fixed pattern, if any.
    pub fn prnu(&self) -> Option<Prnu> {
        self.prnu
    }

    pub fn plane(&self, p: CfaPlane) -> &PlaneNoise {
        &self.planes[plane_slot(p)]
    }

    /// Variance in DN^2 for a sample on a given plane.
    pub fn variance(&self, p: CfaPlane, signal_dn: f32) -> f32 {
        self.plane(p).variance(signal_dn)
    }

    /// Standard deviation in DN for a sample on a given plane.
    pub fn sigma(&self, p: CfaPlane, signal_dn: f32) -> f32 {
        self.plane(p).sigma(signal_dn)
    }

    /// Variance in DN^2 of a **single sample** on a plane, fixed pattern
    /// included.
    ///
    /// `Var = g*S + (RN_e*g)^2 + (kappa*S)^2`. With no [`Prnu`] attached this is
    /// exactly [`Self::variance`], which is what makes the opt-in reversible.
    pub fn variance_with_fixed_pattern(&self, p: CfaPlane, signal_dn: f32) -> f32 {
        let base = self.variance(p, signal_dn);
        match self.prnu {
            None => base,
            Some(k) => {
                let fp = k.kappa(p) * signal_dn.max(0.0);
                base + fp * fp
            }
        }
    }

    /// Standard deviation in DN of a single sample, fixed pattern included.
    pub fn sigma_with_fixed_pattern(&self, p: CfaPlane, signal_dn: f32) -> f32 {
        self.variance_with_fixed_pattern(p, signal_dn).sqrt()
    }

    /// Standard deviation in DN of the green luma `L = (G1 + G2) / 2`.
    ///
    /// The two greens are separate photosites and their read noise is
    /// independent, so `Var(L) = (Var(G1) + Var(G2)) / 4`. Both are evaluated at
    /// `luma_dn`, which assumes the two greens carry the same signal — true
    /// except where a feature falls between the two green lattices.
    ///
    /// **`luma_dn` is the MEAN of the two greens, not their sum** — see
    /// [`crate::plane::green_luma_with_clip`], which emits `0.5 * (G1 + G2)`. So
    /// a signal level quoted "per photosite" and a signal level quoted "in luma
    /// DN" are the *same* number here, and any statement that converts between
    /// them by a factor of two is about a different quantity.
    pub fn green_luma_sigma(&self, luma_dn: f32) -> f32 {
        let v = self.variance(CfaPlane::G1, luma_dn) + self.variance(CfaPlane::G2, luma_dn);
        (0.25 * v).sqrt()
    }

    /// [`Self::green_luma_sigma`] with the fixed pattern included.
    ///
    /// PRNU is **independent between the two greens** — M71 measured it that
    /// way, since `var(G1 - G2) = 2*kappa^2*S^2` requires it — so it enters the
    /// luma average exactly as the temporal terms do, `/4` after summing the two
    /// planes. That is why the *relative* inflation of the luma sigma equals the
    /// relative inflation of a single photosite's sigma at the same DN, and why
    /// the shipped model's zero-crossing sits at the same signal level in both
    /// domains.
    pub fn green_luma_sigma_with_fixed_pattern(&self, luma_dn: f32) -> f32 {
        let v = self.variance_with_fixed_pattern(CfaPlane::G1, luma_dn)
            + self.variance_with_fixed_pattern(CfaPlane::G2, luma_dn);
        (0.25 * v).sqrt()
    }

    /// Predicted standard deviation of the **average of `n` frames**' green luma
    /// at one output pixel, fixed pattern included.
    ///
    /// This is the form the merge's output confidence needs, and it is the one
    /// place in this module where the fixed-pattern term does not behave like
    /// the others:
    ///
    /// ```text
    /// Var = Var_temporal / n  +  Var_fixed * ( rho + (1 - rho) / n )
    /// ```
    ///
    /// `rho_warp` is the fraction of the fixed pattern that stays correlated
    /// across the admitted frames. At `rho = 1` — every frame samples the same
    /// photosite, which fact 230 measures as the case for adjacent frames, whose
    /// relative warp is **0.07-0.22 green px** — PRNU does not average down at
    /// all. At `rho = 0` it averages down exactly like temporal noise and this
    /// reduces to `green_luma_sigma_with_fixed_pattern / sqrt(n)`.
    ///
    /// **`rho_warp` is unmeasured** (M71 §11). It is an argument rather than a
    /// constant precisely so that no call site can acquire one by accident.
    ///
    /// The caller multiplies by [`crate::merge::selection_inflation`] if it
    /// wants the selection penalty; that is the merge's business, not the noise
    /// model's.
    pub fn averaged_green_luma_sigma(&self, luma_dn: f32, n: u16, rho_warp: f32) -> f32 {
        let n = f32::from(n.max(1));
        let rho = rho_warp.clamp(0.0, 1.0);
        let temporal =
            0.25 * (self.variance(CfaPlane::G1, luma_dn) + self.variance(CfaPlane::G2, luma_dn));
        let fixed = match self.prnu {
            None => 0.0,
            Some(k) => {
                let s = luma_dn.max(0.0);
                let a = k.kappa(CfaPlane::G1) * s;
                let b = k.kappa(CfaPlane::G2) * s;
                0.25 * (a * a + b * b)
            }
        };
        (temporal / n + fixed * (rho + (1.0 - rho) / n)).sqrt()
    }

    /// True when every gating decision made against this model is trustworthy.
    pub fn is_trustworthy(&self) -> bool {
        !matches!(self.provenance, Provenance::Fallback)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn plane(gain: f32, rn: f32) -> PlaneNoise {
        PlaneNoise {
            gain_dn_per_e: gain,
            read_noise_e: rn,
            levels: Levels {
                black: 512.0,
                white: 15360.0,
            },
        }
    }

    #[test]
    fn variance_is_affine_in_signal() {
        let p = plane(0.229, 1.47);
        // Read-noise floor at zero signal.
        let floor = (1.47f32 * 0.229).powi(2);
        assert!((p.variance(0.0) - floor).abs() < 1e-6);
        // Shot noise adds linearly.
        assert!((p.variance(1000.0) - (0.229 * 1000.0 + floor)).abs() < 1e-3);
    }

    #[test]
    fn negative_signal_clamps_rather_than_producing_negative_variance() {
        let p = plane(0.229, 1.47);
        // Noise straddles black, so below-black samples are normal and must not
        // produce a negative variance.
        assert_eq!(p.variance(-50.0), p.variance(0.0));
        assert!(p.sigma(-50.0).is_finite());
    }

    #[test]
    fn shot_noise_dominates_read_noise_in_the_midtones() {
        let p = plane(0.229, 1.47);
        let read_var = p.variance(0.0);
        let mid_var = p.variance(7000.0);
        assert!(mid_var > 100.0 * read_var);
    }

    #[test]
    fn fallback_provenance_is_flagged_untrustworthy() {
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Fallback);
        assert!(!m.is_trustworthy());
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Measured);
        assert!(m.is_trustworthy());
    }

    #[test]
    fn usable_white_level_is_not_the_container_maximum() {
        // Measured, M1: rawler reports 15360 for the A7C II, not 16383.
        let p = plane(0.229, 1.47);
        assert_eq!(p.levels.white, 15360.0);
        assert_eq!(p.levels.range(), 14848.0);
    }

    #[test]
    fn green_luma_sigma_is_the_averaging_of_two_independent_greens() {
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile);
        let single = m.sigma(CfaPlane::G1, 3000.0);
        let luma = m.green_luma_sigma(3000.0);
        // Averaging two independent samples: sigma / sqrt(2).
        assert!((luma - single / 2f32.sqrt()).abs() < 1e-4);
    }

    // ---------------------------------------------------------------------
    // M90 — the opt-in fixed-pattern term
    // ---------------------------------------------------------------------

    /// The whole of Deliverable A's promise, asserted on the bits.
    ///
    /// Every pre-M90 accessor must return the **identical f32** with a `Prnu`
    /// attached and without one, across the whole container range and all four
    /// planes. `to_bits` rather than an epsilon, because "bit-identical" is the
    /// claim and an epsilon would not test it.
    #[test]
    fn attaching_prnu_changes_no_pre_existing_accessor() {
        let base = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile);
        let with = base.clone().with_prnu(Prnu::A7C2_MEASURED);
        assert!(base.prnu().is_none());
        assert!(with.prnu().is_some());
        for s in (0..=16_383).step_by(7) {
            let s = s as f32;
            assert_eq!(
                base.green_luma_sigma(s).to_bits(),
                with.green_luma_sigma(s).to_bits(),
                "green_luma_sigma moved at S = {s}"
            );
            for p in CfaPlane::ALL {
                assert_eq!(base.variance(p, s).to_bits(), with.variance(p, s).to_bits());
                assert_eq!(base.sigma(p, s).to_bits(), with.sigma(p, s).to_bits());
            }
        }
    }

    /// The placebo. Switching the machinery on with a zero pattern must be
    /// indistinguishable from not switching it on, or every downstream arm
    /// measured against it is void.
    #[test]
    fn a_zero_prnu_is_a_true_placebo() {
        let base = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile);
        let placebo = base.clone().with_prnu(Prnu::NONE);
        assert!(Prnu::NONE.is_none());
        assert!(!Prnu::A7C2_MEASURED.is_none());
        for s in (0..=16_383).step_by(11) {
            let s = s as f32;
            assert_eq!(
                base.green_luma_sigma(s).to_bits(),
                placebo.green_luma_sigma_with_fixed_pattern(s).to_bits(),
                "the placebo moved the luma sigma at S = {s}"
            );
            for p in CfaPlane::ALL {
                assert_eq!(
                    base.variance(p, s).to_bits(),
                    placebo.variance_with_fixed_pattern(p, s).to_bits()
                );
            }
        }
    }

    /// Without a `Prnu` attached the new entry points *are* the old ones, so a
    /// caller that migrates to them before the constants land sees no change.
    #[test]
    fn the_fixed_pattern_entry_points_reduce_to_the_shipped_model_when_unset() {
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile);
        for s in [0.0f32, 1.0, 504.0, 8000.0, 15360.0] {
            assert_eq!(
                m.green_luma_sigma(s).to_bits(),
                m.green_luma_sigma_with_fixed_pattern(s).to_bits()
            );
            // n = 1 with no pattern is exactly the single-frame sigma.
            assert_eq!(
                m.green_luma_sigma(s).to_bits(),
                m.averaged_green_luma_sigma(s, 1, 0.0).to_bits()
            );
        }
    }

    /// The term is quadratic in signal and zero at zero, which is what makes the
    /// error signal-dependent rather than a constant offset.
    #[test]
    fn the_fixed_pattern_term_is_quadratic_in_signal_and_vanishes_at_zero() {
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile)
            .with_prnu(Prnu::uniform(0.003_096));
        assert_eq!(
            m.variance(CfaPlane::G1, 0.0).to_bits(),
            m.variance_with_fixed_pattern(CfaPlane::G1, 0.0).to_bits()
        );
        let excess = |s: f32| {
            m.variance_with_fixed_pattern(CfaPlane::G1, s) - m.variance(CfaPlane::G1, s)
        };
        // Doubling S must quadruple the excess variance.
        let ratio = excess(8000.0) / excess(4000.0);
        assert!((ratio - 4.0).abs() < 1e-3, "excess ratio {ratio}");
        // And it must match kappa^2 * S^2 directly.
        let want = (0.003_096f32 * 8000.0).powi(2);
        assert!((excess(8000.0) - want).abs() / want < 1e-4);
    }

    /// A negative signal must not manufacture fixed-pattern variance, for the
    /// same reason `variance` clamps: samples legitimately land below black.
    #[test]
    fn a_below_black_sample_carries_no_fixed_pattern_variance() {
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile)
            .with_prnu(Prnu::A7C2_MEASURED);
        assert_eq!(
            m.variance_with_fixed_pattern(CfaPlane::G1, -50.0).to_bits(),
            m.variance(CfaPlane::G1, 0.0).to_bits()
        );
        assert!(m.sigma_with_fixed_pattern(CfaPlane::G1, -50.0).is_finite());
    }

    /// The relative inflation of the luma sigma equals the relative inflation of
    /// one photosite's sigma at the same DN.
    ///
    /// This is the arithmetic behind M90's correction to M71 §8.3: because
    /// `green_luma_with_clip` emits the **mean** of the two greens and
    /// `green_luma_sigma` evaluates both planes at that mean, there is no factor
    /// of two between "per photosite" and "in luma DN". A statement that the
    /// crossover moves from 504 DN to 1009 DN is about a luma defined as the
    /// *sum*, which this crate does not compute anywhere.
    #[test]
    fn the_luma_inflation_equals_the_photosite_inflation_at_the_same_dn() {
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile)
            .with_prnu(Prnu::uniform(0.003_096));
        for s in [100.0f32, 504.0, 2000.0, 8000.0, 15360.0] {
            let photosite = m.sigma_with_fixed_pattern(CfaPlane::G1, s) / m.sigma(CfaPlane::G1, s);
            let luma = m.green_luma_sigma_with_fixed_pattern(s) / m.green_luma_sigma(s);
            assert!(
                (photosite - luma).abs() < 1e-6,
                "S = {s}: photosite {photosite} vs luma {luma}"
            );
        }
        // And the luma sigma is still exactly the photosite sigma over sqrt(2)
        // once the pattern is in, which is what makes that true.
        let s = 8000.0;
        let want = m.sigma_with_fixed_pattern(CfaPlane::G1, s) / 2f32.sqrt();
        assert!((m.green_luma_sigma_with_fixed_pattern(s) - want).abs() < 1e-3);
    }

    /// `rho_warp` is the whole of the fixed-versus-temporal distinction, and the
    /// two endpoints must behave like the two physical stories.
    #[test]
    fn rho_warp_interpolates_between_a_fixed_pattern_and_a_temporal_one() {
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile)
            .with_prnu(Prnu::uniform(0.003_096));
        let s = 8000.0f32;
        let n = 16u16;
        // rho = 0: the pattern averages down exactly like temporal noise.
        let decorrelated = m.averaged_green_luma_sigma(s, n, 0.0);
        let want = m.green_luma_sigma_with_fixed_pattern(s) / f32::from(n).sqrt();
        assert!((decorrelated - want).abs() / want < 1e-5);
        // rho = 1: it does not average down at all, so the merged sigma is
        // strictly larger and floors on the pattern.
        let correlated = m.averaged_green_luma_sigma(s, n, 1.0);
        assert!(correlated > decorrelated);
        let floor = m.green_luma_sigma_with_fixed_pattern(s).powi(2)
            - m.green_luma_sigma(s).powi(2);
        assert!(correlated.powi(2) > floor, "must not fall below the pattern");
        // Monotone in rho.
        let mid = m.averaged_green_luma_sigma(s, n, 0.5);
        assert!(decorrelated < mid && mid < correlated);
        // n = 1 is the single-frame sigma whatever rho says.
        for rho in [0.0f32, 0.5, 1.0] {
            assert!(
                (m.averaged_green_luma_sigma(s, 1, rho)
                    - m.green_luma_sigma_with_fixed_pattern(s))
                .abs()
                    < 1e-3
            );
        }
    }

    /// The measured per-plane pattern, asserted against the report a human can
    /// go and read rather than against itself (AGENTS rule 35).
    ///
    /// # The estimator mix, which looks like an inconsistency and is not
    ///
    /// M71 §8.1 tabulates R 0.3102%, green **0.3096%**, B 0.2528%, and says B is
    /// "0.823x green". 0.2528 / 0.3096 = 0.8165, not 0.823, which looks like an
    /// error in the report. It is not. Reading M71's primary output rather than
    /// its table (`experiments/M71-flat-fields/data/`) resolves it:
    ///
    /// - the green headline 0.3096% is the **matched-pair split-half** estimator
    ///   in `05-kappa.json`;
    /// - R and B come from `10-rb.json`, a different estimator whose own green is
    ///   **0.3072%** (G1 0.30525%, G2 0.30916%).
    ///
    /// B / green **within `10-rb`** is 0.82303, so M71's "0.823x" is a
    /// within-estimator ratio and is right. The two estimators disagree about
    /// green by 0.78%, which is well inside the +/-0.0159% spread M71 quotes
    /// (0.51% relative) doubled, and is the honest size of the systematic.
    ///
    /// The constants below are the tabulated ones, so a reader who looks up the
    /// report finds the numbers in the code. The consequence is that the R and B
    /// entries sit on a scale 0.78% below the green entry. Nothing load-bearing
    /// reads them — the focus field, the gate and `predicted_sigma` are all
    /// green-luma — so this is recorded, not corrected.
    #[test]
    fn the_measured_prnu_is_m71s_per_plane_table() {
        let k = Prnu::A7C2_MEASURED;
        assert_eq!(k.kappa(CfaPlane::G1), 0.003_096);
        assert_eq!(k.kappa(CfaPlane::G2), 0.003_096);
        assert_eq!(k.kappa(CfaPlane::R), 0.003_102);
        assert_eq!(k.kappa(CfaPlane::B), 0.002_528);

        // The two estimators, as read out of M71's primary JSON.
        let green_matched_pair = 0.003_096_227_f64; // 05-kappa.json, the headline
        let green_10rb = (0.003_052_479_9_f64 + 0.003_091_605_5) / 2.0; // 10-rb.json
        let b_10rb = 0.002_528_374_f64;
        assert!(
            ((b_10rb / green_10rb) - 0.823).abs() < 0.001,
            "within-estimator B/green = {}, M71 says 0.823",
            b_10rb / green_10rb
        );
        // The cross-estimator ratio the table invites, which is the 0.8165 that
        // looks wrong. Recorded so nobody re-derives the confusion.
        assert!(((0.002_528_f64 / 0.003_096) - 0.8165).abs() < 0.001);
        // The size of the disagreement between the two estimators on green.
        let mix = green_matched_pair / green_10rb - 1.0;
        assert!(
            (0.005..0.011).contains(&mix),
            "estimator disagreement on green is {mix}, was 0.78% when written"
        );
    }

    /// `read_floor_dn` is the product that was actually measured. It exists so
    /// that a gain correction can be checked against it.
    #[test]
    fn the_read_floor_is_the_product_and_not_either_factor() {
        let p = plane(0.229, 1.47);
        assert!((p.read_floor_dn() - 0.229 * 1.47).abs() < 1e-7);
        assert!((p.sigma(0.0) - p.read_floor_dn()).abs() < 1e-6);
        // Halving the gain while doubling the electrons leaves the floor alone.
        let q = plane(0.229 / 2.0, 1.47 * 2.0);
        assert!((q.read_floor_dn() - p.read_floor_dn()).abs() < 1e-6);
    }
}
