use super::*;
use serde_json::json;

fn online(state: Value) -> Value {
    json!({"online":true,"pending":false,"state":state,
        "receiver":{"ok":true,"folder":"D:\\StrehlCaptures","free_bytes":398_000_000_000_u64},
        "receiver_error":null,"connection_error":null,"command_error":null})
}

fn ready_state() -> Value {
    json!({"connected":true,"camera_model":"ILCE-7CR","usb_speed_mbps":5000,"editable":true,
        "phase":"idle","camera_revision":4,"plan_revision":9,"sequence_id":2,
        "power":{"available":true,"manage_stack":true,"can_manage":true,"can_start_camera":false,
            "can_stop_camera":true,"light":{"on":true,"watts":41.2},"camera":{"on":true,"watts":3.1}}})
}

#[test]
fn an_unopened_connection_is_unknown_not_off() {
    let rig = RigSummary::from_snapshot(&json!({"online":false,"initialized":false}));
    assert!(!rig.initialized);
    assert_eq!(rig.lamp(), Lamp::Unknown);
    assert_eq!(rig.headline(), ("Rig".into(), "not connected".into()));
    let offline = RigSummary::from_snapshot(&json!({"online":false,"state":null}));
    assert_eq!(offline.lamp(), Lamp::Offline);
}

#[test]
fn a_ready_rig_names_its_camera_and_light() {
    let rig = RigSummary::from_snapshot(&online(ready_state()));
    assert_eq!(rig.lamp(), Lamp::Ready);
    assert_eq!(rig.camera_name().as_deref(), Some("A7CR"));
    assert_eq!(rig.headline(), ("A7CR".into(), "light 41 W".into()));
    assert_eq!(rig.usb_warning(), None);
    assert_eq!(lamp_mark(rig.lamp()), Mark::Fine);
}

#[test]
fn a_slow_link_a_stopped_receiver_or_a_fault_needs_a_look() {
    let mut state = ready_state();
    state["usb_speed_mbps"] = json!(480);
    let slow = RigSummary::from_snapshot(&online(state));
    assert_eq!(slow.lamp(), Lamp::Warn);
    assert!(slow.usb_warning().unwrap().contains("USB 480"));
    let mut snapshot = online(ready_state());
    snapshot["receiver"]["ok"] = json!(false);
    assert_eq!(RigSummary::from_snapshot(&snapshot).lamp(), Lamp::Warn);
    let mut state = ready_state();
    state["failure"] = json!({"message":"Camera stopped answering"});
    let fault = RigSummary::from_snapshot(&online(state));
    assert_eq!(fault.lamp(), Lamp::Warn);
    assert_eq!(fault.failure.as_deref(), Some("Camera stopped answering"));
}

#[test]
fn a_capture_in_flight_shows_the_light_and_its_count_only_without_one() {
    let mut state = ready_state();
    state["phase"] = json!("capturing");
    state["completed"] = json!(61);
    state["total"] = json!(96);
    let rig = RigSummary::from_snapshot(&online(state.clone()));
    assert_eq!(rig.lamp(), Lamp::Busy);
    // The activity shows the count; the rig says the light.
    assert_eq!(rig.headline(), ("A7CR".into(), "light 41 W".into()));
    let mut dark = RigSummary::from_snapshot(&online(state));
    dark.light = Default::default();
    assert_eq!(dark.headline(), ("A7CR".into(), "61 / 96".into()));
}

#[test]
fn requests_carry_the_hosts_revisions_and_the_existing_commands() {
    let snapshot = online(ready_state());
    let built = request(&snapshot, RigCommand::PowerPlan(false).command()).unwrap();
    assert_eq!(
        (
            built.camera_revision,
            built.plan_revision,
            built.sequence_id
        ),
        (4, 9, 2)
    );
    assert!(!built.id.is_empty());
    // The host protocol's own encoding (`op`-tagged, snake case).
    for (command, expected) in [
        (RigCommand::ConnectCamera, json!({"op":"connect"})),
        (RigCommand::DisconnectCamera, json!({"op":"disconnect"})),
        (
            RigCommand::Power(OutletKind::Light, false),
            json!({"op":"power","device":"light","on":false}),
        ),
        (
            RigCommand::Power(OutletKind::Camera, true),
            json!({"op":"power","device":"camera","on":true}),
        ),
        (
            RigCommand::PowerPlan(true),
            json!({"op":"power_plan","enabled":true}),
        ),
    ] {
        assert_eq!(serde_json::to_value(command.command()).unwrap(), expected);
    }
    let offline = json!({"online":false,"state":ready_state()});
    assert!(request(&offline, Command::Connect {}).is_err());
}

fn paint(
    ctx: &egui::Context,
    rig: &RigSummary,
    time: f64,
    events: Vec<egui::Event>,
) -> (egui::FullOutput, Option<RigAction>) {
    let mut action = None;
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(800.0, 700.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| action = popover(ui, rig));
        },
    );
    (output, action)
}

fn text_at(output: &egui::FullOutput, needle: &str) -> egui::Pos2 {
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == needle => {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("missing {needle}"))
}

fn click(ctx: &egui::Context, rig: &RigSummary, at: egui::Pos2) -> Option<RigAction> {
    let press = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    paint(
        ctx,
        rig,
        0.1,
        vec![egui::Event::PointerMoved(at), press(true)],
    );
    paint(ctx, rig, 0.15, vec![press(false)]).1
}

#[test]
fn the_popover_sends_the_existing_power_and_connection_commands() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let rig = RigSummary::from_snapshot(&online(ready_state()));
    let (output, _) = paint(&ctx, &rig, 0.0, vec![]);
    for needle in [
        "Camera",
        "Light",
        "Power for a stack",
        "Camera host",
        "Receiver on this PC",
        "Phone remote",
    ] {
        text_at(&output, needle);
    }
    assert_eq!(
        click(&ctx, &rig, text_at(&output, "Off")),
        Some(RigAction::Command(RigCommand::Power(
            OutletKind::Light,
            false
        )))
    );
    let (output, _) = paint(&ctx, &rig, 0.3, vec![]);
    assert_eq!(
        click(&ctx, &rig, text_at(&output, "Shut down")),
        Some(RigAction::Command(RigCommand::Power(
            OutletKind::Camera,
            false
        )))
    );
    let unopened = RigSummary::from_snapshot(&json!({"online":false,"initialized":false}));
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let (output, _) = paint(&ctx, &unopened, 0.0, vec![]);
    assert_eq!(
        click(&ctx, &unopened, text_at(&output, "Connect")),
        Some(RigAction::Connect)
    );
}
