use super::*;
use strehl_edit::{AdaptiveParameters, ImageOrigin, RegionAdjustment, RegionShape};

fn scene() -> LinearImage {
    let mut pixels = Vec::new();
    for y in 0..96 {
        for x in 0..128 {
            let light = 0.025 + 0.38 * (x + y) as f32 / 222.0;
            pixels.extend_from_slice(&[light * 1.2, light, light * 0.7]);
        }
    }
    LinearImage {
        width: 128,
        height: 96,
        pixels,
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

#[test]
fn effect_map_measures_actual_development_and_zero_is_neutral() {
    let image = scene();
    let original = DevelopmentRecipe::default();
    let suggested = strehl_edit::analyze_adaptive(&image, &original)
        .unwrap()
        .suggested;
    let effect = render_effect(&image, &suggested, None, &AtomicBool::new(false)).unwrap();
    assert!(
        effect.lift_fraction + effect.deepen_fraction + effect.color_fraction > 0.01,
        "positive control must actually change mapped samples"
    );
    assert!(effect.image.pixels.iter().any(|p| p.r() != p.b()));
    let mut zero = suggested.clone();
    zero.spatial[0].amount = 0.0;
    let placebo = render_effect(&image, &zero, None, &AtomicBool::new(false)).unwrap();
    assert_eq!(
        [
            placebo.lift_fraction,
            placebo.deepen_fraction,
            placebo.color_fraction
        ],
        [0.0; 3]
    );
    assert!(
        placebo
            .image
            .pixels
            .iter()
            .all(|p| p.r() == p.g() && p.g() == p.b())
    );
    let mut flat = image.clone();
    flat.pixels.fill(0.18);
    let neutral = render_effect(&flat, &original, None, &AtomicBool::new(false)).unwrap();
    assert!(
        neutral
            .image
            .pixels
            .windows(2)
            .all(|pair| pair[0] == pair[1])
    );
    assert!(render_effect(&image, &suggested, None, &AtomicBool::new(true)).is_err());
}

#[test]
fn effect_map_respects_actual_region_mask_not_just_lattice_bounds() {
    let image = scene();
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "local".into(),
        name: "Local".into(),
        note: String::new(),
        shape: RegionShape::Ellipse {
            center: [0.6, 0.5],
            radius: [0.3, 0.35],
        },
        feather: 0.2,
        enabled: true,
        adjustments: Default::default(),
        source_range: None,
    });
    let suggestion = strehl_edit::analyze_adaptive_with_parameters(
        &image,
        &recipe,
        Some("local"),
        AdaptiveIntent::Balance,
        AdaptiveParameters::default(),
    )
    .unwrap();
    let effect = render_effect(
        &image,
        &suggestion.suggested,
        Some("local"),
        &AtomicBool::new(false),
    )
    .unwrap();
    let region = &recipe.regions[0];
    let mut changed_inside = false;
    let mut checked_outside = 0;
    for y in 0..96 {
        for x in 0..128 {
            let p = effect.image.pixels[y * 128 + x];
            let weight = region.shape.weight(
                [(x as f32 + 0.5) / 128.0, (y as f32 + 0.5) / 96.0],
                region.feather,
            );
            if weight == 0.0 {
                assert_eq!(
                    [p.r(), p.g()],
                    [p.b(), p.b()],
                    "map falsely colors outside the actual mask"
                );
                checked_outside += 1;
            } else {
                changed_inside |= p.r() != p.b();
            }
        }
    }
    assert!(checked_outside > 1000 && changed_inside);
}

#[test]
fn ready_effect_for_previous_pixels_or_scope_is_discarded_before_upload() {
    let image = Arc::new(scene());
    let recipe = strehl_edit::analyze_adaptive(&image, &DevelopmentRecipe::default())
        .unwrap()
        .suggested;
    let key = Key {
        image: Arc::clone(&image),
        recipe: recipe.clone(),
        target: None,
    };
    let task = jobs::spawn_task("effect-stale-control", |_| {
        Ok(EffectImage {
            image: egui::ColorImage::filled([1, 1], Color32::RED),
            lift_fraction: 1.0,
            deepen_fraction: 0.0,
            color_fraction: 0.0,
        })
    });
    let mut map = EffectMap {
        pending: Some(Pending {
            key: key.clone(),
            task,
        }),
        ..Default::default()
    };
    let replacement = Arc::new((*image).clone());
    map.poll(&egui::Context::default(), Some(&replacement), &recipe, None);
    assert!(map.pending.is_none() && map.texture.is_none());
    // Even identical pixels are a different image identity; changing only the
    // scope also invalidates an already displayed explanation.
    map.key = Some(key);
    map.poll(
        &egui::Context::default(),
        Some(&image),
        &recipe,
        Some("other"),
    );
    assert!(map.key.is_none());
}

#[test]
fn failed_replacement_never_labels_the_old_map_as_current() {
    let ctx = egui::Context::default();
    let image = Arc::new(scene());
    let recipe = DevelopmentRecipe::default();
    let old_key = Key {
        image: Arc::clone(&image),
        recipe: recipe.clone(),
        target: None,
    };
    let mut changed = recipe.clone();
    changed.global.exposure = 1.0;
    let new_key = Key {
        image: Arc::clone(&image),
        recipe: changed.clone(),
        target: None,
    };
    let (sender, ready) = mpsc::sync_channel(1);
    let task = jobs::spawn_notifying_task(
        "failed-effect-control",
        |_| anyhow::bail!("planted effect-map failure"),
        move || {
            let _ = sender.send(());
        },
    );
    ready.recv_timeout(Duration::from_secs(5)).unwrap();
    let mut map = EffectMap {
        key: Some(old_key),
        texture: Some(ctx.load_texture(
            "old-effect",
            egui::ColorImage::filled([2, 2], Color32::RED),
            egui::TextureOptions::LINEAR,
        )),
        summary: Some([1.0, 0.0, 0.0]),
        pending: Some(Pending { key: new_key, task }),
        error: None,
    };
    assert!(
        map.texture.is_some(),
        "negative control needs an existing visible map"
    );
    map.poll(&ctx, Some(&image), &changed, None);
    assert!(map.pending.is_none() && map.texture.is_none() && map.summary.is_none());
    assert!(
        map.key.as_ref().unwrap().matches(&image, &changed, None),
        "failed request should be remembered instead of endlessly retried"
    );
    assert_eq!(map.error.as_deref(), Some("planted effect-map failure"));
}
