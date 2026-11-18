//! Axial colour correction for the pyramid merge (`STREHL_AXIAL_CA`, default
//! off).
//!
//! # The defect
//!
//! The merge elects on green and replays green's weights into red and blue
//! (`pyramid.rs`, "Elect on GREEN alone"), so red and blue are gathered from
//! the frame where *green* is sharp. A real lens focuses the three colours at
//! slightly different depths, so every render carries red and blue from a
//! frame where they are known to be defocused (SYNTHESIS fact 1413, measured on
//! the A7C II rig: red 0.67-1.07 frames from green, 9-15 % of its gradient
//! energy lost). On the A7CR coin-cell stack the offset is 5.3 frames for red
//! and 1.45 for blue at a step of 8 focus units
//! (`experiments/a7cr-full-potential-2026-11-14/results.md`).
//!
//! # The fix
//!
//! The election is left exactly as it is (green, its noise model, its gate).
//! What changes is the *source* of the coarse part of the red and blue
//! planes: merged frame `k` takes green from RAW `k` and red coarser than
//! `SPLIT_SIGMA` from the RAW nearest `k + d_r(x)`, per pixel; blue likewise
//! with `d_b(x)`. That is the per-channel focus-index offset SYNTHESIS fact
//! 1417 proposed, at no extra election cost.
//!
//! `d_r` and `d_b` are fitted at runtime from this stack (AGENTS: fit geometry
//! at runtime), because they are in frames and therefore depend on the focus
//! step: every frame is decoded once, each CFA channel band-passed (difference
//! of Gaussians, sigma 1 and 2 plane px) and its energy taken per 64-px tile;
//! a through-focus peak is fitted per tile and channel; the per-tile offset of
//! red (blue) from green is fitted with a smooth field `a + b u + c v + e r^2`
//! (normalised plane coordinates, Huber weights). The same measurement between
//! the two green sites is printed as the null. A channel whose band amplitude
//! at its own focus is under `MIN_GAIN` of its amplitude at green's is left
//! alone: there is nothing to fetch.
//!
//! # Three things the first version got wrong (2026-11-15, measured)
//!
//! All on the A7CR coin stack, `experiments/a7cr-full-potential-2026-11-14/`
//! (`axial-probe.py`, `axial-probe-pairs.py`, `results.md`).
//!
//! **Frames several apart do not sit on each other.** The alignment places
//! each frame well enough for a merge that reads one frame at a time, but
//! green five frames away lands 0.53 sensor px rms from green in the
//! borrowing frame (0.18 px for the next frame), red and blue moving with it
//! (correlation 0.94-0.97). About 60 % of that power is a similarity that
//! differs from pair to pair, the rest a fixed spatial pattern. Read where
//! the alignment left it, borrowed red fringes against green by that much. So
//! each borrowed frame is first registered to the borrowing frame on green
//! luma: band-passed (sigma 1 - 3 plane px), a per-tile displacement from the
//! normal equations of `C = a G - a d . grad(G)` pooled over 3x3 tiles of 64
//! px, two passes, a robust similarity over the tiles, and the tiles'
//! departures from it kept where they are well determined. Red and blue are
//! read at the displaced position (Catmull-Rom). That brought red's residual
//! against green from 0.47 px back to 0.23-0.28 (0.25 with no borrowing).
//!
//! **A frame's finest red belongs to that frame's green.** The gather
//! demosaics each frame before it warps it (`warp_frame_in_place_fullres`),
//! and the final demosaic of the merged mosaic reads red's finest detail as a
//! correction to green. Red from another frame is sharper in every band of
//! its plane (1.06-1.13 in amplitude), yet with all of it borrowed the
//! render's 0.25-0.40 cycles/px signal fell 5-7 % in all three channels,
//! noise with it, registered or not. Its finest detail is aliased at the
//! other frame's sampling phase and does not agree with this frame's green.
//! So only the part a Gaussian of `SPLIT_SIGMA` plane px passes is borrowed;
//! the rest stays the frame's own. At 1.0 the fine-detail figure is within
//! 0.4 % of no borrowing; at 0.75 it is 1.3 % down with 2 % less fringe.
//!
//! **Interpolating between two frames buys nothing.** The stack oversamples
//! focus about tenfold, and reading the one nearest frame gave the same
//! figures to the third decimal, so the nearest is read.
//!
//! `STREHL_AXIAL_CA=unregistered` skips the registration, as a control arm.
//!
//! # Cost and limits
//!
//! One extra decode of every frame for the measurement, and every borrowed
//! frame's red and blue planes are gathered a second time (cached while
//! neighbouring frames need them) and resampled once more. Refused, rather
//! than silently ignored, with pixel-shift assembly (its parked groups are
//! consumed once per decode), defect correction, the GPU fold and temporal
//! energy. Red and blue at a frame boundary of the stack are clamped to the
//! end frame.
use super::*;
use std::collections::{BTreeSet, HashMap};
use std::sync::{Arc, Mutex, RwLock};

pub(super) const ENV: &str = "STREHL_AXIAL_CA";
/// Tile edge for the measurement, in plane px.
const TILE: usize = 64;
/// Fewer usable tiles than this and a channel is left uncorrected.
const MIN_TILES: usize = 24;
/// Clipped luma is kept this many plane px away from the registration.
const REG_GUARD: usize = 6;
/// Only what a Gaussian of this sigma (plane px) passes is taken from the
/// borrowed frame; finer red and blue stay the frame's own. See the module
/// documentation for the measurement behind the value.
const SPLIT_SIGMA: f64 = 1.0;
/// A channel is corrected only when its band amplitude at its own focus is
/// at least this multiple of its amplitude at green's focus. Chosen, not
/// tuned: on the A7CR coin stack red reads about 1.08 and blue about 1.01,
/// and correcting blue changed no figure.
const MIN_GAIN: f64 = 1.03;
const DUMP_ENV: &str = "STREHL_AXIAL_DUMP";

/// `off` (default), `on`, `unregistered` or `placebo`. `unregistered` reads
/// the borrowed frames where the alignment put them (a control arm).
/// `placebo` measures as `on` does and then applies the offsets with their
/// sign flipped, reading red and blue twice as far from their focus as doing
/// nothing would: it must do worse than `off`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Mode {
    Off,
    On,
    Unregistered,
    Placebo,
}

fn mode() -> Result<Mode> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(Mode::Off),
        Err(e) => Err(e).context(ENV),
        Ok(v) => parse(&v),
    }
}

/// Whether the operator asked for the correction (or its placebo).
pub(super) fn requested() -> Result<bool> {
    Ok(mode()? != Mode::Off)
}

fn parse(v: &str) -> Result<Mode> {
    match v.trim() {
        "" | "0" | "off" => Ok(Mode::Off),
        "on" | "1" => Ok(Mode::On),
        "unregistered" => Ok(Mode::Unregistered),
        "placebo" => Ok(Mode::Placebo),
        other => anyhow::bail!("{ENV}={other:?} is not on, off, unregistered or placebo"),
    }
}

/// A smooth focus-offset field, in frames, over plane coordinates.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(super) struct Field {
    /// `a + b u + c v + e (u^2 + v^2)`, `u`, `v` plane coordinates about the
    /// plane centre divided by the half diagonal.
    coef: [f64; 4],
    /// Evaluations are clamped to the range the tiles actually showed, so the
    /// quadratic cannot run away into an unmeasured corner.
    lo: f64,
    hi: f64,
}

impl Field {
    const ZERO: Field = Field {
        coef: [0.0; 4],
        lo: 0.0,
        hi: 0.0,
    };

    fn at(&self, u: f64, v: f64) -> f64 {
        let [a, b, c, e] = self.coef;
        (a + b * u + c * v + e * (u * u + v * v)).clamp(self.lo, self.hi)
    }

    /// The same field with its sign flipped: the placebo.
    fn flipped(&self) -> Field {
        Field {
            coef: self.coef.map(|c| -c),
            lo: -self.hi,
            hi: -self.lo,
        }
    }
}

/// Plane-coordinate normalisation shared by the measurement and the gather.
#[derive(Clone, Copy, Debug)]
struct Frame2Unit {
    cx: f64,
    cy: f64,
    norm: f64,
}

impl Frame2Unit {
    fn new(w: usize, h: usize) -> Self {
        let (cx, cy) = ((w as f64 - 1.0) / 2.0, (h as f64 - 1.0) / 2.0);
        Self {
            cx,
            cy,
            norm: cx.hypot(cy).max(1.0),
        }
    }
    fn uv(&self, x: f64, y: f64) -> (f64, f64) {
        ((x - self.cx) / self.norm, (y - self.cy) / self.norm)
    }
}

/// Separable Gaussian blur of a `w x h` plane, edge clamped.
pub(super) fn blur(src: &[f32], w: usize, h: usize, sigma: f64) -> Vec<f32> {
    let (mut tmp, mut out) = (Vec::new(), Vec::new());
    blur_into(src, w, h, sigma, &mut tmp, &mut out);
    out
}

/// [`blur`] into `out` (resized), through `tmp`: the same values, for a
/// caller that blurs frame after frame and keeps the buffers.
pub(super) fn blur_into(
    src: &[f32],
    w: usize,
    h: usize,
    sigma: f64,
    tmp: &mut Vec<f32>,
    out: &mut Vec<f32>,
) {
    let r = (3.0 * sigma).ceil() as isize;
    let k: Vec<f32> = (-r..=r)
        .map(|t| (-0.5 * (t as f64 / sigma).powi(2)).exp() as f32)
        .collect();
    let s: f32 = k.iter().sum();
    let k: Vec<f32> = k.iter().map(|v| v / s).collect();
    // Every element of `tmp` is written below; `out` accumulates from zero.
    tmp.resize(w * h, 0.0);
    // Columns whose taps all fall inside the row accumulate tap by tap over
    // the whole run (vectorisable); the `r` columns at each edge clamp per
    // tap. Either way a pixel sums its taps in tap order from zero, so the
    // two loops give the same bits.
    let ru = r as usize;
    let interior = ru..w.saturating_sub(ru).max(ru);
    tmp.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        let line = &src[y * w..(y + 1) * w];
        let clamped = |x: usize| {
            let mut acc = 0f32;
            for (t, kv) in k.iter().enumerate() {
                let xx = (x as isize + t as isize - r).clamp(0, w as isize - 1) as usize;
                acc += kv * line[xx];
            }
            acc
        };
        for x in (0..interior.start.min(w)).chain(interior.end..w) {
            row[x] = clamped(x);
        }
        if !interior.is_empty() {
            let run = &mut row[interior.clone()];
            run.fill(0.0);
            for (t, kv) in k.iter().enumerate() {
                let src = &line[interior.start + t - ru..interior.end + t - ru];
                for (o, v) in run.iter_mut().zip(src) {
                    *o += kv * v;
                }
            }
        }
    });
    out.clear();
    out.resize(w * h, 0.0);
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (t, kv) in k.iter().enumerate() {
            let yy = (y as isize + t as isize - r).clamp(0, h as isize - 1) as usize;
            let line = &tmp[yy * w..(yy + 1) * w];
            for (o, v) in row.iter_mut().zip(line) {
                *o += kv * v;
            }
        }
    });
}

/// Through-focus peak of one energy curve, in fractional frames, and its
/// contrast (peak above the curve's floor, over the floor). `None` when the
/// curve has no interior, well-formed peak.
pub(super) fn peak(curve: &[f64]) -> Option<(f64, f64)> {
    let n = curve.len();
    if n < 7 {
        return None;
    }
    let mut s = curve.to_vec();
    for _ in 0..2 {
        let p = s.clone();
        for i in 0..n {
            let a = p[i.saturating_sub(1)];
            let b = p[(i + 1).min(n - 1)];
            s[i] = 0.25 * a + 0.5 * p[i] + 0.25 * b;
        }
    }
    let floor = s.iter().copied().fold(f64::INFINITY, f64::min);
    let (kstar, top) = s
        .iter()
        .copied()
        .enumerate()
        .fold(
            (0, f64::NEG_INFINITY),
            |m, (i, v)| if v > m.1 { (i, v) } else { m },
        );
    let amp = top - floor;
    // NaN-safe: a NaN amplitude is refused along with a non-positive one.
    if amp.is_nan()
        || amp <= 0.0
        || kstar < 2
        || kstar + 3 > n
        || amp < floor.max(f64::MIN_POSITIVE)
    {
        return None;
    }
    // Contiguous run above 30 % of the peak, then a weighted parabola in log.
    let above = |i: usize| s[i] - floor > 0.3 * amp;
    let (mut lo, mut hi) = (kstar, kstar);
    while lo > 0 && above(lo - 1) && kstar - lo < 12 {
        lo -= 1;
    }
    while hi + 1 < n && above(hi + 1) && hi - kstar < 12 {
        hi += 1;
    }
    if hi - lo < 3 {
        return None;
    }
    let mut m = [[0f64; 3]; 3];
    let mut r = [0f64; 3];
    for (i, v) in s.iter().enumerate().take(hi + 1).skip(lo) {
        let e = v - floor;
        let w = e * e;
        let t = i as f64 - kstar as f64;
        let y = e.ln();
        let phi = [1.0, t, t * t];
        for a in 0..3 {
            r[a] += w * phi[a] * y;
            for b in 0..3 {
                m[a][b] += w * phi[a] * phi[b];
            }
        }
    }
    let sol = solve3(m, r)?;
    let c = sol[2];
    if c.is_nan() || c >= -1e-6 {
        return None;
    }
    let off = -sol[1] / (2.0 * c);
    (off.abs() < 2.5).then_some((kstar as f64 + off, amp / floor.max(f64::MIN_POSITIVE)))
}

/// A through-focus curve at a fractional frame, linearly interpolated and
/// held at the ends; never below a tiny positive floor, so ratios are finite.
fn value_at(curve: &[f64], k: f64) -> f64 {
    let k = k.clamp(0.0, (curve.len() - 1) as f64);
    let i = (k as usize).min(curve.len().saturating_sub(2));
    let f = k - i as f64;
    ((1.0 - f) * curve[i] + f * curve[(i + 1).min(curve.len() - 1)]).max(f64::MIN_POSITIVE)
}

fn solve3(m: [[f64; 3]; 3], r: [f64; 3]) -> Option<[f64; 3]> {
    let det = |a: [[f64; 3]; 3]| {
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    };
    let d = det(m);
    if d.abs() < 1e-300 {
        return None;
    }
    let mut out = [0f64; 3];
    for (c, o) in out.iter_mut().enumerate() {
        let mut a = m;
        for row in 0..3 {
            a[row][c] = r[row];
        }
        *o = det(a) / d;
    }
    Some(out)
}

/// Huber-weighted least squares for `a + b u + c v + e r^2`.
fn fit_field(rows: &[(f64, f64, f64, f64)]) -> Option<([f64; 4], f64)> {
    if rows.len() < MIN_TILES {
        return None;
    }
    let mut hw = vec![1.0; rows.len()];
    let mut coef = [0f64; 4];
    let mut scale = 0.0;
    for _ in 0..10 {
        let mut m = [[0f64; 4]; 4];
        let mut r = [0f64; 4];
        for ((u, v, d, w), h) in rows.iter().zip(&hw) {
            let phi = [1.0, *u, *v, u * u + v * v];
            for a in 0..4 {
                r[a] += w * h * phi[a] * d;
                for b in 0..4 {
                    m[a][b] += w * h * phi[a] * phi[b];
                }
            }
        }
        coef = solve4(m, r)?;
        let mut res: Vec<f64> = rows
            .iter()
            .map(|(u, v, d, _)| {
                (d - (coef[0] + coef[1] * u + coef[2] * v + coef[3] * (u * u + v * v))).abs()
            })
            .collect();
        let mut sorted = res.clone();
        sorted.sort_by(f64::total_cmp);
        scale = 1.4826 * sorted[sorted.len() / 2] + 1e-6;
        for (h, e) in hw.iter_mut().zip(res.iter_mut()) {
            *h = (2.0 * scale / e.max(1e-12)).min(1.0);
        }
    }
    Some((coef, scale))
}

fn solve4(mut m: [[f64; 4]; 4], mut r: [f64; 4]) -> Option<[f64; 4]> {
    for c in 0..4 {
        let p = (c..4).max_by(|&a, &b| m[a][c].abs().total_cmp(&m[b][c].abs()))?;
        if m[p][c].abs() < 1e-300 {
            return None;
        }
        m.swap(c, p);
        r.swap(c, p);
        for row in 0..4 {
            if row != c {
                let f = m[row][c] / m[c][c];
                let pivot = m[c];
                for (dst, src) in m[row].iter_mut().zip(pivot).skip(c) {
                    *dst -= f * src;
                }
                r[row] -= f * r[c];
            }
        }
    }
    Some([
        r[0] / m[0][0],
        r[1] / m[1][1],
        r[2] / m[2][2],
        r[3] / m[3][3],
    ])
}

/// What the measurement found, for the prologue.
pub(super) struct Measurement {
    pub(super) red: Option<Field>,
    pub(super) blue: Option<Field>,
    lines: Vec<String>,
    unit: Frame2Unit,
}

/// Fit the per-channel focus offsets of a stack. Reads every frame once.
pub(super) fn measure(paths: &[PathBuf]) -> Result<Measurement> {
    let n = paths.len();
    let started = Instant::now();
    // Per frame: [channel][tile] energy, channels R, G1, G2, B; and which
    // tiles held a clipped sample in that frame.
    let mut energy: Vec<[Vec<f64>; 4]> = Vec::with_capacity(n);
    let mut clipped: Vec<bool> = Vec::new();
    let (mut pw, mut ph, mut tw, mut th) = (0, 0, 0, 0);
    for (i, path) in paths.iter().enumerate() {
        let f = strehl_raw::decode(path)
            .with_context(|| format!("axial colour: decoding frame {i}"))?;
        let a = f.active;
        let (w, h) = (a.width / 2, a.height / 2);
        if i == 0 {
            (pw, ph, tw, th) = (w, h, w / TILE, h / TILE);
            clipped = vec![false; tw * th];
        }
        ensure!(
            w == pw && h == ph,
            "axial colour: frame {i} has a different size"
        );
        let clip = 0.9 * (f.levels.white - f.levels.black);
        let mut per = [Vec::new(), Vec::new(), Vec::new(), Vec::new()];
        for (c, (dx, dy)) in BAND_PLANE_OFFSETS.iter().copied().enumerate() {
            let mut plane = vec![0f32; w * h];
            plane.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                let src = &f.data[(a.y + 2 * y + dy) * f.stride + a.x + dx..];
                for (x, o) in row.iter_mut().enumerate() {
                    *o = f32::from(src[2 * x]) - f.levels.black;
                }
            });
            let mut tile_clip = vec![false; tw * th];
            for ty in 0..th {
                for tx in 0..tw {
                    tile_clip[ty * tw + tx] = (ty * TILE..(ty + 1) * TILE).any(|y| {
                        plane[y * w + tx * TILE..y * w + (tx + 1) * TILE]
                            .iter()
                            .any(|v| *v >= clip)
                    });
                }
            }
            for (k, c) in clipped.iter_mut().zip(&tile_clip) {
                *k |= *c;
            }
            let l1 = blur(&plane, w, h, 1.0);
            let l2 = blur(&l1, w, h, 3f64.sqrt());
            let e: Vec<f64> = (0..th * tw)
                .into_par_iter()
                .map(|t| {
                    let (ty, tx) = (t / tw, t % tw);
                    let mut s = 0f64;
                    for y in ty * TILE..(ty + 1) * TILE {
                        for x in tx * TILE..(tx + 1) * TILE {
                            let b = f64::from(l1[y * w + x] - l2[y * w + x]);
                            s += b * b;
                        }
                    }
                    s / (TILE * TILE) as f64
                })
                .collect();
            per[c] = e;
        }
        energy.push(per);
    }
    let unit = Frame2Unit::new(pw, ph);
    let curve = |c: usize, t: usize| -> Vec<f64> {
        energy
            .iter()
            .map(|e| if c == 1 { e[1][t] + e[2][t] } else { e[c][t] })
            .collect()
    };
    let mut rows_r = Vec::new();
    let mut rows_b = Vec::new();
    let (mut gain_r, mut gain_b) = (Vec::new(), Vec::new());
    let mut null = Vec::new();
    for t in 0..tw * th {
        if clipped[t] {
            continue;
        }
        let Some((kg, cg)) = peak(&curve(1, t)) else {
            continue;
        };
        let (u, v) = unit.uv(
            ((t % tw) * TILE + TILE / 2) as f64,
            ((t / tw) * TILE + TILE / 2) as f64,
        );
        // Band amplitude at the channel's own focus over that at green's.
        let gain = |c: &[f64], own: f64| (value_at(c, own) / value_at(c, kg)).sqrt();
        let cr = curve(0, t);
        if let Some((kr, conr)) = peak(&cr) {
            rows_r.push((u, v, kr - kg, cg.min(conr).min(50.0)));
            gain_r.push(gain(&cr, kr));
        }
        let cb = curve(3, t);
        if let Some((kb, conb)) = peak(&cb) {
            rows_b.push((u, v, kb - kg, cg.min(conb).min(50.0)));
            gain_b.push(gain(&cb, kb));
        }
        let g1: Vec<f64> = energy.iter().map(|e| e[1][t]).collect();
        let g2: Vec<f64> = energy.iter().map(|e| e[2][t]).collect();
        if let (Some((k1, _)), Some((k2, _))) = (peak(&g1), peak(&g2)) {
            null.push(k1 - k2);
        }
    }
    let mut lines = vec![format!(
        "measured over {n} frames, {} tiles of {TILE} plane px ({} clipped, left out), {:.1} s",
        tw * th,
        clipped.iter().filter(|c| **c).count(),
        started.elapsed().as_secs_f64()
    )];
    let summarise = |name: &str,
                     rows: &[(f64, f64, f64, f64)],
                     gains: &mut [f64],
                     lines: &mut Vec<String>|
     -> Option<Field> {
        gains.sort_by(f64::total_cmp);
        let gain = gains.get(gains.len() / 2).copied().unwrap_or(1.0);
        let Some((coef, scale)) = fit_field(rows) else {
            lines.push(format!(
                "{name}: {} usable tiles, fewer than {MIN_TILES}; NOT corrected",
                rows.len()
            ));
            return None;
        };
        let mut d: Vec<f64> = rows.iter().map(|r| r.2).collect();
        d.sort_by(f64::total_cmp);
        let q = |p: f64| d[((d.len() - 1) as f64 * p).round() as usize];
        let field = Field {
            coef,
            lo: q(0.05) - 0.5,
            hi: q(0.95) + 0.5,
        };
        let corner = field.at(0.8 * unit.cx / unit.norm, 0.8 * unit.cy / unit.norm);
        lines.push(format!(
            "{name}: {} tiles, median {:+.2} frames from green (IQR {:+.2}..{:+.2}); field centre {:+.2}, \
             0.8 of the way to a corner {:+.2}; scatter about the field {:.2}; band amplitude at its \
             own focus {gain:.3} of that at green's{}",
            rows.len(),
            q(0.5),
            q(0.25),
            q(0.75),
            field.at(0.0, 0.0),
            corner,
            scale,
            if gain < MIN_GAIN {
                format!(", under {MIN_GAIN}: NOT corrected")
            } else {
                String::new()
            }
        ));
        (gain >= MIN_GAIN).then_some(field)
    };
    let red = summarise("red ", &rows_r, &mut gain_r, &mut lines);
    let blue = summarise("blue", &rows_b, &mut gain_b, &mut lines);
    if null.len() >= MIN_TILES {
        null.sort_by(f64::total_cmp);
        let med = null[null.len() / 2];
        let mad = 1.4826 * {
            let mut a: Vec<f64> = null.iter().map(|v| (v - med).abs()).collect();
            a.sort_by(f64::total_cmp);
            a[a.len() / 2]
        };
        lines.push(format!(
            "null: green site 1 against green site 2, {} tiles, median {med:+.3} frames, scatter {mad:.2}",
            null.len()
        ));
    }
    Ok(Measurement {
        red,
        blue,
        lines,
        unit,
    })
}

/// Band-passed green luma of one frame and the samples kept for registration
/// (those at least `REG_GUARD` px from a clipped one).
struct RegBand {
    band: Vec<f32>,
    keep: Vec<u8>,
}

fn reg_band(luma: &[f32], w: usize, h: usize, clip: f32) -> RegBand {
    let l1 = blur(luma, w, h, 1.0);
    let l3 = blur(luma, w, h, 3.0);
    let band: Vec<f32> = l1.par_iter().zip(&l3).map(|(a, b)| a - b).collect();
    let mut hit = vec![0u8; w * h];
    hit.par_chunks_mut(w)
        .zip(luma.par_chunks(w))
        .for_each(|(o, l)| {
            for (x, o) in o.iter_mut().enumerate() {
                let (lo, hi) = (x.saturating_sub(REG_GUARD), (x + REG_GUARD + 1).min(w));
                *o = u8::from(l[lo..hi].iter().any(|v| *v >= clip));
            }
        });
    let mut keep = vec![0u8; w * h];
    keep.par_chunks_mut(w).enumerate().for_each(|(y, o)| {
        let (lo, hi) = (y.saturating_sub(REG_GUARD), (y + REG_GUARD + 1).min(h));
        for (x, o) in o.iter_mut().enumerate() {
            *o = u8::from(!(lo..hi).any(|yy| hit[yy * w + x] != 0));
        }
    });
    RegBand { band, keep }
}

/// Central-difference gradient of a plane (zero on the border).
fn gradient(band: &[f32], w: usize, h: usize) -> (Vec<f32>, Vec<f32>) {
    let mut gx = vec![0f32; w * h];
    let mut gy = vec![0f32; w * h];
    gx.par_chunks_mut(w)
        .zip(gy.par_chunks_mut(w))
        .enumerate()
        .for_each(|(y, (rx, ry))| {
            if y == 0 || y + 1 >= h {
                return;
            }
            let row = &band[y * w..(y + 1) * w];
            let (up, down) = (&band[(y - 1) * w..y * w], &band[(y + 1) * w..(y + 2) * w]);
            for x in 1..w - 1 {
                rx[x] = 0.5 * (row[x + 1] - row[x - 1]);
                ry[x] = 0.5 * (down[x] - up[x]);
            }
        });
    (gx, gy)
}

/// Where a borrowed frame's content sits relative to the borrowing frame's,
/// per registration tile, in plane px: content at `x` in the borrowing frame
/// is at `x + d(x)` in the borrowed one.
#[derive(Clone, Debug)]
struct Shift {
    tw: usize,
    th: usize,
    d: Vec<[f32; 2]>,
    /// Tiles whose own measurement was used, and the rms of the field.
    measured: usize,
    rms: f32,
}

impl Shift {
    /// Bilinear between tile centres, held constant beyond the outer ones.
    fn at(&self, x: f32, y: f32) -> (f32, f32) {
        let fx = ((x + 0.5) / TILE as f32 - 0.5).clamp(0.0, (self.tw - 1) as f32);
        let fy = ((y + 0.5) / TILE as f32 - 0.5).clamp(0.0, (self.th - 1) as f32);
        let (x0, y0) = (
            (fx as usize).min(self.tw.saturating_sub(2)),
            (fy as usize).min(self.th.saturating_sub(2)),
        );
        let (x1, y1) = ((x0 + 1).min(self.tw - 1), (y0 + 1).min(self.th - 1));
        let (ax, ay) = (fx - x0 as f32, fy - y0 as f32);
        let g = |tx: usize, ty: usize| self.d[ty * self.tw + tx];
        let (a, b, c, d) = (g(x0, y0), g(x1, y0), g(x0, y1), g(x1, y1));
        let mix = |i: usize| {
            (1.0 - ay) * ((1.0 - ax) * a[i] + ax * b[i]) + ay * ((1.0 - ax) * c[i] + ax * d[i])
        };
        (mix(0), mix(1))
    }
}

/// Register a borrowed frame's band (`nb`) to the borrowing frame's (`own`,
/// with its gradient). `None` when too few tiles carry a usable measurement.
///
/// Two passes: the linearised estimate reads long by about 8 % at 0.4 px on
/// 7-px detail, so the borrowed band is read again at the first estimate and
/// the remainder measured.
fn register(
    own: &RegBand,
    gx: &[f32],
    gy: &[f32],
    nb: &RegBand,
    w: usize,
    h: usize,
) -> Option<Shift> {
    let first = register_pass(own, gx, gy, nb, w, h, None)?;
    Some(register_pass(own, gx, gy, nb, w, h, Some(&first)).unwrap_or(first))
}

/// One pass of [`register`]: the displacement left after `prior`, added to it.
fn register_pass(
    own: &RegBand,
    gx: &[f32],
    gy: &[f32],
    nb: &RegBand,
    w: usize,
    h: usize,
    prior: Option<&Shift>,
) -> Option<Shift> {
    let (tw, th) = (w / TILE, h / TILE);
    if tw < 2 || th < 2 {
        return None;
    }
    // The borrowed band (and whether it is kept) at `i`, read at the prior.
    let borrowed = |x: usize, y: usize, i: usize| -> Option<f32> {
        let Some(prior) = prior else {
            return (nb.keep[i] != 0).then(|| nb.band[i]);
        };
        let (dx, dy) = prior.at(x as f32, y as f32);
        let (fx, fy) = (
            (x as f32 + dx).clamp(0.0, (w - 1) as f32),
            (y as f32 + dy).clamp(0.0, (h - 1) as f32),
        );
        let (x0, y0) = ((fx as usize).min(w - 2), (fy as usize).min(h - 2));
        let (ax, ay) = (fx - x0 as f32, fy - y0 as f32);
        let o = y0 * w + x0;
        if nb.keep[o] == 0 || nb.keep[o + 1] == 0 || nb.keep[o + w] == 0 || nb.keep[o + w + 1] == 0
        {
            return None;
        }
        Some(
            (1.0 - ay) * ((1.0 - ax) * nb.band[o] + ax * nb.band[o + 1])
                + ay * ((1.0 - ax) * nb.band[o + w] + ax * nb.band[o + w + 1]),
        )
    };
    // Per tile: GG GGx GGy GxGx GxGy GyGy | GC GxC GyC | CC | n.
    let sums: Vec<[f64; 11]> = (0..tw * th)
        .into_par_iter()
        .map(|t| {
            let (ty, tx) = (t / tw, t % tw);
            let mut s = [0f64; 11];
            for y in ty * TILE..(ty + 1) * TILE {
                for px in tx * TILE..(tx + 1) * TILE {
                    let i = y * w + px;
                    if own.keep[i] == 0 {
                        continue;
                    }
                    let Some(c) = borrowed(px, y, i) else {
                        continue;
                    };
                    let (g, x, yv, c) = (
                        f64::from(own.band[i]),
                        f64::from(gx[i]),
                        f64::from(gy[i]),
                        f64::from(c),
                    );
                    s[0] += g * g;
                    s[1] += g * x;
                    s[2] += g * yv;
                    s[3] += x * x;
                    s[4] += x * yv;
                    s[5] += yv * yv;
                    s[6] += g * c;
                    s[7] += x * c;
                    s[8] += yv * c;
                    s[9] += c * c;
                    s[10] += 1.0;
                }
            }
            s
        })
        .collect();
    // Pool 3x3 tiles (the aperture problem is rarely shared by nine), solve.
    let unit = Frame2Unit::new(w, h);
    let centre = |tx: usize, ty: usize| {
        unit.uv(
            (tx * TILE + TILE / 2) as f64 - 0.5,
            (ty * TILE + TILE / 2) as f64 - 0.5,
        )
    };
    let mut tile: Vec<Option<[f64; 2]>> = vec![None; tw * th];
    for ty in 0..th {
        for tx in 0..tw {
            let mut p = [0f64; 11];
            let mut cells = 0usize;
            for yy in ty.saturating_sub(1)..(ty + 2).min(th) {
                for xx in tx.saturating_sub(1)..(tx + 2).min(tw) {
                    for (a, b) in p.iter_mut().zip(&sums[yy * tw + xx]) {
                        *a += b;
                    }
                    cells += 1;
                }
            }
            if p[10] < 0.25 * (cells * TILE * TILE) as f64 || p[9] <= 0.0 {
                continue;
            }
            let m = [[p[0], p[1], p[2]], [p[1], p[3], p[4]], [p[2], p[4], p[5]]];
            let Some(sol) = solve3(m, [p[6], p[7], p[8]]) else {
                continue;
            };
            let a = sol[0];
            if !(a.is_finite() && a > 0.25 && a < 4.0) {
                continue;
            }
            let explained = (sol[0] * p[6] + sol[1] * p[7] + sol[2] * p[8]) / p[9];
            // Smaller eigenvalue of the gradient block against the larger.
            let (tr, det) = (p[3] + p[5], p[3] * p[5] - p[4] * p[4]);
            let disc = (0.25 * tr * tr - det).max(0.0).sqrt();
            let (l0, l1) = (0.5 * tr - disc, 0.5 * tr + disc);
            let before = prior.map_or([0.0; 2], |p| {
                let d = p.d[ty * tw + tx];
                [f64::from(d[0]), f64::from(d[1])]
            });
            let d = [before[0] - sol[1] / a, before[1] - sol[2] / a];
            if explained < 0.25 || l0 < 0.03 * l1 || d[0].hypot(d[1]) > 3.0 {
                continue;
            }
            tile[ty * tw + tx] = Some(d);
        }
    }
    // Robust similarity over the tiles: dx = s u - q v + tx, dy = q u + s v + ty.
    let rows: Vec<(f64, f64, [f64; 2])> = (0..tw * th)
        .filter_map(|t| {
            tile[t].map(|d| {
                let (u, v) = centre(t % tw, t / tw);
                (u, v, d)
            })
        })
        .collect();
    if rows.len() < MIN_TILES {
        return None;
    }
    let mut hw = vec![1.0f64; rows.len()];
    let mut sim = [0f64; 4];
    for _ in 0..8 {
        let mut m = [[0f64; 4]; 4];
        let mut r = [0f64; 4];
        for ((u, v, d), h) in rows.iter().zip(&hw) {
            for (phi, t) in [([*u, -*v, 1.0, 0.0], d[0]), ([*v, *u, 0.0, 1.0], d[1])] {
                for a in 0..4 {
                    r[a] += h * phi[a] * t;
                    for b in 0..4 {
                        m[a][b] += h * phi[a] * phi[b];
                    }
                }
            }
        }
        sim = solve4(m, r)?;
        let res: Vec<f64> = rows
            .iter()
            .map(|(u, v, d)| {
                (d[0] - (sim[0] * u - sim[1] * v + sim[2]))
                    .hypot(d[1] - (sim[1] * u + sim[0] * v + sim[3]))
            })
            .collect();
        let mut sorted = res.clone();
        sorted.sort_by(f64::total_cmp);
        let scale = 1.4826 * sorted[sorted.len() / 2] + 1e-6;
        for (h, e) in hw.iter_mut().zip(&res) {
            *h = (2.0 * scale / e.max(1e-12)).min(1.0);
        }
    }
    let model = |tx: usize, ty: usize| {
        let (u, v) = centre(tx, ty);
        [
            sim[0] * u - sim[1] * v + sim[2],
            sim[1] * u + sim[0] * v + sim[3],
        ]
    };
    // A tile keeps its departure from the similarity when it is modest; a
    // tile without one takes the mean departure of its measured neighbours.
    let depart: Vec<Option<[f64; 2]>> = (0..tw * th)
        .map(|t| {
            let m = model(t % tw, t / tw);
            tile[t]
                .map(|d| [d[0] - m[0], d[1] - m[1]])
                .filter(|r| r[0].hypot(r[1]) <= 1.5)
        })
        .collect();
    let mut d = Vec::with_capacity(tw * th);
    let (mut measured, mut power) = (0usize, 0f64);
    for ty in 0..th {
        for tx in 0..tw {
            let m = model(tx, ty);
            let r = depart[ty * tw + tx].unwrap_or_else(|| {
                let (mut acc, mut n) = ([0f64; 2], 0f64);
                for yy in ty.saturating_sub(1)..(ty + 2).min(th) {
                    for xx in tx.saturating_sub(1)..(tx + 2).min(tw) {
                        if let Some(v) = depart[yy * tw + xx] {
                            acc[0] += v[0];
                            acc[1] += v[1];
                            n += 1.0;
                        }
                    }
                }
                if n > 0.0 {
                    [acc[0] / n, acc[1] / n]
                } else {
                    [0.0; 2]
                }
            });
            measured += usize::from(depart[ty * tw + tx].is_some());
            let v = [m[0] + r[0], m[1] + r[1]];
            power += v[0] * v[0] + v[1] * v[1];
            d.push([v[0] as f32, v[1] as f32]);
        }
    }
    Some(Shift {
        tw,
        th,
        d,
        measured,
        rms: (power / (tw * th) as f64).sqrt() as f32,
    })
}

/// Red and blue of one frame on the reference grid, and its registration
/// band when borrowed frames are registered.
struct Borrowed {
    planes: [Vec<f32>; 2],
    reg: Option<RegBand>,
}

type RedBlue = Arc<Borrowed>;

/// A source whose every read bypasses the decode-ahead plan, and which never
/// hands out a parked pixel-shift group (assembly is refused with this
/// correction). The neighbour gathers read through it.
struct Direct<'a, S: PyramidFrameSource>(&'a S);

impl<S: PyramidFrameSource> PyramidFrameSource for Direct<'_, S> {
    fn len(&self) -> usize {
        self.0.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        self.0.decode_direct(index)
    }
}

struct Scratch {
    warp: WarpScratch,
    planes: Vec<Vec<f32>>,
    luma: Vec<f32>,
}

/// The installed correction: offsets, and red and blue planes of the frames
/// the merge is reading them from.
struct Axial {
    frames: usize,
    red: Field,
    blue: Field,
    unit: Frame2Unit,
    /// Gathered red and blue per frame; `None` when the alignment refused
    /// the frame. Never waited on: two merged frames needing the same
    /// uncached frame may both gather it (the second insert is dropped).
    /// A blocking once-cell here deadlocked: a rayon worker initialising an
    /// entry stole the next frame's preparation job, which then waited on the
    /// same entry from the same thread.
    cache: Mutex<HashMap<usize, Option<RedBlue>>>,
    in_progress: Mutex<BTreeSet<usize>>,
    pool: Mutex<Vec<Scratch>>,
    /// Smallest and largest offset over the fields, for cache retention.
    span: (f64, f64),
    /// Whether borrowed frames are registered to the borrowing frame.
    registered: bool,
    /// Per registered pair: frames apart, rms of the shift field (plane px),
    /// tiles measured; a failed registration is recorded with zero tiles.
    pairs: Mutex<Vec<(usize, f32, usize)>>,
}

static ACTIVE: RwLock<Option<Arc<Axial>>> = RwLock::new(None);

fn active() -> Option<Arc<Axial>> {
    ACTIVE.read().unwrap_or_else(|e| e.into_inner()).clone()
}

/// Whether a correction is installed for the render now running.
pub(super) fn is_active() -> bool {
    active().is_some()
}

/// Clears the installed correction when the render ends, however it ends,
/// and reports what the registration found.
pub(super) struct Installed;

impl Drop for Installed {
    fn drop(&mut self) {
        let was = ACTIVE.write().unwrap_or_else(|e| e.into_inner()).take();
        let Some(ax) = was.filter(|ax| ax.registered) else {
            return;
        };
        let pairs = ax.pairs.lock().unwrap_or_else(|e| e.into_inner());
        let far = pairs.iter().map(|p| p.0).max().unwrap_or(0);
        let mut line = String::new();
        for span in 1..=far {
            let (mut power, mut n, mut failed) = (0f64, 0usize, 0usize);
            for (_, rms, tiles) in pairs.iter().filter(|p| p.0 == span) {
                if *tiles == 0 {
                    failed += 1;
                } else {
                    power += f64::from(*rms).powi(2);
                    n += 1;
                }
            }
            if n + failed > 0 {
                line.push_str(&format!(
                    " {span}: {:.2} px ({n} pairs{})",
                    2.0 * (power / n.max(1) as f64).sqrt(),
                    if failed > 0 {
                        format!(", {failed} left where the alignment put them")
                    } else {
                        String::new()
                    }
                ));
            }
        }
        if !line.is_empty() {
            eprintln!(
                "axial colour    : borrowed frames registered to the borrowing frame on green; rms \
                 shift found, sensor px, by frames apart --{line}"
            );
        }
    }
}

/// Measure and install, when `STREHL_AXIAL_CA` asks. Prints the measurement.
pub(super) fn install_if_requested(opts: &MergeOptions) -> Result<Option<Installed>> {
    let mode = mode()?;
    if mode == Mode::Off {
        return Ok(None);
    }
    let groups = crate::pixel_shift_cmd::StackGroups::from_env(&opts.dir, opts.limit)?;
    ensure!(
        groups.as_ref().is_none_or(|g| !g.assembles()),
        "{ENV}=on cannot combine with pixel-shift assembly (STREHL_PIXEL_SHIFT=remosaic or \
         remosaic-ungated): its measured groups are consumed once per decode, and the axial \
         correction decodes red and blue a second time. Use STREHL_PIXEL_SHIFT=member1 or off."
    );
    ensure!(
        !crate::stack::defect_request_from_env()?.wants_correction(),
        "{ENV}=on does not support sensor defect correction yet (STREHL_DEFECT)"
    );
    let paths = only_frame(match &groups {
        Some(g) => g.planes.clone(),
        None => crate::raw_paths(&opts.dir, opts.limit)?,
    });
    let m = measure(&paths)?;
    match mode {
        Mode::Placebo => eprintln!(
            "axial colour    : PLACEBO ({ENV}=placebo) -- measured as for on, then the offsets are \
             applied with their sign flipped, so red and blue are read twice as far from their \
             focus; a control arm, never a render to keep"
        ),
        Mode::Unregistered => eprintln!(
            "axial colour    : ON, UNREGISTERED ({ENV}=unregistered) -- red and blue below the split \
             are read from the frames where they focus, where the alignment left those frames; a \
             control arm"
        ),
        _ => eprintln!(
            "axial colour    : ON ({ENV}) -- red and blue coarser than {SPLIT_SIGMA} plane px are \
             read from the frames where they focus, each registered to the borrowing frame on green"
        ),
    }
    for l in &m.lines {
        eprintln!("                  {l}");
    }
    let (mut red, mut blue) = (m.red.unwrap_or(Field::ZERO), m.blue.unwrap_or(Field::ZERO));
    if mode == Mode::Placebo {
        (red, blue) = (red.flipped(), blue.flipped());
    }
    let span = (red.lo.min(blue.lo).min(0.0), red.hi.max(blue.hi).max(0.0));
    *ACTIVE.write().unwrap_or_else(|e| e.into_inner()) = Some(Arc::new(Axial {
        frames: paths.len(),
        red,
        blue,
        unit: m.unit,
        cache: Mutex::new(HashMap::new()),
        in_progress: Mutex::new(BTreeSet::new()),
        pool: Mutex::new(Vec::new()),
        span,
        registered: mode != Mode::Unregistered,
        pairs: Mutex::new(Vec::new()),
    }));
    Ok(Some(Installed))
}

impl Axial {
    /// Red and blue of frame `j` on the reference grid, gathered once and
    /// shared by every merged frame that reads them. `None` when the
    /// alignment refused the frame.
    fn red_blue(
        &self,
        source: &impl PyramidFrameSource,
        j: usize,
        domain: PyramidDomain,
        levels: Levels,
        warps: Option<&WarpMap>,
    ) -> Result<Option<RedBlue>> {
        if let Some(hit) = self.cache.lock().unwrap_or_else(|e| e.into_inner()).get(&j) {
            return Ok(hit.clone());
        }
        let got = {
            let mut s = self
                .pool
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .pop()
                .unwrap_or_else(|| Scratch {
                    warp: WarpScratch::new(domain.full),
                    planes: (0..BAND_PLANES)
                        .map(|_| vec![0.0; domain.analysis().pixels()])
                        .collect(),
                    luma: vec![0.0; domain.analysis().pixels()],
                });
            let px = domain.analysis().pixels();
            for p in &mut s.planes {
                p.resize(px, 0.0);
            }
            let r = load_frame(
                &Direct(source),
                j,
                domain,
                levels,
                warps,
                None,
                &mut s.warp,
                None,
                &mut s.planes,
                &mut s.luma,
            )
            .map(|ok| {
                ok.then(|| {
                    let g = domain.analysis();
                    Arc::new(Borrowed {
                        planes: [s.planes[0].clone(), s.planes[3].clone()],
                        reg: self
                            .registered
                            .then(|| reg_band(&s.luma, g.width, g.height, 0.9 * levels.range())),
                    })
                })
            })
            .with_context(|| format!("axial colour: gathering frame {j}"));
            self.pool.lock().unwrap_or_else(|e| e.into_inner()).push(s);
            r?
        };
        Ok(self
            .cache
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .entry(j)
            .or_insert(got)
            .clone())
    }

    /// The frame a pixel of merged frame `index` borrows a channel from.
    fn pick(&self, field: &Field, index: usize, x: f64, y: f64) -> usize {
        let (u, v) = self.unit.uv(x, y);
        (index as f64 + field.at(u, v))
            .round()
            .clamp(0.0, (self.frames - 1) as f64) as usize
    }
}

/// Replace the coarse part of red and blue of merged frame `index` (already
/// gathered into `planes`, with its green `luma`) with that of the frames
/// where they focus. A no-op when the correction is not installed.
pub(super) fn apply(
    source: &impl PyramidFrameSource,
    index: usize,
    domain: PyramidDomain,
    levels: Levels,
    warps: Option<&WarpMap>,
    luma: &[f32],
    planes: &mut [Vec<f32>],
) -> Result<()> {
    let Some(ax) = active() else { return Ok(()) };
    ax.in_progress
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .insert(index);
    let result = (|| -> Result<()> {
        // Release frames no merged frame still in flight can need.
        let oldest = *ax
            .in_progress
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .first()
            .unwrap_or(&index);
        let keep_from = (oldest as f64 + ax.span.0).floor() as isize - 4;
        ax.cache
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .retain(|j, _| *j as isize >= keep_from);

        let g = domain.analysis();
        let (w, h) = (g.width, g.height);
        let (ox, oy) = (domain.rect.x as f64, domain.rect.y as f64);
        let channels = [(0usize, 0usize, ax.red), (1, 3, ax.blue)];
        // The frames this one borrows from. The fields are four-coefficient
        // surfaces, so a 32-px lattice (with the far edges) finds every frame
        // that owns more than a sliver; a pixel whose frame was missed keeps
        // its own value.
        let mut needed = BTreeSet::new();
        for (_, _, field) in channels.iter().filter(|c| c.2 != Field::ZERO) {
            for y in (0..h).step_by(32).chain([h - 1]) {
                for x in (0..w).step_by(32).chain([w - 1]) {
                    needed.insert(ax.pick(field, index, ox + x as f64, oy + y as f64));
                }
            }
        }
        needed.remove(&index);
        let (Some(&lo), Some(&hi)) = (needed.first(), needed.last()) else {
            return Ok(());
        };
        let mut window: Vec<Option<RedBlue>> = vec![None; hi - lo + 1];
        for &j in &needed {
            window[j - lo] = ax.red_blue(source, j, domain, levels, warps)?;
        }
        // Where each borrowed frame sits relative to this one.
        let mut shifts: Vec<Option<Shift>> = vec![None; window.len()];
        if ax.registered {
            let mine = reg_band(luma, w, h, 0.9 * levels.range());
            let (gx, gy) = gradient(&mine.band, w, h);
            for (slot, nb) in window.iter().enumerate() {
                let Some(band) = nb.as_ref().and_then(|nb| nb.reg.as_ref()) else {
                    continue;
                };
                shifts[slot] = register(&mine, &gx, &gy, band, w, h);
                let s = shifts[slot].as_ref();
                ax.pairs.lock().unwrap_or_else(|e| e.into_inner()).push((
                    (lo + slot).abs_diff(index),
                    s.map_or(0.0, |s| s.rms),
                    s.map_or(0, |s| s.measured),
                ));
            }
        }
        let refs: Vec<Option<[strehl_core::align::PlaneRef<'_>; 2]>> = window
            .iter()
            .map(|nb| {
                let nb = nb.as_ref()?;
                Some([
                    strehl_core::align::PlaneRef::new(&nb.planes[0], w, h)?,
                    strehl_core::align::PlaneRef::new(&nb.planes[1], w, h)?,
                ])
            })
            .collect();
        for (slot, plane, field) in channels {
            if field == Field::ZERO {
                continue;
            }
            // Borrowed minus own; zero where the pixel keeps its own value
            // (it borrows from itself, from a frame the lattice missed, or
            // from one the alignment refused).
            let mut diff = vec![0f32; w * h];
            let own = &planes[plane];
            diff.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                for (x, out) in row.iter_mut().enumerate() {
                    let j = ax.pick(&field, index, ox + x as f64, oy + y as f64);
                    if j == index || j < lo || j > hi {
                        continue;
                    }
                    let Some(nb) = &refs[j - lo] else {
                        continue;
                    };
                    let i = y * w + x;
                    let borrowed = match &shifts[j - lo] {
                        Some(s) => {
                            let (dx, dy) = s.at(x as f32, y as f32);
                            strehl_core::align::sample_catmull_rom(
                                nb[slot],
                                x as f64 + f64::from(dx),
                                y as f64 + f64::from(dy),
                            )
                        }
                        None => window[j - lo]
                            .as_ref()
                            .map_or(own[i], |nb| nb.planes[slot][i]),
                    };
                    *out = borrowed - own[i];
                }
            });
            let low = blur(&diff, w, h, SPLIT_SIGMA);
            planes[plane]
                .par_iter_mut()
                .zip(&low)
                .for_each(|(out, l)| *out += l);
        }
        Ok(())
    })();
    ax.in_progress
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .remove(&index);
    result
}

/// Experiment hook, inert unless `STREHL_AXIAL_DUMP=<dir>` is set: writes
/// every gathered frame's red, green-site-1 and blue planes (reference grid,
/// f32 little-endian, `[3, h, w]`, black-subtracted DN, before the axial
/// correction) to `<dir>/fNNN.f32` and the grid to `<dir>/geom.txt`. About
/// 180 MB per frame on the A7CR. Input of
/// `experiments/a7cr-full-potential-2026-11-14/axial-probe.py`.
pub(super) fn dump_if_requested(
    index: usize,
    domain: PyramidDomain,
    planes: &[Vec<f32>],
) -> Result<()> {
    let Ok(dir) = std::env::var(DUMP_ENV) else {
        return Ok(());
    };
    let dir = PathBuf::from(dir);
    std::fs::create_dir_all(&dir)?;
    let g = domain.analysis();
    std::fs::write(
        dir.join("geom.txt"),
        format!(
            "{} {} {} {}\n",
            g.width, g.height, domain.rect.x, domain.rect.y
        ),
    )?;
    let mut bytes = Vec::with_capacity(3 * 4 * g.pixels());
    for p in [0usize, 1, 3] {
        for v in &planes[p][..g.pixels()] {
            bytes.extend_from_slice(&v.to_le_bytes());
        }
    }
    std::fs::write(dir.join(format!("f{index:03}.f32")), bytes)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `blur` as it was before its horizontal pass was split into edge and
    /// interior loops: the bits must not move.
    fn blur_reference(src: &[f32], w: usize, h: usize, sigma: f64) -> Vec<f32> {
        let r = (3.0 * sigma).ceil() as isize;
        let k: Vec<f32> = (-r..=r)
            .map(|t| (-0.5 * (t as f64 / sigma).powi(2)).exp() as f32)
            .collect();
        let s: f32 = k.iter().sum();
        let k: Vec<f32> = k.iter().map(|v| v / s).collect();
        let mut tmp = vec![0f32; w * h];
        for (y, row) in tmp.chunks_mut(w).enumerate() {
            let line = &src[y * w..(y + 1) * w];
            for (x, o) in row.iter_mut().enumerate() {
                let mut acc = 0f32;
                for (t, kv) in k.iter().enumerate() {
                    let xx = (x as isize + t as isize - r).clamp(0, w as isize - 1) as usize;
                    acc += kv * line[xx];
                }
                *o = acc;
            }
        }
        let mut out = vec![0f32; w * h];
        for (y, row) in out.chunks_mut(w).enumerate() {
            for (t, kv) in k.iter().enumerate() {
                let yy = (y as isize + t as isize - r).clamp(0, h as isize - 1) as usize;
                let line = &tmp[yy * w..(yy + 1) * w];
                for (o, v) in row.iter_mut().zip(line) {
                    *o += kv * v;
                }
            }
        }
        out
    }

    #[test]
    fn blur_is_bit_identical_to_the_per_pixel_clamped_form() {
        for (w, h) in [(1, 3), (5, 4), (13, 9), (257, 11)] {
            let src: Vec<f32> = (0..w * h)
                .map(|i| ((i * 2654435761usize) % 10007) as f32 * 0.37 - 900.0)
                .collect();
            for sigma in [1.0, 3f64.sqrt(), 12f64.sqrt(), 7.5] {
                let a = blur(&src, w, h, sigma);
                let b = blur_reference(&src, w, h, sigma);
                assert!(
                    a.iter().zip(&b).all(|(a, b)| a.to_bits() == b.to_bits()),
                    "{w}x{h} sigma {sigma}"
                );
            }
        }
    }

    #[test]
    fn a_planted_gaussian_peak_is_found_to_a_tenth_of_a_frame() {
        for centre in [10.3, 20.0, 31.75] {
            let curve: Vec<f64> = (0..48)
                .map(|k| 3.0 + 40.0 * (-0.5 * ((k as f64 - centre) / 5.0).powi(2)).exp())
                .collect();
            let (k, contrast) = peak(&curve).expect("a clean peak");
            assert!((k - centre).abs() < 0.1, "planted {centre}, found {k}");
            assert!(contrast > 5.0);
        }
    }

    #[test]
    fn a_peak_at_the_end_of_the_stack_or_a_flat_curve_is_refused() {
        let edge: Vec<f64> = (0..40)
            .map(|k| 1.0 + 10.0 * (-0.5 * ((k as f64 - 39.0) / 4.0).powi(2)).exp())
            .collect();
        assert!(peak(&edge).is_none());
        assert!(peak(&[5.0; 40]).is_none());
    }

    #[test]
    fn the_field_fit_recovers_a_planted_radial_offset_despite_outliers() {
        let mut rows = Vec::new();
        for i in 0..20 {
            for j in 0..14 {
                let (u, v) = (i as f64 / 10.0 - 0.95, j as f64 / 10.0 - 0.65);
                let mut d = 5.5 - 3.0 * (u * u + v * v) + 0.2 * u;
                if (i + j) % 17 == 0 {
                    d += 9.0;
                }
                rows.push((u, v, d, 1.0));
            }
        }
        let (c, _) = fit_field(&rows).expect("enough tiles");
        assert!(
            (c[0] - 5.5).abs() < 0.05 && (c[3] + 3.0).abs() < 0.05 && (c[1] - 0.2).abs() < 0.05,
            "{c:?}"
        );
    }

    #[test]
    fn the_placebo_field_is_the_mirror_of_the_measured_one() {
        let f = Field {
            coef: [5.0, 0.5, -0.25, -1.0],
            lo: 3.5,
            hi: 6.5,
        };
        let m = f.flipped();
        for (u, v) in [(0.0, 0.0), (0.7, -0.3), (-1.0, 1.0)] {
            assert_eq!(m.at(u, v), -f.at(u, v));
        }
    }

    #[test]
    fn a_curve_is_read_between_frames_and_held_at_its_ends() {
        let c = [1.0, 3.0, 2.0];
        assert_eq!(value_at(&c, 0.5), 2.0);
        assert_eq!(value_at(&c, 1.75), 2.25);
        assert_eq!(value_at(&c, -4.0), 1.0);
        assert_eq!(value_at(&c, 9.0), 2.0);
    }

    #[test]
    fn the_field_is_clamped_to_the_measured_range() {
        let f = Field {
            coef: [1.0, 0.0, 0.0, 100.0],
            lo: 0.0,
            hi: 3.0,
        };
        assert_eq!(f.at(0.0, 0.0), 1.0);
        assert_eq!(f.at(1.0, 1.0), 3.0);
    }

    /// A band-limited texture, and the same texture as a frame whose content
    /// sits at `x + d(x)`: a translation plus a scale about the centre.
    fn textured_pair(w: usize, h: usize, t: [f64; 2], scale: f64) -> (Vec<f32>, Vec<f32>) {
        let waves: Vec<(f64, f64, f64)> = (0..48)
            .map(|i| {
                let a = 0.61803398875 * i as f64 * std::f64::consts::TAU;
                let period = 7.0 + (i % 9) as f64 * 2.5;
                let k = std::f64::consts::TAU / period;
                (k * a.cos(), k * a.sin(), 1.7 * i as f64)
            })
            .collect();
        let f = |x: f64, y: f64| -> f32 {
            (1000.0
                + 40.0
                    * waves
                        .iter()
                        .map(|(kx, ky, p)| (kx * x + ky * y + p).cos())
                        .sum::<f64>()) as f32
        };
        let (cx, cy) = ((w as f64 - 1.0) / 2.0, (h as f64 - 1.0) / 2.0);
        let mut own = vec![0f32; w * h];
        let mut borrowed = vec![0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                let (xf, yf) = (x as f64, y as f64);
                own[y * w + x] = f(xf, yf);
                // Content at p in `own` is at p + d(p) in `borrowed`, so
                // borrowed(q) = own(q - d) to first order in d.
                let d = [t[0] + scale * (xf - cx), t[1] + scale * (yf - cy)];
                borrowed[y * w + x] = f(xf - d[0], yf - d[1]);
            }
        }
        (own, borrowed)
    }

    #[test]
    fn a_planted_shift_and_scale_between_two_frames_is_registered() {
        let (w, h) = (640, 448);
        for (t, scale) in [
            ([0.30, -0.20], 0.0),
            ([-0.15, 0.40], 4e-4),
            ([0.0, 0.0], 0.0),
        ] {
            let (own, borrowed) = textured_pair(w, h, t, scale);
            let mine = reg_band(&own, w, h, 1e9);
            let (gx, gy) = gradient(&mine.band, w, h);
            let s = register(&mine, &gx, &gy, &reg_band(&borrowed, w, h, 1e9), w, h)
                .expect("a textured pair registers");
            assert_eq!(s.measured, (w / TILE) * (h / TILE));
            for (x, y) in [(100.0f32, 100.0f32), (320.0, 224.0), (560.0, 380.0)] {
                let want = [
                    t[0] + scale * (f64::from(x) - (w as f64 - 1.0) / 2.0),
                    t[1] + scale * (f64::from(y) - (h as f64 - 1.0) / 2.0),
                ];
                let got = s.at(x, y);
                assert!(
                    (f64::from(got.0) - want[0]).abs() < 0.03
                        && (f64::from(got.1) - want[1]).abs() < 0.03,
                    "planted {want:?} at ({x}, {y}), registered {got:?}"
                );
            }
        }
    }

    #[test]
    fn a_frame_with_no_texture_or_all_clipped_is_not_registered() {
        let (w, h) = (640, 448);
        let (own, borrowed) = textured_pair(w, h, [0.3, 0.1], 0.0);
        let flat = vec![500f32; w * h];
        let mine = reg_band(&own, w, h, 1e9);
        let (gx, gy) = gradient(&mine.band, w, h);
        assert!(register(&mine, &gx, &gy, &reg_band(&flat, w, h, 1e9), w, h).is_none());
        // Every sample at or above the clip level: nothing is kept.
        let clipped = reg_band(&borrowed, w, h, 0.0);
        assert!(clipped.keep.iter().all(|k| *k == 0));
        assert!(register(&mine, &gx, &gy, &clipped, w, h).is_none());
    }

    #[test]
    fn the_switch_parses_its_values_and_refuses_a_typo() {
        for (v, want) in [
            ("on", Some(Mode::On)),
            (" 1 ", Some(Mode::On)),
            ("off", Some(Mode::Off)),
            ("0", Some(Mode::Off)),
            ("", Some(Mode::Off)),
            ("placebo", Some(Mode::Placebo)),
            ("unregistered", Some(Mode::Unregistered)),
            ("yes", None),
        ] {
            assert_eq!(parse(v).ok(), want, "{v:?}");
        }
    }
}
