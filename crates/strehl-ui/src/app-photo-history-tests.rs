use super::*;

struct Files(PathBuf);
impl Files {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "strehl-photo-ui-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).unwrap();
        Self(root)
    }
    fn app(&self) -> StrehlApp {
        let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
        app.catalog = crate::workspace_history::Catalog::load(Some(self.0.join("projects.json")));
        let path = self.0.join("photograph.tiff");
        image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
            8,
            6,
            image::Rgb([18000, 25000, 8000]),
        )
        .save(&path)
        .unwrap();
        let image = Arc::new(strehl_edit::load_tiff(&path).unwrap());
        app.editor.path = Some(path.clone());
        app.result = Some(path.clone());
        app.image_path = Some(path.clone());
        app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
            coverage: None,
            image: image.clone(),
            preview: image,
            source: path,
            recipe: Default::default(),
            warnings: vec![],
        });
        app.editor.saved_revision = Some(app.editor.revision);
        app
    }
}
impl Drop for Files {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
fn drain(app: &mut StrehlApp) {
    let ctx = egui::Context::default();
    let until = std::time::Instant::now() + Duration::from_secs(10);
    while app.photo_history_busy() {
        app.editor.poll(&ctx, 4096);
        app.poll_photo_history(&ctx);
        assert!(std::time::Instant::now() < until, "History did not settle");
        std::thread::sleep(Duration::from_millis(2));
    }
}

#[test]
fn restore_is_one_undo_and_preserves_previous_edits_as_a_durable_version() {
    let files = Files::new();
    let mut app = files.app();
    app.editor.recipe.global.exposure = 0.75;
    app.save_edit_version("Warm first edit").unwrap();
    drain(&mut app);
    assert!(
        app.photo_history.error.is_none(),
        "{:?}",
        app.photo_history.error
    );
    let first = app.catalog.photo_versions[0].id.clone();
    let mut changed = app.editor.recipe.clone();
    changed.global.exposure = -1.25;
    app.editor.replace(changed.clone()).unwrap();
    app.restore_edit_version(&first).unwrap();
    drain(&mut app);
    assert!(
        app.photo_history.error.is_none(),
        "{:?}",
        app.photo_history.error
    );
    assert_eq!(app.editor.recipe.global.exposure, 0.75);
    assert_eq!(app.catalog.photo_versions.len(), 2);
    assert!(app.editor.undo());
    assert_eq!(app.editor.recipe, changed);
    let reloaded = crate::workspace_history::Catalog::load(app.catalog.path.clone());
    assert_eq!(reloaded.photo_versions.len(), 2);
    let backup = &reloaded.photo_versions[1];
    let image = &app.editor.loaded.as_ref().unwrap().image;
    assert_eq!(
        photographs::read_version(
            &reloaded.history_root().unwrap(),
            backup,
            &backup.owner,
            image,
            &backup.owner.output,
            &std::sync::atomic::AtomicBool::new(false)
        )
        .unwrap(),
        changed
    );
}

#[test]
fn asynchronous_restore_cannot_replace_newer_edits_or_another_photo() {
    for different_photo in [false, true] {
        let files = Files::new();
        let mut app = files.app();
        app.save_edit_version("Initial").unwrap();
        drain(&mut app);
        let id = app.catalog.photo_versions[0].id.clone();
        app.restore_edit_version(&id).unwrap();
        let mut latest = app.editor.recipe.clone();
        latest.global.exposure = 2.0;
        app.editor.replace(latest.clone()).unwrap();
        if different_photo {
            app.editor.path = Some(files.0.join("other.tiff"));
        }
        drain(&mut app);
        assert_eq!(app.editor.recipe, latest);
        assert!(
            app.photo_history
                .error
                .as_ref()
                .unwrap()
                .contains("changed while restoring")
        );
        assert!(app.flush_photo_history(&egui::Context::default()).is_err());
    }
}

#[test]
fn successful_export_keeps_original_owner_recipe_and_delivery_settings_after_navigation() {
    let files = Files::new();
    let mut app = files.app();
    let original = app.editor.path.clone().unwrap();
    app.editor.recipe.global.exposure = 0.6;
    let path = files.0.join("delivery.png");
    let settings = ExportSettings {
        format: strehl_edit::ExportFormat::Png,
        hdr: false,
        color_space: strehl_edit::OutputColorSpace::DisplayP3,
        ..Default::default()
    };
    app.start_tracked_export(path.clone(), settings.clone())
        .unwrap();
    let ctx = egui::Context::default();
    let until = std::time::Instant::now() + Duration::from_secs(10);
    while app.editor.exporting.is_none() {
        app.poll_photo_history(&ctx);
        assert!(
            std::time::Instant::now() < until,
            "{:?}",
            app.photo_history.error
        );
        std::thread::sleep(Duration::from_millis(2));
    }
    app.editor.path = Some(files.0.join("new-document.tiff"));
    app.result = app.editor.path.clone();
    drain(&mut app);
    assert!(
        app.photo_history.error.is_none(),
        "{:?}",
        app.photo_history.error
    );
    assert_eq!(app.catalog.photo_exports.len(), 1);
    let export = &app.catalog.photo_exports[0];
    assert_eq!(export.path, path);
    assert_eq!(export.settings, settings);
    let version = app
        .catalog
        .photo_versions
        .iter()
        .find(|v| v.id == export.version)
        .unwrap();
    assert_eq!(version.owner.output, original);
    assert!(path.is_file());
    assert_eq!(
        crate::workspace_history::Catalog::load(app.catalog.path.clone())
            .photo_exports
            .len(),
        1
    );
}

#[test]
fn export_default_and_explicit_alternate_are_per_photograph() {
    let files = Files::new();
    let mut app = files.app();
    assert_eq!(app.export_destination_for_current(), Some(files.0.clone()));
    let alternate = files.0.join("deliveries");
    std::fs::create_dir(&alternate).unwrap();
    app.set_export_directory(alternate.clone()).unwrap();
    assert_eq!(
        app.export_destination_for_current(),
        Some(alternate.clone())
    );
    let original = app.editor.path.clone();
    app.editor.path = Some(files.0.join("different-folder").join("photo.tiff"));
    assert_eq!(
        app.export_destination_for_current(),
        Some(files.0.join("different-folder"))
    );
    app.editor.path = original;
    app.catalog = crate::workspace_history::Catalog::load(app.catalog.path.clone());
    assert_eq!(app.export_destination_for_current(), Some(alternate));
}

#[test]
fn export_version_preparation_rejects_new_edits_or_same_path_reload() {
    for change in 0..3 {
        let files = Files::new();
        let mut app = files.app();
        app.editor.recipe.global.exposure = 0.65;
        let frozen_recipe = app.editor.recipe.clone();
        let frozen_image = app.editor.loaded.as_ref().unwrap().image.clone();
        let output = files.0.join("must-not-publish.png");
        let settings = ExportSettings {
            format: strehl_edit::ExportFormat::Png,
            hdr: false,
            color_space: strehl_edit::OutputColorSpace::Srgb,
            ..Default::default()
        };
        app.start_tracked_export(output.clone(), settings).unwrap();
        assert!(app.photo_history.pending.is_some());
        // Change the live state before accepting the real worker completion.
        if change == 0 {
            app.editor.loaded.as_mut().unwrap().image = Arc::new((*frozen_image).clone());
        } else if change == 1 {
            let mut next = app.editor.recipe.clone();
            next.global.exposure = -1.5;
            app.editor.replace(next).unwrap();
        } else {
            let revision = app.editor.revision;
            app.editor.recipe.global.exposure = -1.5;
            assert_eq!(app.editor.revision, revision);
        }
        drain(&mut app);
        assert!(app.editor.exporting.is_none());
        assert!(!output.exists());
        assert!(app.catalog.photo_exports.is_empty());
        assert!(
            app.photo_history
                .error
                .as_ref()
                .unwrap()
                .contains("changed while preparing export")
        );
        let version = app
            .catalog
            .photo_versions
            .last()
            .expect("The immutable pre-export version must remain recoverable");
        let restored = photographs::read_version(
            &app.catalog.history_root().unwrap(),
            version,
            &version.owner,
            &frozen_image,
            &version.owner.output,
            &std::sync::atomic::AtomicBool::new(false),
        )
        .unwrap();
        assert_eq!(restored, frozen_recipe);
    }
}

#[test]
fn restoring_the_current_recipe_is_a_provenance_checked_no_op() {
    let files = Files::new();
    let mut app = files.app();
    app.save_edit_version("Current edit").unwrap();
    drain(&mut app);
    let version = app.catalog.photo_versions[0].id.clone();
    let revision = app.editor.revision;
    app.restore_edit_version(&version).unwrap();
    drain(&mut app);
    assert!(
        app.photo_history.error.is_none(),
        "{:?}",
        app.photo_history.error
    );
    assert_eq!(app.catalog.photo_versions.len(), 1);
    assert_eq!(app.editor.revision, revision);
    assert!(
        !app.editor.undo(),
        "An identical restore must not add an undo or backup"
    );
    assert!(
        app.photo_history
            .status
            .as_ref()
            .unwrap()
            .contains("already applied")
    );
}

#[test]
fn missing_browser_targets_show_feedback_without_creating_or_erasing_durable_failure() {
    for prior_failure in [false, true] {
        for reveal in [false, true] {
            let files = Files::new();
            let mut app = files.app();
            if prior_failure {
                app.photo_history.failed_operation = true;
                app.photo_history.error = Some("prior durable write failed".into());
            }
            let path = files.0.join("missing-delivery.png");
            if reveal {
                app.handle_photo_history_action(
                    crate::project_explorer::ExplorerAction::RevealPath { path },
                );
            } else {
                let id = "a".repeat(32);
                app.catalog.photo_exports.push(serde_json::from_value(serde_json::json!({"id":id,"version":"b".repeat(32),"path":path,"created":1,"settings":strehl_edit::ExportSettings::default(),"bytes":1,"sha256":"c".repeat(64)})).unwrap());
                app.open_recorded_export(&id).unwrap();
            }
            assert!(
                app.photo_history.pending.is_some(),
                "The real asynchronous action must run"
            );
            drain(&mut app);
            assert_eq!(app.photo_history.failed_operation, prior_failure);
            assert_eq!(
                app.flush_photo_history(&egui::Context::default()).is_err(),
                prior_failure
            );
            if prior_failure {
                assert_eq!(
                    app.photo_history.error.as_deref(),
                    Some("prior durable write failed")
                );
            } else {
                assert!(
                    app.photo_history.error.is_some(),
                    "A nondurable failure still needs visible feedback"
                );
            }
        }
    }
}
