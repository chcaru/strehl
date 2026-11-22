//! The capture screen's confirmations, its fault colour and the first
//! pre-flight blocker beside Start (Studio 2 P0 items 2, 4 and 7).
use super::*;
use eframe::egui::{Event, FullOutput, Pos2, RawInput};

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

fn capturing() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"capturing","connected":true,
        "busy":false,"editable":false,"position":30000,"start_set":true,"end_set":true,"planned":10,
        "total":10,"completed":3,"shots_per_plane":1,"pending_control":0})
}

fn ready() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"ready","connected":true,
        "busy":false,"editable":true,"position":30000,"start_set":true,"end_set":false,"planned":null,
        "shots_per_plane":1,"pending_control":0,
        "power":{"light":{"on":true,"watts":10.0},"camera":{"on":true,"watts":2.0},"available":true,
            "can_start_camera":false,"can_stop_camera":true,"can_manage":true,"manage_stack":false}})
}

fn frame(
    ctx: &egui::Context,
    time: f64,
    events: Vec<Event>,
    mut paint: impl FnMut(&mut egui::Ui),
) -> FullOutput {
    let raw = RawInput {
        screen_rect: Some(egui::Rect::from_min_size(
            Pos2::ZERO,
            egui::vec2(1400.0, 900.0),
        )),
        time: Some(time),
        events,
        ..Default::default()
    };
    ctx.run(raw, |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| paint(ui));
    })
}

/// The centre of the first painted text that is exactly `label`.
fn text_at(output: &FullOutput, label: &str) -> Option<Pos2> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Text(text) if text.galley.text() == label => {
            Some(text.visual_bounding_rect().center())
        }
        _ => None,
    })
}

fn color_of(output: &FullOutput, label: &str) -> Option<egui::Color32> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Text(text) if text.galley.text() == label => {
            Some(text.galley.job.sections[0].format.color)
        }
        _ => None,
    })
}

fn press(at: Pos2) -> Vec<Event> {
    vec![
        Event::PointerMoved(at),
        Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed: true,
            modifiers: egui::Modifiers::NONE,
        },
    ]
}

fn release(at: Pos2) -> Vec<Event> {
    vec![Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed: false,
        modifiers: egui::Modifiers::NONE,
    }]
}

/// Clicks `label` in what `paint` draws; panics when it is not drawn.
fn click(
    ctx: &egui::Context,
    time: &mut f64,
    label: &str,
    mut paint: impl FnMut(&mut egui::Ui),
) -> FullOutput {
    let shown = frame(ctx, *time, vec![], &mut paint);
    let at = text_at(&shown, label).unwrap_or_else(|| panic!("{label} is not drawn"));
    *time += 0.05;
    frame(ctx, *time, press(at), &mut paint);
    *time += 0.05;
    let out = frame(ctx, *time, release(at), &mut paint);
    *time += 0.05;
    out
}

fn workspace() -> (tempfile::TempDir, CaptureWorkspace) {
    let dir = tempfile::tempdir().unwrap();
    let mut ui = CaptureWorkspace::new(Some(dir.path().join("capture.json")));
    // A new subject named, so only the rig decides Start.
    ui.station.plan.subject = "Harvestman".into();
    (dir, ui)
}

/// Disconnect in the connection settings asks first; only "Disconnect now"
/// tries to send (here refused: no connection).
#[test]
fn disconnect_needs_a_confirming_click() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let (_dir, mut ws) = workspace();
    let mut state = ready();
    state["end_set"] = json!(true);
    let s = snapshot(state);
    let mut time = 0.0;
    click(&ctx, &mut time, "Disconnect…", |ui| {
        ws.connection_ui(ui, &s)
    });
    assert_eq!(ws.confirm, Some(Confirm::Disconnect));
    assert!(ws.error.is_none(), "the first click sends nothing");
    click(&ctx, &mut time, "Disconnect now", |ui| {
        ws.connection_ui(ui, &s)
    });
    assert_eq!(ws.error.as_deref(), Some("Open Capture first"));
}

/// A fault is drawn in the failure red: the plan's rig step says it, and
/// the strip's Rig chip is the red diamond (P0 item 4).
#[test]
fn a_fault_is_drawn_red() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let (_dir, mut ws) = workspace();
    let mut state = ready();
    state["phase"] = json!("fault");
    state["editable"] = json!(false);
    state["failure"] = json!({"message":"The camera stopped answering","exposure_uncertain":false,"can_reconnect":true});
    let s = snapshot(state);
    let (connection, _inbox) = Connection::detached(s.clone());
    ws.connection = Some(connection);
    let out = frame(&ctx, 0.0, vec![], |ui| ws.station_inspector(ui));
    let palette = style::CapturePalette::default();
    assert_eq!(
        color_of(&out, "The camera stopped answering"),
        Some(palette.bad)
    );
    let blockers = preflight::start_blockers(&s, &ws);
    let chips = preflight::strip_chips(&s, &blockers);
    assert_eq!(chips[0].label, "Rig");
    assert_eq!(chips[0].mark, style::Mark::Bad);
}

/// A blocked Start says why: the strip shows the first blocker, and the
/// plan's Start stays disabled until it is resolved.
#[test]
fn start_shows_its_first_blocker() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let (_dir, mut ws) = workspace();
    let s = snapshot(ready());
    let (connection, _inbox) = Connection::detached(s.clone());
    ws.connection = Some(connection);
    let out = frame(&ctx, 0.0, vec![], |ui| ws.station_strip(ui));
    assert!(text_at(&out, "Mark the end of the focus range").is_some());
    let mut state = ready();
    state["end_set"] = json!(true);
    state["planned"] = json!(10);
    let s = snapshot(state);
    assert!(preflight::start_blockers(&s, &ws).is_empty());
    ws.connection.as_ref().unwrap().replace(s);
    let out = frame(&ctx, 0.1, vec![], |ui| ws.station_strip(ui));
    assert!(text_at(&out, "Mark the end of the focus range").is_none());
    assert!(text_at(&out, "Ready").is_some());
}

/// The success notice is read once per notice (P0 item 9).
#[test]
fn a_success_notice_is_unread_once() {
    let (_dir, mut ws) = workspace();
    assert_eq!(ws.unread_notice(), None, "no connection, no notice");
    let mut s = snapshot(ready());
    s.notice = Some("Request accepted".into());
    s.notice_id = 1;
    let (connection, _inbox) = Connection::detached(s.clone());
    ws.connection = Some(connection);
    assert_eq!(ws.unread_notice().as_deref(), Some("Request accepted"));
    assert_eq!(ws.unread_notice(), None, "read");
    s.notice = Some("Connection saved".into());
    s.notice_id = 2;
    ws.connection.as_ref().unwrap().replace(s);
    assert_eq!(ws.unread_notice().as_deref(), Some("Connection saved"));
}

/// 1 Hz with the station closed and nothing running; 5 Hz while it is shown
/// or a sequence runs; the shell's word overrides the fallback.
#[test]
fn the_cadence_follows_the_station_and_the_sequence() {
    let (_dir, mut ws) = workspace();
    let (connection, _inbox) = Connection::detached(snapshot(ready()));
    ws.connection = Some(connection);
    ws.poll_follow(None);
    assert_eq!(ws.cadence(), Some(Cadence::Background));
    ws.shown = true;
    ws.poll_follow(None);
    assert_eq!(
        ws.cadence(),
        Some(Cadence::Live),
        "show() ran since the last poll"
    );
    ws.poll_follow(None);
    assert_eq!(ws.cadence(), Some(Cadence::Background));
    ws.connection
        .as_ref()
        .unwrap()
        .replace(snapshot(capturing()));
    ws.poll_follow(None);
    assert_eq!(ws.cadence(), Some(Cadence::Sequence));
    ws.set_station_open(true);
    ws.poll_follow(None);
    assert_eq!(ws.cadence(), Some(Cadence::Live));
}

/// A test shot is one position at the current focus with power kept on,
/// sent as `kind: "test"` only to a host that says it accepts it; while it
/// runs, Start and a calibration wait.
#[test]
fn a_test_shot_names_its_kind_only_to_a_host_that_accepts_it() {
    for supported in [true, false] {
        let (_dir, mut ws) = workspace();
        let mut state = ready();
        if supported {
            state["capabilities"] = json!({"test_shot":true});
        }
        let (connection, inbox) = Connection::detached(snapshot(state));
        ws.connection = Some(connection);
        ws.test_shot().unwrap();
        let request = inbox.command().unwrap();
        match request.command {
            Command::CapturePositions {
                positions,
                keep_power_on,
                kind,
            } => {
                assert_eq!(positions, [30000]);
                assert!(keep_power_on);
                assert_eq!(
                    kind,
                    if supported {
                        PositionsKind::Test
                    } else {
                        PositionsKind::Positions
                    }
                );
            }
            other => panic!("{other:?}"),
        }
        assert_eq!(ws.test_shot.sequence(), Some(3));
        assert!(ws.test_shot().is_err(), "one at a time");
        assert!(ws.calibrate().is_err());
        assert!(
            ws.start_blockers()
                .iter()
                .any(|b| b.check == preflight::Check::TestShot)
        );
        ws.stop_test_shot();
        assert_eq!(ws.unfollowed_sequence, Some(3));
        assert!(!ws.test_shot.running());
    }
}
