use std::sync::atomic::AtomicBool;
use strehl_edit::*;

fn image(width: u32, height: u32, f: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
    let mut pixels = Vec::with_capacity(width as usize * height as usize * 3);
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
fn textured() -> LinearImage {
    image(96, 80, |x, y| {
        let v = 0.04 + 0.003 * x as f32 + 0.016 * (y % 7) as f32;
        [v * 1.2, v, v * 0.65]
    })
}
fn region(id: &str) -> RegionAdjustment {
    RegionAdjustment {
        id: id.into(),
        name: "Test".into(),
        note: String::new(),
        shape: RegionShape::Rectangle {
            min: [0.25, 0.2],
            max: [0.75, 0.8],
        },
        feather: 0.2,
        enabled: true,
        adjustments: Default::default(),
        source_range: Some(SourceRange { first: 3, last: 8 }),
    }
}

#[test]
fn spatial_response_is_not_a_global_curve_and_black_white_edges_stay_flat() {
    // Equal RGB patches appear in two different local tonal neighborhoods. A
    // global curve cannot pass the positive control even if it changes pixels.
    let scene = image(120, 80, |x, y| {
        let base = if x < 60 { 0.09 } else { 0.30 };
        let v = if (x % 60 > 24 && x % 60 < 36) && (30..50).contains(&y) {
            0.18
        } else {
            base + (x % 5) as f32 * 0.012
        };
        [v; 3]
    });
    let s = analyze_adaptive(&scene, &DevelopmentRecipe::default()).unwrap();
    let left = scene.developed_pixel(40 * 120 + 30, &s.suggested)[0];
    let right = scene.developed_pixel(40 * 120 + 90, &s.suggested)[0];
    assert!(
        (left - right).abs() > 0.0002,
        "identical RGB ignored different neighborhoods: {left} {right}"
    );
    assert_eq!(s.suggested.global, s.base.global);
    let edge = image(120, 80, |x, _| if x < 60 { [0.04; 3] } else { [0.85; 3] });
    let e = analyze_adaptive(&edge, &DevelopmentRecipe::default()).unwrap();
    // An edge-related gain halo would create a slope in one of these constant
    // surfaces. This is not a general natural-image quality acceptance metric.
    for (start, end) in [(0, 60), (60, 120)] {
        let values: Vec<_> = (start..end)
            .map(|x| edge.developed_pixel(40 * 120 + x, &e.suggested)[0])
            .collect();
        let span = values.iter().copied().fold(f32::NEG_INFINITY, f32::max)
            - values.iter().copied().fold(f32::INFINITY, f32::min);
        assert!(
            span < 0.0005,
            "manufactured an edge halo on a flat surface: {span}"
        );
    }
}

#[test]
fn persisted_field_and_native_region_use_the_same_full_image_coordinates() {
    let mut image = textured();
    image.origin = ImageOrigin::SceneLinear;
    let base = DevelopmentRecipe::default();
    let s = analyze_adaptive(&image, &base).unwrap();
    assert!(!s.suggested.spatial.is_empty());
    assert_eq!(
        image.render_sdr16(&base).unwrap(),
        image.render_sdr16(&s.recipe_at(0.0).unwrap()).unwrap()
    );
    let json = serde_json::to_vec(&s.suggested).unwrap();
    let restored: DevelopmentRecipe = serde_json::from_slice(&json).unwrap();
    assert_eq!(restored, s.suggested);
    assert_eq!(
        image.render_sdr16(&restored).unwrap(),
        image.render_sdr16(&s.suggested).unwrap()
    );
    let region = DisplayRegionRequest {
        min: [13, 17],
        max: [74, 63],
        stride: 1,
    };
    let patch = image
        .render_display_region_mode(&restored, region, &AtomicBool::new(false), true)
        .unwrap();
    for y in 0..46usize {
        for x in 0..61usize {
            let actual = &patch.rgba_linear[(y * 61 + x) * 4..(y * 61 + x) * 4 + 3];
            let expected = image.developed_pixel((y + 17) * 96 + x + 13, &restored);
            assert_eq!(actual, expected, "patch changed annotation/treatment UV");
        }
    }
    let old = r#"{"version":1,"global":{},"regions":[],"hdr":{}}"#;
    assert!(
        serde_json::from_str::<DevelopmentRecipe>(old)
            .unwrap()
            .spatial
            .is_empty()
    );
}

#[test]
fn scoped_spatial_treatment_preserves_other_regions_and_source_constraints() {
    let image = textured();
    let mut base = DevelopmentRecipe::default();
    base.regions.push(region("scope"));
    let s = analyze_adaptive_region(&image, &base, "scope", AdaptiveIntent::Balance).unwrap();
    assert_eq!(s.suggested.regions, base.regions);
    assert!(s.suggested.adaptive_scope(Some("scope")).is_some());
    let before = image.render_sdr16(&base).unwrap();
    let after = image.render_sdr16(&s.suggested).unwrap();
    let mut changed = 0;
    for y in 0..80usize {
        for x in 0..96usize {
            let i = y * 96 + x;
            if !base.regions[0]
                .shape
                .contains([(x as f32 + 0.5) / 96.0, (y as f32 + 0.5) / 80.0])
            {
                assert_eq!(before[i * 3..i * 3 + 3], after[i * 3..i * 3 + 3]);
            } else if before[i * 3..i * 3 + 3] != after[i * 3..i * 3 + 3] {
                changed += 1;
            }
        }
    }
    assert!(
        changed > 200,
        "local positive control never exercised treatment"
    );
    let mut disabled = s.suggested.clone();
    disabled.regions[0].enabled = false;
    let mut deleted = s.suggested.clone();
    deleted.regions.clear();
    assert!(
        deleted.validate().is_err(),
        "orphaned local treatment must be rejected"
    );
    deleted.clear_adaptive_scope(Some("scope"));
    deleted.validate().unwrap();
    assert_eq!(image.render_sdr16(&disabled).unwrap(), before);
    assert_eq!(image.render_sdr16(&deleted).unwrap(), before);
    let again =
        analyze_adaptive_region(&image, &s.suggested, "scope", AdaptiveIntent::Balance).unwrap();
    assert_eq!(again.recipe_at(0.0).unwrap(), s.suggested);
    let half = again.recipe_at(0.5).unwrap();
    let _ = again.recipe_at(0.8).unwrap();
    assert_eq!(half, again.recipe_at(0.5).unwrap());
    assert_eq!(half.spatial.len(), 1);
}

#[test]
fn reanalysis_blending_retains_effective_amount_for_portable_presets() {
    let image = textured();
    let original = analyze_adaptive(&image, &DevelopmentRecipe::default()).unwrap();
    let base = original.recipe_at(0.4).unwrap();
    let second = analyze_adaptive(&image, &base).unwrap();
    let halfway = second.recipe_at(0.5).unwrap();
    let field = halfway.adaptive_scope(None).unwrap();
    assert!(
        (field.amount - 0.7).abs() < 1e-6,
        "halfway treatment lost its portable effective Amount"
    );
    let preset_base = DevelopmentRecipe::default();
    let on_destination = analyze_adaptive_with_parameters(
        &image,
        &preset_base,
        None,
        AdaptiveIntent::Balance,
        field.parameters,
    )
    .unwrap()
    .recipe_at(field.amount)
    .unwrap();
    let a = image.render_sdr16(&halfway).unwrap();
    let b = image.render_sdr16(&on_destination).unwrap();
    assert!(
        a.iter().zip(&b).all(|(x, y)| x.abs_diff(*y) <= 1),
        "preset recapture double-applied or strengthened Adaptive"
    );
    assert_ne!(
        a,
        image
            .render_sdr16(&original.recipe_at(1.0).unwrap())
            .unwrap(),
        "fixture did not distinguish.7from1"
    );
}

#[test]
fn bounded_fields_fit_sidecar_with_maximum_text_annotations_and_reject_malformed_data() {
    let mut recipe = DevelopmentRecipe::default();
    for i in 0..128 {
        let mut r = region(&format!("r{i}"));
        r.note = "n".repeat(4096);
        r.name = "N".repeat(256);
        recipe.regions.push(r);
    }
    let template = SpatialTreatment {
        version: 1,
        target_region: None,
        parameters: Default::default(),
        amount: 1.0,
        bounds: [[0.0, 0.0], [1.0, 1.0]],
        width: 20,
        height: 20,
        levels: 33,
        log_min: -12.0,
        log_max: 4.0,
        tone_ev: vec![-0.123291016; 20 * 20 * 33],
        color_gain: vec![1.0488281; 20 * 20],
        delivery_ceiling: 4.9261084,
        centering_ev: 0.012345678,
    };
    for i in 0..MAX_SPATIAL_TREATMENTS {
        let mut f = template.clone();
        f.target_region = Some(format!("r{i}"));
        recipe.spatial.push(f);
    }
    recipe.validate().unwrap();
    let bytes = serde_json::to_vec_pretty(&recipe).unwrap();
    assert!(
        bytes.len() < 2 * 1024 * 1024 - 4096,
        "maximum text annotations plus bounded fields do not fit: {}",
        bytes.len()
    );
    assert_eq!(
        serde_json::from_slice::<DevelopmentRecipe>(&bytes).unwrap(),
        recipe
    );
    let text = String::from_utf8(bytes).unwrap();
    assert!(
        serde_json::from_str::<DevelopmentRecipe>(&text.replacen("f32hex:", "unknown:", 1))
            .is_err()
    );
    assert!(
        serde_json::from_str::<DevelopmentRecipe>(&text.replacen("f32hex:", "f32hex:z", 1))
            .is_err()
    );
    let mut wrong = recipe.clone();
    wrong.spatial[0].tone_ev.pop();
    assert!(wrong.validate().is_err());
    let mut wrong = recipe.clone();
    wrong.spatial[0].tone_ev[0] = f32::NAN;
    assert!(wrong.validate().is_err());
    let mut wrong = recipe.clone();
    wrong.spatial[0].width = 1000;
    assert!(wrong.validate().is_err());
    let mut wrong = recipe.clone();
    wrong.spatial[0].target_region = wrong.spatial[1].target_region.clone();
    assert!(wrong.validate().is_err());
    let mut wrong = recipe.clone();
    wrong.spatial.push(template);
    assert!(wrong.validate().is_err());
}
