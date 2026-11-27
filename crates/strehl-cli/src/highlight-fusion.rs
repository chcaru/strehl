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
//! 1. **Ratio.** The commanded shutter ratio is only the start: the ratio is
//!    measured by the estimator `strehl survey` uses for the same quantity
//!    ([`crate::exposure_ratio`]: 8-photosite cells well exposed in both
//!    groups, the median of base over companion), with the companion read
//!    through its placement. It must lie within 0.25 EV of the start, two
//!    interleaved halves of its cells must agree within 1 %, and the
//!    hand-over sites (the base at 0.50 to 0.75 of the pin, nothing brighter
//!    near) must read 1.00 within 3 % after it when there are 400 of them
//!    and the companion is its own plane's (a borrowed one sees another
//!    focus). A pair with too few cells takes the commanded ratio when its
//!    hand-over sites confirm it. Motion between the groups is judged by the
//!    companion's measured shift, refused over two photosites. A refused
//!    ratio leaves the frame the base exposure alone, and the log says so
//!    (capture calibration spec, 5.7: the earlier patch fit and its texture
//!    test refused every plane of a dark subject under a deep highlight
//!    group).
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
/// The measured ratio's largest departure from the start, EV.
const CORRECTION_LIMIT_EV: f32 = 0.25;
/// Two interleaved halves of the ratio's cells agree within this fraction.
const HALVES_LIMIT: f64 = 0.01;
/// The hand-over sites read 1 within this fraction after the ratio, when
/// there are at least [`MIN_HANDOVER`] of them and the companion is its own
/// plane's. A companion borrowed from the next plane sees the scene at
/// another focus, and near highlights that moves its hand-over sites more
/// than the ratio does (MEASURED on the dragonfly of 2026-11-26: own planes
/// 0.990 to 1.002 over 117 pairs, borrowed 0.971 to 1.019 over 96, their
/// cell ratios within 0.11 % between halves): there the sites are reported,
/// and gate only a commanded ratio the cells could not measure.
const HANDOVER_LIMIT: f64 = 0.03;
const MIN_HANDOVER: usize = 400;
/// Cells this far inside the active area (the companion must cover them).
const RATIO_MARGIN: usize = 128;
/// The companion moved against its base group by more than this, in
/// photosites: refused. Its placement includes the shift, so this is a
/// guard against gross motion, not a tolerance on it (MEASURED on the
/// dragonfly: median 0.21, largest 0.83 over 213 pairs, on a rig whose
/// four-shot members are 0.14 to 0.50 px apart; spec 5.7 point 3 said one
/// photosite, which that rig would reach).
const MAX_SHIFT_PX: f64 = 2.0;
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
    /// is demoted): read in place by the device's frames and the decoders'
    /// planning, taken by a CPU gather and put back.
    frames: std::sync::RwLock<Option<(strehl_raw::Frame, Option<MeasuredGroup>)>>,
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

/// Every shift the run has measured, by companion, measuring frame and
/// scale: a pure function of those, kept from pass to pass while a [`Run`]
/// lives ([`shifts`] is each pass's own choice among them).
fn shift_memo() -> &'static Mutex<HashMap<String, Measured<[f64; 2]>>> {
    static MEMO: std::sync::OnceLock<Mutex<HashMap<String, Measured<[f64; 2]>>>> =
        std::sync::OnceLock::new();
    MEMO.get_or_init(Default::default)
}

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

/// Companions kept decoded, four frames each (about 0.5 GB at 61 MP): the
/// decode-ahead preloads a few frames before the fold uses them, and a
/// short stack's render pass finds the companions its preview pass decoded
/// ([`Run`]).
const LOADED_KEPT: usize = 8;

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
    // A highlight group's own check, under the witness's signal floor.
    let gate = crate::pixel_shift_cmd::judge_highlight(&m, r.residual);
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
        frames: std::sync::RwLock::new(Some((m1, group))),
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
    /// The correction the measurement applied, `log2(k / start)`.
    correction_ev: f64,
    /// Cells the ratio was measured on (0: the commanded ratio, confirmed
    /// by the hand-over sites), and how far its two halves disagree.
    cells: usize,
    split: Option<f64>,
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

#[allow(clippy::too_many_arguments)]
fn fit_pair(
    base: &Assembled<'_>,
    companion: &Assembled<'_>,
    bright: &Bright,
    maps: &[PointMap; 3],
    noise: &NoiseModel,
    start: f64,
    commanded: bool,
    borrowed: bool,
    black: f32,
    full: f32,
) -> std::result::Result<PairFit, String> {
    let e = ratio_cells(base, companion, bright, maps, noise, black, full);
    let (k, cells, split) = match e.ratio {
        Some(r) => (1.0 / r, e.cells, e.split()),
        // Nothing well exposed in both: the commanded ratio, if the
        // hand-over sites confirm it.
        None if commanded => (start, 0, None),
        None => {
            return Err(format!(
                "only {} cells are well exposed in both groups (need {}), and the capture \
                 records no commanded ratio",
                e.cells,
                crate::exposure_ratio::MIN_CELLS
            ));
        }
    };
    let correction_ev = (k / start).log2();
    if correction_ev.abs() > f64::from(CORRECTION_LIMIT_EV) {
        return Err(format!(
            "the measured ratio is {k:.3} against a start of {start:.3}: a correction of \
             {correction_ev:+.3} EV, beyond the {CORRECTION_LIMIT_EV} EV bound"
        ));
    }
    if let Some(s) = split
        && !(s <= HALVES_LIMIT)
    {
        return Err(format!(
            "two halves of the {cells} cells disagree by {:.2} % (limit {:.0} %)",
            100.0 * s,
            100.0 * HALVES_LIMIT
        ));
    }
    let samples = handover_samples(base, companion, bright, maps, k, black, full);
    let handover = (samples.len() >= 50).then(|| {
        let q = |p| f64::from(percentile(&samples, p));
        (q(0.5), 0.7413 * (q(0.75) - q(0.25)), samples.len())
    });
    let gates = cells == 0 || !borrowed;
    let confirmed = match handover {
        Some((m, _, n)) if n >= MIN_HANDOVER => {
            if gates && !((m - 1.0).abs() <= HANDOVER_LIMIT) {
                return Err(format!(
                    "the {n} hand-over sites read {m:.4} after the {} ratio {k:.3} (limit 1 \
                     +- {HANDOVER_LIMIT})",
                    if cells > 0 { "measured" } else { "commanded" }
                ));
            }
            (m - 1.0).abs() <= HANDOVER_LIMIT
        }
        _ => false,
    };
    if cells == 0 && !confirmed {
        return Err(format!(
            "the exposure ratio could not be measured: {} cells well exposed in both groups \
             (need {}) and {} hand-over sites to confirm the commanded ratio (need \
             {MIN_HANDOVER})",
            e.cells,
            crate::exposure_ratio::MIN_CELLS,
            handover.map_or(0, |h| h.2)
        ));
    }
    Ok(PairFit {
        k,
        start,
        commanded,
        correction_ev,
        cells,
        split,
        handover,
    })
}

/// The shared estimator's cells for a base group and its companion: base
/// samples at each photosite, the companion's at the photosite its
/// placement maps it to (nearest; a cell's mean does not need the
/// fraction). Cells with a base sample at the fusion's ramp do not count.
#[allow(clippy::too_many_arguments)]
fn ratio_cells(
    base: &Assembled<'_>,
    companion: &Assembled<'_>,
    bright: &Bright,
    maps: &[PointMap; 3],
    noise: &NoiseModel,
    black: f32,
    full: f32,
) -> crate::exposure_ratio::Estimate {
    use crate::exposure_ratio::{CELL, Cell, HIGH, LOW};
    let lo = (black + RAMP_LO * full) as u16;
    let floor = (black + LOW * full) as u16;
    let (w, h) = (bright.w, bright.h);
    let cols = w.saturating_sub(2 * RATIO_MARGIN) / CELL;
    let rows = h.saturating_sub(2 * RATIO_MARGIN) / CELL;
    // Samples of each colour a mosaic cell holds: the standard error is
    // taken as a single exposure's, whatever the assembly adds.
    let mosaic = [CELL * CELL / 4, CELL * CELL / 2, CELL * CELL / 4];
    let planes = [CfaPlane::R, CfaPlane::G1, CfaPlane::B];
    let cells: Vec<Cell> = (0..rows)
        .into_par_iter()
        .flat_map_iter(|cy| {
            let mut out = Vec::new();
            for cx in 0..cols {
                let x0 = (RATIO_MARGIN + cx * CELL) as isize;
                let y0 = (RATIO_MARGIN + cy * CELL) as isize;
                let (x1, y1) = (x0 + CELL as isize - 1, y0 + CELL as isize - 1);
                // The brightest raw sample of the four members: a cell at the
                // ramp is pinned, and one under the floor everywhere cannot
                // count (most of a dark subject; it is not read further).
                let top = bright.max(x0, y0, x1, y1, true);
                if top >= lo || top < floor {
                    continue;
                }
                let mut long = [0.0f64; 3];
                for y in y0..=y1 {
                    for x in x0..=x1 {
                        for (c, s) in long.iter_mut().enumerate() {
                            *s += f64::from(base.sample(c, x, y));
                        }
                    }
                }
                let n = (CELL * CELL) as f64;
                let long = long.map(|s| s / n);
                let share = long.map(|l| (l / f64::from(full)) as f32);
                // Only a cell some colour of which can count reads the
                // companion.
                if !share.iter().any(|s| (LOW..=HIGH).contains(s)) {
                    continue;
                }
                let corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)];
                if !corners.iter().all(|&(x, y)| {
                    maps.iter().all(|m| {
                        let (u, v) = m.apply(x as f64, y as f64);
                        companion.inside(u, v, 4.0)
                    })
                }) {
                    continue;
                }
                let mut short = [0.0f64; 3];
                for y in y0..=y1 {
                    for x in x0..=x1 {
                        for (c, s) in short.iter_mut().enumerate() {
                            let (u, v) = maps[c].apply(x as f64, y as f64);
                            *s += f64::from(companion.sample(
                                c,
                                u.round() as isize,
                                v.round() as isize,
                            ));
                        }
                    }
                }
                for c in 0..3 {
                    let s = short[c] / n;
                    out.push(Cell {
                        colour: c,
                        long: long[c],
                        long_share: share[c],
                        pinned: false,
                        short: s,
                        short_se: (f64::from(noise.variance(planes[c], s.max(0.0) as f32))
                            / mosaic[c] as f64)
                            .sqrt(),
                    });
                }
            }
            out
        })
        .collect();
    crate::exposure_ratio::estimate(cells)
}

/// The hand-over: where the base is high but below the ramp, the scaled
/// companion must read what the base reads. `k` x companion / base, green,
/// over the sites where the base is at 0.50 to 0.75 of the pin and nothing
/// within four photosites reaches the ramp.
fn handover_samples(
    base: &Assembled<'_>,
    companion: &Assembled<'_>,
    bright: &Bright,
    maps: &[PointMap; 3],
    k: f64,
    black: f32,
    full: f32,
) -> Vec<f32> {
    let lo = (black + RAMP_LO * full) as u16;
    let (w, h) = (bright.w, bright.h);
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
    rows.into_iter()
        .flatten()
        .filter(|v| v.is_finite())
        .collect()
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
// one frame's fusion
// ---------------------------------------------------------------------------

/// See [`Fusion::apply_variance`]; `model` is gain and read noise (DN) of
/// the two greens.
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

/// The base frame's brightness about each pull, as the fusion weighs a
/// site: per photosite floor `(fx, fy)`, the largest raw code of the
/// group's photosites in `[fx - 1 - r, fx + 2 + r]` each way, each end
/// clamped to the active area ([`Bright::max`]), for `r = widen` (the
/// weight's window) and `r = reach` (the pinned count's). Kept over
/// `[-pad, n + pad)`, beyond which every window clamps to the same
/// photosites. The device builds the same two maps (`hl_dilate_h`, `_v`).
struct Dilated {
    pad: usize,
    /// Padded width and height.
    pw: usize,
    ph: usize,
    wide: Vec<u16>,
    narrow: Vec<u16>,
}

impl Dilated {
    fn new(bright: &Bright, widen: usize, reach: usize) -> Self {
        let (w, h) = (bright.w, bright.h);
        let pad = widen + 3;
        let (pw, ph) = (w + 2 * pad, h + 2 * pad);
        let (wd, rc) = (widen as isize, reach as isize);
        let span = |x: isize, r: isize, n: usize| {
            let c = |v: isize| v.clamp(0, n as isize - 1) as usize;
            (c(x - 1 - r), c(x + 2 + r))
        };
        // Row maxima over the padded columns, both windows.
        let mut rows_wide = vec![0u16; pw * h];
        let mut rows_narrow = vec![0u16; pw * h];
        rows_wide
            .par_chunks_mut(pw)
            .zip(rows_narrow.par_chunks_mut(pw))
            .enumerate()
            .for_each(|(y, (rw, rn))| {
                let src = &bright.b[y * w..(y + 1) * w];
                for (i, (ow, on)) in rw.iter_mut().zip(rn.iter_mut()).enumerate() {
                    let x = i as isize - pad as isize;
                    let (a, b) = span(x, wd, w);
                    *ow = src[a..=b].iter().copied().max().unwrap_or(0);
                    let (a, b) = span(x, rc, w);
                    *on = src[a..=b].iter().copied().max().unwrap_or(0);
                }
            });
        let mut wide = vec![0u16; pw * ph];
        let mut narrow = vec![0u16; pw * ph];
        wide.par_chunks_mut(pw)
            .zip(narrow.par_chunks_mut(pw))
            .enumerate()
            .for_each(|(i, (ow, on))| {
                let y = i as isize - pad as isize;
                for (out, rows, r) in [(ow, &rows_wide, wd), (on, &rows_narrow, rc)] {
                    let (a, b) = span(y, r, h);
                    out.copy_from_slice(&rows[a * pw..(a + 1) * pw]);
                    for k in a + 1..=b {
                        for (o, v) in out.iter_mut().zip(&rows[k * pw..(k + 1) * pw]) {
                            *o = (*o).max(*v);
                        }
                    }
                }
            });
        Self {
            pad,
            pw,
            ph,
            wide,
            narrow,
        }
    }

    /// Both maxima at a photosite floor.
    #[inline]
    fn at(&self, fx: f64, fy: f64) -> (u16, u16) {
        let p = self.pad as f64;
        let x = fx.clamp(-p, (self.pw - self.pad - 1) as f64) + p;
        let y = fy.clamp(-p, (self.ph - self.pad - 1) as f64) + p;
        let i = y as usize * self.pw + x as usize;
        (self.wide[i], self.narrow[i])
    }
}

/// One fused frame's counts: patched sites, sites fully replaced, sites
/// with a pinned base sample in their footprint, those not fully replaced,
/// and companion samples near its own pin.
type Counts = [u64; 5];

/// A frame's fusion (plan X4): planned before its gather ([`plan`], or
/// [`plan_device`] for the device), its companion blended in after it.
///
/// The fold's level-0 planes are blended per site: where the base group's
/// brightest photosite about the site's pull reaches the ramp, weight
/// `w = ramp(max)`, the companion's sample through its own placement
/// times the ratio `k`, `plane = plane * (1 - w) + k v * w`. Every site is
/// weighed where it lies; nothing is listed, sorted or uploaded per site.
pub(crate) struct Fusion {
    r: Arc<CompanionRef>,
    /// The companion's member 1 and group, until the blend.
    comp: CompanionFrames,
    k: f32,
    t: Similarity,
    t_c: Similarity,
    ca: Option<&'static OpticalProfile>,
    black: f32,
    full: f32,
    widen: usize,
    reach: usize,
    carry: bool,
    full_geom: PlaneGeometry,
    rect: [usize; 4],
    bands: Option<Vec<bool>>,
    /// The CPU's brightness maps (`None` on the device).
    dilated: Option<Dilated>,
    bright_tiles: Option<Bright>,
    record: Record,
    started: std::time::Instant,
    /// After the blend: planes 1 and 2's weights where blended, for the
    /// variance.
    weights: Option<[Vec<f32>; 2]>,
}

/// The ramp's start and span, the pin, and the companion's pin, as the
/// device takes them (the CPU's [`ramp`] and comparisons, operand for
/// operand).
fn ramp_levels(full: f32) -> ([f32; 2], f32, f32) {
    (
        [RAMP_LO, RAMP_HI - RAMP_LO],
        f32::from(CONTAINER_MAX_DN - 2),
        0.98 * full,
    )
}

/// A frame's fusion planned for the CPU: `None` when it has no companion or
/// the companion cannot be used (said once in the log, and the frame is its
/// base exposure alone).
pub(crate) fn plan(i: Inputs<'_>) -> Result<Option<Fusion>> {
    plan_for(i, Mode::Cpu)
}

/// The same for the device: the brightness is measured there.
pub(crate) fn plan_device(i: Inputs<'_>) -> Result<Option<Fusion>> {
    plan_for(i, Mode::Device)
}

/// Who plans a frame's fusion.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Mode {
    /// The CPU fold: the brightness maps here, the companion taken for its
    /// gather.
    Cpu,
    /// The device's fold: the companion read in place.
    Device,
    /// A decoder, ahead of the fold ([`warm`]): only what the fold would
    /// measure first, into the render's caches.
    Warm,
}

fn plan_for(i: Inputs<'_>, mode: Mode) -> Result<Option<Fusion>> {
    let Some(r) = companion_of(&i.frame.path) else {
        return Ok(None);
    };
    match prepare(&i, &r, mode) {
        Ok(f) => Ok(Some(f)),
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
    /// Seconds per step: load, shift, bright map, ratio, windows, blend.
    steps: [f64; 6],
    /// The base group, or the companion group, was demoted and is used as
    /// its member 1 alone.
    base_member1: bool,
    companion_member1: Option<String>,
    /// Planned for a consumer of a few bands (counts cover only those).
    partial: bool,
}

impl Record {
    fn count(&mut self, c: Counts) {
        self.sites = c[0] as usize;
        self.replaced = c[1] as usize;
        self.pinned = c[2] as usize;
        self.pinned_unreplaced = c[3] as usize;
        self.companion_pinned = c[4] as usize;
    }
}

/// A companion's member 1 and group.
type Frames = (strehl_raw::Frame, Option<MeasuredGroup>);

/// A companion's frames taken out of their [`Loaded`] for one frame's use
/// and put back when dropped (unless another copy went back first).
struct Held {
    home: Arc<Loaded>,
    item: Option<Frames>,
}

impl Held {
    fn take(home: Arc<Loaded>, r: &CompanionRef) -> std::result::Result<Self, Refusal> {
        let held = home
            .frames
            .write()
            .unwrap_or_else(|e| e.into_inner())
            .take();
        let item = match held {
            Some(item) => item,
            // In use by another frame now: a copy of its own.
            None => decode_companion(r)?
                .frames
                .write()
                .unwrap_or_else(|e| e.into_inner())
                .take()
                .ok_or_else(|| Refusal("the companion's frames could not be read".into()))?,
        };
        Ok(Self {
            home,
            item: Some(item),
        })
    }

    fn frames(&self) -> &Frames {
        self.item.as_ref().expect("held")
    }
}

impl Drop for Held {
    fn drop(&mut self) {
        if let Some(item) = self.item.take() {
            let mut home = self.home.frames.write().unwrap_or_else(|e| e.into_inner());
            if home.is_none() {
                *home = Some(item);
            }
        }
    }
}

/// A fusion's companion frames: taken for the CPU's gather, read in place
/// for the device, or a copy of its own when another fold had taken them.
enum CompanionFrames {
    Held(Box<Held>),
    Shared(Arc<Loaded>),
    Own(Box<Frames>),
}

impl CompanionFrames {
    /// `f` of member 1 and the group; `None` if a shared companion's frames
    /// are out (taken by a CPU gather).
    fn with<R>(
        &self,
        f: impl FnOnce(&strehl_raw::Frame, Option<&MeasuredGroup>) -> R,
    ) -> Option<R> {
        match self {
            CompanionFrames::Held(h) => {
                let (m, g) = h.frames();
                Some(f(m, g.as_ref()))
            }
            CompanionFrames::Shared(l) => {
                let guard = l.frames.read().unwrap_or_else(|e| e.into_inner());
                guard.as_ref().map(|(m, g)| f(m, g.as_ref()))
            }
            CompanionFrames::Own(b) => Some(f(&b.0, b.1.as_ref())),
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

/// The fold's sites in plane order: `(dx, dy, channel)`, the four CFA
/// sites then, with `carry`, the eight carried channels.
fn fold_sites(carry: bool) -> Vec<(usize, usize, usize)> {
    [(0, 0), (1, 0), (0, 1), (1, 1)]
        .into_iter()
        .map(|(dx, dy)| (dx, dy, crate::align_cmd::rggb_channel_index(dx, dy)))
        .chain(CARRIED_SITES.iter().copied().filter(|_| carry))
        .collect()
}

fn prepare(
    i: &Inputs<'_>,
    r: &Arc<CompanionRef>,
    mode: Mode,
) -> std::result::Result<Fusion, Refusal> {
    let cpu = mode == Mode::Cpu;
    let started = std::time::Instant::now();
    let frame = i.frame;
    let mut clock = std::time::Instant::now();
    let mut steps = [0.0f64; 6];
    let mut lap = |k: usize| {
        steps[k] = clock.elapsed().as_secs_f64();
        clock = std::time::Instant::now();
    };
    let l = load(r)?;
    if mode != Mode::Warm {
        load_next(r);
    }
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
    let ca: Option<&'static OpticalProfile> =
        strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
    // The companion's frames: taken for the CPU's gather (another frame
    // using them meanwhile gets its own copy), else read in place.
    let comp = match mode {
        Mode::Cpu => CompanionFrames::Held(Box::new(Held::take(Arc::clone(&l), r)?)),
        _ if l.frames.read().unwrap_or_else(|e| e.into_inner()).is_some() => {
            CompanionFrames::Shared(Arc::clone(&l))
        }
        // Taken by a CPU gather: a decoder leaves the frame to the fold.
        Mode::Warm => return Err(Refusal(String::new())),
        _ => CompanionFrames::Own(Box::new(
            decode_companion(r)?
                .frames
                .write()
                .unwrap_or_else(|e| e.into_inner())
                .take()
                .ok_or_else(|| Refusal("the companion's frames could not be read".into()))?,
        )),
    };
    let guard = matches!(comp, CompanionFrames::Shared(_))
        .then(|| l.frames.read().unwrap_or_else(|e| e.into_inner()));
    let (cm1, cgroup): (&strehl_raw::Frame, Option<&MeasuredGroup>) = match (&comp, guard.as_ref())
    {
        (CompanionFrames::Held(h), _) => {
            let (m, g) = h.frames();
            (m, g.as_ref())
        }
        (CompanionFrames::Own(b), _) => (&b.0, b.1.as_ref()),
        (CompanionFrames::Shared(_), Some(g)) => match g.as_ref() {
            Some((m, g)) => (m, g.as_ref()),
            None if mode == Mode::Warm => return Err(Refusal(String::new())),
            None => return Err(Refusal("the companion's frames could not be read".into())),
        },
        (CompanionFrames::Shared(_), None) => unreachable!("read above"),
    };
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
        let comp = Assembled::new(cm1, cgroup);
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
        // A decoder measures only what the fold would measure first.
        None if mode == Mode::Warm && !first_of_companion(i.frame, r) => {
            return Err(Refusal(String::new()));
        }
        None => {
            // Scaled by the data's own ratio where it has one: a scale error
            // reads as residual noise and hides the structure.
            let scale = start_data.unwrap_or(start);
            // The same frame measuring the same companion at the same scale
            // in an earlier pass of the run measured exactly this.
            let memo_key = format!("{}|{}|{:x}", r.key, frame.path.display(), scale.to_bits());
            let memo = shift_memo()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .get(&memo_key)
                .cloned();
            let measured = match memo {
                Some(m) => m,
                None => {
                    let m = if r.companion_plane == r.plane {
                        measure_shift(frame, cm1, scale)
                    } else {
                        match strehl_raw::decode(&r.anchor_m1) {
                            Ok(a) => measure_shift(&a, cm1, scale),
                            Err(e) => Err(format!(
                                "its plane's base member 1 could not be read: {e:#}"
                            )),
                        }
                    };
                    shift_memo()
                        .lock()
                        .unwrap_or_else(|e| e.into_inner())
                        .insert(memo_key, m.clone());
                    m
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
    let moved = shift[0].hypot(shift[1]);
    if !(moved <= MAX_SHIFT_PX) {
        return Err(Refusal(format!(
            "its highlight group moved {moved:.2} photosites against its base group (limit \
             {MAX_SHIFT_PX}): motion between the groups"
        )));
    }
    let t_c = Similarity {
        a: t_anchor.a,
        b: t_anchor.b + Cx::new(0.5 * shift[0], 0.5 * shift[1]),
    };
    lap(1);
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
    // The CPU weighs sites from the group's brightness; the device measures
    // it there, so here it is needed only for a ratio not yet fitted.
    let bright = (cpu || known.is_none()).then(|| Bright::new(frame, i.group));
    lap(2);
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
            let comp = Assembled::new(cm1, cgroup);
            let f = fit_pair(
                &base,
                &comp,
                bright.as_ref().expect("measured for the fit"),
                &maps,
                &noise,
                start,
                commanded,
                r.companion_plane != r.plane,
                black,
                full,
            );
            pair_fits()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .insert(fit_key, f.clone());
            f
        }
    }
    .map_err(|why| Refusal(format!("its exposure ratio was refused: {why}")))?;
    lap(3);
    // A lone (demoted) frame is demosaiced before the pull: its 5 x 5
    // stencil reaches two photosites beyond the pull's taps.
    let reach: usize = if i.group.is_some() { 0 } else { 2 };
    let widen = GUARD as usize + reach;
    let dilated = match (&bright, cpu) {
        (Some(b), true) => Some(Dilated::new(b, widen, reach)),
        _ => None,
    };
    lap(4);
    let record = Record {
        k: fit.k,
        fit: Some(fit.clone()),
        shift,
        steps,
        base_member1: i.group.is_none(),
        companion_member1: l.gate.clone(),
        partial,
        ..Default::default()
    };
    drop(guard);
    Ok(Fusion {
        r: Arc::clone(r),
        comp,
        k: fit.k as f32,
        t: i.t,
        t_c,
        ca,
        black,
        full,
        widen,
        reach,
        carry: i.carry,
        full_geom: i.full,
        rect: i.rect,
        bands: i.bands.map(<[bool]>::to_vec),
        dilated,
        bright_tiles: if cpu { bright } else { None },
        record,
        started,
        weights: None,
    })
}

impl Fusion {
    /// Base units per companion unit.
    pub(crate) fn ratio(&self) -> f32 {
        self.k
    }

    /// The companion's placement (its own plane's, plus its shift).
    pub(crate) fn companion_placement(&self) -> Similarity {
        self.t_c
    }

    /// `f` of the companion's member 1 and group (`None` when demoted);
    /// `None` if its frames are out.
    pub(crate) fn with_companion<R>(
        &self,
        f: impl FnOnce(&strehl_raw::Frame, Option<&MeasuredGroup>) -> R,
    ) -> Option<R> {
        self.comp.with(f)
    }

    /// The companion's identity, for the device's companion slots.
    pub(crate) fn companion_key(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut h = std::collections::hash_map::DefaultHasher::new();
        self.r.key.hash(&mut h);
        self.r.paths.hash(&mut h);
        self.record.companion_member1.is_none().hash(&mut h);
        h.finish()
    }

    /// The ramp's full scale and black, the brightness windows (widen,
    /// reach), and the ramp's start and span, the pin and the companion's
    /// pin, as the device takes them.
    pub(crate) fn levels(&self) -> (f32, f32, usize, usize, [f32; 2], f32, f32) {
        let (ramp, pin, companion_pin) = ramp_levels(self.full);
        (
            self.black,
            self.full,
            self.widen,
            self.reach,
            ramp,
            pin,
            companion_pin,
        )
    }

    /// The frame was staged on the device with counts under `tag`: its
    /// account waits for them ([`device_counts`]). The companion's frames
    /// go back for the next frame that uses it.
    pub(crate) fn staged_on_device(self, tag: u32) {
        let seconds = self.started.elapsed().as_secs_f64();
        let Fusion { r, record, .. } = self;
        pending()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .insert(tag, (r, record, seconds));
    }

    /// The site pulls of the base frame, as its gather composes them.
    fn base_pulls(&self) -> Vec<Similarity> {
        fold_sites(self.carry)
            .iter()
            .map(|&(_, _, ci)| OpticalProfile::compose(self.ca, channel_of(ci), self.t))
            .collect()
    }

    /// Blend the companion into the gathered planes (black-subtracted,
    /// analysis grid), on the CPU: its gather over only the bands and
    /// columns a site may need, then each site weighed where it lies.
    /// Refused (the frame left as its base exposure) only before any plane
    /// is touched.
    pub(crate) fn apply_planes(&mut self, planes: &mut [Vec<f32>]) -> Result<()> {
        let blend_started = std::time::Instant::now();
        let (Some(dilated), Some(bright)) = (self.dilated.as_ref(), self.bright_tiles.as_ref())
        else {
            anyhow::bail!("a device-planned fusion applied on the CPU");
        };
        let geom = self.full_geom;
        let (gw, gh) = (geom.width, geom.height);
        let centre = (gw as f64 * 0.5, gh as f64 * 0.5);
        let [rx, ry, lw, lh] = self.rect;
        let sites = fold_sites(self.carry);
        let pulls = self.base_pulls();
        let (_, _, companion_pin) = ramp_levels(self.full);
        let (black, full, k) = (self.black, self.full, self.k);
        let lo = (black + RAMP_LO * full) as u16;
        let widen = self.widen as isize;
        let band_rows = crate::align_cmd::BAND_ROWS;
        let only = self.bands.as_deref();
        let wanted =
            |py: usize| only.is_none_or(|b| b.get(py / band_rows).copied().unwrap_or(false));
        // Bands and columns a site may need: a block of 32 columns of a band
        // whose pulls (between its corners', the maps being affine) reach no
        // bright tile is skipped. An upper bound: never too few.
        let bands_n = gh.div_ceil(band_rows);
        const BLOCK: usize = 32;
        let spans: Vec<Vec<(usize, usize)>> = (0..bands_n)
            .into_par_iter()
            .map(|b| {
                let (y0, y1) = ((b * band_rows).max(ry), ((b + 1) * band_rows).min(ry + lh));
                let mut out: Vec<(usize, usize)> = Vec::new();
                if y0 >= y1 || !(y0..y1).any(wanted) {
                    return out;
                }
                for b0 in (0..lw).step_by(BLOCK) {
                    let b1 = (b0 + BLOCK).min(lw);
                    let bright_here = sites.iter().zip(&pulls).any(|(&(dx, dy, _), t)| {
                        let (ox, oy) = (dx as f64 * 0.5, dy as f64 * 0.5);
                        let corners = [(b0, y0), (b1 - 1, y0), (b0, y1 - 1), (b1 - 1, y1 - 1)].map(
                            |(lx, py)| {
                                let (sx, sy) = t.apply_at(
                                    (rx + lx) as f64 + ox,
                                    py as f64 + oy,
                                    centre.0,
                                    centre.1,
                                );
                                (2.0 * sx, 2.0 * sy)
                            },
                        );
                        let xs = corners.map(|c| c.0);
                        let ys = corners.map(|c| c.1);
                        let (xa, xb) = (
                            xs.iter().copied().fold(f64::INFINITY, f64::min),
                            xs.iter().copied().fold(f64::NEG_INFINITY, f64::max),
                        );
                        let (ya, yb) = (
                            ys.iter().copied().fold(f64::INFINITY, f64::min),
                            ys.iter().copied().fold(f64::NEG_INFINITY, f64::max),
                        );
                        !(xa.is_finite() && xb.is_finite() && ya.is_finite() && yb.is_finite())
                            || bright.max(
                                xa.floor() as isize - 2 - widen,
                                ya.floor() as isize - 2 - widen,
                                xb.floor() as isize + 3 + widen,
                                yb.floor() as isize + 3 + widen,
                                false,
                            ) >= lo
                    });
                    if bright_here {
                        let (c0, c1) = (rx + b0, rx + b1);
                        match out.last_mut() {
                            Some(last) if last.1 == c0 => last.1 = c1,
                            _ => out.push((c0, c1)),
                        }
                    }
                }
                out
            })
            .collect();
        let gather_bands: Vec<bool> = spans.iter().map(|s| !s.is_empty()).collect();
        let n = lw * lh;
        let mut weights = [vec![0f32; n], vec![0f32; n]];
        let mut counts: Counts = [0; 5];
        if gather_bands.iter().any(|&b| b) {
            let row_gathered = |py: usize| gather_bands[py / band_rows] && wanted(py);
            // Blend one site's plane from the companion's samples `value`
            // (by full quad index; `None` where it has none).
            let blend = |s: usize,
                         plane: &mut [f32],
                         weight: Option<&mut [f32]>,
                         value: &(dyn Fn(usize) -> Option<f32> + Sync)|
             -> Counts {
                let (dx, dy, _) = sites[s];
                let (ox, oy) = (dx as f64 * 0.5, dy as f64 * 0.5);
                let t = pulls[s];
                let rows = plane.par_chunks_mut(lw).enumerate();
                let per_row = |(ly, row): (usize, &mut [f32]), mut wrow: Option<&mut [f32]>| {
                    let mut c: Counts = [0; 5];
                    let py = ry + ly;
                    if !row_gathered(py) {
                        return c;
                    }
                    for (lx, x) in row.iter_mut().enumerate() {
                        let px = rx + lx;
                        let (sx, sy) =
                            t.apply_at(px as f64 + ox, py as f64 + oy, centre.0, centre.1);
                        let (fx, fy) = (2.0 * sx, 2.0 * sy);
                        if !(fx.is_finite() && fy.is_finite()) {
                            continue;
                        }
                        let (m, near) = dilated.at(fx.floor(), fy.floor());
                        let w = ramp(m, black, full);
                        if w <= 0.0 {
                            continue;
                        }
                        let pinned = near >= CONTAINER_MAX_DN - 2;
                        let v = value(py * gw + px);
                        if let Some(v) = v {
                            let keep = 1.0 - w;
                            *x = *x * keep + (k * v) * w;
                            c[0] += 1;
                            if w >= 1.0 {
                                c[1] += 1;
                            }
                            if v >= companion_pin {
                                c[4] += 1;
                            }
                            if let Some(wr) = wrow.as_deref_mut() {
                                wr[lx] = w;
                            }
                        }
                        if pinned {
                            c[2] += 1;
                            if v.is_none() || w < 1.0 {
                                c[3] += 1;
                            }
                        }
                    }
                    c
                };
                let add = |a: Counts, b: Counts| std::array::from_fn(|i| a[i] + b[i]);
                match weight {
                    Some(wp) => rows
                        .zip(wp.par_chunks_mut(lw))
                        .map(|(r, wr)| per_row(r, Some(wr)))
                        .reduce(|| [0; 5], add),
                    None => rows.map(|r| per_row(r, None)).reduce(|| [0; 5], add),
                }
            };
            let mut scratch = companion_scratch()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .take()
                .unwrap_or_default();
            let CompanionFrames::Held(held) = &mut self.comp else {
                anyhow::bail!("a CPU fusion without its companion's frames");
            };
            let (mut m1, group) = held.item.take().expect("held");
            let [w1, w2] = &mut weights;
            let mut w1 = Some(&mut w1[..]);
            let mut w2 = Some(&mut w2[..]);
            let gathered = crate::align_cmd::gather_companion(
                &mut m1,
                group,
                self.t_c,
                geom,
                &mut scratch,
                gather_bands.clone(),
                spans.clone(),
                self.carry,
                |(dx, dy), dst, cover, inv| {
                    let s = dy * 2 + dx;
                    let weight = match s {
                        1 => w1.take(),
                        2 => w2.take(),
                        _ => None,
                    };
                    let value = |fi: usize| cover[fi].then(|| dst[fi] * inv);
                    let c = blend(s, &mut planes[s], weight, &value);
                    for (a, b) in counts.iter_mut().zip(c) {
                        *a += b;
                    }
                },
            );
            let group = match gathered {
                Ok(group) => group,
                Err(e) => {
                    // Before any site was blended: the frame is its base
                    // exposure alone.
                    *companion_scratch()
                        .lock()
                        .unwrap_or_else(|e| e.into_inner()) = Some(scratch);
                    note_refused(&self.r, format!("its gather failed: {e:#}"));
                    return Ok(());
                }
            };
            held.item = Some((m1, group));
            if self.carry {
                anyhow::ensure!(
                    scratch.carried.len() >= CARRIED_SITES.len(),
                    "the companion's carried channels are missing"
                );
                for k in 0..CARRIED_SITES.len() {
                    let carried = &scratch.carried[k];
                    let value = |fi: usize| Some(carried[fi]);
                    let c = blend(4 + k, &mut planes[4 + k], None, &value);
                    for (a, b) in counts.iter_mut().zip(c) {
                        *a += b;
                    }
                }
            }
            let mut home = companion_scratch()
                .lock()
                .unwrap_or_else(|e| e.into_inner());
            if home.is_none() {
                *home = Some(scratch);
            }
        }
        self.weights = Some(weights);
        self.record.count(counts);
        self.record.steps[5] = blend_started.elapsed().as_secs_f64();
        note_fused(
            &self.r,
            self.record.clone(),
            self.started.elapsed().as_secs_f64(),
        );
        Ok(())
    }

    /// Replace the luma variance at the fused pixels: per green, the
    /// injected model on the base sample and, times the ratio squared, on
    /// the companion's (the luma over the ratio), blended by the weight
    /// squared. The same expression as the device's `hl_variance`.
    pub(crate) fn apply_variance(&self, luma: &[f32], var: &mut [f32], noise: &NoiseModel) {
        let Some([w1, w2]) = self.weights.as_ref() else {
            return;
        };
        let (g1, g2) = (noise.plane(CfaPlane::G1), noise.plane(CfaPlane::G2));
        let model = [
            g1.gain_dn_per_e,
            g1.read_noise_e * g1.gain_dn_per_e,
            g2.gain_dn_per_e,
            g2.read_noise_e * g2.gain_dn_per_e,
        ];
        let k = self.k;
        let ik = 1.0 / k;
        var.par_iter_mut()
            .zip(luma.par_iter())
            .zip(w1.par_iter().zip(w2.par_iter()))
            .for_each(|((v, l), (a, b))| {
                if *a > 0.0 || *b > 0.0 {
                    *v = fused_variance(*l, *a, *b, model, k, ik);
                }
            });
    }
}

// ---------------------------------------------------------------------------
// planning ahead, on the decoders
// ---------------------------------------------------------------------------

/// One fold pass, as its decoders see it: frames in fold order, their
/// placements and the fold's geometry.
struct Pass {
    paths: Vec<PathBuf>,
    placements: Vec<Option<Similarity>>,
    /// Per companion, the pass's first placed frame using it: the frame
    /// whose fold would measure its shift.
    first: HashMap<String, usize>,
    full: PlaneGeometry,
    rect: [usize; 4],
    carry: bool,
}

fn pass() -> &'static std::sync::RwLock<Option<Arc<Pass>>> {
    static PASS: std::sync::OnceLock<std::sync::RwLock<Option<Arc<Pass>>>> =
        std::sync::OnceLock::new();
    PASS.get_or_init(Default::default)
}

/// A fold pass begins: its decoders may plan each frame's fusion as they
/// decode it ([`warm`]). `plan` is the fold's order, `placements` every
/// frame's placement as its gather uses it.
pub(crate) fn begin_pass(
    paths: &[PathBuf],
    plan: &[usize],
    placements: Vec<Option<Similarity>>,
    full: PlaneGeometry,
    rect: [usize; 4],
    carry: bool,
) {
    let mut first: HashMap<String, usize> = HashMap::new();
    let mut early: Vec<Arc<CompanionRef>> = Vec::new();
    for &i in plan {
        if placements.get(i).copied().flatten().is_none() {
            continue;
        }
        if let Some(r) = paths.get(i).and_then(|p| companion_of(p))
            && !first.contains_key(&r.key)
        {
            first.insert(r.key.clone(), i);
            early.push(r);
        }
    }
    // The pass's first companions start decoding now, beside its first
    // frames, rather than when a decoder reaches the frame that needs one.
    // On their own thread, not a rayon worker: `load` may wait.
    early.truncate(LOADED_KEPT);
    if !early.is_empty() {
        std::thread::spawn(move || {
            for r in early {
                let _ = load(&r);
            }
        });
    }
    *pass().write().unwrap_or_else(|e| e.into_inner()) = (!first.is_empty()).then(|| {
        Arc::new(Pass {
            paths: paths.to_vec(),
            placements,
            first,
            full,
            rect,
            carry,
        })
    });
}

/// The pass's decoders plan no more.
pub(crate) fn end_pass() {
    *pass().write().unwrap_or_else(|e| e.into_inner()) = None;
}

/// Is `frame` its pass's first frame of companion `r`?
fn first_of_companion(frame: &strehl_raw::Frame, r: &CompanionRef) -> bool {
    let p = pass().read().unwrap_or_else(|e| e.into_inner()).clone();
    p.is_some_and(|p| {
        p.first
            .get(&r.key)
            .is_some_and(|&i| p.paths.get(i) == Some(&frame.path))
    })
}

/// On a decoder, as frame `index` is decoded: what its fusion's planning
/// would measure on the fold's thread (the companion's decode, its shift,
/// the pair's ratio), into the render's caches, so the fold finds them.
/// The caches hold exactly what the fold would compute: the shift is the
/// one its first frame of the pass measures, the ratio a pure function of
/// the frame, its group and both
/// placements. A frame whose companion's shift is not yet measured leaves
/// its ratio to the fold too (a decoder never waits for another frame).
/// Anything refused is left to the fold, which says why.
pub(crate) fn warm(index: usize, frame: &strehl_raw::Frame, group: Option<&MeasuredGroup>) {
    let Some(p) = pass().read().unwrap_or_else(|e| e.into_inner()).clone() else {
        return;
    };
    let Some(t) = p.placements.get(index).copied().flatten() else {
        return;
    };
    if p.paths.get(index) != Some(&frame.path) {
        return;
    }
    let Some(r) = companion_of(&frame.path) else {
        return;
    };
    let placements = &p.placements;
    let inputs = Inputs {
        frame,
        group,
        t,
        placement: &|q| placements.get(q).copied().flatten(),
        full: p.full,
        rect: p.rect,
        bands: None,
        carry: p.carry,
    };
    let _ = prepare(&inputs, &r, Mode::Warm);
}

/// Frames staged on the device, awaiting their counts: by tag, the
/// companion, the account so far and the seconds spent.
type Pending = HashMap<u32, (Arc<CompanionRef>, Record, f64)>;

fn pending() -> &'static Mutex<Pending> {
    static PENDING: std::sync::OnceLock<Mutex<Pending>> = std::sync::OnceLock::new();
    PENDING.get_or_init(Default::default)
}

/// The next device count tag, below `tags`.
pub(crate) fn next_tag(tags: usize) -> u32 {
    static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    (NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % tags) as u32
}

/// The tags staged on the device whose counts have not been read.
pub(crate) fn pending_tags() -> Vec<u32> {
    let mut t: Vec<u32> = pending()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .keys()
        .copied()
        .collect();
    t.sort_unstable();
    t
}

/// The device's counts for `tags`: each frame's account is complete.
pub(crate) fn device_counts(tags: &[u32], counts: &[[u64; 5]]) {
    for (tag, c) in tags.iter().zip(counts) {
        let entry = pending()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .remove(tag);
        if let Some((r, mut record, seconds)) = entry {
            record.count(*c);
            note_fused(&r, record, seconds);
        }
    }
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
            "ratio_cells": f.map(|f| f.cells),
            "ratio_halves_split": f.and_then(|f| f.split),
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

/// Tell the desktop how many planes with a highlight companion used it
/// ([`crate::ui_progress::highlights`]); nothing when none had one.
pub(crate) fn report_use() {
    let s = stats().lock().unwrap_or_else(|e| e.into_inner());
    let planes = s.fused.len() + s.refused.len();
    if planes == 0 {
        return;
    }
    crate::ui_progress::highlights(
        planes,
        s.fused.len(),
        s.refused.values().next().map(String::as_str),
    );
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

/// One render pass's highlight account: cleared when it begins and when it
/// ends, with its measurements and gather scratch, and the decoded
/// companions unless a [`Run`] keeps them.
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

/// A whole run's companions: kept decoded from one render pass to the next
/// (the lateral-colour preview, then the render) while it lives, with every
/// shift measured. A decode is a pure function of the files and a shift of
/// its frame, companion and scale, so a pass finds exactly what it would
/// compute; which frame measures a companion's shift, and every ratio (it
/// depends on the pass's lateral-colour profile), are still each pass's.
pub(crate) struct Run;

static RUNS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

impl Run {
    pub(crate) fn begin() -> Self {
        RUNS.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        Run
    }
}

impl Drop for Run {
    fn drop(&mut self) {
        if RUNS.fetch_sub(1, std::sync::atomic::Ordering::SeqCst) == 1 {
            loaded_cache()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .clear();
            shift_memo()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .clear();
        }
    }
}

fn clear() {
    *stats().lock().unwrap_or_else(|e| e.into_inner()) = Stats::default();
    if RUNS.load(std::sync::atomic::Ordering::SeqCst) == 0 {
        loaded_cache()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .clear();
        shift_memo()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .clear();
    }
    order().lock().unwrap_or_else(|e| e.into_inner()).clear();
    table().lock().unwrap_or_else(|e| e.into_inner()).clear();
    shifts().lock().unwrap_or_else(|e| e.into_inner()).clear();
    pair_fits()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .clear();
    pending().lock().unwrap_or_else(|e| e.into_inner()).clear();
    end_pass();
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

    /// The padded window maxima equal `Bright::max` over each window,
    /// inside the active area, at its edges and far beyond them.
    #[test]
    fn the_window_maxima_are_brights_maxima_everywhere() {
        let (w, h) = (37usize, 29usize);
        let mut seed = 7u64;
        let b: Vec<u16> = (0..w * h)
            .map(|_| {
                seed = seed
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                (seed >> 52) as u16
            })
            .collect();
        let bright = Bright {
            w,
            h,
            b,
            tw: 1,
            tiles: Vec::new(),
        };
        for (widen, reach) in [(2usize, 0usize), (4, 2)] {
            let d = Dilated::new(&bright, widen, reach);
            for fy in -14isize..h as isize + 14 {
                for fx in -14isize..w as isize + 14 {
                    let (m, n) = d.at(fx as f64, fy as f64);
                    let (wd, rc) = (widen as isize, reach as isize);
                    let want = bright.max(fx - 1 - wd, fy - 1 - wd, fx + 2 + wd, fy + 2 + wd, true);
                    let near = bright.max(fx - 1 - rc, fy - 1 - rc, fx + 2 + rc, fy + 2 + rc, true);
                    assert_eq!((m, n), (want, near), "{fx},{fy} widen {widen}");
                }
            }
        }
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
