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
