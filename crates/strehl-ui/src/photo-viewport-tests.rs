use super::*;
use std::sync::atomic::AtomicBool;
use strehl_edit::ImageOrigin;

fn source() -> Arc<LinearImage> {
    Arc::new(LinearImage {
        width: 512,
        height: 384,
        pixels: vec![0.3; 512 * 384 * 3],
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    })
}
fn identity(revision: u64) -> Identity {
    Identity {
        revision,
        before: false,
        hdr: false,
    }
}
fn initialize(
    ctx: &egui::Context,
    state: &mut ViewportRefinement,
    source: &LinearImage,
    revision: u64,
) {
    let image = source.preview(32);
    let prepared = prepare(
        &image,
        &DevelopmentRecipe::default(),
        DisplayRegionRequest {
            min: [0, 0],
            max: [image.width, image.height],
            stride: 1,
        },
        &AtomicBool::new(false),
        None,
        false,
        true,
    )
    .unwrap();
    let _ = state.publish_overview(ctx, identity(revision), prepared);
}
fn wait_patch(
    ctx: &egui::Context,
    state: &mut ViewportRefinement,
    source: &Arc<LinearImage>,
    revision: u64,
) {
    let until = Instant::now() + Duration::from_secs(5);
    while state.paint.as_ref().unwrap().detail.is_none() {
        assert!(Instant::now() < until, "{}", state.stats());
        state.poll(
            ctx,
            Some(source.clone()),
            &DevelopmentRecipe::default(),
            identity(revision),
        );
        std::thread::sleep(Duration::from_millis(2));
    }
}

#[test]
fn planner_bounds_work_and_reaches_native_detail_with_real_zoom() {
    let source = [7032, 4688];
    let fit = plan(
        source,
        Rect::from_min_max(Pos2::ZERO, Pos2::new(1.0, 1.0)),
        [1600, 1000],
        8192,
    )
    .unwrap();
    assert!(fit.stride >= 4);
    let aperture = Rect::from_min_max(Pos2::new(0.4, 0.3), Pos2::new(0.52, 0.48));
    let zoom = plan(source, aperture, [1400, 1200], 8192).unwrap();
    assert_eq!(
        zoom.stride, 1,
        "A source pixel visible on screen must not remain in a coarse preview"
    );
    assert!(covers(zoom, source, aperture, 1));
    for physical in [[100, 80], [800, 600], [8000, 6000], [16000, 12000]] {
        let p = plan(
            source,
            Rect::from_min_max(Pos2::ZERO, Pos2::new(1.0, 1.0)),
            physical,
            8192,
        )
        .unwrap();
        let size = [
            (p.max[0] - p.min[0]).div_ceil(p.stride),
            (p.max[1] - p.min[1]).div_ceil(p.stride),
        ];
        assert!(size.iter().all(|n| *n <= MAX_PATCH_SIDE));
        assert!(u64::from(size[0]) * u64::from(size[1]) <= MAX_PATCH_PIXELS);
    }
}

#[test]
fn overscan_is_registered_and_small_pans_reuse_the_published_patch() {
    let ctx = egui::Context::default();
    let source = source();
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    let full = Rect::from_min_size(Pos2::ZERO, egui::vec2(1024.0, 768.0));
    let visible = Rect::from_min_max(Pos2::new(350.0, 250.0), Pos2::new(600.0, 450.0));
    state.demand([512, 384], (full, visible), 1.0, 4096);
    state.since = Some(Instant::now() - SETTLE);
    wait_patch(&ctx, &mut state, &source, 1);
    let old_jobs = state.jobs;
    let old = state
        .paint
        .as_ref()
        .unwrap()
        .detail
        .as_ref()
        .unwrap()
        .request;
    state.demand(
        [512, 384],
        (full, visible.translate(egui::vec2(2.0, 1.0))),
        1.0,
        4096,
    );
    state.since = Some(Instant::now() - SETTLE);
    state.poll(
        &ctx,
        Some(source.clone()),
        &DevelopmentRecipe::default(),
        identity(1),
    );
    assert_eq!(state.jobs, old_jobs);
    assert!(state.pending.is_none());
    let patch = state.paint.as_ref().unwrap().detail.as_ref().unwrap();
    assert_eq!(patch.request, old);
    assert_eq!(patch.uv.min.x, old.min[0] as f32 / 512.0);
    assert_eq!(patch.uv.max.y, old.max[1] as f32 / 384.0);
}

#[test]
fn cancellation_retires_worker_lane_and_old_pixels_never_cross_a_document_reset() {
    let ctx = egui::Context::default();
    let source = source();
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    let full = Rect::from_min_size(Pos2::ZERO, egui::vec2(512.0, 384.0));
    state.demand([512, 384], (full, full), 1.0, 4096);
    state.since = Some(Instant::now() - SETTLE);
    state.poll(
        &ctx,
        Some(source.clone()),
        &DevelopmentRecipe::default(),
        identity(1),
    );
    assert!(
        state.pending.is_some(),
        "The fixture must start real asynchronous work"
    );
    state.reset();
    assert!(
        state.pending.is_some(),
        "Cancellation must retain its lane until work retires"
    );
    initialize(&ctx, &mut state, &source, 1); // A new document can reuse the revision number.
    let until = Instant::now() + Duration::from_secs(5);
    while state.pending.is_some() {
        assert!(Instant::now() < until);
        state.poll(
            &ctx,
            Some(source.clone()),
            &DevelopmentRecipe::default(),
            identity(1),
        );
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(state.paint.as_ref().unwrap().detail.is_none());
    assert!(state.cancellations > 0);
}

#[test]
fn publication_replaces_coarse_and_detail_as_one_recipe_generation() {
    let ctx = egui::Context::default();
    let source = source();
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 2);
    let full = Rect::from_min_size(Pos2::ZERO, egui::vec2(512.0, 384.0));
    state.demand([512, 384], (full, full), 1.0, 4096);
    state.since = Some(Instant::now() - SETTLE);
    wait_patch(&ctx, &mut state, &source, 2);
    let retained = state.paint().unwrap();
    initialize(&ctx, &mut state, &source, 3);
    assert!(
        retained.detail.is_some(),
        "An already-recorded paint keeps its immutable old generation"
    );
    assert!(
        state.paint.as_ref().unwrap().detail.is_none(),
        "The new overview cannot retain an old-recipe patch"
    );
    assert_eq!(state.identity, Some(identity(3)));
}
