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
    ws.apply_flight(&s, FlightIntent::ShowPlane(39));
    assert_eq!(ws.take_show_plane(), Some(39));
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
