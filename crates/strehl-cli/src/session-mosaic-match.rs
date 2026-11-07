//! Distributed, oriented gradient descriptors for coarse mosaic nomination.
//! This deliberately small matcher follows the published gradient-histogram
//! construction (Lowe, IJCV 2004), not any third-party implementation source.
//! Its matches are proposals until directly measured on native originals.

use super::{MosaicGeometryConfig, MosaicGuide};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MatchRole {
    Fit,
    Heldout,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CoarseCorrespondence {
    pub id: String,
    pub pass_a: usize,
    pub pass_b: usize,
    pub point_a_quad: [f64; 2],
    pub point_b_quad: [f64; 2],
    pub source_a: usize,
    pub source_b: usize,
    pub focus_a: Option<[f32; 2]>,
    pub focus_b: Option<[f32; 2]>,
    pub role: MatchRole,
    pub spatial_blocks: [[usize; 2]; 2],
    pub descriptor_distance: f32,
    pub seed_residual_quad: f64,
    pub within_seed_support: bool,
    /// Grid nominations require a coarse original-image NCC search before the
    /// unchanged native refinement. Neither kind is a geometry certificate.
    pub grid_nomination: bool,
    pub spatial_roles_match: bool,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PairDiscovery {
    pub pass_a: usize,
    pub pass_b: usize,
    pub features_a: usize,
    pub features_b: usize,
    pub reciprocal_matches: usize,
    pub directional_ratio_matches: [usize; 2],
    pub nomination: String,
    pub fit_inliers: usize,
    /// Centred full-native-quad similarity [real(a),imag(a),real(b),imag(b)].
    pub seed_a_to_b: Option<[f64; 4]>,
    /// A FIT-only acquisition-coordinate search model, never accepted geometry.
    #[serde(default)]
    pub ordinal_seed: Option<ordinal_seed::OrdinalSeed>,
    pub seed_fit_rms_quad: Option<f64>,
    pub seed_semantics: String,
    pub correspondences: Vec<CoarseCorrespondence>,
    pub refusal: Option<String>,
}
#[derive(Clone)]
pub(super) struct Feature {
    point: [f64; 2],
    descriptor: [f32; 128],
    response: f32,
    source: usize,
    focus: Option<[f32; 2]>,
    block: [usize; 2],
    heldout: bool,
    support_radius: f64,
}

#[path = "session-mosaic-ordinal-seed.rs"]
mod ordinal_seed;
#[path = "session-mosaic-scale-features.rs"]
mod scale_features;
#[path = "session-mosaic-source-features.rs"]
mod source_features;
pub use source_features::{
    SourceFeatureReceipt, discover_source_pairs, discover_source_pairs_cached,
};

fn sample(
    values: &[f32],
    valid: &[bool],
    width: usize,
    height: usize,
    x: f32,
    y: f32,
) -> Option<f32> {
    if x < 0.0 || y < 0.0 || x >= (width - 1) as f32 || y >= (height - 1) as f32 {
        return None;
    }
    let ix = x.floor() as usize;
    let iy = y.floor() as usize;
    let fx = x - ix as f32;
    let fy = y - iy as f32;
    let ids = [
        iy * width + ix,
        iy * width + ix + 1,
        (iy + 1) * width + ix,
        (iy + 1) * width + ix + 1,
    ];
    if !ids.into_iter().all(|id| valid[id]) {
        return None;
    }
    Some(
        (values[ids[0]] * (1.0 - fx) + values[ids[1]] * fx) * (1.0 - fy)
            + (values[ids[2]] * (1.0 - fx) + values[ids[3]] * fx) * fy,
    )
}
fn gradient(
    values: &[f32],
    valid: &[bool],
    width: usize,
    height: usize,
    x: f32,
    y: f32,
) -> Option<[f32; 2]> {
    Some([
        sample(values, valid, width, height, x + 1.0, y)?
            - sample(values, valid, width, height, x - 1.0, y)?,
        sample(values, valid, width, height, x, y + 1.0)?
            - sample(values, valid, width, height, x, y - 1.0)?,
    ])
}
#[cfg(test)]
fn descriptor(
    values: &[f32],
    valid: &[bool],
    width: usize,
    height: usize,
    x: usize,
    y: usize,
    radius: usize,
) -> Option<[f32; 128]> {
    let mut orientation = [0.0_f32; 36];
    let r = radius as i32;
    let sigma2 = (radius as f32 * 0.5).powi(2) * 2.0;
    for dy in -r..=r {
        for dx in -r..=r {
            if dx * dx + dy * dy > r * r {
                continue;
            }
            let [gx, gy] = gradient(
                values,
                valid,
                width,
                height,
                x as f32 + dx as f32,
                y as f32 + dy as f32,
            )?;
            let angle = gy.atan2(gx).rem_euclid(std::f32::consts::TAU);
            let bin = ((angle / std::f32::consts::TAU * 36.0) as usize).min(35);
            orientation[bin] += gx.hypot(gy) * (-(dx * dx + dy * dy) as f32 / sigma2).exp();
        }
    }
    let peak = orientation
        .iter()
        .enumerate()
        .max_by(|a, b| a.1.total_cmp(b.1))?
        .0;
    if orientation[peak] <= 1e-8 {
        return None;
    }
    let angle = (peak as f32 + 0.5) * std::f32::consts::TAU / 36.0;
    let (sin, cos) = angle.sin_cos();
    let mut result = [0.0_f32; 128];
    // A fixed descriptor lattice gives the same operation at each guide scale.
    for iy in 0..16 {
        for ix in 0..16 {
            let u = (ix as f32 + 0.5 - 8.0) * radius as f32 / 8.0;
            let v = (iy as f32 + 0.5 - 8.0) * radius as f32 / 8.0;
            let [gx, gy] = gradient(
                values,
                valid,
                width,
                height,
                x as f32 + cos * u - sin * v,
                y as f32 + sin * u + cos * v,
            )?;
            let theta = (gy.atan2(gx) - angle).rem_euclid(std::f32::consts::TAU)
                / std::f32::consts::TAU
                * 8.0;
            let bin = theta.floor() as usize % 8;
            let fraction = theta - theta.floor();
            let cell = (iy / 4 * 4 + ix / 4) * 8;
            let magnitude = gx.hypot(gy) * (-(u * u + v * v) / sigma2).exp();
            result[cell + bin] += magnitude * (1.0 - fraction);
            result[cell + (bin + 1) % 8] += magnitude * fraction;
        }
    }
    let length = result.iter().map(|x| x * x).sum::<f32>().sqrt();
    if length <= 1e-8 {
        return None;
    }
    for value in &mut result {
        *value = (*value / length).min(0.2);
    }
    let length = result.iter().map(|x| x * x).sum::<f32>().sqrt();
    for value in &mut result {
        *value /= length;
    }
    Some(result)
}

#[cfg(test)]
fn fixed_scale_features(guide: &MosaicGuide, config: &MosaicGeometryConfig) -> Vec<Feature> {
    let mut candidates = Vec::new();
    let mut values = guide.intensity.clone();
    let mut valid = guide.covered.clone();
    let mut width = guide.geometry.width;
    let mut height = guide.geometry.height;
    for level in 0..3 {
        let factor = 1_usize << level;
        let margin = 2 * config.descriptor_radius + 3;
        if width <= 2 * margin || height <= 2 * margin {
            break;
        }
        let mut scores = vec![0.0_f32; width * height];
        for y in margin..height - margin {
            for x in margin..width - margin {
                let mut xx = 0.0;
                let mut xy = 0.0;
                let mut yy = 0.0;
                let mut good = true;
                for dy in -1..=1 {
                    for dx in -1..=1 {
                        if let Some([gx, gy]) = gradient(
                            &values,
                            &valid,
                            width,
                            height,
                            x as f32 + dx as f32,
                            y as f32 + dy as f32,
                        ) {
                            xx += gx * gx;
                            xy += gx * gy;
                            yy += gy * gy;
                        } else {
                            good = false;
                        }
                    }
                }
                if good {
                    scores[y * width + x] = (xx * yy - xy * xy - 0.04 * (xx + yy).powi(2)).max(0.0);
                }
            }
        }
        let mut peaks = Vec::new();
        for y in margin..height - margin {
            for x in margin..width - margin {
                let score = scores[y * width + x];
                if score <= 1e-10 {
                    continue;
                }
                if (-1..=1).all(|dy| {
                    (-1..=1).all(|dx| {
                        scores[(y as isize + dy) as usize * width + (x as isize + dx) as usize]
                            <= score
                    })
                }) {
                    peaks.push((score, x, y));
                }
            }
        }
        peaks.sort_by(|a, b| b.0.total_cmp(&a.0));
        for (score, x, y) in peaks.into_iter().take(config.maximum_features * 2) {
            let base = [
                x as f64 * factor as f64 + (factor - 1) as f64 * 0.5,
                y as f64 * factor as f64 + (factor - 1) as f64 * 0.5,
            ];
            let bx = base[0].round() as usize;
            let by = base[1].round() as usize;
            if bx >= guide.geometry.width || by >= guide.geometry.height {
                continue;
            }
            let index = by * guide.geometry.width + bx;
            let Some(source) = guide.source_indices[index]
                .into_iter()
                .find(|&x| x != usize::MAX)
            else {
                continue;
            };
            let block_size = config.holdout_block_guide_pixels;
            let block = [bx / block_size, by / block_size];
            let guard = (2 * config.descriptor_radius * factor).max(
                (config.native_tile + config.native_search_radius as usize).div_ceil(guide.step),
            );
            if guard * 2 >= block_size
                || bx % block_size < guard
                || by % block_size < guard
                || bx % block_size + guard >= block_size
                || by % block_size + guard >= block_size
            {
                continue;
            }
            if let Some(descriptor) = descriptor(
                &values,
                &valid,
                width,
                height,
                x,
                y,
                config.descriptor_radius,
            ) {
                let focus = guide.usable_focus[index]
                    .then_some([guide.focus_ordinal[index], guide.focus_width[index]]);
                candidates.push((
                    score,
                    Feature {
                        point: base,
                        descriptor,
                        response: score,
                        source,
                        focus,
                        block,
                        heldout: (block[0] + block[1]).is_multiple_of(3),
                        support_radius: guard as f64,
                    },
                ));
            }
        }
        let nw = width / 2;
        let nh = height / 2;
        let mut next = vec![0.0; nw * nh];
        let mut mask = vec![false; nw * nh];
        for y in 0..nh {
            for x in 0..nw {
                let ids = [
                    2 * y * width + 2 * x,
                    2 * y * width + 2 * x + 1,
                    (2 * y + 1) * width + 2 * x,
                    (2 * y + 1) * width + 2 * x + 1,
                ];
                next[y * nw + x] = ids.iter().map(|&i| values[i]).sum::<f32>() * 0.25;
                mask[y * nw + x] = ids.into_iter().all(|i| valid[i]);
            }
        }
        values = next;
        valid = mask;
        width = nw;
        height = nh;
    }
    candidates.sort_by(|a, b| b.0.total_cmp(&a.0));
    let mut selected: Vec<Feature> = Vec::new();
    let radius_sq = (config.feature_separation * config.feature_separation) as f64;
    for (_, feature) in candidates {
        if selected
            .iter()
            .any(|prior| distance_sq(prior.point, feature.point) < radius_sq)
        {
            continue;
        }
        selected.push(feature);
        if selected.len() == config.maximum_features {
            break;
        }
    }
    selected
}
fn distance_sq(a: [f64; 2], b: [f64; 2]) -> f64 {
    (a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2)
}

/// The complete finite footprint must stay in one spatial role. Boundaries
/// between two fit blocks do not separate observations and need no empty strip;
/// any fit/heldout boundary remains strictly excluded in both directions.
pub(super) fn reserved_role(
    point: [f64; 2],
    radius: f64,
    side: usize,
) -> Option<([usize; 2], bool)> {
    if side == 0
        || !radius.is_finite()
        || radius < 0.0
        || !point.into_iter().all(f64::is_finite)
        || point.into_iter().any(|v| v - radius < 0.0)
    {
        return None;
    }
    let block = point.map(|v| (v.floor() as usize) / side);
    let role = (block[0] + block[1]) % 3 == 0;
    let low = point.map(|v| ((v - radius).floor() as usize) / side);
    let high = point.map(|v| ((v + radius).ceil() as usize) / side);
    for y in low[1]..=high[1] {
        for x in low[0]..=high[0] {
            if ((x + y) % 3 == 0) != role {
                return None;
            }
        }
    }
    Some((block, role))
}
fn nearest(a: &[Feature], b: &[Feature], ratio: f32) -> Vec<Option<(usize, f32)>> {
    a.iter()
        .map(|feature| {
            let distances: Vec<_> = b
                .iter()
                .map(|other| {
                    if feature.heldout != other.heldout {
                        return f32::INFINITY;
                    }
                    feature
                        .descriptor
                        .iter()
                        .zip(other.descriptor)
                        .map(|(x, y)| (x - y).powi(2))
                        .sum::<f32>()
                })
                .collect();
            let (index, &distance) = distances
                .iter()
                .enumerate()
                .min_by(|a, b| a.1.total_cmp(b.1))?;
            let best = (index, distance);
            // Alternate orientations of one localized feature are one candidate,
            // not an independent second-nearest surface that defeats the ratio.
            let second = distances
                .iter()
                .enumerate()
                .filter(|(i, _)| distance_sq(b[*i].point, b[index].point) > 0.01)
                .map(|(_, d)| *d)
                .fold(f32::INFINITY, f32::min);
            (second.is_finite() && best.1 < ratio * ratio * second).then_some(best)
        })
        .collect()
}
fn predict(t: [f64; 4], p: [f64; 2]) -> [f64; 2] {
    [
        t[0] * p[0] - t[1] * p[1] + t[2],
        t[1] * p[0] + t[0] * p[1] + t[3],
    ]
}
pub(super) fn fit_similarity(points: &[([f64; 2], [f64; 2])]) -> Option<[f64; 4]> {
    if points.len() < 2 {
        return None;
    }
    let mut p = [0.0; 2];
    let mut q = [0.0; 2];
    for &(a, b) in points {
        for axis in 0..2 {
            p[axis] += a[axis];
            q[axis] += b[axis];
        }
    }
    for axis in 0..2 {
        p[axis] /= points.len() as f64;
        q[axis] /= points.len() as f64;
    }
    let mut real = 0.0;
    let mut imag = 0.0;
    let mut denominator = 0.0;
    for &(a, b) in points {
        let u = [a[0] - p[0], a[1] - p[1]];
        let v = [b[0] - q[0], b[1] - q[1]];
        real += u[0] * v[0] + u[1] * v[1];
        imag += u[0] * v[1] - u[1] * v[0];
        denominator += u[0] * u[0] + u[1] * u[1];
    }
    if denominator <= 1e-10 {
        return None;
    }
    real /= denominator;
    imag /= denominator;
    let scale = real.hypot(imag);
    if !(0.5..=2.0).contains(&scale) {
        return None;
    }
    Some([
        real,
        imag,
        q[0] - real * p[0] + imag * p[1],
        q[1] - imag * p[0] - real * p[1],
    ])
}

/// Spatial role is fixed before robust fitting. Held-out descriptors and native
/// measurements never enter the global seed or deformable fit.
pub fn discover_pairs(
    guides: &[MosaicGuide],
    config: &MosaicGeometryConfig,
    max_work_bytes: usize,
) -> Result<Vec<PairDiscovery>> {
    ensure!(
        config.role_work_bytes()? <= max_work_bytes,
        "frozen role plan exceeds feature budget"
    );
    config.validate()?;
    ensure!(guides.len() >= 2, "mosaic discovery needs two passes");
    let mut reserved = config.role_work_bytes()?;
    for (pass, guide) in guides.iter().enumerate() {
        guide.validate()?;
        ensure!(guide.pass == pass, "mosaic guide pass order differs");
        reserved = reserved
            .checked_add(
                guide
                    .geometry
                    .pixels()
                    .checked_mul(256)
                    .context("feature reservation overflow")?,
            )
            .and_then(|n| {
                config
                    .maximum_features
                    .checked_mul(4096)
                    .and_then(|m| n.checked_add(m))
            })
            .context("feature reservation overflow")?;
    }
    ensure!(
        reserved <= max_work_bytes,
        "mosaic feature discovery exceeds workspace budget"
    );
    let all: Vec<_> = guides
        .iter()
        .map(|guide| scale_features::features(guide, config, true))
        .collect();
    discover_features(
        guides,
        &all,
        config,
        "scale-space diagnostic composite guide",
    )
}

pub(super) fn discover_features(
    guides: &[MosaicGuide],
    all: &[Vec<Feature>],
    config: &MosaicGeometryConfig,
    nomination: &str,
) -> Result<Vec<PairDiscovery>> {
    ensure!(
        all.len() == guides.len(),
        "mosaic feature pass count differs"
    );
    let mut results = Vec::new();
    for a in 0..guides.len() {
        for b in a + 1..guides.len() {
            ensure!(
                guides[a].source_geometry == guides[b].source_geometry,
                "mosaic pass sensor geometry differs"
            );
            let ab = nearest(&all[a], &all[b], config.descriptor_ratio);
            let ba = nearest(&all[b], &all[a], config.descriptor_ratio);
            let directional_ratio_matches =
                [ab.iter().flatten().count(), ba.iter().flatten().count()];
            let mut matches = Vec::new();
            for (i, matched) in ab.into_iter().enumerate() {
                let Some((j, distance)) = matched else {
                    continue;
                };
                if ba[j].is_none_or(|(reverse, _)| reverse != i) {
                    continue;
                }
                let fa = &all[a][i];
                let fb = &all[b][j];
                matches.push(CoarseCorrespondence {
                    id: format!("p{a}-p{b}-f{i}-f{j}"),
                    pass_a: a,
                    pass_b: b,
                    point_a_quad: guides[a].full_point(fa.point),
                    point_b_quad: guides[b].full_point(fb.point),
                    source_a: fa.source,
                    source_b: fb.source,
                    focus_a: fa.focus,
                    focus_b: fb.focus,
                    role: if fa.heldout || fb.heldout {
                        MatchRole::Heldout
                    } else {
                        MatchRole::Fit
                    },
                    spatial_blocks: [fa.block, fb.block],
                    descriptor_distance: distance.sqrt(),
                    seed_residual_quad: 0.0,
                    within_seed_support: false,
                    grid_nomination: false,
                    spatial_roles_match: fa.heldout == fb.heldout,
                });
            }
            // Alternate orientations can nominate the same physical point. A
            // duplicate must not inflate seed consensus or native edge counts.
            matches.sort_by(|a, b| a.descriptor_distance.total_cmp(&b.descriptor_distance));
            let mut distinct: Vec<CoarseCorrespondence> = Vec::new();
            for candidate in matches {
                if !distinct.iter().any(|p| {
                    distance_sq(p.point_a_quad, candidate.point_a_quad) < 0.01
                        && distance_sq(p.point_b_quad, candidate.point_b_quad) < 0.01
                }) {
                    distinct.push(candidate);
                }
            }
            let mut matches = distinct;
            let fit: Vec<_> = matches
                .iter()
                .filter(|m| m.role == MatchRole::Fit)
                .map(|m| (m.point_a_quad, m.point_b_quad))
                .collect();
            let threshold =
                config.coarse_residual_guide_pixels * guides[a].step.max(guides[b].step) as f64;
            let mut best: Vec<usize> = Vec::new();
            if fit.len() >= 2 {
                let mut state = 0x923e_31c7_5a41_791d_u64;
                for _ in 0..1024 {
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let i = (state >> 32) as usize % fit.len();
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let j = (state >> 32) as usize % fit.len();
                    if i == j || distance_sq(fit[i].0, fit[j].0) < 16.0 * threshold * threshold {
                        continue;
                    }
                    let Some(model) = fit_similarity(&[fit[i], fit[j]]) else {
                        continue;
                    };
                    let consensus: Vec<_> = fit
                        .iter()
                        .enumerate()
                        .filter_map(|(k, &(p, q))| {
                            (distance_sq(predict(model, p), q) <= threshold * threshold)
                                .then_some(k)
                        })
                        .collect();
                    if consensus.len() > best.len() {
                        best = consensus;
                    }
                }
            }
            let mut seed = None;
            let mut rms = None;
            let ordinal = ordinal_seed::nominate(
                &matches,
                threshold.min(super::native::coarse_search_radius_quad() * 0.5),
            );
            let ordinal = ordinal.filter(|model| model.fit_ids.len() > best.len());
            let mut fit_inliers = best.len();
            let refusal = if let Some(model) = &ordinal {
                fit_inliers = model.fit_ids.len();
                rms = Some(model.fit_rms_quad);
                let midpoint = model.source_interval[0]
                    + (model.source_interval[1] - model.source_interval[0]) / 2;
                seed = Some(model.centred(midpoint, guides[a].source_geometry));
                for correspondence in &mut matches {
                    correspondence.seed_residual_quad = distance_sq(
                        model.predict(correspondence.point_a_quad, correspondence.source_a),
                        correspondence.point_b_quad,
                    )
                    .sqrt();
                    correspondence.within_seed_support = model.supports(correspondence.source_a)
                        && correspondence.seed_residual_quad <= model.nomination_envelope_quad;
                }
                None
            } else if best.len() < 3 {
                Some("fewer than three coherent fit-role descriptor seed nominations".into())
            } else {
                let points: Vec<_> = best.iter().map(|&i| fit[i]).collect();
                if let Some(model) = fit_similarity(&points) {
                    rms = Some(
                        (points
                            .iter()
                            .map(|&(p, q)| distance_sq(predict(model, p), q))
                            .sum::<f64>()
                            / points.len() as f64)
                            .sqrt(),
                    );
                    for correspondence in &mut matches {
                        correspondence.seed_residual_quad = distance_sq(
                            predict(model, correspondence.point_a_quad),
                            correspondence.point_b_quad,
                        )
                        .sqrt();
                        correspondence.within_seed_support =
                            correspondence.seed_residual_quad <= threshold * 4.0;
                    }
                    let centre = [
                        guides[a].source_geometry.width as f64 * 0.5,
                        guides[a].source_geometry.height as f64 * 0.5,
                    ];
                    seed = Some([
                        model[0],
                        model[1],
                        model[2] + model[0] * centre[0] - model[1] * centre[1] - centre[0],
                        model[3] + model[1] * centre[0] + model[0] * centre[1] - centre[1],
                    ]);
                    None
                } else {
                    Some("singular guide similarity".into())
                }
            };
            results.push(PairDiscovery {
                pass_a: a,
                pass_b: b,
                features_a: all[a].len(),
                features_b: all[b].len(),
                reciprocal_matches: matches.len(),
                directional_ratio_matches,
                nomination: nomination.to_owned(),
                fit_inliers,
                seed_a_to_b: seed,
                ordinal_seed: ordinal,
                seed_fit_rms_quad: rms,
                seed_semantics: format!("Unverified search nomination only. A measured pass edge still requires at least {} accepted native fit correspondences; held-out geometry and reciprocal loops are checked independently.",config.minimum_pair_matches),
                correspondences: matches,
                refusal,
            });
        }
    }
    Ok(results)
}

use anyhow::Context;

#[cfg(test)]
#[path = "session-mosaic-match-tests.rs"]
pub(crate) mod tests;
