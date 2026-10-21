//! Independent controls: cache admission and identity, without decoding user data.
use super::*;

fn image() -> Arc<LinearImage> {
    Arc::new(LinearImage {
        width: 3,
        height: 2,
        pixels: vec![0.25; 18],
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    })
}

fn version() -> PhotoVersion {
    let identity = photographs::PhotoIdentity {
        canonical_path: "fixture/result.tiff".into(),
        bytes: 18,
        dimensions: [3, 2],
        sha256: "1".repeat(64),
    };
    PhotoVersion {
        id: "a".repeat(32),
        owner: photographs::PhotoOwner {
            stack: Some(9),
            run: Some("fixture".into()),
            output: "fixture/result.tiff".into(),
        },
        name: "Version".into(),
        created: 1,
        photo: identity.clone(),
        decoded_source: identity,
        loaded_sha256: "2".repeat(64),
    }
}

fn file(number: usize) -> Request {
    Request::File {
        path: format!("fixture/photograph-{number:03}.tiff").into(),
        source: false,
    }
}

#[test]
fn reused_version_id_does_not_reuse_another_roots_or_pixels_texture() {
    let preview = image();
    let make = |root: &str, version: PhotoVersion| Request::Version {
        root: root.into(),
        version: Box::new(version),
        image: Arc::downgrade(&preview),
    };
    let original = make("library-one", version());
    let mut changed_pixels = version();
    changed_pixels.loaded_sha256 = "3".repeat(64);
    let mut changed_output = version();
    changed_output.photo.sha256 = "4".repeat(64);
    let alternatives = [
        make("library-two", version()),
        make("library-one", changed_pixels),
        make("library-one", changed_output),
    ];
    let mut cache = ExplorerPreviews::default();
    let ctx = egui::Context::default();
    let texture = ctx.load_texture(
        "cached-original",
        egui::ColorImage::filled([2, 2], egui::Color32::RED),
        egui::TextureOptions::LINEAR,
    );
    cache.entries.insert(
        original.key(),
        Entry {
            texture: Some(texture),
            error: None,
            bytes: 16,
            touched: 0,
        },
    );
    assert!(cache.request(original.clone()).is_some());
    for request in alternatives {
        assert_ne!(original.key(), request.key());
        assert!(
            cache.request(request).is_none(),
            "a matching ID alone reused the wrong saved photograph"
        );
    }
    assert_eq!(cache.queue.len(), 3, "all identity alternatives must miss");
}

#[test]
fn queued_versions_do_not_keep_closed_documents_pixel_buffers_alive() {
    let full = image();
    let preview = image();
    let weak_full = Arc::downgrade(&full);
    let weak_preview = Arc::downgrade(&preview);
    let mut cache = ExplorerPreviews::default();
    cache.set_current(
        Some(Path::new("fixture/result.tiff")),
        Some(&full),
        Some(&preview),
    );
    cache.request(Request::Version {
        root: "library-one".into(),
        version: Box::new(version()),
        image: Arc::downgrade(&preview),
    });
    cache.request(file(0));
    assert_eq!(cache.queue.len(), 2);
    drop(full);
    drop(preview);
    assert!(
        weak_full.upgrade().is_none(),
        "cache retained full source pixels"
    );
    assert!(
        weak_preview.upgrade().is_some(),
        "open document needs its small preview"
    );
    cache.set_current(None, None, None);
    assert!(
        weak_preview.upgrade().is_none(),
        "queued old versions retained a closed document's preview"
    );
    assert_eq!(cache.queue.len(), 1);
    assert!(matches!(&cache.queue[0].0, Request::File { .. }));
}

#[test]
fn oversized_visible_working_set_stabilizes_and_scroll_admits_new_rows() {
    let mut cache = ExplorerPreviews::default();
    let visible = MAX_ENTRIES + 23;
    for row in 0..visible {
        cache.request(file(row));
    }
    assert_eq!(cache.queue.len(), MAX_ENTRIES);
    // Model completed maximum-size decodes. The test exercises actual request
    // admission, not codec timing; author controls cover real worker publication.
    for (request, _) in cache.queue.drain(..) {
        cache.entries.insert(
            request.key(),
            Entry {
                texture: None,
                error: None,
                bytes: SIDE as usize * SIDE as usize * 4,
                touched: cache.clock,
            },
        );
    }
    let original_keys: Vec<_> = cache.entries.keys().cloned().collect();
    for _ in 0..12 {
        cache.clock += 1;
        for row in 0..visible {
            cache.request(file(row));
        }
        assert!(
            cache.queue.is_empty(),
            "unchanged oversubscribed tree requeued decodes"
        );
        assert_eq!(
            cache.entries.keys().cloned().collect::<Vec<_>>(),
            original_keys
        );
        assert!(
            cache
                .entries
                .values()
                .map(|entry| entry.bytes)
                .sum::<usize>()
                <= MAX_BYTES
        );
    }
    // A real viewport change must still make progress; blanket refusal would
    // pass the no-churn assertion but fail this independent positive arm.
    cache.clock += 1;
    for row in 100..100 + visible {
        cache.request(file(row));
    }
    assert_eq!(cache.queue.len(), MAX_ENTRIES);
    assert!(cache.entries.is_empty());
    assert!(
        cache
            .queue
            .iter()
            .all(|(request, _)| !original_keys.contains(&request.key()))
    );
}
