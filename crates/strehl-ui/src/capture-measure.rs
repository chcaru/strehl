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
    /// The camera's exposure as it was, then the lens to `target`: one
    /// command at a time (a host given both in one frame applied the first
    /// and dropped the second, MEASURED on the rig 2026-11-27); a move not
    /// seen done is sent again.
    Return {
        target: u16,
        exposure_sent: bool,
        moved: Option<Instant>,
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
    /// The proof planes taken since the pass (spec 5.8), and how many more
    /// are asked for.
    pub proofs: Vec<ProofResult>,
    pub proofs_wanted: usize,
}

/// One proof plane (spec 5.8): a four-shot group exactly as the plan stands
/// at the busiest position, checked as the capture checks its groups, and
/// the highlight group after it when the plan has them.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ProofResult {
    /// "pass", "demote" or "retake" (the check's verdict), and its reason.
    pub verdict: String,
    pub reason: Option<String>,
    /// The capture would have retaken it.
    pub retake: bool,
    /// The shots' local disagreement at the 99th percentile and its limit
    /// (photosites), and the largest member residual.
    pub local_px: Option<f64>,
    pub limit_px: Option<f64>,
    pub residual_px: Option<f64>,
    /// Seconds the plane took (base and highlight groups).
    pub seconds: f64,
    /// The check's per-tile local disagreement (the Still lens): columns,
    /// rows, sensor pixels a tile, values (NaN where not measured).
    pub map: Option<(usize, usize, f32, Vec<f32>)>,
}

impl ProofResult {
    /// From `strehl pixel-shift --json`'s first group.
    pub fn from_report(v: &Value, seconds: f64) -> Option<Self> {
        let g = v["groups"].as_array()?.first()?;
        let residual = g["residual_px"].as_array().map(|r| {
            r.iter()
                .filter_map(|p| Some(p.get(0)?.as_f64()?.hypot(p.get(1)?.as_f64()?)))
                .fold(0.0, f64::max)
        });
        let map = (|| {
            let grid = g["tile_grid"].as_array()?;
            let (cols, rows) = (
                grid.first()?.as_u64()? as usize,
                grid.get(1)?.as_u64()? as usize,
            );
            let tile = g["tile"].as_f64()? as f32 * 2.0;
            let values: Vec<f32> = g["tile_local_map"]
                .as_array()?
                .iter()
                .map(|v| v.as_f64().map_or(f32::NAN, |x| x as f32))
                .collect();
            (values.len() == cols * rows).then_some((cols, rows, tile, values))
        })();
        Some(Self {
            verdict: g["verdict"].as_str().unwrap_or("unknown").to_owned(),
            reason: g["gate"]["reason"].as_str().map(str::to_owned),
            retake: g["gate"]["retake"].as_bool().unwrap_or(false),
            local_px: g["gate"]["local_px"].as_f64(),
            limit_px: g["gate"]["local_tolerance_px"].as_f64(),
            residual_px: residual,
            seconds,
            map,
        })
    }

    /// Clean: the checker passed it (its shots agree). A group the capture's
    /// gate keeps can still be demoted by the checker (MEASURED on the rig
    /// 2026-11-27: kept at 0.29 px local, demoted for its witness pairs).
    pub fn clean(&self) -> bool {
        self.reason.is_none() && self.verdict.starts_with("pass")
    }
}

/// The proof's stages, driven once a frame by the workspace.
#[derive(Debug, Default)]
pub(crate) enum Proof {
    #[default]
    Idle,
    /// A test run being taken: the base group, then the highlight group.
    Base {
        sequence: u64,
        since: Instant,
    },
    Highlight {
        sequence: u64,
        base: std::path::PathBuf,
        since: Instant,
        base_seconds: f64,
    },
    /// The base group being checked by the engine.
    Checking {
        base: std::path::PathBuf,
        others: Vec<std::path::PathBuf>,
        job: Box<super::tools::EngineJob>,
        seconds: f64,
    },
    Failed(String),
}

impl std::fmt::Debug for super::tools::EngineJob {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "EngineJob({:.0} s)", self.elapsed().as_secs_f64())
    }
}

impl Proof {
    pub fn running(&self) -> bool {
        matches!(
            self,
            Self::Base { .. } | Self::Highlight { .. } | Self::Checking { .. }
        )
    }
}

/// "3 of 5 groups clean, 1 would be retaken" (spec 5.8).
pub(crate) fn proof_line(proofs: &[ProofResult]) -> Option<String> {
    let last = proofs.last()?;
    let clean = proofs.iter().filter(|p| p.clean()).count();
    let retaken = proofs.iter().filter(|p| p.retake).count();
    let secs = proofs.iter().map(|p| p.seconds).sum::<f64>() / proofs.len() as f64;
    Some(if proofs.len() == 1 {
        let within = match (last.local_px, last.limit_px) {
            (Some(l), Some(m)) => format!(": its shots within {l:.2} px (limit {m:.2})"),
            _ => String::new(),
        };
        format!(
            "{}{within}; {secs:.1} s a plane",
            if last.clean() {
                "clean"
            } else if last.retake {
                "would be retaken"
            } else {
                "not clean, kept"
            }
        )
    } else {
        format!(
            "{clean} of {} groups clean, {retaken} would be retaken; {secs:.1} s a plane",
            proofs.len()
        )
    })
}

/// What calibrations taught about the lens (spec 8), by focus position to
/// the nearest [`MEMORY_BIN`] units, newest last: the sharp depth and the
/// coarse-to-fine offset. They seed the next calibration there; they are
/// never shown as a subject's figures (the sharp depth differed by a third
/// between subjects at one position, grounding R5).
#[derive(Clone, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub(crate) struct LensMemory {
    pub entries: Vec<LensEntry>,
}

#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub(crate) struct LensEntry {
    pub bin: u32,
    pub width: Option<f64>,
    pub offset: Option<f64>,
    pub unix: u64,
}

/// Focus units a remembered figure covers.
pub(crate) const MEMORY_BIN: u32 = 2000;
/// Entries kept in all.
const MEMORY_KEPT: usize = 64;

impl LensMemory {
    pub fn load(path: &std::path::Path) -> Self {
        std::fs::read_to_string(path)
            .ok()
            .and_then(|t| serde_json::from_str(&t).ok())
            .unwrap_or_default()
    }
    pub fn save(&self, path: &std::path::Path) -> std::io::Result<()> {
        let text = serde_json::to_string_pretty(self).map_err(std::io::Error::other)?;
        let tmp = path.with_extension("json.tmp");
        std::fs::write(&tmp, text)?;
        std::fs::rename(&tmp, path)
    }
    fn bin(position: f64) -> u32 {
        ((position / f64::from(MEMORY_BIN)).round().max(0.0) as u32) * MEMORY_BIN
    }
    pub fn record(&mut self, position: f64, width: Option<f64>, offset: Option<f64>, unix: u64) {
        if width.is_none() && offset.is_none() {
            return;
        }
        self.entries.push(LensEntry {
            bin: Self::bin(position),
            width,
            offset,
            unix,
        });
        if self.entries.len() > MEMORY_KEPT {
            self.entries.drain(..self.entries.len() - MEMORY_KEPT);
        }
    }
    /// The newest sharp depth and offset remembered at `position`'s bin.
    pub fn seed(&self, position: f64) -> (Option<f64>, Option<f64>) {
        let bin = Self::bin(position);
        let at = || self.entries.iter().rev().filter(move |e| e.bin == bin);
        (at().find_map(|e| e.width), at().find_map(|e| e.offset))
    }
}

/// The lens's coarse-to-fine offset as this pass measured it (spec 5.3
/// point 6): the median, over preview tiles the sweep kept, of the RAW
/// survey's focus at the tile's centre less the sweep's peak (without the
/// offset it added). `None` under 30 tiles.
pub(crate) fn measured_offset(
    peaks: &Peaks,
    preview: [usize; 2],
    maps: &Value,
    active: [f64; 2],
) -> Option<f64> {
    let (cols, rows) = (
        maps["cols"].as_u64()? as usize,
        maps["rows"].as_u64()? as usize,
    );
    let tile = maps["tile_px"].as_f64().unwrap_or(64.0);
    let focus = maps["focus"].as_array()?;
    let mut d = Vec::new();
    for (t, f) in peaks.focus.iter().enumerate() {
        let Some(f) = f else { continue };
        let (tx, ty) = (t % peaks.cols, t / peaks.cols);
        let fx = (tx as f64 + 0.5) * super::sweep::TILE as f64 / preview[0].max(1) as f64;
        let fy = (ty as f64 + 0.5) * super::sweep::TILE as f64 / preview[1].max(1) as f64;
        let (rx, ry) = (
            (fx * active[0] / tile) as usize,
            (fy * active[1] / tile) as usize,
        );
        if rx >= cols || ry >= rows {
            continue;
        }
        if let Some(raw) = focus.get(ry * cols + rx).and_then(Value::as_f64) {
            d.push(raw - (f - peaks.offset));
        }
    }
    if d.len() < 30 {
        return None;
    }
    d.sort_by(f64::total_cmp);
    Some(d[d.len() / 2])
}

/// Values the owner set by hand since "New capture" (spec 3, rule 2): a
/// calibration never changes them; its own values fill the rest.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct Held {
    pub bounds: bool,
    pub step: bool,
    pub exposure: bool,
}

/// The retained-detail target of the suggested step (owner, 2026-11-26 and
/// 2026-11-27: 99 %).
pub(crate) const DETAIL_TARGET: f64 = 0.99;

/// The coarsest step whose kept detail is at least [`DETAIL_TARGET`] at the
/// sharp depth `width` (spec 5.4), by the measured retention curve.
pub(crate) fn step_for(width: f64) -> u16 {
    let mut best = 1u16;
    for step in 1..=(width.max(1.0).ceil() as u16) {
        if super::guide::detail_kept(width / f64::from(step)).low >= DETAIL_TARGET {
            best = step;
        }
    }
    best
}

/// What a finished pass sets, value by value: the plan intents to apply for
/// those not held, and the readout's words for both.
pub(crate) fn fill(
    survey: &Value,
    held: Held,
) -> (Vec<super::plan::PlanIntent>, Vec<String>, Vec<String>) {
    use super::plan::PlanIntent;
    let (mut intents, mut set, mut kept) = (Vec::new(), Vec::new(), Vec::new());
    let d = &survey["depth"];
    let unit = |v: &Value| v.as_f64().map(|f| f.round().clamp(0.0, 65535.0) as u16);
    if let (Some(lo), Some(hi)) = (unit(&d["suggested_start"]), unit(&d["suggested_end"])) {
        if held.bounds {
            kept.push("Start and End".to_string());
        } else {
            intents.push(PlanIntent::UseSubjectBounds(lo, hi));
            set.push("Start and End".to_string());
        }
    }
    if let Some(w) = survey["step"]["width"].as_f64() {
        let step = step_for(w);
        if held.step {
            kept.push("Step".to_string());
        } else {
            intents.push(PlanIntent::SetStep(step));
            set.push(format!("Step {step}"));
        }
    }
    let advice = &survey["advice"];
    let choice = match advice["suggested"].as_str() {
        Some("highlight_pass") => advice["highlight_pass"]["base_code"].as_u64().map(|b| {
            (
                b,
                advice["highlight_pass"]["short_code"].as_u64(),
                "the exposure with highlight groups",
            )
        }),
        Some("protect") => advice["protect"]["code"]
            .as_u64()
            .map(|c| (c, None, "the exposure")),
        Some("accept") => advice["accept"]["code"]
            .as_u64()
            .map(|c| (c, None, "the exposure")),
        _ => None,
    };
    if let Some((shutter, highlight, words)) = choice {
        if held.exposure {
            kept.push("the exposure".to_string());
        } else {
            intents.push(PlanIntent::UseAdvice { shutter, highlight });
            set.push(words.to_string());
        }
    }
    (intents, set, kept)
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
    /// The sharp depth and the coarse-to-fine offset this pass seeds with
    /// (remembered at this lens position, else the defaults), and the offset
    /// it measured.
    pub w0: f64,
    pub offset: Option<f64>,
    pub offset_measured: Option<f64>,
    /// What the finished pass set and what it left as the owner had it.
    pub applied: Option<(Vec<String>, Vec<String>)>,
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
            w0: DEFAULT_DEPTH,
            offset: None,
            offset_measured: None,
            applied: None,
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
                "kept_by_position": p.histogram(),
                "window": p.window, "offset": p.offset,
                "seconds": self.facts.sweep_seconds, "positions": self.facts.sweep_positions,
            })),
            "busiest": self.facts.busiest,
            "seeded": {"sharp_depth": self.w0, "offset": self.offset},
            "offset_measured": self.offset_measured,
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
        if let Some((set, kept)) = &self.applied {
            let join = |v: &[String]| match v.len() {
                0 => String::new(),
                1 => v[0].clone(),
                n => format!("{} and {}", v[..n - 1].join(", "), v[n - 1]),
            };
            rows.push([
                "Plan".into(),
                if set.is_empty() {
                    "nothing set".into()
                } else {
                    format!("set {}", join(set))
                },
                if kept.is_empty() {
                    "from this calibration".into()
                } else {
                    format!("{} kept as you set them", join(kept))
                },
            ]);
        }
        if let Some(line) = proof_line(&self.facts.proofs) {
            rows.push([
                "Proof".into(),
                line,
                format!(
                    "{} at the busiest position, as the plan stands",
                    match self.facts.proofs.len() {
                        1 => "one plane".to_owned(),
                        n => format!("{n} planes"),
                    }
                ),
            ]);
        }
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
            proof: proof_line(&self.facts.proofs),
            proving: false,
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
    fn the_step_keeps_ninety_nine_percent() {
        let s = step_for(48.0);
        assert!((4..=9).contains(&s), "{s}");
        assert!(super::super::guide::detail_kept(48.0 / f64::from(s)).low >= DETAIL_TARGET);
        assert!(super::super::guide::detail_kept(48.0 / f64::from(s + 1)).low < DETAIL_TARGET);
        assert!(
            step_for(96.0) >= s,
            "a deeper sharp depth never asks a finer step"
        );
    }

    #[test]
    fn a_pass_fills_only_what_the_owner_has_not_set() {
        use super::super::plan::PlanIntent;
        let survey = json!({"depth":{"suggested_start":32349.0,"suggested_end":33199.0},
            "step":{"width":48.0},
            "advice":{"suggested":"highlight_pass","highlight_pass":{"base_code":851978,"short_code":65636}}});
        let (intents, set, kept) = fill(&survey, Held::default());
        assert_eq!(intents.len(), 3);
        assert_eq!(intents[0], PlanIntent::UseSubjectBounds(32349, 33199));
        assert!(matches!(intents[1], PlanIntent::SetStep(_)));
        assert_eq!(
            intents[2],
            PlanIntent::UseAdvice {
                shutter: 851978,
                highlight: Some(65636)
            }
        );
        assert_eq!(set.len(), 3);
        assert!(kept.is_empty());
        let held = Held {
            bounds: false,
            step: true,
            exposure: true,
        };
        let (intents, _, kept) = fill(&survey, held);
        assert_eq!(intents, [PlanIntent::UseSubjectBounds(32349, 33199)]);
        assert_eq!(kept, ["Step", "the exposure"]);
        // A side the subject reaches has no suggestion: the marks stay.
        let past = json!({"depth":{"suggested_start":32349.0,"suggested_end":null}});
        assert!(fill(&past, Held::default()).0.is_empty());
    }

    #[test]
    fn the_lens_memory_seeds_by_position() {
        let mut m = LensMemory::default();
        m.record(32_700.0, Some(48.0), Some(27.0), 1);
        m.record(32_900.0, Some(44.0), None, 2);
        m.record(51_000.0, Some(80.0), Some(40.0), 3);
        // 32,700 and 32,900 both fall in the 32,000 bin (nearest 2,000).
        assert_eq!(m.seed(32_500.0), (Some(44.0), Some(27.0)));
        assert_eq!(m.seed(51_400.0), (Some(80.0), Some(40.0)));
        assert_eq!(m.seed(10_000.0), (None, None));
        let path =
            std::env::temp_dir().join(format!("strehl-lens-memory-{}.json", std::process::id()));
        m.save(&path).unwrap();
        assert_eq!(LensMemory::load(&path), m);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn the_offset_is_the_raw_focus_less_the_sweeps_peak() {
        // A 4 x 2 preview grid over a 128 x 64 preview; the RAW grid 2 x 1
        // tiles of 64 px over a 128 x 64 sensor; every RAW tile 30 later.
        let focus: Vec<Option<f64>> = (0..8)
            .map(|i| Some(1000.0 + 10.0 * f64::from(i % 4 / 2) + 5.0))
            .collect();
        let peaks = super::super::sweep::Peaks {
            cols: 4,
            rows: 2,
            focus: focus.clone(),
            range: None,
            busiest: None,
            kept: 8,
            at_first: 0,
            at_last: 0,
            prominent: 8,
            window: (0.0, 1.0),
            offset: 5.0,
        };
        let maps = json!({"cols":2,"rows":1,"tile_px":64,"focus":[1030.0, 1040.0]});
        // Under 30 tiles: not measured.
        assert_eq!(
            measured_offset(&peaks, [128, 64], &maps, [128.0, 64.0]),
            None
        );
        let many = super::super::sweep::Peaks {
            cols: 4,
            rows: 8,
            focus: (0..32)
                .map(|i| Some(1000.0 + 10.0 * f64::from(i % 4 / 2) + 5.0))
                .collect(),
            ..peaks
        };
        assert_eq!(
            measured_offset(&many, [128, 256], &maps, [128.0, 64.0]),
            Some(30.0)
        );
    }

    /// The proof's report as `strehl pixel-shift --json` writes it (the
    /// rig's numbers of 2026-11-27), and the line five of them make.
    #[test]
    fn proofs_read_the_checks_report() {
        let group = |verdict: &str, reason: Option<&str>, retake: bool, local: f64| {
            json!({"groups":[{"verdict":verdict,"gate":{"reason":reason,"retake":retake,
                "local_px":local,"local_tolerance_px":0.51},
                "residual_px":[[0.0,0.0],[0.1,0.05],[0.2,0.1],[0.0,0.3]],
                "tile":32,"tile_grid":[2,1],"tile_local_map":[0.2,null]}]})
        };
        let pass = ProofResult::from_report(&group("pass", None, false, 0.21), 21.9).unwrap();
        assert!(pass.clean());
        assert_eq!(
            pass.map.as_ref().map(|m| (m.0, m.1, m.2)),
            Some((2, 1, 64.0))
        );
        assert!(pass.map.as_ref().unwrap().3[1].is_nan());
        assert!((pass.residual_px.unwrap() - 0.3).abs() < 1e-9);
        let kept = ProofResult::from_report(
            &group(
                "demote: witness pairs misregistered beyond tolerance",
                None,
                false,
                0.34,
            ),
            22.5,
        )
        .unwrap();
        assert!(!kept.clean() && !kept.retake);
        assert!(
            proof_line(std::slice::from_ref(&kept))
                .unwrap()
                .starts_with("not clean, kept")
        );
        let retake = ProofResult::from_report(
            &group(
                "demote: witness pairs misregistered beyond tolerance",
                Some("witness tiles disagree locally"),
                true,
                0.67,
            ),
            22.4,
        )
        .unwrap();
        let five = [retake.clone(), pass, retake.clone(), kept, retake];
        assert_eq!(
            proof_line(&five).unwrap(),
            "1 of 5 groups clean, 3 would be retaken; 22.3 s a plane"
        );
    }

    #[test]
    fn the_seed_follows_the_lens_once_moved() {
        assert_eq!(seed(51_048, false, Some((32_062, 33_262))), 32_662);
        assert_eq!(seed(40_000, true, Some((32_062, 33_262))), 40_000);
        assert_eq!(seed(40_000, false, None), 40_000);
    }
}
