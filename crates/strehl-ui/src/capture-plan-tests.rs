use super::*;
use crate::capture_client::StoredRaws;
use eframe::egui::{Event, FullOutput, PointerButton, Pos2, RawInput};
use serde_json::json;
use std::time::Instant;

fn snapshot(state: Value) -> Snapshot {
    let mut s = Snapshot {
        online: true,
        observed: Some(Instant::now()),
        receiver: json!({"ok":true,"free_bytes":371_000_000_000u64,"compress_raw":true,"archive_format":2}),
        stored: vec![StoredRaws {
            folder: "stack".into(),
            model: "ILCE-7CR".into(),
            raw_format: "sony-uncompressed".into(),
            raws: 784,
            original: 125_600_000,
            stored: 65_000_000,
            encoding: "strehl-archive-v2".into(),
        }],
        ..Default::default()
    };
    s.set_state(state);
    s
}

/// The mockup's plan: marks 37,100 to 37,764, step 7, four-shot, 1/8 s.
fn ready() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"ready","connected":true,
        "busy":false,"editable":true,"position":37556,"camera_model":"ILCE-7CR","usb_speed_mbps":5000,
        "plan":{"start":37100,"end":37764,"step":7,"settle_ms":500,"approach":128,"capture_timeout_s":120},
        "start_set":true,"end_set":true,"planned":96,"shots_per_plane":4,"pixel_shift_options":[1,4],
        "raw_max_bytes":130000000,"storage_required_bytes":64_700_000_000u64,"initial_seconds":540.0,
        "power":{"light":{"on":true,"watts":41.0},"camera":{"on":true,"watts":2.0},"available":true,
            "can_manage":true,"manage_stack":true,"warmup_seconds":5},
        "exposure":{"iso":100,"shutter":65544,"iso_options":[100,200,400],"shutter_options":[65544,65546],
            "writable":true,"mode":"M","problem":null}})
}

fn calibrated() -> Value {
    json!({"width":50.0,"suggested_step":7,"summary":"Detail stays sharp over about 50 focus units."})
}

fn inputs<'a>(s: &'a Snapshot, blockers: &'a [Blocker]) -> PlanInputs<'a> {
    PlanInputs {
        s,
        blockers,
        step: 7,
        settle_ms: 500,
        calibration: CalibrationView {
            stage: "done",
            result: calibrated(),
            ..Default::default()
        },
        test_shot: TestShotView {
            stage: "idle",
            ..Default::default()
        },
        switches: Switches {
            check: true,
            retake: Some(false),
            stack_when_done: true,
            power_down: Some(true),
        },
        engine: true,
        subjects: &[],
        subject_home: "Captures",
    }
}

/// The step table turns the calibrated width into overlap, planes, minutes
/// and gigabytes by the host's own rules, and marks the row past the
/// measured detail limit.
#[test]
fn the_step_table_reads_the_host_rules() {
    let s = snapshot(ready());
    let rows = step_rows(&s, 7, 500, &calibrated());
    let steps: Vec<u16> = rows.iter().map(|r| r.step).collect();
    assert_eq!(steps, [5, 7, 10, 16]);
    let seven = &rows[1];
    assert!(seven.current && !seven.risk);
    assert_eq!(seven.planes, 96, "Plan::positions over 664 units at step 7");
    assert_eq!(seven.overlap.unwrap().floor(), 7.0);
    // 96 four-shot planes: initial_plane(1/8 s, 500 ms, 4) x 96 + setup + warmup.
    let plane = strehl_capture::timing::initial_plane(65544, 500, 4).unwrap();
    let expected =
        (plane.mul_f64(96.0) + strehl_capture::timing::initial_setup(500)).as_secs_f64() + 5.0;
    assert!((seven.seconds.unwrap() - expected).abs() < 1e-6);
    // Expected disk: the last capture's stored size per RAW, times 384 RAWs.
    assert_eq!(seven.bytes, Some(65_000_000 * 384));
    assert!(rows[3].risk, "16: 3x overlap is past the detail limit");
    assert!(!rows[2].risk, "10: 5x is not");
    // A calibrated step outside the candidates joins the table, and so does
    // the coarsest step that keeps the detail (40 / 5 = 8).
    let odd = step_rows(&s, 7, 500, &json!({"width":40.0,"suggested_step":6}));
    assert_eq!(
        odd.iter().map(|r| r.step).collect::<Vec<_>>(),
        [5, 6, 7, 8, 10, 16]
    );
    // The owner's case: the line said "Steps up to 9" with no row for 9.
    let nine = step_rows(&s, 7, 500, &json!({"width":47.0,"suggested_step":6}));
    let view = CalibrationView {
        stage: "done",
        result: json!({"width":47.0}),
        ..Default::default()
    };
    assert!(guide::step_line(&nine, &view).starts_with("Steps up to 9 "));
    let row = nine.iter().find(|r| r.step == 9).expect("a row for 9");
    assert!(!row.risk, "47 / 9 is above the knee");
    // No bounds, no table.
    let mut unmarked = ready();
    unmarked["end_set"] = json!(false);
    assert!(step_rows(&snapshot(unmarked), 7, 500, &calibrated()).is_empty());
    // Without an earlier capture the worst case stands in.
    let mut fresh = snapshot(ready());
    fresh.stored.clear();
    let rows = step_rows(&fresh, 7, 500, &calibrated());
    assert_eq!(rows[1].bytes, worst_bytes(&fresh, 384));
}

/// The table's plane counts are exactly the host's `Plan::positions()`.
#[test]
fn plane_counts_match_the_hosts_positions() {
    for (start, end) in [
        (37_100, 37_764),
        (37_764, 37_100),
        (500, 500),
        (0, 65_535),
        (1000, 1001),
    ] {
        for step in [1, 2, 5, 7, 10, 16, 64, 999] {
            let plan = strehl_capture::model::Plan {
                start,
                end,
                step,
                ..Default::default()
            };
            if let Ok(p) = plan.positions() {
                assert_eq!(
                    plane_count(start, end, step),
                    p.len(),
                    "{start}..{end} step {step}"
                );
            }
        }
    }
}

#[test]
fn lines_say_what_the_rig_test_shot_and_calibration_found() {
    let s = snapshot(ready());
    assert_eq!(rig_summary(&s), "A7CR on · USB 5 Gbit/s · light 41 W");
    let mut off = ready();
    off["connected"] = json!(false);
    assert!(rig_summary(&snapshot(off)).starts_with("Camera not connected"));
    let levels = RawLevels {
        path: "frame-000001.ARW".into(),
        camera: "ILCE-7CR".into(),
        iso: Some(100.0),
        black: 512.0,
        white: 15360.0,
        samples: 10,
        clipped_share: 0.0,
        shadow_level: 0.012,
        median_level: 0.2,
        highlight_level: 0.9,
        colours: [crate::capture_workspace::test_shot::ColourLevels {
            highlight_level: 0.9,
            ..Default::default()
        }; 3],
        brightest: 1,
    };
    let line = test_shot_sentence(&TestShotView {
        stage: "done",
        levels: Some(levels),
        exposure: None,
        taken: None,
        error: None,
    })
    .unwrap();
    assert_eq!(
        line,
        "Test shot read from the RAW: nothing clipped, green brightest at 90 %, shadows at 1.2 % of full scale"
    );
    let view = CalibrationView {
        stage: "done",
        result: calibrated(),
        ..Default::default()
    };
    assert_eq!(
        calibration_sentence(&view, 7),
        "Calibrated · any point is sharp in 7 planes"
    );
    let waiting = CalibrationView {
        stage: "capturing",
        gives_up_in: Some(std::time::Duration::from_secs(300)),
        ..Default::default()
    };
    assert_eq!(
        calibration_sentence(&waiting, 7),
        "Calibrating: capturing · gives up in 300 s"
    );
    let rows = step_rows(&s, 7, 500, &calibrated());
    let summary = strip_summary(&s, &rows);
    assert!(summary.starts_with("96 planes · 384 RAWs · "), "{summary}");
    let (ends, disk) = footer_lines(&s, &rows);
    assert!(ends.is_some());
    assert_eq!(disk, "371 GB free · needs up to 64.7 GB");
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}

fn frame(
    ctx: &egui::Context,
    view: &mut PlanView,
    input: &PlanInputs<'_>,
    _time: f64,
    events: Vec<Event>,
) -> (FullOutput, Vec<PlanIntent>) {
    let time = CLOCK.with(|c| {
        c.set(c.get() + 0.05);
        c.get()
    });
    let mut intents = Vec::new();
    let raw = RawInput {
        screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(348.0, 982.0))),
        time: Some(time),
        events,
        ..Default::default()
    };
    let palette = CapturePalette::default();
    let out = ctx.run(raw, |ctx| {
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| intents = view.show(ui, input, &palette));
    });
    (out, intents)
}

fn text_at(out: &FullOutput, label: &str) -> Option<Pos2> {
    out.shapes.iter().find_map(|s| match &s.shape {
        egui::Shape::Text(t) if t.galley.text() == label => Some(t.visual_bounding_rect().center()),
        _ => None,
    })
}

fn click(
    ctx: &egui::Context,
    view: &mut PlanView,
    input: &PlanInputs<'_>,
    label: &str,
) -> Vec<PlanIntent> {
    let (out, _) = frame(ctx, view, input, 0.0, vec![]);
    let at = text_at(&out, label).unwrap_or_else(|| panic!("{label} is not drawn"));
    let mut all = Vec::new();
    for (i, events) in [
        vec![
            Event::PointerMoved(at),
            Event::PointerButton {
                pos: at,
                button: PointerButton::Primary,
                pressed: true,
                modifiers: Default::default(),
            },
        ],
        vec![Event::PointerButton {
            pos: at,
            button: PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        }],
    ]
    .into_iter()
    .enumerate()
    {
        all.extend(frame(ctx, view, input, 0.1 * (i + 1) as f64, events).1);
    }
    all
}

/// A ready plan starts on a click; the test shot, the marks, a table row
/// and a switch each say what they ask.
#[test]
fn clicks_become_intents() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(ready());
    let input = inputs(&s, &[]);
    let mut view = PlanView::default();
    assert_eq!(
        click(&ctx, &mut view, &input, "Start stack"),
        [PlanIntent::Start]
    );
    assert_eq!(
        click(&ctx, &mut view, &input, "Test shot"),
        [PlanIntent::TestShot]
    );
    assert_eq!(
        click(&ctx, &mut view, &input, "Mark start here"),
        [PlanIntent::MarkStart]
    );
    assert_eq!(
        click(&ctx, &mut view, &input, "Mark end here"),
        [PlanIntent::MarkEnd]
    );
    assert_eq!(
        click(&ctx, &mut view, &input, "10"),
        [PlanIntent::SetStep(10)]
    );
    assert_eq!(
        click(
            &ctx,
            &mut view,
            &input,
            "Stack it when the capture finishes"
        ),
        [PlanIntent::SetStackWhenDone(false)]
    );
    assert_eq!(
        click(&ctx, &mut view, &input, "Calibrate step"),
        [PlanIntent::Calibrate]
    );
}

/// A blocked plan does not start; its blocker is on the Start button and
/// its step's numeral is not green.
#[test]
fn a_blocked_plan_does_not_start() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut state = ready();
    state["end_set"] = json!(false);
    let s = snapshot(state);
    let blockers = vec![Blocker {
        check: Check::EndMark,
        chip: "End mark",
        sentence: "Mark the end of the focus range".into(),
        fix: Some(Fix::MarkEnd),
    }];
    let input = inputs(&s, &blockers);
    let mut view = PlanView::default();
    assert!(click(&ctx, &mut view, &input, "Start stack").is_empty());
    let (out, _) = frame(&ctx, &mut view, &input, 1.0, vec![]);
    let color = |label: &str| {
        out.shapes.iter().find_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == label => {
                Some(t.galley.job.sections[0].format.color)
            }
            _ => None,
        })
    };
    let palette = CapturePalette::default();
    assert_eq!(color("3"), Some(palette.ink3), "Depth is not ready");
    assert_eq!(color("1"), Some(palette.ok), "the rig is");
}

/// One frame at an inspector width, scrolled to the top.
fn frame_at(
    ctx: &egui::Context,
    view: &mut PlanView,
    input: &PlanInputs<'_>,
    width: f32,
    events: Vec<Event>,
) -> (FullOutput, Vec<PlanIntent>) {
    let time = CLOCK.with(|c| {
        c.set(c.get() + 0.05);
        c.get()
    });
    let mut intents = Vec::new();
    let raw = RawInput {
        screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(width, 1400.0))),
        time: Some(time),
        events,
        ..Default::default()
    };
    let palette = CapturePalette::default();
    let out = ctx.run(raw, |ctx| {
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| intents = view.show(ui, input, &palette));
    });
    (out, intents)
}

fn press_at(
    ctx: &egui::Context,
    view: &mut PlanView,
    input: &PlanInputs<'_>,
    at: Pos2,
) -> Vec<PlanIntent> {
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    let mut all = frame_at(
        ctx,
        view,
        input,
        348.0,
        vec![Event::PointerMoved(at), press(true)],
    )
    .1;
    all.extend(frame_at(ctx, view, input, 348.0, vec![press(false)]).1);
    all
}

fn tested(highlight: f64) -> TestShotView {
    TestShotView {
        stage: "done",
        levels: Some(RawLevels {
            path: "frame-000001.ARW".into(),
            camera: "ILCE-7CR".into(),
            iso: Some(100.0),
            black: 512.0,
            white: 15360.0,
            samples: 10,
            clipped_share: 0.0,
            shadow_level: 0.012,
            median_level: 0.2,
            highlight_level: highlight,
            colours: [crate::capture_workspace::test_shot::ColourLevels {
                highlight_level: highlight,
                ..Default::default()
            }; 3],
            brightest: 1,
        }),
        exposure: Some((100, 65544)),
        taken: None,
        error: None,
    }
}

/// Nothing the plan draws runs past the inspector, at its narrowest (300
/// px) and default width, with the rig settings open and a test shot read.
#[test]
fn nothing_runs_past_the_inspector() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut state = ready();
    state["suggestion"] = json!({"start":37000,"end":37764,"supported_tiles":20,"clipped":false});
    let s = snapshot(state);
    let mut input = inputs(&s, &[]);
    input.test_shot = tested(0.97);
    for width in [300.0, 348.0, 440.0] {
        let mut view = PlanView {
            rig_open: true,
            custom_step: "12".into(),
            ..Default::default()
        };
        frame_at(&ctx, &mut view, &input, width, vec![]);
        let (out, _) = frame_at(&ctx, &mut view, &input, width, vec![]);
        let mut seen = 0;
        for shape in &out.shapes {
            if let egui::Shape::Text(t) = &shape.shape {
                if t.galley.text().is_empty() {
                    continue;
                }
                seen += 1;
                let r = t.visual_bounding_rect();
                assert!(
                    r.right() <= width + 0.5 && r.left() >= -0.5,
                    "at {width}: '{}' runs past the inspector: {r:?}",
                    t.galley.text()
                );
            }
        }
        assert!(seen > 60, "the plan drew its text ({seen})");
    }
}

/// The rig's settings open from its step; the summary names them.
#[test]
fn the_rig_settings_open_from_the_rig_step() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(ready());
    let input = inputs(&s, &[]);
    let mut view = PlanView::default();
    let (out, _) = frame_at(&ctx, &mut view, &input, 348.0, vec![]);
    assert!(text_at(&out, "Approach 128 · settle 500 ms · warm-up 5 s").is_some());
    let at = text_at(&out, "SETTINGS").expect("the Rig step's settings link");
    press_at(&ctx, &mut view, &input, at);
    assert!(view.rig_open);
    let (out, _) = frame_at(&ctx, &mut view, &input, 348.0, vec![]);
    for label in [
        "Approach",
        "Settle",
        "Exposure timeout",
        "Light warm-up",
        "Manage power",
        "Error correction",
    ] {
        assert!(text_at(&out, label).is_some(), "{label}");
    }
}

/// The exposure guidance applies its suggestion, and "What changes" opens
/// the comparison at its section.
#[test]
fn guidance_applies_and_opens_the_comparison() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(ready());
    let mut input = inputs(&s, &[]);
    // 97 % at 1/8 s: 1/10 s keeps the highlights under 90 %.
    input.test_shot = tested(0.97);
    let mut view = PlanView::default();
    let (out, _) = frame_at(&ctx, &mut view, &input, 348.0, vec![]);
    let apply = text_at(&out, "APPLY").expect("the suggestion's action");
    assert_eq!(
        press_at(&ctx, &mut view, &input, apply),
        [PlanIntent::Exposure {
            iso: 100,
            shutter: 65546
        }]
    );
    let (out, _) = frame_at(&ctx, &mut view, &input, 348.0, vec![]);
    let more = text_at(&out, "WHAT CHANGES").expect("the comparison link");
    assert_eq!(
        press_at(&ctx, &mut view, &input, more),
        [PlanIntent::OpenGuide(GuideTab::Exposure)]
    );
    assert_eq!(view.guide, Some(GuideTab::Exposure));
}

/// A typed step shows what it gives in the table's last row and is chosen
/// with Enter or its link; letters are not kept.
#[test]
fn a_typed_step_is_previewed_and_chosen() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(ready());
    let input = inputs(&s, &[]);
    let mut view = PlanView {
        custom_step: "12".into(),
        ..Default::default()
    };
    let (out, _) = frame_at(&ctx, &mut view, &input, 348.0, vec![]);
    // 664 units at 12: 57 planes, as the host counts them.
    let planes = plane_count(37_100, 37_764, 12).to_string();
    assert_eq!(planes, "57");
    assert!(text_at(&out, &planes).is_some(), "the typed row's planes");
    let link = text_at(&out, "USE STEP 12").expect("the typed step's link");
    assert_eq!(
        press_at(&ctx, &mut view, &input, link),
        [PlanIntent::SetStep(12)]
    );
    // Typed with Enter.
    let field = text_at(&out, "12").expect("the typed step");
    press_at(&ctx, &mut view, &input, field);
    let key = |key| Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    };
    frame_at(
        &ctx,
        &mut view,
        &input,
        348.0,
        vec![key(egui::Key::End), Event::Text("x4".into())],
    );
    assert_eq!(view.custom_step, "124", "digits only");
    let (_, sent) = frame_at(&ctx, &mut view, &input, 348.0, vec![key(egui::Key::Enter)]);
    assert_eq!(sent, [PlanIntent::SetStep(124)]);
}

/// Enter that ends typing in a field is the field's: the station, which
/// reads Enter after the plan as Start stack, does not see it.
#[test]
fn enter_in_a_field_is_not_start() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(ready());
    let input = inputs(&s, &[]);
    let mut view = PlanView {
        custom_step: "12".into(),
        ..Default::default()
    };
    let (out, _) = frame_at(&ctx, &mut view, &input, 348.0, vec![]);
    let field = text_at(&out, "12").unwrap();
    press_at(&ctx, &mut view, &input, field);
    let enter = Event::Key {
        key: egui::Key::Enter,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    };
    let palette = CapturePalette::default();
    let mut station_saw_enter = None;
    let _ = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(348.0, 1400.0))),
            events: vec![enter],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    let sent = view.show(ui, &input, &palette);
                    assert_eq!(sent, [PlanIntent::SetStep(12)]);
                    // What the station reads next.
                    station_saw_enter = Some(ui.input(|i| i.key_pressed(egui::Key::Enter)));
                });
        },
    );
    assert_eq!(station_saw_enter, Some(false));
}
