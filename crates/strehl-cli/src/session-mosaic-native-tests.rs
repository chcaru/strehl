use super::*;

fn refused_dependency_fixture(point: [f64; 2], grid_nomination: bool) -> NativeCorrespondence {
    NativeCorrespondence::refused(
        CoarseCorrespondence {
            id: "attempt-support-control".into(),
            pass_a: 0,
            pass_b: 1,
            point_a_quad: point,
            point_b_quad: point,
            source_a: 0,
            source_b: 1,
            focus_a: None,
            focus_b: None,
            role: super::super::MatchRole::Fit,
            spatial_blocks: [[0, 0]; 2],
            descriptor_distance: 0.,
            seed_residual_quad: 0.,
            within_seed_support: true,
            grid_nomination,
            spatial_roles_match: true,
        },
        "controlled preflight/trace failure",
    )
}

#[test]
fn dependency_audit_proves_no_query_or_refuses_unknown_trace_without_string_matching() {
    let g = PlaneGeometry {
        width: 384,
        height: 320,
    };
    let config = MosaicGeometryConfig::default();
    let poses = [Similarity::IDENTITY; 2];
    for coarse in [false, true] {
        let mut edge = refused_dependency_fixture([2., 2.], coarse);
        assert_eq!(
            native_attempted_support(&edge, poses, g, &config).unwrap(),
            None
        );
        edge.accepted = true;
        assert!(native_attempted_support(&edge, poses, g, &config).is_err());
        let interior = refused_dependency_fixture([192., 160.], coarse);
        assert!(
            native_attempted_support(&interior, poses, g, &config).is_err(),
            "missing trace after a geometrically possible query is unknown, not empty support"
        );
    }
}

#[test]
fn frozen_island_plan_allocation_is_included_before_native_work() {
    let (_, config) = super::super::matching::tests::island_fixture();
    let mut initial = config.clone();
    initial.role_plan = None;
    let g = PlaneGeometry {
        width: 128,
        height: 128,
    };
    let base = native_candidate_reservation(g, 1, &initial, usize::MAX).unwrap();
    let extra = config.role_work_bytes().unwrap();
    assert!(extra > 65536);
    assert_eq!(
        native_candidate_reservation(g, 1, &config, usize::MAX).unwrap(),
        base + extra
    );
    assert!(native_candidate_reservation(g, 1, &config, base + extra - 1).is_err());
}

#[test]
fn stage_two_native_fit_uses_old_held_region_without_consuming_frozen_island() {
    struct Original {
        g: PlaneGeometry,
        pixels: Vec<u16>,
    }
    impl QuadSource for Original {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let start = 4 * self.g.width * y;
            let middle = start + 2 * self.g.width;
            (
                &self.pixels[start..middle],
                &self.pixels[middle..middle + 2 * self.g.width],
            )
        }
    }
    let (guides, config) = super::super::matching::tests::island_fixture();
    let g = guides[0].source_geometry;
    let mut original = Original {
        g,
        pixels: vec![0; 4 * g.pixels()],
    };
    for y in 0..g.height {
        for x in 0..g.width {
            let value = texture(g, x as f64, y as f64).round() as u16;
            original.pixels[4 * g.width * y + 2 * x + 1] = value;
            original.pixels[4 * g.width * y + 2 * g.width + 2 * x] = value;
        }
    }
    let mut green = vec![0.; g.pixels()];
    green_luma(&original, 0., &mut green);
    let measure = |moving: &Original,
                   values: &[f32],
                   cfg: &MosaicGeometryConfig,
                   center: [f64; 2],
                   island: Option<usize>| {
        let heldout = island.is_some();
        let roles = [
            support::RoleWitness::new(&guides[0], Similarity::IDENTITY, heldout, cfg)
                .unwrap()
                .for_island(island),
            support::RoleWitness::new(&guides[1], Similarity::IDENTITY, heldout, cfg)
                .unwrap()
                .for_island(island),
        ];
        let originals = [
            support::PixelWitness {
                source: &original,
                white: 16000.,
                filter_halo: 0,
            },
            support::PixelWitness {
                source: moving,
                white: 16000.,
                filter_halo: 0,
            },
        ];
        let mut masked_reference = vec![0.; g.pixels()];
        let mut masked_moving = vec![0.; g.pixels()];
        support::green_luma_reserved(&original, 0., roles[0], &mut masked_reference);
        support::green_luma_reserved(moving, 0., roles[1], &mut masked_moving);
        let mut trace = Vec::new();
        let result = refine_on_planes_observed(
            PlaneRef::from_geometry(&masked_reference, g).unwrap(),
            PlaneRef::from_geometry(&masked_moving, g).unwrap(),
            center,
            center,
            Similarity::IDENTITY,
            cfg,
            Some(&roles),
            Some(&originals),
            &mut trace,
        );
        // Masking must not alter any arithmetic for a fully supported query.
        if let Ok(measured) = &result {
            let mut unmasked_trace = Vec::new();
            let unmasked = refine_on_planes_observed(
                PlaneRef::from_geometry(&green, g).unwrap(),
                PlaneRef::from_geometry(values, g).unwrap(),
                center,
                center,
                Similarity::IDENTITY,
                cfg,
                Some(&roles),
                Some(&originals),
                &mut unmasked_trace,
            )
            .unwrap();
            assert_eq!(measured.0, unmasked.0);
            assert_eq!(
                serde_json::to_value(&trace).unwrap(),
                serde_json::to_value(&unmasked_trace).unwrap()
            );
        }
        (result.map(|v| v.0), trace)
    };
    let mut stage_one = config.clone();
    stage_one.role_plan = None;
    assert!(
        measure(&original, &green, &stage_one, [256., 256.], None)
            .0
            .is_err(),
        "initial FIT cannot consume the old held block"
    );
    let before = measure(&original, &green, &config, [256., 256.], None);
    assert!(
        before.0.is_ok(),
        "stage-two local FIT should be measurable: {:?}",
        before.0
    );
    assert!(
        measure(&original, &green, &config, [144., 144.], Some(0))
            .0
            .is_ok()
    );
    let mut poisoned = Original {
        g,
        pixels: original.pixels.clone(),
    };
    for y in 102..187 {
        for x in 102..187 {
            poisoned.pixels[4 * g.width * y + 2 * x + 1] = 16000;
            poisoned.pixels[4 * g.width * y + 2 * g.width + 2 * x] = 16000;
        }
    }
    let mut poisoned_green = vec![0.; g.pixels()];
    green_luma(&poisoned, 0., &mut poisoned_green);
    let after = measure(&poisoned, &poisoned_green, &config, [256., 256.], None);
    assert_eq!(before.0.unwrap(), after.0.unwrap());
    assert_eq!(
        serde_json::to_value(&before.1).unwrap(),
        serde_json::to_value(&after.1).unwrap()
    );
    assert!(
        after
            .1
            .iter()
            .all(|m| m.support_reserved && m.support_unclipped)
    );
    assert!(
        measure(&poisoned, &poisoned_green, &config, [144., 144.], Some(0))
            .0
            .is_err(),
        "poisoned held evidence must not pass its original-pixel gates"
    );
    assert!(
        measure(&original, &green, &config, [144., 144.], Some(1))
            .0
            .is_err(),
        "one island's photons cannot certify another planned site"
    );
    // A real attempted NCC query near the frozen boundary is refused, but its
    // complete diagnostic scores must also be independent of held pixels.
    for center in [[202., 144.], [144., 202.]] {
        let before = measure(&original, &green, &config, center, None);
        let after = measure(&poisoned, &poisoned_green, &config, center, None);
        assert!(before.0.is_err() && after.0.is_err());
        assert!(
            !before.1.is_empty(),
            "the poison control must reach an actual query"
        );
        assert!(before.1.iter().any(|m| !m.support_reserved));
        assert_eq!(
            before.0.unwrap_err().to_string(),
            after.0.unwrap_err().to_string()
        );
        assert_eq!(
            serde_json::to_value(&before.1).unwrap(),
            serde_json::to_value(&after.1).unwrap()
        );
    }
    let role = support::RoleWitness::new(&guides[1], Similarity::IDENTITY, false, &config).unwrap();
    let parallel = |threads| {
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build()
            .unwrap()
            .install(|| {
                let mut output = vec![0.; g.pixels()];
                support::green_luma_reserved(&poisoned, 0., role, &mut output);
                output
            })
    };
    assert_eq!(parallel(1), parallel(4));
}

#[test]
fn filtered_rotated_native_escape_never_observes_reserved_original_values() {
    struct Original {
        g: PlaneGeometry,
        pixels: Vec<u16>,
    }
    impl QuadSource for Original {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let start = 4 * self.g.width * y;
            let mid = start + 2 * self.g.width;
            (
                &self.pixels[start..mid],
                &self.pixels[mid..mid + 2 * self.g.width],
            )
        }
    }
    let (guides, mut config) = super::super::matching::tests::island_fixture();
    config.native_lowpass = true;
    let g = guides[0].source_geometry;
    let pose = Similarity {
        a: Cx::new(1.035, 0.037),
        b: Cx::new(17., -9.),
    };
    let inverse = pose.invert().unwrap();
    let mut clean = Original {
        g,
        pixels: vec![0; 4 * g.pixels()],
    };
    let mut poison = Original {
        g,
        pixels: vec![0; 4 * g.pixels()],
    };
    let mut altered = 0;
    for y in 0..g.height {
        for x in 0..g.width {
            let value = texture(g, x as f64, y as f64).round() as u16;
            let anchor = point(inverse, [x as f64, y as f64], g);
            let island = config.role_plan.as_ref().unwrap().plan.classify(
                1,
                super::super::roles::Rectangle::around(
                    anchor,
                    0.5 * (inverse.a.re.abs() + inverse.a.im.abs()),
                )
                .unwrap(),
            );
            let reserved = matches!(island, Some(super::super::roles::SpatialRole::Heldout(_)));
            altered += usize::from(reserved);
            for at in [
                4 * g.width * y + 2 * x + 1,
                4 * g.width * y + 2 * g.width + 2 * x,
            ] {
                clean.pixels[at] = value;
                poison.pixels[at] = if reserved { 16000 } else { value };
            }
        }
    }
    assert!(altered > 1000);
    let roles =
        [0, 1].map(|pass| support::RoleWitness::new(&guides[pass], pose, false, &config).unwrap());
    let mut reference = vec![0.; g.pixels()];
    support::green_luma_reserved(&clean, 0., roles[0], &mut reference);
    native_filter::apply(&mut reference, g);
    let center = point(pose, [202., 144.], g);
    let measure = |source: &Original| {
        let mut moving = vec![0.; g.pixels()];
        support::green_luma_reserved(source, 0., roles[1], &mut moving);
        native_filter::apply(&mut moving, g);
        let originals = [
            support::PixelWitness {
                source: &clean,
                white: 16000.,
                filter_halo: native_filter::HALO,
            },
            support::PixelWitness {
                source,
                white: 16000.,
                filter_halo: native_filter::HALO,
            },
        ];
        let mut trace = Vec::new();
        let result = refine_on_planes_observed(
            PlaneRef::from_geometry(&reference, g).unwrap(),
            PlaneRef::from_geometry(&moving, g).unwrap(),
            center,
            center,
            Similarity::IDENTITY,
            &config,
            Some(&roles),
            Some(&originals),
            &mut trace,
        );
        (moving, result, trace)
    };
    let before = measure(&clean);
    let after = measure(&poison);
    assert!(
        before
            .0
            .iter()
            .zip(&after.0)
            .all(|(a, b)| a.to_bits() == b.to_bits()),
        "all filtered values and invalid-border NaN bits must remain exact"
    );
    assert!(before.1.is_err() && after.1.is_err());
    assert!(!before.2.is_empty());
    assert!(before.2.iter().any(|m| !m.support_reserved));
    assert_eq!(
        before.1.unwrap_err().to_string(),
        after.1.unwrap_err().to_string()
    );
    assert_eq!(
        serde_json::to_value(before.2).unwrap(),
        serde_json::to_value(after.2).unwrap()
    );
}

#[test]
fn declared_seed_uncertainty_must_reserve_reverse_query_in_both_views() {
    use super::super::roles::RolePlan;
    struct Original {
        g: PlaneGeometry,
        pixels: Vec<u16>,
    }
    impl QuadSource for Original {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let start = 4 * self.g.width * y;
            let mid = start + 2 * self.g.width;
            (
                &self.pixels[start..mid],
                &self.pixels[mid..mid + 2 * self.g.width],
            )
        }
    }
    let (guides, base) = super::super::matching::tests::island_fixture();
    let g = guides[0].source_geometry;
    let mut original = Original {
        g,
        pixels: vec![0; 4 * g.pixels()],
    };
    for y in 0..g.height {
        for x in 0..g.width {
            let value = texture(g, x as f64, y as f64).round() as u16;
            original.pixels[4 * g.width * y + 2 * x + 1] = value;
            original.pixels[4 * g.width * y + 2 * g.width + 2 * x] = value;
        }
    }
    let measure = |symmetric: bool| {
        let old = &base.role_plan.as_ref().unwrap().plan;
        let mut proposals: Vec<_> = old.islands.iter().map(|i| i.proposal.clone()).collect();
        if symmetric {
            for p in &mut proposals {
                p.query_radius_quad[0] += 24.;
            }
        }
        let frozen = RolePlan::build(
            old.upstream_binding_sha256.clone(),
            old.initial_fit_evidence_sha256.clone(),
            old.grids.clone(),
            [1., 0., 6., 0.],
            24.,
            old.ancestor_footprints.clone(),
            proposals,
        )
        .unwrap()
        .freeze()
        .unwrap();
        assert_eq!(frozen.plan.islands.len(), 3);
        let center_a = frozen.plan.islands[0].proposal.reference_center_quad;
        let center_b = frozen.plan.islands[0].nominated_moving_center_quad;
        let config = MosaicGeometryConfig {
            role_plan: Some(Box::new(frozen)),
            ..base.clone()
        };
        let roles = [0, 1].map(|pass| {
            support::RoleWitness::new(&guides[pass], Similarity::IDENTITY, true, &config)
                .unwrap()
                .for_island(Some(0))
        });
        let mut a = vec![0.; g.pixels()];
        let mut b = vec![0.; g.pixels()];
        support::green_luma_reserved(&original, 0., roles[0], &mut a);
        support::green_luma_reserved(&original, 0., roles[1], &mut b);
        let seed = Similarity {
            a: Cx::new(1., 0.),
            b: Cx::new(6., 0.),
        };
        let mut trace = Vec::new();
        let result = refine_on_planes_observed(
            PlaneRef::from_geometry(&a, g).unwrap(),
            PlaneRef::from_geometry(&b, g).unwrap(),
            center_a,
            center_b,
            seed,
            &config,
            Some(&roles),
            None,
            &mut trace,
        );
        (result, trace)
    };
    let prior = measure(false);
    assert!(prior.0.is_err());
    assert!(
        prior
            .1
            .iter()
            .any(|m| m.direction == "reverse" && !m.support_reserved)
    );
    let corrected = measure(true);
    let fit = corrected
        .0
        .expect("both declared uncertainty envelopes must support the actual reciprocal query");
    assert!(fit.1 < 0.5 && fit.2 < 0.5 && fit.3 < 0.5);
    assert!(corrected.1.iter().all(|m| m.support_reserved));
    // Exercise the complete declared square uncertainty at nonunit scale and
    // rotation. The exact planted seed isolates footprint commissioning from
    // the separate question of recovering a large initial displacement.
    let a = Cx::new(1.035, 0.037);
    let center = Cx::new(g.width as f64 * 0.5, g.height as f64 * 0.5);
    let pivot = Cx::new(144., 144.);
    let nominal = Similarity {
        a,
        b: pivot - center - a * (pivot - center),
    };
    let inverse = nominal.invert().unwrap();
    let forward_extent = a.re.abs() + a.im.abs();
    let reverse_extent = inverse.a.re.abs() + inverse.a.im.abs();
    let placements = [Cx::new(1.1, 0.02), Cx::new(0.9, -0.025)].map(|a| Similarity {
        a,
        b: pivot - center - a * (pivot - center),
    });
    let inverse_placements = placements.map(|p| p.invert().unwrap());
    let source_windows = inverse_placements.map(|p| 43. * (p.a.re.abs() + p.a.im.abs()));
    let mut reference = Original {
        g,
        pixels: vec![0; 4 * g.pixels()],
    };
    for y in 0..g.height {
        for x in 0..g.width {
            let p = point(inverse_placements[0], [x as f64, y as f64], g);
            let value = texture(g, p[0], p[1]).round() as u16;
            reference.pixels[4 * g.width * y + 2 * x + 1] = value;
            reference.pixels[4 * g.width * y + 2 * g.width + 2 * x] = value;
        }
    }
    for displacement in [[-24., -24.], [-24., 24.], [24., -24.], [24., 24.]] {
        let truth = Similarity {
            a,
            b: nominal.b + Cx::new(displacement[0], displacement[1]),
        };
        let inverse_truth = truth.invert().unwrap();
        let mut moving = Original {
            g,
            pixels: vec![0; 4 * g.pixels()],
        };
        for y in 0..g.height {
            for x in 0..g.width {
                let p = point(
                    inverse_truth,
                    point(inverse_placements[1], [x as f64, y as f64], g),
                    g,
                );
                let value = texture(g, p[0], p[1]).round() as u16;
                moving.pixels[4 * g.width * y + 2 * x + 1] = value;
                moving.pixels[4 * g.width * y + 2 * g.width + 2 * x] = value;
            }
        }
        let old = &base.role_plan.as_ref().unwrap().plan;
        let mut proposals: Vec<_> = old.islands.iter().map(|i| i.proposal.clone()).collect();
        for proposal in &mut proposals {
            proposal.query_radius_quad = [
                source_windows[0].max(source_windows[1] * reverse_extent) + 24. * reverse_extent,
                source_windows[1].max(source_windows[0] * forward_extent),
            ];
        }
        let frozen = RolePlan::build(
            old.upstream_binding_sha256.clone(),
            old.initial_fit_evidence_sha256.clone(),
            old.grids.clone(),
            [a.re, a.im, nominal.b.re, nominal.b.im],
            24.,
            old.ancestor_footprints.clone(),
            proposals,
        )
        .unwrap()
        .freeze()
        .unwrap();
        let pa = frozen.plan.islands[0].proposal.reference_center_quad;
        let pb = frozen.plan.islands[0].nominated_moving_center_quad;
        let bounds = frozen.plan.islands[0].reservations;
        let config = MosaicGeometryConfig {
            role_plan: Some(Box::new(frozen)),
            ..base.clone()
        };
        let roles = [0, 1].map(|pass| {
            support::RoleWitness::new(&guides[pass], placements[pass], true, &config)
                .unwrap()
                .for_island(Some(0))
        });
        let mut values_a = vec![0.; g.pixels()];
        let mut values_b = vec![0.; g.pixels()];
        support::green_luma_reserved(&reference, 0., roles[0], &mut values_a);
        support::green_luma_reserved(&moving, 0., roles[1], &mut values_b);
        let mut trace = Vec::new();
        let fit = refine_on_planes_observed(
            PlaneRef::from_geometry(&values_a, g).unwrap(),
            PlaneRef::from_geometry(&values_b, g).unwrap(),
            point(placements[0], pa, g),
            point(placements[1], pb, g),
            inverse_placements[0].then(truth).then(placements[1]),
            &config,
            Some(&roles),
            None,
            &mut trace,
        )
        .expect("both extreme uncertainty corners must retain actual reciprocal support");
        assert!(fit.1 < 0.5 && fit.2 < 0.5 && fit.3 < 0.5);
        assert!(trace.iter().all(|m| m.support_reserved));
        assert!(
            trace.iter().any(|m| m.direction == "forward")
                && trace.iter().any(|m| m.direction == "reverse")
        );
        for pass in 0..2 {
            assert!(
                !roles[pass].rectangle(
                    &[point(
                        placements[pass],
                        [bounds[pass].high[0] + 1., pa[1]],
                        g
                    )],
                    0.,
                    1
                ),
                "a native tap one quad beyond the frozen reservation must refuse"
            );
        }
    }
}

#[test]
fn unconsumed_precheck_ring_across_role_boundary_cannot_change_native_admission() {
    struct Original {
        g: PlaneGeometry,
        pixels: Vec<u16>,
    }
    impl QuadSource for Original {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let start = 4 * self.g.width * y;
            let middle = start + 2 * self.g.width;
            (
                &self.pixels[start..middle],
                &self.pixels[middle..middle + 2 * self.g.width],
            )
        }
    }
    let g = PlaneGeometry {
        width: 384,
        height: 256,
    };
    let values: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(g, x as f64, y as f64)))
        .collect();
    let plane = PlaneRef::from_geometry(&values, g).unwrap();
    let guide = super::super::matching::tests::guide(0, 714, [0, 0], false);
    let config = MosaicGeometryConfig::default();
    let roles =
        [support::RoleWitness::new(&guide, Similarity::IDENTITY, false, &config).unwrap(); 2];
    let center = [170.0, 64.0];
    let mut original = Original {
        g,
        pixels: vec![1000; 4 * g.pixels()],
    };
    let measure = |source: &Original| {
        let originals = [support::PixelWitness {
            source,
            white: 16000.0,
            filter_halo: 0,
        }; 2];
        let mut trace = Vec::new();
        let result = refine_on_planes_observed(
            plane,
            plane,
            center,
            center,
            Similarity::IDENTITY,
            &config,
            Some(&roles),
            Some(&originals),
            &mut trace,
        )
        .unwrap();
        (result.0, trace)
    };
    let before = measure(&original);
    // This pixel is inside the former radius43 square but is in heldout block0.
    // Every actual forward/reverse search stays in FIT block1 instead.
    original.pixels[4 * g.width * 64 + 2 * 127 + 1] = 16000;
    assert!(!unclipped_patch(&original, 16000.0, center, 43));
    let after = measure(&original);
    assert_eq!(before.0, after.0);
    assert_eq!(
        serde_json::to_value(&before.1).unwrap(),
        serde_json::to_value(&after.1).unwrap()
    );
    assert!(
        after
            .1
            .iter()
            .all(|m| m.support_reserved && m.support_unclipped)
    );
}

#[test]
fn affine_receipt_reservation_refuses_similarity_only_budget_and_overflow() {
    let g = PlaneGeometry {
        width: 512,
        height: 384,
    };
    let mut config = MosaicGeometryConfig::default();
    let similarity = native_reservation(g, 2, &config, usize::MAX).unwrap();
    config.native_affine = true;
    let affine = native_reservation(g, 2, &config, usize::MAX).unwrap();
    assert!(affine > similarity);
    assert_eq!(
        affine - similarity,
        2 * (config.maximum_features + grid::MAX_CANDIDATES) * 49152
    );
    assert!(native_reservation(g, 2, &config, similarity).is_err());
    assert!(native_reservation(g, 2, &config, affine - 1).is_err());
    assert_eq!(native_reservation(g, 2, &config, affine).unwrap(), affine);
    assert!(native_reservation(g, usize::MAX, &config, usize::MAX).is_err());
    config.maximum_features = usize::MAX;
    assert!(native_reservation(g, 1, &config, usize::MAX).is_err());
}
fn texture(g: PlaneGeometry, x: f64, y: f64) -> f32 {
    let xx = x / g.width as f64;
    let yy = y / g.height as f64;
    (800.0
        + 70.0 * (x * 0.21 + (y * 0.04).sin()).sin()
        + 60.0 * (y * 0.17 + (x * 0.03).cos()).cos()
        + 45.0 * (x * 0.073 + y * 0.098 + 3.0 * xx * yy).sin()
        + 20.0 * (x * 0.31 - y * 0.27).cos()) as f32
}
#[test]
fn native_mosaic_pair_consumer_recovers_shift_and_refuses_flat() {
    let g = PlaneGeometry {
        width: 256,
        height: 224,
    };
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(g, x as f64, y as f64)))
        .collect();
    let b: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(g, x as f64 - 3.25, y as f64 + 2.5)))
        .collect();
    let p = [128.0, 112.0];
    let q = [131.25, 109.5];
    let seed = anchored_seed(Cx::ONE, p, [132.0, 109.0], g);
    let cfg = MosaicGeometryConfig::default();
    let pa = PlaneRef::from_geometry(&a, g).unwrap();
    let pb = PlaneRef::from_geometry(&b, g).unwrap();
    let (fit, _, _, reciprocal, _, _, _) =
        refine_on_planes(pa, pb, p, q, seed, &cfg, None).unwrap();
    let recovered = point(fit, p, g);
    assert!(
        (recovered[0] - q[0]).hypot(recovered[1] - q[1]) < 0.12,
        "{recovered:?}"
    );
    assert!(reciprocal < 0.12);
    let flat = vec![500.0; g.pixels()];
    assert!(
        refine_on_planes(
            pa,
            PlaneRef::from_geometry(&flat, g).unwrap(),
            p,
            q,
            seed,
            &cfg,
            None
        )
        .is_err()
    );
}

#[test]
fn nominated_focus_support_does_not_certify_flat_directional_or_periodic_pairs() {
    let g = PlaneGeometry {
        width: 256,
        height: 224,
    };
    let p = [128., 112.];
    let cfg = MosaicGeometryConfig::default();
    for kind in 0..3 {
        let values: Vec<_> = (0..g.pixels())
            .map(|i| {
                let x = (i % g.width) as f64;
                let y = (i / g.width) as f64;
                match kind {
                    0 => 500.,
                    1 => 500. + 200. * ((x - 128.) / 8.).tanh() as f32,
                    _ => {
                        500. + 100.
                            * ((x * std::f64::consts::TAU / 8.).sin()
                                + (y * std::f64::consts::TAU / 8.).cos())
                                as f32
                    }
                }
            })
            .collect();
        let plane = PlaneRef::from_geometry(&values, g).unwrap();
        let result = refine_on_planes(plane, plane, p, p, Similarity::IDENTITY, &cfg, None);
        assert!(
            result.is_err(),
            "upstream focus/coverage nomination must not certify unidentifiable2D geometry: kind{kind}, {result:?}"
        );
    }
}

#[test]
fn native_lowpass_alias_control_preserves_placement_and_refuses_flat_noise_alias() {
    let g = PlaneGeometry {
        width: 256,
        height: 224,
    };
    let shift = [3.25, -2.5];
    let scene = |x: f64, y: f64| {
        texture(g, x, y) + 100.0 * ((4.4 * x + 1.1 * y).sin() + (2.5 * x - 4.7 * y).cos()) as f32
    };
    let mut a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| scene(x as f64, y as f64)))
        .collect();
    let mut b: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| scene(x as f64 - shift[0], y as f64 - shift[1])))
        .collect();
    native_filter::apply(&mut a, g);
    native_filter::apply(&mut b, g);
    let p = [128.0, 112.0];
    let q = [p[0] + shift[0], p[1] + shift[1]];
    let seed = anchored_seed(Cx::ONE, p, [132.0, 109.0], g);
    let cfg = MosaicGeometryConfig {
        native_lowpass: true,
        ..Default::default()
    };
    let reference = PlaneRef::from_geometry(&a, g).unwrap();
    let positive = refine_on_planes(
        reference,
        PlaneRef::from_geometry(&b, g).unwrap(),
        p,
        q,
        seed,
        &cfg,
        None,
    )
    .expect("native bandlimited scene must retain useful placement");
    let recovered = point(positive.0, p, g);
    assert!(
        (recovered[0] - q[0]).hypot(recovered[1] - q[1]) < 0.2,
        "{recovered:?}"
    );
    assert!(positive.3 < 0.2);
    let mut state = 0x791d_u64;
    // Expanded focus search may nominate four independent originals. None
    // of four unrelated noise sources may manufacture an accepted site.
    for kind in [0, 1, 1, 1, 1, 2] {
        let mut invalid: Vec<_> = (0..g.pixels())
            .map(|i| match kind {
                0 => 500.0,
                1 => {
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                    500.0 + ((state >> 32) & 65535) as f32 / 128.0
                }
                _ => {
                    if (i / g.width + i % g.width).is_multiple_of(2) {
                        300.0
                    } else {
                        700.0
                    }
                }
            })
            .collect();
        native_filter::apply(&mut invalid, g);
        assert!(
            refine_on_planes(
                reference,
                PlaneRef::from_geometry(&invalid, g).unwrap(),
                p,
                q,
                seed,
                &cfg,
                None
            )
            .is_err(),
            "flat, unrelated noise, and pure Nyquist alias cannot certify a match: {kind}"
        );
    }
}

#[test]
fn proposed_grid_seed_needs_actual_coarse_and_native_evidence_and_refuses_wrong_or_noise_source() {
    let g = PlaneGeometry {
        width: 768,
        height: 640,
    };
    let mut state = 74631_u64;
    let mut a = vec![0.0_f32; g.pixels()];
    let mut unrelated = vec![0.0_f32; g.pixels()];
    for values in [&mut a, &mut unrelated] {
        for value in values {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            *value = 500.0 + ((state >> 32) & 65535) as f32 / 16.0;
        }
    }
    for _ in 0..2 {
        let old = a.clone();
        for y in 1..g.height - 1 {
            for x in 1..g.width - 1 {
                a[y * g.width + x] = (-1_isize..=1)
                    .flat_map(|dy| (-1_isize..=1).map(move |dx| (dx, dy)))
                    .map(|(dx, dy)| {
                        old[(y as isize + dy) as usize * g.width + (x as isize + dx) as usize]
                    })
                    .sum::<f32>()
                    / 9.0;
            }
        }
    }
    let shift = [3.25_f64, -2.5_f64];
    let mut b = vec![0.0; g.pixels()];
    for y in 4..g.height - 4 {
        for x in 4..g.width - 4 {
            let sx = x as f64 - shift[0];
            let sy = y as f64 - shift[1];
            let ix = sx.floor() as usize;
            let iy = sy.floor() as usize;
            let fx = (sx - ix as f64) as f32;
            let fy = (sy - iy as f64) as f32;
            b[y * g.width + x] = (a[iy * g.width + ix] * (1.0 - fx)
                + a[iy * g.width + ix + 1] * fx)
                * (1.0 - fy)
                + (a[(iy + 1) * g.width + ix] * (1.0 - fx) + a[(iy + 1) * g.width + ix + 1] * fx)
                    * fy;
        }
    }
    let a = PlaneRef::from_geometry(&a, g).unwrap();
    let b = PlaneRef::from_geometry(&b, g).unwrap();
    let noise = PlaneRef::from_geometry(&unrelated, g).unwrap();
    let cfg = MosaicGeometryConfig::default();
    let p = [320.0, 320.0];
    let ca = strehl_core::align::downsample(a, grid::FACTOR).unwrap();
    for (moving, proposal, positive) in [
        (b, [10.0, -6.0], true),
        (b, [145.0, -6.0], false),
        (noise, [10.0, -6.0], false),
    ] {
        let cb = strehl_core::align::downsample(moving, grid::FACTOR).unwrap();
        let q = [p[0] + proposal[0], p[1] + proposal[1]];
        let seed = anchored_seed(Cx::ONE, p, q, g);
        let actual = grid::coarse_seed(ca.as_ref(), cb.as_ref(), g, [p, q], seed, &cfg, None)
            .and_then(|coarse| {
                refine_on_planes(a, moving, p, point(coarse, p, g), coarse, &cfg, None)
            });
        assert_eq!(
            actual.is_ok(),
            positive,
            "proposal {proposal:?}: {actual:?}"
        );
        if let Ok((fit, _, _, _, _, _, _)) = actual {
            let found = point(fit, p, g);
            assert!(
                (found[0] - p[0] - shift[0]).hypot(found[1] - p[1] - shift[1]) < 0.25,
                "{found:?}"
            );
        }
    }
}

#[test]
fn actual_native_search_cannot_share_other_views_training_patch_with_holdout() {
    let g = PlaneGeometry {
        width: 384,
        height: 256,
    };
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(g, x as f64, y as f64)))
        .collect();
    let a = PlaneRef::from_geometry(&a, g).unwrap();
    let guide = super::super::matching::tests::guide(0, 714, [0, 0], false);
    let cfg = MosaicGeometryConfig::default();
    let fit = support::RoleWitness::new(&guide, Similarity::IDENTITY, false, &cfg).unwrap();
    let heldout = support::RoleWitness::new(&guide, Similarity::IDENTITY, true, &cfg).unwrap();
    let p = [192.0, 192.0];
    assert!(refine_on_planes(a, a, p, p, Similarity::IDENTITY, &cfg, Some(&[fit, fit])).is_ok());
    assert!(
        refine_on_planes(
            a,
            a,
            p,
            p,
            Similarity::IDENTITY,
            &cfg,
            Some(&[fit, heldout])
        )
        .is_err()
    );
}

#[test]
fn iterated_native_observer_rejects_clipping_beyond_nominal_seed_box_and_keeps_receipt() {
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
    let a: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(g, x as f64, y as f64)))
        .collect();
    let b: Vec<_> = (0..g.height)
        .flat_map(|y| (0..g.width).map(move |x| texture(g, x as f64 - 8.0, y as f64)))
        .collect();
    let a = PlaneRef::from_geometry(&a, g).unwrap();
    let b = PlaneRef::from_geometry(&b, g).unwrap();
    let raw_a = Original {
        g,
        pixels: vec![1000; 4 * g.pixels()],
    };
    let mut raw_b = Original {
        g,
        pixels: vec![1000; 4 * g.pixels()],
    };
    let config = MosaicGeometryConfig::default();
    let pa = [192.0, 192.0];
    let pb = [194.0, 192.0];
    let seed = anchored_seed(Cx::ONE, pa, pb, g);
    let mut measurements = Vec::new();
    let originals = [
        support::PixelWitness {
            source: &raw_a,
            white: 16000.0,
            filter_halo: 0,
        },
        support::PixelWitness {
            source: &raw_b,
            white: 16000.0,
            filter_halo: 0,
        },
    ];
    assert!(
        refine_on_planes_observed(
            a,
            b,
            pa,
            pb,
            seed,
            &config,
            None,
            Some(&originals),
            &mut measurements
        )
        .is_ok()
    );
    assert!(measurements.iter().any(|m| m.attempted_passes > 1));
    // x=239 is beyond the seed's nominal half-width43 (194+43=237),
    // but inside the moving query after the measured +8-pixel correction.
    raw_b.pixels[2 * 192 * 2 * g.width + 2 * 239 + 1] = 16000;
    assert!(unclipped_patch(&raw_b, 16000.0, pb, 43));
    measurements.clear();
    let originals = [
        support::PixelWitness {
            source: &raw_a,
            white: 16000.0,
            filter_halo: 0,
        },
        support::PixelWitness {
            source: &raw_b,
            white: 16000.0,
            filter_halo: 0,
        },
    ];
    let refusal = refine_on_planes_observed(
        a,
        b,
        pa,
        pb,
        seed,
        &config,
        None,
        Some(&originals),
        &mut measurements,
    )
    .unwrap_err();
    assert!(
        refusal
            .to_string()
            .contains("actual native search footprint"),
        "{refusal}"
    );
    assert!(measurements.iter().any(|m| !m.support_unclipped));
    assert!(
        measurements
            .iter()
            .all(|m| m.rms_quad.is_some() && !m.observations.is_empty())
    );
    let encoded = serde_json::to_vec(&measurements).unwrap();
    let decoded: Vec<NativeMeasurement> = serde_json::from_slice(&encoded).unwrap();
    let mut receipt = refused_dependency_fixture(pa, false);
    receipt.measurements = decoded.clone();
    let poses = [
        Similarity {
            a: Cx::new(1.07, 0.04),
            b: Cx::new(3., -7.),
        },
        Similarity {
            a: Cx::new(0.97, -0.03),
            b: Cx::new(-5., 8.),
        },
    ];
    let mut filtered = config.clone();
    filtered.native_lowpass = true;
    let audit = native_attempted_support(&receipt, poses, g, &filtered)
        .unwrap()
        .unwrap();
    // Direct independent corner calculation includes both forward/reverse
    // traces, complete attempted bounds, filter halo and inverse pass gauge.
    let mut expected = [[[f64::INFINITY; 2], [f64::NEG_INFINITY; 2]]; 2];
    for measurement in &receipt.measurements {
        for (source, bounds) in measurement.sampled_bounds_quad.unwrap().iter().enumerate() {
            let pass = if measurement.direction.starts_with("reverse") {
                1 - source
            } else {
                source
            };
            let inverse = poses[pass].invert().unwrap();
            for x in [bounds[0][0] - 2., bounds[1][0] + 2.] {
                for y in [bounds[0][1] - 2., bounds[1][1] + 2.] {
                    let q = inverse.apply_at(x, y, g.width as f64 * 0.5, g.height as f64 * 0.5);
                    expected[pass][0][0] = expected[pass][0][0].min(q.0);
                    expected[pass][0][1] = expected[pass][0][1].min(q.1);
                    expected[pass][1][0] = expected[pass][1][0].max(q.0);
                    expected[pass][1][1] = expected[pass][1][1].max(q.1);
                }
            }
        }
    }
    assert_eq!(audit, expected);
    assert_eq!(decoded.len(), measurements.len());
    assert_eq!(decoded[0].observations, measurements[0].observations);
    assert_eq!(
        decoded[0].rms_quad.map(f32::to_bits),
        measurements[0].rms_quad.map(f32::to_bits)
    );
}
