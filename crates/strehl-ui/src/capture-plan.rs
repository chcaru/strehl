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

use eframe::egui::{self, Align2, Rect, Sense, Stroke, Ui};
use serde_json::Value;

use super::preflight::{Blocker, Check, Fix};
use super::style::{self, ButtonKind, CapturePalette, Mark};
use crate::capture_client::Snapshot;
use crate::capture_workspace::test_shot::RawLevels;

/// Steps offered in the table besides the plan's and the calibrated one.
pub(crate) const CANDIDATE_STEPS: [u16; 4] = [5, 7, 10, 16];
/// Overlap below which fine detail measurably drops between planes:
/// `strehl focus-step`'s EDGE (step = width / 3.6 lost 2-3 % of detail
/// amplitude on the scarab stack). Rows below it are marked.
pub(crate) const DETAIL_LIMIT: f64 = strehl_cli::focus_step_cmd::EDGE;
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
    pub switches: Switches,
    /// The desktop can run the engine (calibration needs it).
    pub engine: bool,
    /// The catalog's subjects, offered for the subject field.
    pub subjects: &'a [String],
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
    SetFourShot(bool),
    SetCheck(bool),
    SetRetake(bool),
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
}

/// The inspector's own state: the names being typed and open pickers.
#[derive(Default)]
pub(crate) struct PlanView {
    pub subject: String,
    pub stack_name: String,
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
    let host = &s.host;
    let shutter = host.exposure.as_ref()?.shutter?;
    let plane = strehl_capture::timing::initial_plane(shutter, settle_ms, host.shots())?;
    let warmup = host
        .power
        .as_ref()
        .filter(|p| p.manage_stack)
        .and_then(|p| p.warmup_seconds)
        .unwrap_or(0);
    Some(
        (plane.mul_f64(planes as f64)
            + strehl_capture::timing::initial_setup(settle_ms)
            + std::time::Duration::from_secs(warmup))
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
    let (Some(plan), true) = (host.plan.as_ref(), host.bounds_set()) else {
        return Vec::new();
    };
    let width = calibration["width"].as_f64();
    let mut steps: Vec<u16> = CANDIDATE_STEPS.to_vec();
    if let Some(suggested) = calibration["suggested_step"].as_u64() {
        steps.push(suggested.clamp(1, 65535) as u16);
    }
    steps.push(step.max(1));
    steps.sort_unstable();
    steps.dedup();
    let per_raw = expected_per_raw(s);
    let shots = host.shots() as usize;
    steps
        .into_iter()
        .map(|candidate| {
            let planes = plane_count(plan.start, plan.end, candidate);
            let overlap = width.map(|w| w / f64::from(candidate));
            StepRow {
                step: candidate,
                overlap,
                planes,
                seconds: stack_seconds(s, planes, settle_ms),
                bytes: per_raw
                    .map(|b| b * (planes * shots) as u64)
                    .or_else(|| worst_bytes(s, planes * shots)),
                current: candidate == step,
                risk: overlap.is_some_and(|o| o < DETAIL_LIMIT),
            }
        })
        .collect()
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
        let clipped = if levels.clipped_share <= 0.0 {
            "nothing clipped".to_owned()
        } else {
            format!("{:.2} % clipped", 100.0 * levels.clipped_share)
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
                        self.names(ui, inputs.subjects, palette, &mut out);
                        ui.add_space(10.0);
                        rig_step(ui, inputs, palette, &mut out);
                        exposure_step(ui, inputs, palette, &mut out);
                        depth_step(ui, inputs, &rows, palette, &mut out);
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
        out
    }

    fn names(
        &mut self,
        ui: &mut Ui,
        subjects: &[String],
        palette: &CapturePalette,
        out: &mut Vec<PlanIntent>,
    ) {
        let w = (ui.available_width() - 10.0) / 2.0;
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 10.0;
            for (label, value, subject) in [
                ("Subject", &mut self.subject, true),
                ("Stack name", &mut self.stack_name, false),
            ] {
                ui.vertical(|ui| {
                    ui.set_width(w);
                    style::caps(ui, label, palette);
                    ui.add_space(5.0);
                    let edit = egui::TextEdit::singleline(value)
                        .desired_width(w)
                        .min_size(egui::vec2(w, 28.0))
                        .vertical_align(egui::Align::Center)
                        .hint_text(if subject {
                            "Name the subject"
                        } else {
                            "Name this stack"
                        })
                        .font(egui::FontId::proportional(13.0))
                        .text_color(palette.ink)
                        .background_color(palette.bg)
                        .margin(egui::Margin::symmetric(9, 4));
                    let r = ui.add(edit);
                    ui.painter().rect_stroke(
                        r.rect,
                        0.0,
                        Stroke::new(1.0_f32, palette.line2),
                        egui::StrokeKind::Inside,
                    );
                    if r.changed() {
                        out.push(if subject {
                            PlanIntent::SetSubject(value.clone())
                        } else {
                            PlanIntent::SetStackName(value.clone())
                        });
                    }
                    // The catalog's subjects that match what is typed.
                    let list_id = ui.id().with("capture-subjects");
                    let over_list = ui.data(|d| d.get_temp::<bool>(list_id).unwrap_or(false));
                    if subject && (r.has_focus() || over_list) && !subjects.is_empty() {
                        let typed = value.trim().to_lowercase();
                        let matches: Vec<&String> = subjects
                            .iter()
                            .filter(|s| typed.is_empty() || s.to_lowercase().contains(&typed))
                            .filter(|s| s.to_lowercase() != typed)
                            .take(8)
                            .collect();
                        if !matches.is_empty() {
                            let area = egui::Area::new(list_id)
                                .order(egui::Order::Foreground)
                                .fixed_pos(r.rect.left_bottom() + egui::vec2(0.0, 2.0));
                            let shown = area.show(ui.ctx(), |ui| {
                                egui::Frame::new()
                                    .fill(palette.panel)
                                    .stroke(Stroke::new(1.0_f32, palette.line2))
                                    .show(ui, |ui| {
                                        ui.set_width(w - 2.0);
                                        for name in matches {
                                            if ui.selectable_label(false, name.as_str()).clicked() {
                                                *value = name.clone();
                                                out.push(PlanIntent::SetSubject(name.clone()));
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
    }
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
    let mut job = style::job(text, 12.5, palette.ink2, 0.0);
    job.wrap.max_width = ui.available_width();
    ui.label(job);
}

fn rig_step(
    ui: &mut Ui,
    inputs: &PlanInputs<'_>,
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
    step(ui, 1, ready, palette, |ui| {
        title(ui, "Rig", palette, |ui| {
            if !s.host.connected && s.fresh() {
                if style::button(ui, "Connect", ButtonKind::Plain, 22.0, !s.pending, palette)
                    .clicked()
                {
                    out.push(PlanIntent::Connect);
                }
            } else if style::link(ui, "Rig…", true, palette).clicked() {
                out.push(PlanIntent::OpenRig);
            }
        });
        note(ui, &rig_summary(s), palette);
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
    });
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
        ui.add_space(6.0);
        if !rows.is_empty() {
            if let Some(step) = step_table(ui, rows, editable, palette) {
                out.push(PlanIntent::SetStep(step));
            }
            overlap_diagram(ui, inputs, palette);
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
                    false,
                    if editable {
                        Sense::click()
                    } else {
                        Sense::hover()
                    },
                    palette,
                );
                egui::Popup::menu(&r)
                    .id(egui::Id::new("capture-settle"))
                    .show(|ui| {
                        for ms in SETTLE_CHOICES {
                            if ui
                                .selectable_label(ms == inputs.settle_ms, format!("{ms} ms"))
                                .clicked()
                            {
                                out.push(PlanIntent::SetSettle(ms));
                            }
                        }
                    });
                style::text(ui, "Settle", 13.0, palette.ink3);
            });
        });
    });
}

/// The step table; a click on a row chooses its step.
fn step_table(
    ui: &mut Ui,
    rows: &[StepRow],
    editable: bool,
    palette: &CapturePalette,
) -> Option<u16> {
    let width = ui.available_width();
    let cols = [0.0, 0.36, 0.56, 0.78, 1.0];
    let row_h = 25.0;
    let (rect, _) = ui.allocate_exact_size(
        egui::vec2(width, 18.0 + row_h * rows.len() as f32),
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
        cell(&row.step.to_string(), 0.0, true);
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
        if response.clicked() && !row.current {
            chosen = Some(row.step);
        }
    }
    chosen
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
    ui.scope_builder(
        egui::UiBuilder::new().max_rect(foot.shrink2(egui::vec2(16.0, 12.0))),
        |ui| {
            ui.horizontal(|ui| {
                let mut job = style::job("Ends about ", 12.5, palette.ink2, 0.0);
                if let Some(ends) = &ends {
                    job.append(
                        ends,
                        0.0,
                        egui::TextFormat {
                            font_id: egui::FontId::proportional(12.5),
                            color: palette.ink,
                            ..Default::default()
                        },
                    );
                } else {
                    job = style::job("", 12.5, palette.ink2, 0.0);
                }
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
                let can_schedule = s.host.schedule.is_some()
                    && !matches!(s.host.schedule_stage(), Some("armed" | "running"))
                    && super::preflight::can_schedule(inputs.blockers);
                if style::button_sized(
                    ui,
                    "Schedule…",
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
