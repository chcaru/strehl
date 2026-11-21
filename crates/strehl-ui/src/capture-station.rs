//! The Capture station composed (Studio 2, 7.4): the pre-flight strip, the
//! canvas (live view, or the capture in flight), the focus rail, the
//! inspector (the plan, or the health column) and glance mode, each drawn
//! into the slot the shell gives it, with the user's intents applied to the
//! camera through the workspace's own checks.
//!
//! Calls for the shell, in its frame slots:
//! `station_strip`, `station_canvas`, `station_rail`, `station_inspector`,
//! and `station_glance` over the whole window while `glance_open()`;
//! `station_hints()` for the hint bar; `take_open_rig()` and
//! `take_show_plane()` for what belongs to the shell.
//! Until the shell is merged, `STREHL_CAPTURE_STATION=1` lays the station
//! out inside today's Capture tab (`show_station`).
use std::{
    path::PathBuf,
    sync::Arc,
    time::{Duration, Instant, SystemTime},
};

use eframe::egui::{self, Rect, TextureHandle, TextureOptions, Ui};
use strehl_capture::session::Command;

use super::{
    CaptureWorkspace, Confirm,
    flight::{self, FlightInputs, FlightIntent},
    glance::{self, GlanceInputs, Next},
    live::{LiveIntent, LiveView},
    plan::{CalibrationView, PlanInputs, PlanIntent, PlanView, Switches, TestShotView},
    preflight::{self, Fix},
    rail::{FlightTicks, FocusRail, RailInputs, RailIntent},
    style::CapturePalette,
    test_shot::TestShot,
    tools::Calibration,
};
use crate::capture_client::{Connection, Snapshot};
use crate::draft_preview::{ProofEvent, ProofJob, ProofUpdate};

/// What the flight ticks depend on: the plan, the counts and the
/// checker's published progress.
type TicksKey = ((u16, u16, u16), (u64, Option<u64>, u64), Option<usize>);

/// How long a dragged bound may take to be reached and marked.
const MARK_AT_TIMEOUT: Duration = Duration::from_secs(20);

/// The proof of the capture being written.
struct ProofState {
    run: PathBuf,
    job: ProofJob,
    latest: Option<Box<ProofUpdate>>,
    texture: Option<(u64, TextureHandle)>,
    error: Option<String>,
}

/// A dragged bound: focus moves there, then it is marked.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct MarkAt {
    pub start: bool,
    pub to: u16,
    pub since: Instant,
}

/// A plane's RAW shown in the canvas ("Show" on a retaken plane).
pub(crate) struct PinnedPlane {
    pub plane: u64,
    task: Option<crate::jobs::Task<crate::preview::PreviewImage>>,
    texture: Option<TextureHandle>,
    error: Option<String>,
}

/// The station's views and their state.
#[derive(Default)]
pub(crate) struct Station {
    pub palette: CapturePalette,
    pub plan: PlanView,
    rail: FocusRail,
    pub live: LiveView,
    pub glance: bool,
    proof: Option<ProofState>,
    pub mark_at: Option<MarkAt>,
    /// The flight rail's ticks and what they were built from.
    ticks: Option<(TicksKey, Arc<FlightTicks>)>,
    rig_requested: bool,
    show_plane: Option<u64>,
    pub calibrated_at: Option<SystemTime>,
    recover_open: bool,
    settings_open: bool,
    /// The catalog's subjects, for the plan's subject field, and the
    /// catalog revision they were read at.
    subjects: Vec<String>,
    subjects_revision: Option<u64>,
    /// The names the plan gave captures, by run folder (newest last).
    named_runs: std::collections::VecDeque<(PathBuf, String, String)>,
    /// A plane's RAW in the canvas, until dismissed.
    pinned: Option<PinnedPlane>,
    /// The checker's journal of a fixture (`--capture-fixture`).
    fixture_progress: Option<Arc<super::follow::Progress>>,
}

/// Which screen the station shows.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum StationMode {
    Plan,
    Flight,
}

/// The hint bar's keys and its right-hand note.
#[allow(dead_code)]
pub(crate) struct StationHints {
    pub keys: Vec<(&'static str, &'static str)>,
    pub note: String,
}

impl CaptureWorkspace {
    fn station_snapshot(&self) -> Snapshot {
        self.connection
            .as_ref()
            .map(Connection::snapshot)
            .unwrap_or_default()
    }

    /// The palette the screens draw with (the shell's tokens).
    pub fn set_palette(&mut self, palette: CapturePalette) {
        self.station.palette = palette;
    }

    /// The catalog's subject names, offered by the plan's subject field.
    pub fn set_subjects(&mut self, subjects: Vec<String>) {
        self.station.subjects = subjects;
    }

    /// Whether the subject names were read before catalog `revision`;
    /// records it as read.
    pub fn subjects_stale(&mut self, revision: u64) -> bool {
        let stale = self.station.subjects_revision != Some(revision);
        self.station.subjects_revision = Some(revision);
        stale
    }

    /// Records the plan's names for the capture in `run` (the newest 16).
    pub(crate) fn remember_names(&mut self, run: PathBuf, subject: String, stack: String) {
        self.station.named_runs.push_back((run, subject, stack));
        if self.station.named_runs.len() > 16 {
            self.station.named_runs.pop_front();
        }
    }

    /// The rail's mesh builds and the live view's texture uploads so far
    /// (performance checks: pointer motion must not add to either).
    #[allow(dead_code)]
    pub(crate) fn station_counters(&self) -> (u64, u64) {
        (self.station.rail.rebuilds, self.station.live.uploads)
    }

    /// The plan's subject and stack names as typed (the shell's breadcrumb).
    pub fn plan_names(&self) -> (&str, &str) {
        (
            self.station.plan.subject.trim(),
            self.station.plan.stack_name.trim(),
        )
    }

    /// A new stack asked for from a subject in the Library: the plan names
    /// that subject.
    pub fn set_plan_subject(&mut self, subject: &str) {
        self.station.plan.subject = subject.to_owned();
    }

    /// The subject and stack name the plan gave the capture in `run`.
    pub fn names_for(&self, run: &std::path::Path) -> Option<(String, String)> {
        self.station
            .named_runs
            .iter()
            .rev()
            .find(|(r, _, _)| r == run)
            .map(|(_, subject, stack)| (subject.clone(), stack.clone()))
    }

    /// The checker's progress: the follower's, or a fixture's.
    pub(crate) fn station_progress(&self) -> Option<Arc<super::follow::Progress>> {
        self.follower
            .as_ref()
            .map(|f| f.progress_arc())
            .or_else(|| self.station.fixture_progress.clone())
    }

    /// The RAW file of `plane` in the run being (or last) followed: its
    /// first member, as stored on this PC.
    pub fn plane_raw(&self, plane: u64) -> Option<PathBuf> {
        let progress = self.station_progress()?;
        let name = progress.plane(plane)?["names"][0].as_str()?.to_owned();
        let run = self.follower.as_ref().map(|f| f.run.clone())?;
        [format!("{name}.straw"), name]
            .into_iter()
            .map(|n| run.join(n))
            .find(|p| p.is_file())
    }

    /// Shows `path` (a plane's RAW) in the canvas until dismissed: its camera
    /// preview, read on a worker.
    pub fn show_plane_raw(&mut self, plane: u64, path: PathBuf) {
        let task = crate::jobs::spawn_task("strehl-capture-plane", move |cancelled| {
            crate::source_preview::load_draft_source(&path, 1920, &cancelled)
        });
        self.station.pinned = Some(PinnedPlane {
            plane,
            task: Some(task),
            texture: None,
            error: None,
        });
    }

    /// Loads a fixture (`--capture-fixture plan|flight|glance`): the
    /// station shows it from a connection that sends nothing.
    pub fn load_fixture(&mut self, name: &str) -> anyhow::Result<()> {
        use super::fixture::{self, Fixture};
        // `plan+rig`, `plan+guide`, `plan+schedule`...: a plan with a panel open.
        let (name, open) = name.split_once('+').unwrap_or((name, ""));
        let which = Fixture::parse(name)
            .ok_or_else(|| anyhow::anyhow!("Use --capture-fixture plan, flight or glance"))?;
        self.connection = Some(Connection::fixture(fixture::snapshot(which)));
        self.station.plan.subject = "Blue weevil".into();
        self.station.plan.stack_name = "Dorsal · 2.8×".into();
        self.test_shot = TestShot::Done {
            folder: PathBuf::from("fixture"),
            levels: fixture::test_levels(),
            taken: fixture::earlier(16),
        };
        self.calibration = Calibration::Done(serde_json::json!({"width":50.0,"suggested_step":7,
            "summary":"Detail stays sharp over about 50 focus units."}));
        self.station.calibrated_at = Some(fixture::earlier(14));
        self.test_shot_exposure = Some((100, 65544));
        self.open_fixture_panel(open);
        if which != Fixture::Plan {
            self.station.fixture_progress = Some(Arc::new(fixture::progress()));
            let image = fixture::subject_image(960, 640, 0.8);
            let rgba = image.pixels.iter().flat_map(|p| p.to_array()).collect();
            let update = ProofUpdate {
                draft: crate::draft_preview::DraftPreview {
                    image: crate::preview::PreviewImage {
                        path: PathBuf::from("fixture"),
                        source_size: [960, 640],
                        size: [960, 640],
                        rgba,
                        is_overview: true,
                    },
                    source_frames: 61,
                    aligned_frames: 61,
                    skipped_frames: 0,
                    alignment_edges: 0,
                    cycle_rank: 0,
                    reference_frame: 30,
                    warnings: Vec::new(),
                },
                received: 61,
                used: 61,
                stride: 1,
                revision: 1,
            };
            self.station.proof = Some(ProofState {
                run: PathBuf::from("fixture"),
                job: ProofJob::start(),
                latest: Some(Box::new(update)),
                texture: None,
                error: None,
            });
        }
        self.station.glance = which == Fixture::Glance;
        Ok(())
    }

    /// Plan, or flight while a capture runs or is paused.
    pub fn station_mode(&self) -> StationMode {
        if self.station_snapshot().host.phase.capturing()
            && !self.calibrating()
            && !self.test_shot.running()
        {
            StationMode::Flight
        } else {
            StationMode::Plan
        }
    }

    /// Glance mode is open (it covers the window).
    #[allow(dead_code)]
    pub fn glance_open(&self) -> bool {
        self.station.glance
    }

    /// Opens glance mode (the shell's `G`, or the stage-1 preview).
    #[allow(dead_code)]
    pub fn open_glance(&mut self) {
        self.station.glance = true;
    }

    /// The shell's rig popover was asked for from the plan.
    #[allow(dead_code)]
    pub fn take_open_rig(&mut self) -> bool {
        std::mem::take(&mut self.station.rig_requested)
    }

    /// A plane the user asked to see (a retaken one, from "Last planes").
    #[allow(dead_code)]
    pub fn take_show_plane(&mut self) -> Option<u64> {
        self.station.show_plane.take()
    }

    /// The keys the station answers, for the hint bar.
    #[allow(dead_code)]
    pub fn station_hints(&self) -> StationHints {
        let s = self.station_snapshot();
        let note = if s.fresh() {
            let receiver = if s.receiver["ok"] == true {
                "receiver ready"
            } else {
                "receiver not ready"
            };
            match s.receiver["folder"].as_str().filter(|f| !f.is_empty()) {
                Some(folder) => format!("Camera host online · {receiver} · {folder}"),
                None => format!("Camera host online · {receiver}"),
            }
        } else {
            "Camera host offline".into()
        };
        match self.station_mode() {
            StationMode::Plan => StationHints {
                keys: vec![
                    ("←→", "focus by 1"),
                    ("Shift", "by 16"),
                    ("S", "mark start"),
                    ("E", "mark end"),
                    ("T", "test shot"),
                    ("Enter", "start"),
                ],
                note,
            },
            StationMode::Flight => StationHints {
                keys: vec![("Space", "pause"), ("G", "glance mode")],
                note: "Stop asks first, and keeps the planes already taken".into(),
            },
        }
    }

    /// Advances the proof and a dragged bound; called with the other polls.
    pub(super) fn poll_station(&mut self, s: &Snapshot) {
        // The lens and the plan as the host holds them, before painting.
        self.observe_focus(s);
        if let Some(plan) = s.host.plan.clone() {
            self.sync_plan(plan, s.host.plan_revision.unwrap_or(0));
        }
        // The proof follows the capture being written (not a test shot).
        if let Some(run) = s
            .in_progress
            .as_ref()
            .filter(|r| !r.test && s.host.phase.capturing())
            && self
                .station
                .proof
                .as_ref()
                .is_none_or(|p| p.run != run.folder)
        {
            self.station.proof = Some(ProofState {
                run: run.folder.clone(),
                job: ProofJob::for_run(run.folder.clone(), s.host.shots()),
                latest: None,
                texture: None,
                error: None,
            });
        }
        if let Some(run) = s
            .in_progress
            .as_ref()
            .filter(|r| !r.test && s.host.phase.capturing())
            && !self
                .station
                .named_runs
                .iter()
                .any(|(r, _, _)| *r == run.folder)
        {
            let (subject, stack) = (
                self.station.plan.subject.trim().to_owned(),
                self.station.plan.stack_name.trim().to_owned(),
            );
            if !subject.is_empty() || !stack.is_empty() {
                let folder = run.folder.clone();
                self.remember_names(folder, subject, stack);
            }
        }
        if let Some(proof) = &mut self.station.proof {
            match proof.job.poll() {
                Some(ProofEvent::Updated(update)) => {
                    proof.latest = Some(update);
                    proof.error = None;
                }
                Some(ProofEvent::Failed(e)) => proof.error = Some(e),
                None => {}
            }
        }
        // A dragged bound: once the lens is there and the camera idle, mark.
        if let Some(at) = self.station.mark_at {
            let host = &s.host;
            if at.since.elapsed() > MARK_AT_TIMEOUT || !s.fresh() {
                self.station.mark_at = None;
                self.error = Some("The bound was not reached; it was not marked".into());
            } else if host.position == Some(at.to)
                && host.editable
                && !s.pending
                && self.focus_pending.is_none()
                && self.focus_flight.is_none()
            {
                self.station.mark_at = None;
                self.command(s, Command::Mark { start: at.start });
            }
        }
    }

    fn proof_texture(
        &mut self,
        ctx: &egui::Context,
    ) -> Option<(egui::TextureId, egui::Vec2, String)> {
        let proof = self.station.proof.as_mut()?;
        let update = proof.latest.as_ref()?;
        if proof
            .texture
            .as_ref()
            .is_none_or(|(r, _)| *r != update.revision)
        {
            let image = &update.draft.image;
            let color = egui::ColorImage::from_rgba_unmultiplied(image.size, &image.rgba);
            match &mut proof.texture {
                Some((r, t)) => {
                    t.set(color, TextureOptions::LINEAR);
                    *r = update.revision;
                }
                None => {
                    proof.texture = Some((
                        update.revision,
                        ctx.load_texture("capture-proof", color, TextureOptions::LINEAR),
                    ))
                }
            }
        }
        let (_, t) = proof.texture.as_ref()?;
        Some((
            t.id(),
            t.size_vec2(),
            format!("planes 1–{}", update.received),
        ))
    }

    /// The pre-flight strip, in the control strip's slot.
    pub fn station_strip(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let blockers = preflight::start_blockers(&s, self);
        let chips = preflight::strip_chips(&s, &blockers);
        let rows = super::plan::step_rows(
            &s,
            s.host.plan.as_ref().map_or(1, |p| p.step),
            s.host.plan.as_ref().map_or(500, |p| p.settle_ms),
            &self.calibration_result(),
        );
        let summary = super::plan::strip_summary(&s, &rows);
        let palette = self.station.palette;
        if let Some(fix) = preflight::strip_ui(ui, &chips, &blockers, &summary, &palette) {
            self.apply_fix(&s, fix);
        }
    }

    fn calibration_result(&self) -> serde_json::Value {
        match &self.calibration {
            Calibration::Done(v) | Calibration::Restoring { result: v, .. } => v.clone(),
            Calibration::Failed(e) => serde_json::json!({"error":e}),
            _ => serde_json::Value::Null,
        }
    }

    /// The canvas: the live view while planning, the capture in flight.
    pub fn station_canvas(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let palette = self.station.palette;
        self.shown = true;
        // An offscreen screenshot waits for the state that was drawn.
        self.painted_ready = (!s.receiver.is_null() || s.receiver_error.is_some())
            && ((s.observed.is_some() && (s.preview.is_some() || !s.host.preview.available))
                || s.connection_error.is_some()
                || self.config.controller.is_empty());
        self.station_canvas_body(ui, &s, &palette);
        // A focus target from the rail or a dragged bound goes out once the
        // camera is free (the canvas is the station's last slot).
        self.flush_focus(&s);
    }

    fn station_canvas_body(&mut self, ui: &mut Ui, s: &Snapshot, palette: &CapturePalette) {
        let palette = palette.on_canvas();
        if self.station.pinned.is_some() {
            self.pinned_canvas(ui, &palette);
            return;
        }
        match self.station_mode() {
            StationMode::Plan => {
                let intents = self.station.live.show(ui, s, &palette);
                for intent in intents {
                    self.apply_live(s, intent);
                }
            }
            StationMode::Flight => {
                let proof = self.proof_texture(ui.ctx());
                self.station.live.sync_textures(ui.ctx(), s, &palette);
                let latest = self.station.live.preview_texture();
                let progress = self.station_progress();
                let inputs = FlightInputs {
                    s,
                    progress: progress.as_deref(),
                    checking: self.follow_enabled,
                    proof,
                    latest,
                    stack_when_done: self.stack_when_done,
                    power_down: s.host.power.as_ref().map(|p| p.manage_stack),
                    confirm_stop: self.confirm == Some(Confirm::Stop),
                };
                let intents = flight::canvas(ui, &inputs, &palette);
                for intent in intents {
                    self.apply_flight(s, intent);
                }
            }
        }
    }

    /// A plane's RAW in the canvas, with the way back to the live view.
    fn pinned_canvas(&mut self, ui: &mut Ui, palette: &CapturePalette) {
        let rect = ui.max_rect();
        ui.painter().rect_filled(rect, 0.0, palette.surround);
        let Some(pinned) = &mut self.station.pinned else {
            return;
        };
        if let Some(task) = &pinned.task
            && let Ok(result) = task.receiver.try_recv()
        {
            pinned.task = None;
            match result {
                Ok(image) => {
                    let color = egui::ColorImage::from_rgba_unmultiplied(image.size, &image.rgba);
                    pinned.texture = Some(ui.ctx().load_texture(
                        "capture-plane-raw",
                        color,
                        TextureOptions::LINEAR,
                    ));
                }
                Err(e) => pinned.error = Some(e),
            }
        }
        let photo = super::live::photo_rect(rect, 1.5);
        let p = ui.painter();
        p.rect_filled(photo, 0.0, egui::Color32::BLACK);
        if let Some(t) = &pinned.texture {
            let size = t.size_vec2();
            let scale = (photo.width() / size.x).min(photo.height() / size.y);
            p.image(
                t.id(),
                Rect::from_center_size(photo.center(), size * scale),
                Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                egui::Color32::WHITE,
            );
        } else if pinned.task.is_some() {
            ui.ctx().request_repaint_after(Duration::from_millis(100));
        }
        let caption = match &pinned.error {
            Some(e) => format!("Plane {} · {e}", pinned.plane),
            None => format!(
                "Plane {} · from its RAW's camera preview, not the RAW stack",
                pinned.plane
            ),
        };
        super::style::paint_job(
            p,
            photo.left_top() - egui::vec2(0.0, 8.0),
            egui::Align2::LEFT_BOTTOM,
            super::style::caps_job(&caption, 10.5, palette.ink2),
        );
        let back = Rect::from_min_size(
            photo.right_top() + egui::vec2(-130.0, -30.0),
            egui::vec2(130.0, 24.0),
        );
        let mut close = false;
        ui.scope_builder(egui::UiBuilder::new().max_rect(back), |ui| {
            close = super::style::button_sized(
                ui,
                "Back to the capture",
                super::style::ButtonKind::Plain,
                back.size(),
                true,
                palette,
            )
            .clicked();
        });
        if close || ui.input(|i| i.key_pressed(egui::Key::Escape)) {
            self.station.pinned = None;
        }
    }

    /// Glance mode, drawn over the whole window (top bar and hint bar
    /// included), as the mockup's bare screen.
    pub fn station_glance_overlay(&mut self, ctx: &egui::Context) {
        let screen = ctx.content_rect();
        egui::Area::new(egui::Id::new("capture-glance"))
            .order(egui::Order::Foreground)
            .fixed_pos(screen.min)
            .show(ctx, |ui| {
                ui.set_min_size(screen.size());
                let mut child = ui.new_child(egui::UiBuilder::new().max_rect(screen));
                self.station_glance(&mut child);
            });
    }

    /// The focus rail, in the rail's slot.
    pub fn station_rail(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let host = &s.host;
        let palette = self.station.palette;
        let flight_mode = self.station_mode() == StationMode::Flight;
        let (start, end) = host.plan_bounds();
        let progress = self.station_progress();
        let ticks = flight_mode.then(|| {
            let step = host.plan.as_ref().map_or(1, |p| p.step);
            // Rebuilt only when a plane's state can have changed.
            let key = (
                (start, end, step),
                (host.completed, host.storage.saved_frames, host.shots()),
                progress.as_ref().map(|p| Arc::as_ptr(p) as usize),
            );
            if self.station.ticks.as_ref().is_none_or(|(k, _)| *k != key) {
                let revision = self.station.ticks.as_ref().map_or(0, |(_, t)| t.revision) + 1;
                let mut ticks = flight::flight_ticks(
                    super::rail::planned(start, end, step),
                    &s,
                    progress.as_deref(),
                );
                ticks.revision = revision;
                self.station.ticks = Some((key, Arc::new(ticks)));
            }
            self.station.ticks.as_ref().map(|(_, t)| t.clone()).unwrap()
        });
        let survey =
            (!host.samples.is_empty()).then(|| "survey: where the subject is sharp".to_owned());
        let inputs = RailInputs {
            samples: &host.samples,
            start: host.start_set.then_some(start),
            end: host.end_set.then_some(end),
            step: host.plan.as_ref().map_or(1, |p| p.step),
            lens: self.focus_pending.or(host.position),
            flight: ticks.as_deref(),
            survey,
            can_use_survey: host.suggestion.as_ref().is_some_and(|s| !s.clipped),
            editable: s.fresh() && host.editable && !s.pending && self.focus_flight.is_none(),
            keys: !self.station.glance && !self.schedule_ui.editing(),
        };
        let intents = self.station.rail.show(ui, &inputs, &palette);
        for intent in intents {
            self.apply_rail(&s, intent);
        }
    }

    /// The inspector: the plan, or the capture's health while it runs.
    pub fn station_inspector(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let palette = self.station.palette;
        match self.station_mode() {
            StationMode::Plan => {
                let blockers = preflight::start_blockers(&s, self);
                let now = Instant::now();
                let (stage, levels, taken, error) = match &self.test_shot {
                    TestShot::Done { levels, taken, .. } => {
                        ("done", Some(levels.clone()), Some(*taken), None)
                    }
                    TestShot::Failed(e) => ("failed", None, None, Some(e.clone())),
                    other => (other.stage(), None, None, None),
                };
                let inputs = PlanInputs {
                    s: &s,
                    blockers: &blockers,
                    step: self.draft.step,
                    settle_ms: self.draft.settle_ms,
                    calibration: CalibrationView {
                        stage: self.calibration.stage(),
                        gives_up_in: self.calibration.gives_up_in(now),
                        result: self.calibration_result(),
                        finished: self.station.calibrated_at,
                    },
                    test_shot: TestShotView {
                        stage,
                        levels,
                        exposure: self.test_shot_exposure,
                        taken,
                        error,
                    },
                    switches: Switches {
                        check: self.follow_enabled,
                        retake: s.host.error_correction,
                        stack_when_done: self.stack_when_done,
                        power_down: s.host.power.as_ref().map(|p| p.manage_stack),
                    },
                    engine: self.engine.is_some(),
                    subjects: &self.station.subjects,
                };
                let mut intents = self.station.plan.show(ui, &inputs, &palette);
                // The comparison panel ("What changes"), left of the inspector.
                if let Some(mut tab) = self.station.plan.guide {
                    let guide_inputs = super::guide::GuideInputs {
                        s: &s,
                        step: inputs.step,
                        settle_ms: inputs.settle_ms,
                        calibration: &inputs.calibration,
                        test_shot: &inputs.test_shot,
                        editable: s.fresh() && s.host.editable && !s.pending,
                    };
                    let (chosen, close) = super::guide::show_panel(
                        ui.ctx(),
                        ui.max_rect(),
                        &mut tab,
                        &guide_inputs,
                        &palette,
                    );
                    intents.extend(chosen);
                    self.station.plan.guide = (!close).then_some(tab);
                }
                // T takes a test shot; Enter starts a ready plan.
                if !ui.ctx().wants_keyboard_input()
                    && !self.station.glance
                    && !self.schedule_ui.editing()
                {
                    ui.input(|i| {
                        if i.key_pressed(egui::Key::T) {
                            intents.push(PlanIntent::TestShot);
                        }
                        if i.key_pressed(egui::Key::Enter) && blockers.is_empty() {
                            intents.push(PlanIntent::Start);
                        }
                    });
                }
                for intent in intents {
                    self.apply_plan(&s, intent);
                }
            }
            StationMode::Flight => {
                let progress = self.station_progress();
                let inputs = FlightInputs {
                    s: &s,
                    progress: progress.as_deref(),
                    checking: self.follow_enabled,
                    proof: None,
                    latest: None,
                    stack_when_done: self.stack_when_done,
                    power_down: s.host.power.as_ref().map(|p| p.manage_stack),
                    confirm_stop: self.confirm == Some(Confirm::Stop),
                };
                let intents = flight::inspector(ui, &inputs, &palette);
                for intent in intents {
                    self.apply_flight(&s, intent);
                }
            }
        }
        self.station_windows(ui.ctx(), &s);
    }

    /// Glance mode over the whole window; Escape returns.
    pub fn station_glance(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let palette = self.station.palette;
        let proof = self.proof_texture(ui.ctx()).map(|(id, size, _)| (id, size));
        let progress = self.station_progress();
        let received = self
            .station
            .proof
            .as_ref()
            .and_then(|p| p.latest.as_ref())
            .map(|u| u.received);
        let caption = [
            self.station.plan.subject.clone(),
            self.station.plan.stack_name.clone(),
            received
                .map(|n| format!("proof from planes 1–{n}"))
                .unwrap_or_default(),
        ]
        .into_iter()
        .filter(|t| !t.is_empty())
        .collect::<Vec<_>>()
        .join(" · ");
        let inputs = GlanceInputs {
            s: &s,
            progress: progress.as_deref(),
            proof,
            caption,
            next: Next {
                stack: self.follow_enabled && self.stack_when_done,
                power_down: s.host.power.as_ref().is_some_and(|p| p.manage_stack),
            },
        };
        if glance::show(ui, &inputs, &palette) {
            self.station.glance = false;
        }
    }

    /// Recovery and connection settings, opened from a pre-flight fix.
    fn station_windows(&mut self, ctx: &egui::Context, s: &Snapshot) {
        if self.station.recover_open {
            let mut open = true;
            egui::Window::new("Recover the camera")
                .open(&mut open)
                .collapsible(false)
                .resizable(false)
                .show(ctx, |ui| {
                    let failure = s.host.failure.clone();
                    ui.label(
                        failure
                            .as_ref()
                            .and_then(|f| f.message.clone())
                            .unwrap_or_else(|| "The camera needs recovery".into()),
                    );
                    let uncertain = failure.as_ref().is_some_and(|f| f.exposure_uncertain);
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
                        self.station.recover_open = false;
                    }
                });
            self.station.recover_open &= open && s.host.failure.is_some();
        }
        if self.station.settings_open {
            let mut open = true;
            egui::Window::new("Captures, storage and connection")
                .open(&mut open)
                .collapsible(false)
                .default_width(360.0)
                .show(ctx, |ui| {
                    egui::ScrollArea::vertical()
                        .max_height(620.0)
                        .show(ui, |ui| {
                            self.connection_ui(ui, s);
                            ui.separator();
                            self.storage_ui(ui, s);
                            ui.separator();
                            self.completed_ui(ui, s, true);
                        });
                });
            self.station.settings_open &= open;
        }
        self.phone_ui(ctx);
        if self.schedule_ui.editing() {
            let blockers = preflight::start_blockers(s, self);
            let timing = self.schedule_timing(s);
            let palette = self.station.palette;
            if let Some(cmd) =
                self.schedule_ui
                    .show(ctx, s, preflight::can_schedule(&blockers), timing, &palette)
            {
                self.command(s, cmd);
            }
        }
    }

    fn apply_fix(&mut self, s: &Snapshot, fix: Fix) {
        match fix {
            Fix::ConnectionSettings => self.station.settings_open = true,
            Fix::ConnectCamera => self.connect_camera(s, Command::Connect {}),
            Fix::RecoverCamera => self.station.recover_open = true,
            Fix::MarkStart => self.command(s, Command::Mark { start: true }),
            Fix::MarkEnd => self.command(s, Command::Mark { start: false }),
            Fix::ApplyEdits => self.send_settings(s, self.draft.step, self.draft.settle_ms),
            Fix::StartReceiver => {
                let result = self.start_receiver();
                self.record(result);
            }
            Fix::StopWaiting => {
                if self.calibrating() {
                    self.stop_calibration();
                }
                if self.test_shot.running() {
                    self.stop_test_shot();
                }
            }
        }
    }

    /// Sends the plan's step and settle as the host's `settings` command.
    fn send_settings(&mut self, s: &Snapshot, step: u16, settle_ms: u32) {
        self.send_plan(s, step, settle_ms, None, None);
    }

    /// The host's `settings` command with the plan's step and settle, and
    /// its approach and exposure timeout unless given.
    fn send_plan(
        &mut self,
        s: &Snapshot,
        step: u16,
        settle_ms: u32,
        approach: Option<u16>,
        capture_timeout_s: Option<u32>,
    ) {
        let Some(plan) = s.host.plan.clone() else {
            return;
        };
        let command = Command::Settings {
            step: step.max(1),
            settle_ms,
            approach: approach.unwrap_or(plan.approach),
            capture_timeout_s: capture_timeout_s.unwrap_or(plan.capture_timeout_s),
        };
        let revision = s.host.plan_revision.unwrap_or(0);
        let result = s.request(command).and_then(|mut r| {
            r.plan_revision = revision;
            self.submit(r)
        });
        if result.is_ok() {
            self.draft.step = step.max(1);
            self.draft.settle_ms = settle_ms;
            self.draft_dirty = false;
        }
        self.record(result);
    }

    pub(super) fn apply_plan(&mut self, s: &Snapshot, intent: PlanIntent) {
        match intent {
            PlanIntent::SetSubject(_) | PlanIntent::SetStackName(_) => {}
            PlanIntent::OpenRig => self.station.rig_requested = true,
            PlanIntent::Connect => self.connect_camera(s, Command::Connect {}),
            PlanIntent::Exposure { iso, shutter } => {
                self.command(s, Command::Exposure { iso, shutter })
            }
            PlanIntent::TestShot => {
                if !self.test_shot.running() && !self.calibrating() {
                    let result = self.test_shot();
                    self.record(result);
                }
            }
            PlanIntent::StopTestShot => self.stop_test_shot(),
            PlanIntent::MarkStart => self.command(s, Command::Mark { start: true }),
            PlanIntent::MarkEnd => self.command(s, Command::Mark { start: false }),
            PlanIntent::Calibrate => {
                let result = self.calibrate();
                self.record(result);
            }
            PlanIntent::StopCalibration => self.stop_calibration(),
            PlanIntent::SetStep(step) => self.send_settings(s, step, self.draft.settle_ms),
            PlanIntent::SetSettle(ms) => self.send_settings(s, self.draft.step, ms),
            PlanIntent::SetApproach(approach) => self.send_plan(
                s,
                self.draft.step,
                self.draft.settle_ms,
                Some(approach),
                None,
            ),
            PlanIntent::SetCaptureTimeout(seconds) => self.send_plan(
                s,
                self.draft.step,
                self.draft.settle_ms,
                None,
                Some(seconds),
            ),
            PlanIntent::SetWarmup(seconds) => self.command(s, Command::SetWarmup { seconds }),
            PlanIntent::UseSurveyBounds => self.command(s, Command::ApplyBounds {}),
            PlanIntent::OpenGuide(tab) => self.station.plan.guide = Some(tab),
            PlanIntent::SetFourShot(four) => self.command(
                s,
                Command::PixelShift {
                    shots: if four { 4 } else { 1 },
                },
            ),
            PlanIntent::SetCheck(on) => self.set_follow(on),
            PlanIntent::SetRetake(on) => self.command(s, Command::ErrorCorrection { enabled: on }),
            PlanIntent::SetStackWhenDone(on) => self.stack_when_done = on,
            PlanIntent::SetPowerDown(on) => self.command(s, Command::PowerPlan { enabled: on }),
            PlanIntent::Start => {
                if preflight::start_blockers(s, self).is_empty() {
                    self.command(s, Command::Start {});
                }
            }
            PlanIntent::Schedule => self.schedule_ui.open(s),
            PlanIntent::OpenSettings => self.station.settings_open = true,
            PlanIntent::Fix(fix) => self.apply_fix(s, fix),
        }
    }

    pub(super) fn apply_rail(&mut self, s: &Snapshot, intent: RailIntent) {
        match intent {
            RailIntent::Jog(delta) => self.command(s, Command::Jog { delta }),
            RailIntent::Focus(target) => self.focus_pending = Some(target),
            RailIntent::MarkStart => self.command(s, Command::Mark { start: true }),
            RailIntent::MarkEnd => self.command(s, Command::Mark { start: false }),
            RailIntent::MoveBound { start, to } => {
                self.station.mark_at = Some(MarkAt {
                    start,
                    to,
                    since: Instant::now(),
                });
                if s.host.position != Some(to) {
                    self.focus_pending = Some(to);
                }
            }
            RailIntent::UseSurveyBounds => self.command(s, Command::ApplyBounds {}),
            RailIntent::SurveyAgain => self.command(s, Command::Survey {}),
        }
    }

    pub(super) fn apply_live(&mut self, s: &Snapshot, intent: LiveIntent) {
        match intent {
            LiveIntent::SetRoi(roi) => self.command(s, Command::Roi { roi }),
            LiveIntent::Magnify { ratio, x, y } => {
                self.command(s, Command::Magnify { ratio, x, y })
            }
        }
    }

    pub(super) fn apply_flight(&mut self, s: &Snapshot, intent: FlightIntent) {
        match intent {
            FlightIntent::Pause => self.command(s, Command::Pause {}),
            FlightIntent::Resume => self.command(s, Command::Resume {}),
            FlightIntent::AskStop => self.confirm = Some(Confirm::Stop),
            FlightIntent::Stop => {
                self.confirm = None;
                self.command(s, Command::Stop {});
            }
            FlightIntent::KeepGoing => self.confirm = None,
            FlightIntent::Glance => self.station.glance = true,
            FlightIntent::SetStackWhenDone(on) => self.stack_when_done = on,
            FlightIntent::SetPowerDown(on) => self.command(s, Command::PowerPlan { enabled: on }),
            FlightIntent::ShowPlane(plane) => self.station.show_plane = Some(plane),
        }
    }

    /// Stage 1: the station inside today's Capture tab, laid out as the
    /// mockup's frame (control strip, canvas, rail, 348 px inspector), for
    /// checking the screens before the shell composes them.
    pub fn show_station(&mut self, ctx: &egui::Context) {
        self.activate(ctx);
        self.shown = true;
        let s = self.station_snapshot();
        self.observe_focus(&s);
        if let Some(plan) = s.host.plan.clone() {
            self.sync_plan(plan, s.host.plan_revision.unwrap_or(0));
        }
        self.painted_ready = (!s.receiver.is_null() || s.receiver_error.is_some())
            && ((s.observed.is_some() && (s.preview.is_some() || !s.host.preview.available))
                || s.connection_error.is_some()
                || self.config.controller.is_empty());
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| {
                let full = ui.max_rect();
                if self.station.glance {
                    self.station_glance(ui);
                    return;
                }
                let insp =
                    Rect::from_min_max(egui::pos2(full.right() - 348.0, full.top()), full.max);
                let main = Rect::from_min_max(full.min, egui::pos2(insp.left(), full.bottom()));
                let flight_mode = self.station_mode() == StationMode::Flight;
                let strip_h = if flight_mode { 0.0 } else { 36.0 };
                let rail_h = if flight_mode { 127.0 } else { 135.0 };
                let strip = Rect::from_min_size(main.min, egui::vec2(main.width(), strip_h));
                let rail =
                    Rect::from_min_max(egui::pos2(main.left(), main.bottom() - rail_h), main.max);
                let canvas = Rect::from_min_max(
                    egui::pos2(main.left(), strip.bottom()),
                    egui::pos2(main.right(), rail.top()),
                );
                if !flight_mode {
                    ui.scope_builder(egui::UiBuilder::new().max_rect(strip), |ui| {
                        self.station_strip(ui)
                    });
                }
                ui.scope_builder(egui::UiBuilder::new().max_rect(canvas), |ui| {
                    self.station_canvas(ui)
                });
                ui.scope_builder(egui::UiBuilder::new().max_rect(rail), |ui| {
                    self.station_rail(ui)
                });
                ui.scope_builder(egui::UiBuilder::new().max_rect(insp), |ui| {
                    self.station_inspector(ui)
                });
            });
        self.flush_focus(&s);
    }
}

impl LiveView {
    /// The live preview's texture, for the in-flight view's latest plane.
    pub(crate) fn preview_texture(&self) -> Option<(egui::TextureId, egui::Vec2)> {
        self.preview_handle().map(|t| (t.id(), t.size_vec2()))
    }
}

/// Records when a calibration finished, for the plan's "Calibrated 21:33".
pub(super) fn note_calibration(station: &mut Station, before: &str, after: &Calibration) {
    if before != "done" && matches!(after, Calibration::Done(_)) {
        station.calibrated_at = Some(SystemTime::now());
    }
}

#[cfg(test)]
#[path = "capture-station-tests.rs"]
mod tests;
