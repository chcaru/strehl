//! Independent scheduling witnesses. These count requested worker operations,
//! not elapsed time, and require actual overview and refinement work to occur.
use super::*;

fn warm_all_contacts(harness: &mut Harness) {
    for index in 0..harness.frames.len() {
        harness.browser.thumbs.insert(
            index,
            cache_image(&harness.ctx, image(index), Kind::Thumbnail),
        );
    }
}

fn drain(harness: &mut Harness) {
    let mut operations = 0;
    while harness.has_pending() {
        harness.deliver_image();
        operations += 1;
        assert!(operations < 32, "one selected neighborhood must reach idle");
    }
}

#[test]
fn warm_130_capture_sweep_and_refinement_request_no_discarded_contact_derivatives() {
    let mut h = Harness::new(130);
    warm_all_contacts(&mut h);
    let contact_ids: Vec<_> = (0..130)
        .map(|i| h.browser.native_thumbnail(i).unwrap().id())
        .collect();
    for index in 0..130 {
        h.select(index);
        // The process workspace retains the selected source plus a pair end.
        h.browser.set_probe_frames([Some(index), Some(129)]);
        h.tick();
        drain(&mut h);
        assert_eq!(h.browser.displayed_index(), Some(index));
    }
    // A second, far-jumping pass defeats the two-neighbor refinement cache;
    // every selected photograph must still become a real high-resolution hit.
    for index in (0..130).map(|step| step * 37 % 130) {
        h.select(index);
        h.browser.set_probe_frames([Some(index), Some(129)]);
        h.tick();
        drain(&mut h);
        h.now += SETTLE;
        h.tick();
        drain(&mut h);
        assert!(
            h.browser.has_image(index),
            "selected capture must really refine"
        );
    }
    let calls = h.derivatives.borrow();
    assert!(
        calls
            .iter()
            .filter(|(_, k, _)| *k == Kind::Overview)
            .count()
            >= 100,
        "fixture must decode many uncached sources, not just inspect a warm image cache"
    );
    assert!(
        calls.iter().filter(|(_, k, _)| *k == Kind::Image).count() >= 100,
        "fixture must exercise the settled higher-resolution lane"
    );
    assert!(
        calls.iter().all(|(_, _, requested)| !requested),
        "retained contacts must avoid redundant worker resizing/allocation"
    );
    for (index, id) in contact_ids.into_iter().enumerate() {
        assert_eq!(
            h.browser.native_thumbnail(index).unwrap().id(),
            id,
            "overview/refinement may not replace established contact geometry"
        );
    }
}

#[test]
fn missing_contact_derivative_recovers_identity_even_after_native_contact_failure() {
    let mut h = Harness::new(1);
    h.browser
        .errors
        .insert((0, Kind::Thumbnail), "broken small embedded JPEG".into());
    h.tick();
    assert!(
        h.pending[0].thumbnail,
        "an error entry is not a retained contact"
    );
    assert_eq!(h.pending[0].kind, Kind::Overview);
    h.deliver(Ok(image(0)));
    assert_eq!(h.browser.displayed_index(), Some(0));
    assert!(h.browser.native_thumbnail(0).is_some());
    assert!(h.browser.native_thumbnail_error(0).is_none());
    let (epoch, _, source_size) = h.browser.texture_snapshot(0).unwrap();
    assert_eq!(epoch, h.epoch);
    assert_eq!(source_size, image(0).source_size);
}

#[test]
fn contact_batch_arriving_before_requested_derivative_keeps_its_texture_handle() {
    let mut h = Harness::new(20);
    h.tick();
    let target = h.film_pending[0].indices[0];
    assert_ne!(
        target, h.pending[0].index,
        "fixture needs two genuinely distinct lanes"
    );
    h.select(target);
    h.tick();
    h.deliver(Ok(image(0)));
    assert_eq!(h.pending[0].index, target);
    assert!(
        h.pending[0].thumbnail,
        "contact was absent at detail scheduling time"
    );
    assert!(h.film_pending[0].indices.contains(&target));
    h.deliver_film_images();
    let contact = h.browser.native_thumbnail(target).unwrap().id();
    h.deliver(Ok(image(target)));
    assert_eq!(h.browser.displayed_index(), Some(target));
    assert_eq!(
        h.browser.native_thumbnail(target).unwrap().id(),
        contact,
        "a raced redundant derivative cannot replace an already published contact"
    );
}

#[test]
fn fast_rescue_skips_retained_derivative_while_old_detail_decode_is_still_blocked() {
    let mut h = Harness::new(130);
    warm_all_contacts(&mut h);
    h.tick();
    assert_eq!(h.pending[0].index, 0);
    h.select(75);
    h.tick();
    assert_eq!(h.film_pending[0].kind, Kind::Overview);
    assert_eq!(h.film_pending[0].indices, [75]);
    assert!(!h.film_pending[0].thumbnail);
    h.deliver_film_images();
    assert_eq!(h.browser.displayed_index(), Some(75));
    assert_eq!(
        h.pending[0].index, 0,
        "the rescue must not wait for old detail work"
    );
    assert!(
        h.derivatives
            .borrow()
            .iter()
            .any(|&(i, k, d)| i == 75 && k == Kind::Overview && !d),
        "fixture must observe the rescue request, not infer it from final cache state"
    );
}
