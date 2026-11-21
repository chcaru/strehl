//! Rig settings: the host's ranges, the values shown, and the command each
//! control sends.
use super::*;
use crate::capture_client::{Connection, TestInbox};
use eframe::egui::{Event, FullOutput, PointerButton, Pos2, RawInput, Rect};
use serde_json::{Value, json};
use std::time::Instant;

fn snapshot(state: Value) -> Snapshot {
    let mut s = Snapshot {
        online: true,
        observed: Some(Instant::now()),
        receiver: json!({"ok":true,"free_bytes":1_000_000_000_000u64}),
        ..Default::default()
    };
    s.set_state(state);
    s
}

fn ready() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"ready","connected":true,
        "busy":false,"editable":true,"position":37556,
        "plan":{"start":37100,"end":37764,"step":7,"settle_ms":500,"approach":128,"capture_timeout_s":120},
        "start_set":true,"end_set":true,"planned":96,"shots_per_plane":1,"raw_max_bytes":80000000,
        "power":{"light":{"on":true},"camera":{"on":true},"available":true,"can_manage":true,
            "manage_stack":true,"warmup_seconds":5},
        "error_correction":false,
        "exposure":{"iso":100,"shutter":65544,"mode":"M","writable":true,"iso_options":[100,200],"shutter_options":[65544]},
        "suggestion":{"start":37100,"end":37764,"supported_tiles":20,"clipped":false},
        "capabilities":{"test_shot":true,"exposure_check":true}})
}

/// Every typed value is judged as the host judges it: the plan's own
/// `validate` for approach, settle and timeout, the schedule store's
/// `set_warmup` for the warm-up.
#[test]
fn values_are_checked_by_the_hosts_rules() {
    let plan = Plan {
        start: 10_000,
        end: 11_000,
        step: 7,
        ..Plan::default()
    };
    let dir = tempfile::tempdir().unwrap();
    let mut store = strehl_capture::schedule::Store::open(dir.path().join("s.json"), 5, 0).unwrap();
    for value in [
        0u32, 1, 4, 5, 99, 100, 101, 128, 299, 300, 301, 3600, 3601, 4096, 4097, 30000, 30001,
    ] {
        let text = value.to_string();
        let host = |p: Plan| p.validate().is_ok();
        assert_eq!(
            validate(Key::Approach, &text, Some(&plan)).is_ok(),
            u16::try_from(value).is_ok_and(|a| host(Plan {
                approach: a,
                ..plan.clone()
            })),
            "approach {value}"
        );
        assert_eq!(
            validate(Key::Settle, &text, Some(&plan)).is_ok(),
            host(Plan {
                settle_ms: value,
                ..plan.clone()
            }),
            "settle {value}"
        );
        assert_eq!(
            validate(Key::Timeout, &text, Some(&plan)).is_ok(),
            host(Plan {
                capture_timeout_s: value,
                ..plan.clone()
            }),
            "timeout {value}"
        );
        assert_eq!(
            validate(Key::Warmup, &text, None).is_ok(),
            store.set_warmup(value).is_ok(),
            "warm-up {value}"
        );
    }
    // A unit after the number is allowed; anything else is not.
    assert_eq!(validate(Key::Approach, "256 units", None), Ok(256));
    assert_eq!(validate(Key::Settle, " 750ms ", None), Ok(750));
    assert!(validate(Key::Approach, "12a", None).is_err());
    assert!(validate(Key::Settle, "", None).is_err());
    // The approach must fit before the start mark (the lens limit).
    let near = Plan {
        start: 100,
        end: 1000,
        ..plan.clone()
    };
    assert_eq!(validate(Key::Approach, "100", Some(&near)), Ok(100));
    let error = validate(Key::Approach, "128", Some(&near)).unwrap_err();
    assert!(error.contains("lens limit"), "{error}");
}

#[test]
fn steppers_walk_the_ladders_within_the_range() {
    let settle = spec(Key::Settle);
    assert_eq!(step_value(settle, 500, true), 750);
    assert_eq!(step_value(settle, 500, false), 250);
    assert_eq!(
        step_value(settle, 600, false),
        500,
        "off the ladder: the one below"
    );
    assert_eq!(step_value(settle, 30000, true), 30000);
    assert_eq!(step_value(spec(Key::Approach), 100, true), 128);
    assert_eq!(step_value(spec(Key::Approach), 16, false), 1);
    assert_eq!(step_value(spec(Key::Warmup), 0, false), 0);
    assert_eq!(step_value(spec(Key::Timeout), 120, true), 300);
    for s in &SPECS {
        assert!(
            s.ladder.iter().all(|v| (s.min..=s.max).contains(v)),
            "{}",
            s.label
        );
        assert!((s.min..=s.max).contains(&s.default));
        assert!(help(s).contains(&format!("Default {} {}", s.default, s.unit)));
    }
    // The defaults are the host's.
    let host = Plan::default();
    assert_eq!(spec(Key::Approach).default, u32::from(host.approach));
    assert_eq!(spec(Key::Settle).default, host.settle_ms);
    assert_eq!(spec(Key::Timeout).default, host.capture_timeout_s);
}

#[test]
fn the_host_values_are_read_and_summarised() {
    let s = snapshot(ready());
    let v = RigValues::read(&s, 500, true);
    assert_eq!(
        (v.approach, v.settle, v.timeout, v.warmup),
        (Some(128), Some(500), Some(120), Some(5))
    );
    assert_eq!(v.manage_power, Some(true));
    assert_eq!(v.error_correction, Some(false));
    assert!(v.plan_editable && v.between);
    assert_eq!(summary(&v), "Approach 128 · settle 500 ms · warm-up 5 s");
    let mut bare = ready();
    bare.as_object_mut().unwrap().remove("power");
    let v = RigValues::read(&snapshot(bare), 2000, false);
    assert_eq!(v.warmup, None);
    assert_eq!(summary(&v), "Approach 128 · settle 2 s");
}

fn workspace(
    state: Value,
) -> (
    tempfile::TempDir,
    super::super::CaptureWorkspace,
    TestInbox,
    Snapshot,
) {
    let dir = tempfile::tempdir().unwrap();
    let mut ws = super::super::CaptureWorkspace::new(Some(dir.path().join("capture.json")));
    let s = snapshot(state);
    let (connection, inbox) = Connection::detached(s.clone());
    ws.connection = Some(connection);
    // The plan as the station reads it each frame.
    ws.sync_plan(s.host.plan.clone().unwrap(), 3);
    (dir, ws, inbox, s)
}

/// Each setting sends the host's own command, the plan's other fields kept.
#[test]
fn each_setting_sends_the_hosts_command() {
    let (_dir, mut ws, inbox, s) = workspace(ready());
    let mut sent = |intent: PlanIntent| {
        ws.apply_plan(&s, intent);
        let request = inbox.command();
        ws.connection.as_ref().unwrap().replace(s.clone());
        request.map(|r| serde_json::to_value(r.command).unwrap())
    };
    assert_eq!(
        sent(intent(Key::Approach, 256)),
        Some(
            json!({"op":"settings","step":7,"settle_ms":500,"approach":256,"capture_timeout_s":120})
        )
    );
    assert_eq!(
        sent(intent(Key::Timeout, 300)),
        Some(
            json!({"op":"settings","step":7,"settle_ms":500,"approach":128,"capture_timeout_s":300})
        )
    );
    assert_eq!(
        sent(intent(Key::Settle, 2000)),
        Some(
            json!({"op":"settings","step":7,"settle_ms":2000,"approach":128,"capture_timeout_s":120})
        )
    );
    assert_eq!(
        sent(intent(Key::Warmup, 60)),
        Some(json!({"op":"set_warmup","seconds":60}))
    );
    assert_eq!(
        sent(PlanIntent::SetRetake(true)),
        Some(json!({"op":"error_correction","enabled":true}))
    );
    assert_eq!(
        sent(PlanIntent::SetPowerDown(false)),
        Some(json!({"op":"power_plan","enabled":false}))
    );
    assert_eq!(
        sent(PlanIntent::UseSurveyBounds),
        Some(json!({"op":"apply_bounds"}))
    );
    // Opening the comparison panel sends nothing.
    assert_eq!(
        sent(PlanIntent::OpenGuide(super::super::guide::GuideTab::Step)),
        None
    );
    assert_eq!(
        ws.station.plan.guide,
        Some(super::super::guide::GuideTab::Step)
    );
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}

fn frame(
    ctx: &egui::Context,
    editor: &mut RigEditor,
    v: &RigValues,
    plan: Option<&Plan>,
    events: Vec<Event>,
) -> (FullOutput, Vec<PlanIntent>) {
    let time = CLOCK.with(|c| {
        c.set(c.get() + 0.05);
        c.get()
    });
    let mut out = Vec::new();
    let output = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(282.0, 900.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    editor.show(ui, v, plan, &CapturePalette::default(), &mut out)
                });
        },
    );
    (output, out)
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

fn click(
    ctx: &egui::Context,
    editor: &mut RigEditor,
    v: &RigValues,
    plan: Option<&Plan>,
    at: Pos2,
) -> Vec<PlanIntent> {
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    let mut all = frame(
        ctx,
        editor,
        v,
        plan,
        vec![Event::PointerMoved(at), press(true)],
    )
    .1;
    all.extend(frame(ctx, editor, v, plan, vec![press(false)]).1);
    all
}

/// The editor: a stepper sends the ladder's next value, a typed value is
/// sent on Enter, an out-of-range one is refused with the range, and the
/// switches flip.
#[test]
fn the_editor_sends_steps_typed_values_and_switches() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(ready());
    let v = RigValues::read(&s, 500, true);
    let plan = s.host.plan.clone();
    let mut editor = RigEditor::default();
    let (out, _) = frame(&ctx, &mut editor, &v, plan.as_ref(), vec![]);
    let all = texts(&out);
    for spec in &SPECS {
        assert!(
            all.iter().any(|(t, _)| t == spec.label),
            "{} drawn",
            spec.label
        );
        let default =
            super::super::guide::unbreak(&format!("Default {} {}", spec.default, spec.unit));
        assert!(all.iter().any(|(t, _)| t.contains(&default)), "{default}");
    }
    // Every label sits inside the column (nothing clipped at 282 px).
    for (t, r) in all.iter().filter(|(t, _)| !t.is_empty()) {
        assert!(r.right() <= 282.5, "{t} runs past the column: {r:?}");
    }
    // The approach row's "+": the drawn stepper at the row's right edge.
    let row = all.iter().find(|(t, _)| t == "Approach").unwrap().1;
    let plus = Pos2::new(282.0 - 11.0, row.center().y);
    assert_eq!(
        click(&ctx, &mut editor, &v, plan.as_ref(), plus),
        [PlanIntent::SetApproach(256)]
    );
    // Type into the settle field.
    let field = all.iter().find(|(t, _)| t == "500 ms").unwrap().1.center();
    assert!(click(&ctx, &mut editor, &v, plan.as_ref(), field).is_empty());
    // The field appears and takes the keyboard.
    frame(&ctx, &mut editor, &v, plan.as_ref(), vec![]);
    let select_all = Event::Key {
        key: egui::Key::A,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers::COMMAND,
    };
    frame(
        &ctx,
        &mut editor,
        &v,
        plan.as_ref(),
        vec![select_all.clone(), Event::Text("1500".into())],
    );
    let enter = Event::Key {
        key: egui::Key::Enter,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    };
    let (_, sent) = frame(&ctx, &mut editor, &v, plan.as_ref(), vec![enter.clone()]);
    assert_eq!(sent, [PlanIntent::SetSettle(1500)]);
    // Out of range: refused, the range said.
    let (out, _) = frame(&ctx, &mut editor, &v, plan.as_ref(), vec![]);
    let field = texts(&out)
        .into_iter()
        .find(|(t, _)| t == "120 s")
        .unwrap()
        .1
        .center();
    click(&ctx, &mut editor, &v, plan.as_ref(), field);
    frame(&ctx, &mut editor, &v, plan.as_ref(), vec![]);
    frame(
        &ctx,
        &mut editor,
        &v,
        plan.as_ref(),
        vec![select_all, Event::Text("9000".into())],
    );
    let (_, sent) = frame(&ctx, &mut editor, &v, plan.as_ref(), vec![enter]);
    assert!(sent.is_empty(), "{sent:?}");
    let (out, _) = frame(&ctx, &mut editor, &v, plan.as_ref(), vec![]);
    assert!(
        texts(&out)
            .iter()
            .any(|(t, _)| t == "Exposure timeout must be 5-3600 s"),
        "the range is said"
    );
    // The switches: error correction on (checking is on), power off.
    let toggle_left = |label: &str| {
        let r = texts(&out).into_iter().find(|(t, _)| t == label).unwrap().1;
        // The toggle sits at the row's right edge.
        Pos2::new(282.0 - 13.0, r.center().y)
    };
    assert_eq!(
        click(
            &ctx,
            &mut editor,
            &v,
            plan.as_ref(),
            toggle_left("Error correction")
        ),
        [PlanIntent::SetRetake(true)]
    );
    assert_eq!(
        click(
            &ctx,
            &mut editor,
            &v,
            plan.as_ref(),
            toggle_left("Manage power")
        ),
        [PlanIntent::SetPowerDown(false)]
    );
    // Without the checker, error correction cannot be switched on.
    let off = RigValues {
        checking: false,
        ..v.clone()
    };
    assert!(
        click(
            &ctx,
            &mut editor,
            &off,
            plan.as_ref(),
            toggle_left("Error correction")
        )
        .is_empty()
    );
}
