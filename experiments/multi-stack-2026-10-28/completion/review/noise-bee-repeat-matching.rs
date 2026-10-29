//! Experiment-only bounded two-pass matching. This module never certifies PSF,
//! sharpness, stationarity or geometry. Unknown evidence cannot enter assignment.
//! The64/pass cap is a checked whole-component resource limit, not truncation.
use std::collections::{BTreeMap, BTreeSet};
pub type ContentId = [u8; 32];
#[derive(Clone, Debug)]
pub struct Source {
    pub id: ContentId,
    pub pass: u8,
    pub log_scale: f64,
    pub uncertainty_proxy: Option<f64>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct Pair(pub ContentId, pub ContentId);
impl Pair {
    pub fn new(a: ContentId, b: ContentId) -> Self {
        if a < b { Self(a, b) } else { Self(b, a) }
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NominationReason {
    WithinProxy,
    ScaleSeparated,
    UnknownProxy,
}
#[derive(Clone, Debug)]
pub struct Nomination {
    pub pair: Pair,
    pub reason: NominationReason,
    pub log_scale_gap: f64,
    pub proposal_radius: Option<f64>,
}
#[derive(Clone, Debug)]
pub enum Compatibility {
    /// Cost is fixed-point and bounded. Receipts identify independently qualified
    /// original-observation evidence; their existence is NOT verified by this
    /// graph primitive. A consumer must verify both receipts before constructing.
    Compatible {
        cost: u32,
        geometry_receipt: ContentId,
        compatibility_receipt: ContentId,
    },
    Incompatible,
    Unknown,
}
#[derive(Clone, Debug)]
pub struct Assessment {
    pub pair: Pair,
    pub state: Compatibility,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Matching {
    pub pairs: Vec<Pair>,
    pub unmatched: Vec<ContentId>,
    pub total_cost: u64,
    pub reservation_bytes: usize,
}
const MAX_PER_PASS: usize = 64;
const MAX_COST: u32 = 1_000_000_000;
fn validate(sources: &[Source]) -> Result<(Vec<&Source>, Vec<&Source>), &'static str> {
    if sources.is_empty() || sources.len() > 2 * MAX_PER_PASS {
        return Err("whole component exceeds bounded64/pass solver");
    }
    let mut ids = BTreeSet::new();
    let mut passes = BTreeSet::new();
    for s in sources {
        if s.id == [0; 32] || !ids.insert(s.id) {
            return Err("missing/duplicate original content identity");
        }
        if !s.log_scale.is_finite()
            || s.uncertainty_proxy
                .is_some_and(|u| !u.is_finite() || u < 0.)
        {
            return Err("nonfinite scale/proxy");
        }
        passes.insert(s.pass);
    }
    if passes.len() > 2 {
        return Err("two-pass component required");
    }
    // Canonical orientation depends on CONTENT, not pass labels or caller order.
    let first = sources.iter().min_by_key(|s| s.id).unwrap().pass;
    let mut a: Vec<_> = sources.iter().filter(|s| s.pass == first).collect();
    let mut b: Vec<_> = sources.iter().filter(|s| s.pass != first).collect();
    if a.len() > MAX_PER_PASS || b.len() > MAX_PER_PASS {
        return Err("whole component exceeds bounded64/pass solver");
    }
    a.sort_by_key(|s| s.id);
    b.sort_by_key(|s| s.id);
    Ok((a, b))
}
pub fn reservation_bytes(sources: usize, edges: usize) -> Result<usize, &'static str> {
    if sources > 128 || edges > 4096 {
        return Err("component budget exceeded; never truncate");
    }
    // Conservative bound includes all input assessments, residual arcs, maps,
    // heap/vector overhead and Bellman-Ford state; actual graphs are bounded.
    sources
        .checked_mul(4096)
        .and_then(|v| edges.checked_mul(512).and_then(|e| v.checked_add(e)))
        .and_then(|v| v.checked_add(1 << 20))
        .ok_or("reservation overflow")
}
pub fn nominate(sources: &[Source], old_radius: f64) -> Result<Vec<Nomination>, &'static str> {
    if !old_radius.is_finite() || old_radius < 0. {
        return Err("invalid old proposal radius");
    }
    let (a, b) = validate(sources)?;
    let mut out = Vec::with_capacity(a.len() * b.len());
    for x in &a {
        for y in &b {
            let gap = (x.log_scale - y.log_scale).abs();
            let radius = match (x.uncertainty_proxy, y.uncertainty_proxy) {
                (Some(u), Some(v)) => {
                    let r = old_radius.max(u + v);
                    if !r.is_finite() {
                        return Err("proposal radius overflow");
                    }
                    Some(r)
                }
                _ => None,
            };
            let reason = match radius {
                None => NominationReason::UnknownProxy,
                Some(r) if gap <= r => NominationReason::WithinProxy,
                _ => NominationReason::ScaleSeparated,
            };
            out.push(Nomination {
                pair: Pair::new(x.id, y.id),
                reason,
                log_scale_gap: gap,
                proposal_radius: radius,
            });
        }
    }
    out.sort_by_key(|v| v.pair);
    Ok(out)
}
#[derive(Clone, Debug)]
struct Arc {
    to: usize,
    reverse: usize,
    capacity: bool,
    cost: i64,
}
fn arc(g: &mut [Vec<Arc>], a: usize, b: usize, cost: i64) -> usize {
    let ai = g[a].len();
    let bi = g[b].len();
    g[a].push(Arc {
        to: b,
        reverse: bi,
        capacity: true,
        cost,
    });
    g[b].push(Arc {
        to: a,
        reverse: ai,
        capacity: false,
        cost: -cost,
    });
    ai
}
pub fn assign(
    sources: &[Source],
    old_radius: f64,
    assessments: &[Assessment],
    budget: usize,
) -> Result<Matching, &'static str> {
    let (a, b) = validate(sources)?;
    if assessments.len() > a.len() * b.len() {
        return Err("too many/duplicate assessments");
    }
    let reserve = reservation_bytes(sources.len(), assessments.len())?;
    if reserve > budget {
        return Err("component reservation exceeds budget; no graph allocation/truncation");
    }
    let nominations: BTreeMap<_, _> = nominate(sources, old_radius)?
        .into_iter()
        .map(|v| (v.pair, v.reason))
        .collect();
    let mut assessed = BTreeMap::new();
    for e in assessments {
        if !nominations.contains_key(&e.pair) || assessed.insert(e.pair, &e.state).is_some() {
            return Err("invalid same-pass/unknown/duplicate assessment");
        }
        if let Compatibility::Compatible {
            cost,
            geometry_receipt,
            compatibility_receipt,
        } = &e.state
        {
            if *cost > MAX_COST || *geometry_receipt == [0; 32] || *compatibility_receipt == [0; 32]
            {
                return Err("unbound compatibility/cost");
            }
        }
    }
    let n = a.len() + b.len() + 2;
    let src = n - 2;
    let dst = n - 1;
    let mut g = vec![Vec::new(); n];
    for i in 0..a.len() {
        arc(&mut g, src, i, 0);
    }
    for j in 0..b.len() {
        arc(&mut g, a.len() + j, dst, 0);
    }
    let mut candidates = Vec::new();
    for (i, x) in a.iter().enumerate() {
        for (j, y) in b.iter().enumerate() {
            let pair = Pair::new(x.id, y.id);
            if nominations.get(&pair) != Some(&NominationReason::WithinProxy) {
                continue;
            }
            if let Some(Compatibility::Compatible { cost, .. }) = assessed.get(&pair).copied() {
                let ai = arc(&mut g, i, a.len() + j, i64::from(*cost));
                candidates.push((pair, i, ai, *cost));
            }
        }
    }
    // Successive shortest augmenting paths with negative reverse arcs. Stable
    // node/edge order and strict improvement define equal-cost ties. Continue
    // until no path, giving maximum cardinality before minimum summed cost.
    loop {
        let mut distance = vec![i64::MAX; n];
        let mut predecessor = vec![None; n];
        distance[src] = 0;
        for _ in 0..n - 1 {
            let mut changed = false;
            for u in 0..n {
                if distance[u] == i64::MAX {
                    continue;
                }
                for (ei, e) in g[u].iter().enumerate() {
                    if !e.capacity {
                        continue;
                    }
                    let d = distance[u]
                        .checked_add(e.cost)
                        .ok_or("path cost overflow")?;
                    if d < distance[e.to] {
                        distance[e.to] = d;
                        predecessor[e.to] = Some((u, ei));
                        changed = true;
                    }
                }
            }
            if !changed {
                break;
            }
        }
        if predecessor[dst].is_none() {
            break;
        }
        let mut v = dst;
        let mut count = 0;
        while v != src {
            let (u, ei) = predecessor[v].ok_or("broken augmentation")?;
            let rev = g[u][ei].reverse;
            g[u][ei].capacity = false;
            g[v][rev].capacity = true;
            v = u;
            count += 1;
            if count >= n {
                return Err("cyclic augmentation");
            }
        }
    }
    let mut pairs = Vec::new();
    let mut used = BTreeSet::new();
    let mut total_cost = 0u64;
    for (pair, u, ei, cost) in candidates {
        if !g[u][ei].capacity {
            pairs.push(pair);
            used.insert(pair.0);
            used.insert(pair.1);
            total_cost += u64::from(cost);
        }
    }
    pairs.sort();
    let mut unmatched: Vec<_> = sources
        .iter()
        .filter(|s| !used.contains(&s.id))
        .map(|s| s.id)
        .collect();
    unmatched.sort();
    Ok(Matching {
        pairs,
        unmatched,
        total_cost,
        reservation_bytes: reserve,
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    fn id(n: u8) -> ContentId {
        [n; 32]
    }
    fn s(n: u8, pass: u8) -> Source {
        Source {
            id: id(n),
            pass,
            log_scale: 0.,
            uncertainty_proxy: Some(1e-4),
        }
    }
    fn e(a: u8, b: u8, cost: u32) -> Assessment {
        Assessment {
            pair: Pair::new(id(a), id(b)),
            state: Compatibility::Compatible {
                cost,
                geometry_receipt: id(250),
                compatibility_receipt: id(251),
            },
        }
    }
    fn go(s: &[Source], e: &[Assessment]) -> Matching {
        assign(s, 0., e, 8 << 20).unwrap()
    }
    #[test]
    fn flat_unknown_never_becomes_an_assignment() {
        let s = [s(1, 0), s(2, 1)];
        let e = [Assessment {
            pair: Pair::new(id(1), id(2)),
            state: Compatibility::Unknown,
        }];
        assert!(go(&s, &e).pairs.is_empty());
        assert_eq!(go(&s, &[]).unmatched.len(), 2);
    }
    #[test]
    fn augmenting_path_recovers_pair_lost_by_greedy() {
        let s = [s(1, 0), s(2, 0), s(3, 1), s(4, 1)];
        let e = [e(1, 3, 0), e(1, 4, 100), e(2, 3, 0)];
        let m = go(&s, &e);
        assert_eq!(
            m.pairs,
            vec![Pair::new(id(1), id(4)), Pair::new(id(2), id(3))]
        );
        assert_eq!(m.total_cost, 100);
    }
    #[test]
    fn minimum_total_cost_after_maximum_cardinality() {
        let s = [s(1, 0), s(2, 0), s(3, 1), s(4, 1)];
        let m = go(&s, &[e(1, 3, 4), e(1, 4, 1), e(2, 3, 2), e(2, 4, 8)]);
        assert_eq!(m.total_cost, 3);
        assert_eq!(m.pairs.len(), 2);
    }
    #[test]
    fn pass_swap_source_and_edge_permutation_are_equivalent() {
        let mut s = vec![s(1, 0), s(2, 0), s(3, 1), s(4, 1)];
        let mut e = vec![e(1, 3, 0), e(1, 4, 0), e(2, 3, 0), e(2, 4, 0)];
        let a = go(&s, &e);
        s.reverse();
        e.reverse();
        for x in &mut s {
            x.pass = 1 - x.pass;
        }
        assert_eq!(go(&s, &e), a);
    }
    #[test]
    fn scale_uncertainty_only_nominates_not_admits() {
        let mut s = [s(1, 0), s(2, 1)];
        s[1].log_scale = 1e-3;
        assert_eq!(
            nominate(&s, 0.).unwrap()[0].reason,
            NominationReason::ScaleSeparated
        );
        assert!(go(&s, &[e(1, 2, 0)]).pairs.is_empty());
        s[1].uncertainty_proxy = Some(0.1);
        assert_eq!(
            nominate(&s, 0.).unwrap()[0].reason,
            NominationReason::WithinProxy
        );
        assert!(go(&s, &[]).pairs.is_empty());
    }
    #[test]
    fn malformed_identity_role_cost_and_budget_refuse() {
        let mut a = s(1, 0);
        assert!(assign(&[a.clone(), s(1, 1)], 0., &[], 8 << 20).is_err());
        a.log_scale = f64::NAN;
        assert!(assign(&[a, s(2, 1)], 0., &[], 8 << 20).is_err());
        let s = [s(1, 0), s(2, 0), s(3, 1)];
        assert!(assign(&s, 0., &[e(1, 2, 0)], 8 << 20).is_err());
        assert!(assign(&s, 0., &[e(1, 3, u32::MAX)], 8 << 20).is_err());
        assert!(assign(&s, 0., &[e(1, 3, 0), e(1, 3, 0)], 8 << 20).is_err());
        assert!(assign(&s, 0., &[], 1).is_err());
    }
    #[test]
    fn full64_by64_component_is_bounded_and_complete() {
        let s: Vec<_> = (1..=128).map(|i| s(i, u8::from(i > 64))).collect();
        let mut edges = Vec::new();
        for a in 1..=64 {
            for b in 65..=128 {
                edges.push(e(a, b, u32::from(a.abs_diff(b - 64))));
            }
        }
        let m = go(&s, &edges);
        assert_eq!(m.pairs.len(), 64);
        assert_eq!(m.total_cost, 0);
        assert!(m.reservation_bytes < 8 << 20);
        assert!(m.unmatched.is_empty());
    }
    #[test]
    fn overbudget_component_refuses_without_splitting() {
        let s: Vec<_> = (1..=130).map(|i| s(i, u8::from(i > 65))).collect();
        assert!(assign(&s, 0., &[], 8 << 20).is_err());
    }
    #[test]
    fn rejected_psf_edges_remain_unmatched_even_when_scale_identical() {
        let s = [s(1, 0), s(2, 1)];
        let e = [Assessment {
            pair: Pair::new(id(1), id(2)),
            state: Compatibility::Incompatible,
        }];
        assert!(go(&s, &e).pairs.is_empty());
    }
    #[test]
    fn exhaustive_three_by_three_oracle_with_unknowns_and_ties() {
        fn oracle(row: usize, used: u8, edges: &[[Option<u32>; 3]; 3]) -> (usize, u64) {
            if row == 3 {
                return (0, 0);
            }
            let mut best = oracle(row + 1, used, edges);
            for col in 0..3 {
                if used & (1 << col) != 0 {
                    continue;
                }
                if let Some(cost) = edges[row][col] {
                    let (n, c) = oracle(row + 1, used | (1 << col), edges);
                    let v = (n + 1, c + u64::from(cost));
                    if v.0 > best.0 || (v.0 == best.0 && v.1 < best.1) {
                        best = v;
                    }
                }
            }
            best
        }
        for mask in 0u16..512 {
            for cost_case in 0..6 {
                let sources = vec![s(1, 0), s(2, 0), s(3, 0), s(4, 1), s(5, 1), s(6, 1)];
                let mut edges = [[None; 3]; 3];
                let mut assessed = Vec::new();
                for row in 0..3 {
                    for col in 0..3 {
                        let bit = row * 3 + col;
                        let pair = Pair::new(id(row as u8 + 1), id(col as u8 + 4));
                        if mask & (1 << bit) != 0 {
                            let cost = if cost_case == 0 {
                                0
                            } else {
                                ((bit * 7 + cost_case * 3) % 11) as u32
                            };
                            edges[row][col] = Some(cost);
                            assessed.push(e(row as u8 + 1, col as u8 + 4, cost));
                        } else {
                            match (bit + cost_case) % 3 {
                                0 => {}
                                1 => assessed.push(Assessment {
                                    pair,
                                    state: Compatibility::Unknown,
                                }),
                                _ => assessed.push(Assessment {
                                    pair,
                                    state: Compatibility::Incompatible,
                                }),
                            }
                        }
                    }
                }
                let expected = oracle(0, 0, &edges);
                let got = go(&sources, &assessed);
                assert_eq!(
                    (got.pairs.len(), got.total_cost),
                    expected,
                    "graph{mask} costs{cost_case}"
                );
                let mut swapped = sources.clone();
                swapped.rotate_left(2);
                for src in &mut swapped {
                    src.pass = 1 - src.pass;
                }
                assessed.reverse();
                assert_eq!(
                    go(&swapped, &assessed),
                    got,
                    "canonical tie graph{mask} costs{cost_case}"
                );
            }
        }
    }
}
