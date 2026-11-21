//! Activities in the window (Studio 2 P5): every long task reported once a
//! frame, Quiet mode, the serial stack queue and its file, the render's time
//! left, and the tray's actions. The Heavy lane is serial, so the running
//! render keeps today's state on `StrehlApp` (job, progress, logs); a queued
//! stack starts through the same `launch_render` as the Start button.
use super::studio_route::Station;
use super::*;
use crate::activity::{
    ActionId, Activities, ActivityKind, ActivityStatus, CancelMode, HistoryEntry, Lane, QuietMode,
    metadata_status, render_status,
};
use crate::activity_queue::{
    ActivityStore, FrozenRequest, QueueEntry, QueuedStack, StackQueue, StartGate,
};
use crate::render_eta::{EtaTracker, StageTimes};

/// The window's activity state, one field on `StrehlApp`.
pub(super) struct ActivityHub {
    pub activities: Activities,
    pub quiet: QuietMode,
    pub queue: StackQueue,
    store: ActivityStore,
    eta: EtaTracker,
    eta_seed: Option<Task<Option<StageTimes>>>,
    /// A queued stack whose stack is being opened before it starts.
    launching: Option<QueuedStack>,
    /// The queued stack now rendering.
    running_queue: Option<u64>,
    /// The running render's title and stack, for its history entry.
    render: Option<(String, Option<crate::workspace_history::NodeId>)>,
    /// What the running render renders, so the same render is not queued
    /// behind itself.
    rendering: Option<FrozenRequest>,
    /// Bytes copied by the view-bundle export in flight.
    pub bundle_progress: Option<std::sync::Arc<crate::session_import::BundleProgress>>,
}

impl ActivityHub {
    /// Reconcile runs a killed desktop left "Stacking", then load the queue
    /// and history beside the catalog (none for offscreen pictures).
    pub(super) fn load(
        catalog: &mut crate::workspace_history::Catalog,
        launch: &LaunchOptions,
    ) -> Self {
        catalog.reconcile_interrupted_runs(&[]);
        let path = catalog
            .path
            .as_ref()
            .and_then(|p| p.parent())
            .map(|dir| dir.join("activities.json"))
            .filter(|_| !launch.offscreen);
        let (mut queue, history, error) = match &path {
            Some(path) => crate::activity_queue::load(path),
            None => (StackQueue::default(), Default::default(), None),
        };
        let unix = crate::workspace_history::timestamp();
        let notes = queue.reconcile(catalog, unix);
        let mut activities = Activities::with_history(history);
        for note in notes {
            activities.record(note);
        }
        if let Some(error) = error {
            activities.record(HistoryEntry {
                kind: ActivityKind::Stack,
                title: "Earlier activity".into(),
                stack: None,
                outcome: "needs_you".into(),
                summary: error,
                finished: unix,
                took_seconds: None,
                action: None,
                log: None,
            });
        }
        let mut store = ActivityStore::new(path);
        store.mark_saved(&queue, &activities);
        Self {
            activities,
            quiet: QuietMode::default(),
            queue,
            store,
            eta: EtaTracker::default(),
            eta_seed: None,
            launching: None,
            running_queue: None,
            render: None,
            rendering: None,
            bundle_progress: None,
        }
    }
    /// A render is starting (`launch_render`, from Start or the queue).
    pub(super) fn launching_render(&mut self, request: &RenderRequest) {
        self.rendering = Some(FrozenRequest::from(request));
    }
}

impl StrehlApp {
    /// Once a frame, after the render events: start the queue's next stack
    /// when the Heavy lane allows, report every activity, save on change.
    pub(super) fn activities_frame(&mut self, ctx: &egui::Context) {
        let now = Instant::now();
        let unix = crate::workspace_history::timestamp();
        if let Some(task) = &self.activity_hub.eta_seed {
            match task.receiver.try_recv() {
                Ok(seed) => {
                    self.activity_hub.eta.set_seed(seed.ok().flatten());
                    self.activity_hub.eta_seed = None;
                }
                Err(mpsc::TryRecvError::Disconnected) => self.activity_hub.eta_seed = None,
                Err(mpsc::TryRecvError::Empty) => {}
            }
        }
        self.activity_hub.quiet.enabled = self.shell.prefs.quiet;
        let gate = StartGate {
            heavy_busy: self.job.is_some() || self.activity_hub.activities.heavy_busy(),
            quiet: self.activity_hub.quiet.holds(now),
            workspace: self.queue_workspace_hold(),
        };
        self.drive_queue(gate, unix);
        let mut activities = std::mem::take(&mut self.activity_hub.activities);
        activities.begin();
        self.report_activities(&mut activities, self.activity_hub.eta.eta(now));
        self.activity_hub
            .queue
            .report(&mut activities, gate, self.activity_hub.quiet.reason());
        activities.end(now, unix);
        self.activity_hub.activities = activities;
        let hub = &mut self.activity_hub;
        hub.store.save_if_changed(&hub.queue, &hub.activities);
        if !hub.queue.is_empty() && (gate.quiet || gate.workspace.is_some()) {
            // Look again for the full-screen program, or the workspace, soon.
            ctx.request_repaint_after(crate::activity::QUIET_POLL);
        }
    }

    /// Why the workspace cannot take a queued stack now, if it cannot.
    fn queue_workspace_hold(&self) -> Option<&'static str> {
        if self.activity_hub.launching.is_some() {
            None
        } else if self.picker_active() {
            Some("the file dialog to close")
        } else if self.scan.is_some() || self.replay.is_some() || self.editor.loading.is_some() {
            Some("the workspace to finish opening")
        } else if matches!(
            self.shell.navigator.station(),
            Station::Develop | Station::Export
        ) && self.editor.loaded.is_some()
        {
            // Starting a stack replaces the open photograph: never under a
            // developing hand.
            Some("you to leave Develop or Export")
        } else {
            None
        }
    }

    /// Start the queue's next stack: at once when it is the open stack,
    /// else after its stack has opened.
    fn drive_queue(&mut self, gate: StartGate, unix: u64) {
        if self.activity_hub.launching.is_some() {
            if self.scan.is_some() || self.replay.is_some() || self.editor.loading.is_some() {
                return;
            }
            let item = self.activity_hub.launching.take().unwrap();
            if self.active_stack == Some(item.stack) {
                self.launch_queued(item);
            } else {
                self.activity_hub.queue.finish(item.id);
                self.activity_hub.activities.record(HistoryEntry {
                    kind: ActivityKind::Stack,
                    title: item.title,
                    stack: Some(item.stack),
                    outcome: "needs_you".into(),
                    summary: "Its stack could not be opened".into(),
                    finished: unix,
                    took_seconds: None,
                    action: Some(ActionId::OpenStack { stack: item.stack }),
                    log: None,
                });
            }
            return;
        }
        let Some(item) = self.activity_hub.queue.take_next(gate, unix) else {
            return;
        };
        if self.active_stack == Some(item.stack) && self.stack.is_some() {
            self.launch_queued(item);
        } else {
            self.open_project_stack(item.stack);
            self.activity_hub.launching = Some(item);
        }
    }

    /// The frozen request, with its run record, through today's launch.
    fn launch_queued(&mut self, item: QueuedStack) {
        let mut run = item.run;
        run.created = crate::workspace_history::timestamp();
        let request: RenderRequest = item.request.into();
        // The controls show what renders.
        self.controls.settings = request.settings.clone();
        self.controls.exposure = request.exposure_ev;
        self.controls.gate = request.pyramid_gate;
        if let Some(workers) = request.worker_threads {
            self.controls.workers = workers;
        }
        self.pending_stack = Some(item.stack);
        self.pending_run = Some(run);
        self.activity_hub.running_queue = Some(item.id);
        self.launch_render(request);
    }

    /// Start (the shortcut or the palette) while a stack renders: queue the
    /// open stack with its current recipe instead, once. A repeated press,
    /// or a recipe already rendering or waiting, queues nothing. Returns
    /// whether the press was handled here.
    pub(super) fn queue_while_running(&mut self) -> bool {
        if self.job.is_none() {
            return false;
        }
        self.save_active_draft();
        self.status = match self.active_stack.map(|id| self.queue_stack(id)) {
            Some(Ok(_)) => "Queued; it starts when the running stack ends".into(),
            Some(Err(error)) => error.to_string(),
            None => "A stack is already running".into(),
        };
        true
    }

    /// Queue a catalog stack with its saved recipe (`StackDraft`), without
    /// opening it. Returns the queue id.
    pub(super) fn queue_stack(
        &mut self,
        id: crate::workspace_history::NodeId,
    ) -> anyhow::Result<u64> {
        let node = self
            .catalog
            .node(id)
            .filter(|n| n.kind == crate::workspace_history::NodeKind::Stack)
            .ok_or_else(|| anyhow::anyhow!("Choose a stack"))?;
        let draft = node
            .stack
            .clone()
            .ok_or_else(|| anyhow::anyhow!("Choose a stack"))?;
        anyhow::ensure!(
            draft.settings.session.is_none(),
            "Sessions start from their own panel"
        );
        let engine = self
            .engine
            .clone()
            .ok_or_else(|| anyhow::anyhow!("Stacking engine unavailable"))?;
        anyhow::ensure!(
            !self.output.as_os_str().is_empty(),
            "Choose an output folder in Adjust > Destination"
        );
        let planes = draft
            .settings
            .frame_limit
            .unwrap_or(draft.sources.len())
            .min(draft.sources.len().max(1));
        let label = draft
            .source
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();
        let run = crate::workspace_history::Run {
            directory: PathBuf::new(),
            source: draft.source.clone(),
            output: PathBuf::new(),
            log: PathBuf::new(),
            label,
            created: crate::workspace_history::timestamp(),
            status: "Stacking".into(),
            frames: planes,
            sources: draft.sources.clone(),
            settings: draft.settings.clone(),
            exposure: draft.exposure,
            gate: draft.gate,
            workers: draft.workers,
            pinned: false,
            imported: None,
        };
        let request = RenderRequest {
            executable: engine,
            source: draft.source.clone(),
            output_parent: self.output.clone(),
            exposure_ev: draft.exposure,
            pyramid_gate: draft.gate,
            worker_threads: Some(draft.workers.max(1)),
            settings: draft.settings.clone(),
            retain_master: true,
            recipe: None,
        };
        let frozen = FrozenRequest::from(&request);
        anyhow::ensure!(
            !(self.job.is_some()
                && self.pending_stack.or(self.active_stack) == Some(id)
                && self
                    .activity_hub
                    .rendering
                    .as_ref()
                    .is_some_and(|running| running.same_render(&frozen))),
            "This stack is already rendering with these settings"
        );
        anyhow::ensure!(
            !self.activity_hub.queue.waiting_same(id, &frozen),
            "This stack already waits in the queue with these settings"
        );
        let title = format!("Stack · {}", node.name);
        let estimate = self
            .previous_seed(id)
            .and_then(|seed| seed.estimate(planes));
        self.activity_hub.queue.enqueue(
            QueueEntry {
                stack: id,
                title,
                planes,
                estimate_seconds: estimate,
            },
            &request,
            run,
            crate::workspace_history::timestamp(),
        )
    }

    /// The newest saved render of `stack`, whose log seeds the time left.
    /// Only the catalog is read here; the log is read on a worker.
    fn previous_log(&self, stack: crate::workspace_history::NodeId) -> Option<PathBuf> {
        let node = self.catalog.node(stack)?;
        node.revisions.iter().rev().find_map(|directory| {
            self.catalog
                .runs
                .iter()
                .find(|run| &run.directory == directory && run.status == "Saved")
                .map(|run| run.log.clone())
        })
    }
    /// The running render's seed, for a queued variant of the same stack.
    fn previous_seed(&self, stack: crate::workspace_history::NodeId) -> Option<StageTimes> {
        (self.activity_hub.render.as_ref().and_then(|r| r.1) == Some(stack))
            .then(|| self.activity_hub.eta.seed())
            .flatten()
    }

    pub(super) fn activity_render_started(&mut self, ctx: &egui::Context) {
        let stack = self.pending_stack.or(self.active_stack);
        let name = stack
            .and_then(|id| self.catalog.node(id))
            .map_or_else(|| "this stack".to_owned(), |node| node.name.clone());
        self.activity_hub.render = Some((format!("Stack · {name}"), stack));
        self.activity_hub.eta = EtaTracker::new(None);
        self.activity_hub.eta_seed = stack
            .and_then(|id| self.previous_log(id))
            .map(|log| crate::render_eta::spawn_seed(log, ctx.clone()));
    }
    pub(super) fn activity_render_log(&mut self, text: &str) {
        self.activity_hub.eta.ingest(text, Instant::now());
    }
    pub(super) fn activity_render_finished(&mut self, outcome: &jobs::RenderOutcome) {
        let (title, stack) = self
            .activity_hub
            .render
            .take()
            .unwrap_or_else(|| ("Stack".into(), self.pending_stack));
        let note = Self::render_outcome_note(
            stack,
            &title,
            outcome,
            self.started.map(|s| s.elapsed()),
            crate::workspace_history::timestamp(),
        );
        self.activity_hub.activities.record(note);
        if let Some(id) = self.activity_hub.running_queue.take() {
            self.activity_hub.queue.finish(id);
        }
        self.activity_hub.eta = EtaTracker::default();
        self.activity_hub.eta_seed = None;
        self.activity_hub.rendering = None;
    }

    /// The tray's actions that concern activities; the shell routes the rest.
    pub(super) fn activity_action(&mut self, action: crate::activity_tray::TrayAction) {
        use crate::activity_tray::TrayAction;
        match action {
            TrayAction::Cancel(id) => self.cancel_activity(id),
            TrayAction::Remove(id) => {
                self.activity_hub.queue.remove(id);
            }
            TrayAction::SetQuiet(on) => {
                self.shell.prefs.quiet = on;
                self.shell.prefs_dirty = true;
                self.activity_hub.quiet.enabled = on;
            }
            TrayAction::ResumeQueue => self.activity_hub.queue.resume(),
            TrayAction::Action(next) => self.activity_next(next),
            TrayAction::OpenLog | TrayAction::OpenAgent | TrayAction::Notice(_) => {}
        }
    }
    fn cancel_activity(&mut self, id: u64) {
        let Some(status) = self.activity_hub.activities.find(id).cloned() else {
            return;
        };
        if let Some(queued) = status.queued {
            self.activity_hub.queue.remove(queued);
            return;
        }
        match status.kind {
            ActivityKind::Stack => self.stop_stack(),
            ActivityKind::Export => {
                if let Some(task) = &self.editor.exporting {
                    task.cancel();
                }
            }
            ActivityKind::ViewBundle => {
                if let Some(task) = &self.view_bundle_export {
                    task.cancel();
                }
            }
            ActivityKind::Import => {
                if let Some((_, _, task)) = &self.session_import {
                    task.cancel();
                }
            }
            ActivityKind::FocusStep => self.capture.cancel_focus_step(),
            ActivityKind::CompactEstimate => self.capture.cancel_compact_estimate(),
            ActivityKind::Calibration => self.capture.stop_calibration(),
            ActivityKind::Metadata => self.camera_metadata.cancel(),
            ActivityKind::Capture => {
                // Only through the capture's own confirmation.
                self.capture.confirm = Some(crate::capture_workspace::Confirm::Stop);
                self.go_station(Station::Capture);
            }
            ActivityKind::CaptureFollow | ActivityKind::CompactApply | ActivityKind::Open => {}
        }
    }
    fn activity_next(&mut self, next: ActionId) {
        match next {
            ActionId::OpenStack { stack } => {
                if self.job.is_none() {
                    self.open_project_stack(stack);
                }
            }
            ActionId::OpenRun { run } => {
                if let Some(saved) = self
                    .catalog
                    .runs
                    .iter()
                    .find(|r| r.directory == run)
                    .cloned()
                {
                    self.reopen_run(saved);
                }
            }
            ActionId::OpenCapture => self.go_station(Station::Capture),
            ActionId::Reveal { path } | ActionId::ShowLog { path } => {
                if let Err(error) = crate::reveal_path::reveal(&path) {
                    self.error = Some(error.to_string());
                }
            }
            ActionId::Retry { stack } => {
                if let Err(error) = self.queue_stack(stack) {
                    self.error = Some(error.to_string());
                }
            }
            ActionId::ResumeQueue => self.activity_hub.queue.resume(),
        }
    }

    /// Report every activity this window owns.
    pub(super) fn report_activities(
        &self,
        activities: &mut Activities,
        render_eta: Option<Duration>,
    ) {
        if let Some(job) = &self.job {
            let stack = self.pending_stack.or(self.active_stack);
            let run = stack
                .and_then(|id| self.catalog.latest_run(id))
                .filter(|run| run.status == "Stacking");
            let title = self.activity_hub.render.as_ref().map_or_else(
                || {
                    let name = stack
                        .and_then(|id| self.catalog.node(id))
                        .map_or_else(|| "this stack".to_owned(), |node| node.name.clone());
                    format!("Stack · {name}")
                },
                |render| render.0.clone(),
            );
            let mut status = render_status(
                "render",
                &title,
                stack,
                &self.progress,
                job.is_cancelling(),
                self.started,
                render_eta,
                run.map(|run| run.log.clone()),
            );
            if self.pending_run.is_some() && !job.is_cancelling() {
                status.phase = "Starting".into();
            }
            if status.total.is_none()
                && let Some((done, total)) = self.progress.folded
            {
                status.done = Some(done as u64);
                status.total = Some(total as u64);
            }
            status.facts = match &self.stack {
                Some(scan) => format!(
                    "{} workers · {} RAW · {}",
                    self.controls.workers,
                    scan.frames.len(),
                    crate::library_paint::bytes(scan.total_bytes)
                ),
                None => format!("{} workers", self.controls.workers),
            };
            activities.report(status);
        }
        if let Some(item) = &self.activity_hub.launching {
            let mut status = ActivityStatus::new(
                ActivityKind::Stack,
                &format!("queued:{}", item.id),
                item.title.clone(),
                Lane::Heavy,
            )
            .with_phase("Opening its stack");
            status.stack = Some(item.stack);
            activities.report(status);
        }
        if self.scan.is_some() {
            activities.report(ActivityStatus::new(
                ActivityKind::Open,
                "scan",
                "Reading the bracket",
                Lane::Background,
            ));
        }
        if self.replay.is_some() {
            activities.report(ActivityStatus::new(
                ActivityKind::Open,
                "replay",
                "Opening the saved render",
                Lane::Background,
            ));
        }
        if let Some((phase, path)) = self.export_phase() {
            let file = path
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default();
            activities.report(
                ActivityStatus::new(
                    ActivityKind::Export,
                    &path.to_string_lossy(),
                    format!("Export · {file}"),
                    Lane::Background,
                )
                .with_phase(match phase {
                    1 => "Preparing the version",
                    2 => "Writing the file",
                    _ => "Recording the export",
                })
                .with_progress(Some(u64::from(phase.saturating_sub(1))), Some(3))
                .with_cancel(if phase == 2 {
                    CancelMode::Cooperative
                } else {
                    CancelMode::None
                }),
            );
        } else if self.editor.exporting.is_some() {
            activities.report(
                ActivityStatus::running(ActivityKind::Export, "Exporting", Lane::Background)
                    .with_cancel(CancelMode::Cooperative),
            );
        } else if self.photo_history_busy() {
            activities.report(ActivityStatus::running(
                ActivityKind::Export,
                "Saving the version history",
                Lane::Background,
            ));
        }
        if self.view_bundle_export.is_some() {
            let progress = self.activity_hub.bundle_progress.as_ref().map(|p| {
                (
                    p.copied.load(std::sync::atomic::Ordering::Relaxed),
                    p.total.load(std::sync::atomic::Ordering::Relaxed),
                )
            });
            let (done, total) = match progress {
                Some((copied, total)) if total > 0 => (Some(copied.min(total)), Some(total)),
                _ => (None, None),
            };
            activities.report(
                ActivityStatus::running(
                    ActivityKind::ViewBundle,
                    "Exporting the view bundle",
                    Lane::Background,
                )
                .with_phase("Copying and verifying the complete bundle")
                .with_progress(done, total)
                .with_cancel(CancelMode::Cooperative),
            );
        }
        if let Some((epoch, _, _)) = &self.session_import {
            activities.report(
                ActivityStatus::new(
                    ActivityKind::Import,
                    &format!("session-import:{epoch}"),
                    "Importing a completed session",
                    Lane::Background,
                )
                .with_phase("Verifying the session's files")
                .with_cancel(CancelMode::Cooperative),
            );
        }
        if let Some(status) = metadata_status(&self.camera_metadata) {
            activities.report(status);
        }
        self.capture.report_activities(activities);
        // A capture this window does not run (the rig reports it).
        if self.shell.rig.capturing()
            && !activities
                .statuses()
                .iter()
                .any(|s| s.kind == ActivityKind::Capture)
        {
            let mut capture = ActivityStatus::new(
                ActivityKind::Capture,
                "rig",
                ActivityKind::Capture.label(),
                Lane::Camera,
            )
            .with_progress(self.shell.rig.completed, self.shell.rig.planned);
            capture.phase = self.shell.rig.phase.clone().unwrap_or_default();
            activities.report(capture);
        }
    }

    /// The agent snapshot's `activities` key (plan 11): current activities
    /// (the queue's waiting stacks among them), the newest history entries,
    /// and whether the queue waits for Resume.
    pub(super) fn activities_value(hub: &ActivityHub) -> serde_json::Value {
        let mut value = hub.activities.public(Instant::now(), 16);
        value["queue_paused"] = serde_json::Value::Bool(hub.queue.paused);
        value
    }

    /// What a finished render leaves in the history.
    pub(super) fn render_outcome_note(
        stack: Option<crate::workspace_history::NodeId>,
        title: &str,
        outcome: &jobs::RenderOutcome,
        took: Option<Duration>,
        unix: u64,
    ) -> HistoryEntry {
        let (state, summary, action, log) = match outcome {
            jobs::RenderOutcome::Completed { output, log, .. } => (
                "done",
                "Stack saved".to_owned(),
                Some(ActionId::Reveal {
                    path: output.clone(),
                }),
                Some(log.clone()),
            ),
            jobs::RenderOutcome::Cancelled { .. } => {
                ("stopped", "Cancelled".to_owned(), None, None)
            }
            jobs::RenderOutcome::Failed { message, .. } => (
                "needs_you",
                message.clone(),
                stack.map(|stack| ActionId::Retry { stack }),
                None,
            ),
        };
        HistoryEntry {
            kind: ActivityKind::Stack,
            title: title.to_owned(),
            stack,
            outcome: state.into(),
            summary,
            finished: unix,
            took_seconds: took.map(|d| d.as_secs_f64()),
            action,
            log,
        }
    }
}

#[cfg(test)]
#[path = "app-activities-tests.rs"]
mod tests;
