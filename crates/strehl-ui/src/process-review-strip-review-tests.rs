//! Independent display and pointer witnesses: these inspect the rendered
//! labels and actual widget responses, rather than reproducing strip geometry.
use super::*;
use crate::pipeline::{DiagnosticScale, DiagnosticScope};
use eframe::egui::{Event, FullOutput, Pos2};

fn bounds(width: f32) -> Rect {
    bounds_height(width, 41.0)
}

fn bounds_height(width: f32, height: f32) -> Rect {
    Rect::from_min_size(egui::pos2(20.0, 30.0), egui::vec2(width, height))
}

fn packet(level: usize) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence: level as u64 + 1,
        frame: 2,
        level,
        kind: DiagnosticKind::Averaging,
        scope: DiagnosticScope::Stack,
        scale: DiagnosticScale::Linear,
        width: 2,
        height: 2,
        min: 0.0,
        max: 1.0,
        pixels: vec![0, 255, 0, 0].into(),
        folded: 3,
    }
}

fn paint(
    ctx: &egui::Context,
    width: f32,
    time: f64,
    progress: &PipelineProgress,
    maps: &[DiagnosticSurface],
    events: Vec<Event>,
) -> (Response, FullOutput) {
    paint_sized(ctx, bounds(width), time, progress, maps, events)
}

fn paint_sized(
    ctx: &egui::Context,
    rect: Rect,
    time: f64,
    progress: &PipelineProgress,
    maps: &[DiagnosticSurface],
    events: Vec<Event>,
) -> (Response, FullOutput) {
    let mut response = Response::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1200.0, 300.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = show(ui, rect, progress, maps.iter(), 0);
                });
        },
    );
    (response, output)
}

fn labels(output: &FullOutput) -> Vec<(String, Rect)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => {
                Some((text.galley.text().to_owned(), text.visual_bounding_rect()))
            }
            _ => None,
        })
        .collect()
}

fn click(at: Pos2, pressed: bool) -> Vec<Event> {
    vec![
        Event::PointerMoved(at),
        Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        },
    ]
}

#[test]
fn intentional_tone_mean_is_not_drawn_as_rejected_detail() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.band_averaged = vec![0.21, 0.21, 0.21, 0.21, 0.21, 0.21, 0.21, 1.0];
    progress.base = Some("plain mean".into());
    let maps: Vec<_> = (0..8).map(packet).collect();
    let (_, output) = paint(&ctx, 900.0, 0.0, &progress, &maps, vec![]);
    let text = labels(&output);
    assert_eq!(
        text.iter().filter(|(s, _)| s == "21%").count(),
        7,
        "fixture must draw all seven measured detail fractions"
    );
    assert!(
        !text.iter().any(|(s, _)| s == "100%" || s == "128px"),
        "the deliberate plain-mean tone base is not failed gate evidence"
    );
}

#[test]
fn labels_remain_disjoint_at_dense_narrow_and_hidpi_sizes() {
    let mut progress = PipelineProgress::default();
    progress.bands = Some(16);
    progress.band_averaged = vec![1.0; 16];
    let maps: Vec<_> = (0..16).map(packet).collect();
    for (width, height) in [210.0, 320.0, 1060.0]
        .into_iter()
        .flat_map(|width| [28.0, 41.0].map(|height| (width, height)))
    {
        for dpi in [1.0, 1.5, 2.0] {
            let ctx = egui::Context::default();
            ctx.set_pixels_per_point(dpi);
            let rect = bounds_height(width, height);
            let (_, output) = paint_sized(&ctx, rect, 0.0, &progress, &maps, vec![]);
            let text = labels(&output);
            assert!(
                text.iter().any(|(s, _)| s == "FALLBACK"),
                "fixture must draw strip"
            );
            if width == 1060.0 {
                assert_eq!(
                    text.iter().filter(|(s, _)| s == "100%").count(),
                    16,
                    "wide witness must render numeric evidence, not evade overlap by hiding everything"
                );
            }
            for (i, (label, area)) in text.iter().enumerate() {
                assert!(
                    rect.expand(0.5).contains_rect(*area),
                    "{label:?} escaped the strip at width{width} height{height} dpi{dpi}: {area:?}"
                );
                for (other, other_area) in &text[i + 1..] {
                    assert!(
                        !area.shrink(0.25).intersects(other_area.shrink(0.25)),
                        "{label:?} overlaps {other:?} at width{width} height{height} dpi{dpi}"
                    );
                }
            }
        }
    }
}

#[test]
fn hover_and_click_name_the_visible_band_and_missing_maps_do_not_open_one() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(3);
    progress.band_averaged = vec![0.1, 0.2, 0.3];
    let maps: Vec<_> = (0..3).map(packet).collect();
    paint(&ctx, 700.0, 0.0, &progress, &maps, vec![]);
    let (_, output) = paint(&ctx, 700.0, 0.1, &progress, &maps, vec![]);
    let at = labels(&output)
        .into_iter()
        .find(|(s, _)| s == "4px")
        .expect("third-band label")
        .1
        .center();
    let hover = paint(
        &ctx,
        700.0,
        0.2,
        &progress,
        &maps,
        vec![Event::PointerMoved(at)],
    )
    .0;
    assert_eq!(hover.hovered, Some(2));
    assert_eq!(hover.selected, None, "hover must stay temporary");
    paint(&ctx, 700.0, 0.3, &progress, &maps, click(at, true));
    assert_eq!(
        paint(&ctx, 700.0, 0.4, &progress, &maps, click(at, false))
            .0
            .selected,
        Some(2)
    );
    let mut wrong_kind = packet(2);
    wrong_kind.kind = DiagnosticKind::GateSupport;
    let missing = [packet(0), packet(1), wrong_kind];
    let blank = paint(
        &ctx,
        700.0,
        0.8,
        &progress,
        &missing,
        vec![Event::PointerMoved(at)],
    )
    .0;
    assert_eq!(blank.hovered, None);
    paint(&ctx, 700.0, 0.9, &progress, &missing, click(at, true));
    assert_eq!(
        paint(&ctx, 700.0, 1.0, &progress, &missing, click(at, false))
            .0
            .selected,
        None,
        "a final scalar fraction cannot invent a spatial map"
    );
}

#[test]
fn final_scalar_and_sample_estimate_remain_distinguishable_and_malformed_is_unknown() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(3);
    progress.band_averaged = vec![0.13];
    let mut malformed = packet(2);
    malformed.width = 3;
    let maps = [packet(0), packet(1), malformed];
    let (_, output) = paint(&ctx, 700.0, 0.0, &progress, &maps, vec![]);
    let text = labels(&output);
    assert_eq!(
        text.iter().filter(|(s, _)| s == "13%").count(),
        1,
        "whole-band fraction must outrank the deliberately different25% sparse map"
    );
    assert_eq!(
        text.iter().filter(|(s, _)| s == "~25%").count(),
        1,
        "only a valid map can supply an approximate sample fraction"
    );
    assert_eq!(
        text.iter().filter(|(s, _)| s == "—").count(),
        1,
        "malformed dimensions cannot manufacture a fraction"
    );
}
