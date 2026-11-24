//! A capture in flight (Studio 2, 7.4; mockup `flight.html`): the headline
//! (plane, bar, time left, finishing time, RAWs and retakes), the plane
//! view's place (`capture-plane-view.rs` draws it), the feed of every
//! checked group from the checker's journal, and the health column with the "when it finishes"
//! switches, Pause, Stop and Glance. Once the capture has ended the same
//! view says what happened to every plane, until the user goes back to
//! planning.
//!
//! The view takes [`FlightInputs`] and a [`FlightView`] (its state across
//! frames) and returns [`FlightIntent`]s. The numbers are computed by the
//! pure functions here ([`headline`], [`health`], [`feed_row`],
//! [`summary_sentence`], [`flight_ticks`]), which the glance mode shares.
//!
//! Retakes are the host's error correction (`strehl_capture::worker`): a
//! group the PC's checker demotes with `retake: true` is taken again after
//! the next plane, at most the run's own number of times (the host's
//! `retakes.max`, 2 on an older host); the plane's last group is the one the
//! stack uses, folded to its first shot when it failed. A plane left from
//! one shot can be retaken by hand ("Retake" on its row), during the capture
//! or after it; a run of such planes too long for the calibrated overlap is
//! named above the feed with what it costs and "Retake planes A–B"
//! (h-retake: [`risk_spans`], [`RiskSpan`]).
use std::{collections::VecDeque, sync::Arc, time::Instant};

use eframe::egui::{self, Align2, Rect, Sense, Ui};

use super::follow::{FeedItem, Progress, Tally, Verdict};
use super::rail::{FlightTicks, TickState};
use super::style::{self, ButtonKind, CapturePalette, Mark};
use crate::capture_client::{Snapshot, host::HostPhase};

/// The headline's numbers.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct Headline {
    /// Planes done (each plane once, however often it was taken), and
    /// planned.
    pub plane: u64,
    pub total: u64,
    pub fraction: f32,
    pub per_plane: Option<f64>,
    /// Every RAW the camera has taken, retakes included.
    pub raws_taken: u64,
    /// Of those, the RAWs of retakes.
    pub raws_for_retakes: u64,
    /// Retakes checked (groups beyond each plane's first), and the planes
    /// they were of.
    pub retakes: u64,
    pub retaken_planes: u64,
    pub elapsed: Option<f64>,
    /// The host's estimate of the time left (see [`LeftClock`] for the one
    /// shown).
    pub left: Option<f64>,
    pub paused: bool,
    /// Before the first exposure: what the capture is doing, and how far
    /// through it is when that is known (owner feedback, 2026-11-23).
    pub starting: Option<(String, Option<f32>)>,
}

/// What a capture is doing before its first exposure: the host's
/// `starting` (light warm-up, approach), else, from an older host, its
/// message while nothing has been taken yet.
pub(crate) fn starting(s: &Snapshot) -> Option<(String, Option<f32>)> {
    let host = &s.host;
    if host.phase != HostPhase::Capturing {
        return None;
    }
    if let Some(start) = &host.starting {
        let elapsed = start.elapsed.unwrap_or(0.0).max(0.0);
        return Some(match (start.stage.as_deref(), start.seconds) {
            (Some("light"), Some(total)) if total >= 0.5 => (
                format!(
                    "Warming the light: {:.0} of {:.0} s",
                    elapsed.min(total),
                    total
                ),
                Some((elapsed / total).clamp(0.0, 1.0) as f32),
            ),
            (Some("light"), _) => ("The light is warm".into(), None),
            (Some("approach"), _) => (
                format!("Moving to the start: the approach ({elapsed:.0} s)"),
                None,
            ),
            _ => ("Starting".into(), None),
        });
    }
    let nothing_yet = host.completed == 0 && host.storage.captured_frames.unwrap_or(0) == 0;
    nothing_yet.then(|| {
        let message = host.message.as_deref().unwrap_or("").trim();
        (
            if message.is_empty() {
                "Starting".into()
            } else {
                message.to_owned()
            },
            None,
        )
    })
}

/// The headline from the host's state and the checker's journal.
pub(crate) fn headline(s: &Snapshot, progress: Option<&Progress>) -> Headline {
    let host = &s.host;
    let shots = host.shots();
    let total = host.total.max(host.completed);
    let timer = host.timer.as_ref();
    let elapsed = timer.and_then(|t| t.elapsed);
    let taken = host
        .storage
        .captured_frames
        .unwrap_or(host.completed * shots);
    let retakes = progress.map_or(0, |p| p.retakes as u64);
    Headline {
        plane: host.completed,
        total,
        fraction: if total > 0 {
            host.completed as f32 / total as f32
        } else {
            0.0
        },
        per_plane: elapsed
            .filter(|_| host.completed > 0)
            .map(|e| e / host.completed as f64),
        raws_taken: taken,
        raws_for_retakes: (retakes * shots).min(taken),
        retakes,
        retaken_planes: progress.map_or(0, |p| p.retaken as u64),
        elapsed,
        left: timer.and_then(|t| t.remaining),
        paused: host.phase == HostPhase::Paused,
        starting: starting(s),
    }
}

/// What retakes cost the run, measured from the host's counts as they
/// change: the active time between two planes finished, less the plain
/// pace, whenever the camera took more groups than planes in between.
/// Retakes are taken between planes, so each interval holds whole retakes.
#[derive(Clone, Debug, Default)]
pub(crate) struct RetakeClock {
    sequence: Option<u64>,
    /// The last change seen: planes done, groups captured, active seconds.
    last: Option<(u64, u64, f64)>,
    /// Seconds a plane took in the newest intervals without a retake.
    plain: VecDeque<f64>,
    /// Seconds the timed retakes added, and how many they were.
    pub seconds: f64,
    pub timed: u64,
}

/// Intervals without a retake the plain pace is the median of.
const PLAIN_KEPT: usize = 31;

impl RetakeClock {
    /// Takes the host's state (each poll; unchanged counts cost nothing).
    pub fn observe(&mut self, s: &Snapshot) {
        let host = &s.host;
        if host.sequence_id != self.sequence {
            *self = Self {
                sequence: host.sequence_id,
                ..Self::default()
            };
        }
        let (Some(elapsed), Some(frames)) = (
            host.timer.as_ref().and_then(|t| t.elapsed),
            host.storage.captured_frames,
        ) else {
            return;
        };
        let groups = frames / host.shots().max(1);
        let done = host.completed;
        let Some((d0, g0, e0)) = self.last else {
            self.last = Some((done, groups, elapsed));
            return;
        };
        let dt = (elapsed - e0).max(0.0);
        if done > d0 {
            let planes = done - d0;
            let extra = groups.saturating_sub(g0).saturating_sub(planes);
            if extra == 0 {
                self.plain.push_back(dt / planes as f64);
                if self.plain.len() > PLAIN_KEPT {
                    self.plain.pop_front();
                }
            } else if let Some(pace) = self.plain_pace() {
                self.seconds += (dt - planes as f64 * pace).max(0.0);
                self.timed += extra;
            }
            self.last = Some((done, groups, elapsed));
        } else if done >= host.total && host.total > 0 && groups > g0 {
            // Retakes after the last plane: their time is all theirs.
            self.seconds += dt;
            self.timed += groups - g0;
            self.last = Some((done, groups, elapsed));
        } else if done < d0 {
            self.last = Some((done, groups, elapsed));
        }
    }
    /// The median seconds a plane takes without a retake, once three
    /// intervals were seen.
    pub fn plain_pace(&self) -> Option<f64> {
        if self.plain.len() < 3 {
            return None;
        }
        let mut v: Vec<f64> = self.plain.iter().copied().collect();
        v.sort_by(f64::total_cmp);
        Some(v[v.len() / 2])
    }
    /// The time `retakes` retakes added: measured, with any not timed (the
    /// desktop was started mid-run) at the timed ones' average. `None`
    /// before one was timed.
    pub fn cost(&self, retakes: u64) -> Option<f64> {
        if retakes == 0 || self.timed == 0 {
            return None;
        }
        let each = self.seconds / self.timed as f64;
        Some(self.seconds + retakes.saturating_sub(self.timed) as f64 * each)
    }
}

/// The time left as shown: it counts down second by second and eases to
/// the host's estimate (which jumps when a plane's pace changes, as a
/// retake makes it), so the figures neither jitter nor run backwards
/// without cause. A large change (a pause, a new estimate) is taken at once.
#[derive(Clone, Debug, Default)]
pub(crate) struct LeftClock {
    sequence: Option<u64>,
    shown: Option<f64>,
    at: Option<Instant>,
}

/// How quickly the shown time follows the host's estimate (seconds).
const LEFT_EASE: f64 = 20.0;

impl LeftClock {
    /// The time left to show at `now`; `running`: the clock counts down.
    pub fn update(
        &mut self,
        estimate: Option<f64>,
        sequence: Option<u64>,
        running: bool,
        now: Instant,
    ) -> Option<f64> {
        if sequence != self.sequence {
            *self = Self {
                sequence,
                ..Self::default()
            };
        }
        let Some(target) = estimate else {
            self.shown = None;
            self.at = None;
            return None;
        };
        let dt = self
            .at
            .map_or(0.0, |at| now.saturating_duration_since(at).as_secs_f64())
            .min(5.0);
        self.at = Some(now);
        let shown = match self.shown {
            None => target,
            Some(v) => {
                let v = if running { v - dt } else { v };
                let error = target - v;
                if error.abs() > (0.25 * target).max(90.0) {
                    target
                } else {
                    v + error * (1.0 - (-dt / LEFT_EASE).exp())
                }
            }
        }
        .max(0.0);
        self.shown = Some(shown);
        Some(shown)
    }
}

/// One line of the health column.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct HealthLine {
    pub title: &'static str,
    pub mark: Mark,
    pub text: String,
    /// The line's bar, when it has one.
    pub fraction: Option<f32>,
}

/// "1 plane", "3 planes".
fn count(n: usize, one: &str, many: &str) -> String {
    format!("{n} {}", if n == 1 { one } else { many })
}

/// Transfer, checks, disk and rig.
pub(crate) fn health(s: &Snapshot, progress: Option<&Progress>, checking: bool) -> [HealthLine; 4] {
    let host = &s.host;
    let shots = host.shots();
    let storage = &host.storage;
    let taken = storage.captured_frames.unwrap_or(host.completed * shots);
    let saved = storage.saved_frames.unwrap_or(0);
    let behind = storage
        .pending_frames
        .unwrap_or(taken.saturating_sub(saved));
    let rate = storage
        .receipt
        .as_ref()
        .and_then(|r| r.wire_mb_per_second)
        .map(|r| format!(" · {r:.0} MB/s on Wi-Fi"))
        .unwrap_or_default();
    let on_pc = storage.mode.as_deref() == Some("host-pc");
    let transfer = if on_pc {
        HealthLine {
            title: "Transfer",
            mark: if behind > 2 * shots.max(1) * 2 {
                Mark::Warn
            } else {
                Mark::Ok
            },
            text: format!("{saved} of {taken} RAWs on this PC · {behind} behind{rate}"),
            fraction: (taken > 0).then(|| saved as f32 / taken as f32),
        }
    } else {
        HealthLine {
            title: "Transfer",
            mark: Mark::Idle,
            text: format!("{taken} RAWs kept on the camera's card"),
            fraction: None,
        }
    };
    let checks = match (progress, checking) {
        (Some(p), _) => {
            let mut t = p.tally;
            t.resolve(host.max_retakes() as usize);
            let t = &t;
            let mut text = format!("{} checked", count(p.checked, "plane", "planes"));
            if t.first_try > 0 {
                text.push_str(&format!(" · {} passed first time", t.first_try));
            }
            if t.retaken() > 0 {
                text.push_str(&format!(
                    " · {} retaken ({} then passed)",
                    t.retaken(),
                    t.retake_passed
                ));
            }
            if t.asked > 0 {
                text.push_str(&format!(" · {} being retaken", t.asked));
            }
            if t.single_shot() > 0 {
                text.push_str(&format!(" · {} stacked from one shot", t.single_shot()));
            }
            if t.incomplete > 0 {
                text.push_str(&format!(" · {} incomplete", t.incomplete));
            }
            HealthLine {
                title: "Checks",
                mark: if p.attention > t.asked {
                    Mark::Warn
                } else {
                    Mark::Ok
                },
                text,
                fraction: (host.completed > 0).then(|| p.checked as f32 / host.completed as f32),
            }
        }
        (None, true) => HealthLine {
            title: "Checks",
            mark: Mark::Idle,
            text: "Starts with the first plane saved on this PC".into(),
            fraction: None,
        },
        (None, false) => HealthLine {
            title: "Checks",
            mark: Mark::Idle,
            text: "Off: the stack is checked when it is opened".into(),
            fraction: None,
        },
    };
    let per_raw = super::plan::expected_per_raw(s);
    let free = s.receiver["free_bytes"].as_u64();
    // The planned RAWs and the retakes' so far: never "written past all".
    let retake_raws = progress.map_or(0, |p| p.retakes as u64) * shots;
    let expected = (host.total * shots + retake_raws).max(saved);
    let disk = if !on_pc {
        HealthLine {
            title: "Disk",
            mark: Mark::Idle,
            text: host.card_remaining.map_or("The camera's card".into(), |n| {
                format!("The camera's card: room for {n} more RAWs")
            }),
            fraction: None,
        }
    } else {
        HealthLine {
            title: "Disk",
            mark: if host.storage_error.is_some() {
                Mark::Warn
            } else {
                Mark::Ok
            },
            text: match (per_raw, free) {
                (Some(b), Some(f)) => format!(
                    "{:.1} of about {} written · {:.0} GB free",
                    (saved * b) as f64 / 1e9,
                    style::gigabytes(expected * b),
                    f as f64 / 1e9
                ),
                (None, Some(f)) => format!("{saved} RAWs written · {:.0} GB free", f as f64 / 1e9),
                _ => format!("{saved} RAWs written"),
            },
            fraction: (host.total > 0).then(|| saved as f32 / expected.max(1) as f32),
        }
    };
    let rig = HealthLine {
        title: "Rig",
        mark: if host.failure.is_some() {
            Mark::Bad
        } else if host.connected {
            Mark::Ok
        } else {
            Mark::Warn
        },
        text: super::plan::rig_summary(s),
        fraction: None,
    };
    [transfer, checks, disk, rig]
}

/// The checker's reasons for failing a group, in plain words
/// (`strehl follow`'s `reason`, from `pixel-shift-cmd.rs` `demotion`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Failure {
    /// "witness tiles disagree locally": the shots differ in places.
    Motion,
    /// "witness pairs misregistered" in the exposures themselves.
    OutOfLine,
    /// "witness pairs misregistered" only once this scene's measured
    /// sensor-shift residuals are applied.
    Correction,
    /// "offsets ... do not cover the four CFA parities", measured offsets:
    /// a shot slipped by a whole photosite (retaken).
    Slip,
    /// "offsets ... do not cover the four CFA parities", offsets not
    /// measurable.
    Pattern,
    /// "too little scene structure".
    Structure,
    /// "shifted photosites leave the sensor buffer".
    Edge,
    /// "members disagree in black or white level".
    Levels,
    /// The group could not be decoded.
    Unreadable,
    /// Its RAWs did not all arrive.
    Missing,
    /// A diagnostic retake (`STREHL_FOLLOW_RETAKE_PLANES`).
    Forced,
    Other,
}

impl Failure {
    /// The failure a feed item reports (`None` when it passed).
    pub fn of(item: &FeedItem) -> Option<Self> {
        if item.verdict.passed() {
            return None;
        }
        if item.verdict == Verdict::Incomplete {
            return Some(Self::Missing);
        }
        let reason = item.reason.as_deref().unwrap_or("");
        Some(
            if item.verdict == Verdict::Failed || reason.starts_with("decode") {
                Self::Unreadable
            } else if reason.contains("witness tiles disagree") {
                Self::Motion
            } else if reason.contains("misregistered") {
                if item.retake {
                    Self::OutOfLine
                } else {
                    Self::Correction
                }
            } else if reason.contains("CFA parities") {
                if item.retake {
                    Self::Slip
                } else {
                    Self::Pattern
                }
            } else if reason.contains("scene structure") {
                Self::Structure
            } else if reason.contains("sensor buffer") {
                Self::Edge
            } else if reason.contains("black or white level") {
                Self::Levels
            } else if reason.contains("forced retake") {
                Self::Forced
            } else {
                Self::Other
            },
        )
    }
    /// A short name.
    pub fn title(self) -> &'static str {
        match self {
            Self::Motion => "Shots differ in places",
            Self::OutOfLine => "Shots out of line",
            Self::Correction => "Shift correction off",
            Self::Slip => "Shot slipped",
            Self::Pattern => "Shift pattern off",
            Self::Structure => "Too little detail",
            Self::Edge => "Shifts leave the sensor",
            Self::Levels => "Levels differ",
            Self::Unreadable => "Could not be read",
            Self::Missing => "RAWs missing",
            Self::Forced => "Forced retake",
            Self::Other => "Flagged",
        }
    }
    /// What went wrong, in one short sentence.
    pub fn cause(self) -> &'static str {
        match self {
            Self::Motion => "Something moved, or focus slipped.",
            Self::OutOfLine => "The four shots do not line up.",
            Self::Correction => "The shots agree; the correction does not.",
            Self::Slip => "A shot slipped a whole pixel, off the four colour sites.",
            Self::Pattern => "A shot landed off the four colour sites.",
            Self::Structure => "Too little detail to measure the shifts.",
            Self::Edge => "Shifted photosites fall off the sensor.",
            Self::Levels => "Levels changed between the shots.",
            Self::Unreadable => "The RAWs could not be decoded.",
            Self::Missing => "Its RAWs did not all reach this PC.",
            Self::Forced => "A diagnostic retake.",
            Self::Other => "The checker flagged it.",
        }
    }
    /// Why the checker does not ask for a retake, in a few words (the
    /// row's; [`Self::policy`] says it fully).
    pub fn not_retaken(self) -> &'static str {
        match self {
            Self::Correction => "Not retaken: the shots are not at fault.",
            Self::Pattern => "Not retaken, by the checker's rule.",
            Self::Missing => "The stack uses the first that arrived.",
            _ => "Not retaken: a retake fails the same way.",
        }
    }
    /// [`Self::policy`], its "up to two times" said with the run's own
    /// limit (h-retake).
    pub fn policy_for(self, max: u32) -> String {
        let times = match max {
            0 => "never (retakes are set to 0)".to_owned(),
            1 => "up to once".to_owned(),
            2 => "up to two times".to_owned(),
            n => format!("up to {n} times"),
        };
        let policy = self.policy();
        if max == 0
            && let Some(rest) = policy.strip_prefix("Retaken, up to two times: ")
        {
            return format!("Retaken never (retakes are set to 0), though {rest}");
        }
        policy.replacen("up to two times", &times, 1)
    }
    /// Whether the checker asks for a retake of this failure, and why.
    pub fn policy(self) -> &'static str {
        match self {
            Self::Motion => {
                "Retaken, up to two times: something changed between the shots, so another try can pass."
            }
            Self::OutOfLine => {
                "Retaken, up to two times: the exposures themselves are out of line, so another try can pass."
            }
            Self::Levels => {
                "Retaken, up to two times: the light or exposure changed between the shots."
            }
            Self::Slip => {
                "Retaken, up to two times: the picture moved a whole pixel between the shots, so another try can land right."
            }
            Self::Unreadable => "Retaken, up to two times: another try can be read.",
            Self::Forced => "Retaken: asked for by STREHL_FOLLOW_RETAKE_PLANES.",
            Self::Correction => {
                "Not retaken: the shots agree with each other; the correction measured from this scene is what fails, and a retake measures it the same way."
            }
            Self::Pattern => {
                "Not retaken: the checker treats a wrong shift pattern as a property of the plane or the camera mode and expects a retake to fail the same way."
            }
            Self::Structure => {
                "Not retaken: the plane has too little detail to measure; a retake would fail the same way."
            }
            Self::Edge => {
                "Not retaken: a property of the camera mode; a retake would fail the same way."
            }
            Self::Missing => "Not retaken: the stack uses the first of its RAWs that arrived.",
            Self::Other => "",
        }
    }
}

/// A feed row's height.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum RowSize {
    /// A plane that passed on its first try: one line.
    One,
    /// A retake that passed: a title and one line.
    Two,
    /// A failed try: a title and up to two lines.
    Three,
}

impl RowSize {
    pub fn height(self) -> f32 {
        match self {
            Self::One => 30.0,
            Self::Two => 48.0,
            Self::Three => 64.0,
        }
    }
    /// From the item alone (never from what happens after it), so the
    /// rows' positions only ever grow at the end.
    pub fn of(item: &FeedItem) -> Self {
        if !item.verdict.passed() {
            Self::Three
        } else if item.attempt > 1 {
            Self::Two
        } else {
            Self::One
        }
    }
}

/// What the feed's rows depend on besides the items.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct FeedContext {
    /// The host retakes what the checker asks (error correction is on).
    pub error_correction: bool,
    /// The capture has ended: a retake asked for will not come.
    pub ended: bool,
    /// Error correction's retakes of a plane in this run (h-retake).
    pub max_retakes: u32,
    /// The host takes retakes asked for by hand (h-retake).
    pub manual: bool,
}

impl Default for FeedContext {
    fn default() -> Self {
        Self {
            error_correction: false,
            ended: false,
            max_retakes: strehl_capture::worker::MAX_RETAKES as u32,
            manual: false,
        }
    }
}

/// What a row offers for retaking its plane by hand (h-retake).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum RetakeOffer {
    None,
    /// "Retake": the plane's last try failed and nothing will retake it.
    Offer,
    /// Asked for; not taken yet.
    Queued,
}

/// One feed row in words.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct FeedRow {
    pub mark: Mark,
    /// Tracked capitals at the right ("passed", "retaken", "not retaken").
    pub status: &'static str,
    pub title: String,
    /// What happened and what follows (one or two lines).
    pub detail: String,
    /// The whole story, with the policy and the engine's own reason.
    pub tip: String,
    pub size: RowSize,
    /// Retake by hand (h-retake).
    pub retake: RetakeOffer,
}

/// The feed's row for `item`; `next`: the plane's next try, once checked.
#[cfg(test)]
pub(crate) fn feed_row(item: &FeedItem, next: Option<&FeedItem>, cx: FeedContext) -> FeedRow {
    feed_row_with(item, next, cx, false)
}

/// [`feed_row`], with whether the plane's retake by hand is `queued`.
pub(crate) fn feed_row_with(
    item: &FeedItem,
    next: Option<&FeedItem>,
    cx: FeedContext,
    queued: bool,
) -> FeedRow {
    let size = RowSize::of(item);
    let single = item.verdict == Verdict::Decoded || item.members == 1;
    let what = if single {
        "Decoded and aligned"
    } else {
        "Four shots agree"
    };
    let engine = item
        .reason
        .as_deref()
        .map(|r| format!("\nChecker: {r}"))
        .unwrap_or_default();
    let Some(failure) = Failure::of(item) else {
        return if item.attempt > 1 {
            FeedRow {
                mark: Mark::Ok,
                status: "passed",
                title: format!("Retake passed · try {}", item.attempt),
                detail: format!("{what}. The stack uses this try."),
                tip: format!(
                    "Plane {} was taken again after a failed try; this try passed and the stack uses it.",
                    item.plane
                ),
                size,
                retake: RetakeOffer::None,
            }
        } else {
            FeedRow {
                mark: Mark::Ok,
                status: "",
                title: what.to_owned(),
                detail: String::new(),
                tip: format!("Plane {}: {}.", item.plane, what.to_lowercase()),
                size,
                retake: RetakeOffer::None,
            }
        };
    };
    let tries_left = (cx.max_retakes + 1).saturating_sub(item.attempt);
    // The status says what the stack gets: a retake (to come or taken), or
    // this try's first shot.
    let (mark, status, then) = if failure == Failure::Missing {
        (Mark::Idle, "incomplete", failure.not_retaken().to_owned())
    } else if let Some(n) = next {
        let outcome = if n.verdict.passed() {
            "passed"
        } else {
            "failed too"
        };
        (
            Mark::Warn,
            "retaken",
            format!("Retaken: try {} {outcome}.", n.attempt),
        )
    } else if item.retake && cx.max_retakes == 0 && item.attempt == 1 && cx.error_correction {
        (
            Mark::Bad,
            "one shot",
            "Not retaken: retakes are set to 0.".to_owned(),
        )
    } else if item.retake && tries_left == 0 {
        (
            Mark::Bad,
            "one shot",
            format!("Failed {} tries; no retakes left.", item.attempt),
        )
    } else if item.retake && cx.error_correction && !cx.ended {
        (
            Mark::Warn,
            "retaking",
            format!(
                "Taking it again (try {} of {}).",
                item.attempt + 1,
                cx.max_retakes + 1
            ),
        )
    } else if item.retake {
        let why = if cx.error_correction {
            "Not retaken: the capture ended."
        } else {
            "Not retaken: error correction is off."
        };
        (Mark::Bad, "one shot", why.to_owned())
    } else {
        (Mark::Bad, "one shot", failure.not_retaken().to_owned())
    };
    // Nothing else will take it again: it may be retaken by hand.
    let open = next.is_none() && matches!(status, "one shot" | "incomplete");
    let retake = if !open || !cx.manual {
        RetakeOffer::None
    } else if queued {
        RetakeOffer::Queued
    } else {
        RetakeOffer::Offer
    };
    let (mark, status, then) = if retake == RetakeOffer::Queued {
        (
            Mark::Warn,
            "queued",
            if cx.ended {
                "Retake asked for.".to_owned()
            } else {
                "Retake asked for: taken between planes.".to_owned()
            },
        )
    } else {
        (mark, status, then)
    };
    let stacked = match status {
        "one shot" => "\nThe stack uses this try's first shot: one shot's detail there, not four.",
        "retaken" | "retaking" => "\nThe stack uses the plane's last try.",
        "queued" => "\nThe stack uses the plane's newest try: the retake, once taken.",
        _ => "",
    };
    let title = if item.attempt > 1 {
        format!("{} · try {}", failure.title(), item.attempt)
    } else {
        failure.title().to_owned()
    };
    let detail = format!("{} {then}", failure.cause());
    let by_hand = match retake {
        RetakeOffer::Offer => "\nRetake takes this plane again by hand.",
        _ => "",
    };
    let tip = format!(
        "Plane {}, try {}: {}\n{then}{stacked}{by_hand}\n{}{engine}",
        item.plane,
        item.attempt,
        failure.cause(),
        failure.policy_for(cx.max_retakes)
    );
    FeedRow {
        mark,
        status,
        title,
        detail,
        tip,
        size,
        retake,
    }
}

/// The plain-language account of the planes so far (or, once `ended`, of
/// the capture): how many passed, were retaken and how that went, and what
/// the stack does with the rest.
pub(crate) fn summary_sentence(t: &Tally, ended: bool) -> String {
    let mut out = Vec::new();
    let planes = count(t.planes, "plane", "planes");
    if t.planes == 0 {
        return if ended {
            "No plane was checked.".into()
        } else {
            "No plane checked yet.".into()
        };
    }
    out.push(if ended {
        format!("{planes} checked: {} passed on the first try.", t.first_try)
    } else {
        format!(
            "{planes} checked so far: {} passed on the first try.",
            t.first_try
        )
    });
    if t.retaken() > 0 {
        let mut s = format!(
            "{} taken again: {} then passed",
            count(t.retaken(), "plane was", "planes were"),
            t.retake_passed
        );
        if t.retake_failed > 0 {
            s.push_str(&format!(", {} failed every try", t.retake_failed));
        }
        s.push('.');
        out.push(s);
    }
    if t.asked > 0 {
        out.push(if ended {
            format!(
                "{} asked for a retake that was not taken.",
                count(t.asked, "plane", "planes")
            )
        } else {
            format!(
                "{} being taken again.",
                count(t.asked, "plane is", "planes are")
            )
        });
    }
    if t.not_retaken > 0 {
        out.push(format!(
            "{} failed a check the checker does not retake.",
            count(t.not_retaken, "plane", "planes"),
        ));
    }
    let single = t.single_shot() + if ended { t.asked } else { 0 };
    if single > 0 {
        out.push(format!(
            "The stack uses the first shot of {} (one shot's detail there, not four); every plane is in the stack.",
            if single == 1 {
                "that plane".to_owned()
            } else {
                format!("those {single} planes")
            }
        ));
    } else if ended && t.incomplete == 0 {
        out.push("Every plane is stacked from its four shots.".into());
    }
    if t.incomplete > 0 {
        out.push(format!(
            "{} RAWs did not all arrive; the stack uses the first that did.",
            count(t.incomplete, "plane's", "planes'")
        ));
    }
    out.join(" ")
}

/// A failure kind, the tries that failed with it, and the planes whose
/// last try did (the stack uses one shot of those).
pub(crate) type KindCount = (Failure, usize, usize);

/// The feed's failures by kind (see [`KindCount`]), most tries first, for
/// the summary's why.
pub(crate) fn failure_kinds(feed: &[FeedItem]) -> Vec<KindCount> {
    let mut kinds: Vec<KindCount> = Vec::new();
    for (i, item) in feed.iter().enumerate() {
        let Some(f) = Failure::of(item) else { continue };
        // The plane's last try: the stack folds it to its first shot.
        let single = item.next.is_none_or(|n| i + n as usize >= feed.len());
        match kinds.iter_mut().find(|(k, _, _)| *k == f) {
            Some(k) => {
                k.1 += 1;
                k.2 += usize::from(single);
            }
            None => kinds.push((f, 1, usize::from(single))),
        }
    }
    kinds.sort_by_key(|k| std::cmp::Reverse(k.1));
    kinds
}

// ----- retakes by hand and the stack's coverage (h-retake) ------------------

/// The feed's context from the view's inputs.
pub(crate) fn feed_context(inputs: &FlightInputs<'_>) -> FeedContext {
    let host = &inputs.s.host;
    FeedContext {
        error_correction: host.error_correction == Some(true),
        ended: inputs.ended,
        max_retakes: host.max_retakes(),
        manual: host.takes_manual_retakes() && inputs.s.fresh(),
    }
}

/// Each plane's newest checked try, by plane: `feed`'s last item of it.
fn newest_tries(feed: &[FeedItem]) -> std::collections::BTreeMap<u64, &FeedItem> {
    let mut newest = std::collections::BTreeMap::new();
    for (i, item) in feed.iter().enumerate() {
        if item.next.is_none_or(|n| i + n as usize >= feed.len()) {
            newest.insert(item.plane, item);
        }
    }
    newest
}

/// Why a plane's newest try leaves it to one shot, for good: `None` when it
/// passed or error correction will still retake it.
pub(crate) fn one_shot_why(item: &FeedItem, cx: FeedContext) -> Option<String> {
    let failure = Failure::of(item)?;
    if failure == Failure::Missing {
        return Some("RAWs missing".into());
    }
    let pending = item.retake && cx.error_correction && !cx.ended && item.attempt <= cx.max_retakes;
    if pending {
        return None;
    }
    Some(if item.retake {
        if item.attempt > 1 {
            "failed every try".into()
        } else if cx.error_correction && cx.max_retakes == 0 {
            "not retaken (retakes are set to 0)".into()
        } else if !cx.error_correction {
            "not retaken (error correction is off)".into()
        } else {
            "not retaken (the capture ended first)".into()
        }
    } else {
        let why = failure
            .not_retaken()
            .trim_start_matches("Not retaken")
            .trim_start_matches([',', ':'])
            .trim()
            .trim_end_matches('.');
        format!("not retaken: {} ({why})", failure.title().to_lowercase())
    })
}

/// The planes whose every try failed (error correction gave up on them):
/// the review offers them for a retake by hand.
pub(crate) fn exhausted_planes(feed: &[FeedItem], cx: FeedContext) -> Vec<u64> {
    newest_tries(feed)
        .into_iter()
        .filter(|(_, item)| {
            item.retake && item.attempt > cx.max_retakes && Failure::of(item).is_some()
        })
        .map(|(plane, _)| plane)
        .collect()
}

/// A run of neighbouring planes stacked from one shot, wide enough that
/// depth between them is sharp in no four-shot plane (h-retake).
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct RiskSpan {
    pub first: u64,
    pub last: u64,
    /// Focus units between the four-shot planes either side.
    pub gap: f64,
    /// The sharp width the rule used, and whether it was assumed.
    pub width: f64,
    pub assumed: bool,
    /// Focus units of depth farther than a quarter of the sharp width from
    /// any four-shot plane.
    pub band: f64,
    /// Why its planes are from one shot, with how many, most first.
    pub why: Vec<(String, usize)>,
}

impl RiskSpan {
    pub fn planes(&self) -> Vec<u64> {
        (self.first..=self.last).collect()
    }
    pub fn count(&self) -> usize {
        (self.last - self.first + 1) as usize
    }
}

/// The sharp width assumed without a calibration: the step a calibration
/// suggests is width / 7 (`strehl focus-step`'s SAFE), so a plan made that
/// way holds a point sharp over 7 steps.
pub(crate) const ASSUMED_OVERLAP: f64 = 7.0;

/// What [`risk_spans`] was computed from.
type RiskKey = (usize, super::follow::Tally, FeedContext, u16, u64);

/// The runs of planes left to one shot that put the stack at risk.
///
/// The rule (ARGUED, h-retake.md): a plane stacked from one shot still adds
/// its depth's detail at one shot's resolution, so what a run of them loses
/// is four-shot detail, and only where no four-shot plane is sharp enough.
/// Sharpness falls to half its peak at half the calibrated sharp width
/// (`strehl focus-step` measures the width at half height) and to about 84 %
/// at a quarter of it (for a peak of that width). With the four-shot planes
/// either side `gap = (k + 1) × step` apart, the depth midway is `gap / 2`
/// from both; it is at risk once that is more than a quarter of the width,
/// that is `gap > width / 2`: fewer than two four-shot planes hold that
/// depth sharp. The band at risk is `gap − width / 2`. At the suggested step
/// (width / 7) that is three planes in a row; one plane alone only at a step
/// coarser than width / 4, past the measured knee (width / 5).
/// Planes whose retake is still to come, and planes not checked yet, break
/// a run (no warning before it is known).
pub(crate) fn risk_spans(
    feed: &[FeedItem],
    cx: FeedContext,
    step: u16,
    width: Option<f64>,
) -> Vec<RiskSpan> {
    let step = f64::from(step.max(1));
    let (width, assumed) = match width.filter(|w| w.is_finite() && *w > 0.0) {
        Some(w) => (w, false),
        None => (ASSUMED_OVERLAP * step, true),
    };
    let mut spans = Vec::new();
    let mut run: Vec<(u64, String)> = Vec::new();
    let mut close = |run: &mut Vec<(u64, String)>| {
        if run.is_empty() {
            return;
        }
        let gap = (run.len() + 1) as f64 * step;
        if gap > width / 2.0 {
            let mut why: Vec<(String, usize)> = Vec::new();
            for (_, w) in run.iter() {
                match why.iter_mut().find(|(k, _)| k == w) {
                    Some(k) => k.1 += 1,
                    None => why.push((w.clone(), 1)),
                }
            }
            why.sort_by_key(|(_, n)| std::cmp::Reverse(*n));
            spans.push(RiskSpan {
                first: run[0].0,
                last: run[run.len() - 1].0,
                gap,
                width,
                assumed,
                band: gap - width / 2.0,
                why,
            });
        }
        run.clear();
    };
    for (plane, item) in newest_tries(feed) {
        let why = one_shot_why(item, cx);
        let follows = run.last().is_some_and(|(p, _)| *p + 1 == plane);
        if !follows {
            close(&mut run);
        }
        match why {
            Some(w) => run.push((plane, w)),
            None => close(&mut run),
        }
    }
    close(&mut run);
    spans
}

/// "30–33", "30, 41 and 52", or the first and the count.
pub(crate) fn plane_list(planes: &[u64]) -> String {
    match planes {
        [] => String::new(),
        [one] => one.to_string(),
        _ if planes.windows(2).all(|w| w[1] == w[0] + 1) => {
            format!("{}–{}", planes[0], planes[planes.len() - 1])
        }
        _ if planes.len() <= 4 => {
            let (last, rest) = planes.split_last().unwrap();
            format!(
                "{} and {last}",
                rest.iter()
                    .map(u64::to_string)
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        }
        _ => format!("{} and {} more", planes[0], planes.len() - 1),
    }
}

/// The warning's title and its sentence for one span.
pub(crate) fn risk_sentence(span: &RiskSpan) -> (String, String) {
    let title = format!(
        "Planes {}–{}: {} in a row from one shot",
        span.first,
        span.last,
        span.count()
    );
    let width = if span.assumed {
        format!("{:.0}, assumed; Calibrate step measures it", span.width)
    } else {
        format!("{:.0}", span.width)
    };
    let why = span
        .why
        .iter()
        .map(|(w, n)| format!("{n} {w}"))
        .collect::<Vec<_>>()
        .join("; ");
    (
        title,
        format!(
            "The four-shot planes either side are {:.0} units apart, more than half the sharp width ({width}): about {:.0} units of depth there get one shot's detail, not four. {}.",
            span.gap,
            span.band,
            why[..1].to_uppercase() + &why[1..]
        ),
    )
}

/// The coverage warning above the feed: each risky span (two at most, the
/// longest), what it costs, and "Retake planes A–B"; `list` less the
/// warning's height is returned for the feed.
#[allow(clippy::too_many_arguments)]
fn risk_banner(
    ui: &mut Ui,
    list: Rect,
    progress: &Progress,
    inputs: &FlightInputs<'_>,
    cx: FeedContext,
    view: &mut FlightView,
    palette: &CapturePalette,
    out: &mut Vec<FlightIntent>,
) -> Rect {
    let Some(step) = inputs.retakes.step else {
        return list;
    };
    let key: RiskKey = (
        progress.feed.len(),
        progress.tally,
        cx,
        step,
        inputs.retakes.width.unwrap_or(0.0).to_bits(),
    );
    if view.risk.as_ref().is_none_or(|(k, _)| *k != key) {
        let spans = risk_spans(&progress.feed, cx, step, inputs.retakes.width);
        view.risk = Some((key, Arc::new(spans)));
    }
    let spans = view
        .risk
        .as_ref()
        .map(|(_, s)| s.clone())
        .unwrap_or_default();
    if spans.is_empty() {
        return list;
    }
    let in_hand = &inputs.retakes.in_hand;
    let open = |planes: Vec<u64>| -> Vec<u64> {
        planes
            .into_iter()
            .filter(|p| in_hand.binary_search(p).is_err())
            .collect()
    };
    let mut shown: Vec<&RiskSpan> = spans.iter().collect();
    shown.sort_by_key(|s| std::cmp::Reverse(s.count()));
    shown.truncate(2);
    shown.sort_by_key(|s| s.first);
    let p = ui.painter().clone();
    let inner = list.width() - 22.0;
    let x = list.left() + 18.0;
    let mut y = list.top() + 8.0;
    let mut actions: Vec<(Rect, String, Vec<u64>)> = Vec::new();
    let mut texts: Vec<(egui::Pos2, Arc<egui::Galley>)> = Vec::new();
    for span in &shown {
        let (title, detail) = risk_sentence(span);
        let mut job = style::job(&title, 12.5, palette.ink, 0.0);
        job.wrap.max_width = inner;
        let g = p.layout_job(job);
        texts.push((egui::pos2(x, y), g.clone()));
        y += g.size().y + 2.0;
        let mut job = style::job(&detail, 12.0, palette.ink2, 0.0);
        job.wrap.max_width = inner;
        let g = p.layout_job(job);
        texts.push((egui::pos2(x, y), g.clone()));
        y += g.size().y + 6.0;
        let todo = open(span.planes());
        if !cx.manual {
            // The host cannot take retakes by hand: the warning alone.
        } else if todo.is_empty() {
            let mut job = style::job(
                &format!("Retakes asked for planes {}–{}.", span.first, span.last),
                12.0,
                palette.ink3,
                0.0,
            );
            job.wrap.max_width = inner;
            let g = p.layout_job(job);
            texts.push((egui::pos2(x, y), g.clone()));
            y += g.size().y + 6.0;
        } else {
            let r = Rect::from_min_size(egui::pos2(x, y), egui::vec2(inner.min(260.0), 26.0));
            actions.push((
                r,
                format!("Retake planes {}–{}", span.first, span.last),
                todo,
            ));
            y += 26.0 + 8.0;
        }
    }
    if spans.len() > shown.len() {
        let all: Vec<u64> = open(spans.iter().flat_map(RiskSpan::planes).collect());
        let mut job = style::job(
            &format!("{} more runs like these.", spans.len() - shown.len()),
            12.0,
            palette.ink2,
            0.0,
        );
        job.wrap.max_width = inner;
        let g = p.layout_job(job);
        texts.push((egui::pos2(x, y), g.clone()));
        y += g.size().y + 6.0;
        if cx.manual && !all.is_empty() {
            let r = Rect::from_min_size(egui::pos2(x, y), egui::vec2(inner.min(260.0), 26.0));
            actions.push((r, format!("Retake all {} planes", all.len()), all));
            y += 26.0 + 8.0;
        }
    }
    let banner = Rect::from_min_max(list.left_top(), egui::pos2(list.right(), y + 2.0));
    p.rect_filled(banner, 0.0, palette.panel);
    p.rect_stroke(
        banner,
        0.0,
        egui::Stroke::new(1.0_f32, palette.warn),
        egui::StrokeKind::Inside,
    );
    style::mark(
        &p,
        egui::pos2(list.left() + 9.0, list.top() + 17.0),
        Mark::Warn,
        7.0,
        palette,
    );
    for (at, g) in texts {
        p.galley(at, g, palette.ink);
    }
    for (r, label, planes) in actions {
        let tip = format!(
            "Takes planes {} again by hand, each through the approach as error correction does{}",
            plane_list(&planes),
            if cx.ended {
                ""
            } else {
                ", between the next planes"
            }
        );
        let clicked = ui
            .scope_builder(egui::UiBuilder::new().max_rect(r), |ui| {
                style::button_sized(ui, &label, ButtonKind::Plain, r.size(), true, palette)
                    .on_hover_text(tip)
                    .clicked()
            })
            .inner;
        if clicked {
            out.push(FlightIntent::QueueRetakes(planes));
        }
    }
    Rect::from_min_max(egui::pos2(list.left(), banner.bottom() + 14.0), list.max)
}

/// The rail's ticks in flight: each planned plane checked, retaken, needing
/// attention, on the camera host or to come.
pub(crate) fn flight_ticks(
    positions: Vec<u16>,
    s: &Snapshot,
    progress: Option<&Progress>,
) -> FlightTicks {
    let host = &s.host;
    let shots = host.shots().max(1);
    let retake_raws = progress.map_or(0, |p| p.retakes as u64) * shots;
    let saved_planes = host
        .storage
        .saved_frames
        .map_or(host.completed, |f| f.saturating_sub(retake_raws) / shots)
        .min(host.completed);
    let states = (0..positions.len() as u64)
        .map(|i| {
            let plane = i + 1;
            let line = progress.and_then(|p| p.plane(plane));
            if i >= host.completed {
                TickState::ToCome
            } else if progress.is_some_and(|p| p.retaken_planes.contains(&plane)) {
                TickState::Retaken
            } else if let Some(v) = line {
                match v["verdict"].as_str() {
                    Some("pass" | "decoded") => TickState::Checked,
                    Some("incomplete") => TickState::OnHost,
                    _ => TickState::Attention,
                }
            } else if i >= saved_planes {
                TickState::OnHost
            } else {
                TickState::Checked
            }
        })
        .collect();
    FlightTicks {
        positions,
        states,
        revision: 0,
    }
}

/// The overall state in one word, for the inspector's chip.
pub(crate) fn needs_you(s: &Snapshot, health: &[HealthLine; 4]) -> (Mark, &'static str) {
    let host = &s.host;
    if host.failure.is_some() || host.phase == HostPhase::Fault {
        (Mark::Bad, "Needs you")
    } else if host.phase == HostPhase::Paused {
        (Mark::Warn, "Paused")
    } else if host.phase == HostPhase::Complete {
        (Mark::Info, "Finished")
    } else if host.phase == HostPhase::Stopped {
        (Mark::Warn, "Stopped")
    } else if health.iter().any(|h| h.mark == Mark::Warn) {
        (Mark::Warn, "Worth a look")
    } else {
        (Mark::Ok, "Nothing needs you")
    }
}

/// Everything the in-flight view shows.
pub(crate) struct FlightInputs<'a> {
    pub s: &'a Snapshot,
    pub progress: Option<&'a Progress>,
    /// The checker is on.
    pub checking: bool,
    pub stack_when_done: bool,
    /// "Manage power"; `None` without studio outlets.
    pub power_down: Option<bool>,
    /// Stop was clicked once and waits for its confirmation.
    pub confirm_stop: bool,
    /// The time left as shown ([`LeftClock`]).
    pub left: Option<f64>,
    /// The time retakes added so far ([`RetakeClock::cost`]).
    pub retake_cost: Option<f64>,
    /// The seconds a plane takes without a retake, once measured.
    pub plain_pace: Option<f64>,
    /// The capture has ended: the view reviews it.
    pub ended: bool,
    /// When it ended, local time ("15:04").
    pub ended_at: Option<String>,
    /// A capture stopped by hand with this many complete planes (at least
    /// two): it can be stacked as it stands (plan Q6).
    pub stack_stopped: Option<usize>,
    /// Retakes by hand and the stack's coverage (h-retake).
    pub retakes: RetakeInputs,
}

/// What the retake actions and the coverage warning need (h-retake).
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct RetakeInputs {
    /// Planes asked to be retaken and not taken yet, ascending.
    pub in_hand: Vec<u64>,
    /// The plan's step, in focus units.
    pub step: Option<u16>,
    /// The calibrated sharp width (`strehl focus-step`), in focus units.
    pub width: Option<f64>,
}

/// What the user asked of the in-flight view.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum FlightIntent {
    Pause,
    Resume,
    /// The first click on Stop…: ask.
    AskStop,
    /// The confirming click.
    Stop,
    KeepGoing,
    Glance,
    SetStackWhenDone(bool),
    SetPowerDown(bool),
    /// Show a plane: the RAW of one of its tries (`raw`, its first file's
    /// name) or its last.
    ShowPlane {
        plane: u64,
        raw: Option<Arc<str>>,
    },
    /// Take these planes again by hand (h-retake).
    QueueRetakes(Vec<u64>),
    /// The capture has ended and the user is done with its review.
    Done,
    /// Done with the review, and the next capture starts from nothing.
    NewCapture,
    /// Stack a stopped capture's complete planes as they stand (plan Q6).
    StackStopped,
}

/// The view's state across frames: where each feed row starts.
#[derive(Default)]
pub(crate) struct FlightView {
    /// The top of each feed item's row, and the content's height.
    tops: Vec<f32>,
    height: f32,
    /// The feed the tops were built for: its length and first item.
    built: Option<(usize, u64, u32)>,
    /// The failure kinds of the feed (review only), and its length.
    kinds: Option<(usize, Vec<KindCount>)>,
    /// The feed's scroll offset and height last frame: a feed scrolled
    /// away from the newest keeps its rows in place as it grows.
    scroll: Option<(f32, f32)>,
    /// Rows laid out last frame (performance checks).
    pub rows_drawn: usize,
    /// The coverage warning's spans and what they were computed from.
    risk: Option<(RiskKey, Arc<Vec<RiskSpan>>)>,
    /// Where the plane view goes (`capture-plane-view.rs`), set by
    /// [`canvas`] each frame.
    pub plane: Option<Rect>,
}

impl FlightView {
    /// The rows' tops for `feed`, extended as it grows; rebuilt only when
    /// its start changed (the oldest items were dropped).
    fn tops(&mut self, feed: &[FeedItem]) -> (&[f32], f32) {
        let first = feed.first().map(|i| (i.plane, i.attempt));
        let start_same = match (self.built, first) {
            (Some((len, plane, attempt)), Some(f)) => len <= feed.len() && (plane, attempt) == f,
            (None, _) => false,
            (Some(_), None) => false,
        };
        if !start_same {
            self.tops.clear();
            self.height = 0.0;
        }
        for item in &feed[self.tops.len()..] {
            self.tops.push(self.height);
            self.height += RowSize::of(item).height();
        }
        if let Some((plane, attempt)) = first {
            self.built = Some((feed.len(), plane, attempt));
        } else {
            self.built = None;
        }
        (&self.tops, self.height)
    }
}

/// The canvas part: headline, the plane view's place, the feed.
pub(crate) fn canvas(
    ui: &mut Ui,
    inputs: &FlightInputs<'_>,
    view: &mut FlightView,
    palette: &CapturePalette,
) -> Vec<FlightIntent> {
    let mut out = Vec::new();
    let r = ui.max_rect();
    let p = ui.painter().clone();
    p.rect_filled(r, 0.0, palette.surround);
    let h = headline(inputs.s, inputs.progress);
    let head = Rect::from_min_size(
        r.min + egui::vec2(24.0, 20.0),
        egui::vec2(r.width() - 48.0, 108.0),
    );
    head_ui(&p, head, &h, inputs, palette);
    // The plane view (as large as fits; drawn by the station into
    // `view.plane`) and the side column.
    let top = head.bottom() + 20.0;
    let side_w = (r.width() * 0.25).clamp(340.0, 460.0);
    let plane = Rect::from_min_max(
        egui::pos2(r.left() + 24.0, top),
        egui::pos2(r.right() - 24.0 - side_w - 14.0, r.bottom() - 16.0),
    );
    view.plane = Some(plane);
    let side = egui::pos2(plane.right() + 14.0, top);
    let progress = inputs.progress;
    let cx = feed_context(inputs);
    let list = Rect::from_min_max(side, egui::pos2(side.x + side_w, r.bottom() - 16.0));
    match progress {
        Some(progress) => {
            let list = risk_banner(ui, list, progress, inputs, cx, view, palette, &mut out);
            feed_ui(
                ui,
                list,
                progress,
                cx,
                &inputs.retakes.in_hand,
                view,
                palette,
                &mut out,
            )
        }
        None => {
            style::paint_job(
                &p,
                list.left_top(),
                Align2::LEFT_TOP,
                style::caps_job("Planes", 10.5, palette.ink3),
            );
            style::hairline(
                &p,
                egui::pos2(list.left(), list.top() + 22.0),
                egui::pos2(list.right(), list.top() + 22.0),
                palette.line,
            );
            style::paint_job(
                &p,
                egui::pos2(list.left(), list.top() + 39.0),
                Align2::LEFT_CENTER,
                style::job("Checking is off", 12.5, palette.ink3, 0.0),
            );
        }
    }
    // G opens glance; Space pauses (the shell may route them elsewhere).
    if !ui.ctx().wants_keyboard_input() && !inputs.ended {
        ui.input(|i| {
            if i.key_pressed(egui::Key::G) {
                out.push(FlightIntent::Glance);
            }
            if i.key_pressed(egui::Key::Space) {
                out.push(if h.paused {
                    FlightIntent::Resume
                } else {
                    FlightIntent::Pause
                });
            }
        });
    }
    out
}

/// The 64 px figures' tracking.
const BIG_TRACKING: f32 = -0.6;

/// The headline: plane and total on one baseline, the bar and its two rows,
/// the time left and the finishing time in fixed slots.
fn head_ui(
    p: &egui::Painter,
    head: Rect,
    h: &Headline,
    inputs: &FlightInputs<'_>,
    palette: &CapturePalette,
) {
    style::hairline(p, head.left_bottom(), head.right_bottom(), palette.line);
    // Every number in the headline sits on this baseline.
    let base = head.bottom() - 28.0;
    let cap = |pos: egui::Pos2, align: Align2, text: &str| {
        style::paint_job(p, pos, align, style::caps_job(text, 10.5, palette.ink3));
    };
    cap(
        egui::pos2(head.left(), base - 54.0),
        Align2::LEFT_BOTTOM,
        "Plane",
    );
    // The plane's slot is as wide as the total's digits, so the bar beside
    // it never moves.
    let digits = "0".repeat(h.total.max(h.plane).to_string().len().max(2));
    let slot = style::figures_width(p, &digits, 64.0, BIG_TRACKING);
    let plane = style::paint_figures(
        p,
        egui::pos2(head.left(), base),
        false,
        &h.plane.to_string(),
        64.0,
        palette.ink,
        BIG_TRACKING,
    );
    let of = style::paint_on_baseline(
        p,
        egui::pos2(plane.right() + 10.0, base),
        egui::Align::Min,
        style::job(&format!("of {}", h.total), 20.0, palette.ink3, 0.0),
    );
    let of_right = head.left() + slot + 10.0 + of.width();
    // The finishing time and the time left (once ended: when it ended and
    // how long it took), right to left, in fixed slots.
    let ends_w = style::figures_width(p, "00:00", 64.0, BIG_TRACKING);
    let left = inputs.left;
    let (ends_text, ends_cap, left_text, left_cap) = if inputs.ended {
        (
            inputs.ended_at.clone().unwrap_or_else(|| "—".into()),
            "Ended",
            h.elapsed.map(style::clock).unwrap_or_else(|| "—".into()),
            "Took",
        )
    } else {
        (
            left.map(style::local_time_in).unwrap_or_else(|| "—".into()),
            "Ends",
            left.map(style::clock).unwrap_or_else(|| "—".into()),
            "Left",
        )
    };
    style::paint_figures(
        p,
        egui::pos2(head.right(), base),
        true,
        &ends_text,
        64.0,
        palette.ink3,
        BIG_TRACKING,
    );
    cap(
        egui::pos2(head.right(), base - 54.0),
        Align2::RIGHT_BOTTOM,
        ends_cap,
    );
    let left_right = head.right() - ends_w - 34.0;
    let long = h.elapsed.unwrap_or(0.0) + left.unwrap_or(0.0) >= 3600.0;
    let left_w = style::figures_width(
        p,
        if long { "0:00:00" } else { "00:00" },
        64.0,
        BIG_TRACKING,
    );
    style::paint_figures(
        p,
        egui::pos2(left_right, base),
        true,
        &left_text,
        64.0,
        palette.ink,
        BIG_TRACKING,
    );
    cap(
        egui::pos2(left_right, base - 54.0),
        Align2::RIGHT_BOTTOM,
        left_cap,
    );
    // The bar and its two rows.
    let grow = Rect::from_min_max(
        egui::pos2(of_right + 34.0, base - 46.0),
        egui::pos2(left_right - left_w - 34.0, base + 14.0),
    );
    // Before the first plane the bar shows the warm-up, in the quiet ink.
    let start = h.starting.as_ref().filter(|_| !inputs.ended);
    let (fill, fill_colour) = match start {
        Some((_, Some(f))) => (*f, palette.ink3),
        _ => (h.fraction, palette.ok),
    };
    style::bar(
        p,
        Rect::from_min_size(grow.min, egui::vec2(grow.width(), 8.0)),
        fill,
        fill_colour,
        palette,
    );
    let row1 = grow.top() + 8.0 + 14.0;
    let row2 = row1 + 19.0;
    let (mark, state) = if inputs.ended {
        match inputs.s.host.phase {
            HostPhase::Stopped => (Mark::Warn, "Stopped"),
            _ => (Mark::Info, "Finished"),
        }
    } else if h.paused {
        (Mark::Warn, "Paused")
    } else if let Some((text, _)) = start {
        (Mark::Info, text.as_str())
    } else {
        (Mark::Ok, "On track")
    };
    style::mark(p, egui::pos2(grow.left() + 3.5, row1), mark, 7.0, palette);
    let pace = inputs
        .plain_pace
        .or(h.per_plane)
        .map(|s| format!("{s:.1} s a plane"))
        .unwrap_or_default();
    let started = h
        .elapsed
        .map(|e| format!("started {}", style::local_time_in(-e)))
        .unwrap_or_default();
    // In a narrow bar the start time goes first, then the pace, so nothing
    // overlaps (the finishing time stays under ENDS).
    let width = |text: &str| {
        if text.is_empty() {
            0.0
        } else {
            p.layout_job(style::job(text, 12.5, palette.ink2, 0.0))
                .size()
                .x
        }
    };
    let room = grow.width() - 13.0 - 24.0;
    let state_w = width(state);
    let pace_w = if pace.is_empty() {
        0.0
    } else {
        width(&pace) + 10.0
    };
    let show_started = state_w + pace_w + width(&started) <= room;
    let show_pace = state_w + pace_w <= room + 24.0;
    let mut x = grow.left() + 13.0;
    for (text, color) in [
        (state.to_owned(), palette.ink),
        (if show_pace { pace } else { String::new() }, palette.ink2),
    ] {
        if text.is_empty() {
            continue;
        }
        let rr = style::paint_job(
            p,
            egui::pos2(x, row1),
            Align2::LEFT_CENTER,
            style::job(&text, 12.5, palette.ink2, 0.0).with_color(color),
        );
        x = rr.right() + 10.0;
    }
    if show_started && !started.is_empty() {
        style::paint_job(
            p,
            egui::pos2(grow.right(), row1),
            Align2::RIGHT_CENTER,
            style::job(&started, 12.5, palette.ink2, 0.0),
        );
    }
    // RAWs: every one taken, and those of retakes; never "X of Y". In a
    // narrow window the two texts shorten, the RAWs first, so they never
    // overlap.
    let raws_short = format!("{} RAWs taken", h.raws_taken);
    let raws_full = if h.raws_for_retakes > 0 {
        format!("{raws_short} · {} for retakes", h.raws_for_retakes)
    } else {
        raws_short.clone()
    };
    let (retakes_full, retakes_short) = if h.retakes > 0 {
        let cost = inputs
            .retake_cost
            .map(|c| format!(" · +{}", style::minutes(c)))
            .unwrap_or_default();
        let retakes = count(h.retakes as usize, "retake", "retakes");
        (
            format!(
                "{retakes} of {}{cost}",
                count(h.retaken_planes as usize, "plane", "planes")
            ),
            format!("{retakes}{cost}"),
        )
    } else {
        (String::new(), String::new())
    };
    let width = |text: &str| {
        if text.is_empty() {
            0.0
        } else {
            p.layout_job(style::job(text, 12.5, palette.ink2, 0.0))
                .size()
                .x
        }
    };
    // The warning mark and a gap of 24 pt between the two.
    let room = grow.width() - 13.0 - 24.0 - 12.0;
    let (raws, retakes) = [
        (&raws_full, &retakes_full),
        (&raws_short, &retakes_full),
        (&raws_short, &retakes_short),
    ]
    .into_iter()
    .find(|(left, right)| width(left) + width(right) <= room)
    .unwrap_or((&raws_short, &retakes_short));
    style::paint_job(
        p,
        egui::pos2(grow.left() + 13.0, row2),
        Align2::LEFT_CENTER,
        style::job(raws, 12.5, palette.ink2, 0.0),
    );
    if !retakes.is_empty() {
        let rr = style::paint_job(
            p,
            egui::pos2(grow.right(), row2),
            Align2::RIGHT_CENTER,
            style::job(retakes, 12.5, palette.warn, 0.0),
        );
        style::mark(
            p,
            egui::pos2(rr.left() - 8.0, row2),
            Mark::Warn,
            7.0,
            palette,
        );
    }
}

trait WithColor {
    fn with_color(self, color: egui::Color32) -> Self;
}

impl WithColor for egui::text::LayoutJob {
    fn with_color(mut self, color: egui::Color32) -> Self {
        for s in &mut self.sections {
            s.format.color = color;
        }
        self
    }
}

/// The feed: a summary of the planes so far, then every checked group in
/// the order it was checked, newest at the bottom. It fills its area and
/// scrolls; it follows the newest unless the user scrolled up. Only the
/// rows in view are laid out.
#[allow(clippy::too_many_arguments)]
fn feed_ui(
    ui: &mut Ui,
    list: Rect,
    progress: &Progress,
    cx: FeedContext,
    in_hand: &[u64],
    view: &mut FlightView,
    palette: &CapturePalette,
    out: &mut Vec<FlightIntent>,
) {
    let p = ui.painter().clone();
    let mut tally = progress.tally;
    tally.resolve(cx.max_retakes as usize);
    let t = &tally;
    style::paint_job(
        &p,
        list.left_top(),
        Align2::LEFT_TOP,
        style::caps_job(
            &format!("Planes · {} checked", progress.checked),
            10.5,
            palette.ink3,
        ),
    );
    // The counts by outcome, each with its mark.
    let mut y = list.top() + 22.0;
    style::hairline(
        &p,
        egui::pos2(list.left(), y),
        egui::pos2(list.right(), y),
        palette.line,
    );
    let counts = [
        (Mark::Ok, t.first_try, "first try"),
        (Mark::Ok, t.retake_passed, "after a retake"),
        (Mark::Warn, t.asked, "retaking"),
        (Mark::Bad, t.single_shot(), "one shot"),
        (Mark::Idle, t.incomplete, "incomplete"),
    ];
    let row = y + 15.0;
    let mut x = list.left() + 4.0;
    for (mark, n, what) in counts {
        if n == 0 && what != "first try" {
            continue;
        }
        style::mark(&p, egui::pos2(x, row), mark, 7.0, palette);
        let r = style::paint_job(
            &p,
            egui::pos2(x + 9.0, row),
            Align2::LEFT_CENTER,
            style::job(&format!("{n} {what}"), 12.0, palette.ink2, 0.0),
        );
        x = r.right() + 14.0;
    }
    y += 30.0;
    // The feed itself, below a rule: rows scroll under it, never into the
    // counts above.
    style::hairline(
        &p,
        egui::pos2(list.left(), y),
        egui::pos2(list.right(), y),
        palette.line,
    );
    y += 1.0;
    let area = Rect::from_min_max(egui::pos2(list.left(), y), list.max);
    if area.height() < 30.0 {
        return;
    }
    // Once the capture ended, the feed opens with what happened, in words,
    // and why each kind of failure was or was not retaken; it scrolls with
    // the rows, so it never runs past the column.
    let mut header: Vec<(Option<Mark>, std::sync::Arc<egui::Galley>)> = Vec::new();
    // The review's own retake: every plane that failed every try (h-retake).
    let exhausted: Vec<u64> = if cx.ended && cx.manual {
        exhausted_planes(&progress.feed, cx)
            .into_iter()
            .filter(|p| in_hand.binary_search(p).is_err())
            .collect()
    } else {
        Vec::new()
    };
    if cx.ended {
        let wrap = area.width() - FEED_GUTTER;
        let mut job = style::job(&summary_sentence(t, true), 12.5, palette.ink, 0.0);
        job.wrap.max_width = wrap;
        header.push((None, p.layout_job(job)));
        let len = progress.feed.len();
        if view.kinds.as_ref().is_none_or(|(n, _)| *n != len) {
            view.kinds = Some((len, failure_kinds(&progress.feed)));
        }
        for (failure, tries, _) in view.kinds.as_ref().map_or(&[][..], |(_, k)| k) {
            let mut job = style::job(
                &format!("{} · {}  ", failure.title(), count(*tries, "try", "tries")),
                12.0,
                palette.ink,
                0.0,
            );
            job.append(
                failure.policy(),
                0.0,
                egui::TextFormat {
                    font_id: egui::FontId::proportional(12.0),
                    color: palette.ink3,
                    ..Default::default()
                },
            );
            job.wrap.max_width = wrap - 14.0;
            let mark = if failure.policy().starts_with("Retaken") {
                Mark::Warn
            } else {
                Mark::Bad
            };
            header.push((Some(mark), p.layout_job(job)));
        }
    }
    const ACTION_H: f32 = 36.0;
    let action_h = if exhausted.is_empty() { 0.0 } else { ACTION_H };
    let header_h = if header.is_empty() {
        0.0
    } else {
        header.iter().map(|(_, g)| g.size().y + 8.0).sum::<f32>() + 12.0 + action_h
    };
    let feed = &progress.feed;
    let last = view.scroll;
    let (tops, rows_h) = view.tops(feed);
    let height = header_h + rows_h;
    let mut drawn = 0;
    let mut scroll_ui = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(area)
            .layout(egui::Layout::top_down(egui::Align::Min)),
    );
    let mut scroll = egui::ScrollArea::vertical()
        .id_salt("capture-flight-feed")
        .auto_shrink([false, false])
        // The wheel and the bar scroll; a press is for Show, not a drag.
        .scroll_source(egui::scroll_area::ScrollSource {
            drag: false,
            ..Default::default()
        });
    // Newest at the top. At the top, the feed follows the newest; scrolled
    // down, the rows in view stay put as new ones arrive above them.
    if let Some((offset, before)) = last
        && offset > 0.5
        && height > before
    {
        scroll = scroll.vertical_scroll_offset(offset + (height - before));
    }
    let output = scroll.show_viewport(&mut scroll_ui, |ui, viewport| {
        ui.set_height(height);
        let width = ui.max_rect().width();
        let origin = ui.max_rect().left_top();
        let painter = ui.painter().clone();
        let mut hy = 6.0;
        for (i, (mark, galley)) in header.iter().enumerate() {
            let x = if let Some(mark) = mark {
                style::mark(
                    &painter,
                    origin + egui::vec2(4.0, hy + 8.0),
                    *mark,
                    7.0,
                    palette,
                );
                14.0
            } else {
                0.0
            };
            painter.galley(origin + egui::vec2(x, hy), galley.clone(), palette.ink);
            hy += galley.size().y + 8.0;
            // Under the summary: the planes that failed every try, again.
            if i == 0 && !exhausted.is_empty() {
                let r = Rect::from_min_size(
                    origin + egui::vec2(0.0, hy),
                    egui::vec2((width - FEED_GUTTER).clamp(120.0, 300.0), 28.0),
                );
                let label = format!(
                    "Retake the {} that failed every try",
                    count(exhausted.len(), "plane", "planes")
                );
                let tip = format!(
                    "Planes {}: each taken again by hand, through the approach, as error correction does",
                    plane_list(&exhausted)
                );
                let clicked = ui
                    .scope_builder(egui::UiBuilder::new().max_rect(r), |ui| {
                        style::button_sized(ui, &label, ButtonKind::Plain, r.size(), true, palette)
                            .on_hover_text(tip)
                            .clicked()
                    })
                    .inner;
                if clicked {
                    out.push(FlightIntent::QueueRetakes(exhausted.clone()));
                }
                hy += ACTION_H;
            }
        }
        if header_h > 0.0 {
            style::hairline(
                &painter,
                origin + egui::vec2(0.0, header_h - 1.0),
                origin + egui::vec2(width, header_h - 1.0),
                palette.line,
            );
        }
        // Item i's row ends `tops[i] + its height` from the oldest end, so
        // from the rows' top it starts at `rows_h - that`: the rows in view
        // are those ending between `rows_h - max` and `rows_h - min` from
        // the oldest end, the viewport taken below the header.
        let (min, max) = (viewport.min.y - header_h, viewport.max.y - header_h);
        let newest_shown = tops.partition_point(|t| *t < rows_h - min).min(feed.len());
        let oldest_shown = tops
            .partition_point(|t| *t <= rows_h - max)
            .saturating_sub(1);
        for i in (oldest_shown..newest_shown).rev() {
            let item = &feed[i];
            drawn += 1;
            let next = item.next.and_then(|n| feed.get(i + n as usize));
            let queued = next.is_none() && in_hand.binary_search(&item.plane).is_ok();
            let row = feed_row_with(item, next, cx, queued);
            let top = header_h + rows_h - tops[i] - row.size.height();
            let rect = Rect::from_min_size(
                origin + egui::vec2(0.0, top),
                egui::vec2(width, row.size.height()),
            );
            if let Some(intent) = feed_row_ui(ui, &painter, rect, i, item, &row, palette) {
                out.push(intent);
            }
        }
    });
    view.scroll = Some((output.state.offset.y, height));
    view.rows_drawn = drawn;
}

/// The feed's right margin, clear of its scroll bar.
const FEED_GUTTER: f32 = 12.0;

/// One feed row: mark, plane, title and status on the first line, the
/// detail wrapped below; "Show" under the plane for a try that did not
/// simply pass.
fn feed_row_ui(
    ui: &Ui,
    p: &egui::Painter,
    rect: Rect,
    index: usize,
    item: &FeedItem,
    row: &FeedRow,
    palette: &CapturePalette,
) -> Option<FlightIntent> {
    let line1 = rect.top() + 15.0;
    let hover = ui.interact(
        rect,
        ui.id().with(("capture-feed-row", index)),
        Sense::hover(),
    );
    if hover.hovered() {
        p.rect_filled(rect, 0.0, palette.raised);
    }
    style::mark(
        p,
        egui::pos2(rect.left() + 4.0, line1),
        row.mark,
        7.0,
        palette,
    );
    style::paint_job(
        p,
        egui::pos2(rect.left() + 18.0, line1),
        Align2::LEFT_CENTER,
        style::job(&item.plane.to_string(), 12.5, palette.ink, 0.2),
    );
    let text_left = rect.left() + 58.0;
    // Status (or the check's time) at the right of the first line.
    let right = if row.status.is_empty() {
        item.seconds
            .map(|s| {
                style::paint_job(
                    p,
                    egui::pos2(rect.right() - FEED_GUTTER, line1),
                    Align2::RIGHT_CENTER,
                    style::job(&format!("{s:.1} s"), 12.0, palette.ink3, 0.0),
                )
                .left()
            })
            .unwrap_or(rect.right())
    } else {
        style::paint_job(
            p,
            egui::pos2(rect.right() - FEED_GUTTER, line1),
            Align2::RIGHT_CENTER,
            style::caps_job(row.status, 10.0, palette.mark_color(row.mark)),
        )
        .left()
    };
    let mut title = style::job(&row.title, 12.5, palette.ink, 0.0);
    title.wrap.max_width = (right - 8.0 - text_left).max(20.0);
    title.wrap.max_rows = 1;
    style::paint_job(p, egui::pos2(text_left, line1), Align2::LEFT_CENTER, title);
    let mut intent = None;
    if !row.detail.is_empty() {
        let mut detail = style::job(&row.detail, 12.0, palette.ink2, 0.0);
        detail.wrap.max_width = (rect.right() - FEED_GUTTER - text_left).max(20.0);
        detail.wrap.max_rows = if row.size == RowSize::Three { 2 } else { 1 };
        let g = p.layout_job(detail);
        p.galley(egui::pos2(text_left, rect.top() + 25.0), g, palette.ink2);
        // Show, under the mark and the plane's number: this try's RAW (or
        // the plane's last). At the row's left edge, so "Retake" under it
        // clears the detail's column.
        let link = Rect::from_min_size(
            egui::pos2(rect.left() + 2.0, rect.top() + 27.0),
            egui::vec2(38.0, 16.0),
        );
        let resp = ui
            .interact(
                link,
                ui.id().with(("capture-feed-show", index)),
                Sense::click(),
            )
            .on_hover_text("Show this try's RAW");
        style::paint_job(
            p,
            link.left_center() + egui::vec2(2.0, 0.0),
            Align2::LEFT_CENTER,
            style::caps_job(
                "Show",
                9.5,
                if resp.hovered() {
                    palette.ink
                } else {
                    palette.ink3
                },
            ),
        );
        if resp.clicked() {
            intent = Some(FlightIntent::ShowPlane {
                plane: item.plane,
                raw: item.first.clone(),
            });
        }
        // Retake, under Show: this plane again, by hand (h-retake).
        if row.retake != RetakeOffer::None {
            let link = Rect::from_min_size(
                egui::pos2(rect.left() + 2.0, rect.top() + 44.0),
                egui::vec2(40.0, 16.0),
            );
            let offered = row.retake == RetakeOffer::Offer;
            let resp = ui.interact(
                link,
                ui.id().with(("capture-feed-retake", index)),
                if offered {
                    Sense::click()
                } else {
                    Sense::hover()
                },
            );
            let resp = if offered {
                resp.on_hover_text("Take this plane again by hand")
            } else {
                resp.on_hover_text("Asked for; not taken yet")
            };
            style::paint_job(
                p,
                link.left_center() + egui::vec2(2.0, 0.0),
                Align2::LEFT_CENTER,
                style::caps_job(
                    if offered { "Retake" } else { "Asked" },
                    9.5,
                    if !offered {
                        palette.ink3
                    } else if resp.hovered() {
                        palette.ink
                    } else {
                        palette.warn
                    },
                ),
            );
            if offered && resp.clicked() {
                intent = Some(FlightIntent::QueueRetakes(vec![item.plane]));
            }
        }
    }
    hover.on_hover_text(&row.tip);
    style::hairline(p, rect.left_bottom(), rect.right_bottom(), palette.line);
    intent
}

/// The inspector part: the health column, the switches and the foot.
pub(crate) fn inspector(
    ui: &mut Ui,
    inputs: &FlightInputs<'_>,
    palette: &CapturePalette,
) -> Vec<FlightIntent> {
    let mut out = Vec::new();
    let full = ui.max_rect();
    ui.painter().rect_filled(full, 0.0, palette.panel);
    style::hairline(
        ui.painter(),
        full.left_top() + egui::vec2(0.5, 0.0),
        full.left_bottom() + egui::vec2(0.5, 0.0),
        palette.line,
    );
    let foot = Rect::from_min_max(egui::pos2(full.left(), full.bottom() - 53.0), full.max);
    let body = Rect::from_min_max(full.min, egui::pos2(full.right(), foot.top()));
    let lines = health(inputs.s, inputs.progress, inputs.checking);
    let (state_mark, state) = needs_you(inputs.s, &lines);
    ui.scope_builder(egui::UiBuilder::new().max_rect(body.shrink2(egui::vec2(16.0, 14.0))), |ui| {
        ui.spacing_mut().item_spacing.y = 0.0;
        section(ui, if inputs.ended { "Captured" } else { "In flight" }, Some((state_mark, state)), palette);
        for line in &lines {
            health_row(ui, line, palette);
        }
        if inputs.ended {
            return;
        }
        ui.add_space(14.0);
        section(ui, "When it finishes", None, palette);
        ui.add_space(6.0);
        if style::option(ui, inputs.stack_when_done, "Stack it, then show the checks", None, inputs.checking, palette) {
            out.push(FlightIntent::SetStackWhenDone(!inputs.stack_when_done));
        }
        if let Some(down) = inputs.power_down
            && style::option(ui, down, "Power the rig down", Some("after the last RAW is saved"), false, palette)
        {
            out.push(FlightIntent::SetPowerDown(!down));
        }
        ui.add_space(14.0);
        let mut job = style::job("You can leave this page. ", 12.5, palette.ink, 0.0);
        job.append(
            "The capture keeps its place in the bar at the top right while you develop another photograph.",
            0.0,
            egui::TextFormat {
                font_id: egui::FontId::proportional(12.5),
                color: palette.ink2,
                ..Default::default()
            },
        );
        job.wrap.max_width = ui.available_width();
        ui.label(job);
    });
    style::hairline(
        ui.painter(),
        foot.left_top() + egui::vec2(0.0, 0.5),
        foot.right_top() + egui::vec2(0.0, 0.5),
        palette.line,
    );
    let s = inputs.s;
    let host = &s.host;
    let fresh = s.fresh() && !s.pending;
    ui.scope_builder(
        egui::UiBuilder::new()
            .max_rect(foot.shrink2(egui::vec2(16.0, 12.0)))
            .layout(egui::Layout::left_to_right(egui::Align::Center)),
        |ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            if inputs.ended {
                // Two ways on (owner feedback, 2026-11-23): a clean plan for
                // the next subject, or back to this one's plan as it stands.
                let parts = if inputs.stack_stopped.is_some() { 3.0 } else { 2.0 };
                let w = (ui.available_width() - 8.0 * (parts - 1.0)) / parts;
                if let Some(planes) = inputs.stack_stopped
                    && style::button_sized(
                        ui,
                        &format!("Stack {planes} planes"),
                        ButtonKind::Primary,
                        egui::vec2(w, 28.0),
                        true,
                        palette,
                    )
                    .on_hover_text(
                        "Stack the planes this capture completed before it was stopped, as they stand",
                    )
                    .clicked()
                {
                    out.push(FlightIntent::StackStopped);
                }
                if style::button_sized(
                    ui,
                    "New capture",
                    if inputs.stack_stopped.is_some() {
                        ButtonKind::Plain
                    } else {
                        ButtonKind::Primary
                    },
                    egui::vec2(w, 28.0),
                    true,
                    palette,
                )
                .on_hover_text(
                    "A clean plan: clears the subject, bounds, survey, test shot and step calibration. The rig's settings stay.",
                )
                .clicked()
                {
                    out.push(FlightIntent::NewCapture);
                }
                if style::button_sized(
                    ui,
                    "Back to the plan",
                    ButtonKind::Plain,
                    egui::vec2(w, 28.0),
                    true,
                    palette,
                )
                .on_hover_text("This capture's plan as it stands, to shoot it again or adjust it")
                .clicked()
                {
                    out.push(FlightIntent::Done);
                }
                return;
            }
            if inputs.confirm_stop {
                let w = ui.available_width() - 100.0 - 8.0;
                if style::button_sized(
                    ui,
                    "Stop now",
                    ButtonKind::Danger,
                    egui::vec2(w, 28.0),
                    fresh && host.phase.active(),
                    palette,
                )
                .clicked()
                {
                    out.push(FlightIntent::Stop);
                }
                if style::button_sized(
                    ui,
                    "Keep going",
                    ButtonKind::Plain,
                    egui::vec2(100.0, 28.0),
                    true,
                    palette,
                )
                .clicked()
                {
                    out.push(FlightIntent::KeepGoing);
                }
                return;
            }
            let paused = host.phase == HostPhase::Paused;
            let w = ui.available_width() - 56.0 - 72.0 - 16.0;
            let pause = style::button_sized(
                ui,
                if paused { "Resume" } else { "Pause" },
                ButtonKind::Plain,
                egui::vec2(w, 28.0),
                fresh
                    && (paused
                        || (host.phase == HostPhase::Capturing && host.pending_control != 1)),
                palette,
            );
            if pause.clicked() {
                out.push(if paused {
                    FlightIntent::Resume
                } else {
                    FlightIntent::Pause
                });
            }
            if style::button_sized(
                ui,
                "Stop…",
                ButtonKind::Danger,
                egui::vec2(56.0, 28.0),
                fresh && host.phase.active() && host.pending_control != 2,
                palette,
            )
            .on_hover_text("Asks first, and keeps the planes already taken")
            .clicked()
            {
                out.push(FlightIntent::AskStop);
            }
            if style::button_sized(
                ui,
                "Glance",
                ButtonKind::Plain,
                egui::vec2(72.0, 28.0),
                true,
                palette,
            )
            .clicked()
            {
                out.push(FlightIntent::Glance);
            }
        },
    );
    out
}

fn section(ui: &mut Ui, title: &str, state: Option<(Mark, &str)>, palette: &CapturePalette) {
    let w = ui.available_width();
    let (r, _) = ui.allocate_exact_size(egui::vec2(w, 24.0), Sense::hover());
    let p = ui.painter();
    style::paint_job(
        p,
        r.left_center(),
        Align2::LEFT_CENTER,
        style::caps_job(title, 10.5, palette.ink3),
    );
    if let Some((mark, text)) = state {
        let t = style::paint_job(
            p,
            r.right_center(),
            Align2::RIGHT_CENTER,
            style::job(text, 12.0, palette.ink, 0.0),
        );
        style::mark(
            p,
            egui::pos2(t.left() - 9.0, r.center().y),
            mark,
            7.0,
            palette,
        );
    }
    style::hairline(p, r.left_bottom(), r.right_bottom(), palette.line);
}

fn health_row(ui: &mut Ui, line: &HealthLine, palette: &CapturePalette) {
    let w = ui.available_width();
    let mut job = style::job(&line.text, 12.5, palette.ink2, 0.0);
    job.wrap.max_width = w - 28.0;
    let galley = ui.painter().layout_job(job);
    let h = 11.0 + 18.0 + galley.size().y + if line.fraction.is_some() { 10.0 } else { 0.0 } + 11.0;
    let (r, _) = ui.allocate_exact_size(egui::vec2(w, h), Sense::hover());
    let p = ui.painter();
    style::mark(
        p,
        egui::pos2(r.left() + 5.0, r.top() + 11.0 + 9.0),
        line.mark,
        7.0,
        palette,
    );
    style::paint_job(
        p,
        egui::pos2(r.left() + 28.0, r.top() + 11.0),
        Align2::LEFT_TOP,
        style::job(line.title, 13.0, palette.ink, 0.2),
    );
    p.galley(
        egui::pos2(r.left() + 28.0, r.top() + 29.0),
        galley.clone(),
        palette.ink2,
    );
    if let Some(f) = line.fraction {
        let y = r.top() + 29.0 + galley.size().y + 8.0;
        style::bar(
            p,
            Rect::from_min_size(egui::pos2(r.left() + 28.0, y), egui::vec2(w - 28.0, 2.0)),
            f,
            if line.mark == Mark::Warn {
                palette.warn
            } else {
                palette.ok
            },
            palette,
        );
    }
    style::hairline(p, r.left_bottom(), r.right_bottom(), palette.line);
}

#[cfg(test)]
#[path = "capture-flight-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "capture-retake-tests.rs"]
mod retake_tests;
