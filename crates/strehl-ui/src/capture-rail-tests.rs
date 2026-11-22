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

/// The jog buttons read "-128" ... "+128" with an ASCII minus (the UI face
/// draws U+2212 on the baseline), and no text on the rail uses U+2212.
#[test]
fn jog_labels_use_an_ascii_minus() {
    let ctx = egui::Context::default();
    let s = samples();
    let mut rail = FocusRail::default();
    let (out, _) = frame(&ctx, &mut rail, &inputs(&s, None), 0.0, vec![]);
    let texts: Vec<String> = out
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            Shape::Text(t) => Some(t.galley.text().to_owned()),
            _ => None,
        })
        .collect();
    for want in ["-128", "-16", "-1", "+1", "+16", "+128"] {
        assert!(texts.iter().any(|t| t == want), "{want}: {texts:?}");
    }
    assert!(!texts.iter().any(|t| t.contains('\u{2212}')), "{texts:?}");
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
    let view = RailView::of((10_000, 22_000));
    let ticks = pooled(
        positions.iter().copied().zip(states.iter().copied()),
        view,
        2.0 * view.span / width,
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
    let axis = Axis::new(chart, RailView::of(domain(&input)));
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

// ----- the rail's scale ----------------------------------------------------

const CHART: Rect = Rect {
    min: Pos2 { x: 0.0, y: HEAD },
    max: Pos2 {
        x: 1332.0,
        y: 135.0,
    },
};

fn wheel(notches: f32, shift: bool) -> Event {
    Event::MouseWheel {
        unit: MouseWheelUnit::Line,
        delta: egui::vec2(0.0, notches),
        modifiers: Modifiers {
            shift,
            ..Modifiers::NONE
        },
    }
}

/// Frames at 60 Hz from `time` until the view stops moving (at most a
/// second); returns the frames it took.
fn settle(
    ctx: &egui::Context,
    rail: &mut FocusRail,
    input: &RailInputs<'_>,
    time: &mut f64,
) -> usize {
    for n in 0..60 {
        let before = rail.view();
        *time += 1.0 / 60.0;
        frame(ctx, rail, input, *time, vec![]);
        if rail.view() == before {
            return n;
        }
    }
    panic!("the view did not settle: {:?}", rail.view());
}

fn texts(out: &egui::FullOutput) -> Vec<String> {
    out.shapes
        .iter()
        .filter_map(|s| match &s.shape {
            Shape::Text(t) => Some(t.galley.text().to_owned()),
            _ => None,
        })
        .collect()
}

/// The view's arithmetic: inside the travel, no finer than `MIN_SPAN`, the
/// anchor held by a zoom, a notch of the wheel a factor of √2.
#[test]
fn the_view_stays_inside_the_lens_travel() {
    let v = RailView::around(10.0, 0.5, 1000.0);
    assert_eq!(v.lo, 0.0, "clamped at the near end");
    let v = RailView::around(65_500.0, 0.5, 1000.0);
    assert_eq!(v.hi(), TRAVEL, "clamped at the far end");
    assert_eq!(RailView::around(30_000.0, 0.5, 1e9).span, TRAVEL);
    let fine = RailView {
        lo: 100.0,
        span: 4.0,
    }
    .clamped();
    assert_eq!(fine.span, MIN_SPAN);
    assert!(
        (fine.at(0.5) - 102.0).abs() < 1e-9,
        "widened about its centre"
    );
    let shown = RailView {
        lo: 37_000.0,
        span: 800.0,
    };
    let z = wheel_zoom(shown, shown, 1.0, 0.25);
    assert!((z.span - 800.0 / NOTCH).abs() < 1e-9);
    assert!(
        (z.at(0.25) - shown.at(0.25)).abs() < 1e-9,
        "the pointer's position stays"
    );
    let z = wheel_zoom(shown, shown, -2.0, 0.25);
    assert!((z.span - 1600.0).abs() < 1e-9, "two notches back double it");
    // Mid-ease the position under the pointer is the drawn one's.
    let target = RailView {
        lo: 37_100.0,
        span: 400.0,
    };
    let z = wheel_zoom(shown, target, 1.0, 0.75);
    assert!((z.at(0.75) - shown.at(0.75)).abs() < 1e-9);
    assert!((z.span - 400.0 / NOTCH).abs() < 1e-9);
}

/// Easing moves on a log scale with the anchor still, monotonically, and
/// lands exactly on the goal.
#[test]
fn easing_holds_the_anchor_and_lands_on_the_goal() {
    let from = RailView {
        lo: 37_000.0,
        span: 800.0,
    };
    let goal = RailView::around(from.at(0.3), 0.3, 100.0);
    let spans: Vec<f64> = (0..=20)
        .map(|i| {
            let v = between(from, goal, 0.3, ease_out(f64::from(i) / 20.0));
            assert!((v.at(0.3) - from.at(0.3)).abs() < 1e-6, "{v:?}");
            v.span
        })
        .collect();
    assert_eq!(between(from, goal, 0.3, ease_out(1.0)), goal);
    let start = between(from, goal, 0.3, 0.0);
    assert!((start.lo - from.lo).abs() < 1e-9 && (start.span - from.span).abs() < 1e-9);
    assert!(
        spans.windows(2).all(|w| w[1] < w[0]),
        "monotonic: {spans:?}"
    );
    // Ease-out: most of the way early.
    assert!(ease_out(0.25) > 0.5 && ease_out(0.5) > 0.85);
}

/// Clicks land on the resolution the scale shows: 1, 2, 5 ... units.
#[test]
fn the_scale_sets_the_resolution_of_a_click() {
    assert_eq!(quantum(0.03), 1);
    assert_eq!(quantum(0.74), 1);
    assert_eq!(quantum(1.2), 2);
    assert_eq!(quantum(3.3), 5);
    assert_eq!(quantum(50.7), 100);
    assert_eq!(snap(37_556.4, 1), 37_556);
    assert_eq!(snap(37_556.4, 50), 37_550);
    assert_eq!(snap(65_534.0, 100), 65_500);
    assert_eq!(snap(65_560.0, 100), 65_535, "within the travel");
    assert_eq!(snap(-30.0, 100), 0);
    // Labels about every 110 px, re-picked at every scale.
    assert_eq!(label_spacing(960.0, 1292.0), 100);
    assert_eq!(label_spacing(64.0, 1292.0), 10);
    assert_eq!(label_spacing(32.0, 1292.0), 5);
    assert_eq!(label_spacing(TRAVEL, 1292.0), 10_000);
    // Minor ticks at least 9 px apart, dividing the major step.
    assert_eq!(minor_spacing(20, 0.093), 1, "single units zoomed in");
    assert_eq!(minor_spacing(100, 0.83), 10);
    assert_eq!(minor_spacing(10_000, 50.7), 500);
    assert_eq!(minor_spacing(5, 0.5), 5, "no minor ticks");
    assert_eq!(minor_spacing(20, 0.5), 5);

    let ctx = egui::Context::default();
    let s = samples();
    let input = inputs(&s, None);
    let mut time = 0.0;
    // Points between units, away from the handles and the lens.
    for (view, q, point) in [
        (
            RailView {
                lo: 0.0,
                span: TRAVEL,
            },
            100u16,
            20_041.37,
        ),
        (
            RailView {
                lo: 37_380.0,
                span: 64.0,
            },
            1,
            37_401.37,
        ),
    ] {
        let mut rail = FocusRail::default();
        rail.set_view(Some(view));
        frame(&ctx, &mut rail, &input, time, vec![]);
        let axis = Axis::new(CHART, rail.view().unwrap());
        assert_eq!(rail.view(), Some(view));
        assert_eq!(quantum(axis.units_per_px()), q);
        let x = axis.xf(point);
        let at = egui::pos2(x, 90.0);
        let mut all = Vec::new();
        for events in [
            vec![Event::PointerMoved(at), button(at, true)],
            vec![button(at, false)],
        ] {
            time += 0.05;
            all.extend(frame(&ctx, &mut rail, &input, time, events).1);
        }
        let want = snap(point, q);
        assert_eq!(all, [RailIntent::Focus(want)], "at {q} units a step");
        time += 1.0;
    }
}

/// The wheel over the rail zooms around the pointer, eased; the slider's
/// readout follows; Shift and the wheel pan; Fit returns to the bounds.
#[test]
fn the_wheel_zooms_around_the_pointer_and_fit_returns() {
    let ctx = egui::Context::default();
    let s = samples();
    let input = inputs(&s, None);
    let mut rail = FocusRail::default();
    let mut time = 0.0;
    frame(&ctx, &mut rail, &input, time, vec![]);
    let fit = rail.view().unwrap();
    assert_eq!(fit, RailView::of(domain(&input)));
    let axis = Axis::new(CHART, fit);
    let x = axis.xf(37_300.0);
    let at = egui::pos2(x, 100.0);
    time += 1.0 / 60.0;
    frame(
        &ctx,
        &mut rail,
        &input,
        time,
        vec![Event::PointerMoved(at), wheel(2.0, false)],
    );
    let frames = settle(&ctx, &mut rail, &input, &mut time);
    assert!((2..=20).contains(&frames), "eased over {frames} frames");
    let zoomed = rail.view().unwrap();
    assert!((zoomed.span - fit.span / 2.0).abs() < 1e-6, "{zoomed:?}");
    let under = Axis::new(CHART, zoomed).fraction(x);
    assert!(
        (zoomed.at(under) - 37_300.0).abs() < 0.5,
        "the position under the pointer stayed: {}",
        zoomed.at(under)
    );
    time += 1.0 / 60.0;
    let (out, _) = frame(&ctx, &mut rail, &input, time, vec![]);
    let readout = format!(
        "{} units · 0.37/px",
        style::focus_units(zoomed.span.round() as u16)
    );
    assert!(
        texts(&out).contains(&readout),
        "{readout}: {:?}",
        texts(&out)
    );
    // Shift and the wheel pan by a share of the span, towards Near.
    time += 1.0 / 60.0;
    frame(
        &ctx,
        &mut rail,
        &input,
        time,
        vec![Event::PointerMoved(at), wheel(1.0, true)],
    );
    settle(&ctx, &mut rail, &input, &mut time);
    let panned = rail.view().unwrap();
    assert!((panned.span - zoomed.span).abs() < 1e-9);
    assert!((panned.lo - (zoomed.lo - PAN_NOTCH * zoomed.span)).abs() < 1e-6);
    // Fit, in the head.
    let out = frame(&ctx, &mut rail, &input, time + 0.01, vec![]).0;
    let fit_link = out
        .shapes
        .iter()
        .find_map(|s| match &s.shape {
            Shape::Text(t) if t.galley.text() == "FIT" => Some(t.visual_bounding_rect()),
            _ => None,
        })
        .expect("Fit in the head");
    time += 0.02;
    let c = fit_link.center();
    for events in [
        vec![Event::PointerMoved(c), button(c, true)],
        vec![button(c, false)],
    ] {
        time += 1.0 / 60.0;
        frame(&ctx, &mut rail, &input, time, events);
    }
    settle(&ctx, &mut rail, &input, &mut time);
    assert_eq!(rail.view(), Some(fit));
}

/// A drag on the empty rail pans the view with the pointer; it asks the
/// camera for nothing.
#[test]
fn dragging_the_empty_rail_pans() {
    let ctx = egui::Context::default();
    let s = samples();
    let input = inputs(&s, None);
    let mut rail = FocusRail::default();
    let zoomed = RailView {
        lo: 37_200.0,
        span: 200.0,
    };
    rail.set_view(Some(zoomed));
    let mut time = 0.0;
    frame(&ctx, &mut rail, &input, time, vec![]);
    let axis = Axis::new(CHART, zoomed);
    let from = egui::pos2(axis.xf(37_250.0), 100.0);
    let to = from + egui::vec2(-323.0, 0.0);
    let mut all = Vec::new();
    for events in [
        vec![Event::PointerMoved(from), button(from, true)],
        vec![Event::PointerMoved(from + egui::vec2(-20.0, 0.0))],
        vec![Event::PointerMoved(to)],
        vec![button(to, false)],
    ] {
        time += 1.0 / 60.0;
        all.extend(frame(&ctx, &mut rail, &input, time, events).1);
    }
    assert!(all.is_empty(), "{all:?}");
    let v = rail.view().unwrap();
    let moved = 323.0 * zoomed.span / f64::from(axis.width);
    assert!((v.lo - (zoomed.lo + moved)).abs() < 0.01, "{v:?}");
    assert_eq!(v.span, zoomed.span);
}

/// The lens can be dragged: the focus is asked for on release, at the
/// scale's resolution.
#[test]
fn dragging_the_lens_focuses_there_on_release() {
    let ctx = egui::Context::default();
    let s = samples();
    let input = inputs(&s, None);
    let mut rail = FocusRail::default();
    let view = RailView {
        lo: 37_500.0,
        span: 100.0,
    };
    rail.set_view(Some(view));
    let mut time = 0.0;
    frame(&ctx, &mut rail, &input, time, vec![]);
    let axis = Axis::new(CHART, view);
    let lens = egui::pos2(axis.x(37_556), 120.0);
    let to = egui::pos2(axis.xf(37_531.2), 120.0);
    let mut all = Vec::new();
    for events in [
        vec![Event::PointerMoved(lens), button(lens, true)],
        vec![Event::PointerMoved(lens + egui::vec2(-12.0, 0.0))],
        vec![Event::PointerMoved(to)],
        vec![button(to, false)],
    ] {
        time += 1.0 / 60.0;
        all.extend(frame(&ctx, &mut rail, &input, time, events).1);
    }
    assert_eq!(all, [RailIntent::Focus(37_531)]);
}

/// A lens moved out of a zoomed view brings the view along; one inside it
/// leaves the view alone, and so does the fit.
#[test]
fn a_lens_leaving_the_view_brings_it_along() {
    let ctx = egui::Context::default();
    let s = samples();
    let mut rail = FocusRail::default();
    let view = RailView {
        lo: 37_500.0,
        span: 100.0,
    };
    rail.set_view(Some(view));
    let mut time = 0.0;
    frame(&ctx, &mut rail, &inputs(&s, None), time, vec![]);
    let inside = RailInputs {
        lens: Some(37_560),
        ..inputs(&s, None)
    };
    time += 0.1;
    frame(&ctx, &mut rail, &inside, time, vec![]);
    settle(&ctx, &mut rail, &inside, &mut time);
    assert_eq!(rail.view(), Some(view));
    let stepped = RailInputs {
        lens: Some(37_616),
        ..inputs(&s, None)
    };
    frame(&ctx, &mut rail, &stepped, time, vec![]);
    settle(&ctx, &mut rail, &stepped, &mut time);
    let v = rail.view().unwrap();
    assert!((v.fraction(37_616.0) - 0.92).abs() < 1e-6, "{v:?}");
    assert_eq!(v.span, view.span);
    let far = RailInputs {
        lens: Some(40_000),
        ..inputs(&s, None)
    };
    frame(&ctx, &mut rail, &far, time, vec![]);
    settle(&ctx, &mut rail, &far, &mut time);
    let v = rail.view().unwrap();
    assert!((v.fraction(40_000.0) - 0.5).abs() < 1e-6, "centred: {v:?}");
}

/// Zoomed, pointer motion still rebuilds nothing; a change of scale
/// rebuilds, and the bars and ticks re-bin to it.
#[test]
fn a_zoomed_rail_rebuilds_on_scale_not_on_motion() {
    let ctx = egui::Context::default();
    let s = samples();
    let input = inputs(&s, None);
    let mut rail = FocusRail::default();
    rail.set_view(Some(RailView {
        lo: 37_300.0,
        span: 120.0,
    }));
    frame(&ctx, &mut rail, &input, 0.0, vec![]);
    let built = rail.rebuilds;
    for (i, x) in [200.0, 500.0, 800.0, 1100.0].into_iter().enumerate() {
        frame(
            &ctx,
            &mut rail,
            &input,
            0.1 * (i + 1) as f64,
            vec![Event::PointerMoved(egui::pos2(x, 90.0))],
        );
    }
    assert_eq!(rail.rebuilds, built, "hover is a separate shape");
    let mesh_of = |rail: &FocusRail| rail.cache.as_ref().unwrap().1.clone();
    let fine = mesh_of(&rail);
    rail.set_view(Some(RailView {
        lo: 0.0,
        span: TRAVEL,
    }));
    frame(&ctx, &mut rail, &input, 1.0, vec![]);
    assert_eq!(rail.rebuilds, built + 1);
    let coarse = mesh_of(&rail);
    // Zoomed in, each plane in view is a bar (120 units at step 7, 0.09
    // units a pixel); zoomed out the whole survey is a few 3 px bars.
    let bars = |mesh: &Mesh, color: Color32| {
        mesh.vertices
            .chunks(4)
            .filter(|q| q[0].color == color)
            .count()
    };
    let green = CapturePalette::default().ok.gamma_multiply(0.6);
    let fine_bars = bars(&fine, green);
    assert!(
        (17..=20).contains(&fine_bars),
        "one bar a plane: {fine_bars}"
    );
    let coarse_bars = bars(&coarse, green);
    assert!((2..=7).contains(&coarse_bars), "{coarse_bars}");
}

/// A coarse bar keeps the highest point of the range it stands for.
#[test]
fn coarse_bars_keep_the_peaks() {
    let profile = [(100u16, 0.2f32), (110, 0.9), (120, 0.1)];
    assert_eq!(profile_max(&profile, 95.0, 125.0), 0.9);
    assert!((profile_max(&profile, 101.0, 104.0) - 0.48).abs() < 1e-6);
    assert_eq!(
        profile_max(&profile, 130.0, 200.0),
        0.0,
        "outside the survey"
    );
    // Columns are anchored to focus units: panning keeps a plane's column.
    let a = pooled(
        [(1000u16, 0u8), (1001, 1), (1003, 0)],
        RailView {
            lo: 900.0,
            span: 300.0,
        },
        2.0,
        |s| s,
    );
    let b = pooled(
        [(1000u16, 0u8), (1001, 1), (1003, 0)],
        RailView {
            lo: 901.3,
            span: 300.0,
        },
        2.0,
        |s| s,
    );
    assert_eq!(a, b);
    assert_eq!(a, [(1000, 1), (1003, 0)]);
}

/// The rail's CPU per frame (paint and tessellation) on a hover sweep and
/// while the wheel zooms every frame (a mesh rebuild a frame), at a 664-unit
/// plan of step 1 (665 planned ticks):
/// `cargo test --release --locked -p strehl-ui rail_zoom_cost -- --ignored --nocapture`.
#[test]
#[ignore = "benchmark: prints ms per frame"]
fn rail_zoom_cost() {
    let ctx = egui::Context::default();
    let s = samples();
    let input = RailInputs {
        step: 1,
        ..inputs(&s, None)
    };
    let run = |zoom: bool| {
        let mut rail = FocusRail::default();
        let mut time = 0.0;
        frame(&ctx, &mut rail, &input, time, vec![]);
        let steps = 240;
        let started = std::time::Instant::now();
        for i in 0..steps {
            time += 1.0 / 60.0;
            let at = egui::pos2(40.0 + (i % 120) as f32 * 10.0, 90.0);
            let mut events = vec![Event::PointerMoved(at)];
            if zoom {
                // In for two seconds, out for two.
                events.push(wheel(if i < steps / 2 { 0.25 } else { -0.25 }, false));
            }
            let (out, _) = frame(&ctx, &mut rail, &input, time, events);
            std::hint::black_box(ctx.tessellate(out.shapes, out.pixels_per_point));
        }
        let ms = started.elapsed().as_secs_f64() * 1000.0 / f64::from(steps);
        (ms, rail.rebuilds)
    };
    for _ in 0..3 {
        let (hover, hover_builds) = run(false);
        let (zoom, zoom_builds) = run(true);
        println!(
            "rail_cpu_ms_per_frame hover {hover:.4} ({hover_builds} builds), \
             zooming {zoom:.4} ({zoom_builds} builds)"
        );
    }
}

// ----- the rail in flight --------------------------------------------------

/// A stack in flight: planes 37,100-37,764, 61 checked.
fn flight_ticks() -> FlightTicks {
    FlightTicks {
        positions: planned(37_100, 37_764, 7),
        states: (0..96)
            .map(|i| {
                if i < 61 {
                    TickState::Checked
                } else {
                    TickState::ToCome
                }
            })
            .collect(),
        revision: 1,
    }
}

/// In flight the rail fits the stack being captured: neither a wider survey
/// nor the lens (which goes below a plane to retake it) moves the fit.
#[test]
fn in_flight_the_fit_is_the_stack() {
    let wide: Vec<SurveySample> = (0..40)
        .map(|i| SurveySample {
            position: 30_000 + i * 400,
            scores: vec![Some(0.5); 24],
        })
        .collect();
    let flight = flight_ticks();
    let mut input = inputs(&wide, Some(&flight));
    let (lo, hi) = domain(&input);
    assert_eq!((lo, hi), (37_100 - 66, 37_764 + 66));
    input.lens = Some(36_900);
    assert_eq!(domain(&input), (lo, hi), "a retake's approach");
    // Planning, the survey and the lens count.
    let plan = inputs(&wide, None);
    assert_eq!(domain(&plan).0, 30_000 - 1_560);
}

/// A view zoomed while planning is let go when the capture starts: the
/// rail fits the stack and stays fitted as planes are taken; a wheel in
/// flight holds the user's view until Fit.
#[test]
fn a_capture_starts_fitted_and_fit_restores_following() {
    let ctx = egui::Context::default();
    let s = samples();
    let mut rail = FocusRail::default();
    let mut time = 0.0;
    let plan = inputs(&s, None);
    frame(&ctx, &mut rail, &plan, time, vec![]);
    rail.set_view(Some(RailView::of((37_500, 37_620))));
    frame(&ctx, &mut rail, &plan, time + 0.01, vec![]);
    assert_eq!(rail.view(), Some(RailView::of((37_500, 37_620))));
    // The capture starts.
    let flight = flight_ticks();
    let input = inputs(&s, Some(&flight));
    let fitted = RailView::of(domain(&input));
    settle(&ctx, &mut rail, &input, &mut time);
    assert_eq!(rail.view(), Some(fitted));
    // Planes are taken and the lens moves on: still fitted.
    let mut more = flight.clone();
    more.states[61] = TickState::Checked;
    more.revision = 2;
    let mut next = inputs(&s, Some(&more));
    next.lens = Some(37_534);
    settle(&ctx, &mut rail, &next, &mut time);
    assert_eq!(rail.view(), Some(fitted));
    // The user zooms in flight: the view is theirs...
    let at = egui::pos2(Axis::new(CHART, fitted).xf(37_400.0), 100.0);
    time += 1.0 / 60.0;
    frame(
        &ctx,
        &mut rail,
        &next,
        time,
        vec![Event::PointerMoved(at), wheel(2.0, false)],
    );
    settle(&ctx, &mut rail, &next, &mut time);
    let zoomed = rail.view().unwrap();
    assert!((zoomed.span - fitted.span / 2.0).abs() < 1e-6);
    let mut later = more.clone();
    later.states[62] = TickState::Checked;
    later.revision = 3;
    let later_input = inputs(&s, Some(&later));
    settle(&ctx, &mut rail, &later_input, &mut time);
    assert_eq!(rail.view(), Some(zoomed), "the user's view holds");
    // ...until Fit, which follows the stack again.
    rail.fit();
    settle(&ctx, &mut rail, &later_input, &mut time);
    assert_eq!(rail.view(), Some(fitted));
}
