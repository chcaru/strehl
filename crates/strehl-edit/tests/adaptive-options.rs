//! Rejectable controls for opt-in tone selection and highlight compression.
//! These are operator guards, not aesthetic scores or claims of recovered detail.
use std::sync::atomic::AtomicBool;
use strehl_edit::*;

fn make_image(width: u32, height: u32, f: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
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
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}
fn scene() -> LinearImage {
    make_image(160, 96, |x, y| {
        let light = if x < 32 {
            0.003 + (x % 7) as f32 * 0.0002
        } else if x > 155 {
            0.85
        } else {
            0.05 + (x - 32) as f32 * 0.003 + (y % 9) as f32 * 0.009
        };
        [light * 1.12, light, light * 0.74]
    })
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
fn y(p: [f32; 3]) -> f64 {
    (0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]) as f64
}
fn mean(image: &LinearImage, recipe: &DevelopmentRecipe) -> f64 {
    (0..image.width as usize * image.height as usize)
        .map(|i| y(image.developed_pixel(i, recipe)))
        .sum::<f64>()
        / (image.width * image.height) as f64
}

#[test]
fn selective_treatment_keeps_light_placement_and_rejects_a_bad_offset() {
    let image = scene();
    let base = DevelopmentRecipe::default();
    let before = mean(&image, &base);
    for range in [
        AdaptiveToneRange::All,
        AdaptiveToneRange::Shadows,
        AdaptiveToneRange::Midtones,
        AdaptiveToneRange::Highlights,
    ] {
        let s = analyze(
            &image,
            AdaptiveParameters {
                balance: 0.85,
                local_contrast: 0.95,
                color: 0.7,
                tone_range: range,
                shadow_protection: 0.8,
                ..Default::default()
            },
        );
        assert!(s.suggested.spatial[0].version == 2);
        let after = mean(&image, &s.suggested);
        assert!(
            (after / before - 1.0).abs() < 0.001,
            "{range:?} silently changed whole-image placement: {}",
            after / before
        );
        assert_ne!(
            image.render_sdr16(&base).unwrap(),
            image.render_sdr16(&s.suggested).unwrap(),
            "positive control did not exercise treatment"
        );
        let mut wrong = s.suggested.clone();
        wrong.spatial[0].centering_ev += 0.1;
        assert!(
            (mean(&image, &wrong) / before - 1.0).abs() > 0.01,
            "mean detector failed to reject planted global brightening"
        );
    }
}

#[test]
fn tone_selection_and_dark_protection_cover_color_as_well_as_light() {
    let image = scene();
    let parameters = AdaptiveParameters {
        balance: 0.8,
        local_contrast: 0.8,
        color: 1.0,
        shadow_protection: 1.0,
        ..Default::default()
    };
    let s = analyze(&image, parameters);
    let base = DevelopmentRecipe::default();
    for yy in 0..96 {
        for x in 0..32 {
            let i = yy * 160 + x;
            assert_eq!(
                image.developed_pixel(i, &s.suggested),
                image.developed_pixel(i, &base),
                "dark background was recolored or lifted"
            );
        }
    }
    let highlights = analyze(
        &image,
        AdaptiveParameters {
            tone_range: AdaptiveToneRange::Highlights,
            ..parameters
        },
    );
    let shadows = analyze(
        &image,
        AdaptiveParameters {
            tone_range: AdaptiveToneRange::Shadows,
            ..parameters
        },
    );
    let mut highlight_changes = 0;
    let mut shadow_changes = 0;
    for i in 0..160 * 96 {
        let before = image.developed_pixel(i, &base);
        let light = y(before);
        let h = image.developed_pixel(i, &highlights.suggested);
        let s = image.developed_pixel(i, &shadows.suggested);
        if light <= 0.125 {
            assert_eq!(
                h, before,
                "highlights treatment escaped its low-light boundary"
            );
        }
        if light >= 0.25 {
            assert_eq!(
                s, before,
                "shadows treatment escaped its high-light boundary"
            );
        }
        highlight_changes += usize::from(h != before);
        shadow_changes += usize::from(s != before);
    }
    assert!(
        highlight_changes > 500 && shadow_changes > 500,
        "both range controls must actually affect supported light"
    );
}

#[test]
fn flat_noise_and_hard_edges_are_not_invented_texture() {
    for range in [
        AdaptiveToneRange::All,
        AdaptiveToneRange::Shadows,
        AdaptiveToneRange::Midtones,
        AdaptiveToneRange::Highlights,
    ] {
        let parameters = AdaptiveParameters {
            balance: 1.0,
            local_contrast: 1.0,
            color: 1.0,
            tone_range: range,
            shadow_protection: 1.0,
            ..Default::default()
        };
        let flat = make_image(120, 80, |x, y| {
            let noise = (((x * 17 + y * 43) % 11) as f32 - 5.0) * 0.00002;
            [0.18 + noise; 3]
        });
        let treatment = analyze(&flat, parameters);
        assert_eq!(
            flat.render_sdr16(&treatment.suggested).unwrap(),
            flat.render_sdr16(&DevelopmentRecipe::default()).unwrap(),
            "flat/noise control was contrast-enhanced"
        );
        let edge = make_image(120, 80, |x, _| if x < 60 { [0.04; 3] } else { [0.85; 3] });
        let result = analyze(&edge, parameters);
        for (a, b) in [(0, 60), (60, 120)] {
            let values: Vec<_> = (a..b)
                .map(|x| edge.developed_pixel(40 * 120 + x, &result.suggested)[0])
                .collect();
            let span = values.iter().copied().fold(f32::NEG_INFINITY, f32::max)
                - values.iter().copied().fold(f32::INFINITY, f32::min);
            assert!(
                span < 0.0005,
                "{range:?} created a bright/dark band on an otherwise flat step: {span}"
            );
        }
    }
}

#[test]
fn compression_is_monotone_hue_preserving_and_does_not_lift_other_light() {
    let image = make_image(128, 96, |x, _| {
        let light = x as f32 / 127.0 * 8.0;
        [light, light * 0.75, light * 0.25]
    });
    let parameters = AdaptiveParameters {
        balance: 0.0,
        local_contrast: 0.0,
        color: 0.0,
        highlight_compression: 1.0,
        ..Default::default()
    };
    let s = analyze(&image, parameters);
    assert!(s.suggested.adaptive_scope(None).is_some());
    let mut previous = 0.0;
    let mut compressed = 0;
    for x in 0..128 {
        let before = image.developed_pixel(x, &DevelopmentRecipe::default());
        let after = image.developed_pixel(x, &s.suggested);
        assert!(
            after[0] >= previous - 1e-6,
            "highlight order reversed at {x}"
        );
        previous = after[0];
        assert!(
            after.iter().zip(before).all(|(a, b)| *a <= b + 1e-6),
            "highlight action brightened a sample"
        );
        if before[0] < 1.0 {
            assert_eq!(after, before, "valid HDR diffuse light was compressed");
        }
        if after[0] > 0.0 {
            assert!(
                (after[1] / after[0] - 0.75).abs() < 1e-6
                    && (after[2] / after[0] - 0.25).abs() < 1e-6,
                "compression changed hue ratios"
            );
        }
        compressed += usize::from(after[0] < before[0] - 0.01);
    }
    assert!(
        compressed > 20,
        "planted bright HDR tail did not exercise compression"
    );
    let flat_white = make_image(32, 24, |_, _| [4.8; 3]);
    let flat = analyze(&flat_white, parameters);
    let output = flat_white.render_sdr16(&flat.suggested).unwrap();
    assert!(
        output.as_chunks::<3>().0.iter().all(|p| p == &output[0..3]),
        "flat highlight acquired detail"
    );
    assert!(
        flat_white.developed_pixel(0, &flat.suggested)[0] < 4.8,
        "uniform bright input should permit compression without a false detail claim"
    );
}

#[test]
fn default_wire_form_is_unchanged_and_version_two_is_portable_at_native_coordinates() {
    let params = serde_json::to_string(&AdaptiveParameters::default()).unwrap();
    assert_eq!(
        params,
        r#"{"balance":0.5,"local_contrast":0.5,"color":0.35}"#
    );
    let image = scene();
    let s = analyze(
        &image,
        AdaptiveParameters {
            tone_range: AdaptiveToneRange::Midtones,
            shadow_protection: 0.8,
            highlight_compression: 0.6,
            ..Default::default()
        },
    );
    let field = s.suggested.adaptive_scope(None).unwrap();
    assert_eq!(field.color_gain.len(), field.tone_ev.len());
    assert_eq!(s.recipe_at(0.0).unwrap(), s.base);
    let stored = serde_json::to_vec(&s.suggested).unwrap();
    let reopened: DevelopmentRecipe = serde_json::from_slice(&stored).unwrap();
    assert_eq!(reopened, s.suggested);
    let request = DisplayRegionRequest {
        min: [17, 13],
        max: [111, 87],
        stride: 1,
    };
    let patch = image
        .render_display_region_mode(&reopened, request, &AtomicBool::new(false), true)
        .unwrap();
    for yy in 0..74 {
        for x in 0..94 {
            assert_eq!(
                &patch.rgba_linear[(yy * 94 + x) * 4..(yy * 94 + x) * 4 + 3],
                image.developed_pixel((yy + 13) * 160 + x + 17, &reopened)
            );
        }
    }
    let next = analyze_adaptive(&image, &reopened).unwrap();
    assert_eq!(
        next.suggested.spatial[0].version, 1,
        "control must actually interpolate old and new layouts"
    );
    let half = next.recipe_at(0.5).unwrap();
    assert_eq!(half.spatial[0].version, 2);
    half.validate().unwrap();
    let low = next.recipe_at(0.499).unwrap();
    let high = next.recipe_at(0.501).unwrap();
    let a = image.render_sdr16(&low).unwrap();
    let b = image.render_sdr16(&high).unwrap();
    assert!(
        a.iter().zip(b).all(|(a, b)| a.abs_diff(b) < 64),
        "range change introduced a discrete Amount jump"
    );
}
