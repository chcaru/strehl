//! From evidence to a subject (plan S2 steps 5-8). Cheap enough to re-run on
//! every slider movement: no frame is read again.

use rayon::prelude::*;

use super::evidence::Evidence;
use super::morph::{self, Grid};
use super::outline::{Ring, Source, ThresholdKind};
use super::trace;

/// The user's three controls.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Params {
    /// The threshold stands `2 x sensitivity` lower-side spreads above the
    /// quiet mode (log evidence); in the absolute fallback it is this many
    /// times the noise floor.
    pub sensitivity: f32,
    /// Hysteresis: evidence `grow` spreads above the quiet mode (or, for RAW,
    /// a level `4 x grow` deviations from the backdrop's) joins where it
    /// touches the sure subject. 0 turns growth off.
    pub grow: f32,
    /// Margin added around the result, sensor pixels.
    pub buffer_px: f32,
}

impl Default for Params {
    fn default() -> Self {
        Self {
            sensitivity: 3.0,
            grow: 3.0,
            buffer_px: 16.0,
        }
    }
}

impl Params {
    /// Defaults for live-view evidence: one cell (about 37 sensor px on a
    /// 1024 px preview of a 9504 px sensor) of buffer.
    pub fn live() -> Self {
        Self {
            buffer_px: 40.0,
            ..Self::default()
        }
    }
}

/// A quiet mode above this many times the noise floor means there is no
/// quiet backdrop: the subject fills the frame.
pub const ABSOLUTE_MODE: f32 = 6.0;
/// Width of the frame edge (cells) whose quiet cells define the backdrop.
const BORDER: usize = 6;
/// In-focus regions smaller than this share of the frame are specks (hot
/// pixels, dust, noise) and do not seed a subject.
pub const MIN_SEED_SHARE: f64 = 0.0002;
/// ... and never smaller than this many cells: one hot pixel, spread by the
/// 3 x 3 cell mean, covers up to 16.
pub const MIN_SEED_CELLS: usize = 25;
/// Enclosed holes smaller than this share are filled.
pub const FILL_HOLE_SHARE: f64 = 0.0005;
/// Parts smaller than this share are dropped.
pub const MIN_PART_SHARE: f64 = 0.002;
/// Outline tolerance before the point limit forces more, cells.
const OUTLINE_EPS: f64 = 1.0;

/// The frame's quiet population of log evidence.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Quiet {
    /// Mode of log evidence over its lower 60 %.
    pub mode: f32,
    /// Mode minus the 16th percentile of the values below it (at least 0.02).
    pub spread: f32,
    /// Share of cells in the backdrop: quiet cells connected to the edge.
    pub backdrop_share: f32,
    /// Backdrop level median and robust deviation.
    pub backdrop_level: f32,
    pub backdrop_mad: f32,
}

/// Diagnostics of one selection.
#[derive(Clone, Debug, PartialEq)]
pub struct Stats {
    pub quiet: Quiet,
    pub threshold: ThresholdKind,
    /// The focus threshold, in multiples of the noise floor.
    pub cut: f32,
    /// In-focus cells, and those left after specks were removed.
    pub in_focus_cells: usize,
    pub seed_cells: usize,
    pub specks: usize,
    pub parts: usize,
    pub dropped_parts: usize,
    pub holes_left: usize,
    pub rings: usize,
}

/// First and last plane (indices into [`Evidence::planes`]) at which an
/// in-focus subject cell is sharpest. The evidence is a three-plane running
/// mean, so a sparse survey's first and last can sit one plane outside the
/// subject's true range; `core_*` hold the central 99 % of those cells.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Depth {
    pub first: usize,
    pub last: usize,
    pub core_first: usize,
    pub core_last: usize,
    /// In-focus subject cells sharpest at each plane.
    pub cells: Vec<usize>,
}

#[derive(Clone, Debug)]
pub struct Selection {
    /// The final raster on the evidence grid (row-major).
    pub mask: Vec<bool>,
    /// Outer rings and holes, even-odd, normalised to the active area.
    pub rings: Vec<Ring>,
    /// Share of the frame in the raster.
    pub area_share: f32,
    /// `None` when nothing was found.
    pub depth: Option<Depth>,
    /// The controls this selection used.
    pub params: Params,
    pub threshold: ThresholdKind,
    /// Plain-language reading of the result, including why it is empty.
    pub summary: String,
    pub stats: Stats,
}

/// `q`-th percentile (0..100) with linear interpolation, as numpy's default.
pub(crate) fn percentile(mut v: Vec<f32>, q: f64) -> f32 {
    if v.is_empty() {
        return f32::NAN;
    }
    let pos = q / 100.0 * (v.len() - 1) as f64;
    let k = pos.floor() as usize;
    let frac = (pos - k as f64) as f32;
    let (_, &mut lo, right) = v.select_nth_unstable_by(k, f32::total_cmp);
    if frac == 0.0 || right.is_empty() {
        return lo;
    }
    let hi = right.iter().copied().fold(f32::INFINITY, f32::min);
    lo + (hi - lo) * frac
}

/// The quiet population of an evidence map (plan S2 step 5).
pub fn quiet(e: &Evidence) -> Quiet {
    let lf: Vec<f32> = e.focus.par_iter().map(|&f| f.max(1e-3).ln()).collect();
    let p60 = percentile(lf.clone(), 60.0);
    let low: Vec<f32> = lf.iter().copied().filter(|&v| v <= p60).collect();
    let (lo, hi) = low
        .iter()
        .fold((f32::INFINITY, f32::NEG_INFINITY), |(a, b), &v| {
            (a.min(v), b.max(v))
        });
    const BINS: usize = 120;
    let mut hist = [0.0f64; BINS];
    let width = ((hi - lo) as f64).max(1e-12);
    for &v in &low {
        let b = (((v - lo) as f64 / width) * BINS as f64) as usize;
        hist[b.min(BINS - 1)] += 1.0;
    }
    // Five-bin running mean, edges reflected.
    let at = |i: isize| -> f64 {
        let n = BINS as isize;
        let j = if i < 0 {
            -i - 1
        } else if i >= n {
            2 * n - i - 1
        } else {
            i
        };
        hist[j as usize]
    };
    let mut best = (f64::NEG_INFINITY, 0usize);
    for i in 0..BINS {
        let s: f64 = (-2..=2).map(|d| at(i as isize + d)).sum::<f64>() / 5.0;
        if s > best.0 {
            best = (s, i);
        }
    }
    let mode = (f64::from(lo) + (best.1 as f64 + 0.5) * width / BINS as f64) as f32;
    let below: Vec<f32> = lf.iter().copied().filter(|&v| v < mode).collect();
    let spread = if below.is_empty() {
        0.02
    } else {
        (mode - percentile(below, 16.0)).max(0.02)
    };
    let quiet_cut = (mode + 3.0 * spread).exp();
    let g = Grid {
        cols: e.cols,
        rows: e.rows,
    };
    let quiet: Vec<bool> = e.focus.iter().map(|&f| f < quiet_cut).collect();
    let (lab, sizes) = morph::label(&quiet, g);
    let mut edge = vec![false; sizes.len()];
    for y in 0..e.rows {
        for x in 0..e.cols {
            if y < BORDER || y + BORDER >= e.rows || x < BORDER || x + BORDER >= e.cols {
                edge[lab[y * e.cols + x] as usize] = true;
            }
        }
    }
    let mut backdrop: Vec<bool> = lab.iter().map(|&l| l != 0 && edge[l as usize]).collect();
    let mut count = backdrop.iter().filter(|&&b| b).count();
    if (count as f64) < 0.02 * g.len() as f64 {
        backdrop = quiet;
        count = backdrop.iter().filter(|&&b| b).count();
    }
    let levels: Vec<f32> = e
        .level
        .iter()
        .zip(&backdrop)
        .filter(|(_, b)| **b)
        .map(|(l, _)| *l)
        .collect();
    let (med, mad) = if levels.is_empty() {
        (0.0, 1e-6)
    } else {
        let med = percentile(levels.clone(), 50.0);
        let dev: Vec<f32> = levels.iter().map(|l| (l - med).abs()).collect();
        (med, 1.4826 * percentile(dev, 50.0) + 1e-6)
    };
    Quiet {
        mode,
        spread,
        backdrop_share: count as f32 / g.len() as f32,
        backdrop_level: med,
        backdrop_mad: mad,
    }
}

/// Selects the subject from stored evidence. `quiet` is [`quiet`]`(e)`,
/// passed in so that slider moves do not recompute it.
pub fn select(e: &Evidence, q: &Quiet, p: &Params) -> Selection {
    let g = Grid {
        cols: e.cols,
        rows: e.rows,
    };
    let cells = g.len() as f64;
    let raw = e.layout.source == Source::Raw;
    let absolute = q.mode.exp() > ABSOLUTE_MODE;
    let (threshold, cut) = if absolute {
        (ThresholdKind::Absolute, p.sensitivity)
    } else {
        (
            ThresholdKind::Relative,
            (q.mode + 2.0 * p.sensitivity * q.spread).exp(),
        )
    };
    let in_focus: Vec<bool> = e.focus.iter().map(|&f| f >= cut).collect();
    let in_focus_cells = in_focus.iter().filter(|&&v| v).count();
    // Specks do not seed.
    let min_seed = (MIN_SEED_SHARE * cells).max(MIN_SEED_CELLS as f64).ceil() as usize;
    let (seed, _, specks) = morph::drop_small(&in_focus, g, min_seed);
    let seed_cells = seed.iter().filter(|&&v| v).count();
    // Growth: weaker evidence touching the sure subject. Live view grows on
    // focus evidence only: its defocused glow differs from the backdrop.
    let mut m = if p.grow > 0.0 {
        let weak_cut = (q.mode + p.grow * q.spread).exp();
        let level_cut = 4.0 * p.grow;
        let weak: Vec<bool> = e
            .focus
            .par_iter()
            .zip(&e.level)
            .zip(&seed)
            .map(|((&f, &l), &s)| {
                s || f >= weak_cut
                    || (raw && (l - q.backdrop_level).abs() / q.backdrop_mad >= level_cut)
            })
            .collect();
        morph::reconstruct(&weak, &seed, g)
    } else {
        seed
    };
    // Clean-up: close, fill small enclosed holes, open (RAW), drop small parts.
    m = morph::close(&m, g, if raw { 3 } else { 2 });
    let holes = morph::holes(&m, g);
    let (hl, hs) = morph::label(&holes, g);
    let fill = FILL_HOLE_SHARE * cells;
    for (v, &l) in m.iter_mut().zip(&hl) {
        if l != 0 && (hs[l as usize] as f64) < fill {
            *v = true;
        }
    }
    let holes_left = hs.iter().skip(1).filter(|&&s| s as f64 >= fill).count();
    if raw {
        m = morph::open(&m, g, 1);
    }
    let min_part = if raw {
        (MIN_PART_SHARE * cells).max(60.0)
    } else {
        MIN_PART_SHARE * cells
    };
    let (kept, parts, dropped_parts) = morph::drop_small(&m, g, min_part.ceil() as usize);
    m = kept;
    let iterations = (p.buffer_px / e.layout.cell_px).round().max(0.0) as usize;
    if iterations > 0 && parts > 0 {
        m = morph::dilate(&m, g, iterations);
    }
    let rings = trace::rings(&m, g, e.layout.cell_norm, OUTLINE_EPS);
    let area = m.iter().filter(|&&v| v).count();
    // Depth range: sharpest plane of every in-focus subject cell.
    let mut sharpest = vec![0usize; e.planes.len()];
    for ((&inside, &sharp), &d) in m.iter().zip(&in_focus).zip(&e.depth) {
        if inside && sharp {
            sharpest[d as usize] += 1;
        }
    }
    let total: usize = sharpest.iter().sum();
    let depth = (total > 0).then(|| {
        let first = sharpest.iter().position(|&c| c > 0).unwrap_or(0);
        let last = sharpest.iter().rposition(|&c| c > 0).unwrap_or(0);
        // The planes holding the central 99 % of those cells.
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
        Depth {
            first,
            last,
            core_first,
            core_last,
            cells: sharpest,
        }
    });
    let share = area as f32 / cells as f32;
    let floor_note = match threshold {
        ThresholdKind::Relative => format!(
            "threshold {cut:.2} x the noise floor, set against the frame's quiet cells (mode {:.2} x, spread {:.3})",
            q.mode.exp(),
            q.spread
        ),
        ThresholdKind::Absolute => format!(
            "no quiet backdrop (quiet mode {:.1} x the noise floor, above {ABSOLUTE_MODE}): absolute threshold {cut:.2} x the noise floor",
            q.mode.exp()
        ),
    };
    let summary = if area == 0 {
        if seed_cells == 0 {
            format!(
                "No subject: nothing comes into focus in these {} planes ({in_focus_cells} in-focus cells, all in specks under {min_seed} cells). The subject is out of focus throughout, or outside the planes surveyed; {floor_note}.",
                e.planes.len()
            )
        } else {
            format!(
                "No subject: what comes into focus forms only parts under {:.1} % of the frame; {floor_note}.",
                100.0 * MIN_PART_SHARE
            )
        }
    } else {
        let d = depth.as_ref().map_or(String::new(), |d| {
            format!(
                "; sharp from plane {} to {}",
                e.planes[d.first].ordinal, e.planes[d.last].ordinal
            )
        });
        format!(
            "Subject: {:.1} % of the frame in {parts} part(s), {holes_left} hole(s) left out{d}; {floor_note}.",
            100.0 * share
        )
    };
    let stats = Stats {
        quiet: *q,
        threshold,
        cut,
        in_focus_cells,
        seed_cells,
        specks,
        parts,
        dropped_parts,
        holes_left,
        rings: rings.len(),
    };
    Selection {
        mask: m,
        rings,
        area_share: share,
        depth,
        params: *p,
        threshold,
        summary,
        stats,
    }
}
