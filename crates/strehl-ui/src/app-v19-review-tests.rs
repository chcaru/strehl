//! Independent end-to-end workspace witnesses: operate the rendered explorer,
//! vary geometry through threshold sizes, and compare saved recipes, not labels.
use super::*;
use crate::workspace_history::{Catalog, Run, StackDraft};

fn isolated_app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Catalog::default();
    app
}
fn paint(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    size: egui::Vec2,
    focused: bool,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, size)),
            focused,
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.status_bar(ctx);
            app.workspace(ctx);
        },
    )
}
fn text_rect(output: &egui::FullOutput, needle: &str) -> Option<egui::Rect> {
    fn find(shape: &egui::Shape, needle: &str) -> Option<egui::Rect> {
        match shape {
            egui::Shape::Text(t) if t.galley.text() == needle => {
                Some(egui::Rect::from_min_size(t.pos, t.galley.size()))
            }
            egui::Shape::Vec(parts) => parts.iter().find_map(|s| find(s, needle)),
            _ => None,
        }
    }
    output.shapes.iter().find_map(|s| find(&s.shape, needle))
}
fn click(app: &mut StrehlApp, ctx: &egui::Context, at: egui::Pos2, time: f64) {
    let pointer = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    paint(
        app,
        ctx,
        egui::vec2(1440.0, 940.0),
        true,
        time,
        vec![egui::Event::PointerMoved(at), pointer(true)],
    );
    paint(
        app,
        ctx,
        egui::vec2(1440.0, 940.0),
        true,
        time + 0.05,
        vec![pointer(false)],
    );
}
fn fixture_run() -> Run {
    serde_json::from_value(serde_json::json!({
        "directory":"review-past-run", "source":"review-capture",
        "output":"review-past-run/photo.tiff", "log":"review-past-run/render.log",
        "label":"Earlier settings", "created":1, "status":"Saved", "frames":2,
        "settings":jobs::RenderSettings::default(), "exposure":null,
        "gate":1.25, "workers":2
    }))
    .unwrap()
}
fn fixture_scan() -> StackScan {
    StackScan {
        directory: PathBuf::from("review-capture"),
        frames: (0..2)
            .map(|i| jobs::FrameFile {
                path: PathBuf::from(format!("review-capture/frame-{i}.arw")),
                bytes: 10,
            })
            .collect(),
        total_bytes: 20,
    }
}
#[test]
fn inspecting_old_revision_and_navigating_does_not_rewrite_newer_stack_recipe() {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = isolated_app();
    let mut old = fixture_run();
    old.settings.pyramid_bands = Some(5);
    let mut next = StackDraft::from_run(&old);
    next.settings.pyramid_bands = Some(9);
    next.gate = Some(3.5);
    let project = app
        .catalog
        .create_project("Independent review project")
        .unwrap();
    let id = app
        .catalog
        .create_stack(project, "Evolving capture", next)
        .unwrap();
    app.catalog.add_revision(id, old.clone()).unwrap();
    app.active_stack = Some(id);
    app.stack = Some(fixture_scan());
    app.controls.settings.pyramid_bands = Some(9);
    app.controls.gate = Some(3.5);
    let evidence = serde_json::to_vec(&app.catalog.runs[0]).unwrap();
    let output = paint(&mut app, &ctx, egui::vec2(1440.0, 940.0), true, 0.0, vec![]);
    let at = text_rect(&output, "01  Earlier settings")
        .expect("revision must be rendered")
        .center();
    click(&mut app, &ctx, at, 0.1);
    assert_eq!(
        app.expected_run.as_ref().map(|r| r.directory.as_path()),
        Some(old.directory.as_path()),
        "must actually open the old revision"
    );
    assert_eq!(
        app.controls.settings.pyramid_bands,
        Some(5),
        "revision inspection shows its actual recipe"
    );
    app.scan = None;
    app.replay = None;
    app.stack = Some(fixture_scan());
    // An actual tree selection takes the same sidebar changed branch as naming,
    // notes and moves. That branch must not commit historical controls as a draft.
    let output = paint(&mut app, &ctx, egui::vec2(1440.0, 940.0), true, 0.3, vec![]);
    let project_at = text_rect(&output, "Independent review project")
        .unwrap()
        .center();
    click(&mut app, &ctx, project_at, 0.4);
    assert_eq!(app.catalog.selected, Some(project));
    assert_eq!(
        app.catalog
            .node(id)
            .unwrap()
            .stack
            .as_ref()
            .unwrap()
            .settings
            .pyramid_bands,
        Some(9),
        "ordinary project selection cannot silently commit the historical recipe"
    );
    // Follow with bracket navigation, a separate former save-on-import path.
    app.catalog.rename(project, "Renamed project").unwrap();
    app.import(PathBuf::from("another-capture"));
    app.scan = None;
    let draft = app.catalog.node(id).unwrap().stack.as_ref().unwrap();
    assert_eq!(draft.settings.pyramid_bands, Some(9));
    assert_eq!(draft.gate, Some(3.5));
    assert_eq!(serde_json::to_vec(&app.catalog.runs[0]).unwrap(), evidence);
}
#[test]
fn opening_stack_uses_its_next_recipe_while_replaying_saved_run_evidence() {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = isolated_app();
    let mut run = fixture_run();
    run.settings.pyramid_bands = Some(4);
    let mut next = StackDraft::from_run(&run);
    next.settings.pyramid_bands = Some(8);
    let project = app.catalog.create_project("Project").unwrap();
    let id = app
        .catalog
        .create_stack(project, "Next recipe capture", next)
        .unwrap();
    app.catalog.add_revision(id, run).unwrap();
    let output = paint(&mut app, &ctx, egui::vec2(1440.0, 940.0), true, 0.0, vec![]);
    click(
        &mut app,
        &ctx,
        text_rect(&output, "Next recipe capture").unwrap().center(),
        0.1,
    );
    assert_eq!(app.active_stack, Some(id));
    assert_eq!(app.controls.settings.pyramid_bands, Some(8));
    assert_eq!(
        app.expected_run.as_ref().unwrap().settings.pyramid_bands,
        Some(4)
    );
    assert!(app.replay.is_some() && app.process_view);
    app.scan = None;
    app.replay = None;
}
#[test]
fn complete_workspace_settles_after_restore_and_scrollbar_threshold_resizes() {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = isolated_app();
    app.stack = Some(fixture_scan());
    let before = app.process_space.layout();
    let mut time = 0.0;
    let mut saw_geometry_change = false;
    let mut previous = None;
    // +/- one point around minimum-canvas/dock boundaries challenges the
    // scrollbar -> content size -> scrollbar feedback loop, not just large sizes.
    for (width, height) in [
        (1440., 940.),
        (1337., 819.),
        (1338., 820.),
        (1339., 821.),
        (1000., 760.),
        (1001., 761.),
        (1920., 1080.),
        (1440., 940.),
    ] {
        let size = egui::vec2(width, height);
        let mut last = None;
        for frame in 0..28 {
            time += 0.02;
            let output = paint(&mut app, &ctx, size, frame >= 3, time, vec![]);
            let title = text_rect(&output, "READ").expect("process survives restore");
            let scrub = text_rect(&output, "Sources").expect("primary viewer command persists");
            let timeline = text_rect(&output, "CAPTURES / SOURCES")
                .or_else(|| text_rect(&output, "CAPTURE / ADMITTED SAMPLES"))
                .or_else(|| text_rect(&output, "CAPTURES"))
                .expect("one integrated capture timeline remains on screen");
            let rect = title.union(scrub).union(timeline);
            if frame > 18 {
                if let Some(previous) = last {
                    assert_eq!(
                        rect, previous,
                        "stable viewport must not continue changing geometry at {size:?}"
                    );
                }
                last = Some(rect);
            }
        }
        let rect = last.unwrap();
        if let Some(old) = previous {
            saw_geometry_change |= old != rect;
        }
        previous = Some(rect);
        assert_eq!(
            app.process_space.layout(),
            before,
            "resize/focus events without a seam drag must not change saved proportions"
        );
    }
    assert!(
        saw_geometry_change,
        "fixture must actually change the process geometry"
    );
}

#[test]
fn rendered_project_rename_defers_disk_write_and_exit_flushes_latest_name() {
    let directory = std::env::temp_dir().join(format!(
        "strehl-v19-project-exit-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&directory).unwrap();
    let path = directory.join("projects.json");
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = isolated_app();
    app.catalog = Catalog::load(Some(path.clone()));
    let project = app.catalog.create_project("Before editing").unwrap();
    app.catalog.save().unwrap();
    let before = std::fs::read(&path).unwrap();
    let output = paint(&mut app, &ctx, egui::vec2(1440.0, 940.0), true, 0.0, vec![]);
    click(
        &mut app,
        &ctx,
        text_rect(&output, "Before editing").unwrap().center(),
        0.1,
    );
    let key = |key, modifiers| egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers,
    };
    paint(
        &mut app,
        &ctx,
        egui::vec2(1440.0, 940.0),
        true,
        0.2,
        vec![key(egui::Key::F2, egui::Modifiers::NONE)],
    );
    paint(&mut app, &ctx, egui::vec2(1440.0, 940.0), true, 0.3, vec![]);
    paint(
        &mut app,
        &ctx,
        egui::vec2(1440.0, 940.0),
        true,
        0.4,
        vec![
            key(
                egui::Key::A,
                egui::Modifiers {
                    command: true,
                    mac_cmd: cfg!(target_os = "macos"),
                    ctrl: !cfg!(target_os = "macos"),
                    ..egui::Modifiers::NONE
                },
            ),
            egui::Event::Text("After editing".into()),
        ],
    );
    paint(
        &mut app,
        &ctx,
        egui::vec2(1440.0, 940.0),
        true,
        0.5,
        vec![key(egui::Key::Enter, egui::Modifiers::NONE)],
    );
    assert_eq!(
        app.catalog.node(project).unwrap().name,
        "After editing",
        "fixture must actually rename via the rendered explorer"
    );
    assert!(
        app.catalog_edit_pending.is_some(),
        "UI edit must schedule persistence"
    );
    assert_eq!(
        std::fs::read(&path).unwrap(),
        before,
        "typing and accepting a name must not synchronously rewrite the catalog"
    );
    eframe::App::on_exit(&mut app);
    assert!(app.catalog_edit_pending.is_none());
    let loaded = Catalog::load(Some(path.clone()));
    assert!(loaded.load_error.is_none());
    assert_eq!(
        loaded.node(project).unwrap().name,
        "After editing",
        "exit must preserve the last pending edit"
    );
    std::fs::remove_dir_all(directory).unwrap();
}
#[test]
fn pending_project_edits_flush_when_idle_but_not_during_pointer_drag() {
    let directory = std::env::temp_dir().join(format!(
        "strehl-v19-project-idle-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&directory).unwrap();
    let path = directory.join("projects.json");
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = isolated_app();
    app.catalog = Catalog::load(Some(path.clone()));
    let project = app.catalog.create_project("Initial").unwrap();
    app.catalog.save().unwrap();
    let before = std::fs::read(&path).unwrap();
    app.catalog
        .rename(project, "Edited while pointer down")
        .unwrap();
    app.catalog_edit_pending = Some(Instant::now() - Duration::from_secs(1));
    let at = egui::pos2(700.0, 400.0);
    let pointer = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1440.0, 940.0),
            )),
            events: vec![egui::Event::PointerMoved(at), pointer(true)],
            ..Default::default()
        },
        |ctx| app.update_workspace(ctx),
    );
    assert_eq!(
        std::fs::read(&path).unwrap(),
        before,
        "an overdue save must wait for an active drag"
    );
    assert!(app.catalog_edit_pending.is_some());
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1440.0, 940.0),
            )),
            events: vec![pointer(false)],
            ..Default::default()
        },
        |ctx| app.update_workspace(ctx),
    );
    assert!(app.catalog_edit_pending.is_none());
    assert_eq!(
        Catalog::load(Some(path.clone()))
            .node(project)
            .unwrap()
            .name,
        "Edited while pointer down"
    );
    std::fs::remove_dir_all(directory).unwrap();
}

#[test]
fn limited_render_preserves_the_full_verified_source_axis_in_the_primary_workspace() {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = isolated_app();
    let mut scan = fixture_scan();
    scan.frames = (0..12)
        .map(|i| jobs::FrameFile {
            path: PathBuf::from(format!("review-capture/frame-{i}.arw")),
            bytes: 10,
        })
        .collect();
    scan.total_bytes = 120;
    let mut saved = fixture_run();
    saved.frames = 3;
    saved.settings.frame_limit = Some(3);
    saved.sources = crate::workspace_history::source_identities(&scan);
    assert!(
        saved.matches_scan(&scan),
        "full bracket must actually match the saved limited render"
    );
    app.stack = Some(scan);
    app.expected_run = Some(saved);
    app.progress.frames_total = Some(3);
    app.progress.mark_complete();
    app.activity = true;
    app.recorded = true;
    paint(&mut app, &ctx, egui::vec2(1440.0, 940.0), true, 0.0, vec![]);
    app.inspect_frame(11);
    let output = paint(&mut app, &ctx, egui::vec2(1440.0, 940.0), true, 0.1, vec![]);
    assert_eq!(app.selected, 11);
    assert_eq!(app.process_space.inspection_frame(), Some(11));
    assert!(
        output.shapes.iter().any(
            |s| matches!(&s.shape,egui::Shape::Text(t) if t.galley.text() == "012 · SOURCE" && t.visual_bounding_rect().center().y > 600.0)
        ),
        "a 3-frame output cannot hide captures 4–12 from the source timeline"
    );
    assert_eq!(
        app.progress.frames_total,
        Some(3),
        "source browsing must not inflate engine progress"
    );
}

#[test]
fn minimized_and_transient_tiny_viewports_cannot_rewrite_sidebar_geometry() {
    for (tiny, minimized) in [
        (egui::vec2(0.0, 0.0), true),
        (egui::vec2(1.0, 1.0), true),
        (egui::vec2(240.0, 160.0), true),
        (egui::vec2(1.0, 1.0), false),
        (egui::vec2(240.0, 160.0), false),
    ] {
        let ctx = egui::Context::default();
        theme::install(&ctx);
        let mut app = isolated_app();
        app.catalog.create_project("Restore witness").unwrap();
        app.stack = Some(fixture_scan());
        let original_layout = app.process_space.layout();
        let mut frame = 0;
        let mut update = |app: &mut StrehlApp, size: egui::Vec2, minimized: bool| {
            frame += 1;
            let mut raw = egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, size)),
                focused: !minimized,
                time: Some(frame as f64 / 60.0),
                ..Default::default()
            };
            raw.viewports
                .entry(egui::ViewportId::ROOT)
                .or_default()
                .minimized = Some(minimized);
            ctx.run(raw, |ctx| app.update_workspace(ctx))
        };
        let normal = egui::vec2(1440.0, 940.0);
        let mut before = None;
        for _ in 0..8 {
            before = text_rect(&update(&mut app, normal, false), "READ");
        }
        let before = before.expect("fixture must render the primary process workspace");
        let updates_before = app.updates;
        for _ in 0..6 {
            update(&mut app, tiny, minimized);
        }
        assert_eq!(
            app.updates,
            updates_before + 6,
            "minimizing must keep the update/poll path alive"
        );
        for _ in 0..16 {
            let after = update(&mut app, normal, false);
            assert_eq!(
                text_rect(&after, "READ"),
                Some(before),
                "restore after {tiny:?} minimized={minimized} must preserve the chosen sidebar boundary"
            );
        }
        assert_eq!(app.process_space.layout(), original_layout);
    }
}
