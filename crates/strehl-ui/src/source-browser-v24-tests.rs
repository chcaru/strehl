//! Scheduling witnesses use held worker deliveries, not elapsed-time claims.
use super::*;

#[test]
fn distant_scrub_cancels_both_obsolete_lanes_without_starting_more_decoders() {
    let mut h = Harness::new(300);
    h.tick();
    let old_detail = h.pending[0].index;
    let old_contacts = h.film_pending[0].indices.clone();
    assert_eq!(old_detail, 0);
    assert_eq!(old_contacts.len(), source_preview::FILMSTRIP_BATCH_MAX);
    h.select(250);
    h.tick();
    assert!(h.browser.work.as_ref().unwrap().task.is_cancelled());
    assert!(h.browser.film_work.as_ref().unwrap().task.is_cancelled());
    let issued = h.started.borrow().len();
    for index in [270, 210, 230, 299, 245] {
        h.select(index);
        h.tick();
        assert_eq!(h.started.borrow().len(), issued);
        assert_eq!(h.pending.len(), 1);
        assert_eq!(h.film_pending.len(), 1);
        assert!(h.browser.texture_snapshot(index).is_none());
    }
    // Even an already prepared old result is ineligible for a texture upload
    // after retirement. Cancellation is not recorded as a corrupt photograph.
    h.deliver(Ok(image(old_detail)));
    assert_eq!(h.pending[0].index, 245);
    assert!(h.browser.texture_snapshot(old_detail).is_none());
    assert!(h.browser.errors.is_empty());
    assert_eq!(h.browser.displayed_index(), None);
    h.deliver_film_images();
    assert!(
        old_contacts
            .iter()
            .all(|&i| h.browser.native_thumbnail(i).is_none())
    );
    assert!(h.browser.errors.is_empty());
    h.deliver(Ok(image(245)));
    assert_eq!(h.browser.displayed_index(), Some(245));
    assert!(h.browser.texture_snapshot(245).is_some());
    // Retired requests remain eligible if the user comes back to them.
    h.select(0);
    h.tick();
    assert!(h.browser.missing(0, Kind::Overview));
    assert!(h.browser.error(0).is_none());
}

#[test]
fn nearby_overview_and_explicit_probe_are_retained_but_old_detail_is_cancelled() {
    let mut h = Harness::new(100);
    h.tick();
    h.select(1);
    h.tick();
    assert!(!h.browser.work.as_ref().unwrap().task.is_cancelled());
    h.browser.set_probe_frames([Some(0), None]);
    h.select(90);
    h.tick();
    assert!(!h.browser.work.as_ref().unwrap().task.is_cancelled());
    h.browser.set_probe_frames([None, None]);
    h.tick();
    assert!(h.browser.work.as_ref().unwrap().task.is_cancelled());

    let mut h = Harness::new(100);
    h.browser
        .overviews
        .insert(40, cache_image(&h.ctx, image(40), Kind::Overview));
    h.select(40);
    h.now += SETTLE;
    h.tick();
    assert_eq!((h.pending[0].index, h.pending[0].kind), (40, Kind::Image));
    let visible = h.viewer.texture.as_ref().unwrap().id();
    h.select(41);
    h.tick();
    assert!(h.browser.work.as_ref().unwrap().task.is_cancelled());
    assert_eq!(h.viewer.texture.as_ref().unwrap().id(), visible);
    assert_eq!(h.browser.displayed_index(), Some(40));
    assert!(h.browser.pending());
}

#[test]
fn process_comparison_warms_both_scrub_directions_without_redecoding_pinned_pair() {
    let mut h = Harness::new(130);
    for index in 0..130 {
        h.browser
            .thumbs
            .insert(index, cache_image(&h.ctx, image(index), Kind::Thumbnail));
    }
    h.select(60);
    h.browser.set_probe_frames([Some(0), Some(129)]);
    h.tick();
    let mut operations = 0;
    while h.has_pending() {
        h.deliver_image();
        operations += 1;
        assert!(
            operations <= OVERVIEW_COUNT + 3,
            "bounded working set must actually settle"
        );
    }
    assert_eq!(h.browser.overviews.len(), 11);
    for index in [0, 56, 57, 58, 59, 60, 61, 62, 63, 64, 129] {
        assert!(
            h.browser.texture_snapshot(index).is_some(),
            "missing warmed source {index}"
        );
        assert_eq!(
            h.started
                .borrow()
                .iter()
                .filter(|&&(i, k)| i == index && k == Kind::Overview)
                .count(),
            1
        );
    }
    let issued = h.started.borrow().len();
    for index in [61, 62, 63, 64, 63, 62, 61, 60, 59, 58, 57, 56] {
        h.select(index);
        assert_eq!(h.browser.displayed_index(), Some(index));
        assert!(!h.browser.pending());
        assert_eq!(
            h.started.borrow().len(),
            issued,
            "cached gesture must not issue work"
        );
        let (_, texture, aperture) = h.browser.texture_snapshot(index).unwrap();
        assert_eq!(h.viewer.texture.as_ref().unwrap().id(), texture.id());
        assert_eq!(aperture, image(index).source_size);
    }
}

#[test]
fn cancelled_rescue_retires_before_newest_request_and_never_poisoned_as_failure() {
    let mut h = Harness::new(200);
    for index in 0..200 {
        h.browser
            .thumbs
            .insert(index, cache_image(&h.ctx, image(index), Kind::Thumbnail));
    }
    h.tick();
    h.select(80);
    h.tick();
    assert_eq!(h.film_pending[0].kind, Kind::Overview);
    assert_eq!(h.film_pending[0].indices, [80]);
    h.select(150);
    h.tick();
    assert!(h.browser.film_work.as_ref().unwrap().task.is_cancelled());
    h.deliver_film_images();
    assert_eq!(h.film_pending[0].indices, [150]);
    assert!(h.browser.texture_snapshot(80).is_none());
    assert!(h.browser.error(80).is_none());
    h.deliver_film_images();
    assert_eq!(h.browser.displayed_index(), Some(150));
    assert_eq!(
        h.pending.len(),
        1,
        "the original detail lane is still owned until its codec exits"
    );
}
