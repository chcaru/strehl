//! Image reset recognizes a released pair on the same image, independently of
//! egui's shorter global click window and its six-point drag threshold.
use eframe::egui::{self, Context, Event, Id, PointerButton, Pos2, Response, Ui};

const DOUBLE_CLICK_SECONDS: f64 = 0.5;
const SLOP: f32 = 12.0;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct Gesture {
    /// A valid second release. Reset takes precedence over focus/pan on this frame.
    pub reset: bool,
    /// Keep the pan origin, but suppress applying movement while this is true.
    pub pending: bool,
}

#[derive(Clone, Copy)]
struct Released {
    time: f64,
    point: Pos2,
    serial: u64,
}

#[derive(Clone, Copy)]
struct Pressed {
    time: f64,
    point: Pos2,
    serial: u64,
    second: bool,
    moved: bool,
}

#[derive(Clone, Copy, Default)]
struct WidgetState {
    epoch: u64,
    frame: Option<u64>,
    release: Option<Released>,
    press: Option<Pressed>,
    gesture: Gesture,
}

#[derive(Clone, Copy, Default)]
struct PressSequence {
    epoch: u64,
    frame: Option<u64>,
    start: u64,
    end: u64,
}

fn sequence_id(ctx: &Context) -> Id {
    Id::new(("image-gesture-sequence", ctx.viewport_id()))
}

/// Invalidate all image click histories on an application domain/modal change.
/// Held buttons cannot establish a new history until a fresh press is seen.
pub(crate) fn clear(ctx: &Context) {
    let id = sequence_id(ctx);
    ctx.data_mut(|data| {
        let mut sequence = data.get_temp::<PressSequence>(id).unwrap_or_default();
        sequence.epoch = sequence.epoch.wrapping_add(1);
        data.insert_temp(id, sequence);
    });
}

fn sequence(ctx: &Context, frame: u64, events: &[Event]) -> PressSequence {
    let id = sequence_id(ctx);
    ctx.data_mut(|data| {
        let mut sequence = data.get_temp::<PressSequence>(id).unwrap_or_default();
        if sequence.frame != Some(frame) {
            sequence.frame = Some(frame);
            sequence.start = sequence.end;
            sequence.end = sequence.end.wrapping_add(
                events
                    .iter()
                    .filter(|event| {
                        matches!(
                            event,
                            Event::PointerButton {
                                button: PointerButton::Primary,
                                pressed: true,
                                ..
                            }
                        )
                    })
                    .count() as u64,
            );
            data.insert_temp(id, sequence);
        }
        sequence
    })
}

pub(crate) fn reset(ui: &Ui, response: &Response) -> Gesture {
    let ctx = ui.ctx();
    let frame = ctx.cumulative_frame_nr();
    let (now, focused, events) = ui.input(|input| {
        (
            input.time,
            input.focused
                && input.viewport().focused != Some(false)
                && input.viewport().minimized != Some(true),
            input.events.clone(),
        )
    });
    let canceled = !focused
        || ctx.memory(|memory| memory.top_modal_layer().is_some())
        || egui::Popup::is_any_open(ctx)
        || events.iter().any(|event| {
            matches!(
                event,
                Event::WindowFocused(false)
                    | Event::Key {
                        key: egui::Key::Escape,
                        pressed: true,
                        ..
                    }
            )
        });
    let id = response.id.with("image-reset-released-pair");
    if canceled {
        clear(ctx);
    }
    if canceled || !ui.is_enabled() || !response.enabled() {
        ctx.data_mut(|data| data.remove::<WidgetState>(id));
        return Gesture::default();
    }
    let sequence = sequence(ctx, frame, &events);
    let mut state = ctx.data_mut(|data| data.get_temp::<WidgetState>(id).unwrap_or_default());
    if state.epoch != sequence.epoch {
        state = WidgetState {
            epoch: sequence.epoch,
            ..Default::default()
        };
    }
    if state.frame == Some(frame) {
        return state.gesture;
    }
    state.frame = Some(frame);
    state.gesture = Gesture::default();
    let owns_press = response.is_pointer_button_down_on()
        || response.clicked_by(PointerButton::Primary)
        || response.drag_started_by(PointerButton::Primary)
        || response.drag_stopped_by(PointerButton::Primary)
        || response.contains_pointer();
    let mut serial = sequence.start;
    for event in events {
        match event {
            Event::PointerButton {
                pos,
                button: PointerButton::Primary,
                pressed: true,
                ..
            } => {
                serial = serial.wrapping_add(1);
                if owns_press && response.rect.contains(pos) {
                    let second = state.release.is_some_and(|released| {
                        serial == released.serial.wrapping_add(1)
                            && (0.0..=DOUBLE_CLICK_SECONDS).contains(&(now - released.time))
                            && pos.distance(released.point) <= SLOP
                    });
                    state.press = Some(Pressed {
                        time: now,
                        point: pos,
                        serial,
                        second,
                        moved: false,
                    });
                } else {
                    state.press = None;
                }
                state.release = None;
            }
            Event::PointerMoved(pos) => {
                if let Some(press) = state.press.as_mut() {
                    press.moved |= pos.distance(press.point) > SLOP;
                }
            }
            Event::PointerButton {
                pos,
                button: PointerButton::Primary,
                pressed: false,
                ..
            } => {
                if let Some(press) = state.press.take() {
                    let valid = !press.moved
                        && (0.0..=DOUBLE_CLICK_SECONDS).contains(&(now - press.time))
                        && pos.distance(press.point) <= SLOP
                        && response.rect.contains(pos);
                    if valid && press.second {
                        state.gesture.reset = true;
                        state.release = None;
                    } else if valid {
                        state.release = Some(Released {
                            time: now,
                            point: pos,
                            serial: press.serial,
                        });
                    } else {
                        state.release = None;
                    }
                }
            }
            Event::PointerGone => {
                state.press = None;
                state.release = None;
            }
            _ => {}
        }
    }
    state.gesture.pending = state.press.is_some_and(|press| {
        press.second && !press.moved && now - press.time <= DOUBLE_CLICK_SECONDS
    });
    let gesture = state.gesture;
    ctx.data_mut(|data| data.insert_temp(id, state));
    gesture
}

#[cfg(test)]
#[path = "image-gesture-review-tests.rs"]
mod review_tests;
