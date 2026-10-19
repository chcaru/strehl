//! Admission at the shared image pin, in original capture order. Only retained
//! binary observations paint marks; a missing mask is never an observed zero.
use crate::{
    process_output_space::{OutputGeometry, detail_label},
    process_provenance::AdmissionArchive,
    process_space::Input,
    theme::{ACCENT, GREEN, INK, LINE, MUTED},
};
use eframe::egui::{self, Align2, FontId, Pos2, Rect, Sense, Stroke, Ui};
use std::ops::Range;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct FingerprintPick {
    pub frame: Option<usize>,
    pub level: usize,
}
#[derive(Default)]
pub(crate) struct FingerprintResponse {
    pub hovered: Option<FingerprintPick>,
    pub clicked: Option<FingerprintPick>,
}
#[derive(Clone, Copy, Default)]
struct Cell {
    observed: usize,
    admitted: usize,
}
#[derive(Clone, Copy)]
struct Layout {
    grid: Rect,
    rows: usize,
    columns: usize,
    captures: usize,
}
impl Layout {
    fn new(rect: Rect, rows: usize, captures: usize) -> Option<Self> {
        if rect.width() < 300.0 || rect.height() < 60.0 || rows == 0 || captures == 0 {
            return None;
        }
        let grid = Rect::from_min_max(
            // Reserve a separate unit-caption line below the title while
            // keeping the capture-axis labels clear of the bottom legend.
            rect.min + egui::vec2(48.0, 24.0),
            rect.max - egui::vec2(4.0, 21.0),
        );
        Some(Self {
            grid,
            rows,
            columns: captures.min((grid.width() / 3.0).floor().max(1.0) as usize),
            captures,
        })
    }
    fn range(self, column: usize) -> Range<usize> {
        (column * self.captures).div_ceil(self.columns)
            ..((column + 1) * self.captures).div_ceil(self.columns)
    }
    fn column(self, frame: usize) -> usize {
        frame * self.columns / self.captures
    }
    fn row(self, level: usize) -> Rect {
        let height = self.grid.height() / self.rows as f32;
        Rect::from_min_size(
            self.grid.min + egui::vec2(0.0, level as f32 * height),
            egui::vec2(self.grid.width(), height),
        )
    }
    fn cell(self, level: usize, column: usize) -> Rect {
        let row = self.row(level);
        let range = self.range(column);
        Rect::from_min_max(
            egui::pos2(
                self.grid.left() + self.grid.width() * range.start as f32 / self.captures as f32,
                row.top(),
            ),
            egui::pos2(
                self.grid.left() + self.grid.width() * range.end as f32 / self.captures as f32,
                row.bottom(),
            ),
        )
    }
    fn pick(self, point: Pos2) -> Option<(usize, usize)> {
        if !self.grid.contains(point) {
            return None;
        }
        let frame = (((point.x - self.grid.left()) / self.grid.width() * self.captures as f32)
            as usize)
            .min(self.captures - 1);
        let level = (((point.y - self.grid.top()) / self.grid.height() * self.rows as f32)
            as usize)
            .min(self.rows - 1);
        Some((level, self.column(frame)))
    }
}

fn rows(input: &Input<'_>, archive: &AdmissionArchive) -> usize {
    input
        .progress
        .bands
        .map_or(8, |bands| bands.saturating_add(1))
        .max(archive.levels().max().map_or(0, |level| level + 1))
        .clamp(1, 64)
}
fn row_name(level: usize, base: bool, geometry: Option<OutputGeometry>) -> String {
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
fn cells(layout: Layout, archive: &AdmissionArchive, pin: Pos2) -> Vec<Vec<Cell>> {
    let mut rows = vec![vec![Cell::default(); layout.columns]; layout.rows];
    // Iterate retained observations, never every possible frame×scale position.
    for (level, row) in rows.iter_mut().enumerate() {
        for frame in archive
            .frames(level)
            .filter(|&frame| frame < layout.captures)
        {
            if let Some(admitted) = archive.sample(level, frame, [pin.x, pin.y]) {
                let cell = &mut row[layout.column(frame)];
                cell.observed += 1;
                cell.admitted += usize::from(admitted);
            }
        }
    }
    rows
}
fn pick(layout: Layout, cells: &[Vec<Cell>], level: usize, column: usize) -> FingerprintPick {
    let range = layout.range(column);
    FingerprintPick {
        frame: (range.len() == 1 && cells[level][column].observed == 1).then_some(range.start),
        level,
    }
}
fn description(
    layout: Layout,
    cell: Cell,
    level: usize,
    column: usize,
    base: bool,
    geometry: Option<OutputGeometry>,
) -> String {
    let range = layout.range(column);
    let detail = if base {
        "broad tone".into()
    } else {
        detail_label(level, geometry)
    };
    let identity = if range.len() == 1 {
        format!("Capture {}", range.start + 1)
    } else {
        format!(
            "Captures {}–{} · grouped at this zoom",
            range.start + 1,
            range.end
        )
    };
    let observed = if cell.observed == 0 {
        "No mask observed here".into()
    } else if range.len() == 1 {
        if cell.admitted == 1 {
            "Admitted at the nearest sampled location".into()
        } else {
            "Observed: not admitted at the nearest sampled location".into()
        }
    } else {
        format!(
            "{} admitted / {} observed · {} captures in this group",
            cell.admitted,
            cell.observed,
            range.len()
        )
    };
    let action = if range.len() == 1 && cell.observed == 1 {
        "Click to inspect this capture and detail size."
    } else {
        "Click selects the detail size only."
    };
    format!(
        "{identity} · {detail}\n{observed}\n{action}\nThe mask records positive support at the shared pin's nearest telemetry sample. It carries no contribution magnitude. Blank is unobserved; diagonal marks indicate a partly observed group."
    )
}

pub(crate) fn show(
    ui: &mut Ui,
    rect: Rect,
    input: &Input<'_>,
    archive: &AdmissionArchive,
    pin: Pos2,
    selected_level: usize,
) -> FingerprintResponse {
    let mut result = FingerprintResponse::default();
    let Some(layout) = Layout::new(rect, rows(input, archive), input.frame_count) else {
        return result;
    };
    let cells = cells(layout, archive, pin);
    let selected_level = selected_level.min(layout.rows - 1);
    let p = ui.painter_at(rect);
    let cross = rect.min + egui::vec2(5.0, 7.0);
    p.circle_stroke(cross, 2.0, Stroke::new(0.7_f32, INK));
    p.line_segment(
        [cross - egui::vec2(4.0, 0.0), cross + egui::vec2(4.0, 0.0)],
        Stroke::new(0.5_f32, INK),
    );
    p.line_segment(
        [cross - egui::vec2(0.0, 4.0), cross + egui::vec2(0.0, 4.0)],
        Stroke::new(0.5_f32, INK),
    );
    p.text(
        rect.min + egui::vec2(14.0, 1.0),
        Align2::LEFT_TOP,
        "AT PIN / CAPTURE ADMISSION",
        FontId::proportional(9.0),
        ACCENT,
    );
    p.text(
        rect.right_top() - egui::vec2(4.0, -2.0),
        Align2::RIGHT_TOP,
        if layout.columns < layout.captures {
            "grouped · nearest samples"
        } else {
            "nearest samples"
        },
        FontId::proportional(7.0),
        MUTED,
    );
    p.text(
        egui::pos2(layout.grid.left() - 5.0, layout.grid.top() - 2.0),
        Align2::RIGHT_BOTTOM,
        if input.progress.output_geometry.is_some() {
            "photo px"
        } else {
            "grid px"
        },
        FontId::proportional(6.0),
        MUTED,
    );
    for (level, row) in cells.iter().enumerate() {
        let bounds = layout.row(level);
        if bounds.height() >= 7.0 {
            p.text(
                egui::pos2(layout.grid.left() - 5.0, bounds.center().y),
                Align2::RIGHT_CENTER,
                row_name(
                    level,
                    input.progress.bands == Some(level),
                    input.progress.output_geometry,
                ),
                FontId::proportional(6.0),
                if level == selected_level { INK } else { MUTED },
            );
        }
        p.line_segment(
            [bounds.left_bottom(), bounds.right_bottom()],
            Stroke::new(0.4_f32, LINE.gamma_multiply(0.35)),
        );
        for (column, &cell) in row.iter().enumerate().filter(|(_, cell)| cell.observed > 0) {
            let area = layout.cell(level, column);
            let mark = Rect::from_center_size(
                area.center(),
                egui::vec2(
                    (area.width() - 1.0).clamp(1.0, 9.0),
                    (area.height() - 1.5).max(0.5),
                ),
            );
            if cell.admitted == 0 {
                p.rect_stroke(
                    mark,
                    0.0,
                    Stroke::new(0.65_f32, GREEN.gamma_multiply(0.5)),
                    egui::StrokeKind::Inside,
                );
            } else {
                let fraction = cell.admitted as f32 / cell.observed as f32;
                p.rect_filled(mark, 0.0, GREEN.gamma_multiply(0.3 + 0.7 * fraction));
            }
            if cell.observed < layout.range(column).len() {
                p.line_segment(
                    [mark.left_bottom(), mark.right_top()],
                    Stroke::new(0.65_f32, MUTED),
                );
            }
        }
    }
    if input.selected < layout.captures {
        let selected = layout.cell(selected_level, layout.column(input.selected));
        p.rect_stroke(
            selected.shrink2(egui::vec2(0.0, 0.25)),
            0.0,
            Stroke::new(0.6_f32, INK.gamma_multiply(0.55)),
            egui::StrokeKind::Inside,
        );
    }
    let response = ui.interact(
        layout.grid,
        ui.id().with("capture-admission-fingerprint"),
        Sense::click(),
    );
    if let Some(point) = response.hover_pos()
        && let Some((level, column)) = layout.pick(point)
    {
        let selection = pick(layout, &cells, level, column);
        result.hovered = Some(selection);
        if response.clicked() {
            result.clicked = Some(selection);
        }
        let cell = layout.cell(level, column);
        p.line_segment(
            [
                egui::pos2(cell.center().x, layout.grid.top()),
                egui::pos2(cell.center().x, layout.grid.bottom()),
            ],
            Stroke::new(0.6_f32, INK.gamma_multiply(0.6)),
        );
        let scope = selection
            .frame
            .and_then(|frame| archive.metadata(level, frame))
            .map_or_else(String::new, |meta| {
                format!(
                    "\n{}×{} sampled grid within {}×{} aligned working pixels · observation {}.",
                    meta.samples[0], meta.samples[1], meta.extent[0], meta.extent[1], meta.sequence
                )
            });
        response.on_hover_text(format!(
            "{}{scope}",
            description(
                layout,
                cells[level][column],
                level,
                column,
                input.progress.bands == Some(level),
                input.progress.output_geometry,
            )
        ));
    }
    p.text(
        egui::pos2(rect.left(), layout.grid.bottom() + 2.0),
        Align2::LEFT_TOP,
        "capture",
        FontId::proportional(6.5),
        MUTED,
    );
    p.text(
        layout.grid.left_bottom() + egui::vec2(0.0, 2.0),
        Align2::LEFT_TOP,
        "001",
        FontId::monospace(6.5),
        MUTED,
    );
    if layout.captures > 1 {
        p.text(
            layout.grid.right_bottom() + egui::vec2(0.0, 2.0),
            Align2::RIGHT_TOP,
            format!("{:03}", layout.captures),
            FontId::monospace(6.5),
            MUTED,
        );
    }
    let y = rect.bottom() - 9.0;
    let legend = [(0.0, "admitted", true), (62.0, "not admitted", false)];
    for (x, text, filled) in legend {
        let icon = Rect::from_min_size(egui::pos2(rect.left() + x, y + 1.0), egui::vec2(5.0, 5.0));
        if filled {
            p.rect_filled(icon, 0.0, GREEN);
        } else {
            p.rect_stroke(
                icon,
                0.0,
                Stroke::new(0.7_f32, GREEN.gamma_multiply(0.5)),
                egui::StrokeKind::Inside,
            );
        }
        p.text(
            icon.right_top() + egui::vec2(4.0, -1.0),
            Align2::LEFT_TOP,
            text,
            FontId::proportional(6.5),
            MUTED,
        );
    }
    p.text(
        egui::pos2(rect.left() + 149.0, y),
        Align2::LEFT_TOP,
        "blank: unobserved",
        FontId::proportional(6.5),
        MUTED,
    );
    let count: usize = cells[selected_level].iter().map(|cell| cell.observed).sum();
    let status = if archive.dropped() > 0 {
        format!("{} masks omitted", archive.dropped())
    } else {
        format!("{count}/{} captures observed", layout.captures)
    };
    p.text(
        egui::pos2(rect.right() - 4.0, y),
        Align2::RIGHT_TOP,
        status,
        FontId::proportional(6.5),
        MUTED,
    );
    ui.interact(Rect::from_min_max(rect.min, rect.min + egui::vec2(rect.width(), 17.0)),
        ui.id().with("admission-scope"), Sense::hover()).on_hover_text(format!(
        "One aligned location, across the original captures and every detail size. {} spatial masks retained; {} sampling-domain changes. Green means positive support at the nearest transmitted sample. It does not measure a capture's share, sharpness, or quality. Newer observations refresh the same capture and detail size.", archive.len(), archive.resets()));
    result
}

#[cfg(test)]
#[path = "process-fingerprint-tests.rs"]
mod tests;
