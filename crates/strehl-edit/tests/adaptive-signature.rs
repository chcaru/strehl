//! Fail-capable operator controls. These guard contrast behavior; neither a
//! changed pixel nor a contrast increase establishes photographic improvement.
use strehl_edit::*;

fn image(width: u32, height: u32, f: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
    let mut pixels = Vec::new();
    for y in 0..height {
        for x in 0..width {
            pixels.extend(f(x, y));
        }
    }
    LinearImage {
        width,
        height,
        pixels,
        origin: ImageOrigin::DisplayReferred,
        baseline: None,
        baked_recipe: None,
    }
}
fn analyze(image: &LinearImage, parameters: AdaptiveParameters) -> AdaptiveSuggestion {
    analyze_adaptive_with_parameters(
        image,
        &DevelopmentRecipe::default(),
        None,
        AdaptiveIntent::Balance,
        parameters,
    )
    .unwrap()
}
fn scene() -> LinearImage {
    image(192, 96, |x, y| {
        if x < 32 {
            return [0.003 + (y % 7) as f32 * 0.0001; 3];
        }
        let light = 0.03 + ((x - 32) as f32 / 160.0).powf(1.8) * 0.72;
        [light, light * (0.75 + (y % 13) as f32 * 0.01), light * 0.55]
    })
}

#[test]
fn signature_preserves_flat_noise_and_does_not_make_hard_edge_bands() {
    // A flat noisy control can reject a spatial treatment which mistakes noise
    // for useful variation. Test it before the positive scene.
    let flat = image(128, 80, |x, y| {
        let n = (((x * 17 + y * 29) % 13) as f32 - 6.0) * 0.00002;
        [0.18 + n; 3]
    });
    let base = DevelopmentRecipe::default();
    assert_eq!(
        flat.render_sdr16(&base).unwrap(),
        flat.render_sdr16(&analyze(&flat, AdaptiveParameters::signature()).suggested)
            .unwrap()
    );
    let edge = image(128, 80, |x, _| if x < 64 { [0.08; 3] } else { [0.8; 3] });
    let treatment = analyze(&edge, AdaptiveParameters::signature());
    for (a, b) in [(0, 64), (64, 128)] {
        let values: Vec<_> = (a..b)
            .map(|x| edge.developed_pixel(40 * 128 + x, &treatment.suggested)[0])
            .collect();
        let span = values.iter().copied().fold(f32::NEG_INFINITY, f32::max)
            - values.iter().copied().fold(f32::INFINITY, f32::min);
        assert!(
            span < 0.0005,
            "flat side of hard edge acquired a band: {span}"
        );
    }
    let scene = scene();
    assert_ne!(
        scene.render_sdr16(&base).unwrap(),
        scene
            .render_sdr16(&analyze(&scene, AdaptiveParameters::signature()).suggested)
            .unwrap(),
        "positive scene did not exercise Signature"
    );
}

#[test]
fn signature_keeps_dark_floor_hue_neutrals_and_bright_channels_bounded() {
    let source = scene();
    let treatment = analyze(&source, AdaptiveParameters::signature());
    let base = DevelopmentRecipe::default();
    for row in 0..96 {
        for col in 0..32 {
            let i = row * 192 + col;
            assert_eq!(
                source.developed_pixel(i, &base),
                source.developed_pixel(i, &treatment.suggested)
            );
        }
    }
    let mut changed = 0;
    for light in [0.04, 0.1, 0.18, 0.4, 0.8, 1.0, 2.0] {
        let rgb = [light, light * 0.7, light * 0.3];
        let out = treatment.suggested.apply_pixel(rgb, [0.55, 0.4]);
        assert!(
            out.into_iter()
                .all(|c| c.is_finite() && c >= 0.0 && c <= light.max(1.0))
        );
        // Chroma must remain on the original RGB hue ray; contrast and color
        // are not permitted to rotate hue or manufacture a neutral tint.
        assert!(((out[0] - out[1]) / (out[1] - out[2]) - 0.75).abs() < 0.00002);
        let neutral = treatment.suggested.apply_pixel([light; 3], [0.55, 0.4]);
        assert!(neutral[0] == neutral[1] && neutral[1] == neutral[2]);
        changed += usize::from(out != rgb);
    }
    assert!(
        changed >= 4,
        "test did not exercise actual tonal/color changes"
    );
}

#[test]
fn presence_is_scene_relative_and_monotone_with_reversible_portable_amount() {
    let a = scene();
    let mut b = a.clone();
    for p in &mut b.pixels {
        *p *= 0.4;
    }
    let parameters = AdaptiveParameters {
        balance: 0.0,
        local_contrast: 0.0,
        color: 0.0,
        highlight_compression: 0.0,
        ..AdaptiveParameters::signature()
    };
    let sa = analyze(&a, parameters);
    let sb = analyze(&b, parameters);
    assert_ne!(
        sa.suggested.spatial[0].tone_ev, sb.suggested.spatial[0].tone_ev,
        "different light distributions received a fixed canned tone curve"
    );
    for uv in [[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]] {
        let mut previous = 0.0;
        for i in 0..2048 {
            let value = (i as f32 / 2047.0).powf(2.0) * 4.0;
            let out = sa.suggested.apply_pixel([value; 3], uv)[0];
            assert!(
                out >= previous - 1e-6,
                "luminance order reversed at {value}"
            );
            previous = out;
        }
    }
    assert_eq!(sa.recipe_at(0.0).unwrap(), sa.base);
    assert_eq!(
        a.render_sdr16(&sa.recipe_at(0.0).unwrap()).unwrap(),
        a.render_sdr16(&sa.base).unwrap()
    );
    let stored = serde_json::to_vec(&sa.recipe_at(0.37).unwrap()).unwrap();
    let reopened: DevelopmentRecipe = serde_json::from_slice(&stored).unwrap();
    assert_eq!(reopened, sa.recipe_at(0.37).unwrap());
    let mut invalid = parameters;
    invalid.presence = f32::NAN;
    assert!(invalid.validate().is_err());
    invalid.presence = 1.01;
    assert!(invalid.validate().is_err());
}

#[test]
fn strongest_presence_is_valid_for_each_tonal_scope() {
    let source = scene();
    for tone_range in [
        AdaptiveToneRange::All,
        AdaptiveToneRange::Shadows,
        AdaptiveToneRange::Midtones,
        AdaptiveToneRange::Highlights,
    ] {
        let parameters = AdaptiveParameters {
            balance: 1.0,
            local_contrast: 1.0,
            color: 1.0,
            presence: 1.0,
            shadow_protection: 1.0,
            highlight_compression: 1.0,
            tone_range,
        };
        let result = analyze(&source, parameters);
        result.suggested.validate().unwrap();
        assert!(!result.suggested.spatial.is_empty());
        for uv in [[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]] {
            let mut previous = 0.0;
            for i in 0..2048 {
                let value = (i as f32 / 2047.0).powf(2.0) * 4.0;
                let out = result.suggested.apply_pixel([value; 3], uv)[0];
                assert!(
                    out >= previous - 1e-6,
                    "{tone_range:?} strongest profile reverses luminance at {value}"
                );
                previous = out;
            }
        }
    }
    let actual = analyze(&source, AdaptiveParameters::signature());
    for uv in [[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]] {
        let mut previous = 0.0;
        for i in 0..2048 {
            let value = (i as f32 / 2047.0).powf(2.0) * 4.0;
            let out = actual.suggested.apply_pixel([value; 3], uv)[0];
            assert!(
                out >= previous - 1e-6,
                "Signature reverses luminance at {value}"
            );
            previous = out;
        }
    }
}

#[test]
fn embedded_midtone_noise_follows_tonal_slope_without_new_fine_structure() {
    let source = image(384, 256, |x, y| {
        let light = if (80..304).contains(&x) && (64..192).contains(&y) {
            0.18
        } else {
            0.03 + (x as f32 / 383.0).powf(1.4) * 0.7
        };
        [light; 3]
    });
    let treatment = analyze(&source, AdaptiveParameters::signature());
    let field = treatment.suggested.adaptive_scope(None).unwrap();
    let mut flat = Vec::new();
    let epsilon = 0.0001;
    let mut measured_noise = 0.0f64;
    let mut predicted_noise = 0.0f64;
    for y in 116..140 {
        for x in 160..224 {
            let uv = [(x as f32 + 0.5) / 384.0, (y as f32 + 0.5) / 256.0];
            let value = treatment.suggested.apply_pixel([0.18; 3], uv)[0];
            flat.push(value);
            let below = treatment.suggested.apply_pixel([0.18 - epsilon; 3], uv)[0];
            let above = treatment.suggested.apply_pixel([0.18 + epsilon; 3], uv)[0];
            // This plateau is above the black guard and below the highlight
            // guard, so y' = y * 2^e(y). Its analytic derivative is an
            // independent expectation for the actual developed noisy pair.
            let ev = field.gain_ev_at(uv, 0.18);
            let derivative_ev = (field.gain_ev_at(uv, 0.18 + epsilon)
                - field.gain_ev_at(uv, 0.18 - epsilon))
                / (2.0 * epsilon);
            let derivative = ev.exp2() * (1.0 + std::f32::consts::LN_2 * 0.18 * derivative_ev);
            measured_noise += f64::from((above - below) / (2.0 * epsilon));
            predicted_noise += f64::from(derivative);
            assert!(
                ((above - below) / (2.0 * epsilon) - derivative).abs() < 0.002,
                "fine variation differs from the expected local tone response"
            );
        }
    }
    let span = flat.iter().copied().fold(f32::NEG_INFINITY, f32::max)
        - flat.iter().copied().fold(f32::INFINITY, f32::min);
    assert!(
        span < 0.005,
        "embedded uniform patch acquired excessive spatial shading: {span}"
    );
    assert!(
        measured_noise > 1000.0 && predicted_noise > 1000.0,
        "test did not exercise the midtone plateau"
    );
    // A planted pixelwise sharpening gain would fail the derivative detector.
    assert!((measured_noise * 1.5 / predicted_noise - 1.0).abs() > 0.4);
}
