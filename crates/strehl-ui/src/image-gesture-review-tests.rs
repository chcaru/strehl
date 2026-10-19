//! Independent raw-pointer checks. Egui's own click/drag classification is
//! recorded as a witness, so the jitter fixture cannot quietly become a clean
//! synthetic double click that never exercised the reported failure.
use super::*;
use eframe::egui::{self, Id, Pos2, Rect, Sense};

#[derive(Default, Debug)]
struct Seen {
    reset: [bool; 2],
    pending: [bool; 2],
    dragged: [bool; 2],
    double: [bool; 2],
    button: bool,
}

struct Fixture {
    ctx: egui::Context,
}
impl Fixture {
    fn new() -> Self {
        let this = Self {
            ctx: egui::Context::default(),
        };
        this.frame(0.0, true, vec![]);
        this.frame(0.01, true, vec![]);
        this
    }
    fn frame(&self, time: f64, focused: bool, events: Vec<egui::Event>) -> Seen {
        self.viewport_frame(time, focused, focused, false, events)
    }
    fn viewport_frame(
        &self,
        time: f64,
        focused: bool,
        viewport_focused: bool,
        minimized: bool,
        events: Vec<egui::Event>,
    ) -> Seen {
        let mut seen = Seen::default();
        let mut raw = egui::RawInput {
            screen_rect: Some(Rect::from_min_max(Pos2::ZERO, egui::pos2(800.0, 300.0))),
            time: Some(time),
            focused,
            events,
            ..Default::default()
        };
        let viewport = raw.viewports.get_mut(&egui::ViewportId::ROOT).unwrap();
        viewport.focused = Some(viewport_focused);
        viewport.minimized = Some(minimized);
        let _ = self.ctx.run(raw, |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    for index in 0..2 {
                        let rect = Rect::from_min_size(
                            egui::pos2(20.0 + index as f32 * 320.0, 30.0),
                            egui::vec2(280.0, 220.0),
                        );
                        let hit = ui.interact(
                            rect,
                            Id::new(("independent-image", index)),
                            Sense::click_and_drag(),
                        );
                        let intent = reset(ui, &hit);
                        seen.reset[index] = intent.reset;
                        seen.pending[index] = intent.pending;
                        seen.dragged[index] = hit.dragged();
                        seen.double[index] = hit.double_clicked();
                    }
                    seen.button = ui
                        .put(
                            Rect::from_min_size(egui::pos2(670.0, 90.0), egui::vec2(110.0, 30.0)),
                            egui::Button::new("Non-image action"),
                        )
                        .clicked();
                });
        });
        seen
    }
    fn first_click(&self, point: Pos2) {
        let press = self.frame(0.10, true, pointer(point, true));
        assert!(!press.reset[0] && !press.pending[0]);
        let release = self.frame(0.14, true, pointer(point, false));
        assert!(!release.reset[0] && !release.pending[0]);
    }
}

fn button(point: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: point,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}
fn pointer(point: Pos2, pressed: bool) -> Vec<egui::Event> {
    vec![egui::Event::PointerMoved(point), button(point, pressed)]
}
fn moved(point: Pos2) -> Vec<egui::Event> {
    vec![egui::Event::PointerMoved(point)]
}
fn escape(pressed: bool) -> egui::Event {
    egui::Event::Key {
        key: egui::Key::Escape,
        physical_key: Some(egui::Key::Escape),
        pressed,
        repeat: false,
        modifiers: egui::Modifiers::NONE,
    }
}

#[test]
fn slow_double_click_with_real_egui_drag_jitter_resets_once_on_release() {
    let f = Fixture::new();
    let start = egui::pos2(90.0, 100.0);
    f.first_click(start);
    // 450ms after release: outside egui's default300ms, inside desktop policy.
    let pressed = f.frame(0.59, true, pointer(start, true));
    assert!(pressed.pending[0] && !pressed.reset[0]);
    let jitter = start + egui::vec2(8.0, 0.0);
    let motion = f.frame(0.62, true, moved(jitter));
    assert!(
        motion.dragged[0],
        "fixture must cross egui's6px drag threshold"
    );
    assert!(motion.pending[0] && !motion.reset[0]);
    let released = f.frame(0.64, true, pointer(jitter, false));
    assert!(released.reset[0] && !released.pending[0]);
    assert!(
        !released.double[0],
        "the legacy double_clicked path must miss this case"
    );
    let settled = f.frame(0.66, true, vec![]);
    assert!(!settled.reset[0] && !settled.pending[0]);
}

#[test]
fn genuine_second_drag_is_not_a_reset_even_if_it_returns_to_press_origin() {
    let f = Fixture::new();
    let start = egui::pos2(90.0, 100.0);
    f.first_click(start);
    assert!(f.frame(0.30, true, pointer(start, true)).pending[0]);
    let far = f.frame(0.32, true, moved(start + egui::vec2(18.0, 0.0)));
    assert!(far.dragged[0] && !far.pending[0] && !far.reset[0]);
    let returned = f.frame(0.34, true, moved(start));
    assert!(!returned.pending[0] && !returned.reset[0]);
    let released = f.frame(0.36, true, pointer(start, false));
    assert!(!released.reset[0] && !released.pending[0]);
    // A canceled second drag must not manufacture a fresh first click.
    assert!(!f.frame(0.40, true, pointer(start, true)).pending[0]);
    assert!(!f.frame(0.44, true, pointer(start, false)).reset[0]);
}

#[test]
fn clicks_on_different_images_do_not_share_global_egui_double_click_count() {
    let f = Fixture::new();
    let a = egui::pos2(90.0, 100.0);
    let b = egui::pos2(410.0, 100.0);
    f.first_click(a);
    let pressed = f.frame(0.22, true, pointer(b, true));
    assert!(!pressed.pending[1]);
    let released = f.frame(0.26, true, pointer(b, false));
    assert!(
        released.double[1],
        "egui's cross-widget click-count pitfall must occur"
    );
    assert!(!released.reset[0] && !released.reset[1]);
    assert!(!f.frame(0.32, true, pointer(a, true)).pending[0]);
    assert!(!f.frame(0.36, true, pointer(a, false)).reset[0]);
}

#[test]
fn unrelated_non_image_click_invalidates_the_older_image_click() {
    let f = Fixture::new();
    let a = egui::pos2(90.0, 100.0);
    let control = egui::pos2(725.0, 105.0);
    f.first_click(a);
    f.frame(0.22, true, pointer(control, true));
    assert!(f.frame(0.26, true, pointer(control, false)).button);
    let returned = f.frame(0.32, true, pointer(a, true));
    assert!(!returned.pending[0]);
    assert!(!f.frame(0.36, true, pointer(a, false)).reset[0]);
}

#[test]
fn distant_clicks_on_one_image_and_expired_clicks_are_not_resets() {
    for (delay, second) in [
        (0.30, egui::pos2(210.0, 100.0)),
        (0.80, egui::pos2(90.0, 100.0)),
    ] {
        let f = Fixture::new();
        f.first_click(egui::pos2(90.0, 100.0));
        assert!(!f.frame(delay, true, pointer(second, true)).pending[0]);
        assert!(!f.frame(delay + 0.04, true, pointer(second, false)).reset[0]);
    }
}

#[test]
fn an_initial_drag_or_long_hold_does_not_arm_a_reset() {
    for long_hold in [false, true] {
        let f = Fixture::new();
        let a = egui::pos2(90.0, 100.0);
        f.frame(0.10, true, pointer(a, true));
        let (at, release) = if long_hold {
            (a, 1.10)
        } else {
            let at = a + egui::vec2(24.0, 0.0);
            assert!(f.frame(0.13, true, moved(at)).dragged[0]);
            (at, 0.17)
        };
        assert!(!f.frame(release, true, pointer(at, false)).reset[0]);
        assert!(!f.frame(release + 0.15, true, pointer(at, true)).pending[0]);
        assert!(!f.frame(release + 0.19, true, pointer(at, false)).reset[0]);
    }
}

#[test]
fn escape_or_focus_loss_cancels_a_pending_reset_through_the_held_release() {
    for focus_loss in [false, true] {
        let f = Fixture::new();
        let at = egui::pos2(90.0, 100.0);
        f.first_click(at);
        assert!(f.frame(0.30, true, pointer(at, true)).pending[0]);
        let canceled = f.frame(
            0.32,
            !focus_loss,
            if focus_loss {
                vec![]
            } else {
                vec![escape(true)]
            },
        );
        assert!(!canceled.pending[0] && !canceled.reset[0]);
        let mut events = moved(at + egui::vec2(8.0, 0.0));
        if !focus_loss {
            events.push(escape(false));
        }
        let moved_after = f.frame(0.34, true, events);
        assert!(!moved_after.pending[0] && !moved_after.reset[0]);
        assert!(!f.frame(0.36, true, pointer(at, false)).reset[0]);
        assert!(!f.frame(0.40, true, pointer(at, true)).pending[0]);
        assert!(!f.frame(0.44, true, pointer(at, false)).reset[0]);
        assert!(f.frame(0.60, true, pointer(at, true)).pending[0]);
        assert!(f.frame(0.64, true, pointer(at, false)).reset[0]);
    }
}

#[test]
fn viewport_focus_or_minimize_cancels_even_when_application_focus_stays_true() {
    for minimized in [false, true] {
        let f = Fixture::new();
        let at = egui::pos2(90.0, 100.0);
        f.first_click(at);
        assert!(f.frame(0.30, true, pointer(at, true)).pending[0]);
        let canceled = f.viewport_frame(0.32, true, minimized, minimized, vec![]);
        assert!(!canceled.pending[0] && !canceled.reset[0]);
        assert!(!f.frame(0.36, true, pointer(at, false)).reset[0]);
        assert!(!f.frame(0.40, true, pointer(at, true)).pending[0]);
        assert!(!f.frame(0.44, true, pointer(at, false)).reset[0]);
        // Cancellation must not leave the image permanently unable to reset.
        assert!(f.frame(0.60, true, pointer(at, true)).pending[0]);
        assert!(f.frame(0.64, true, pointer(at, false)).reset[0]);
    }
}

#[test]
fn second_press_motion_and_release_in_one_paint_preserve_gesture_order() {
    for excursion in [8.0, 18.0] {
        let f = Fixture::new();
        let at = egui::pos2(90.0, 100.0);
        f.first_click(at);
        let out = f.frame(
            0.40,
            true,
            vec![
                egui::Event::PointerMoved(at),
                button(at, true),
                egui::Event::PointerMoved(at + egui::vec2(excursion, 0.0)),
                egui::Event::PointerMoved(at),
                button(at, false),
            ],
        );
        assert_eq!(out.reset[0], excursion < 12.0);
        assert!(!out.pending[0]);
    }
}
