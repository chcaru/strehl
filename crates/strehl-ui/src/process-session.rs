//! Completed session presentation uses retained receipts and a source-only browser.
use super::*;
use crate::session_workspace::{SessionMode, SessionSummary, mode_label};
use crate::theme::{ACCENT, GREEN, INK, MUTED, PANEL};

impl ProcessSpace {
    pub(super) fn show_session(
        &mut self,
        ui: &mut Ui,
        scene: Rect,
        input: &Input<'_>,
        summary: &SessionSummary,
        response: &mut Response,
    ) {
        let layer = summary.layer(self.output_path.as_deref());
        let header = Rect::from_min_max(
            scene.min + egui::vec2(12.0, 9.0),
            egui::pos2(scene.right() - 164.0, scene.top() + 86.0),
        );
        ui.scope_builder(egui::UiBuilder::new().max_rect(header), |ui| {
            ui.label(
                egui::RichText::new(if summary.completed {
                    "SESSION SAVED"
                } else {
                    "SAVED SESSION"
                })
                .monospace()
                .size(11.0)
                .color(GREEN),
            );
            ui.label(
                egui::RichText::new(format!(
                    "{} · {} passes · {} captures",
                    mode_label(summary.mode),
                    summary.passes.len(),
                    summary.frames
                ))
                .size(16.0)
                .color(INK),
            );
            ui.label(
                egui::RichText::new(format!(
                    "{} photograph{} + linear masters{}",
                    summary.outputs.len(),
                    if summary.outputs.len() == 1 { "" } else { "s" },
                    if summary.completed {
                        " complete"
                    } else {
                        " · completion receipt unavailable"
                    }
                ))
                .size(11.0)
                .color(MUTED),
            );
        });
        let timeline_height = 162.0_f32;
        let body = Rect::from_min_max(
            scene.min + egui::vec2(12.0, 94.0),
            scene.max - egui::vec2(12.0, timeline_height + 12.0),
        );
        let side_width = (body.width() * 0.25).clamp(150.0, 220.0);
        let side = Rect::from_min_max(
            body.min,
            egui::pos2(body.left() + side_width, body.bottom()),
        );
        ui.scope_builder(egui::UiBuilder::new().max_rect(side), |ui| {
            egui::ScrollArea::vertical()
                .id_salt("session-saved-summary")
                .show(ui, |ui| {
                    ui.label(
                        egui::RichText::new("JOINT ALIGNMENT")
                            .monospace()
                            .size(10.0)
                            .color(ACCENT),
                    );
                    if let Some(geometry) = &summary.geometry {
                        ui.label(format!(
                            "{} / {} captures placed",
                            geometry.placed, summary.frames
                        ));
                        ui.label(format!("{} refused", geometry.refused));
                        ui.label(format!("{} measured pair fits", geometry.measured_edges));
                        ui.label(format!("{} independent graph cycles", geometry.cycle_rank));
                    } else {
                        ui.label(if summary.ordinary_delegate {
                            "Ordinary single-pass alignment"
                        } else {
                            "Joint alignment report unavailable"
                        });
                    }
                    ui.add_space(10.0);
                    ui.label(
                        egui::RichText::new("SAVED PASSES")
                            .monospace()
                            .size(10.0)
                            .color(ACCENT),
                    );
                    for (i, pass) in summary.passes.iter().enumerate() {
                        ui.label(
                            egui::RichText::new(format!(
                                "{}{}",
                                if summary.primary == Some(i) {
                                    "★ "
                                } else {
                                    ""
                                },
                                pass.name
                            ))
                            .color(if layer == Some(i) {
                                ACCENT
                            } else {
                                INK
                            }),
                        );
                        ui.label(
                            egui::RichText::new(match pass.placed {
                                Some(placed) => {
                                    format!("{} captures · {} placed", pass.range.len(), placed)
                                }
                                None => format!("{} captures", pass.range.len()),
                            })
                            .size(10.0)
                            .color(MUTED),
                        );
                        ui.add_space(5.0);
                    }
                    ui.add_space(7.0);
                    ui.label(
                        egui::RichText::new(if summary.primary.is_some() {
                            if summary.mode == SessionMode::Layers {
                                "★ Primary sets the common reference and initially displayed layer."
                            } else {
                                "★ Primary anchors framing, appearance and disagreement fallback."
                            }
                        } else {
                            "Automatic reference; no preferred fusion pass."
                        })
                        .size(10.0)
                        .color(MUTED),
                    );
                    if let Some(error) = &summary.report_error {
                        ui.add_space(8.0);
                        ui.label(
                            egui::RichText::new("Some saved report details are unavailable")
                                .color(ACCENT),
                        )
                        .on_hover_text(error);
                    }
                    ui.add_space(12.0);
                    ui.label(
                        egui::RichText::new(format!("CAMERA ORIGINAL {:03}", input.selected + 1))
                            .monospace()
                            .size(10.0)
                            .color(MUTED),
                    );
                    ui.label(
                        egui::RichText::new("Unregistered capture preview")
                            .size(9.0)
                            .color(MUTED),
                    );
                    if let Some(photo) = input
                        .inspection_photos
                        .iter()
                        .chain(input.photos)
                        .find(|photo| photo.index == input.selected)
                    {
                        let size = egui::vec2(
                            ui.available_width(),
                            ui.available_width() * photo.texture.size()[1] as f32
                                / photo.texture.size()[0].max(1) as f32,
                        );
                        ui.add(egui::Image::from_texture(&photo.texture).fit_to_exact_size(size));
                    }
                });
        });
        let photo = Rect::from_min_max(egui::pos2(side.right() + 16.0, body.top()), body.max);
        let title = if let Some(index) = layer {
            format!(
                "Layer {} of {} · {} · {} captures",
                index + 1,
                summary.outputs.len(),
                summary.passes[index].name,
                summary.passes[index].range.len()
            )
        } else {
            format!("Saved photograph · {} session captures", summary.frames)
        };
        ui.painter().with_clip_rect(photo).text(
            photo.min,
            egui::Align2::LEFT_TOP,
            title,
            egui::FontId::proportional(12.0),
            ACCENT,
        );
        let photograph = Rect::from_min_max(photo.min + egui::vec2(0.0, 24.0), photo.max);
        if input.output.is_some() {
            // The final image has a legitimate UV domain. Ordinary source-admission
            // observations from the last rendered layer do not describe this session.
            let mut progress = PipelineProgress::default();
            progress.stage = Stage::Complete;
            let saved = Input {
                progress: &progress,
                frame_count: 0,
                photos: &[],
                inspection_photos: &[],
                surfaces: &[],
                inspected_pair: None,
                ..*input
            };
            self.theater
                .show_with_ribbon(ui, photograph, &saved, response, None);
            self.theater.update_balance(ui.ctx(), None, None);
        } else {
            ui.painter().text(
                photograph.center(),
                egui::Align2::CENTER_CENTER,
                "Opening saved photograph…",
                egui::FontId::proportional(12.0),
                MUTED,
            );
        }
        let timeline = Rect::from_min_max(
            egui::pos2(body.left(), body.bottom() + 13.0),
            scene.max - egui::vec2(12.0, 5.0),
        );
        ui.scope_builder(egui::UiBuilder::new().max_rect(timeline), |ui| {
            ui.label(egui::RichText::new(if layer.is_some() {
                "ALL SESSION CAPTURES · other-pass thumbnails dimmed · admission overlays unavailable"
            } else { "ALL SESSION CAPTURES · camera previews · admission overlays unavailable" }).monospace().size(9.0).color(MUTED));
            let (strip, _) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 20.0), egui::Sense::hover());
            for (i, pass) in summary.passes.iter().enumerate() {
                let left = strip.left() + strip.width() * pass.range.start as f32 / summary.frames.max(1) as f32;
                let right = strip.left() + strip.width() * pass.range.end as f32 / summary.frames.max(1) as f32;
                let rect = Rect::from_min_max(egui::pos2(left, strip.top()), egui::pos2((right - 2.0).max(left + 1.0), strip.bottom()));
                ui.painter().rect_filled(rect, 3.0, PANEL);
                ui.painter().with_clip_rect(rect).text(rect.center(), egui::Align2::CENTER_CENTER,
                    format!("{}{} · {}–{}", if summary.primary == Some(i) { "★ " } else { "" }, pass.name, pass.range.start + 1, pass.range.end),
                    egui::FontId::proportional(10.0), if layer == Some(i) { ACCENT } else { MUTED });
                if ui.interact(rect, ui.id().with(("saved-session-pass", i)), egui::Sense::click()).clicked() {
                    response.selected = Some(pass.range.start + pass.range.len() / 2);
                }
            }
            self.session_contacts.clear();
            egui::ScrollArea::horizontal().id_salt("saved-session-captures").auto_shrink([false, false]).show_viewport(ui, |ui, viewport| {
                let stride = 112.0_f32;
                let (row, _) = ui.allocate_exact_size(egui::vec2(summary.frames as f32 * stride, 91.0), egui::Sense::hover());
                let first = (viewport.left() / stride).floor().max(0.0) as usize;
                let last = ((viewport.right() / stride).ceil() as usize).min(summary.frames).min(input.frame_count);
                for index in first..last {
                    self.session_contacts.push(index);
                    let rect = Rect::from_min_size(row.min + egui::vec2(index as f32 * stride, 0.0), egui::vec2(stride - 6.0, 72.0));
                    let belongs = layer.is_none_or(|i| summary.passes[i].range.contains(&index));
                    ui.painter().rect_filled(rect, 2.0, PANEL);
                    if let Some(photo) = input.photos.iter().find(|photo| photo.index == index) {
                        let size = photo.texture.size_vec2();
                        let scale = (rect.width() / size.x).min(rect.height() / size.y);
                        let image = Rect::from_center_size(rect.center(), size * scale);
                        ui.painter().image(photo.texture.id(), image, Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)), egui::Color32::WHITE);
                    }
                    if !belongs { ui.painter().rect_filled(rect, 2.0, egui::Color32::from_black_alpha(140)); }
                    if index == input.selected { ui.painter().rect_stroke(rect, 2.0, egui::Stroke::new(1.0_f32, ACCENT), egui::StrokeKind::Inside); }
                    ui.painter().text(rect.center_bottom() + egui::vec2(0.0, 3.0), egui::Align2::CENTER_TOP,
                        format!("{:03}{}", index + 1, if belongs { "" } else { " · other pass" }), egui::FontId::monospace(9.0), MUTED);
                    if ui.interact(rect, ui.id().with(("saved-session-capture", index)), egui::Sense::click()).clicked() { response.selected = Some(index); }
                }
            });
        });
        if let Some(index) = response.selected {
            self.inspect_frame(index);
        }
    }
}
