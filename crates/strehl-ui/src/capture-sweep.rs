//! The calibration's live sweep (capture calibration spec 4.1 and 5.3,
//! ledger row `cpf-s1-sweep`): the lens is moved across a window, the
//! preview read after each move, and each tile's focus read from the
//! position of its PEAK.
//!
//! The host's bounds survey (`strehl-capture/src/bounds.rs`) reads where a
//! tile's curve is above half its height; on the dragonfly of 2026-11-26 that
//! put the range 575 units too early and 1,090 too late, because a preview
//! tile's curve is nine or more sharp depths wide. Its peak is not: one sweep
//! of 33 positions over 6,080 units placed the range within 18 units, and
//! half the tiles within 14 to 17 units of their RAW focus (MEASURED,
//! `experiments/capture-planning-flow-2026-11-26/grounding/results.md` R2.4;
//! reference `scripts/live-sweep.py`).
//!
//! Per frame, on the preview's luma: a Gaussian of 1 px, the squared
//! gradient, its mean and the luma's over [`TILE`] px tiles, and the tile
//! measure `E / (Lnear^2 + LEVEL_FLOOR^2)` with `Lnear` the brightest tile
//! luma in the 3 x 3 around. Across the sweep, per tile: the curve smoothed
//! over [`SMOOTH_UNITS`], a peak when its largest value is over
//! [`PEAK_OVER_FLOOR`] times its 15th percentile and not at either end, its
//! position the vertex of the parabola through it and its neighbours; a peak
//! kept when it lies within two sharp depths of its neighbours' median.

// `!(x > limit)` is deliberate: it also rejects NaN.
#![allow(clippy::neg_cmp_op_on_partial_ord)]

use eframe::egui;
use std::time::{Duration, Instant};

use crate::capture_client::Snapshot;

/// Tile side, preview pixels.
pub(crate) const TILE: usize = 32;
/// The luma floor under the level (0..1 luma).
pub(crate) const LEVEL_FLOOR: f32 = 0.03;
/// The curve is smoothed along focus over this many units (at least 0.7
/// samples).
pub(crate) const SMOOTH_UNITS: f64 = 40.0;
/// A peak stands this many times over the curve's 15th percentile.
pub(crate) const PEAK_OVER_FLOOR: f32 = 3.0;
/// A kept peak lies within this many sharp depths of its neighbours' median.
pub(crate) const COHERENCE_DEPTHS: f64 = 2.0;
/// Positions in a sweep, and the window's half-width in focus units.
pub(crate) const POSITIONS: usize = 33;
pub(crate) const HALF_WINDOW: u16 = 3000;
/// Fewer kept peaks than this: nothing found.
pub(crate) const MIN_TILES: usize = 8;
/// Running off an end: this share of the prominent tiles peak at the
/// window's first or last position.
pub(crate) const OFF_END_SHARE: f64 = 0.03;
/// A kept peak has at least this many neighbours with peaks (3 x 3), and
/// an end of the range at least this many others within two sharp depths.
pub(crate) const MIN_NEIGHBOURS: usize = 2;
/// An end-peaking tile counts with this many end-peaking neighbours.
pub(crate) const END_NEIGHBOURS: usize = 3;
/// Every move arrives from below, as a capture's do.
pub(crate) const APPROACH: u16 = 128;
/// How long one position may take before its latest frame is used.
pub(crate) const POSITION_TIMEOUT: Duration = Duration::from_secs(8);

/// One frame's tile measure.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct FrameTiles {
    pub position: f64,
    pub cols: usize,
    pub rows: usize,
    pub m: Vec<f32>,
}

/// Luma of a preview frame, 0..1 (Rec. 709 weights on the camera's sRGB).
pub(crate) fn luma(image: &egui::ColorImage) -> (Vec<f32>, usize, usize) {
    let [w, h] = image.size;
    let l = image
        .pixels
        .iter()
        .map(|p| {
            (0.2126 * f32::from(p.r()) + 0.7152 * f32::from(p.g()) + 0.0722 * f32::from(p.b()))
                / 255.0
        })
        .collect();
    (l, w, h)
}

/// A 1 px Gaussian (radius 4), edges clamped, separably.
fn smooth(src: &[f32], w: usize, h: usize) -> Vec<f32> {
    let k: Vec<f32> = (-4i32..=4).map(|i| (-(i * i) as f32 / 2.0).exp()).collect();
    let sum: f32 = k.iter().sum();
    let k: Vec<f32> = k.iter().map(|v| v / sum).collect();
    let mut tmp = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut a = 0.0;
            for (i, kv) in k.iter().enumerate() {
                let xx = (x as i64 + i as i64 - 4).clamp(0, w as i64 - 1) as usize;
                a += kv * src[y * w + xx];
            }
            tmp[y * w + x] = a;
        }
    }
    let mut out = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut a = 0.0;
            for (i, kv) in k.iter().enumerate() {
                let yy = (y as i64 + i as i64 - 4).clamp(0, h as i64 - 1) as usize;
                a += kv * tmp[yy * w + x];
            }
            out[y * w + x] = a;
        }
    }
    out
}

/// The tile measure of one frame (spec 5.3 points 1 and 2).
pub(crate) fn frame_tiles(luma: &[f32], w: usize, h: usize, position: f64) -> FrameTiles {
    let sm = smooth(luma, w, h);
    let (cols, rows) = (w / TILE, h / TILE);
    let mut e = vec![0.0f64; cols * rows];
    let mut l = vec![0.0f64; cols * rows];
    for y in 0..rows * TILE {
        for x in 0..cols * TILE {
            // Central differences, one-sided at the frame's edges.
            let at = |x: usize, y: usize| sm[y * w + x];
            let gx = if x == 0 {
                at(1, y) - at(0, y)
            } else if x + 1 == w {
                at(x, y) - at(x - 1, y)
            } else {
                0.5 * (at(x + 1, y) - at(x - 1, y))
            };
            let gy = if y == 0 {
                at(x, 1) - at(x, 0)
            } else if y + 1 == h {
                at(x, y) - at(x, y - 1)
            } else {
                0.5 * (at(x, y + 1) - at(x, y - 1))
            };
            let t = (y / TILE) * cols + x / TILE;
            e[t] += f64::from(gx * gx + gy * gy);
            l[t] += f64::from(at(x, y));
        }
    }
    let n = (TILE * TILE) as f64;
    let m = (0..cols * rows)
        .map(|t| {
            let (tx, ty) = (t % cols, t / cols);
            let mut near = 0.0f64;
            for yy in ty.saturating_sub(1)..(ty + 2).min(rows) {
                for xx in tx.saturating_sub(1)..(tx + 2).min(cols) {
                    near = near.max(l[yy * cols + xx] / n);
                }
            }
            let floor = f64::from(LEVEL_FLOOR);
            (e[t] / n / (near * near + floor * floor)) as f32
        })
        .collect();
    FrameTiles {
        position,
        cols,
        rows,
        m,
    }
}

/// What a sweep found.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Peaks {
    pub cols: usize,
    pub rows: usize,
    /// Per tile, row-major: the kept peak's focus, offset applied.
    pub focus: Vec<Option<f64>>,
    /// The smallest and largest kept peak.
    pub range: Option<(f64, f64)>,
    /// The mode of the kept peaks in bins of a sharp depth (its bin's centre).
    pub busiest: Option<f64>,
    /// Kept peaks, and the prominent tiles that peaked at the window's first
    /// or last position among [`END_NEIGHBOURS`] that did too (the subject
    /// may go on past it), with all prominent.
    pub kept: usize,
    pub at_first: usize,
    pub at_last: usize,
    pub prominent: usize,
    /// The window, and the offset added.
    pub window: (f64, f64),
    pub offset: f64,
}

impl Peaks {
    /// Too few kept peaks: nothing in focus in the window.
    pub fn nothing(&self) -> bool {
        self.kept < MIN_TILES
    }
    /// Kept peaks by sweep position (`[position, tiles]`, the window cut in
    /// equal steps, the offset taken off): what the rail draws and a run's
    /// record shows.
    pub fn histogram(&self) -> Vec<[f64; 2]> {
        let (a, b) = self.window;
        let n = POSITIONS.max(2);
        let step = (b - a) / (n - 1) as f64;
        let mut counts = vec![0usize; n];
        for v in self.focus.iter().flatten() {
            let i = ((v - self.offset - a) / step.max(1.0)).round();
            if i >= 0.0 && (i as usize) < n {
                counts[i as usize] += 1;
            }
        }
        counts
            .iter()
            .enumerate()
            .map(|(i, c)| [a + step * i as f64, *c as f64])
            .collect()
    }
    /// The subject runs off the window's low (-1) or high (+1) end.
    pub fn off_end(&self) -> Option<i8> {
        let share = |n: usize| n as f64 / self.prominent.max(1) as f64;
        if share(self.at_last) >= OFF_END_SHARE && self.at_last >= self.at_first {
            Some(1)
        } else if share(self.at_first) >= OFF_END_SHARE {
            Some(-1)
        } else {
            None
        }
    }
}

/// Quantile with linear interpolation (numpy's default).
fn quantile(v: &mut [f32], q: f32) -> f32 {
    v.sort_by(f32::total_cmp);
    let pos = q * (v.len().max(1) - 1) as f32;
    let k = pos.floor() as usize;
    match v.get(k + 1) {
        Some(&hi) => v[k] + (hi - v[k]) * (pos - k as f32),
        None => v.get(k).copied().unwrap_or(0.0),
    }
}

fn median_f64(mut v: Vec<f64>) -> Option<f64> {
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

/// The sweep's peaks (spec 5.3 points 3 to 7): `w0` the sharp depth the
/// coherence and the bins use, `offset` the lens's coarse-to-fine offset.
pub(crate) fn peaks(frames: &[FrameTiles], w0: f64, offset: f64) -> Option<Peaks> {
    let first = frames.first()?;
    let (cols, rows) = (first.cols, first.rows);
    if frames.len() < 5 || frames.iter().any(|f| (f.cols, f.rows) != (cols, rows)) {
        return None;
    }
    let mut order: Vec<usize> = (0..frames.len()).collect();
    order.sort_by(|&a, &b| frames[a].position.total_cmp(&frames[b].position));
    let pos: Vec<f64> = order.iter().map(|&i| frames[i].position).collect();
    let p = pos.len();
    let spacing = median_f64(pos.windows(2).map(|w| w[1] - w[0]).collect())?.max(1.0);
    // The Gaussian along focus (truncated at four sigma, edges clamped).
    let sigma = (SMOOTH_UNITS / spacing).max(0.7);
    let r = (4.0 * sigma).ceil() as i64;
    let k: Vec<f64> = (-r..=r)
        .map(|i| (-(i * i) as f64 / (2.0 * sigma * sigma)).exp())
        .collect();
    let ksum: f64 = k.iter().sum();
    let tiles = cols * rows;
    let mut est = vec![None; tiles];
    // Prominent tiles peaking at the window's first (-1) or last (+1) frame.
    let mut end = vec![0i8; tiles];
    let mut prominent = 0;
    for (t, slot) in est.iter_mut().enumerate() {
        let raw: Vec<f64> = order.iter().map(|&i| f64::from(frames[i].m[t])).collect();
        let c: Vec<f32> = (0..p as i64)
            .map(|i| {
                let mut a = 0.0;
                for (j, kv) in k.iter().enumerate() {
                    let q = (i + j as i64 - r).clamp(0, p as i64 - 1) as usize;
                    a += kv * raw[q];
                }
                (a / ksum) as f32
            })
            .collect();
        let (kmax, peak) = c
            .iter()
            .enumerate()
            .fold((0, f32::MIN), |b, (i, &v)| if v > b.1 { (i, v) } else { b });
        let mut sorted = c.clone();
        let floor = quantile(&mut sorted, 0.15).max(1e-9);
        if !(peak > PEAK_OVER_FLOOR * floor) {
            continue;
        }
        prominent += 1;
        if kmax == 0 {
            end[t] = -1;
            continue;
        }
        if kmax + 1 == p {
            end[t] = 1;
            continue;
        }
        let (y0, y1, y2) = (
            f64::from(c[kmax - 1]),
            f64::from(c[kmax]),
            f64::from(c[kmax + 1]),
        );
        let d = y0 - 2.0 * y1 + y2;
        let vertex = if d.abs() > 1e-12 {
            0.5 * (y0 - y2) / d
        } else {
            0.0
        };
        *slot = Some(pos[kmax] + vertex * spacing);
    }
    // A subject running past an end peaks there over an area; a stray tile
    // (backdrop, a defocused highlight) alone (MEASURED on the dragonfly's
    // sweep: 16 of 450 prominent tiles peaked at the far end, 2,400 units
    // past the subject, none with three such neighbours).
    let clustered = |t: usize, side: i8| {
        let (tx, ty) = (t % cols, t / cols);
        let mut n = 0;
        for yy in ty.saturating_sub(1)..(ty + 2).min(rows) {
            for xx in tx.saturating_sub(1)..(tx + 2).min(cols) {
                n += usize::from(yy * cols + xx != t && end[yy * cols + xx] == side);
            }
        }
        n >= END_NEIGHBOURS
    };
    let at_first = (0..tiles)
        .filter(|&t| end[t] == -1 && clustered(t, -1))
        .count();
    let at_last = (0..tiles)
        .filter(|&t| end[t] == 1 && clustered(t, 1))
        .count();
    // Coherence: within two sharp depths of the 3 x 3 neighbourhood's median.
    let focus: Vec<Option<f64>> = (0..tiles)
        .map(|t| {
            let v = est[t]?;
            let (tx, ty) = (t % cols, t / cols);
            let mut near = Vec::with_capacity(9);
            for yy in ty.saturating_sub(1)..(ty + 2).min(rows) {
                for xx in tx.saturating_sub(1)..(tx + 2).min(cols) {
                    if let Some(e) = est[yy * cols + xx] {
                        near.push(e);
                    }
                }
            }
            // A lone peak has itself for a median: it needs neighbours
            // (MEASURED on the rig, 2026-11-27: one stray tile 1,000 units
            // before the subject set the sweep's near end).
            if near.len() < 1 + MIN_NEIGHBOURS {
                return None;
            }
            let m = median_f64(near)?;
            ((v - m).abs() <= COHERENCE_DEPTHS * w0).then_some(v + offset)
        })
        .collect();
    let kept: Vec<f64> = focus.iter().flatten().copied().collect();
    // The range: peaks with company in depth too (two others within two
    // sharp depths), so one tile alone at its depth does not move an end.
    let mut sorted = kept.clone();
    sorted.sort_by(f64::total_cmp);
    let reach = COHERENCE_DEPTHS * w0;
    let supported: Vec<f64> = sorted
        .iter()
        .enumerate()
        .filter(|(i, v)| {
            let lo = sorted.partition_point(|x| *x < **v - reach);
            let hi = sorted.partition_point(|x| *x <= **v + reach);
            hi - lo > MIN_NEIGHBOURS && *i < sorted.len()
        })
        .map(|(_, v)| *v)
        .collect();
    let range = supported
        .iter()
        .copied()
        .fold(None, |r: Option<(f64, f64)>, v| match r {
            None => Some((v, v)),
            Some((a, b)) => Some((a.min(v), b.max(v))),
        });
    let busiest = range.and_then(|(lo, _)| {
        let bin = w0.max(1.0);
        let mut counts: std::collections::BTreeMap<i64, usize> = Default::default();
        for v in &kept {
            *counts.entry(((v - lo) / bin).floor() as i64).or_default() += 1;
        }
        counts
            .iter()
            .max_by(|a, b| a.1.cmp(b.1).then(b.0.cmp(a.0)))
            .map(|(b, _)| lo + (*b as f64 + 0.5) * bin)
    });
    Some(Peaks {
        cols,
        rows,
        kept: kept.len(),
        focus,
        range,
        busiest,
        at_first,
        at_last,
        prominent,
        window: (pos[0], pos[p - 1]),
        offset,
    })
}

/// The sweep's window (spec 4.1): `POSITIONS` positions over
/// `HALF_WINDOW` either side of `seed`, inside `reach`.
pub(crate) fn window(seed: u16, reach: (u16, u16)) -> Vec<u16> {
    let (near, far) = (i64::from(reach.0), i64::from(reach.1.max(reach.0)));
    let half = i64::from(HALF_WINDOW);
    let (mut lo, mut hi) = (i64::from(seed) - half, i64::from(seed) + half);
    if lo < near {
        hi = (hi + (near - lo)).min(far);
        lo = near;
    }
    if hi > far {
        lo = (lo - (hi - far)).max(near);
        hi = far;
    }
    let n = POSITIONS as i64;
    let mut v: Vec<u16> = (0..n)
        .map(|i| (lo + (hi - lo) * i / (n - 1)).clamp(0, 65535) as u16)
        .collect();
    v.dedup();
    v
}

/// What the driver asks of the workspace this frame.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum Step {
    /// Send this move.
    Move(u16),
    Wait,
    /// Every position has its frame.
    Done,
    Failed(String),
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum Phase {
    /// The move below the first position, sent.
    Approach { sent: Instant },
    /// A move to `positions[next]`, sent.
    Moving { sent: Instant },
    /// At the position: the generation seen on arrival.
    Waiting { since: Instant, arrived: u64 },
}

/// The sweep, driven once a frame.
pub(crate) struct Sweep {
    pub positions: Vec<u16>,
    next: usize,
    phase: Option<Phase>,
    pub frames: Vec<FrameTiles>,
    /// Frames being measured off the UI thread (about 20 ms each).
    measuring: Vec<crate::jobs::Task<FrameTiles>>,
    /// Every position has its frame; waiting for the last measures.
    taken: bool,
    pub started: Instant,
    /// The preview frame kept at the busiest position (the lens's picture
    /// under the Depth lens), and the last frame's size.
    pub size: Option<[usize; 2]>,
}

impl Sweep {
    pub fn new(positions: Vec<u16>, now: Instant) -> Self {
        Self {
            positions,
            next: 0,
            phase: None,
            frames: Vec::new(),
            measuring: Vec::new(),
            taken: false,
            started: now,
            size: None,
        }
    }

    /// Positions done, of all.
    pub fn progress(&self) -> (usize, usize) {
        (self.next.min(self.positions.len()), self.positions.len())
    }

    /// Collects measured frames; an error ends the sweep.
    fn collect(&mut self) -> Result<(), String> {
        let mut still = Vec::new();
        for task in self.measuring.drain(..) {
            match task.receiver.try_recv() {
                Ok(Ok(f)) => self.frames.push(f),
                Ok(Err(e)) => return Err(e),
                Err(std::sync::mpsc::TryRecvError::Empty) => still.push(task),
                Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                    return Err("A sweep frame's measure stopped without a result".into());
                }
            }
        }
        self.measuring = still;
        Ok(())
    }

    pub fn poll(&mut self, s: &Snapshot, now: Instant) -> Step {
        if let Err(e) = self.collect() {
            return Step::Failed(e);
        }
        if self.taken {
            return if self.measuring.is_empty() {
                Step::Done
            } else {
                Step::Wait
            };
        }
        let host = &s.host;
        if !host.connected || !s.fresh() {
            return Step::Failed("The camera is not connected".into());
        }
        let Some(&first) = self.positions.first() else {
            return Step::Failed("No positions to sweep".into());
        };
        let position = host.position;
        let generation = s.preview.as_ref().map(|p| p.0);
        match self.phase {
            None => {
                self.phase = Some(Phase::Approach { sent: now });
                Step::Move(first.saturating_sub(APPROACH))
            }
            Some(Phase::Approach { sent }) => {
                if host.busy || position != Some(first.saturating_sub(APPROACH)) {
                    return self.waiting_move(sent, now);
                }
                self.phase = Some(Phase::Moving { sent: now });
                Step::Move(first)
            }
            Some(Phase::Moving { sent }) => {
                let target = self.positions[self.next];
                if host.busy || position != Some(target) {
                    return self.waiting_move(sent, now);
                }
                let Some(g) = generation else {
                    return Step::Failed("Live view is off: the sweep reads it".into());
                };
                self.phase = Some(Phase::Waiting {
                    since: now,
                    arrived: g,
                });
                Step::Wait
            }
            Some(Phase::Waiting { since, arrived }) => {
                // The first new frame may straddle the move: the second.
                let fresh = generation.is_some_and(|g| g >= arrived + 2);
                let late = now.duration_since(since) > POSITION_TIMEOUT;
                if !fresh && !late {
                    return Step::Wait;
                }
                let Some((_, image)) = s.preview.as_ref() else {
                    return Step::Failed("Live view is off: the sweep reads it".into());
                };
                let image = std::sync::Arc::clone(image);
                self.size = Some(image.size);
                let position = f64::from(self.positions[self.next]);
                self.measuring
                    .push(crate::jobs::spawn_task("strehl-sweep-frame", move |_| {
                        let (l, w, h) = luma(&image);
                        Ok(frame_tiles(&l, w, h, position))
                    }));
                self.next += 1;
                if self.next == self.positions.len() {
                    self.phase = None;
                    self.taken = true;
                    return Step::Wait;
                }
                self.phase = Some(Phase::Moving { sent: now });
                Step::Move(self.positions[self.next])
            }
        }
    }

    fn waiting_move(&self, sent: Instant, now: Instant) -> Step {
        if now.duration_since(sent) > Duration::from_secs(40) {
            Step::Failed("The lens did not reach its position".into())
        } else {
            Step::Wait
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A frame whose tiles of `focus` (per tile, `None`: flat) are in focus
    /// near it: fine detail falling off over `width` units.
    fn planted(focus: &[Option<f64>], cols: usize, position: f64, width: f64) -> FrameTiles {
        FrameTiles {
            position,
            cols,
            rows: focus.len() / cols,
            m: focus
                .iter()
                .map(|f| match f {
                    Some(f) => {
                        0.02 + (-(position - f).powi(2) / (2.0 * width * width)).exp() as f32
                    }
                    None => 0.02,
                })
                .collect(),
        }
    }

    #[test]
    fn two_planted_depths_come_back_as_two_populations() {
        // 10 x 6 tiles: the left half in focus at 32,400, the right at 33,000.
        let cols = 10;
        let focus: Vec<Option<f64>> = (0..60)
            .map(|t| Some(if t % cols < 5 { 32_400.0 } else { 33_000.0 }))
            .collect();
        let positions = window(32_700, (1509, 63_487));
        assert_eq!(positions.len(), POSITIONS);
        let frames: Vec<FrameTiles> = positions
            .iter()
            .map(|&p| planted(&focus, cols, f64::from(p), 250.0))
            .collect();
        let r = peaks(&frames, 45.0, 0.0).unwrap();
        assert!(!r.nothing());
        let left: Vec<f64> = (0..60)
            .filter(|t| t % cols < 5)
            .filter_map(|t| r.focus[t])
            .collect();
        let right: Vec<f64> = (0..60)
            .filter(|t| t % cols >= 5)
            .filter_map(|t| r.focus[t])
            .collect();
        assert!(left.iter().all(|f| (f - 32_400.0).abs() < 40.0), "{left:?}");
        assert!(
            right.iter().all(|f| (f - 33_000.0).abs() < 40.0),
            "{right:?}"
        );
        let (lo, hi) = r.range.unwrap();
        assert!((lo - 32_400.0).abs() < 40.0 && (hi - 33_000.0).abs() < 40.0);
        assert_eq!(r.off_end(), None);
    }

    #[test]
    fn a_stray_peak_unlike_its_neighbours_is_not_kept() {
        let cols = 10;
        let mut focus: Vec<Option<f64>> = vec![Some(32_700.0); 60];
        focus[25] = Some(30_500.0); // a backdrop highlight in the middle
        let positions = window(32_000, (1509, 63_487));
        let frames: Vec<FrameTiles> = positions
            .iter()
            .map(|&p| planted(&focus, cols, f64::from(p), 250.0))
            .collect();
        let r = peaks(&frames, 45.0, 27.0).unwrap();
        assert_eq!(r.focus[25], None);
        assert!(
            (r.focus[0].unwrap() - 32_727.0).abs() < 40.0,
            "the offset is added"
        );
    }

    #[test]
    fn a_flat_scene_finds_nothing_and_a_subject_past_the_end_says_so() {
        let cols = 10;
        let positions = window(32_000, (1509, 63_487));
        let flat: Vec<FrameTiles> = positions
            .iter()
            .map(|&p| planted(&[None; 60], cols, f64::from(p), 250.0))
            .collect();
        assert!(peaks(&flat, 45.0, 0.0).unwrap().nothing());
        // In focus just past the window's last position, 35,000.
        let past: Vec<FrameTiles> = positions
            .iter()
            .map(|&p| planted(&[Some(35_150.0); 60], cols, f64::from(p), 250.0))
            .collect();
        assert_eq!(peaks(&past, 45.0, 0.0).unwrap().off_end(), Some(1));
    }

    /// The dragonfly's real sweep of 2026-11-27 (33 positions 190 apart,
    /// two previews each), replayed: `STREHL_SWEEP_FRAMES=<folder of
    /// <position>-<k>.jpg>`. Spec S1's rig gate against the stack's in-focus
    /// range from contrast (32,374 to 33,174, F2): the far end within one
    /// sharp depth (48), the near end within two and a half (120).
    #[test]
    #[ignore = "needs the owner's sweep frames"]
    fn the_recorded_dragonfly_sweep_finds_its_range() {
        let Ok(dir) = std::env::var("STREHL_SWEEP_FRAMES") else {
            return;
        };
        let mut by: std::collections::BTreeMap<u32, Vec<std::path::PathBuf>> = Default::default();
        for e in std::fs::read_dir(&dir).unwrap() {
            let path = e.unwrap().path();
            let name = path.file_stem().unwrap().to_string_lossy().into_owned();
            if let Some((p, _)) = name.split_once('-')
                && let Ok(p) = p.parse()
            {
                by.entry(p).or_default().push(path);
            }
        }
        let frames: Vec<FrameTiles> = by
            .iter()
            .map(|(p, paths)| {
                let mut sum: Option<(Vec<f32>, usize, usize)> = None;
                for path in paths {
                    let im = image::open(path).unwrap().to_rgb8();
                    let (w, h) = (im.width() as usize, im.height() as usize);
                    let l: Vec<f32> = im
                        .pixels()
                        .map(|q| {
                            (0.2126 * f32::from(q[0])
                                + 0.7152 * f32::from(q[1])
                                + 0.0722 * f32::from(q[2]))
                                / 255.0
                        })
                        .collect();
                    sum = Some(match sum {
                        None => (l, w, h),
                        Some((a, w, h)) => (a.iter().zip(&l).map(|(x, y)| x + y).collect(), w, h),
                    });
                }
                let (a, w, h) = sum.unwrap();
                let n = paths.len() as f32;
                let mean: Vec<f32> = a.iter().map(|v| v / n).collect();
                frame_tiles(&mean, w, h, f64::from(*p))
            })
            .collect();
        let r = peaks(&frames, 45.0, 27.0).unwrap();
        let (lo, hi) = r.range.unwrap();
        eprintln!(
            "replayed: {} positions, {} kept of {} prominent, at the ends {} and {}, range {lo:.0} to {hi:.0}, busiest {:?}",
            frames.len(),
            r.kept,
            r.prominent,
            r.at_first,
            r.at_last,
            r.busiest
        );
        assert!((hi - 33_174.0).abs() <= 48.0, "far end {hi}");
        assert!((lo - 32_374.0).abs() <= 120.0, "near end {lo}");
        assert_eq!(r.off_end(), None);
    }

    #[test]
    fn the_window_stays_inside_the_lens() {
        let w = window(2_000, (1509, 63_487));
        assert_eq!((w[0], *w.last().unwrap()), (1509, 7509));
        let w = window(63_000, (1509, 63_487));
        assert_eq!(*w.last().unwrap(), 63_487);
    }

    #[test]
    fn the_measure_is_relative_to_the_level() {
        // The same scene at two brightnesses reads the same (well above the
        // floor), and a flat frame reads nothing.
        let (w, h) = (128, 64);
        let scene = |g: f32| -> Vec<f32> {
            (0..w * h)
                .map(|i| {
                    let (x, y) = ((i % w) as f32, (i / w) as f32);
                    g * (0.3 + 0.1 * (x * 0.7).sin() * (y * 0.5).cos())
                })
                .collect()
        };
        let a = frame_tiles(&scene(1.0), w, h, 0.0);
        let b = frame_tiles(&scene(2.0), w, h, 0.0);
        for (x, y) in a.m.iter().zip(&b.m) {
            assert!((y / x - 1.0).abs() < 0.02, "{x} against {y}");
        }
        let flat = frame_tiles(&vec![0.4; w * h], w, h, 0.0);
        assert!(flat.m.iter().all(|v| *v < 1e-9));
    }
}
