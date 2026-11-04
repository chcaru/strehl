use super::*;

fn mesh(width: usize, height: usize, columns: usize, rows: usize) -> ForwardMesh {
    let vertices = (0..rows)
        .flat_map(|y| {
            (0..columns).map(move |x| {
                [
                    (width - 1) as f64 * x as f64 / (columns - 1) as f64,
                    (height - 1) as f64 * y as f64 / (rows - 1) as f64,
                ]
            })
        })
        .collect();
    ForwardMesh::new(
        PlaneGeometry { width, height },
        columns,
        rows,
        vertices,
        vec![Visibility::SingleView; (columns - 1) * (rows - 1)],
        vec![
            FocusEvidence {
                ordinal: 0.,
                width: 1.,
                usable: true
            };
            columns * rows
        ],
    )
    .unwrap()
}
fn measure(meshes: &mut [ForwardMesh], points: &[Point]) -> ValidationReport {
    let observations: Vec<_> = points
        .iter()
        .map(|&p| Correspondence {
            pass_a: 0,
            point_a: p,
            pass_b: 1,
            point_b: p,
            weight: 1.,
            role: ObservationRole::Heldout,
        })
        .collect();
    validate_observations(meshes, &observations, &[], MeshValidation::default()).unwrap()
}
fn index(mesh: &ForwardMesh) -> BackwardMesh {
    BackwardMesh::new(
        mesh,
        MeshValidation::default(),
        IndexLimits {
            bin_side: 64,
            max_bins: 10000,
            max_entries: 100000,
        },
    )
    .unwrap()
}

#[test]
fn hull_shape_refuses_collinear_skinny_clustered_and_duplicate_witnesses() {
    for points in [
        [[80., 80.], [250., 250.], [420., 420.]],
        [[80., 80.], [250., 81.], [420., 80.]],
        [[200., 200.], [210., 200.], [200., 210.]],
        [[80., 80.], [80., 80.], [420., 420.]],
        [[60., 80.], [440., 80.], [250., 200.]], // area alone passes; y span fails.
    ] {
        let mut meshes = vec![mesh(501, 501, 2, 2); 2];
        // Measured-curvature scale from the marigold FIT-only census. Shape
        // refusal must persist under a smooth curved common coordinate gauge.
        for m in &mut meshes {
            for p in &mut m.vertices {
                p[0] += 13.5906 * (p[0] / 296.269).sin() * (p[1] / 296.269).sin();
                p[1] += 13.5906 * (p[0] / 296.269).cos() * (p[1] / 296.269).sin();
            }
        }
        let report = measure(&mut meshes, &points);
        assert_eq!(report.heldout_observations, 3);
        assert!(report.join_support.iter().all(|s| !s.qualified));
        assert!(
            meshes
                .iter()
                .all(|m| m.visibility[0] == Visibility::SingleView && m.join_hulls[0].is_empty())
        );
    }
}

#[test]
fn qualified_hull_limits_blending_without_creating_single_view_holes() {
    let points = [[80., 80.], [420., 100.], [120., 420.]];
    let mut meshes = vec![mesh(501, 501, 2, 2); 2];
    let report = measure(&mut meshes, &points);
    assert!(
        report
            .join_support
            .iter()
            .all(|s| s.qualified && s.area_fraction > 0.2)
    );
    let backward = index(&meshes[0]);
    for p in [[150., 150.], points[0], points[1]] {
        assert!(backward.join_supported(0, p));
    }
    assert!(!backward.join_supported(0, [450., 450.]));
    assert!(
        matches!(backward.map([450., 450.]), MappedPoint::Supported { .. }),
        "outside the certificate retains its continuous original-view geometry"
    );
    assert!(!backward.join_supported(0, [80. - 1e-5, 80.]));
    assert_eq!(meshes[0].join_hulls[0], report.join_support[0].hull);
    // A caller's cell label with no measured hull cannot fabricate a certificate.
    meshes[0].join_hulls[0].clear();
    let without = index(&meshes[0]);
    assert_eq!(without.cell_visibility(0), Some(Visibility::SingleView));
    assert!(!without.join_supported(0, [150., 150.]));
}

#[test]
fn border_cell_normalizes_by_actual_physical_dimensions_and_depth_jump_refuses() {
    let mut meshes = vec![mesh(302, 202, 4, 3); 2];
    let cell = 5;
    let bounds = cell_bounds(&meshes[0], cell).unwrap();
    let size = sub(bounds.max, bounds.min);
    let points = [[0.1, 0.1], [0.8, 0.2], [0.2, 0.8]].map(|p| {
        [
            bounds.min[0] + size[0] * p[0],
            bounds.min[1] + size[1] * p[1],
        ]
    });
    let report = measure(&mut meshes, &points);
    for support in &report.join_support {
        assert_eq!(support.cell, cell);
        assert!(support.qualified);
        assert!((support.area_fraction - 0.24).abs() < 1e-12);
        assert!(
            support
                .span_fraction
                .into_iter()
                .all(|s| (s - 0.7).abs() < 1e-12)
        );
    }
    let mut observations: Vec<_> = points
        .iter()
        .map(|&p| Correspondence {
            pass_a: 0,
            point_a: p,
            pass_b: 1,
            point_b: p,
            weight: 1.,
            role: ObservationRole::Heldout,
        })
        .collect();
    observations[2].point_b[0] += 8.;
    let report =
        validate_observations(&mut meshes, &observations, &[], MeshValidation::default()).unwrap();
    assert!(report.maximum_heldout_error > 7.);
    assert!(
        meshes
            .iter()
            .all(|m| m.visibility[cell] == Visibility::HeldoutFailure
                && m.join_hulls[cell].is_empty())
    );
}
