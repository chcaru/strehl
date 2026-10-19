use super::*;

fn contacts(h: &mut Harness) {
    for index in 0..h.frames.len() {
        h.browser
            .thumbs
            .insert(index, cache_image(&h.ctx, image(index), Kind::Thumbnail));
    }
}

#[test]
fn foreground_inspection_owns_refinement_even_when_old_clicked_frame_remains_a_probe() {
    let mut h = Harness::new(130);
    contacts(&mut h);
    for index in [0, 80, 129] {
        h.browser
            .overviews
            .insert(index, cache_image(&h.ctx, image(index), Kind::Overview));
    }
    h.select(0);
    h.now += SETTLE;
    h.tick();
    assert_eq!((h.pending[0].index, h.pending[0].kind), (0, Kind::Image));
    // App supplies the transient process inspection as the foreground poll
    // target; it need not mutate the catalog's clicked frame to request pixels.
    h.browser.set_probe_frames([Some(0), Some(129)]);
    h.select(80);
    let visible80 = h.viewer.texture.as_ref().unwrap().id();
    h.tick();
    assert_eq!(h.browser.displayed_index(), Some(80));
    assert!(
        h.browser.work.as_ref().unwrap().task.is_cancelled(),
        "cached foreground overview must not hide stale-refinement priority"
    );
    assert_eq!(
        h.pending.len(),
        1,
        "cancellation retains the actual decoder lane"
    );
    h.now += SETTLE;
    h.deliver(Ok(image(0)));
    assert!(
        !h.browser.images.contains_key(&0),
        "cancelled old pixels never upload"
    );
    assert_eq!(h.viewer.texture.as_ref().unwrap().id(), visible80);
    assert_eq!((h.pending[0].index, h.pending[0].kind), (80, Kind::Image));
    h.deliver(Ok(image(80)));
    assert!(h.browser.has_image(80));
    assert_eq!(h.browser.displayed_index(), Some(80));
    assert_eq!(
        (h.pending[0].index, h.pending[0].kind),
        (81, Kind::Overview),
        "warming follows the inspected source's motion, not the old clicked frame"
    );
}

#[test]
fn uncached_foreground_inspection_rescues_while_old_pinned_refinement_retires() {
    let mut h = Harness::new(130);
    contacts(&mut h);
    for index in [0, 129] {
        h.browser
            .overviews
            .insert(index, cache_image(&h.ctx, image(index), Kind::Overview));
    }
    h.select(0);
    h.now += SETTLE;
    h.tick();
    let retained = h.viewer.texture.as_ref().unwrap().id();
    h.browser.set_probe_frames([Some(0), Some(129)]);
    h.select(80);
    h.tick();
    assert!(h.browser.work.as_ref().unwrap().task.is_cancelled());
    assert_eq!(h.film_pending[0].indices, [80]);
    assert_eq!(h.film_pending[0].kind, Kind::Overview);
    assert_eq!(h.browser.displayed_index(), Some(0));
    assert_eq!(h.viewer.texture.as_ref().unwrap().id(), retained);
    assert!(h.browser.pending());
    h.deliver_film_images();
    assert_eq!(h.browser.displayed_index(), Some(80));
    assert_eq!(
        h.pending.len(),
        1,
        "rescue cannot multiply large decoder lanes"
    );
}
