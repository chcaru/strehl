use super::*;

/// A stand-in for the top bar: a drag surface on its empty space and an
/// application button beside it, with the controls' corner left free.
const TOP: f32 = 44.0;

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
        egui::vec2(1060.0, 720.0),
    )
}

fn frame_in(
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
    maximized: bool,
    modal: bool,
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
        egui::TopBottomPanel::top("chrome-test-top")
            .exact_height(TOP)
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| {
                drag_space(ui, drag_rect(), modal);
                clicked = ui
                    .put(action_rect(), egui::Button::new("Application action"))
                    .clicked();
            });
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| {
                assert_eq!(
                    ui.max_rect().top(),
                    TOP,
                    "the top bar is the only title row"
                );
            });
        if modal {
            modal_closed = egui::Modal::new(Id::new("chrome-test-modal"))
                .show(ctx, |ui| {
                    ui.label("Bracket chooser");
                    let _ = ui.button("Folder card");
                })
                .should_close();
        }
        finish_with(ctx, modal, 1.0);
    });
    (output, clicked, modal_closed)
}

fn drag_rect() -> Rect {
    Rect::from_min_max(egui::pos2(300.0, 0.0), egui::pos2(700.0, 43.0))
}
fn action_rect() -> Rect {
    Rect::from_min_size(egui::pos2(90.0, 10.0), egui::vec2(160.0, 22.0))
}
fn viewport() -> Rect {
    Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0))
}
fn controls() -> Rect {
    controls_rect(viewport())
}
/// The centre of a button's hit area while the window can be resized.
fn button_point(index: usize) -> Pos2 {
    button_hit(button_rect(controls(), index), viewport(), true).center()
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
                let point = button_point(index);
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
fn the_top_bar_drags_immediately_and_a_second_press_toggles_but_its_buttons_never_do() {
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
        "Modal backdrop presses must never drag the window"
    );
}

#[test]
fn resize_edges_have_correct_native_directions_and_cursors_but_no_maximized_hits() {
    let regions = resize_regions(viewport());
    for (index, (rect, direction, cursor)) in regions.iter().enumerate() {
        assert!(viewport().contains_rect(*rect));
        for button in 0..3 {
            let hit = button_hit(button_rect(controls(), button), viewport(), true);
            assert!(
                !rect.intersects(hit.shrink(0.1)),
                "edge {index} must not cover button {button}"
            );
        }
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
            // A maximised or modal window has no resize edges. Maximised, the
            // top edge is the top bar again (dragging it restores the window);
            // under a modal nothing behind the backdrop answers.
            if modal {
                assert!(
                    commands(&press).is_empty(),
                    "edge {index} under a modal: {:?}",
                    commands(&press)
                );
            }
            assert!(
                !commands(&press)
                    .iter()
                    .any(|c| matches!(c, ViewportCommand::BeginResize(_))),
                "edge {index} resized while maximized={maximized} modal={modal}"
            );
        }
    }
}

#[test]
fn the_buttons_fill_the_top_bars_corner_and_keyboard_focus_can_maximize() {
    let ctx = context(false, false);
    let (output, _, _) = frame(&ctx, 0.1, vec![], false, false);
    assert_eq!(controls().right(), 1060.0);
    assert_eq!(controls().top(), 0.0);
    assert_eq!(controls().size(), egui::vec2(126.0, 43.0));
    for index in 0..3 {
        assert_eq!(button_rect(controls(), index).width(), BUTTON_WIDTH);
    }
    assert!(
        !output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text() == "Move")),
        "the floating dock and its grip are gone"
    );
    let top_action = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Application action" => Some(text.pos),
            _ => None,
        })
        .expect("the top bar keeps real interactive content");
    assert!(top_action.y < TOP);
    ctx.memory_mut(|memory| memory.request_focus(Id::new(("native-window-button", 1_usize))));
    let (focus, _, _) = frame(&ctx, 0.2, vec![], false, false);
    assert!(
        focus.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Rect(rect) if rect.stroke.color == crate::studio_theme::GRAPHITE.accent
                && controls().contains_rect(rect.rect)
        )),
        "Keyboard focus needs its own visible outline"
    );
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
fn controls_follow_the_window_width_without_click_through() {
    for size in [
        egui::vec2(1060.0, 720.0),
        egui::vec2(1680.0, 1050.0),
        egui::vec2(2048.0, 1300.0),
    ] {
        let viewport = Rect::from_min_size(Pos2::ZERO, size);
        let controls = controls_rect(viewport);
        assert_eq!(controls.right(), size.x);
        assert_eq!(controls.top(), 0.0);
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
                let _ = frame_in(&ctx, time, vec![], false, false, size);
            }
            let button = button_hit(button_rect(controls, index), viewport, true);
            assert!(button.width() >= 36.0 && button.height() >= 30.0);
            let _ = frame_in(
                &ctx,
                0.1,
                pointer(button.center(), true),
                false,
                false,
                size,
            );
            let (release, action, _) = frame_in(
                &ctx,
                0.2,
                pointer(button.center(), false),
                false,
                false,
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

#[test]
fn pressing_a_button_then_releasing_over_its_neighbor_does_not_activate_either_or_drag() {
    for index in 0..3 {
        let ctx = context(false, false);
        let from = button_point(index);
        let to = button_point((index + 1) % 3);
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

#[test]
fn faded_controls_are_not_drawn_and_take_no_clicks() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let point = button_point(2);
    for (time, pressed) in [(0.0, true), (0.05, false)] {
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(viewport()),
                time: Some(time),
                events: pointer(point, pressed),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |_| {});
                finish_with(ctx, false, 0.0);
            },
        );
        assert!(commands(&output).is_empty());
    }
}
