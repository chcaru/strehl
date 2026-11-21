//! The rig popover (implementation plan 7.1): camera, light, power for a
//! stack, the camera host, the receiver on this PC and the phone remote, read
//! from the capture client's public state. Its buttons send the host's
//! existing `Power`, `PowerPlan`, `Connect` and `Disconnect` commands; it adds
//! no protocol of its own.
use crate::studio_theme::{self, scale};
use crate::studio_widgets::{self as w, Mark};
use eframe::egui::{self, Color32, Ui};
use serde_json::Value;
use strehl_capture::{
    power::Outlet,
    session::{Command, CommandRequest},
};

/// What the top bar's lamp says about the rig.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Lamp {
    /// No connection to the camera host has been opened in this session.
    Unknown,
    /// The host does not answer.
    Offline,
    /// Online, camera off or not connected.
    Idle,
    /// Camera connected and nothing needs attention.
    Ready,
    /// Capturing or paused.
    Busy,
    /// A slow camera link, a stopped receiver, or a capture fault.
    Warn,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct OutletState {
    pub on: Option<bool>,
    pub watts: Option<f64>,
    pub error: Option<String>,
}

/// The parts of the capture client's public state the popover shows.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct RigSummary {
    /// A connection to the host exists in this session.
    pub initialized: bool,
    pub online: bool,
    pub pending: bool,
    pub demo: bool,
    pub editable: bool,
    pub camera_connected: bool,
    pub camera_model: Option<String>,
    pub usb_mbps: Option<u64>,
    pub phase: Option<String>,
    pub completed: Option<u64>,
    pub planned: Option<u64>,
    pub failure: Option<String>,
    pub power_available: bool,
    pub light: OutletState,
    pub camera_power: OutletState,
    pub manage_stack: bool,
    pub can_manage: bool,
    pub can_start_camera: bool,
    pub can_stop_camera: bool,
    pub receiver_ok: Option<bool>,
    pub receiver_folder: Option<String>,
    pub receiver_free: Option<u64>,
    pub receiver_error: Option<String>,
    pub connection_error: Option<String>,
    pub command_error: Option<String>,
}

fn text(value: &Value) -> Option<String> {
    value.as_str().filter(|s| !s.is_empty()).map(str::to_owned)
}
fn outlet(value: &Value) -> OutletState {
    OutletState {
        on: value["on"].as_bool(),
        watts: value["watts"].as_f64(),
        error: text(&value["error"]),
    }
}

impl RigSummary {
    /// From `CaptureWorkspace::snapshot()`.
    pub(crate) fn from_snapshot(snapshot: &Value) -> Self {
        let state = &snapshot["state"];
        let power = &state["power"];
        Self {
            initialized: snapshot["initialized"] != false,
            online: snapshot["online"] == true,
            pending: snapshot["pending"] == true,
            demo: state["demo"] == true,
            editable: state["editable"] == true,
            camera_connected: state["connected"] == true,
            camera_model: text(&state["camera_model"]),
            usb_mbps: state["usb_speed_mbps"].as_u64(),
            phase: text(&state["phase"]),
            completed: state["completed"].as_u64(),
            planned: state["total"]
                .as_u64()
                .or_else(|| state["planned"].as_u64()),
            failure: state["failure"]["message"]
                .as_str()
                .map(str::to_owned)
                .or_else(|| {
                    state["failure"]
                        .is_object()
                        .then(|| "Capture needs attention".into())
                }),
            power_available: power["available"] == true,
            light: outlet(&power["light"]),
            camera_power: outlet(&power["camera"]),
            manage_stack: power["manage_stack"] == true,
            can_manage: power["can_manage"] == true,
            can_start_camera: power["can_start_camera"] == true,
            can_stop_camera: power["can_stop_camera"] == true,
            receiver_ok: snapshot["receiver"]["ok"].as_bool(),
            receiver_folder: text(&snapshot["receiver"]["folder"]),
            receiver_free: snapshot["receiver"]["free_bytes"].as_u64(),
            receiver_error: text(&snapshot["receiver_error"]),
            connection_error: text(&snapshot["connection_error"]),
            command_error: text(&snapshot["command_error"]),
        }
    }
    /// A slow-link warning while the camera is connected.
    pub(crate) fn usb_warning(&self) -> Option<String> {
        self.usb_mbps
            .filter(|_| self.camera_connected)
            .and_then(|mbps| strehl_capture::worker::usb_link_warning(mbps as u32))
    }
    pub(crate) fn capturing(&self) -> bool {
        matches!(self.phase.as_deref(), Some("capturing" | "paused"))
    }
    pub(crate) fn lamp(&self) -> Lamp {
        if !self.initialized {
            Lamp::Unknown
        } else if !self.online {
            Lamp::Offline
        } else if self.failure.is_some()
            || self.usb_warning().is_some()
            || self.receiver_ok == Some(false)
        {
            Lamp::Warn
        } else if self.capturing() {
            Lamp::Busy
        } else if self.camera_connected {
            Lamp::Ready
        } else {
            Lamp::Idle
        }
    }
    /// The camera's short name: `ILCE-7CR` reads as `A7CR`.
    pub(crate) fn camera_name(&self) -> Option<String> {
        self.camera_model.as_ref().map(|model| {
            model
                .strip_prefix("ILCE-")
                .map_or_else(|| model.clone(), |rest| format!("A{rest}"))
        })
    }
    /// The top bar's two words: a name and a dim fact.
    pub(crate) fn headline(&self) -> (String, String) {
        match self.lamp() {
            Lamp::Unknown => ("Rig".into(), "not connected".into()),
            Lamp::Offline => ("Rig".into(), "offline".into()),
            _ if self.capturing() => (
                self.camera_name().unwrap_or_else(|| "Camera".into()),
                match (self.completed, self.planned) {
                    (Some(done), Some(total)) => format!("{done} / {total}"),
                    _ => self.phase.clone().unwrap_or_default(),
                },
            ),
            _ => {
                let fact = match (self.light.on, self.light.watts) {
                    (Some(true), Some(watts)) => format!("light {watts:.0} W"),
                    (Some(false), _) => "light off".into(),
                    _ if self.camera_connected => "connected".into(),
                    _ => "camera off".into(),
                };
                (
                    self.camera_name()
                        .filter(|_| self.camera_connected)
                        .unwrap_or_else(|| "Rig".into()),
                    fact,
                )
            }
        }
    }
}

/// A command request built from the public state, exactly as the capture
/// client builds one from its own snapshot.
pub(crate) fn request(snapshot: &Value, command: Command) -> anyhow::Result<CommandRequest> {
    anyhow::ensure!(
        snapshot["online"] == true,
        "Reconnect to the Pi before sending a camera command"
    );
    let state = &snapshot["state"];
    let field = |name: &str| {
        state[name]
            .as_u64()
            .ok_or_else(|| anyhow::anyhow!("Missing {name}"))
    };
    Ok(CommandRequest {
        id: strehl_capture::lan::new_key()?,
        camera_revision: field("camera_revision")?,
        plan_revision: field("plan_revision")?,
        sequence_id: field("sequence_id")?,
        command,
    })
}

/// What the owner chose in the popover.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum RigAction {
    /// Open the connection to the camera host for this session.
    Connect,
    Command(RigCommand),
    OpenCapture,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum RigCommand {
    ConnectCamera,
    DisconnectCamera,
    Power(OutletKind, bool),
    PowerPlan(bool),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum OutletKind {
    Light,
    Camera,
}
impl RigCommand {
    pub(crate) fn command(self) -> Command {
        match self {
            Self::ConnectCamera => Command::Connect {},
            Self::DisconnectCamera => Command::Disconnect {},
            Self::Power(OutletKind::Light, on) => Command::Power {
                device: Outlet::Light,
                on,
            },
            Self::Power(OutletKind::Camera, on) => Command::Power {
                device: Outlet::Camera,
                on,
            },
            Self::PowerPlan(enabled) => Command::PowerPlan { enabled },
        }
    }
}

pub(crate) fn lamp_mark(lamp: Lamp) -> Mark {
    match lamp {
        Lamp::Unknown | Lamp::Offline | Lamp::Idle => Mark::NotYet,
        Lamp::Ready => Mark::Fine,
        Lamp::Busy => Mark::Running,
        Lamp::Warn => Mark::Look,
    }
}

fn bytes(value: u64) -> String {
    if value >= 1 << 40 {
        format!("{:.1} TB", value as f64 / (1_u64 << 40) as f64)
    } else {
        format!("{:.0} GB", value as f64 / (1_u64 << 30) as f64)
    }
}

/// One row of the popover: a title, a line under it, and a control.
fn row(
    ui: &mut Ui,
    title: &str,
    detail: &str,
    control: impl FnOnce(&mut Ui) -> Option<RigAction>,
) -> Option<RigAction> {
    let t = studio_theme::tokens(ui.ctx());
    let mut action = None;
    let frame = egui::Frame::NONE
        .inner_margin(egui::Margin::symmetric(14, 10))
        .show(ui, |ui| {
            ui.spacing_mut().item_spacing = egui::vec2(8.0, 4.0);
            ui.set_width(ui.available_width());
            ui.horizontal(|ui| {
                ui.label(
                    egui::RichText::new(title)
                        .font(w::font(ui, crate::studio_fonts::Face::Strong, scale::BODY))
                        .color(t.ink),
                );
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    action = control(ui);
                });
            });
            if !detail.is_empty() {
                ui.add(
                    egui::Label::new(
                        egui::RichText::new(detail)
                            .size(scale::SECONDARY)
                            .color(t.ink2),
                    )
                    .wrap(),
                );
            }
        });
    hairline(ui, frame.response.rect, t.line);
    action
}

/// A rule along the bottom of a row.
fn hairline(ui: &Ui, rect: egui::Rect, color: Color32) {
    crate::theme::rule(ui.painter(), rect.left_bottom(), rect.right_bottom(), color);
}

/// The popover body, 390 wide.
pub(crate) fn popover(ui: &mut Ui, rig: &RigSummary) -> Option<RigAction> {
    let t = studio_theme::tokens(ui.ctx());
    ui.set_width(390.0);
    ui.set_max_width(390.0);
    ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);
    let mut action = None;
    let header = egui::Frame::NONE
        .inner_margin(egui::Margin::symmetric(14, 11))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                w::caps_colored(ui, "Rig", scale::CAPS, t.ink);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    let (mark, label) = match rig.lamp() {
                        Lamp::Unknown => (Mark::NotYet, "Not connected"),
                        Lamp::Offline => (Mark::NotYet, "Offline"),
                        Lamp::Idle => (Mark::NotYet, "Camera off"),
                        Lamp::Ready => (Mark::Fine, "Ready"),
                        Lamp::Busy => (Mark::Running, "Capturing"),
                        Lamp::Warn => (Mark::Look, "Needs a look"),
                    };
                    w::chip(ui, Some(mark), label, false);
                });
            });
        });
    hairline(ui, header.response.rect, t.line);
    if !rig.initialized {
        let pick = row(
            ui,
            "Camera host",
            "Strehl talks to the Pi only once you ask. Connecting reads the rig's state; it does not power anything on.",
            |ui| {
                ui.add(w::Button::new("Connect").small())
                    .clicked()
                    .then_some(RigAction::Connect)
            },
        );
        action = action.or(pick);
    } else {
        let idle = rig.online && !rig.pending;
        // Camera
        let model = rig
            .camera_model
            .clone()
            .unwrap_or_else(|| "No camera".into());
        let camera_line = if rig.camera_connected {
            match rig.usb_mbps {
                Some(mbps) => format!("On · {model} · USB {} Gbit/s", format_gbit(mbps)),
                None => format!("On · {model}"),
            }
        } else {
            match rig.camera_power.on {
                Some(true) => "Powered, not connected".into(),
                Some(false) => "Off".into(),
                None => "Not connected".into(),
            }
        };
        let camera_line = match rig.usb_warning() {
            Some(warning) => format!("{camera_line}. {warning}."),
            None => camera_line,
        };
        let pick = row(ui, "Camera", &camera_line, |ui| {
            if rig.camera_connected {
                if rig.power_available && rig.can_stop_camera {
                    ui.add(w::Button::new("Shut down").small().enabled(idle))
                        .clicked()
                        .then_some(RigAction::Command(RigCommand::Power(
                            OutletKind::Camera,
                            false,
                        )))
                } else {
                    ui.add(
                        w::Button::new("Disconnect")
                            .small()
                            .enabled(idle && rig.editable),
                    )
                    .clicked()
                    .then_some(RigAction::Command(RigCommand::DisconnectCamera))
                }
            } else if rig.power_available && rig.can_start_camera {
                ui.add(w::Button::new("Power on").small().enabled(idle))
                    .clicked()
                    .then_some(RigAction::Command(RigCommand::Power(
                        OutletKind::Camera,
                        true,
                    )))
            } else {
                ui.add(w::Button::new("Connect").small().enabled(idle))
                    .clicked()
                    .then_some(RigAction::Command(RigCommand::ConnectCamera))
            }
        });
        action = action.or(pick);
        if rig.power_available {
            let light_line = match (rig.light.on, rig.light.watts) {
                (Some(on), Some(watts)) => {
                    format!("{} · {watts:.0} W", if on { "On" } else { "Off" })
                }
                (Some(on), None) => if on { "On" } else { "Off" }.into(),
                _ => rig
                    .light
                    .error
                    .clone()
                    .unwrap_or_else(|| "Waiting for the outlet".into()),
            };
            let pick = row(ui, "Light", &light_line, |ui| {
                let on = rig.light.on == Some(true);
                ui.add(
                    w::Button::new(if on { "Off" } else { "On" })
                        .small()
                        .enabled(idle && rig.light.on.is_some()),
                )
                .clicked()
                .then_some(RigAction::Command(RigCommand::Power(
                    OutletKind::Light,
                    !on,
                )))
            });
            action = action.or(pick);
            let pick = row(
                ui,
                "Power for a stack",
                "Warm the light at the start; switch both off when the files are saved",
                |ui| {
                    let mut enabled = rig.manage_stack;
                    let response =
                        ui.add_enabled_ui(idle && rig.can_manage, |ui| w::toggle(ui, &mut enabled));
                    response
                        .inner
                        .changed()
                        .then_some(RigAction::Command(RigCommand::PowerPlan(enabled)))
                },
            );
            action = action.or(pick);
        }
        let host_line = if rig.online {
            if rig.demo {
                "Online · simulator".to_owned()
            } else {
                "Online".to_owned()
            }
        } else {
            rig.connection_error
                .clone()
                .unwrap_or_else(|| "Not answering".into())
        };
        row(ui, "Camera host", &host_line, |ui| {
            w::chip(
                ui,
                Some(if rig.online { Mark::Fine } else { Mark::NotYet }),
                if rig.online { "online" } else { "offline" },
                false,
            );
            None
        });
        let receiver_line = match (&rig.receiver_folder, rig.receiver_free) {
            (Some(folder), Some(free)) => format!("{folder} · {} free", bytes(free)),
            (Some(folder), None) => folder.clone(),
            _ => rig
                .receiver_error
                .clone()
                .unwrap_or_else(|| "Checking…".into()),
        };
        let receiver_ready = rig.receiver_ok == Some(true);
        let pick = row(ui, "Receiver on this PC", &receiver_line, |ui| {
            if receiver_ready {
                w::chip(ui, Some(Mark::Fine), "ready", false);
                None
            } else {
                ui.add(w::Button::new("Open Capture").small())
                    .clicked()
                    .then_some(RigAction::OpenCapture)
            }
        });
        action = action.or(pick);
        let pick = row(
            ui,
            "Phone remote",
            "Follow a capture from your phone; the pairing code is in Capture",
            |ui| {
                ui.add(w::Button::new("Open Capture").small())
                    .clicked()
                    .then_some(RigAction::OpenCapture)
            },
        );
        action = action.or(pick);
        if let Some(error) = rig.command_error.as_ref().or(rig.failure.as_ref()) {
            egui::Frame::NONE
                .inner_margin(egui::Margin::symmetric(14, 8))
                .show(ui, |ui| {
                    ui.horizontal_wrapped(|ui| {
                        w::mark(ui, Mark::Failed);
                        ui.label(
                            egui::RichText::new(error)
                                .size(scale::SECONDARY)
                                .color(t.bad),
                        );
                    });
                });
        }
    }
    action
}

fn format_gbit(mbps: u64) -> String {
    if mbps >= 1000 {
        format!("{}", (mbps as f64 / 1000.0 * 10.0).round() / 10.0)
    } else {
        format!("{:.2}", mbps as f64 / 1000.0)
    }
}

#[cfg(test)]
#[path = "rig-status-tests.rs"]
mod tests;
