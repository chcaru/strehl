use super::*;
fn support() -> Vec<([f32; 2], f32)> {
    let mut out = Vec::new();
    for y in -3..=3 {
        for x in -3..=3 {
            let p = [x as f32 * 0.31 + 0.11, y as f32 * 0.29 - 0.07];
            if !(x < 0 && y < 1) {
                out.push((
                    p,
                    (-0.5 * (p[0] * p[0] + p[1] * p[1]) / (0.35 * 0.35)).exp(),
                ));
            }
        }
    }
    out
}
fn uniform(mut x: u64) -> f32 {
    x = x.wrapping_add(0x9e3779b97f4a7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d049bb133111eb);
    x ^= x >> 31;
    ((x >> 40) as f32 / 16777216.) * 2. - 1.
}
#[test]
fn a01_flat_first_temporal_mean_and_propagated_variance() {
    let sites = support();
    let mut values = Vec::new();
    let mut predicted = 0.;
    for realization in 0..4096 {
        let mut m = Moments::default();
        for (i, &(d, w)) in sites.iter().enumerate() {
            let noise = 3f32.sqrt() * 4. * uniform((realization * sites.len() + i) as u64);
            m.add(d, 1000. + noise, w, 16.).unwrap();
        }
        let e = m.solve(1e-6).unwrap();
        values.push(e.value as f64);
        predicted = e.variance as f64;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let variance =
        values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (values.len() - 1) as f64;
    assert!((mean - 1000.).abs() < 0.08, "mean{mean}");
    assert!(
        (variance / predicted - 1.).abs() < 0.06,
        "temporal{variance} vs conditional{predicted}"
    );
}
#[test]
fn b01_irregular_color_linear_fields_reproduce_without_centroid_shift() {
    let sites = support();
    for slope in [[400., -100.], [-300., 350.], [100., 250.]] {
        let mut m = Moments::default();
        let mut constant = 0.;
        let mut wsum = 0.;
        for &(d, w) in &sites {
            let value = 1000. + slope[0] * d[0] + slope[1] * d[1];
            m.add(d, value, w, 16.).unwrap();
            constant += w * value;
            wsum += w;
        }
        let e = m.solve(1e-6).unwrap();
        assert!((e.value - 1000.).abs() < 0.002, "{e:?}");
        assert!((constant / wsum - 1000.).abs() > 5.);
        assert!(e.within_observed_hull());
        let mut moments = [0.; 3];
        for &(d, w) in &sites {
            let h = e.influence(d, w);
            moments[0] += h;
            moments[1] += h * d[0];
            moments[2] += h * d[1];
        }
        assert!(
            (moments[0] - 1.).abs() < 2e-6 && moments[1].abs() < 2e-6 && moments[2].abs() < 2e-6,
            "{moments:?}"
        );
    }
}
#[test]
fn b02_exact_influence_variance_and_gain_squared() {
    let sites = support();
    let mut first = Moments::default();
    let mut second = Moments::default();
    for &(d, w) in &sites {
        first.add(d, 1000. + 30. * d[0], w, 16.).unwrap();
        second.add(d, 2. * (1000. + 30. * d[0]), w, 64.).unwrap();
    }
    let a = first.solve(1e-6).unwrap();
    let b = second.solve(1e-6).unwrap();
    let propagated: f32 = sites
        .iter()
        .map(|&(d, w)| a.influence(d, w).powi(2) * 16.)
        .sum();
    assert!((propagated / a.variance - 1.).abs() < 2e-6);
    assert!((b.value / a.value - 2.).abs() < 1e-6);
    assert!((b.variance / a.variance - 4.).abs() < 1e-6);
}
#[test]
fn c01_rank_deficiency_and_invalid_observations_refuse() {
    let mut m = Moments::default();
    for x in -3..=3 {
        m.add([x as f32, 0.], 1000., 1., 16.).unwrap();
    }
    assert!(m.solve(1e-6).is_none());
    let mut m = Moments::default();
    assert!(m.add([0., f32::NAN], 1000., 1., 16.).is_err());
    assert!(m.add([0., 0.], 1000., -1., 16.).is_err());
    assert!(m.add([0., 0.], 1000., 1., -16.).is_err());
}
#[test]
fn c02_negative_influence_ringing_is_visible_to_exact_hull_guard() {
    let sites = support();
    let mut template = Moments::default();
    for &(d, w) in &sites {
        template.add(d, 1000., w, 16.).unwrap();
    }
    let t = template.solve(1e-6).unwrap();
    assert!(sites.iter().any(|&(d, w)| t.influence(d, w) < -1e-4));
    // A planted edge partitions by the signed influence, maximizing overshoot.
    let mut m = Moments::default();
    for &(d, w) in &sites {
        m.add(d, if t.influence(d, w) > 0. { 1000. } else { 0. }, w, 16.)
            .unwrap();
    }
    let e = m.solve(1e-6).unwrap();
    assert!(e.value > 1000.1, "{e:?}");
    assert!(!e.within_observed_hull());
}
#[test]
fn c03_zero_weight_remote_sites_cannot_change_the_operator() {
    let mut a = Moments::default();
    for (d, w) in support() {
        a.add(d, 1000. + d[0] * 100., w, 16.).unwrap();
    }
    let mut b = a;
    b.add([1000., -1000.], 1e6, 0., 1e4).unwrap();
    let a = a.solve(1e-6).unwrap();
    let b = b.solve(1e-6).unwrap();
    assert_eq!(a.value.to_bits(), b.value.to_bits());
    assert_eq!(a.variance.to_bits(), b.variance.to_bits());
    assert_eq!(a.samples, b.samples);
}
