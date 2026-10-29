//! Conditional nomination from frozen guide masks only; never native residuals.
use super::*;
#[cfg(test)]
#[path = "island-nomination-tests.rs"]
pub(crate) mod tests;
pub const RADIUS_QUAD: f64 = 96.0;
pub const RULE: &str = "frozen-focus-coverage.v1: same36 anchors; existing4quad lattice within Linf96; both covered+usable focus masks; squared nominal displacement then y,x; A first original,B first three distinct originals; first full reciprocal/ancestor/old-held/nonoverlap-valid candidate in anchor order; no post-native retry";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Policy {
    Fixed,
    FocusCoverage,
}

pub struct Planning<'a> {
    pub upstream: &'a str,
    pub evidence: &'a str,
    pub grids: &'a [AnchorGrid; 2],
    pub ancestors: &'a [AncestorFootprint],
}

fn coordinate(guide: &MosaicGuide, p: [f64; 2]) -> Option<(usize, usize, usize)> {
    let q = [0, 1].map(|axis| ((p[axis] - guide.origin[axis]) / guide.step as f64).round());
    if !q.into_iter().all(f64::is_finite)
        || q[0] < 0.
        || q[1] < 0.
        || q[0] >= guide.geometry.width as f64
        || q[1] >= guide.geometry.height as f64
    {
        return None;
    }
    let (x, y) = (q[0] as usize, q[1] as usize);
    Some((x, y, y * guide.geometry.width + x))
}
fn predict(seed: Similarity, p: [f64; 2], guide: &MosaicGuide) -> [f64; 2] {
    let q = seed.apply_at(
        p[0],
        p[1],
        guide.source_geometry.width as f64 * 0.5,
        guide.source_geometry.height as f64 * 0.5,
    );
    [q.0, q.1]
}
fn eligible(guides: &[MosaicGuide], seed: Similarity, anchor: [f64; 2]) -> Vec<[f64; 2]> {
    let guide = &guides[0];
    let mut candidates = Vec::new();
    let low = [0, 1].map(|i| {
        ((anchor[i] - RADIUS_QUAD - guide.origin[i]) / guide.step as f64)
            .ceil()
            .max(0.) as usize
    });
    let high = [0, 1].map(|i| {
        ((anchor[i] + RADIUS_QUAD - guide.origin[i]) / guide.step as f64)
            .floor()
            .max(0.) as usize
    });
    for y in low[1]..=high[1].min(guide.geometry.height - 1) {
        for x in low[0]..=high[0].min(guide.geometry.width - 1) {
            let index = y * guide.geometry.width + x;
            if !guide.covered[index] || !guide.usable_focus[index] {
                continue;
            }
            let p = guide.full_point([x as f64, y as f64]);
            let q = predict(seed, p, guide);
            let Some((_, _, other)) = coordinate(&guides[1], q) else {
                continue;
            };
            if guides[1].covered[other] && guides[1].usable_focus[other] {
                candidates.push(p);
            }
        }
    }
    candidates.sort_by(|a, b| {
        let distance = |p: &[f64; 2]| (p[0] - anchor[0]).powi(2) + (p[1] - anchor[1]).powi(2);
        distance(a)
            .total_cmp(&distance(b))
            .then(a[1].total_cmp(&b[1]))
            .then(a[0].total_cmp(&b[0]))
    });
    candidates
}
fn physical_cell(guide: &MosaicGuide, p: [f64; 2], config: &MosaicGeometryConfig) -> [usize; 2] {
    let size = [guide.source_geometry.width, guide.source_geometry.height];
    [0, 1].map(|axis| {
        let cells = size[axis].div_ceil(config.mesh_cell_quad_pixels);
        ((p[axis] * cells as f64 / (size[axis] - 1) as f64)
            .floor()
            .max(0.) as usize)
            .min(cells - 1)
    })
}
fn proposal_at(
    guides: &[MosaicGuide],
    maps: &[WarpMap],
    config: &MosaicGeometryConfig,
    seed: Similarity,
    id: String,
    p: [f64; 2],
) -> Result<Option<(IslandProposal, Value)>> {
    let q = predict(seed, p, &guides[0]);
    let witnesses = [
        original_witnesses(&guides[0], &maps[0], p, 1),
        original_witnesses(&guides[1], &maps[1], q, 3),
    ];
    if witnesses.iter().any(Vec::is_empty) {
        return Ok(None);
    }
    let focus:Vec<_>=[p,q].iter().enumerate().map(|(pass,&point)| {
        let (x,y,index)=coordinate(&guides[pass],point).expect("covered witness coordinate");
        json!({"pass":pass,"query_guide_xy":[x,y],"covered":guides[pass].covered[index],"focus_usable":guides[pass].usable_focus[index],"ordinal":guides[pass].focus_ordinal[index],"width":guides[pass].focus_width[index],"sources":witnesses[pass]})
    }).collect();
    let mut own = [0_f64; 2];
    for pass in 0..2 {
        for id in &witnesses[pass] {
            let inv = maps[pass].warps()[*id]
                .placed()
                .unwrap()
                .invert()
                .context("singular original witness")?;
            let halo = if config.native_lowpass { 2. } else { 0. };
            let radius =
                (config.native_tile as f64 + f64::from(config.native_search_radius) + 3. + halo)
                    * (inv.a.re.abs() + inv.a.im.abs());
            own[pass] = own[pass].max(radius);
        }
    }
    let inverse = seed.invert().context("singular initial cross-view seed")?;
    let forward = seed.a.re.abs() + seed.a.im.abs();
    let reverse = inverse.a.re.abs() + inverse.a.im.abs();
    let uncertainty = config.coarse_residual_guide_pixels * guides[0].step as f64;
    let radii = [
        own[0].max(own[1] * reverse) + uncertainty * reverse,
        own[1].max(own[0] * forward),
    ];
    let cell = physical_cell(&guides[0], p, config);
    let metadata = json!({"id":id,"reference_quad":p,"moving_quad":q,"physical_mesh_cell":cell,"focus":focus,"query_radius_quad":radii,"target_extra_uncertainty_quad":uncertainty,"semantics":"Frozen original search witnesses and conditional focus-mask selection; no depth, native quality or join certificate."});
    Ok(Some((
        IslandProposal {
            id,
            cell,
            reference_center_quad: p,
            original_witnesses: witnesses,
            query_radius_quad: radii,
        },
        metadata,
    )))
}

pub fn propose(
    guides: &[MosaicGuide],
    maps: &[WarpMap],
    config: &MosaicGeometryConfig,
    seed: [f64; 4],
    policy: Policy,
    planning: Planning<'_>,
) -> Result<(Vec<IslandProposal>, Vec<Value>, Vec<Value>)> {
    ensure!(
        policy == Policy::Fixed || guides.iter().all(|g| g.step == 4),
        "focus-nominated commissioning requires the frozen4quad guide lattice"
    );
    let transform = Similarity {
        a: strehl_core::align::Cx::new(seed[0], seed[1]),
        b: strehl_core::align::Cx::new(seed[2], seed[3]),
    };
    let side = config.holdout_block_guide_pixels * guides[0].step;
    let source = guides[0].source_geometry;
    let mut proposals = Vec::new();
    let mut absent = Vec::new();
    let mut receipts = Vec::new();
    for by in 0..source.height.div_ceil(side) {
        for bx in 0..source.width.div_ceil(side) {
            if !(bx + by).is_multiple_of(3) {
                continue;
            }
            for (slot, fraction) in [[144., 144.], [368., 144.], [256., 368.]]
                .iter()
                .enumerate()
            {
                let anchor = [
                    guides[0].origin[0]
                        + bx as f64 * side as f64
                        + fraction[0] / 512. * side as f64,
                    guides[0].origin[1]
                        + by as f64 * side as f64
                        + fraction[1] / 512. * side as f64,
                ];
                let id = format!("island-{bx}-{by}-{slot}");
                let candidates = if policy == Policy::Fixed {
                    vec![anchor]
                } else {
                    eligible(guides, transform, anchor)
                };
                let mut failures = Vec::new();
                let mut selected = None;
                for (rank, &p) in candidates.iter().enumerate() {
                    let Some((proposal, metadata)) =
                        proposal_at(guides, maps, config, transform, id.clone(), p)?
                    else {
                        failures.push(json!({"rank":rank,"point_quad":p,"reason":"no covered original witness"}));
                        continue;
                    };
                    if policy == Policy::FocusCoverage {
                        let mut trial = proposals.clone();
                        trial.push(proposal.clone());
                        let check = RolePlan::build(
                            planning.upstream.into(),
                            planning.evidence.into(),
                            (*planning.grids).clone(),
                            seed,
                            config.coarse_residual_guide_pixels * guides[0].step as f64,
                            planning.ancestors.to_vec(),
                            trial,
                        )?;
                        if let Some(refused) = check.refused.iter().find(|r| r.proposal.id == id) {
                            failures
                                .push(json!({"rank":rank,"point_quad":p,"reason":refused.reason}));
                            continue;
                        }
                    }
                    proposals.push(proposal);
                    selected = Some(
                        json!({"rank":rank,"nominal_displacement_quad":[p[0]-anchor[0],p[1]-anchor[1]],"witness":metadata}),
                    );
                    break;
                }
                if selected.is_none() {
                    absent.push(json!({"id":id,"nominal_reference_quad":anchor,"candidate_count":candidates.len(),"reason":"no candidate satisfies frozen focus/source/geometric reservation rules"}));
                }
                receipts.push(json!({"id":id,"nominal_reference_quad":anchor,"nominal_mesh_cell":physical_cell(&guides[0],anchor,config),"policy":format!("{policy:?}"),"ranked_candidates_quad":candidates,"geometric_refusals":failures,"selected":selected,"native_retry_policy":"none"}));
            }
        }
    }
    Ok((proposals, absent, receipts))
}
