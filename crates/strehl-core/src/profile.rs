//! Camera sensor profiles — the *only* place a per-body constant may appear.
//!
//! SYNTHESIS §4.1 ruled that of everything the research corpus called a
//! constant, only the sensor calibration is genuinely per-body-model; the rest
//! are per-stack artifacts that must be fitted at runtime. It also ruled that
//! even the sensor calibration must live in a **camera-profile data file, never
//! in pipeline code**.
//!
//! This module is the stopgap: a compiled-in table, so the constants are at
//! least in one named place that no pipeline stage may reach around. Moving it
//! to a data file is owed before v1 and is deliberately cheap from here —
//! [`by_model`] is the only entry point.
//!
//! Black and white levels are **not** here. Those come from the file, per frame,
//! because they are firmware and compression dependent.

use crate::noise::{Levels, NoiseModel, PlaneNoise, Provenance};

/// Sensor calibration for one camera model.
pub struct CameraProfile {
    /// `clean_model` as the decoder reports it.
    pub model: &'static str,
    /// Gain is `iso / gain_divisor` DN per electron.
    ///
    /// **DERIVED, not measured.** The divisor was obtained by reproducing the
    /// camera's own white level to 0.23% — a consistency check on one relation,
    /// not a photon-transfer curve. SYNTHESIS §10 open question 5 owes a real
    /// PTC measurement, which needs the dark frames listed in
    /// `docs/captures-needed.md`.
    pub gain_divisor: f32,
    /// Read noise in electrons below [`Self::second_base_iso`].
    pub read_noise_e_low: f32,
    /// Read noise in electrons at and above it.
    pub read_noise_e_high: f32,
    /// The dual-gain switch point. Above it read noise *drops*, so this is not
    /// a monotone-in-ISO model. Per body and per firmware.
    pub second_base_iso: f32,
}

impl CameraProfile {
    pub fn read_noise_e(&self, iso: f32) -> f32 {
        if iso >= self.second_base_iso {
            self.read_noise_e_high
        } else {
            self.read_noise_e_low
        }
    }

    pub fn gain_dn_per_e(&self, iso: f32) -> f32 {
        iso / self.gain_divisor
    }

    /// Build the injected noise model for one stack.
    ///
    /// Both greens get the same coefficients here. They are modelled separately
    /// by construction (`PlaneNoise` is per plane) but nothing has yet measured
    /// them apart, and inventing a difference would be worse than admitting
    /// there is none.
    pub fn noise_model(&self, iso: f32, levels: Levels) -> NoiseModel {
        let p = PlaneNoise {
            gain_dn_per_e: self.gain_dn_per_e(iso),
            read_noise_e: self.read_noise_e(iso),
            levels,
        };
        NoiseModel::new([p; 4], iso, Provenance::Profile)
    }
}

/// Sony A7C II. Constants confirmed against M1 where M1 could confirm them:
/// white level 15360 and black level 512 came back from the decoder, and the
/// ISO 400 second base and the gain relation came from report F.
const A7C2: CameraProfile = CameraProfile {
    model: "ILCE-7CM2",
    gain_divisor: 436.8,
    read_noise_e_low: 4.20,
    read_noise_e_high: 1.47,
    second_base_iso: 400.0,
};

const PROFILES: [&CameraProfile; 1] = [&A7C2];

pub fn by_model(model: &str) -> Option<&'static CameraProfile> {
    PROFILES.iter().copied().find(|p| p.model == model)
}

/// The noise model to use when the body is unprofiled, or when the file did not
/// report an ISO.
///
/// Unity gain and a 4 e- read noise are a **guess**. The returned model is
/// stamped [`Provenance::Fallback`] so that every consumer can see it, and so
/// that a run made against it is visibly untrustworthy rather than silently
/// wrong. SYNTHESIS §3.3 puts a real runtime estimator on the v1 path for
/// exactly this case; it is not built yet.
pub fn fallback(iso: f32, levels: Levels) -> NoiseModel {
    let p = PlaneNoise {
        gain_dn_per_e: 1.0,
        read_noise_e: 4.0,
        levels,
    };
    NoiseModel::new([p; 4], iso, Provenance::Fallback)
}

/// Resolve a noise model for a stack, falling back visibly rather than
/// pretending.
pub fn noise_model_for(model: &str, iso: Option<f32>, levels: Levels) -> NoiseModel {
    match (by_model(model), iso) {
        (Some(profile), Some(iso)) => profile.noise_model(iso, levels),
        (_, iso) => fallback(iso.unwrap_or(0.0), levels),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::CfaPlane;

    fn levels() -> Levels {
        Levels {
            black: 512.0,
            white: 15360.0,
        }
    }

    #[test]
    fn the_reference_body_resolves_to_a_profile() {
        let m = noise_model_for("ILCE-7CM2", Some(100.0), levels());
        assert_eq!(m.provenance, Provenance::Profile);
        assert!(m.is_trustworthy());
    }

    #[test]
    fn an_unknown_body_falls_back_visibly() {
        let m = noise_model_for("NOT-A-CAMERA", Some(100.0), levels());
        assert_eq!(m.provenance, Provenance::Fallback);
        assert!(!m.is_trustworthy());
    }

    #[test]
    fn a_missing_iso_falls_back_rather_than_assuming_base_iso() {
        // Silently assuming ISO 100 would give a plausible-looking but wrong
        // noise floor, and nothing downstream could tell.
        let m = noise_model_for("ILCE-7CM2", None, levels());
        assert_eq!(m.provenance, Provenance::Fallback);
    }

    #[test]
    fn the_second_base_iso_lowers_read_noise() {
        // Fact #14: 4.20 e- -> 1.47 e- at ISO 400. Noise vs ISO is not monotone.
        let p = by_model("ILCE-7CM2").unwrap();
        assert_eq!(p.read_noise_e(320.0), 4.20);
        assert_eq!(p.read_noise_e(400.0), 1.47);
        let floor_320 = p.noise_model(320.0, levels()).sigma(CfaPlane::R, 0.0);
        let floor_400 = p.noise_model(400.0, levels()).sigma(CfaPlane::R, 0.0);
        assert!(floor_400 < floor_320, "{floor_400} vs {floor_320}");
    }

    #[test]
    fn gain_follows_the_iso_relation() {
        let p = by_model("ILCE-7CM2").unwrap();
        assert!((p.gain_dn_per_e(100.0) - 100.0 / 436.8).abs() < 1e-6);
        assert!((p.gain_dn_per_e(800.0) - 8.0 * p.gain_dn_per_e(100.0)).abs() < 1e-6);
    }
}
