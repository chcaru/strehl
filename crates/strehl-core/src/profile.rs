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
//!
//! # Which statistic these constants are — discipline 291
//!
//! **Every noise constant in this file is a pooled RMS temporal sigma:**
//! `sqrt(mean over pixels of the per-pixel temporal variance)`, over **20** dark
//! frames at one ISO, with the owner's **first two stabilisation frames per
//! directory dropped**, on the raw integer DN with no black subtraction.
//!
//! M4 §8.1's table is that statistic. It has been reproduced through an
//! independent decoder (`rawpy`, not `strehl-raw`) at all **44** published cells
//! — every plane at every ISO — at ratios **0.99986–0.99998**. What M4 never
//! said is *which* statistic it is, and three constants were then fitted to it
//! as though it described a typical pixel. It does not: on the same frames the
//! **mean** pixel reads 5.9% below the pooled RMS at ISO 50 and **14.6%** below
//! at ISO 1600, and the **median** pixel 9.8% and **24.1%** below.
//!
//! **The pooled RMS is the right choice, and that is measured rather than
//! preferred.**
//!
//! - *The consumer averages, and the gate is calibrated on the fluctuation.*
//!   [`FocusField::compute`](crate::focus::FocusField::compute) divides a 27x27
//!   windowed gradient mean by this model's sigma; the merge regulariser
//!   averages that again over 17x17; [`Gate`](crate::merge::Gate) then compares
//!   response *differences* against the single scalar
//!   `sqrt(2) * `[`FOCUS_NOISE_SD`](crate::merge::FOCUS_NOISE_SD). The
//!   fluctuation of a spatial mean over pixels with unequal variances is set by
//!   the **mean variance** — the pooled RMS squared — not by the mean sigma.
//!   Normalising by the mean pixel would leave the real response **6.3% noisier
//!   at ISO 50 and 17.1% noisier at ISO 1600** than that constant assumes, so
//!   the gate would be that much too tight, and worse the higher the ISO.
//! - *The typical-pixel basis cannot be delivered anyway.* The argument for it
//!   is that hot pixels are a separate concern with their own map (M22) and
//!   their own milestone (M29). Measured: the whole of M22's recurrent map —
//!   11,393 px, **0.0346%** of the sensor — carries only 2.2%–3.6% of the
//!   temporal variance, and an *oracle* excision of all of it moves the pooled
//!   RMS by **1.1%–1.8%**, roughly a tenth of the gap. Meeting the mean pixel
//!   takes **0.64%–1.23% of every plane**, which is 18x–36x the map and is not
//!   a defect set at all. There is nothing to hand off.
//!
//! **What is genuinely wrong is the shape, and re-basing would not have fixed
//! it.** Per-pixel temporal sigma has a coefficient of variation of **0.32** at
//! ISO 100 rising to **0.58** at ISO 1600 (DERIVED from the mean/RMS ratio); the
//! 99th-percentile pixel sits at **2.5x** the median at ISO 100 and **4.3x** at
//! ISO 1600 (MEASURED). No scalar on any basis represents that. The honest
//! object is a per-pixel sigma *field*, and the 242 delivered darks are already
//! enough to build one. **Scoped, not built** — see
//! `docs/research/M48-read-noise-measured.md`.

use crate::noise::{Levels, NoiseModel, PlaneNoise, Prnu, Provenance};

/// Which **measured** corrections to apply when building a [`NoiseModel`].
///
/// Every field defaults to `false`, and [`Corrections::SHIPPED`] is the default
/// path: `Corrections::default() == Corrections::SHIPPED`, and building with it
/// produces a model that is **bit-identical** to
/// [`CameraProfile::noise_model`]. That identity is the point — it is what makes
/// this reversible, and `the_shipped_corrections_are_bit_identical_to_the_default_path`
/// asserts it across the whole container range at every ISO.
///
/// See `docs/research/M90-prnu-noise-model.md` for what flipping each flag
/// costs, measured, and `docs/research/M71-flat-fields.md` for where the
/// constants come from.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Corrections {
    /// Use M71's photon-transfer gain instead of the profile's `gain_divisor`.
    ///
    /// **`read_noise_e` is rescaled inversely so that `RN_e * g` — the product
    /// that was actually measured — is preserved.** See
    /// [`CameraProfile::measured_gain_divisor`].
    pub measured_gain: bool,
    /// Attach M71's measured per-plane PRNU.
    ///
    /// Attaching it changes nothing by itself; only the `*_with_fixed_pattern`
    /// entry points read it. See [`Prnu`].
    pub prnu: bool,
}

impl Corrections {
    /// The default path. Nothing applied.
    pub const SHIPPED: Corrections = Corrections {
        measured_gain: false,
        prnu: false,
    };
    /// Gain only — the arm that is **worse than shipped** over most of the
    /// range, because it removes the error that was cancelling the missing PRNU
    /// term. Kept as a named constant precisely so that it is measurable rather
    /// than assumed.
    pub const GAIN_ONLY: Corrections = Corrections {
        measured_gain: true,
        prnu: false,
    };
    /// PRNU only.
    pub const PRNU_ONLY: Corrections = Corrections {
        measured_gain: false,
        prnu: true,
    };
    /// Both — the model M71's measurements imply.
    pub const BOTH: Corrections = Corrections {
        measured_gain: true,
        prnu: true,
    };
}

/// Sensor calibration for one camera model.
pub struct CameraProfile {
    /// `clean_model` as the decoder reports it.
    pub model: &'static str,
    /// Gain is `max(iso, base_iso) / gain_divisor` DN per electron.
    ///
    /// **MEASURED at ISO 160, by photon transfer on signal** (M25 fact 200,
    /// SYNTHESIS fact 550): 0.3273 against the relation's 0.3663, 10.7% low.
    /// The divisor was originally DERIVED by reproducing the camera's own white
    /// level to 0.23%, which is a consistency check on one relation and not a
    /// PTC; the PTC now exists and the relation survives it at true gain steps.
    /// **SYNTHESIS fact 585 adjudicates this constant by name**: it is not a
    /// fourth wrong sensor constant, and the −10.7% is licensed to stand.
    ///
    /// **The relation is calibrated in the LOW gain mode only, and M48c measures
    /// that it does not carry across [`second_base_iso`](Self::second_base_iso).**
    /// The PTC above was taken at ISO 160; every ISO ≥ 400 is extrapolation.
    /// M48c took the 13,630 recurrent hot pixels from the 242 darks — a
    /// dark-current signal, which is generated at the photodiode *before* the
    /// analogue gain and therefore cannot depend on the ISO dial — and measured
    /// their excess at all 11 ISOs. Within each mode the excess is *purely*
    /// proportional to this relation's `g` (additive term −0.055 DN high,
    /// −0.125 DN low, both consistent with zero; residuals ≤ 4.8%), but the
    /// constant of proportionality **steps by 2.17× exactly at ISO 400**:
    /// 6.69 e⁻ below, 3.08 e⁻ above, for the same pixels.
    ///
    /// Exposure and temperature are excluded as causes: all 11 groups are
    /// 1/100 s to the EXIF, and they were shot interleaved inside 3.5 minutes
    /// (ISO 400/800/1600 *before* ISO 50/200/250), so no monotone thermal drift
    /// can produce a step that sorts by gain mode while scrambled in time.
    ///
    /// **Consequence, and it is a labelling failure rather than an arithmetic
    /// one.** [`read_noise_e_high`](Self::read_noise_e_high) was fitted to dark
    /// σ_DN *through this same `g`*, so the product `RN_e × g` reproduces the
    /// measured DN and **every DN-domain prediction of this model is unaffected**.
    /// What is not identified above ISO 400 is the *split*: `gain_divisor` and
    /// `read_noise_e_high` are degenerate there, and only their product is
    /// measured. Read in electrons, the high-mode read noise is ~2.7 e⁻ rather
    /// than 1.2392, and the dual-gain improvement is ~1.6× rather than ~3.4×.
    ///
    /// This is **not** fixed here, because fixing it means making gain
    /// mode-dependent — a model *shape* change — on the strength of one
    /// measurement, made on darks. The measurement it needs is a PTC at ISO 500
    /// or 1000, which the corpus can support (261 of 421 frames are at those two
    /// settings) and which nothing has yet run. Until then the degeneracy is
    /// documented rather than silently split, and
    /// `the_gain_relation_is_still_continuous_across_the_dual_gain_switch`
    /// is the tripwire that fails the day someone changes it.
    pub gain_divisor: f32,
    /// The lowest ISO that is a real analogue gain step.
    ///
    /// Settings below this are **extended / pull** ISOs: the sensor reads out at
    /// `base_iso` gain and the stop is taken in exposure. Dividing by the marked
    /// ISO there under-states `g`, and since `sigma^2 = g*S + (RN_e*g)^2` is
    /// linear in `g`, it under-states the whole noise floor.
    ///
    /// **MEASURED twice, independently.** M4 §8.2 from dark frames: ISO 50 and
    /// ISO 100 give the same dark sigma in DN, 0.9866 against 0.9845, a ratio of
    /// 1.0021 where a genuine gain step demands 0.5. M25 fact 200 (SYNTHESIS
    /// fact 550) from signal, by photon transfer on two real ISO-50 stacks: `g`
    /// measures 0.2342 and 0.2583, which is +105% and +126% against the
    /// marked-ISO relation and within +2% and +13% of this floor.
    ///
    /// **The boundary itself is not measured** (M25 fact 200a, which folded as
    /// SYNTHESIS *question* 126 — it is an open question, not a fact): the
    /// corpus holds no ISO 64 or ISO 80 capture, so 100 is the simplest value
    /// consistent with the evidence rather than a located transition.
    pub base_iso: f32,
    /// Read noise in electrons below [`Self::second_base_iso`].
    ///
    /// **DELIBERATELY NOT RE-FITTED. The reason is a fact about the model, and
    /// it is asserted as one.**
    ///
    /// A dark frame has `S = 0`, so `RN_e = sigma_DN / g` directly. On the
    /// pooled-RMS basis and this profile's [`base_iso`](Self::base_iso) gain the
    /// four low-mode ISOs imply **4.3091 / 4.3000 / 3.8034 / 3.7787 e-** at ISO
    /// 50 / 100 / 200 / 250. That is not scatter about a constant: the implied
    /// read noise *falls monotonically*, by 12% between ISO 100 and ISO 250.
    /// **This is a shape error and no scalar can fix it.** The best single value
    /// under relative least squares, 4.0153, still misses by −6.8% / −6.6% /
    /// +5.6% / +6.3%.
    ///
    /// 4.20 reads **−2.5% / −2.3% / +10.4% / +11.1%**. It is the *more* accurate
    /// choice at ISO 50 and 100, which is where the captures this constant
    /// governs actually sit. M25 fact 200's table (SYNTHESIS fact 550) names
    /// three stacks at ISO 50 and ISO 160, but that is the `C:\dev\macro\test`
    /// subset and not the corpus. The measured census is **160 of 421 frames
    /// below ISO 400, every one of them at ISO 50 or 160**; the other 261 sit at
    /// ISO 500 and 1000, where [`read_noise_e_high`](Self::read_noise_e_high)
    /// rules instead. **No capture anywhere uses ISO 200 or 250.** So moving to
    /// 4.0153 would buy a smaller worst case at two ISOs nothing shoots, pay for
    /// it with 4.3% of accuracy at every ISO this constant does govern, and
    /// leave the shape error untouched.
    ///
    /// The tolerated disagreement is asserted at its expected wrong value in
    /// `the_model_is_checked_against_measured_dark_sigma_at_every_iso`, per
    /// rule 30 — so it goes red the day the model shape improves, which is the
    /// day anyone would want to hear about it.
    pub read_noise_e_low: f32,
    /// Read noise in electrons at and above it.
    ///
    /// **DERIVED from the independently verified dark table**, on the pooled-RMS
    /// basis named in this module's header. With `S = 0` the seven high-mode
    /// ISOs imply **1.3088 / 1.2823 / 1.2338 / 1.2265 / 1.2267 / 1.2026 /
    /// 1.2083 e-** at ISO 400 / 500 / 640 / 800 / 1000 / 1600 / 2000. This value
    /// is the single `RN_e` minimising the **relative** residual over those
    /// seven, `argmin sum (RN/RN_i − 1)^2` — relative because sigma spans 4.6x
    /// across the mode and an absolute fit would be decided by ISO 2000 alone.
    /// Residuals here: −5.3% / −3.4% / +0.4% / +1.0% / +1.0% / +3.0% / +2.6%.
    ///
    /// **Only the first two digits are physical.** The rest are carried so the
    /// fit is reproducible, and
    /// `the_high_mode_read_noise_is_the_relative_least_squares_optimum` asserts
    /// the derivation, not just the number.
    ///
    /// **The previous value, 1.47, was wrong on every basis:** +18.4% against
    /// this one, +36.5% against the mean pixel, +51.9% against the median. The
    /// shipped model over-predicted measured dark sigma by **12.3% at ISO 400
    /// rising to 22.2% at ISO 1600**. M4 §8.3 saw it — "fact 14's 4.20 → 1.47
    /// e- measures as 4.30 → 1.31 e-: 2.4% off on the low-gain side, 11% off on
    /// the high side" — and the correction never reached the code. That is the
    /// same failure mode as the ISO-50 gain defect (fact 550): measured in a
    /// research document, never carried across to the constant it invalidated.
    pub read_noise_e_high: f32,
    /// The dual-gain switch point. Above it read noise *drops*, so this is not
    /// a monotone-in-ISO model. Per body and per firmware.
    pub second_base_iso: f32,
    /// The gain divisor M71's photon transfer measured, when one exists.
    ///
    /// **MEASURED, M71 §6.1 (SYNTHESIS fact 1065).** Green gain
    /// **0.224103 DN/e-** at ISO 100 by a between-group PTC over 484 flat
    /// fields, replicated drift-immune within-frame at
    /// **0.223864 +/- 0.000836** (ratio 0.99893) by an estimator that fails
    /// differently, and corroborated by fact 29's spectral floor to 3.0%. That
    /// is **-2.16%** against [`gain_divisor`](Self::gain_divisor)'s implied
    /// 0.228938, and `100 / 0.224103 = 446.2233`.
    ///
    /// **The per-plane values are deliberately not carried here.** M71 measured
    /// R at -3.50% and **B at -14.85%**, and B's deficit is the still-unruled
    /// B-plane anomaly that M48c, M61, M68, M71 and M72 have all chased. Baking
    /// an unruled anomaly into a constant labelled "corrected" would be the
    /// worse error; the greens are what every load-bearing consumer of this
    /// model actually reads, since the focus field, the gate and
    /// `predicted_sigma` are all green-luma.
    ///
    /// **Applying this alone makes the model worse**, and that is measured, not
    /// argued: it removes the error that was cancelling the absent PRNU term.
    /// See `docs/research/M90-prnu-noise-model.md` §2.
    pub measured_gain_divisor: Option<f32>,
    /// The PRNU M71 measured on this body, when one exists.
    pub measured_prnu: Option<Prnu>,
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
        iso.max(self.base_iso) / self.gain_divisor
    }

    /// [`Self::gain_dn_per_e`] under a correction set.
    ///
    /// With [`Corrections::SHIPPED`] this is `gain_dn_per_e` evaluated by the
    /// same expression, in the same order, so it returns the identical `f32`.
    pub fn gain_dn_per_e_with(&self, iso: f32, c: Corrections) -> f32 {
        match (c.measured_gain, self.measured_gain_divisor) {
            (true, Some(d)) => iso.max(self.base_iso) / d,
            _ => iso.max(self.base_iso) / self.gain_divisor,
        }
    }

    /// True when this profile can honour every flag in `c`.
    ///
    /// A correction requested but not available for this body is **not** an
    /// error and **not** silently applied: the model is built without it and
    /// this reports so, because a caller measuring a correction's effect needs
    /// to know whether it was applied at all.
    pub fn supports(&self, c: Corrections) -> bool {
        (!c.measured_gain || self.measured_gain_divisor.is_some())
            && (!c.prnu || self.measured_prnu.is_some())
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

    /// [`Self::noise_model`] under a correction set.
    ///
    /// # The trap this function exists to avoid
    ///
    /// `read_noise_e` is **not** an independent measurement. `profile.rs`'s own
    /// header records that it was fitted to measured dark sigma **in DN**
    /// through this profile's gain, so the identified quantity is the product
    /// `RN_e * g`, not either factor — and above [`second_base_iso`] the two are
    /// explicitly documented as degenerate. Scaling `g` down by 2.16% while
    /// leaving `RN_e` alone therefore drops the predicted **dark** sigma 2.16%
    /// below the 44 independently reproduced cells of M4's table, replacing a
    /// known error at high signal with a new one at low signal.
    ///
    /// So the gain correction here scales `read_noise_e` by the inverse ratio
    /// and the read floor in DN is preserved exactly.
    /// `the_measured_gain_correction_preserves_the_dark_floor` asserts it, and
    /// it is asserted **at zero signal**, where it is the only term.
    pub fn noise_model_with(&self, iso: f32, levels: Levels, c: Corrections) -> NoiseModel {
        if c == Corrections::SHIPPED {
            return self.noise_model(iso, levels);
        }
        let gain = self.gain_dn_per_e_with(iso, c);
        let shipped_gain = self.gain_dn_per_e(iso);
        // Preserve RN_e * g, the product that was measured.
        let read_noise_e = if gain > 0.0 {
            self.read_noise_e(iso) * (shipped_gain / gain)
        } else {
            self.read_noise_e(iso)
        };
        let p = PlaneNoise {
            gain_dn_per_e: gain,
            read_noise_e,
            levels,
        };
        let m = NoiseModel::new([p; 4], iso, Provenance::Profile);
        match (c.prnu, self.measured_prnu) {
            (true, Some(k)) => m.with_prnu(k),
            _ => m,
        }
    }
}

/// Sony A7C II. Constants confirmed against M1 where M1 could confirm them:
/// white level 15360 and black level 512 came back from the decoder, and the
/// ISO 400 second base and the gain relation came from report F.
const A7C2: CameraProfile = CameraProfile {
    model: "ILCE-7CM2",
    gain_divisor: 436.8,
    base_iso: 100.0,
    read_noise_e_low: 4.20,
    read_noise_e_high: 1.2392,
    second_base_iso: 400.0,
    measured_gain_divisor: Some(A7C2_MEASURED_GAIN_DIVISOR),
    measured_prnu: Some(Prnu::A7C2_MEASURED),
};

/// `100 / 0.224103`, from M71 §6.1's between-group green photon transfer.
///
/// Written as the quotient of the two numbers a reader can look up rather than
/// as a bare 446.2233, so the derivation is in the source and the constant
/// cannot drift away from the measurement it encodes.
pub const A7C2_MEASURED_GREEN_GAIN_DN_PER_E: f32 = 0.224_103;
/// The divisor implied by [`A7C2_MEASURED_GREEN_GAIN_DN_PER_E`] at ISO 100.
pub const A7C2_MEASURED_GAIN_DIVISOR: f32 = 100.0 / A7C2_MEASURED_GREEN_GAIN_DN_PER_E;

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

/// [`noise_model_for`] under a correction set.
///
/// The fallback arm is **deliberately never corrected**. Its gain is a guess of
/// 1.0, so M71's -2.16% and its 0.3096% pattern — both measured on one specific
/// A7C II sensor — mean nothing against it, and applying them would dress a
/// guess up as a measurement. `Provenance::Fallback` keeps saying so.
pub fn noise_model_for_with(
    model: &str,
    iso: Option<f32>,
    levels: Levels,
    c: Corrections,
) -> NoiseModel {
    match (by_model(model), iso) {
        (Some(profile), Some(iso)) => profile.noise_model_with(iso, levels, c),
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
        // Fact #14's mechanism, at M48's re-derived value: 4.20 e- -> 1.2392 e-
        // at ISO 400. Noise vs ISO is not monotone. Fact 14's own 1.47 was
        // +18.4% against the measurement it was supposed to summarise.
        let p = by_model("ILCE-7CM2").unwrap();
        assert_eq!(p.read_noise_e(320.0), 4.20);
        assert_eq!(p.read_noise_e(400.0), 1.2392);
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

    /// Extended ISOs are not gain steps, and the dark frames say so.
    ///
    /// M4 §8.2 measured sigma_temporal at **0.9866 DN at ISO 50** against
    /// **0.9845 DN at ISO 100** — a ratio of **1.0021**. The marked-ISO relation
    /// predicts 0.5. This test holds the model to the measurement rather than to
    /// the relation, because the relation is what was wrong.
    #[test]
    fn extended_iso_reads_out_at_base_gain() {
        let p = by_model("ILCE-7CM2").unwrap();
        assert_eq!(p.gain_dn_per_e(50.0), p.gain_dn_per_e(100.0));

        // Dark: S = 0, so sigma = RN_e * g and the ratio is the gain ratio.
        let s50 = p.noise_model(50.0, levels()).sigma(CfaPlane::R, 0.0);
        let s100 = p.noise_model(100.0, levels()).sigma(CfaPlane::R, 0.0);
        let measured = 0.9866 / 0.9845;
        assert!(
            ((s50 / s100) - measured).abs() < 0.01,
            "M4 measured {measured}, model gives {}",
            s50 / s100
        );

        // The defect this replaced, stated so it cannot come back silently.
        let marked_iso_relation = 50.0 / 436.8;
        assert!(
            (p.gain_dn_per_e(50.0) / marked_iso_relation - 2.0).abs() < 1e-4,
            "the floor must be worth exactly the 2.05x M25 measured"
        );
    }

    /// A true gain step below base ISO would break the floor, so no profile may
    /// declare one it does not honour.
    #[test]
    fn every_profile_bases_its_gain_at_or_below_its_second_base() {
        for p in PROFILES {
            assert!(
                p.base_iso <= p.second_base_iso,
                "{}: base {} above second base {}",
                p.model,
                p.base_iso,
                p.second_base_iso
            );
            assert!(p.base_iso > 0.0, "{}: base ISO must be positive", p.model);
        }
    }

    /// The measured dark table this profile's constants are fitted to.
    ///
    /// `(ISO, sigma_DN, expected model/measured)`. `sigma_DN` is the **pooled
    /// RMS temporal sigma** over 20 dark frames, stabilisation shots dropped,
    /// averaged over the four CFA planes — the statistic named in this module's
    /// header. Source: M4 §8.1, independently reproduced through `rawpy` at
    /// ratios 0.99986–0.99998 in `experiments/m48-noise-floor`
    /// (`data/estimator-reconciliation.json`, `data/variance-concentration.json`).
    ///
    /// The model is plane-independent by construction, so comparing it against
    /// the 4-plane mean is like for like at the level the model is defined.
    const DARK_SIGMA_RMS_DN: [(f32, f32, f32); 11] = [
        // Low mode. ISO 50 is the only one of these the corpus actually shoots
        // — its other low-mode stack is ISO 160, which this dark set has no row
        // for — and the model is 2.3–2.5% low at both, the best a scalar
        // `read_noise_e_low` does here.
        (50.0, 0.986524, 0.97467),
        (100.0, 0.98444, 0.97674),
        // Still low mode, and KNOWINGLY WRONG. The implied read noise falls 12%
        // from ISO 100 to ISO 250, so one scalar cannot serve both ends of the
        // mode. Asserted at the wrong value rather than carved out (rule 30):
        // SYNTHESIS question 129's additive DN floor is what would fix it, and
        // when it lands these two rows must change.
        (200.0, 1.741494, 1.10427),
        (250.0, 2.162736, 1.11148),
        // High mode, at M48's re-derived 1.2392. The residual is the same shape
        // error one mode up — the ends of the mode disagree by 8.8% — but it is
        // now centred instead of sitting entirely on one side, which is the
        // whole of what re-fitting a scalar can buy.
        (400.0, 1.198538, 0.94682),
        (500.0, 1.46783, 0.96639),
        (640.0, 1.807805, 1.00435),
        (800.0, 2.246382, 1.01033),
        (1000.0, 2.808366, 1.01019),
        (1600.0, 4.405162, 1.03043),
        (2000.0, 5.532721, 1.02553),
    ];

    /// Every measured ISO, asserted. No carve-outs — rule 30 and discipline 288.
    ///
    /// M25's dark-noise self-test excluded ISO 50 *because the model was known to
    /// be wrong there*, which silenced the one assertion that would have caught a
    /// 2x gain defect. So this test covers **all eleven** ISOs in the corpus and
    /// carries the known disagreements as expected values rather than as gaps.
    ///
    /// **What would make it fail:** any change to `read_noise_e_*`,
    /// `gain_divisor`, `base_iso`, `second_base_iso` or the variance relation —
    /// including an *improvement*, which is the point. The tolerance is 0.1%,
    /// tight enough that a 0.3% move in either read-noise constant trips it.
    #[test]
    fn the_model_is_checked_against_measured_dark_sigma_at_every_iso() {
        let p = by_model("ILCE-7CM2").unwrap();
        let mut checked = 0;
        for (iso, measured_dn, expected_ratio) in DARK_SIGMA_RMS_DN {
            // A dark frame is S = 0, so sigma reduces to RN_e * g.
            let model_dn = p.noise_model(iso, levels()).sigma(CfaPlane::R, 0.0);
            let ratio = model_dn / measured_dn;
            assert!(
                (ratio / expected_ratio - 1.0).abs() < 1e-3,
                "ISO {iso}: model {model_dn} DN / measured {measured_dn} DN = \
                 {ratio}, expected {expected_ratio} ({:+.2}% vs {:+.2}%)",
                100.0 * (ratio - 1.0),
                100.0 * (expected_ratio - 1.0)
            );
            checked += 1;
        }
        // Rule 36: prove the loop ran. An empty or truncated table would
        // otherwise pass this test in silence, which is how a no-carve-outs
        // test quietly becomes a carve-out.
        assert_eq!(checked, 11, "every measured ISO must be checked");
        assert!(
            DARK_SIGMA_RMS_DN.iter().any(|(iso, _, _)| *iso < 400.0)
                && DARK_SIGMA_RMS_DN.iter().any(|(iso, _, _)| *iso >= 400.0),
            "both gain modes must be represented"
        );
    }

    /// The `base_iso` fix, confirmed from a route that did not exist when it was
    /// made — and cheap enough to keep forever.
    ///
    /// ISO 50 is an extended/pull setting, so it reads out at ISO 100's gain and
    /// the two must imply the *same* electron read noise. Under this profile's
    /// gain they do, to **0.21%**. Under the marked-ISO relation M4 §8.3 used,
    /// ISO 50 implied 8.6183 e- against ISO 100's 4.3000 — M4 published exactly
    /// that and called it "visibly nonsense … the tell".
    ///
    /// **What would make it fail:** removing `base_iso`, or moving it above 50
    /// or below 100. The second assertion is the placebo — it shows the first
    /// one is testing the floor and not an identity, because the same data under
    /// the un-floored gain disagrees by 100%.
    #[test]
    fn the_iso_50_and_iso_100_darks_imply_the_same_read_noise() {
        let p = by_model("ILCE-7CM2").unwrap();
        // Read from the one table, so the two tests cannot drift apart.
        let (s50, s100) = (DARK_SIGMA_RMS_DN[0].1, DARK_SIGMA_RMS_DN[1].1);
        assert_eq!(
            (DARK_SIGMA_RMS_DN[0].0, DARK_SIGMA_RMS_DN[1].0),
            (50.0, 100.0)
        );

        let implied = |iso: f32, sigma: f32| sigma / p.gain_dn_per_e(iso);
        let ratio = implied(50.0, s50) / implied(100.0, s100);
        assert!(
            (ratio - 1.0).abs() < 0.01,
            "ISO 50 implies {} e-, ISO 100 implies {} e-, ratio {ratio}",
            implied(50.0, s50),
            implied(100.0, s100)
        );

        // Placebo: the relation this replaced, on the same two measurements.
        let marked = s50 / (50.0 / p.gain_divisor);
        let marked_ratio = marked / implied(100.0, s100);
        assert!(
            marked_ratio > 1.9,
            "the marked-ISO relation must still be visibly broken here, got \
             {marked_ratio}; if it is not, this test has no power"
        );
    }

    /// The *derivation* of `read_noise_e_high`, not just its value.
    ///
    /// §5 discipline 3: every headline number needs a regression test on its own
    /// code path. The shipped constant is `argmin_RN sum (RN/RN_i − 1)^2` over
    /// the seven high-mode ISOs, and this recovers that argmin by brute force
    /// from the measured table, independently of the closed form used to compute
    /// it. It also pins the residual spread, which is what says how many digits
    /// of the constant mean anything.
    ///
    /// **What would make it fail:** shipping a rounded value, shipping the
    /// *unweighted mean* of the per-ISO values (1.2413, which is 0.17% away and
    /// outside the grid tolerance), or re-basing onto the mean pixel (1.0731) or
    /// the median pixel (0.9679) without saying so.
    #[test]
    fn the_high_mode_read_noise_is_the_relative_least_squares_optimum() {
        let p = by_model("ILCE-7CM2").unwrap();
        let implied: Vec<f64> = DARK_SIGMA_RMS_DN
            .iter()
            .filter(|(iso, _, _)| *iso >= 400.0)
            .map(|(iso, sigma, _)| *sigma as f64 / (*iso as f64 / p.gain_divisor as f64))
            .collect();
        assert_eq!(implied.len(), 7);

        let objective =
            |rn: f64| -> f64 { implied.iter().map(|r| (rn / r - 1.0).powi(2)).sum::<f64>() };

        let step = 2e-4;
        let mut best = (f64::INFINITY, 0.0);
        for k in 0..=2500 {
            let rn = 1.0 + step * k as f64;
            let o = objective(rn);
            if o < best.0 {
                best = (o, rn);
            }
        }
        assert!(
            (best.1 - p.read_noise_e_high as f64).abs() <= step,
            "grid argmin {} vs shipped {}",
            best.1,
            p.read_noise_e_high
        );

        // The spread that limits how many digits are meaningful.
        let worst = implied
            .iter()
            .map(|r| (p.read_noise_e_high as f64 / r - 1.0).abs())
            .fold(0.0f64, f64::max);
        assert!(
            (0.050..0.056).contains(&worst),
            "worst relative residual in the high mode is {worst}, expected ~5.3%"
        );
    }

    /// The gain relation runs continuously through the dual-gain switch, and
    /// M48c measured that it should not. This test asserts the **known-wrong**
    /// present behaviour, rule-30 style, so that it goes red the day the model
    /// is improved rather than letting the improvement land unremarked.
    ///
    /// M48c's measurement, on the 13,630 recurrent hot pixels of the 242 darks:
    /// dark current is generated before the analogue gain, so a fixed set of hot
    /// pixels must imply the same electron excess at every ISO. It does not. It
    /// implies 6.69 e⁻ below ISO 400 and 3.08 e⁻ at or above it — a 2.17× step,
    /// with a purely proportional (additive term ≈ 0) fit inside each mode. All
    /// 11 dark groups are 1/100 s and were shot interleaved within 3.5 minutes,
    /// which excludes exposure and temperature.
    ///
    /// Only the *product* `gain × read_noise_e` is measured above ISO 400, so
    /// the DN-domain predictions are right and the electron-domain split is not
    /// identified. See [`CameraProfile::gain_divisor`].
    ///
    /// **What would make it fail:** making gain depend on the mode — which is
    /// the correct fix, and should be made deliberately, on the strength of a
    /// PTC at ISO 500 or 1000 rather than on darks alone.
    #[test]
    fn the_gain_relation_is_still_continuous_across_the_dual_gain_switch() {
        let p = by_model("ILCE-7CM2").unwrap();

        // Gain is a single straight line through the switch: doubling the ISO
        // doubles g on both sides of it and across it.
        let below = p.gain_dn_per_e(200.0);
        let above = p.gain_dn_per_e(400.0);
        assert!(
            (above / below - 2.0).abs() < 1e-5,
            "gain steps by {} across the switch, not 2.0; if this is deliberate, \
             M48c's 2.17x dark-current discrepancy is the measurement to cite",
            above / below
        );

        // The measured step, carried as the expected wrong value. 2.174 is
        // 6.6855 / 3.0765 from the two independent within-mode fits.
        let measured_step = 6.6855_f64 / 3.0765_f64;
        assert!(
            (2.10..2.25).contains(&measured_step),
            "M48c measured {measured_step}"
        );
        // What the model currently asserts instead: no step at all.
        let modelled_step = 1.0_f64;
        assert!(
            (measured_step - modelled_step).abs() > 1.0,
            "the discrepancy this test exists to record has gone away"
        );
    }

    // ---------------------------------------------------------------------
    // M90 — the opt-in corrections
    // ---------------------------------------------------------------------

    /// Deliverable A, on the bits. The default path must not move, at any ISO,
    /// at any signal, on any plane — including through `noise_model_for`, which
    /// is what the merge actually calls.
    #[test]
    fn the_shipped_corrections_are_bit_identical_to_the_default_path() {
        assert_eq!(Corrections::default(), Corrections::SHIPPED);
        let p = by_model("ILCE-7CM2").unwrap();
        for iso in [50.0f32, 100.0, 160.0, 400.0, 800.0, 3200.0, 12800.0] {
            assert_eq!(
                p.gain_dn_per_e(iso).to_bits(),
                p.gain_dn_per_e_with(iso, Corrections::SHIPPED).to_bits()
            );
            let a = p.noise_model(iso, levels());
            let b = p.noise_model_with(iso, levels(), Corrections::SHIPPED);
            let c = noise_model_for("ILCE-7CM2", Some(iso), levels());
            let d = noise_model_for_with("ILCE-7CM2", Some(iso), levels(), Corrections::SHIPPED);
            assert!(b.prnu().is_none(), "SHIPPED must not attach a pattern");
            assert!(d.prnu().is_none());
            for s in (0..=15_360).step_by(53) {
                let s = s as f32;
                assert_eq!(a.green_luma_sigma(s).to_bits(), b.green_luma_sigma(s).to_bits());
                assert_eq!(c.green_luma_sigma(s).to_bits(), d.green_luma_sigma(s).to_bits());
                for pl in CfaPlane::ALL {
                    assert_eq!(a.variance(pl, s).to_bits(), b.variance(pl, s).to_bits());
                    assert_eq!(a.sigma(pl, s).to_bits(), b.sigma(pl, s).to_bits());
                    assert_eq!(c.sigma(pl, s).to_bits(), d.sigma(pl, s).to_bits());
                }
            }
        }
    }

    /// The trap. A gain-only correction that forgets `read_noise_e` was fitted
    /// through the *old* gain silently moves the dark floor, and the dark floor
    /// is the one part of this model that 44 independently reproduced cells of
    /// M4's table already pin down.
    #[test]
    fn the_measured_gain_correction_preserves_the_dark_floor() {
        let p = by_model("ILCE-7CM2").unwrap();
        for iso in [100.0f32, 200.0, 400.0, 1600.0, 6400.0] {
            for c in [
                Corrections::GAIN_ONLY,
                Corrections::PRNU_ONLY,
                Corrections::BOTH,
            ] {
                let shipped = p.noise_model(iso, levels());
                let corrected = p.noise_model_with(iso, levels(), c);
                let a = shipped.sigma(CfaPlane::G1, 0.0);
                let b = corrected.sigma(CfaPlane::G1, 0.0);
                assert!(
                    (a - b).abs() / a < 1e-5,
                    "ISO {iso} {c:?}: dark floor moved {a} -> {b}"
                );
                // And with the pattern switched on, since it is quadratic and
                // must contribute nothing at zero.
                let b2 = corrected.sigma_with_fixed_pattern(CfaPlane::G1, 0.0);
                assert!((a - b2).abs() / a < 1e-5, "ISO {iso} {c:?}: {a} -> {b2}");
            }
        }
    }

    /// The gain correction is the -2.16% M71 reported, and it is a pure scale in
    /// ISO rather than something that only holds at base.
    #[test]
    fn the_measured_gain_is_2_16_percent_below_the_shipped_one() {
        let p = by_model("ILCE-7CM2").unwrap();
        for iso in [100.0f32, 400.0, 1600.0, 12800.0] {
            let ratio = p.gain_dn_per_e_with(iso, Corrections::GAIN_ONLY) / p.gain_dn_per_e(iso);
            assert!(
                (ratio - 0.978_88).abs() < 5e-4,
                "ISO {iso}: ratio {ratio}, expected 0.97888 (= 436.8 / 446.2233)"
            );
        }
        // The divisor a reader would look up in M71 §6.1.
        assert!((A7C2_MEASURED_GAIN_DIVISOR - 446.2233).abs() < 0.01);
    }

    /// Fact 1064's crossover, re-derived from the constants this file carries
    /// rather than copied from the report: shot-only and shot-plus-pattern cross
    /// where `(g_shipped - g_measured) * S = (kappa * S)^2`, i.e. at
    /// `S = (g_s - g_m) / kappa^2`.
    #[test]
    fn the_two_errors_cross_at_about_504_dn() {
        let p = by_model("ILCE-7CM2").unwrap();
        let shipped = p.noise_model(100.0, levels());
        let both = p.noise_model_with(100.0, levels(), Corrections::BOTH);
        let excess = |s: f32| {
            both.variance_with_fixed_pattern(CfaPlane::G1, s) - shipped.variance(CfaPlane::G1, s)
        };
        // Below the crossover the corrected model is the *smaller* one.
        assert!(excess(100.0) < 0.0, "at S = 100: {}", excess(100.0));
        // Above it, the larger.
        assert!(excess(2000.0) > 0.0, "at S = 2000: {}", excess(2000.0));
        // Bisect for the sign change.
        let (mut lo, mut hi) = (100.0f32, 2000.0f32);
        for _ in 0..60 {
            let mid = 0.5 * (lo + hi);
            if excess(mid) < 0.0 {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        let crossover = 0.5 * (lo + hi);
        assert!(
            (crossover - 504.0).abs() < 15.0,
            "crossover at {crossover} DN, fact 1064 says 504"
        );
    }

    /// A correction the profile cannot honour must be visible, not silent.
    #[test]
    fn an_unsupported_correction_is_reported_rather_than_faked() {
        let p = by_model("ILCE-7CM2").unwrap();
        assert!(p.supports(Corrections::BOTH));
        // The fallback body has no measurements, so the corrected call is the
        // uncorrected one and stays stamped as a guess.
        let a = noise_model_for("NOT-A-CAMERA", Some(100.0), levels());
        let b = noise_model_for_with("NOT-A-CAMERA", Some(100.0), levels(), Corrections::BOTH);
        assert_eq!(b.provenance, Provenance::Fallback);
        assert!(b.prnu().is_none(), "a guessed gain must not carry M71's kappa");
        for s in (0..=15_360).step_by(211) {
            let s = s as f32;
            assert_eq!(a.sigma(CfaPlane::G1, s).to_bits(), b.sigma(CfaPlane::G1, s).to_bits());
        }
    }
}
