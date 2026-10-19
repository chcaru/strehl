use super::*;
use crate::jobs;
use std::cell::RefCell;
use std::sync::mpsc::{self, SyncSender};

#[path = "source-browser-v23-review-tests.rs"]
mod v23_review_tests;

#[path = "source-browser-v24-tests.rs"]
mod v24_tests;

#[path = "source-browser-v24-review-tests.rs"]
mod v24_review_tests;

#[path = "source-browser-v25-tests.rs"]
mod v25_tests;

#[path = "source-browser-v26-tests.rs"]
mod v26_tests;

struct Pending {
    index: usize,
    side: u32,
    kind: Kind,
    thumbnail: bool,
    send: SyncSender<Result<PreviewImage, String>>,
}

struct PendingFilm {
    indices: Vec<usize>,
    kind: Kind,
    side: u32,
    thumbnail: bool,
    send: SyncSender<Result<FilmstripBatch, String>>,
}

struct Harness {
    browser: SourceBrowser,
    viewer: Viewer,
    ctx: egui::Context,
    frames: Vec<FrameFile>,
    visible: Vec<usize>,
    selected: usize,
    epoch: u64,
    now: Instant,
    pending: Vec<Pending>,
    film_pending: Vec<PendingFilm>,
    started: RefCell<Vec<(usize, Kind)>>,
    derivatives: RefCell<Vec<(usize, Kind, bool)>>,
}

impl Harness {
    fn new(count: usize) -> Self {
        Self {
            browser: SourceBrowser::default(),
            viewer: Viewer::default(),
            ctx: egui::Context::default(),
            frames: (0..count)
                .map(|index| FrameFile {
                    path: PathBuf::from(index.to_string()),
                    bytes: 0,
                })
                .collect(),
            visible: Vec::new(),
            selected: 0,
            epoch: 0,
            now: Instant::now(),
            pending: Vec::new(),
            film_pending: Vec::new(),
            started: RefCell::new(Vec::new()),
            derivatives: RefCell::new(Vec::new()),
        }
    }

    fn tick(&mut self) {
        self.browser.poll_with(
            &self.ctx,
            self.epoch,
            self.selected,
            &self.frames,
            &self.visible,
            8_192,
            &mut self.viewer,
            self.now,
            |path, side, kind, thumbnail| {
                let index = path.to_string_lossy().parse().unwrap();
                self.started.borrow_mut().push((index, kind));
                self.derivatives.borrow_mut().push((index, kind, thumbnail));
                let (send, receive) = mpsc::sync_channel(1);
                self.pending.push(Pending {
                    index,
                    side,
                    kind,
                    thumbnail,
                    send,
                });
                jobs::spawn_task("preview-scheduler-test", move |_| {
                    receive
                        .recv()
                        .map_err(|_| anyhow::anyhow!("fixture released decoder"))?
                        .map(|image| {
                            let mut preview = bundle(image);
                            if !thumbnail {
                                preview.thumbnail = None;
                            }
                            preview
                        })
                        .map_err(anyhow::Error::msg)
                })
            },
            |paths, side, kind, thumbnail| {
                let indices: Vec<_> = paths.iter().map(|(index, _)| *index).collect();
                self.started
                    .borrow_mut()
                    .extend(indices.iter().map(|&index| (index, kind)));
                self.derivatives
                    .borrow_mut()
                    .extend(indices.iter().map(|&index| (index, kind, thumbnail)));
                let (send, receive) = mpsc::sync_channel(1);
                self.film_pending.push(PendingFilm {
                    indices,
                    kind,
                    side,
                    thumbnail,
                    send,
                });
                jobs::spawn_task("filmstrip-scheduler-test", move |_| {
                    receive
                        .recv()
                        .map_err(|_| anyhow::anyhow!("fixture released filmstrip decoder"))?
                        .map_err(anyhow::Error::msg)
                })
            },
        );
    }

    fn select(&mut self, index: usize) {
        self.selected = index;
        self.now += Duration::from_millis(2);
        self.browser.select_at(index, &mut self.viewer, self.now);
    }

    fn deliver(&mut self, result: Result<PreviewImage, String>) {
        let pending = self.pending.remove(0);
        let epoch = self.browser.work.as_ref().unwrap().epoch;
        pending.send.send(result).unwrap();
        let deadline = Instant::now() + Duration::from_secs(3);
        while self.browser.work.as_ref().is_some_and(|work| {
            work.epoch == epoch && work.index == pending.index && work.kind == pending.kind
        }) {
            self.tick();
            assert!(Instant::now() < deadline, "fixture decoder did not return");
            std::thread::yield_now();
        }
    }

    fn deliver_film(&mut self, result: Result<FilmstripBatch, String>) -> usize {
        let pending = self.film_pending.remove(0);
        let count = pending.indices.len();
        let epoch = self.browser.film_work.as_ref().unwrap().epoch;
        pending.send.send(result).unwrap();
        let deadline = Instant::now() + Duration::from_secs(3);
        while self.browser.film_work.as_ref().is_some_and(|work| {
            work.epoch == epoch && work.indices == pending.indices && work.kind == pending.kind
        }) {
            self.tick();
            assert!(
                Instant::now() < deadline,
                "fixture filmstrip decoder did not return"
            );
            std::thread::yield_now();
        }
        count
    }

    fn deliver_film_images(&mut self) -> usize {
        let pending = &self.film_pending[0];
        let images = pending
            .indices
            .iter()
            .map(|&index| {
                (
                    index,
                    Ok(if matches!(pending.kind, Kind::Overview | Kind::Scrub) {
                        let mut preview = bundle(image(index));
                        if !pending.thumbnail {
                            preview.thumbnail = None;
                        }
                        preview
                    } else {
                        SourcePreview {
                            image: image(index),
                            thumbnail: None,
                        }
                    }),
                )
            })
            .collect();
        self.deliver_film(Ok(images))
    }

    fn deliver_image(&mut self) -> usize {
        if let Some(pending) = self.pending.first() {
            let index = pending.index;
            self.deliver(Ok(image(index)));
            1
        } else {
            self.deliver_film_images()
        }
    }

    fn has_pending(&self) -> bool {
        !self.pending.is_empty() || !self.film_pending.is_empty()
    }
}

fn bundle(image: PreviewImage) -> SourcePreview {
    let thumbnail = PreviewImage {
        path: image.path.clone(),
        source_size: image.source_size,
        size: image.size,
        rgba: image.rgba.clone(),
        is_overview: true,
    };
    SourcePreview {
        image,
        thumbnail: Some(thumbnail),
    }
}

fn image(index: usize) -> PreviewImage {
    PreviewImage {
        path: PathBuf::from(index.to_string()),
        source_size: [2, 1],
        size: [2, 1],
        rgba: vec![index as u8, 12, 38, 255, 43, index as u8, 22, 255],
        is_overview: false,
    }
}

#[test]
fn rapid_reversals_retain_display_and_start_only_the_latest_request() {
    // Fails if a miss clears the Viewer, if old work replaces the newest
    // identity, or if every pointer movement starts another decoder.
    let mut harness = Harness::new(100);
    harness.tick();
    harness.deliver_image();
    let first = harness.viewer.texture.as_ref().unwrap().id();
    assert_eq!(harness.browser.displayed_index(), Some(0));
    assert_eq!(harness.pending.len(), 1);
    let in_flight = harness.pending[0].index;
    assert_ne!(in_flight, 79, "fixture must have obsolete work in flight");

    for index in [1, 31, 90, 12, 80, 4, 79] {
        harness.select(index);
        harness.tick();
        assert_eq!(harness.viewer.texture.as_ref().unwrap().id(), first);
        assert_eq!(harness.browser.displayed_index(), Some(0));
        assert!(harness.browser.pending());
        assert_eq!(harness.pending.len(), 1, "a scrub must not fork decoders");
        assert_eq!(
            harness.film_pending.len(),
            1,
            "a scrub must not fork fast workers"
        );
        assert_eq!(harness.pending[0].index, in_flight);
    }
    harness.deliver_film_images(); // Retire the old batch, not the blocked detail decode.
    assert_eq!(harness.film_pending[0].indices, [79]);
    assert_eq!(harness.film_pending[0].kind, Kind::Overview);
    assert_eq!(harness.browser.displayed_index(), Some(0));
    harness.deliver_film_images();
    assert_eq!(harness.browser.displayed_index(), Some(79));
    assert!(!harness.browser.pending());
    assert_ne!(harness.viewer.texture.as_ref().unwrap().id(), first);
    assert_eq!(
        harness.pending[0].index, in_flight,
        "latest overview does not wait for obsolete detail work"
    );
    harness.deliver_image();
    assert_eq!(
        harness.browser.displayed_index(),
        Some(79),
        "late detail cannot overwrite latest selection"
    );
}

#[test]
fn cached_small_capture_is_immediate_and_full_refinement_keeps_camera_position() {
    let mut harness = Harness::new(20);
    harness
        .browser
        .overviews
        .insert(9, cache_image(&harness.ctx, image(9), Kind::Overview));
    harness.viewer.fit = false;
    harness.viewer.zoom = 2.75;
    harness.select(9);
    let thumbnail_id = harness.viewer.texture.as_ref().unwrap().id();
    assert_eq!(harness.browser.displayed_index(), Some(9));
    assert!(harness.browser.refining());
    assert!(
        harness.viewer.overview,
        "tiny JPEG must not advertise native sensor pixels"
    );
    assert!(!harness.viewer.fit);
    assert_eq!(harness.viewer.zoom, 2.75);
    let previous_extent =
        harness.viewer.texture.as_ref().unwrap().size_vec2() * harness.viewer.zoom;
    harness.now += SETTLE;
    harness.tick();
    assert_eq!(harness.pending[0].index, 9);
    assert_eq!(harness.pending[0].side, IMAGE_SIDE);
    harness.deliver(Ok(PreviewImage {
        path: PathBuf::from("9"),
        source_size: [20, 10],
        size: [20, 10],
        rgba: [8, 40, 20, 255].repeat(200),
        is_overview: false,
    }));
    assert_eq!(harness.browser.displayed_index(), Some(9));
    assert!(!harness.browser.refining());
    let refined_extent = harness.viewer.texture.as_ref().unwrap().size_vec2() * harness.viewer.zoom;
    assert!((refined_extent - previous_extent).length() < 1e-5);
    assert!(!harness.viewer.fit);
    assert!((harness.viewer.zoom - 0.275).abs() < 1e-5);
    assert_ne!(harness.viewer.texture.as_ref().unwrap().id(), thumbnail_id);
}

#[test]
fn decode_failures_keep_visible_identity_and_do_not_poison_other_frames() {
    let mut harness = Harness::new(30);
    harness
        .browser
        .images
        .insert(0, cache_image(&harness.ctx, image(0), Kind::Image));
    harness.select(0);
    let displayed = harness.viewer.texture.as_ref().unwrap().id();
    harness.select(8);
    harness.tick();
    harness.deliver(Err("small preview damaged".into()));
    assert_eq!(harness.pending[0].index, 8);
    assert_eq!(
        harness.pending[0].side, IMAGE_SIDE,
        "full fallback must be attempted"
    );
    harness.deliver(Err("camera JPEG damaged".into()));
    assert_eq!(harness.browser.displayed_index(), Some(0));
    assert_eq!(harness.viewer.texture.as_ref().unwrap().id(), displayed);
    assert!(harness.browser.pending());
    assert_eq!(harness.browser.error(8), Some("camera JPEG damaged"));
    assert!(harness.browser.error(9).is_none());
    harness.select(9);
    harness.deliver_image(); // An old neighbor may already be decoding.
    if harness.browser.displayed_index() != Some(9) {
        assert_eq!(harness.pending[0].index, 9);
        harness.deliver_image();
    }
    assert_eq!(harness.browser.displayed_index(), Some(9));
}

#[test]
fn imports_discard_late_pixels_and_errors_without_overlapping_decoders() {
    for delivery in [Ok(image(0)), Err("old bracket failure".into())] {
        let mut harness = Harness::new(10);
        harness.tick();
        assert!(harness.browser.active());
        harness.epoch = 12;
        harness.browser.reset(harness.epoch);
        harness.frames.clear();
        harness.tick();
        assert_eq!(harness.pending.len(), 1);
        harness.deliver(delivery);
        if !harness.film_pending.is_empty() {
            harness.deliver_film_images();
        }
        assert!(!harness.browser.active());
        assert!(harness.browser.images.is_empty());
        assert!(harness.browser.thumbs.is_empty());
        assert!(harness.browser.overviews.is_empty());
        assert!(harness.browser.errors.is_empty());
        assert!(harness.browser.displayed_index().is_none());
    }
}

#[test]
fn new_populated_import_at_the_same_index_never_accepts_old_pixels_or_errors() {
    for old_delivery in [Ok(image(0)), Err("old bracket decoder failure".into())] {
        let mut harness = Harness::new(10);
        harness.tick();
        harness.epoch = 17;
        harness.browser.reset(harness.epoch);
        harness.viewer = Viewer::default();
        harness.tick();
        assert_eq!(
            harness.pending.len(),
            1,
            "old decoder must remain the sole worker"
        );
        harness.deliver(old_delivery);
        assert_eq!(
            harness.pending.len(),
            1,
            "new bracket must start after old work retires"
        );
        assert_eq!(
            harness.pending[0].index, 0,
            "fixture must reuse the numeric index"
        );
        assert!(harness.viewer.texture.is_none());
        assert!(harness.browser.displayed_index().is_none());
        assert!(harness.browser.thumbs.is_empty());
        assert!(harness.browser.overviews.is_empty());
        assert!(harness.browser.errors.is_empty());
        harness.deliver_image();
        assert_eq!(harness.browser.displayed_index(), Some(0));
        assert!(harness.viewer.texture.is_some());
    }
}

#[test]
fn cache_limits_include_bytes_and_idle_warming_can_finish() {
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser {
        requested: Some(100),
        ..Default::default()
    };
    // Accounting uses deliberately expensive entries, while test textures stay
    // tiny. A count-only cache passes six entries and fails this byte gate.
    for index in 20..220 {
        let mut cached = cache_image(&ctx, image(index), Kind::Image);
        cached.bytes = IMAGE_SIDE as usize * IMAGE_SIDE as usize * 4;
        browser.images.insert(index, cached.clone());
        browser.thumbs.insert(index, cached);
    }
    browser.trim();
    assert!(browser.images.len() <= IMAGE_COUNT);
    assert!(
        browser
            .images
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= IMAGE_BYTES
    );
    assert!(
        browser
            .thumbs
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= THUMB_BYTES
    );
    assert!(browser.images.contains_key(&100));

    let mut harness = Harness::new(200);
    harness.selected = 100;
    harness
        .browser
        .select_at(100, &mut harness.viewer, harness.now);
    harness.now += SETTLE;
    harness.visible = (91..110).collect();
    harness.tick();
    let mut count = 0;
    while harness.has_pending() {
        count += harness.deliver_image();
        assert!(
            count <= 100,
            "idle warming must not decode and evict forever"
        );
    }
    assert!(count > 80, "fixture must exercise broad idle warming");
    assert_eq!(harness.browser.displayed_index(), Some(100));
    assert!(!harness.browser.active());
}

#[test]
fn cache_misses_preserve_displayed_identity_and_directional_neighbors_are_bounded() {
    let mut harness = Harness::new(20_000);
    harness
        .browser
        .images
        .insert(80, cache_image(&harness.ctx, image(80), Kind::Image));
    harness.select(80);
    harness.select(19_999);
    assert_eq!(harness.browser.displayed_index(), Some(80));
    assert!(harness.browser.pending());
    let forward = neighborhood(19_999, 20_000, 1, 40);
    let reverse = neighborhood(0, 20_000, -1, 40);
    assert_eq!(forward.len(), 40);
    assert_eq!(reverse.len(), 40);
    assert!(forward.iter().all(|&index| index < 20_000));
    assert_eq!(neighborhood(100, 200, -1, 2), [99, 101, 98, 102]);
    assert_eq!(neighborhood(100, 200, 1, 2), [101, 99, 102, 98]);
}

#[test]
fn unusually_wide_filmstrip_cannot_create_a_decode_and_evict_loop() {
    // Exceed the normal visible-item budget. Warm only a bounded
    // visible subset, so an adversarial larger viewport cannot compete with
    // trajectory warming indefinitely.
    let mut harness = Harness::new(400);
    harness.selected = 200;
    harness.visible = (0..150).collect();
    harness
        .browser
        .select_at(200, &mut harness.viewer, harness.now);
    harness.now += SETTLE;
    harness.tick();
    let mut count = 0;
    while harness.has_pending() {
        count += harness.deliver_image();
        assert!(count < 200, "working set must reach an idle state");
    }
    assert!(
        count > 100,
        "fixture must warm disjoint visible and trajectory sets"
    );
    assert!(harness.browser.thumbs.len() <= THUMB_COUNT);
    assert!(!harness.browser.active());
}

#[test]
fn maximum_square_preview_bytes_and_disjoint_warming_sets_reach_idle_together() {
    // Independent review requested exercising both adversaries together:
    // distant visible sources and the actual worst-case byte accounting.
    // Tiny textures keep this test cheap; charged bytes match production's
    // largest supported square previews on every consumed delivery.
    let mut harness = Harness::new(400);
    harness.selected = 200;
    harness.visible = (0..150).collect();
    harness
        .browser
        .select_at(200, &mut harness.viewer, harness.now);
    harness.now += SETTLE;
    harness.tick();
    let mut count = 0;
    while harness.has_pending() {
        count += harness.deliver_image();
        for image in harness.browser.images.values_mut() {
            image.bytes = IMAGE_SIDE as usize * IMAGE_SIDE as usize * 4;
        }
        for image in harness.browser.thumbs.values_mut() {
            image.bytes = THUMB_SIDE as usize * THUMB_SIDE as usize * 4;
        }
        for image in harness.browser.overviews.values_mut() {
            image.bytes = OVERVIEW_SIDE as usize * OVERVIEW_SIDE as usize * 4;
        }
        harness.browser.trim();
        assert!(
            count < 200,
            "byte pressure must not restart warming forever"
        );
    }
    assert!(count > 100, "fixture must exercise disjoint warming sets");
    assert_eq!(harness.browser.images.len(), 3);
    assert_eq!(harness.browser.thumbs.len(), 177);
    assert_eq!(harness.browser.overviews.len(), 9);
    assert!(
        harness
            .browser
            .overviews
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= OVERVIEW_BYTES
    );
    assert!(
        harness
            .browser
            .images
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= IMAGE_BYTES
    );
    assert!(
        harness
            .browser
            .thumbs
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= THUMB_BYTES
    );
    assert!(!harness.browser.active());
}

#[test]
fn a_four_capture_scrub_and_reverse_use_warm_canonical_pixels_without_a_display_gap() {
    let mut harness = Harness::new(200);
    harness.select(100);
    harness.now += SETTLE;
    harness.tick();
    let mut delivered = 0;
    while harness.has_pending() {
        delivered += harness.deliver_image();
        assert!(
            delivered < 130,
            "predictive warming must reach idle without evict/redecode churn"
        );
    }
    let starts = harness.started.borrow().len();
    let texture = harness
        .browser
        .texture_snapshot(104)
        .expect("the forward fourth capture must have its own canonical overview")
        .1
        .id();
    harness.select(104);
    assert_eq!(harness.browser.displayed_index(), Some(104));
    assert!(!harness.browser.pending());
    assert_eq!(harness.viewer.texture.as_ref().unwrap().id(), texture);
    harness.select(96);
    assert_eq!(
        harness.browser.displayed_index(),
        Some(96),
        "reversing the gesture must reuse the other side of the same bounded warm window"
    );
    assert!(!harness.browser.pending());
    assert_eq!(
        harness.started.borrow().len(),
        starts,
        "both selections must be cache hits before any new worker is scheduled"
    );
    let old_shallow_cache: Vec<_> = [99, 100, 101].into();
    assert!(
        !old_shallow_cache.contains(&104) && !old_shallow_cache.contains(&96),
        "negative control: the former three-capture cache cannot satisfy this gesture"
    );
}

#[test]
fn expanded_network_axis_and_source_dock_all_receive_native_contacts_then_reach_idle() {
    let mut harness = Harness::new(1_000);
    harness.select(450);
    harness.visible = (0..48)
        .map(|slot| slot * 7)
        .chain(600..616) // separate capture-axis contacts
        .chain(800..810) // open source-browser viewport
        .chain([998, 999]) // direct comparison endpoints
        .collect();
    assert_eq!(
        harness.visible.len(),
        76,
        "the fixture must exceed the former 64-visible limit with real distinct surfaces"
    );
    assert!(
        harness
            .visible
            .iter()
            .all(|&index| index.abs_diff(450) > 40),
        "trajectory warming must not accidentally hide a dropped visible contact"
    );
    harness.browser.set_probe_frames([Some(998), Some(999)]);
    harness.browser.set_live_frame(Some(997));
    harness.now += SETTLE;
    harness.tick();
    let mut delivered = 0;
    while harness.has_pending() {
        delivered += harness.deliver_image();
        for image in harness.browser.thumbs.values_mut() {
            image.bytes = THUMB_SIDE as usize * THUMB_SIDE as usize * 4;
        }
        harness.browser.trim();
        assert!(
            delivered < 220,
            "all visible surfaces must settle without cyclic decoding"
        );
    }
    for &index in &harness.visible {
        assert!(
            harness.browser.native_thumbnail(index).is_some(),
            "actually painted capture {index} must not be silently omitted from warming"
        );
    }
    assert!(harness.browser.native_thumbnail(997).is_some());
    assert!(!harness.browser.active());
    assert!(
        harness
            .browser
            .thumbs
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= THUMB_BYTES
    );
}

#[test]
fn canvas_starts_with_a_useful_overview_and_only_same_frame_refinement_reveals() {
    let mut harness = Harness::new(20);
    harness.tick();
    assert_eq!(harness.pending[0].side, OVERVIEW_SIDE);
    assert_eq!(harness.pending[0].kind, Kind::Overview);
    harness.deliver(Ok(PreviewImage {
        path: PathBuf::from("0"),
        source_size: [3_000, 2_000],
        size: [96, 64],
        rgba: [20, 50, 90, 255].repeat(96 * 64),
        is_overview: true,
    }));
    assert_eq!(harness.browser.displayed_index(), Some(0));
    assert!(harness.browser.overviews.contains_key(&0));
    assert!(
        harness.browser.thumbs.contains_key(&0),
        "detail worker supplies a ready filmstrip derivative"
    );
    assert_ne!(
        harness.browser.thumbs[&0].texture.id(),
        harness.browser.overviews[&0].texture.id(),
        "filmstrip derivative is separately bounded, not an overview alias charged as tiny"
    );
    harness.now += SETTLE;
    // Retire whichever adjacent overview was already in flight, then the
    // selected high preview wins before any more neighbor/filmstrip work.
    harness.deliver_image();
    assert_eq!(
        (harness.pending[0].index, harness.pending[0].kind),
        (0, Kind::Image)
    );
    harness.deliver(Ok(PreviewImage {
        path: PathBuf::from("0"),
        source_size: [3_000, 2_000],
        size: [192, 128],
        rgba: [20, 50, 90, 255].repeat(192 * 128),
        is_overview: true,
    }));
    assert!(harness.viewer.transitioning());
    let displayed = harness.viewer.texture.as_ref().unwrap().id();
    harness.select(17);
    assert!(
        !harness.viewer.transitioning(),
        "a new requested capture cancels stale refinement"
    );
    assert_eq!(
        harness.viewer.texture.as_ref().unwrap().id(),
        displayed,
        "uncached selection retains a photo"
    );
    assert_eq!(harness.browser.displayed_index(), Some(0));
}

#[test]
fn disjoint_probe_pair_warms_medium_photos_once_and_stays_pinned_under_byte_pressure() {
    // Fail if pinned endpoints are evicted in favour of closer neighbors, or
    // if the normal overview trajectory repeatedly reloads into three slots
    // already required by the selected photo and two distant probe endpoints.
    let mut harness = Harness::new(400);
    harness.select(200);
    harness.visible = (0..150).collect();
    harness.browser.set_probe_frames([Some(0), Some(399)]);
    harness.now += SETTLE;
    harness.tick();
    while harness.has_pending() {
        harness.deliver_image();
        for image in harness.browser.images.values_mut() {
            image.bytes = IMAGE_SIDE as usize * IMAGE_SIDE as usize * 4;
        }
        for image in harness.browser.thumbs.values_mut() {
            image.bytes = THUMB_SIDE as usize * THUMB_SIDE as usize * 4;
        }
        for image in harness.browser.overviews.values_mut() {
            image.bytes = OVERVIEW_SIDE as usize * OVERVIEW_SIDE as usize * 4;
        }
        harness.browser.trim();
        assert!(
            harness.started.borrow().len() < 200,
            "pinned views must not form a decode/evict loop"
        );
    }
    let jobs = harness.started.borrow().clone();
    assert!(
        jobs.len() > 100,
        "fixture must compete with broad disjoint filmstrip warming"
    );
    assert_eq!(
        &jobs
            .iter()
            .copied()
            .filter(|(_, kind)| *kind != Kind::Thumbnail)
            .take(3)
            .collect::<Vec<_>>(),
        &[
            (200, Kind::Overview),
            (0, Kind::Overview),
            (399, Kind::Overview)
        ]
    );
    assert_eq!(
        harness
            .browser
            .overviews
            .keys()
            .copied()
            .collect::<Vec<_>>(),
        [0, 196, 197, 198, 199, 200, 201, 202, 203, 204, 399]
    );
    for index in [0, 399] {
        assert_eq!(
            jobs.iter()
                .filter(|&&(i, k)| i == index && k == Kind::Overview)
                .count(),
            1
        );
        assert!(harness.browser.thumbs.contains_key(&index));
        let snapshot = harness.browser.texture_snapshot(index).unwrap();
        assert_eq!(snapshot.0, 0);
        assert_eq!(
            snapshot.1.id(),
            harness.browser.overviews[&index].texture.id()
        );
    }
    assert!(
        harness
            .browser
            .overviews
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= OVERVIEW_BYTES
    );
    assert!(
        harness
            .browser
            .thumbs
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= THUMB_BYTES
    );
    assert!(harness.browser.thumbs.len() <= 179);
    harness.tick();
    assert!(!harness.browser.active());
}

#[test]
fn probe_changes_and_new_import_keep_snapshot_epochs_honest_and_worker_serial() {
    let mut harness = Harness::new(400);
    harness.select(200);
    harness.browser.set_probe_frames([Some(0), Some(399)]);
    harness.tick();
    harness.deliver_image();
    assert_eq!(
        harness.pending[0].index, 0,
        "fixture must have an obsolete pair decoder running"
    );
    harness.browser.set_probe_frames([Some(17), Some(380)]);
    harness.deliver_image();
    assert_eq!(harness.pending.len(), 1);
    assert_eq!(harness.pending[0].index, 17);
    assert!(
        harness.browser.thumbnail(0).is_some(),
        "same-bracket obsolete pixels may remain cached"
    );
    assert!(
        harness.browser.texture_snapshot(0).is_some(),
        "an obsolete same-bracket overview can remain a truthful cached snapshot"
    );
    harness.epoch = 9;
    harness.browser.reset(9);
    harness.browser.set_probe_frames([Some(17), Some(380)]);
    assert!(harness.browser.texture_snapshot(0).is_none());
    assert!(harness.browser.texture_snapshot(200).is_none());
    harness.deliver_image();
    assert_eq!(
        harness.pending.len(),
        1,
        "import cannot fork another worker"
    );
    assert!(
        harness.browser.texture_snapshot(17).is_none(),
        "old pair delivery must not acquire the new epoch"
    );
    harness.deliver_image();
    let snapshot = harness.browser.texture_snapshot(200).unwrap();
    assert_eq!(snapshot.0, 9);
    assert_eq!(
        snapshot.1.id(),
        harness.viewer.texture.as_ref().unwrap().id()
    );
}

#[test]
fn interactive_snapshot_rejects_filmstrip_only_but_accepts_a_truly_small_overview() {
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser::default();
    browser
        .thumbs
        .insert(4, cache_image(&ctx, image(4), Kind::Thumbnail));
    assert!(
        browser.thumbnail(4).is_some(),
        "filmstrip remains independently usable"
    );
    assert!(
        browser.texture_snapshot(4).is_none(),
        "a tiny filmstrip tier cannot become the main interactive photo"
    );
    browser
        .overviews
        .insert(4, cache_image(&ctx, image(4), Kind::Overview));
    let snapshot = browser.texture_snapshot(4).unwrap();
    assert_eq!(
        snapshot.1.size(),
        [2, 1],
        "eligibility follows decoded overview provenance, not an arbitrary pixel cutoff"
    );
    assert_eq!(snapshot.1.id(), browser.overviews[&4].texture.id());
}

#[test]
fn strict_native_contact_api_excludes_overview_fallbacks_and_unmasks_its_own_failure() {
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser::default();
    browser
        .overviews
        .insert(4, cache_image(&ctx, image(4), Kind::Overview));
    browser
        .images
        .insert(9, cache_image(&ctx, image(9), Kind::Image));
    browser
        .thumbs
        .insert(7, cache_image(&ctx, image(7), Kind::Thumbnail));
    assert_eq!(
        browser.thumbnail(4).unwrap().id(),
        browser.overviews[&4].texture.id(),
        "existing preview fallback must stay available to its current consumers"
    );
    assert!(browser.thumbnail(9).is_some());
    assert!(browser.native_thumbnail(4).is_none());
    assert!(browser.native_thumbnail(9).is_none());
    assert_eq!(browser.native_thumbnail_indices(), vec![7]);
    assert_eq!(browser.thumbnail_indices(), vec![4, 7, 9]);
    browser
        .errors
        .insert((4, Kind::Thumbnail), "native contact damaged".into());
    browser
        .errors
        .insert((9, Kind::Image), "unrelated detail failure".into());
    browser
        .errors
        .insert((12, Kind::Overview), "unrelated overview failure".into());
    assert!(
        browser.error(4).is_none(),
        "a successful overview still masks errors for legacy display lookup"
    );
    assert_eq!(
        browser.native_thumbnail_error(4),
        Some("native contact damaged")
    );
    assert!(browser.native_thumbnail_error(9).is_none());
    assert!(browser.native_thumbnail_error(12).is_none());
    browser
        .thumbs
        .insert(4, cache_image(&ctx, image(4), Kind::Thumbnail));
    assert_eq!(browser.native_thumbnail_indices(), vec![4, 7]);
    assert_eq!(
        browser.native_thumbnail(4).unwrap().id(),
        browser.thumbs[&4].texture.id()
    );
    assert_ne!(
        browser.native_thumbnail(4).unwrap().id(),
        browser.overviews[&4].texture.id(),
        "positive native control must be an actual separate contact texture"
    );
}

#[test]
fn real_contact_delivery_retains_native_texture_identity_through_overview_and_detail_arrival() {
    let mut harness = Harness::new(20);
    harness.visible = vec![5];
    harness.tick();
    assert_eq!(
        (harness.pending[0].index, harness.pending[0].kind),
        (0, Kind::Overview)
    );
    assert!(
        harness.film_pending[0].indices.contains(&5),
        "native delivery must really include the test capture"
    );
    harness.deliver_film_images();
    let native = harness.browser.native_thumbnail(5).unwrap().id();
    let native_size = harness.browser.native_thumbnail(5).unwrap().size();
    assert!(
        harness.browser.texture_snapshot(5).is_none(),
        "native must arrive before any canonical image in this control"
    );
    harness.browser.set_probe_frames([Some(5), Some(5)]);
    harness.select(5);
    harness.deliver(Ok(image(0)));
    assert_eq!(
        (harness.pending[0].index, harness.pending[0].kind),
        (5, Kind::Overview)
    );
    let larger = |size: [usize; 2]| PreviewImage {
        path: PathBuf::from("5"),
        source_size: [7008, 4672],
        size,
        rgba: vec![120; size[0] * size[1] * 4],
        is_overview: true,
    };
    harness.deliver(Ok(larger([96, 64])));
    assert_eq!(harness.browser.native_thumbnail(5).unwrap().id(), native);
    assert_eq!(
        harness.browser.native_thumbnail(5).unwrap().size(),
        native_size
    );
    let overview = harness.browser.texture_snapshot(5).unwrap().1;
    assert_eq!(overview.size(), [96, 64]);
    assert_ne!(
        overview.id(),
        native,
        "control must deliver an actual distinct larger tier"
    );
    harness.now += SETTLE;
    harness.tick();
    assert_eq!(
        (harness.pending[0].index, harness.pending[0].kind),
        (6, Kind::Overview),
        "the immediately adjacent overview already started before the settling deadline"
    );
    assert!(
        !harness.browser.work.as_ref().unwrap().task.is_cancelled(),
        "useful neighboring work should finish in its existing bounded lane"
    );
    harness.deliver(Ok(image(6)));
    assert_eq!(harness.browser.displayed_index(), Some(5));
    assert_eq!(
        harness.browser.texture_snapshot(5).unwrap().1.id(),
        overview.id()
    );
    assert_eq!(harness.browser.native_thumbnail(5).unwrap().id(), native);
    assert_eq!(
        (harness.pending[0].index, harness.pending[0].kind),
        (5, Kind::Image),
        "settled selected detail must outrank every remaining speculative neighbor"
    );
    harness.deliver(Ok(larger([192, 128])));
    let detail = harness.browser.texture_snapshot(5).unwrap().1;
    assert_eq!(detail.size(), [192, 128]);
    assert_ne!(detail.id(), overview.id());
    assert_eq!(
        harness.browser.native_thumbnail(5).unwrap().id(),
        native,
        "a detail derivative must not replace an established native contact"
    );
    assert_eq!(
        harness.browser.native_thumbnail(5).unwrap().size(),
        native_size
    );
    assert!(harness.browser.native_thumbnail_indices().contains(&5));
}

#[test]
fn five_warm_contacts_refill_after_eviction_even_when_canonical_tiers_exist_then_reach_idle() {
    let mut harness = Harness::new(5);
    for index in [0, 1, 2, 4] {
        let mut cached = cache_image(&harness.ctx, image(index), Kind::Image);
        cached.bytes = IMAGE_BYTES / 4;
        harness.browser.images.insert(index, cached);
    }
    for index in [1, 3] {
        let mut cached = cache_image(&harness.ctx, image(index), Kind::Overview);
        cached.bytes = OVERVIEW_BYTES / 2;
        harness.browser.overviews.insert(index, cached);
    }
    // Simulate contact eviction independently of the retained canonical tiers.
    let evicted = cache_image(&harness.ctx, image(1), Kind::Thumbnail);
    let old_native = evicted.texture.id();
    harness.browser.thumbs.insert(1, evicted);
    harness.browser.thumbs.clear();
    harness.browser.set_probe_frames([Some(1), Some(4)]);
    harness.visible = (0..5).collect();
    harness.select(0);
    harness.now += SETTLE;
    let canonical: Vec<_> = (0..5)
        .map(|index| harness.browser.thumbnail(index).unwrap().id())
        .collect();
    assert!(
        (0..5).all(|index| harness.browser.native_thumbnail(index).is_none()),
        "control must have canonical fallbacks but no contact textures"
    );
    harness.tick();
    assert!(
        harness.pending.is_empty(),
        "existing canonical tiers need no new detail decoder"
    );
    assert_eq!(harness.film_pending.len(), 1);
    assert_eq!(harness.film_pending[0].kind, Kind::Thumbnail);
    assert_eq!(
        harness.film_pending[0].indices,
        vec![0, 1, 2, 3, 4],
        "native contacts must actually be scheduled despite larger cached images"
    );
    assert_eq!(harness.deliver_film_images(), 5);
    assert_eq!(
        harness.browser.native_thumbnail_indices(),
        vec![0, 1, 2, 3, 4]
    );
    assert_ne!(
        harness.browser.native_thumbnail(1).unwrap().id(),
        old_native,
        "an evicted handle cannot stand in for actual replacement delivery"
    );
    for (index, canonical) in canonical.into_iter().enumerate() {
        assert_ne!(
            harness.browser.native_thumbnail(index).unwrap().id(),
            canonical,
            "native getter must expose the new small delivery, not its larger fallback"
        );
    }
    for _ in 0..4 {
        harness.tick();
    }
    assert!(!harness.has_pending());
    assert!(
        !harness.browser.active(),
        "a completed warm set must settle instead of repeatedly decoding native contacts"
    );
    assert_eq!(harness.browser.thumbs.len(), 5);
    assert!(
        harness
            .browser
            .thumbs
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= THUMB_BYTES
    );
    assert!(
        harness
            .browser
            .images
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= IMAGE_BYTES
    );
    assert!(
        harness
            .browser
            .overviews
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= OVERVIEW_BYTES
    );
}

#[test]
fn visible_eight_commit_together_while_expensive_detail_and_pins_are_blocked() {
    // The former one-worker scheduler cannot start this batch until the
    // deliberately withheld1920 delivery. The range is distant from the
    // selected frame and both probe pins, so trajectory warming cannot pass.
    let mut harness = Harness::new(400);
    harness
        .browser
        .overviews
        .insert(200, cache_image(&harness.ctx, image(200), Kind::Overview));
    harness.select(200);
    harness.visible = (40..48).collect();
    harness.now += SETTLE;
    harness.tick();
    assert_eq!(
        (harness.pending[0].index, harness.pending[0].side),
        (200, IMAGE_SIDE)
    );
    assert_eq!(
        harness.film_pending[0].indices,
        (40..48).collect::<Vec<_>>()
    );
    assert_eq!(harness.film_pending[0].side, THUMB_SIDE);
    assert!((40..48).all(|index| !harness.browser.has_thumbnail(index)));
    let retained = harness.viewer.texture.as_ref().unwrap().id();
    harness.browser.set_probe_frames([Some(0), Some(399)]);
    harness.deliver_film_images();
    assert!(
        (40..48).all(|index| harness.browser.has_thumbnail(index)),
        "one delivery must expose the complete real visible range"
    );
    assert!(
        (40..48).all(|index| harness.browser.texture_snapshot(index).is_none()),
        "native strip crops cannot enter the canvas"
    );
    assert_eq!(
        harness.pending[0].index, 200,
        "large decoder must still be blocked for this test to reject starvation"
    );
    assert_eq!(harness.viewer.texture.as_ref().unwrap().id(), retained);
    assert_eq!(harness.pending.len(), 1);
    assert_eq!(harness.film_pending.len(), 1);
}

#[test]
fn latest_visible_range_replaces_obsolete_batch_and_errors_do_not_poison_valid_overviews() {
    let mut harness = Harness::new(400);
    harness.visible = (40..48).collect();
    harness.tick();
    harness.visible = (180..188).collect();
    harness.deliver_film_images();
    assert_eq!(
        harness.film_pending[0].indices,
        (180..188).collect::<Vec<_>>()
    );
    let images = (180..188)
        .map(|index| {
            (
                index,
                if index == 184 {
                    Err("damaged tiny camera thumbnail".into())
                } else {
                    Ok(SourcePreview {
                        image: image(index),
                        thumbnail: None,
                    })
                },
            )
        })
        .collect();
    harness.deliver_film(Ok(images));
    assert!(harness.browser.error(184).is_some());
    assert!(
        (180..188)
            .filter(|&index| index != 184)
            .all(|index| harness.browser.has_thumbnail(index))
    );
    harness
        .browser
        .overviews
        .insert(184, cache_image(&harness.ctx, image(184), Kind::Overview));
    assert!(
        harness.browser.error(184).is_none(),
        "failed tiny crop cannot poison usable canvas pixels"
    );
    assert!(harness.browser.has_thumbnail(184));
}

#[test]
fn import_retires_both_old_lanes_without_retagging_late_pixels_or_errors() {
    let mut harness = Harness::new(200);
    harness.select(100);
    harness.visible = (40..48).collect();
    harness.tick();
    harness.epoch = 12;
    harness.browser.reset(12);
    harness.viewer = Viewer::default();
    harness.tick();
    assert_eq!(harness.pending.len(), 1);
    assert_eq!(harness.film_pending.len(), 1);
    let old = (40..48)
        .map(|index| {
            (
                index,
                if index == 43 {
                    Err("old bracket corrupt thumbnail".into())
                } else {
                    Ok(SourcePreview {
                        image: image(index),
                        thumbnail: None,
                    })
                },
            )
        })
        .collect();
    harness.deliver_film(Ok(old));
    assert!(harness.browser.thumbs.is_empty() && harness.browser.errors.is_empty());
    assert!(harness.viewer.texture.is_none());
    assert_eq!(
        harness.film_pending.len(),
        1,
        "retired old fast task is replaced by only one new task"
    );
    assert_eq!(harness.film_pending[0].indices, [100]);
    assert_eq!(harness.film_pending[0].kind, Kind::Overview);
    harness.deliver(Ok(image(100)));
    assert!(
        harness.viewer.texture.is_none(),
        "old main pixels cannot be assigned to the new bracket"
    );
    assert!(
        harness.pending.is_empty(),
        "do not duplicate the new selected overview already running on the fast lane"
    );
    harness.deliver_film_images();
    assert_eq!(harness.browser.displayed_index(), Some(100));
    assert_eq!(harness.browser.texture_snapshot(100).unwrap().0, 12);
    assert!(harness.browser.error(43).is_none());
}

#[test]
fn protected_complete_working_set_evicts_stale_nearby_thumbs_and_reaches_idle() {
    // A fresh-cache test misses distance eviction's failure: old nearby
    // thumbnails can continually evict required distant visible cells.
    let mut harness = Harness::new(600);
    harness.select(300);
    harness.visible = (0..24).collect();
    harness.browser.set_probe_frames([Some(550), Some(599)]);
    harness.browser.set_live_frame(Some(500));
    for index in 44..556 {
        let mut cached = cache_image(&harness.ctx, image(index), Kind::Thumbnail);
        cached.bytes = THUMB_SIDE as usize * THUMB_SIDE as usize * 4;
        harness.browser.thumbs.insert(index, cached);
    }
    harness.now += SETTLE;
    harness.tick();
    let mut delivered = 0;
    while harness.has_pending() {
        delivered += harness.deliver_image();
        for image in harness.browser.thumbs.values_mut() {
            image.bytes = THUMB_SIDE as usize * THUMB_SIDE as usize * 4;
        }
        for image in harness.browser.overviews.values_mut() {
            image.bytes = OVERVIEW_SIDE as usize * OVERVIEW_SIDE as usize * 4;
        }
        for image in harness.browser.images.values_mut() {
            image.bytes = IMAGE_SIDE as usize * IMAGE_SIDE as usize * 4;
        }
        harness.browser.trim();
        assert!(
            delivered < 180,
            "a full old cache cannot force infinite visible re-decoding"
        );
    }
    assert!((0..24).all(|index| harness.browser.has_thumbnail(index)));
    assert!(
        [500, 550, 599]
            .into_iter()
            .all(|index| harness.browser.has_thumbnail(index))
    );
    assert!(
        harness
            .browser
            .thumbs
            .values()
            .map(|image| image.bytes)
            .sum::<usize>()
            <= THUMB_BYTES
    );
    assert!(harness.browser.thumbnail_indices().len() <= THUMB_COUNT);
    assert!(!harness.browser.active());
}

#[test]
fn paused_selection_warms_far_live_input_without_moving_or_decoding_its_canvas() {
    let mut harness = Harness::new(1_000);
    harness
        .browser
        .images
        .insert(0, cache_image(&harness.ctx, image(0), Kind::Image));
    harness.select(0);
    harness.visible = (0..14).collect();
    harness.browser.set_live_frame(Some(999));
    harness.tick();
    assert!(harness.film_pending[0].indices.contains(&999));
    assert_eq!(harness.film_pending[0].kind, Kind::Thumbnail);
    harness.deliver_film_images();
    assert!(harness.browser.has_thumbnail(999));
    assert!(harness.browser.texture_snapshot(999).is_none());
    assert_eq!(harness.browser.displayed_index(), Some(0));
    assert_eq!(harness.selected, 0);
    assert!(
        !harness
            .started
            .borrow()
            .iter()
            .any(|&(index, kind)| index == 999 && kind != Kind::Thumbnail)
    );
    assert!(harness.browser.warm_thumbs.contains(&999));
}

#[test]
fn filmstrip_worker_failure_retires_its_lane_and_does_not_repeat_a_failed_batch() {
    let mut harness = Harness::new(200);
    harness.visible = (80..88).collect();
    harness.tick();
    let indices = harness.film_pending[0].indices.clone();
    harness.deliver_film(Err("fixture filmstrip worker disconnected".into()));
    for index in indices {
        assert!(
            harness
                .browser
                .error(index)
                .unwrap()
                .contains("worker disconnected")
        );
        assert!(
            !harness.film_pending[0].indices.contains(&index),
            "failed cells must not create a retry loop"
        );
    }
    assert_eq!(
        harness.pending.len(),
        1,
        "filmstrip failure leaves the independent detail worker alive"
    );
    assert_eq!(
        harness.film_pending.len(),
        1,
        "one failed task is replaced by only one next batch"
    );
}

#[test]
fn old_nearby_errors_cannot_evict_current_distant_failures_into_a_retry_loop() {
    let mut harness = Harness::new(600);
    harness.select(300);
    harness.visible = (0..24).collect();
    harness
        .browser
        .images
        .insert(300, cache_image(&harness.ctx, image(300), Kind::Image));
    for index in 50..306 {
        harness
            .browser
            .errors
            .insert((index, Kind::Thumbnail), "old nearby failure".into());
    }
    harness.tick();
    let mut seen = std::collections::BTreeSet::new();
    for _ in 0..3 {
        assert_eq!(harness.film_pending[0].indices.len(), 8);
        for &index in &harness.film_pending[0].indices {
            assert!(
                index < 24,
                "visible failures take priority over background trajectory work"
            );
            assert!(
                seen.insert(index),
                "failed visible range must advance instead of re-decoding the same evicted failures"
            );
        }
        harness.deliver_film(Err("current visible batch unreadable".into()));
        assert!(harness.browser.errors.len() <= ERROR_COUNT);
    }
    assert_eq!(
        seen.into_iter().collect::<Vec<_>>(),
        (0..24).collect::<Vec<_>>()
    );
    assert!((0..24).all(|index| harness.browser.error(index).is_some()));
    assert!(
        harness.film_pending[0]
            .indices
            .iter()
            .all(|&index| index >= 24)
    );
}
