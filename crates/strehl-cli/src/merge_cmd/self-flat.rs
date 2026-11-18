//! The sensor's response pattern, mapped from the stack's own raw frames and
//! divided out at the gather (`STREHL_SELF_FLAT`): off by default.
//!
//! # Why
//!
//! Every photosite has its own response error: 0.30 / 0.35 / 0.40 % of level
//! for red / green / blue photosites on the A7CR, nearly white and stable
//! from day to day. A four-shot group reads each photosite four times at four
//! adjacent output pixels, so the error lands on a 2 x 2 block and in green
//! midtones carries about as much power as photon noise in the default
//! output at 0.08-0.30 cycles/px; it does not average down across
//! neighbouring planes, which move it only 0.1-0.4 px
//! (`experiments/a7cr-fourshot-quality-2026-11-16/results.md` Q2; proposal
//! item 1).
//!
//! # How
//!
//! The scene slides across the sensor as focus moves, so the pattern is the
//! part of every raw frame's high-pass that stays on the photosite. One pass
//! over every raw frame of the stack (every member of a four-shot group),
//! per CFA plane of the decoded buffer: `r = M / gauss(M, 2) - 1`, weight
//! `1 / max(gauss(r^2, 4), the injected noise model's energy)` (so textured
//! samples count little rather than not at all; a hard smoothness gate
//! rejects bright smooth areas, where the pattern matters most), zero below
//! 150 DN and within 12 plane px of a sample near clipping. Per photosite,
//! `map = sum(w r) / (sum(w) + 1 / kappa^2)`: a photosite rarely seen smooth
//! is pulled toward no correction instead of receiving a noisy one.
//!
//! The planes are cut into segments; each frame is corrected with the map
//! accumulated from the segments that are neither its own nor adjacent
//! (with fewer than four segments, not its own), so a photosite's map
//! carries no detail that was in focus on it in the frames it corrects.
//!
//! MEASURED with the prototype (`self-flat.py`, round 2 R1): a map from the
//! 392 raw frames of planes 1-98, applied to raw frames of planes 120-193,
//! left 17 / 10 / 10 % of the pattern's power (R / G / B); the map rolled by
//! (5, 3) photosites raised it to 155-186 %.
//!
//! `placebo` applies the map rolled by (5, 3) photosites (a control arm).
use super::*;
use std::sync::Arc;
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};

pub(super) const ENV: &str = "STREHL_SELF_FLAT";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Mode {
    Off,
    On,
    Placebo,
}

pub(super) fn mode() -> Result<Mode> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(Mode::Off),
        Err(e) => Err(e).context(ENV),
        Ok(v) => match v.trim() {
            "" | "0" | "off" => Ok(Mode::Off),
            "1" | "on" => Ok(Mode::On),
            "placebo" => Ok(Mode::Placebo),
            other => anyhow::bail!("{ENV}={other:?} is not off, on or placebo"),
        },
    }
}

/// Gaussian sigma (plane px) of the local level the residual is taken from.
const SIGMA_LEVEL: f32 = 2.0;
/// Gaussian sigma (plane px) of the local energy the weight is taken from.
const SIGMA_ENERGY: f32 = 4.0;
/// Samples whose local level is below this (DN above black) carry no weight.
const MIN_LEVEL: f32 = 150.0;
/// A sample within this many plane px of one above [`CLIP_FRACTION`] of the
/// range carries no weight.
const CLIP_RADIUS: usize = 12;
const CLIP_FRACTION: f32 = 0.909;
/// Fewest focal planes a map is built from: shorter stacks are left
/// uncorrected, and the banner says so. A guess, not a measurement (the
/// scarab's 196 planes reached full weight on 97 % of photosites from half
/// of them).
const MIN_PLANES: usize = 24;
/// Raw frames decoded at once.
const DECODE_BATCH: usize = 16;

/// Expected size of the response pattern (fraction of level) for R, G, B
/// photosites: the shrinkage's prior. MEASURED on the A7CR (`prnu.py`,
/// high-passed at 2 plane px); other bodies get the A7CR's green figure, and
/// the banner says it was assumed.
fn kappa(camera: &str) -> ([f32; 3], bool) {
    if camera.contains("ILCE-7CR") {
        ([0.0030, 0.0035, 0.0040], true)
    } else {
        ([0.0035; 3], false)
    }
}

/// The maps of one stack: per segment, the factor every raw sample of a
/// frame in that segment is multiplied by, `1 / (1 + map)`, over the whole
/// decoded buffer (`stride x buffer_height`; 1 where nothing was measured).
pub(crate) struct Maps {
    key: (PathBuf, usize, Mode),
    segments: Vec<Arc<Vec<f32>>>,
    plane_segment: Vec<usize>,
}

static CACHE: Mutex<Option<Arc<Maps>>> = Mutex::new(None);
static ACTIVE: AtomicBool = AtomicBool::new(false);

/// The factor map for focal plane `index`, while a render has one installed.
pub(super) fn map_for(index: usize) -> Option<Arc<Vec<f32>>> {
    if !ACTIVE.load(Ordering::Relaxed) {
        return None;
    }
    let cache = CACHE.lock().unwrap_or_else(|e| e.into_inner());
    let maps = cache.as_ref()?;
    let s = *maps.plane_segment.get(index)?;
    Some(maps.segments[s].clone())
}

/// Check a map against a decoded frame's buffer.
pub(crate) fn check_geometry(map: &[f32], frame: &strehl_raw::Frame) -> Result<()> {
    ensure!(
        map.len() == frame.stride * frame.buffer_height,
        "{ENV}: the response map covers {} samples, but {} has a {}x{} buffer",
        map.len(),
        frame.path.display(),
        frame.stride,
        frame.buffer_height
    );
    Ok(())
}

/// Clears the installed map when the render ends, however it ends. The maps
/// stay cached for a second pass over the same stack (the lateral-CA
/// refinement renders twice).
pub(super) struct Active;

impl Drop for Active {
    fn drop(&mut self) {
        ACTIVE.store(false, Ordering::Relaxed);
    }
}

/// Build (or reuse) the maps for this stack and install them, when asked.
pub(super) fn install_if_requested(
    paths: &[PathBuf],
    groups: Option<&crate::pixel_shift_cmd::StackGroups>,
    noise: &NoiseModel,
    camera: &str,
) -> Result<Option<Active>> {
    let m = mode()?;
    if m == Mode::Off {
        return Ok(None);
    }
    let Some(first) = paths.first() else {
        return Ok(None);
    };
    if paths.len() < MIN_PLANES {
        eprintln!(
            "self flat field: NOT APPLIED -- {ENV} set, but {} focal planes are too few to carry \
             the scene across the sensor (at least {MIN_PLANES})",
            paths.len()
        );
        return Ok(None);
    }
    let key = (first.clone(), paths.len(), m);
    {
        let cache = CACHE.lock().unwrap_or_else(|e| e.into_inner());
        if cache.as_ref().is_some_and(|c| c.key == key) {
            eprintln!(
                "self flat field: {m:?} -- the response maps built for this stack are reused"
            );
            ACTIVE.store(true, Ordering::Relaxed);
            return Ok(Some(Active));
        }
    }
    let maps = build(paths, groups, noise, camera, m, key)?;
    *CACHE.lock().unwrap_or_else(|e| e.into_inner()) = Some(Arc::new(maps));
    ACTIVE.store(true, Ordering::Relaxed);
    Ok(Some(Active))
}

/// The CFA colour (0 R, 1 G, 2 B) and noise plane of buffer parity `(dx, dy)`.
fn parity_colour(frame: &strehl_raw::Frame, dx: usize, dy: usize) -> (usize, CfaPlane) {
    let (lx, ly) = ((dx + frame.active.x) % 2, (dy + frame.active.y) % 2);
    match (lx, ly) {
        (0, 0) => (0, CfaPlane::R),
        (1, 0) => (1, CfaPlane::G1),
        (0, 1) => (1, CfaPlane::G2),
        _ => (2, CfaPlane::B),
    }
}

fn taps(sigma: f32) -> Vec<f32> {
    let r = (3.5 * sigma).ceil() as isize;
    let mut t: Vec<f32> = (-r..=r)
        .map(|k| (-((k * k) as f32) / (2.0 * sigma * sigma)).exp())
        .collect();
    let s: f32 = t.iter().sum();
    t.iter_mut().for_each(|v| *v /= s);
    t
}

#[inline]
fn reflect(v: isize, n: usize) -> usize {
    let n = n as isize;
    let mut v = v;
    while v < 0 || v >= n {
        v = if v < 0 { -v - 1 } else { 2 * n - 1 - v };
    }
    v as usize
}

/// Separable convolution of a `w x h` plane with `k` on both axes,
/// reflecting at the border. `tmp` and `out` are resized.
fn separable(src: &[f32], w: usize, h: usize, k: &[f32], tmp: &mut Vec<f32>, out: &mut Vec<f32>) {
    let r = k.len() / 2;
    tmp.resize(w * h, 0.0);
    out.resize(w * h, 0.0);
    tmp.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        let s = &src[y * w..(y + 1) * w];
        row.iter_mut().for_each(|v| *v = 0.0);
        if w > 2 * r {
            for (j, t) in k.iter().enumerate() {
                let (o, i) = (&mut row[r..w - r], &s[j..j + w - 2 * r]);
                for (a, b) in o.iter_mut().zip(i) {
                    *a += t * b;
                }
            }
        }
        for x in (0..r.min(w)).chain(w.saturating_sub(r).max(r.min(w))..w) {
            row[x] = k
                .iter()
                .enumerate()
                .map(|(j, t)| t * s[reflect(x as isize + j as isize - r as isize, w)])
                .sum();
        }
    });
    let tmp = &*tmp;
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        row.iter_mut().for_each(|v| *v = 0.0);
        for (j, t) in k.iter().enumerate() {
            let yy = reflect(y as isize + j as isize - r as isize, h);
            for (a, b) in row.iter_mut().zip(&tmp[yy * w..(yy + 1) * w]) {
                *a += t * b;
            }
        }
    });
}

/// Gaussian blur of a `w x h` plane at `sigma` px (taps to 3.5 sigma),
/// reflecting at the border; `sigma <= 0` copies.
pub(super) fn gaussian(src: &[f32], w: usize, h: usize, sigma: f32) -> Vec<f32> {
    if sigma <= 0.0 {
        return src.to_vec();
    }
    let (mut tmp, mut out) = (Vec::new(), Vec::new());
    separable(src, w, h, &taps(sigma), &mut tmp, &mut out);
    out
}

/// Per-thread-free working planes for one CFA plane of one frame.
#[derive(Default)]
struct Work {
    m: Vec<f32>,
    s: Vec<f32>,
    rr: Vec<f32>,
    e: Vec<f32>,
    tmp: Vec<f32>,
    near: Vec<f32>,
}

/// Add one raw frame's weighted residuals to `num` and `den` (buffer layout).
#[allow(clippy::too_many_arguments)]
fn accumulate(
    frame: &strehl_raw::Frame,
    noise: &NoiseModel,
    hp: f32,
    k_level: &[f32],
    k_energy: &[f32],
    work: &mut Work,
    num: &mut [f32],
    den: &mut [f32],
) {
    let (stride, bh) = (frame.stride, frame.buffer_height);
    let (w, h) = (stride / 2, bh / 2);
    let black = frame.levels.black;
    let clip = CLIP_FRACTION * (frame.levels.white - black);
    for (dx, dy) in [(0usize, 0usize), (1, 0), (0, 1), (1, 1)] {
        let (_, plane) = parity_colour(frame, dx, dy);
        work.m.resize(w * h, 0.0);
        work.m.par_chunks_mut(w).enumerate().for_each(|(j, row)| {
            let base = (2 * j + dy) * stride + dx;
            for (i, v) in row.iter_mut().enumerate() {
                *v = frame.data[base + 2 * i] as f32 - black;
            }
        });
        let Work {
            m,
            s,
            rr,
            e,
            tmp,
            near,
        } = &mut *work;
        separable(m, w, h, k_level, tmp, s);
        s.par_iter_mut().for_each(|v| *v = v.max(1.0));
        rr.resize(w * h, 0.0);
        rr.par_iter_mut()
            .zip(m.par_iter().zip(s.par_iter()))
            .for_each(|(o, (mv, sv))| {
                let r = mv / sv - 1.0;
                *o = r * r;
            });
        separable(rr, w, h, k_energy, tmp, e);
        // Near clipping: a box count of samples above the clip level, only
        // when any sample of this plane reaches it.
        let clipped = m.par_iter().any(|v| *v > clip);
        if clipped {
            near.resize(w * h, 0.0);
            near.par_iter_mut()
                .zip(m.par_iter())
                .for_each(|(o, v)| *o = if *v > clip { 1.0 } else { 0.0 });
            let boxk = vec![1.0f32; 2 * CLIP_RADIUS + 1];
            let src = std::mem::take(near);
            let mut out = Vec::new();
            separable(&src, w, h, &boxk, tmp, &mut out);
            *near = out;
        }
        let (m, s, e, near) = (&*m, &*s, &*e, &*near);
        // Rows of the buffer for this parity, in parallel; each row writes
        // only its own buffer samples.
        num.par_chunks_mut(stride)
            .zip(den.par_chunks_mut(stride))
            .enumerate()
            .filter(|(y, _)| y % 2 == dy && y / 2 < h)
            .for_each(|(y, (nrow, drow))| {
                let j = y / 2;
                for i in 0..w {
                    let p = j * w + i;
                    let sv = s[p];
                    if sv <= MIN_LEVEL || (clipped && near[p] > 0.5) {
                        continue;
                    }
                    let r = m[p] / sv - 1.0;
                    let v = noise.variance(plane, sv) / (sv * sv) * hp;
                    let wgt = hp / e[p].max(v);
                    if wgt.is_finite() {
                        nrow[2 * i + dx] += wgt * r;
                        drow[2 * i + dx] += wgt;
                    }
                }
            });
    }
}

fn build(
    paths: &[PathBuf],
    groups: Option<&crate::pixel_shift_cmd::StackGroups>,
    noise: &NoiseModel,
    camera: &str,
    m: Mode,
    key: (PathBuf, usize, Mode),
) -> Result<Maps> {
    let t0 = Instant::now();
    let planes = paths.len();
    let segments = (planes / 32).clamp(2, 6);
    let segment_of = |i: usize| i * segments / planes;
    let neighbours = segments >= 4;
    let mut frames: Vec<(usize, PathBuf)> = Vec::new();
    for (i, p) in paths.iter().enumerate() {
        frames.push((i, p.clone()));
        if let Some(members) = groups.and_then(|g| g.members_of(p)) {
            frames.extend(members.iter().map(|q| (i, q.clone())));
        }
    }
    let first = strehl_raw::decode(&paths[0]).context("self flat field: decoding")?;
    let (stride, bh) = (first.stride, first.buffer_height);
    let levels = first.levels;
    let active = first.active;
    drop(first);
    let n = stride * bh;
    let mut num: Vec<Vec<f32>> = (0..segments).map(|_| vec![0.0f32; n]).collect();
    let mut den: Vec<Vec<f32>> = (0..segments).map(|_| vec![0.0f32; n]).collect();
    let k_level = taps(SIGMA_LEVEL);
    let k_energy = taps(SIGMA_ENERGY);
    // The high-pass's factor on white noise, `1 - 2 k0 + sum k^2` for the
    // 2-D Gaussian (`k0` its centre weight).
    let c = k_level.iter().copied().fold(0.0f32, f32::max);
    let sq: f32 = k_level.iter().map(|v| v * v).sum();
    let hp = 1.0 - 2.0 * c * c + sq * sq;
    let mut work = Work::default();
    for batch in frames.chunks(DECODE_BATCH) {
        let decoded: Vec<strehl_raw::Frame> = batch
            .par_iter()
            .map(|(_, p)| strehl_raw::decode(p).with_context(|| p.display().to_string()))
            .collect::<Result<_>>()?;
        for ((i, _), f) in batch.iter().zip(&decoded) {
            ensure!(
                f.stride == stride && f.buffer_height == bh && f.levels == levels,
                "{ENV}: {} disagrees with the stack's buffer geometry or levels",
                f.path.display()
            );
            let s = segment_of(*i);
            accumulate(
                f,
                noise,
                hp,
                &k_level,
                &k_energy,
                &mut work,
                &mut num[s],
                &mut den[s],
            );
        }
    }
    drop(work);
    let (kap, measured_kappa) = kappa(camera);
    let colour_at = |idx: usize| -> usize {
        let (bx, by) = (idx % stride, idx / stride);
        let (lx, ly) = ((bx + active.x) % 2, (by + active.y) % 2);
        match (lx, ly) {
            (0, 0) => 0,
            (1, 1) => 2,
            _ => 1,
        }
    };
    let prior: [f32; 3] = kap.map(|k| 1.0 / (k * k));
    let mut maps = Vec::with_capacity(segments);
    // Report over the active area of the first segment's map.
    let mut report: Option<[(f64, f64, usize, usize); 3]> = None;
    for s in 0..segments {
        let used: Vec<usize> = (0..segments)
            .filter(|t| {
                if neighbours {
                    t.abs_diff(s) > 1
                } else {
                    *t != s
                }
            })
            .collect();
        let mut map = vec![0.0f32; n];
        map.par_chunks_mut(stride).enumerate().for_each(|(y, row)| {
            for (x, o) in row.iter_mut().enumerate() {
                let idx = y * stride + x;
                let (nv, dv) = used.iter().fold((0.0f32, 0.0f32), |(a, b), t| {
                    (a + num[*t][idx], b + den[*t][idx])
                });
                *o = if dv > 0.0 {
                    nv / (dv + prior[colour_at(idx)])
                } else {
                    0.0
                };
            }
        });
        if s == 0 {
            let mut acc = [(0.0f64, 0.0f64, 0usize, 0usize); 3];
            for y in (active.y..active.y + active.height).step_by(7) {
                for x in (active.x..active.x + active.width).step_by(3) {
                    let idx = y * stride + x;
                    let c = colour_at(idx);
                    let dv: f32 = used.iter().map(|t| den[*t][idx]).sum();
                    let trust = dv / (dv + prior[c]);
                    acc[c].0 += f64::from(map[idx]).powi(2);
                    acc[c].1 += f64::from(trust);
                    acc[c].2 += 1;
                    if trust < 0.5 {
                        acc[c].3 += 1;
                    }
                }
            }
            report = Some(acc);
        }
        // Factor, and the placebo's roll by (5, 3) photosites of the same
        // colour (10, 6 buffer samples).
        let factor: Vec<f32> = (0..n)
            .into_par_iter()
            .map(|idx| {
                let src = if m == Mode::Placebo {
                    let (x, y) = (idx % stride, idx / stride);
                    (x >= 10 && y >= 6).then(|| (y - 6) * stride + x - 10)
                } else {
                    Some(idx)
                };
                src.map_or(1.0, |i| 1.0 / (1.0 + map[i]))
            })
            .collect();
        maps.push(Arc::new(factor));
    }
    drop(num);
    drop(den);
    let plane_segment = (0..planes).map(segment_of).collect();
    eprintln!(
        "self flat field: {} -- response maps from {} raw frames of {planes} focal planes, {segments} \
         segments, each frame corrected by the map of the segments {} its own; kappa R/G/B \
         {:.2}/{:.2}/{:.2} % ({}); {:.1} s",
        match m {
            Mode::Placebo => "PLACEBO (map rolled by 5, 3 photosites)",
            _ => "ON",
        },
        frames.len(),
        if neighbours {
            "neither adjacent to nor"
        } else {
            "other than"
        },
        kap[0] * 100.0,
        kap[1] * 100.0,
        kap[2] * 100.0,
        if measured_kappa {
            "measured on this body model"
        } else {
            "ASSUMED: no measured pattern size for this body"
        },
        t0.elapsed().as_secs_f64()
    );
    if let Some(acc) = report {
        for (c, name) in ["R", "G", "B"].iter().enumerate() {
            let (sq, trust, k, low) = acc[c];
            if k > 0 {
                eprintln!(
                    "                  {name}: map rms {:.3} %, mean trust {:.3}, {:.1} % of photosites \
                     under half trust (segment 0's map, sampled)",
                    100.0 * (sq / k as f64).sqrt(),
                    trust / k as f64,
                    100.0 * low as f64 / k as f64
                );
            }
        }
    }
    Ok(Maps {
        key,
        segments: maps,
        plane_segment,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn separable_matches_a_direct_sum() {
        let (w, h) = (37usize, 23usize);
        let src: Vec<f32> = (0..w * h).map(|i| ((i * 7919) % 101) as f32).collect();
        let k = taps(2.0);
        let (mut tmp, mut out) = (Vec::new(), Vec::new());
        separable(&src, w, h, &k, &mut tmp, &mut out);
        let r = (k.len() / 2) as isize;
        for y in 0..h {
            for x in 0..w {
                let mut want = 0.0f64;
                for (j, a) in k.iter().enumerate() {
                    for (i, b) in k.iter().enumerate() {
                        let yy = reflect(y as isize + j as isize - r, h);
                        let xx = reflect(x as isize + i as isize - r, w);
                        want += f64::from(*a) * f64::from(*b) * f64::from(src[yy * w + xx]);
                    }
                }
                let got = f64::from(out[y * w + x]);
                assert!(
                    (got - want).abs() < 1e-3 * want.abs().max(1.0),
                    "{x},{y}: {got} vs {want}"
                );
            }
        }
    }

    #[test]
    fn reflect_stays_inside() {
        for n in [1usize, 2, 5] {
            for v in -12isize..12 {
                assert!(reflect(v, n) < n);
            }
        }
    }
}
