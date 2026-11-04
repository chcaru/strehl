use super::*;

fn grids() -> [AnchorGrid; 2] {
    [0, 1].map(|pass| AnchorGrid {
        source_size_quad: [1536, 1024],
        guide_origin_quad: [1.5; 2],
        guide_step_quad: 4,
        initial_block_guide_pixels: 128,
        global_source_range: [pass * 100, pass * 100 + 100],
    })
}
fn proposals() -> Vec<IslandProposal> {
    [[144., 144.], [368., 144.], [256., 368.]]
        .into_iter()
        .enumerate()
        .map(|(id, point)| IslandProposal {
            id: format!("fixed-0-0-{id}"),
            cell: [0, 0],
            reference_center_quad: point,
            original_witnesses: [vec![1], vec![101, 102]],
            query_radius_quad: [43., 43.],
        })
        .collect()
}
fn ancestor() -> AncestorFootprint {
    AncestorFootprint {
        pass: 0,
        source: 1,
        measurement_id: "all-attempts-initial-fit".into(),
        bounds: Rectangle::around([700., 100.], 40.).unwrap(),
    }
}
fn plan() -> RolePlan {
    RolePlan::build(
        "a".repeat(64),
        "b".repeat(64),
        grids(),
        [1., 0., 50., -10.],
        24.,
        vec![ancestor()],
        proposals(),
    )
    .unwrap()
}

#[test]
fn frozen_islands_bind_sources_seed_and_complete_reservations() {
    let plan = plan();
    assert_eq!(plan.islands.len(), 3);
    assert!(plan.refused.is_empty());
    for (id, island) in plan.islands.iter().enumerate() {
        for pass in 0..2 {
            assert_eq!(
                plan.grids[pass].initial_role(island.reservations[pass]),
                Some(true)
            );
            assert_eq!(
                plan.classify(pass, island.reservations[pass]),
                Some(SpatialRole::Heldout(id))
            );
        }
    }
    assert!(plan.witness_allowed(0, 0, 1));
    assert!(plan.witness_allowed(0, 1, 102));
    assert!(!plan.witness_allowed(0, 1, 1));
    assert!(!plan.witness_allowed(0, 2, 1));
    let frozen = plan.freeze().unwrap();
    let encoded = serde_json::to_vec(&frozen).unwrap();
    let loaded: FrozenRolePlan = serde_json::from_slice(&encoded).unwrap();
    loaded.verify().unwrap();
    assert_eq!(frozen.sha256, loaded.sha256);
    let mut poison = loaded;
    poison.plan.initial_seed[2] += 1.;
    assert!(poison.verify().is_err());
}

#[test]
fn stage_two_fit_is_permitted_only_outside_every_frozen_island() {
    let plan = plan();
    let new_fit = AncestorFootprint {
        pass: 0,
        source: 1,
        measurement_id: "stage-two-new-fit".into(),
        bounds: Rectangle::around([256., 256.], 20.).unwrap(),
    };
    assert_eq!(plan.grids[0].initial_role(new_fit.bounds), Some(true));
    plan.check_fit_attempt(&new_fit).unwrap();
    let mut clipped = new_fit;
    clipped.bounds = Rectangle::around([144., 144.], 50.).unwrap();
    assert!(plan.check_fit_attempt(&clipped).is_err());
    assert!(plan.classify(0, clipped.bounds).is_none());
    // Filter/derivative/interpolation support must be expanded before querying.
    let inner = Rectangle::around([144., 144.], 42.).unwrap();
    assert_eq!(plan.classify(0, inner), Some(SpatialRole::Heldout(0)));
    assert_eq!(
        plan.classify(0, Rectangle::around([144., 144.], 44.).unwrap()),
        None
    );
    // Measured movement beyond the frozen initial uncertainty cannot grow it.
    let moving = plan.islands[0].nominated_moving_center_quad;
    assert_eq!(
        plan.classify(
            1,
            Rectangle::around([moving[0] + 80., moving[1]], 43.).unwrap()
        ),
        None
    );
}

#[test]
fn initial_ancestor_overlap_wrong_identity_and_projection_are_refused() {
    let mut wrong = ancestor();
    wrong.bounds = Rectangle::around([144., 144.], 43.).unwrap();
    let overlapping = RolePlan::build(
        "a".repeat(64),
        "b".repeat(64),
        grids(),
        [1., 0., 50., -10.],
        24.,
        vec![wrong],
        proposals(),
    )
    .unwrap();
    assert_eq!(overlapping.islands.len(), 2);
    assert_eq!(overlapping.refused.len(), 1);
    assert!(
        overlapping.refused[0]
            .reason
            .contains("initial FIT attempt")
    );
    let projected = RolePlan::build(
        "a".repeat(64),
        "b".repeat(64),
        grids(),
        [1., 0., 350., -10.],
        24.,
        vec![ancestor()],
        proposals(),
    )
    .unwrap();
    assert!(!projected.refused.is_empty());
    assert!(projected.islands.len() < 3);
    let mut proposals = proposals();
    proposals[0].original_witnesses[1] = vec![1];
    let wrong = RolePlan::build(
        "a".repeat(64),
        "b".repeat(64),
        grids(),
        [1., 0., 50., -10.],
        24.,
        vec![ancestor()],
        proposals,
    )
    .unwrap();
    assert_eq!(wrong.refused.len(), 1);
    assert!(wrong.refused[0].reason.contains("witness"));
    let mut invalid_grid = grids();
    invalid_grid[0].guide_origin_quad[0] = -1e300;
    assert!(
        RolePlan::build(
            "a".repeat(64),
            "b".repeat(64),
            invalid_grid,
            [1., 0., 50., -10.],
            24.,
            vec![ancestor()],
            Vec::new()
        )
        .is_err()
    );
}

#[test]
fn overlapping_validation_sites_are_one_support_and_cannot_inflate_counts() {
    let mut proposals = proposals();
    let mut near = proposals[0].clone();
    near.id = "same-support-alternate-original".into();
    near.original_witnesses[1] = vec![103];
    near.reference_center_quad[0] += 10.;
    proposals.push(near);
    let plan = RolePlan::build(
        "a".repeat(64),
        "b".repeat(64),
        grids(),
        [1., 0., 50., -10.],
        24.,
        vec![ancestor()],
        proposals,
    )
    .unwrap();
    assert_eq!(plan.islands.len(), 3);
    assert_eq!(plan.refused.len(), 1);
    assert!(plan.refused[0].reason.contains("distinct physical support"));
    plan.freeze().unwrap().verify().unwrap();
}
