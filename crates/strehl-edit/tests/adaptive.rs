use strehl_edit::*;

fn fixture(width: u32, height: u32, f: impl Fn(usize) -> [f32; 3]) -> LinearImage {
    LinearImage {
        width,
        height,
        pixels: (0..width as usize * height as usize).flat_map(f).collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

fn varied() -> LinearImage {
    fixture(128, 64, |i| {
        let v = 0.03 + (i % 128) as f32 / 127.0 * 0.45;
        [v * 1.1, v, v * 0.8]
    })
}

#[test]
fn flat_dark_and_black_background_controls_do_not_manufacture_a_scene() {
    // A contrast/exposure heuristic can fail by amplifying a nearly uniform
    // dark field. Run these negative controls before judging the positive case.
    for image in [
        fixture(128, 64, |_| [0.0; 3]),
        fixture(128, 64, |_| [0.18; 3]),
        fixture(128, 64, |_| [1.0; 3]),
        fixture(128, 64, |i| [0.18 + (i % 7) as f32 * 0.00001; 3]),
        fixture(128, 64, |i| [(i % 128) as f32 * 0.000001; 3]),
        fixture(128, 64, |i| {
            if i % 128 < 123 {
                [0.0; 3]
            } else {
                [0.6, 0.2, 0.1]
            }
        }),
    ] {
        let recipe = DevelopmentRecipe::default();
        let suggestion = analyze_adaptive(&image, &recipe).unwrap();
        assert_eq!(suggestion.suggested, recipe);
        assert!(suggestion.changes.is_empty());
        assert_eq!(
            image.render_sdr16(&recipe).unwrap(),
            image
                .render_sdr16(&suggestion.recipe_at(1.0).unwrap())
                .unwrap()
        );
    }
    let image = varied();
    let suggestion = analyze_adaptive(&image, &DevelopmentRecipe::default()).unwrap();
    assert!(suggestion.stats.dynamic_range_stops > 1.0);
    assert!(
        !suggestion.changes.is_empty(),
        "positive fixture never exercised an adaptive edit"
    );
    assert_ne!(
        image.render_sdr16(&suggestion.base).unwrap(),
        image.render_sdr16(&suggestion.suggested).unwrap()
    );
}

#[test]
fn frozen_base_strength_is_exact_and_regions_hue_hdr_are_preserved() {
    let mut base = DevelopmentRecipe::default();
    base.global.temperature = 12.0;
    base.global.tint = -4.0;
    base.global.saturation = 3.0;
    base.global.blacks = -7.0;
    base.hdr.peak_nits = 1800.0;
    base.regions.push(RegionAdjustment {
        id: "repair".into(),
        name: "Marked wing".into(),
        note: "retain".into(),
        shape: RegionShape::Ellipse {
            center: [0.4, 0.6],
            radius: [0.2, 0.3],
        },
        feather: 0.4,
        enabled: true,
        adjustments: Adjustments {
            exposure: 0.2,
            ..Default::default()
        },
        source_range: Some(SourceRange {
            first: 17,
            last: 23,
        }),
    });
    let image = varied();
    let original_bits: Vec<_> = image.pixels.iter().map(|x| x.to_bits()).collect();
    let suggestion = analyze_adaptive(&image, &base).unwrap();
    assert_eq!(suggestion.recipe_at(0.0).unwrap(), base);
    assert_eq!(
        image.render_sdr16(&base).unwrap(),
        image
            .render_sdr16(&suggestion.recipe_at(0.0).unwrap())
            .unwrap()
    );
    for amount in [0.0, 0.1, 0.5, 1.0, 0.2, 0.5] {
        let recipe = suggestion.recipe_at(amount).unwrap();
        assert_eq!(recipe.regions, base.regions);
        assert_eq!(recipe.hdr, base.hdr);
        assert_eq!(recipe.global.temperature, base.global.temperature);
        assert_eq!(recipe.global.tint, base.global.tint);
        assert_eq!(recipe.global.saturation, base.global.saturation);
        assert_eq!(recipe.global.blacks, base.global.blacks);
    }
    assert!(suggestion.suggested.global.vibrance > base.global.vibrance);
    assert_eq!(
        suggestion.recipe_at(0.5).unwrap().global.vibrance,
        (base.global.vibrance + suggestion.suggested.global.vibrance) * 0.5
    );
    assert_eq!(
        original_bits,
        image.pixels.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
    );
    for amount in [f32::NAN, f32::INFINITY, -0.1, 1.01] {
        assert!(suggestion.recipe_at(amount).is_err());
    }
}

#[test]
fn local_paint_does_not_compensate_global_metering() {
    let image = varied();
    let plain = DevelopmentRecipe::default();
    let mut local = plain.clone();
    local.regions.push(RegionAdjustment {
        id: "bright".into(),
        name: "Exposure patch".into(),
        note: String::new(),
        shape: RegionShape::Rectangle {
            min: [0.0, 0.0],
            max: [1.0, 1.0],
        },
        feather: 0.0,
        enabled: true,
        adjustments: Adjustments {
            exposure: 4.0,
            ..Default::default()
        },
        source_range: None,
    });
    let a = analyze_adaptive(&image, &plain).unwrap();
    let b = analyze_adaptive(&image, &local).unwrap();
    assert_eq!(a.stats, b.stats);
    assert_eq!(a.suggested.global, b.suggested.global);
    assert_eq!(b.suggested.regions, local.regions);
}

#[test]
fn low_key_high_key_and_saturated_subjects_keep_their_identity() {
    let low = fixture(128, 64, |i| {
        if i % 128 < 90 {
            [0.001; 3]
        } else {
            [0.2 + (i % 17) as f32 * 0.02; 3]
        }
    });
    let s = analyze_adaptive(&low, &DevelopmentRecipe::default()).unwrap();
    assert!(s.stats.dark_fraction > 0.65 && s.stats.luminance_percentiles[3] > 0.1);
    assert_eq!(s.suggested.global.exposure, 0.0);
    assert_eq!(s.suggested.global.shadows, 0.0);
    assert_eq!(s.suggested.global.contrast, 0.0);

    let mut high = fixture(128, 64, |i| [0.7 + (i % 128) as f32 * 0.004; 3]);
    high.origin = ImageOrigin::DisplayReferred;
    let s = analyze_adaptive(&high, &DevelopmentRecipe::default()).unwrap();
    assert!(s.stats.luminance_percentiles[1] > 0.45);
    assert_eq!(s.suggested.global.exposure, 0.0);
    assert_eq!(s.suggested.global.contrast, 0.0);
    assert!(
        s.suggested.global.highlights < 0.0,
        "bright control did not exercise compression"
    );

    let colored = fixture(128, 64, |i| {
        let v = 0.1 + (i % 128) as f32 * 0.005;
        match i % 3 {
            0 => [v, 0.0, 0.0],
            1 => [0.0, v, 0.0],
            _ => [0.0, 0.0, v],
        }
    });
    let s = analyze_adaptive(&colored, &DevelopmentRecipe::default()).unwrap();
    assert!(s.stats.saturated_color_fraction > 0.99);
    assert_eq!(s.suggested.global.vibrance, 0.0);
    assert_eq!(s.suggested.global.temperature, 0.0);
    assert_eq!(s.suggested.global.tint, 0.0);
}

#[test]
fn separated_black_white_compositions_and_isolated_color_outliers_are_not_reinterpreted() {
    let target = fixture(128, 64, |i| {
        if i % 128 < 70 {
            [0.005 + (i % 17) as f32 * 0.001; 3]
        } else {
            [0.75 + (i % 19) as f32 * 0.007; 3]
        }
    });
    let s = analyze_adaptive(&target, &DevelopmentRecipe::default()).unwrap();
    assert!(s.stats.luminance_percentiles[2] < 0.05);
    assert!(s.stats.luminance_percentiles[3] > 0.65);
    assert_eq!(s.suggested, s.base);
    let mostly_gray = fixture(128, 64, |i| {
        if i % 128 == 0 {
            [0.5, 0.2, 0.1]
        } else {
            [0.08 + (i % 128) as f32 * 0.003; 3]
        }
    });
    let s = analyze_adaptive(&mostly_gray, &DevelopmentRecipe::default()).unwrap();
    assert_eq!(s.suggested.global.vibrance, 0.0);
    assert!(
        s.suggested.global.contrast > 0.0,
        "gray control did not exercise a real tone suggestion"
    );
    let gray_with_small_channel_noise = fixture(128, 64, |i| {
        if i % 128 < 80 {
            let v = 0.021 + (i % 37) as f32 * 0.0007;
            [v + 0.008, v, v - 0.004]
        } else {
            [0.4 + (i % 23) as f32 * 0.02; 3]
        }
    });
    assert!(
        gray_with_small_channel_noise
            .pixels
            .as_chunks::<3>()
            .0
            .iter()
            .filter(|p| (p[0] - p[2]) / p[0] > 0.1)
            .count()
            > gray_with_small_channel_noise.pixels.len() / 6,
        "negative control must fool a purely relative chroma detector"
    );
    let s = analyze_adaptive(
        &gray_with_small_channel_noise,
        &DevelopmentRecipe::default(),
    )
    .unwrap();
    assert_eq!(s.suggested.global.vibrance, 0.0);

    let sparse_color = fixture(128, 64, |i| {
        let v = 0.14 + (i % 16) as f32 * 0.012;
        if i % 4 == 0 {
            [v * 1.3, v, v * 0.7]
        } else {
            [v; 3]
        }
    });
    let s = analyze_adaptive(&sparse_color, &DevelopmentRecipe::default()).unwrap();
    let before = sparse_color.render_sdr16(&s.base).unwrap();
    let after = sparse_color.render_sdr16(&s.suggested).unwrap();
    assert!(
        s.suggested.global.vibrance > 5.0,
        "real color support should receive a useful editable lift"
    );
    assert_ne!(before, after);
    // Neutral samples must stay neutral even though the colored quarter changes.
    for (i, p) in after.as_chunks::<3>().0.iter().enumerate() {
        if i % 4 != 0 {
            assert_eq!(p[0], p[1]);
            assert_eq!(p[1], p[2]);
        }
    }
}

#[test]
fn bright_color_outliers_do_not_cancel_useful_middle_tone_correction() {
    let mut image = fixture(128, 96, |i| {
        if i % 131 == 0 {
            [0.99, 0.65, 0.4]
        } else {
            let v = 0.025 + (i % 127) as f32 * 0.001;
            [v * 1.3, v, v * 0.7]
        }
    });
    image.origin = ImageOrigin::DisplayReferred;
    let s = analyze_adaptive(&image, &DevelopmentRecipe::default()).unwrap();
    assert!(s.stats.luminance_percentiles[2] < 0.12);
    assert!(
        s.after_stats.luminance_percentiles[2] > s.stats.luminance_percentiles[2] * 1.20,
        "highlight protection erased the requested tonal correction: {:?}",
        s.changes
    );
    assert!(
        s.suggested.global.highlights < -1.0,
        "fixture must exercise highlight protection"
    );
    assert!(s.suggested.global.vibrance > 5.0);
    assert_eq!(s.after_stats.above_white_fraction, 0.0);
}

fn region_recipe() -> DevelopmentRecipe {
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "bright-part".into(),
        name: "Bright wing".into(),
        note: "retain annotation".into(),
        shape: RegionShape::Rectangle {
            min: [0.5, 0.0],
            max: [1.0, 1.0],
        },
        feather: 0.2,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: Some(SourceRange { first: 3, last: 7 }),
    });
    recipe
}

#[test]
fn regional_highlight_treatment_has_exact_scope_and_frozen_strength() {
    let image = fixture(128, 96, |i| {
        if i % 128 < 64 {
            [0.12, 0.08, 0.05]
        } else {
            let v = 0.7 + (i % 64) as f32 * 0.03;
            [v, v * 0.95, v * 0.9]
        }
    });
    let base = region_recipe();
    let s = analyze_adaptive_region(
        &image,
        &base,
        "bright-part",
        AdaptiveIntent::RestoreHighlights,
    )
    .unwrap();
    assert!(s.highlights.bright_fraction > 0.8 && s.highlights.bright_luminance_span > 0.1);
    assert_eq!(s.highlights.stored_white_channel_fraction, None);
    assert!(s.suggested.regions[0].adjustments.highlights < -15.0);
    assert_eq!(s.suggested.global, base.global);
    assert_eq!(s.suggested.hdr, base.hdr);
    let mut structure = s.suggested.clone();
    structure.regions[0].adjustments = base.regions[0].adjustments;
    assert_eq!(structure, base, "annotation/source constraint changed");
    assert_eq!(s.recipe_at(0.0).unwrap(), base);
    let half_before = s.recipe_at(0.5).unwrap();
    let _ = s.recipe_at(0.1).unwrap();
    let _ = s.recipe_at(1.0).unwrap();
    assert_eq!(half_before, s.recipe_at(0.5).unwrap());
    let before = image.render_sdr16(&base).unwrap();
    let after = image.render_sdr16(&s.suggested).unwrap();
    let mut changed = 0;
    for i in 0..128 * 96 {
        if i % 128 < 64 {
            assert_eq!(&before[i * 3..i * 3 + 3], &after[i * 3..i * 3 + 3]);
        } else if before[i * 3..i * 3 + 3] != after[i * 3..i * 3 + 3] {
            changed += 1;
        }
    }
    assert!(
        changed > 1000,
        "selected-region positive control did not change pixels"
    );
}

#[test]
fn clipped_white_is_dimmed_without_inventing_texture_or_claiming_recovery() {
    let mut image = fixture(128, 96, |i| if i % 128 < 64 { [0.1; 3] } else { [1.0; 3] });
    image.origin = ImageOrigin::DisplayReferred;
    let mut base = region_recipe();
    base.regions[0].feather = 0.0;
    let s = analyze_adaptive_region(
        &image,
        &base,
        "bright-part",
        AdaptiveIntent::RestoreHighlights,
    )
    .unwrap();
    assert_eq!(s.highlights.stored_white_channel_fraction, Some(1.0));
    assert_eq!(s.highlights.bright_luminance_span, 0.0);
    assert!(s.highlights.assessment.contains("cannot restore"));
    let after = image.render_sdr16(&s.suggested).unwrap();
    let value = after[64 * 3];
    assert!(value < 64000 && value > 50000);
    for i in 0..128 * 96 {
        if i % 128 >= 64 {
            assert_eq!(&after[i * 3..i * 3 + 3], &[value; 3]);
        }
    }
    let dark = fixture(128, 96, |_| [0.12; 3]);
    let unchanged = analyze_adaptive_region(
        &dark,
        &base,
        "bright-part",
        AdaptiveIntent::RestoreHighlights,
    )
    .unwrap();
    assert_eq!(unchanged.suggested, base);
}

#[test]
fn small_region_metering_is_local_and_disabled_regions_are_rejected() {
    let image = fixture(1000, 800, |i| {
        let x = i % 1000;
        let y = i / 1000;
        if (480..520).contains(&x) && (380..420).contains(&y) {
            let v = 0.02 + (x - 480) as f32 * 0.0015;
            [v * 1.3, v, v * 0.7]
        } else {
            [0.0; 3]
        }
    });
    let mut base = region_recipe();
    base.regions[0].shape = RegionShape::Ellipse {
        center: [0.5, 0.5],
        radius: [0.018, 0.022],
    };
    let s = analyze_adaptive_region(&image, &base, "bright-part", AdaptiveIntent::Balance).unwrap();
    assert!(s.stats.sample_count > 400 && s.stats.sample_count < 1600);
    assert!(s.suggested.regions[0].adjustments.exposure > 0.3);
    assert_eq!(s.suggested.global, base.global);
    assert!(analyze_adaptive_region(&image, &base, "missing", AdaptiveIntent::Balance).is_err());
    base.regions[0].enabled = false;
    assert!(
        analyze_adaptive_region(&image, &base, "bright-part", AdaptiveIntent::Balance).is_err()
    );
}

#[test]
fn feathered_exposure_cannot_invent_recorded_highlight_variation() {
    let image = fixture(128, 96, |_| [0.3; 3]);
    let mut base = region_recipe();
    base.regions[0].feather = 1.0;
    base.regions[0].adjustments.exposure = 4.0;
    let s = analyze_adaptive_region(
        &image,
        &base,
        "bright-part",
        AdaptiveIntent::RestoreHighlights,
    )
    .unwrap();
    assert!(
        s.highlights.bright_fraction > 0.5,
        "fixture never exercised bright edited light"
    );
    assert_eq!(
        s.highlights.bright_luminance_span, 0.0,
        "the feather's gradient was mistaken for recorded variation"
    );
    assert!(s.highlights.assessment.contains("Little variation"));
}

#[test]
fn actual_tone_stays_ordered_and_keeps_linear_headroom_without_new_clipping() {
    let image = fixture(128, 64, |i| {
        let v = (-8.0 + (i % 128) as f32 * 10.0 / 127.0).exp2();
        [v, v * 0.85, v * 0.6]
    });
    let mut recipe = DevelopmentRecipe::default();
    recipe.hdr.peak_nits = 500.0;
    let s = analyze_adaptive(&image, &recipe).unwrap();
    assert!(s.stats.above_white_fraction > 0.05);
    assert!(s.suggested.global.highlights < 0.0);
    let mut previous = 0.0;
    for i in 0..2048 {
        let v = (-20.0 + i as f32 * 26.0 / 2047.0).exp2();
        let p = s.suggested.global.apply([v; 3], 1.0);
        assert_eq!(p[0], p[1], "gray acquired a color cast");
        assert_eq!(p[1], p[2]);
        assert!(p[0] >= previous, "neutral light order reversed");
        previous = p[0];
    }
    assert!(
        s.suggested.global.apply([4.0; 3], 1.0)[0] > 1.0,
        "float headroom was clipped away"
    );
    let count = |recipe: &DevelopmentRecipe| {
        image
            .pixels
            .as_chunks::<3>()
            .0
            .iter()
            .flat_map(|p| recipe.global.apply([p[0], p[1], p[2]], 1.0))
            .filter(|&v| v > s.stats.delivery_ceiling)
            .count()
    };
    assert!(count(&s.suggested) <= count(&s.base));
}

#[test]
fn hdr_point_lights_and_bright_colors_are_not_mistaken_for_sdr_clipping() {
    let image = fixture(128, 64, |i| {
        if i % 128 < 110 {
            let v = 0.08 + (i % 110) as f32 * 0.004;
            [v, v, v]
        } else {
            match i % 3 {
                0 => [3.0, 1.2, 0.4],
                1 => [0.8, 2.5, 1.2],
                _ => [2.0; 3],
            }
        }
    });
    let hdr = analyze_adaptive(&image, &DevelopmentRecipe::default()).unwrap();
    assert!(
        hdr.stats.above_white_fraction > 0.1,
        "fixture did not contain meaningful HDR light"
    );
    assert!(hdr.stats.delivery_ceiling > 4.0);
    assert_eq!(hdr.suggested.global.highlights, 0.0);
    assert_eq!(hdr.suggested.global.whites, 0.0);
    let mut sdr = image.clone();
    sdr.origin = ImageOrigin::DisplayReferred;
    let sdr = analyze_adaptive(&sdr, &DevelopmentRecipe::default()).unwrap();
    assert!(
        sdr.suggested.global.highlights < -10.0,
        "delivery target negative control had no effect"
    );
}

#[test]
fn sampling_is_bounded_deterministic_and_checks_spatial_phase_bias() {
    let image = fixture(1200, 800, |i| {
        let y = (i / 1200) as f32 / 800.0;
        let x = (i % 1200) as f32 / 1200.0;
        [0.03 + x * 0.4, 0.05 + y * 0.35, 0.04 + x * y * 0.3]
    });
    let a = analyze_adaptive(&image, &DevelopmentRecipe::default()).unwrap();
    let b = analyze_adaptive(&image, &DevelopmentRecipe::default()).unwrap();
    assert_eq!(a, b);
    assert!(a.stats.sample_count <= 16_384 && a.stats.sample_count > 16_000);
    assert!(a.stats.sampling_disagreement_stops < 0.1);
    let comb = fixture(128, 128, |i| if i % 2 == 0 { [0.01; 3] } else { [0.7; 3] });
    let s = analyze_adaptive(&comb, &DevelopmentRecipe::default()).unwrap();
    assert!(
        s.stats.sampling_disagreement_stops > 0.75,
        "phase destroyer was not detected"
    );
    assert_eq!(s.suggested, s.base);
}

#[test]
fn invalid_geometry_metadata_and_sampled_nonfinite_values_fail() {
    let mut image = varied();
    image.pixels[0] = f32::NAN;
    assert!(analyze_adaptive(&image, &DevelopmentRecipe::default()).is_err());
    let mut image = varied();
    image.baseline = Some(DisplayBaseline {
        black: 1.0,
        white: 1.0,
        contrast: 0.5,
        exposure_gain: 1.0,
    });
    assert!(analyze_adaptive(&image, &DevelopmentRecipe::default()).is_err());
    let mut image = varied();
    image.width = 0;
    assert!(analyze_adaptive(&image, &DevelopmentRecipe::default()).is_err());
}
