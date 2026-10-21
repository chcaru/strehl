use super::*;
use std::sync::atomic::AtomicBool;

fn tick(cache: &mut ExplorerPreviews, ctx: &egui::Context) -> egui::FullOutput {
    ctx.run(egui::RawInput::default(), |ctx| cache.poll(ctx))
}
fn settle(cache: &mut ExplorerPreviews, ctx: &egui::Context) {
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while cache.pending() {
        tick(cache, ctx);
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(std::time::Duration::from_millis(2));
    }
}
#[test]
fn worker_resizes_once_and_failed_rows_do_not_restart_on_paint() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("large.png");
    image::RgbImage::from_pixel(1200, 700, image::Rgb([20, 80, 180]))
        .save(&path)
        .unwrap();
    let mut cache = ExplorerPreviews::default();
    let ctx = egui::Context::default();
    tick(&mut cache, &ctx);
    assert!(cache.file(&path, false).is_none());
    assert!(
        cache.entries.is_empty(),
        "Requesting a row only queues work"
    );
    settle(&mut cache, &ctx);
    let texture = cache.file(&path, false).unwrap();
    assert_eq!(texture.size()[0], SIDE as usize);
    assert!(texture.size()[1] < SIDE as usize);
    std::fs::remove_file(&path).unwrap();
    for _ in 0..6 {
        tick(&mut cache, &ctx);
        assert_eq!(cache.file(&path, false).unwrap().id(), texture.id());
        assert!(!cache.pending());
    }
    let missing = directory.path().join("missing.tiff");
    cache.file(&missing, false);
    settle(&mut cache, &ctx);
    assert!(cache.error(&missing, false).is_some());
    for _ in 0..6 {
        tick(&mut cache, &ctx);
        assert!(cache.file(&missing, false).is_none());
        assert!(!cache.pending());
    }
}
#[test]
fn current_version_uses_saved_controls_and_mismatched_pixels_use_labeled_base() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("photo.tiff");
    image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
        20,
        12,
        image::Rgb([14000, 14000, 14000]),
    )
    .save(&path)
    .unwrap();
    let image = Arc::new(strehl_edit::load_tiff(&path).unwrap());
    let mut recipe = strehl_edit::DevelopmentRecipe::default();
    recipe.global.exposure = 1.5;
    let version = photographs::save_version(
        directory.path(),
        crate::workspace_history::PhotoOwner {
            stack: None,
            run: None,
            output: path.clone(),
        },
        "Brighter",
        recipe.clone(),
        &image,
        &path,
        &AtomicBool::new(false),
    )
    .unwrap();
    let mut cache = ExplorerPreviews::default();
    let ctx = egui::Context::default();
    cache.set_current(Some(&path), Some(&image), Some(&image));
    tick(&mut cache, &ctx);
    let mut published = None;
    for _ in 0..500 {
        let (_, exact) = cache.version(Some(directory.path()), &version);
        let output = tick(&mut cache, &ctx);
        for (_, delta) in output.textures_delta.set {
            let egui::ImageData::Color(color) = delta.image;
            published = Some(color);
        }
        if exact {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(2));
    }
    let (texture, exact) = cache.version(Some(directory.path()), &version);
    assert!(exact && texture.is_some());
    let expected = image
        .render_region_sdr8(&recipe, [0.0, 0.0], [1.0, 1.0], SIDE)
        .unwrap()
        .2;
    assert_eq!(published.unwrap().pixels[0].r(), expected[0]);
    let mut different = (*image).clone();
    different.pixels[0] += 0.1;
    let different = Arc::new(different);
    cache.set_current(Some(&path), Some(&different), Some(&different));
    cache.version(Some(directory.path()), &version);
    settle(&mut cache, &ctx);
    assert!(
        !cache.version(Some(directory.path()), &version).1,
        "An old exact texture cannot be reused for different loaded pixels"
    );
}
#[test]
fn scrolling_discards_old_queued_rows_before_decode() {
    let mut cache = ExplorerPreviews::default();
    let ctx = egui::Context::default();
    tick(&mut cache, &ctx);
    for i in 0..20 {
        cache.file(Path::new(&format!("old-{i}.png")), false);
    }
    cache.clock += 2;
    tick(&mut cache, &ctx);
    assert!(
        cache.queue.is_empty() && cache.pending.is_none(),
        "Invisible rows must not delay current rows with stale I/O"
    );
}

#[test]
fn newly_loaded_photo_invalidates_cached_and_inflight_base_even_after_loading_gap() {
    for loading_gap in [false, true] {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("replaced.png");
        image::RgbImage::from_pixel(16, 12, image::Rgb([200, 10, 20]))
            .save(&path)
            .unwrap();
        let first = Arc::new(LinearImage {
            width: 16,
            height: 12,
            pixels: vec![0.2; 16 * 12 * 3],
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: None,
            baked_recipe: None,
        });
        let mut cache = ExplorerPreviews::default();
        let ctx = egui::Context::default();
        cache.set_current(Some(&path), Some(&first), Some(&first));
        tick(&mut cache, &ctx);
        cache.file(&path, false);
        settle(&mut cache, &ctx);
        let old = cache.file(&path, false).unwrap();
        image::RgbImage::from_pixel(16, 12, image::Rgb([10, 200, 20]))
            .save(&path)
            .unwrap();
        let mut changed = (*first).clone();
        changed.pixels[0] = 0.8;
        let changed = Arc::new(changed);
        if loading_gap {
            cache.set_current(None, None, None);
        }
        cache.set_current(Some(&path), Some(&changed), Some(&changed));
        assert!(
            cache.file(&path, false).is_none(),
            "A replaced photograph retained the old cached base"
        );
        let key = Request::File {
            path: path.clone(),
            source: false,
        }
        .key();
        tick(&mut cache, &ctx);
        assert!(cache.pending.as_ref().is_some_and(|p| p.key == key));
        // A second accepted decode must cancel the old in-flight base too.
        let next = Arc::new((*changed).clone());
        cache.set_current(Some(&path), Some(&next), Some(&next));
        assert!(cache.pending.is_none());
        assert!(!cache.queue.iter().any(|(r, _)| r.key() == key));
        cache.file(&path, false);
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
        let mut color = None;
        while cache.pending() {
            for (_, delta) in tick(&mut cache, &ctx).textures_delta.set {
                let egui::ImageData::Color(image) = delta.image;
                color = Some(image.pixels[0]);
            }
            assert!(std::time::Instant::now() < deadline);
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
        assert_eq!(color.unwrap(), egui::Color32::from_rgb(10, 200, 20));
        assert_ne!(cache.file(&path, false).unwrap().id(), old.id());
    }
}
