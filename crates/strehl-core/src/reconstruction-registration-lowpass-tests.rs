use super::*;
fn impulse() -> Patch {
    let mut values = vec![0.; 25 * 25];
    values[12 * 25 + 12] = 1.;
    Patch {
        origin: [0, 0],
        geometry: PlaneGeometry {
            width: 25,
            height: 25,
        },
        values,
        valid: vec![true; 25 * 25],
        variance: 17.5,
        gradient_variance: 8.75,
        pull: Similarity::IDENTITY,
    }
}
#[test]
fn a01_geometry_filter_variance_matches_independent_impulse_energy() {
    for sigma in [0., 0.4, 1.2, 1.8] {
        let kernel = geometry_kernel(sigma).unwrap();
        let mut p = impulse();
        geometry_lowpass(&mut p, &kernel);
        let energy: f64 = p.values.iter().map(|v| f64::from(*v).powi(2)).sum();
        let mut derivative_energy = 0f64;
        for y in 1..24 {
            for x in 1..24 {
                let i = y * 25 + x;
                derivative_energy += (0.5 * f64::from(p.values[i + 1] - p.values[i - 1])).powi(2);
            }
        }
        assert!(
            (f64::from(p.variance) - 17.5 * energy).abs() < 2e-5,
            "sigma{sigma}"
        );
        assert!(
            (f64::from(p.gradient_variance) - 17.5 * derivative_energy).abs() < 2e-5,
            "sigma{sigma}"
        );
    }
}
#[test]
fn c01_geometry_filter_never_uses_poisoned_or_missing_taps() {
    let kernel = geometry_kernel(1.2).unwrap();
    let radius = kernel.len() / 2;
    let mut p = impulse();
    p.valid[12 * 25 + 12] = false;
    p.values[12 * 25 + 12] = f32::NAN;
    geometry_lowpass(&mut p, &kernel);
    for y in 0..25 {
        for x in 0..25 {
            let border = x < radius || y < radius || x + radius >= 25 || y + radius >= 25;
            let poisoned = x.abs_diff(12) <= radius && y.abs_diff(12) <= radius;
            assert_eq!(p.valid[y * 25 + x], !border && !poisoned, "{x},{y}");
            assert!(p.values[y * 25 + x].is_finite());
        }
    }
    for sigma in [f32::NAN, -0.1, 3.1, f32::INFINITY] {
        assert!(geometry_kernel(sigma).is_err());
    }
}
