//! h-retake: retakes asked of the camera host, and the retake setting.
use super::*;
use crate::capture_client::TestInbox;
use serde_json::{Value, json};

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

/// A capture in flight on a host that takes retakes by hand (`new`) or an
/// older one.
fn capturing(new: bool) -> Value {
    let mut state = json!({"camera_revision":9,"plan_revision":3,"sequence_id":5,"phase":"capturing",
        "connected":true,"busy":false,"editable":false,"completed":12,"total":40,"shots_per_plane":4,
        "plan":{"start":37100,"end":37373,"step":7,"settle_ms":500,"approach":128,"capture_timeout_s":120},
        "error_correction":true,"capabilities":{"test_shot":true,"exposure_check":true}});
    if new {
        state["capabilities"]["max_retakes"] = json!(true);
        state["capabilities"]["queue_retakes"] = json!(true);
        state["retakes"] =
            json!({"max":3,"limit":5,"accepted":true,"queued":[],"run":"stack-1","followup":null});
    }
    state
}

fn workspace(state: Value) -> (tempfile::TempDir, CaptureWorkspace, TestInbox, Snapshot) {
    let dir = tempfile::tempdir().unwrap();
    let mut ws = CaptureWorkspace::new(Some(dir.path().join("capture.json")));
    let s = snapshot(state);
    let (connection, inbox) = Connection::detached(s.clone());
    ws.connection = Some(connection);
    (dir, ws, inbox, s)
}

/// "Retake" sends the host's `queue_retakes` for those planes; the plane is
/// shown as asked until the host holds it, its next try is checked, or (the
/// capture over and the host holding nothing) a moment has passed. An older
/// host is not asked: the user is told to update it.
#[test]
fn retakes_are_asked_of_the_host_and_shown_until_taken() {
    let (_dir, mut ws, inbox, s) = workspace(capturing(true));
    ws.apply_flight(&s, FlightIntent::QueueRetakes(vec![24, 25]));
    let sent = inbox.command().expect("sent");
    assert_eq!(
        serde_json::to_value(&sent.command).unwrap(),
        json!({"op":"queue_retakes","planes":[24,25]})
    );
    assert_eq!(sent.sequence_id, 5);
    assert_eq!(ws.error, None);
    let now = Instant::now();
    assert_eq!(
        retakes_in_hand(&s, &ws.station.asked, None, now),
        [24, 25],
        "asked, before the host says so"
    );
    // Plane 24's second try is checked: no longer in hand.
    let line = |plane: u64, attempt: u32| {
        json!({"plane":plane,"group_id":format!("g{plane}-{attempt}"),"verdict":"pass","retake":false})
            .to_string()
    };
    let journal = [line(24, 1), line(25, 1), line(24, 2)].join("\n");
    let p = super::super::follow::progress(&journal);
    ws.station.asked = vec![
        AskedRetake {
            plane: 24,
            tries: 1,
            at: now,
            sequence: Some(5),
        },
        AskedRetake {
            plane: 25,
            tries: 1,
            at: now,
            sequence: Some(5),
        },
    ];
    assert_eq!(retakes_in_hand(&s, &ws.station.asked, Some(&p), now), [25]);
    // Another capture's request is not this one's.
    let mut other = capturing(true);
    other["sequence_id"] = json!(6);
    assert!(retakes_in_hand(&snapshot(other), &ws.station.asked, Some(&p), now).is_empty());
    // Ended, the host holding nothing, after a moment: offered again.
    let mut ended = capturing(true);
    ended["phase"] = json!("complete");
    let ended = snapshot(ended);
    let later = now + Duration::from_secs(5);
    assert_eq!(
        retakes_in_hand(&ended, &ws.station.asked, Some(&p), now),
        [25]
    );
    assert!(retakes_in_hand(&ended, &ws.station.asked, Some(&p), later).is_empty());
    // The host's own queue and its retakes after the capture count too.
    let mut held = capturing(true);
    held["retakes"]["queued"] = json!([30]);
    held["retakes"]["followup"] = json!({"planes":[31,32,33],"taken":1,"skipped":0});
    assert_eq!(
        retakes_in_hand(&snapshot(held), &[], None, later),
        [30, 32, 33]
    );

    let (_dir, mut ws, inbox, s) = workspace(capturing(false));
    ws.apply_flight(&s, FlightIntent::QueueRetakes(vec![24]));
    assert!(inbox.command().is_none());
    assert!(
        ws.error
            .as_deref()
            .unwrap()
            .contains("cannot take retakes by hand")
    );
}

/// The retake setting goes with error correction's own command, and the
/// switch keeps it (an `error_correction` without it means two); an older
/// host is sent neither.
#[test]
fn the_retake_setting_travels_with_error_correction() {
    let mut ready = capturing(true);
    ready["phase"] = json!("ready");
    ready["editable"] = json!(true);
    let (_dir, mut ws, inbox, s) = workspace(ready.clone());
    let sent = |ws: &mut CaptureWorkspace, s: &Snapshot, intent: PlanIntent| {
        ws.apply_plan(s, intent);
        let request = inbox.command();
        ws.connection.as_ref().unwrap().replace(s.clone());
        request.map(|r| serde_json::to_value(r.command).unwrap())
    };
    assert_eq!(
        sent(&mut ws, &s, PlanIntent::SetMaxRetakes(4)),
        Some(json!({"op":"error_correction","enabled":true,"max_retakes":4}))
    );
    assert_eq!(
        sent(&mut ws, &s, PlanIntent::SetRetake(false)),
        Some(json!({"op":"error_correction","enabled":false,"max_retakes":3}))
    );
    let mut old = ready;
    old["capabilities"] = json!({"test_shot":true,"exposure_check":true});
    old.as_object_mut().unwrap().remove("retakes");
    let old = snapshot(old);
    assert_eq!(sent(&mut ws, &old, PlanIntent::SetMaxRetakes(4)), None);
    assert_eq!(
        sent(&mut ws, &old, PlanIntent::SetRetake(true)),
        Some(json!({"op":"error_correction","enabled":true}))
    );
    // The rig settings read the host's value, and none from an older host.
    let v = super::super::rig_settings::RigValues::read(&s, 500, true);
    assert_eq!(v.max_retakes, Some(3));
    let v = super::super::rig_settings::RigValues::read(&old, 500, true);
    assert_eq!(v.max_retakes, None);
}
