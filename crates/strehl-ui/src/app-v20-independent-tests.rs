//! Independent v20 witnesses run the real workspace and cross-domain actions.
use super::*;

fn app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = crate::workspace_history::Catalog::default();
    app
}
fn paint(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    size: egui::Vec2,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, size)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| app.update_workspace(ctx),
    )
}
fn key(key: egui::Key, modifiers: egui::Modifiers) -> egui::Event {
    egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers,
    }
}
fn text_rect(out: &egui::FullOutput, needle: &str) -> egui::Rect {
    fn find(s: &egui::Shape, needle: &str) -> Option<egui::Rect> {
        match s {
            egui::Shape::Text(t) if t.galley.text() == needle => {
                Some(egui::Rect::from_min_size(t.pos, t.galley.size()))
            }
            egui::Shape::Vec(v) => v.iter().find_map(|s| find(s, needle)),
            _ => None,
        }
    }
    out.shapes
        .iter()
        .find_map(|s| find(&s.shape, needle))
        .unwrap_or_else(|| panic!("Missing rendered control {needle}"))
}
fn rename(app: &mut StrehlApp, ctx: &egui::Context, name: &str, time: f64) {
    let size = egui::vec2(1060.0, 720.0);
    let current = app
        .catalog
        .node(app.catalog.selected.unwrap())
        .unwrap()
        .name
        .clone();
    let out = paint(app, ctx, size, time, vec![]);
    let point = text_rect(&out, &current).center();
    for (offset, pressed) in [(0.01, true), (0.02, false)] {
        paint(
            app,
            ctx,
            size,
            time + offset,
            vec![
                egui::Event::PointerMoved(point),
                egui::Event::PointerButton {
                    pos: point,
                    button: egui::PointerButton::Primary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
    }
    paint(
        app,
        ctx,
        size,
        time + 0.03,
        vec![key(egui::Key::F2, egui::Modifiers::NONE)],
    );
    paint(app, ctx, size, time + 0.04, vec![]);
    paint(
        app,
        ctx,
        size,
        time + 0.05,
        vec![egui::Event::Text(name.into())],
    );
    paint(
        app,
        ctx,
        size,
        time + 0.06,
        vec![key(egui::Key::Enter, egui::Modifiers::NONE)],
    );
    paint(app, ctx, size, time + 0.07, vec![]);
}

#[test]
fn global_undo_reverses_latest_project_action_after_that_domain_reaches_capacity() {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = app();
    let id = app.catalog.create_project("Original").unwrap();
    app.catalog.selected = Some(id);
    paint(&mut app, &ctx, egui::vec2(1060.0, 720.0), 0.0, vec![]);
    // Beyond the independent per-domain cap. A later revision must still be
    // ordered even when the domain reports unchanged bounded history depths.
    for i in 0..85 {
        let name = format!("Project edit {i}");
        rename(&mut app, &ctx, &name, 1.0 + i as f64);
        assert_eq!(
            app.catalog.node(id).unwrap().name,
            name,
            "fixture must exercise actual UI renaming"
        );
    }
    assert_eq!(app.project_explorer.history_depths(), (80, 0));
    let original = app.controls.settings.frame_limit;
    let recipe = history::Recipe::capture(&app.controls);
    app.controls.settings.frame_limit = Some(7);
    app.edits.changed_recipe(recipe, 90.0);
    paint(&mut app, &ctx, egui::vec2(1060.0, 720.0), 90.5, vec![]);
    assert_eq!(app.undo_label(false), "Undo settings");
    rename(&mut app, &ctx, "Latest project edit", 91.0);
    assert!(app.undo_edit(false));
    assert_eq!(
        app.catalog.node(id).unwrap().name,
        "Project edit 84",
        "undo should reverse the most recent project edit, not an earlier settings change"
    );
    assert_eq!(app.controls.settings.frame_limit, Some(7));
    assert!(app.undo_edit(false));
    assert_eq!(app.controls.settings.frame_limit, original);
    assert!(app.undo_edit(true));
    assert_eq!(app.controls.settings.frame_limit, Some(7));
    assert!(app.undo_edit(true));
    assert_eq!(app.catalog.node(id).unwrap().name, "Latest project edit");
}

#[test]
fn source_picker_is_opened_from_selected_nested_folder_without_creating_a_stack_early() {
    for from_welcome in [false, true] {
        let ctx = egui::Context::default();
        theme::install(&ctx);
        let mut app = app();
        let p = app.catalog.create_project("Field study").unwrap();
        let f = app.catalog.create_folder(p, "Lens experiments").unwrap();
        app.catalog.selected = Some(f);
        if from_welcome {
            app.sidebar = None;
        }
        let size = egui::vec2(1060.0, 720.0);
        let out = paint(&mut app, &ctx, size, 0.0, vec![]);
        let at = text_rect(&out, "New stack").center();
        for (i, pressed) in [true, false].into_iter().enumerate() {
            paint(
                &mut app,
                &ctx,
                size,
                0.1 + i as f64 * 0.1,
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
        assert!(
            app.picker_active(),
            "New stack must actually open the custom source picker"
        );
        assert_eq!(app.capture_parent, Some(f));
        assert_eq!(
            app.catalog.nodes.len(),
            2,
            "cancelable browsing must not create phantom stacks"
        );
        assert!(app.stack.is_none());
    }
}

#[test]
fn workspace_reclaims_top_edge_and_keeps_chrome_local_at_different_pixel_densities() {
    for scale in [1.0, 1.25, 1.5, 2.0] {
        let ctx = egui::Context::default();
        ctx.set_pixels_per_point(scale);
        theme::install(&ctx);
        let mut app = app();
        app.activity = true;
        app.catalog
            .create_project("Desktop density witness")
            .unwrap();
        let size = egui::vec2(1060.0, 720.0);
        let mut out = paint(&mut app, &ctx, size, 0.0, vec![]);
        for i in 1..5 {
            out = paint(&mut app, &ctx, size, i as f64 * 0.05, vec![]);
        }
        let heading = text_rect(&out, "PROJECTS");
        assert!(
            heading.top() < 20.0,
            "unused title row must not reappear at scale {scale}: {heading:?}"
        );
        let action = text_rect(&out, "New stack");
        assert!(
            action.top() < 65.0,
            "source workflow should stay next to the explorer heading"
        );
        let read = text_rect(&out, "READ");
        assert!(
            read.top() < 40.0,
            "primary process should use the former title row at scale {scale}"
        );
        assert!(
            read.left() > heading.left(),
            "process stays alongside project navigation"
        );
        let again = paint(&mut app, &ctx, size, 1.0, vec![]);
        assert_eq!(
            text_rect(&again, "READ"),
            read,
            "stable density must not ratchet pane geometry"
        );
    }
}
