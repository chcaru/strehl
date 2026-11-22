//! Studio 2 activities (plan 6.6): one model for every long task the desktop
//! runs — stacking, exports, the view-bundle copy, the engine's capture
//! tools, calibration, the capture and its checker, metadata reads and
//! session imports. Owners keep running their work as before; once a frame
//! each reports an `ActivityStatus` into `Activities`, which keeps the
//! frame's list, notices terminal states and keeps a bounded history.
//!
//! Interactive edit previews and thumbnails are not activities.
use crate::workspace_history::NodeId;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::VecDeque,
    path::PathBuf,
    time::{Duration, Instant},
};

/// Finished activities kept for the tray's "Earlier" list and the file.
pub(crate) const MAX_HISTORY: usize = 200;
/// Terminal states already recorded, remembered so an owner that keeps its
/// last result on screen is recorded once.
const MAX_RECORDED: usize = 256;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ActivityKind {
    Stack,
    Export,
    ViewBundle,
    FocusStep,
    CompactEstimate,
    CompactApply,
    Calibration,
    CaptureFollow,
    Capture,
    Metadata,
    Import,
    /// Reading a bracket or reopening a saved render (additive to the plan's
    /// list: they hold the workspace while they run).
    Open,
    /// Develop's depth repair: the painted area only, or the whole stack.
    Repair,
}
impl ActivityKind {
    /// The snapshot's name for the kind.
    pub(crate) fn key(self) -> &'static str {
        match self {
            Self::Stack => "stack",
            Self::Export => "export",
            Self::ViewBundle => "view_bundle",
            Self::FocusStep => "focus_step",
            Self::CompactEstimate => "compact_estimate",
            Self::CompactApply => "compact_apply",
            Self::Calibration => "calibration",
            Self::CaptureFollow => "capture_follow",
            Self::Capture => "capture",
            Self::Metadata => "metadata",
            Self::Import => "import",
            Self::Open => "open",
            Self::Repair => "repair",
        }
    }
    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::Stack => "Stack",
            Self::Export => "Export",
            Self::ViewBundle => "View bundle",
            Self::FocusStep => "Measure focus step",
            Self::CompactEstimate => "Compaction estimate",
            Self::CompactApply => "Compact",
            Self::Calibration => "Calibrate step",
            Self::CaptureFollow => "Checks",
            Self::Capture => "Capture",
            Self::Metadata => "Camera metadata",
            Self::Import => "Open completed session",
            Self::Open => "Open",
            Self::Repair => "Depth repair",
        }
    }
}

/// Something the user can do next, carried by a state and routed by the shell.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "action", rename_all = "snake_case")]
pub(crate) enum ActionId {
    OpenStack {
        stack: NodeId,
    },
    OpenRun {
        run: PathBuf,
    },
    OpenCapture,
    Reveal {
        path: PathBuf,
    },
    ShowLog {
        path: PathBuf,
    },
    /// Queue the stack again with its last recipe.
    Retry {
        stack: NodeId,
    },
    ResumeQueue,
}

/// Each state names its obligation: what it waits for, what it needs, what
/// was kept, what comes next (proposal 5.8).
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum ActivityState {
    Waiting {
        for_what: String,
        gives_up: Option<Instant>,
    },
    Running,
    NeedsYou {
        message: String,
        action: Option<ActionId>,
    },
    Stopped {
        message: String,
        kept: Option<String>,
    },
    Done {
        summary: String,
        next: Option<ActionId>,
    },
}
impl ActivityState {
    pub(crate) fn name(&self) -> &'static str {
        match self {
            Self::Waiting { .. } => "waiting",
            Self::Running => "running",
            Self::NeedsYou { .. } => "needs_you",
            Self::Stopped { .. } => "stopped",
            Self::Done { .. } => "done",
        }
    }
    pub(crate) fn terminal(&self) -> bool {
        matches!(self, Self::Stopped { .. } | Self::Done { .. })
    }
}

/// Heavy work is serial and holds in Quiet mode; captures and transfers
/// never wait.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum Lane {
    Heavy,
    Background,
    Camera,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum CancelMode {
    None,
    /// The work stops at its next check.
    Cooperative,
    /// The engine process is ended.
    Kill,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ActivityStatus {
    /// Stable for the activity's life: a hash of its kind and its owner's key.
    pub id: u64,
    pub kind: ActivityKind,
    pub title: String,
    pub stack: Option<NodeId>,
    pub state: ActivityState,
    pub phase: String,
    pub done: Option<u64>,
    pub total: Option<u64>,
    pub started: Option<Instant>,
    pub eta: Option<Duration>,
    pub cancel: CancelMode,
    pub lane: Lane,
    pub log: Option<PathBuf>,
    /// A queued stack's place in the queue, for Remove.
    pub queued: Option<u64>,
    /// Facts beside the progress: workers, RAW count, size.
    pub facts: String,
}
impl ActivityStatus {
    /// A running activity identified by `key` (a run folder, a capture, …).
    pub(crate) fn new(kind: ActivityKind, key: &str, title: impl Into<String>, lane: Lane) -> Self {
        Self {
            id: activity_id(kind, key),
            kind,
            title: title.into(),
            stack: None,
            state: ActivityState::Running,
            phase: String::new(),
            done: None,
            total: None,
            started: None,
            eta: None,
            cancel: CancelMode::None,
            lane,
            log: None,
            queued: None,
            facts: String::new(),
        }
    }
    /// One running activity of a kind that runs one at a time.
    pub(crate) fn running(kind: ActivityKind, title: impl Into<String>, lane: Lane) -> Self {
        Self::new(kind, kind.key(), title, lane)
    }
    pub(crate) fn with_state(mut self, state: ActivityState) -> Self {
        self.state = state;
        self
    }
    pub(crate) fn with_phase(mut self, phase: impl Into<String>) -> Self {
        self.phase = phase.into();
        self
    }
    pub(crate) fn with_progress(mut self, done: Option<u64>, total: Option<u64>) -> Self {
        self.done = done;
        self.total = total;
        self
    }
    pub(crate) fn with_cancel(mut self, cancel: CancelMode) -> Self {
        self.cancel = cancel;
        self
    }
    /// 0..=1 when both counts are known.
    pub(crate) fn fraction(&self) -> Option<f32> {
        let (done, total) = (self.done?, self.total?);
        (total > 0).then(|| (done as f32 / total as f32).clamp(0.0, 1.0))
    }
    /// The short line under a title: phase, count, then time left when
    /// known, else the time it has run ("Merge · 120 / 299 · 1 min 40 s left").
    pub(crate) fn progress_line(&self, now: Instant) -> String {
        let mut parts: Vec<String> = Vec::new();
        if !self.phase.is_empty() {
            parts.push(self.phase.clone());
        }
        if let (Some(done), Some(total)) = (self.done, self.total) {
            parts.push(format!("{done} / {total}"));
        }
        if let Some(eta) = self.eta {
            parts.push(format!("{} left", crate::render_eta::spoken(eta)));
        } else if let Some(started) = self.started {
            let seconds = now.saturating_duration_since(started).as_secs();
            parts.push(format!("{}:{:02}", seconds / 60, seconds % 60));
        }
        parts.join(" · ")
    }
    /// Whether the activity still holds the user's attention (not finished).
    pub(crate) fn active(&self) -> bool {
        !self.state.terminal()
    }
    pub(crate) fn public(&self, now: Instant) -> Value {
        let mut value = json!({
            "id": self.id, "kind": self.kind, "title": self.title, "stack": self.stack,
            "state": self.state.name(), "phase": self.phase, "done": self.done, "total": self.total,
            "elapsed_seconds": self.started.map(|s| now.saturating_duration_since(s).as_secs_f64()),
            "eta_seconds": self.eta.map(|e| e.as_secs_f64()),
            "cancel": self.cancel, "lane": self.lane, "log": self.log, "queued": self.queued,
            "facts": self.facts,
        });
        match &self.state {
            ActivityState::Waiting { for_what, gives_up } => {
                value["waiting_for"] = json!(for_what);
                value["gives_up_seconds"] =
                    json!(gives_up.map(|g| g.saturating_duration_since(now).as_secs_f64()));
            }
            ActivityState::NeedsYou { message, action } => {
                value["message"] = json!(message);
                value["action"] = json!(action);
            }
            ActivityState::Stopped { message, kept } => {
                value["message"] = json!(message);
                value["kept"] = json!(kept);
            }
            ActivityState::Done { summary, next } => {
                value["summary"] = json!(summary);
                value["next"] = json!(next);
            }
            ActivityState::Running => {}
        }
        value
    }
}

/// FNV-1a of the kind and key: stable across frames and runs.
pub(crate) fn activity_id(kind: ActivityKind, key: &str) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325u64;
    for byte in [kind as u8].iter().chain(key.as_bytes()) {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    hash
}

/// A finished activity, as the tray's "Earlier" list and the file keep it.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct HistoryEntry {
    pub kind: ActivityKind,
    pub title: String,
    #[serde(default)]
    pub stack: Option<NodeId>,
    /// "done", "stopped" or "needs_you".
    pub outcome: String,
    pub summary: String,
    /// Unix seconds.
    pub finished: u64,
    #[serde(default)]
    pub took_seconds: Option<f64>,
    #[serde(default)]
    pub action: Option<ActionId>,
    #[serde(default)]
    pub log: Option<PathBuf>,
}

/// The frame's activities and the history. Per frame it touches only this
/// frame's and last frame's lists (their capacity is reused); history grows
/// only when a terminal state first appears.
#[derive(Default)]
pub(crate) struct Activities {
    current: Vec<ActivityStatus>,
    previous: Vec<ActivityStatus>,
    history: VecDeque<HistoryEntry>,
    recorded: VecDeque<(u64, u64)>,
    revision: u64,
    history_revision: u64,
}

impl Activities {
    pub(crate) fn with_history(history: VecDeque<HistoryEntry>) -> Self {
        let mut activities = Self {
            history,
            ..Self::default()
        };
        activities.trim();
        activities
    }
    /// Start a frame's reports.
    pub(crate) fn begin(&mut self) {
        std::mem::swap(&mut self.current, &mut self.previous);
        self.current.clear();
    }
    pub(crate) fn report(&mut self, status: ActivityStatus) {
        self.current.push(status);
    }
    /// Close the frame: record terminal states once, note changes.
    pub(crate) fn end(&mut self, now: Instant, unix: u64) {
        let changed = self.current.len() != self.previous.len()
            || self.current.iter().zip(&self.previous).any(|(a, b)| {
                a.id != b.id
                    || std::mem::discriminant(&a.state) != std::mem::discriminant(&b.state)
                    || a.done != b.done
                    || a.phase != b.phase
            });
        if changed {
            self.revision = self.revision.wrapping_add(1);
        }
        for index in 0..self.current.len() {
            let status = &self.current[index];
            let (outcome, summary, action) = match &status.state {
                ActivityState::Done { summary, next } => ("done", summary.clone(), next.clone()),
                ActivityState::Stopped { message, kept } => (
                    "stopped",
                    match kept {
                        Some(kept) => format!("{message} · {kept}"),
                        None => message.clone(),
                    },
                    None,
                ),
                ActivityState::NeedsYou { message, action } => {
                    ("needs_you", message.clone(), action.clone())
                }
                _ => continue,
            };
            let mark = (
                status.id,
                activity_id(status.kind, &format!("{outcome}:{summary}")),
            );
            if self.recorded.contains(&mark) {
                continue;
            }
            if self.recorded.len() == MAX_RECORDED {
                self.recorded.pop_front();
            }
            self.recorded.push_back(mark);
            let entry = HistoryEntry {
                kind: status.kind,
                title: status.title.clone(),
                stack: status.stack,
                outcome: outcome.into(),
                summary,
                finished: unix,
                took_seconds: status
                    .started
                    .map(|s| now.saturating_duration_since(s).as_secs_f64()),
                action,
                log: status.log.clone(),
            };
            self.record(entry);
        }
    }
    /// Add a finished activity directly (a queue entry, a reconciled run).
    pub(crate) fn record(&mut self, entry: HistoryEntry) {
        self.history.push_front(entry);
        self.trim();
        self.history_revision = self.history_revision.wrapping_add(1);
        self.revision = self.revision.wrapping_add(1);
    }
    fn trim(&mut self) {
        self.history.truncate(MAX_HISTORY);
    }
    /// This frame's activities, in report order.
    pub(crate) fn statuses(&self) -> &[ActivityStatus] {
        &self.current
    }
    pub(crate) fn find(&self, id: u64) -> Option<&ActivityStatus> {
        self.current.iter().find(|s| s.id == id)
    }
    #[cfg(test)]
    pub(crate) fn running(&self) -> impl Iterator<Item = &ActivityStatus> {
        self.current
            .iter()
            .filter(|s| matches!(s.state, ActivityState::Running))
    }
    pub(crate) fn waiting(&self) -> impl Iterator<Item = &ActivityStatus> {
        self.current
            .iter()
            .filter(|s| matches!(s.state, ActivityState::Waiting { .. }))
    }
    /// What is under way or waiting for the user: everything not finished.
    pub(crate) fn active(&self) -> impl Iterator<Item = &ActivityStatus> {
        self.current.iter().filter(|s| s.active())
    }
    /// Whether a Heavy-lane activity is running (the lane is serial).
    pub(crate) fn heavy_busy(&self) -> bool {
        self.current
            .iter()
            .any(|s| s.lane == Lane::Heavy && matches!(s.state, ActivityState::Running))
    }
    /// Newest first.
    pub(crate) fn history(&self) -> &VecDeque<HistoryEntry> {
        &self.history
    }
    /// Changes when the list or a state changes.
    #[cfg(test)]
    pub(crate) fn revision(&self) -> u64 {
        self.revision
    }
    /// Changes when history gains an entry; the store saves on it.
    pub(crate) fn history_revision(&self) -> u64 {
        self.history_revision
    }
    /// The agent snapshot's additive `activities` key.
    pub(crate) fn public(&self, now: Instant, history: usize) -> Value {
        json!({
            "current": self.current.iter().map(|s| s.public(now)).collect::<Vec<_>>(),
            "history": self.history.iter().take(history.min(64)).collect::<Vec<_>>(),
            "history_total": self.history.len(),
        })
    }
}

/// Quiet mode: while it is on (the Preferences switch, default on), hold the
/// Heavy lane's next start while a full-screen program is in front.
/// Captures and transfers never wait. The foreground is read at most every
/// `QUIET_POLL`, and only while Quiet is on.
pub(crate) struct QuietMode {
    /// The Preferences switch.
    pub enabled: bool,
    detected: bool,
    checked: Option<Instant>,
    probe: fn() -> bool,
}
pub(crate) const QUIET_POLL: Duration = Duration::from_secs(2);
impl Default for QuietMode {
    fn default() -> Self {
        Self {
            enabled: true,
            detected: false,
            checked: None,
            probe: full_screen_in_front,
        }
    }
}
impl QuietMode {
    #[cfg(test)]
    pub(crate) fn with_probe(probe: fn() -> bool) -> Self {
        Self {
            probe,
            ..Self::default()
        }
    }
    /// Whether heavy work waits now; reads the foreground on a timer.
    pub(crate) fn holds(&mut self, now: Instant) -> bool {
        if !self.enabled {
            self.detected = false;
            return false;
        }
        if self
            .checked
            .is_none_or(|at| now.saturating_duration_since(at) >= QUIET_POLL)
        {
            self.checked = Some(now);
            self.detected = (self.probe)();
        }
        self.detected
    }
    /// The last reading, without probing.
    pub(crate) fn full_screen(&self) -> bool {
        self.detected
    }
    /// Why heavy work waits, for a Waiting state.
    pub(crate) fn reason(&self) -> Option<&'static str> {
        (self.enabled && self.detected)
            .then_some("the full-screen program in front to close (Quiet)")
    }
}

/// `SHQueryUserNotificationState`: a Direct3D full-screen program, or a
/// full-screen program the shell reports busy, holds heavy work (plan 6.6).
#[cfg(windows)]
pub(crate) fn full_screen_in_front() -> bool {
    use windows_sys::Win32::UI::Shell::{
        QUERY_USER_NOTIFICATION_STATE, QUNS_BUSY, QUNS_RUNNING_D3D_FULL_SCREEN,
        SHQueryUserNotificationState,
    };
    let mut state: QUERY_USER_NOTIFICATION_STATE = 0;
    // SAFETY: one out-parameter of the declared type, alive for the call.
    let result = unsafe { SHQueryUserNotificationState(&mut state) };
    result >= 0 && (state == QUNS_RUNNING_D3D_FULL_SCREEN || state == QUNS_BUSY)
}
#[cfg(not(windows))]
pub(crate) fn full_screen_in_front() -> bool {
    false
}

// ---------- adapters for crate-level owners ----------

/// A capture tool's engine job (`capture-tools.rs` `Slot`): running, or its
/// kept result as a terminal state.
pub(crate) fn tool_status(
    kind: ActivityKind,
    slot: &crate::capture_workspace::tools::Slot,
    lane: Lane,
) -> Option<ActivityStatus> {
    let folder = slot.folder.as_ref()?;
    let key = folder.to_string_lossy();
    let name = folder
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default();
    let title = format!("{} · {name}", kind.label());
    let status = ActivityStatus::new(kind, &key, title, lane);
    if let Some(job) = &slot.job {
        // Compaction rewrites a capture: once started it runs to the end.
        let cancel = if kind == ActivityKind::CompactApply {
            CancelMode::None
        } else {
            CancelMode::Kill
        };
        let mut status = status.with_phase("Running the engine").with_cancel(cancel);
        status.started = Instant::now().checked_sub(job.elapsed());
        return Some(status);
    }
    let state = match slot.result.as_ref()? {
        Ok(value) => ActivityState::Done {
            summary: value["summary"]
                .as_str()
                .map_or_else(|| "Finished".to_owned(), str::to_owned),
            next: None,
        },
        Err(message) if message == crate::capture_workspace::tools::CANCELLED => {
            ActivityState::Stopped {
                message: "Cancelled".into(),
                kept: None,
            }
        }
        Err(message) => ActivityState::NeedsYou {
            message: message.clone(),
            action: None,
        },
    };
    Some(status.with_state(state))
}

/// The step calibration (`capture-tools.rs` `Calibration`): its waiting
/// stages give up at their deadlines.
pub(crate) fn calibration_status(
    calibration: &crate::capture_workspace::tools::Calibration,
    key: &str,
) -> Option<ActivityStatus> {
    use crate::capture_workspace::tools::Calibration as C;
    let status = ActivityStatus::new(
        ActivityKind::Calibration,
        key,
        ActivityKind::Calibration.label(),
        Lane::Camera,
    );
    let (phase, state) = match calibration {
        C::Idle => return None,
        C::Switching { deadline, .. } => (
            "Switching the camera to one RAW a plane",
            ActivityState::Waiting {
                for_what: "the camera to switch to one RAW a plane".into(),
                gives_up: Some(*deadline),
            },
        ),
        C::Capturing { deadline, .. } => (
            "Capturing the survey",
            ActivityState::Waiting {
                for_what: "the survey's RAWs".into(),
                gives_up: Some(*deadline),
            },
        ),
        C::Measuring { .. } => ("Measuring the survey", ActivityState::Running),
        C::Restoring { deadline, .. } => (
            "Restoring four RAWs a plane",
            ActivityState::Waiting {
                for_what: "the camera to return to four RAWs a plane".into(),
                gives_up: Some(*deadline),
            },
        ),
        C::Done(value) => (
            "",
            ActivityState::Done {
                summary: value["summary"]
                    .as_str()
                    .map_or_else(|| "Step calibrated".to_owned(), str::to_owned),
                next: Some(ActionId::OpenCapture),
            },
        ),
        C::Failed(message) => (
            "",
            ActivityState::NeedsYou {
                message: message.clone(),
                action: Some(ActionId::OpenCapture),
            },
        ),
    };
    Some(
        status
            .with_phase(phase)
            .with_state(state)
            .with_cancel(if calibration.running() {
                CancelMode::Cooperative
            } else {
                CancelMode::None
            }),
    )
}

/// The capture checker (`capture-follow.rs` `Follower`).
pub(crate) fn follow_status(
    follower: &crate::capture_workspace::follow::Follower,
) -> ActivityStatus {
    use crate::capture_workspace::follow::State;
    let progress = follower.progress();
    let tally = &progress.tally;
    let mut detail = format!(
        "{} checked as they arrived",
        plural(progress.checked, "plane", "planes")
    );
    // The words of the in-flight feed (capture-flight.rs): how retakes went
    // and how many planes the stack folds to one shot.
    if tally.retaken() > 0 {
        detail.push_str(&format!(
            " · {} retaken, {} then passed",
            tally.retaken(),
            tally.retake_passed
        ));
    }
    if tally.single_shot() > 0 {
        detail.push_str(&format!(" · {} stacked from one shot", tally.single_shot()));
    }
    if tally.incomplete > 0 {
        detail.push_str(&format!(" · {} incomplete", tally.incomplete));
    }
    let state = match &follower.state {
        State::Running if follower.observing => ActivityState::Waiting {
            for_what: "the other window checking this capture".into(),
            gives_up: None,
        },
        State::Running => ActivityState::Running,
        State::Finished => ActivityState::Done {
            summary: detail.clone(),
            next: Some(ActionId::OpenRun {
                run: follower.run.clone(),
            }),
        },
        State::Failed(message) => ActivityState::NeedsYou {
            message: message.clone(),
            action: Some(ActionId::ShowLog {
                path: follower.log.clone(),
            }),
        },
        State::Stopped(message) => ActivityState::Stopped {
            message: message.clone(),
            kept: Some(detail.clone()),
        },
    };
    let mut status = ActivityStatus::new(
        ActivityKind::CaptureFollow,
        &follower.run.to_string_lossy(),
        ActivityKind::CaptureFollow.label(),
        Lane::Background,
    )
    .with_state(state)
    .with_phase(detail)
    .with_cancel(if follower.running() && !follower.observing {
        CancelMode::Kill
    } else {
        CancelMode::None
    });
    status.started = Some(follower.started);
    status.log = Some(follower.log.clone());
    status
}

/// A camera metadata read in flight.
pub(crate) fn metadata_status(
    metadata: &crate::camera_metadata::CameraMetadata,
) -> Option<ActivityStatus> {
    metadata.is_loading().then(|| {
        ActivityStatus::new(
            ActivityKind::Metadata,
            "camera-metadata",
            "Reading camera metadata",
            Lane::Background,
        )
        .with_cancel(CancelMode::Cooperative)
    })
}

/// The render in flight, from its progress and the ETA estimate.
#[allow(clippy::too_many_arguments)]
pub(crate) fn render_status(
    key: &str,
    title: &str,
    stack: Option<NodeId>,
    progress: &crate::pipeline::PipelineProgress,
    cancelling: bool,
    started: Option<Instant>,
    eta: Option<Duration>,
    log: Option<PathBuf>,
) -> ActivityStatus {
    let mut status = ActivityStatus::new(ActivityKind::Stack, key, title, Lane::Heavy)
        .with_phase(if cancelling {
            "Stopping"
        } else {
            progress.stage.title()
        })
        .with_progress(
            progress.frames_processed.map(|n| n as u64),
            progress.frames_total.map(|n| n as u64),
        )
        .with_cancel(if cancelling {
            CancelMode::None
        } else {
            CancelMode::Kill
        });
    status.stack = stack;
    status.started = started;
    status.eta = eta;
    status.log = log;
    status
}

pub(crate) fn plural(count: usize, one: &str, many: &str) -> String {
    format!("{count} {}", if count == 1 { one } else { many })
}

#[cfg(test)]
#[path = "activity-tests.rs"]
mod tests;
