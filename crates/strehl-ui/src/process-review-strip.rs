//! Always-visible review entry points, derived only from retained fallback data.
//! A fallback fraction describes a blend decision, never photographic quality.
use crate::{
    pipeline::{DiagnosticKind, DiagnosticSurface, PipelineProgress},
    theme,
};
use eframe::egui::{self, Align2, FontId, Rect, Sense, Ui};

#[derive(Default)]
pub(super) struct Response {
    pub hovered: Option<usize>,
    pub selected: Option<usize>,
}

pub(super) fn show<'a>(
    ui: &mut Ui,
    rect: Rect,
    progress: &PipelineProgress,
    maps: impl Iterator<Item = &'a DiagnosticSurface>,
    selected: usize,
) -> Response {
    let mut result = Response::default();
    if rect.width() < 210.0 || rect.height() < 24.0 {
        return result;
    }
    let maps: Vec<_> = maps
        .filter(|m| m.kind == DiagnosticKind::Averaging)
        .collect();
    // The following base octave is an intentional tone average, not a failed
    // detail gate. Only the announced Laplacian bands belong in this strip.
    let levels = progress.bands.unwrap_or(0).min(16);
    let p = ui.painter_at(rect);
    theme::rule(&p, rect.left_top(), rect.right_top(), theme::LINE);
    if levels == 0 {
        p.text(
            rect.center(),
            Align2::CENTER_CENTER,
            if progress.stage == crate::pipeline::Stage::Complete {
                "No blend evidence recorded"
            } else {
                "Awaiting measured blend evidence"
            },
            FontId::proportional(9.0),
            theme::MUTED,
        );
        return result;
    }
    let label_width = if rect.width() < 360.0 { 70.0 } else { 100.0 };
    p.text(
        rect.min + egui::vec2(0.0, 4.0),
        Align2::LEFT_TOP,
        "FALLBACK",
        FontId::monospace(8.5),
        theme::AMBER,
    );
    p.text(
        rect.min + egui::vec2(0.0, 16.0),
        Align2::LEFT_TOP,
        if progress.output_geometry.is_some() {
            "by photo px"
        } else {
            "by grid px"
        },
        FontId::proportional(8.0),
        theme::MUTED,
    );
    let width = (rect.width() - label_width) / levels as f32;
    let compact = rect.height() < 34.0;
    let allowed = ui.is_enabled()
        && ui.input(|i| i.focused && i.viewport().focused != Some(false))
        && ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()))
        && !egui::Popup::is_any_open(ui.ctx());
    for level in 0..levels {
        let cell = Rect::from_min_size(
            rect.min + egui::vec2(label_width + level as f32 * width, 3.0),
            egui::vec2(width, rect.height() - 3.0),
        );
        let map = maps
            .iter()
            .filter(|m| m.level == level)
            .max_by_key(|m| m.sequence);
        let measured = progress
            .band_averaged
            .get(level)
            .copied()
            .filter(|f| f.is_finite() && (0.0..=1.0).contains(f));
        let sampled = map.and_then(|m| sampled_fraction(m));
        let value = measured.or(sampled);
        let hit = ui.interact(
            cell,
            ui.id().with(("fallback-review", level)),
            Sense::click(),
        );
        if allowed && hit.hovered() && map.is_some() {
            result.hovered = Some(level);
        }
        if allowed && hit.clicked() && map.is_some() {
            result.selected = Some(level);
        }
        let track = Rect::from_min_size(
            cell.min + egui::vec2(3.0, if compact { 9.0 } else { 2.0 }),
            egui::vec2((width - 6.0).max(1.0), if compact { 3.0 } else { 5.0 }),
        );
        p.rect_filled(track, 0.0, theme::PANEL);
        if let Some(fraction) = value {
            p.rect_filled(
                Rect::from_min_max(
                    track.min,
                    egui::pos2(track.left() + track.width() * fraction, track.bottom()),
                ),
                0.0,
                theme::AMBER.gamma_multiply(if hit.hovered() || level == selected {
                    1.0
                } else {
                    0.65
                }),
            );
        }
        if width >= 25.0 {
            p.text(
                egui::pos2(
                    cell.center().x,
                    cell.top() + if compact { 15.0 } else { 11.0 },
                ),
                Align2::CENTER_TOP,
                value.map_or_else(
                    || "—".into(),
                    |v| {
                        format!(
                            "{}{:0.0}%",
                            if measured.is_none() { "~" } else { "" },
                            v * 100.0
                        )
                    },
                ),
                FontId::monospace(8.0),
                if hit.hovered() {
                    theme::INK
                } else {
                    theme::MUTED
                },
            );
        }
        if width >= 25.0 {
            p.text(
                egui::pos2(
                    cell.center().x,
                    cell.top() + if compact { 0.0 } else { 20.0 },
                ),
                Align2::CENTER_TOP,
                crate::process_output_space::detail_label(level, progress.output_geometry)
                    .split_whitespace()
                    .next()
                    .unwrap_or("?")
                    .to_owned(),
                FontId::monospace(6.5),
                theme::MUTED,
            );
        }
        let reading = value.map_or_else(
            || "No observation".to_owned(),
            |v| {
                format!(
                    "{:.1}% {}",
                    v * 100.0,
                    if measured.is_some() {
                        "of whole band"
                    } else {
                        "of retained samples"
                    }
                )
            },
        );
        let receipt = map.map_or_else(
            || "No retained spatial map".to_owned(),
            |m| format!("Spatial samples after {} folded captures", m.folded),
        );
        hit.on_hover_text(format!("{} {reading}. {receipt}. Where no detail weight survives the gate, the engine uses the averaged fallback. This is not a defect score. Hover: locate retained samples · click: keep this detail size.", crate::process_output_space::detail_tooltip(level, progress.output_geometry)));
    }
    result
}

fn sampled_fraction(map: &DiagnosticSurface) -> Option<f32> {
    (map.width.checked_mul(map.height)? == map.pixels.len()
        && !map.pixels.is_empty()
        && map.min == 0.0
        && map.max == 1.0)
        .then(|| map.pixels.iter().filter(|&&v| v > 0).count() as f32 / map.pixels.len() as f32)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn observed_fraction_does_not_impute_missing_or_empty_maps() {
        let mut packet = DiagnosticSurface {
            sequence: 1,
            frame: 0,
            level: 2,
            kind: DiagnosticKind::Averaging,
            scope: crate::pipeline::DiagnosticScope::Stack,
            scale: crate::pipeline::DiagnosticScale::Linear,
            width: 2,
            height: 2,
            min: 0.0,
            max: 1.0,
            pixels: vec![0, 255, 0, 0].into(),
            folded: 3,
        };
        assert_eq!(sampled_fraction(&packet), Some(0.25));
        packet.width = 3;
        assert_eq!(sampled_fraction(&packet), None);
        packet.width = 0;
        packet.height = 0;
        packet.pixels = vec![].into();
        assert_eq!(sampled_fraction(&packet), None);
    }
}

#[cfg(test)]
#[path = "process-review-strip-review-tests.rs"]
mod review_tests;
