use super::*;
use strehl_core::align::Cx;

fn geom() -> PlaneGeometry {
    PlaneGeometry::from_active(7032, 4688)
}

fn opts() -> GlobalOptions {
    let mut result = GlobalOptions::new(geom());
    result.smooth = DEFAULT_SMOOTH_LAMBDA;
    result.smooth_huber_px = Some(DEFAULT_SMOOTH_HUBER_PX);
    result
}

fn edge(i: usize, j: usize) -> AlignEdge {
    AlignEdge {
        i,
        j,
        t: Similarity::IDENTITY,
        rms: 0.1,
        used: 32,
        lever: 1000.0,
    }
}

fn map_with(warps: Vec<FrameWarp>, reference: usize, strategy: &str) -> WarpMap {
    let count = warps.len();
    let entries: Vec<_> = (0..count)
        .map(|i| (format!("generated-{i}.arw"), 100))
        .collect();
    WarpMap::new(
        Provenance {
            stack: StackIdentity::from_entries("generated-no-files", &entries),
            strategy: strategy.into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference,
            note: "V generated contract fixture; no image claim".into(),
        },
        geom(),
        Resampler::CatmullRom,
        warps,
    )
}

#[test]
fn ordinary_defaults_are_the_shipping_prior_settings() {
    assert_eq!(DEFAULT_SMOOTH_LAMBDA, 1.0);
    assert_eq!(DEFAULT_SMOOTH_HUBER_PX, 1.0);
    assert_eq!(SOLVE_GENERATION, 3);
}

#[test]
fn normal_warps_use_requested_reference_and_keep_explicit_refusals() {
    let edges = [edge(2, 3), edge(3, 4), edge(2, 4)];
    let placements = solve_global_in_component(&edges, 6, &opts(), 4).unwrap();
    let warps = ordinary_component_warps(&placements, 4).unwrap();
    let map = map_with(warps, 4, NORMAL_ALIGNMENT_STRATEGY);
    assert_eq!(map.placed_count(), 3);
    assert_eq!(map.refused_count(), 3);
    assert_eq!(map.placement(4).unwrap(), Similarity::IDENTITY);
    assert!(map.placement(0).is_err());
    assert!(matches!(map.warp(0).unwrap(), FrameWarp::Refused(why)
        if why == "frame 0 is not connected to reference frame 4 by any measured edge"));
    let roundtrip = WarpMap::from_text(&map.to_text()).unwrap();
    assert_eq!(roundtrip, map);
    assert!(ordinary_map_policy_matches(&roundtrip));
    assert_eq!(roundtrip.provenance().reference, 4);
    let (covered, _) = fit_to_cover(&roundtrip, 3.0).unwrap();
    for k in [0, 1, 5] {
        assert_eq!(covered.warp(k).unwrap(), map.warp(k).unwrap());
    }
    assert_eq!(covered.provenance().reference, 4);
    assert_eq!(covered.provenance().strategy, NORMAL_ALIGNMENT_STRATEGY);
    println!(
        "V_CLI selected_reference=4 placed=3 refused=3 roundtrip=true cover_refusals_preserved=true"
    );
}

#[test]
fn normal_rebase_rejects_missing_and_singular_reference() {
    let t = Similarity {
        a: Cx::real(0.98),
        b: Cx::new(2.0, -1.0),
    };
    // Exercise the old fallback as a causal control: missing reference used to
    // return a transform in an unrelated gauge without an error.
    assert_eq!(rebase(t, None), t);
    let missing = ordinary_component_warps(&[Some(t), None], 1).unwrap_err();
    assert!(
        missing
            .to_string()
            .contains("reference frame 1 has no invertible measured placement")
    );
    let zero = Similarity {
        a: Cx::ZERO,
        b: Cx::ZERO,
    };
    assert!(ordinary_component_warps(&[Some(t), Some(zero)], 1).is_err());
    assert!(ordinary_component_warps(&[Some(t)], 2).is_err());
    // Valid nonzero gauge keeps the old arithmetic bits exactly.
    let valid = ordinary_component_warps(&[Some(t), Some(Similarity::IDENTITY)], 0).unwrap();
    for (k, source) in [t, Similarity::IDENTITY].into_iter().enumerate() {
        let actual = valid[k].placed().unwrap();
        let old = rebase(source, Some(t));
        assert_eq!(
            [
                actual.a.re.to_bits(),
                actual.a.im.to_bits(),
                actual.b.re.to_bits(),
                actual.b.im.to_bits()
            ],
            [
                old.a.re.to_bits(),
                old.a.im.to_bits(),
                old.b.re.to_bits(),
                old.b.im.to_bits()
            ]
        );
    }
}

#[test]
fn ordinary_cache_policy_predicate_distinguishes_versions() {
    let old = map_with(
        vec![FrameWarp::Placed(Similarity::IDENTITY); 3],
        0,
        "S3-ba-unit",
    );
    let new = map_with(
        vec![FrameWarp::Placed(Similarity::IDENTITY); 3],
        0,
        NORMAL_ALIGNMENT_STRATEGY,
    );
    assert_eq!(ordinary_map_policy(&old), OrdinaryMapPolicy::Legacy);
    assert_eq!(ordinary_map_policy(&new), OrdinaryMapPolicy::Current);
    let planted = map_with(
        vec![FrameWarp::Placed(Similarity::IDENTITY); 3],
        0,
        "V-planted-control",
    );
    assert_eq!(
        ordinary_map_policy(&planted),
        OrdinaryMapPolicy::Nonordinary
    );
    assert!(
        !ordinary_map_policy_matches(&planted),
        "nonordinary explicit maps are not ordinary cache entries"
    );
    assert!(!ordinary_map_policy_matches(&old));
    assert!(ordinary_map_policy_matches(&new));
    assert!(!ordinary_map_policy_matches(
        &WarpMap::from_text(&old.to_text()).unwrap()
    ));
}

#[test]
fn diagnostics_exclude_other_measured_components() {
    let mut edges = vec![edge(2, 3), edge(3, 4), edge(2, 4)];
    let mut poison = edge(0, 1);
    poison.t.b = Cx::new(200.0, -100.0);
    edges.push(poison);
    edges.push(edge(6, 100));
    let selected = measured_reference_edges(&edges, 7, 4);
    assert_eq!(
        selected.iter().map(|e| (e.i, e.j)).collect::<Vec<_>>(),
        [(2, 3), (3, 4), (2, 4)]
    );
    assert_eq!(cycle_floor(&selected, geom()), Some(0.0));
    assert!(measured_reference_edges(&edges, 7, 6).is_empty());
}

#[test]
fn heldout_diagnostic_does_not_score_prior_only_extrapolation() {
    // Frame 40 belongs to the full measured component through the held-out
    // edge, but the training graph supplies no measured placement for it.
    let edges = [edge(0, 1), edge(0, 40)];
    assert_eq!(measured_reference_edges(&edges, 41, 0).len(), 2);
    assert!(
        heldout_error(&edges, 41, &opts(), geom(), None).is_some(),
        "legacy positive control must extrapolate the held-out endpoint"
    );
    assert!(heldout_error(&edges, 41, &opts(), geom(), Some(0)).is_none());
    assert!(heldout_error(&edges, 41, &opts(), geom(), Some(20)).is_none());
    println!("V_HELDOUT legacy_scores_prior_only=true component_mode_refuses=true");
}
