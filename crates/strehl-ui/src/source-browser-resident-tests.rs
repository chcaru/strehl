use super::*;

#[test]
fn eviction_preserves_the_presented_canonical_photo_without_claiming_cache_residency() {
    let mut h = Harness::new(130);
    h.browser
        .scrubs
        .insert(0, cache_image(&h.ctx, image(0), Kind::Scrub));
    h.select(0);
    let texture = h.viewer.texture.as_ref().unwrap().id();
    let aperture = h.viewer.source_size;
    h.browser.scrubs.clear();
    h.select(0);
    assert_eq!(h.browser.displayed, Some((0, Kind::Scrub)));
    assert_eq!(h.viewer.texture.as_ref().unwrap().id(), texture);
    assert_eq!(h.viewer.source_size, aperture);
    assert!(h.browser.texture_snapshot(0).is_none());
    h.select(1);
    assert_eq!(h.browser.displayed_index(), Some(0));
    assert!(
        h.browser.pending(),
        "held pixels must not be relabelled as the next source"
    );
    assert_eq!(h.viewer.texture.as_ref().unwrap().id(), texture);
}

#[test]
fn warmed_stacks_up_to_512_scrub_every_capture_without_new_work_or_texture_uploads() {
    for count in [130, 299, 512] {
        assert_resident_stack_scrubs_without_work(count);
    }
}

fn assert_resident_stack_scrubs_without_work(count: usize) {
    let mut h = Harness::new(count);
    h.select(0);
    h.now += SCRUB_IDLE;
    h.tick();
    let mut deliveries = 0;
    while h.has_pending() {
        h.deliver_image();
        deliveries += 1;
        assert!(
            deliveries < 400,
            "resident warming must terminate, never decode/evict itself"
        );
    }
    assert_eq!(h.browser.scrubs.len(), count);
    assert_eq!(
        h.browser.thumbs.len(),
        count,
        "missing contacts receive bounded derivatives"
    );
    for index in 0..count {
        assert_eq!(
            h.started
                .borrow()
                .iter()
                .filter(|&&(i, kind)| i == index && kind == Kind::Scrub)
                .count(),
            1
        );
    }
    let issued = h.started.borrow().len();
    let allocated = h.ctx.tex_manager().read().num_allocated();
    let identities: Vec<_> = (0..count)
        .map(|i| h.browser.texture_snapshot(i).unwrap().1.id())
        .collect();
    let contacts: Vec<_> = (0..count)
        .map(|i| h.browser.native_thumbnail(i).unwrap().id())
        .collect();
    let _ = h.ctx.run(egui::RawInput::default(), |_| {});
    for index in (0..count).chain((0..count).rev()) {
        h.select(index);
        let ctx = h.ctx.clone();
        let output = ctx.run(egui::RawInput::default(), |_| h.tick());
        assert_eq!(h.browser.displayed_index(), Some(index));
        assert!(!h.browser.pending());
        assert_eq!(h.viewer.texture.as_ref().unwrap().id(), identities[index]);
        assert_eq!(h.viewer.source_size, image(index).source_size);
        assert_eq!(
            h.browser.native_thumbnail(index).unwrap().id(),
            contacts[index]
        );
        assert!(
            output.textures_delta.set.is_empty(),
            "warm scrubbing must not upload any tier"
        );
        assert_eq!(
            h.started.borrow().len(),
            issued,
            "warm scrub must not issue background work"
        );
        assert_eq!(h.ctx.tex_manager().read().num_allocated(), allocated);
    }
    // Remove the resident layer alone: distant frames outside the measured
    // refinement window really are cold. This witnesses the failure this
    // coverage protects against, rather than asserting a cache against itself.
    h.browser.scrubs.clear();
    h.select(90);
    h.tick();
    assert!(h.browser.pending());
    assert!(h.started.borrow().len() > issued);
    assert!(h.browser.texture_snapshot(90).is_none());
}

fn square(index: usize, side: usize) -> PreviewImage {
    PreviewImage {
        path: PathBuf::from(index.to_string()),
        source_size: [7008, 7008],
        size: [side, side],
        rgba: [index as u8, 123, 74, 255].repeat(side * side),
        is_overview: true,
    }
}

#[test]
fn actual_square_uploads_are_paced_and_foreground_wins_without_replacing_native_contacts() {
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser {
        requested: Some(0),
        ..Default::default()
    };
    browser
        .thumbs
        .insert(0, cache_image(&ctx, image(0), Kind::Thumbnail));
    let native = browser.native_thumbnail(0).unwrap().id();
    // Consume the initial native contact allocation separately.
    let _ = ctx.run(egui::RawInput::default(), |_| {});
    for index in [1, 2, 0] {
        browser.scrub_pending.push_back((
            index,
            SourcePreview {
                image: square(index, SCRUB_SIDE as usize),
                thumbnail: Some(square(index, THUMB_SIDE as usize)),
            },
        ));
    }
    for (turn, expected) in [0, 1, 2].into_iter().enumerate() {
        let output = ctx.run(egui::RawInput::default(), |ctx| {
            browser.upload_scrubs(ctx, 0, 130);
        });
        let uploaded: usize = output
            .textures_delta
            .set
            .iter()
            .map(|(_, image)| image.image.size().into_iter().product::<usize>() * 4)
            .sum();
        assert!(
            uploaded > 0 && uploaded <= SCRUB_UPLOAD_BYTES,
            "actual egui uploads must stay within this turn's budget"
        );
        assert_eq!(browser.scrubs.len(), turn + 1);
        assert!(browser.scrubs.contains_key(&expected));
        assert_eq!(browser.native_thumbnail(0).unwrap().id(), native);
        assert_eq!(browser.texture_snapshot(expected).unwrap().2, [7008, 7008]);
    }
    assert!(browser.scrub_pending.is_empty());
}

#[test]
fn cold_foreground_retires_warming_lane_and_import_discards_queued_pixels() {
    let mut h = Harness::new(300);
    for index in 0..300 {
        h.browser
            .thumbs
            .insert(index, cache_image(&h.ctx, image(index), Kind::Thumbnail));
    }
    for index in 0..5 {
        h.browser
            .overviews
            .insert(index, cache_image(&h.ctx, image(index), Kind::Overview));
    }
    for index in 0..2 {
        h.browser
            .images
            .insert(index, cache_image(&h.ctx, image(index), Kind::Image));
    }
    h.select(0);
    h.now += SCRUB_IDLE;
    h.tick();
    assert_eq!(h.film_pending[0].kind, Kind::Scrub);
    assert_eq!(h.film_pending[0].indices, [0, 1, 2, 3]);
    assert!(h.pending.is_empty());
    h.select(250);
    h.tick();
    assert!(h.browser.film_work.as_ref().unwrap().task.is_cancelled());
    assert_eq!(h.pending.len(), 1);
    assert_eq!(
        (h.pending[0].index, h.pending[0].kind),
        (250, Kind::Overview)
    );
    h.deliver_film_images();
    assert!(
        h.browser.scrubs.is_empty(),
        "cancelled batch must never upload"
    );
    assert!(h.browser.errors.is_empty());
    h.browser.scrub_pending.push_back((250, bundle(image(250))));
    h.browser.reset(1);
    h.browser.upload_scrubs(&h.ctx, 250, 300);
    assert!(h.browser.scrub_pending.is_empty() && h.browser.scrubs.is_empty());
}

#[test]
fn resident_resolution_covers_realistic_stack_lengths_under_a_square_byte_bound() {
    for count in [1, 12, 130, 299, 300, 512, 10_000] {
        let side = scrub_side(count) as usize;
        assert!((256..=640).contains(&side));
        assert!(count.min(SCRUB_COUNT) * side * side * 4 <= SCRUB_BYTES);
        assert!(
            side * side * 4 + THUMB_SIDE as usize * THUMB_SIDE as usize * 4 <= SCRUB_UPLOAD_BYTES
        );
    }
    assert!(
        scrub_side(130) > scrub_side(300),
        "the fixture must exercise adaptation"
    );
    let mut browser = SourceBrowser {
        requested: Some(9999),
        ..Default::default()
    };
    assert_eq!(browser.scrub_range(10_000), 9488..10_000);
    browser.requested = Some(0);
    assert_eq!(browser.scrub_range(10_000), 0..512);
}

#[test]
fn canonical_inspection_survives_native_contact_eviction_beyond_512_sources() {
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser {
        requested: Some(0),
        ..Default::default()
    };
    for index in 0..600 {
        browser
            .thumbs
            .insert(index, cache_image(&ctx, image(index), Kind::Thumbnail));
    }
    let canonical: Vec<_> = (0..300).chain(std::iter::once(599)).collect();
    for &index in &canonical {
        browser
            .scrubs
            .insert(index, cache_image(&ctx, image(index), Kind::Scrub));
    }
    let last = browser.texture_snapshot(599).unwrap();
    browser.trim();
    assert!(
        browser.native_thumbnail(599).is_none(),
        "fixture must really evict the native contact"
    );
    assert!(!browser.thumbnail_indices().contains(&599));
    assert_eq!(browser.canonical_indices(), canonical);
    assert_eq!(browser.texture_snapshot(599).unwrap().1.id(), last.1.id());
    browser
        .overviews
        .insert(599, cache_image(&ctx, image(599), Kind::Overview));
    assert_eq!(
        browser.canonical_indices().len(),
        301,
        "higher tiers cannot duplicate source identities"
    );
}

#[test]
fn repeated_selection_checks_viewer_identity_and_accepts_new_quality() {
    let mut h = Harness::new(2);
    h.browser
        .scrubs
        .insert(0, cache_image(&h.ctx, square(0, 8), Kind::Scrub));
    h.select(0);
    let scrub = h.viewer.texture.as_ref().unwrap().clone();
    assert!(h.viewer.has_source(&scrub, (0, 0)));
    // A result/draft can use the same texture handle while clearing its source
    // identity. Comparing only IDs would prevent the browser from reclaiming it.
    h.viewer.install(&scrub, [7008, 7008], true);
    assert!(!h.viewer.has_source(&scrub, (0, 0)));
    h.select(0);
    assert!(h.viewer.has_source(&scrub, (0, 0)));

    h.browser
        .overviews
        .insert(0, cache_image(&h.ctx, square(0, 16), Kind::Overview));
    h.select(0);
    let overview = h.viewer.texture.as_ref().unwrap().clone();
    assert_ne!(overview.id(), scrub.id());
    assert!(h.viewer.has_source(&overview, (0, 0)));
    assert!(
        h.viewer.transitioning(),
        "same-capture refinement still reveals"
    );
    h.select(0);
    assert!(h.viewer.transitioning());

    h.viewer = Viewer::default();
    h.select(0);
    assert!(h.viewer.has_source(&overview, (0, 0)));
    h.viewer
        .install_source(&overview, [7008, 7008], true, (1, 0));
    assert!(!h.viewer.has_source(&overview, (0, 0)));
    h.select(0);
    assert!(h.viewer.has_source(&overview, (0, 0)));
    assert!(
        !h.viewer.transitioning(),
        "different imports must never blend"
    );
}

#[test]
fn thumbnail_capacity_keeps_512_squares_but_enforces_count_and_byte_caps() {
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser {
        requested: Some(0),
        ..Default::default()
    };
    for index in 0..512 {
        let mut cached = cache_image(&ctx, image(index), Kind::Thumbnail);
        // Charge production's actual worst-case square bytes with tiny GPU
        // fixtures; this is a budget test, not a memory or timing measurement.
        cached.bytes = 240 * 240 * 4;
        browser.thumbs.insert(index, cached);
    }
    browser.trim();
    assert_eq!(browser.thumbs.len(), 512);
    assert_eq!(
        browser
            .thumbs
            .values()
            .map(|image| image.bytes)
            .sum::<usize>(),
        117_964_800
    );
    browser
        .thumbs
        .insert(512, cache_image(&ctx, image(512), Kind::Thumbnail));
    browser.trim();
    assert_eq!(
        browser.thumbs.len(),
        512,
        "count eviction must really occur"
    );
    for cached in browser.thumbs.values_mut() {
        cached.bytes = 1024 * 1024;
    }
    browser.trim();
    assert_eq!(
        browser.thumbs.len(),
        128,
        "byte eviction must work below the count cap"
    );
    assert!(browser.thumbs.contains_key(&0));
}

#[test]
fn resident_shortcuts_require_the_complete_range_and_follow_large_stack_windows() {
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser {
        requested: Some(0),
        ..Default::default()
    };
    for index in 0..512 {
        browser
            .scrubs
            .insert(index, cache_image(&ctx, image(index), Kind::Scrub));
    }
    assert!(cache_covers_range(&browser.scrubs, &(0..512)));
    assert!(!cache_covers_range(&browser.scrubs, &(1..513)));
    assert!(browser.next_scrubs(512).is_empty());
    assert!(!browser.upload_scrubs(&ctx, 0, 600));
    assert_eq!(browser.scrub_window, 0..512);
    browser.requested = Some(599);
    assert!(!browser.upload_scrubs(&ctx, 599, 600));
    assert_eq!(browser.scrub_window, 88..600);
    assert_eq!(browser.scrubs.len(), 424);
    assert!(!browser.scrubs.contains_key(&0));
    assert_eq!(browser.next_scrubs(600).first(), Some(&599));
    browser.scrub_pending.push_back((0, bundle(image(0))));
    browser.upload_scrubs(&ctx, 599, 600);
    assert!(browser.scrub_pending.is_empty());
    assert!(!browser.scrubs.contains_key(&0));
    browser.reset(1);
    assert_eq!(browser.scrub_window, 0..0);
}

#[test]
fn old_scrub_batch_failures_are_discarded_after_the_resident_window_moves() {
    let mut h = Harness::new(600);
    for index in 0..41 {
        h.browser
            .thumbs
            .insert(index, cache_image(&h.ctx, image(index), Kind::Thumbnail));
    }
    for index in (0..5).chain(std::iter::once(599)) {
        h.browser
            .overviews
            .insert(index, cache_image(&h.ctx, image(index), Kind::Overview));
    }
    for index in 0..2 {
        h.browser
            .images
            .insert(index, cache_image(&h.ctx, image(index), Kind::Image));
    }
    h.select(0);
    h.now += SCRUB_IDLE;
    h.tick();
    assert_eq!(h.film_pending[0].kind, Kind::Scrub);
    assert_eq!(h.film_pending[0].indices, [0, 1, 2, 3]);
    h.select(599);
    h.tick();
    assert_eq!(h.browser.scrub_window, 88..600);
    assert!(
        !h.browser.film_work.as_ref().unwrap().task.is_cancelled(),
        "the cached foreground must let the old scrub batch finish"
    );
    h.deliver_film(Err("late independent corrupt samples".into()));
    assert!(
        h.browser.scrub_failures.is_empty(),
        "late failures outside the stable current window must not remain"
    );
    assert!((0..4).all(|index| h.browser.missing(index, Kind::Scrub)));
}

#[test]
fn more_corrupt_sources_than_the_foreground_error_log_can_hold_still_settle() {
    let mut h = Harness::new(300);
    for index in 0..300 {
        h.browser
            .thumbs
            .insert(index, cache_image(&h.ctx, image(index), Kind::Thumbnail));
    }
    h.select(0);
    h.now += SCRUB_IDLE;
    h.tick();
    let mut deliveries = 0;
    while h.has_pending() {
        if !h.pending.is_empty() {
            h.deliver(Err("independent corrupt camera fixture".into()));
        } else {
            h.deliver_film(Err("independent corrupt camera fixture".into()));
        }
        deliveries += 1;
        assert!(
            deliveries < 400,
            "failed resident samples must not cycle through the error log"
        );
    }
    assert_eq!(h.browser.scrub_failures.len(), 300);
    assert!(
        h.browser.scrub_failures.len() > ERROR_COUNT,
        "the old log cap must be exceeded"
    );
    assert!(h.browser.scrubs.is_empty());
    let requests = h.started.borrow().len();
    for _ in 0..12 {
        h.tick();
    }
    assert_eq!(h.started.borrow().len(), requests);
    assert!(!h.browser.active());
    h.browser.reset(1);
    assert!(
        h.browser.scrub_failures.is_empty(),
        "fresh import can retry the source files"
    );
}
