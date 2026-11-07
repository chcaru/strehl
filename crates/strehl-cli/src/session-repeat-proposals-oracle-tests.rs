//! Independent implementation controls for the geometric proposal experiment.
//! These enumerate assignments directly; they do not validate photographic quality.
use super::{RESERVATION_BYTES, Source, assignment, plan};
use crate::session_align::{EdgeReceipt, PairPurpose};
use std::collections::{BTreeMap, BTreeSet};

fn edge_key(a: usize, b: usize) -> (usize, usize) {
    (a.min(b), a.max(b))
}

/// Every row independently chooses unmatched or one of three columns.
/// Reject collisions and absent edges, then compare the declared lexicographic
/// objective. This deliberately shares no residual graph or path machinery.
fn enumerated_optimum(costs: &[[Option<u32>; 3]; 3]) -> (usize, u64) {
    let mut best = (0, 0);
    for encoded in 0_u32..64 {
        let mut columns = 0_u8;
        let mut count = 0;
        let mut total = 0_u64;
        let mut valid = true;
        for (row, values) in costs.iter().enumerate() {
            let choice = ((encoded >> (2 * row)) & 3) as usize;
            if choice == 0 {
                continue;
            }
            let column = choice - 1;
            if columns & (1 << column) != 0 {
                valid = false;
                break;
            }
            let Some(cost) = values[column] else {
                valid = false;
                break;
            };
            columns |= 1 << column;
            count += 1;
            total += u64::from(cost);
        }
        if valid && (count > best.0 || (count == best.0 && total < best.1)) {
            best = (count, total);
        }
    }
    best
}

fn planted_cost(arm: usize, row: usize, column: usize) -> u32 {
    let ordinal = (3 * row + column) as u32;
    match arm {
        0 => 0,
        1 => ordinal * 97 + 13,
        2 => ((row + column) % 2) as u32,
        3 => 1_000_000 - (ordinal * 31 % 101),
        // Arithmetic stress of the private solver, beyond the proposal cost
        // range. This is not a licensed production cost or uncertainty model.
        4 => u32::MAX - ordinal * 13,
        5 => {
            ordinal
                .wrapping_add(19)
                .wrapping_mul(2_654_435_761)
                .rotate_left(11)
                % 1_000_001
        }
        6 => u32::from(row != column),
        7 => ((row * 5 + column * 3) % 3) as u32 * 997,
        _ => unreachable!(),
    }
}

fn check_feasible(
    left: &[usize],
    right: &[usize],
    costs: &BTreeMap<(usize, usize), u32>,
    pairs: &[[usize; 2]],
    reported_cost: u64,
) {
    let mut used = BTreeSet::new();
    let mut total = 0_u64;
    for pair in pairs {
        assert!(pair[0] < pair[1]);
        assert!(
            (left.contains(&pair[0]) && right.contains(&pair[1]))
                || (right.contains(&pair[0]) && left.contains(&pair[1]))
        );
        assert!(used.insert(pair[0]) && used.insert(pair[1]));
        total += u64::from(costs[&edge_key(pair[0], pair[1])]);
    }
    assert_eq!(reported_cost, total);
}

#[test]
fn repeat_proposals_independent_all_three_by_three_graphs_match_enumeration() {
    // Deliberately nonmonotone original indices.
    let left = [7, 29, 11];
    let right = [103, 59, 83];
    for mask in 0_u16..512 {
        for arm in 0..8 {
            let mut matrix = [[None; 3]; 3];
            let mut edges = BTreeMap::new();
            for (row, values) in matrix.iter_mut().enumerate() {
                for (column, value) in values.iter_mut().enumerate() {
                    if mask & (1 << (row * 3 + column)) != 0 {
                        let cost = planted_cost(arm, row, column);
                        *value = Some(cost);
                        edges.insert(edge_key(left[row], right[column]), cost);
                    }
                }
            }
            let expected = enumerated_optimum(&matrix);
            let variants = [
                (left, right),
                ([left[2], left[1], left[0]], [right[1], right[2], right[0]]),
                (right, left),
            ];
            for (a, b) in variants {
                let (pairs, total) = assignment(&a, &b, &edges).unwrap();
                check_feasible(&a, &b, &edges, &pairs, total);
                assert_eq!(
                    (pairs.len(), total),
                    expected,
                    "mask={mask} cost_arm={arm} left={a:?} right={b:?}"
                );
                // Raw assignment permutations need preserve the objective;
                // exact tie pairs are fixed by plan's canonical content order.
            }
        }
    }
}

fn source(index: usize, pass: usize, log_scale: f64) -> Source {
    Source {
        index,
        pass,
        sha256: format!("{:064x}", (index * 37 + 11) % 101 + 1),
        log_scale,
    }
}

fn measured_edge(i: usize, j: usize, log_scale: f64, lever: f64) -> EdgeReceipt {
    EdgeReceipt {
        i,
        j,
        purpose: PairPurpose::CrossProbe,
        stage: "native".into(),
        accepted: true,
        transform_bits: Some([
            log_scale.exp().to_bits(),
            0_f64.to_bits(),
            0_f64.to_bits(),
            0_f64.to_bits(),
        ]),
        rms_plane_px: Some(0.1),
        used: 8,
        attempted: 8,
        correlated: 8,
        peak_mean: Some(0.99),
        lever_plane_px: Some(lever),
        refusal: None,
    }
}

#[test]
fn repeat_proposals_independent_plan_content_ties_survive_every_graph_permutation() {
    for mask in 0_u16..512 {
        let mut sources: Vec<_> = (0..6).map(|i| source(i, i / 3, 0.)).collect();
        let mut edges = Vec::new();
        let mut matrix = [[None; 3]; 3];
        for (i, row) in matrix.iter_mut().enumerate() {
            for (j, value) in row.iter_mut().enumerate() {
                if mask & (1 << (i * 3 + j)) != 0 {
                    *value = Some(0);
                }
            }
        }
        for i in 0..6 {
            for j in i + 1..6 {
                let same_pass = i / 3 == j / 3;
                let selected = !same_pass && mask & (1 << (i * 3 + j - 3)) != 0;
                if same_pass || selected {
                    edges.push(measured_edge(i, j, 0., 1000.));
                }
            }
        }
        let expected = enumerated_optimum(&matrix);
        let first = plan(&sources, &edges, 0., RESERVATION_BYTES).unwrap();
        assert_eq!((first.matched_pairs, first.total_cost), expected);
        let mut retained: Vec<_> = first.groups.iter().flatten().copied().collect();
        retained.sort_unstable();
        assert_eq!(retained, (0..6).collect::<Vec<_>>());

        sources.rotate_left(2);
        for item in &mut sources {
            item.pass = if item.pass == 0 { 91 } else { 17 };
        }
        edges.reverse();
        let permuted = plan(&sources, &edges, 0., RESERVATION_BYTES).unwrap();
        assert_eq!(first.groups, permuted.groups, "canonical mask={mask}");
        assert_eq!(first.total_cost, permuted.total_cost);
    }
}

#[test]
fn repeat_proposals_independent_weak_leverage_is_only_a_broader_proposal() {
    let sources: Vec<_> = (0..6)
        .map(|i| source(i, i / 3, if i < 3 { 0. } else { 0.005 }))
        .collect();
    let make_edges = |lever| {
        let mut out = Vec::new();
        for i in 0..6 {
            for j in i + 1..6 {
                out.push(measured_edge(
                    i,
                    j,
                    sources[j].log_scale - sources[i].log_scale,
                    lever,
                ));
            }
        }
        out
    };
    let strong = plan(&sources, &make_edges(1000.), 0., RESERVATION_BYTES).unwrap();
    let weak = plan(&sources, &make_edges(0.1), 0., RESERVATION_BYTES).unwrap();
    assert_eq!(strong.matched_pairs, 0);
    assert_eq!(weak.matched_pairs, 3);
    assert!(strong.proposals.iter().all(|p| !p.nominated));
    assert!(weak.proposals.iter().all(|p| p.nominated));
    assert!(
        weak.sources
            .iter()
            .zip(&strong.sources)
            .all(|(w, s)| w.uncertainty_proxy.unwrap() > s.uncertainty_proxy.unwrap() * 1000.)
    );
    assert_eq!(weak.basis, "GeometryProposal");
    assert!(weak.scope.contains("No calibrated scale uncertainty"));
    assert!(
        weak.scope
            .contains("RepeatCompatible admission or SR eligibility")
    );
    // This intentionally exposes the heuristic: weak leverage broadens the
    // graph. It is not a compatibility, source-admission, or quality positive.
    assert!(plan(&sources, &make_edges(0.), 0., RESERVATION_BYTES).is_err());
}
