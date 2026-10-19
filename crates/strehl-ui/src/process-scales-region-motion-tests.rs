//! Region focus is one coordinated camera movement, including at equal zoom.
use super::*;
use crate::pipeline::PipelineProgress;

fn paint(ctx: &egui::Context, scales: &mut ProcessScales, time: f64) {
    let progress = PipelineProgress::default();
    let input = Input {
        epoch: 1,
        progress: &progress,
        frame_count: 1,
        selected: 0,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    };
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(800.0, 600.0))),
            time: Some(time),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    scales.show(ui, ui.max_rect(), &input);
                });
        },
    );
}

fn close_point(actual: Pos2, expected: Pos2) {
    assert!(
        actual.distance(expected) < 0.0001,
        "{actual:?} != {expected:?}"
    );
}

fn scene(pin: Pos2, zoom: f32) -> (egui::Context, ProcessScales) {
    let ctx = egui::Context::default();
    let mut scales = ProcessScales::default();
    paint(&ctx, &mut scales, 0.0);
    scales.set_view(pin, zoom);
    paint(&ctx, &mut scales, 1.0);
    close_point(scales.painted_pin(), pin);
    (ctx, scales)
}

#[test]
fn region_focus_moves_center_and_zoom_together_without_a_first_frame_jump() {
    let origin = egui::pos2(0.4, 0.4);
    let target = egui::pos2(0.65, 0.6);
    let (ctx, mut scales) = scene(origin, 2.0);
    scales.focus_region(Rect::from_center_size(target, egui::vec2(0.25, 0.125)));
    let intent = scales.view();
    close_point(intent.pin, target);
    assert_eq!(intent.zoom, 4.0);

    paint(&ctx, &mut scales, 1.0);
    close_point(scales.painted_pin(), origin);
    assert!((scales.painted_aperture.width() - 0.5).abs() < 0.000001);

    paint(&ctx, &mut scales, 1.09);
    close_point(scales.painted_pin(), egui::pos2(0.525, 0.5));
    assert!((scales.painted_aperture.width() - 1.0 / 3.0).abs() < 0.0001);
    assert!(
        scales.transitioning(),
        "the fixture must observe real motion"
    );
    assert_eq!(
        scales.view(),
        intent,
        "history records the requested region, not a midway camera pose"
    );

    paint(&ctx, &mut scales, 1.181);
    close_point(scales.painted_pin(), target);
    assert!((scales.painted_aperture.width() - 0.25).abs() < 0.0001);
    assert_eq!(scales.view(), intent);
    assert!(!scales.transitioning());
}

#[test]
fn equal_zoom_region_selection_still_animates_the_new_center() {
    let origin = egui::pos2(0.3, 0.45);
    let target = egui::pos2(0.7, 0.55);
    let (ctx, mut scales) = scene(origin, 4.0);
    scales.focus_region(Rect::from_center_size(target, egui::vec2(0.25, 0.2)));
    assert!(
        scales.transitioning(),
        "equal zoom cannot suppress center motion"
    );
    paint(&ctx, &mut scales, 1.0);
    close_point(scales.painted_pin(), origin);
    paint(&ctx, &mut scales, 1.09);
    close_point(scales.painted_pin(), egui::pos2(0.5, 0.5));
    assert_eq!(scales.magnification, 4.0);
    assert!(scales.transitioning());
    paint(&ctx, &mut scales, 1.181);
    close_point(scales.painted_pin(), target);
    assert!(!scales.transitioning());
}

#[test]
fn direct_photo_pan_interrupts_region_motion_without_later_snapback() {
    let (ctx, mut scales) = scene(egui::pos2(0.4, 0.4), 2.0);
    scales.focus_region(Rect::from_center_size(
        egui::pos2(0.65, 0.6),
        egui::vec2(0.25, 0.2),
    ));
    paint(&ctx, &mut scales, 1.09);
    let pan_target = egui::pos2(0.45, 0.6);
    let interrupted_zoom = scales.magnification;
    assert!((interrupted_zoom - 3.0).abs() < 0.0001);
    scales.set_view(pan_target, interrupted_zoom);
    let pan_intent = scales.view();
    paint(&ctx, &mut scales, 1.1);
    close_point(scales.painted_pin(), pan_target);
    paint(&ctx, &mut scales, 2.0);
    close_point(scales.painted_pin(), pan_target);
    assert!((scales.magnification - interrupted_zoom).abs() < 0.0001);
    assert_eq!(scales.view(), pan_intent);
    assert!(!scales.transitioning());
}

#[test]
fn linked_pin_interruption_clears_the_old_region_center_target() {
    let (ctx, mut scales) = scene(egui::pos2(0.3, 0.45), 4.0);
    scales.focus_region(Rect::from_center_size(
        egui::pos2(0.7, 0.55),
        egui::vec2(0.25, 0.2),
    ));
    paint(&ctx, &mut scales, 1.09);
    let pin = egui::pos2(0.4, 0.6);
    scales.set_pin(pin);
    paint(&ctx, &mut scales, 2.0);
    close_point(scales.painted_pin(), pin);
    close_point(scales.view().pin, pin);
    assert!(!scales.transitioning());
}
