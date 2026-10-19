//! A measured revision is attached to the photograph that actually reached the
//! canvas. The same reveal opacity carries its contour; no clock invents work.
use crate::{
    process_revision::{Revision, RevisionField},
    theme::{ACCENT, AMBER, INK, LINE, MUTED},
};
use eframe::egui::{self, Align2, Color32, FontId, Painter, Rect, Stroke, TextureHandle, Ui};

const COOL: Color32 = Color32::from_rgb(112, 177, 190);

struct Layer {
    texture: TextureHandle,
    revision: Revision,
}

#[derive(Default)]
pub(crate) struct RevisionView {
    current: Option<Layer>,
    previous: Option<Layer>,
}

impl RevisionView {
    pub(crate) fn sync(&mut self, ctx: &egui::Context, revision: Option<&Revision>) {
        if revision.is_none() {
            // A new baseline has no comparable spatial evidence. In particular,
            // an old domain must never be stretched across changed geometry.
            self.current = None;
            self.previous = None;
            return;
        }
        if self.current.as_ref().map(|layer| layer.revision.sequence)
            == revision.map(|revision| revision.sequence)
        {
            return;
        }
        self.previous = self.current.take().filter(|layer| {
            revision.is_some_and(|next| {
                next.extent == layer.revision.extent
                    && next.width == layer.revision.width
                    && next.height == layer.revision.height
            })
        });
        self.current = revision.map(|revision| Layer {
            texture: ctx.load_texture(
                format!("observed-revision-{}", revision.sequence),
                contour(revision),
                egui::TextureOptions::NEAREST,
            ),
            revision: revision.clone(),
        });
    }

    pub(crate) fn paint(&self, painter: &Painter, destination: Rect, alpha: f32) {
        let uv = Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0));
        if alpha < 1.0
            && let Some(previous) = &self.previous
        {
            painter.image(
                previous.texture.id(),
                destination,
                uv,
                Color32::from_white_alpha(((1.0 - alpha) * 255.0).round() as u8),
            );
        }
        if let Some(current) = &self.current {
            painter.image(
                current.texture.id(),
                destination,
                uv,
                Color32::from_white_alpha((alpha * 255.0).round() as u8),
            );
        }
    }

    pub(crate) fn footer(
        &self,
        ui: &mut Ui,
        rect: Rect,
        field: &RevisionField,
        frame_count: usize,
    ) {
        let p = ui.painter_at(rect);
        let label = self.current.as_ref().map_or_else(
            || "Coarse green · waiting for a comparable revision".to_owned(),
            |layer| {
                format!(
                    "{} → {} inputs · {:.0}% changed samples",
                    layer.revision.from,
                    layer.revision.to,
                    100.0 * layer.revision.changed_samples as f32
                        / layer.revision.total_samples.max(1) as f32
                )
            },
        );
        let chart = Rect::from_min_max(
            egui::pos2(
                rect.right() - (rect.width() * 0.22).min(94.0),
                rect.top() + 2.0,
            ),
            rect.right_bottom() - egui::vec2(0.0, 3.0),
        );
        let label_rect =
            Rect::from_min_max(rect.min, egui::pos2(chart.left() - 9.0, rect.bottom()));
        p.with_clip_rect(label_rect).text(
            label_rect.left_center(),
            Align2::LEFT_CENTER,
            label,
            FontId::proportional(8.0),
            MUTED,
        );
        p.line_segment(
            [chart.left_bottom(), chart.right_bottom()],
            Stroke::new(0.6_f32, LINE),
        );
        let history = field.history();
        let trace_hit = ui.interact(
            chart,
            ui.id().with("revision-history-trace"),
            egui::Sense::hover(),
        );
        let hovered = trace_hit.hover_pos().and_then(|point| {
            history.iter().min_by(|a, b| {
                let x = |sample: &crate::process_revision::RevisionSummary| {
                    chart.left()
                        + chart.width() * sample.to.min(frame_count) as f32
                            / frame_count.max(1) as f32
                };
                (x(a) - point.x).abs().total_cmp(&(x(b) - point.x).abs())
            })
        });
        if !history.is_empty() {
            for sample in history {
                let x = chart.left()
                    + chart.width() * sample.to.min(frame_count) as f32 / frame_count.max(1) as f32;
                let height = chart.height() * sample.changed_samples as f32
                    / sample.total_samples.max(1) as f32;
                p.line_segment(
                    [
                        egui::pos2(x, chart.bottom()),
                        egui::pos2(x, chart.bottom() - height),
                    ],
                    Stroke::new(
                        if hovered.is_some_and(|item| item.sequence == sample.sequence) {
                            2.0_f32
                        } else {
                            1.0_f32
                        },
                        if hovered.is_some_and(|item| item.sequence == sample.sequence)
                            || self
                                .current
                                .as_ref()
                                .is_some_and(|layer| layer.revision.sequence == sample.sequence)
                        {
                            ACCENT
                        } else {
                            COOL.gamma_multiply(0.7)
                        },
                    ),
                );
            }
        }
        if let Some(sample) = hovered {
            trace_hit.on_hover_text(format!(
                "BUILD HISTORY · {} → {} accepted inputs\nCapture {:03} → {:03}\n{:.0}% of sampled locations changed beyond encoding resolution.\nObserved brightness movement: {:.2} to {:.2} green DN.\nThis trace remains available as new work arrives; inspecting it leaves the live photograph running.",
                sample.from, sample.to, sample.from_frame + 1, sample.to_frame + 1,
                100.0 * sample.changed_samples as f32 / sample.total_samples.max(1) as f32,
                sample.range_dn[0], sample.range_dn[1]
            ));
        }
        let detail = self.current.as_ref().map_or_else(String::new, |layer| format!(
            "\nAccepted {}→{}; capture F{:03}→F{:03}. Sampled {}×{} in {}×{} working pixels. Resolvable DN movement [{:.2}, {:.2}].",
            layer.revision.from, layer.revision.to, layer.revision.from_frame + 1, layer.revision.to_frame + 1,
            layer.revision.width, layer.revision.height, layer.revision.extent[0], layer.revision.extent[1],
            layer.revision.range_dn[0], layer.revision.range_dn[1]));
        let recent = history.back().map_or_else(String::new, |sample| {
            format!(
                "\nLatest retained interval: {}→{} accepted, capture F{:03}→F{:03}; DN [{:.2}, {:.2}].",
                sample.from,
                sample.to,
                sample.from_frame + 1,
                sample.to_frame + 1,
                sample.range_dn[0],
                sample.range_dn[1]
            )
        });
        ui.interact(label_rect, ui.id().with("revision-readout"), egui::Sense::hover()).on_hover_text(format!(
            "Changes between observed coarse-green stack prefixes, in the aligned working domain. Warm contours mark increased DN; cool contours mark decreased DN. The percentage counts sampled locations with resolvable change. Only differences larger than both packets' encoding uncertainty are marked. Unmarked samples may contain smaller changes. This records activity, not sharpness, quality, or an exact frame contribution.{detail}{recent}"
        ));
    }
}

const DISPLAY_CELL: usize = 8;

fn contour(revision: &Revision) -> egui::ColorImage {
    // This raster refines the drawing only. Each measured sample retains its
    // exact cell; no interpolation adds a measured location or changes its sign.
    let width = revision.width * DISPLAY_CELL;
    let height = revision.height * DISPLAY_CELL;
    let mut pixels = vec![Color32::TRANSPARENT; width * height];
    let sign = |index: usize| {
        let value = revision.signed_dn[index];
        if value > 0.0 {
            1
        } else if value < 0.0 {
            -1
        } else {
            0
        }
    };
    for y in 0..revision.height {
        for x in 0..revision.width {
            let i = y * revision.width + x;
            if revision.signed_dn[i] == 0.0 {
                continue;
            }
            let left = x == 0 || sign(i - 1) != sign(i);
            let right = x + 1 == revision.width || sign(i + 1) != sign(i);
            let top = y == 0 || sign(i - revision.width) != sign(i);
            let bottom = y + 1 == revision.height || sign(i + revision.width) != sign(i);
            let color = if revision.signed_dn[i] > 0.0 {
                AMBER
            } else {
                COOL
            };
            let interior = Color32::from_rgba_unmultiplied(color.r(), color.g(), color.b(), 8);
            let outline = Color32::from_rgba_unmultiplied(color.r(), color.g(), color.b(), 110);
            for dy in 0..DISPLAY_CELL {
                for dx in 0..DISPLAY_CELL {
                    let boundary = (left && dx == 0)
                        || (right && dx + 1 == DISPLAY_CELL)
                        || (top && dy == 0)
                        || (bottom && dy + 1 == DISPLAY_CELL);
                    pixels[(y * DISPLAY_CELL + dy) * width + x * DISPLAY_CELL + dx] =
                        if boundary { outline } else { interior };
                }
            }
        }
    }
    egui::ColorImage::new([width, height], pixels)
}

pub(crate) fn toggle(ui: &mut Ui, rect: Rect, on: &mut bool) {
    let hit = ui.interact(
        rect,
        ui.id().with("revision-overlay-toggle"),
        egui::Sense::click(),
    );
    if hit.clicked() {
        *on = !*on;
    }
    let p = ui.painter_at(rect);
    p.line_segment(
        [rect.left_bottom(), rect.right_bottom()],
        Stroke::new(1.0_f32, if *on { ACCENT } else { LINE }),
    );
    p.text(
        rect.center(),
        Align2::CENTER_CENTER,
        if *on { "CHANGES ON" } else { "CHANGES OFF" },
        FontId::monospace(8.0),
        if hit.hovered() { INK } else { MUTED },
    );
    hit.on_hover_text("Show or hide measured coarse-green revisions on the live photograph. The saved TIFF is always shown without this overlay.");
}

#[cfg(test)]
mod tests {
    use super::*;

    fn revision(sequence: u64) -> Revision {
        Revision {
            sequence,
            from: 4,
            to: 7,
            from_frame: 5,
            to_frame: 9,
            width: 3,
            height: 3,
            extent: [900, 600],
            signed_dn: vec![0.0, 0.0, 0.0, 0.0, 8.0, -6.0, 0.0, 0.0, 0.0],
            changed_samples: 2,
            total_samples: 9,
            range_dn: [-6.0, 8.0],
        }
    }

    #[test]
    fn a_new_spatial_domain_never_inherits_old_contours() {
        let ctx = egui::Context::default();
        let mut view = RevisionView::default();
        view.sync(&ctx, Some(&revision(1)));
        let mut changed = revision(2);
        changed.extent = [600, 900];
        view.sync(&ctx, Some(&changed));
        assert!(view.current.is_some());
        assert!(view.previous.is_none());
        view.sync(&ctx, None);
        let output = ctx.run(egui::RawInput::default(), |ctx| {
            view.paint(
                &ctx.layer_painter(egui::LayerId::background()),
                Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(300.0, 200.0)),
                0.25,
            );
        });
        assert!(
            output.shapes.is_empty(),
            "a fresh baseline has no comparable contours even during reveal"
        );
    }

    #[test]
    fn unresolved_pixels_are_transparent_and_signed_boundaries_are_distinct() {
        let image = contour(&revision(1));
        assert_eq!(image.size, [24, 24]);
        assert_eq!(
            image.pixels.iter().filter(|pixel| pixel.a() > 0).count(),
            128
        );
        let pixel = |x, y| image.pixels[y * image.size[0] + x];
        for y in 0..24 {
            for x in 0..24 {
                if !(8..16).contains(&y) || x < 8 {
                    assert_eq!(pixel(x, y), Color32::TRANSPARENT);
                }
            }
        }
        assert_eq!(
            pixel(15, 12),
            Color32::from_rgba_unmultiplied(AMBER.r(), AMBER.g(), AMBER.b(), 110),
            "the positive side of a sign split has its own thin outline"
        );
        assert_eq!(
            pixel(16, 12),
            Color32::from_rgba_unmultiplied(COOL.r(), COOL.g(), COOL.b(), 110),
            "the adjacent negative side retains its distinct sign colour"
        );
        assert_eq!(
            pixel(12, 12),
            Color32::from_rgba_unmultiplied(AMBER.r(), AMBER.g(), AMBER.b(), 8)
        );
        assert_eq!(
            pixel(20, 12),
            Color32::from_rgba_unmultiplied(COOL.r(), COOL.g(), COOL.b(), 8)
        );
        assert_eq!(
            image.pixels.iter().filter(|pixel| pixel.a() == 110).count(),
            56
        );
    }

    #[test]
    fn same_sign_samples_form_one_outline_without_internal_grid_lines() {
        let mut measured = revision(1);
        measured.signed_dn[5] = 4.0;
        let image = contour(&measured);
        let pixel = |x, y| image.pixels[y * image.size[0] + x];
        for y in 9..15 {
            assert_eq!(pixel(15, y).a(), 8);
            assert_eq!(pixel(16, y).a(), 8);
        }
        for x in 8..24 {
            assert_eq!(pixel(x, 8).a(), 110);
            assert_eq!(pixel(x, 15).a(), 110);
        }
        assert_eq!(
            image.pixels.iter().filter(|pixel| pixel.a() == 110).count(),
            44
        );
        assert_eq!(
            image.pixels.iter().filter(|pixel| pixel.a() == 8).count(),
            84
        );

        measured.width = 64;
        measured.height = 48;
        measured.signed_dn = vec![0.0; 64 * 48];
        let empty = contour(&measured);
        assert_eq!(empty.size, [512, 384]);
        assert!(
            empty
                .pixels
                .iter()
                .all(|pixel| *pixel == Color32::TRANSPARENT)
        );
    }

    #[test]
    fn overlay_retains_only_two_real_generations_and_clears_for_non_preview() {
        let ctx = egui::Context::default();
        let mut view = RevisionView::default();
        view.sync(&ctx, Some(&revision(4)));
        let first = view.current.as_ref().unwrap().texture.id();
        view.sync(&ctx, Some(&revision(7)));
        assert_eq!(view.previous.as_ref().unwrap().texture.id(), first);
        let second = view.current.as_ref().unwrap().texture.id();
        view.sync(&ctx, Some(&revision(9)));
        assert_eq!(view.previous.as_ref().unwrap().texture.id(), second);
        view.sync(&ctx, None);
        let output = ctx.run(egui::RawInput::default(), |ctx| {
            let p = ctx.layer_painter(egui::LayerId::background());
            view.paint(
                &p,
                Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(300.0, 200.0)),
                1.0,
            );
        });
        assert!(
            output.shapes.is_empty(),
            "completed or unrelated image must carry no revision layer"
        );
    }
}
