use super::super::registration::HeldOut;
use super::*;
fn nodes() -> Vec<Node> {
    (0..4)
        .map(|i| Node {
            acquisition: 10 + i as u64,
            color_pulls: [Similarity {
                a: Cx::new(1. + i as f64 * 0.001, i as f64 * 0.0002),
                b: Cx::new(i as f64 * 0.25, -i as f64 * 0.15),
            }; 3],
        })
        .collect()
}
fn domain() -> Domain {
    Domain {
        full: PlaneGeometry {
            width: 3516,
            height: 2344,
        },
        corners_sensor: [
            [1970., 2090.],
            [2162., 2090.],
            [1970., 2282.],
            [2162., 2282.],
        ],
    }
}
fn pair(nodes: &[Node], i: usize, j: usize, c: usize) -> PairEvidence {
    let kind = [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue][c];
    let fit = Similarity::relative(
        plane_pull(nodes[i].color_pulls[c], kind),
        plane_pull(nodes[j].color_pulls[c], kind),
    );
    PairEvidence {
        window: super::super::registration::Window {
            full: domain().full,
            center_sensor: [2066., 2186.],
            side_quad: 192,
        },
        input_color_pulls: [nodes[i].color_pulls[c], nodes[j].color_pulls[c]],
        acquisitions: [nodes[i].acquisition, nodes[j].acquisition],
        plane: kind,
        original_crop_origins: [[0; 2]; 2],
        trained_tiles: 8,
        heldout_tiles: (0..8)
            .map(|k| HeldOut {
                reference_quad_global: [
                    900. + (k % 2) as f64 * 900.,
                    900. + ((k / 2) % 2) as f64 * 700.,
                ],
                measured_moving_quad_global: [0.; 2],
                saved_error_anchor_sensor: [0.02, -0.01],
                refined_error_anchor_sensor: [0.; 2],
                peak: 0.99,
                information_ratio: 0.5,
            })
            .collect(),
        raw_fit_rms_source_quad: 0.01,
        fitted_pair_global: fit,
        maximum_saved_disagreement_sensor: 0.03,
        maximum_refined_disagreement_sensor: 0.01,
        saved_map_supported: true,
        refined_map_supported: true,
        refusal: None,
        reservation_bytes: 0,
    }
}
fn evidence(nodes: &[Node], list: &[(usize, usize)]) -> Vec<PairEvidence> {
    list.iter()
        .flat_map(|&(i, j)| (0..3).map(move |c| pair(nodes, i, j, c)))
        .collect()
}
#[test]
fn a01_chain_star_and_disconnected_cycle_are_not_an_anchor_certificate() {
    let n = nodes();
    for e in [
        vec![(0, 1), (1, 2), (2, 3)],
        vec![(0, 1), (0, 2), (0, 3)],
        vec![(1, 2), (2, 3), (3, 1)],
    ] {
        let g = certify(&n, 0, domain(), &evidence(&n, &e), Policy::default()).unwrap();
        assert!(g.sources.iter().all(|s| s.admitted_rgb == [false; 3]));
    }
}
#[test]
fn b01_direct_closed_triangles_have_explicit_anchor_relative_support() {
    let n = nodes();
    let e = evidence(&n, &[(0, 1), (0, 2), (0, 3), (1, 2), (2, 3)]);
    let g = certify(&n, 0, domain(), &e, Policy::default()).unwrap();
    assert!(g.sources.iter().all(|s| s.admitted_rgb == [true; 3]));
    assert_eq!(g.cycle_rank_rgb, [2; 3]);
    assert_eq!(g.passed_anchor_triangles_rgb, [2; 3]);
    assert_eq!(g.anchor_acquisition, 10);
    assert_eq!(g.sources[0].direct_anchor_max_error_sensor, [0.; 3]);
}
#[test]
fn c01_inconsistent_cycle_or_one_color_loss_refuses_that_channel() {
    let n = nodes();
    let mut e = evidence(&n, &[(0, 1), (0, 2), (1, 2)]);
    e.iter_mut()
        .find(|p| p.acquisitions == [11, 12] && p.plane == PlaneKind::Blue)
        .unwrap()
        .fitted_pair_global
        .as_mut()
        .unwrap()
        .b
        .re += 0.25;
    let g = certify(&n, 0, domain(), &e, Policy::default()).unwrap();
    for s in &g.sources[..3] {
        assert_eq!(s.admitted_rgb, [true, true, false]);
    }
    assert_eq!(g.sources[3].admitted_rgb, [false; 3]);
    assert!(g.maximum_cycle_error_sensor_rgb[2] > 0.4);
    e.iter_mut()
        .find(|p| p.acquisitions == [10, 11] && p.plane == PlaneKind::GreenLuma)
        .unwrap()
        .heldout_tiles[0]
        .saved_error_anchor_sensor = [0.5, 0.];
    let g = certify(&n, 0, domain(), &e, Policy::default()).unwrap();
    assert!(g.sources.iter().all(|s| !s.admitted_rgb[1]));
}
#[test]
fn c02_duplicate_identity_pair_and_unknown_acquisition_refuse() {
    let n = nodes();
    let mut e = evidence(&n, &[(0, 1), (0, 2), (1, 2)]);
    e.push(pair(&n, 1, 0, 0));
    assert!(certify(&n, 0, domain(), &e, Policy::default()).is_err());
    e.pop();
    e[0].acquisitions[0] = 99;
    assert!(certify(&n, 0, domain(), &e, Policy::default()).is_err());
    let mut n = nodes();
    n[1].acquisition = n[0].acquisition;
    assert!(certify(&n, 0, domain(), &[], Policy::default()).is_err());
}

#[test]
fn c03_mismatched_binding_and_extrapolated_domain_cannot_certify() {
    let n = nodes();
    let mut e = evidence(&n, &[(0, 1), (0, 2), (1, 2)]);
    e[0].input_color_pulls[0].b.re += 0.001;
    assert!(certify(&n, 0, domain(), &e, Policy::default()).is_err());
    let e = evidence(&n, &[(0, 1), (0, 2), (1, 2)]);
    let far = Domain {
        corners_sensor: [[4000., 100.], [4100., 100.], [4000., 200.], [4100., 200.]],
        ..domain()
    };
    let g = certify(&n, 0, far, &e, Policy::default()).unwrap();
    assert!(g.sources.iter().all(|s| s.admitted_rgb == [false; 3]));
}

#[test]
fn b02_sixty_four_nodes_use_direct_edges_and_return_consuming_pulls_with_checked_budget() {
    let nodes: Vec<_> = (0..64)
        .map(|i| Node {
            acquisition: i as u64,
            color_pulls: [Similarity::IDENTITY; 3],
        })
        .collect();
    let links: Vec<_> = (1..64)
        .map(|i| (0, i))
        .chain((1..63).map(|i| (i, i + 1)))
        .collect();
    let pairs = evidence(&nodes, &links);
    let result = certify(&nodes, 0, domain(), &pairs, Policy::default()).unwrap();
    assert_eq!(result.sources.len(), 64);
    assert!(result.sources.iter().all(|s| s.admitted_rgb == [true; 3]));
    assert!(result.reservation_bytes < 2 << 20);
    for (s, n) in result.sources.iter().zip(&nodes) {
        for c in 0..3 {
            assert!(same_pull(s.consuming_color_pulls[c], n.color_pulls[c]));
        }
    }
    assert!(
        certify(
            &nodes,
            0,
            domain(),
            &pairs,
            Policy {
                budget_bytes: 1,
                ..Policy::default()
            }
        )
        .is_err()
    );
    assert!(reservation_bytes(65).is_err());
    assert!(reservation_bytes(usize::MAX).is_err());
}
