//! The Studio 2 frame, exercised through its real controls (plan 10.1).
use super::*;
use crate::jobs::FrameFile;
use egui::containers::panel::PanelState;

const SIZE: egui::Vec2 = egui::vec2(1680.0, 1050.0);

fn app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = crate::workspace_history::Catalog::default();
    app.stack = Some(StackScan {
        directory: PathBuf::from("shell-bracket"),
        frames: (0..13)
            .map(|index| FrameFile {
                path: PathBuf::from(format!("shell-{index}.arw")),
                bytes: 42,
            })
            .collect(),
        total_bytes: 546,
    });
    app
}

fn context() -> egui::Context {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    ctx
}

/// One frame of the shell as `update_workspace` draws it, without the
/// polls, so no worker or camera connection starts.
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
            app.undo_shortcuts(ctx);
            app.shell_shortcuts(ctx);
            app.shell_bars(ctx);
            app.workspace(ctx);
            app.shell_overlays(ctx);
            crate::window_chrome::finish_with(ctx, app.picker_active(), 1.0);
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
fn press(at: egui::Pos2, pressed: bool) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(at),
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        },
    ]
}
fn click(app: &mut StrehlApp, ctx: &egui::Context, at: egui::Pos2, time: f64) -> egui::FullOutput {
    frame(app, ctx, time, press(at, true));
    frame(app, ctx, time + 0.02, press(at, false))
}
fn key(key: egui::Key, modifiers: egui::Modifiers) -> Vec<egui::Event> {
    vec![egui::Event::Key {
        key,
        physical_key: Some(key),
        pressed: true,
        repeat: false,
        modifiers,
    }]
}
fn panel(ctx: &egui::Context, id: &str) -> Option<egui::Rect> {
    PanelState::load(ctx, egui::Id::new(id)).map(|state| state.rect)
}
fn assert_rect(actual: Option<egui::Rect>, expected: [f32; 4], what: &str) {
    let actual = actual.unwrap_or_else(|| panic!("{what} was not drawn"));
    let got = [actual.left(), actual.top(), actual.width(), actual.height()];
    for (a, e) in got.iter().zip(expected) {
        assert!(
            (a - e).abs() <= 2.0,
            "{what}: {got:?}, reference {expected:?}"
        );
    }
}

#[test]
fn every_route_matches_the_reference_chrome_rectangles() {
    // metrics.json at 1680 x 1050: top 44, hint 24, inspector 348 from x 1332,
    // control strip 36 under the top bar.
    for route in [
        LaunchRoute::Library,
        LaunchRoute::Stack,
        LaunchRoute::Engine,
        LaunchRoute::Develop,
        LaunchRoute::Export,
    ] {
        let ctx = context();
        let mut app = app();
        app.apply_launch_route(route);
        for time in 0..3 {
            frame(&mut app, &ctx, time as f64 * 0.05, vec![]);
        }
        assert_rect(
            panel(&ctx, "studio-top"),
            [0.0, 0.0, 1680.0, 44.0],
            "top bar",
        );
        assert_rect(
            panel(&ctx, "studio-hints"),
            [0.0, 1026.0, 1680.0, 24.0],
            "hint bar",
        );
        let station = app.shell.navigator.station();
        let room = app.shell.navigator.route().room();
        if matches!(station, Station::Stack | Station::Develop | Station::Export)
            && room != Some(Room::Engine)
        {
            assert_rect(
                panel(&ctx, "studio-inspector"),
                [1332.0, 44.0, 348.0, 982.0],
                "inspector",
            );
            assert_rect(
                panel(&ctx, "studio-control-strip"),
                [0.0, 44.0, 1332.0, 36.0],
                "control strip",
            );
        }
        if station == Station::Library {
            let nav = panel(&ctx, "library-nav").expect("the Library's left pane");
            assert_eq!((nav.left(), nav.top()), (0.0, 44.0));
        }
    }
}

#[test]
fn the_stations_navigate_and_every_existing_pane_stays_reachable() {
    let ctx = context();
    let mut app = app();
    frame(&mut app, &ctx, 0.0, vec![]);
    let mut time = 0.1;
    for (label, pane) in [
        ("STACK", workspace::Sidebar::Adjust),
        ("DEVELOP", workspace::Sidebar::Edit),
        ("EXPORT", workspace::Sidebar::Export),
        ("LIBRARY", workspace::Sidebar::Projects),
    ] {
        let out = frame(&mut app, &ctx, time, vec![]);
        let at = find(&out, label).expect("station label").center();
        assert!(at.y < 44.0, "{label} is in the top bar");
        click(&mut app, &ctx, at, time + 0.05);
        assert_eq!(app.sidebar, Some(pane), "{label} opens its pane");
        assert!(app.process_view);
        let out = frame(&mut app, &ctx, time + 0.1, vec![]);
        // The open station carries the amber rule under its label.
        let rule = out.shapes.iter().any(|s| {
            matches!(&s.shape,
            egui::Shape::Rect(r) if r.fill == studio_theme::GRAPHITE.accent
                && r.rect.height() == 2.0 && r.rect.bottom() == 44.0
                && r.rect.left() < at.x && r.rect.right() > at.x)
        });
        assert!(rule, "{label} is marked as the open station");
        time += 0.2;
    }
    // Review is the Stack inspector's second tab.
    app.go_station(Station::Stack);
    let out = frame(&mut app, &ctx, time, vec![]);
    click(
        &mut app,
        &ctx,
        find(&out, "REVIEW").unwrap().center(),
        time + 0.05,
    );
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Review));
    // Agent opens over the station from the brand menu; Close returns.
    let out = frame(&mut app, &ctx, time + 0.2, vec![]);
    click(
        &mut app,
        &ctx,
        find(&out, "STREHL").unwrap().center(),
        time + 0.25,
    );
    frame(&mut app, &ctx, time + 0.3, vec![]);
    let menu = frame(&mut app, &ctx, time + 0.32, vec![]);
    click(
        &mut app,
        &ctx,
        find(&menu, "Agent").expect("brand menu").center(),
        time + 0.35,
    );
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Agent));
    assert_eq!(
        app.shell.navigator.station(),
        Station::Stack,
        "a drawer keeps the station"
    );
    let out = frame(&mut app, &ctx, time + 0.5, vec![]);
    click(
        &mut app,
        &ctx,
        find(&out, "Close").unwrap().center(),
        time + 0.55,
    );
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Review));
}

/// Open a top-bar popover and return the first frame that shows it (egui
/// lays a new popup out invisibly once).
fn open(app: &mut StrehlApp, ctx: &egui::Context, at: egui::Pos2, time: f64) -> egui::FullOutput {
    click(app, ctx, at, time);
    frame(app, ctx, time + 0.04, vec![]);
    frame(app, ctx, time + 0.06, vec![])
}

#[test]
fn opening_the_activity_tray_closes_the_rig_popover_and_the_reverse() {
    let ctx = context();
    let mut app = app();
    let out = frame(&mut app, &ctx, 0.0, vec![]);
    let rig = find(&out, "Rig").expect("rig status").center();
    let activity = find(&out, "Nothing running")
        .expect("activity status")
        .center();
    let opened = open(&mut app, &ctx, rig, 0.1);
    assert!(
        find(&opened, "Camera host").is_some(),
        "the rig popover opens"
    );
    let tray = open(&mut app, &ctx, activity, 0.2);
    assert!(find(&tray, "NOTICES").is_some(), "the tray opens");
    assert!(
        find(&tray, "Camera host").is_none(),
        "and the rig popover closes"
    );
    let rig_again = open(&mut app, &ctx, rig, 0.3);
    assert!(find(&rig_again, "Camera host").is_some());
    assert!(find(&rig_again, "NOTICES").is_none());
    frame(
        &mut app,
        &ctx,
        0.4,
        key(egui::Key::Escape, egui::Modifiers::NONE),
    );
    let closed = frame(&mut app, &ctx, 0.45, vec![]);
    assert!(
        find(&closed, "Camera host").is_none(),
        "Escape closes popovers"
    );
}

#[test]
fn ctrl_k_f_and_e_do_what_the_hint_bar_says() {
    let ctx = context();
    let mut app = app();
    app.go_station(Station::Stack);
    frame(&mut app, &ctx, 0.0, vec![]);
    frame(
        &mut app,
        &ctx,
        0.05,
        key(egui::Key::K, egui::Modifiers::COMMAND),
    );
    assert!(app.shell.palette.is_open());
    frame(&mut app, &ctx, 0.1, vec![]);
    let out = frame(&mut app, &ctx, 0.15, vec![]);
    assert!(
        find(&out, "Engine room").is_some(),
        "the palette lists commands"
    );
    frame(
        &mut app,
        &ctx,
        0.2,
        key(egui::Key::Escape, egui::Modifiers::NONE),
    );
    assert!(!app.shell.palette.is_open());
    frame(
        &mut app,
        &ctx,
        0.3,
        key(egui::Key::E, egui::Modifiers::NONE),
    );
    assert_eq!(app.shell.navigator.route().room(), Some(Room::Engine));
    assert_eq!(app.sidebar, None, "the engine room has the whole canvas");
    frame(
        &mut app,
        &ctx,
        0.4,
        key(egui::Key::E, egui::Modifiers::NONE),
    );
    assert_eq!(app.shell.navigator.route().room(), Some(Room::Photograph));
    frame(
        &mut app,
        &ctx,
        0.5,
        key(egui::Key::F, egui::Modifiers::NONE),
    );
    assert!(app.shell.focus);
    let focused = frame(&mut app, &ctx, 0.55, vec![]);
    assert!(
        find(&focused, "LIBRARY").is_none(),
        "focus mode gives the canvas the window"
    );
    frame(
        &mut app,
        &ctx,
        0.6,
        key(egui::Key::Escape, egui::Modifiers::NONE),
    );
    assert!(!app.shell.focus, "Escape leaves focus mode");
}

#[test]
fn focus_mode_floats_the_inspector_and_fades_it_without_relayout() {
    let ctx = context();
    let mut app = app();
    app.go_station(Station::Stack);
    frame(&mut app, &ctx, 0.0, vec![]);
    app.shell.focus = true;
    frame(
        &mut app,
        &ctx,
        0.1,
        vec![egui::Event::PointerMoved(egui::pos2(800.0, 500.0))],
    );
    let moved = frame(&mut app, &ctx, 0.3, vec![]);
    let tab = find(&moved, "ADJUST").expect("the inspector floats while the pointer moves");
    // Two seconds without motion: the panel fades out.
    for step in 0..8 {
        frame(&mut app, &ctx, 2.2 + step as f64 * 0.05, vec![]);
    }
    let still = frame(&mut app, &ctx, 2.8, vec![]);
    assert!(
        find(&still, "ADJUST").is_none(),
        "it fades after two seconds"
    );
    frame(
        &mut app,
        &ctx,
        2.9,
        vec![egui::Event::PointerMoved(egui::pos2(810.0, 500.0))],
    );
    frame(&mut app, &ctx, 3.2, vec![]);
    let shown = frame(&mut app, &ctx, 3.3, vec![]);
    assert_eq!(
        find(&shown, "ADJUST"),
        Some(tab),
        "the same place: one alpha, no relayout"
    );
}

#[test]
fn station_marks_reserve_their_slots_so_labels_never_move() {
    let ctx = context();
    let mut app = app();
    app.go_station(Station::Library);
    let without = frame(&mut app, &ctx, 0.0, vec![]);
    app.progress.mark_complete();
    app.result = Some(PathBuf::from("shell-result.tiff"));
    let with = frame(&mut app, &ctx, 0.1, vec![]);
    for label in ["LIBRARY", "CAPTURE", "STACK", "DEVELOP", "EXPORT"] {
        assert_eq!(find(&without, label), find(&with, label), "{label} moved");
    }
    // A finished render marks Stack fine.
    let stack = find(&with, "STACK").unwrap();
    let mark = with.shapes.iter().any(|s| {
        matches!(&s.shape,
        egui::Shape::Circle(c) if c.fill == studio_theme::GRAPHITE.ok
            && (c.center.y - stack.center().y).abs() < 2.0 && c.center.x > stack.right())
    });
    assert!(mark, "Stack shows a filled circle");
}

#[test]
fn a_new_error_becomes_the_top_bars_failure_until_the_tray_is_read() {
    let ctx = context();
    let mut app = app();
    frame(&mut app, &ctx, 0.0, vec![]);
    app.error = Some("The stacking engine stopped".into());
    app.observe_notices();
    let out = frame(&mut app, &ctx, 0.1, vec![]);
    let failure = find(&out, "The stacking engine stopped").expect("the failure is in the top bar");
    assert!(failure.bottom() <= 44.0);
    let diamond = out.shapes.iter().any(|s| {
        matches!(&s.shape,
        egui::Shape::Path(p) if p.points.len() == 4 && p.fill == studio_theme::GRAPHITE.bad)
    });
    assert!(diamond, "failures carry the diamond, drawn");
    let tray = open(&mut app, &ctx, failure.center(), 0.2);
    assert!(
        find(&tray, "NOTICES").is_some(),
        "the failure opens the tray"
    );
    let after = frame(&mut app, &ctx, 0.4, vec![]);
    assert!(
        !texts(&after)
            .iter()
            .any(|(text, rect)| text == "The stacking engine stopped" && rect.bottom() <= 44.0),
        "read, it leaves the top bar"
    );
    // The legacy error string stays; the snapshot gains additive keys.
    assert_eq!(app.error.as_deref(), Some("The stacking engine stopped"));
    let keys = app.studio_snapshot();
    assert_eq!(
        keys.iter().map(|(key, _)| *key).collect::<Vec<_>>(),
        ["route", "notices", "activities"]
    );
    assert_eq!(keys[0].1["key"], "library");
    assert_eq!(keys[1].1[0]["severity"], "failure");
    assert!(keys[2].1["current"].as_array().unwrap().is_empty());
    assert_eq!(keys[2].1["queue_paused"], false);
}

#[test]
fn tick_owns_the_side_effects_painting_used_to_have() {
    let mut app = app();
    let ctx = context();
    app.editor.tool = crate::edit_workspace::DrawingTool::Select;
    let _ = ctx.run(egui::RawInput::default(), |ctx| app.tick(ctx));
    assert_eq!(
        app.editor.tool,
        crate::edit_workspace::DrawingTool::Navigate,
        "outside Develop the editor returns to navigation without painting"
    );
    // The recipe is saved by the next tick, not during paint.
    app.ensure_project_stack();
    let id = app.active_stack.unwrap();
    let workers = |app: &StrehlApp| {
        app.catalog
            .node(id)
            .unwrap()
            .stack
            .as_ref()
            .unwrap()
            .workers
    };
    let before = workers(&app);
    app.controls.workers = before + 1;
    app.after_pane(true, true, None);
    assert_eq!(workers(&app), before);
    let _ = ctx.run(egui::RawInput::default(), |ctx| app.tick(ctx));
    assert_eq!(workers(&app), before + 1);
}

#[test]
fn an_open_palette_builds_its_index_once_and_pointer_motion_rebuilds_nothing() {
    let ctx = context();
    let mut app = app();
    for name in ["Blue weevil", "Net-patterned beetle", "Star sand"] {
        let project = app.catalog.create_project(name).unwrap();
        app.catalog.selected = Some(project);
    }
    frame(&mut app, &ctx, 0.0, vec![]);
    frame(
        &mut app,
        &ctx,
        0.05,
        key(egui::Key::K, egui::Modifiers::COMMAND),
    );
    for step in 0..20 {
        frame(
            &mut app,
            &ctx,
            0.1 + step as f64 * 0.02,
            vec![egui::Event::PointerMoved(egui::pos2(
                200.0 + step as f32 * 7.0,
                400.0,
            ))],
        );
    }
    assert_eq!(
        app.shell.palette.builds, 1,
        "pointer motion rebuilt the index"
    );
    app.persist_catalog();
    frame(&mut app, &ctx, 0.6, vec![]);
    assert_eq!(
        app.shell.palette.builds, 2,
        "a catalog change rebuilds it once"
    );
    frame(&mut app, &ctx, 0.65, vec![]);
    assert_eq!(app.shell.palette.builds, 2);
}

#[test]
fn the_palettes_rig_status_opens_the_real_rig_popover() {
    let ctx = context();
    let mut app = app();
    frame(&mut app, &ctx, 0.0, vec![]);
    app.run_palette_command(&ctx, crate::command_palette::Command::Rig);
    frame(&mut app, &ctx, 0.05, vec![]);
    let shown = frame(&mut app, &ctx, 0.1, vec![]);
    assert!(find(&shown, "Camera host").is_some());
}

/// Chrome cost with a large catalog: top bar, hint bar and an inspector over
/// an empty canvas, while the pointer sweeps the top bar. Not a GPU frame rate.
#[test]
#[ignore = "explicit CPU paint+tessellation benchmark of the Studio 2 chrome"]
fn benchmark_shell_chrome_with_a_large_catalog() {
    let ctx = context();
    let mut app = app();
    app.stack = None;
    for project in 0..40 {
        let id = app
            .catalog
            .create_project(&format!("Collection {project}"))
            .unwrap();
        for folder in 0..10 {
            app.catalog
                .create_folder(id, &format!("Subject {project}-{folder}"))
                .unwrap();
        }
    }
    app.go_station(Station::Export);
    for step in 0..10 {
        frame(&mut app, &ctx, step as f64 * 0.01, vec![]);
    }
    let mut times = Vec::new();
    for round in 0..5 {
        let started = std::time::Instant::now();
        for step in 0..120 {
            let x = 100.0 + (step as f32 / 119.0) * 1400.0;
            let output = frame(
                &mut app,
                &ctx,
                1.0 + round as f64 + step as f64 / 120.0,
                vec![egui::Event::PointerMoved(egui::pos2(x, 22.0))],
            );
            std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
        }
        times.push(started.elapsed().as_secs_f64() * 1000.0 / 120.0);
    }
    eprintln!(
        "studio chrome, {} catalog nodes: {:.3?} ms per frame (paint + tessellation)",
        app.catalog.nodes.len(),
        times
    );
}
