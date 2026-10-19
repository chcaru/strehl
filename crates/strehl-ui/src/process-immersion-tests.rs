//! Independent interaction witnesses: use painted image geometry and real
//! pointer events, rather than calling the coordinate helpers under test.
use super::*;
use crate::{
    pipeline::{DiagnosticScope, DiagnosticSurface, PipelineProgress},
    process_space::Surface,
};
use std::sync::Arc;

fn texture(ctx: &egui::Context, name: &str) -> TextureHandle {
    ctx.load_texture(
        name,
        egui::ColorImage::filled([12, 8], Color32::GRAY),
        egui::TextureOptions::NEAREST,
    )
}

fn packet(kind: DiagnosticKind, sequence: u64, folded: usize, middle: u8) -> DiagnosticSurface {
    let mask = matches!(
        kind,
        DiagnosticKind::GateSupport | DiagnosticKind::Averaging
    );
    DiagnosticSurface {
        sequence,
        frame: folded + 1,
        level: if mask { 2 } else { 3 },
        kind,
        scope: if kind == DiagnosticKind::GateSupport {
            DiagnosticScope::Frame
        } else {
            DiagnosticScope::Stack
        },
        scale: DiagnosticScale::Linear,
        width: 12,
        height: 8,
        min: 0.0,
        max: if mask { 1.0 } else { 255.0 },
        pixels: Arc::from(
            (0..96)
                .map(|index| match index % 3 {
                    0 => 0,
                    1 if !mask => middle,
                    _ => 255,
                })
                .collect::<Vec<_>>(),
        ),
        folded,
    }
}

fn surface<'a>(packet: &'a DiagnosticSurface, texture: &'a TextureHandle) -> Surface<'a> {
    Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: packet.level,
        texture,
        frame: (packet.scope == DiagnosticScope::Frame).then_some(packet.frame),
        meta: Some(SurfaceMeta {
            sequence: packet.sequence,
            kind: packet.kind,
            scale: packet.scale,
            min: packet.min,
            max: packet.max,
            samples: [packet.width, packet.height],
            folded: packet.folded,
        }),
        packet: Some(packet),
    }
}

fn progress() -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.bands = Some(7);
    progress.analysis_size = Some([901, 601]);
    progress
}

fn input(progress: &PipelineProgress) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: 12,
        selected: 2,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}

const SIZE: [f32; 2] = [1400.0, 730.0];

fn draw(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, SIZE.into())),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.show(ui, ui.max_rect(), &input, &mut Response::default());
                });
        },
    )
}

#[derive(Clone, Copy, Debug)]
struct Image {
    id: egui::TextureId,
    bounds: Rect,
    uv: Rect,
    alpha: u8,
}

fn images(output: &egui::FullOutput) -> Vec<Image> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh)
                if mesh.texture_id != egui::TextureId::default() && !mesh.vertices.is_empty() =>
            {
                Some(Image {
                    id: mesh.texture_id,
                    bounds: Rect::from_points(
                        &mesh
                            .vertices
                            .iter()
                            .map(|vertex| vertex.pos)
                            .collect::<Vec<_>>(),
                    ),
                    uv: Rect::from_points(
                        &mesh
                            .vertices
                            .iter()
                            .map(|vertex| vertex.uv)
                            .collect::<Vec<_>>(),
                    ),
                    alpha: mesh.vertices[0].color.a(),
                })
            }
            _ => None,
        })
        .collect()
}

fn button(point: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: point,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

fn near(actual: Rect, expected: Rect) {
    assert!(
        actual.min.distance(expected.min) < 0.002 && actual.max.distance(expected.max) < 0.002,
        "painted {actual:?}, expected {expected:?}"
    );
}
fn lens_samples(
    output: &egui::FullOutput,
    field: &ProcessTheater,
    images: &[Image],
    aperture: Rect,
) {
    for (image, kind) in images
        .iter()
        .zip([DiagnosticKind::GateSupport, DiagnosticKind::Averaging])
    {
        let packet = field.observation(kind).unwrap().packet.as_ref().unwrap();
        crate::process_sample_glyphs::assert_painted_samples(
            output,
            image.bounds,
            aperture,
            packet,
            [901, 601],
        );
    }
}

fn seed_lenses(field: &mut ProcessTheater, ctx: &egui::Context, progress: &PipelineProgress) {
    let packets = [
        packet(DiagnosticKind::GateSupport, 1, 1, 0),
        packet(DiagnosticKind::Averaging, 2, 3, 0),
        packet(DiagnosticKind::Preview, 3, 3, 80),
    ];
    let textures: [_; 3] = std::array::from_fn(|i| texture(ctx, &format!("immersion-map-{i}")));
    let surfaces: [_; 3] = std::array::from_fn(|i| surface(&packets[i], &textures[i]));
    let _ = draw(
        field,
        ctx,
        Input {
            surfaces: &surfaces,
            ..input(progress)
        },
        0.0,
        vec![],
    );
    field.level = 2;
    let _ = draw(field, ctx, input(progress), 0.5, vec![]);
}

#[test]
fn zoomed_photo_click_moves_both_real_lens_crops_and_the_photo_locator_to_one_point() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    seed_lenses(&mut field, &ctx, &progress);
    field.zoom = 2.0;
    field.pan = egui::vec2(13.0, -17.0);
    let painted = draw(&mut field, &ctx, input(&progress), 0.6, vec![]);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
    let photo_id = field.hero.as_ref().unwrap().plate.texture.id();
    let photograph = images(&painted)
        .into_iter()
        .find(|image| image.id == photo_id && image.bounds.intersects(layout.hero))
        .unwrap();
    assert!(
        photograph.bounds.width() > layout.hero.width(),
        "fixture must actually zoom beyond the aperture"
    );
    let expected_pin = egui::pos2(0.61, 0.43);
    let point = photograph.bounds.min + photograph.bounds.size() * expected_pin.to_vec2();
    assert!(layout.hero.shrink(36.0).contains(point));
    let _ = draw(
        &mut field,
        &ctx,
        input(&progress),
        0.7,
        vec![egui::Event::PointerMoved(point), button(point, true)],
    );
    let _ = draw(
        &mut field,
        &ctx,
        input(&progress),
        0.73,
        vec![button(point, false)],
    );
    assert!(field.pin.distance(expected_pin) < 0.0001);
    assert_eq!(field.zoom, 2.0, "a single pin click cannot reset the zoom");
    let during = draw(&mut field, &ctx, input(&progress), 0.8, vec![]);
    let shared = field.scales.aperture();
    assert!(
        shared.width() > 0.25 && shared.width() < 1.0,
        "the fixture must witness the shared zoom reveal"
    );
    let revealing: Vec<_> = images(&during)
        .into_iter()
        .filter(|image| layout.contributions.contains_rect(image.bounds))
        .collect();
    assert_eq!(revealing.len(), 2);
    lens_samples(&during, &field, &revealing, shared);
    for image in revealing {
        near(image.uv, shared);
    }
    let after = draw(&mut field, &ctx, input(&progress), 1.05, vec![]);
    let expected_uv = Rect::from_min_max(egui::pos2(0.485, 0.305), egui::pos2(0.735, 0.555));
    let lens_images: Vec<_> = images(&after)
        .into_iter()
        .filter(|image| layout.contributions.contains_rect(image.bounds))
        .collect();
    assert_eq!(
        lens_images.len(),
        2,
        "both actual photo crops remain beneath sparse registered observations"
    );
    assert_eq!(
        lens_images
            .iter()
            .filter(|image| image.id == photo_id)
            .count(),
        2
    );
    lens_samples(&after, &field, &lens_images, expected_uv);
    for image in lens_images {
        near(image.uv, expected_uv);
    }
    let expected_locator = Rect::from_min_max(
        photograph.bounds.min + expected_uv.min.to_vec2() * photograph.bounds.size(),
        photograph.bounds.min + expected_uv.max.to_vec2() * photograph.bounds.size(),
    );
    assert!(
        after.shapes.iter().any(|shape| match &shape.shape {
            egui::Shape::Rect(mark) =>
                mark.rect.min.distance(expected_locator.min) < 0.002
                    && mark.rect.max.distance(expected_locator.max) < 0.002
                    && mark.stroke.color.a() > 0,
            _ => false,
        }),
        "the locator must use the same crop in the zoomed photograph"
    );
}

#[test]
fn lens_drag_clamps_at_the_real_edge_and_stationary_or_release_frames_cannot_recenter_it() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    seed_lenses(&mut field, &ctx, &progress);
    field.pin = egui::pos2(0.97, 0.02);
    field.scales.set_view(field.pin, 4.0);
    let painted = draw(&mut field, &ctx, input(&progress), 0.6, vec![]);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
    let photo_id = field.hero.as_ref().unwrap().plate.texture.id();
    let lens = images(&painted)
        .into_iter()
        .find(|image| image.id == photo_id && layout.contributions.contains_rect(image.bounds))
        .unwrap();
    let start = lens.bounds.center();
    let target = start + lens.bounds.size() * egui::vec2(-0.2, 0.15);
    assert!(
        start.distance(target) > 8.0,
        "fixture must exceed the native drag threshold"
    );
    let _ = draw(
        &mut field,
        &ctx,
        input(&progress),
        0.7,
        vec![egui::Event::PointerMoved(start), button(start, true)],
    );
    let _ = draw(
        &mut field,
        &ctx,
        input(&progress),
        0.8,
        vec![egui::Event::PointerMoved(target)],
    );
    assert_eq!(field.pin, egui::pos2(0.875, 0.125));
    let _ = draw(&mut field, &ctx, input(&progress), 0.9, vec![]);
    assert_eq!(
        field.pin,
        egui::pos2(0.875, 0.125),
        "holding still cannot reset a relative drag"
    );
    let _ = draw(
        &mut field,
        &ctx,
        input(&progress),
        1.0,
        vec![button(target, false)],
    );
    assert_eq!(
        field.pin,
        egui::pos2(0.875, 0.125),
        "drag release cannot become an absolute click"
    );
    let settled = draw(&mut field, &ctx, input(&progress), 1.1, vec![]);
    let lens_images: Vec<_> = images(&settled)
        .into_iter()
        .filter(|image| layout.contributions.contains_rect(image.bounds))
        .collect();
    assert_eq!(lens_images.len(), 2);
    lens_samples(
        &settled,
        &field,
        &lens_images,
        Rect::from_min_max(egui::pos2(0.75, 0.0), egui::pos2(1.0, 0.25)),
    );
    for image in lens_images {
        near(
            image.uv,
            Rect::from_min_max(egui::pos2(0.75, 0.0), egui::pos2(1.0, 0.25)),
        );
    }
}

#[test]
fn rapid_real_revisions_stay_with_the_adopted_photo_and_cannot_enter_the_tiff_transition() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = progress();
    let transport = texture(&ctx, "immersion-preview-transport");
    let packets = [
        packet(DiagnosticKind::Preview, 100, 1, 80),
        packet(DiagnosticKind::Preview, 101, 2, 120),
        packet(DiagnosticKind::Preview, 102, 3, 60),
    ];
    let deliver = |field: &mut ProcessTheater, index: usize, time: f64| {
        let surfaces = [surface(&packets[index], &transport)];
        draw(
            field,
            &ctx,
            Input {
                surfaces: &surfaces,
                ..input(&progress)
            },
            time,
            vec![],
        )
    };
    let _ = deliver(&mut field, 0, 0.0);
    let first_id = field.hero.as_ref().unwrap().plate.texture.id();
    let _ = draw(&mut field, &ctx, input(&progress), 0.5, vec![]);
    let _ = deliver(&mut field, 1, 0.6);
    let second_id = field.hero.as_ref().unwrap().plate.texture.id();
    assert_ne!(first_id, second_id);
    assert_eq!(field.hero.as_ref().unwrap().alpha, 0.0);
    let second = draw(&mut field, &ctx, input(&progress), 0.7, vec![]);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
    let contours = |output: &egui::FullOutput, photos: &[egui::TextureId]| -> Vec<Image> {
        images(output)
            .into_iter()
            .filter(|image| layout.hero.contains_rect(image.bounds) && !photos.contains(&image.id))
            .collect()
    };
    let second_contours = contours(&second, &[first_id, second_id]);
    assert_eq!(
        second_contours.len(),
        1,
        "fixture must actually paint a measured contour"
    );
    assert!((1..255).contains(&second_contours[0].alpha));
    let second_contour = second_contours[0].id;
    let waiting = deliver(&mut field, 2, 0.75);
    assert_eq!(field.hero.as_ref().unwrap().plate.sequence, 101);
    assert_eq!(field.revisions.latest().unwrap().sequence, 102);
    assert!(
        field.hero_pending,
        "third preview must truly arrive during the previous reveal"
    );
    assert_eq!(
        contours(&waiting, &[first_id, second_id])
            .iter()
            .map(|image| image.id)
            .collect::<Vec<_>>(),
        [second_contour]
    );
    assert!(
        waiting.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Text(text) if text.galley.text().starts_with("1 → 2 inputs"))),
        "the displayed revision must not jump to unseen latest pixels"
    );
    let _ = draw(&mut field, &ctx, input(&progress), 0.99, vec![]);
    let _ = draw(&mut field, &ctx, input(&progress), 1.0, vec![]);
    assert_eq!(field.hero.as_ref().unwrap().plate.sequence, 102);
    let third_id = field.hero.as_ref().unwrap().plate.texture.id();
    let third = draw(&mut field, &ctx, input(&progress), 1.1, vec![]);
    let third_contours = contours(&third, &[first_id, second_id, third_id]);
    assert_eq!(
        third_contours.len(),
        2,
        "the two real contours crossfade with their photo generations"
    );
    assert!(
        third_contours
            .iter()
            .all(|image| (1..255).contains(&image.alpha))
    );
    assert!(
        third_contours
            .iter()
            .any(|image| image.id == second_contour)
    );
    let contour_ids: Vec<_> = third_contours.iter().map(|image| image.id).collect();
    let tiff = texture(&ctx, "immersion-owned-final-tiff");
    progress.mark_complete();
    for (index, time) in [1.11, 1.4, 1.41, 1.6, 1.9].into_iter().enumerate() {
        let output = draw(
            &mut field,
            &ctx,
            Input {
                output: (index == 0).then_some(&tiff),
                ..input(&progress)
            },
            time,
            vec![],
        );
        assert!(
            !images(&output)
                .iter()
                .any(|image| contour_ids.contains(&image.id)),
            "neither contour can survive owned TIFF arrival, including deferred and fading frames"
        );
        if index == 0 {
            assert!(field.hero_pending);
            assert_eq!(field.hero.as_ref().unwrap().plate.sequence, 102);
        }
        if index == 4 {
            assert_eq!(field.hero.as_ref().unwrap().plate.kind, 3);
            assert!(images(&output).iter().any(|image| image.id == tiff.id()
                && image.alpha == 255
                && layout.hero.contains_rect(image.bounds)));
            assert!(
                !field.transitioning(),
                "the retained result must finish without more decoder input"
            );
        }
    }
}
