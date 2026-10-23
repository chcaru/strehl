use std::sync::{Arc, atomic::AtomicBool};
use strehl_edit::learned_profile::{
    ColorEncoding, ColorLut, GainMap, GainMapParameters, IDENTITY_MATRIX, ProfileRegion,
};
use strehl_edit::learned_scene::{
    PreparedSceneSdrProfile, SCENE_SDR_LINEAR_V1, SceneSdrParameters, blend_sdr_scene_pixel,
};

fn gain(values: &[f32], dimensions: [u32; 3]) -> GainMap {
    GainMap::new(
        Arc::from(values),
        GainMapParameters {
            dimensions,
            origin_yx: [0., 0.],
            spacing_yx: [
                1. / (dimensions[1].max(2) - 1) as f32,
                1. / (dimensions[2].max(2) - 1) as f32,
            ],
            input_weights: [1., 0., 0., 0., 0.],
            gamma: 1.,
        },
    )
    .unwrap()
}

fn table(encoding: ColorEncoding) -> ColorLut {
    let mut values = Vec::new();
    for c in 0..3 {
        for r in 0..2 {
            for g in 0..2 {
                for b in 0..2 {
                    values.push([r, g, b][c] as f32);
                }
            }
        }
    }
    ColorLut::new(2, values.into(), IDENTITY_MATRIX, encoding, true).unwrap()
}

fn parameters(query: f32, exposure: f32) -> SceneSdrParameters {
    SceneSdrParameters {
        linear_709_to_working: IDENTITY_MATRIX,
        working_to_linear_709: IDENTITY_MATRIX,
        gain_query_scale: query,
        exposure_scale: exposure,
    }
}

fn prepared(map: GainMap, p: SceneSdrParameters) -> PreparedSceneSdrProfile {
    PreparedSceneSdrProfile::new(map, table(ColorEncoding::Linear), p).unwrap()
}

fn close(actual: [f32; 3], expected: [f32; 3], tolerance: f32) {
    for (a, e) in actual.into_iter().zip(expected) {
        assert!((a - e).abs() <= tolerance, "{actual:?} != {expected:?}");
    }
}

#[test]
fn query_scale_and_exposure_are_distinct_operations() {
    // Gain = 1 + 2*z, with z = 2*(2*red) = 0.4, so gain = 1.8.
    // The source remains unscaled until exposure halves it after gain.
    let p = prepared(gain(&[1., 3.], [2, 1, 1]), parameters(2., 0.5));
    let actual = p.develop_pixel([0.1, 0.2, 0.3], [0.3, 0.8]).unwrap();
    close(actual, [0.09, 0.18, 0.27], 1e-7);
    assert!(
        (actual[0] - 0.18).abs() > 0.08,
        "Scaled-source negative control"
    );
    let swapped = prepared(gain(&[1., 3.], [2, 1, 1]), parameters(0.5, 2.));
    assert!(
        (swapped.develop_pixel([0.1, 0.2, 0.3], [0.3, 0.8]).unwrap()[0] - actual[0]).abs() > 0.1
    );
    assert_eq!(p.contract_id(), SCENE_SDR_LINEAR_V1);
}

#[test]
fn subunit_exposure_and_query_factors_are_supported() {
    // Signed EV is converted by the caller. Negative EV is a valid factor < 1.
    for scale in [1. / 256., 0.25, 0.5, 1., 2., 256.] {
        let p = prepared(gain(&[1.], [1, 1, 1]), parameters(scale, scale));
        let source = [0.001, 0.002, 0.003];
        close(
            p.develop_pixel(source, [0.5; 2]).unwrap(),
            source.map(|v| v * scale),
            1e-7,
        );
    }
}

#[test]
fn sdr_cap_preserves_middle_channel_relation_for_every_rgb_permutation() {
    let p = prepared(gain(&[1.], [1, 1, 1]), parameters(1., 1.));
    let values = [0.2, 0.8, 2.];
    // Independent geometric interpolation: (middle-low)/(high-low) = 1/3.
    let expected = [0.2, 0.2 + 0.8 / 3., 1.];
    for order in [
        [0, 1, 2],
        [0, 2, 1],
        [1, 0, 2],
        [1, 2, 0],
        [2, 0, 1],
        [2, 1, 0],
    ] {
        let source = order.map(|i| values[i]);
        let result = p.develop_pixel(source, [0.5; 2]).unwrap();
        close(result, order.map(|i| expected[i]), 2e-7);
        assert!(
            result
                .iter()
                .zip(source)
                .any(|(a, b)| (a - b.min(1.)).abs() > 0.3),
            "Per-channel cap must fail this fixture"
        );
    }
    for (source, expected) in [
        ([0.2, 0.2, 2.], [0.2, 0.2, 1.]),
        ([0.2, 2., 2.], [0.2, 1., 1.]),
        ([2., 3., 4.], [1.; 3]),
        ([0.3, 0.3, 0.3], [0.3; 3]),
        ([-0.2, 0.4, 0.8], [0., 0.4, 0.8]),
    ] {
        close(p.develop_pixel(source, [0.5; 2]).unwrap(), expected, 2e-7);
    }
}

#[test]
fn transforms_are_applied_in_declared_order_before_negative_clamp() {
    // Invertible shear: R' = R + G, G' = G. Negative R is not clamped until
    // after entering this working space, which distinguishes the two orders.
    let mut params = parameters(1., 1.);
    params.linear_709_to_working = [[1., 1., 0.], [0., 1., 0.], [0., 0., 1.]];
    params.working_to_linear_709 = [[1., -1., 0.], [0., 1., 0.], [0., 0., 1.]];
    let p = prepared(gain(&[1.], [1, 1, 1]), params);
    close(
        p.develop_pixel([-0.1, 0.4, 0.2], [0.5; 2]).unwrap(),
        [-0.1, 0.4, 0.2],
        1e-7,
    );
    close(
        p.develop_pixel([0.8, 0.6, 0.2], [0.5; 2]).unwrap(),
        [0.5333333, 0.4666667, 0.2],
        3e-7,
    );
}

#[test]
fn explicit_power_encoding_and_asymmetric_lut_are_used() {
    let mut values = Vec::new();
    for c in 0..3 {
        for r in 0..2 {
            for g in 0..2 {
                for b in 0..2 {
                    values.push([r, g, b][c] as f32 * [1., 0.5, 0.25][c]);
                }
            }
        }
    }
    let color = ColorLut::new(
        2,
        values.into(),
        IDENTITY_MATRIX,
        ColorEncoding::Power { gamma: 2.2 },
        true,
    )
    .unwrap();
    let p =
        PreparedSceneSdrProfile::new(gain(&[1.], [1, 1, 1]), color, parameters(1., 1.)).unwrap();
    let source = [0.15, 0.4, 0.7];
    let result = p.develop_pixel(source, [0.2, 0.7]).unwrap();
    // Multiplying encoded channels by a means multiplying linear by a^gamma.
    close(
        result,
        [
            source[0],
            source[1] * 0.5f32.powf(2.2),
            source[2] * 0.25f32.powf(2.2),
        ],
        2e-7,
    );
    assert!(
        (result[1] - source[1] * 0.5).abs() > 0.1,
        "Linear-encoding negative control"
    );
}

#[test]
fn native_crops_match_full_render_and_rebased_coordinates_do_not() {
    // Analytic gain surface 1 + 0.4*u + 0.8*v, deliberately asymmetric.
    let values: Vec<_> = (0..3)
        .flat_map(|y| (0..4).map(move |x| 1. + 0.4 * x as f32 / 3. + 0.8 * y as f32 / 2.))
        .collect();
    let p = prepared(gain(&values, [1, 3, 4]), parameters(1., 1.));
    let source: Vec<_> = (0..35).flat_map(|_| [0.05, 0.1, 0.2]).collect();
    let mut whole = vec![0.; source.len()];
    let flag = AtomicBool::new(false);
    p.render_region(
        &source,
        &mut whole,
        ProfileRegion {
            full_size: [7, 5],
            origin: [0, 0],
            size: [7, 5],
        },
        &flag,
    )
    .unwrap();
    for y in 0..5 {
        for x in 0..7 {
            let expected_gain = 1. + 0.4 * (x as f32 + 0.5) / 7. + 0.8 * (y as f32 + 0.5) / 5.;
            close(
                whole[(y * 7 + x) * 3..(y * 7 + x) * 3 + 3]
                    .try_into()
                    .unwrap(),
                [0.05, 0.1, 0.2].map(|v| v * expected_gain),
                1e-7,
            );
        }
    }
    let source_crop: Vec<_> = (1..3)
        .flat_map(|y| source[(y * 7 + 2) * 3..(y * 7 + 5) * 3].iter().copied())
        .collect();
    let mut crop = vec![0.; source_crop.len()];
    p.render_region(
        &source_crop,
        &mut crop,
        ProfileRegion {
            full_size: [7, 5],
            origin: [2, 1],
            size: [3, 2],
        },
        &flag,
    )
    .unwrap();
    let expected: Vec<_> = (1..3)
        .flat_map(|y| whole[(y * 7 + 2) * 3..(y * 7 + 5) * 3].iter().copied())
        .collect();
    assert_eq!(
        crop.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
        expected.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
    );
    let mut rebased = vec![0.; crop.len()];
    p.render_region(
        &source_crop,
        &mut rebased,
        ProfileRegion {
            full_size: [3, 2],
            origin: [0, 0],
            size: [3, 2],
        },
        &flag,
    )
    .unwrap();
    assert!(crop.iter().zip(rebased).any(|(a, b)| (a - b).abs() > 0.02));
}

#[test]
fn zero_amount_keeps_complete_baseline_bits_and_does_not_resolve_candidate() {
    // A developed baseline deliberately differs from the hypothetical raw
    // source. Negative zero also detects a seemingly harmless math round-trip.
    let baseline = [-0.0, 0.43, 0.77];
    let result = blend_sdr_scene_pixel(baseline, 0., || {
        panic!("Unresolved asset must not be touched")
    })
    .unwrap();
    assert_eq!(result.map(f32::to_bits), baseline.map(f32::to_bits));
    assert_ne!(
        result,
        [0., 0.2, 0.3],
        "Raw identity would violate this boundary"
    );
    let candidate = [0.1, 0.8, -0.0];
    assert_eq!(
        blend_sdr_scene_pixel(baseline, 1., || Ok(candidate))
            .unwrap()
            .map(f32::to_bits),
        candidate.map(f32::to_bits)
    );
    close(
        blend_sdr_scene_pixel(baseline, 0.25, || Ok(candidate)).unwrap(),
        [0.025, 0.5225, 0.5775],
        1e-7,
    );
    assert!(blend_sdr_scene_pixel(baseline, 0.5, || anyhow::bail!("Missing asset")).is_err());
    assert!(blend_sdr_scene_pixel(baseline, 0.5, || Ok([f32::NAN; 3])).is_err());
    assert!(
        blend_sdr_scene_pixel(baseline, -0.1, || panic!("Invalid amount must stop first")).is_err()
    );
}

#[test]
fn malformed_parameters_pixels_and_buffers_fail_before_publication() {
    for value in [0., -1., f32::NAN, f32::INFINITY, 256.01] {
        for params in [parameters(value, 1.), parameters(1., value)] {
            assert!(
                PreparedSceneSdrProfile::new(
                    gain(&[1.], [1, 1, 1]),
                    table(ColorEncoding::Linear),
                    params
                )
                .is_err()
            );
        }
    }
    let mut bad = parameters(1., 1.);
    bad.working_to_linear_709[0][0] = 2.;
    assert!(
        PreparedSceneSdrProfile::new(gain(&[1.], [1, 1, 1]), table(ColorEncoding::Linear), bad)
            .is_err()
    );
    bad.working_to_linear_709 = [[0.; 3]; 3];
    assert!(
        PreparedSceneSdrProfile::new(gain(&[1.], [1, 1, 1]), table(ColorEncoding::Linear), bad)
            .is_err()
    );
    let p = prepared(gain(&[1.], [1, 1, 1]), parameters(2., 2.));
    assert!(p.develop_pixel([f32::NAN; 3], [0.5; 2]).is_err());
    assert!(
        p.develop_pixel([f32::MAX; 3], [0.5; 2]).is_err(),
        "Overflow may not be concealed by the cap"
    );
    assert!(p.develop_pixel([0.1; 3], [0.5, 1.01]).is_err());
    let region = ProfileRegion {
        full_size: [2, 1],
        origin: [0, 0],
        size: [2, 1],
    };
    let mut out = [42.; 6];
    assert!(
        p.render_region(&[0.1; 6], &mut out, region, &AtomicBool::new(true))
            .is_err()
    );
    assert_eq!(out, [42.; 6]);
    assert!(
        p.render_region(&[0.1; 3], &mut out, region, &AtomicBool::new(false))
            .is_err()
    );
    assert!(
        p.render_region(
            &[0.1; 6],
            &mut out,
            ProfileRegion {
                origin: [u32::MAX, 0],
                ..region
            },
            &AtomicBool::new(false)
        )
        .is_err()
    );
    assert_eq!(out, [42.; 6]);
}
