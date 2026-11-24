//! The Capture plan inspector (Studio 2, 7.4; mockup `capture-plan.html`):
//! the subject and stack name, then four numbered steps, each with a ready
//! mark (Rig, Exposure, Depth, While it runs and after), and a footer with
//! the finishing time, the disk line, Start stack and Schedule.
//!
//! The view takes everything as [`PlanInputs`] and returns [`PlanIntent`]s;
//! it sends nothing itself. The numbers it shows come from the host's own
//! rules: planes from `Plan::positions()`, minutes from
//! `timing::initial_plane` and `initial_setup`, the worst case from
//! `capacity::required`, the expected size from `StoredRaws::expected`.
use std::time::SystemTime;

use eframe::egui::{self, Align2, Rect, Response, Sense, Stroke, Ui};
use serde_json::Value;

use super::guide::{self, DetailKept, GuideTab, Tone};
use super::preflight::{Blocker, Check, Fix};
use super::rig_settings::{self, RigEditor, RigValues};
use super::style::{self, ButtonKind, CapturePalette, Mark};
use super::subject::{self, SubjectChoice};
use crate::capture_client::Snapshot;
use crate::capture_workspace::test_shot::RawLevels;
use crate::workspace_history::NodeId;

/// Steps offered in the table besides the plan's and the calibrated one.
pub(crate) const CANDIDATE_STEPS: [u16; 4] = [5, 7, 10, 16];
/// Overlap below which fine detail measurably drops between planes: the
/// measured knee at about width / 5 (`guide::KNEE`; the step-curve runs of
/// 2026-11-20, which refined `strehl focus-step`'s EDGE of width / 3.6).
/// Rows below it are marked.
pub(crate) const DETAIL_LIMIT: f64 = guide::KNEE;
/// Settle times offered, in milliseconds.
pub(crate) const SETTLE_CHOICES: [u32; 6] = [250, 500, 1000, 1500, 2000, 3000];

/// The step calibration as the plan shows it.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct CalibrationView {
    /// `Calibration::stage()`.
    pub stage: &'static str,
    pub gives_up_in: Option<std::time::Duration>,
    /// The `strehl focus-step` result once done (`width`, `suggested_step`,
    /// `summary`), or `{"error": ...}` when it failed.
    pub result: Value,
    pub finished: Option<SystemTime>,
}

/// The test shot as the plan shows it.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct TestShotView {
    pub stage: &'static str,
    pub levels: Option<RawLevels>,
    /// The ISO and shutter codes it was taken at (the guidance scales its
    /// levels to other settings).
    pub exposure: Option<(u64, u64)>,
    pub taken: Option<SystemTime>,
    pub error: Option<String>,
}

/// The switches of step 4.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct Switches {
    pub check: bool,
    /// Error correction; `None` from a host without it.
    pub retake: Option<bool>,
    pub stack_when_done: bool,
    /// "Manage power"; `None` without studio outlets.
    pub power_down: Option<bool>,
}

/// Everything the inspector shows.
pub(crate) struct PlanInputs<'a> {
    pub s: &'a Snapshot,
    pub blockers: &'a [Blocker],
    /// The plan's step and settle as edited (the draft).
    pub step: u16,
    pub settle_ms: u32,
    pub calibration: CalibrationView,
    pub test_shot: TestShotView,
    /// Plan Q7: the stillness check's stage and line.
    pub stillness: (&'static str, Option<String>),
    pub switches: Switches,
    /// The desktop can run the engine (calibration needs it).
    pub engine: bool,
    /// The catalog's subjects, offered for the subject field.
    pub subjects: &'a [SubjectChoice],
    /// Where a new subject is made ("Bugs").
    pub subject_home: &'a str,
}

/// What the user asked of the plan.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum PlanIntent {
    SetSubject(String),
    SetStackName(String),
    OpenRig,
    Connect,
    Exposure {
        iso: u64,
        shutter: u64,
    },
    TestShot,
    StopTestShot,
    MarkStart,
    MarkEnd,
    Calibrate,
    StopCalibration,
    SetStep(u16),
    SetSettle(u32),
    /// The plan's approach, in focus units.
    SetApproach(u16),
    /// The plan's exposure timeout, in seconds.
    SetCaptureTimeout(u32),
    /// The light warm-up before a managed stack, in seconds.
    SetWarmup(u32),
    /// Start and End from the bounds survey.
    UseSurveyBounds,
    /// The comparison panel ("What changes") at a section.
    OpenGuide(GuideTab),
    /// Clear the stages for a new capture.
    NewCapture,
    /// Plan Q7: watch the magnified picture for sway, or stop watching.
    CheckStillness,
    StopStillness,
    SetFourShot(bool),
    SetCheck(bool),
    SetRetake(bool),
    /// Error correction's retakes of one plane (h-retake).
    SetMaxRetakes(u8),
    SetStackWhenDone(bool),
    SetPowerDown(bool),
    Start,
    Schedule,
    /// The connection, storage and past captures window.
    OpenSettings,
    Fix(Fix),
}

/// One row of the step table.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct StepRow {
    pub step: u16,
    /// Sharp width / step, when the width is measured.
    pub overlap: Option<f64>,
    pub planes: usize,
    pub seconds: Option<f64>,
    /// Expected bytes on disk (the last capture's size per RAW), or the
    /// worst case when there is no earlier capture.
    pub bytes: Option<u64>,
    /// The plan's current step.
    pub current: bool,
    /// Beyond the measured detail limit (overlap below [`DETAIL_LIMIT`]).
    pub risk: bool,
    /// Fine detail kept, read between the two measured stacks.
    pub detail: Option<DetailKept>,
}

/// The inspector's own state: the names being typed and open pickers.
#[derive(Default)]
pub(crate) struct PlanView {
    pub subject: String,
    /// The existing subject chosen on purpose (from the field's list or the
    /// Library); None makes a new subject of `subject`.
    pub chosen: Option<NodeId>,
    /// Put the cursor in the subject field (the pre-flight fix).
    pub focus_subject: bool,
    pub stack_name: String,
    /// The Rig step's settings are open.
    pub rig_open: bool,
    rig: RigEditor,
    /// The comparison panel, when open, at its section.
    pub guide: Option<GuideTab>,
    /// A step typed into the table's last row.
    pub custom_step: String,
}

/// How many planes `Plan::positions()` gives for these bounds and step,
/// without listing them (the table is drawn every frame): the offsets
/// below the distance, then the end.
pub(crate) fn plane_count(start: u16, end: u16, step: u16) -> usize {
    let distance = usize::from(start.abs_diff(end));
    distance.div_ceil(usize::from(step.max(1))) + 1
}

/// Seconds a stack of `planes` takes by the host's own formula (initial
/// plane x planes + setup + warmup), when the shutter is known.
pub(crate) fn stack_seconds(s: &Snapshot, planes: usize, settle_ms: u32) -> Option<f64> {
    let shutter = s.host.exposure.as_ref()?.shutter?;
    stack_seconds_at(s, planes, settle_ms, shutter)
}

/// The light warm-up a stack waits through: the host's, when it manages
/// power.
pub(crate) fn managed_warmup(s: &Snapshot) -> u64 {
    s.host
        .power
        .as_ref()
        .filter(|p| p.manage_stack)
        .and_then(|p| p.warmup_seconds)
        .unwrap_or(0)
}

/// [`stack_seconds`] at another shutter code.
pub(crate) fn stack_seconds_at(
    s: &Snapshot,
    planes: usize,
    settle_ms: u32,
    shutter: u64,
) -> Option<f64> {
    let plane = strehl_capture::timing::initial_plane(shutter, settle_ms, s.host.shots())?;
    Some(
        (plane.mul_f64(planes as f64)
            + strehl_capture::timing::initial_setup(settle_ms)
            + std::time::Duration::from_secs(managed_warmup(s)))
        .as_secs_f64(),
    )
}

/// Expected bytes per RAW of a new capture with this camera, as the
/// receiver now stores them, from the newest earlier capture.
pub(crate) fn expected_per_raw(s: &Snapshot) -> Option<u64> {
    let model = s.host.camera_model.as_deref()?;
    let past = s.stored.iter().find(|p| p.model == model)?;
    if s.receiver["ok"] != true {
        return None;
    }
    let compress = s.receiver["compress_raw"].as_bool().unwrap_or(true);
    let format = s.receiver["archive_format"].as_u64().unwrap_or(1) as u8;
    Some(past.expected(compress, format).0)
}

/// The worst case a stack of `raws` must find free to start.
pub(crate) fn worst_bytes(s: &Snapshot, raws: usize) -> Option<u64> {
    strehl_capture::capacity::required(
        raws,
        s.host
            .raw_max_bytes
            .unwrap_or(strehl_capture::transport::MAX_RAW),
    )
    .ok()
}

/// The step table: the candidate steps, the calibrated one and the plan's,
/// each with its overlap, planes, minutes and gigabytes.
pub(crate) fn step_rows(
    s: &Snapshot,
    step: u16,
    settle_ms: u32,
    calibration: &Value,
) -> Vec<StepRow> {
    let host = &s.host;
    if host.plan.is_none() || !host.bounds_set() {
        return Vec::new();
    }
    let width = calibration["width"].as_f64();
    let mut steps: Vec<u16> = CANDIDATE_STEPS.to_vec();
    if let Some(suggested) = calibration["suggested_step"].as_u64() {
        steps.push(suggested.clamp(1, 65535) as u16);
    }
    // The coarsest step that keeps the detail, which the line under the
    // table names ("Steps up to 9 keep the detail"): it must be a row.
    if let Some(w) = width {
        steps.push((w / guide::KNEE).floor().clamp(1.0, 65535.0) as u16);
    }
    steps.push(step.max(1));
    steps.sort_unstable();
    steps.dedup();
    steps
        .into_iter()
        .map(|candidate| step_row(s, candidate, step, settle_ms, width))
        .collect()
}

/// One step's row (the table's, or a typed step's).
pub(crate) fn step_row(
    s: &Snapshot,
    candidate: u16,
    step: u16,
    settle_ms: u32,
    width: Option<f64>,
) -> StepRow {
    let (start, end) = s.host.plan_bounds();
    let shots = s.host.shots() as usize;
    let planes = plane_count(start, end, candidate);
    let overlap = width.map(|w| w / f64::from(candidate.max(1)));
    StepRow {
        step: candidate,
        overlap,
        planes,
        seconds: stack_seconds(s, planes, settle_ms),
        bytes: expected_per_raw(s)
            .map(|b| b * (planes * shots) as u64)
            .or_else(|| worst_bytes(s, planes * shots)),
        current: candidate == step,
        risk: overlap.is_some_and(|o| o < DETAIL_LIMIT),
        detail: overlap.map(guide::detail_kept),
    }
}

/// A typed step: a whole number of focus units from 1 to 65535.
pub(crate) fn parse_step(text: &str) -> Result<u16, String> {
    let text = text.trim();
    match text.parse::<u32>() {
        Ok(v) if (1..=65535).contains(&v) => Ok(v as u16),
        Ok(_) => Err("A step is 1-65535 focus units".into()),
        Err(_) if text.is_empty() => Err(String::new()),
        Err(_) => Err("Type a whole number of focus units".into()),
    }
}

/// The rig's one line: camera, link, light.
pub(crate) fn rig_summary(s: &Snapshot) -> String {
    let host = &s.host;
    if !s.fresh() {
        return "The camera host is not answering".into();
    }
    let mut parts = Vec::new();
    if host.connected {
        // The short name the top bar uses: ILCE-7CR reads as A7CR.
        let model = host.camera_model.as_deref().unwrap_or("Camera");
        let model = model
            .strip_prefix("ILCE-")
            .map_or_else(|| model.to_owned(), |rest| format!("A{rest}"));
        parts.push(format!("{model} on"));
        if let Some(mbps) = host.usb_speed_mbps {
            parts.push(if mbps >= 1000 {
                format!("USB {} Gbit/s", mbps / 1000)
            } else {
                format!("USB {mbps} Mbit/s")
            });
        }
    } else {
        parts.push("Camera not connected".into());
    }
    if let Some(power) = &host.power {
        parts.push(match (power.light.on, power.light.watts) {
            (Some(true), Some(w)) => format!("light {w:.0} W"),
            (Some(false), _) => "light off".into(),
            _ => "light unknown".into(),
        });
    }
    parts.join(" · ")
}

/// The test shot's line: when, and what the RAW says.
pub(crate) fn test_shot_sentence(view: &TestShotView) -> Option<String> {
    if let Some(levels) = &view.levels {
        let when = view
            .taken
            .map(|t| {
                chrono::DateTime::<chrono::Local>::from(t)
                    .format("%H:%M ")
                    .to_string()
            })
            .unwrap_or_default();
        // Per colour (plan Q4): the brightest colour is named.
        let colour = super::test_shot::colour_name(levels.brightest);
        let clipped = if levels.clipped_share <= 0.0 {
            format!(
                "nothing clipped, {colour} brightest at {:.0} %",
                100.0 * levels.highlight_level
            )
        } else {
            format!("{colour} {:.2} % clipped", 100.0 * levels.clipped_share)
        };
        return Some(format!(
            "Test shot {when}read from the RAW: {clipped}, shadows at {:.1} % of full scale",
            100.0 * levels.shadow_level
        ));
    }
    match view.stage {
        "capturing" => Some("Taking a test shot…".into()),
        "reading" => Some("Reading the test RAW…".into()),
        _ => view.error.clone(),
    }
}

/// The line under the overlap diagram.
pub(crate) fn calibration_sentence(view: &CalibrationView, step: u16) -> String {
    match view.stage {
        "done" => {
            let when = view
                .finished
                .map(|t| {
                    chrono::DateTime::<chrono::Local>::from(t)
                        .format("Calibrated %H:%M · ")
                        .to_string()
                })
                .unwrap_or_else(|| "Calibrated · ".into());
            match view.result["width"].as_f64() {
                Some(w) => format!(
                    "{when}any point is sharp in {:.0} planes",
                    (w / f64::from(step.max(1))).floor()
                ),
                None => format!(
                    "{when}{}",
                    view.result["summary"].as_str().unwrap_or("not measurable")
                ),
            }
        }
        "failed" => format!(
            "Calibration stopped: {}",
            view.result["error"].as_str().unwrap_or("")
        ),
        "idle" => "Calibrate step to see how far detail stays sharp".into(),
        _ => {
            let left = view
                .gives_up_in
                .map(|d| format!(" · gives up in {} s", d.as_secs()))
                .unwrap_or_default();
            format!("Calibrating: {}{left}", view.stage)
        }
    }
}

/// "Ends about" and the disk line of the footer.
pub(crate) fn footer_lines(s: &Snapshot, rows: &[StepRow]) -> (Option<String>, String) {
    let current = rows.iter().find(|r| r.current);
    let ends = current
        .and_then(|r| r.seconds)
        .or(s.host.initial_seconds)
        .map(style::local_time_in);
    let free = s.receiver["free_bytes"]
        .as_u64()
        .map(|b| format!("{:.0} GB free", b as f64 / 1e9));
    let needs = s
        .host
        .storage_required_bytes
        .map(|b| format!("needs up to {}", style::gigabytes(b)));
    let disk = [free, needs]
        .into_iter()
        .flatten()
        .collect::<Vec<_>>()
        .join(" · ");
    (ends, disk)
}

/// The pre-flight strip's right-hand summary for a ready plan.
pub(crate) fn strip_summary(s: &Snapshot, rows: &[StepRow]) -> String {
    let Some(row) = rows.iter().find(|r| r.current) else {
        return String::new();
    };
    let mut parts = vec![
        format!("{} planes", row.planes),
        format!("{} RAWs", row.planes * s.host.shots() as usize),
    ];
    if let Some(sec) = row.seconds {
        parts.push(format!("{:.0} min", (sec / 60.0).round()));
    }
    if let Some(b) = row.bytes {
        parts.push(style::gigabytes(b));
    }
    parts.join(" · ")
}

fn has(blockers: &[Blocker], checks: &[Check]) -> bool {
    blockers.iter().any(|b| checks.contains(&b.check))
}

impl PlanView {
    /// Draws the inspector into `ui` (348 px wide in the shell) and returns
    /// what the user asked.
    pub fn show(
        &mut self,
        ui: &mut Ui,
        inputs: &PlanInputs<'_>,
        palette: &CapturePalette,
    ) -> Vec<PlanIntent> {
        let mut out = Vec::new();
        let full = ui.max_rect();
        ui.painter().rect_filled(full, 0.0, palette.panel);
        style::hairline(
            ui.painter(),
            full.left_top() + egui::vec2(0.5, 0.0),
            full.left_bottom() + egui::vec2(0.5, 0.0),
            palette.line,
        );
        let foot_h = 86.0;
        let body = Rect::from_min_max(full.min, egui::pos2(full.right(), full.bottom() - foot_h));
        let foot = Rect::from_min_max(egui::pos2(full.left(), body.bottom()), full.max);
        let rows = step_rows(
            inputs.s,
            inputs.step,
            inputs.settle_ms,
            &inputs.calibration.result,
        );
        ui.scope_builder(
            egui::UiBuilder::new().max_rect(body.shrink2(egui::vec2(16.0, 14.0))),
            |ui| {
                egui::ScrollArea::vertical()
                    .id_salt("capture-plan-body")
                    .auto_shrink([false, false])
                    .show(ui, |ui| {
                        ui.spacing_mut().item_spacing.y = 0.0;
                        self.names(ui, inputs, palette, &mut out);
                        ui.add_space(10.0);
                        rig_step(
                            ui,
                            inputs,
                            &mut self.rig_open,
                            &mut self.rig,
                            palette,
                            &mut out,
                        );
                        exposure_step(ui, inputs, palette, &mut out);
                        depth_step(ui, inputs, &rows, &mut self.custom_step, palette, &mut out);
                        after_step(ui, inputs, palette, &mut out);
                        ui.add_space(4.0);
                        if style::link(ui, "Captures, storage and connection…", true, palette)
                            .clicked()
                        {
                            out.push(PlanIntent::OpenSettings);
                        }
                    });
            },
        );
        footer(ui, foot, inputs, &rows, palette, &mut out);
        for intent in &out {
            if let PlanIntent::OpenGuide(tab) = intent {
                self.guide = Some(*tab);
            }
        }
        out
    }

    fn names(
        &mut self,
        ui: &mut Ui,
        inputs: &PlanInputs<'_>,
        palette: &CapturePalette,
        out: &mut Vec<PlanIntent>,
    ) {
        let subjects = inputs.subjects;
        let w = (ui.available_width() - 10.0) / 2.0;
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 10.0;
            for (label, subject) in [("Subject", true), ("Stack name", false)] {
                ui.vertical(|ui| {
                    ui.set_width(w);
                    style::caps(ui, label, palette);
                    ui.add_space(5.0);
                    let value = if subject {
                        &mut self.subject
                    } else {
                        &mut self.stack_name
                    };
                    let edit = egui::TextEdit::singleline(value)
                        .id_salt(("capture-plan-name", subject))
                        .desired_width(w)
                        .min_size(egui::vec2(w, 28.0))
                        .vertical_align(egui::Align::Center)
                        .hint_text(if subject {
                            "Name the new subject"
                        } else {
                            "Name this stack"
                        })
                        .font(egui::FontId::proportional(13.0))
                        .text_color(palette.ink)
                        .background_color(palette.bg)
                        .margin(egui::Margin::symmetric(9, 4));
                    let r = ui.add(edit);
                    if subject && std::mem::take(&mut self.focus_subject) {
                        r.request_focus();
                    }
                    if r.lost_focus() {
                        consume_enter(ui);
                    }
                    ui.painter().rect_stroke(
                        r.rect,
                        0.0,
                        Stroke::new(1.0_f32, palette.line2),
                        egui::StrokeKind::Inside,
                    );
                    if r.changed() {
                        if subject {
                            // Typing names a new subject; choosing is on purpose.
                            self.chosen = None;
                            out.push(PlanIntent::SetSubject(self.subject.clone()));
                        } else {
                            out.push(PlanIntent::SetStackName(self.stack_name.clone()));
                        }
                    }
                    // The catalog's subjects that match what is typed, to
                    // choose one on purpose.
                    let list_id = ui.id().with("capture-subjects");
                    let over_list = ui.data(|d| d.get_temp::<bool>(list_id).unwrap_or(false));
                    if subject
                        && self.chosen.is_none()
                        && (r.has_focus() || over_list)
                        && !subjects.is_empty()
                    {
                        let typed = self.subject.trim().to_lowercase();
                        let matches: Vec<&SubjectChoice> = subjects
                            .iter()
                            .filter(|s| typed.is_empty() || s.name.to_lowercase().contains(&typed))
                            .take(8)
                            .collect();
                        if !matches.is_empty() {
                            let area = egui::Area::new(list_id)
                                .order(egui::Order::Foreground)
                                .fixed_pos(r.rect.left_bottom() + egui::vec2(0.0, 2.0));
                            let wide = (2.0 * w + 10.0).max(w);
                            let shown = area.show(ui.ctx(), |ui| {
                                egui::Frame::new()
                                    .fill(palette.panel)
                                    .stroke(Stroke::new(1.0_f32, palette.line2))
                                    .show(ui, |ui| {
                                        ui.set_width(wide - 2.0);
                                        style::caps(ui, "Add this stack to", palette);
                                        for choice in matches {
                                            if subject_row(ui, choice, wide - 2.0, palette)
                                                .clicked()
                                            {
                                                self.subject = choice.name.clone();
                                                self.chosen = Some(choice.id);
                                                out.push(PlanIntent::SetSubject(
                                                    choice.name.clone(),
                                                ));
                                            }
                                        }
                                    });
                            });
                            let over = shown.response.contains_pointer();
                            ui.data_mut(|d| d.insert_temp(list_id, over));
                        } else {
                            ui.data_mut(|d| d.insert_temp(list_id, false));
                        }
                    }
                });
            }
        });
        // Where the stack goes, said plainly (owner feedback, 2026-11-22).
        let destination = subject::destination(&self.subject, self.chosen, subjects);
        let ready = destination.ready();
        ui.add_space(7.0);
        ui.horizontal_top(|ui| {
            ui.spacing_mut().item_spacing.x = 7.0;
            let (mark_rect, _) = ui.allocate_exact_size(egui::vec2(8.0, 16.0), Sense::hover());
            style::mark(
                ui.painter(),
                mark_rect.center(),
                if ready { Mark::Ok } else { Mark::Warn },
                7.0,
                palette,
            );
            let job = style::job(
                &subject::sentence(&destination, inputs.subject_home),
                12.5,
                if ready { palette.ink2 } else { palette.ink },
                0.0,
            );
            ui.add(egui::Label::new(job).wrap());
        });
        // Anything a new capture would clear (owner feedback, 2026-11-23).
        let host = &inputs.s.host;
        let started = host.start_set
            || host.end_set
            || !host.samples.is_empty()
            || inputs.test_shot.stage != "idle"
            || inputs.calibration.stage != "idle"
            || !self.subject.trim().is_empty()
            || !self.stack_name.trim().is_empty();
        let idle = !host.phase.active()
            && !matches!(inputs.test_shot.stage, "capturing" | "reading")
            && matches!(inputs.calibration.stage, "idle" | "done" | "failed");
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 16.0;
            if self.chosen.is_some()
                && style::link(ui, "A new subject instead", true, palette).clicked()
            {
                self.subject.clear();
                self.chosen = None;
                self.focus_subject = true;
                out.push(PlanIntent::SetSubject(String::new()));
            }
            if started
                && style::link(ui, "New capture", idle, palette)
                    .on_hover_text(
                        "Start over: clears the subject, bounds, survey, test shot and step calibration. The rig's settings stay.",
                    )
                    .clicked()
            {
                out.push(PlanIntent::NewCapture);
            }
        });
    }
}

/// One subject in the subject field's list: its name, and its collection
/// and stacks at the right.
fn subject_row(
    ui: &mut Ui,
    choice: &SubjectChoice,
    width: f32,
    palette: &CapturePalette,
) -> Response {
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 26.0), Sense::click());
    if response.hovered() {
        ui.painter().rect_filled(rect, 0.0, palette.raised);
    }
    let name = style::paint_job(
        ui.painter(),
        egui::pos2(rect.left() + 8.0, rect.center().y),
        Align2::LEFT_CENTER,
        style::job(&choice.name, 13.0, palette.ink, 0.0),
    );
    if !choice.detail.is_empty() {
        let mut job = style::job(&choice.detail, 12.0, palette.ink3, 0.0);
        job.wrap.max_width = (rect.right() - 8.0 - name.right() - 12.0).max(0.0);
        job.wrap.max_rows = 1;
        style::paint_job(
            ui.painter(),
            egui::pos2(rect.right() - 8.0, rect.center().y),
            Align2::RIGHT_CENTER,
            job,
        );
    }
    response
}

/// A numbered step: its numeral (green when ready) and content.
fn step(ui: &mut Ui, n: u8, ready: bool, palette: &CapturePalette, content: impl FnOnce(&mut Ui)) {
    let top = ui.cursor().top();
    let left = ui.max_rect().left();
    let right = ui.max_rect().right();
    style::hairline(
        ui.painter(),
        egui::pos2(left, top + 0.5),
        egui::pos2(right, top + 0.5),
        palette.line,
    );
    ui.add_space(12.0);
    ui.horizontal_top(|ui| {
        ui.spacing_mut().item_spacing.x = 8.0;
        let (r, _) = ui.allocate_exact_size(egui::vec2(26.0, 26.0), Sense::hover());
        style::paint_job(
            ui.painter(),
            r.left_top() - egui::vec2(0.0, 3.0),
            Align2::LEFT_TOP,
            style::job(
                &n.to_string(),
                26.0,
                if ready { palette.ok } else { palette.ink3 },
                0.0,
            ),
        );
        ui.vertical(|ui| {
            ui.spacing_mut().item_spacing.y = 3.0;
            content(ui);
        });
    });
    ui.add_space(13.0);
}

/// A step's title row: the name, and an action at the right.
fn title(ui: &mut Ui, name: &str, palette: &CapturePalette, action: impl FnOnce(&mut Ui)) {
    ui.horizontal(|ui| {
        style::text(ui, name, 13.0, palette.ink).on_hover_text(name);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), action);
    });
}

fn note(ui: &mut Ui, text: &str, palette: &CapturePalette) {
    let mut job = style::job(&guide::unbreak(text), 12.5, palette.ink2, 0.0);
    job.wrap.max_width = ui.available_width();
    ui.label(job);
}

fn rig_step(
    ui: &mut Ui,
    inputs: &PlanInputs<'_>,
    open: &mut bool,
    editor: &mut RigEditor,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let rig_checks = [
        Check::Offline,
        Check::HostState,
        Check::Camera,
        Check::Failure,
        Check::NotEditable,
    ];
    let ready = !has(inputs.blockers, &rig_checks);
    let s = inputs.s;
    let values = RigValues::read(s, inputs.settle_ms, inputs.switches.check);
    step(ui, 1, ready, palette, |ui| {
        title(ui, "Rig", palette, |ui| {
            ui.spacing_mut().item_spacing.x = 10.0;
            if disclosure(ui, "Settings", *open, palette)
                .on_hover_text(
                    "Approach, settle, exposure timeout, light warm-up, power and error correction",
                )
                .clicked()
            {
                *open = !*open;
            }
            if !s.host.connected
                && s.fresh()
                && style::button(ui, "Connect", ButtonKind::Plain, 22.0, !s.pending, palette)
                    .clicked()
            {
                out.push(PlanIntent::Connect);
            }
        });
        note(ui, &rig_summary(s), palette);
        let line = rig_settings::summary(&values);
        if !line.is_empty() && !*open {
            let mut job = style::job(&line, 12.0, palette.ink3, 0.0);
            job.wrap.max_width = ui.available_width();
            if ui
                .add(egui::Label::new(job).sense(Sense::click()))
                .on_hover_cursor(egui::CursorIcon::PointingHand)
                .on_hover_text("Change the rig settings")
                .clicked()
            {
                *open = true;
            }
        }
        if let Some(b) = inputs
            .blockers
            .iter()
            .find(|b| rig_checks.contains(&b.check))
        {
            // A fault is red (P0 item 4); anything else waits in amber.
            let color = if matches!(b.check, Check::Failure | Check::HostState) {
                palette.bad
            } else {
                palette.warn
            };
            let mut job = style::job(&b.sentence, 12.5, color, 0.0);
            job.wrap.max_width = ui.available_width();
            let r = ui.add(egui::Label::new(job).sense(Sense::click()));
            if r.clicked()
                && let Some(fix) = b.fix
            {
                out.push(PlanIntent::Fix(fix));
            }
        }
        if *open {
            editor.show(ui, &values, s.host.plan.as_ref(), palette, out);
        }
    });
}

/// A tracked-capitals link with a drawn chevron: down when closed, up when
/// open.
fn disclosure(ui: &mut Ui, label: &str, open: bool, palette: &CapturePalette) -> egui::Response {
    let galley = ui
        .painter()
        .layout_job(style::caps_job(label, 10.5, palette.ink2));
    let size = galley.size() + egui::vec2(14.0, 0.0);
    let (rect, response) = ui.allocate_exact_size(size, Sense::click());
    let color = if response.hovered() {
        palette.ink
    } else {
        palette.ink2
    };
    ui.painter().galley(rect.min, galley, color);
    let c = egui::pos2(rect.right() - 4.0, rect.center().y);
    let (a, b) = if open { (2.0, -2.0) } else { (-2.0, 2.0) };
    let stroke = Stroke::new(1.2_f32, color);
    ui.painter()
        .line_segment([c + egui::vec2(-3.5, a), c + egui::vec2(0.0, b)], stroke);
    ui.painter()
        .line_segment([c + egui::vec2(0.0, b), c + egui::vec2(3.5, a)], stroke);
    response.on_hover_cursor(egui::CursorIcon::PointingHand)
}

/// A line of guidance in its tone, and under it the change it offers and
/// the way to the comparison panel.
fn guidance(
    ui: &mut Ui,
    line: Option<&guide::Line>,
    more: Option<GuideTab>,
    enabled: bool,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let action = line.and_then(|l| l.action.clone());
    ui.horizontal_wrapped(|ui| {
        ui.spacing_mut().item_spacing = egui::vec2(10.0, 2.0);
        if let Some(line) = line {
            let color = match line.tone {
                Tone::Note => palette.ink2,
                Tone::Good => palette.ok,
                Tone::Warn => palette.warn,
            };
            ui.add(
                egui::Label::new(
                    egui::RichText::new(guide::unbreak(&line.text))
                        .size(12.0)
                        .color(color),
                )
                .wrap(),
            );
        }
        if let Some((label, intent)) = action
            && style::link(ui, label, enabled, palette).clicked()
        {
            out.push(intent);
        }
        if let Some(tab) = more
            && style::link(ui, "What changes", true, palette)
                .on_hover_text("Compare the choices: noise, detail, time and disk")
                .clicked()
        {
            out.push(PlanIntent::OpenGuide(tab));
        }
    });
}

fn exposure_step(
    ui: &mut Ui,
    inputs: &PlanInputs<'_>,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let s = inputs.s;
    let exposure = s.host.exposure.as_ref();
    let ready = exposure.is_some() && !has(inputs.blockers, &[Check::Exposure]);
    let editable = s.fresh() && s.host.editable && !s.pending;
    step(ui, 2, ready, palette, |ui| {
        let running = matches!(inputs.test_shot.stage, "capturing" | "reading");
        title(ui, "Exposure", palette, |ui| {
            if running {
                if inputs.test_shot.stage == "capturing"
                    && style::button(ui, "Stop waiting", ButtonKind::Quiet, 22.0, true, palette)
                        .clicked()
                {
                    out.push(PlanIntent::StopTestShot);
                }
            } else if style::button(
                ui,
                "Test shot",
                ButtonKind::Plain,
                22.0,
                editable && s.host.position.is_some(),
                palette,
            )
            .on_hover_text(
                "One exposure at the current focus, read on the RAW. It is not kept as a stack.",
            )
            .clicked()
            {
                out.push(PlanIntent::TestShot);
            }
        });
        ui.add_space(5.0);
        let w = (ui.available_width() - 8.0) / 2.0;
        match exposure {
            Some(e) => {
                let (iso, shutter) = (e.iso.unwrap_or(0), e.shutter.unwrap_or(0));
                ui.horizontal(|ui| {
                    ui.spacing_mut().item_spacing.x = 8.0;
                    let can = editable && e.writable;
                    if let Some(code) = picker(
                        ui,
                        "capture-iso",
                        w,
                        &style::iso_label(iso),
                        &e.iso_options,
                        style::iso_label,
                        can,
                        palette,
                    ) {
                        out.push(PlanIntent::Exposure { iso: code, shutter });
                    }
                    if let Some(code) = picker(
                        ui,
                        "capture-shutter",
                        w,
                        &style::shutter_label(shutter),
                        &e.shutter_options,
                        style::shutter_label,
                        can,
                        palette,
                    ) {
                        out.push(PlanIntent::Exposure { iso, shutter: code });
                    }
                });
                if let Some(problem) = &e.problem {
                    let mut job = style::job(problem, 12.5, palette.warn, 0.0);
                    job.wrap.max_width = ui.available_width();
                    ui.label(job);
                }
            }
            None => note(
                ui,
                "The camera reports its exposure once connected",
                palette,
            ),
        }
        ui.add_space(3.0);
        if let Some(line) = test_shot_sentence(&inputs.test_shot) {
            note(ui, &line, palette);
        }
        // Plan Q7: is the picture still enough for the exposure?
        let (stage, line) = &inputs.stillness;
        let checking = matches!(*stage, "magnifying" | "watching" | "measuring");
        ui.horizontal_wrapped(|ui| {
            ui.spacing_mut().item_spacing = egui::vec2(10.0, 2.0);
            if let Some(line) = line {
                let colour = if *stage == "done" && !line.starts_with("Still") {
                    palette.warn
                } else {
                    palette.ink2
                };
                ui.add(
                    egui::Label::new(egui::RichText::new(line).size(12.0).color(colour)).wrap(),
                );
            }
            if checking {
                if *stage != "measuring" && style::link(ui, "Stop", true, palette).clicked() {
                    out.push(PlanIntent::StopStillness);
                }
            } else if style::link(
                ui,
                if line.is_some() {
                    "Check stillness again"
                } else {
                    "Check stillness (20 s)"
                },
                editable && s.host.preview.available,
                palette,
            )
            .on_hover_text(
                "Watches the magnified live view for 20 s and says how far the picture sways, along which axis, and the longest exposure that keeps the blur under a quarter pixel",
            )
            .clicked()
            {
                out.push(PlanIntent::CheckStillness);
            }
        });
        if let Some(e) = exposure {
            let m = guide::metered(&inputs.test_shot);
            let advice = guide::advise(e, m.as_ref());
            let rows = guide::exposure_rows(
                s,
                inputs.settle_ms,
                marked_planes(s, inputs.step),
                m.as_ref(),
                &advice,
            );
            let line = guide::exposure_line(&advice, &rows);
            guidance(
                ui,
                line.as_ref(),
                Some(GuideTab::Exposure),
                editable && e.writable,
                palette,
                out,
            );
        }
    });
}

/// The planes of the marked range at `step`, once both bounds are set.
pub(crate) fn marked_planes(s: &Snapshot, step: u16) -> Option<usize> {
    s.host.bounds_set().then(|| {
        let (start, end) = s.host.plan_bounds();
        plane_count(start, end, step.max(1))
    })
}

/// A picker field: the value with a chevron; a click lists `options`.
#[allow(clippy::too_many_arguments)]
fn picker(
    ui: &mut Ui,
    id: &str,
    width: f32,
    value: &str,
    options: &[u64],
    label: fn(u64) -> String,
    enabled: bool,
    palette: &CapturePalette,
) -> Option<u64> {
    let sense = if enabled && !options.is_empty() {
        Sense::click()
    } else {
        Sense::hover()
    };
    let r = style::field(ui, width, None, value, true, sense, palette);
    let mut chosen = None;
    egui::Popup::menu(&r)
        .id(egui::Id::new(id))
        .width(width)
        .show(|ui| {
            egui::ScrollArea::vertical()
                .max_height(260.0)
                .show(ui, |ui| {
                    for &code in options {
                        if ui.selectable_label(false, label(code)).clicked() {
                            chosen = Some(code);
                        }
                    }
                });
        });
    chosen
}

fn depth_step(
    ui: &mut Ui,
    inputs: &PlanInputs<'_>,
    rows: &[StepRow],
    custom: &mut String,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let s = inputs.s;
    let host = &s.host;
    let ready = host.bounds_set()
        && !has(
            inputs.blockers,
            &[Check::StartMark, Check::EndMark, Check::Plan, Check::Edits],
        );
    let editable = s.fresh() && host.editable && !s.pending;
    let calibrating = !matches!(inputs.calibration.stage, "idle" | "done" | "failed");
    step(ui, 3, ready, palette, |ui| {
        title(ui, "Depth", palette, |ui| {
            if calibrating {
                if style::button(ui, "Stop waiting", ButtonKind::Quiet, 22.0, true, palette).clicked() {
                    out.push(PlanIntent::StopCalibration);
                }
            } else if style::button(
                ui,
                "Calibrate step",
                ButtonKind::Plain,
                22.0,
                editable && host.bounds_set() && inputs.engine,
                palette,
            )
            .on_hover_text("Takes 25 single RAWs around the middle of the marked range, measures how far detail stays sharp and deletes the survey.")
            .clicked()
            {
                out.push(PlanIntent::Calibrate);
            }
        });
        ui.add_space(5.0);
        let w = (ui.available_width() - 8.0) / 2.0;
        let (start, end) = host.plan_bounds();
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            let shown = |set: bool, p: u16| {
                if set {
                    style::focus_units(p)
                } else {
                    "—".into()
                }
            };
            style::field(
                ui,
                w,
                Some("Start"),
                &shown(host.start_set, start),
                false,
                Sense::hover(),
                palette,
            );
            style::field(
                ui,
                w,
                Some("End"),
                &shown(host.end_set, end),
                false,
                Sense::hover(),
                palette,
            );
        });
        ui.add_space(4.0);
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            if style::button(
                ui,
                "Mark start here",
                ButtonKind::Plain,
                22.0,
                editable,
                palette,
            )
            .clicked()
            {
                out.push(PlanIntent::MarkStart);
            }
            if style::button(
                ui,
                "Mark end here",
                ButtonKind::Plain,
                22.0,
                editable,
                palette,
            )
            .clicked()
            {
                out.push(PlanIntent::MarkEnd);
            }
            if host.bounds_set() {
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    style::text(
                        ui,
                        &format!("{} units", start.abs_diff(end)),
                        12.5,
                        palette.ink3,
                    );
                });
            }
        });
        if let Some(line) = guide::bounds_line(s, inputs.step, inputs.settle_ms) {
            ui.add_space(2.0);
            guidance(ui, Some(&line), None, editable, palette, out);
        }
        ui.add_space(6.0);
        if !rows.is_empty() {
            let width = inputs.calibration.result["width"].as_f64();
            let typed = parse_step(custom);
            let custom_row = typed
                .as_ref()
                .ok()
                .map(|&v| step_row(s, v, inputs.step, inputs.settle_ms, width));
            if let Some(step) = step_table(ui, rows, custom_row.as_ref(), custom, editable, palette)
            {
                out.push(PlanIntent::SetStep(step));
            }
            match (&typed, custom_row.as_ref()) {
                (Ok(v), Some(row)) if !row.current => {
                    ui.horizontal(|ui| {
                        if style::link(ui, &format!("Use step {v}"), editable, palette).clicked() {
                            out.push(PlanIntent::SetStep(*v));
                        }
                        style::text(ui, "or press Enter", 11.5, palette.ink3);
                    });
                }
                (Err(e), _) if !e.is_empty() => {
                    style::text(ui, e, 11.5, palette.warn);
                }
                _ => {}
            }
            ui.add_space(4.0);
            overlap_diagram(ui, inputs, palette);
            ui.add_space(4.0);
            let line = guide::Line {
                text: guide::step_line(rows, &inputs.calibration),
                tone: Tone::Note,
                action: None,
            };
            guidance(
                ui,
                Some(&line),
                Some(GuideTab::Step),
                editable,
                palette,
                out,
            );
        }
        ui.add_space(6.0);
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            let four = host.shots_per_plane == Some(4);
            if style::toggle(ui, four, editable && host.offers_four_shot(), palette).clicked() {
                out.push(PlanIntent::SetFourShot(!four));
            }
            style::text(ui, "4-shot pixel shift", 13.0, palette.ink);
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.spacing_mut().item_spacing.x = 8.0;
                let r = style::field(
                    ui,
                    74.0,
                    None,
                    &format!("{} ms", inputs.settle_ms),
                    true,
                    if editable {
                        Sense::click()
                    } else {
                        Sense::hover()
                    },
                    palette,
                );
                egui::Popup::menu(&r)
                    .id(egui::Id::new("capture-settle"))
                    .width(300.0)
                    .align(egui::RectAlign::BOTTOM_END)
                    .show(|ui| {
                        if let Some(ms) = settle_menu(ui, inputs, palette) {
                            out.push(PlanIntent::SetSettle(ms));
                        }
                    });
                style::text(ui, "Settle", 13.0, palette.ink3);
            });
        });
    });
}

/// The settle choices with what each costs and what the rig measured.
fn settle_menu(ui: &mut Ui, inputs: &PlanInputs<'_>, palette: &CapturePalette) -> Option<u32> {
    ui.set_width(300.0);
    let rows = guide::settle_rows(
        inputs.s,
        marked_planes(inputs.s, inputs.step),
        inputs.settle_ms,
    );
    let cols = [
        guide::Col {
            head: "Settle",
            left: true,
        },
        guide::Col {
            head: "A plane",
            left: false,
        },
        guide::Col {
            head: "Stack",
            left: false,
        },
        guide::Col {
            head: "Passed",
            left: false,
        },
    ];
    let table: Vec<guide::Row> = rows
        .iter()
        .map(|r| guide::Row {
            cells: vec![
                format!("{} ms", r.ms),
                r.plane.map_or("—".into(), |p| format!("{p:.1} s")),
                r.stack.map_or("—".into(), style::minutes),
                r.still.unwrap_or("—").into(),
            ],
            current: r.current,
            ..Default::default()
        })
        .collect();
    let chosen = guide::ruled_table(ui, "settle-menu", &cols, &table, true, palette);
    let mut job = style::job(
        "Up to 500 ms is free: the lens moves while the last RAW is fetched. The plane after the approach always settles 2 s. Passed: groups the checker accepted in a still room (measured; † before that rule).",
        11.0,
        palette.ink3,
        0.0,
    );
    job.wrap.max_width = ui.available_width();
    ui.label(job);
    if chosen.is_some() {
        ui.close();
    }
    chosen.map(|i| rows[i].ms)
}

/// The step table; a click on a row chooses its step. Its last row takes a
/// typed step and shows what it would give; Enter there chooses it.
fn step_table(
    ui: &mut Ui,
    rows: &[StepRow],
    custom: Option<&StepRow>,
    custom_text: &mut String,
    editable: bool,
    palette: &CapturePalette,
) -> Option<u16> {
    let width = ui.available_width();
    let cols = [0.0, 0.36, 0.56, 0.78, 1.0];
    let row_h = 25.0;
    let (rect, _) = ui.allocate_exact_size(
        egui::vec2(width, 18.0 + row_h * (rows.len() + 1) as f32),
        Sense::hover(),
    );
    let p = ui.painter();
    let x = |f: f32| rect.left() + f * width;
    for (i, head) in ["Step", "Overlap", "Planes", "Time", "Disk"]
        .into_iter()
        .enumerate()
    {
        let (pos, anchor) = if i == 0 {
            (egui::pos2(x(0.0), rect.top() + 3.0), Align2::LEFT_TOP)
        } else {
            (egui::pos2(x(cols[i]), rect.top() + 3.0), Align2::RIGHT_TOP)
        };
        style::paint_job(p, pos, anchor, style::caps_job(head, 9.5, palette.ink3));
    }
    let mut chosen = None;
    let paint_cells = |p: &egui::Painter, r: Rect, row: &StepRow, step_cell: bool| {
        let color = if row.risk {
            palette.warn
        } else if row.current {
            palette.ink
        } else {
            palette.ink2
        };
        let tracking = if row.current { 0.25 } else { 0.0 };
        let cell = |text: &str, f: f32, left: bool| {
            let inset = if row.current { 6.0 } else { 0.0 };
            let (pos, anchor) = if left {
                (egui::pos2(x(f) + inset, r.center().y), Align2::LEFT_CENTER)
            } else {
                (
                    egui::pos2(x(f) - if f >= 1.0 { inset } else { 0.0 }, r.center().y),
                    Align2::RIGHT_CENTER,
                )
            };
            style::paint_job(p, pos, anchor, style::job(text, 12.0, color, tracking))
        };
        if step_cell {
            cell(&row.step.to_string(), 0.0, true);
        }
        let overlap = row
            .overlap
            .map_or("—".into(), |o| format!("{:.0}×", o.floor().max(0.0)));
        let ov = cell(
            &overlap,
            cols[1] - if row.risk { 0.035 } else { 0.0 },
            false,
        );
        if row.risk {
            style::mark(
                p,
                egui::pos2(ov.right() + 7.0, r.center().y),
                Mark::Warn,
                7.0,
                palette,
            );
        }
        cell(&row.planes.to_string(), cols[2], false);
        cell(
            &row.seconds.map_or("—".into(), style::minutes),
            cols[3],
            false,
        );
        cell(
            &row.bytes.map_or("—".into(), style::gigabytes),
            cols[4],
            false,
        );
    };
    for (i, row) in rows.iter().enumerate() {
        let r = Rect::from_min_size(
            egui::pos2(rect.left(), rect.top() + 18.0 + row_h * i as f32),
            egui::vec2(width, row_h),
        );
        let response = ui.interact(
            r,
            ui.id().with(("capture-step-row", row.step)),
            if editable {
                Sense::click()
            } else {
                Sense::hover()
            },
        );
        let p = ui.painter();
        if row.current {
            p.rect_filled(r, 0.0, palette.accent_soft);
            p.line_segment(
                [r.left_top(), r.right_top()],
                Stroke::new(1.0_f32, palette.accent),
            );
            p.line_segment(
                [r.left_bottom(), r.right_bottom()],
                Stroke::new(1.0_f32, palette.accent),
            );
        } else {
            style::hairline(p, r.left_top(), r.right_top(), palette.line);
            if response.hovered() && editable {
                p.rect_filled(r, 0.0, palette.raised);
            }
        }
        paint_cells(p, r, row, true);
        let response = match &row.detail {
            Some(d) => response.on_hover_text(format!(
                "Step {}: about {} of fine detail kept (estimate from two measured stacks){}",
                row.step,
                guide::detail_label(d),
                if row.risk {
                    "; coarser than width / 5 loses detail between planes"
                } else {
                    ""
                }
            )),
            None => response,
        };
        if response.clicked() && !row.current {
            chosen = Some(row.step);
        }
    }
    // The typed step.
    let r = Rect::from_min_size(
        egui::pos2(rect.left(), rect.top() + 18.0 + row_h * rows.len() as f32),
        egui::vec2(width, row_h),
    );
    style::hairline(ui.painter(), r.left_top(), r.right_top(), palette.line);
    style::hairline(
        ui.painter(),
        r.left_bottom(),
        r.right_bottom(),
        palette.line,
    );
    let field = Rect::from_min_size(
        egui::pos2(r.left(), r.top() + 2.5),
        egui::vec2((width * 0.18).clamp(44.0, 64.0), row_h - 5.0),
    );
    let mut edit_ui = ui.new_child(egui::UiBuilder::new().max_rect(field));
    let edit = egui::TextEdit::singleline(custom_text)
        .id(ui.id().with("capture-step-custom"))
        .desired_width(field.width())
        .hint_text("other")
        .font(egui::FontId::proportional(12.0))
        .text_color(palette.ink)
        .background_color(palette.bg)
        .vertical_align(egui::Align::Center)
        .margin(egui::Margin::symmetric(4, 1))
        .interactive(editable)
        .char_limit(5);
    let response = edit_ui.add_sized(field.size(), edit);
    ui.painter().rect_stroke(
        field,
        0.0,
        Stroke::new(
            1.0_f32,
            if response.has_focus() {
                palette.accent
            } else {
                palette.line2
            },
        ),
        egui::StrokeKind::Inside,
    );
    let response = response.on_hover_text("Type any step in focus units; Enter uses it");
    custom_text.retain(|c| c.is_ascii_digit());
    let entered = response.lost_focus() && consume_enter(ui);
    if let Some(row) = custom {
        paint_cells(ui.painter(), r, row, false);
        if entered && editable && !row.current {
            chosen = Some(row.step);
        }
    }
    chosen
}

/// Takes an Enter that ended typing in a field, so the station's Enter
/// (Start stack) does not see it.
pub(crate) fn consume_enter(ui: &Ui) -> bool {
    ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Enter))
}

/// Seven overlapping slices: how many planes keep a point sharp at the
/// plan's step, and the line that says so.
fn overlap_diagram(ui: &mut Ui, inputs: &PlanInputs<'_>, palette: &CapturePalette) {
    let width = ui.available_width();
    let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 48.0), Sense::hover());
    let p = ui.painter();
    let sharp = inputs.calibration.result["width"].as_f64();
    if let Some(w) = sharp {
        let k = (w / f64::from(inputs.step.max(1))).max(1.0) as f32;
        let slice = (width * 0.53).min(150.0);
        let offset = slice / k;
        for i in 0..7 {
            let x = rect.left() + offset * i as f32;
            if x + slice > rect.right() + slice {
                break;
            }
            p.rect_filled(
                Rect::from_min_size(
                    egui::pos2(x, rect.top() + 2.0 + 4.0 * i as f32),
                    egui::vec2(slice, 2.0),
                ),
                0.0,
                palette.ok.gamma_multiply(0.85),
            );
        }
        let index = rect.left() + offset * 6.0 + offset * 0.6;
        p.line_segment(
            [
                egui::pos2(index, rect.top()),
                egui::pos2(index, rect.top() + 30.0),
            ],
            Stroke::new(1.0_f32, palette.ink),
        );
    }
    style::paint_job(
        p,
        egui::pos2(rect.left(), rect.bottom()),
        Align2::LEFT_BOTTOM,
        style::job(
            &calibration_sentence(&inputs.calibration, inputs.step),
            11.5,
            palette.ink2,
            0.0,
        ),
    );
}

fn after_step(
    ui: &mut Ui,
    inputs: &PlanInputs<'_>,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let sw = inputs.switches;
    let s = inputs.s;
    let between = s.fresh() && !s.pending && !s.host.phase.active();
    step(ui, 4, true, palette, |ui| {
        style::text(ui, "While it runs, and after", 13.0, palette.ink);
        if style::option(
            ui,
            sw.check,
            "Check each plane as it arrives",
            None,
            true,
            palette,
        ) {
            out.push(PlanIntent::SetCheck(!sw.check));
        }
        if let Some(retake) = sw.retake
            && style::option(
                ui,
                retake,
                "Retake planes that fail",
                Some("adds a few seconds each"),
                between && (sw.check || retake),
                palette,
            )
        {
            out.push(PlanIntent::SetRetake(!retake));
        }
        if style::option(
            ui,
            sw.stack_when_done,
            "Stack it when the capture finishes",
            None,
            sw.check,
            palette,
        ) {
            out.push(PlanIntent::SetStackWhenDone(!sw.stack_when_done));
        }
        if let Some(down) = sw.power_down
            && style::option(
                ui,
                down,
                "Then power the rig down",
                Some("after the last RAW is saved"),
                between,
                palette,
            )
        {
            out.push(PlanIntent::SetPowerDown(!down));
        }
    });
}

fn footer(
    ui: &mut Ui,
    foot: Rect,
    inputs: &PlanInputs<'_>,
    rows: &[StepRow],
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    style::hairline(
        ui.painter(),
        foot.left_top() + egui::vec2(0.0, 0.5),
        foot.right_top() + egui::vec2(0.0, 0.5),
        palette.line,
    );
    let s = inputs.s;
    let (ends, disk) = footer_lines(s, rows);
    let armed = super::schedule_ui::armed_label(s);
    ui.scope_builder(
        egui::UiBuilder::new().max_rect(foot.shrink2(egui::vec2(16.0, 12.0))),
        |ui| {
            ui.horizontal(|ui| {
                let job = match (&armed, &ends) {
                    (Some(armed), _) => style::job(armed, 12.5, palette.accent, 0.0),
                    (None, Some(ends)) => {
                        let mut job = style::job("Ends about ", 12.5, palette.ink2, 0.0);
                        job.append(
                            ends,
                            0.0,
                            egui::TextFormat {
                                font_id: egui::FontId::proportional(12.5),
                                color: palette.ink,
                                ..Default::default()
                            },
                        );
                        job
                    }
                    (None, None) => style::job("", 12.5, palette.ink2, 0.0),
                };
                ui.label(job);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    style::text(ui, &disk, 12.5, palette.ink2);
                });
            });
            ui.add_space(8.0);
            ui.horizontal(|ui| {
                ui.spacing_mut().item_spacing.x = 8.0;
                let start = inputs.blockers.is_empty();
                let label = if s.host.schedule_stage() == Some("armed") {
                    "Start stack now"
                } else {
                    "Start stack"
                };
                let w = ui.available_width() - 106.0 - 8.0;
                let r = style::button_sized(
                    ui,
                    label,
                    ButtonKind::Primary,
                    egui::vec2(w, 36.0),
                    start,
                    palette,
                );
                let r = match inputs.blockers.first() {
                    Some(b) => r.on_disabled_hover_text(&b.sentence),
                    None => r,
                };
                if r.clicked() {
                    out.push(PlanIntent::Start);
                }
                // An armed schedule opens the dialog to see or cancel it.
                let armed_now = s.host.schedule_stage() == Some("armed");
                let can_schedule = s.host.schedule.is_some()
                    && (armed_now
                        || (s.host.schedule_stage() != Some("running")
                            && super::preflight::can_schedule(inputs.blockers)));
                if style::button_sized(
                    ui,
                    if armed_now {
                        "Scheduled…"
                    } else {
                        "Schedule…"
                    },
                    ButtonKind::Plain,
                    egui::vec2(106.0, 36.0),
                    can_schedule,
                    palette,
                )
                .clicked()
                {
                    out.push(PlanIntent::Schedule);
                }
            });
        },
    );
}

#[cfg(test)]
#[path = "capture-plan-tests.rs"]
mod tests;
