use super::*;

fn photo(w: u32, h: u32, pixel: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
    let mut pixels = Vec::new();
    for y in 0..h {
        for x in 0..w {
            pixels.extend(pixel(x, y));
        }
    }
    LinearImage {
        width: w,
        height: h,
        pixels,
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}
fn enclosure() -> RegionShape {
    RegionShape::Polygon {
        points: vec![[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]],
    }
}
fn select(image: &LinearImage) -> Selection {
    segment(
        image,
        &DevelopmentRecipe::default(),
        &enclosure(),
        &AtomicBool::new(false),
    )
    .unwrap()
}
#[test]
fn magic_selects_two_supported_objects_but_not_isolated_bright_noise() {
    let image = photo(160, 120, |x, y| {
        if (30..65).contains(&x) && (35..80).contains(&y) {
            [0.7, 0.12, 0.1]
        } else if (95..130).contains(&x) && (45..85).contains(&y) {
            [0.15, 0.6, 0.2]
        } else if (x * 197 + y * 37) % 1009 == 0 {
            [1.0; 3]
        } else {
            [0.08; 3]
        }
    });
    let result = select(&image);
    assert_eq!(result.shapes.len(), 2);
    assert!(result.shapes.iter().any(|s| s.contains([0.3, 0.5])));
    assert!(result.shapes.iter().any(|s| s.contains([0.7, 0.5])));
    assert!(result.shapes.iter().all(|s| !s.contains([0.5, 0.5])));
    assert!(
        result
            .shapes
            .iter()
            .all(|s| matches!(s,RegionShape::Polygon{points} if points.len()<=256))
    );
}
#[test]
fn magic_rejects_flat_noise_gradient_and_meaningful_holes() {
    for image in [
        photo(128, 96, |_, _| [0.2; 3]),
        photo(128, 96, |x, y| {
            [0.2 + ((x * 31 + y * 13) % 17) as f32 * 0.001; 3]
        }),
        photo(128, 96, |x, y| [0.05 + (x + y) as f32 * 0.003; 3]),
    ] {
        assert!(select(&image).shapes.is_empty());
    }
    let ring = photo(128, 96, |x, y| {
        let d = (x as f32 - 64.0).hypot(y as f32 - 48.0);
        if (14.0..30.0).contains(&d) {
            [0.7; 3]
        } else {
            [0.07; 3]
        }
    });
    let result = select(&ring);
    assert!(result.shapes.is_empty());
    assert_eq!(result.skipped_holes, 1);
}
#[test]
fn magic_cancellation_is_checked_before_sampling() {
    let image = photo(16, 16, |_, _| [0.2; 3]);
    let result = segment(
        &image,
        &DevelopmentRecipe::default(),
        &enclosure(),
        &AtomicBool::new(true),
    );
    assert!(result.is_err());
}

#[test]
fn magic_uses_hdr_headroom_and_keeps_dark_visible_detail() {
    for (background, foreground) in [(1.2, 3.0), (0.001, 0.012)] {
        let image = photo(100, 100, |x, y| {
            if (30..70).contains(&x) && (30..70).contains(&y) {
                [foreground; 3]
            } else {
                [background; 3]
            }
        });
        let selected = select(&image);
        assert_eq!(selected.shapes.len(), 1);
        assert!(selected.shapes[0].contains([0.5, 0.5]));
        if background > 1.0 {
            let clipped = photo(100, 100, |_, _| [1.0; 3]);
            assert!(
                select(&clipped).shapes.is_empty(),
                "The deliberately clipped control destroys the HDR boundary"
            );
        }
    }
}

#[test]
fn magic_keeps_dark_colored_and_textured_objects_and_does_not_bridge_a_narrow_gap() {
    for kind in 0..3 {
        let image = photo(128, 96, |x, y| {
            let object = (35..90).contains(&x) && (25..75).contains(&y);
            match kind {
                0 => {
                    if object {
                        [0.015; 3]
                    } else {
                        [0.5; 3]
                    }
                }
                1 => {
                    if object {
                        [0.6, 0.0, 0.0]
                    } else {
                        [0.12756; 3]
                    }
                }
                _ => {
                    if object {
                        [if (x / 4 + y / 4) % 2 == 0 { 0.3 } else { 0.65 }; 3]
                    } else {
                        [0.03; 3]
                    }
                }
            }
        });
        let result = select(&image);
        assert_eq!(result.shapes.len(), 1, "kind {kind}");
        assert!(result.shapes[0].contains([0.5, 0.5]));
        assert!(!result.shapes[0].contains([0.15, 0.15]));
    }
    let split = photo(128, 96, |x, y| {
        if (25..105).contains(&x) && (25..75).contains(&y) && x != 64 {
            [0.8; 3]
        } else {
            [0.03; 3]
        }
    });
    let result = select(&split);
    assert_eq!(result.shapes.len(), 2);
    assert!(
        result
            .shapes
            .iter()
            .all(|shape| !shape.contains([64.5 / 128.0, 0.5]))
    );
}

#[test]
fn magic_respects_concave_enclosure_and_image_edges_and_reports_component_limit() {
    let shape = RegionShape::Polygon {
        points: vec![
            [0.0, 0.05],
            [0.95, 0.05],
            [0.95, 0.3],
            [0.45, 0.3],
            [0.45, 0.95],
            [0.0, 0.95],
        ],
    };
    let image = photo(128, 128, |x, y| {
        if (15..47).contains(&x) && (20..100).contains(&y) {
            [0.7; 3]
        } else if x > 75 && y > 75 {
            [f32::NAN; 3]
        } else {
            [0.05; 3]
        }
    });
    let result = segment(
        &image,
        &DevelopmentRecipe::default(),
        &shape,
        &AtomicBool::new(false),
    )
    .unwrap();
    assert_eq!(result.shapes.len(), 1);
    assert!(result.shapes[0].contains([0.25, 0.5]));
    for y in 0..256 {
        for x in 0..256 {
            let uv = [(x as f32 + 0.5) / 256.0, (y as f32 + 0.5) / 256.0];
            if result.shapes[0].contains(uv) {
                assert!(shape.contains(uv), "Selection escaped enclosure at {uv:?}");
            }
        }
    }
    let crowded = photo(180, 160, |x, y| {
        if (15..165).contains(&x) && (15..145).contains(&y) && x % 40 < 15 && y % 40 < 15 {
            [0.8; 3]
        } else {
            [0.05; 3]
        }
    });
    let selected = select(&crowded);
    assert_eq!(selected.shapes.len(), 8);
    assert!(selected.omitted_components > 0);
}

fn editor_fixture() -> EditorState {
    let image = Arc::new(photo(120, 100, |x, y| {
        if ((20..45).contains(&x) || (75..100).contains(&x)) && (25..75).contains(&y) {
            [0.8; 3]
        } else {
            [0.05; 3]
        }
    }));
    EditorState {
        tool: DrawingTool::MagicLasso,
        loaded: Some(LoadedPhoto {
            coverage: None,
            image: image.clone(),
            preview: image,
            recipe: Default::default(),
            source: "fixture".into(),
            warnings: vec![],
        }),
        ..Default::default()
    }
}
#[test]
fn real_magic_worker_commits_multiple_masks_as_one_undo_without_source_repairs() {
    let mut editor = editor_fixture();
    let ctx = egui::Context::default();
    let mut recipe = editor.recipe.clone();
    recipe.regions.push(RegionAdjustment {
        id: "repair".into(),
        name: "Repair".into(),
        note: String::new(),
        shape: RegionShape::Rectangle {
            min: [0.0, 0.0],
            max: [0.1, 0.1],
        },
        feather: 0.2,
        enabled: true,
        adjustments: Default::default(),
        source_range: Some(strehl_edit::SourceRange { first: 2, last: 4 }),
    });
    editor.recipe = recipe.clone();
    editor.start_magic(enclosure(), &ctx);
    let until = Instant::now() + Duration::from_secs(5);
    while editor.magic_pending() && Instant::now() < until {
        editor.poll_magic(&ctx);
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(!editor.magic_pending());
    assert_eq!(editor.recipe.regions.len(), 3);
    assert_eq!(editor.recipe.regions[0], recipe.regions[0]);
    assert!(
        editor.recipe.regions[1..]
            .iter()
            .all(|r| r.source_range.is_none())
    );
    assert_eq!(editor.history_depths(), (1, 0));
    assert_eq!(editor.tool, DrawingTool::Select);
    assert!(editor.undo());
    assert_eq!(editor.recipe, recipe);
}

#[test]
fn magic_result_cannot_publish_after_revision_document_tool_or_escape_changes() {
    for change in 0..4 {
        let mut editor = editor_fixture();
        let ctx = egui::Context::default();
        editor.start_magic(enclosure(), &ctx);
        match change {
            0 => editor.revision += 1,
            1 => editor.loaded = editor_fixture().loaded,
            2 => editor.set_tool(DrawingTool::Rectangle),
            _ => {
                let _ = ctx.run(
                    egui::RawInput {
                        events: vec![egui::Event::Key {
                            key: egui::Key::Escape,
                            physical_key: None,
                            pressed: true,
                            repeat: false,
                            modifiers: Default::default(),
                        }],
                        ..Default::default()
                    },
                    |ctx| editor.poll_magic(ctx),
                );
            }
        }
        editor.poll_magic(&ctx);
        assert!(!editor.magic_pending());
        assert!(editor.recipe.regions.is_empty());
        assert!(!editor.can_undo());
    }
}

#[test]
#[ignore = "Manual real-photo receipt; requires copied review TIFF under outputs"]
fn magic_real_photo_receipt() {
    let input = std::env::var_os("STREHL_MAGIC_REVIEW_INPUT").expect("review TIFF path");
    let output = std::env::var_os("STREHL_MAGIC_REVIEW_OUTPUT").expect("receipt JSON path");
    let image = strehl_edit::load_tiff(Path::new(&input)).unwrap();
    let shape = std::env::var("STREHL_MAGIC_REVIEW_ENCLOSURE")
        .map(|json| serde_json::from_str::<RegionShape>(&json).expect("valid enclosure JSON"))
        .unwrap_or(RegionShape::Ellipse {
            center: [0.749, 0.48],
            radius: [0.045, 0.09],
        });
    let start = Instant::now();
    let result = segment(
        &image,
        &DevelopmentRecipe::default(),
        &shape,
        &AtomicBool::new(false),
    )
    .unwrap();
    let receipt = serde_json::json!({"input":PathBuf::from(input),"image_size":[image.width,image.height],"enclosure":shape,"sampling_grid":result.sampling_grid,"sampled_pixels":result.sampled_pixels,"retained_count":result.shapes.len(),"regions":result.shapes,"skipped_holes":result.skipped_holes,"closed_gaps":result.closed_gaps,"omitted_components":result.omitted_components,"core_refinements":result.core_refinements,"segmentation_ms":start.elapsed().as_secs_f64()*1000.0,"scope":"Bounded image-contrast selection, editable approximation; no semantic/AI claim"});
    std::fs::write(output, serde_json::to_vec_pretty(&receipt).unwrap()).unwrap();
}
