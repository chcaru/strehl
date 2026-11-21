use super::*;
use crate::{RegionAdjustment, SpatialTreatment};

/// The pre-P7 `apply_pixel`, verbatim: every region for every pixel.
fn unculled(recipe: &DevelopmentRecipe, rgb: [f32; 3], uv: [f32; 2]) -> [f32; 3] {
    let mut v = recipe.global.apply(rgb, 1.0);
    for region in &recipe.regions {
        if region.enabled && region.adjustments != Adjustments::default() {
            v = region
                .adjustments
                .apply(v, region.shape.weight(uv, region.feather));
        }
    }
    for treatment in &recipe.spatial {
        let weight = match treatment.target_region.as_deref() {
            None => 1.0,
            Some(id) => recipe
                .regions
                .iter()
                .find(|r| r.id == id && r.enabled)
                .map_or(0.0, |r| r.shape.weight(uv, r.feather)),
        };
        v = treatment.apply(v, uv, weight);
    }
    v
}

fn region(id: usize, shape: RegionShape) -> RegionAdjustment {
    RegionAdjustment {
        id: format!("r{id}"),
        name: format!("Region {id}"),
        note: String::new(),
        shape,
        feather: [0.0, 0.35, 0.8][id % 3],
        enabled: id % 7 != 3,
        adjustments: Adjustments {
            exposure: 0.4 - (id % 5) as f32 * 0.2,
            saturation: 15.0,
            temperature: -10.0 + id as f32,
            ..Default::default()
        },
        source_range: None,
    }
}

fn treatment(target: Option<&str>) -> SpatialTreatment {
    SpatialTreatment {
        version: 2,
        target_region: target.map(Into::into),
        parameters: Default::default(),
        amount: 0.8,
        bounds: [[0.0, 0.0], [1.0, 1.0]],
        width: 4,
        height: 3,
        levels: 5,
        log_min: -8.0,
        log_max: 2.0,
        tone_ev: (0..60).map(|i| (i % 7) as f32 * 0.05 - 0.1).collect(),
        color_gain: (0..60).map(|i| 1.0 + (i % 5) as f32 * 0.01).collect(),
        delivery_ceiling: 4.0,
        centering_ev: 0.01,
    }
}

/// Every shape kind, with boundaries crossing the test grid, and a spatial
/// treatment scoped to a polygon and one to a stroke.
fn recipe() -> DevelopmentRecipe {
    let mut regions = Vec::new();
    for i in 0..60usize {
        let c = [
            0.05 + (i * 37 % 90) as f32 / 100.0,
            0.05 + (i * 53 % 90) as f32 / 100.0,
        ];
        let r = [0.02 + (i % 4) as f32 * 0.03, 0.03 + (i % 3) as f32 * 0.04];
        let shape = match i % 4 {
            0 => RegionShape::Ellipse {
                center: c,
                radius: r,
            },
            1 => RegionShape::Rectangle {
                min: [(c[0] - r[0]).max(0.0), (c[1] - r[1]).max(0.0)],
                max: [(c[0] + r[0]).min(1.0), (c[1] + r[1]).min(1.0)],
            },
            2 => RegionShape::Polygon {
                points: (0..7)
                    .map(|k| {
                        let a = k as f32 * std::f32::consts::TAU / 7.0;
                        let s = if k % 2 == 0 { 1.0 } else { 0.55 };
                        [
                            (c[0] + r[0] * s * a.cos()).clamp(0.0, 1.0),
                            (c[1] + r[1] * s * a.sin()).clamp(0.0, 1.0),
                        ]
                    })
                    .collect(),
            },
            _ => RegionShape::Stroke {
                points: (0..40)
                    .map(|k| {
                        let t = k as f32 / 39.0;
                        [
                            (c[0] - 0.2 + 0.4 * t).clamp(0.0, 1.0),
                            (c[1] + 0.08 * (t * 9.0).sin()).clamp(0.0, 1.0),
                        ]
                    })
                    .collect(),
                radius: [r[0] * 0.5, r[1] * 0.5],
            },
        };
        regions.push(region(i, shape));
    }
    let mut recipe = DevelopmentRecipe {
        regions,
        ..Default::default()
    };
    recipe.global.exposure = 0.3;
    recipe.spatial = vec![
        treatment(None),
        treatment(Some("r2")),
        treatment(Some("r7")),
    ];
    recipe.validate().unwrap();
    recipe
}

fn grid() -> impl Iterator<Item = [f32; 2]> {
    // Pixel centres of a 331 x 257 raster, plus the exact edges.
    (0..=257).flat_map(|y| (0..=331).map(move |x| [x as f32 / 331.0, y as f32 / 257.0]))
}

#[test]
fn culled_and_prepared_paths_are_bit_identical_to_the_unculled_loop() {
    let recipe = recipe();
    let prepared = recipe.prepare();
    let mut culled_weight_zero = 0usize;
    let mut samples = 0usize;
    for uv in grid() {
        let rgb = [
            0.02 + uv[0] * 0.9,
            0.18 * (1.0 + uv[1]),
            0.05 + uv[0] * uv[1],
        ];
        let want = unculled(&recipe, rgb, uv);
        let plain = recipe.apply_pixel(rgb, uv);
        let fast = prepared.apply_pixel(rgb, uv);
        assert_eq!(want.map(f32::to_bits), plain.map(f32::to_bits), "{uv:?}");
        assert_eq!(want.map(f32::to_bits), fast.map(f32::to_bits), "{uv:?}");
        for r in &recipe.regions {
            let p = r.shape.prepare();
            assert_eq!(
                r.shape.weight(uv, r.feather).to_bits(),
                p.weight(uv, r.feather).to_bits()
            );
            if !p.may_contain(uv) {
                culled_weight_zero += 1;
            }
            samples += 1;
        }
    }
    assert!(
        culled_weight_zero * 10 > samples * 8,
        "culling must actually skip work"
    );
}

#[test]
fn a_shrunken_box_is_caught_by_the_same_grid() {
    // Negative control: culling 2% inside the true box changes pixels, so the
    // identity test above reaches the boundary regime it guards.
    let recipe = recipe();
    let mut differing = 0;
    for uv in grid() {
        let rgb = [0.3, 0.2, 0.1];
        let mut v = recipe.global.apply(rgb, 1.0);
        for r in &recipe.regions {
            let (lo, hi) = r.shape.cull_box();
            let shrink = [(hi[0] - lo[0]) * 0.02, (hi[1] - lo[1]) * 0.02];
            let inside = uv[0] >= lo[0] + shrink[0]
                && uv[0] <= hi[0] - shrink[0]
                && uv[1] >= lo[1] + shrink[1]
                && uv[1] <= hi[1] - shrink[1];
            if r.enabled && r.adjustments != Adjustments::default() && inside {
                v = r.adjustments.apply(v, r.shape.weight(uv, r.feather));
            }
        }
        let mut want = recipe.global.apply(rgb, 1.0);
        for r in &recipe.regions {
            if r.enabled && r.adjustments != Adjustments::default() {
                want = r.adjustments.apply(want, r.shape.weight(uv, r.feather));
            }
        }
        if v != want {
            differing += 1;
        }
    }
    assert!(differing > 100, "only {differing} samples differ");
}

#[test]
fn layer_order_changes_application_but_not_list_order() {
    let mut recipe = DevelopmentRecipe::default();
    for i in 0..3 {
        let mut r = region(
            i,
            RegionShape::Rectangle {
                min: [0.1, 0.1],
                max: [0.9, 0.9],
            },
        );
        r.enabled = true;
        r.feather = 0.0;
        recipe.regions.push(r);
    }
    recipe.regions[0].adjustments = Adjustments {
        exposure: 1.0,
        ..Default::default()
    };
    recipe.regions[1].adjustments = Adjustments {
        contrast: 80.0,
        ..Default::default()
    };
    let uv = [0.5, 0.5];
    let rgb = [0.05, 0.04, 0.03];
    let listed = recipe.apply_pixel(rgb, uv);
    assert_eq!(recipe.application_order(), vec![0, 1, 2]);
    recipe.move_layer("r1", 0).unwrap();
    assert_eq!(recipe.layers_order, vec!["r1", "r0", "r2"]);
    assert_eq!(recipe.application_order(), vec![1, 0, 2]);
    recipe.validate().unwrap();
    let reordered = recipe.apply_pixel(rgb, uv);
    assert_ne!(listed, reordered, "exposure and contrast do not commute");
    assert_eq!(
        reordered.map(f32::to_bits),
        recipe.prepare().apply_pixel(rgb, uv).map(f32::to_bits)
    );
    // Unlisted regions follow in list order; moving back clears the order.
    recipe.layers_order = vec!["r2".into()];
    assert_eq!(recipe.application_order(), vec![2, 0, 1]);
    recipe.layers_order.clear();
    recipe.move_layer("r1", 1).unwrap();
    assert!(
        recipe.layers_order.is_empty(),
        "list order needs no explicit order"
    );
    recipe.move_layer("r2", 0).unwrap();
    assert_eq!(recipe.remove_region("r2").unwrap().id, "r2");
    assert!(recipe.layers_order.iter().all(|id| id != "r2"));
    recipe.validate().unwrap();
    for bad in [
        vec!["r0".to_owned(), "r0".to_owned()],
        vec!["missing".to_owned()],
    ] {
        let mut broken = recipe.clone();
        broken.layers_order = bad;
        assert!(broken.validate().is_err());
    }
}
