//! Experiment-only estimator-specific repeat compatibility; NOT a sharpness,
//! depth or universal PSF certificate. No camera estimation or image I/O.
//! Caller must supply exact frozen-guide original-tap covariances, two distinct
//! acquisitions, disjoint point footprints, and separate declared patches/colors.
//! Gaussian quadratic envelopes are a commissioning instrument. Shared guide /
//! fitted geometry and quantized shot noise preclude a literal real-data p-value.
#[derive(Clone, Copy, Debug)]
pub struct PairSample {
    pub x: [f64; 3],
    pub y: [f64; 3],
    pub covariance_x: [[f64; 3]; 3],
    pub covariance_y: [[f64; 3]; 3],
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    Compatible,
    Incompatible,
    Unknown,
}
#[derive(Clone, Copy, Debug)]
pub struct Interval {
    pub lower: f64,
    pub upper: f64,
}
#[derive(Clone, Debug)]
pub struct BandEvidence {
    pub band: usize,
    pub signal_x: Option<Interval>,
    pub signal_y: Option<Interval>,
    pub signal_difference: Option<Interval>,
    pub signed_cross: Option<Interval>,
    pub y_from_x_amplitude: Option<Interval>,
    pub x_from_y_amplitude: Option<Interval>,
    pub difference_cost_to_equal_noise_benefit: Option<Interval>,
    pub decision: Decision,
}
#[derive(Clone, Debug)]
pub struct Evidence {
    pub points: usize,
    pub bands: Vec<BandEvidence>,
    pub joint_difference_to_noise: Option<Interval>,
    /// Native identity=high+mid+low, including every covariance cross-term.
    pub identity_difference_to_noise: Option<Interval>,
    pub decision: Decision,
}
#[derive(Clone, Copy, Debug)]
pub struct Policy {
    pub minimum_points: usize,
    pub envelope_t: f64,
    pub loss_budget_fraction: f64,
    pub amplitude_margin: f64,
}
impl Default for Policy {
    fn default() -> Self {
        Self {
            minimum_points: 64,
            envelope_t: 4.605170185988092,
            loss_budget_fraction: 0.5,
            amplitude_margin: 0.05,
        }
    }
}
#[derive(Clone, Copy, Default)]
struct Moments {
    observed: f64,
    trace: f64,
    frobenius2: f64,
    operator_bound: f64,
}
fn covariance_valid(c: &[[f64; 3]; 3]) -> bool {
    if !c.iter().flatten().all(|v| v.is_finite()) {
        return false;
    }
    let scale = c.iter().flatten().map(|v| v.abs()).fold(0., f64::max);
    if scale == 0. {
        return true;
    }
    let a = std::array::from_fn::<_, 3, _>(|i| std::array::from_fn::<_, 3, _>(|j| c[i][j] / scale));
    for i in 0..3 {
        if a[i][i] < 0. {
            return false;
        }
        for j in 0..3 {
            if (a[i][j] - a[j][i]).abs() > 1e-12 {
                return false;
            }
        }
    }
    for i in 0..3 {
        for j in i + 1..3 {
            if a[i][i] * a[j][j] - a[i][j] * a[i][j] < -1e-12 {
                return false;
            }
        }
    }
    let det = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
    det >= -1e-12
}
impl Moments {
    fn scalar(&mut self, x: f64, v: f64) {
        self.observed += x * x;
        self.trace += v;
        self.frobenius2 += v * v;
        self.operator_bound = self.operator_bound.max(v);
    }
    fn vector(&mut self, x: [f64; 3], c: [[f64; 3]; 3]) {
        self.observed += x.iter().map(|v| v * v).sum::<f64>();
        self.trace += (0..3).map(|i| c[i][i]).sum::<f64>();
        self.frobenius2 += c.iter().flatten().map(|v| v * v).sum::<f64>();
        self.operator_bound = self.operator_bound.max(
            c.iter()
                .map(|r| r.iter().map(|v| v.abs()).sum::<f64>())
                .fold(0., f64::max),
        );
    }
    fn interval(self, t: f64) -> Option<Interval> {
        let z = self.observed - self.trace;
        let v = self.operator_bound;
        let a = self.frobenius2;
        if v == 0. {
            return Some(Interval {
                lower: self.observed,
                upper: self.observed,
            });
        }
        let rad = t * (a + 2. * v * z + 4. * t * v * v);
        if rad < 0. || !rad.is_finite() {
            return None;
        }
        let upper = z + 4. * t * v + 2. * rad.sqrt();
        if upper < 0. {
            return None;
        }
        let q = z - 2. * v * t;
        let lower = if q <= 2. * (t * a).sqrt() {
            0.
        } else {
            let r = t * (a + 2. * v * q + 4. * t * v * v);
            if r < 0. {
                return None;
            }
            (q + 4. * t * v - 2. * r.sqrt()).max(0.)
        };
        if !lower.is_finite() || !upper.is_finite() || lower > upper {
            return None;
        }
        Some(Interval { lower, upper })
    }
}
fn combine(a: Decision, b: Decision) -> Decision {
    if a == Decision::Incompatible || b == Decision::Incompatible {
        Decision::Incompatible
    } else if a == Decision::Unknown || b == Decision::Unknown {
        Decision::Unknown
    } else {
        Decision::Compatible
    }
}
fn upper_gate(v: Option<Interval>, bar: f64) -> Decision {
    match v {
        Some(i) if i.upper <= bar => Decision::Compatible,
        Some(i) if i.lower > bar => Decision::Incompatible,
        _ => Decision::Unknown,
    }
}
fn ratio(num: Option<Interval>, den: Option<Interval>) -> Option<Interval> {
    let n = num?;
    let d = den?;
    if d.lower <= 0. || n.lower <= 0. {
        return None;
    }
    Some(Interval {
        lower: n.lower / d.upper,
        upper: n.upper / d.lower,
    })
}
fn transfer_gate(v: Option<Interval>, margin: f64) -> Decision {
    match v {
        Some(i) if i.lower >= 1. - margin && i.upper <= 1. + margin => Decision::Compatible,
        Some(i) if i.upper < 1. - margin || i.lower > 1. + margin => Decision::Incompatible,
        _ => Decision::Unknown,
    }
}
fn loss_ratio(i: Option<Interval>, noise: f64) -> Option<Interval> {
    let i = i?;
    if noise == 0. {
        return if i.upper == 0. {
            Some(Interval {
                lower: 0.,
                upper: 0.,
            })
        } else {
            None
        };
    }
    Some(Interval {
        lower: i.lower / noise,
        upper: i.upper / noise,
    })
}
pub fn evaluate(points: &[PairSample], policy: Policy) -> Result<Evidence, &'static str> {
    if points.len() > 1024
        || policy.minimum_points < 2
        || policy.minimum_points > 1024
        || !policy.envelope_t.is_finite()
        || policy.envelope_t <= 0.
        || !policy.loss_budget_fraction.is_finite()
        || !(0.0..=1.0).contains(&policy.loss_budget_fraction)
        || !policy.amplitude_margin.is_finite()
        || !(0.0..=0.5).contains(&policy.amplitude_margin)
    {
        return Err("invalid bounded policy");
    }
    let mut x = [Moments::default(); 3];
    let mut y = x;
    let mut difference = x;
    let mut sum = x;
    let mut joint = Moments::default();
    let mut identity = Moments::default();
    for p in points {
        if !p.x.iter().chain(&p.y).all(|v| v.is_finite())
            || !covariance_valid(&p.covariance_x)
            || !covariance_valid(&p.covariance_y)
        {
            return Err("invalid value/full within-point covariance");
        }
        let c = std::array::from_fn(|i| {
            std::array::from_fn(|j| p.covariance_x[i][j] + p.covariance_y[i][j])
        });
        joint.vector(std::array::from_fn(|i| p.x[i] - p.y[i]), c);
        let identity_variance: f64 = c.iter().flatten().sum();
        if identity_variance < 0. {
            return Err("negative identity variance");
        }
        identity.scalar(
            p.x.iter().sum::<f64>() - p.y.iter().sum::<f64>(),
            identity_variance,
        );
        for b in 0..3 {
            x[b].scalar(p.x[b], p.covariance_x[b][b]);
            y[b].scalar(p.y[b], p.covariance_y[b][b]);
            difference[b].scalar(p.x[b] - p.y[b], c[b][b]);
            sum[b].scalar(p.x[b] + p.y[b], c[b][b]);
        }
    }
    let mut bands = Vec::new();
    let mut decision = if points.len() >= policy.minimum_points {
        Decision::Compatible
    } else {
        Decision::Unknown
    };
    for b in 0..3 {
        let ex = x[b].interval(policy.envelope_t);
        let ey = y[b].interval(policy.envelope_t);
        let ed = difference[b].interval(policy.envelope_t);
        let es = sum[b].interval(policy.envelope_t);
        let cross = match (es, ed) {
            (Some(s), Some(d)) => Some(Interval {
                lower: (s.lower - d.upper) * 0.25,
                upper: (s.upper - d.lower) * 0.25,
            }),
            _ => None,
        };
        let yx = ratio(cross, ex);
        let xy = ratio(cross, ey);
        let loss = loss_ratio(ed, difference[b].trace);
        let mut state = upper_gate(loss, policy.loss_budget_fraction);
        // lowband carries raw-gain brightness consistency; only AC mid/high license
        // transfer. Both AC bands must have positive identified signal energy.
        if b != 2 {
            state = combine(
                state,
                combine(
                    transfer_gate(yx, policy.amplitude_margin),
                    transfer_gate(xy, policy.amplitude_margin),
                ),
            );
        }
        decision = combine(decision, state);
        bands.push(BandEvidence {
            band: b,
            signal_x: ex,
            signal_y: ey,
            signal_difference: ed,
            signed_cross: cross,
            y_from_x_amplitude: yx,
            x_from_y_amplitude: xy,
            difference_cost_to_equal_noise_benefit: loss,
            decision: state,
        });
    }
    let joint_ratio = loss_ratio(joint.interval(policy.envelope_t), joint.trace);
    decision = combine(
        decision,
        upper_gate(joint_ratio, policy.loss_budget_fraction),
    );
    let identity_ratio = loss_ratio(identity.interval(policy.envelope_t), identity.trace);
    decision = combine(
        decision,
        upper_gate(identity_ratio, policy.loss_budget_fraction),
    );
    Ok(Evidence {
        identity_difference_to_noise: identity_ratio,
        points: points.len(),
        bands,
        joint_difference_to_noise: joint_ratio,
        decision,
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    fn gaussian(s: &mut u64) -> f64 {
        fn unit(s: &mut u64) -> f64 {
            *s = s
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((*s >> 11) as f64 + 0.5) / (1u64 << 53) as f64
        }
        let a = unit(s);
        let b = unit(s);
        (-2. * a.ln()).sqrt() * (std::f64::consts::TAU * b).cos()
    }
    fn plant(seed: u64, amplitude: f64, scale: f64, sign: f64) -> Vec<PairSample> {
        let mut r = seed;
        (0..256)
            .map(|i| {
                let s = [
                    amplitude * (i as f64 * 0.71).sin(),
                    amplitude * (i as f64 * 0.39).cos(),
                    400.,
                ];
                let correlated = |r: &mut u64| {
                    let z = [gaussian(r), gaussian(r), gaussian(r)];
                    let l11 = 0.96f64.sqrt();
                    let l21 = 0.08 / l11;
                    [
                        z[0],
                        0.2 * z[0] + l11 * z[1],
                        0.1 * z[0] + l21 * z[1] + (1. - 0.01 - l21 * l21).sqrt() * z[2],
                    ]
                };
                let nx = correlated(&mut r);
                let ny = correlated(&mut r);
                let x = std::array::from_fn(|b| s[b] + nx[b]);
                let y =
                    std::array::from_fn(|b| s[b] * if b < 2 { scale * sign } else { 1. } + ny[b]);
                let cov = [[1., 0.2, 0.1], [0.2, 1., 0.1], [0.1, 0.1, 1.]];
                PairSample {
                    x,
                    y,
                    covariance_x: cov,
                    covariance_y: cov,
                }
            })
            .collect()
    }
    #[test]
    fn flat_lowpower_is_unknown() {
        let e = evaluate(&plant(91, 0., 1., 1.), Policy::default()).unwrap();
        assert_ne!(e.decision, Decision::Compatible);
        assert!(e.bands[0].y_from_x_amplitude.is_none());
    }
    #[test]
    fn finite_noise_same_signal_census_not_universal_admission() {
        let mut admitted = 0;
        let mut unknown = 0;
        for seed in 64..80 {
            let e = evaluate(&plant(seed, 100., 1., 1.), Policy::default()).unwrap();
            println!("same-signal seed{seed} {:?}", e.decision);
            match e.decision {
                Decision::Compatible => admitted += 1,
                Decision::Unknown => unknown += 1,
                Decision::Incompatible => {
                    panic!("controlled same signal was incompatible at{seed}: {e:?}")
                }
            }
        }
        println!("same-signal admitted{admitted}/16 unknown{unknown}/16");
        assert!(
            admitted > 0 && unknown > 0,
            "Report power, never turn a finite-noise unknown into an admission"
        );
        let foil = evaluate(&plant(65, 100., 1., 1.), Policy::default()).unwrap();
        assert_eq!(foil.decision, Decision::Unknown);
        assert!(
            foil.bands[1]
                .difference_cost_to_equal_noise_benefit
                .unwrap()
                .upper
                > 0.5
        );
    }
    #[test]
    fn exact_identical_signal_positive_has_no_noise_bound() {
        let mut p = plant(64, 100., 1., 1.);
        for point in &mut p {
            point.y = point.x;
            point.covariance_x = [[0.; 3]; 3];
            point.covariance_y = [[0.; 3]; 3];
        }
        let e = evaluate(&p, Policy::default()).unwrap();
        assert_eq!(e.decision, Decision::Compatible);
    }
    #[test]
    fn attenuation_and_opposite_texture_are_not_admitted() {
        for scale in [0.5, 0.9] {
            let e = evaluate(&plant(51, 100., scale, 1.), Policy::default()).unwrap();
            assert_eq!(e.decision, Decision::Incompatible);
        }
        let e = evaluate(&plant(51, 100., 1., -1.), Policy::default()).unwrap();
        assert_eq!(e.decision, Decision::Incompatible);
    }
    #[test]
    fn boundary_transfer_is_unknown_not_forced() {
        let e = evaluate(&plant(51, 100., 0.95, 1.), Policy::default()).unwrap();
        assert_ne!(e.decision, Decision::Compatible);
    }
    #[test]
    fn missing_points_and_covariance_refuse() {
        let mut p = plant(51, 100., 1., 1.);
        assert_ne!(
            evaluate(&p[..4], Policy::default()).unwrap().decision,
            Decision::Compatible
        );
        p[0].covariance_x[0][1] = 3.;
        assert!(evaluate(&p, Policy::default()).is_err());
        assert!(evaluate(&vec![p[1]; 1025], Policy::default()).is_err());
    }
    #[test]
    fn full_band_covariance_affects_joint_envelope() {
        let p = plant(51, 100., 1., 1.);
        let mut q = p.clone();
        for s in &mut q {
            s.covariance_x = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]];
            s.covariance_y = s.covariance_x;
        }
        let a = evaluate(&p, Policy::default()).unwrap();
        let b = evaluate(&q, Policy::default()).unwrap();
        assert_ne!(
            a.joint_difference_to_noise.unwrap().upper.to_bits(),
            b.joint_difference_to_noise.unwrap().upper.to_bits()
        );
    }
    #[test]
    fn cancelled_identity_noise_does_not_license_native_mean() {
        let mut p = plant(64, 100., 1., 1.);
        let mut rng = 17;
        for (i, v) in p.iter_mut().enumerate() {
            let z = gaussian(&mut rng);
            let w = gaussian(&mut rng);
            let a = 100. * (i as f64 * 0.7).sin();
            let b = 100. * (i as f64 * 0.3).cos();
            v.x = [a + z, b - z, 400.];
            v.y = [a + w + 0.001, b - w + 0.001, 400.];
            v.covariance_x = [[1., -1., 0.], [-1., 1., 0.], [0., 0., 0.]];
            v.covariance_y = v.covariance_x;
        }
        let e = evaluate(&p, Policy::default()).unwrap();
        assert!(e.identity_difference_to_noise.is_none());
        assert_ne!(e.decision, Decision::Compatible);
    }
}
