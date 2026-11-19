use super::{AMBER, Snapshot};
use chrono::{DateTime, Local, NaiveDateTime, TimeZone};
use eframe::egui;
use strehl_capture::{schedule::StackPower, session::Command};

#[derive(Default)]
pub(super) struct ScheduleUi {
    open: bool,
    local: String,
    power: StackPower,
    warmup: u32,
}

fn start_time(text: &str) -> Result<u64, &'static str> {
    let local = NaiveDateTime::parse_from_str(text.trim(), "%Y-%m-%d %H:%M")
        .map_err(|_| "Enter a date and time as YYYY-MM-DD HH:MM.")?;
    let at = Local
        .from_local_datetime(&local)
        .single()
        .ok_or("This local time is skipped or repeated by daylight saving. Choose another time.")?;
    if at <= Local::now() {
        return Err("Choose a future local date and time.");
    }
    Ok(at.timestamp() as u64)
}
impl ScheduleUi {
    pub(super) fn editing(&self) -> bool {
        self.open
    }
    pub fn open(&mut self, s: &Snapshot) {
        self.open = true;
        if start_time(&self.local).is_err() {
            self.local = (Local::now() + chrono::Duration::minutes(10))
                .format("%Y-%m-%d %H:%M")
                .to_string();
        }
        self.power = if s.state["power"].is_object() {
            StackPower::managed()
        } else {
            StackPower::default()
        };
        self.warmup = s.state["power"]["warmup_seconds"].as_u64().unwrap_or(5) as u32;
    }
    pub fn show(&mut self, ui: &mut egui::Ui, s: &Snapshot, can_arm: bool) -> Option<Command> {
        let schedule = &s.state["schedule"];
        if !schedule.is_object() {
            return None;
        }
        let job = &schedule["job"];
        let stage = job["stage"].as_str().unwrap_or_default();
        let active = matches!(stage, "armed" | "running");
        let mut command = None;
        if let Some(ts) = job["start_at"]
            .as_i64()
            .and_then(|at| DateTime::from_timestamp(at, 0))
        {
            let time = ts.with_timezone(&Local).format("%a %b %d · %H:%M %:z");
            let r = &job["recipe"];
            ui.horizontal_wrapped(|ui| {
                ui.label(format!(
                    "Scheduled stack · {time} · {}",
                    job["message"].as_str().unwrap_or(stage)
                ));
                if active
                    && ui
                        .add_enabled(
                            s.fresh() && !s.pending,
                            egui::Button::new(if stage == "armed" {
                                "Cancel schedule"
                            } else {
                                "Stop scheduled stack"
                            }),
                        )
                        .clicked()
                {
                    command = job["id"]
                        .as_str()
                        .map(|id| Command::CancelSchedule { id: id.into() });
                }
            });
            if active {
                ui.small(format!(
                    "Saved bounds {} → {} · step {} · {} RAWs per plane",
                    r["plan"]["start"], r["plan"]["end"], r["plan"]["step"], r["shots"]
                ));
            }
        }
        if let Some(error) = schedule["error"].as_str() {
            ui.colored_label(AMBER, error);
        }
        if !self.open || active {
            self.open = false;
            return command;
        }
        let mut open = true;
        egui::Window::new("Schedule stack")
            .open(&mut open)
            .collapsible(false)
            .resizable(false)
            .show(ui.ctx(), |ui| command = self.form(ui, s, can_arm));
        self.open = open && command.is_none();
        command
    }
    fn form(&mut self, ui: &mut egui::Ui, s: &Snapshot, can_arm: bool) -> Option<Command> {
        ui.set_max_width(360.0);
        ui.label("Start preparation at local time");
        ui.horizontal(|ui| {
            ui.add(
                egui::TextEdit::singleline(&mut self.local)
                    .desired_width(160.0)
                    .hint_text("YYYY-MM-DD HH:MM"),
            );
            if let Ok(at) = start_time(&self.local)
                && let Some(dt) = DateTime::from_timestamp(at as i64, 0)
            {
                ui.label(dt.with_timezone(&Local).format("UTC%:z").to_string());
            }
        });
        if s.state["power"].is_object() {
            ui.add_space(6.0);
            ui.label("Before the stack");
            ui.checkbox(&mut self.power.wake_camera, "Power on camera if needed");
            ui.checkbox(&mut self.power.light_on, "Turn on light");
            ui.add_enabled_ui(self.power.light_on, |ui| {
                ui.horizontal(|ui| {
                    ui.label("Light warmup");
                    ui.add(
                        egui::DragValue::new(&mut self.warmup)
                            .range(0..=300)
                            .suffix(" s"),
                    );
                });
            });
            ui.label("After the files are saved");
            ui.checkbox(&mut self.power.light_off, "Turn off light");
            ui.checkbox(&mut self.power.camera_off, "Shut down camera");
        }
        if let (Some(n), Some(shots)) = (
            s.state["planned"].as_u64(),
            s.state["shots_per_plane"].as_u64(),
        ) {
            ui.label(format!("{n} focus planes · {} RAWs", n * shots));
        }
        ui.small("The Pi saves these marks and settings. Keep the Pi and receiver PC awake.");
        let time = start_time(&self.local);
        if let Err(e) = time {
            ui.colored_label(AMBER, e);
        }
        if !can_arm {
            ui.small(
                "Connect the camera, apply edits and check the marked plan and available storage.",
            );
        }
        if ui
            .add_enabled(
                can_arm && time.is_ok(),
                egui::Button::new("Schedule this stack"),
            )
            .clicked()
        {
            return Some(Command::ScheduleStack {
                start_at: time.ok()?,
                power: self.power,
                warmup_seconds: Some(self.warmup),
            });
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn native_form_sends_one_timed_stack_with_selected_outlet_actions() {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let snapshot = Snapshot {
            state: json!({"power":{"warmup_seconds":17},"schedule":{"job":null},"planned":4,"shots_per_plane":4}),
            ..Default::default()
        };
        let mut dialog = ScheduleUi::default();
        dialog.open(&snapshot);
        let mut command = None;
        let mut paint = |time, events| {
            ctx.run(
                egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(
                        egui::Pos2::ZERO,
                        egui::vec2(900., 700.),
                    )),
                    time: Some(time),
                    events,
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default().show(ctx, |ui| {
                        if let Some(c) = dialog.show(ui, &snapshot, true) {
                            command = Some(c);
                        }
                    });
                },
            )
        };
        fn center(out: &egui::FullOutput, label: &str) -> egui::Pos2 {
            out.shapes
                .iter()
                .find_map(|s| match &s.shape {
                    egui::Shape::Text(t) if t.galley.text() == label => {
                        Some(egui::Rect::from_min_size(t.pos, t.galley.size()).center())
                    }
                    _ => None,
                })
                .unwrap_or_else(|| panic!("Missing control {label}"))
        }
        paint(0., vec![]);
        let initial = paint(0.5, vec![]);
        let mut clicked = |at: egui::Pos2, time: f64| {
            let button = |pressed| egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed,
                modifiers: egui::Modifiers::NONE,
            };
            paint(time, vec![egui::Event::PointerMoved(at), button(true)]);
            paint(time + 0.07, vec![button(false)])
        };
        let toggled = clicked(center(&initial, "Shut down camera"), 0.8);
        clicked(center(&toggled, "Schedule this stack"), 1.1);
        let Some(Command::ScheduleStack {
            power,
            warmup_seconds,
            ..
        }) = command
        else {
            panic!("Rendered button did not schedule")
        };
        assert!(!power.camera_off && power.light_off && power.wake_camera && power.light_on);
        assert_eq!(warmup_seconds, Some(17));
    }
}
