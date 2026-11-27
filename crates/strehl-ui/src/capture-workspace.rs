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
    theme::{AMBER, GREEN, MUTED},
};
use eframe::egui::{self, RichText};
use serde_json::{Value, json};
use std::{
    path::PathBuf,
    sync::mpsc,
    time::{Duration, Instant},
};
use strehl_capture::{
    model::Plan,
    session::{Command, CommandRequest, PositionsKind},
};
#[path = "capture-auto-subject.rs"]
pub(crate) mod auto_subject;
#[path = "capture-fixture.rs"]
pub(crate) mod fixture;
#[path = "capture-flight.rs"]
pub(crate) mod flight;
#[path = "capture-follow.rs"]
pub(crate) mod follow;
#[path = "capture-glance.rs"]
pub(crate) mod glance;
#[path = "capture-guide.rs"]
pub(crate) mod guide;
#[path = "capture-live.rs"]
pub(crate) mod live;
#[path = "capture-measure.rs"]
pub(crate) mod measure;
#[path = "capture-plan.rs"]
pub(crate) mod plan;
#[path = "capture-plane-view.rs"]
pub(crate) mod plane_view;
#[path = "capture-planes.rs"]
pub(crate) mod planes;
#[path = "capture-preflight.rs"]
pub(crate) mod preflight;
#[path = "capture-rail.rs"]
pub(crate) mod rail;
#[path = "capture-rig-settings.rs"]
pub(crate) mod rig_settings;
#[path = "capture-schedule.rs"]
mod schedule_ui;
#[path = "capture-station.rs"]
pub(crate) mod station;
#[path = "capture-stillness.rs"]
pub(crate) mod stillness;
#[path = "capture-style.rs"]
pub(crate) mod style;
#[path = "capture-subject.rs"]
pub(crate) mod subject;
#[path = "capture-sweep.rs"]
pub(crate) mod sweep;
#[path = "capture-test-shot.rs"]
pub(crate) mod test_shot;
#[path = "capture-tools.rs"]
pub(crate) mod tools;

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
    draft: Plan,
    confirmed_plan: Plan,
    draft_revision: u64,
    draft_dirty: bool,
    acknowledge_uncertain: bool,
    folder_picker: Option<mpsc::Receiver<Option<PathBuf>>>,
    folder_draft: String,
    folder_dirty: bool,
    selected_stack: usize,
    painted_ready: bool,
    phone_open: bool,
    phone_texture: Option<(String, egui::TextureHandle)>,
    focus_target: u16,
    focus_pending: Option<u16>,
    focus_flight: Option<(u16, u64, Instant)>,
    schedule_ui: schedule_ui::ScheduleUi,
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
    /// The ISO and shutter codes the test shot was taken at, for the
    /// exposure guidance.
    test_shot_exposure: Option<(u64, u64)>,
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
    /// Plan Q7: the stillness check before Start.
    stillness: stillness::StillnessCheck,
    /// The camera took four RAWs a plane when the calibration began: a
    /// calibration that fails sets it again (see `poll_tools`).
    restore_four_after_calibration: bool,
    /// Plan S1: an outline to give the host once it can take one (the
    /// subject's last outline, for a new stack of it).
    pending_subject: Option<strehl_capture::model::Subject>,
    /// Plan X2: a highlight plan to give the host once the exposure it goes
    /// with has been set.
    pending_highlight: Option<Option<strehl_capture::model::Highlight>>,
    /// Plan S2/S3: the bounds survey's live frames and the automatic
    /// selection made from them.
    survey_frames: auto_subject::SurveyFrames,
    auto_subject: auto_subject::AutoSubject,
    /// The calibration pass (capture calibration spec 4): one button runs
    /// the sweep, the light wait, the test pair and the survey.
    pub(crate) pass: measure::Pass,
    /// When the light was first seen on (spec 4: exposure work waits until
    /// it has been on [`measure::LIGHT_SETTLED`]).
    light_on_since: Option<Instant>,
    /// The lens position when the camera was first seen connected: a pass
    /// seeds its sweep from the marks until the lens has moved.
    connect_position: Option<u16>,
    /// The Depth lens's map, built when the pass's facts change.
    depth_cache: Option<(u64, Option<std::sync::Arc<live::DepthMap>>)>,
    /// What the owner set by hand since "New capture" (rule 2).
    pub(crate) held: measure::Held,
    /// A finished pass's values, applied one a frame once the camera is
    /// ready (marks move the lens; settings and exposure wait their turn).
    fill_queue: std::collections::VecDeque<plan::PlanIntent>,
    /// The proof plane (spec 5.8), and the plan's base shutter while it runs.
    pub(crate) proof: measure::Proof,
    proof_base_shutter: Option<u64>,
    /// The last stack's highlight-group line, for the capture it is of:
    /// its folder, the line, and whether every group was used.
    pub(crate) stacked_highlights: Option<(PathBuf, String, bool)>,
    /// A proof that could not be sent waits until then; tries so far.
    proof_retry: Option<Instant>,
    proof_tries: u32,
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
            draft: Plan::default(),
            confirmed_plan: Plan::default(),
            draft_revision: 0,
            draft_dirty: false,
            acknowledge_uncertain: false,
            folder_picker: None,
            folder_draft: String::new(),
            folder_dirty: false,
            selected_stack: 0,
            painted_ready: false,
            phone_open: false,
            phone_texture: None,
            focus_target: 0,
            focus_pending: None,
            focus_flight: None,
            schedule_ui: Default::default(),
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
            test_shot_exposure: None,
            connect_wait: None,
            connect_note: None,
            confirm: None,
            station_open: None,
            shown: false,
            unfollowed_sequence: None,
            notice_read: 0,
            selected_stopped: 0,
            station: station::Station::default(),
            stillness: Default::default(),
            restore_four_after_calibration: false,
            pending_subject: None,
            pending_highlight: None,
            survey_frames: Default::default(),
            auto_subject: Default::default(),
            pass: Default::default(),
            light_on_since: None,
            connect_position: None,
            depth_cache: None,
            held: Default::default(),
            fill_queue: Default::default(),
            proof: Default::default(),
            proof_base_shutter: None,
            proof_retry: None,
            proof_tries: 0,
            stacked_highlights: None,
        }
    }
    fn calibrating(&self) -> bool {
        self.calibration.running() || self.pass.running()
    }
    /// The calibration's depth map for the Depth lens (spec 6.1): from the
    /// survey's RAW tiles once read, else from the live sweep's.
    pub(crate) fn depth_map(&mut self) -> Option<std::sync::Arc<live::DepthMap>> {
        let f = &self.pass.facts;
        let revision = f.revision;
        if let Some((r, m)) = &self.depth_cache
            && *r == revision
        {
            return m.clone();
        }
        let map = self.build_depth_map(revision).map(std::sync::Arc::new);
        self.depth_cache = Some((revision, map.clone()));
        map
    }
    fn build_depth_map(&self, revision: u64) -> Option<live::DepthMap> {
        let mut map = self.build_depth_map_only(revision)?;
        // The Still lens: the last proof plane's check (spec 6.1).
        let active = auto_subject::active_px(None).map(|v| v as f32);
        map.still = self.pass.facts.proofs.last().and_then(|p| {
            let (cols, rows, tile, local) = p.map.clone()?;
            Some(live::StillMap {
                cols,
                rows,
                extent: [
                    cols as f32 * tile / active[0],
                    rows as f32 * tile / active[1],
                ],
                local,
                limit: p.limit_px.unwrap_or(0.51) as f32,
                verdict: measure::proof_line(std::slice::from_ref(p))
                    .and_then(|l| l.split(':').next().map(str::to_owned))
                    .unwrap_or_default(),
            })
        });
        Some(map)
    }
    fn build_depth_map_only(&self, revision: u64) -> Option<live::DepthMap> {
        let f = &self.pass.facts;
        if let Some(v) = &f.survey
            && let Some(m) = v.get("maps")
            && let (Some(cols), Some(rows), Some(focus)) = (
                m["cols"].as_u64(),
                m["rows"].as_u64(),
                m["focus"].as_array(),
            )
        {
            let (cols, rows) = (cols as usize, rows as usize);
            let focus: Vec<Option<f64>> = focus.iter().map(Value::as_f64).collect();
            let d = &v["depth"];
            let active = auto_subject::active_px(None).map(|v| v as f32);
            let tile = m["tile_px"].as_f64().unwrap_or(64.0) as f32;
            if focus.len() == cols * rows
                && let (Some(lo), Some(hi)) =
                    (d["in_focus_first"].as_f64(), d["in_focus_last"].as_f64())
            {
                return Some(live::DepthMap {
                    revision,
                    cols,
                    rows,
                    focus,
                    lo,
                    hi,
                    source: "from RAW",
                    depth: v["step"]["width"]
                        .as_f64()
                        .unwrap_or(measure::DEFAULT_DEPTH),
                    extent: [
                        cols as f32 * tile / active[0],
                        rows as f32 * tile / active[1],
                    ],
                    anchor: f.busiest,
                    light: (|| {
                        let level: Vec<f32> = m["level"]
                            .as_array()?
                            .iter()
                            .map(|v| v.as_f64().unwrap_or(0.0) as f32)
                            .collect();
                        let glint: Vec<f32> = m["glint"]
                            .as_array()?
                            .iter()
                            .map(|v| v.as_f64().unwrap_or(0.0) as f32)
                            .collect();
                        let subject: Vec<bool> = m["subject"]
                            .as_array()?
                            .iter()
                            .map(|v| v.as_bool().unwrap_or(false))
                            .collect();
                        let n = cols * rows;
                        (level.len() == n && glint.len() == n && subject.len() == n).then_some(
                            live::LightMap {
                                level,
                                glint,
                                subject,
                                long_s: m["long_s"].as_f64()?,
                            },
                        )
                    })(),
                    still: None,
                });
            }
        }
        let p = f.peaks.as_ref()?;
        let (lo, hi) = p.range?;
        Some(live::DepthMap {
            revision,
            cols: p.cols,
            rows: p.rows,
            focus: p.focus.clone(),
            lo,
            hi,
            source: "from the live sweep, coarse",
            depth: measure::DEFAULT_DEPTH,
            extent: f.preview_size.map_or([1.0, 1.0], |[w, h]| {
                [
                    (p.cols * sweep::TILE) as f32 / w.max(1) as f32,
                    (p.rows * sweep::TILE) as f32 / h.max(1) as f32,
                ]
            }),
            anchor: f.busiest,
            light: None,
            still: None,
        })
    }
    /// The rail's bars from the calibration (spec 6.3): the survey's tiles
    /// in focus per frame, else the live sweep's kept peaks counted per
    /// sweep position; with the rail's caption.
    pub(crate) fn rail_samples(
        &self,
    ) -> Option<(Vec<crate::capture_client::host::SurveySample>, String)> {
        use crate::capture_client::host::SurveySample;
        let f = &self.pass.facts;
        if let Some(pp) = f
            .survey
            .as_ref()
            .and_then(|v| v["depth"]["per_position"].as_array())
            .filter(|a| !a.is_empty())
        {
            let samples = pp
                .iter()
                .filter_map(|p| {
                    let pos = p.get(0)?.as_f64()?;
                    let n = p.get(1)?.as_f64()?;
                    Some(SurveySample {
                        position: pos.round().clamp(0.0, 65535.0) as u16,
                        scores: vec![Some(n as f32)],
                    })
                })
                .collect();
            return Some((
                samples,
                "calibration: subject tiles in focus, from RAW".into(),
            ));
        }
        let p = f.peaks.as_ref()?;
        let (a, b) = p.window;
        let n = f.sweep_positions.max(2);
        let spacing = (b - a) / (n - 1) as f64;
        let mut counts = vec![0u32; n];
        for v in p.focus.iter().flatten() {
            let i = ((v - p.offset - a) / spacing).round();
            if i >= 0.0 && (i as usize) < n {
                counts[i as usize] += 1;
            }
        }
        let samples = counts
            .iter()
            .enumerate()
            .map(|(i, c)| SurveySample {
                position: (a + spacing * i as f64).round().clamp(0.0, 65535.0) as u16,
                scores: vec![Some(*c as f32)],
            })
            .collect();
        Some((
            samples,
            "calibration: tiles in focus, from the live sweep".into(),
        ))
    }
    /// The lens memory beside `capture.json` (spec 8).
    fn lens_memory_path(&self) -> PathBuf {
        self.path.with_file_name("capture-lens-memory.json")
    }
    /// How long the light has been on, as this desktop saw it.
    pub(crate) fn light_on_for(&self, now: Instant) -> Option<Duration> {
        self.light_on_since.map(|t| now.duration_since(t))
    }
    /// A run the desktop knows is not a stack: a test shot (by its
    /// manifest, or one this desktop took), a survey, or a sequence it
    /// stopped waiting for.
    pub(super) fn not_a_stack(&self, s: &Snapshot) -> bool {
        s.in_progress.as_ref().is_some_and(|r| r.test)
            || self.test_shot.running()
            || self.calibrating()
            || (self.unfollowed_sequence.is_some()
                && self.unfollowed_sequence == s.host.sequence_id
                && s.host.phase.capturing())
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
        // The light's time on, and the lens where the camera connected.
        match s.host.power.as_ref().and_then(|p| p.light.on) {
            Some(true) => {
                self.light_on_since.get_or_insert(now);
            }
            Some(false) => self.light_on_since = None,
            None => {}
        }
        if s.fresh() && s.host.connected {
            if self.connect_position.is_none() {
                self.connect_position = s.host.position;
            }
        } else if s.fresh() {
            self.connect_position = None;
        }
        if let Some((ratio, x, y)) = self.stillness.poll(&s, now) {
            // The magnifier as it was before the check.
            self.command(&s, Command::Magnify { ratio, x, y });
        }
        // Plan S2/S3: the survey's frames, and a selection found from them.
        self.survey_frames.observe(&s);
        self.auto_subject.poll();
        if let Some(subject) = self.auto_subject.take_unsent() {
            self.apply_live(&s, live::LiveIntent::SetSubject(Some(subject)));
        }
        // Plan X2: the highlight plan of a chosen advice, after its exposure.
        if self.pending_highlight.is_some()
            && s.fresh()
            && !s.pending
            && s.host.editable
            && s.host.capabilities.exposure_tiers
            && !s.host.phase.active()
        {
            let highlight = self.pending_highlight.take().flatten();
            self.command(&s, Command::Highlight { highlight });
        }
        // The subject's last outline, once the camera is ready for it.
        if self.pending_subject.is_some()
            && s.fresh()
            && !s.pending
            && s.host.editable
            && s.host.capabilities.subject
            && !s.host.phase.active()
        {
            let subject = self.pending_subject.take();
            self.command(&s, Command::Subject { subject });
        }
        let Some(connection) = &self.connection else {
            return;
        };
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
        self.poll_pass(&s, now);
        self.poll_proof(&s, now);
        // One filled value a frame, each once the camera is ready for it.
        if !self.fill_queue.is_empty()
            && s.fresh()
            && !s.pending
            && s.host.editable
            && !s.host.busy
            && self.station.mark_at.is_none()
            && self.station.mark_queue.is_empty()
            && self.pending_highlight.is_none()
            && let Some(intent) = self.fill_queue.pop_front()
        {
            self.apply_plan(&s, intent);
        }
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
            C::Restoring { result, .. } if gone && result["error"].is_string() => {
                C::Failed(format!(
                    "{}. The camera switched off before four-shot could be set again: set it when the camera is back",
                    result["error"].as_str().unwrap_or_default()
                ))
            }
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
                shutters,
                round,
                ..
            } if idle && shots == Some(1) => {
                let survey = shutters.is_some();
                let sequence = host.sequence_id.unwrap_or(0) + 1;
                // The dense cluster's step: the two-shutter survey takes
                // pairs at one position (owner, 2026-11-24: their gap of 0
                // made the second round a survey 1 unit apart).
                let spacing = if survey {
                    tools::SURVEY_SPACING
                } else {
                    positions
                        .windows(2)
                        .map(|w| w[0].abs_diff(w[1]))
                        .find(|d| *d > 0)
                        .unwrap_or(1)
                };
                match s
                    .request(Command::CapturePositions {
                        positions,
                        // "Manage power" would switch the camera off after the
                        // survey, before a second survey or four-shot is set again.
                        keep_power_on: true,
                        kind: PositionsKind::Positions,
                        shutters,
                    })
                    .and_then(|r| self.submit(r))
                {
                    Ok(()) => C::Capturing {
                        restore_four,
                        sequence,
                        round,
                        spacing,
                        survey,
                        // Twice the RAWs of a step survey and its long ones.
                        deadline: Self::survey_deadline(&s, now)
                            + if survey {
                                tools::SURVEY_TIMEOUT
                            } else {
                                Duration::ZERO
                            },
                    },
                    Err(e) => C::Failed(format!("{e:#}")),
                }
            }
            C::Capturing {
                restore_four,
                sequence,
                round,
                spacing,
                survey,
                deadline,
            } if host.sequence_id == Some(sequence) && !host.busy => match host.phase {
                HostPhase::Complete => {
                    let run = host.last_receipt_run();
                    match (run, &self.engine) {
                        (Some(run), Some(engine)) => {
                            let args = tools::measure_args(survey, &run);
                            match tools::EngineJob::start(engine, args) {
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
                    survey,
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
                            // `strehl survey` (plan X1): its step reads as
                            // `focus-step`'s, the whole survey kept beside it.
                            let v = if v["step"].is_object() && v["census"].is_object() {
                                json!({"width":v["step"]["width"],"suggested_step":v["step"]["suggested_step"],
                                    "summary":v["summary"],"survey":v})
                            } else {
                                v
                            };
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
                                        host.lens_travel.range(),
                                    ),
                                    shutters: None,
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
                                            sent: true,
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
            C::Restoring { result, .. } if idle && shots == Some(4) => {
                match result["error"].as_str() {
                    Some(why) => C::Failed(format!("{why}. Four-shot is set again")),
                    None => C::Done(result),
                }
            }
            C::Restoring {
                result,
                sent: false,
                deadline,
            } if idle => {
                match s
                    .request(Command::PixelShift { shots: 4 })
                    .and_then(|r| self.submit(r))
                {
                    Ok(()) => C::Restoring {
                        result,
                        sent: true,
                        deadline: deadline.max(now + tools::SWITCH_TIMEOUT),
                    },
                    Err(e) => C::Failed(format!(
                        "{}. Four-shot could not be set again ({e:#}): set it before the next stack",
                        result["error"].as_str().unwrap_or_default()
                    )),
                }
            }
            other => other,
        };
        // A calibration that switched the camera to one RAW a plane and then
        // failed or was stopped sets four-shot again before it reports
        // (owner, 2026-11-24). A survey still finishing on the host is waited
        // for; a camera that went away cannot be set.
        if self.restore_four_after_calibration {
            match &mut self.calibration {
                C::Failed(why) if host.connected => {
                    self.restore_four_after_calibration = false;
                    self.calibration = C::Restoring {
                        result: json!({"error": why.clone()}),
                        sent: false,
                        deadline: now + tools::SURVEY_TIMEOUT + tools::SWITCH_TIMEOUT,
                    };
                }
                C::Failed(why) => {
                    self.restore_four_after_calibration = false;
                    why.push_str(
                        ". The camera is off, so four-shot was not set again: set it before the next stack",
                    );
                }
                C::Done(_) | C::Restoring { .. } | C::Idle => {
                    self.restore_four_after_calibration = false;
                }
                _ => {}
            }
        }
        station::note_calibration(&mut self.station, stage_before, &self.calibration);
        // Plan X1/S2: the survey's precise outline (RAW frames) becomes the
        // subject when the plan has none.
        if stage_before != "done"
            && let C::Done(v) = &self.calibration
            && !self.pass.testing()
            && host.plan.as_ref().is_some_and(|p| p.subject.is_none())
            && let Some(subject) = survey_subject(&v["survey"]["subject"])
        {
            self.pending_subject = Some(subject);
        }
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
        // Plan X1: with a host that takes a shutter per position, one
        // survey at two shutters feeds the step, the subject and the
        // exposure advice; else the step survey alone.
        let two = s
            .host
            .exposure
            .as_ref()
            .filter(|_| s.host.capabilities.exposure_tiers)
            .and_then(|e| {
                let base = e.shutter?;
                let short = plan::shorter_shutter(&e.shutter_options, base, 4.0)?;
                (short != base).then_some((base, short))
            });
        let reach = s.host.lens_travel.range();
        let (positions, shutters) = match two {
            Some((base, short)) => {
                let (p, s) = tools::two_shutter_survey(start, end, base, short, reach);
                (p, Some(s))
            }
            None => (
                tools::survey_positions(
                    start,
                    end,
                    tools::SURVEY_SPACING,
                    tools::SURVEY_PLANES,
                    reach,
                ),
                None,
            ),
        };
        if restore_four {
            self.command(s, Command::PixelShift { shots: 1 });
        }
        self.restore_four_after_calibration = restore_four;
        self.calibration = tools::Calibration::Switching {
            restore_four,
            positions,
            shutters,
            round: 0,
            deadline: Instant::now() + tools::SWITCH_TIMEOUT,
        };
    }
    /// Stops waiting for the calibration at whatever stage it is in (see
    /// [`tools::Calibration::stop`]). A survey being captured is left to
    /// finish on the host and is not followed. A pass stops too: what it
    /// measured stays.
    pub fn stop_calibration(&mut self) {
        if let Some(sequence) = self.calibration.survey_sequence() {
            self.unfollowed_sequence = Some(sequence);
        }
        self.calibration.stop("Calibration stopped");
        self.pass.stop("Calibration stopped");
    }
    /// The calibration pass (spec 4), from the column's Calibrate button or
    /// the control interface's `calibrate`.
    pub fn calibrate_pass(&mut self) -> anyhow::Result<()> {
        self.calibrate_pass_at(None)
    }
    /// [`Self::calibrate_pass`] with the sweep centred on `at` when given.
    pub fn calibrate_pass_at(&mut self, at: Option<u16>) -> anyhow::Result<()> {
        let s = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .snapshot();
        anyhow::ensure!(!self.calibrating(), "A calibration is running");
        anyhow::ensure!(self.engine.is_some(), "The Strehl engine was not found");
        anyhow::ensure!(!self.test_shot.running(), "A test shot is running");
        anyhow::ensure!(
            s.fresh() && s.host.editable && !s.pending && s.host.connected,
            "The camera is not ready"
        );
        anyhow::ensure!(
            s.host.capabilities.exposure_tiers,
            "The camera host cannot take a shutter per position: update it"
        );
        let position = s
            .host
            .position
            .ok_or_else(|| anyhow::anyhow!("The lens position is not known"))?;
        let moved = self.connect_position.is_some_and(|p| p != position);
        // The marks, else the range the host still holds for this subject
        // (spec 4.1: after a power cycle the lens can stand tens of thousands
        // of units from the subject, and "New capture" clears only the marks).
        let marks = if s.host.bounds_set() {
            Some(s.host.plan_bounds())
        } else {
            s.host
                .plan
                .as_ref()
                .map(|p| (p.start, p.end))
                .filter(|(a, b)| a != b)
        };
        let seed = at.unwrap_or_else(|| measure::seed(position, moved, marks));
        let now = Instant::now();
        // Spec 8: what earlier calibrations measured at this lens position.
        let (w0, offset) =
            measure::LensMemory::load(&self.lens_memory_path()).seed(f64::from(seed));
        self.pass = measure::Pass {
            w0: w0.unwrap_or(measure::DEFAULT_DEPTH),
            offset,
            stage: measure::start_sweep(seed, s.host.lens_travel.range(), now),
            started: Some(now),
            exposure_before: s
                .host
                .exposure
                .as_ref()
                .and_then(|e| Some((e.iso?, e.shutter?))),
            four_before: s.host.shots_per_plane == Some(4),
            ..Default::default()
        };
        Ok(())
    }
    /// Advances the calibration pass (spec 4) once a frame. The test pair
    /// and the survey run on [`tools::Calibration`]; this watches it.
    fn poll_pass(&mut self, s: &Snapshot, now: Instant) {
        use measure::Stage as P;
        use tools::Calibration as C;
        if !self.pass.running()
            || !s.fresh()
            || self.connection.as_ref().is_some_and(Connection::is_fixture)
        {
            return;
        }
        if !s.host.connected && !s.host.busy {
            self.pass
                .stop("The camera switched off during the calibration");
            return;
        }
        let reach = s.host.lens_travel.range();
        let idle = !s.host.busy && s.host.editable && !s.pending;
        let stage = std::mem::replace(&mut self.pass.stage, P::Idle);
        self.pass.stage = match stage {
            P::Sweep { mut sweep, moved } => match sweep.poll(s, now) {
                sweep::Step::Move(target) => {
                    self.command(s, Command::Focus { target });
                    P::Sweep { sweep, moved }
                }
                sweep::Step::Wait => P::Sweep { sweep, moved },
                sweep::Step::Failed(why) => P::Failed(why),
                sweep::Step::Done => {
                    let w0 = self.pass.w0;
                    // Until this lens's coarse-to-fine offset is known: half a
                    // sharp depth (spec 5.3 point 6).
                    let offset = self.pass.offset.unwrap_or(w0 / 2.0);
                    match sweep::peaks(&sweep.frames, w0, offset) {
                        None => P::Failed("The sweep's frames could not be read".into()),
                        Some(p) if p.nothing() => {
                            let (a, b) = p.window;
                            self.pass.facts.peaks = Some(p);
                            P::Failed(format!(
                                "Nothing in focus between {} and {}: move the lens to the subject, or mark the range by hand",
                                style::focus_units(a as u16),
                                style::focus_units(b as u16)
                            ))
                        }
                        Some(p) => {
                            let off = p.off_end();
                            let (a, b) = p.window;
                            self.pass.facts.sweep_seconds =
                                Some(now.duration_since(sweep.started).as_secs_f64());
                            self.pass.facts.sweep_positions = sweep.positions.len();
                            self.pass.facts.busiest = p.busiest.map(|v| v.round() as u16);
                            self.pass.facts.preview_size = sweep.size;
                            self.pass.facts.peaks = Some(p);
                            self.pass.facts.revision += 1;
                            match off {
                                // Moved half its width that way, once (spec 4.1).
                                Some(dir) if !moved => {
                                    let seed = (0.5 * (a + b) + f64::from(dir) * 0.5 * (b - a))
                                        .clamp(0.0, 65535.0)
                                        as u16;
                                    P::Sweep {
                                        sweep: Box::new(sweep::Sweep::new(
                                            sweep::window(seed, reach),
                                            now,
                                        )),
                                        moved: true,
                                    }
                                }
                                Some(dir) => P::Failed(format!(
                                    "The subject is still in focus at the sweep's {} end, {}: move the lens past it and calibrate again",
                                    if dir > 0 { "far" } else { "near" },
                                    style::focus_units(if dir > 0 { b } else { a } as u16)
                                )),
                                None => P::Light { sent: false },
                            }
                        }
                    }
                }
            },
            P::Light { sent } => {
                let power = s.host.power.as_ref().filter(|p| p.available);
                let on = power.and_then(|p| p.light.on);
                if power.is_some() && on == Some(false) && !sent {
                    self.command(
                        s,
                        Command::Power {
                            device: strehl_capture::power::Outlet::Light,
                            on: true,
                        },
                    );
                    P::Light { sent: true }
                } else {
                    // Without studio outlets the light's state is not known.
                    let settled = power.is_none()
                        || self
                            .light_on_for(now)
                            .is_some_and(|d| d >= measure::LIGHT_SETTLED);
                    match (settled && idle, self.pass.facts.busiest) {
                        (true, Some(b)) => self.start_test_pair(s, b, now),
                        (true, None) => P::Failed("The sweep found no busiest position".into()),
                        _ => P::Light { sent },
                    }
                }
            }
            P::Test { position, shutters } => match &self.calibration {
                C::Done(v) => {
                    let survey = &v["survey"];
                    let top = survey["body"]["top"].as_f64();
                    self.pass.facts.test_top = top;
                    let options = s
                        .host
                        .exposure
                        .as_ref()
                        .map(|e| e.shutter_options.clone())
                        .unwrap_or_default();
                    let pair =
                        measure::survey_shutters(&options, shutters.0, top).unwrap_or(shutters);
                    self.start_survey(s, position, pair, now)
                }
                C::Failed(why) => P::Failed(format!("The test pair: {why}")),
                _ => P::Test { position, shutters },
            },
            P::Survey {
                shutters,
                positions,
            } => match &self.calibration {
                C::Done(v) => {
                    self.pass.facts.survey = Some(v["survey"].clone());
                    self.pass.facts.revision += 1;
                    // Spec 8: the sharp depth and the offset this pass measured,
                    // remembered at its lens position.
                    let survey = &v["survey"];
                    self.pass.offset_measured =
                        match (&self.pass.facts.peaks, self.pass.facts.preview_size) {
                            (Some(p), Some(size)) => {
                                let a = auto_subject::active_px(None).map(f64::from);
                                measure::measured_offset(p, size, &survey["maps"], a)
                            }
                            _ => None,
                        };
                    if let Some(b) = self.pass.facts.busiest {
                        let path = self.lens_memory_path();
                        let mut memory = measure::LensMemory::load(&path);
                        let unix = std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .map_or(0, |d| d.as_secs());
                        memory.record(
                            f64::from(b),
                            survey["step"]["width"].as_f64(),
                            self.pass.offset_measured,
                            unix,
                        );
                        let _ = memory.save(&path);
                    }
                    match self.pass.facts.busiest {
                        Some(b) => P::Return {
                            target: b,
                            exposure_sent: false,
                            moved: None,
                        },
                        None => P::Done,
                    }
                }
                C::Failed(why) => P::Failed(format!("The survey: {why}")),
                _ => P::Survey {
                    shutters,
                    positions,
                },
            },
            P::Return {
                target,
                exposure_sent,
                moved,
            } => {
                let current = s.host.exposure.as_ref().and_then(|e| e.iso.zip(e.shutter));
                let want = self.pass.exposure_before;
                if !exposure_sent && idle {
                    if let Some((iso, shutter)) = want.filter(|w| current != Some(*w)) {
                        self.command(s, Command::Exposure { iso, shutter });
                    }
                    P::Return {
                        target,
                        exposure_sent: true,
                        moved: None,
                    }
                } else if exposure_sent
                    && idle
                    && (want.is_none() || current == want)
                    && s.host.position != Some(target)
                    && moved.is_none_or(|t| now.duration_since(t) > Duration::from_secs(5))
                {
                    self.command(s, Command::Focus { target });
                    P::Return {
                        target,
                        exposure_sent,
                        moved: Some(now),
                    }
                } else if exposure_sent && idle && s.host.position == Some(target) {
                    self.pass.finished = Some(std::time::SystemTime::now());
                    // Rule 2: the calibration's values fill what the owner
                    // has not set.
                    if let Some(survey) = &self.pass.facts.survey {
                        let (intents, set, kept) = measure::fill(survey, self.held);
                        self.fill_queue.extend(intents);
                        self.pass.applied = Some((set, kept));
                        self.pass.facts.revision += 1;
                        // Spec 4 stage 6: one plane as the plan now stands.
                        self.pass.facts.proofs_wanted = self.pass.facts.proofs.len() + 1;
                    }
                    P::Done
                } else {
                    P::Return {
                        target,
                        exposure_sent,
                        moved,
                    }
                }
            }
            other => other,
        };
        if matches!(self.pass.stage, P::Failed(_)) && self.pass.stopped_in.is_none() {
            self.pass.stopped_in = Some("unknown");
        }
    }
    /// Asks for `n` proof planes (spec 5.8): taken one after another at the
    /// busiest position once the camera is ready.
    pub fn prove(&mut self, n: usize) -> anyhow::Result<()> {
        anyhow::ensure!(self.engine.is_some(), "The Strehl engine was not found");
        anyhow::ensure!(
            self.pass.facts.busiest.is_some(),
            "Calibrate first: the proof is taken at the busiest position"
        );
        anyhow::ensure!(!self.proof.running(), "A proof is running");
        self.pass.facts.proofs.clear();
        self.pass.facts.proofs_wanted = n.clamp(1, 10);
        Ok(())
    }
    /// Advances the proof plane: a test run of the base group, one of the
    /// highlight group when the plan has them, the base group checked by
    /// `strehl pixel-shift`; the runs deleted once read.
    fn poll_proof(&mut self, s: &Snapshot, now: Instant) {
        use measure::Proof as Q;
        if self.connection.as_ref().is_some_and(Connection::is_fixture) || !s.fresh() {
            return;
        }
        let host = &s.host;
        let idle = !host.busy && host.editable && !s.pending && !host.phase.capturing();
        let done = |seq: u64| {
            host.sequence_id == Some(seq) && !host.busy && host.phase == HostPhase::Complete
        };
        let failed = |seq: u64| {
            host.sequence_id == Some(seq)
                && !host.busy
                && matches!(
                    host.phase,
                    HostPhase::Stopped | HostPhase::Fault | HostPhase::Disconnected
                )
        };
        let test = |shutters: Option<Vec<u64>>, at: u16| Command::CapturePositions {
            positions: vec![at],
            keep_power_on: true,
            kind: PositionsKind::Test,
            shutters,
        };
        let state = std::mem::take(&mut self.proof);
        self.proof = match state {
            Q::Idle | Q::Failed(_)
                if self.pass.facts.proofs.len() < self.pass.facts.proofs_wanted
                    && idle
                    && !self.calibrating()
                    && self.fill_queue.is_empty()
                    && self.station.mark_at.is_none()
                    && self.station.mark_queue.is_empty()
                    && self.pending_highlight.is_none()
                    && host.shots_per_plane == Some(4) =>
            {
                let at = self.pass.facts.busiest.unwrap_or(0);
                let sequence = host.sequence_id.unwrap_or(0) + 1;
                if self.proof_retry.is_some_and(|t| now < t) {
                    Q::Idle
                } else {
                    match s.request(test(None, at)).and_then(|r| self.submit(r)) {
                        Ok(()) => {
                            self.proof_retry = None;
                            Q::Base {
                                sequence,
                                since: now,
                            }
                        }
                        // A request still in flight (the fill's last, on the
                        // rig 2026-11-27): try again shortly, a few times.
                        Err(e) => {
                            self.proof_tries += 1;
                            if self.proof_tries >= 10 {
                                self.proof_tries = 0;
                                self.pass.facts.proofs_wanted = self.pass.facts.proofs.len();
                            }
                            self.proof_retry = Some(now + Duration::from_secs(2));
                            Q::Failed(format!("{e:#}"))
                        }
                    }
                }
            }
            Q::Base { sequence, since } if done(sequence) => {
                let base_seconds = now.duration_since(since).as_secs_f64();
                match host.last_receipt_run() {
                    None => Q::Failed("The proof's folder was not reported".into()),
                    Some(base) => {
                        if let Some(c) = &self.connection {
                            c.mark_test_run(base.clone());
                        }
                        match host
                            .plan
                            .as_ref()
                            .and_then(|p| p.highlight)
                            .map(|h| h.shutter)
                        {
                            Some(h) => {
                                let at = self.pass.facts.busiest.unwrap_or(0);
                                let sequence = host.sequence_id.unwrap_or(0) + 1;
                                match s
                                    .request(test(Some(vec![h]), at))
                                    .and_then(|r| self.submit(r))
                                {
                                    Ok(()) => Q::Highlight {
                                        sequence,
                                        base,
                                        since: now,
                                        base_seconds,
                                    },
                                    Err(e) => Q::Failed(format!("{e:#}")),
                                }
                            }
                            None => self.check_proof(base, Vec::new(), base_seconds),
                        }
                    }
                }
            }
            Q::Highlight {
                sequence,
                base,
                since,
                base_seconds,
            } if done(sequence) => {
                let mut others = Vec::new();
                if let Some(run) = host.last_receipt_run() {
                    if let Some(c) = &self.connection {
                        c.mark_test_run(run.clone());
                    }
                    others.push(run);
                }
                // The camera keeps the highlight group's shutter: the plan's
                // base shutter goes back.
                if let (Some(iso), Some(shutter)) = (
                    host.exposure.as_ref().and_then(|e| e.iso),
                    self.proof_base_shutter,
                ) {
                    self.command(s, Command::Exposure { iso, shutter });
                }
                self.check_proof(
                    base,
                    others,
                    base_seconds + now.duration_since(since).as_secs_f64(),
                )
            }
            Q::Base { sequence, .. } | Q::Highlight { sequence, .. } if failed(sequence) => {
                self.pass.facts.proofs_wanted = self.pass.facts.proofs.len();
                Q::Failed("The proof plane did not finish".into())
            }
            Q::Checking {
                base,
                others,
                mut job,
                seconds,
            } => match job.poll() {
                None => Q::Checking {
                    base,
                    others,
                    job,
                    seconds,
                },
                Some(result) => {
                    for run in std::iter::once(&base).chain(&others) {
                        if run.join("manifest.json").is_file() && run.join("events.jsonl").is_file()
                        {
                            let _ = std::fs::remove_dir_all(run);
                        }
                    }
                    match result
                        .ok()
                        .and_then(|v| measure::ProofResult::from_report(&v, seconds))
                    {
                        Some(r) => {
                            self.pass.facts.proofs.push(r);
                            self.pass.facts.revision += 1;
                            Q::Idle
                        }
                        None => {
                            self.pass.facts.proofs_wanted = self.pass.facts.proofs.len();
                            Q::Failed("The proof's check could not be read".into())
                        }
                    }
                }
            },
            other => other,
        };
        if matches!(self.proof, Q::Base { .. }) && self.proof_base_shutter.is_none() {
            self.proof_base_shutter = host.exposure.as_ref().and_then(|e| e.shutter);
        }
        if matches!(self.proof, Q::Idle | Q::Failed(_)) {
            self.proof_base_shutter = None;
        }
    }
    fn check_proof(&mut self, base: PathBuf, others: Vec<PathBuf>, seconds: f64) -> measure::Proof {
        let Some(engine) = &self.engine else {
            return measure::Proof::Failed("The Strehl engine was not found".into());
        };
        match tools::EngineJob::start(
            engine,
            vec!["pixel-shift".into(), base.as_os_str().to_owned()],
        ) {
            Ok(job) => measure::Proof::Checking {
                base,
                others,
                job: Box::new(job),
                seconds,
            },
            Err(e) => measure::Proof::Failed(format!("{e:#}")),
        }
    }
    /// The test pair at the busiest position: the camera's shutter (at most
    /// 1.3 s) and five stops under, one RAW each.
    fn start_test_pair(&mut self, s: &Snapshot, at: u16, now: Instant) -> measure::Stage {
        let Some(e) = s.host.exposure.as_ref() else {
            return measure::Stage::Failed("The camera's exposure is not known".into());
        };
        let Some(pair) = e
            .shutter
            .and_then(|c| measure::test_shutters(&e.shutter_options, c))
        else {
            return measure::Stage::Failed("The camera's shutters are not known".into());
        };
        self.pass.facts.light_on_seconds = self.light_on_for(now).map(|d| d.as_secs_f64());
        if s.host.shots_per_plane == Some(4) {
            self.command(s, Command::PixelShift { shots: 1 });
        }
        self.restore_four_after_calibration = self.pass.four_before;
        // No second round: a pair at one position has no step to measure.
        self.calibration = tools::Calibration::Switching {
            restore_four: false,
            positions: vec![at, at],
            shutters: Some(vec![pair.0, pair.1]),
            round: 1,
            deadline: now + tools::SWITCH_TIMEOUT,
        };
        measure::Stage::Test {
            position: at,
            shutters: pair,
        }
    }
    /// The survey on the grid of spec 4.2 around the sweep's range.
    fn start_survey(
        &mut self,
        s: &Snapshot,
        busiest: u16,
        shutters: (u64, u64),
        now: Instant,
    ) -> measure::Stage {
        let Some((lo, hi)) = self.pass.facts.peaks.as_ref().and_then(|p| p.range) else {
            return measure::Stage::Failed("The sweep found no range".into());
        };
        let w0 = self.pass.w0;
        let (positions, codes) = measure::survey_grid(
            (lo, hi),
            f64::from(busiest),
            w0,
            shutters,
            s.host.lens_travel.range(),
        );
        self.pass.facts.shutters = Some(shutters);
        let n = positions.len();
        self.calibration = tools::Calibration::Switching {
            restore_four: self.pass.four_before,
            positions,
            shutters: Some(codes),
            round: 1,
            deadline: now + tools::SWITCH_TIMEOUT,
        };
        measure::Stage::Survey {
            shutters,
            positions: n,
        }
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
                "gives_up_seconds":self.calibration.gives_up_in(now).map(|d| d.as_secs_f64()),
                "pass":self.pass.public(),
                "proof":{"running":self.proof.running(),
                    "error":match &self.proof { measure::Proof::Failed(e) => Some(e.clone()), _ => None },
                    "results":self.pass.facts.proofs.iter().map(|p| json!({"verdict":p.verdict,"reason":p.reason,
                        "retake":p.retake,"local_px":p.local_px,"limit_px":p.limit_px,"residual_px":p.residual_px,
                        "seconds":p.seconds})).collect::<Vec<_>>(),
                    "line":measure::proof_line(&self.pass.facts.proofs)},
                "light_on_seconds":self.light_on_for(now).map(|d| d.as_secs_f64())},
            "focus_step":self.step_report.public(),
            "compact_estimate":self.compact_estimate.public(),
            "compact":self.compact_apply.public(),
            "test_shot":self.test_shot.public(now),
            "connect_wait":self.connect_wait.as_ref().map(|w| json!({"gives_up_seconds":w.gives_up_in(now).as_secs_f64()})),
            "connect_note":self.connect_note})
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
        let not_a_stack = self.not_a_stack(&s);
        let current = s.in_progress.as_ref().filter(|_| !not_a_stack);
        // Retakes after the capture ended (h-retake) go into its run: its
        // checker, finished with the capture, checks them too.
        let followup_run = s
            .host
            .retakes
            .as_ref()
            .filter(|r| r.followup.is_some() && capturing)
            .and_then(|r| r.run.clone());
        if let Some(name) = followup_run
            && self.follow_enabled
            && let Some(engine) = engine
        {
            let folder = self
                .follower
                .as_ref()
                .map(|f| f.run.clone())
                .into_iter()
                .chain(s.completed.iter().map(|c| c.folder.clone()))
                .chain(s.stopped.iter().map(|c| c.folder.clone()))
                .find(|f| f.file_name().and_then(|n| n.to_str()) == Some(name.as_str()));
            let idle = self.follower.as_ref().is_none_or(|f| !f.running());
            if let Some(folder) = folder
                && idle
                && self
                    .follow_refused
                    .as_ref()
                    .is_none_or(|(r, _)| *r != folder)
            {
                match follow::Follower::start(engine, &folder, Some(self.config.clone())) {
                    Ok(f) => {
                        // Its capture was offered once already.
                        let mut f = f;
                        f.offered = true;
                        self.follower = Some(f);
                    }
                    Err(e) => self.follow_refused = Some((folder, format!("{e:#}"))),
                }
            }
        }
        if let Some(f) = &mut self.follower {
            f.set_max_retakes(s.host.max_retakes() as usize);
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
    /// Start the next capture from this outline (plan S1: a new stack of a
    /// subject starts from its last outline).
    pub fn set_pending_subject(&mut self, subject: Option<strehl_capture::model::Subject>) {
        self.pending_subject = subject;
    }
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
            let mut receiver_path=crate::display_path::display_path(&self.config.receiver_config);
            if ui.add(egui::TextEdit::singleline(&mut receiver_path).desired_width(f32::INFINITY)).changed(){self.config.receiver_config=receiver_path.into();}
            if ui.add_enabled(!s.pending,egui::Button::new("Save connection")).clicked() {
                let result=self.config.normalize().and_then(|()|self.connection.as_ref().unwrap().configure(self.config.clone()));
                self.record(result);
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
            let left = self
                .time_left(&s)
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
                status.eta = self
                    .time_left(&s)
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
            shutters: None,
        })?;
        let sequence = s.host.sequence_id.unwrap_or(0) + 1;
        self.submit(request)?;
        self.test_shot_exposure = s.host.exposure.as_ref().and_then(|e| e.iso.zip(e.shutter));
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

/// The host's subject from `strehl survey`'s or `strehl subject`'s outline
/// JSON (rings, reference focus, ppm a focus unit, provenance), when valid.
pub(crate) fn survey_subject(v: &Value) -> Option<strehl_capture::model::Subject> {
    let rings: Vec<Vec<[f32; 2]>> = serde_json::from_value(v["rings"].clone()).ok()?;
    let subject = strehl_capture::model::Subject {
        rings,
        reference_focus: v["reference_focus"]
            .as_f64()
            .map(|f| f.round().clamp(0.0, 65535.0) as u16),
        rate_ppm: v["ppm_per_unit"].as_f64().map(|r| r as f32),
        provenance: json!({"kind":"auto","source":"raw survey","detail":v["provenance"].clone()}),
    };
    subject.validate().ok().map(|()| subject)
}

fn duration(seconds: Option<f64>) -> String {
    let Some(seconds) = seconds.filter(|s| s.is_finite() && *s >= 0.0) else {
        return "—".into();
    };
    let n = seconds.round() as u64;
    format!("{:02}:{:02}:{:02}", n / 3600, n / 60 % 60, n % 60)
}

#[cfg(test)]
#[path = "capture-workspace-tests.rs"]
mod station_tests;

#[cfg(test)]
mod tests {
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
}
