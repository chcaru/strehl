//! Scheduling a stack (owner feedback, 2026-11-21): one dialog, titled
//! once, in the station's square, ruled style. The start is chosen either
//! as a local date and time (a calendar and hour and minute wheels) or as
//! a span from now ("in 1 h 30 m", with quick chips); either way the dialog
//! shows the resulting local start, the time zone and the estimated end.
//!
//! The camera host takes `schedule_stack.start_at` as Unix seconds (UTC,
//! `strehl_capture::schedule::now`), so a local wall-clock time is
//! resolved through the zone's rules here: a time skipped by daylight
//! saving is refused, a repeated one is the earlier of the two and says so.
use chrono::{
    Datelike, Duration, Local, LocalResult, NaiveDate, NaiveDateTime, NaiveTime, TimeZone,
    Timelike, Utc,
};
use eframe::egui::{self, Align2, Rect, Sense, Stroke, Ui};
use strehl_capture::{schedule::StackPower, session::Command};

use super::Snapshot;
use super::rig_settings::{self, Key};
use super::style::{self, ButtonKind, CapturePalette};

/// How the start is chosen.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum Mode {
    /// A local date and time.
    #[default]
    At,
    /// A span from now.
    In,
}

/// The soonest start the dialog accepts, from now: the host refuses a past
/// start, and the request takes a moment to arrive.
pub(crate) const MIN_LEAD: i64 = 60;
/// The longest span "in a while" offers, in minutes (three days).
pub(crate) const MAX_IN_MINUTES: u32 = 72 * 60;
/// The pickers' height (the calendar's), so both modes are the same size.
const PICKER_H: f32 = 214.0;
/// Quick spans, in minutes.
pub(crate) const CHIPS: [(u32, &str); 6] = [
    (15, "+15 m"),
    (30, "+30 m"),
    (60, "+1 h"),
    (120, "+2 h"),
    (240, "+4 h"),
    (480, "+8 h"),
];

/// A local start resolved to Unix seconds.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Start {
    pub unix: i64,
    /// The wall-clock time happens twice (clocks go back); this is the
    /// earlier.
    pub repeated: bool,
}

/// Resolves a local wall-clock time in `tz` by its daylight-saving rules.
pub(crate) fn resolve<Tz: TimeZone>(tz: &Tz, local: NaiveDateTime) -> Result<Start, String> {
    match tz.from_local_datetime(&local) {
        LocalResult::Single(t) => Ok(Start {
            unix: t.timestamp(),
            repeated: false,
        }),
        LocalResult::Ambiguous(a, b) => Ok(Start {
            unix: a.timestamp().min(b.timestamp()),
            repeated: true,
        }),
        LocalResult::None => Err(format!(
            "{} does not exist on {}: the clocks go forward. Choose another time.",
            local.format("%H:%M"),
            local.format("%a %b %-d")
        )),
    }
}

/// A start must be at least [`MIN_LEAD`] seconds away.
pub(crate) fn check_future(unix: i64, now: i64) -> Result<(), String> {
    if unix < now + MIN_LEAD {
        Err("That time has passed or is too close: choose one at least a minute from now.".into())
    } else {
        Ok(())
    }
}

/// `UTC−08:00`.
pub(crate) fn offset_label(seconds: i32) -> String {
    // ASCII minus: the UI face draws U+2212 on the baseline.
    let sign = if seconds < 0 { '-' } else { '+' };
    let s = seconds.unsigned_abs();
    format!("UTC{sign}{:02}:{:02}", s / 3600, s / 60 % 60)
}

/// `Today · 14:35`, `Tomorrow · 06:10` or `Mon Nov 23 · 06:10`, in `tz`.
pub(crate) fn when_label<Tz: TimeZone>(tz: &Tz, unix: i64, now: i64) -> String
where
    Tz::Offset: std::fmt::Display,
{
    let (Some(at), Some(today)) = (
        tz.timestamp_opt(unix, 0).single(),
        tz.timestamp_opt(now, 0).single(),
    ) else {
        return String::new();
    };
    let day = at.date_naive();
    let today = today.date_naive();
    let prefix = if day == today {
        "Today".to_owned()
    } else if Some(day) == today.succ_opt() {
        "Tomorrow".to_owned()
    } else {
        at.format("%a %b %-d").to_string()
    };
    format!("{prefix} · {}", at.format("%H:%M"))
}

/// The local zone's offset at `unix`.
pub(crate) fn local_offset(unix: i64) -> Option<i32> {
    Local
        .timestamp_opt(unix, 0)
        .single()
        .map(|t| t.offset().local_minus_utc())
}

/// `1 h 30 m`, `45 m`, `2 d 3 h`.
pub(crate) fn span_label(seconds: i64) -> String {
    let minutes = (seconds.max(0) + 59) / 60;
    let (d, h, m) = (minutes / 1440, minutes / 60 % 24, minutes % 60);
    match (d, h, m) {
        (0, 0, m) => format!("{m} m"),
        (0, h, 0) => format!("{h} h"),
        (0, h, m) => format!("{h} h {m} m"),
        (d, 0, _) => format!("{d} d"),
        (d, h, _) => format!("{d} d {h} h"),
    }
}

/// A local time rounded up to the next five minutes.
fn round_up_five(at: NaiveDateTime) -> NaiveDateTime {
    let base = at.date().and_hms_opt(at.hour(), 0, 0).unwrap_or(at);
    let minute = (at.minute() + u32::from(at.second() > 0)).div_ceil(5) * 5;
    base + Duration::minutes(i64::from(minute))
}

/// The default start: half an hour from now, on the next five minutes.
pub(crate) fn default_start<Tz: TimeZone>(tz: &Tz, now: i64) -> NaiveDateTime {
    tz.timestamp_opt(now + 30 * 60, 0)
        .single()
        .map(|t| round_up_five(t.naive_local()))
        .unwrap_or_default()
}

/// What the stack takes, for its end: the planes and setup by the host's
/// formula without the light warm-up, which the dialog adds.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct StackTiming {
    pub seconds: f64,
    pub planes: usize,
    pub raws: usize,
}

/// The dialog's state.
#[derive(Default)]
pub(super) struct ScheduleUi {
    open: bool,
    pub(crate) mode: Mode,
    date: Option<NaiveDate>,
    hour: u32,
    minute: u32,
    /// The month the calendar shows (year, month).
    month: Option<(i32, u32)>,
    pub(crate) in_minutes: u32,
    power: StackPower,
    warmup: u32,
}

impl ScheduleUi {
    pub(super) fn editing(&self) -> bool {
        self.open
    }

    pub fn open(&mut self, s: &Snapshot) {
        self.open = true;
        let now = Utc::now().timestamp();
        let stale = self
            .local()
            .and_then(|l| resolve(&Local, l).ok())
            .is_none_or(|st| check_future(st.unix, now).is_err());
        if stale {
            self.set_local(default_start(&Local, now));
        }
        if self.in_minutes == 0 {
            self.in_minutes = 30;
        }
        let power = s.host.power.as_ref();
        self.power = if power.is_some() {
            StackPower::managed()
        } else {
            StackPower::default()
        };
        self.warmup = power.and_then(|p| p.warmup_seconds).unwrap_or(5).min(300) as u32;
    }

    fn local(&self) -> Option<NaiveDateTime> {
        Some(
            self.date?
                .and_time(NaiveTime::from_hms_opt(self.hour, self.minute, 0)?),
        )
    }

    fn set_local(&mut self, at: NaiveDateTime) {
        self.date = Some(at.date());
        self.hour = at.hour();
        self.minute = at.minute();
        self.month = Some((at.year(), at.month()));
    }

    /// The chosen start, resolved at `now`.
    pub(crate) fn start(&self, now: i64) -> Result<Start, String> {
        let start = match self.mode {
            Mode::At => resolve(&Local, self.local().ok_or("Choose a day")?)?,
            Mode::In => Start {
                unix: now + i64::from(self.in_minutes) * 60,
                repeated: false,
            },
        };
        check_future(start.unix, now)?;
        Ok(start)
    }

    /// Switches mode, carrying the chosen start across.
    pub(crate) fn switch(&mut self, mode: Mode, now: i64) {
        if mode == self.mode {
            return;
        }
        match mode {
            Mode::In => {
                if let Ok(start) = self.start(now) {
                    let minutes = ((start.unix - now) as f64 / 300.0).ceil() as u32 * 5;
                    self.in_minutes = minutes.clamp(5, MAX_IN_MINUTES);
                }
            }
            Mode::At => {
                let unix = now + i64::from(self.in_minutes) * 60;
                if let Some(t) = Local.timestamp_opt(unix, 0).single() {
                    self.set_local(round_up_five(t.naive_local()));
                }
            }
        }
        self.mode = mode;
    }

    /// The dialog (a modal over the window) while it is open. Returns the
    /// command to send: a schedule, or cancelling the armed one.
    pub fn show(
        &mut self,
        ctx: &egui::Context,
        s: &Snapshot,
        can_arm: bool,
        timing: Option<StackTiming>,
        palette: &CapturePalette,
    ) -> Option<Command> {
        if !self.open {
            return None;
        }
        let mut command = None;
        let mut close = false;
        let frame = egui::Frame::new()
            .fill(palette.panel)
            .stroke(Stroke::new(1.0_f32, palette.line2))
            .inner_margin(egui::Margin::symmetric(22, 18));
        let response = egui::Modal::new(egui::Id::new("capture-schedule"))
            .frame(frame)
            .show(ctx, |ui| {
                ui.set_width(470.0);
                ui.spacing_mut().item_spacing.y = 6.0;
                ui.horizontal(|ui| {
                    ui.label(style::caps_job("Schedule this stack", 11.5, palette.ink));
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if style::button(ui, "Close", ButtonKind::Quiet, 22.0, true, palette)
                            .clicked()
                        {
                            close = true;
                        }
                    });
                });
                rule(ui, palette);
                command = self.armed(ui, s, palette);
                if command.is_none() && armed_stage(s).is_none() {
                    command = self.form(ui, s, can_arm, timing, palette, &mut close);
                }
            });
        if response.should_close() || close || command.is_some() {
            self.open = false;
        }
        command
    }

    /// The armed (or last) scheduled stack, and its cancel.
    fn armed(&mut self, ui: &mut Ui, s: &Snapshot, palette: &CapturePalette) -> Option<Command> {
        let schedule = s.host.schedule.as_ref()?;
        let mut command = None;
        if let Some(job) = &schedule.job
            && let Some(at) = job.start_at
        {
            let stage = job.stage.as_deref().unwrap_or("");
            let active = matches!(stage, "armed" | "running");
            let now = Utc::now().timestamp();
            let zone = local_offset(at).map(offset_label).unwrap_or_default();
            ui.horizontal(|ui| {
                ui.label(style::caps_job(
                    if active {
                        "Scheduled"
                    } else {
                        "Last scheduled"
                    },
                    9.5,
                    palette.ink3,
                ));
                ui.label(style::job(
                    &format!("{} · local, {zone}", when_label(&Local, at, now)),
                    13.0,
                    palette.ink,
                    0.0,
                ));
            });
            if let Some(message) = job.message.as_deref().filter(|m| !m.is_empty()) {
                note(ui, message, palette.ink2);
            }
            if active {
                let recipe = &s.state["schedule"]["job"]["recipe"];
                if recipe.is_object() {
                    note(
                        ui,
                        &format!(
                            "Saved marks {} to {} · step {} · {} RAWs a plane",
                            recipe["plan"]["start"],
                            recipe["plan"]["end"],
                            recipe["plan"]["step"],
                            recipe["shots"]
                        ),
                        palette.ink3,
                    );
                }
                ui.add_space(4.0);
                let label = if stage == "armed" {
                    "Cancel schedule"
                } else {
                    "Stop scheduled stack"
                };
                if style::button(
                    ui,
                    label,
                    ButtonKind::Danger,
                    28.0,
                    s.fresh() && !s.pending,
                    palette,
                )
                .clicked()
                {
                    command = job.id.clone().map(|id| Command::CancelSchedule { id });
                }
            }
            rule(ui, palette);
        }
        if let Some(error) = &schedule.error {
            note(ui, error, palette.warn);
        }
        command
    }

    fn form(
        &mut self,
        ui: &mut Ui,
        s: &Snapshot,
        can_arm: bool,
        timing: Option<StackTiming>,
        palette: &CapturePalette,
        close: &mut bool,
    ) -> Option<Command> {
        let now = Utc::now().timestamp();
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 4.0;
            for (mode, label) in [(Mode::At, "At a time"), (Mode::In, "In a while")] {
                let kind = if self.mode == mode {
                    ButtonKind::On
                } else {
                    ButtonKind::Quiet
                };
                if style::button(ui, label, kind, 26.0, true, palette).clicked() {
                    self.switch(mode, now);
                }
            }
        });
        ui.add_space(4.0);
        // One height for both pickers, so the dialog does not jump.
        let top = ui.cursor().top();
        match self.mode {
            Mode::At => self.at_picker(ui, now, palette),
            Mode::In => self.in_picker(ui, palette),
        }
        let used = ui.cursor().top() - top;
        ui.add_space((PICKER_H - used).max(0.0) + 6.0);
        rule(ui, palette);
        let start = self.start(now);
        let warmup = if self.power.light_on {
            f64::from(self.warmup)
        } else {
            0.0
        };
        summary(ui, &start, now, timing, warmup, palette);
        rule(ui, palette);
        if s.host.power.is_some() {
            self.power_ui(ui, palette);
            rule(ui, palette);
        }
        note(
            ui,
            "The Pi keeps these marks and settings and starts the stack itself. Keep the Pi and this PC awake.",
            palette.ink3,
        );
        if !can_arm {
            note(
                ui,
                "Connect the camera, mark both bounds, and check the plan and free space first.",
                palette.warn,
            );
        }
        ui.add_space(6.0);
        let mut command = None;
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            let label = match &start {
                Ok(st) => format!(
                    "Schedule for {}",
                    Local
                        .timestamp_opt(st.unix, 0)
                        .single()
                        .map(|t| t.format("%H:%M").to_string())
                        .unwrap_or_default()
                ),
                Err(_) => "Schedule".into(),
            };
            let w = ui.available_width() - 100.0 - 8.0;
            if style::button_sized(
                ui,
                &label,
                ButtonKind::Primary,
                egui::vec2(w, 34.0),
                can_arm && start.is_ok(),
                palette,
            )
            .clicked()
                && let Ok(st) = self.start(Utc::now().timestamp())
            {
                command = Some(Command::ScheduleStack {
                    start_at: st.unix as u64,
                    power: self.power,
                    warmup_seconds: Some(self.warmup),
                });
            }
            if style::button_sized(
                ui,
                "Cancel",
                ButtonKind::Plain,
                egui::vec2(100.0, 34.0),
                true,
                palette,
            )
            .clicked()
            {
                *close = true;
            }
        });
        command
    }

    /// The calendar and the hour and minute wheels.
    fn at_picker(&mut self, ui: &mut Ui, now: i64, palette: &CapturePalette) {
        let today = Local
            .timestamp_opt(now, 0)
            .single()
            .map(|t| t.date_naive())
            .unwrap_or_default();
        let shown = self.month.unwrap_or((today.year(), today.month()));
        ui.horizontal_top(|ui| {
            ui.spacing_mut().item_spacing.x = 28.0;
            ui.vertical(|ui| {
                ui.spacing_mut().item_spacing.y = 4.0;
                if let Some(picked) =
                    calendar(ui, shown, today, self.date, palette, &mut self.month)
                {
                    self.date = Some(picked);
                }
            });
            ui.vertical(|ui| {
                ui.spacing_mut().item_spacing.y = 4.0;
                ui.label(style::caps_job("Time", 9.5, palette.ink3));
                ui.horizontal(|ui| {
                    ui.spacing_mut().item_spacing.x = 6.0;
                    let mut hour = i64::from(self.hour);
                    if wheel(
                        ui,
                        "schedule-hour",
                        &mut hour,
                        (0, 23, 1),
                        true,
                        two,
                        palette,
                    ) {
                        self.hour = hour as u32;
                    }
                    ui.label(style::job(":", 20.0, palette.ink3, 0.0));
                    let mut minute = i64::from(self.minute);
                    if minute % 5 != 0 {
                        minute -= minute % 5;
                    }
                    if wheel(
                        ui,
                        "schedule-minute",
                        &mut minute,
                        (0, 55, 5),
                        true,
                        two,
                        palette,
                    ) {
                        self.minute = minute as u32;
                    }
                });
                note(ui, "Scroll, drag or click the wheels.", palette.ink3);
            });
        });
    }

    /// The quick chips and the hours and minutes wheels.
    fn in_picker(&mut self, ui: &mut Ui, palette: &CapturePalette) {
        ui.horizontal_wrapped(|ui| {
            ui.spacing_mut().item_spacing.x = 6.0;
            for (minutes, label) in CHIPS {
                let kind = if self.in_minutes == minutes {
                    ButtonKind::On
                } else {
                    ButtonKind::Plain
                };
                if style::button(ui, label, kind, 26.0, true, palette).clicked() {
                    self.in_minutes = minutes;
                }
            }
        });
        ui.add_space(4.0);
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            let total = i64::from(self.in_minutes);
            let mut hours = total / 60;
            let mut minutes = total % 60;
            let max_hours = i64::from(MAX_IN_MINUTES / 60);
            let mut next = total;
            if wheel(
                ui,
                "schedule-in-hours",
                &mut hours,
                (0, max_hours, 1),
                false,
                plain,
                palette,
            ) {
                next = hours * 60 + total % 60;
            }
            ui.label(style::job("h", 14.0, palette.ink3, 0.0));
            if wheel(
                ui,
                "schedule-in-minutes",
                &mut minutes,
                (0, 55, 5),
                true,
                two,
                palette,
            ) {
                next = carry(total, minutes);
            }
            ui.label(style::job("m", 14.0, palette.ink3, 0.0));
            self.in_minutes = next.clamp(5, i64::from(MAX_IN_MINUTES)) as u32;
        });
        note(
            ui,
            "From now. Scroll, drag or click the wheels.",
            palette.ink3,
        );
    }

    fn power_ui(&mut self, ui: &mut Ui, palette: &CapturePalette) {
        ui.label(style::caps_job("Before the stack", 9.5, palette.ink3));
        if style::option(
            ui,
            self.power.wake_camera,
            "Power on the camera if needed",
            None,
            true,
            palette,
        ) {
            self.power.wake_camera = !self.power.wake_camera;
        }
        ui.horizontal(|ui| {
            if style::option(
                ui,
                self.power.light_on,
                "Turn on the light",
                None,
                true,
                palette,
            ) {
                self.power.light_on = !self.power.light_on;
            }
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.spacing_mut().item_spacing.x = 2.0;
                let on = self.power.light_on;
                let spec = rig_settings::spec(Key::Warmup);
                if rig_settings::stepper(ui, true, on && self.warmup < spec.max, palette).clicked()
                {
                    self.warmup = rig_settings::step_value(spec, self.warmup, true);
                }
                let (r, _) = ui.allocate_exact_size(egui::vec2(52.0, 22.0), Sense::hover());
                ui.painter().rect_stroke(
                    r,
                    0.0,
                    Stroke::new(1.0_f32, palette.line2),
                    egui::StrokeKind::Inside,
                );
                style::paint_job(
                    ui.painter(),
                    r.center(),
                    Align2::CENTER_CENTER,
                    style::job(
                        &format!("{} s", self.warmup),
                        12.5,
                        if on { palette.ink } else { palette.ink3 },
                        0.0,
                    ),
                );
                if rig_settings::stepper(ui, false, on && self.warmup > spec.min, palette).clicked()
                {
                    self.warmup = rig_settings::step_value(spec, self.warmup, false);
                }
                ui.add_space(6.0);
                style::text(ui, "Warm-up", 12.5, palette.ink3);
            });
        });
        ui.label(style::caps_job(
            "After the files are saved",
            9.5,
            palette.ink3,
        ));
        if style::option(
            ui,
            self.power.light_off,
            "Turn off the light",
            None,
            true,
            palette,
        ) {
            self.power.light_off = !self.power.light_off;
        }
        if style::option(
            ui,
            self.power.camera_off,
            "Shut down the camera",
            None,
            true,
            palette,
        ) {
            self.power.camera_off = !self.power.camera_off;
        }
    }
}

/// Minutes stepped on the wheel, carrying into the hours across the wrap
/// (55 up to 00 adds an hour; 00 down to 55 takes one).
pub(crate) fn carry(total: i64, minutes: i64) -> i64 {
    let before = total % 60;
    let hours = total / 60;
    let shift = if before >= 55 && minutes == 0 {
        1
    } else if before == 0 && minutes >= 55 {
        -1
    } else {
        0
    };
    (hours + shift) * 60 + minutes
}

fn two(v: i64) -> String {
    format!("{v:02}")
}

fn plain(v: i64) -> String {
    v.to_string()
}

/// The armed or running schedule's stage, if any.
fn armed_stage(s: &Snapshot) -> Option<&str> {
    s.host
        .schedule_stage()
        .filter(|st| matches!(*st, "armed" | "running"))
}

/// When the scheduled stack starts, for the plan's footer.
pub(crate) fn armed_label(s: &Snapshot) -> Option<String> {
    let job = s.host.schedule.as_ref()?.job.as_ref()?;
    match job.stage.as_deref()? {
        "running" => Some("Scheduled stack running".into()),
        "armed" => Some(format!(
            "Scheduled · {}",
            when_label(&Local, job.start_at?, Utc::now().timestamp())
        )),
        _ => None,
    }
}

fn rule(ui: &mut Ui, palette: &CapturePalette) {
    ui.add_space(2.0);
    let y = ui.cursor().top();
    style::hairline(
        ui.painter(),
        egui::pos2(ui.max_rect().left(), y),
        egui::pos2(ui.max_rect().right(), y),
        palette.line,
    );
    ui.add_space(4.0);
}

fn note(ui: &mut Ui, text: &str, color: egui::Color32) {
    let mut job = style::job(&super::guide::unbreak(text), 12.0, color, 0.0);
    job.wrap.max_width = ui.available_width();
    ui.label(job);
}

/// Starts and ends, local, with the zone.
fn summary(
    ui: &mut Ui,
    start: &Result<Start, String>,
    now: i64,
    timing: Option<StackTiming>,
    warmup: f64,
    palette: &CapturePalette,
) {
    let row = |ui: &mut Ui, label: &str, value: &str, detail: &str| {
        ui.horizontal_top(|ui| {
            let (r, _) = ui.allocate_exact_size(egui::vec2(56.0, 18.0), Sense::hover());
            style::paint_job(
                ui.painter(),
                r.left_center(),
                Align2::LEFT_CENTER,
                style::caps_job(label, 9.5, palette.ink3),
            );
            ui.vertical(|ui| {
                ui.spacing_mut().item_spacing.y = 1.0;
                ui.label(style::job(value, 14.0, palette.ink, 0.1));
                let mut job = style::job(detail, 12.0, palette.ink2, 0.0);
                job.wrap.max_width = ui.available_width();
                ui.label(job);
            });
        });
    };
    let Ok(st) = start else {
        if let Err(e) = start {
            note(ui, e, palette.warn);
        }
        return;
    };
    let zone = local_offset(st.unix).map(offset_label).unwrap_or_default();
    row(
        ui,
        "Starts",
        &when_label(&Local, st.unix, now),
        &format!("local time, {zone} · in {}", span_label(st.unix - now)),
    );
    if st.repeated {
        note(
            ui,
            "This time happens twice that night (the clocks go back): the stack starts at the first.",
            palette.warn,
        );
    }
    match timing {
        Some(t) => {
            let end = st.unix + (t.seconds + warmup).round() as i64;
            let warm = if warmup > 0.0 {
                format!(" + {warmup:.0} s warm-up")
            } else {
                String::new()
            };
            let same_day = Local.timestamp_opt(end, 0).single().map(|t| t.date_naive())
                == Local
                    .timestamp_opt(st.unix, 0)
                    .single()
                    .map(|t| t.date_naive());
            let end_label = if same_day {
                Local
                    .timestamp_opt(end, 0)
                    .single()
                    .map(|t| t.format("%H:%M").to_string())
                    .unwrap_or_default()
            } else {
                when_label(&Local, end, now)
            };
            row(
                ui,
                "Ends",
                &format!("about {end_label}"),
                &format!(
                    "{} planes · {} RAWs · {}{warm} (estimate)",
                    t.planes,
                    t.raws,
                    style::minutes(t.seconds)
                ),
            );
        }
        None => row(
            ui,
            "Ends",
            "—",
            "set the exposure and both marks to estimate",
        ),
    }
}

/// A month of days: Sunday first, past days not offered, today ringed,
/// the chosen day filled. Returns a clicked day.
fn calendar(
    ui: &mut Ui,
    (year, month): (i32, u32),
    today: NaiveDate,
    chosen: Option<NaiveDate>,
    palette: &CapturePalette,
    shown: &mut Option<(i32, u32)>,
) -> Option<NaiveDate> {
    let cell = egui::vec2(32.0, 26.0);
    let first = NaiveDate::from_ymd_opt(year, month, 1)?;
    let next_month = if month == 12 {
        NaiveDate::from_ymd_opt(year + 1, 1, 1)
    } else {
        NaiveDate::from_ymd_opt(year, month + 1, 1)
    }?;
    let days = (next_month - first).num_days() as u32;
    let lead = first.weekday().num_days_from_sunday();
    let can_back = (year, month) > (today.year(), today.month());
    ui.horizontal(|ui| {
        ui.spacing_mut().item_spacing.x = 0.0;
        if style::button_sized(
            ui,
            "\u{2039}",
            ButtonKind::Quiet,
            egui::vec2(24.0, 22.0),
            can_back,
            palette,
        )
        .clicked()
        {
            let prev = first - Duration::days(1);
            *shown = Some((prev.year(), prev.month()));
        }
        let (r, _) = ui.allocate_exact_size(egui::vec2(cell.x * 7.0 - 48.0, 22.0), Sense::hover());
        style::paint_job(
            ui.painter(),
            r.center(),
            Align2::CENTER_CENTER,
            style::job(&first.format("%B %Y").to_string(), 13.0, palette.ink, 0.1),
        );
        if style::button_sized(
            ui,
            "\u{203a}",
            ButtonKind::Quiet,
            egui::vec2(24.0, 22.0),
            true,
            palette,
        )
        .clicked()
        {
            *shown = Some((next_month.year(), next_month.month()));
        }
    });
    let (rect, _) = ui.allocate_exact_size(
        egui::vec2(cell.x * 7.0, 18.0 + cell.y * 6.0),
        Sense::hover(),
    );
    for (i, d) in ["S", "M", "T", "W", "T", "F", "S"].iter().enumerate() {
        style::paint_job(
            ui.painter(),
            egui::pos2(rect.left() + cell.x * (i as f32 + 0.5), rect.top() + 2.0),
            Align2::CENTER_TOP,
            style::caps_job(d, 9.5, palette.ink3),
        );
    }
    let mut picked = None;
    for day in 1..=days {
        let index = lead + day - 1;
        let (row, col) = (index / 7, index % 7);
        let r = Rect::from_min_size(
            egui::pos2(
                rect.left() + cell.x * col as f32,
                rect.top() + 18.0 + cell.y * row as f32,
            ),
            cell,
        )
        .shrink(1.0);
        let Some(date) = NaiveDate::from_ymd_opt(year, month, day) else {
            continue;
        };
        let past = date < today;
        let response = ui.interact(
            r,
            ui.id().with(("schedule-day", year, month, day)),
            if past { Sense::hover() } else { Sense::click() },
        );
        let p = ui.painter();
        let selected = chosen == Some(date);
        if selected {
            p.rect_filled(r, 0.0, palette.accent);
        } else if response.hovered() && !past {
            p.rect_filled(r, 0.0, palette.raised);
        }
        if date == today && !selected {
            p.rect_stroke(
                r,
                0.0,
                Stroke::new(1.0_f32, palette.ink3),
                egui::StrokeKind::Inside,
            );
        }
        let color = if selected {
            palette.accent_ink
        } else if past {
            palette.ink3.gamma_multiply(0.5)
        } else {
            palette.ink
        };
        style::paint_job(
            p,
            r.center(),
            Align2::CENTER_CENTER,
            style::job(&day.to_string(), 12.5, color, 0.0),
        );
        if response.clicked() {
            picked = Some(date);
        }
    }
    picked
}

/// The next value on a wheel of `(min, max, step)`, `by` steps on; it
/// wraps round when `wrap`.
pub(crate) fn shift(value: i64, by: i64, (min, max, step): (i64, i64, i64), wrap: bool) -> i64 {
    let n = value + by * step;
    if wrap {
        let span = max - min + step;
        (n - min).rem_euclid(span) + min
    } else {
        n.clamp(min, max)
    }
}

/// A wheel: the value boxed between its neighbours. A click on a
/// neighbour, the scroll wheel, a vertical drag or the arrow keys (while
/// hovered) step it; it wraps round when `wrap`. Returns whether it
/// changed.
pub(crate) fn wheel(
    ui: &mut Ui,
    id: &str,
    value: &mut i64,
    range: (i64, i64, i64),
    wrap: bool,
    label: fn(i64) -> String,
    palette: &CapturePalette,
) -> bool {
    let size = egui::vec2(58.0, 96.0);
    let (rect, response) = ui.allocate_exact_size(size, Sense::click_and_drag());
    let id = ui.id().with(id);
    let row_h = size.y / 3.0;
    let mut by = 0i64;
    if response.hovered() {
        let (scroll, up, down) = ui.input(|i| {
            (
                i.raw_scroll_delta.y,
                i.key_pressed(egui::Key::ArrowUp),
                i.key_pressed(egui::Key::ArrowDown),
            )
        });
        let mut acc = ui.data(|d| d.get_temp::<f32>(id).unwrap_or(0.0)) + scroll;
        while acc >= 24.0 {
            by -= 1;
            acc -= 24.0;
        }
        while acc <= -24.0 {
            by += 1;
            acc += 24.0;
        }
        ui.data_mut(|d| d.insert_temp(id, acc));
        if up {
            by -= 1;
        }
        if down {
            by += 1;
        }
    }
    if response.dragged() {
        let drag = id.with("drag");
        let mut acc = ui.data(|d| d.get_temp::<f32>(drag).unwrap_or(0.0)) + response.drag_delta().y;
        while acc >= 18.0 {
            by -= 1;
            acc -= 18.0;
        }
        while acc <= -18.0 {
            by += 1;
            acc += 18.0;
        }
        ui.data_mut(|d| d.insert_temp(drag, acc));
    }
    if response.clicked()
        && let Some(pos) = response.interact_pointer_pos()
    {
        if pos.y < rect.top() + row_h {
            by -= 1;
        } else if pos.y > rect.bottom() - row_h {
            by += 1;
        }
    }
    let before = *value;
    if by != 0 {
        *value = shift(*value, by, range, wrap);
    }
    let p = ui.painter();
    let mid = Rect::from_min_size(rect.min + egui::vec2(0.0, row_h), egui::vec2(size.x, row_h));
    p.rect_filled(mid, 0.0, palette.bg);
    p.line_segment(
        [mid.left_top(), mid.right_top()],
        Stroke::new(1.0_f32, palette.accent),
    );
    p.line_segment(
        [mid.left_bottom(), mid.right_bottom()],
        Stroke::new(1.0_f32, palette.accent),
    );
    if response.hovered() {
        p.rect_stroke(
            rect,
            0.0,
            Stroke::new(1.0_f32, palette.line2),
            egui::StrokeKind::Inside,
        );
    }
    let prev = shift(*value, -1, range, wrap);
    let next = shift(*value, 1, range, wrap);
    if prev != *value {
        style::paint_job(
            p,
            egui::pos2(rect.center().x, rect.top() + row_h / 2.0),
            Align2::CENTER_CENTER,
            style::job(&label(prev), 14.0, palette.ink3, 0.0),
        );
    }
    style::paint_job(
        p,
        mid.center(),
        Align2::CENTER_CENTER,
        style::job(&label(*value), 20.0, palette.ink, 0.2),
    );
    if next != *value {
        style::paint_job(
            p,
            egui::pos2(rect.center().x, rect.bottom() - row_h / 2.0),
            Align2::CENTER_CENTER,
            style::job(&label(next), 14.0, palette.ink3, 0.0),
        );
    }
    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::ResizeVertical);
    }
    *value != before
}

impl super::CaptureWorkspace {
    /// The planned stack's time for the dialog's end, without the light
    /// warm-up (the dialog adds its own).
    pub(super) fn schedule_timing(&self, s: &Snapshot) -> Option<StackTiming> {
        let planes = super::plan::marked_planes(s, self.draft.step)?;
        let seconds = super::plan::stack_seconds(s, planes, self.draft.settle_ms)?
            - super::plan::managed_warmup(s) as f64;
        Some(StackTiming {
            seconds,
            planes,
            raws: planes * s.host.shots() as usize,
        })
    }
}

#[cfg(test)]
#[path = "capture-schedule-tests.rs"]
mod tests;
