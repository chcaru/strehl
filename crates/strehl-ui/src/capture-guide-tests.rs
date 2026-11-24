//! The guidance arithmetic against the measurements it cites, and the
//! comparison panel's tables.
use super::*;
use crate::capture_workspace::fixture::{self, Fixture};
use crate::capture_workspace::test_shot::RawLevels;
use eframe::egui::{Event, FullOutput, PointerButton, Pos2, RawInput};
use serde_json::json;

/// Sony shutter codes.
const S_1_25: u64 = (1 << 16) | 25;
const S_1_8: u64 = (1 << 16) | 8;
const S_0_4: u64 = (4 << 16) | 10;
const S_0_6: u64 = (6 << 16) | 10;
const S_0_8: u64 = (8 << 16) | 10;

fn levels(highlight: f64, clipped: f64, iso: f32) -> RawLevels {
    RawLevels {
        path: "frame-000001.ARW".into(),
        camera: "ILCE-7CR".into(),
        iso: Some(iso),
        black: 512.0,
        white: 15360.0,
        samples: 61_000_000,
        clipped_share: clipped,
        shadow_level: 0.012,
        median_level: 0.1,
        highlight_level: highlight,
        colours: [crate::capture_workspace::test_shot::ColourLevels {
            highlight_level: highlight,
            ..Default::default()
        }; 3],
        brightest: 1,
        in_subject: false,
    }
}

fn view(highlight: f64, clipped: f64, iso: u64, shutter: u64) -> TestShotView {
    TestShotView {
        stage: "done",
        levels: Some(levels(highlight, clipped, iso as f32)),
        exposure: Some((iso, shutter)),
        ..Default::default()
    }
}

/// The fixture's plan: ISO 100, 1/8 s, four-shot, marks 37,100-37,764,
/// shutter options from 1/25 s to 1 s in thirds.
fn plan() -> Snapshot {
    fixture::snapshot(Fixture::Plan)
}

/// SNR rises as the square root of the exposure: in dB, 10 log10 of the
/// ratio; the noise falls by half a stop per stop of exposure. The
/// measured SNRs (results.md, follow-up table) sit within 15 % of it.
#[test]
fn noise_follows_the_square_root_of_the_exposure() {
    assert!((snr_db(0.6, 0.125) - 6.812).abs() < 1e-3);
    assert!((noise_stops(0.6, 0.125) + 1.131).abs() < 1e-3);
    assert_eq!(snr_db(0.2, 0.2), 0.0);
    // Measured final-image SNR at 0.6 s 67.7; 1/3 s 48.1; 1/6 s 32.4;
    // 1/10 s 27.2; 1/25 s 15.4 (one ISO each, raised to keep brightness).
    for (seconds, measured) in [
        (1.0 / 3.0, 48.1),
        (1.0 / 6.0, 32.4),
        (0.1, 27.2),
        (0.04, 15.4),
    ] {
        let predicted = 67.7 * 10f64.powf(snr_db(seconds, 0.6) / 20.0);
        assert!(
            (measured / predicted - 1.0).abs() < 0.15,
            "{seconds} s: measured {measured}, predicted {predicted:.1}"
        );
    }
}

#[test]
fn numbers_keep_their_units_on_the_line() {
    assert_eq!(
        unbreak("at least 2 s, 9 % and 48 of 48."),
        "at least 2\u{a0}s, 9\u{a0}% and 48 of 48."
    );
    assert_eq!(unbreak("ISO 100 · 0.4 s:"), "ISO 100 · 0.4\u{a0}s:");
    assert_eq!(unbreak("step 16 keeps"), "step 16 keeps");
}

#[test]
fn the_base_iso_is_the_lowest_fixed_one() {
    assert_eq!(base_iso(&[400, 100, 200, 0x00ff_ffff], 400), 100);
    assert_eq!(
        base_iso(&[0x1000_0032, 100, 200], 200),
        100,
        "flagged codes after plain ones"
    );
    assert_eq!(base_iso(&[], 640), 640);
    assert_eq!(iso_number(0x00ff_ffff), None);
    assert_eq!(iso_number(0x1000_0c80), Some(3200.0));
}

/// Highlights scale with ISO x exposure; past the target they are near,
/// past full scale they clip; a clipped test cannot speak for brighter.
#[test]
fn highlights_scale_linearly_from_the_test_shot() {
    let m = metered(&view(0.24, 0.0, 100, S_1_8)).unwrap();
    assert!((m.highlight_at(100.0, 0.4).unwrap() - 0.768).abs() < 1e-9);
    assert_eq!(clip_at(Some(&m), Some(100.0), 0.4), Clip::Safe);
    assert_eq!(clip_at(Some(&m), Some(100.0), 0.5), Clip::Near);
    assert_eq!(clip_at(Some(&m), Some(100.0), 0.6), Clip::Clips);
    assert_eq!(
        clip_at(Some(&m), Some(400.0), 0.125),
        Clip::Near,
        "ISO is brightness too"
    );
    assert_eq!(clip_at(None, Some(100.0), 0.4), Clip::Unknown);
    assert_eq!(clip_at(Some(&m), None, 0.4), Clip::Unknown, "ISO AUTO");
    let clipped = metered(&view(1.0, 0.01, 100, S_1_8)).unwrap();
    assert!(clipped.clipped());
    assert_eq!(clip_at(Some(&clipped), Some(100.0), 0.125), Clip::Clips);
    assert_eq!(clip_at(Some(&clipped), Some(100.0), 0.0625), Clip::Unknown);
    // The RAW's own ISO is preferred to the code the camera reported.
    let raw = TestShotView {
        levels: Some(levels(0.3, 0.0, 200.0)),
        exposure: Some((100, S_1_8)),
        ..Default::default()
    };
    assert_eq!(metered(&raw).unwrap().iso, 200.0);
    // Without the exposure it was taken at, nothing can be scaled.
    let unknown = TestShotView {
        levels: Some(levels(0.3, 0.0, 100.0)),
        ..Default::default()
    };
    assert_eq!(metered(&unknown), None);
}

/// The suggestion is base ISO and the longest offered exposure whose
/// highlights stay under 90 %.
#[test]
fn advice_is_base_iso_and_the_longest_exposure_that_does_not_clip() {
    let s = plan();
    let e = s.host.exposure.clone().unwrap();
    // 24 % at 1/8 s: 0.4 s gives 77 %, 1/2 s 96 %.
    let m = metered(&view(0.24, 0.0, 100, S_1_8));
    assert_eq!(
        advise(&e, m.as_ref()),
        Advice::Change {
            iso: 100,
            shutter: S_0_4
        }
    );
    // 86 % at 1/8 s: already the longest.
    let m = metered(&view(0.86, 0.0, 100, S_1_8));
    assert_eq!(
        advise(&e, m.as_ref()),
        Advice::Best {
            iso: 100,
            shutter: S_1_8
        }
    );
    // At ISO 400, 50 %: base ISO and 0.8 s (0.5 x 6.4 / 4 = 80 %).
    let mut at400 = e.clone();
    at400.iso = Some(400);
    let m = metered(&view(0.5, 0.0, 400, S_1_8));
    assert_eq!(
        advise(&at400, m.as_ref()),
        Advice::Change {
            iso: 100,
            shutter: S_0_8
        }
    );
    // Too bright even at 1/25 s.
    let m = metered(&view(0.99, 0.0, 100, S_1_25));
    assert_eq!(
        advise(&e, m.as_ref()),
        Advice::TooBright {
            iso: 100,
            shutter: S_1_25
        }
    );
    // Brighter than 90 % at the current setting: a shorter suggestion.
    let m = metered(&view(0.97, 0.0, 100, S_1_8));
    assert!(
        matches!(advise(&e, m.as_ref()), Advice::Change { shutter, .. } if shutter == (1 << 16) | 10)
    );
    // Clipped, or no test shot.
    let m = metered(&view(1.0, 0.002, 100, S_1_8));
    assert_eq!(advise(&e, m.as_ref()), Advice::Clipped { share: 0.002 });
    assert_eq!(advise(&e, None), Advice::TestShot { iso: 100 });
    // Placebo: with a target of full scale the suggestion would be 1/2 s
    // (96 %); the target is what keeps it at 0.4 s.
    let m = metered(&view(0.24, 0.0, 100, S_1_8)).unwrap();
    assert!(m.highlight_at(100.0, 0.5).unwrap() > HIGHLIGHT_TARGET);
    assert!(m.highlight_at(100.0, 0.5).unwrap() < 1.0);
}

/// The comparison keeps now and the suggestion, rows about a stop apart,
/// at most seven, with the host's own plane and stack times.
#[test]
fn exposure_rows_keep_now_and_the_suggestion_and_say_the_cost() {
    let s = plan();
    let m = metered(&view(0.24, 0.0, 100, S_1_8));
    let advice = advise(s.host.exposure.as_ref().unwrap(), m.as_ref());
    let planes = Some(96);
    let rows = exposure_rows(&s, 500, planes, m.as_ref(), &advice);
    assert!(
        rows.len() <= MAX_EXPOSURE_ROWS && rows.len() >= 3,
        "{rows:?}"
    );
    let now = rows.iter().find(|r| r.current).unwrap();
    assert_eq!(now.shutter, S_1_8);
    assert_eq!(now.snr_db, 0.0);
    let pick = rows.iter().find(|r| r.suggested).unwrap();
    assert_eq!(pick.shutter, S_0_4);
    assert!((pick.snr_db - 10.0 * (0.4f64 / 0.125).log10()).abs() < 1e-9);
    assert_eq!(pick.clip, Clip::Safe);
    let host_plane = strehl_capture::timing::initial_plane(S_0_4, 500, 4).unwrap();
    assert_eq!(pick.plane, Some(host_plane.as_secs_f64()));
    assert_eq!(pick.stack, plan::stack_seconds_at(&s, 96, 500, S_0_4));
    // Longest first, about a stop apart (the options nearest to whole
    // stops from now), the suggestion between: 1 s, 1/2, 0.4, 1/4, 1/8, 1/15.
    let shown: Vec<String> = rows
        .iter()
        .map(|r| style::shutter_label(r.shutter))
        .collect();
    assert_eq!(shown, ["1 s", "1/2 s", "0.4 s", "1/4 s", "1/8 s", "1/15 s"]);
    for pair in rows.windows(2) {
        assert!(pair[0].seconds > pair[1].seconds);
        let apart = (pair[0].seconds / pair[1].seconds).log2();
        let pinned = |r: &ExposureRow| r.current || r.suggested;
        assert!(
            (0.7..=1.4).contains(&apart) || pinned(&pair[0]) || pinned(&pair[1]),
            "{apart}"
        );
    }
    // Something past the suggestion is shown clipping or near.
    assert!(
        rows.iter()
            .any(|r| matches!(r.clip, Clip::Near | Clip::Clips))
    );
    // The line: what to change, what it buys and costs, and the action.
    let line = exposure_line(&advice, &rows).unwrap();
    assert!(
        line.text
            .starts_with("Suggested ISO 100 · 0.4 s: +5.1 dB SNR"),
        "{}",
        line.text
    );
    assert!(
        line.text
            .contains(", +0.5 s a plane, +46 s a stack (estimate)"),
        "{}",
        line.text
    );
    assert_eq!(
        line.action,
        Some((
            "Apply",
            PlanIntent::Exposure {
                iso: 100,
                shutter: S_0_4
            }
        ))
    );
    // At the best already: said in green, nothing to do.
    let m = metered(&view(0.86, 0.0, 100, S_1_8));
    let best = advise(s.host.exposure.as_ref().unwrap(), m.as_ref());
    let line = exposure_line(&best, &exposure_rows(&s, 500, planes, m.as_ref(), &best)).unwrap();
    assert_eq!(line.tone, Tone::Good);
    assert!(line.action.is_none());
    // No test shot: the rule, and the way to apply it.
    let line = exposure_line(&Advice::TestShot { iso: 100 }, &[]).unwrap();
    assert!(line.text.contains("not ISO") && line.text.contains("test shot"));
}

/// Detail kept reads the two measured stacks: their measured points
/// exactly, between them linearly, everything at fine steps.
#[test]
fn detail_kept_reads_the_measured_curves() {
    let at = |k: f64| detail_kept(k);
    // Fine steps keep it all.
    assert_eq!(
        at(20.0),
        DetailKept {
            low: 1.0,
            high: 1.0,
            beyond: false
        }
    );
    // The scarab's step 24 (overlap 113 / 24): 0.988 measured; the dark
    // stack between its 16 and 24.
    let d = at(113.0 / 24.0);
    assert!((d.high - 0.988).abs() < 1e-9);
    let f = (113.0 / 24.0 - 88.0 / 24.0) / (88.0 / 16.0 - 88.0 / 24.0);
    assert!((d.low - (0.983 + f * (0.989 - 0.983))).abs() < 1e-9);
    assert_eq!(detail_label(&d), "99 %");
    // The scarab's step 32 lost 5 %.
    let d = at(113.0 / 32.0);
    assert!((d.low - 0.946).abs() < 1e-9);
    assert_eq!(detail_label(&d), "95 %");
    // Coarser than either was measured.
    let d = at(1.0);
    assert!(d.beyond);
    assert_eq!(detail_label(&d), "<82 %");
    // The knee: the scarab's step 24 (overlap 4.7) is past it, 16 (7.1)
    // is not; the plan marks rows by the same constant.
    let (k24, k16) = (113.0 / 24.0, 113.0 / 16.0);
    assert!(std::hint::black_box(k24) < KNEE && std::hint::black_box(k16) > KNEE);
    assert_eq!(plan::DETAIL_LIMIT, KNEE);
}

#[test]
fn step_rows_carry_detail_and_the_knee() {
    let s = plan();
    let calibration = json!({"width":50.0,"suggested_step":7});
    let rows = plan::step_rows(&s, 7, 500, &calibration);
    let ten = rows.iter().find(|r| r.step == 10).unwrap();
    assert!(!ten.risk, "50 / 10 = 5: at the knee");
    let sixteen = rows.iter().find(|r| r.step == 16).unwrap();
    assert!(sixteen.risk);
    assert_eq!(sixteen.detail, Some(detail_kept(50.0 / 16.0)));
    // A typed step's row is computed the same way.
    let typed = plan::step_row(&s, 12, 7, 500, Some(50.0));
    assert_eq!(typed.planes, plan::plane_count(37_100, 37_764, 12));
    assert!(typed.risk && !typed.current);
    assert_eq!(plan::parse_step("12"), Ok(12));
    assert!(plan::parse_step("0").is_err() && plan::parse_step("70000").is_err());
    assert_eq!(plan::parse_step(""), Err(String::new()));
    let view = CalibrationView {
        stage: "done",
        result: calibration,
        ..Default::default()
    };
    assert!(step_line(&rows, &view).starts_with("Steps up to 10 keep the detail"));
    let finer = plan::step_rows(&s, 4, 500, &json!({"width":50.0}));
    assert!(step_line(&finer, &view).contains("finer than it needs"));
    let none = CalibrationView::default();
    assert!(step_line(&rows, &none).starts_with("Calibrate step"));
}

/// Settle rows: the host's plane time for each choice, the measured passes
/// where measured.
#[test]
fn settle_rows_say_time_and_what_passed() {
    let s = plan();
    let rows = settle_rows(&s, Some(96), 500);
    let at = |ms| rows.iter().find(|r| r.ms == ms).unwrap();
    assert!(at(500).current);
    assert_eq!(at(500).still, Some("48 of 48"));
    assert_eq!(at(2000).still, Some("48 of 48"));
    assert_eq!(at(1000).still, Some("45 of 48 †"));
    assert_eq!(at(250).still, None);
    let host = |ms| {
        strehl_capture::timing::initial_plane(S_1_8, ms, 4)
            .unwrap()
            .as_secs_f64()
    };
    assert_eq!(at(2000).plane, Some(host(2000)));
    // The rig measured 7.03 s against 5.66 s a four-shot plane at 0.6 s:
    // the host's model gives the same 1.4 s difference.
    let d = strehl_capture::timing::initial_plane(S_0_6, 2000, 4)
        .unwrap()
        .as_secs_f64()
        - strehl_capture::timing::initial_plane(S_0_6, 500, 4)
            .unwrap()
            .as_secs_f64();
    assert!((d - 1.45).abs() < 0.1, "{d}");
    // A setting off the list joins it.
    assert!(
        settle_rows(&s, None, 1200)
            .iter()
            .any(|r| r.ms == 1200 && r.current)
    );
}

#[test]
fn warmup_rows_add_to_a_managed_stack() {
    let s = plan();
    let rows = warmup_rows(&s, Some(96), 500);
    let five = rows.iter().find(|r| r.seconds == 5).unwrap();
    assert!(five.current);
    let sixty = rows.iter().find(|r| r.seconds == 60).unwrap();
    assert_eq!(sixty.adds, Some(60.0));
    assert!((sixty.stack.unwrap() - five.stack.unwrap() - 55.0).abs() < 1e-9);
}

/// Start and End against the survey.
#[test]
fn bounds_are_compared_with_the_survey() {
    let mut state = s_state();
    let line = |state: &serde_json::Value| {
        let mut s = plan();
        s.set_state(state.clone());
        bounds_line(&s, 7, 500)
    };
    assert_eq!(line(&state).unwrap().tone, Tone::Good);
    // The survey saw more than the marks: warned, with the survey's bounds.
    state["suggestion"]["start"] = json!(37_000);
    let l = line(&state).unwrap();
    assert_eq!(l.tone, Tone::Warn);
    assert!(l.text.contains("100 units outside"), "{}", l.text);
    assert_eq!(l.action.map(|a| a.1), Some(PlanIntent::UseSurveyBounds));
    // Marks beyond the survey: what they cost.
    state["suggestion"]["start"] = json!(37_200);
    let l = line(&state).unwrap();
    assert_eq!(l.tone, Tone::Note);
    assert!(
        l.text.contains("100 units past") && l.text.contains("more planes"),
        "{}",
        l.text
    );
    // At its search limit: survey again.
    state["suggestion"]["clipped"] = json!(true);
    assert!(line(&state).unwrap().text.contains("search limit"));
    // No survey, nothing said.
    state.as_object_mut().unwrap().remove("suggestion");
    assert!(line(&state).is_none());
}

fn s_state() -> serde_json::Value {
    plan().state
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}

fn panel(
    ctx: &egui::Context,
    tab: &mut GuideTab,
    inputs: &GuideInputs<'_>,
    events: Vec<Event>,
    width: f32,
) -> (FullOutput, Vec<PlanIntent>, bool) {
    let time = CLOCK.with(|c| {
        c.set(c.get() + 0.05);
        c.get()
    });
    let mut result = (Vec::new(), false);
    let out = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(width, 1000.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            let anchor =
                Rect::from_min_max(egui::pos2(width - 348.0, 80.0), egui::pos2(width, 1000.0));
            result = show_panel(ctx, anchor, tab, inputs, &CapturePalette::default());
        },
    );
    (out, result.0, result.1)
}

fn texts(out: &FullOutput) -> Vec<(String, Rect)> {
    out.shapes
        .iter()
        .filter_map(|s| match &s.shape {
            egui::Shape::Text(t) => Some((t.galley.text().to_owned(), t.visual_bounding_rect())),
            _ => None,
        })
        .collect()
}

/// Each section draws; its table's cells never overlap one another, at a
/// wide and at a narrow window; a click on a row chooses it.
#[test]
fn the_panel_draws_each_section_and_a_row_chooses() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = plan();
    let calibration = CalibrationView {
        stage: "done",
        result: json!({"width":50.0,"suggested_step":7}),
        ..Default::default()
    };
    let test_shot = view(0.24, 0.0, 100, S_1_8);
    let inputs = GuideInputs {
        s: &s,
        step: 7,
        settle_ms: 500,
        calibration: &calibration,
        test_shot: &test_shot,
        editable: true,
    };
    for width in [1680.0, 1100.0] {
        for t in GuideTab::ALL {
            let mut tab = t;
            panel(&ctx, &mut tab, &inputs, vec![], width);
            let (out, _, _) = panel(&ctx, &mut tab, &inputs, vec![], width);
            let all = texts(&out);
            assert!(all.iter().any(|(t, _)| t == "WHAT CHANGES"));
            // Cells on one row (same centre line, short single lines) must
            // not overlap.
            let cells: Vec<&(String, Rect)> =
                all.iter().filter(|(_, r)| r.height() < 18.0).collect();
            for (i, (a, ra)) in cells.iter().enumerate() {
                for (b, rb) in cells.iter().skip(i + 1) {
                    if (ra.center().y - rb.center().y).abs() < 2.0 {
                        assert!(
                            !ra.intersects(rb.shrink(0.5)),
                            "{t:?} at {width}: '{a}' {ra:?} overlaps '{b}' {rb:?}"
                        );
                    }
                }
            }
            // Everything inside the panel, left of the inspector.
            for (text, r) in &all {
                assert!(
                    r.right() <= width - 348.0 + 0.5,
                    "{t:?} at {width}: '{text}' {r:?}"
                );
            }
        }
    }
    // Exposure: a click on the 0.4 s row asks for it.
    let mut tab = GuideTab::Exposure;
    let (out, _, _) = panel(&ctx, &mut tab, &inputs, vec![], 1680.0);
    let at = texts(&out)
        .into_iter()
        .find(|(t, _)| t == "0.4 s")
        .unwrap()
        .1
        .center();
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    panel(
        &ctx,
        &mut tab,
        &inputs,
        vec![Event::PointerMoved(at), press(true)],
        1680.0,
    );
    let (_, chosen, _) = panel(&ctx, &mut tab, &inputs, vec![press(false)], 1680.0);
    assert_eq!(
        chosen,
        [PlanIntent::Exposure {
            iso: 100,
            shutter: S_0_4
        }]
    );
    // Step: the 10 row.
    let mut tab = GuideTab::Step;
    let (out, _, _) = panel(&ctx, &mut tab, &inputs, vec![], 1680.0);
    let at = texts(&out)
        .into_iter()
        .find(|(t, _)| t == "10")
        .unwrap()
        .1
        .center();
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    panel(
        &ctx,
        &mut tab,
        &inputs,
        vec![Event::PointerMoved(at), press(true)],
        1680.0,
    );
    let (_, chosen, _) = panel(&ctx, &mut tab, &inputs, vec![press(false)], 1680.0);
    assert_eq!(chosen, [PlanIntent::SetStep(10)]);
    // Not editable: rows are not choices.
    let fixed = GuideInputs {
        editable: false,
        ..inputs
    };
    panel(
        &ctx,
        &mut tab,
        &fixed,
        vec![Event::PointerMoved(at), press(true)],
        1680.0,
    );
    let (_, chosen, _) = panel(&ctx, &mut tab, &fixed, vec![press(false)], 1680.0);
    assert!(chosen.is_empty());
    // Escape closes.
    let escape = Event::Key {
        key: egui::Key::Escape,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    };
    let (_, _, close) = panel(&ctx, &mut tab, &inputs, vec![escape], 1680.0);
    assert!(close);
}
