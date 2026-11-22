//! Rig settings in the Capture plan (owner feedback, 2026-11-21: "where do
//! I configure approach units, warmup time, etc.?"). The camera host's own
//! settings, in one place under the plan's Rig step: approach, settle,
//! exposure timeout, light warm-up, manage power and error correction, each
//! with what it does and its default.
//!
//! Values are the host's current ones (its plan and power state); a typed
//! value is checked against the host's own rules before anything is sent
//! (`Plan::validate`, `Schedule::set_warmup`'s 0-300 s), and sent through
//! the plan's intents as the host's `settings`, `set_warmup`, `power_plan`
//! and `error_correction` commands.
use eframe::egui::{self, Align2, Sense, Stroke, Ui};
use strehl_capture::model::Plan;

use super::plan::PlanIntent;
use super::style::{self, ButtonKind, CapturePalette};
use crate::capture_client::Snapshot;

/// A numeric rig setting.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Key {
    Approach,
    Settle,
    Timeout,
    Warmup,
    /// Error correction's retakes of one plane (h-retake).
    MaxRetakes,
}

/// Its range, default, unit, the values the steppers walk and its line.
pub(crate) struct Spec {
    pub key: Key,
    pub label: &'static str,
    pub unit: &'static str,
    pub min: u32,
    pub max: u32,
    pub default: u32,
    pub ladder: &'static [u32],
    pub help: &'static str,
}

/// The host's ranges: `Plan::validate` (approach 1-4096 units, settle
/// 100-30000 ms, exposure timeout 5-3600 s) and the light warm-up 0-300 s
/// (`Schedule::set_warmup`); defaults from `Plan::default` and the power
/// configuration's `default_warmup` (5 s).
pub(crate) const SPECS: [Spec; 5] = [
    Spec {
        key: Key::Approach,
        label: "Approach",
        unit: "units",
        min: 1,
        max: 4096,
        default: 128,
        ladder: &[16, 32, 64, 128, 256, 512, 1024, 2048, 4096],
        help: "Before the first plane (and a retake) the lens backs off this far and comes forward, so every plane is reached from the same side.",
    },
    Spec {
        key: Key::Settle,
        label: "Settle",
        unit: "ms",
        min: 100,
        max: 30000,
        default: 500,
        ladder: &[
            100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000, 10000, 30000,
        ],
        help: "Wait after each focus move. Up to 500 ms is free: the lens moves while the last RAW is fetched. The plane after the approach always waits at least 2 s.",
    },
    Spec {
        key: Key::Timeout,
        label: "Exposure timeout",
        unit: "s",
        min: 5,
        max: 3600,
        default: 120,
        ladder: &[5, 10, 30, 60, 120, 300, 600, 1200, 3600],
        help: "How long the camera may take to deliver one exposure before the capture stops with a fault.",
    },
    Spec {
        key: Key::Warmup,
        label: "Light warm-up",
        unit: "s",
        min: 0,
        max: 300,
        default: 5,
        ladder: &[0, 5, 10, 15, 30, 60, 90, 120, 180, 300],
        help: "With Manage power, the light is on this long before the first plane. It dimmed 9 % over its first minute (measured).",
    },
    // The host's 0-5 (`strehl_capture::worker::MAX_RETAKES_LIMIT`, where the
    // range is argued); 2 as before it could be set.
    Spec {
        key: Key::MaxRetakes,
        label: "Retakes a plane",
        unit: "retakes",
        min: 0,
        max: strehl_capture::worker::MAX_RETAKES_LIMIT as u32,
        default: strehl_capture::worker::MAX_RETAKES as u32,
        ladder: &[0, 1, 2, 3, 4, 5],
        help: "With error correction, a failed plane is taken again up to this often; a later try passed about half the time (measured). 0 checks every plane and retakes none. Retake on a plane takes it again by hand.",
    },
];

pub(crate) fn spec(key: Key) -> &'static Spec {
    SPECS
        .iter()
        .find(|s| s.key == key)
        .expect("every key has a spec")
}

/// The next value of the ladder above (`up`) or below `value`, clamped.
pub(crate) fn step_value(spec: &Spec, value: u32, up: bool) -> u32 {
    let next = if up {
        spec.ladder.iter().copied().find(|&v| v > value)
    } else {
        spec.ladder.iter().rev().copied().find(|&v| v < value)
    };
    next.unwrap_or(if up { spec.max } else { spec.min })
        .clamp(spec.min, spec.max)
}

/// A typed value checked by the host's rules: digits (a unit after them
/// is allowed), the range, and for the approach the lens limit before the
/// marked start (`Plan::prestart`).
pub(crate) fn validate(key: Key, text: &str, plan: Option<&Plan>) -> Result<u32, String> {
    let spec = spec(key);
    let digits: String = text
        .trim()
        .chars()
        .take_while(char::is_ascii_digit)
        .collect();
    let rest = text.trim()[digits.len()..].trim();
    if digits.is_empty() || !(rest.is_empty() || spec.unit.starts_with(rest)) {
        return Err(format!("Type a whole number of {}", spec.unit));
    }
    let value: u32 = digits.parse().map_err(|_| {
        format!(
            "{} must be {}-{} {}",
            spec.label, spec.min, spec.max, spec.unit
        )
    })?;
    if !(spec.min..=spec.max).contains(&value) {
        return Err(format!(
            "{} must be {}-{} {}",
            spec.label, spec.min, spec.max, spec.unit
        ));
    }
    if key == Key::Approach
        && let Some(plan) = plan
    {
        let probe = Plan {
            approach: value as u16,
            ..plan.clone()
        };
        if probe.prestart().is_err() {
            return Err("The start mark is too close to the lens limit for this approach".into());
        }
    }
    Ok(value)
}

/// The rig settings as the host holds them now.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct RigValues {
    pub approach: Option<u32>,
    pub settle: Option<u32>,
    pub timeout: Option<u32>,
    /// `None` without studio outlets.
    pub warmup: Option<u32>,
    pub manage_power: Option<bool>,
    pub error_correction: Option<bool>,
    /// Error correction's retakes of a plane; `None` from a host that does
    /// not take the setting (it retakes twice).
    pub max_retakes: Option<u32>,
    /// Plan settings may be sent (a ready camera, nothing running).
    pub plan_editable: bool,
    /// Between sequences: power, warm-up and error correction may change.
    pub between: bool,
    /// Each plane is checked as it arrives (error correction needs it).
    pub checking: bool,
}

impl RigValues {
    pub fn read(s: &Snapshot, settle_ms: u32, checking: bool) -> Self {
        let host = &s.host;
        let plan = host.plan.as_ref();
        let power = host.power.as_ref();
        let between = s.fresh() && !s.pending && !host.phase.active();
        Self {
            approach: plan.map(|p| u32::from(p.approach)),
            settle: plan.map(|_| settle_ms),
            timeout: plan.map(|p| p.capture_timeout_s),
            warmup: power.and_then(|p| p.warmup_seconds).map(|w| w as u32),
            manage_power: power.map(|p| p.manage_stack),
            error_correction: host.error_correction,
            max_retakes: host.capabilities.max_retakes.then(|| host.max_retakes()),
            plan_editable: s.fresh() && host.editable && !s.pending && plan.is_some(),
            between,
            checking,
        }
    }
    pub fn value(&self, key: Key) -> Option<u32> {
        match key {
            Key::Approach => self.approach,
            Key::Settle => self.settle,
            Key::Timeout => self.timeout,
            Key::Warmup => self.warmup,
            Key::MaxRetakes => self.max_retakes,
        }
    }
    fn editable(&self, key: Key) -> bool {
        match key {
            Key::Warmup => self.between && self.warmup.is_some(),
            Key::MaxRetakes => self.between && self.max_retakes.is_some(),
            _ => self.plan_editable,
        }
    }
}

/// The value as the summary line writes it.
fn shown(key: Key, value: u32) -> String {
    match key {
        Key::Settle if value >= 1000 && value.is_multiple_of(100) => {
            format!("{} s", value as f64 / 1000.0)
        }
        _ => format!("{value} {}", spec(key).unit),
    }
}

/// The Rig step's second line: the settings at a glance.
pub(crate) fn summary(v: &RigValues) -> String {
    let mut parts = Vec::new();
    if let Some(a) = v.approach {
        parts.push(format!("approach {a}"));
    }
    if let Some(s) = v.settle {
        parts.push(format!("settle {}", shown(Key::Settle, s)));
    }
    if let Some(w) = v.warmup {
        parts.push(format!("warm-up {w} s"));
    }
    let mut text = parts.join(" · ");
    if let Some(first) = text.get(..1) {
        text = first.to_uppercase() + &text[1..];
    }
    text
}

/// The intent that sends `value` for `key`.
pub(crate) fn intent(key: Key, value: u32) -> PlanIntent {
    match key {
        Key::Approach => PlanIntent::SetApproach(value as u16),
        Key::Settle => PlanIntent::SetSettle(value),
        Key::Timeout => PlanIntent::SetCaptureTimeout(value),
        Key::Warmup => PlanIntent::SetWarmup(value),
        Key::MaxRetakes => PlanIntent::SetMaxRetakes(value.min(u32::from(u8::MAX)) as u8),
    }
}

/// The editor's own state: the field being typed in and its last error.
#[derive(Default)]
pub(crate) struct RigEditor {
    typing: Option<(Key, String)>,
    error: Option<(Key, String)>,
}

impl RigEditor {
    /// Draws the settings (in the Rig step's column) and pushes what was
    /// chosen to `out`.
    pub fn show(
        &mut self,
        ui: &mut Ui,
        v: &RigValues,
        plan: Option<&Plan>,
        palette: &CapturePalette,
        out: &mut Vec<PlanIntent>,
    ) {
        ui.add_space(6.0);
        let left = ui.max_rect().left();
        let right = ui.max_rect().right();
        for spec in SPECS.iter().filter(|s| s.key != Key::MaxRetakes) {
            let top = ui.cursor().top();
            style::hairline(
                ui.painter(),
                egui::pos2(left, top + 0.5),
                egui::pos2(right, top + 0.5),
                palette.line,
            );
            ui.add_space(6.0);
            self.number_row(ui, spec, v, plan, palette, out);
            ui.add_space(6.0);
        }
        let switches = [
            (
                "Manage power",
                v.manage_power,
                v.between,
                "Light and camera on for a stack, off once its RAWs are saved.",
            ),
            (
                "Error correction",
                v.error_correction,
                v.between && (v.checking || v.error_correction == Some(true)),
                "Each plane waits for this PC's check; failed planes are retaken later, about 10 s each (measured). Needs Check each plane.",
            ),
        ];
        for (i, (label, value, enabled, help)) in switches.into_iter().enumerate() {
            let top = ui.cursor().top();
            style::hairline(
                ui.painter(),
                egui::pos2(left, top + 0.5),
                egui::pos2(right, top + 0.5),
                palette.line,
            );
            ui.add_space(6.0);
            ui.horizontal(|ui| {
                ui.set_min_height(22.0);
                style::text(ui, label, 12.5, palette.ink);
                ui.with_layout(
                    egui::Layout::right_to_left(egui::Align::Center),
                    |ui| match value {
                        Some(on) => {
                            if style::toggle(ui, on, enabled, palette).clicked() {
                                out.push(if i == 0 {
                                    PlanIntent::SetPowerDown(!on)
                                } else {
                                    PlanIntent::SetRetake(!on)
                                });
                            }
                        }
                        None => {
                            style::text(ui, "not on this host", 12.0, palette.ink3);
                        }
                    },
                );
            });
            help_line(ui, help, palette);
            ui.add_space(6.0);
            // Error correction's own setting, under its switch (h-retake).
            if i == 1 {
                let top = ui.cursor().top();
                style::hairline(
                    ui.painter(),
                    egui::pos2(left, top + 0.5),
                    egui::pos2(right, top + 0.5),
                    palette.line,
                );
                ui.add_space(6.0);
                self.number_row(ui, spec(Key::MaxRetakes), v, plan, palette, out);
                ui.add_space(6.0);
            }
        }
        let top = ui.cursor().top();
        style::hairline(
            ui.painter(),
            egui::pos2(left, top + 0.5),
            egui::pos2(right, top + 0.5),
            palette.line,
        );
        ui.add_space(8.0);
        ui.horizontal_wrapped(|ui| {
            ui.spacing_mut().item_spacing.x = 14.0;
            if style::link(ui, "Light and camera power", true, palette).clicked() {
                out.push(PlanIntent::OpenRig);
            }
            if style::link(ui, "Connection and storage", true, palette).clicked() {
                out.push(PlanIntent::OpenSettings);
            }
        });
    }

    #[allow(clippy::too_many_arguments)]
    fn number_row(
        &mut self,
        ui: &mut Ui,
        spec: &Spec,
        v: &RigValues,
        plan: Option<&Plan>,
        palette: &CapturePalette,
        out: &mut Vec<PlanIntent>,
    ) {
        let value = v.value(spec.key);
        let enabled = value.is_some() && v.editable(spec.key);
        ui.horizontal(|ui| {
            ui.set_min_height(24.0);
            style::text(ui, spec.label, 12.5, palette.ink);
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.spacing_mut().item_spacing.x = 2.0;
                let Some(value) = value else {
                    style::text(
                        ui,
                        if spec.key == Key::Warmup {
                            "no studio outlets"
                        } else if spec.key == Key::MaxRetakes {
                            "2, fixed on this host"
                        } else {
                            "—"
                        },
                        12.0,
                        palette.ink3,
                    );
                    return;
                };
                if stepper(ui, true, enabled && value < spec.max, palette)
                    .on_hover_text(format!("Up to {}", step_value(spec, value, true)))
                    .clicked()
                {
                    self.send(spec.key, step_value(spec, value, true), plan, out);
                }
                self.value_field(ui, spec, value, enabled, plan, palette, out);
                if stepper(ui, false, enabled && value > spec.min, palette)
                    .on_hover_text(format!("Down to {}", step_value(spec, value, false)))
                    .clicked()
                {
                    self.send(spec.key, step_value(spec, value, false), plan, out);
                }
            });
        });
        if let Some((key, error)) = &self.error
            && *key == spec.key
        {
            let mut job = style::job(error, 11.5, palette.warn, 0.0);
            job.wrap.max_width = ui.available_width();
            ui.label(job);
        }
        help_line(ui, &help(spec), palette);
    }

    /// The value, typed into on a click: Enter or leaving the field sends a
    /// valid value, Escape puts the host's back.
    #[allow(clippy::too_many_arguments)]
    fn value_field(
        &mut self,
        ui: &mut Ui,
        spec: &Spec,
        value: u32,
        enabled: bool,
        plan: Option<&Plan>,
        palette: &CapturePalette,
        out: &mut Vec<PlanIntent>,
    ) {
        let size = egui::vec2(82.0, 22.0);
        let id = ui.id().with(("rig-setting", spec.label));
        let typing = matches!(&self.typing, Some((k, _)) if *k == spec.key);
        if typing && enabled {
            let mut text = self
                .typing
                .as_ref()
                .map(|(_, t)| t.clone())
                .unwrap_or_default();
            let edit = egui::TextEdit::singleline(&mut text)
                .id(id)
                .desired_width(size.x)
                .min_size(size)
                .horizontal_align(egui::Align::Max)
                .vertical_align(egui::Align::Center)
                .font(egui::FontId::proportional(12.5))
                .text_color(palette.ink)
                .background_color(palette.bg)
                .margin(egui::Margin::symmetric(6, 2));
            let r = ui.add_sized(size, edit);
            ui.painter().rect_stroke(
                r.rect,
                0.0,
                Stroke::new(1.0_f32, palette.accent),
                egui::StrokeKind::Inside,
            );
            self.typing = Some((spec.key, text.clone()));
            if !r.has_focus() && !r.lost_focus() {
                r.request_focus();
            }
            let escape = ui.input(|i| i.key_pressed(egui::Key::Escape));
            if escape {
                self.typing = None;
                self.error = None;
            } else if r.lost_focus() {
                // Enter here applies the value; it is not the station's Start.
                super::plan::consume_enter(ui);
                self.typing = None;
                self.send_text(spec.key, &text, value, plan, out);
            }
            return;
        }
        let (rect, response) = ui.allocate_exact_size(
            size,
            if enabled {
                Sense::click()
            } else {
                Sense::hover()
            },
        );
        let p = ui.painter();
        p.rect_filled(rect, 0.0, palette.bg);
        p.rect_stroke(
            rect,
            0.0,
            Stroke::new(
                1.0_f32,
                if enabled && response.hovered() {
                    palette.ink3
                } else {
                    palette.line2
                },
            ),
            egui::StrokeKind::Inside,
        );
        style::paint_job(
            p,
            rect.right_center() - egui::vec2(6.0, 0.0),
            Align2::RIGHT_CENTER,
            style::job(
                &format!("{value} {}", spec.unit),
                12.5,
                if enabled { palette.ink } else { palette.ink3 },
                0.1,
            ),
        );
        let response = if enabled {
            response
                .on_hover_cursor(egui::CursorIcon::Text)
                .on_hover_text(format!("Type {}-{} {}", spec.min, spec.max, spec.unit))
        } else {
            response
        };
        if response.clicked() {
            self.typing = Some((spec.key, value.to_string()));
            self.error = None;
        }
    }

    fn send_text(
        &mut self,
        key: Key,
        text: &str,
        now: u32,
        plan: Option<&Plan>,
        out: &mut Vec<PlanIntent>,
    ) {
        match validate(key, text, plan) {
            Ok(value) if value == now => self.error = None,
            Ok(value) => self.send(key, value, plan, out),
            Err(e) => self.error = Some((key, e)),
        }
    }

    fn send(&mut self, key: Key, value: u32, plan: Option<&Plan>, out: &mut Vec<PlanIntent>) {
        match validate(key, &value.to_string(), plan) {
            Ok(value) => {
                self.error = None;
                out.push(intent(key, value));
            }
            Err(e) => self.error = Some((key, e)),
        }
    }
}

/// A square 22 px button with a drawn plus or minus (the UI face draws
/// U+2212 on the baseline).
pub(crate) fn stepper(
    ui: &mut Ui,
    plus: bool,
    enabled: bool,
    palette: &CapturePalette,
) -> egui::Response {
    let r = style::button_sized(
        ui,
        "",
        ButtonKind::Plain,
        egui::vec2(22.0, 22.0),
        enabled,
        palette,
    );
    let c = r.rect.center();
    let color = if enabled {
        palette.ink
    } else {
        palette.ink3.gamma_multiply(0.6)
    };
    let stroke = Stroke::new(1.2_f32, color);
    ui.painter()
        .line_segment([c - egui::vec2(4.5, 0.0), c + egui::vec2(4.5, 0.0)], stroke);
    if plus {
        ui.painter()
            .line_segment([c - egui::vec2(0.0, 4.5), c + egui::vec2(0.0, 4.5)], stroke);
    }
    r
}

/// A setting's line with its default.
pub(crate) fn help(spec: &Spec) -> String {
    format!("{} Default {} {}.", spec.help, spec.default, spec.unit)
}

fn help_line(ui: &mut Ui, text: &str, palette: &CapturePalette) {
    let mut job = style::job(&super::guide::unbreak(text), 11.5, palette.ink3, 0.0);
    job.wrap.max_width = ui.available_width();
    ui.label(job);
}

#[cfg(test)]
#[path = "capture-rig-settings-tests.rs"]
mod tests;
