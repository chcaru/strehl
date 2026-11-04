use super::*;
use crate::session_align::PairPurpose;
fn source(index: usize, pass: usize) -> Source {
    Source {
        index,
        pass,
        sha256: format!("{index:064x}"),
        log_scale: 0.,
    }
}
fn edge(i: usize, j: usize, log_scale: f64) -> EdgeReceipt {
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
        lever_plane_px: Some(1000.),
        refusal: None,
    }
}
fn complete(n: usize) -> Vec<EdgeReceipt> {
    (0..n)
        .flat_map(|i| (i + 1..n).map(move |j| edge(i, j, 0.)))
        .collect()
}
#[test]
fn repeat_proposals_preserve_every_source_and_do_not_claim_admission() {
    let sources: Vec<_> = (0..8).map(|i| source(i, i / 4)).collect();
    let plan = plan(&sources, &complete(8), 0., RESERVATION_BYTES).unwrap();
    assert_eq!(plan.matched_pairs, 4);
    assert_eq!(plan.basis, "GeometryProposal");
    let mut members: Vec<_> = plan.groups.iter().flatten().copied().collect();
    members.sort();
    assert_eq!(members, (0..8).collect::<Vec<_>>());
    assert!(
        plan.sources
            .iter()
            .all(|s| s.uncertainty_proxy == Some(0.0001))
    );
    assert!(plan.proposals.iter().all(|p| p.nominated));
}
#[test]
fn repeat_proposals_unknown_no_cycle_or_missing_direct_edge_stay_single() {
    let sources: Vec<_> = (0..4).map(|i| source(i, i / 2)).collect();
    let result = plan(
        &sources,
        &[edge(0, 2, 0.), edge(1, 3, 0.)],
        1.,
        RESERVATION_BYTES,
    )
    .unwrap();
    assert_eq!(result.matched_pairs, 0);
    assert_eq!(result.groups.len(), 4);
    let edges: Vec<_> = complete(4)
        .into_iter()
        .filter(|e| (e.i, e.j) != (0, 2))
        .collect();
    let result = plan(&sources, &edges, 0., RESERVATION_BYTES).unwrap();
    assert!(
        !result
            .proposals
            .iter()
            .find(|p| p.sources == [0, 2])
            .unwrap()
            .nominated
    );
}
#[test]
fn repeat_proposals_augmenting_path_and_minimum_cost_are_exact() {
    let costs = BTreeMap::from([((0, 2), 0), ((0, 3), 100), ((1, 2), 0)]);
    assert_eq!(
        assignment(&[0, 1], &[2, 3], &costs).unwrap(),
        (vec![[0, 3], [1, 2]], 100)
    );
    let costs = BTreeMap::from([((0, 2), 1), ((0, 3), 2), ((1, 2), 2), ((1, 3), 10)]);
    assert_eq!(
        assignment(&[0, 1], &[2, 3], &costs).unwrap(),
        (vec![[0, 3], [1, 2]], 4)
    );
}
#[test]
fn repeat_proposals_canonical_content_ties_ignore_source_order_and_pass_labels() {
    let mut sources: Vec<_> = (0..8).map(|i| source(i, i / 4)).collect();
    let first = plan(&sources, &complete(8), 0., RESERVATION_BYTES).unwrap();
    sources.reverse();
    for s in &mut sources {
        s.pass = 1 - s.pass;
    }
    let second = plan(&sources, &complete(8), 0., RESERVATION_BYTES).unwrap();
    assert_eq!(first.groups, second.groups);
}
#[test]
fn repeat_proposals_never_truncate_duplicate_or_overbudget_inputs() {
    let sources: Vec<_> = (0..8).map(|i| source(i, i / 4)).collect();
    assert!(plan(&sources, &complete(8), 0., RESERVATION_BYTES - 1).is_err());
    let mut duplicate = sources.clone();
    duplicate[1].sha256 = duplicate[0].sha256.clone();
    assert!(plan(&duplicate, &complete(8), 0., RESERVATION_BYTES).is_err());
    let huge: Vec<_> = (0..130).map(|i| source(i, i / 65)).collect();
    assert!(plan(&huge, &[], 0., RESERVATION_BYTES).is_err());
    let mut overflow = complete(8);
    overflow[0].rms_plane_px = Some(f64::MAX);
    overflow[0].lever_plane_px = Some(f64::MIN_POSITIVE);
    assert!(plan(&sources, &overflow, 0., RESERVATION_BYTES).is_err());
    let mut overflow = sources.clone();
    overflow[0].log_scale = f64::MAX;
    overflow[4].log_scale = -f64::MAX;
    assert!(plan(&overflow, &complete(8), 0., RESERVATION_BYTES).is_err());
}
