use super::*;

fn grid(columns: usize, rows: usize, offset: Point) -> ForwardMesh {
    let source = PlaneGeometry {
        width: 101,
        height: 81,
    };
    let vertices = (0..rows)
        .flat_map(|y| {
            (0..columns).map(move |x| {
                [
                    100.0 * x as f64 / (columns - 1) as f64 + offset[0],
                    80.0 * y as f64 / (rows - 1) as f64 + offset[1],
                ]
            })
        })
        .collect();
    ForwardMesh::new(
        source,
        columns,
        rows,
        vertices,
        vec![Visibility::SingleView; (columns - 1) * (rows - 1)],
        vec![
            FocusEvidence {
                ordinal: 0.0,
                width: 1.0,
                usable: true
            };
            columns * rows
        ],
    )
    .unwrap()
}
fn index(mesh: &ForwardMesh) -> BackwardMesh {
    BackwardMesh::new(
        mesh,
        MeshValidation::default(),
        IndexLimits {
            bin_side: 16,
            max_bins: 100_000,
            max_entries: 100_000,
        },
    )
    .unwrap()
}
fn observations(shift: Point, role: ObservationRole) -> Vec<Correspondence> {
    (1..8)
        .flat_map(|y| {
            (1..10).map(move |x| {
                let p = [f64::from(x) * 10.0, f64::from(y) * 10.0];
                Correspondence {
                    pass_a: 0,
                    point_a: p,
                    pass_b: 1,
                    point_b: [p[0] - shift[0], p[1] - shift[1]],
                    weight: 1.0,
                    role,
                }
            })
        })
        .collect()
}

#[test]
fn canvas_is_signed_union_and_refuses_explosion() {
    let bounds = [
        Bounds {
            min: [-31.2, -7.4],
            max: [68.8, 72.6],
        },
        Bounds {
            min: [20.0, 0.0],
            max: [120.0, 80.0],
        },
    ];
    let canvas = MosaicCanvas::from_bounds(
        &bounds,
        CanvasLimits {
            max_side: 1000,
            max_pixels: 100_000,
        },
    )
    .unwrap();
    assert_eq!(
        canvas,
        MosaicCanvas {
            origin: [-32, -8],
            width: 152,
            height: 88
        }
    );
    assert_eq!(canvas.world(0.25, 0.75), [-31.75, -7.25]);
    assert!(canvas.width > 100); // A hidden intersection implementation fails.
    assert!(
        MosaicCanvas::from_bounds(
            &bounds,
            CanvasLimits {
                max_side: 100,
                max_pixels: 100_000
            }
        )
        .is_err()
    );
    assert!(
        MosaicCanvas::from_bounds(
            &bounds,
            CanvasLimits {
                max_side: 1000,
                max_pixels: 100
            }
        )
        .is_err()
    );
    assert!(
        MosaicCanvas::from_bounds(
            &[Bounds {
                min: [0.0, 0.0],
                max: [f64::INFINITY, 1.0]
            }],
            CanvasLimits {
                max_side: usize::MAX,
                max_pixels: usize::MAX
            }
        )
        .is_err()
    );
}

#[test]
fn tile_plan_covers_union_once_and_preserves_global_pyramid_phase() {
    let canvas = MosaicCanvas {
        origin: [-37, 13],
        width: 307,
        height: 219,
    };
    let plan = MosaicTilePlan::new(canvas, 71, 3, 29, 200 * 200, 100).unwrap();
    let mut coverage = vec![0_u8; canvas.width * canvas.height];
    let mut would_fail_local_phase = false;
    for tile in &plan.tiles {
        assert_eq!(tile.work.x % 8, 0);
        assert_eq!(tile.work.y % 8, 0);
        would_fail_local_phase |= tile.core.x % 8 != 0;
        let right = tile.work.x + tile.work.width;
        let bottom = tile.work.y + tile.work.height;
        assert!(tile.work.x <= tile.core.x.saturating_sub(29));
        assert!(tile.work.y <= tile.core.y.saturating_sub(29));
        assert!(right >= (tile.core.x + tile.core.width + 29).min(canvas.width));
        assert!(bottom >= (tile.core.y + tile.core.height + 29).min(canvas.height));
        for y in tile.core.y..tile.core.y + tile.core.height {
            for x in tile.core.x..tile.core.x + tile.core.width {
                coverage[y * canvas.width + x] += 1;
            }
        }
    }
    assert!(would_fail_local_phase);
    assert!(coverage.iter().all(|&count| count == 1));
    assert!(MosaicTilePlan::new(canvas, 71, 3, 29, 50, 100).is_err());
    assert!(MosaicTilePlan::new(canvas, 71, usize::BITS, 29, 40_000, 100).is_err());
    assert!(MosaicTilePlan::new(canvas, 1, 3, 29, 40_000, 1).is_err());
}

#[test]
fn backward_mesh_roundtrip_retains_subpixel_sites_and_shared_edges() {
    let mut mesh = grid(5, 4, [-33.75, 11.125]);
    for (i, p) in mesh.vertices.iter_mut().enumerate() {
        let x = (i % 5) as f64;
        let y = (i / 5) as f64;
        p[0] += 0.07 * y * y;
        p[1] += 0.05 * x * x;
    }
    let backward = index(&mesh);
    for p in [
        [0.0, 0.0],
        [100.0, 80.0],
        [25.0, 80.0 / 3.0],
        [13.25, 21.75],
        [87.75, 62.25],
    ] {
        let world = mesh.map_source(p).unwrap();
        match backward.map(world) {
            MappedPoint::Supported { source, .. } => assert!(norm(sub(source, p)) < 1e-10),
            other => panic!("expected supported roundtrip, got {other:?}"),
        }
    }
    assert_eq!(backward.map([-500.0, 10.0]), MappedPoint::Uncovered);
}

#[test]
fn invalid_visibility_is_not_a_black_sample_and_cannot_be_cleared_by_fit() {
    let mut meshes = vec![grid(2, 2, [0.0, 0.0]), grid(2, 2, [0.0, 0.0])];
    meshes[0].visibility[0] = Visibility::Disoccluded;
    meshes[1].visibility[0] = Visibility::AmbiguousFocus;
    let report = validate_observations(
        &mut meshes,
        &observations([0.0, 0.0], ObservationRole::Heldout),
        &[],
        MeshValidation::default(),
    )
    .unwrap();
    assert_eq!(report.usable_cells, 0);
    assert_eq!(
        index(&meshes[0]).map([23.25, 25.5]),
        MappedPoint::Rejected(Visibility::Disoccluded)
    );
    assert_eq!(
        index(&meshes[1]).map([23.25, 25.5]),
        MappedPoint::Rejected(Visibility::AmbiguousFocus)
    );
}

#[test]
fn backward_mesh_refuses_folds_stretch_and_multiple_inverse_surfaces() {
    let mut mirror = grid(2, 2, [0.0, 0.0]);
    for p in &mut mirror.vertices {
        p[0] = 100.0 - p[0];
    }
    assert_eq!(
        index(&mirror).map([20.0, 30.0]),
        MappedPoint::Rejected(Visibility::Fold)
    );
    let mut stretched = grid(2, 2, [0.0, 0.0]);
    for p in &mut stretched.vertices {
        p[0] *= 8.0;
    }
    assert_eq!(
        index(&stretched).map([20.0, 30.0]),
        MappedPoint::Rejected(Visibility::ExcessiveStretch)
    );
    let mut overlap = grid(4, 2, [0.0, 0.0]);
    for (i, p) in overlap.vertices.iter_mut().enumerate() {
        p[0] = [0.0, 40.0, 10.0, 50.0][i % 4];
    }
    assert_eq!(index(&overlap).map([20.0, 30.0]), MappedPoint::Ambiguous);
}

#[test]
fn malformed_mesh_and_index_budgets_are_refused_before_allocating() {
    let mut mesh = grid(4, 3, [0.0, 0.0]);
    assert!(
        BackwardMesh::new(
            &mesh,
            MeshValidation::default(),
            IndexLimits {
                bin_side: 1,
                max_bins: 10,
                max_entries: 1_000_000
            }
        )
        .is_err()
    );
    assert!(
        BackwardMesh::new(
            &mesh,
            MeshValidation::default(),
            IndexLimits {
                bin_side: 16,
                max_bins: 1000,
                max_entries: 4
            }
        )
        .is_err()
    );
    mesh.vertices.pop();
    assert!(mesh.validate().is_err());
    assert!(
        BackwardMesh::new(
            &mesh,
            MeshValidation::default(),
            IndexLimits {
                bin_side: 16,
                max_bins: 1000,
                max_entries: 1000
            }
        )
        .is_err()
    );
}

#[test]
fn compiled_cell_visibility_exposes_shape_refusals_without_fabricating_cells() {
    let mut mesh = grid(2, 2, [0.0, 0.0]);
    assert_eq!(
        index(&mesh).cell_visibility(0),
        Some(Visibility::SingleView)
    );
    for point in &mut mesh.vertices {
        point[0] = 100.0 - point[0];
    }
    let backward = index(&mesh);
    assert_eq!(backward.cell_visibility(0), Some(Visibility::Fold));
    assert_eq!(backward.cell_visibility(1), None);
    assert_eq!(backward.cell_visibility(usize::MAX), None);
}

#[test]
fn heldout_and_measured_loop_failures_remain_local() {
    let mut meshes = vec![grid(3, 2, [0.0, 0.0]), grid(3, 2, [0.0, 0.0])];
    for mesh in &mut meshes {
        mesh.visibility.fill(Visibility::Unverified);
    }
    let mut samples = observations([0.0, 0.0], ObservationRole::Heldout);
    samples.push(Correspondence {
        pass_a: 0,
        point_a: [20.0, 20.0],
        pass_b: 1,
        point_b: [22.0, 20.0],
        weight: 1.0,
        role: ObservationRole::Heldout,
    });
    let report =
        validate_observations(&mut meshes, &samples, &[], MeshValidation::default()).unwrap();
    assert_eq!(report.maximum_heldout_error, 2.0);
    assert_eq!(
        meshes[0].visibility,
        vec![Visibility::HeldoutFailure, Visibility::ValidatedOverlap]
    );
    let loops = [LoopWitness {
        pass: 0,
        source: [75.0, 20.0],
        error: 3.0,
    }];
    let report =
        validate_observations(&mut meshes, &samples, &loops, MeshValidation::default()).unwrap();
    assert_eq!(report.measured_loop_witnesses, 1);
    assert_eq!(meshes[0].visibility[1], Visibility::LoopFailure);
    assert_eq!(meshes[1].visibility[1], Visibility::ValidatedOverlap);
}

#[test]
fn training_constraints_cannot_qualify_an_overlap() {
    let mut meshes = vec![grid(2, 2, [0.0, 0.0]), grid(2, 2, [0.0, 0.0])];
    for mesh in &mut meshes {
        mesh.visibility.fill(Visibility::Unverified);
    }
    let report = validate_observations(
        &mut meshes,
        &observations([0.0, 0.0], ObservationRole::Fit),
        &[],
        MeshValidation::default(),
    )
    .unwrap();
    assert_eq!(report.heldout_observations, 0);
    assert_eq!(report.usable_cells, 0);
    assert_eq!(
        index(&meshes[0]).map([20.0, 20.0]),
        MappedPoint::Rejected(Visibility::Unverified)
    );
}

#[test]
fn joint_fit_uses_both_passes_without_a_primary_and_ignores_heldout_labels() {
    let seeds = vec![grid(5, 4, [0.0, 0.0]), grid(5, 4, [0.0, 0.0])];
    let fit = observations([6.0, -2.0], ObservationRole::Fit);
    let (a, report) = fit_meshes(&seeds, &fit, MeshFitOptions::default()).unwrap();
    assert_eq!(report.fitted_observations, fit.len());
    assert!(report.fit_rms < 0.1, "{}", report.fit_rms);
    assert!(report.maximum_displacement > 2.0);
    let sum: Point = a
        .iter()
        .zip(&seeds)
        .fold([0.0; 2], |mut total, (mesh, seed)| {
            for (p, q) in mesh.vertices.iter().zip(&seed.vertices) {
                for axis in 0..2 {
                    total[axis] += p[axis] - q[axis];
                }
            }
            total
        });
    assert!(
        norm(sum) < 1e-6,
        "the symmetric deformation gauge drifted: {sum:?}"
    );
    for mesh in &a {
        assert!(norm(sub(mesh.vertices[7], seeds[0].vertices[7])) > 1.0);
    }
    let mut poisoned_holdout = fit;
    poisoned_holdout.extend(observations([-8.0, 6.0], ObservationRole::Heldout));
    let (b, _) = fit_meshes(&seeds, &poisoned_holdout, MeshFitOptions::default()).unwrap();
    assert_eq!(a[0].vertices, b[0].vertices);
    assert_eq!(a[1].vertices, b[1].vertices);
    let mut b = b;
    assert!(
        validate_observations(&mut b, &poisoned_holdout, &[], MeshValidation::default())
            .unwrap()
            .maximum_heldout_error
            > 10.0
    );
}

#[test]
fn focus_regularizer_preserves_a_planted_parallax_change_better_than_constant_focus() {
    let mut seeds = vec![grid(9, 5, [0.0, 0.0]), grid(9, 5, [0.0, 0.0])];
    for mesh in &mut seeds {
        for (i, focus) in mesh.focus.iter_mut().enumerate() {
            focus.ordinal = if i % 9 < 4 { 0.0 } else { 100.0 };
            focus.width = 0.1;
        }
    }
    let mut samples = Vec::new();
    for y in [10.0, 25.0, 40.0, 55.0, 70.0] {
        for x in [12.0, 20.0, 28.0, 66.0, 74.0, 82.0, 90.0] {
            let displacement = if x < 40.0 { 4.0 } else { -4.0 };
            samples.push(Correspondence {
                pass_a: 0,
                point_a: [x, y],
                pass_b: 1,
                point_b: [x - displacement, y],
                weight: 1.0,
                role: ObservationRole::Fit,
            });
        }
    }
    let options = MeshFitOptions {
        smoothness: 50.0,
        huber_delta: 20.0,
        tether: 0.001,
        ..MeshFitOptions::default()
    };
    let (_, informed) = fit_meshes(&seeds, &samples, options).unwrap();
    for mesh in &mut seeds {
        for focus in &mut mesh.focus {
            focus.ordinal = 0.0;
        }
    }
    let (_, placebo) = fit_meshes(&seeds, &samples, options).unwrap();
    assert!(
        placebo.fit_rms > 0.5,
        "plant must expose the depth-blind smoothing failure"
    );
    assert!(
        informed.fit_rms < placebo.fit_rms * 0.5,
        "focus={} constant={}",
        informed.fit_rms,
        placebo.fit_rms
    );
}

#[test]
fn disconnected_graph_budget_and_nonfinite_observations_are_refused() {
    let mut seeds = vec![
        grid(3, 3, [0.0, 0.0]),
        grid(3, 3, [0.0, 0.0]),
        grid(3, 3, [0.0, 0.0]),
    ];
    let samples = observations([1.0, 0.0], ObservationRole::Fit);
    assert!(fit_meshes(&seeds, &samples, MeshFitOptions::default()).is_err());
    seeds.pop();
    assert!(
        fit_meshes(
            &seeds,
            &samples,
            MeshFitOptions {
                max_work_bytes: 1,
                ..MeshFitOptions::default()
            }
        )
        .is_err()
    );
    let mut broken = samples;
    broken[0].point_a[0] = f64::NAN;
    assert!(fit_meshes(&seeds, &broken, MeshFitOptions::default()).is_err());
}
