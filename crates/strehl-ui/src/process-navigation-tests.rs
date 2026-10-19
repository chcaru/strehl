//! Independent v16 navigation witnesses. Expected coordinates come from the
//! painted photo/map meshes and real pointer events, not navigation helpers.
use super::*;
use crate::{
    pipeline::{DiagnosticScope, DiagnosticSurface, PipelineProgress},
    process_space::Surface,
    workbench::SourcePhoto,
};

const SIZE: [f32; 2] = [1410.0, 850.0];

struct Fixture {
    progress: PipelineProgress,
    packets: Vec<DiagnosticSurface>,
    textures: Vec<TextureHandle>,
}

impl Fixture {
    #[allow(clippy::field_reassign_with_default)]
    fn new(ctx: &egui::Context) -> Self {
        let mut progress = PipelineProgress::default();
        progress.stage = Stage::Merge;
        progress.analysis_size = Some([131, 99]);
        progress.bands = Some(7);
        let mut packets = Vec::new();
        for level in 0..8 {
            let [width, height] = [
                131usize.div_ceil(1 << level).min(13),
                99usize.div_ceil(1 << level).min(9),
            ];
            for kind in SIGNALS {
                if level == 7
                    && matches!(
                        kind,
                        DiagnosticKind::FocusEnergy | DiagnosticKind::GateFloor
                    )
                {
                    continue;
                }
                let frame = matches!(
                    kind,
                    DiagnosticKind::FocusEnergy
                        | DiagnosticKind::GateFloor
                        | DiagnosticKind::GateSupport
                );
                packets.push(DiagnosticSurface {
                    sequence: packets.len() as u64 + 1,
                    frame: 4,
                    level,
                    kind,
                    scope: if frame {
                        DiagnosticScope::Frame
                    } else {
                        DiagnosticScope::Stack
                    },
                    scale: match kind {
                        DiagnosticKind::FocusEnergy | DiagnosticKind::GateFloor => {
                            DiagnosticScale::Log
                        }
                        DiagnosticKind::Coefficient => DiagnosticScale::Symmetric,
                        _ => DiagnosticScale::Linear,
                    },
                    width,
                    height,
                    min: 0.0,
                    max: 1.0,
                    pixels: (0..width * height)
                        .map(|i| if i % 3 == 0 { 255 } else { 0 })
                        .collect::<Vec<_>>()
                        .into(),
                    folded: if frame { 1 } else { 3 },
                });
            }
        }
        packets.push(DiagnosticSurface {
            sequence: 100,
            frame: 4,
            level: 3,
            kind: DiagnosticKind::Preview,
            scope: DiagnosticScope::Stack,
            scale: DiagnosticScale::Linear,
            width: 13,
            height: 9,
            min: 10.0,
            max: 300.0,
            pixels: (0..117).map(|i| (i * 2) as u8).collect::<Vec<_>>().into(),
            folded: 3,
        });
        let textures = packets
            .iter()
            .map(|packet| texture(ctx, &format!("navigation-{}", packet.sequence)))
            .collect();
        Self {
            progress,
            packets,
            textures,
        }
    }

    fn surfaces(&self) -> Vec<Surface<'_>> {
        self.packets
            .iter()
            .zip(&self.textures)
            .map(|(packet, texture)| Surface {
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
            })
            .collect()
    }
}

fn texture(ctx: &egui::Context, name: &str) -> TextureHandle {
    ctx.load_texture(
        name,
        egui::ColorImage::filled([13, 9], Color32::GRAY),
        egui::TextureOptions::NEAREST,
    )
}

fn input(progress: &PipelineProgress) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: 67,
        selected: 2,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}

fn draw(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (egui::FullOutput, Response) {
    draw_modified(field, ctx, input, time, events, egui::Modifiers::NONE)
}

fn draw_modified(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
    modifiers: egui::Modifiers,
) -> (egui::FullOutput, Response) {
    let mut response = Response::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, SIZE.into())),
            time: Some(time),
            events,
            modifiers,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.show(ui, ui.max_rect(), &input, &mut response);
                });
        },
    );
    (output, response)
}

fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

#[derive(Debug)]
struct Image {
    id: egui::TextureId,
    rect: Rect,
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
                    rect: Rect::from_points(
                        &mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>(),
                    ),
                    uv: Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>()),
                    alpha: mesh.vertices[0].color.a(),
                })
            }
            _ => None,
        })
        .collect()
}

fn close_point(actual: Pos2, expected: Pos2) {
    assert!(
        actual.distance(expected) < 0.0002,
        "actual {actual:?}, expected {expected:?}"
    );
}

fn same_rect(actual: Rect, expected: Rect) {
    assert!(
        actual.min.distance(expected.min) < 0.002 && actual.max.distance(expected.max) < 0.002,
        "painted {actual:?}, expected {expected:?}"
    );
}

fn photo(output: &egui::FullOutput, field: &ProcessTheater) -> Rect {
    let id = field
        .hero
        .as_ref()
        .expect("real coarse photo required")
        .plate
        .texture
        .id();
    images(output)
        .into_iter()
        .filter(|image| image.id == id)
        .max_by(|a, b| a.rect.area().total_cmp(&b.rect.area()))
        .unwrap()
        .rect
}

fn projected(photo: Rect, uv: Rect) -> Rect {
    Rect::from_min_max(
        photo.min + uv.min.to_vec2() * photo.size(),
        photo.min + uv.max.to_vec2() * photo.size(),
    )
}

fn linked_views(output: &egui::FullOutput, fixture: &Fixture, photo: Rect, aperture: Rect) {
    let painted = images(output);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
    let binary = crate::process_sample_glyphs::binary_panes(output, layout.signals);
    assert_eq!(
        binary.len(),
        16,
        "all observed binary panes remain alongside the scalar maps"
    );
    for (packet, texture) in fixture
        .packets
        .iter()
        .zip(&fixture.textures)
        .filter(|(packet, _)| packet.kind != DiagnosticKind::Preview)
    {
        if matches!(
            packet.kind,
            DiagnosticKind::GateSupport | DiagnosticKind::Averaging
        ) {
            assert!(!painted.iter().any(|image| image.id == texture.id()));
            let pane =
                binary[packet.level * 2 + usize::from(packet.kind == DiagnosticKind::Averaging)];
            crate::process_sample_glyphs::assert_painted_samples(
                output,
                pane,
                aperture,
                packet,
                [131, 99],
            );
            continue;
        }
        let map = painted
            .iter()
            .find(|image| image.id == texture.id())
            .unwrap_or_else(|| panic!("missing {:?} level {}", packet.kind, packet.level));
        same_rect(map.uv, aperture);
    }
    let lenses: Vec<_> = painted
        .iter()
        .filter(|image| layout.contributions.contains_rect(image.rect))
        .collect();
    assert!(
        lenses.len() >= 2,
        "both photographic lenses remain under their sparse observations: {lenses:?}"
    );
    for lens in lenses {
        same_rect(lens.uv, aperture);
    }
    let locator = projected(photo, aperture);
    assert!(
        output.shapes.iter().any(|shape| match &shape.shape {
            egui::Shape::Rect(rect) =>
                (rect.stroke.width - 2.6).abs() < 0.001
                    && rect.rect.min.distance(locator.min) < 0.002
                    && rect.rect.max.distance(locator.max) < 0.002,
            _ => false,
        }),
        "the main-photo locator must project the same aperture {locator:?}"
    );
}

fn warm(field: &mut ProcessTheater, ctx: &egui::Context, input: Input<'_>, pin: Pos2, zoom: f32) {
    let _ = draw(field, ctx, input, 0.0, vec![]);
    field.pin = pin;
    field.scales.set_view(pin, zoom);
    let _ = draw(field, ctx, input, 0.4, vec![]);
    let _ = draw(field, ctx, input, 0.6, vec![]);
}

#[test]
fn off_center_box_grab_preserves_all_motion_and_all_linked_apertures_on_a_zoomed_photo() {
    let ctx = egui::Context::default();
    let fixture = Fixture::new(&ctx);
    let surfaces = fixture.surfaces();
    let input = Input {
        surfaces: &surfaces,
        ..input(&fixture.progress)
    };
    let mut field = ProcessTheater::default();
    let center = egui::pos2(0.46, 0.57);
    warm(&mut field, &ctx, input, center, 4.0);
    field.zoom = 1.7;
    field.pan = egui::vec2(-11.0, 17.0);
    let (before, _) = draw(&mut field, &ctx, input, 0.7, vec![]);
    let photo = photo(&before, &field);
    let initial_aperture = field.scales.aperture();
    linked_views(&before, &fixture, photo, initial_aperture);
    let locator = projected(photo, initial_aperture);
    let grab = locator.min + locator.size() * egui::vec2(0.72, 0.23);
    assert!(
        grab.distance(locator.center()) > 10.0,
        "off-center positive control"
    );
    let pan = field.pan;
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(grab), button(grab, true)],
    );
    close_point(field.pin, center);
    for (step, displacement) in [
        egui::vec2(3.0, 0.0),
        egui::vec2(6.0, 0.0),
        egui::vec2(19.0, -12.0),
    ]
    .into_iter()
    .enumerate()
    {
        let (out, response) = draw(
            &mut field,
            &ctx,
            input,
            0.82 + step as f64 * 0.02,
            vec![egui::Event::PointerMoved(grab + displacement)],
        );
        assert_eq!(response.selected, None);
        linked_views(&out, &fixture, photo, field.scales.aperture());
    }
    let expected = center + egui::vec2(19.0, -12.0) / photo.size();
    close_point(field.pin, expected);
    assert_eq!(
        field.pan, pan,
        "grabbing the detail box must not pan the photograph"
    );
    assert_eq!(field.zoom, 1.7);
    let (held, _) = draw(&mut field, &ctx, input, 0.9, vec![]);
    close_point(field.pin, expected);
    let expected_uv = Rect::from_center_size(expected, egui::Vec2::splat(0.25));
    linked_views(&held, &fixture, photo, expected_uv);
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.92,
        vec![button(grab + egui::vec2(19.0, -12.0), false)],
    );
    close_point(field.pin, expected);
    assert_eq!(field.enlarged, None);
}

#[test]
fn dragging_an_edge_clamped_box_can_reverse_immediately_after_overshooting() {
    let ctx = egui::Context::default();
    let fixture = Fixture::new(&ctx);
    let surfaces = fixture.surfaces();
    let input = Input {
        surfaces: &surfaces,
        ..input(&fixture.progress)
    };
    let mut field = ProcessTheater::default();
    warm(&mut field, &ctx, input, egui::pos2(0.875, 0.4), 4.0);
    let (before, _) = draw(&mut field, &ctx, input, 0.7, vec![]);
    let photo = photo(&before, &field);
    let aperture = field.scales.aperture();
    assert_eq!(aperture.right(), 1.0);
    let locator = projected(photo, aperture);
    let grab = locator.min + locator.size() * egui::vec2(0.32, 0.41);
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(grab), button(grab, true)],
    );
    let overshot = grab + egui::vec2(34.0, 0.0);
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.85,
        vec![egui::Event::PointerMoved(overshot)],
    );
    close_point(field.pin, egui::pos2(0.875, 0.4));
    let reversed = overshot - egui::vec2(11.0, 0.0);
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.9,
        vec![egui::Event::PointerMoved(reversed)],
    );
    let expected = egui::pos2(0.875 - 11.0 / photo.width(), 0.4);
    close_point(field.pin, expected);
    let (held, _) = draw(&mut field, &ctx, input, 0.95, vec![]);
    linked_views(
        &held,
        &fixture,
        photo,
        Rect::from_center_size(expected, egui::Vec2::splat(0.25)),
    );
    let _ = draw(&mut field, &ctx, input, 1.0, vec![button(reversed, false)]);
    close_point(field.pin, expected);
}

#[test]
fn wheel_inside_the_box_animates_one_shared_aperture_without_zooming_the_photo() {
    let ctx = egui::Context::default();
    let fixture = Fixture::new(&ctx);
    let surfaces = fixture.surfaces();
    let input = Input {
        surfaces: &surfaces,
        ..input(&fixture.progress)
    };
    let mut field = ProcessTheater::default();
    warm(&mut field, &ctx, input, egui::pos2(0.46, 0.57), 4.0);
    let (before, _) = draw(&mut field, &ctx, input, 0.7, vec![]);
    let photo = photo(&before, &field);
    let locator = projected(photo, field.scales.aperture());
    let anchor = egui::vec2(0.28, 0.66);
    let at = locator.min + locator.size() * anchor;
    let anchored_sample = egui::Pos2::ZERO + (at - photo.min) / photo.size();
    let old_zoom = field.zoom;
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![
            egui::Event::PointerMoved(at),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, 100.0),
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    assert!(
        field.scales.detail_zoom() > 5.0,
        "real wheel input must reach detail zoom"
    );
    assert_eq!(field.zoom, old_zoom);
    let mut intermediate = false;
    for (step, time) in [0.82, 0.87, 0.93, 1.0].into_iter().enumerate() {
        let (out, _) = draw(&mut field, &ctx, input, time, vec![]);
        let aperture = field.scales.aperture();
        linked_views(&out, &fixture, photo, aperture);
        close_point(aperture.min + aperture.size() * anchor, anchored_sample);
        if step < 3
            && aperture.width() < 0.25
            && aperture.width() > field.scales.detail_zoom().recip() + 0.001
        {
            intermediate = true;
        }
        assert_eq!(field.zoom, old_zoom);
    }
    assert!(
        intermediate,
        "fixture must inspect an actual in-between animated aperture"
    );
    let detail_zoom = field.scales.detail_zoom();
    let at = projected(photo, field.scales.aperture()).center();
    let _ = draw_modified(
        &mut field,
        &ctx,
        input,
        1.1,
        vec![
            egui::Event::PointerMoved(at),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, 80.0),
                modifiers: egui::Modifiers::CTRL,
            },
        ],
        egui::Modifiers::CTRL,
    );
    assert!(
        field.zoom > old_zoom + 0.1,
        "Ctrl+wheel must reach photograph zoom even inside the detail box"
    );
    assert_eq!(
        field.scales.detail_zoom(),
        detail_zoom,
        "one wheel event must never zoom both domains"
    );
}

#[test]
fn corner_resize_keeps_the_opposite_corner_fixed_and_respects_both_zoom_limits() {
    let ctx = egui::Context::default();
    let fixture = Fixture::new(&ctx);
    let surfaces = fixture.surfaces();
    let input = Input {
        surfaces: &surfaces,
        ..input(&fixture.progress)
    };
    let mut field = ProcessTheater::default();
    warm(&mut field, &ctx, input, egui::pos2(0.46, 0.57), 4.0);
    let (before, _) = draw(&mut field, &ctx, input, 0.7, vec![]);
    let photo = photo(&before, &field);
    let initial = field.scales.aperture();
    let at = projected(photo, initial).right_bottom();
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(at), button(at, true)],
    );
    // Move equally in physical normalized coordinates, despite the photograph's
    // nonsquare dimensions. This must resize rather than translate the box.
    let shrink = photo.size() * -0.08;
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.85,
        vec![egui::Event::PointerMoved(at + shrink)],
    );
    assert!((field.scales.detail_zoom() - 1.0 / 0.17).abs() < 0.001);
    let expected = Rect::from_min_size(initial.min, egui::Vec2::splat(0.17));
    let (held, _) = draw(&mut field, &ctx, input, 0.9, vec![]);
    linked_views(&held, &fixture, photo, expected);
    close_point(field.pin, expected.center());
    assert_eq!(field.pan, Vec2::ZERO);
    assert_eq!(field.zoom, 1.0);
    let tiny = at + photo.size() * -0.7;
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.95,
        vec![egui::Event::PointerMoved(tiny)],
    );
    assert_eq!(field.scales.detail_zoom(), 16.0);
    let (minimum, _) = draw(&mut field, &ctx, input, 1.0, vec![]);
    linked_views(
        &minimum,
        &fixture,
        photo,
        Rect::from_min_size(initial.min, egui::Vec2::splat(1.0 / 16.0)),
    );
    let huge = tiny + photo.size();
    let _ = draw(
        &mut field,
        &ctx,
        input,
        1.05,
        vec![egui::Event::PointerMoved(huge)],
    );
    assert_eq!(field.scales.detail_zoom(), 2.0);
    let (maximum, _) = draw(&mut field, &ctx, input, 1.1, vec![]);
    let expected = Rect::from_min_size(initial.min, egui::Vec2::splat(0.5));
    linked_views(&maximum, &fixture, photo, expected);
    let _ = draw(&mut field, &ctx, input, 1.15, vec![button(huge, false)]);
    close_point(field.pin, expected.center());
}

#[test]
fn new_live_pixels_do_not_interrupt_a_held_box_and_final_arrival_cancels_its_domain() {
    let ctx = egui::Context::default();
    let mut fixture = Fixture::new(&ctx);
    let mut field = ProcessTheater::default();
    {
        let surfaces = fixture.surfaces();
        warm(
            &mut field,
            &ctx,
            Input {
                surfaces: &surfaces,
                ..input(&fixture.progress)
            },
            egui::pos2(0.44, 0.52),
            4.0,
        );
    }
    let (photo_rect, grab, initial_id) = {
        let surfaces = fixture.surfaces();
        let input = Input {
            surfaces: &surfaces,
            ..input(&fixture.progress)
        };
        let (before, _) = draw(&mut field, &ctx, input, 0.7, vec![]);
        let photo_rect = photo(&before, &field);
        let locator = projected(photo_rect, field.scales.aperture());
        let grab = locator.min + locator.size() * egui::vec2(0.68, 0.31);
        let id = field.hero.as_ref().unwrap().plate.texture.id();
        let _ = draw(
            &mut field,
            &ctx,
            input,
            0.8,
            vec![egui::Event::PointerMoved(grab), button(grab, true)],
        );
        (photo_rect, grab, id)
    };
    let preview = fixture.packets.last_mut().unwrap();
    preview.sequence = 101;
    preview.frame = 5;
    preview.folded = 4;
    preview.pixels = (0..117).map(|i| (240 - i) as u8).collect::<Vec<_>>().into();
    *fixture.textures.last_mut().unwrap() = texture(&ctx, "navigation-new-preview");
    let displacement = egui::vec2(-17.0, 12.0);
    let expected = egui::pos2(0.44, 0.52) + displacement / photo_rect.size();
    {
        let surfaces = fixture.surfaces();
        let input = Input {
            surfaces: &surfaces,
            ..input(&fixture.progress)
        };
        let (out, response) = draw(
            &mut field,
            &ctx,
            input,
            0.86,
            vec![egui::Event::PointerMoved(grab + displacement)],
        );
        close_point(field.pin, expected);
        assert_eq!(response.selected, None);
        assert_eq!(field.inspected_source, None);
        linked_views(&out, &fixture, photo_rect, field.scales.aperture());
        for time in [0.95, 1.05, 1.2] {
            let _ = draw(&mut field, &ctx, input, time, vec![]);
        }
        close_point(field.pin, expected);
        assert_eq!(field.hero.as_ref().unwrap().plate.sequence, 101);
        assert_ne!(
            field.hero.as_ref().unwrap().plate.texture.id(),
            initial_id,
            "the live photograph must actually advance while held"
        );
    }
    let output = texture(&ctx, "navigation-owned-final");
    fixture.progress.stage = Stage::Complete;
    let surfaces = fixture.surfaces();
    let final_input = Input {
        surfaces: &surfaces,
        output: Some(&output),
        ..input(&fixture.progress)
    };
    let _ = draw(
        &mut field,
        &ctx,
        final_input,
        1.25,
        vec![egui::Event::PointerMoved(
            grab + displacement + egui::vec2(20.0, 0.0),
        )],
    );
    close_point(field.pin, expected);
    let _ = draw(
        &mut field,
        &ctx,
        final_input,
        1.3,
        vec![button(grab + displacement + egui::vec2(20.0, 0.0), false)],
    );
    let (final_paint, _) = draw(&mut field, &ctx, final_input, 1.7, vec![]);
    close_point(field.pin, expected);
    assert_eq!(field.hero.as_ref().unwrap().plate.texture.id(), output.id());
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
    let painted = images(&final_paint);
    assert!(painted.iter().any(|image| image.id == output.id()
        && image.alpha == 255
        && image.rect.intersects(layout.hero)));
    assert!(
        !final_paint.shapes.iter().any(|shape| match &shape.shape {
            egui::Shape::Rect(rect) =>
                (rect.stroke.width - 2.6).abs() < 0.001 && layout.hero.contains(rect.rect.center()),
            _ => false,
        }),
        "aligned navigation must never overlay the cropped final photograph"
    );
}

#[test]
fn dragging_a_camera_source_does_not_move_the_aligned_inspection_window() {
    let ctx = egui::Context::default();
    let fixture = Fixture::new(&ctx);
    let source = texture(&ctx, "navigation-unregistered-source");
    let photos = [SourcePhoto {
        epoch: 1,
        index: 2,
        texture: source.clone(),
        aperture: [907, 613],
    }];
    let input = Input {
        inspection_photos: &photos,
        ..input(&fixture.progress)
    };
    let mut field = ProcessTheater::default();
    let _ = draw(&mut field, &ctx, input, 0.0, vec![]);
    field.pin = egui::pos2(0.21, 0.79);
    field.scales.set_view(field.pin, 4.0);
    field.zoom = 1.8;
    let (before, _) = draw(&mut field, &ctx, input, 0.6, vec![]);
    let source_rect = images(&before)
        .into_iter()
        .filter(|image| image.id == source.id())
        .max_by(|a, b| a.rect.area().total_cmp(&b.rect.area()))
        .unwrap()
        .rect;
    let at = source_rect.center();
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.7,
        vec![egui::Event::PointerMoved(at), button(at, true)],
    );
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.75,
        vec![egui::Event::PointerMoved(at + egui::vec2(21.0, -17.0))],
    );
    close_point(field.pin, egui::pos2(0.21, 0.79));
    assert!(
        field.pan.length() > 10.0,
        "source gesture must actually pan the source rather than being ignored"
    );
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![button(at + egui::vec2(21.0, -17.0), false)],
    );
    close_point(field.pin, egui::pos2(0.21, 0.79));
}

#[test]
fn pinch_outside_the_box_zooms_only_the_photo_and_keeps_its_cursor_sample_stationary() {
    let ctx = egui::Context::default();
    let fixture = Fixture::new(&ctx);
    let surfaces = fixture.surfaces();
    let input = Input {
        surfaces: &surfaces,
        ..input(&fixture.progress)
    };
    let mut field = ProcessTheater::default();
    let pin = egui::pos2(0.46, 0.57);
    warm(&mut field, &ctx, input, pin, 4.0);
    field.zoom = 1.7;
    field.pan = egui::vec2(-11.0, 17.0);
    let (before, _) = draw(&mut field, &ctx, input, 0.7, vec![]);
    let previous = photo(&before, &field);
    let sample = egui::pos2(0.34, 0.38);
    let at = previous.min + previous.size() * sample.to_vec2();
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
    assert!(
        layout.hero.shrink(36.0).contains(at),
        "the pointer must hit the photograph"
    );
    assert!(
        !projected(previous, field.scales.aperture())
            .expand(10.0)
            .contains(at),
        "the pointer must be clearly outside the detail box and resize grip"
    );
    let (changed, _) = draw(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(at), egui::Event::Zoom(1.25)],
    );
    assert!(
        (field.zoom - 2.125).abs() < 0.0001,
        "actual pinch input must reach the photograph"
    );
    assert_eq!(field.scales.detail_zoom(), 4.0);
    close_point(field.pin, pin);
    let current = photo(&changed, &field);
    assert!((current.width() / previous.width() - 1.25).abs() < 0.0001);
    close_point(Pos2::ZERO + (at - current.min) / current.size(), sample);
    linked_views(&changed, &fixture, current, field.scales.aperture());
    let _ = draw(&mut field, &ctx, input, 0.9, vec![]);
    assert!(
        (field.zoom - 2.125).abs() < 0.0001,
        "a consumed pinch cannot repeat during an idle paint"
    );
}

#[test]
fn opening_a_modal_during_a_real_box_grab_blocks_retained_drag_and_zoom() {
    let ctx = egui::Context::default();
    let fixture = Fixture::new(&ctx);
    let surfaces = fixture.surfaces();
    let input = Input {
        surfaces: &surfaces,
        ..input(&fixture.progress)
    };
    let mut field = ProcessTheater::default();
    let original = egui::pos2(0.46, 0.57);
    warm(&mut field, &ctx, input, original, 4.0);
    let (before, _) = draw(&mut field, &ctx, input, 0.7, vec![]);
    let photo = photo(&before, &field);
    let grab = projected(photo, field.scales.aperture()).center();
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(grab), button(grab, true)],
    );
    let held = grab + egui::vec2(12.0, -9.0);
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.85,
        vec![egui::Event::PointerMoved(held)],
    );
    let retained = field.pin;
    assert!(
        retained.distance(original) > 0.01,
        "a real in-progress navigator drag must precede the modal"
    );
    let photo_zoom = field.zoom;
    let photo_pan = field.pan;
    let detail_zoom = field.scales.detail_zoom();
    // Mirror the application's layering order: scene first, chooser last.
    // Establish the modal without motion, then send input while it is active.
    for (index, events) in [
        vec![],
        vec![],
        vec![
            egui::Event::PointerMoved(held + egui::vec2(24.0, 18.0)),
            egui::Event::Zoom(1.4),
        ],
        vec![button(held + egui::vec2(24.0, 18.0), false)],
    ]
    .into_iter()
    .enumerate()
    {
        let mut response = Response::default();
        let _ = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, SIZE.into())),
                time: Some(0.9 + index as f64 * 0.05),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        field.show(ui, ui.max_rect(), &input, &mut response);
                    });
                egui::Modal::new(egui::Id::new("navigation-mid-grab-modal")).show(ctx, |ui| {
                    ui.label("Choose a bracket");
                });
            },
        );
        close_point(field.pin, retained);
        assert_eq!(field.zoom, photo_zoom);
        assert_eq!(field.pan, photo_pan);
        assert_eq!(field.scales.detail_zoom(), detail_zoom);
        assert_eq!(response.selected, None);
    }
}
