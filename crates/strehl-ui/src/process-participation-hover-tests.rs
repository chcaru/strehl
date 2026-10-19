//! Actual-pointer witnesses for transient source exploration and its bounded
//! grace, including a neighboring real control that must keep input ownership.
use super::*;
use crate::pipeline::PipelineProgress;

fn bounds() -> Rect {
    Rect::from_min_size(egui::pos2(20.0, 70.0), egui::vec2(940.0, HEIGHT))
}
fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}
fn paint(
    row: &mut CaptureParticipation,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> (ParticipationResponse, bool, egui::FullOutput) {
    paint_focused(row, ctx, time, events, true)
}
fn paint_focused(
    row: &mut CaptureParticipation,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
    focused: bool,
) -> (ParticipationResponse, bool, egui::FullOutput) {
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let data = Input {
        epoch: 1,
        progress: &progress,
        frame_count: 67,
        selected: 3,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    };
    let mut response = ParticipationResponse::default();
    let mut neighbor = false;
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 360.0))),
            time: Some(time),
            events,
            focused,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = row.show(
                        ui,
                        bounds(),
                        &data,
                        &progress.admission_archive,
                        0,
                        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                    );
                    neighbor = ui
                        .put(
                            Rect::from_min_size(
                                egui::pos2(450.0, bounds().bottom() + 8.0),
                                egui::vec2(100.0, 24.0),
                            ),
                            egui::Button::new("Neighbor"),
                        )
                        .clicked();
                });
        },
    );
    (response, neighbor, output)
}
fn point(output: &egui::FullOutput, frame: usize) -> Pos2 {
    let label = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Full image" => {
                Some(text.visual_bounding_rect().center().y)
            }
            _ => None,
        })
        .unwrap();
    let line = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && points[1].x - points[0].x > bounds().width() * 0.5
                    && (label + 1.0..label + 25.0).contains(&points[0].y) =>
            {
                Some(*points)
            }
            _ => None,
        })
        .unwrap();
    line[0].lerp(line[1], frame as f32 / 66.0) - egui::vec2(0.0, 4.0)
}

#[test]
fn hover_grace_requires_actual_entry_tracks_horizontal_motion_then_expires() {
    let ctx = egui::Context::default();
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, 0.0, vec![]);
    let scene = paint(&mut row, &ctx, 0.1, vec![]).2;
    let a = point(&scene, 12);
    let b = point(&scene, 39);
    let outside = egui::pos2(a.x, bounds().bottom() + 24.0);
    assert_eq!(
        paint(
            &mut row,
            &ctx,
            0.2,
            vec![egui::Event::PointerMoved(outside)]
        )
        .0
        .hover_source,
        None,
        "the grace band cannot arm by itself"
    );
    let inside = paint(&mut row, &ctx, 0.3, vec![egui::Event::PointerMoved(a)]).0;
    assert_eq!(inside.hover_source, Some(12));
    assert_eq!(inside.open_source, None);
    assert!(row.held.is_none() && row.spans.is_empty());
    let across = egui::pos2(b.x, bounds().bottom() + 24.0);
    assert_eq!(
        paint(&mut row, &ctx, 0.4, vec![egui::Event::PointerMoved(across)])
            .0
            .hover_source,
        Some(39)
    );
    assert_eq!(paint(&mut row, &ctx, 0.55, vec![]).0.hover_source, Some(39));
    assert_eq!(
        paint(&mut row, &ctx, 0.65, vec![]).0.hover_source,
        None,
        "stationary outside hover expires; horizontal motion cannot refresh its clock"
    );
    assert_eq!(
        paint(
            &mut row,
            &ctx,
            0.7,
            vec![egui::Event::PointerMoved(outside)]
        )
        .0
        .hover_source,
        None
    );
    assert_eq!(
        paint(&mut row, &ctx, 0.8, vec![egui::Event::PointerMoved(a)])
            .0
            .hover_source,
        Some(12)
    );
    assert_eq!(
        paint(
            &mut row,
            &ctx,
            0.9,
            vec![egui::Event::PointerMoved(egui::pos2(
                a.x,
                bounds().bottom() + 41.0
            ))]
        )
        .0
        .hover_source,
        None,
        "grace is spatially bounded as well as time bounded"
    );
}

#[test]
fn clear_restore_and_neighbor_actions_cannot_rearm_a_stationary_hover() {
    let ctx = egui::Context::default();
    let mut row = CaptureParticipation::default();
    let scene = paint(&mut row, &ctx, 0.0, vec![]).2;
    paint(&mut row, &ctx, 0.1, vec![]);
    let at = point(&scene, 20);
    assert_eq!(
        paint(&mut row, &ctx, 0.2, vec![egui::Event::PointerMoved(at)])
            .0
            .hover_source,
        Some(20)
    );
    row.clear();
    assert_eq!(paint(&mut row, &ctx, 0.3, vec![]).0.hover_source, None);
    let state = row.selection();
    row.restore_selection(&state);
    assert_eq!(paint(&mut row, &ctx, 0.4, vec![]).0.hover_source, None);
    assert_eq!(
        paint(
            &mut row,
            &ctx,
            0.5,
            vec![egui::Event::PointerMoved(point(&scene, 21))]
        )
        .0
        .hover_source,
        Some(21)
    );
    let neighbor = egui::pos2(500.0, bounds().bottom() + 20.0);
    let press = paint(
        &mut row,
        &ctx,
        0.6,
        vec![egui::Event::PointerMoved(neighbor), button(neighbor, true)],
    );
    assert!(press.0.hover_source.is_none() && press.0.open_source.is_none());
    let release = paint(&mut row, &ctx, 0.7, vec![button(neighbor, false)]);
    assert!(
        release.1,
        "the real neighboring button must own the click, despite the grace band"
    );
    assert!(release.0.hover_source.is_none());
    assert!(paint(&mut row, &ctx, 0.8, vec![]).0.hover_source.is_none());
}

#[test]
fn wheel_steps_transient_sources_without_mutating_spans_and_leaves_neighbor_scroll_alone() {
    let ctx = egui::Context::default();
    let mut row = CaptureParticipation::default();
    let scene = paint(&mut row, &ctx, 0.0, vec![]).2;
    paint(&mut row, &ctx, 0.1, vec![]);
    row.select_frame(4);
    let held = row.selection();
    let at = point(&scene, 20);
    paint(&mut row, &ctx, 0.2, vec![egui::Event::PointerMoved(at)]);
    let wheel = |dy| egui::Event::MouseWheel {
        unit: egui::MouseWheelUnit::Point,
        delta: egui::vec2(0.0, dy),
        modifiers: egui::Modifiers::NONE,
    };
    let step = paint(&mut row, &ctx, 0.3, vec![wheel(-48.0)]).0;
    assert_eq!(step.hover_source, Some(21));
    assert!(step.open_source.is_none());
    assert_eq!(
        row.selection(),
        held,
        "scroll explores without changing held contribution spans"
    );
    assert_eq!(paint(&mut row, &ctx, 0.4, vec![]).0.hover_source, Some(21));
    assert_eq!(ctx.input(|state| state.raw_scroll_delta), egui::Vec2::ZERO);
    for (step, expected) in [(1.0, 21), (2.0, 21), (3.0, 20)] {
        assert_eq!(
            paint(
                &mut row,
                &ctx,
                0.4 + step as f64 * 0.01,
                vec![egui::Event::PointerMoved(at + egui::vec2(step, 0.0))]
            )
            .0
            .hover_source,
            Some(expected),
            "small pointer events accumulate so physical capture position takes over from wheel stepping"
        );
    }
    paint(
        &mut row,
        &ctx,
        0.45,
        vec![
            egui::Event::PointerMoved(egui::pos2(at.x, bounds().bottom() + 20.0)),
            wheel(-48.0),
        ],
    );
    assert_ne!(
        ctx.input(|state| state.raw_scroll_delta),
        egui::Vec2::ZERO,
        "grace observes the pointer but never consumes neighboring scroll"
    );
}

#[test]
fn focus_loss_and_popup_close_require_new_pointer_motion_to_resume_exploring() {
    let ctx = egui::Context::default();
    let mut row = CaptureParticipation::default();
    let scene = paint(&mut row, &ctx, 0.0, vec![]).2;
    paint(&mut row, &ctx, 0.1, vec![]);
    let at = point(&scene, 20);
    assert_eq!(
        paint(&mut row, &ctx, 0.2, vec![egui::Event::PointerMoved(at)])
            .0
            .hover_source,
        Some(20)
    );
    assert_eq!(
        paint_focused(&mut row, &ctx, 0.3, vec![], false)
            .0
            .hover_source,
        None
    );
    assert_eq!(
        paint(&mut row, &ctx, 0.4, vec![]).0.hover_source,
        None,
        "reactivating a window must not restore a stale hover comparison"
    );
    let next = point(&scene, 21);
    assert_eq!(
        paint(&mut row, &ctx, 0.5, vec![egui::Event::PointerMoved(next)])
            .0
            .hover_source,
        Some(21)
    );
    egui::Popup::open_id(&ctx, egui::Id::new("hover-review-popup"));
    assert!(
        egui::Popup::is_any_open(&ctx),
        "fixture must actually block with an open popup"
    );
    assert_eq!(paint(&mut row, &ctx, 0.6, vec![]).0.hover_source, None);
    egui::Popup::close_all(&ctx);
    assert_eq!(
        paint(&mut row, &ctx, 0.7, vec![]).0.hover_source,
        None,
        "closing another control must not silently rearm exploration"
    );
    // Tiny motion accumulates from the suppression origin, not from the last
    // event: high-frequency mice must not require a sudden multi-pixel jump.
    for (step, expected) in [(1.0, None), (2.0, None), (3.0, Some(21))] {
        assert_eq!(
            paint(
                &mut row,
                &ctx,
                0.7 + step as f64 * 0.1,
                vec![egui::Event::PointerMoved(next + egui::vec2(step, 0.0))]
            )
            .0
            .hover_source,
            expected
        );
    }
}
