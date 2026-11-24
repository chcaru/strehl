use super::*;
use serde_json::json;
use std::{
    collections::BTreeSet,
    path::PathBuf,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};
use strehl_capture::{
    session::{Command, CommandRequest, Controls, Session},
    worker::Worker,
};

fn demo_session(root: &std::path::Path) -> Session {
    Session::new(
        Arc::new(Worker::new(PathBuf::new(), true)),
        Arc::new(Mutex::new(Controls::new(root.into()))),
        true,
    )
}

fn send(session: &Session, id: &str, command: Command) {
    let state = session.state();
    session
        .dispatch(CommandRequest {
            id: id.into(),
            camera_revision: state["camera_revision"].as_u64().unwrap(),
            plan_revision: state["plan_revision"].as_u64().unwrap(),
            sequence_id: state["sequence_id"].as_u64().unwrap(),
            command,
        })
        .unwrap();
}

fn until(session: &Session, predicate: impl Fn(&HostState) -> bool) -> (Value, HostState) {
    let end = Instant::now() + Duration::from_secs(20);
    loop {
        let state = session.state();
        let host = HostState::parse(&state).unwrap_or_else(|e| panic!("{e}: {state}"));
        if predicate(&host) {
            return (state, host);
        }
        assert!(Instant::now() < end, "{state}");
        std::thread::sleep(Duration::from_millis(10));
    }
}

fn keys(state: &Value) -> BTreeSet<String> {
    state.as_object().unwrap().keys().cloned().collect()
}

/// The host's own state, from its simulator, reads into the typed state in
/// every phase the desktop drives it through, and names exactly the keys the
/// desktop knows: a field the host adds or renames fails here.
#[test]
fn the_simulators_state_reads_typed_through_a_whole_capture() {
    let temp = tempfile::tempdir().unwrap();
    let session = demo_session(temp.path());
    // `starting` is sent only while a capture starts.
    let known: BTreeSet<String> = KNOWN_KEYS
        .iter()
        .filter(|k| **k != "starting")
        .map(|k| k.to_string())
        .collect();
    let (state, host) = until(&session, |_| true);
    assert_eq!(keys(&state), known);
    assert_eq!(host.phase, HostPhase::Disconnected);
    assert!(!host.connected && !host.editable);
    assert_eq!(
        host.capabilities,
        Capabilities {
            test_shot: true,
            exposure_check: true,
            max_retakes: true,
            queue_retakes: true,
            new_plan: true,
            subject: true,
        }
    );
    assert_eq!(host.error_correction, Some(false));
    assert!(host.demo);
    // h-retake: the setting and nothing in hand.
    assert_eq!(host.max_retakes(), 2);
    let retakes = host.retakes.as_ref().unwrap();
    assert_eq!((retakes.max, retakes.limit), (Some(2), Some(5)));
    assert!(retakes.queued.is_empty() && retakes.followup.is_none());
    assert!(!host.takes_manual_retakes(), "no capture yet");

    send(&session, "connect-typed", Command::Connect {});
    let (state, host) = until(&session, |h| h.phase == HostPhase::Ready && !h.busy);
    assert_eq!(keys(&state), known);
    assert!(host.connected && host.editable);
    assert_eq!(host.camera_model.as_deref(), Some("Simulator"));
    assert_eq!(host.pixel_shift_options, vec![1, 4]);
    let exposure = host.exposure.as_ref().unwrap();
    assert_eq!(exposure.mode.as_deref(), Some("M"));
    assert_eq!(exposure.problem, None);
    assert_eq!(exposure.iso_options, vec![100, 200, 400, 800, 1600]);
    assert_eq!(
        Some(exposure.shutter.unwrap()),
        state["exposure"]["shutter"].as_u64()
    );
    assert_eq!(host.camera_revision, state["camera_revision"].as_u64());
    assert_eq!(host.position, state["position"].as_u64().map(|p| p as u16));
    let (state, host) = until(&session, |h| h.preview.available);
    assert_eq!(
        host.preview.generation,
        state["preview"]["generation"].as_u64()
    );
    assert_eq!(
        host.preview.width,
        state["preview"]["width"].as_u64().map(|w| w as u32)
    );

    send(&session, "focus-typed", Command::Focus { target: 60500 });
    until(&session, |h| h.position == Some(60500) && !h.busy);
    send(&session, "mark-typed-start", Command::Mark { start: true });
    send(&session, "focus-typed-2", Command::Focus { target: 60503 });
    until(&session, |h| h.position == Some(60503) && !h.busy);
    send(&session, "mark-typed-end", Command::Mark { start: false });
    let (state, host) = until(&session, |h| h.end_set);
    assert!(host.bounds_set());
    assert_eq!(host.planned, Some(4));
    assert_eq!(host.plan_bounds(), (60500, 60503));
    assert_eq!(host.initial_seconds, state["initial_seconds"].as_f64());
    assert_eq!(host.plan_error, None);

    send(&session, "start-typed", Command::Start {});
    let (state, host) = until(&session, |h| h.phase.capturing());
    // The approach may be under way: `starting`, read typed when sent.
    let mut sent = keys(&state);
    assert_eq!(sent.remove("starting"), host.starting.is_some());
    assert_eq!(sent, known);
    assert!(host.phase.active());
    assert_eq!(host.total, 4);
    assert!(host.timer.is_some());
    let (_, host) = until(&session, |h| h.phase == HostPhase::Complete && !h.busy);
    assert_eq!(host.completed, 4);
    assert!(!host.phase.active());
}

/// An older host lacks the newer fields: it reads as "not supported", never
/// as an error.
#[test]
fn an_older_hosts_state_reads_with_its_newer_fields_absent() {
    let old = json!({"camera_revision":3,"plan_revision":2,"sequence_id":1,"phase":"ready",
        "connected":true,"busy":false,"editable":true,"message":"Connected","demo":false,"power":null,
        "position":30000,"plan":{"start":0,"end":0,"step":1,"settle_ms":500,"approach":128,"capture_timeout_s":120},
        "start_set":false,"end_set":false,"roi":{"x":0.1,"y":0.1,"width":0.8,"height":0.8},
        "planned":null,"plan_error":null,"initial_seconds":null,"completed":0,"saved":null,"total":0,
        "timer":null,"pending_control":0,"storage":{"mode":"camera-sd"},"raw_max_bytes":80000000,
        "shots_per_plane":1,"pixel_shift_options":null,"camera_model":"ILCE-7CM2","failure":null,
        "preview":{"available":true,"fresh":true,"generation":9},
        "exposure":{"iso":100,"shutter":65546,"iso_options":[100],"shutter_options":[65546],"writable":true}});
    let host = HostState::parse(&old).unwrap();
    assert_eq!(host.capabilities, Capabilities::default());
    assert_eq!(
        host.error_correction, None,
        "no error correction on this host"
    );
    assert_eq!(host.exposure.as_ref().unwrap().mode, None);
    assert_eq!(host.exposure_problem(), None);
    // h-retake: an older host retakes twice and takes none by hand.
    assert_eq!(host.retakes, None);
    assert_eq!(host.max_retakes(), 2);
    assert!(!host.takes_manual_retakes() && host.retakes_in_hand().is_empty());
    assert!(host.pixel_shift_options.is_empty() && !host.offers_four_shot());
    assert!(host.schedule.is_none() && host.usb_speed_mbps.is_none());
    assert_eq!(host.shots(), 1);
    assert_eq!(
        HostState::parse(&Value::Null).unwrap(),
        HostState::default()
    );
}

/// A field that decides what may be sent fails the parse when it has another
/// form; a display-only field reads as absent; a phase from a newer host
/// reads as unknown.
#[test]
fn control_fields_are_strict_and_display_fields_lenient() {
    let base = json!({"camera_revision":3,"plan_revision":2,"sequence_id":1,"phase":"ready",
        "connected":true,"busy":false,"editable":true});
    for (key, bad) in [
        ("editable", json!("yes")),
        ("camera_revision", json!(-1)),
        ("start_set", json!(1)),
        ("failure", json!("broken")),
        ("capabilities", json!({"test_shot":"yes"})),
    ] {
        let mut state = base.clone();
        state[key] = bad;
        let error = HostState::parse(&state).unwrap_err();
        assert!(!error.is_empty(), "{key}");
    }
    let mut state = base.clone();
    state["samples"] = json!([{"position":5,"scores":[1.0,null]}]);
    state["suggestion"] = json!("not an object");
    state["magnifier_ratios"] = json!({"weird":true});
    state["power"] = json!({"light":"offline","available":true});
    state["storage"] = json!({"receipt":{"path":7},"pending_frames":3});
    let host = HostState::parse(&state).unwrap();
    assert_eq!(host.samples[0].scores, vec![Some(1.0), None]);
    assert!(host.suggestion.is_none() && host.magnifier_ratios.is_empty());
    let power = host.power.as_ref().unwrap();
    assert!(power.available && power.light == Outlet::default());
    assert_eq!(host.storage.receipt, None);
    assert_eq!(host.storage.pending_frames, Some(3));
    state["phase"] = json!("levitating");
    assert_eq!(HostState::parse(&state).unwrap().phase, HostPhase::Unknown);
}

#[cfg(windows)]
#[test]
fn the_last_receipt_names_its_run_folder() {
    let state = json!({"storage":{"mode":"host-pc",
        "receipt":{"path":r"\\?\D:\Captures\stack-1\frame-000001.ARW.straw"}}});
    let host = HostState::parse(&state).unwrap();
    assert_eq!(
        host.last_receipt_run(),
        Some(PathBuf::from(r"D:\Captures\stack-1"))
    );
    assert_eq!(HostState::default().last_receipt_run(), None);
}
