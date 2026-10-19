//! Read-only review of evidence emitted by this run. No inferred quality grade.
use crate::{
    pipeline::{CoveragePlan, PipelineProgress},
    theme::{ACCENT, AMBER, GREEN, INK, LINE, MUTED},
};
use eframe::egui::{self, Align2, FontId, Rect, RichText, Sense, Stroke, Vec2, pos2};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ReviewFocus {
    Captures,
    Coverage,
    Alignment,
    Blend(usize),
}

#[derive(Clone, Debug, PartialEq)]
struct CaptureCounts {
    placed: usize,
    refused: usize,
    total: usize,
}

fn capture_counts(progress: &PipelineProgress) -> Option<CaptureCounts> {
    let (placed, refused, total) = (progress.placed?, progress.refused?, progress.frames_total?);
    (total > 0 && placed.checked_add(refused)? == total).then_some(CaptureCounts {
        placed,
        refused,
        total,
    })
}

/// Normalized covered rectangle. Scaled coverage is centered, exactly as the
/// engine's global field-of-view scale; a crop keeps its measured origin.
fn coverage_rect(plan: CoveragePlan) -> Option<Rect> {
    match plan {
        CoveragePlan::Whole => Some(Rect::from_min_max(pos2(0.0, 0.0), pos2(1.0, 1.0))),
        CoveragePlan::Scaled(k) if k.is_finite() && k > 0.0 && k <= 1.0 => {
            Some(Rect::from_center_size(pos2(0.5, 0.5), Vec2::splat(k)))
        }
        CoveragePlan::Cropped {
            width,
            height,
            x,
            y,
            grid_width,
            grid_height,
        } if grid_width > 0
            && grid_height > 0
            && width > 0
            && height > 0
            && x.checked_add(width).is_some_and(|end| end <= grid_width)
            && y.checked_add(height).is_some_and(|end| end <= grid_height) =>
        {
            Some(Rect::from_min_max(
                pos2(x as f32 / grid_width as f32, y as f32 / grid_height as f32),
                pos2(
                    (x + width) as f32 / grid_width as f32,
                    (y + height) as f32 / grid_height as f32,
                ),
            ))
        }
        _ => None,
    }
}

pub(crate) fn show(ui: &mut egui::Ui, progress: &PipelineProgress) -> Option<ReviewFocus> {
    let mut action = None;
    ui.label(
        RichText::new("RUN EVIDENCE")
            .monospace()
            .size(9.0)
            .color(MUTED),
    );
    ui.add_space(8.0);

    heading(ui, "Capture placement");
    if let Some(counts) = capture_counts(progress) {
        let (r, response) =
            ui.allocate_exact_size(Vec2::new(ui.available_width(), 30.0), Sense::click());
        let split = r.left() + r.width() * counts.placed as f32 / counts.total as f32;
        ui.painter().rect_filled(r, 0.0, AMBER.gamma_multiply(0.25));
        ui.painter().rect_filled(
            Rect::from_min_max(r.min, pos2(split, r.bottom())),
            0.0,
            GREEN.gamma_multiply(0.28),
        );
        ui.painter().text(
            r.center(),
            Align2::CENTER_CENTER,
            format!("{} placed / {} captures", counts.placed, counts.total),
            FontId::monospace(11.0),
            INK,
        );
        if response
            .on_hover_text("Inspect capture placement and the measured direct-fit network")
            .clicked()
        {
            action = Some(ReviewFocus::Captures);
        }
        if counts.refused > 0 {
            ui.label(
                RichText::new(format!("{} capture(s) could not be placed", counts.refused))
                    .size(11.0)
                    .color(AMBER),
            );
            small(
                ui,
                "Inspect the refused captures against their neighbours before deciding whether to exclude or recapture them.",
            );
        }
    } else {
        small(ui, "Placement totals have not been reported.");
    }
    if let (Some(accepted), Some(processed)) = (progress.frames_accepted, progress.frames_processed)
    {
        ui.label(
            RichText::new(format!(
                "{accepted} accepted / {processed} processed by merge"
            ))
            .size(10.0)
            .color(MUTED),
        );
    }

    divider(ui);
    heading(ui, "Shared image area");
    if let Some(plan) = progress.coverage_plan {
        if let Some(inner) = coverage_rect(plan) {
            let (r, response) =
                ui.allocate_exact_size(Vec2::new(ui.available_width(), 92.0), Sense::click());
            let outer =
                Rect::from_center_size(r.center(), Vec2::new((r.width() - 12.0).min(130.0), 78.0));
            let paint = ui.painter();
            paint.rect_stroke(
                outer,
                0.0,
                Stroke::new(1.0_f32, LINE),
                egui::StrokeKind::Inside,
            );
            let mapped = Rect::from_min_max(
                outer.min + inner.min.to_vec2() * outer.size(),
                outer.min + inner.max.to_vec2() * outer.size(),
            );
            paint.rect_filled(mapped, 0.0, ACCENT.gamma_multiply(0.15));
            paint.rect_stroke(
                mapped,
                0.0,
                Stroke::new(1.0_f32, ACCENT),
                egui::StrokeKind::Inside,
            );
            paint.text(
                mapped.center(),
                Align2::CENTER_CENTER,
                format!("{:.1}% area", 100.0 * inner.width() * inner.height()),
                FontId::monospace(11.0),
                INK,
            );
            if response
                .on_hover_text("Inspect the image boundary and shared coverage")
                .clicked()
            {
                action = Some(ReviewFocus::Coverage);
            }
            match plan {
                CoveragePlan::Whole => {
                    small(ui, "Every placed capture covers the whole image grid.")
                }
                CoveragePlan::Scaled(k) => small(
                    ui,
                    &format!(
                        "Field of view ×{k:.4} · output dimensions retained. Compare Shared coverage crop if preserving the unscaled sampling matters."
                    ),
                ),
                CoveragePlan::Cropped {
                    width,
                    height,
                    x,
                    y,
                    ..
                } => small(
                    ui,
                    &format!("{width} × {height} plane pixels at ({x}, {y}) · unity-scale crop."),
                ),
                CoveragePlan::Uncovered => unreachable!(),
            }
        } else {
            ui.label(
                RichText::new("Fully shared coverage was not established")
                    .size(11.0)
                    .color(AMBER),
            );
            small(ui, "Inspect the image boundary for uncovered areas.");
        }
    } else {
        small(ui, "Coverage has not been reported.");
    }

    divider(ui);
    heading(ui, "Alignment evidence");
    if let Some(source) = &progress.alignment_source {
        let bypassed = matches!(source.as_str(), "off" | "refused");
        ui.label(
            RichText::new(format!("Placement source · {source}"))
                .monospace()
                .size(10.0)
                .color(if bypassed { AMBER } else { MUTED }),
        );
        if bypassed {
            small(
                ui,
                "No solved placement was applied. Inspect corresponding edges across captures.",
            );
        }
    }
    if let Some(value) = &progress.alignment_error {
        ui.label(RichText::new(value).monospace().size(10.0).color(INK));
        small(
            ui,
            "Held-out pair prediction; this is not a per-pixel sharpness score. Inspect fine edges in the photograph and its sources.",
        );
        if ui.small_button("Inspect alignment").clicked() {
            action = Some(ReviewFocus::Alignment);
        }
    } else {
        small(ui, "No held-out error was reported for this run.");
    }

    divider(ui);
    heading(ui, "Averaging by detail size");
    if progress.band_averaged.is_empty() {
        small(ui, "Per-band averaging totals arrive after the fold.");
    }
    for (level, &fraction) in progress.band_averaged.iter().enumerate() {
        if !fraction.is_finite() || !(0.0..=1.0).contains(&fraction) {
            continue;
        }
        let percent = 100.0 * fraction;
        let (r, response) =
            ui.allocate_exact_size(Vec2::new(ui.available_width(), 22.0), Sense::click());
        ui.painter().rect_filled(
            r.shrink2(Vec2::new(0.0, 3.0)),
            0.0,
            LINE.gamma_multiply(0.6),
        );
        let filled = Rect::from_min_size(
            r.min + Vec2::new(0.0, 3.0),
            Vec2::new(r.width() * percent / 100.0, r.height() - 6.0),
        );
        ui.painter()
            .rect_filled(filled, 0.0, ACCENT.gamma_multiply(0.3));
        ui.painter().text(
            r.left_center() + Vec2::new(5.0, 0.0),
            Align2::LEFT_CENTER,
            format!(
                "{} px grid",
                1_usize.checked_shl(level.min(30) as u32).unwrap_or(0)
            ),
            FontId::monospace(10.0),
            INK,
        );
        ui.painter().text(
            r.right_center() - Vec2::new(5.0, 0.0),
            Align2::RIGHT_CENTER,
            format!("{percent:.1}%"),
            FontId::monospace(10.0),
            INK,
        );
        if response.on_hover_text("Share of coefficients averaged below the noise gate at this band; not a share of final RGB pixels. Inspect texture, noise limit and accepted contributions together.").clicked() { action = Some(ReviewFocus::Blend(level)); }
    }
    if !progress.band_averaged.is_empty() {
        small(
            ui,
            "Averaged below the gate. Compare a saved variation at the same image position when changing the noise gate or selection ramp.",
        );
    }
    if let Some(model) = &progress.noise_model {
        divider(ui);
        heading(ui, "Calibration used");
        small(ui, model);
    }
    action
}

fn heading(ui: &mut egui::Ui, text: &str) {
    ui.label(RichText::new(text).size(11.0).color(INK));
}
fn small(ui: &mut egui::Ui, text: &str) {
    ui.label(RichText::new(text).size(10.0).color(MUTED));
}
fn divider(ui: &mut egui::Ui) {
    ui.add_space(8.0);
    ui.separator();
    ui.add_space(5.0);
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn review_counts_do_not_turn_partial_or_unknown_placement_into_success() {
        let mut p = PipelineProgress::default();
        p.frames_total = Some(9);
        p.placed = Some(7);
        p.refused = Some(2);
        assert_eq!(
            capture_counts(&p).unwrap(),
            CaptureCounts {
                placed: 7,
                refused: 2,
                total: 9
            }
        );
        p.refused = Some(0);
        assert!(capture_counts(&p).is_none());
        p.refused = None;
        assert!(capture_counts(&p).is_none());
        p.placed = Some(usize::MAX);
        p.refused = Some(2);
        assert!(capture_counts(&p).is_none());
    }
    #[test]
    fn coverage_diagram_preserves_off_center_crop_and_rejects_invalid_extent() {
        let r = coverage_rect(CoveragePlan::Cropped {
            width: 80,
            height: 40,
            x: 10,
            y: 5,
            grid_width: 100,
            grid_height: 80,
        })
        .unwrap();
        assert_eq!(r, Rect::from_min_max(pos2(0.1, 0.0625), pos2(0.9, 0.5625)));
        assert!((r.area() - 0.4).abs() < 1e-6);
        assert!(coverage_rect(CoveragePlan::Uncovered).is_none());
        assert!(coverage_rect(CoveragePlan::Scaled(f32::NAN)).is_none());
        assert!(
            coverage_rect(CoveragePlan::Cropped {
                width: 80,
                height: 40,
                x: 70,
                y: 5,
                grid_width: 100,
                grid_height: 80
            })
            .is_none()
        );
    }
}
