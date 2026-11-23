//! h-retake: the run's own retake limit in the feed's words, "Retake" on a
//! plane left to one shot, and the warning for a run of such planes too
//! long for the calibrated overlap.
use super::super::{fixture, follow};
use super::*;
use eframe::egui::{Event, FullOutput, PointerButton, Pos2, RawInput};
use serde_json::{Value, json};

/// The retake fixture's host state: capturing (or ended), retakes by hand
/// accepted, plane 59 asked for.
fn retake_state(done: bool) -> Snapshot {
    let mut s = fixture::snapshot(fixture::Fixture::Flight);
    fixture::add_retakes(&mut s, done);
    if done {
        fixture::finish(&mut s);
    }
    s
}

fn inputs<'a>(s: &'a Snapshot, p: &'a Progress, ended: bool) -> FlightInputs<'a> {
    FlightInputs {
        s,
        progress: Some(p),
        checking: true,
        stack_when_done: true,
        power_down: Some(true),
        confirm_stop: false,
        left: Some(198.0),
        retake_cost: None,
        plain_pace: None,
        ended,
        ended_at: None,
        retakes: RetakeInputs {
            in_hand: s.host.retakes_in_hand(),
            step: Some(7),
            width: Some(50.0),
        },
    }
}

fn texts(out: &FullOutput) -> Vec<(String, Rect)> {
    fn walk(shape: &egui::Shape, out: &mut Vec<(String, Rect)>) {
        match shape {
            egui::Shape::Text(t) => {
                out.push((t.galley.text().to_owned(), t.visual_bounding_rect()))
            }
            egui::Shape::Vec(parts) => parts.iter().for_each(|p| walk(p, out)),
            _ => {}
        }
    }
    let mut v = Vec::new();
    for s in &out.shapes {
        walk(&s.shape, &mut v);
    }
    v
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}

fn canvas_frame(
    ctx: &egui::Context,
    input: &FlightInputs<'_>,
    view: &mut FlightView,
    events: Vec<Event>,
) -> (FullOutput, Vec<FlightIntent>) {
    let palette = CapturePalette::default();
    let time = CLOCK.with(|c| {
        c.set(c.get() + 0.05);
        c.get()
    });
    let mut intents = Vec::new();
    let out = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 855.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| intents = canvas(ui, input, view, &palette));
        },
    );
    (out, intents)
}

/// Clicks the first text `label` drawn (a button's or a link's).
fn click(
    ctx: &egui::Context,
    input: &FlightInputs<'_>,
    view: &mut FlightView,
    label: &str,
) -> Vec<FlightIntent> {
    let (out, _) = canvas_frame(ctx, input, view, vec![]);
    let at = texts(&out)
        .into_iter()
        .find(|t| t.0 == label)
        .map(|t| t.1.center())
        .unwrap_or_else(|| panic!("{label} is not drawn"));
    click_at(ctx, input, view, at)
}

fn click_at(
    ctx: &egui::Context,
    input: &FlightInputs<'_>,
    view: &mut FlightView,
    at: Pos2,
) -> Vec<FlightIntent> {
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    for _ in 0..3 {
        canvas_frame(ctx, input, view, vec![Event::PointerMoved(at)]);
    }
    let mut all = canvas_frame(ctx, input, view, vec![press(true)]).1;
    all.extend(canvas_frame(ctx, input, view, vec![press(false)]).1);
    all
}

fn item(plane: u64, attempt: u32, verdict: Verdict, retake: bool, reason: &str) -> FeedItem {
    FeedItem {
        plane,
        attempt,
        verdict,
        retake,
        reason: Some(reason.into()),
        members: 4,
        ..FeedItem::default()
    }
}

const RUNNING: FeedContext = FeedContext {
    error_correction: true,
    ended: false,
    max_retakes: 2,
    manual: true,
};

/// The rows say the run's own limit, not the old constant: tries left,
/// the policy, and none at all when retakes are set to 0.
#[test]
fn rows_say_the_runs_own_limit() {
    let first = item(7, 1, Verdict::Demote, true, fixture::MOTION);
    let three = FeedContext {
        max_retakes: 3,
        ..RUNNING
    };
    let row = feed_row(&first, None, three);
    assert_eq!(row.status, "retaking");
    assert!(
        row.detail.ends_with("Taking it again (try 2 of 4)."),
        "{}",
        row.detail
    );
    assert!(row.tip.contains("Retaken, up to 3 times"), "{}", row.tip);
    let third = item(7, 3, Verdict::Demote, true, fixture::MOTION);
    assert_eq!(feed_row(&third, None, three).status, "retaking");
    assert_eq!(feed_row(&third, None, RUNNING).status, "one shot");
    let none = FeedContext {
        max_retakes: 0,
        ..RUNNING
    };
    let row = feed_row(&first, None, none);
    assert_eq!((row.status, row.mark), ("one shot", Mark::Bad));
    assert!(
        row.detail.ends_with("Not retaken: retakes are set to 0."),
        "{}",
        row.detail
    );
    assert!(
        row.tip.contains("Retaken never (retakes are set to 0)"),
        "{}",
        row.tip
    );
    assert_eq!(
        Failure::Motion.policy_for(1),
        "Retaken, up to once: something changed between the shots, so another try can pass."
    );
    assert_eq!(Failure::Motion.policy_for(2), Failure::Motion.policy());
    // The tally counts by the same limit.
    let line = json!({"plane":7,"group_id":"g7","verdict":"demote","reason":fixture::MOTION,
        "retake":true,"members":4,"names":["frame-000025.ARW"]});
    let mut tally = follow::progress(&line.to_string()).tally;
    assert_eq!((tally.asked, tally.not_retaken), (1, 0));
    tally.resolve(0);
    assert_eq!((tally.asked, tally.not_retaken), (0, 1));
}

/// "Retake" is offered on a plane's last try when nothing else will take it
/// again, by a host that takes retakes by hand; once asked, the row says so.
#[test]
fn retake_is_offered_where_nothing_else_will_retake() {
    let exhausted = item(52, 3, Verdict::Demote, true, fixture::MOTION);
    let pattern = item(24, 1, Verdict::Demote, false, fixture::PATTERN);
    let retaking = item(60, 1, Verdict::Demote, true, fixture::MOTION);
    let passed = item(3, 2, Verdict::Pass, false, "");
    for it in [&exhausted, &pattern] {
        let row = feed_row(it, None, RUNNING);
        assert_eq!(row.retake, RetakeOffer::Offer, "{}", row.detail);
        assert!(row.tip.contains("Retake takes this plane again by hand"));
        let queued = feed_row_with(it, None, RUNNING, true);
        assert_eq!(
            (queued.retake, queued.status, queued.mark),
            (RetakeOffer::Queued, "queued", Mark::Warn)
        );
        assert!(
            queued
                .detail
                .ends_with("Retake asked for: taken between planes."),
            "{}",
            queued.detail
        );
        // An older host: no offer.
        let old = FeedContext {
            manual: false,
            ..RUNNING
        };
        assert_eq!(feed_row(it, None, old).retake, RetakeOffer::None);
        // A try followed by another: the later one is the plane's.
        assert_eq!(
            feed_row(it, Some(&passed), RUNNING).retake,
            RetakeOffer::None
        );
    }
    assert_eq!(feed_row(&retaking, None, RUNNING).retake, RetakeOffer::None);
    assert_eq!(feed_row(&passed, None, RUNNING).retake, RetakeOffer::None);
    let ended = FeedContext {
        ended: true,
        ..RUNNING
    };
    assert_eq!(feed_row(&retaking, None, ended).retake, RetakeOffer::Offer);
    let queued = feed_row_with(&exhausted, None, ended, true);
    assert!(
        queued.detail.ends_with("Retake asked for."),
        "{}",
        queued.detail
    );
}

/// A journal of `planes` planes, each try's check from `checks`.
fn run_of(planes: u64, checks: impl Fn(u64) -> Vec<fixture::Check>) -> Progress {
    let (lines, _) = fixture::journal(37_100, planes, checks);
    let text: Vec<String> = lines.iter().map(Value::to_string).collect();
    follow::progress(&text.join("\n"))
}

/// The coverage rule: a run of planes from one shot is named when the
/// four-shot planes either side are more than half the sharp width apart;
/// singles are not; a retake still to come and a plane not checked yet break
/// a run; without a calibration the width is assumed and said so.
#[test]
fn a_run_too_long_for_the_overlap_is_named_with_its_cost() {
    let ended = FeedContext {
        ended: true,
        ..RUNNING
    };
    let p = fixture::retake_progress(true).0;
    let spans = risk_spans(&p.feed, ended, 7, Some(50.0));
    assert_eq!(spans.len(), 1, "{spans:?}");
    let span = &spans[0];
    assert_eq!((span.first, span.last, span.count()), (44, 47, 4));
    assert_eq!(
        (span.gap, span.width, span.band, span.assumed),
        (35.0, 50.0, 10.0, false)
    );
    let why: Vec<(&str, usize)> = span.why.iter().map(|(w, n)| (w.as_str(), *n)).collect();
    assert_eq!(
        why,
        [
            ("not retaken: shift pattern off (by the checker's rule)", 2),
            ("failed every try", 1),
            (
                "not retaken: shift correction off (the shots are not at fault)",
                1
            ),
        ]
    );
    let (title, sentence) = risk_sentence(span);
    assert_eq!(title, "Planes 44–47: 4 in a row from one shot");
    assert!(
        sentence.starts_with(
            "The four-shot planes either side are 35 units apart, more than half the sharp width (50): about 10 units of depth there get one shot's detail, not four. 2 not retaken: shift pattern off"
        ),
        "{sentence}"
    );
    // A wider sharp width covers it; an assumed one (7 steps) does not.
    assert!(risk_spans(&p.feed, ended, 7, Some(80.0)).is_empty());
    let assumed = risk_spans(&p.feed, ended, 7, None);
    assert_eq!(assumed.len(), 1);
    assert!(assumed[0].assumed);
    assert!(
        risk_sentence(&assumed[0])
            .1
            .contains("(49, assumed; Calibrate step measures it)")
    );
    // The flight fixture's single failures (24, 27, 52, 59) never are.
    let singles = fixture::finished_progress().0;
    assert!(risk_spans(&singles.feed, ended, 7, Some(50.0)).is_empty());
    // Three in a row at width / 7 are; two are not.
    use fixture::Check::{Demote, Pass};
    let three = run_of(9, |p| {
        if (3..=5).contains(&p) {
            vec![Demote(fixture::PATTERN, false)]
        } else {
            vec![Pass]
        }
    });
    assert_eq!(risk_spans(&three.feed, ended, 7, Some(49.0)).len(), 1);
    let two = run_of(9, |p| {
        if (3..=4).contains(&p) {
            vec![Demote(fixture::PATTERN, false)]
        } else {
            vec![Pass]
        }
    });
    assert!(risk_spans(&two.feed, ended, 7, Some(49.0)).is_empty());
    // A retake still to come breaks the run while the capture runs.
    let pending = run_of(9, |p| match p {
        3 | 5 => vec![Demote(fixture::PATTERN, false)],
        4 => vec![Demote(fixture::MOTION, true)],
        _ => vec![Pass],
    });
    let last_lines = &pending.feed;
    assert!(risk_spans(last_lines, RUNNING, 7, Some(49.0)).is_empty());
    assert_eq!(risk_spans(last_lines, ended, 7, Some(49.0)).len(), 1);
    // A plane not checked yet breaks it too.
    let mut gap = three.clone();
    gap.feed.retain(|i| i.plane != 4);
    assert!(risk_spans(&gap.feed, ended, 7, Some(49.0)).is_empty());
    assert_eq!(plane_list(&[44, 45, 46, 47]), "44–47");
    assert_eq!(plane_list(&[45, 52]), "45 and 52");
}

/// The warning above the feed names the run and its cost, and "Retake
/// planes 44–47" asks for exactly those; "RETAKE" on a row asks for its
/// plane; the review offers the planes that failed every try. A host that
/// takes no retakes by hand gets the warning without the actions.
#[test]
fn the_warning_and_the_rows_ask_for_retakes() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = retake_state(false);
    let p = fixture::retake_progress(false).0;
    let mut input = inputs(&s, &p, false);
    assert_eq!(input.retakes.in_hand, [59]);
    let mut view = FlightView::default();
    let (out, _) = canvas_frame(&ctx, &input, &mut view, vec![]);
    let all = texts(&out);
    assert!(
        all.iter()
            .any(|t| t.0 == "Planes 44–47: 4 in a row from one shot")
    );
    // Plane 59, asked for: its row says so and offers nothing more.
    assert!(all.iter().any(|t| t.0 == "QUEUED"));
    assert!(all.iter().any(|t| t.0 == "ASKED"));
    assert!(
        all.iter()
            .any(|t| t.0.ends_with("Retake asked for: taken between planes.")),
        "{:?}",
        all.iter().map(|t| &t.0).collect::<Vec<_>>()
    );
    assert_eq!(
        click(&ctx, &input, &mut view, "Retake planes 44–47"),
        [FlightIntent::QueueRetakes(vec![44, 45, 46, 47])]
    );
    // Not asked for: the newest one-shot row in view offers its plane.
    input.retakes.in_hand.clear();
    let (out, _) = canvas_frame(&ctx, &input, &mut view, vec![]);
    let link = texts(&out)
        .into_iter()
        .filter(|t| t.0 == "RETAKE")
        .min_by(|a, b| a.1.top().total_cmp(&b.1.top()))
        .expect("a row offers Retake");
    let row_plane = texts(&out)
        .into_iter()
        .filter(|t| {
            t.0.parse::<u64>().is_ok()
                && t.1.center().x < link.1.right()
                && (t.1.center().y - (link.1.center().y - 37.0)).abs() < 6.0
        })
        .map(|t| t.0.parse::<u64>().unwrap())
        .next()
        .expect("its plane");
    assert_eq!(row_plane, 59, "the newest plane left to one shot");
    assert_eq!(
        click_at(&ctx, &input, &mut view, link.1.center()),
        [FlightIntent::QueueRetakes(vec![row_plane])]
    );
    // The review: the exhausted planes (45 and 52) in one action.
    let done = retake_state(true);
    let finished = fixture::retake_progress(true).0;
    let review = inputs(&done, &finished, true);
    let mut view = FlightView::default();
    assert_eq!(
        click(
            &ctx,
            &review,
            &mut view,
            "Retake the 2 planes that failed every try"
        ),
        [FlightIntent::QueueRetakes(vec![45, 52])]
    );
    // An older host: the warning stays, the actions go.
    let mut state = fixture::snapshot(fixture::Fixture::Flight).state;
    state["capabilities"] = json!({"test_shot":true,"exposure_check":true});
    state.as_object_mut().unwrap().remove("retakes");
    let mut old = fixture::snapshot(fixture::Fixture::Flight);
    old.set_state(state);
    assert!(!old.host.takes_manual_retakes());
    let input = inputs(&old, &p, false);
    let mut view = FlightView::default();
    let (out, _) = canvas_frame(&ctx, &input, &mut view, vec![]);
    let all = texts(&out);
    assert!(
        all.iter()
            .any(|t| t.0 == "Planes 44–47: 4 in a row from one shot")
    );
    assert!(
        !all.iter()
            .any(|t| t.0 == "Retake planes 44–47" || t.0 == "RETAKE")
    );
}

/// What the coverage rule costs when a new plane is checked (it runs once
/// per change of the feed, never per frame): the 5,400-plane run.
/// `cargo test --release -p strehl-ui risk_spans_cost -- --ignored --nocapture`.
#[test]
#[ignore = "benchmark: prints ms per evaluation"]
fn risk_spans_cost() {
    let (p, _) = fixture::long_progress();
    let cx = FeedContext {
        ended: true,
        ..RUNNING
    };
    let start = std::time::Instant::now();
    let mut spans = 0;
    for _ in 0..20 {
        spans += risk_spans(std::hint::black_box(&p.feed), cx, 7, Some(50.0)).len();
    }
    println!(
        "risk_spans over {} items: {:.3} ms each ({spans} spans)",
        p.feed.len(),
        start.elapsed().as_secs_f64() * 1000.0 / 20.0
    );
}
