use super::*;
use crate::edit_workspace::EditorState;
use strehl_edit::{RegionAdjustment, RegionShape};

fn region(id: &str) -> RegionAdjustment {
    RegionAdjustment {
        id: id.into(),
        name: "Glints".into(),
        note: String::new(),
        shape: RegionShape::Ellipse {
            center: [0.5, 0.5],
            radius: [0.2, 0.2],
        },
        feather: 0.4,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: None,
    }
}

fn editor() -> EditorState {
    let mut editor = EditorState::default();
    editor.recipe.regions.push(region("glints"));
    editor
}

#[test]
fn the_scope_switch_retargets_the_sliders_and_nothing_else() {
    let mut editor = editor();
    editor
        .apply_develop(&DevelopIntent::Adjust(AdjustmentField::Contrast, 20.0), 1.0)
        .unwrap();
    assert_eq!(editor.recipe.global.contrast, 20.0);
    assert_eq!(editor.recipe.regions[0].adjustments.contrast, 0.0);
    editor
        .apply_develop(&DevelopIntent::SetScope(Some("glints".into())), 2.0)
        .unwrap();
    assert_eq!(editor.selected.as_deref(), Some("glints"));
    editor
        .apply_develop(
            &DevelopIntent::Adjust(AdjustmentField::Highlights, -25.0),
            3.0,
        )
        .unwrap();
    assert_eq!(editor.recipe.regions[0].adjustments.highlights, -25.0);
    assert_eq!(
        editor.recipe.global.highlights, 0.0,
        "the whole photograph is untouched"
    );
    // A missing layer falls back to the whole photograph.
    editor
        .apply_develop(&DevelopIntent::SetScope(Some("gone".into())), 4.0)
        .unwrap();
    assert_eq!(editor.selected, None);
    editor
        .apply_develop(&DevelopIntent::Adjust(AdjustmentField::Exposure, 9.0), 5.0)
        .unwrap();
    assert_eq!(
        editor.recipe.global.exposure, 8.0,
        "clamped to the recipe's range"
    );
    assert!(editor.can_undo(), "adjustments go through the undo journal");
}

#[test]
fn painting_a_stroke_makes_a_depth_repair_from_the_chosen_planes() {
    let mut editor = editor();
    editor
        .apply_develop(&DevelopIntent::SetRepairRange(115, 131), 1.0)
        .unwrap();
    let path: Vec<[f32; 2]> = (0..50).map(|i| [0.3 + i as f32 * 0.002, 0.6]).collect();
    editor
        .apply_develop(
            &DevelopIntent::PaintStroke {
                points: path,
                radius: [0.02, 0.03],
                feather: 0.6,
            },
            2.0,
        )
        .unwrap();
    let repair = editor.recipe.regions.last().unwrap();
    assert!(matches!(repair.shape, RegionShape::Stroke { .. }));
    assert_eq!(repair.name, "Depth repair 1");
    assert_eq!(repair.feather, 0.6);
    assert_eq!(
        repair.source_range,
        Some(strehl_edit::SourceRange {
            first: 115,
            last: 131
        })
    );
    assert_eq!(editor.selected.as_ref(), Some(&repair.id));
    // Re-ranging the selected repair moves its planes.
    editor
        .apply_develop(&DevelopIntent::SetRepairRange(140, 150), 3.0)
        .unwrap();
    assert_eq!(
        editor.recipe.regions.last().unwrap().source_range,
        Some(strehl_edit::SourceRange {
            first: 140,
            last: 150
        })
    );
    editor.recipe.validate().unwrap();
}

#[test]
fn finishing_intents_edit_the_recipe_and_view_intents_do_not() {
    let mut editor = editor();
    let crop = Crop {
        min: [0.1, 0.1],
        max: [0.9, 0.8],
        angle_deg: 2.0,
    };
    for intent in [
        DevelopIntent::SetCrop(Some(crop)),
        DevelopIntent::AddHeal(auto_heal([0.5, 0.5], [0.01, 0.015])),
        DevelopIntent::SetBackdrop(Some(Backdrop {
            threshold: 0.012,
            softness: 1.0,
            key: BackdropKey::Dark,
            enabled: true,
        })),
        DevelopIntent::AddNote([0.2, 0.3]),
    ] {
        let revision = editor.revision;
        assert!(editor.apply_develop(&intent, 1.0).unwrap(), "{intent:?}");
        assert_ne!(editor.revision, revision, "{intent:?} changed nothing");
    }
    assert_eq!(editor.recipe.crop, Some(crop));
    assert_eq!(editor.recipe.heals.len(), 1);
    let note = editor.recipe.regions.last().unwrap();
    assert_eq!(layers::region_kind(note), layers::LayerKind::Note);
    let revision = editor.revision;
    for intent in [
        DevelopIntent::SelectTool(DevelopTool::DepthBrush),
        DevelopIntent::SetCompare(Compare::Split),
        DevelopIntent::SetSurround(Surround::Grey),
        DevelopIntent::SetBrush {
            size_px: 60.0,
            feather: 0.3,
        },
    ] {
        assert!(editor.apply_develop(&intent, 2.0).unwrap());
    }
    assert_eq!(editor.revision, revision, "view choices are not edits");
    assert_eq!(editor.develop.tool, DevelopTool::DepthBrush);
    assert_eq!(editor.develop.compare, Compare::Split);
    assert!(!editor.before, "split shows the edit on one side");
    assert_eq!(editor.develop.brush_px, 60.0);
    // App-level intents are left to the app.
    assert!(
        !editor
            .apply_develop(&DevelopIntent::PickLook(1), 3.0)
            .unwrap()
    );
    assert!(
        !editor
            .apply_develop(&DevelopIntent::StartRepair, 3.0)
            .unwrap()
    );
}

#[test]
fn the_canvas_state_survives_a_new_photograph() {
    let mut editor = editor();
    editor
        .apply_develop(&DevelopIntent::SelectTool(DevelopTool::Crop), 1.0)
        .unwrap();
    editor.develop.repair_range = Some((1, 2));
    editor.develop.outbox.push(DevelopIntent::Export);
    editor.reset_document();
    assert_eq!(editor.develop.tool, DevelopTool::Crop);
    assert_eq!(
        editor.develop.repair_range, None,
        "planes belong to a stack"
    );
    assert!(editor.develop.outbox.is_empty());
}

#[test]
fn geometry_helpers_stay_inside_the_photograph() {
    assert_eq!(default_range(299), (120, 178));
    assert_eq!(default_range(1), (0, 0));
    for center in [[0.01, 0.5], [0.99, 0.5], [0.5, 0.99], [0.99, 0.99]] {
        let heal = auto_heal(center, [0.02, 0.03]);
        heal.validate().unwrap();
    }
    let drag = CropDrag {
        grip: CropGrip::Sides(1, 1),
        start: Crop {
            min: [0.2, 0.2],
            max: [0.6, 0.6],
            angle_deg: 5.0,
        },
        origin: [0.0, 0.0],
    };
    let crop = drag_crop(drag, [5000.0, 5000.0], [1000, 800]);
    assert!(crop.fits(1000, 800), "{crop:?}");
    crop.validate().unwrap();
    let moved = drag_crop(
        CropDrag {
            grip: CropGrip::Body,
            ..drag
        },
        [-900.0, 0.0],
        [1000, 800],
    );
    assert!(moved.fits(1000, 800) && moved.min[0] >= 0.0, "{moved:?}");
}

#[test]
fn the_histogram_counts_luminance_and_names_the_clipping() {
    let mut rgb = vec![0u8; 300];
    rgb.extend(vec![128u8; 600]);
    rgb.extend(vec![255u8; 3]);
    let h = Histogram::from_rgb8(&rgb);
    assert_eq!(h.bins.iter().sum::<u32>(), 301);
    assert_eq!(h.bins[0], 100);
    assert!((h.shadows - 100.0 / 301.0).abs() < 1e-6);
    assert_eq!(h.caption(), "highlights 0.3 % at white");
    let dark = Histogram::from_rgb8(&[0, 0, 0, 200, 200, 200]);
    assert_eq!(dark.caption(), "shadows 50 % below 1 %");
}

fn view<'a>(
    recipe: &'a DevelopmentRecipe,
    versions: &'a [VersionRow],
    palette: &'a StudioPalette,
) -> DevelopView<'a> {
    DevelopView {
        palette,
        recipe,
        scope: None,
        histogram: None,
        look: Some(0),
        look_amount: Some(0.6),
        look_busy: false,
        versions,
        render: "Render 3",
        repair: RepairView::default(),
        planes: Some(299),
        um_per_px: Some(2.0),
        image_size: [7032, 4688],
        hdr_photo: true,
        hdr_available: false,
        hdr_display: false,
        display: Vec::new(),
    }
}

fn frame(
    ctx: &egui::Context,
    events: Vec<egui::Event>,
    show: impl FnOnce(&mut Ui),
) -> egui::FullOutput {
    let mut show = Some(show);
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(348.0, 980.0))),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    if let Some(show) = show.take() {
                        show(ui);
                    }
                });
        },
    )
}

fn text_at(output: &egui::FullOutput, text: &str) -> Option<Pos2> {
    output.shapes.iter().find_map(|s| match &s.shape {
        egui::Shape::Text(t) if t.galley.text() == text => Some(t.pos + t.galley.size() * 0.5),
        _ => None,
    })
}

fn click(at: Pos2) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(at),
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed: true,
            modifiers: Default::default(),
        },
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        },
    ]
}

#[test]
fn inspector_clicks_become_intents_and_pointer_motion_raises_none() {
    let ctx = egui::Context::default();
    let palette = StudioPalette::GRAPHITE;
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(region("glints"));
    let versions = vec![VersionRow {
        id: String::new(),
        name: "Edited now".into(),
        detail: "1 layer".into(),
        current: true,
    }];
    let rows = layers::layer_rows(&recipe, |_| false);
    let mut panel = DevelopPanel::default();
    let mut intents = Vec::new();
    let output = frame(&ctx, Vec::new(), |ui| {
        intents = inspector(ui, &mut panel, &view(&recipe, &versions, &palette), &rows)
    });
    assert!(intents.is_empty());
    for label in [
        "Natural",
        "Signature",
        "Whole photograph",
        "Glints",
        "Pick neutral",
        "Export…",
        "Save version",
    ] {
        assert!(text_at(&output, label).is_some(), "{label} not drawn");
    }
    // Pointer-only motion over the inspector raises nothing.
    for y in (100..900).step_by(37) {
        let mut moved = Vec::new();
        frame(
            &ctx,
            vec![egui::Event::PointerMoved(egui::pos2(170.0, y as f32))],
            |ui| moved = inspector(ui, &mut panel, &view(&recipe, &versions, &palette), &rows),
        );
        assert!(moved.is_empty(), "pointer motion at y={y} raised {moved:?}");
    }
    let signature = text_at(&output, "Signature").unwrap();
    frame(&ctx, click(signature), |ui| {
        intents = inspector(ui, &mut panel, &view(&recipe, &versions, &palette), &rows)
    });
    assert_eq!(intents, vec![DevelopIntent::PickLook(1)]);
    let scope = text_at(&output, "Glints").unwrap();
    frame(&ctx, click(scope), |ui| {
        intents = inspector(ui, &mut panel, &view(&recipe, &versions, &palette), &rows)
    });
    assert_eq!(
        intents,
        vec![DevelopIntent::SetScope(Some("glints".into()))]
    );
    let export = text_at(&output, "Export…").unwrap();
    frame(&ctx, click(export), |ui| {
        intents = inspector(ui, &mut panel, &view(&recipe, &versions, &palette), &rows)
    });
    assert_eq!(intents, vec![DevelopIntent::Export]);
}

#[test]
fn the_tools_strip_and_keys_choose_tools() {
    let ctx = egui::Context::default();
    let palette = StudioPalette::GRAPHITE;
    let mut chosen = None;
    frame(&ctx, Vec::new(), |ui| {
        chosen = tools_strip(ui, &palette, DevelopTool::Move)
    });
    assert_eq!(chosen, None);
    // The fourth tool (after one separator) is the depth brush; icons are
    // centred on the strip, here the whole 348 px test panel.
    let at = egui::pos2(174.0, 8.0 + 3.0 * 34.0 + 13.0 + 16.0);
    frame(&ctx, click(at), |ui| {
        chosen = tools_strip(ui, &palette, DevelopTool::Move)
    });
    assert_eq!(chosen, Some(DevelopTool::DepthBrush));
    let mut keyed = None;
    let _ = ctx.run(
        egui::RawInput {
            events: vec![egui::Event::Key {
                key: egui::Key::B,
                physical_key: None,
                pressed: true,
                repeat: false,
                modifiers: Default::default(),
            }],
            ..Default::default()
        },
        |ctx| keyed = tool_shortcut(ctx),
    );
    assert_eq!(keyed, Some(DevelopTool::DepthBrush));
}
