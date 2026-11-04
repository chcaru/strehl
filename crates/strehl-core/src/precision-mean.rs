//! Stable fixed-weight statistics for optional session means. A caller must
//! predict variances independently of the measurements being weighted. This
//! helper propagates conditional temporal variance, not adaptive-selection risk.

#[derive(Clone, Copy, Debug)]
pub struct PrecisionMean {
    mean: [f32; 4],
    reference: f32,
    weight: f32,
    weight_squared: f32,
    variance_numerator: [f32; 2],
    primary_weight: f32,
    dominant_weight: f32,
    dominant_source: u64,
    count: u32,
    positive_count: u32,
}
impl Default for PrecisionMean {
    fn default() -> Self {
        Self {
            mean: [0.0; 4],
            reference: f32::INFINITY,
            weight: 0.0,
            weight_squared: 0.0,
            variance_numerator: [0.0; 2],
            primary_weight: 0.0,
            dominant_weight: 0.0,
            dominant_source: u64::MAX,
            count: 0,
            positive_count: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PrecisionResult {
    pub mean: [f32; 4],
    /// Luma variance and common-weight maximum-color variance bound.
    pub temporal_variance: [f32; 2],
    pub effective_sources: f32,
    pub primary_fraction: f32,
    pub dominant_fraction: f32,
    pub dominant_source: u64,
    /// Eligible observations, including observations with zero numerical weight.
    pub count: u32,
    /// Observations retaining positive weight after the zero-variance limit.
    pub positive_count: u32,
}
impl PrecisionMean {
    /// `prediction` supplies the precision weight; `variance` supplies the
    /// propagated luma and maximum-color temporal variance. Their distinction
    /// permits a caller to audit a deliberately misspecified prediction.
    pub fn push(
        &mut self,
        value: [f32; 4],
        prediction: f32,
        variance: [f32; 2],
        source: u64,
        primary: bool,
    ) -> Result<(), &'static str> {
        // A failed observation never poisons a reusable accumulator.
        let mut next = *self;
        next.push_inner(value, prediction, variance, source, primary)?;
        *self = next;
        Ok(())
    }

    fn push_inner(
        &mut self,
        value: [f32; 4],
        prediction: f32,
        variance: [f32; 2],
        source: u64,
        primary: bool,
    ) -> Result<(), &'static str> {
        if !prediction.is_finite()
            || prediction < 0.0
            || value.iter().any(|v| !v.is_finite())
            || variance.iter().any(|v| !v.is_finite() || *v < 0.0)
        {
            return Err("invalid precision observation");
        }
        if self.count == u32::MAX {
            return Err("precision count overflow");
        }
        // Scale all weights by the smallest encountered prediction, so no
        // reciprocal of a tiny variance can overflow. Exact zero predictions
        // give weight only to other zero predictions, without an invented floor.
        if prediction < self.reference {
            let ratio = if self.reference.is_infinite() {
                0.0
            } else {
                prediction / self.reference
            };
            if ratio == 0.0 {
                self.positive_count = 0;
            }
            self.weight *= ratio;
            self.weight_squared *= ratio * ratio;
            for n in &mut self.variance_numerator {
                *n *= ratio * ratio;
            }
            self.primary_weight *= ratio;
            self.dominant_weight *= ratio;
            self.reference = prediction;
        }
        let w = if prediction == 0.0 {
            1.0
        } else {
            self.reference / prediction
        };
        self.count += 1;
        if w == 0.0 {
            return Ok(());
        }
        self.positive_count += 1;
        let total = self.weight + w;
        if self.weight == 0.0 {
            self.mean = value;
        } else {
            for (mean, v) in self.mean.iter_mut().zip(value) {
                *mean += (v - *mean) * (w / total);
            }
        }
        self.weight = total;
        self.weight_squared += w * w;
        for (n, v) in self.variance_numerator.iter_mut().zip(variance) {
            *n += w * w * v;
        }
        if primary {
            self.primary_weight += w;
        }
        if w > self.dominant_weight || (w == self.dominant_weight && source < self.dominant_source)
        {
            self.dominant_weight = w;
            self.dominant_source = source;
        }
        if self
            .mean
            .iter()
            .chain(&self.variance_numerator)
            .any(|v| !v.is_finite())
        {
            return Err("nonfinite precision accumulation");
        }
        Ok(())
    }
    pub fn result(&self) -> Option<PrecisionResult> {
        (self.weight > 0.0).then(|| PrecisionResult {
            mean: self.mean,
            temporal_variance: self
                .variance_numerator
                .map(|v| v / (self.weight * self.weight)),
            effective_sources: self.weight * self.weight / self.weight_squared,
            primary_fraction: self.primary_weight / self.weight,
            dominant_fraction: self.dominant_weight / self.weight,
            dominant_source: self.dominant_source,
            count: self.count,
            positive_count: self.positive_count,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn gaussian(state: &mut u64) -> f32 {
        fn uniform(s: &mut u64) -> f64 {
            *s = s
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((*s >> 11) as f64 + 0.5) / 9007199254740992.0
        }
        let u = uniform(state);
        let v = uniform(state);
        ((-2.0 * u.ln()).sqrt() * (std::f64::consts::TAU * v).cos()) as f32
    }
    #[test]
    fn a_flat_temporal_trials_verify_noise_and_same_sample_weighting_bias() {
        let mut seed = 73;
        let mut sum = 0.0_f64;
        let mut square = 0.0_f64;
        let mut biased_sum = 0.0_f64;
        let trials = 100_000;
        for _ in 0..trials {
            let x = 100.0 + 20.0 * gaussian(&mut seed);
            let y = 100.0 + 10.0 * gaussian(&mut seed);
            let mut fixed = PrecisionMean::default();
            fixed.push([x; 4], 400.0, [400.0; 2], 0, false).unwrap();
            fixed.push([y; 4], 100.0, [100.0; 2], 1, false).unwrap();
            let value = f64::from(fixed.result().unwrap().mean[0]);
            sum += value;
            square += value * value;
            let mut biased = PrecisionMean::default();
            biased
                .push([x; 4], (4.0 * x).max(1.0), [400.0; 2], 0, false)
                .unwrap();
            biased
                .push([y; 4], y.max(1.0), [100.0; 2], 1, false)
                .unwrap();
            biased_sum += f64::from(biased.result().unwrap().mean[0]);
        }
        let mean = sum / f64::from(trials);
        let variance = square / f64::from(trials) - mean * mean;
        assert!((mean - 100.0).abs() < 0.12, "fixed prediction mean {mean}");
        assert!(
            (variance / 80.0 - 1.0).abs() < 0.02,
            "fixed prediction variance {variance}"
        );
        let biased_mean = biased_sum / f64::from(trials);
        // First-order expected bias here is -0.8 DN. This cut is >10 standard
        // errors from zero; it tests mean preservation, not a fitted noise score.
        assert!(
            biased_mean < mean - 0.4,
            "same-sample precision foil mean {biased_mean}, fixed {mean}"
        );
        eprintln!(
            "precision flat: fixed mean={mean}, variance={variance}, same-sample mean={biased_mean}, trials={trials}"
        );
    }
    #[test]
    fn heterogeneous_fixed_prediction_reaches_known_mean_variance_and_attribution() {
        let mut a = PrecisionMean::default();
        a.push([100.0; 4], 400.0, [400.0, 900.0], 11, false)
            .unwrap();
        a.push([120.0; 4], 100.0, [100.0, 225.0], 29, true).unwrap();
        let r = a.result().unwrap();
        assert_eq!(r.mean, [116.0; 4]);
        assert_eq!(r.temporal_variance, [80.0, 180.0]);
        assert!((r.effective_sources - 25.0 / 17.0).abs() < 1e-6);
        assert_eq!(r.primary_fraction, 0.8);
        assert_eq!(r.dominant_source, 29);
        assert_eq!(r.dominant_fraction, 0.8);
    }
    #[test]
    fn equal_prediction_is_equal_mean_and_extreme_precision_cannot_overflow_reciprocals() {
        let mut a = PrecisionMean::default();
        for (i, v) in [2.0, 4.0, 6.0].into_iter().enumerate() {
            a.push([v; 4], 1e-30, [1e-30; 2], i as u64, false).unwrap();
        }
        let r = a.result().unwrap();
        assert_eq!(r.mean, [4.0; 4]);
        assert_eq!(r.effective_sources, 3.0);
        assert!((r.temporal_variance[0] / 1e-30 - 1.0 / 3.0).abs() < 1e-6);
    }
    #[test]
    fn zero_prediction_limit_and_invalid_inputs_are_explicit() {
        let mut a = PrecisionMean::default();
        assert!(a.result().is_none());
        a.push([2.0; 4], 4.0, [4.0; 2], 0, true).unwrap();
        a.push([8.0; 4], 0.0, [0.0; 2], 1, false).unwrap();
        a.push([10.0; 4], 0.0, [0.0; 2], 2, false).unwrap();
        let r = a.result().unwrap();
        assert_eq!(r.mean, [9.0; 4]);
        assert_eq!(r.temporal_variance, [0.0; 2]);
        assert_eq!(r.primary_fraction, 0.0);
        assert_eq!(r.effective_sources, 2.0);
        assert_eq!(r.count, 3);
        assert_eq!(r.positive_count, 2);
        assert!(a.push([f32::NAN; 4], 1.0, [1.0; 2], 3, false).is_err());
        assert!(a.push([1.0; 4], -1.0, [1.0; 2], 3, false).is_err());
    }
    #[test]
    fn misspecified_prediction_does_not_relabel_actual_variance() {
        let mut a = PrecisionMean::default();
        a.push([0.0; 4], 1.0, [400.0; 2], 0, false).unwrap();
        a.push([0.0; 4], 1.0, [100.0; 2], 1, false).unwrap();
        assert_eq!(a.result().unwrap().temporal_variance, [125.0; 2]);
    }

    #[test]
    fn original_u64_identity_and_failed_push_preserve_state() {
        let mut a = PrecisionMean::default();
        let id = u64::from(u32::MAX) + 123;
        a.push([1.0; 4], 1.0, [1.0; 2], id, true).unwrap();
        let before = a.result().unwrap();
        assert_eq!(before.dominant_source, id);
        assert!(a.push([f32::MAX; 4], 1.0, [f32::MAX; 2], 1, false).is_ok());
        let before_overflow = a.result().unwrap();
        assert!(
            a.push([-f32::MAX; 4], 1.0, [f32::MAX; 2], 2, false)
                .is_err()
        );
        assert_eq!(a.result().unwrap(), before_overflow);
        assert!(a.push([0.0; 4], f32::NAN, [1.0; 2], 0, false).is_err());
        assert_eq!(a.result().unwrap(), before_overflow);
    }
}
