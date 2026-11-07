use super::*;
use crate::session_mosaic_geometry::GuideReceipt;
use strehl_core::plane::PlaneGeometry;

pub(crate) fn guide(pass: usize, seed: u64, shift: [isize; 2], flat: bool) -> MosaicGuide {
    let geometry = PlaneGeometry {
        width: 384,
        height: 256,
    };
    let mut base = vec![0.0_f32; geometry.pixels()];
    let mut state = seed;
    for value in &mut base {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
        *value = ((state >> 32) & 65535) as f32 / 64.0;
    }
    let mut smooth = base.clone();
    for y in 1..geometry.height - 1 {
        for x in 1..geometry.width - 1 {
            smooth[y * geometry.width + x] = (-1..=1)
                .flat_map(|dy| (-1..=1).map(move |dx| (dx, dy)))
                .map(|(dx, dy)| {
                    base[(y as isize + dy) as usize * geometry.width + (x as isize + dx) as usize]
                })
                .sum::<f32>()
                / 9.0;
        }
    }
    let mut intensity = vec![0.0; geometry.pixels()];
    let mut covered = vec![false; geometry.pixels()];
    for y in 0..geometry.height {
        for x in 0..geometry.width {
            let sx = x as isize - shift[0];
            let sy = y as isize - shift[1];
            if sx >= 0 && sy >= 0 && sx < geometry.width as isize && sy < geometry.height as isize {
                intensity[y * geometry.width + x] = if flat {
                    137.0
                } else {
                    smooth[sy as usize * geometry.width + sx as usize]
                };
                covered[y * geometry.width + x] = true;
            }
        }
    }
    let n = geometry.pixels();
    MosaicGuide {
        pass,
        source_geometry: geometry,
        geometry,
        origin: [0.0, 0.0],
        step: 1,
        intensity,
        covered,
        focus_ordinal: vec![3.0; n],
        focus_width: vec![1.0; n],
        usable_focus: vec![true; n],
        source_indices: vec![[3 * pass + 1, usize::MAX, usize::MAX, usize::MAX]; n],
        receipt: GuideReceipt {
            pass,
            source_geometry: [geometry.width, geometry.height],
            guide_geometry: [geometry.width, geometry.height],
            origin_quad_pixels: [0.0, 0.0],
            step_quad_pixels: 1,
            alignment_sha256: "control".into(),
            focus_evidence_sha256: "control".into(),
            guide_sha256: "control".into(),
            covered_pixels: n,
            usable_focus_pixels: n,
            source_contributions: vec![(3 * pass + 1, n)],
            reserved_work_bytes: 0,
            construction: "synthetic operator control".into(),
        },
    }
}
fn config() -> MosaicGeometryConfig {
    MosaicGeometryConfig {
        native_tile: 16,
        native_search_radius: 2,
        maximum_features: 1000,
        ..MosaicGeometryConfig::default()
    }
}

pub(crate) fn island_fixture() -> ([MosaicGuide; 2], MosaicGeometryConfig) {
    use crate::session_mosaic_geometry::roles::{
        AncestorFootprint, AnchorGrid, IslandProposal, Rectangle, RolePlan,
    };
    let mut guides = [guide(0, 714, [0, 0], false), guide(1, 714, [0, 0], false)];
    for guide in &mut guides {
        guide.step = 4;
        guide.origin = [1.5; 2];
        guide.source_geometry.width *= 4;
        guide.source_geometry.height *= 4;
        guide.receipt.source_geometry = [guide.source_geometry.width, guide.source_geometry.height];
        guide.receipt.step_quad_pixels = 4;
        guide.receipt.origin_quad_pixels = [1.5; 2];
    }
    let grids = [0, 1].map(|pass| AnchorGrid {
        source_size_quad: [1536, 1024],
        guide_origin_quad: [1.5; 2],
        guide_step_quad: 4,
        initial_block_guide_pixels: 128,
        global_source_range: [3 * pass, 3 * pass + 3],
    });
    let ancestors = [0, 1]
        .into_iter()
        .map(|pass| AncestorFootprint {
            pass,
            source: 3 * pass + 1,
            measurement_id: format!("initial-fit-pass{pass}"),
            bounds: Rectangle::around([700., 100.], 40.).unwrap(),
        })
        .collect();
    let proposals = [[144., 144.], [368., 144.], [256., 368.]]
        .into_iter()
        .enumerate()
        .map(|(id, point)| IslandProposal {
            id: format!("frozen-site-{id}"),
            cell: [0, 0],
            reference_center_quad: point,
            original_witnesses: [vec![1], vec![4]],
            query_radius_quad: [43., 43.],
        })
        .collect();
    let plan = RolePlan::build(
        "a".repeat(64),
        "b".repeat(64),
        grids,
        [1., 0., 0., 0.],
        24.,
        ancestors,
        proposals,
    )
    .unwrap()
    .freeze()
    .unwrap();
    assert_eq!(plan.plan.islands.len(), 3);
    let cfg = MosaicGeometryConfig {
        maximum_features: 96,
        role_plan: Some(Box::new(plan)),
        ..Default::default()
    };
    (guides, cfg)
}

#[test]
fn frozen_island_poison_leaves_both_actual_feature_stages_and_fit_seeds_exact() {
    use crate::session_mosaic_geometry::roles::{Rectangle, SpatialRole};
    let (clean, stage_two) = island_fixture();
    let (mut poisoned, _) = island_fixture();
    let frozen = stage_two.role_plan.as_ref().unwrap();
    let frozen_hash = frozen.sha256.clone();
    let mut poisoned_pixels = 0;
    for (pass, guide) in poisoned.iter_mut().enumerate() {
        for y in 0..guide.geometry.height {
            for x in 0..guide.geometry.width {
                let physical =
                    Rectangle::around(guide.full_point([x as f64, y as f64]), 1.5).unwrap();
                if matches!(
                    frozen.plan.classify(pass, physical),
                    Some(SpatialRole::Heldout(_))
                ) {
                    guide.intensity[y * guide.geometry.width + x] =
                        ((x * 193 + y * 977 + pass * 17) % 101) as f32 * 100_000.0;
                    poisoned_pixels += 1;
                }
            }
        }
    }
    assert!(poisoned_pixels > 1000);
    let mut stage_one = stage_two.clone();
    stage_one.role_plan = None;
    for cfg in [&stage_one, &stage_two] {
        for (a, b) in clean.iter().zip(&poisoned) {
            let fit = |g: &MosaicGuide| {
                scale_features::features(g, cfg, true)
                    .into_iter()
                    .filter(|f| !f.heldout)
                    .collect::<Vec<_>>()
            };
            let original = fit(a);
            assert!(original.len() >= 8);
            assert_eq!(feature_bits(&original), feature_bits(&fit(b)));
        }
        let a = discover_pairs(&clean, cfg, 128 << 20).unwrap();
        let b = discover_pairs(&poisoned, cfg, 128 << 20).unwrap();
        assert!(a[0].seed_a_to_b.is_some());
        assert_eq!(a[0].seed_a_to_b, b[0].seed_a_to_b);
        assert_eq!(a[0].fit_inliers, b[0].fit_inliers);
        let fits = |p: &PairDiscovery| {
            serde_json::to_value(
                p.correspondences
                    .iter()
                    .filter(|m| m.role == MatchRole::Fit)
                    .collect::<Vec<_>>(),
            )
            .unwrap()
        };
        assert_eq!(fits(&a[0]), fits(&b[0]));
    }
    assert!(
        scale_features::features(&clean[0], &stage_two, true)
            .iter()
            .all(|f| !f.heldout),
        "stage-two validation cannot silently reuse broad descriptors"
    );
    frozen.verify().unwrap();
    assert_eq!(frozen_hash, frozen.sha256);
}

pub(crate) fn feature_bits(features: &[Feature]) -> Vec<serde_json::Value> {
    features.iter().map(|f| serde_json::json!({
        "point":f.point.map(f64::to_bits), "descriptor":f.descriptor.map(f32::to_bits).to_vec(),
        "response":f.response.to_bits(), "source":f.source, "block":f.block,
        "heldout":f.heldout, "radius":f.support_radius.to_bits()
    })).collect()
}

#[test]
fn heldout_pixel_and_competitor_poison_leave_fit_detection_and_seed_exact() {
    let cfg = MosaicGeometryConfig {
        maximum_features: 96,
        ..config()
    };
    let original = [guide(0, 714, [0, 0], false), guide(1, 714, [0, 0], false)];
    let mut poisoned = [guide(0, 714, [0, 0], false), guide(1, 714, [0, 0], false)];
    for (pass, image) in poisoned.iter_mut().enumerate() {
        for y in 0..image.geometry.height {
            for x in 0..image.geometry.width {
                if (x / cfg.holdout_block_guide_pixels + y / cfg.holdout_block_guide_pixels)
                    .is_multiple_of(3)
                {
                    image.intensity[y * image.geometry.width + x] =
                        ((x * 193 + y * 977 + pass * 181) % 101) as f32 * 100_000.0;
                }
            }
        }
    }
    let mut clean_fit = Vec::new();
    for (a, b) in original.iter().zip(&poisoned) {
        let fit = |g: &MosaicGuide| {
            scale_features::features(g, &cfg, true)
                .into_iter()
                .filter(|f| !f.heldout)
                .collect::<Vec<_>>()
        };
        let clean = fit(a);
        let dirty = fit(b);
        assert!(clean.len() >= 8, "positive FIT features must survive");
        assert_eq!(feature_bits(&clean), feature_bits(&dirty));
        clean_fit.push(clean);
    }
    let baseline = discover_pairs(&original, &cfg, 128 << 20).unwrap();
    let poison = discover_pairs(&poisoned, &cfg, 128 << 20).unwrap();
    assert!(baseline[0].seed_a_to_b.is_some());
    assert_eq!(baseline[0].seed_a_to_b, poison[0].seed_a_to_b);
    assert_eq!(baseline[0].fit_inliers, poison[0].fit_inliers);
    let fit_matches = |p: &PairDiscovery| {
        serde_json::to_value(
            p.correspondences
                .iter()
                .filter(|m| m.role == MatchRole::Fit)
                .collect::<Vec<_>>(),
        )
        .unwrap()
    };
    assert_eq!(fit_matches(&baseline[0]), fit_matches(&poison[0]));
    // A held-only exact descriptor duplicate must not become the FIT
    // second competitor and defeat its ratio test.
    let before = nearest(&clean_fit[0], &clean_fit[1], cfg.descriptor_ratio);
    assert!(before.iter().flatten().count() >= 8);
    let mut adversary = clean_fit[1].clone();
    for feature in &clean_fit[1] {
        let mut duplicate = feature.clone();
        duplicate.heldout = true;
        duplicate.point[0] += 32.0;
        adversary.push(duplicate);
    }
    assert_eq!(
        before,
        nearest(&clean_fit[0], &adversary, cfg.descriptor_ratio)
    );
}

#[test]
fn spatial_reservation_keeps_same_role_boundaries_but_never_shares_fit_holdout_support() {
    assert_eq!(
        reserved_role([128.0, 192.0], 24.0, 128),
        Some(([1, 1], false))
    );
    assert!(reserved_role([128.0, 64.0], 24.0, 128).is_none());
    let mut footprints = Vec::new();
    for y in (32..480).step_by(16) {
        for x in (32..736).step_by(16) {
            let p = [x as f64, y as f64];
            if let Some((_, heldout)) = reserved_role(p, 31.5, 128) {
                footprints.push((p, heldout));
            }
        }
    }
    assert!(footprints.iter().any(|(_, r)| *r) && footprints.iter().any(|(_, r)| !*r));
    for (a, ar) in &footprints {
        for (b, br) in &footprints {
            if ar != br {
                assert!(
                    (a[0] - b[0]).abs() > 63.0 || (a[1] - b[1]).abs() > 63.0,
                    "fit and heldout descriptor supports overlap: {a:?}, {b:?}"
                );
            }
        }
    }
}
#[test]
fn production_mosaic_matcher_recovers_extended_view_and_reserves_spatial_holdouts() {
    let guides = [guide(0, 714, [0, 0], false), guide(1, 714, [21, -7], false)];
    let pairs = discover_pairs(&guides, &config(), 100_000_000).unwrap();
    let pair = &pairs[0];
    let model = pair.seed_a_to_b.unwrap_or_else(|| {
        panic!("positive translated texture must nominate native geometry: {pair:?}")
    });
    assert!(pair.fit_inliers >= 8, "{}", pair.fit_inliers);
    assert!((model[0] - 1.0).abs() < 0.002 && model[1].abs() < 0.002);
    assert!(
        (model[2] - 21.0).abs() < 0.2 && (model[3] + 7.0).abs() < 0.2,
        "{model:?}"
    );
    assert!(
        pair.correspondences
            .iter()
            .any(|m| m.role == MatchRole::Heldout)
    );
    for matched in pair
        .correspondences
        .iter()
        .filter(|m| m.role == MatchRole::Fit)
    {
        assert!(
            matched
                .spatial_blocks
                .iter()
                .all(|b| (b[0] + b[1]) % 3 != 0)
        );
    }
}
#[test]
fn scale_space_features_recover_rotation_scale_and_subpixel_shift() {
    let mut first = guide(0, 713, [0, 0], false);
    // A larger independent texture gives multiple spatial fit/holdout blocks.
    let g = PlaneGeometry {
        width: 768,
        height: 512,
    };
    let mut state = 713_u64;
    let mut pixels = vec![0.0_f32; g.pixels()];
    for v in &mut pixels {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
        *v = ((state >> 32) & 65535) as f32 / 64.0;
    }
    // Smooth two-dimensional scene texture; no frame-axis filtering.
    for _ in 0..2 {
        let prior = pixels.clone();
        for y in 1..g.height - 1 {
            for x in 1..g.width - 1 {
                pixels[y * g.width + x] = (-1_isize..=1)
                    .flat_map(|dy| (-1_isize..=1).map(move |dx| (dx, dy)))
                    .map(|(dx, dy)| {
                        prior[(y as isize + dy) as usize * g.width + (x as isize + dx) as usize]
                    })
                    .sum::<f32>()
                    / 9.0;
            }
        }
    }
    first.source_geometry = g;
    first.geometry = g;
    first.intensity = pixels;
    first.covered = vec![true; g.pixels()];
    first.usable_focus = vec![true; g.pixels()];
    first.focus_ordinal = vec![3.0; g.pixels()];
    first.focus_width = vec![1.0; g.pixels()];
    first.source_indices = vec![[1, usize::MAX, usize::MAX, usize::MAX]; g.pixels()];
    let scale = 1.13_f64;
    let angle = 0.11_f64;
    let model = [scale * angle.cos(), scale * angle.sin(), 21.25, -7.5];
    let denominator = model[0] * model[0] + model[1] * model[1];
    let mut second = guide(1, 713, [0, 0], false);
    second.source_geometry = g;
    second.geometry = g;
    second.intensity = vec![0.0; g.pixels()];
    second.covered = vec![false; g.pixels()];
    second.usable_focus = vec![true; g.pixels()];
    second.focus_ordinal = vec![3.0; g.pixels()];
    second.focus_width = vec![1.0; g.pixels()];
    second.source_indices = vec![[4, usize::MAX, usize::MAX, usize::MAX]; g.pixels()];
    for y in 0..g.height {
        for x in 0..g.width {
            let (xx, yy) = (x as f64 - model[2], y as f64 - model[3]);
            let sx = (model[0] * xx + model[1] * yy) / denominator;
            let sy = (-model[1] * xx + model[0] * yy) / denominator;
            if let Some(v) = sample(
                &first.intensity,
                &first.covered,
                g.width,
                g.height,
                sx as f32,
                sy as f32,
            ) {
                second.intensity[y * g.width + x] = 1.7 * v + 37.0;
                second.covered[y * g.width + x] = true;
            }
        }
    }
    let cfg = config();
    let fixed = [
        fixed_scale_features(&first, &cfg),
        fixed_scale_features(&second, &cfg),
    ];
    let fixed_matches = nearest(&fixed[0], &fixed[1], cfg.descriptor_ratio)
        .iter()
        .flatten()
        .count();
    let pairs = discover_pairs(&[first, second], &cfg, 300_000_000).unwrap();
    let pair = &pairs[0];
    let recovered = pair.seed_a_to_b.unwrap_or_else(|| {
        panic!("scale-space failed; fixed-scale directional matches {fixed_matches}; {pair:?}")
    });
    assert!(pair.fit_inliers >= 8);
    // Returned similarity uses the native centred gauge, unlike this plant.
    let center = [g.width as f64 * 0.5, g.height as f64 * 0.5];
    for p in [[128.0, 128.0], [384.0, 256.0], [640.0, 384.0]] {
        let predicted = [
            recovered[0] * (p[0] - center[0]) - recovered[1] * (p[1] - center[1])
                + recovered[2]
                + center[0],
            recovered[1] * (p[0] - center[0])
                + recovered[0] * (p[1] - center[1])
                + recovered[3]
                + center[1],
        ];
        let truth = predict(model, p);
        assert!(
            distance_sq(predicted, truth).sqrt() < 1.5,
            "{predicted:?} vs {truth:?}"
        );
    }
    assert!(
        pair.correspondences
            .iter()
            .any(|m| m.role == MatchRole::Heldout)
    );
}
#[test]
fn production_mosaic_matcher_refuses_flat_and_unrelated_texture() {
    for (seed, flat) in [(911, false), (714, true)] {
        let guides = [guide(0, 714, [0, 0], false), guide(1, seed, [0, 0], flat)];
        let pairs = discover_pairs(&guides, &config(), 100_000_000).unwrap();
        assert!(
            pairs[0].seed_a_to_b.is_none(),
            "wrong or flat source must refuse"
        );
    }
}
#[test]
fn production_mosaic_matcher_refuses_repeated_period_alias() {
    let mut guides = [guide(0, 714, [0, 0], true), guide(1, 714, [0, 0], true)];
    for (pass, guide) in guides.iter_mut().enumerate() {
        for y in 0..guide.geometry.height {
            for x in 0..guide.geometry.width {
                guide.intensity[y * guide.geometry.width + x] =
                    (((x + 24 * pass) / 24 + y / 24) % 2) as f32 * 1000.0;
            }
        }
    }
    assert!(
        discover_pairs(&guides, &config(), 100_000_000).unwrap()[0]
            .seed_a_to_b
            .is_none()
    );
}
