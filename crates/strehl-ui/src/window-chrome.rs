//! The native window controls at the right end of the top bar, and the
//! window's resize edges. The top bar's empty space is the move handle
//! (`drag_space`); there is no title row and no floating dock.
use eframe::egui::{self, Color32, Id, Pos2, Rect, Sense, Stroke, Ui, Vec2, ViewportCommand};

const EDGE: f32 = 5.0;
const CORNER: f32 = 12.0;

/// Minimise, maximise and close, each this wide (the mockup's `.wctl`).
pub(crate) const BUTTON_WIDTH: f32 = 42.0;
/// The top bar reserves this much at its right end for the three buttons.
pub(crate) const CONTROLS_WIDTH: f32 = 3.0 * BUTTON_WIDTH;
/// The top bar's height without its bottom rule.
pub(crate) const CONTROLS_HEIGHT: f32 = 43.0;

/// The three buttons, flush with the window's top-right corner.
pub(crate) fn controls_rect(viewport: Rect) -> Rect {
    Rect::from_min_size(
        egui::pos2(viewport.right() - CONTROLS_WIDTH, viewport.top()),
        egui::vec2(CONTROLS_WIDTH, CONTROLS_HEIGHT),
    )
}
fn button_rect(controls: Rect, index: usize) -> Rect {
    Rect::from_min_size(
        controls.min + egui::vec2(index as f32 * BUTTON_WIDTH, 0.0),
        egui::vec2(BUTTON_WIDTH, controls.height()),
    )
}
/// The part of a button that answers the pointer. While the window can be
/// resized, the outer few pixels at the top and right belong to the resize
/// edges, as they do on a native caption.
fn button_hit(button: Rect, viewport: Rect, resizable: bool) -> Rect {
    if !resizable {
        return button;
    }
    let mut hit = button;
    hit.min.y = hit.min.y.max(viewport.top() + EDGE);
    hit.max.x = hit.max.x.min(viewport.right() - EDGE);
    hit
}

#[derive(Clone, Copy, Default)]
struct TitlePress {
    time: f64,
    point: Pos2,
    origin: Option<Pos2>,
}

/// Native move surfaces have their own hit area, separate from every control.
pub(crate) fn drag_space(ui: &mut Ui, rect: Rect, blocked: bool) {
    let gesture = ui.interact(
        rect,
        ui.id().with("window-drag-title"),
        Sense::click_and_drag(),
    );
    // Each grab surface owns its click history. A secondary rail surface must
    // not clear the dock's first click before its second press is delivered.
    let press_id = ui.id().with("window-title-previous-press");
    if !blocked && gesture.hovered() {
        ui.ctx()
            .set_cursor_icon(if gesture.is_pointer_button_down_on() {
                egui::CursorIcon::Grabbing
            } else {
                egui::CursorIcon::Grab
            });
    }
    let pressed = ui.input(|i| i.pointer.button_pressed(egui::PointerButton::Primary));
    if pressed {
        let pointer = ui.input(|i| i.pointer.interact_pos());
        if !blocked
            && gesture.is_pointer_button_down_on()
            && let Some(point) = pointer
            && rect.contains(point)
        {
            let now = ui.input(|i| i.time);
            let origin = ui.input(|i| i.viewport().outer_rect.map(|r| r.min));
            let thresholds = ui.ctx().options(|o| {
                (
                    o.input_options.max_double_click_delay,
                    o.input_options.max_click_dist,
                )
            });
            let previous = ui
                .ctx()
                .data_mut(|data| data.remove_temp::<TitlePress>(press_id));
            let doubled = previous.is_some_and(|previous| {
                now - previous.time <= thresholds.0
                    && point.distance(previous.point) <= thresholds.1
                    && match (origin, previous.origin) {
                        (Some(a), Some(b)) => a.distance(b) <= 1.0,
                        (None, None) => true,
                        _ => false,
                    }
            });
            if doubled {
                toggle_maximized(ui.ctx());
            } else {
                ui.ctx().data_mut(|data| {
                    data.insert_temp(
                        press_id,
                        TitlePress {
                            time: now,
                            point,
                            origin,
                        },
                    )
                });
                prepare_native_drag();
                ui.ctx().send_viewport_cmd(ViewportCommand::StartDrag);
            }
        } else {
            ui.ctx()
                .data_mut(|data| data.remove::<TitlePress>(press_id));
        }
    }
    gesture.on_hover_text("Drag to move window · double-click to maximize / restore");
}

fn toggle_maximized(ctx: &egui::Context) {
    let (fullscreen, maximized) = ctx.input(|i| {
        (
            i.viewport().fullscreen.unwrap_or(false),
            i.viewport().maximized.unwrap_or(false),
        )
    });
    ctx.send_viewport_cmd(if fullscreen {
        ViewportCommand::Fullscreen(false)
    } else {
        ViewportCommand::Maximized(!maximized)
    });
}

/// Run after application modals: the resize edges, then the three window
/// buttons. The buttons sit over the top bar's reserved right end, in their
/// own foreground layer, so they still work while a modal dims the window.
/// They are drawn at `opacity` (focus mode fades the chrome); at zero they
/// are not drawn and do not take clicks.
pub(crate) fn finish_with(ctx: &egui::Context, modal: bool, opacity: f32) {
    finish_resize(ctx, modal);
    if opacity <= 0.01 {
        return;
    }
    let viewport = ctx.viewport_rect();
    let controls = controls_rect(viewport);
    let t = crate::studio_theme::tokens(ctx);
    let maximized = ctx.input(|i| {
        i.viewport().maximized.unwrap_or(false) || i.viewport().fullscreen.unwrap_or(false)
    });
    let resizable = !maximized && !modal;
    // The layer answers the pointer only where the buttons do, so the resize
    // strips along the top and right edges stay reachable beneath it.
    let hit_area = if resizable {
        Rect::from_min_max(
            egui::pos2(controls.left(), viewport.top() + EDGE),
            egui::pos2(viewport.right() - EDGE, controls.bottom()),
        )
    } else {
        controls
    };
    let layer = egui::LayerId::new(egui::Order::Foreground, Id::new("native-window-controls"));
    ctx.move_to_top(layer);
    egui::Area::new(layer.id)
        .order(layer.order)
        .fixed_pos(hit_area.min)
        .default_size(hit_area.size())
        .movable(false)
        .constrain(false)
        .sense(Sense::hover())
        .show(ctx, |ui| {
            ui.set_opacity(opacity);
            ui.set_min_size(hit_area.size());
            ui.set_max_size(hit_area.size());
            let mut painter = ctx.layer_painter(layer);
            painter.set_opacity(opacity);
            painter.rect_filled(controls, 0.0, t.panel);
            for index in 0..3 {
                let rect = button_rect(controls, index);
                let label = match index {
                    0 => "Minimize window",
                    1 if maximized => "Restore window",
                    1 => "Maximize window",
                    _ => "Close window",
                };
                let response = ui.interact(
                    button_hit(rect, viewport, resizable),
                    Id::new(("native-window-button", index)),
                    Sense::click(),
                );
                response.widget_info(|| {
                    egui::WidgetInfo::labeled(egui::WidgetType::Button, true, label)
                });
                let active = ui.input(|i| i.viewport().focused.unwrap_or(i.focused));
                let ink = if response.hovered() || (active && index == 2) {
                    t.ink
                } else if active {
                    t.ink2
                } else {
                    t.ink3
                };
                if response.hovered() {
                    painter.rect_filled(rect, 0.0, t.raised);
                }
                if response.has_focus() {
                    painter.rect_stroke(
                        rect.shrink(2.0),
                        0.0,
                        Stroke::new(1.0_f32, t.accent),
                        egui::StrokeKind::Inside,
                    );
                }
                window_icon(&painter, rect.center(), index, maximized, ink, t.panel);
                if response.clicked() {
                    match index {
                        0 => ctx.send_viewport_cmd(ViewportCommand::Minimized(true)),
                        1 => toggle_maximized(ctx),
                        _ => ctx.send_viewport_cmd(ViewportCommand::Close),
                    }
                }
                response.on_hover_text(label);
            }
            crate::theme::rule(
                &painter,
                controls.left_top(),
                controls.left_bottom(),
                t.line,
            );
        });
    // Keep the buttons above application modals and the resize layers,
    // including the frame after focus or maximise changes.
    ctx.move_to_top(layer);
}

fn finish_resize(ctx: &egui::Context, modal: bool) {
    let viewport = ctx.viewport_rect();
    let fixed = ctx.input(|i| {
        i.viewport().maximized.unwrap_or(false) || i.viewport().fullscreen.unwrap_or(false)
    });
    if fixed || modal {
        return;
    }
    for (index, (rect, direction, cursor)) in resize_regions(viewport).into_iter().enumerate() {
        egui::Area::new(Id::new(("native-window-edge", index)))
            .order(egui::Order::Foreground)
            .fixed_pos(rect.min)
            .default_size(rect.size())
            .movable(false)
            .constrain(false)
            .sense(Sense::hover())
            .show(ctx, |ui| {
                ui.set_min_size(rect.size());
                let response = ui.interact(rect, ui.id().with("resize"), Sense::click_and_drag());
                if response.hovered() {
                    ctx.set_cursor_icon(cursor);
                }
                if response.is_pointer_button_down_on()
                    && ui.input(|i| i.pointer.button_pressed(egui::PointerButton::Primary))
                {
                    prepare_native_drag();
                    ctx.send_viewport_cmd(ViewportCommand::BeginResize(direction));
                }
            });
    }
}

fn prepare_native_drag() {
    #[cfg(windows)]
    crate::window_native::prepare_drag();
}

fn window_icon(
    p: &egui::Painter,
    center: Pos2,
    index: usize,
    maximized: bool,
    color: Color32,
    fill: Color32,
) {
    let stroke = Stroke::new(1.0 / p.ctx().pixels_per_point(), color);
    let rect = Rect::from_center_size(center, Vec2::splat(9.0));
    match index {
        0 => p.line_segment(
            [
                center - egui::vec2(4.5, -2.5),
                center + egui::vec2(4.5, 2.5),
            ],
            stroke,
        ),
        1 if maximized => {
            p.rect_stroke(
                rect.translate(egui::vec2(1.5, -1.5)),
                0.0,
                stroke,
                egui::StrokeKind::Inside,
            );
            p.rect_filled(rect.translate(egui::vec2(-1.0, 1.0)), 0.0, fill);
            p.rect_stroke(
                rect.translate(egui::vec2(-1.0, 1.0)),
                0.0,
                stroke,
                egui::StrokeKind::Inside,
            )
        }
        1 => p.rect_stroke(rect, 0.0, stroke, egui::StrokeKind::Inside),
        _ => {
            p.line_segment([rect.left_top(), rect.right_bottom()], stroke);
            p.line_segment([rect.right_top(), rect.left_bottom()], stroke)
        }
    };
}

fn resize_regions(rect: Rect) -> [(Rect, egui::ResizeDirection, egui::CursorIcon); 12] {
    use egui::{CursorIcon as C, ResizeDirection as D};
    let region = |x1, y1, x2, y2| Rect::from_min_max(egui::pos2(x1, y1), egui::pos2(x2, y2));
    let (l, r, t, b) = (rect.left(), rect.right(), rect.top(), rect.bottom());
    [
        (
            region(l, t, l + CORNER, t + EDGE),
            D::NorthWest,
            C::ResizeNwSe,
        ),
        (
            region(r - CORNER, t, r, t + EDGE),
            D::NorthEast,
            C::ResizeNeSw,
        ),
        (
            region(l, b - EDGE, l + CORNER, b),
            D::SouthWest,
            C::ResizeNeSw,
        ),
        (
            region(r - CORNER, b - EDGE, r, b),
            D::SouthEast,
            C::ResizeNwSe,
        ),
        (
            region(l + CORNER, t, r - CORNER, t + EDGE),
            D::North,
            C::ResizeVertical,
        ),
        (
            region(l + CORNER, b - EDGE, r - CORNER, b),
            D::South,
            C::ResizeVertical,
        ),
        (
            region(l, t + EDGE, l + EDGE, t + CORNER),
            D::NorthWest,
            C::ResizeNwSe,
        ),
        (
            region(r - EDGE, t + EDGE, r, t + CORNER),
            D::NorthEast,
            C::ResizeNeSw,
        ),
        (
            region(l, b - CORNER, l + EDGE, b - EDGE),
            D::SouthWest,
            C::ResizeNeSw,
        ),
        (
            region(r - EDGE, b - CORNER, r, b - EDGE),
            D::SouthEast,
            C::ResizeNwSe,
        ),
        (
            region(l, t + CORNER, l + EDGE, b - CORNER),
            D::West,
            C::ResizeHorizontal,
        ),
        (
            region(r - EDGE, t + CORNER, r, b - CORNER),
            D::East,
            C::ResizeHorizontal,
        ),
    ]
}

#[cfg(test)]
#[path = "window-chrome-tests.rs"]
mod tests;
