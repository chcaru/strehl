//! Stream original-image feature descriptions into each pass's coordinate gauge.
//! A focus composite may contain selector terraces. It supplies support and
//! source nominations, but it does not supply these descriptor intensities.

use super::{Feature, discover_features, scale_features};
use crate::session_cache::SourceCache;
use crate::session_input::{ResolvedSession, SourceIdentity};
use crate::session_mosaic_geometry::{
    GuideReceipt, MosaicGeometryConfig, MosaicGuide, PairDiscovery,
};
use anyhow::{Context, Result, ensure};
use serde::Serialize;
use strehl_core::align::Similarity;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::warpmap::WarpMap;
#[path = "session-mosaic-source-selection.rs"]
mod selection;

/// Bounded acquisition nominations, not a subsampling of final image inputs.
const MAX_SOURCE_GUIDES: usize = 128;

#[derive(Serialize)]
pub struct FeatureWitness {
    pub index: usize,
    pub point_quad: [f64; 2],
    pub source: usize,
    pub focus: Option<[f32; 2]>,
    pub heldout: bool,
    pub spatial_block: [usize; 2],
    pub support_radius_quad: f64,
    pub response: f32,
}

fn witness_metadata(anchor: &MosaicGuide, features: &[Feature]) -> Vec<FeatureWitness> {
    features
        .iter()
        .enumerate()
        .map(|(index, feature)| FeatureWitness {
            index,
            point_quad: anchor.full_point(feature.point),
            source: feature.source,
            focus: feature.focus,
            heldout: feature.heldout,
            spatial_block: feature.block,
            support_radius_quad: feature.support_radius * anchor.step as f64,
            response: feature.response,
        })
        .collect()
}

#[derive(Serialize)]
pub struct SourceFeatureReceipt {
    pub pass: usize,
    pub source_features: Vec<(usize, usize, usize)>,
    pub retained_features: usize,
    /// Bounded original-source nomination witnesses, never aligned output pixels.
    pub feature_witnesses: Vec<FeatureWitness>,
    pub maximum_source_guides: usize,
    pub reserved_bytes: usize,
    pub nominations: Vec<selection::Nomination>,
    pub nomination_coverage: selection::Coverage,
    pub semantics: &'static str,
}

#[cfg(test)]
fn nominated_sources(guide: &MosaicGuide, range: std::ops::Range<usize>) -> Result<Vec<usize>> {
    Ok(selection::select(guide, range, MAX_SOURCE_GUIDES)?
        .0
        .into_iter()
        .map(|n| n.source)
        .collect())
}

fn map_feature(
    feature: &mut Feature,
    source: &MosaicGuide,
    anchor: &MosaicGuide,
    warp: Similarity,
    config: &MosaicGeometryConfig,
) -> bool {
    let Some(inverse) = warp.invert() else {
        return false;
    };
    let p = source.full_point(feature.point);
    let (x, y) = inverse.apply_at(
        p[0],
        p[1],
        anchor.source_geometry.width as f64 * 0.5,
        anchor.source_geometry.height as f64 * 0.5,
    );
    let point = [
        (x - anchor.origin[0]) / anchor.step as f64,
        (y - anchor.origin[1]) / anchor.step as f64,
    ];
    if !point.into_iter().all(f64::is_finite)
        || point[0] < 0.0
        || point[1] < 0.0
        || point[0] >= anchor.geometry.width as f64
        || point[1] >= anchor.geometry.height as f64
    {
        return false;
    }
    // The finite dependency envelope is a square. Its rotated axis-aligned
    // radius uses the matrix row L1 norm, not the complex/radial magnitude.
    let radius =
        feature.support_radius * source.step as f64 * (inverse.a.re.abs() + inverse.a.im.abs())
            / anchor.step as f64;
    let (bx, by) = (point[0].round() as usize, point[1].round() as usize);
    if bx >= anchor.geometry.width || by >= anchor.geometry.height {
        return false;
    }
    let Some((block, heldout)) = config.spatial_role(anchor, point, radius) else {
        return false;
    };
    let index = by * anchor.geometry.width + bx;
    if !anchor.covered[index] {
        return false;
    }
    feature.point = point;
    feature.support_radius = radius;
    feature.block = block;
    feature.heldout = heldout;
    feature.focus = anchor.usable_focus[index]
        .then_some([anchor.focus_ordinal[index], anchor.focus_width[index]]);
    true
}

fn original_role_mask(
    source: &MosaicGuide,
    anchor: &MosaicGuide,
    warp: Similarity,
    heldout: bool,
    config: &MosaicGeometryConfig,
) -> Result<Vec<bool>> {
    let inverse = warp.invert().context("singular original feature gauge")?;
    let center = [
        anchor.source_geometry.width as f64 * 0.5,
        anchor.source_geometry.height as f64 * 0.5,
    ];
    let radius = (source.step - 1) as f64 * 0.5;
    Ok(source
        .covered
        .iter()
        .enumerate()
        .map(|(i, &covered)| {
            if !covered {
                return false;
            }
            let p = source.full_point([
                (i % source.geometry.width) as f64,
                (i / source.geometry.width) as f64,
            ]);
            let q = inverse.apply_at(p[0], p[1], center[0], center[1]);
            let point = [
                (q.0 - anchor.origin[0]) / anchor.step as f64,
                (q.1 - anchor.origin[1]) / anchor.step as f64,
            ];
            let guard = radius * (inverse.a.re.abs() + inverse.a.im.abs()) / anchor.step as f64;
            config
                .spatial_role(anchor, point, guard)
                .is_some_and(|(_, role)| role == heldout)
        })
        .collect())
}

fn retain_feature(pool: &mut Vec<Feature>, feature: Feature, maximum: usize) -> bool {
    if !feature.response.is_finite() || feature.response <= 0.0 {
        return false;
    }
    let nearby: Vec<_> = pool
        .iter()
        .enumerate()
        .filter(|(_, prior)| super::distance_sq(prior.point, feature.point) < 4.0)
        .map(|(i, _)| i)
        .collect();
    if let Some(&first) = nearby.first() {
        let strongest = nearby
            .iter()
            .map(|&i| pool[i].response)
            .fold(f32::NEG_INFINITY, f32::max);
        // A source chosen first for broad coverage must not suppress a stronger
        // localized original-image feature from a later acquisition. This is
        // descriptor nomination only; native evidence still certifies geometry.
        if feature.response > strongest {
            pool.retain(|prior| super::distance_sq(prior.point, feature.point) >= 4.0);
        } else {
            // Preserve alternate orientations of the same strongest peak.
            // `nearest` already treats these as one location for its ratio.
            let prior = &pool[first];
            if feature.response != strongest
                || feature.source != prior.source
                || super::distance_sq(prior.point, feature.point) > 0.01
                || nearby.len() >= 4
                || nearby
                    .iter()
                    .any(|&i| pool[i].descriptor == feature.descriptor)
            {
                return false;
            }
        }
    }
    if pool.len() >= maximum {
        return false;
    }
    pool.push(feature);
    true
}

#[allow(clippy::too_many_arguments)]
pub fn discover_source_pairs(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    guides: &[MosaicGuide],
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<(Vec<PairDiscovery>, Vec<SourceFeatureReceipt>)> {
    discover_source_pairs_impl(
        session, identities, maps, cache, guides, config, budget, false,
    )
}

/// Replay the production nominator while refusing every missing cache entry.
#[allow(clippy::too_many_arguments)]
pub fn discover_source_pairs_cached(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    guides: &[MosaicGuide],
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<(Vec<PairDiscovery>, Vec<SourceFeatureReceipt>)> {
    discover_source_pairs_impl(
        session, identities, maps, cache, guides, config, budget, true,
    )
}

#[allow(clippy::too_many_arguments)]
fn discover_source_pairs_impl(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    guides: &[MosaicGuide],
    config: &MosaicGeometryConfig,
    budget: usize,
    cached_only: bool,
) -> Result<(Vec<PairDiscovery>, Vec<SourceFeatureReceipt>)> {
    ensure!(
        config.role_work_bytes()? <= budget,
        "frozen role plan exceeds source feature budget"
    );
    config.validate()?;
    ensure!(
        session.len() == identities.len()
            && guides.len() == session.passes.len()
            && maps.len() == guides.len(),
        "mosaic source feature census differs"
    );
    let largest = guides
        .iter()
        .map(|g| g.geometry.pixels())
        .max()
        .context("missing mosaic guides")?;
    let reserved = largest
        .checked_mul(384)
        .and_then(|n| n.checked_add(config.maximum_features.checked_mul(16384)?))
        .and_then(|n| {
            n.checked_add(
                guides
                    .len()
                    .checked_mul(config.maximum_features)?
                    .checked_mul(1024)?,
            )
        })
        .and_then(|n| n.checked_add(config.role_work_bytes().ok()?))
        .context("mosaic source feature reservation overflow")?;
    ensure!(
        reserved <= budget,
        "mosaic source features exceed explicit memory budget"
    );
    let mut all = Vec::new();
    let mut reports = Vec::new();
    for (pass, anchor) in guides.iter().enumerate() {
        anchor.validate()?;
        ensure!(
            anchor.pass == pass
                && maps[pass].len() == session.len()
                && maps[pass].geometry() == anchor.source_geometry,
            "mosaic source feature gauge differs"
        );
        let (nominations, nomination_coverage) = selection::select(
            anchor,
            session.passes[pass].global_range.clone(),
            MAX_SOURCE_GUIDES,
        )?;
        let selected: Vec<_> = nominations.iter().map(|n| n.source).collect();
        let mut pooled_by_role: [Vec<Feature>; 2] = [Vec::new(), Vec::new()];
        let mut counts = Vec::new();
        for global in selected {
            let frame = &session.frames[global];
            let identity = &identities[global];
            identity.validate()?;
            ensure!(
                frame.path == identity.path
                    && frame.bytes == identity.bytes
                    && frame.modified_unix_nanos == identity.modified_unix_nanos,
                "mosaic feature original identity differs"
            );
            let warp = maps[pass].warps()[global]
                .placed()
                .context("mosaic feature source unplaced")?;
            let original = if cached_only {
                cache
                    .load(identity)?
                    .context("cached mosaic feature original missing; RAW decode prohibited")?
            } else {
                cache.load_or_decode(frame, identity)?
            };
            ensure!(
                original.geometry() == anchor.source_geometry,
                "mosaic feature source shape differs"
            );
            let geometry = PlaneGeometry {
                width: anchor.source_geometry.width / anchor.step,
                height: anchor.source_geometry.height / anchor.step,
            };
            let n = geometry.pixels();
            let (intensity, covered) = super::super::guide::original_boxes(
                original.as_ref(),
                original.levels(),
                anchor.step,
            );
            drop(original);
            let source = MosaicGuide {
                pass,
                source_geometry: anchor.source_geometry,
                geometry,
                origin: [(anchor.step - 1) as f64 * 0.5; 2],
                step: anchor.step,
                intensity,
                source_indices: covered
                    .iter()
                    .map(|&v| {
                        if v {
                            [global, usize::MAX, usize::MAX, usize::MAX]
                        } else {
                            [usize::MAX; 4]
                        }
                    })
                    .collect(),
                covered,
                focus_ordinal: vec![f32::NAN; n],
                focus_width: vec![f32::NAN; n],
                usable_focus: vec![false; n],
                receipt: GuideReceipt {
                    pass,
                    source_geometry: [anchor.source_geometry.width, anchor.source_geometry.height],
                    guide_geometry: [geometry.width, geometry.height],
                    origin_quad_pixels: [(anchor.step - 1) as f64 * 0.5; 2],
                    step_quad_pixels: anchor.step,
                    alignment_sha256: anchor.receipt.alignment_sha256.clone(),
                    focus_evidence_sha256: anchor.receipt.focus_evidence_sha256.clone(),
                    guide_sha256: identity.sha256.clone(),
                    covered_pixels: 0,
                    usable_focus_pixels: 0,
                    source_contributions: vec![(global, n)],
                    reserved_work_bytes: reserved,
                    construction: "single original CFA diagnostic box guide; never output pixels"
                        .into(),
                },
            };
            let mut detected = 0;
            let mut admitted = 0;
            for heldout in [false, true] {
                if heldout && config.role_plan.is_some() {
                    continue; // Held sites use only the plan's frozen native witnesses.
                }
                let mask = original_role_mask(&source, anchor, warp, heldout, config)?;
                let mut separate = config.clone();
                separate.maximum_features = if config.role_plan.is_some() {
                    config.maximum_features
                } else {
                    scale_features::role_quota(config.maximum_features, heldout)
                };
                let quota = (separate.maximum_features / nominations.len().max(1)).max(1);
                let features = scale_features::features_on_mask(&source, &separate, &mask, false);
                detected += features.len();
                let mut admitted_role = 0;
                for mut feature in features {
                    ensure!(
                        feature.source == global,
                        "mosaic descriptor witness changed"
                    );
                    if !map_feature(&mut feature, &source, anchor, warp, config)
                        || feature.heldout != heldout
                    {
                        continue;
                    }
                    // Roles have separate caps and competition. A changed
                    // heldout original cannot replace or crowd out a FIT peak.
                    if !retain_feature(
                        &mut pooled_by_role[usize::from(heldout)],
                        feature,
                        separate.maximum_features,
                    ) {
                        continue;
                    }
                    admitted += 1;
                    admitted_role += 1;
                    if admitted_role >= quota {
                        break;
                    }
                }
            }
            counts.push((global, detected, admitted));
        }
        let pooled: Vec<_> = pooled_by_role.into_iter().flatten().collect();
        reports.push(SourceFeatureReceipt{pass,source_features:counts,retained_features:pooled.len(),feature_witnesses:witness_metadata(anchor,&pooled),
            maximum_source_guides:MAX_SOURCE_GUIDES,reserved_bytes:reserved,nominations,nomination_coverage,
            semantics:"Original u16 CFA source guides streamed singly; role-isolated normalization, detection, quotas and nearest competitors; frozen spatial holdouts include original-box and descriptor support. Independence is conditional on bound per-pass alignment/focus/source nominations. Nominations cover qualified focus intervals before marginal spatial witness support, with128-source/2000-descriptor bounds; these are search proposals, not physical depth or merge weights. Native measurement still required."});
        all.push(pooled);
    }
    Ok((
        discover_features(
            guides,
            &all,
            config,
            "streamed original-CFA source feature pool",
        )?,
        reports,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::align::Cx;
    #[test]
    fn exported_original_feature_witness_preserves_gauge_role_source_and_memory_bound() {
        let mut guide = super::super::tests::guide(0, 714, [0, 0], false);
        guide.step = 4;
        guide.origin = [1.5, 1.5];
        let feature = Feature {
            point: [20.25, 30.5],
            descriptor: [0.0; 128],
            response: 9.0,
            source: 23,
            focus: Some([22.25, 2.5]),
            block: [1, 2],
            heldout: true,
            support_radius: 8.0,
        };
        let metadata = witness_metadata(&guide, &[feature]);
        assert_eq!(metadata[0].point_quad, [82.5, 123.5]);
        assert_eq!(metadata[0].source, 23);
        assert_eq!(metadata[0].support_radius_quad, 32.0);
        assert!(metadata[0].heldout);
        assert_eq!(metadata[0].spatial_block, [1, 2]);
        assert!(std::mem::size_of::<Feature>() + std::mem::size_of::<FeatureWitness>() <= 1024);
        let value = serde_json::to_value(&metadata).unwrap();
        assert_eq!(value[0]["source"], 23);
    }
    #[test]
    fn source_feature_pool_refuses_wrong_pass_original_witness() {
        let mut guide = super::super::tests::guide(0, 714, [0, 0], false);
        assert_eq!(nominated_sources(&guide, 0..3).unwrap(), vec![1]);
        guide.source_indices[1234][0] = 9;
        assert!(nominated_sources(&guide, 0..3).is_err());
    }

    #[test]
    fn transformed_original_role_mask_isolates_detection_and_box_boundary_taps() {
        let mut source = super::super::tests::guide(0, 714, [0, 0], false);
        let mut anchor = super::super::tests::guide(0, 714, [0, 0], false);
        for guide in [&mut source, &mut anchor] {
            guide.step = 4;
            guide.origin = [1.5; 2];
            guide.source_geometry.width *= 4;
            guide.source_geometry.height *= 4;
        }
        let warp = Similarity {
            a: Cx::new(1.13 * 0.11_f64.cos(), 1.13 * 0.11_f64.sin()),
            b: Cx::new(21.25, -7.5),
        };
        let config = MosaicGeometryConfig {
            maximum_features: 96,
            ..Default::default()
        };
        let mask = original_role_mask(&source, &anchor, warp, false, &config).unwrap();
        let clean = scale_features::features_on_mask(&source, &config, &mask, false);
        assert!(clean.len() >= 8);
        let inverse = warp.invert().unwrap();
        let boundary_rejections = mask
            .iter()
            .enumerate()
            .filter(|(i, allowed)| {
                if **allowed {
                    return false;
                }
                let p = source.full_point([
                    (*i % source.geometry.width) as f64,
                    (*i / source.geometry.width) as f64,
                ]);
                let q = inverse.apply_at(
                    p[0],
                    p[1],
                    anchor.source_geometry.width as f64 * 0.5,
                    anchor.source_geometry.height as f64 * 0.5,
                );
                super::super::reserved_role(
                    [(q.0 - 1.5) / 4.0, (q.1 - 1.5) / 4.0],
                    0.0,
                    config.holdout_block_guide_pixels,
                )
                .is_some_and(|(_, heldout)| !heldout)
            })
            .count();
        assert!(
            boundary_rejections > 0,
            "whole original boxes must reject some apparently safe centres"
        );
        for (i, allowed) in mask.iter().enumerate() {
            if !allowed {
                source.intensity[i] = ((i * 977) % 101) as f32 * 100_000.0;
            }
        }
        let poisoned = scale_features::features_on_mask(&source, &config, &mask, false);
        assert_eq!(
            super::super::tests::feature_bits(&clean),
            super::super::tests::feature_bits(&poisoned)
        );
        let mut admitted = 0;
        for mut feature in poisoned {
            if map_feature(&mut feature, &source, &anchor, warp, &config) {
                assert!(!feature.heldout);
                admitted += 1;
            }
        }
        assert!(admitted >= 8);
    }

    #[test]
    fn frozen_island_poison_isolated_in_both_mapped_original_feature_stages() {
        let (guides, stage_two) = super::super::tests::island_fixture();
        let mut views = guides.into_iter();
        let mut source = views.next().unwrap();
        let anchor = views.next().unwrap();
        // This is one pass's own original-to-anchor mapping; use the same pass
        // identity on both diagnostic objects rather than crossing pass gauges.
        source.pass = 1;
        source
            .source_indices
            .fill([4, usize::MAX, usize::MAX, usize::MAX]);
        let warp = Similarity {
            a: Cx::new(1.07 * 0.07_f64.cos(), 1.07 * 0.07_f64.sin()),
            b: Cx::new(17.25, -6.5),
        };
        let held = original_role_mask(&source, &anchor, warp, true, &stage_two).unwrap();
        assert!(held.iter().filter(|v| **v).count() > 1000);
        let mut stage_one = stage_two.clone();
        stage_one.role_plan = None;
        let mut baselines = Vec::new();
        for config in [&stage_one, &stage_two] {
            let mask = original_role_mask(&source, &anchor, warp, false, config).unwrap();
            assert!(!mask.iter().zip(&held).any(|(a, b)| *a && *b));
            let features = scale_features::features_on_mask(&source, config, &mask, false);
            assert!(features.len() >= 8);
            baselines.push((mask, super::super::tests::feature_bits(&features)));
        }
        for (i, held) in held.into_iter().enumerate() {
            if held {
                source.intensity[i] = ((i * 977) % 101) as f32 * 100_000.;
            }
        }
        for (config, (mask, expected)) in [&stage_one, &stage_two].into_iter().zip(baselines) {
            let features = scale_features::features_on_mask(&source, config, &mask, false);
            assert_eq!(expected, super::super::tests::feature_bits(&features));
            let admitted = features
                .into_iter()
                .filter_map(|mut feature| {
                    map_feature(&mut feature, &source, &anchor, warp, config).then_some(feature)
                })
                .collect::<Vec<_>>();
            assert!(admitted.len() >= 8);
            assert!(admitted.iter().all(|f| !f.heldout));
        }
    }

    #[test]
    fn source_feature_coordinates_and_holdout_footprint_use_pass_gauge() {
        let source = super::super::tests::guide(0, 714, [0, 0], false);
        let anchor = super::super::tests::guide(0, 714, [0, 0], false);
        let warp = Similarity {
            a: Cx::new(1.13 * 0.11_f64.cos(), 1.13 * 0.11_f64.sin()),
            b: Cx::new(21.25, -7.5),
        };
        let cfg = MosaicGeometryConfig::default();
        for (point, accepted) in [([192.0, 64.0], true), ([129.0, 64.0], false)] {
            let mapped = warp.apply_at(point[0], point[1], 192.0, 128.0);
            let mut feature = Feature {
                point: [mapped.0, mapped.1],
                descriptor: [0.0; 128],
                response: 1.0,
                source: 1,
                focus: None,
                block: [0, 0],
                heldout: false,
                support_radius: 8.0,
            };
            assert_eq!(
                map_feature(&mut feature, &source, &anchor, warp, &cfg),
                accepted
            );
            if accepted {
                assert!(super::super::distance_sq(feature.point, point) < 1e-12);
                assert_eq!(feature.block, [1, 0]);
                assert!(!feature.heldout);
                assert_eq!(feature.source, 1);
            }
        }
    }
    #[test]
    fn rotated_square_dependency_cannot_cross_holdout_boundary() {
        let guide = super::super::tests::guide(0, 714, [0, 0], false);
        let angle = std::f64::consts::FRAC_PI_4;
        let warp = Similarity {
            a: Cx::new(angle.cos(), angle.sin()),
            b: Cx::ZERO,
        };
        let mapped = warp.apply_at(138.0, 64.0, 192.0, 128.0);
        let mut feature = Feature {
            point: [mapped.0, mapped.1],
            descriptor: [0.0; 128],
            response: 1.0,
            source: 1,
            focus: None,
            block: [0, 0],
            heldout: false,
            support_radius: 8.0,
        };
        // Centre is 10 pixels from the block boundary: a radial radius of8
        // would accept, but the rotated square extends11.31 pixels and must fail.
        assert!(!map_feature(
            &mut feature,
            &guide,
            &guide,
            warp,
            &MosaicGeometryConfig::default()
        ));
    }
    #[test]
    fn source_pool_global_cap_survives_more_nominated_sources_than_capacity() {
        let mut pool = Vec::new();
        for source in 0..MAX_SOURCE_GUIDES {
            let feature = Feature {
                point: [160.0 + 4.0 * source as f64, 64.0],
                descriptor: [0.0; 128],
                response: 1.0,
                source,
                focus: None,
                block: [1, 0],
                heldout: false,
                support_radius: 8.0,
            };
            assert_eq!(retain_feature(&mut pool, feature, 8), source < 8);
        }
        assert_eq!(pool.len(), 8);
        assert_eq!(
            pool.iter().map(|f| f.source).collect::<Vec<_>>(),
            (0..8).collect::<Vec<_>>()
        );
    }

    #[test]
    fn strongest_original_witness_replaces_early_blur_and_retains_orientations() {
        let weak = Feature {
            point: [160.0, 64.0],
            descriptor: [0.1; 128],
            response: 0.02,
            source: 1,
            focus: None,
            block: [1, 0],
            heldout: false,
            support_radius: 8.0,
        };
        let mut strong = weak.clone();
        strong.response = 0.08;
        strong.source = 9;
        strong.descriptor.fill(0.2);
        let mut pool = Vec::new();
        assert!(retain_feature(&mut pool, weak.clone(), 2));
        assert!(retain_feature(&mut pool, strong.clone(), 2));
        assert_eq!(pool.len(), 1);
        assert_eq!(
            pool[0].source, 9,
            "first source must not win by insertion order"
        );
        let mut alternate = strong.clone();
        alternate.descriptor.fill(0.3);
        assert!(retain_feature(&mut pool, alternate.clone(), 2));
        assert!(!retain_feature(&mut pool, alternate, 2));
        assert!(!retain_feature(&mut pool, weak, 2));
        let mut strongest = strong;
        strongest.response = 0.1;
        strongest.source = 12;
        assert!(
            retain_feature(&mut pool, strongest, 2),
            "replacement must work at full capacity"
        );
        assert_eq!(pool.len(), 1);
        assert_eq!(pool[0].source, 12);
    }
}
