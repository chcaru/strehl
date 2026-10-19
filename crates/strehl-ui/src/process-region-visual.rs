//! A photographic receipt: one region, its source footprints, and every scale
//! along the capture axis. Admission is evidence of a positive gate, not a
//! reconstruction weight or a probability of photographic correctness.
use super::*;

#[derive(Default)]
pub(super) struct HeatCache {
    key: Option<(u64, usize, Rect, f32)>,
    mesh: std::sync::Arc<egui::Mesh>,
    #[cfg(test)]
    builds: usize,
}

impl RegionProbe {
    #[allow(clippy::too_many_arguments)]
    pub(super) fn diagnostic_tooltip(
        &self,
        ctx: &egui::Context,
        width: f32,
        available_height: f32,
        region: Rect,
        active: usize,
        extent: [usize; 2],
        frames: usize,
    ) -> PopupPaint {
        let mut out = PopupPaint::new(ctx, width);
        out.label("THIS REGION / SOURCE SUPPORT", 11.0, ACCENT);
        out.label(
            format!(
                "{:.0} × {:.0} photograph px · Ctrl+wheel to resize",
                region.width() * extent[0] as f32,
                region.height() * extent[1] as f32
            ),
            9.0,
            MUTED,
        );
        let top = self
            .spatial_key
            .as_ref()
            .map(|key| key.sources.as_slice())
            .unwrap_or_default();
        if let Some(frame) = self.source_frame.filter(|frame| *frame < frames) {
            let count = self
                .evidence
                .get(&(active, frame))
                .map(|item| item.count)
                .unwrap_or_default();
            let detail = if count.observed == 0 {
                "no recorded samples here".into()
            } else {
                format!("{}/{} samples admitted", count.admitted, count.observed)
            };
            out.label(
                format!("Comparing {:03} · {detail}", frame + 1),
                10.0,
                capture_ink(frame),
            );
        }
        let analysis = self.analysis_extent.unwrap_or(extent);
        let grid_pixels = 1usize << active;
        let active_pixels = grid_pixels as f32 * extent[0] as f32 / analysis[0].max(1) as f32;
        let show_cards = !top.is_empty() && available_height > 230.0 && width > 220.0;
        if show_cards {
            out.label(
                if top
                    .first()
                    .is_some_and(|&(frame, _, _)| Some(frame) == self.source_frame)
                {
                    format!("Final crop · {grid_pixels}px grid → {active_pixels:.0}px photo · current + peers")
                } else {
                    format!("Final crop · {grid_pixels}px grid → {active_pixels:.0}px photo · leading sources")
                },
                10.0,
                MUTED,
            );
            let column = (out.width - 8.0 * (top.len() - 1) as f32) / top.len() as f32;
            let height = (column * 0.78).clamp(38.0, 100.0);
            let row = out.row(height + 36.0);
            for (slot, &(frame, _, _)) in top.iter().enumerate() {
                let left = row.left() + slot as f32 * (column + 8.0);
                let slot_rect = Rect::from_min_size(
                    egui::pos2(left, row.top() + 16.0),
                    egui::vec2(column, height),
                );
                let crop_size = region.size() * egui::vec2(extent[0] as f32, extent[1] as f32);
                let scale = (slot_rect.width() / crop_size.x).min(slot_rect.height() / crop_size.y);
                let card = Rect::from_center_size(slot_rect.center(), crop_size * scale);
                let color = capture_ink(frame);
                out.fitted(
                    egui::pos2(left, row.top()),
                    column,
                    format!(
                        "{:03}{}",
                        frame + 1,
                        if Some(frame) == self.source_frame {
                            " / current"
                        } else {
                            ""
                        }
                    ),
                    10.0,
                    color,
                );
                // Every card uses the SAME aligned final crop. Camera JPEGs are
                // deliberately not projected onto an uncertified sensor domain.
                if let Some(texture) = self.texture {
                    let mut mesh = egui::Mesh::with_texture(texture);
                    mesh.add_rect_with_uv(card, region, Color32::from_gray(115));
                    out.shapes.push(egui::Shape::mesh(mesh));
                }
                let mut marks = egui::Mesh::default();
                let positive = || {
                    self.spatial
                        .iter()
                        .filter(|point| point.sources & (1 << slot) != 0)
                };
                let stride = positive().count().div_ceil(240).max(1);
                for point in positive().step_by(stride) {
                    let at =
                        card.min + (point.glyph.center - region.min) / region.size() * card.size();
                    let dot = Rect::from_center_size(at, Vec2::splat(2.6)).intersect(card);
                    if dot.is_positive() {
                        marks.add_colored_rect(dot, color);
                    }
                }
                out.shapes.push(egui::Shape::mesh(marks));
                let count = self
                    .evidence
                    .get(&(active, frame))
                    .map(|item| item.count)
                    .unwrap_or_default();
                let label = count.fraction().map_or_else(
                    || "unrecorded".into(),
                    |fraction| {
                        format!(
                            "{:.0}% · {}/{}",
                            100.0 * fraction,
                            count.admitted,
                            count.observed
                        )
                    },
                );
                out.fitted(
                    egui::pos2(left, slot_rect.bottom() + 4.0),
                    column,
                    label,
                    9.0,
                    color,
                );
            }
        }
        if !show_cards && !top.is_empty() {
            let row = out.row(14.0);
            let column = row.width() / top.len() as f32;
            for (slot, &(frame, _, _)) in top.iter().enumerate() {
                out.fitted(
                    row.min + egui::vec2(slot as f32 * column, 0.0),
                    column - 3.0,
                    format!("{:03}", frame + 1),
                    10.0,
                    capture_ink(frame),
                );
            }
        }
        let known = self
            .evidence
            .range((active, 0)..=(active, usize::MAX))
            .filter(|(_, item)| item.count.observed > 0)
            .count();
        let passing = self
            .evidence
            .range((active, 0)..=(active, usize::MAX))
            .filter(|(_, item)| item.count.admitted > 0)
            .count();
        out.label(
            format!("{passing} captures with admitted samples · {known}/{frames} recorded"),
            10.0,
            theme_ink(),
        );
        out.label("PHOTOGRAPH PX ↓     CAPTURE ORDER →", 9.0, MUTED);
        let row_height = ((available_height - out.y - 102.0) / self.levels.len().max(1) as f32)
            .clamp(12.0, 22.0);
        let label_width = 40.0_f32.min(out.width * 0.22);
        let mut bounds = Rect::NOTHING;
        for &level in &self.levels {
            let row = out.row(row_height);
            let analysis = self.analysis_extent.unwrap_or(extent);
            let physical = (1usize << level) as f32 * extent[0] as f32 / analysis[0].max(1) as f32;
            out.fitted(
                row.min,
                label_width - 3.0,
                format!("{physical:.0}px"),
                9.0,
                level_color(level),
            );
            let plot = Rect::from_min_max(row.min + egui::vec2(label_width, 0.0), row.max);
            bounds = bounds.union(plot);
            if level == active {
                out.line(
                    [
                        row.left_bottom(),
                        row.left_bottom() + egui::vec2(label_width - 6.0, 0.0),
                    ],
                    1.0,
                    level_color(level),
                );
            }
        }
        if bounds.is_finite() {
            out.shapes
                .push(egui::Shape::Mesh(self.heatmap(bounds, row_height, frames)));
            if let Some(row) = self.levels.iter().position(|&level| level == active) {
                let active_row = Rect::from_min_size(
                    bounds.min + egui::vec2(0.0, row as f32 * (row_height + 4.0)),
                    egui::vec2(bounds.width(), row_height - 2.0),
                );
                out.shapes.push(egui::Shape::rect_stroke(
                    active_row,
                    0.0,
                    Stroke::new(0.7_f32, level_color(active).gamma_multiply(0.65)),
                    egui::StrokeKind::Inside,
                ));
            }
            for &(frame, _, _) in top {
                let x = egui::lerp(
                    bounds.left()..=bounds.right(),
                    (frame as f32 + 0.5) / frames.max(1) as f32,
                );
                out.line(
                    [egui::pos2(x, bounds.top()), egui::pos2(x, bounds.bottom())],
                    0.7,
                    capture_ink(frame),
                );
            }
            let axis = out.row(12.0);
            out.text(
                egui::pos2(bounds.left(), axis.top()),
                Align2::LEFT_TOP,
                "001",
                8.0,
                MUTED,
            );
            out.text(
                egui::pos2(bounds.right(), axis.top()),
                Align2::RIGHT_TOP,
                format!("{frames:03}"),
                8.0,
                MUTED,
            );
        }
        let narrow_scale = out.width < 270.0;
        if narrow_scale {
            out.label("Sampled sites passing", 9.0, MUTED);
        }
        let scale = out.row(16.0);
        out.text(
            scale.left_center(),
            Align2::LEFT_CENTER,
            if narrow_scale {
                "0"
            } else {
                "Sampled sites passing · 0"
            },
            9.0,
            MUTED,
        );
        let start = scale.right() - 92.0;
        for index in 0..5 {
            let rect = Rect::from_min_size(
                egui::pos2(start + index as f32 * 12.0, scale.top() + 3.0),
                egui::vec2(10.0, 8.0),
            );
            out.shapes.push(egui::Shape::rect_filled(
                rect,
                0.0,
                level_color(active).gamma_multiply(0.10 + 0.90 * index as f32 / 4.0),
            ));
        }
        out.text(
            scale.right_center(),
            Align2::RIGHT_CENTER,
            "100%",
            8.0,
            MUTED,
        );
        if let Some(fallback) = &self.fallback
            && fallback.packet.level == active
            && Some(fallback.meta.extent) == self.analysis_extent
        {
            if let Some(fraction) = fallback.count.fraction() {
                out.label(
                    format!(
                        "Fallback average · {:.0}% of sampled sites",
                        fraction * 100.0
                    ),
                    10.0,
                    ACCENT,
                );
                let row = out.row(4.0);
                out.line([row.left_center(), row.right_center()], 2.0, LINE);
                out.line(
                    [
                        row.left_center(),
                        egui::pos2(
                            egui::lerp(row.left()..=row.right(), fraction),
                            row.center().y,
                        ),
                    ],
                    2.0,
                    ACCENT,
                );
            } else {
                out.label("Fallback: no recorded samples in this region", 9.0, MUTED);
            }
        }
        if let Some(balance) = self.balance {
            out.label(
                format!("Observation balance · {balance}/1000 at pointer"),
                10.0,
                MUTED,
            );
            let row = out.row(6.0);
            out.line([row.left_center(), row.right_center()], 2.0, LINE);
            let x = egui::lerp(row.left()..=row.right(), f32::from(balance) / 1000.0);
            out.shapes.push(egui::Shape::circle_filled(
                egui::pos2(x, row.center().y),
                3.0,
                ACCENT,
            ));
        }
        out.label(
            "Sources can overlap. Gate support is not blend share. Gaps are unrecorded.",
            9.0,
            MUTED,
        );
        out
    }

    pub(super) fn heatmap(
        &self,
        bounds: Rect,
        row_height: f32,
        frames: usize,
    ) -> std::sync::Arc<egui::Mesh> {
        let key = (self.visual_revision, frames, bounds, row_height);
        let mut cache = self.visual_cache.borrow_mut();
        if cache.key != Some(key) {
            let mut mesh = egui::Mesh::default();
            for (row, &level) in self.levels.iter().enumerate() {
                let y = bounds.top() + row as f32 * (row_height + 4.0);
                for (&(_, frame), item) in self
                    .evidence
                    .range((level, 0)..=(level, frames.saturating_sub(1)))
                {
                    let Some(fraction) = item.count.fraction() else {
                        continue;
                    };
                    let cell = Rect::from_min_max(
                        egui::pos2(
                            egui::lerp(
                                bounds.left()..=bounds.right(),
                                frame as f32 / frames.max(1) as f32,
                            ),
                            y,
                        ),
                        egui::pos2(
                            egui::lerp(
                                bounds.left()..=bounds.right(),
                                (frame + 1) as f32 / frames.max(1) as f32,
                            ),
                            y + row_height - 2.0,
                        ),
                    );
                    // Zero is observed dark support. A missing packet has no
                    // cell; linear brightness encodes sampled gate incidence.
                    mesh.add_colored_rect(
                        cell,
                        level_color(level).gamma_multiply(0.10 + 0.90 * fraction),
                    );
                }
            }
            cache.mesh = std::sync::Arc::new(mesh);
            cache.key = Some(key);
            #[cfg(test)]
            {
                cache.builds += 1;
            }
        }
        cache.mesh.clone()
    }
}

fn theme_ink() -> Color32 {
    crate::theme::INK
}
