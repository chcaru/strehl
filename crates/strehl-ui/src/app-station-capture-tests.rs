//! The Capture station in the shell: its slots, fixtures, naming, the rig
//! popover's confirmations, and performance on pointer motion.
use super::*;
use std::time::Instant;

const SIZE: egui::Vec2 = egui::vec2(1680.0, 1050.0);

/// A shell on the Capture station showing `fixture`; nothing connects.
fn station(fixture: &str) -> (tempfile::TempDir, StrehlApp) {
    let dir = tempfile::tempdir().unwrap();
    let launch = LaunchOptions {
        capture_settings: Some(dir.path().join("capture.json")),
        capture_fixture: Some(fixture.into()),
        route: crate::app::studio_route::LaunchRoute::parse("capture"),
        ..LaunchOptions::default()
    };
    let mut app = StrehlApp::from_launch(4096, launch);
    app.catalog = crate::workspace_history::Catalog::default();
    (dir, app)
}

fn context() -> egui::Context {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    ctx
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}

/// One frame as the window draws it, the shell's tick included (a fixture
/// connection sends and receives nothing).
fn frame(app: &mut StrehlApp, ctx: &egui::Context, events: Vec<egui::Event>) -> egui::FullOutput {
    let time = CLOCK.with(|c| {
        c.set(c.get() + 1.0 / 60.0);
        c.get()
    });
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, SIZE)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.tick(ctx);
            app.sync_route();
            app.shell_shortcuts(ctx);
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

fn find(output: &egui::FullOutput, needle: &str) -> Option<egui::Rect> {
    texts(output)
        .into_iter()
        .find(|(text, _)| text == needle)
        .map(|(_, rect)| rect)
}

/// The plan fills the shell's slots where the mockup puts them: the strip
/// under the top bar, the rail above the hint bar, the plan in the 348 px
/// inspector from its top (no tabs), and the station's keys in the hint bar.
#[test]
fn the_plan_fills_the_shells_slots() {
    let ctx = context();
    let (_dir, mut app) = station("plan");
    frame(&mut app, &ctx, vec![]);
    let out = frame(&mut app, &ctx, vec![]);
    let strip = find(&out, "PRE-FLIGHT").expect("the pre-flight strip");
    assert!((44.0..80.0).contains(&strip.center().y), "{strip:?}");
    let rail = find(&out, "DEPTH RAIL").expect("the rail");
    assert!((891.0..921.0).contains(&rail.center().y), "{rail:?}");
    let subject = find(&out, "SUBJECT").expect("the plan starts at the top");
    assert!(
        subject.left() >= 1332.0 && subject.top() < 70.0,
        "{subject:?}"
    );
    let start = find(&out, "Start stack").expect("Start stack");
    assert!(start.left() > 1332.0 && start.top() > 960.0, "{start:?}");
    assert!(find(&out, "Ready").is_some(), "the fixture's plan is ready");
    assert!(
        find(&out, "mark start").is_some(),
        "the hint bar has the station's keys"
    );
    assert!(find(&out, "estimate, not the RAW").is_some());
}

/// The capture in flight has no strip; glance covers the window and Escape
/// returns.
#[test]
fn flight_and_glance_fill_the_window() {
    let ctx = context();
    let (_dir, mut app) = station("flight");
    frame(&mut app, &ctx, vec![]);
    let out = frame(&mut app, &ctx, vec![]);
    assert!(find(&out, "PRE-FLIGHT").is_none());
    let plane = find(&out, "PLANE").expect("the headline");
    assert!(
        plane.top() < 80.0,
        "the canvas starts under the top bar: {plane:?}"
    );
    assert!(find(&out, "of 96").is_some());
    assert!(find(&out, "Glance").is_some());
    assert_eq!(
        app.capture.status_line().as_deref(),
        Some("Capturing 61 / 96 planes · 00:03:18 left")
    );
    // The top bar and the tray read the capture's activity report.
    let mut activities = crate::activity::Activities::default();
    activities.begin();
    app.capture.report_activities(&mut activities);
    let capture = activities
        .statuses()
        .iter()
        .find(|s| s.kind == crate::activity::ActivityKind::Capture)
        .expect("the capture reports an activity");
    assert_eq!(
        capture.progress_line(std::time::Instant::now()),
        "Capturing · 61 / 96 · 3 min 18 s left"
    );
    let (_dir, mut app) = station("glance");
    frame(&mut app, &ctx, vec![]);
    let out = frame(&mut app, &ctx, vec![]);
    assert!(find(&out, "Esc to return").is_some());
    let escape = egui::Event::Key {
        key: egui::Key::Escape,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    };
    frame(&mut app, &ctx, vec![escape]);
    let out = frame(&mut app, &ctx, vec![]);
    assert!(find(&out, "Esc to return").is_none());
    assert!(
        find(&out, "of 96").is_some(),
        "back to the capture in flight"
    );
}

/// A finished capture lands in the plan's subject (found, or created in
/// the selected project) under the plan's stack name; without names it
/// takes P4's default.
#[test]
fn a_finished_capture_lands_in_its_subject() {
    let (_dir, mut app) = station("plan");
    let project = app.catalog.create_project("Macro").unwrap();
    app.catalog.selected = Some(project);
    let run = PathBuf::from("D:/Captures/stack-1794000000000-1");
    app.capture
        .remember_names(run.clone(), "Blue weevil".into(), "Dorsal".into());
    app.capture_names(&run);
    let subject = app.capture_parent.expect("a subject");
    let node = app.catalog.node(subject).unwrap();
    assert_eq!(
        (node.name.as_str(), node.kind, node.parent),
        ("Blue weevil", NodeKind::Subject, Some(project))
    );
    assert_eq!(app.session_ui.pending_name.as_deref(), Some("Dorsal"));
    // The same name again finds the subject rather than founding another.
    app.capture_parent = None;
    app.capture
        .remember_names(run.clone(), "blue WEEVIL".into(), String::new());
    app.capture_names(&run);
    assert_eq!(app.capture_parent, Some(subject));
    assert_eq!(
        app.session_ui.pending_name.as_deref(),
        Some("stack-1794000000000-1"),
        "no stack name: P4's default for the folder"
    );
    let subjects = app
        .catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject)
        .count();
    assert_eq!(subjects, 1);
    // With nothing selected, new subjects share one "Captures" project.
    app.catalog.selected = None;
    for name in ["Moth", "Ant"] {
        app.capture
            .remember_names(run.clone(), name.into(), String::new());
        app.capture_names(&run);
    }
    let captures: Vec<_> = app
        .catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Project && n.name == "Captures")
        .map(|n| n.id)
        .collect();
    assert_eq!(captures.len(), 1);
    let ant = app.catalog.node(app.capture_parent.unwrap()).unwrap();
    assert_eq!((ant.name.as_str(), ant.parent), ("Ant", Some(captures[0])));
}

/// The rig popover's Shut down and Disconnect ask first; Light does not.
#[test]
fn the_rig_popover_asks_before_the_camera_goes() {
    use strehl_capture::{power::Outlet, session::Command};
    let (_dir, mut app) = station("plan");
    assert!(app.capture_needs_confirm(&Command::Power {
        device: Outlet::Camera,
        on: false
    }));
    assert_eq!(app.capture.confirm, Some(Confirm::ShutDown));
    assert!(app.capture_needs_confirm(&Command::Disconnect {}));
    assert_eq!(app.capture.confirm, Some(Confirm::Disconnect));
    assert!(!app.capture_needs_confirm(&Command::Power {
        device: Outlet::Light,
        on: false
    }));
}

/// Milliseconds per frame over `steps` frames, and the last frame's vertices.
fn sweep(app: &mut StrehlApp, ctx: &egui::Context, steps: usize) -> (f64, usize) {
    let start = Instant::now();
    let mut vertices = 0;
    for step in 0..steps {
        let f = step as f32 / (steps - 1) as f32;
        // Across the live view, then along the rail.
        let at = if step % 2 == 0 {
            egui::pos2(120.0 + 1100.0 * f, 300.0 + 300.0 * f)
        } else {
            egui::pos2(40.0 + 1250.0 * f, 980.0)
        };
        let out = frame(app, ctx, vec![egui::Event::PointerMoved(at)]);
        let primitives = ctx.tessellate(out.shapes, out.pixels_per_point);
        vertices = primitives
            .iter()
            .map(|p| match &p.primitive {
                egui::epaint::Primitive::Mesh(mesh) => mesh.vertices.len(),
                _ => 0,
            })
            .sum();
        std::hint::black_box(primitives);
    }
    (
        start.elapsed().as_secs_f64() * 1000.0 / steps as f64,
        vertices,
    )
}

/// Spec 5.2: pointer motion over the live view and the rail builds no mesh
/// and uploads no texture.
#[test]
fn pointer_motion_over_the_station_rebuilds_nothing() {
    let ctx = context();
    let (_dir, mut app) = station("plan");
    for _ in 0..3 {
        frame(&mut app, &ctx, vec![]);
    }
    let before = app.capture.station_counters();
    sweep(&mut app, &ctx, 24);
    assert_eq!(app.capture.station_counters(), before);
}

/// The station's CPU paint and tessellation per frame on a pointer sweep:
/// `cargo test --release -p strehl-ui capture_station_pointer_sweeps -- --ignored --nocapture`.
#[test]
#[ignore = "benchmark: prints ms per frame"]
fn capture_station_pointer_sweeps() {
    let ctx = context();
    // `flight+long`: 5,400 of 6,000 planes checked, hundreds retaken.
    for fixture in ["plan", "flight", "flight+long"] {
        let (_dir, mut app) = station(fixture);
        for _ in 0..5 {
            frame(&mut app, &ctx, vec![]);
        }
        let runs: Vec<(f64, usize)> = (0..6).map(|_| sweep(&mut app, &ctx, 80)).collect();
        let ms: Vec<f64> = runs.iter().map(|r| r.0).collect();
        println!(
            "capture_{fixture}_cpu_ms_per_frame {ms:?} min={:.3} final_vertices={}",
            ms.iter().copied().fold(f64::INFINITY, f64::min),
            runs[5].1
        );
    }
}

/// The in-flight canvas's CPU cost with the pointer over the planes' feed
/// and the wheel scrolling it, on the 61-plane fixture and on the long run:
/// `cargo test --release -p strehl-ui capture_flight_feed_sweeps -- --ignored --nocapture`.
#[test]
#[ignore = "benchmark: prints ms per frame"]
fn capture_flight_feed_sweeps() {
    let ctx = context();
    for fixture in ["flight", "flight+long"] {
        let (_dir, mut app) = station(fixture);
        for _ in 0..5 {
            frame(&mut app, &ctx, vec![]);
        }
        let mut runs = Vec::new();
        for _ in 0..6 {
            let start = Instant::now();
            let mut vertices = 0;
            let steps = 80;
            for step in 0..steps {
                let f = step as f32 / (steps - 1) as f32;
                // Down the side column, scrolling back and forth.
                let at = egui::pos2(1150.0 + 120.0 * f, 450.0 + 400.0 * f);
                let delta = if (step / 10) % 2 == 0 { -60.0 } else { 60.0 };
                let out = frame(
                    &mut app,
                    &ctx,
                    vec![
                        egui::Event::PointerMoved(at),
                        egui::Event::MouseWheel {
                            unit: egui::MouseWheelUnit::Point,
                            delta: egui::vec2(0.0, delta),
                            modifiers: Default::default(),
                        },
                    ],
                );
                let primitives = ctx.tessellate(out.shapes, out.pixels_per_point);
                vertices = primitives
                    .iter()
                    .map(|p| match &p.primitive {
                        egui::epaint::Primitive::Mesh(mesh) => mesh.vertices.len(),
                        _ => 0,
                    })
                    .sum();
                std::hint::black_box(primitives);
            }
            runs.push((
                start.elapsed().as_secs_f64() * 1000.0 / steps as f64,
                vertices,
            ));
        }
        let ms: Vec<f64> = runs.iter().map(|r| r.0).collect();
        println!(
            "capture_{fixture}_feed_cpu_ms_per_frame {ms:?} min={:.3} final_vertices={}",
            ms.iter().copied().fold(f64::INFINITY, f64::min),
            runs[5].1
        );
    }
}

fn color_of(output: &egui::FullOutput, needle: &str) -> Option<egui::Color32> {
    fn walk(shape: &egui::Shape, needle: &str) -> Option<egui::Color32> {
        match shape {
            egui::Shape::Text(text) if text.galley.text() == needle => {
                Some(text.galley.job.sections[0].format.color)
            }
            egui::Shape::Vec(parts) => parts.iter().find_map(|part| walk(part, needle)),
            _ => None,
        }
    }
    output
        .shapes
        .iter()
        .find_map(|shape| walk(&shape.shape, needle))
}

/// The station takes the shell's theme: on Lightbox the canvas's text uses
/// the canvas inks (light on the dark surround) and the inspector's the
/// panel inks; Graphite and Instrument draw both with their own inks.
#[test]
fn the_station_follows_all_three_themes() {
    use crate::studio_theme::ThemeName;
    for theme in [
        ThemeName::Graphite,
        ThemeName::Instrument,
        ThemeName::Lightbox,
    ] {
        let ctx = context();
        let (dir, _) = station("flight");
        let launch = LaunchOptions {
            capture_settings: Some(dir.path().join("capture.json")),
            capture_fixture: Some("flight".into()),
            route: crate::app::studio_route::LaunchRoute::parse("capture"),
            theme: Some(theme),
            ..LaunchOptions::default()
        };
        let mut app = StrehlApp::from_launch(4096, launch);
        frame(&mut app, &ctx, vec![]);
        let out = frame(&mut app, &ctx, vec![]);
        let t = crate::studio_theme::tokens(&ctx);
        let canvas = color_of(&out, "of 96").expect("the headline");
        assert!(t.canvas_ink.contains(&canvas), "{theme:?}: {canvas:?}");
        let panel = color_of(&out, "Transfer").expect("the inspector");
        assert!(
            [t.ink, t.ink2, t.ink3].contains(&panel),
            "{theme:?}: {panel:?}"
        );
        if theme == ThemeName::Lightbox {
            assert_ne!(canvas, panel, "dark canvas, light inspector");
        }
    }
}

/// The plane view through the production GPU path (h-proof): an offscreen
/// egui-wgpu target and the offscreen presenter, so tiles are uploaded and
/// registered on the plane view's workers as in the window. Frames are paced
/// at 60 Hz while the view steps a plane a second (each step a full build,
/// as a plane arriving is), at fit, at 100 % and while panning at 100 %.
/// Prints the UI thread's time a frame (egui, tessellation, buffers,
/// submit) and until the GPU is done, the builds and the process's CPU.
///
/// `STREHL_BENCH_FIXTURE` (default `flight`; `flight+long` is 5,400 planes)
/// and `STREHL_BENCH_SIZE` (default `1680x1050`); with `STREHL_FIXTURE_RUN`
/// and `STREHL_FIXTURE_JOURNAL` the planes are a real run's RAWs, and with
/// `STREHL_FIXTURE_REPLAY_MS` they arrive at that pace while the view
/// follows (`STREHL_BENCH_SECONDS` a phase, no stepping):
/// `cargo test --release -p strehl-ui capture_plane_view_frames -- --ignored --nocapture`.
#[test]
#[ignore = "benchmark: needs a GPU"]
fn capture_plane_view_frames() {
    use eframe::egui_wgpu;
    use std::time::Duration;
    fn block_on<T>(future: impl std::future::Future<Output = T>) -> T {
        struct Wake(std::thread::Thread);
        impl std::task::Wake for Wake {
            fn wake(self: std::sync::Arc<Self>) {
                self.0.unpark();
            }
        }
        let waker = std::task::Waker::from(std::sync::Arc::new(Wake(std::thread::current())));
        let mut task = std::task::Context::from_waker(&waker);
        let mut future = std::pin::pin!(future);
        loop {
            match future.as_mut().poll(&mut task) {
                std::task::Poll::Ready(value) => return value,
                std::task::Poll::Pending => std::thread::park_timeout(Duration::from_millis(1)),
            }
        }
    }
    #[cfg(windows)]
    fn cpu_seconds() -> f64 {
        use windows_sys::Win32::Foundation::FILETIME;
        use windows_sys::Win32::System::Threading::{GetCurrentProcess, GetProcessTimes};
        let zero = FILETIME {
            dwLowDateTime: 0,
            dwHighDateTime: 0,
        };
        let (mut a, mut b, mut k, mut u) = (zero, zero, zero, zero);
        // SAFETY: the current process's pseudo-handle and four out-params.
        unsafe { GetProcessTimes(GetCurrentProcess(), &mut a, &mut b, &mut k, &mut u) };
        let t = |f: FILETIME| {
            ((u64::from(f.dwHighDateTime) << 32) | u64::from(f.dwLowDateTime)) as f64 * 1e-7
        };
        t(k) + t(u)
    }
    #[cfg(not(windows))]
    fn cpu_seconds() -> f64 {
        0.0
    }
    /// This thread's CPU cycles and the process's page faults so far: a
    /// slow step that ran (cycles) differs from one that waited.
    #[cfg(windows)]
    fn cycles_and_faults() -> (u64, u32) {
        #[link(name = "kernel32")]
        unsafe extern "system" {
            fn GetCurrentThread() -> *mut std::ffi::c_void;
            fn QueryThreadCycleTime(thread: *mut std::ffi::c_void, cycles: *mut u64) -> i32;
            fn GetCurrentProcess() -> *mut std::ffi::c_void;
            fn K32GetProcessMemoryInfo(
                process: *mut std::ffi::c_void,
                counters: *mut [u32; 20],
                size: u32,
            ) -> i32;
        }
        let mut cycles = 0u64;
        let mut counters = [0u32; 20];
        // SAFETY: pseudo-handles and out-params of the documented sizes
        // (PROCESS_MEMORY_COUNTERS: cb, PageFaultCount, then sizes).
        unsafe {
            QueryThreadCycleTime(GetCurrentThread(), &mut cycles);
            counters[0] = 72;
            K32GetProcessMemoryInfo(GetCurrentProcess(), &mut counters, 72);
        }
        (cycles, counters[1])
    }
    #[cfg(not(windows))]
    fn cycles_and_faults() -> (u64, u32) {
        (0, 0)
    }
    // Slow frames' spans, matched with the workers' steps after each phase
    // (a step is recorded when it ends).
    static SLOW: std::sync::Mutex<Vec<(Instant, Instant)>> = std::sync::Mutex::new(Vec::new());
    let meanwhile = || {
        let slow = std::mem::take(&mut *SLOW.lock().unwrap());
        let trace = crate::capture_workspace::planes::TRACE.lock().unwrap();
        for (a, b) in slow {
            let during: Vec<String> = trace
                .iter()
                .filter(|(s, e, _)| *e >= a && *s <= b)
                .map(|(s, e, w)| format!("{w} {:.0} ms", (*e - *s).as_secs_f64() * 1000.0))
                .collect();
            println!(
                "    {:.1} ms frame; workers meanwhile: {during:?}",
                (b - a).as_secs_f64() * 1000.0
            );
        }
    };
    let fixture = std::env::var("STREHL_BENCH_FIXTURE").unwrap_or_else(|_| "flight".into());
    let size: [u32; 2] = std::env::var("STREHL_BENCH_SIZE")
        .ok()
        .and_then(|s| {
            let (w, h) = s.split_once('x')?;
            Some([w.parse().ok()?, h.parse().ok()?])
        })
        .unwrap_or([1680, 1050]);
    let config = crate::hdr_display::configuration();
    let instance = block_on(config.wgpu_setup.new_instance());
    let render = block_on(egui_wgpu::RenderState::create(
        &config,
        &instance,
        None,
        egui_wgpu::RendererOptions::default(),
    ))
    .unwrap();
    println!("adapter: {:?}", render.adapter.get_info().name);
    let canvas = render.device.create_texture(&wgpu::TextureDescriptor {
        label: Some("plane view benchmark"),
        size: wgpu::Extent3d {
            width: size[0],
            height: size[1],
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: render.target_format,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
        view_formats: &[],
    });
    let ctx = context();
    ctx.set_pixels_per_point(1.0);
    let (_dir, mut app) = station(&fixture);
    app.apply_theme(&ctx);
    app.editor.viewport.presenter = Some(crate::hdr_display::PhotoPresenter::offscreen(
        render.clone(),
        ctx.clone(),
    ));
    let started = Instant::now();
    let frame_gpu = |app: &mut StrehlApp, events: Vec<egui::Event>| -> (f64, f64) {
        let began = Instant::now();
        let screen =
            egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(size[0] as f32, size[1] as f32));
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(screen),
                time: Some(started.elapsed().as_secs_f64()),
                predicted_dt: 1.0 / 60.0,
                focused: true,
                events,
                ..Default::default()
            },
            |ctx| app.update_workspace(ctx),
        );
        let ran = began.elapsed();
        // How long the context's lock takes to get (another thread holding
        // it stalls the frame here, not in the tessellator).
        let probe = Instant::now();
        ctx.input(|_| ());
        let lock_ms = probe.elapsed().as_secs_f64() * 1000.0;
        let shapes = output.shapes.len();
        let kept = output.shapes.clone();
        let (c0, f0) = cycles_and_faults();
        let primitives = ctx.tessellate(output.shapes, output.pixels_per_point);
        let tessellated = began.elapsed();
        let (c1, f1) = cycles_and_faults();
        if (tessellated - ran).as_secs_f64() > 0.008 {
            // Which shape: each tessellated alone, the slowest three.
            let mut each: Vec<(f64, String)> = kept
                .iter()
                .map(|s| {
                    let t = Instant::now();
                    let _ = ctx.tessellate(vec![s.clone()], output.pixels_per_point);
                    let kind = match &s.shape {
                        egui::Shape::Vec(v) => format!("Vec of {}", v.len()),
                        egui::Shape::Mesh(m) => format!("Mesh {} vertices", m.vertices.len()),
                        egui::Shape::Text(t) => format!(
                            "Text {:?}",
                            t.galley.text().chars().take(30).collect::<String>()
                        ),
                        other => format!("{:?}", other.visual_bounding_rect()),
                    };
                    (
                        t.elapsed().as_secs_f64() * 1000.0,
                        format!("{kind} clip {:?}", s.clip_rect),
                    )
                })
                .collect();
            each.sort_by(|a, b| b.0.total_cmp(&a.0));
            println!("    slowest shapes: {:?}", &each[..3.min(each.len())]);
        }
        let vertices: usize = primitives
            .iter()
            .map(|p| match &p.primitive {
                egui::epaint::Primitive::Mesh(m) => m.vertices.len(),
                _ => 0,
            })
            .sum();
        let descriptor = egui_wgpu::ScreenDescriptor {
            size_in_pixels: size,
            pixels_per_point: output.pixels_per_point,
        };
        let mut encoder = render.device.create_command_encoder(&Default::default());
        let commands = {
            let mut renderer = render.renderer.write();
            for (id, image) in &output.textures_delta.set {
                renderer.update_texture(&render.device, &render.queue, *id, image);
            }
            renderer.update_buffers(
                &render.device,
                &render.queue,
                &mut encoder,
                &primitives,
                &descriptor,
            )
        };
        let updated = began.elapsed();
        let view = canvas.create_view(&Default::default());
        {
            let pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: None,
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                        store: wgpu::StoreOp::Store,
                    },
                    depth_slice: None,
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            render
                .renderer
                .read()
                .render(&mut pass.forget_lifetime(), &primitives, &descriptor);
        }
        let submission = render
            .queue
            .submit(commands.into_iter().chain([encoder.finish()]));
        for id in &output.textures_delta.free {
            render.renderer.write().free_texture(id);
        }
        let cpu = began.elapsed().as_secs_f64() * 1000.0;
        if cpu > 8.0 {
            SLOW.lock()
                .unwrap()
                .push((began, began + Duration::from_secs_f64(cpu / 1000.0)));
            let ms = |d: Duration| d.as_secs_f64() * 1000.0;
            println!(
                "  slow frame {cpu:.2} ms: egui {:.2}, context lock {lock_ms:.2}, tessellate {:.2} ({shapes} shapes, {vertices} vertices; {} M cycles on this thread, {} process page faults meanwhile), textures+buffers {:.2}, render+submit {:.2}",
                ms(ran),
                ms(tessellated - ran),
                (c1 - c0) / 1_000_000,
                f1.wrapping_sub(f0),
                ms(updated - tessellated),
                cpu - ms(updated)
            );
        }
        render
            .device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(submission),
                timeout: Some(Duration::from_secs(10)),
            })
            .unwrap();
        (cpu, began.elapsed().as_secs_f64() * 1000.0)
    };
    // Settle: every try measured and the newest built.
    let settle = Instant::now();
    let mut warm = 0;
    let unsettled = std::env::var_os("STREHL_BENCH_NO_UPLOAD").is_some()
        || std::env::var_os("STREHL_BENCH_NO_BUILD").is_some();
    while !((unsettled || app.capture.plane_view_settled()) && warm > 30) {
        frame_gpu(&mut app, vec![]);
        warm += 1;
        assert!(settle.elapsed() < Duration::from_secs(240), "never settled");
        std::thread::sleep(Duration::from_millis(16));
    }
    println!(
        "{fixture} {}x{}: settled in {:.1} s ({warm} frames)",
        size[0],
        size[1],
        settle.elapsed().as_secs_f64()
    );
    let key = |k| egui::Event::Key {
        key: k,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    };
    let summary = |label: &str,
                   ui: &mut Vec<f64>,
                   gpu: &mut Vec<f64>,
                   builds: &[f64],
                   cpu: f64,
                   secs: f64| {
        ui.sort_by(f64::total_cmp);
        gpu.sort_by(f64::total_cmp);
        let q = |v: &[f64], p: f64| v[((v.len() - 1) as f64 * p) as usize];
        let built = if builds.is_empty() {
            String::new()
        } else {
            let mut b = builds.to_vec();
            b.sort_by(f64::total_cmp);
            format!(
                ", build median {:.0} ms max {:.0} ms",
                q(&b, 0.5),
                b[b.len() - 1]
            )
        };
        println!(
            "{label}: {} frames; UI ms median {:.2} p99 {:.2} max {:.2}, over 16 ms {}; until GPU done median {:.2} max {:.2}; {} builds{built}; process CPU {:.2} cores over {secs:.0} s",
            ui.len(),
            q(ui, 0.5),
            q(ui, 0.99),
            ui[ui.len() - 1],
            ui.iter().filter(|t| **t > 16.0).count(),
            q(gpu, 0.5),
            gpu[gpu.len() - 1],
            builds.len(),
            cpu / secs,
        );
    };
    let follow = std::env::var_os("STREHL_FIXTURE_REPLAY_MS").is_some();
    let seconds: f64 = std::env::var("STREHL_BENCH_SECONDS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(15.0);
    let phases: [(&str, Option<f32>, bool); 3] = if follow {
        [
            ("following arrivals, fit", None, false),
            ("following arrivals, 100 %", Some(1.0), false),
            ("following arrivals, 100 %, panning", Some(1.0), true),
        ]
    } else {
        [
            ("fit, a plane a second", None, false),
            ("100 %, a plane a second", Some(1.0), false),
            ("100 %, panning, a plane a second", Some(1.0), true),
        ]
    };
    let overlays = std::env::var("STREHL_BENCH_OVERLAYS").map_or(true, |v| v != "0");
    for (label, zoom, pan) in phases {
        {
            let (view, ..) = app.capture.plane_view_parts();
            view.set_zoom(zoom, egui::pos2(0.45, 0.5));
            view.sharp = overlays;
            view.checks = overlays;
        }
        let (mut ui, mut gpu, mut builds) = (Vec::new(), Vec::new(), Vec::new());
        let mut last_id = app.capture.plane_view_parts().1.map_or(0, |i| i.id);
        let cpu0 = cpu_seconds();
        let phase = Instant::now();
        let mut next_step = 0.5;
        let mut n = 0u64;
        while phase.elapsed().as_secs_f64() < seconds {
            let tick = Instant::now();
            let mut events = Vec::new();
            if !follow && phase.elapsed().as_secs_f64() >= next_step {
                events.push(key(egui::Key::ArrowLeft));
                next_step += 1.0;
            }
            if pan {
                let (view, ..) = app.capture.plane_view_parts();
                let x = 0.3 + 0.4 * (0.5 + 0.5 * (n as f32 * 0.02).sin());
                view.set_zoom(zoom, egui::pos2(x, 0.5));
            }
            let (c, g) = frame_gpu(&mut app, events);
            ui.push(c);
            gpu.push(g);
            let (view, _, _, poll) = app.capture.plane_view_parts();
            if c > 8.0 {
                println!(
                    "  slow frame {c:.2} ms: deck poll {poll:.2} ms, panel {:.2} ms",
                    view.paint_ms
                );
            }
            if let (_, Some(image), ..) = app.capture.plane_view_parts()
                && image.id != last_id
            {
                last_id = image.id;
                if image.kind != crate::capture_workspace::planes::ImageKind::Preview {
                    builds.push(image.cost.iter().sum());
                }
            }
            n += 1;
            std::thread::sleep(Duration::from_secs_f64(1.0 / 60.0).saturating_sub(tick.elapsed()));
        }
        let cpu = cpu_seconds() - cpu0;
        summary(label, &mut ui, &mut gpu, &builds, cpu, seconds);
        meanwhile();
        let (_, image, tiles, _) = app.capture.plane_view_parts();
        if let Some(image) = image {
            println!(
                "  shown: plane {} try {} {:?} {}x{}, {} MB of pyramid, {tiles} tiles uploaded, cost {:?} ms",
                image.key.plane,
                image.key.attempt,
                image.kind,
                image.size[0],
                image.size[1],
                image.bytes() / 1_000_000,
                image.cost.map(|c| c.round()),
            );
        }
    }
}
