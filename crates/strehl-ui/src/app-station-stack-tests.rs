//! The Stack station through the real shell (spec 10.1 items 1-6 and 9).
use super::*;
use crate::{
    jobs::FrameFile,
    pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface},
};

const SIZE: egui::Vec2 = egui::vec2(1680.0, 1050.0);
const PLANES: usize = 130;
const ANALYSIS: [usize; 2] = [3516, 2344];

fn finished_app(ctx: &egui::Context) -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = crate::workspace_history::Catalog::default();
    app.stack = Some(StackScan {
        directory: PathBuf::from("station-bracket"),
        frames: (0..PLANES)
            .map(|index| FrameFile {
                path: PathBuf::from(format!("station-{index}.arw")),
                bytes: 42,
            })
            .collect(),
        total_bytes: 42 * PLANES as u64,
    });
    app.progress.ingest("planes : 3516 x 2344 per CFA plane\nbands : 7 Laplacian levels + 1 base, coarsest 28 x 19\nwrote : result.tiff (7032 x 4688, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
    app.progress.frames_total = Some(PLANES);
    app.progress.placed = Some(PLANES);
    app.progress.refused = Some(0);
    let mut sequence = 0;
    for level in 0..8 {
        let spacing = 1usize << level;
        let width = ANALYSIS[0].div_ceil(spacing).min(128);
        let height = ANALYSIS[1].div_ceil(spacing).min(96);
        for plane in 0..PLANES {
            sequence += 1;
            let centre = (plane as f32 + 0.5) / PLANES as f32;
            let pixels: Vec<u8> = (0..width * height)
                .map(|index| {
                    let x = (index % width) as f32 / width as f32;
                    if (x - centre).abs() < 0.08 + 0.02 * level as f32 {
                        255
                    } else {
                        0
                    }
                })
                .collect();
            app.progress.admission_archive.ingest(
                &DiagnosticSurface {
                    sequence,
                    frame: plane,
                    level,
                    kind: DiagnosticKind::GateSupport,
                    scope: DiagnosticScope::Frame,
                    scale: DiagnosticScale::Linear,
                    width,
                    height,
                    min: 0.0,
                    max: 1.0,
                    folded: 1,
                    pixels: pixels.into(),
                },
                ANALYSIS,
            );
        }
    }
    app.progress.mark_complete();
    let result = PathBuf::from("station-result.tiff");
    app.result = Some(result.clone());
    app.image_path = Some(result);
    app.result_viewer.texture = Some(ctx.load_texture(
        "station-final",
        egui::ColorImage::filled([96, 64], Color32::from_rgb(40, 90, 110)),
        egui::TextureOptions::LINEAR,
    ));
    app.result_viewer.source_size = [7032, 4688];
    app.go_station(Station::Stack);
    app
}

fn context() -> egui::Context {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    ctx
}

fn frame(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, SIZE)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.sync_route();
            app.undo_shortcuts(ctx);
            app.shell_shortcuts(ctx);
            app.shell_bars(ctx);
            app.workspace(ctx);
            app.shell_overlays(ctx);
            crate::window_chrome::finish_with(ctx, app.picker_active(), 1.0);
        },
    )
}

fn texts(output: &egui::FullOutput) -> Vec<String> {
    fn walk(shape: &egui::Shape, into: &mut Vec<String>) {
        match shape {
            egui::Shape::Text(text) => into.push(text.galley.text().to_owned()),
            egui::Shape::Vec(shapes) => shapes.iter().for_each(|shape| walk(shape, into)),
            _ => {}
        }
    }
    let mut found = Vec::new();
    for clipped in &output.shapes {
        walk(&clipped.shape, &mut found);
    }
    found
}

fn moved(at: Pos2) -> Vec<egui::Event> {
    vec![egui::Event::PointerMoved(at)]
}

fn click(app: &mut StrehlApp, ctx: &egui::Context, at: Pos2, time: f64) {
    let button = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    frame(app, ctx, time, moved(at));
    frame(app, ctx, time + 0.01, vec![button(true)]);
    frame(app, ctx, time + 0.02, vec![button(false)]);
}

fn key(key: egui::Key, shift: bool) -> Vec<egui::Event> {
    vec![egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers {
            shift,
            ..Default::default()
        },
    }]
}

fn rail_x(plane: usize) -> f32 {
    RailGeometry::new(
        Rect::from_min_size(egui::pos2(0.0, 867.0), egui::vec2(1332.0, RAIL_CHART)),
        PLANES,
    )
    .unwrap()
    .x(plane)
}

#[test]
fn the_stack_route_composes_the_station_at_the_reference_rectangles() {
    let ctx = context();
    let mut app = finished_app(&ctx);
    frame(&mut app, &ctx, 0.0, vec![]);
    let output = frame(&mut app, &ctx, 0.1, vec![]);
    let shown = texts(&output);
    for expected in [
        "Photograph",
        "Plane",
        "Depth",
        "Soft spots",
        "Alignment",
        "CHECKS",
        "RECIPE",
        "DEPTH RAIL",
        "NEAR",
        "FAR",
        "Every plane read and placed",
    ] {
        assert!(
            shown.iter().any(|text| text == expected),
            "{expected} in {shown:?}"
        );
    }
    assert!(shown.iter().any(|text| text.starts_with("130 planes")));
    assert!(
        !shown.iter().any(|text| text.contains("ADMITTED SAMPLES")),
        "the old process view does not show on the Stack route"
    );
    assert!(app.stack_station_view());
    assert_eq!(app.stack_layout().rail, Some(STACK_RAIL));
    let photo = photo_rect(
        Rect::from_min_max(egui::pos2(0.0, 80.0), egui::pos2(1332.0, 836.0)),
        7032.0 / 4688.0,
    );
    for (actual, expected) in [
        (photo.left(), 128.0),
        (photo.top(), 94.0),
        (photo.width(), 1076.0),
        (photo.height(), 718.0),
    ] {
        assert!((actual - expected).abs() <= 2.0, "{actual} vs {expected}");
    }
    assert!(!app.stack_paints_legacy(), "the station paints from tokens");
}

#[test]
fn rail_hover_peeks_click_holds_keys_step_and_escape_releases() {
    let ctx = context();
    let mut app = finished_app(&ctx);
    frame(&mut app, &ctx, 0.0, vec![]);
    let at = egui::pos2(rail_x(99), 900.0);
    frame(&mut app, &ctx, 0.1, moved(at));
    let peek = frame(&mut app, &ctx, 0.2, moved(at));
    assert!(app.stack_station.lens.peeking());
    assert_eq!(
        app.process_inspection(),
        Some(99),
        "the browser previews the peeked plane"
    );
    let shown = texts(&peek);
    assert!(shown.iter().any(|text| text == "Plane 100"));
    assert!(shown.iter().any(|text| text == "click to hold"));
    click(&mut app, &ctx, at, 0.3);
    assert_eq!(app.stack_station.lens.held(), Some(99));
    assert_eq!(app.stack_station.mode, Lens::Plane);
    let held = frame(&mut app, &ctx, 0.4, moved(egui::pos2(600.0, 400.0)));
    let shown = texts(&held);
    assert_eq!(
        shown.iter().filter(|text| text.ends_with(" kept")).count(),
        8
    );
    assert!(shown.iter().any(|text| text == "Holding a plane"));
    frame(&mut app, &ctx, 0.5, key(egui::Key::ArrowRight, false));
    assert_eq!(app.stack_station.lens.held(), Some(100));
    frame(&mut app, &ctx, 0.6, key(egui::Key::ArrowLeft, true));
    assert_eq!(app.stack_station.lens.held(), Some(90));
    frame(&mut app, &ctx, 0.7, key(egui::Key::Escape, false));
    assert!(!app.stack_station.lens.holding());
    assert_eq!(app.stack_station.mode, Lens::Photograph);
}

#[test]
fn keys_choose_lenses_and_e_opens_the_engine_room() {
    let ctx = context();
    let mut app = finished_app(&ctx);
    frame(&mut app, &ctx, 0.0, vec![]);
    frame(&mut app, &ctx, 0.1, key(egui::Key::Num2, false));
    assert!(
        app.stack_station.lens.holding(),
        "2 chooses the Plane lens and holds a plane"
    );
    frame(&mut app, &ctx, 0.2, key(egui::Key::Num1, false));
    assert!(!app.stack_station.lens.holding());
    frame(&mut app, &ctx, 0.3, key(egui::Key::Num3, false));
    assert_eq!(
        app.stack_station.mode,
        Lens::Photograph,
        "no depth evidence: Depth stays off"
    );
    frame(&mut app, &ctx, 0.4, key(egui::Key::E, false));
    frame(&mut app, &ctx, 0.5, vec![]);
    assert_eq!(app.stack_room(), Room::Engine);
    assert!(!app.stack_station_view());
    assert!(app.stack_paints_legacy());
}

#[test]
fn hovering_the_photograph_goes_live_and_pointer_motion_rebuilds_nothing() {
    let ctx = context();
    let mut app = finished_app(&ctx);
    frame(&mut app, &ctx, 0.0, vec![]);
    let at = egui::pos2(128.0 + 1076.0 * 0.6, 94.0 + 718.0 * 0.5);
    frame(&mut app, &ctx, 0.1, moved(at));
    let live = frame(&mut app, &ctx, 0.2, moved(at));
    let shown = texts(&live);
    assert!(shown.iter().any(|text| text == "CORE SAMPLE"));
    assert!(shown.iter().any(|text| text == "LIVE"));
    assert_eq!(app.stack_station.last_core.leading.len(), 3);
    assert!(
        app.stack_station.rail.has_region(),
        "the rail's region line appears"
    );
    let builds = app.stack_station.rail.builds;
    let strips = app.stack_station.core.strip_builds;
    let marks = app.stack_station.film.mark_builds;
    // Sub-pixel motion: rebuilds happen only when the sampled window (its
    // cell set) really changes, once per change, never per frame.
    let mut keys = vec![app.stack_station.core.rail_key(0)];
    for step in 0..20 {
        let jitter = egui::vec2((step % 3) as f32 * 0.3, (step % 2) as f32 * 0.3);
        frame(&mut app, &ctx, 0.3 + step as f64 * 0.01, moved(at + jitter));
        keys.push(app.stack_station.core.rail_key(0));
    }
    let changes = keys.windows(2).filter(|pair| pair[0] != pair[1]).count();
    // The rail paints before the canvas measures, so its line follows one
    // frame later; settle that frame before counting.
    let last = at + egui::vec2((19 % 3) as f32 * 0.3, (19 % 2) as f32 * 0.3);
    frame(&mut app, &ctx, 0.6, moved(last));
    assert_eq!(app.stack_station.core.rail_key(0), *keys.last().unwrap());
    let after = app.stack_station.rail.builds;
    assert_eq!(
        after.meshes, builds.meshes,
        "markers never rebuild the engraving"
    );
    assert_eq!(after.series, builds.series);
    assert_eq!(after.regions - builds.regions, changes);
    assert_eq!(app.stack_station.core.strip_builds - strips, changes);
    assert_eq!(app.stack_station.film.mark_builds, marks);
    assert!(changes < 20, "most sub-pixel steps stay inside one window");
    // A click pins the sample where clicked.
    click(&mut app, &ctx, at, 1.0);
    assert!(app.stack_station.core.pinned());
}

#[test]
fn plane_hold_from_launch_holds_once_the_planes_are_known() {
    let ctx = context();
    let mut app = finished_app(&ctx);
    app.stack_station.launch_hold = Some(65);
    frame(&mut app, &ctx, 0.0, vec![]);
    frame(&mut app, &ctx, 0.1, vec![]);
    assert_eq!(app.stack_station.lens.held(), Some(64));
    assert_eq!(app.stack_station.launch_hold, None);
}

/// A finished app on any synthetic length (level-major maps, as the engine's
/// archive retains them) or, with `STREHL_UI_BENCH_RUN_LOG`, a real render's
/// log streamed into the pipeline (read-only).
fn benchmark_app(ctx: &egui::Context, planes: usize, log: Option<&std::path::Path>) -> StrehlApp {
    let mut app = finished_app(ctx);
    if let Some(log) = log {
        app.progress = crate::pipeline::PipelineProgress::default();
        let text = std::fs::read(log).expect("render log");
        for chunk in text.split(|&byte| byte == b'\n') {
            if let Ok(line) = std::str::from_utf8(chunk) {
                app.progress.ingest(&format!("{line}\n"));
            }
        }
        app.progress.mark_complete();
        let frames = app.progress.frames_total.unwrap_or(0);
        app.stack = Some(StackScan {
            directory: PathBuf::from("real-bracket"),
            frames: (0..frames)
                .map(|index| FrameFile {
                    path: PathBuf::from(format!("real-{index}.arw")),
                    bytes: 42,
                })
                .collect(),
            total_bytes: 42 * frames as u64,
        });
        return app;
    }
    if planes == PLANES {
        return app;
    }
    app.progress.admission_archive = Default::default();
    app.progress.frames_total = Some(planes);
    app.progress.placed = Some(planes);
    let mut sequence = 0;
    for level in 0..8 {
        let spacing = 1usize << level;
        let width = ANALYSIS[0].div_ceil(spacing).min(128);
        let height = ANALYSIS[1].div_ceil(spacing).min(96);
        for plane in 0..planes {
            sequence += 1;
            let centre = (plane as f32 + 0.5) / planes as f32;
            let pixels: Vec<u8> = (0..width * height)
                .map(|index| {
                    let x = (index % width) as f32 / width as f32;
                    if (x - centre).abs() < 0.05 + 0.02 * level as f32 && (index + plane) % 7 != 0 {
                        255
                    } else {
                        0
                    }
                })
                .collect();
            app.progress.admission_archive.ingest(
                &DiagnosticSurface {
                    sequence,
                    frame: plane,
                    level,
                    kind: DiagnosticKind::GateSupport,
                    scope: DiagnosticScope::Frame,
                    scale: DiagnosticScale::Linear,
                    width,
                    height,
                    min: 0.0,
                    max: 1.0,
                    folded: 1,
                    pixels: pixels.into(),
                },
                ANALYSIS,
            );
        }
    }
    app.stack = Some(StackScan {
        directory: PathBuf::from("bench-bracket"),
        frames: (0..planes)
            .map(|index| FrameFile {
                path: PathBuf::from(format!("bench-{index}.arw")),
                bytes: 42,
            })
            .collect(),
        total_bytes: 42 * planes as u64,
    });
    app
}

#[test]
#[ignore = "explicit Stack station CPU paint+tessellation benchmark; not GPU FPS"]
fn benchmark_stack_station_pointer_sweeps() {
    let real = std::env::var_os("STREHL_UI_BENCH_RUN_LOG").map(PathBuf::from);
    let mut cases: Vec<(String, usize, Option<PathBuf>)> = vec![
        ("synthetic".into(), PLANES, None),
        ("synthetic".into(), 1_500, None),
        ("synthetic".into(), 6_000, None),
    ];
    if let Some(log) = real {
        cases.push(("real".into(), 0, Some(log)));
    }
    for (kind, planes, log) in cases {
        let ctx = context();
        let built = std::time::Instant::now();
        let mut app = benchmark_app(&ctx, planes, log.as_deref());
        let build_s = built.elapsed().as_secs_f64();
        let planes = app.stack_planes();
        let mut time = 0.0;
        for _ in 0..3 {
            time += 1.0 / 120.0;
            frame(&mut app, &ctx, time, vec![]);
        }
        assert!(app.stack_station_view(), "the station owns the canvas");
        let mut sweep = |app: &mut StrehlApp, at: &dyn Fn(f32) -> Pos2, reverse: bool| -> f64 {
            let start = std::time::Instant::now();
            for step in 0..120 {
                time += 1.0 / 120.0;
                let phase = if reverse { 119 - step } else { step } as f32 / 119.0;
                let output = frame(app, &ctx, time, moved(at(phase)));
                std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
            }
            start.elapsed().as_secs_f64() * 1000.0 / 120.0
        };
        let photo = |phase: f32| {
            egui::pos2(
                128.0 + 1076.0 * (0.1 + 0.8 * phase),
                94.0 + 718.0 * (0.3 + 0.4 * phase),
            )
        };
        let rail = |phase: f32| egui::pos2(20.0 + phase * 1292.0, 905.0);
        let mut photo_ms = Vec::new();
        let mut rail_ms = Vec::new();
        for round in 0..4 {
            photo_ms.push(sweep(&mut app, &photo, round % 2 == 1));
            rail_ms.push(sweep(&mut app, &rail, round % 2 == 1));
        }
        // Held: stepping through planes with the arrow key, two-up painted.
        app.stack_station.lens.hold(planes / 2);
        let start = std::time::Instant::now();
        for _ in 0..120 {
            time += 1.0 / 120.0;
            let output = frame(&mut app, &ctx, time, key(egui::Key::ArrowRight, false));
            std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
        }
        let held_ms = start.elapsed().as_secs_f64() * 1000.0 / 120.0;
        let min = |values: &[f64]| values.iter().copied().fold(f64::INFINITY, f64::min);
        println!(
            "stack_station_cpu_ms_per_frame kind={kind} planes={planes} maps={} dropped={} build_s={build_s:.1} photo={photo_ms:?} rail={rail_ms:?} held_step={held_ms:.3}",
            app.progress.admission_archive.len(),
            app.progress.admission_archive.dropped(),
        );
        println!(
            "stack_station_cpu_min_ms kind={kind} planes={planes} photo={:.3} rail={:.3} held_step={held_ms:.3}",
            min(&photo_ms),
            min(&rail_ms)
        );
    }
}

#[test]
fn develop_and_export_show_the_photograph_alone_and_the_footer_offers_render_again() {
    let ctx = context();
    let mut app = finished_app(&ctx);
    frame(&mut app, &ctx, 0.0, vec![]);
    let stack = frame(&mut app, &ctx, 0.1, vec![]);
    let shown = texts(&stack);
    assert!(shown.iter().any(|text| text == "Develop this render"));
    assert!(shown.iter().any(|text| text == "Render again"));
    for station in [Station::Develop, Station::Export] {
        app.go_station(station);
        frame(&mut app, &ctx, 0.2, vec![]);
        let output = frame(&mut app, &ctx, 0.3, vec![]);
        let shown = texts(&output);
        for legacy in [
            "CAPTURE / ADMITTED SAMPLES",
            "PHOTOGRAPH / EDIT",
            "YOUR PHOTOGRAPH",
        ] {
            assert!(
                !shown.iter().any(|text| text.contains(legacy)),
                "{station:?} shows only the photograph, not {legacy}"
            );
        }
        assert!(
            app.process_space.edit_mapping().is_some(),
            "overlays still map onto it"
        );
    }
}
