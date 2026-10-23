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
fn saved_version_uses_saved_controls_without_waiting_for_loaded_identity() {
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
    let mut published = BTreeMap::new();
    for _ in 0..500 {
        let (_, exact) = cache.version(Some(directory.path()), &version);
        let output = tick(&mut cache, &ctx);
        for (id, delta) in output.textures_delta.set {
            let egui::ImageData::Color(color) = delta.image;
            published.insert(id, color);
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
    assert_eq!(published[&texture.unwrap().id()].pixels[0].r(), expected[0]);
    let mut different = (*image).clone();
    different.pixels[0] += 0.1;
    let different = Arc::new(different);
    cache.set_current(Some(&path), Some(&different), Some(&different));
    cache.version(Some(directory.path()), &version);
    settle(&mut cache, &ctx);
    assert!(
        cache.version(Some(directory.path()), &version).1,
        "An immutable saved preview remains bound to its own pixels when another image is open"
    );
    assert!(
        cache.current.as_ref().unwrap().identity.is_none(),
        "Saved thumbnails must not hash the open 33 MP image"
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
        cache.queue.is_empty() && cache.pending.len() <= WORKERS,
        "Invisible rows must not delay current rows with stale I/O"
    );
}

#[test]
fn already_open_photo_never_reopens_its_file_or_waits_for_identity() {
    let missing = Path::new("does-not-exist/already-open.tiff");
    let image = Arc::new(LinearImage {
        width: 8,
        height: 6,
        pixels: vec![0.2; 8 * 6 * 3],
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    let mut cache = ExplorerPreviews::default();
    let ctx = egui::Context::default();
    cache.set_current(Some(missing), Some(&image), Some(&image));
    tick(&mut cache, &ctx);
    cache.file(missing, false);
    assert_eq!(
        cache.pending.len(),
        1,
        "work starts in the requesting paint, not after another polling timer"
    );
    assert!(cache.current.as_ref().unwrap().identifying.is_none());
    settle(&mut cache, &ctx);
    assert!(
        cache.file(missing, false).is_some(),
        "the loaded image must work even without a file"
    );
}

#[test]
fn reconstructed_legacy_version_remains_exact_after_leaving_its_photograph() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("legacy.tiff");
    let image = Arc::new(LinearImage {
        width: 12,
        height: 8,
        pixels: vec![0.2; 12 * 8 * 3],
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    strehl_edit::save_linear_tiff(&path, &image).unwrap();
    let mut recipe = strehl_edit::DevelopmentRecipe::default();
    recipe.global.exposure = 1.3;
    let version = photographs::save_version(
        directory.path(),
        photographs::PhotoOwner {
            stack: None,
            run: None,
            output: path.clone(),
        },
        "Legacy",
        recipe,
        &image,
        &path,
        &AtomicBool::new(false),
    )
    .unwrap();
    let derivative = directory.path().join(format!("{}.preview", version.id));
    std::fs::remove_file(&derivative).unwrap();
    let mut cache = ExplorerPreviews::default();
    let ctx = egui::Context::default();
    cache.set_current(Some(&path), Some(&image), Some(&image));
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    let mut saw_saved_miss = false;
    let saved_key = Request::SavedVersion {
        root: directory.path().into(),
        version: Box::new(version.clone()),
    }
    .key();
    let exact_texture = loop {
        tick(&mut cache, &ctx);
        saw_saved_miss |= cache
            .entries
            .get(&saved_key)
            .is_some_and(|entry| entry.error.is_some());
        let (texture, exact) = cache.version(Some(directory.path()), &version);
        if exact {
            break texture.unwrap();
        }
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(std::time::Duration::from_millis(2));
    };
    assert!(
        saw_saved_miss,
        "fixture must exercise reconstruction after a missing saved derivative"
    );
    assert!(derivative.is_file());
    assert_eq!(
        cache.entries[&saved_key].texture.as_ref().unwrap().id(),
        exact_texture.id()
    );
    cache.set_current(None, None, None);
    let (after, exact) = cache.version(Some(directory.path()), &version);
    assert!(
        exact,
        "leaving an image must not restore the old cached miss"
    );
    assert_eq!(after.unwrap().id(), exact_texture.id());
}

#[test]
fn cancelled_decoders_keep_their_lanes_until_completion() {
    let mut cache = ExplorerPreviews::default();
    let ctx = egui::Context::default();
    tick(&mut cache, &ctx);
    let gate = Arc::new(std::sync::Barrier::new(WORKERS + 1));
    for i in 0..WORKERS {
        let gate = gate.clone();
        cache.pending.push(Pending {
            key: format!("busy-{i}"),
            task: jobs::spawn_task("blocked-test-preview", move |_| {
                gate.wait();
                anyhow::bail!("released")
            }),
        });
    }
    for pending in &cache.pending {
        pending.task.cancel();
    }
    cache.file(Path::new("new.png"), false);
    assert_eq!(cache.pending.len(), WORKERS);
    assert_eq!(
        cache.queue.len(),
        1,
        "cancel must not free a lane while a decoder is still working"
    );
    gate.wait();
    settle(&mut cache, &ctx);
    assert!(cache.pending.is_empty());
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
        assert!(cache.pending.iter().any(|p| p.key == key));
        // A second accepted decode must cancel the old in-flight base too.
        let next = Arc::new((*changed).clone());
        cache.set_current(Some(&path), Some(&next), Some(&next));
        assert!(cache.pending.iter().all(|p| p.task.is_cancelled()));
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
        let expected =
            preview::explorer::render(&path, &next, &Default::default(), [16, 12]).unwrap();
        assert_eq!(
            color.unwrap(),
            egui::Color32::from_rgb(expected.rgba[0], expected.rgba[1], expected.rgba[2])
        );
        assert_ne!(cache.file(&path, false).unwrap().id(), old.id());
    }
}
