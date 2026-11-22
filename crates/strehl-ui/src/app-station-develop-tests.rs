//! Develop and Export composed in the shell: panels, tabs, footer, rail,
//! themes, and pointer motion that rebuilds nothing.
use super::*;
use crate::jobs::FrameFile;
use std::sync::Arc;
use strehl_edit::{ImageOrigin, LinearImage};

const SIZE: egui::Vec2 = egui::vec2(1680.0, 1050.0);

fn context() -> egui::Context {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    ctx
}

fn app(dir: &Path) -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = crate::workspace_history::Catalog::default();
    app.stack = Some(StackScan {
        directory: PathBuf::from("develop-bracket"),
        frames: (0..13)
            .map(|index| FrameFile {
                path: PathBuf::from(format!("develop-{index}.arw")),
                bytes: 42,
            })
            .collect(),
        total_bytes: 546,
    });
    let image = Arc::new(LinearImage {
        width: 96,
        height: 64,
        pixels: (0..96 * 64)
            .flat_map(|i| [0.03 + (i % 96) as f32 * 0.004, 0.1, 0.2])
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    let path = dir.join("run").join("result.tiff");
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        coverage: None,
        image: Arc::clone(&image),
        preview: image,
        recipe: Default::default(),
        source: dir.join("run").join("master.tiff"),
        warnings: Vec::new(),
    });
    app.export_pane.station.library = Some(crate::export_presets::Library::default());
    app
}

fn frame(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, SIZE)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.sync_route();
            app.shell_bars(ctx);
            app.workspace(ctx);
            app.shell_overlays(ctx);
        },
    )
}

fn texts(output: &egui::FullOutput) -> Vec<(String, egui::Rect)> {
    fn walk(shape: &egui::Shape, into: &mut Vec<(String, egui::Rect)>) {
        match shape {
            egui::Shape::Text(text) => {
                into.push((text.galley.text().to_owned(), text.visual_bounding_rect()))
            }
            egui::Shape::Vec(parts) => parts.iter().for_each(|part| walk(part, into)),
            _ => {}
        }
    }
    let mut found = Vec::new();
    for shape in &output.shapes {
        walk(&shape.shape, &mut found);
    }
    found
}

fn find(output: &egui::FullOutput, text: &str) -> Option<egui::Rect> {
    texts(output)
        .into_iter()
        .find(|(t, _)| t == text)
        .map(|(_, rect)| rect)
}

fn panel(ctx: &egui::Context, id: &str) -> Option<egui::Rect> {
    egui::containers::panel::PanelState::load(ctx, egui::Id::new(id)).map(|state| state.rect)
}

fn click(at: egui::Pos2) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(at),
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed: true,
            modifiers: Default::default(),
        },
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        },
    ]
}

#[test]
fn develop_fills_the_tools_strip_tabs_inspector_and_footer() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut app = app(dir.path());
    app.go_station(Station::Develop);
    let mut output = frame(&mut app, &ctx, 0.0, vec![]);
    for step in 1..3 {
        output = frame(&mut app, &ctx, step as f64 * 0.05, vec![]);
    }
    // develop.png metrics: tools 0, 44, 44, 982; control strip 44, 44, 1288, 36.
    let tools = panel(&ctx, "studio-tools").expect("the tools strip");
    assert_eq!(
        (tools.left(), tools.top(), tools.width()),
        (0.0, 44.0, 44.0)
    );
    let strip = panel(&ctx, "studio-control-strip").unwrap();
    assert!(
        (strip.left() - 44.0).abs() <= 2.0 && (strip.width() - 1288.0).abs() <= 2.0,
        "{strip:?}"
    );
    for label in [
        "ADJUST",
        "LAYERS · 0",
        "VERSIONS · 1",
        "MOVE",
        "After",
        "Whole photograph",
        "Signature",
        "Export…",
        "Save version",
    ] {
        assert!(find(&output, label).is_some(), "{label} is not drawn");
    }
    // The footer sits in the shell's 53 px footer.
    let export = find(&output, "Export…").unwrap();
    assert!(export.center().y > 1026.0 - 53.0 && export.center().x > 1332.0);
    assert!(!app.station_paints_legacy(Station::Develop));
    // Tabs switch.
    let layers = find(&output, "LAYERS · 0").unwrap();
    frame(&mut app, &ctx, 0.2, click(layers.center()));
    assert_eq!(
        app.edit_pane.develop.panel.tab,
        station::InspectorTab::Layers
    );
    // The rail opens with the depth brush.
    assert_eq!(app.develop_layout(Station::Develop).rail, None);
    app.editor.develop.tool = DevelopTool::DepthBrush;
    let output = frame(&mut app, &ctx, 0.3, vec![]);
    let output = {
        let _ = output;
        frame(&mut app, &ctx, 0.35, vec![])
    };
    assert_eq!(app.develop_layout(Station::Develop).rail, Some(DEPTH_RAIL));
    assert!(find(&output, "DEPTH RAIL").is_some());
    assert!(find(&output, "DEPTH BRUSH").is_some());
}

#[test]
fn export_fills_presets_footer_history_and_preview() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut app = app(dir.path());
    app.go_station(Station::Export);
    let mut output = frame(&mut app, &ctx, 0.0, vec![]);
    for step in 1..3 {
        output = frame(&mut app, &ctx, step as f64 * 0.05, vec![]);
    }
    for label in [
        "PRESETS",
        "Web",
        "HDR",
        "Print",
        "Archive",
        // No folder is chosen for this subject yet: the button chooses one.
        "Choose a folder…",
        "EXPORTS OF THIS PHOTOGRAPH",
        "PREVIEW OF",
    ] {
        assert!(find(&output, label).is_some(), "{label} is not drawn");
    }
    let rail = panel(&ctx, "studio-rail").expect("the history under the canvas");
    assert_eq!(rail.height(), 152.0);
    assert!(
        panel(&ctx, "studio-tools").is_none_or(|r| r.width() == 0.0)
            || !app.develop_layout(Station::Export).tools
    );
    assert!(!app.station_paints_legacy(Station::Export));
}

#[test]
fn the_palette_follows_every_theme() {
    let ctx = context();
    for name in crate::studio_theme::ThemeName::ALL {
        crate::studio_theme::apply(&ctx, name, crate::studio_theme::Surround::Theme, false);
        let t = crate::studio_theme::tokens(&ctx);
        let p = style::StudioPalette::of(&ctx);
        assert_eq!(
            (p.panel, p.ink, p.accent, p.line_2),
            (t.panel, t.ink, t.accent, t.line2),
            "{name:?}"
        );
    }
}

#[test]
fn pointer_only_motion_over_develop_and_export_changes_nothing() {
    let dir = tempfile::tempdir().unwrap();
    for station in [Station::Develop, Station::Export] {
        let ctx = context();
        let mut app = app(dir.path());
        app.go_station(station);
        for step in 0..3 {
            frame(&mut app, &ctx, step as f64 * 0.05, vec![]);
        }
        let revision = app.editor.revision;
        let history = app.editor.history_revision();
        let library = app.export_pane.station.library.clone();
        let tab = app.edit_pane.develop.panel.tab;
        for step in 0..120 {
            let x = 10.0 + (step as f32 / 119.0) * 1660.0;
            let y = 60.0 + (step as f32 * 37.0) % 960.0;
            frame(
                &mut app,
                &ctx,
                1.0 + step as f64 / 60.0,
                vec![egui::Event::PointerMoved(egui::pos2(x, y))],
            );
        }
        assert_eq!(
            app.editor.revision, revision,
            "{station:?}: motion edited the photograph"
        );
        assert_eq!(app.editor.history_revision(), history);
        assert_eq!(app.export_pane.station.library, library);
        assert_eq!(app.edit_pane.develop.panel.tab, tab);
        assert!(app.editor.develop.outbox.is_empty());
        assert!(app.export_pane.station.batch.is_none());
    }
}

#[test]
fn clipping_builds_its_overlay_on_a_worker_and_clears_it() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut app = app(dir.path());
    app.editor.recovery_root = Some(dir.path().join("recovery"));
    app.handle_develop_intents(vec![station::DevelopIntent::ToggleClipping], 0.0);
    assert!(app.editor.develop.clipping);
    let started = std::time::Instant::now();
    while app.editor.clip_overlay.is_none() {
        assert!(
            started.elapsed() < std::time::Duration::from_secs(20),
            "no clipping overlay"
        );
        let _ = ctx.run(egui::RawInput::default(), |ctx| {
            app.editor.poll(ctx, 4096);
        });
        std::thread::sleep(std::time::Duration::from_millis(5));
    }
    let overlay = app.editor.clip_overlay.as_ref().unwrap();
    assert_eq!(overlay.revision, app.editor.revision);
    assert_eq!(overlay.texture.size(), [96, 64]);
    app.handle_develop_intents(vec![station::DevelopIntent::ToggleClipping], 0.1);
    let _ = ctx.run(egui::RawInput::default(), |ctx| app.editor.poll(ctx, 4096));
    assert!(app.editor.clip_overlay.is_none());
}

/// One frame of only the canvas and a 348 px inspector: today's Edit pane
/// or the Studio 2 inspector (body, footer, strip), for a like comparison.
fn bare_frame(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    at: egui::Pos2,
    legacy: bool,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, SIZE)),
            time: Some(time),
            events: vec![egui::Event::PointerMoved(at)],
            ..Default::default()
        },
        |ctx| {
            egui::SidePanel::right("bench-inspector")
                .exact_width(348.0)
                .resizable(false)
                .show(ctx, |ui| {
                    if legacy {
                        app.edit_panel(ui);
                    } else {
                        app.develop_inspector_body(ui, Station::Develop);
                        app.develop_footer(ui, Station::Develop);
                    }
                });
            if !legacy {
                egui::TopBottomPanel::top("bench-strip")
                    .exact_height(36.0)
                    .show(ctx, |ui| {
                        ui.horizontal_centered(|ui| app.develop_strip(ui, Station::Develop));
                    });
            }
            egui::CentralPanel::default().show(ctx, |ui| app.show_process(ui));
        },
    )
}

/// Release benchmark: CPU paint and tessellation per frame while the pointer
/// sweeps, through the whole shell, and the inspector alone against today's
/// Edit pane in the same panel.
#[test]
#[ignore = "release benchmark: cargo test --release -p strehl-ui -- --ignored benchmark_develop_and_export --nocapture"]
fn benchmark_develop_and_export_pointer_sweeps() {
    let dir = tempfile::tempdir().unwrap();
    let point = |step: usize| {
        egui::pos2(
            60.0 + (step as f32 / 119.0) * 1600.0,
            100.0 + (step as f32 * 53.0) % 900.0,
        )
    };
    let mut results = Vec::new();
    for (label, shell, station, legacy) in [
        ("shell: Develop", true, Station::Develop, false),
        ("shell: Export", true, Station::Export, false),
        (
            "panel: Studio 2 Develop inspector",
            false,
            Station::Develop,
            false,
        ),
        ("panel: legacy Edit pane", false, Station::Develop, true),
    ] {
        let ctx = context();
        let mut app = app(dir.path());
        app.go_station(station);
        let run = |app: &mut StrehlApp, time: f64, step: usize| {
            if shell {
                frame(
                    app,
                    &ctx,
                    time,
                    vec![egui::Event::PointerMoved(point(step))],
                )
            } else {
                bare_frame(app, &ctx, time, point(step), legacy)
            }
        };
        for step in 0..10 {
            run(&mut app, step as f64 * 0.01, step);
        }
        let mut times = Vec::new();
        for round in 0..6 {
            let started = std::time::Instant::now();
            for step in 0..120 {
                let output = run(&mut app, 1.0 + round as f64 + step as f64 / 120.0, step);
                std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
            }
            times.push(started.elapsed().as_secs_f64() * 1000.0 / 120.0);
        }
        results.push((label, times));
    }
    for (label, times) in results {
        eprintln!("{label}: {times:.3?} ms per frame (paint + tessellation)");
    }
}

/// Release benchmark on a real master. `STREHL_UI_BENCH_RUN` names a COPY of
/// a run folder (result.tiff, master.tiff): the editor may write recovery
/// and sidecar files beside it, so never point it at a capture folder.
/// The canvas is driven as `show_process` drives it (`request_view` and
/// `draw_overlay` with the photograph's screen mapping), so no render log is
/// needed. Measures (spec 5.3 for P7): slider drag to the updated overview,
/// release to the sharp patch at 6x, the split handle drag per frame
/// against a plain pointer sweep, and the histogram's share of each overview.
#[test]
#[ignore = "release benchmark: STREHL_UI_BENCH_RUN=<copied run> cargo test --release -p strehl-ui -- --ignored benchmark_develop_latency --nocapture"]
fn benchmark_develop_latency_on_a_real_master() {
    use std::cell::{Cell, RefCell};
    use std::time::{Duration, Instant};
    let Ok(run) = std::env::var("STREHL_UI_BENCH_RUN") else {
        eprintln!("STREHL_UI_BENCH_RUN is not set");
        return;
    };
    let run = PathBuf::from(run);
    let result = run.join("result.tiff");
    let ctx = context();
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = crate::workspace_history::Catalog::default();
    app.editor.recovery_root = Some(run.join("bench-recovery"));
    app.result = Some(result.clone());
    app.image_path = Some(result.clone());
    app.go_station(Station::Develop);
    let start = Instant::now();
    let zoom = Cell::new(1.0_f32);
    let frame_ms = RefCell::new(Vec::new());
    let canvas = egui::Rect::from_min_max(egui::pos2(44.0, 80.0), egui::pos2(1332.0, 1026.0));
    // The photograph's screen rectangle at `zoom` about the canvas centre.
    let mapping = |app: &StrehlApp| {
        let loaded = app.editor.loaded.as_ref()?;
        let size = egui::vec2(loaded.image.width as f32, loaded.image.height as f32);
        let fit = (canvas.width() / size.x).min(canvas.height() / size.y);
        Some((
            egui::Rect::from_center_size(canvas.center(), size * fit * zoom.get()),
            canvas,
        ))
    };
    let live = |app: &mut StrehlApp, events: Vec<egui::Event>, record: bool| {
        let began = Instant::now();
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, SIZE)),
                time: Some(start.elapsed().as_secs_f64()),
                events,
                ..Default::default()
            },
            |ctx| {
                app.poll_editing(ctx);
                egui::SidePanel::right("bench-inspector")
                    .exact_width(348.0)
                    .resizable(false)
                    .show(ctx, |ui| {
                        app.develop_inspector_body(ui, Station::Develop);
                    });
                egui::CentralPanel::default().show(ctx, |ui| {
                    if let Some((image, clip)) = mapping(app) {
                        if let Some(texture) = &app.editor.texture {
                            ui.painter().with_clip_rect(clip).image(
                                texture.id(),
                                image,
                                egui::Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                                egui::Color32::WHITE,
                            );
                        }
                        app.editor.request_view(ctx, (image, clip), 4096);
                        app.editor.draw_overlay(ui, (image, clip));
                    }
                });
            },
        );
        std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
        if record {
            frame_ms
                .borrow_mut()
                .push(began.elapsed().as_secs_f64() * 1000.0);
        }
        std::thread::sleep(Duration::from_millis(4));
    };
    let wait = |label: &str, app: &mut StrehlApp, done: &dyn Fn(&StrehlApp) -> bool| {
        let began = Instant::now();
        while !done(app) {
            assert!(
                began.elapsed() < Duration::from_secs(180),
                "{label} timed out: painted {:?} of {}, viewport {}",
                app.editor.painted_revision,
                app.editor.revision,
                app.editor.viewport.stats()
            );
            live(app, vec![], false);
        }
        began.elapsed().as_secs_f64() * 1000.0
    };
    let current = |app: &StrehlApp| {
        app.editor.loaded.is_some() && app.editor.painted_revision == Some(app.editor.revision)
    };
    let sharp = |app: &StrehlApp| {
        let stats = app.editor.viewport.stats();
        current(app)
            && stats["settled"] == true
            && stats["published"]["revision"].as_u64() == Some(app.editor.revision)
    };
    let opened = wait("open", &mut app, &current);
    let loaded = app.editor.loaded.as_ref().unwrap();
    eprintln!(
        "open to first overview {opened:.0} ms; master {} x {}, overview {} x {}, regions {}",
        loaded.image.width,
        loaded.image.height,
        loaded.preview.width,
        loaded.preview.height,
        app.editor.recipe.regions.len()
    );
    // The histogram's cost on the worker, per overview.
    let job = app.editor.development_job(false).unwrap();
    let mut histogram = Vec::new();
    for _ in 0..15 {
        let began = Instant::now();
        let (_, _, rgb) = job
            .image(true)
            .render_region_sdr8(job.recipe(), [0.0, 0.0], [1.0, 1.0], 256)
            .unwrap();
        std::hint::black_box(station::Histogram::from_rgb8(&rgb));
        histogram.push(began.elapsed().as_secs_f64() * 1000.0);
    }
    // 6x on the centre: the settle needs a sharp patch.
    zoom.set(6.0);
    let first = wait("first sharp patch", &mut app, &sharp);
    eprintln!("first sharp patch at 6x {first:.0} ms");
    // Slider drag: 40 steps at 60 Hz with the button held on the inspector's
    // empty foot (not on a control).
    let pointer = egui::pos2(1500.0, 1040.0);
    live(
        &mut app,
        vec![
            egui::Event::PointerMoved(pointer),
            egui::Event::PointerButton {
                pos: pointer,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Default::default(),
            },
        ],
        false,
    );
    let field = station::AdjustmentField::LIGHT[0];
    let range = field.range();
    let mut pending: Vec<(u64, Instant)> = Vec::new();
    let mut latencies = Vec::new();
    let drag_began = Instant::now();
    let mut step = 0;
    while step < 40 || !pending.is_empty() {
        if step < 40 && drag_began.elapsed() >= Duration::from_secs_f64(step as f64 / 60.0) {
            let t = step as f32 / 39.0;
            let value = range.start() + (range.end() - range.start()) * (0.35 + 0.3 * t);
            app.handle_develop_intents(
                vec![station::DevelopIntent::Adjust(field, value)],
                start.elapsed().as_secs_f64(),
            );
            pending.push((app.editor.revision, Instant::now()));
            step += 1;
        }
        live(&mut app, vec![], true);
        let painted = app.editor.painted_revision.unwrap_or(0);
        pending.retain(|(revision, at)| {
            if painted >= *revision {
                latencies.push(at.elapsed().as_secs_f64() * 1000.0);
                false
            } else {
                true
            }
        });
        assert!(
            drag_began.elapsed() < Duration::from_secs(120),
            "drag timed out"
        );
    }
    let drag_frames = frame_ms.take();
    live(
        &mut app,
        vec![egui::Event::PointerButton {
            pos: pointer,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        }],
        false,
    );
    let settle = wait("settle", &mut app, &sharp);
    // Split view at fit: drag the handle across, against the same sweep
    // without it.
    zoom.set(1.0);
    wait("fit", &mut app, &sharp);
    let (image, _) = mapping(&app).unwrap();
    let y = image.center().y;
    let sweep = |i: usize| image.left() + image.width() * (0.1 + 0.8 * i as f32 / 119.0);
    for i in 0..120 {
        live(
            &mut app,
            vec![egui::Event::PointerMoved(egui::pos2(sweep(i), y))],
            true,
        );
    }
    let plain = frame_ms.take();
    app.editor.develop.compare = station::Compare::Split;
    app.editor.develop.split = 0.1;
    let revision = app.editor.revision;
    wait("before overview", &mut app, &|app| {
        app.editor.before_overview.is_some()
    });
    let jobs_before = app.editor.viewport.stats()["jobs"].as_u64();
    let grip = egui::pos2(sweep(0), y);
    live(
        &mut app,
        vec![
            egui::Event::PointerMoved(grip),
            egui::Event::PointerButton {
                pos: grip,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Default::default(),
            },
        ],
        false,
    );
    for i in 0..120 {
        live(
            &mut app,
            vec![egui::Event::PointerMoved(egui::pos2(sweep(i), y))],
            true,
        );
    }
    let split = frame_ms.take();
    let split_end = app.editor.develop.split;
    live(
        &mut app,
        vec![egui::Event::PointerButton {
            pos: egui::pos2(sweep(119), y),
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        }],
        false,
    );
    let jobs_after = app.editor.viewport.stats()["jobs"].as_u64();
    // h-develop: the same at 4x, where the tiles hold full resolution and
    // the line stays on screen (a fraction of the visible photograph).
    zoom.set(4.0);
    wait("sharp at 4x", &mut app, &sharp);
    let (image4, clip4) = mapping(&app).unwrap();
    let shown = image4.intersect(clip4);
    let y4 = shown.top() + shown.height() * 0.3;
    let sweep4 = |i: usize| shown.left() + shown.width() * (0.1 + 0.8 * i as f32 / 119.0);
    app.editor.develop.compare = station::Compare::After;
    for i in 0..120 {
        live(
            &mut app,
            vec![egui::Event::PointerMoved(egui::pos2(sweep4(i), y4))],
            true,
        );
    }
    let plain4 = frame_ms.take();
    app.editor.develop.compare = station::Compare::Split;
    app.editor.develop.split = 0.1;
    // One frame with the line drawn, so the press finds it (as a person's
    // would: the line is on screen before it is taken).
    live(&mut app, vec![], false);
    let jobs4 = app.editor.viewport.stats()["jobs"].as_u64();
    let grip4 = egui::pos2(sweep4(0), y4);
    live(
        &mut app,
        vec![
            egui::Event::PointerMoved(grip4),
            egui::Event::PointerButton {
                pos: grip4,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Default::default(),
            },
        ],
        false,
    );
    for i in 0..120 {
        live(
            &mut app,
            vec![egui::Event::PointerMoved(egui::pos2(sweep4(i), y4))],
            true,
        );
    }
    let split4 = frame_ms.take();
    let split4_end = app.editor.develop.split;
    live(
        &mut app,
        vec![egui::Event::PointerButton {
            pos: egui::pos2(sweep4(119), y4),
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        }],
        false,
    );
    let jobs4_end = app.editor.viewport.stats()["jobs"].as_u64();
    let stats = |mut v: Vec<f64>| {
        v.sort_by(f64::total_cmp);
        let at = |q: f64| v[((v.len() - 1) as f64 * q).round() as usize];
        format!(
            "median {:.2} p95 {:.2} max {:.2} (n {})",
            at(0.5),
            at(0.95),
            at(1.0),
            v.len()
        )
    };
    eprintln!("slider drag to updated overview: {} ms", stats(latencies));
    eprintln!("frame time during the drag: {} ms", stats(drag_frames));
    eprintln!("histogram per overview (256 px): {} ms", stats(histogram));
    eprintln!("release to sharp patch at 6x: {settle:.0} ms");
    eprintln!("pointer sweep at fit, After: {} ms per frame", stats(plain));
    eprintln!("split handle drag: {} ms per frame", stats(split));
    eprintln!(
        "split moved 0.10 -> {split_end:.2}; revision unchanged {}; viewport jobs {:?} -> {:?}",
        app.editor.revision == revision,
        jobs_before,
        jobs_after,
    );
    eprintln!("pointer sweep at 4x, After: {} ms per frame", stats(plain4));
    eprintln!("split line drag at 4x: {} ms per frame", stats(split4));
    eprintln!(
        "split at 4x moved 0.10 -> {split4_end:.2}; revision unchanged {}; viewport jobs {:?} -> {:?}",
        app.editor.revision == revision,
        jobs4,
        jobs4_end
    );
}

#[path = "app-station-develop-actions-tests.rs"]
mod actions;

#[path = "app-station-develop-split-tests.rs"]
mod split;
