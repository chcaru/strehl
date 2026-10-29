use super::*;

fn texture(x: f64, y: f64) -> f32 {
    let mut value = 1000.0;
    for i in 1..=17 {
        let k = i as f64;
        value += 35.0
            * ((0.065 + 0.023 * k) * x + (0.047 + 0.019 * (i * i % 19) as f64) * y + k * 2.17)
                .sin();
        value += 25.0
            * ((0.041 + 0.017 * (i * 7 % 23) as f64) * x - (0.061 + 0.013 * k) * y + k * 0.71)
                .cos();
    }
    value as f32
}

fn centered(linear: [f64; 4], p: [f64; 2], q: [f64; 2]) -> Affine {
    let [a, b, c, d] = linear;
    Affine([
        a,
        b,
        c,
        d,
        q[0] - a * p[0] - b * p[1],
        q[1] - c * p[0] - d * p[1],
    ])
}

#[test]
fn affine_actual_image_warp_recovers_anisotropy_and_exposes_similarity_foil() {
    let g = PlaneGeometry {
        width: 384,
        height: 320,
    };
    let p = [192.0, 160.0];
    let q = [195.25, 157.5];
    let truth = centered([1.06, 0.10, -0.025, 0.91], p, q);
    let inverse = truth.inverse().unwrap();
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(x as f64, y as f64)))
        .collect();
    let b: Vec<_> = (0..g.height)
        .flat_map(|y| {
            (0..g.width).map(move |x| {
                let u = inverse.apply([x as f64, y as f64]);
                texture(u[0], u[1])
            })
        })
        .collect();
    let a = PlaneRef::from_geometry(&a, g).unwrap();
    let b = PlaneRef::from_geometry(&b, g).unwrap();
    let seed = anchored_seed(Cx::new(0.985, -0.0625), p, [195.8, 157.0], g);
    let config = MosaicGeometryConfig {
        native_affine: true,
        ..Default::default()
    };
    let mut trace = Vec::new();
    let actual = refine(a, b, p, q, seed, &config, None, None, &mut trace).unwrap();
    let error = (actual.0[0] - q[0]).hypot(actual.0[1] - q[1]);
    assert!(error < 0.15, "affine placement {actual:?}, truth {q:?}");
    assert!(actual.3 < 0.2, "independent loop {actual:?}");
    assert!(
        trace
            .iter()
            .all(|t| t.affine_seed.is_some() && !t.affine_footprints.is_empty())
    );
    assert!(trace.iter().any(|t| t.attempted_passes > 1));
    let fitted = Affine(
        trace
            .iter()
            .rev()
            .find(|t| t.direction == "forward-affine")
            .unwrap()
            .affine_fit
            .unwrap(),
    );
    // These fractional points are absent from the nine measured tile centers.
    // Their independent planted positions challenge extra affine parameters.
    for offset in [[-11.3, 7.7], [13.8, -9.4], [5.2, 12.1]] {
        let at = [p[0] + offset[0], p[1] + offset[1]];
        let found = fitted.apply(at);
        let expected = truth.apply(at);
        assert!((found[0] - expected[0]).hypot(found[1] - expected[1]) < 0.2);
    }
    let foil = super::super::refine_on_planes(a, b, p, q, seed, &config, None);
    assert!(
        foil.is_err(),
        "plant must expose the missing affine image degrees of freedom: {foil:?}"
    );
    let encoded = serde_json::to_vec(&trace).unwrap();
    let decoded: Vec<NativeMeasurement> = serde_json::from_slice(&encoded).unwrap();
    assert_eq!(decoded[0].affine_seed, trace[0].affine_seed);
    assert_eq!(decoded[0].affine_footprints, trace[0].affine_footprints);
}

#[test]
fn independent_descriptor_coordinates_nominate_native_without_generated_extrapolation() {
    let mut candidate = CoarseCorrespondence {
        id: "independent-original-feature".into(),
        pass_a: 0,
        pass_b: 1,
        point_a_quad: [128.0, 112.0],
        point_b_quad: [131.25, 109.5],
        source_a: 0,
        source_b: 1,
        focus_a: None,
        focus_b: None,
        role: super::super::super::MatchRole::Heldout,
        spatial_blocks: [[0, 0]; 2],
        descriptor_distance: 0.1,
        seed_residual_quad: 80.0,
        within_seed_support: false,
        grid_nomination: false,
        spatial_roles_match: true,
    };
    let proposal = [1.0, 0.0, 300.0, -200.0];
    let selected = native_candidate_seed(&candidate, Some(proposal)).unwrap();
    let g = PlaneGeometry {
        width: 256,
        height: 224,
    };
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(x as f64, y as f64)))
        .collect();
    let b: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(x as f64 - 3.25, y as f64 + 2.5)))
        .collect();
    // Only the bounded linear part is borrowed; descriptor pixel coordinates
    // anchor translation. The known-wrong global translation never certifies it.
    let seed = anchored_seed(
        Cx::new(selected[0], selected[1]),
        candidate.point_a_quad,
        candidate.point_b_quad,
        g,
    );
    let result = refine(
        PlaneRef::from_geometry(&a, g).unwrap(),
        PlaneRef::from_geometry(&b, g).unwrap(),
        candidate.point_a_quad,
        candidate.point_b_quad,
        seed,
        &MosaicGeometryConfig::default(),
        None,
        None,
        &mut Vec::new(),
    )
    .unwrap();
    assert!((result.0[0] - 131.25).hypot(result.0[1] - 109.5) < 0.15);
    candidate.grid_nomination = true;
    assert!(native_candidate_seed(&candidate, Some(proposal)).is_none());
    candidate.grid_nomination = false;
    assert!(native_candidate_seed(&candidate, Some([0.1, 0.0, 0.0, 0.0])).is_none());
    assert!(native_candidate_seed(&candidate, None).is_none());
}

fn nonlinear_inverse(q: [f64; 2], projective: f64, curvature: f64) -> [f64; 2] {
    let forward = |p: [f64; 2]| {
        let den = 1.0 + projective * p[0] - projective * 0.6 * p[1];
        [
            (1.03 * p[0] + 0.08 * p[1]) / den + curvature * p[0] * p[1],
            (-0.03 * p[0] + 0.96 * p[1]) / den + curvature * (p[0] * p[0] - p[1] * p[1]),
        ]
    };
    let mut p = q;
    for _ in 0..15 {
        let f = forward(p);
        let x = forward([p[0] + 0.01, p[1]]);
        let y = forward([p[0], p[1] + 0.01]);
        let a = (x[0] - f[0]) / 0.01;
        let b = (y[0] - f[0]) / 0.01;
        let c = (x[1] - f[1]) / 0.01;
        let d = (y[1] - f[1]) / 0.01;
        let det = a * d - b * c;
        let e = [f[0] - q[0], f[1] - q[1]];
        p[0] -= (d * e[0] - b * e[1]) / det;
        p[1] -= (-c * e[0] + a * e[1]) / det;
    }
    p
}

#[test]
fn affine_native_projective_and_curved_plants_check_point_placement_not_fit_alone() {
    let g = PlaneGeometry {
        width: 384,
        height: 320,
    };
    let p = [192.0, 160.0];
    let q = [195.25, 157.5];
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(x as f64, y as f64)))
        .collect();
    let a = PlaneRef::from_geometry(&a, g).unwrap();
    let config = MosaicGeometryConfig {
        native_affine: true,
        ..Default::default()
    };
    let seed = anchored_seed(Cx::new(0.995, -0.055), p, [195.6, 157.1], g);
    for (projective, curvature, positive) in [
        (0.00012, 0.0, true),
        (0.0, 0.00008, true),
        (0.0018, 0.0, false),
    ] {
        let b: Vec<_> = (0..g.height)
            .flat_map(|y| {
                (0..g.width).map(move |x| {
                    let u = nonlinear_inverse(
                        [x as f64 - q[0], y as f64 - q[1]],
                        projective,
                        curvature,
                    );
                    texture(u[0] + p[0], u[1] + p[1])
                })
            })
            .collect();
        let actual = refine(
            a,
            PlaneRef::from_geometry(&b, g).unwrap(),
            p,
            q,
            seed,
            &config,
            None,
            None,
            &mut Vec::new(),
        );
        assert_eq!(
            actual.is_ok(),
            positive,
            "projective={projective}, curvature={curvature}: {actual:?}"
        );
        if let Ok(actual) = actual {
            assert!(
                (actual.0[0] - q[0]).hypot(actual.0[1] - q[1]) < 0.2,
                "{actual:?}"
            );
        }
    }
}

#[test]
fn fit_affine_neighbor_nominations_need_direct_pixels_across_smooth_and_discontinuous_surfaces() {
    let g = PlaneGeometry {
        width: 768,
        height: 640,
    };
    let p = [320.0, 320.0];
    let q = [323.25, 317.5];
    let projective = 0.00010;
    let forward = |u: [f64; 2]| {
        let x = u[0] - p[0];
        let y = u[1] - p[1];
        let den = 1.0 + projective * x - projective * 0.6 * y;
        [
            q[0] + (1.03 * x + 0.08 * y) / den,
            q[1] + (-0.03 * x + 0.96 * y) / den,
        ]
    };
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(x as f64, y as f64)))
        .collect();
    let b: Vec<_> = (0..g.height)
        .flat_map(|y| {
            (0..g.width).map(move |x| {
                let u = nonlinear_inverse([x as f64 - q[0], y as f64 - q[1]], projective, 0.0);
                texture(u[0] + p[0], u[1] + p[1])
            })
        })
        .collect();
    let reference = PlaneRef::from_geometry(&a, g).unwrap();
    let moving = PlaneRef::from_geometry(&b, g).unwrap();
    let config = MosaicGeometryConfig {
        native_affine: true,
        ..Default::default()
    };
    let seed = anchored_seed(Cx::new(0.995, -0.055), p, q, g);
    let mut traces = Vec::new();
    refine(
        reference,
        moving,
        p,
        q,
        seed,
        &config,
        None,
        None,
        &mut traces,
    )
    .unwrap();
    let parent = Affine(
        traces
            .iter()
            .rev()
            .find(|t| t.direction == "forward-affine")
            .unwrap()
            .affine_fit
            .unwrap(),
    );
    let linear = Cx::new(
        (parent.0[0] + parent.0[3]) * 0.5,
        (parent.0[2] - parent.0[1]) * 0.5,
    );
    for offset in [[128.0, 0.0], [0.0, 128.0]] {
        let at = [p[0] + offset[0], p[1] + offset[1]];
        let prediction = parent.apply(at);
        let nominated = anchored_seed(linear, at, prediction, g);
        let actual = refine(
            reference,
            moving,
            at,
            prediction,
            nominated,
            &config,
            None,
            None,
            &mut Vec::new(),
        )
        .unwrap();
        let truth = forward(at);
        assert!(
            (actual.0[0] - truth[0]).hypot(actual.0[1] - truth[1]) < 0.2,
            "{actual:?}, truth {truth:?}"
        );
    }
    let at = [p[0] + 128.0, p[1]];
    let prediction = parent.apply(at);
    let truth = forward(at);
    for discontinuity in [false, true] {
        let mut bad = b.clone();
        let mut state = 29741_u64;
        for y in (truth[1] as usize - 62)..=(truth[1] as usize + 62) {
            for x in (truth[0] as usize - 62)..=(truth[0] as usize + 62) {
                bad[y * g.width + x] = if discontinuity {
                    let u = nonlinear_inverse(
                        [x as f64 - q[0] - 28.0, y as f64 - q[1]],
                        projective,
                        0.0,
                    );
                    texture(u[0] + p[0], u[1] + p[1])
                } else {
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                    500.0 + ((state >> 32) & 65535) as f32 / 128.0
                };
            }
        }
        let bad = PlaneRef::from_geometry(&bad, g).unwrap();
        assert!(
            refine(
                reference,
                bad,
                p,
                q,
                seed,
                &config,
                None,
                None,
                &mut Vec::new()
            )
            .is_ok(),
            "parent must remain real evidence"
        );
        assert!(
            refine(
                reference,
                bad,
                at,
                prediction,
                anchored_seed(linear, at, prediction, g),
                &config,
                None,
                None,
                &mut Vec::new()
            )
            .is_err(),
            "neighbor cannot inherit parent acceptance across depth jump or unrelated surface: {discontinuity}"
        );
    }
}

#[test]
fn affine_native_expanded_source_search_refuses_flat_noise_and_alias() {
    let g = PlaneGeometry {
        width: 256,
        height: 224,
    };
    let p = [128.0, 112.0];
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(x as f64, y as f64)))
        .collect();
    let a = PlaneRef::from_geometry(&a, g).unwrap();
    let config = MosaicGeometryConfig {
        native_affine: true,
        native_affine_robust: true,
        ..Default::default()
    };
    let mut state = 1749_u64;
    for kind in [0, 1, 1, 1, 1, 2] {
        let b: Vec<_> = (0..g.pixels())
            .map(|i| match kind {
                0 => 1000.0,
                1 => {
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                    500.0 + ((state >> 32) & 65535) as f32 / 128.0
                }
                _ => {
                    if (i % g.width + i / g.width).is_multiple_of(2) {
                        700.0
                    } else {
                        1300.0
                    }
                }
            })
            .collect();
        assert!(
            refine(
                a,
                PlaneRef::from_geometry(&b, g).unwrap(),
                p,
                p,
                Similarity::IDENTITY,
                &config,
                None,
                None,
                &mut Vec::new()
            )
            .is_err(),
            "unrelated original kind {kind}"
        );
    }
    let wrong = anchored_seed(Cx::ONE, p, [p[0] + 25.0, p[1] - 20.0], g);
    assert!(refine(a, a, p, p, wrong, &config, None, None, &mut Vec::new()).is_err());
    assert!(!Affine([1.0, 0.0, 0.0, -1.0, 0.0, 0.0]).valid());
}

#[test]
fn robust_affine_keeps_center_surface_and_reports_occluded_corner_measurement() {
    let g = PlaneGeometry {
        width: 256,
        height: 224,
    };
    let p = [128.0, 112.0];
    let shift = [2.5, -1.75];
    let q = [p[0] + shift[0], p[1] + shift[1]];
    let scene = |x: f64, y: f64, background_shift: [f64; 2]| {
        let base = texture(x, y);
        if x < p[0] - 16.0 && y < p[1] - 16.0 {
            base + 10.0 * (texture(x - background_shift[0], y - background_shift[1]) - 1000.0)
        } else {
            base
        }
    };
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| scene(x as f64, y as f64, [0.0, 0.0])))
        .collect();
    let b: Vec<_> = (0..g.height)
        .flat_map(|y| {
            (0..g.width).map(move |x| scene(x as f64 - shift[0], y as f64 - shift[1], [5.0, -3.0]))
        })
        .collect();
    let reference = PlaneRef::from_geometry(&a, g).unwrap();
    let moving = PlaneRef::from_geometry(&b, g).unwrap();
    let seed = anchored_seed(Cx::ONE, p, q, g);
    let config = MosaicGeometryConfig {
        native_affine: true,
        native_affine_robust: true,
        ..Default::default()
    };
    let mut trace = Vec::new();
    let actual = refine(
        reference, moving, p, q, seed, &config, None, None, &mut trace,
    )
    .unwrap();
    assert!(
        (actual.0[0] - q[0]).hypot(actual.0[1] - q[1]) < 0.2,
        "{actual:?}"
    );
    assert!(
        trace.iter().any(|t| t.kept.iter().any(|&v| !v)),
        "plant must actually reject a measured corner"
    );
    assert!(
        trace
            .iter()
            .filter(|t| t.termination == "final affine image measurement")
            .all(|t| t.center_leave_one_out_error_quad.is_some_and(|e| e <= 0.5))
    );
    let strict = MosaicGeometryConfig {
        native_affine_robust: false,
        ..config
    };
    assert!(
        refine(
            reference,
            moving,
            p,
            q,
            seed,
            &strict,
            None,
            None,
            &mut Vec::new()
        )
        .is_err(),
        "all-tile foil must expose the physical corner discontinuity"
    );
    let mut observations = Vec::new();
    for y in [-16.0, 0.0, 16.0] {
        for x in [-16.0, 0.0, 16.0] {
            observations.push(Observation {
                p: [x, y],
                q: [x + 3.0, y - 2.0],
                peak: 1.0,
                center: x == 0.0 && y == 0.0,
            });
        }
    }
    observations[4].q[0] += 3.0;
    assert!(
        coherent_fit(&observations, 0.5).is_none(),
        "eight coherent background tiles cannot silently discard the center surface"
    );
}

#[test]
fn affine_actual_footprint_respects_clipped_taps_and_spatial_holdout_roles() {
    struct Original {
        g: PlaneGeometry,
        pixels: Vec<u16>,
    }
    impl QuadSource for Original {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let a = 4 * self.g.width * y;
            let b = a + 2 * self.g.width;
            (&self.pixels[a..b], &self.pixels[b..b + 2 * self.g.width])
        }
    }
    let g = PlaneGeometry {
        width: 384,
        height: 320,
    };
    let p = [192.0, 192.0];
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(x as f64, y as f64)))
        .collect();
    let a = PlaneRef::from_geometry(&a, g).unwrap();
    let config = MosaicGeometryConfig {
        native_affine: true,
        ..Default::default()
    };
    let clean = Original {
        g,
        pixels: vec![1000; 4 * g.pixels()],
    };
    let mut clipped = Original {
        g,
        pixels: vec![1000; 4 * g.pixels()],
    };
    clipped.pixels[2 * 192 * 2 * g.width + 2 * 232 + 1] = 16000;
    let originals = [
        support::PixelWitness {
            source: &clean,
            white: 16000.0,
            filter_halo: 0,
        },
        support::PixelWitness {
            source: &clipped,
            white: 16000.0,
            filter_halo: 0,
        },
    ];
    let mut trace = Vec::new();
    assert!(
        refine(
            a,
            a,
            p,
            p,
            Similarity::IDENTITY,
            &config,
            None,
            Some(&originals),
            &mut trace
        )
        .is_err()
    );
    assert!(trace.iter().any(|t| !t.support_unclipped));
    let guide = super::super::super::matching::tests::guide(0, 714, [0, 0], false);
    let fit = support::RoleWitness::new(&guide, Similarity::IDENTITY, false, &config).unwrap();
    let heldout = support::RoleWitness::new(&guide, Similarity::IDENTITY, true, &config).unwrap();
    assert!(
        refine(
            a,
            a,
            p,
            p,
            Similarity::IDENTITY,
            &config,
            Some(&[fit, fit]),
            None,
            &mut Vec::new()
        )
        .is_ok()
    );
    assert!(
        refine(
            a,
            a,
            p,
            p,
            Similarity::IDENTITY,
            &config,
            Some(&[fit, heldout]),
            None,
            &mut Vec::new()
        )
        .is_err()
    );
}
