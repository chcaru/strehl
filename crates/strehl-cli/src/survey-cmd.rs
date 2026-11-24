//! `strehl survey <folder>`: one Calibrate survey that feeds every calibration
//! (plan X1 and the inputs of X2,
//! `docs/proposals/2026-11-subject-highlights-and-detail-plan.md`).
//!
//! The survey is a positions run of single-shot RAWs: about twelve positions
//! over the marked range, each at two shutters (the current one and one about
//! four stops shorter), and a dense cluster at the current shutter for the
//! step. Each group's journal events carry the commanded exposure
//! (`experiments/subject-highlights-detail-2026-11-23/impl/tiers.md`). From
//! the folder alone this reports:
//!
//! - the subject (plan S2, `strehl subject`'s code paths) from the long
//!   frames, or the one given (`--subject`, or the manifest's
//!   `plan.subject`), and its depth range;
//! - the step from the dense cluster, over the subject's 64 px tiles
//!   (`focus-step`'s measure, repeated here over a tile mask);
//! - the body's level per colour in the long frames, highlights set aside;
//! - a highlight census from the short frames, in units of the long
//!   shutter's full scale, with the exposure ratio measured per pair;
//! - the numbers plan X2's three choices need.
//!
//! Read-only over the capture. Statistics are over subject sites of the
//! decoded active area only (RGGB from the active origin, greens pooled);
//! one noise model is injected per frame (`profile::noise_model_for`).
//! Every pooled statistic is a sum of per-frame histograms, so the result
//! does not depend on the order the journal lists the shots in.

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, HashMap};
use std::path::{Path, PathBuf};
use std::time::Instant;
use strehl_core::CfaPlane;
use strehl_core::noise::{NoiseModel, Provenance};
use strehl_core::pixel_shift::cfa_colour;
use strehl_core::profile;
use strehl_core::subject::select::ABSOLUTE_MODE;
use strehl_core::subject::{
    CfaView, Depth, Evidence, Params, Quiet, Registration, Ring, quiet, rasterize, select,
};

use crate::focus_step_cmd::{EDGE, SAFE};
use crate::pixel_shift_cmd::all_groups;
use crate::subject_cmd::{SubjectJson, run_evidence};

#[derive(clap::Args, Debug)]
pub struct SurveyArgs {
    /// Survey folder: a positions run of single shots at two shutters.
    pub dir: PathBuf,
    /// Write the survey JSON to this file, as the other capture tools take
    /// it (`--json <file>`; `--out` is the same).
    #[arg(long, visible_alias = "out")]
    pub json: Option<PathBuf>,
    /// Print the survey JSON on stdout (the report goes to stderr).
    #[arg(long)]
    pub print_json: bool,
    /// Use this subject instead of finding one: a `strehl subject` JSON, or
    /// a manifest whose `plan.subject` holds one.
    #[arg(long)]
    pub subject: Option<PathBuf>,
    /// Long frames the subject is found from, spread over the positions.
    #[arg(long, default_value_t = 13)]
    pub count: usize,
    /// Do not register the subject's planes by a magnification rate.
    #[arg(long)]
    pub no_register: bool,
    /// Exposures decoded at once.
    #[arg(long, default_value_t = 4)]
    pub decodes: usize,
}

/// Subject raster cell, sensor pixels (the subject engine's).
const CELL: usize = 8;
/// A site within this many DN of white is pinned (the prototype's
/// `ladder.py`).
const PIN_MARGIN_DN: f32 = 2.0;
/// Ratio cells: the long frame's cell mean between these shares of
/// black..white, no pinned sample, and the short mean this many of its own
/// standard errors above black.
const RATIO_LOW: f32 = 0.05;
const RATIO_HIGH: f32 = 0.7;
const RATIO_SNR: f32 = 10.0;
/// Fewer selected cells than this: the ratio is not measured.
const MIN_RATIO_CELLS: usize = 100;
/// Long sites set aside from the body: the short frame shows a site within
/// two pixels above this multiple of the body's 99th percentile (scaled by
/// the measured ratio).
const SET_ASIDE_OVER_P99: f64 = 2.0;
const SET_ASIDE_RADIUS: usize = 2;
/// A highlight: more than a stop above the body's diffuse top (its colour's
/// 99.9th percentile), by more than this many noise deviations of the short
/// frame at that level.
const HIGHLIGHT_OVER_BODY: f64 = 2.0;
const HIGHLIGHT_SIGMAS: f64 = 6.0;
/// Plan X2: the body's diffuse top and the census top with its margin are
/// placed here; protection keeps the census top with its margin under 1.
const TARGET: f64 = 0.8;
/// The census is a lower bound by about a stop (plan X1).
const MARGIN_STOPS: f64 = 1.0;
/// Fewer dense positions than this: the step uses every long position.
const MIN_DENSE: usize = 5;
/// `focus-step`'s tile edge in green-site samples (64 sensor px), and its
/// thresholds.
const TILE: usize = 32;
const PEAK_OVER_FLOOR: f64 = 6.0;
const MIN_TILES: usize = 30;

// ---------------------------------------------------------------- shutters

/// A Sony ShutterSpeed code (numerator << 16 | denominator) as its marked
/// seconds; `None` when it is not a timed exposure (0, 0xffffffff, bulb).
pub fn code_seconds(code: u64) -> Option<f64> {
    if code == 0 || code >= 0xffff_ffff {
        return None;
    }
    let (n, d) = ((code >> 16) & 0xffff, code & 0xffff);
    (n > 0 && d > 0).then(|| n as f64 / d as f64)
}

/// The time a marked third-stop setting exposes for: the camera's series is
/// 2^(k/3) s, and its marks are rounded (1/60 is 1/64 s, 1.3 is 1.26 s;
/// DERIVED in the results note's Q3 and consistent with its measured
/// ratios). A mark more than 0.3 third-stops off the series is taken as
/// marked.
pub fn effective_seconds(marked: f64) -> f64 {
    let k = 3.0 * marked.log2();
    if (k - k.round()).abs() <= 0.3 {
        2f64.powf(k.round() / 3.0)
    } else {
        marked
    }
}

fn code_effective(code: u64) -> Option<f64> {
    code_seconds(code).map(effective_seconds)
}

/// The offered code nearest `seconds` (effective times, in stops).
pub fn nearest_code(offered: &[u64], seconds: f64) -> Option<u64> {
    offered
        .iter()
        .filter_map(|&c| Some((c, code_effective(c)?)))
        .min_by(|a, b| {
            let da = (a.1 / seconds).log2().abs();
            let db = (b.1 / seconds).log2().abs();
            da.total_cmp(&db).then(a.1.total_cmp(&b.1))
        })
        .map(|(c, _)| c)
}

/// The longest offered code not longer than `seconds`.
pub fn longest_within(offered: &[u64], seconds: f64) -> Option<u64> {
    offered
        .iter()
        .filter_map(|&c| Some((c, code_effective(c)?)))
        .filter(|(_, s)| *s <= seconds * (1.0 + 1e-9))
        .max_by(|a, b| a.1.total_cmp(&b.1).then(b.0.cmp(&a.0)))
        .map(|(c, _)| c)
}

/// "1/60" or "1.3" for a code.
pub fn code_label(code: u64) -> String {
    let (n, d) = ((code >> 16) & 0xffff, code & 0xffff);
    match code_seconds(code) {
        None => "untimed".into(),
        Some(_) if n == 1 && d > 1 => format!("1/{d}"),
        Some(s) => format!("{s}"),
    }
}

// ----------------------------------------------------------------- journal

/// One single-shot exposure of the survey (member 1 of its group).
#[derive(Clone, Debug, PartialEq)]
pub struct Shot {
    pub plane: u64,
    pub focus: u64,
    pub shutter: u64,
    pub iso: Option<u64>,
    pub tier: String,
    pub path: PathBuf,
    /// Recording order; the later of two shots at one focus and shutter is
    /// used.
    pub order: usize,
}

#[derive(Clone, Debug, Default)]
struct Tagged {
    shutter: Option<u64>,
    iso: Option<u64>,
    tier: Option<String>,
}

fn read_jsonl(path: &Path) -> Result<Vec<Value>> {
    let text = std::fs::read_to_string(path).with_context(|| format!("read {}", path.display()))?;
    Ok(text
        .lines()
        .filter_map(|l| serde_json::from_str::<Value>(l).ok())
        .collect())
}

fn status_value(d: &Value, name: &str) -> Option<u64> {
    d["camera_status"]["properties"][name]["value"].as_u64()
}

/// Commanded exposure and tier per file name, from the journal: the
/// `capture_buffered` event's `exposure` and `tier` (plan X3), else its
/// `capture_intent`'s, else the camera status the intent recorded.
fn tagged_files(dir: &Path) -> Result<HashMap<String, Tagged>> {
    let mut intents: HashMap<u64, Tagged> = HashMap::new();
    let mut out = HashMap::new();
    for e in read_jsonl(&dir.join("events.jsonl"))? {
        let d = &e["data"];
        match e["event"].as_str() {
            Some("capture_intent") => {
                if let Some(o) = d["ordinal"].as_u64() {
                    intents.insert(
                        o,
                        Tagged {
                            shutter: d["exposure"]["shutter"]
                                .as_u64()
                                .or_else(|| status_value(d, "ShutterSpeed")),
                            iso: d["exposure"]["iso"]
                                .as_u64()
                                .or_else(|| status_value(d, "IsoSensitivity")),
                            tier: d["tier"].as_str().map(String::from),
                        },
                    );
                }
            }
            Some("capture_buffered" | "capture_complete") => {
                let intent = d["ordinal"]
                    .as_u64()
                    .and_then(|o| intents.get(&o))
                    .cloned()
                    .unwrap_or_default();
                let shutter = d["exposure"]["shutter"].as_u64().or(intent.shutter);
                let iso = d["exposure"]["iso"].as_u64().or(intent.iso);
                let tier = d["tier"].as_str().map(String::from).or(intent.tier);
                for f in d["response"]["files"].as_array().into_iter().flatten() {
                    if let Some(name) = f["name"].as_str() {
                        out.insert(
                            name.to_string(),
                            Tagged {
                                shutter,
                                iso,
                                tier: f["tier"].as_str().map(String::from).or(tier.clone()),
                            },
                        );
                    }
                }
            }
            _ => {}
        }
    }
    Ok(out)
}

/// The survey's shots, from the capture's own records: member 1 of each
/// recorded group with a durable file, a focus target and a timed shutter.
/// The second value counts groups left out.
pub fn shots(dir: &Path) -> Result<(Vec<Shot>, usize)> {
    let tags = tagged_files(dir)?;
    let mut out = Vec::new();
    let mut skipped = 0;
    for (order, g) in all_groups(dir)?.into_iter().enumerate() {
        let first = g.files.iter().find(|f| f.durable && f.member_index == 1);
        let (Some(target), Some(first)) = (g.target, first) else {
            skipped += 1;
            continue;
        };
        let tag = tags.get(&first.name).cloned().unwrap_or_default();
        let Some(shutter) = tag.shutter.filter(|&c| code_seconds(c).is_some()) else {
            skipped += 1;
            continue;
        };
        out.push(Shot {
            plane: g.plane,
            focus: target,
            shutter,
            iso: tag.iso,
            tier: tag.tier.unwrap_or_else(|| "base".into()),
            path: first.path.clone(),
            order,
        });
    }
    Ok((out, skipped))
}

/// How the shots divide: pairs (a position at two shutters), the long
/// frames, and the dense cluster for the step. Everything is sorted by focus.
#[derive(Clone, Debug, PartialEq)]
pub struct Plan {
    pub long_code: u64,
    pub short_code: Option<u64>,
    /// (long, short) per position.
    pub pairs: Vec<(Shot, Shot)>,
    /// Every position's shot at the long shutter.
    pub longs: Vec<Shot>,
    pub dense: Vec<Shot>,
    /// `true` when the dense cluster is the positions taken at one shutter
    /// only, `false` when there were too few and every long position is used.
    pub dense_is_cluster: bool,
    pub notes: Vec<String>,
}

fn mode_code(codes: impl Iterator<Item = u64>) -> Option<u64> {
    let mut n: BTreeMap<u64, usize> = BTreeMap::new();
    for c in codes {
        *n.entry(c).or_default() += 1;
    }
    n.into_iter()
        .max_by(|a, b| {
            a.1.cmp(&b.1).then(
                code_seconds(a.0)
                    .unwrap_or(0.0)
                    .total_cmp(&code_seconds(b.0).unwrap_or(0.0)),
            )
        })
        .map(|(c, _)| c)
}

pub fn classify(shots: &[Shot]) -> Result<Plan> {
    // The latest shot per (focus, shutter).
    let mut last: BTreeMap<(u64, u64), &Shot> = BTreeMap::new();
    for s in shots {
        match last.get(&(s.focus, s.shutter)) {
            Some(k) if k.order > s.order => {}
            _ => {
                last.insert((s.focus, s.shutter), s);
            }
        }
    }
    ensure!(!last.is_empty(), "no timed single shots in this survey");
    let mut by_focus: BTreeMap<u64, Vec<&Shot>> = BTreeMap::new();
    for ((f, _), s) in &last {
        by_focus.entry(*f).or_default().push(s);
    }
    let secs = |s: &Shot| code_seconds(s.shutter).unwrap_or(0.0);
    let mut candidates: Vec<(Shot, Shot)> = Vec::new();
    let mut singles: Vec<Shot> = Vec::new();
    for v in by_focus.values_mut() {
        v.sort_by(|a, b| secs(b).total_cmp(&secs(a)).then(a.shutter.cmp(&b.shutter)));
        if v.len() >= 2 {
            // The short shot's partner is the long shot at its focus taken
            // nearest it in time (the light drifts between groups), not
            // whichever long shot came last.
            let short = v[v.len() - 1];
            let long = shots
                .iter()
                .filter(|s| s.focus == short.focus && s.shutter == v[0].shutter)
                .min_by_key(|s| (s.order.abs_diff(short.order), usize::MAX - s.order))
                .unwrap_or(v[0]);
            candidates.push((long.clone(), short.clone()));
        } else {
            singles.push(v[0].clone());
        }
    }
    let long_code = mode_code(candidates.iter().map(|p| p.0.shutter))
        .or_else(|| mode_code(last.values().map(|s| s.shutter)))
        .context("no timed shots")?;
    let mut notes = Vec::new();
    let (pairs, odd): (Vec<_>, Vec<_>) = candidates
        .into_iter()
        .partition(|p| p.0.shutter == long_code);
    if !odd.is_empty() {
        notes.push(format!(
            "{} position(s) whose longer shutter is not {} were left out of the census",
            odd.len(),
            code_label(long_code)
        ));
    }
    let short_code = mode_code(pairs.iter().map(|p| p.1.shutter));
    // `last` is keyed by (focus, shutter): one shot per focus, in focus order.
    let longs: Vec<Shot> = last
        .values()
        .filter(|s| s.shutter == long_code)
        .map(|s| (*s).clone())
        .collect();
    let singles: Vec<Shot> = singles
        .into_iter()
        .filter(|s| s.shutter == long_code)
        .collect();
    let cluster = dense_run(&singles);
    let dense_is_cluster = cluster.len() >= MIN_DENSE;
    let dense = if dense_is_cluster {
        cluster.to_vec()
    } else {
        longs.clone()
    };
    Ok(Plan {
        long_code,
        short_code,
        pairs,
        longs,
        dense,
        dense_is_cluster,
        notes,
    })
}

/// The longest run of shots (in focus order) no further apart than twice
/// the closest two: the dense cluster, without long-only positions elsewhere
/// in the range.
fn dense_run(singles: &[Shot]) -> &[Shot] {
    let Some(min_gap) = singles.windows(2).map(|w| w[1].focus - w[0].focus).min() else {
        return singles;
    };
    let (mut best, mut start) = ((0, singles.len().min(1)), 0);
    for i in 1..=singles.len() {
        let breaks = i == singles.len() || singles[i].focus - singles[i - 1].focus > 2 * min_gap;
        if breaks {
            if i - start > best.1 - best.0 {
                best = (start, i);
            }
            start = i;
        }
    }
    &singles[best.0..best.1]
}

/// Up to `count` shots spread evenly over their focus range (first and last
/// included); all of them when there are no more.
pub fn spread(shots: &[Shot], count: usize) -> Vec<Shot> {
    let n = shots.len();
    if count == 0 || n <= count || count < 2 {
        return shots.to_vec();
    }
    let (lo, hi) = (shots[0].focus as f64, shots[n - 1].focus as f64);
    let mut used = vec![false; n];
    for k in 0..count {
        let target = lo + (hi - lo) * k as f64 / (count - 1) as f64;
        if let Some(i) = (0..n).filter(|&i| !used[i]).min_by(|&a, &b| {
            let da = (shots[a].focus as f64 - target).abs();
            let db = (shots[b].focus as f64 - target).abs();
            da.total_cmp(&db).then(a.cmp(&b))
        }) {
            used[i] = true;
        }
    }
    shots
        .iter()
        .zip(used)
        .filter(|(_, u)| *u)
        .map(|(s, _)| s.clone())
        .collect()
}

// ----------------------------------------------------------------- subject

/// An outline and the geometry to map it to any focus.
#[derive(Clone, Debug, PartialEq)]
pub struct Outline {
    pub rings: Vec<Ring>,
    pub reference_focus: Option<f64>,
    pub ppm_per_unit: Option<f64>,
}

impl Outline {
    /// Magnification at `focus` against the outline's reference plane (the
    /// evidence's convention: frame k shows the reference grid scaled by
    /// `exp(rate * (focus_k - focus_ref))` about the centre).
    pub fn scale_at(&self, focus: f64) -> f64 {
        match (self.ppm_per_unit, self.reference_focus) {
            (Some(ppm), Some(r)) => (ppm * 1e-6 * (focus - r)).exp(),
            _ => 1.0,
        }
    }

    /// The subject's sites at `focus` on an active area of `size` px.
    pub fn mask_at(&self, focus: f64, size: [usize; 2]) -> SiteMask {
        let m = self.scale_at(focus);
        let rings: Vec<Ring> = self
            .rings
            .iter()
            .map(|r| {
                r.iter()
                    .map(|p| {
                        [
                            (0.5 + (f64::from(p[0]) - 0.5) * m) as f32,
                            (0.5 + (f64::from(p[1]) - 0.5) * m) as f32,
                        ]
                    })
                    .collect()
            })
            .collect();
        let (cols, rows) = (size[0] / CELL, size[1] / CELL);
        let norm = [CELL as f64 / size[0] as f64, CELL as f64 / size[1] as f64];
        SiteMask {
            cols,
            rows,
            cells: rasterize(&rings, cols, rows, norm),
        }
    }
}

/// Which sites of an active area count, by 8 px cell.
#[derive(Clone, Debug)]
pub struct SiteMask {
    pub cols: usize,
    pub rows: usize,
    pub cells: Vec<bool>,
}

impl SiteMask {
    /// Every site of the active area.
    pub fn all(size: [usize; 2]) -> Self {
        let (cols, rows) = (size[0].div_ceil(CELL), size[1].div_ceil(CELL));
        Self {
            cols,
            rows,
            cells: vec![true; cols * rows],
        }
    }

    fn row(&self, y: usize) -> Option<&[bool]> {
        let r = y / CELL;
        (r < self.rows).then(|| &self.cells[r * self.cols..(r + 1) * self.cols])
    }

    pub fn count(&self) -> usize {
        self.cells.iter().filter(|&&c| c).count()
    }
}

#[inline]
fn has(row: &[bool], x: usize) -> bool {
    row.get(x / CELL).copied().unwrap_or(false)
}

/// The subject object of a `--subject` file: a `strehl subject` JSON, a
/// host `Subject` (`rate_ppm`), or a manifest holding either as
/// `plan.subject` or `subject`.
pub fn outline_from(v: &Value) -> Option<(Outline, Value)> {
    let s = if v.get("rings").is_some() {
        v
    } else if v["plan"]["subject"].is_object() {
        &v["plan"]["subject"]
    } else if v["subject"].is_object() {
        &v["subject"]
    } else {
        return None;
    };
    let rings: Vec<Ring> = serde_json::from_value(s["rings"].clone()).ok()?;
    if rings.iter().all(|r| r.len() < 3) {
        return None;
    }
    Some((
        Outline {
            rings,
            reference_focus: s["reference_focus"].as_f64(),
            ppm_per_unit: s["ppm_per_unit"].as_f64().or(s["rate_ppm"].as_f64()),
        },
        s.clone(),
    ))
}

/// [`select`]'s depth rule over a given mask on the evidence grid.
pub fn depth_over(e: &Evidence, q: &Quiet, p: &Params, mask: &[bool]) -> Option<Depth> {
    let cut = if q.mode.exp() > ABSOLUTE_MODE {
        p.sensitivity
    } else {
        (q.mode + 2.0 * p.sensitivity * q.spread).exp()
    };
    let mut sharpest = vec![0usize; e.planes.len()];
    for ((&inside, &f), &d) in mask.iter().zip(&e.focus).zip(&e.depth) {
        if inside && f >= cut {
            sharpest[d as usize] += 1;
        }
    }
    let total: usize = sharpest.iter().sum();
    if total == 0 {
        return None;
    }
    let first = sharpest.iter().position(|&c| c > 0)?;
    let last = sharpest.iter().rposition(|&c| c > 0)?;
    let tail = total / 200;
    let mut acc = 0;
    let core_first = sharpest
        .iter()
        .position(|&c| {
            acc += c;
            acc > tail
        })
        .unwrap_or(first);
    acc = 0;
    let core_last = sharpest
        .iter()
        .rposition(|&c| {
            acc += c;
            acc > tail
        })
        .unwrap_or(last);
    Some(Depth {
        first,
        last,
        core_first,
        core_last,
        cells: sharpest,
    })
}

// --------------------------------------------------------------- statistics

/// Per colour (R, G pooled, B) counts of raw values.
pub type Hist = [Vec<u64>; 3];

fn new_hist() -> Hist {
    std::array::from_fn(|_| vec![0u64; 1 << 16])
}

fn add_hist(a: &mut Hist, b: &Hist) {
    for (x, y) in a.iter_mut().zip(b) {
        for (p, q) in x.iter_mut().zip(y) {
            *p += q;
        }
    }
}

#[inline]
fn colour(x: usize, y: usize) -> usize {
    cfa_colour(x as isize, y as isize)
}

fn plane_of(c: usize) -> CfaPlane {
    match c {
        0 => CfaPlane::R,
        2 => CfaPlane::B,
        _ => CfaPlane::G1,
    }
}

fn active_row<'a>(v: &CfaView<'a>, y: usize) -> &'a [u16] {
    let start = (v.y0 + y) * v.stride + v.x0;
    &v.data[start..start + v.width]
}

/// A long frame over the subject: its values, and its pinned sites.
#[derive(Clone, Debug)]
pub struct LongPass {
    pub hist: Hist,
    pub pinned: u64,
    pub sites: u64,
}

pub fn long_pass(v: &CfaView<'_>, mask: &SiteMask) -> LongPass {
    let pin = v.white - PIN_MARGIN_DN;
    let empty = || LongPass {
        hist: new_hist(),
        pinned: 0,
        sites: 0,
    };
    (0..v.height)
        .into_par_iter()
        .with_min_len(64)
        .fold(empty, |mut acc, y| {
            if let Some(m) = mask.row(y) {
                for (x, &s) in active_row(v, y).iter().enumerate() {
                    if has(m, x) {
                        acc.hist[colour(x, y)][usize::from(s)] += 1;
                        acc.sites += 1;
                        acc.pinned += u64::from(f32::from(s) >= pin);
                    }
                }
            }
            acc
        })
        .reduce(empty, |mut a, b| {
            add_hist(&mut a.hist, &b.hist);
            a.pinned += b.pinned;
            a.sites += b.sites;
            a
        })
}

/// The exposure ratio short / long of one pair, measured on 8 px cells
/// well exposed in both (never from the shutter codes).
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct RatioMeasure {
    /// Median over the selected cells of all colours.
    pub ratio: Option<f64>,
    pub per_colour: [Option<f64>; 3],
    pub cells: usize,
}

fn median(mut v: Vec<f64>) -> Option<f64> {
    if v.is_empty() {
        return None;
    }
    v.sort_by(f64::total_cmp);
    let n = v.len();
    Some(if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    })
}

/// `short_var(colour, signal_dn)`: the injected noise model of the short
/// frame.
pub fn measure_ratio(
    long: &CfaView<'_>,
    short: &CfaView<'_>,
    short_var: &(dyn Fn(usize, f32) -> f32 + Sync),
) -> RatioMeasure {
    let (cols, rows) = (long.width / CELL, long.height / CELL);
    let range = (long.white - long.black).max(1.0);
    let pin = long.white - PIN_MARGIN_DN;
    let cells: Vec<(usize, f64)> = (0..rows)
        .into_par_iter()
        .flat_map_iter(|cy| {
            // Per cell and colour: long sum, short sum, count, long max.
            let mut acc = vec![[0f64; 4]; cols * 3];
            for y in cy * CELL..(cy + 1) * CELL {
                let (lr, sr) = (active_row(long, y), active_row(short, y));
                for (x, (&l, &s)) in lr.iter().zip(sr).take(cols * CELL).enumerate() {
                    let a = &mut acc[(x / CELL) * 3 + colour(x, y)];
                    a[0] += f64::from(f32::from(l) - long.black);
                    a[1] += f64::from(f32::from(s) - short.black);
                    a[2] += 1.0;
                    a[3] = a[3].max(f64::from(l));
                }
            }
            acc.into_iter()
                .enumerate()
                .filter_map(|(k, a)| {
                    let c = k % 3;
                    let n = a[2];
                    if n == 0.0 || a[3] >= f64::from(pin) {
                        return None;
                    }
                    let (lm, sm) = (a[0] / n, a[1] / n);
                    let share = (lm / f64::from(range)) as f32;
                    let se = (f64::from(short_var(c, sm.max(0.0) as f32)) / n).sqrt();
                    ((RATIO_LOW..=RATIO_HIGH).contains(&share) && sm >= f64::from(RATIO_SNR) * se)
                        .then(|| (c, sm / lm))
                })
                .collect::<Vec<_>>()
        })
        .collect();
    let per_colour = std::array::from_fn(|c| {
        let v: Vec<f64> = cells.iter().filter(|p| p.0 == c).map(|p| p.1).collect();
        (v.len() >= MIN_RATIO_CELLS / 3)
            .then(|| median(v))
            .flatten()
    });
    let n = cells.len();
    RatioMeasure {
        ratio: (n >= MIN_RATIO_CELLS)
            .then(|| median(cells.into_iter().map(|p| p.1).collect()))
            .flatten(),
        per_colour,
        cells: n,
    }
}

/// Max over a `(2r+1)^2` window, edges clamped.
fn dilate<T: Copy + Ord + Default + Send + Sync>(f: &[T], w: usize, h: usize, r: usize) -> Vec<T> {
    let mut tmp = vec![T::default(); f.len()];
    tmp.par_chunks_mut(w).enumerate().for_each(|(y, out)| {
        let row = &f[y * w..(y + 1) * w];
        for (x, o) in out.iter_mut().enumerate() {
            *o = row[x.saturating_sub(r)..(x + r + 1).min(w)]
                .iter()
                .copied()
                .max()
                .unwrap_or_default();
        }
    });
    let mut out = vec![T::default(); f.len()];
    out.par_chunks_mut(w).enumerate().for_each(|(y, o)| {
        for yy in y.saturating_sub(r)..(y + r + 1).min(h) {
            for (p, q) in o.iter_mut().zip(&tmp[yy * w..(yy + 1) * w]) {
                *p = (*p).max(*q);
            }
        }
    });
    out
}

/// A pair over the subject: the long frame's body (highlights set aside)
/// and the short frame's values.
#[derive(Clone, Debug)]
pub struct PairPass {
    pub body: Hist,
    /// Every subject site of the short frame.
    pub short: Hist,
    /// The short frame's sites the long frame confirms: its brightest
    /// sample within two pixels reaches half of what the short site
    /// predicts (or is pinned). A site bright in the short frame alone is a
    /// fixed-pattern or hot pixel, which does not scale with exposure; a
    /// glint shows in both.
    pub confirmed: Hist,
    pub set_aside: u64,
    /// Short sites above the set-aside cut that the long frame does not
    /// confirm.
    pub unconfirmed: u64,
    pub pinned_short: u64,
}

/// The share of the predicted long level the long frame must reach near a
/// site for the short site to count as radiance.
const CONFIRM: f64 = 0.5;

/// The short frame's cut (DN above black) for setting a site aside from
/// the body: `SET_ASIDE_OVER_P99` times the body's 99th percentile
/// (`p99_long_dn`, long DN above black) scaled by the pair's ratio, and
/// clear of the short frame's noise there by `HIGHLIGHT_SIGMAS`
/// (`short_sigma(colour, dn)`: the injected noise model). Without the noise
/// term a body near black would be set aside whole.
pub fn set_aside_cut(
    p99_long_dn: [f64; 3],
    ratio: f64,
    short_sigma: &dyn Fn(usize, f32) -> f32,
) -> [f64; 3] {
    std::array::from_fn(|c| {
        let dn = SET_ASIDE_OVER_P99 * p99_long_dn[c] * ratio;
        dn + HIGHLIGHT_SIGMAS * f64::from(short_sigma(c, dn as f32))
    })
}

/// `set_aside[c]`: the short frame's DN above black beyond which a
/// confirmed short site (and the long sites within two pixels of it) is a
/// highlight; see [`set_aside_cut`]. `ratio` is short / long.
pub fn pair_pass(
    long: &CfaView<'_>,
    short: &CfaView<'_>,
    mask: &SiteMask,
    ratio: f64,
    set_aside: [f64; 3],
) -> PairPass {
    let (w, h) = (long.width, long.height);
    let long_pin = f64::from(long.white - PIN_MARGIN_DN - long.black);
    let mut active = vec![0u16; w * h];
    active
        .par_chunks_mut(w)
        .enumerate()
        .for_each(|(y, row)| row.copy_from_slice(active_row(long, y)));
    let long_max = dilate(&active, w, h, SET_ASIDE_RADIUS);
    drop(active);
    let confirmed = |s: u16, lmax: u16| -> bool {
        let s_dn = f64::from(f32::from(s) - short.black);
        let expected = (s_dn / ratio).min(long_pin);
        expected <= 0.0 || f64::from(f32::from(lmax) - long.black) >= CONFIRM * expected
    };
    let mut flags = vec![0u8; w * h];
    flags.par_chunks_mut(w).enumerate().for_each(|(y, out)| {
        let lm = &long_max[y * w..(y + 1) * w];
        for (x, ((o, &s), &l)) in out.iter_mut().zip(active_row(short, y)).zip(lm).enumerate() {
            let above = f64::from(f32::from(s) - short.black) > set_aside[colour(x, y)];
            *o = u8::from(above && confirmed(s, l)) + 2 * u8::from(above && !confirmed(s, l));
        }
    });
    let near = dilate(
        &flags.iter().map(|f| f & 1).collect::<Vec<u8>>(),
        w,
        h,
        SET_ASIDE_RADIUS,
    );
    let pin = short.white - PIN_MARGIN_DN;
    let empty = || PairPass {
        body: new_hist(),
        short: new_hist(),
        confirmed: new_hist(),
        set_aside: 0,
        unconfirmed: 0,
        pinned_short: 0,
    };
    (0..h)
        .into_par_iter()
        .with_min_len(64)
        .fold(empty, |mut acc, y| {
            if let Some(m) = mask.row(y) {
                let (lr, sr) = (active_row(long, y), active_row(short, y));
                let row = y * w..(y + 1) * w;
                let (nr, fr, lm) = (&near[row.clone()], &flags[row.clone()], &long_max[row]);
                for (x, ((((&l, &s), &n), &f), &lx)) in
                    lr.iter().zip(sr).zip(nr).zip(fr).zip(lm).enumerate()
                {
                    if !has(m, x) {
                        continue;
                    }
                    let c = colour(x, y);
                    if n != 0 {
                        acc.set_aside += 1;
                    } else {
                        acc.body[c][usize::from(l)] += 1;
                    }
                    acc.short[c][usize::from(s)] += 1;
                    if confirmed(s, lx) {
                        acc.confirmed[c][usize::from(s)] += 1;
                    }
                    acc.unconfirmed += u64::from(f & 2 != 0);
                    acc.pinned_short += u64::from(f32::from(s) >= pin);
                }
            }
            acc
        })
        .reduce(empty, |mut a, b| {
            add_hist(&mut a.body, &b.body);
            add_hist(&mut a.short, &b.short);
            add_hist(&mut a.confirmed, &b.confirmed);
            a.set_aside += b.set_aside;
            a.unconfirmed += b.unconfirmed;
            a.pinned_short += b.pinned_short;
            a
        })
}

/// Nearest-rank percentile (`q` in 0..1) of value-count pairs sorted by
/// value.
fn weighted_percentile(sorted: &[(f64, u64)], q: f64) -> Option<f64> {
    let total: u64 = sorted.iter().map(|p| p.1).sum();
    if total == 0 {
        return None;
    }
    let rank = ((q * total as f64).ceil() as u64).clamp(1, total);
    let mut acc = 0;
    for &(v, c) in sorted {
        acc += c;
        if acc >= rank {
            return Some(v);
        }
    }
    sorted.last().map(|p| p.0)
}

/// A histogram of raw values as shares of black..white times `scale`.
fn as_values(h: &[u64], black: f32, range: f32, scale: f64) -> Vec<(f64, u64)> {
    h.iter()
        .enumerate()
        .filter(|(_, c)| **c > 0)
        .map(|(dn, &c)| (f64::from(dn as f32 - black) / f64::from(range) * scale, c))
        .collect()
}

// --------------------------------------------------------------- the census

/// What one pair contributes to the census.
#[derive(Clone, Debug)]
pub struct PairResult {
    pub focus: u64,
    pub long_code: u64,
    pub short_code: u64,
    pub ratio: RatioMeasure,
    /// The ratio used: measured, or the commanded one when it could not be.
    pub used: f64,
    pub pass: PairPass,
    /// The long frame over the subject, all sites.
    pub long_hist: Hist,
    pub pinned_long: u64,
    pub noise: NoiseModel,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize)]
pub struct Level {
    pub p50: f64,
    pub p99: f64,
    pub p999: f64,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize)]
pub struct Tail {
    pub p999: f64,
    pub p9999: f64,
    pub max: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct PerColour<T> {
    pub r: T,
    pub g: T,
    pub b: T,
}

impl<T: Copy> PerColour<T> {
    fn from_fn(f: impl Fn(usize) -> T) -> Self {
        Self {
            r: f(0),
            g: f(1),
            b: f(2),
        }
    }
    fn get(&self, c: usize) -> T {
        [self.r, self.g, self.b][c]
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct BodyJson {
    /// Shares of black..white in the long frames, over subject sites with
    /// highlights set aside.
    #[serde(flatten)]
    pub levels: PerColour<Level>,
    /// The brightest colour's 99.9th percentile.
    pub top: f64,
    pub sites: u64,
    pub set_aside_sites: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PinnedAt {
    pub focus: u64,
    /// Subject sites pinned in the long frame.
    pub pinned: u64,
    /// What the short frame predicts at the long shutter (a check of the
    /// census against the long frame).
    pub predicted: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct CensusJson {
    /// Subject radiance in the short frames, in units of the long shutter's
    /// full scale: short value x measured ratio / (white - black).
    #[serde(flatten)]
    pub tails: PerColour<Tail>,
    /// The largest of the colours' maxima.
    pub top: f64,
    pub margin_stops: f64,
    /// Subject sites more than a stop above their colour's body top (and
    /// clear of noise), summed over the pairs; `highlights` is whether any.
    pub highlight_sites: u64,
    pub highlights: bool,
    /// Sites pinned even in the short frames: the census does not see
    /// above them.
    pub pinned_short_sites: u64,
    /// Short sites above the body that the long frame does not confirm
    /// (fixed-pattern and hot pixels): left out of `max`, `top` and the
    /// highlights.
    pub unconfirmed_sites: u64,
    pub pinned_long_per_position: Vec<PinnedAt>,
    pub per_position: Vec<CensusAt>,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct CensusAt {
    pub focus: u64,
    /// The brightest subject site at this position, per colour (R, G, B),
    /// in units of the long shutter's full scale.
    pub max: [f64; 3],
    pub highlight_sites: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PairRatio {
    pub focus: u64,
    pub long_code: u64,
    pub short_code: u64,
    pub commanded: f64,
    pub commanded_marked: f64,
    pub measured: Option<f64>,
    pub per_colour: [Option<f64>; 3],
    pub cells: usize,
    /// Measured against commanded, percent.
    pub off_commanded_pct: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct RatioJson {
    /// Short / long on the camera's third-stop series (what it exposes).
    pub commanded: f64,
    /// Short / long from the codes as marked.
    pub commanded_marked: f64,
    /// Median of the pairs' measured ratios.
    pub measured: Option<f64>,
    pub per_position: Vec<PairRatio>,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct HighlightPass {
    pub base_s: f64,
    pub base_code: Option<u64>,
    pub base_code_s: Option<f64>,
    pub short_s: f64,
    pub short_code: Option<u64>,
    pub short_code_s: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct OneShutter {
    pub s: f64,
    pub code: Option<u64>,
    pub code_s: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Accept {
    pub s: f64,
    pub code: Option<u64>,
    pub code_s: Option<f64>,
    /// Subject sites expected to pin a plane at `code` (at `s` without a
    /// code list), averaged over the positions; a lower bound.
    pub pinned_sites_per_plane: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct AdviceJson {
    pub highlight_pass: HighlightPass,
    pub protect: OneShutter,
    pub accept: Accept,
    /// `"highlight_pass"` when the census top exceeds the body's top by more
    /// than a stop, else `"accept"`.
    pub suggested: String,
    /// The long shutter the survey measured at (effective seconds).
    pub from_s: f64,
}

/// Everything after the passes: pure arithmetic on histograms.
#[derive(Clone, Debug, PartialEq)]
pub struct Census {
    pub body: BodyJson,
    pub census: CensusJson,
    pub ratio: RatioJson,
    pub advice: AdviceJson,
}

/// Subject sites at or above white in a plane exposed `t` seconds, from one
/// pair's short frame (the long shutter is `t_long`).
fn pinned_at(p: &PairResult, levels: (f32, f32), t: f64, t_long: f64) -> u64 {
    let (black, white) = levels;
    let range = f64::from(white - black);
    let pin_share = f64::from(white - PIN_MARGIN_DN - black) / range;
    let cut = f64::from(black) + pin_share * range * (t_long / t) * p.used;
    p.pass
        .confirmed
        .iter()
        .flat_map(|h| h.iter().enumerate())
        .filter(|(dn, c)| **c > 0 && *dn as f64 >= cut)
        .map(|(_, c)| *c)
        .sum()
}

/// Subject sites expected to pin a plane exposed `t` seconds. Longer than
/// the long shutter: from the long frame (16 times the short frame's
/// signal against its noise, so the short frame's noise is not
/// extrapolated); shorter: from the short frame.
fn expected_pinned(p: &PairResult, levels: (f32, f32), t: f64, t_long: f64) -> u64 {
    if t < t_long {
        return pinned_at(p, levels, t, t_long);
    }
    let (black, white) = levels;
    let pin = f64::from(white - PIN_MARGIN_DN);
    let cut = f64::from(black) + (pin - f64::from(black)) * t_long / t;
    p.long_hist
        .iter()
        .flat_map(|h| h.iter().enumerate())
        .filter(|(dn, c)| **c > 0 && *dn as f64 >= cut)
        .map(|(_, c)| *c)
        .sum()
}

/// The census, body, ratio and advice from the pairs' passes. `levels` is
/// (black, white), the same for every frame; `offered` the camera's codes.
pub fn census(
    pairs: &[PairResult],
    levels: (f32, f32),
    long_code: u64,
    offered: &[u64],
) -> Result<Census> {
    ensure!(!pairs.is_empty(), "no position was taken at two shutters");
    let (black, white) = levels;
    let range = (white - black).max(1.0);
    let t_long = code_effective(long_code).context("untimed long shutter")?;
    // Body: pooled long histograms with highlights set aside.
    let mut body_hist = new_hist();
    for p in pairs {
        add_hist(&mut body_hist, &p.pass.body);
    }
    let levels_c = PerColour::from_fn(|c| {
        let v = as_values(&body_hist[c], black, range, 1.0);
        Level {
            p50: weighted_percentile(&v, 0.5).unwrap_or(0.0),
            p99: weighted_percentile(&v, 0.99).unwrap_or(0.0),
            p999: weighted_percentile(&v, 0.999).unwrap_or(0.0),
        }
    });
    let body_top = (0..3).map(|c| levels_c.get(c).p999).fold(0.0, f64::max);
    let body = BodyJson {
        levels: levels_c,
        top: body_top,
        sites: body_hist.iter().flatten().sum(),
        set_aside_sites: pairs.iter().map(|p| p.pass.set_aside).sum(),
    };
    // Census: pooled short histograms, each scaled by its pair's ratio; the
    // maximum and the highlights only over sites the long frame confirms.
    let pooled = |c: usize, confirmed: bool| -> Vec<(f64, u64)> {
        let mut v: Vec<(f64, u64)> = pairs
            .iter()
            .flat_map(|p| {
                let h = if confirmed {
                    &p.pass.confirmed[c]
                } else {
                    &p.pass.short[c]
                };
                as_values(h, black, range, 1.0 / p.used)
            })
            .collect();
        v.sort_by(|a, b| a.0.total_cmp(&b.0));
        v
    };
    let tails = PerColour::from_fn(|c| {
        let v = pooled(c, false);
        Tail {
            p999: weighted_percentile(&v, 0.999).unwrap_or(0.0),
            p9999: weighted_percentile(&v, 0.9999).unwrap_or(0.0),
            max: pooled(c, true).last().map_or(0.0, |p| p.0),
        }
    });
    let top = (0..3).map(|c| tails.get(c).max).fold(0.0, f64::max);
    let per_position: Vec<CensusAt> = pairs
        .iter()
        .map(|p| CensusAt {
            focus: p.focus,
            max: std::array::from_fn(|c| {
                p.pass.confirmed[c]
                    .iter()
                    .rposition(|&n| n > 0)
                    .map_or(0.0, |dn| {
                        f64::from(dn as f32 - black) / f64::from(range) / p.used
                    })
            }),
            highlight_sites: (0..3)
                .map(|c| {
                    let thr = HIGHLIGHT_OVER_BODY * levels_c.get(c).p999;
                    let dn = thr * f64::from(range) * p.used;
                    let sigma = f64::from(p.noise.sigma(plane_of(c), dn as f32));
                    let cut = f64::from(black) + dn + HIGHLIGHT_SIGMAS * sigma;
                    p.pass.confirmed[c]
                        .iter()
                        .enumerate()
                        .filter(|(v, n)| **n > 0 && *v as f64 > cut)
                        .map(|(_, n)| *n)
                        .sum::<u64>()
                })
                .sum(),
        })
        .collect();
    let highlight_sites: u64 = per_position.iter().map(|p| p.highlight_sites).sum();
    let census = CensusJson {
        tails,
        top,
        margin_stops: MARGIN_STOPS,
        highlight_sites,
        highlights: highlight_sites > 0,
        pinned_short_sites: pairs.iter().map(|p| p.pass.pinned_short).sum(),
        unconfirmed_sites: pairs.iter().map(|p| p.pass.unconfirmed).sum(),
        pinned_long_per_position: pairs
            .iter()
            .map(|p| PinnedAt {
                focus: p.focus,
                pinned: p.pinned_long,
                predicted: pinned_at(p, levels, t_long, t_long),
            })
            .collect(),
        per_position,
    };
    // Ratios.
    let per_position: Vec<PairRatio> = pairs
        .iter()
        .map(|p| {
            let commanded = code_effective(p.short_code).unwrap_or(f64::NAN) / t_long;
            let marked = code_seconds(p.short_code).unwrap_or(f64::NAN)
                / code_seconds(p.long_code).unwrap_or(f64::NAN);
            PairRatio {
                focus: p.focus,
                long_code: p.long_code,
                short_code: p.short_code,
                commanded,
                commanded_marked: marked,
                measured: p.ratio.ratio,
                per_colour: p.ratio.per_colour,
                cells: p.ratio.cells,
                off_commanded_pct: p.ratio.ratio.map(|m| 100.0 * (m / commanded - 1.0)),
            }
        })
        .collect();
    let short_mode = mode_code(pairs.iter().map(|p| p.short_code)).unwrap_or(long_code);
    let ratio = RatioJson {
        commanded: code_effective(short_mode).unwrap_or(f64::NAN) / t_long,
        commanded_marked: code_seconds(short_mode).unwrap_or(f64::NAN)
            / code_seconds(long_code).unwrap_or(f64::NAN),
        measured: median(
            per_position
                .iter()
                .filter(|p| p.short_code == short_mode)
                .filter_map(|p| p.measured)
                .collect(),
        ),
        per_position,
    };
    // Advice (plan X2), in effective seconds.
    let margin = 2f64.powf(MARGIN_STOPS);
    let with_s = |code: Option<u64>| (code, code.and_then(code_seconds));
    let base_s = if body_top > 0.0 {
        t_long * TARGET / body_top
    } else {
        t_long
    };
    let short_s = if top > 0.0 {
        t_long * TARGET / (top * margin)
    } else {
        t_long
    };
    let protect_s = if top > 0.0 {
        t_long / (top * margin)
    } else {
        t_long
    };
    let (base_code, base_code_s) = with_s(nearest_code(offered, base_s));
    let (short_code, short_code_s) = with_s(nearest_code(offered, short_s));
    let (protect_code, protect_code_s) = with_s(longest_within(offered, protect_s));
    let accept_t = base_code.and_then(code_effective).unwrap_or(base_s);
    let pinned_per_plane = pairs
        .iter()
        .map(|p| expected_pinned(p, levels, accept_t, t_long) as f64)
        .sum::<f64>()
        / pairs.len() as f64;
    let advice = AdviceJson {
        highlight_pass: HighlightPass {
            base_s,
            base_code,
            base_code_s,
            short_s,
            short_code,
            short_code_s,
        },
        protect: OneShutter {
            s: protect_s,
            code: protect_code,
            code_s: protect_code_s,
        },
        accept: Accept {
            s: base_s,
            code: base_code,
            code_s: base_code_s,
            pinned_sites_per_plane: pinned_per_plane,
        },
        suggested: if top > HIGHLIGHT_OVER_BODY * body_top && census.highlights {
            "highlight_pass"
        } else {
            "accept"
        }
        .into(),
        from_s: t_long,
    };
    Ok(Census {
        body,
        census,
        ratio,
        advice,
    })
}

// --------------------------------------------------------------------- step

/// `focus-step`'s fine-detail energy per 64 px tile (one green site plane,
/// 4-neighbour Laplacian, unblurred). The same measure as
/// `focus-step-cmd.rs`, repeated here over a tile mask until `focus-step
/// --subject` exists to call.
fn tile_energy(v: &CfaView<'_>) -> (usize, Vec<f64>) {
    let (w, h) = (v.width / 2, v.height / 2);
    let (gx, gy) = if cfa_colour(1, 0) == 1 {
        (1, 0)
    } else {
        (0, 1)
    };
    let at = |i: usize, j: usize| -> f32 {
        f32::from(v.data[(v.y0 + 2 * j + gy) * v.stride + v.x0 + 2 * i + gx]) - v.black
    };
    let (tw, th) = (w / TILE, h / TILE);
    let rows: Vec<Vec<f64>> = (0..th)
        .into_par_iter()
        .map(|ty| {
            let mut row = vec![0.0f64; tw];
            for j in ty * TILE..(ty + 1) * TILE {
                if j == 0 || j + 1 >= h {
                    continue;
                }
                for (tx, cell) in row.iter_mut().enumerate() {
                    let mut sum = 0.0f64;
                    for i in tx * TILE..(tx + 1) * TILE {
                        if i == 0 || i + 1 >= w {
                            continue;
                        }
                        let l = at(i - 1, j) + at(i + 1, j) + at(i, j - 1) + at(i, j + 1)
                            - 4.0 * at(i, j);
                        sum += f64::from(l * l);
                    }
                    *cell += sum;
                }
            }
            row
        })
        .collect();
    (tw, rows.into_iter().flatten().collect())
}

fn percentile_sorted(sorted: &[f64], q: f64) -> f64 {
    sorted[((sorted.len() - 1) as f64 * q).round() as usize]
}

/// `focus-step`'s half-height width of one tile's curve.
// `!(x > limit)` is deliberate, as in `focus-step`: it also rejects NaN.
#[allow(clippy::neg_cmp_op_on_partial_ord)]
fn half_width(positions: &[f64], curve: &[f64]) -> Option<f64> {
    let n = curve.len();
    let mut sorted = curve.to_vec();
    sorted.sort_by(f64::total_cmp);
    let floor = percentile_sorted(&sorted, 0.1);
    let (at, &peak) = curve.iter().enumerate().max_by(|a, b| a.1.total_cmp(b.1))?;
    if !(peak > PEAK_OVER_FLOOR * floor) || at == 0 || at + 1 == n {
        return None;
    }
    let half = floor + (peak - floor) / 2.0;
    let cross = |from: usize, to: usize| -> f64 {
        let (a, b) = (curve[from] - half, curve[to] - half);
        positions[from] + (positions[to] - positions[from]) * a / (a - b)
    };
    let mut lo = at;
    while lo > 0 && curve[lo] > half {
        lo -= 1;
    }
    let mut hi = at;
    while hi + 1 < n && curve[hi] > half {
        hi += 1;
    }
    if curve[lo] > half || curve[hi] > half {
        return None;
    }
    Some((cross(hi - 1, hi) - cross(lo, lo + 1)).abs())
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct StepJson {
    /// Median half-height width of the tiles' sharpness peaks (focus units),
    /// with the 10th and 90th percentiles.
    pub width: Option<f64>,
    pub width_p10: Option<f64>,
    pub width_p90: Option<f64>,
    /// Width / 7 (lost nothing measurable on the scarab) and width / 3.6
    /// (the edge), as `focus-step`.
    pub suggested_step: Option<u32>,
    pub edge_step: Option<u32>,
    /// Tiles whose peak was measured, of those considered.
    pub tiles: usize,
    pub tiles_considered: usize,
    pub positions: usize,
    pub spacing: f64,
    pub source: String,
}

/// The step from per-position tile energies (focus order) over the tiles
/// `use_tile` admits.
pub fn step_from(
    positions: &[f64],
    energies: &[Vec<f64>],
    use_tile: &[bool],
    source: String,
) -> StepJson {
    let mut gaps: Vec<f64> = positions.windows(2).map(|w| w[1] - w[0]).collect();
    gaps.sort_by(f64::total_cmp);
    let spacing = gaps.get(gaps.len() / 2).copied().unwrap_or(0.0);
    let tiles: Vec<usize> = (0..use_tile.len()).filter(|&t| use_tile[t]).collect();
    let mut widths: Vec<f64> = tiles
        .par_iter()
        .filter_map(|&t| {
            let curve: Vec<f64> = energies.iter().map(|e| e[t]).collect();
            half_width(positions, &curve)
        })
        .collect();
    widths.sort_by(f64::total_cmp);
    let ok = widths.len() >= MIN_TILES && positions.len() >= 5;
    let width = ok.then(|| percentile_sorted(&widths, 0.5));
    StepJson {
        width,
        width_p10: ok.then(|| percentile_sorted(&widths, 0.1)),
        width_p90: ok.then(|| percentile_sorted(&widths, 0.9)),
        suggested_step: width.map(|w| (w / SAFE).floor().max(1.0) as u32),
        edge_step: width.map(|w| (w / EDGE).floor().max(1.0) as u32),
        tiles: widths.len(),
        tiles_considered: tiles.len(),
        positions: positions.len(),
        spacing,
        source,
    }
}

// ------------------------------------------------------------------ output

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct DepthOut {
    pub first_focus: Option<f64>,
    pub last_focus: Option<f64>,
    pub core_first_focus: Option<f64>,
    pub core_last_focus: Option<f64>,
    pub first_plane: u64,
    pub last_plane: u64,
    /// First and last focus widened by half a sharp width each side (plan
    /// S4's bounds); `null` without a width.
    pub suggested_start: Option<f64>,
    pub suggested_end: Option<f64>,
}

#[derive(Clone, Debug, Serialize)]
pub struct ShuttersOut {
    pub long_code: u64,
    pub long_s: Option<f64>,
    pub long_effective_s: Option<f64>,
    pub short_code: Option<u64>,
    pub short_s: Option<f64>,
    pub short_effective_s: Option<f64>,
    pub iso: Option<u64>,
    /// The camera's offered codes were found in the manifest.
    pub offered: usize,
}

#[derive(Clone, Debug, Serialize)]
pub struct SurveyJson {
    /// As `strehl subject` writes it, or the subject given; `null` when none
    /// was found.
    pub subject: Value,
    /// `"subject"`, or `"frame"` when there is no subject and the
    /// statistics cover the whole active area.
    pub scope: String,
    pub depth: Option<DepthOut>,
    pub step: StepJson,
    pub body: Option<BodyJson>,
    pub ratio: Option<RatioJson>,
    pub census: Option<CensusJson>,
    pub advice: Option<AdviceJson>,
    pub shutters: ShuttersOut,
    /// The frames' black and white levels (raw DN) that every share is of.
    pub levels: Option<[f32; 2]>,
    pub positions: PositionsOut,
    pub summary: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct PositionsOut {
    pub pairs: usize,
    pub long: usize,
    pub dense: usize,
    pub subject_frames: usize,
    pub skipped_groups: usize,
    pub notes: Vec<String>,
}

/// The camera's offered ShutterSpeed codes, from the manifest.
pub fn offered_codes(manifest: &Value) -> Vec<u64> {
    let paths = [
        &manifest["initial_status"]["properties"]["ShutterSpeed"]["allowed"],
        &manifest["camera"]["properties"]["ShutterSpeed"]["allowed"],
        &manifest["camera"]["status"]["properties"]["ShutterSpeed"]["allowed"],
    ];
    paths
        .iter()
        .find_map(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(Value::as_u64)
                .filter(|&c| code_seconds(c).is_some())
                .collect()
        })
        .unwrap_or_default()
}

fn view(f: &strehl_raw::Frame) -> CfaView<'_> {
    CfaView {
        data: &f.data,
        stride: f.stride,
        x0: f.active.x,
        y0: f.active.y,
        width: f.active.width,
        height: f.active.height,
        black: f.levels.black,
        white: f.levels.white,
    }
}

fn decode(path: &Path) -> Result<strehl_raw::Frame> {
    strehl_raw::decode(path).with_context(|| path.display().to_string())
}

fn refuse_inside(dir: &Path, out: &Path) -> Result<()> {
    let canon = |p: &Path| std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
    let parent = out.parent().filter(|p| !p.as_os_str().is_empty());
    let target = parent.map_or_else(|| canon(Path::new(".")), canon);
    if target.starts_with(canon(dir)) {
        bail!(
            "{} is inside the capture folder; capture folders are read-only",
            out.display()
        );
    }
    Ok(())
}

fn fmt_s(s: f64) -> String {
    if s >= 0.3 {
        format!("{s:.2} s")
    } else {
        format!("1/{:.0} s", 1.0 / s)
    }
}

fn code_text(code: Option<u64>, s: f64) -> String {
    match code {
        Some(c) => format!("{} (code {c})", code_label(c)),
        None => fmt_s(s),
    }
}

pub fn run(args: &SurveyArgs) -> Result<()> {
    if let Some(out) = &args.json {
        refuse_inside(&args.dir, out)?;
    }
    let t0 = Instant::now();
    let manifest: Value = std::fs::read_to_string(args.dir.join("manifest.json"))
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or(Value::Null);
    let offered = offered_codes(&manifest);
    let (all, skipped) = shots(&args.dir)?;
    let plan = classify(&all)?;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(args.decodes.max(1))
        .build()?;
    let mut notes = plan.notes.clone();
    if manifest["capture_kind"].as_str() != Some("positions") {
        notes.push(format!(
            "capture_kind is {}, not \"positions\"",
            manifest["capture_kind"]
        ));
    }

    // 1. Subject from the long frames (or the one given), and its depth.
    let given: Option<(Outline, Value)> = match &args.subject {
        Some(p) => {
            let v: Value = serde_json::from_str(
                &std::fs::read_to_string(p).with_context(|| format!("read {}", p.display()))?,
            )
            .with_context(|| format!("parse {}", p.display()))?;
            Some(
                outline_from(&v)
                    .with_context(|| format!("{} holds no subject with rings", p.display()))?,
            )
        }
        None => outline_from(&manifest),
    };
    let frames = spread(&plan.longs, args.count);
    let chosen: Vec<(u64, (Option<f64>, PathBuf))> = frames
        .iter()
        .map(|s| (s.plane, (Some(s.focus as f64), s.path.clone())))
        .collect();
    let registration = if args.no_register {
        Registration::Off
    } else if let Some(ppm) = given.as_ref().and_then(|g| g.0.ppm_per_unit) {
        Registration::Rate(ppm)
    } else {
        Registration::Fit
    };
    let (e, provenance, _) = pool.install(|| run_evidence(&args.dir, &chosen, registration))?;
    let size = [
        e.layout.active_px[0] as usize,
        e.layout.active_px[1] as usize,
    ];
    let q = quiet(&e);
    let params = Params::default();
    let ref_focus = e.planes[e.reference].position;
    let (outline, subject_value, depth): (Option<Outline>, Value, Option<Depth>) = match given {
        Some((o, v)) => {
            // Map the given outline into the evidence's reference geometry.
            let mut at_ref = o.clone();
            if let Some(r) = ref_focus {
                let m = o.scale_at(r);
                at_ref.rings = o
                    .rings
                    .iter()
                    .map(|ring| {
                        ring.iter()
                            .map(|p| {
                                [
                                    (0.5 + (f64::from(p[0]) - 0.5) * m) as f32,
                                    (0.5 + (f64::from(p[1]) - 0.5) * m) as f32,
                                ]
                            })
                            .collect()
                    })
                    .collect();
            }
            let mask = rasterize(&at_ref.rings, e.cols, e.rows, e.layout.cell_norm);
            let d = depth_over(&e, &q, &params, &mask);
            (Some(o), v, d)
        }
        None => {
            let sel = select(&e, &q, &params);
            let json = SubjectJson::new(&e, &sel, Some(provenance));
            let o = (!sel.rings.is_empty()).then(|| Outline {
                rings: sel.rings.clone(),
                reference_focus: ref_focus,
                ppm_per_unit: e.registration.map(|r| r.ppm_per_unit),
            });
            let v = if o.is_some() {
                serde_json::to_value(&json)?
            } else {
                Value::Null
            };
            (o, v, sel.depth)
        }
    };
    let scope = if outline.is_some() {
        "subject"
    } else {
        "frame"
    };
    let mask_at = |focus: u64| -> SiteMask {
        outline
            .as_ref()
            .map_or_else(|| SiteMask::all(size), |o| o.mask_at(focus as f64, size))
    };

    // 2. Step from the dense cluster, over the subject's tiles.
    let dense_pos: Vec<f64> = plan.dense.iter().map(|s| s.focus as f64).collect();
    let energies: Vec<(usize, Vec<f64>)> = pool.install(|| {
        plan.dense
            .par_iter()
            .map(|s| -> Result<(usize, Vec<f64>)> {
                let f = decode(&s.path)?;
                Ok(tile_energy(&view(&f)))
            })
            .collect::<Result<_>>()
    })?;
    let step = if let Some((tw, first)) = energies.first() {
        let tiles = first.len();
        ensure!(
            energies.iter().all(|e| e.1.len() == tiles),
            "exposures of different sizes in one survey"
        );
        let mid = dense_pos[dense_pos.len() / 2] as u64;
        let use_tile: Vec<bool> = match &outline {
            Some(o) => {
                let m = o.mask_at(mid as f64, size);
                (0..tiles)
                    .map(|t| {
                        let (tx, ty) = (t % tw, t / tw);
                        let mut n = 0;
                        for cy in ty * 8..(ty + 1) * 8 {
                            for cx in tx * 8..(tx + 1) * 8 {
                                if cy < m.rows && cx < m.cols && m.cells[cy * m.cols + cx] {
                                    n += 1;
                                }
                            }
                        }
                        n >= 32
                    })
                    .collect()
            }
            None => vec![true; tiles],
        };
        let ev: Vec<Vec<f64>> = energies.into_iter().map(|e| e.1).collect();
        let source = format!(
            "{}: {} positions spaced {:.0} units; {} (computed here, not by focus-step --subject)",
            if plan.dense_is_cluster {
                "dense cluster"
            } else {
                "every long position (no dense cluster)"
            },
            dense_pos.len(),
            {
                let mut g: Vec<f64> = dense_pos.windows(2).map(|w| w[1] - w[0]).collect();
                g.sort_by(f64::total_cmp);
                g.get(g.len() / 2).copied().unwrap_or(0.0)
            },
            if outline.is_some() {
                "64 px tiles with at least half their area in the subject"
            } else {
                "all 64 px tiles"
            }
        );
        step_from(&dense_pos, &ev, &use_tile, source)
    } else {
        step_from(&[], &[], &[], "no long positions".into())
    };

    // 3. Body and census from the pairs.
    let mut frame_levels: Option<[f32; 2]> = None;
    let result: Option<Census> = if plan.pairs.is_empty() {
        notes.push("no position was taken at two shutters: no body, census or advice".into());
        None
    } else {
        // Pass A: the body's 99th percentile per colour, for setting
        // highlights aside.
        let longs: Vec<(LongPass, (f32, f32))> = pool.install(|| {
            plan.pairs
                .par_iter()
                .map(|(l, _)| -> Result<(LongPass, (f32, f32))> {
                    let f = decode(&l.path)?;
                    let v = view(&f);
                    Ok((long_pass(&v, &mask_at(l.focus)), (v.black, v.white)))
                })
                .collect::<Result<_>>()
        })?;
        let lv = longs[0].1;
        frame_levels = Some([lv.0, lv.1]);
        ensure!(
            longs.iter().all(|l| l.1 == lv),
            "frames with different black or white levels in one survey"
        );
        let range = (lv.1 - lv.0).max(1.0);
        let mut pooled = new_hist();
        for l in &longs {
            add_hist(&mut pooled, &l.0.hist);
        }
        let p99_long_dn: [f64; 3] = std::array::from_fn(|c| {
            let v = as_values(&pooled[c], lv.0, range, 1.0);
            weighted_percentile(&v, 0.99).unwrap_or(1.0) * f64::from(range)
        });
        // Pass B: each pair's ratio, body and short values.
        let pair_results: Vec<PairResult> = pool.install(|| {
            plan.pairs
                .par_iter()
                .zip(longs.into_par_iter())
                .map(|((l, s), (lp, _))| -> Result<PairResult> {
                    let (fl, fs) = (decode(&l.path)?, decode(&s.path)?);
                    let (vl, vs) = (view(&fl), view(&fs));
                    ensure!(
                        vl.width == vs.width && vl.height == vs.height,
                        "a pair of different sizes at focus {}",
                        l.focus
                    );
                    ensure!(
                        (vs.black, vs.white) == lv,
                        "frames with different black or white levels in one survey"
                    );
                    let noise = profile::noise_model_for(&fs.camera, fs.iso, fs.levels);
                    let var = |c: usize, sig: f32| noise.variance(plane_of(c), sig);
                    let sigma = |c: usize, sig: f32| noise.sigma(plane_of(c), sig);
                    let ratio = measure_ratio(&vl, &vs, &var);
                    let commanded = code_effective(s.shutter).unwrap_or(1.0)
                        / code_effective(l.shutter).unwrap_or(1.0);
                    let used = ratio.ratio.unwrap_or(commanded);
                    let cut = set_aside_cut(p99_long_dn, used, &sigma);
                    let pass = pair_pass(&vl, &vs, &mask_at(l.focus), used, cut);
                    Ok(PairResult {
                        focus: l.focus,
                        long_code: l.shutter,
                        short_code: s.shutter,
                        ratio,
                        used,
                        pass,
                        long_hist: lp.hist,
                        pinned_long: lp.pinned,
                        noise,
                    })
                })
                .collect::<Result<_>>()
        })?;
        let unmeasured = pair_results
            .iter()
            .filter(|p| p.ratio.ratio.is_none())
            .count();
        if unmeasured > 0 {
            notes.push(format!(
                "{unmeasured} pair(s) had too few cells well exposed in both: their commanded ratio was used"
            ));
        }
        if provenance != Provenance::Profile {
            notes.push(
                "no camera profile: the noise model is a fallback and the highlight noise guard means little"
                    .into(),
            );
        }
        Some(census(&pair_results, lv, plan.long_code, &offered)?)
    };

    // Depth, with half a sharp width each side.
    let depth_out = depth.as_ref().map(|d| {
        let f = |i: usize| e.planes[i].position;
        let half = step.width.map(|w| w / 2.0);
        DepthOut {
            first_focus: f(d.first),
            last_focus: f(d.last),
            core_first_focus: f(d.core_first),
            core_last_focus: f(d.core_last),
            first_plane: e.planes[d.first].ordinal,
            last_plane: e.planes[d.last].ordinal,
            suggested_start: f(d.first).zip(half).map(|(a, h)| a - h),
            suggested_end: f(d.last).zip(half).map(|(a, h)| a + h),
        }
    });

    let summary = summarize(
        &plan,
        scope,
        outline.as_ref().map(|_| {
            subject_value["area_share"]
                .as_f64()
                .map_or(String::new(), |a| {
                    format!(" ({:.1} % of the frame)", 100.0 * a)
                })
        }),
        depth_out.as_ref(),
        &step,
        result.as_ref(),
    );
    let iso = plan
        .pairs
        .first()
        .and_then(|p| p.0.iso)
        .or(plan.longs[0].iso);
    let out = SurveyJson {
        subject: subject_value,
        scope: scope.into(),
        depth: depth_out,
        step,
        body: result.as_ref().map(|r| r.body.clone()),
        ratio: result.as_ref().map(|r| r.ratio.clone()),
        census: result.as_ref().map(|r| r.census.clone()),
        advice: result.as_ref().map(|r| r.advice.clone()),
        levels: frame_levels,
        shutters: ShuttersOut {
            long_code: plan.long_code,
            long_s: code_seconds(plan.long_code),
            long_effective_s: code_effective(plan.long_code),
            short_code: plan.short_code,
            short_s: plan.short_code.and_then(code_seconds),
            short_effective_s: plan.short_code.and_then(code_effective),
            iso,
            offered: offered.len(),
        },
        positions: PositionsOut {
            pairs: plan.pairs.len(),
            long: plan.longs.len(),
            dense: plan.dense.len(),
            subject_frames: frames.len(),
            skipped_groups: skipped,
            notes,
        },
        summary,
    };

    let mut report = String::new();
    let mut line = |s: String| {
        report.push_str(&s);
        report.push('\n');
    };
    line(format!("survey          : {}", args.dir.display()));
    line(format!(
        "shots           : {} pairs at {} / {}, {} long positions, {} for the step, {} groups skipped",
        out.positions.pairs,
        code_label(plan.long_code),
        plan.short_code.map_or("-".into(), code_label),
        out.positions.long,
        out.positions.dense,
        skipped
    ));
    line(format!("noise model     : {provenance:?}"));
    if let Some([b, w]) = frame_levels {
        line(format!("levels          : black {b}, white {w}"));
    }
    if let Some(r) = &result {
        for p in &r.ratio.per_position {
            line(format!(
                "ratio @ {:>6}   : commanded {:.5} (marked {:.5}), measured {} on {} cells{}",
                p.focus,
                p.commanded,
                p.commanded_marked,
                p.measured.map_or("-".into(), |m| format!("{m:.5}")),
                p.cells,
                p.off_commanded_pct
                    .map_or(String::new(), |o| format!(" ({o:+.1} %)"))
            ));
        }
        line(format!(
            "body (long)     : R p50 {:.4} p99.9 {:.4} | G p50 {:.4} p99.9 {:.4} | B p50 {:.4} p99.9 {:.4}; {} sites, {} set aside",
            r.body.levels.r.p50,
            r.body.levels.r.p999,
            r.body.levels.g.p50,
            r.body.levels.g.p999,
            r.body.levels.b.p50,
            r.body.levels.b.p999,
            r.body.sites,
            r.body.set_aside_sites
        ));
        line(format!(
            "census (x long FS): R p99.9 {:.3} p99.99 {:.3} max {:.3} | G {:.3} {:.3} {:.3} | B {:.3} {:.3} {:.3}; {} highlight sites, {} pinned in the short frames",
            r.census.tails.r.p999,
            r.census.tails.r.p9999,
            r.census.tails.r.max,
            r.census.tails.g.p999,
            r.census.tails.g.p9999,
            r.census.tails.g.max,
            r.census.tails.b.p999,
            r.census.tails.b.p9999,
            r.census.tails.b.max,
            r.census.highlight_sites,
            r.census.pinned_short_sites
        ));
        line(format!(
            "unconfirmed     : {} short sites above the body that the long frame does not show (fixed pattern, hot pixels)",
            r.census.unconfirmed_sites
        ));
        for (p, a) in r
            .census
            .pinned_long_per_position
            .iter()
            .zip(&r.census.per_position)
        {
            line(format!(
                "census @ {:>6}  : max R {:.3} G {:.3} B {:.3}, {} highlight sites; pinned {} in the long frame, {} predicted from the short",
                p.focus, a.max[0], a.max[1], a.max[2], a.highlight_sites, p.pinned, p.predicted
            ));
        }
    }
    line(format!(
        "time            : {:.1} s",
        t0.elapsed().as_secs_f64()
    ));
    line(format!("summary         : {}", out.summary));
    let text = serde_json::to_string_pretty(&out)?;
    if args.print_json {
        eprint!("{report}");
        println!("{text}");
    } else {
        print!("{report}");
    }
    if let Some(path) = &args.json {
        std::fs::write(path, &text).with_context(|| format!("write {}", path.display()))?;
    }
    Ok(())
}

fn summarize(
    plan: &Plan,
    scope: &str,
    area: Option<String>,
    depth: Option<&DepthOut>,
    step: &StepJson,
    r: Option<&Census>,
) -> String {
    let mut s = Vec::new();
    match (area, depth) {
        (Some(a), Some(d)) => s.push(format!(
            "Subject found{a}, sharp from focus {} to {}.",
            d.first_focus.map_or("?".into(), |f| format!("{f:.0}")),
            d.last_focus.map_or("?".into(), |f| format!("{f:.0}"))
        )),
        (Some(a), None) => s.push(format!("Subject{a}; no part of it comes into focus.")),
        (None, _) => s.push(format!(
            "No subject: the statistics cover the whole {scope}."
        )),
    }
    match (step.width, step.suggested_step) {
        (Some(w), Some(st)) => s.push(format!(
            "Detail stays sharp over about {w:.0} focus units; a step of {st} suits it."
        )),
        _ if step.positions < 5 => s.push(format!(
            "The step was not measured: {} positions at the current shutter, at least 5 are needed.",
            step.positions
        )),
        _ => s.push(format!(
            "The step was not measurable ({} of {} tiles peaked inside the {} positions; at least {MIN_TILES} are needed).",
            step.tiles, step.tiles_considered, step.positions
        )),
    }
    let Some(r) = r else {
        return s.join(" ");
    };
    let long = code_label(plan.long_code);
    let brightest = ["red", "green", "blue"][(0..3)
        .max_by(|&a, &b| {
            r.body
                .levels
                .get(a)
                .p999
                .total_cmp(&r.body.levels.get(b).p999)
        })
        .unwrap_or(1)];
    s.push(format!(
        "At {long} s the body's diffuse top ({brightest}, 99.9th percentile) sits at {:.2} of full scale.",
        r.body.top
    ));
    if let Some(m) = r.ratio.measured {
        s.push(format!(
            "The short frames measured {m:.4} of the long ({:.4} commanded).",
            r.ratio.commanded
        ));
    }
    if r.census.highlights {
        s.push(format!(
            "Highlights: the brightest subject site reads {:.1} times the {long} s full scale; with a stop of margin (a sparse survey sees glints off their focus) plan for {:.1}.",
            r.census.top,
            r.census.top * 2f64.powf(MARGIN_STOPS)
        ));
    } else {
        s.push("No highlights above the body.".into());
    }
    let a = &r.advice;
    let hp = &a.highlight_pass;
    if r.census.highlights {
        s.push(format!(
            "Choices: a highlight pass at {} with a short group at {}; protect highlights with one exposure at {}; or accept specks at {}, about {:.0} pinned subject sites a plane.",
            code_text(hp.base_code, hp.base_s),
            code_text(hp.short_code, hp.short_s),
            code_text(a.protect.code, a.protect.s),
            code_text(a.accept.code, a.accept.s),
            a.accept.pinned_sites_per_plane
        ));
    } else {
        s.push(format!(
            "One exposure at {} puts the body's top at {TARGET} of full scale, with about {:.0} pinned subject sites a plane.",
            code_text(a.accept.code, a.accept.s),
            a.accept.pinned_sites_per_plane
        ));
    }
    s.push(format!(
        "Suggested: {}.",
        if a.suggested == "highlight_pass" {
            "the highlight pass"
        } else {
            "one exposure (accept)"
        }
    ));
    if r.census.pinned_short_sites > 0 {
        s.push(format!(
            "{} sites were pinned even in the short frames: the census does not see above them.",
            r.census.pinned_short_sites
        ));
    }
    s.join(" ")
}

#[cfg(test)]
#[path = "survey-cmd-tests.rs"]
mod tests;
