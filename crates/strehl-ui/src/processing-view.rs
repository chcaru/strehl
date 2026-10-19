//! A stage-responsive account of the photograph being built. Diagrams show
//! reported frame identities or the declared method, never invented image data.

use crate::{
    pipeline::{AlignmentPhase, CoveragePlan, FrameObservation, PipelineProgress, Stage},
    theme::{ACCENT, BG, GREEN, INK, LINE, MUTED, RAISED},
};
use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, RichText, Sense, Stroke, Ui, Vec2};

#[derive(Default)]
pub struct DockResponse {
    pub selected: Option<usize>,
    pub compare_pair: Option<[usize; 2]>,
}

pub fn timeline(ui: &mut Ui, progress: &PipelineProgress) {
    let names = ["Read", "Place", "Blend", "Save"];
    ui.columns(4, |columns| {
        for (index, stage) in Stage::ALL.iter().enumerate() {
            let done = progress.stage == Stage::Complete
                || progress.stage > *stage && progress.stage <= Stage::Rendering;
            let current = progress.stage == *stage;
            let colour = if current {
                ACCENT
            } else if done {
                GREEN
            } else {
                MUTED
            };
            let width = columns[index].available_width();
            let (rect, response) =
                columns[index].allocate_exact_size(Vec2::new(width, 28.0), Sense::hover());
            columns[index].painter().line_segment(
                [rect.left_top(), rect.right_top()],
                Stroke::new(
                    if current { 2.0_f32 } else { 1.0_f32 },
                    if done || current { colour } else { LINE },
                ),
            );
            columns[index].painter().text(
                rect.left_center() + Vec2::new(0.0, 3.0),
                Align2::LEFT_CENTER,
                names[index],
                FontId::proportional(10.0),
                colour,
            );
            response.on_hover_text(format!(
                "{}\nStage widths do not estimate time.",
                stage.description()
            ));
        }
    });
}

/// The primary Live dock is deliberately readable at 288 logical pixels wide.
/// Returned indices let the photograph follow a click on the real frame route.
pub fn show_dock(
    ui: &mut Ui,
    progress: &PipelineProgress,
    pair_previews: [Option<(usize, &egui::TextureHandle)>; 2],
) -> DockResponse {
    let (title, purpose) = match progress.stage {
        Stage::Preparing => (
            "Read the capture",
            "Understand the bracket and its camera noise before combining frames.",
        ),
        Stage::Alignment => (
            "Find the overlap",
            "Match the same subject across changing focus, then place every frame on a shared canvas.",
        ),
        Stage::Merge => (
            "Bring depth into focus",
            "Give stronger detail more weight. Average what the stack cannot distinguish from noise.",
        ),
        Stage::Rendering => (
            "Make the photograph",
            "Turn the merged sensor samples into colour and save the finished TIFF.",
        ),
        Stage::Complete => (
            "The stack is ready",
            "Every accepted frame has contributed. The finished TIFF is saved.",
        ),
        Stage::Failed => (
            "Stack needs attention",
            "Processing stopped with an error. The log contains the engine's explanation.",
        ),
        Stage::Cancelled => (
            "Stack stopped",
            "The render was cancelled. You can inspect the bracket and start again.",
        ),
    };
    ui.label(RichText::new(title).size(23.0).color(INK))
        .on_hover_text(purpose);
    ui.add_space(9.0);
    timeline(ui, progress);
    ui.add_space(8.0);
    let response = if progress.stage == Stage::Alignment {
        alignment_story(ui, progress);
        pair_route(ui, progress, pair_previews)
    } else {
        let selected = frame_ledger(ui, progress);
        if progress.stage == Stage::Preparing {
            capture_story(ui, progress);
        } else if matches!(
            progress.stage,
            Stage::Merge | Stage::Rendering | Stage::Complete
        ) {
            ui.add_space(12.0);
            blend_story(ui, progress);
        }
        DockResponse {
            selected,
            ..Default::default()
        }
    };
    ui.add_space(12.0);
    coverage_story(ui, progress);
    ui.add_space(10.0);
    egui::CollapsingHeader::new("Advanced signals")
        .id_salt("live-advanced")
        .show(ui, |ui| {
            technical_notes(ui, progress);
        });
    response
}

/// Retained for callers that show the journal in a larger region.
#[cfg(test)]
pub fn show(ui: &mut Ui, progress: &PipelineProgress) -> Option<usize> {
    show_dock(ui, progress, [None, None]).selected
}

fn small(ui: &mut Ui, text: impl Into<String>) {
    ui.add(egui::Label::new(RichText::new(text.into()).size(10.0).color(MUTED)).wrap());
}

fn section_title(ui: &mut Ui, text: &str) {
    ui.label(RichText::new(text).size(13.0).color(INK));
}

fn capture_story(ui: &mut Ui, progress: &PipelineProgress) {
    ui.add_space(12.0);
    if let Some(camera) = progress.camera.as_deref() {
        small(ui, camera);
    }
    if let Some(total) = progress.frames_total {
        small(ui, format!("{total} RAW captures in file order"));
    }
}

fn counted_work(ui: &mut Ui, done: usize, total: usize, label: &str) {
    ui.horizontal(|ui| {
        ui.label(
            RichText::new(format!("{done} / {total}"))
                .monospace()
                .size(19.0)
                .color(INK),
        );
    });
    small(ui, label);
    if total > 0 && done <= total {
        let (rect, response) =
            ui.allocate_exact_size(Vec2::new(ui.available_width(), 3.0), Sense::hover());
        ui.painter().rect_filled(rect, 0.0, RAISED);
        ui.painter().rect_filled(
            Rect::from_min_size(
                rect.min,
                Vec2::new(rect.width() * done as f32 / total as f32, rect.height()),
            ),
            0.0,
            ACCENT,
        );
        response.on_hover_text(
            "Observed work in this step. It does not estimate the fraction of total render time.",
        );
    }
}

fn alignment_story(ui: &mut Ui, progress: &PipelineProgress) {
    use AlignmentPhase::*;
    ui.add_space(8.0);
    let (title, reason) = match progress.alignment_phase {
        Some(Planes) => (
            "Read each frame",
            "Read sensor samples for a comparison image from each RAW capture.",
        ),
        Some(Pyramids) => (
            "Look at several scales",
            "Broad forms and fine texture both help locate the same subject.",
        ),
        Some(Pairs) => (
            "Find shared features",
            "Direct comparisons connect frames even when their sharp regions change.",
        ),
        Some(CycleCheck) => (
            "Cross-check the matches",
            "Compare routes through the bracket to catch placements that disagree.",
        ),
        Some(Solve) => (
            "Place the whole bracket",
            "Solve the connected frames together instead of accumulating a chain of shifts.",
        ),
        Some(Validate) => (
            "Challenge the placements",
            "Check comparisons that were held out of the placement solve.",
        ),
        Some(Cache) => (
            "Reuse saved placements",
            "Read placements already recorded for this bracket.",
        ),
        Some(Complete) => (
            "The frames are placed",
            "The merge can now gather each frame on the same canvas.",
        ),
        Some(Bypassed) if progress.alignment_source.as_deref() == Some("off") => (
            "Use original positions",
            "Alignment is disabled. Camera or subject movement is not corrected.",
        ),
        Some(Bypassed) => (
            "No placements available",
            "No alignment placements are applied. Camera or subject movement is not corrected.",
        ),
        None => (
            "Prepare the comparison",
            "Waiting for the next observed alignment step.",
        ),
    };
    ui.label(RichText::new(title).size(13.0).color(INK))
        .on_hover_text(reason);
    match progress.alignment_phase {
        Some(Planes) => {
            if let Some((done, total)) = progress.alignment_planes {
                counted_work(ui, done, total, "comparison images read");
            }
        }
        Some(Pyramids) => {
            if let Some((done, total)) = progress.alignment_pyramids {
                counted_work(ui, done, total, "images processed at several scales");
            }
        }
        Some(Pairs) => {
            if let Some((done, accepted, total)) = progress.alignment_pairs {
                counted_work(ui, done, total, "direct frame comparisons finished");
                small(ui, format!("{accepted} comparisons accepted so far"));
            }
        }
        Some(Complete) => {
            if let (Some(placed), Some(refused)) = (progress.placed, progress.refused) {
                small(ui, format!("{placed} frames placed / {refused} refused"));
            }
        }
        _ => (),
    }
}

/// A comparison joins real frame indices. Curve height is only a layout device,
/// not a measurement of camera motion, focus depth, or fit accuracy.
fn pair_route(
    ui: &mut Ui,
    progress: &PipelineProgress,
    previews: [Option<(usize, &egui::TextureHandle)>; 2],
) -> DockResponse {
    let active = progress.alignment_current_pair;
    let pair = active.or(progress.alignment_latest_pair);
    let total = progress.frames_total.unwrap_or(0);
    let mut selected = None;
    let mut compare_pair = None;
    ui.add_space(8.0);
    if let Some(indices) = pair.filter(|indices| indices.iter().all(|index| *index < total)) {
        ui.label(
            RichText::new(format!(
                "{} {:03} ↔ {:03}",
                if active.is_some() {
                    "Comparing"
                } else {
                    "Last comparison"
                },
                indices[0] + 1,
                indices[1] + 1
            ))
            .size(11.0)
            .color(INK),
        );
        ui.columns(2, |columns| {
            for (slot,index) in indices.into_iter().enumerate() {
                let width=columns[slot].available_width();
                let (rect,response)=columns[slot].allocate_exact_size(Vec2::new(width,64.0),Sense::click());
                let painter=columns[slot].painter();
                painter.rect_filled(rect,0.0,BG);
                if let Some(texture)=previews.iter().flatten().find_map(|(identity,texture)| (*identity==index).then_some(*texture)) {
                    let size=texture.size_vec2();
                    let fit=(rect.width()/size.x).min(rect.height()/size.y);
                    painter.image(texture.id(),Rect::from_center_size(rect.center(),size*fit),Rect::from_min_max(Pos2::ZERO,egui::pos2(1.0,1.0)),Color32::WHITE);
                } else {
                    painter.text(rect.center(),Align2::CENTER_CENTER,format!("{:03}",index+1),FontId::monospace(23.0),MUTED);
                }
                painter.line_segment([rect.left_bottom(),rect.right_bottom()],Stroke::new(1.0_f32,if active.is_some(){ACCENT}else{LINE}));
                if response.on_hover_text(format!("Frame {} / source camera preview. Click to inspect this endpoint. No alignment vectors are drawn onto the JPEG.",index+1)).clicked() { selected=Some(index); }
            }
        });
        if ui
            .add(
                egui::Button::new(RichText::new("Compare pair").size(11.0).color(ACCENT))
                    .frame(false),
            )
            .clicked()
        {
            compare_pair = Some(indices);
        }
    }
    let (rect, response) = ui.allocate_exact_size(
        Vec2::new(ui.available_width(), 120.0),
        Sense::click_and_drag(),
    );
    let axis = Rect::from_min_max(
        rect.min + Vec2::new(8.0, 94.0),
        rect.max - Vec2::new(8.0, 21.0),
    );
    let y = axis.center().y;
    let position = |index: usize| {
        Pos2::new(
            axis.left() + axis.width() * index as f32 / total.saturating_sub(1).max(1) as f32,
            y,
        )
    };
    let painter = ui.painter();
    let edge_points = |indices: [usize; 2]| {
        if indices.iter().any(|index| *index >= total) {
            return None;
        }
        let a = position(indices[0]);
        let b = position(indices[1]);
        let height = 40.0 + ((a.x - b.x).abs() / axis.width().max(1.0)).sqrt() * 98.0;
        let bend = Pos2::new((a.x + b.x) * 0.5, y - height);
        let points: Vec<_> = (0..=20)
            .map(|step| {
                let t = step as f32 / 20.0;
                Pos2::new(
                    (1.0 - t).powi(2) * a.x + 2.0 * (1.0 - t) * t * bend.x + t * t * b.x,
                    (1.0 - t).powi(2) * a.y + 2.0 * (1.0 - t) * t * bend.y + t * t * b.y,
                )
            })
            .collect();
        Some(points)
    };
    let observed: Vec<_> = progress
        .alignment_observed_pairs
        .iter()
        .filter_map(|indices| edge_points(*indices).map(|points| (*indices, points)))
        .collect();
    let nearest = response
        .hover_pos()
        .filter(|point| point.y < y - 6.0)
        .and_then(|point| {
            observed
                .iter()
                .enumerate()
                .map(|(index, (_, points))| {
                    let distance = points
                        .windows(2)
                        .map(|line| {
                            let vector = line[1] - line[0];
                            let t = ((point - line[0]).dot(vector)
                                / vector.length_sq().max(f32::EPSILON))
                            .clamp(0.0, 1.0);
                            point.distance(line[0] + vector * t)
                        })
                        .fold(f32::INFINITY, f32::min);
                    (index, distance)
                })
                .min_by(|left, right| left.1.total_cmp(&right.1))
                .filter(|(_, distance)| *distance <= 5.0)
                .map(|(index, _)| index)
        });
    for (index, (_, points)) in observed.iter().enumerate() {
        painter.add(egui::Shape::line(
            points.clone(),
            Stroke::new(
                if nearest == Some(index) {
                    1.7_f32
                } else {
                    0.65_f32
                },
                if nearest == Some(index) {
                    INK
                } else {
                    LINE.gamma_multiply(0.8)
                },
            ),
        ));
    }
    if let Some(points) = progress.alignment_latest_pair.and_then(edge_points) {
        painter.add(egui::Shape::line(
            points,
            Stroke::new(1.0_f32, MUTED.gamma_multiply(0.75)),
        ));
    }
    if let Some(indices) = active {
        if let Some(points) = edge_points(indices) {
            painter.add(egui::Shape::line(points, Stroke::new(1.6_f32, ACCENT)));
        }
        for index in indices {
            if index < total {
                painter.circle_filled(position(index), 3.0, ACCENT);
            }
        }
    }
    painter.line_segment(
        [axis.left_center(), axis.right_center()],
        Stroke::new(1.0_f32, MUTED),
    );
    if total > 0 {
        for fraction in 0..=8 {
            let x = axis.left() + axis.width() * fraction as f32 / 8.0;
            painter.line_segment(
                [Pos2::new(x, y - 2.0), Pos2::new(x, y + 2.0)],
                Stroke::new(1.0_f32, MUTED),
            );
        }
        painter.text(
            Pos2::new(axis.left(), rect.bottom() - 9.0),
            Align2::LEFT_CENTER,
            "1",
            FontId::monospace(9.0),
            MUTED,
        );
        painter.text(
            Pos2::new(axis.right(), rect.bottom() - 9.0),
            Align2::RIGHT_CENTER,
            total.to_string(),
            FontId::monospace(9.0),
            MUTED,
        );
        painter.text(
            Pos2::new(axis.center().x, rect.bottom() - 9.0),
            Align2::CENTER_CENTER,
            "Capture order",
            FontId::proportional(9.0),
            MUTED,
        );
    }
    painter.text(
        rect.left_top() + Vec2::new(0.0, 3.0),
        Align2::LEFT_TOP,
        format!("Connections / {}", progress.alignment_observed_pairs.len()),
        FontId::proportional(9.0),
        MUTED,
    );
    if response.clicked() || response.dragged() {
        selected = response
            .interact_pointer_pos()
            .filter(|point| {
                rect.contains(*point)
                    && (point.y - y).abs() <= 7.0
                    && total > 0
                    && axis.width() > 0.0
            })
            .map(|point| {
                (((point.x - axis.left()) / axis.width()).clamp(0.0, 1.0)
                    * total.saturating_sub(1) as f32)
                    .round() as usize
            });
    }
    if let Some(index) = nearest {
        let indices = observed[index].0;
        if response.clicked() {
            compare_pair = Some(indices);
        }
        response
            .on_hover_cursor(egui::CursorIcon::PointingHand)
            .on_hover_text(format!(
                "Compare frames {} ↔ {}",
                indices[0] + 1,
                indices[1] + 1
            ));
    } else {
        response.on_hover_text("Only actual reported comparisons are drawn, at most 512 retained samples. Click a connection to compare its real endpoints; drag the capture-order axis to inspect a source. Curve height is layout, not measured movement, depth or accuracy.");
    }
    DockResponse {
        selected,
        compare_pair,
    }
}

fn blend_story(ui: &mut Ui, progress: &PipelineProgress) {
    let observed = !progress.band_averaged.is_empty();
    ui.horizontal(|ui| {
        section_title(ui, "Scale mix");
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            ui.label(
                RichText::new(if observed { "OBSERVED" } else { "PLAN" })
                    .monospace()
                    .size(8.5)
                    .color(MUTED),
            );
        });
    });
    let count = progress
        .bands
        .unwrap_or(progress.band_exponents.len())
        .min(24);
    if count == 0 {
        return;
    }
    let indices = [0, count / 2, count.saturating_sub(1), count];
    let names = [
        "Fine texture",
        "Middle scales",
        "Broad shapes",
        "Overall tone",
    ];
    let max_power = progress
        .band_exponents
        .iter()
        .copied()
        .fold(1.0_f32, f32::max);
    for (rung, (index, name)) in indices.into_iter().zip(names).enumerate() {
        let (rect, response) =
            ui.allocate_exact_size(Vec2::new(ui.available_width(), 38.0), Sense::hover());
        let node = Pos2::new(rect.left() + 10.0, rect.top() + 10.0);
        if rung < 3 {
            ui.painter().line_segment(
                [node, Pos2::new(node.x, rect.bottom() + 10.0)],
                Stroke::new(1.0_f32, LINE),
            );
        }
        let glyph = Rect::from_center_size(node, Vec2::splat(4.0 + rung as f32 * 3.0));
        ui.painter().rect_filled(glyph, 0.0, BG);
        ui.painter().rect_stroke(
            glyph,
            0.0,
            Stroke::new(1.0_f32, MUTED),
            egui::StrokeKind::Inside,
        );
        ui.painter().text(
            rect.left_top() + Vec2::new(30.0, 10.0),
            Align2::LEFT_CENTER,
            name,
            FontId::proportional(11.0),
            INK,
        );
        let fraction = progress.band_averaged.get(index).copied();
        let power = progress.band_exponents.get(index).copied();
        let mean = index == count
            && progress
                .base
                .as_deref()
                .is_some_and(|base| base.starts_with("plain mean"));
        let value = if let Some(fraction) = fraction {
            format!("{:.0}% avg", fraction * 100.0)
        } else if mean {
            "mean".into()
        } else if let Some(power) = power {
            format!("p{power:.0}")
        } else {
            "—".into()
        };
        ui.painter().text(
            rect.right_top() + Vec2::new(-2.0, 10.0),
            Align2::RIGHT_CENTER,
            value,
            FontId::monospace(10.0),
            if fraction.is_some() { GREEN } else { MUTED },
        );
        let track = Rect::from_min_max(
            rect.left_top() + Vec2::new(30.0, 24.0),
            rect.right_top() + Vec2::new(-2.0, 28.0),
        );
        ui.painter().rect_filled(track, 0.0, RAISED);
        if let Some(fraction) = fraction {
            ui.painter()
                .rect_filled(track, 0.0, ACCENT.gamma_multiply(0.3));
            ui.painter().rect_filled(
                Rect::from_min_size(
                    track.min,
                    Vec2::new(track.width() * fraction, track.height()),
                ),
                0.0,
                GREEN,
            );
        } else if let Some(power) = power {
            ui.painter().rect_filled(
                Rect::from_min_size(
                    track.min,
                    Vec2::new(track.width() * power / max_power, track.height()),
                ),
                0.0,
                ACCENT.gamma_multiply(0.6),
            );
        }
        let mut detail = format!(
            "{name}: engine scale {index}. Fractions count coefficients at this scale, not areas of the photograph."
        );
        if let Some(power) = power {
            detail.push_str(&format!("\nPlanned weight exponent: {power:.2}"));
        }
        if let Some(fraction) = fraction {
            detail.push_str(&format!(
                "\nObserved: {:.1}% averaged, {:.1}% weighted blend",
                fraction * 100.0,
                (1.0 - fraction) * 100.0
            ));
        }
        if let Some(floor) = progress.band_floor.get(index) {
            detail.push_str(&format!(
                "\nActual gate floor: {floor:.4} / sensor variance"
            ));
        }
        if let Some(gate) = progress.gate.as_deref() {
            detail.push_str(&format!("\nNoise gate: {gate}"));
        }
        response.on_hover_text(detail);
    }
    ui.horizontal(|ui| {
        if observed {
            key(ui, GREEN, "Average");
            key(ui, ACCENT.gamma_multiply(0.45), "Weighted");
        } else {
            small(ui, "Weight power / fine → broad");
        }
    });
}

fn coverage_story(ui: &mut Ui, progress: &PipelineProgress) {
    let Some(plan) = progress.coverage_plan else {
        return;
    };
    section_title(ui, "Shared view");
    let aspect = match plan {
        CoveragePlan::Cropped {
            grid_width,
            grid_height,
            ..
        } => grid_width as f32 / grid_height as f32,
        _ => progress
            .plane_size
            .map_or(1.5, |[width, height]| width as f32 / height as f32),
    };
    let grid_width = ui.available_width() * 0.71;
    let grid_height = grid_width / aspect;
    let (rect, response) = ui.allocate_exact_size(
        Vec2::new(ui.available_width(), grid_height + 16.0),
        Sense::hover(),
    );
    let grid = Rect::from_min_size(
        rect.min + Vec2::new(0.0, 8.0),
        Vec2::new(grid_width, grid_height),
    );
    ui.painter().rect_stroke(
        grid,
        0.0,
        Stroke::new(1.0_f32, LINE),
        egui::StrokeKind::Inside,
    );
    let (inside, value, note) = match plan {
        CoveragePlan::Whole => (Some(grid), "100%".to_string(), "width"),
        CoveragePlan::Scaled(scale) => (
            Some(Rect::from_center_size(grid.center(), grid.size() * scale)),
            format!("{:.1}%", scale * 100.0),
            "width\nrescaled",
        ),
        CoveragePlan::Cropped {
            width,
            height,
            x,
            y,
            grid_width,
            grid_height,
        } => {
            let inside = Rect::from_min_size(
                grid.min
                    + Vec2::new(
                        grid.width() * x as f32 / grid_width as f32,
                        grid.height() * y as f32 / grid_height as f32,
                    ),
                Vec2::new(
                    grid.width() * width as f32 / grid_width as f32,
                    grid.height() * height as f32 / grid_height as f32,
                ),
            );
            (
                Some(inside),
                format!("{:.1}%", 100.0 * width as f32 / grid_width as f32),
                "width\ncropped",
            )
        }
        CoveragePlan::Uncovered => (None, "—".into(), "uncovered\nedges"),
    };
    if let Some(inside) = inside {
        ui.painter()
            .rect_filled(inside.shrink(1.0), 0.0, ACCENT.gamma_multiply(0.12));
        ui.painter().rect_stroke(
            inside,
            0.0,
            Stroke::new(1.0_f32, ACCENT),
            egui::StrokeKind::Inside,
        );
        for corner in [
            inside.left_top(),
            inside.right_top(),
            inside.left_bottom(),
            inside.right_bottom(),
        ] {
            ui.painter().circle_filled(corner, 1.6, ACCENT);
        }
    }
    let x = grid.right() + 10.0;
    ui.painter().text(
        Pos2::new(x, grid.center().y - 10.0),
        Align2::LEFT_CENTER,
        value,
        FontId::monospace(13.0),
        INK,
    );
    ui.painter().text(
        Pos2::new(x, grid.center().y + 14.0),
        Align2::LEFT_CENTER,
        note,
        FontId::proportional(9.0),
        MUTED,
    );
    response.on_hover_text(format!("{}\nThe rectangle shows reported shared extent, not individual placement vectors. Scale mode preserves output dimensions; crop mode uses the actual reported origin and extent.",progress.coverage.as_deref().unwrap_or("Reported shared view.")));
}

fn technical_notes(ui: &mut Ui, progress: &PipelineProgress) {
    if let Some(event) = progress.events.back() {
        ui.label(RichText::new("Latest observation").size(10.0).color(INK));
        small(ui, format!("{} / {}", event.stage.title(), event.detail));
        ui.add_space(5.0);
    }
    for (name, value) in [
        ("Camera", progress.camera.as_deref()),
        ("Noise model", progress.noise_model.as_deref()),
        ("Noise gate", progress.gate.as_deref()),
        (
            "Weight exponents / broad to fine",
            progress.exponents.as_deref(),
        ),
        ("Buffer and thread plan", progress.memory.as_deref()),
        (
            "Actual per-band floor / sensor variance",
            progress.measured_floor.as_deref(),
        ),
        ("Alignment", progress.alignment.as_deref()),
    ] {
        if let Some(value) = value {
            ui.label(RichText::new(name).size(10.0).color(INK));
            small(ui, value);
            ui.add_space(5.0);
        }
    }
    if let Some(error) = progress.alignment_error.as_deref() {
        small(
            ui,
            format!(
                "Engine held-out residual: {error}. The log does not specify its pixel gauge; it is not a per-frame placement error."
            ),
        );
    }
}

fn key(ui: &mut Ui, colour: Color32, label: &str) {
    let (rect, _) = ui.allocate_exact_size(Vec2::new(5.0, 5.0), Sense::hover());
    ui.painter().rect_filled(rect, 0.0, colour);
    ui.label(RichText::new(label).size(9.0).color(MUTED));
}

fn frame_ledger(ui: &mut Ui, progress: &PipelineProgress) -> Option<usize> {
    ui.horizontal(|ui| {
        ui.label(RichText::new("Frames").size(9.0).color(MUTED).strong());
        let summary = match (progress.frames_processed, progress.frames_total) {
            (Some(done), Some(total)) => format!(
                "{done} / {total} processed  ·  {} admitted",
                progress.frames_accepted.unwrap_or(0)
            ),
            _ if progress.folded.is_some() => {
                let (admitted, total) = progress.folded.unwrap();
                format!("{admitted} / {total} folded · per-frame events unavailable")
            }
            (_, Some(total)) => format!("{total} source frames · waiting for frame events"),
            _ => "Waiting for the source inventory".into(),
        };
        small(ui, summary);
    });
    let width = ui.available_width();
    let (rect, response) = ui.allocate_exact_size(Vec2::new(width, 18.0), Sense::click_and_drag());
    ui.painter().rect_filled(rect, 0.0, BG);
    let Some(total) = progress.frames_total.filter(|total| *total > 0) else {
        ui.painter().line_segment(
            [rect.left_center(), rect.right_center()],
            Stroke::new(1.0_f32, LINE),
        );
        return None;
    };
    let at_pointer = |position: Pos2| {
        (rect.width() > 0.0 && rect.contains(position)).then(|| {
            (((f64::from(position.x) - f64::from(rect.left())) / f64::from(rect.width())
                * total as f64)
                .floor() as usize)
                .min(total - 1)
        })
    };
    let selected = (response.clicked() || response.dragged())
        .then(|| response.interact_pointer_pos().and_then(at_pointer))
        .flatten();
    // A bin is mixed if it contains both observed and unobserved identities.
    // Aggregate processed counts never paint unidentified frames as finished.
    let bins = total.min((width / 4.0).floor().max(1.0) as usize).min(360);
    let gap = if bins > 180 { 1.0 } else { 2.0 };
    let step = width / bins as f32;
    let mut hovered = None;
    for bin in 0..bins {
        let boundary = |index| total / bins * index + (total % bins * index) / bins;
        let start = boundary(bin);
        let end = boundary(bin + 1).max(start + 1);
        let mut processed = 0;
        let mut active = false;
        for (index, state) in progress.frame_observations.range(start..end) {
            match state {
                FrameObservation::Started => {
                    active |=
                        progress.stage == Stage::Merge && progress.processing_frame == Some(*index);
                }
                FrameObservation::Processed => processed += 1,
            }
        }
        let colour = if active {
            ACCENT
        } else if processed == end - start {
            GREEN.gamma_multiply(0.8)
        } else if processed > 0 {
            GREEN.gamma_multiply(0.45)
        } else {
            RAISED
        };
        let cell = Rect::from_min_size(
            rect.min + Vec2::new(bin as f32 * step, 3.0),
            Vec2::new((step - gap).max(1.0), 12.0),
        );
        ui.painter().rect_filled(cell, 0.0, colour);
        if response
            .hover_pos()
            .is_some_and(|position| cell.contains(position))
        {
            let target = response
                .hover_pos()
                .and_then(at_pointer)
                .map(|frame| frame + 1);
            hovered = Some(format!(
                "Frames {}–{}: {processed} observed processed{}\nClick or drag to inspect frame {}.\nProcessing is distinct from admission. The admitted count is reported separately.",
                start + 1,
                end,
                if active {
                    ", work observed in progress"
                } else {
                    ""
                },
                target.unwrap_or(start + 1),
            ));
        }
    }
    if let Some(position) = response
        .hover_pos()
        .filter(|position| rect.contains(*position))
    {
        ui.painter().line_segment(
            [
                Pos2::new(position.x, rect.top()),
                Pos2::new(position.x, rect.bottom()),
            ],
            Stroke::new(1.0_f32, INK),
        );
    }
    if let Some(text) = hovered {
        response.on_hover_text(text);
    }
    ui.horizontal(|ui| {
        key(ui, ACCENT, "Processing");
        key(ui, GREEN, "Processed");
        key(ui, RAISED, "Not observed");
        if let Some(index) = progress
            .processing_frame
            .filter(|_| progress.stage == Stage::Merge)
        {
            small(ui, format!("Reading + gathering frame {}", index + 1));
        }
    });
    selected
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn actual_pair_controls_bind_photos_to_indices_and_open_the_observed_comparison() {
        let context = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.ingest(
            "STREHL_UI_PROGRESS event=stage name=alignment total=259\n\
STREHL_UI_PROGRESS event=align-phase name=pairs frames=259 total=170\n\
STREHL_UI_PROGRESS event=align-pair i=1 j=2 completed=14 accepted=11 frames=259 total=170\n\
STREHL_UI_PROGRESS event=align-pair-start i=2 j=180 started=15 frames=259 total=170\n",
        );
        let real = context.load_texture(
            "real-endpoint",
            egui::ColorImage::new([16, 10], vec![Color32::RED; 160]),
            egui::TextureOptions::LINEAR,
        );
        let stale = context.load_texture(
            "stale-other-frame",
            egui::ColorImage::new([16, 10], vec![Color32::GREEN; 160]),
            egui::TextureOptions::LINEAR,
        );
        let draw = |time, events| {
            let mut response = DockResponse::default();
            let output = context.run(
                egui::RawInput {
                    screen_rect: Some(Rect::from_min_size(Pos2::ZERO, Vec2::new(288.0, 1100.0))),
                    time: Some(time),
                    events,
                    ..Default::default()
                },
                |context| {
                    egui::CentralPanel::default()
                        .frame(egui::Frame::NONE)
                        .show(context, |ui| {
                            response =
                                show_dock(ui, &progress, [Some((2, &real)), Some((999, &stale))]);
                        });
                },
            );
            (response, output)
        };
        let (initial, output) = draw(0.0, vec![]);
        assert!(
            initial.selected.is_none() && initial.compare_pair.is_none(),
            "drawing must not silently choose a workbench action"
        );
        let photo = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == real.id() => Some(Rect::from_points(
                    &mesh
                        .vertices
                        .iter()
                        .map(|vertex| vertex.pos)
                        .collect::<Vec<_>>(),
                )),
                _ => None,
            })
            .expect("fixture must draw the actual endpoint photo");
        assert!(!output.shapes.iter().any(|shape|matches!(&shape.shape,egui::Shape::Mesh(mesh) if mesh.texture_id==stale.id())),"a stale preview with the wrong source identity must never appear as the other endpoint");
        assert!(output.shapes.iter().any(|shape|matches!(&shape.shape,egui::Shape::Text(text) if text.galley.text()=="Connections / 1")),"14 completed comparisons with one emitted sample must not fabricate the missing 13 graph edges");
        let compare = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == "Compare pair" => {
                    Some(text.visual_bounding_rect().center())
                }
                _ => None,
            })
            .expect("the comparison action must actually be visible");
        let button = |pos, pressed| egui::Event::PointerButton {
            pos,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        };
        let _ = draw(
            0.1,
            vec![egui::Event::PointerMoved(compare), button(compare, true)],
        );
        let (response, _) = draw(0.2, vec![button(compare, false)]);
        assert_eq!(response.compare_pair, Some([2, 180]));
        assert_eq!(response.selected, None);
        let at = photo.center();
        let _ = draw(0.3, vec![egui::Event::PointerMoved(at), button(at, true)]);
        let (response, _) = draw(0.4, vec![button(at, false)]);
        assert_eq!(response.selected, Some(2));
        assert_eq!(response.compare_pair, None);
        let connection = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Path(path) if path.points.len() == 21 => Some(&path.points),
                _ => None,
            })
            .expect("the fixture must paint its actually observed comparison curve");
        let on_curve = connection[10];
        let _ = draw(
            0.5,
            vec![egui::Event::PointerMoved(on_curve), button(on_curve, true)],
        );
        let (response, _) = draw(0.6, vec![button(on_curve, false)]);
        assert_eq!(
            response.compare_pair,
            Some([1, 2]),
            "clicking a rendered historical connection must compare its exact real endpoints"
        );
        assert_eq!(
            response.selected, None,
            "a curve click must not become an arbitrary source-axis selection"
        );
        let empty = Pos2::new(270.0, connection[0].y - 80.0);
        let _ = draw(
            0.7,
            vec![egui::Event::PointerMoved(empty), button(empty, true)],
        );
        let (response, _) = draw(0.8, vec![button(empty, false)]);
        assert_eq!(
            response.compare_pair, None,
            "empty graph space cannot invent a pair"
        );
        assert_eq!(response.selected, None);
    }

    fn narrow_journal(progress: &PipelineProgress) -> egui::FullOutput {
        let context = egui::Context::default();
        context.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, Vec2::new(300.0, 1200.0))),
                ..Default::default()
            },
            |context| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(context, |ui| {
                        ui.set_width(288.0);
                        let _ = show_dock(ui, progress, [None, None]);
                    });
            },
        )
    }

    #[test]
    fn narrow_journal_names_actual_work_and_keeps_technical_topology_secondary() {
        let mut progress = PipelineProgress::default();
        progress.ingest(
            "STREHL_UI_PROGRESS event=stage name=alignment total=259\n\
STREHL_UI_PROGRESS event=align-phase name=pairs frames=259 total=170\n\
STREHL_UI_PROGRESS event=align-pair i=1 j=2 completed=14 accepted=11 frames=259 total=170\n\
STREHL_UI_PROGRESS event=align-pair-start i=2 j=180 started=15 frames=259 total=170\n",
        );
        progress.memory = Some("4 canonical chunks, 1 reusable frame worker".into());
        let output = narrow_journal(&progress);
        let texts: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) => Some(text.galley.text()),
                _ => None,
            })
            .collect();
        for required in [
            "Find the overlap",
            "Find shared features",
            "Comparing 003 ↔ 181",
            "14 / 170",
            "11 comparisons accepted so far",
        ] {
            assert!(
                texts.contains(&required),
                "missing actual-work explanation: {required}"
            );
        }
        assert!(
            !texts.contains(&"Buffer and thread plan"),
            "technical notes must start collapsed"
        );
        assert!(!texts.contains(&"Frequency blend"));
        assert!(!texts.contains(&"Memory & execution"));
        // Once the comparison ends, the same endpoints are history. A diagram
        // must not continue claiming that completed work is currently running.
        progress.ingest("STREHL_UI_PROGRESS event=align-pair i=2 j=180 completed=15 accepted=12 frames=259 total=170\n");
        let output = narrow_journal(&progress);
        assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text() == "Last comparison 003 ↔ 181"
        )));
        assert!(!output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text().starts_with("Comparing ")
        )));
    }

    #[test]
    fn narrow_blend_story_explains_scales_without_inventing_live_measurements() {
        let mut progress = PipelineProgress::default();
        progress.ingest(
            "STREHL_UI_PROGRESS event=stage name=merge total=259\n\
bands: 7 Laplacian levels + 1 base\n\
base band: plain mean across frames\n",
        );
        let pending = narrow_journal(&progress);
        assert!(pending.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text() == "PLAN"
        )));
        assert!(!pending.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text().ends_with("% avg")
        )));
        progress.ingest("averaged: 4.8% 0.0% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0%\n");
        let observed = narrow_journal(&progress);
        for name in [
            "Fine texture",
            "Middle scales",
            "Broad shapes",
            "Overall tone",
            "5% avg",
            "100% avg",
        ] {
            let shape = observed
                .shapes
                .iter()
                .find(|shape| {
                    matches!(&shape.shape,
                    egui::Shape::Text(text) if text.galley.text() == name)
                })
                .unwrap_or_else(|| panic!("missing readable scale result {name}"));
            assert!(
                shape
                    .clip_rect
                    .expand(1.0)
                    .contains_rect(shape.shape.visual_bounding_rect()),
                "scale result clipped at dock width: {name}"
            );
        }
        assert_eq!(
            progress.frames_processed, None,
            "final scale observations cannot invent frame counters"
        );
    }

    fn ledger_input(
        context: &egui::Context,
        progress: &PipelineProgress,
        time: f64,
        events: Vec<egui::Event>,
    ) -> (Option<usize>, egui::FullOutput) {
        let mut selected = None;
        let output = context.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, Vec2::new(600.0, 300.0))),
                time: Some(time),
                events,
                ..Default::default()
            },
            |context| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(context, |ui| {
                        ui.set_width(600.0);
                        selected = frame_ledger(ui, progress);
                    });
            },
        );
        (selected, output)
    }

    #[test]
    fn real_ledger_pointer_selects_exact_frames_inside_grouped_unknown_cells() {
        // 10,000 frames occupy only 150 visual cells. Two positions in the
        // same cell must still choose different full-resolution source indices.
        // No frame events exist: browsing must not fabricate any completion.
        let context = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.ingest("frames: 10000 from a large capture\n");
        let (_, initial) = ledger_input(&context, &progress, 0.0, vec![]);
        let cell = initial
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Rect(shape) if (shape.rect.height() - 18.0).abs() < 0.1 => {
                    Some(shape.rect)
                }
                _ => None,
            })
            .expect("the fixture must actually paint the frame cells");
        let y = cell.center().y;
        let button = |position: Pos2, pressed| egui::Event::PointerButton {
            pos: position,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        };
        let click = Pos2::new(150.15, y);
        let _ = ledger_input(
            &context,
            &progress,
            0.1,
            vec![egui::Event::PointerMoved(click), button(click, true)],
        );
        assert_eq!(
            ledger_input(&context, &progress, 0.2, vec![button(click, false)]).0,
            Some(2502)
        );

        let start = Pos2::new(100.0, y);
        let _ = ledger_input(
            &context,
            &progress,
            0.3,
            vec![egui::Event::PointerMoved(start), button(start, true)],
        );
        assert_eq!(
            ledger_input(
                &context,
                &progress,
                0.4,
                vec![egui::Event::PointerMoved(Pos2::new(450.0, y))]
            )
            .0,
            Some(7500),
            "fixture must cross the drag threshold and actually drag"
        );
        assert_eq!(
            ledger_input(
                &context,
                &progress,
                0.5,
                vec![egui::Event::PointerMoved(Pos2::new(150.45, y))]
            )
            .0,
            Some(2507),
            "same visual bin as the earlier click, different exact source"
        );
        let outside = Pos2::new(-20.0, y);
        assert_eq!(
            ledger_input(
                &context,
                &progress,
                0.6,
                vec![egui::Event::PointerMoved(outside)]
            )
            .0,
            None,
            "captured drag outside the ledger must not clamp to an unrelated frame"
        );
        assert_eq!(
            ledger_input(&context, &progress, 0.7, vec![button(outside, false)]).0,
            None
        );
        assert!(progress.frame_observations.is_empty());
        assert_eq!(progress.frames_processed, None);
        assert_eq!(progress.frames_accepted, None);
    }

    #[test]
    fn instruments_can_draw_unknown_live_and_recorded_states() {
        // Empty and interrupted states used to be tempting places to invent a
        // percentage. Render each without any fake measurements or timers.
        let context = egui::Context::default();
        for text in [
            "",
            "STREHL_UI_PROGRESS event=stage name=alignment total=259\n",
            "STREHL_UI_PROGRESS event=frame-started index=1 total=3\n",
            "bands: 7 Laplacian levels + 1 base\nper-band exp: 2 3 4 5 8 8 8 (coarsest -> finest)\naveraged: 98.7% 80.1% 41.7% 2.8% 0% 0% 0% 100%\n",
        ] {
            let mut progress = PipelineProgress::default();
            progress.ingest(text);
            let _ = context.run(egui::RawInput::default(), |context| {
                egui::CentralPanel::default().show(context, |ui| {
                    ui.set_width(780.0);
                    timeline(ui, &progress);
                    let _ = show(ui, &progress);
                });
            });
        }
    }

    #[test]
    fn emitted_frame_cells_distinguish_current_work_from_an_interrupted_start() {
        let context = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.ingest("STREHL_UI_PROGRESS event=frame-started index=0 total=3\n");
        // Simulate a dropped finish followed by a newer start. The old frame
        // remains known-started; it is not a second current decoder.
        progress.ingest("STREHL_UI_PROGRESS event=frame-started index=2 total=3\n");
        let draw = |progress: &PipelineProgress| {
            context.run(egui::RawInput::default(), |context| {
                egui::CentralPanel::default().show(context, |ui| {
                    ui.set_width(600.0);
                    let _ = frame_ledger(ui, progress);
                });
            })
        };
        let active_cells = |output: &egui::FullOutput| {
            output.shapes.iter().filter(|shape| matches!(&shape.shape,
                egui::Shape::Rect(rect) if rect.fill == ACCENT && (rect.rect.height() - 12.0).abs() < 0.1
            )).count()
        };
        assert_eq!(
            active_cells(&draw(&progress)),
            1,
            "only the newest observed frame is current"
        );
        progress.mark_cancelled();
        assert_eq!(
            active_cells(&draw(&progress)),
            0,
            "stopped work cannot appear live"
        );
        assert_eq!(
            progress.frame_observations.len(),
            2,
            "the stale observations must actually be present in this fixture"
        );
    }
}
