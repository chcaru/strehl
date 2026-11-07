//! Frozen mask/source-ranked FIT grid. No intensity or residual input.
use super::*;
pub const STRIDE: usize = 128;
pub const RADIUS: f64 = 48.;
pub const MAX_ANCHORS: usize = 512;
pub const RULE: &str = "focus-fit-grid.v1: native anchors64+128n; Linf48 on4quad lattice; covered+usable masks in both guides; initial frozen FIT seed only; distance2,y,x order; A1/B3 original ranks; complete120quad inverse-pose coarse footprint in FIT; first geometrically eligible centre; coarse original NCC mandatory; no post-native retries; max512 anchors/1536 pairs";

fn index(g: &MosaicGuide, p: [f64; 2]) -> Option<usize> {
    let q = [0, 1].map(|axis| ((p[axis] - g.origin[axis]) / g.step as f64).round());
    if q.into_iter().any(|x| !x.is_finite())
        || q[0] < 0.
        || q[1] < 0.
        || q[0] >= g.geometry.width as f64
        || q[1] >= g.geometry.height as f64
    {
        return None;
    }
    Some(q[1] as usize * g.geometry.width + q[0] as usize)
}
fn point(seed: Similarity, p: [f64; 2], g: &MosaicGuide) -> [f64; 2] {
    let q = seed.apply_at(
        p[0],
        p[1],
        g.source_geometry.width as f64 * 0.5,
        g.source_geometry.height as f64 * 0.5,
    );
    [q.0, q.1]
}
fn ranked(
    guides: &[MosaicGuide],
    seed: Similarity,
    anchor: [f64; 2],
) -> Vec<([f64; 2], [usize; 2])> {
    let a = &guides[0];
    let mut result = Vec::new();
    let low = [0, 1].map(|i| {
        ((anchor[i] - RADIUS - a.origin[i]) / a.step as f64)
            .ceil()
            .max(0.) as usize
    });
    let high = [0, 1].map(|i| {
        ((anchor[i] + RADIUS - a.origin[i]) / a.step as f64)
            .floor()
            .max(0.) as usize
    });
    for y in low[1]..=high[1].min(a.geometry.height - 1) {
        for x in low[0]..=high[0].min(a.geometry.width - 1) {
            let i = y * a.geometry.width + x;
            if !a.covered[i] || !a.usable_focus[i] {
                continue;
            }
            let p = a.full_point([x as f64, y as f64]);
            let Some(j) = index(&guides[1], point(seed, p, a)) else {
                continue;
            };
            if guides[1].covered[j] && guides[1].usable_focus[j] {
                result.push((p, [i, j]));
            }
        }
    }
    result.sort_by(|(a, _), (b, _)| {
        let distance = |p: [f64; 2]| (p[0] - anchor[0]).powi(2) + (p[1] - anchor[1]).powi(2);
        distance(*a)
            .total_cmp(&distance(*b))
            .then(a[1].total_cmp(&b[1]))
            .then(a[0].total_cmp(&b[0]))
    });
    result
}
pub fn nominate(
    guides: &[MosaicGuide],
    maps: &[WarpMap],
    config: &MosaicGeometryConfig,
) -> Result<(Vec<CoarseCorrespondence>, Vec<Value>)> {
    ensure!(
        guides.len() == 2 && maps.len() == 2 && guides.iter().all(|g| g.step == 4),
        "focus grid requires two4quad guides"
    );
    for g in guides {
        g.validate()?;
    }
    let frozen = config
        .role_plan
        .as_ref()
        .context("focus grid requires existing frozen held plan")?;
    frozen.verify()?;
    let seed = frozen.plan.initial_seed;
    let seed = Similarity {
        a: strehl_core::align::Cx::new(seed[0], seed[1]),
        b: strehl_core::align::Cx::new(seed[2], seed[3]),
    };
    let size = guides[0].source_geometry;
    let anchors: Vec<_> = (64..size.height)
        .step_by(STRIDE)
        .flat_map(|y| {
            (64..size.width)
                .step_by(STRIDE)
                .map(move |x| [x as f64, y as f64])
        })
        .collect();
    ensure!(
        anchors.len() <= MAX_ANCHORS,
        "focus grid anchor budget exceeded; no biased prefix truncation"
    );
    let mut candidates = Vec::new();
    let mut receipts = Vec::new();
    for (anchor_id, anchor) in anchors.into_iter().enumerate() {
        let positions = ranked(guides, seed, anchor);
        let mut refusals = Vec::new();
        let mut selected = None;
        for (rank, (p, indices)) in positions.iter().enumerate() {
            let q = point(seed, *p, &guides[0]);
            let mut sources = [Vec::new(), Vec::new()];
            for pass in 0..2 {
                for id in guides[pass].source_indices[indices[pass]] {
                    if id == usize::MAX {
                        continue;
                    }
                    let range = frozen.plan.grids[pass].global_source_range;
                    ensure!(
                        (range[0]..range[1]).contains(&id) && id < maps[pass].len(),
                        "focus grid original identity outside declared pass"
                    );
                    if maps[pass].warps()[id].placed().is_some() && !sources[pass].contains(&id) {
                        sources[pass].push(id);
                    }
                    if sources[pass].len() == if pass == 0 { 1 } else { 3 } {
                        break;
                    }
                }
            }
            let mut eligible = Vec::new();
            let mut pair_checks = Vec::new();
            for &ia in &sources[0] {
                for &ib in &sources[1] {
                    let mut bounds = Vec::new();
                    let mut safe = true;
                    for (pass, source, p) in [(0, ia, *p), (1, ib, q)] {
                        let inverse = maps[pass].warps()[source]
                            .placed()
                            .unwrap()
                            .invert()
                            .context("singular focus-grid source pose")?;
                        let radius = (120. + if config.native_lowpass { 2. } else { 0. })
                            * (inverse.a.re.abs() + inverse.a.im.abs());
                        let rectangle = Rectangle::around(p, radius)?;
                        safe &= frozen.plan.classify(pass, rectangle) == Some(SpatialRole::Fit);
                        bounds.push(rectangle);
                    }
                    pair_checks.push(json!({"sources":[ia,ib],"coarse_pass_gauge_bounds":bounds,"wholly_fit":safe}));
                    if safe {
                        eligible.push((ia, ib));
                    }
                }
            }
            if eligible.is_empty() {
                refusals.push(json!({"rank":rank,"point_quad":p,"pairs":pair_checks,"reason":"no placed source pair has complete coarse footprint in FIT"}));
                continue;
            }
            for (ia, ib) in eligible {
                candidates.push(CoarseCorrespondence {
                    id: format!("focused-fit-anchor{anchor_id}-source{ia}-{ib}"),
                    pass_a: 0,
                    pass_b: 1,
                    point_a_quad: *p,
                    point_b_quad: q,
                    source_a: ia,
                    source_b: ib,
                    focus_a: Some([
                        guides[0].focus_ordinal[indices[0]],
                        guides[0].focus_width[indices[0]],
                    ]),
                    focus_b: Some([
                        guides[1].focus_ordinal[indices[1]],
                        guides[1].focus_width[indices[1]],
                    ]),
                    role: MatchRole::Fit,
                    spatial_blocks: [*p, q].map(|p| {
                        p.map(|v| v.max(0.) as usize / (4 * config.holdout_block_guide_pixels))
                    }),
                    descriptor_distance: 0.,
                    seed_residual_quad: 0.,
                    within_seed_support: true,
                    grid_nomination: true,
                    spatial_roles_match: true,
                });
            }
            selected = Some(
                json!({"rank":rank,"reference_quad":p,"moving_quad":q,"guide_indices":indices,"covered":[true,true],"usable_focus":[true,true],"sources":sources,"pairs":pair_checks,"grid_nomination":true}),
            );
            break;
        }
        receipts.push(json!({"anchor_id":anchor_id,"anchor_quad":anchor,"ranked_candidates":positions,"geometric_refusals":refusals,"selected":selected,"native_retry_policy":"none"}));
    }
    ensure!(
        candidates.len() <= MAX_ANCHORS * 3,
        "focus grid source-pair budget exceeded"
    );
    Ok((candidates, receipts))
}

#[cfg(test)]
mod tests {
    use super::*;
    use staged::nomination::tests::{guides, maps};
    fn setup() -> ([MosaicGuide; 2], MosaicGeometryConfig) {
        let guides = guides([1024, 1024]);
        let grids = [0, 1].map(|pass| AnchorGrid {
            source_size_quad: [1024, 1024],
            guide_origin_quad: [1.5; 2],
            guide_step_quad: 4,
            initial_block_guide_pixels: 128,
            global_source_range: [pass, pass + 1],
        });
        let proposal = IslandProposal {
            id: "held".into(),
            cell: [0, 0],
            reference_center_quad: [145.5; 2],
            original_witnesses: [vec![0], vec![1]],
            query_radius_quad: [35.; 2],
        };
        let plan = RolePlan::build(
            "a".repeat(64),
            "b".repeat(64),
            grids,
            [1., 0., 0., 0.],
            0.,
            Vec::new(),
            vec![proposal],
        )
        .unwrap()
        .freeze()
        .unwrap();
        (
            guides,
            MosaicGeometryConfig {
                role_plan: Some(Box::new(plan)),
                ..MosaicGeometryConfig::default()
            },
        )
    }
    fn both(g: &mut [MosaicGuide; 2], p: [f64; 2]) {
        for a in g {
            let i = index(a, p).unwrap();
            a.covered[i] = true;
            a.usable_focus[i] = true;
        }
    }
    #[test]
    fn focus_grid_uses_exact_tie_order_coarse_role_and_no_signal_ranking() {
        let (mut g, c) = setup();
        both(&mut g, [193.5; 2]);
        both(&mut g, [449.5, 445.5]);
        both(&mut g, [445.5, 449.5]);
        let (a, r) = nominate(&g, &maps(&g), &c).unwrap();
        assert_eq!(a.len(), 1);
        assert_eq!(a[0].point_a_quad, [449.5, 445.5]);
        assert!(a[0].grid_nomination);
        assert!(
            r.iter()
                .any(|x| !x["geometric_refusals"].as_array().unwrap().is_empty())
        );
        for x in &mut g {
            x.intensity.fill(9e6);
        }
        let (b, s) = nominate(&g, &maps(&g), &c).unwrap();
        assert_eq!(
            serde_json::to_value(a).unwrap(),
            serde_json::to_value(b).unwrap()
        );
        assert_eq!(r, s);
    }
    #[test]
    fn focus_grid_retains_unavailable_anchors_and_refuses_wrong_source_identity() {
        let (mut g, c) = setup();
        let (a, r) = nominate(&g, &maps(&g), &c).unwrap();
        assert!(a.is_empty());
        assert_eq!(r.len(), 64);
        both(&mut g, [449.5; 2]);
        let i = index(&g[1], [449.5; 2]).unwrap();
        g[1].source_indices[i][0] = 0;
        assert!(
            nominate(&g, &maps(&g), &c)
                .unwrap_err()
                .to_string()
                .contains("identity")
        );
    }
}
