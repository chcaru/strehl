use super::*;
use std::sync::atomic::AtomicBool;
use strehl_edit::{DevelopmentRecipe, ImageOrigin};

fn image(width: u32, height: u32, pixel: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
    let pixel = &pixel;
    LinearImage {
        width,
        height,
        pixels: (0..height)
            .flat_map(|y| (0..width).flat_map(move |x| pixel(x, y)))
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

fn source() -> Arc<LinearImage> {
    Arc::new(image(512, 384, |_, _| [0.3; 3]))
}

fn patterned(width: u32, height: u32) -> LinearImage {
    image(width, height, |x, y| {
        [
            0.02 + (x % 151) as f32 / 150.0,
            0.03 + (y % 101) as f32 / 100.0,
            0.04 + ((x * 11 + y * 7) % 37) as f32 / 60.0,
        ]
    })
}

fn identity(revision: u64) -> Identity {
    Identity {
        snapshot: None,
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

/// As if the zoom and the recipe had both rested.
fn rest(state: &mut ViewportRefinement, id: Identity) {
    state.since = Some(Instant::now() - SETTLE);
    state.seen = Some((id, Instant::now() - SETTLE));
}

fn poll_until(
    ctx: &egui::Context,
    state: &mut ViewportRefinement,
    job: &DevelopmentJob,
    id: Identity,
    done: impl Fn(&ViewportRefinement) -> bool,
) {
    let until = Instant::now() + Duration::from_secs(60);
    while !done(state) {
        assert!(Instant::now() < until, "{}", state.stats());
        let _ = ctx.run(Default::default(), |ctx| {
            state.poll_job(ctx, Some(job.clone()), id);
        });
        std::thread::sleep(Duration::from_millis(2));
    }
}

/// Nothing queued, nothing to upload, and the view's detail complete.
fn idle(state: &ViewportRefinement) -> bool {
    state.outstanding.is_empty() && state.staged.is_empty() && state.settled()
}

fn whole(size: [u32; 2]) -> (Rect, Rect) {
    let rect = Rect::from_min_size(Pos2::ZERO, egui::vec2(size[0] as f32, size[1] as f32));
    (rect, rect)
}

#[test]
fn planner_reaches_native_on_a_4k_canvas_where_one_bounded_patch_stopped_at_half() {
    // The owner's canvas: a 4K display with the inspector and tools beside it.
    let physical = [3290, 1750];
    let weevil = [7032, 4688];
    let full = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    // Fitted by height, the view needs about 2.7 source pixels per screen pixel.
    assert_eq!(target_stride(weevil, full, physical), Some(2));
    // At 100 % the screen shows 3290 x 1750 source pixels: every one of them.
    // The single 3072-px patch this replaces had to double its stride here.
    let actual = Rect::from_min_size(
        egui::pos2(0.2, 0.2),
        egui::vec2(3290.0 / 7032.0, 1750.0 / 4688.0),
    );
    assert_eq!(target_stride(weevil, actual, physical), Some(1));
    let four_shot = [14064, 9376];
    assert_eq!(target_stride(four_shot, full, physical), Some(4));
    // From fit to 800 %: never fewer texels than screen pixels, and below
    // native never more than twice as many (one level of the pyramid).
    for source in [weevil, four_shot] {
        let fit =
            (physical[0] as f32 / source[0] as f32).min(physical[1] as f32 / source[1] as f32);
        for step in 0..400 {
            // Screen pixels per source pixel.
            let scale = fit * 1.02f32.powi(step);
            if scale > 8.0 {
                break;
            }
            let size = [0, 1].map(|i| (physical[i] as f32 / (source[i] as f32 * scale)).min(1.0));
            let aperture =
                Rect::from_center_size(egui::pos2(0.5, 0.5), egui::vec2(size[0], size[1]));
            let shown = [0, 1].map(|i| (size[i] * source[i] as f32 * scale).round());
            let stride = target_stride(source, aperture, physical).unwrap();
            let per_pixel = (size[0] * source[0] as f32 / stride as f32 / shown[0])
                .min(size[1] * source[1] as f32 / stride as f32 / shown[1]);
            assert!(
                per_pixel >= 0.985 || stride == 1,
                "{source:?} at {scale}: {per_pixel} texels per pixel"
            );
            assert!(
                stride == 1 || per_pixel < 2.0 + 1e-3,
                "{source:?} at {scale}: {per_pixel}"
            );
        }
    }
    // An 8K canvas at nearly 2x oversampling is bounded, one level coarser.
    let big = [16384, 12288];
    let aperture = Rect::from_min_size(Pos2::ZERO, egui::vec2(0.9, 0.67));
    let stride = target_stride(big, aperture, [7680, 4320]).unwrap();
    let texels = aperture.width() * big[0] as f32 * aperture.height() * big[1] as f32
        / (stride * stride) as f32;
    assert!(
        texels <= MAX_VIEW_TEXELS && stride == 2,
        "{stride} {texels}"
    );
    assert_eq!(target_stride([0, 10], full, physical), None);
}

#[test]
fn tile_bins_share_one_global_grid_and_aprons_equal_the_neighbouring_core() {
    let source = patterned(300, 200);
    let size = [300, 200];
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = -0.35;
    for stride in [1, 4] {
        let whole = source
            .render_display_region(
                &recipe,
                DisplayRegionRequest {
                    min: [0, 0],
                    max: size,
                    stride,
                },
                &AtomicBool::new(false),
            )
            .unwrap();
        let side = 64 / stride.min(2);
        for (a, b) in [((0, 0), (1, 0)), ((0, 0), (0, 1)), ((1, 1), (2, 1))] {
            let key = |(x, y)| TileKey { stride, side, x, y };
            let (ka, kb) = (key(a), key(b));
            for k in [ka, kb] {
                let request = k.request(size);
                let tile = source
                    .render_display_region(&recipe, request, &AtomicBool::new(false))
                    .unwrap();
                // Every texel, apron included, is the global grid's texel.
                let mut compared = 0;
                for ty in 0..tile.size[1] {
                    for tx in 0..tile.size[0] {
                        let gx = (request.min[0] / stride + tx) as usize;
                        let gy = (request.min[1] / stride + ty) as usize;
                        let t = (ty * tile.size[0] + tx) as usize * 3;
                        let g = (gy * whole.size[0] as usize + gx) * 3;
                        assert_eq!(
                            tile.rgb[t..t + 3],
                            whole.rgb[g..g + 3],
                            "stride {stride} tile {k:?}"
                        );
                        compared += 1;
                    }
                }
                assert!(compared > 64);
            }
            // The shared edge: a's apron is b's first core texel row/column.
            let (ca, cb) = (ka.core(size), kb.core(size));
            assert!(ca[2] == cb[0] || ca[3] == cb[1], "{ca:?} {cb:?}");
            let ra = ka.request(size);
            assert!(ra.max[0] == ca[2] + stride || ra.max[1] == ca[3] + stride);
        }
    }
    // A shifted correspondence must fail: the comparison can detect an error.
    let tile = source
        .render_display_region(
            &recipe,
            TileKey {
                stride: 1,
                side: 64,
                x: 1,
                y: 1,
            }
            .request(size),
            &AtomicBool::new(false),
        )
        .unwrap();
    let whole = source
        .render_display_region(
            &recipe,
            DisplayRegionRequest {
                min: [0, 0],
                max: size,
                stride: 1,
            },
            &AtomicBool::new(false),
        )
        .unwrap();
    let shifted = (64 * 300 + 64) * 3;
    assert_ne!(tile.rgb[..3], whole.rgb[shifted..shifted + 3]);
}

#[test]
fn detail_tile_pixels_equal_the_full_resolution_development_and_the_export() {
    use strehl_edit::{
        Backdrop, BackdropKey, ExportFormat, ExportSettings, Heal, OutputColorSpace,
        RegionAdjustment, RegionShape,
    };
    let source = patterned(300, 220);
    let size = [300, 220];
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = 0.4;
    recipe.global.contrast = 18.0;
    recipe.global.shadows = 12.0;
    recipe.regions.push(RegionAdjustment {
        id: "edge".into(),
        name: "Edge".into(),
        note: String::new(),
        shape: RegionShape::Ellipse {
            center: [0.42, 0.55],
            radius: [0.2, 0.15],
        },
        feather: 0.4,
        enabled: true,
        source_range: None,
        adjustments: strehl_edit::Adjustments {
            exposure: -0.8,
            ..Default::default()
        },
    });
    // A heal and a backdrop whose neighbourhoods cross the tile's edges.
    recipe.heals.push(Heal {
        center: [64.0 / 300.0, 64.0 / 220.0],
        radius: [0.04, 0.05],
        source_offset: [0.1, 0.02],
        enabled: true,
    });
    recipe.backdrop = Some(Backdrop {
        threshold: 0.08,
        softness: 1.0,
        key: BackdropKey::Dark,
        enabled: true,
    });
    recipe.validate().unwrap();
    let developed = source.render_sdr8(&recipe).unwrap();
    let directory = tempfile::tempdir().unwrap();
    let png = directory.path().join("export.png");
    strehl_edit::export_image(
        &png,
        &source,
        &recipe,
        &ExportSettings {
            format: ExportFormat::Png,
            color_space: OutputColorSpace::Srgb,
            hdr: false,
            ..Default::default()
        },
        &AtomicBool::new(false),
    )
    .unwrap();
    let exported = image::open(&png).unwrap().to_rgb16();
    assert_eq!(exported.dimensions(), (300, 220));
    let check = |recipe: &DevelopmentRecipe| -> Result<usize, String> {
        let mut compared = 0;
        // Tiles inside, at the corner and on the photograph's edge.
        for (x, y) in [(1, 1), (0, 0), (4, 3)] {
            let key = TileKey {
                stride: 1,
                side: 64,
                x,
                y,
            };
            let request = key.request(size);
            let tile = prepare_covered(
                &source,
                recipe,
                request,
                &AtomicBool::new(false),
                None,
                (true, true, true),
                None,
            )
            .unwrap();
            let sdr = tile.sdr.unwrap();
            let [x0, y0, x1, y1] = key.core(size);
            for sy in y0..y1 {
                for sx in x0..x1 {
                    let t = ((sy - request.min[1]) * tile.size[0] + sx - request.min[0]) as usize;
                    let p = sdr.pixels[t];
                    let d = ((sy * 300 + sx) * 3) as usize;
                    if [p.r(), p.g(), p.b()] != developed[d..d + 3] {
                        return Err(format!("({sx}, {sy}) differs from render_sdr8"));
                    }
                    let e = exported.get_pixel(sx, sy).0;
                    for c in 0..3 {
                        let coded = f32::from(e[c]) / 65535.0 * 255.0;
                        if (coded - f32::from(developed[d + c])).abs() > 0.5 + 255.0 / 65535.0 {
                            return Err(format!("({sx}, {sy}) differs from the export"));
                        }
                    }
                    compared += 1;
                }
            }
        }
        Ok(compared)
    };
    let compared = check(&recipe).unwrap();
    assert_eq!(compared, 64 * 64 * 2 + (300 - 256) * (220 - 192));
    // Negative control: a slightly different recipe must be caught.
    let mut other = recipe.clone();
    other.global.exposure += 0.05;
    assert!(
        check(&other).is_err(),
        "The comparison must be able to fail"
    );
}

#[test]
fn stale_results_never_cross_a_snapshot_reload_or_a_document_reset() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(2048, 1536));
    let old = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let next = DevelopmentJob::native(Arc::new((*source).clone()), DevelopmentRecipe::default());
    let old_id = Identity {
        snapshot: Some(old.token()),
        ..identity(1)
    };
    let next_id = Identity {
        snapshot: Some(next.token()),
        ..identity(1)
    };
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    state.identity = Some(old_id);
    state.demand([2048, 1536], whole([2048, 1536]), 1.0, 4096);
    rest(&mut state, old_id);
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(old.clone()), old_id);
    });
    assert!(
        !state.outstanding.is_empty(),
        "The fixture must start real work"
    );
    // The same revision reopened with another snapshot: nothing old may publish.
    let until = Instant::now() + Duration::from_secs(60);
    loop {
        let _ = ctx.run(Default::default(), |ctx| {
            state.poll_job(ctx, Some(next.clone()), next_id);
        });
        if state.outstanding.is_empty() && state.posted.is_none() {
            break;
        }
        assert!(Instant::now() < until);
        std::thread::sleep(Duration::from_millis(2));
    }
    std::thread::sleep(Duration::from_millis(200));
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(next.clone()), next_id);
    });
    assert!(state.tiles.is_empty() && state.staged.is_empty());
    assert!(state.cancellations > 0);
    assert_eq!(
        state.identity,
        Some(old_id),
        "Retain the last complete view until the new overview is ready"
    );
    // A document reset while work runs; the new document repeats the identity.
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    state.reset();
    initialize(&ctx, &mut state, &source, 1);
    state.demand([2048, 1536], whole([2048, 1536]), 1.0, 4096);
    rest(&mut state, identity(1));
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert!(!state.outstanding.is_empty());
    let epoch = state.epoch;
    state.reset();
    initialize(&ctx, &mut state, &source, 1);
    assert!(state.epoch > epoch);
    std::thread::sleep(Duration::from_millis(300));
    let _ = ctx.run(Default::default(), |ctx| {
        // No demand yet: only results from before the reset can arrive.
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert!(
        state.tiles.is_empty() && state.staged.is_empty(),
        "Old pixels never cross a document reset"
    );
}

#[test]
fn publication_replaces_the_overview_and_its_tiles_as_one_recipe_generation() {
    let ctx = egui::Context::default();
    let source = source();
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 2);
    state.demand([512, 384], whole([512, 384]), 1.0, 4096);
    rest(&mut state, identity(2));
    poll_until(&ctx, &mut state, &job, identity(2), |s| {
        s.paint.as_ref().is_some_and(|p| !p.tiles.is_empty())
    });
    let retained = state.paint().unwrap();
    initialize(&ctx, &mut state, &source, 3);
    assert!(
        !retained.tiles.is_empty(),
        "An already-recorded paint keeps its immutable old generation"
    );
    assert!(
        state.paint.as_ref().unwrap().tiles.is_empty() && state.tiles.is_empty(),
        "The new overview cannot retain an old-recipe tile"
    );
    assert_eq!(state.identity, Some(identity(3)));
}

fn tile_paint(ctx: &egui::Context, stride: u32, core: Rect, color: Color32) -> TilePaint {
    TilePaint {
        stride,
        core,
        uv: core,
        size: [8, 6],
        texture: Some(ctx.load_texture(
            format!("tile-{stride}-{:?}", core.min),
            egui::ColorImage::filled([8, 6], color),
            egui::TextureOptions::LINEAR,
        )),
        layer: None,
        published: Instant::now() - REVEAL - Duration::from_secs(1),
    }
}

fn painted_textures(
    ctx: &egui::Context,
    paint: &PhotoPaint,
    aperture: Rect,
) -> Vec<egui::TextureId> {
    let output = ctx.run(Default::default(), |ctx| {
        egui::CentralPanel::default()
            .show(ctx, |ui| paint.paint(ui.painter(), ui.max_rect(), aperture));
    });
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) => Some(mesh.texture_id),
            _ => None,
        })
        .collect()
}

#[test]
fn only_opaque_tiles_covering_the_aperture_elide_the_overview() {
    let ctx = egui::Context::default();
    let overview = ctx.load_texture(
        "overview",
        egui::ColorImage::filled([4, 3], Color32::DARK_GRAY),
        egui::TextureOptions::LINEAR,
    );
    let left = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.5, 1.0));
    let right = Rect::from_min_max(egui::pos2(0.5, 0.0), egui::pos2(1.0, 1.0));
    let coarse = tile_paint(
        &ctx,
        2,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        Color32::GRAY,
    );
    let a = tile_paint(&ctx, 1, left, Color32::WHITE);
    let b = tile_paint(&ctx, 1, right, Color32::WHITE);
    let ids = |t: &TilePaint| t.texture.as_ref().unwrap().id();
    let (overview_id, coarse_id, a_id, b_id) = (overview.id(), ids(&coarse), ids(&a), ids(&b));
    let paint = |tiles: Vec<TilePaint>| PhotoPaint {
        overview: overview.clone(),
        presenter: None,
        layer: None,
        tiles: Arc::new(tiles),
        hdr: false,
        progress: None,
        export: None,
    };
    let full = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    // Both fine tiles cover the view: they are the whole base.
    let both = painted_textures(
        &ctx,
        &paint(vec![coarse.clone(), a.clone(), b.clone()]),
        full,
    );
    assert!(both.contains(&a_id) && both.contains(&b_id));
    assert!(!both.contains(&overview_id) && !both.contains(&coarse_id));
    // One fine tile: the coarse level covers, so the overview is still elided.
    let one = painted_textures(&ctx, &paint(vec![coarse.clone(), a.clone()]), full);
    assert!(one.contains(&coarse_id) && one.contains(&a_id) && !one.contains(&overview_id));
    // Only part covered and nothing coarser: the overview stays beneath.
    let partial = painted_textures(&ctx, &paint(vec![a.clone()]), full);
    assert!(partial.contains(&overview_id) && partial.contains(&a_id));
    // A view inside one tile needs only that tile.
    let inside = painted_textures(
        &ctx,
        &paint(vec![coarse.clone(), a.clone(), b.clone()]),
        left.shrink(0.05),
    );
    assert_eq!(inside, vec![a_id]);
    // A fading tile does not count as covering.
    let mut fading = b.clone();
    fading.published = Instant::now();
    let faded = painted_textures(&ctx, &paint(vec![a.clone(), fading]), full);
    assert!(faded.contains(&overview_id));
}

#[test]
fn tile_reveal_uses_a_future_deadline_and_settled_pixels_stop_waking() {
    let ctx = egui::Context::default();
    let overview = ctx.load_texture(
        "paced-overview",
        egui::ColorImage::filled([8, 6], Color32::DARK_GRAY),
        egui::TextureOptions::LINEAR,
    );
    let full = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    let mut tile = tile_paint(&ctx, 1, full, Color32::WHITE);
    let detail_id = tile.texture.as_ref().unwrap().id();
    let frame = |tile: &TilePaint, time| {
        let paint = PhotoPaint {
            overview: overview.clone(),
            presenter: None,
            layer: None,
            tiles: Arc::new(vec![tile.clone()]),
            hdr: false,
            progress: None,
            export: None,
        };
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(320.0, 240.0))),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| paint.paint(ui.painter(), ui.max_rect(), full));
            },
        )
    };
    for i in 0..4 {
        frame(&tile, i as f64);
    }
    tile.published = Instant::now() - Duration::from_millis(60);
    let active = frame(&tile, 4.0);
    let delay = active.viewport_output[&egui::ViewportId::ROOT].repaint_delay;
    assert!(
        delay > Duration::ZERO && delay <= Duration::from_millis(16),
        "Reveal must be paced: {delay:?}"
    );
    let colors = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == detail_id => Some(mesh),
                _ => None,
            })
            .flat_map(|mesh| mesh.vertices.iter().map(|vertex| vertex.color))
            .collect::<Vec<_>>()
    };
    let fading = colors(&active);
    assert!(
        !fading.is_empty() && fading.iter().all(|c| c.a() > 0 && c.a() < 255),
        "The fixture must paint an actual intermediate fade"
    );
    tile.published = Instant::now() - REVEAL - Duration::from_secs(1);
    frame(&tile, 5.0);
    let settled = frame(&tile, 6.0);
    assert_eq!(
        settled.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
        Duration::MAX,
        "A settled photograph must not animate"
    );
    let opaque = colors(&settled);
    assert!(!opaque.is_empty() && opaque.iter().all(|c| *c == Color32::WHITE));
}

#[test]
fn settling_has_a_future_deadline_and_pending_work_waits_for_the_worker() {
    for predicted_dt in [1.0 / 240.0, 1.0 / 60.0, 1.0 / 24.0] {
        let ctx = egui::Context::default();
        // Large enough that the first tile is still developing when checked.
        let source = Arc::new(patterned(4096, 3072));
        let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
        let mut state = ViewportRefinement::default();
        initialize(&ctx, &mut state, &source, 1);
        for i in 0..4 {
            let _ = ctx.run(
                egui::RawInput {
                    time: Some(i as f64),
                    predicted_dt,
                    ..Default::default()
                },
                |_| {},
            );
        }
        let poll = |state: &mut ViewportRefinement, time| {
            ctx.run(
                egui::RawInput {
                    time: Some(time),
                    predicted_dt,
                    ..Default::default()
                },
                |ctx| state.poll_job(ctx, Some(job.clone()), identity(1)),
            )
        };
        state.demand([4096, 3072], whole([4096, 3072]), 1.0, 4096);
        let settling = poll(&mut state, 4.0);
        let delay = settling.viewport_output[&egui::ViewportId::ROOT].repaint_delay;
        assert!(
            delay > Duration::ZERO && delay <= SETTLE,
            "Settling spun at {predicted_dt}s: {delay:?}"
        );
        assert!(
            state.outstanding.is_empty(),
            "Settling must not start work early"
        );
        rest(&mut state, identity(1));
        let pending = poll(&mut state, 5.0);
        assert!(!state.outstanding.is_empty());
        assert_eq!(
            pending.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
            Duration::MAX,
            "Pending work scheduled polling at {predicted_dt}s"
        );
        state.reset();
    }
}

#[test]
fn tile_completion_wakes_a_sleeping_viewport_without_waiting_for_polling() {
    let ctx = egui::Context::default();
    let source = source();
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    for _ in 0..4 {
        let _ = ctx.run(Default::default(), |_| {});
    }
    let (wake, received) = mpsc::channel();
    ctx.set_request_repaint_callback(move |info| {
        let _ = wake.send(info.delay);
    });
    state.demand([512, 384], whole([512, 384]), 1.0, 4096);
    rest(&mut state, identity(1));
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert!(!state.outstanding.is_empty());
    let delay = received
        .recv_timeout(Duration::from_secs(30))
        .expect("The completed worker never woke the viewport");
    assert!(
        delay > Duration::ZERO && delay <= Duration::from_millis(1),
        "Completion must request one prompt future frame: {delay:?}"
    );
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert!(state.outstanding.is_empty(), "{}", state.stats());
    // Without a presenter the pixels become an egui texture on this thread.
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    let paint = state.paint().unwrap();
    assert_eq!(paint.tiles.len(), 1);
    assert!(paint.tiles[0].texture.is_some());
    assert_eq!(paint.tiles[0].stride, 1);
}

#[test]
fn failed_and_panicking_tiles_retire_without_retrying_or_polling_forever() {
    let ctx = egui::Context::default();
    let source = source();
    // A coverage mask shorter than its stated size panics inside the worker.
    let broken = crate::photo_coverage::Coverage {
        size: [512, 384],
        values: Arc::from(vec![255u8; 16]),
    };
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default())
        .with_coverage(Some(Arc::new(broken)));
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    for _ in 0..4 {
        let _ = ctx.run(Default::default(), |_| {});
    }
    state.demand([512, 384], whole([512, 384]), 1.0, 4096);
    rest(&mut state, identity(1));
    poll_until(&ctx, &mut state, &job, identity(1), idle);
    assert_eq!(state.failed.len(), 1);
    assert!(
        state
            .last_error
            .as_ref()
            .unwrap()
            .contains("stopped before publishing")
    );
    let output = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert_eq!(
        state.jobs, 0,
        "A panic must not start an automatic crash loop"
    );
    assert!(state.outstanding.is_empty() && state.settled());
    assert_eq!(
        output.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
        Duration::MAX
    );
    // The worker survived: a sound job still gets its tile.
    let sound = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    initialize(&ctx, &mut state, &source, 2);
    rest(&mut state, identity(2));
    poll_until(&ctx, &mut state, &sound, identity(2), |s| {
        s.tiles.len() == 1
    });
}

#[test]
fn a_pan_shows_prefetched_tiles_at_once_and_develops_only_new_ones() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(1024, 768));
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    // 128-texel tiles at 100 %: a 300 x 200 view of a 1024 x 768 photograph.
    let full = Rect::from_min_size(Pos2::ZERO, egui::vec2(1024.0, 768.0));
    let view = Rect::from_min_size(egui::pos2(300.0, 260.0), egui::vec2(300.0, 200.0));
    state.demand([1024, 768], (full, view), 1.0, 130);
    assert_eq!(state.desired.unwrap().stride, 1);
    rest(&mut state, identity(1));
    poll_until(&ctx, &mut state, &job, identity(1), idle);
    let demand = state.desired.unwrap();
    assert!(demand.keys(demand.visible).count() >= 6);
    assert!(
        demand
            .keys(demand.ring())
            .all(|k| state.tiles.contains_key(&k))
    );
    let jobs = state.jobs;
    // Pan by 100 px: every newly visible tile was prefetched.
    state.demand(
        [1024, 768],
        (full, view.translate(egui::vec2(100.0, 0.0))),
        1.0,
        130,
    );
    let moved = state.desired.unwrap();
    assert_ne!(moved.visible, demand.visible);
    assert!(state.missing(moved.keys(moved.visible)).is_empty());
    assert!(state.reuses > 0);
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    // Only the new ring is developed; nothing already cached is redone.
    poll_until(&ctx, &mut state, &job, identity(1), |s| {
        s.outstanding.is_empty() && s.staged.is_empty()
    });
    let new_ring = moved
        .keys(moved.ring())
        .filter(|k| !demand.keys(demand.ring()).any(|old| old == *k))
        .count() as u64;
    assert_eq!(state.jobs - jobs, new_ring);
}

#[test]
fn eviction_bounds_retained_tiles_and_never_drops_the_view() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(1024, 768));
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let mut state = ViewportRefinement {
        budget: Some(4 * 130 * 130 * 8),
        ..Default::default()
    };
    initialize(&ctx, &mut state, &source, 1);
    let full = Rect::from_min_size(Pos2::ZERO, egui::vec2(1024.0, 768.0));
    let mut view = Rect::from_min_size(egui::pos2(0.0, 0.0), egui::vec2(260.0, 260.0));
    for _ in 0..4 {
        state.demand([1024, 768], (full, view), 1.0, 130);
        rest(&mut state, identity(1));
        let _ = ctx.run(Default::default(), |ctx| {
            state.poll_job(ctx, Some(job.clone()), identity(1));
        });
        poll_until(&ctx, &mut state, &job, identity(1), idle);
        let demand = state.desired.unwrap();
        assert!(
            demand
                .keys(demand.visible)
                .all(|k| state.tiles.contains_key(&k))
        );
        assert!(state.cached_bytes() <= state.view_bytes(&demand) + state.cache_budget());
        view = view.translate(egui::vec2(250.0, 160.0));
    }
    assert!(state.evictions > 0, "{}", state.stats());
}

#[test]
fn native_tiles_magnify_nearest_and_coarser_levels_filter_linearly() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(1024, 768));
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    let options = |state: &ViewportRefinement, stride: u32| {
        let tile = state.tiles.iter().find(|(k, _)| k.stride == stride)?.1;
        let id = tile.texture.as_ref()?.id();
        ctx.tex_manager().read().meta(id).map(|meta| meta.options)
    };
    // 100 %, then fitted to a quarter of the photograph's size.
    for (scale, stride) in [(1.0, 1), (0.25, 4)] {
        let full = Rect::from_min_size(Pos2::ZERO, egui::vec2(1024.0, 768.0) * scale);
        state.demand([1024, 768], (full, full), 1.0, 4096);
        rest(&mut state, identity(1));
        poll_until(&ctx, &mut state, &job, identity(1), |s| {
            s.tiles.keys().any(|k| k.stride == stride)
                && s.outstanding.is_empty()
                && s.staged.is_empty()
        });
        let got = options(&state, stride).unwrap();
        assert_eq!(got.minification, egui::TextureFilter::Linear);
        assert_eq!(
            got.magnification,
            if stride == 1 {
                egui::TextureFilter::Nearest
            } else {
                egui::TextureFilter::Linear
            }
        );
    }
}

#[test]
fn progress_mark_is_quiet_for_fast_detail_and_ruled_while_detail_is_pending() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(4096, 3072));
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    state.demand([4096, 3072], whole([4096, 3072]), 1.0, 4096);
    rest(&mut state, identity(1));
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert!(!state.outstanding.is_empty());
    assert_eq!(state.paint().unwrap().progress, None, "Quiet at first");
    state.wanting = Some(Instant::now() - QUIET);
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    let progress = state.paint().unwrap().progress;
    assert!(
        progress.is_some_and(|p| (0.0..1.0).contains(&p)),
        "{progress:?}"
    );
    let output = ctx.run(Default::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            state.paint().unwrap().paint(
                ui.painter(),
                ui.max_rect(),
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            )
        });
    });
    // Only straight one-pixel rules: no rounded shapes, no text.
    let lines = output
        .shapes
        .iter()
        .filter(
            |s| matches!(&s.shape, egui::Shape::LineSegment { stroke, .. } if stroke.width == 1.0),
        )
        .count();
    assert_eq!(lines, 2);
    state.reset();
}

fn web(long_edge: u32) -> ExportRequest {
    ExportRequest {
        settings: strehl_edit::ExportSettings {
            format: strehl_edit::ExportFormat::Jpeg,
            color_space: strehl_edit::OutputColorSpace::Srgb,
            hdr: false,
            quality: 90,
            resize: Some(strehl_edit::Resize {
                long_edge,
                filter: strehl_edit::ResizeFilter::Mitchell,
            }),
            ..Default::default()
        },
        um_per_px: None,
    }
}

#[test]
fn export_shows_the_presets_own_pixels_and_only_for_its_recipe_and_preset() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(600, 400));
    let job = DevelopmentJob::native(source.clone(), DevelopmentRecipe::default());
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    state.demand([600, 400], whole([600, 400]), 1.0, 4096);
    state.want_export(Some(web(300)));
    rest(&mut state, identity(1));
    poll_until(&ctx, &mut state, &job, identity(1), |s| {
        s.export
            .paint(identity(1))
            .is_some_and(|p| p.opacity() >= 1.0)
    });
    // The output's own size and pixels: 300 x 200, placed over the whole frame.
    let paint = state.paint().unwrap();
    let export = paint.export.as_ref().expect("Export paints the preset");
    assert!(export.covers(Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))));
    let texture = export.texture.as_ref().unwrap();
    assert_eq!(texture.size(), [300, 200]);
    let meta = ctx.tex_manager().read().meta(texture.id()).unwrap().options;
    assert_eq!(meta.magnification, egui::TextureFilter::Nearest);
    assert!((state.export_scale().unwrap() - 0.5).abs() < 1e-6);
    // Covered by the export, the view plans no development tiles (they
    // develop meanwhile, while the preview is built).
    state.cancel();
    state.tiles.clear();
    let jobs = state.jobs;
    for _ in 0..5 {
        let _ = ctx.run(Default::default(), |ctx| {
            state.poll_job(ctx, Some(job.clone()), identity(1));
        });
    }
    assert!(state.outstanding.is_empty() && state.posted.is_none());
    assert_eq!(state.jobs, jobs);
    assert!(state.settled());
    // Drawn as one quad of the output texture; the overview is not drawn.
    let output = ctx.run(Default::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            paint.paint(
                ui.painter(),
                ui.max_rect(),
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            )
        });
    });
    let textures = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) => Some(mesh.texture_id),
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(textures, vec![texture.id()]);
    // Another preset hides it at once and builds its own.
    state.want_export(Some(web(240)));
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert!(state.paint().unwrap().export.is_none());
    // Develop (no request) never shows an export.
    state.want_export(None);
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(job.clone()), identity(1));
    });
    assert!(state.paint().unwrap().export.is_none() && state.export_scale().is_none());
    // A preset without stages is the development itself: no preview.
    state.want_export(Some(ExportRequest {
        settings: strehl_edit::ExportSettings {
            resize: None,
            ..web(300).settings
        },
        um_per_px: None,
    }));
    state.export.wanted.as_mut().unwrap().1 = Instant::now() - SETTLE;
    poll_until(&ctx, &mut state, &job, identity(1), |s| {
        s.export.settled(identity(1))
    });
    assert!(state.paint().unwrap().export.is_none());
    assert!(
        state.stats()["export"]["outcome"]
            .as_str()
            .is_some_and(|o| o == "development")
    );
}

#[test]
fn a_new_recipe_hides_the_export_until_its_own_preview_is_ready() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(600, 400));
    let mut recipe = DevelopmentRecipe::default();
    let job = DevelopmentJob::native(source.clone(), recipe.clone());
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    state.demand([600, 400], whole([600, 400]), 1.0, 4096);
    state.want_export(Some(web(300)));
    rest(&mut state, identity(1));
    poll_until(&ctx, &mut state, &job, identity(1), |s| {
        s.export.paint(identity(1)).is_some()
    });
    recipe.global.exposure = 1.0;
    let next = DevelopmentJob::native(source.clone(), recipe);
    initialize(&ctx, &mut state, &source, 2);
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll_job(ctx, Some(next.clone()), identity(2));
    });
    assert!(
        state.paint().unwrap().export.is_none(),
        "An old recipe's export is never shown over a new overview"
    );
    rest(&mut state, identity(2));
    poll_until(&ctx, &mut state, &next, identity(2), |s| {
        s.export.paint(identity(2)).is_some()
    });
    assert_eq!(state.export.jobs, 2);
}

#[test]
fn a_straightened_crop_is_painted_turned_over_its_frame() {
    let ctx = egui::Context::default();
    let source = Arc::new(patterned(600, 400));
    let recipe = DevelopmentRecipe {
        crop: Some(strehl_edit::Crop {
            min: [0.2, 0.2],
            max: [0.8, 0.8],
            angle_deg: 5.0,
        }),
        ..Default::default()
    };
    let job = DevelopmentJob::native(source.clone(), recipe);
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    state.demand([600, 400], whole([600, 400]), 1.0, 4096);
    state.want_export(Some(web(200)));
    rest(&mut state, identity(1));
    poll_until(&ctx, &mut state, &job, identity(1), |s| {
        s.export.paint(identity(1)).is_some()
    });
    let export = state.export.paint(identity(1)).unwrap();
    assert!(export.turned);
    // The frame's top edge descends to the right for a positive angle.
    assert!(export.corners[1].y > export.corners[0].y);
    assert!(!export.covers(Rect::from_min_max(
        egui::pos2(0.45, 0.45),
        egui::pos2(0.55, 0.55)
    )));
    // A turned export never elides the development under its corners.
    let paint = state.paint().unwrap();
    let output = ctx.run(Default::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            paint.paint(
                ui.painter(),
                ui.max_rect(),
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            )
        });
    });
    let meshes = output
        .shapes
        .iter()
        .filter(|shape| matches!(&shape.shape, egui::Shape::Mesh(_)))
        .count();
    assert!(meshes >= 2);
}
