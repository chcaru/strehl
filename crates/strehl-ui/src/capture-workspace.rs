//! Native Capture workspace: camera controls, preview and PC storage in one tab.
//!
//! The model behind the Studio 2 Capture station lives here and in its
//! modules: the typed host state (`capture-host.rs`), the pre-flight list
//! that alone decides Start (`capture-preflight.rs`), the test shot
//! (`capture-test-shot.rs`), calibration and engine jobs with their time
//! limits (`capture-tools.rs`), the checker's per-plane records
//! (`capture-follow.rs`) and the connection cadence (`capture-client.rs`).
//! The calls the shell makes are listed at [`CaptureWorkspace::poll_background`].
use crate::{
    capture_client::{Cadence, Config, Connection, Snapshot, host::HostPhase},
    theme::{ACCENT, AMBER, BG, GREEN, INK, MUTED, PANEL},
};
use eframe::egui::{self, RichText};
use serde_json::{Value, json};
use std::{
    path::PathBuf,
    sync::mpsc,
    time::{Duration, Instant},
};
use strehl_capture::{
    model::{Plan, Roi},
    power::Outlet,
    session::{Command, CommandRequest, PositionsKind},
};
#[path = "capture-flight.rs"]
pub(crate) mod flight;
#[path = "capture-follow.rs"]
pub(crate) mod follow;
#[path = "capture-glance.rs"]
pub(crate) mod glance;
#[path = "capture-live.rs"]
pub(crate) mod live;
#[path = "capture-plan.rs"]
pub(crate) mod plan;
#[path = "capture-preflight.rs"]
pub(crate) mod preflight;
#[path = "capture-rail.rs"]
pub(crate) mod rail;
#[path = "capture-schedule.rs"]
mod schedule_ui;
#[path = "capture-station.rs"]
pub(crate) mod station;
#[path = "capture-style.rs"]
pub(crate) mod style;
#[path = "capture-test-shot.rs"]
pub(crate) mod test_shot;
#[path = "capture-tools.rs"]
pub(crate) mod tools;

/// Failure red, the Studio 2 palette's `#e5604c`. LOCAL STAND-IN: the shell
/// adds a red token to `theme.rs`; replace this constant with it then.
const FAULT_RED: egui::Color32 = egui::Color32::from_rgb(0xe5, 0x60, 0x4c);

/// A camera action that waits for a second click.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Confirm {
    /// Stop the running sequence.
    Stop,
    /// Disconnect the camera.
    Disconnect,
    /// Shut the camera down and switch its outlet off.
    ShutDown,
}

pub(crate) struct CaptureWorkspace {
    config: Config,
    path: PathBuf,
    connection: Option<Connection>,
    pub error: Option<String>,
    texture: Option<(u64, egui::TextureHandle)>,
    draft: Plan,
    confirmed_plan: Plan,
    draft_revision: u64,
    draft_dirty: bool,
    acknowledge_uncertain: bool,
    zoom: f32,
    select_roi: bool,
    roi_start: Option<egui::Pos2>,
    folder_picker: Option<mpsc::Receiver<Option<PathBuf>>>,
    folder_draft: String,
    folder_dirty: bool,
    selected_stack: usize,
    painted_ready: bool,
    phone_open: bool,
    phone_texture: Option<(String, egui::TextureHandle)>,
    peaking: bool,
    peak_threshold: u8,
    peak_texture: Option<(u64, u8, egui::TextureHandle)>,
    focus_target: u16,
    focus_anchor: Option<u16>,
    focus_range: u8,
    focus_pending: Option<u16>,
    focus_flight: Option<(u16, u64, Instant)>,
    schedule_ui: schedule_ui::ScheduleUi,
    warmup_edit: Option<u32>,
    /// Stacking during capture: check and align planes as they arrive.
    pub follow_enabled: bool,
    /// Open a finished, checked capture in Projects and stack it.
    pub stack_when_done: bool,
    follower: Option<follow::Follower>,
    /// The run whose checker could not start; not retried until asked.
    follow_refused: Option<(PathBuf, String)>,
    finished_capture: Option<PathBuf>,
    /// What became of the last finished capture, from the workspace.
    pub follow_note: Option<String>,
    /// The engine the desktop runs (from `poll_follow`).
    engine: Option<PathBuf>,
    /// Calibrate step: a short survey measured for the focus step.
    calibration: tools::Calibration,
    /// A completed capture's focus step, its compact estimate and compaction.
    step_report: tools::Slot,
    compact_estimate: tools::Slot,
    compact_apply: tools::Slot,
    compact_confirm: bool,
    /// A test shot at the current focus (Studio 2, 7.4).
    test_shot: test_shot::TestShot,
    /// Waiting for the camera to connect, and what became of the last wait.
    connect_wait: Option<tools::ConnectWait>,
    connect_note: Option<String>,
    /// The camera action waiting for its confirming click.
    pub confirm: Option<Confirm>,
    /// Whether the shell shows the Capture station; `None` until the shell
    /// says, when [`Self::show`] having run since the last poll stands in.
    station_open: Option<bool>,
    shown: bool,
    /// A host sequence never followed: a calibration survey or a test shot
    /// the desktop stopped waiting for, still being written.
    unfollowed_sequence: Option<u64>,
    /// The last success notice read (`Snapshot::notice_id`).
    notice_read: u64,
    selected_stopped: usize,
    /// The Studio 2 station's views (`capture-station.rs`).
    station: station::Station,
}
impl CaptureWorkspace {
    pub fn new(path: Option<PathBuf>) -> Self {
        let path = path.unwrap_or_else(crate::capture_client::default_path);
        let loaded = Config::load(&path);
        let error = loaded.as_ref().err().map(|e| format!("{e:#}"));
        Self {
            config: loaded.unwrap_or_default(),
            path,
            connection: None,
            error,
            texture: None,
            draft: Plan::default(),
            confirmed_plan: Plan::default(),
            draft_revision: 0,
            draft_dirty: false,
            acknowledge_uncertain: false,
            zoom: 1.0,
            select_roi: false,
            roi_start: None,
            folder_picker: None,
            folder_draft: String::new(),
            folder_dirty: false,
            selected_stack: 0,
            painted_ready: false,
            phone_open: false,
            phone_texture: None,
            peaking: true,
            peak_threshold: 18,
            peak_texture: None,
            focus_target: 0,
            focus_anchor: None,
            focus_range: 0,
            focus_pending: None,
            focus_flight: None,
            schedule_ui: Default::default(),
            warmup_edit: None,
            follow_enabled: true,
            stack_when_done: true,
            follower: None,
            follow_refused: None,
            finished_capture: None,
            follow_note: None,
            engine: None,
            calibration: tools::Calibration::Idle,
            step_report: Default::default(),
            compact_estimate: Default::default(),
            compact_apply: Default::default(),
            compact_confirm: false,
            test_shot: test_shot::TestShot::Idle,
            connect_wait: None,
            connect_note: None,
            confirm: None,
            station_open: None,
            shown: false,
            unfollowed_sequence: None,
            notice_read: 0,
            selected_stopped: 0,
            station: station::Station::default(),
        }
    }
    fn calibrating(&self) -> bool {
        self.calibration.running()
    }
    /// The light warmup a capture waits through when the host manages power.
    fn warmup(s: &Snapshot) -> Duration {
        Duration::from_secs(
            s.host
                .power
                .as_ref()
                .filter(|p| p.manage_stack)
                .and_then(|p| p.warmup_seconds)
                .unwrap_or(0),
        )
    }
    /// The survey's capture time limit: [`tools::SURVEY_TIMEOUT`] plus the
    /// light warmup.
    fn survey_deadline(s: &Snapshot, now: Instant) -> Instant {
        now + tools::SURVEY_TIMEOUT + Self::warmup(s)
    }
    /// Advances the step calibration, the test shot, the connect wait and the
    /// background engine jobs; gives up any wait past its time limit.
    fn poll_tools(&mut self) {
        self.step_report.poll();
        self.compact_estimate.poll();
        self.compact_apply.poll();
        let Some(connection) = &self.connection else {
            return;
        };
        let s = connection.snapshot();
        let now = Instant::now();
        if let Some(run) = self.test_shot.poll(&s, now) {
            connection.mark_test_run(run);
        }
        // A survey or test shot the desktop stopped waiting for is kept out
        // of the lists once its folder is known (it is not deleted).
        if self.unfollowed_sequence.is_some() && self.unfollowed_sequence == s.host.sequence_id {
            let run = if s.host.phase.capturing() {
                s.in_progress.as_ref().map(|r| r.folder.clone())
            } else {
                s.host.last_receipt_run()
            };
            if let Some(run) = run {
                connection.mark_test_run(run);
            }
        }
        if let Some(wait) = &mut self.connect_wait
            && let Some(outcome) = wait.poll(&s, now)
        {
            self.connect_note = match outcome {
                tools::ConnectOutcome::Connected => None,
                tools::ConnectOutcome::Failed(why) => Some(why),
                tools::ConnectOutcome::TimedOut => Some(format!(
                    "The camera did not connect within {} s. Check its switch, the USB cable and USB Remote Shoot mode, then connect again.",
                    tools::CONNECT_TIMEOUT.as_secs()
                )),
            };
            self.connect_wait = None;
        }
        self.poll_station(&s);
        use tools::Calibration as C;
        let stage_before = self.calibration.stage();
        let state = std::mem::replace(&mut self.calibration, C::Idle);
        let host = &s.host;
        let idle = !host.busy && host.editable;
        let shots = host.shots_per_plane;
        // The camera went away while the calibration waited for it (switched
        // off, or an older controller's "manage power" after the survey):
        // waiting for it would never end.
        let gone = !host.connected && !host.busy;
        self.calibration = match state {
            C::Switching { .. } if gone => C::Failed(
                "The camera switched off during the calibration: turn it on and calibrate again"
                    .into(),
            ),
            C::Restoring { mut result, .. } if gone => {
                let summary = result["summary"].as_str().unwrap_or("").to_owned();
                result["summary"] = json!(format!(
                    "{summary} The camera switched off before four-shot could be set again: set it when the camera is back."
                ));
                C::Done(result)
            }
            C::Switching {
                restore_four,
                positions,
                round,
                ..
            } if idle && shots == Some(1) => {
                let sequence = host.sequence_id.unwrap_or(0) + 1;
                let spacing = positions
                    .windows(2)
                    .map(|w| w[0].abs_diff(w[1]))
                    .next()
                    .unwrap_or(1);
                match s
                    .request(Command::CapturePositions {
                        positions,
                        // "Manage power" would switch the camera off after the
                        // survey, before a second survey or four-shot is set again.
                        keep_power_on: true,
                        kind: PositionsKind::Positions,
                    })
                    .and_then(|r| self.submit(r))
                {
                    Ok(()) => C::Capturing {
                        restore_four,
                        sequence,
                        round,
                        spacing,
                        deadline: Self::survey_deadline(&s, now),
                    },
                    Err(e) => C::Failed(format!("{e:#}")),
                }
            }
            C::Capturing {
                restore_four,
                sequence,
                round,
                spacing,
                deadline,
            } if host.sequence_id == Some(sequence) && !host.busy => match host.phase {
                HostPhase::Complete => {
                    let run = host.last_receipt_run();
                    match (run, &self.engine) {
                        (Some(run), Some(engine)) => {
                            match tools::EngineJob::start(
                                engine,
                                vec!["focus-step".into(), run.clone().into_os_string()],
                            ) {
                                Ok(job) => C::Measuring {
                                    restore_four,
                                    run,
                                    job,
                                    round,
                                    spacing,
                                    deadline: now + tools::MEASURE_TIMEOUT,
                                    ended: None,
                                },
                                Err(e) => C::Failed(format!("{e:#}")),
                            }
                        }
                        (None, _) => C::Failed("The survey's folder was not reported".into()),
                        (_, None) => C::Failed("The Strehl engine was not found".into()),
                    }
                }
                HostPhase::Stopped | HostPhase::Fault | HostPhase::Disconnected => {
                    C::Failed("The survey did not finish".into())
                }
                _ => C::Capturing {
                    restore_four,
                    sequence,
                    round,
                    spacing,
                    deadline,
                },
            },
            C::Measuring {
                restore_four,
                run,
                mut job,
                round,
                spacing,
                deadline,
                ended,
            } => match job.poll() {
                None => C::Measuring {
                    restore_four,
                    run,
                    job,
                    round,
                    spacing,
                    deadline,
                    ended,
                },
                Some(result) => {
                    // The survey's RAWs served their purpose (or the
                    // measurement was ended): free the disk. The engine has
                    // been reaped by now.
                    if run.join("manifest.json").is_file() && run.join("events.jsonl").is_file() {
                        let _ = std::fs::remove_dir_all(&run);
                    }
                    match (ended, result) {
                        (Some(why), _) => C::Failed(why),
                        (None, Err(e)) => C::Failed(format!("{e:#}")),
                        (None, Ok(v)) => {
                            let width = v["width"].as_f64();
                            let again = match width {
                                None => Some(spacing.saturating_mul(4)),
                                Some(w) if w < 3.0 * f64::from(spacing) && spacing > 2 => {
                                    Some((spacing / 4).max(1))
                                }
                                _ => None,
                            };
                            let (start, end) = host.plan_bounds();
                            match again.filter(|_| round == 0) {
                                Some(spacing) => C::Switching {
                                    restore_four,
                                    positions: tools::survey_positions(
                                        start,
                                        end,
                                        spacing,
                                        tools::SURVEY_PLANES,
                                    ),
                                    round: 1,
                                    deadline: now + tools::SWITCH_TIMEOUT,
                                },
                                None if restore_four => {
                                    let r = s
                                        .request(Command::PixelShift { shots: 4 })
                                        .and_then(|r| self.submit(r));
                                    match r {
                                        Ok(()) => C::Restoring {
                                            result: v,
                                            deadline: now + tools::SWITCH_TIMEOUT,
                                        },
                                        Err(e) => C::Failed(format!("{e:#}")),
                                    }
                                }
                                None => C::Done(v),
                            }
                        }
                    }
                }
            },
            C::Restoring { result, .. } if idle && shots == Some(4) => C::Done(result),
            other => other,
        };
        station::note_calibration(&mut self.station, stage_before, &self.calibration);
        // A survey left running when the calibration gave up is not followed.
        let survey = self.calibration.survey_sequence();
        self.calibration.expire(now);
        if survey.is_some()
            && self.calibration.survey_sequence().is_none()
            && matches!(self.calibration, C::Failed(_))
        {
            self.unfollowed_sequence = survey;
        }
    }
    /// Starts a step calibration: single RAWs across the middle of the marked
    /// range, measured on this PC, then the camera's pixel shift as it was.
    fn start_calibration(&mut self, s: &Snapshot) {
        let restore_four = s.host.shots_per_plane == Some(4);
        let (start, end) = s.host.plan_bounds();
        let positions =
            tools::survey_positions(start, end, tools::SURVEY_SPACING, tools::SURVEY_PLANES);
        if restore_four {
            self.command(s, Command::PixelShift { shots: 1 });
        }
        self.calibration = tools::Calibration::Switching {
            restore_four,
            positions,
            round: 0,
            deadline: Instant::now() + tools::SWITCH_TIMEOUT,
        };
    }
    /// Stops waiting for the calibration at whatever stage it is in (see
    /// [`tools::Calibration::stop`]). A survey being captured is left to
    /// finish on the host and is not followed.
    pub fn stop_calibration(&mut self) {
        if let Some(sequence) = self.calibration.survey_sequence() {
            self.unfollowed_sequence = Some(sequence);
        }
        self.calibration.stop("Calibration stopped");
    }
    /// `calibrate_step` from the control interface.
    pub fn calibrate(&mut self) -> anyhow::Result<()> {
        let s = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .snapshot();
        anyhow::ensure!(!self.calibrating(), "A calibration is running");
        anyhow::ensure!(self.engine.is_some(), "The Strehl engine was not found");
        anyhow::ensure!(!self.test_shot.running(), "A test shot is running");
        anyhow::ensure!(
            s.fresh() && s.host.editable && !s.pending,
            "The camera is not ready"
        );
        anyhow::ensure!(s.host.bounds_set(), "Mark the start and end first");
        self.start_calibration(&s);
        match self.error.take() {
            Some(e) => {
                self.calibration = tools::Calibration::Failed(e.clone());
                anyhow::bail!(e)
            }
            None => Ok(()),
        }
    }
    fn completed_folder(&self, index: usize) -> anyhow::Result<PathBuf> {
        let s = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .snapshot();
        Ok(s.completed
            .get(index)
            .ok_or_else(|| anyhow::anyhow!("Completed capture unavailable"))?
            .folder
            .clone())
    }
    /// `measure_focus_step` from the control interface.
    pub fn measure_focus_step(&mut self, index: usize) -> anyhow::Result<()> {
        let folder = self.completed_folder(index)?;
        anyhow::ensure!(!self.step_report.running(), "A measurement is running");
        let engine = self.engine.clone();
        self.step_report.start(
            engine.as_deref(),
            &folder,
            vec!["focus-step".into(), folder.clone().into_os_string()],
        );
        Ok(())
    }
    /// `compact_capture` from the control interface: an estimate, or (after
    /// an estimate of the same capture) the compaction itself.
    pub fn compact(&mut self, index: usize, apply: bool) -> anyhow::Result<()> {
        let folder = self.completed_folder(index)?;
        anyhow::ensure!(
            !self.compact_estimate.running() && !self.compact_apply.running(),
            "A compaction is running"
        );
        let engine = self.engine.clone();
        let mut args = vec!["compact".into(), folder.clone().into_os_string()];
        if apply {
            anyhow::ensure!(
                matches!(self.compact_estimate.for_folder(&folder), Some(Ok(_))),
                "Estimate this capture's compaction first"
            );
            args.push("--apply".into());
            self.compact_apply.start(engine.as_deref(), &folder, args);
        } else {
            self.compact_estimate
                .start(engine.as_deref(), &folder, args);
        }
        Ok(())
    }
    /// Calibration, focus-step, compaction and test-shot state for snapshots.
    fn tools_public(&self) -> Value {
        use tools::Calibration as C;
        let now = Instant::now();
        let result = match &self.calibration {
            C::Restoring { result, .. } | C::Done(result) => result.clone(),
            C::Failed(e) => json!({"error":e}),
            _ => Value::Null,
        };
        json!({"calibration":{"stage":self.calibration.stage(),"result":result,
                "gives_up_seconds":self.calibration.gives_up_in(now).map(|d| d.as_secs_f64())},
            "focus_step":self.step_report.public(),
            "compact_estimate":self.compact_estimate.public(),
            "compact":self.compact_apply.public(),
            "test_shot":self.test_shot.public(now),
            "connect_wait":self.connect_wait.as_ref().map(|w| json!({"gives_up_seconds":w.gives_up_in(now).as_secs_f64()})),
            "connect_note":self.connect_note})
    }
    fn calibration_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot, editable: bool) {
        use tools::Calibration as C;
        let bounds = s.host.bounds_set();
        let busy = self.calibrating() || self.test_shot.running();
        ui.horizontal(|ui| {
            if ui
                .add_enabled(
                    editable && bounds && !busy && self.engine.is_some() && !self.draft_dirty,
                    egui::Button::new("Calibrate step"),
                )
                .on_hover_text("Takes 25 single RAWs around the middle of the marked range (about a minute), measures how far detail stays sharp, suggests the step, and deletes the survey. Needs the light on and the bounds marked.")
                .clicked()
            {
                self.start_calibration(s);
            }
            let label = match &self.calibration {
                C::Switching { .. } | C::Restoring { .. } => Some("Setting the camera…"),
                C::Capturing { .. } => Some("Surveying…"),
                C::Measuring { ended: Some(_), .. } => Some("Stopping…"),
                C::Measuring { .. } => Some("Measuring…"),
                _ => None,
            };
            if let Some(label) = label {
                ui.spinner();
                ui.small(label);
                if let Some(left) = self.calibration.gives_up_in(Instant::now()) {
                    ui.small(format!("gives up in {} s", left.as_secs()));
                    ui.ctx().request_repaint_after(Duration::from_secs(1));
                }
                if ui
                    .small_button("Stop waiting")
                    .on_hover_text("Ends the calibration here; the camera is left as it is. A survey being captured finishes on the camera and is not checked.")
                    .clicked()
                {
                    self.stop_calibration();
                }
            }
        });
        match &self.calibration {
            C::Done(v) => {
                ui.small(v["summary"].as_str().unwrap_or(""));
                if let Some(step) = v["suggested_step"].as_u64().map(|n| n as u16) {
                    let range = self.confirmed_plan.start.abs_diff(self.confirmed_plan.end);
                    let planes = u64::from(range / step.max(1)) + 1;
                    let shots = if s.host.shots_per_plane == Some(4) {
                        4
                    } else {
                        1
                    };
                    let estimate = s
                        .host
                        .exposure
                        .as_ref()
                        .and_then(|e| e.shutter)
                        .and_then(|shutter| {
                            strehl_capture::timing::initial_plane(
                                shutter,
                                self.confirmed_plan.settle_ms,
                                shots,
                            )
                        })
                        .map(|plane| plane * planes as u32);
                    ui.small(format!(
                        "At step {step}: {planes} planes{}",
                        estimate.map_or(String::new(), |d| format!(
                            ", about {}",
                            strehl_capture::timing::format_duration(d)
                        ))
                    ));
                    if step != self.confirmed_plan.step
                        && ui
                            .add_enabled(editable, egui::Button::new(format!("Use step {step}")))
                            .clicked()
                    {
                        let command = Command::Settings {
                            step,
                            settle_ms: self.confirmed_plan.settle_ms,
                            approach: self.confirmed_plan.approach,
                            capture_timeout_s: self.confirmed_plan.capture_timeout_s,
                        };
                        let result = s.request(command).and_then(|mut r| {
                            r.plan_revision = self.draft_revision;
                            self.submit(r)
                        });
                        self.record(result);
                    }
                }
            }
            C::Failed(e) => {
                ui.colored_label(AMBER, format!("Calibration stopped: {e}"));
            }
            _ => {}
        }
    }
    /// Starts, watches and ends the engine's checker for the capture being
    /// written (see `capture-follow.rs`). Called every frame, whichever tab
    /// is open, once Capture has connected.
    pub fn poll_follow(&mut self, engine: Option<&std::path::Path>) {
        self.engine = engine.map(std::path::Path::to_path_buf);
        self.poll_tools();
        let Some(connection) = &self.connection else {
            return;
        };
        let s = connection.snapshot();
        // Live while the station is shown or a sequence runs; 1 Hz otherwise.
        let open = self.station_open.unwrap_or(self.shown);
        self.shown = false;
        connection.set_cadence(Cadence::choose(open, s.host.phase.active()));
        let capturing = s.host.phase.capturing();
        // A run the desktop knows is not a stack: a test shot (by its
        // manifest, or one this desktop took), a survey, or a sequence it
        // stopped waiting for.
        let not_a_stack = s.in_progress.as_ref().is_some_and(|r| r.test)
            || self.test_shot.running()
            || self.calibrating()
            || (self.unfollowed_sequence.is_some()
                && self.unfollowed_sequence == s.host.sequence_id
                && capturing);
        let current = s.in_progress.as_ref().filter(|_| !not_a_stack);
        if let Some(f) = &mut self.follower {
            f.poll();
            if f.running() {
                let followed = current.filter(|r| r.folder == f.run);
                if !self.follow_enabled {
                    f.stop("Turned off; the planes checked so far are kept");
                } else if current.is_some()
                    && followed.is_none()
                    && !f.run.join("result.json").exists()
                {
                    f.stop("A newer capture started");
                } else if followed.is_some_and(|r| r.idle > follow::ABANDONED) && !capturing {
                    f.stop("No new RAWs for 10 minutes; the planes checked so far are kept");
                }
            }
            if f.state == follow::State::Finished && !f.offered {
                f.offered = true;
                if self.stack_when_done && crate::capture_client::verify_completed(&f.run).is_ok() {
                    self.finished_capture = Some(f.run.clone());
                }
            }
        }
        let Some(run) = current else { return };
        let fresh = self
            .follower
            .as_ref()
            .is_none_or(|f| !f.running() && (f.run != run.folder || f.observing));
        let refused = self
            .follow_refused
            .as_ref()
            .is_some_and(|(r, _)| *r == run.folder);
        // A calibration survey is measured and deleted, never followed; nor
        // is a test shot (`not_a_stack` above).
        if self.follow_enabled
            && fresh
            && !refused
            && (capturing || run.idle < follow::ABANDONED)
            && let Some(engine) = engine
        {
            match follow::Follower::start(engine, &run.folder, Some(self.config.clone())) {
                Ok(f) => {
                    self.follower = Some(f);
                    self.follow_note = None;
                }
                Err(e) => self.follow_refused = Some((run.folder.clone(), format!("{e:#}"))),
            }
        }
    }
    /// A capture that finished, was checked while it ran, and is to be
    /// opened in Projects and stacked.
    pub fn take_finished_capture(&mut self) -> Option<PathBuf> {
        self.finished_capture.take()
    }
    fn follow_public(&self) -> Value {
        json!({"enabled":self.follow_enabled,"stack_when_done":self.stack_when_done,
            "checker":self.follower.as_ref().map(follow::Follower::public),
            "refused":self.follow_refused.as_ref().map(|(run, e)| json!({"run":run,"error":e})),
            "note":self.follow_note})
    }
    pub fn activate(&mut self, ctx: &egui::Context) {
        if self.connection.is_none() {
            match Connection::start(self.config.clone(), self.path.clone(), ctx.clone()) {
                Ok(connection) => self.connection = Some(connection),
                Err(e) => self.error = Some(format!("{e:#}")),
            }
        }
    }

    pub fn snapshot(&self) -> Value {
        let mut value = self
            .connection
            .as_ref()
            .map_or(json!({"online":false,"initialized":false}), |c| {
                c.snapshot().public()
            });
        value["follow"] = self.follow_public();
        value["tools"] = self.tools_public();
        value
    }
    /// Turns stacking during capture on or off. Turning it on, or retrying,
    /// lets a stopped or failed checker start again.
    pub fn set_follow(&mut self, enabled: bool) {
        self.follow_enabled = enabled;
        if enabled {
            self.follow_refused = None;
            if self.follower.as_ref().is_some_and(|f| !f.running()) {
                self.follower = None;
            }
        }
    }
    pub fn ready_for_screenshot(&self) -> bool {
        // The background thread may publish new status halfway through paint.
        // A screenshot must wait for the state that was actually drawn.
        self.painted_ready
    }
    pub fn submit(&mut self, request: CommandRequest) -> anyhow::Result<()> {
        self.connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .command(request)
    }
    pub fn import_completed(&mut self, index: usize) -> anyhow::Result<()> {
        let c = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?;
        let s = c.snapshot();
        let stack = s
            .completed
            .get(index)
            .ok_or_else(|| anyhow::anyhow!("Completed stack unavailable"))?;
        c.handoff(stack.folder.clone())
    }
    pub fn take_handoff(&self) -> Option<PathBuf> {
        self.connection.as_ref()?.take_handoff()
    }
    pub fn start_receiver(&self) -> anyhow::Result<()> {
        self.connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .start_receiver()
    }
    pub fn set_compression(&self, compressed: bool) -> anyhow::Result<()> {
        let c = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?;
        let s = c.snapshot();
        let folder = s.receiver["folder"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Receiver unavailable"))?;
        c.storage(folder.into(), compressed)
    }
    fn command(&mut self, s: &Snapshot, command: Command) {
        let result = s.request(command).and_then(|r| self.submit(r));
        self.record(result);
    }
    fn record(&mut self, result: anyhow::Result<()>) {
        self.error = result.err().map(|e| format!("{e:#}"));
    }
    pub fn show(&mut self, ctx: &egui::Context, can_import: bool) {
        if let Some(mode) = std::env::var_os("STREHL_CAPTURE_STATION")
            && (mode == "1" || mode == "glance")
        {
            if mode == "glance" && !self.station_glance_seen() {
                self.open_glance_once();
            }
            self.show_station(ctx);
            return;
        }
        self.activate(ctx);
        self.shown = true;
        let s = self
            .connection
            .as_ref()
            .map(Connection::snapshot)
            .unwrap_or_default();
        self.observe_focus(&s);
        self.painted_ready = (!s.receiver.is_null() || s.receiver_error.is_some())
            && ((s.observed.is_some() && (s.preview.is_some() || !s.host.preview.available))
                || s.connection_error.is_some()
                || self.config.controller.is_empty());
        if let Some(plan) = s.host.plan.clone() {
            self.sync_plan(plan, s.host.plan_revision.unwrap_or(0));
        }
        if !self.folder_dirty {
            self.folder_draft = s.receiver["folder"].as_str().unwrap_or_default().into();
        }
        if let Some(result) = self
            .folder_picker
            .as_ref()
            .and_then(|rx| rx.try_recv().ok())
        {
            self.folder_picker = None;
            if let Some(path) = result {
                self.folder_draft = path.display().to_string();
                self.folder_dirty = true;
            }
        }
        if let Some((generation, image)) = &s.preview
            && self.texture.as_ref().is_none_or(|(g, _)| g != generation)
        {
            let image = image.as_ref().clone();
            match &mut self.texture {
                Some((g, texture)) => {
                    texture.set(image, egui::TextureOptions::LINEAR);
                    *g = *generation;
                }
                None => {
                    self.texture = Some((
                        *generation,
                        ctx.load_texture(
                            "capture-live-preview",
                            image,
                            egui::TextureOptions::LINEAR,
                        ),
                    ))
                }
            }
        }
        if self.peaking
            && let Some((generation, peaks)) = &s.peaking
            && self
                .peak_texture
                .as_ref()
                .is_none_or(|(g, t, _)| g != generation || *t != self.peak_threshold)
        {
            let image = peaks.overlay(self.peak_threshold);
            match &mut self.peak_texture {
                Some((g, t, texture)) => {
                    texture.set(image, egui::TextureOptions::NEAREST);
                    *g = *generation;
                    *t = self.peak_threshold;
                }
                None => {
                    self.peak_texture = Some((
                        *generation,
                        self.peak_threshold,
                        ctx.load_texture("capture-peaking", image, egui::TextureOptions::NEAREST),
                    ))
                }
            }
        }
        egui::SidePanel::left("capture-controls")
            .default_width(310.0)
            .width_range(290.0..=430.0)
            .frame(egui::Frame::new().fill(PANEL).inner_margin(16))
            .show(ctx, |ui| {
                egui::ScrollArea::vertical()
                    .id_salt("capture-controls-scroll")
                    .show(ui, |ui| {
                        ui.label(RichText::new("CAPTURE").color(ACCENT).size(12.0).strong());
                        ui.add_space(12.0);
                        self.connection_ui(ui, &s);
                        self.power_ui(ui, &s);
                        ui.add_space(12.0);
                        ui.separator();
                        ui.add_space(10.0);
                        self.focus_ui(ui, &s);
                        ui.add_space(12.0);
                        ui.separator();
                        ui.add_space(10.0);
                        self.storage_ui(ui, &s);
                        ui.add_space(12.0);
                        ui.separator();
                        ui.add_space(10.0);
                        self.follow_ui(ui, &s);
                        ui.add_space(12.0);
                        ui.separator();
                        ui.add_space(10.0);
                        self.completed_ui(ui, &s, can_import);
                    });
            });
        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(BG).inner_margin(20))
            .show(ctx, |ui| {
                self.sequence_ui(ui, &s);
                ui.add_space(12.0);
                ui.horizontal_wrapped(|ui| {
                    ui.label(RichText::new("LIVE VIEW").color(MUTED).size(11.0));
                    if ui.selectable_label(self.zoom == 1.0, "Fit").clicked() {
                        self.zoom = 1.0;
                    }
                    ui.add(
                        egui::Slider::new(&mut self.zoom, 1.0..=4.0)
                            .suffix("×")
                            .show_value(true),
                    );
                    ui.toggle_value(&mut self.peaking, "Focus peaking").on_hover_text("Cyan highlights fine contrast in the live JPEG. A viewing aid, not a RAW sharpness measurement.");
                    if self.peaking {
                        ui.add(egui::Slider::new(&mut self.peak_threshold, 6..=40).text("Threshold"));
                    }
                    if let Some((_, levels)) = &s.levels {
                        ui.small(format!(
                            "{:.1} % clipped · {}",
                            100.0 * levels.clipped_share,
                            crate::capture_aids::PreviewLevels::CAUTION
                        ));
                    }
                    ui.add_enabled_ui(s.fresh() && s.host.editable && !s.pending, |ui| {
                        ui.toggle_value(&mut self.select_roi, "Select subject");
                    });
                });
                self.preview_ui(ui, &s);
            });
        self.phone_ui(ctx);
        self.flush_focus(&s);
    }
    fn phone_ui(&mut self, ctx: &egui::Context) {
        if !self.phone_open {
            return;
        }
        let mut config = self.config.clone();
        if let Err(e) = config.normalize() {
            self.error = Some(e.to_string());
            self.phone_open = false;
            return;
        }
        let link = format!("{}/#key={}", config.controller, config.pairing_key);
        if self
            .phone_texture
            .as_ref()
            .is_none_or(|(old, _)| old != &link)
        {
            match crate::capture_aids::phone_qr(&link) {
                Ok(qr) => {
                    self.phone_texture = Some((
                        link.clone(),
                        ctx.load_texture(
                            "private-phone-pairing",
                            qr,
                            egui::TextureOptions::NEAREST,
                        ),
                    ))
                }
                Err(e) => {
                    self.error = Some(e.to_string());
                    self.phone_open = false;
                    return;
                }
            }
        }
        egui::Window::new("Phone remote control")
            .open(&mut self.phone_open)
            .collapsible(false)
            .resizable(false)
            .show(ctx, |ui| {
                ui.label("Scan with your phone camera on the same Wi-Fi.");
                if let Some((_, texture)) = &self.phone_texture {
                    ui.image((texture.id(), texture.size_vec2() * 5.0));
                }
                ui.label(&config.controller);
                if ui.button("Copy pairing link").clicked() {
                    ui.ctx().copy_text(link);
                }
                ui.small("This QR includes your private pairing key.");
                ui.small("Android Chrome may need Nearby devices permission.");
            });
    }
    fn sync_plan(&mut self, plan: Plan, revision: u64) {
        // Only the sequence settings are editable drafts. The Pi owns both marks.
        self.draft.start = plan.start;
        self.draft.end = plan.end;
        self.confirmed_plan.start = plan.start;
        self.confirmed_plan.end = plan.end;
        if !self.draft_dirty {
            self.draft = plan.clone();
            self.confirmed_plan = plan;
            self.draft_revision = revision;
        } else if self.confirmed_plan == plan {
            self.draft_revision = revision;
        }
    }
    fn observe_focus(&mut self, s: &Snapshot) {
        let host = &s.host;
        if !s.fresh()
            || !matches!(
                host.phase,
                HostPhase::Ready | HostPhase::Complete | HostPhase::Stopped | HostPhase::Moving
            )
        {
            self.focus_pending = None;
            self.focus_flight = None;
        }
        if let Some((target, revision, sent)) = self.focus_flight {
            if s.command_error.is_some() || sent.elapsed() > Duration::from_secs(15) {
                self.focus_pending = None;
                self.focus_flight = None;
                self.error = Some(
                    "Focus move was not confirmed. Check the camera before scrubbing again.".into(),
                );
            } else if host.camera_revision.is_some_and(|r| r > revision)
                && host.editable
                && !s.pending
            {
                self.focus_flight = None;
                if host.position != Some(target) {
                    self.focus_pending = None;
                    self.error = Some(
                        "Focus did not reach the slider target; move was not repeated.".into(),
                    );
                }
            }
        }
        if self.focus_pending.is_none()
            && self.focus_flight.is_none()
            && let Some(p) = host.position
        {
            self.focus_target = p;
            if self.focus_anchor.is_none_or(|a| a.abs_diff(p) > 128) {
                self.focus_anchor = Some(p);
            }
        }
    }
    fn flush_focus(&mut self, s: &Snapshot) {
        if self.focus_flight.is_some() || s.pending || !s.fresh() || !s.host.editable {
            return;
        }
        if let Some(target) = self.focus_pending.take() {
            if s.host.position == Some(target) {
                return;
            }
            let revision = s.host.camera_revision.unwrap_or(0);
            let result = s
                .request(Command::Focus { target })
                .and_then(|r| self.submit(r));
            if result.is_ok() {
                self.focus_flight = Some((target, revision, Instant::now()));
            }
            self.record(result);
        }
    }
    fn scrub_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        let host = &s.host;
        let enabled = s.fresh()
            && host.connected
            && (host.editable
                || (matches!(host.phase, HostPhase::Ready | HostPhase::Moving)
                    && self.focus_flight.is_some()));
        ui.add_enabled_ui(enabled, |ui| {
            ui.horizontal(|ui| {
                for (value, text) in [(0, "Fine"), (1, "Marked range"), (2, "Full lens")] {
                    if ui
                        .selectable_value(&mut self.focus_range, value, text)
                        .clicked()
                    {
                        self.focus_anchor = s.host.position;
                    }
                }
            });
            let anchor = self.focus_anchor.unwrap_or(self.focus_target);
            let (lo, hi) = match self.focus_range {
                0 => (anchor.saturating_sub(128), anchor.saturating_add(128)),
                1 if s.host.bounds_set() => (
                    self.draft.start.min(self.draft.end).saturating_sub(16),
                    self.draft.start.max(self.draft.end).saturating_add(16),
                ),
                _ => (0, u16::MAX),
            };
            ui.scope(|ui| {
                ui.spacing_mut().slider_width = (ui.available_width() - 60.0).max(80.0);
                let r = ui.add(
                    egui::Slider::new(&mut self.focus_target, lo..=hi)
                        .step_by(1.0)
                        .clamping(egui::SliderClamping::Edits),
                );
                if r.changed() {
                    self.focus_pending = Some(self.focus_target);
                }
            });
            ui.small(format!("{lo} – {hi} · drag to focus"));
        });
    }
    fn connection_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        let connected = s.host.connected;
        ui.horizontal(|ui| {
            ui.colored_label(
                if s.fresh() { GREEN } else { AMBER },
                if s.fresh() {
                    "●  Pi online"
                } else {
                    "○  Pi offline"
                },
            );
            if s.host.demo {
                ui.label(RichText::new("SIMULATOR").color(AMBER));
            }
        });
        ui.label(
            RichText::new(s.host.camera_model.as_deref().unwrap_or(if connected {
                "Camera connected"
            } else {
                "Camera not connected"
            }))
            .strong()
            .size(18.0),
        );
        let can_disconnect = s.fresh() && connected && s.host.editable && !s.pending;
        if !can_disconnect && self.confirm == Some(Confirm::Disconnect) {
            self.confirm = None;
        }
        ui.horizontal(|ui| {
            if ui
                .add_enabled(
                    s.fresh() && !connected && !s.pending && self.connect_wait.is_none(),
                    egui::Button::new("Connect camera"),
                )
                .clicked()
            {
                self.connect_camera(s, Command::Connect {});
            }
            if self.confirm == Some(Confirm::Disconnect) {
                if ui
                    .add_enabled(can_disconnect, egui::Button::new("Disconnect now"))
                    .clicked()
                {
                    self.confirm = None;
                    self.command(s, Command::Disconnect {});
                }
                if ui.button("Keep connected").clicked() {
                    self.confirm = None;
                }
            } else if ui
                .add_enabled(can_disconnect, egui::Button::new("Disconnect…"))
                .on_hover_text("Asks before releasing the camera")
                .clicked()
            {
                self.confirm = Some(Confirm::Disconnect);
            }
        });
        if self.confirm == Some(Confirm::Disconnect) {
            ui.small("Release the camera? Marks and the subject region are cleared.");
        }
        self.connect_wait_ui(ui);
        if ui
            .add_enabled(
                !self.config.controller.is_empty(),
                egui::Button::new("Phone control · QR code"),
            )
            .clicked()
        {
            self.phone_open = true;
        }
        egui::CollapsingHeader::new("Connection settings").default_open(self.config.controller.is_empty()).show(ui,|ui| {
            ui.label("Pi address or pairing link");
            ui.add(egui::TextEdit::singleline(&mut self.config.controller).desired_width(f32::INFINITY).hint_text("http://10.0.0.178:8787"));
            ui.label("Pairing key");
            ui.add(egui::TextEdit::singleline(&mut self.config.pairing_key).password(true).desired_width(f32::INFINITY));
            ui.label("Local subnet");ui.text_edit_singleline(&mut self.config.lan);
            ui.label("Receiver configuration on this PC");
            let mut receiver_path=self.config.receiver_config.display().to_string();
            if ui.add(egui::TextEdit::singleline(&mut receiver_path).desired_width(f32::INFINITY)).changed(){self.config.receiver_config=receiver_path.into();}
            if ui.add_enabled(!s.pending,egui::Button::new("Save connection")).clicked() {
                let result=self.config.normalize().and_then(|()|self.connection.as_ref().unwrap().configure(self.config.clone()));
                self.record(result); self.texture=None;
            }
            ui.small("LAN only. Use the same pairing key as your phone. Closing Strehl leaves the Pi's sequence running.");
        });
        if let Some(error) = &s.connection_error {
            ui.colored_label(AMBER, error);
        }
    }
    /// Sends a connect (or power-on and connect) and waits for the camera,
    /// with a time limit and Stop waiting.
    fn connect_camera(&mut self, s: &Snapshot, command: Command) {
        let result = s.request(command).and_then(|r| self.submit(r));
        if result.is_ok() {
            self.connect_wait = Some(tools::ConnectWait::new(Instant::now()));
            self.connect_note = None;
        }
        self.record(result);
    }
    fn connect_wait_ui(&mut self, ui: &mut egui::Ui) {
        if let Some(wait) = &self.connect_wait {
            let left = wait.gives_up_in(Instant::now());
            let mut stop = false;
            ui.horizontal_wrapped(|ui| {
                ui.spinner();
                ui.small(format!(
                    "Waiting for the camera · gives up in {} s",
                    left.as_secs()
                ));
                stop = ui
                    .small_button("Stop waiting")
                    .on_hover_text("Stops waiting here; nothing is sent to the camera")
                    .clicked();
            });
            ui.ctx().request_repaint_after(Duration::from_secs(1));
            if stop {
                self.stop_waiting_for_camera();
            }
        } else if let Some(note) = &self.connect_note {
            ui.colored_label(AMBER, note);
        }
    }
    fn power_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        let Some(power) = &s.host.power else {
            return;
        };
        let idle = s.fresh() && !s.pending && power.available;
        if self.confirm == Some(Confirm::ShutDown) && !(idle && power.can_stop_camera) {
            self.confirm = None;
        }
        egui::CollapsingHeader::new("Studio power")
            .default_open(true)
            .show(ui, |ui| {
                for (p, device, on_label, off_label) in [
                    (&power.light, Outlet::Light, "Light on", "Light off"),
                    (
                        &power.camera,
                        Outlet::Camera,
                        "Power on & connect",
                        "Shut down camera",
                    ),
                ] {
                    let state = p.on;
                    ui.label(match (state, p.watts) {
                        (Some(on), Some(w)) => {
                            format!("{device:?} {} · {w:.1} W", if on { "on" } else { "off" })
                        }
                        _ => format!(
                            "{device:?} · {}",
                            p.error.as_deref().unwrap_or("Waiting for outlet")
                        ),
                    });
                    ui.horizontal_wrapped(|ui| {
                        for (on, label) in [(true, on_label), (false, off_label)] {
                            let allowed = match device {
                                Outlet::Light => state != Some(on),
                                Outlet::Camera if on => power.can_start_camera,
                                Outlet::Camera => power.can_stop_camera,
                            };
                            let shut_down = device == Outlet::Camera && !on;
                            if shut_down && self.confirm == Some(Confirm::ShutDown) {
                                if ui
                                    .add_enabled(idle && allowed, egui::Button::new("Shut down now"))
                                    .clicked()
                                {
                                    self.confirm = None;
                                    self.command(s, Command::Power { device, on });
                                }
                                if ui.button("Keep it on").clicked() {
                                    self.confirm = None;
                                }
                                continue;
                            }
                            let label = if shut_down {
                                format!("{label}…")
                            } else {
                                label.to_owned()
                            };
                            if ui
                                .add_enabled(idle && allowed, egui::Button::new(label))
                                .clicked()
                            {
                                if shut_down {
                                    self.confirm = Some(Confirm::ShutDown);
                                } else if device == Outlet::Camera && on {
                                    self.connect_camera(s, Command::Power { device, on });
                                } else {
                                    self.command(s, Command::Power { device, on });
                                }
                            }
                        }
                    });
                    if device == Outlet::Camera && self.confirm == Some(Confirm::ShutDown) {
                        ui.small("Restore the camera's settings, put it in standby and switch its outlet off?");
                    }
                }
                let mut enabled = power.manage_stack;
                if ui
                    .add_enabled(
                        idle && power.can_manage,
                        egui::Checkbox::new(
                            &mut enabled,
                            "Warm light at start, power both off after saving",
                        ),
                    )
                    .changed()
                {
                    self.command(s, Command::PowerPlan { enabled });
                }
                if let Some(e) = &power.error {
                    ui.colored_label(AMBER, e);
                }
                if s.host.schedule.is_some() {
                    let saved = power.warmup_seconds.unwrap_or(5) as u32;
                    let mut secs = self.warmup_edit.unwrap_or(saved);
                    ui.horizontal_wrapped(|ui| {
                        ui.label("Light warmup");
                        if ui
                            .add_enabled(
                                idle,
                                egui::DragValue::new(&mut secs).range(0..=300).suffix(" s"),
                            )
                            .changed()
                        {
                            self.warmup_edit = Some(secs);
                        }
                        if secs != saved
                            && ui
                                .add_enabled(idle, egui::Button::new("Save warmup"))
                                .clicked()
                        {
                            self.command(s, Command::SetWarmup { seconds: secs });
                            self.warmup_edit = None;
                        }
                    });
                    ui.small("Delay from switching the light on to starting the focus sweep.");
                }
            });
    }
    fn focus_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        ui.label(RichText::new("Focus bounds").strong());
        ui.label(format!(
            "Position  {}",
            s.host.position.map_or("—".into(), |p| p.to_string())
        ));
        self.scrub_ui(ui, s);
        let editable = s.fresh()
            && s.host.editable
            && !s.pending
            && self.focus_pending.is_none()
            && self.focus_flight.is_none();
        ui.add_enabled_ui(editable,|ui| {
            ui.horizontal(|ui| {
                for (label,delta) in [("−128",-128),("−16",-16),("−1",-1),("+1",1),("+16",16),("+128",128)] {
                    if ui.small_button(label).clicked(){self.command(s,Command::Jog{delta});}
                }
            });
            for (start,label,set) in [(true,"Start",s.host.start_set),(false,"End",s.host.end_set)] {
                ui.horizontal(|ui| {
                    let position=if start{self.draft.start}else{self.draft.end};
                    ui.label(format!("{label}  {}",if set{position.to_string()}else{"not set".into()}));
                    if ui.button(format!("Mark {label}")).clicked(){self.command(s,Command::Mark{start});}
                    if ui.add_enabled(set,egui::Button::new("Go")).clicked(){self.command(s,Command::Go{start});}
                });
            }
            ui.small("Move focus until the first and last details are sharp, then mark each bound.");
            ui.add_space(8.0);
            let supported = s.host.offers_four_shot();
            let mut shift = s.host.shots_per_plane == Some(4);
            if ui.add_enabled(supported, egui::Checkbox::new(&mut shift, "4-shot pixel shift")).on_hover_text("Four RAW exposures at each focus position. Requires a compatible camera and matching Pi driver.").changed() {
                self.command(s, Command::PixelShift { shots: if shift {4} else {1} });
            }
            self.test_shot_ui(ui, s);
            egui::Grid::new("capture-plan").num_columns(2).spacing([10.0,8.0]).show(ui,|ui| {
                ui.label("Step size");self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.step).range(1..=65535)).changed();ui.end_row();
                ui.label("Settle time");self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.settle_ms).range(100..=30000).suffix(" ms")).changed();ui.end_row();
            });
            ui.small("1 is the smallest normalized camera step. Lens response is not a calibrated distance.");
            self.calibration_ui(ui, s, editable);
            egui::CollapsingHeader::new("Sequence settings").show(ui,|ui| {
                ui.horizontal(|ui|{ui.label("Approach"); self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.approach).range(1..=4096)).changed();});
                ui.horizontal(|ui|{ui.label("Capture timeout");self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.capture_timeout_s).range(5..=3600).suffix(" s")).changed();});
            });
            if self.draft_dirty {
                ui.horizontal(|ui| {
                    if ui.button("Apply settings").clicked(){
                        let command=Command::Settings{step:self.draft.step,settle_ms:self.draft.settle_ms,approach:self.draft.approach,capture_timeout_s:self.draft.capture_timeout_s};
                        let result=s.request(command).and_then(|mut r|{r.plan_revision=self.draft_revision;self.submit(r)});
                        if result.is_ok(){self.draft_dirty=false;} self.record(result);
                    }
                    if ui.button("Discard edits").clicked(){self.draft_dirty=false;}
                });
            }
            let bounds=s.host.bounds_set();
            if ui.add_enabled(bounds && s.host.preview.fresh,egui::Button::new("Survey focus within these bounds")).clicked(){self.command(s,Command::Survey{});}
            ui.small("Survey uses the selected subject region to suggest tighter bounds. Set a broad range first.");
            if let Some(suggestion)=&s.host.suggestion {
                ui.label(suggestion.explanation.as_deref().unwrap_or("Focus survey finished"));
                if ui.add_enabled(!suggestion.clipped,egui::Button::new("Use suggested bounds")).clicked(){self.command(s,Command::ApplyBounds{});}
            }
            if !s.host.magnifier_ratios.is_empty() {
                egui::CollapsingHeader::new("Camera magnifier").show(ui,|ui| {
                    ui.horizontal_wrapped(|ui| {for &ratio in &s.host.magnifier_ratios {
                        if ui.button(if ratio==0{"Off".into()}else{format!("{:.1}×",ratio as f32/10.0)}).clicked(){
                            let roi: Roi=s.host.roi.unwrap_or_default();
                            self.command(s,Command::Magnify{ratio,x:((roi.x+roi.width/2.0)*639.0).round() as u16,y:((roi.y+roi.height/2.0)*479.0).round() as u16});
                        }
                    }});
                });
            }
        });
    }
    /// One exposure at the current focus, read on the RAW: its clipped share
    /// and shadow level.
    fn test_shot_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        use test_shot::TestShot as T;
        let ready = s.fresh()
            && s.host.editable
            && !s.pending
            && s.host.position.is_some()
            && !self.calibrating()
            && !self.test_shot.running();
        let mut stop = false;
        ui.horizontal_wrapped(|ui| {
            if ui
                .add_enabled(ready, egui::Button::new("Test shot"))
                .on_hover_text("One exposure at the current focus, saved on this PC and read on the RAW: how much clips and where the shadows sit. It is not checked, listed or opened as a stack.")
                .clicked()
            {
                let result = self.test_shot();
                self.record(result);
            }
            match &self.test_shot {
                T::Capturing { .. } | T::Reading { .. } => {
                    ui.spinner();
                    ui.small(if matches!(self.test_shot, T::Reading { .. }) {
                        "Reading the RAW…".to_owned()
                    } else {
                        format!(
                            "Taking a test shot · gives up in {} s",
                            self.test_shot
                                .gives_up_in(Instant::now())
                                .unwrap_or_default()
                                .as_secs()
                        )
                    });
                    ui.ctx().request_repaint_after(Duration::from_secs(1));
                    stop = matches!(self.test_shot, T::Capturing { .. })
                        && ui.small_button("Stop waiting").clicked();
                }
                T::Done { levels, .. } => {
                    ui.small(format!(
                        "RAW: {:.2} % clipped · shadows at {:.1} % · median {:.1} % of the range",
                        100.0 * levels.clipped_share,
                        100.0 * levels.shadow_level,
                        100.0 * levels.median_level
                    ));
                }
                T::Failed(e) => {
                    ui.colored_label(AMBER, e);
                }
                T::Idle => {}
            }
        });
        if stop {
            self.stop_test_shot();
        }
    }
    fn storage_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        ui.label(RichText::new("Storage on this PC").strong());
        let available = s.receiver["ok"] == true;
        let checking = s.receiver.is_null() && s.receiver_error.is_none();
        ui.colored_label(
            if available {
                GREEN
            } else if checking {
                MUTED
            } else {
                AMBER
            },
            if available {
                "Receiver ready · runs in background"
            } else if checking {
                "Checking receiver…"
            } else {
                "Receiver unavailable"
            },
        );
        if !available
            && !checking
            && ui
                .add_enabled(!s.pending, egui::Button::new("Start receiver"))
                .clicked()
        {
            let result = self.connection.as_ref().unwrap().start_receiver();
            self.record(result);
        }
        if !available && let Some(error) = &s.receiver_error {
            ui.small(error);
        }
        ui.small("RAWs go directly to this PC. Keep this PC awake and connected while capturing.");
        let free = s.receiver["free_bytes"].as_u64().unwrap_or(0);
        if available {
            ui.label(format!("{:.1} GB free", free as f64 / 1e9));
        }
        ui.add_enabled_ui(available && !s.pending, |ui| {
            self.folder_dirty |= ui
                .add(
                    egui::TextEdit::singleline(&mut self.folder_draft).desired_width(f32::INFINITY),
                )
                .changed();
            ui.horizontal(|ui| {
                if ui
                    .add_enabled(
                        self.folder_picker.is_none(),
                        egui::Button::new("Choose folder…"),
                    )
                    .clicked()
                {
                    let (tx, rx) = mpsc::channel();
                    self.folder_picker = Some(rx);
                    std::thread::spawn(move || {
                        let _ = tx.send(
                            rfd::FileDialog::new()
                                .set_title("Save new captures here")
                                .pick_folder(),
                        );
                    });
                }
                if ui
                    .add_enabled(self.folder_dirty, egui::Button::new("Save folder"))
                    .clicked()
                {
                    let result = self.connection.as_ref().unwrap().storage(
                        PathBuf::from(&self.folder_draft),
                        s.receiver["compress_raw"] != false,
                    );
                    if result.is_ok() {
                        self.folder_dirty = false;
                    }
                    self.record(result);
                }
            });
            let mut compressed = s.receiver["compress_raw"] != false;
            if ui
                .checkbox(&mut compressed, "Keep RAWs losslessly compressed")
                .changed()
                && let Some(folder) = s.receiver["folder"].as_str()
            {
                let result = self
                    .connection
                    .as_ref()
                    .unwrap()
                    .storage(folder.into(), compressed);
                self.record(result);
            }
        });
        ui.small("Strehl opens .ARW.straw directly. Changes apply to new stacks.");
        if let Some(receipt) = &s.host.storage.receipt {
            if let Some(rate) = receipt.wire_mb_per_second {
                ui.label(format!("Last transfer  {rate:.1} MB/s on Wi-Fi"));
            }
            if let (Some(raw), Some(stored)) = (receipt.bytes, receipt.storage_bytes)
                && raw > 0.0
            {
                ui.label(format!("Space saved  {:.0}%", 100.0 * (1.0 - stored / raw)));
            }
        }
    }
    fn follow_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        ui.label(RichText::new("Stack while capturing").strong());
        let mut enabled = self.follow_enabled;
        if ui
            .checkbox(&mut enabled, "Check and align planes as they arrive")
            .on_hover_text("Each focal plane is decoded, checked and aligned as soon as all its RAWs are saved on this PC. The final stack reuses that work, so it finishes sooner. Runs at low priority.")
            .changed()
        {
            self.set_follow(enabled);
        }
        ui.add_enabled(
            self.follow_enabled,
            egui::Checkbox::new(&mut self.stack_when_done, "Stack when the capture finishes"),
        )
        .on_hover_text("Open the finished capture in Projects and start the stack with your current settings. Skipped while another stack or import is running.");
        // Error correction is the camera host's setting; its verdicts come
        // from this checker, so it needs the checker on.
        let supported = s.host.error_correction.is_some();
        let active = s.host.phase.active();
        let mut correct = s.host.error_correction == Some(true);
        if ui
            .add_enabled(
                supported && s.fresh() && !s.pending && !active && (self.follow_enabled || correct),
                egui::Checkbox::new(&mut correct, "Error correction"),
            )
            .on_hover_text(if supported {
                "This PC checks each plane while the camera goes on to the next. A group that failed for movement, a focus slip or a level change is taken again: the camera goes back to that plane (approaching it from the same side as before) and then carries on, up to twice a plane. Planes that fail for too little detail are not retaken. Needs the checks above."
            } else {
                "Update the camera host to use error correction."
            })
            .changed()
        {
            self.command(s, Command::ErrorCorrection { enabled: correct });
        }
        if s.host.error_correction == Some(true) && !self.follow_enabled {
            ui.colored_label(
                AMBER,
                "Error correction needs the checks above; without them it turns itself off after the first plane.",
            );
        }
        let saved = s.host.saved;
        match &self.follower {
            Some(f) => {
                let p = f.progress();
                let name = f.run.file_name().unwrap_or_default().to_string_lossy();
                let counts = format!(
                    "{} planes checked{}",
                    p.checked,
                    if p.passed > 0 {
                        format!(" · {} four-shot groups pass", p.passed)
                    } else {
                        String::new()
                    }
                );
                match &f.state {
                    follow::State::Running => {
                        ui.horizontal_wrapped(|ui| {
                            ui.spinner();
                            ui.label(match saved {
                                Some(saved) if saved > p.checked as u64 => {
                                    format!("{counts} · {saved} saved")
                                }
                                _ => counts.clone(),
                            });
                        });
                        ui.small(if f.observing {
                            format!("{name} is being checked by another Strehl window")
                        } else {
                            format!("Following {name}")
                        });
                    }
                    follow::State::Finished => {
                        ui.colored_label(GREEN, format!("Capture checked · {counts}"));
                    }
                    follow::State::Failed(e) => {
                        ui.colored_label(AMBER, format!("Checking stopped: {e}"));
                        ui.small(format!("{counts}. Log: {}", f.log.display()));
                    }
                    follow::State::Stopped(why) => {
                        ui.colored_label(MUTED, format!("{why}. {counts}."));
                    }
                }
                if p.align_pairs > 0 {
                    ui.small(format!("{} alignment pairs measured", p.align_pairs));
                }
                if p.retaken > 0 {
                    ui.small(format!(
                        "{} plane{} retaken during the capture",
                        p.retaken,
                        if p.retaken == 1 { "" } else { "s" }
                    ));
                }
                if p.attention > 0 {
                    ui.colored_label(
                        AMBER,
                        format!(
                            "{} plane{} the stack will not assemble as recorded",
                            p.attention,
                            if p.attention == 1 { "" } else { "s" }
                        ),
                    );
                }
                if !p.retake.is_empty() {
                    let shown: Vec<String> = p.retake.iter().take(8).map(u64::to_string).collect();
                    ui.small(format!(
                        "Worth retaking at focus {}{}",
                        shown.join(", "),
                        if p.retake.len() > 8 { ", …" } else { "" }
                    ));
                }
            }
            None if !self.follow_enabled => {
                ui.small("Off. A capture is stacked from the start when you open it.");
            }
            None => {
                ui.small("Starts with the next capture saved on this PC.");
            }
        }
        if let Some((_, e)) = &self.follow_refused {
            ui.colored_label(AMBER, format!("Could not start checking: {e}"));
        }
        let retry = self.follow_refused.is_some()
            || self
                .follower
                .as_ref()
                .is_some_and(|f| matches!(f.state, follow::State::Failed(_)));
        if retry && self.follow_enabled && ui.button("Try again").clicked() {
            self.set_follow(true);
        }
        if let Some(note) = &self.follow_note {
            ui.small(note);
        }
    }
    /// Captures that ended early, listed as "stopped · N planes" and opened
    /// like any folder (Studio 2, D13).
    fn stopped_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot, can_import: bool) {
        if s.stopped.is_empty() {
            return;
        }
        ui.add_space(8.0);
        ui.label(RichText::new("Stopped captures").strong());
        self.selected_stopped = self.selected_stopped.min(s.stopped.len() - 1);
        let name = |run: &crate::capture_client::StoppedCapture| {
            format!(
                "{} · {}",
                run.folder.file_name().unwrap_or_default().to_string_lossy(),
                run.label()
            )
        };
        crate::theme::Dropdown::from_id_salt("capture-stopped")
            .width(ui.available_width() - 15.0)
            .selected_text(name(&s.stopped[self.selected_stopped]))
            .show_ui(ui, |ui| {
                for (i, run) in s.stopped.iter().enumerate() {
                    ui.selectable_value(&mut self.selected_stopped, i, name(run));
                }
            });
        let run = &s.stopped[self.selected_stopped];
        ui.small(format!(
            "{} RAWs on this PC{}{}",
            run.frames,
            if run.unverified > 0 {
                format!(" · {} without a matching receipt", run.unverified)
            } else {
                String::new()
            },
            if run.outcome == "uncertain" {
                " · ended by a fault"
            } else {
                ""
            }
        ));
        if ui
            .add_enabled(
                can_import && !s.pending,
                egui::Button::new("Open in Projects"),
            )
            .clicked()
        {
            let result = self.import_stopped(self.selected_stopped);
            self.record(result);
        }
    }
    fn completed_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot, can_import: bool) {
        ui.label(RichText::new("Completed captures").strong());
        if s.completed.is_empty() {
            ui.small("Completed, durably saved stacks will appear here.");
            self.stopped_ui(ui, s, can_import);
            return;
        }
        self.selected_stack = self.selected_stack.min(s.completed.len() - 1);
        crate::theme::Dropdown::from_id_salt("capture-completed")
            .width(ui.available_width() - 15.0)
            .selected_text(
                s.completed[self.selected_stack]
                    .folder
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy(),
            )
            .show_ui(ui, |ui| {
                for (i, stack) in s.completed.iter().enumerate() {
                    ui.selectable_value(
                        &mut self.selected_stack,
                        i,
                        stack
                            .folder
                            .file_name()
                            .unwrap_or_default()
                            .to_string_lossy(),
                    );
                }
            });
        let stack = &s.completed[self.selected_stack];
        ui.small(format!(
            "{} focal planes · {} RAWs · {} per plane",
            stack.planes, stack.frames, stack.shots_per_plane
        ));
        if ui
            .add_enabled(
                can_import && !s.pending,
                egui::Button::new("Open in Projects"),
            )
            .clicked()
        {
            let result = self.import_completed(self.selected_stack);
            self.record(result);
        }
        ui.small("Open the complete bracket for processing.");
        let folder = stack.folder.clone();
        let engine = self.engine.clone();
        ui.add_space(6.0);
        // How finely the planes sampled the depth of field.
        if ui
            .add_enabled(
                !self.step_report.running() && engine.is_some(),
                egui::Button::new("Measure focus step"),
            )
            .on_hover_text("How far detail stays sharp across this capture's planes, and the step that would have done.")
            .clicked()
        {
            self.step_report.start(
                engine.as_deref(),
                &folder,
                vec!["focus-step".into(), folder.clone().into_os_string()],
            );
        }
        if self.step_report.running() && self.step_report.folder.as_deref() == Some(&folder) {
            let mut cancel = false;
            ui.horizontal(|ui| {
                ui.spinner();
                ui.small(format!(
                    "Measuring… {} s",
                    self.step_report.elapsed().unwrap_or_default().as_secs()
                ));
                cancel = ui.small_button("Cancel").clicked();
            });
            ui.ctx().request_repaint_after(Duration::from_secs(1));
            if cancel {
                self.cancel_focus_step();
            }
        }
        match self.step_report.for_folder(&folder) {
            Some(Ok(v)) => {
                ui.small(v["summary"].as_str().unwrap_or(""));
            }
            Some(Err(e)) => {
                ui.colored_label(AMBER, e);
            }
            None => {}
        }
        // Compact: an estimate first, then an explicit confirmation.
        ui.add_space(6.0);
        let busy = self.compact_estimate.running() || self.compact_apply.running();
        if ui
            .add_enabled(!busy && engine.is_some(), egui::Button::new("Compact…"))
            .on_hover_text("Estimate how small this capture becomes when every sample is kept to within half a step of the camera's own noise. Nothing is changed until you confirm.")
            .clicked()
        {
            self.compact_confirm = false;
            self.compact_estimate.start(
                engine.as_deref(),
                &folder,
                vec!["compact".into(), folder.clone().into_os_string()],
            );
        }
        if busy && self.compact_estimate.folder.as_deref() == Some(&folder) {
            let mut cancel = false;
            ui.horizontal(|ui| {
                ui.spinner();
                ui.small(if self.compact_apply.running() {
                    "Compacting… (the originals are replaced one by one, each after its new file reads back)"
                } else {
                    "Estimating…"
                });
                cancel = self.compact_estimate.running() && ui.small_button("Cancel").clicked();
            });
            if cancel {
                self.cancel_compact_estimate();
            }
        }
        if let Some(Ok(v)) = self.compact_apply.for_folder(&folder) {
            let (before, after) = (
                v["before_bytes"].as_f64().unwrap_or(0.0),
                v["after_bytes"].as_f64().unwrap_or(0.0),
            );
            ui.colored_label(
                GREEN,
                format!(
                    "Compacted: {:.1} GB, {:.1} GB freed",
                    after / 1e9,
                    (before - after) / 1e9
                ),
            );
        } else if let Some(Err(e)) = self.compact_apply.for_folder(&folder) {
            ui.colored_label(
                AMBER,
                format!("Compact stopped: {e}. Files not yet compacted are unchanged."),
            );
        } else {
            match self.compact_estimate.for_folder(&folder) {
                Some(Ok(v)) => {
                    let (before, after) = (
                        v["before_bytes"].as_f64().unwrap_or(0.0),
                        v["estimated_after_bytes"].as_f64().unwrap_or(0.0),
                    );
                    ui.small(format!(
                        "Now {:.1} GB; compacted about {:.1} GB ({:.1} GB freed).",
                        before / 1e9,
                        after / 1e9,
                        (before - after) / 1e9
                    ));
                    ui.checkbox(
                        &mut self.compact_confirm,
                        "I understand this is not lossless: every sample is kept to within half a step of the camera's noise (renders measured the same as with that much extra noise, about +0.5 %), the camera's full-size preview JPEG is removed, and the original RAWs cannot be restored afterwards.",
                    );
                    if ui
                        .add_enabled(
                            self.compact_confirm && !busy,
                            egui::Button::new("Compact now"),
                        )
                        .clicked()
                    {
                        self.compact_confirm = false;
                        self.compact_apply.start(
                            engine.as_deref(),
                            &folder,
                            vec![
                                "compact".into(),
                                folder.clone().into_os_string(),
                                "--apply".into(),
                            ],
                        );
                    }
                }
                Some(Err(e)) => {
                    ui.colored_label(AMBER, e);
                }
                None => {}
            }
        }
        self.stopped_ui(ui, s, can_import);
    }
    fn sequence_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        let host = &s.host;
        let phase = host.phase;
        let active = phase.active();
        let total = if active && host.total > 0 {
            host.total
        } else {
            host.planned.unwrap_or(0)
        };
        let complete = if active { host.completed } else { 0 };
        let shots = host.shots();
        ui.horizontal(|ui| {
            ui.heading("Capture studio");
            ui.label(
                RichText::new(if shots > 1 {
                    format!("{shots}-shot pixel shift")
                } else {
                    "Single RAW per plane".into()
                })
                .color(ACCENT),
            );
            ui.colored_label(
                if phase == HostPhase::Fault {
                    FAULT_RED
                } else if s.fresh() {
                    GREEN
                } else {
                    AMBER
                },
                phase.as_str().to_uppercase(),
            );
        });
        ui.label(host.message.as_deref().unwrap_or("Connect the Pi to begin"));
        if let Some(e) = &s.host_error {
            ui.colored_label(FAULT_RED, e);
        }
        // The camera's USB link, while it is connected (round-3 performance
        // plan, C1): a body that fell back to USB 2.0 captures at about half
        // speed and says nothing else.
        if host.connected
            && let Some(warning) = host
                .usb_speed_mbps
                .and_then(|mbps| strehl_capture::worker::usb_link_warning(mbps as u32))
        {
            ui.colored_label(AMBER, format!("{warning}."));
        }
        if let Some(error) = self.error.as_ref().or(s.command_error.as_ref()) {
            ui.colored_label(AMBER, error);
        }
        if let Some(failure) = &host.failure {
            ui.colored_label(
                FAULT_RED,
                failure
                    .message
                    .as_deref()
                    .unwrap_or("Capture needs attention"),
            );
            let uncertain = failure.exposure_uncertain;
            if uncertain {
                ui.checkbox(
                    &mut self.acknowledge_uncertain,
                    "I checked the last exposure; recover without replaying it",
                );
            }
            if ui
                .add_enabled(
                    s.fresh() && !s.pending && (!uncertain || self.acknowledge_uncertain),
                    egui::Button::new("Recover camera"),
                )
                .clicked()
            {
                self.command(
                    s,
                    Command::Recover {
                        acknowledge_uncertain: self.acknowledge_uncertain,
                    },
                );
                self.acknowledge_uncertain = false;
            }
        }
        let capacity_error = preflight::capacity_error(s);
        // The single source of truth for Start (P0 item 2).
        let blockers = preflight::start_blockers(s, self);
        let start = blockers.is_empty();
        let can_stop = s.fresh() && active && !s.pending && host.pending_control != 2;
        if !can_stop && self.confirm == Some(Confirm::Stop) {
            self.confirm = None;
        }
        ui.horizontal_wrapped(|ui| {
            if ui
                .add_enabled(
                    start,
                    egui::Button::new(
                        RichText::new(if host.schedule_stage() == Some("armed") {
                            "Start stack now"
                        } else {
                            "Start stack"
                        })
                        .color(BG),
                    )
                    .fill(ACCENT),
                )
                .clicked()
            {
                self.command(s, Command::Start {});
            }
            if let Some(first) = blockers.first()
                && !active
            {
                ui.label(RichText::new(&first.sentence).color(MUTED))
                    .on_hover_text(
                        blockers
                            .iter()
                            .map(|b| format!("{}: {}", b.chip, b.sentence))
                            .collect::<Vec<_>>()
                            .join("\n"),
                    );
            }
            if host.schedule.is_some()
                && !matches!(host.schedule_stage(), Some("armed" | "running"))
                && ui.button("Schedule stack…").clicked()
            {
                self.schedule_ui.open(s);
            }
            if phase == HostPhase::Paused {
                if ui
                    .add_enabled(s.fresh() && !s.pending, egui::Button::new("Resume"))
                    .clicked()
                {
                    self.command(s, Command::Resume {});
                }
            } else if ui
                .add_enabled(
                    s.fresh()
                        && phase == HostPhase::Capturing
                        && !s.pending
                        && host.pending_control != 1,
                    egui::Button::new("Pause"),
                )
                .clicked()
            {
                self.command(s, Command::Pause {});
            }
            if self.confirm == Some(Confirm::Stop) {
                if ui
                    .add_enabled(can_stop, egui::Button::new("Stop now"))
                    .clicked()
                {
                    self.confirm = None;
                    self.command(s, Command::Stop {});
                }
                if ui.button("Keep going").clicked() {
                    self.confirm = None;
                }
            } else if ui
                .add_enabled(can_stop, egui::Button::new("Stop…"))
                .on_hover_text("Asks before stopping the sequence")
                .clicked()
            {
                self.confirm = Some(Confirm::Stop);
            }
            if s.pending {
                ui.spinner();
                ui.label("Sending…");
            }
            ui.label(if active {
                format!(
                    "{} / {} planes · {} RAWs saved",
                    complete,
                    total,
                    host.storage.saved_frames.unwrap_or(0)
                )
            } else {
                format!("{total} planes · {} RAWs planned", total * shots)
            });
        });
        if self.confirm == Some(Confirm::Stop) {
            ui.small(if shots > 1 {
                "Stop the stack? The current pixel-shift group finishes, and every plane taken so far is kept."
            } else {
                "Stop the stack? Every plane taken so far is kept."
            });
        }
        if let Some(cmd) = self
            .schedule_ui
            .show(ui, s, preflight::can_schedule(&blockers))
        {
            self.command(s, cmd);
        }
        if let Some(error) = &capacity_error {
            ui.colored_label(AMBER, error);
        }
        if let Some(bytes) = host.storage_required_bytes {
            ui.small(storage_line(
                total * shots,
                bytes,
                &s.stored,
                host.camera_model.as_deref(),
                &s.receiver,
            ));
        }
        if let Some(error) = &host.plan_error {
            ui.colored_label(AMBER, error);
        }
        let percent = if total > 0 {
            complete as f32 / total as f32
        } else {
            0.0
        };
        ui.add(egui::ProgressBar::new(percent.clamp(0.0, 1.0)).desired_height(4.0));
        ui.horizontal_wrapped(|ui| {
            let timer = host.timer.as_ref();
            if active {
                ui.label(format!(
                    "Elapsed {}",
                    duration(timer.and_then(|t| t.elapsed))
                ));
            }
            let remaining = if active {
                timer.and_then(|t| t.remaining)
            } else {
                host.initial_seconds
            };
            ui.label(format!(
                "{} {}",
                if active {
                    "Estimated remaining"
                } else {
                    "Estimated stack duration"
                },
                duration(remaining)
            ));
            if let Some(queued) = host.storage.pending_frames {
                ui.label(format!("{queued} RAWs awaiting PC"));
            }
            if shots > 1 && active {
                ui.small("Pause / stop finishes the current pixel-shift group.");
            }
        });
    }
    fn preview_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        if let Some(error) = s
            .preview_error
            .as_deref()
            .or(s.host.preview.error.as_deref())
        {
            // Decoder errors are independent of focus controls.
            if !error.is_empty() {
                ui.colored_label(AMBER, error);
            }
        }
        if !s.host.preview.fresh && self.texture.is_some() {
            ui.colored_label(AMBER, "Last preview · waiting for a fresh camera frame");
        }
        let Some((_, texture)) = &self.texture else {
            ui.centered_and_justified(|ui|{ui.label(RichText::new("Live preview appears here\nFocus controls remain available if preview is interrupted.").color(MUTED));});
            return;
        };
        let texture = texture.clone();
        let available = ui.available_size();
        let fit = (available.x / texture.size_vec2().x)
            .min((available.y - 22.0).max(50.0) / texture.size_vec2().y);
        let size = texture.size_vec2() * fit * self.zoom;
        egui::ScrollArea::both()
            .id_salt("capture-preview-scroll")
            .auto_shrink([false, false])
            .show(ui, |ui| {
                let response = ui.add(
                    egui::Image::new((texture.id(), size)).sense(egui::Sense::click_and_drag()),
                );
                let r = response.rect;
                if self.peaking
                    && s.host.preview.fresh
                    && let Some((generation, _, peaks)) = &self.peak_texture
                    && self.texture.as_ref().is_some_and(|(g, _)| g == generation)
                {
                    ui.painter().image(
                        peaks.id(),
                        r,
                        egui::Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                        egui::Color32::WHITE,
                    );
                }
                if self.select_roi && s.fresh() && s.host.editable && !s.pending {
                    if response.drag_started() {
                        self.roi_start = response.interact_pointer_pos();
                    }
                    if let (Some(start), Some(end)) =
                        (self.roi_start, response.interact_pointer_pos())
                    {
                        let region = egui::Rect::from_two_pos(start, end).intersect(r);
                        ui.painter().rect_stroke(
                            region,
                            0.0,
                            egui::Stroke::new(2.0_f32, INK),
                            egui::StrokeKind::Inside,
                        );
                        if response.drag_stopped() {
                            let roi = Roi {
                                x: (region.left() - r.left()) / r.width(),
                                y: (region.top() - r.top()) / r.height(),
                                width: region.width() / r.width(),
                                height: region.height() / r.height(),
                            };
                            if roi.width >= 0.05 && roi.height >= 0.05 {
                                self.command(s, Command::Roi { roi });
                                self.select_roi = false;
                            }
                            self.roi_start = None;
                        }
                    }
                }
            });
    }
}
/// Calls for the Studio 2 shell and the Capture station. Until the shell
/// wires them, the current Capture tab does not need them all.
#[allow(dead_code)]
impl CaptureWorkspace {
    // ---- Calls for the shell (Studio 2, P6; P0 items 8 and 9) ----------
    //
    // Every frame, on every station:
    //   capture.set_station_open(route == Capture);
    //   capture.poll_background(ctx, engine);        // instead of poll_follow
    // When the Capture station is shown: capture.show(ctx, can_import).
    // For the status bar and the notice tray:
    //   capture.status_line(), capture.unread_notice(), capture.cadence().

    /// Keeps the Pi connection up whenever capture is configured, not only
    /// while Capture is open (P0 item 8), then runs [`Self::poll_follow`].
    /// Polling is 1 Hz with the station closed and no sequence running, and
    /// 5 Hz otherwise ([`Cadence`]). Tests and headless control should pass
    /// an isolated `--capture-settings` file: with the owner's settings this
    /// connects to the real Pi (reads only; it sends no camera command).
    pub fn poll_background(&mut self, ctx: &egui::Context, engine: Option<&std::path::Path>) {
        if !self.config.controller.trim().is_empty() {
            self.activate(ctx);
        }
        self.poll_follow(engine);
    }
    /// Whether the shell shows the Capture station. Until it is called the
    /// workspace takes [`Self::show`] having run since the last poll.
    pub fn set_station_open(&mut self, open: bool) {
        self.station_open = Some(open);
    }
    /// The connection's polling cadence, once connected.
    pub fn cadence(&self) -> Option<Cadence> {
        self.connection.as_ref().map(Connection::cadence)
    }
    /// The newest success notice ("Request accepted", "Connection saved",
    /// ...), once: `None` after it was read, until a new one (P0 item 9).
    pub fn unread_notice(&mut self) -> Option<String> {
        let s = self.connection.as_ref()?.snapshot();
        if s.notice_id == self.notice_read {
            return None;
        }
        self.notice_read = s.notice_id;
        s.notice
    }
    /// A short line for the status bar while a sequence runs or the
    /// desktop's own camera work does; `None` when idle.
    pub fn status_line(&self) -> Option<String> {
        let s = self.connection.as_ref()?.snapshot();
        let host = &s.host;
        if host.phase.active() {
            let what = if host.phase == HostPhase::Scanning {
                "Surveying".to_owned()
            } else {
                format!(
                    "Capturing {} / {} planes",
                    host.completed,
                    host.total.max(host.completed)
                )
            };
            let left = host
                .timer
                .as_ref()
                .and_then(|t| t.remaining)
                .map(|r| format!(" · {} left", duration(Some(r))))
                .unwrap_or_default();
            let paused = if host.phase == HostPhase::Paused {
                " · paused"
            } else {
                ""
            };
            return Some(format!("{what}{left}{paused}"));
        }
        if self.calibrating() {
            return Some(format!("Calibrating step · {}", self.calibration.stage()));
        }
        if self.test_shot.running() {
            return Some("Test shot".into());
        }
        (host.phase == HostPhase::Fault).then(|| "Camera needs attention".into())
    }
    /// Every reason Start is unavailable now ([`preflight::start_blockers`]).
    pub fn start_blockers(&self) -> Vec<preflight::Blocker> {
        let s = self
            .connection
            .as_ref()
            .map(Connection::snapshot)
            .unwrap_or_default();
        preflight::start_blockers(&s, self)
    }
    /// The capture, its checker, the calibration and the engine tools as
    /// activities (Studio 2 P5, plan 6.6). Cheap: no I/O, one snapshot read.
    pub(crate) fn report_activities(&self, activities: &mut crate::activity::Activities) {
        use crate::activity::{
            ActivityKind, ActivityState, ActivityStatus, CancelMode, Lane, calibration_status,
            follow_status, tool_status,
        };
        if let Some(connection) = &self.connection {
            let s = connection.snapshot();
            let host = &s.host;
            if host.phase.active() && !self.calibrating() {
                let key = host
                    .sequence_id
                    .map_or_else(|| "capture".to_owned(), |id| format!("sequence:{id}"));
                let paused = host.phase == HostPhase::Paused;
                let mut status = ActivityStatus::new(
                    ActivityKind::Capture,
                    &key,
                    ActivityKind::Capture.label(),
                    Lane::Camera,
                )
                .with_phase(if host.phase == HostPhase::Scanning {
                    "Surveying the range"
                } else if paused {
                    "Paused"
                } else {
                    "Capturing"
                })
                .with_progress(
                    (host.phase != HostPhase::Scanning).then_some(host.completed),
                    (host.phase != HostPhase::Scanning).then_some(host.total.max(host.completed)),
                )
                .with_cancel(CancelMode::Cooperative);
                status.eta = host
                    .timer
                    .as_ref()
                    .and_then(|t| t.remaining)
                    .map(|r| std::time::Duration::from_secs_f64(r.max(0.0)));
                if paused {
                    status.state = ActivityState::Waiting {
                        for_what: "you to resume the capture".into(),
                        gives_up: None,
                    };
                }
                activities.report(status);
            } else if host.phase == HostPhase::Fault {
                activities.report(
                    ActivityStatus::new(
                        ActivityKind::Capture,
                        "capture-fault",
                        ActivityKind::Capture.label(),
                        Lane::Camera,
                    )
                    .with_state(ActivityState::NeedsYou {
                        message: "The camera needs attention".into(),
                        action: Some(crate::activity::ActionId::OpenCapture),
                    }),
                );
            }
        }
        if let Some(follower) = &self.follower {
            activities.report(follow_status(follower));
        }
        if let Some(status) = calibration_status(&self.calibration, "calibration") {
            activities.report(status);
        }
        for (kind, slot, lane) in [
            (ActivityKind::FocusStep, &self.step_report, Lane::Background),
            (
                ActivityKind::CompactEstimate,
                &self.compact_estimate,
                Lane::Background,
            ),
            (ActivityKind::CompactApply, &self.compact_apply, Lane::Heavy),
        ] {
            if let Some(status) = tool_status(kind, slot, lane) {
                activities.report(status);
            }
        }
    }
    /// The capture checker's records, each plane's journal line among them.
    pub fn follow_progress(&self) -> Option<&follow::Progress> {
        self.follower.as_ref().map(follow::Follower::progress)
    }
    /// Takes a test shot at the current focus: one position, power kept on,
    /// marked `kind: "test"` when the host supports it. Its run is never
    /// followed, listed or handed to the library; its RAW's clipped share and
    /// shadow level are read on a worker (`capture.tools.test_shot`).
    pub fn test_shot(&mut self) -> anyhow::Result<()> {
        let s = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .snapshot();
        anyhow::ensure!(!self.calibrating(), "A calibration is running");
        anyhow::ensure!(!self.test_shot.running(), "A test shot is running");
        anyhow::ensure!(
            s.fresh() && s.host.editable && !s.pending,
            "The camera is not ready"
        );
        let position = s
            .host
            .position
            .ok_or_else(|| anyhow::anyhow!("The focus position is unknown"))?;
        let kind = if s.host.capabilities.test_shot {
            PositionsKind::Test
        } else {
            PositionsKind::Positions
        };
        let request = s.request(Command::CapturePositions {
            positions: vec![position],
            // Managed power would switch the rig off after one exposure.
            keep_power_on: true,
            kind,
        })?;
        let sequence = s.host.sequence_id.unwrap_or(0) + 1;
        self.submit(request)?;
        self.test_shot = test_shot::TestShot::Capturing {
            sequence,
            deadline: Instant::now() + test_shot::TEST_SHOT_TIMEOUT + Self::warmup(&s),
            folder: None,
        };
        Ok(())
    }
    /// Stops waiting for a test shot; a run still being written is not
    /// followed.
    pub fn stop_test_shot(&mut self) {
        if let Some(sequence) = self.test_shot.sequence() {
            self.unfollowed_sequence = Some(sequence);
        }
        self.test_shot.stop();
    }
    /// Stops waiting for the camera to connect. Nothing is sent: the host
    /// keeps its own limit.
    pub fn stop_waiting_for_camera(&mut self) {
        if self.connect_wait.take().is_some() {
            self.connect_note = Some("Stopped waiting for the camera".into());
        }
    }
    /// Ends a running focus-step measurement (P0 item 7).
    pub fn cancel_focus_step(&mut self) {
        self.step_report.cancel();
    }
    /// Ends a running compaction estimate (P0 item 7). The compaction itself
    /// is not offered a cancel: it is safe to interrupt, but it is the
    /// owner's explicit action.
    pub fn cancel_compact_estimate(&mut self) {
        self.compact_estimate.cancel();
    }
    /// Opens a stopped capture from `capture.stopped` in Projects, like any
    /// folder (Studio 2, D13).
    pub fn import_stopped(&mut self, index: usize) -> anyhow::Result<()> {
        let c = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?;
        let s = c.snapshot();
        let run = s
            .stopped
            .get(index)
            .ok_or_else(|| anyhow::anyhow!("Stopped capture unavailable"))?;
        c.handoff(run.folder.clone())
    }
}

fn duration(seconds: Option<f64>) -> String {
    let Some(seconds) = seconds.filter(|s| s.is_finite() && *s >= 0.0) else {
        return "—".into();
    };
    let n = seconds.round() as u64;
    format!("{:02}:{:02}:{:02}", n / 3600, n / 60 % 60, n % 60)
}

/// The capture screen's storage line: the expected size on disk, from the
/// last capture with this camera (`stored`) as the receiver now stores RAWs,
/// and the worst case the stack must find free to start (`required`: every
/// RAW at the camera's largest size, uncompressed, with headroom).
fn storage_line(
    raws: u64,
    required: u64,
    stored: &[crate::capture_client::StoredRaws],
    model: Option<&str>,
    receiver: &serde_json::Value,
) -> String {
    let worst = format!(
        "up to {:.1} GB must be free to start",
        required as f64 / 1e9
    );
    let past = model.and_then(|m| stored.iter().find(|s| s.model == m));
    match past {
        Some(past) if receiver["ok"] == true => {
            let compress = receiver["compress_raw"].as_bool().unwrap_or(true);
            let format = receiver["archive_format"].as_u64().unwrap_or(1) as u8;
            let (per_raw, basis) = past.expected(compress, format);
            format!(
                "{raws} RAWs · about {:.1} GB on disk ({basis}) · {worst}",
                (raws * per_raw) as f64 / 1e9
            )
        }
        _ => format!("{raws} RAWs · {worst}; compression savings are extra"),
    }
}

#[cfg(test)]
#[path = "capture-workspace-tests.rs"]
mod station_tests;

#[cfg(test)]
mod tests {
    /// The expected size follows the last capture with the connected camera
    /// as the receiver stores RAWs now; with no such capture only the worst
    /// case is given.
    #[test]
    fn the_storage_line_expects_what_the_receiver_will_store() {
        use crate::capture_client::StoredRaws;
        use serde_json::json;
        let past = |encoding: &str| StoredRaws {
            folder: "stack".into(),
            model: "ILCE-7CR".into(),
            raw_format: "sony-uncompressed".into(),
            raws: 784,
            original: 125_600_000,
            stored: 65_000_000,
            encoding: encoding.into(),
        };
        let receiver = |compress: bool, format: Option<u64>| {
            let mut r = json!({"ok":true,"compress_raw":compress});
            if let Some(f) = format {
                r["archive_format"] = json!(f);
            }
            r
        };
        let line = |stored: &[StoredRaws], model: &str, r: serde_json::Value| {
            storage_line(784, 132_000_000_000, stored, Some(model), &r)
        };
        let v2 = [past("strehl-archive-v2")];
        let v1 = [past("strehl-archive-v1")];
        assert_eq!(
            line(&v2, "ILCE-7CR", receiver(true, Some(2))),
            "784 RAWs · about 51.0 GB on disk (as your last ILCE-7CR capture) · up to 132.0 GB must be free to start"
        );
        let l = line(&v1, "ILCE-7CR", receiver(true, Some(2)));
        assert!(
            l.contains("about 48.8 GB") && l.contains("less 4 % for archive format 2"),
            "{l}"
        );
        let l = line(&v1, "ILCE-7CR", receiver(true, None));
        assert!(l.contains("about 51.0 GB"), "an older receiver: {l}");
        let l = line(&v2, "ILCE-7CR", receiver(false, Some(2)));
        assert!(
            l.contains("about 98.5 GB") && l.contains("uncompressed"),
            "{l}"
        );
        assert_eq!(
            line(&v2, "ILCE-7CM2", receiver(true, Some(2))),
            "784 RAWs · up to 132.0 GB must be free to start; compression savings are extra"
        );
        assert!(!line(&v2, "ILCE-7CR", json!(null)).contains("about"));
    }

    #[test]
    fn accepted_marks_update_with_an_unapplied_step_edit() {
        let tmp = tempfile::tempdir().unwrap();
        let mut ui = CaptureWorkspace::new(Some(tmp.path().join("capture.json")));
        let mut plan = Plan {
            start: 39000,
            end: 39001,
            ..Default::default()
        };
        ui.sync_plan(plan.clone(), 1);
        ui.draft.step = 8;
        ui.draft_dirty = true;
        plan.start = 39100;
        plan.end = 39800;
        ui.sync_plan(plan.clone(), 2);
        assert_eq!(
            (
                ui.draft.start,
                ui.draft.end,
                ui.draft.step,
                ui.draft_revision
            ),
            (39100, 39800, 8, 2)
        );
        plan.step = 4;
        ui.sync_plan(plan, 3);
        assert_eq!(
            ui.draft_revision, 2,
            "conflicting settings must still require review"
        );
    }
    use super::*;
    fn ready() -> Snapshot {
        let mut s = Snapshot {
            online: true,
            observed: Some(Instant::now()),
            ..Default::default()
        };
        s.set_state(json!({"phase":"ready","editable":true,"connected":true,"position":30000,"camera_revision":10}));
        s
    }
    /// Changes one field of the host's state, typed reading included.
    fn set(s: &mut Snapshot, key: &str, value: Value) {
        let mut state = s.state.clone();
        state[key] = value;
        s.set_state(state);
    }
    #[test]
    fn scrub_coalesces_intent_and_drops_it_on_failure_or_sequence_start() {
        let temp = tempfile::tempdir().unwrap();
        let mut ui = CaptureWorkspace::new(Some(temp.path().join("config.json")));
        let mut s = ready();
        ui.observe_focus(&s);
        assert_eq!(ui.focus_target, 30000);
        ui.focus_flight = Some((30001, 10, Instant::now()));
        ui.focus_pending = Some(30010); // Newest slider intent replaces intermediate targets.
        set(&mut s, "phase", json!("moving"));
        set(&mut s, "editable", json!(false));
        ui.observe_focus(&s);
        assert_eq!(ui.focus_pending, Some(30010));
        assert!(ui.focus_flight.is_some());
        set(&mut s, "phase", json!("ready"));
        set(&mut s, "editable", json!(true));
        set(&mut s, "camera_revision", json!(11));
        set(&mut s, "position", json!(30001));
        ui.observe_focus(&s);
        assert!(ui.focus_flight.is_none());
        assert_eq!(ui.focus_pending, Some(30010));
        ui.focus_flight = Some((30010, 11, Instant::now()));
        ui.focus_pending = Some(30015);
        s.command_error = Some("Acknowledgement lost".into());
        ui.observe_focus(&s);
        assert!(ui.focus_pending.is_none() && ui.focus_flight.is_none());
        s.command_error = None;
        ui.focus_pending = Some(30020);
        set(&mut s, "phase", json!("capturing"));
        ui.observe_focus(&s);
        assert!(ui.focus_pending.is_none());
    }
    #[test]
    fn changing_slider_range_does_not_move_the_camera_without_input() {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let temp = tempfile::tempdir().unwrap();
        let mut ui = CaptureWorkspace::new(Some(temp.path().join("config.json")));
        let mut s = ready();
        set(&mut s, "start_set", json!(true));
        set(&mut s, "end_set", json!(true));
        ui.focus_target = 30000;
        ui.focus_anchor = Some(30000);
        ui.focus_range = 1;
        ui.draft.start = 10000;
        ui.draft.end = 10100;
        for _ in 0..3 {
            let _ = ctx.run(Default::default(), |ctx| {
                egui::CentralPanel::default().show(ctx, |panel| ui.scrub_ui(panel, &s));
            });
        }
        assert_eq!(ui.focus_target, 30000);
        assert!(ui.focus_pending.is_none());
    }
}
