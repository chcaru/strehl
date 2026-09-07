//! The registry: calibrated operators in, a **dimensionless** gate out.
//!
//! # What `--gate` means, before and after
//!
//! Before: `tol = t * sqrt(2) * FOCUS_NOISE_SD` with `FOCUS_NOISE_SD` a
//! compiled-in constant measured for one operator at one window under one
//! regulariser. Fact 436 verified that relation against the shipped binary at
//! five gates spanning 35x, `tol/t` constant to 2.0e-6 — so `t` is exactly
//! linear in a constant that belongs to the *replaceable* component. An
//! operator whose true SD is `k` times the constant runs at `t/k`, and fact 438
//! is that nothing observable changes.
//!
//! **Read `t/k` as a price, not as a repair.** Fact 631 scopes it: the
//! substitution is exact for the same operator rescaled — scale the operator
//! and its constant by 7 and 18 pixels in 8,236,816 move — and false across
//! genuinely different operators, which shift `n_eff` by up to 4.54x and the
//! winner map on 71.5% of pixels. So there is no gate a user could type that
//! recovers a correctly calibrated operator's decisions from a mis-calibrated
//! one. `--gate` is the wrong place to fix this, which is why the fix is here.
//!
//! After: the field is divided by its own host-measured noise SD before the
//! gate, so its noise SD is **1.0 by construction** and
//!
//! ```text
//! tol = t * sqrt(2)
//! ```
//!
//! carries no operator in it at all. That is the only version of this design in
//! which a `--gate` written down in a shared preset means the same thing on two
//! different operators (workstream E §F5.3, point 3).
//!
//! # The two paths are the same admission set — *in exact arithmetic*
//!
//! Fact 503 derives it and fact 504 sharpens it: dividing the field by a
//! positive constant and multiplying the tolerance by the same one changes the
//! *rounding*, not the mathematics, so a small number of f32 comparisons flip.
//! The predicted rate is 1e-6 to 1e-5 of decisions. Both paths are offered here
//! — [`Registered::field`] with [`Registered::gate`], or
//! [`Registered::raw_field`] with [`Registered::unnormalised_tolerance`] — and
//! `tests::pre_normalising_the_field_flips_a_bounded_and_tiny_number_of_admissions`
//! measures the disagreement rather than asserting it away.

use std::sync::Arc;

use strehl_core::noise::NoiseModel;

use crate::calibrate::{
    Calibration, CalibrationError, CalibrationPlan, SelfCheck, SelfCheckError, calibrate,
    self_check,
};
use crate::field::{FieldConfig, FieldWorkspace};
use crate::measure::FocusMeasure;

/// The merge's admission rule, in units of the response's own noise.
///
/// A frame is admitted at a pixel when its **pre-normalised** focus response is
/// within `threshold` standard deviations of the winner's. Both responses are
/// already in units of their own noise SD and the two frames' sensor noise is
/// independent, so the standard deviation of the difference is `sqrt(2)` — with
/// no operator constant anywhere in it.
///
/// This is deliberately the same shape as [`strehl_core::merge::Gate`], minus
/// the constant. It is a different type because it consumes a different field:
/// handing a raw field to this gate would run the merge at `1 / SD` times the
/// intended tolerance, which for the shipped operator is **65.7x**.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Gate {
    threshold: f32,
}

impl Gate {
    /// The user's `--gate`, in standard deviations.
    #[must_use]
    pub fn threshold(self) -> f32 {
        self.threshold
    }

    /// The admission half-width. **Dimensionless.**
    #[must_use]
    pub fn tolerance(self) -> f32 {
        self.threshold * std::f32::consts::SQRT_2
    }

    /// Is a frame with response `focus` admitted against a winner at `best`?
    ///
    /// A non-finite response is never admitted, because every comparison
    /// against NaN is false. Same rule, same direction, as
    /// [`strehl_core::merge::Gate::admits`].
    #[must_use]
    pub fn admits(self, focus: f32, best: f32) -> bool {
        best - focus <= self.tolerance()
    }
}

/// A registered, calibrated operator.
///
/// Carries the [`FieldConfig`] it was calibrated under, so there is no way to
/// obtain a field from it under a configuration its constant does not describe.
pub struct Registered {
    measure: Arc<dyn FocusMeasure>,
    calibration: Calibration,
    cfg: FieldConfig,
}

impl Registered {
    #[must_use]
    pub fn id(&self) -> &str {
        self.measure.id()
    }

    #[must_use]
    pub fn measure(&self) -> &dyn FocusMeasure {
        self.measure.as_ref()
    }

    /// The **host-measured** noise scale. Not declared, not trusted, not
    /// defaulted.
    #[must_use]
    pub fn calibration(&self) -> Calibration {
        self.calibration
    }

    /// The configuration this operator was calibrated under.
    #[must_use]
    pub fn config(&self) -> FieldConfig {
        self.cfg
    }

    /// The plugin halo — the rectangle expansion a tile needs beyond its own
    /// bounds under this operator and this host regulariser (rule 15).
    #[must_use]
    pub fn plugin_halo(&self) -> usize {
        self.cfg.plugin_halo(self.measure.as_ref())
    }

    /// The dimensionless gate for a user threshold.
    #[must_use]
    pub fn gate(&self, threshold: f32) -> Gate {
        assert!(
            threshold >= 0.0 && threshold.is_finite(),
            "gate threshold must be finite and non-negative, got {threshold}"
        );
        Gate { threshold }
    }

    /// The focus field, **divided by its own measured noise SD**. Its noise
    /// standard deviation is 1.0 by construction, which is what makes
    /// [`Gate`] dimensionless.
    pub fn field<'w>(
        &self,
        ws: &'w mut FieldWorkspace,
        luma: &[f32],
        noise: &NoiseModel,
    ) -> &'w [f32] {
        let scale = 1.0 / self.calibration.response_sd();
        ws.run(self.measure.as_ref(), self.cfg, luma, noise);
        ws.scale_in_place(scale)
    }

    /// The focus field in the operator's own units, un-normalised. Pair it with
    /// [`unnormalised_tolerance`](Self::unnormalised_tolerance).
    ///
    /// This is the shape the merge has today. It is kept because it is the
    /// migration path — a host can adopt the *measured* constant without
    /// adopting the pre-normalisation, and get the correctness property
    /// immediately while the f32 question of fact 504 is settled separately.
    pub fn raw_field<'w>(
        &self,
        ws: &'w mut FieldWorkspace,
        luma: &[f32],
        noise: &NoiseModel,
    ) -> &'w [f32] {
        ws.run(self.measure.as_ref(), self.cfg, luma, noise)
    }

    /// `t * sqrt(2) * response_sd` — the tolerance for a raw field.
    ///
    /// The same arithmetic [`strehl_core::merge::Gate::tolerance`] performs,
    /// with the compiled-in constant replaced by the measured one. **This is
    /// the whole of the repair**, and it is one multiplication.
    #[must_use]
    pub fn unnormalised_tolerance(&self, threshold: f32) -> f32 {
        threshold * std::f32::consts::SQRT_2 * self.calibration.response_sd()
    }
}

/// Why a registration was refused.
#[derive(Debug, thiserror::Error)]
pub enum RegistrationError {
    #[error("a focus measure is already registered as `{0}`")]
    Duplicate(String),
    #[error("a focus measure must have a non-empty id")]
    EmptyId,
    #[error("calibrating `{id}` failed: {source}")]
    Calibration {
        id: String,
        #[source]
        source: CalibrationError,
    },
}

/// Calibrated focus measures, keyed by id.
///
/// # Two structural properties, both tested
///
/// - **Registration order does not change anything.** The entries are a `Vec`
///   in registration order and [`Registry::ids`] returns them sorted, so
///   nothing downstream can depend on the order. Workstream E §F4.6 fault 4 is
///   the reason this is stated: a registry built on a `HashMap` and iterated
///   directly is order-stable *within a process*, so an in-process property
///   test is blind to it.
/// - **The registry refuses to exist if its own instrument fails.** [`new`](Self::new)
///   runs [`self_check`] first, against both in-crate constants in both of
///   their configurations. Discipline 257 at the API boundary rather than in a
///   test file.
pub struct Registry {
    cfg: FieldConfig,
    plan: CalibrationPlan,
    check: SelfCheck,
    entries: Vec<Registered>,
}

impl Registry {
    /// Build a registry, validating the calibrator against both in-crate
    /// constants first.
    ///
    /// # Errors
    ///
    /// [`SelfCheckError`] if either target misses. Nothing can be registered
    /// against an instrument that cannot reproduce the two numbers this
    /// repository already measured.
    pub fn new(cfg: FieldConfig, plan: CalibrationPlan) -> Result<Self, SelfCheckError> {
        let check = self_check(&plan)?;
        Ok(Self {
            cfg,
            plan,
            check,
            entries: Vec::new(),
        })
    }

    /// **Register an operator, measuring its noise scale on the way in.**
    ///
    /// # Errors
    ///
    /// [`RegistrationError`]. Note that a degenerate or non-finite operator is
    /// refused here rather than admitted with a plausible-looking constant.
    pub fn register(
        &mut self,
        measure: Arc<dyn FocusMeasure>,
    ) -> Result<&Registered, RegistrationError> {
        let id = measure.id().to_string();
        if id.is_empty() {
            return Err(RegistrationError::EmptyId);
        }
        if self.entries.iter().any(|e| e.id() == id) {
            return Err(RegistrationError::Duplicate(id));
        }
        let calibration = calibrate(measure.as_ref(), self.cfg, &self.plan)
            .map_err(|source| RegistrationError::Calibration { id, source })?;
        self.entries.push(Registered {
            measure,
            calibration,
            cfg: self.cfg,
        });
        Ok(self.entries.last().expect("just pushed"))
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&Registered> {
        self.entries.iter().find(|e| e.id() == id)
    }

    /// Every registered id, **sorted** — so nothing downstream can inherit the
    /// registration order.
    #[must_use]
    pub fn ids(&self) -> Vec<&str> {
        let mut ids: Vec<&str> = self.entries.iter().map(Registered::id).collect();
        ids.sort_unstable();
        ids
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    #[must_use]
    pub fn config(&self) -> FieldConfig {
        self.cfg
    }

    #[must_use]
    pub fn plan(&self) -> &CalibrationPlan {
        &self.plan
    }

    /// The two-target instrument check this registry passed on construction.
    #[must_use]
    pub fn instrument_check(&self) -> &SelfCheck {
        &self.check
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reference::{SumModifiedLaplacian, Tenengrad};
    use crate::rng::{NoiseSource, unit_sigma_model};
    use strehl_core::focus::WINDOW_RADIUS;
    use strehl_core::merge::FOCUS_NOISE_SD;
    use strehl_core::plane::PlaneGeometry;

    fn registry() -> Registry {
        Registry::new(FieldConfig::SHIPPED, CalibrationPlan::host_default())
            .expect("the instrument must pass its own two-target check")
    }

    /// **`--gate` is dimensionless: the tolerance is identical for two
    /// operators whose noise scales differ by 6.7x.**
    ///
    /// Rule 20 — this fails if the gate carried any operator-dependent factor,
    /// which is precisely the state the code is in today. The second half is
    /// what stops it being a tautology: the *un-normalised* tolerances must
    /// differ by exactly the measured `k`, so the operators genuinely are
    /// different and the equality above is a property of the normalisation
    /// rather than of the two operators being the same.
    #[test]
    fn the_gate_is_dimensionless_across_operators_that_differ_by_a_factor_of_six() {
        let mut reg = registry();
        reg.register(Arc::new(Tenengrad::shipped())).unwrap();
        reg.register(Arc::new(SumModifiedLaplacian::at_radius(WINDOW_RADIUS)))
            .unwrap();

        let ten = reg.get("tenengrad-w13").unwrap();
        let sml = reg.get("sml-w13").unwrap();

        for t in [0.0f32, 0.5, 1.0, 2.0, 5.94] {
            assert_eq!(
                ten.gate(t).tolerance(),
                sml.gate(t).tolerance(),
                "the dimensionless tolerance must not depend on the operator"
            );
            assert_eq!(ten.gate(t).tolerance(), t * std::f32::consts::SQRT_2);
        }

        let k = sml.calibration().response_sd() / ten.calibration().response_sd();
        let ratio = sml.unnormalised_tolerance(1.0) / ten.unnormalised_tolerance(1.0);
        assert!(
            (ratio - k).abs() < 1e-5,
            "the un-normalised tolerances must differ by exactly k: {ratio} vs {k}"
        );
        assert!(
            k > 5.5,
            "the two operators must actually differ, or the equality above is \
             vacuous; k = {k}"
        );
    }

    /// **Fault 5 is unrepresentable, demonstrated end to end through the
    /// registry.**
    ///
    /// A deliberately mis-matched operator — SML, fact 439's worst case and the
    /// likeliest real contribution — is registered against a host whose
    /// compiled-in constant is 0.015214. The host-measured constant tracks the
    /// operator. There is no code path by which SML could have inherited
    /// 0.015214, because [`Calibration`] has no public constructor and
    /// [`FocusMeasure`] has no method that could supply one.
    ///
    /// 6.680 is quoted below as *this repository's* SML, not as a property of
    /// SML: fact 635 scopes fact 439 by showing a `k` scales exactly with any
    /// constant folded into the stencil, and this one folds none. The band is
    /// wide because the number is convention-dependent; the *seam* is not.
    #[test]
    fn registering_a_mismatched_operator_yields_its_own_constant_not_the_hosts() {
        let mut reg = registry();
        reg.register(Arc::new(Tenengrad::shipped())).unwrap();
        reg.register(Arc::new(SumModifiedLaplacian::at_radius(WINDOW_RADIUS)))
            .unwrap();

        let sml = reg.get("sml-w13").unwrap().calibration();
        let k = sml.k_against_host_constant();
        let inherited_effective_gate = 1.0 / k;
        println!(
            "SML w13 + r8: host-measured SD {:e} +/- {:e}, k = {k:.4} against the \
             host's {FOCUS_NOISE_SD:e} (fact 439 measures 6.680). A plugin \
             inheriting the host constant would run --gate 1.0 at {:.4}.",
            sml.response_sd(),
            sml.sem(),
            inherited_effective_gate
        );
        assert!(
            (sml.response_sd() - FOCUS_NOISE_SD).abs() > 20.0 * sml.sem(),
            "the measured constant must be distinguishable from the host default"
        );
        assert!((5.5..8.0).contains(&k), "k = {k}");
    }

    /// Workstream E's P1, on the one ordering this crate controls: the
    /// resolved calibration must be a function of the config alone.
    #[test]
    fn registration_order_does_not_change_a_single_calibrated_constant() {
        let make = |reverse: bool| {
            let mut reg = registry();
            let ops: Vec<Arc<dyn FocusMeasure>> = if reverse {
                vec![
                    Arc::new(SumModifiedLaplacian::at_radius(WINDOW_RADIUS)),
                    Arc::new(Tenengrad::shipped()),
                ]
            } else {
                vec![
                    Arc::new(Tenengrad::shipped()),
                    Arc::new(SumModifiedLaplacian::at_radius(WINDOW_RADIUS)),
                ]
            };
            for op in ops {
                reg.register(op).unwrap();
            }
            reg
        };
        let a = make(false);
        let b = make(true);
        assert_eq!(a.ids(), b.ids(), "ids() must be order-independent");
        for id in a.ids() {
            assert_eq!(
                a.get(id).unwrap().calibration(),
                b.get(id).unwrap().calibration(),
                "{id} calibrated differently depending on registration order"
            );
        }
    }

    #[test]
    fn a_duplicate_id_is_refused_and_an_empty_one_too() {
        let mut reg = registry();
        reg.register(Arc::new(Tenengrad::shipped())).unwrap();
        let err = reg
            .register(Arc::new(Tenengrad::shipped()))
            .err()
            .expect("a duplicate id must be refused");
        assert!(matches!(err, RegistrationError::Duplicate(ref s) if s == "tenengrad-w13"));
        assert_eq!(reg.len(), 1);
        assert!(!reg.is_empty());
        assert_eq!(reg.config(), FieldConfig::SHIPPED);
        assert!(reg.instrument_check().coarse.passed);
    }

    /// The normalised field really does have unit noise SD — which is the
    /// claim that makes the gate dimensionless, and it is checked on a plane
    /// the calibration never saw.
    #[test]
    fn the_normalised_field_has_unit_noise_sd_on_a_held_out_seed() {
        let mut reg = registry();
        reg.register(Arc::new(SumModifiedLaplacian::at_radius(WINDOW_RADIUS)))
            .unwrap();
        let entry = reg.get("sml-w13").unwrap();

        let g = PlaneGeometry {
            width: 512,
            height: 512,
        };
        let mut plane = vec![0.0f32; g.pixels()];
        // A seed outside CRATE_SEEDS, and a different generator, so this is a
        // held-out check rather than a restatement of the calibration.
        NoiseSource::PcgBoxMuller.fill(0x5745_4C4C, &mut plane);
        let noise = unit_sigma_model();
        let mut ws = FieldWorkspace::new(g);
        let field = entry.field(&mut ws, &plane, &noise).to_vec();

        let margin = entry.config().calibration_margin(entry.measure());
        let mut vals = Vec::new();
        for y in margin..g.height - margin {
            for x in margin..g.width - margin {
                vals.push(f64::from(field[y * g.width + x]));
            }
        }
        let mean = vals.iter().sum::<f64>() / vals.len() as f64;
        let sd =
            (vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (vals.len() - 1) as f64).sqrt();
        println!("held-out normalised SML field: sd = {sd:.4} (target 1.0)");
        assert!(
            (0.90..1.10).contains(&sd),
            "the pre-normalised field must have unit noise SD, got {sd:.4}"
        );
    }

    // ------------------------------------------------------------ facts 503/504

    /// Raw and pre-normalised field stacks for `frames` independent unit-noise
    /// planes, plus the interior index list.
    ///
    /// Both stacks come from the **real API** — [`Registered::raw_field`] and
    /// [`Registered::field`] — rather than from a hand-written rescale, so what
    /// is measured is the rounding this crate actually performs (a multiply by
    /// the reciprocal, not a divide) and not an idealisation of it.
    ///
    /// Pure noise is deliberate: it is the configuration in which the frames
    /// are statistically identical, so `best - focus` piles up right where the
    /// tolerance sits. It is the **worst case** for the flip rate, not a
    /// flattering one.
    fn noise_field_stacks(
        entry: &Registered,
        side: usize,
        frames: usize,
        first_seed: u64,
    ) -> (Vec<Vec<f32>>, Vec<Vec<f32>>, Vec<usize>) {
        let g = PlaneGeometry {
            width: side,
            height: side,
        };
        let noise = unit_sigma_model();
        let mut ws = FieldWorkspace::new(g);
        let mut plane = vec![0.0f32; g.pixels()];
        let mut raw = Vec::with_capacity(frames);
        let mut norm = Vec::with_capacity(frames);
        for k in 0..frames {
            NoiseSource::SplitMixBoxMuller.fill(first_seed + k as u64, &mut plane);
            raw.push(entry.raw_field(&mut ws, &plane, &noise).to_vec());
            norm.push(entry.field(&mut ws, &plane, &noise).to_vec());
        }
        let margin = entry.config().calibration_margin(entry.measure());
        let mut interior = Vec::new();
        for y in margin..g.height - margin {
            for x in margin..g.width - margin {
                interior.push(y * g.width + x);
            }
        }
        (raw, norm, interior)
    }

    /// How many admission decisions differ between `(raw, raw_tol)` and
    /// `(norm scaled by an extra `bias`, dimensionless_tol)`.
    ///
    /// `bias == 1.0` is the treatment arm: the two arms are then the same
    /// comparison in exact arithmetic (fact 503) and only rounding can differ.
    /// `bias != 1.0` is a genuinely different gate, and is the positive
    /// control.
    fn admission_disagreements(
        raw: &[Vec<f32>],
        norm: &[Vec<f32>],
        interior: &[usize],
        raw_tol: f32,
        dimensionless_tol: f32,
        bias: f32,
    ) -> (usize, usize) {
        let mut differing = 0usize;
        let mut decisions = 0usize;
        for &i in interior {
            let mut best_raw = f32::NEG_INFINITY;
            let mut best_norm = f32::NEG_INFINITY;
            for f in raw {
                best_raw = best_raw.max(f[i]);
            }
            for f in norm {
                best_norm = best_norm.max(f[i] * bias);
            }
            for (r, n) in raw.iter().zip(norm) {
                let a = best_raw - r[i] <= raw_tol;
                let b = best_norm - n[i] * bias <= dimensionless_tol;
                if a != b {
                    differing += 1;
                }
                decisions += 1;
            }
        }
        (differing, decisions)
    }

    /// **Facts 503/504, measured.** Pre-normalising the focus field by its own
    /// host-measured noise SD is behaviour-preserving in exact arithmetic; in
    /// f32 it re-rounds, so some admissions may flip.
    ///
    /// **The assertion is a bounded flip RATE, never byte-identity.** Fact 504
    /// predicted, before this test existed, that an equality assertion would go
    /// red at a rate of order 1e-6 to 1e-5 and be misread as refuting the
    /// design. A rate above **1e-4** is the pre-registered refutation: it would
    /// mean the admission boundary carries far more near-ties than the
    /// smoothness of a 27-box-then-17-box field allows, which would itself be a
    /// finding about the gate.
    ///
    /// Rule 20 — the bound above is worthless on a plant with no near-ties, so
    /// the second arm is the positive control: the *same* normalisation carried
    /// out with a constant **1% wrong**, which is a real change of gate and
    /// must blow the bound. A 0.1%-wrong arm is measured and printed but not
    /// asserted, to state the resolution this instrument actually has.
    ///
    /// An earlier version of this test used, as its control, a field divided by
    /// `SD * 1.001` compared against a tolerance *also* divided by `SD * 1.001`.
    /// That is the identical comparison — both sides scale — and it measured 0
    /// flips, correctly reporting that the control had no power. The control
    /// caught a bug in the control. It is recorded in the report rather than
    /// quietly deleted.
    ///
    /// This runs on this crate's own field, not through `merge.rs`, which
    /// another agent holds.
    #[test]
    fn pre_normalising_the_field_changes_a_bounded_and_tiny_fraction_of_admissions() {
        let mut reg = registry();
        reg.register(Arc::new(Tenengrad::shipped())).unwrap();
        let entry = reg.get("tenengrad-w13").unwrap();
        let sd = entry.calibration().response_sd();

        let (raw, norm, interior) = noise_field_stacks(entry, 512, 32, 0x9E11_0000);
        let decisions = interior.len() * raw.len();
        println!(
            "flip plant: {} frames x {} interior px = {decisions} decisions, \
             response sd {sd:e}",
            raw.len(),
            interior.len()
        );

        let mut worst = 0.0f64;
        for t in [0.5f32, 1.0, 2.0] {
            let raw_tol = entry.unnormalised_tolerance(t);
            let dim_tol = entry.gate(t).tolerance();

            let (n, total) = admission_disagreements(&raw, &norm, &interior, raw_tol, dim_tol, 1.0);
            let rate = n as f64 / total as f64;
            worst = worst.max(rate);

            let (c1, _) =
                admission_disagreements(&raw, &norm, &interior, raw_tol, dim_tol, 1.0 / 1.01);
            let (c2, _) =
                admission_disagreements(&raw, &norm, &interior, raw_tol, dim_tol, 1.0 / 1.001);
            let r1 = c1 as f64 / total as f64;
            let r2 = c2 as f64 / total as f64;

            println!(
                "  gate {t:>4}: flips {n}/{total} = {rate:.3e}   \
                 control(+1%) {r1:.3e}   control(+0.1%) {r2:.3e}"
            );
            assert!(
                rate < 1e-4,
                "gate {t}: flip rate {rate:.3e} exceeds fact 504's pre-registered \
                 refutation threshold of 1e-4"
            );
            assert!(
                r1 > 1e-4,
                "gate {t}: a 1%-wrong noise constant changed only {r1:.3e} of \
                 decisions, so the bound above has no power on this plant"
            );
        }
        // Rule of three: with zero events in `decisions` trials the 95% upper
        // bound on the rate is 3/decisions.
        println!(
            "worst measured flip rate {worst:.3e}; 95% upper bound with 0 events \
             would be {:.3e}",
            3.0 / decisions as f64
        );
    }
}
