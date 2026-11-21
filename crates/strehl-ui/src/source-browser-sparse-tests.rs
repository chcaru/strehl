//! Studio 2 P3: the stack-wide sparse tier and large-tier upload pacing.
use super::*;

fn warm_sparse(h: &mut Harness) {
    let count = h.frames.len();
    let slots = count.div_ceil(SourceBrowser::sparse_stride(count).unwrap());
    let mut deliveries = 0;
    loop {
        h.tick();
        if h.browser.sparse.len() == slots && h.browser.sparse_pending.is_empty() {
            break;
        }
        if h.has_pending() {
            // Contacts and the selection's overview come first, then sparse.
            h.deliver_image();
            deliveries += 1;
        }
        assert!(deliveries < 600, "the sparse tier must finish, never cycle");
    }
}

#[test]
fn short_stacks_have_no_sparse_tier() {
    for count in [1, 130, 299, 512] {
        assert_eq!(SourceBrowser::sparse_stride(count), None);
        let mut h = Harness::new(count);
        h.select(0);
        h.tick();
        assert!(h.browser.next_sparse(count).is_empty());
        assert!(
            h.film_pending
                .iter()
                .all(|pending| pending.kind != Kind::Sparse)
        );
    }
    assert_eq!(SourceBrowser::sparse_stride(1_444), Some(3));
    assert_eq!(SourceBrowser::sparse_stride(6_000), Some(12));
}

#[test]
fn a_cold_sweep_of_1444_planes_always_shows_the_plane_or_its_nearest_resident_neighbour() {
    let count = 1_444;
    let stride = SourceBrowser::sparse_stride(count).unwrap();
    let mut h = Harness::new(count);
    h.select(700);
    warm_sparse(&mut h);
    let slots = count.div_ceil(stride);
    assert_eq!(
        h.browser.sparse.len(),
        slots,
        "resident from open, every k-th plane"
    );
    assert!(
        h.browser
            .sparse
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= SPARSE_BYTES
    );
    // Nothing else is resident: every step of the sweep is cold.
    h.browser.scrubs.clear();
    h.browser.overviews.clear();
    h.browser.images.clear();
    let ctx = h.ctx.clone();
    let _ = ctx.run(egui::RawInput::default(), |_| {});
    let mut worst = 0;
    for index in (0..count).chain((0..count).rev()) {
        h.select(index);
        let output = ctx.run(egui::RawInput::default(), |_| h.tick());
        let shown = h
            .browser
            .displayed_index()
            .expect("a picture is always on screen");
        let distance = shown.abs_diff(index);
        worst = worst.max(distance);
        assert!(
            distance <= stride / 2 + 1,
            "plane {index} showed {shown}, farther than its nearest resident neighbour"
        );
        assert_eq!(
            h.browser.pending(),
            shown != index,
            "a stand-in is named as such: the request stays pending"
        );
        assert!(
            output.textures_delta.set.is_empty(),
            "a resident stand-in uploads nothing"
        );
        if shown == index {
            assert!(matches!(h.browser.displayed, Some((_, Kind::Sparse))));
        }
    }
    assert!(worst >= 1, "the fixture must actually exercise stand-ins");
    // A stand-in is never closer-looking than the real plane: when the
    // request's own tier arrives it replaces the neighbour.
    h.select(301);
    h.tick();
    assert_ne!(h.browser.displayed_index(), Some(301));
    h.browser
        .scrubs
        .insert(301, cache_image(&h.ctx, image(301), Kind::Scrub));
    h.select(301);
    assert_eq!(h.browser.displayed, Some((301, Kind::Scrub)));
    assert!(!h.browser.pending());
    // The plane's own sparse picture is exact identity for inspection.
    let own = (0..count).step_by(stride).nth(50).unwrap();
    assert!(h.browser.texture_snapshot(own).is_some());
    assert_eq!(
        h.browser
            .nearest_resident(own + 1)
            .map(|(index, _, _)| index),
        Some(own)
    );
}

#[test]
fn a_sparse_stand_in_never_replaces_a_closer_picture() {
    let count = 1_500;
    let mut h = Harness::new(count);
    h.select(0);
    warm_sparse(&mut h);
    h.browser.scrubs.clear();
    h.browser
        .scrubs
        .insert(100, cache_image(&h.ctx, image(100), Kind::Scrub));
    h.select(100);
    assert_eq!(h.browser.displayed, Some((100, Kind::Scrub)));
    // 101 is cold; the nearest sparse plane (99 or 102) is not closer than 100.
    h.select(101);
    assert_eq!(h.browser.displayed_index(), Some(100));
    h.select(104);
    let shown = h.browser.displayed_index().unwrap();
    assert!(
        shown.abs_diff(104) < 4,
        "a closer stand-in replaces a distant picture"
    );
}

#[test]
fn a_large_tier_uploads_alone_and_scrubs_wait_for_the_next_poll() {
    let mut h = Harness::new(130);
    h.select(5);
    h.now += SETTLE;
    let ctx = h.ctx.clone();
    let _ = ctx.run(egui::RawInput::default(), |_| {});
    // Three small resident-tier images are ready to upload.
    for index in 10..13 {
        h.browser
            .scrub_pending
            .push_back((index, bundle(image(index))));
    }
    // A large detail decode, prepared on its worker, completes now.
    let mut detail = bundle(square(5, 1_200));
    detail.thumbnail = None;
    let color = crate::source_preview::texels(&mut detail.image);
    let (done, finished) = std::sync::mpsc::sync_channel(1);
    h.browser.work = Some(Work {
        epoch: h.epoch,
        index: 5,
        kind: Kind::Image,
        task: jobs::spawn_task("large-detail-fixture", move |_| {
            done.send(()).ok();
            Ok(DetailPreview {
                preview: detail,
                color: Some(color),
            })
        }),
    });
    // The result is published right after the closure returns.
    finished.recv().unwrap();
    std::thread::sleep(Duration::from_millis(50));
    let deadline = Instant::now() + Duration::from_secs(3);
    let mut first = None;
    while first.is_none() {
        let output = ctx.run(egui::RawInput::default(), |_| h.tick());
        if !output.textures_delta.set.is_empty() {
            first = Some(output);
        }
        assert!(
            Instant::now() < deadline,
            "the detail fixture did not return"
        );
        std::thread::yield_now();
    }
    let first = first.unwrap();
    let sizes: Vec<usize> = first
        .textures_delta
        .set
        .iter()
        .map(|(_, delta)| delta.image.size().into_iter().product::<usize>() * 4)
        .collect();
    assert!(
        sizes.iter().any(|&bytes| bytes >= 1_200 * 1_200 * 4),
        "the large image uploads first: {sizes:?}"
    );
    assert_eq!(
        sizes.len(),
        1,
        "nothing shares the large upload's poll: {sizes:?}"
    );
    assert_eq!(
        h.browser.scrub_pending.len(),
        3,
        "scrubs wait for the next poll"
    );
    assert!(h.browser.has_image(5));
    let next = ctx.run(egui::RawInput::default(), |_| h.tick());
    assert!(!next.textures_delta.set.is_empty());
    assert!(
        h.browser.scrub_pending.len() < 3,
        "then the scrub tier resumes"
    );
}

fn square(index: usize, side: usize) -> PreviewImage {
    PreviewImage {
        path: PathBuf::from(index.to_string()),
        source_size: [7008, 7008],
        size: [side, side],
        rgba: [index as u8, 50, 90, 255].repeat(side * side),
        is_overview: true,
    }
}

#[test]
fn a_sweep_from_open_warms_the_sparse_tier_around_the_pointer_and_shows_stand_ins() {
    let count = 1_444;
    let mut h = Harness::new(count);
    let mut shown = 0;
    let mut sparse_batches = 0;
    for step in 0..400 {
        // A pointer moving four planes per poll, never settling.
        h.select((step * 4) % count);
        h.tick();
        if let Some(pending) = h.film_pending.first() {
            if pending.kind == Kind::Sparse {
                // Its first batch is the pointer's neighbourhood; later ones
                // fill the nearest slots still missing, wherever they are.
                if sparse_batches == 0 {
                    assert!(
                        pending
                            .indices
                            .iter()
                            .all(|&index| index.abs_diff(h.selected) <= 48),
                        "the sparse tier warms around the pointer first"
                    );
                }
                sparse_batches += 1;
            }
            h.deliver_film_images();
        }
        h.tick();
        shown += usize::from(h.browser.displayed_index().is_some());
        assert!(
            h.browser
                .film_work
                .as_ref()
                .is_none_or(|work| !work.task.is_cancelled()),
            "a sparse batch is never cancelled by a moving cold pointer"
        );
    }
    assert!(sparse_batches > 0);
    assert!(
        shown >= 390,
        "after its first batch a cold sweep shows a picture: {shown} of 400"
    );
}
