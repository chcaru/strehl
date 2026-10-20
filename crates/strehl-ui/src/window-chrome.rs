//! One compact, persistent native window dock; no full-width title row.
use crate::theme::{ACCENT, AMBER, BG, INK, LINE, MUTED, PANEL, RAISED};
use eframe::egui::{self, Color32, Id, Pos2, Rect, Sense, Stroke, Ui, Vec2, ViewportCommand};

const EDGE: f32 = 5.0;
const CORNER: f32 = 12.0;

pub(crate) const RAIL_WIDTH: f32 = 48.0;
pub(crate) const DOCK_WIDTH: f32 = 192.0;
pub(crate) const DOCK_HEIGHT: f32 = 30.0;
const DOCK_INSET: f32 = 6.0;
const GRIP_WIDTH: f32 = 84.0;
const BUTTON_WIDTH: f32 = 36.0;

/// Reserve this corner only. The rest of the workspace reaches the top edge.
pub(crate) fn dock_rect(viewport: Rect) -> Rect {
    Rect::from_min_size(
        egui::pos2(
            viewport.right() - DOCK_INSET - DOCK_WIDTH,
            viewport.top() + DOCK_INSET,
        ),
        egui::vec2(DOCK_WIDTH, DOCK_HEIGHT),
    )
}
fn grip_rect(dock: Rect) -> Rect {
    Rect::from_min_size(dock.min, egui::vec2(GRIP_WIDTH, dock.height()))
}
fn button_rect(dock: Rect, index: usize) -> Rect {
    Rect::from_min_size(
        dock.min + egui::vec2(GRIP_WIDTH + index as f32 * BUTTON_WIDTH, 0.0),
        egui::vec2(BUTTON_WIDTH, dock.height()),
    )
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

/// Run after application modals. Only these small native-control/edge areas
/// sit above them; no full-window foreground hit surface can consume photos.
pub(crate) fn finish(ctx: &egui::Context, modal: bool) {
    finish_resize(ctx, modal);
    let viewport = ctx.viewport_rect();
    let controls = dock_rect(viewport);
    let layer = egui::LayerId::new(egui::Order::Foreground, Id::new("native-window-controls"));
    ctx.move_to_top(layer);
    egui::Area::new(layer.id)
        .order(layer.order)
        .fixed_pos(controls.min)
        .default_size(controls.size())
        .movable(false)
        .constrain(false)
        .sense(Sense::hover())
        .show(ctx, |ui| {
            ui.set_min_size(controls.size());
            ui.painter().rect_filled(controls, 0.0, PANEL);
            let grip = grip_rect(controls);
            let grip_hovered = ui.rect_contains_pointer(grip);
            if grip_hovered {
                ui.painter().rect_filled(grip, 0.0, RAISED);
            }
            let grip_ink = if grip_hovered { INK } else { MUTED };
            for row in 0..3 {
                for column in 0..2 {
                    ui.painter().circle_filled(
                        egui::pos2(
                            grip.left() + 11.0 + column as f32 * 4.0,
                            grip.center().y - 4.0 + row as f32 * 4.0,
                        ),
                        0.7,
                        grip_ink,
                    );
                }
            }
            ui.painter().text(
                grip.min + egui::vec2(27.0, grip.height() * 0.5),
                egui::Align2::LEFT_CENTER,
                "Move",
                egui::FontId::proportional(10.5),
                grip_ink,
            );
            // Native chrome remains usable while an application modal is open.
            drag_space(ui, grip, false);
            let maximized = ctx.input(|i| {
                i.viewport().maximized.unwrap_or(false) || i.viewport().fullscreen.unwrap_or(false)
            });
            for index in 0..3 {
                let rect = button_rect(controls, index);
                let label = match index {
                    0 => "Minimize window",
                    1 if maximized => "Restore window",
                    1 => "Maximize window",
                    _ => "Close window",
                };
                let response = ui.interact(
                    rect,
                    Id::new(("native-window-button", index)),
                    Sense::click(),
                );
                response.widget_info(|| {
                    egui::WidgetInfo::labeled(egui::WidgetType::Button, true, label)
                });
                let active = ui.input(|i| i.viewport().focused.unwrap_or(i.focused));
                let ink = if response.hovered() && index == 2 {
                    AMBER
                } else if active {
                    INK
                } else {
                    MUTED
                };
                ui.painter().rect_filled(
                    rect,
                    0.0,
                    if response.hovered() { RAISED } else { PANEL },
                );
                if response.has_focus() {
                    ui.painter().rect_stroke(
                        rect.shrink(2.0),
                        0.0,
                        Stroke::new(1.0_f32, ACCENT),
                        egui::StrokeKind::Inside,
                    );
                }
                window_icon(ui.painter(), rect.center(), index, maximized, ink);
                if response.clicked() {
                    match index {
                        0 => ctx.send_viewport_cmd(ViewportCommand::Minimized(true)),
                        1 => toggle_maximized(ctx),
                        _ => ctx.send_viewport_cmd(ViewportCommand::Close),
                    }
                }
                response.on_hover_text(label);
            }
            let painter = ui.painter();
            for x in [controls.left(), grip.right(), controls.right()] {
                crate::theme::rule(
                    painter,
                    egui::pos2(x, controls.top()),
                    egui::pos2(x, controls.bottom()),
                    LINE,
                );
            }
            crate::theme::rule(painter, controls.left_top(), controls.right_top(), LINE);
            crate::theme::rule(
                painter,
                controls.left_bottom(),
                controls.right_bottom(),
                LINE,
            );
        });
    // Keep chrome above application modal and resize layers, including the
    // frame after focus/maximize changes. Only the dock owns this layer.
    ctx.move_to_top(layer);
}

/// Legacy test permutations share the ordinary workspace's native affordances.
#[cfg(test)]
pub(crate) fn finish_spatial(ctx: &egui::Context, modal: bool) {
    finish(ctx, modal);
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

fn window_icon(p: &egui::Painter, center: Pos2, index: usize, maximized: bool, color: Color32) {
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
            p.rect_filled(rect.translate(egui::vec2(-1.0, 1.0)), 0.0, BG);
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
