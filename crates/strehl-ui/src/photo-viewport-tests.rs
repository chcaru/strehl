use super::*;
use crate::jobs::spawn_task;
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

fn patterned_source() -> LinearImage {
    LinearImage {
        width: 97,
        height: 65,
        pixels: (0..65)
            .flat_map(|y| {
                (0..97).flat_map(move |x| {
                    [
                        0.02 + x as f32 / 150.0,
                        0.03 + y as f32 / 100.0,
                        0.04 + ((x * 11 + y * 7) % 37) as f32 / 60.0,
                    ]
                })
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

#[test]
fn overlapping_patch_lattices_preserve_actual_global_pixels() {
    let source = patterned_source();
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = -0.35;
    for (stride, first, next) in [
        (1, ([5, 7], [61, 47]), ([29, 15], [75, 55])),
        (4, ([0, 0], [64, 48]), ([32, 16], [96, 64])),
    ] {
        let request = |(min, max)| DisplayRegionRequest { min, max, stride };
        let a = source
            .render_display_region(&recipe, request(first), &AtomicBool::new(false))
            .unwrap();
        let b = source
            .render_display_region(&recipe, request(next), &AtomicBool::new(false))
            .unwrap();
        let index = |p: [u32; 2], min: [u32; 2], width: u32| {
            (((p[1] - min[1]) / stride) * width + (p[0] - min[0]) / stride) as usize
        };
        let mut compared = 0;
        let mut different_neighbor = false;
        for y in (next.0[1]..first.1[1]).step_by(stride as usize) {
            for x in (next.0[0]..first.1[0]).step_by(stride as usize) {
                let ia = index([x, y], first.0, a.size[0]);
                let ib = index([x, y], next.0, b.size[0]);
                assert_eq!(&a.rgb[ia * 3..ia * 3 + 3], &b.rgb[ib * 3..ib * 3 + 3]);
                assert_eq!(
                    &a.rgba_linear[ia * 4..ia * 4 + 4],
                    &b.rgba_linear[ib * 4..ib * 4 + 4]
                );
                different_neighbor |=
                    a.rgb[ia * 3..ia * 3 + 3] != b.rgb[(ib + 1) * 3..(ib + 1) * 3 + 3];
                compared += 1;
            }
        }
        assert!(
            compared > 32 && different_neighbor,
            "A shifted correspondence must fail"
        );
    }
}

fn publish_ready_patch(
    ctx: &egui::Context,
    state: &mut ViewportRefinement,
    request: DisplayRegionRequest,
    prepared: PreparedPhoto,
    aperture: Rect,
) -> egui::FullOutput {
    state.desired = Some(Demand {
        aperture,
        physical: [320, 240],
        source: [97, 65],
        request,
    });
    state.pending = Some(Pending {
        identity: state.identity.unwrap(),
        request,
        task: spawn_task("patch-publication-control", move |_| Ok(prepared)),
    });
    let until = Instant::now() + Duration::from_secs(5);
    loop {
        assert!(
            Instant::now() < until,
            "Publication never reached the actual UI path"
        );
        let output = ctx.run(Default::default(), |ctx| {
            state.poll(
                ctx,
                None,
                &DevelopmentRecipe::default(),
                state.identity.unwrap(),
            );
            egui::CentralPanel::default().show(ctx, |ui| {
                state
                    .paint
                    .as_ref()
                    .unwrap()
                    .paint(ui.painter(), ui.max_rect(), aperture);
            });
        });
        if state.pending.is_none() {
            return output;
        }
        std::thread::sleep(Duration::from_millis(1));
    }
}

#[test]
fn publication_keeps_small_pan_reveal_clocks_but_not_new_coverage_or_lod() {
    let source = patterned_source();
    let recipe = DevelopmentRecipe::default();
    let uv = |min: [u32; 2], max: [u32; 2]| {
        Rect::from_min_max(
            egui::pos2(min[0] as f32 / 97.0, min[1] as f32 / 65.0),
            egui::pos2(max[0] as f32 / 97.0, max[1] as f32 / 65.0),
        )
    };
    let old = DisplayRegionRequest {
        min: [0, 0],
        max: [64, 48],
        stride: 1,
    };
    for (name, previous, next, aperture, inherited, ongoing, new_recipe) in [
        (
            "already sharp",
            old,
            DisplayRegionRequest {
                min: [8, 0],
                max: [80, 48],
                stride: 1,
            },
            uv([16, 4], [68, 44]),
            true,
            false,
            false,
        ),
        (
            "ongoing reveal",
            old,
            DisplayRegionRequest {
                min: [8, 0],
                max: [80, 48],
                stride: 1,
            },
            uv([16, 4], [68, 44]),
            true,
            true,
            false,
        ),
        (
            "coarse aligned",
            DisplayRegionRequest { stride: 4, ..old },
            DisplayRegionRequest {
                min: [8, 0],
                max: [80, 48],
                stride: 4,
            },
            uv([16, 4], [68, 44]),
            true,
            false,
            false,
        ),
        (
            "one pixel overlap",
            old,
            DisplayRegionRequest {
                min: [63, 0],
                max: [97, 48],
                stride: 1,
            },
            uv([63, 4], [95, 44]),
            false,
            false,
            false,
        ),
        (
            "diagonal nonoverlap",
            old,
            DisplayRegionRequest {
                min: [68, 52],
                max: [97, 65],
                stride: 1,
            },
            uv([70, 54], [95, 64]),
            false,
            false,
            false,
        ),
        (
            "changed resolution",
            old,
            DisplayRegionRequest {
                min: [8, 0],
                max: [80, 48],
                stride: 2,
            },
            uv([16, 4], [68, 44]),
            false,
            false,
            false,
        ),
        (
            "partial coarse edge",
            DisplayRegionRequest {
                max: [65, 48],
                stride: 4,
                ..old
            },
            DisplayRegionRequest {
                min: [8, 0],
                max: [80, 48],
                stride: 4,
            },
            uv([16, 4], [68, 44]),
            false,
            false,
            false,
        ),
        (
            "new patch lacks visible coverage",
            old,
            DisplayRegionRequest {
                min: [8, 0],
                max: [60, 48],
                stride: 1,
            },
            uv([16, 4], [68, 44]),
            false,
            false,
            false,
        ),
        (
            "new recipe",
            old,
            DisplayRegionRequest {
                min: [8, 0],
                max: [80, 48],
                stride: 1,
            },
            uv([16, 4], [68, 44]),
            false,
            false,
            true,
        ),
    ] {
        let ctx = egui::Context::default();
        let mut state = ViewportRefinement::default();
        initialize(&ctx, &mut state, &source, 1);
        let prepared = |request| {
            prepare(
                &source,
                &recipe,
                request,
                &AtomicBool::new(false),
                None,
                false,
                true,
            )
            .unwrap()
        };
        publish_ready_patch(
            &ctx,
            &mut state,
            previous,
            prepared(previous),
            uv(previous.min, previous.max),
        );
        let next_pixels = prepared(next);
        if new_recipe {
            initialize(&ctx, &mut state, &source, 2);
        }
        for _ in 0..4 {
            let _ = ctx.run(Default::default(), |_| {});
        }
        let previous_clock = Instant::now()
            - if ongoing {
                Duration::from_millis(30)
            } else {
                REVEAL + Duration::from_secs(1)
            };
        if let Some(patch) = state.paint.as_mut().unwrap().detail.as_mut() {
            patch.published = previous_clock;
        }
        let started = Instant::now();
        let output = publish_ready_patch(&ctx, &mut state, next, next_pixels, aperture);
        let patch = state.paint.as_ref().unwrap().detail.as_ref().unwrap();
        assert_eq!(
            patch.request, next,
            "{name}: fixture must publish new pixels"
        );
        assert_eq!(state.reveal_reused, u64::from(inherited), "{name}");
        assert_eq!(state.reveal_restarted, 2 - u64::from(inherited), "{name}");
        if inherited {
            assert_eq!(patch.published, previous_clock, "{name}: reveal restarted");
            if !ongoing {
                let texture = patch.texture.as_ref().unwrap().id();
                let detail_vertices = output
                    .shapes
                    .iter()
                    .filter_map(|shape| match &shape.shape {
                        egui::Shape::Mesh(mesh) if mesh.texture_id == texture => {
                            Some(&mesh.vertices)
                        }
                        _ => None,
                    })
                    .flatten()
                    .collect::<Vec<_>>();
                assert!(!detail_vertices.is_empty());
                assert!(
                    detail_vertices.iter().all(|v| v.color == Color32::WHITE),
                    "{name}: resolved pixels softened"
                );
                assert_eq!(
                    output.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
                    Duration::MAX,
                    "{name}: publication added another frame"
                );
            }
        } else {
            assert!(
                patch.published >= started,
                "{name}: a new reveal was incorrectly skipped"
            );
        }
    }
}

#[test]
fn only_opaque_detail_covering_the_aperture_elides_the_overview() {
    let ctx = egui::Context::default();
    let mut state = ViewportRefinement::default();
    let source = patterned_source();
    initialize(&ctx, &mut state, &source, 1);
    let request = DisplayRegionRequest {
        min: [16, 8],
        max: [80, 56],
        stride: 1,
    };
    let prepared = prepare(
        &source,
        &DevelopmentRecipe::default(),
        request,
        &AtomicBool::new(false),
        None,
        false,
        true,
    )
    .unwrap();
    let patch_uv = Rect::from_min_max(Pos2::from(prepared.uv[0]), Pos2::from(prepared.uv[1]));
    publish_ready_patch(&ctx, &mut state, request, prepared, patch_uv);
    let mut paint = state.paint().unwrap();
    let overview = paint.overview.id();
    let detail = paint
        .detail
        .as_ref()
        .unwrap()
        .texture
        .as_ref()
        .unwrap()
        .id();
    for (aperture, fading, overview_visible) in [
        (patch_uv.shrink(0.03), false, false),
        (patch_uv.shrink(0.03), true, true),
        (
            Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            false,
            true,
        ),
    ] {
        paint.detail.as_mut().unwrap().published = Instant::now()
            - if fading {
                Duration::from_millis(30)
            } else {
                REVEAL + Duration::from_secs(1)
            };
        let output = ctx.run(Default::default(), |ctx| {
            egui::CentralPanel::default()
                .show(ctx, |ui| paint.paint(ui.painter(), ui.max_rect(), aperture));
        });
        let textures = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) => Some(mesh.texture_id),
                _ => None,
            })
            .collect::<Vec<_>>();
        assert!(
            textures.contains(&detail),
            "Fixture must actually draw detail"
        );
        assert_eq!(textures.contains(&overview), overview_visible);
    }
    paint.detail.as_mut().unwrap().texture = None;
    let output = ctx.run(Default::default(), |ctx| {
        egui::CentralPanel::default()
            .show(ctx, |ui| paint.paint(ui.painter(), ui.max_rect(), patch_uv));
    });
    assert!(
        output.shapes.iter().any(
            |shape| matches!(&shape.shape, egui::Shape::Mesh(mesh) if mesh.texture_id == overview)
        ),
        "Unavailable detail must retain its fallback"
    );
}

#[test]
fn detail_reveal_uses_a_future_deadline_and_settled_pixels_stop_waking() {
    let ctx = egui::Context::default();
    let texture = |name, color| {
        ctx.load_texture(
            name,
            egui::ColorImage::filled([8, 6], color),
            egui::TextureOptions::LINEAR,
        )
    };
    let overview = texture("paced-overview", Color32::DARK_GRAY);
    let detail = texture("paced-detail", Color32::WHITE);
    let detail_id = detail.id();
    let full = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    let mut paint = PhotoPaint {
        overview,
        presenter: None,
        layer: None,
        detail: Some(Patch {
            request: DisplayRegionRequest {
                min: [0, 0],
                max: [8, 6],
                stride: 1,
            },
            texture: Some(detail),
            size: [8, 6],
            layer: None,
            uv: full,
            published: Instant::now() - REVEAL,
        }),
        hdr: false,
    };
    let frame = |paint: &PhotoPaint, time| {
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(320.0, 240.0))),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        paint.paint(ui.painter(), ui.max_rect(), full);
                    });
            },
        )
    };
    // Drain startup, texture allocation and layout wakes first; only the
    // actual photograph's animation may schedule the measured repaint.
    for i in 0..4 {
        frame(&paint, i as f64);
    }
    paint.detail.as_mut().unwrap().published = Instant::now() - Duration::from_millis(60);
    let active = frame(&paint, 4.0);
    let delay = active.viewport_output[&egui::ViewportId::ROOT].repaint_delay;
    assert!(
        delay > Duration::ZERO && delay <= Duration::from_millis(16),
        "Reveal must be paced: {delay:?}"
    );
    let colors = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .filter_map(|shape| {
                if let egui::Shape::Mesh(mesh) = &shape.shape {
                    (mesh.texture_id == detail_id).then_some(mesh)
                } else {
                    None
                }
            })
            .flat_map(|mesh| mesh.vertices.iter().map(|vertex| vertex.color))
            .collect::<Vec<_>>()
    };
    let active_colors = colors(&active);
    assert!(
        !active_colors.is_empty()
            && active_colors
                .iter()
                .all(|color| color.a() > 0 && color.a() < 255),
        "The fixture must paint an actual intermediate fade"
    );
    paint.detail.as_mut().unwrap().published = Instant::now() - REVEAL - Duration::from_secs(1);
    frame(&paint, 5.0);
    let settled = frame(&paint, 6.0);
    assert_eq!(
        settled.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
        Duration::MAX,
        "A settled photograph must not animate"
    );
    let settled_colors = colors(&settled);
    assert!(
        !settled_colors.is_empty() && settled_colors.iter().all(|color| *color == Color32::WHITE),
        "The fade must finish at the exact opaque detail pixels"
    );
}

#[test]
fn settling_has_a_future_deadline_and_pending_workers_wait_for_notification() {
    for predicted_dt in [1.0 / 240.0, 1.0 / 60.0, 1.0 / 24.0] {
        let ctx = egui::Context::default();
        let source = source();
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
        let whole = Rect::from_min_size(Pos2::ZERO, egui::vec2(512.0, 384.0));
        state.demand([512, 384], (whole, whole), 1.0, 4096);
        let poll = |state: &mut ViewportRefinement, time| {
            ctx.run(
                egui::RawInput {
                    time: Some(time),
                    predicted_dt,
                    ..Default::default()
                },
                |ctx| {
                    state.poll(
                        ctx,
                        Some(source.clone()),
                        &DevelopmentRecipe::default(),
                        identity(1),
                    )
                },
            )
        };
        let settling = poll(&mut state, 4.0);
        let delay = settling.viewport_output[&egui::ViewportId::ROOT].repaint_delay;
        assert!(
            delay > Duration::ZERO && delay <= SETTLE,
            "Settling spun at {predicted_dt}s: {delay:?}"
        );
        assert!(
            state.pending.is_none(),
            "Settling must not start a worker early"
        );
        let request = state.desired.unwrap().request;
        let (release, blocked) = std::sync::mpsc::channel();
        state.pending = Some(Pending {
            identity: identity(1),
            request,
            task: spawn_notifying_task(
                "paced-poll-control",
                move |_| {
                    blocked.recv()?;
                    anyhow::bail!("intentional blocked-worker control")
                },
                || {},
            ),
        });
        state.since = Some(Instant::now() - SETTLE);
        let pending = poll(&mut state, 5.0);
        assert_eq!(
            pending.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
            Duration::MAX,
            "A pending worker scheduled polling at {predicted_dt}s"
        );
        release.send(()).unwrap();
        let work = state.pending.take().unwrap();
        assert!(
            work.task
                .receiver
                .recv_timeout(Duration::from_secs(5))
                .unwrap()
                .is_err()
        );
    }
}

#[test]
fn actual_detail_completion_wakes_a_sleeping_viewport_without_waiting_for_polling() {
    let ctx = egui::Context::default();
    let source = source();
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    for _ in 0..4 {
        let _ = ctx.run(Default::default(), |_| {});
    }
    let (wake, received) = std::sync::mpsc::channel();
    ctx.set_request_repaint_callback(move |info| {
        let _ = wake.send(info.delay);
    });
    let whole = Rect::from_min_size(Pos2::ZERO, egui::vec2(512.0, 384.0));
    state.demand([512, 384], (whole, whole), 1.0, 4096);
    state.since = Some(Instant::now() - SETTLE);
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll(
            ctx,
            Some(source.clone()),
            &DevelopmentRecipe::default(),
            identity(1),
        )
    });
    assert!(state.pending.is_some());
    let delay = received
        .recv_timeout(Duration::from_secs(5))
        .expect("The actual completed worker never woke the viewport");
    assert!(
        delay > Duration::ZERO && delay <= Duration::from_millis(1),
        "Completion must request one prompt future frame, without an extra immediate pass: {delay:?}"
    );
    let _ = ctx.run(Default::default(), |ctx| {
        state.poll(
            ctx,
            Some(source.clone()),
            &DevelopmentRecipe::default(),
            identity(1),
        );
    });
    assert!(
        state.pending.is_none(),
        "The next paint must find the completed result"
    );
    let detail = state
        .paint
        .as_ref()
        .unwrap()
        .detail
        .as_ref()
        .expect("The wake must accompany actual prepared pixels");
    assert!(detail.texture.is_some());
    assert_eq!(detail.request.stride, 1);
}

#[test]
fn a_panicking_detail_worker_retires_without_restarting_or_polling_forever() {
    let ctx = egui::Context::default();
    let source = source();
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    for _ in 0..4 {
        let _ = ctx.run(Default::default(), |_| {});
    }
    let whole = Rect::from_min_size(Pos2::ZERO, egui::vec2(512.0, 384.0));
    state.demand([512, 384], (whole, whole), 1.0, 4096);
    state.since = Some(Instant::now() - SETTLE);
    let request = state.desired.unwrap().request;
    let (notice, received) = std::sync::mpsc::channel();
    state.pending = Some(Pending {
        identity: identity(1),
        request,
        task: spawn_notifying_task(
            "failed-detail-control",
            |_| panic!("controlled detail panic"),
            move || {
                let _ = notice.send(());
            },
        ),
    });
    received
        .recv_timeout(Duration::from_secs(5))
        .expect("A failed worker must notify");
    let output = ctx.run(Default::default(), |ctx| {
        state.poll(
            ctx,
            Some(source.clone()),
            &DevelopmentRecipe::default(),
            identity(1),
        );
    });
    assert!(state.pending.is_none());
    assert_eq!(state.failed, Some((identity(1), request)));
    assert!(
        state
            .last_error
            .as_ref()
            .unwrap()
            .contains("stopped before publishing")
    );
    assert_eq!(
        state.jobs, 0,
        "A panic must not start an automatic crash loop"
    );
    assert_eq!(
        output.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
        Duration::MAX
    );
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
fn planner_shrinks_cache_padding_before_sacrificing_visible_native_pixels() {
    let source = [8192, 8192];
    let aperture = |min: [u32; 2], max: [u32; 2]| {
        Rect::from_min_max(
            Pos2::from(min.map(|v| v as f32 / 8192.0)),
            Pos2::from(max.map(|v| v as f32 / 8192.0)),
        )
    };
    // Even the old 32-bin snapping (without padding) exceeds a ceiling here;
    // the actually visible native pixels fit at both off-grid positions.
    for (min, max) in [([31, 113], [3091, 1137]), ([31, 17], [2539, 2525])] {
        let extent: [u32; 2] = std::array::from_fn(|i| max[i] - min[i]);
        assert!(extent.iter().all(|&n| n <= MAX_PATCH_SIDE));
        assert!(u64::from(extent[0]) * u64::from(extent[1]) <= MAX_PATCH_PIXELS);
        let snapped: [u32; 2] =
            std::array::from_fn(|i| max[i].div_ceil(32) * 32 - min[i] / 32 * 32);
        assert!(
            snapped.iter().any(|&n| n > MAX_PATCH_SIDE)
                || u64::from(snapped[0]) * u64::from(snapped[1]) > MAX_PATCH_PIXELS,
            "The fixture must reject cache rounding while visible native pixels fit"
        );
        let planned = plan(source, aperture(min, max), extent, 8192).unwrap();
        assert_eq!(
            planned.stride, 1,
            "Padding must not lower visible resolution"
        );
        assert_eq!(planned.min, min);
        assert_eq!(planned.max, max);
    }
    // Wide padding cannot fit here, but the smaller margin still can.
    let min = [2048, 2048];
    let max = [3948, 3048];
    let smaller = plan(source, aperture(min, max), [1900, 1000], 8192).unwrap();
    assert!((max[0] - min[0]) as f32 * 1.7 > MAX_PATCH_SIDE as f32);
    assert_eq!(smaller.stride, 1);
    assert!(smaller.min[0] < min[0] && smaller.max[0] > max[0]);
    assert!(smaller.max[0] - smaller.min[0] < 1900 * 3 / 2);
    // Oversized visible areas still obey both ceilings after increasing LOD.
    let large = plan(
        [16384, 12288],
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        [30000, 30000],
        65536,
    )
    .unwrap();
    let size: [u32; 2] =
        std::array::from_fn(|i| (large.max[i] - large.min[i]).div_ceil(large.stride));
    assert!(large.stride > 1);
    assert!(size.iter().all(|&n| n <= MAX_PATCH_SIDE));
    assert!(u64::from(size[0]) * u64::from(size[1]) <= MAX_PATCH_PIXELS);
}

#[test]
fn wider_cache_reuses_native_pixels_after_a_pan_that_exhausted_the_old_margin() {
    let ctx = egui::Context::default();
    let source = source();
    let mut state = ViewportRefinement::default();
    initialize(&ctx, &mut state, &source, 1);
    let full = Rect::from_min_size(Pos2::ZERO, egui::vec2(512.0, 384.0));
    let visible = Rect::from_min_max(egui::pos2(160.0, 120.0), egui::pos2(288.0, 216.0));
    state.demand([512, 384], (full, visible), 1.0, 4096);
    state.since = Some(Instant::now() - SETTLE);
    wait_patch(&ctx, &mut state, &source, 1);
    let initial_jobs = state.jobs;
    assert_eq!(initial_jobs, 1, "The fixture must develop real detail");
    let first = state
        .paint
        .as_ref()
        .unwrap()
        .detail
        .as_ref()
        .unwrap()
        .request;
    assert_eq!(first.stride, 1);
    let moved = visible.translate(egui::vec2(40.0, 0.0));
    state.demand([512, 384], (full, moved), 1.0, 4096);
    let demand = state.desired.unwrap();
    let former_margin = DisplayRegionRequest {
        min: [128, 96],
        max: [320, 256],
        stride: 1,
    };
    assert!(!covers(former_margin, [512, 384], demand.aperture, 1));
    assert!(covers(first, [512, 384], demand.aperture, 1));
    state.since = Some(Instant::now() - SETTLE);
    state.poll(
        &ctx,
        Some(source),
        &DevelopmentRecipe::default(),
        identity(1),
    );
    assert_eq!(
        state.jobs, initial_jobs,
        "The pan must not redo already cached detail"
    );
    assert!(state.pending.is_none());
    assert_eq!(
        state
            .paint
            .as_ref()
            .unwrap()
            .detail
            .as_ref()
            .unwrap()
            .request,
        first
    );
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
