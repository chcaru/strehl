//! Algebra/control checkpoint only. Not yet the complete warped image observer.
fn weights(nodes: &[f64], t: f64) -> Result<Vec<f64>, &'static str> {
    if nodes.len() < 3 || nodes.len() > 16 || !t.is_finite() || nodes.iter().any(|v| !v.is_finite())
    {
        return Err("invalid temporal design");
    }
    let basis = |x: f64| [1., (x - 4.) / 4., ((x - 4.) / 4.).powi(2)];
    let mut aug = [[0.; 6]; 3];
    for &x in nodes {
        let b = basis(x);
        for i in 0..3 {
            for j in 0..3 {
                aug[i][j] += b[i] * b[j];
            }
        }
    }
    for i in 0..3 {
        aug[i][3 + i] = 1.;
    }
    for col in 0..3 {
        let pivot = (col..3)
            .max_by(|&a, &b| aug[a][col].abs().total_cmp(&aug[b][col].abs()))
            .unwrap();
        if aug[pivot][col].abs() < 1e-12 {
            return Err("rank deficient temporal design");
        };
        aug.swap(pivot, col);
        let d = aug[col][col];
        for v in &mut aug[col] {
            *v /= d;
        }
        let row = aug[col];
        for (i, out) in aug.iter_mut().enumerate() {
            if i != col {
                let d = out[col];
                for j in 0..6 {
                    out[j] -= d * row[j];
                }
            }
        }
    }
    let b = basis(t);
    let v: [f64; 3] = std::array::from_fn(|j| (0..3).map(|i| b[i] * aug[i][3 + j]).sum());
    Ok(nodes
        .iter()
        .map(|&x| v.iter().zip(basis(x)).map(|(a, b)| a * b).sum())
        .collect())
}
fn predict(h: &[f64], values: &[f64]) -> f64 {
    h.iter().zip(values).map(|(h, v)| h * v).sum()
}
fn cov(h: &[f64], k: &[f64], variance: &[f64]) -> f64 {
    h.iter()
        .zip(k)
        .zip(variance)
        .map(|((h, k), v)| h * k * v)
        .sum()
}
fn normal(s: &mut u64) -> f64 {
    fn u(s: &mut u64) -> f64 {
        *s ^= *s << 13;
        *s ^= *s >> 7;
        *s ^= *s << 17;
        ((*s >> 11) as f64 + 0.5) / (1u64 << 53) as f64
    }
    (-2. * u(s).ln()).sqrt() * (std::f64::consts::TAU * u(s)).cos()
}
#[test]
fn a01_flat_first_preserves_signal_and_independent_reference_risk() {
    let q = [0., 4., 8.];
    for t in [1., 3., 5., 7., 9.] {
        assert!((predict(&weights(&q, t).unwrap(), &[1200.; 3]) - 1200.).abs() < 1e-9);
    }
    let mut rng = 20261028;
    let mut risk = 0.;
    let n = 100000;
    for _ in 0..n {
        let m = normal(&mut rng);
        let w = normal(&mut rng);
        let r = normal(&mut rng);
        let a = 0.5 * (m + w);
        risk += (a - r).powi(2) - (m - r).powi(2);
    }
    risk /= n as f64;
    assert!((risk + 0.5).abs() < 0.025, "{risk}");
}
#[test]
fn a02_quadratic_prediction_matches_independent_lagrange_oracle() {
    for t in [-1., 1., 3., 5., 7., 9., 11.] {
        let expected = [
            (t - 4.) * (t - 8.) / 32.,
            -t * (t - 8.) / 16.,
            t * (t - 4.) / 32.,
        ];
        let actual = weights(&[0., 4., 8.], t).unwrap();
        for i in 0..3 {
            assert!((actual[i] - expected[i]).abs() < 1e-12);
        }
    }
    let r = [-2., 2., 6., 10.];
    for t in [1., 3., 5., 7., 9.] {
        let values = r.map(|x| 13. + 2.7 * x - 0.38 * x * x);
        assert!(
            (predict(&weights(&r, t).unwrap(), &values) - (13. + 2.7 * t - 0.38 * t * t)).abs()
                < 1e-10
        );
    }
}
#[test]
fn a03_shared_prediction_covariance_is_retained() {
    let h = weights(&[0., 4., 8.], 1.).unwrap();
    let k = weights(&[0., 4., 8.], 5.).unwrap();
    let v = [7., 13., 19.];
    let expected = cov(&h, &k, &v);
    assert!(expected.abs() > 0.5);
    let mut rng = 53139;
    let mut xy = 0.;
    let n = 100000;
    for _ in 0..n {
        let e = v.map(|x| normal(&mut rng) * x.sqrt());
        xy += predict(&h, &e) * predict(&k, &e);
    }
    assert!((xy / n as f64 - expected).abs() < 0.08);
    let d: Vec<_> = h.iter().zip(&k).map(|(a, b)| a - b).collect();
    assert!((cov(&d, &d, &v) - (cov(&h, &h, &v) + cov(&k, &k, &v) - 2. * expected)).abs() < 1e-10);
}
#[test]
fn b01_shared_weight_reference_photons_create_false_risk_gain() {
    let mut rng = 123456789;
    let mut shared = 0.;
    let mut independent = 0.;
    let n = 100000;
    for _ in 0..n {
        let m = normal(&mut rng);
        let w = normal(&mut rng);
        let r = normal(&mut rng);
        let a = 0.5 * (m + w);
        shared += (a - w).powi(2) - (m - w).powi(2);
        independent += (a - r).powi(2) - (m - r).powi(2);
    }
    let shared = shared / n as f64;
    let independent = independent / n as f64;
    assert!((shared + 1.5).abs() < 0.03);
    assert!((independent + 0.5).abs() < 0.03);
    assert!(shared < independent - 0.9);
}
#[test]
fn b02_reference_driven_survivor_selection_can_reverse_risk_sign() {
    let mut rng = 765492551;
    let mut leaked = 0.;
    let mut clean = 0.;
    let mut nl = 0;
    let mut nc = 0;
    for _ in 0..200000 {
        let m = normal(&mut rng);
        let r = normal(&mut rng);
        let q = normal(&mut rng);
        let risk = (m + 1. - r).powi(2) - (m - r).powi(2);
        if r > 0. {
            leaked += risk;
            nl += 1;
        }
        if q > 0. {
            clean += risk;
            nc += 1;
        }
    }
    let leaked = leaked / nl as f64;
    let clean = clean / nc as f64;
    assert!(leaked < -0.5);
    assert!((clean - 1.).abs() < 0.04);
}
#[test]
fn b03_model_bias_does_not_cancel_with_independent_target_noise() {
    let mu = 0f64;
    let a = 1f64;
    let b = 0f64;
    let true_risk = (a - mu).powi(2) - (b - mu).powi(2);
    let biased_reference = 1f64;
    let apparent = (a - biased_reference).powi(2) - (b - biased_reference).powi(2);
    assert_eq!(true_risk, 1.);
    assert_eq!(apparent, -1.);
    assert_eq!(apparent, true_risk - 2. * (biased_reference - mu) * (a - b));
}
#[test]
fn b04_out_of_model_curvature_must_remain_observable_on_validation() {
    let q = [0., 4., 8.];
    let values = q.map(|x| 100. + 0.1 * x * x * x);
    let residual: Vec<_> = [1., 5., 9.]
        .iter()
        .map(|&t| predict(&weights(&q, t).unwrap(), &values) - (100. + 0.1 * t * t * t))
        .collect();
    assert!(residual.iter().any(|v| v.abs() > 4.));
    // A measurement-only fit would erase these errors; the observer must never do that.
    let first = weights(&q, 3.).unwrap();
    let second = weights(&q, 7.).unwrap();
    assert!(predict(&first, &values).is_finite() && predict(&second, &values).is_finite());
}
#[test]
fn b05_data_roles_are_globally_disjoint() {
    use std::collections::BTreeSet;
    let roles: [&[i32]; 5] = [&[0, 4, 8], &[1, 5, 9], &[-2, 2, 6, 10], &[-1, 11], &[3, 7]];
    let sets: Vec<BTreeSet<_>> = roles
        .iter()
        .map(|d| {
            [36, 76, 116, 156, 196, 236]
                .into_iter()
                .flat_map(|b| d.iter().map(move |x| b + x))
                .collect()
        })
        .collect();
    for i in 0..5 {
        for j in i + 1..5 {
            assert!(sets[i].is_disjoint(&sets[j]));
        }
    }
    assert_eq!(sets.iter().map(BTreeSet::len).sum::<usize>(), 84);
}
#[test]
fn b06_invalid_temporal_design_refuses() {
    assert!(weights(&[0., 0., 0.], 1.).is_err());
    assert!(weights(&[0., 4.], 1.).is_err());
    assert!(weights(&[0., 4., 8.], f64::NAN).is_err());
}
