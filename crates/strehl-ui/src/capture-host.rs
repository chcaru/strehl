//! The camera host's state, typed (Studio 2, section 7.4).
//!
//! The desktop used to read every field of `/api/state` as an untyped
//! `serde_json::Value` (`s.state["editable"]`), so a misspelt key read as
//! `null` and quietly disabled or enabled a control. [`HostState`] names
//! every field the desktop reads, and is parsed once per poll on the client
//! thread. The raw value is kept beside it for pass-through and for the
//! agent snapshot, whose keys do not change.
//!
//! Parsing is strict for the fields that decide what may be sent to the
//! camera (revisions, phase, the editable and busy flags, the marks, the
//! plan, counts, the failure, the exposure values and the capability flags):
//! a host that sends one of them in a form this desktop cannot read gives a
//! [`HostState::default`] (disconnected, nothing editable) and an error the
//! screen shows, rather than a guess. Fields that only inform a display
//! (outlets, storage, schedule, survey samples, option lists) are read
//! leniently: a value of an unexpected shape reads as absent.
//!
//! Every field is `#[serde(default)]`: an older host that lacks a field
//! (`capabilities`, `error_correction`, `exposure.mode`) reads as "not
//! supported", never as an error.
use serde::{Deserialize, Deserializer, de::DeserializeOwned};
use serde_json::Value;
use strehl_capture::model::{Plan, Roi};

/// The host's phase (`strehl_capture::model::Phase`), with an `Unknown`
/// for any phase a newer host adds.
#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub(crate) enum HostPhase {
    #[default]
    Disconnected,
    Connecting,
    Ready,
    Moving,
    Scanning,
    Capturing,
    Paused,
    Complete,
    Stopped,
    Fault,
    Recovering,
    Disconnecting,
    #[serde(other)]
    Unknown,
}

impl HostPhase {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Disconnected => "disconnected",
            Self::Connecting => "connecting",
            Self::Ready => "ready",
            Self::Moving => "moving",
            Self::Scanning => "scanning",
            Self::Capturing => "capturing",
            Self::Paused => "paused",
            Self::Complete => "complete",
            Self::Stopped => "stopped",
            Self::Fault => "fault",
            Self::Recovering => "recovering",
            Self::Disconnecting => "disconnecting",
            Self::Unknown => "unknown",
        }
    }
    /// A sequence is running: a capture (also paused) or a bounds survey.
    pub fn active(self) -> bool {
        matches!(self, Self::Capturing | Self::Paused | Self::Scanning)
    }
    /// A capture is running or paused.
    pub fn capturing(self) -> bool {
        matches!(self, Self::Capturing | Self::Paused)
    }
}

/// A studio outlet's last reading (`power.light`, `power.camera`).
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Outlet {
    pub on: Option<bool>,
    pub watts: Option<f64>,
    pub error: Option<String>,
}

/// `power`: present only when the Pi has studio outlets configured.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Power {
    #[serde(deserialize_with = "lenient")]
    pub light: Outlet,
    #[serde(deserialize_with = "lenient")]
    pub camera: Outlet,
    pub warmup_seconds: Option<u64>,
    pub available: bool,
    pub can_start_camera: bool,
    pub can_stop_camera: bool,
    pub can_manage: bool,
    /// "Manage power" for stacks: warm the light first, switch both off after.
    pub manage_stack: bool,
    pub error: Option<String>,
}

/// `timer`, while a sequence has timing.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Timer {
    pub label: Option<String>,
    pub elapsed: Option<f64>,
    pub remaining: Option<f64>,
    pub finished: bool,
    pub paused: bool,
}

/// `failure`: what needs recovery.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Failure {
    pub message: Option<String>,
    pub exposure_uncertain: bool,
    pub can_reconnect: bool,
}

/// `preview`: the live view's state on the host.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct PreviewState {
    pub available: bool,
    pub fresh: bool,
    pub generation: Option<u64>,
    pub age_seconds: Option<f64>,
    pub error: Option<String>,
    pub width: Option<u32>,
    pub height: Option<u32>,
}

/// `storage.receipt`: the last RAW the PC acknowledged.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Receipt {
    pub path: Option<String>,
    pub bytes: Option<f64>,
    pub storage_bytes: Option<f64>,
    #[serde(rename = "wire_MB_per_second")]
    pub wire_mb_per_second: Option<f64>,
}

/// `storage`: the transfer report (`mode` "host-pc" or "camera-sd").
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Storage {
    pub mode: Option<String>,
    pub state: Option<String>,
    pub message: Option<String>,
    pub free_bytes: Option<u64>,
    pub pipelined: Option<bool>,
    pub captured_frames: Option<u64>,
    pub saved_frames: Option<u64>,
    /// RAWs on the host not yet acknowledged by the PC.
    pub pending_frames: Option<u64>,
    #[serde(deserialize_with = "lenient")]
    pub receipt: Option<Receipt>,
}

/// One position of the bounds survey: 24 tile scores (6 x 4) of the live
/// JPEG. A focusing aid, not a RAW measurement.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct SurveySample {
    pub position: u16,
    pub scores: Vec<Option<f32>>,
}

/// The survey's suggested bounds.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Suggestion {
    pub start: u16,
    pub end: u16,
    pub supported_tiles: usize,
    pub clipped: bool,
    pub explanation: Option<String>,
}

/// `exposure`: present while the camera reports ISO.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Exposure {
    pub iso: Option<u64>,
    /// Sony's code: `numerator << 16 | denominator`
    /// (`strehl_capture::timing::shutter_seconds`).
    pub shutter: Option<u64>,
    pub f_number: Option<u64>,
    #[serde(deserialize_with = "lenient")]
    pub iso_options: Vec<u64>,
    #[serde(deserialize_with = "lenient")]
    pub shutter_options: Vec<u64>,
    pub writable: bool,
    /// H1: `M`, `P`, `A`, `S` or `other`; absent from older hosts.
    pub mode: Option<String>,
    /// H1: why these settings cannot start a stack (M mode, fixed ISO, a
    /// timed shutter); absent when they can, and from older hosts.
    pub problem: Option<String>,
}

/// `schedule.job`.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct ScheduleJob {
    pub id: Option<String>,
    pub start_at: Option<i64>,
    pub stage: Option<String>,
    pub message: Option<String>,
}

/// `schedule`: present when the Pi supports scheduled stacks.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Schedule {
    #[serde(deserialize_with = "lenient")]
    pub job: Option<ScheduleJob>,
    pub error: Option<String>,
}

/// `starting`: what a capture does before its first exposure (the light's
/// warm-up, the approach move). Absent from older hosts and once begun.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Starting {
    /// `"light"` or `"approach"`.
    pub stage: Option<String>,
    pub elapsed: Option<f64>,
    /// How long the stage takes, when known.
    pub seconds: Option<f64>,
}

/// `capabilities`: what the host accepts beyond the original protocol.
/// Absent (older hosts) means none.
#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(default)]
pub(crate) struct Capabilities {
    /// `capture_positions` with `kind: "test"` (H2).
    pub test_shot: bool,
    /// `exposure.mode` and `exposure.problem` (H1).
    pub exposure_check: bool,
    /// `error_correction` takes `max_retakes`; `retakes.max` (h-retake).
    pub max_retakes: bool,
    /// `queue_retakes`; `retakes.queued` and `retakes.followup` (h-retake).
    pub queue_retakes: bool,
    /// `new_plan`: clear the marks, the subject box and the survey.
    pub new_plan: bool,
    /// `subject`: an outline kept in the plan and manifest (plan S1).
    pub subject: bool,
    /// `highlight`, `shutters` per position and `queue_pass` (plan X3).
    pub exposure_tiers: bool,
    /// `lens_travel`; a move past an end stops there (2026-11-24).
    pub lens_travel: bool,
}

/// `lens_travel`: the ends the lens stopped at when sent past them; `None`
/// where an end has not been met (the camera's property admits 0-65535
/// whatever the lens).
#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(default)]
pub(crate) struct LensTravel {
    pub near: Option<u16>,
    pub far: Option<u16>,
}

impl LensTravel {
    /// The focus range a move can reach: the known ends, else the
    /// property's whole range.
    pub fn range(&self) -> (u16, u16) {
        (self.near.unwrap_or(0), self.far.unwrap_or(u16::MAX))
    }
}

/// `retakes` (h-retake): the setting and the manual retakes in hand.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Retakes {
    /// Error correction's retakes of one plane.
    pub max: Option<u64>,
    /// The most it may be set to.
    pub limit: Option<u64>,
    /// The current (or last) capture takes manual retakes.
    pub accepted: bool,
    /// Planes asked for during the capture and not yet taken.
    #[serde(deserialize_with = "lenient")]
    pub queued: Vec<u64>,
    /// The current (or last) capture's run folder name.
    pub run: Option<String>,
    /// Retakes after the capture, while they run.
    #[serde(deserialize_with = "lenient")]
    pub followup: Option<Followup>,
}

/// `retakes.followup`.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct Followup {
    pub planes: Vec<u64>,
    pub taken: u64,
    pub skipped: u64,
}

/// Every field of `/api/state` the desktop reads.
#[derive(Clone, Debug, Default, Deserialize, PartialEq)]
#[serde(default)]
pub(crate) struct HostState {
    pub camera_revision: Option<u64>,
    pub plan_revision: Option<u64>,
    pub sequence_id: Option<u64>,
    pub phase: HostPhase,
    pub connected: bool,
    /// A camera command is in flight on the host.
    pub busy: bool,
    pub editable: bool,
    pub message: Option<String>,
    /// The host runs its simulator.
    pub demo: bool,
    #[serde(deserialize_with = "lenient")]
    pub power: Option<Power>,
    pub position: Option<u16>,
    pub plan: Option<Plan>,
    pub start_set: bool,
    pub end_set: bool,
    pub roi: Option<Roi>,
    /// Planes of the marked plan.
    pub planned: Option<u64>,
    pub plan_error: Option<String>,
    pub initial_seconds: Option<f64>,
    /// Planes done in the current sequence.
    pub completed: u64,
    pub saved: Option<u64>,
    pub total: u64,
    pub timer: Option<Timer>,
    /// 0 none, 1 pause pending, 2 stop pending.
    pub pending_control: u8,
    #[serde(deserialize_with = "lenient")]
    pub storage: Storage,
    pub storage_required_bytes: Option<u64>,
    pub storage_error: Option<String>,
    pub raw_max_bytes: Option<u64>,
    pub shots_per_plane: Option<u64>,
    #[serde(deserialize_with = "lenient")]
    pub pixel_shift_options: Vec<u64>,
    pub camera_model: Option<String>,
    pub failure: Option<Failure>,
    pub battery: Option<u64>,
    pub card_remaining: Option<u64>,
    pub preview: PreviewState,
    #[serde(deserialize_with = "lenient")]
    pub magnifier_ratios: Vec<u32>,
    pub magnifier_current: Option<u64>,
    #[serde(deserialize_with = "lenient")]
    pub suggestion: Option<Suggestion>,
    #[serde(deserialize_with = "lenient")]
    pub samples: Vec<SurveySample>,
    pub exposure: Option<Exposure>,
    pub usb_speed_mbps: Option<u64>,
    #[serde(deserialize_with = "lenient")]
    pub schedule: Option<Schedule>,
    /// `None` from a host without error correction.
    pub error_correction: Option<bool>,
    pub capabilities: Capabilities,
    #[serde(deserialize_with = "lenient")]
    pub starting: Option<Starting>,
    /// Absent from an older host (h-retake).
    #[serde(deserialize_with = "lenient")]
    pub retakes: Option<Retakes>,
    /// The lens's ends as found; absent from an older host.
    #[serde(deserialize_with = "lenient")]
    pub lens_travel: LensTravel,
}

/// The top-level keys [`HostState`] reads. A test holds this against the
/// host's own state, so a field the host adds or renames is noticed.
#[cfg(test)]
pub(crate) const KNOWN_KEYS: &[&str] = &[
    "camera_revision",
    "plan_revision",
    "sequence_id",
    "phase",
    "connected",
    "busy",
    "editable",
    "message",
    "demo",
    "power",
    "position",
    "plan",
    "start_set",
    "end_set",
    "roi",
    "planned",
    "plan_error",
    "initial_seconds",
    "completed",
    "saved",
    "total",
    "timer",
    "pending_control",
    "storage",
    "storage_required_bytes",
    "storage_error",
    "raw_max_bytes",
    "shots_per_plane",
    "pixel_shift_options",
    "camera_model",
    "failure",
    "battery",
    "card_remaining",
    "preview",
    "magnifier_ratios",
    "magnifier_current",
    "suggestion",
    "samples",
    "exposure",
    "usb_speed_mbps",
    "schedule",
    "error_correction",
    "capabilities",
    "retakes",
    "starting",
    "lens_travel",
];

impl HostState {
    /// Parses a state reply; `Err` names the field this desktop cannot read.
    pub fn parse(state: &Value) -> Result<Self, String> {
        if state.is_null() {
            return Ok(Self::default());
        }
        Self::deserialize(state).map_err(|e| format!("{e}"))
    }
    /// RAWs a plane: 1, or 4 with pixel shift.
    pub fn shots(&self) -> u64 {
        self.shots_per_plane.unwrap_or(1)
    }
    pub fn bounds_set(&self) -> bool {
        self.start_set && self.end_set
    }
    /// The marked start and end as the host holds them.
    pub fn plan_bounds(&self) -> (u16, u16) {
        self.plan.as_ref().map_or((0, 0), |p| (p.start, p.end))
    }
    pub fn offers_four_shot(&self) -> bool {
        self.pixel_shift_options.contains(&4)
    }
    pub fn schedule_stage(&self) -> Option<&str> {
        self.schedule.as_ref()?.job.as_ref()?.stage.as_deref()
    }
    /// Error correction's retakes of a plane for this host's runs: its
    /// setting, or the fixed two of a host without one (h-retake).
    pub fn max_retakes(&self) -> u32 {
        self.retakes
            .as_ref()
            .and_then(|r| r.max)
            .filter(|_| self.capabilities.max_retakes)
            .map_or(strehl_capture::worker::MAX_RETAKES as u32, |m| m as u32)
    }
    /// The host takes manual retakes of the current (or last) capture.
    pub fn takes_manual_retakes(&self) -> bool {
        self.capabilities.queue_retakes && self.retakes.as_ref().is_some_and(|r| r.accepted)
    }
    /// Planes asked to be taken again and not taken yet: queued during the
    /// capture, or in the retakes after it.
    pub fn retakes_in_hand(&self) -> Vec<u64> {
        let Some(r) = &self.retakes else {
            return Vec::new();
        };
        let mut planes = r.queued.clone();
        if let Some(f) = &r.followup {
            let done = (f.taken + f.skipped) as usize;
            planes.extend(f.planes.iter().skip(done));
        }
        planes
    }
    pub fn exposure_problem(&self) -> Option<&str> {
        self.exposure.as_ref()?.problem.as_deref()
    }
    /// The run folder of the last RAW the PC acknowledged, from its receipt
    /// path (without a `\\?\` prefix).
    pub fn last_receipt_run(&self) -> Option<std::path::PathBuf> {
        let path = self.storage.receipt.as_ref()?.path.as_deref()?;
        let parent = std::path::Path::new(path).parent()?;
        Some(std::path::PathBuf::from(
            parent.to_string_lossy().trim_start_matches(r"\\?\"),
        ))
    }
}

/// A field that only informs a display: a value of another shape reads as
/// absent instead of failing the whole state.
fn lenient<'de, D, T>(deserializer: D) -> Result<T, D::Error>
where
    D: Deserializer<'de>,
    T: DeserializeOwned + Default,
{
    let value = Value::deserialize(deserializer)?;
    Ok(serde_json::from_value(value).unwrap_or_default())
}

#[cfg(test)]
#[path = "capture-host-tests.rs"]
mod tests;
