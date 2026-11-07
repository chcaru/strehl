//! Direct native pair refinement of coarse guide correspondences. Sources are
//! grouped by original pair and frozen spatial role, before signal arithmetic.
use super::{CoarseCorrespondence, MosaicGeometryConfig, PairDiscovery};
use crate::session_cache::SourceCache;
use crate::session_input::{ResolvedSession, SourceIdentity};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use strehl_core::align::{AlignConfig, Cx, PlaneRef, Similarity, refine_pair_observed};
#[cfg(test)]
use strehl_core::plane::green_luma;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::warpmap::WarpMap;
#[path = "session-mosaic-native-affine.rs"]
mod affine;
#[path = "session-mosaic-grid.rs"]
mod grid;
#[path = "session-mosaic-native-filter.rs"]
mod native_filter;
#[path = "session-mosaic-native-trace.rs"]
mod native_trace;
#[path = "session-mosaic-support.rs"]
mod support;
pub use native_trace::NativeMeasurement;
pub type NativeSupportBounds = [[[f64; 2]; 2]; 2];

pub(super) fn coarse_search_radius_quad() -> f64 {
    grid::FACTOR as f64 * f64::from(grid::RADIUS)
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NativeCorrespondence {
    pub candidate: CoarseCorrespondence,
    pub accepted: bool,
    pub refined_b_quad: Option<[f64; 2]>,
    pub forward_rms_quad: Option<f32>,
    pub reverse_rms_quad: Option<f32>,
    pub reciprocal_error_quad: Option<f64>,
    pub mean_peak: Option<f32>,
    pub forward_tiles: usize,
    pub reverse_tiles: usize,
    pub refusal: Option<String>,
    pub reserved_dependency_checked: bool,
    /// Nomination provenance is not a geometry acceptance certificate.
    #[serde(default)]
    pub nomination_policy: String,
    /// Complete attempted source support in each independent pass-anchor gauge.
    /// Nearby matches whose physical supports overlap are one geometry witness.
    #[serde(default)]
    pub support_bounds_quad: Option<NativeSupportBounds>,
    /// Actual selected-stage observations survive acceptance and refusal alike.
    #[serde(default)]
    pub measurements: Vec<NativeMeasurement>,
}
impl NativeCorrespondence {
    fn refused(candidate: CoarseCorrespondence, reason: impl Into<String>) -> Self {
        let nomination_policy = nomination_policy(&candidate).into();
        Self {
            candidate,
            accepted: false,
            refined_b_quad: None,
            forward_rms_quad: None,
            reverse_rms_quad: None,
            reciprocal_error_quad: None,
            mean_peak: None,
            forward_tiles: 0,
            reverse_tiles: 0,
            refusal: Some(reason.into()),
            reserved_dependency_checked: false,
            nomination_policy,
            support_bounds_quad: None,
            measurements: Vec::new(),
        }
    }
}

fn nomination_policy(candidate: &CoarseCorrespondence) -> &'static str {
    if candidate.grid_nomination {
        "generated grid within FIT-only spatial/acquisition support; coarse original NCC required"
    } else if candidate.within_seed_support {
        "reciprocal original-feature coordinates within coarse support; untrusted native nomination"
    } else {
        "reciprocal original-feature coordinates outside coarse support; own observed coordinates, bounded linear seed only, no generated extrapolation"
    }
}

fn native_candidate_seed(
    candidate: &CoarseCorrespondence,
    seed: Option<[f64; 4]>,
) -> Option<[f64; 4]> {
    seed.filter(|s| {
        s.iter().all(|v| v.is_finite())
            && (0.5..=2.0).contains(&s[0].hypot(s[1]))
            && (!candidate.grid_nomination || candidate.within_seed_support)
    })
}

fn anchor_support_bounds(
    measurements: &[NativeMeasurement],
    placements: [Similarity; 2],
    g: PlaneGeometry,
    halo: usize,
) -> Result<[[[f64; 2]; 2]; 2]> {
    let inverse = [
        placements[0]
            .invert()
            .context("singular support placement")?,
        placements[1]
            .invert()
            .context("singular support placement")?,
    ];
    let mut output = [[[f64::INFINITY; 2], [f64::NEG_INFINITY; 2]]; 2];
    for measurement in measurements {
        let mut bounds = measurement
            .sampled_bounds_quad
            .unwrap_or([[[f64::INFINITY; 2], [f64::NEG_INFINITY; 2]]; 2]);
        for footprint in &measurement.affine_footprints {
            for (source, corners) in footprint.iter().enumerate() {
                for q in corners {
                    for (axis, value) in q.iter().enumerate() {
                        bounds[source][0][axis] = bounds[source][0][axis].min(value.floor());
                        bounds[source][1][axis] = bounds[source][1][axis]
                            .max(value.floor() + if source == 1 { 1.0 } else { 0.0 });
                    }
                }
            }
        }
        ensure!(
            bounds.iter().flatten().flatten().all(|v| v.is_finite()),
            "accepted native support bounds missing"
        );
        for (source, bound) in bounds.iter().enumerate() {
            let target = if measurement.direction.starts_with("reverse") {
                1 - source
            } else {
                source
            };
            for x in [bound[0][0] - halo as f64, bound[1][0] + halo as f64] {
                for y in [bound[0][1] - halo as f64, bound[1][1] + halo as f64] {
                    let q = point(inverse[target], [x, y], g);
                    for (axis, value) in q.iter().enumerate() {
                        output[target][0][axis] = output[target][0][axis].min(*value);
                        output[target][1][axis] = output[target][1][axis].max(*value);
                    }
                }
            }
        }
    }
    ensure!(
        output.iter().flatten().flatten().all(|v| v.is_finite()),
        "native support cannot be empty"
    );
    Ok(output)
}

/// Complete dependency union for either accepted or refused native work.
/// The caller binds these placements to the receipt's exact original IDs.
/// None is returned only when the same producing-path geometric guard proves
/// that no NCC query could run; missing/partial attempted traces are errors.
pub fn native_attempted_support(
    receipt: &NativeCorrespondence,
    placements: [Similarity; 2],
    geometry: PlaneGeometry,
    config: &MosaicGeometryConfig,
) -> Result<Option<NativeSupportBounds>> {
    let pa = point(placements[0], receipt.candidate.point_a_quad, geometry);
    let pb = point(placements[1], receipt.candidate.point_b_quad, geometry);
    if receipt.measurements.is_empty() {
        ensure!(
            !receipt.accepted,
            "accepted correspondence lacks dependency trace"
        );
        let no_query = if receipt.candidate.grid_nomination {
            grid::coarse_spots(
                pa,
                PlaneGeometry {
                    width: geometry.width / grid::FACTOR,
                    height: geometry.height / grid::FACTOR,
                },
            )
            .is_none()
        } else if !config.native_affine {
            spots(
                pa,
                geometry,
                config.native_tile,
                config.native_search_radius,
            )
            .is_none()
                || spots(
                    pb,
                    geometry,
                    config.native_tile,
                    config.native_search_radius,
                )
                .is_none()
        } else {
            false
        };
        ensure!(
            no_query,
            "attempted native dependency trace is unknown; cannot plan validation islands"
        );
        return Ok(None);
    }
    let bounds = anchor_support_bounds(
        &receipt.measurements,
        placements,
        geometry,
        if config.native_lowpass {
            native_filter::HALO
        } else {
            0
        },
    )?;
    if receipt.accepted {
        ensure!(
            receipt.support_bounds_quad == Some(bounds),
            "accepted dependency bounds differ from complete attempted trace"
        );
    }
    Ok(Some(bounds))
}

fn point(t: Similarity, p: [f64; 2], g: PlaneGeometry) -> [f64; 2] {
    let q = t.apply_at(p[0], p[1], g.width as f64 * 0.5, g.height as f64 * 0.5);
    [q.0, q.1]
}
fn anchored_seed(linear: Cx, p: [f64; 2], q: [f64; 2], g: PlaneGeometry) -> Similarity {
    let center = Cx::new(g.width as f64 * 0.5, g.height as f64 * 0.5);
    Similarity {
        a: linear,
        b: Cx::new(q[0], q[1]) - center - linear * (Cx::new(p[0], p[1]) - center),
    }
}
fn spots(
    point: [f64; 2],
    g: PlaneGeometry,
    tile: usize,
    radius: i32,
) -> Option<Vec<(usize, usize)>> {
    if !point.into_iter().all(f64::is_finite) {
        return None;
    }
    let half = tile as f64 * 0.5;
    let mut out = Vec::with_capacity(9);
    for dy in [-half, 0.0, half] {
        for dx in [-half, 0.0, half] {
            let x = (point[0] + dx - half).round();
            let y = (point[1] + dy - half).round();
            if x < f64::from(radius) + 2.0
                || y < f64::from(radius) + 2.0
                || x + tile as f64 + f64::from(radius) + 2.0 >= g.width as f64
                || y + tile as f64 + f64::from(radius) + 2.0 >= g.height as f64
            {
                return None;
            }
            out.push((x as usize, y as usize));
        }
    }
    Some(out)
}

/// Same native estimator as the normal geometry path; independent forward and
/// reverse image calls are required. The result is evaluated at the actual
/// feature point, not its large global similarity lever arm.
#[allow(clippy::too_many_arguments)]
fn refine_on_planes_observed(
    a: PlaneRef<'_>,
    b: PlaneRef<'_>,
    pa: [f64; 2],
    pb: [f64; 2],
    seed: Similarity,
    config: &MosaicGeometryConfig,
    roles: Option<&[support::RoleWitness<'_>; 2]>,
    originals: Option<&[support::PixelWitness<'_>; 2]>,
    measurements: &mut Vec<NativeMeasurement>,
) -> Result<(Similarity, f32, f32, f64, f32, usize, usize)> {
    let g = a.geometry();
    ensure!(b.geometry() == g, "native mosaic plane geometry differs");
    let mut cfg = AlignConfig::shallow();
    cfg.fine_tile = config.native_tile;
    cfg.fine_radius = config.native_search_radius;
    cfg.fine_iters = 3;
    cfg.warp_tiles = true;
    cfg.min_peak = config.native_minimum_peak;
    cfg.min_tiles = 6;
    let sa = spots(pa, g, cfg.fine_tile, cfg.fine_radius)
        .context("native reference patch leaves source")?;
    let sb = spots(pb, g, cfg.fine_tile, cfg.fine_radius)
        .context("native moving patch leaves source")?;
    let mut forward_reserved = true;
    let mut forward_unclipped = true;
    let mut check_forward = |trace: &strehl_core::align::PairTrace| {
        if let Some(roles) = roles {
            forward_reserved &= support::reserved(trace, roles, 1);
        }
        forward_unclipped &=
            forward_reserved && support::observed_support(trace, None, originals, 1);
        measurements.push(native_trace::capture(
            "forward",
            trace,
            forward_reserved,
            forward_unclipped,
            1,
        ));
    };
    let forward = refine_pair_observed(a, b, &sa, &cfg, seed, Some(&mut check_forward))
        .map_err(|error| anyhow::anyhow!("forward native measurement refused: {error:?}"))?;
    let mut reverse_reserved = true;
    let mut reverse_unclipped = true;
    let mut check_reverse = |trace: &strehl_core::align::PairTrace| {
        if let Some(roles) = roles {
            reverse_reserved &= support::reserved(trace, &[roles[1], roles[0]], 1);
        }
        let swapped = originals.map(|o| [o[1], o[0]]);
        reverse_unclipped &=
            reverse_reserved && support::observed_support(trace, None, swapped.as_ref(), 1);
        measurements.push(native_trace::capture(
            "reverse",
            trace,
            reverse_reserved,
            reverse_unclipped,
            1,
        ));
    };
    let reverse = refine_pair_observed(
        b,
        a,
        &sb,
        &cfg,
        seed.invert().context("singular native seed")?,
        Some(&mut check_reverse),
    )
    .map_err(|error| anyhow::anyhow!("reverse native measurement refused: {error:?}"))?;
    ensure!(
        forward_reserved && reverse_reserved,
        "actual native search footprint leaves reserved spatial role"
    );
    ensure!(
        forward_unclipped && reverse_unclipped,
        "actual native search footprint has missing or clipped original green support"
    );
    let transformed = point(forward.similarity(), pa, g);
    let roundtrip = point(reverse.similarity(), transformed, g);
    let reciprocal = (pa[0] - roundtrip[0]).hypot(pa[1] - roundtrip[1]);
    ensure!(
        f64::from(forward.rms) <= config.maximum_native_residual
            && f64::from(reverse.rms) <= config.maximum_native_residual,
        "native local fit residual exceeds configured bar: forward={} reverse={} maximum={} quad pixels (tiles {}/{}, peaks {}/{})",
        forward.rms,
        reverse.rms,
        config.maximum_native_residual,
        forward.used,
        reverse.used,
        forward.peak_mean,
        reverse.peak_mean
    );
    ensure!(
        reciprocal <= config.maximum_reciprocal_error,
        "independently measured forward/reverse loop exceeds configured bar: {reciprocal} > {} quad pixels",
        config.maximum_reciprocal_error
    );
    Ok((
        forward.similarity(),
        forward.rms,
        reverse.rms,
        reciprocal,
        (forward.peak_mean + reverse.peak_mean) * 0.5,
        forward.used,
        reverse.used,
    ))
}

#[cfg(test)]
fn refine_on_planes(
    a: PlaneRef<'_>,
    b: PlaneRef<'_>,
    pa: [f64; 2],
    pb: [f64; 2],
    seed: Similarity,
    config: &MosaicGeometryConfig,
    roles: Option<&[support::RoleWitness<'_>; 2]>,
) -> Result<(Similarity, f32, f32, f64, f32, usize, usize)> {
    refine_on_planes_observed(a, b, pa, pb, seed, config, roles, None, &mut Vec::new())
}

#[cfg(test)]
fn unclipped_patch<S: QuadSource + ?Sized>(
    source: &S,
    white: f32,
    p: [f64; 2],
    radius: usize,
) -> bool {
    let g = source.geometry();
    if p[0] < radius as f64
        || p[1] < radius as f64
        || p[0] + radius as f64 >= g.width as f64
        || p[1] + radius as f64 >= g.height as f64
    {
        return false;
    }
    let x = p[0].round() as usize;
    let y = p[1].round() as usize;
    if x < radius || y < radius || x + radius >= g.width || y + radius >= g.height {
        return false;
    }
    for row in y - radius..=y + radius {
        let (r0, r1) = source.quad_rows(row);
        if r0.len() < 2 * g.width || r1.len() < 2 * g.width {
            return false;
        }
        for column in x - radius..=x + radius {
            if f32::from(r0[2 * column + 1]) >= white || f32::from(r1[2 * column]) >= white {
                return false;
            }
        }
    }
    true
}

fn native_reservation(
    g: PlaneGeometry,
    pair_count: usize,
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<usize> {
    let candidates = pair_count
        .checked_mul(
            config
                .maximum_features
                .checked_add(grid::MAX_CANDIDATES)
                .context("native mosaic reservation overflow")?,
        )
        .context("native mosaic reservation overflow")?;
    native_candidate_reservation(g, candidates, config, budget)
}

fn native_candidate_reservation(
    g: PlaneGeometry,
    candidates: usize,
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<usize> {
    // Affine diagnostics retain every attempted pass and its transformed
    // corners. Ten passes of nine probes plus coarse receipts fit this bound;
    // the similarity observer retains only its selected-stage measurements.
    let receipt_bytes = if config.native_affine { 65536 } else { 16384 };
    let reserved = g
        .pixels()
        .checked_mul(64)
        .and_then(|n| n.checked_add(candidates.checked_mul(receipt_bytes)?))
        .and_then(|n| n.checked_add(config.role_work_bytes().ok()?))
        .context("native mosaic reservation overflow")?;
    ensure!(
        reserved <= budget,
        "native mosaic refinement exceeds explicit memory reservation"
    );
    Ok(reserved)
}

/// `maps[p]` retains all global source indices, with placements for pass p in
/// that pass's independent anchor gauge. The function never requires a global
/// similarity to explain different mosaic viewpoints.
#[allow(clippy::too_many_arguments)]
pub fn refine_native_correspondences(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    guides: &[super::MosaicGuide],
    pairs: &[PairDiscovery],
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<Vec<NativeCorrespondence>> {
    refine_native_correspondences_impl(
        session, identities, maps, cache, guides, pairs, config, budget, false, true,
    )
}

/// Replay the production estimator while refusing every missing cache entry.
#[allow(clippy::too_many_arguments)]
pub fn refine_native_correspondences_cached(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    guides: &[super::MosaicGuide],
    pairs: &[PairDiscovery],
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<Vec<NativeCorrespondence>> {
    refine_native_correspondences_impl(
        session, identities, maps, cache, guides, pairs, config, budget, true, true,
    )
}

/// Research replay of explicit FIT-derived nominations only. No recursive grid
/// generation, no RAW decode, and no bypass of actual native acceptance checks.
#[allow(clippy::too_many_arguments)]
pub fn refine_explicit_correspondences_cached(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    guides: &[super::MosaicGuide],
    pairs: &[PairDiscovery],
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<Vec<NativeCorrespondence>> {
    refine_native_correspondences_impl(
        session, identities, maps, cache, guides, pairs, config, budget, true, false,
    )
}

#[allow(clippy::too_many_arguments)]
fn refine_native_correspondences_impl(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    guides: &[super::MosaicGuide],
    pairs: &[PairDiscovery],
    config: &MosaicGeometryConfig,
    budget: usize,
    cached_only: bool,
    generate_grid: bool,
) -> Result<Vec<NativeCorrespondence>> {
    ensure!(
        config.role_work_bytes()? <= budget,
        "frozen role plan exceeds native query budget"
    );
    config.validate()?;
    ensure!(
        maps.len() == session.passes.len()
            && guides.len() == maps.len()
            && identities.len() == session.len(),
        "native mosaic census differs"
    );
    let g = maps.first().context("no mosaic passes")?.geometry();
    ensure!(
        maps.iter()
            .all(|map| map.len() == session.len() && map.geometry() == g),
        "native mosaic map gauge differs"
    );
    if generate_grid {
        native_reservation(g, pairs.len(), config, budget)?;
    } else {
        let count = pairs
            .iter()
            .try_fold(0_usize, |count, pair| {
                count.checked_add(pair.correspondences.len())
            })
            .context("explicit native candidate count overflow")?;
        native_candidate_reservation(g, count, config, budget)?;
    }
    type SourcePairCandidates = BTreeMap<
        (usize, usize, bool, Option<usize>),
        Vec<(CoarseCorrespondence, [f64; 4], String)>,
    >;
    let mut grouped: SourcePairCandidates = BTreeMap::new();
    let mut receipts = Vec::new();
    for pair in pairs {
        ensure!(
            pair.pass_a < maps.len() && pair.pass_b < maps.len() && pair.pass_a != pair.pass_b,
            "native mosaic pair index invalid"
        );
        let mut candidates = pair.correspondences.clone();
        if generate_grid {
            candidates.extend(grid::nominate(guides, maps, pair, config)?);
        }
        for candidate in &candidates {
            ensure!(
                candidate.pass_a == pair.pass_a
                    && candidate.pass_b == pair.pass_b
                    && session.passes[pair.pass_a]
                        .global_range
                        .contains(&candidate.source_a)
                    && session.passes[pair.pass_b]
                        .global_range
                        .contains(&candidate.source_b),
                "native candidate source/pass binding differs"
            );
            if !candidate.spatial_roles_match {
                receipts.push(NativeCorrespondence::refused(
                    candidate.clone(),
                    "both views must reserve the same fit/heldout role",
                ));
            } else if let Some(seed) = native_candidate_seed(candidate, pair.seed_a_to_b) {
                let heldout = candidate.role == super::MatchRole::Heldout;
                let island = (heldout && config.role_plan.is_some())
                    .then_some(candidate.spatial_blocks[0][0]);
                grouped
                    .entry((candidate.source_a, candidate.source_b, heldout, island))
                    .or_default()
                    .push((
                        candidate.clone(),
                        seed,
                        if generate_grid {
                            nomination_policy(candidate).into()
                        } else {
                            pair.nomination.clone()
                        },
                    ));
            } else {
                receipts.push(NativeCorrespondence::refused(
                    candidate.clone(),
                    "coarse overlap seed unavailable or outside supported search",
                ));
            }
        }
    }
    for ((ia, ib, heldout, island), candidates) in grouped {
        let first = &candidates[0].0;
        let Some(wa) = maps[first.pass_a].warps()[ia].placed() else {
            receipts.extend(
                candidates.into_iter().map(|(c, _, _)| {
                    NativeCorrespondence::refused(c, "native reference is unplaced")
                }),
            );
            continue;
        };
        let Some(wb) = maps[first.pass_b].warps()[ib].placed() else {
            receipts.extend(candidates.into_iter().map(|(c, _, _)| {
                NativeCorrespondence::refused(c, "native moving source is unplaced")
            }));
            continue;
        };
        let group_roles = [
            support::RoleWitness::new(&guides[first.pass_a], wa, heldout, config)?
                .for_island(island),
            support::RoleWitness::new(&guides[first.pass_b], wb, heldout, config)?
                .for_island(island),
        ];
        let source_a = if cached_only {
            cache
                .load(&identities[ia])?
                .context("cached mosaic reference missing; RAW decode prohibited")?
        } else {
            cache.load_or_decode(&session.frames[ia], &identities[ia])?
        };
        let source_b = if cached_only {
            cache
                .load(&identities[ib])?
                .context("cached mosaic moving source missing; RAW decode prohibited")?
        } else {
            cache.load_or_decode(&session.frames[ib], &identities[ib])?
        };
        ensure!(
            source_a.geometry() == g && source_b.geometry() == g,
            "native mosaic source shape differs"
        );
        let mut pixels_a = vec![0.0; g.pixels()];
        let mut pixels_b = vec![0.0; g.pixels()];
        support::green_luma_reserved(
            source_a.as_ref(),
            source_a.levels().black,
            group_roles[0],
            &mut pixels_a,
        );
        support::green_luma_reserved(
            source_b.as_ref(),
            source_b.levels().black,
            group_roles[1],
            &mut pixels_b,
        );
        let coarse = if candidates.iter().any(|(c, _, _)| c.grid_nomination) {
            Some((
                strehl_core::align::downsample(
                    PlaneRef::from_geometry(&pixels_a, g).context("native reference shape")?,
                    grid::FACTOR,
                )
                .context("coarse reference too small")?,
                strehl_core::align::downsample(
                    PlaneRef::from_geometry(&pixels_b, g).context("native moving shape")?,
                    grid::FACTOR,
                )
                .context("coarse moving too small")?,
            ))
        } else {
            None
        };
        if config.native_lowpass {
            native_filter::apply(&mut pixels_a, g);
            native_filter::apply(&mut pixels_b, g);
        }
        let a = PlaneRef::from_geometry(&pixels_a, g).context("native reference plane shape")?;
        let b = PlaneRef::from_geometry(&pixels_b, g).context("native moving plane shape")?;
        for (candidate, seed, nomination) in candidates {
            let mut measurements = Vec::new();
            let result = (|| -> Result<NativeCorrespondence> {
                let wa = maps[candidate.pass_a].warps()[ia]
                    .placed()
                    .context("native reference is unplaced")?;
                let wb = maps[candidate.pass_b].warps()[ib]
                    .placed()
                    .context("native moving source is unplaced")?;
                let pa = point(wa, candidate.point_a_quad, g);
                let pb = point(wb, candidate.point_b_quad, g);
                let linear = wa
                    .invert()
                    .context("singular reference placement")?
                    .then(Similarity {
                        a: Cx::new(seed[0], seed[1]),
                        b: Cx::new(seed[2], seed[3]),
                    })
                    .then(wb)
                    .a;
                let mut native_seed = anchored_seed(linear, pa, pb, g);
                let heldout = candidate.role == super::MatchRole::Heldout;
                let island = if let Some(frozen) = &config.role_plan {
                    if heldout {
                        let island = candidate.spatial_blocks[0][0];
                        let planned = frozen
                            .plan
                            .islands
                            .get(island)
                            .context("unknown frozen validation island")?;
                        ensure!(
                            candidate.pass_a == 0
                                && candidate.pass_b == 1
                                && candidate.spatial_blocks == [[island, usize::MAX]; 2]
                                && !candidate.grid_nomination
                                && candidate.point_a_quad == planned.proposal.reference_center_quad
                                && candidate.point_b_quad == planned.nominated_moving_center_quad
                                && frozen.plan.witness_allowed(island, 0, ia)
                                && frozen.plan.witness_allowed(island, 1, ib),
                            "validation candidate differs from frozen native-only island plan"
                        );
                        Some(island)
                    } else {
                        None
                    }
                } else {
                    None
                };
                let roles = [
                    support::RoleWitness::new(&guides[candidate.pass_a], wa, heldout, config)?
                        .for_island(island),
                    support::RoleWitness::new(&guides[candidate.pass_b], wb, heldout, config)?
                        .for_island(island),
                ];
                let originals = [
                    support::PixelWitness {
                        source: source_a.as_ref(),
                        white: source_a.levels().white,
                        filter_halo: if config.native_lowpass {
                            native_filter::HALO
                        } else {
                            0
                        },
                    },
                    support::PixelWitness {
                        source: source_b.as_ref(),
                        white: source_b.levels().white,
                        filter_halo: if config.native_lowpass {
                            native_filter::HALO
                        } else {
                            0
                        },
                    },
                ];
                if candidate.grid_nomination {
                    let (ca, cb) = coarse.as_ref().context("grid search planes missing")?;
                    let mut reserved = true;
                    let mut unclipped = true;
                    let proposed_linear = native_seed.a;
                    native_seed = grid::coarse_seed(
                        ca.as_ref(),
                        cb.as_ref(),
                        g,
                        [pa, pb],
                        native_seed,
                        config,
                        Some(&mut |trace| {
                            reserved &= support::reserved(trace, &roles, grid::FACTOR);
                            unclipped &= reserved
                                && support::observed_support(
                                    trace,
                                    None,
                                    Some(&originals),
                                    grid::FACTOR,
                                );
                            measurements.push(native_trace::capture(
                                "coarse",
                                trace,
                                reserved,
                                unclipped,
                                grid::FACTOR,
                            ));
                        }),
                    )?;
                    if !generate_grid {
                        // FIT-derived explicit neighbors borrow only the coarse
                        // translation search. Its noisy local similarity must
                        // not replace the independently measured parent linear seed.
                        native_seed =
                            anchored_seed(proposed_linear, pa, point(native_seed, pa, g), g);
                    }
                    ensure!(
                        reserved,
                        "actual coarse search footprint leaves reserved spatial role"
                    );
                    ensure!(
                        unclipped,
                        "actual coarse search footprint has missing or clipped original green support"
                    );
                }
                let measured_pb = point(native_seed, pa, g);
                // Admission depends only on original pixels recorded by the
                // actual coarse/fine/affine support observer. A separate square
                // clipping precheck would consume an unrecorded outer ring and
                // could cross a reserved FIT/heldout boundary.
                let (refined_native, forward, reverse, reciprocal, peak, used_a, used_b) =
                    if config.native_affine {
                        affine::refine(
                            a,
                            b,
                            pa,
                            measured_pb,
                            native_seed,
                            config,
                            Some(&roles),
                            Some(&originals),
                            &mut measurements,
                        )?
                    } else {
                        let (fit, forward, reverse, reciprocal, peak, used_a, used_b) =
                            refine_on_planes_observed(
                                a,
                                b,
                                pa,
                                measured_pb,
                                native_seed,
                                config,
                                Some(&roles),
                                Some(&originals),
                                &mut measurements,
                            )?;
                        (
                            point(fit, pa, g),
                            forward,
                            reverse,
                            reciprocal,
                            peak,
                            used_a,
                            used_b,
                        )
                    };
                let refined_b = point(
                    wb.invert().context("singular moving placement")?,
                    refined_native,
                    g,
                );
                Ok(NativeCorrespondence {
                    candidate: candidate.clone(),
                    accepted: true,
                    refined_b_quad: Some(refined_b),
                    forward_rms_quad: Some(forward),
                    reverse_rms_quad: Some(reverse),
                    reciprocal_error_quad: Some(reciprocal),
                    mean_peak: Some(peak),
                    forward_tiles: used_a,
                    reverse_tiles: used_b,
                    refusal: None,
                    reserved_dependency_checked: true,
                    nomination_policy: nomination_policy(&candidate).into(),
                    support_bounds_quad: Some(anchor_support_bounds(
                        &measurements,
                        [wa, wb],
                        g,
                        if config.native_lowpass {
                            native_filter::HALO
                        } else {
                            0
                        },
                    )?),
                    measurements: Vec::new(),
                })
            })();
            let mut receipt = result.unwrap_or_else(|error| {
                NativeCorrespondence::refused(candidate, error.to_string())
            });
            receipt.measurements = measurements;
            receipt.nomination_policy = nomination;
            receipts.push(receipt);
        }
    }
    receipts.sort_by(|a, b| a.candidate.id.cmp(&b.candidate.id));
    Ok(receipts)
}

#[cfg(test)]
#[path = "session-mosaic-native-tests.rs"]
mod tests;
