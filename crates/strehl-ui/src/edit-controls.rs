//! Quiet, aligned photo controls with the same reset and keyboard contract.
use crate::theme::{self, ACCENT, INK, LINE, MUTED, PANEL, RAISED};
use eframe::egui::{self, Align2, FontId, Rect, RichText, Sense, Stroke, Ui};
use std::ops::RangeInclusive;

pub(crate) const ACTION_HEIGHT: f32 = 26.0;

/// Fixed header/shelf commands share the scrolling controls' content edges.
/// The scrollbar gutter remains reserved as sections open and close.
pub(crate) fn pane_margin(ui: &Ui, vertical: i8) -> egui::Margin {
    egui::Margin {
        left: 12,
        right: 12 + ui.spacing().scroll.allocated_width().round() as i8,
        top: vertical,
        bottom: vertical,
    }
}

/// Shared geometry for pane commands, including secondary actions. A short
/// label should not turn into a smaller target or move the row's baseline.
pub(crate) fn action_button(ui: &mut Ui, text: &str, width: f32) -> egui::Response {
    ui.add_sized(
        [width.max(1.0), ACTION_HEIGHT],
        egui::Button::new(RichText::new(text).size(11.0)).truncate(),
    )
}

pub(crate) fn adjustment_scope<R>(
    ui: &mut Ui,
    document: Option<&std::path::Path>,
    selected: Option<&str>,
    contents: impl FnOnce(&mut Ui) -> R,
) -> egui::InnerResponse<R> {
    ui.push_id(("photo-controls", document, selected), contents)
}

pub(crate) fn rule(ui: &mut Ui) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 1.0), Sense::hover());
    theme::rule(ui.painter(), rect.left_center(), rect.right_center(), LINE);
}

pub(crate) fn section(ui: &mut Ui, key: &str, title: &str, default_open: bool) -> bool {
    // The pane's organization persists across region changes; only numeric
    // editing state is isolated by the active photograph/region scope.
    let id = egui::Id::new(("photo-edit-section", key));
    let mut open = ui
        .ctx()
        .data_mut(|data| data.get_temp::<bool>(id))
        .unwrap_or(default_open);
    let (rect, hit) =
        ui.allocate_exact_size(egui::vec2(ui.available_width(), 29.0), Sense::click());
    hit.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::CollapsingHeader, true, title));
    if hit.clicked() {
        open = !open;
        ui.ctx().data_mut(|data| data.insert_temp(id, open));
    }
    ui.painter()
        .rect_filled(rect, 0.0, if hit.hovered() { RAISED } else { PANEL });
    theme::rule(ui.painter(), rect.left_top(), rect.right_top(), LINE);
    let c = rect.left_center() + egui::vec2(12.0, 0.0);
    let points = if open {
        [
            c + egui::vec2(-3.0, -1.5),
            c + egui::vec2(0.0, 1.5),
            c + egui::vec2(3.0, -1.5),
        ]
    } else {
        [
            c + egui::vec2(-1.5, -3.0),
            c + egui::vec2(1.5, 0.0),
            c + egui::vec2(-1.5, 3.0),
        ]
    };
    ui.painter().add(egui::Shape::line(
        points.to_vec(),
        Stroke::new(1.0f32, MUTED),
    ));
    ui.painter().text(
        rect.left_center() + egui::vec2(25.0, 0.0),
        Align2::LEFT_CENTER,
        title,
        FontId::proportional(11.0),
        INK,
    );
    open
}

/// A full-width track beneath a left-aligned label and right-aligned numeric
/// editor. No label/number/track competes for a narrow sidebar's horizontal space.
pub(crate) fn slider(
    ui: &mut Ui,
    label: &str,
    value: &mut f32,
    range: RangeInclusive<f32>,
    default: f32,
    decimals: usize,
    suffix: &str,
) -> egui::Response {
    ui.push_id(label, |ui| {
        let initial = *value;
        let width = ui.available_width().max(80.0);
        let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 40.0), Sense::hover());
        let number = Rect::from_min_max(
            egui::pos2(rect.right() - 62.0, rect.top()),
            egui::pos2(rect.right(), rect.top() + 22.0),
        );
        let label_rect =
            Rect::from_min_max(rect.min, egui::pos2(number.left() - 4.0, number.bottom()));
        let label_hit = ui.interact(label_rect, ui.id().with("label"), Sense::click());
        ui.painter().with_clip_rect(label_rect).text(
            label_rect.left_center(),
            Align2::LEFT_CENTER,
            label,
            FontId::proportional(11.0),
            INK,
        );
        let number_hit = ui
            .scope(|ui| {
                // DragValue otherwise inherits the pane's taller command
                // height and paints beyond its allocated label/value row.
                ui.spacing_mut().interact_size.y = number.height();
                ui.spacing_mut().button_padding = egui::vec2(4.0, 2.0);
                ui.visuals_mut().override_text_color = Some(if (*value - default).abs() > 0.0001 {
                    ACCENT
                } else {
                    MUTED
                });
                ui.put(
                    number,
                    egui::DragValue::new(value)
                        .range(range.clone())
                        .speed(if decimals > 0 { 0.02 } else { 0.5 })
                        .fixed_decimals(decimals)
                        .suffix(suffix),
                )
            })
            .inner;
        let track = Rect::from_min_max(
            egui::pos2(rect.left(), rect.top() + 24.0),
            egui::pos2(rect.right(), rect.bottom()),
        );
        let mut track_ui = ui.new_child(egui::UiBuilder::new().id_salt("track").max_rect(track));
        track_ui.spacing_mut().slider_width = track.width();
        track_ui.spacing_mut().slider_rail_height = 2.0;
        track_ui.spacing_mut().interact_size.y = 16.0;
        let track_hit = track_ui.add(egui::Slider::new(value, range).show_value(false));
        let number_id = number_hit.id;
        let mut hit = label_hit.union(number_hit).union(track_hit);
        // Slider's drag-only response does not report click counts. Match the
        // pointer's double click within this control's visible, topmost rect.
        let mut reset = hit.double_clicked()
            || (ui.is_enabled()
                && ui.rect_contains_pointer(rect)
                && ui.input(|i| {
                    i.pointer
                        .button_double_clicked(egui::PointerButton::Primary)
                }));
        hit.context_menu(|ui| {
            if ui.button(format!("Reset {label}")).clicked() {
                reset = true;
                ui.close();
            }
        });
        if reset {
            *value = default;
            // DragValue's first click enters text editing. Discard its cached
            // pre-reset string, or losing focus later silently restores it.
            ui.data_mut(|data| {
                data.remove_temp::<String>(number_id);
            });
            ui.memory_mut(|memory| memory.surrender_focus(number_id));
        }
        if *value != initial {
            hit.mark_changed();
        }
        hit.on_hover_text("Drag to adjust · click the value to type · double-click to reset")
    })
    .inner
}

pub(super) fn quiet_button(ui: &mut Ui, text: &str, selected: bool) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).size(11.0).color(if selected {
            ACCENT
        } else {
            MUTED
        }))
        .min_size(egui::vec2(0.0, ACTION_HEIGHT))
        .truncate()
        .selected(selected)
        .frame(selected),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame(ctx: &egui::Context, value: &mut f32, time: f64, events: Vec<egui::Event>) -> Rect {
        let mut bounds = Rect::NOTHING;
        let _ = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(230.0, 200.0),
                )),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    bounds = slider(ui, "Exposure", value, -8.0..=8.0, 0.0, 2, " EV").rect;
                });
            },
        );
        bounds
    }

    fn pointer(at: egui::Pos2, pressed: bool) -> Vec<egui::Event> {
        vec![
            egui::Event::PointerMoved(at),
            egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed,
                modifiers: egui::Modifiers::NONE,
            },
        ]
    }

    #[test]
    fn narrow_photo_controls_fit_and_double_click_label_resets() {
        let ctx = egui::Context::default();
        let mut value = 2.75;
        let rect = frame(&ctx, &mut value, 0.0, vec![]);
        assert!(rect.left() >= 0.0 && rect.right() <= 230.0);
        let label = rect.left_top() + egui::vec2(18.0, 7.0);
        frame(&ctx, &mut value, 0.1, pointer(label, true));
        frame(&ctx, &mut value, 0.15, pointer(label, false));
        assert_eq!(value, 2.75, "A single label click must not change exposure");
        frame(&ctx, &mut value, 0.22, pointer(label, true));
        frame(&ctx, &mut value, 0.27, pointer(label, false));
        assert_eq!(
            value, 0.0,
            "A real double click must reset the actual control"
        );
    }

    #[test]
    fn track_and_numeric_double_click_resets_survive_losing_focus() {
        for numeric in [false, true] {
            let ctx = egui::Context::default();
            let mut value = 2.75;
            let rect = frame(&ctx, &mut value, 0.0, vec![]);
            let at = if numeric {
                rect.right_top() + egui::vec2(-25.0, 8.0)
            } else {
                rect.left_top() + egui::vec2(50.0, 26.0)
            };
            frame(&ctx, &mut value, 0.1, pointer(at, true));
            frame(&ctx, &mut value, 0.15, pointer(at, false));
            frame(&ctx, &mut value, 0.22, pointer(at, true));
            frame(&ctx, &mut value, 0.27, pointer(at, false));
            assert_eq!(value, 0.0, "double click did not reset; numeric={numeric}");
            frame(
                &ctx,
                &mut value,
                0.35,
                pointer(egui::pos2(20.0, 150.0), true),
            );
            frame(
                &ctx,
                &mut value,
                0.4,
                pointer(egui::pos2(20.0, 150.0), false),
            );
            frame(&ctx, &mut value, 0.5, vec![]);
            assert_eq!(
                value, 0.0,
                "old numeric edit returned on focus loss; numeric={numeric}"
            );
        }
    }

    #[test]
    fn focused_numeric_text_cannot_cross_document_or_region_scope() {
        fn scoped_frame(
            ctx: &egui::Context,
            document: &str,
            region: Option<&str>,
            value: &mut f32,
            time: f64,
            events: Vec<egui::Event>,
            isolated: bool,
        ) -> Rect {
            let mut bounds = Rect::NOTHING;
            let _ = ctx.run(
                egui::RawInput {
                    screen_rect: Some(Rect::from_min_size(
                        egui::Pos2::ZERO,
                        egui::vec2(230.0, 200.0),
                    )),
                    time: Some(time),
                    events,
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default().show(ctx, |ui| {
                        let mut draw = |ui: &mut Ui| {
                            slider(ui, "Exposure", value, -8.0..=8.0, 0.0, 2, " EV").rect
                        };
                        bounds = if isolated {
                            adjustment_scope(ui, Some(std::path::Path::new(document)), region, draw)
                                .inner
                        } else {
                            draw(ui)
                        };
                    });
                },
            );
            bounds
        }

        for (old_document, old_region, new_document, new_region) in [
            ("first.tiff", None, "first.tiff", Some("mask-b")),
            ("first.tiff", Some("mask-a"), "first.tiff", Some("mask-b")),
            ("first.tiff", Some("mask-a"), "second.tiff", Some("mask-a")),
        ] {
            for isolated in [false, true] {
                let ctx = egui::Context::default();
                let mut old_value = 2.25;
                let rect = scoped_frame(
                    &ctx,
                    old_document,
                    old_region,
                    &mut old_value,
                    0.0,
                    vec![],
                    isolated,
                );
                let number = rect.right_top() + egui::vec2(-25.0, 8.0);
                for (time, events) in [
                    (0.1, pointer(number, true)),
                    (0.15, pointer(number, false)),
                    (0.18, vec![]),
                    (0.2, vec![egui::Event::Text("-3.25".into())]),
                ] {
                    scoped_frame(
                        &ctx,
                        old_document,
                        old_region,
                        &mut old_value,
                        time,
                        events,
                        isolated,
                    );
                }
                assert_eq!(
                    old_value, -3.25,
                    "fixture must edit the real numeric control"
                );
                let focused = ctx
                    .memory(|memory| memory.focused())
                    .expect("numeric field owns focus");
                assert_eq!(
                    ctx.data_mut(|data| data.get_temp::<String>(focused))
                        .as_deref(),
                    Some("-3.25"),
                    "fixture must retain the text that could leak across scope"
                );
                // A document/agent selection can change scope while the user is
                // typing. The next digit must not continue an old field's edit
                // session against a newly selected adjustment.
                let mut new_value = 1.75;
                scoped_frame(
                    &ctx,
                    new_document,
                    new_region,
                    &mut new_value,
                    0.3,
                    vec![],
                    isolated,
                );
                if !isolated {
                    assert_eq!(
                        ctx.data_mut(|data| data.get_temp::<String>(focused))
                            .as_deref(),
                        Some("-3.25"),
                        "negative control must retain the old field's text after switching scope"
                    );
                }
                for (time, events) in [
                    (0.35, vec![egui::Event::Text("7".into())]),
                    (0.4, pointer(egui::pos2(20.0, 150.0), true)),
                    (0.45, pointer(egui::pos2(20.0, 150.0), false)),
                    (0.5, vec![]),
                ] {
                    scoped_frame(
                        &ctx,
                        new_document,
                        new_region,
                        &mut new_value,
                        time,
                        events,
                        isolated,
                    );
                }
                if isolated {
                    assert_eq!(new_value, 1.75, "old text changed the new adjustment scope");
                } else {
                    assert!(
                        (new_value - -3.257).abs() < 0.00001,
                        "negative control must continue the prior numeric text in the new scope: {new_value}"
                    );
                }
                assert_eq!(old_value, -3.25);
            }
        }
    }
}
