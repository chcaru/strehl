//! Independent actual-input witnesses for the completed capture ribbon. The
//! targets deliberately include non-thumbnail captures and missing observations.
use super::*;
use crate::pipeline::{
    DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface, PipelineProgress,
};

const SIZE: [f32; 2] = [960.0, 290.0];

fn rect() -> Rect {
    Rect::from_min_size(egui::pos2(20.0, 30.0), egui::vec2(900.0, HEIGHT))
}

fn fixture() -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    progress.bands = Some(7);
    for (frame, pixels) in [
        (4, vec![0, 0, 0, 0]),
        (31, vec![0, 255, 0, 255]),
        (66, vec![255; 4]),
    ] {
        progress.admission_archive.ingest(
            &DiagnosticSurface {
                sequence: frame as u64 + 1,
                frame,
                level: 0,
                kind: DiagnosticKind::GateSupport,
                scope: DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width: 2,
                height: 2,
                min: 0.0,
                max: 1.0,
                pixels: pixels.into(),
                folded: 1,
            },
            [131, 99],
        );
    }
    progress
}

fn input(progress: &PipelineProgress, epoch: u64) -> Input<'_> {
    Input {
        epoch,
        progress,
        frame_count: 67,
        selected: 0,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}

fn paint_with_output(
    ribbon: &mut CaptureParticipation,
    ctx: &egui::Context,
    progress: &PipelineProgress,
    epoch: u64,
    time: f64,
    events: Vec<egui::Event>,
    modal: bool,
) -> (ParticipationResponse, egui::FullOutput) {
    let mut response = ParticipationResponse::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, SIZE.into())),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = ribbon.show(
                        ui,
                        rect(),
                        &input(progress, epoch),
                        &progress.admission_archive,
                        0,
                        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                    );
                });
            if modal {
                egui::Modal::new(egui::Id::new("independent-ribbon-modal")).show(ctx, |ui| {
                    ui.label("Choose a bracket");
                });
            }
        },
    );
    (response, output)
}

fn paint(
    ribbon: &mut CaptureParticipation,
    ctx: &egui::Context,
    progress: &PipelineProgress,
    epoch: u64,
    time: f64,
    events: Vec<egui::Event>,
    modal: bool,
) -> ParticipationResponse {
    paint_with_output(ribbon, ctx, progress, epoch, time, events, modal).0
}

fn target(output: &egui::FullOutput, frame: usize) -> Pos2 {
    // Locate the actual painted evidence track. Its full capture axis stays
    // linear even when contact cards become denser or use even visual slots.
    let label_y = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Full image" => {
                Some(text.visual_bounding_rect().center().y)
            }
            _ => None,
        })
        .expect("full-image admission plot label");
    let points = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && (points[1].x - points[0].x) > rect().width() * 0.5
                    && (label_y + 1.0..label_y + 25.0).contains(&points[0].y) =>
            {
                Some(*points)
            }
            _ => None,
        })
        .expect("painted scene evidence track");
    points[0].lerp(points[1], frame as f32 / 66.0) - egui::vec2(0.0, 4.0)
}

fn contact_bounds(output: &egui::FullOutput, frame: usize) -> Rect {
    let label = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text)
                if text.galley.text() == format!("{:03}", frame + 1)
                    && shape
                        .clip_rect
                        .contains(text.visual_bounding_rect().center()) =>
            {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
        .expect("actual capture label");
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Rect(card)
                if card.fill == BG
                    && (card.rect.center().x - label.x).abs() < 2.0
                    && card.rect.height() >= 24.0
                    && (card.rect.bottom() + 5.0 - label.y).abs() < 2.0
                    && shape.clip_rect.contains_rect(card.rect) =>
            {
                Some(card.rect)
            }
            _ => None,
        })
        .expect("painted card under capture label")
}

fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

fn key(key: egui::Key) -> Vec<egui::Event> {
    [true, false]
        .map(|pressed| egui::Event::Key {
            key,
            physical_key: None,
            pressed,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        })
        .into()
}

fn warm(
    ribbon: &mut CaptureParticipation,
    ctx: &egui::Context,
    progress: &PipelineProgress,
) -> egui::FullOutput {
    paint(ribbon, ctx, progress, 1, 0.0, vec![], false);
    paint_with_output(ribbon, ctx, progress, 1, 0.1, vec![], false).1
}

#[test]
fn actual_hover_only_marks_support_but_deliberate_drag_requests_a_persistent_source() {
    let ctx = egui::Context::default();
    let progress = fixture();
    let mut ribbon = CaptureParticipation::default();
    let scene = warm(&mut ribbon, &ctx, &progress);
    assert!(
        !ribbon.indices().contains(&30),
        "the hovered sample must not have a thumbnail anchor"
    );
    let at = target(&scene, 30);
    let hovered = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.2,
        vec![egui::Event::PointerMoved(at)],
        false,
    );
    assert_eq!(hovered.frame, Some(30));
    assert_eq!(hovered.open_source, None);
    assert!(!hovered.held);
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.3,
        vec![button(at, true)],
        false,
    );
    let scrub = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.4,
        vec![egui::Event::PointerMoved(target(&scene, 66))],
        false,
    );
    assert_eq!(scrub.frame, Some(66));
    assert_eq!(scrub.open_source, Some(66));
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.5,
        vec![button(target(&scene, 66), false)],
        false,
    );
    let left = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.6,
        vec![egui::Event::PointerMoved(egui::pos2(5.0, 200.0))],
        false,
    );
    assert_eq!(
        left.frame,
        Some(66),
        "a deliberate lane drag holds its final footprint after release"
    );
    assert_eq!(ribbon.held, Some(66));
}

#[test]
fn held_capture_and_keyboard_steps_survive_stationary_pointer_then_escape_clears() {
    let ctx = egui::Context::default();
    let progress = fixture();
    let mut ribbon = CaptureParticipation::default();
    let scene = warm(&mut ribbon, &ctx, &progress);
    let at = target(&scene, 31);
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.2,
        vec![egui::Event::PointerMoved(at), button(at, true)],
        false,
    );
    let clicked = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.3,
        vec![button(at, false)],
        false,
    );
    assert_eq!(clicked.frame, Some(31));
    assert!(clicked.held);
    let next = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.4,
        key(egui::Key::ArrowRight),
        false,
    );
    assert_eq!(next.frame, Some(32));
    let idle = paint(&mut ribbon, &ctx, &progress, 1, 0.5, vec![], false);
    assert_eq!(
        idle.frame,
        Some(32),
        "stationary hover must not undo an intentional keyboard step"
    );
    let next = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.6,
        key(egui::Key::ArrowRight),
        false,
    );
    assert_eq!(next.frame, Some(33));
    let left = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.7,
        vec![egui::Event::PointerMoved(egui::pos2(5.0, 200.0))],
        false,
    );
    assert_eq!(left.frame, Some(33));
    assert!(left.held);
    let escaped = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.8,
        key(egui::Key::Escape),
        false,
    );
    assert_eq!(escaped.frame, None);
    assert_eq!(ribbon.held, None);
}

#[test]
fn modal_and_new_capture_cannot_reuse_or_advance_a_held_identity() {
    let ctx = egui::Context::default();
    let progress = fixture();
    let mut ribbon = CaptureParticipation::default();
    let scene = warm(&mut ribbon, &ctx, &progress);
    let at = target(&scene, 31);
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.2,
        vec![egui::Event::PointerMoved(at), button(at, true)],
        false,
    );
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.3,
        vec![button(at, false)],
        false,
    );
    assert_eq!(
        ribbon.held,
        Some(31),
        "modal must interrupt a real held capture"
    );
    paint(&mut ribbon, &ctx, &progress, 1, 0.4, vec![], true);
    paint(&mut ribbon, &ctx, &progress, 1, 0.5, vec![], true);
    let blocked = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.6,
        key(egui::Key::ArrowRight),
        true,
    );
    assert_eq!(blocked.frame, None);
    assert_eq!(blocked.open_source, None);
    assert_eq!(ribbon.held, Some(31));
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        2,
        0.7,
        vec![egui::Event::PointerMoved(egui::pos2(5.0, 200.0))],
        false,
    );
    assert_eq!(
        ribbon.held, None,
        "a new bracket cannot inherit a capture hold"
    );
}

#[test]
fn final_thumbnail_edges_keep_identity_and_double_click_resets_the_modifier() {
    let ctx = egui::Context::default();
    let progress = fixture();
    let mut ribbon = CaptureParticipation::default();
    let scene = warm(&mut ribbon, &ctx, &progress);
    let named = ribbon.indices()[ribbon.indices().len() / 2];
    // This point lies near the pictured capture's left edge; the continuous
    // evidence lane at the same x would target a different capture.
    let card = contact_bounds(&scene, named);
    let at = card.left_center() + egui::vec2(1.0, 0.0);
    let lane_at = egui::pos2(at.x, target(&scene, 0).y);
    let lane = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.12,
        vec![egui::Event::PointerMoved(lane_at)],
        false,
    );
    assert!(lane.frame.is_some());
    assert_ne!(
        lane.frame,
        Some(named),
        "fixture must distinguish the card from the full capture axis"
    );
    let hover = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.15,
        vec![egui::Event::PointerMoved(at)],
        false,
    );
    assert_eq!(
        hover.frame, lane.frame,
        "hover continues along the full capture axis even over a contact edge"
    );
    let named = hover.frame.unwrap();
    // Hover has replaced this card with the current actual source. The click
    // must pick that newly painted identity, not its obsolete sparse anchor.
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.2,
        vec![button(at, true)],
        false,
    );
    let single = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.25,
        vec![button(at, false)],
        false,
    );
    assert_eq!(single.open_source, Some(named));
    assert_eq!(single.frame, Some(named));
    paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.3,
        vec![button(at, true)],
        false,
    );
    let double = paint(
        &mut ribbon,
        &ctx,
        &progress,
        1,
        0.35,
        vec![button(at, false)],
        false,
    );
    assert_eq!(double.open_source, None);
    assert!(double.reset_view && double.return_photo);
    assert_eq!(double.frame, None);
    assert_eq!(ribbon.held, None);
}
