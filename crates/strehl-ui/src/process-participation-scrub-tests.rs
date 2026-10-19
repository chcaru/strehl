//! An actual130-capture pointer sweep must visit unpictured captures, rather
//! than treating the handful of contact photographs as scrub stops.
use super::*;
use crate::pipeline::PipelineProgress;

const COUNT: usize = 130;
fn bounds() -> Rect {
    Rect::from_min_size(egui::pos2(20.0, 30.0), egui::vec2(1280.0, HEIGHT))
}
struct Scrub {
    ctx: egui::Context,
    row: CaptureParticipation,
    progress: PipelineProgress,
    selected: usize,
    time: f64,
}
impl Scrub {
    fn new(source: bool) -> Self {
        let mut progress = PipelineProgress::default();
        if !source {
            progress.mark_complete();
        }
        let mut row = CaptureParticipation::default();
        row.set_source_mode(source);
        Self {
            ctx: egui::Context::default(),
            row,
            progress,
            selected: 0,
            time: 0.0,
        }
    }
    fn paint(&mut self, events: Vec<egui::Event>) -> (ParticipationResponse, egui::FullOutput) {
        self.time += 0.02;
        let mut response = ParticipationResponse::default();
        let data = Input {
            epoch: 1,
            progress: &self.progress,
            frame_count: COUNT,
            selected: self.selected,
            inspected_pair: None,
            photos: &[],
            inspection_photos: &[],
            surfaces: &[],
            output: None,
            output_size: None,
        };
        let output = self.ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1320.0, 260.0))),
                time: Some(self.time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        response = self.row.show(
                            ui,
                            bounds(),
                            &data,
                            &self.progress.admission_archive,
                            0,
                            Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                        );
                    });
            },
        );
        if let Some(frame) = response.open_source {
            self.selected = frame;
        }
        (response, output)
    }
    fn warm(&mut self) -> egui::FullOutput {
        self.paint(vec![]);
        self.paint(vec![]).1
    }
}
fn axis(output: &egui::FullOutput) -> [Pos2; 2] {
    let label_y = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if ["Full image", "read"].contains(&text.galley.text()) => {
                Some(text.visual_bounding_rect().center().y)
            }
            _ => None,
        })
        .unwrap();
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && points[1].x - points[0].x > 1000.0
                    && (label_y + 1.0..label_y + 25.0).contains(&points[0].y) =>
            {
                Some(*points)
            }
            _ => None,
        })
        .unwrap()
}
fn cards(output: &egui::FullOutput) -> Vec<Rect> {
    let mut cards: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(card) if card.fill == BG && card.rect.height() > 45.0 => {
                Some(card.rect)
            }
            _ => None,
        })
        .collect();
    cards.sort_by(|a, b| a.left().total_cmp(&b.left()));
    cards
}
fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

#[test]
fn sparse_contact_hover_visits_all130_real_captures_on_the_same_continuous_axis() {
    let mut scene = Scrub::new(false);
    let output = scene.warm();
    let axis = axis(&output);
    let cards = cards(&output);
    assert!(
        cards.len() < COUNT / 4 && cards.len() > 2,
        "fixture must expose only sparse contacts"
    );
    let y = cards[0].center().y;
    let mut seen = Vec::new();
    for frame in 0..COUNT {
        let at = egui::pos2(
            egui::lerp(axis[0].x..=axis[1].x, frame as f32 / (COUNT - 1) as f32),
            y,
        );
        let response = scene.paint(vec![egui::Event::PointerMoved(at)]).0;
        assert_eq!(
            response.hover_source,
            Some(frame),
            "contact pixels must not snap the full axis at capture{frame}"
        );
        assert_eq!(response.open_source, None);
        seen.push(response.frame.unwrap());
    }
    assert_eq!(seen, (0..COUNT).collect::<Vec<_>>());
    assert!(scene.row.spans.is_empty() && scene.row.held.is_none());
    for (x, expected) in [
        (cards[0].left() + 0.5, 0),
        (cards.last().unwrap().right() - 0.5, COUNT - 1),
    ] {
        assert_eq!(
            scene
                .paint(vec![egui::Event::PointerMoved(egui::pos2(x, y))])
                .0
                .hover_source,
            Some(expected)
        );
    }
}

#[test]
fn source_and_final_contact_drags_cross_every_frame_and_reverse_without_anchor_stops() {
    for source in [true, false] {
        let mut scene = Scrub::new(source);
        let output = scene.warm();
        let axis = axis(&output);
        let y = cards(&output)[0].center().y;
        let at = |frame| {
            egui::pos2(
                egui::lerp(axis[0].x..=axis[1].x, frame as f32 / (COUNT - 1) as f32),
                y,
            )
        };
        assert!(scene.row.indices().len() < COUNT / 4);
        let initial = scene
            .paint(vec![egui::Event::PointerMoved(at(0)), button(at(0), true)])
            .0;
        assert_eq!(initial.open_source, Some(0));
        for frame in (1..COUNT).chain((0..COUNT - 1).rev()) {
            let response = scene.paint(vec![egui::Event::PointerMoved(at(frame))]).0;
            assert_eq!(
                response.open_source,
                Some(frame),
                "source={source}, capture{frame} must remain addressable during the held sweep"
            );
            assert_eq!(response.frame, Some(frame));
        }
        let ended = scene.paint(vec![button(at(0), false)]).0;
        assert_eq!(ended.frame, Some(0));
        assert_eq!(scene.selected, 0);
    }
}

#[test]
fn card_click_keeps_its_named_capture_while_hover_and_cursor_are_continuous() {
    let mut scene = Scrub::new(false);
    let output = scene.warm();
    let axis = axis(&output);
    let cards = cards(&output);
    let slot = cards.len() / 2;
    let named = scene.row.indices()[slot];
    let card = cards[slot];
    let edge = card.left_center() + egui::vec2(1.0, 0.0);
    let hover = scene.paint(vec![egui::Event::PointerMoved(edge)]).0;
    assert_ne!(
        hover.frame,
        Some(named),
        "edge fixture must separate continuous position from the pictured capture"
    );
    let named = hover.frame.unwrap();
    assert!(
        scene
            .row
            .contact_frames(scene.row.active_source)
            .contains(&named),
        "hover replaces the sparse card with the currently explored source"
    );
    scene.paint(vec![button(edge, true)]);
    let clicked = scene.paint(vec![button(edge, false)]).0;
    assert_eq!(clicked.open_source, Some(named));
    assert_eq!(clicked.frame, Some(named));
    assert_eq!(scene.row.held, Some(named));
    let x = egui::lerp(axis[0].x..=axis[1].x, 20.0 / (COUNT - 1) as f32) + 2.0;
    let (_, output) = scene.paint(vec![egui::Event::PointerMoved(egui::pos2(
        x,
        card.center().y,
    ))]);
    let cursor_x = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, stroke }
                if points[0].x == points[1].x
                    && stroke.color == ACCENT
                    && points[1].y - points[0].y > 120.0 =>
            {
                Some(points[0].x)
            }
            _ => None,
        })
        .expect("actual full-height scrub cursor");
    assert!(
        (cursor_x - x).abs() < 0.01,
        "the visual cursor follows the pointer, not discrete frame centers"
    );
}
