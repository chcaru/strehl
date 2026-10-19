use super::*;
use crate::{pipeline::PipelineProgress, workbench::SourcePhoto};
use egui::{FullOutput, Pos2, TextureId};

fn input<'a>(progress: &'a PipelineProgress, photos: &'a [SourcePhoto]) -> Input<'a> {
    Input {
        epoch: 1,
        progress,
        frame_count: 259,
        selected: 0,
        inspected_pair: None,
        photos,
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}
fn area() -> Rect {
    Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(1056.0, 58.0))
}
fn draw(
    axis: &mut CaptureAxis,
    ctx: &egui::Context,
    input: Input<'_>,
    rect: Rect,
    time: f64,
    events: Vec<egui::Event>,
) -> (Response, FullOutput) {
    let mut response = Response::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1400.0, 180.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| axis.show(ui, rect, &input, &mut response));
        },
    );
    (response, output)
}
fn photo(ctx: &egui::Context, epoch: u64, index: usize, name: &str) -> SourcePhoto {
    SourcePhoto {
        epoch,
        index,
        aperture: [160, 120],
        texture: ctx.load_texture(
            name,
            egui::ColorImage::new([160, 120], vec![Color32::from_rgb(180, 90, 40); 160 * 120]),
            egui::TextureOptions::LINEAR,
        ),
    }
}
fn image_mesh(output: &FullOutput, id: TextureId) -> Option<&egui::epaint::Mesh> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Mesh(mesh) if mesh.texture_id == id => Some(&**mesh),
        _ => None,
    })
}
fn bounds(output: &FullOutput, id: TextureId) -> Rect {
    let mesh = image_mesh(output, id).expect("actual contact image was not painted");
    Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>())
}
fn captions(output: &FullOutput) -> BTreeMap<String, Pos2> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some((
                text.galley.text().to_owned(),
                text.visual_bounding_rect().center(),
            )),
            _ => None,
        })
        .collect()
}
fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}
fn click(
    axis: &mut CaptureAxis,
    ctx: &egui::Context,
    input: Input<'_>,
    at: Pos2,
    time: f64,
) -> Response {
    draw(
        axis,
        ctx,
        input,
        area(),
        time,
        vec![egui::Event::PointerMoved(at), button(at, true)],
    );
    draw(
        axis,
        ctx,
        input,
        area(),
        time + 0.1,
        vec![button(at, false)],
    )
    .0
}

#[test]
fn contact_meshes_and_captions_stay_fixed_across_arrival_eviction_and_distant_pairs() {
    let ctx = egui::Context::default();
    let mut axis = CaptureAxis::default();
    let mut progress = PipelineProgress::default();
    let (_, empty) = draw(&mut axis, &ctx, input(&progress, &[]), area(), 0.0, vec![]);
    let indices = axis.indices();
    assert!((2..=16).contains(&indices.len()));
    assert_eq!(indices.first(), Some(&0));
    assert_eq!(indices.last(), Some(&258));
    assert!(indices.windows(2).all(|pair| pair[0] < pair[1]));
    assert!(
        !indices.contains(&1),
        "unrelated-index control must not accidentally be an anchor"
    );
    let captions_before = captions(&empty);
    assert_eq!(
        captions_before.len(),
        indices.len(),
        "every pending contact needs a visible capture identity"
    );
    let left = photo(&ctx, 1, 0, "fixed-left");
    let middle = photo(&ctx, 1, indices[indices.len() / 2], "fixed-middle");
    let right = photo(&ctx, 1, 258, "late-right");
    let unrelated = photo(&ctx, 1, 1, "unrelated-contact");
    let first = [left.clone(), middle.clone()];
    let (_, ready) = draw(
        &mut axis,
        &ctx,
        input(&progress, &first),
        area(),
        0.1,
        vec![],
    );
    let left_bounds = bounds(&ready, left.texture.id());
    let middle_bounds = bounds(&ready, middle.texture.id());
    assert_eq!(left_bounds.size(), egui::vec2(64.0, 34.0));
    progress.processing_frame = Some(257);
    progress.alignment_current_pair = Some([1, 257]);
    let arrivals = [
        right.clone(),
        unrelated.clone(),
        middle.clone(),
        left.clone(),
    ];
    let changed = Input {
        selected: 201,
        ..input(&progress, &arrivals)
    };
    let (_, late) = draw(&mut axis, &ctx, changed, area(), 0.2, vec![]);
    assert_eq!(bounds(&late, left.texture.id()), left_bounds);
    assert_eq!(bounds(&late, middle.texture.id()), middle_bounds);
    assert!(
        image_mesh(&late, right.texture.id()).is_some(),
        "late real contact must fill its reserved slot"
    );
    assert!(
        image_mesh(&late, unrelated.texture.id()).is_none(),
        "available previews cannot choose capture slots"
    );
    assert_eq!(captions(&late), captions_before);
    let (_, evicted) = draw(
        &mut axis,
        &ctx,
        Input {
            selected: 258,
            inspected_pair: Some([0, 258]),
            ..input(&progress, &[])
        },
        area(),
        0.3,
        vec![],
    );
    assert_eq!(bounds(&evicted, left.texture.id()), left_bounds);
    assert_eq!(bounds(&evicted, middle.texture.id()), middle_bounds);
    assert_eq!(
        bounds(&evicted, right.texture.id()),
        bounds(&late, right.texture.id())
    );
    assert_eq!(captions(&evicted), captions_before);
    assert_eq!(axis.indices(), indices);
}

#[test]
fn native_photo_permutations_have_identical_contact_geometry_and_epoch_clears_cache() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let photos = [
        photo(&ctx, 1, 0, "order-a"),
        photo(&ctx, 1, 129, "order-unanchored"),
        photo(&ctx, 1, 258, "order-z"),
    ];
    let mut first = CaptureAxis::default();
    let (_, a) = draw(
        &mut first,
        &ctx,
        input(&progress, &photos),
        area(),
        0.0,
        vec![],
    );
    let mut second = CaptureAxis::default();
    let reverse = [photos[2].clone(), photos[1].clone(), photos[0].clone()];
    let (_, b) = draw(
        &mut second,
        &ctx,
        input(&progress, &reverse),
        area(),
        0.1,
        vec![],
    );
    assert_eq!(first.indices(), second.indices());
    for p in [&photos[0], &photos[2]] {
        assert_eq!(bounds(&a, p.texture.id()), bounds(&b, p.texture.id()));
    }
    let (_, new_epoch) = draw(
        &mut first,
        &ctx,
        Input {
            epoch: 2,
            ..input(&progress, &photos)
        },
        area(),
        0.2,
        vec![],
    );
    assert!(image_mesh(&new_epoch, photos[0].texture.id()).is_none());
    assert!(image_mesh(&new_epoch, photos[2].texture.id()).is_none());
    assert!(
        first.contacts.is_empty(),
        "old native contacts cannot cross capture epochs"
    );
    assert_eq!(captions(&new_epoch), captions(&a));
    let replacement = photo(&ctx, 2, 0, "new-epoch-contact");
    let (_, new_ready) = draw(
        &mut first,
        &ctx,
        Input {
            epoch: 2,
            ..input(&progress, std::slice::from_ref(&replacement))
        },
        area(),
        0.3,
        vec![],
    );
    assert_eq!(
        bounds(&new_ready, replacement.texture.id()),
        bounds(&a, photos[0].texture.id())
    );
}

#[test]
fn inspection_previews_never_fill_contacts_and_native_crop_uses_actual_texture_aspect() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let inspection = photo(&ctx, 1, 0, "canonical-imposter");
    let unrelated = photo(&ctx, 1, 1, "available-but-not-anchor");
    let mut axis = CaptureAxis::default();
    let (_, pending) = draw(
        &mut axis,
        &ctx,
        Input {
            inspection_photos: std::slice::from_ref(&inspection),
            ..input(&progress, std::slice::from_ref(&unrelated))
        },
        area(),
        0.0,
        vec![],
    );
    assert!(
        image_mesh(&pending, inspection.texture.id()).is_none(),
        "canonical detail is not a native contact substitute"
    );
    assert!(image_mesh(&pending, unrelated.texture.id()).is_none());
    let mut native = photo(&ctx, 1, 0, "actual-native-contact");
    native.aperture = [7008, 4672]; // The strip must use native pixels, never this canonical aperture.
    let (_, ready) = draw(
        &mut axis,
        &ctx,
        Input {
            inspection_photos: std::slice::from_ref(&inspection),
            ..input(&progress, std::slice::from_ref(&native))
        },
        area(),
        0.1,
        vec![],
    );
    let mesh = image_mesh(&ready, native.texture.id()).unwrap();
    let image = Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
    let uv = Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>());
    assert!(
        (image.width() / (uv.width() * 160.0) - image.height() / (uv.height() * 120.0)).abs()
            < 1e-5,
        "native crop must preserve uniform pixel scale"
    );
    assert!(
        uv.height() < 1.0,
        "4:3 native contact must actually exercise center cover-crop"
    );
    assert!(image_mesh(&ready, inspection.texture.id()).is_none());
    assert_eq!(captions(&pending), captions(&ready));
}

#[test]
fn actual_pointer_contact_and_continuous_axis_select_capture_identities() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let mut axis = CaptureAxis::default();
    let (_, output) = draw(&mut axis, &ctx, input(&progress, &[]), area(), 0.0, vec![]);
    let anchors = axis.indices();
    let chosen = anchors[anchors.len() / 2];
    let at = captions(&output)[&format!("{:03}", chosen + 1)];
    assert_eq!(
        click(&mut axis, &ctx, input(&progress, &[]), at, 0.1).selected,
        Some(chosen),
        "pending contact caption must select its promised actual frame"
    );
    assert_eq!(
        click(
            &mut axis,
            &ctx,
            input(&progress, &[]),
            egui::pos2(area().center().x - 10.0, area().top() + 4.0),
            0.4
        )
        .selected,
        Some(126),
        "axis must support exact capture selection between contact anchors"
    );
    assert!(
        !anchors.contains(&126),
        "continuous-axis control must exercise an unpictured capture"
    );
}

fn ticks(output: &FullOutput, colour: Color32, top: f32, bottom: f32) -> Vec<f32> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, stroke }
                if stroke.color == colour && points[0].y == top && points[1].y == bottom =>
            {
                Some(points[0].x)
            }
            _ => None,
        })
        .collect()
}

#[test]
fn read_pyramid_and_processed_marks_are_only_actual_sparse_identities_and_remain_additive() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=align-phase name=planes total=10 frames=10\nSTREHL_UI_PROGRESS event=align-plane index=6 completed=6 total=10 frames=10\nSTREHL_UI_PROGRESS event=align-phase name=pyramids total=10 frames=10\nSTREHL_UI_PROGRESS event=align-pyramid index=9 completed=6 total=10 frames=10\nSTREHL_UI_PROGRESS event=frame-finished index=2 processed=6 accepted=6 total=10\n");
    let mut axis = CaptureAxis::default();
    let inp = Input {
        frame_count: 10,
        ..input(&progress, &[])
    };
    let (_, first) = draw(&mut axis, &ctx, inp, area(), 0.0, vec![]);
    let raw = ticks(&first, GREEN, area().top() + 0.5, area().top() + 3.0);
    let pyramid = ticks(&first, ACCENT, area().top() + 5.0, area().top() + 7.5);
    let processed = ticks(&first, GREEN, area().top() + 9.0, area().top() + 11.0);
    assert_eq!(
        raw.len(),
        1,
        "six reported reads cannot invent six capture ticks"
    );
    assert_eq!(
        pyramid.len(),
        1,
        "six prepared scales cannot invent six capture ticks"
    );
    assert_eq!(
        processed.len(),
        1,
        "six processed captures cannot invent a prefix"
    );
    assert!(
        processed[0] < raw[0] && raw[0] < pyramid[0],
        "marks must land on actual capture identities 2,6,9"
    );
    progress.ingest("STREHL_UI_PROGRESS event=frame-started index=5 total=10\nSTREHL_UI_PROGRESS event=frame-finished index=8 processed=7 accepted=7 total=10\nSTREHL_UI_PROGRESS event=stage name=render total=10\n");
    let (_, later) = draw(
        &mut axis,
        &ctx,
        Input {
            frame_count: 10,
            selected: 9,
            ..input(&progress, &[])
        },
        area(),
        0.1,
        vec![],
    );
    assert_eq!(
        ticks(&later, GREEN, area().top() + 0.5, area().top() + 3.0),
        raw
    );
    assert_eq!(
        ticks(&later, ACCENT, area().top() + 5.0, area().top() + 7.5),
        pyramid
    );
    let completed = ticks(&later, GREEN, area().top() + 9.0, area().top() + 11.0);
    assert_eq!(
        completed.len(),
        2,
        "started capture5 cannot be shown as processed"
    );
    assert_eq!(completed[0], processed[0]);
    assert!(completed[1] > raw[0] && completed[1] < pyramid[0]);
}

#[test]
fn slot_budget_and_cache_follow_only_capture_size_epoch_and_width() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let mut axis = CaptureAxis::default();
    let wide = Rect::from_min_size(area().min, egui::vec2(1300.0, 58.0));
    draw(&mut axis, &ctx, input(&progress, &[]), wide, 0.0, vec![]);
    assert_eq!(axis.indices().len(), 16);
    let photos: Vec<_> = axis
        .indices()
        .into_iter()
        .map(|index| photo(&ctx, 1, index, &format!("budget-{index}")))
        .collect();
    draw(
        &mut axis,
        &ctx,
        input(&progress, &photos),
        wide,
        0.1,
        vec![],
    );
    assert_eq!(axis.contacts.len(), 16);
    let narrow = Rect::from_min_size(area().min, egui::vec2(456.0, 58.0));
    draw(&mut axis, &ctx, input(&progress, &[]), narrow, 0.2, vec![]);
    assert!(axis.contacts.len() <= axis.indices().len());
    assert_eq!(axis.indices().first(), Some(&0));
    assert_eq!(axis.indices().last(), Some(&258));
    draw(
        &mut axis,
        &ctx,
        Input {
            frame_count: 1,
            ..input(&progress, &[])
        },
        narrow,
        0.3,
        vec![],
    );
    assert_eq!(axis.indices(), vec![0]);
    assert!(
        axis.contacts.is_empty(),
        "a changed capture population cannot reuse prior native identities"
    );
    draw(
        &mut axis,
        &ctx,
        Input {
            frame_count: 0,
            ..input(&progress, &[])
        },
        narrow,
        0.4,
        vec![],
    );
    assert!(axis.indices().is_empty());
}

#[test]
fn processed_marks_have_their_own_rail_above_images_and_actual_caption_glyphs() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    for index in [0, 129, 258] {
        progress
            .frame_observations
            .insert(index, FrameObservation::Processed);
    }
    let photos = [
        photo(&ctx, 1, 0, "mark-caption-first"),
        photo(&ctx, 1, 129, "mark-caption-middle"),
        photo(&ctx, 1, 258, "mark-caption-last"),
    ];
    let mut axis = CaptureAxis::default();
    let (_, output) = draw(
        &mut axis,
        &ctx,
        input(&progress, &photos),
        area(),
        0.0,
        vec![],
    );
    let glyph_bounds: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.visual_bounding_rect()),
            _ => None,
        })
        .collect();
    assert_eq!(
        glyph_bounds.len(),
        axis.indices().len(),
        "every pending and ready contact must actually exercise a visible ordinal"
    );
    let mark_bounds: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, stroke }
                if stroke.color == GREEN && stroke.width == 1.2 =>
            {
                Some(Rect::from_two_pos(points[0], points[1]).expand(stroke.width * 0.5))
            }
            _ => None,
        })
        .collect();
    assert_eq!(
        mark_bounds.len(),
        3,
        "the fixture must actually paint processed marks under first/middle/last ordinals"
    );
    for mark in &mark_bounds {
        for glyph in &glyph_bounds {
            assert!(
                mark.bottom() < glyph.top(),
                "processed mark reached the caption glyph row: {mark:?} / {glyph:?}"
            );
            assert!(
                !mark.intersects(*glyph),
                "processed mark crosses an actual painted ordinal"
            );
        }
        for photo in &photos {
            assert!(
                mark.bottom() < bounds(&output, photo.texture.id()).top(),
                "processed marks need their own rail above actual contact images"
            );
        }
    }
    // The retired bottom row could not pass the actual above-image contract.
    let old_bottom = area().bottom() - 0.5 + 1.2 * 0.5;
    assert!(old_bottom > bounds(&output, photos[0].texture.id()).top());
}
