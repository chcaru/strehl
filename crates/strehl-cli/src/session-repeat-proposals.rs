//! Research-only geometric repeat proposals. No PSF or source admission claim.
//! The ordinary per-coefficient repeat consumer remains the actual estimator.
use crate::session_align::EdgeReceipt;
use anyhow::{Context, Result, ensure};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

pub const RESERVATION_BYTES: usize = 64 << 20;
const MAX_PER_PASS: usize = 64;

#[derive(Clone, Debug, Serialize)]
pub struct Source {
    pub index: usize,
    pub pass: usize,
    pub sha256: String,
    pub log_scale: f64,
}
#[derive(Debug, Serialize)]
pub struct Proxy {
    pub source: Source,
    pub incident_native_edges: usize,
    pub incident_triangles: usize,
    pub rms_over_lever_q75: Option<f64>,
    pub cycle_log_scale_q95: Option<f64>,
    pub uncertainty_proxy: Option<f64>,
}
#[derive(Debug, Serialize)]
pub struct Proposal {
    pub sources: [usize; 2],
    pub log_scale_gap: f64,
    pub radius: Option<f64>,
    pub direct_native_edge: bool,
    pub nominated: bool,
    pub cost: Option<u32>,
}
#[derive(Debug, Serialize)]
pub struct Plan {
    pub schema: &'static str,
    pub basis: &'static str,
    pub scope: &'static str,
    pub objective: &'static str,
    pub old_radius: f64,
    pub sources: Vec<Proxy>,
    pub proposals: Vec<Proposal>,
    pub groups: Vec<Vec<usize>>,
    pub matched_pairs: usize,
    pub total_cost: u64,
    pub reservation_bytes: usize,
}
fn quantile(values: &mut [f64], p: f64) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    values.sort_by(f64::total_cmp);
    Some(values[((p * values.len() as f64).ceil() as usize).saturating_sub(1)])
}
#[derive(Clone)]
struct Arc {
    to: usize,
    reverse: usize,
    capacity: bool,
    cost: i64,
}
fn arc(graph: &mut [Vec<Arc>], a: usize, b: usize, cost: i64) -> usize {
    let i = graph[a].len();
    let j = graph[b].len();
    graph[a].push(Arc {
        to: b,
        reverse: j,
        capacity: true,
        cost,
    });
    graph[b].push(Arc {
        to: a,
        reverse: i,
        capacity: false,
        cost: -cost,
    });
    i
}
fn assignment(
    a: &[usize],
    b: &[usize],
    costs: &BTreeMap<(usize, usize), u32>,
) -> Result<(Vec<[usize; 2]>, u64)> {
    let n = a.len() + b.len() + 2;
    let start = n - 2;
    let end = n - 1;
    let mut graph = vec![Vec::new(); n];
    for i in 0..a.len() {
        arc(&mut graph, start, i, 0);
    }
    for j in 0..b.len() {
        arc(&mut graph, a.len() + j, end, 0);
    }
    let mut candidates = Vec::new();
    for (i, &x) in a.iter().enumerate() {
        for (j, &y) in b.iter().enumerate() {
            if let Some(&cost) = costs.get(&(x.min(y), x.max(y))) {
                let edge = arc(&mut graph, i, a.len() + j, i64::from(cost));
                candidates.push(([x, y], i, edge, cost));
            }
        }
    }
    loop {
        let mut distance = vec![i64::MAX; n];
        let mut predecessor = vec![None; n];
        distance[start] = 0;
        for _ in 0..n - 1 {
            let mut changed = false;
            for u in 0..n {
                if distance[u] == i64::MAX {
                    continue;
                }
                for (e, edge) in graph[u].iter().enumerate() {
                    if !edge.capacity {
                        continue;
                    }
                    let d = distance[u]
                        .checked_add(edge.cost)
                        .context("proposal cost overflow")?;
                    if d < distance[edge.to] {
                        distance[edge.to] = d;
                        predecessor[edge.to] = Some((u, e));
                        changed = true;
                    }
                }
            }
            if !changed {
                break;
            }
        }
        if predecessor[end].is_none() {
            break;
        }
        let mut v = end;
        let mut steps = 0;
        while v != start {
            let (u, e) = predecessor[v].context("broken proposal augmentation")?;
            let reverse = graph[u][e].reverse;
            graph[u][e].capacity = false;
            graph[v][reverse].capacity = true;
            v = u;
            steps += 1;
            ensure!(steps < n, "cyclic proposal augmentation");
        }
    }
    let mut pairs = Vec::new();
    let mut cost = 0;
    for (mut pair, u, e, c) in candidates {
        if !graph[u][e].capacity {
            pair.sort();
            pairs.push(pair);
            cost += u64::from(c);
        }
    }
    pairs.sort();
    Ok((pairs, cost))
}

/// Freeze proposals from GEOMETRY ONLY. Every input source is retained exactly
/// once as a pair member or singleton. Unknown proxy does not nominate an edge.
/// The bound applies to this whole experiment; it never truncates a deep sweep.
pub fn plan(
    sources: &[Source],
    edges: &[EdgeReceipt],
    old_radius: f64,
    budget: usize,
) -> Result<Plan> {
    ensure!(
        budget >= RESERVATION_BYTES,
        "repeat proposal reservation exceeds budget"
    );
    ensure!(
        !sources.is_empty() && sources.len() <= 2 * MAX_PER_PASS,
        "proposal experiment needs at most64 sources per pass; no truncation"
    );
    ensure!(
        old_radius.is_finite() && old_radius >= 0.,
        "invalid old proposal radius"
    );
    let mut ids = BTreeSet::new();
    let mut indices = BTreeMap::new();
    let mut passes = BTreeSet::new();
    for (local, s) in sources.iter().enumerate() {
        ensure!(
            s.sha256.len() == 64
                && s.sha256.bytes().all(|c| c.is_ascii_hexdigit())
                && ids.insert(s.sha256.to_ascii_lowercase()),
            "invalid or duplicated original identity"
        );
        ensure!(
            indices.insert(s.index, local).is_none() && s.log_scale.is_finite(),
            "invalid original index/scale"
        );
        passes.insert(s.pass);
    }
    ensure!(
        passes.len() == 2
            && passes
                .iter()
                .all(|p| sources.iter().filter(|s| s.pass == *p).count() <= MAX_PER_PASS),
        "proposal experiment requires two bounded passes"
    );
    let mut incident = vec![Vec::new(); sources.len()];
    let mut cycles = vec![Vec::new(); sources.len()];
    let mut direct = BTreeMap::new();
    for e in edges.iter().filter(|e| e.accepted && e.stage == "native") {
        let (Some(&i), Some(&j)) = (indices.get(&e.i), indices.get(&e.j)) else {
            continue;
        };
        ensure!(e.i < e.j, "unordered original geometry edge");
        let (Some(rms), Some(lever), Some(bits)) =
            (e.rms_plane_px, e.lever_plane_px, e.transform_bits)
        else {
            continue;
        };
        ensure!(
            rms.is_finite() && rms >= 0. && lever.is_finite() && lever > 0.,
            "invalid measured geometry proxy"
        );
        let scale = f64::from_bits(bits[0]).hypot(f64::from_bits(bits[1])).ln();
        ensure!(scale.is_finite(), "invalid measured edge scale");
        ensure!(
            direct.insert((e.i, e.j), scale).is_none(),
            "duplicate native geometry edge"
        );
        let ratio = rms / lever;
        ensure!(ratio.is_finite(), "geometry proxy division overflow");
        incident[i].push(ratio);
        incident[j].push(ratio);
    }
    let mut ordered: Vec<_> = sources.iter().map(|s| s.index).collect();
    ordered.sort();
    for (pi, &i) in ordered.iter().enumerate() {
        for (pj, &j) in ordered.iter().enumerate().skip(pi + 1) {
            let Some(ij) = direct.get(&(i, j)) else {
                continue;
            };
            for &k in ordered.iter().skip(pj + 1) {
                if let (Some(jk), Some(ik)) = (direct.get(&(j, k)), direct.get(&(i, k))) {
                    let closure = (ij + jk - ik).abs();
                    for index in [i, j, k] {
                        cycles[indices[&index]].push(closure);
                    }
                }
            }
        }
    }
    let rows: Vec<_> = sources
        .iter()
        .enumerate()
        .map(|(i, s)| {
            let ec = incident[i].len();
            let tc = cycles[i].len();
            let r = quantile(&mut incident[i], 0.75);
            let c = quantile(&mut cycles[i], 0.95);
            Proxy {
                source: s.clone(),
                incident_native_edges: ec,
                incident_triangles: tc,
                rms_over_lever_q75: r,
                cycle_log_scale_q95: c,
                uncertainty_proxy: if ec >= 3 && tc >= 1 {
                    r.zip(c).map(|(x, y)| x + y)
                } else {
                    None
                },
            }
        })
        .collect();
    let mut proposals = Vec::new();
    let mut costs = BTreeMap::new();
    for (i, x) in rows.iter().enumerate() {
        for y in rows.iter().skip(i + 1) {
            if x.source.pass == y.source.pass {
                continue;
            }
            let pair = (
                x.source.index.min(y.source.index),
                x.source.index.max(y.source.index),
            );
            let gap = (x.source.log_scale - y.source.log_scale).abs();
            ensure!(gap.is_finite(), "proposal scale gap overflow");
            let radius = x
                .uncertainty_proxy
                .zip(y.uncertainty_proxy)
                .map(|(a, b)| old_radius.max(a + b));
            ensure!(radius.is_none_or(f64::is_finite), "proposal proxy overflow");
            let available = direct.contains_key(&pair);
            let nominated = available && radius.is_some_and(|r| gap <= r);
            let cost = radius.map(|r| {
                if r == 0. {
                    0
                } else {
                    (1e6 * (gap / r).powi(2)).round().min(u32::MAX as f64) as u32
                }
            });
            if nominated {
                costs.insert(pair, cost.context("nominated proposal lacks cost")?);
            }
            proposals.push(Proposal {
                sources: [pair.0, pair.1],
                log_scale_gap: gap,
                radius,
                direct_native_edge: available,
                nominated,
                cost,
            });
        }
    }
    // Canonical content order also fixes equal-cost assignment and pass reversal.
    let mut canonical: Vec<_> = sources.iter().collect();
    canonical.sort_by_key(|s| s.sha256.to_ascii_lowercase());
    let first = canonical[0].pass;
    let a: Vec<_> = canonical
        .iter()
        .filter(|s| s.pass == first)
        .map(|s| s.index)
        .collect();
    let b: Vec<_> = canonical
        .iter()
        .filter(|s| s.pass != first)
        .map(|s| s.index)
        .collect();
    let (pairs, total_cost) = assignment(&a, &b, &costs)?;
    let used: BTreeSet<_> = pairs.iter().flatten().copied().collect();
    let mut groups: Vec<Vec<usize>> = pairs.iter().map(|p| p.to_vec()).collect();
    groups.extend(
        sources
            .iter()
            .filter(|s| !used.contains(&s.index))
            .map(|s| vec![s.index]),
    );
    groups.sort_by_key(|g| g[0]);
    proposals.sort_by_key(|p| p.sources);
    Ok(Plan {
        schema: "strehl.repeat-geometry-proposals.v1",
        basis: "GeometryProposal",
        scope: "Nomination only. No calibrated scale uncertainty, PSF equality, focus peak, RepeatCompatible admission or SR eligibility. Native coefficient gates and fallback remain unchanged.",
        objective: "Maximum pair count, then minimum summed round(1e6*(scale_gap/radius)^2); not optimal photographic quality.",
        old_radius,
        sources: rows,
        proposals,
        groups,
        matched_pairs: pairs.len(),
        total_cost,
        reservation_bytes: RESERVATION_BYTES,
    })
}

#[cfg(test)]
#[path = "session-repeat-proposals-oracle-tests.rs"]
mod oracle_tests;
#[cfg(test)]
#[path = "session-repeat-proposals-tests.rs"]
mod tests;
