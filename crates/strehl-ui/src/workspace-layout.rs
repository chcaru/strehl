//! Persistent proportions, independent of the current bracket or render phase.
use eframe::egui::{self, Color32, CursorIcon, Rect, Sense, Stroke, Ui};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub(crate) struct WorkspaceLayout {
    pub network: f32,
    pub detail: f32,
    pub final_detail: f32,
    pub lower: f32,
    pub fingerprint: f32,
    pub focus_photo: bool,
}
impl Default for WorkspaceLayout {
    fn default() -> Self {
        Self {
            network: 0.20,
            detail: 0.61,
            final_detail: 0.44,
            lower: 0.0,
            fingerprint: 0.0,
            focus_photo: false,
        }
    }
}
impl WorkspaceLayout {
    /// Preserve readable diagnostic columns when docks consume window space.
    /// The process canvas scrolls below 1000 points instead of shrinking its maps.
    pub fn constrain_width(&mut self, width: f32) {
        self.sanitize();
        let width = width.max(1000.0);
        self.final_detail = self.final_detail.max(380.0 / width);
        self.detail = self.detail.max(self.network + 376.0 / width);
    }

    pub fn sanitize(&mut self) {
        if ![
            self.network,
            self.detail,
            self.final_detail,
            self.lower,
            self.fingerprint,
        ]
        .iter()
        .all(|n| n.is_finite())
        {
            *self = Self::default();
        }
        // The process canvas is at least 1000 points wide; keep its capture
        // board above the 160-point paint/hit threshold, including gutters.
        self.network = self.network.clamp(0.18, 0.38);
        self.detail = self.detail.clamp(self.network + 0.22, 0.80);
        self.final_detail = self.final_detail.clamp(0.25, 0.72);
        self.lower = self.lower.clamp(-0.12, 0.20);
        self.fingerprint = self.fingerprint.clamp(-0.04, 0.16);
    }
}

/// A quiet seam becomes an explicit grip on approach. Double-click restores it.
pub(crate) fn seam(ui: &mut Ui, id: &str, rect: Rect, vertical: bool) -> (f32, bool) {
    let id = ui.id().with(id);
    let hit = ui.interact(rect, id, Sense::click_and_drag());
    let allowed = ui.is_enabled()
        && ui.input(|i| i.focused && i.viewport().minimized != Some(true))
        && ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()));
    if !allowed {
        ui.ctx().data_mut(|data| data.remove::<egui::Pos2>(id));
        return (0.0, false);
    }
    let active = hit.hovered() || hit.dragged();
    let p = ui.painter_at(rect);
    let color = if active {
        crate::theme::ACCENT
    } else {
        Color32::from_white_alpha(16)
    };
    let center = rect.center();
    let ends = if vertical {
        [
            egui::pos2(center.x, rect.top()),
            egui::pos2(center.x, rect.bottom()),
        ]
    } else {
        [
            egui::pos2(rect.left(), center.y),
            egui::pos2(rect.right(), center.y),
        ]
    };
    p.line_segment(
        ends,
        Stroke::new(ui.ctx().pixels_per_point().recip(), color),
    );
    let pointer = ui.input(|i| i.pointer.interact_pos());
    if hit.is_pointer_button_down_on()
        && ui.input(|i| i.pointer.primary_pressed())
        && let Some(at) = pointer
    {
        ui.ctx().data_mut(|data| data.insert_temp(id, at));
    }
    let delta = if hit.dragged()
        && let Some(at) = pointer
    {
        ui.ctx().data_mut(|data| {
            let previous = data.get_temp::<egui::Pos2>(id).unwrap_or(at);
            data.insert_temp(id, at);
            if vertical {
                at.x - previous.x
            } else {
                at.y - previous.y
            }
        })
    } else {
        0.0
    };
    if !ui.input(|i| i.pointer.primary_down()) {
        ui.ctx().data_mut(|data| data.remove::<egui::Pos2>(id));
    }
    let reset = hit.double_clicked();
    hit.on_hover_cursor(if vertical {
        CursorIcon::ResizeHorizontal
    } else {
        CursorIcon::ResizeVertical
    })
    .on_hover_text("Drag to resize · double-click to restore");
    (delta, reset)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn frame(ctx: &egui::Context, x: &mut f32, focused: bool, time: f64, events: Vec<egui::Event>) {
        let _ = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(900.0, 500.0),
                )),
                focused,
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    let rect =
                        Rect::from_min_max(egui::pos2(*x - 5.0, 20.0), egui::pos2(*x + 5.0, 480.0));
                    *x += seam(ui, "restore-resize", rect, true).0;
                });
            },
        );
    }
    fn button(at: egui::Pos2, pressed: bool) -> egui::Event {
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        }
    }
    #[test]
    fn taskbar_focus_loss_drops_the_old_resize_pointer_before_restore() {
        let ctx = egui::Context::default();
        let mut x = 300.0;
        let start = egui::pos2(300.0, 200.0);
        frame(&ctx, &mut x, true, 0.0, vec![]);
        frame(
            &ctx,
            &mut x,
            true,
            0.1,
            vec![egui::Event::PointerMoved(start), button(start, true)],
        );
        frame(
            &ctx,
            &mut x,
            true,
            0.2,
            vec![egui::Event::PointerMoved(egui::pos2(330.0, 200.0))],
        );
        assert_eq!(x, 330.0, "the fixture must first perform a real resize");
        frame(
            &ctx,
            &mut x,
            false,
            0.3,
            vec![egui::Event::PointerMoved(egui::pos2(650.0, 200.0))],
        );
        assert_eq!(x, 330.0, "an unfocused window cannot continue a stale drag");
        frame(&ctx, &mut x, true, 0.4, vec![]);
        frame(
            &ctx,
            &mut x,
            true,
            0.5,
            vec![button(egui::pos2(650.0, 200.0), false)],
        );
        assert_eq!(
            x, 330.0,
            "restoring focus cannot replay accumulated pointer travel"
        );
    }
}
