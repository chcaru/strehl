//! An unverified coarse pose nominates spatial original-image measurements.
//! Descriptor counts never certify these grid points; every admitted point must
//! survive its own original-CFA coarse search and reciprocal native refinement.
use super::*;

pub(super) const FACTOR: usize = 4;
pub(super) const TILE: usize = 16;
pub(super) const RADIUS: i32 = 12;
pub(super) const MAX_CANDIDATES: usize = 1024;

fn witness(guide: &super::super::MosaicGuide, p: [f64; 2]) -> Option<(usize, Option<[f32; 2]>)> {
    let x = ((p[0] - guide.origin[0]) / guide.step as f64).round();
    let y = ((p[1] - guide.origin[1]) / guide.step as f64).round();
    if !x.is_finite()
        || !y.is_finite()
        || x < 0.0
        || y < 0.0
        || x >= guide.geometry.width as f64
        || y >= guide.geometry.height as f64
    {
        return None;
    }
    let i = y as usize * guide.geometry.width + x as usize;
    if !guide.covered[i] {
        return None;
    }
    let source = guide.source_indices[i]
        .into_iter()
        .find(|&s| s != usize::MAX)?;
    Some((
        source,
        guide.usable_focus[i].then_some([guide.focus_ordinal[i], guide.focus_width[i]]),
    ))
}

pub(super) fn nominate(
    guides: &[super::super::MosaicGuide],
    maps: &[WarpMap],
    pair: &PairDiscovery,
    config: &MosaicGeometryConfig,
) -> Result<Vec<CoarseCorrespondence>> {
    let Some(seed) = pair.seed_a_to_b else {
        return Ok(Vec::new());
    };
    let a = &guides[pair.pass_a];
    let b = &guides[pair.pass_b];
    let seed = Similarity {
        a: Cx::new(seed[0], seed[1]),
        b: Cx::new(seed[2], seed[3]),
    };
    let stride = (config.holdout_block_guide_pixels / 4).max(16);
    let mut result = Vec::new();
    for y in (stride / 2..a.geometry.height).step_by(stride) {
        for x in (stride / 2..a.geometry.width).step_by(stride) {
            if result.len() == MAX_CANDIDATES {
                return Ok(result);
            }
            let pa = a.full_point([x as f64, y as f64]);
            let Some((ia, fa)) = witness(a, pa) else {
                continue;
            };
            let pb = if let Some(model) = &pair.ordinal_seed {
                if !model.supports(ia) {
                    continue;
                }
                model.predict(pa, ia)
            } else {
                point(seed, pa, a.source_geometry)
            };
            let Some((ib, fb)) = witness(b, pb) else {
                continue;
            };
            let mut moving_sources = Vec::new();
            if let Some(model) = &pair.ordinal_seed {
                for source in model.target_sources(ia) {
                    if source != ib
                        && maps[pair.pass_b]
                            .warps()
                            .get(source)
                            .is_some_and(|w| w.placed().is_some())
                    {
                        moving_sources.push(source);
                    }
                }
            }
            moving_sources.push(ib);
            debug_assert!(moving_sources.len() <= 4);
            for ib in moving_sources {
                if result.len() == MAX_CANDIDATES {
                    return Ok(result);
                }
                let wa = maps[pair.pass_a].warps()[ia]
                    .placed()
                    .context("grid reference witness unplaced")?;
                let wb = maps[pair.pass_b].warps()[ib]
                    .placed()
                    .context("grid moving witness unplaced")?;
                let mut roles = Vec::new();
                for (guide, p, warp) in [(a, pa, wa), (b, pb, wb)] {
                    let inverse = warp.invert().context("singular grid source pose")?;
                    let radius = (FACTOR * (TILE + RADIUS as usize + 2)) as f64
                        * (inverse.a.re.abs() + inverse.a.im.abs())
                        / guide.step as f64;
                    let q = [
                        (p[0] - guide.origin[0]) / guide.step as f64,
                        (p[1] - guide.origin[1]) / guide.step as f64,
                    ];
                    roles.push(config.spatial_role(guide, q, radius));
                }
                let (Some((ba, ra)), Some((bb, rb))) = (roles[0], roles[1]) else {
                    continue;
                };
                // Both physical views must reserve the same role. Using OR here
                // could let a held-out match share its other view with training.
                if ra != rb || (ra && config.role_plan.is_some()) {
                    continue;
                }
                result.push(CoarseCorrespondence {
                    id: format!("p{}-p{}-grid-{x}-{y}-source{ib}", pair.pass_a, pair.pass_b),
                    pass_a: pair.pass_a,
                    pass_b: pair.pass_b,
                    point_a_quad: pa,
                    point_b_quad: pb,
                    source_a: ia,
                    source_b: ib,
                    focus_a: fa,
                    focus_b: fb,
                    role: if ra {
                        super::super::MatchRole::Heldout
                    } else {
                        super::super::MatchRole::Fit
                    },
                    spatial_blocks: [ba, bb],
                    descriptor_distance: 0.0,
                    seed_residual_quad: 0.0,
                    within_seed_support: true,
                    grid_nomination: true,
                    spatial_roles_match: true,
                });
            }
        }
    }
    Ok(result)
}

pub(super) fn coarse_spots(
    point_native: [f64; 2],
    geometry: PlaneGeometry,
) -> Option<Vec<(usize, usize)>> {
    let offset = (FACTOR - 1) as f64 * 0.5;
    let point = point_native.map(|v| (v - offset) / FACTOR as f64);
    spots(point, geometry, TILE, RADIUS)
}

pub(super) fn coarse_seed(
    a: PlaneRef<'_>,
    b: PlaneRef<'_>,
    native: PlaneGeometry,
    points: [[f64; 2]; 2],
    seed: Similarity,
    config: &MosaicGeometryConfig,
    observer: Option<&mut dyn FnMut(&strehl_core::align::PairTrace)>,
) -> Result<Similarity> {
    let [pa, pb] = points;
    let factor = FACTOR as f64;
    let offset = (FACTOR - 1) as f64 * 0.5;
    let ca = pa.map(|v| (v - offset) / factor);
    let cb = pb.map(|v| (v - offset) / factor);
    let geometry = a.geometry();
    ensure!(
        b.geometry() == geometry,
        "coarse mosaic source shapes differ"
    );
    let seed = anchored_seed(seed.a, ca, cb, geometry);
    let mut cfg = AlignConfig::shallow();
    cfg.fine_tile = TILE;
    cfg.fine_radius = RADIUS;
    cfg.fine_iters = 1;
    cfg.min_tiles = 6;
    cfg.min_peak = config.native_minimum_peak;
    cfg.warp_tiles = true;
    let sites = coarse_spots(pa, geometry).context("coarse mosaic source patch leaves image")?;
    let measured = refine_pair_observed(a, b, &sites, &cfg, seed, observer)
        .map_err(|e| anyhow::anyhow!("coarse original-image search refused: {e:?}"))?;
    let q = point(measured.similarity(), ca, geometry).map(|v| factor * v + offset);
    // This only recentres the full-native search; the coarse residual is never
    // substituted for the final native, reciprocal or held-out residual.
    ensure!(
        geometry.width == native.width / FACTOR && geometry.height == native.height / FACTOR,
        "coarse mosaic grid differs from native geometry"
    );
    Ok(anchored_seed(measured.similarity().a, pa, q, native))
}
