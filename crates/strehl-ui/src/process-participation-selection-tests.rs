use super::*;
use crate::pipeline::PipelineProgress;

#[test]
fn screenshot_ranges_wait_for_the_domain_and_reject_invalid_bounds_transactionally() {
    let mut row = CaptureParticipation::default();
    row.select_frame(7);
    let before = row.selection();
    assert_eq!(
        row.screenshot_ranges((3, 5), 67, &[[4, 12], [31, 35]]),
        Ok(false)
    );
    assert_eq!(row.selection(), before);
    row.domain = Some((3, 5));
    for invalid in [
        vec![],
        vec![[0, 0]; 9],
        vec![[12, 4]],
        vec![[4, 12], [65, 67]],
    ] {
        assert!(row.screenshot_ranges((3, 5), 67, &invalid).is_err());
        assert_eq!(
            row.selection(),
            before,
            "invalid preset must not partly apply"
        );
    }
    assert_eq!(
        row.screenshot_ranges((3, 5), 67, &[[4, 12], [31, 35]]),
        Ok(true)
    );
    assert_eq!(
        row.spans,
        [
            SelectionSpan {
                start: 4,
                end: 12,
                id: 0
            },
            SelectionSpan {
                start: 31,
                end: 35,
                id: 1
            },
        ]
    );
    assert_eq!(row.held, Some(35));
    assert_eq!(row.anchor, Some(31));
    assert_eq!(row.active_span, Some(1));
    assert!(row.hover_suppressed);
    let applied = row.selection();
    assert_eq!(row.screenshot_ranges((3, 6), 67, &[[0, 66]]), Ok(false));
    assert_eq!(
        row.selection(),
        applied,
        "later replay cannot use the old domain"
    );
}

fn frame_input(progress: &PipelineProgress, epoch: u64) -> Input<'_> {
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
fn viewport() -> Rect {
    Rect::from_min_size(egui::pos2(20.0, 30.0), egui::vec2(900.0, HEIGHT))
}
fn pointer(at: Pos2, pressed: bool, modifiers: egui::Modifiers) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers,
    }
}
struct Gesture {
    ctx: egui::Context,
    ribbon: CaptureParticipation,
    progress: PipelineProgress,
    time: f64,
    axis: [Pos2; 2],
}
impl Gesture {
    fn new() -> Self {
        let mut this = Self {
            ctx: Default::default(),
            ribbon: Default::default(),
            progress: Default::default(),
            time: 0.0,
            axis: [Pos2::ZERO; 2],
        };
        this.paint(egui::Modifiers::NONE, vec![], 1);
        this.paint(egui::Modifiers::NONE, vec![], 1);
        this
    }
    fn paint(
        &mut self,
        modifiers: egui::Modifiers,
        events: Vec<egui::Event>,
        epoch: u64,
    ) -> ParticipationResponse {
        self.time += 0.2;
        let mut response = ParticipationResponse::default();
        let output = self.ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(960.0, 240.0))),
                time: Some(self.time),
                modifiers,
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        response = self.ribbon.show(
                            ui,
                            viewport(),
                            &frame_input(&self.progress, epoch),
                            &self.progress.admission_archive,
                            0,
                            Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                        );
                    });
            },
        );
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
        self.axis = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::LineSegment { points, .. }
                    if points[0].y == points[1].y
                        && points[1].x - points[0].x > viewport().width() * 0.5
                        && (label_y + 1.0..label_y + 25.0).contains(&points[0].y) =>
                {
                    Some(*points)
                }
                _ => None,
            })
            .expect("actual painted capture evidence axis");
        response
    }
    fn at(&self, frame: usize) -> Pos2 {
        self.axis[0].lerp(self.axis[1], frame as f32 / 66.0) - egui::vec2(0.0, 4.0)
    }
    fn click(&mut self, frame: usize, modifiers: egui::Modifiers) -> ParticipationResponse {
        self.paint(
            modifiers,
            vec![
                egui::Event::PointerMoved(self.at(frame)),
                pointer(self.at(frame), true, modifiers),
            ],
            1,
        );
        self.paint(
            modifiers,
            vec![pointer(self.at(frame), false, modifiers)],
            1,
        )
    }
    fn drag(
        &mut self,
        from: usize,
        to: usize,
        modifiers: egui::Modifiers,
    ) -> ParticipationResponse {
        self.paint(
            modifiers,
            vec![
                egui::Event::PointerMoved(self.at(from)),
                pointer(self.at(from), true, modifiers),
            ],
            1,
        );
        self.paint(modifiers, vec![egui::Event::PointerMoved(self.at(to))], 1);
        self.paint(modifiers, vec![pointer(self.at(to), false, modifiers)], 1)
    }
    fn key(&mut self, key: egui::Key, modifiers: egui::Modifiers) -> ParticipationResponse {
        let events = [true, false]
            .map(|pressed| egui::Event::Key {
                key,
                physical_key: None,
                pressed,
                repeat: false,
                modifiers,
            })
            .into();
        self.paint(modifiers, events, 1)
    }
}
fn ranges(response: &ParticipationResponse) -> Vec<(usize, usize)> {
    response
        .spans
        .iter()
        .map(|span| (span.start, span.end))
        .collect()
}

#[test]
fn physical_shift_click_and_ctrl_drag_build_persistent_independent_spans() {
    let mut gesture = Gesture::new();
    gesture.click(4, egui::Modifiers::NONE);
    let extended = gesture.click(12, egui::Modifiers::SHIFT);
    assert_eq!(ranges(&extended), [(4, 12)]);
    let first_color = extended.spans[0].color();
    let added = gesture.drag(31, 35, egui::Modifiers::CTRL);
    assert_eq!(ranges(&added), [(4, 12), (31, 35)]);
    assert_ne!(added.spans[0].color(), added.spans[1].color());
    assert_eq!(added.spans[0].color(), first_color);
    assert_eq!(added.open_source, None);
    let left = gesture.paint(
        egui::Modifiers::NONE,
        vec![egui::Event::PointerMoved(egui::pos2(4.0, 200.0))],
        1,
    );
    assert_eq!(ranges(&left), [(4, 12), (31, 35)]);
    assert_eq!(left.frame, Some(35));
    let escaped = gesture.key(egui::Key::Escape, egui::Modifiers::NONE);
    assert!(escaped.spans.is_empty());
    assert!(escaped.frame.is_none());
}

#[test]
fn range_colour_survives_palette_churn_without_colliding_with_a_new_identity() {
    let mut gesture = Gesture::new();
    gesture.drag(4, 12, egui::Modifiers::SHIFT);
    let retained = gesture.ribbon.spans()[0];
    let mut saw_extended_palette = false;
    for _ in 0..20 {
        gesture.click(40, egui::Modifiers::CTRL);
        let spans = gesture.ribbon.spans();
        assert_eq!(spans.len(), 2);
        assert_eq!(spans[0], retained);
        assert_ne!(spans[1].id, retained.id);
        assert_ne!(
            spans[1].color(),
            retained.color(),
            "an unrelated new range must not reuse the colour of the retained range"
        );
        saw_extended_palette |= spans[1].id >= 8;
        gesture.click(40, egui::Modifiers::CTRL);
        assert_eq!(gesture.ribbon.spans(), [retained]);
    }
    assert!(
        saw_extended_palette,
        "the fixture must cross the old modulo-eight collision"
    );
    gesture.drag(31, 35, egui::Modifiers::CTRL);
    assert_eq!(gesture.ribbon.spans()[0], retained);
    assert_ne!(
        gesture.ribbon.spans()[1].color(),
        retained.color(),
        "Ctrl-drag must allocate through the same live-colour check"
    );
}

#[test]
fn more_than_eight_ranges_have_distinct_colours_and_subtraction_keeps_original_identity() {
    let mut gesture = Gesture::new();
    gesture.drag(0, 2, egui::Modifiers::SHIFT);
    let original = gesture.ribbon.spans()[0];
    for frame in (6..66).step_by(3) {
        gesture.click(frame, egui::Modifiers::CTRL);
    }
    let before = gesture.ribbon.spans().to_vec();
    assert!(
        before.len() > 16,
        "exercise more than both historical palette and bit-mask limits"
    );
    for (index, span) in before.iter().enumerate() {
        assert!(
            before[..index]
                .iter()
                .all(|other| other.id != span.id && other.color() != span.color()),
            "each active independent range must have its own identity and colour"
        );
        let color = span.color();
        assert!(
            color.r().max(color.g()).max(color.b()) >= 190 && color.a() == 255,
            "extended colours must remain bright enough for the dark interface"
        );
    }
    gesture.click(1, egui::Modifiers::CTRL);
    let after = gesture.ribbon.spans();
    let fragments: Vec<_> = after.iter().filter(|span| span.id == original.id).collect();
    assert_eq!(fragments.len(), 2);
    assert_eq!((fragments[0].start, fragments[0].end), (0, 0));
    assert_eq!((fragments[1].start, fragments[1].end), (2, 2));
    assert!(
        fragments
            .iter()
            .all(|span| span.color() == original.color())
    );
    assert_eq!(
        &after[2..],
        &before[1..],
        "subtracting one capture must not recolour any other range"
    );
}

#[test]
fn new_range_allocator_skips_live_colours_for_click_and_drag() {
    let mut gesture = Gesture::new();
    gesture.drag(4, 12, egui::Modifiers::SHIFT);
    let original = gesture.ribbon.spans()[0];
    // Force an allocator collision independently of the palette formula. This
    // fails if either creation path bypasses the active-colour check.
    gesture.ribbon.next_span = original.id;
    gesture.click(25, egui::Modifiers::CTRL);
    assert_ne!(gesture.ribbon.spans()[1].color(), original.color());
    let preserved = gesture.ribbon.spans().to_vec();
    gesture.ribbon.next_span = original.id;
    gesture.drag(31, 35, egui::Modifiers::CTRL);
    assert_eq!(&gesture.ribbon.spans()[..2], preserved);
    let added = gesture.ribbon.spans()[2];
    assert!(
        preserved
            .iter()
            .all(|span| span.id != added.id && span.color() != added.color())
    );
}

#[test]
fn ctrl_toggle_splits_without_fabricating_a_gap_or_changing_remaining_colour() {
    let mut gesture = Gesture::new();
    gesture.drag(4, 12, egui::Modifiers::SHIFT);
    let old_color = gesture.ribbon.spans[0].color();
    let cut = gesture.click(7, egui::Modifiers::CTRL);
    assert_eq!(ranges(&cut), [(4, 6), (8, 12)]);
    assert!(cut.spans.iter().all(|span| span.color() == old_color));
    assert!(cut.spans.iter().all(|span| !span.contains(7)));
    let extended = gesture.key(egui::Key::ArrowRight, egui::Modifiers::SHIFT);
    assert_eq!(ranges(&extended), [(4, 6), (8, 13)]);
    let added = gesture.click(50, egui::Modifiers::CTRL);
    assert!(added.spans.iter().any(|span| span.contains(50)));
    let removed = gesture.click(50, egui::Modifiers::CTRL);
    assert!(!removed.spans.iter().any(|span| span.contains(50)));
    assert_ne!(
        removed.frame,
        Some(50),
        "a removed capture must not immediately return as hover"
    );
}

#[test]
fn plain_source_scrub_click_and_space_preserve_ranges_but_new_bracket_clears() {
    for complete in [false, true] {
        let mut gesture = Gesture::new();
        if complete {
            gesture.progress.mark_complete();
        }
        gesture.drag(4, 12, egui::Modifiers::SHIFT);
        gesture.drag(31, 35, egui::Modifiers::CTRL);
        let before = gesture.ribbon.selection();
        assert!(gesture.ribbon.has_ranges());
        let scrub = gesture.drag(45, 60, egui::Modifiers::NONE);
        assert_eq!(scrub.spans, before.spans);
        assert_eq!(scrub.frame, Some(60));
        assert_eq!(gesture.ribbon.anchor, before.anchor);
        assert_eq!(gesture.ribbon.active_span, before.active_span);
        assert_eq!(gesture.ribbon.next_span, before.next_span);
        let peek = gesture.key(egui::Key::Space, egui::Modifiers::NONE);
        assert_eq!(peek.spans, before.spans);
        let compared = gesture.click(20, egui::Modifiers::NONE);
        assert_eq!(compared.spans, before.spans);
        assert_eq!(compared.frame, Some(20));
        assert_eq!(gesture.ribbon.anchor, before.anchor);
        assert_eq!(gesture.ribbon.active_span, before.active_span);
        // Explicit editing still starts from the saved range anchor31 rather
        // than the unrelated comparison source20.
        let extended = gesture.click(40, egui::Modifiers::SHIFT);
        assert_eq!(ranges(&extended), [(4, 12), (31, 40)]);
        assert_eq!(extended.spans[0].id, before.spans[0].id);
        assert_eq!(extended.spans[1].id, before.spans[1].id);
        let reimport = gesture.paint(egui::Modifiers::NONE, vec![], 2);
        assert!(reimport.spans.is_empty());
        assert!(gesture.ribbon.spans().is_empty());
    }
}

#[test]
fn shift_arrows_edit_the_range_while_plain_keys_only_move_the_comparison() {
    let mut gesture = Gesture::new();
    gesture.click(31, egui::Modifiers::NONE);
    assert_eq!(
        ranges(&gesture.key(egui::Key::ArrowRight, egui::Modifiers::SHIFT)),
        [(31, 32)]
    );
    assert_eq!(
        ranges(&gesture.key(egui::Key::ArrowLeft, egui::Modifiers::SHIFT)),
        [(31, 31)]
    );
    assert_eq!(
        ranges(&gesture.key(egui::Key::ArrowLeft, egui::Modifiers::SHIFT)),
        [(30, 31)]
    );
    assert_eq!(
        ranges(&gesture.key(egui::Key::ArrowRight, egui::Modifiers::NONE)),
        [(30, 31)]
    );
    assert_eq!(gesture.ribbon.held, Some(31));
    assert_eq!(gesture.ribbon.anchor, Some(31));
    for (key, frame) in [
        (egui::Key::Home, 0),
        (egui::Key::End, 66),
        (egui::Key::ArrowLeft, 65),
    ] {
        let compared = gesture.key(key, egui::Modifiers::NONE);
        assert_eq!(ranges(&compared), [(30, 31)]);
        assert_eq!(compared.frame, Some(frame));
        assert_eq!(gesture.ribbon.anchor, Some(31));
    }
    assert_eq!(
        ranges(&gesture.key(egui::Key::ArrowLeft, egui::Modifiers::SHIFT)),
        [(31, 64)],
        "explicit extension uses the original anchor and current comparison"
    );
}

#[test]
fn source_inspection_api_preserves_one_range_and_multiple_single_capture_groups() {
    for spans in [
        vec![SelectionSpan {
            start: 4,
            end: 12,
            id: 3,
        }],
        vec![
            SelectionSpan {
                start: 4,
                end: 4,
                id: 3,
            },
            SelectionSpan {
                start: 12,
                end: 12,
                id: 5,
            },
        ],
    ] {
        let mut row = CaptureParticipation {
            spans: spans.clone(),
            anchor: Some(4),
            active_span: Some(3),
            next_span: 6,
            ..Default::default()
        };
        row.select_frame(50);
        assert_eq!(row.spans, spans);
        assert_eq!(row.held, Some(50));
        assert_eq!(row.anchor, Some(4));
        assert_eq!(row.active_span, Some(3));
        assert_eq!(row.next_span, 6);
    }
    let mut single = CaptureParticipation::default();
    single.select_frame(4);
    assert!(!single.has_ranges());
    single.select_frame(50);
    assert_eq!((single.spans[0].start, single.spans[0].end), (50, 50));
}

#[test]
fn escape_during_plain_source_drag_clears_ranges_and_cancels_the_source_request() {
    let mut gesture = Gesture::new();
    gesture.progress.mark_complete();
    gesture.drag(4, 12, egui::Modifiers::SHIFT);
    gesture.paint(
        egui::Modifiers::NONE,
        vec![
            egui::Event::PointerMoved(gesture.at(45)),
            pointer(gesture.at(45), true, egui::Modifiers::NONE),
        ],
        1,
    );
    let dragged = gesture.paint(
        egui::Modifiers::NONE,
        vec![egui::Event::PointerMoved(gesture.at(60))],
        1,
    );
    assert_eq!(ranges(&dragged), [(4, 12)]);
    assert_eq!(dragged.open_source, Some(60));
    let escaped = gesture.key(egui::Key::Escape, egui::Modifiers::NONE);
    assert!(escaped.spans.is_empty());
    assert!(escaped.frame.is_none() && escaped.open_source.is_none());
    assert!(escaped.return_photo);
    let idle = gesture.paint(egui::Modifiers::NONE, vec![], 1);
    assert!(idle.spans.is_empty());
    assert!(idle.frame.is_none() && idle.open_source.is_none());
}

#[test]
fn escape_during_a_span_drag_clears_without_stationary_pointer_resurrection() {
    let mut gesture = Gesture::new();
    gesture.paint(
        egui::Modifiers::CTRL,
        vec![
            egui::Event::PointerMoved(gesture.at(10)),
            pointer(gesture.at(10), true, egui::Modifiers::CTRL),
        ],
        1,
    );
    let stretched = gesture.paint(
        egui::Modifiers::CTRL,
        vec![egui::Event::PointerMoved(gesture.at(25))],
        1,
    );
    assert_eq!(
        ranges(&stretched),
        [(10, 25)],
        "fixture must enter an active dragged span"
    );
    let escaped = gesture.key(egui::Key::Escape, egui::Modifiers::CTRL);
    assert!(escaped.spans.is_empty());
    assert!(escaped.frame.is_none());
    let idle = gesture.paint(egui::Modifiers::CTRL, vec![], 1);
    assert!(idle.spans.is_empty());
    assert!(
        idle.frame.is_none(),
        "a stationary pressed pointer must not undo Escape"
    );
}

#[test]
fn released_shift_chord_uses_the_pressed_event_modifiers_instead_of_the_final_frame_state() {
    let mut gesture = Gesture::new();
    gesture.click(2, egui::Modifiers::NONE);
    let response = gesture.paint(
        egui::Modifiers::NONE,
        vec![
            egui::Event::Key {
                key: egui::Key::ArrowRight,
                physical_key: None,
                pressed: true,
                repeat: false,
                modifiers: egui::Modifiers::SHIFT,
            },
            egui::Event::Key {
                key: egui::Key::ArrowRight,
                physical_key: None,
                pressed: false,
                repeat: false,
                modifiers: egui::Modifiers::NONE,
            },
        ],
        1,
    );
    assert_eq!(
        ranges(&response),
        [(2, 3)],
        "a Shift-arrow completed between paints must extend the held capture"
    );
    assert_eq!(response.frame, Some(3));
}

#[test]
fn released_shift_click_uses_pointer_event_modifiers_after_the_chord_has_ended() {
    let mut gesture = Gesture::new();
    gesture.click(2, egui::Modifiers::NONE);
    gesture.paint(
        egui::Modifiers::NONE,
        vec![
            egui::Event::PointerMoved(gesture.at(7)),
            pointer(gesture.at(7), true, egui::Modifiers::SHIFT),
        ],
        1,
    );
    let response = gesture.paint(
        egui::Modifiers::NONE,
        vec![pointer(gesture.at(7), false, egui::Modifiers::SHIFT)],
        1,
    );
    assert_eq!(
        ranges(&response),
        [(2, 7)],
        "Shift release after the pointer release in the same frame must not turn the span into a single capture"
    );
}
