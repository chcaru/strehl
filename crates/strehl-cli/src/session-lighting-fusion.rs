//! Lighting fusion by light superposition: combine separately merged,
//! differently lit renders of one subject into a single photograph.
//!
//! Light adds linearly, so the sum of renders under lamp positions L1..Lk is
//! the render with every lamp on at once. Each lighting group is normalised to
//! the anchor's overall brightness and the groups are averaged with equal
//! weight: a physically valid "all lights" image with lower noise where groups
//! overlap. Before averaging, each layer
//!
//! 1. is dropped if it is defocused: lighting scales contrast equally across
//!    frequency bands, defocus attenuates fine bands more, so the ratio of a
//!    layer's fine to coarse band contrast against the anchor's measures blur
//!    independently of lighting;
//! 2. is registered onto the anchor by a measured dense residual field (tile
//!    NCC on band-passed log brightness, which is insensitive to lighting),
//!    because averaging misplaced detail blurs it. The joint geometry solve
//!    leaves about a plane pixel between passes, more after a pose change;
//! 3. has its uncovered canvas predicted as the anchor times the layer's
//!    smooth relighting ratio, so coverage edges cannot leave seams.
//!
//! The anchor's near-clipped speculars stay the anchor's: clipped values are
//! only lower bounds and averaging them punched dark holes (bug-4). This
//! operates on merged native CFA planes before development, so demosaic,
//! colour and tone stay exactly the ordinary path. Earlier detail-selection
//! blends (Laplacian pyramids, anchor-first weights) never beat the anchor
//! alone on bug-4; see the third-slice record.

use rayon::prelude::*;

/// One lighting group's merged planes in native API order R, G1, B, G2, in
/// shared signal units, with its coverage on the common canvas.
#[derive(Clone)]
pub struct GroupPlanes {
    pub planes: [Vec<f32>; 4],
    pub valid: Vec<bool>,
    /// Black-subtracted clipping level in these signal units.
    pub ceiling: f32,
}

#[derive(Clone, Debug, serde::Serialize)]
pub struct FieldStats {
    /// Tiles with an accepted displacement.
    pub vectors: usize,
    /// Accepted tiles rejected as inconsistent with their neighbours.
    pub rejected: usize,
    /// Median and 90th-percentile displacement magnitude (plane px).
    pub median_px: f64,
    pub p90_px: f64,
}

#[derive(Clone, Debug, serde::Serialize)]
pub struct LayerReport {
    /// Index into the lighting groups (0 is the anchor).
    pub group: usize,
    /// Layer/anchor fine-band contrast (lighting and blur both move it).
    pub fine_contrast_ratio: f64,
    /// Fine-band ratio over coarse-band ratio: about 1 for a sharp layer
    /// under any lighting, well below 1 when defocused.
    pub fine_over_coarse: f64,
    /// `superposed`, `defocused` or `no_overlap`.
    pub outcome: &'static str,
    pub residual_before: Option<FieldStats>,
    /// Same estimator after warping; convergence, not independent accuracy.
    pub residual_after: Option<FieldStats>,
    /// Layer brightness relative to the anchor (removed before averaging).
    pub brightness_gain: Option<f64>,
    /// Mean fraction of the canvas the layer covers with its own pixels.
    pub coverage: Option<f64>,
    /// Pose layers: fraction of the covered canvas that agrees with the
    /// anchor after registration and relighting (the rest yields to it).
    pub agreement: Option<f64>,
    /// Fraction of the common subject where the layer is locally sharp.
    pub sharp_fraction: Option<f64>,
}

#[derive(Clone, Debug, serde::Serialize)]
pub struct FusionReport {
    pub schema: &'static str,
    pub groups: usize,
    /// Groups averaged, including the anchor.
    pub superposed: usize,
    pub layers: Vec<LayerReport>,
    /// Fraction of the canvas kept from the anchor because it is near clipping.
    pub anchor_highlight_fraction: f64,
    pub config: FusionConfig,
    pub semantics: &'static str,
}

#[derive(Clone, Copy, Debug, serde::Serialize)]
pub struct FusionConfig {
    /// Registration tile size, grid stride and refinement search radius
    /// (plane px); the quarter-resolution seed search reaches
    /// `coarse_search` quarter-resolution px (four times as many plane px).
    pub tile: usize,
    pub stride: usize,
    pub search: usize,
    pub coarse_search: usize,
    /// Extra registration rounds while the residual median exceeds
    /// `converged_px` (plane px).
    pub registration_rounds: usize,
    pub converged_px: f64,
    /// Distance (plane px) from the neighbourhood median that rejects a tile.
    pub outlier_px: f32,
    /// Gaussian sigma (plane px) of the relighting ratio field.
    pub ratio_sigma: f32,
    /// Distance (plane px) over which a layer fades in from its coverage edge.
    pub feather: usize,
    /// Fine-band contrast ratio below half of which a layer has no usable
    /// contrast at all.
    pub min_fine_contrast: f32,
    /// Local defocus gate: pooling radius (plane px) and the local fine/coarse
    /// shape relative to the anchor at which a layer starts, and fully
    /// stops, being rejected as blurred.
    pub sharp_radius: usize,
    pub blur_reject: f32,
    pub blur_accept: f32,
    /// Fraction of the subject that must be locally sharp to use a layer.
    pub min_sharp_fraction: f64,
    /// Anchor value/ceiling range over which the anchor takes over highlights.
    pub highlight_start: f32,
    pub highlight_full: f32,
    /// Pose layers: smoothed |log| difference from the relit anchor at which
    /// a pixel starts, and fully stops, contributing.
    pub pose_agree: f32,
    pub pose_disagree: f32,
}

impl Default for FusionConfig {
    fn default() -> Self {
        Self {
            tile: 64,
            stride: 32,
            search: 4,
            coarse_search: 8,
            registration_rounds: 2,
            converged_px: 0.35,
            outlier_px: 1.5,
            ratio_sigma: 24.0,
            feather: 24,
            min_fine_contrast: 0.3,
            sharp_radius: 24,
            blur_reject: 0.6,
            blur_accept: 0.85,
            min_sharp_fraction: 0.05,
            highlight_start: 0.8,
            highlight_full: 0.95,
            pose_agree: 0.1,
            pose_disagree: 0.25,
        }
    }
}

/// Minimum normalised cross-correlation of an accepted registration tile.
const MIN_CORRELATION: f32 = 0.5;
/// Resolution reduction of the smooth relighting-ratio field.
const RATIO_DOWNSAMPLE: usize = 8;

fn smoothstep(edge0: f32, edge1: f32, x: f32) -> f32 {
    let t = ((x - edge0) / (edge1 - edge0)).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

/// Separable box mean with clamped borders.
fn box_mean(data: &[f32], width: usize, height: usize, radius: usize) -> Vec<f32> {
    if radius == 0 {
        return data.to_vec();
    }
    let r = radius as isize;
    let mut rows = vec![0.0f32; data.len()];
    rows.par_chunks_mut(width).enumerate().for_each(|(y, out)| {
        let src = &data[y * width..(y + 1) * width];
        let at = |i: isize| f64::from(src[i.clamp(0, width as isize - 1) as usize]);
        let mut sum: f64 = (-r..=r).map(at).sum();
        for (i, o) in out.iter_mut().enumerate() {
            let i = i as isize;
            *o = (sum / (2 * r + 1) as f64) as f32;
            sum += at(i + r + 1) - at(i - r);
        }
    });
    // Column pass as running sums, one row at a time (cache friendly).
    let at =
        |y: isize, x: usize| f64::from(rows[y.clamp(0, height as isize - 1) as usize * width + x]);
    let mut sums: Vec<f64> = (0..width)
        .map(|x| (-r..=r).map(|y| at(y, x)).sum())
        .collect();
    let mut out = vec![0.0f32; data.len()];
    for y in 0..height {
        for x in 0..width {
            out[y * width + x] = (sums[x] / (2 * r + 1) as f64) as f32;
            sums[x] += at(y as isize + r + 1, x) - at(y as isize - r, x);
        }
    }
    out
}

/// Separable Gaussian blur with clamped borders.
fn gaussian_blur(data: &[f32], width: usize, height: usize, sigma: f32) -> Vec<f32> {
    if sigma <= 0.0 {
        return data.to_vec();
    }
    let radius = (3.0 * sigma).ceil() as isize;
    let mut kernel: Vec<f32> = (-radius..=radius)
        .map(|i| (-(i * i) as f32 / (2.0 * sigma * sigma)).exp())
        .collect();
    let total: f32 = kernel.iter().sum();
    kernel.iter_mut().for_each(|k| *k /= total);
    let mut rows = vec![0.0f32; data.len()];
    rows.par_chunks_mut(width).enumerate().for_each(|(y, out)| {
        let src = &data[y * width..(y + 1) * width];
        for (x, o) in out.iter_mut().enumerate() {
            *o = kernel
                .iter()
                .enumerate()
                .map(|(k, w)| {
                    w * src
                        [(x as isize + k as isize - radius).clamp(0, width as isize - 1) as usize]
                })
                .sum();
        }
    });
    let mut out = vec![0.0f32; data.len()];
    out.par_chunks_mut(width).enumerate().for_each(|(y, out)| {
        for (k, w) in kernel.iter().enumerate() {
            let sy = (y as isize + k as isize - radius).clamp(0, height as isize - 1) as usize;
            let src = &rows[sy * width..(sy + 1) * width];
            for (o, s) in out.iter_mut().zip(src) {
                *o += w * s;
            }
        }
    });
    out
}

/// `q`-quantile of `values` (consumed).
fn quantile(mut values: Vec<f32>, q: f64) -> Option<f32> {
    if values.is_empty() {
        return None;
    }
    let k = ((values.len() - 1) as f64 * q).round() as usize;
    Some(*values.select_nth_unstable_by(k, f32::total_cmp).1)
}

fn luma(group: &GroupPlanes) -> Vec<f32> {
    let [r, g1, b, g2] = &group.planes;
    (0..r.len())
        .map(|i| 0.25 * (r[i] + g1[i] + b[i] + g2[i]))
        .collect()
}

/// Pixels whose whole `radius` neighbourhood is set.
fn erode(mask: &[bool], width: usize, height: usize, radius: usize) -> Vec<bool> {
    let m: Vec<f32> = mask.iter().map(|&v| f32::from(u8::from(v))).collect();
    box_mean(&m, width, height, radius)
        .into_iter()
        .map(|v| v > 1.0 - 1e-4)
        .collect()
}

/// Normalised convolution of `values` (weighted by `weights`) on a small grid,
/// falling back to progressively wider support where weights are sparse, so
/// every cell receives an estimate.
fn fill_smooth(
    values: &[f32],
    weights: &[f32],
    width: usize,
    height: usize,
    sigma: f32,
) -> Vec<f32> {
    let vw: Vec<f32> = values.iter().zip(weights).map(|(v, w)| v * w).collect();
    let peak = weights.iter().copied().fold(0.0f32, f32::max).max(1e-12);
    let den = gaussian_blur(weights, width, height, sigma);
    let num = gaussian_blur(&vw, width, height, sigma);
    let mut result: Vec<f32> = num
        .iter()
        .zip(&den)
        .map(|(n, d)| n / d.max(1e-12))
        .collect();
    let mut confidence = den;
    for factor in [4.0, 16.0, 64.0] {
        let d2 = gaussian_blur(weights, width, height, sigma * factor);
        let n2 = gaussian_blur(&vw, width, height, sigma * factor);
        for i in 0..result.len() {
            let blend = (confidence[i] / (confidence[i] + 0.05 * peak)).clamp(0.0, 1.0);
            result[i] = blend * result[i] + (1.0 - blend) * n2[i] / d2[i].max(1e-12);
            confidence[i] = confidence[i].max(d2[i]);
        }
    }
    result
}

/// Lighting-insensitive registration feature: band-passed log brightness.
fn feature(luma: &[f32], width: usize, height: usize, floor: f32) -> Vec<f32> {
    let log: Vec<f32> = luma.iter().map(|&v| v.max(floor).ln()).collect();
    let fine = gaussian_blur(&log, width, height, 1.0);
    let coarse = gaussian_blur(&log, width, height, 4.0);
    fine.iter().zip(&coarse).map(|(f, c)| f - c).collect()
}

/// Dense residual displacement (dy, dx) such that `layer(p + d) ~ anchor(p)`.
struct Field {
    dy: Vec<f32>,
    dx: Vec<f32>,
    stats: FieldStats,
}

/// Tile grid geometry of one registration level.
#[derive(Clone, Copy)]
struct Grid {
    tile: usize,
    stride: usize,
    search: usize,
    outlier_px: f32,
}

/// Coarse-to-fine dense residual field: a quarter-resolution search with
/// wide reach seeds a full-resolution refinement.
fn register(
    anchor: &[f32],
    layer: &[f32],
    valid: &[bool],
    width: usize,
    height: usize,
    cfg: &FusionConfig,
) -> Option<Field> {
    const F: usize = 4;
    let fine = Grid {
        tile: cfg.tile,
        stride: cfg.stride,
        search: cfg.search,
        outlier_px: cfg.outlier_px,
    };
    let (cw, ch) = (width / F, height / F);
    let coarse = Grid {
        tile: (cfg.tile / F).max(16),
        stride: (cfg.stride / F).max(8),
        search: cfg.coarse_search,
        outlier_px: cfg.outlier_px,
    };
    let shrink = |data: &[f32]| -> Vec<f32> {
        (0..cw * ch)
            .map(|c| {
                let (y, x) = (c / cw * F, c % cw * F);
                (0..F * F)
                    .map(|k| data[(y + k / F) * width + x + k % F])
                    .sum::<f32>()
                    / (F * F) as f32
            })
            .collect()
    };
    let coarse_valid: Vec<bool> = (0..cw * ch)
        .map(|c| {
            let (y, x) = (c / cw * F, c % cw * F);
            (0..F * F).all(|k| valid[(y + k / F) * width + x + k % F])
        })
        .collect();
    let seed = residual_field(
        &shrink(anchor),
        &shrink(layer),
        &coarse_valid,
        cw,
        ch,
        coarse,
        None,
    )
    .map(|c| {
        let up = |v: &[f32]| {
            upsample_by(v, cw, ch, width, height, F)
                .into_iter()
                .map(|d| d * F as f32)
                .collect::<Vec<f32>>()
        };
        (up(&c.dy), up(&c.dx))
    });
    let fine = match &seed {
        Some(_) => fine,
        None => Grid {
            search: cfg.search + cfg.coarse_search,
            ..fine
        },
    };
    residual_field(anchor, layer, valid, width, height, fine, seed.as_ref())
}

fn residual_field(
    anchor: &[f32],
    layer: &[f32],
    valid: &[bool],
    width: usize,
    height: usize,
    grid: Grid,
    seed: Option<&(Vec<f32>, Vec<f32>)>,
) -> Option<Field> {
    let (t, s, r) = (grid.tile, grid.stride, grid.search);
    if width < t + 2 * r + 1 || height < t + 2 * r + 1 {
        return None;
    }
    let ys: Vec<usize> = (0..=height - t).step_by(s).collect();
    let xs: Vec<usize> = (0..=width - t).step_by(s).collect();
    let (gw, gh) = (xs.len(), ys.len());
    // Prefix sums of invalid pixels for O(1) window checks.
    let mut invalid = vec![0u32; (width + 1) * (height + 1)];
    for y in 0..height {
        for x in 0..width {
            invalid[(y + 1) * (width + 1) + x + 1] = u32::from(!valid[y * width + x])
                + invalid[y * (width + 1) + x + 1]
                + invalid[(y + 1) * (width + 1) + x]
                - invalid[y * (width + 1) + x];
        }
    }
    let window_valid = |y0: isize, x0: isize, size: usize| {
        if y0 < 0 || x0 < 0 || y0 as usize + size > height || x0 as usize + size > width {
            return false;
        }
        let (y0, x0) = (y0 as usize, x0 as usize);
        let at = |y: usize, x: usize| invalid[y * (width + 1) + x];
        at(y0 + size, x0 + size) + at(y0, x0) == at(y0, x0 + size) + at(y0 + size, x0)
    };
    let span = 2 * r + 1;
    let measured: Vec<Option<(f32, f32, f32)>> = (0..gw * gh)
        .into_par_iter()
        .map(|cell| {
            let (y, x) = (ys[cell / gw], xs[cell % gw]);
            let centre = (y + t / 2) * width + x + t / 2;
            let (oy, ox) = seed.map_or((0, 0), |(sy, sx)| {
                (sy[centre].round() as isize, sx[centre].round() as isize)
            });
            let (wy, wx) = (y as isize + oy - r as isize, x as isize + ox - r as isize);
            if !window_valid(wy, wx, t + 2 * r) {
                return None;
            }
            let (wy, wx) = (wy as usize, wx as usize);
            let n = (t * t) as f64;
            let (mut sa, mut saa) = (0.0f64, 0.0f64);
            for yy in 0..t {
                for &v in &anchor[(y + yy) * width + x..(y + yy) * width + x + t] {
                    sa += f64::from(v);
                    saa += f64::from(v) * f64::from(v);
                }
            }
            let mean_a = sa / n;
            let std_a = (saa / n - mean_a * mean_a).max(0.0).sqrt();
            if std_a < 0.01 {
                return None;
            }
            let mut scores = vec![-1.0f32; span * span];
            for dy in 0..span {
                for dx in 0..span {
                    let (by, bx) = (wy + dy, wx + dx);
                    let (mut sb, mut sbb, mut sab) = (0.0f64, 0.0f64, 0.0f64);
                    for yy in 0..t {
                        let ar = &anchor[(y + yy) * width + x..(y + yy) * width + x + t];
                        let br = &layer[(by + yy) * width + bx..(by + yy) * width + bx + t];
                        for (&a, &b) in ar.iter().zip(br) {
                            let (a, b) = (f64::from(a), f64::from(b));
                            sb += b;
                            sbb += b * b;
                            sab += a * b;
                        }
                    }
                    let mean_b = sb / n;
                    let std_b = (sbb / n - mean_b * mean_b).max(0.0).sqrt();
                    scores[dy * span + dx] =
                        ((sab / n - mean_a * mean_b) / (std_a * std_b + 1e-12)) as f32;
                }
            }
            let (best, &peak) = scores
                .iter()
                .enumerate()
                .max_by(|a, b| a.1.total_cmp(b.1))?;
            let (iy, ix) = (best / span, best % span);
            if peak < MIN_CORRELATION || iy == 0 || ix == 0 || iy == span - 1 || ix == span - 1 {
                return None;
            }
            let sub = |c: f32, l: f32, h: f32| {
                let den = l - 2.0 * c + h;
                if den.abs() < 1e-9 {
                    0.0
                } else {
                    (0.5 * (l - h) / den).clamp(-0.5, 0.5)
                }
            };
            let fy = (oy + iy as isize - r as isize) as f32
                + sub(peak, scores[best - span], scores[best + span]);
            let fx = (ox + ix as isize - r as isize) as f32
                + sub(peak, scores[best - 1], scores[best + 1]);
            Some((fy, fx, peak * peak))
        })
        .collect();
    let mut dy = vec![0.0f32; gw * gh];
    let mut dx = vec![0.0f32; gw * gh];
    let mut weight = vec![0.0f32; gw * gh];
    for (i, m) in measured.iter().enumerate() {
        if let Some((y, x, w)) = *m {
            (dy[i], dx[i], weight[i]) = (y, x, w);
        }
    }
    // Reject vectors far from the median of their accepted 5x5 neighbourhood.
    let mut rejected = 0;
    let mut keep = weight.clone();
    for gy in 0..gh {
        for gx in 0..gw {
            let i = gy * gw + gx;
            if weight[i] == 0.0 {
                continue;
            }
            let mut ny = Vec::new();
            let mut nx = Vec::new();
            for yy in gy.saturating_sub(2)..(gy + 3).min(gh) {
                for xx in gx.saturating_sub(2)..(gx + 3).min(gw) {
                    let j = yy * gw + xx;
                    if weight[j] > 0.0 {
                        ny.push(dy[j]);
                        nx.push(dx[j]);
                    }
                }
            }
            let my = quantile(ny, 0.5).unwrap_or(dy[i]);
            let mx = quantile(nx, 0.5).unwrap_or(dx[i]);
            if (dy[i] - my).hypot(dx[i] - mx) > grid.outlier_px {
                keep[i] = 0.0;
                rejected += 1;
            }
        }
    }
    let magnitudes: Vec<f32> = (0..gw * gh)
        .filter(|&i| keep[i] > 0.0)
        .map(|i| dy[i].hypot(dx[i]))
        .collect();
    let vectors = magnitudes.len();
    if vectors == 0 {
        return None;
    }
    let stats = FieldStats {
        vectors,
        rejected,
        median_px: f64::from(quantile(magnitudes.clone(), 0.5).unwrap_or(0.0)),
        p90_px: f64::from(quantile(magnitudes, 0.9).unwrap_or(0.0)),
    };
    let sy = fill_smooth(&dy, &keep, gw, gh, 1.5);
    let sx = fill_smooth(&dx, &keep, gw, gh, 1.5);
    // Grid (tile centres) to dense, bilinear with clamped ends.
    let origin = (t as f32 / 2.0, t as f32 / 2.0);
    let sample = |grid: &[f32], y: f32, x: f32| {
        let gy = ((y - origin.0) / s as f32).clamp(0.0, (gh - 1) as f32);
        let gx = ((x - origin.1) / s as f32).clamp(0.0, (gw - 1) as f32);
        let (y0, x0) = (gy.floor() as usize, gx.floor() as usize);
        let (y1, x1) = ((y0 + 1).min(gh - 1), (x0 + 1).min(gw - 1));
        let (fy, fx) = (gy - y0 as f32, gx - x0 as f32);
        let top = grid[y0 * gw + x0] * (1.0 - fx) + grid[y0 * gw + x1] * fx;
        let bottom = grid[y1 * gw + x0] * (1.0 - fx) + grid[y1 * gw + x1] * fx;
        top * (1.0 - fy) + bottom * fy
    };
    let mut dense_y = vec![0.0f32; width * height];
    let mut dense_x = vec![0.0f32; width * height];
    dense_y
        .par_chunks_mut(width)
        .zip(dense_x.par_chunks_mut(width))
        .enumerate()
        .for_each(|(y, (ry, rx))| {
            for x in 0..width {
                ry[x] = sample(&sy, y as f32, x as f32);
                rx[x] = sample(&sx, y as f32, x as f32);
            }
        });
    Some(Field {
        dy: dense_y,
        dx: dense_x,
        stats,
    })
}

/// Field equivalent to warping by `first` and then by `second`:
/// `layer(p + d2(p) + d1(p + d2(p)))`.
fn compose(first: &Field, second: &Field, width: usize, height: usize) -> Field {
    let sample = |grid: &[f32], y: f32, x: f32| {
        let y = y.clamp(0.0, (height - 1) as f32);
        let x = x.clamp(0.0, (width - 1) as f32);
        let (y0, x0) = ((y as usize).min(height - 2), (x as usize).min(width - 2));
        let (fy, fx) = (y - y0 as f32, x - x0 as f32);
        let at = |yy: usize, xx: usize| grid[yy * width + xx];
        (at(y0, x0) * (1.0 - fx) + at(y0, x0 + 1) * fx) * (1.0 - fy)
            + (at(y0 + 1, x0) * (1.0 - fx) + at(y0 + 1, x0 + 1) * fx) * fy
    };
    let n = width * height;
    let (dy, dx): (Vec<f32>, Vec<f32>) = (0..n)
        .into_par_iter()
        .map(|i| {
            let (y, x) = ((i / width) as f32, (i % width) as f32);
            let (sy, sx) = (y + second.dy[i], x + second.dx[i]);
            (
                second.dy[i] + sample(&first.dy, sy, sx),
                second.dx[i] + sample(&first.dx, sy, sx),
            )
        })
        .unzip();
    Field {
        dy,
        dx,
        stats: second.stats.clone(),
    }
}

/// Catmull-Rom weights for a fractional offset `t` (taps -1, 0, 1, 2).
fn cubic_weights(t: f32) -> [f32; 4] {
    let (t2, t3) = (t * t, t * t * t);
    [
        0.5 * (-t3 + 2.0 * t2 - t),
        0.5 * (3.0 * t3 - 5.0 * t2 + 2.0),
        0.5 * (-3.0 * t3 + 4.0 * t2 + t),
        0.5 * (t3 - t2),
    ]
}

/// Bicubic (Catmull-Rom) warp of a group by a dense field, so registration
/// does not soften fine detail; a pixel stays valid only when its whole 4x4
/// source neighbourhood is.
/// Source rows, columns and their Catmull-Rom weights of one warped pixel.
type Taps = ([usize; 4], [usize; 4], [f32; 4], [f32; 4]);

fn warp(group: &GroupPlanes, field: &Field, width: usize, height: usize) -> GroupPlanes {
    let n = width * height;
    let clamp_y = |v: isize| v.clamp(0, height as isize - 1) as usize;
    let clamp_x = |v: isize| v.clamp(0, width as isize - 1) as usize;
    let source = |i: usize| -> Option<Taps> {
        let y = (i / width) as f32 + field.dy[i];
        let x = (i % width) as f32 + field.dx[i];
        if y < 0.0 || x < 0.0 || y > (height - 1) as f32 || x > (width - 1) as f32 {
            return None;
        }
        let (y0, x0) = (y.floor() as isize, x.floor() as isize);
        let rows = std::array::from_fn(|k| clamp_y(y0 + k as isize - 1));
        let cols = std::array::from_fn(|k| clamp_x(x0 + k as isize - 1));
        Some((
            rows,
            cols,
            cubic_weights(y - y0 as f32),
            cubic_weights(x - x0 as f32),
        ))
    };
    let valid: Vec<bool> = (0..n)
        .into_par_iter()
        .map(|i| {
            source(i).is_some_and(|(rows, cols, _, _)| {
                rows.iter()
                    .all(|&r| cols.iter().all(|&c| group.valid[r * width + c]))
            })
        })
        .collect();
    let planes = std::array::from_fn(|p| {
        let plane = &group.planes[p];
        (0..n)
            .into_par_iter()
            .map(|i| match source(i) {
                Some((rows, cols, wy, wx)) => rows
                    .iter()
                    .zip(wy)
                    .map(|(&r, wy)| {
                        wy * cols
                            .iter()
                            .zip(wx)
                            .map(|(&c, wx)| wx * plane[r * width + c])
                            .sum::<f32>()
                    })
                    .sum(),
                None => 0.0,
            })
            .collect()
    });
    GroupPlanes {
        planes,
        valid,
        ceiling: group.ceiling,
    }
}

fn downsample(data: &[f32], width: usize, height: usize) -> (Vec<f32>, usize, usize) {
    let f = RATIO_DOWNSAMPLE;
    let (w, h) = (width.div_ceil(f), height.div_ceil(f));
    let mut out = vec![0.0f32; w * h];
    for (cell, o) in out.iter_mut().enumerate() {
        let (cy, cx) = (cell / w, cell % w);
        let (mut sum, mut count) = (0.0f64, 0usize);
        for y in cy * f..((cy + 1) * f).min(height) {
            for x in cx * f..((cx + 1) * f).min(width) {
                sum += f64::from(data[y * width + x]);
                count += 1;
            }
        }
        *o = (sum / count as f64) as f32;
    }
    (out, w, h)
}

fn upsample(data: &[f32], w: usize, h: usize, width: usize, height: usize) -> Vec<f32> {
    upsample_by(data, w, h, width, height, RATIO_DOWNSAMPLE)
}

/// Bilinear upsampling of a block-mean grid of factor `f` (block centres).
fn upsample_by(
    data: &[f32],
    w: usize,
    h: usize,
    width: usize,
    height: usize,
    f: usize,
) -> Vec<f32> {
    let f = f as f32;
    let mut out = vec![0.0f32; width * height];
    out.par_chunks_mut(width).enumerate().for_each(|(y, row)| {
        let gy = ((y as f32 + 0.5) / f - 0.5).clamp(0.0, (h - 1) as f32);
        let y0 = gy.floor() as usize;
        let y1 = (y0 + 1).min(h - 1);
        let fy = gy - y0 as f32;
        for (x, o) in row.iter_mut().enumerate() {
            let gx = ((x as f32 + 0.5) / f - 0.5).clamp(0.0, (w - 1) as f32);
            let x0 = gx.floor() as usize;
            let x1 = (x0 + 1).min(w - 1);
            let fx = gx - x0 as f32;
            let top = data[y0 * w + x0] * (1.0 - fx) + data[y0 * w + x1] * fx;
            let bottom = data[y1 * w + x0] * (1.0 - fx) + data[y1 * w + x1] * fx;
            *o = top * (1.0 - fy) + bottom * fy;
        }
    });
    out
}

/// |DoG| of `luma` between Gaussian scales sigma and 2 sigma, pooled locally.
fn local_band(luma: &[f32], width: usize, height: usize, sigma: f32, radius: usize) -> Vec<f32> {
    let a = gaussian_blur(luma, width, height, sigma);
    let b = gaussian_blur(luma, width, height, 2.0 * sigma);
    let band: Vec<f32> = a.iter().zip(&b).map(|(a, b)| (a - b).abs()).collect();
    box_mean(&band, width, height, radius)
}

/// Per-pixel weight in [0, 1] for where `layer` is locally as sharp as
/// `anchor`: the ratio of fine to coarse band contrast, relative to the
/// anchor's, is lighting-independent (lighting scales both bands) and falls
/// with defocus. Where the anchor has little structure, blur cannot show and
/// the weight returns to 1.
fn local_sharpness(
    anchor: &[f32],
    layer: &[f32],
    overlap: &[bool],
    width: usize,
    height: usize,
    cfg: &FusionConfig,
) -> (Vec<f32>, Vec<bool>) {
    let r = cfg.sharp_radius;
    let (fa, ca) = (
        local_band(anchor, width, height, 0.7, r),
        local_band(anchor, width, height, 2.8, r),
    );
    let (fl, cl) = (
        local_band(layer, width, height, 0.7, r),
        local_band(layer, width, height, 2.8, r),
    );
    let reference = quantile(
        (0..anchor.len())
            .filter(|&i| overlap[i])
            .map(|i| ca[i])
            .collect(),
        0.5,
    )
    .unwrap_or(0.0)
    .max(1e-12);
    // Clamped borders flatten both bands within the pooling reach of the
    // canvas edge, which reads as sharp: judge nothing there.
    let margin = r + 6;
    (0..anchor.len())
        .map(|i| {
            let (x, y) = (i % width, i / width);
            if x < margin || y < margin || x + margin >= width || y + margin >= height {
                return (0.0, false);
            }
            let shape = (fl[i] / cl[i].max(1e-12)) / (fa[i] / ca[i].max(1e-12)).max(1e-12);
            let structure = ca[i] / (ca[i] + 0.25 * reference);
            let blended = structure * shape + (1.0 - structure);
            (
                smoothstep(cfg.blur_reject, cfg.blur_accept, blended),
                structure > 0.5,
            )
        })
        .unzip()
}

/// Mean |band| of `luma` between Gaussian scales sigma and 2 sigma over `mask`.
fn band_contrast(luma: &[f32], mask: &[bool], width: usize, height: usize, sigma: f32) -> f64 {
    let a = gaussian_blur(luma, width, height, sigma);
    let b = gaussian_blur(luma, width, height, 2.0 * sigma);
    let (mut sum, mut count) = (0.0f64, 0usize);
    for i in 0..luma.len() {
        if mask[i] {
            sum += f64::from((a[i] - b[i]).abs());
            count += 1;
        }
    }
    sum / count.max(1) as f64
}

/// How a layer differs from the anchor, which decides how it may contribute.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LayerKind {
    /// Same geometry, other lamps: superposed everywhere it is sharp.
    Lighting,
    /// The subject moved between passes: superposed only where it matches
    /// the anchor after registration.
    Pose,
}

/// `kinds[k]` describes group `k` (entry 0, the anchor, is ignored; missing
/// entries are lighting layers).
pub fn fuse(
    groups: &[GroupPlanes],
    kinds: &[LayerKind],
    width: usize,
    height: usize,
) -> ([Vec<f32>; 4], FusionReport) {
    fuse_with(groups, kinds, width, height, &FusionConfig::default())
}

pub fn fuse_with(
    groups: &[GroupPlanes],
    kinds: &[LayerKind],
    width: usize,
    height: usize,
    cfg: &FusionConfig,
) -> ([Vec<f32>; 4], FusionReport) {
    let n = width * height;
    let anchor = &groups[0];
    let anchor_luma = luma(anchor);
    let floor = (anchor.ceiling * 1e-4).max(1e-6);
    let anchor_feature = feature(&anchor_luma, width, height, floor);
    let mut sum: [Vec<f64>; 4] =
        std::array::from_fn(|p| anchor.planes[p].iter().map(|&v| f64::from(v)).collect());
    let mut count = 1usize;
    let mut layers = Vec::new();
    for (index, original) in groups.iter().enumerate().skip(1) {
        let mut report = LayerReport {
            group: index,
            fine_contrast_ratio: 0.0,
            fine_over_coarse: 0.0,
            outcome: "no_overlap",
            residual_before: None,
            residual_after: None,
            brightness_gain: None,
            coverage: None,
            agreement: None,
            sharp_fraction: None,
        };
        // Defocus gate on the common bright subject.
        let common: Vec<bool> = anchor
            .valid
            .iter()
            .zip(&original.valid)
            .map(|(&a, &b)| a && b)
            .collect();
        let common = erode(&common, width, height, 8);
        let layer_luma = luma(original);
        let bright = quantile(
            (0..n)
                .filter(|&i| common[i])
                .map(|i| anchor_luma[i])
                .collect(),
            0.6,
        );
        let subject: Vec<bool> = (0..n)
            .map(|i| {
                common[i] && bright.is_some_and(|b| anchor_luma[i] > b && anchor_luma[i] > 0.0)
            })
            .collect();
        let gain0 = quantile(
            (0..n)
                .filter(|&i| subject[i])
                .map(|i| layer_luma[i] / anchor_luma[i])
                .collect(),
            0.5,
        );
        let Some(gain0) =
            gain0.filter(|g| *g > 0.0 && subject.iter().filter(|&&s| s).count() >= 1000)
        else {
            layers.push(report);
            continue;
        };
        let normalized: Vec<f32> = layer_luma.iter().map(|v| v / gain0).collect();
        let ratio = |sigma| {
            band_contrast(&normalized, &subject, width, height, sigma)
                / band_contrast(&anchor_luma, &subject, width, height, sigma).max(1e-12)
        };
        let (fine, coarse) = (ratio(0.7), ratio(2.8));
        report.fine_contrast_ratio = fine;
        report.fine_over_coarse = fine / coarse.max(1e-12);
        // Only a layer with no usable contrast at all is dropped here; a
        // partly defocused one (a short pass covering part of the depth) is
        // gated locally after registration.
        if fine < f64::from(cfg.min_fine_contrast) * 0.5 {
            report.outcome = "defocused";
            layers.push(report);
            continue;
        }
        // Residual registration onto the anchor.
        let layer_feature = feature(&layer_luma, width, height, floor);
        drop(normalized);
        let registered = match register(
            &anchor_feature,
            &layer_feature,
            &original.valid,
            width,
            height,
            cfg,
        ) {
            Some(field) => {
                report.residual_before = Some(field.stats.clone());
                // Large pose changes do not converge in one measurement:
                // re-measure on the warped layer and compose the fields, then
                // resample the original once (no repeated interpolation).
                let mut field = field;
                let mut warped = warp(original, &field, width, height);
                let mut after = None;
                for round in 0..=cfg.registration_rounds {
                    let feature_now = feature(&luma(&warped), width, height, floor);
                    let residual = register(
                        &anchor_feature,
                        &feature_now,
                        &warped.valid,
                        width,
                        height,
                        cfg,
                    );
                    let converged = residual
                        .as_ref()
                        .is_none_or(|r| r.stats.median_px <= cfg.converged_px);
                    if converged || round == cfg.registration_rounds {
                        after = residual.map(|r| r.stats);
                        break;
                    }
                    field = compose(&field, &residual.expect("residual"), width, height);
                    warped = warp(original, &field, width, height);
                }
                report.residual_after = after;
                warped
            }
            None => original.clone(),
        };
        drop(layer_feature);
        let layer = &registered;
        let layer_luma = luma(layer);
        // Relighting ratio over trusted overlap: covered, unclipped, not dark.
        let overlap: Vec<bool> = anchor
            .valid
            .iter()
            .zip(&layer.valid)
            .map(|(&a, &b)| a && b)
            .collect();
        let overlap = erode(&overlap, width, height, 4);
        let unclipped = |g: &GroupPlanes, i: usize| g.planes.iter().all(|p| p[i] < 0.9 * g.ceiling);
        let dark = quantile(
            (0..n)
                .filter(|&i| overlap[i])
                .map(|i| anchor_luma[i])
                .collect(),
            0.2,
        )
        .unwrap_or(0.0);
        let trusted: Vec<bool> = (0..n)
            .map(|i| {
                overlap[i]
                    && unclipped(anchor, i)
                    && unclipped(layer, i)
                    && anchor_luma[i] > dark
                    && layer_luma[i] > 0.0
            })
            .collect();
        let Some(log_gain) = quantile(
            (0..n)
                .filter(|&i| trusted[i])
                .map(|i| (layer_luma[i] / anchor_luma[i]).ln())
                .collect(),
            0.5,
        ) else {
            report.outcome = "no_overlap";
            layers.push(report);
            continue;
        };
        let coverage: Vec<f32> = erode(&layer.valid, width, height, 8)
            .iter()
            .map(|&v| f32::from(u8::from(v)))
            .collect();
        let alpha: Vec<f32> = box_mean(&coverage, width, height, cfg.feather)
            .into_iter()
            .map(|c| smoothstep(0.5, 1.0, c))
            .collect();
        drop(coverage);
        // Local defocus gate: the layer contributes only where it is as sharp
        // as the anchor, so a pass covering part of the depth adds where it is
        // in focus and nowhere else.
        let (sharp, structured) =
            local_sharpness(&anchor_luma, &layer_luma, &overlap, width, height, cfg);
        let judged = |i: usize| subject[i] && structured[i];
        let judged_pixels = (0..n).filter(|&i| judged(i)).count().max(1);
        report.sharp_fraction = Some(
            (0..n).filter(|&i| judged(i) && sharp[i] > 0.5).count() as f64 / judged_pixels as f64,
        );
        drop(structured);
        if report.sharp_fraction < Some(cfg.min_sharp_fraction) {
            report.outcome = "defocused";
            layers.push(report);
            continue;
        }
        let alpha: Vec<f32> = alpha.iter().zip(&sharp).map(|(a, s)| a * s).collect();
        drop(sharp);
        let scale = f64::from((-log_gain).exp());
        let relit = |trusted: &[bool]| -> [Vec<f32>; 4] {
            std::array::from_fn(|p| {
                let (a, b) = (&anchor.planes[p], &layer.planes[p]);
                let weights: Vec<f32> = (0..n)
                    .map(|i| {
                        if trusted[i] {
                            a[i].max(0.0).sqrt()
                        } else {
                            0.0
                        }
                    })
                    .collect();
                let weighted: Vec<f32> = (0..n)
                    .map(|i| {
                        if trusted[i] {
                            weights[i] * (b[i].max(floor) / a[i].max(floor)).ln()
                        } else {
                            0.0
                        }
                    })
                    .collect();
                let (vw, w, h) = downsample(&weighted, width, height);
                let (ww, _, _) = downsample(&weights, width, height);
                let values: Vec<f32> = vw
                    .iter()
                    .zip(&ww)
                    .map(|(v, w)| if *w > 0.0 { v / w } else { 0.0 })
                    .collect();
                let field = fill_smooth(
                    &values,
                    &ww,
                    w,
                    h,
                    cfg.ratio_sigma / RATIO_DOWNSAMPLE as f32,
                );
                let relight = upsample(&field, w, h, width, height);
                (0..n).map(|i| a[i] * relight[i].exp()).collect()
            })
        };
        let mut predicted = relit(&trusted);
        // A pose layer is the same subject moved: after registration and
        // relighting it must match the anchor, and wherever it does not (a
        // limb moved, an occlusion) it yields to the relit anchor rather than
        // ghosting. Lighting layers are not gated: their differences are the
        // other lamps' light.
        let alpha = match kinds.get(index).copied().unwrap_or(LayerKind::Lighting) {
            LayerKind::Lighting => alpha,
            LayerKind::Pose => {
                let agreement = |predicted: &[Vec<f32>; 4]| -> Vec<f32> {
                    let difference: Vec<f32> = (0..n)
                        .map(|i| {
                            let p = 0.25 * predicted.iter().map(|p| p[i]).sum::<f32>();
                            (layer_luma[i].max(floor) / p.max(floor)).ln()
                        })
                        .collect();
                    let agree: Vec<f32> = gaussian_blur(&difference, width, height, 2.0)
                        .iter()
                        .map(|d| 1.0 - smoothstep(cfg.pose_agree, cfg.pose_disagree, d.abs()))
                        .collect();
                    // Shrink agreement away from disagreement: no fringe ghosts.
                    box_mean(&agree, width, height, 6)
                        .into_iter()
                        .zip(agree)
                        .map(|(m, a)| a.min(smoothstep(0.5, 1.0, m)))
                        .collect()
                };
                // Moved structure must not steer the relighting either:
                // refit the ratio on agreeing pixels only, then re-gate.
                let first = agreement(&predicted);
                let trusted: Vec<bool> = (0..n).map(|i| trusted[i] && first[i] > 0.5).collect();
                predicted = relit(&trusted);
                let agree = agreement(&predicted);
                let covered = (0..n).filter(|&i| alpha[i] > 0.5).count().max(1);
                report.agreement = Some(
                    (0..n).filter(|&i| alpha[i] > 0.5 && agree[i] > 0.5).count() as f64
                        / covered as f64,
                );
                alpha.iter().zip(&agree).map(|(a, g)| a * g).collect()
            }
        };
        for (p, predicted) in predicted.iter().enumerate() {
            let b = &layer.planes[p];
            sum[p].par_iter_mut().enumerate().for_each(|(i, s)| {
                let value = if layer.valid[i] {
                    alpha[i] * b[i] + (1.0 - alpha[i]) * predicted[i]
                } else {
                    predicted[i]
                };
                *s += f64::from(value) * scale;
            });
        }
        report.outcome = "superposed";
        report.brightness_gain = Some(f64::from(log_gain.exp()));
        report.coverage = Some(alpha.iter().map(|&a| f64::from(a)).sum::<f64>() / n as f64);
        count += 1;
        layers.push(report);
    }
    // Keep the anchor's near-clipped highlights: clipped values are lower
    // bounds, and averaging them darkens real speculars.
    let near: Vec<f32> = (0..n)
        .map(|i| {
            let peak = anchor.planes.iter().map(|p| p[i]).fold(0.0f32, f32::max);
            smoothstep(
                cfg.highlight_start,
                cfg.highlight_full,
                peak / anchor.ceiling,
            )
        })
        .collect();
    let keep: Vec<f32> = box_mean(&near, width, height, 2)
        .into_iter()
        .map(|v| (3.0 * v).min(1.0))
        .collect();
    let anchor_highlight_fraction = keep.iter().filter(|&&k| k > 0.5).count() as f64 / n as f64;
    let planes = std::array::from_fn(|p| {
        (0..n)
            .into_par_iter()
            .map(|i| {
                let mean = (sum[p][i] / count as f64) as f32;
                keep[i] * anchor.planes[p][i] + (1.0 - keep[i]) * mean
            })
            .collect()
    });
    let report = FusionReport {
        schema: "strehl.session-lighting-fusion.v5",
        groups: groups.len(),
        superposed: count,
        layers,
        anchor_highlight_fraction,
        config: *cfg,
        semantics: "equal-weight light superposition of brightness-normalised lighting groups, each registered onto the anchor by a dense residual field; uncovered canvas predicted from the anchor and the smooth relighting ratio; anchor near-clipped highlights kept",
    };
    (planes, report)
}

// --- detached layers --------------------------------------------------------

/// Where a separately stacked pass sits on the anchor canvas.
#[derive(Clone, Debug, serde::Serialize)]
pub struct DetachedPlacement {
    /// Layer plane px per canvas plane px.
    pub scale: f64,
    pub rotation_deg: f64,
    /// Verified overlap-weighted NCC of the chosen proposal on finer
    /// lighting-insensitive structure (8--32 plane px).
    pub ncc: f64,
    /// Verified NCC of the best clearly different proposal.
    pub runner_up_ncc: Option<f64>,
    pub accepted: bool,
}

/// Decimation of the coarse placement features (plane px per feature px).
const DETACHED_FEATURE_FACTOR: usize = 4;
/// Distinct coarse proposals re-scored on finer structure.
const DETACHED_VERIFY: usize = 8;

/// Finer verification of a placement: overlap-weighted masked NCC of
/// band-passed log luma at 8--32 plane px (half resolution) between the anchor
/// and the layer warped through the proposal, with a small translation search.
struct Verifier {
    anchor: Vec<f32>,
    layer: Vec<f32>,
    aw: usize,
    ah: usize,
    lw2: usize,
    lh2: usize,
    width: usize,
    height: usize,
    lw: usize,
    lh: usize,
}

impl Verifier {
    fn feature(group: &GroupPlanes, width: usize, height: usize) -> (Vec<f32>, usize, usize) {
        let (w, h) = (width / 2, height / 2);
        let l = luma(group);
        let floor = (group.ceiling * 1e-4).max(1e-6);
        let small: Vec<f32> = (0..w * h)
            .map(|c| {
                let (y, x) = (c / w * 2, c % w * 2);
                let mean = 0.25
                    * (l[y * width + x]
                        + l[y * width + x + 1]
                        + l[(y + 1) * width + x]
                        + l[(y + 1) * width + x + 1]);
                mean.max(floor).ln()
            })
            .collect();
        // 8--32 plane px: finer than the search features, coarse enough to
        // survive a change of lighting.
        let a = gaussian_blur(&small, w, h, 4.0);
        let b = gaussian_blur(&small, w, h, 16.0);
        (a.iter().zip(&b).map(|(a, b)| a - b).collect(), w, h)
    }

    fn new(
        anchor: &GroupPlanes,
        layer: &GroupPlanes,
        lw: usize,
        lh: usize,
        width: usize,
        height: usize,
    ) -> Self {
        let (a, aw, ah) = Self::feature(anchor, width, height);
        let (l, lw2, lh2) = Self::feature(layer, lw, lh);
        Self {
            anchor: a,
            layer: l,
            aw,
            ah,
            lw2,
            lh2,
            width,
            height,
            lw,
            lh,
        }
    }

    /// Masked NCC through `s` after shifting the canvas sample by `shift`
    /// verification px, and the overlap as a fraction of the canvas.
    fn ncc(&self, s: &strehl_core::align::Similarity, shift: (f64, f64)) -> (f64, f64) {
        let (mut sa, mut sb, mut saa, mut sbb, mut sab, mut n) =
            (0.0f64, 0.0f64, 0.0f64, 0.0f64, 0.0f64, 0.0f64);
        for v in 0..self.ah {
            for u in 0..self.aw {
                // Verification pixel centre in canvas plane px, centred.
                let p = strehl_core::align::Cx::new(
                    2.0 * (u as f64 + shift.0) + 1.0 - self.width as f64 / 2.0,
                    2.0 * (v as f64 + shift.1) + 1.0 - self.height as f64 / 2.0,
                );
                let q = s.apply(p);
                let x = (q.re + self.lw as f64 / 2.0 - 1.0) / 2.0;
                let y = (q.im + self.lh as f64 / 2.0 - 1.0) / 2.0;
                if x < 0.0 || y < 0.0 || x >= (self.lw2 - 1) as f64 || y >= (self.lh2 - 1) as f64 {
                    continue;
                }
                let (x0, y0) = (x as usize, y as usize);
                let (fx, fy) = ((x - x0 as f64) as f32, (y - y0 as f64) as f32);
                let at = |yy: usize, xx: usize| self.layer[yy * self.lw2 + xx];
                let b = (at(y0, x0) * (1.0 - fx) + at(y0, x0 + 1) * fx) * (1.0 - fy)
                    + (at(y0 + 1, x0) * (1.0 - fx) + at(y0 + 1, x0 + 1) * fx) * fy;
                let a = self.anchor[v * self.aw + u];
                let (a, b) = (f64::from(a), f64::from(b));
                sa += a;
                sb += b;
                saa += a * a;
                sbb += b * b;
                sab += a * b;
                n += 1.0;
            }
        }
        let overlap = n / (self.aw * self.ah) as f64;
        if overlap < 0.05 {
            return (0.0, overlap);
        }
        let cov = sab / n - (sa / n) * (sb / n);
        let va = saa / n - (sa / n).powi(2);
        let vb = sbb / n - (sb / n).powi(2);
        (cov / (va * vb).sqrt().max(1e-12), overlap)
    }

    /// Best overlap-weighted NCC over small translations (+-6 verification px,
    /// +-12 plane px), and the proposal refined by that translation. Weighting
    /// by the square root of the overlap keeps sliver overlaps, where a few
    /// samples correlate by chance, from outscoring a broad true overlap.
    fn score(&self, s: &strehl_core::align::Similarity) -> (f64, strehl_core::align::Similarity) {
        let mut best = (f64::NEG_INFINITY, (0.0, 0.0));
        for dy in (-6..=6).step_by(2) {
            for dx in (-6..=6).step_by(2) {
                let (ncc, overlap) = self.ncc(s, (f64::from(dx), f64::from(dy)));
                let value = ncc * overlap.min(1.0).sqrt();
                if value > best.0 {
                    best = (value, (f64::from(dx), f64::from(dy)));
                }
            }
        }
        // Canvas shift d (plane px) maps to layer translation a*d.
        let d = strehl_core::align::Cx::new(2.0 * best.1.0, 2.0 * best.1.1);
        (
            best.0,
            strehl_core::align::Similarity {
                a: s.a,
                b: s.b + s.a * d,
            },
        )
    }
}
/// Verified overlap-weighted NCC needed, and its margin over the runner-up.
const DETACHED_MIN_NCC: f64 = 0.3;
const DETACHED_MIN_MARGIN: f64 = 0.05;

/// Coarse, lighting-insensitive structure for placement: band-passed log luma
/// at 0.5--2% of the canvas width (fine texture such as iridescent scales does
/// not repeat across sessions), made positive because the global search compresses
/// intensities with a square root.
fn placement_feature(group: &GroupPlanes, width: usize, height: usize) -> (Vec<f32>, usize, usize) {
    let f = DETACHED_FEATURE_FACTOR;
    let (w, h) = (width / f, height / f);
    let l = luma(group);
    let floor = (group.ceiling * 1e-4).max(1e-6);
    let small: Vec<f32> = (0..w * h)
        .map(|c| {
            let (y, x) = (c / w * f, c % w * f);
            let mean = (0..f * f)
                .map(|k| l[(y + k / f) * width + x + k % f])
                .sum::<f32>()
                / (f * f) as f32;
            mean.max(floor).ln()
        })
        .collect();
    // About 0.5% and 2% of the canvas width (16 and 64 plane px on a
    // 24-megapixel canvas), so small inputs keep proportionate structure.
    let sigma = (width as f32 / (200 * f) as f32).max(1.0);
    let a = gaussian_blur(&small, w, h, sigma);
    let b = gaussian_blur(&small, w, h, 4.0 * sigma);
    let band: Vec<f32> = a.iter().zip(&b).map(|(a, b)| a - b).collect();
    let low = band.iter().copied().fold(f32::INFINITY, f32::min);
    (
        band.iter().map(|v| (v - low + 0.05).powi(2)).collect(),
        w,
        h,
    )
}

/// `image` rotated by `k` quarter turns about its centre: output centred
/// point `p` samples input centred point `i^k p` (complex `x + iy`).
fn quarter_turn(image: &[f32], w: usize, h: usize, k: usize) -> (Vec<f32>, usize, usize) {
    let (rw, rh) = if k % 2 == 1 { (h, w) } else { (w, h) };
    let out = (0..rw * rh)
        .map(|i| {
            let (x, y) = (
                (i % rw) as f64 + 0.5 - rw as f64 / 2.0,
                (i / rw) as f64 + 0.5 - rh as f64 / 2.0,
            );
            let (qx, qy) = match k % 4 {
                0 => (x, y),
                1 => (-y, x),
                2 => (-x, -y),
                _ => (y, -x),
            };
            let sx = (qx + w as f64 / 2.0 - 0.5)
                .round()
                .clamp(0.0, (w - 1) as f64) as usize;
            let sy = (qy + h as f64 / 2.0 - 0.5)
                .round()
                .clamp(0.0, (h - 1) as f64) as usize;
            image[sy * w + sx]
        })
        .collect();
    (out, rw, rh)
}

/// Locate a separately stacked layer (its own canvas, `lw` x `lh`) on the
/// anchor canvas and resample it there. The search covers 1/4..4x scale and a
/// full turn (four quarter-turn pre-rotations, each +-48 degrees), on
/// lighting-insensitive coarse features. Each CFA plane is sampled at its own
/// site phase, and minification is prefiltered so no aliasing is introduced.
pub fn place_detached(
    anchor: &GroupPlanes,
    layer: &GroupPlanes,
    lw: usize,
    lh: usize,
    width: usize,
    height: usize,
) -> (Option<GroupPlanes>, DetachedPlacement) {
    let search = strehl_core::align_global::GlobalSearchConfig {
        max_rotation: 48f64.to_radians(),
        rotation_step: 4f64.to_radians(),
        min_overlap_fraction: 0.2,
        candidates: 6,
        ..strehl_core::align_global::GlobalSearchConfig::default()
    };
    place_detached_with(anchor, layer, lw, lh, width, height, &search)
}

/// [`place_detached`] with an explicit search grid (each quarter turn).
pub fn place_detached_with(
    anchor: &GroupPlanes,
    layer: &GroupPlanes,
    lw: usize,
    lh: usize,
    width: usize,
    height: usize,
    cfg: &strehl_core::align_global::GlobalSearchConfig,
) -> (Option<GroupPlanes>, DetachedPlacement) {
    use strehl_core::align::{Cx, PlaneRef, Similarity, lift_box_decimated_similarity};
    use strehl_core::align_global::global_similarity_candidates;
    use strehl_core::plane::PlaneGeometry;
    let mut placement = DetachedPlacement {
        scale: 0.0,
        rotation_deg: 0.0,
        ncc: 0.0,
        runner_up_ncc: None,
        accepted: false,
    };
    let (af, aw, ah) = placement_feature(anchor, width, height);
    let (lf, lfw, lfh) = placement_feature(layer, lw, lh);
    let i_pow = |k: usize| {
        [
            Cx::new(1.0, 0.0),
            Cx::new(0.0, 1.0),
            Cx::new(-1.0, 0.0),
            Cx::new(0.0, -1.0),
        ][k % 4]
    };
    let mut proposals: Vec<(f64, Similarity)> = (0..4usize)
        .into_par_iter()
        .flat_map_iter(|k| {
            let (rf, rw, rh) = quarter_turn(&lf, lfw, lfh, k);
            let (Some(reference), Some(moving)) =
                (PlaneRef::new(&af, aw, ah), PlaneRef::new(&rf, rw, rh))
            else {
                return Vec::new();
            };
            let (lgw, lgh) = if k % 2 == 1 { (lh, lw) } else { (lw, lh) };
            global_similarity_candidates(reference, moving, cfg)
                .into_iter()
                .filter_map(|c| {
                    let lifted = lift_box_decimated_similarity(
                        c.transform,
                        PlaneGeometry { width, height },
                        PlaneGeometry {
                            width: lgw,
                            height: lgh,
                        },
                        DETACHED_FEATURE_FACTOR,
                    )?;
                    // Rotated-centred -> original layer-centred: multiply by i^k.
                    let turn = i_pow(k);
                    Some((
                        c.ncc,
                        Similarity {
                            a: turn * lifted.a,
                            b: turn * lifted.b,
                        },
                    ))
                })
                .collect::<Vec<_>>()
        })
        .collect();
    proposals.sort_by(|a, b| b.0.total_cmp(&a.0));
    let diag = ((width * width + height * height) as f64).sqrt();
    let distinct = |s: &Similarity, t: &Similarity| {
        (s.b - t.b).abs() > 0.1 * diag || (s.scale() / t.scale()).ln().abs() > 0.1 || {
            let d = (s.rotation() - t.rotation()).abs();
            d.min(std::f64::consts::TAU - d) > 10f64.to_radians()
        }
    };
    // Coarse features can confuse mirror-like structure (a beetle's two wing
    // covers); verify the strongest distinct proposals on finer structure.
    let mut shortlist: Vec<Similarity> = Vec::new();
    for (_, s) in &proposals {
        if shortlist.len() < DETACHED_VERIFY && shortlist.iter().all(|t| distinct(s, t)) {
            shortlist.push(*s);
        }
    }
    let verifier = Verifier::new(anchor, layer, lw, lh, width, height);
    let mut verified: Vec<(f64, Similarity)> =
        shortlist.par_iter().map(|s| verifier.score(s)).collect();
    verified.sort_by(|a, b| b.0.total_cmp(&a.0));
    let Some(&(ncc, best)) = verified.first() else {
        return (None, placement);
    };
    placement.scale = best.scale();
    placement.rotation_deg = best.rotation().to_degrees();
    placement.ncc = ncc;
    placement.runner_up_ncc = verified.get(1).map(|(n, _)| *n);
    placement.accepted = ncc >= DETACHED_MIN_NCC
        && placement
            .runner_up_ncc
            .is_none_or(|r| ncc - r >= DETACHED_MIN_MARGIN);
    if !placement.accepted {
        return (None, placement);
    }
    // Resample: canvas plane px (centred) -> layer plane px (centred) by
    // `best`; each plane at its CFA site phase (R, G1, B, G2 offsets in plane
    // px), prefiltered by the minification.
    let phase = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]; // (x, y)
    let s = best.scale();
    let sigma = if s > 1.05 {
        0.5 * (s * s - 1.0).sqrt() as f32
    } else {
        0.0
    };
    let n = width * height;
    let source = |i: usize, c: usize| -> Option<(f64, f64)> {
        let (ox, oy) = phase[c];
        let p = Cx::new(
            (i % width) as f64 + ox - width as f64 / 2.0,
            (i / width) as f64 + oy - height as f64 / 2.0,
        );
        let q = best.apply(p);
        let (x, y) = (q.re + lw as f64 / 2.0 - ox, q.im + lh as f64 / 2.0 - oy);
        (x >= 1.0 && y >= 1.0 && x <= (lw - 3) as f64 && y <= (lh - 3) as f64).then_some((x, y))
    };
    let planes: [Vec<f32>; 4] = std::array::from_fn(|c| {
        let plane = gaussian_blur(&layer.planes[c], lw, lh, sigma);
        (0..n)
            .into_par_iter()
            .map(|i| match source(i, c) {
                Some((x, y)) => {
                    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
                    let (wx, wy) = (
                        cubic_weights((x - x0 as f64) as f32),
                        cubic_weights((y - y0 as f64) as f32),
                    );
                    let mut v = 0.0f32;
                    for (r, wy) in wy.iter().enumerate() {
                        for (q, wx) in wx.iter().enumerate() {
                            v += wy * wx * plane[(y0 + r - 1) * lw + x0 + q - 1];
                        }
                    }
                    v
                }
                None => 0.0,
            })
            .collect()
    });
    let valid: Vec<bool> = (0..n)
        .into_par_iter()
        .map(|i| {
            (0..4).all(|c| {
                source(i, c).is_some_and(|(x, y)| {
                    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
                    (0..4).all(|r| (0..4).all(|q| layer.valid[(y0 + r - 1) * lw + x0 + q - 1]))
                })
            })
        })
        .collect();
    (
        Some(GroupPlanes {
            planes,
            valid,
            ceiling: layer.ceiling,
        }),
        placement,
    )
}

/// Diagnostic dump of captured groups (`STREHL_LIGHTING_DUMP`), so fusion can
/// be studied without re-merging: `meta.json` plus raw little-endian planes.
pub fn dump(
    groups: &[GroupPlanes],
    kinds: &[LayerKind],
    width: usize,
    height: usize,
    dir: &std::path::Path,
) -> anyhow::Result<()> {
    use std::io::Write;
    std::fs::create_dir_all(dir)?;
    let ceilings: Vec<f32> = groups.iter().map(|g| g.ceiling).collect();
    std::fs::write(
        dir.join("meta.json"),
        serde_json::to_vec(
            &serde_json::json!({"width": width, "height": height, "ceilings": ceilings, "kinds": kinds}),
        )?,
    )?;
    for (k, g) in groups.iter().enumerate() {
        let mut f =
            std::io::BufWriter::new(std::fs::File::create(dir.join(format!("group-{k}.f32")))?);
        for plane in &g.planes {
            for v in plane {
                f.write_all(&v.to_le_bytes())?;
            }
        }
        f.flush()?;
        std::fs::write(
            dir.join(format!("group-{k}.valid")),
            g.valid.iter().map(|&v| u8::from(v)).collect::<Vec<_>>(),
        )?;
    }
    Ok(())
}

/// Read a [`dump`].
#[allow(clippy::type_complexity)]
pub fn load_dump(
    dir: &std::path::Path,
) -> anyhow::Result<(Vec<GroupPlanes>, Vec<LayerKind>, usize, usize)> {
    let meta: serde_json::Value = serde_json::from_slice(&std::fs::read(dir.join("meta.json"))?)?;
    let width = meta["width"].as_u64().unwrap_or(0) as usize;
    let height = meta["height"].as_u64().unwrap_or(0) as usize;
    let n = width * height;
    let mut groups = Vec::new();
    for (k, c) in meta["ceilings"]
        .as_array()
        .into_iter()
        .flatten()
        .enumerate()
    {
        let bytes = std::fs::read(dir.join(format!("group-{k}.f32")))?;
        anyhow::ensure!(bytes.len() == 16 * n, "group {k} has the wrong size");
        let values: Vec<f32> = bytes
            .as_chunks::<4>()
            .0
            .iter()
            .map(|b| f32::from_le_bytes(*b))
            .collect();
        let planes = std::array::from_fn(|p| values[p * n..(p + 1) * n].to_vec());
        let valid = std::fs::read(dir.join(format!("group-{k}.valid")))?
            .into_iter()
            .map(|v| v != 0)
            .collect();
        groups.push(GroupPlanes {
            planes,
            valid,
            ceiling: c.as_f64().unwrap_or(1.0) as f32,
        });
    }
    let kinds = serde_json::from_value(meta["kinds"].clone()).unwrap_or_default();
    Ok((groups, kinds, width, height))
}

#[cfg(test)]
mod tests {
    use super::*;

    const W: usize = 256;
    const H: usize = 192;

    fn group(value: impl Fn(f32, f32) -> f32) -> GroupPlanes {
        let plane: Vec<f32> = (0..W * H)
            .map(|i| value((i % W) as f32, (i / W) as f32))
            .collect();
        GroupPlanes {
            planes: [plane.clone(), plane.clone(), plane.clone(), plane],
            valid: vec![true; W * H],
            ceiling: 4000.0,
        }
    }

    /// Deterministic pseudo-noise in [-1, 1].
    fn noise(x: f32, y: f32, seed: u32) -> f32 {
        let mut v = (x as u32).wrapping_mul(0x9E37_79B9)
            ^ (y as u32).wrapping_mul(0x85EB_CA6B)
            ^ seed.wrapping_mul(0xC2B2_AE35);
        v ^= v >> 15;
        v = v.wrapping_mul(0x2C1B_3C6D);
        v ^= v >> 12;
        (v & 0xFFFF) as f32 / 32767.5 - 1.0
    }

    /// Band-limited multi-scale texture: registrable at every tile.
    fn texture(x: f32, y: f32) -> f32 {
        let a = (x * 0.31).sin() * (y * 0.23).cos();
        let b = (x * 0.13 + y * 0.07).sin();
        let c = ((x - y) * 0.47).cos() * (y * 0.11).sin();
        let d = ((x * 0.053).sin() * (y * 0.061).cos() * 9.0).sin();
        1.0 + 0.25 * a + 0.2 * b + 0.15 * c + 0.2 * d
    }

    fn shading(x: f32, y: f32) -> f32 {
        0.6 + 0.8 * (x / W as f32) * (0.7 + 0.3 * (y / H as f32))
    }

    fn worst_interior(a: &[f32], b: impl Fn(usize) -> f32, margin: usize) -> f32 {
        let mut worst = 0.0f32;
        for y in margin..H - margin {
            for x in margin..W - margin {
                let i = y * W + x;
                worst = worst.max((a[i] - b(i)).abs() / b(i).abs().max(1.0));
            }
        }
        worst
    }

    #[test]
    fn identical_groups_superpose_to_the_input() {
        let f = |x, y| 500.0 * texture(x, y);
        let (fused, report) = fuse(&[group(f), group(f)], &[], W, H);
        let worst = worst_interior(&fused[1], |i| f((i % W) as f32, (i / W) as f32), 0);
        assert!(worst < 2e-3, "{worst} {report:?}");
        assert_eq!(report.superposed, 2, "{report:?}");
    }

    #[test]
    fn a_relit_layer_superposes_without_seams_at_its_coverage_edge() {
        // The layer is the same subject under a smooth different lighting,
        // twice as bright, covering only the left half.
        let anchor = group(|x, y| 500.0 * texture(x, y));
        let mut partial = group(|x, y| 1000.0 * texture(x, y) * shading(x, y));
        for i in 0..W * H {
            if i % W >= W / 2 {
                partial.valid[i] = false;
                for plane in &mut partial.planes {
                    plane[i] = 0.0;
                }
            }
        }
        let (fused, report) = fuse(&[anchor, partial], &[], W, H);
        assert_eq!(report.layers[0].outcome, "superposed", "{report:?}");
        // Seamless: the fused/anchor ratio changes smoothly across the edge.
        // The relit fill and the coverage feather each prevent a step; with
        // neither (constant-gain fill, hard cut) this fails (mutation check).
        let mut worst = 0.0f32;
        for y in 16..H - 16 {
            for x in 16..W - 17 {
                let q = |x: usize| fused[0][y * W + x] / (500.0 * texture(x as f32, y as f32));
                worst = worst.max((q(x + 1) - q(x)).abs());
            }
        }
        assert!(worst < 0.01, "coverage edge left a seam: {worst}");
    }

    #[test]
    fn residual_misregistration_is_measured_and_removed() {
        let f = |x: f32, y: f32| 500.0 * texture(x, y);
        let anchor = group(f);
        // Same lighting, displaced by (1.6, -2.3) px: averaging without
        // registration would blur the texture.
        let layer = group(|x, y| f(x - 2.3, y + 1.6));
        let (fused, report) = fuse(&[anchor, layer], &[], W, H);
        let layer_report = &report.layers[0];
        let before = layer_report.residual_before.as_ref().expect("field");
        assert!((before.median_px - 2.8).abs() < 0.3, "{report:?}");
        assert!(
            layer_report.residual_after.as_ref().unwrap().median_px < 0.3,
            "{report:?}"
        );
        let worst = worst_interior(&fused[2], |i| f((i % W) as f32, (i / W) as f32), 24);
        assert!(worst < 0.03, "registered superposition blurred: {worst}");
    }

    /// Coarse aperiodic structure: pseudo-random blobs of 8..40 px radius, so
    /// no rotation or reflection of the scene resembles itself.
    fn scene(x: f32, y: f32) -> f32 {
        let mut v = 300.0;
        for k in 0..90u32 {
            let r = |s: u32| (noise(k as f32, s as f32, 17 + s) + 1.0) * 0.5;
            let (cx, cy) = (r(1) * 560.0 - 24.0, r(2) * 430.0 - 23.0);
            let radius = 8.0 + 32.0 * r(3);
            let amplitude = 400.0 * (r(4) - 0.4);
            let d2 = ((x - cx).powi(2) + (y - cy).powi(2)) / (radius * radius);
            v += amplitude * (-d2).exp();
        }
        v.max(40.0) + 20.0 * texture(x, y)
    }

    #[test]
    fn a_detached_layer_is_found_through_rotation_magnification_and_relighting() {
        // A half turn at 1.6x, and a quarter turn at 1.3x (odd turns swap the
        // layer's axes, which a half turn cannot reveal).
        detached_case(strehl_core::align::Cx::new(-1.6, 0.05), 180.0);
        detached_case(strehl_core::align::Cx::new(0.04, 1.3), 90.0);
    }

    fn detached_case(a: strehl_core::align::Cx, rotation: f64) {
        let (w, h) = (512usize, 384usize);
        let anchor = GroupPlanes {
            planes: std::array::from_fn(|_| {
                (0..w * h)
                    .map(|i| scene((i % w) as f32, (i / w) as f32))
                    .collect()
            }),
            valid: vec![true; w * h],
            ceiling: 4000.0,
        };
        // The layer is its own canvas: canvas-centred p maps to layer-centred
        // q = a p + b with |a| = 1.6 and a half turn; lit differently per channel.
        let b = strehl_core::align::Cx::new(14.0, -9.0);
        let (lw, lh) = (320usize, 240usize);
        let gains = [0.55f32, 0.7, 0.4, 0.7];
        let inverse = strehl_core::align::Similarity { a, b }.invert().unwrap();
        let layer = GroupPlanes {
            planes: std::array::from_fn(|c| {
                (0..lw * lh)
                    .map(|i| {
                        let q = strehl_core::align::Cx::new(
                            (i % lw) as f64 - lw as f64 / 2.0,
                            (i / lw) as f64 - lh as f64 / 2.0,
                        );
                        let p = inverse.apply(q);
                        gains[c]
                            * scene(
                                (p.re + w as f64 / 2.0) as f32,
                                (p.im + h as f64 / 2.0) as f32,
                            )
                    })
                    .collect()
            }),
            valid: vec![true; lw * lh],
            ceiling: 4000.0,
        };
        // A coarser grid than the default keeps this test fast in debug builds.
        let search = strehl_core::align_global::GlobalSearchConfig {
            max_rotation: 45f64.to_radians(),
            rotation_step: 7.5f64.to_radians(),
            log_scale_step: 0.08,
            min_overlap_fraction: 0.2,
            candidates: 6,
            ..strehl_core::align_global::GlobalSearchConfig::default()
        };
        let (placed, report) = place_detached_with(&anchor, &layer, lw, lh, w, h, &search);
        assert!(report.accepted, "{report:?}");
        assert!((report.scale / a.abs() - 1.0).abs() < 0.04, "{report:?}");
        let turn = (report.rotation_deg - rotation).rem_euclid(360.0);
        assert!(turn.min(360.0 - turn) < 8.0, "{report:?}");
        let placed = placed.expect("placed");
        // Where valid, the placed layer is the anchor scene relit (gain only).
        let (mut sum, mut count) = (0.0f64, 0usize);
        for i in 0..w * h {
            if placed.valid[i] {
                let expected = gains[1] * anchor.planes[1][i];
                sum += f64::from((placed.planes[1][i] - expected).abs() / expected);
                count += 1;
            }
        }
        assert!(count > 5000, "covered {count}");
        assert!(
            sum / (count as f64) < 0.08,
            "mean relative error {}",
            sum / count as f64
        );
    }

    #[test]
    fn a_smoothly_deformed_layer_is_registered_in_composed_rounds() {
        let f = |x: f32, y: f32| 500.0 * texture(x, y);
        let anchor = group(f);
        // A smooth non-rigid deformation of up to ~5 px (a pose change).
        let shift = |x: f32, y: f32| (4.0 * (y / 70.0).sin() + 1.5, 3.0 * (x / 90.0).cos());
        let layer = group(|x, y| {
            let (sx, sy) = shift(x, y);
            f(x - sx, y - sy)
        });
        let kinds = [LayerKind::Lighting, LayerKind::Pose];
        let (_, report) = fuse(&[anchor, layer], &kinds, W, H);
        let after = report.layers[0].residual_after.as_ref().expect("residual");
        assert!(after.median_px <= 0.5, "{report:?}");
    }

    #[test]
    fn a_defocused_layer_is_not_superposed() {
        let anchor = group(|x, y| 500.0 * texture(x, y) + 30.0 * noise(x, y, 7).signum());
        let sharp = anchor.planes[0].clone();
        let blurred = gaussian_blur(&sharp, W, H, 3.0);
        let mut layer = anchor.clone();
        layer.planes = std::array::from_fn(|_| blurred.iter().map(|v| 0.7 * v).collect());
        let (fused, report) = fuse(&[anchor, layer], &[], W, H);
        assert_eq!(report.layers[0].outcome, "defocused", "{report:?}");
        assert_eq!(report.superposed, 1);
        assert!(
            fused[0]
                .iter()
                .zip(&sharp)
                .all(|(a, b)| (a - b).abs() < 1e-3)
        );
    }

    #[test]
    fn a_partly_defocused_layer_contributes_only_where_it_is_sharp() {
        // A short pass: in focus on the left, blurred on the right.
        let base = |x: f32, y: f32| 400.0 * texture(x, y) + 40.0 * noise(x, y, 9).signum();
        let anchor = group(|x, y| base(x, y) + 15.0 * noise(x, y, 1));
        let sharp_layer: Vec<f32> = (0..W * H)
            .map(|i| {
                let (x, y) = ((i % W) as f32, (i / W) as f32);
                0.7 * (base(x, y) + 15.0 * noise(x, y, 2))
            })
            .collect();
        let blurred = gaussian_blur(&sharp_layer, W, H, 2.5);
        let mixed: Vec<f32> = (0..W * H)
            .map(|i| {
                if i % W < W / 2 {
                    sharp_layer[i]
                } else {
                    blurred[i]
                }
            })
            .collect();
        let mut layer = anchor.clone();
        layer.planes = std::array::from_fn(|_| mixed.clone());
        let (fused, report) = fuse(&[anchor.clone(), layer], &[], W, H);
        let l = &report.layers[0];
        assert_eq!(l.outcome, "superposed", "{report:?}");
        let fraction = l.sharp_fraction.unwrap();
        assert!(fraction > 0.25 && fraction < 0.75, "{report:?}");
        // Right half keeps the anchor's fine detail.
        let fine = |plane: &[f32], x0: usize, x1: usize| {
            let band = gaussian_blur(plane, W, H, 0.7);
            let coarse = gaussian_blur(plane, W, H, 1.4);
            let mut sum = 0.0f64;
            for y in 32..H - 32 {
                for x in x0..x1 {
                    sum += f64::from((band[y * W + x] - coarse[y * W + x]).abs());
                }
            }
            sum
        };
        let kept =
            fine(&fused[0], W / 2 + 48, W - 32) / fine(&anchor.planes[0], W / 2 + 48, W - 32);
        assert!(kept > 0.9, "blurred half softened the result: {kept}");
        // Left half averages noise.
        let rms = |values: &[f32]| {
            let mut sum = 0.0f64;
            let mut count = 0;
            for y in 32..H - 32 {
                for x in 32..W / 2 - 48 {
                    let e = values[y * W + x] - base(x as f32, y as f32);
                    sum += f64::from(e * e);
                    count += 1;
                }
            }
            (sum / f64::from(count)).sqrt()
        };
        let (before, after) = (rms(&anchor.planes[0]), rms(&fused[0]));
        assert!(after < 0.85 * before, "noise {before} -> {after}");
    }

    #[test]
    fn superposition_averages_noise_and_keeps_anchor_highlights() {
        let base = |x, y| 400.0 * texture(x, y);
        let anchor = group(|x, y| base(x, y) + 20.0 * noise(x, y, 1));
        let layer = group(|x, y| 0.5 * (base(x, y) + 20.0 * noise(x, y, 2)));
        let (fused, report) = fuse(&[anchor.clone(), layer], &[], W, H);
        assert_eq!(report.superposed, 2, "{report:?}");
        let rms = |values: &[f32]| {
            let mut sum = 0.0f64;
            let mut count = 0;
            for y in 32..H - 32 {
                for x in 32..W - 32 {
                    let e = values[y * W + x] - base(x as f32, y as f32);
                    sum += f64::from(e * e);
                    count += 1;
                }
            }
            (sum / f64::from(count)).sqrt()
        };
        let (before, after) = (rms(&anchor.planes[0]), rms(&fused[0]));
        assert!(after < 0.8 * before, "noise {before} -> {after}");
        // A clipped anchor specular stays exactly the anchor's.
        let mut anchor = group(base);
        let mut layer = group(|x, y| 0.5 * base(x, y));
        for y in 90..100 {
            for x in 120..130 {
                anchor.planes.iter_mut().for_each(|p| p[y * W + x] = 4000.0);
                layer.planes.iter_mut().for_each(|p| p[y * W + x] = 100.0);
            }
        }
        let (fused, _) = fuse(&[anchor, layer], &[], W, H);
        assert_eq!(fused[0][95 * W + 125], 4000.0);
    }

    #[test]
    fn a_pose_layer_averages_where_it_matches_and_never_ghosts() {
        let base = |x: f32, y: f32| 400.0 * texture(x, y);
        // A limb (bright blob) present only in the moved pass, which is
        // also displaced by (2.0, 1.0) px and darker overall.
        let blob = |x: f32, y: f32| {
            let r2 = (x - 170.0).powi(2) + (y - 90.0).powi(2);
            if r2 < 18.0 * 18.0 { 600.0 } else { 0.0 }
        };
        let anchor = group(|x, y| base(x, y) + 20.0 * noise(x, y, 1));
        let layer =
            group(|x, y| 0.8 * (base(x - 1.0, y - 2.0) + blob(x, y) + 20.0 * noise(x, y, 2)));
        let kinds = [LayerKind::Lighting, LayerKind::Pose];
        let (fused, report) = fuse(&[anchor.clone(), layer.clone()], &kinds, W, H);
        let pose = &report.layers[0];
        assert_eq!(pose.outcome, "superposed", "{report:?}");
        let agreement = pose.agreement.expect("pose agreement");
        assert!(agreement > 0.7 && agreement < 0.99, "{report:?}");
        // No ghost of the blob.
        let mut ghost = 0.0f32;
        for y in 76..104 {
            for x in 156..184 {
                let i = y * W + x;
                ghost =
                    ghost.max((fused[0][i] - anchor.planes[0][i]).abs() / base(x as f32, y as f32));
            }
        }
        assert!(ghost < 0.15, "moved structure ghosted: {ghost}");
        // Elsewhere the noise averages.
        let rms = |values: &[f32]| {
            let mut sum = 0.0f64;
            let mut count = 0;
            for y in 24..64 {
                for x in 24..120 {
                    let e = values[y * W + x] - base(x as f32, y as f32);
                    sum += f64::from(e * e);
                    count += 1;
                }
            }
            (sum / f64::from(count)).sqrt()
        };
        let (before, after) = (rms(&anchor.planes[0]), rms(&fused[0]));
        assert!(after < 0.85 * before, "noise {before} -> {after}");
    }
}

/// Offline placement of a detached layer: `STREHL_DETACHED_ANCHOR` (a dump
/// whose group 0 is the anchor) and `STREHL_DETACHED_LAYER` (a one-group dump).
#[cfg(test)]
#[test]
#[ignore = "needs lighting-fusion dumps"]
fn detached_placement_from_dump() {
    let anchor = std::env::var_os("STREHL_DETACHED_ANCHOR").expect("STREHL_DETACHED_ANCHOR");
    let layer = std::env::var_os("STREHL_DETACHED_LAYER").expect("STREHL_DETACHED_LAYER");
    let (anchor, _, w, h) = load_dump(std::path::Path::new(&anchor)).unwrap();
    let (layer, _, lw, lh) = load_dump(std::path::Path::new(&layer)).unwrap();
    let started = std::time::Instant::now();
    let (placed, report) = place_detached(&anchor[0], &layer[0], lw, lh, w, h);
    eprintln!(
        "{report:?} in {:.1} s; covered {}",
        started.elapsed().as_secs_f64(),
        placed.map_or(0, |p| p.valid.iter().filter(|&&v| v).count())
    );
}

/// Offline study of a [`dump`]: `STREHL_LIGHTING_DUMP_IN` (input) and
/// `STREHL_LIGHTING_DUMP_OUT` (fused planes, dump format).
#[cfg(test)]
#[test]
#[ignore = "needs a lighting-fusion dump"]
fn lighting_fusion_from_dump() {
    let input = std::env::var_os("STREHL_LIGHTING_DUMP_IN").expect("STREHL_LIGHTING_DUMP_IN");
    let output = std::env::var_os("STREHL_LIGHTING_DUMP_OUT").expect("STREHL_LIGHTING_DUMP_OUT");
    let (groups, kinds, width, height) = load_dump(std::path::Path::new(&input)).unwrap();
    let started = std::time::Instant::now();
    let (planes, report) = fuse(&groups, &kinds, width, height);
    eprintln!("fused in {:.1} s", started.elapsed().as_secs_f64());
    eprintln!("{}", serde_json::to_string_pretty(&report).unwrap());
    let fused = GroupPlanes {
        planes,
        valid: vec![true; width * height],
        ceiling: groups[0].ceiling,
    };
    dump(&[fused], &[], width, height, std::path::Path::new(&output)).unwrap();
}
