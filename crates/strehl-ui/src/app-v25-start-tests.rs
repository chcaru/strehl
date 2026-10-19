//! Start-workflow witnesses use the actual Projects/Adjust controls. The fake
//! executable cannot decode captures or produce a photograph.
use super::*;

fn fixture() -> (StrehlApp, jobs::tests::TestDirectory) {
    let files = jobs::tests::TestDirectory::new("v25-start-workflow");
    let source = files.path().join("camera-bracket");
    std::fs::create_dir(&source).unwrap();
    let frames = (0..3)
        .map(|index| {
            let path = source.join(format!("photo-{index:02}.arw"));
            std::fs::write(&path, [index as u8; 42]).unwrap();
            jobs::FrameFile { path, bytes: 42 }
        })
        .collect();
    let engine = files.path().join("deliberately-invalid.exe");
    std::fs::write(&engine, b"This is not an executable").unwrap();
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = crate::workspace_history::Catalog::default();
    app.stack = Some(StackScan {
        directory: source,
        frames,
        total_bytes: 126,
    });
    app.engine = Some(engine);
    app.output = files.path().join("results");
    app.controls.settings.frame_limit = Some(2);
    app.controls.exposure = Some(0.75);
    app.sidebar = Some(workspace::Sidebar::Projects);
    app.ensure_project_stack();
    app.catalog
        .node_mut(app.active_stack.unwrap())
        .unwrap()
        .name = "Petal study".into();
    (app, files)
}

fn paint(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1060.0, 720.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.undo_shortcuts(ctx);
            app.workspace(ctx);
            let _ = app.bracket_browser.show(ctx);
        },
    )
}
fn text(out: &egui::FullOutput, needle: &str) -> egui::Rect {
    out.shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(t) if t.galley.text() == needle => Some(t.visual_bounding_rect()),
            _ => None,
        })
        .find(|rect| rect.left() > crate::window_chrome::RAIL_WIDTH && rect.left() < 340.0)
        .unwrap_or_else(|| panic!("missing sidebar text: {needle}"))
}
fn click(app: &mut StrehlApp, ctx: &egui::Context, at: egui::Pos2, time: f64) {
    for (offset, pressed) in [(0.0, true), (0.02, false)] {
        paint(
            app,
            ctx,
            time + offset,
            vec![
                egui::Event::PointerMoved(at),
                egui::Event::PointerButton {
                    pos: at,
                    button: egui::PointerButton::Primary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
    }
}
fn shortcut(app: &mut StrehlApp, ctx: &egui::Context, time: f64) {
    paint(
        app,
        ctx,
        time,
        vec![egui::Event::Key {
            key: egui::Key::Enter,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: egui::Modifiers::COMMAND,
        }],
    );
}

#[test]
fn local_stack_command_freezes_request_and_second_click_cannot_stop_or_duplicate_it() {
    let (mut app, _files) = fixture();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let before = paint(&mut app, &ctx, 0.0, vec![]);
    assert!(text(&before, "Petal study").top() < 100.0);
    assert!(text(&before, "First 2 of 3 photos · new result").top() < 130.0);
    let action = text(&before, "Stack");
    assert!(
        action.top() < 160.0,
        "launch is local and visible without scrolling Adjust"
    );
    let recipe = app.controls.settings.clone();
    click(&mut app, &ctx, action.center(), 0.1);
    let started = app
        .started
        .expect("actual worker starts from the rendered command");
    let pending = app
        .pending_run
        .as_ref()
        .expect("immutable pending request exists immediately");
    assert_eq!(pending.frames, 2);
    assert_eq!(pending.settings, recipe);
    assert_eq!(pending.exposure, Some(0.75));
    assert!(app.process_view && !app.spatial_view && app.job.is_some());
    let pending_ui = paint(&mut app, &ctx, 0.15, vec![]);
    text(&pending_ui, "STARTING");
    text(&pending_ui, "Starting…");
    click(&mut app, &ctx, action.center(), 0.2);
    shortcut(&mut app, &ctx, 0.25);
    app.start_render();
    assert_eq!(app.started, Some(started));
    assert!(
        !app.job.as_ref().unwrap().is_cancelling(),
        "a second launch click must not become Stop"
    );
    app.sidebar = None;
    let running = paint(&mut app, &ctx, 0.3, vec![]);
    let rail = running
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text)
                if text.galley.text() == "Stack"
                    && text.visual_bounding_rect().right() < crate::window_chrome::RAIL_WIDTH =>
            {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
        .expect("running stack retains its rail launch target");
    click(&mut app, &ctx, rail, 0.4);
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Projects));
    click(&mut app, &ctx, rail, 0.5);
    assert_eq!(app.started, Some(started));
    assert!(
        !app.job.as_ref().unwrap().is_cancelling(),
        "repeated rail clicks reveal the running stack without cancelling it"
    );
    let stop = text(&paint(&mut app, &ctx, 0.6, vec![]), "Stop");
    assert!(
        stop.left() > action.right(),
        "cancellation has a separate target"
    );
    click(&mut app, &ctx, stop.center(), 0.7);
    assert!(app.job.as_ref().unwrap().is_cancelling());
    app.sidebar = None;
    click(&mut app, &ctx, rail, 0.8);
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Projects));
    text(&paint(&mut app, &ctx, 0.9, vec![]), "STOPPING");
}

#[test]
fn blocked_start_reasons_are_visible_and_guard_shortcuts_before_catalog_or_job_changes() {
    for mode in 0..5 {
        let (mut app, _files) = fixture();
        let ctx = egui::Context::default();
        theme::install(&ctx);
        let expected = match mode {
            0 => {
                app.engine = None;
                "Stacking engine unavailable"
            }
            1 => {
                app.scan = Some(jobs::spawn_task("v25-scan-guard", |_| {
                    anyhow::bail!("fixture intentionally unpolled")
                }));
                "Reading source photos…"
            }
            2 => {
                app.replay = Some(jobs::spawn_task("v25-replay-guard", |_| {
                    anyhow::bail!("fixture intentionally unpolled")
                }));
                "Opening the saved result…"
            }
            3 => {
                app.controls.settings.frame_limit = Some(0);
                "Choose at least one source photo"
            }
            _ => {
                let (_sender, receiver) = mpsc::channel();
                app.dialog = Some(receiver);
                "Finish choosing your photos"
            }
        };
        let catalog = serde_json::to_value(&app.catalog).unwrap();
        let output = paint(&mut app, &ctx, 0.0, vec![]);
        text(&output, expected);
        let at = text(&output, "Stack").center();
        click(&mut app, &ctx, at, 0.1);
        shortcut(&mut app, &ctx, 0.2);
        app.start_render();
        assert!(app.job.is_none() && app.pending_run.is_none() && app.started.is_none());
        assert_eq!(serde_json::to_value(&app.catalog).unwrap(), catalog);
    }
}

#[test]
fn adjust_keeps_launch_above_scrolling_recipe_and_cancelled_import_preserves_current_capture() {
    let (mut app, _files) = fixture();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let output = paint(&mut app, &ctx, 0.0, vec![]);
    click(&mut app, &ctx, text(&output, "Adjust").center(), 0.1);
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Adjust));
    let adjusted = paint(&mut app, &ctx, 0.2, vec![]);
    let at = text(&adjusted, "Stack");
    paint(
        &mut app,
        &ctx,
        0.3,
        vec![
            egui::Event::PointerMoved(egui::pos2(200.0, 500.0)),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, -600.0),
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    assert_eq!(text(&paint(&mut app, &ctx, 0.4, vec![]), "Stack"), at);
    app.sidebar = Some(workspace::Sidebar::Projects);
    let previous_source = app.stack.as_ref().unwrap().directory.clone();
    let active = app.active_stack;
    let recipe = app.controls.settings.clone();
    let catalog = serde_json::to_value(&app.catalog).unwrap();
    let projects = paint(&mut app, &ctx, 0.5, vec![]);
    click(&mut app, &ctx, text(&projects, "New stack").center(), 0.6);
    assert!(app.bracket_browser.active());
    paint(
        &mut app,
        &ctx,
        0.7,
        vec![egui::Event::Key {
            key: egui::Key::Escape,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        }],
    );
    assert!(!app.bracket_browser.active());
    assert_eq!(app.stack.as_ref().unwrap().directory, previous_source);
    assert_eq!(app.active_stack, active);
    assert_eq!(app.controls.settings, recipe);
    assert_eq!(serde_json::to_value(&app.catalog).unwrap(), catalog);
    assert!(app.job.is_none());
}
