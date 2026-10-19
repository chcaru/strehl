//! Independent pointer-level regressions for the final-photo area selector.
use super::*;

#[test]
fn control_wheel_resizes_hover_region_without_zooming_the_photograph() {
    let fixture = Fixture::new();
    let mut viewer = ResultPhoto::default();
    viewer.configure_probe(12, Some([450, 300]), None);
    let aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    let at = egui::pos2(400.0, 300.0);
    fixture.draw(&mut viewer, aperture, 0.0, egui::Modifiers::NONE, vec![]);
    fixture.draw(
        &mut viewer,
        aperture,
        0.1,
        egui::Modifiers::NONE,
        vec![egui::Event::PointerMoved(at)],
    );
    let before = viewer.probe_region.expect("a real hover region must exist");
    let control = egui::Modifiers {
        ctrl: true,
        command: true,
        ..Default::default()
    };
    let action = fixture.draw(
        &mut viewer,
        aperture,
        0.2,
        control,
        vec![egui::Event::MouseWheel {
            unit: egui::MouseWheelUnit::Point,
            delta: egui::vec2(0.0, 80.0),
            modifiers: control,
        }],
    );
    assert!(action.zoom.is_none() && action.view.is_none() && action.focus.is_none());
    let after = viewer
        .probe_region
        .expect("resizing must keep the visible probe");
    assert!(after.width() > before.width() * 1.1);
    let mut saw_tail = false;
    for step in 1..=5 {
        let action = fixture.draw(
            &mut viewer,
            aperture,
            0.2 + f64::from(step) * 0.016,
            egui::Modifiers::NONE,
            vec![],
        );
        saw_tail |= fixture
            .ctx
            .input(|state| (state.zoom_delta() - 1.0).abs() > 1e-6);
        assert!(
            action.zoom.is_none(),
            "consumed resize cannot leak a delayed zoom"
        );
    }
    assert!(
        saw_tail,
        "fixture must actually exercise egui's private smoothed zoom tail"
    );
    // The same input without Ctrl must still zoom the actual photograph.
    let action = fixture.draw(
        &mut viewer,
        aperture,
        0.3,
        egui::Modifiers::NONE,
        vec![egui::Event::MouseWheel {
            unit: egui::MouseWheelUnit::Point,
            delta: egui::vec2(0.0, 80.0),
            modifiers: egui::Modifiers::NONE,
        }],
    );
    assert!(action.zoom.is_some_and(|(factor, _)| factor > 1.0));
    let pinch = fixture.draw(
        &mut viewer,
        aperture,
        0.316,
        egui::Modifiers::NONE,
        vec![egui::Event::Zoom(1.2)],
    );
    assert!(
        pinch
            .zoom
            .is_some_and(|(factor, _)| (factor - 1.2).abs() < 1e-5),
        "a real pinch must survive while a consumed wheel tail is draining"
    );
}

#[test]
fn linked_timeline_region_uses_current_pointer_before_the_next_photo_paint() {
    let fixture = Fixture::new();
    let mut viewer = ResultPhoto::default();
    viewer.configure_probe(12, Some([450, 300]), None);
    let aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    fixture.draw(&mut viewer, aperture, 0.0, egui::Modifiers::NONE, vec![]);
    fixture.draw(
        &mut viewer,
        aperture,
        0.1,
        egui::Modifiers::NONE,
        vec![egui::Event::PointerMoved(egui::pos2(220.0, 250.0))],
    );
    let previous = viewer.probe_region.expect("actual prior painted region");
    let current = egui::pos2(580.0, 350.0);
    let mut measured = None;
    let _ = fixture.ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(800.0, 600.0))),
            time: Some(0.12),
            events: vec![egui::Event::PointerMoved(current)],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    measured = viewer.hover_region(ui, aperture);
                    assert_eq!(
                        viewer.probe_region,
                        Some(previous),
                        "no new photo painting has happened"
                    );
                    assert!(
                        viewer
                            .hover_region(
                                ui,
                                Rect::from_center_size(aperture.center(), aperture.size() * 0.5)
                            )
                            .is_none(),
                        "stale aperture certificate cannot be reused"
                    );
                });
        },
    );
    let actual = measured.expect("current pointer is eligible");
    assert_ne!(actual, previous);
    let expected_center = Pos2::ZERO + (current - fixture.image().min) / fixture.image().size();
    assert!(actual.center().distance(expected_center) < 1e-5);
}

struct Fixture {
    ctx: egui::Context,
    texture: TextureHandle,
    archive: AdmissionArchive,
}
impl Fixture {
    fn new() -> Self {
        let ctx = egui::Context::default();
        let texture = ctx.load_texture(
            "region-photo",
            egui::ColorImage::new([12, 8], vec![Color32::GRAY; 96]),
            egui::TextureOptions::LINEAR,
        );
        Self {
            ctx,
            texture,
            archive: AdmissionArchive::default(),
        }
    }
    fn draw(
        &self,
        viewer: &mut ResultPhoto,
        aperture: Rect,
        time: f64,
        modifiers: egui::Modifiers,
        events: Vec<egui::Event>,
    ) -> Action {
        let mut action = Action::default();
        let _ = self.ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(800.0, 600.0))),
                time: Some(time),
                modifiers,
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        action = viewer.show(
                            ui,
                            ui.max_rect(),
                            Context {
                                texture: &self.texture,
                                extent: egui::vec2(900.0, 600.0),
                                aperture,
                                pin: aperture.center(),
                                archive: &self.archive,
                                level: 0,
                                frame: None,
                                spans: &[],
                                linked_hover: false,
                            },
                        );
                    });
            },
        );
        action
    }
    fn image(&self) -> Rect {
        // Independently fixed3:2 photograph fitted in800×600.
        Rect::from_min_max(
            egui::pos2(0.0, 100.0 / 3.0),
            egui::pos2(800.0, 1700.0 / 3.0),
        )
    }
}
fn button(point: Pos2, pressed: bool, modifiers: egui::Modifiers) -> egui::Event {
    egui::Event::PointerButton {
        pos: point,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers,
    }
}
fn near(actual: Rect, expected: Rect) {
    assert!(actual.min.distance(expected.min) < 0.0001);
    assert!(actual.max.distance(expected.max) < 0.0001);
}
fn gesture(
    fixture: &Fixture,
    viewer: &mut ResultPhoto,
    aperture: Rect,
    modifiers: egui::Modifiers,
) -> Action {
    let image = fixture.image();
    let start = image.min + image.size() * egui::vec2(0.2, 0.25);
    let end = image.min + image.size() * egui::vec2(0.6, 0.75);
    let _ = fixture.draw(viewer, aperture, 0.0, modifiers, vec![]);
    let _ = fixture.draw(
        viewer,
        aperture,
        0.1,
        modifiers,
        vec![
            egui::Event::PointerMoved(start),
            button(start, true, modifiers),
        ],
    );
    let moving = fixture.draw(
        viewer,
        aperture,
        0.2,
        modifiers,
        vec![egui::Event::PointerMoved(end)],
    );
    assert!(
        moving.region.is_none(),
        "the linked aperture cannot jump until the rectangle is released"
    );
    fixture.draw(
        viewer,
        aperture,
        0.3,
        modifiers,
        vec![button(end, false, modifiers)],
    )
}

#[test]
fn fit_drag_selects_exact_region_then_linked_details_contain_the_whole_selection() {
    let fixture = Fixture::new();
    let mut viewer = ResultPhoto::default();
    let action = gesture(&fixture, &mut viewer, full(), egui::Modifiers::NONE);
    let selected = action
        .region
        .expect("dragging a fitted photo must select a region");
    near(
        selected,
        Rect::from_min_max(egui::pos2(0.2, 0.25), egui::pos2(0.6, 0.75)),
    );
    assert!(action.focus.is_none() && action.view.is_none() && action.zoom.is_none());
    let mut scales = crate::process_scales::ProcessScales::default();
    scales.focus_region(selected);
    assert!((scales.detail_zoom() - 2.0).abs() < 0.0001);
    assert!(scales.pin().distance(egui::pos2(0.4, 0.5)) < 0.0001);
}

#[test]
fn zoomed_drag_remains_pan_and_cannot_submit_a_region_on_release() {
    let fixture = Fixture::new();
    let mut viewer = ResultPhoto::default();
    let aperture = Rect::from_min_max(egui::pos2(0.25, 0.25), egui::pos2(0.75, 0.75));
    let start = fixture.image().center();
    let end = start + egui::vec2(80.0, 0.0);
    let none = egui::Modifiers::NONE;
    let _ = fixture.draw(&mut viewer, aperture, 0.0, none, vec![]);
    let _ = fixture.draw(
        &mut viewer,
        aperture,
        0.1,
        none,
        vec![egui::Event::PointerMoved(start), button(start, true, none)],
    );
    let moving = fixture.draw(
        &mut viewer,
        aperture,
        0.2,
        none,
        vec![egui::Event::PointerMoved(end)],
    );
    let (center, zoom) = moving
        .view
        .expect("zoomed photograph drag remains a natural grab");
    assert!(center.distance(egui::pos2(0.45, 0.5)) < 0.0001);
    assert_eq!(zoom, 2.0);
    assert!(moving.region.is_none());
    let released = fixture.draw(
        &mut viewer,
        aperture,
        0.3,
        none,
        vec![button(end, false, none)],
    );
    assert!(released.region.is_none() && released.focus.is_none());
}

#[test]
fn shift_drag_selects_within_existing_zoom_in_final_image_coordinates() {
    let fixture = Fixture::new();
    let aperture = Rect::from_min_max(egui::pos2(0.25, 0.25), egui::pos2(0.75, 0.75));
    let action = gesture(
        &fixture,
        &mut ResultPhoto::default(),
        aperture,
        egui::Modifiers {
            shift: true,
            ..Default::default()
        },
    );
    let selected = action
        .region
        .expect("Shift-drag chooses a subregion rather than moving the photo");
    near(
        selected,
        Rect::from_min_max(egui::pos2(0.35, 0.375), egui::pos2(0.55, 0.625)),
    );
    assert!(action.view.is_none() && action.focus.is_none());
}

#[test]
fn escape_cancels_pending_rectangle_and_release_does_not_resurrect_it() {
    let fixture = Fixture::new();
    let mut viewer = ResultPhoto::default();
    let start = fixture.image().min + egui::vec2(100.0, 100.0);
    let end = start + egui::vec2(160.0, 120.0);
    let none = egui::Modifiers::NONE;
    let _ = fixture.draw(&mut viewer, full(), 0.0, none, vec![]);
    let _ = fixture.draw(
        &mut viewer,
        full(),
        0.1,
        none,
        vec![egui::Event::PointerMoved(start), button(start, true, none)],
    );
    let _ = fixture.draw(
        &mut viewer,
        full(),
        0.2,
        none,
        vec![egui::Event::PointerMoved(end)],
    );
    let cancelled = fixture.draw(
        &mut viewer,
        full(),
        0.3,
        none,
        vec![egui::Event::Key {
            key: egui::Key::Escape,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: none,
        }],
    );
    assert!(viewer.region.is_none());
    assert!(cancelled.region.is_none() && cancelled.view.is_none());
    let released = fixture.draw(
        &mut viewer,
        full(),
        0.4,
        none,
        vec![button(end, false, none)],
    );
    assert!(released.region.is_none() && released.focus.is_none());
}

#[test]
fn selecting_a_rectangle_suppresses_scroll_zoom_until_release() {
    let fixture = Fixture::new();
    let mut viewer = ResultPhoto::default();
    let start = fixture.image().center();
    let none = egui::Modifiers::NONE;
    let _ = fixture.draw(&mut viewer, full(), 0.0, none, vec![]);
    let _ = fixture.draw(
        &mut viewer,
        full(),
        0.1,
        none,
        vec![egui::Event::PointerMoved(start), button(start, true, none)],
    );
    let moving = fixture.draw(
        &mut viewer,
        full(),
        0.2,
        none,
        vec![
            egui::Event::PointerMoved(start + egui::vec2(60.0, 50.0)),
            egui::Event::Zoom(1.5),
        ],
    );
    assert!(
        moving.zoom.is_none(),
        "aperture cannot change beneath the screen-space selection"
    );
}

#[test]
fn escape_after_a_press_or_tiny_movement_cannot_turn_release_into_click_focus() {
    for movement in [egui::Vec2::ZERO, egui::vec2(1.0, 1.0)] {
        let fixture = Fixture::new();
        let mut viewer = ResultPhoto::default();
        let start = fixture.image().center();
        let end = start + movement;
        let none = egui::Modifiers::NONE;
        let _ = fixture.draw(&mut viewer, full(), 0.0, none, vec![]);
        let _ = fixture.draw(
            &mut viewer,
            full(),
            0.1,
            none,
            vec![egui::Event::PointerMoved(start), button(start, true, none)],
        );
        let cancelled = fixture.draw(
            &mut viewer,
            full(),
            0.2,
            none,
            vec![
                egui::Event::PointerMoved(end),
                egui::Event::Key {
                    key: egui::Key::Escape,
                    physical_key: None,
                    pressed: true,
                    repeat: false,
                    modifiers: none,
                },
            ],
        );
        assert!(cancelled.region.is_none() && cancelled.focus.is_none());
        let released = fixture.draw(
            &mut viewer,
            full(),
            0.3,
            none,
            vec![button(end, false, none)],
        );
        assert!(
            released.region.is_none() && released.focus.is_none(),
            "Escape must suppress the click candidate too; movement {movement:?}"
        );

        // Cancellation consumes only this gesture; the next ordinary click works.
        let _ = fixture.draw(
            &mut viewer,
            full(),
            1.0,
            none,
            vec![button(start, true, none)],
        );
        let next = fixture.draw(
            &mut viewer,
            full(),
            1.1,
            none,
            vec![button(start, false, none)],
        );
        assert!(next.focus.is_some(), "Escape cannot leave the image inert");
    }
}

#[test]
fn jittering_second_click_resets_without_panning_or_committing_a_small_region() {
    for aperture in [
        full(),
        Rect::from_min_max(egui::pos2(0.25, 0.25), egui::pos2(0.75, 0.75)),
    ] {
        let fixture = Fixture::new();
        let mut viewer = ResultPhoto::default();
        let at = fixture.image().center();
        let jitter = at + egui::vec2(8.0, 8.0);
        let none = egui::Modifiers::NONE;
        let _ = fixture.draw(&mut viewer, aperture, 0.0, none, vec![]);
        let _ = fixture.draw(
            &mut viewer,
            aperture,
            0.1,
            none,
            vec![egui::Event::PointerMoved(at), button(at, true, none)],
        );
        let first = fixture.draw(
            &mut viewer,
            aperture,
            0.14,
            none,
            vec![button(at, false, none)],
        );
        assert!(
            first.focus.is_some(),
            "the image must receive a real first click"
        );
        let _ = fixture.draw(
            &mut viewer,
            aperture,
            0.59,
            none,
            vec![button(at, true, none)],
        );
        let moved = fixture.draw(
            &mut viewer,
            aperture,
            0.62,
            none,
            vec![egui::Event::PointerMoved(jitter)],
        );
        assert!(moved.view.is_none() && moved.region.is_none() && moved.focus.is_none());
        let release = fixture.draw(
            &mut viewer,
            aperture,
            0.64,
            none,
            vec![button(jitter, false, none)],
        );
        assert!(
            release.reset,
            "the release must fit even though egui classified the jitter as a drag"
        );
        assert!(
            release.view.is_none()
                && release.region.is_none()
                && release.focus.is_none()
                && release.zoom.is_none()
        );
    }
}
