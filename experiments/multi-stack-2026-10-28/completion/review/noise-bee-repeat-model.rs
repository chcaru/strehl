//! Two-endpoint temporal observer, independent reference, no image/source I/O.
//! Its threshold needs exact sampled-noise commissioning before real use.

#[derive(Clone, Copy, Debug)]
pub struct Times {
    pub q: [f64; 2],
    pub v: [f64; 2],
    pub r: [f64; 2],
    pub m: [f64; 2],
}

pub fn weights(endpoints: [f64; 2], time: f64) -> Result<[f64; 2], &'static str> {
    if !endpoints.iter().all(|x| x.is_finite())
        || !time.is_finite()
        || endpoints[1] <= endpoints[0]
        || time < endpoints[0]
        || time > endpoints[1]
    {
        return Err("invalid or extrapolated temporal prediction");
    }
    let b = (time - endpoints[0]) / (endpoints[1] - endpoints[0]);
    Ok([1. - b, b])
}

pub fn prediction(endpoints: [f64; 2], weights: [f64; 2]) -> f64 {
    endpoints[0] * weights[0] + endpoints[1] * weights[1]
}

impl Times {
    pub fn validate(&self) -> Result<(), &'static str> {
        for time in self.v.into_iter().chain(self.m).chain(self.r) {
            weights(self.q, time)?;
        }
        for time in self.m {
            weights(self.r, time)?;
        }
        if self.v[0] >= self.v[1] || self.m[0] >= self.m[1] {
            return Err("unordered validation or measurement times");
        }
        let mut all: Vec<_> = self
            .q
            .into_iter()
            .chain(self.v)
            .chain(self.r)
            .chain(self.m)
            .collect();
        all.sort_by(f64::total_cmp);
        if all.windows(2).any(|w| w[0] == w[1]) {
            return Err("temporal roles overlap");
        }
        Ok(())
    }

    /// Covariance of V - linear(Q). All variances supplied by the ONE injected
    /// camera model times actual original interpolation squared-weight norm.
    pub fn covariance(
        &self,
        q_variance: [f64; 2],
        v_variance: [f64; 2],
    ) -> Result<[[f64; 2]; 2], &'static str> {
        self.validate()?;
        if !q_variance
            .into_iter()
            .chain(v_variance)
            .all(|v| v.is_finite() && v > 0.)
        {
            return Err("invalid injected variance");
        }
        let h = [weights(self.q, self.v[0])?, weights(self.q, self.v[1])?];
        Ok(std::array::from_fn(|i| {
            std::array::from_fn(|j| {
                h[i][0] * h[j][0] * q_variance[0]
                    + h[i][1] * h[j][1] * q_variance[1]
                    + if i == j { v_variance[i] } else { 0. }
            })
        }))
    }

    /// Difference of squared errors, using the same independently predicted
    /// reference for candidate and its matching single-source comparator.
    /// Return BOTH physical-state terms; the primary statistic averages these.
    pub fn risk_delta(
        &self,
        candidate: f64,
        single: [f64; 2],
        reference: [f64; 2],
    ) -> Result<[f64; 2], &'static str> {
        self.validate()?;
        if ![candidate, single[0], single[1], reference[0], reference[1]]
            .iter()
            .all(|v| v.is_finite())
        {
            return Err("nonfinite delivered output/reference");
        }
        let r = [
            prediction(reference, weights(self.r, self.m[0])?),
            prediction(reference, weights(self.r, self.m[1])?),
        ];
        Ok(std::array::from_fn(|j| {
            (candidate - r[j]).powi(2) - (single[j] - r[j]).powi(2)
        }))
    }
}

pub fn whitened_energy(c: [[f64; 2]; 2], residual: [f64; 2]) -> Result<f64, &'static str> {
    if !c
        .iter()
        .flatten()
        .chain(residual.iter())
        .all(|v| v.is_finite())
        || c[0][1] != c[1][0]
    {
        return Err("nonfinite/asymmetric covariance");
    }
    let scale = c[0][0].max(c[1][1]);
    if scale <= 0. || c[0][0] <= scale * 1e-12 {
        return Err("singular covariance");
    }
    let l00 = c[0][0].sqrt();
    let l10 = c[1][0] / l00;
    let pivot = c[1][1] - l10 * l10;
    if pivot <= scale * 1e-12 {
        return Err("singular covariance");
    }
    let z0 = residual[0] / l00;
    let z1 = (residual[1] - l10 * z0) / pivot.sqrt();
    Ok((z0 * z0 + z1 * z1) / 2.)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn times() -> Times {
        Times {
            q: [0., 7.],
            v: [1., 6.],
            r: [2., 5.],
            m: [3., 4.],
        }
    }

    #[test]
    fn flat_variance_two_state_risk_independent_reference() {
        // Exhaust every sign combination of four INDEPENDENT errors. Exact
        // finite distribution; a noisy shared reference cancels in expectation.
        let mut mean = 0.;
        let sigma = 9.;
        for mask in 0..16 {
            let e: [f64; 4] =
                std::array::from_fn(|i| if mask & (1 << i) == 0 { -sigma } else { sigma });
            let m = [400. + e[0], 400. + e[1]];
            let d = times()
                .risk_delta((m[0] + m[1]) * 0.5, m, [400. + e[2], 400. + e[3]])
                .unwrap();
            mean += (d[0] + d[1]) * 0.5 / 16.;
        }
        assert!((mean + sigma * sigma / 2.).abs() < 1e-10);
    }

    #[test]
    fn noiseless_linear_drift_midpoint_is_flattering_but_two_state_penalizes() {
        let m = [130., 140.];
        let r = [120., 150.];
        let candidate = 135.;
        let d = times().risk_delta(candidate, m, r).unwrap();
        assert_eq!(d, [25., 25.]);
        let midpoint_delta = (candidate - 135f64).powi(2) - (m[0] - 135f64).powi(2);
        assert_eq!(midpoint_delta, -25.);
    }

    #[test]
    fn noise_and_drift_have_separate_known_contributions() {
        let sigma = 9.;
        let mut mean = 0.;
        for mask in 0..16 {
            let e: [f64; 4] =
                std::array::from_fn(|i| if mask & (1 << i) == 0 { -sigma } else { sigma });
            let m = [130. + e[0], 140. + e[1]];
            let d = times()
                .risk_delta((m[0] + m[1]) * 0.5, m, [120. + e[2], 150. + e[3]])
                .unwrap();
            mean += (d[0] + d[1]) * 0.5 / 16.;
        }
        assert!((mean - (-sigma * sigma / 2. + 25.)).abs() < 1e-10);
    }

    #[test]
    fn actual_timestamp_weights_reproduce_linear_physical_states() {
        let t = Times {
            q: [0., 15.601],
            v: [2.217, 13.374],
            r: [4.493, 11.159],
            m: [6.711, 8.932],
        };
        let f = |x: f64| 50. + x * 2.3;
        let single = t.m.map(f);
        let r = t.r.map(f);
        let d = t.risk_delta(single[0], single, r).unwrap();
        assert!(d[0].abs() < 1e-20);
        assert!((d[1] - (single[0] - single[1]).powi(2)).abs() < 1e-10);
    }

    #[test]
    fn full_covariance_detects_contrary_direction() {
        let c = [[1., 0.9], [0.9, 1.]];
        assert!((whitened_energy(c, [1., -1.]).unwrap() - 10.).abs() < 1e-10);
        assert!((whitened_energy(c, [1., 1.]).unwrap() - 1. / 1.9).abs() < 1e-10);
        assert!(whitened_energy([[0.; 2]; 2], [0.; 2]).is_err());
        assert!(whitened_energy([[1., 1.], [1., 1. + 1e-15]], [0.; 2]).is_err());
    }

    #[test]
    fn q_noise_correlation_is_in_validation_covariance() {
        let c = times().covariance([4., 9.], [16., 25.]).unwrap();
        assert!((c[0][1] - 78. / 49.).abs() < 1e-12);
        assert!((c[0][0] - (16. + 153. / 49.)).abs() < 1e-12);
        assert!((c[1][1] - (25. + 328. / 49.)).abs() < 1e-12);
    }

    #[test]
    fn role_overlap_extrapolation_and_invalid_outputs_refuse() {
        let mut t = times();
        t.m[0] = t.r[0];
        assert!(t.validate().is_err());
        assert!(weights([2., 5.], 6.).is_err());
        assert!(times().risk_delta(f64::NAN, [0.; 2], [0.; 2]).is_err());
        assert!(times().covariance([0., 1.], [1., 1.]).is_err());
    }
}
