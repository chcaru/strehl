//! Persistent sampled contribution evidence in capture order. The separate
//! fallback strip has accepted-prefix coordinates, never source coordinates.
use crate::{
    pipeline::{DiagnosticKind, SampledMaskHistory, Stage, WorkState},
    process_output_space::{OutputGeometry, detail_label},
    process_space::Input,
    theme::{ACCENT, AMBER, BG, GREEN, INK, LINE, MUTED, PANEL},
    workbench::PhotoSlot,
};
use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, Ui};
use std::ops::Range;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct LedgerPick {
    /// Only an individually observed capture. Grouped or missing evidence
    /// selects the detail size without inventing a capture observation.
    pub frame: Option<usize>,
    pub level: usize,
}
#[derive(Default)]
pub(crate) struct LedgerResponse {
    pub hovered: Option<LedgerPick>,
    pub clicked: Option<LedgerPick>,
}
#[derive(Default)]
pub(crate) struct ProcessLedger {
    epoch: Option<u64>,
    photos: [Option<PhotoSlot>; 4],
}

pub(crate) fn contact_indices(count: usize) -> Vec<usize> {
    let shown = count.min(4);
    if shown < 2 {
        return (0..shown).collect();
    }
    (0..shown)
        .map(|slot| slot * (count - 1) / (shown - 1))
        .collect()
}

/// Match the same aperture guard as show, so prefetch names only painted slots.
pub(crate) fn visible_contact_indices(rect: Rect, count: usize) -> Vec<usize> {
    if count > 0 && Layout::new(rect, 1).is_some() {
        contact_indices(count)
    } else {
        Vec::new()
    }
}

#[derive(Clone, Copy)]
struct Layout {
    rect: Rect,
    grid: Rect,
    fallback: Rect,
    rows: usize,
}
impl Layout {
    fn new(rect: Rect, rows: usize) -> Option<Self> {
        (rect.width() >= 190.0 && rect.height() >= 160.0 && rows > 0).then(|| Self {
            rect,
            grid: Rect::from_min_max(
                // Contact numbers end above the unit-caption line. Keep the
                // original row heights while reserving room for both labels.
                rect.min + egui::vec2(44.0, 82.0),
                rect.max - egui::vec2(8.0, 34.0),
            ),
            fallback: Rect::from_min_max(
                egui::pos2(rect.left() + 44.0, rect.bottom() - 14.0),
                rect.max - egui::vec2(8.0, 8.0),
            ),
            rows,
        })
    }
    fn row(self, level: usize) -> Rect {
        let height = self.grid.height() / self.rows as f32;
        Rect::from_min_size(
            self.grid.min + egui::vec2(0.0, level as f32 * height),
            egui::vec2(self.grid.width(), height),
        )
    }
    fn photo(self, slot: usize, shown: usize) -> Rect {
        let cell = (self.rect.width() - 16.0) / shown.max(1) as f32;
        Rect::from_center_size(
            egui::pos2(
                self.rect.left() + 8.0 + cell * (slot as f32 + 0.5),
                self.rect.top() + 47.5,
            ),
            egui::vec2((cell - 6.0).min(43.0), 25.0),
        )
    }
    fn pick(self, point: Pos2, count: usize) -> Option<(usize, usize)> {
        if !self.grid.contains(point) || count == 0 {
            return None;
        }
        Some((
            (((point.x - self.grid.left()) / self.grid.width() * count as f32) as usize)
                .min(count - 1),
            (((point.y - self.grid.top()) / self.grid.height() * self.rows as f32) as usize)
                .min(self.rows - 1),
        ))
    }
}

struct Evidence {
    range: Range<usize>,
    observed: usize,
    on: u64,
    samples: u64,
}
fn history<'a>(
    input: &'a Input<'_>,
    kind: DiagnosticKind,
    level: usize,
) -> Option<&'a SampledMaskHistory> {
    input.progress.sampled_mask_history.iter().find(|history| {
        history.kind == kind && history.level == level && history.total == input.frame_count
    })
}
fn evidence(history: &SampledMaskHistory, frame: usize) -> Option<Evidence> {
    if frame >= history.total || history.bins.is_empty() {
        return None;
    }
    let index = frame * history.bins.len() / history.total;
    let bin = &history.bins[index];
    Some(Evidence {
        range: history.range(index),
        observed: bin.observations(),
        on: bin.on_samples,
        samples: bin.samples,
    })
}
fn grouped_evidence(history: &SampledMaskHistory, start: usize, end: usize) -> Evidence {
    let (on, samples, observed) =
        history.bins[start..end]
            .iter()
            .fold((0, 0, 0), |(on, samples, observed), bin| {
                (
                    on + bin.on_samples,
                    samples + bin.samples,
                    observed + bin.observations(),
                )
            });
    Evidence {
        range: history.range(start).start..history.range(end - 1).end,
        observed,
        on,
        samples,
    }
}
fn displayed_evidence(history: &SampledMaskHistory, rect: Rect, frame: usize) -> Option<Evidence> {
    if frame >= history.total || history.bins.is_empty() {
        return None;
    }
    let bins = history.bins.len();
    let columns = bins.min(rect.width().floor().max(1.0) as usize);
    let bin = frame * bins / history.total;
    let column = bin * columns / bins;
    Some(grouped_evidence(
        history,
        (column * bins).div_ceil(columns),
        ((column + 1) * bins).div_ceil(columns),
    ))
}
fn count_rows(input: &Input<'_>) -> usize {
    input
        .progress
        .bands
        .map_or(8, |bands| bands.saturating_add(1))
        .max(
            input
                .progress
                .sampled_mask_history
                .iter()
                .map(|history| history.level + 1)
                .max()
                .unwrap_or(0),
        )
        .clamp(1, 64)
}
fn scale_name(level: usize, base: bool, geometry: Option<OutputGeometry>) -> String {
    if base {
        "broad tone".into()
    } else {
        detail_label(level, geometry)
            .split("px ")
            .next()
            .unwrap_or_default()
            .to_owned()
    }
}
fn active(input: &Input<'_>, rows: usize) -> Option<(usize, Option<usize>)> {
    if input.progress.stage != Stage::Merge
        || input.progress.merge_step_state != Some(WorkState::Started)
    {
        return None;
    }
    let frame = input
        .progress
        .merge_step_frame
        .filter(|&frame| frame < input.frame_count)?;
    Some((
        frame,
        input
            .progress
            .merge_step_level
            .filter(|&level| level < rows),
    ))
}

impl ProcessLedger {
    pub(crate) fn transitioning(&self) -> bool {
        self.photos.iter().flatten().any(PhotoSlot::needs_repaint)
    }
    pub(crate) fn show(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
        selected_level: usize,
    ) -> LedgerResponse {
        if self.epoch != Some(input.epoch) {
            *self = Self {
                epoch: Some(input.epoch),
                ..Default::default()
            };
        }
        let mut result = LedgerResponse::default();
        let rows = count_rows(input);
        let Some(layout) = Layout::new(rect, rows).filter(|_| input.frame_count > 0) else {
            return result;
        };
        let selected_level = selected_level.min(rows - 1);
        let p = ui.painter_at(rect);
        p.rect_filled(rect, 0.0, PANEL);
        p.text(
            rect.min + egui::vec2(8.0, 4.0),
            Align2::LEFT_TOP,
            "CAPTURE CONTRIBUTIONS",
            FontId::proportional(10.5),
            INK,
        );
        let grouped = input.frame_count > layout.grid.width().floor() as usize;
        p.text(
            rect.min + egui::vec2(8.0, 21.0),
            Align2::LEFT_TOP,
            if grouped {
                "Sampled · grouped · hatching = missing"
            } else {
                "Sampled · blank unobserved"
            },
            FontId::proportional(7.0),
            MUTED,
        );
        if !grouped {
            p.text(
                egui::pos2(rect.right() - 64.0, rect.top() + 21.0),
                Align2::RIGHT_TOP,
                "0%",
                FontId::monospace(6.5),
                MUTED,
            );
            p.text(
                egui::pos2(rect.right() - 8.0, rect.top() + 21.0),
                Align2::RIGHT_TOP,
                "100%",
                FontId::monospace(6.5),
                MUTED,
            );
            for step in 0..8 {
                let mark = Rect::from_min_size(
                    egui::pos2(rect.right() - 60.0 + step as f32 * 3.5, rect.top() + 23.0),
                    egui::vec2(3.5, 3.0),
                );
                p.rect_filled(
                    mark,
                    0.0,
                    GREEN.gamma_multiply(0.22 + 0.78 * step as f32 / 7.0),
                );
            }
        }
        self.contacts(ui, layout, input, selected_level, &mut result);
        p.text(
            egui::pos2(layout.grid.left() - 5.0, layout.grid.top() - 2.0),
            Align2::RIGHT_BOTTOM,
            if input.progress.output_geometry.is_some() {
                "photo px"
            } else {
                "grid px"
            },
            FontId::proportional(6.5),
            MUTED,
        );
        for level in 0..rows {
            let row = layout.row(level);
            p.rect_filled(row, 0.0, BG);
            if let Some(history) = history(input, DiagnosticKind::GateSupport, level) {
                paint_history(
                    &p,
                    row.shrink2(egui::vec2(0.0, (row.height() * 0.1).min(1.0))),
                    history,
                    GREEN,
                );
            }
            if row.height() >= 7.0 {
                let name = scale_name(
                    level,
                    input.progress.bands == Some(level),
                    input.progress.output_geometry,
                );
                p.text(
                    egui::pos2(layout.grid.left() - 5.0, row.center().y),
                    Align2::RIGHT_CENTER,
                    name,
                    FontId::proportional(6.5),
                    if level == selected_level { INK } else { MUTED },
                );
            }
            if level == selected_level {
                p.line_segment(
                    [row.left_top(), row.right_top()],
                    Stroke::new(0.6_f32, INK.gamma_multiply(0.4)),
                );
            }
        }
        if input.selected < input.frame_count {
            let x = frame_x(layout.grid, input.selected, input.frame_count);
            p.line_segment(
                [
                    egui::pos2(x, layout.grid.top()),
                    egui::pos2(x, layout.grid.bottom()),
                ],
                Stroke::new(0.7_f32, INK.gamma_multiply(0.45)),
            );
        }
        if let Some((frame, level)) = active(input, rows) {
            let x = frame_x(layout.grid, frame, input.frame_count);
            if let Some(level) = level {
                let row = layout.row(level);
                let cell = Rect::from_center_size(
                    egui::pos2(x, row.center().y),
                    egui::vec2(
                        (layout.grid.width() / input.frame_count as f32).max(2.0),
                        row.height(),
                    ),
                );
                p.rect_stroke(
                    cell.intersect(row),
                    0.0,
                    Stroke::new(1.0_f32, ACCENT),
                    egui::StrokeKind::Inside,
                );
            } else {
                p.line_segment(
                    [
                        egui::pos2(x - 2.0, layout.grid.top() - 2.0),
                        egui::pos2(x + 2.0, layout.grid.top() - 2.0),
                    ],
                    Stroke::new(1.0_f32, ACCENT),
                );
            }
        }
        let response = ui.interact(
            layout.grid,
            ui.id().with("contribution-ledger-grid"),
            Sense::click(),
        );
        if let Some(point) = response.hover_pos()
            && let Some((frame, level)) = layout.pick(point, input.frame_count)
        {
            let observed = history(input, DiagnosticKind::GateSupport, level)
                .and_then(|history| evidence(history, frame));
            let displayed = history(input, DiagnosticKind::GateSupport, level)
                .and_then(|history| displayed_evidence(history, layout.grid, frame));
            let exact = observed
                .as_ref()
                .is_some_and(|item| item.range.len() == 1 && item.observed == 1);
            let pick = LedgerPick {
                frame: exact.then_some(frame),
                level,
            };
            result.hovered = Some(pick);
            if response.clicked() {
                result.clicked = Some(pick);
            }
            let row = layout.row(level);
            let x = frame_x(layout.grid, frame, input.frame_count);
            p.line_segment(
                [egui::pos2(x, row.top()), egui::pos2(x, row.bottom())],
                Stroke::new(1.0_f32, INK),
            );
            let detail = if input.progress.bands == Some(level) {
                "broad tone".into()
            } else {
                detail_label(level, input.progress.output_geometry)
            };
            let display_note = displayed
                .as_ref()
                .filter(|item| item.range.len() > 1)
                .map_or(String::new(), |item| {
                    format!("\nDisplayed column: {}", describe(Some(item), "captures"))
                });
            let action = if exact {
                "Click to inspect this observed capture and detail size."
            } else {
                "Click selects detail size only."
            };
            response.on_hover_text(format!("Capture {} · {detail}\n{}{display_note}\n{action}\nBlank cells have no observed mask. Hatching marks a partially observed group. This is nearest-sampled positive support, not weight magnitude or whole-photo coverage.", frame + 1, describe(observed.as_ref(), "captures")));
        }
        p.text(
            egui::pos2(rect.left() + 8.0, rect.bottom() - 30.0),
            Align2::LEFT_TOP,
            "Fallback / accepted prefix",
            FontId::proportional(7.5),
            AMBER,
        );
        p.text(
            egui::pos2(rect.right() - 8.0, rect.bottom() - 30.0),
            Align2::RIGHT_TOP,
            scale_name(
                selected_level,
                input.progress.bands == Some(selected_level),
                input.progress.output_geometry,
            ),
            FontId::monospace(7.5),
            MUTED,
        );
        p.rect_filled(layout.fallback, 0.0, BG);
        if let Some(history) = history(input, DiagnosticKind::Averaging, selected_level) {
            paint_history(&p, layout.fallback, history, AMBER);
        }
        let response = ui.interact(
            layout.fallback.expand2(egui::vec2(0.0, 2.0)),
            ui.id().with("contribution-ledger-fallback"),
            Sense::hover(),
        );
        if let Some(point) = response.hover_pos() {
            let prefix = (((point.x - layout.fallback.left()) / layout.fallback.width())
                .clamp(0.0, 0.999_999)
                * input.frame_count as f32) as usize;
            let item = history(input, DiagnosticKind::Averaging, selected_level)
                .and_then(|history| evidence(history, prefix));
            let displayed = history(input, DiagnosticKind::Averaging, selected_level)
                .and_then(|history| displayed_evidence(history, layout.fallback, prefix));
            let display_note = displayed
                .as_ref()
                .filter(|item| item.range.len() > 1)
                .map_or(String::new(), |item| {
                    format!(
                        "\nDisplayed column: {}",
                        describe(Some(item), "accepted prefixes")
                    )
                });
            let detail = if input.progress.bands == Some(selected_level) {
                "broad tone".into()
            } else {
                detail_label(selected_level, input.progress.output_geometry)
            };
            response.on_hover_text(format!("After {} accepted captures · {detail}\n{}{display_note}\nAccepted-prefix order differs from capture order when a frame is refused. The amber samples locate fallback, not a contributing source.", prefix + 1, describe(item.as_ref(), "accepted prefixes")));
        }
        result
    }
    fn contacts(
        &mut self,
        ui: &mut Ui,
        layout: Layout,
        input: &Input<'_>,
        selected_level: usize,
        response: &mut LedgerResponse,
    ) {
        let indices = contact_indices(input.frame_count);
        let now = ui.input(|state| state.time);
        let p = ui.painter_at(layout.rect);
        for (slot, &frame) in indices.iter().enumerate() {
            let image = layout.photo(slot, indices.len());
            let x = frame_x(layout.grid, frame, input.frame_count);
            let points = [
                image.center_bottom() + egui::vec2(0.0, 10.0),
                egui::pos2(x, layout.grid.top() - 2.0),
            ];
            p.line_segment(points, Stroke::new(0.6_f32, LINE));
            p.rect_filled(image, 0.0, BG);
            let incoming = input
                .photos
                .iter()
                .find(|photo| photo.epoch == input.epoch && photo.index == frame)
                .cloned();
            PhotoSlot::sync(&mut self.photos[slot], incoming, input.epoch);
            if let Some(photo) = &mut self.photos[slot]
                && photo.current().index == frame
            {
                if photo.advance(now) {
                    ui.ctx().request_repaint();
                }
                let extent = photo.current().aperture;
                let size = egui::vec2(extent[0] as f32, extent[1] as f32);
                let scale = (image.width() / size.x).min(image.height() / size.y);
                let fitted = Rect::from_center_size(image.center(), size * scale);
                photo.paint(
                    &p,
                    fitted,
                    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                );
            }
            p.text(
                image.center_bottom() + egui::vec2(0.0, 1.0),
                Align2::CENTER_TOP,
                format!("{:03}", frame + 1),
                FontId::monospace(6.5),
                if frame == input.selected { INK } else { MUTED },
            );
            let hit = ui.interact(
                image,
                ui.id().with(("contribution-contact", frame)),
                Sense::click(),
            );
            if hit.hovered() {
                response.hovered = Some(LedgerPick {
                    frame: Some(frame),
                    level: selected_level,
                });
            }
            if hit.clicked() {
                response.clicked = Some(LedgerPick {
                    frame: Some(frame),
                    level: selected_level,
                });
            }
            hit.on_hover_text(format!("Capture {} · original camera preview", frame + 1));
        }
    }
}

fn frame_x(rect: Rect, frame: usize, count: usize) -> f32 {
    rect.left() + rect.width() * (frame as f32 + 0.5) / count.max(1) as f32
}
fn describe(item: Option<&Evidence>, axis: &str) -> String {
    let Some(item) = item.filter(|item| item.samples > 0) else {
        return "No sampled mask observed".into();
    };
    let fraction = item.on as f64 * 100.0 / item.samples as f64;
    if item.range.len() == 1 {
        format!(
            "{fraction:.0}% of nearest samples ON · {}/{} samples",
            item.on, item.samples
        )
    } else {
        format!(
            "Grouped {axis} {}–{} · {}/{} observed\n{fraction:.0}% of observed nearest samples ON",
            item.range.start + 1,
            item.range.end,
            item.observed,
            item.range.len()
        )
    }
}
fn paint_history(p: &egui::Painter, rect: Rect, history: &SampledMaskHistory, color: Color32) {
    let bins = history.bins.len();
    let columns = bins.min(rect.width().floor().max(1.0) as usize);
    for column in 0..columns {
        let start = (column * bins).div_ceil(columns);
        let end = ((column + 1) * bins).div_ceil(columns);
        let item = grouped_evidence(history, start, end);
        if item.samples == 0 {
            continue;
        }
        let range = &item.range;
        let mark = Rect::from_min_max(
            egui::pos2(
                rect.left() + rect.width() * range.start as f32 / history.total as f32,
                rect.top(),
            ),
            egui::pos2(
                rect.left() + rect.width() * range.end as f32 / history.total as f32,
                rect.bottom(),
            ),
        );
        let intensity = 0.22 + 0.78 * item.on as f32 / item.samples as f32;
        let inset = if mark.width() >= 4.0 { 0.5 } else { 0.0 };
        p.rect_filled(
            mark.shrink2(egui::vec2(inset, 0.0)),
            0.0,
            color.gamma_multiply(intensity),
        );
        if item.observed < item.range.len() {
            p.line_segment(
                [mark.left_bottom(), mark.right_top()],
                Stroke::new(0.6_f32, MUTED),
            );
        }
    }
}

#[cfg(test)]
#[path = "process-ledger-tests.rs"]
mod tests;
