use super::super::super::{registration_global, registration_graph};
use super::*;

fn wide_window() -> Window {
    Window {
        full: PlaneGeometry {
            width: 512,
            height: 512,
        },
        center_sensor: [478.5, 542.5],
        side_quad: 384,
    }
}
fn wide_policy() -> Policy {
    Policy {
        geometry_lowpass_sigma_quad: 1.2,
        tile_quad: 46,
        grid_axis: 5,
        ..Policy::default()
    }
}
fn wide_raw(t: Similarity, f: &dyn Fn(f64, f64) -> f64) -> Raw {
    raw_with_geometry([t; 3], f, wide_window().full)
}
fn broad_scene(x: f64, y: f64) -> f64 {
    scene(x * 0.5, y * 0.5)
}

#[test]
fn a01_wide_geometry_still_refuses_flat_clipped_and_one_axis_first() {
    let identity = Similarity::IDENTITY;
    let signals: [&dyn Fn(f64, f64) -> f64; 3] = [&|_, _| 6000., &|_, _| 65000., &|x, _| {
        6000. + 1100. * (0.071 * x).cos()
    }];
    for signal in signals {
        let a = wide_raw(identity, signal);
        let b = wide_raw(transform(), signal);
        let result = measure_pair_with_footprints(
            &view(&a, 1, [identity; 3]),
            &view(&b, 2, [transform(); 3]),
            wide_window(),
            PlaneKind::Red,
            wide_policy(),
        )
        .unwrap();
        assert!(!result.evidence.saved_map_supported);
        assert!(!result.evidence.refined_map_supported);
        assert_eq!(result.footprints.side_quad, 384);
    }
}

#[test]
fn b01_wide_measured_curvature_has_direct_triangle_and_original_holdouts() {
    // Log-scale/angle quadratic coefficients measured on the predeclared
    // tilted-chart sources29..35, centered at32. This is a geometry plant,
    // not a calibration or a claim about photographic transfer.
    let transforms: Vec<_> = [-3f64, 0., 3.]
        .iter()
        .map(|&k| {
            let scale = (-0.0006005232054385012 * k + 3.404974052523214e-6 * k * k).exp();
            let angle = 2.9939791346775986e-5 * k + 2.2789681287579972e-7 * k * k;
            Similarity {
                a: Cx::new(scale * angle.cos(), scale * angle.sin()),
                b: Cx::new(0.11 * k, -0.07 * k),
            }
        })
        .collect();
    let sources: Vec<_> = transforms
        .iter()
        .map(|&t| wide_raw(t, &broad_scene))
        .collect();
    let mut witnesses = Vec::new();
    for i in 0..3 {
        for j in i + 1..3 {
            for color in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
                let witness = measure_pair_with_footprints(
                    &view(&sources[i], i as u64, [transforms[i]; 3]),
                    &view(&sources[j], j as u64, [transforms[j]; 3]),
                    wide_window(),
                    color,
                    wide_policy(),
                )
                .unwrap();
                assert!(
                    witness.evidence.saved_map_supported,
                    "{:?}",
                    witness.evidence
                );
                assert!(
                    witness.evidence.refined_map_supported,
                    "{:?}",
                    witness.evidence
                );
                assert!(witness.evidence.heldout_tiles.len() >= 4);
                for channel in 0..2 {
                    assert!(
                        witness.footprints.training[channel]
                            .iter()
                            .zip(&witness.footprints.heldout[channel])
                            .all(|(a, b)| a & b == 0)
                    );
                }
                witnesses.push(witness);
            }
        }
    }
    let nodes: Vec<_> = transforms
        .iter()
        .enumerate()
        .map(|(i, &t)| registration_graph::Node {
            acquisition: i as u64,
            color_pulls: [t; 3],
        })
        .collect();
    let domain = registration_graph::Domain {
        full: wide_window().full,
        corners_sensor: [
            [382.5, 446.5],
            [574.5, 446.5],
            [382.5, 638.5],
            [574.5, 638.5],
        ],
    };
    let reserved = registration_global::reservation_bytes(3, witnesses.len(), 384).unwrap();
    assert!(reserved < 64 << 20);
    assert!(
        registration_global::solve(
            &nodes,
            1,
            domain,
            &witnesses,
            registration_graph::Policy::default(),
            reserved - 1
        )
        .is_err()
    );
    let solved = registration_global::solve(
        &nodes,
        1,
        domain,
        &witnesses,
        registration_graph::Policy::default(),
        64 << 20,
    )
    .unwrap();
    assert_eq!(solved.training_cycle_rank_rgb, [1; 3]);
    assert_eq!(solved.certificate.cycle_rank_rgb, [1; 3]);
    assert!(
        solved
            .certificate
            .sources
            .iter()
            .all(|s| s.admitted_rgb.iter().all(|v| *v))
    );
}

#[test]
fn c01_wide_wrong_map_spatial_mismatch_and_budget_are_not_certified() {
    let identity = Similarity::IDENTITY;
    let actual = transform();
    let a = wide_raw(identity, &broad_scene);
    let b = wide_raw(actual, &broad_scene);
    let mut wrong = actual;
    wrong.b.re += 0.35;
    wrong.b.im -= 0.2;
    let result = measure_pair(
        &view(&a, 1, [identity; 3]),
        &view(&b, 2, [wrong; 3]),
        wide_window(),
        PlaneKind::Red,
        wide_policy(),
    )
    .unwrap();
    assert!(!result.saved_map_supported);
    // Recovery is not guaranteed: the unchanged estimator can still refuse
    // its corrected map at the strict held residual boundary. This control's
    // requirement is that a fitted training solution cannot certify the bad
    // supplied placement; the known-map triangle above is the positive arm.
    assert!(result.fitted_pair_global.is_some());
    assert!(result.maximum_saved_disagreement_sensor > 0.5);
    let inconsistent = wide_raw(identity, &|x, y| {
        broad_scene(x + if y > 542.5 { 1.8 } else { -1.8 }, y)
    });
    let refused = measure_pair(
        &view(&a, 1, [identity; 3]),
        &view(&inconsistent, 2, [identity; 3]),
        wide_window(),
        PlaneKind::Red,
        wide_policy(),
    )
    .unwrap();
    assert!(!refused.saved_map_supported);
    assert!(!refused.refined_map_supported, "{refused:?}");
    let need = reservation_bytes(wide_window()).unwrap();
    assert!(
        measure_pair(
            &view(&a, 1, [identity; 3]),
            &view(&b, 2, [actual; 3]),
            wide_window(),
            PlaneKind::Red,
            Policy {
                budget_bytes: need - 1,
                ..wide_policy()
            }
        )
        .is_err()
    );
    assert!(
        measure_pair(
            &view(&a, 1, [identity; 3]),
            &view(&b, 2, [actual; 3]),
            Window {
                side_quad: 385,
                ..wide_window()
            },
            PlaneKind::Red,
            wide_policy()
        )
        .is_err()
    );
}
