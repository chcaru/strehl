use super::*;

fn frame(
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
    maximized: bool,
    modal: bool,
) -> (egui::FullOutput, bool, bool) {
    frame_in(
        ctx,
        time,
        events,
        maximized,
        modal,
        false,
        egui::vec2(1060.0, 720.0),
    )
}

#[allow(clippy::too_many_arguments)]
fn frame_in(
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
    maximized: bool,
    modal: bool,
    spatial: bool,
    size: Vec2,
) -> (egui::FullOutput, bool, bool) {
    let viewport = Rect::from_min_size(Pos2::ZERO, size);
    let mut raw = egui::RawInput {
        screen_rect: Some(viewport),
        time: Some(time),
        events,
        ..Default::default()
    };
    let info = raw.viewports.get_mut(&egui::ViewportId::ROOT).unwrap();
    info.maximized = Some(maximized);
    info.outer_rect = Some(viewport.translate(egui::vec2(100.0, 100.0)));
    let mut clicked = false;
    let mut modal_closed = false;
    let output = ctx.run(raw, |ctx| {
        egui::SidePanel::left("chrome-test-rail")
            .exact_width(RAIL_WIDTH)
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| {
                drag_space(ui, drag_rect(), modal);
            });
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| {
                assert_eq!(
                    ui.max_rect().top(),
                    0.0,
                    "no title row may consume workspace height"
                );
                clicked = ui
                    .put(action_rect(), egui::Button::new("Application action"))
                    .clicked();
            });
        if modal {
            modal_closed = egui::Modal::new(Id::new("chrome-test-modal"))
                .show(ctx, |ui| {
                    ui.label("Bracket chooser");
                    let _ = ui.button("Folder card");
                })
                .should_close();
        }
        if spatial {
            finish_spatial(ctx, modal);
        } else {
            finish(ctx, modal);
        }
    });
    (output, clicked, modal_closed)
}

fn drag_rect() -> Rect {
    Rect::from_min_max(egui::pos2(7.0, 300.0), egui::pos2(41.0, 520.0))
}
fn action_rect() -> Rect {
    Rect::from_min_size(egui::pos2(90.0, 6.0), egui::vec2(200.0, 22.0))
}
fn controls() -> Rect {
    dock_rect(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0)))
}

fn pointer(point: Pos2, pressed: bool) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(point),
        egui::Event::PointerButton {
            pos: point,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        },
    ]
}

fn commands(output: &egui::FullOutput) -> &[ViewportCommand] {
    &output.viewport_output[&egui::ViewportId::ROOT].commands
}

fn context(modal: bool, maximized: bool) -> egui::Context {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    for time in [0.0, 0.01, 0.02] {
        let _ = frame(&ctx, time, vec![], maximized, modal);
    }
    ctx
}

#[test]
fn native_buttons_emit_the_actual_commands_without_dragging_and_survive_a_modal() {
    for modal in [false, true] {
        for maximized in [false, true] {
            for (index, command) in [
                ViewportCommand::Minimized(true),
                ViewportCommand::Maximized(!maximized),
                ViewportCommand::Close,
            ]
            .into_iter()
            .enumerate()
            {
                let ctx = context(modal, maximized);
                let point = button_rect(controls(), index).center();
                let (press, action, closed) =
                    frame(&ctx, 0.1, pointer(point, true), maximized, modal);
                assert!(commands(&press).is_empty() && !action && !closed);
                let (release, action, closed) =
                    frame(&ctx, 0.2, pointer(point, false), maximized, modal);
                assert_eq!(commands(&release), &[command]);
                assert!(
                    !action && !closed,
                    "Window controls must not click the application or modal backdrop"
                );
            }
        }
    }
}

#[test]
fn blank_rail_drags_immediately_and_second_press_toggles_but_workspace_never_does() {
    for maximized in [false, true] {
        let ctx = context(false, maximized);
        let point = drag_rect().center();
        let (press, _, _) = frame(&ctx, 0.1, pointer(point, true), maximized, false);
        assert_eq!(commands(&press), &[ViewportCommand::StartDrag]);
        let (release, _, _) = frame(&ctx, 0.15, pointer(point, false), maximized, false);
        assert!(
            commands(&release).is_empty(),
            "Native drag must begin on press, not after release"
        );
        let (second, _, _) = frame(&ctx, 0.2, pointer(point, true), maximized, false);
        assert_eq!(commands(&second), &[ViewportCommand::Maximized(!maximized)]);
    }
    let ctx = context(false, false);
    let mut clicks = 0;
    for (time, pressed) in [(0.1, true), (0.15, false), (0.2, true), (0.25, false)] {
        let (output, action, _) = frame(
            &ctx,
            time,
            pointer(action_rect().center(), pressed),
            false,
            false,
        );
        assert!(commands(&output).is_empty());
        clicks += usize::from(action);
    }
    assert_eq!(
        clicks, 2,
        "The negative control must really activate an application button twice"
    );
    let ctx = context(true, false);
    let (output, _, _) = frame(&ctx, 0.1, pointer(drag_rect().center(), true), false, true);
    assert!(
        commands(&output).is_empty(),
        "Modal backdrop presses must never drag the title"
    );
}

#[test]
fn resize_edges_have_correct_native_directions_and_cursors_but_no_maximized_hits() {
    let viewport = Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0));
    let regions = resize_regions(viewport);
    for (index, (rect, direction, cursor)) in regions.iter().enumerate() {
        assert!(viewport.contains_rect(*rect));
        assert!(!rect.intersects(controls().shrink(0.1)));
        assert!(
            regions
                .iter()
                .enumerate()
                .all(|(other, (r, _, _))| other == index || !rect.shrink(0.1).intersects(*r))
        );
        let ctx = context(false, false);
        let (hover, _, _) = frame(
            &ctx,
            0.1,
            vec![egui::Event::PointerMoved(rect.center())],
            false,
            false,
        );
        assert_eq!(hover.platform_output.cursor_icon, *cursor);
        let (press, _, _) = frame(&ctx, 0.2, pointer(rect.center(), true), false, false);
        assert_eq!(
            commands(&press),
            &[ViewportCommand::BeginResize(*direction)]
        );
        for (maximized, modal) in [(true, false), (false, true)] {
            let ctx = context(modal, maximized);
            let (press, _, _) = frame(&ctx, 0.1, pointer(rect.center(), true), maximized, modal);
            assert!(
                commands(&press).is_empty(),
                "edge {index}, maximized={maximized}, modal={modal}, commands={:?}",
                commands(&press)
            );
        }
    }
}

#[test]
fn minimum_width_preserves_all_controls_and_keyboard_focus_can_maximize() {
    let ctx = context(false, false);
    let (output, _, _) = frame(&ctx, 0.1, vec![], false, false);
    assert!(controls().left() > 800.0 && controls().right() < 1060.0);
    assert_eq!(controls().height(), DOCK_HEIGHT);
    let top_action = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Application action" => Some(text.pos),
            _ => None,
        })
        .expect("the reclaimed top area must contain real interactive workspace content");
    assert!(top_action.y < 20.0);
    ctx.memory_mut(|memory| memory.request_focus(Id::new(("native-window-button", 1_usize))));
    let (focus, _, _) = frame(&ctx, 0.2, vec![], false, false);
    assert!(focus.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Rect(rect) if rect.stroke.color == ACCENT && controls().contains_rect(rect.rect)
    )), "Keyboard focus needs its own visible outline");
    let (activate, _, _) = frame(
        &ctx,
        0.3,
        vec![egui::Event::Key {
            key: egui::Key::Enter,
            physical_key: Some(egui::Key::Enter),
            pressed: true,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        }],
        false,
        false,
    );
    assert_eq!(commands(&activate), &[ViewportCommand::Maximized(true)]);
}

#[test]
fn move_grip_is_visible_separate_and_works_in_both_workspaces_even_over_a_modal() {
    for spatial in [false, true] {
        for modal in [false, true] {
            let ctx = egui::Context::default();
            crate::theme::install(&ctx);
            let size = egui::vec2(1060.0, 720.0);
            for time in [0.0, 0.01, 0.02] {
                let _ = frame_in(&ctx, time, vec![], false, modal, spatial, size);
            }
            let point = grip_rect(controls()).center();
            let (hover, _, _) = frame_in(
                &ctx,
                0.1,
                vec![egui::Event::PointerMoved(point)],
                false,
                modal,
                spatial,
                size,
            );
            assert_eq!(hover.platform_output.cursor_icon, egui::CursorIcon::Grab);
            let labels = hover.shapes.iter().filter(|shape|
                matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text() == "Move")
            ).count();
            assert_eq!(
                labels, 1,
                "exactly one visible native dock in each workspace"
            );
            let (press, action, dismissed) =
                frame_in(&ctx, 0.2, pointer(point, true), false, modal, spatial, size);
            assert_eq!(commands(&press), &[ViewportCommand::StartDrag]);
            assert!(!action && !dismissed);
            let (release, _, _) = frame_in(
                &ctx,
                0.25,
                pointer(point, false),
                false,
                modal,
                spatial,
                size,
            );
            assert!(commands(&release).is_empty());
            let (second, _, _) =
                frame_in(&ctx, 0.3, pointer(point, true), false, modal, spatial, size);
            assert_eq!(commands(&second), &[ViewportCommand::Maximized(true)]);
        }
    }
}

#[test]
fn corner_dock_follows_window_width_without_overlapping_resize_or_action_targets() {
    for size in [
        egui::vec2(416.0, 300.0),
        egui::vec2(1060.0, 720.0),
        egui::vec2(2048.0, 1300.0),
    ] {
        let viewport = Rect::from_min_size(Pos2::ZERO, size);
        let dock = dock_rect(viewport);
        assert_eq!(dock.right(), size.x - 6.0);
        assert_eq!(dock.top(), 6.0);
        assert!(viewport.contains_rect(dock));
        assert!(
            dock.area() < viewport.area() * 0.05,
            "chrome cannot grow into a title row"
        );
        for (edge, _, _) in resize_regions(viewport) {
            assert!(
                !edge.intersects(dock),
                "native resizing must never cover the window buttons"
            );
        }
        for spatial in [false, true] {
            for (index, command) in [
                ViewportCommand::Minimized(true),
                ViewportCommand::Maximized(true),
                ViewportCommand::Close,
            ]
            .into_iter()
            .enumerate()
            {
                let ctx = egui::Context::default();
                crate::theme::install(&ctx);
                for time in [0.0, 0.01, 0.02] {
                    let _ = frame_in(&ctx, time, vec![], false, false, spatial, size);
                }
                let button = button_rect(dock, index);
                assert!(button.width() >= 36.0 && button.height() >= 30.0);
                assert!(!grip_rect(dock).shrink(0.1).intersects(button));
                let _ = frame_in(
                    &ctx,
                    0.1,
                    pointer(button.center(), true),
                    false,
                    false,
                    spatial,
                    size,
                );
                let (release, action, _) = frame_in(
                    &ctx,
                    0.2,
                    pointer(button.center(), false),
                    false,
                    false,
                    spatial,
                    size,
                );
                assert_eq!(commands(&release), &[command]);
                assert!(
                    !action,
                    "window actions cannot click through to the workspace"
                );
            }
        }
    }
}

#[test]
fn pressing_a_button_then_releasing_over_its_neighbor_does_not_activate_either_or_drag() {
    for index in 0..3 {
        let ctx = context(false, false);
        let from = button_rect(controls(), index).center();
        let to = button_rect(controls(), (index + 1) % 3).center();
        let (press, _, _) = frame(&ctx, 0.1, pointer(from, true), false, false);
        assert!(commands(&press).is_empty());
        let (motion, _, _) = frame(
            &ctx,
            0.15,
            vec![egui::Event::PointerMoved(to)],
            false,
            false,
        );
        assert!(commands(&motion).is_empty());
        let (release, _, _) = frame(&ctx, 0.2, pointer(to, false), false, false);
        assert!(commands(&release).is_empty());
    }
}
