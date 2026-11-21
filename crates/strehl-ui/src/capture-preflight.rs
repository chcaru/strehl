//! Pre-flight (Studio 2, 7.4): the single source of truth for Start.
//!
//! [`start_blockers`] lists, in the order to resolve them, every reason
//! Start is not available. The Start button is enabled exactly when the list
//! is empty, the first entry is shown beside it, and the pre-flight strip
//! draws all of them as chips. It covers the condition the Start button used
//! before (fresh, editable, both marks, no plan error, no unapplied edits,
//! no focus move, capacity, the receiver or the simulator, no request in
//! flight, no schedule editor open) and adds what the host can now say before
//! Start (H1: the exposure program) and what the desktop itself is doing
//! with the camera (a calibration or a test shot).
use super::CaptureWorkspace;
use crate::capture_client::Snapshot;

/// Which condition a [`Blocker`] stands for (stable; tests and the strip
/// key on it).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Check {
    /// The Pi's state is not fresh.
    Offline,
    /// The Pi's state could not be read.
    HostState,
    /// No camera is connected.
    Camera,
    /// The camera needs recovery.
    Failure,
    /// The camera is busy or a sequence runs.
    NotEditable,
    /// The exposure program, ISO or shutter cannot start a stack (H1).
    Exposure,
    StartMark,
    EndMark,
    /// The host rejects the plan.
    Plan,
    /// Step or settle edits are not applied.
    Edits,
    /// A focus move is pending or in flight.
    Focus,
    /// The PC's disk cannot hold the stack.
    Capacity,
    /// The PC's receiver is not ready.
    Receiver,
    /// A step calibration is using the camera.
    Calibration,
    /// A test shot is using the camera.
    TestShot,
    /// A request is being sent.
    Sending,
    /// The schedule editor is open.
    Schedule,
}

/// What resolves a blocker, when one action does.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Fix {
    /// Open the connection settings.
    ConnectionSettings,
    ConnectCamera,
    RecoverCamera,
    MarkStart,
    MarkEnd,
    ApplyEdits,
    StartReceiver,
    /// Stop waiting for the desktop's own camera work.
    StopWaiting,
}

/// One reason Start is not available.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Blocker {
    pub check: Check,
    /// A one- or two-word chip label.
    pub chip: &'static str,
    /// What is wrong and what to do, as a sentence.
    pub sentence: String,
    pub fix: Option<Fix>,
}

fn blocker(
    check: Check,
    chip: &'static str,
    sentence: impl Into<String>,
    fix: Option<Fix>,
) -> Blocker {
    Blocker {
        check,
        chip,
        sentence: sentence.into(),
        fix,
    }
}

/// Why the PC cannot hold the planned stack, if it cannot: the host's own
/// capacity rule over the receiver's free space. Not judged in the simulator,
/// nor without a ready receiver (that is its own blocker).
pub(crate) fn capacity_error(s: &Snapshot) -> Option<String> {
    let host = &s.host;
    if host.demo || s.receiver["ok"] != true {
        return None;
    }
    let planned = host.planned?;
    strehl_capture::capacity::check(
        s.receiver["free_bytes"].as_u64(),
        planned as usize * host.shots() as usize,
        host.raw_max_bytes
            .unwrap_or(strehl_capture::transport::MAX_RAW),
    )
    .err()
    .map(|e| e.to_string())
}

/// Every reason Start is not available now, most fundamental first. Empty
/// means Start may be sent.
pub(crate) fn start_blockers(s: &Snapshot, ui: &CaptureWorkspace) -> Vec<Blocker> {
    use Check as C;
    let mut out = Vec::new();
    let host = &s.host;
    if !s.fresh() {
        out.push(blocker(
            C::Offline,
            "Pi offline",
            s.connection_error
                .as_deref()
                .map_or("Connect to the Pi first".to_owned(), |e| {
                    format!("The Pi is not answering: {e}")
                }),
            Some(Fix::ConnectionSettings),
        ));
    }
    if let Some(e) = &s.host_error {
        out.push(blocker(C::HostState, "Host state", e.clone(), None));
    }
    if s.fresh() && s.host_error.is_none() {
        if !host.connected {
            out.push(blocker(
                C::Camera,
                "Camera",
                "Connect the camera",
                Some(Fix::ConnectCamera),
            ));
        }
        if let Some(failure) = &host.failure {
            out.push(blocker(
                C::Failure,
                "Recover",
                failure
                    .message
                    .clone()
                    .unwrap_or_else(|| "The camera needs recovery".into()),
                Some(Fix::RecoverCamera),
            ));
        } else if host.connected && !host.editable {
            out.push(blocker(
                C::NotEditable,
                "Busy",
                if host.phase.active() {
                    "A sequence is running".to_owned()
                } else {
                    format!("Wait for the camera ({})", host.phase.as_str())
                },
                None,
            ));
        }
        if host.connected
            && let Some(problem) = host.exposure_problem()
        {
            out.push(blocker(C::Exposure, "Exposure", problem, None));
        }
        if !host.start_set {
            out.push(blocker(
                C::StartMark,
                "Start mark",
                "Mark the start of the focus range",
                Some(Fix::MarkStart),
            ));
        }
        if !host.end_set {
            out.push(blocker(
                C::EndMark,
                "End mark",
                "Mark the end of the focus range",
                Some(Fix::MarkEnd),
            ));
        }
        if let Some(e) = &host.plan_error {
            out.push(blocker(C::Plan, "Plan", e.clone(), None));
        }
    }
    if ui.draft_dirty {
        out.push(blocker(
            C::Edits,
            "Edits",
            "Apply or discard the step and settle edits",
            Some(Fix::ApplyEdits),
        ));
    }
    if ui.focus_pending.is_some() || ui.focus_flight.is_some() {
        out.push(blocker(
            C::Focus,
            "Focus moving",
            "Wait for the focus move to finish",
            None,
        ));
    }
    if let Some(e) = capacity_error(s) {
        out.push(blocker(C::Capacity, "Disk", e, None));
    }
    if s.receiver["ok"] != true && !host.demo {
        out.push(blocker(
            C::Receiver,
            "Receiver",
            "Start the receiver on this PC",
            Some(Fix::StartReceiver),
        ));
    }
    if ui.calibration.running() {
        out.push(blocker(
            C::Calibration,
            "Calibrating",
            "A step calibration is using the camera",
            Some(Fix::StopWaiting),
        ));
    }
    if ui.test_shot.running() {
        out.push(blocker(
            C::TestShot,
            "Test shot",
            "A test shot is using the camera",
            Some(Fix::StopWaiting),
        ));
    }
    if s.pending {
        out.push(blocker(
            C::Sending,
            "Sending",
            "Wait for the previous request",
            None,
        ));
    }
    if ui.schedule_ui.editing() {
        out.push(blocker(
            C::Schedule,
            "Schedule",
            "Finish or close the schedule editor",
            None,
        ));
    }
    out
}

/// Whether a stack may be scheduled: every Start condition but the open
/// schedule editor, which is where scheduling happens.
pub(crate) fn can_schedule(blockers: &[Blocker]) -> bool {
    blockers.iter().all(|b| b.check == Check::Schedule)
}

#[cfg(test)]
#[path = "capture-preflight-tests.rs"]
mod tests;
