use super::*;
#[path = "fixture.rs"]
mod fixture;
use fixture::*;

#[test]
fn default_prior_does_not_place_unmeasured_frame() {
    let edge = AlignEdge {
        i: 0,
        j: 1,
        t: Similarity::IDENTITY,
        rms: 0.1,
        used: 32,
        lever: 1000.0,
    };
    for smooth in [0.0, 1.0] {
        let result = solve_global_in_component(&[edge], 3, &options(smooth), 0).unwrap();
        expect_mask(&result, &[0, 1]);
    }
}

#[test]
fn fully_connected_m103_curvature_keeps_legacy_bits() {
    let track = truth();
    assert!(
        track
            .windows(3)
            .any(|w| (w[0].a.re - 2.0 * w[1].a.re + w[2].a.re).abs() > 0.001)
    );
    let mut edges = edges_for(&(0..9).collect::<Vec<_>>(), &track);
    // Nonzero, fixed perturbations exercise edge/prior IRLS, not just a perfect fit.
    for (k, edge) in edges.iter_mut().enumerate() {
        edge.t.b.re += ((k % 5) as f64 - 2.0) * 0.07;
        edge.t.a.re += ((k % 3) as f64 - 1.0) * 0.00001;
    }
    assert_eq!(graph_stats(&edges, 9).cycle_rank, 28);
    for smooth in [0.0, 1.0] {
        let old = solve_global(&edges, 9, &options(smooth)).unwrap();
        println!(
            "V_CONNECTED smooth={} bits={}",
            smooth,
            serde_json::to_string(&bits(&old)).unwrap()
        );
        for reference in [0, 4, 8] {
            let new = solve_global_in_component(&edges, 9, &options(smooth), reference).unwrap();
            assert_eq!(
                bits(&new),
                bits(&old),
                "connected coordinate bits changed, smooth={smooth}, reference={reference}"
            );
        }
    }
}

#[test]
fn selected_reference_component_works_when_zero_is_isolated() {
    let track = truth();
    let ids = [2, 3, 4, 5, 6];
    let edges = edges_for(&ids, &track);
    assert_eq!(graph_stats(&edges, 9).cycle_rank, 6);
    for smooth in [0.0, 1.0] {
        let g = solve_global_in_component(&edges, 9, &options(smooth), 4).unwrap();
        expect_mask(&g, &ids);
        assert_eq!(
            g[2],
            Some(Similarity::IDENTITY),
            "smallest admitted frame is the numeric gauge"
        );
        if smooth == 0.0 {
            let mut max_native: f64 = 0.0;
            for &k in &ids {
                max_native = max_native.max(native_error(
                    relative(g[4].unwrap(), g[k].unwrap()),
                    relative(track[4], track[k]),
                ));
            }
            let wrong_gauge = native_error(
                relative(g[4].unwrap(), g[6].unwrap()),
                relative(track[0], track[6]),
            );
            assert!(
                wrong_gauge > 1.0,
                "truth gate must reject wrong reference: {wrong_gauge}"
            );
            assert!(
                max_native < 1e-8,
                "reference-gauge truth mismatch: {max_native}"
            );
            println!(
                "V_TRUTH smooth0 max_native_px={max_native} wrong_gauge_native_px={wrong_gauge}"
            );
        }
    }
}

#[test]
fn isolated_selected_reference_stays_the_only_placement() {
    let track = truth();
    let mut edges = edges_for(&[0, 1, 2], &track);
    edges.extend(edges_for(&[6, 7, 8], &track));
    for smooth in [0.0, 1.0] {
        let g = solve_global_in_component(&edges, 9, &options(smooth), 4).unwrap();
        expect_mask(&g, &[4]);
        assert_eq!(g[4], Some(Similarity::IDENTITY));
    }
}

#[test]
fn gaps_do_not_become_false_temporal_neighbors() {
    let track = truth();
    let ids = [0, 2, 4, 6, 8];
    let edges = edges_for(&ids, &track);
    let no_prior = solve_global_in_component(&edges, 9, &options(0.0), 4).unwrap();
    let with_prior = solve_global_in_component(&edges, 9, &options(1.0), 4).unwrap();
    expect_mask(&with_prior, &ids);
    // Commission the curved-track discriminator before checking the null.
    assert!(
        ids.windows(3)
            .any(|w| (track[w[0]].a.re - 2.0 * track[w[1]].a.re + track[w[2]].a.re).abs() > 0.001)
    );
    assert_eq!(
        bits(&with_prior),
        bits(&no_prior),
        "no original adjacent triple is admitted"
    );
}

#[test]
fn unrelated_poison_cannot_contaminate_or_attach_components() {
    let track = truth();
    for ids in [&[2, 3, 4, 5, 6][..], &[0, 2, 4, 6, 8][..]] {
        let clean = edges_for(ids, &track);
        let outside: Vec<_> = (0..9).filter(|k| !ids.contains(k)).collect();
        let mut poisoned = clean.clone();
        let mut poison_edges = edges_for(&outside, &track);
        for (k, e) in poison_edges.iter_mut().enumerate() {
            e.t.a = Cx::new(1.4 + 0.02 * k as f64, 0.2);
            e.t.b = Cx::new(200.0 + 17.0 * k as f64, -130.0);
        }
        poisoned.extend(poison_edges);
        // Gate commission: legacy smoothing links the components; final masking
        // alone leaves a changed active solution. This must be observably nonzero.
        let old_clean = solve_global(&clean, 9, &options(1.0)).unwrap();
        let old_poison = solve_global(&poisoned, 9, &options(1.0)).unwrap();
        let delta = ids
            .iter()
            .map(|&k| {
                native_error(
                    relative(old_clean[4].unwrap(), old_clean[k].unwrap()),
                    relative(old_poison[4].unwrap(), old_poison[k].unwrap()),
                )
            })
            .fold(0.0, f64::max);
        assert!(
            delta > 1e-5,
            "poison control did not exercise contamination: {delta}"
        );
        println!("V_POISON ids={ids:?} legacy_rebased_max_delta_native_px={delta}");
        for smooth in [0.0, 1.0] {
            let base = solve_global_in_component(&clean, 9, &options(smooth), 4).unwrap();
            let candidate = solve_global_in_component(&poisoned, 9, &options(smooth), 4).unwrap();
            expect_mask(&candidate, ids);
            assert_eq!(
                bits(&candidate),
                bits(&base),
                "outside observations entered active solve"
            );
        }
    }
}

#[test]
fn edge_order_and_invalid_indices_preserve_component_contract() {
    let edges = edges_for(&[2, 3, 4, 5, 6], &truth());
    for smooth in [0.0, 1.0] {
        let forward = solve_global_in_component(&edges, 9, &options(smooth), 4).unwrap();
        let mut reversed = edges.clone();
        reversed.reverse();
        let backward = solve_global_in_component(&reversed, 9, &options(smooth), 4).unwrap();
        expect_mask(&backward, &[2, 3, 4, 5, 6]);
        for k in [2, 3, 4, 5, 6] {
            assert!(native_error(forward[k].unwrap(), backward[k].unwrap()) < 1e-8);
        }
        reversed.push(AlignEdge {
            i: 9,
            j: 100,
            t: Similarity::IDENTITY,
            rms: 0.1,
            used: 32,
            lever: 1000.0,
        });
        let invalid_ignored = solve_global_in_component(&reversed, 9, &options(smooth), 4).unwrap();
        assert_eq!(bits(&invalid_ignored), bits(&backward));
    }
    assert!(solve_global_in_component(&edges, 9, &options(1.0), 9).is_none());
    assert!(solve_global_in_component(&[], 0, &options(1.0), 0).is_none());
    assert_eq!(reachable_from(&edges, 9, 9), vec![false; 9]);
}
#[test]
fn admitted_original_triples_keep_prior_active() {
    let track = truth();
    // First a contiguous selected component with isolated 0; then a connected
    // component with real index holes and two retained original triples.
    for ids in [&[2, 3, 4, 5, 6][..], &[0, 2, 3, 4, 6, 7, 8][..]] {
        let centers: Vec<_> = (1..8)
            .filter(|k| ids.contains(&(k - 1)) && ids.contains(k) && ids.contains(&(k + 1)))
            .collect();
        assert!(!centers.is_empty());
        assert!(
            centers.iter().any(
                |&k| (track[k - 1].a.re - 2.0 * track[k].a.re + track[k + 1].a.re).abs() > 0.001
            ),
            "retained prior stencil must see measured curvature"
        );
        let edges = edges_for(ids, &track);
        let off = solve_global_in_component(&edges, 9, &options(0.0), 4).unwrap();
        let on = solve_global_in_component(&edges, 9, &options(1.0), 4).unwrap();
        expect_mask(&on, ids);
        let delta = ids
            .iter()
            .map(|&k| {
                native_error(
                    relative(off[4].unwrap(), off[k].unwrap()),
                    relative(on[4].unwrap(), on[k].unwrap()),
                )
            })
            .fold(0.0, f64::max);
        assert!(
            delta > 1e-5,
            "admitted prior was disabled when unrelated frames were refused: {delta}"
        );
        println!(
            "V_RETAINED_PRIOR ids={ids:?} centers={centers:?} rebased_max_delta_native_px={delta}"
        );
    }
}

#[test]
fn requested_reference_does_not_change_inconsistent_component_solution() {
    // Independent review's analytical cycle: no original adjacent triple, so
    // default smooth1 cannot hide the smooth0 gauge issue. See review witness.
    let ids = [2, 4, 6];
    let mut edges = edges_for(&ids, &[Similarity::IDENTITY; 7]);
    edges[1].t.a.re = 1.001; // a24=a46=1, a26=1+epsilon
    assert_eq!(graph_stats(&edges, 7).cycle_rank, 1);
    assert!(
        native_error(edges[1].t, Similarity::IDENTITY) > 0.1,
        "the exact-cycle null must not replace the inconsistent-edge control"
    );
    for smooth in [0.0, 1.0] {
        let baseline = solve_global_in_component(&edges, 7, &options(smooth), 2).unwrap();
        for reference in [4, 6] {
            let changed =
                solve_global_in_component(&edges, 7, &options(smooth), reference).unwrap();
            expect_mask(&changed, &ids);
            let delta = ids
                .iter()
                .map(|&k| {
                    native_error(
                        relative(baseline[2].unwrap(), baseline[k].unwrap()),
                        relative(changed[2].unwrap(), changed[k].unwrap()),
                    )
                })
                .fold(0.0, f64::max);
            assert!(
                delta < 1e-8,
                "output reference changed the measured least-squares optimum: smooth={smooth}, reference={reference}, delta={delta}"
            );
            println!(
                "V_REFERENCE_INVARIANCE smooth={smooth} reference={reference} max_native_px={delta}"
            );
        }
    }
}
