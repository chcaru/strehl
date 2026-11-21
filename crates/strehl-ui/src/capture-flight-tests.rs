use super::*;
use eframe::egui::{Event, FullOutput, PointerButton, Pos2, RawInput};
use serde_json::json;
use std::time::Instant;

fn snapshot(state: Value) -> Snapshot {
    let mut s = Snapshot {
        online: true,
        observed: Some(Instant::now()),
        receiver: json!({"ok":true,"free_bytes":355_000_000_000u64}),
        ..Default::default()
    };
    s.set_state(state);
    s
}

fn capturing() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"capturing","connected":true,
        "busy":false,"editable":false,"completed":61,"total":96,"shots_per_plane":4,"position":37520,
        "timer":{"elapsed":341.6,"remaining":198.0},"camera_model":"ILCE-7CR",
        "storage":{"mode":"host-pc","captured_frames":244,"saved_frames":242,"pending_frames":2,
            "receipt":{"wire_MB_per_second":38.2}}})
}

fn journal() -> Progress {
    let lines = [
        r#"{"plane":39,"target":37252,"group_id":"g39","verdict":"demote","reason":"x","retake":true,"members":4,"seconds":2.0}"#,
        r#"{"plane":39,"target":37252,"group_id":"g39b","verdict":"pass","retake":false,"members":4,"seconds":2.2}"#,
        r#"{"plane":58,"target":37499,"group_id":"g58","verdict":"pass","retake":false,"members":4,"seconds":1.4}"#,
        r#"{"plane":59,"target":37506,"group_id":"g59","verdict":"pass","retake":false,"members":4,"seconds":2.0}"#,
        r#"{"plane":60,"target":37513,"group_id":"g60","verdict":"failed","reason":"decode: truncated","retake":true,"members":4,"seconds":1.9}"#,
        r#"{"plane":61,"target":37520,"group_id":"g61","verdict":"pass","retake":false,"members":4,"seconds":2.1}"#,
    ];
    super::super::follow::progress(&lines.join("\n"))
}

#[test]
fn the_health_column_reads_transfer_checks_disk_and_rig() {
    let s = snapshot(capturing());
    let p = journal();
    let lines = health(&s, Some(&p), true);
    assert_eq!(lines[0].title, "Transfer");
    assert_eq!(
        lines[0].text,
        "242 of 244 RAWs on this PC · 2 behind · 38 MB/s on Wi-Fi"
    );
    assert_eq!(lines[0].mark, Mark::Ok);
    assert!((lines[0].fraction.unwrap() - 242.0 / 244.0).abs() < 1e-6);
    assert_eq!(
        lines[1].text,
        "5 planes checked · 3 passed first time · 1 retaken · 1 need attention"
    );
    assert_eq!(lines[1].mark, Mark::Warn);
    assert!(lines[2].text.ends_with("355 GB free"));
    assert_eq!(lines[3].title, "Rig");
    let off = health(&s, None, false);
    assert!(off[1].text.starts_with("Off"));
    let (mark, word) = needs_you(&s, &lines);
    assert_eq!((mark, word), (Mark::Warn, "Worth a look"));
}

#[test]
fn the_last_planes_say_their_verdicts() {
    let p = journal();
    let recent = recent_planes(&p, 5);
    let planes: Vec<u64> = recent.iter().map(|r| r.0).collect();
    assert_eq!(planes, [61, 60, 59, 58, 39]);
    assert_eq!(recent[0].1, Mark::Ok);
    assert_eq!(recent[0].2, "four shots agree");
    assert_eq!(recent[0].3.as_deref(), Some("2.1 s"));
    assert_eq!(
        (recent[1].1, recent[1].2.as_str()),
        (Mark::Bad, "decode: truncated")
    );
    assert_eq!(recent[4].1, Mark::Warn, "retaken");
    assert!(recent[4].2.contains("second try passed"));
}

#[test]
fn the_rail_ticks_follow_the_planes() {
    let s = snapshot(capturing());
    let p = journal();
    let positions: Vec<u16> = (0..96).map(|i| 37100 + i * 7).collect();
    let ticks = flight_ticks(positions, &s, Some(&p));
    assert_eq!(ticks.states.len(), 96);
    assert_eq!(ticks.states[38], TickState::Retaken, "plane 39");
    assert_eq!(ticks.states[59], TickState::Attention, "plane 60 failed");
    assert_eq!(
        ticks.states[60],
        TickState::Checked,
        "plane 61 passed its check"
    );
    assert_eq!(ticks.states[0], TickState::Checked);
    assert_eq!(ticks.states[61], TickState::ToCome);
    // Without the checker: 242 of 244 RAWs here, so plane 61 is on the host.
    let positions: Vec<u16> = (0..96).map(|i| 37100 + i * 7).collect();
    let plain = flight_ticks(positions, &s, None);
    assert_eq!(plain.states[59], TickState::Checked);
    assert_eq!(plain.states[60], TickState::OnHost);
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}
/// Frame times only move forward within a context.
fn tick() -> f64 {
    CLOCK.with(|c| {
        c.set(c.get() + 0.05);
        c.get()
    })
}

fn frame(
    ctx: &egui::Context,
    input: &FlightInputs<'_>,
    _time: f64,
    events: Vec<Event>,
) -> (FullOutput, Vec<FlightIntent>) {
    let time = tick();
    let mut intents = Vec::new();
    let palette = CapturePalette::default();
    let out = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(348.0, 982.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| intents = inspector(ui, input, &palette));
        },
    );
    (out, intents)
}

fn click(ctx: &egui::Context, input: &FlightInputs<'_>, label: &str) -> Vec<FlightIntent> {
    let (out, _) = frame(ctx, input, 0.0, vec![]);
    let at = out
        .shapes
        .iter()
        .find_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == label => {
                Some(t.visual_bounding_rect().center())
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("{label} is not drawn"));
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    let mut all = frame(ctx, input, 0.1, vec![Event::PointerMoved(at), press(true)]).1;
    all.extend(frame(ctx, input, 0.2, vec![press(false)]).1);
    all
}

/// Stop asks first; the confirmation stops; Glance opens glance.
#[test]
fn stop_asks_first_and_glance_opens() {
    let ctx = egui::Context::default();
    let s = snapshot(capturing());
    let p = journal();
    let mut input = FlightInputs {
        s: &s,
        progress: Some(&p),
        checking: true,
        proof: None,
        latest: None,
        stack_when_done: true,
        power_down: Some(true),
        confirm_stop: false,
    };
    assert_eq!(click(&ctx, &input, "Stop…"), [FlightIntent::AskStop]);
    assert_eq!(click(&ctx, &input, "Pause"), [FlightIntent::Pause]);
    assert_eq!(click(&ctx, &input, "Glance"), [FlightIntent::Glance]);
    input.confirm_stop = true;
    assert_eq!(click(&ctx, &input, "Stop now"), [FlightIntent::Stop]);
    assert_eq!(click(&ctx, &input, "Keep going"), [FlightIntent::KeepGoing]);
}

/// The canvas: G opens glance, and its text says the headline.
#[test]
fn the_canvas_reads_the_headline_and_g_opens_glance() {
    let ctx = egui::Context::default();
    let s = snapshot(capturing());
    let p = journal();
    let input = FlightInputs {
        s: &s,
        progress: Some(&p),
        checking: true,
        proof: None,
        latest: None,
        stack_when_done: true,
        power_down: None,
        confirm_stop: false,
    };
    let palette = CapturePalette::default();
    let mut intents = Vec::new();
    let out = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 855.0))),
            events: vec![Event::Key {
                key: egui::Key::G,
                physical_key: None,
                pressed: true,
                repeat: false,
                modifiers: Default::default(),
            }],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| intents = canvas(ui, &input, &palette));
        },
    );
    assert_eq!(intents, [FlightIntent::Glance]);
    let texts: Vec<String> = out
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            egui::Shape::Text(t) => Some(t.galley.text().to_owned()),
            _ => None,
        })
        .collect();
    for want in [
        "61",
        "of 96",
        "3:18",
        "On track",
        "244 of 384 RAWs taken",
        "four shots agree",
    ] {
        assert!(texts.iter().any(|t| t == want), "{want}: {texts:?}");
    }
    assert!(texts.iter().any(|t| t.contains("not the RAW stack")));
}
