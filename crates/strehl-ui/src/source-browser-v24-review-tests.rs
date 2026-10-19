//! Independent working-set and cancellation reversal witnesses. These exercise
//! real retained byte sizes and stale publication, not elapsed-time claims.
use super::*;

#[test]
fn worst_case_square_overviews_keep_both_pins_and_the_entire_scrub_neighborhood() {
    let ctx = egui::Context::default();
    let mut cache = BTreeMap::new();
    let wanted = [0, 56, 57, 58, 59, 60, 61, 62, 63, 64, 129];
    for index in wanted.into_iter().chain([100]) {
        let side = 960;
        let preview = PreviewImage {
            path: PathBuf::from(index.to_string()),
            source_size: [4096, 4096],
            size: [side, side],
            rgba: vec![index as u8; side * side * 4],
            is_overview: true,
        };
        let image = cache_image(&ctx, preview, Kind::Overview);
        assert_eq!(image.texture.size(), [960, 960]);
        cache.insert(index, image);
    }
    assert!(cache.values().map(|image| image.bytes).sum::<usize>() > OVERVIEW_BYTES);
    trim_cache_pinned(
        &mut cache,
        60,
        OVERVIEW_COUNT,
        OVERVIEW_BYTES,
        [Some(0), Some(129)],
    );
    assert_eq!(cache.keys().copied().collect::<Vec<_>>(), wanted);
    assert!(cache.values().map(|image| image.bytes).sum::<usize>() <= OVERVIEW_BYTES);
    // The identical entries must exercise byte eviction independently of the
    // count limit. A tiny-pixel scheduler fixture cannot catch this failure.
    let mut insufficient = cache.clone();
    trim_cache_pinned(
        &mut insufficient,
        60,
        OVERVIEW_COUNT,
        32 * 1024 * 1024,
        [Some(0), Some(129)],
    );
    assert!(insufficient.len() < wanted.len());
    assert!(insufficient.contains_key(&0) && insufficient.contains_key(&129));
    assert!(insufficient.contains_key(&60));
}

#[test]
fn returning_to_cancelled_capture_before_codec_returns_reissues_it_without_stale_publication() {
    let mut h = Harness::new(150);
    h.tick();
    assert_eq!(h.pending[0].index, 0);
    h.select(100);
    h.tick();
    assert!(h.browser.work.as_ref().unwrap().task.is_cancelled());
    h.select(0);
    h.tick();
    assert_eq!(
        h.pending.len(),
        1,
        "returning to A cannot reopen its occupied lane"
    );
    assert!(h.browser.work.as_ref().unwrap().task.is_cancelled());
    let retired = h.pending.remove(0);
    retired.send.send(Ok(image(0))).unwrap();
    let deadline = Instant::now() + Duration::from_secs(3);
    loop {
        h.tick();
        if h.browser
            .work
            .as_ref()
            .is_some_and(|work| !work.task.is_cancelled())
        {
            break;
        }
        assert!(Instant::now() < deadline, "cancelled lane did not retire");
        std::thread::yield_now();
    }
    assert_eq!(h.pending.len(), 1);
    assert_eq!((h.pending[0].index, h.pending[0].kind), (0, Kind::Overview));
    assert!(
        h.browser.texture_snapshot(0).is_none(),
        "an ABA identity match cannot rehabilitate canceled pixels"
    );
    assert!(h.browser.errors.is_empty());
    h.deliver_image();
    assert_eq!(h.browser.displayed_index(), Some(0));
    assert!(!h.browser.pending());
    assert!(h.browser.texture_snapshot(0).is_some());
}
