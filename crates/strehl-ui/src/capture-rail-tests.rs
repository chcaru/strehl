use super::*;
use eframe::egui::{Event, Modifiers, PointerButton, RawInput};

fn samples() -> Vec<SurveySample> {
    (0..33)
        .map(|i| SurveySample {
            position: 37_000 + i * 25,
            scores: (0..24)
                .map(|t| Some(((i as f32 - 16.0).abs() * -0.05 + 1.0 + t as f32 * 0.001).max(0.0)))
                .collect(),
        })
        .collect()
}

fn inputs<'a>(samples: &'a [SurveySample], flight: Option<&'a FlightTicks>) -> RailInputs<'a> {
    RailInputs {
        samples,
        start: Some(37_100),
        end: Some(37_764),
        step: 7,
        lens: Some(37_556),
        flight,
        survey: Some("survey 21:30: where the subject is sharp".into()),
        can_use_survey: true,
        editable: true,
        keys: true,
    }
}

fn frame(
    ctx: &egui::Context,
    rail: &mut FocusRail,
    input: &RailInputs<'_>,
    time: f64,
    events: Vec<Event>,
) -> (egui::FullOutput, Vec<RailIntent>) {
    let mut intents = Vec::new();
    let raw = RawInput {
        screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 135.0))),
        time: Some(time),
        events,
        ..Default::default()
    };
    let palette = CapturePalette::default();
    let out = ctx.run(raw, |ctx| {
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| intents = rail.show(ui, input, &palette));
    });
    (out, intents)
}

fn key(key: Key, shift: bool) -> Event {
    Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Modifiers {
            shift,
            ..Modifiers::NONE
        },
    }
}

fn button(at: Pos2, pressed: bool) -> Event {
    Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Modifiers::NONE,
    }
}

#[test]
fn the_median_of_the_tiles_is_the_bar() {
    let s = SurveySample {
        position: 1,
        scores: vec![Some(3.0), None, Some(1.0), Some(2.0), Some(f32::NAN)],
    };
    assert_eq!(profile_value(&s), Some(2.0));
    let even = SurveySample {
        position: 1,
        scores: vec![Some(1.0), Some(4.0)],
    };
    assert_eq!(profile_value(&even), Some(2.5));
    assert_eq!(
        profile_value(&SurveySample {
            position: 1,
            scores: vec![None]
        }),
        None
    );
}

/// Left and Right move focus by 1, Shift by 16; S and E mark; nothing when
/// the rail does not have the keyboard or the camera is not editable.
#[test]
fn rail_keys_jog_and_mark() {
    let ctx = egui::Context::default();
    let s = samples();
    let mut rail = FocusRail::default();
    let input = inputs(&s, None);
    let (_, intents) = frame(
        &ctx,
        &mut rail,
        &input,
        0.0,
        vec![
            key(Key::ArrowLeft, false),
            key(Key::ArrowRight, true),
            key(Key::S, false),
            key(Key::E, false),
        ],
    );
    assert_eq!(
        intents,
        [
            RailIntent::Jog(-1),
            RailIntent::Jog(16),
            RailIntent::MarkStart,
            RailIntent::MarkEnd
        ]
    );
    let locked = RailInputs {
        editable: false,
        ..inputs(&s, None)
    };
    let (_, intents) = frame(
        &ctx,
        &mut rail,
        &locked,
        0.1,
        vec![key(Key::ArrowLeft, false)],
    );
    assert!(intents.is_empty());
    let elsewhere = RailInputs {
        keys: false,
        ..inputs(&s, None)
    };
    let (_, intents) = frame(&ctx, &mut rail, &elsewhere, 0.2, vec![key(Key::S, false)]);
    assert!(intents.is_empty());
}

/// Spec 5.2 and 5.4: pointer motion over the rail rebuilds no mesh; a
/// changed plan does.
#[test]
fn pointer_motion_rebuilds_nothing() {
    let ctx = egui::Context::default();
    let s = samples();
    let mut rail = FocusRail::default();
    let input = inputs(&s, None);
    frame(&ctx, &mut rail, &input, 0.0, vec![]);
    assert_eq!(rail.rebuilds, 1);
    for (i, x) in [200.0, 400.0, 600.0, 900.0, 1200.0].into_iter().enumerate() {
        frame(
            &ctx,
            &mut rail,
            &input,
            0.1 * (i + 1) as f64,
            vec![Event::PointerMoved(egui::pos2(x, 90.0))],
        );
    }
    assert_eq!(rail.rebuilds, 1, "hover is a separate shape");
    let moved_lens = RailInputs {
        lens: Some(37_300),
        ..inputs(&s, None)
    };
    frame(&ctx, &mut rail, &moved_lens, 1.0, vec![]);
    assert_eq!(
        rail.rebuilds, 1,
        "the lens is a separate shape in plan mode"
    );
    let new_step = RailInputs {
        step: 10,
        ..inputs(&s, None)
    };
    frame(&ctx, &mut rail, &new_step, 1.1, vec![]);
    assert_eq!(rail.rebuilds, 2);
}

/// At 6,000 planes the ticks are pooled to at most one per 2 px column.
#[test]
fn ticks_are_pooled_to_two_pixel_columns() {
    let positions: Vec<u16> = (0..6000).map(|i| 10_000 + i * 2).collect();
    let mut states = vec![TickState::Checked; 6000];
    states[3000] = TickState::Retaken;
    let width = 1292.0;
    let ticks = pooled(
        &positions,
        &states,
        (10_000, 22_000),
        (width / 2.0) as usize,
        tick_rank,
    );
    assert!(ticks.len() <= (width / 2.0) as usize + 1, "{}", ticks.len());
    assert!(
        ticks.iter().any(|t| t.1 == TickState::Retaken),
        "a retaken plane survives pooling"
    );
    let p = planned(37_100, 37_764, 7);
    assert_eq!(p.first(), Some(&37_100));
    assert_eq!(p.last(), Some(&37_764));
    assert_eq!(p.len(), 96, "the host's own plan: 664 units at step 7");
}

/// Dragging the End handle asks to move the bound there on release; a click
/// away from the handles moves the lens.
#[test]
fn dragging_a_handle_moves_the_bound() {
    let ctx = egui::Context::default();
    let s = samples();
    let mut rail = FocusRail::default();
    let input = inputs(&s, None);
    frame(&ctx, &mut rail, &input, 0.0, vec![]);
    let chart = Rect::from_min_max(egui::pos2(0.0, HEAD), egui::pos2(1332.0, 135.0));
    let axis = Axis::new(chart, domain(&input));
    let end = egui::pos2(axis.x(37_764), 90.0);
    let to = egui::pos2(axis.x(37_700), 90.0);
    let mut time = 0.1;
    let mut all = Vec::new();
    for events in [
        vec![Event::PointerMoved(end), button(end, true)],
        vec![Event::PointerMoved(end + egui::vec2(-10.0, 0.0))],
        vec![Event::PointerMoved(to)],
        vec![button(to, false)],
    ] {
        let (_, intents) = frame(&ctx, &mut rail, &input, time, events);
        all.extend(intents);
        time += 0.05;
    }
    assert_eq!(all.len(), 1, "{all:?}");
    match all[0] {
        RailIntent::MoveBound { start, to } => {
            assert!(!start);
            assert!(to.abs_diff(37_700) <= 2, "{to}");
        }
        other => panic!("{other:?}"),
    }
    let away = egui::pos2(axis.x(37_400), 90.0);
    let mut all = Vec::new();
    for events in [
        vec![Event::PointerMoved(away), button(away, true)],
        vec![button(away, false)],
    ] {
        let (_, intents) = frame(&ctx, &mut rail, &input, time, events);
        all.extend(intents);
        time += 0.05;
    }
    assert!(
        matches!(all.as_slice(), [RailIntent::Focus(p)] if p.abs_diff(37_400) <= 2),
        "{all:?}"
    );
}

/// In flight the ticks show the planes' states and the head its legend.
#[test]
fn flight_ticks_follow_the_planes() {
    let ctx = egui::Context::default();
    let s = samples();
    let flight = FlightTicks {
        positions: planned(37_100, 37_764, 7),
        states: (0..96)
            .map(|i| match i {
                38 => TickState::Retaken,
                0..=58 => TickState::Checked,
                59..=60 => TickState::OnHost,
                _ => TickState::ToCome,
            })
            .collect(),
        revision: 1,
    };
    let mut rail = FocusRail::default();
    let input = inputs(&s, Some(&flight));
    let (out, intents) = frame(&ctx, &mut rail, &input, 0.0, vec![key(Key::S, false)]);
    assert!(intents.is_empty(), "no marks or jogs in flight");
    let texts: Vec<String> = out
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            Shape::Text(t) => Some(t.galley.text().to_owned()),
            _ => None,
        })
        .collect();
    assert!(texts.iter().any(|t| t == "retaken"));
    assert!(!texts.iter().any(|t| t.contains("lens travel")));
    let mut more = flight.clone();
    more.states[61] = TickState::OnHost;
    more.revision = 2;
    let next = inputs(&s, Some(&more));
    frame(&ctx, &mut rail, &next, 0.1, vec![]);
    assert_eq!(rail.rebuilds, 2, "a plane's new state rebuilds once");
}
