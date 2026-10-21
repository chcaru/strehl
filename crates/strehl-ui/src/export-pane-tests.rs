use super::*;
use std::sync::Arc;

#[test]
fn direct_photo_launch_opens_the_requested_pane_without_claiming_a_capture_history() {
    let path = PathBuf::from("standalone-not-decoded.tiff");
    for export in [false, true] {
        let app = StrehlApp::from_launch(
            4096,
            LaunchOptions {
                preview: Some(path.clone()),
                edit: !export,
                export,
                ..Default::default()
            },
        );
        assert_eq!(app.result.as_ref(), Some(&path));
        assert_eq!(app.pending_result.as_ref(), Some(&path));
        assert_eq!(app.progress.stage, Stage::Complete);
        assert!(app.stack.is_none());
        assert_eq!(
            app.sidebar,
            Some(if export {
                workspace::Sidebar::Export
            } else {
                workspace::Sidebar::Edit
            })
        );
    }
    let legacy = StrehlApp::from_launch(
        4096,
        LaunchOptions {
            preview: Some(path),
            ..Default::default()
        },
    );
    assert!(
        legacy.result.is_none(),
        "ordinary image browsing cannot claim stack ownership"
    );
}

fn fixture() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    let image = Arc::new(strehl_edit::LinearImage {
        width: 4,
        height: 3,
        pixels: vec![0.25; 36],
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    let path = PathBuf::from("never-written-export-photo.tiff");
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        image: image.clone(),
        preview: image,
        recipe: Default::default(),
        source: path,
        warnings: Vec::new(),
    });
    app
}

#[test]
fn hdr_preference_survives_sdr_photographs_and_lossless_formats() {
    let settings = ExportSettings::default();
    assert!(settings.hdr);
    assert_eq!(settings.format, ExportFormat::Avif);
    assert_eq!(settings.color_space, OutputColorSpace::Rec2020);
    assert_eq!(settings.quality, 100);
    assert!(!effective_settings(&settings, ImageOrigin::DisplayReferred).hdr);
    for format in [ExportFormat::Tiff, ExportFormat::Png, ExportFormat::Jpeg] {
        let mut changed = settings.clone();
        changed.format = format;
        assert!(!effective_settings(&changed, ImageOrigin::SceneLinear).hdr);
        assert!(
            changed.hdr,
            "temporary format fallback must not erase the preference"
        );
    }
    assert!(effective_settings(&settings, ImageOrigin::SceneLinear).hdr);
}

#[test]
fn chosen_format_controls_suffix_and_existing_aliases_are_preserved() {
    for (input, format, expected) in [
        ("photo.tiff", ExportFormat::Avif, "photo.avif"),
        ("photo.avif", ExportFormat::Png, "photo.png"),
        ("photo.JPG", ExportFormat::Jpeg, "photo.JPG"),
        ("photo.tif", ExportFormat::Tiff, "photo.tif"),
        ("photo", ExportFormat::Tiff, "photo.tiff"),
    ] {
        assert_eq!(
            formatted_path(input.into(), format),
            PathBuf::from(expected)
        );
    }
}

#[test]
fn export_destination_picker_cannot_deliver_a_changed_photograph() {
    for change_document in [false, true] {
        let mut app = fixture();
        app.export_pane.pending = Some(PendingExport {
            document: app.editor.path.clone().unwrap(),
            revision: app.editor.revision,
            settings: ExportSettings::default(),
        });
        if change_document {
            app.editor.path = Some("another-photo.tiff".into());
        } else {
            app.editor.revision += 1;
        }
        let error = app
            .finish_export_dialog("never-created.avif".into())
            .unwrap_err();
        assert!(error.to_string().contains("photograph changed"));
        assert!(app.editor.exporting.is_none());
        assert!(app.export_pane.pending.is_none());
    }
}

#[test]
fn export_pane_paint_preserves_edits_in_compact_and_tall_workspaces() {
    let mut app = fixture();
    app.editor.recipe.global.exposure = 0.7;
    let before = app.editor.recipe.clone();
    let ctx = egui::Context::default();
    for size in [egui::vec2(235.0, 350.0), egui::vec2(340.0, 900.0)] {
        for _ in 0..3 {
            let output = ctx.run(
                egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, size)),
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default().show(ctx, |ui| app.export_panel(ui));
                },
            );
            assert!(!output.shapes.is_empty());
            assert_eq!(app.editor.recipe, before);
            assert!(!app.editor.can_undo());
        }
    }
}
