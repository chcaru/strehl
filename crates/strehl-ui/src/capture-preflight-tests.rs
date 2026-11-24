use super::super::{test_shot::TestShot, tools::Calibration};
use super::*;
use serde_json::{Value, json};
use std::time::{Duration, Instant};

/// A connected, marked, idle camera with a ready receiver and room to spare.
fn ready_state() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"ready","connected":true,
        "busy":false,"editable":true,"demo":false,"position":30000,
        "plan":{"start":30000,"end":30090,"step":10,"settle_ms":500,"approach":128,"capture_timeout_s":120},
        "start_set":true,"end_set":true,"planned":10,"plan_error":null,"shots_per_plane":1,
        "raw_max_bytes":80000000,
        "exposure":{"iso":100,"shutter":65546,"mode":"M","problem":null,"writable":true},
        "capabilities":{"test_shot":true,"exposure_check":true}})
}

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

fn checks(s: &Snapshot, ui: &CaptureWorkspace) -> Vec<Check> {
    start_blockers(s, ui).into_iter().map(|b| b.check).collect()
}

/// A workspace whose plan names a new subject (`unnamed()` names none).
fn workspace() -> (tempfile::TempDir, CaptureWorkspace) {
    let (dir, mut ui) = unnamed();
    ui.station.plan.subject = "Harvestman".into();
    (dir, ui)
}
fn unnamed() -> (tempfile::TempDir, CaptureWorkspace) {
    let dir = tempfile::tempdir().unwrap();
    let ui = CaptureWorkspace::new(Some(dir.path().join("capture.json")));
    (dir, ui)
}

#[test]
fn a_ready_rig_has_no_blockers() {
    let (_dir, ui) = workspace();
    let s = snapshot(ready_state());
    assert_eq!(start_blockers(&s, &ui), vec![]);
    assert!(can_schedule(&[]));
}

/// Each host condition, alone, is the one blocker named, with its chip,
/// sentence and fix.
#[test]
fn each_host_condition_blocks_start_on_its_own() {
    let (_dir, ui) = workspace();
    let cases: Vec<(&str, Value, Check, Option<Fix>)> = vec![
        (
            "connected",
            json!(false),
            Check::Camera,
            Some(Fix::ConnectCamera),
        ),
        ("editable", json!(false), Check::NotEditable, None),
        (
            "failure",
            json!({"message":"Lost the camera","exposure_uncertain":false,"can_reconnect":true}),
            Check::Failure,
            Some(Fix::RecoverCamera),
        ),
        (
            "start_set",
            json!(false),
            Check::StartMark,
            Some(Fix::MarkStart),
        ),
        ("end_set", json!(false), Check::EndMark, Some(Fix::MarkEnd)),
        (
            "plan_error",
            json!("Shorten Approach; the first position is too close to the lens limit"),
            Check::Plan,
            None,
        ),
    ];
    for (key, value, check, fix) in cases {
        let mut state = ready_state();
        state[key] = value;
        if key == "connected" {
            state["editable"] = json!(false);
        }
        if key == "failure" {
            state["editable"] = json!(false);
            state["phase"] = json!("fault");
        }
        let s = snapshot(state);
        let blockers = start_blockers(&s, &ui);
        assert_eq!(blockers.len(), 1, "{key}: {blockers:?}");
        assert_eq!((blockers[0].check, blockers[0].fix), (check, fix), "{key}");
        assert!(!blockers[0].chip.is_empty() && !blockers[0].sentence.is_empty());
    }
    let mut state = ready_state();
    state["failure"] = json!({"message":"Lost the camera"});
    state["editable"] = json!(false);
    assert_eq!(
        start_blockers(&snapshot(state), &ui)[0].sentence,
        "Lost the camera"
    );
    let mut state = ready_state();
    state["editable"] = json!(false);
    state["phase"] = json!("capturing");
    assert_eq!(
        start_blockers(&snapshot(state), &ui)[0].sentence,
        "A sequence is running"
    );
}

/// H1: the host's exposure problem is a blocker before Start, with the
/// host's own sentence; an older host (no `problem`) is not blocked by it.
#[test]
fn the_exposure_problem_blocks_before_start() {
    let (_dir, ui) = workspace();
    let mut state = ready_state();
    state["exposure"]["mode"] = json!("A");
    state["exposure"]["problem"] =
        json!("Set the camera to M (manual exposure) before starting a stack");
    let blockers = start_blockers(&snapshot(state.clone()), &ui);
    assert_eq!(blockers.len(), 1);
    assert_eq!(blockers[0].check, Check::Exposure);
    assert_eq!(
        blockers[0].sentence,
        "Set the camera to M (manual exposure) before starting a stack"
    );
    state["exposure"] = json!({"iso":100,"shutter":65546});
    assert!(start_blockers(&snapshot(state), &ui).is_empty());
}

#[test]
fn an_offline_or_unreadable_host_blocks_first() {
    let (_dir, ui) = workspace();
    let mut s = snapshot(ready_state());
    s.observed = None;
    s.connection_error = Some("timed out".into());
    let blockers = start_blockers(&s, &ui);
    assert_eq!(blockers[0].check, Check::Offline);
    assert_eq!(blockers[0].fix, Some(Fix::ConnectionSettings));
    assert!(blockers[0].sentence.contains("timed out"));
    assert!(
        !blockers.iter().any(|b| b.check == Check::StartMark),
        "stale host fields are not judged"
    );
    let mut state = ready_state();
    state["editable"] = json!("yes");
    let s = snapshot(state);
    assert_eq!(checks(&s, &ui), [Check::HostState]);
}

#[test]
fn the_pc_side_conditions_block_start() {
    let (_dir, ui) = workspace();
    let mut s = snapshot(ready_state());
    s.receiver = json!({"ok":true,"free_bytes":1_000_000u64});
    assert_eq!(checks(&s, &ui), [Check::Capacity]);
    s.receiver = json!({"ok":false});
    assert_eq!(
        checks(&s, &ui),
        [Check::Receiver],
        "free space unknown: the receiver says why"
    );
    assert_eq!(start_blockers(&s, &ui)[0].fix, Some(Fix::StartReceiver));
    // The simulator needs neither.
    let mut state = ready_state();
    state["demo"] = json!(true);
    let mut demo = snapshot(state);
    demo.receiver = Value::Null;
    assert!(checks(&demo, &ui).is_empty());
    let mut s = snapshot(ready_state());
    s.pending = true;
    assert_eq!(checks(&s, &ui), [Check::Sending]);
}

/// The desktop's own state: unapplied edits, a focus move, a calibration or
/// a test shot, and the schedule editor, which still lets a stack be
/// scheduled.
#[test]
fn the_desktops_own_work_blocks_start() {
    let s = snapshot(ready_state());
    let (_dir, mut ui) = workspace();
    ui.draft_dirty = true;
    assert_eq!(checks(&s, &ui), [Check::Edits]);
    assert_eq!(start_blockers(&s, &ui)[0].fix, Some(Fix::ApplyEdits));
    let (_dir, mut ui) = workspace();
    ui.focus_pending = Some(30010);
    assert_eq!(checks(&s, &ui), [Check::Focus]);
    let (_dir, mut ui) = workspace();
    ui.focus_flight = Some((30010, 4, Instant::now()));
    assert_eq!(checks(&s, &ui), [Check::Focus]);
    let (_dir, mut ui) = workspace();
    ui.calibration = Calibration::Switching {
        restore_four: false,
        positions: vec![30000],
        round: 0,
        deadline: Instant::now() + Duration::from_secs(45),
        shutters: None,
    };
    assert_eq!(checks(&s, &ui), [Check::Calibration]);
    let (_dir, mut ui) = workspace();
    ui.test_shot = TestShot::Capturing {
        sequence: 3,
        deadline: Instant::now() + Duration::from_secs(60),
        folder: None,
    };
    assert_eq!(checks(&s, &ui), [Check::TestShot]);
    let (_dir, mut ui) = workspace();
    ui.schedule_ui.open(&s);
    let blockers = start_blockers(&s, &ui);
    assert_eq!(blockers.len(), 1);
    assert_eq!(blockers[0].check, Check::Schedule);
    assert!(
        can_schedule(&blockers),
        "the editor is where scheduling happens"
    );
    ui.draft_dirty = true;
    assert!(!can_schedule(&start_blockers(&s, &ui)));
}

/// The list keeps the order to resolve them in: the camera before its marks,
/// the marks before the PC.
#[test]
fn blockers_come_in_the_order_to_resolve_them() {
    let (_dir, mut ui) = workspace();
    ui.draft_dirty = true;
    let mut state = ready_state();
    state["connected"] = json!(false);
    state["editable"] = json!(false);
    state["start_set"] = json!(false);
    let mut s = snapshot(state);
    s.receiver = json!({"ok":false});
    assert_eq!(
        checks(&s, &ui),
        [
            Check::Camera,
            Check::StartMark,
            Check::Edits,
            Check::Receiver
        ]
    );
}

/// Owner feedback, 2026-11-22: with nothing named, the subject is the one
/// blocker, the strip's Subject chip says so and its fix puts the cursor in
/// the field; named, the chip is met.
#[test]
fn an_unnamed_subject_blocks_start_and_its_chip_says_so() {
    let (_dir, mut ui) = unnamed();
    let s = snapshot(ready_state());
    assert_eq!(checks(&s, &ui), vec![Check::Subject]);
    let blockers = start_blockers(&s, &ui);
    assert_eq!(blockers[0].fix, Some(Fix::NameSubject));
    let chips = strip_chips(&s, &blockers);
    let chip = chips.iter().find(|c| c.label == "Subject").unwrap();
    assert_eq!(chip.mark, Mark::Warn);
    assert_eq!(chip.fix, Some(Fix::NameSubject));
    ui.station.plan.subject = "Harvestman".into();
    let chips = strip_chips(&s, &start_blockers(&s, &ui));
    let chip = chips.iter().find(|c| c.label == "Subject").unwrap();
    assert_eq!((chip.mark, chip.sentence.as_ref()), (Mark::Ok, None));
}
