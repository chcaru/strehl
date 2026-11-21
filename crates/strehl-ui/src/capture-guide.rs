//! Guidance for the Capture plan (owner feedback, 2026-11-21): which ISO,
//! exposure, bounds, step, settle and light warm-up are best, and what each
//! choice is likely to do to the image and to the time.
//!
//! Everything here is cheap arithmetic over the host's state, the test
//! shot's RAW levels and the step calibration, done each frame (no I/O, no
//! allocation beyond a few short rows). The numbers come from the rig's own
//! measurements (`experiments/capture-implementation-2026-11-20/results.md`
//! and its `evidence/`) and from the host's timing model
//! (`strehl_capture::timing::initial_plane`); each table says which, and the
//! screen labels estimates as estimates.
//!
//! - Exposure: final-image SNR rose as the square root of the exposure time
//!   and did not depend on ISO (MEASURED, six settings of two runs each; at
//!   1/25 s, ISO 100 pushed four stops gave SNR 12.1 against 11.0 at ISO
//!   1600). So the best setting is the camera's base ISO and the longest
//!   exposure that does not clip, judged from the test RAW's brightest 0.1 %
//!   scaled by ISO x exposure (DERIVED: RAW values are linear).
//! - Step: fine detail at the worst 10 % of detail tiles of two stacks
//!   rendered from every k-th plane (MEASURED); detail held to a step of
//!   about width / 5 and finer steps bought no noise reduction.
//! - Settle: the K4 runs (MEASURED); the host settles the plane after the
//!   approach move at least 2 s itself.
//! - Light: it dimmed 9 % over its first minute (MEASURED).
use eframe::egui::{self, Align2, Color32, Rect, Sense, Stroke, Ui};
use strehl_capture::timing;

use super::plan::{self, CalibrationView, PlanIntent, StepRow, TestShotView};
use super::style::{self, ButtonKind, CapturePalette, Mark};
use crate::capture_client::{Snapshot, host::Exposure};

// ----- exposure --------------------------------------------------------------

/// The suggested exposure keeps the test RAW's brightest 0.1 % at or below
/// this share of full scale: about 0.15 stop of room for a part of the
/// subject brighter than the test shot saw.
pub(crate) const HIGHLIGHT_TARGET: f64 = 0.9;
/// A test RAW with more than this share of its samples at white has
/// clipped; its levels then no longer scale with the exposure.
pub(crate) const CLIPPED_LIMIT: f64 = 1e-4;

/// The ISO of a Sony code, or `None` for ISO AUTO.
pub(crate) fn iso_number(code: u64) -> Option<f64> {
    let value = code & 0x00ff_ffff;
    (value != 0x00ff_ffff && value > 0).then_some(value as f64)
}

/// The lowest fixed ISO the camera offers (plain codes before ones with
/// flag bits), or `current` when it offers none.
pub(crate) fn base_iso(options: &[u64], current: u64) -> u64 {
    let lowest = |plain: bool| {
        options
            .iter()
            .copied()
            .filter(|&c| iso_number(c).is_some() && (!plain || c >> 24 == 0))
            .min_by_key(|&c| c & 0x00ff_ffff)
    };
    lowest(true).or_else(|| lowest(false)).unwrap_or(current)
}

/// What the test shot says about brightness.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Metered {
    pub iso: f64,
    pub seconds: f64,
    /// The 99.9th percentile above black, as a share of black to white.
    pub highlight: f64,
    /// Share of samples at or above white.
    pub clipped: f64,
}

impl Metered {
    pub fn clipped(&self) -> bool {
        self.clipped > CLIPPED_LIMIT
    }
    /// Light at `iso` and `seconds` against the test shot's.
    pub fn ratio(&self, iso: f64, seconds: f64) -> f64 {
        iso * seconds / (self.iso * self.seconds)
    }
    /// The brightest 0.1 % at `iso` and `seconds`, as a share of full scale
    /// (RAW values are linear in ISO x exposure); `None` once the test
    /// itself clipped.
    pub fn highlight_at(&self, iso: f64, seconds: f64) -> Option<f64> {
        (!self.clipped()).then(|| self.highlight * self.ratio(iso, seconds))
    }
}

/// The test shot's metering: its RAW levels and the exposure it was taken
/// at (the RAW's own ISO when it reports one).
pub(crate) fn metered(view: &TestShotView) -> Option<Metered> {
    let levels = view.levels.as_ref()?;
    let (iso_code, shutter) = view.exposure?;
    let seconds = timing::shutter_seconds(shutter)?;
    let iso = levels
        .iso
        .map(f64::from)
        .filter(|v| *v > 0.0)
        .or_else(|| iso_number(iso_code))?;
    Some(Metered {
        iso,
        seconds,
        highlight: levels.highlight_level,
        clipped: levels.clipped_share,
    })
}

/// Whether the highlights clip at a setting.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Clip {
    /// No test shot, ISO AUTO, or brighter than a test shot that clipped
    /// can say.
    Unknown,
    Safe,
    /// The brightest 0.1 % above [`HIGHLIGHT_TARGET`].
    Near,
    Clips,
}

pub(crate) fn clip_at(m: Option<&Metered>, iso: Option<f64>, seconds: f64) -> Clip {
    let (Some(m), Some(iso)) = (m, iso) else {
        return Clip::Unknown;
    };
    if m.clipped() {
        return if m.ratio(iso, seconds) >= 1.0 - 1e-9 {
            Clip::Clips
        } else {
            Clip::Unknown
        };
    }
    match m.highlight_at(iso, seconds) {
        Some(h) if h >= 1.0 => Clip::Clips,
        Some(h) if h > HIGHLIGHT_TARGET => Clip::Near,
        Some(_) => Clip::Safe,
        None => Clip::Unknown,
    }
}

/// SNR change in dB of `seconds` against `now`: SNR rises as the square
/// root of the exposure, so 10 log10(t / now).
pub(crate) fn snr_db(seconds: f64, now: f64) -> f64 {
    10.0 * (seconds / now).log10()
}

/// Noise against the signal, in stops (negative: less noise).
pub(crate) fn noise_stops(seconds: f64, now: f64) -> f64 {
    -0.5 * (seconds / now).log2()
}

/// What the plan suggests for ISO and exposure.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Advice {
    /// The camera reports no exposure.
    None,
    /// No test shot to judge brightness from; `iso` is the base ISO.
    TestShot { iso: u64 },
    /// The test shot clipped this share of its samples.
    Clipped { share: f64 },
    /// The current setting is the suggestion.
    Best { iso: u64, shutter: u64 },
    /// Another setting is suggested.
    Change { iso: u64, shutter: u64 },
    /// Even the shortest exposure offered clips at base ISO.
    TooBright { iso: u64, shutter: u64 },
}

impl Advice {
    pub fn suggested(&self) -> Option<(u64, u64)> {
        match *self {
            Self::Best { iso, shutter }
            | Self::Change { iso, shutter }
            | Self::TooBright { iso, shutter } => Some((iso, shutter)),
            _ => None,
        }
    }
}

/// The shutter codes offered with their seconds, longest first, the
/// current one included.
fn shutter_choices(e: &Exposure) -> Vec<(u64, f64)> {
    let mut out: Vec<(u64, f64)> = e
        .shutter_options
        .iter()
        .chain(e.shutter.iter())
        .filter_map(|&c| timing::shutter_seconds(c).map(|t| (c, t)))
        .collect();
    out.sort_by(|a, b| b.1.total_cmp(&a.1));
    out.dedup_by(|a, b| (a.1 - b.1).abs() < 1e-9);
    out
}

/// Base ISO and the longest exposure whose brightest 0.1 % stays at or
/// below [`HIGHLIGHT_TARGET`].
pub(crate) fn advise(e: &Exposure, m: Option<&Metered>) -> Advice {
    let (Some(iso), Some(shutter)) = (e.iso, e.shutter) else {
        return Advice::None;
    };
    let base = base_iso(&e.iso_options, iso);
    let Some(m) = m else {
        return Advice::TestShot { iso: base };
    };
    if m.clipped() {
        return Advice::Clipped { share: m.clipped };
    }
    let Some(base_n) = iso_number(base) else {
        return Advice::TestShot { iso: base };
    };
    let choices = shutter_choices(e);
    let now = timing::shutter_seconds(shutter);
    match choices.iter().find(|(_, t)| {
        m.highlight_at(base_n, *t)
            .is_some_and(|h| h <= HIGHLIGHT_TARGET)
    }) {
        Some(&(_, t)) if base == iso && now.is_some_and(|n| (n - t).abs() < 1e-9) => {
            Advice::Best { iso, shutter }
        }
        Some(&(code, _)) => Advice::Change {
            iso: base,
            shutter: code,
        },
        None => Advice::TooBright {
            iso: base,
            shutter: choices.last().map_or(shutter, |c| c.0),
        },
    }
}

/// One exposure of the comparison.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ExposureRow {
    pub iso: u64,
    pub shutter: u64,
    pub seconds: f64,
    pub snr_db: f64,
    pub noise_stops: f64,
    pub highlight: Option<f64>,
    pub clip: Clip,
    /// The host's estimate of a plane, and of the stack at the plan's step.
    pub plane: Option<f64>,
    pub stack: Option<f64>,
    pub current: bool,
    pub suggested: bool,
}

/// Up to `MAX_EXPOSURE_ROWS` exposures about a stop apart around the
/// current and the suggested one (both always kept): the current at its
/// own ISO, the others at the base ISO.
pub(crate) const MAX_EXPOSURE_ROWS: usize = 7;

pub(crate) fn exposure_rows(
    s: &Snapshot,
    settle_ms: u32,
    planes: Option<usize>,
    m: Option<&Metered>,
    advice: &Advice,
) -> Vec<ExposureRow> {
    let Some(e) = s.host.exposure.as_ref() else {
        return Vec::new();
    };
    let (Some(iso), Some(shutter)) = (e.iso, e.shutter) else {
        return Vec::new();
    };
    let Some(now) = timing::shutter_seconds(shutter) else {
        return Vec::new();
    };
    let base = base_iso(&e.iso_options, iso);
    let suggested = advice.suggested().map(|(_, c)| c);
    let suggested_t = suggested.and_then(timing::shutter_seconds);
    let choices = shutter_choices(e);
    // Whole stops from now, reaching a stop past the suggestion.
    let toward = suggested_t.map(|t| (t / now).log2());
    let low = toward
        .map_or(-2, |r| (r.floor() as i32 - 1).min(-1))
        .max(-5);
    let high = toward.map_or(2, |r| (r.ceil() as i32 + 1).max(1)).min(6);
    let mut kept: Vec<(u64, f64)> = Vec::new();
    for k in low..=high {
        let target = now * 2f64.powi(k);
        let nearest = choices.iter().min_by(|a, b| {
            (a.1 / target)
                .log2()
                .abs()
                .total_cmp(&(b.1 / target).log2().abs())
        });
        if let Some(&(code, t)) = nearest
            && (t / target).log2().abs() <= 0.5
        {
            kept.push((code, t));
        }
    }
    let pinned =
        |t: f64| (t - now).abs() < 1e-9 || suggested_t.is_some_and(|s| (s - t).abs() < 1e-9);
    kept.extend(choices.iter().copied().filter(|(_, t)| pinned(*t)));
    kept.sort_by(|a, b| b.1.total_cmp(&a.1));
    kept.dedup_by(|a, b| (a.1 - b.1).abs() < 1e-9);
    while kept.len() > MAX_EXPOSURE_ROWS {
        // Drop the end farther from now and the suggestion.
        let far = |t: f64| {
            let a = (t / now).log2().abs();
            suggested_t.map_or(a, |s| a.min((t / s).log2().abs()))
        };
        let (first, last) = (kept[0].1, kept[kept.len() - 1].1);
        if !pinned(first) && (pinned(last) || far(first) >= far(last)) {
            kept.remove(0);
        } else if !pinned(last) {
            kept.pop();
        } else {
            break;
        }
    }
    let base_n = iso_number(base);
    kept.into_iter()
        .map(|(code, t)| {
            let current = (t - now).abs() < 1e-9;
            let row_iso = if current { iso } else { base };
            let iso_n = if current { iso_number(iso) } else { base_n };
            let plane =
                timing::initial_plane(code, settle_ms, s.host.shots()).map(|d| d.as_secs_f64());
            ExposureRow {
                iso: row_iso,
                shutter: code,
                seconds: t,
                snr_db: snr_db(t, now),
                noise_stops: noise_stops(t, now),
                highlight: m.zip(iso_n).and_then(|(m, n)| m.highlight_at(n, t)),
                clip: clip_at(m, iso_n, t),
                plane,
                stack: planes.and_then(|n| plan::stack_seconds_at(s, n, settle_ms, code)),
                current,
                suggested: suggested_t.is_some_and(|s| (s - t).abs() < 1e-9),
            }
        })
        .collect()
}

/// How a guidance line reads.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Tone {
    Note,
    Good,
    Warn,
}

/// One line of guidance and the change it offers.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Line {
    pub text: String,
    pub tone: Tone,
    pub action: Option<(&'static str, PlanIntent)>,
}

fn signed(v: f64, decimals: usize) -> String {
    // ASCII minus: the UI face draws U+2212 on the baseline.
    format!("{:+.*}", decimals, v)
}

/// Units that stay on the line of their number.
const UNITS: [&str; 15] = [
    "s", "ms", "%", "dB", "min", "h", "m", "units", "GB", "MB", "MB/s", "st", "planes", "W",
    "stops",
];

/// `text` with the space between a number and its unit made
/// non-breaking, so a wrapped line never ends in "2" with "s" below.
pub(crate) fn unbreak(text: &str) -> String {
    let words: Vec<&str> = text.split(' ').collect();
    let mut out = String::with_capacity(text.len());
    for (i, word) in words.iter().enumerate() {
        out.push_str(word);
        if let Some(next) = words.get(i + 1) {
            let unit = next.trim_end_matches([',', '.', ';', ':', ')']);
            let glued = word.ends_with(|c: char| c.is_ascii_digit()) && UNITS.contains(&unit);
            out.push(if glued { '\u{a0}' } else { ' ' });
        }
    }
    out
}

fn seconds_short(seconds: f64) -> String {
    if seconds.abs() < 60.0 {
        format!("{:.1} s", seconds.abs())
    } else {
        style::minutes(seconds.abs())
    }
}

/// The exposure step's guidance line.
pub(crate) fn exposure_line(advice: &Advice, rows: &[ExposureRow]) -> Option<Line> {
    let now = rows.iter().find(|r| r.current);
    let pick = rows.iter().find(|r| r.suggested);
    let describe = |row: &ExposureRow| {
        let mut parts = vec![format!("{} dB SNR", signed(row.snr_db, 1))];
        let sign = |d: f64| if d > 0.0 { "+" } else { "-" };
        if let (Some(a), Some(b)) = (row.plane, now.and_then(|n| n.plane)) {
            let d = a - b;
            if d.abs() >= 0.05 {
                parts.push(format!("{}{} a plane", sign(d), seconds_short(d)));
            } else {
                parts.push("same time a plane".into());
            }
        }
        if let (Some(a), Some(b)) = (row.stack, now.and_then(|n| n.stack)) {
            let d = a - b;
            if d.abs() >= 1.0 {
                parts.push(format!("{}{} a stack", sign(d), style::minutes(d.abs())));
            }
        }
        parts.join(", ")
    };
    match *advice {
        Advice::None => None,
        Advice::TestShot { iso } => Some(Line {
            text: format!(
                "Noise is set by the exposure time, not ISO: keep {} and take a test shot to see how long the exposure can be.",
                style::iso_label(iso)
            ),
            tone: Tone::Note,
            action: None,
        }),
        Advice::Clipped { share } => Some(Line {
            text: format!(
                "The test shot clipped {:.2} % of the RAW: shorten the exposure, then take another.",
                100.0 * share
            ),
            tone: Tone::Warn,
            action: None,
        }),
        Advice::Best { iso, shutter } => Some(Line {
            text: format!(
                "{} · {} is the longest exposure that keeps highlights under {:.0} % (estimate from the test shot).",
                style::iso_label(iso),
                style::shutter_label(shutter),
                100.0 * HIGHLIGHT_TARGET
            ),
            tone: Tone::Good,
            action: None,
        }),
        Advice::Change { iso, shutter } => {
            let row = pick?;
            let longer = now.is_some_and(|n| row.seconds > n.seconds + 1e-9);
            let text = if longer || now.is_none() {
                format!(
                    "Suggested {} · {}: {} (estimate).",
                    style::iso_label(iso),
                    style::shutter_label(shutter),
                    describe(row)
                )
            } else if now.is_some_and(|n| (n.seconds - row.seconds).abs() < 1e-9) {
                format!(
                    "{} gives the same noise with {:.1} stops more highlight room.",
                    style::iso_label(iso),
                    now.and_then(|n| Some((iso_number(n.iso)? / iso_number(iso)?).log2()))
                        .unwrap_or(0.0)
                )
            } else {
                format!(
                    "Highlights would clip: {} · {} keeps them under {:.0} %: {}.",
                    style::iso_label(iso),
                    style::shutter_label(shutter),
                    100.0 * HIGHLIGHT_TARGET,
                    describe(row)
                )
            };
            Some(Line {
                text,
                tone: if longer { Tone::Note } else { Tone::Warn },
                action: Some(("Apply", PlanIntent::Exposure { iso, shutter })),
            })
        }
        Advice::TooBright { iso, shutter } => Some(Line {
            text: format!(
                "Even {} at {} clips the highlights: lower the light.",
                style::shutter_label(shutter),
                style::iso_label(iso)
            ),
            tone: Tone::Warn,
            action: None,
        }),
    }
}

// ----- step ------------------------------------------------------------------

/// Fine detail held to a step of about the sharp width / 5 (MEASURED: on
/// the scarab, width 113, step 24 kept what 16 kept and 32 lost 5 %; the
/// step-curve table). Rows with less overlap are marked.
pub(crate) const KNEE: f64 = 5.0;

/// Fine detail at the worst 10 % of detail tiles against overlap (sharp
/// width / step), relative to every plane at step 8: the scarab stack
/// (width 113) and the dark-background stack (width 88). MEASURED,
/// `step-curve-scarab4.txt`, `step-curve-dark4.txt`.
const SCARAB: [(f64, f64); 7] = [
    (113.0 / 8.0, 1.000),
    (113.0 / 16.0, 0.990),
    (113.0 / 24.0, 0.988),
    (113.0 / 32.0, 0.946),
    (113.0 / 48.0, 0.895),
    (113.0 / 64.0, 0.863),
    (113.0 / 96.0, 0.818),
];
const DARK: [(f64, f64); 5] = [
    (88.0 / 8.0, 1.000),
    (88.0 / 16.0, 0.989),
    (88.0 / 24.0, 0.983),
    (88.0 / 32.0, 0.982),
    (88.0 / 48.0, 0.962),
];

/// The detail a step keeps, between the two measured stacks.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct DetailKept {
    pub low: f64,
    pub high: f64,
    /// Coarser than either stack was measured at.
    pub beyond: bool,
}

/// One measured curve at overlap `k` (linear between the measured steps;
/// finer than the reference reads as all of it).
fn curve(points: &[(f64, f64)], k: f64) -> (f64, bool) {
    let first = points[0];
    let last = points[points.len() - 1];
    if k >= first.0 {
        return (first.1, false);
    }
    if k <= last.0 {
        return (last.1, k < last.0 - 1e-9);
    }
    for pair in points.windows(2) {
        let (a, b) = (pair[0], pair[1]);
        if k <= a.0 && k >= b.0 {
            let f = (k - b.0) / (a.0 - b.0);
            return (b.1 + f * (a.1 - b.1), false);
        }
    }
    (last.1, false)
}

pub(crate) fn detail_kept(overlap: f64) -> DetailKept {
    let (a, beyond_a) = curve(&SCARAB, overlap);
    let (b, beyond_b) = curve(&DARK, overlap);
    DetailKept {
        low: a.min(b),
        high: a.max(b),
        beyond: beyond_a && beyond_b,
    }
}

/// `99 %`, or `<82 %` past the measured steps (the lower of the two
/// stacks: the conservative reading).
pub(crate) fn detail_label(d: &DetailKept) -> String {
    let pct = (100.0 * d.low).round();
    if d.beyond {
        format!("<{pct:.0} %")
    } else {
        format!("{pct:.0} %")
    }
}

/// The depth step's line about the table, under it.
pub(crate) fn step_line(rows: &[StepRow], calibration: &CalibrationView) -> String {
    let width = calibration.result["width"].as_f64();
    match width {
        Some(w) => {
            let edge = (w / KNEE).floor().max(1.0);
            let finer = rows
                .iter()
                .filter(|r| r.current)
                .any(|r| r.overlap.is_some_and(|o| o > 2.0 * KNEE));
            if finer {
                format!(
                    "Steps up to {edge:.0} keep the detail (width / 5); this one is finer than it needs: more time, no less noise."
                )
            } else {
                format!("Steps up to {edge:.0} keep the detail (width / 5); finer adds only time.")
            }
        }
        None => {
            "Calibrate step to see what each step keeps here; finer steps never lower the noise."
                .into()
        }
    }
}

// ----- bounds ----------------------------------------------------------------

/// Start and End against the survey's sharp range.
pub(crate) fn bounds_line(s: &Snapshot, step: u16, settle_ms: u32) -> Option<Line> {
    let host = &s.host;
    let suggestion = host.suggestion.as_ref()?;
    if suggestion.clipped {
        return Some(Line {
            text: "The survey reached its search limit: the subject may go on past it. Widen the rough bounds and survey again.".into(),
            tone: Tone::Warn,
            action: None,
        });
    }
    let (s_lo, s_hi) = (
        suggestion.start.min(suggestion.end),
        suggestion.start.max(suggestion.end),
    );
    let use_survey = Some(("Use the survey's", PlanIntent::UseSurveyBounds));
    if !host.bounds_set() {
        return Some(Line {
            text: format!(
                "The survey found sharp detail from {} to {} (two survey intervals of margin included).",
                style::focus_units(s_lo),
                style::focus_units(s_hi)
            ),
            tone: Tone::Note,
            action: use_survey,
        });
    }
    let (start, end) = host.plan_bounds();
    let (lo, hi) = (start.min(end), start.max(end));
    let outside = u32::from(lo.saturating_sub(s_lo)) + u32::from(s_hi.saturating_sub(hi));
    let beyond = u32::from(s_lo.saturating_sub(lo)) + u32::from(hi.saturating_sub(s_hi));
    if outside == 0 && beyond == 0 {
        return Some(Line {
            text: "The marks match the survey's sharp range.".into(),
            tone: Tone::Good,
            action: None,
        });
    }
    if outside > 0 {
        return Some(Line {
            text: format!(
                "The survey saw sharp detail {outside} units outside the marks: those parts would be soft."
            ),
            tone: Tone::Warn,
            action: use_survey,
        });
    }
    let step = step.max(1);
    let extra = plan::plane_count(start, end, step).saturating_sub(plan::plane_count(
        suggestion.start,
        suggestion.end,
        step,
    ));
    let time = host
        .exposure
        .as_ref()
        .and_then(|e| e.shutter)
        .and_then(|sh| timing::initial_plane(sh, settle_ms, host.shots()))
        .map(|p| {
            format!(
                ", about {} more",
                style::minutes(p.as_secs_f64() * extra as f64)
            )
        })
        .unwrap_or_default();
    Some(Line {
        text: format!(
            "The marks reach {beyond} units past the survey's sharp range: {extra} more planes{time}."
        ),
        tone: Tone::Note,
        action: use_survey,
    })
}

// ----- settle ----------------------------------------------------------------

/// The host settles the plane reached straight after the approach move (the
/// first, and a retake's) at least this long, whatever the plan's settle
/// (`strehl_capture::worker::AFTER_APPROACH_MS`, private there).
pub(crate) const FIRST_PLANE_SETTLE_MS: u32 = 2000;

/// Groups passing the checker at a settle, MEASURED in interleaved 12-plane
/// runs (K4, 2026-11-20): still room, and with someone walking about.
/// 500 ms: 48 of 48 once the plane after the approach settled 2 s
/// (`ab-settle-first-plane.txt`; 45 of 48 before that rule); the others
/// were measured before the rule.
const SETTLE_MEASURED: [(u32, &str, Option<&str>); 3] = [
    (500, "48 of 48", Some("13 of 24 †")),
    (1000, "45 of 48 †", None),
    (2000, "48 of 48", Some("20 of 24 †")),
];

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SettleRow {
    pub ms: u32,
    pub plane: Option<f64>,
    pub stack: Option<f64>,
    pub still: Option<&'static str>,
    pub walking: Option<&'static str>,
    pub current: bool,
}

pub(crate) fn settle_rows(s: &Snapshot, planes: Option<usize>, settle_ms: u32) -> Vec<SettleRow> {
    let mut choices: Vec<u32> = plan::SETTLE_CHOICES.to_vec();
    choices.push(settle_ms);
    choices.sort_unstable();
    choices.dedup();
    let shutter = s.host.exposure.as_ref().and_then(|e| e.shutter);
    choices
        .into_iter()
        .map(|ms| {
            let measured = SETTLE_MEASURED.iter().find(|m| m.0 == ms);
            SettleRow {
                ms,
                plane: shutter
                    .and_then(|sh| timing::initial_plane(sh, ms, s.host.shots()))
                    .map(|d| d.as_secs_f64()),
                stack: shutter
                    .zip(planes)
                    .and_then(|(sh, n)| plan::stack_seconds_at(s, n, ms, sh)),
                still: measured.map(|m| m.1),
                walking: measured.and_then(|m| m.2),
                current: ms == settle_ms,
            }
        })
        .collect()
}

// ----- light -----------------------------------------------------------------

/// Warm-ups the light tab offers, in seconds.
pub(crate) const WARMUP_CHOICES: [u32; 6] = [0, 5, 15, 30, 60, 120];

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct WarmupRow {
    pub seconds: u32,
    /// What it adds to a stack against no warm-up (only with Manage power).
    pub adds: Option<f64>,
    pub stack: Option<f64>,
    pub current: bool,
}

pub(crate) fn warmup_rows(s: &Snapshot, planes: Option<usize>, settle_ms: u32) -> Vec<WarmupRow> {
    let power = s.host.power.as_ref();
    let current = power.and_then(|p| p.warmup_seconds).map(|w| w as u32);
    let managed = power.is_some_and(|p| p.manage_stack);
    let mut choices: Vec<u32> = WARMUP_CHOICES.to_vec();
    choices.extend(current);
    choices.sort_unstable();
    choices.dedup();
    let shutter = s.host.exposure.as_ref().and_then(|e| e.shutter);
    let base = shutter
        .zip(planes)
        .and_then(|(sh, n)| plan::stack_seconds_at(s, n, settle_ms, sh));
    let without = base.map(|b| {
        b - if managed {
            f64::from(current.unwrap_or(0))
        } else {
            0.0
        }
    });
    choices
        .into_iter()
        .map(|w| WarmupRow {
            seconds: w,
            adds: managed.then_some(f64::from(w)),
            stack: without.map(|b| b + if managed { f64::from(w) } else { 0.0 }),
            current: Some(w) == current,
        })
        .collect()
}

// ----- the comparison panel --------------------------------------------------

/// The panel's sections.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum GuideTab {
    Exposure,
    Step,
    Settle,
    Light,
}

impl GuideTab {
    const ALL: [Self; 4] = [Self::Exposure, Self::Step, Self::Settle, Self::Light];
    fn label(self) -> &'static str {
        match self {
            Self::Exposure => "ISO and exposure",
            Self::Step => "Step",
            Self::Settle => "Settle",
            Self::Light => "Light warm-up",
        }
    }
}

/// What the panel shows.
#[derive(Clone, Copy)]
pub(crate) struct GuideInputs<'a> {
    pub s: &'a Snapshot,
    pub step: u16,
    pub settle_ms: u32,
    pub calibration: &'a CalibrationView,
    pub test_shot: &'a TestShotView,
    /// Choices may be sent now.
    pub editable: bool,
}

/// One column of a ruled table.
#[derive(Clone, Copy)]
pub(crate) struct Col {
    pub head: &'static str,
    pub left: bool,
}

/// One row of a ruled table.
#[derive(Clone, Debug, Default)]
pub(crate) struct Row {
    pub cells: Vec<String>,
    pub current: bool,
    pub suggested: bool,
    pub warn: bool,
    pub hover: Option<String>,
}

const ROW_H: f32 = 24.0;
const HEAD_H: f32 = 18.0;

/// A ruled table across the available width, each column as wide as its
/// widest cell and the gaps shared out; the current row is marked as in
/// the step table, a suggested row with an accent lamp at its left. The
/// font steps down until the columns fit, so no cell overlaps another.
/// Returns the clicked row when `clickable`.
pub(crate) fn ruled_table(
    ui: &mut Ui,
    id: &str,
    cols: &[Col],
    rows: &[Row],
    clickable: bool,
    palette: &CapturePalette,
) -> Option<usize> {
    let width = ui.available_width();
    let inset = 12.0;
    let mut size = 12.0;
    let mut widths = vec![0.0f32; cols.len()];
    for attempt in [12.0, 11.0, 10.0] {
        size = attempt;
        for (i, col) in cols.iter().enumerate() {
            let head = ui
                .painter()
                .layout_job(style::caps_job(col.head, 9.5, palette.ink3))
                .size()
                .x;
            let cells = rows
                .iter()
                .filter_map(|r| r.cells.get(i))
                .map(|c| {
                    ui.painter()
                        .layout_job(style::job(c, size, palette.ink, 0.0))
                        .size()
                        .x
                })
                .fold(0.0f32, f32::max);
            widths[i] = head.max(cells);
        }
        let need: f32 = widths.iter().sum::<f32>() + 10.0 * (cols.len() - 1) as f32 + inset * 2.0;
        if need <= width {
            break;
        }
    }
    let total: f32 = widths.iter().sum();
    let gap = ((width - inset * 2.0 - total) / (cols.len().max(2) - 1) as f32).max(6.0);
    let (rect, _) = ui.allocate_exact_size(
        egui::vec2(width, HEAD_H + ROW_H * rows.len() as f32),
        Sense::hover(),
    );
    // Each column's left and right edge.
    let mut edges = Vec::with_capacity(cols.len());
    let mut x = rect.left() + inset;
    for w in &widths {
        edges.push((x, x + w));
        x += w + gap;
    }
    let p = ui.painter();
    for (col, &(l, r)) in cols.iter().zip(&edges) {
        let (pos, anchor) = if col.left {
            (egui::pos2(l, rect.top() + 3.0), Align2::LEFT_TOP)
        } else {
            (egui::pos2(r, rect.top() + 3.0), Align2::RIGHT_TOP)
        };
        style::paint_job(p, pos, anchor, style::caps_job(col.head, 9.5, palette.ink3));
    }
    let mut clicked = None;
    for (i, row) in rows.iter().enumerate() {
        let r = Rect::from_min_size(
            egui::pos2(rect.left(), rect.top() + HEAD_H + ROW_H * i as f32),
            egui::vec2(width, ROW_H),
        );
        let can = clickable && !row.current;
        let response = ui.interact(
            r,
            ui.id().with((id, i)),
            if can { Sense::click() } else { Sense::hover() },
        );
        let p = ui.painter();
        if row.current {
            p.rect_filled(r, 0.0, palette.accent_soft);
            p.line_segment(
                [r.left_top(), r.right_top()],
                Stroke::new(1.0_f32, palette.accent),
            );
            p.line_segment(
                [r.left_bottom(), r.right_bottom()],
                Stroke::new(1.0_f32, palette.accent),
            );
        } else {
            style::hairline(p, r.left_top(), r.right_top(), palette.line);
            if can && response.hovered() {
                p.rect_filled(r, 0.0, palette.raised);
            }
        }
        if row.suggested {
            style::mark(
                p,
                egui::pos2(r.left() + 5.0, r.center().y),
                Mark::Accent,
                6.0,
                palette,
            );
        }
        let color = if row.warn {
            palette.warn
        } else if row.current || row.suggested {
            palette.ink
        } else {
            palette.ink2
        };
        for ((cell, col), &(l, rr)) in row.cells.iter().zip(cols).zip(&edges) {
            let (pos, anchor) = if col.left {
                (egui::pos2(l, r.center().y), Align2::LEFT_CENTER)
            } else {
                (egui::pos2(rr, r.center().y), Align2::RIGHT_CENTER)
            };
            style::paint_job(p, pos, anchor, style::job(cell, size, color, 0.0));
        }
        let response = match &row.hover {
            Some(h) => response.on_hover_text(h),
            None => response,
        };
        if can && response.clicked() {
            clicked = Some(i);
        }
    }
    clicked
}

/// A paragraph in the panel's small ink.
fn para(ui: &mut Ui, text: &str, size: f32, color: Color32) {
    let mut job = style::job(&unbreak(text), size, color, 0.0);
    job.wrap.max_width = ui.available_width();
    ui.label(job);
}

/// A source note: its label in capitals, then the sentence.
fn source(ui: &mut Ui, label: &str, text: &str, palette: &CapturePalette) {
    let mut job = style::caps_job(label, 9.0, palette.ink3);
    job.append(
        &format!("  {}", unbreak(text)),
        0.0,
        egui::TextFormat {
            font_id: egui::FontId::proportional(11.5),
            color: palette.ink3,
            ..Default::default()
        },
    );
    job.wrap.max_width = ui.available_width();
    ui.label(job);
}

fn line_color(tone: Tone, palette: &CapturePalette) -> Color32 {
    match tone {
        Tone::Note => palette.ink2,
        Tone::Good => palette.ok,
        Tone::Warn => palette.warn,
    }
}

fn clock_in(seconds: Option<f64>) -> String {
    seconds.map_or("—".into(), style::local_time_in)
}

fn current_planes(s: &Snapshot, step: u16) -> Option<usize> {
    let host = &s.host;
    host.bounds_set().then(|| {
        let (a, b) = host.plan_bounds();
        plan::plane_count(a, b, step.max(1))
    })
}

/// The comparison panel ("What changes"), drawn left of the inspector over
/// the canvas. Returns what was chosen and whether it asked to close.
pub(crate) fn show_panel(
    ctx: &egui::Context,
    anchor: Rect,
    tab: &mut GuideTab,
    inputs: &GuideInputs<'_>,
    palette: &CapturePalette,
) -> (Vec<PlanIntent>, bool) {
    let mut out = Vec::new();
    let mut close = false;
    let width = (anchor.left() - 40.0).clamp(380.0, 700.0);
    // Below the pre-flight strip (36 px), left of the inspector.
    let pos = egui::pos2(anchor.left() - width - 16.0, anchor.top() + 48.0);
    // Down to just above the depth rail (about 150 px from the bottom).
    let max_h = (ctx.content_rect().bottom() - 150.0 - pos.y).max(240.0);
    egui::Area::new(egui::Id::new("capture-guide"))
        .order(egui::Order::Foreground)
        .fixed_pos(pos.max(egui::pos2(8.0, anchor.top())))
        .show(ctx, |ui| {
            egui::Frame::new()
                .fill(palette.panel)
                .stroke(Stroke::new(1.0_f32, palette.line2))
                .inner_margin(egui::Margin::symmetric(18, 14))
                .show(ui, |ui| {
                    ui.set_width(width - 36.0);
                    // An area's room is last frame's size; give the body the
                    // window's height so a taller section can grow into it.
                    ui.set_max_height(max_h);
                    ui.spacing_mut().item_spacing.y = 6.0;
                    ui.horizontal(|ui| {
                        ui.label(style::caps_job("What changes", 11.0, palette.ink));
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if style::button(ui, "Close", ButtonKind::Quiet, 22.0, true, palette)
                                .clicked()
                            {
                                close = true;
                            }
                        });
                    });
                    ui.horizontal(|ui| {
                        ui.spacing_mut().item_spacing.x = 4.0;
                        for t in GuideTab::ALL {
                            let kind = if *tab == t {
                                ButtonKind::On
                            } else {
                                ButtonKind::Quiet
                            };
                            if style::button(ui, t.label(), kind, 24.0, true, palette).clicked() {
                                *tab = t;
                            }
                        }
                    });
                    let top = ui.cursor().top();
                    style::hairline(
                        ui.painter(),
                        egui::pos2(ui.max_rect().left(), top),
                        egui::pos2(ui.max_rect().right(), top),
                        palette.line,
                    );
                    ui.add_space(4.0);
                    egui::ScrollArea::vertical()
                        .id_salt("capture-guide-body")
                        .max_height(max_h - 90.0)
                        .auto_shrink([false, true])
                        .show(ui, |ui| match *tab {
                            GuideTab::Exposure => exposure_tab(ui, inputs, palette, &mut out),
                            GuideTab::Step => step_tab(ui, inputs, palette, &mut out),
                            GuideTab::Settle => settle_tab(ui, inputs, palette, &mut out),
                            GuideTab::Light => light_tab(ui, inputs, palette, &mut out),
                        });
                });
        });
    if ctx.input(|i| i.key_pressed(egui::Key::Escape)) {
        close = true;
    }
    (out, close)
}

fn exposure_tab(
    ui: &mut Ui,
    inputs: &GuideInputs<'_>,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let s = inputs.s;
    let Some(e) = s.host.exposure.as_ref() else {
        para(
            ui,
            "The camera reports its exposure once connected.",
            12.5,
            palette.ink2,
        );
        return;
    };
    let m = metered(inputs.test_shot);
    let advice = advise(e, m.as_ref());
    let planes = current_planes(s, inputs.step);
    let rows = exposure_rows(s, inputs.settle_ms, planes, m.as_ref(), &advice);
    para(
        ui,
        "Best: the camera's base ISO and the longest exposure that does not clip. Noise follows the light collected, not the ISO.",
        13.0,
        palette.ink,
    );
    if let Some(line) = exposure_line(&advice, &rows) {
        para(ui, &line.text, 12.5, line_color(line.tone, palette));
    }
    ui.add_space(4.0);
    let cols = [
        Col {
            head: "Exposure",
            left: true,
        },
        Col {
            head: "ISO",
            left: false,
        },
        Col {
            head: "Noise",
            left: false,
        },
        Col {
            head: "SNR",
            left: false,
        },
        Col {
            head: "Highlights",
            left: false,
        },
        Col {
            head: "A plane",
            left: false,
        },
        Col {
            head: "Stack",
            left: false,
        },
        Col {
            head: "Ends",
            left: false,
        },
    ];
    let table: Vec<Row> = rows
        .iter()
        .map(|r| Row {
            cells: vec![
                style::shutter_label(r.shutter),
                style::iso_label(r.iso).trim_start_matches("ISO ").to_owned(),
                if r.current {
                    "now".into()
                } else {
                    format!("{} st", signed(r.noise_stops, 1))
                },
                if r.current {
                    "now".into()
                } else {
                    format!("{} dB", signed(r.snr_db, 1))
                },
                match (r.clip, r.highlight) {
                    (Clip::Clips, _) => "clips".into(),
                    (_, Some(h)) => format!("{:.0} %", 100.0 * h),
                    _ => "—".into(),
                },
                r.plane.map_or("—".into(), |p| format!("{p:.1} s")),
                r.stack.map_or("—".into(), style::minutes),
                clock_in(r.stack),
            ],
            current: r.current,
            suggested: r.suggested,
            warn: matches!(r.clip, Clip::Clips | Clip::Near),
            hover: Some(format!(
                "{} at {}: noise {} stops and SNR {} dB against now (estimate: SNR rises as the square root of the exposure). {}",
                style::shutter_label(r.shutter),
                style::iso_label(r.iso),
                signed(r.noise_stops, 2),
                signed(r.snr_db, 1),
                match r.clip {
                    Clip::Unknown => "Highlights unknown: take a test shot.".to_owned(),
                    Clip::Safe => "Highlights stay under 90 % of full scale.".to_owned(),
                    Clip::Near => "Highlights within 0.15 stop of clipping.".to_owned(),
                    Clip::Clips => "Highlights clip.".to_owned(),
                }
            )),
        })
        .collect();
    if let Some(i) = ruled_table(
        ui,
        "guide-exposure",
        &cols,
        &table,
        inputs.editable,
        palette,
    ) {
        let r = &rows[i];
        out.push(PlanIntent::Exposure {
            iso: r.iso,
            shutter: r.shutter,
        });
    }
    ui.add_space(2.0);
    para(
        ui,
        "Click a row to use it. ● suggested. Times are for the marked range at the plan's step; Ends if started now.",
        11.5,
        palette.ink3,
    );
    ui.add_space(4.0);
    source(
        ui,
        "Measured",
        "On the A7CR (2026-11-20), final-image SNR fell as the square root of the exposure: 0.6 s 67.7, 1/6 s 32.4, 1/25 s 15.4. ISO adds no noise of its own: at 1/25 s, ISO 100 pushed four stops gave SNR 12.1 against 11.0 at ISO 1600.",
        palette,
    );
    source(
        ui,
        "Measured",
        "Below about 1/6 s a plane hardly gets faster (four-shot 4.3-4.4 s against 5.7 s at 0.6 s) while noise keeps rising; at 1/25 s and ISO 1600 the Wi-Fi carried 63 of its 69 MB/s and RAWs were 67 MB on the wire against 48 MB at ISO 100.",
        palette,
    );
    source(
        ui,
        "Estimate",
        "Highlights: the test RAW's brightest 0.1 % scaled by ISO x exposure (RAW is linear); the suggestion keeps it under 90 %. Plane and stack times: the camera host's own estimate.",
        palette,
    );
    source(
        ui,
        "Argued",
        "More light, not a longer exposure, gives both speed and low noise.",
        palette,
    );
}

fn step_tab(
    ui: &mut Ui,
    inputs: &GuideInputs<'_>,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let s = inputs.s;
    let rows = plan::step_rows(s, inputs.step, inputs.settle_ms, &inputs.calibration.result);
    para(
        ui,
        "Best: a step of about the sharp width / 5 to / 7. Coarser loses fine detail between planes; finer adds planes, time and disk but keeps no more detail and lowers no noise.",
        13.0,
        palette.ink,
    );
    let width = inputs.calibration.result["width"].as_f64();
    let suggested = inputs.calibration.result["suggested_step"].as_u64();
    para(
        ui,
        &match width {
            Some(w) => format!(
                "Calibrated: detail stays sharp over about {w:.0} units, so steps up to {:.0} keep it{}.",
                (w / KNEE).floor().max(1.0),
                suggested.map(|s| format!("; the calibration suggests {s}")).unwrap_or_default()
            ),
            None => "Not calibrated: the table cannot say what a step keeps on this subject. Calibrate step (25 single RAWs, about a minute) first.".into(),
        },
        12.5,
        if width.is_some() { palette.ink2 } else { palette.warn },
    );
    if rows.is_empty() {
        para(
            ui,
            "Mark the start and end to compare steps.",
            12.5,
            palette.ink2,
        );
        return;
    }
    ui.add_space(4.0);
    let cols = [
        Col {
            head: "Step",
            left: true,
        },
        Col {
            head: "Sharp in",
            left: false,
        },
        Col {
            head: "Detail kept",
            left: false,
        },
        Col {
            head: "Noise",
            left: false,
        },
        Col {
            head: "Planes",
            left: false,
        },
        Col {
            head: "RAWs",
            left: false,
        },
        Col {
            head: "Time",
            left: false,
        },
        Col {
            head: "Ends",
            left: false,
        },
        Col {
            head: "Disk",
            left: false,
        },
    ];
    let shots = s.host.shots() as usize;
    let table: Vec<Row> = rows
        .iter()
        .map(|r| Row {
            cells: vec![
                r.step.to_string(),
                r.overlap
                    .map_or("—".into(), |o| format!("{:.0} planes", o.floor().max(0.0))),
                r.detail.as_ref().map_or("—".into(), detail_label),
                "same".into(),
                r.planes.to_string(),
                (r.planes * shots).to_string(),
                r.seconds.map_or("—".into(), style::minutes),
                clock_in(r.seconds),
                r.bytes.map_or("—".into(), style::gigabytes),
            ],
            current: r.current,
            suggested: suggested == Some(u64::from(r.step)),
            warn: r.risk,
            hover: r.detail.map(|d| {
                format!(
                    "Step {}: fine detail kept {:.1}-{:.1} % at the worst 10 % of points, between the two measured stacks{}.",
                    r.step,
                    100.0 * d.low,
                    100.0 * d.high,
                    if d.beyond { " (coarser than either was measured)" } else { "" }
                )
            }),
        })
        .collect();
    if let Some(i) = ruled_table(ui, "guide-step", &cols, &table, inputs.editable, palette) {
        out.push(PlanIntent::SetStep(rows[i].step));
    }
    ui.add_space(2.0);
    para(
        ui,
        "Click a row to use it. ● the calibration's suggestion; amber past width / 5. Sharp in: how many planes hold any point sharp.",
        11.5,
        palette.ink3,
    );
    ui.add_space(4.0);
    source(
        ui,
        "Measured",
        "Two stacks taken at step 8 and rendered from every k-th plane (2026-11-20): the scarab (width 113) kept 99.0 % of fine detail at step 16, 98.8 % at 24, 94.6 % at 32, 89.5 % at 48; the dark-background stack (width 88) 98.9 % at 16, 98.3 % at 24, 96.2 % at 48. The knee is about width / 5.",
        palette,
    );
    source(
        ui,
        "Measured",
        "Noise is set by the exposure, not the step: the pyramid merge picks per detail band and does not average planes; flat-tile noise moved -21 to +19 % from step to step with no direction.",
        palette,
    );
    source(
        ui,
        "Estimate",
        "Detail kept is read between those two stacks at this calibration's width (the lower shown); another subject may differ. Time, RAWs and disk: the camera host's rules and the last capture's size per RAW.",
        palette,
    );
}

fn settle_tab(
    ui: &mut Ui,
    inputs: &GuideInputs<'_>,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let s = inputs.s;
    para(
        ui,
        "Best: 500 ms in a still room; it costs nothing, the lens moves while the last RAW is fetched. With people moving about, 2 s on every plane is the safe choice (about 1.4 s more a plane).",
        13.0,
        palette.ink,
    );
    para(
        ui,
        &format!(
            "The plane straight after the approach move (the first, and a retake's) always settles at least {:.0} s; the camera host does that itself.",
            f64::from(FIRST_PLANE_SETTLE_MS) / 1000.0
        ),
        12.5,
        palette.ink2,
    );
    ui.add_space(4.0);
    let planes = current_planes(s, inputs.step);
    let rows = settle_rows(s, planes, inputs.settle_ms);
    let cols = [
        Col {
            head: "Settle",
            left: true,
        },
        Col {
            head: "A plane",
            left: false,
        },
        Col {
            head: "Stack",
            left: false,
        },
        Col {
            head: "Passed, still",
            left: false,
        },
        Col {
            head: "Someone walking",
            left: false,
        },
    ];
    let table: Vec<Row> = rows
        .iter()
        .map(|r| Row {
            cells: vec![
                format!("{} ms", r.ms),
                r.plane.map_or("—".into(), |p| format!("{p:.1} s")),
                r.stack.map_or("—".into(), style::minutes),
                r.still.unwrap_or("—").into(),
                r.walking.unwrap_or("—").into(),
            ],
            current: r.current,
            suggested: false,
            warn: false,
            hover: None,
        })
        .collect();
    if let Some(i) = ruled_table(ui, "guide-settle", &cols, &table, inputs.editable, palette) {
        out.push(PlanIntent::SetSettle(rows[i].ms));
    }
    ui.add_space(2.0);
    para(
        ui,
        "Click a row to use it. Passed: four-shot groups the checker accepted, out of the groups taken.",
        11.5,
        palette.ink3,
    );
    ui.add_space(4.0);
    source(
        ui,
        "Measured",
        "Interleaved 12-plane runs (2026-11-20): plane period 5.66-5.69 s at 500 ms, 6.00-6.02 s at 1 s, 7.03-7.05 s at 2 s. At 500 ms two of three misses were the plane after the approach move, which is why it now settles 2 s; with that, 48 of 48 passed.",
        palette,
    );
    source(
        ui,
        "†",
        "Measured before the first-plane rule. A failed plane is retaken later when error correction is on, about 8.5 s each (measured).",
        palette,
    );
    source(
        ui,
        "Estimate",
        "A plane and Stack: the camera host's own estimate for this exposure.",
        palette,
    );
}

fn light_tab(
    ui: &mut Ui,
    inputs: &GuideInputs<'_>,
    palette: &CapturePalette,
    out: &mut Vec<PlanIntent>,
) {
    let s = inputs.s;
    let power = s.host.power.as_ref();
    para(
        ui,
        "With Manage power, the light switches on as a stack starts and the first plane waits for the warm-up. The light dims as it warms, most in its first minute.",
        13.0,
        palette.ink,
    );
    let Some(power) = power else {
        para(
            ui,
            "The camera host has no studio outlets configured: the light is switched by hand.",
            12.5,
            palette.ink2,
        );
        return;
    };
    if !power.manage_stack {
        para(
            ui,
            "Manage power is off: the warm-up applies to scheduled stacks that turn the light on.",
            12.5,
            palette.ink2,
        );
    }
    ui.add_space(4.0);
    let planes = current_planes(s, inputs.step);
    let rows = warmup_rows(s, planes, inputs.settle_ms);
    let cols = [
        Col {
            head: "Warm-up",
            left: true,
        },
        Col {
            head: "Adds",
            left: false,
        },
        Col {
            head: "Stack",
            left: false,
        },
        Col {
            head: "First planes",
            left: false,
        },
    ];
    let table: Vec<Row> = rows
        .iter()
        .map(|r| Row {
            cells: vec![
                format!("{} s", r.seconds),
                r.adds.map_or("—".into(), |a| format!("{a:.0} s")),
                r.stack.map_or("—".into(), style::minutes),
                if r.seconds >= 60 {
                    "after the first minute".into()
                } else {
                    "while it dims".into()
                },
            ],
            current: r.current,
            suggested: false,
            warn: false,
            hover: None,
        })
        .collect();
    if let Some(i) = ruled_table(ui, "guide-light", &cols, &table, inputs.editable, palette) {
        out.push(PlanIntent::SetWarmup(rows[i].seconds));
    }
    ui.add_space(4.0);
    source(
        ui,
        "Measured",
        "Straight after switching on, the light dimmed 9 % over the first run's 60 s and 6 % over the second's; later runs drifted -6 to +4 % with no pattern (2026-11-20).",
        palette,
    );
    source(
        ui,
        "Argued",
        "With a short warm-up the first minute of planes is brighter than the rest; its effect on the stacked image was not tested.",
        palette,
    );
}

impl super::CaptureWorkspace {
    /// A fixture's open panel (`--capture-fixture plan+NAME`): `rig`,
    /// `guide`, `guide-step`, `guide-settle`, `guide-light`, `schedule`,
    /// `schedule-in`, for offscreen renders.
    pub(super) fn open_fixture_panel(&mut self, open: &str) {
        let s = self
            .connection
            .as_ref()
            .map(crate::capture_client::Connection::snapshot)
            .unwrap_or_default();
        let plan = &mut self.station.plan;
        match open {
            "rig" => plan.rig_open = true,
            "guide" => plan.guide = Some(GuideTab::Exposure),
            "guide-step" => plan.guide = Some(GuideTab::Step),
            "guide-settle" => plan.guide = Some(GuideTab::Settle),
            "guide-light" => plan.guide = Some(GuideTab::Light),
            "schedule" | "schedule-in" => {
                self.schedule_ui.open(&s);
                if open == "schedule-in" {
                    self.schedule_ui
                        .switch(super::schedule_ui::Mode::In, chrono::Utc::now().timestamp());
                }
            }
            _ => {}
        }
    }
}

#[cfg(test)]
#[path = "capture-guide-tests.rs"]
mod tests;
