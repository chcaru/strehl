//! The stack queue (plan 6.6 step 4) and the activity file (step 6). A queued
//! stack is a frozen request: the recipe, sources and output folder chosen
//! when it was queued, never the editor's later state. The Heavy lane is
//! serial: the head starts only when nothing heavy runs, Quiet does not hold
//! and the queue is not paused.
//!
//! Queue and history live in `%LOCALAPPDATA%\Strehl\activities.json`, never
//! in `projects.json`; it is written atomically and its history is bounded.
use crate::{
    activity::{
        ActionId, Activities, ActivityKind, ActivityState, ActivityStatus, CancelMode,
        HistoryEntry, Lane, MAX_HISTORY,
    },
    jobs::{RenderRequest, RenderSettings},
    workspace_history::{Catalog, NodeId, NodeKind, Run},
};
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::{
    collections::VecDeque,
    io::Write,
    path::{Path, PathBuf},
    time::Duration,
};

const FORMAT: u32 = 1;
const MAX_QUEUE: usize = 64;
const MAX_FILE_BYTES: u64 = 8 * 1024 * 1024;

/// `RenderRequest`, as the queue stores it.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct FrozenRequest {
    pub executable: PathBuf,
    pub source: PathBuf,
    pub output_parent: PathBuf,
    pub exposure_ev: Option<f32>,
    pub pyramid_gate: Option<f32>,
    pub worker_threads: Option<usize>,
    pub settings: RenderSettings,
    pub retain_master: bool,
    pub recipe: Option<strehl_edit::DevelopmentRecipe>,
}
impl FrozenRequest {
    /// Whether two requests render the same photograph: one source, one
    /// recipe of settings, exposure, gate and workers (the engine path and
    /// a development recipe carried along aside).
    pub(crate) fn same_render(&self, other: &Self) -> bool {
        self.source == other.source
            && self.settings == other.settings
            && self.exposure_ev == other.exposure_ev
            && self.pyramid_gate == other.pyramid_gate
            && self.worker_threads == other.worker_threads
    }
}
impl From<&RenderRequest> for FrozenRequest {
    fn from(request: &RenderRequest) -> Self {
        Self {
            executable: request.executable.clone(),
            source: request.source.clone(),
            output_parent: request.output_parent.clone(),
            exposure_ev: request.exposure_ev,
            pyramid_gate: request.pyramid_gate,
            worker_threads: request.worker_threads,
            settings: request.settings.clone(),
            retain_master: request.retain_master,
            recipe: request.recipe.clone(),
        }
    }
}
impl From<FrozenRequest> for RenderRequest {
    fn from(request: FrozenRequest) -> Self {
        Self {
            executable: request.executable,
            source: request.source,
            output_parent: request.output_parent,
            exposure_ev: request.exposure_ev,
            pyramid_gate: request.pyramid_gate,
            worker_threads: request.worker_threads,
            settings: request.settings,
            retain_master: request.retain_master,
            recipe: request.recipe,
        }
    }
}

/// One queued stack: the request, the run record the start will complete
/// (directory, output and log are filled in when the engine starts) and the
/// catalog stack it belongs to.
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct QueuedStack {
    pub id: u64,
    pub stack: NodeId,
    /// "Stack · Blue weevil, dorsal"
    pub title: String,
    pub request: FrozenRequest,
    pub run: Run,
    /// Unix seconds.
    pub queued: u64,
    pub planes: usize,
    /// From the stack's previous render, when known (seconds).
    #[serde(default)]
    pub estimate_seconds: Option<f64>,
}

/// What a queued stack is, apart from its frozen request and run record.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct QueueEntry {
    pub stack: NodeId,
    pub title: String,
    pub planes: usize,
    /// From the stack's previous render (`render_eta::StageTimes::estimate`).
    pub estimate_seconds: Option<f64>,
}

/// What the Heavy lane's next start depends on.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct StartGate {
    /// A Heavy-lane activity is running (a stack, a repair, compaction).
    pub heavy_busy: bool,
    /// Quiet mode holds (a full-screen program is in front).
    pub quiet: bool,
    /// Why the workspace cannot take a stack now (a dialog, an opening,
    /// a photograph being developed), if it cannot.
    pub workspace: Option<&'static str>,
}

#[derive(Debug, Default)]
pub(crate) struct StackQueue {
    items: VecDeque<QueuedStack>,
    /// The queued stack that was started and has not finished.
    running: Option<RunningStack>,
    /// Loaded queues wait for the owner: heavy work never starts by itself
    /// after a restart.
    pub paused: bool,
    next_id: u64,
    revision: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RunningStack {
    pub id: u64,
    pub stack: NodeId,
    pub title: String,
    pub started: u64,
}

impl StackQueue {
    #[cfg(test)]
    pub(crate) fn len(&self) -> usize {
        self.items.len()
    }
    pub(crate) fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
    #[cfg(test)]
    pub(crate) fn items(&self) -> impl Iterator<Item = &QueuedStack> {
        self.items.iter()
    }
    #[cfg(test)]
    pub(crate) fn running(&self) -> Option<&RunningStack> {
        self.running.as_ref()
    }
    /// Changes with every edit; the store saves on it.
    pub(crate) fn revision(&self) -> u64 {
        self.revision
    }
    fn touch(&mut self) {
        self.revision = self.revision.wrapping_add(1);
    }
    /// Queue a frozen request; returns its id.
    pub(crate) fn enqueue(
        &mut self,
        entry: QueueEntry,
        request: &RenderRequest,
        run: Run,
        unix: u64,
    ) -> Result<u64> {
        let QueueEntry {
            stack,
            title,
            planes,
            estimate_seconds,
        } = entry;
        anyhow::ensure!(
            self.items.len() < MAX_QUEUE,
            "The queue holds {MAX_QUEUE} stacks; start or remove one first"
        );
        self.next_id = self
            .next_id
            .max(self.items.iter().map(|i| i.id).max().unwrap_or(0))
            + 1;
        let id = self.next_id;
        self.items.push_back(QueuedStack {
            id,
            stack,
            title,
            request: FrozenRequest::from(request),
            run,
            queued: unix,
            planes,
            estimate_seconds,
        });
        self.touch();
        Ok(id)
    }
    /// The stacks waiting, in order.
    pub(crate) fn stacks(&self) -> impl Iterator<Item = NodeId> + '_ {
        self.items.iter().map(|item| item.stack)
    }
    /// Whether `stack` already waits with the same render.
    pub(crate) fn waiting_same(&self, stack: NodeId, request: &FrozenRequest) -> bool {
        self.items
            .iter()
            .any(|item| item.stack == stack && item.request.same_render(request))
    }
    /// Remove a waiting stack; a started one is cancelled through its job.
    pub(crate) fn remove(&mut self, id: u64) -> Option<QueuedStack> {
        let at = self.items.iter().position(|item| item.id == id)?;
        self.touch();
        self.items.remove(at)
    }
    /// Move a waiting stack to `position` (0 is next).
    pub(crate) fn move_to(&mut self, id: u64, position: usize) -> bool {
        let Some(at) = self.items.iter().position(|item| item.id == id) else {
            return false;
        };
        let item = self.items.remove(at).unwrap();
        self.items.insert(position.min(self.items.len()), item);
        self.touch();
        true
    }
    pub(crate) fn resume(&mut self) {
        if self.paused {
            self.paused = false;
            self.touch();
        }
    }
    /// Why the head waits, or None when it may start now.
    pub(crate) fn holding(&self, gate: StartGate, quiet_reason: Option<&str>) -> Option<String> {
        if self.paused {
            Some("you to resume the queue".into())
        } else if self.running.is_some() || gate.heavy_busy {
            Some("the stack before it".into())
        } else if gate.quiet {
            Some(
                quiet_reason
                    .unwrap_or("the full-screen program in front to close (Quiet)")
                    .to_owned(),
            )
        } else {
            gate.workspace.map(str::to_owned)
        }
    }
    /// The head, when the lane is free; it becomes the running stack.
    pub(crate) fn take_next(&mut self, gate: StartGate, unix: u64) -> Option<QueuedStack> {
        if self.holding(gate, None).is_some() {
            return None;
        }
        let item = self.items.pop_front()?;
        self.running = Some(RunningStack {
            id: item.id,
            stack: item.stack,
            title: item.title.clone(),
            started: unix,
        });
        self.touch();
        Some(item)
    }
    /// The started stack finished, failed or was cancelled.
    pub(crate) fn finish(&mut self, id: u64) {
        if self.running.as_ref().is_some_and(|r| r.id == id) {
            self.running = None;
            self.touch();
        }
    }
    /// Report every waiting stack, in order.
    pub(crate) fn report(
        &self,
        activities: &mut Activities,
        gate: StartGate,
        quiet_reason: Option<&str>,
    ) {
        for (index, item) in self.items.iter().enumerate() {
            let for_what = if index == 0 {
                self.holding(gate, quiet_reason)
                    .unwrap_or_else(|| "its turn".into())
            } else {
                "the stack before it".into()
            };
            let mut status = ActivityStatus::new(
                ActivityKind::Stack,
                &format!("queued:{}", item.id),
                item.title.clone(),
                Lane::Heavy,
            )
            .with_state(ActivityState::Waiting {
                for_what,
                gives_up: None,
            })
            .with_phase(queued_detail(item))
            .with_cancel(CancelMode::Cooperative)
            .with_progress(None, Some(item.planes as u64));
            status.stack = Some(item.stack);
            status.queued = Some(item.id);
            status.eta = item
                .estimate_seconds
                .filter(|s| s.is_finite() && *s >= 0.0)
                .map(Duration::from_secs_f64);
            activities.report(status);
        }
    }
    /// After loading: drop stacks the catalog no longer has, record a stack
    /// that was running when the desktop closed, and pause what is left.
    /// Returns the notes for the history.
    pub(crate) fn reconcile(&mut self, catalog: &Catalog, unix: u64) -> Vec<HistoryEntry> {
        let mut notes = Vec::new();
        if let Some(running) = self.running.take() {
            notes.push(HistoryEntry {
                kind: ActivityKind::Stack,
                title: running.title,
                stack: Some(running.stack),
                outcome: "stopped".into(),
                summary: "The desktop closed while this stack was running; the render is marked interrupted".into(),
                finished: unix,
                took_seconds: None,
                action: Some(ActionId::Retry {
                    stack: running.stack,
                }),
                log: None,
            });
        }
        self.items.retain(|item| {
            let exists = catalog
                .node(item.stack)
                .is_some_and(|n| n.kind == NodeKind::Stack);
            if !exists {
                notes.push(HistoryEntry {
                    kind: ActivityKind::Stack,
                    title: item.title.clone(),
                    stack: None,
                    outcome: "stopped".into(),
                    summary: "Removed from the queue: its stack is no longer in the library".into(),
                    finished: unix,
                    took_seconds: None,
                    action: None,
                    log: None,
                });
            }
            exists
        });
        if !self.items.is_empty() {
            self.paused = true;
        }
        self.touch();
        notes
    }
}

fn queued_detail(item: &QueuedStack) -> String {
    let mut detail = crate::activity::plural(item.planes, "plane", "planes");
    if let Some(seconds) = item.estimate_seconds.filter(|s| s.is_finite() && *s > 0.0) {
        detail.push_str(" · about ");
        detail.push_str(&crate::render_eta::spoken(Duration::from_secs_f64(seconds)));
    }
    detail
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredActivities {
    format: u32,
    #[serde(default)]
    paused: bool,
    #[serde(default)]
    running: Option<RunningStack>,
    #[serde(default)]
    queue: Vec<QueuedStack>,
    #[serde(default)]
    history: Vec<HistoryEntry>,
}

/// The file's contents, or why they could not be read (then everything
/// starts empty and the unreadable file is left untouched until a save).
pub(crate) fn load(path: &Path) -> (StackQueue, VecDeque<HistoryEntry>, Option<String>) {
    if !path.exists() {
        return (StackQueue::default(), VecDeque::new(), None);
    }
    let read = (|| -> Result<StoredActivities> {
        let file = std::fs::File::open(path)?;
        anyhow::ensure!(
            file.metadata()?.len() <= MAX_FILE_BYTES,
            "The activity file exceeds its size limit"
        );
        let stored: StoredActivities = serde_json::from_reader(std::io::BufReader::new(file))?;
        anyhow::ensure!(
            stored.format <= FORMAT,
            "The activity file was written by a newer Strehl"
        );
        Ok(stored)
    })();
    match read {
        Ok(stored) => {
            let next_id = stored.queue.iter().map(|i| i.id).max().unwrap_or(0);
            let queue = StackQueue {
                items: stored.queue.into_iter().take(MAX_QUEUE).collect(),
                running: stored.running,
                paused: stored.paused,
                next_id,
                revision: 0,
            };
            let history = stored.history.into_iter().take(MAX_HISTORY).collect();
            (queue, history, None)
        }
        Err(error) => (
            StackQueue::default(),
            VecDeque::new(),
            Some(format!("Earlier activity could not be read: {error:#}")),
        ),
    }
}

/// Write queue and history atomically (temporary file, then rename).
pub(crate) fn save(
    path: &Path,
    queue: &StackQueue,
    history: &VecDeque<HistoryEntry>,
) -> Result<()> {
    let stored = StoredActivities {
        format: FORMAT,
        paused: queue.paused,
        running: queue.running.clone(),
        queue: queue.items.iter().cloned().collect(),
        history: history.iter().take(MAX_HISTORY).cloned().collect(),
    };
    let bytes = serde_json::to_vec_pretty(&stored)?;
    anyhow::ensure!(
        bytes.len() as u64 <= MAX_FILE_BYTES,
        "The activity file would exceed its size limit"
    );
    let parent = path.parent().context("The activity file has no folder")?;
    std::fs::create_dir_all(parent)?;
    let temporary = path.with_extension(format!("{}.tmp", std::process::id()));
    let result = (|| -> Result<()> {
        let mut file = std::fs::File::create(&temporary)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        drop(file);
        std::fs::rename(&temporary, path)?;
        Ok(())
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(&temporary);
    }
    result
}

/// Saves when the queue or the history changed since the last save.
#[derive(Debug, Default)]
pub(crate) struct ActivityStore {
    pub path: Option<PathBuf>,
    saved: Option<(u64, u64)>,
    pub error: Option<String>,
}
impl ActivityStore {
    pub(crate) fn new(path: Option<PathBuf>) -> Self {
        Self {
            path,
            saved: None,
            error: None,
        }
    }
    /// What was just loaded needs no writing back.
    pub(crate) fn mark_saved(&mut self, queue: &StackQueue, activities: &Activities) {
        self.saved = Some((queue.revision(), activities.history_revision()));
    }
    /// Cheap when nothing changed: two counters compared.
    pub(crate) fn save_if_changed(&mut self, queue: &StackQueue, activities: &Activities) {
        let key = (queue.revision(), activities.history_revision());
        if self.saved == Some(key) {
            return;
        }
        let Some(path) = &self.path else {
            self.saved = Some(key);
            return;
        };
        match save(path, queue, activities.history()) {
            Ok(()) => {
                self.saved = Some(key);
                self.error = None;
            }
            Err(error) => {
                // One attempt per change: a failing disk is not retried every frame.
                self.saved = Some(key);
                self.error = Some(format!("Saving activity: {error:#}"));
            }
        }
    }
}

#[cfg(test)]
#[path = "activity-queue-tests.rs"]
mod tests;
