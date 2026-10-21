//! Independent panel/close checks: expanded controls, new documents while typing,
//! and overlapping asynchronous close reasons rather than only a clean default.
use super::*;
use std::sync::Arc;

fn photograph(origin: ImageOrigin) -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    let image = Arc::new(strehl_edit::LinearImage {
        width: 3,
        height: 2,
        pixels: vec![0.3; 18],
        origin,
        baseline: None,
        baked_recipe: None,
    });
    let path = PathBuf::from("independent-export-first.tiff");
    app.result = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        image: image.clone(),
        preview: image,
        source: path,
        recipe: Default::default(),
        warnings: Vec::new(),
    });
    app.editor.saved_revision = Some(app.editor.revision);
    app
}

fn paint(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(340.0, 1100.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| app.export_panel(ui));
        },
    )
}

fn text_rect(output: &egui::FullOutput, label: &str) -> Option<egui::Rect> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Text(text) if text.galley.text() == label => Some(text.visual_bounding_rect()),
        _ => None,
    })
}

fn pointer(at: egui::Pos2, pressed: bool) -> Vec<egui::Event> {
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

fn expand_options(ctx: &egui::Context) {
    ctx.data_mut(|data| {
        data.insert_temp(
            egui::Id::new(("photo-edit-section", "export-luminance")),
            true,
        );
        data.insert_temp(
            egui::Id::new(("photo-edit-section", "export-encoding")),
            true,
        );
    });
}

#[test]
fn destination_and_saved_filename_offer_local_file_actions_without_starting_work() {
    for label in ["destination", "delivery.avif"] {
        let mut app = photograph(ImageOrigin::DisplayReferred);
        app.catalog.export_directories.insert(
            app.editor.path.clone().unwrap(),
            PathBuf::from("fixtures/destination"),
        );
        app.editor.last_export = Some(PathBuf::from("fixtures/destination/delivery.avif"));
        let before = app.editor.recipe.clone();
        let revision = app.editor.revision;
        let context = egui::Context::default();
        // The bottom panel discovers its content height on its first paint;
        // interact with the next settled layout, as the native window does.
        let _ = paint(&mut app, &context, 0.0, Vec::new());
        let initial = paint(&mut app, &context, 0.05, Vec::new());
        let at = text_rect(&initial, label)
            .unwrap_or_else(|| panic!("Missing visible path: {label}"))
            .center();
        for (time, pressed) in [(0.1, true), (0.2, false)] {
            let _ = paint(
                &mut app,
                &context,
                time,
                vec![
                    egui::Event::PointerMoved(at),
                    egui::Event::PointerButton {
                        pos: at,
                        button: egui::PointerButton::Secondary,
                        pressed,
                        modifiers: egui::Modifiers::NONE,
                    },
                ],
            );
        }
        let menu = paint(&mut app, &context, 0.3, Vec::new());
        assert!(text_rect(&menu, "Reveal in Explorer").is_some(), "{label}");
        assert!(text_rect(&menu, "Copy path").is_some(), "{label}");
        assert!(!app.photo_history_busy());
        assert!(app.editor.exporting.is_none());
        assert_eq!(app.editor.recipe, before);
        assert_eq!(app.editor.revision, revision);
    }
}

#[test]
fn expanded_export_controls_preserve_valid_extreme_luminance_and_truthful_tags() {
    for (origin, format, peak, white, tag) in [
        (
            ImageOrigin::SceneLinear,
            ExportFormat::Avif,
            80.0,
            80.0,
            "PQ · embedded CICP",
        ),
        (
            ImageOrigin::SceneLinear,
            ExportFormat::Avif,
            10_000.0,
            500.0,
            "PQ · embedded CICP",
        ),
        (
            ImageOrigin::DisplayReferred,
            ExportFormat::Avif,
            1000.0,
            203.0,
            "Embedded CICP",
        ),
        (
            ImageOrigin::SceneLinear,
            ExportFormat::Png,
            1000.0,
            203.0,
            "Embedded ICC profile",
        ),
    ] {
        let mut app = photograph(origin);
        app.export_pane.settings.format = format;
        app.editor.recipe.hdr.peak_nits = peak;
        app.editor.recipe.hdr.reference_white_nits = white;
        app.editor.recipe.validate().unwrap();
        let recipe = app.editor.recipe.clone();
        let revision = app.editor.revision;
        let ctx = egui::Context::default();
        expand_options(&ctx);
        for time in [0.0, 0.1, 0.2] {
            let output = paint(&mut app, &ctx, time, vec![]);
            assert!(
                text_rect(&output, tag).is_some(),
                "missing actual tagging label {tag}"
            );
            assert!(text_rect(&output, "Embedded CICP + ICC").is_none());
            if effective_settings(&app.export_pane.settings, origin).hdr {
                assert!(
                    text_rect(&output, "Peak brightness").is_some(),
                    "fixture must paint the expanded numeric controls"
                );
            }
            assert_eq!(app.editor.recipe, recipe);
            assert_eq!(app.editor.revision, revision);
            assert!(!app.editor.can_undo());
        }
    }
}

#[test]
fn export_luminance_typing_cannot_continue_into_another_photograph() {
    let mut app = photograph(ImageOrigin::SceneLinear);
    let ctx = egui::Context::default();
    expand_options(&ctx);
    let output = paint(&mut app, &ctx, 0.0, vec![]);
    let number = text_rect(&output, "1000 nits")
        .expect("real peak numeric editor is visible")
        .center();
    for (time, events) in [
        (0.1, pointer(number, true)),
        (0.15, pointer(number, false)),
        (0.18, vec![]),
        (0.2, vec![egui::Event::Text("750".into())]),
    ] {
        paint(&mut app, &ctx, time, events);
    }
    assert_eq!(
        app.editor.recipe.hdr.peak_nits, 750.0,
        "fixture must edit the real Export numeric control"
    );
    let focused = ctx
        .memory(|memory| memory.focused())
        .expect("number owns focus");
    assert_eq!(
        ctx.data_mut(|data| data.get_temp::<String>(focused))
            .as_deref(),
        Some("750")
    );

    // Simulate a document scope change without adding filesystem or worker noise.
    app.editor.path = Some("independent-export-second.tiff".into());
    app.result = app.editor.path.clone();
    app.editor.recipe.hdr.peak_nits = 1550.0;
    app.editor.recipe.hdr.reference_white_nits = 120.0;
    let recipe = app.editor.recipe.clone();
    let revision = app.editor.revision;
    for (time, events) in [
        (0.3, vec![]),
        (0.35, vec![egui::Event::Text("2".into())]),
        (0.4, pointer(egui::pos2(12.0, 12.0), true)),
        (0.45, pointer(egui::pos2(12.0, 12.0), false)),
        (0.5, vec![]),
    ] {
        paint(&mut app, &ctx, time, events);
    }
    assert_eq!(
        app.editor.recipe, recipe,
        "cached first-photo text leaked into the next photograph"
    );
    assert_eq!(app.editor.revision, revision);
}

#[test]
fn failed_export_cancels_every_deferred_close_reason() {
    let mut app = photograph(ImageOrigin::SceneLinear);
    app.editor.path = None; // This state-machine check must never write a sidecar.
    app.close_after_export = true;
    app.close_after_presets = true;
    app.editor.last_export = None;
    app.editor.error = Some("deliberate background export failure".into());
    let ctx = egui::Context::default();
    let output = ctx.run(egui::RawInput::default(), |ctx| app.handle_close(ctx));
    assert!(
        output.viewport_output[&egui::ViewportId::ROOT]
            .commands
            .iter()
            .any(|command| matches!(command, egui::ViewportCommand::CancelClose))
    );
    assert!(!app.close_after_export);
    assert!(
        !app.close_after_presets,
        "a second wait reason must not close on the next frame"
    );
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Export));
    for _ in 0..3 {
        let output = ctx.run(egui::RawInput::default(), |ctx| app.handle_close(ctx));
        assert!(
            !output.viewport_output[&egui::ViewportId::ROOT]
                .commands
                .iter()
                .any(|command| matches!(command, egui::ViewportCommand::Close))
        );
    }
    assert!(app.editor.error.as_deref().unwrap().contains("deliberate"));
}
