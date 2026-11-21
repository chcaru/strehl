//! Activities (implementation plan 6.6), step 1: a read-only view of every
//! long task the desktop is running, gathered each frame from the state the
//! tasks already keep. Nothing here starts, queues or owns work yet; P5 moves
//! each task into a per-job struct behind this same status type.
use crate::workspace_history::NodeId;
use serde_json::{Value, json};
use std::time::{Duration, Instant};

#[allow(dead_code)] // P5 adds the camera tools' activities.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
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
    /// list: today these hold the workspace while they run).
    Open,
}
impl ActivityKind {
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
        }
    }
}

/// An action an activity offers. Kept as a name until P5's action table.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct ActionId(pub &'static str);

#[allow(dead_code)] // P5's queue sets the other states.
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

/// Heavy work is serial and holds in Quiet mode; captures never wait.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Lane {
    Heavy,
    Background,
    Camera,
}
#[allow(dead_code)] // `Kill` arrives with P5's owned engine children.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum CancelMode {
    None,
    Cooperative,
    Kill,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ActivityStatus {
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
    pub log: Option<std::path::PathBuf>,
    /// Facts that used to sit on the status bar: workers, RAW count, size.
    pub facts: String,
}
impl ActivityStatus {
    pub(crate) fn running(kind: ActivityKind, title: impl Into<String>, lane: Lane) -> Self {
        Self {
            id: kind as u64,
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
            facts: String::new(),
        }
    }
    /// Done as a fraction, when the task counts its work.
    pub(crate) fn fraction(&self) -> Option<f32> {
        match (self.done, self.total) {
            (Some(done), Some(total)) if total > 0 => {
                Some((done as f32 / total as f32).clamp(0.0, 1.0))
            }
            _ => None,
        }
    }
    /// The short line under the title: phase, count and elapsed time.
    pub(crate) fn progress_line(&self, now: Instant) -> String {
        let mut parts: Vec<String> = Vec::new();
        if !self.phase.is_empty() {
            parts.push(self.phase.clone());
        }
        if let (Some(done), Some(total)) = (self.done, self.total) {
            parts.push(format!("{done} / {total}"));
        }
        if let Some(started) = self.started {
            let seconds = now.saturating_duration_since(started).as_secs();
            parts.push(format!("{}:{:02}", seconds / 60, seconds % 60));
        }
        parts.join(" · ")
    }
    pub(crate) fn snapshot(&self) -> Value {
        json!({"kind":self.kind.key(),"title":self.title,"stack":self.stack,
            "state":match &self.state {
                ActivityState::Waiting { .. } => "waiting",
                ActivityState::Running => "running",
                ActivityState::NeedsYou { .. } => "needs_you",
                ActivityState::Stopped { .. } => "stopped",
                ActivityState::Done { .. } => "done",
            },
            "phase":self.phase,"done":self.done,"total":self.total,
            "elapsed_seconds":self.started.map(|s| s.elapsed().as_secs_f64()),
            "cancel":match self.cancel { CancelMode::None => "none", CancelMode::Cooperative => "cooperative", CancelMode::Kill => "kill" },
            "lane":match self.lane { Lane::Heavy => "heavy", Lane::Background => "background", Lane::Camera => "camera" }})
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn progress_reads_phase_count_and_elapsed_time() {
        let now = Instant::now();
        let mut stack = ActivityStatus::running(ActivityKind::Stack, "Stacking", Lane::Heavy);
        assert_eq!(stack.fraction(), None);
        assert_eq!(stack.progress_line(now), "");
        stack.phase = "Build the stack".into();
        stack.done = Some(34);
        stack.total = Some(299);
        stack.started = now.checked_sub(Duration::from_secs(72));
        assert!((stack.fraction().unwrap() - 34.0 / 299.0).abs() < 1e-6);
        assert_eq!(
            stack.progress_line(now),
            "Build the stack · 34 / 299 · 1:12"
        );
        let snapshot = stack.snapshot();
        assert_eq!(snapshot["kind"], "stack");
        assert_eq!(snapshot["state"], "running");
        assert_eq!(snapshot["lane"], "heavy");
        stack.total = Some(0);
        assert_eq!(stack.fraction(), None, "an empty total is not progress");
    }
}
