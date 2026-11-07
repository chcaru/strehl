//! Independent consumer checks: different pixel content at reused identities,
//! stale failures, ownership release and export continuity across navigation.
use super::*;
use std::sync::atomic::AtomicBool;

fn photo(bright: bool) -> LoadedPhoto {
    let image = Arc::new(LinearImage {
        width: 83,
        height: 57,
        pixels: (0..83 * 57)
            .flat_map(|i| {
                if bright {
                    [0.7, 0.02 + (i % 83) as f32 / 400., 0.04]
                } else {
                    [0.03, 0.02 + (i / 83) as f32 / 300., 0.5]
                }
            })
            .collect(),
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    LoadedPhoto {
        coverage: None,
        preview: Arc::new(image.preview(17)),
        image,
        recipe: Default::default(),
        source: "unchanged-path.tiff".into(),
        warnings: vec![],
    }
}

fn state() -> EditorState {
    EditorState {
        loaded: Some(photo(false)),
        revision: 41,
        saved_revision: Some(41),
        ..Default::default()
    }
}

fn settle(state: &mut EditorState, ctx: &egui::Context) {
    let deadline = Instant::now() + Duration::from_secs(10);
    loop {
        state.poll(ctx, 4096);
        if state.developing.is_none()
            && state.painted_snapshot.is_some()
            && state.painted_snapshot == state.development.as_ref().map(|(_, _, job)| job.token())
        {
            return;
        }
        assert!(
            Instant::now() < deadline,
            "Current development did not settle"
        );
        std::thread::sleep(Duration::from_millis(2));
    }
}

#[test]
fn same_revision_replacement_publishes_new_pixels_not_just_new_geometry() {
    let ctx = egui::Context::default();
    let mut state = state();
    settle(&mut state, &ctx);
    let old_token = state.painted_snapshot;
    let _ = ctx.tex_manager().write().take_delta();
    let replacement = photo(true);
    let expected = replacement
        .preview
        .render_display_region_mode(
            &DevelopmentRecipe::default(),
            strehl_edit::DisplayRegionRequest {
                min: [0, 0],
                max: [replacement.preview.width, replacement.preview.height],
                stride: 1,
            },
            &AtomicBool::new(false),
            false,
        )
        .unwrap();
    let expected = egui::ColorImage::from_rgb(expected.size.map(|n| n as usize), &expected.rgb);
    state.loaded = Some(replacement);
    settle(&mut state, &ctx);
    assert_eq!(state.revision, 41);
    assert_ne!(old_token, state.painted_snapshot);
    let id = state.texture.as_ref().unwrap().id();
    let uploads = ctx.tex_manager().write().take_delta();
    let pixels = uploads.set.iter().find(|(key, _)| *key == id).unwrap();
    let egui::ImageData::Color(actual) = &pixels.1.image;
    assert_eq!(actual.as_ref(), &expected);
    assert!(expected.pixels.iter().any(|p| p.r() > p.b() + 40));
}

#[test]
fn stale_failure_cannot_replace_current_feedback_or_prevent_new_preview() {
    let ctx = egui::Context::default();
    let mut state = state();
    let previous = state.development_job(false).unwrap();
    let (release, wait) = std::sync::mpsc::channel();
    state.developing = Some(spawn_task("independent-stale-failure", move |_| {
        wait.recv().unwrap();
        anyhow::bail!("error belonging to previous photograph")
    }));
    state.developing_revision = Some(41);
    state.developing_snapshot = Some(previous.token());
    state.loaded = Some(photo(true));
    state.error = Some("current unrelated feedback".into());
    state.poll(&ctx, 4096);
    assert!(state.developing.as_ref().unwrap().is_cancelled());
    release.send(()).unwrap();
    settle(&mut state, &ctx);
    assert_eq!(state.error.as_deref(), Some("current unrelated feedback"));
    assert_ne!(state.painted_snapshot, Some(previous.token()));
    assert!(state.texture.is_some());
}

#[test]
fn document_reset_releases_cached_full_resolution_source() {
    let mut state = state();
    let weak = Arc::downgrade(&state.loaded.as_ref().unwrap().image);
    let job = state.development_job(false).unwrap();
    drop(job);
    assert!(weak.upgrade().is_some());
    state.reset_document();
    assert!(state.development.is_none());
    assert!(
        weak.upgrade().is_none(),
        "Old source retained by idle snapshot cache"
    );
}

#[test]
fn before_view_and_document_navigation_do_not_change_an_accepted_export() {
    let mut state = state();
    state.recipe.global.exposure = -0.75;
    state.before = true;
    let before = state.development_job(true).unwrap();
    let accepted = state.freeze_export_job().unwrap();
    assert_ne!(before.token(), accepted.token());
    assert_eq!(accepted.recipe().global.exposure, -0.75);
    let root = tempfile::tempdir().unwrap();
    let settings = strehl_edit::ExportSettings {
        format: strehl_edit::ExportFormat::Png,
        hdr: false,
        color_space: strehl_edit::OutputColorSpace::Srgb,
        ..Default::default()
    };
    let expected = root.path().join("expected.png");
    let output = root.path().join("continued.png");
    strehl_edit::export_image(
        &expected,
        accepted.image(false),
        accepted.recipe(),
        &settings,
        &AtomicBool::new(false),
    )
    .unwrap();
    state
        .export_job(output.clone(), settings, accepted)
        .unwrap();
    state.reset_document();
    state.loaded = Some(photo(true));
    state.recipe.global.exposure = 1.5;
    state
        .exporting
        .take()
        .unwrap()
        .receiver
        .recv_timeout(Duration::from_secs(10))
        .unwrap()
        .unwrap();
    assert_eq!(
        std::fs::read(output).unwrap(),
        std::fs::read(expected).unwrap()
    );
}
