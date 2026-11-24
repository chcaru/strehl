use super::*;
use std::sync::atomic::AtomicBool;

fn editor() -> EditorState {
    let image = Arc::new(LinearImage {
        width: 64,
        height: 48,
        pixels: vec![0.2; 64 * 48 * 3],
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    EditorState {
        path: Some("same-path.tiff".into()),
        loaded: Some(LoadedPhoto {
            coverage: None,
            preview: Arc::new(image.preview(16)),
            image,
            recipe: Default::default(),
            source: "same-path.tiff".into(),
            warnings: vec![],
        }),
        ..Default::default()
    }
}

fn settle(editor: &mut EditorState) {
    let ctx = egui::Context::default();
    let until = Instant::now() + Duration::from_secs(8);
    loop {
        editor.poll(&ctx, 4096);
        if editor.developing.is_none()
            && editor.painted_snapshot == editor.development.as_ref().map(|(_, _, job)| job.token())
        {
            break;
        }
        assert!(Instant::now() < until);
        std::thread::sleep(Duration::from_millis(2));
    }
}

#[test]
fn current_snapshot_is_shared_until_source_recipe_or_before_changes() {
    let mut state = editor();
    let first = state.development_job(false).unwrap();
    assert_eq!(first.token(), state.development_job(false).unwrap().token());
    settle(&mut state);
    assert_eq!(state.painted_snapshot, Some(first.token()));
    let mut recipe = state.recipe.clone();
    recipe.global.exposure = 0.5;
    state.replace(recipe).unwrap();
    let edited = state.development_job(false).unwrap();
    assert_ne!(first.token(), edited.token());
    let before = state.development_job(true).unwrap();
    assert_ne!(edited.token(), before.token());
    assert_eq!(before.recipe(), &DevelopmentRecipe::default());
    assert!(state.undo());
    let undone = state.development_job(false).unwrap();
    assert_eq!(undone.recipe(), first.recipe());
    assert_ne!(
        undone.token(),
        first.token(),
        "Undo cannot revive an earlier asynchronous token"
    );
    let reloaded = Arc::new((*state.loaded.as_ref().unwrap().image).clone());
    state.loaded.as_mut().unwrap().image = reloaded.clone();
    let new = state.development_job(false).unwrap();
    assert_ne!(undone.token(), new.token());
    assert!(new.matches_source(&reloaded));
    assert!(!undone.matches_source(&reloaded));
}

#[test]
fn continuing_slider_gesture_replaces_snapshot_before_history_commit() {
    let mut state = editor();
    let first = state.development_job(false).unwrap();
    for (time, exposure) in [(1., 0.4), (1.1, 0.8), (1.2, 1.1)] {
        let before = state.recipe.clone();
        let previous = state.development_job(false).unwrap();
        state.recipe.global.exposure = exposure;
        state.begin_edit(before, time);
        assert!(state.pending_edit.is_some());
        assert_eq!(state.history_commits(), 0);
        let current = state.development_job(false).unwrap();
        assert_ne!(previous.token(), current.token());
        assert_eq!(current.recipe().global.exposure, exposure);
    }
    state.commit_edit();
    assert_eq!(state.history_commits(), 1);
    assert_ne!(first.token(), state.development_job(false).unwrap().token());
}

#[test]
fn export_acceptance_refreshes_direct_recipe_changes_without_revision_bump() {
    let mut state = editor();
    let previous = state.development_job(false).unwrap();
    let revision = state.revision;
    state.recipe.global.exposure = 0.9;
    let frozen = state.freeze_export_job().unwrap();
    assert_eq!(state.revision, revision);
    assert_ne!(previous.token(), frozen.token());
    assert_eq!(frozen.recipe(), &state.recipe);
    assert!(Arc::ptr_eq(previous.image(false), frozen.image(false)));
}

#[test]
fn same_path_same_revision_reload_discards_ready_coarse_pixels_and_keeps_latest() {
    let mut state = editor();
    let old = state.development_job(false).unwrap();
    let revision = state.revision;
    let prepared = crate::photo_viewport::prepare_job(
        &old,
        false,
        strehl_edit::DisplayRegionRequest {
            min: [0, 0],
            max: [64, 48],
            stride: 1,
        },
        &AtomicBool::new(false),
        None,
        false,
        true,
    )
    .unwrap();
    let task = spawn_task("stale-ready-coarse", move |_| {
        Ok(DevelopedPreview {
            histogram: None,
            snapshot: old.token(),
            revision,
            before: false,
            hdr: false,
            prepared,
        })
    });
    std::thread::sleep(Duration::from_millis(10));
    state.developing = Some(task);
    state.developing_revision = Some(revision);
    state.developing_snapshot = state.development.as_ref().map(|(_, _, job)| job.token());
    let loaded = state.loaded.as_mut().unwrap();
    loaded.image = Arc::new((*loaded.image).clone());
    loaded.preview = Arc::new(loaded.image.preview(13));
    settle(&mut state);
    assert_eq!(state.revision, revision);
    assert_eq!(
        state.texture.as_ref().unwrap().size(),
        [13, 10],
        "The old 64x48 completion must not publish"
    );
    assert_eq!(
        state.painted_snapshot,
        state.development.as_ref().map(|(_, _, job)| job.token())
    );
}

#[test]
fn explicit_cancelled_ready_coarse_result_is_replaced_not_published() {
    let mut state = editor();
    let job = state.development_job(false).unwrap();
    let token = job.token();
    let prepared = crate::photo_viewport::prepare_job(
        &job,
        false,
        strehl_edit::DisplayRegionRequest {
            min: [0, 0],
            max: [64, 48],
            stride: 1,
        },
        &AtomicBool::new(false),
        None,
        false,
        true,
    )
    .unwrap();
    let task = spawn_task("cancel-ready-coarse", move |_| {
        Ok(DevelopedPreview {
            histogram: None,
            snapshot: token,
            revision: 0,
            before: false,
            hdr: false,
            prepared,
        })
    });
    std::thread::sleep(Duration::from_millis(10));
    task.cancel();
    state.developing = Some(task);
    state.developing_revision = Some(0);
    state.developing_snapshot = Some(token);
    settle(&mut state);
    assert_eq!(state.texture.as_ref().unwrap().size(), [16, 12]);
}

#[test]
fn accepted_export_uses_frozen_recipe_after_edit_and_reload_and_cancel_refuses_publish() {
    let mut state = editor();
    state.recipe.global.exposure = 0.6;
    let job = state.development_job(false).unwrap();
    let root = tempfile::tempdir().unwrap();
    let expected = root.path().join("expected.png");
    let output = root.path().join("output.png");
    let settings = strehl_edit::ExportSettings {
        format: strehl_edit::ExportFormat::Png,
        hdr: false,
        color_space: strehl_edit::OutputColorSpace::Srgb,
        ..Default::default()
    };
    job.export(&expected, &settings, &AtomicBool::new(false))
        .unwrap();
    state.recipe.global.exposure = -2.;
    state.loaded.as_mut().unwrap().image = Arc::new((**job.image(false)).clone());
    state
        .export_job(output.clone(), settings.clone(), job.clone())
        .unwrap();
    state
        .exporting
        .take()
        .unwrap()
        .receiver
        .recv_timeout(Duration::from_secs(8))
        .unwrap()
        .unwrap();
    assert_eq!(
        std::fs::read(expected).unwrap(),
        std::fs::read(output).unwrap()
    );
    let cancelled = root.path().join("cancelled.png");
    assert!(
        job.export(&cancelled, &settings, &AtomicBool::new(true))
            .is_err()
    );
    assert!(!cancelled.exists());
}

/// Split view: the "before" half develops its own native tiles for the part
/// left of the line, as the "after" does, instead of magnifying a 1600 px
/// overview; they are freed when Split is left.
#[test]
fn split_before_half_shows_native_tiles_left_of_the_line() {
    let image = Arc::new(LinearImage {
        width: 2400,
        height: 1600,
        pixels: (0..2400u32 * 1600)
            .flat_map(|i| {
                let v = 0.05 + ((i * 37) % 23) as f32 / 30.0;
                [v, 0.3, 0.9 - 0.5 * v]
            })
            .collect(),
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    let mut state = EditorState {
        path: Some("split.tiff".into()),
        loaded: Some(LoadedPhoto {
            coverage: None,
            preview: Arc::new(image.preview(400)),
            image,
            recipe: Default::default(),
            source: "split.tiff".into(),
            warnings: vec![],
        }),
        ..Default::default()
    };
    state.develop.compare = crate::develop_station::Compare::Split;
    state.develop.split = 0.5;
    let ctx = egui::Context::default();
    // 100 %: a 1000 x 600 canvas over the photograph's middle.
    let canvas = egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(1000.0, 600.0));
    let full = egui::Rect::from_min_size(egui::pos2(-700.0, -500.0), egui::vec2(2400.0, 1600.0));
    let until = Instant::now() + Duration::from_secs(60);
    let settled = |state: &EditorState| {
        state.before_overview.is_some()
            && state.before_view.settled()
            && state.before_view.stats()["published"]["stride"] == 1
    };
    while !settled(&state) {
        assert!(Instant::now() < until, "{}", state.before_view.stats());
        let _ = ctx.run(Default::default(), |ctx| {
            state.poll(ctx, 4096);
            state.request_view(ctx, (full, canvas), 4096);
        });
        std::thread::sleep(Duration::from_millis(2));
    }
    let stats = state.before_view.stats();
    // Only the left half of the view: x from 700 to 1200 source pixels.
    let uv = &stats["requested"]["uv"];
    assert!(
        (uv[0][0].as_f64().unwrap() - 700.0 / 2400.0).abs() < 1e-3,
        "{stats}"
    );
    assert!(
        (uv[1][0].as_f64().unwrap() - 1200.0 / 2400.0).abs() < 2e-3,
        "{stats}"
    );
    assert_eq!(stats["hdr_pixels"], false, "no presenter: SDR");
    // The paint holds those native tiles, and the split view gets them.
    let paint = state.before_paint().expect("before paint");
    let _ = ctx.run(Default::default(), |ctx| {
        let painter = ctx.layer_painter(egui::LayerId::background());
        let left = egui::Rect::from_min_max(canvas.min, egui::pos2(500.0, 600.0));
        let aperture = egui::Rect::from_min_max(
            egui::pos2(700.0 / 2400.0, 500.0 / 1600.0),
            egui::pos2(1200.0 / 2400.0, 1100.0 / 1600.0),
        );
        let shapes = paint.paint_shapes(&painter, left, aperture);
        assert!(shapes.iter().any(|s| matches!(s, egui::Shape::Mesh(_))));
        // Taken back out of the layer: nothing painted twice.
        assert!(ctx.graphics(|g| g.get(painter.layer_id()).is_none_or(|l| {
            l.all_entries()
                .all(|c| matches!(c.shape, egui::Shape::Noop))
        })));
    });
    assert!(
        state.before_view.stats()["tiles_cached"].as_u64().unwrap() >= 1,
        "{}",
        state.before_view.stats()
    );
    // The main view's own detail is unaffected: "after" asks for the whole view.
    let after = state.viewport.stats();
    assert!((after["requested"]["uv"][1][0].as_f64().unwrap() - 1700.0 / 2400.0).abs() < 2e-3);
    // Leaving Split frees the "before" tiles.
    state.develop.compare = crate::develop_station::Compare::After;
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll(ctx, 4096);
        state.request_view(ctx, (full, canvas), 4096);
    });
    assert_eq!(state.before_view.stats()["tiles_cached"], 0);
    assert!(state.before_paint().is_none());
}
