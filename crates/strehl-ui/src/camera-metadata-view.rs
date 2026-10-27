//! Native views of stored camera values. Coordinates and units stay uncalibrated.
use super::{SourceStamp, Summary, parse_frame};
use anyhow::{Context, Result, ensure};
use eframe::egui::{self, Color32, Pos2, Rect, Sense, Stroke, Vec2};
use serde_json::Value;
use std::path::Path;

pub(super) const MAX_FRAMES: usize = 4096;
const MAX_CELLS: usize = 4096;
const BLUE: Color32 = Color32::from_rgb(38, 99, 161);
const ORANGE: Color32 = Color32::from_rgb(190, 94, 42);
const NEUTRAL: Color32 = Color32::from_rgb(238, 240, 241);
const GRID: Color32 = Color32::from_rgb(205, 212, 220);

#[derive(Debug)]
pub(super) struct Cell {
    pub bits: u16,
    pub signed: i16,
    pub flags: [u8; 2],
}
#[derive(Debug)]
pub(super) struct Grid {
    pub width: usize,
    pub height: usize,
    pub cells: Vec<Cell>,
}
#[derive(Debug)]
pub(super) struct Curve {
    pub name: &'static str,
    pub samples: Vec<i16>,
}
#[derive(Debug)]
pub(super) struct Frame {
    pub summary: Summary,
    pub path: String,
    pub grid: Option<Grid>,
    pub values: [Option<f64>; 3],
    pub curves: Vec<Curve>,
    pub details: String,
}
#[derive(Debug)]
pub(super) struct BracketView {
    pub frames: Vec<Frame>,
    pub breaks: Vec<bool>,
}
impl BracketView {
    pub fn from_report(
        report: &Value,
        sources: &[(std::path::PathBuf, SourceStamp)],
    ) -> Result<Self> {
        ensure!(
            report["schema"] == "strehl-sony-focus-audit-v1",
            "Unsupported metadata report"
        );
        ensure!(
            !sources.is_empty() && sources.len() <= MAX_FRAMES,
            "Unsupported bracket size"
        );
        ensure!(
            report["records_included"] == true,
            "The metadata engine omitted AF records"
        );
        let frames = report["frames"]
            .as_array()
            .context("Missing metadata frames")?;
        ensure!(
            frames.len() == sources.len()
                && report["file_count"].as_u64() == Some(sources.len() as u64),
            "Report does not match the imported bracket"
        );
        let mut views = Vec::with_capacity(frames.len());
        for (index, (frame, (path, stamp))) in frames.iter().zip(sources).enumerate() {
            ensure!(
                frame["index"].as_u64() == Some(index as u64),
                "Metadata frame order changed"
            );
            views.push(Frame::parse(frame, path, stamp)?);
        }
        let mut breaks = vec![false; frames.len()];
        for item in report["comparison_breaks"]
            .as_array()
            .context("Missing metadata comparison breaks")?
        {
            let from = item["from_index"]
                .as_u64()
                .context("Invalid comparison break")? as usize;
            let to = item["to_index"]
                .as_u64()
                .context("Invalid comparison break")? as usize;
            ensure!(
                from.checked_add(1) == Some(to) && to < frames.len(),
                "Invalid comparison break indices"
            );
            breaks[to] = true;
        }
        Ok(Self {
            frames: views,
            breaks,
        })
    }
    pub fn frame(&self, index: usize) -> Option<&Frame> {
        self.frames.get(index)
    }
    fn trace(&self, mode: usize, cell: usize) -> Vec<Option<f64>> {
        self.frames
            .iter()
            .map(|f| {
                if mode < 3 {
                    f.values[mode]
                } else {
                    f.grid
                        .as_ref()
                        .and_then(|g| g.cells.get(cell))
                        .map(|c| f64::from(c.signed))
                }
            })
            .collect()
    }
}
impl Frame {
    fn parse(frame: &Value, path: &Path, stamp: &SourceStamp) -> Result<Self> {
        let summary = parse_frame(frame, path, stamp)?;
        let meta = &frame["metadata"];
        let mut values = [None; 3];
        let grid = if frame["status"] == "present" {
            values[0] = if meta["coarse_focus_position"].is_null() {
                None
            } else {
                Some(f64::from(u8::try_from(
                    meta["coarse_focus_position"]
                        .as_u64()
                        .context("Invalid focus position code")?,
                )?))
            };
            for (destination, index) in [(1, 0), (2, 1)] {
                let value = meta["scalars_raw"][index]
                    .as_u64()
                    .context("Missing AF scalar")?;
                ensure!(u32::try_from(value).is_ok(), "Invalid AF scalar");
                values[destination] = Some(value as f64);
            }
            let raw = &meta["grid"];
            let width = raw["width"].as_u64().context("Missing AF width")? as usize;
            let height = raw["height"].as_u64().context("Missing AF height")? as usize;
            let count = width.checked_mul(height).context("AF grid is too large")?;
            ensure!(
                width > 0 && height > 0 && count <= MAX_CELLS,
                "Unsupported AF grid size"
            );
            let records = raw["records"]
                .as_array()
                .context("Missing AF grid records")?;
            ensure!(
                records.len() == count && raw["record_count"].as_u64() == Some(count as u64),
                "AF grid count mismatch"
            );
            let mut cells = Vec::with_capacity(count);
            for record in records {
                let bits =
                    u16::try_from(record["value_bits"].as_u64().context("Invalid AF bits")?)?;
                let signed = i16::try_from(
                    record["signed_display"]
                        .as_i64()
                        .context("Invalid signed AF value")?,
                )?;
                ensure!(
                    signed == bits as i16,
                    "AF signed display disagrees with stored bits"
                );
                let flags: [u8; 2] = serde_json::from_value(record["flags"].clone())?;
                cells.push(Cell {
                    bits,
                    signed,
                    flags,
                });
            }
            Some(Grid {
                width,
                height,
                cells,
            })
        } else {
            None
        };
        let mut curves = Vec::new();
        if frame["optical"]["status"] == "present" {
            for (name, key, count) in [
                ("Shading", "shading", 16),
                ("Distortion", "distortion", 16),
                ("Color fringing", "chromatic_aberration", 32),
            ] {
                let table = &frame["optical"]["facts"][key]["table"];
                if table.is_null() {
                    continue;
                }
                let raw = table["samples"]
                    .as_array()
                    .context("Missing optical samples")?;
                ensure!(raw.len() == count, "Unexpected {name} sample count");
                let samples = raw
                    .iter()
                    .map(|v| -> Result<i16> {
                        Ok(i16::try_from(
                            v.as_i64().context("Invalid optical sample")?,
                        )?)
                    })
                    .collect::<Result<Vec<_>>>()?;
                curves.push(Curve { name, samples });
            }
        }
        Ok(Self {
            summary,
            path: path.display().to_string(),
            grid,
            values,
            curves,
            details: serde_json::to_string_pretty(frame)?,
        })
    }
}

#[derive(Default)]
pub(super) struct ViewState {
    mode: usize,
    trace_mode: usize,
    cell: usize,
}
impl ViewState {
    pub fn show(
        &mut self,
        ui: &mut egui::Ui,
        view: &BracketView,
        selected: usize,
    ) -> Option<usize> {
        let Some(frame) = view.frame(selected) else {
            ui.label("The selected capture is outside this metadata snapshot.");
            return None;
        };
        let mut select = None;
        ui.horizontal(|ui| {
            ui.heading("Camera metadata");
            ui.label(format!("Capture {} / {}", selected + 1, view.frames.len()));
        });
        ui.label(&frame.path);
        ui.horizontal_wrapped(|ui| {
            ui.strong(&frame.summary.camera);
            ui.label(&frame.summary.firmware);
            ui.label(&frame.summary.lens);
        });
        ui.separator();
        ui.heading("Focus through the bracket");
        ui.horizontal(|ui| {
            for (i, label) in ["Position code", "Scalar A", "Scalar B", "Selected AF cell"]
                .iter()
                .enumerate()
            {
                ui.selectable_value(&mut self.trace_mode, i, *label);
            }
        });
        let mut values = view.trace(self.trace_mode, self.cell);
        if self.trace_mode == 3 {
            let shape = frame.grid.as_ref().map(|g| (g.width, g.height));
            for (value, other) in values.iter_mut().zip(&view.frames) {
                if other.grid.as_ref().map(|g| (g.width, g.height)) != shape {
                    *value = None;
                }
            }
        }
        if let Some(index) = plot(ui, &values, &view.breaks, Some(selected), 120.0, true) {
            select = Some(index);
        }
        ui.small(
            "Capture order · raw camera units. Gaps mark unavailable or incompatible metadata.",
        );
        ui.separator();
        ui.heading("Stored AF grid");
        super::status(ui, "AF metadata", &frame.summary.focus);
        for (label, value) in &frame.summary.focus_rows {
            ui.small(format!("{label}: {value}"));
        }
        if let Some(grid) = &frame.grid {
            ui.horizontal(|ui| {
                for (i, label) in ["Signed view (i16)", "Flag 0", "Flag 1", "Flag 1: 0x20"]
                    .iter()
                    .enumerate()
                {
                    ui.selectable_value(&mut self.mode, i, *label);
                }
            });
            self.cell = self.cell.min(grid.cells.len() - 1);
            let width = ui
                .available_width()
                .min(260.0 * grid.width as f32 / grid.height as f32);
            let (rect, response) = ui.allocate_exact_size(
                Vec2::new(width, width * grid.height as f32 / grid.width as f32),
                Sense::click_and_drag(),
            );
            let cell_size = Vec2::new(
                rect.width() / grid.width as f32,
                rect.height() / grid.height as f32,
            );
            let painter = ui.painter_at(rect);
            for (index, cell) in grid.cells.iter().enumerate() {
                let position = rect.min
                    + Vec2::new(
                        (index % grid.width) as f32 * cell_size.x,
                        (index / grid.width) as f32 * cell_size.y,
                    );
                let cell_rect = Rect::from_min_size(position, cell_size);
                painter.rect_filled(cell_rect, 0.0, cell_color(cell, self.mode));
                if index == self.cell {
                    painter.rect_stroke(
                        cell_rect.shrink(0.5),
                        0.0,
                        Stroke::new(1.5_f32, Color32::BLACK),
                        egui::StrokeKind::Inside,
                    );
                }
            }
            let hovered = response
                .hover_pos()
                .and_then(|p| grid_hit(rect, p, grid.width, grid.height));
            if (response.clicked() || response.dragged())
                && let Some(index) = hovered
            {
                self.cell = index;
            }
            let inspected = hovered.unwrap_or(self.cell);
            let cell = &grid.cells[inspected];
            ui.monospace(format!("Record {inspected} · row {} / column {} · bits 0x{:04X} · signed {} · flags {:02X} {:02X}", inspected/grid.width, inspected%grid.width,cell.bits,cell.signed,cell.flags[0],cell.flags[1]));
            ui.small(format!("{} × {} · click a cell to follow it through the bracket. Signed colors use a fixed -32768 to 32767 scale.",grid.width,grid.height));
            ui.small("Two's-complement i16 is a display interpretation of stored bits; the camera's arithmetic is not established.");
            ui.small("Firmware record order. Mapping onto the photograph, physical units and measurement freshness are uncalibrated. Flag meanings are not established.");
        }
        ui.separator();
        ui.heading("Stored optical curves");
        super::status(ui, "Optical metadata", &frame.summary.optical);
        for curve in &frame.curves {
            ui.strong(format!("{} · {} samples", curve.name, curve.samples.len()));
            let values = curve
                .samples
                .iter()
                .map(|v| Some(f64::from(*v)))
                .collect::<Vec<_>>();
            plot(ui, &values, &vec![false; values.len()], None, 110.0, false);
            ui.small("Stored sample index → · raw signed value ↑");
        }
        for row in &frame.summary.optical_rows {
            ui.label(format!(
                "{}: RAW setting {}; MakerNote setting {}",
                row.label, row.raw_setting, row.maker_setting
            ));
            ui.small(&row.table);
        }
        ui.small("Settings and tables are separate facts. No correction is enabled; sample indices do not imply a calibrated radius or color channel.");
        ui.collapsing("Full capture details", |ui| {
            ui.monospace(&frame.details);
        });
        select
    }
}
fn grid_hit(rect: Rect, position: Pos2, width: usize, height: usize) -> Option<usize> {
    if !rect.contains(position) {
        return None;
    }
    let x = (((position.x - rect.left()) / rect.width()) * width as f32).floor() as usize;
    let y = (((position.y - rect.top()) / rect.height()) * height as f32).floor() as usize;
    (x < width && y < height).then_some(y * width + x)
}
fn mix(a: Color32, b: Color32, t: f32) -> Color32 {
    let channel = |a: u8, b: u8| {
        (f32::from(a) + (f32::from(b) - f32::from(a)) * t.clamp(0.0, 1.0)).round() as u8
    };
    Color32::from_rgb(
        channel(a.r(), b.r()),
        channel(a.g(), b.g()),
        channel(a.b(), b.b()),
    )
}
fn cell_color(cell: &Cell, mode: usize) -> Color32 {
    match mode {
        0 => mix(
            NEUTRAL,
            if cell.signed < 0 { BLUE } else { ORANGE },
            f32::from(cell.signed).abs() / 32768.0,
        ),
        1 | 2 => mix(NEUTRAL, BLUE, f32::from(cell.flags[mode - 1]) / 255.0),
        _ => {
            if cell.flags[1] & 0x20 != 0 {
                ORANGE
            } else {
                NEUTRAL
            }
        }
    }
}
fn plot(
    ui: &mut egui::Ui,
    values: &[Option<f64>],
    breaks: &[bool],
    selected: Option<usize>,
    height: f32,
    interactive: bool,
) -> Option<usize> {
    let (rect, response) = ui.allocate_exact_size(
        Vec2::new(ui.available_width().min(900.0), height),
        if interactive {
            Sense::click_and_drag()
        } else {
            Sense::hover()
        },
    );
    let graph = rect.shrink2(Vec2::new(34.0, 18.0));
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 4.0, Color32::from_rgb(247, 249, 251));
    let low = values.iter().flatten().copied().reduce(f64::min);
    let high = values.iter().flatten().copied().reduce(f64::max);
    let (Some(low), Some(high)) = (low, high) else {
        painter.text(
            rect.center(),
            egui::Align2::CENTER_CENTER,
            "No recorded values",
            egui::FontId::proportional(13.0),
            Color32::DARK_GRAY,
        );
        return None;
    };
    let span = (high - low).max(1.0);
    let position = |i: usize, v: f64| {
        Pos2::new(
            graph.left() + graph.width() * i as f32 / values.len().saturating_sub(1).max(1) as f32,
            graph.bottom() - graph.height() * ((v - low) / span) as f32,
        )
    };
    painter.line_segment(
        [graph.left_bottom(), graph.right_bottom()],
        Stroke::new(1.0_f32, GRID),
    );
    painter.text(
        rect.left_top() + Vec2::new(2.0, 2.0),
        egui::Align2::LEFT_TOP,
        format!("{high:.0}"),
        egui::FontId::monospace(10.0),
        Color32::DARK_GRAY,
    );
    painter.text(
        rect.left_bottom() - Vec2::new(-2.0, 2.0),
        egui::Align2::LEFT_BOTTOM,
        format!("{low:.0}"),
        egui::FontId::monospace(10.0),
        Color32::DARK_GRAY,
    );
    for (i, value) in values.iter().enumerate() {
        let Some(value) = value else {
            continue;
        };
        let point = position(i, *value);
        if i > 0
            && !breaks.get(i).copied().unwrap_or(true)
            && let Some(previous) = values[i - 1]
        {
            painter.line_segment(
                [position(i - 1, previous), point],
                Stroke::new(1.5_f32, BLUE),
            );
        }
        painter.circle_filled(
            point,
            if Some(i) == selected { 4.0 } else { 2.0 },
            if Some(i) == selected { ORANGE } else { BLUE },
        );
    }
    if let Some(index) = selected.filter(|i| *i < values.len()) {
        let x = position(index, low).x;
        painter.line_segment(
            [Pos2::new(x, graph.top()), Pos2::new(x, graph.bottom())],
            Stroke::new(1.0_f32, ORANGE),
        );
    }
    if let Some(pointer) = response.hover_pos() {
        let i = (((pointer.x - graph.left()) / graph.width()).clamp(0.0, 1.0)
            * values.len().saturating_sub(1) as f32)
            .round() as usize;
        response.clone().on_hover_text(format!(
            "{} {}: {}",
            if interactive { "Capture" } else { "Sample" },
            if interactive { i + 1 } else { i },
            values[i].map_or_else(|| "Not recorded".into(), |v| format!("{v:.0}"))
        ));
        if interactive && (response.clicked() || response.dragged()) {
            return Some(i);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn grid_hit_is_row_major_and_does_not_wrap_the_right_edge() {
        let rect = Rect::from_min_size(Pos2::ZERO, Vec2::new(330.0, 230.0));
        assert_eq!(grid_hit(rect, Pos2::new(15.0, 25.0), 33, 23), Some(67));
        assert_eq!(grid_hit(rect, Pos2::new(330.0, 20.0), 33, 23), None);
        assert_ne!(
            cell_color(
                &Cell {
                    bits: 0,
                    signed: 0,
                    flags: [0, 0]
                },
                3
            ),
            cell_color(
                &Cell {
                    bits: 0,
                    signed: 0,
                    flags: [0, 32]
                },
                3
            )
        );
    }
}
