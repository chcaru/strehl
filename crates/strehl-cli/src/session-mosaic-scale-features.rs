//! Scale-space feature nominations, implemented from the published equations in
//! Lowe, IJCV 2004: https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf . No external
//! implementation is incorporated. These are diagnostic geometry features, not
//! a merge selector or a final-pixel image. Native and held-out tests still decide
//! whether a correspondence can authorize a join.

use super::{Feature, MosaicGeometryConfig, MosaicGuide, gradient};
use rayon::prelude::*;

const INTERVALS: usize = 3;
const BASE_SIGMA: f32 = 1.6;
const CONTRAST: f32 = 0.01;
const EDGE_RATIO: f32 = 10.0;

fn blur(input: &[f32], width: usize, height: usize, sigma: f32) -> Vec<f32> {
    let radius = (3.0 * sigma).ceil() as isize;
    let mut kernel: Vec<f32> = (-radius..=radius)
        .map(|x| (-(x * x) as f32 / (2.0 * sigma * sigma)).exp())
        .collect();
    let sum = kernel.iter().sum::<f32>();
    for value in &mut kernel {
        *value /= sum;
    }
    let mut scratch = vec![0.0; input.len()];
    let mut output = vec![0.0; input.len()];
    scratch
        .par_chunks_mut(width)
        .enumerate()
        .for_each(|(y, row)| {
            for (x, value) in row.iter_mut().enumerate() {
                *value = kernel
                    .iter()
                    .enumerate()
                    .map(|(k, &w)| {
                        let sx = (x as isize + k as isize - radius).clamp(0, width as isize - 1)
                            as usize;
                        w * input[y * width + sx]
                    })
                    .sum();
            }
        });
    output
        .par_chunks_mut(width)
        .enumerate()
        .for_each(|(y, row)| {
            for (x, value) in row.iter_mut().enumerate() {
                *value = kernel
                    .iter()
                    .enumerate()
                    .map(|(k, &w)| {
                        let sy = (y as isize + k as isize - radius).clamp(0, height as isize - 1)
                            as usize;
                        w * scratch[sy * width + x]
                    })
                    .sum();
            }
        });
    output
}

#[derive(Clone, Copy)]
struct Peak {
    x: f32,
    y: f32,
    level: usize,
    sigma: f32,
    response: f32,
}

fn solve3(mut h: [[f32; 3]; 3], mut rhs: [f32; 3]) -> Option<[f32; 3]> {
    for c in 0..3 {
        let pivot = (c..3).max_by(|&a, &b| h[a][c].abs().total_cmp(&h[b][c].abs()))?;
        if h[pivot][c].abs() < 1e-12 {
            return None;
        }
        h.swap(c, pivot);
        rhs.swap(c, pivot);
        let divisor = h[c][c];
        for value in &mut h[c][c..] {
            *value /= divisor;
        }
        rhs[c] /= divisor;
        for row in 0..3 {
            if row == c {
                continue;
            }
            let scale = h[row][c];
            let pivot = h[c];
            for (value, &reference) in h[row][c..].iter_mut().zip(&pivot[c..]) {
                *value -= scale * reference;
            }
            rhs[row] -= scale * rhs[c];
        }
    }
    rhs.into_iter().all(f32::is_finite).then_some(rhs)
}

fn locate(dog: &[Vec<f32>], w: usize, h: usize, level: usize, x: usize, y: usize) -> Option<Peak> {
    let (mut x, mut y, mut s) = (x as isize, y as isize, level as isize);
    for _ in 0..5 {
        if x < 2
            || y < 2
            || x >= w as isize - 2
            || y >= h as isize - 2
            || s < 1
            || s > INTERVALS as isize
        {
            return None;
        }
        let v = |dx: isize, dy: isize, ds: isize| {
            dog[(s + ds) as usize][(y + dy) as usize * w + (x + dx) as usize]
        };
        let value = v(0, 0, 0);
        let gradient = [
            (v(1, 0, 0) - v(-1, 0, 0)) * 0.5,
            (v(0, 1, 0) - v(0, -1, 0)) * 0.5,
            (v(0, 0, 1) - v(0, 0, -1)) * 0.5,
        ];
        let xx = v(1, 0, 0) + v(-1, 0, 0) - 2.0 * value;
        let yy = v(0, 1, 0) + v(0, -1, 0) - 2.0 * value;
        let ss = v(0, 0, 1) + v(0, 0, -1) - 2.0 * value;
        let xy = (v(1, 1, 0) - v(1, -1, 0) - v(-1, 1, 0) + v(-1, -1, 0)) * 0.25;
        let xs = (v(1, 0, 1) - v(1, 0, -1) - v(-1, 0, 1) + v(-1, 0, -1)) * 0.25;
        let ys = (v(0, 1, 1) - v(0, 1, -1) - v(0, -1, 1) + v(0, -1, -1)) * 0.25;
        let offset = solve3(
            [[xx, xy, xs], [xy, yy, ys], [xs, ys, ss]],
            gradient.map(|v| -v),
        )?;
        if offset.into_iter().any(|v| v.abs() > 2.0) {
            return None;
        }
        if offset.into_iter().all(|v| v.abs() < 0.5) {
            let contrast =
                value + 0.5 * gradient.iter().zip(offset).map(|(a, b)| a * b).sum::<f32>();
            let det = xx * yy - xy * xy;
            if contrast.abs() < CONTRAST / INTERVALS as f32
                || det <= 0.0
                || (xx + yy).powi(2) / det >= (EDGE_RATIO + 1.0).powi(2) / EDGE_RATIO
            {
                return None;
            }
            return Some(Peak {
                x: x as f32 + offset[0],
                y: y as f32 + offset[1],
                level: s as usize,
                sigma: BASE_SIGMA * 2.0_f32.powf((s as f32 + offset[2]) / INTERVALS as f32),
                response: contrast.abs(),
            });
        }
        x += offset[0].round() as isize;
        y += offset[1].round() as isize;
        s += offset[2].round() as isize;
    }
    None
}

fn orientations(values: &[f32], valid: &[bool], w: usize, h: usize, p: Peak) -> Vec<f32> {
    let sigma = 1.5 * p.sigma;
    let radius = (3.0 * sigma).round() as isize;
    let mut histogram = [0.0_f32; 36];
    for dy in -radius..=radius {
        for dx in -radius..=radius {
            let Some([gx, gy]) = gradient(values, valid, w, h, p.x + dx as f32, p.y + dy as f32)
            else {
                return Vec::new();
            };
            let bin = gy.atan2(gx).rem_euclid(std::f32::consts::TAU) * 36.0 / std::f32::consts::TAU;
            let weight = gx.hypot(gy) * (-(dx * dx + dy * dy) as f32 / (2.0 * sigma * sigma)).exp();
            let i = bin.floor() as usize % 36;
            histogram[i] += weight * (1.0 - bin.fract());
            histogram[(i + 1) % 36] += weight * bin.fract();
        }
    }
    for _ in 0..6 {
        let old = histogram;
        for i in 0..36 {
            histogram[i] = (old[(i + 35) % 36] + old[i] + old[(i + 1) % 36]) / 3.0;
        }
    }
    let peak = histogram.iter().copied().fold(0.0_f32, f32::max);
    let mut out = Vec::new();
    for i in 0..36 {
        let (left, center, right) = (
            histogram[(i + 35) % 36],
            histogram[i],
            histogram[(i + 1) % 36],
        );
        if center > 0.0 && center >= 0.8 * peak && center > left && center > right {
            let offset = 0.5 * (left - right) / (left - 2.0 * center + right);
            out.push((i as f32 + offset) * std::f32::consts::TAU / 36.0);
        }
    }
    out
}

fn descriptor(
    values: &[f32],
    valid: &[bool],
    w: usize,
    h: usize,
    p: Peak,
    angle: f32,
) -> Option<[f32; 128]> {
    let cell = 3.0 * p.sigma;
    let radius = (cell * 2.5 * std::f32::consts::SQRT_2).ceil() as isize;
    let (sin, cos) = angle.sin_cos();
    let mut out = [0.0_f32; 128];
    for dy in -radius..=radius {
        for dx in -radius..=radius {
            let u = (cos * dx as f32 + sin * dy as f32) / cell;
            let v = (-sin * dx as f32 + cos * dy as f32) / cell;
            let (bx, by) = (u + 1.5, v + 1.5);
            if bx <= -1.0 || bx >= 4.0 || by <= -1.0 || by >= 4.0 {
                continue;
            }
            let [gx, gy] = gradient(values, valid, w, h, p.x + dx as f32, p.y + dy as f32)?;
            let theta = (gy.atan2(gx) - angle).rem_euclid(std::f32::consts::TAU) * 8.0
                / std::f32::consts::TAU;
            let magnitude = gx.hypot(gy) * (-(u * u + v * v) / 8.0).exp();
            for yy in [by.floor() as isize, by.floor() as isize + 1] {
                for xx in [bx.floor() as isize, bx.floor() as isize + 1] {
                    if !(0..4).contains(&xx) || !(0..4).contains(&yy) {
                        continue;
                    }
                    let spatial = (1.0 - (bx - xx as f32).abs()) * (1.0 - (by - yy as f32).abs());
                    let base = (yy as usize * 4 + xx as usize) * 8;
                    let bin = theta.floor() as usize % 8;
                    out[base + bin] += magnitude * spatial * (1.0 - theta.fract());
                    out[base + (bin + 1) % 8] += magnitude * spatial * theta.fract();
                }
            }
        }
    }
    let norm = out.iter().map(|v| v * v).sum::<f32>().sqrt();
    if norm <= 1e-10 {
        return None;
    }
    for v in &mut out {
        *v = (*v / norm).min(0.2);
    }
    let norm = out.iter().map(|v| v * v).sum::<f32>().sqrt();
    for v in &mut out {
        *v /= norm;
    }
    Some(out)
}

pub(super) fn features(
    guide: &MosaicGuide,
    config: &MosaicGeometryConfig,
    reserve_blocks: bool,
) -> Vec<Feature> {
    if !reserve_blocks {
        return features_on_mask(guide, config, &guide.covered, false);
    }
    let mut output = Vec::new();
    for heldout in [false, true] {
        if heldout && config.role_plan.is_some() {
            continue; // Stage-two validation has fixed native sites, not descriptors.
        }
        let mask: Vec<_> = guide
            .covered
            .iter()
            .enumerate()
            .map(|(i, &covered)| {
                covered
                    && config
                        .spatial_role(
                            guide,
                            [
                                (i % guide.geometry.width) as f64,
                                (i / guide.geometry.width) as f64,
                            ],
                            0.5,
                        )
                        .is_some_and(|(_, role)| role == heldout)
            })
            .collect();
        let mut separate = config.clone();
        separate.maximum_features = if config.role_plan.is_some() {
            config.maximum_features
        } else {
            role_quota(config.maximum_features, heldout)
        };
        output.extend(features_on_mask(guide, &separate, &mask, true));
    }
    output
}

pub(super) fn role_quota(maximum: usize, heldout: bool) -> usize {
    if heldout {
        maximum / 3
    } else {
        maximum - maximum / 3
    }
}

/// Masking occurs before normalization and every global detector quota. Thus
/// pixels in the other role cannot alter contrast, peak competition or order.
pub(super) fn features_on_mask(
    guide: &MosaicGuide,
    config: &MosaicGeometryConfig,
    covered: &[bool],
    reserve_blocks: bool,
) -> Vec<Feature> {
    assert_eq!(covered.len(), guide.intensity.len());
    let mut base = guide.intensity.clone();
    let low = base
        .iter()
        .zip(covered)
        .filter(|(_, v)| **v)
        .map(|(x, _)| *x)
        .fold(f32::INFINITY, f32::min);
    let high = base
        .iter()
        .zip(covered)
        .filter(|(_, v)| **v)
        .map(|(x, _)| *x)
        .fold(f32::NEG_INFINITY, f32::max);
    if !low.is_finite() || high - low <= 1e-8 {
        return Vec::new();
    }
    for value in &mut base {
        *value = (*value - low) / (high - low);
    }
    // Sample the first octave at half a guide pixel. This restores small
    // repeatable details; these diagnostic samples never become final pixels.
    let (mut w, mut h) = (2 * guide.geometry.width, 2 * guide.geometry.height);
    let mut doubled = vec![0.0_f32; w * h];
    let mut valid = vec![false; w * h];
    for y in 0..h {
        for x in 0..w {
            if let Some(value) = super::sample(
                &base,
                covered,
                guide.geometry.width,
                guide.geometry.height,
                x as f32 * 0.5,
                y as f32 * 0.5,
            ) {
                doubled[y * w + x] = value;
                valid[y * w + x] = true;
            }
        }
    }
    base = doubled;
    let initial_sigma = (BASE_SIGMA * BASE_SIGMA - 1.0).sqrt();
    base = blur(&base, w, h, initial_sigma);
    let mut inherited_support = f64::from((3.0 * initial_sigma).ceil()) * 0.5 + 1.0;
    let stride = guide.geometry.width + 1;
    let mut missing = vec![0_u32; stride * (guide.geometry.height + 1)];
    for y in 0..guide.geometry.height {
        let mut row = 0;
        for x in 0..guide.geometry.width {
            row += u32::from(!covered[y * guide.geometry.width + x]);
            missing[(y + 1) * stride + x + 1] = missing[y * stride + x + 1] + row;
        }
    }
    let mut all = Vec::new();
    for octave in 0..5 {
        if w < 48 || h < 48 {
            break;
        }
        let factor = 2.0_f64.powi(octave - 1);
        let mut gaussian = vec![base];
        let mut level_support = vec![inherited_support];
        for level in 1..INTERVALS + 3 {
            let previous = BASE_SIGMA * 2.0_f32.powf((level - 1) as f32 / INTERVALS as f32);
            let next = BASE_SIGMA * 2.0_f32.powf(level as f32 / INTERVALS as f32);
            let sigma = (next * next - previous * previous).sqrt();
            gaussian.push(blur(gaussian.last().expect("base"), w, h, sigma));
            level_support.push(
                level_support.last().expect("base support")
                    + f64::from((3.0 * sigma).ceil()) * factor,
            );
        }
        let dog: Vec<Vec<f32>> = gaussian
            .windows(2)
            .map(|v| v[1].iter().zip(&v[0]).map(|(a, b)| a - b).collect())
            .collect();
        let mut peaks = Vec::new();
        for level in 1..=INTERVALS {
            for y in 2..h - 2 {
                for x in 2..w - 2 {
                    let index = y * w + x;
                    let value = dog[level][index];
                    if !valid[index] || value.abs() < 0.5 * CONTRAST / INTERVALS as f32 {
                        continue;
                    }
                    let mut extreme = true;
                    'neighbors: for ds in -1_isize..=1 {
                        for dy in -1_isize..=1 {
                            for dx in -1_isize..=1 {
                                if dx == 0 && dy == 0 && ds == 0 {
                                    continue;
                                }
                                let other = dog[(level as isize + ds) as usize]
                                    [(y as isize + dy) as usize * w + (x as isize + dx) as usize];
                                if (value > 0.0 && other >= value)
                                    || (value < 0.0 && other <= value)
                                {
                                    extreme = false;
                                    break 'neighbors;
                                }
                            }
                        }
                    }
                    if extreme && let Some(peak) = locate(&dog, w, h, level, x, y) {
                        peaks.push(peak);
                    }
                }
            }
        }
        peaks.sort_by(|a, b| b.response.total_cmp(&a.response));
        peaks.truncate(config.maximum_features * 4);
        for peak in peaks {
            let point = [peak.x as f64 * factor, peak.y as f64 * factor];
            let bx = point[0].round() as usize;
            let by = point[1].round() as usize;
            if bx >= guide.geometry.width || by >= guide.geometry.height {
                continue;
            }
            let index = by * guide.geometry.width + bx;
            let Some(source) = guide.source_indices[index]
                .into_iter()
                .find(|&v| v != usize::MAX)
            else {
                continue;
            };
            // Reserve the complete descriptor plus Gaussian support, not merely
            // its centre. Training and held-out spatial evidence cannot overlap.
            let guard =
                ((f64::from((3.0 * peak.sigma * 2.5 * std::f32::consts::SQRT_2).ceil() + 2.0)
                    * factor
                    + level_support[peak.level])
                    .ceil() as usize)
                    .max(
                        (config.native_tile + config.native_search_radius as usize)
                            .div_ceil(guide.step),
                    );
            if bx < guard
                || by < guard
                || bx + guard >= guide.geometry.width
                || by + guard >= guide.geometry.height
            {
                continue;
            }
            let (x0, y0, x1, y1) = (bx - guard, by - guard, bx + guard + 1, by + guard + 1);
            if missing[y1 * stride + x1] + missing[y0 * stride + x0]
                != missing[y0 * stride + x1] + missing[y1 * stride + x0]
            {
                continue;
            }
            let block_size = config.holdout_block_guide_pixels;
            let (block, heldout) = if reserve_blocks {
                let Some(role) = config.spatial_role(guide, point, guard as f64) else {
                    continue;
                };
                role
            } else {
                let block = [bx / block_size, by / block_size];
                (block, (block[0] + block[1]).is_multiple_of(3))
            };
            for angle in orientations(&gaussian[peak.level], &valid, w, h, peak) {
                if let Some(descriptor) =
                    descriptor(&gaussian[peak.level], &valid, w, h, peak, angle)
                {
                    all.push((
                        peak.response,
                        Feature {
                            point,
                            descriptor,
                            response: peak.response,
                            source,
                            focus: guide.usable_focus[index]
                                .then_some([guide.focus_ordinal[index], guide.focus_width[index]]),
                            block,
                            heldout,
                            support_radius: guard as f64,
                        },
                    ));
                    if all.len() > config.maximum_features * 4 {
                        all.sort_by(|a, b| b.0.total_cmp(&a.0));
                        all.truncate(config.maximum_features * 2);
                    }
                }
            }
        }
        let (nw, nh) = (w / 2, h / 2);
        base = vec![0.0; nw * nh];
        let mut mask = vec![false; nw * nh];
        for y in 0..nh {
            for x in 0..nw {
                base[y * nw + x] = gaussian[INTERVALS][2 * y * w + 2 * x];
                mask[y * nw + x] = valid[2 * y * w + 2 * x];
            }
        }
        valid = mask;
        w = nw;
        h = nh;
        inherited_support = level_support[INTERVALS];
    }
    all.sort_by(|a, b| b.0.total_cmp(&a.0));
    let mut out: Vec<Feature> = Vec::new();
    for (_, feature) in all {
        // Keep alternate stable orientations at an identical localized point,
        // but suppress distinct nearby detector peaks before descriptor lookup.
        if out.iter().any(|other| {
            let d = super::distance_sq(feature.point, other.point);
            d > 0.01 && d < (config.feature_separation * config.feature_separation) as f64
        }) {
            continue;
        }
        out.push(feature);
        if out.len() == config.maximum_features {
            break;
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parallel_scale_space_preserves_feature_coordinates_descriptors_and_order() {
        let guide = super::super::tests::guide(0, 714, [0, 0], false);
        let config = MosaicGeometryConfig::default();
        let run = |workers| {
            rayon::ThreadPoolBuilder::new()
                .num_threads(workers)
                .build()
                .unwrap()
                .install(|| features(&guide, &config, true))
        };
        let one = run(1);
        let four = run(4);
        assert!(
            one.len() >= 8,
            "positive texture must yield useful nominations"
        );
        assert_eq!(one.len(), four.len());
        for (a, b) in one.iter().zip(&four) {
            assert_eq!(a.point.map(f64::to_bits), b.point.map(f64::to_bits));
            assert_eq!(
                a.descriptor.map(f32::to_bits),
                b.descriptor.map(f32::to_bits)
            );
            assert_eq!(
                (a.source, a.block, a.heldout),
                (b.source, b.block, b.heldout)
            );
            assert_eq!(a.support_radius.to_bits(), b.support_radius.to_bits());
        }
    }
}
