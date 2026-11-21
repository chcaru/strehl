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
    // A calibrated step outside the candidates joins the table.
    let odd = step_rows(&s, 7, 500, &json!({"width":40.0,"suggested_step":6}));
    assert_eq!(
        odd.iter().map(|r| r.step).collect::<Vec<_>>(),
        [5, 6, 7, 10, 16]
    );
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
    assert_eq!(rig_summary(&s), "ILCE-7CR on · USB 5 Gbit/s · light 41 W");
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
    };
    let line = test_shot_sentence(&TestShotView {
        stage: "done",
        levels: Some(levels),
        taken: None,
        error: None,
    })
    .unwrap();
    assert_eq!(
        line,
        "Test shot read from the RAW: nothing clipped, shadows at 1.2 % of full scale"
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
