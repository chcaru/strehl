//! Conservative anchor-relative local consistency, not statistical uncertainty.
//! No chained corrections: every admitted source has a measured direct anchor
//! edge and belongs to an independently measured closed triangle in each color.
use super::local_registration::{PairEvidence, PlaneKind, plane_pull};
use strehl_core::{
    align::{Cx, Similarity},
    plane::PlaneGeometry,
};
#[derive(Clone, Copy)]
pub struct Node {
    pub acquisition: u64,
    pub color_pulls: [Similarity; 3],
}
#[derive(Clone, Copy)]
pub struct Domain {
    pub full: PlaneGeometry,
    pub corners_sensor: [[f64; 2]; 4],
}
#[derive(Clone, Copy)]
pub struct Policy {
    pub maximum_pair_error_sensor: f64,
    pub maximum_cycle_error_sensor: f64,
    pub minimum_heldout: usize,
}
impl Default for Policy {
    fn default() -> Self {
        Self {
            maximum_pair_error_sensor: 0.15,
            maximum_cycle_error_sensor: 0.15,
            minimum_heldout: 4,
        }
    }
}
#[derive(Debug)]
pub struct SourceCertificate {
    pub acquisition: u64,
    /// Relative to the explicitly chosen local native anchor; not a probability.
    pub admitted_rgb: [bool; 3],
    pub direct_anchor_max_error_sensor: [f64; 3],
    pub passed_anchor_triangles_rgb: [usize; 3],
}
#[derive(Debug)]
pub struct GraphCertificate {
    pub anchor_acquisition: u64,
    pub sources: Vec<SourceCertificate>,
    pub passed_edges_rgb: [usize; 3],
    pub components_rgb: [usize; 3],
    pub cycle_rank_rgb: [usize; 3],
    pub tested_anchor_triangles_rgb: [usize; 3],
    pub passed_anchor_triangles_rgb: [usize; 3],
    pub maximum_cycle_error_sensor_rgb: [f64; 3],
}
fn color(kind: PlaneKind) -> usize {
    match kind {
        PlaneKind::Red => 0,
        PlaneKind::GreenLuma => 1,
        PlaneKind::Blue => 2,
    }
}
fn finite(t: Similarity) -> bool {
    [t.a.re, t.a.im, t.b.re, t.b.im]
        .iter()
        .all(|v| v.is_finite())
        && t.invert().is_some()
}
fn same_pull(a: Similarity, b: Similarity) -> bool {
    [a.a.re, a.a.im, a.b.re, a.b.im].map(f64::to_bits)
        == [b.a.re, b.a.im, b.b.re, b.b.im].map(f64::to_bits)
}
fn corners(node: &Node, c: usize, domain: Domain) -> [(f64, f64); 4] {
    let kind = [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue][c];
    let site = match kind {
        PlaneKind::Red => [0., 0.],
        PlaneKind::GreenLuma => [0.5, 0.5],
        PlaneKind::Blue => [1., 1.],
    };
    let pull = plane_pull(node.color_pulls[c], kind);
    domain.corners_sensor.map(|p| {
        pull.apply_at(
            (p[0] - site[0]) * 0.5,
            (p[1] - site[1]) * 0.5,
            domain.full.width as f64 * 0.5,
            domain.full.height as f64 * 0.5,
        )
    })
}
fn within_heldout_bounds(pair: &PairEvidence, node: &Node, c: usize, domain: Domain) -> bool {
    let minx = pair
        .heldout_tiles
        .iter()
        .map(|h| h.reference_quad_global[0])
        .fold(f64::INFINITY, f64::min);
    let miny = pair
        .heldout_tiles
        .iter()
        .map(|h| h.reference_quad_global[1])
        .fold(f64::INFINITY, f64::min);
    let maxx = pair
        .heldout_tiles
        .iter()
        .map(|h| h.reference_quad_global[0])
        .fold(f64::NEG_INFINITY, f64::max);
    let maxy = pair
        .heldout_tiles
        .iter()
        .map(|h| h.reference_quad_global[1])
        .fold(f64::NEG_INFINITY, f64::max);
    corners(node, c, domain)
        .iter()
        .all(|p| p.0 >= minx && p.0 <= maxx && p.1 >= miny && p.1 <= maxy)
}
fn edge_error(e: &PairEvidence) -> f64 {
    e.heldout_tiles
        .iter()
        .map(|h| h.saved_error_anchor_sensor[0].hypot(h.saved_error_anchor_sensor[1]))
        .fold(0., f64::max)
}
fn components(edges: &[Vec<Option<Similarity>>]) -> usize {
    let mut seen = vec![false; edges.len()];
    let mut count = 0;
    for seed in 0..edges.len() {
        if seen[seed] {
            continue;
        }
        count += 1;
        seen[seed] = true;
        let mut pending = vec![seed];
        while let Some(i) = pending.pop() {
            for j in 0..edges.len() {
                if !seen[j] && edges[i][j].is_some() {
                    seen[j] = true;
                    pending.push(j);
                }
            }
        }
    }
    count
}
pub fn certify(
    nodes: &[Node],
    anchor: usize,
    domain: Domain,
    pairs: &[PairEvidence],
    policy: Policy,
) -> Result<GraphCertificate, String> {
    let n = nodes.len();
    if !(3..=18).contains(&n)
        || anchor >= n
        || domain.full.width == 0
        || domain.full.height == 0
        || domain
            .corners_sensor
            .iter()
            .flatten()
            .any(|v| !v.is_finite())
        || policy.minimum_heldout < 4
        || ![
            policy.maximum_pair_error_sensor,
            policy.maximum_cycle_error_sensor,
        ]
        .iter()
        .all(|v| v.is_finite() && *v > 0.)
    {
        return Err("invalid local graph domain/policy".into());
    }
    for (i, node) in nodes.iter().enumerate() {
        if nodes[..i].iter().any(|p| p.acquisition == node.acquisition)
            || !node.color_pulls.iter().all(|t| finite(*t))
        {
            return Err("duplicate acquisition or invalid pull".into());
        }
    }
    let mut edges: Vec<Vec<Vec<Option<Similarity>>>> =
        (0..3).map(|_| vec![vec![None; n]; n]).collect();
    let mut errors = vec![vec![vec![f64::INFINITY; n]; n]; 3];
    let mut observed = vec![vec![vec![false; n]; n]; 3];
    let mut edge_counts = [0; 3];
    for pair in pairs {
        let i = nodes
            .iter()
            .position(|node| node.acquisition == pair.acquisitions[0])
            .ok_or("unknown graph acquisition")?;
        let j = nodes
            .iter()
            .position(|node| node.acquisition == pair.acquisitions[1])
            .ok_or("unknown graph acquisition")?;
        let c = color(pair.plane);
        if pair.window.full != domain.full
            || !same_pull(pair.input_color_pulls[0], nodes[i].color_pulls[c])
            || !same_pull(pair.input_color_pulls[1], nodes[j].color_pulls[c])
        {
            return Err("pair evidence coordinate/placement binding mismatch".into());
        }
        if i == j || observed[c][i][j] {
            return Err("duplicate pair/color evidence".into());
        }
        observed[c][i][j] = true;
        observed[c][j][i] = true;
        if pair.heldout_tiles.len() < policy.minimum_heldout
            || pair.trained_tiles < 4
            || !pair.saved_map_supported
            || pair
                .heldout_tiles
                .iter()
                .any(|h| h.saved_error_anchor_sensor.iter().any(|x| !x.is_finite()))
        {
            continue;
        }
        if pair
            .heldout_tiles
            .iter()
            .any(|h| h.reference_quad_global.iter().any(|v| !v.is_finite()))
            || !within_heldout_bounds(pair, &nodes[i], c, domain)
        {
            continue;
        }
        let error = edge_error(pair);
        if error > policy.maximum_pair_error_sensor {
            continue;
        }
        let Some(t) = pair.fitted_pair_global.filter(|t| finite(*t)) else {
            continue;
        };
        edges[c][i][j] = Some(t);
        edges[c][j][i] = t.invert();
        errors[c][i][j] = error;
        errors[c][j][i] = error;
        edge_counts[c] += 1;
    }
    let mut result = GraphCertificate {
        anchor_acquisition: nodes[anchor].acquisition,
        sources: nodes
            .iter()
            .map(|n| SourceCertificate {
                acquisition: n.acquisition,
                admitted_rgb: [false; 3],
                direct_anchor_max_error_sensor: [f64::INFINITY; 3],
                passed_anchor_triangles_rgb: [0; 3],
            })
            .collect(),
        passed_edges_rgb: edge_counts,
        components_rgb: [0; 3],
        cycle_rank_rgb: [0; 3],
        tested_anchor_triangles_rgb: [0; 3],
        passed_anchor_triangles_rgb: [0; 3],
        maximum_cycle_error_sensor_rgb: [0.; 3],
    };
    for c in 0..3 {
        result.components_rgb[c] = components(&edges[c]);
        result.cycle_rank_rgb[c] = edge_counts[c] + result.components_rgb[c] - n;
        let kind = [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue][c];
        let anchor_pull = plane_pull(nodes[anchor].color_pulls[c], kind);
        let inverse = anchor_pull.invert().ok_or("invalid anchor pull")?;
        let site = match kind {
            PlaneKind::Red => [0., 0.],
            PlaneKind::GreenLuma => [0.5, 0.5],
            PlaneKind::Blue => [1., 1.],
        };
        let center = [
            domain.full.width as f64 * 0.5,
            domain.full.height as f64 * 0.5,
        ];
        let anchor_points = domain.corners_sensor.map(|p| {
            anchor_pull.apply_at(
                (p[0] - site[0]) * 0.5,
                (p[1] - site[1]) * 0.5,
                center[0],
                center[1],
            )
        });
        result.sources[anchor].direct_anchor_max_error_sensor[c] = 0.;
        for i in 0..n {
            if i != anchor {
                result.sources[i].direct_anchor_max_error_sensor[c] = errors[c][anchor][i];
            }
        }
        for i in 0..n {
            if i == anchor {
                continue;
            }
            for j in i + 1..n {
                if j == anchor {
                    continue;
                }
                let (Some(a), Some(b), Some(d)) =
                    (edges[c][anchor][i], edges[c][i][j], edges[c][j][anchor])
                else {
                    continue;
                };
                result.tested_anchor_triangles_rgb[c] += 1;
                let closure = a.then(b).then(d);
                let error = anchor_points
                    .iter()
                    .map(|p| {
                        let q = closure.apply_at(p.0, p.1, center[0], center[1]);
                        (inverse.a * Cx::new(q.0 - p.0, q.1 - p.1)).abs() * 2.
                    })
                    .fold(0., f64::max);
                result.maximum_cycle_error_sensor_rgb[c] =
                    result.maximum_cycle_error_sensor_rgb[c].max(error);
                if error <= policy.maximum_cycle_error_sensor {
                    result.passed_anchor_triangles_rgb[c] += 1;
                    for source in [anchor, i, j] {
                        result.sources[source].admitted_rgb[c] = true;
                        result.sources[source].passed_anchor_triangles_rgb[c] += 1;
                    }
                }
            }
        }
    }
    Ok(result)
}
#[cfg(test)]
#[path = "local-registration-graph-tests.rs"]
mod tests;
