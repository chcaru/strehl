//! Direct manipulation of one aligned sampling window. The photograph is
//! context; this rectangle is the aperture painted by every detail view.
use crate::theme::{ACCENT, BG, INK};
use eframe::egui::{self, Color32, FontId, Painter, Pos2, Rect, Stroke, Ui, Vec2};

#[derive(Clone, Copy)]
struct Grab {
    pointer: Pos2,
    aperture: Rect,
    resize: bool,
}

#[derive(Default)]
pub(crate) struct DetailNavigator {
    grab: Option<Grab>,
    hovered: bool,
    resizing: bool,
}

#[derive(Default)]
pub(crate) struct Navigation {
    pub reset: bool,
    pub owns_drag: bool,
    pub owns_click: bool,
    pub owns_scroll: bool,
    pub view: Option<(Pos2, f32)>,
    pub zoom: Option<(f32, Pos2)>,
}

impl DetailNavigator {
    pub(crate) fn clear(&mut self) {
        *self = Self::default();
    }
    pub(crate) fn hovered(&self) -> bool {
        self.hovered
    }

    #[allow(clippy::too_many_arguments)]
    pub(crate) fn interact(
        &mut self,
        ui: &mut Ui,
        response: &egui::Response,
        destination: Rect,
        clip: Rect,
        aperture: Rect,
        // Completed photographs permit continuous resizing back to Scene.
        full_range: bool,
    ) -> Navigation {
        let mut result = Navigation::default();
        let reset_gesture = crate::image_gesture::reset(ui, response);
        if reset_gesture.reset {
            self.clear();
            return Navigation {
                reset: true,
                owns_drag: true,
                owns_click: true,
                owns_scroll: true,
                ..Default::default()
            };
        }
        if !ui.is_enabled()
            || !ui.input(|input| {
                input.focused
                    && input.viewport().focused != Some(false)
                    && input.viewport().minimized != Some(true)
            })
            || egui::Popup::is_any_open(ui.ctx())
            || ui.input(|input| input.key_pressed(egui::Key::Escape))
            || !ui
                .ctx()
                .memory(|memory| memory.is_above_modal_layer(ui.layer_id()))
        {
            self.clear();
            return result;
        }
        let locator = project(destination, aperture);
        let grip = Rect::from_center_size(locator.right_bottom(), Vec2::splat(18.0));
        let pointer = ui.input(|input| input.pointer.interact_pos());
        let hovered = response.hovered()
            && pointer.is_some_and(|at| locator.contains(at) && clip.contains(at));
        let grip_hovered = response.hovered()
            && aperture.width() < 0.99
            && pointer.is_some_and(|at| grip.contains(at) && clip.contains(at));
        self.hovered = hovered || grip_hovered;
        // Capture the press, not drag_started: egui may accumulate several
        // sub-threshold movements before it classifies a gesture as a drag.
        if response.is_pointer_button_down_on()
            && ui.input(|input| input.pointer.primary_pressed())
            && self.hovered
            && aperture.width() < 0.99
            && let Some(pointer) = pointer
        {
            self.grab = Some(Grab {
                pointer,
                aperture,
                resize: grip_hovered,
            });
        }
        if let Some(grab) = self.grab {
            result.owns_drag = true;
            result.owns_click = true;
            self.resizing = grab.resize;
            if response.dragged()
                && !reset_gesture.pending
                && let Some(pointer) = pointer
                && pointer != grab.pointer
            {
                let delta = (pointer - grab.pointer) / destination.size();
                if grab.resize {
                    // The bottom-right handle keeps the opposite corner fixed.
                    // Project motion onto the normalized diagonal so portrait
                    // and landscape photographs behave identically.
                    let side = (grab.aperture.width() + (delta.x + delta.y) * 0.5)
                        .clamp(1.0 / 16.0, if full_range { 1.0 } else { 0.5 })
                        .min(1.0 - grab.aperture.min.x)
                        .min(1.0 - grab.aperture.min.y);
                    result.view = Some((grab.aperture.min + Vec2::splat(side * 0.5), side.recip()));
                } else {
                    let half = grab.aperture.size() * 0.5;
                    let center = (grab.aperture.center() + delta)
                        .clamp(Pos2::ZERO + half, egui::pos2(1.0, 1.0) - half);
                    result.view = Some((center, grab.aperture.width().recip()));
                }
                if let Some((center, zoom)) = result.view {
                    // Rebase after every actual movement, including a clamp.
                    // Reversing at an edge must move immediately, without
                    // paying back pointer motion that happened outside it.
                    self.grab = Some(Grab {
                        pointer,
                        aperture: Rect::from_center_size(center, Vec2::splat(zoom.recip())),
                        resize: grab.resize,
                    });
                }
                ui.ctx().request_repaint();
            }
        }
        let ctrl = ui.input(|input| input.modifiers.ctrl || input.modifiers.command);
        if self.hovered && !ctrl && !reset_gesture.pending {
            let wheel = ui.input(|input| input.raw_scroll_delta.y);
            let pinch = crate::process_region_probe::zoom_delta(ui);
            let factor = if (pinch - 1.0).abs() > f32::EPSILON {
                pinch
            } else {
                (wheel * 0.004).exp()
            };
            if factor.is_finite() && (factor - 1.0).abs() > f32::EPSILON {
                result.owns_scroll = true;
                if let Some(pointer) = pointer {
                    let anchor = ((pointer - locator.min) / locator.size())
                        .clamp(Vec2::ZERO, Vec2::splat(1.0));
                    result.zoom = Some((factor, Pos2::ZERO + anchor));
                    ui.ctx().request_repaint();
                }
            }
        }
        if self.grab.is_some() {
            ui.ctx().set_cursor_icon(if self.resizing {
                egui::CursorIcon::ResizeNwSe
            } else {
                egui::CursorIcon::Grabbing
            });
        } else if self.hovered {
            ui.ctx().set_cursor_icon(if grip_hovered {
                egui::CursorIcon::ResizeNwSe
            } else {
                egui::CursorIcon::Grab
            });
        }
        if !ui.input(|input| input.pointer.primary_down()) {
            self.grab = None;
            self.resizing = false;
        }
        result
    }

    pub(crate) fn paint(
        &self,
        painter: &Painter,
        destination: Rect,
        aperture: Rect,
        pin: Pos2,
        linked_hover: bool,
    ) {
        let locator = project(destination, aperture);
        let active = self.hovered || self.grab.is_some() || linked_hover;
        let color = if active {
            ACCENT
        } else {
            Color32::from_white_alpha(175)
        };
        if active && aperture.width() < 0.99 {
            let shade = Color32::from_black_alpha(32);
            for region in [
                Rect::from_min_max(
                    destination.min,
                    egui::pos2(destination.right(), locator.top()),
                ),
                Rect::from_min_max(
                    egui::pos2(destination.left(), locator.bottom()),
                    destination.max,
                ),
                Rect::from_min_max(
                    egui::pos2(destination.left(), locator.top()),
                    locator.left_bottom(),
                ),
                Rect::from_min_max(
                    locator.right_top(),
                    egui::pos2(destination.right(), locator.bottom()),
                ),
            ] {
                painter.rect_filled(region, 0.0, shade);
            }
        }
        // A dark under-stroke keeps the locator readable over both bright and
        // dark samples. Corner brackets carry the interaction, without chrome.
        painter.rect_stroke(
            locator,
            0.0,
            Stroke::new(2.6_f32, Color32::from_black_alpha(130)),
            egui::StrokeKind::Inside,
        );
        painter.rect_stroke(
            locator,
            0.0,
            Stroke::new(0.8_f32, color.gamma_multiply(0.7)),
            egui::StrokeKind::Inside,
        );
        let length = (locator.width().min(locator.height()) * 0.22).clamp(4.0, 10.0);
        for (corner, dx, dy) in [
            (locator.left_top(), 1.0, 1.0),
            (locator.right_top(), -1.0, 1.0),
            (locator.left_bottom(), 1.0, -1.0),
            (locator.right_bottom(), -1.0, -1.0),
        ] {
            painter.line_segment(
                [corner + egui::vec2(dx * length, 0.0), corner],
                Stroke::new(1.5_f32, color),
            );
            painter.line_segment(
                [corner, corner + egui::vec2(0.0, dy * length)],
                Stroke::new(1.5_f32, color),
            );
        }
        let at = destination.min + pin.to_vec2() * destination.size();
        painter.circle_stroke(at, 2.6, Stroke::new(0.9_f32, color));
        if aperture.width() < 0.99 {
            let handle = Rect::from_center_size(locator.right_bottom(), Vec2::splat(5.0));
            painter.rect_filled(handle, 0.0, color);
        }
        let label = if active {
            format!("{:.1}×  LINKED DETAILS", aperture.width().recip())
        } else {
            format!("{:.1}×", aperture.width().recip())
        };
        let galley = painter.layout_no_wrap(label, FontId::monospace(8.0), INK);
        let origin = egui::pos2(
            locator.left().clamp(
                destination.left(),
                (destination.right() - galley.size().x - 8.0).max(destination.left()),
            ),
            (locator.top() - 19.0).max(destination.top() + 3.0),
        );
        let tag = Rect::from_min_size(origin, galley.size() + egui::vec2(8.0, 6.0));
        painter.rect_filled(tag, 0.0, BG.gamma_multiply(0.94));
        painter.galley(tag.min + egui::vec2(4.0, 3.0), galley, INK);
    }
}

fn project(destination: Rect, aperture: Rect) -> Rect {
    Rect::from_min_max(
        destination.min + aperture.min.to_vec2() * destination.size(),
        destination.min + aperture.max.to_vec2() * destination.size(),
    )
}
