use super::*;

fn parameters(dimensions: [u32; 3]) -> GainMapParameters {
    GainMapParameters {
        dimensions,
        origin_yx: [0., 0.],
        spacing_yx: [1., 1.],
        input_weights: [1., 0., 0., 0., 0.],
        gamma: 1.,
    }
}

fn uniform_gain(gain: f32) -> GainMap {
    GainMap::new(vec![gain].into(), parameters([1, 1, 1])).unwrap()
}

fn profile(gain: GainMap, tables: [Option<ColorLut>; 3]) -> PreparedLearnedProfile {
    let [background, subject, sky] = tables;
    PreparedLearnedProfile::new(
        gain,
        background,
        subject,
        sky,
        ProfileParameters {
            linear_709_to_rimm: IDENTITY_MATRIX,
            pre_gain_scale: 1.,
            tone_curve: ProfileToneCurve::identity(),
        },
    )
    .unwrap()
}

fn identity_data(size: usize) -> Arc<[f32]> {
    let mut result = Vec::with_capacity(3 * size * size * size);
    for c in 0..3 {
        for r in 0..size {
            for g in 0..size {
                for b in 0..size {
                    result.push([r, g, b][c] as f32 / (size - 1) as f32);
                }
            }
        }
    }
    result.into()
}

fn constant_table(color: [f32; 3]) -> ColorLut {
    ColorLut::new(
        2,
        color
            .into_iter()
            .flat_map(|v| [v; 8])
            .collect::<Vec<_>>()
            .into(),
        IDENTITY_MATRIX,
        ColorEncoding::Linear,
        false,
    )
    .unwrap()
}

fn close(a: [f32; 3], b: [f32; 3], tolerance: f32) {
    for c in 0..3 {
        assert!(
            (a[c] - b[c]).abs() <= tolerance,
            "channel{c}: {a:?} != {b:?}"
        );
    }
}

#[test]
fn brightness_uses_number_of_points_not_number_of_intervals() {
    let map = GainMap::new(vec![0., 1., 2., 3.].into(), parameters([4, 1, 1])).unwrap();
    let actual = map.sample([0.25, 0., 0.], [0.5, 0.5]).unwrap();
    assert_eq!(actual, 1.);
    // The common N-1 mistake is distinguishable on the very same analytic plant.
    assert!((actual - 0.75).abs() > 0.2);
    assert_eq!(map.sample([1., 0., 0.], [0.5, 0.5]).unwrap(), 3.);
}

#[test]
fn spatial_gain_plane_is_sampled_at_full_image_pixel_centers() {
    let map = GainMap::new(vec![0., 1., 2., 3.].into(), parameters([1, 2, 2])).unwrap();
    // Independently specified analytic surface x+2y, not a second lookup.
    for (uv, expected) in [
        ([0.25, 0.25], 0.75),
        ([0.75, 0.25], 1.25),
        ([0.25, 0.75], 1.75),
        ([0.75, 0.75], 2.25),
    ] {
        assert!((map.sample([0.2; 3], uv).unwrap() - expected).abs() < 1e-6);
    }
    let p = profile(map, [None, None, None]);
    let mut output = [0.; 6];
    p.render_region(
        &[1.; 6],
        &mut output,
        ProfileRegion {
            full_size: [5, 3],
            origin: [1, 1],
            size: [2, 1],
        },
        SemanticMaskPlanes::default(),
        1.,
        &AtomicBool::new(false),
    )
    .unwrap();
    close(output[..3].try_into().unwrap(), [1.3; 3], 1e-6);
    close(output[3..].try_into().unwrap(), [1.5; 3], 1e-6);
}

#[test]
fn asymmetric_lut_reveals_channel_and_axis_transposition() {
    let original = identity_data(32);
    let volume = 32usize.pow(3);
    let swapped: Arc<[f32]> = [2, 0, 1]
        .into_iter()
        .flat_map(|c| original[c * volume..(c + 1) * volume].iter().copied())
        .collect::<Vec<_>>()
        .into();
    let table = ColorLut::new(32, swapped, IDENTITY_MATRIX, ColorEncoding::Linear, true).unwrap();
    let input = [0.71, 0.09, 0.38];
    let output = table.apply(input).unwrap();
    close(output, [0.38, 0.71, 0.09], 5e-7);
    assert!((output[0] - input[0]).abs() > 0.3);
}

#[test]
fn asymmetric_matrix_and_lut_have_independently_known_composition() {
    let original = identity_data(8);
    let volume = 8usize.pow(3);
    let permuted: Arc<[f32]> = [2, 0, 1]
        .into_iter()
        .flat_map(|c| original[c * volume..(c + 1) * volume].iter().copied())
        .collect::<Vec<_>>()
        .into();
    let matrix = [[1., 0.2, 0.], [0., 1., 0.], [0., 0., 1.]];
    let table = ColorLut::new(8, permuted, matrix, ColorEncoding::Linear, false).unwrap();
    // M*[.2,.3,.4] = [.26,.3,.4]; B,R,G permutation = [.4,.26,.3].
    // M^-1 subtracts .2*green from red, giving [.348,.26,.3]. An identity
    // LUT would cancel even a mutually consistent wrong matrix convention.
    let output = table.apply([0.2, 0.3, 0.4]).unwrap();
    close(output, [0.348, 0.26, 0.3], 5e-7);
    // Transposing both M and its inverse instead yields [.4,.12,.34].
    assert!((output[1] - 0.12).abs() > 0.1);
}

#[test]
fn profile_gain_precedes_nonlinear_tone_curve() {
    let p = PreparedLearnedProfile::new(
        uniform_gain(2.),
        None,
        None,
        None,
        ProfileParameters {
            linear_709_to_rimm: IDENTITY_MATRIX,
            pre_gain_scale: 1.,
            tone_curve: ProfileToneCurve::piecewise_linear(
                vec![[0., 0.], [0.5, 0.25], [1., 1.]].into(),
            )
            .unwrap(),
        },
    )
    .unwrap();
    // Gain maps .4 to .8; the upper tone segment then gives .25+.3*1.5=.7.
    let output = p.apply_pixel([0.4; 3], [0.5, 0.5], [0., 0.], 1.).unwrap();
    close(output, [0.7; 3], 3e-7);
    // Tone first would map .4 to .2, then gain would produce .4.
    assert!((output[0] - 0.4).abs() > 0.25);
}

#[test]
fn explicit_scale_precedes_brightness_gain_lookup() {
    let map = GainMap::new(vec![1., 2., 3., 4.].into(), parameters([4, 1, 1])).unwrap();
    let p = PreparedLearnedProfile::new(
        map,
        None,
        None,
        None,
        ProfileParameters {
            linear_709_to_rimm: IDENTITY_MATRIX,
            pre_gain_scale: 2.,
            tone_curve: ProfileToneCurve::identity(),
        },
    )
    .unwrap();
    // Source .2 scales to .4; brightness position N*.4=1.6 gives gain2.6,
    // producing 1.04. Scaling after lookup instead gives .2*1.8*2=.72.
    let output = p.apply_pixel([0.2; 3], [0.5, 0.5], [0., 0.], 1.).unwrap();
    close(output, [1.04; 3], 3e-7);
    assert!((output[0] - 0.72).abs() > 0.3);
}

#[test]
fn identity_tables_preserve_negative_values_and_hdr_offsets_for_all_encodings() {
    let input = [-0.1, 0.2, 1.3];
    for encoding in [
        ColorEncoding::Linear,
        ColorEncoding::Srgb,
        ColorEncoding::Power { gamma: 1.8 },
        ColorEncoding::Power { gamma: 2.2 },
    ] {
        let table = ColorLut::new(32, identity_data(32), IDENTITY_MATRIX, encoding, true).unwrap();
        close(table.apply(input).unwrap(), input, 2e-6);
    }
    let without_extension = ColorLut::new(
        32,
        identity_data(32),
        IDENTITY_MATRIX,
        ColorEncoding::Linear,
        false,
    )
    .unwrap();
    close(without_extension.apply(input).unwrap(), [0., 0.2, 1.], 2e-6);
    // This placebo proves the input exercises both sides of the nominal gamut.
    assert!(input[0] < 0. && input[2] > 1.);
}

#[test]
fn nonlinear_transfer_decodes_known_half_code_values() {
    for (encoding, expected) in [
        (ColorEncoding::Srgb, 0.214_041_14),
        (ColorEncoding::Power { gamma: 1.8 }, 0.287_174_58),
        (ColorEncoding::Power { gamma: 2.2 }, 0.217_637_64),
    ] {
        // Constant encoded half-gray yields an analytic inverse-transfer value;
        // unlike encode/decode roundtrip, two reciprocal wrong curves cannot pass.
        let data = vec![0.5; 3 * 8].into();
        let table = ColorLut::new(2, data, IDENTITY_MATRIX, encoding, false).unwrap();
        close(
            table.apply([0.17, 0.52, 0.83]).unwrap(),
            [expected; 3],
            2e-7,
        );
    }
}

#[test]
fn overlapping_semantics_normalize_independent_outputs() {
    let p = profile(
        uniform_gain(1.),
        [
            Some(constant_table([0., 1., 0.])),
            Some(constant_table([1., 0., 0.])),
            Some(constant_table([0., 0., 1.])),
        ],
    );
    let input = [0.2, 0.3, 0.4];
    close(
        p.apply_pixel(input, [0.5, 0.5], [1., 1.], 1.).unwrap(),
        [0.5, 0., 0.5],
        1e-7,
    );
    close(
        p.apply_pixel(input, [0.5, 0.5], [0.75, 0.75], 1.).unwrap(),
        [0.5, 0., 0.5],
        1e-7,
    );
    close(
        p.apply_pixel(input, [0.5, 0.5], [0.25, 0.5], 1.).unwrap(),
        [0.25, 0.25, 0.5],
        1e-7,
    );
    // No table for a semantic is not a hidden identity layer diluting others.
    let absent = profile(
        uniform_gain(1.),
        [None, None, Some(constant_table([0., 0., 1.]))],
    );
    close(
        absent.apply_pixel(input, [0.5, 0.5], [1., 0.], 1.).unwrap(),
        input,
        1e-7,
    );
    close(
        absent
            .apply_pixel(input, [0.5, 0.5], [1., 0.5], 1.)
            .unwrap(),
        [0.1, 0.15, 0.7],
        1e-7,
    );
}

#[test]
fn crop_and_full_frame_match_without_rebasing_gain_coordinates() {
    let map = GainMap::new(
        (0..12)
            .map(|v| v as f32 / 10. + 0.5)
            .collect::<Vec<_>>()
            .into(),
        GainMapParameters {
            spacing_yx: [0.5, 1. / 3.],
            ..parameters([1, 3, 4])
        },
    )
    .unwrap();
    let p = profile(map, [None, None, None]);
    let source = vec![0.2; 7 * 9 * 3];
    let mut whole = vec![0.; source.len()];
    p.render_region(
        &source,
        &mut whole,
        ProfileRegion {
            full_size: [9, 7],
            origin: [0, 0],
            size: [9, 7],
        },
        SemanticMaskPlanes::default(),
        1.,
        &AtomicBool::new(false),
    )
    .unwrap();
    let crop_input = vec![0.2; 3 * 4 * 3];
    let mut cropped = vec![0.; crop_input.len()];
    p.render_region(
        &crop_input,
        &mut cropped,
        ProfileRegion {
            full_size: [9, 7],
            origin: [2, 3],
            size: [4, 3],
        },
        SemanticMaskPlanes::default(),
        1.,
        &AtomicBool::new(false),
    )
    .unwrap();
    for y in 0..3 {
        for x in 0..4 {
            close(
                cropped[(y * 4 + x) * 3..][..3].try_into().unwrap(),
                whole[((y + 3) * 9 + x + 2) * 3..][..3].try_into().unwrap(),
                0.,
            );
        }
    }
    let spread = whole.iter().copied().fold(f32::NEG_INFINITY, f32::max)
        - whole.iter().copied().fold(f32::INFINITY, f32::min);
    assert!(spread > 0.1, "Fixture must exercise spatial variation");
    let rebased = p
        .apply_pixel([0.2; 3], [0.5 / 4., 0.5 / 3.], [0., 0.], 1.)
        .unwrap();
    assert!(
        (rebased[0] - cropped[0]).abs() > 0.05,
        "Wrong crop coordinates must fail"
    );
}

#[test]
fn zero_amount_is_exact_identity_even_for_signed_zero_and_headroom() {
    let p = PreparedLearnedProfile::new(
        uniform_gain(2.),
        Some(constant_table([0.8, 0.3, 0.2])),
        None,
        None,
        ProfileParameters {
            linear_709_to_rimm: LINEAR_709_TO_RIMM,
            pre_gain_scale: 1.5,
            tone_curve: ProfileToneCurve::identity(),
        },
    )
    .unwrap();
    let input = [-0.0, -0.123_456_7, 3.14];
    assert_eq!(
        p.apply_pixel(input, [0.3, 0.9], [0., 0.], 0.)
            .unwrap()
            .map(f32::to_bits),
        input.map(f32::to_bits)
    );
    let changed = p.apply_pixel(input, [0.3, 0.9], [0., 0.], 1.).unwrap();
    assert!(
        (changed[2] - input[2]).abs() > 1.,
        "Fixture must exercise a nonidentity treatment"
    );
    close(
        p.apply_pixel(input, [0.3, 0.9], [0., 0.], 0.5).unwrap(),
        std::array::from_fn(|c| (input[c] + changed[c]) * 0.5),
        2e-7,
    );
}

#[test]
fn explicit_tone_knots_preserve_headroom_and_have_monotone_domain() {
    let tone =
        ProfileToneCurve::piecewise_linear(vec![[0.1, 0.2], [0.5, 0.6], [1., 1.1]].into()).unwrap();
    assert_eq!(tone.domain_and_range(), Some([[0.1, 1.], [0.2, 1.1]]));
    for (input, expected) in [(-0.2, -0.1), (0.3, 0.4), (2., 2.1)] {
        assert!((tone.apply(input) - expected).abs() < 2e-7);
    }
    for knots in [
        vec![[0., 0.], [0., 1.]],
        vec![[0., 1.], [1., 0.]],
        vec![[0., 0.], [f32::NAN, 1.]],
    ] {
        assert!(ProfileToneCurve::piecewise_linear(knots.into()).is_err());
    }
    assert!(ProfileToneCurve::identity().domain_and_range().is_none());
}

#[test]
fn constant_gain_adds_no_flat_structure_or_step_shoulders() {
    let p = profile(uniform_gain(1.7), [None, None, None]);
    let source = (0..5 * 11)
        .flat_map(|i| [if i % 11 < 6 { 0.08 } else { 0.42 }; 3])
        .collect::<Vec<_>>();
    let mut output = vec![0.; source.len()];
    p.render_region(
        &source,
        &mut output,
        ProfileRegion {
            full_size: [11, 5],
            origin: [0, 0],
            size: [11, 5],
        },
        SemanticMaskPlanes::default(),
        1.,
        &AtomicBool::new(false),
    )
    .unwrap();
    for (before, after) in source.iter().zip(output.iter()) {
        assert!((after - before * 1.7).abs() < 1e-7);
    }
    assert!(
        output[6 * 3] - output[5 * 3] > 0.5,
        "Fixture must retain a real edge"
    );
    assert_eq!(output[0], output[5 * 3]);
}

#[test]
fn invalid_maps_tables_matrices_and_pixel_arguments_fail_closed() {
    for values in [vec![f32::NAN], vec![-0.1], vec![f32::INFINITY], vec![]] {
        assert!(GainMap::new(values.into(), parameters([1, 1, 1])).is_err());
    }
    for p in [
        GainMapParameters {
            gamma: 0.,
            ..parameters([1, 1, 1])
        },
        GainMapParameters {
            spacing_yx: [0., 1.],
            ..parameters([1, 1, 1])
        },
        parameters([64, 512, 512]),
    ] {
        assert!(GainMap::new(vec![1.].into(), p).is_err());
    }
    for value in [-0.001, 1.001, f32::NAN] {
        assert!(
            ColorLut::new(
                2,
                vec![value; 24].into(),
                IDENTITY_MATRIX,
                ColorEncoding::Linear,
                true
            )
            .is_err()
        );
    }
    assert!(
        ColorLut::new(
            32,
            vec![0.; 24].into(),
            IDENTITY_MATRIX,
            ColorEncoding::Linear,
            true
        )
        .is_err()
    );
    assert!(
        ColorLut::new(
            2,
            identity_data(2),
            [[0.; 3]; 3],
            ColorEncoding::Linear,
            true
        )
        .is_err()
    );
    assert!(
        ColorLut::new(
            2,
            identity_data(2),
            IDENTITY_MATRIX,
            ColorEncoding::Power { gamma: 0. },
            true
        )
        .is_err()
    );
    let p = profile(uniform_gain(1.), [None, None, None]);
    assert!(
        p.apply_pixel([f32::NAN, 0., 0.], [0.5, 0.5], [0., 0.], 0.)
            .is_err()
    );
    assert!(p.apply_pixel([0.2; 3], [-0.1, 0.5], [0., 0.], 1.).is_err());
    assert!(p.apply_pixel([0.2; 3], [0.5, 0.5], [1.1, 0.], 1.).is_err());
    assert!(
        p.apply_pixel([0.2; 3], [0.5, 0.5], [0., 0.], f32::NAN)
            .is_err()
    );
}

#[test]
fn cancellation_and_invalid_crop_buffers_do_not_publish_an_image() {
    let p = profile(uniform_gain(1.), [None, None, None]);
    let region = ProfileRegion {
        full_size: [2, 2],
        origin: [0, 0],
        size: [2, 2],
    };
    let mut output = [42.; 12];
    assert!(
        p.render_region(
            &[0.2; 12],
            &mut output,
            region,
            SemanticMaskPlanes::default(),
            1.,
            &AtomicBool::new(true)
        )
        .is_err()
    );
    assert_eq!(output, [42.; 12]);
    assert!(
        p.render_region(
            &[0.2; 9],
            &mut output,
            region,
            SemanticMaskPlanes::default(),
            1.,
            &AtomicBool::new(false)
        )
        .is_err()
    );
    assert!(
        p.render_region(
            &[0.2; 12],
            &mut output,
            region,
            SemanticMaskPlanes {
                subject: Some(&[0.5]),
                sky: None
            },
            1.,
            &AtomicBool::new(false)
        )
        .is_err()
    );
    assert!(
        p.render_region(
            &[0.2; 12],
            &mut output,
            ProfileRegion {
                origin: [1, 1],
                ..region
            },
            SemanticMaskPlanes::default(),
            1.,
            &AtomicBool::new(false)
        )
        .is_err()
    );
}

#[test]
fn extreme_finite_pixels_return_errors_instead_of_panicking() {
    let p = PreparedLearnedProfile::new(
        uniform_gain(f32::MAX),
        None,
        None,
        None,
        ProfileParameters {
            linear_709_to_rimm: IDENTITY_MATRIX,
            pre_gain_scale: f32::MAX,
            tone_curve: ProfileToneCurve::piecewise_linear(vec![[0., 0.], [1., 1.]].into())
                .unwrap(),
        },
    )
    .unwrap();
    assert!(
        p.apply_pixel([f32::MAX; 3], [0.5, 0.5], [0., 0.], 1.)
            .is_err()
    );
}
