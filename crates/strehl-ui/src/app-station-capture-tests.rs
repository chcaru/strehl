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
    assert_eq!(app.capture_activity_phase().as_deref(), Some("3:18"));
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
    for fixture in ["plan", "flight"] {
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
