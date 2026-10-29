//! Experiment-only direct global training fit with graph-wide original holdout.
//! Equal fixed edge weights, no smoothness prior, no held-out residual fitting.
use super::{local_registration as reg, local_registration_graph as graph};
use strehl_core::{
    align::{
        AlignEdge, Cx, GlobalOptions, Similarity, Weighting, graph_stats, solve_global_in_component,
    },
    plane::PlaneGeometry,
};
type Result<T> = std::result::Result<T, String>;
pub struct Corrected {
    pub certificate: graph::GraphCertificate,
    pub pairs: Vec<reg::PairEvidence>,
    pub training_edges_rgb: [usize; 3],
    pub training_cycle_rank_rgb: [usize; 3],
    pub reservation_bytes: usize,
}
fn color(c: reg::PlaneKind) -> usize {
    match c {
        reg::PlaneKind::Red => 0,
        reg::PlaneKind::GreenLuma => 1,
        reg::PlaneKind::Blue => 2,
    }
}
fn kind(c: usize) -> reg::PlaneKind {
    [
        reg::PlaneKind::Red,
        reg::PlaneKind::GreenLuma,
        reg::PlaneKind::Blue,
    ][c]
}
fn site(c: usize) -> Cx {
    let s = [-0.25, 0., 0.25][c];
    Cx::new(s, s)
}
fn guide_pull(t: Similarity, c: usize) -> Similarity {
    Similarity {
        a: t.a,
        b: t.b - t.a * site(c) + site(c),
    }
}
fn center_shift(t: Similarity, offset: Cx) -> Similarity {
    Similarity {
        a: t.a,
        b: t.b + t.a * offset - offset,
    }
}
pub fn reservation_bytes(n: usize, pairs: usize, side: usize) -> Result<usize> {
    let witness = reg::OriginalFootprints::reservation_bytes(side)?;
    witness
        .checked_mul(pairs)
        .and_then(|v| v.checked_add(n.checked_mul(3)?.checked_mul(witness / 2)?))
        .and_then(|v| v.checked_add(n.checked_mul(n)?.checked_mul(128)?))
        .and_then(|v| v.checked_add(1 << 20))
        .ok_or_else(|| "global witness budget overflow".into())
}
pub fn solve(
    nodes: &[graph::Node],
    anchor: usize,
    domain: graph::Domain,
    witnessed: &[reg::WitnessedPair],
    policy: graph::Policy,
    budget: usize,
) -> Result<Corrected> {
    let n = nodes.len();
    if !(3..=64).contains(&n) || anchor >= n || witnessed.is_empty() {
        return Err("invalid corrected graph dimensions".into());
    }
    let first = &witnessed[0].evidence;
    let window = first.window;
    let side = window.side_quad;
    let reserved = reservation_bytes(n, witnessed.len(), side)?;
    if reserved > budget || budget > 64 << 20 {
        return Err("global footprint reservation exceeds budget".into());
    }
    // Validate exact node/evidence bindings and duplicate inputs before solving.
    let original_pairs: Vec<_> = witnessed.iter().map(|w| w.evidence.clone()).collect();
    graph::certify(nodes, anchor, domain, &original_pairs, policy)?;
    let words = side
        .checked_mul(side)
        .ok_or("footprint dimensions overflow")?
        .div_ceil(64);
    let mut union: Vec<[Vec<u64>; 2]> = (0..3 * n)
        .map(|_| [vec![0; words], vec![0; words]])
        .collect();
    let mut origins: Vec<Option<[usize; 2]>> = vec![None; 3 * n];
    for w in witnessed {
        let e = &w.evidence;
        let c = color(e.plane);
        if e.window.full != window.full
            || e.window.side_quad != side
            || e.window.center_sensor.map(f64::to_bits) != window.center_sensor.map(f64::to_bits)
            || w.footprints.side_quad != side
        {
            return Err("mixed original footprint domains".into());
        }
        for role in 0..2 {
            let i = nodes
                .iter()
                .position(|v| v.acquisition == e.acquisitions[role])
                .ok_or("unknown footprint acquisition")?;
            let key = c * n + i;
            let origin = e.original_crop_origins[role];
            if origins[key].is_some_and(|old| old != origin) {
                return Err("mixed source crop origins".into());
            }
            origins[key] = Some(origin);
            for (which, mask) in [&w.footprints.training[role], &w.footprints.heldout[role]]
                .into_iter()
                .enumerate()
            {
                if mask.len() != words {
                    return Err("incomplete original footprint witness".into());
                }
                for (a, b) in union[key][which].iter_mut().zip(mask) {
                    *a |= *b;
                }
            }
        }
    }
    if union
        .iter()
        .any(|m| m[0].iter().zip(&m[1]).any(|(a, b)| a & b != 0))
    {
        return Err("graph-wide training and held-out original evidence overlap".into());
    }
    let mut corrected: Vec<_> = nodes
        .iter()
        .map(|v| graph::Node {
            acquisition: v.acquisition,
            color_pulls: v.color_pulls,
        })
        .collect();
    let mut counts = [0; 3];
    let mut ranks = [0; 3];
    for c in 0..3 {
        let offset = Cx::new(
            (window.center_sensor[0] - [0., 0.5, 1.][c]) * 0.5 - domain.full.width as f64 * 0.5,
            (window.center_sensor[1] - [0., 0.5, 1.][c]) * 0.5 - domain.full.height as f64 * 0.5,
        );
        let mut edges = Vec::new();
        for w in witnessed {
            let e = &w.evidence;
            if color(e.plane) != c {
                continue;
            }
            let Some(t) = e.fitted_pair_global else {
                continue;
            };
            let i = nodes
                .iter()
                .position(|v| v.acquisition == e.acquisitions[0])
                .unwrap();
            let j = nodes
                .iter()
                .position(|v| v.acquisition == e.acquisitions[1])
                .unwrap();
            // Fixed weights: held-out outcomes never select or weight a fit.
            edges.push(AlignEdge {
                i,
                j,
                t: center_shift(t, offset),
                rms: f64::from(e.raw_fit_rms_source_quad),
                used: e.trained_tiles,
                lever: 1.,
            });
        }
        let stats = graph_stats(&edges, n);
        counts[c] = stats.n_edges;
        ranks[c] = stats.cycle_rank;
        if stats.cycle_rank == 0 {
            continue;
        }
        let options = GlobalOptions {
            weighting: Weighting::Unit,
            irls_iters: 1,
            smooth: 0.,
            geometry: PlaneGeometry {
                width: side,
                height: side,
            },
            ..GlobalOptions::new(domain.full)
        };
        let solved = solve_global_in_component(&edges, n, &options, anchor)
            .ok_or("direct local graph solve failed")?;
        let a = solved[anchor].ok_or("local anchor unplaced")?;
        let anchored = reg::plane_pull(nodes[anchor].color_pulls[c], kind(c));
        for (i, p) in solved.iter().enumerate() {
            if let Some(p) = p {
                let relative = Similarity::relative(a, *p).ok_or("singular local solve")?;
                let full = center_shift(relative, Cx::new(-offset.re, -offset.im));
                corrected[i].color_pulls[c] = guide_pull(anchored.then(full), c);
            }
        }
        // Keep the explicit anchor bits exactly; it defines the output gauge.
        corrected[anchor].color_pulls[c] = nodes[anchor].color_pulls[c];
    }
    let center = [
        domain.full.width as f64 * 0.5,
        domain.full.height as f64 * 0.5,
    ];
    let mut rescored = original_pairs;
    for e in &mut rescored {
        let c = color(e.plane);
        let i = nodes
            .iter()
            .position(|v| v.acquisition == e.acquisitions[0])
            .unwrap();
        let j = nodes
            .iter()
            .position(|v| v.acquisition == e.acquisitions[1])
            .unwrap();
        e.input_color_pulls = [corrected[i].color_pulls[c], corrected[j].color_pulls[c]];
        let first = reg::plane_pull(e.input_color_pulls[0], e.plane);
        let second = reg::plane_pull(e.input_color_pulls[1], e.plane);
        let relative = Similarity::relative(first, second).ok_or("singular corrected pair")?;
        let inverse = second.invert().ok_or("singular corrected source")?;
        for h in &mut e.heldout_tiles {
            let p = relative.apply_at(
                h.reference_quad_global[0],
                h.reference_quad_global[1],
                center[0],
                center[1],
            );
            let d = inverse.a
                * Cx::new(
                    h.measured_moving_quad_global[0] - p.0,
                    h.measured_moving_quad_global[1] - p.1,
                );
            h.saved_error_anchor_sensor = [2. * d.re, 2. * d.im];
        }
        e.maximum_saved_disagreement_sensor = if e.heldout_tiles.len() >= policy.minimum_heldout {
            e.heldout_tiles
                .iter()
                .map(|h| h.saved_error_anchor_sensor[0].hypot(h.saved_error_anchor_sensor[1]))
                .fold(0., f64::max)
        } else {
            f64::INFINITY
        };
        e.saved_map_supported =
            e.maximum_saved_disagreement_sensor <= policy.maximum_pair_error_sensor;
        e.refusal = (!e.saved_map_supported)
            .then(|| "corrected placement fails held-out local displacement bound".into());
    }
    let certificate = graph::certify(&corrected, anchor, domain, &rescored, policy)?;
    Ok(Corrected {
        certificate,
        pairs: rescored,
        training_edges_rgb: counts,
        training_cycle_rank_rgb: ranks,
        reservation_bytes: reserved,
    })
}
