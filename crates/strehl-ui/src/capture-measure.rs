//! The calibration pass (capture calibration spec 4, ledger rows
//! `cpf-f3-light`, `cpf-s1-sweep`, `cpf-s2-pass`): one button measures, the
//! owner decides.
//!
//! | Stage | What it does |
//! | --- | --- |
//! | Sweep | 33 lens positions over 6,000 units around the seed, the preview read after each move: per-tile peaks give the range, the busiest position and a depth map ([`super::sweep`]) |
//! | Light | Waits until the light has been on [`LIGHT_SETTLED`]: its output falls 11 % in its first 140 s (MEASURED, grounding R4), and every later stage measures exposure |
//! | Test | One position, the busiest, at two shutters (the camera's, at most 1.3 s, and five stops under), read by `strehl survey`: the body's top with the highlights set aside chooses the survey's shutters. A single RAW cannot: on a subject whose glints are 48 times the body's top, its top 0.1 % is the glints at any shutter |
//! | Survey | The grid of spec 4.2 around the sweep's range at the long shutter, every second position and the ends at the short, and the dense cluster at the busiest position; read by `strehl survey` |
//! | Return | The lens back to the busiest position, the camera's exposure as it was |
//!
//! The test and the survey run on the workspace's survey machinery
//! (`tools::Calibration`): one RAW a plane, the run measured on this PC and
//! deleted, four-shot set again whatever happens. A camera reporting the
//! last session's shutter (the highlight groups' 1/40 s, grounding R4) no
//! longer sets the survey's exposure.

use std::time::{Duration, Instant};

use serde_json::{Value, json};

use super::sweep::{self, Peaks, Sweep};

/// The light must have been on this long before exposure is measured.
pub(crate) const LIGHT_SETTLED: Duration = Duration::from_secs(150);
/// The sharp depth assumed before one is known at this lens position
/// (spec 4.2: the dragonfly's 45, the 2x teleconverter's typical).
pub(crate) const DEFAULT_DEPTH: f64 = 45.0;
/// The survey's long shutter at most, seconds.
pub(crate) const LONG_MAX_S: f64 = 1.3;
/// The short shutter, stops under the long.
pub(crate) const SHORT_STOPS: f64 = 5.0;
/// The body's top is placed here by the long shutter (spec 4.2).
pub(crate) const BODY_TARGET: f64 = 0.5;
/// The dense cluster: positions, and their spacing in sharp depths (never
/// under 4 units). Its span, 4.8 depths: a cluster under four reads the
/// depth low (grounding R5).
pub(crate) const CLUSTER: usize = 25;
pub(crate) const CLUSTER_SPACING_DEPTHS: f64 = 0.2;

#[derive(Debug)]
pub(crate) enum Stage {
    Idle,
    Sweep {
        sweep: Box<Sweep>,
        /// The window was moved once already (the subject ran off an end).
        moved: bool,
    },
    Light {
        /// The light was switched on by the pass.
        sent: bool,
    },
    /// The workspace's survey machinery takes and reads the test pair.
    Test {
        position: u16,
        shutters: (u64, u64),
    },
    /// ... and then the survey.
    Survey {
        shutters: (u64, u64),
        positions: usize,
    },
    Return {
        target: u16,
        sent: bool,
    },
    Done,
    Failed(String),
}

impl std::fmt::Debug for Sweep {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let (a, b) = self.progress();
        write!(f, "Sweep({a} of {b})")
    }
}

/// What the pass has measured, each with where it came from.
#[derive(Debug, Default)]
pub(crate) struct Facts {
    pub peaks: Option<Peaks>,
    pub sweep_seconds: Option<f64>,
    pub sweep_positions: usize,
    /// The busiest position (the sweep's), where the test and the cluster
    /// are taken and the lens is left.
    pub busiest: Option<u16>,
    /// The test pair's body top at its long shutter, and the shutters the
    /// survey used (codes).
    pub test_top: Option<f64>,
    pub shutters: Option<(u64, u64)>,
    /// Seconds the light had been on when the first RAW was taken.
    pub light_on_seconds: Option<f64>,
    /// The survey's `strehl survey` JSON.
    pub survey: Option<Value>,
    /// The sweep's preview size (its tiles cover part of it).
    pub preview_size: Option<[usize; 2]>,
    /// Counts every change of the facts the lenses draw.
    pub revision: u64,
}

/// The pass and what it found.
#[derive(Debug)]
pub(crate) struct Pass {
    pub stage: Stage,
    pub facts: Facts,
    pub started: Option<Instant>,
    pub finished: Option<std::time::SystemTime>,
    /// The camera's ISO and shutter before the pass, put back after.
    pub exposure_before: Option<(u64, u64)>,
    /// The camera took four RAWs a plane before the pass.
    pub four_before: bool,
    /// The stage that did not finish, for "Run the rest".
    pub stopped_in: Option<&'static str>,
}

impl Default for Pass {
    fn default() -> Self {
        Self {
            stage: Stage::Idle,
            facts: Facts::default(),
            started: None,
            finished: None,
            exposure_before: None,
            four_before: false,
            stopped_in: None,
        }
    }
}

impl Pass {
    pub fn running(&self) -> bool {
        !matches!(self.stage, Stage::Idle | Stage::Done | Stage::Failed(_))
    }

    /// The stage name snapshots and the column report.
    pub fn stage_name(&self) -> &'static str {
        match self.stage {
            Stage::Idle => "idle",
            Stage::Sweep { .. } => "sweep",
            Stage::Light { .. } => "light",
            Stage::Test { .. } => "test",
            Stage::Survey { .. } => "survey",
            Stage::Return { .. } => "return",
            Stage::Done => "done",
            Stage::Failed(_) => "failed",
        }
    }

    /// The test pair is being taken: its outline must not become the
    /// subject (it is one position).
    pub fn testing(&self) -> bool {
        matches!(self.stage, Stage::Test { .. })
    }

    /// Stops at once; what was measured stays.
    pub fn stop(&mut self, why: &str) {
        if self.running() {
            self.stopped_in = Some(self.stage_name());
            self.stage = Stage::Failed(why.into());
        }
    }

    /// One line of what the pass is doing (the column's running state).
    pub fn doing(&self, now: Instant, light_on: Option<Duration>) -> String {
        match &self.stage {
            Stage::Sweep { sweep, .. } => {
                let (done, all) = sweep.progress();
                format!(
                    "Sweeping the lens: {done} of {all} positions, {:.0} s",
                    now.duration_since(sweep.started).as_secs_f64()
                )
            }
            Stage::Light { .. } => match light_on {
                Some(on) => format!(
                    "Waiting for the light to settle: {:.0} s of {}",
                    on.as_secs_f64(),
                    LIGHT_SETTLED.as_secs()
                ),
                None => "Switching the light on".into(),
            },
            Stage::Test { .. } => "Test pair at the busiest position: two single RAWs".into(),
            Stage::Survey { positions, .. } => {
                format!("Survey: {positions} single RAWs, then read on this PC")
            }
            Stage::Return { .. } => "Putting the lens and the camera back".into(),
            Stage::Done => "Calibrated".into(),
            Stage::Failed(why) => why.clone(),
            Stage::Idle => String::new(),
        }
    }

    /// For snapshots (`capture.tools.calibration.pass`).
    pub fn public(&self) -> Value {
        let p = self.facts.peaks.as_ref();
        json!({
            "stage": self.stage_name(),
            "seconds": self.started.map(|t| t.elapsed().as_secs_f64()),
            "error": match &self.stage { Stage::Failed(w) => Some(w.clone()), _ => None },
            "stopped_in": self.stopped_in,
            "sweep": p.map(|p| json!({
                "range": p.range, "busiest": p.busiest, "kept_tiles": p.kept,
                "window": p.window, "offset": p.offset,
                "seconds": self.facts.sweep_seconds, "positions": self.facts.sweep_positions,
            })),
            "busiest": self.facts.busiest,
            "test_top": self.facts.test_top,
            "shutters": self.facts.shutters,
            "light_on_seconds": self.facts.light_on_seconds,
            "survey_depth": self.facts.survey.as_ref().map(|v| v["depth"].clone()),
        })
    }
}

impl Pass {
    /// Stages passed of five, for the column's progress line.
    pub fn passed(&self) -> usize {
        match self.stage {
            Stage::Idle | Stage::Sweep { .. } => 0,
            Stage::Light { .. } => 1,
            Stage::Test { .. } => 2,
            Stage::Survey { .. } => 3,
            Stage::Return { .. } => 4,
            Stage::Done => 5,
            Stage::Failed(_) => 0,
        }
    }

    /// The readout (spec 6.4): what, its value, where it came from. Rows
    /// appear as their facts are measured; nothing reflows.
    pub fn rows(&self) -> Vec<[String; 3]> {
        let mut rows = Vec::new();
        let units = |v: f64| super::style::focus_units(v.round().clamp(0.0, 65535.0) as u16);
        let survey = self.facts.survey.as_ref();
        let depth = survey.map(|v| &v["depth"]);
        let surveyed = depth.and_then(|d| {
            Some((
                d["in_focus_first"].as_f64()?,
                d["in_focus_last"].as_f64()?,
                d["per_position"].as_array().map_or(0, Vec::len),
                d["reaches_first"].as_bool().unwrap_or(false)
                    || d["reaches_last"].as_bool().unwrap_or(false),
            ))
        });
        if let Some((a, b, n, reaches)) = surveyed {
            rows.push([
                "In focus".into(),
                format!(
                    "{} \u{2013} {}{}",
                    units(a),
                    units(b),
                    if reaches { ", and past an end" } else { "" }
                ),
                format!("survey, {n} frames"),
            ]);
        } else if let Some(p) = &self.facts.peaks
            && let Some((a, b)) = p.range
        {
            rows.push([
                "In focus".into(),
                format!("{} \u{2013} {}", units(a), units(b)),
                format!(
                    "live sweep, {} positions in {:.0} s",
                    self.facts.sweep_positions,
                    self.facts.sweep_seconds.unwrap_or(0.0)
                ),
            ]);
        }
        let Some(v) = survey else {
            return rows;
        };
        if let Some(share) = v["subject"]["area_share"].as_f64() {
            rows.push([
                "Outline".into(),
                format!("{:.0} % of the frame", 100.0 * share),
                "from the survey".into(),
            ]);
        }
        let step = &v["step"];
        if let Some(w) = step["width"].as_f64() {
            let spread = match (step["width_p10"].as_f64(), step["width_p90"].as_f64()) {
                (Some(a), Some(b)) => format!("{a:.0} to {b:.0} across the subject \u{b7} "),
                _ => String::new(),
            };
            rows.push([
                "Sharp depth".into(),
                format!(
                    "{w:.0} units{}",
                    if step["width_low"].as_bool() == Some(true) {
                        ", low: the cluster was short"
                    } else {
                        ""
                    }
                ),
                format!(
                    "{spread}{} RAWs {:.0} apart",
                    step["positions"].as_u64().unwrap_or(0),
                    step["spacing"].as_f64().unwrap_or(0.0)
                ),
            ]);
        }
        let top = v["body"]["top"].as_f64().filter(|t| *t > 0.0);
        let long = v["shutters"]["long_effective_s"].as_f64();
        if let (Some(top), Some(long)) = (top, long) {
            let full = long / top;
            let median = v["body"]["g"]["p50"].as_f64();
            rows.push([
                "Body".into(),
                format!(
                    "full scale at {}{}",
                    seconds_label(full),
                    median
                        .map(|m| format!("; median {:.1} %", 100.0 * m))
                        .unwrap_or_default()
                ),
                format!(
                    "{} positions{}",
                    v["positions"]["pairs"].as_u64().unwrap_or(0),
                    self.facts
                        .light_on_seconds
                        .map(|s| format!(", light on {:.0} min", s / 60.0))
                        .unwrap_or_default()
                ),
            ]);
        }
        if let (Some(census), Some(top)) = (v["census"]["top"].as_f64(), top) {
            let stops = (census / top).log2();
            rows.push([
                "Highlights".into(),
                if stops > 0.0 {
                    format!("up to {stops:.1} stops over the body's top")
                } else {
                    "none over the body's top".into()
                },
                format!(
                    "{} positions, short frames",
                    v["positions"]["pairs"].as_u64().unwrap_or(0)
                ),
            ]);
        }
        rows
    }

    /// The column's view.
    pub fn view(
        &self,
        now: Instant,
        light_on: Option<Duration>,
        available: bool,
    ) -> super::plan::PassView {
        super::plan::PassView {
            stage: self.stage_name(),
            doing: self.doing(now, light_on),
            passed: self.passed(),
            finished: self.finished,
            rows: self.rows(),
            available,
        }
    }
}

/// "1.6 s" or "1/40 s".
fn seconds_label(s: f64) -> String {
    if s >= 0.3 {
        format!("{s:.1} s")
    } else {
        format!("1/{:.0} s", 1.0 / s)
    }
}

/// The sweep's seed (spec 4.1): the lens position if the owner moved it
/// since the camera connected; else the middle of the marks the host still
/// holds; else the lens position.
pub(crate) fn seed(position: u16, moved: bool, marks: Option<(u16, u16)>) -> u16 {
    match (moved, marks) {
        (false, Some((a, b))) => ((u32::from(a) + u32::from(b)) / 2) as u16,
        _ => position,
    }
}

pub(crate) fn start_sweep(seed: u16, reach: (u16, u16), now: Instant) -> Stage {
    Stage::Sweep {
        sweep: Box::new(Sweep::new(sweep::window(seed, reach), now)),
        moved: false,
    }
}

/// The seconds a shutter code exposes for.
fn seconds(code: u64) -> Option<f64> {
    strehl_capture::timing::shutter_seconds(code)
}

/// The offered code nearest `want` seconds (in stops), at most `max`.
pub(crate) fn nearest(options: &[u64], want: f64, max: f64) -> Option<u64> {
    options
        .iter()
        .filter_map(|&c| Some((c, seconds(c)?)))
        .filter(|(_, t)| *t <= max * 1.02)
        .min_by(|a, b| {
            (a.1 / want)
                .ln()
                .abs()
                .total_cmp(&(b.1 / want).ln().abs())
                .then(a.1.total_cmp(&b.1))
        })
        .map(|(c, _)| c)
}

/// The test pair's shutters: the camera's, at most 1.3 s, and five stops
/// under it.
pub(crate) fn test_shutters(options: &[u64], current: u64) -> Option<(u64, u64)> {
    let t = seconds(current)?.min(LONG_MAX_S);
    let long = nearest(options, t, LONG_MAX_S)?;
    let short = nearest(options, seconds(long)? / 2f64.powf(SHORT_STOPS), LONG_MAX_S)?;
    Some((long, short))
}

/// The survey's shutters from the test pair's body top at its long shutter
/// (spec 4.2): the long puts the top nearest [`BODY_TARGET`], at most
/// 1.3 s; the short is five stops under it. A top that is not measured, or
/// at the pin, keeps the test's long shutter (`None`: keep the test's pair).
pub(crate) fn survey_shutters(
    options: &[u64],
    test_long: u64,
    top: Option<f64>,
) -> Option<(u64, u64)> {
    let t = seconds(test_long)?;
    let top = top.filter(|v| v.is_finite() && *v > 0.0 && *v < 0.98)?;
    let long = nearest(options, t * BODY_TARGET / top, LONG_MAX_S)?;
    let short = nearest(options, seconds(long)? / 2f64.powf(SHORT_STOPS), LONG_MAX_S)?;
    Some((long, short))
}

/// The survey grid (spec 4.2): from `first - 3 w0` to `last + 2 w0`, `w0`
/// apart, long at every position, short at every second and at the ends;
/// the dense cluster of [`CLUSTER`] positions `w0 / 5` apart (at least 4)
/// centred on `busiest`, long. In increasing focus, a position's long before
/// its short; inside `reach`.
pub(crate) fn survey_grid(
    range: (f64, f64),
    busiest: f64,
    w0: f64,
    shutters: (u64, u64),
    reach: (u16, u16),
) -> (Vec<u16>, Vec<u64>) {
    let (near, far) = (f64::from(reach.0), f64::from(reach.1.max(reach.0)));
    let clamp = |p: f64| p.round().clamp(near, far).clamp(0.0, 65535.0) as u16;
    let (lo, hi) = (range.0 - 3.0 * w0, range.1 + 2.0 * w0);
    let n = (((hi - lo) / w0).ceil() as usize).max(1) + 1;
    let mut taken: Vec<(u16, u8, u64)> = Vec::new();
    for i in 0..n {
        let p = clamp(lo + w0 * i as f64);
        taken.push((p, 0, shutters.0));
        if i % 2 == 0 || i + 1 == n {
            taken.push((p, 1, shutters.1));
        }
    }
    let spacing = (CLUSTER_SPACING_DEPTHS * w0).max(4.0);
    let start = busiest - spacing * (CLUSTER as f64 - 1.0) / 2.0;
    for i in 0..CLUSTER {
        taken.push((clamp(start + spacing * i as f64), 0, shutters.0));
    }
    taken.sort_by_key(|t| (t.0, t.1));
    taken.dedup();
    taken.into_iter().map(|(p, _, s)| (p, s)).unzip()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Sony codes: numerator << 16 | denominator.
    fn code(n: u64, d: u64) -> u64 {
        (n << 16) | d
    }

    fn options() -> Vec<u64> {
        vec![
            code(13, 10),
            code(1, 1),
            code(1, 2),
            code(1, 4),
            code(1, 8),
            code(1, 15),
            code(1, 30),
            code(1, 40),
            code(1, 60),
            code(1, 125),
            code(2, 1),
        ]
    }

    #[test]
    fn the_test_pair_is_the_cameras_shutter_and_five_stops_under() {
        let (l, s) = test_shutters(&options(), code(2, 1)).unwrap();
        assert_eq!(l, code(13, 10), "at most 1.3 s");
        assert_eq!(s, code(1, 30));
        let (l, _) = test_shutters(&options(), code(1, 40)).unwrap();
        assert_eq!(l, code(1, 40));
    }

    #[test]
    fn the_survey_shutter_puts_the_body_top_at_half() {
        // A camera left at 1/40 s: the top reads 0.0148; the long that puts
        // it at 0.5 is about 0.84 s, the nearest offered 1 s.
        let (l, s) = survey_shutters(&options(), code(1, 40), Some(0.0148)).unwrap();
        assert_eq!(l, code(1, 1));
        assert_eq!(s, code(1, 30));
        // At 1.3 s a top of 0.77: about 0.84 s again.
        let (l, _) = survey_shutters(&options(), code(13, 10), Some(0.77)).unwrap();
        assert_eq!(l, code(1, 1));
        // Never past 1.3 s.
        let (l, _) = survey_shutters(&options(), code(13, 10), Some(0.05)).unwrap();
        assert_eq!(l, code(13, 10));
        assert_eq!(survey_shutters(&options(), code(13, 10), Some(1.0)), None);
        assert_eq!(survey_shutters(&options(), code(13, 10), None), None);
    }

    #[test]
    fn the_grid_spans_the_range_with_its_margins_and_the_cluster() {
        let (p, s) = survey_grid((32_355.0, 33_161.0), 32_742.0, 45.0, (1, 2), (1509, 63_487));
        assert_eq!(p.len(), s.len());
        assert_eq!(p[0], 32_220);
        assert!(*p.last().unwrap() >= 33_251);
        assert!(p.windows(2).all(|w| w[0] <= w[1]), "increasing focus");
        let longs = s.iter().filter(|c| **c == 1).count();
        let shorts = s.iter().filter(|c| **c == 2).count();
        // 24 grid positions, 13 shorts, the cluster's 25 of which five fall
        // on the grid.
        assert_eq!(longs, 24 + 25 - 5);
        assert_eq!(shorts, 13);
        // The cluster: 9 apart around 32,742.
        assert!(p.contains(&32_634) && p.contains(&32_850));
    }

    #[test]
    fn the_seed_follows_the_lens_once_moved() {
        assert_eq!(seed(51_048, false, Some((32_062, 33_262))), 32_662);
        assert_eq!(seed(40_000, true, Some((32_062, 33_262))), 40_000);
        assert_eq!(seed(40_000, false, None), 40_000);
    }
}
