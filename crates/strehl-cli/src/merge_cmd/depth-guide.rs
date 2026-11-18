//! Depth-guided fusion for the pyramid merge (`STREHL_FUSION=depth`, default
//! off). The weights are `strehl_core::pyramid::DepthGuide`'s; this module
//! measures what they need from the stack itself, before the fold.
//!
//! # Why
//!
//! On the A7CR scarab stack the A7CR full-potential prototype's fusion
//! (`experiments/a7cr-full-potential-2026-11-14/`, arm `m1c`), run on the same
//! demosaiced single shots the shipped merge folds, read 1.05 / 1.26 / 1.26
//! times the shipped stack's fine-detail signal at 0.47-0.55 of its noise
//! (same-capture halves). The shipped merge elects per coefficient from that
//! coefficient's own noisy energy; the prototype weights every frame by its
//! measured through-focus transfer at its distance from a focus plane
//! measured once from the whole stack.
//!
//! # The measurement
//!
//! Every placed frame is gathered exactly as the fold gathers it
//! (`load_frame`: decode, warp, lateral colour), and its green luma split
//! into three bands (Gaussian differences, sigma 0-1, 1-2 and 2-4 plane px:
//! the pyramid's three finest levels). Each band's energy is averaged over
//! cells of `CELL` plane px. Per cell, the through-focus peak of the middle
//! band (the axial-colour module's log-parabola) is the focus plane, its
//! contrast the confidence; weak cells are filled by confidence-weighted
//! smoothing at growing radii. Each band has its own map.
//!
//! The transfer width is the COHERENT one (`Coherence`): in sampled tiles,
//! the band product of frames `j` apart about the tile's focus, over the
//! product of frames one apart, fitted with `exp(-(j^2 - 1) / 2 s^2)`.
//! Products of different frames carry no noise, and they include whatever
//! keeps two frames from adding up -- residual misregistration, highlight
//! walk -- which the energy curve (printed for reference) cannot see. Coarser
//! levels extrapolate the third band's width by `COARSER` per octave.
//!
//! # Measured (A7CR scarab, single-shot run, 2026-11-15)
//!
//! Odd/even half-stacks, ratios to the default merge's halves
//! (`experiments/a7cr-full-potential-2026-11-14/results.md`): finest-band
//! detail (0.25-0.40 cycles per sensor px) 0.78-0.80, its noise 0.53-0.54,
//! signal-to-noise power 2.15x; mid band 0.90-0.93. Widths scaled by
//! `STREHL_FUSION_WIDTH` trace the trade: 0.3 reads 1.03-1.06 detail at 0.85
//! noise, 0.18 reads 1.11-1.15 at 1.0. The finest sensor-scale detail lives
//! above the half-resolution planes' own bands, decorrelates between frames
//! faster than the finest band this module can measure, and so is blended
//! slightly too wide: the fusion is meant to be followed by restoration
//! that knows its transfer (`STREHL_OPTICAL_RESTORE`, `optical-restore.rs`).
//! With it, the single-shot scarab reads 1.23 / 1.06 / 0.82 the default's
//! finest detail at 0.82 / 0.70 / 0.55 its noise; with colour carry on the
//! four-shot run, 1.16-1.38x plain pixel shift's detail at 0.60-0.78x its
//! noise. Still off by default: one subject, not independently reviewed.
//!
//! # Limits
//!
//! One extra gather of every frame (about the fold's own cost). Red and blue
//! take green's weights; where their focus differs (axial colour) the blend
//! leaves a faint coloured rim at bright-on-dark edges. Refused with the GPU
//! fold, temporal energy, hard-max selection and the estimator; skipped in
//! the lateral-CA refinement preview (that pass only measures channel
//! alignment).
use super::*;
use std::sync::{Arc, RwLock};
use strehl_core::pyramid::{DepthGuide, LevelSize};

pub(super) const ENV: &str = "STREHL_FUSION";
/// Experiment-only multiplier on every measured transfer width.
pub(super) const WIDTH_ENV: &str = "STREHL_FUSION_WIDTH";
/// Cell edge of the depth map, plane px.
const CELL: usize = 8;
/// Weights below this transfer are zero (the prototype's floor).
const FLOOR: f32 = 0.3;
/// Width growth per octave past the third band.
const COARSER: f32 = 1.25;
/// Cells with a peak contrast below this do not inform the depth map or the
/// widths.
const MIN_CONTRAST: f64 = 1.0;
/// Coherence sampling: tiles of this edge (plane px), every `COH_STRIDE`-th
/// tile in each direction, frame pairs up to `MAX_LAG` apart.
const COH_TILE: usize = 64;
const COH_STRIDE: usize = 3;
const MAX_LAG: usize = 12;

fn requested_mode() -> Result<bool> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Err(e) => Err(e).context(ENV),
        Ok(v) => match v.trim() {
            "" | "0" | "off" | "election" => Ok(false),
            "depth" => Ok(true),
            // Calibrated fusion (`fusion_calibrated`): its first pass is the
            // plain election, its second the fusion.
            "calibrated" => Ok(!fusion_calibrated::election_pass()),
            other => anyhow::bail!("{ENV}={other:?} is not off, depth or calibrated"),
        },
    }
}

/// Whether the operator asked for depth-guided fusion.
pub(super) fn requested() -> Result<bool> {
    requested_mode()
}

/// Experiment control: `election` leaves levels past the three measured
/// ones to the merge's own election; `guide` (the default) guides them all.
pub(super) const COARSE_ENV: &str = "STREHL_FUSION_COARSE";

fn coarse_election() -> Result<bool> {
    match std::env::var(COARSE_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Err(e) => Err(e).context(COARSE_ENV),
        Ok(v) => match v.trim() {
            "" | "guide" => Ok(false),
            "election" => Ok(true),
            other => anyhow::bail!("{COARSE_ENV}={other:?} is not guide or election"),
        },
    }
}

fn width_scale() -> Result<f32> {
    match std::env::var(WIDTH_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(1.0),
        Err(e) => Err(e).context(WIDTH_ENV),
        Ok(v) => {
            let s: f32 = v
                .trim()
                .parse()
                .with_context(|| format!("{WIDTH_ENV}={v:?}"))?;
            ensure!(s.is_finite() && s > 0.0, "{WIDTH_ENV} must be positive");
            Ok(s)
        }
    }
}

static ACTIVE: RwLock<Option<Arc<DepthGuide>>> = RwLock::new(None);

/// The installed guide, if this render uses one.
pub(super) fn active() -> Option<Arc<DepthGuide>> {
    ACTIVE.read().unwrap_or_else(|e| e.into_inner()).clone()
}

/// Clears the installed guide when the render ends, however it ends.
pub(super) struct Installed;

impl Drop for Installed {
    fn drop(&mut self) {
        *ACTIVE.write().unwrap_or_else(|e| e.into_inner()) = None;
    }
}

/// The three band images of one luma plane (Gaussian differences, sigma 0-1,
/// 1-2 and 2-4 plane px).
fn band_images(luma: &[f32], w: usize, h: usize) -> [Vec<f32>; 3] {
    let [d0, d1, g2] = two_band_images(luma, w, h);
    let g4 = axial_colour::blur(&g2, w, h, 12f64.sqrt());
    [d0, d1, difference(&g2, &g4)]
}

fn difference(a: &[f32], b: &[f32]) -> Vec<f32> {
    a.par_iter().zip(b).map(|(a, b)| a - b).collect()
}

/// The first two of [`band_images`] (the only ones the optical restoration's
/// tile plan reads), and the sigma-2 blur the third would start from.
fn two_band_images(luma: &[f32], w: usize, h: usize) -> [Vec<f32>; 3] {
    let g1 = axial_colour::blur(luma, w, h, 1.0);
    let g2 = axial_colour::blur(&g1, w, h, 3f64.sqrt());
    [difference(luma, &g1), difference(&g1, &g2), g2]
}

/// Band energies per cell: `[band][cell]`.
fn cell_energy(bands: &[Vec<f32>; 3], w: usize, h: usize) -> [Vec<f32>; 3] {
    let [a, b, c] = bands;
    [
        cell_energy_of(a, w, h),
        cell_energy_of(b, w, h),
        cell_energy_of(c, w, h),
    ]
}

/// One band image's mean square per `CELL x CELL` cell.
fn cell_energy_of(band: &[f32], w: usize, h: usize) -> Vec<f32> {
    let (cw, ch) = (w / CELL, h / CELL);
    let pool = |a: &[f32]| -> Vec<f32> {
        (0..cw * ch)
            .into_par_iter()
            .map(|c| {
                let (cy, cx) = (c / cw, c % cw);
                let mut s = 0f64;
                for y in cy * CELL..(cy + 1) * CELL {
                    let o = y * w + cx * CELL;
                    for v in &a[o..o + CELL] {
                        let d = f64::from(*v);
                        s += d * d;
                    }
                }
                (s / (CELL * CELL) as f64) as f32
            })
            .collect()
    };
    pool(band)
}

/// The coherent through-focus transfer, measured: in sampled tiles, the band
/// product of every pair of frames up to `MAX_LAG` apart. Different frames
/// carry independent noise, so these products are noise-free estimates of the
/// coefficients' common part -- what a matched filter can actually use --
/// including any residual misregistration between the two frames, which an
/// energy curve cannot see (the prototype's `coherence.py`).
struct Coherence {
    /// Tile origins, plane px.
    tiles: Vec<(usize, usize)>,
    /// The last `MAX_LAG` placed frames: index and band samples, tile by tile.
    ring: std::collections::VecDeque<(usize, [Vec<f32>; 3])>,
    /// `[band][tile][frame][lag - 1]`: sum of band products of frame `k` and
    /// `k + lag` over the tile; NaN where a frame was refused.
    sums: Vec<f64>,
    frames: usize,
}

impl Coherence {
    fn new(w: usize, h: usize, frames: usize) -> Self {
        let tiles: Vec<(usize, usize)> = (0..h / COH_TILE)
            .step_by(COH_STRIDE)
            .flat_map(|ty| {
                (0..w / COH_TILE)
                    .step_by(COH_STRIDE)
                    .map(move |tx| (tx * COH_TILE, ty * COH_TILE))
            })
            .collect();
        let sums = vec![f64::NAN; 3 * tiles.len() * frames * MAX_LAG];
        Self {
            tiles,
            ring: std::collections::VecDeque::new(),
            sums,
            frames,
        }
    }

    fn at(&self, b: usize, t: usize, k: usize, lag: usize) -> usize {
        ((b * self.tiles.len() + t) * self.frames + k) * MAX_LAG + lag - 1
    }

    fn add(&mut self, index: usize, bands: &[Vec<f32>; 3], w: usize) {
        let n = COH_TILE * COH_TILE;
        let samples: [Vec<f32>; 3] = std::array::from_fn(|b| {
            let mut v = Vec::with_capacity(self.tiles.len() * n);
            for &(x0, y0) in &self.tiles {
                for y in y0..y0 + COH_TILE {
                    v.extend_from_slice(&bands[b][y * w + x0..y * w + x0 + COH_TILE]);
                }
            }
            v
        });
        while self.ring.front().is_some_and(|(k, _)| index - k > MAX_LAG) {
            self.ring.pop_front();
        }
        for (k, old) in &self.ring {
            let lag = index - k;
            for b in 0..3 {
                let products: Vec<f64> = (0..self.tiles.len())
                    .into_par_iter()
                    .map(|t| {
                        samples[b][t * n..(t + 1) * n]
                            .iter()
                            .zip(&old[b][t * n..(t + 1) * n])
                            .map(|(a, c)| f64::from(*a) * f64::from(*c))
                            .sum()
                    })
                    .collect();
                for (t, p) in products.into_iter().enumerate() {
                    let i = self.at(b, t, *k, lag);
                    self.sums[i] = p;
                }
            }
        }
        self.ring.push_back((index, samples));
    }

    /// Band `b`'s coherent width in frames, from tiles whose focus (by the
    /// band's depth map) lies at least `MAX_LAG` frames inside the stack:
    /// per tile, the product at lag `j` about its focus frame (the mean of
    /// the pair starting there and the pair ending there) over the product
    /// at lag 1; the median over tiles; and `r(j) = exp(-(j^2 - 1) / 2 s^2)`
    /// fitted. Also returns the median ratios at lags 2, 4 and 8 and the
    /// number of tiles used.
    fn width(
        &self,
        b: usize,
        depth: &[f32],
        cw: usize,
        ok: &[bool],
    ) -> (Option<f64>, [f64; 3], usize) {
        let per = COH_TILE / CELL;
        let mut by_lag: Vec<Vec<f64>> = vec![Vec::new(); MAX_LAG + 1];
        let mut used = 0usize;
        for (t, &(x0, y0)) in self.tiles.iter().enumerate() {
            let (cx0, cy0) = (x0 / CELL, y0 / CELL);
            let mut d = Vec::with_capacity(per * per);
            let mut good = 0usize;
            for cy in cy0..cy0 + per {
                for cx in cx0..cx0 + per {
                    d.push(f64::from(depth[cy * cw + cx]));
                    good += usize::from(ok[cy * cw + cx]);
                }
            }
            if good * 5 < per * per * 4 {
                continue;
            }
            let k0 = median(&mut d).unwrap_or(0.0).round() as usize;
            if k0 < MAX_LAG || k0 + MAX_LAG >= self.frames {
                continue;
            }
            let c = |j: usize| -> Option<f64> {
                let f = self.sums[self.at(b, t, k0, j)];
                let r = self.sums[self.at(b, t, k0 - j, j)];
                match (f.is_finite(), r.is_finite()) {
                    (true, true) => Some(0.5 * (f + r)),
                    (true, false) => Some(f),
                    (false, true) => Some(r),
                    _ => None,
                }
            };
            let Some(c1) = c(1).filter(|c1| *c1 > 0.0) else {
                continue;
            };
            used += 1;
            for (j, slot) in by_lag.iter_mut().enumerate().skip(1) {
                if let Some(cj) = c(j) {
                    slot.push(cj / c1);
                }
            }
        }
        let r: Vec<Option<f64>> = by_lag.iter_mut().map(|v| median(v)).collect();
        let (mut num, mut den) = (0f64, 0f64);
        for (j, rj) in r.iter().enumerate().skip(2) {
            if let Some(rj) = rj.filter(|v| *v > 0.1 && *v < 0.98) {
                let x = (j * j - 1) as f64;
                num += x * x;
                den += 2.0 * x * (-rj.ln());
            }
        }
        let pick = |j: usize| r[j].unwrap_or(f64::NAN);
        (
            (den > 0.0 && used >= 8).then(|| (num / den).sqrt()),
            [pick(2), pick(4), pick(8)],
            used,
        )
    }
}

/// Confidence-weighted smoothing of `v` (Gaussian, `sigma` cells) where
/// `c > 0`; returns the smoothed value and its support.
fn normalised(v: &[f64], c: &[f64], w: usize, h: usize, sigma: f64) -> (Vec<f64>, Vec<f64>) {
    let num: Vec<f32> = v.iter().zip(c).map(|(v, c)| (v * c) as f32).collect();
    let den: Vec<f32> = c.iter().map(|c| *c as f32).collect();
    let n = axial_colour::blur(&num, w, h, sigma);
    let d = axial_colour::blur(&den, w, h, sigma);
    (
        n.iter()
            .zip(&d)
            .map(|(n, d)| f64::from(*n) / f64::from(*d).max(1e-12))
            .collect(),
        d.iter().map(|d| f64::from(*d)).collect(),
    )
}

/// Gaussian width `s` of a normalised amplitude curve `a(j)`, from
/// `ln a = -j^2 / (2 s^2)` over the offsets where `a` is informative.
fn gaussian_width(a: &[(i32, f64)]) -> Option<f64> {
    let (mut num, mut den) = (0f64, 0f64);
    for &(j, v) in a {
        if j != 0 && v > 0.15 && v < 0.98 {
            let j2 = f64::from(j * j);
            num += j2 * (-v.ln());
            den += j2 * j2;
        }
    }
    (den > 0.0 && num > 0.0).then(|| (den / (2.0 * num)).sqrt())
}

fn median(v: &mut [f64]) -> Option<f64> {
    if v.is_empty() {
        return None;
    }
    v.sort_by(f64::total_cmp);
    Some(v[v.len() / 2])
}

/// Measure and install, when `STREHL_FUSION=depth`. Prints the measurement.
#[allow(clippy::too_many_arguments)]
pub(super) fn install_if_requested(
    source: &impl PyramidFrameSource,
    frames: usize,
    domain: PyramidDomain,
    levels: Levels,
    warps: Option<&WarpMap>,
    bands: usize,
) -> Result<Option<Installed>> {
    // Optical restoration reads its in-focus tiles and reference frames from
    // the same measurement, so it runs for that too.
    let fusion = requested()?;
    if !(fusion || optical_restore::active()) || ca_refine::preview_active() {
        return Ok(None);
    }
    let scale = width_scale()?;
    let started = Instant::now();
    let g = domain.analysis();
    let (w, h) = (g.width, g.height);
    let (cw, ch) = (w / CELL, h / CELL);
    ensure!(
        cw >= 4 && ch >= 4,
        "{ENV}=depth: the frame is too small for a depth map"
    );
    let cells = cw * ch;
    // energy[band][frame * cells + cell]; NaN for a frame the alignment refused.
    let mut energy = [
        vec![f32::NAN; frames * cells],
        vec![f32::NAN; frames * cells],
        vec![f32::NAN; frames * cells],
    ];
    let mut scratch = WarpScratch::new(domain.full);
    let mut planes: Vec<Vec<f32>> = (0..BAND_PLANES).map(|_| vec![0.0; g.pixels()]).collect();
    let mut luma = vec![0.0; g.pixels()];
    let mut placed = 0usize;
    let mut placed_frames = vec![false; frames];
    let mut coherence = Coherence::new(w, h, frames);
    for i in 0..frames {
        let ok = load_frame(
            source,
            i,
            domain,
            levels,
            warps,
            None,
            &mut scratch,
            None,
            &mut planes,
            &mut luma,
        )
        .with_context(|| format!("{ENV}=depth: gathering frame {i}"))?;
        if !ok {
            continue;
        }
        placed += 1;
        placed_frames[i] = true;
        let images = band_images(&luma, w, h);
        for (b, e) in cell_energy(&images, w, h).into_iter().enumerate() {
            energy[b][i * cells..(i + 1) * cells].copy_from_slice(&e);
        }
        coherence.add(i, &images, w);
    }
    let Analysis {
        fits,
        valid,
        depths,
        conf0,
    } = analyse(&energy, &placed_frames, cells, cw, ch)?;
    let band_curve = |b: usize, c: usize| curve(&energy[b], frames, cells, c);
    if optical_restore::active() {
        plan_restoration(&fits, &depths, &placed_frames, w, h, cw)?;
    }
    if !fusion {
        eprintln!(
            "depth map       : measured for the optical restoration's in-focus tiles ({cw} x {ch}              cells of {CELL} plane px from {placed} placed frames, {:.1} s); fusion off",
            started.elapsed().as_secs_f64()
        );
        return Ok(None);
    }
    fusion_guide(
        &fits,
        &valid,
        &depths,
        &conf0,
        &band_curve,
        &coherence,
        FusionShape {
            frames,
            cells,
            cw,
            ch,
            w,
            h,
            bands,
            placed,
            scale,
            started,
        },
    )
}

/// Band `b`'s energy curve over the frames at cell `c`. A refused frame
/// takes its nearest placed neighbour's value, so the curve stays defined;
/// the peak fit smooths across it.
fn curve(energy: &[f32], frames: usize, cells: usize, c: usize) -> Vec<f64> {
    let raw: Vec<Option<f64>> = (0..frames)
        .map(|k| {
            let v = energy[k * cells + c];
            v.is_finite().then_some(f64::from(v))
        })
        .collect();
    (0..frames)
        .map(|k| {
            raw[k].unwrap_or_else(|| {
                (1..frames)
                    .find_map(|d| {
                        raw.get(k.wrapping_sub(d))
                            .copied()
                            .flatten()
                            .or_else(|| raw.get(k + d).copied().flatten())
                    })
                    .unwrap_or(0.0)
            })
        })
        .collect()
}

/// What the depth measurement derives from the band energies, per band.
struct Analysis {
    /// Per band and cell: the focus plane and its contrast, where confident.
    fits: Vec<Vec<Option<(f64, f64)>>>,
    /// Per band: cells with a peak.
    valid: Vec<usize>,
    /// Per band: the filled focus-plane map.
    depths: Vec<Vec<f32>>,
    /// Band 0's peak confidence per cell.
    conf0: Vec<f32>,
}

/// The depth maps from `energy[band][frame * cells + cell]` (NaN for a frame
/// the alignment refused). Shared by the pre-pass and the measurement taken
/// during the fold, which differ only in how many bands they keep: every band
/// is derived from its own energies alone.
fn analyse(
    energy: &[Vec<f32>],
    placed_frames: &[bool],
    cells: usize,
    cw: usize,
    ch: usize,
) -> Result<Analysis> {
    let frames = placed_frames.len();
    let placed = placed_frames.iter().filter(|p| **p).count();
    ensure!(
        placed >= 7,
        "{ENV}=depth: {placed} placed frames; a depth map needs at least 7"
    );
    // Per band and cell: focus plane and confidence. Each band gets its own
    // map: on the A7CR scarab stack single-frame renders are sharpest about
    // 4.5 frames after the plane the 2-4 sensor px band peaks at (spherical
    // aberration focuses fine detail elsewhere), so one map from a coarser
    // band put the finest band's weights on defocused frames (2026-11-15).
    let fits: Vec<Vec<Option<(f64, f64)>>> = energy
        .iter()
        .map(|e| {
            (0..cells)
                .into_par_iter()
                .map(|c| {
                    axial_colour::peak(&curve(e, frames, cells, c))
                        .filter(|(_, con)| *con >= MIN_CONTRAST)
                })
                .collect()
        })
        .collect();
    let valid: Vec<usize> = fits
        .iter()
        .map(|f| f.iter().filter(|f| f.is_some()).count())
        .collect();
    ensure!(
        valid[1] > cells / 50,
        "{ENV}=depth: only {} of {cells} cells show a focus peak; this stack has no usable depth",
        valid[1]
    );
    let mut depths: Vec<Vec<f32>> = Vec::new();
    let mut conf0: Vec<f32> = Vec::new();
    for f in &fits {
        let d0: Vec<f64> = f.iter().map(|f| f.map_or(0.0, |f| f.0)).collect();
        let c0: Vec<f64> = f.iter().map(|f| f.map_or(0.0, |f| f.1.min(50.0))).collect();
        // Fill: the finest smoothing whose support reaches 5 % of the most
        // confident cell's, else coarser.
        let mut depth = vec![f64::NAN; cells];
        let full = c0.iter().copied().fold(0.0, f64::max).max(1e-9);
        for sigma in [1.5, 4.0, 12.0, 40.0] {
            let (v, s) = normalised(&d0, &c0, cw, ch, sigma);
            for i in 0..cells {
                if depth[i].is_nan() && s[i] >= 0.05 * full {
                    depth[i] = v[i];
                }
            }
        }
        let mut known: Vec<f64> = depth.iter().copied().filter(|d| d.is_finite()).collect();
        let fallback = median(&mut known).unwrap_or((frames - 1) as f64 / 2.0);
        if conf0.is_empty() {
            conf0 = c0.iter().map(|c| *c as f32).collect();
        }
        depths.push(
            depth
                .iter()
                .map(|d| {
                    let d = if d.is_finite() { *d } else { fallback };
                    d.clamp(0.0, (frames - 1) as f64) as f32
                })
                .collect(),
        );
    }
    Ok(Analysis {
        fits,
        valid,
        depths,
        conf0,
    })
}

/// The optical restoration's spectrum tiles from band 0's depth map.
fn plan_restoration(
    fits: &[Vec<Option<(f64, f64)>>],
    depths: &[Vec<f32>],
    placed_frames: &[bool],
    w: usize,
    h: usize,
    cw: usize,
) -> Result<()> {
    let confident: Vec<bool> = fits[0]
        .iter()
        .map(|f| f.is_some_and(|f| f.1 >= 5.0))
        .collect();
    let folded: Vec<bool> = placed_frames
        .iter()
        .enumerate()
        .map(|(i, p)| Ok(*p && frame_parity_keeps(i)?))
        .collect::<Result<_>>()?;
    optical_restore::plan_tiles(w, h, cw, CELL, &depths[0], &confident, &folded);
    Ok(())
}

/// The depth-guided fusion's sizes and settings.
struct FusionShape {
    frames: usize,
    cells: usize,
    cw: usize,
    ch: usize,
    w: usize,
    h: usize,
    bands: usize,
    placed: usize,
    scale: f32,
    started: Instant,
}

/// Measure the transfer widths and install the depth guide
/// (`STREHL_FUSION=depth`).
#[allow(clippy::too_many_arguments)]
fn fusion_guide(
    fits: &[Vec<Option<(f64, f64)>>],
    valid: &[usize],
    depths: &[Vec<f32>],
    conf0: &[f32],
    curve: &dyn Fn(usize, usize) -> Vec<f64>,
    coherence: &Coherence,
    shape: FusionShape,
) -> Result<Option<Installed>> {
    let FusionShape {
        frames,
        cells,
        cw,
        ch,
        w,
        h,
        bands,
        placed,
        scale,
        started,
    } = shape;
    // Per band: the through-focus amplitude of confident cells about the
    // band's own peak.
    let mut widths = Vec::new();
    let mut profile_lines = Vec::new();
    for b in 0..3 {
        let confident: Vec<usize> = (0..cells)
            .filter(|&c| {
                fits[b][c].is_some_and(|(k, con)| {
                    con >= 5.0 && k >= 12.0 && k + 12.0 <= (frames - 1) as f64
                })
            })
            .collect();
        let mut by_offset: Vec<Vec<f64>> = vec![Vec::new(); 25];
        for &c in &confident {
            let e = curve(b, c);
            let floor = e.iter().copied().fold(f64::INFINITY, f64::min);
            let k0 = fits[b][c].expect("confident").0.round() as usize;
            let top = e[k0] - floor;
            if top <= 0.0 {
                continue;
            }
            for (slot, j) in (-12i32..=12).enumerate() {
                let k = (k0 as i32 + j) as usize;
                by_offset[slot].push(((e[k] - floor).max(0.0) / top).sqrt());
            }
        }
        let curve_a: Vec<(i32, f64)> = by_offset
            .iter_mut()
            .zip(-12i32..=12)
            .filter_map(|(v, j)| median(v).map(|m| (j, m)))
            .collect();
        let s = gaussian_width(&curve_a);
        let mut lead: Vec<f64> = (0..cells)
            .filter_map(|c| Some(fits[b][c]?.0 - fits[1][c]?.0))
            .collect();
        profile_lines.push(format!(
            "band {b}: {} cells with a peak, {} confident; focus {:+.2} frames from band 1's (median); \
             energy amplitude at -8/-4/+4/+8 frames {}; energy width {}",
            valid[b],
            confident.len(),
            median(&mut lead).unwrap_or(0.0),
            [-8, -4, 4, 8]
                .iter()
                .map(|j| curve_a
                    .iter()
                    .find(|(o, _)| o == j)
                    .map_or("-".into(), |(_, v)| format!("{v:.2}")))
                .collect::<Vec<_>>()
                .join("/"),
            s.map_or("not measured".into(), |s| format!("{s:.2} frames"))
        ));
        widths.push(s);
    }
    // The coherent widths, which set the weights. The energy-curve widths
    // above read 10-17 frames on the A7CR scarab, where weights that wide
    // lost 40 % of the finest detail: frames several apart do not add
    // coherently at that scale.
    let mut coherent = Vec::new();
    for b in 0..3 {
        let ok: Vec<bool> = fits[b]
            .iter()
            .map(|f| f.is_some_and(|f| f.1 >= 5.0))
            .collect();
        let (s, r, used) = coherence.width(b, &depths[b], cw, &ok);
        profile_lines.push(format!(
            "band {b} coherent: product of frames 2/4/8 apart about focus over 1 apart {:.2}/{:.2}/{:.2} \
             ({used} tiles); width {}",
            r[0],
            r[1],
            r[2],
            s.map_or("not measured".into(), |s| format!("{s:.2} frames"))
        ));
        coherent.push(s);
    }
    ensure!(
        coherent.iter().any(|s| s.is_some()),
        "{ENV}=depth: the coherent transfer could not be measured on any band (too few in-focus tiles \
         at least {MAX_LAG} frames inside the stack)"
    );
    let widths = coherent;
    // A band whose width could not be measured takes its finer neighbour's
    // scaled by `COARSER`, or the next coarser one's.
    let mut ws: Vec<f32> = Vec::new();
    for b in 0..3 {
        let s = widths[b]
            .or_else(|| {
                (b > 0)
                    .then(|| widths[b - 1].map(|s| s * f64::from(COARSER)))
                    .flatten()
            })
            .or_else(|| widths.iter().skip(b + 1).find_map(|s| *s))
            .with_context(|| {
                format!("{ENV}=depth: no band's through-focus width could be measured")
            })?;
        ws.push(s as f32);
    }
    let sizes: Vec<LevelSize> = strehl_core::pyramid::level_sizes(w, h, bands);
    let cap = (frames as f32 / 2.0).max(1.0);
    let level_widths: Vec<f32> = (0..sizes.len())
        .map(|k| {
            let s = if k < 3 {
                ws[k]
            } else {
                ws[2] * COARSER.powi(k as i32 - 2)
            };
            (s * scale).min(cap)
        })
        .collect();
    let coarse_election = coarse_election()?;
    let guide = DepthGuide::from_cells(&sizes, CELL, cw, ch, depths, &level_widths, FLOOR, 3);
    let guide = if coarse_election {
        guide.with_guided_levels(3)
    } else {
        guide
    };
    // Experiment hook (`STREHL_FUSION_DUMP`, declared in check-defaults.py):
    // the three bands' depth maps and band 0's peak confidence as raw
    // little-endian f32 [4, ch, cw]; `<path>.txt` holds "cw ch cell 4".
    if let Ok(path) = std::env::var("STREHL_FUSION_DUMP") {
        let mut bytes = Vec::with_capacity(16 * cells);
        for v in depths.iter().flatten().chain(conf0) {
            bytes.extend_from_slice(&v.to_le_bytes());
        }
        std::fs::write(&path, bytes)?;
        std::fs::write(format!("{path}.txt"), format!("{cw} {ch} {CELL} 4\n"))?;
    }
    let mut dq: Vec<f64> = depths[0].iter().map(|d| f64::from(*d)).collect();
    dq.sort_by(f64::total_cmp);
    let q = |p: f64| dq[((dq.len() - 1) as f64 * p).round() as usize];
    eprintln!(
        "fusion          : DEPTH-GUIDED ({ENV}=depth) -- every frame weighted by its band's measured through-focus \
         transfer at its distance from that band's focus plane, measured once from the stack; sum(t L) / sum(t^2)"
    );
    eprintln!(
        "                  depth maps {cw} x {ch} cells of {CELL} plane px, one per band, from {placed} placed \
         frames; finest band's focus plane 5/50/95 % {:.1} / {:.1} / {:.1}; {:.1} s",
        q(0.05),
        q(0.5),
        q(0.95),
        started.elapsed().as_secs_f64()
    );
    for l in &profile_lines {
        eprintln!("                  {l}");
    }
    eprintln!(
        "                  transfer width per level, frames: {}{}; weights under {FLOOR} are zero",
        level_widths
            .iter()
            .map(|s| format!("{s:.1}"))
            .collect::<Vec<_>>()
            .join(" "),
        if scale == 1.0 {
            String::new()
        } else {
            format!(" (x{scale} by {WIDTH_ENV}, an experiment)")
        }
    );
    if coarse_election {
        eprintln!(
            "                  levels past the third take the merge's own election ({COARSE_ENV}=election)"
        );
    }
    *ACTIVE.write().unwrap_or_else(|e| e.into_inner()) = Some(Arc::new(guide));
    Ok(Some(Installed))
}

/// `STREHL_DEPTH_PASS`: where the optical restoration's depth map is
/// measured when fusion is off. `fused` (the default where eligible) takes
/// the band energies from the fold's own green luma as each frame is
/// prepared, and gathers the reference tiles' frames again after the fold;
/// `prepass` keeps the separate gather of every frame before the fold. The
/// two give byte-identical output: the luma is the same array (same decode,
/// group measurement, warp and expression) and everything after it is the
/// same code. Measured on the A7CR scarab four-shot run (2026-11-18): the
/// pre-pass cost 128 s of a 346 s render.
pub(super) const PASS_ENV: &str = "STREHL_DEPTH_PASS";

fn prepass_forced() -> Result<bool> {
    match std::env::var(PASS_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Err(e) => Err(e).context(PASS_ENV),
        Ok(v) => match v.trim() {
            "" | "fused" => Ok(false),
            "prepass" => Ok(true),
            other => anyhow::bail!("{PASS_ENV}={other:?} is not fused or prepass"),
        },
    }
}

/// The band energies recorded during the fold.
struct Tap {
    w: usize,
    h: usize,
    cw: usize,
    ch: usize,
    /// `energy[band][frame * cells + cell]`, bands 0 and 1; NaN for a frame
    /// that was not recorded.
    energy: [Vec<f32>; 2],
    placed: Vec<bool>,
    started: Instant,
}

static TAP: std::sync::Mutex<Option<Tap>> = std::sync::Mutex::new(None);

fn tap() -> std::sync::MutexGuard<'static, Option<Tap>> {
    TAP.lock().unwrap_or_else(|e| e.into_inner())
}

/// Clears the tap when the render ends, however it ends.
pub(super) struct TapGuard;

impl Drop for TapGuard {
    fn drop(&mut self) {
        *tap() = None;
    }
}

/// The measurement failed after the fold: the stack shows no usable depth.
/// A defaulted restoration renders again without restoring (the fold it
/// ran folded in half-stacks, whose sums are associated differently from
/// an unrestored fold's).
#[derive(Debug)]
pub(super) struct Unmeasured(pub String);

impl std::fmt::Display for Unmeasured {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for Unmeasured {}

/// Start measuring depth during the fold instead of before it, when this
/// render only needs the measurement for the optical restoration's tiles
/// and nothing makes the fold's frames differ from the pre-pass's: fusion
/// off, no `STREHL_FRAME_PARITY` (the pre-pass measures frames the fold
/// skips), no defect correction (the pre-pass gathers without it), no
/// temporal energy, and not `STREHL_DEPTH_PASS=prepass`. The failures the
/// pre-pass would raise before the fold are raised here, with its messages.
pub(super) fn begin_tap(
    frames: usize,
    domain: PyramidDomain,
    warps: Option<&WarpMap>,
    defect: bool,
    temporal: bool,
) -> Result<Option<TapGuard>> {
    if !optical_restore::active()
        || requested()?
        || ca_refine::preview_active()
        || std::env::var_os("STREHL_FRAME_PARITY").is_some()
        || defect
        || temporal
        || prepass_forced()?
    {
        return Ok(None);
    }
    let g = domain.analysis();
    let (w, h) = (g.width, g.height);
    let (cw, ch) = (w / CELL, h / CELL);
    ensure!(
        cw >= 4 && ch >= 4,
        "{ENV}=depth: the frame is too small for a depth map"
    );
    let placed = match warps {
        Some(map) => (0..frames)
            .filter(|&i| matches!(map.warp(i), Ok(FrameWarp::Placed(_))))
            .count(),
        None => frames,
    };
    ensure!(
        placed >= 7,
        "{ENV}=depth: {placed} placed frames; a depth map needs at least 7"
    );
    let cells = cw * ch;
    *tap() = Some(Tap {
        w,
        h,
        cw,
        ch,
        energy: [
            vec![f32::NAN; frames * cells],
            vec![f32::NAN; frames * cells],
        ],
        placed: vec![false; frames],
        started: Instant::now(),
    });
    Ok(Some(TapGuard))
}

/// [`record`]'s blur buffers, kept between frames (a fresh 60 MB plane per
/// blur cost first-touch page faults on every frame).
static RECORD_BUFFERS: std::sync::Mutex<Vec<[Vec<f32>; 3]>> = std::sync::Mutex::new(Vec::new());

/// [`cell_energy_of`] the difference `a - b`, without materialising it.
fn cell_energy_of_difference(a: &[f32], b: &[f32], w: usize, h: usize) -> Vec<f32> {
    let (cw, ch) = (w / CELL, h / CELL);
    (0..cw * ch)
        .into_par_iter()
        .map(|c| {
            let (cy, cx) = (c / cw, c % cw);
            let mut s = 0f64;
            for y in cy * CELL..(cy + 1) * CELL {
                let o = y * w + cx * CELL;
                for (p, q) in a[o..o + CELL].iter().zip(&b[o..o + CELL]) {
                    let d = f64::from(p - q);
                    s += d * d;
                }
            }
            (s / (CELL * CELL) as f64) as f32
        })
        .collect()
}

/// Whether depth is being measured during the fold ([`begin_tap`]).
pub(super) fn tap_active() -> bool {
    tap().is_some()
}

/// Record frame `index`'s band 0 and 1 cell energies from the fold's green
/// luma (`prepare_frame_into`, right after the gather). A no-op unless
/// [`begin_tap`] started a measurement.
pub(super) fn record(index: usize, luma: &[f32]) {
    let Some((w, h)) = tap().as_ref().map(|t| (t.w, t.h)) else {
        return;
    };
    // `two_band_images` and `cell_energy_of`, through reused buffers and
    // without materialising the differences: each cell sums the same
    // `f64::from(a - b)` squares in the same order.
    let [mut tmp, mut g1, mut g2] = RECORD_BUFFERS
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .pop()
        .unwrap_or_default();
    axial_colour::blur_into(luma, w, h, 1.0, &mut tmp, &mut g1);
    axial_colour::blur_into(&g1, w, h, 3f64.sqrt(), &mut tmp, &mut g2);
    let e = [
        cell_energy_of_difference(luma, &g1, w, h),
        cell_energy_of_difference(&g1, &g2, w, h),
    ];
    RECORD_BUFFERS
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .push([tmp, g1, g2]);
    let mut guard = tap();
    let Some(t) = guard.as_mut() else { return };
    let cells = t.cw * t.ch;
    for (band, e) in t.energy.iter_mut().zip(&e) {
        band[index * cells..(index + 1) * cells].copy_from_slice(e);
    }
    t.placed[index] = true;
}

/// Finish the measurement taken during the fold: what the pre-pass does
/// after its loop, for the restoration's tiles only (bands 0 and 1). Ends
/// the tap. A failure is an [`Unmeasured`] error.
pub(super) fn finish_tap() -> Result<()> {
    let Some(t) = tap().take() else {
        return Ok(());
    };
    let cells = t.cw * t.ch;
    let placed = t.placed.iter().filter(|p| **p).count();
    // Asked for, the failure is the render's error, as the pre-pass's is.
    let a = analyse(&t.energy, &t.placed, cells, t.cw, t.ch).map_err(|e| {
        if optical_restore::defaulted() {
            anyhow::Error::new(Unmeasured(format!("{e:#}")))
        } else {
            e
        }
    })?;
    plan_restoration(&a.fits, &a.depths, &t.placed, t.w, t.h, t.cw)?;
    eprintln!(
        "depth map       : measured during the fold for the optical restoration's in-focus tiles \
         ({} x {} cells of {CELL} plane px from {placed} placed frames, {:.1} s since the fold \
         began); fusion off",
        t.cw,
        t.ch,
        t.started.elapsed().as_secs_f64()
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The fold's record takes each band's cell energy from the two blurs
    /// directly; the pre-pass from the materialised difference. Same bits.
    #[test]
    fn cell_energy_of_a_difference_is_that_of_the_band_image() {
        let (w, h) = (8 * 9 + 5, 8 * 7 + 3);
        let a: Vec<f32> = (0..w * h)
            .map(|i| ((i * 7919) % 1013) as f32 * 0.73)
            .collect();
        let b: Vec<f32> = (0..w * h)
            .map(|i| ((i * 104_729) % 997) as f32 * 0.61)
            .collect();
        let want = cell_energy_of(&difference(&a, &b), w, h);
        let got = cell_energy_of_difference(&a, &b, w, h);
        assert_eq!(
            want.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            got.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
        );
    }

    #[test]
    fn a_planted_gaussian_width_is_recovered() {
        let a: Vec<(i32, f64)> = (-12..=12)
            .map(|j| (j, (-f64::from(j * j) / (2.0 * 5.0 * 5.0)).exp()))
            .collect();
        let s = gaussian_width(&a).expect("informative");
        assert!((s - 5.0).abs() < 1e-6, "{s}");
        assert!(gaussian_width(&[(0, 1.0)]).is_none());
    }

    #[test]
    fn smoothing_fills_a_hole_from_its_confident_neighbours() {
        let (w, h) = (9, 9);
        let mut v = vec![7.0; w * h];
        let mut c = vec![1.0; w * h];
        v[40] = 0.0;
        c[40] = 0.0;
        let (out, support) = normalised(&v, &c, w, h, 1.5);
        assert!((out[40] - 7.0).abs() < 1e-4, "{}", out[40]);
        assert!(support[40] > 0.5);
    }
}
