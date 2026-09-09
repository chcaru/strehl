// Independently authored controls. Root executes; no fixture radiance is imported.
use super::{apply_estimate, cell_moments, point_moments, NormalSystem, Refusal};

fn close(actual: f32, expected: f64, tolerance: f64, label: &str) {
    assert!(actual.is_finite(), "{label}: nonfinite {actual}");
    assert!((actual as f64 - expected).abs() <= tolerance,
        "{label}: actual={actual}, expected={expected}, tolerance={tolerance}");
}

fn literal_system(coefficients: [f32; 6]) -> NormalSystem {
    let mut system = NormalSystem::new();
    // Two independent surfaces, symmetric 2-D sample positions and known weights.
    for variance in [1.0, 2.0, 4.0] {
        for surface in 0..2 {
            for x in [-1.0, 1.0] {
                for y in [-1.0, 1.0] {
                    let i = 3 * surface;
                    let mut row = [0.0; 6];
                    row[i] = 1.0;
                    row[i + 1] = x;
                    row[i + 2] = y;
                    let observed = coefficients[i] + x * coefficients[i + 1]
                        + y * coefficients[i + 2];
                    assert!(system.add(row, observed, variance));
                }
            }
        }
    }
    system
}

fn affine_and_refusal_controls() {
    let planted = [3000.0, 2.0, -3.0, 1500.0, -1.0, 4.0];
    let q = [0.5, 0.125, 0.0, 0.5, -0.125, 0.0];
    let mut system = literal_system(planted);
    let fit = system.solve(q).expect("full-rank affine fit must be accepted");
    for i in 0..6 { close(fit.coefficients[i], planted[i] as f64, 0.003, "affine coefficient"); }
    close(fit.value, 2250.375, 0.003, "unit-cell affine target");
    // N = 7 I by literal rows/weights; q^T q = 17/32.
    close(fit.variance, 17.0 / 224.0, 2e-5, "independent target variance");
    assert_eq!(fit.observations, 24);
    assert!(fit.min_pivot >= 1e-4);
    assert!(fit.normalized_residual.is_finite());
    let constant = literal_system([40.0, 0.0, 0.0, 10.0, 0.0, 0.0]).solve(q).unwrap();
    close(constant.value, 25.0, 1e-4, "distinct constant layers");
    assert!((fit.value - 2250.0).abs() > 0.3, "alpha-only destroyer is inert");

    let mut destination = -123.0;
    assert!(apply_estimate(&mut destination, Some(&fit)), "accepted correction not applied");
    assert_eq!(destination.to_bits(), fit.value.to_bits());
    for bits in [0_u32, 0x8000_0000, 0x7fc0_1234, 0x7f80_0000, 512.25_f32.to_bits()] {
        let mut untouched = f32::from_bits(bits);
        assert!(!apply_estimate(&mut untouched, None));
        assert_eq!(untouched.to_bits(), bits, "no-treatment changed bits");
    }
    // Invalid observations must not silently modify count or sufficient statistics.
    for (row, value, variance) in [([f32::NAN; 6], 1.0, 1.0),
        ([1.0; 6], f32::NAN, 1.0), ([1.0; 6], 1.0, 0.0),
        ([1.0; 6], 1.0, -1.0), ([1.0; 6], 1.0, f32::INFINITY)] {
        assert!(!system.add(row, value, variance));
    }
    let unchanged = system.solve(q).unwrap();
    assert_eq!(unchanged.observations, fit.observations);
    assert_eq!(unchanged.value.to_bits(), fit.value.to_bits());
    assert_eq!(unchanged.variance.to_bits(), fit.variance.to_bits());
    for i in 0..6 { assert_eq!(unchanged.coefficients[i].to_bits(), fit.coefficients[i].to_bits()); }
    assert!(matches!(NormalSystem::new().solve(q), Err(Refusal::InsufficientObservations)));
    let mut identical = NormalSystem::new();
    let mut missing_layer = NormalSystem::new();
    for i in 0..24 {
        assert!(identical.add([0.5, 0.0, 0.0, 0.5, 0.0, 0.0], 25.0, 1.0));
        assert!(missing_layer.add([1.0, (i % 3) as f32 - 1.0,
            (i / 3 % 3) as f32 - 1.0, 0.0, 0.0, 0.0], 40.0, 1.0));
    }
    assert!(matches!(identical.solve(q), Err(Refusal::RankDeficient)));
    assert!(matches!(missing_layer.solve(q), Err(Refusal::RankDeficient)));
    assert!(matches!(system.solve([0.0, 4.0, 0.0, 0.0, 0.0, 0.0]), Err(Refusal::ExcessVariance)));
    assert!(matches!(literal_system([-20.0, 0.0, 0.0, -10.0, 0.0, 0.0]).solve(q), Err(Refusal::NegativeEstimate)));

    // The fixed threshold is the normalized Schur pivot, BEFORE square root.
    // Four orthogonal columns and a two-column block with correlation rho.
    // For that block the second normalized Schur pivot is 1-rho^2.
    for (planted_pivot, should_accept) in [(5e-5_f32, false), (2e-4_f32, true)] {
        let rho = (1.0 - planted_pivot).sqrt();
        let root = planted_pivot.sqrt();
        let mut edge = NormalSystem::new();
        for _ in 0..2 {
            for i in 0..4 {
                let mut row = [0.0; 6]; row[i] = 1.0;
                assert!(edge.add(row, if i == 0 { 50.0 } else { 0.0 }, 1.0));
            }
            assert!(edge.add([0.0, 0.0, 0.0, 0.0, 1.0, rho], 0.0, 1.0));
            assert!(edge.add([0.0, 0.0, 0.0, 0.0, 0.0, root], 0.0, 1.0));
        }
        let result = edge.solve([1.0, 0.0, 0.0, 0.0, 0.0, 0.0]);
        if should_accept {
            let accepted = result.expect("pivot above frozen Schur threshold must pass");
            close(accepted.value, 50.0, 0.01, "threshold positive control");
            close(accepted.min_pivot, planted_pivot as f64, 2e-6, "reported Schur pivot");
        } else {
            assert!(matches!(result, Err(Refusal::RankDeficient)), "below-threshold pivot escaped");
        }
    }
}

fn literal_moment_controls() {
    let m = 2.0 / (3.0 * std::f64::consts::PI);
    for df in [-2.0_f32, 2.0] {
        let sign = if df < 0.0 { -1.0 } else { 1.0 };
        let row = point_moments([1.0, 0.0], 0.0, df, 3.0, [0.0, 0.0], [0.0, 0.0]);
        let expected = [0.5, 2.0*m, 0.0, 0.5, -3.0*sign*m, 0.0];
        for i in 0..6 { close(row[i], expected[i], 3e-6, "literal shared half-disc"); }
        // Independent marginal averaging would set this to zero; same-ray visibility cannot.
        assert!(row[4].abs() > 0.6, "background shared-ray covariance power missing");
    }
    for (source, expected) in [([0.0, 0.0], [0.5, 0.125, 0.0, 0.5, -0.125, 0.0]),
        ([0.25, 0.375], [0.75, 0.28125, 0.28125, 0.25, -0.03125, 0.09375])] {
        let row = cell_moments([1.0, 0.0], 0.0, 0.0, 6.0, source, [0.0, 0.0]);
        for i in 0..6 { close(row[i], expected[i], 3e-6, "literal clipped-cell moments"); }
    }
    let full = cell_moments([1.0, 0.0], 0.0, -2.0, 3.0, [4.0, 2.0], [1.0, 1.0]);
    for (a, b) in full.into_iter().zip([1.0, 3.0, 1.0, 0.0, 0.0, 0.0]) {
        close(a, b, 3e-6, "full foreground affine location");
    }
    let correct = cell_moments([1.0, -0.15], 142.0, -3.0, 3.0, [160.0, 120.0], [160.0, 120.0]);
    let shifted = cell_moments([1.0, -0.15], 146.0, -3.0, 3.0, [160.0, 120.0], [160.0, 120.0]);
    assert!((correct[0] - shifted[0]).abs() > 0.4, "four-pixel boundary destroyer is inert");
}

// Independent integration order: for one pupil ray clip the sensor square, then
// integrate its area/first moments. No production circle-segment formula is used.
fn square_moments(normal: [f64; 2], offset: f64) -> [f64; 3] {
    let square = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]];
    let mut polygon = [[0.0; 2]; 8];
    let mut count = 0;
    let mut previous = square[3];
    let mut h_previous = normal[0]*previous[0] + normal[1]*previous[1] - offset;
    for current in square {
        let h_current = normal[0]*current[0] + normal[1]*current[1] - offset;
        if (h_current >= 0.0) != (h_previous >= 0.0) {
            let t = h_previous / (h_previous - h_current);
            polygon[count] = [previous[0] + t*(current[0]-previous[0]),
                previous[1] + t*(current[1]-previous[1])];
            count += 1;
        }
        if h_current >= 0.0 { polygon[count] = current; count += 1; }
        previous = current; h_previous = h_current;
    }
    let mut result = [0.0; 3];
    if count < 3 { return result; }
    // Triangle areas/centroids about the first vertex, not production polygon moments.
    for i in 1..count-1 {
        let a = polygon[0]; let b = polygon[i]; let c = polygon[i+1];
        let area = ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])) * 0.5;
        result[0] += area;
        result[1] += area * (a[0]+b[0]+c[0]) / 3.0;
        result[2] += area * (a[1]+b[1]+c[1]) / 3.0;
    }
    result
}

fn ray_integrated_row(df: f64, db: f64, source: [f64; 2], radial: usize, angular: usize) -> [f64; 6] {
    let n = [1.0, -0.15]; let target = [160.0, 120.0];
    let mut sum = [0.0; 6];
    for ir in 0..radial {
        let radius = ((ir as f64 + 0.5) / radial as f64).sqrt();
        for ia in 0..angular {
            let angle = 2.0 * std::f64::consts::PI * (ia as f64 + 0.5) / angular as f64;
            let u = [radius*angle.cos(), radius*angle.sin()];
            let offset = 142.0 - n[0]*source[0] - n[1]*source[1] - df*(n[0]*u[0]+n[1]*u[1]);
            let [area, mx, my] = square_moments(n, offset);
            let delta = [source[0]-target[0], source[1]-target[1]];
            let row = [area, (delta[0]+df*u[0])*area+mx, (delta[1]+df*u[1])*area+my,
                1.0-area, (delta[0]+db*u[0])*(1.0-area)-mx,
                (delta[1]+db*u[1])*(1.0-area)-my];
            for i in 0..6 { sum[i] += row[i]; }
        }
    }
    for x in &mut sum { *x /= (radial*angular) as f64; }
    sum
}

fn independently_integrated_moments() {
    // Fixed validation resolutions, never a scored-output parameter sweep.
    for (df, db) in [(-6.0, 0.0), (-3.0, 3.0), (-1.5, 4.5), (0.0, 6.0), (2.0, -3.0)] {
        for source in [[160.0, 120.0], [161.25, 119.5], [158.75, 120.5]] {
            let coarse = ray_integrated_row(df, db, source, 96, 384);
            let reference = ray_integrated_row(df, db, source, 192, 768);
            let actual = cell_moments([1.0, -0.15], 142.0, df as f32, db as f32,
                [source[0] as f32, source[1] as f32], [160.0, 120.0]);
            for i in 0..6 {
                assert!((coarse[i]-reference[i]).abs() < 4e-4,
                    "independent reference unresolved: df={df},db={db},source={source:?},component={i},coarse={},fine={}", coarse[i], reference[i]);
                close(actual[i], reference[i], 1e-3, "independent pupil-first moment integral");
            }
            close(actual[0]+actual[3], 1.0, 2e-6, "visible area partition");
        }
    }
}

#[test]
fn independent_boundary_radiance_controls() {
    affine_and_refusal_controls();
    literal_moment_controls();
    independently_integrated_moments();
    eprintln!("BOUNDARY_RADIANCE_INDEPENDENT: affine/constant recovery, Schur threshold sides, variance/rank refusals, no-treatment bits, analytic shared-pupil/cell moments, displaced boundary and 15 independent ray-integrated rows passed");
}
