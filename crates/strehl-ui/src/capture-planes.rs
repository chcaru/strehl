//! The planes of a capture as they arrive, for the in-flight plane view
//! (`capture-plane-view.rs`, h-proof). Everything here runs off the UI
//! thread, at below-normal priority.
//!
//! Two tiers:
//!
//! - **Every try, cheaply.** Each group the camera takes (a plane's first
//!   try and each retake) is bound to its plane by the capture journal
//!   (`events.jsonl`: `capture_buffered` lists its files with `name`,
//!   `plane`, `group_id` and `member_index`) and arrives once each of its
//!   RAWs has a durable receipt. Its first RAW's camera preview (about
//!   1024 px) gives a focus map: per cell of a [`MAP_CELLS`]-wide grid, the
//!   mean squared Laplacian of the preview's luma. A cell is sharp in a try
//!   when its measure is within [`KEEP`] of the most any try has shown there
//!   and above the run's floor ([`FLOOR_BELOW`] under its strong detail).
//!   The history strip's bars and the picture's "Sharp" overlay are these
//!   maps. They are a display aid: where a plane is sharpest so far, not a
//!   measurement of quality, and never a merge input.
//! - **The plane shown, at full resolution.** Its RAWs are decoded; a
//!   four-shot group is measured as the checker measures it
//!   (`strehl_cli::pixel_shift_cmd::measure_with_tiles`, the same group check
//!   and witness, with the witness's tile map) and, when its offsets cover
//!   the four CFA parities, assembled with each site's red, green and blue
//!   from the members that sampled it; otherwise the first shot is
//!   demosaiced (bilinear). It is developed with the camera's matrix and
//!   white balance and one display gain for the whole run, into an 8-bit
//!   pyramid that a tile worker cuts into 1024 px textures on demand.
//!
//! Only one full build runs at a time, only for a try the view asks for,
//! and only while the view is painted; a newer request supersedes it at the
//! next member.
use std::{
    collections::{HashMap, HashSet, VecDeque},
    path::{Path, PathBuf},
    sync::{
        Arc, Condvar, Mutex,
        atomic::{AtomicBool, AtomicU64, Ordering},
        mpsc,
    },
    time::{Duration, Instant},
};

use anyhow::{Context, Result, bail, ensure};
use eframe::egui::{self, Rect, TextureId};
use rayon::prelude::*;

use crate::draft_preview::LineTail;
use crate::hdr_display::{PhotoLayer, PhotoPresenter};

/// Focus-map cells across the preview's long side.
pub(crate) const MAP_CELLS: usize = 48;
/// The camera preview's side the focus maps are measured on.
const MAP_SIDE: u32 = 1024;
/// Focus measures are kept as `256 * log2(F) + 32768` (u16): 256 a factor
/// of two.
const ENC_OCTAVE: f32 = 256.0;
/// Sharp: within 70 % of the most any try showed in that cell
/// (`256 * log2(1 / 0.7)`).
pub(crate) const KEEP: u16 = 132;
/// ...and no more than 4 octaves (1/16) under the run's strong detail (the
/// 95th percentile of the cells' maxima): cells of background and noise stay
/// clear.
pub(crate) const FLOOR_BELOW: u16 = 1024;
/// The side of a tile's core in texels.
pub(crate) const TILE: u32 = 1024;
/// The coarsest level is uploaded whole: no side above this.
const OVERVIEW_SIDE: u32 = 1024;
/// Threads of the plane builder's own pool (below-normal priority): a
/// 32-thread desktop keeps most of itself for the receiver, the checker and
/// stacking during capture.
const PLANE_THREADS: usize = 6;
/// The view counts as shown while it was painted this recently.
const ACTIVE: Duration = Duration::from_millis(1500);
/// A request waits this long for a newer one before its full build starts
/// (scrubbing the history does not decode every plane passed).
const SETTLE: Duration = Duration::from_millis(220);
/// Tiles kept beyond those in view (4 MiB each): 192 MiB of texture.
const TILE_BUDGET: usize = 48;

/// The workers' steps, timed (benchmarks only): what was running when a
/// frame was slow.
#[cfg(test)]
pub(crate) static TRACE: Mutex<Vec<(Instant, Instant, &'static str)>> = Mutex::new(Vec::new());

/// Runs `f`, recording its span under `what` in benchmarks.
#[inline]
fn step<T>(what: &'static str, f: impl FnOnce() -> T) -> T {
    #[cfg(test)]
    let began = Instant::now();
    let out = f();
    #[cfg(test)]
    if let Ok(mut t) = TRACE.lock()
        && t.len() < 200_000
    {
        t.push((began, Instant::now(), what));
    }
    #[cfg(not(test))]
    let _ = what;
    out
}

/// The workers run below normal priority (benchmarks:
/// `STREHL_BENCH_NORMAL_PRIORITY` leaves them at normal).
fn lower_priority() {
    #[cfg(test)]
    if std::env::var_os("STREHL_BENCH_NORMAL_PRIORITY").is_some() {
        return;
    }
    crate::draft_preview::lower_thread_priority();
}

/// A try: one group the camera took for a plane.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PlaneTry {
    pub plane: u64,
    /// 1 for the plane's first group, 2 for its first retake, ...
    pub attempt: u32,
    /// Member RAWs' logical names, in member order.
    pub names: Vec<Arc<str>>,
    /// Their stored files.
    pub paths: Vec<PathBuf>,
    /// The lens position it was taken at.
    pub focus: Option<u16>,
    /// When the camera host had it (Unix ms).
    pub taken_ms: Option<u64>,
}

impl PlaneTry {
    pub fn key(&self) -> TryKey {
        TryKey {
            plane: self.plane,
            attempt: self.attempt,
        }
    }
    pub fn first(&self) -> Option<&Arc<str>> {
        self.names.first()
    }
}

/// A try's identity in a run.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord, Default)]
pub(crate) struct TryKey {
    pub plane: u64,
    pub attempt: u32,
}

/// A RAW's capture ordinal (`frame-000017.ARW`: 17).
fn ordinal(name: &str) -> Option<u64> {
    name.strip_prefix("frame-")?
        .strip_suffix(".ARW")?
        .parse()
        .ok()
}

/// A group the capture journal bound, waiting for its RAWs.
#[derive(Clone, Debug)]
struct Bound {
    plane: u64,
    names: Vec<String>,
    focus: Option<u16>,
    unix_ms: Option<u64>,
}

/// Follows a run's capture journal and transfer receipts: the tries whose
/// RAWs are all on this PC, in capture order. Without bindings (a host that
/// writes none) a plane is every `shots` RAWs.
pub(crate) struct TryTail {
    run: PathBuf,
    shots: u64,
    events: LineTail,
    receipts: LineTail,
    groups: HashSet<String>,
    pending: VecDeque<Bound>,
    durable: HashMap<String, PathBuf>,
    attempts: HashMap<u64, u32>,
    /// Unbound RAWs in arrival order (fallback).
    loose: VecDeque<String>,
    bound_any: bool,
}

impl TryTail {
    pub fn new(run: PathBuf, shots: u64) -> Self {
        Self {
            run,
            shots: shots.max(1),
            events: LineTail::default(),
            receipts: LineTail::default(),
            groups: HashSet::new(),
            pending: VecDeque::new(),
            durable: HashMap::new(),
            attempts: HashMap::new(),
            loose: VecDeque::new(),
            bound_any: false,
        }
    }

    /// The tries that became complete since the last call.
    pub fn poll(&mut self) -> Vec<PlaneTry> {
        let journal = self.run.join("events.jsonl");
        let has_journal = journal.is_file();
        let (lines, _) = self.events.lines(&journal);
        for line in lines {
            self.bind(&line);
        }
        let (lines, _) = self
            .receipts
            .lines(&self.run.join("transfer-receipts.jsonl"));
        for line in lines {
            if let Some((name, path)) = receipt(&self.run, &line) {
                self.loose.push_back(name.clone());
                self.durable.insert(name, path);
            }
        }
        let mut out = Vec::new();
        // Bound groups, in capture order; one whose RAWs are not all here
        // does not hold up later ones (its RAWs may never all arrive).
        let mut i = 0;
        while i < self.pending.len() {
            let b = &self.pending[i];
            if b.names.iter().all(|n| self.durable.contains_key(n)) {
                let b = self.pending.remove(i).expect("index");
                out.push(self.make(b));
            } else {
                i += 1;
            }
        }
        if self.bound_any {
            self.loose.clear();
        } else if !has_journal || self.loose.len() as u64 > 2 * self.shots {
            // No bindings: every `shots` RAWs in ordinal order are a plane.
            let mut names: Vec<String> = self.loose.drain(..).collect();
            names.sort_by_key(|n| ordinal(n));
            let mut rest = Vec::new();
            let mut by_plane: std::collections::BTreeMap<u64, Vec<String>> = Default::default();
            for n in names {
                match ordinal(&n) {
                    Some(o) => by_plane
                        .entry((o - 1) / self.shots + 1)
                        .or_default()
                        .push(n),
                    None => rest.push(n),
                }
            }
            for (plane, names) in by_plane {
                if names.len() as u64 >= self.shots {
                    out.push(self.make(Bound {
                        plane,
                        names,
                        focus: None,
                        unix_ms: None,
                    }));
                } else {
                    self.loose.extend(names);
                }
            }
        }
        out
    }

    fn make(&mut self, b: Bound) -> PlaneTry {
        let attempt = self.attempts.entry(b.plane).or_default();
        *attempt += 1;
        PlaneTry {
            plane: b.plane,
            attempt: *attempt,
            paths: b
                .names
                .iter()
                .map(|n| self.durable.get(n).cloned().unwrap_or_default())
                .collect(),
            names: b.names.iter().map(|n| Arc::from(n.as_str())).collect(),
            focus: b.focus,
            taken_ms: b.unix_ms,
        }
    }

    /// Records the groups a journal line binds.
    fn bind(&mut self, line: &[u8]) {
        let needle = |n: &[u8]| line.windows(n.len()).any(|w| w == n);
        if !needle(b"\"capture_buffered\"") && !needle(b"\"capture_complete\"") {
            return;
        }
        let Ok(v) = serde_json::from_slice::<serde_json::Value>(line) else {
            return;
        };
        let response = &v["data"]["response"];
        let focus = response["camera_reply"]["focus"]
            .as_u64()
            .or_else(|| response["camera_reply"]["files"][0]["focus"].as_u64())
            .and_then(|f| u16::try_from(f).ok());
        // Each group in the line: its id, plane, and members by index.
        type Group = (String, u64, Vec<(u64, String)>);
        let mut groups: Vec<Group> = Vec::new();
        for file in response["files"].as_array().into_iter().flatten() {
            let (Some(name), Some(plane)) = (file["name"].as_str(), file["plane"].as_u64()) else {
                continue;
            };
            let group = file["group_id"].as_str().unwrap_or("").to_owned();
            let member = file["member_index"].as_u64().unwrap_or(0);
            match groups
                .iter_mut()
                .find(|(g, p, _)| *g == group && *p == plane)
            {
                Some(g) => g.2.push((member, name.to_owned())),
                None => groups.push((group, plane, vec![(member, name.to_owned())])),
            }
        }
        for (group, plane, mut members) in groups {
            let id = format!("{group}/{plane}/{}", members[0].1);
            if !self.groups.insert(id) {
                continue;
            }
            self.bound_any = true;
            members.sort();
            self.pending.push_back(Bound {
                plane,
                names: members.into_iter().map(|(_, n)| n).collect(),
                focus,
                unix_ms: v["unix_ms"].as_u64(),
            });
        }
    }
}

/// A durable RAW receipt: its name and stored file.
fn receipt(run: &Path, line: &[u8]) -> Option<(String, PathBuf)> {
    let r: serde_json::Value = serde_json::from_slice(line).ok()?;
    if r["ok"] != true || r["durable"] != true {
        return None;
    }
    let name = r["logical_name"].as_str()?;
    ordinal(name)?;
    let file = run.join(match r["storage_encoding"].as_str() {
        Some("identity") | None => name.to_owned(),
        Some(_) => format!("{name}.straw"),
    });
    Some((name.to_owned(), file))
}

// ---------------------------------------------------------------------------
// Focus maps

/// A focus measure as kept (see [`ENC_OCTAVE`]); 0 for none.
pub(crate) fn encode(f: f32) -> u16 {
    if f.is_nan() || f <= 0.0 {
        return 0;
    }
    (f.log2() * ENC_OCTAVE + 32768.0)
        .round()
        .clamp(1.0, 65535.0) as u16
}

/// A preview's focus map: its grid and, per cell row-major, the encoded
/// mean squared Laplacian of luma.
pub(crate) fn focus_map(rgba: &[u8], size: [usize; 2]) -> ([usize; 2], Vec<u16>) {
    let [w, h] = size;
    let cell = w.max(h).div_ceil(MAP_CELLS).max(1);
    let grid = [w.div_ceil(cell), h.div_ceil(cell)];
    let mut sum = vec![0f64; grid[0] * grid[1]];
    let mut count = vec![0u32; grid[0] * grid[1]];
    let luma = |x: usize, y: usize| {
        let i = 4 * (y * w + x);
        0.2126 * f32::from(rgba[i])
            + 0.7152 * f32::from(rgba[i + 1])
            + 0.0722 * f32::from(rgba[i + 2])
    };
    for y in 1..h.saturating_sub(1) {
        for x in 1..w.saturating_sub(1) {
            let l = 4.0 * luma(x, y)
                - luma(x - 1, y)
                - luma(x + 1, y)
                - luma(x, y - 1)
                - luma(x, y + 1);
            let c = (y / cell) * grid[0] + x / cell;
            sum[c] += f64::from(l * l);
            count[c] += 1;
        }
    }
    let cells = sum
        .iter()
        .zip(&count)
        .map(|(s, n)| {
            if *n > 0 {
                encode((*s / f64::from(*n)) as f32)
            } else {
                0
            }
        })
        .collect();
    (grid, cells)
}

/// One try as the deck publishes it.
#[derive(Clone, Debug)]
pub(crate) struct TryInfo {
    pub t: PlaneTry,
    /// Its focus map, once measured (on the run's grid).
    pub map: Option<Arc<[u16]>>,
    /// The share of the frame sharp in it.
    pub share: Option<f32>,
}

/// What the deck knows of the run: every try arrived, with its focus map.
#[derive(Clone, Debug, Default)]
pub(crate) struct DeckSnapshot {
    pub revision: u64,
    /// In capture order.
    pub tries: Vec<TryInfo>,
    pub grid: [usize; 2],
    /// The previews' size the grid divides.
    pub preview: [usize; 2],
    /// Per cell, the most any try showed.
    pub max: Arc<[u16]>,
    pub floor: u16,
    /// Tries whose preview could not be read, and the last reason.
    pub unreadable: usize,
    pub note: Option<String>,
    /// The source was read at least once, and tries not measured yet.
    pub polled: bool,
    pub pending: usize,
}

impl DeckSnapshot {
    /// Whether cell `i` of `map` is sharp.
    pub fn sharp(&self, map: &[u16], i: usize) -> bool {
        let v = map[i];
        v > 0 && v >= self.floor && v.saturating_add(KEEP) >= self.max[i]
    }
    /// The share of `map`'s cells that are sharp.
    pub fn share(&self, map: &[u16]) -> f32 {
        if map.is_empty() || map.len() != self.max.len() {
            return 0.0;
        }
        let n = (0..map.len()).filter(|&i| self.sharp(map, i)).count();
        n as f32 / map.len() as f32
    }
    /// The newest try's index.
    pub fn newest(&self) -> Option<usize> {
        self.tries.len().checked_sub(1)
    }
    /// The index of the try `key`.
    pub fn index(&self, key: TryKey) -> Option<usize> {
        self.tries.iter().rposition(|t| t.t.key() == key)
    }
    /// The try whose first RAW is `first`, else the plane's last try.
    pub fn find(&self, plane: u64, first: Option<&str>) -> Option<usize> {
        first
            .and_then(|f| {
                self.tries
                    .iter()
                    .rposition(|t| t.t.first().is_some_and(|n| &**n == f))
            })
            .or_else(|| self.tries.iter().rposition(|t| t.t.plane == plane))
    }
}

/// Recomputes the cells' maxima, the floor and every try's share.
fn summarize(snap: &mut DeckSnapshot) {
    let cells = snap.grid[0] * snap.grid[1];
    let mut max = vec![0u16; cells];
    for t in &snap.tries {
        if let Some(map) = t.map.as_ref().filter(|m| m.len() == cells) {
            for (m, v) in max.iter_mut().zip(map.iter()) {
                *m = (*m).max(*v);
            }
        }
    }
    let mut sorted: Vec<u16> = max.iter().copied().filter(|v| *v > 0).collect();
    sorted.sort_unstable();
    let strong = sorted
        .get((sorted.len().max(1) - 1) * 95 / 100)
        .copied()
        .unwrap_or(0);
    snap.floor = strong.saturating_sub(FLOOR_BELOW).max(1);
    snap.max = max.into();
    let shares: Vec<Option<f32>> = snap
        .tries
        .iter()
        .map(|t| t.map.as_ref().map(|m| snap.share(m)))
        .collect();
    for (t, s) in snap.tries.iter_mut().zip(shares) {
        t.share = s;
    }
}

// ---------------------------------------------------------------------------
// The full-resolution plane

/// What the picture of a try is.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum ImageKind {
    /// The four shots, each site's colours from the members that sampled it.
    FourShot,
    /// The first shot, demosaiced: the four shots could not be assembled
    /// (their offsets miss a CFA parity), as the stack folds the group.
    FirstShot,
    /// A one-shot plane, demosaiced.
    OneShot,
    /// The camera's own preview, while the RAWs are read.
    Preview,
}

/// The checker's findings on a four-shot group, as measured here.
#[derive(Clone, Debug, Default)]
pub(crate) struct Findings {
    pub offsets: [(isize, isize); 4],
    pub gains: [f64; 4],
    pub structure: [f64; 4],
    pub parities: bool,
    /// The checker's reason for demoting it (`judge`), if any.
    pub reason: Option<String>,
    pub retake: bool,
    /// Witness tiles: side in sites, grid, mean z^2 each (row-major).
    pub tile: usize,
    pub grid: [usize; 2],
    pub z2: Vec<f32>,
    pub median: f32,
    /// Per tile, how far the shots disagree there once each pair's
    /// whole-group shift is taken out, photosites (`NaN`: too little
    /// detail), and its p99: what the checker judges.
    pub local: Vec<f32>,
    pub local_px: f64,
    /// Witness pair shift per quadrant (TL, TR, BL, BR), photosites, both
    /// pairs, less the residual compensation the checker applies to the
    /// whole group (`residual[b] - residual[a]`): what it judges, by
    /// quadrant.
    pub quadrants: [[[f64; 2]; 2]; 4],
    pub pair_shift: [[f64; 2]; 2],
    pub mean_z2: f64,
}

/// Local disagreement above which the checker demotes a group (photosites).
pub(crate) const LOCAL_LIMIT: f64 = strehl_cli::pixel_shift_cmd::LOCAL_TOLERANCE_PX;
/// Witness pair shift the checker tolerates (photosites).
pub(crate) const PAIR_SHIFT: f64 = strehl_cli::pixel_shift_cmd::PAIR_SHIFT_TOLERANCE_PX;

/// One level of a picture's pyramid: `stride` source pixels a texel, RGB.
pub(crate) struct Level {
    pub stride: u32,
    pub size: [u32; 2],
    pub rgb: Vec<u8>,
}

/// A try's picture and what is known of it.
pub(crate) struct PlaneImage {
    /// Counts builds: a new picture replaces the shown one's tiles.
    pub id: u64,
    pub key: TryKey,
    /// Source pixels.
    pub size: [u32; 2],
    /// The geometry it stands for: the sensor's pixels (a preview is drawn
    /// over the same rectangle), so a zoom means the same with either.
    pub frame: [u32; 2],
    pub levels: Vec<Level>,
    pub kind: ImageKind,
    pub findings: Option<Findings>,
    pub iso: Option<f32>,
    /// The display gain (one for the run), in stops.
    pub display_ev: f32,
    /// Milliseconds: decoding, the group check, development and pyramid.
    pub cost: [f64; 3],
}

impl PlaneImage {
    pub fn overview(&self) -> &Level {
        self.levels.last().expect("a level")
    }
    pub fn level(&self, stride: u32) -> Option<&Level> {
        self.levels.iter().find(|l| l.stride == stride)
    }
    /// Bytes held (performance checks).
    #[allow(dead_code)]
    pub fn bytes(&self) -> usize {
        self.levels.iter().map(|l| l.rgb.len()).sum()
    }
}

/// The big buffers a build reuses. A 61 MP four-shot build needs about
/// 490 MB of member samples and 240 MB of pyramid; allocating and returning
/// them for every plane stalls every other thread's small allocations,
/// the UI's included (MEASURED, `large_buffers_stall_small_allocations`:
/// worst burst 28 ms against 2.2 alone; 6.8 ms when reused). They are kept
/// while the deck lives: the members, and one picture's pyramid besides
/// the one shown.
#[derive(Default)]
pub(crate) struct Buffers {
    members: Vec<Vec<u16>>,
    bytes: Vec<Vec<u8>>,
}

/// Member buffers kept (a four-shot group).
const KEEP_MEMBERS: usize = 4;
/// Bytes of picture buffers kept: about two 61 MP pyramids.
const KEEP_BYTES: usize = 520 << 20;

impl Buffers {
    fn member(&mut self) -> Vec<u16> {
        self.members.pop().unwrap_or_default()
    }
    fn keep_member(&mut self, v: Vec<u16>) {
        if self.members.len() < KEEP_MEMBERS && v.capacity() > 0 {
            self.members.push(v);
        }
    }
    /// `len` bytes, every one overwritten by the caller: the smallest kept
    /// buffer that holds them, else a new one.
    fn bytes(&mut self, len: usize) -> Vec<u8> {
        let best = (0..self.bytes.len())
            .filter(|&i| self.bytes[i].capacity() >= len)
            .min_by_key(|&i| self.bytes[i].capacity());
        match best {
            Some(i) => {
                let mut v = self.bytes.swap_remove(i);
                v.clear();
                v.resize(len, 0);
                v
            }
            None => vec![0u8; len],
        }
    }
    fn keep_bytes(&mut self, v: Vec<u8>) {
        if v.capacity() < (1 << 20) {
            return;
        }
        self.bytes.push(v);
        // Within the bound, the largest are kept: they cost most to make.
        self.bytes.sort_by_key(|b| std::cmp::Reverse(b.capacity()));
        let mut total = 0;
        self.bytes.retain(|b| {
            total += b.capacity();
            total <= KEEP_BYTES
        });
    }
    /// Takes back a picture's levels.
    fn reclaim(&mut self, image: PlaneImage) {
        for l in image.levels {
            self.keep_bytes(l.rgb);
        }
    }
}

/// A picture's pixels before its pyramid.
pub(crate) struct Developed {
    pub size: [u32; 2],
    pub rgb: Vec<u8>,
    pub kind: ImageKind,
    pub findings: Option<Findings>,
    pub iso: Option<f32>,
    pub gain: f32,
    pub decode_ms: f64,
    pub check_ms: f64,
}

/// Camera RGB (black-subtracted DN) to display sRGB bytes.
pub(crate) struct Develop {
    inv_range: f32,
    wb: [f32; 3],
    render: strehl_core::color::Render,
    pub gain: f32,
    lut: Vec<u8>,
}

/// Entries of the sRGB encoding table.
const LUT: usize = 4096;

fn encode_lut() -> Vec<u8> {
    (0..LUT)
        .map(|i| {
            (strehl_core::color::srgb_encode(i as f32 / (LUT - 1) as f32) * 255.0)
                .round()
                .clamp(0.0, 255.0) as u8
        })
        .collect()
}

impl Develop {
    pub fn of(frame: &strehl_raw::Frame) -> Self {
        let levels = frame.levels;
        let wb = frame
            .wb_gains()
            .or_else(|| {
                frame
                    .xyz_to_cam_rgb()
                    .and_then(strehl_core::color::implied_daylight_wb_gains)
            })
            .unwrap_or([1.0; 3]);
        let render = frame
            .xyz_to_cam_rgb()
            .and_then(strehl_core::color::camera_to_srgb)
            .unwrap_or_else(|| {
                strehl_core::color::Render::new([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
            })
            .with_saturation(levels, wb, 1.0);
        Self {
            inv_range: 1.0 / levels.range().max(1.0),
            wb,
            render,
            gain: 1.0,
            lut: encode_lut(),
        }
    }
    /// Linear sRGB before the display gain.
    #[inline]
    fn linear(&self, cam: [f32; 3]) -> [f32; 3] {
        let k = self.inv_range;
        self.render.develop([
            cam[0].max(0.0) * k * self.wb[0],
            cam[1].max(0.0) * k * self.wb[1],
            cam[2].max(0.0) * k * self.wb[2],
        ])
    }
    #[inline]
    fn pixel(&self, cam: [f32; 3]) -> [u8; 3] {
        let v = self.linear(cam);
        let e =
            |c: f32| self.lut[((c * self.gain).clamp(0.0, 1.0) * (LUT - 1) as f32 + 0.5) as usize];
        [e(v[0]), e(v[1]), e(v[2])]
    }
    /// The display gain that puts the 99.5th percentile of `luma` at 0.9,
    /// between 1 and 8.
    pub fn gain_for(mut luma: Vec<f32>) -> f32 {
        let Some(p) = strehl_core::color::percentile_in_place(&mut luma, 99.5) else {
            return 1.0;
        };
        if p > 0.0 {
            (0.9 / p).clamp(1.0, 8.0)
        } else {
            1.0
        }
    }
}

/// A frame's black-subtracted sample at active coordinates, clamped to its
/// buffer.
#[inline]
fn sample(f: &strehl_raw::Frame, x: isize, y: isize) -> f32 {
    let bx = (f.active.x as isize + x).clamp(0, f.stride as isize - 1) as usize;
    let by = (f.active.y as isize + y).clamp(0, f.buffer_height as isize - 1) as usize;
    f32::from(f.data[by * f.stride + bx]) - f.levels.black
}

/// Mirror `i` into `0..n` (keeps the CFA parity).
#[inline]
fn reflect(i: isize, n: usize) -> isize {
    let n = n as isize;
    if i < 0 {
        -i
    } else if i >= n {
        2 * (n - 1) - i
    } else {
        i
    }
}

/// Bilinear demosaic of `f`'s active area at site `(x, y)`: camera RGB.
#[inline]
fn bilinear(f: &strehl_raw::Frame, x: usize, y: usize) -> [f32; 3] {
    let (w, h) = (f.active.width, f.active.height);
    let at =
        |dx: isize, dy: isize| sample(f, reflect(x as isize + dx, w), reflect(y as isize + dy, h));
    let own = at(0, 0);
    let cross = 0.25 * (at(-1, 0) + at(1, 0) + at(0, -1) + at(0, 1));
    let diag = 0.25 * (at(-1, -1) + at(1, -1) + at(-1, 1) + at(1, 1));
    let horiz = 0.5 * (at(-1, 0) + at(1, 0));
    let vert = 0.5 * (at(0, -1) + at(0, 1));
    match strehl_core::pixel_shift::cfa_colour(x as isize, y as isize) {
        0 => [own, cross, diag],
        2 => [diag, cross, own],
        _ if y.is_multiple_of(2) => [horiz, own, vert],
        _ => [vert, own, horiz],
    }
}

/// The four members' camera RGB at member 1's site `(x, y)`.
#[inline]
fn assembled(
    frames: &[strehl_raw::Frame],
    offsets: &[(isize, isize); 4],
    inv_gain: &[f32; 4],
    table: &[[usize; 4]; 4],
    x: usize,
    y: usize,
) -> [f32; 3] {
    let m = table[(x & 1) | ((y & 1) << 1)];
    let s = |k: usize| {
        sample(
            &frames[k],
            x as isize + offsets[k].0,
            y as isize + offsets[k].1,
        ) * inv_gain[k]
    };
    [s(m[0]), 0.5 * (s(m[1]) + s(m[2])), s(m[3])]
}

/// Develops the try's frames: four shots assembled when `offsets` cover the
/// parities, else the first demosaiced. `gain`: the run's display gain, or
/// measured from this picture.
/// Four members' offsets and gains, when they are assembled.
type Assembly<'a> = Option<(&'a [(isize, isize); 4], &'a [f64; 4])>;

fn develop(
    frames: &[strehl_raw::Frame],
    assemble: Assembly<'_>,
    gain: Option<f32>,
    buffers: &mut Buffers,
) -> (Vec<u8>, f32) {
    let first = &frames[0];
    let (w, h) = (first.active.width, first.active.height);
    let mut dev = Develop::of(first);
    let table: [[usize; 4]; 4] = assemble.map_or([[0; 4]; 4], |(o, _)| {
        std::array::from_fn(|p| {
            strehl_core::pixel_shift::site_members(o, (p & 1) as isize, (p >> 1) as isize)
        })
    });
    let inv_gain: [f32; 4] = assemble.map_or([1.0; 4], |(_, g)| {
        g.map(|g| if g > 0.0 { (1.0 / g) as f32 } else { 1.0 })
    });
    let cam = |x: usize, y: usize| match assemble {
        Some((o, _)) => assembled(frames, o, &inv_gain, &table, x, y),
        None => bilinear(first, x, y),
    };
    dev.gain = gain.unwrap_or_else(|| {
        let luma: Vec<f32> = (0..h)
            .step_by(8)
            .collect::<Vec<_>>()
            .par_iter()
            .flat_map_iter(|&y| {
                let dev = &dev;
                let cam = &cam;
                (0..w)
                    .step_by(8)
                    .map(move |x| strehl_core::color::luminance(dev.linear(cam(x, y))))
            })
            .collect();
        Develop::gain_for(luma)
    });
    let mut rgb = buffers.bytes(w * h * 3);
    rgb.par_chunks_mut(w * 3).enumerate().for_each(|(y, row)| {
        for x in 0..w {
            row[3 * x..3 * x + 3].copy_from_slice(&dev.pixel(cam(x, y)));
        }
    });
    (rgb, dev.gain)
}

/// sRGB byte to linear.
fn to_linear() -> [f32; 256] {
    std::array::from_fn(|i| {
        let v = i as f32 / 255.0;
        if v <= 0.04045 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        }
    })
}

/// Half of `level` (each texel the mean of up to 2 x 2, in linear light).
fn halve(level: &Level, lin: &[f32; 256], lut: &[u8], buffers: &mut Buffers) -> Level {
    let [w, h] = level.size.map(|s| s as usize);
    let (nw, nh) = (w.div_ceil(2), h.div_ceil(2));
    let mut rgb = buffers.bytes(nw * nh * 3);
    rgb.par_chunks_mut(nw * 3).enumerate().for_each(|(y, row)| {
        for x in 0..nw {
            for c in 0..3 {
                let mut sum = 0.0;
                let mut n = 0.0;
                for (dx, dy) in [(0, 0), (1, 0), (0, 1), (1, 1)] {
                    let (sx, sy) = (2 * x + dx, 2 * y + dy);
                    if sx < w && sy < h {
                        sum += lin[level.rgb[(sy * w + sx) * 3 + c] as usize];
                        n += 1.0;
                    }
                }
                row[3 * x + c] = lut[((sum / n) * (LUT - 1) as f32 + 0.5) as usize];
            }
        }
    });
    Level {
        stride: level.stride * 2,
        size: [nw as u32, nh as u32],
        rgb,
    }
}

/// The pyramid of a picture: itself, then halves until the coarsest fits
/// [`OVERVIEW_SIDE`].
pub(crate) fn pyramid(size: [u32; 2], rgb: Vec<u8>, buffers: &mut Buffers) -> Vec<Level> {
    let lin = to_linear();
    let lut = encode_lut();
    let mut levels = vec![Level {
        stride: 1,
        size,
        rgb,
    }];
    while levels
        .last()
        .expect("a level")
        .size
        .iter()
        .any(|s| *s > OVERVIEW_SIDE)
    {
        let next = halve(levels.last().expect("a level"), &lin, &lut, buffers);
        levels.push(next);
    }
    levels
}

/// The checker's group findings, measured from the decoded members.
fn findings(frames: &[strehl_raw::Frame]) -> Findings {
    use strehl_cli::pixel_shift_cmd as ps;
    let first = &frames[0];
    let noise = strehl_core::profile::noise_model_for(
        &first.camera,
        first.iso,
        strehl_core::noise::Levels {
            black: first.levels.black,
            white: first.levels.white,
        },
    );
    let (m, w) = ps::measure_with_tiles([&frames[0], &frames[1], &frames[2], &frames[3]], &noise);
    let residual = ps::ResidualMode::default();
    let c = &m.check;
    let mut out = Findings {
        offsets: c.offsets,
        gains: c.gains,
        structure: c.precision,
        parities: c.parities,
        reason: ps::judge(&m, residual),
        retake: ps::retake_helps(&m, residual),
        local_px: m.witness.as_ref().map_or(f64::NAN, |w| w.local_px),
        ..Findings::default()
    };
    if let Some(w) = w {
        let mut finite: Vec<f32> = w
            .tile_z2
            .iter()
            .copied()
            .filter(|v| v.is_finite())
            .collect();
        finite.sort_by(f32::total_cmp);
        out.median = finite.get(finite.len() / 2).copied().unwrap_or(f32::NAN);
        out.tile = w.tile;
        out.grid = w.tiles;
        out.z2 = w.tile_z2;
        out.local = w.tile_local_px;
        // The checker judges each pair's shift less the members' measured
        // residual displacement (its default `ResidualMode::Compensate`).
        let comp: [[f64; 2]; 2] = std::array::from_fn(|p| {
            let [a, b] = w.pair_members[p];
            match residual.sign() {
                Some(_) => [
                    c.residual[b][0] - c.residual[a][0],
                    c.residual[b][1] - c.residual[a][1],
                ],
                None => [0.0, 0.0],
            }
        });
        out.quadrants = w
            .pair_shift_quadrants
            .map(|q| std::array::from_fn(|p| [q[p][0] - comp[p][0], q[p][1] - comp[p][1]]));
        out.pair_shift = std::array::from_fn(|p| {
            [
                w.pair_shift[p][0] - comp[p][0],
                w.pair_shift[p][1] - comp[p][1],
            ]
        });
        out.mean_z2 = w.mean_z2;
    }
    out
}

// ---------------------------------------------------------------------------
// Sources: a run on disk, or a fixture

/// Where the deck's tries and pictures come from.
pub(crate) trait Source: Send + Sync {
    /// Tries that arrived since the last call, in capture order.
    fn poll(&mut self) -> Vec<PlaneTry>;
    /// The try's camera preview: its size and RGBA, at most `side` px.
    fn preview(&self, t: &PlaneTry, side: u32) -> Result<([usize; 2], Vec<u8>)> {
        self.preview_of(t, side).map(|(size, rgba, _)| (size, rgba))
    }
    /// The same, and the size of the picture it was made from (the
    /// camera's full-size JPEG is the sensor's geometry).
    fn preview_of(&self, t: &PlaneTry, side: u32) -> Result<([usize; 2], Vec<u8>, [u32; 2])>;
    /// The try at full resolution; `abort` says when a newer request came.
    fn full(
        &self,
        t: &PlaneTry,
        gain: Option<f32>,
        abort: &dyn Fn() -> bool,
        buffers: &mut Buffers,
    ) -> Result<Developed>;
    /// The try's focus map without a preview (fixtures): the preview's
    /// size, the grid and the cells.
    fn map(&self, _t: &PlaneTry) -> Option<([usize; 2], [usize; 2], Vec<u16>)> {
        None
    }
}

/// A capture folder being written (or written).
pub(crate) struct RunSource {
    tail: TryTail,
}

impl RunSource {
    pub fn new(run: PathBuf, shots: u64) -> Self {
        Self {
            tail: TryTail::new(run, shots),
        }
    }
}

/// Reads a try's RAWs and develops them (see the module's notes).
pub(crate) fn build_raw(
    paths: &[PathBuf],
    gain: Option<f32>,
    abort: &dyn Fn() -> bool,
    buffers: &mut Buffers,
) -> Result<Developed> {
    ensure!(!paths.is_empty(), "The try has no RAWs");
    let started = Instant::now();
    let mut frames = Vec::with_capacity(paths.len());
    // Members one after another (each decode is parallel within): a newer
    // request stops the build between them.
    let give_back = |frames: Vec<strehl_raw::Frame>, buffers: &mut Buffers| {
        for f in frames {
            buffers.keep_member(f.data);
        }
    };
    ensure!(!abort(), "superseded");
    // Each member decoded on its own pool thread with the decoder's serial
    // path, which reads into that thread's reused file buffer: no member
    // allocates its 29 MB archive or its 122 MB of samples afresh.
    let given: Vec<Vec<u16>> = paths.iter().map(|_| buffers.member()).collect();
    let decoded: Vec<std::result::Result<strehl_raw::Frame, strehl_raw::RawError>> = paths
        .par_iter()
        .zip(given.into_par_iter())
        .map(|(path, buffer)| {
            step("decode a member", || {
                strehl_raw::decode_serial(path, Some(buffer))
            })
        })
        .collect();
    let mut failure = None;
    for (path, d) in paths.iter().zip(decoded) {
        match d {
            Ok(f) => frames.push(f),
            Err(e) => {
                failure.get_or_insert((path, e));
            }
        }
    }
    if let Some((path, e)) = failure {
        give_back(frames, buffers);
        return Err(e).with_context(|| crate::display_path::display_path(path).to_string());
    }
    let decode_ms = started.elapsed().as_secs_f64() * 1000.0;
    if abort() {
        give_back(frames, buffers);
        bail!("superseded");
    }
    let checked = Instant::now();
    let four = frames.len() == 4
        && frames.iter().all(|f| {
            f.active.width == frames[0].active.width && f.active.height == frames[0].active.height
        });
    let found = four.then(|| step("group check", || findings(&frames)));
    let check_ms = checked.elapsed().as_secs_f64() * 1000.0;
    if abort() {
        give_back(frames, buffers);
        bail!("superseded");
    }
    let assemble = found
        .as_ref()
        .filter(|f| f.parities)
        .map(|f| (&f.offsets, &f.gains));
    let (rgb, gain) = step("develop", || develop(&frames, assemble, gain, buffers));
    let size = [
        frames[0].active.width as u32,
        frames[0].active.height as u32,
    ];
    let iso = frames[0].iso;
    give_back(frames, buffers);
    Ok(Developed {
        size,
        rgb,
        kind: match (&found, assemble.is_some()) {
            (_, true) => ImageKind::FourShot,
            (Some(_), false) => ImageKind::FirstShot,
            (None, _) => ImageKind::OneShot,
        },
        findings: found,
        iso,
        gain,
        decode_ms,
        check_ms,
    })
}

impl Source for RunSource {
    fn poll(&mut self) -> Vec<PlaneTry> {
        self.tail.poll()
    }
    fn preview_of(&self, t: &PlaneTry, side: u32) -> Result<([usize; 2], Vec<u8>, [u32; 2])> {
        let path = t.paths.first().context("The try has no RAWs")?;
        let image = crate::source_preview::load_draft_source(path, side, &AtomicBool::new(false))?;
        Ok((image.size, image.rgba, image.source_size))
    }
    fn full(
        &self,
        t: &PlaneTry,
        gain: Option<f32>,
        abort: &dyn Fn() -> bool,
        buffers: &mut Buffers,
    ) -> Result<Developed> {
        build_raw(&t.paths, gain, abort, buffers)
    }
}

/// A finished run's tries handed out one every `every`, as a capture
/// in flight hands them (benchmarks and offscreen checks).
pub(crate) struct ReplaySource {
    inner: RunSource,
    every: Duration,
    started: Option<Instant>,
    all: Vec<PlaneTry>,
    given: usize,
}

impl ReplaySource {
    pub fn new(run: PathBuf, shots: u64, every: Duration) -> Self {
        Self {
            inner: RunSource::new(run, shots),
            every,
            started: None,
            all: Vec::new(),
            given: 0,
        }
    }
}

impl Source for ReplaySource {
    fn poll(&mut self) -> Vec<PlaneTry> {
        self.all.extend(self.inner.poll());
        let started = *self.started.get_or_insert_with(Instant::now);
        let due =
            (started.elapsed().as_secs_f64() / self.every.as_secs_f64().max(1e-3)) as usize + 1;
        let end = due.min(self.all.len());
        let out = self.all[self.given.min(end)..end].to_vec();
        self.given = end;
        out
    }
    fn preview_of(&self, t: &PlaneTry, side: u32) -> Result<([usize; 2], Vec<u8>, [u32; 2])> {
        self.inner.preview_of(t, side)
    }
    fn full(
        &self,
        t: &PlaneTry,
        gain: Option<f32>,
        abort: &dyn Fn() -> bool,
        buffers: &mut Buffers,
    ) -> Result<Developed> {
        self.inner.full(t, gain, abort, buffers)
    }
}

/// The fixtures' synthetic capture (`--capture-fixture flight...`): a
/// textured oval subject tilted in depth, so each plane is sharp in a band
/// that moves down the subject; the checker's verdicts from the fixture's
/// journal, with witness tiles and pair shifts made to match them.
pub(crate) struct FixtureSource {
    tries: Vec<PlaneTry>,
    reasons: HashMap<TryKey, Option<String>>,
    given: bool,
    /// The full pictures' size.
    size: [u32; 2],
    /// Planes in the stack (the subject's depth spans them).
    planes: u64,
}

impl FixtureSource {
    pub fn new(progress: &super::follow::Progress, planes: u64, size: [u32; 2]) -> Self {
        let mut tries = Vec::new();
        let mut reasons = HashMap::new();
        let start = 1_795_300_000_000u64;
        for (i, item) in progress.feed.iter().enumerate() {
            let first = item
                .first
                .clone()
                .unwrap_or_else(|| "frame-000001.ARW".into());
            let o = ordinal(&first).unwrap_or(1);
            let names: Vec<Arc<str>> = (0..4)
                .map(|k| Arc::from(format!("frame-{:06}.ARW", o + k).as_str()))
                .collect();
            let t = PlaneTry {
                plane: item.plane,
                attempt: item.attempt,
                paths: names.iter().map(|n| PathBuf::from(&**n)).collect(),
                names,
                focus: item.target,
                taken_ms: Some(start + i as u64 * 5_690),
            };
            reasons.insert(t.key(), item.reason.as_deref().map(str::to_owned));
            tries.push(t);
        }
        Self {
            tries,
            reasons,
            given: false,
            size,
            planes,
        }
    }

    /// The subject's depth (in planes) at `(u, v)`, or `None` off it.
    fn depth(&self, u: f32, v: f32) -> Option<f32> {
        let (dx, dy) = ((u - 0.5) / 0.36, (v - 0.53) / 0.34);
        let r = dx * dx + dy * dy;
        (r <= 1.0).then(|| {
            // Tilted top to bottom, domed in the middle.
            let tilt = 0.08 + 0.84 * ((v - 0.19) / 0.68).clamp(0.0, 1.0);
            (tilt - 0.06 * (1.0 - r)) * self.planes as f32
        })
    }

    /// The scene at `(u, v)` for plane `p`, `scale` pixels per unit of
    /// texture (sRGB bytes).
    fn shade(&self, u: f32, v: f32, p: f32, px: f32) -> [u8; 3] {
        match self.depth(u, v) {
            None => {
                let g = (14.0 + 10.0 * (1.0 - v)) as u8;
                [g, g, g + 2]
            }
            Some(d) => {
                let sharp = (-((d - p) / 4.0).powi(2)).exp();
                // Fine texture a few source pixels across (only where the
                // plane is sharp), and coarse segments and spots that blur
                // keeps, so the subject reads at any zoom.
                let fine = ((u * px * 0.9).sin() * (v * px * 1.3).sin()) * 0.5
                    + ((((u * px) as i64 * 7919 + (v * px) as i64 * 104_729) % 97) as f32 / 97.0
                        - 0.5)
                        * 0.6;
                let segment = ((v - 0.2) * 26.0).sin().abs().powf(0.4);
                let spots = ((u * 61.0).sin() * (v * 47.0).sin()).abs().powf(3.0);
                let shade = 1.0 - 0.45 * ((u - 0.5) / 0.36).powi(2);
                let l = ((0.18 + 0.42 * segment - 0.25 * spots) * shade + 0.3 * fine * sharp)
                    .clamp(0.0, 1.0);
                [
                    (34.0 + 175.0 * l) as u8,
                    (26.0 + 128.0 * l) as u8,
                    (18.0 + 80.0 * l) as u8,
                ]
            }
        }
    }

    fn render(&self, plane: u64, size: [u32; 2], px: f32) -> Vec<u8> {
        let [w, h] = size.map(|s| s as usize);
        let mut rgb = vec![0u8; w * h * 3];
        rgb.par_chunks_mut(w * 3).enumerate().for_each(|(y, row)| {
            let v = (y as f32 + 0.5) / h as f32;
            for x in 0..w {
                let u = (x as f32 + 0.5) / w as f32;
                row[3 * x..3 * x + 3].copy_from_slice(&self.shade(u, v, plane as f32, px));
            }
        });
        rgb
    }

    /// The fixture's findings for a try, made to match its verdict.
    fn findings_for(&self, key: TryKey) -> Findings {
        let reason = self.reasons.get(&key).cloned().flatten();
        let r = reason.as_deref().unwrap_or("");
        let parities = !r.contains("CFA parities");
        let tile = 64;
        let grid = [
            (self.size[0] as usize).div_ceil(tile),
            (self.size[1] as usize).div_ceil(tile),
        ];
        let motion = r.contains("witness tiles disagree");
        let z2: Vec<f32> = if parities {
            (0..grid[0] * grid[1])
                .map(|i| {
                    let (x, y) = ((i % grid[0]) as f32, (i / grid[0]) as f32);
                    let noise = 0.9 + 0.2 * (((i * 2_654_435_761) % 1000) as f32 / 1000.0);
                    let (cx, cy) = (grid[0] as f32 * 0.62, grid[1] as f32 * 0.42);
                    let d2 = ((x - cx) / (0.08 * grid[0] as f32)).powi(2)
                        + ((y - cy) / (0.08 * grid[1] as f32)).powi(2);
                    if motion {
                        noise + 8.0 * (-d2).exp()
                    } else {
                        noise
                    }
                })
                .collect()
        } else {
            Vec::new()
        };
        let mut sorted = z2.clone();
        sorted.sort_by(f32::total_cmp);
        let q = |p: f64| {
            f64::from(
                sorted
                    .get(((sorted.len().max(1) - 1) as f64 * p) as usize)
                    .copied()
                    .unwrap_or(f32::NAN),
            )
        };
        // The same picture in photosites: about 0.1 px of noise, and the
        // moved patch well over the limit.
        let local: Vec<f32> = z2
            .iter()
            .map(|z| {
                if *z > 2.0 {
                    LOCAL_LIMIT as f32 * (z / 2.0).sqrt()
                } else {
                    0.1 * z.sqrt()
                }
            })
            .collect();
        // The fixture's frame is a few tiles across, so a moved patch is
        // one tile: its p99 is the largest.
        let local_px = {
            let mut s = local.clone();
            s.sort_by(f32::total_cmp);
            let at = if motion { 1.0 } else { 0.99 };
            s.get(((s.len().max(1) - 1) as f64 * at) as usize)
                .map_or(f64::NAN, |v| f64::from(*v))
        };
        let misregistered = r.contains("misregistered");
        let shift = if misregistered { 0.21 } else { 0.04 };
        Findings {
            offsets: if parities {
                [(0, 0), (0, -1), (1, -1), (1, 0)]
            } else {
                [(0, 0), (0, -1), (1, -1), (1, 1)]
            },
            gains: [1.0, 1.0002, 0.9992, 0.9976],
            structure: [1.0, 0.994, 0.993, 0.99],
            parities,
            reason,
            retake: motion,
            tile,
            grid: if parities { grid } else { [0, 0] },
            median: q(0.5) as f32,
            quadrants: [
                [[shift, -0.02], [0.03, shift * 0.8]],
                [[shift * 0.9, 0.01], [0.02, shift]],
                [[shift * 1.1, -0.03], [0.01, shift * 0.7]],
                [[shift, 0.02], [-0.02, shift * 0.9]],
            ],
            pair_shift: [[shift, -0.01], [0.01, shift * 0.85]],
            mean_z2: q(0.5),
            z2,
            local,
            local_px,
        }
    }
}

impl Source for FixtureSource {
    fn map(&self, t: &PlaneTry) -> Option<([usize; 2], [usize; 2], Vec<u16>)> {
        let [w, h] = self.size.map(|v| v as usize);
        let s = MAP_SIDE as f32 / w.max(h) as f32;
        let preview = [(w as f32 * s) as usize, (h as f32 * s) as usize];
        let cell = preview[0].max(preview[1]).div_ceil(MAP_CELLS);
        let grid = [preview[0].div_ceil(cell), preview[1].div_ceil(cell)];
        let cells = (0..grid[0] * grid[1])
            .map(|i| {
                let u = ((i % grid[0]) as f32 + 0.5) * cell as f32 / preview[0] as f32;
                let v = ((i / grid[0]) as f32 + 0.5) * cell as f32 / preview[1] as f32;
                encode(match self.depth(u.min(1.0), v.min(1.0)) {
                    Some(d) => 20.0 + 2000.0 * (-((d - t.plane as f32) / 4.0).powi(2)).exp(),
                    None => 2.0,
                })
            })
            .collect();
        Some((preview, grid, cells))
    }
    fn poll(&mut self) -> Vec<PlaneTry> {
        if std::mem::replace(&mut self.given, true) {
            Vec::new()
        } else {
            self.tries.clone()
        }
    }
    fn preview_of(&self, t: &PlaneTry, side: u32) -> Result<([usize; 2], Vec<u8>, [u32; 2])> {
        let [w, h] = self.size;
        let s = side as f32 / w.max(h) as f32;
        let size = [(w as f32 * s) as u32, (h as f32 * s) as u32];
        let rgb = self.render(t.plane, size, 900.0 * s * w as f32 / 6000.0);
        let rgba = rgb
            .as_chunks::<3>()
            .0
            .iter()
            .flat_map(|p| [p[0], p[1], p[2], 255])
            .collect();
        Ok(([size[0] as usize, size[1] as usize], rgba, self.size))
    }
    fn full(
        &self,
        t: &PlaneTry,
        gain: Option<f32>,
        abort: &dyn Fn() -> bool,
        _buffers: &mut Buffers,
    ) -> Result<Developed> {
        ensure!(!abort(), "superseded");
        let started = Instant::now();
        let f = self.findings_for(t.key());
        let rgb = self.render(t.plane, self.size, 900.0 * self.size[0] as f32 / 6000.0);
        Ok(Developed {
            size: self.size,
            rgb,
            kind: if f.parities {
                ImageKind::FourShot
            } else {
                ImageKind::FirstShot
            },
            findings: Some(f),
            iso: Some(100.0),
            gain: gain.unwrap_or(1.0),
            decode_ms: started.elapsed().as_secs_f64() * 1000.0,
            check_ms: 0.0,
        })
    }
}

// ---------------------------------------------------------------------------
// Textures

/// A texture uploaded off the UI thread: through the presenter (the window
/// and offscreen screenshots), else egui's own (tests).
pub(crate) enum TileTex {
    Layer(PhotoLayer),
    Handle(egui::TextureHandle),
}

impl TileTex {
    pub fn id(&self) -> Option<TextureId> {
        match self {
            Self::Layer(l) => l.texture_id(),
            Self::Handle(h) => Some(h.id()),
        }
    }
}

/// How textures reach the GPU.
#[derive(Clone)]
pub(crate) struct Uploader {
    pub presenter: Option<PhotoPresenter>,
    pub ctx: egui::Context,
}

impl Uploader {
    fn upload(&self, size: [u32; 2], rgba: &[u8], nearest: bool) -> Result<TileTex> {
        if let Some(p) = &self.presenter {
            return p
                .upload_sdr_slice(size, rgba, [[0.0, 0.0], [1.0, 1.0]], nearest)
                .map(TileTex::Layer);
        }
        let image =
            egui::ColorImage::from_rgba_unmultiplied([size[0] as usize, size[1] as usize], rgba);
        let options = egui::TextureOptions {
            magnification: if nearest {
                egui::TextureFilter::Nearest
            } else {
                egui::TextureFilter::Linear
            },
            ..egui::TextureOptions::LINEAR
        };
        Ok(TileTex::Handle(self.ctx.load_texture(
            "capture-plane-tile",
            image,
            options,
        )))
    }
}

/// A tile: `stride`, and its column and row at that stride.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub(crate) struct TileKey {
    pub stride: u32,
    pub x: u32,
    pub y: u32,
}

/// An uploaded tile: the source UV its core covers, and where that core is
/// in its texture (inside a one-texel apron).
pub(crate) struct TileEntry {
    pub tex: TileTex,
    pub core: Rect,
    pub uv: Rect,
    pub last: u64,
}

/// Cuts `key` out of `image`'s pyramid into `rgba` (RGBA with a
/// one-texel apron); returns its size, core and the core's texture UV.
pub(crate) fn cut(
    image: &PlaneImage,
    key: TileKey,
    rgba: &mut Vec<u8>,
) -> Option<([u32; 2], Rect, Rect)> {
    let level = image.level(key.stride)?;
    let [lw, lh] = level.size;
    let (x0, y0) = (key.x * TILE, key.y * TILE);
    if x0 >= lw || y0 >= lh {
        return None;
    }
    let (x1, y1) = ((x0 + TILE).min(lw), (y0 + TILE).min(lh));
    let (ax0, ay0) = (x0.saturating_sub(1), y0.saturating_sub(1));
    let (ax1, ay1) = ((x1 + 1).min(lw), (y1 + 1).min(lh));
    let (tw, th) = (ax1 - ax0, ay1 - ay0);
    rgba.clear();
    rgba.reserve((tw * th * 4) as usize);
    for y in ay0..ay1 {
        let row = &level.rgb[((y * lw + ax0) * 3) as usize..((y * lw + ax1) * 3) as usize];
        for p in row.as_chunks::<3>().0 {
            rgba.extend_from_slice(&[p[0], p[1], p[2], 255]);
        }
    }
    let s = key.stride as f32;
    let [w, h] = image.size.map(|v| v as f32);
    let core = Rect::from_min_max(
        egui::pos2(x0 as f32 * s / w, y0 as f32 * s / h),
        egui::pos2((x1 as f32 * s / w).min(1.0), (y1 as f32 * s / h).min(1.0)),
    );
    let uv = Rect::from_min_max(
        egui::pos2((x0 - ax0) as f32 / tw as f32, (y0 - ay0) as f32 / th as f32),
        egui::pos2((x1 - ax0) as f32 / tw as f32, (y1 - ay0) as f32 / th as f32),
    );
    Some(([tw, th], core, uv))
}

/// Cuts and uploads `key`.
fn upload_tile(
    up: &Uploader,
    image: &PlaneImage,
    key: TileKey,
    scratch: &mut Vec<u8>,
) -> Option<TileEntry> {
    let (size, core, uv) = step("cut a tile", || cut(image, key, scratch))?;
    let tex = step("upload a tile", || {
        up.upload(size, scratch, key.stride == 1)
    })
    .ok()?;
    Some(TileEntry {
        tex,
        core,
        uv,
        last: 0,
    })
}

/// Uploads `image`'s coarsest level whole.
fn upload_overview(up: &Uploader, image: &PlaneImage, scratch: &mut Vec<u8>) -> Result<TileEntry> {
    let level = image.overview();
    scratch.clear();
    scratch.extend(
        level
            .rgb
            .as_chunks::<3>()
            .0
            .iter()
            .flat_map(|p| [p[0], p[1], p[2], 255]),
    );
    let tex = step("upload the overview", || {
        up.upload(level.size, scratch, level.stride == 1)
    })?;
    let full = Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0));
    Ok(TileEntry {
        tex,
        core: full,
        uv: full,
        last: 0,
    })
}

// ---------------------------------------------------------------------------
// The deck: its worker threads and the UI's handle

/// What the view asks for.
#[derive(Clone, Debug, Default, PartialEq)]
struct Want {
    key: Option<TryKey>,
    /// The RAWs at full resolution; otherwise the camera's preview, which
    /// is all a fitted view of a passing plane shows.
    full: bool,
    /// Show the camera's preview first (not when following: the last plane
    /// stays until the next is ready).
    placeholder: bool,
    generation: u64,
}

/// The tiles in view when a build finishes: uploaded with it, so the new
/// picture replaces the old without a soft frame.
#[derive(Clone, Debug, Default)]
struct ViewTiles {
    size: [u32; 2],
    keys: Vec<TileKey>,
}

struct Shared {
    stop: AtomicBool,
    want: Mutex<Want>,
    wake: Condvar,
    /// Milliseconds since `epoch` the view was last painted.
    painted: AtomicU64,
    epoch: Instant,
    snapshot: Mutex<Arc<DeckSnapshot>>,
    uploader: Mutex<Option<Uploader>>,
    view: Mutex<ViewTiles>,
    /// Builds so far (picture ids).
    built: AtomicU64,
}

impl Shared {
    fn active(&self) -> bool {
        let now = self.epoch.elapsed().as_millis() as u64;
        let painted = self.painted.load(Ordering::Relaxed);
        painted > 0 && now.saturating_sub(painted) < ACTIVE.as_millis() as u64
    }
    fn generation(&self) -> u64 {
        self.want.lock().unwrap().generation
    }
}

/// What the UI let go of, freed on the deck's worker.
struct Retired {
    image: Option<Arc<PlaneImage>>,
    overview: Option<TileEntry>,
    tiles: Vec<TileEntry>,
}

/// A finished build, for the UI.
enum Built {
    Image {
        image: Arc<PlaneImage>,
        overview: TileEntry,
        tiles: Vec<(TileKey, TileEntry)>,
    },
    Failed(TryKey, String),
}

/// Tiles asked of the tile worker.
struct TileJob {
    image: Arc<PlaneImage>,
    keys: Vec<TileKey>,
}

/// A tile uploaded for picture `image`.
struct TileReady {
    image: u64,
    key: TileKey,
    entry: TileEntry,
}

/// The in-flight plane view's data: its workers and what they published.
pub(crate) struct PlaneDeck {
    shared: Arc<Shared>,
    pub run: PathBuf,
    snapshot: Arc<DeckSnapshot>,
    image: Option<Arc<PlaneImage>>,
    overview: Option<TileEntry>,
    tiles: HashMap<TileKey, TileEntry>,
    requested: HashSet<TileKey>,
    builds: mpsc::Receiver<Built>,
    /// Pictures and tiles replaced, to be freed on the worker (a 61 MP
    /// picture's pages take milliseconds to return).
    retire: mpsc::Sender<Retired>,
    tile_jobs: mpsc::Sender<TileJob>,
    tile_results: mpsc::Receiver<TileReady>,
    /// The last build that failed, and why.
    pub failed: Option<(TryKey, String)>,
    /// Milliseconds the last [`Self::poll`] took (performance checks).
    pub poll_ms: f64,
    frame: u64,
    want: Want,
}

impl PlaneDeck {
    /// The deck of the capture written to `run`.
    pub fn for_run(run: PathBuf, shots: u64) -> Self {
        Self::start(run.clone(), Box::new(RunSource::new(run, shots)))
    }

    /// A deck over any source.
    pub fn start(run: PathBuf, source: Box<dyn Source>) -> Self {
        let shared = Arc::new(Shared {
            stop: AtomicBool::new(false),
            want: Mutex::new(Want::default()),
            wake: Condvar::new(),
            painted: AtomicU64::new(0),
            epoch: Instant::now(),
            snapshot: Mutex::new(Arc::new(DeckSnapshot::default())),
            uploader: Mutex::new(None),
            view: Mutex::new(ViewTiles::default()),
            built: AtomicU64::new(0),
        });
        let (build_tx, builds) = mpsc::channel();
        let (retire, graveyard) = mpsc::channel::<Retired>();
        let (tile_jobs, job_rx) = mpsc::channel::<TileJob>();
        let (tile_tx, tile_results) = mpsc::channel();
        let worker = shared.clone();
        let _ = std::thread::Builder::new()
            .name("strehl-capture-planes".into())
            .spawn(move || {
                lower_priority();
                deck_worker(&worker, source, &build_tx, &graveyard);
            });
        let tiles = shared.clone();
        let tile_retire = retire.clone();
        let _ = std::thread::Builder::new()
            .name("strehl-capture-tiles".into())
            .spawn(move || {
                lower_priority();
                tile_worker(&tiles, &job_rx, &tile_tx, &tile_retire);
            });
        Self {
            shared,
            run,
            snapshot: Arc::new(DeckSnapshot::default()),
            image: None,
            overview: None,
            tiles: HashMap::new(),
            requested: HashSet::new(),
            builds,
            retire,
            tile_jobs,
            tile_results,
            failed: None,
            poll_ms: 0.0,
            frame: 0,
            want: Want::default(),
        }
    }

    /// How textures are uploaded (the presenter when the window has one).
    pub fn set_uploader(&self, presenter: Option<&PhotoPresenter>, ctx: &egui::Context) {
        let mut up = self.shared.uploader.lock().unwrap();
        if up.is_none() {
            *up = Some(Uploader {
                presenter: presenter.cloned(),
                ctx: ctx.clone(),
            });
        }
    }

    /// Takes what the workers published; returns whether anything changed.
    /// Reads no file and moves no pixels.
    pub fn poll(&mut self) -> bool {
        let started = Instant::now();
        self.frame += 1;
        let mut changed = false;
        let snap = self.shared.snapshot.lock().unwrap().clone();
        if snap.revision != self.snapshot.revision {
            self.snapshot = snap;
            changed = true;
        }
        while let Ok(built) = self.builds.try_recv() {
            changed = true;
            match built {
                Built::Image {
                    image,
                    overview,
                    tiles,
                } => {
                    self.failed = None;
                    let old = Retired {
                        image: self.image.replace(image),
                        overview: self.overview.replace(overview),
                        tiles: self.tiles.drain().map(|(_, t)| t).collect(),
                    };
                    let _ = self.retire.send(old);
                    self.requested.clear();
                    self.tiles.extend(tiles);
                }
                Built::Failed(key, e) => self.failed = Some((key, e)),
            }
        }
        while let Ok(ready) = self.tile_results.try_recv() {
            if self.image.as_ref().is_some_and(|i| i.id == ready.image) {
                self.requested.remove(&ready.key);
                self.tiles.insert(ready.key, ready.entry);
                changed = true;
            }
        }
        self.poll_ms = started.elapsed().as_secs_f64() * 1000.0;
        changed
    }

    pub fn snapshot(&self) -> &Arc<DeckSnapshot> {
        &self.snapshot
    }

    /// The picture shown (the newest built).
    pub fn image(&self) -> Option<&Arc<PlaneImage>> {
        self.image.as_ref()
    }

    pub fn overview(&self) -> Option<&TileEntry> {
        self.overview.as_ref()
    }

    pub fn tile(&self, key: &TileKey) -> Option<&TileEntry> {
        self.tiles.get(key)
    }

    /// Uploaded tiles (performance checks).
    #[allow(dead_code)]
    pub fn tile_count(&self) -> usize {
        self.tiles.len()
    }

    /// Asks for the try `key` (a new request supersedes a build in progress
    /// at its next member). The view calls this every frame it is painted.
    pub fn want(&mut self, key: Option<TryKey>, full: bool, placeholder: bool) {
        self.shared.painted.store(
            self.shared.epoch.elapsed().as_millis().max(1) as u64,
            Ordering::Relaxed,
        );
        if key == self.want.key && full == self.want.full {
            return;
        }
        let mut want = self.shared.want.lock().unwrap();
        want.key = key;
        want.full = full;
        want.placeholder = placeholder;
        want.generation += 1;
        self.want = want.clone();
        self.shared.wake.notify_all();
    }

    /// Asks for the tiles in view (stride and keys, centre first); uploads
    /// those not present on the tile worker. Marks them used, and drops the
    /// least recently used beyond the budget.
    pub fn demand(&mut self, keys: &[TileKey]) {
        let Some(image) = self.image.clone() else {
            return;
        };
        for k in keys {
            if let Some(t) = self.tiles.get_mut(k) {
                t.last = self.frame;
            }
        }
        {
            let mut view = self.shared.view.lock().unwrap();
            if view.keys != keys {
                view.size = image.size;
                view.keys = keys.to_vec();
            }
        }
        let missing: Vec<TileKey> = keys
            .iter()
            .filter(|k| !self.tiles.contains_key(k) && !self.requested.contains(k))
            .copied()
            .collect();
        if !missing.is_empty() {
            // Only what is in view now is wanted; older requests lapse.
            self.requested = missing.iter().copied().collect();
            let _ = self.tile_jobs.send(TileJob {
                image,
                keys: missing,
            });
        }
        if self.tiles.len() > keys.len() + TILE_BUDGET {
            let mut old: Vec<(u64, TileKey)> = self
                .tiles
                .iter()
                .filter(|(k, _)| !keys.contains(k))
                .map(|(k, t)| (t.last, *k))
                .collect();
            old.sort();
            let drop = self.tiles.len() - keys.len() - TILE_BUDGET;
            let tiles = old
                .into_iter()
                .take(drop)
                .filter_map(|(_, k)| self.tiles.remove(&k))
                .collect();
            let _ = self.retire.send(Retired {
                image: None,
                overview: None,
                tiles,
            });
        }
    }

    /// Whether the view has what it asked for: every try measured, the
    /// picture asked for built (or failed) and the tiles in view uploaded.
    pub fn settled(&self) -> bool {
        let snap = &self.snapshot;
        snap.polled
            && snap.pending == 0
            && match self.want.key {
                None => true,
                Some(k) => {
                    self.failed.as_ref().is_some_and(|(f, _)| *f == k)
                        || (self.image.as_ref().is_some_and(|i| {
                            i.key == k && (i.kind != ImageKind::Preview || !self.want.full)
                        }) && self.requested.is_empty())
                }
            }
    }

    /// Bytes of picture held by the shown image (performance checks).
    #[allow(dead_code)]
    pub fn resident(&self) -> usize {
        self.image.as_ref().map_or(0, |i| i.bytes())
    }
}

impl Drop for PlaneDeck {
    fn drop(&mut self) {
        self.shared.stop.store(true, Ordering::SeqCst);
        self.shared.wake.notify_all();
    }
}

/// The deck's worker: follows the source, measures each try's preview,
/// and builds the picture the view asks for.
fn deck_worker(
    shared: &Shared,
    mut source: Box<dyn Source>,
    out: &mpsc::Sender<Built>,
    graveyard: &mpsc::Receiver<Retired>,
) {
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(PLANE_THREADS)
        .thread_name(|i| format!("strehl-capture-plane-{i}"))
        .start_handler(|_| lower_priority())
        .build()
        .ok();
    let mut buffers = Buffers::default();
    // Texels for uploads, reused (4 MB a tile).
    let mut scratch = Vec::new();
    let mut snap = DeckSnapshot::default();
    let mut mapped = 0usize;
    let mut built_generation = 0u64;
    // The try whose picture the view was last sent, and whether it was
    // the full one.
    let mut last_built: Option<(TryKey, bool)> = None;
    // The sensor's pixels, once a full picture was built.
    let mut sensor: Option<[u32; 2]> = None;
    let mut gain: Option<f32> = None;
    let mut published = Instant::now();
    let mut dirty = false;
    loop {
        if shared.stop.load(Ordering::SeqCst) {
            return;
        }
        while let Ok(retired) = graveyard.try_recv() {
            // Benchmarks: `STREHL_BENCH_KEEP_TEXTURES` never destroys them.
            #[cfg(test)]
            if std::env::var_os("STREHL_BENCH_KEEP_TEXTURES").is_some() {
                std::mem::forget(retired.tiles);
                std::mem::forget(retired.overview);
                if let Some(image) = retired.image.and_then(|i| Arc::try_unwrap(i).ok()) {
                    buffers.reclaim(image);
                }
                continue;
            }
            step("drop retired tiles", || {
                for t in retired.tiles.into_iter().chain(retired.overview) {
                    match t.tex {
                        TileTex::Layer(layer) => step("drop a layer", || drop(layer)),
                        TileTex::Handle(h) => drop(h),
                    }
                }
            });
            // Its pyramid's buffers serve the next build (the tile worker
            // hands back its own reference the same way).
            if let Some(image) = retired.image.and_then(|i| Arc::try_unwrap(i).ok()) {
                step("reclaim a picture", || buffers.reclaim(image));
            }
        }
        let new = step("follow the run", || source.poll());
        if !new.is_empty() {
            snap.tries.extend(new.into_iter().map(|t| TryInfo {
                t,
                map: None,
                share: None,
            }));
            dirty = true;
        }
        // The view's request first: it is what the user is looking at.
        let want = shared.want.lock().unwrap().clone();
        if shared.active()
            && want.generation != built_generation
            && let Some(key) = want.key
            && let Some(i) = snap.index(key)
        {
            // Asked again for the picture it shows (picked away and back
            // before anything else was sent): nothing to do.
            if last_built.is_some_and(|(k, full)| k == key && (full || !want.full)) {
                built_generation = want.generation;
                continue;
            }
            let t = snap.tries[i].t.clone();
            let uploader = shared.uploader.lock().unwrap().clone();
            if let Some(up) = uploader {
                if (want.placeholder || !want.full)
                    && let Ok((size, rgba, made_from)) =
                        step("read a preview", || source.preview_of(&t, 2048))
                {
                    let rgb: Vec<u8> = rgba
                        .as_chunks::<4>()
                        .0
                        .iter()
                        .flat_map(|p| [p[0], p[1], p[2]])
                        .collect();
                    let size = [size[0] as u32, size[1] as u32];
                    let image = PlaneImage {
                        id: shared.built.fetch_add(1, Ordering::Relaxed) + 1,
                        key,
                        size,
                        // A preview made from a picture of the sensor's
                        // aspect stands for that picture's pixels.
                        frame: sensor.unwrap_or(
                            if made_from[0] * size[1] == made_from[1] * size[0]
                                || made_from[0] > size[0]
                            {
                                made_from
                            } else {
                                size
                            },
                        ),
                        levels: pyramid(size, rgb, &mut buffers),
                        kind: ImageKind::Preview,
                        findings: None,
                        iso: None,
                        display_ev: 0.0,
                        cost: [0.0; 3],
                    };
                    send_image(shared, &up, image, out, &mut scratch);
                    last_built = Some((key, false));
                }
                if !want.full {
                    // The preview is the picture: no RAW is read.
                    built_generation = want.generation;
                    continue;
                }
                // Settle: a newer request (scrubbing) skips this build.
                let deadline = Instant::now() + SETTLE;
                let mut guard = shared.want.lock().unwrap();
                while guard.generation == want.generation && Instant::now() < deadline {
                    guard = shared
                        .wake
                        .wait_timeout(guard, deadline.saturating_duration_since(Instant::now()))
                        .unwrap()
                        .0;
                }
                let newer = guard.generation != want.generation;
                drop(guard);
                if newer {
                    continue;
                }
                built_generation = want.generation;
                // Benchmarks: `STREHL_BENCH_NO_BUILD` reads no RAW.
                #[cfg(test)]
                if std::env::var_os("STREHL_BENCH_NO_BUILD").is_some() {
                    continue;
                }
                let started = Instant::now();
                let abort = || {
                    shared.stop.load(Ordering::Relaxed) || shared.generation() != want.generation
                };
                let result = match &pool {
                    Some(pool) => pool.install(|| source.full(&t, gain, &abort, &mut buffers)),
                    None => source.full(&t, gain, &abort, &mut buffers),
                };
                match result {
                    Ok(d) => {
                        gain.get_or_insert(d.gain);
                        let size = d.size;
                        let rgb = d.rgb;
                        let levels = step("pyramid", || match &pool {
                            Some(pool) => pool.install(|| pyramid(size, rgb, &mut buffers)),
                            None => pyramid(size, rgb, &mut buffers),
                        });
                        let total = started.elapsed().as_secs_f64() * 1000.0;
                        sensor = Some(size);
                        let image = PlaneImage {
                            id: shared.built.fetch_add(1, Ordering::Relaxed) + 1,
                            key,
                            size,
                            frame: size,
                            levels,
                            kind: d.kind,
                            findings: d.findings,
                            iso: d.iso,
                            display_ev: d.gain.log2(),
                            cost: [
                                d.decode_ms,
                                d.check_ms,
                                (total - d.decode_ms - d.check_ms).max(0.0),
                            ],
                        };
                        if !abort() {
                            send_image(shared, &up, image, out, &mut scratch);
                            last_built = Some((key, true));
                        }
                    }
                    Err(e) => {
                        if !abort() {
                            let _ = out.send(Built::Failed(key, format!("{e:#}")));
                            step("request a repaint", || up.ctx.request_repaint());
                        }
                    }
                }
                continue;
            }
        }
        // Previews: a few at a time, so a request is never long behind.
        let end = (mapped + 8).min(snap.tries.len());
        for i in mapped..end {
            if shared.stop.load(Ordering::SeqCst) {
                return;
            }
            let measured = source.map(&snap.tries[i].t).map(Ok).unwrap_or_else(|| {
                step("read a preview", || {
                    source.preview(&snap.tries[i].t, MAP_SIDE)
                })
                .map(|(size, rgba)| {
                    let (grid, cells) = step("focus map", || focus_map(&rgba, size));
                    (size, grid, cells)
                })
            });
            match measured {
                Ok((size, grid, cells)) => {
                    if snap.grid == [0, 0] {
                        snap.grid = grid;
                        snap.preview = size;
                    }
                    if grid == snap.grid {
                        snap.tries[i].map = Some(cells.into());
                    }
                }
                Err(e) => {
                    snap.unreadable += 1;
                    snap.note = Some(format!("{e:#}"));
                }
            }
        }
        if end > mapped {
            mapped = end;
            dirty = true;
        }
        let caught_up = mapped == snap.tries.len();
        if !snap.polled {
            snap.polled = true;
            dirty = true;
        }
        if dirty && (caught_up || published.elapsed() > Duration::from_secs(1)) {
            snap.pending = snap.tries.len() - mapped;
            step("publish the tries", || {
                summarize(&mut snap);
                snap.revision += 1;
                *shared.snapshot.lock().unwrap() = Arc::new(snap.clone());
            });
            if let Some(up) = shared.uploader.lock().unwrap().as_ref() {
                step("request a repaint", || up.ctx.request_repaint());
            }
            published = Instant::now();
            dirty = false;
        }
        if caught_up {
            let guard = shared.want.lock().unwrap();
            if guard.generation == built_generation || !shared.active() {
                let _ = shared.wake.wait_timeout(guard, Duration::from_millis(250));
            } else {
                drop(guard);
                std::thread::sleep(Duration::from_millis(50));
            }
        }
    }
}

/// Uploads a new picture's overview and the tiles in view, and hands them
/// to the UI together.
fn send_image(
    shared: &Shared,
    up: &Uploader,
    image: PlaneImage,
    out: &mpsc::Sender<Built>,
    scratch: &mut Vec<u8>,
) {
    // Benchmarks: `STREHL_BENCH_NO_UPLOAD` builds but never shows.
    #[cfg(test)]
    if std::env::var_os("STREHL_BENCH_NO_UPLOAD").is_some() {
        return;
    }
    let Ok(overview) = upload_overview(up, &image, scratch) else {
        return;
    };
    let view = shared.view.lock().unwrap().clone();
    let tiles = if view.size == image.size {
        view.keys
            .iter()
            .filter_map(|k| upload_tile(up, &image, *k, scratch).map(|t| (*k, t)))
            .collect()
    } else {
        Vec::new()
    };
    let _ = out.send(Built::Image {
        image: Arc::new(image),
        overview,
        tiles,
    });
    step("request a repaint", || up.ctx.request_repaint());
}

/// The tile worker: cuts and uploads the tiles the view asks for, the
/// newest request first.
fn tile_worker(
    shared: &Shared,
    jobs: &mpsc::Receiver<TileJob>,
    out: &mpsc::Sender<TileReady>,
    retire: &mpsc::Sender<Retired>,
) {
    let hand_back = |job: TileJob| {
        let _ = retire.send(Retired {
            image: Some(job.image),
            overview: None,
            tiles: Vec::new(),
        });
    };
    let mut next: Option<TileJob> = None;
    let mut scratch = Vec::new();
    loop {
        let job = match next.take() {
            Some(j) => j,
            None => match jobs.recv() {
                Ok(j) => j,
                Err(_) => return,
            },
        };
        let mut job = job;
        while let Ok(newer) = jobs.try_recv() {
            hand_back(std::mem::replace(&mut job, newer));
        }
        let Some(up) = shared.uploader.lock().unwrap().clone() else {
            hand_back(job);
            continue;
        };
        for key in &job.keys {
            if shared.stop.load(Ordering::Relaxed) {
                return;
            }
            if let Ok(newer) = jobs.try_recv() {
                next = Some(newer);
                break;
            }
            if let Some(entry) = upload_tile(&up, &job.image, *key, &mut scratch) {
                let _ = out.send(TileReady {
                    image: job.image.id,
                    key: *key,
                    entry,
                });
                step("request a repaint", || up.ctx.request_repaint());
            }
        }
        hand_back(job);
    }
}

/// A check that `rect` is a usable UV rectangle (tests).
#[cfg(test)]
pub(crate) fn unit(rect: Rect) -> bool {
    rect.min.x >= 0.0 && rect.min.y >= 0.0 && rect.max.x <= 1.0 && rect.max.y <= 1.0
}

#[cfg(test)]
#[path = "capture-planes-tests.rs"]
mod tests;
