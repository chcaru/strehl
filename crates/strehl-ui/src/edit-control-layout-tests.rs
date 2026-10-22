//! Render the actual Edit pane; checking shared height constants alone would
//! miss egui minimum sizes, inherited spacing, and the numeric editor overflow.
use super::*;
use egui::{Color32, Pos2, Rect};
use std::sync::Arc;
use strehl_edit::{ImageOrigin, LinearImage};

fn fixture() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    let image = Arc::new(LinearImage {
        width: 40,
        height: 24,
        pixels: (0..960)
            .flat_map(|i| {
                let light = 0.02 + (i % 40) as f32 * 0.01;
                [light * 1.1, light, light * 0.8]
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    let path = PathBuf::from("never-written-edit-layout.tiff");
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        image: image.clone(),
        preview: image.clone(),
        source: path,
        recipe: Default::default(),
        warnings: Vec::new(),
    });
    app.editor.recipe = strehl_edit::analyze_adaptive(&image, &DevelopmentRecipe::default())
        .unwrap()
        .suggested;
    app.editor.set_tool(DrawingTool::Select);
    app.editor.saved_revision = Some(app.editor.revision);
    app
}

fn frame(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    width: f32,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(width, 850.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| app.edit_panel(ui));
        },
    )
}

fn label(output: &egui::FullOutput, needle: &str) -> Rect {
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == needle => {
                Some(text.visual_bounding_rect())
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("actual pane did not paint {needle}"))
}

fn button(output: &egui::FullOutput, needle: &str) -> Rect {
    let text = label(output, needle);
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if rect.rect.contains(text.center())
                    && rect.rect.width() >= text.width()
                    && rect.rect.height() <= 36.0
                    && rect.fill != Color32::TRANSPARENT =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .min_by(|a, b| a.area().total_cmp(&b.area()))
        .unwrap_or_else(|| panic!("missing painted button {needle}"))
}

fn pointer(at: Pos2, pressed: bool) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(at),
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        },
    ]
}

#[test]
fn actual_edit_pane_aligns_actions_and_keeps_amount_editor_clear_of_track() {
    for width in [230.0, 270.0, 440.0] {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let mut app = fixture();
        frame(&mut app, &ctx, width, 0.0, vec![]);
        let output = frame(&mut app, &ctx, width, 0.1, vec![]);
        let save = button(&output, "Save version…");
        let versions = button(&output, "Versions");
        let profile = button(&output, "Natural");
        let apply = button(&output, "Recalculate");
        for rect in [save, versions, profile, apply] {
            assert!(
                (rect.height() - 26.0).abs() < 0.1,
                "visible button must share the command height at pane width {width}: {rect:?}"
            );
            assert!(
                rect.left() >= 12.0 - 0.1 && rect.right() <= width - 12.0 + 0.1,
                "button escaped actual pane inset at width {width}: {rect:?}"
            );
        }
        assert!((save.width() - versions.width()).abs() < 0.1);
        assert!((save.center().y - versions.center().y).abs() < 0.1);
        assert!((profile.center().y - apply.center().y).abs() < 0.1);
        assert!(profile.right() + 4.0 <= apply.left());
        let select = button(&output, "Select");
        let more = button(&output, "···");
        let shelf_title = label(&output, "Regions  0");
        let shelf = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Rect(rect)
                    if rect.fill == PANEL
                        && rect.rect.contains(shelf_title.center())
                        && rect.rect.width() >= width - 1.0 =>
                {
                    Some(rect.rect)
                }
                _ => None,
            })
            .min_by(|a, b| a.area().total_cmp(&b.area()))
            .expect("actual Regions shelf must paint its background");
        assert!(
            shelf.bottom() <= 850.1,
            "Regions contents must not expand the painted shelf beyond the viewport: {shelf:?}"
        );
        assert!(
            (save.left() - profile.left()).abs() < 0.1
                && (select.left() - profile.left()).abs() < 0.1,
            "header, adjustments, and region tools must share their left edge at {width}: save={save:?} profile={profile:?} select={select:?}"
        );
        assert!(
            (versions.right() - apply.right()).abs() < 0.1
                && (more.right() - apply.right()).abs() < 0.1,
            "fixed commands must reserve the scrolling controls' gutter: {versions:?} {more:?} {apply:?}"
        );
        let amount = label(&output, "Amount");
        assert!((amount.left() - save.left()).abs() < 0.1);
        let number = button(&output, "1.00");
        assert!((number.right() - apply.right()).abs() < 0.1);
        let number_text = label(&output, "1.00");
        assert!(
            (amount.center().y - number_text.center().y).abs() < 1.0,
            "amount label/value text must align: {amount:?} {number_text:?}"
        );
        assert!(amount.right() < number.left());
        let handle = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Rect(rect)
                    if rect.rect.width() <= 14.0
                        && rect.rect.height() > 7.0
                        && rect.rect.top() >= number.bottom()
                        && rect.rect.top() < number.bottom() + 20.0
                        && rect.rect.right() > number.right() - 20.0 =>
                {
                    Some(rect.rect)
                }
                _ => None,
            })
            .next()
            .expect("Amount=1 must paint its actual slider handle at the right end");
        assert!(
            handle.top() >= number.bottom() + 1.0,
            "numeric editor must not touch or cover the slider handle: {number:?} {handle:?}"
        );

        // Exercise an actual overflow -> fits transition. A conditionally
        // allocated scrollbar would shift the entire control grid sideways.
        let mut collapsed = output;
        let mut time = 0.2;
        for name in ["Light", "Color"] {
            let at = label(&collapsed, name).center();
            frame(&mut app, &ctx, width, time, pointer(at, true));
            frame(&mut app, &ctx, width, time + 0.05, pointer(at, false));
            collapsed = frame(&mut app, &ctx, width, time + 0.1, vec![]);
            time += 0.3;
        }
        for section in ["light", "color"] {
            assert_eq!(
                ctx.data(
                    |data| data.get_temp::<bool>(egui::Id::new(("photo-edit-section", section)))
                ),
                Some(false),
                "real pointer clicks must actually collapse the sections"
            );
        }
        assert!(
            label(&collapsed, "Display").bottom() + 50.0 < label(&collapsed, "Regions  0").top(),
            "collapsed fixture must have spare room instead of retaining scroll overflow"
        );
        for (name, before) in [
            ("Versions", versions),
            ("Recalculate", apply),
            ("1.00", number),
            ("Select", select),
        ] {
            let after = button(&collapsed, name);
            assert!(
                (before.left() - after.left()).abs() < 0.1
                    && (before.right() - after.right()).abs() < 0.1,
                "collapsing content must not shift {name} horizontally: {before:?} {after:?}"
            );
        }
    }
}

#[test]
fn amount_label_and_value_align_with_bundled_fonts_and_fractional_display_scales() {
    for pixels_per_point in [1.0, 1.25, 1.5, 2.0] {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        // Linux/macOS use these bundled faces. Windows otherwise substitutes
        // Segoe UI, whose metrics conceal the different glyph-row alignment.
        ctx.set_fonts(egui::FontDefinitions::default());
        ctx.set_pixels_per_point(pixels_per_point);
        let mut app = fixture();
        frame(&mut app, &ctx, 270.0, 0.0, vec![]);
        let output = frame(&mut app, &ctx, 270.0, 0.1, vec![]);
        let number = button(&output, "1.00");
        frame(&mut app, &ctx, 270.0, 0.2, pointer(number.center(), true));
        frame(&mut app, &ctx, 270.0, 0.25, pointer(number.center(), false));
        let editing = frame(&mut app, &ctx, 270.0, 0.3, vec![]);
        assert!(
            ctx.memory(|memory| memory.focused().is_some()),
            "The variant must exercise the actual text editor"
        );
        for (state, output) in [("display", &output), ("typing", &editing)] {
            let amount = label(output, "Amount");
            let value = label(output, "1.00");
            assert!(
                (amount.left() - 12.0).abs() < 0.1,
                "Amount caption must keep the pane's left edge while {state}: {amount:?}"
            );
            assert!(
                (amount.center().y - value.center().y).abs() < 1.0,
                "Bundled-font Amount row must align while {state} at {pixels_per_point} pixels/point: {amount:?} {value:?}"
            );
        }
    }
}

#[test]
fn actual_profile_menu_applies_signature_and_disabled_pane_cannot_start_it() {
    for enabled in [true, false] {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let mut app = fixture();
        if !enabled {
            app.editor
                .recipe
                .regions
                .push(strehl_edit::RegionAdjustment {
                    id: "off".into(),
                    name: "Disabled region".into(),
                    note: String::new(),
                    shape: strehl_edit::RegionShape::Ellipse {
                        center: [0.5, 0.5],
                        radius: [0.2, 0.2],
                    },
                    feather: 0.1,
                    enabled: false,
                    adjustments: Default::default(),
                    source_range: None,
                });
            app.editor.selected = Some("off".into());
        }
        // Let the actual scroll area and collapsing section settle before
        // targeting a widget; their first pass establishes hit-test geometry.
        frame(&mut app, &ctx, 270.0, 0.0, vec![]);
        let initial = frame(&mut app, &ctx, 270.0, 0.05, vec![]);
        let at = label(&initial, "Natural").center();
        frame(
            &mut app,
            &ctx,
            270.0,
            0.08,
            vec![egui::Event::PointerMoved(at)],
        );
        frame(&mut app, &ctx, 270.0, 0.1, pointer(at, true));
        frame(&mut app, &ctx, 270.0, 0.15, pointer(at, false));
        if enabled {
            assert!(
                egui::Popup::is_any_open(&ctx),
                "the actual profile control must open its menu"
            );
            // A newly opened egui popup has an invisible sizing pass before
            // its rows acquire their displayed position and hit rectangles.
            let menu = frame(&mut app, &ctx, 270.0, 0.2, vec![]);
            let choice = label(&menu, "Signature").center();
            frame(&mut app, &ctx, 270.0, 0.3, pointer(choice, true));
            frame(&mut app, &ctx, 270.0, 0.35, pointer(choice, false));
            assert!(
                app.adaptive_busy(),
                "selecting a profile must apply it without a second command"
            );
        } else {
            assert!(
                !egui::Popup::is_any_open(&ctx),
                "disabled scope must not expose active profile choices"
            );
            assert!(!app.adaptive_busy());
        }
    }
}
