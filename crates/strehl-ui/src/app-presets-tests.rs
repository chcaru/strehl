use super::*;
use strehl_edit::{Adjustments, ImageOrigin, RegionAdjustment, RegionShape, SourceRange};

fn fixture() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    app.presets.initialized = true;
    let mut pixels = Vec::new();
    for y in 0..96 {
        for x in 0..128 {
            let light = 0.025 + 0.42 * (x + y) as f32 / 222.0;
            pixels.extend_from_slice(&[light * 1.12, light, light * 0.83]);
        }
    }
    let image = Arc::new(LinearImage {
        width: 128,
        height: 96,
        pixels,
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    let path = PathBuf::from("never-written-preset-photo.tiff");
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        coverage: None,
        image: image.clone(),
        preview: image,
        recipe: Default::default(),
        source: path,
        warnings: Vec::new(),
    });
    app.editor.recipe.regions.push(RegionAdjustment {
        id: "reflection".into(),
        name: "Reflection".into(),
        note: "Keep evidence".into(),
        shape: RegionShape::Ellipse {
            center: [0.6, 0.4],
            radius: [0.25, 0.2],
        },
        feather: 0.3,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: Some(SourceRange { first: 2, last: 5 }),
    });
    app
}

fn add(app: &mut StrehlApp, adaptive: bool) -> String {
    app.presets
        .library
        .add(
            "Warm specimen",
            PresetSettings {
                adjustments: Adjustments {
                    exposure: 0.7,
                    temperature: 12.0,
                    ..Default::default()
                },
                adaptive: adaptive.then(|| AdaptivePreset {
                    intent: AdaptiveIntent::Balance,
                    amount: 0.8,
                    parameters: Default::default(),
                }),
            },
        )
        .unwrap()
}

fn finish(app: &mut StrehlApp, ctx: &egui::Context) {
    let deadline = Instant::now() + Duration::from_secs(5);
    while app.presets_busy() {
        app.poll_presets(ctx);
        assert!(Instant::now() < deadline, "preset worker did not complete");
        std::thread::yield_now();
    }
}

#[test]
fn static_preset_is_one_scoped_undo_action_and_preserves_repair_identity() {
    for selected in [None, Some("reflection".to_string())] {
        let mut app = fixture();
        app.editor.selected = selected.clone();
        let before = app.editor.recipe.clone();
        let id = add(&mut app, false);
        app.apply_saved_look(&id, &egui::Context::default())
            .unwrap();
        let after = app.editor.recipe.clone();
        assert_ne!(after, before);
        if selected.is_some() {
            assert_eq!(after.global, before.global);
            assert_eq!(after.regions[0].adjustments.exposure, 0.7);
        } else {
            assert_eq!(after.global.exposure, 0.7);
            assert_eq!(after.regions, before.regions);
        }
        assert_eq!(
            after.regions[0].source_range,
            before.regions[0].source_range
        );
        assert_eq!(after.regions[0].shape, before.regions[0].shape);
        assert!(app.editor.undo());
        assert_eq!(app.editor.recipe, before);
        assert!(!app.editor.can_undo());
        assert!(app.editor.redo());
        assert_eq!(app.editor.recipe, after);
    }
}

#[test]
fn adaptive_preset_publishes_controls_and_destination_analysis_together() {
    let mut app = fixture();
    let ctx = egui::Context::default();
    let id = add(&mut app, true);
    let before = app.editor.recipe.clone();
    app.apply_saved_look(&id, &ctx).unwrap();
    assert!(app.presets_busy());
    assert_eq!(
        app.editor.recipe, before,
        "no partial slider application while analysis runs"
    );
    assert!(
        app.start_adaptive(0.5).is_err(),
        "a second action must not race preset completion"
    );
    // Before is a transient comparison, not a new recipe. An explicit preset
    // commit returns to the resulting look, just like synchronous application.
    app.editor.before = true;
    finish(&mut app, &ctx);
    assert!(!app.editor.before);
    assert_eq!(app.editor.recipe.global.exposure, 0.7);
    assert!(
        app.editor.recipe.adaptive_scope(None).is_some(),
        "fixture must exercise real spatial recomputation"
    );
    assert_eq!(app.editor.recipe.regions, before.regions);
    assert!(app.editor.undo());
    assert_eq!(app.editor.recipe, before);
    assert!(!app.editor.can_undo(), "one application must be one Undo");
}

#[test]
fn changed_scope_document_or_revision_discards_pending_preset() {
    for changed in 0..6 {
        let mut app = fixture();
        let ctx = egui::Context::default();
        let id = add(&mut app, true);
        app.apply_saved_look(&id, &ctx).unwrap();
        match changed {
            0 => app.editor.selected = Some("reflection".into()),
            1 => app.editor.path = Some("another-photo.tiff".into()),
            2 => {
                let mut recipe = app.editor.recipe.clone();
                recipe.global.saturation = -25.0;
                app.editor.replace(recipe).unwrap();
            }
            3 => {
                let image = app.editor.loaded.as_ref().unwrap().image.as_ref().clone();
                app.editor.loaded.as_mut().unwrap().image = Arc::new(image);
            }
            4 => app.result = Some("new-result-before-editor-opens.tiff".into()),
            _ => app.image_path = Some("different-displayed-image.tiff".into()),
        }
        let newer = app.editor.recipe.clone();
        app.poll_presets(&ctx);
        assert!(!app.presets_busy());
        assert_eq!(
            app.editor.recipe, newer,
            "stale result must not overwrite newer intent"
        );
        assert!(app.presets.status.as_ref().unwrap().contains("cancelled"));
    }
}

#[test]
fn saving_a_look_captures_scope_once_and_excludes_photo_specific_state() {
    let mut app = fixture();
    app.editor.selected = Some("reflection".into());
    app.editor.recipe.regions[0].adjustments.highlights = -36.0;
    app.save_current_look().unwrap();
    app.editor.selected = None;
    app.editor.recipe.global.exposure = 2.0;
    let Some(NameForm::Save { name, .. }) = app.presets.form.as_mut() else {
        panic!("save form missing")
    };
    *name = "Reflection control".into();
    let before = app.editor.recipe.clone();
    app.presets.finish_form().unwrap();
    assert_eq!(
        app.editor.recipe, before,
        "saving must never edit the photograph"
    );
    let settings = &app.presets.library.presets[0].settings;
    assert_eq!(settings.adjustments.highlights, -36.0);
    assert_eq!(
        settings.adjustments.exposure, 0.0,
        "switching scope while naming must not change captured settings"
    );
    assert!(
        !serde_json::to_string(settings)
            .unwrap()
            .contains("source_range")
    );
}

#[test]
fn ordinary_panel_painting_neither_mutates_recipe_nor_starts_io() {
    let mut app = fixture();
    let ctx = egui::Context::default();
    add(&mut app, false);
    let before = app.editor.recipe.clone();
    let library = app.presets.library.clone();
    for time in [0.0, 0.02, 0.04] {
        let _ = ctx.run(
            egui::RawInput {
                time: Some(time),
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(230.0, 500.0),
                )),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| app.presets_panel(ui));
            },
        );
    }
    assert_eq!(app.editor.recipe, before);
    assert_eq!(app.presets.library, library);
    assert!(
        app.presets.saving.is_none()
            && app.presets.loading.is_none()
            && app.presets.applying.is_none()
    );
}

#[test]
fn close_waits_for_durable_save_and_failure_retains_the_unsaved_library() {
    let mut app = fixture();
    let ctx = egui::Context::default();
    let dir = std::env::temp_dir().join(format!(
        "strehl-preset-close-{}-{}",
        std::process::id(),
        crate::workspace_history::timestamp()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    let blocker = dir.join("parent-is-file");
    std::fs::write(&blocker, b"preserve").unwrap();
    app.presets.path = Some(blocker.join("looks.json"));
    add(&mut app, false);
    app.presets.changed();
    let before = app.presets.library.clone();
    assert!(
        !app.flush_presets(&ctx).unwrap(),
        "close must wait while save is pending"
    );
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        match app.flush_presets(&ctx) {
            Err(_) => break,
            Ok(false) => {
                assert!(Instant::now() < deadline);
                std::thread::yield_now();
            }
            Ok(true) => panic!("failing save was reported durable"),
        }
    }
    assert_eq!(app.presets.library, before);
    assert_eq!(std::fs::read(&blocker).unwrap(), b"preserve");
    app.presets.path = Some(dir.join("looks.json"));
    app.presets.error = None;
    while !app.flush_presets(&ctx).unwrap() {
        assert!(Instant::now() < deadline);
        std::thread::yield_now();
    }
    assert_eq!(
        develop_presets::load(app.presets.path.as_ref().unwrap())
            .unwrap()
            .library,
        before
    );
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn conflict_recovery_keeps_both_libraries_and_allows_close() {
    let mut app = fixture();
    let ctx = egui::Context::default();
    let dir = std::env::temp_dir().join(format!(
        "strehl-preset-recovery-{}-{}",
        std::process::id(),
        crate::workspace_history::timestamp()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("develop-presets.json");
    app.presets.bytes = Some(develop_presets::save(&path, &Library::default(), None).unwrap());
    app.presets.path = Some(path.clone());
    add(&mut app, false);
    app.presets.changed();
    let pending = app.presets.library.clone();
    let mut external = Library::default();
    external
        .add(
            "Another window",
            PresetSettings {
                adjustments: Default::default(),
                adaptive: None,
            },
        )
        .unwrap();
    let remote_bytes =
        develop_presets::save(&path, &external, app.presets.bytes.as_deref()).unwrap();
    app.presets.error = Some("Conflicting saved version".into());
    assert!(app.flush_presets(&ctx).is_err());
    app.presets.keep_recovery_and_reload(&ctx);
    let deadline = Instant::now() + Duration::from_secs(5);
    while !app.flush_presets(&ctx).unwrap() {
        assert!(Instant::now() < deadline);
        std::thread::yield_now();
    }
    assert_eq!(app.presets.library, external);
    assert_eq!(std::fs::read(&path).unwrap(), remote_bytes);
    let recovery = app
        .presets
        .recovery_path
        .as_ref()
        .expect("durable recovery path");
    assert_eq!(develop_presets::load(recovery).unwrap().library, pending);
    assert_ne!(recovery, &path);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn close_waits_for_preset_publication_and_adaptive_cannot_race_it() {
    let mut app = fixture();
    let ctx = egui::Context::default();
    let before = app.editor.recipe.clone();
    let mut after = before.clone();
    after.global.exposure = 0.9;
    let worker_recipe = after.clone();
    let (release, blocked) = std::sync::mpsc::sync_channel(1);
    let image = app.editor.loaded.as_ref().unwrap().image.clone();
    app.presets.applying = Some(Applying {
        path: app.editor.path.clone(),
        image,
        revision: app.editor.revision,
        region: None,
        magic_generation: app.editor.magic_generation(),
        name: "Delayed look".into(),
        task: jobs::spawn_notifying_task(
            "preset-close-control",
            move |_| {
                blocked.recv()?;
                Ok(worker_recipe)
            },
            || {},
        ),
    });
    assert!(
        !app.flush_presets(&ctx).unwrap(),
        "a pending application is not safe to close"
    );
    assert!(app.start_adaptive(0.5).is_err());
    assert_eq!(app.editor.recipe, before);
    release.send(()).unwrap();
    let deadline = Instant::now() + Duration::from_secs(5);
    while !app.flush_presets(&ctx).unwrap() {
        assert!(Instant::now() < deadline);
        std::thread::yield_now();
    }
    assert_eq!(app.editor.recipe, after);
    assert!(app.editor.undo());
    assert_eq!(app.editor.recipe, before);

    // Reverse order must also reject, rather than publishing whichever worker
    // happens to finish first.
    app.start_adaptive(0.5).unwrap();
    let id = add(&mut app, true);
    assert!(app.apply_saved_look(&id, &ctx).is_err());
    assert!(!app.presets_busy());
}
