use strehl_edit::*;

fn image() -> LinearImage {
    LinearImage {
        width: 32,
        height: 32,
        pixels: (0..32 * 32)
            .flat_map(|i| {
                let v = 0.02 + (i % 32) as f32 * 0.09;
                [v, v * 0.8, v * 0.5]
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

#[test]
fn master_roundtrip_keeps_negative_and_above_white_samples() {
    let temp = tempfile::tempdir().unwrap();
    let mut original = image();
    original.pixels[0] = -0.123;
    original.baseline = Some(DisplayBaseline {
        black: 0.01,
        white: 1.6,
        contrast: 0.55,
        exposure_gain: 2.0,
    });
    let path = temp.path().join("master.tiff");
    save_linear_tiff(&path, &original).unwrap();
    let read = load_tiff(&path).unwrap();
    assert_eq!(read.pixels, original.pixels);
    assert_eq!(read.baseline, original.baseline);
    assert_eq!(read.origin, ImageOrigin::SceneLinear);
    assert!(read.pixels.iter().any(|&v| v > 1.0));
    assert!(read.pixels.iter().any(|&v| v < 0.0));
}

#[test]
fn neutral_recipe_is_exact_and_exposure_recovers_highlights_before_display_clamp() {
    let mut recipe = DevelopmentRecipe::default();
    assert_eq!(
        recipe.apply_pixel([-0.1, 0.2, 3.7], [0.5, 0.5]),
        [-0.1, 0.2, 3.7]
    );
    recipe.global.exposure = -2.0;
    assert_eq!(recipe.apply_pixel([2.0; 3], [0.5, 0.5]), [0.5; 3]);
    let src = image();
    let original = src.pixels.clone();
    assert_ne!(
        src.render_sdr8(&recipe).unwrap(),
        src.render_sdr8(&DevelopmentRecipe::default()).unwrap()
    );
    assert_eq!(src.pixels, original, "development mutated the master");
}

#[test]
fn region_feather_and_normalized_location_are_resolution_independent() {
    let shape = RegionShape::Ellipse {
        center: [0.5, 0.5],
        radius: [0.2, 0.1],
    };
    assert_eq!(shape.weight([0.5, 0.5], 0.5), 1.0);
    assert_eq!(shape.weight([0.8, 0.5], 0.5), 0.0);
    let middle = shape.weight([0.65, 0.5], 0.5);
    assert!((0.49..0.51).contains(&middle));
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "one".into(),
        name: "Eye".into(),
        note: String::new(),
        shape,
        feather: 0.5,
        enabled: true,
        adjustments: Adjustments {
            exposure: 1.0,
            ..Default::default()
        },
        source_range: None,
    });
    assert_eq!(recipe.apply_pixel([0.25; 3], [0.5, 0.5]), [0.5; 3]);
    assert_eq!(recipe.apply_pixel([0.25; 3], [0.8, 0.5]), [0.25; 3]);
}

#[test]
fn invalid_recipes_and_geometry_fail_before_rendering() {
    let mut r = DevelopmentRecipe::default();
    r.global.exposure = f32::NAN;
    assert!(r.validate().is_err());
    r.global.exposure = 9.0;
    assert!(r.validate().is_err());
    r.global.exposure = 0.0;
    r.version = 2;
    assert!(r.validate().is_err());
    assert!(serde_json::from_str::<DevelopmentRecipe>(r#"{"bogus":12}"#).is_err());
    assert!(
        RegionShape::Ellipse {
            center: [2.0, 0.5],
            radius: [0.1, 0.1]
        }
        .validate()
        .is_err()
    );
    assert!(
        RegionShape::Polygon {
            points: vec![[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]
        }
        .validate()
        .is_err()
    );
    assert!(
        HdrSettings {
            peak_nits: 100.0,
            ..Default::default()
        }
        .validate()
        .is_err()
    );
}

#[test]
fn xmp_import_reports_nonportable_look_and_rejects_invalid_values() {
    // A fabricated preset, not the user's private preset.
    let x = r#"<rdf:Description crs:Contrast2012="+15" crs:Vibrance="+20" crs:HDRMaxValue="2.3"><crs:Look><rdf:Description crs:Name="Example AI" crs:Exposure2012="8"/></crs:Look></rdf:Description>"#;
    let import = import_xmp(x).unwrap();
    assert_eq!(import.recipe.global.contrast, 15.0);
    assert_eq!(import.recipe.global.vibrance, 20.0);
    assert_eq!(
        import.recipe.global.exposure, 0.0,
        "nested look was applied"
    );
    assert!(import.warnings.iter().any(|s| s.contains("not portable")));
    assert!((import.recipe.hdr.peak_nits - 999.7).abs() < 1.0);
    assert!(import_xmp(r#"<x crs:Exposure2012="NaN"/>"#).is_err());
    assert!(import_xmp(r#"<!DOCTYPE foo><x crs:Exposure2012="0"/>"#).is_err());
}

#[test]
fn hdr_is_not_allowed_to_relabel_a_clipped_sdr_photograph() {
    let temp = tempfile::tempdir().unwrap();
    let mut src = image();
    src.origin = ImageOrigin::DisplayReferred;
    assert!(
        export_hdr_avif(
            &temp.path().join("bad.avif"),
            &src,
            &DevelopmentRecipe::default()
        )
        .is_err()
    );
    assert!(save_linear_tiff(&temp.path().join("bad.tiff"), &src).is_err());
}

#[test]
fn avif_is_real_ten_bit_bt2020_pq_and_survives_independent_container_inspection() {
    let temp = tempfile::tempdir().unwrap();
    let path = temp.path().join("hdr.avif");
    let recipe = DevelopmentRecipe {
        hdr: HdrSettings {
            speed: 10,
            ..Default::default()
        },
        ..Default::default()
    };
    let report = export_hdr_avif(&path, &image(), &recipe).unwrap();
    assert_eq!(report.bit_depth, 10);
    assert!(
        report.max_content_light_nits > 203,
        "test never exercised HDR headroom"
    );
    let file = std::fs::read(path).unwrap();
    let pos = file
        .windows(4)
        .position(|x| x == b"nclx")
        .expect("AVIF color metadata");
    assert_eq!(
        &file[pos + 4..pos + 10],
        &[0, 9, 0, 16, 0, 9],
        "BT.2020, PQ, BT.2020 nonconstant-luminance"
    );
    assert_eq!(file[pos + 10] & 0x80, 0x80, "full range");
    let av1c = file
        .windows(4)
        .position(|x| x == b"av1C")
        .expect("AV1 codec config");
    assert_ne!(file[av1c + 6] & 0x40, 0, "high_bitdepth bit absent");
}

#[test]
fn neutral_sdr_load_edit_export_roundtrip_is_within_one_code_value() {
    let temp = tempfile::tempdir().unwrap();
    let src = image();
    let path = temp.path().join("sdr.tiff");
    save_sdr_tiff(&path, &src, &DevelopmentRecipe::default()).unwrap();
    let read = load_tiff(&path).unwrap();
    assert_eq!(read.origin, ImageOrigin::DisplayReferred);
    let a = src.render_sdr16(&DevelopmentRecipe::default()).unwrap();
    let b = read.render_sdr16(&DevelopmentRecipe::default()).unwrap();
    assert!(a.iter().zip(b).all(|(&a, b)| a.abs_diff(b) <= 1));
}

#[test]
fn cropped_preview_preserves_full_image_region_coordinates() {
    let src = LinearImage {
        width: 100,
        height: 100,
        pixels: vec![0.1; 30_000],
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    };
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "corner".into(),
        name: "Corner".into(),
        note: String::new(),
        shape: RegionShape::Rectangle {
            min: [0.7, 0.7],
            max: [0.9, 0.9],
        },
        feather: 0.0,
        enabled: true,
        adjustments: Adjustments {
            exposure: 2.0,
            ..Default::default()
        },
        source_range: None,
    });
    let full = src.render_sdr8(&recipe).unwrap();
    let (w, h, roi) = src
        .render_region_sdr8(&recipe, [0.5, 0.5], [1.0, 1.0], 100)
        .unwrap();
    assert_eq!((w, h), (50, 50));
    for y in 0..50 {
        for x in 0..50 {
            let a = (y * 50 + x) * 3;
            let b = ((y + 50) * 100 + x + 50) * 3;
            assert_eq!(&roi[a..a + 3], &full[b..b + 3]);
        }
    }
    assert!(
        roi[(30 * 50 + 30) * 3] > roi[0],
        "fixture did not straddle the adjusted region"
    );
}

#[test]
fn source_repair_provenance_allows_tone_but_requires_restack_for_geometry_changes() {
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "repair".into(),
        name: "Edge".into(),
        note: String::new(),
        shape: RegionShape::Ellipse {
            center: [0.5, 0.5],
            radius: [0.1, 0.2],
        },
        feather: 0.5,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: Some(SourceRange { first: 2, last: 5 }),
    });
    let mut src = image();
    assert!(
        src.validate_source_repairs(&recipe).is_err(),
        "pending repair accepted without a rebuilt master"
    );
    src.baked_recipe = Some(recipe.clone());
    recipe.global.exposure = 1.0;
    recipe.regions[0].name = "Renamed".into();
    recipe.regions[0].adjustments.highlights = -40.0;
    src.validate_source_repairs(&recipe).unwrap();
    recipe.regions[0].feather = 0.3;
    assert!(src.validate_source_repairs(&recipe).is_err());
    assert!(
        src.validate_source_repairs(&DevelopmentRecipe::default())
            .is_err(),
        "deleting a baked repair cannot unbake it"
    );
}

#[test]
fn exports_preserve_an_existing_destination_byte_for_byte() {
    let dir = tempfile::tempdir().unwrap();
    let tiff = dir.path().join("photo.tiff");
    let avif = dir.path().join("photo.avif");
    std::fs::write(&tiff, b"existing TIFF").unwrap();
    std::fs::write(&avif, b"existing AVIF").unwrap();
    let recipe = DevelopmentRecipe {
        hdr: HdrSettings {
            speed: 10,
            ..Default::default()
        },
        ..Default::default()
    };
    assert!(save_sdr_tiff(&tiff, &image(), &recipe).is_err());
    assert!(export_hdr_avif(&avif, &image(), &recipe).is_err());
    assert_eq!(std::fs::read(&tiff).unwrap(), b"existing TIFF");
    assert_eq!(std::fs::read(&avif).unwrap(), b"existing AVIF");
    assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 2);
}
