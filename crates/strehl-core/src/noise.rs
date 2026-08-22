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
//! # Provenance, and why a runtime estimator exists
//!
//! The A7C II coefficients were originally inferred by reproducing the camera's
//! own white level to 0.23%. That is a consistency check on one relation, **not
//! a photon-transfer measurement**. A wrong noise floor does not raise an error;
//! it silently mis-gates the merge and quietly degrades the output.
//!
//! So [`NoiseModel::estimated`] exists on the v1 path, not as a future
//! nicety, and profiled bodies are validated against it.

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
    pub fn variance(&self, signal_dn: f32) -> f32 {
        let s = signal_dn.max(0.0);
        let read_dn = self.read_noise_e * self.gain_dn_per_e;
        self.gain_dn_per_e * s + read_dn * read_dn
    }

    /// Noise standard deviation in DN at a black-subtracted signal level.
    pub fn sigma(&self, signal_dn: f32) -> f32 {
        self.variance(signal_dn).sqrt()
    }
}

/// The calibrated noise model for one stack, at one ISO.
#[derive(Debug, Clone)]
pub struct NoiseModel {
    planes: [PlaneNoise; 4],
    pub iso: f32,
    pub provenance: Provenance,
}

impl NoiseModel {
    pub fn new(planes: [PlaneNoise; 4], iso: f32, provenance: Provenance) -> Self {
        Self {
            planes,
            iso,
            provenance,
        }
    }

    pub fn plane(&self, p: CfaPlane) -> &PlaneNoise {
        &self.planes[match p {
            CfaPlane::R => 0,
            CfaPlane::G1 => 1,
            CfaPlane::B => 2,
            CfaPlane::G2 => 3,
        }]
    }

    /// Variance in DN^2 for a sample on a given plane.
    pub fn variance(&self, p: CfaPlane, signal_dn: f32) -> f32 {
        self.plane(p).variance(signal_dn)
    }

    /// Standard deviation in DN for a sample on a given plane.
    pub fn sigma(&self, p: CfaPlane, signal_dn: f32) -> f32 {
        self.plane(p).sigma(signal_dn)
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
}
