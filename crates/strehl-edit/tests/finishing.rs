//! P7 recipe additions: compatibility with earlier builds, strokes, crop
//! geometry, caps, and the white-balance pick.
use strehl_edit::*;

/// The recipe schema of the pre-P7 build (61effa01b), field for field, with
/// its `deny_unknown_fields`. Standing in for "an older build reads this".
mod older {
    use serde::Deserialize;
    #[derive(Deserialize)]
    #[serde(default, deny_unknown_fields)]
    #[allow(dead_code)]
    pub struct Recipe {
        pub version: u32,
        pub global: serde_json::Value,
        pub regions: Vec<Region>,
        pub hdr: serde_json::Value,
        pub spatial: Vec<serde_json::Value>,
    }
    impl Default for Recipe {
        fn default() -> Self {
            Self {
                version: 1,
                global: serde_json::Value::Null,
                regions: Vec::new(),
                hdr: serde_json::Value::Null,
                spatial: Vec::new(),
            }
        }
    }
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    #[allow(dead_code)]
    pub struct Region {
        pub id: String,
        pub name: String,
        #[serde(default)]
        pub note: String,
        pub shape: Shape,
        pub feather: f32,
        pub enabled: bool,
        #[serde(default)]
        pub adjustments: serde_json::Value,
        #[serde(default)]
        pub source_range: Option<serde_json::Value>,
    }
    #[derive(Deserialize)]
    #[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
    #[allow(dead_code)]
    pub enum Shape {
        Ellipse { center: [f32; 2], radius: [f32; 2] },
        Rectangle { min: [f32; 2], max: [f32; 2] },
        Polygon { points: Vec<[f32; 2]> },
    }
}

fn region(id: &str, shape: RegionShape) -> RegionAdjustment {
    RegionAdjustment {
        id: id.into(),
        name: id.into(),
        note: String::new(),
        shape,
        feather: 0.5,
        enabled: true,
        adjustments: Adjustments {
            exposure: 1.0,
            ..Default::default()
        },
        source_range: None,
    }
}

fn stroke(points: Vec<[f32; 2]>, r: f32) -> RegionShape {
    RegionShape::Stroke {
        points,
        radius: [r, r],
    }
}

#[test]
fn option_free_recipes_stay_readable_by_the_older_schema_and_new_fields_are_refused() {
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(region(
        "e",
        RegionShape::Ellipse {
            center: [0.5, 0.5],
            radius: [0.2, 0.2],
        },
    ));
    let text = serde_json::to_string_pretty(&recipe).unwrap();
    serde_json::from_str::<older::Recipe>(&text).expect("older build must read it");
    for key in ["crop", "scale_bar", "heals", "backdrop", "layers_order"] {
        assert!(!text.contains(key), "{key} serialized while unused");
    }
    // Each new feature, used, is refused by the older schema: it falls back
    // to the master's baked recipe with a warning (implementation plan 7.5).
    let mut variants = Vec::new();
    let mut v = recipe.clone();
    v.crop = Some(Crop {
        min: [0.1, 0.1],
        max: [0.9, 0.9],
        angle_deg: 0.0,
    });
    variants.push(v);
    let mut v = recipe.clone();
    v.scale_bar = Some(ScaleBar {
        enabled: true,
        length_um: 500.0,
        corner: ScaleBarCorner::BottomRight,
        style: ScaleBarStyle::Light,
    });
    variants.push(v);
    let mut v = recipe.clone();
    v.heals.push(Heal {
        enabled: true,
        center: [0.3, 0.3],
        radius: [0.01, 0.01],
        source_offset: [0.05, 0.0],
    });
    variants.push(v);
    let mut v = recipe.clone();
    v.backdrop = Some(Backdrop {
        enabled: true,
        key: BackdropKey::Light,
        threshold: 0.8,
        softness: 1.0,
    });
    variants.push(v);
    let mut v = recipe.clone();
    v.layers_order = vec!["e".into()];
    variants.push(v);
    let mut v = recipe.clone();
    v.regions[0].shape = stroke(vec![[0.2, 0.2], [0.4, 0.3]], 0.02);
    variants.push(v);
    for v in variants {
        v.validate().unwrap();
        assert!(v.uses_finishing());
        let text = serde_json::to_string(&v).unwrap();
        assert!(
            serde_json::from_str::<older::Recipe>(&text).is_err(),
            "{text}"
        );
        assert_eq!(serde_json::from_str::<DevelopmentRecipe>(&text).unwrap(), v);
    }
}

#[test]
fn stroke_weight_follows_the_polyline_within_its_radius() {
    let shape = stroke(vec![[0.2, 0.5], [0.8, 0.5]], 0.1);
    assert_eq!(shape.weight([0.5, 0.5], 0.0), 1.0);
    assert_eq!(shape.weight([0.5, 0.59], 0.0), 1.0);
    assert_eq!(shape.weight([0.5, 0.61], 0.0), 0.0);
    assert_eq!(shape.weight([0.15, 0.5], 0.0), 1.0, "round cap");
    assert_eq!(shape.weight([0.05, 0.5], 0.0), 0.0);
    let soft = shape.weight([0.5, 0.57], 0.5);
    assert!(
        soft > 0.0 && soft < 1.0,
        "feather is a fraction of the radius"
    );
    let (min, max) = shape.bounds();
    assert!((min[0] - 0.1).abs() < 1e-6 && (max[0] - 0.9).abs() < 1e-6);
    assert!((min[1] - 0.4).abs() < 1e-6 && (max[1] - 0.6).abs() < 1e-6);
    // A single point is a dab; per-axis radii make it round in pixels.
    let dab = RegionShape::Stroke {
        points: vec![[0.5, 0.5]],
        radius: [0.05, 0.1],
    };
    assert_eq!(dab.weight([0.54, 0.5], 0.0), 1.0);
    assert_eq!(dab.weight([0.56, 0.5], 0.0), 0.0);
    assert_eq!(dab.weight([0.5, 0.59], 0.0), 1.0);
    let json = serde_json::to_string(&dab).unwrap();
    assert_eq!(
        json,
        r#"{"kind":"stroke","points":[[0.5,0.5]],"radius":[0.05,0.1]}"#
    );
    assert_eq!(serde_json::from_str::<RegionShape>(&json).unwrap(), dab);
}

#[test]
fn brush_paths_simplify_within_a_tenth_of_the_radius_and_respect_caps() {
    let path: Vec<[f32; 2]> = (0..20_000)
        .map(|i| {
            let t = i as f32 / 19_999.0;
            [0.1 + 0.8 * t, 0.5 + 0.2 * (t * 12.0).sin()]
        })
        .collect();
    let radius = [0.01, 0.015];
    let shape = RegionShape::stroke_from_path(&path, radius);
    let RegionShape::Stroke { points, .. } = &shape else {
        panic!()
    };
    assert!(points.len() <= MAX_STROKE_POINTS && points.len() > 10);
    assert_eq!(points[0], path[0]);
    assert_eq!(*points.last().unwrap(), *path.last().unwrap());
    shape.validate().unwrap();
    // Every original path point stays well inside the simplified stroke.
    for p in path.iter().step_by(37) {
        assert_eq!(shape.weight(*p, 0.0), 1.0, "{p:?}");
    }
    assert!(
        stroke(vec![[0.5, 0.5]; MAX_STROKE_POINTS + 1], 0.01)
            .validate()
            .is_err()
    );
    assert!(stroke(vec![], 0.01).validate().is_err());
    assert!(stroke(vec![[0.5, 1.2]], 0.01).validate().is_err());
    let mut recipe = DevelopmentRecipe::default();
    for i in 0..(MAX_RECIPE_STROKE_POINTS / MAX_STROKE_POINTS + 1) {
        recipe.regions.push(region(
            &format!("s{i}"),
            stroke(vec![[0.5, 0.5]; MAX_STROKE_POINTS], 0.01),
        ));
    }
    assert!(recipe.validate().is_err(), "recipe-wide stroke cap");
}

#[test]
fn the_largest_stroke_recipe_fits_the_engine_recipe_cap() {
    // Engine: --region-recipe is refused above 1 MiB (region-repair.rs).
    let mut recipe = DevelopmentRecipe::default();
    let per = MAX_RECIPE_STROKE_POINTS / 8;
    for i in 0..8 {
        let points = (0..per)
            .map(|k| {
                [
                    0.123_456_79 + k as f32 * 1e-4,
                    0.876_543_2 - k as f32 * 7e-5,
                ]
            })
            .collect();
        let mut r = region(&format!("stroke-{i}"), stroke(points, 0.012_345_67));
        r.source_range = Some(SourceRange { first: 3, last: 9 });
        recipe.regions.push(r);
    }
    recipe.validate().unwrap();
    let pretty = serde_json::to_vec_pretty(&recipe).unwrap();
    // MEASURED when written: 8192 points took 587,702 bytes, so the cap is 4096.
    println!("largest stroke recipe: {} bytes pretty", pretty.len());
    assert!(pretty.len() < 320 * 1024, "{} bytes", pretty.len());
}

#[test]
fn crop_geometry_fits_rounds_and_shrinks_about_its_centre() {
    let crop = Crop {
        min: [0.1, 0.2],
        max: [0.6, 0.7],
        angle_deg: 0.0,
    };
    crop.validate().unwrap();
    assert_eq!(crop.pixel_rect(1000, 800), [100, 160, 600, 560]);
    assert_eq!(crop.output_size(1000, 800), [500, 400]);
    assert!(crop.fits(1000, 800));
    let turned = Crop {
        min: [0.0, 0.0],
        max: [1.0, 1.0],
        angle_deg: 5.0,
    };
    assert!(
        !turned.fits(1000, 800),
        "a turned full frame leaves the photograph"
    );
    let fitted = turned.fit_inside(1000, 800);
    assert!(fitted.fits(1000, 800));
    let size = fitted.output_size(1000, 800);
    assert!(size[0] > 800 && size[0] < 1000, "{size:?}");
    let aspect = |c: &Crop| (c.max[0] - c.min[0]) * 1000.0 / ((c.max[1] - c.min[1]) * 800.0);
    assert!(
        (aspect(&fitted) - aspect(&turned)).abs() < 1e-3,
        "aspect kept"
    );
    let json = serde_json::to_string(&crop).unwrap();
    assert!(!json.contains("angle_deg"), "zero angle is omitted: {json}");
    for bad in [
        Crop {
            angle_deg: 46.0,
            ..crop
        },
        Crop {
            max: [0.1, 0.7],
            ..crop
        },
        Crop {
            min: [-0.1, 0.2],
            ..crop
        },
    ] {
        assert!(bad.validate().is_err());
    }
}

#[test]
fn scale_bar_labels_and_suggestions_use_round_lengths() {
    let bar = |length_um| ScaleBar {
        enabled: true,
        length_um,
        corner: ScaleBarCorner::BottomLeft,
        style: ScaleBarStyle::Dark,
    };
    assert_eq!(bar(500.0).label(), "500 µm");
    assert_eq!(bar(2.5).label(), "2.5 µm");
    assert_eq!(bar(1000.0).label(), "1 mm");
    assert_eq!(bar(1500.0).label(), "1.5 mm");
    // 1.2 µm/px over 2560 px: a fifth is 614 µm, nearest 1-2-5 is 500.
    assert_eq!(ScaleBar::suggested_length_um(1.2, 2560), 500.0);
    assert_eq!(ScaleBar::suggested_length_um(0.05, 7000), 50.0);
    assert!(bar(0.0).validate().is_err());
}

#[test]
fn heals_and_backdrops_validate_their_geometry() {
    let heal = Heal {
        enabled: true,
        center: [0.4, 0.4],
        radius: [0.02, 0.03],
        source_offset: [0.05, 0.0],
    };
    heal.validate().unwrap();
    for bad in [
        Heal {
            enabled: true,
            source_offset: [0.01, 0.0],
            ..heal
        },
        Heal {
            enabled: true,
            source_offset: [0.7, 0.0],
            ..heal
        },
        Heal {
            enabled: true,
            radius: [0.3, 0.3],
            ..heal
        },
    ] {
        assert!(bad.validate().is_err(), "{bad:?}");
    }
    let recipe = DevelopmentRecipe {
        heals: vec![heal; MAX_HEALS + 1],
        ..Default::default()
    };
    assert!(recipe.validate().is_err());
    let backdrop = Backdrop {
        enabled: true,
        key: BackdropKey::Light,
        threshold: 0.5,
        softness: 1.0,
    };
    assert_eq!(backdrop.membership(0.5), 1.0);
    assert_eq!(backdrop.membership(0.25), 0.0);
    assert!(backdrop.membership(0.35) > 0.0 && backdrop.membership(0.35) < 1.0);
    assert_eq!(
        Backdrop {
            enabled: true,
            key: BackdropKey::Light,
            softness: 0.0,
            ..backdrop
        }
        .membership(0.49),
        0.0
    );
    assert!(
        Backdrop {
            enabled: true,
            key: BackdropKey::Light,
            threshold: 0.0,
            ..backdrop
        }
        .validate()
        .is_err()
    );
}

fn cast_image(rgb: [f32; 3], baseline: Option<DisplayBaseline>) -> LinearImage {
    LinearImage {
        width: 40,
        height: 30,
        pixels: (0..40 * 30)
            .flat_map(|i| {
                // A neutral patch in the middle, colour elsewhere.
                let (x, y) = (i % 40, i / 40);
                if (15..25).contains(&x) && (10..20).contains(&y) {
                    rgb
                } else {
                    [0.6, 0.1, 0.05]
                }
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline,
        baked_recipe: None,
    }
}

#[test]
fn white_balance_pick_neutralizes_the_sampled_patch_through_the_recipe() {
    let baseline = DisplayBaseline {
        black: 0.002,
        white: 1.2,
        contrast: 0.55,
        exposure_gain: 1.1,
    };
    for placement in [None, Some(baseline)] {
        let image = cast_image([0.12, 0.16, 0.21], placement);
        let pick = image.pick_white_balance([0.5, 0.5], 3).unwrap();
        assert!(!pick.clamped);
        // The formulas of implementation plan 7.5, on the post-place sample.
        let [r, g, b] = pick.sample.map(f64::from);
        assert!((f64::from(pick.temperature) - 100.0 * (b / r).log2()).abs() < 1e-3);
        assert!((f64::from(pick.tint) + 200.0 * ((r * b).sqrt() / g).log2()).abs() < 1e-3);
        let mut recipe = DevelopmentRecipe::default();
        recipe.global.temperature = pick.temperature;
        recipe.global.tint = pick.tint;
        recipe.global.exposure = 0.7;
        recipe.global.contrast = 30.0;
        recipe.global.saturation = 40.0;
        let out = image.developed_pixel(15 * 40 + 20, &recipe);
        let spread = out.iter().copied().fold(f32::MIN, f32::max)
            - out.iter().copied().fold(f32::MAX, f32::min);
        assert!(spread < 1e-4 * out[1], "{out:?} not neutral");
        // Negative control: without the pick the same development is tinted.
        recipe.global.temperature = 0.0;
        recipe.global.tint = 0.0;
        let tinted = image.developed_pixel(15 * 40 + 20, &recipe);
        assert!(tinted[2] - tinted[0] > 0.05 * tinted[1]);
    }
}

#[test]
fn white_balance_pick_reports_clamping_and_refuses_impossible_samples() {
    let pick = white_balance_from_neutral([0.05, 0.2, 0.4]).unwrap();
    assert!(pick.clamped && pick.temperature == 100.0);
    assert!(white_balance_from_neutral([0.0, 0.2, 0.4]).is_none());
    assert!(white_balance_from_neutral([f32::NAN, 0.2, 0.4]).is_none());
    let grey = white_balance_from_neutral([0.3; 3]).unwrap();
    assert_eq!(
        (grey.temperature, grey.tint, grey.clamped),
        (0.0, 0.0, false)
    );
    // The square is clipped at the photograph's edge, not wrapped.
    let image = cast_image([0.2; 3], None);
    let corner = image.sample_placed([0.0, 0.0], 5).unwrap();
    assert_eq!(corner, [0.6, 0.1, 0.05]);
}

#[test]
fn a_pending_repair_exports_with_the_repairs_the_master_holds() {
    let repair = |id: &str, first| RegionAdjustment {
        source_range: Some(SourceRange {
            first,
            last: first + 4,
        }),
        adjustments: Adjustments::default(),
        ..region(id, stroke(vec![[0.3, 0.3], [0.5, 0.4]], 0.03))
    };
    let baked = DevelopmentRecipe {
        regions: vec![
            repair("old", 10),
            region(
                "tone",
                RegionShape::Rectangle {
                    min: [0.1, 0.1],
                    max: [0.4, 0.4],
                },
            ),
        ],
        ..Default::default()
    };
    let image = LinearImage {
        width: 8,
        height: 8,
        pixels: vec![0.2; 8 * 8 * 3],
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: Some(baked.clone()),
    };
    // Now: the baked repair re-ranged, a new stroke painted, tone changed,
    // and the tone region moved ahead of the repair in the list.
    let mut current = baked.clone();
    current.regions.swap(0, 1);
    current.regions[1].source_range = Some(SourceRange {
        first: 20,
        last: 30,
    });
    current.regions.push(repair("new", 40));
    current.global.exposure = 0.7;
    current.validate().unwrap();
    assert!(
        image.validate_source_repairs(&current).is_err(),
        "fixture is pending"
    );
    let export = current.with_baked_repairs(image.baked_recipe.as_ref());
    export.validate().unwrap();
    image.validate_source_repairs(&export).unwrap();
    assert_eq!(export.global, current.global, "tone is kept");
    let order = |r: &DevelopmentRecipe| {
        r.application_order()
            .into_iter()
            .map(|i| r.regions[i].id.clone())
            .collect::<Vec<_>>()
    };
    assert_eq!(
        order(&export)[..3],
        order(&current)[..],
        "tone order is kept"
    );
    assert!(
        export
            .regions
            .iter()
            .find(|r| r.id == "new")
            .unwrap()
            .source_range
            .is_none()
    );
    // A deleted baked repair returns as a neutral region; nothing pending is identity.
    let mut deleted = current.clone();
    deleted.remove_region("old");
    let export = deleted.with_baked_repairs(image.baked_recipe.as_ref());
    image.validate_source_repairs(&export).unwrap();
    assert_eq!(
        export
            .regions
            .iter()
            .find(|r| r.id == "old")
            .unwrap()
            .adjustments,
        Adjustments::default()
    );
    let unchanged = baked.with_baked_repairs(Some(&baked));
    assert_eq!(unchanged, baked);
}
