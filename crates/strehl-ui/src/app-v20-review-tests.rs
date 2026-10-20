//! Independent interaction witnesses: use rendered controls and native key events,
//! compare immutable run evidence, and deliberately keep non-text widgets focused.
use super::*;
use crate::workspace_history::{Catalog, NodeId, Run, StackDraft};

fn fixture() -> (StrehlApp, NodeId, NodeId) {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Catalog::default();
    let project = app.catalog.create_project("Garden study").unwrap();
    let run: Run = serde_json::from_value(serde_json::json!({
        "directory":"v20-saved-result", "source":"v20-captures", "output":"v20-saved-result/photo.tiff", "log":"v20-saved-result/render.log",
        "label":"Before adjustment", "created":2, "status":"Saved", "frames":3,
        "settings":jobs::RenderSettings::default(),"exposure":-0.5,"gate":null,"workers":2
    })).unwrap();
    let mut draft = StackDraft::from_run(&run);
    draft.exposure = Some(0.75);
    let stack = app.catalog.create_stack(project, "Fern", draft).unwrap();
    app.catalog.add_revision(stack, run).unwrap();
    app.active_stack = Some(stack);
    app.stack = Some(StackScan {
        directory: PathBuf::from("v20-captures"),
        frames: (0..3)
            .map(|i| jobs::FrameFile {
                path: PathBuf::from(format!("v20-captures/{i}.arw")),
                bytes: 10,
            })
            .collect(),
        total_bytes: 30,
    });
    app.controls.exposure = Some(0.75);
    app.process_view = true;
    (app, project, stack)
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
                egui::vec2(1440.0, 940.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.undo_shortcuts(ctx);
            app.status_bar(ctx);
            app.workspace(ctx);
            app.observe_edits(ctx);
            crate::window_chrome::finish(ctx, false);
        },
    )
}
fn find(output: &egui::FullOutput, text: &str) -> Option<egui::Rect> {
    fn in_shape(shape: &egui::Shape, text: &str) -> Option<egui::Rect> {
        match shape {
            egui::Shape::Text(t) if t.galley.text() == text => {
                Some(egui::Rect::from_min_size(t.pos, t.galley.size()))
            }
            egui::Shape::Vec(shapes) => shapes.iter().find_map(|s| in_shape(s, text)),
            _ => None,
        }
    }
    output.shapes.iter().find_map(|s| in_shape(&s.shape, text))
}
fn click(app: &mut StrehlApp, ctx: &egui::Context, at: egui::Pos2, time: f64) {
    let layer = ctx.layer_id_at(at);
    let native_edge = (0..12)
        .find(|index| layer.is_some_and(|l| l.id == egui::Id::new(("native-window-edge", index))));
    assert!(
        layer.is_none_or(|l| l.order != egui::Order::Foreground),
        "workspace action at {at:?} is occluded by foreground layer {layer:?}; native edge {native_edge:?}, controls={}",
        layer.is_some_and(|l| l.id == egui::Id::new("native-window-controls"))
    );
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
fn key(key: egui::Key, command: bool) -> egui::Event {
    egui::Event::Key {
        key,
        physical_key: Some(key),
        pressed: true,
        repeat: false,
        modifiers: if command {
            egui::Modifiers {
                ctrl: true,
                command: true,
                ..Default::default()
            }
        } else {
            egui::Modifiers::NONE
        },
    }
}
fn toggle_auto_exposure(app: &mut StrehlApp, ctx: &egui::Context) {
    app.sidebar = Some(workspace::Sidebar::Adjust);
    let out = paint(app, ctx, 0.0, vec![]);
    let at = find(&out, "Automatic exposure")
        .expect("actual settings checkbox is visible")
        .center();
    click(app, ctx, at, 0.1);
    assert!(
        app.controls.settings.auto_exposure,
        "fixture must edit the actual control"
    );
    assert_eq!(app.controls.exposure, None);
}
#[test]
fn actual_recipe_checkbox_undo_redo_restores_manual_exposure_and_preserves_saved_evidence() {
    let (mut app, _, stack) = fixture();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let evidence = serde_json::to_vec(&app.catalog.runs).unwrap();
    toggle_auto_exposure(&mut app, &ctx);
    paint(&mut app, &ctx, 0.6, vec![]);
    assert!(app.can_undo_edit(false));
    // Do not click elsewhere or clear focus: Undo should work immediately after the control.
    paint(&mut app, &ctx, 0.7, vec![key(egui::Key::Z, true)]);
    assert!(
        !app.controls.settings.auto_exposure,
        "Ctrl-Z must undo a focused checkbox edit"
    );
    assert_eq!(app.controls.exposure, Some(0.75));
    assert_eq!(
        app.catalog
            .node(stack)
            .unwrap()
            .stack
            .as_ref()
            .unwrap()
            .exposure,
        Some(0.75)
    );
    paint(&mut app, &ctx, 0.8, vec![key(egui::Key::Y, true)]);
    assert!(app.controls.settings.auto_exposure);
    assert_eq!(serde_json::to_vec(&app.catalog.runs).unwrap(), evidence);
}
#[test]
fn pending_recipe_then_escape_view_gesture_undo_in_actual_gesture_order() {
    let (mut app, _, _) = fixture();
    let ctx = egui::Context::default();
    toggle_auto_exposure(&mut app, &ctx);
    app.process_space.inspect_frame(1);
    paint(&mut app, &ctx, 0.2, vec![key(egui::Key::Escape, false)]);
    assert!(
        app.process_space.can_undo(),
        "Escape must actually change the explored view"
    );
    assert_eq!(app.process_space.inspection_frame(), None);
    assert_eq!(app.undo_label(false), "Undo view");
    assert!(app.undo_edit(false));
    assert_eq!(app.process_space.inspection_frame(), Some(1));
    assert!(
        app.controls.settings.auto_exposure,
        "first undo reverses later view gesture only"
    );
    assert_eq!(app.undo_label(false), "Undo settings");
    assert!(app.undo_edit(false));
    assert!(!app.controls.settings.auto_exposure);
    assert_eq!(app.controls.exposure, Some(0.75));
}
#[test]
fn local_view_undo_and_global_recipe_redo_share_one_consistent_order() {
    let (mut app, _, _) = fixture();
    let ctx = egui::Context::default();
    toggle_auto_exposure(&mut app, &ctx);
    app.process_space.inspect_frame(2);
    paint(&mut app, &ctx, 0.2, vec![key(egui::Key::Escape, false)]);
    assert!(
        app.process_space.undo(),
        "same local operation used by viewer context menu"
    );
    paint(&mut app, &ctx, 0.3, vec![]);
    assert_eq!(
        app.undo_label(false),
        "Undo settings",
        "local undo must remove its global entry"
    );
    assert!(app.undo_edit(false));
    assert!(app.undo_edit(true));
    assert!(app.controls.settings.auto_exposure);
    assert_eq!(app.undo_label(true), "Redo view");
    assert!(app.undo_edit(true));
    assert_eq!(app.process_space.inspection_frame(), None);
    assert!(
        !app.can_undo_edit(true),
        "redo history must not duplicate the local gesture"
    );
}
#[test]
fn project_creation_undo_works_while_its_tree_row_has_keyboard_focus() {
    let (mut app, _, _) = fixture();
    let ctx = egui::Context::default();
    app.sidebar = Some(workspace::Sidebar::Projects);
    let out = paint(&mut app, &ctx, 0.0, vec![]);
    click(
        &mut app,
        &ctx,
        find(&out, "New project").unwrap().center(),
        0.1,
    );
    paint(
        &mut app,
        &ctx,
        0.2,
        vec![egui::Event::Text("Winter fieldwork".into())],
    );
    paint(&mut app, &ctx, 0.3, vec![key(egui::Key::Enter, false)]);
    let created = app.catalog.selected.unwrap();
    assert_eq!(app.catalog.node(created).unwrap().name, "Winter fieldwork");
    let out = paint(&mut app, &ctx, 0.4, vec![]);
    click(
        &mut app,
        &ctx,
        find(&out, "Winter fieldwork").unwrap().center(),
        0.5,
    );
    assert!(
        ctx.memory(|m| m.focused().is_some()),
        "fixture intentionally keeps the non-text row focused"
    );
    paint(&mut app, &ctx, 0.6, vec![key(egui::Key::Z, true)]);
    assert!(
        app.catalog.node(created).is_none(),
        "focused explorer row cannot swallow application Undo"
    );
    paint(&mut app, &ctx, 0.7, vec![key(egui::Key::Y, true)]);
    assert_eq!(app.catalog.node(created).unwrap().name, "Winter fieldwork");
}
#[test]
fn saved_result_open_highlights_the_result_and_stack_open_highlights_its_recipe_owner() {
    let (mut app, _, _) = fixture();
    let ctx = egui::Context::default();
    app.sidebar = Some(workspace::Sidebar::Projects);
    let out = paint(&mut app, &ctx, 0.0, vec![]);
    click(
        &mut app,
        &ctx,
        find(&out, "01  Before adjustment").unwrap().center(),
        0.1,
    );
    assert!(
        app.expected_run.is_some(),
        "fixture opens the real app's saved-result path"
    );
    app.scan = None;
    app.replay = None;
    let out = paint(&mut app, &ctx, 0.2, vec![]);
    let result = find(&out, "01  Before adjustment").unwrap();
    let selected = |out: &egui::FullOutput, at: egui::Pos2| {
        out.shapes.iter().any(|s| matches!(&s.shape, egui::Shape::Rect(r) if r.fill == Color32::from_rgb(43,49,61) && r.rect.contains(at) && r.rect.width() > 200.0))
    };
    assert!(
        selected(&out, result.center()),
        "programmatic result navigation must visibly select its exact row"
    );
    click(&mut app, &ctx, find(&out, "Fern").unwrap().center(), 0.3);
    app.scan = None;
    app.replay = None;
    let out = paint(&mut app, &ctx, 0.4, vec![]);
    let owner = find(&out, "Fern").unwrap();
    assert!(selected(&out, owner.center()));
    assert!(!selected(
        &out,
        find(&out, "01  Before adjustment").unwrap().center()
    ));
}
#[test]
fn workspace_chrome_reclaims_top_edge_without_placing_controls_over_projects() {
    let (mut app, _, _) = fixture();
    let ctx = egui::Context::default();
    let out = paint(&mut app, &ctx, 0.0, vec![]);
    let projects = find(&out, "PROJECTS").expect("actual explorer header is present");
    assert!(
        projects.top() < 16.0,
        "sidebar must start at the reclaimed top edge, got {projects:?}"
    );
    assert!(
        find(&out, "STREHL").is_none(),
        "brand/title strip must not consume a row"
    );
    assert!(projects.left() >= crate::window_chrome::RAIL_WIDTH);
    let out = paint(&mut app, &ctx, 0.1, vec![]);
    assert_eq!(
        projects,
        find(&out, "PROJECTS").unwrap(),
        "native controls must not push sidebar downward on a later frame"
    );
}

fn install_owned_photo(app: &mut StrehlApp, ctx: &egui::Context) -> egui::TextureId {
    let photo = ctx.load_texture(
        "review-owned-photo",
        egui::ColorImage::filled([180, 120], Color32::from_rgb(40, 75, 100)),
        egui::TextureOptions::LINEAR,
    );
    app.result = Some(app.catalog.runs[0].output.clone());
    app.image_path = app.result.clone();
    app.result_viewer.install(&photo, [180, 120], false);
    app.activity = true;
    app.progress.mark_complete();
    photo.id()
}
#[test]
fn resetting_an_idle_imported_stack_never_leaves_the_primary_process_workspace() {
    let (mut app, _, _) = fixture();
    let ctx = egui::Context::default();
    assert!(
        !app.activity,
        "fixture is imported and idle, without engine observations"
    );
    paint(&mut app, &ctx, 0.0, vec![]);
    app.process_space.inspect_frame(1);
    paint(&mut app, &ctx, 0.1, vec![key(egui::Key::Escape, false)]);
    assert!(
        app.process_view,
        "Escape must not enter the legacy canvas when no render has started"
    );
    let out = paint(&mut app, &ctx, 0.2, vec![]);
    assert!(find(&out, "READ").is_some());
}

#[test]
fn escape_dismisses_actual_photo_menu_before_resetting_inspection_or_zoom() {
    fn primary_photo(out: &egui::FullOutput, id: egui::TextureId) -> (egui::Rect, Vec<egui::Pos2>) {
        out.shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == id => {
                    let positions: Vec<_> = mesh.vertices.iter().map(|v| v.pos).collect();
                    Some((
                        egui::Rect::from_points(&positions),
                        mesh.vertices.iter().map(|v| v.uv).collect(),
                    ))
                }
                _ => None,
            })
            // The same texture also appears in contribution insets and the
            // overview. Observe the primary photograph, not the first mesh.
            .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
            .expect("owned photograph is actually painted")
    }
    let (mut app, _, _) = fixture();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let photo = install_owned_photo(&mut app, &ctx);
    // A completed texture alone is deliberately insufficient for linked UV
    // inspection. Reproduce the real writer's coordinate certificate as well.
    app.progress.ingest("planes: 90 x 60 per CFA plane\nbands: 7 Laplacian levels + 1 base, coarsest 1 x 1\nwrote: photo.tiff (180 x 120, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
    app.progress.mark_complete();
    assert!(
        crate::process_output_space::OutputSpace::from_progress(&app.progress, [180, 120])
            .is_some()
    );
    paint(&mut app, &ctx, 0.0, vec![]);
    let initial = paint(&mut app, &ctx, 0.4, vec![]);
    let (_, fitted_uv) = primary_photo(&initial, photo);
    app.process_space.inspect_frame(1);
    for step in 0..=24 {
        paint(&mut app, &ctx, 0.41 + f64::from(step) * 0.02, vec![]);
    }
    let focused = paint(&mut app, &ctx, 0.91, vec![]);
    let at = primary_photo(&focused, photo).0.center();
    paint(&mut app, &ctx, 0.93, vec![egui::Event::PointerMoved(at)]);
    paint(
        &mut app,
        &ctx,
        0.95,
        vec![
            egui::Event::PointerMoved(at),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, 200.0),
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    let zoomed = paint(&mut app, &ctx, 1.2, vec![]);
    let (zoomed_rect, zoomed_uv) = primary_photo(&zoomed, photo);
    assert_ne!(
        zoomed_uv, fitted_uv,
        "fixture must truly zoom the photograph"
    );
    assert_eq!(app.process_space.inspection_frame(), Some(1));
    assert_eq!(
        primary_photo(&paint(&mut app, &ctx, 1.25, vec![]), photo).1,
        zoomed_uv,
        "the photograph must finish easing before menu cancellation is measured"
    );
    // Source inspection opens a companion, so find the current final photo
    // again instead of right-clicking its old pre-comparison position.
    let at = zoomed_rect.center();
    for (time, pressed) in [(1.3, true), (1.32, false)] {
        paint(
            &mut app,
            &ctx,
            time,
            vec![
                egui::Event::PointerMoved(at),
                egui::Event::PointerButton {
                    pos: at,
                    button: egui::PointerButton::Secondary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
    }
    let open = paint(&mut app, &ctx, 1.4, vec![]);
    assert!(
        egui::Popup::is_any_open(&ctx),
        "actual photo menu must be open"
    );
    assert!(find(&open, "Fit photograph and linked details").is_some());
    let depths = app.process_space.history_depths();
    let commits = app.process_space.history_commits();
    let undo_label = app.undo_label(false);
    paint(&mut app, &ctx, 1.5, vec![key(egui::Key::Escape, false)]);
    let dismissed = paint(&mut app, &ctx, 1.6, vec![]);
    assert!(!egui::Popup::is_any_open(&ctx));
    assert!(find(&dismissed, "Fit photograph and linked details").is_none());
    assert_eq!(app.process_space.inspection_frame(), Some(1));
    assert_eq!(primary_photo(&dismissed, photo).1, zoomed_uv);
    assert_eq!(app.process_space.history_depths(), depths);
    assert_eq!(app.process_space.history_commits(), commits);
    assert_eq!(app.undo_label(false), undo_label);
    paint(&mut app, &ctx, 1.7, vec![key(egui::Key::Escape, false)]);
    let reset = paint(&mut app, &ctx, 2.2, vec![]);
    assert_eq!(app.process_space.inspection_frame(), None);
    assert_eq!(primary_photo(&reset, photo).1, fitted_uv);
    assert_eq!(app.process_space.history_commits(), commits + 1);
}
