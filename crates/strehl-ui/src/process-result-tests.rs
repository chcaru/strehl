//! Independent v17 integration witnesses. Physical image dimensions deliberately
//! differ from GPU texture dimensions; expected regions come from input events
//! and painted meshes, rather than the output-space/navigation implementation.
use super::*;
use crate::{
    pipeline::{DiagnosticScope, DiagnosticSurface, PipelineProgress},
    process_space::Surface,
};

const REVIEW_SIZE: [f32; 2] = [1410.0, 850.0];

struct ResultFixture {
    progress: PipelineProgress,
    packets: Vec<DiagnosticSurface>,
    textures: Vec<TextureHandle>,
    photograph: TextureHandle,
    original_size: [u32; 2],
}

impl ResultFixture {
    fn new(ctx: &egui::Context, cropped: bool) -> Self {
        let mut progress = PipelineProgress::default();
        progress.ingest("planes : 131 x 99 per CFA plane\n");
        let original_size = if cropped {
            progress.ingest("analysis domain : 105 x 81 at full-plane origin (9, 7) -- Crop is applied BEFORE luma, variance, weighting and accumulation\n");
            progress.ingest("coverage : CROPPED to the region EVERY frame covers -- 105 x 81 plane px at (9, 7) of 131 x 99, emitted at UNITY SCALE.\n");
            progress.ingest("output domain : compact Crop 105x81 from full-plane origin (9, 7); collapsed plane written directly (no second crop)\n");
            [210, 162]
        } else {
            progress.ingest("coverage : field of view scaled to 0.9500 so that EVERY frame covers every pixel\n");
            [262, 198]
        };
        progress.ingest("bands : 7 Laplacian levels + 1 base, coarsest 1 x 1\n");
        progress.ingest(&format!("wrote : result.tiff ({} x {}, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n", original_size[0], original_size[1]));
        progress.mark_complete();
        let mut packets = Vec::new();
        for level in 0..8 {
            let extent = if cropped {
                [105usize, 81]
            } else {
                [131usize, 99]
            };
            let [width, height] = [
                extent[0].div_ceil(1 << level).min(13),
                extent[1].div_ceil(1 << level).min(9),
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
                let per_frame = matches!(
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
                    scope: if per_frame {
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
                        .map(|i| {
                            if (i % width) < (width * 5).div_ceil(13) {
                                255
                            } else {
                                0
                            }
                        })
                        .collect::<Vec<_>>()
                        .into(),
                    folded: if per_frame { 1 } else { 3 },
                });
            }
        }
        for packet in &packets {
            progress
                .admission_archive
                .ingest(packet, if cropped { [105, 81] } else { [131, 99] });
        }
        let textures = packets
            .iter()
            .map(|packet| {
                ctx.load_texture(
                    format!("independent-final-map-{}", packet.sequence),
                    egui::ColorImage::filled([packet.width, packet.height], Color32::GRAY),
                    egui::TextureOptions::NEAREST,
                )
            })
            .collect();
        // Deliberately not the decoded TIFF dimensions, and not an exact aspect
        // ratio match: integer overview rounding must not shift the coordinates.
        let photograph = ctx.load_texture(
            "independent-final-photograph",
            egui::ColorImage::filled([83, 63], Color32::WHITE),
            egui::TextureOptions::LINEAR,
        );
        Self {
            progress,
            packets,
            textures,
            photograph,
            original_size,
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

fn result_input<'a>(fixture: &'a ResultFixture, surfaces: &'a [Surface<'a>]) -> Input<'a> {
    Input {
        epoch: 1,
        progress: &fixture.progress,
        frame_count: 67,
        selected: 2,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces,
        output: Some(&fixture.photograph),
        output_size: Some(fixture.original_size),
    }
}

fn result_paint(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, REVIEW_SIZE.into())),
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

fn result_button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

#[derive(Clone, Copy, Debug)]
struct ResultMesh {
    id: egui::TextureId,
    rect: Rect,
    uv: Rect,
}

fn result_meshes(output: &egui::FullOutput) -> Vec<ResultMesh> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh)
                if mesh.texture_id != egui::TextureId::default() && !mesh.vertices.is_empty() =>
            {
                Some(ResultMesh {
                    id: mesh.texture_id,
                    rect: Rect::from_points(
                        &mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>(),
                    ),
                    uv: Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>()),
                })
            }
            _ => None,
        })
        .collect()
}

fn result_photo(output: &egui::FullOutput, fixture: &ResultFixture) -> ResultMesh {
    result_meshes(output)
        .into_iter()
        .filter(|image| image.id == fixture.photograph.id())
        .max_by(|a, b| a.rect.area().total_cmp(&b.rect.area()))
        .expect("owned final photograph must actually be painted")
}

fn result_same_rect(actual: Rect, expected: Rect) {
    assert!(
        actual.min.distance(expected.min) < 0.002 && actual.max.distance(expected.max) < 0.002,
        "painted {actual:?}, expected {expected:?}; min delta {:?}, max delta {:?}",
        [actual.min.x - expected.min.x, actual.min.y - expected.min.y],
        [actual.max.x - expected.max.x, actual.max.y - expected.max.y]
    );
}

fn result_same_region(output: &egui::FullOutput, fixture: &ResultFixture, expected: Rect) {
    let meshes = result_meshes(output);
    result_same_rect(result_photo(output, fixture).uv, expected);
    for (packet, texture) in fixture.packets.iter().zip(&fixture.textures) {
        if matches!(
            packet.kind,
            DiagnosticKind::GateSupport | DiagnosticKind::Averaging
        ) {
            assert!(
                !meshes.iter().any(|mesh| mesh.id == texture.id()),
                "binary observations must not paint full-frame ownership textures"
            );
            continue;
        }
        let map = meshes
            .iter()
            .find(|mesh| mesh.id == texture.id())
            .unwrap_or_else(|| panic!("missing {:?} level {}", packet.kind, packet.level));
        result_same_rect(map.uv, expected);
    }
    let layout = Layout::completed(Rect::from_min_size(Pos2::ZERO, REVIEW_SIZE.into()));
    let lenses: Vec<_> = meshes
        .iter()
        .filter(|mesh| layout.contributions.contains_rect(mesh.rect))
        .collect();
    assert!(
        lenses.len() >= 2,
        "both photographic lenses must remain present under sparse sample markers"
    );
    for lens in lenses {
        result_same_rect(lens.uv, expected);
    }
}

fn result_warm(field: &mut ProcessTheater, ctx: &egui::Context, input: Input<'_>) {
    result_paint(field, ctx, input, 0.0, vec![]);
    result_paint(field, ctx, input, 0.4, vec![]);
    result_paint(field, ctx, input, 0.6, vec![]);
}

#[test]
fn drawing_on_zoomed_final_photo_uses_its_real_crop_and_does_not_pan() {
    use crate::edit_workspace::{DrawingTool, EditorState, LoadedPhoto};
    use std::sync::Arc;
    for cropped in [false, true] {
        let ctx = egui::Context::default();
        let fixture = ResultFixture::new(&ctx, cropped);
        let surfaces = fixture.surfaces();
        let input = result_input(&fixture, &surfaces);
        let mut field = ProcessTheater::default();
        result_warm(&mut field, &ctx, input);
        field.set_photo_view(egui::pos2(0.65, 0.4), 4.0);
        let output = result_paint(&mut field, &ctx, input, 0.8, vec![]);
        let painted = result_photo(&output, &fixture);
        assert!(
            painted.uv.width() < 0.3,
            "agent view must zoom the final photograph"
        );
        assert!((painted.uv.center().x - 0.65).abs() < 0.002);
        let before = field.scales.aperture();
        let image = Arc::new(strehl_edit::LinearImage {
            width: 16,
            height: 12,
            pixels: vec![0.2; 16 * 12 * 3],
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: None,
            baked_recipe: None,
        });
        let mut editor = EditorState::default();
        editor.loaded = Some(LoadedPhoto {
            image: image.clone(),
            preview: image,
            recipe: Default::default(),
            source: "unopened-fixture".into(),
            warnings: vec![],
        });
        editor.tool = DrawingTool::Rectangle;
        let a = painted.rect.min + painted.rect.size() * egui::vec2(0.2, 0.3);
        let b = painted.rect.min + painted.rect.size() * egui::vec2(0.7, 0.65);
        for (time, events) in [
            (1.0, vec![]),
            (
                1.2,
                vec![egui::Event::PointerMoved(a), result_button(a, true)],
            ),
            (1.4, vec![egui::Event::PointerMoved(b)]),
            (1.6, vec![result_button(b, false)]),
        ] {
            let _ = ctx.run(
                egui::RawInput {
                    screen_rect: Some(Rect::from_min_size(Pos2::ZERO, REVIEW_SIZE.into())),
                    time: Some(time),
                    events,
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default()
                        .frame(egui::Frame::NONE)
                        .show(ctx, |ui| {
                            field.annotation_mode = editor.tool != DrawingTool::Navigate;
                            field.show(ui, ui.max_rect(), &input, &mut Response::default());
                            let mapping = field
                                .edit_mapping
                                .expect("final photograph must expose its coordinates");
                            editor.draw_overlay(ui, mapping);
                        });
                },
            );
        }
        assert_eq!(
            editor.recipe.regions.len(),
            1,
            "one drag must create one region"
        );
        let expected = Rect::from_min_max(
            painted.uv.min + painted.uv.size() * egui::vec2(0.2, 0.3),
            painted.uv.min + painted.uv.size() * egui::vec2(0.7, 0.65),
        );
        let bounds = crate::edit_workspace::shape_bounds(&editor.recipe.regions[0].shape);
        result_same_rect(
            Rect::from_min_max(bounds[0].into(), bounds[1].into()),
            expected,
        );
        result_same_rect(field.scales.aperture(), before);
        assert!(editor.undo());
        assert!(editor.recipe.regions.is_empty());
        assert!(editor.redo());
        assert_eq!(editor.recipe.regions.len(), 1);
    }
}

#[test]
fn scene_button_resets_the_actual_photo_crop_while_annotation_owns_the_canvas() {
    // A no-op click fails because every arm starts with a non-central,
    // visibly magnified crop. Exercise both the instrument and photo layouts,
    // and both certified output geometries rather than only a square fixture.
    for cropped in [false, true] {
        for photo_focus in [false, true] {
            let ctx = egui::Context::default();
            let fixture = ResultFixture::new(&ctx, cropped);
            let surfaces = fixture.surfaces();
            let input = result_input(&fixture, &surfaces);
            let mut field = ProcessTheater {
                annotation_mode: true,
                edit_focus: photo_focus,
                ..Default::default()
            };
            result_warm(&mut field, &ctx, input);
            field.set_photo_view(egui::pos2(0.68, 0.43), 3.6);
            let zoomed = result_paint(&mut field, &ctx, input, 0.9, vec![]);
            let photo = result_photo(&zoomed, &fixture);
            assert!(photo.uv.width() < 0.3, "fixture must be visibly zoomed");
            assert!((photo.uv.center().x - 0.68).abs() < 0.002);
            let button = zoomed
                .shapes
                .iter()
                .find_map(|shape| match &shape.shape {
                    egui::Shape::Text(text) if text.galley.text().ends_with("× · Scene") => {
                        Some(text.visual_bounding_rect().center())
                    }
                    _ => None,
                })
                .expect("Scene reset must be visible while drawing");
            result_paint(
                &mut field,
                &ctx,
                input,
                1.1,
                vec![
                    egui::Event::PointerMoved(button),
                    result_button(button, true),
                ],
            );
            result_paint(
                &mut field,
                &ctx,
                input,
                1.2,
                vec![result_button(button, false)],
            );
            let reset = result_paint(&mut field, &ctx, input, 1.8, vec![]);
            let photo = result_photo(&reset, &fixture);
            result_same_rect(
                photo.uv,
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            );
            assert!(
                field.annotation_mode,
                "reset must leave the drawing tool active"
            );
            let (whole, visible) = field.edit_mapping.expect("drawing mapping must remain");
            result_same_rect(whole, photo.rect);
            result_same_rect(visible, photo.rect);
        }
    }
}

#[test]
fn completion_supersedes_the_real_live_preview_and_shows_the_actual_final_photo() {
    let ctx = egui::Context::default();
    let mut fixture = ResultFixture::new(&ctx, false);
    fixture.progress.stage = Stage::Merge;
    fixture.packets.push(DiagnosticSurface {
        sequence: 900,
        frame: 3,
        level: 3,
        kind: DiagnosticKind::Preview,
        scope: DiagnosticScope::Stack,
        scale: DiagnosticScale::Linear,
        width: 13,
        height: 9,
        min: 10.0,
        max: 300.0,
        pixels: (0..117).map(|i| (i * 2) as u8).collect::<Vec<_>>().into(),
        folded: 4,
    });
    fixture.textures.push(ctx.load_texture(
        "review-observed-history-packet",
        egui::ColorImage::filled([13, 9], Color32::GRAY),
        egui::TextureOptions::NEAREST,
    ));
    let mut field = ProcessTheater::default();
    {
        let surfaces = fixture.surfaces();
        let input = Input {
            output: None,
            output_size: None,
            ..result_input(&fixture, &surfaces)
        };
        result_warm(&mut field, &ctx, input);
        let live = result_paint(&mut field, &ctx, input, 0.7, vec![]);
        let latest = field
            .hero
            .as_ref()
            .expect("a real live composite is displayed");
        assert_eq!(latest.plate.folded, 4);
        assert!(
            result_meshes(&live)
                .iter()
                .any(|mesh| mesh.id == latest.plate.texture.id() && mesh.rect.area() > 10_000.0)
        );
        assert!(!live.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text() == "BUILD")));
    }
    fixture.progress.mark_complete();
    let surfaces = fixture.surfaces();
    let input = result_input(&fixture, &surfaces);
    result_paint(&mut field, &ctx, input, 1.0, vec![]);
    result_paint(&mut field, &ctx, input, 1.5, vec![]);
    let completed = result_paint(&mut field, &ctx, input, 2.0, vec![]);
    assert!(
        result_photo(&completed, &fixture).rect.area() > 10_000.0,
        "the final photograph must be the main painted image, not only a lens or thumbnail"
    );
}

#[test]
fn final_tiff_and_every_diagnostic_share_the_region_for_scaled_and_offset_cropped_outputs() {
    for cropped in [false, true] {
        let ctx = egui::Context::default();
        let fixture = ResultFixture::new(&ctx, cropped);
        let surfaces = fixture.surfaces();
        let input = result_input(&fixture, &surfaces);
        let mut field = ProcessTheater::default();
        result_warm(&mut field, &ctx, input);
        let clean = result_paint(&mut field, &ctx, input, 0.7, vec![]);
        let photo = result_photo(&clean, &fixture);
        result_same_rect(
            photo.uv,
            Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        );
        assert!(
            (photo.rect.width() / photo.rect.height()
                - fixture.original_size[0] as f32 / fixture.original_size[1] as f32)
                .abs()
                < 0.0001,
            "physical TIFF aspect must survive a rounded GPU overview"
        );
        let image_layers = result_meshes(&clean)
            .into_iter()
            .filter(|mesh| mesh.rect == photo.rect)
            .count();
        assert_eq!(
            image_layers, 1,
            "completed scene starts with the unmarked TIFF"
        );

        field.pin = egui::pos2(0.58, 0.39);
        field.scales.set_view(field.pin, 4.0);
        let local = result_paint(&mut field, &ctx, input, 0.8, vec![]);
        let expected = Rect::from_min_max(egui::pos2(0.455, 0.265), egui::pos2(0.705, 0.515));
        result_same_region(&local, &fixture, expected);
        let completed = Layout::completed(Rect::from_min_size(Pos2::ZERO, REVIEW_SIZE.into()));
        assert!(
            result_photo(&local, &fixture).rect.width() > REVIEW_SIZE[0] * 0.45,
            "completion must reclaim the registration network's space for the photograph"
        );
        assert!(completed.signals.width() > REVIEW_SIZE[0] * 0.40);
    }
}

#[test]
fn real_pinch_and_slow_grab_move_the_finished_image_with_all_maps_in_one_snapshot() {
    let ctx = egui::Context::default();
    let fixture = ResultFixture::new(&ctx, true);
    let surfaces = fixture.surfaces();
    let input = result_input(&fixture, &surfaces);
    let mut field = ProcessTheater::default();
    result_warm(&mut field, &ctx, input);
    field.pin = egui::pos2(0.58, 0.39);
    field.scales.set_view(field.pin, 4.0);
    let start = result_paint(&mut field, &ctx, input, 0.7, vec![]);
    let photo = result_photo(&start, &fixture);
    let anchor = egui::vec2(0.31, 0.27);
    let at = photo.rect.min + photo.rect.size() * anchor;
    let old_sample = photo.uv.min + photo.uv.size() * anchor;
    result_paint(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(at), egui::Event::Zoom(1.3)],
    );
    let zoomed = result_paint(&mut field, &ctx, input, 1.1, vec![]);
    let next = result_photo(&zoomed, &fixture);
    assert!(
        (next.uv.width() - 1.0 / 5.2).abs() < 0.0001,
        "the actual pinch event must change shared magnification"
    );
    assert!(
        (next.uv.min + next.uv.size() * anchor).distance(old_sample) < 0.0001,
        "the photograph's sampled point stays beneath the pinch anchor"
    );
    result_same_region(&zoomed, &fixture, next.uv);

    let grab = next.rect.min + next.rect.size() * egui::vec2(0.42, 0.36);
    result_paint(
        &mut field,
        &ctx,
        input,
        1.2,
        vec![egui::Event::PointerMoved(grab), result_button(grab, true)],
    );
    result_paint(
        &mut field,
        &ctx,
        input,
        1.23,
        vec![egui::Event::PointerMoved(grab + egui::vec2(3.0, 1.0))],
    );
    let displacement = egui::vec2(24.0, -13.0);
    result_paint(
        &mut field,
        &ctx,
        input,
        1.27,
        vec![egui::Event::PointerMoved(grab + displacement)],
    );
    result_paint(
        &mut field,
        &ctx,
        input,
        1.31,
        vec![result_button(grab + displacement, false)],
    );
    let settled = result_paint(&mut field, &ctx, input, 1.4, vec![]);
    let expected = next
        .uv
        .translate(-displacement / next.rect.size() * next.uv.size());
    result_same_region(&settled, &fixture, expected);
    let actual = result_photo(&settled, &fixture);
    assert!(
        actual.uv.center().x < next.uv.center().x && actual.uv.center().y > next.uv.center().y,
        "photograph follows the pointer, with no pre-threshold movement lost"
    );
}

#[test]
fn invalid_geometry_does_not_link_an_unrelated_tiff_and_a_new_bracket_clears_the_result() {
    let ctx = egui::Context::default();
    let fixture = ResultFixture::new(&ctx, false);
    let surfaces = fixture.surfaces();
    let mut input = result_input(&fixture, &surfaces);
    input.output_size = Some([524, 396]); // same aspect, unrelated original dimensions
    let mut field = ProcessTheater::default();
    result_warm(&mut field, &ctx, input);
    field.pin = egui::pos2(0.58, 0.39);
    field.scales.set_view(field.pin, 4.0);
    let before = result_paint(&mut field, &ctx, input, 0.7, vec![]);
    let at = result_photo(&before, &fixture).rect.center();
    result_paint(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(at), egui::Event::Zoom(1.3)],
    );
    result_paint(&mut field, &ctx, input, 1.1, vec![]);
    assert_eq!(
        field.scales.detail_zoom(),
        4.0,
        "a photographic-only zoom cannot move registered diagnostic coordinates without a certificate"
    );
    assert_eq!(field.pin, egui::pos2(0.58, 0.39));
    assert!(
        (field.zoom - 1.3).abs() < 0.0001,
        "fallback image inspection still works"
    );

    let fresh = PipelineProgress::default();
    let next_input = Input {
        epoch: 2,
        progress: &fresh,
        output: None,
        output_size: None,
        surfaces: &[],
        ..input
    };
    let output = result_paint(&mut field, &ctx, next_input, 1.2, vec![]);
    assert!(field.saved_output.is_none());
    assert!(
        result_meshes(&output)
            .iter()
            .all(|mesh| mesh.id != fixture.photograph.id()),
        "a new bracket must not show the previous TIFF or retain its overlay"
    );
    assert_eq!(field.scales.detail_zoom(), 1.0);
}

#[test]
fn held_capture_footprint_allows_clean_space_peek_without_losing_focused_ribbon_state() {
    fn paint(
        field: &mut ProcessTheater,
        ctx: &egui::Context,
        input: Input<'_>,
        time: f64,
        events: Vec<egui::Event>,
    ) -> egui::FullOutput {
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, REVIEW_SIZE.into())),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        field.show_with_ribbon(
                            ui,
                            Rect::from_min_size(Pos2::ZERO, egui::vec2(1410.0, 596.0)),
                            &input,
                            &mut Response::default(),
                            Some(Rect::from_min_size(
                                egui::pos2(0.0, 612.0),
                                egui::vec2(1410.0, 238.0),
                            )),
                        );
                    });
            },
        )
    }
    fn key(key: egui::Key, pressed: bool) -> egui::Event {
        egui::Event::Key {
            key,
            physical_key: None,
            pressed,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        }
    }
    fn layers(output: &egui::FullOutput, fixture: &ResultFixture) -> usize {
        let photo = result_photo(output, fixture);
        let photos = result_meshes(output)
            .iter()
            .filter(|mesh| mesh.rect == photo.rect)
            .count();
        let sparse_modifier = crate::process_result::overlay_marker_centers(output)
            .iter()
            .any(|point| photo.rect.contains(*point));
        photos + usize::from(sparse_modifier)
    }
    let ctx = egui::Context::default();
    let fixture = ResultFixture::new(&ctx, false);
    let surfaces = fixture.surfaces();
    let input = result_input(&fixture, &surfaces);
    assert!(
        input.photos.is_empty() && input.inspection_photos.is_empty(),
        "saved gate evidence must remain explorable even without camera JPEGs"
    );
    assert!(input.progress.admission_archive.counts(0, 4).unwrap().0 > 0);

    let mut field = ProcessTheater::default();
    paint(&mut field, &ctx, input, 0.0, vec![]);
    let clean = paint(&mut field, &ctx, input, 0.4, vec![]);
    assert_eq!(layers(&clean, &fixture), 1);
    let label_y = clean
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Full image" => {
                Some(text.visual_bounding_rect().center().y)
            }
            _ => None,
        })
        .expect("actual participation lane");
    let axis = clean
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && points[1].x - points[0].x > 1000.0
                    && (label_y + 1.0..label_y + 25.0).contains(&points[0].y) =>
            {
                Some(*points)
            }
            _ => None,
        })
        .expect("actual continuous capture axis");
    let at = axis[0].lerp(axis[1], 4.0 / 66.0) - egui::vec2(0.0, 4.0);
    paint(
        &mut field,
        &ctx,
        input,
        0.5,
        vec![egui::Event::PointerMoved(at), result_button(at, true)],
    );
    let held = paint(&mut field, &ctx, input, 0.6, vec![result_button(at, false)]);
    assert_eq!(field.participation_frame, Some(4));
    assert!(field.participation_held);
    assert_eq!(
        layers(&held, &fixture),
        2,
        "real archive sample points must modify the owned TIFF"
    );
    assert!(
        ctx.wants_keyboard_input(),
        "the ribbon must actually retain keyboard focus for this witness"
    );
    let peek = paint(
        &mut field,
        &ctx,
        input,
        0.7,
        vec![key(egui::Key::Space, true)],
    );
    assert_eq!(
        layers(&peek, &fixture),
        1,
        "Space is available after clicking a held footprint"
    );
    assert_eq!(field.participation_frame, Some(4));
    assert!(field.participation_held);
    let returned = paint(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![
            key(egui::Key::Space, false),
            egui::Event::PointerMoved(egui::pos2(4.0, 200.0)),
        ],
    );
    assert_eq!(layers(&returned, &fixture), 2);
    let released = paint(
        &mut field,
        &ctx,
        input,
        0.9,
        vec![key(egui::Key::Escape, true), key(egui::Key::Escape, false)],
    );
    assert_eq!(layers(&released, &fixture), 1);
    assert_eq!(field.participation_frame, None);
}

#[test]
fn a_photo_grab_keeps_ownership_when_the_pointer_crosses_the_overview_inset() {
    let ctx = egui::Context::default();
    let fixture = ResultFixture::new(&ctx, false);
    let surfaces = fixture.surfaces();
    let input = result_input(&fixture, &surfaces);
    let mut field = ProcessTheater::default();
    result_warm(&mut field, &ctx, input);
    field.pin = egui::pos2(0.58, 0.39);
    field.scales.set_view(field.pin, 4.0);
    let start = result_paint(&mut field, &ctx, input, 0.7, vec![]);
    let photo = result_photo(&start, &fixture);
    let overview = result_meshes(&start)
        .into_iter()
        .find(|mesh| {
            mesh.id == fixture.photograph.id()
                && mesh.rect.width() <= 112.1
                && photo.rect.contains_rect(mesh.rect)
        })
        .expect("zoomed final photograph must have a real overview image");
    let from = overview.rect.min - egui::vec2(18.0, 14.0);
    let to = overview.rect.center();
    assert!(photo.rect.contains(from) && !overview.rect.expand(3.0).contains(from));
    result_paint(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(from), result_button(from, true)],
    );
    result_paint(
        &mut field,
        &ctx,
        input,
        0.9,
        vec![egui::Event::PointerMoved(to)],
    );
    result_paint(&mut field, &ctx, input, 1.0, vec![result_button(to, false)]);
    let moved = result_paint(&mut field, &ctx, input, 1.1, vec![]);
    let expected = photo
        .uv
        .translate(-(to - from) / photo.rect.size() * photo.uv.size());
    result_same_region(&moved, &fixture, expected);
}

#[test]
fn final_map_lens_and_overview_gestures_share_the_continuous_zoom_range_below_two() {
    let ctx = egui::Context::default();
    let fixture = ResultFixture::new(&ctx, false);
    let surfaces = fixture.surfaces();
    let input = result_input(&fixture, &surfaces);
    let mut field = ProcessTheater::default();
    result_warm(&mut field, &ctx, input);
    for (step, lens) in [false, true].into_iter().enumerate() {
        field.pin = egui::pos2(0.5, 0.5);
        field.scales.set_view(field.pin, 1.3);
        let time = 0.8 + step as f64;
        let start = result_paint(&mut field, &ctx, input, time, vec![]);
        let meshes = result_meshes(&start);
        let at = if lens {
            let layout = Layout::completed(Rect::from_min_size(Pos2::ZERO, REVIEW_SIZE.into()));
            meshes
                .iter()
                .find(|mesh| {
                    mesh.id == fixture.photograph.id()
                        && layout.contributions.contains_rect(mesh.rect)
                })
                .expect("actual photographic lens is required")
                .rect
                .center()
        } else {
            meshes
                .iter()
                .find(|mesh| mesh.id == fixture.textures[0].id())
                .expect("actual diagnostic map is required")
                .rect
                .center()
        };
        result_paint(
            &mut field,
            &ctx,
            input,
            time + 0.1,
            vec![egui::Event::PointerMoved(at), egui::Event::Zoom(0.9)],
        );
        let changed = result_paint(&mut field, &ctx, input, time + 0.4, vec![]);
        assert!(
            (field.scales.detail_zoom() - 1.17).abs() < 0.0001,
            "zooming out from1.3x must not jump inward to2x on {}",
            if lens { "a lens" } else { "a map" }
        );
        result_same_region(
            &changed,
            &fixture,
            Rect::from_center_size(egui::pos2(0.5, 0.5), Vec2::splat(1.0 / 1.17)),
        );
    }
    field.pin = egui::pos2(0.5, 0.5);
    field.scales.set_view(field.pin, 1.3);
    let start = result_paint(&mut field, &ctx, input, 3.0, vec![]);
    let photo = result_photo(&start, &fixture);
    let overview = result_meshes(&start)
        .into_iter()
        .find(|mesh| {
            mesh.id == fixture.photograph.id()
                && mesh.rect.width() <= 112.1
                && photo.rect.contains_rect(mesh.rect)
        })
        .unwrap();
    let from = overview.rect.min + overview.rect.size() * photo.uv.max.to_vec2();
    let side = 1.0 / 1.15;
    let to = from + overview.rect.size() * (side - photo.uv.width());
    result_paint(
        &mut field,
        &ctx,
        input,
        3.1,
        vec![egui::Event::PointerMoved(from), result_button(from, true)],
    );
    result_paint(
        &mut field,
        &ctx,
        input,
        3.2,
        vec![egui::Event::PointerMoved(to)],
    );
    result_paint(&mut field, &ctx, input, 3.3, vec![result_button(to, false)]);
    let resized = result_paint(&mut field, &ctx, input, 3.4, vec![]);
    assert!(
        (field.scales.detail_zoom() - 1.15).abs() < 0.0002,
        "overview resizing must preserve its continuous final-image range"
    );
    result_same_region(
        &resized,
        &fixture,
        Rect::from_min_size(photo.uv.min, Vec2::splat(side)),
    );
}

#[test]
fn overview_body_grab_needs_no_prehover_even_after_releasing_a_photograph_pan() {
    for preceding_pan in [false, true] {
        let ctx = egui::Context::default();
        let fixture = ResultFixture::new(&ctx, false);
        let surfaces = fixture.surfaces();
        let input = result_input(&fixture, &surfaces);
        let mut field = ProcessTheater::default();
        result_warm(&mut field, &ctx, input);
        field.pin = egui::pos2(0.5, 0.5);
        field.scales.set_view(field.pin, 1.4);
        let start = result_paint(&mut field, &ctx, input, 0.7, vec![]);
        let photo = result_photo(&start, &fixture);
        let outside = photo.rect.center();
        result_paint(
            &mut field,
            &ctx,
            input,
            0.8,
            if preceding_pan {
                vec![
                    egui::Event::PointerMoved(outside),
                    result_button(outside, true),
                ]
            } else {
                vec![egui::Event::PointerMoved(outside)]
            },
        );
        if preceding_pan {
            let moved = outside + egui::vec2(14.0, -11.0);
            result_paint(
                &mut field,
                &ctx,
                input,
                0.9,
                vec![egui::Event::PointerMoved(moved)],
            );
            result_paint(
                &mut field,
                &ctx,
                input,
                1.0,
                vec![result_button(moved, false)],
            );
        }
        let settled = result_paint(&mut field, &ctx, input, 1.1, vec![]);
        let photo = result_photo(&settled, &fixture);
        let overview = result_meshes(&settled)
            .into_iter()
            .find(|mesh| {
                mesh.id == fixture.photograph.id()
                    && mesh.rect.width() <= 112.1
                    && photo.rect.contains_rect(mesh.rect)
            })
            .expect("the final overview must be visible before the gesture");
        assert!(!overview.rect.contains(outside));
        let from = overview.rect.min + overview.rect.size() * photo.uv.center().to_vec2();
        let delta = egui::vec2(0.065, -0.06);
        let to = from + overview.rect.size() * delta;
        assert!(
            from.distance(to) > 6.0,
            "the gesture must cross drag threshold"
        );
        // No intervening hover frame: this models a pointer jump followed by
        // the initial press, including after another surface owned the grab.
        result_paint(
            &mut field,
            &ctx,
            input,
            1.2,
            vec![egui::Event::PointerMoved(from), result_button(from, true)],
        );
        result_paint(
            &mut field,
            &ctx,
            input,
            1.3,
            vec![egui::Event::PointerMoved(to)],
        );
        result_paint(&mut field, &ctx, input, 1.4, vec![result_button(to, false)]);
        let moved = result_paint(&mut field, &ctx, input, 1.5, vec![]);
        let expected = photo.uv.translate(delta);
        assert!(expected.center().distance(photo.uv.center()) > 0.08);
        result_same_region(&moved, &fixture, expected);
    }
}

#[test]
fn a_large_diagnostic_modifies_the_owned_photo_and_double_click_returns_clean() {
    let ctx = egui::Context::default();
    let fixture = ResultFixture::new(&ctx, false);
    let surfaces = fixture.surfaces();
    let data = result_input(&fixture, &surfaces);
    let mut field = ProcessTheater::default();
    result_warm(&mut field, &ctx, data);
    let clean = result_paint(&mut field, &ctx, data, 0.8, vec![]);
    let photo = result_photo(&clean, &fixture);
    field.enlarged = Some(DiagnosticKind::GateSupport);
    let modified = result_paint(&mut field, &ctx, data, 1.0, vec![]);
    result_same_rect(result_photo(&modified, &fixture).rect, photo.rect);
    let markers = |output: &egui::FullOutput| {
        crate::process_result::overlay_marker_centers(output)
            .iter()
            .filter(|point| photo.rect.contains(**point))
            .count()
    };
    let before_markers = markers(&clean);
    assert!(
        markers(&modified) > before_markers,
        "the explicit diagnostic action must paint actual sample points on the owned photograph"
    );
    assert!(
        !modified
            .shapes
            .iter()
            .any(|shape| matches!(&shape.shape, egui::Shape::Mesh(mesh)
        if !mesh.vertices.is_empty() && mesh.vertices.iter().all(|v| v.color.a() == 125))),
        "sparse observations must not become full-frame ownership rectangles"
    );
    let at = photo.rect.center();
    for (time, pressed) in [(1.2, true), (1.25, false), (1.3, true), (1.35, false)] {
        result_paint(
            &mut field,
            &ctx,
            data,
            time,
            vec![egui::Event::PointerMoved(at), result_button(at, pressed)],
        );
    }
    assert_eq!(field.enlarged, None);
    let restored = result_paint(&mut field, &ctx, data, 1.6, vec![]);
    result_same_rect(result_photo(&restored, &fixture).rect, photo.rect);
    assert_eq!(markers(&restored), before_markers);
    assert!(!restored.shapes.iter().any(|shape|matches!(&shape.shape,egui::Shape::Mesh(mesh) if !mesh.vertices.is_empty() && mesh.vertices.iter().all(|v|v.color.a()==125))));
}

#[test]
fn convergence_ends_at_actual_photograph_pixels_after_container_resizing() {
    let ctx = egui::Context::default();
    let fixture = ResultFixture::new(&ctx, false);
    let surfaces = fixture.surfaces();
    let data = result_input(&fixture, &surfaces);
    let mut field = ProcessTheater::default();
    result_warm(&mut field, &ctx, data);
    for (index, split) in [0.44, 0.28, 0.65, 0.36].into_iter().enumerate() {
        field.layout.final_detail = split;
        let out = result_paint(&mut field, &ctx, data, 1.0 + index as f64, vec![]);
        let photo = result_photo(&out, &fixture).rect;
        let ends: Vec<_> = out
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::CubicBezier(curve) if curve.points[3].x > photo.left() - 1.0 => {
                    Some(curve.points[3])
                }
                _ => None,
            })
            .collect();
        assert!(
            !ends.is_empty(),
            "fixture must actually paint matrix convergence"
        );
        for endpoint in ends {
            assert!(
                endpoint.distance(photo.left_center()) < 0.01,
                "connector detached: {endpoint:?}, photograph {photo:?}"
            );
        }
    }
}
