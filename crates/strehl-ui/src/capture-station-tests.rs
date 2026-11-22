//! The station's intents reach the camera through the workspace's checks.
use super::*;
use crate::capture_client::TestInbox;
use serde_json::{Value, json};
use strehl_capture::session::PositionsKind;

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
        "exposure":{"iso":100,"shutter":65544,"mode":"M","writable":true,"iso_options":[100,200],"shutter_options":[65544]},
        "capabilities":{"test_shot":true,"exposure_check":true}})
}

fn workspace(state: Value) -> (tempfile::TempDir, CaptureWorkspace, TestInbox, Snapshot) {
    let dir = tempfile::tempdir().unwrap();
    let mut ws = CaptureWorkspace::new(Some(dir.path().join("capture.json")));
    ws.station.plan.subject = "Harvestman".into();
    let s = snapshot(state);
    let (connection, inbox) = Connection::detached(s.clone());
    ws.connection = Some(connection);
    (dir, ws, inbox, s)
}

/// Each plan intent sends the host's own command, with fresh revisions.
#[test]
fn plan_intents_send_the_hosts_commands() {
    let (_dir, mut ws, inbox, s) = workspace(ready());
    let sent = |ws: &mut CaptureWorkspace, intent: PlanIntent| {
        ws.apply_plan(&s, intent);
        let request = inbox.command();
        // The detached connection never answers, so clear `pending`.
        ws.connection.as_ref().unwrap().replace(s.clone());
        request.map(|r| r.command)
    };
    assert!(matches!(
        sent(
            &mut ws,
            PlanIntent::Exposure {
                iso: 200,
                shutter: 65544
            }
        ),
        Some(Command::Exposure {
            iso: 200,
            shutter: 65544
        })
    ));
    assert!(matches!(
        sent(&mut ws, PlanIntent::MarkEnd),
        Some(Command::Mark { start: false })
    ));
    assert!(matches!(
        sent(&mut ws, PlanIntent::SetStep(10)),
        Some(Command::Settings {
            step: 10,
            settle_ms: 500,
            approach: 128,
            capture_timeout_s: 120
        })
    ));
    assert!(matches!(
        sent(&mut ws, PlanIntent::SetSettle(1000)),
        Some(Command::Settings {
            step: 10,
            settle_ms: 1000,
            ..
        })
    ));
    assert!(matches!(
        sent(&mut ws, PlanIntent::SetFourShot(true)),
        Some(Command::PixelShift { shots: 4 })
    ));
    assert!(matches!(
        sent(&mut ws, PlanIntent::Start),
        Some(Command::Start {})
    ));
    assert!(matches!(
        sent(&mut ws, PlanIntent::TestShot),
        Some(Command::CapturePositions {
            kind: PositionsKind::Test,
            ..
        })
    ));
    assert!(sent(&mut ws, PlanIntent::SetStackWhenDone(false)).is_none());
    assert!(!ws.stack_when_done);
    assert!(sent(&mut ws, PlanIntent::OpenRig).is_none());
    assert!(ws.take_open_rig());
    assert!(!ws.take_open_rig(), "taken once");
}

/// A blocked plan does not start, whatever asks.
#[test]
fn a_blocked_plan_does_not_start() {
    let mut state = ready();
    state["end_set"] = json!(false);
    let (_dir, mut ws, inbox, s) = workspace(state);
    ws.apply_plan(&s, PlanIntent::Start);
    assert!(inbox.command().is_none());
}

/// A dragged bound moves focus there first, and is marked only once the
/// lens has arrived and the camera is idle.
#[test]
fn a_dragged_bound_is_reached_then_marked() {
    let (_dir, mut ws, inbox, s) = workspace(ready());
    ws.apply_rail(
        &s,
        RailIntent::MoveBound {
            start: false,
            to: 37_700,
        },
    );
    assert_eq!(ws.focus_pending, Some(37_700));
    assert!(ws.station.mark_at.is_some());
    ws.poll_station(&s);
    assert!(inbox.command().is_none(), "not there yet");
    ws.focus_pending = None;
    let mut there = ready();
    there["position"] = json!(37_700);
    there["camera_revision"] = json!(5);
    let s = snapshot(there);
    ws.connection.as_ref().unwrap().replace(s.clone());
    ws.poll_station(&s);
    assert!(matches!(
        inbox.command().map(|r| r.command),
        Some(Command::Mark { start: false })
    ));
    assert!(ws.station.mark_at.is_none());
}

/// Rail jogs and live-view intents become commands; flight intents pause,
/// ask before stopping and open glance.
#[test]
fn rail_live_and_flight_intents() {
    let (_dir, mut ws, inbox, s) = workspace(ready());
    ws.apply_rail(&s, RailIntent::Jog(16));
    assert!(matches!(
        inbox.command().map(|r| r.command),
        Some(Command::Jog { delta: 16 })
    ));
    ws.connection.as_ref().unwrap().replace(s.clone());
    ws.apply_rail(&s, RailIntent::Focus(37_000));
    assert_eq!(ws.focus_pending, Some(37_000));
    ws.apply_live(
        &s,
        LiveIntent::Magnify {
            ratio: 59,
            x: 320,
            y: 240,
        },
    );
    assert!(matches!(
        inbox.command().map(|r| r.command),
        Some(Command::Magnify { ratio: 59, .. })
    ));
    let mut running = ready();
    running["phase"] = json!("capturing");
    running["editable"] = json!(false);
    let (_dir, mut ws, inbox, s) = workspace(running);
    assert_eq!(ws.station_mode(), StationMode::Flight);
    ws.apply_flight(&s, FlightIntent::AskStop);
    assert_eq!(ws.confirm, Some(Confirm::Stop));
    assert!(inbox.command().is_none(), "asking sends nothing");
    ws.apply_flight(&s, FlightIntent::Stop);
    assert!(matches!(
        inbox.command().map(|r| r.command),
        Some(Command::Stop {})
    ));
    assert_eq!(ws.confirm, None);
    ws.apply_flight(&s, FlightIntent::Glance);
    assert!(ws.glance_open());
    let raw: Option<std::sync::Arc<str>> = Some("frame-000157.ARW".into());
    ws.apply_flight(
        &s,
        FlightIntent::ShowPlane {
            plane: 39,
            raw: raw.clone(),
        },
    );
    assert_eq!(ws.take_show_plane(), Some((39, raw)));
}

fn texts(out: &egui::FullOutput) -> Vec<String> {
    out.shapes
        .iter()
        .filter_map(|s| match &s.shape {
            egui::Shape::Text(t) => Some(t.galley.text().to_owned()),
            _ => None,
        })
        .collect()
}

/// The station draws in its slots: the strip says Ready with the plan, the
/// plan's Start is drawn, and Escape leaves glance mode.
#[test]
fn the_station_draws_and_glance_returns() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let (_dir, mut ws, _inbox, _s) = workspace(ready());
    let screen = Some(Rect::from_min_size(
        egui::Pos2::ZERO,
        egui::vec2(1680.0, 1006.0),
    ));
    let out = ctx.run(
        egui::RawInput {
            screen_rect: screen,
            ..Default::default()
        },
        |ctx| ws.show_station(ctx),
    );
    let all = texts(&out);
    for want in [
        "PRE-FLIGHT",
        "Ready",
        "Start stack",
        "DEPTH RAIL",
        "Rig",
        "Exposure",
        "Depth",
    ] {
        assert!(all.iter().any(|t| t == want), "{want}: {all:?}");
    }
    ws.station.glance = true;
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: screen,
            events: vec![egui::Event::Key {
                key: egui::Key::Escape,
                physical_key: None,
                pressed: true,
                repeat: false,
                modifiers: Default::default(),
            }],
            ..Default::default()
        },
        |ctx| ws.show_station(ctx),
    );
    assert!(!ws.glance_open());
}

/// The proof as the station runs it, through `poll_station` and its
/// texture, on a scratch copy of a real capture: `STREHL_PROOF_RUN` as for
/// `draft_preview`'s `proof_follows_a_real_run` (its RAWs,
/// `transfer-receipts.full.jsonl` and optionally `events.full.jsonl`).
/// `cargo test --release -p strehl-ui the_station_proof_follows_a_real_run -- --ignored --nocapture`.
#[test]
#[ignore = "needs a scratch copy of a real capture"]
fn the_station_proof_follows_a_real_run() {
    use std::io::Write;
    let Some(run) = std::env::var_os("STREHL_PROOF_RUN").map(PathBuf::from) else {
        return;
    };
    let full = std::fs::read_to_string(run.join("transfer-receipts.full.jsonl")).unwrap();
    let lines: Vec<&str> = full
        .lines()
        .filter(|l| {
            serde_json::from_str::<Value>(l).is_ok_and(|r| {
                r["logical_name"].as_str().is_some_and(|n| {
                    !n.starts_with("frame-") || run.join(format!("{n}.straw")).is_file()
                })
            })
        })
        .collect();
    let receipts = run.join("transfer-receipts.jsonl");
    std::fs::write(&receipts, "").unwrap();
    let _ = std::fs::remove_file(run.join("result.json"));
    if let Ok(events) = std::fs::read(run.join("events.full.jsonl")) {
        std::fs::write(run.join("events.jsonl"), events).unwrap();
    }
    let mut state = ready();
    state["phase"] = json!("capturing");
    state["shots_per_plane"] = json!(4);
    state["completed"] = json!(1);
    state["total"] = json!(211);
    let (_dir, mut ws, _inbox, mut s) = workspace(state);
    s.in_progress = Some(crate::capture_client::InProgress {
        folder: run.clone(),
        idle: Duration::ZERO,
        test: false,
    });
    ws.connection.as_ref().unwrap().replace(s.clone());
    let ctx = egui::Context::default();
    let started = Instant::now();
    let mut shown = Vec::new();
    let seen = |ws: &mut CaptureWorkspace, shown: &mut Vec<(f64, String)>| {
        let s = ws.station_snapshot();
        ws.poll_station(&s);
        if let Some((_, _, what)) = ws.proof_texture(&ctx)
            && shown.last().is_none_or(|(_, w)| *w != what)
        {
            println!("{:>6.1} s: {what}", started.elapsed().as_secs_f64());
            shown.push((started.elapsed().as_secs_f64(), what));
        }
    };
    for line in &lines {
        let mut f = std::fs::OpenOptions::new()
            .append(true)
            .open(&receipts)
            .unwrap();
        writeln!(f, "{line}").unwrap();
        drop(f);
        std::thread::sleep(Duration::from_millis(100));
        seen(&mut ws, &mut shown);
    }
    let end = Instant::now() + Duration::from_secs(20);
    while Instant::now() < end {
        std::thread::sleep(Duration::from_millis(100));
        seen(&mut ws, &mut shown);
    }
    let errors = ws.station.proof.as_ref().and_then(|p| p.error.clone());
    println!("updates shown: {}; last error: {errors:?}", shown.len());
    assert!(shown.len() > 3, "{shown:?}");
}

/// A capture this desktop watched that completes (or is stopped) stays in
/// the flight view, saying what happened, until Back to planning; a test
/// shot's run does not.
#[test]
fn an_ended_capture_is_reviewed_until_back_to_planning() {
    let mut capturing = ready();
    capturing["phase"] = json!("capturing");
    capturing["editable"] = json!(false);
    let (_dir, mut ws, _inbox, s) = workspace(capturing.clone());
    ws.poll_station(&s);
    assert_eq!(ws.station_mode(), StationMode::Flight);
    let mut complete = capturing.clone();
    complete["phase"] = json!("complete");
    complete["editable"] = json!(true);
    let ended = snapshot(complete.clone());
    ws.connection.as_ref().unwrap().replace(ended.clone());
    ws.poll_station(&ended);
    assert!(ws.station.review);
    assert_eq!(ws.station_mode(), StationMode::Flight);
    assert!(ws.station.ended_at.is_some());
    assert!(ws.station_hints().keys.is_empty());
    ws.apply_flight(&ended, FlightIntent::Done);
    assert_eq!(ws.station_mode(), StationMode::Plan);
    // A test shot's run ends without a review.
    let mut test = snapshot(capturing);
    test.in_progress = Some(crate::capture_client::InProgress {
        folder: PathBuf::from("test-run"),
        idle: Duration::ZERO,
        test: true,
    });
    ws.connection.as_ref().unwrap().replace(test.clone());
    ws.poll_station(&test);
    ws.connection.as_ref().unwrap().replace(ended.clone());
    ws.poll_station(&ended);
    assert!(!ws.station.review);
    assert_eq!(ws.station_mode(), StationMode::Plan);
}

/// Owner feedback, 2026-11-22: a capture goes to a new subject unless one
/// is chosen on purpose. Start waits for the new subject's name (or a
/// choice); a test shot does not. The capture takes the names, keeps them
/// while it runs and is reviewed, and the next plan starts unnamed again.
#[test]
fn each_capture_names_its_subject_and_the_next_one_starts_unnamed() {
    use super::super::subject::SubjectChoice;
    let (_dir, mut ws, inbox, s) = workspace(ready());
    let sent = |ws: &mut CaptureWorkspace, intent: PlanIntent| {
        ws.apply_plan(&s, intent);
        let request = inbox.command();
        ws.connection.as_ref().unwrap().replace(s.clone());
        request.map(|r| r.command)
    };
    ws.clear_plan_subject();
    assert!(
        sent(&mut ws, PlanIntent::Start).is_none(),
        "unnamed: Start waits"
    );
    let blockers = preflight::start_blockers(&s, &ws);
    assert_eq!(
        blockers.iter().map(|b| b.check).collect::<Vec<_>>(),
        [preflight::Check::Subject]
    );
    assert!(
        !preflight::can_schedule(&blockers),
        "nor is a stack scheduled"
    );
    // An existing subject's name typed is not a choice; choosing it is.
    ws.set_subjects(vec![SubjectChoice {
        id: 7,
        name: "Blue weevil".into(),
        detail: "Bugs · 2 stacks".into(),
    }]);
    ws.station.plan.subject = "blue weevil".into();
    assert!(sent(&mut ws, PlanIntent::Start).is_none());
    ws.set_plan_subject(7, "Blue weevil");
    assert!(matches!(
        sent(&mut ws, PlanIntent::Start),
        Some(Command::Start {})
    ));
    // A new subject, named: the capture that starts takes the names.
    ws.clear_plan_subject();
    ws.station.plan.subject = "Harvestman".into();
    ws.station.plan.stack_name = "Dorsal".into();
    let run = PathBuf::from("D:/Captures/stack-1795400000000-1");
    let mut capturing = ready();
    capturing["phase"] = json!("capturing");
    capturing["editable"] = json!(false);
    let mut running = snapshot(capturing.clone());
    running.in_progress = Some(crate::capture_client::InProgress {
        folder: run.clone(),
        idle: Duration::ZERO,
        test: false,
    });
    ws.connection.as_ref().unwrap().replace(running.clone());
    ws.poll_station(&running);
    let names = ws.run_names(&run).expect("the capture took the names");
    assert_eq!(
        (names.subject.as_str(), names.stack.as_str(), names.chosen),
        ("Harvestman", "Dorsal", None)
    );
    assert_eq!(ws.station.plan.subject, "Harvestman", "kept while it runs");
    // It ends and is reviewed: still named. Back to planning: unnamed.
    let mut complete = capturing;
    complete["phase"] = json!("complete");
    complete["editable"] = json!(true);
    let ended = snapshot(complete);
    ws.connection.as_ref().unwrap().replace(ended.clone());
    ws.poll_station(&ended);
    assert_eq!(ws.station_mode(), StationMode::Flight);
    assert_eq!(ws.station.plan.subject, "Harvestman");
    ws.apply_flight(&ended, FlightIntent::Done);
    ws.poll_station(&ended);
    assert_eq!(
        (
            ws.station.plan.subject.as_str(),
            ws.station.plan.stack_name.as_str(),
            ws.station.plan.chosen
        ),
        ("", "", None),
        "the next capture starts a new, unnamed subject"
    );
    assert_eq!(ws.run_names(&run).unwrap().subject, "Harvestman");
    assert!(
        preflight::start_blockers(&ended, &ws)
            .iter()
            .any(|b| b.check == preflight::Check::Subject)
    );
    // A test shot makes no stack: it does not ask for a subject.
    assert!(matches!(
        sent(&mut ws, PlanIntent::TestShot),
        Some(Command::CapturePositions {
            kind: PositionsKind::Test,
            ..
        })
    ));
}
