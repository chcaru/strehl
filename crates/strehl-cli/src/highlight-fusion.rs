//! Plan X4: highlight fusion at the gather
//! (`docs/proposals/2026-11-subject-highlights-and-detail-plan.md`, X3-X4;
//! the capture format is `experiments/subject-highlights-detail-2026-11-23/impl/tiers.md`).
//!
//! A capture may take, at a focal plane, a second four-shot group at a
//! shorter shutter (tier `highlight`). Only base groups make the stack; a
//! base frame gets its plane's highlight group as a *companion*, or, when the
//! plan takes one every `every` planes, the nearest plane's.
//!
//! # What happens to a base frame with a companion
//!
//! 1. **Ratio.** The commanded shutter ratio is only the start: it is
//!    corrected from sites well exposed in both groups by the bounded fit of
//!    the session pipeline (`session-photometry.rs`, `assess_pair`: trimmed
//!    patch means per colour, the median log ratio of fit patches, at most
//!    0.25 EV of correction, held-out validation patches within 1 / 3 / 5 %,
//!    a textured-agreement check). That module is compiled only with
//!    `multi-stack`, so its rule is restated here with its tolerances. A
//!    refused fit leaves the frame the base exposure alone, and the log says
//!    so.
//! 2. **Where.** A site of the gathered plane is replaced where any colour
//!    of the base group within the site's resampling footprint, widened by a
//!    two-photosite guard, is near the raw pin: a smooth ramp from 0.75 to
//!    0.90 of the pin on the brightest of the four samples each photosite
//!    holds, so all colours of a site switch together.
//! 3. **Value.** The companion's own sample at the same output site, gathered
//!    through its own placement (its plane's placement plus the shift of its
//!    member 1 against that plane's base member 1, measured as member offsets
//!    are), times the ratio.
//! 4. **Storage.** The base plane stays u16; replaced sites travel as a
//!    sparse list (site, weight, value) applied when the planes are lifted to
//!    f32, on the CPU here and on the GPU in its preparation, before luma and
//!    variance.
//! 5. **Noise.** The same injected model, evaluated on the companion's sample
//!    and scaled by the ratio squared, blended by the weight.
//!
//! The focus election is untouched (M54): it receives planes whose pinned
//! sites hold real values. `STREHL_HIGHLIGHT_FUSION=off` renders a tiered
//! capture as its base exposure alone.
// `!(x < limit)` is deliberate: it also rejects NaN.
#![allow(clippy::neg_cmp_op_on_partial_ord)]
use anyhow::{Context, Result};
use rayon::prelude::*;
use std::collections::{BTreeMap, HashMap};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use strehl_core::CfaPlane;
use strehl_core::align::{Cx, Similarity};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::noise::NoiseModel;
use strehl_core::optics::{Channel, OpticalProfile};
use strehl_core::plane::PlaneGeometry;

use crate::align_cmd::{CARRIED_SITES, MeasuredGroup, WarpScratch};
use crate::pixel_shift_cmd::{GroupJournal, RecordedGroup, ResidualMode, Tier};

/// `STREHL_HIGHLIGHT_FUSION`: `on` (the default) fuses a capture's highlight
/// groups; `off` renders it as its base exposure alone.
pub const ENV: &str = "STREHL_HIGHLIGHT_FUSION";
/// `STREHL_HIGHLIGHT_RATIO_PLANT=<factor>`: multiply the starting exposure
/// ratio by `factor` (a gate: a 5 % error must be corrected, 25 % refused).
pub const PLANT_ENV: &str = "STREHL_HIGHLIGHT_RATIO_PLANT";
/// `STREHL_HIGHLIGHT_REPORT=<path>`: one JSON line per fused frame.
pub const REPORT_ENV: &str = "STREHL_HIGHLIGHT_REPORT";

/// The replacement ramp, as fractions of the raw pin above black.
pub const RAMP_LO: f32 = 0.75;
pub const RAMP_HI: f32 = 0.90;
/// Photosites added around a site's resampling footprint.
pub const GUARD: isize = 2;
/// Fit patches: the base below this fraction of the pin everywhere.
const FIT_CEILING: f32 = 0.70;
/// Side of a fit patch, photosites (32 x 32 quads, the session's patch).
const PATCH: usize = 64;
/// Patches the fit uses at most (half of them held out).
const MAX_PATCHES: usize = 64;
/// The session's tolerances (`PhotometryConfig::default`).
const MIN_FIT: usize = 6;
const MIN_VALIDATION: usize = 6;
const MIN_TEXTURED: usize = 4;
const SIGNAL_SIGMA: f32 = 8.0;
const CORRECTION_LIMIT_EV: f32 = 0.25;
const MEDIAN_LIMIT: f32 = 0.01;
const P95_LIMIT: f32 = 0.03;
const MAX_LIMIT: f32 = 0.05;
const TEXTURE_LIMIT: f32 = 0.1;
/// The session allows 16 times the injected variance before a patch counts
/// as textured (its passes lie within about 1 EV). A highlight group lies 3
/// to 5 EV under the base, so its noise scaled by the ratio squared is 8 to
/// 26 times the base's, and with that allowance no patch of the weevil
/// fixture counted as textured (MEASURED: 0 of 32 on two planes). Here the
/// variance is the injected model's own, unallowed; a patch still needs 16
/// times it in texture power, and the residual test is the session's.
const NOISE_ALLOWANCE: f32 = 1.0;
/// Bright-map tile side, photosites.
const TILE: usize = 16;

fn enabled() -> Result<bool> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(true),
        Err(e) => Err(e).context(ENV),
        Ok(v) => match v.trim() {
            "" | "on" | "1" => Ok(true),
            "off" | "0" => Ok(false),
            other => anyhow::bail!("{ENV}={other:?} is not on or off"),
        },
    }
}

fn plant() -> Result<f64> {
    match std::env::var(PLANT_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(1.0),
        Err(e) => Err(e).context(PLANT_ENV),
        Ok(v) if v.trim().is_empty() => Ok(1.0),
        Ok(v) => {
            let f: f64 = v
                .trim()
                .parse()
                .with_context(|| format!("{PLANT_ENV}={v:?} is not a number"))?;
            anyhow::ensure!(
                f.is_finite() && f > 0.0,
                "{PLANT_ENV}={v:?} must be positive"
            );
            Ok(f)
        }
    }
}

/// One base frame's companion: which highlight group, which base group of
/// its own plane it was taken with, and the commanded ratio.
pub struct CompanionRef {
    /// The base frame's plane.
    pub plane: u64,
    /// The highlight group's plane (the base plane, or the nearest).
    pub companion_plane: u64,
    /// The highlight group's id.
    pub key: String,
    pub paths: [PathBuf; 4],
    /// Member 1 of the base group of the companion's plane, taken in the
    /// same visit: the companion's shift is measured against it.
    pub anchor_m1: PathBuf,
    /// That frame's index in the stack (for its placement), if it is in it.
    pub anchor_index: Option<usize>,
    /// Commanded base / highlight exposure, from the shutter codes.
    pub nominal: Option<f64>,
    /// [`PLANT_ENV`].
    pub plant: f64,
    journal: Option<Arc<GroupJournal>>,
    residual: ResidualMode,
}

/// The render's companions by the base frame's member-1 path
/// ([`companions`] installs them, [`Render`] clears them).
fn table() -> &'static Mutex<HashMap<PathBuf, Arc<CompanionRef>>> {
    static TABLE: std::sync::OnceLock<Mutex<HashMap<PathBuf, Arc<CompanionRef>>>> =
        std::sync::OnceLock::new();
    TABLE.get_or_init(Default::default)
}

/// Pair every complete four-shot base plane of `base` that the stack holds
/// (`planes`, member-1 paths in frame order) with its highlight companion,
/// install them for the render, and return the banner's line.
pub(crate) fn companions(
    dir: &Path,
    all: &[RecordedGroup],
    base: &[RecordedGroup],
    planes: &[PathBuf],
    journal: Option<Arc<GroupJournal>>,
    residual: ResidualMode,
) -> Result<Option<String>> {
    let (map, line) = pair(dir, all, base, planes, journal, residual)?;
    let mut refs: Vec<Arc<CompanionRef>> = map.values().cloned().collect();
    refs.sort_by_key(|c| c.plane);
    *order().lock().unwrap_or_else(|e| e.into_inner()) = refs;
    *table().lock().unwrap_or_else(|e| e.into_inner()) = map;
    Ok(line)
}

type Paired = (HashMap<PathBuf, Arc<CompanionRef>>, Option<String>);

fn pair(
    dir: &Path,
    all: &[RecordedGroup],
    base: &[RecordedGroup],
    planes: &[PathBuf],
    journal: Option<Arc<GroupJournal>>,
    residual: ResidualMode,
) -> Result<Paired> {
    let highlights: BTreeMap<u64, RecordedGroup> =
        crate::pixel_shift_cmd::tier_groups(all.to_vec(), &Tier::Highlight)
            .into_iter()
            .filter(|(_, g)| g.complete && g.files.len() == 4)
            .collect();
    let other = all
        .iter()
        .filter(|g| matches!(g.tier, Tier::Other(_)))
        .count();
    let other_line = (other > 0).then(|| {
        format!("exposure tiers  : {other} groups of another tier are recorded and not used")
    });
    if highlights.is_empty() {
        return Ok((HashMap::new(), other_line));
    }
    if !enabled()? {
        return Ok((
            HashMap::new(),
            Some(format!(
                "highlights      : {} highlight groups recorded, NOT fused ({ENV}=off): the \
                 stack is the base exposure alone",
                highlights.len()
            )),
        ));
    }
    let plan = crate::pixel_shift_cmd::highlight_plan(dir);
    let every = plan.every.unwrap_or(1).max(1);
    let plant = plant()?;
    let index: HashMap<&Path, usize> = planes
        .iter()
        .enumerate()
        .map(|(i, p)| (p.as_path(), i))
        .collect();
    let four: BTreeMap<u64, &RecordedGroup> = base
        .iter()
        .filter(|g| g.complete && g.files.len() == 4)
        .map(|g| (g.plane, g))
        .collect();
    let seconds = crate::pixel_shift_cmd::shutter_seconds;
    let mut out = HashMap::new();
    let (mut own, mut near, mut uncommanded) = (0usize, 0usize, 0usize);
    for g in four.values() {
        let m1 = &g.files[0].path;
        if !index.contains_key(m1.as_path()) {
            continue;
        }
        let q = if highlights.contains_key(&g.plane) {
            Some(g.plane)
        } else if every > 1 {
            highlights
                .keys()
                .copied()
                .filter(|q| q.abs_diff(g.plane) < every)
                .min_by_key(|q| (q.abs_diff(g.plane), *q))
        } else {
            None
        };
        // A highlight group is measured against the base group it was
        // taken with, so that plane needs one.
        let Some((q, anchor)) = q.and_then(|q| four.get(&q).map(|a| (q, a))) else {
            continue;
        };
        let h = &highlights[&q];
        let nominal = g
            .shutter
            .or(plan.base_shutter)
            .and_then(seconds)
            .zip(h.shutter.or(plan.shutter).and_then(seconds))
            .map(|(b, s)| b / s);
        if nominal.is_none() {
            uncommanded += 1;
        }
        if q == g.plane {
            own += 1;
        } else {
            near += 1;
        }
        let paths: [PathBuf; 4] = std::array::from_fn(|k| h.files[k].path.clone());
        out.insert(
            m1.clone(),
            Arc::new(CompanionRef {
                plane: g.plane,
                companion_plane: q,
                key: h.key(),
                paths,
                anchor_m1: anchor.files[0].path.clone(),
                anchor_index: index.get(anchor.files[0].path.as_path()).copied(),
                nominal,
                plant,
                journal: journal.clone(),
                residual,
            }),
        );
    }
    let mut line = format!(
        "highlights      : {} of {} four-shot planes have a highlight companion ({own} their own \
         plane's, {near} the nearest plane's; every {every}); replaced near the raw pin at the \
         gather, ratio measured per pair{}",
        out.len(),
        four.len(),
        if uncommanded > 0 {
            format!(" ({uncommanded} without a commanded exposure: started from the data)")
        } else {
            String::new()
        }
    );
    if plant != 1.0 {
        line += &format!("\n                  {PLANT_ENV}={plant}: the starting ratio is planted");
    }
    if let Some(o) = other_line {
        line += &format!("\n{o}");
    }
    Ok((out, Some(line)))
}

// ---------------------------------------------------------------------------
// the companion's data, loaded once and kept for the next frame that uses it
// ---------------------------------------------------------------------------

struct Loaded {
    /// Member 1 and the group (members 2-4, measured; `None` when the group
    /// is demoted), taken by a gather and put back.
    frames: Mutex<Option<(strehl_raw::Frame, Option<MeasuredGroup>)>>,
    /// The group's demotion, if the stack's own gate refuses it: then it is
    /// used as its member 1 alone.
    gate: Option<String>,
}

/// Each companion's shift (by group id) against its plane's base member 1,
/// photosites, measured once per render.
fn shifts() -> &'static Mutex<HashMap<String, Measured<[f64; 2]>>> {
    static SHIFTS: std::sync::OnceLock<Mutex<HashMap<String, Measured<[f64; 2]>>>> =
        std::sync::OnceLock::new();
    SHIFTS.get_or_init(Default::default)
}

/// A measurement, or why it was refused.
type Measured<T> = std::result::Result<T, String>;

/// One companion's place in the cache, decoded outside the cache's lock.
///
/// A thread that finds it being decoded waits only if it is not a rayon
/// worker: the decode itself runs on the rayon pool, and a worker that
/// blocks (or, while it waits inside the decode's own parallel loop, steals
/// a job that asks for the same companion) could starve or re-enter it. A
/// worker decodes its own copy instead; the cost is a duplicate decode, never
/// a deadlock (one was observed with a `OnceLock` here).
struct Slot {
    paths: [PathBuf; 4],
    state: Mutex<SlotState>,
    ready: std::sync::Condvar,
}

enum SlotState {
    Empty,
    Loading,
    Ready(std::result::Result<Arc<Loaded>, String>),
}

fn loaded_cache() -> &'static Mutex<Vec<Arc<Slot>>> {
    static CACHE: std::sync::OnceLock<Mutex<Vec<Arc<Slot>>>> = std::sync::OnceLock::new();
    CACHE.get_or_init(Default::default)
}

/// Companions kept decoded, four frames each: the decode-ahead preloads a
/// few frames before the fold uses them.
const LOADED_KEPT: usize = 4;

/// The render's companions in plane order, for loading the next one while
/// the fold uses this one.
fn order() -> &'static Mutex<Vec<Arc<CompanionRef>>> {
    static ORDER: std::sync::OnceLock<Mutex<Vec<Arc<CompanionRef>>>> = std::sync::OnceLock::new();
    ORDER.get_or_init(Default::default)
}

/// Start decoding the companion that follows `r`'s in plane order, in the
/// background: the fold takes planes in order, so it is usually next.
fn load_next(r: &CompanionRef) {
    let next = {
        let order = order().lock().unwrap_or_else(|e| e.into_inner());
        order
            .iter()
            .skip_while(|c| c.plane <= r.plane)
            .find(|c| c.paths != r.paths)
            .cloned()
    };
    if let Some(next) = next {
        // Its own thread, not a rayon worker: it may wait (see [`Slot`]).
        std::thread::spawn(move || {
            let _ = load(&next);
        });
    }
}

fn load(r: &CompanionRef) -> Result<Arc<Loaded>> {
    let slot = {
        let mut cache = loaded_cache().lock().unwrap_or_else(|e| e.into_inner());
        match cache.iter().find(|s| s.paths == r.paths) {
            Some(s) => Arc::clone(s),
            None => {
                let s = Arc::new(Slot {
                    paths: r.paths.clone(),
                    state: Mutex::new(SlotState::Empty),
                    ready: std::sync::Condvar::new(),
                });
                cache.push(Arc::clone(&s));
                while cache.len() > LOADED_KEPT {
                    cache.remove(0);
                }
                s
            }
        }
    };
    let may_wait = rayon::current_thread_index().is_none();
    let decode_here = {
        let mut st = slot.state.lock().unwrap_or_else(|e| e.into_inner());
        loop {
            match &*st {
                SlotState::Ready(r) => return r.clone().map_err(|e| anyhow::anyhow!(e)),
                SlotState::Loading if may_wait => {
                    st = slot.ready.wait(st).unwrap_or_else(|e| e.into_inner());
                }
                SlotState::Loading => break false,
                SlotState::Empty => {
                    *st = SlotState::Loading;
                    break true;
                }
            }
        }
    };
    let loaded = decode_companion(r).map_err(|e| format!("{e:#}"));
    if decode_here {
        *slot.state.lock().unwrap_or_else(|e| e.into_inner()) = SlotState::Ready(loaded.clone());
        slot.ready.notify_all();
    }
    loaded.map_err(|e| anyhow::anyhow!(e))
}

fn decode_companion(r: &CompanionRef) -> Result<Arc<Loaded>> {
    let frames: Vec<strehl_raw::Frame> = r
        .paths
        .par_iter()
        .map(|p| strehl_raw::decode(p).with_context(|| p.display().to_string()))
        .collect::<Result<_>>()?;
    let first = &frames[0];
    let noise = strehl_core::profile::noise_model_for(
        &first.camera,
        first.iso,
        strehl_core::noise::Levels {
            black: first.levels.black,
            white: first.levels.white,
        },
    );
    let m = crate::pixel_shift_cmd::measure_cached(
        r.journal.as_deref(),
        [&r.paths[0], &r.paths[1], &r.paths[2], &r.paths[3]].map(PathBuf::as_path),
        [&frames[0], &frames[1], &frames[2], &frames[3]],
        &noise,
        r.companion_plane as usize,
    );
    let gate = crate::pixel_shift_cmd::judge(&m, r.residual);
    let mut it = frames.into_iter();
    let m1 = it.next().expect("four frames");
    let members: [strehl_raw::Frame; 3] = [
        it.next().expect("four frames"),
        it.next().expect("four frames"),
        it.next().expect("four frames"),
    ];
    let c = &m.check;
    let group = MeasuredGroup {
        members,
        offsets: c.offsets,
        gains: c.gains,
        residuals: r.residual.sign().map(|s| (c.residual, s)),
        keep: true,
    };
    // A demoted group is used as its member 1 alone, as the stack folds a
    // demoted base group.
    let group = gate.is_none().then_some(group);
    Ok(Arc::new(Loaded {
        frames: Mutex::new(Some((m1, group))),
        gate,
    }))
}

// ---------------------------------------------------------------------------
// the base group's brightness, per photosite
// ---------------------------------------------------------------------------

/// The brightest of the four samples each photosite of a group holds (its
/// red, two greens and blue), raw codes, over the active area; and its
/// maximum per [`TILE`] square.
struct Bright {
    w: usize,
    h: usize,
    b: Vec<u16>,
    tw: usize,
    tiles: Vec<u16>,
}

impl Bright {
    /// A group's, or a lone frame's (each photosite its own sample).
    fn new(frame: &strehl_raw::Frame, group: Option<&MeasuredGroup>) -> Self {
        match group {
            Some(group) => Self::of(
                frame,
                &[
                    &frame.data,
                    &group.members[0].data,
                    &group.members[1].data,
                    &group.members[2].data,
                ],
                &group.offsets,
            ),
            None => Self::of(frame, &[&frame.data], &[(0, 0)]),
        }
    }

    /// Over the members `sources` (member 1 first; buffers of `frame`'s
    /// geometry) at their measured `offsets`.
    fn of(frame: &strehl_raw::Frame, sources: &[&[u16]], offsets: &[(isize, isize)]) -> Self {
        let (ax, ay) = (frame.active.x as isize, frame.active.y as isize);
        let (w, h) = (frame.active.width, frame.active.height);
        let (stride, bh) = (frame.stride as isize, frame.buffer_height as isize);
        let mut b = vec![0u16; w * h];
        b.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
            for (x, o) in row.iter_mut().enumerate() {
                let mut m = 0u16;
                for (src, &(ox, oy)) in sources.iter().zip(offsets) {
                    let bx = ax + x as isize + ox;
                    let by = ay + y as isize + oy;
                    if bx >= 0 && by >= 0 && bx < stride && by < bh {
                        m = m.max(src[(by * stride + bx) as usize]);
                    }
                }
                *o = m;
            }
        });
        let (tw, th) = (w.div_ceil(TILE), h.div_ceil(TILE));
        let mut tiles = vec![0u16; tw * th];
        tiles.par_chunks_mut(tw).enumerate().for_each(|(ty, trow)| {
            for y in ty * TILE..((ty + 1) * TILE).min(h) {
                for (x, v) in b[y * w..(y + 1) * w].iter().enumerate() {
                    let t = &mut trow[x / TILE];
                    *t = (*t).max(*v);
                }
            }
        });
        Self { w, h, b, tw, tiles }
    }

    /// Maximum over the inclusive window, clamped to the active area, of the
    /// tiles (`exact` false, an upper bound) or the photosites.
    fn max(&self, x0: isize, y0: isize, x1: isize, y1: isize, exact: bool) -> u16 {
        let cx = |x: isize| x.clamp(0, self.w as isize - 1) as usize;
        let cy = |y: isize| y.clamp(0, self.h as isize - 1) as usize;
        let (x0, x1, y0, y1) = (cx(x0), cx(x1), cy(y0), cy(y1));
        let mut m = 0u16;
        if exact {
            for y in y0..=y1 {
                for &v in &self.b[y * self.w + x0..=y * self.w + x1] {
                    m = m.max(v);
                }
            }
        } else {
            for ty in y0 / TILE..=y1 / TILE {
                for tx in x0 / TILE..=x1 / TILE {
                    m = m.max(self.tiles[ty * self.tw + tx]);
                }
            }
        }
        m
    }
}

/// Plan X5's cue, for the in-capture checker: the CFA sites (2 x 2
/// photosite quads of member 1's active area) any of whose colours is at or
/// above [`RAMP_HI`] of the raw pin, the level from which the fusion
/// replaces a site outright. Member 1 alone, so a group the stack demotes
/// counts on the same scale as one it assembles. With the capture's subject
/// (`plan.subject` rings, normalised to the active area), only sites inside
/// it count.
pub(crate) fn pinned_sites(
    frame: &strehl_raw::Frame,
    subject: Option<&[strehl_core::subject::Ring]>,
) -> usize {
    let (ax, ay) = (frame.active.x, frame.active.y);
    let (w, h) = (frame.active.width, frame.active.height);
    let black = frame.levels.black;
    let near = (black + RAMP_HI * (f32::from(CONTAINER_MAX_DN) - black)) as u16;
    let (qw, qh) = (w / 2, h / 2);
    let mask = subject.map(|rings| {
        let (cols, rows) = (qw.div_ceil(TILE), qh.div_ceil(TILE));
        let cell = [2.0 * TILE as f64 / w as f64, 2.0 * TILE as f64 / h as f64];
        strehl_core::subject::rasterize(rings, cols, rows, cell)
    });
    let tw = qw.div_ceil(TILE);
    (0..qh)
        .into_par_iter()
        .map(|qy| {
            let r0 = &frame.data[(ay + 2 * qy) * frame.stride + ax..][..2 * qw];
            let r1 = &frame.data[(ay + 2 * qy + 1) * frame.stride + ax..][..2 * qw];
            (0..qw)
                .filter(|&qx| {
                    let m = r0[2 * qx]
                        .max(r0[2 * qx + 1])
                        .max(r1[2 * qx])
                        .max(r1[2 * qx + 1]);
                    m >= near
                        && mask
                            .as_ref()
                            .is_none_or(|k| k[(qy / TILE) * tw + qx / TILE])
                })
                .count()
        })
        .sum()
}

/// The ramp's weight for a window's brightest raw code.
fn ramp(v: u16, black: f32, full: f32) -> f32 {
    let u = ((f32::from(v) - black) / full - RAMP_LO) / (RAMP_HI - RAMP_LO);
    let u = u.clamp(0.0, 1.0);
    u * u * (3.0 - 2.0 * u)
}

// ---------------------------------------------------------------------------
// assembled samples of a group (no interpolation of colour)
// ---------------------------------------------------------------------------

/// A four-shot group read as the gather assembles it (`measured_rows`,
/// without white balance): every photosite's red, green (mean of two) and
/// blue, black-subtracted and divided by the member's exposure gain. A group
/// that failed its check is its member 1 alone, a mosaic: there a colour a
/// photosite lacks is the mean of its nearest photosites of that colour
/// (for the ratio's patches and the hand-over check only; the gather
/// demosaics such a frame as it does any).
struct Assembled<'a> {
    sources: [&'a [u16]; 4],
    offsets: [(isize, isize); 4],
    inv: [f32; 4],
    single: bool,
    stride: isize,
    bh: isize,
    origin: (isize, isize),
    size: (isize, isize),
    black: f32,
}

impl<'a> Assembled<'a> {
    fn new(frame: &'a strehl_raw::Frame, group: Option<&'a MeasuredGroup>) -> Self {
        let (sources, offsets, inv) = match group {
            Some(group) => (
                [
                    &frame.data[..],
                    &group.members[0].data[..],
                    &group.members[1].data[..],
                    &group.members[2].data[..],
                ],
                group.offsets,
                group.gains.map(|g| (1.0 / g) as f32),
            ),
            None => ([&frame.data[..]; 4], [(0, 0); 4], [1.0; 4]),
        };
        Self {
            sources,
            offsets,
            inv,
            single: group.is_none(),
            stride: frame.stride as isize,
            bh: frame.buffer_height as isize,
            origin: (frame.active.x as isize, frame.active.y as isize),
            size: (frame.active.width as isize, frame.active.height as isize),
            black: frame.levels.black,
        }
    }

    fn at(&self, j: usize, x: isize, y: isize) -> f32 {
        let (ox, oy) = self.offsets[j];
        let bx = (self.origin.0 + x + ox).clamp(0, self.stride - 1);
        let by = (self.origin.1 + y + oy).clamp(0, self.bh - 1);
        (f32::from(self.sources[j][(by * self.stride + bx) as usize]) - self.black) * self.inv[j]
    }

    /// Colour `c` (0 red, 1 green, 2 blue) at photosite `(x, y)`.
    fn sample(&self, c: usize, x: isize, y: isize) -> f32 {
        let x = x.clamp(0, self.size.0 - 1);
        let y = y.clamp(0, self.size.1 - 1);
        if self.single {
            let own = strehl_core::pixel_shift::cfa_colour(x, y);
            if own == c {
                return self.at(0, x, y);
            }
            let near: &[(isize, isize)] = match (c, own) {
                // Green at a red or blue photosite: its four edge neighbours.
                (1, _) => &[(-1, 0), (1, 0), (0, -1), (0, 1)],
                // Red at blue or blue at red: the four diagonals.
                (_, 0 | 2) => &[(-1, -1), (1, -1), (-1, 1), (1, 1)],
                // Red or blue at a green photosite: the row's or the column's.
                _ => {
                    if strehl_core::pixel_shift::cfa_colour(x + 1, y) == c {
                        &[(-1, 0), (1, 0)]
                    } else {
                        &[(0, -1), (0, 1)]
                    }
                }
            };
            let sum: f32 = near
                .iter()
                .map(|&(dx, dy)| self.at(0, x + dx, y + dy))
                .sum();
            return sum / near.len() as f32;
        }
        let sm = strehl_core::pixel_shift::site_members(&self.offsets, x, y);
        match c {
            0 => self.at(sm[0], x, y),
            2 => self.at(sm[3], x, y),
            _ => (self.at(sm[1], x, y) + self.at(sm[2], x, y)) * 0.5,
        }
    }

    /// Colour `c` at a fractional photosite, Catmull-Rom.
    fn interpolate(&self, c: usize, x: f64, y: f64) -> f32 {
        let (x0, y0) = (x.floor(), y.floor());
        let wx = cr(x - x0);
        let wy = cr(y - y0);
        let (x0, y0) = (x0 as isize, y0 as isize);
        let mut acc = 0.0f32;
        for (j, wyj) in wy.iter().enumerate() {
            let mut row = 0.0f32;
            for (i, wxi) in wx.iter().enumerate() {
                row += self.sample(c, x0 - 1 + i as isize, y0 - 1 + j as isize) * wxi;
            }
            acc += row * wyj;
        }
        acc
    }

    fn inside(&self, x: f64, y: f64, margin: f64) -> bool {
        x >= margin
            && y >= margin
            && x <= self.size.0 as f64 - 1.0 - margin
            && y <= self.size.1 as f64 - 1.0 - margin
    }
}

fn cr(f: f64) -> [f32; 4] {
    let f = f as f32;
    let (f2, f3) = (f * f, f * f * f);
    [
        -0.5 * f3 + f2 - 0.5 * f,
        1.5 * f3 - 2.5 * f2 + 1.0,
        -1.5 * f3 + 2.0 * f2 + 0.5 * f,
        0.5 * f3 - 0.5 * f2,
    ]
}

/// The map from a base photosite to the companion photosite that sees the
/// same scene point, for one colour's lateral-colour transform.
#[derive(Clone, Copy)]
struct PointMap {
    m: Similarity,
    centre: (f64, f64),
}

impl PointMap {
    fn new(base: Similarity, companion: Similarity, centre: (f64, f64)) -> Option<Self> {
        Some(Self {
            m: base.invert()?.then(companion),
            centre,
        })
    }

    fn apply(&self, x: f64, y: f64) -> (f64, f64) {
        let (sx, sy) = self
            .m
            .apply_at(x * 0.5, y * 0.5, self.centre.0, self.centre.1);
        (2.0 * sx, 2.0 * sy)
    }
}

// ---------------------------------------------------------------------------
// the shift and the ratio
// ---------------------------------------------------------------------------

/// Member 1 of the companion against member 1 of its plane's base group, on
/// block luma as member offsets are measured (`pixel_shift::register`),
/// both clipped at 0.6 of the pin and the companion scaled by `k`, so the
/// pinned parts of the base cannot steer it: photosites, the companion's
/// position of the scene point base `(x, y)` sees is `(x + d.x, y + d.y)`.
fn measure_shift(
    anchor: &strehl_raw::Frame,
    companion: &strehl_raw::Frame,
    k: f64,
) -> std::result::Result<[f64; 2], String> {
    if anchor.stride != companion.stride
        || anchor.buffer_height != companion.buffer_height
        || anchor.active != companion.active
    {
        return Err("the companion's geometry differs from its plane's base group".into());
    }
    let black = anchor.levels.black;
    let full = f32::from(CONTAINER_MAX_DN) - black;
    let cap = (black + 0.6 * full) as u16;
    let a: Vec<u16> = anchor.data.par_iter().map(|&v| v.min(cap)).collect();
    let kf = k as f32;
    let c: Vec<u16> = companion
        .data
        .par_iter()
        .map(|&v| ((f32::from(v) - black) * kf + black).clamp(0.0, f32::from(cap)) as u16)
        .collect();
    fn view<'a>(
        data: &'a [u16],
        f: &strehl_raw::Frame,
    ) -> strehl_core::pixel_shift::MemberView<'a> {
        strehl_core::pixel_shift::MemberView {
            data,
            stride: f.stride,
            buffer_height: f.buffer_height,
            active: [f.active.x, f.active.y, f.active.width, f.active.height],
            black: f.levels.black,
            white: f.levels.white,
        }
    }
    let fit = strehl_core::pixel_shift::register(&view(&a, anchor), &view(&c, companion), 2, 2);
    if !(fit.structure > 0.8) {
        return Err(format!(
            "its shift against the base group is unmeasurable (structure {:.2}, offset {:?}, \
             remainder {:.2?} px, flux ratio {:.3})",
            fit.structure, fit.offset, fit.residual, fit.gain
        ));
    }
    Ok([
        fit.offset.0 as f64 + fit.residual[0],
        fit.offset.1 as f64 + fit.residual[1],
    ])
}

/// The measured exposure ratio of one base frame and its companion.
#[derive(Clone, Debug)]
struct PairFit {
    /// Base units per companion unit.
    k: f64,
    /// Where the fit started (commanded, planted), and whether it was
    /// commanded at all.
    start: f64,
    commanded: bool,
    /// The correction the fit applied, EV (positive: the companion was
    /// brighter than the start says).
    correction_ev: f64,
    patches: (usize, usize, usize),
    validation: [f32; 3],
    /// Scaled companion over base, green, where the base is at 0.50-0.75 of
    /// the pin and nothing near is brighter: median, robust spread, sites.
    handover: Option<(f64, f64, usize)>,
}

fn percentile(values: &[f32], fraction: f32) -> f32 {
    let mut sorted = values.to_vec();
    sorted.sort_by(f32::total_cmp);
    let position = fraction * (sorted.len() - 1) as f32;
    let low = position.floor() as usize;
    let high = position.ceil() as usize;
    sorted[low] + (sorted[high] - sorted[low]) * (position - low as f32)
}

fn trimmed_mean(values: &[f32]) -> Option<f32> {
    if values.is_empty() || values.iter().any(|v| !v.is_finite()) {
        return None;
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f32::total_cmp);
    let trim = sorted.len() / 10;
    let kept = &sorted[trim..sorted.len() - trim];
    Some(kept.iter().sum::<f32>() / kept.len() as f32)
}

/// CfaPlane order `R, G1, B, G2`: each plane's colour and photosite in the quad.
const PLANES: [(CfaPlane, usize, (usize, usize)); 4] = [
    (CfaPlane::R, 0, (0, 0)),
    (CfaPlane::G1, 1, (1, 0)),
    (CfaPlane::B, 2, (1, 1)),
    (CfaPlane::G2, 1, (0, 1)),
];

#[allow(clippy::too_many_arguments)]
fn fit_pair(
    base: &Assembled<'_>,
    companion: &Assembled<'_>,
    bright: &Bright,
    maps: &[PointMap; 3],
    noise: &NoiseModel,
    start: f64,
    commanded: bool,
    black: f32,
    full: f32,
) -> std::result::Result<PairFit, String> {
    let ceiling = (black + FIT_CEILING * full) as u16;
    let lo = (black + RAMP_LO * full) as u16;
    let (w, h) = (bright.w, bright.h);
    let margin = 128usize;
    // Candidate patches: unclipped and below the ramp everywhere, their
    // companion inside its frame, the companion's expected green well above
    // its noise.
    let mut candidates: Vec<(usize, usize)> = Vec::new();
    let mut y0 = margin;
    while y0 + PATCH + margin <= h {
        let mut x0 = margin;
        while x0 + PATCH + margin <= w {
            candidates.push((x0, y0));
            x0 += PATCH;
        }
        y0 += PATCH;
    }
    let kept: Vec<(usize, usize)> = candidates
        .into_par_iter()
        .filter(|&(x0, y0)| {
            let (x0i, y0i) = (x0 as isize, y0 as isize);
            let (x1, y1) = (x0i + PATCH as isize - 1, y0i + PATCH as isize - 1);
            if bright.max(x0i, y0i, x1, y1, false) >= ceiling
                && bright.max(x0i, y0i, x1, y1, true) >= ceiling
            {
                return false;
            }
            for (cx, cy) in [(x0i, y0i), (x1, y0i), (x0i, y1), (x1, y1)] {
                for m in maps {
                    let (u, v) = m.apply(cx as f64, cy as f64);
                    if !companion.inside(u, v, 4.0) {
                        return false;
                    }
                }
            }
            // The dimmest colour's mean, as the companion would read it.
            let mut sum = [0.0f32; 3];
            let mut n = 0.0f32;
            for y in (y0i..=y1).step_by(8) {
                for x in (x0i..=x1).step_by(8) {
                    for (c, s) in sum.iter_mut().enumerate() {
                        *s += base.sample(c, x, y);
                    }
                    n += 1.0;
                }
            }
            let dimmest = sum.iter().copied().fold(f32::INFINITY, f32::min) / n;
            let c = (dimmest / start as f32).max(0.0);
            c > 1.5 * SIGNAL_SIGMA * noise.variance(CfaPlane::G1, c).sqrt()
        })
        .collect();
    if kept.len() < MIN_FIT + MIN_VALIDATION {
        return Err(format!(
            "only {} patches are well exposed in both groups (need {})",
            kept.len(),
            MIN_FIT + MIN_VALIDATION
        ));
    }
    let chosen: Vec<(usize, usize)> = if kept.len() > MAX_PATCHES {
        (0..MAX_PATCHES)
            .map(|i| kept[i * kept.len() / MAX_PATCHES])
            .collect()
    } else {
        kept
    };
    // Each patch's [R, G1, B, G2] values: the base's own, and the
    // companion's at the same scene points.
    type Values = [Vec<f32>; 4];
    let sampled: Vec<(Values, Values)> = chosen
        .par_iter()
        .map(|&(x0, y0)| {
            let mut a: Values = Default::default();
            let mut b: Values = Default::default();
            for qy in 0..PATCH / 2 {
                for qx in 0..PATCH / 2 {
                    for (p, &(_, c, (dx, dy))) in PLANES.iter().enumerate() {
                        let x = (x0 + 2 * qx + dx) as isize;
                        let y = (y0 + 2 * qy + dy) as isize;
                        a[p].push(base.sample(c, x, y));
                        let (u, v) = maps[c].apply(x as f64, y as f64);
                        b[p].push(companion.interpolate(c, u, v));
                    }
                }
            }
            (a, b)
        })
        .collect();
    let mut fit = Vec::new();
    let mut ratios: Vec<Option<[f32; 4]>> = Vec::with_capacity(sampled.len());
    let (mut fit_patches, mut validation_patches) = (0usize, 0usize);
    let start32 = start as f32;
    for (i, (a, b)) in sampled.iter().enumerate() {
        let mut r = [0.0f32; 4];
        let mut ok = true;
        for (p, &(plane, _, _)) in PLANES.iter().enumerate() {
            let (Some(ma), Some(mb)) = (trimmed_mean(&a[p]), trimmed_mean(&b[p])) else {
                ok = false;
                break;
            };
            let (va, vb) = (noise.variance(plane, ma), noise.variance(plane, mb));
            if !(ma > SIGNAL_SIGMA * va.sqrt()) || !(mb > SIGNAL_SIGMA * vb.sqrt()) {
                ok = false;
                break;
            }
            r[p] = ((mb * start32) / ma).ln();
            if !r[p].is_finite() {
                ok = false;
                break;
            }
        }
        if !ok {
            ratios.push(None);
            continue;
        }
        if i % 2 == 1 {
            validation_patches += 1;
        } else {
            fit.extend(r);
            fit_patches += 1;
        }
        ratios.push(Some(r));
    }
    if fit_patches < MIN_FIT || validation_patches < MIN_VALIDATION {
        return Err(format!(
            "only {fit_patches} fit and {validation_patches} validation patches have four-colour \
             signal in both groups"
        ));
    }
    let fitted = percentile(&fit, 0.5);
    let correction_ev = -fitted / std::f32::consts::LN_2;
    if fitted.abs() / std::f32::consts::LN_2 > CORRECTION_LIMIT_EV {
        return Err(format!(
            "the measured ratio is {:.3} against a start of {start:.3}: a correction of \
             {correction_ev:+.3} EV, beyond the {CORRECTION_LIMIT_EV} EV bound",
            start / f64::from(fitted).exp()
        ));
    }
    let residuals: Vec<f32> = ratios
        .iter()
        .enumerate()
        .filter(|(i, _)| i % 2 == 1)
        .filter_map(|(_, r)| *r)
        .flatten()
        .map(|r| ((r - fitted).exp() - 1.0).abs())
        .collect();
    let validation = [
        percentile(&residuals, 0.5),
        percentile(&residuals, 0.95),
        residuals.iter().copied().fold(0.0, f32::max),
    ];
    if !(validation[0] <= MEDIAN_LIMIT && validation[1] <= P95_LIMIT && validation[2] <= MAX_LIMIT)
    {
        return Err(format!(
            "held-out patches disagree with one ratio (median {:.2} %, p95 {:.2} %, max {:.2} %)",
            100.0 * validation[0],
            100.0 * validation[1],
            100.0 * validation[2]
        ));
    }
    // Textured agreement, as the session checks it.
    let gain_b = start32 / fitted.exp();
    let mut textured = 0usize;
    let mut worst_all = 0.0f32;
    for ((a, b), r) in sampled.iter().zip(&ratios) {
        if r.is_none() {
            continue;
        }
        let mut is_textured = false;
        let mut worst = 0.0f32;
        for (p, &(plane, _, _)) in PLANES.iter().enumerate() {
            let (x, y) = (&a[p], &b[p]);
            let n = x.len() as f32;
            let mx = x.iter().sum::<f32>() / n;
            let my = y.iter().sum::<f32>() / n;
            let (mut tx, mut ty, mut difference, mut variance) = (0.0f32, 0.0, 0.0, 0.0);
            for (&x, &y) in x.iter().zip(y) {
                let dx = x - mx;
                let dy = (y - my) * gain_b;
                tx += dx * dx;
                ty += dy * dy;
                difference += (dx - dy) * (dx - dy);
                variance += noise.variance(plane, x) + noise.variance(plane, y) * gain_b * gain_b;
            }
            tx /= n;
            ty /= n;
            difference /= n;
            variance = variance / n * NOISE_ALLOWANCE;
            if tx.min(ty) > 16.0 * variance {
                is_textured = true;
                worst = worst.max((difference - variance).max(0.0) / tx.max(ty));
            }
        }
        if is_textured {
            textured += 1;
            worst_all = worst_all.max(worst);
        }
    }
    if worst_all > TEXTURE_LIMIT {
        return Err(format!(
            "textured patches disagree after the ratio (worst residual {worst_all:.3} of the \
             texture's power): focus, motion or placement"
        ));
    }
    if textured < MIN_TEXTURED {
        return Err(format!(
            "only {textured} textured patches can confirm the groups see the same detail \
             (need {MIN_TEXTURED})"
        ));
    }
    let k = f64::from(gain_b);
    // The hand-over: where the base is high but below the ramp, the scaled
    // companion must read what the base reads.
    let (b_lo, b_hi) = (0.50 * full, RAMP_LO * full);
    let rows: Vec<Vec<f32>> = (8..h.saturating_sub(8))
        .step_by(3)
        .collect::<Vec<_>>()
        .into_par_iter()
        .map(|y| {
            let mut out = Vec::new();
            let yi = y as isize;
            for x in (8..w.saturating_sub(8)).step_by(3) {
                let xi = x as isize;
                if bright.b[y * w + x] < (black + b_lo) as u16 {
                    continue;
                }
                let g = base.sample(1, xi, yi);
                if !(g >= b_lo && g < b_hi) {
                    continue;
                }
                if bright.max(xi - 4, yi - 4, xi + 4, yi + 4, false) >= lo
                    && bright.max(xi - 4, yi - 4, xi + 4, yi + 4, true) >= lo
                {
                    continue;
                }
                let (u, v) = maps[1].apply(x as f64, y as f64);
                if !companion.inside(u, v, 4.0) {
                    continue;
                }
                out.push((k * f64::from(companion.interpolate(1, u, v)) / f64::from(g)) as f32);
            }
            out
        })
        .collect();
    let handover: Vec<f32> = rows.into_iter().flatten().collect();
    let handover = (handover.len() >= 50).then(|| {
        let q = |p| f64::from(percentile(&handover, p));
        (q(0.5), 0.7413 * (q(0.75) - q(0.25)), handover.len())
    });
    Ok(PairFit {
        k,
        start,
        commanded,
        correction_ev: f64::from(correction_ev),
        patches: (fit_patches, validation_patches, textured),
        validation,
        handover,
    })
}

/// A rough ratio from the data, for a companion whose exposure the journal
/// does not record: the median base over companion green where both are
/// well exposed, at the same photosite (the shift is a fraction of one).
fn data_ratio(base: &Assembled<'_>, companion: &Assembled<'_>, full: f32) -> Option<f64> {
    let (w, h) = base.size;
    let mut r: Vec<f32> = Vec::new();
    for y in (64..h - 64).step_by(37) {
        for x in (64..w - 64).step_by(41) {
            let (a, b) = (base.sample(1, x, y), companion.sample(1, x, y));
            if a > 0.1 * full && a < 0.6 * full && b > 20.0 {
                r.push(a / b);
            }
        }
    }
    (r.len() >= 100).then(|| f64::from(percentile(&r, 0.5)))
}

// ---------------------------------------------------------------------------
// one frame's patches
// ---------------------------------------------------------------------------

/// One replaced site of a gathered plane: `plane = plane * (1 - w) + v * w`.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Patch {
    /// The plane's index in the fold (0-3 the CFA sites, 4-11 carried).
    pub plane: u32,
    /// Index in the analysis plane.
    pub index: u32,
    pub w: f32,
    pub v: f32,
}

/// One luma pixel whose greens were replaced: weights of planes 1 and 2.
#[derive(Clone, Copy, Debug)]
pub(crate) struct LumaPatch {
    pub index: u32,
    pub w1: f32,
    pub w2: f32,
}

/// A frame's replaced sites (the sparse per-frame list of plan X4).
#[derive(Clone, Debug, Default)]
pub(crate) struct FramePatches {
    pub sites: Vec<Patch>,
    pub luma: Vec<LumaPatch>,
    /// Base units per companion unit.
    pub ratio: f32,
}

impl FramePatches {
    /// Apply to the gathered planes (black-subtracted, analysis grid).
    pub(crate) fn apply_planes(&self, planes: &mut [Vec<f32>]) {
        for p in &self.sites {
            if let Some(plane) = planes.get_mut(p.plane as usize) {
                let x = &mut plane[p.index as usize];
                let keep = 1.0 - p.w;
                *x = *x * keep + p.v * p.w;
            }
        }
    }

    /// Replace the luma variance at the patched pixels: per green, the
    /// injected model on the base sample and, times the ratio squared, on
    /// the companion's (the luma over the ratio), blended by the weight
    /// squared. The same expression as the GPU's `patch_variance`.
    pub(crate) fn apply_variance(&self, luma: &[f32], var: &mut [f32], noise: &NoiseModel) {
        let (g1, g2) = (noise.plane(CfaPlane::G1), noise.plane(CfaPlane::G2));
        let model = [
            g1.gain_dn_per_e,
            g1.read_noise_e * g1.gain_dn_per_e,
            g2.gain_dn_per_e,
            g2.read_noise_e * g2.gain_dn_per_e,
        ];
        let k = self.ratio;
        let ik = 1.0 / k;
        for p in &self.luma {
            let i = p.index as usize;
            var[i] = fused_variance(luma[i], p.w1, p.w2, model, k, ik);
        }
    }
}

/// See [`FramePatches::apply_variance`]; `model` is gain and read noise (DN)
/// of the two greens.
pub(crate) fn fused_variance(l: f32, w1: f32, w2: f32, model: [f32; 4], k: f32, ik: f32) -> f32 {
    let s = l.max(0.0);
    let c = s * ik;
    let kk = k * k;
    let base1 = model[0] * s + model[1] * model[1];
    let comp1 = model[0] * c + model[1] * model[1];
    let base2 = model[2] * s + model[3] * model[3];
    let comp2 = model[2] * c + model[3] * model[3];
    let keep1 = 1.0 - w1;
    let keep2 = 1.0 - w2;
    let v1 = keep1 * keep1 * base1 + w1 * w1 * (kk * comp1);
    let v2 = keep2 * keep2 * base2 + w2 * w2 * (kk * comp2);
    0.25 * (v1 + v2)
}

/// The base frame `path`'s companion in this render, if it has one: a cheap
/// test for a consumer.
pub(crate) fn companion_of(path: &Path) -> Option<Arc<CompanionRef>> {
    table()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .get(path)
        .cloned()
}

/// What [`plan`] needs of the consumer.
pub(crate) struct Inputs<'a> {
    /// Member 1 of the base group, before the gather writes it.
    pub frame: &'a strehl_raw::Frame,
    /// Its checked group's other members; `None` when the group was demoted
    /// and the frame is folded as member 1 alone.
    pub group: Option<&'a MeasuredGroup>,
    /// The base frame's placement, as its gather uses it.
    pub t: Similarity,
    /// Another frame's placement, as its gather would use it.
    pub placement: &'a dyn Fn(usize) -> Option<Similarity>,
    pub full: PlaneGeometry,
    /// The analysis rectangle: x, y, width, height.
    pub rect: [usize; 4],
    /// Only these gather bands are consumed (`WarpScratch::bands`).
    pub bands: Option<&'a [bool]>,
    /// The fold carries the eight non-native channels too.
    pub carry: bool,
}

/// A frame's replaced sites, or `None` when it has no companion or the
/// companion cannot be used (said once in the log, and the frame is its base
/// exposure alone).
pub(crate) fn plan(i: Inputs<'_>) -> Result<Option<FramePatches>> {
    let Some(r) = companion_of(&i.frame.path) else {
        return Ok(None);
    };
    let started = std::time::Instant::now();
    match plan_impl(&i, &r) {
        Ok((patches, record)) => {
            note_fused(&r, record, started.elapsed().as_secs_f64());
            Ok(Some(patches))
        }
        // A partial consumer without the fold's measurements: silently the
        // base exposure (the fold's account stands).
        Err(Refusal(why)) if why.is_empty() => Ok(None),
        Err(Refusal(why)) => {
            note_refused(&r, why);
            Ok(None)
        }
    }
}

struct Refusal(String);

impl<E: std::fmt::Display> From<E> for Refusal {
    fn from(e: E) -> Self {
        Refusal(format!("{e:#}"))
    }
}

/// What one fused frame reports.
#[derive(Clone, Debug, Default)]
struct Record {
    k: f64,
    fit: Option<PairFit>,
    shift: [f64; 2],
    sites: usize,
    replaced: usize,
    pinned: usize,
    pinned_unreplaced: usize,
    companion_pinned: usize,
    /// Seconds per step: load, shift, bright map, ratio, sites, gather.
    steps: [f64; 6],
    /// The base group, or the companion group, was demoted and is used as
    /// its member 1 alone.
    base_member1: bool,
    companion_member1: Option<String>,
    /// Planned for a consumer of a few bands (counts cover only those).
    partial: bool,
}

/// A companion's member 1 and group.
type Frames = (strehl_raw::Frame, Option<MeasuredGroup>);

/// A companion's frames taken out of their [`Loaded`] for one frame's use
/// and put back when dropped (unless another copy went back first).
struct Checkout<'a> {
    home: &'a Mutex<Option<Frames>>,
    item: Option<Frames>,
}

impl<'a> Checkout<'a> {
    fn take(
        home: &'a Mutex<Option<Frames>>,
        r: &CompanionRef,
    ) -> std::result::Result<Self, Refusal> {
        let held = home.lock().unwrap_or_else(|e| e.into_inner()).take();
        let item = match held {
            Some(item) => item,
            // In use by another frame now: a copy of its own.
            None => decode_companion(r)?
                .frames
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .take()
                .ok_or_else(|| Refusal("the companion's frames could not be read".into()))?,
        };
        Ok(Self {
            home,
            item: Some(item),
        })
    }
}

impl Drop for Checkout<'_> {
    fn drop(&mut self) {
        if let Some(item) = self.item.take() {
            let mut home = self.home.lock().unwrap_or_else(|e| e.into_inner());
            if home.is_none() {
                *home = Some(item);
            }
        }
    }
}

fn pair_fits() -> &'static Mutex<HashMap<String, Measured<PairFit>>> {
    static FITS: std::sync::OnceLock<Mutex<HashMap<String, Measured<PairFit>>>> =
        std::sync::OnceLock::new();
    FITS.get_or_init(Default::default)
}

fn companion_scratch() -> &'static Mutex<Option<WarpScratch>> {
    static SCRATCH: std::sync::OnceLock<Mutex<Option<WarpScratch>>> = std::sync::OnceLock::new();
    SCRATCH.get_or_init(Default::default)
}

fn bits(t: Similarity) -> String {
    format!(
        "{:x}.{:x}.{:x}.{:x}",
        t.a.re.to_bits(),
        t.a.im.to_bits(),
        t.b.re.to_bits(),
        t.b.im.to_bits()
    )
}

fn channel_of(ci: usize) -> Channel {
    match ci {
        0 => Channel::Red,
        2 => Channel::Blue,
        _ => Channel::Green,
    }
}

fn plan_impl(
    i: &Inputs<'_>,
    r: &CompanionRef,
) -> std::result::Result<(FramePatches, Record), Refusal> {
    let frame = i.frame;
    let mut clock = std::time::Instant::now();
    let mut steps = [0.0f64; 6];
    let mut lap = |k: usize| {
        steps[k] = clock.elapsed().as_secs_f64();
        clock = std::time::Instant::now();
    };
    let l = load(r)?;
    load_next(r);
    lap(0);
    let black = frame.levels.black;
    let full = f32::from(CONTAINER_MAX_DN) - black;
    let (gw, gh) = (i.full.width, i.full.height);
    let centre = (gw as f64 * 0.5, gh as f64 * 0.5);
    // The companion's placement: its own plane's, plus its measured shift.
    let t_anchor = if r.companion_plane == r.plane {
        i.t
    } else {
        let q = r.anchor_index.ok_or_else(|| {
            Refusal(format!(
                "plane {}'s base group is not in this stack",
                r.companion_plane
            ))
        })?;
        (i.placement)(q).ok_or_else(|| {
            Refusal(format!(
                "plane {}'s base group has no placement",
                r.companion_plane
            ))
        })?
    };
    let ident = strehl_raw::identity_cached(&frame.path);
    let ca: Option<&OpticalProfile> =
        strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
    // The companion's frames, checked out (no lock is held across the
    // parallel work below; see [`Slot`]): another frame using them now gets
    // its own copy.
    let mut out = Checkout::take(&l.frames, r)?;
    let (cm1, cgroup) = out.item.as_mut().expect("checked out");
    if cm1.levels != frame.levels
        || cm1.active != frame.active
        || cm1.stride != frame.stride
        || cm1.buffer_height != frame.buffer_height
    {
        return Err(Refusal(
            "its highlight group's geometry or levels differ from the base group's".into(),
        ));
    }
    let base = Assembled::new(frame, i.group);
    let start_data = {
        let comp = Assembled::new(cm1, cgroup.as_ref());
        data_ratio(&base, &comp, full)
    };
    let (start, commanded) = match (r.nominal, start_data) {
        (Some(n), _) => (n * r.plant, true),
        (None, Some(d)) => (d * r.plant, false),
        (None, None) => {
            return Err(Refusal(
                "no commanded exposure and too few well-exposed sites to start a ratio".into(),
            ));
        }
    };
    // The shift, once per companion (against its own plane's base member 1).
    // A consumer of a few bands decodes only their rows (the restoration's
    // reference crops): the shift and the ratio need the whole frame, so it
    // uses what the fold measured, and without that leaves the frame alone.
    let partial = i.bands.is_some();
    let known = shifts()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .get(&r.key)
        .cloned();
    let shift = match known {
        Some(s) => s,
        None if partial => return Err(Refusal(String::new())),
        None => {
            // Scaled by the data's own ratio where it has one: a scale error
            // reads as residual noise and hides the structure.
            let scale = start_data.unwrap_or(start);
            let measured = if r.companion_plane == r.plane {
                measure_shift(frame, cm1, scale)
            } else {
                match strehl_raw::decode(&r.anchor_m1) {
                    Ok(a) => measure_shift(&a, cm1, scale),
                    Err(e) => Err(format!(
                        "its plane's base member 1 could not be read: {e:#}"
                    )),
                }
            };
            shifts()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .insert(r.key.clone(), measured.clone());
            measured
        }
    }
    .map_err(Refusal)?;
    let t_c = Similarity {
        a: t_anchor.a,
        b: t_anchor.b + Cx::new(0.5 * shift[0], 0.5 * shift[1]),
    };
    lap(1);
    let bright = Bright::new(frame, i.group);
    lap(2);
    // The ratio, once per pair and placement.
    let fit_key = format!(
        "{}|{}|{}|{}|{}",
        frame.path.display(),
        r.key,
        bits(i.t),
        bits(t_c),
        start.to_bits()
    );
    let known = pair_fits()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .get(&fit_key)
        .cloned();
    let fit = match known {
        Some(f) => f,
        None if partial => return Err(Refusal(String::new())),
        None => {
            let maps: Option<Vec<PointMap>> = [Channel::Red, Channel::Green, Channel::Blue]
                .into_iter()
                .map(|ch| {
                    PointMap::new(
                        OpticalProfile::compose(ca, ch, i.t),
                        OpticalProfile::compose(ca, ch, t_c),
                        centre,
                    )
                })
                .collect();
            let maps: [PointMap; 3] = maps
                .and_then(|m| m.try_into().ok())
                .ok_or_else(|| Refusal("a singular placement".into()))?;
            let noise = strehl_core::profile::noise_model_for(
                &frame.camera,
                frame.iso,
                strehl_core::noise::Levels {
                    black,
                    white: frame.levels.white,
                },
            );
            let comp = Assembled::new(cm1, cgroup.as_ref());
            let f = fit_pair(
                &base, &comp, &bright, &maps, &noise, start, commanded, black, full,
            );
            pair_fits()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .insert(fit_key, f.clone());
            f
        }
    }
    .map_err(|why| Refusal(format!("its exposure ratio was refused: {why}")))?;
    let k = fit.k;
    lap(3);

    // Where: every site of the analysis planes whose footprint, with the
    // guard, reaches the ramp.
    let lo = (black + RAMP_LO * full) as u16;
    let pin = CONTAINER_MAX_DN - 2;
    let sites: Vec<(usize, usize, usize)> = [(0, 0), (1, 0), (0, 1), (1, 1)]
        .into_iter()
        .map(|(dx, dy)| (dx, dy, crate::align_cmd::rggb_channel_index(dx, dy)))
        .chain(CARRIED_SITES.iter().copied().filter(|_| i.carry))
        .collect();
    let transforms: Vec<Similarity> = sites
        .iter()
        .map(|&(_, _, ci)| OpticalProfile::compose(ca, channel_of(ci), i.t))
        .collect();
    let [rx, ry, lw, lh] = i.rect;
    let only = i.bands;
    // A lone (demoted) frame is demosaiced before the pull: its 5 x 5
    // stencil reaches two photosites beyond the pull's taps.
    let reach: isize = if i.group.is_some() { 0 } else { 2 };
    let widen = GUARD + reach;
    // (site, analysis index, full quad index, weight, base footprint pinned)
    type Candidate = (u32, u32, u32, f32, bool);
    let candidates: Vec<Candidate> = (0..lh)
        .into_par_iter()
        .filter(|&ly| {
            only.is_none_or(|b| {
                b.get((ry + ly) / crate::align_cmd::BAND_ROWS)
                    .copied()
                    .unwrap_or(false)
            })
        })
        .flat_map_iter(|ly| {
            let py = ry + ly;
            let mut out: Vec<Candidate> = Vec::new();
            const BLOCK: usize = 32;
            for (s, (&(dx, dy, _), t)) in sites.iter().zip(&transforms).enumerate() {
                let (ox, oy) = (dx as f64 * 0.5, dy as f64 * 0.5);
                for b0 in (0..lw).step_by(BLOCK) {
                    let b1 = (b0 + BLOCK).min(lw);
                    // The block's pulls lie between its two ends' (the map is
                    // affine): skip it when no tile they can reach is bright.
                    let ends = [b0, b1 - 1].map(|lx| {
                        t.apply_at((rx + lx) as f64 + ox, py as f64 + oy, centre.0, centre.1)
                    });
                    let (xa, xb) = (
                        2.0 * ends[0].0.min(ends[1].0),
                        2.0 * ends[0].0.max(ends[1].0),
                    );
                    let (ya, yb) = (
                        2.0 * ends[0].1.min(ends[1].1),
                        2.0 * ends[0].1.max(ends[1].1),
                    );
                    if xa.is_finite()
                        && xb.is_finite()
                        && ya.is_finite()
                        && yb.is_finite()
                        && bright.max(
                            xa.floor() as isize - 2 - widen,
                            ya.floor() as isize - 2 - widen,
                            xb.floor() as isize + 3 + widen,
                            yb.floor() as isize + 3 + widen,
                            false,
                        ) < lo
                    {
                        continue;
                    }
                    for lx in b0..b1 {
                        let px = rx + lx;
                        let (sx, sy) =
                            t.apply_at(px as f64 + ox, py as f64 + oy, centre.0, centre.1);
                        let (x, y) = (2.0 * sx, 2.0 * sy);
                        if !(x.is_finite() && y.is_finite()) {
                            continue;
                        }
                        let (fx, fy) = (x.floor() as isize, y.floor() as isize);
                        let (x0, y0, x1, y1) = (
                            fx - 1 - widen,
                            fy - 1 - widen,
                            fx + 2 + widen,
                            fy + 2 + widen,
                        );
                        if bright.max(x0, y0, x1, y1, false) < lo {
                            continue;
                        }
                        let m = bright.max(x0, y0, x1, y1, true);
                        if m < lo {
                            continue;
                        }
                        let w = ramp(m, black, full);
                        if w <= 0.0 {
                            continue;
                        }
                        let pinned = bright.max(
                            fx - 1 - reach,
                            fy - 1 - reach,
                            fx + 2 + reach,
                            fy + 2 + reach,
                            true,
                        ) >= pin;
                        out.push((
                            s as u32,
                            (ly * lw + lx) as u32,
                            (py * gw + px) as u32,
                            w,
                            pinned,
                        ));
                    }
                }
            }
            out
        })
        .collect();
    lap(4);
    let mut record = Record {
        k,
        fit: Some(fit.clone()),
        shift,
        pinned: candidates.iter().filter(|c| c.4).count(),
        base_member1: i.group.is_none(),
        companion_member1: l.gate.clone(),
        partial,
        ..Default::default()
    };
    if candidates.is_empty() {
        return Ok((
            FramePatches {
                sites: Vec::new(),
                luma: Vec::new(),
                ratio: k as f32,
            },
            record,
        ));
    }
    // The companion, gathered only over the bands and columns those sites
    // occupy, through its own placement.
    let bands_n = gh.div_ceil(crate::align_cmd::BAND_ROWS);
    let mut bands = vec![false; bands_n];
    let mut spans: Vec<Option<(usize, usize)>> = vec![None; bands_n];
    for c in &candidates {
        let (px, py) = (c.2 as usize % gw, c.2 as usize / gw);
        let b = py / crate::align_cmd::BAND_ROWS;
        bands[b] = true;
        spans[b] = Some(match spans[b] {
            None => (px, px + 1),
            Some((a, z)) => (a.min(px), z.max(px + 1)),
        });
    }
    let columns: Vec<Vec<(usize, usize)>> =
        spans.into_iter().map(|s| s.into_iter().collect()).collect();
    let mut by_site: Vec<Vec<usize>> = vec![Vec::new(); sites.len()];
    for (n, c) in candidates.iter().enumerate() {
        by_site[c.0 as usize].push(n);
    }
    let mut values: Vec<Option<f32>> = vec![None; candidates.len()];
    {
        // The gather's scratch, checked out as the frames are (a busy one
        // means a fresh one here).
        let mut scratch = companion_scratch()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .take()
            .unwrap_or_default();
        let (mut m1, group) = out.item.take().expect("checked out");
        let gathered = crate::align_cmd::gather_companion(
            &mut m1,
            group,
            t_c,
            i.full,
            &mut scratch,
            bands,
            columns,
            i.carry,
            |(dx, dy), dst, cover, inv| {
                let s = dy * 2 + dx;
                for &n in &by_site[s] {
                    let fi = candidates[n].2 as usize;
                    if cover[fi] {
                        values[n] = Some(dst[fi] * inv);
                    }
                }
            },
        );
        match gathered {
            Ok(group) => out.item = Some((m1, group)),
            Err(e) => return Err(Refusal(format!("its gather failed: {e:#}"))),
        }
        drop(out);
        let carried = if i.carry {
            let mut missing = false;
            for (k, list) in by_site.iter().enumerate().skip(4) {
                match scratch.carried.get(k - 4) {
                    Some(carried) => {
                        for &n in list {
                            values[n] = Some(carried[candidates[n].2 as usize]);
                        }
                    }
                    None => missing = true,
                }
            }
            !missing
        } else {
            true
        };
        let mut home = companion_scratch()
            .lock()
            .unwrap_or_else(|e| e.into_inner());
        if home.is_none() {
            *home = Some(scratch);
        }
        drop(home);
        if !carried {
            return Err(Refusal(
                "the companion's carried channels are missing".into(),
            ));
        }
    }
    lap(5);
    record.steps = steps;
    let k32 = k as f32;
    let companion_pin = 0.98 * full;
    let mut patches: Vec<Patch> = Vec::with_capacity(candidates.len());
    for (c, v) in candidates.iter().zip(&values) {
        match v {
            Some(v) => {
                if *v >= companion_pin {
                    record.companion_pinned += 1;
                }
                if c.3 >= 1.0 {
                    record.replaced += 1;
                }
                patches.push(Patch {
                    plane: c.0,
                    index: c.1,
                    w: c.3,
                    v: k32 * v,
                });
            }
            None => {
                if c.4 {
                    record.pinned_unreplaced += 1;
                }
            }
        }
    }
    record.pinned_unreplaced += candidates
        .iter()
        .zip(&values)
        .filter(|(c, v)| c.4 && v.is_some() && c.3 < 1.0)
        .count();
    patches.sort_by_key(|p| (p.index, p.plane));
    let mut luma: Vec<LumaPatch> = Vec::new();
    for p in patches.iter().filter(|p| p.plane == 1 || p.plane == 2) {
        match luma.last_mut() {
            Some(last) if last.index == p.index => {
                if p.plane == 1 {
                    last.w1 = p.w;
                } else {
                    last.w2 = p.w;
                }
            }
            _ => luma.push(LumaPatch {
                index: p.index,
                w1: if p.plane == 1 { p.w } else { 0.0 },
                w2: if p.plane == 2 { p.w } else { 0.0 },
            }),
        }
    }
    record.sites = patches.len();
    Ok((
        FramePatches {
            sites: patches,
            luma,
            ratio: k32,
        },
        record,
    ))
}

// ---------------------------------------------------------------------------
// the render's account
// ---------------------------------------------------------------------------

#[derive(Default)]
struct Stats {
    fused: BTreeMap<u64, Record>,
    refused: BTreeMap<u64, String>,
    seconds: f64,
}

fn stats() -> &'static Mutex<Stats> {
    static STATS: std::sync::OnceLock<Mutex<Stats>> = std::sync::OnceLock::new();
    STATS.get_or_init(Default::default)
}

fn note_fused(r: &CompanionRef, record: Record, seconds: f64) {
    if let Ok(path) = std::env::var(REPORT_ENV)
        && !path.trim().is_empty()
    {
        let f = record.fit.as_ref();
        let line = serde_json::json!({
            "plane": r.plane,
            "companion_plane": r.companion_plane,
            "ratio_start": f.map(|f| f.start),
            "commanded": f.map(|f| f.commanded),
            "ratio": record.k,
            "correction_ev": f.map(|f| f.correction_ev),
            "patches_fit_validation_textured": f.map(|f| [f.patches.0, f.patches.1, f.patches.2]),
            "validation_median_p95_max": f.map(|f| f.validation),
            "handover_median_spread_sites": f.and_then(|f| f.handover).map(|h| [h.0, h.1, h.2 as f64]),
            "shift_px": record.shift,
            "patched_sites": record.sites,
            "weight_one_sites": record.replaced,
            "base_pinned_sites": record.pinned,
            "pinned_not_fully_replaced": record.pinned_unreplaced,
            "companion_near_pin": record.companion_pinned,
            "seconds": seconds,
            "seconds_load_shift_bright_ratio_sites_gather": record.steps,
            "partial": record.partial,
            "base_member1_only": record.base_member1,
            "companion_member1_only": record.companion_member1,
        });
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path.trim())
        {
            use std::io::Write;
            let _ = writeln!(file, "{line}");
        }
    }
    let mut s = stats().lock().unwrap_or_else(|e| e.into_inner());
    s.seconds += seconds;
    s.refused.remove(&r.plane);
    // A whole frame's account is not replaced by a few bands'.
    if !(record.partial && s.fused.get(&r.plane).is_some_and(|f| !f.partial)) {
        s.fused.insert(r.plane, record);
    }
}

fn note_refused(r: &CompanionRef, why: String) {
    let mut s = stats().lock().unwrap_or_else(|e| e.into_inner());
    if !s.refused.contains_key(&r.plane) && !s.fused.contains_key(&r.plane) {
        eprintln!(
            "highlights      : plane {}: {why}; this plane is the base exposure alone",
            r.plane
        );
        if let Ok(path) = std::env::var(REPORT_ENV)
            && !path.trim().is_empty()
            && let Ok(mut file) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path.trim())
        {
            use std::io::Write;
            let _ = writeln!(
                file,
                "{}",
                serde_json::json!({"plane": r.plane, "companion_plane": r.companion_plane, "refused": why})
            );
        }
        s.refused.insert(r.plane, why);
    }
}

/// The render's summary line, when it had highlight companions.
pub(crate) fn summary() -> Option<String> {
    let s = stats().lock().unwrap_or_else(|e| e.into_inner());
    if s.fused.is_empty() && s.refused.is_empty() {
        return None;
    }
    let ks: Vec<f64> = s.fused.values().map(|r| r.k).collect();
    let sites: usize = s.fused.values().map(|r| r.sites).sum();
    let pinned: usize = s.fused.values().map(|r| r.pinned).sum();
    let unreplaced: usize = s.fused.values().map(|r| r.pinned_unreplaced).sum();
    let companion_pinned: usize = s.fused.values().map(|r| r.companion_pinned).sum();
    let lone = (
        s.fused.values().filter(|r| r.base_member1).count(),
        s.fused
            .values()
            .filter(|r| r.companion_member1.is_some())
            .count(),
    );
    let hand: Vec<f64> = s
        .fused
        .values()
        .filter_map(|r| r.fit.as_ref()?.handover.map(|h| h.0))
        .collect();
    let (kmin, kmax) = ks
        .iter()
        .fold((f64::INFINITY, f64::NEG_INFINITY), |(a, b), k| {
            (a.min(*k), b.max(*k))
        });
    Some(format!(
        "highlights      : {} planes fused ({} of them a demoted base group's member 1, {} with a \
         demoted highlight group's member 1), {} the base exposure alone; ratio {:.3}-{:.3}; {sites} \
         sites replaced or blended ({pinned} with a pinned sample in their footprint, {unreplaced} \
         of those not fully replaced; {companion_pinned} near the companion's own pin); hand-over \
         {}; {:.1} s",
        s.fused.len(),
        lone.0,
        lone.1,
        s.refused.len(),
        kmin,
        kmax,
        if hand.is_empty() {
            "not measured".to_string()
        } else {
            let mut h = hand.clone();
            h.sort_by(f64::total_cmp);
            format!(
                "median {:.4} (planes {:.4}-{:.4})",
                h[h.len() / 2],
                h[0],
                h[h.len() - 1]
            )
        },
        s.seconds
    ))
}

/// The writer's headroom: the fused data's ceiling over the base exposure's,
/// the smallest ratio of the frames that replaced sites (a site is
/// neutralised only where the companion is pinned too). `None` without
/// fused sites: the writer is exactly as before.
pub(crate) fn ceiling_factor() -> Option<f32> {
    let s = stats().lock().unwrap_or_else(|e| e.into_inner());
    s.fused
        .values()
        .filter(|r| r.sites > 0)
        .map(|r| r.k as f32)
        .reduce(f32::min)
        .filter(|k| k.is_finite() && *k > 1.0)
}

/// One render's highlight account: cleared when it begins and when it ends,
/// with the decoded companions and their gather scratch.
pub(crate) struct Render;

impl Render {
    pub(crate) fn begin() -> Self {
        clear();
        Render
    }
}

impl Drop for Render {
    fn drop(&mut self) {
        clear();
    }
}

fn clear() {
    *stats().lock().unwrap_or_else(|e| e.into_inner()) = Stats::default();
    loaded_cache()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .clear();
    order().lock().unwrap_or_else(|e| e.into_inner()).clear();
    table().lock().unwrap_or_else(|e| e.into_inner()).clear();
    shifts().lock().unwrap_or_else(|e| e.into_inner()).clear();
    pair_fits()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .clear();
    *companion_scratch()
        .lock()
        .unwrap_or_else(|e| e.into_inner()) = None;
}

#[cfg(test)]
mod tests {
    use super::*;

    fn noise() -> NoiseModel {
        crate::pixel_shift_cmd::tests::synthetic_noise()
    }

    fn model(n: &NoiseModel) -> [f32; 4] {
        let (g1, g2) = (n.plane(CfaPlane::G1), n.plane(CfaPlane::G2));
        [
            g1.gain_dn_per_e,
            g1.read_noise_e * g1.gain_dn_per_e,
            g2.gain_dn_per_e,
            g2.read_noise_e * g2.gain_dn_per_e,
        ]
    }

    /// An unweighted pixel keeps the injected model's variance; a fully
    /// replaced one is the model on the companion's sample times the ratio
    /// squared (one model, no private estimate).
    #[test]
    fn the_variance_is_the_injected_model_on_each_sample() {
        let n = noise();
        let m = model(&n);
        for l in [0.0f32, 40.0, 900.0, 14000.0, 180_000.0] {
            let plain = 0.25 * (n.variance(CfaPlane::G1, l) + n.variance(CfaPlane::G2, l));
            let v0 = fused_variance(l, 0.0, 0.0, m, 20.0, 1.0 / 20.0);
            assert!(
                (v0 - plain).abs() <= 1e-5 * plain.max(1.0),
                "{l}: {v0} {plain}"
            );
            let c = l / 20.0;
            let comp = 0.25 * (n.variance(CfaPlane::G1, c) + n.variance(CfaPlane::G2, c)) * 400.0;
            let v1 = fused_variance(l, 1.0, 1.0, m, 20.0, 1.0 / 20.0);
            assert!((v1 - comp).abs() <= 1e-4 * comp, "{l}: {v1} {comp}");
            // Replaced samples are noisier than a base sample at the same level.
            if l > 100.0 {
                assert!(v1 > v0);
            }
        }
    }

    #[test]
    fn patches_blend_and_replace() {
        let mut planes = vec![vec![1000.0f32; 4], vec![2000.0; 4]];
        let p = FramePatches {
            sites: vec![
                Patch {
                    plane: 0,
                    index: 1,
                    w: 1.0,
                    v: 50_000.0,
                },
                Patch {
                    plane: 1,
                    index: 2,
                    w: 0.5,
                    v: 4000.0,
                },
                Patch {
                    plane: 7,
                    index: 0,
                    w: 1.0,
                    v: 1.0,
                },
            ],
            luma: Vec::new(),
            ratio: 20.0,
        };
        p.apply_planes(&mut planes);
        assert_eq!(planes[0], [1000.0, 50_000.0, 1000.0, 1000.0]);
        assert_eq!(planes[1], [2000.0, 2000.0, 3000.0, 2000.0]);
    }

    #[test]
    fn the_ramp_switches_between_three_quarters_and_nine_tenths_of_the_pin() {
        let (black, full) = (512.0f32, 16383.0 - 512.0);
        let at = |f: f32| ramp((black + f * full) as u16, black, full);
        assert_eq!(at(0.5), 0.0);
        assert_eq!(at(0.74), 0.0);
        assert!(at(0.8) > 0.0 && at(0.8) < 1.0);
        assert_eq!(at(0.91), 1.0);
        assert_eq!(ramp(16383, black, full), 1.0);
    }

    /// The checker's pin count: quads with any photosite at 0.9 of the pin,
    /// inside the subject only when one is given.
    #[test]
    fn pinned_sites_count_quads_inside_the_subject() {
        let mut f = crate::pixel_shift_cmd::tests::synthetic_group([(0, 0); 4], [1.0; 4])
            .into_iter()
            .next()
            .unwrap();
        let (ax, ay, s) = (f.active.x, f.active.y, f.stride);
        // Three quads near the pin: two in the left half, one in the right.
        for (x, y) in [(10usize, 10usize), (21, 30), (250, 100)] {
            f.data[(ay + y) * s + ax + x] = 16383;
        }
        f.data[(ay + 50) * s + ax + 50] = 14000; // below 0.9 of the pin
        assert_eq!(pinned_sites(&f, None), 3);
        let left: Vec<strehl_core::subject::Ring> =
            vec![vec![[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]]];
        assert_eq!(pinned_sites(&f, Some(&left)), 2);
    }

    /// A lone frame reads its own colour where it has it and its
    /// neighbours' otherwise.
    #[test]
    fn a_lone_frame_reads_each_colour_from_its_own_photosites() {
        let f = crate::pixel_shift_cmd::tests::synthetic_group([(0, 0); 4], [1.0; 4])
            .into_iter()
            .next()
            .unwrap();
        let a = Assembled::new(&f, None);
        let raw = |x: usize, y: usize| {
            f32::from(f.data[(f.active.y + y) * f.stride + f.active.x + x]) - 512.0
        };
        // (10, 10) is red: its own red, green from its four neighbours.
        assert_eq!(a.sample(0, 10, 10), raw(10, 10));
        let g = (raw(9, 10) + raw(11, 10) + raw(10, 9) + raw(10, 11)) / 4.0;
        assert!((a.sample(1, 10, 10) - g).abs() < 1e-3);
        // (11, 11) is blue: red from the four diagonals.
        let r = (raw(10, 10) + raw(12, 10) + raw(10, 12) + raw(12, 12)) / 4.0;
        assert!((a.sample(0, 11, 11) - r).abs() < 1e-3);
    }
}
