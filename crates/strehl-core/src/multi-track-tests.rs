//! Controls for explicit tracks and bounded pair refinement. Plants establish
//! algebra/operator behavior, not calibration or photographic quality.

use super::*;

fn geom() -> PlaneGeometry {
    PlaneGeometry::from_active(7032, 4688)
}

fn options(smooth: f64, robust: Option<f64>) -> GlobalOptions {
    GlobalOptions {
        smooth,
        smooth_huber_px: robust,
        irls_iters: 6,
        ..GlobalOptions::new(geom())
    }
}

fn curved_truth(n: usize, offset: f64) -> Vec<Similarity> {
    (0..n)
        .map(|k| {
            let t = k as f64 / (n - 1).max(1) as f64;
            Similarity::from_params(SimilarityParams {
                ax: offset + 10.0 * t + 184.4 * t * t,
                ay: -offset * 0.4 + 7.0 * t - 16.0 * t * t,
                g: offset * 0.0001 + 0.003 * t + 0.001 * t * t,
                rot: 0.0004 * t * t,
            })
        })
        .collect()
}

fn edges_for(ids: &[usize], truth: &[Similarity]) -> Vec<AlignEdge> {
    let mut edges = Vec::new();
    for (position, &i) in ids.iter().enumerate() {
        for &j in &ids[position + 1..] {
            edges.push(AlignEdge {
                i,
                j,
                t: Similarity::relative(truth[i], truth[j]).unwrap(),
                rms: 0.2,
                used: 48,
                lever: 1200.0,
            });
        }
    }
    edges
}

fn perturb(edges: &mut [AlignEdge]) {
    for (k, edge) in edges.iter_mut().enumerate() {
        edge.t.b.re += (k % 7) as f64 * 0.03 - 0.09;
        edge.t.b.im += (k % 5) as f64 * 0.02 - 0.04;
        edge.t.a.re += ((k % 3) as f64 - 1.0) * 0.00001;
    }
}

fn bits(placement: &Placement) -> Vec<Option<[u64; 4]>> {
    placement
        .iter()
        .map(|p| {
            p.map(|p| {
                [
                    p.a.re.to_bits(),
                    p.a.im.to_bits(),
                    p.b.re.to_bits(),
                    p.b.im.to_bits(),
                ]
            })
        })
        .collect()
}

#[test]
fn one_track_keeps_ordinary_and_legacy_coordinate_bits() {
    let truth = curved_truth(9, 0.0);
    // Carry the measured 46.1-plane-pixel departure from a straight chord.
    let chord_mid = (truth[0].b.re + truth[8].b.re) * 0.5;
    assert!((chord_mid - truth[4].b.re - 46.1).abs() < 1e-10);
    let mut edges = edges_for(&(0..9).collect::<Vec<_>>(), &truth);
    perturb(&mut edges);
    assert!(graph_stats(&edges, 9).cycle_rank > 0);
    for smooth in [0.0, 1.0, 5.0] {
        for robust in [None, Some(0.2), Some(1.0)] {
            let opts = options(smooth, robust);
            let legacy = solve_global(&edges, 9, &opts).unwrap();
            for reference in [0, 4, 8] {
                let ordinary = solve_global_in_component(&edges, 9, &opts, reference).unwrap();
                let tracks =
                    solve_global_in_tracks(&edges, 9, &opts, reference, &[(0..9).collect()])
                        .unwrap();
                assert_eq!(bits(&tracks), bits(&ordinary));
                assert_eq!(bits(&tracks), bits(&legacy));
            }
        }
    }
}

#[test]
fn malformed_tracks_are_refused_before_solving() {
    let opts = options(1.0, Some(1.0));
    assert_eq!(
        solve_global_in_tracks(&[], 0, &opts, 0, &[]),
        Err(TrackSolveError::EmptySession)
    );
    assert_eq!(
        solve_global_in_tracks(&[], 3, &opts, 3, &[vec![0, 1, 2]]),
        Err(TrackSolveError::ReferenceOutOfBounds {
            reference: 3,
            frames: 3
        })
    );
    for (tracks, error) in [
        (vec![vec![]], TrackSolveError::EmptyTrack { track: 0 }),
        (vec![], TrackSolveError::MissingFrame { frame: 0 }),
        (vec![vec![0, 2]], TrackSolveError::MissingFrame { frame: 1 }),
        (
            vec![vec![0, 1, 3]],
            TrackSolveError::FrameOutOfBounds {
                track: 0,
                frame: 3,
                frames: 3,
            },
        ),
        (
            vec![vec![0, 1, 1, 2]],
            TrackSolveError::RepeatedFrame {
                frame: 1,
                first_track: 0,
                track: 0,
            },
        ),
        (
            vec![vec![0, 1], vec![1, 2]],
            TrackSolveError::RepeatedFrame {
                frame: 1,
                first_track: 0,
                track: 1,
            },
        ),
    ] {
        assert_eq!(
            solve_global_in_tracks(&[], 3, &opts, 0, &tracks),
            Err(error)
        );
    }
}

#[test]
fn disconnected_tracks_and_missing_neighbors_never_gain_coverage() {
    let truth = curved_truth(8, 0.0);
    let mut edges = edges_for(&[0, 2, 4], &truth);
    edges.extend(edges_for(&[5, 6, 7], &truth));
    let tracks = vec![vec![0, 1, 2, 3, 4], vec![7, 6, 5]];
    let plain = solve_global_in_tracks(&edges, 8, &options(0.0, None), 2, &tracks).unwrap();
    let smooth = solve_global_in_tracks(&edges, 8, &options(100.0, Some(1.0)), 2, &tracks).unwrap();
    assert_eq!(
        bits(&plain),
        bits(&smooth),
        "no complete original triple is admitted"
    );
    for (k, placement) in smooth.iter().enumerate() {
        assert_eq!(placement.is_some(), [0, 2, 4].contains(&k));
    }
    // Caller chooses any reference: a non-first pass is a valid component.
    let other = solve_global_in_tracks(&edges, 8, &options(1.0, Some(1.0)), 6, &tracks).unwrap();
    for (k, placement) in other.iter().enumerate() {
        assert_eq!(placement.is_some(), [5, 6, 7].contains(&k));
    }
    assert_eq!(other[5], Some(Similarity::IDENTITY));
    let isolated = solve_global_in_tracks(&edges, 8, &options(100.0, None), 1, &tracks).unwrap();
    assert_eq!(isolated.iter().flatten().count(), 1);
    assert_eq!(isolated[1], Some(Similarity::IDENTITY));
}

#[test]
fn pass_boundary_jump_survives_a_strong_prior_in_either_capture_direction() {
    let truth: Vec<_> = (0..8)
        .map(|k| {
            Similarity::from_params(SimilarityParams {
                ax: if k < 4 {
                    k as f64
                } else {
                    100.0 + (k - 4) as f64
                },
                ay: 0.0,
                g: 0.0,
                rot: 0.0,
            })
        })
        .collect();
    let edges = edges_for(&(0..8).collect::<Vec<_>>(), &truth);
    let opts = options(100.0, None);
    let flattened = solve_global_in_component(&edges, 8, &opts, 0).unwrap();
    let wrong = flattened[4].unwrap().corner_err(truth[4], geom());
    assert!(wrong > 10.0, "boundary control must discriminate: {wrong}");
    for second in [vec![4, 5, 6, 7], vec![7, 6, 5, 4]] {
        let solved =
            solve_global_in_tracks(&edges, 8, &opts, 0, &[vec![0, 1, 2, 3], second]).unwrap();
        for (got, want) in solved.iter().zip(&truth) {
            assert!(got.unwrap().corner_err(*want, geom()) < 1e-7);
        }
    }
}

#[test]
fn interleaving_global_indices_preserves_curved_tracks_and_robust_prior_weights() {
    let mut truth = curved_truth(5, 0.0);
    truth.extend(curved_truth(5, 80.0));
    let mut edges = edges_for(&(0..10).collect::<Vec<_>>(), &truth);
    perturb(&mut edges);
    let tracks = vec![vec![0, 1, 2, 3, 4], vec![9, 8, 7, 6, 5]];
    let opts = options(8.0, Some(0.3));
    let normal = solve_global_in_tracks(&edges, 10, &opts, 7, &tracks).unwrap();
    let no_prior = solve_global_in_tracks(&edges, 10, &options(0.0, None), 7, &tracks).unwrap();
    assert!(
        normal
            .iter()
            .zip(&no_prior)
            .any(|(a, b)| a.unwrap().corner_err(b.unwrap(), geom()) > 0.01)
    );
    let remap = |i: usize| if i < 5 { i * 2 } else { (i - 5) * 2 + 1 };
    let moved_edges: Vec<_> = edges
        .iter()
        .map(|e| AlignEdge {
            i: remap(e.i),
            j: remap(e.j),
            ..*e
        })
        .collect();
    let moved_tracks: Vec<Vec<_>> = tracks
        .iter()
        .map(|t| t.iter().map(|&i| remap(i)).collect())
        .collect();
    let interleaved =
        solve_global_in_tracks(&moved_edges, 10, &opts, remap(7), &moved_tracks).unwrap();
    for i in 0..10 {
        let error = normal[i]
            .unwrap()
            .corner_err(interleaved[remap(i)].unwrap(), geom());
        assert!(error < 1e-7, "track reindexing changed frame {i}: {error}");
    }
}

#[test]
fn box_guide_lift_matches_independent_absolute_coordinate_mapping() {
    let guide_transform = Similarity::from_params(SimilarityParams {
        ax: 0.5,
        ay: -0.75,
        g: 0.031,
        rot: -0.012,
    });
    for (reference, moving, factor) in [
        (
            PlaneGeometry {
                width: 719,
                height: 513,
            },
            PlaneGeometry {
                width: 733,
                height: 525,
            },
            8,
        ),
        (geom(), geom(), 4),
        (
            PlaneGeometry {
                width: 715,
                height: 523,
            },
            PlaneGeometry {
                width: 715,
                height: 523,
            },
            3,
        ),
    ] {
        let lifted =
            lift_box_decimated_similarity(guide_transform, reference, moving, factor).unwrap();
        let s = factor as f64;
        let half = (s - 1.0) * 0.5;
        for (x, y) in [
            (0.0, 0.0),
            (37.25, 81.5),
            (reference.width as f64 - 1.0, reference.height as f64 - 1.0),
        ] {
            let guide_centered = Cx::new(
                (x - half) / s - (reference.width / factor) as f64 * 0.5,
                (y - half) / s - (reference.height / factor) as f64 * 0.5,
            );
            let guide_moving = guide_transform.apply(guide_centered);
            let expected = Cx::new(
                s * (guide_moving.re + (moving.width / factor) as f64 * 0.5) + half,
                s * (guide_moving.im + (moving.height / factor) as f64 * 0.5) + half,
            );
            let actual = lifted.apply(Cx::new(
                x - reference.width as f64 * 0.5,
                y - reference.height as f64 * 0.5,
            )) + Cx::new(moving.width as f64 * 0.5, moving.height as f64 * 0.5);
            assert!((expected - actual).abs() < 1e-10);
        }
        let naive = Similarity {
            a: guide_transform.a,
            b: guide_transform.b.scale(s),
        };
        assert!(
            naive.corner_err(lifted, reference) > 0.01,
            "plant must expose omitted centre term"
        );
    }
    assert_eq!(
        lift_box_decimated_similarity(guide_transform, geom(), geom(), 1),
        Some(guide_transform)
    );
    assert!(lift_box_decimated_similarity(guide_transform, geom(), geom(), 0).is_none());
    assert!(lift_box_decimated_similarity(guide_transform, geom(), geom(), 10_000).is_none());
    assert!(
        lift_box_decimated_similarity(
            Similarity {
                a: Cx::ZERO,
                b: Cx::ZERO
            },
            geom(),
            geom(),
            4
        )
        .is_none()
    );
}

fn analytic_texture(x: f64, y: f64) -> f32 {
    (500.0
        + 91.0 * (0.173 * x + 0.079 * y).sin()
        + 73.0 * (0.097 * x - 0.231 * y).cos()
        + 48.0 * (0.307 * x + 0.137 * y).sin()
        + 31.0 * (0.053 * x - 0.331 * y).cos()) as f32
}

fn fit_bits(fit: &StageFit) -> [u64; 7] {
    [
        fit.fit.ax.to_bits(),
        fit.fit.ay.to_bits(),
        fit.fit.g.to_bits(),
        fit.fit.rot.to_bits(),
        u64::from(fit.rms.to_bits()),
        u64::from(fit.lever_rms.to_bits()),
        u64::from(fit.peak_mean.to_bits()),
    ]
}

#[test]
fn seeded_refinement_recovers_a_direct_pair_and_observation_is_nonperturbing() {
    let (w, h) = (240, 180);
    let full = PlaneGeometry {
        width: w,
        height: h,
    };
    let truth = Similarity::from_params(SimilarityParams {
        ax: 2.4,
        ay: -1.7,
        g: 0.004,
        rot: -0.002,
    });
    let inverse = truth.invert().unwrap();
    let mut reference = Vec::with_capacity(w * h);
    let mut moving = Vec::with_capacity(w * h);
    for y in 0..h {
        for x in 0..w {
            reference.push(analytic_texture(x as f64, y as f64));
            let (sx, sy) = inverse.apply_at(x as f64, y as f64, w as f64 * 0.5, h as f64 * 0.5);
            moving.push(analytic_texture(sx, sy));
        }
    }
    let reference = PlaneRef::from_geometry(&reference, full).unwrap();
    let moving = PlaneRef::from_geometry(&moving, full).unwrap();
    let cfg = AlignConfig {
        fine_tile: 24,
        fine_grid: (5, 4),
        fine_radius: 4,
        margin: 24,
        fine_iters: 4,
        warp_tiles: true,
        ..AlignConfig::shallow()
    };
    let spots = tile_grid(
        reference,
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin,
    )
    .unwrap();
    let seed = Similarity {
        b: truth.b + Cx::new(-0.8, 0.7),
        ..truth
    };
    let existing = fit_stage_iterated_impl(
        reference,
        moving,
        cfg.fine_tile,
        &spots,
        cfg.fine_radius,
        Some(seed.to_params()),
        &cfg,
        None,
    )
    .unwrap();
    let plain = refine_pair_observed(reference, moving, &spots, &cfg, seed, None).unwrap();
    let mut observed = None;
    let tapped = refine_pair_observed(
        reference,
        moving,
        &spots,
        &cfg,
        seed,
        Some(&mut |t| observed = Some(t.clone())),
    )
    .unwrap();
    assert_eq!(fit_bits(&plain), fit_bits(&existing));
    assert_eq!(fit_bits(&plain), fit_bits(&tapped));
    let error = plain.similarity().corner_err(truth, full);
    assert!(error < 0.35, "direct analytic pair error {error}");
    assert!(
        seed.corner_err(truth, full) > 1.0,
        "seed must need refinement"
    );
    let trace = observed.unwrap();
    assert!(!trace.fine_passes.is_empty());
    assert_eq!(fit_bits(trace.result.as_ref().unwrap()), fit_bits(&plain));

    let bad_seed = Similarity {
        b: Cx::new(10_000.0, 10_000.0),
        ..truth
    };
    let mut refused = None;
    assert!(
        refine_pair_observed(
            reference,
            moving,
            &spots,
            &cfg,
            bad_seed,
            Some(&mut |t| refused = Some(t.clone()))
        )
        .is_err()
    );
    assert!(matches!(
        refused.unwrap().termination,
        PairTermination::FineStageFailed { pass: 0, .. }
    ));
}

#[test]
fn seeded_refinement_refuses_flat_content_and_invalid_seed() {
    let flat = vec![500.0; 120 * 100];
    let plane = PlaneRef::new(&flat, 120, 100).unwrap();
    let cfg = AlignConfig {
        fine_tile: 16,
        fine_grid: (4, 3),
        fine_radius: 3,
        margin: 10,
        ..AlignConfig::shallow()
    };
    let spots = tile_grid(plane, 16, 4, 3, 10).unwrap();
    assert!(matches!(
        refine_pair_observed(plane, plane, &spots, &cfg, Similarity::IDENTITY, None),
        Err(AlignFailure::TooFewTiles { correlated: 0 })
    ));
    for seed in [
        Similarity {
            a: Cx::ZERO,
            b: Cx::ZERO,
        },
        Similarity {
            a: Cx::ONE,
            b: Cx::new(f64::NAN, 0.0),
        },
    ] {
        let mut trace = None;
        assert!(matches!(
            refine_pair_observed(
                plane,
                plane,
                &spots,
                &cfg,
                seed,
                Some(&mut |t| trace = Some(t.clone()))
            ),
            Err(AlignFailure::InvalidSeed)
        ));
        let trace = trace.unwrap();
        assert_eq!(trace.termination, PairTermination::InvalidSeed);
        assert!(trace.fine_passes.is_empty());
    }
}
