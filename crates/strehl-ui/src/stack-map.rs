//! A capture-order instrument. Camera slices, observed work and real comparison
//! endpoints share one axis; schematic merge/output plans never claim pixels.

use std::collections::BTreeMap;

use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, Ui, Vec2};

use crate::{
    pipeline::{AlignmentPhase, CoveragePlan, FrameObservation, PipelineProgress, Stage},
    theme::{ACCENT, BG, GREEN, INK, LINE, MUTED, RAISED},
};

pub const HEIGHT: f32 = 94.0;

#[derive(Default, Debug, PartialEq, Eq)]
pub struct Response {
    pub selected: Option<usize>,
    pub compare_pair: Option<[usize; 2]>,
}

/// Every supplied photograph is bound to its real source index. Sparse input is
/// allowed: missing slices remain empty instead of borrowing another identity.
pub fn show(
    ui: &mut Ui,
    progress: &PipelineProgress,
    frame_count: usize,
    selected: usize,
    displayed: Option<usize>,
    previews: &[(usize, &egui::TextureHandle)],
    visible_range: Option<[usize; 2]>,
) -> Response {
    let (rect, interaction) = ui.allocate_exact_size(
        Vec2::new(ui.available_width(), HEIGHT),
        Sense::click_and_drag(),
    );
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 0.0, BG);
    let axis = Rect::from_min_max(
        rect.min + egui::vec2(12.0, 60.0),
        rect.max - egui::vec2(12.0, 13.0),
    );
    if frame_count == 0 || axis.width() <= 0.0 {
        text(
            &painter,
            rect.left_center(),
            Align2::LEFT_CENTER,
            "No capture",
            MUTED,
        );
        return Response::default();
    }
    let x = |index| frame_x(axis, frame_count, index);
    let top = rect.top();
    text(
        &painter,
        rect.left_top() + egui::vec2(12.0, 1.0),
        Align2::LEFT_TOP,
        &format!("STACK / {frame_count:03}"),
        INK,
    );
    text(
        &painter,
        rect.right_top() - egui::vec2(12.0, -1.0),
        Align2::RIGHT_TOP,
        &summary(progress),
        ACCENT,
    );

    let photos: BTreeMap<_, _> = previews
        .iter()
        .filter(|(index, _)| *index < frame_count)
        .map(|(index, texture)| (*index, *texture))
        .collect();
    let cell = axis.width() / frame_count as f32;
    painter.rect_filled(axis, 0.0, RAISED.gamma_multiply(0.55));
    for (&index, texture) in &photos {
        let photo = Rect::from_min_max(
            egui::pos2(axis.left() + cell * index as f32, axis.top()),
            egui::pos2(axis.left() + cell * (index + 1) as f32, axis.bottom()),
        );
        let aspect = texture.size_vec2().x / texture.size_vec2().y.max(1.0);
        let uv_width = (photo.width() / photo.height() / aspect).min(1.0);
        let uv_height = (photo.height() * aspect / photo.width().max(0.001)).min(1.0);
        painter.image(
            texture.id(),
            photo.shrink2(egui::vec2(cell.min(1.0) * 0.2, 0.0)),
            Rect::from_center_size(egui::pos2(0.5, 0.5), egui::vec2(uv_width, uv_height)),
            Color32::from_white_alpha(175),
        );
    }
    let mut photo_cards = Vec::new();
    let mut last_card = f32::NEG_INFINITY;
    for (&index, texture) in &photos {
        let margin = 17.0_f32.min(axis.width() * 0.5);
        let centre = x(index).clamp(axis.left() + margin, axis.right() - margin);
        if centre - last_card >= 42.0 {
            let card = Rect::from_center_size(
                egui::pos2(centre, axis.center().y),
                egui::vec2(34.0, axis.height()),
            );
            photo_card(&painter, card, index, texture);
            photo_cards.push((index, card));
            last_card = centre;
        }
    }

    // A single tick means this identity was actually present in the observed
    // stream. Aggregate jumps never colour an inferred capture-order prefix.
    for &index in &progress.alignment_plane_observations {
        if index < frame_count {
            painter.line_segment(
                [
                    egui::pos2(x(index), axis.top() - 5.0),
                    egui::pos2(x(index), axis.top() - 2.0),
                ],
                Stroke::new(1.0_f32, MUTED),
            );
        }
    }
    for &index in &progress.alignment_pyramid_observations {
        if index < frame_count {
            painter.circle_filled(egui::pos2(x(index), axis.top() - 9.0), 1.2, MUTED);
        }
    }
    for (&index, observation) in &progress.frame_observations {
        if index < frame_count {
            painter.line_segment(
                [
                    egui::pos2(x(index), axis.bottom() - 3.0),
                    egui::pos2(x(index), axis.bottom()),
                ],
                Stroke::new(
                    2.0_f32,
                    if *observation == FrameObservation::Processed {
                        GREEN
                    } else {
                        LINE
                    },
                ),
            );
        }
    }

    let mut curves = Vec::new();
    match progress.stage {
        Stage::Preparing => capture_lanes(&painter, rect, progress, frame_count),
        Stage::Alignment
            if matches!(
                progress.alignment_phase,
                Some(AlignmentPhase::Planes | AlignmentPhase::Pyramids)
            ) =>
        {
            capture_lanes(&painter, rect, progress, frame_count);
        }
        Stage::Alignment => {
            for &pair in &progress.alignment_observed_pairs {
                if pair.iter().all(|index| *index < frame_count) {
                    curves.push((pair, edge(axis, pair, frame_count)));
                }
            }
            for (_, points) in &curves {
                painter.add(egui::Shape::line(
                    points.clone(),
                    Stroke::new(0.65_f32, LINE),
                ));
            }
            if let Some(pair) = progress
                .alignment_current_pair
                .filter(|pair| pair.iter().all(|index| *index < frame_count))
            {
                painter.add(egui::Shape::line(
                    edge(axis, pair, frame_count),
                    Stroke::new(1.5_f32, ACCENT),
                ));
                for index in pair {
                    painter.circle_filled(egui::pos2(x(index), axis.top() - 2.0), 2.5, ACCENT);
                }
            }
        }
        Stage::Merge => scale_lanes(&painter, rect, progress),
        Stage::Rendering | Stage::Complete => output_plane(&painter, rect, progress, &photos),
        Stage::Failed | Stage::Cancelled => (),
    }
    if progress.stage == Stage::Merge
        && let Some(index) = progress
            .processing_frame
            .filter(|index| *index < frame_count)
    {
        painter.line_segment(
            [
                egui::pos2(x(index), axis.bottom()),
                egui::pos2(x(index), axis.top() - 1.0),
            ],
            Stroke::new(1.6_f32, ACCENT),
        );
        painter.circle_filled(egui::pos2(x(index), axis.top() - 1.0), 2.5, ACCENT);
    }
    let context_pair = if progress.stage == Stage::Alignment {
        progress
            .alignment_current_pair
            .or(progress.alignment_latest_pair)
    } else {
        None
    };
    let context_indices: Vec<_> = context_pair.map(|pair| pair.to_vec()).unwrap_or_else(|| {
        progress
            .processing_frame
            .filter(|index| *index < frame_count)
            .into_iter()
            .collect()
    });
    let mut centres: Vec<_> = context_indices
        .iter()
        .map(|index| {
            let margin = 25.0_f32.min(axis.width() * 0.5);
            x(*index).clamp(axis.left() + margin, axis.right() - margin)
        })
        .collect();
    if centres.len() == 2 && (centres[1] - centres[0]).abs() < 54.0 {
        let margin = 52.0_f32.min(axis.width() * 0.5);
        let centre =
            ((centres[0] + centres[1]) * 0.5).clamp(axis.left() + margin, axis.right() - margin);
        centres[0] = centre - 27.0;
        centres[1] = centre + 27.0;
    }
    for (&index, centre) in context_indices.iter().zip(centres) {
        if let Some(texture) = photos.get(&index) {
            let card = Rect::from_center_size(
                egui::pos2(
                    if progress.stage == Stage::Merge {
                        rect.left() + 40.0
                    } else {
                        centre
                    },
                    top + if progress.stage == Stage::Merge {
                        41.0
                    } else {
                        37.0
                    },
                ),
                egui::vec2(48.0, 28.0),
            );
            if progress.stage == Stage::Merge {
                painter.add(egui::Shape::line(
                    vec![
                        card.center_bottom(),
                        egui::pos2(card.center().x, top + 57.0),
                        egui::pos2(x(index), top + 57.0),
                        egui::pos2(x(index), axis.bottom()),
                    ],
                    Stroke::new(1.0_f32, ACCENT),
                ));
            } else {
                painter.line_segment(
                    [card.center_bottom(), egui::pos2(x(index), axis.bottom())],
                    Stroke::new(1.0_f32, ACCENT),
                );
            }
            photo_card(&painter, card, index, texture);
            photo_cards.push((index, card));
        }
    }
    if let Some([first, last]) =
        visible_range.filter(|range| range[0] <= range[1] && range[1] < frame_count)
    {
        let left = axis.left() + cell * first as f32;
        let right = axis.left() + cell * (last + 1) as f32;
        let y = axis.top() - 2.0;
        painter.add(egui::Shape::line(
            vec![
                egui::pos2(left, y - 3.0),
                egui::pos2(left, y),
                egui::pos2(right, y),
                egui::pos2(right, y - 3.0),
            ],
            Stroke::new(1.0_f32, INK),
        ));
    }
    if selected < frame_count {
        let at = egui::pos2(x(selected), axis.bottom() - 1.0);
        painter.add(egui::Shape::convex_polygon(
            vec![at, at + egui::vec2(-3.0, -4.0), at + egui::vec2(3.0, -4.0)],
            INK,
            Stroke::NONE,
        ));
    }
    if let Some(index) = displayed.filter(|index| *index < frame_count) {
        painter.rect_stroke(
            Rect::from_center_size(
                egui::pos2(x(index), axis.center().y),
                egui::vec2(cell.max(3.0), axis.height()),
            ),
            0.0,
            Stroke::new(1.0_f32, INK),
            egui::StrokeKind::Inside,
        );
    }
    text(
        &painter,
        rect.left_bottom() + egui::vec2(12.0, -1.0),
        Align2::LEFT_BOTTOM,
        "001",
        MUTED,
    );
    text(
        &painter,
        rect.center_bottom() - egui::vec2(0.0, 1.0),
        Align2::CENTER_BOTTOM,
        "CAPTURE ORDER / OBSERVED MARKS",
        MUTED,
    );
    text(
        &painter,
        rect.right_bottom() - egui::vec2(12.0, 1.0),
        Align2::RIGHT_BOTTOM,
        &format!("{frame_count:03}"),
        MUTED,
    );

    let nearest = interaction
        .hover_pos()
        .filter(|at| at.y < axis.top() - 6.0)
        .and_then(|at| {
            curves
                .iter()
                .map(|(pair, points)| (*pair, curve_distance(at, points)))
                .min_by(|a, b| a.1.total_cmp(&b.1))
                .filter(|(_, distance)| *distance <= 5.0)
        });
    let mut response = Response::default();
    if let Some((pair, _)) = nearest {
        painter.add(egui::Shape::line(
            edge(axis, pair, frame_count),
            Stroke::new(1.7_f32, INK),
        ));
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
        if interaction.clicked() {
            response.compare_pair = Some(pair);
        }
    }
    if (interaction.clicked() || interaction.dragged())
        && let Some(at) = interaction.interact_pointer_pos().filter(|at| {
            at.x >= axis.left()
                && at.x <= axis.right()
                && at.y >= axis.top() - 5.0
                && at.y <= axis.bottom() + 6.0
        })
    {
        response.selected = Some(frame_at(axis, frame_count, at.x));
    }
    let hovered_photo = interaction.hover_pos().and_then(|at| {
        photo_cards
            .iter()
            .rev()
            .find(|(_, card)| card.contains(at))
            .map(|(index, _)| *index)
    });
    if interaction.clicked()
        && let Some(index) = hovered_photo
    {
        response.selected = Some(index);
        response.compare_pair = None;
    }
    if let Some(index) = hovered_photo.or_else(|| {
        interaction
            .hover_pos()
            .filter(|at| axis.contains(*at))
            .map(|at| frame_at(axis, frame_count, at.x))
    }) {
        interaction.on_hover_ui(|ui| {
            ui.label(format!("Frame {:03}", index + 1));
            if let Some(texture) = photos.get(&index) {
                let size = texture.size_vec2();
                ui.image(egui::load::SizedTexture::new(
                    texture.id(),
                    size * (180.0 / size.x.max(size.y)),
                ));
                ui.label("Camera JPEG slice");
            }
            if progress.alignment_plane_observations.contains(&index) {
                ui.label("RAW comparison image observed");
            }
            if progress.alignment_pyramid_observations.contains(&index) {
                ui.label("Multiscale processing observed");
            }
            match progress.frame_observations.get(&index) {
                Some(FrameObservation::Processed) => {
                    ui.label("Merge processing finished");
                }
                Some(FrameObservation::Started) => {
                    ui.label("Merge start observed");
                }
                None => (),
            }
            ui.label("Blank marks mean not observed, not unprocessed.");
        });
    } else if progress.stage == Stage::Merge
        && let Some(at) = interaction.hover_pos().filter(|at| {
            at.y >= top + 24.0
                && at.y <= top + 36.0
                && at.x >= rect.left() + 132.0
                && at.x < rect.right() - 28.0
        })
    {
        let details = progress
            .bands
            .unwrap_or(progress.band_exponents.len())
            .min(31);
        if details > 0 {
            let band = (((at.x - rect.left() - 132.0) / (rect.width() - 160.0))
                * (details + 1) as f32)
                .floor() as usize;
            let label = if band == details {
                "Tone base".into()
            } else {
                format!("Detail scale {} / fine to coarse", band + 1)
            };
            let mut tooltip = label;
            if let Some(power) = progress.band_exponents.get(band) {
                tooltip.push_str(&format!("\nPlanned weight exponent: {power:.2}"));
            }
            if band == details
                && let Some(base) = &progress.base
            {
                tooltip.push_str(&format!("\n{base}"));
            }
            if let Some(fraction) = progress.band_averaged.get(band) {
                tooltip.push_str(&format!(
                    "\nObserved averaged coefficients: {:.1}%",
                    fraction * 100.0
                ));
            }
            tooltip.push_str("\nScale glyphs describe the method, not live frequency measurements. Fractions count coefficients, not photograph area or completion.");
            interaction.on_hover_text(tooltip);
        }
    }
    response
}

fn photo_card(painter: &egui::Painter, card: Rect, index: usize, texture: &egui::TextureHandle) {
    painter.rect_filled(card, 0.0, BG);
    let size = texture.size_vec2();
    let fit = (card.width() / size.x).min(card.height() / size.y);
    painter.image(
        texture.id(),
        Rect::from_center_size(card.center(), size * fit),
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        Color32::WHITE,
    );
    painter.rect_stroke(
        card,
        0.0,
        Stroke::new(0.7_f32, LINE),
        egui::StrokeKind::Inside,
    );
    let label = Rect::from_min_size(card.left_top(), egui::vec2(22.0, 10.0));
    painter.rect_filled(label, 0.0, BG.gamma_multiply(0.9));
    text(
        painter,
        label.left_top() + egui::vec2(1.0, 0.0),
        Align2::LEFT_TOP,
        &format!("{:03}", index + 1),
        INK,
    );
}

fn frame_x(axis: Rect, count: usize, index: usize) -> f32 {
    axis.left() + axis.width() * (index as f32 + 0.5) / count.max(1) as f32
}

fn frame_at(axis: Rect, count: usize, x: f32) -> usize {
    (((x - axis.left()) / axis.width() * count as f32)
        .floor()
        .max(0.0) as usize)
        .min(count.saturating_sub(1))
}

fn text(painter: &egui::Painter, at: Pos2, anchor: Align2, value: &str, colour: Color32) {
    painter.text(at, anchor, value, FontId::monospace(9.0), colour);
}

fn summary(progress: &PipelineProgress) -> String {
    match progress.stage {
        Stage::Preparing => "READ CAPTURE".into(),
        Stage::Alignment => match progress.alignment_phase {
            Some(AlignmentPhase::Planes) => progress
                .alignment_planes
                .map(|(done, total)| format!("{done}/{total} RAW READS"))
                .unwrap_or_else(|| "RAW READS".into()),
            Some(AlignmentPhase::Pyramids) => progress
                .alignment_pyramids
                .map(|(done, total)| format!("{done}/{total} MULTISCALE"))
                .unwrap_or_else(|| "MULTISCALE".into()),
            Some(AlignmentPhase::Pairs) => progress
                .alignment_pairs
                .map(|(done, accepted, total)| format!("{done}/{total} PAIRS / {accepted} FITS"))
                .unwrap_or_else(|| "PAIR COMPARISONS".into()),
            Some(phase) => phase.title().to_uppercase(),
            None => "ALIGNMENT".into(),
        },
        Stage::Merge => progress
            .frames_processed
            .zip(progress.frames_total)
            .map(|(done, total)| {
                progress
                    .frames_accepted
                    .map(|accepted| format!("{done}/{total} PROCESSED / {accepted} ACCEPTED"))
                    .unwrap_or_else(|| format!("{done}/{total} PROCESSED"))
            })
            .unwrap_or_else(|| "RAW MERGE / WAITING FOR COUNTS".into()),
        Stage::Rendering => "RECONSTRUCT / TONE / TIFF".into(),
        Stage::Complete => "TIFF SAVED".into(),
        Stage::Failed => "STOPPED / ERROR".into(),
        Stage::Cancelled => "CANCELLED".into(),
    }
}

fn edge(axis: Rect, pair: [usize; 2], count: usize) -> Vec<Pos2> {
    let a = egui::pos2(frame_x(axis, count, pair[0]), axis.top() - 2.0);
    let b = egui::pos2(frame_x(axis, count, pair[1]), axis.top() - 2.0);
    // Curvature is a layout device, never a displacement or fit score.
    let height = 16.0 + ((a.x - b.x).abs() / axis.width()).sqrt() * 60.0;
    let control = egui::pos2((a.x + b.x) * 0.5, a.y - height);
    (0..=20)
        .map(|step| {
            let t = step as f32 / 20.0;
            egui::pos2(
                (1.0 - t).powi(2) * a.x + 2.0 * (1.0 - t) * t * control.x + t * t * b.x,
                (1.0 - t).powi(2) * a.y + 2.0 * (1.0 - t) * t * control.y + t * t * b.y,
            )
        })
        .collect()
}

fn curve_distance(at: Pos2, points: &[Pos2]) -> f32 {
    points
        .windows(2)
        .map(|line| {
            let delta = line[1] - line[0];
            let fraction =
                ((at - line[0]).dot(delta) / delta.length_sq().max(f32::EPSILON)).clamp(0.0, 1.0);
            at.distance(line[0] + delta * fraction)
        })
        .fold(f32::INFINITY, f32::min)
}

fn capture_lanes(painter: &egui::Painter, rect: Rect, progress: &PipelineProgress, count: usize) {
    let left = rect.left() + 12.0;
    let right = rect.right() - 12.0;
    for (row, label, observed) in [
        (27.0, "R", &progress.alignment_plane_observations),
        (41.0, "S", &progress.alignment_pyramid_observations),
    ] {
        text(
            painter,
            egui::pos2(rect.left() + 2.0, rect.top() + row),
            Align2::LEFT_CENTER,
            label,
            MUTED,
        );
        painter.line_segment(
            [
                egui::pos2(left, rect.top() + row),
                egui::pos2(right, rect.top() + row),
            ],
            Stroke::new(1.0_f32, LINE),
        );
        for &index in observed {
            if index < count {
                let at = egui::pos2(
                    left + (right - left) * (index as f32 + 0.5) / count as f32,
                    rect.top() + row,
                );
                painter.line_segment(
                    [at - egui::vec2(0.0, 3.0), at + egui::vec2(0.0, 3.0)],
                    Stroke::new(1.5_f32, GREEN),
                );
            }
        }
    }
    if let Some(index) = progress.processing_frame.filter(|index| *index < count) {
        let at = egui::pos2(
            left + (right - left) * (index as f32 + 0.5) / count as f32,
            rect.top() + 58.0,
        );
        painter.line_segment(
            [at, at - egui::vec2(0.0, 12.0)],
            Stroke::new(1.5_f32, ACCENT),
        );
    }
}

fn scale_lanes(painter: &egui::Painter, rect: Rect, progress: &PipelineProgress) {
    let detail_bands = progress
        .bands
        .unwrap_or(progress.band_exponents.len())
        .min(31);
    let bands = if detail_bands > 0 {
        detail_bands + 1
    } else {
        0
    };
    let observed = bands > 0 && progress.band_averaged.len() == bands;
    text(
        painter,
        rect.left_top() + egui::vec2(12.0, 16.0),
        Align2::LEFT_TOP,
        if observed {
            "OBSERVED MIX"
        } else {
            "BLEND PLAN"
        },
        MUTED,
    );
    if bands == 0 {
        return;
    }
    let width = (rect.width() - 160.0).max(1.0);
    let start = rect.left() + 132.0;
    let step = width / bands as f32;
    let joint = egui::pos2(rect.left() + 96.0, rect.top() + 50.0);
    painter.add(egui::Shape::line(
        vec![
            egui::pos2(rect.left() + 64.0, rect.top() + 41.0),
            egui::pos2(joint.x, rect.top() + 41.0),
            joint,
            egui::pos2(start + width - step * 0.5, joint.y),
        ],
        Stroke::new(1.0_f32, MUTED.gamma_multiply(0.65)),
    ));
    for band in 0..bands {
        let bar = Rect::from_min_size(
            egui::pos2(start + step * band as f32, rect.top() + 24.0),
            egui::vec2((step - 4.0).max(1.0), 12.0),
        );
        painter.rect_filled(bar, 0.0, RAISED);
        let fraction = if observed {
            progress.band_averaged[band].clamp(0.0, 1.0)
        } else {
            0.0
        };
        if observed {
            painter.rect_filled(
                Rect::from_min_size(bar.min, egui::vec2(bar.width() * fraction, bar.height())),
                0.0,
                GREEN.gamma_multiply(0.8),
            );
            text(
                painter,
                bar.center(),
                Align2::CENTER_CENTER,
                &format!("{:.0}%", fraction * 100.0),
                INK,
            );
        } else if band + 1 == bands {
            painter.line_segment(
                [
                    bar.left_center() + egui::vec2(5.0, 0.0),
                    bar.right_center() - egui::vec2(5.0, 0.0),
                ],
                Stroke::new(1.0_f32, MUTED),
            );
        } else {
            // These line spacings identify the declared pyramid scales;
            // they are a method glyph, not a measured frequency response.
            let stripes = ((bar.width() - 8.0) / (3.0 * 2.0_f32.powi(band as i32)))
                .floor()
                .clamp(1.0, 24.0) as usize;
            for stripe in 0..stripes {
                let x = bar.left() + bar.width() * (stripe as f32 + 0.5) / stripes as f32;
                painter.line_segment(
                    [
                        egui::pos2(x, bar.top() + 2.0),
                        egui::pos2(x, bar.bottom() - 2.0),
                    ],
                    Stroke::new(1.0_f32, MUTED),
                );
            }
        }
        painter.line_segment(
            [bar.center_bottom(), egui::pos2(bar.center().x, joint.y)],
            Stroke::new(1.0_f32, MUTED.gamma_multiply(0.65)),
        );
        painter.circle_filled(egui::pos2(bar.center().x, joint.y), 1.4, MUTED);
    }
    text(
        painter,
        egui::pos2(start, rect.top() + 18.0),
        Align2::LEFT_CENTER,
        "FINE",
        MUTED,
    );
    text(
        painter,
        egui::pos2(start + width, rect.top() + 18.0),
        Align2::RIGHT_CENTER,
        if observed {
            "COARSE / % AVERAGED"
        } else {
            "COARSE"
        },
        MUTED,
    );
}

fn output_view(rect: Rect, coverage: Option<CoveragePlan>) -> Option<Rect> {
    match coverage? {
        CoveragePlan::Whole => Some(rect),
        CoveragePlan::Scaled(scale) => {
            Some(Rect::from_center_size(rect.center(), rect.size() * scale))
        }
        CoveragePlan::Cropped {
            width,
            height,
            x,
            y,
            grid_width,
            grid_height,
        } => Some(Rect::from_min_max(
            rect.min
                + egui::vec2(
                    rect.width() * x as f32 / grid_width as f32,
                    rect.height() * y as f32 / grid_height as f32,
                ),
            rect.min
                + egui::vec2(
                    rect.width() * (x + width) as f32 / grid_width as f32,
                    rect.height() * (y + height) as f32 / grid_height as f32,
                ),
        )),
        CoveragePlan::Uncovered => None,
    }
}

fn output_plane(
    painter: &egui::Painter,
    rect: Rect,
    progress: &PipelineProgress,
    photos: &BTreeMap<usize, &egui::TextureHandle>,
) {
    let centre = rect.center().x;
    let destination = Rect::from_center_size(
        egui::pos2(centre + 35.0, rect.top() + 35.0),
        egui::vec2(62.0, 32.0),
    );
    for (layer, (_, texture)) in photos.iter().take(3).enumerate() {
        let source = Rect::from_min_size(
            egui::pos2(
                centre - 104.0 + layer as f32 * 9.0,
                rect.top() + 20.0 + layer as f32 * 3.0,
            ),
            egui::vec2(42.0, 25.0),
        );
        painter.image(
            texture.id(),
            source,
            Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            Color32::from_white_alpha(150),
        );
        painter.rect_stroke(
            source,
            0.0,
            Stroke::new(0.7_f32, LINE),
            egui::StrokeKind::Inside,
        );
    }
    painter.line_segment(
        [
            egui::pos2(centre - 25.0, rect.top() + 35.0),
            destination.left_center() - egui::vec2(5.0, 0.0),
        ],
        Stroke::new(1.0_f32, MUTED),
    );
    painter.rect_stroke(
        destination,
        0.0,
        Stroke::new(1.0_f32, LINE),
        egui::StrokeKind::Inside,
    );
    if let Some(view) = output_view(destination, progress.coverage_plan) {
        painter.rect_filled(view, 0.0, ACCENT.gamma_multiply(0.2));
        painter.rect_stroke(
            view,
            0.0,
            Stroke::new(1.0_f32, ACCENT),
            egui::StrokeKind::Inside,
        );
    }
    let label = match progress.coverage_plan {
        Some(CoveragePlan::Uncovered) => "PARTIAL COVERAGE",
        Some(_) => "OUTPUT VIEW",
        None => "VIEW PENDING",
    };
    text(
        painter,
        destination.right_center() + egui::vec2(10.0, 0.0),
        Align2::LEFT_CENTER,
        label,
        MUTED,
    );
}

#[cfg(test)]
#[path = "stack-map-tests.rs"]
mod tests;
