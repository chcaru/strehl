use super::*;
use egui::{
    Context, Event, FullOutput, Modifiers, MouseWheelUnit, PointerButton, RawInput, TextureId,
};

#[test]
fn pending_double_click_preserves_probe_and_compare_then_resets_without_reholding_the_pair() {
    for mode in [WorkbenchMode::Probe, WorkbenchMode::Compare] {
        let ctx = Context::default();
        let mut bench = Workbench::default();
        let photos = [
            Some(photo(&ctx, 1, 0, [120, 80])),
            Some(photo(&ctx, 1, 1, [120, 80])),
        ];
        let at = egui::pos2(240.0, 180.0);
        let event = |point: Pos2, pressed: bool| {
            vec![
                Event::PointerMoved(point),
                Event::PointerButton {
                    pos: point,
                    button: PointerButton::Primary,
                    pressed,
                    modifiers: Modifiers::NONE,
                },
            ]
        };
        frame(&ctx, &mut bench, mode, photos.clone(), 1, 0.0, vec![]);
        frame(
            &ctx,
            &mut bench,
            mode,
            photos.clone(),
            1,
            0.1,
            event(at, true),
        );
        let (_, first_hold) = frame_with_hold(
            &ctx,
            &mut bench,
            mode,
            photos.clone(),
            1,
            0.14,
            event(at, false),
        );
        assert!(
            bench.pin.is_some() || first_hold.is_some(),
            "the first click must change a real image interaction"
        );
        let previous = (bench.pin, bench.wipe);
        frame(
            &ctx,
            &mut bench,
            mode,
            photos.clone(),
            1,
            0.59,
            event(at, true),
        );
        let (_, hold) = frame_with_hold(
            &ctx,
            &mut bench,
            mode,
            photos.clone(),
            1,
            0.62,
            vec![Event::PointerMoved(at + egui::vec2(8.0, 0.0))],
        );
        assert_eq!((bench.pin, bench.wipe), previous);
        assert!(hold.is_none());
        let (_, hold) = frame_with_hold(
            &ctx,
            &mut bench,
            mode,
            photos,
            1,
            0.64,
            event(at + egui::vec2(8.0, 0.0), false),
        );
        assert!(hold.is_none());
        assert!(bench.pin.is_none());
        assert_eq!(bench.wipe, 0.5);
        assert_eq!(bench.zoom_index, 0);
    }
}

#[test]
fn pending_compare_click_becoming_a_real_drag_holds_the_pair_once() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let photos = [
        Some(photo(&ctx, 1, 2, [120, 80])),
        Some(photo(&ctx, 1, 7, [120, 80])),
    ];
    let at = egui::pos2(240.0, 180.0);
    let event = |pressed| {
        vec![
            Event::PointerMoved(at),
            Event::PointerButton {
                pos: at,
                button: PointerButton::Primary,
                pressed,
                modifiers: Modifiers::NONE,
            },
        ]
    };
    let mode = WorkbenchMode::Compare;
    frame(&ctx, &mut bench, mode, photos.clone(), 1, 0.0, vec![]);
    frame(&ctx, &mut bench, mode, photos.clone(), 1, 0.1, event(true));
    let (_, first) = frame_with_hold(
        &ctx,
        &mut bench,
        mode,
        photos.clone(),
        1,
        0.14,
        event(false),
    );
    assert_eq!(first, Some([2, 7]));
    frame(&ctx, &mut bench, mode, photos.clone(), 1, 0.3, event(true));
    for (time, delta, expected) in [
        (0.32, 8.0, None),
        (0.34, 18.0, Some([2, 7])),
        (0.36, 24.0, None),
    ] {
        let (_, hold) = frame_with_hold(
            &ctx,
            &mut bench,
            mode,
            photos.clone(),
            1,
            time,
            vec![Event::PointerMoved(at + egui::vec2(delta, 0.0))],
        );
        assert_eq!(
            hold, expected,
            "the transition to a real drag owns one hold, including after the6px drag-start event"
        );
    }
}

fn photo(ctx: &Context, epoch: u64, index: usize, size: [usize; 2]) -> SourcePhoto {
    solid_photo(ctx, epoch, index, size, Color32::WHITE)
}

fn solid_photo(
    ctx: &Context,
    epoch: u64,
    index: usize,
    size: [usize; 2],
    color: Color32,
) -> SourcePhoto {
    SourcePhoto {
        epoch,
        index,
        aperture: [7_008, 4_672],
        texture: ctx.load_texture(
            format!("camera-{epoch}-{index}-{size:?}"),
            egui::ColorImage::new(size, vec![color; size[0] * size[1]]),
            egui::TextureOptions::LINEAR,
        ),
    }
}

#[allow(clippy::too_many_arguments)]
fn frame(
    ctx: &Context,
    bench: &mut Workbench,
    mode: WorkbenchMode,
    photos: [Option<SourcePhoto>; 2],
    epoch: u64,
    time: f64,
    events: Vec<Event>,
) -> FullOutput {
    frame_with_hold(ctx, bench, mode, photos, epoch, time, events).0
}

#[allow(clippy::too_many_arguments)]
fn frame_with_hold(
    ctx: &Context,
    bench: &mut Workbench,
    mode: WorkbenchMode,
    photos: [Option<SourcePhoto>; 2],
    epoch: u64,
    time: f64,
    events: Vec<Event>,
) -> (FullOutput, Option<[usize; 2]>) {
    sized_frame_with_hold(
        ctx,
        bench,
        mode,
        photos,
        epoch,
        time,
        events,
        egui::vec2(720.0, 520.0),
    )
}

#[allow(clippy::too_many_arguments)]
fn sized_frame_with_hold(
    ctx: &Context,
    bench: &mut Workbench,
    mode: WorkbenchMode,
    photos: [Option<SourcePhoto>; 2],
    epoch: u64,
    time: f64,
    events: Vec<Event>,
    size: Vec2,
) -> (FullOutput, Option<[usize; 2]>) {
    let mut hold = None;
    let output = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, size)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    hold = bench.show(ui, mode, photos[0].clone(), photos[1].clone(), epoch);
                });
        },
    );
    (output, hold)
}

fn painted_labels(output: &FullOutput) -> Vec<String> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.galley.text().to_owned()),
            _ => None,
        })
        .collect()
}

struct Quad {
    texture: TextureId,
    bounds: Rect,
    uv: Rect,
    clip: Rect,
    alpha: u8,
}

fn quads(output: &FullOutput, ids: &[TextureId]) -> Vec<Quad> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if ids.contains(&mesh.texture_id) => {
                assert_eq!(
                    mesh.vertices.len(),
                    4,
                    "actual photo must reach the paint consumer"
                );
                Some(Quad {
                    texture: mesh.texture_id,
                    bounds: Rect::from_points(
                        &mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>(),
                    ),
                    uv: Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>()),
                    clip: shape.clip_rect,
                    alpha: mesh.vertices[0].color.a(),
                })
            }
            _ => None,
        })
        .collect()
}

fn button(pos: Pos2, pressed: bool) -> Event {
    Event::PointerButton {
        pos,
        button: PointerButton::Primary,
        pressed,
        modifiers: Modifiers::NONE,
    }
}

#[test]
fn real_pointer_pins_feature_and_two_lenses_sample_real_frame_textures() {
    // A displaced pin and unequal preview resolutions expose a fake centre
    // crop, a swapped frame, and a lens that merely enlarges its UI rectangle.
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let a = photo(&ctx, 3, 17, [96, 64]);
    let b = photo(&ctx, 3, 22, [192, 128]);
    let ids = [a.texture.id(), b.texture.id()];
    let photos = || [Some(a.clone()), Some(b.clone())];
    let initial = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        3,
        0.0,
        vec![],
    );
    let main = quads(&initial, &ids).remove(0).bounds;
    let expected = egui::pos2(0.29, 0.37);
    let pointer = main.min + expected.to_vec2() * main.size();
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        3,
        0.02,
        vec![Event::PointerMoved(pointer), button(pointer, true)],
    );
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        3,
        0.04,
        vec![button(pointer, false)],
    );
    assert!(
        (bench.pin.unwrap() - expected).length() < 1e-5,
        "fixture must actually send pointer input to the photo"
    );
    let painted = quads(&output, &ids);
    assert_eq!(painted.len(), 3, "main A plus two real ROI images");
    assert_eq!(painted[0].texture, a.texture.id());
    assert_eq!(painted[1].texture, a.texture.id());
    assert_eq!(painted[2].texture, b.texture.id());
    for lens in &painted[1..] {
        assert!((lens.uv.center() - expected).length() < 1e-5);
        assert!(lens.uv.width() < 0.1 && lens.uv.height() < 0.1);
        assert!(lens.clip.contains_rect(lens.bounds));
        let visible_x = lens.bounds.width() / lens.uv.width();
        let visible_y = lens.bounds.height() / lens.uv.height();
        assert!(
            (visible_x / visible_y - 1.5).abs() < 1e-4,
            "ROI pixels must use uniform photo scaling"
        );
    }
    assert!(
        bench
            .a
            .as_ref()
            .unwrap()
            .label("A")
            .starts_with("A · frame 18")
    );
    assert!(
        bench
            .b
            .as_ref()
            .unwrap()
            .label("B")
            .starts_with("B · frame 23")
    );

    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        3,
        0.06,
        vec![
            Event::PointerMoved(pointer),
            Event::MouseWheel {
                unit: MouseWheelUnit::Point,
                delta: egui::vec2(0.0, 30.0),
                modifiers: Modifiers::NONE,
            },
        ],
    );
    assert_eq!(bench.zoom_index, 1, "wheel input must change magnification");
    let enlarged = quads(&output, &ids);
    assert!((enlarged[1].uv.width() * 2.0 - painted[1].uv.width()).abs() < 1e-5);
    assert_eq!(
        enlarged[1].bounds, painted[1].bounds,
        "zoom changes sampled pixels, not the lens box"
    );
}

#[test]
fn wipe_pointer_clamps_and_uses_real_clipped_comparison_without_stretching() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let a = photo(&ctx, 5, 2, [96, 64]);
    let b = photo(&ctx, 5, 7, [192, 128]);
    let ids = [a.texture.id(), b.texture.id()];
    let photos = || [Some(a.clone()), Some(b.clone())];
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        5,
        1.0,
        vec![],
    );
    let main = quads(&output, &ids)[0].bounds;
    let pointer = egui::pos2(main.left() + main.width() * 0.31, main.center().y);
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        5,
        1.02,
        vec![Event::PointerMoved(pointer), button(pointer, true)],
    );
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        5,
        1.04,
        vec![button(pointer, false)],
    );
    assert!((bench.wipe - 0.31).abs() < 1e-5);
    let painted = quads(&output, &ids);
    assert_eq!(painted.len(), 2);
    assert_eq!(painted[0].bounds, painted[1].bounds);
    assert!((painted[1].clip.left() - pointer.x).abs() < 0.001);
    assert_eq!(
        painted[1].uv,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
    );
    assert!(
        bench.pin.is_none(),
        "comparison dragging must never pin or pan the photo"
    );

    let start = main.center();
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        5,
        1.1,
        vec![Event::PointerMoved(start), button(start, true)],
    );
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        5,
        1.2,
        vec![Event::PointerMoved(egui::pos2(-100.0, start.y))],
    );
    assert_eq!(bench.wipe, 0.0);
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        5,
        1.3,
        vec![Event::PointerMoved(egui::pos2(950.0, start.y))],
    );
    assert_eq!(bench.wipe, 1.0);
}

#[test]
fn missing_photos_hold_only_their_actual_identity_and_import_clears_everything() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let a = photo(&ctx, 8, 21, [96, 64]);
    let b = photo(&ctx, 8, 29, [96, 64]);
    let stale = photo(&ctx, 7, 110, [192, 128]);
    let ids = [a.texture.id(), b.texture.id(), stale.texture.id()];
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [Some(a.clone()), Some(b.clone())],
        8,
        0.0,
        vec![],
    );
    bench.pin = Some(egui::pos2(0.2, 0.8));
    let held = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [None, Some(stale.clone())],
        8,
        0.1,
        vec![],
    );
    assert_eq!(quads(&held, &ids).len(), 2);
    assert_eq!(
        bench.a.as_ref().unwrap().label("A"),
        "A · frame 22 · 96px · updating"
    );
    assert_eq!(
        bench.b.as_ref().unwrap().label("B"),
        "B · frame 30 · 96px · updating"
    );
    assert!(
        quads(&held, &ids)
            .iter()
            .all(|q| q.texture != stale.texture.id())
    );
    let imported = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(a), Some(b)],
        9,
        0.2,
        vec![],
    );
    assert!(
        quads(&imported, &ids).is_empty(),
        "old bracket pixels cannot survive epoch reset"
    );
    assert!(bench.a.is_none() && bench.b.is_none() && bench.pin.is_none());
    assert_eq!(bench.wipe, 0.5);
}

#[test]
fn incompatible_crops_do_not_get_a_fabricated_full_image_comparison() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let a = photo(&ctx, 1, 0, [96, 64]);
    let mut b = photo(&ctx, 1, 1, [160, 120]);
    b.aperture = [160, 120];
    let ids = [a.texture.id(), b.texture.id()];
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [Some(a.clone()), Some(b.clone())],
        1,
        0.0,
        vec![],
    );
    assert!(
        !compatible_photos(&a, &b),
        "negative control must contain truly different crops"
    );
    let painted = quads(&output, &ids);
    assert_eq!(painted.len(), 1);
    assert_eq!(painted[0].texture, a.texture.id());
}

#[test]
fn two_resolution_reveals_are_timed_bounded_and_cancelled_for_different_frames() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let small = [photo(&ctx, 4, 8, [96, 64]), photo(&ctx, 4, 11, [96, 64])];
    let high = [
        photo(&ctx, 4, 8, [192, 128]),
        photo(&ctx, 4, 11, [192, 128]),
    ];
    let ids = [
        small[0].texture.id(),
        small[1].texture.id(),
        high[0].texture.id(),
        high[1].texture.id(),
    ];
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [Some(small[0].clone()), Some(small[1].clone())],
        4,
        10.0,
        vec![],
    );
    let mut alpha = Vec::new();
    let mut reference: Option<Rect> = None;
    for time in [10.1, 10.155, 10.21, 10.265, 10.34] {
        let output = frame(
            &ctx,
            &mut bench,
            WorkbenchMode::Compare,
            [Some(high[0].clone()), Some(high[1].clone())],
            4,
            time,
            vec![],
        );
        let painted = quads(&output, &ids);
        let unique: std::collections::HashSet<_> = painted.iter().map(|q| q.texture).collect();
        assert!(
            unique.len() <= 4,
            "two slots may retain only two textures each"
        );
        let current_alpha = painted
            .iter()
            .find(|q| q.texture == high[0].texture.id())
            .map_or(0, |q| q.alpha);
        alpha.push(current_alpha);
        for quad in painted {
            if let Some(reference) = reference {
                assert!((quad.bounds.min - reference.min).length() < 0.002);
                assert!((quad.bounds.max - reference.max).length() < 0.002);
            } else {
                reference = Some(quad.bounds);
            }
            if small.iter().any(|p| p.texture.id() == quad.texture) {
                assert_eq!(quad.alpha, 255);
            }
        }
    }
    assert_eq!(alpha[0], 0);
    assert!(
        (120..=135).contains(&alpha[2]),
        "must paint an intermediate reveal, not a delayed hard switch"
    );
    assert!(alpha.windows(2).all(|pair| pair[0] < pair[1]));
    assert_eq!(alpha[4], 255);
    assert!(!bench.transitioning());

    let bigger = photo(&ctx, 4, 8, [384, 256]);
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [Some(bigger), Some(high[1].clone())],
        4,
        10.4,
        vec![],
    );
    assert!(
        bench.transitioning(),
        "fixture must interrupt a live reveal"
    );
    let next = photo(&ctx, 4, 19, [96, 64]);
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [Some(next.clone()), Some(high[1].clone())],
        4,
        10.5,
        vec![],
    );
    assert!(!bench.transitioning());
    assert!(bench.a.as_ref().unwrap().previous.is_none());
    let painted = quads(&output, &[ids.as_slice(), &[next.texture.id()]].concat());
    assert_eq!(
        painted.len(),
        2,
        "a different frame cannot ghost its predecessor"
    );
    assert_eq!(painted[0].texture, next.texture.id());
    assert_eq!(painted[0].alpha, 255);
}

#[test]
fn explicit_probe_pin_clamps_finite_coordinates_and_survives_initial_paint_only() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    bench.set_pin(egui::pos2(-0.5, 1.5));
    assert_eq!(bench.pin(), Some(egui::pos2(0.0, 1.0)));
    bench.set_pin(egui::pos2(f32::NAN, 0.2));
    assert_eq!(bench.pin(), Some(egui::pos2(0.0, 1.0)));
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [None, None],
        3,
        0.0,
        vec![],
    );
    assert!(
        bench.pin().is_some(),
        "caller may establish an initial probe before its photo arrives"
    );
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [None, None],
        4,
        0.1,
        vec![],
    );
    assert!(
        bench.pin().is_none(),
        "a new bracket does not inherit a location from the old one"
    );
}

#[test]
fn third_tier_waits_for_current_reveal_without_a_brightness_flash_or_third_texture() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    // Black -> white -> black is an intentionally severe resolution-tier
    // placebo: promoting a partly revealed white tier to an opaque base makes
    // a large flash, even though identity, bounds and texture count all pass.
    let small = solid_photo(&ctx, 6, 4, [48, 32], Color32::BLACK);
    let middle = solid_photo(&ctx, 6, 4, [96, 64], Color32::WHITE);
    let large = solid_photo(&ctx, 6, 4, [192, 128], Color32::BLACK);
    let ids = [small.texture.id(), middle.texture.id(), large.texture.id()];
    let composite = |output: &FullOutput| {
        quads(output, &ids).into_iter().fold(0.0, |base, quad| {
            let light = if quad.texture == middle.texture.id() {
                1.0
            } else {
                0.0
            };
            let alpha = f32::from(quad.alpha) / 255.0;
            base * (1.0 - alpha) + light * alpha
        })
    };
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(small.clone()), None],
        6,
        0.0,
        vec![],
    );
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(middle.clone()), None],
        6,
        0.1,
        vec![],
    );
    let before = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(middle.clone()), None],
        6,
        0.16,
        vec![],
    );
    assert!(
        (0.05..0.3).contains(&composite(&before)),
        "fixture must interrupt a partly visible tier"
    );
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(large.clone()), None],
        6,
        0.17,
        vec![],
    );
    let painted = quads(&output, &ids);
    assert!(
        bench.transitioning(),
        "latest tier must wait while an existing reveal is unfinished"
    );
    assert!(
        painted
            .iter()
            .all(|quad| quad.texture != large.texture.id())
    );
    assert!(
        (composite(&output) - composite(&before)).abs() < 0.1,
        "arrival of a third tier must not promote the partially revealed base to full brightness"
    );
    assert!(
        (1.0 - composite(&before)).abs() > 0.5,
        "negative control: old promotion-to-opaque policy must fail this continuity threshold"
    );
    assert_eq!(
        bench
            .a
            .as_ref()
            .unwrap()
            .previous
            .as_ref()
            .unwrap()
            .texture
            .id(),
        small.texture.id()
    );
    frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(large.clone()), None],
        6,
        0.39,
        vec![],
    );
    assert!(
        bench.transitioning(),
        "deferred tier prevents a premature settled state at the first reveal's completion"
    );
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(large.clone()), None],
        6,
        0.4,
        vec![],
    );
    let painted = quads(&output, &ids);
    assert_eq!(painted.len(), 2);
    assert!(
        painted
            .iter()
            .all(|quad| quad.texture != small.texture.id())
    );
    assert_eq!(
        composite(&output),
        1.0,
        "the next reveal starts from the completed white tier"
    );
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(small.clone()), None],
        6,
        0.51,
        vec![],
    );
    assert_eq!(
        bench.a.as_ref().unwrap().current.texture.id(),
        large.texture.id(),
        "smaller fallback cannot downgrade current pixels or restart the fade"
    );
    let painted = quads(&output, &ids);
    assert!(
        (120..=135).contains(&painted[1].alpha),
        "fallback polls must not restart an active reveal"
    );
}

#[test]
fn compare_gesture_holds_actual_displayed_pair_once_and_probe_never_holds() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let a = photo(&ctx, 6, 8, [96, 64]);
    let b = photo(&ctx, 6, 31, [96, 64]);
    let ids = [a.texture.id(), b.texture.id()];
    let photos = || [Some(a.clone()), Some(b.clone())];
    let initial = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        6,
        0.0,
        vec![],
    );
    let pointer = quads(&initial, &ids)[0].bounds.center();
    let (_, held) = frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        6,
        0.1,
        vec![Event::PointerMoved(pointer), button(pointer, true)],
    );
    assert!(held.is_none());
    let (_, held) = frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        6,
        0.12,
        vec![button(pointer, false)],
    );
    assert!(
        bench.pin().is_some(),
        "negative Probe arm must actually receive the click"
    );
    assert!(
        held.is_none(),
        "pinning a feature does not suspend live endpoints"
    );

    // Requested replacements have not arrived. Freeze the actual two photos,
    // not those missing requests or stale photos from a previous bracket.
    let stale = photo(&ctx, 5, 120, [192, 128]);
    frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [None, Some(stale.clone())],
        6,
        0.3,
        vec![Event::PointerMoved(pointer), button(pointer, true)],
    );
    let (_, held) = frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [None, Some(stale)],
        6,
        0.32,
        vec![button(pointer, false)],
    );
    assert_eq!(held, Some([8, 31]));
    assert!(bench.a.as_ref().unwrap().pending && bench.b.as_ref().unwrap().pending);

    frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        6,
        0.5,
        vec![button(pointer, true)],
    );
    let moved = pointer + egui::vec2(80.0, 0.0);
    let (_, held) = frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        6,
        0.6,
        vec![Event::PointerMoved(moved)],
    );
    assert_eq!(
        held,
        Some([8, 31]),
        "first actual drag movement must suspend live endpoints"
    );
    let (_, held) = frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        6,
        0.7,
        vec![Event::PointerMoved(moved + egui::vec2(20.0, 0.0))],
    );
    assert!(
        held.is_none(),
        "continuing the same drag does not repeatedly hold the pair"
    );
    let (_, held) = frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        [None, None],
        7,
        0.8,
        vec![button(moved, false)],
    );
    assert!(
        held.is_none(),
        "empty new bracket cannot emit an old pair identity"
    );
}

#[test]
fn detail_footprint_matches_the_actual_sampled_pixels_and_identifies_both_frames() {
    // An off-centre location and unequal texture sizes reject a decorative
    // centre rectangle, switched frame labels, or a lens with no magnification.
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let pin = egui::pos2(0.23, 0.34);
    bench.set_pin(pin);
    let a = photo(&ctx, 2, 17, [96, 64]);
    let b = photo(&ctx, 2, 130, [192, 128]);
    let ids = [a.texture.id(), b.texture.id()];
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        [Some(a), Some(b)],
        2,
        0.0,
        vec![],
    );
    let images = quads(&output, &ids);
    assert_eq!(
        images.len(),
        3,
        "main photo and two actual detail crops must be painted"
    );
    let main = &images[0];
    let detail = &images[1];
    let expected = Rect::from_min_max(
        main.bounds.min + detail.uv.min.to_vec2() * main.bounds.size(),
        main.bounds.min + detail.uv.max.to_vec2() * main.bounds.size(),
    );
    assert!(
        (expected.center() - main.bounds.center()).length() > 100.0,
        "negative control: an always-centred decorative footprint must fail"
    );
    assert!(
        output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Rect(rect) if (rect.stroke.width - 1.5).abs() < 1e-5
            && (rect.rect.min - expected.min).length() < 1e-4
            && (rect.rect.max - expected.max).length() < 1e-4)),
        "the visible footprint must describe the actual ROI read by the A lens"
    );
    let magnification = detail.bounds.width() / detail.uv.width() / main.bounds.width();
    assert!(
        (magnification - 4.0).abs() < 1e-4,
        "default detail is a real fourfold crop"
    );
    let labels = painted_labels(&output);
    assert!(labels.iter().any(|text| text == "Detail · 4×"));
    assert!(
        labels
            .iter()
            .any(|text| text == "A · frame 18   B · frame 131"),
        "the sampled area identifies both actual frame textures"
    );
    assert!(labels.iter().any(|text| text.starts_with("A · frame 18 ·")));
    assert!(
        labels
            .iter()
            .any(|text| text.starts_with("B · frame 131 ·"))
    );
}

#[test]
fn detail_lens_hit_does_not_repin_the_photo_but_an_image_hit_does() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let pin = egui::pos2(0.2, 0.34);
    bench.set_pin(pin);
    let a = photo(&ctx, 2, 7, [96, 64]);
    let b = photo(&ctx, 2, 12, [192, 128]);
    let ids = [a.texture.id(), b.texture.id()];
    let photos = || [Some(a.clone()), Some(b.clone())];
    let output = frame(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        2,
        0.0,
        vec![],
    );
    let images = quads(&output, &ids);
    let lens_point = images[1].bounds.center();
    for (time, events) in [
        (
            0.1,
            vec![Event::PointerMoved(lens_point), button(lens_point, true)],
        ),
        (0.12, vec![button(lens_point, false)]),
    ] {
        frame(
            &ctx,
            &mut bench,
            WorkbenchMode::Probe,
            photos(),
            2,
            time,
            events,
        );
    }
    assert_eq!(
        bench.pin(),
        Some(pin),
        "touching an enlarged crop must not select the pixels behind it"
    );
    let next = egui::pos2(0.74, 0.28);
    let photo_point = images[0].bounds.min + next.to_vec2() * images[0].bounds.size();
    for (time, events) in [
        (
            0.2,
            vec![Event::PointerMoved(photo_point), button(photo_point, true)],
        ),
        (0.22, vec![button(photo_point, false)]),
    ] {
        frame(
            &ctx,
            &mut bench,
            WorkbenchMode::Probe,
            photos(),
            2,
            time,
            events,
        );
    }
    assert!(
        (bench.pin().unwrap() - next).length() < 1e-5,
        "positive control: the same pointer stream must move the sample when it hits the photo"
    );
}

#[test]
fn compact_detail_layout_keeps_lenses_out_of_the_sample_and_difference_has_a_grab_handle() {
    let ctx = Context::default();
    let mut bench = Workbench::default();
    let pin = egui::pos2(0.18, 0.86);
    bench.set_pin(pin);
    let a = photo(&ctx, 2, 17, [96, 64]);
    let b = photo(&ctx, 2, 130, [192, 128]);
    let ids = [a.texture.id(), b.texture.id()];
    let photos = || [Some(a.clone()), Some(b.clone())];
    let size = egui::vec2(360.0, 280.0);
    let viewport = Rect::from_min_size(Pos2::ZERO, size);
    let (output, _) = sized_frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Probe,
        photos(),
        2,
        0.0,
        vec![],
        size,
    );
    let images = quads(&output, &ids);
    let anchor = images[0].bounds.min + pin.to_vec2() * images[0].bounds.size();
    for lens in &images[1..] {
        assert!(viewport.contains_rect(lens.bounds));
        assert!(
            lens.bounds.top() >= 38.0 && lens.bounds.bottom() < anchor.y,
            "lower-photo inspection moves both lenses above the actual sampled feature"
        );
    }
    let (difference, _) = sized_frame_with_hold(
        &ctx,
        &mut bench,
        WorkbenchMode::Compare,
        photos(),
        2,
        0.1,
        vec![],
        size,
    );
    let labels = painted_labels(&difference);
    assert!(labels.iter().any(|text| text == "Slide to compare"));
    assert!(labels.iter().any(|text| text.starts_with("A · frame 18 ·")));
    assert!(
        labels
            .iter()
            .any(|text| text.starts_with("B · frame 131 ·"))
    );
    assert!(
        difference.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Rect(rect) if (rect.rect.width() - 34.0).abs() < 1e-4
            && (rect.rect.height() - 44.0).abs() < 1e-4
            && viewport.contains_rect(rect.rect))),
        "a visible two-direction grab handle must be painted"
    );
}
