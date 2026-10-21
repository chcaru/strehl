use super::*;
use crate::edit_workspace::EditorState;
use strehl_edit::{RegionAdjustment, RegionShape, SourceRange};

fn region(id: &str) -> RegionAdjustment {
    RegionAdjustment {
        id: id.into(),
        name: "昆虫✨".repeat(28),
        note: String::new(),
        shape: RegionShape::Ellipse {
            center: [0.5, 0.5],
            radius: [0.2, 0.3],
        },
        feather: 0.4,
        enabled: true,
        adjustments: Adjustments {
            exposure: -1.5,
            ..Default::default()
        },
        source_range: Some(SourceRange { first: 3, last: 8 }),
    }
}

#[test]
fn duplicate_validates_limits_and_is_one_reversible_photo_edit() {
    let original_id = "x".repeat(128);
    let mut editor = EditorState::default();
    editor.recipe.regions.push(region(&original_id));
    editor.recipe.validate().unwrap();
    let before = editor.recipe.clone();
    assert!(
        before.regions[0].name.len() + " copy".len() > 256,
        "fixture must exercise name truncation"
    );
    duplicate_region(&mut editor, &original_id).unwrap();
    editor.recipe.validate().unwrap();
    let copy = &editor.recipe.regions[1];
    assert!(copy.name.len() <= 256 && copy.name.ends_with(" copy"));
    assert_ne!(copy.id, original_id);
    assert_eq!(copy.shape, before.regions[0].shape);
    assert_eq!(copy.adjustments, before.regions[0].adjustments);
    assert!(
        copy.source_range.is_none(),
        "copy must not schedule a second source repair"
    );
    assert_eq!(editor.selected.as_ref(), Some(&copy.id));
    assert!(editor.undo());
    assert_eq!(editor.recipe, before);
    assert!(
        editor.selected.is_none(),
        "undo must not leave a deleted region selected"
    );
    assert!(!editor.can_undo());
    editor.recipe.regions = (0..128).map(|i| region(&format!("r{i}"))).collect();
    let full = editor.recipe.clone();
    assert!(duplicate_region(&mut editor, "r0").is_err());
    assert_eq!(
        editor.recipe, full,
        "a rejected duplicate must leave edits intact"
    );
}

#[test]
fn rename_state_does_not_cross_documents_or_survive_a_deleted_region() {
    let mut editor = EditorState::default();
    editor.path = Some("first.tiff".into());
    editor.recipe.regions.push(region("r"));
    let mut state = EditPaneState::default();
    state.reconcile(&editor);
    state.rename = Some(("r".into(), "new name".into()));
    state.reconcile(&editor);
    assert!(state.rename.is_some());
    editor.path = Some("second.tiff".into());
    state.reconcile(&editor);
    assert!(
        state.rename.is_none(),
        "matching region IDs in another file are not the same region"
    );
    state.rename = Some(("r".into(), "new name".into()));
    editor.recipe.regions.clear();
    state.reconcile(&editor);
    assert!(state.rename.is_none());
}

#[test]
fn inline_rename_consumes_escape_and_bounds_unicode_without_losing_selection() {
    let ctx = egui::Context::default();
    let mut name = "Original".to_owned();
    let mut text = "Changed".to_owned();
    let id = egui::Id::new(("rename-region", "r"));
    ctx.data_mut(|d| d.insert_temp(id.with("request-focus"), true));
    let mut frame = |events, time| {
        let mut finished = false;
        let mut escaped_canvas = false;
        let _ = ctx.run(
            egui::RawInput {
                events,
                time: Some(time),
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(240.0, 80.0),
                )),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    finished = rename_region(
                        ui,
                        egui::Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(210.0, 24.0)),
                        "r",
                        &mut text,
                        &mut name,
                    );
                    escaped_canvas = ui.input(|i| i.key_pressed(egui::Key::Escape));
                });
            },
        );
        (finished, escaped_canvas)
    };
    frame(vec![], 0.0);
    let event = |key| egui::Event::Key {
        key,
        physical_key: Some(key),
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers::NONE,
    };
    let (finished, escaped_canvas) = frame(vec![event(egui::Key::Escape)], 0.1);
    assert!(finished);
    assert!(!escaped_canvas, "Escape must stop at the inline name field");
    assert_eq!(name, "Original");
    let bounded = bounded_text(&"✨虫".repeat(100), 256);
    assert!(bounded.len() <= 256);
    assert!(
        bounded.len() >= 253,
        "truncate by a code point, not a character count"
    );
}

#[test]
fn collapsing_region_shelf_preserves_expanded_height() {
    let ctx = egui::Context::default();
    let id = egui::Id::new("edit-regions-shelf");
    // Exercise a resized height, rather than merely the default 210 points.
    ctx.data_mut(|d| {
        d.insert_persisted(
            id,
            egui::containers::panel::PanelState {
                rect: egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(250.0, 270.0)),
            },
        )
    });
    let mut heights = Vec::new();
    for open in [true, false, true] {
        let _ = ctx.run(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(250.0, 800.0),
                )),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        region_shelf(ui, open, true, |ui| {
                            heights.push(ui.max_rect().height());
                        });
                    });
            },
        );
    }
    assert!(
        heights[0] > 250.0,
        "fixture must exercise a resized shelf: {heights:?}"
    );
    assert!(heights[1] <= 29.0);
    assert!(
        (heights[2] - heights[0]).abs() < 1.0,
        "collapsed height replaced expanded height: {heights:?}"
    );
}

#[test]
fn empty_shelf_reclaims_space_and_tool_guidance_without_erasing_resized_list() {
    for width in [235.0, 272.0] {
        let ctx = egui::Context::default();
        theme::install(&ctx);
        ctx.data_mut(|d| {
            d.insert_persisted(
                egui::Id::new("edit-regions-shelf"),
                egui::containers::panel::PanelState {
                    rect: egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(width, 276.0)),
                },
            );
        });
        let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
        app.catalog = Default::default();
        app.editor = Default::default();
        let mut heights = Vec::new();
        let mut free_heights = Vec::new();
        for (populated, tool, expected_hint) in [
            (true, DrawingTool::Select, None),
            (
                false,
                DrawingTool::Select,
                Some("Choose a shape to add a region."),
            ),
            (
                false,
                DrawingTool::Ellipse,
                Some("Drag an ellipse on the photograph."),
            ),
            (
                false,
                DrawingTool::MagicLasso,
                Some("Enclose detail with a little background."),
            ),
            (true, DrawingTool::Select, None),
        ] {
            app.editor.recipe.regions = if populated {
                vec![region("r")]
            } else {
                Vec::new()
            };
            app.editor.set_tool(tool);
            let recipe = app.editor.recipe.clone();
            let mut shelf_rect = egui::Rect::NOTHING;
            let mut free_height = 0.0;
            let mut output = None;
            for _ in 0..2 {
                output = Some(ctx.run(
                    egui::RawInput {
                        screen_rect: Some(egui::Rect::from_min_size(
                            egui::Pos2::ZERO,
                            egui::vec2(width, 720.0),
                        )),
                        ..Default::default()
                    },
                    |ctx| {
                        egui::CentralPanel::default()
                            .frame(egui::Frame::NONE)
                            .show(ctx, |ui| {
                                region_shelf(ui, true, populated, |ui| {
                                    shelf_rect = ui.max_rect();
                                    app.edit_region_shelf(ui, true);
                                });
                                free_height = ui.available_height();
                            });
                    },
                ));
            }
            let output = output.unwrap();
            if let Some(hint) = expected_hint {
                let text = output
                    .shapes
                    .iter()
                    .find_map(|shape| match &shape.shape {
                        egui::Shape::Text(text) if text.galley.text() == hint => {
                            Some((shape.clip_rect, text.visual_bounding_rect()))
                        }
                        _ => None,
                    })
                    .unwrap_or_else(|| panic!("Missing tool guidance at width {width}: {hint}"));
                assert!(
                    text.0.intersect(text.1).height() >= 8.0,
                    "Guidance was clipped away: {hint}"
                );
                assert!(shelf_rect.expand(1.0).contains(text.1.center()));
            }
            assert_eq!(app.editor.recipe, recipe);
            heights.push(shelf_rect.height());
            free_heights.push(free_height);
        }
        assert!(
            heights[0] > 250.0,
            "Resized fixture did not apply: {heights:?}"
        );
        assert!(
            heights[1] <= 151.0 && heights[0] - heights[1] > 100.0,
            "Empty shelf did not reclaim space: {heights:?}"
        );
        assert!(
            (heights[1] - heights[2]).abs() < 0.1 && (heights[2] - heights[3]).abs() < 0.1,
            "Tool changes resized the empty shelf: {heights:?}"
        );
        assert!(
            (heights[0] - heights[4]).abs() < 1.0,
            "Empty shelf erased the populated user height: {heights:?}"
        );
        assert!(
            free_heights[1] - free_heights[0] > 100.0,
            "Space was not returned to the adjustment controls: {free_heights:?}"
        );
    }
}

#[test]
fn displaying_missing_or_shorter_capture_bracket_preserves_saved_range() {
    for count in [None, Some(0), Some(12), Some(100)] {
        let ctx = egui::Context::default();
        let mut saved = Some(SourceRange {
            first: 48,
            last: 59,
        });
        let original = saved.clone();
        for _ in 0..3 {
            let _ = ctx.run(egui::RawInput::default(), |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    source_range_controls(ui, &mut saved, count, 0);
                });
            });
        }
        assert_eq!(
            saved, original,
            "opening range controls changed saved source evidence: {count:?}"
        );
    }
}

#[test]
fn displaying_valid_hdr_settings_does_not_clamp_imported_recipe() {
    for (white, peak) in [(100.0, 150.0), (203.0, 6000.0), (500.0, 10_000.0)] {
        let ctx = egui::Context::default();
        let mut hdr = strehl_edit::HdrSettings {
            reference_white_nits: white,
            peak_nits: peak,
            ..Default::default()
        };
        hdr.validate().unwrap();
        let original = hdr;
        for _ in 0..3 {
            let _ = ctx.run(egui::RawInput::default(), |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| hdr_luminance_controls(ui, &mut hdr));
            });
        }
        assert_eq!(hdr, original, "opening HDR controls changed a valid recipe");
    }
}
