//! Independent consumer checks: inspect the image mesh egui actually emits,
//! rather than calling a second copy of the viewer's layout calculation.

use super::*;
use egui::{Context, Event, FullOutput, Modifiers, PointerButton, Pos2, RawInput};

const SOURCE: [usize; 2] = [317, 199];

fn fixture(context: &Context, overview: bool) -> Viewer {
    // Odd dimensions and an off-grid pan expose half-pixel placement mistakes.
    let texture = context.load_texture(
        "independent-pixel-witness",
        egui::ColorImage::new(SOURCE, vec![Color32::WHITE; SOURCE[0] * SOURCE[1]]),
        egui::TextureOptions::NEAREST,
    );
    Viewer {
        texture: Some(texture),
        source_size: if overview {
            [10_000, 6_000]
        } else {
            [317, 199]
        },
        overview,
        fit: false,
        zoom: 1.0,
        pan: egui::vec2(0.137, -0.281),
        ..Default::default()
    }
}

fn frame(
    context: &Context,
    viewer: &mut Viewer,
    scale: f32,
    time: f64,
    events: Vec<Event>,
) -> FullOutput {
    let mut input = RawInput {
        screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(701.0, 503.0))),
        time: Some(time),
        events,
        ..Default::default()
    };
    input
        .viewports
        .get_mut(&egui::ViewportId::ROOT)
        .unwrap()
        .native_pixels_per_point = Some(scale);
    context.run(input, |context| {
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(context, |ui| {
                viewer.show(ui, false);
            });
    })
}

fn image_bounds(output: &FullOutput, texture: egui::TextureId) -> Rect {
    let meshes: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == texture => Some(mesh),
            _ => None,
        })
        .collect();
    assert_eq!(meshes.len(), 1, "the fixture must exercise a painted image");
    let mesh = meshes[0];
    assert_eq!(mesh.vertices.len(), 4);
    let bounds = Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.pos)
            .collect::<Vec<_>>(),
    );
    // Full source UVs must reach the paint consumer, without a hidden crop.
    let uv_bounds = Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.uv)
            .collect::<Vec<_>>(),
    );
    assert_eq!(
        uv_bounds,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
    );
    bounds
}

fn native_intervals(bounds: Rect, scale: f32) -> bool {
    let device_width = bounds.width() * scale;
    let device_height = bounds.height() * scale;
    (device_width - SOURCE[0] as f32).abs() < 0.001
        && (device_height - SOURCE[1] as f32).abs() < 0.001
}

#[test]
fn bounded_photo_paint_attachment_and_detachment_preserve_zoomed_panned_bounds() {
    let context = Context::default();
    let mut viewer = fixture(&context, true);
    // A resized full photograph, including odd-dimension rounding, unlike the
    // deliberately different camera crop used by the generic viewer fixture.
    viewer.source_size = [3173, 1991];
    viewer.zoom = 2.4;
    let before = frame(&context, &mut viewer, 1.5, 0.0, vec![]);
    let bounds = image_bounds(&before, viewer.texture.as_ref().unwrap().id());
    let pan = viewer.pan;
    let mut editor = crate::edit_workspace::EditorState::default();
    let image = std::sync::Arc::new(strehl_edit::LinearImage {
        width: 8,
        height: 6,
        pixels: vec![0.2; 8 * 6 * 3],
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        preview: std::sync::Arc::new(image.preview(8)),
        image,
        recipe: Default::default(),
        source: "unopened-viewer-fixture.tiff".into(),
        warnings: Vec::new(),
    });
    let until = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while editor.photo_paint().is_none() {
        assert!(std::time::Instant::now() < until);
        editor.poll(&context, 4096);
        std::thread::sleep(std::time::Duration::from_millis(2));
    }
    viewer.set_photo_paint(editor.photo_paint());
    assert!(viewer.native_inspection_available());
    frame(&context, &mut viewer, 1.5, 0.1, vec![]);
    let attached = viewer.display_mapping.unwrap().0;
    viewer.set_photo_paint(None);
    assert!(!viewer.native_inspection_available());
    let after = frame(&context, &mut viewer, 1.5, 0.2, vec![]);
    let detached = image_bounds(&after, viewer.texture.as_ref().unwrap().id());
    for observed in [attached, detached] {
        assert!(
            observed.min.distance(bounds.min) < 0.001,
            "{observed:?} versus {bounds:?}"
        );
        assert!(
            observed.max.distance(bounds.max) < 0.001,
            "{observed:?} versus {bounds:?}"
        );
    }
    assert_eq!(viewer.pan, pan);
    assert!(!viewer.fit);
}

#[test]
fn native_scale_maps_known_source_intervals_to_single_physical_pixels() {
    // Different settings from the author's 1x examples: fractional Windows
    // scaling plus 2.75x, odd texture dimensions, and subpixel pan offsets.
    for scale in [1.0, 1.25, 1.5, 2.0, 2.75] {
        let context = Context::default();
        let mut viewer = fixture(&context, false);
        let output = frame(&context, &mut viewer, scale, 0.0, vec![]);
        assert!((output.pixels_per_point - scale).abs() < f32::EPSILON);
        let bounds = image_bounds(&output, viewer.texture.as_ref().unwrap().id());
        assert!(
            native_intervals(bounds, scale),
            "source intervals changed at {scale}x"
        );
        for origin in [bounds.min.x * scale, bounds.min.y * scale] {
            assert!(
                (origin - origin.round()).abs() < 0.001,
                "pixel origin is unsnapped at {scale}x"
            );
        }
        // Negative control: a deliberately enlarged image must fail the same
        // native-pixel criterion, proving this test can reject interpolation.
        viewer.zoom = 2.0;
        let enlarged = frame(&context, &mut viewer, scale, 0.1, vec![]);
        assert!(!native_intervals(
            image_bounds(&enlarged, viewer.texture.as_ref().unwrap().id()),
            scale
        ));
    }
}

fn double_click(context: &Context, viewer: &mut Viewer, base: f64) -> FullOutput {
    let pointer = egui::pos2(350.0, 250.0);
    frame(
        context,
        viewer,
        1.5,
        base,
        vec![Event::PointerMoved(pointer)],
    );
    let mut outputs = Vec::new();
    for (offset, pressed) in [(0.02, true), (0.04, false), (0.10, true), (0.12, false)] {
        outputs.push(frame(
            context,
            viewer,
            1.5,
            base + offset,
            vec![Event::PointerButton {
                pos: pointer,
                button: PointerButton::Primary,
                pressed,
                modifiers: Modifiers::NONE,
            }],
        ));
    }
    outputs.pop().unwrap()
}

#[test]
fn real_double_click_fits_native_and_reduced_sources_and_never_toggles_back() {
    for overview in [false, true] {
        let context = Context::default();
        let mut viewer = fixture(&context, overview);
        assert!(
            !viewer.fit && viewer.pan != Vec2::ZERO,
            "start in a genuinely modified view"
        );
        frame(&context, &mut viewer, 1.5, 0.0, vec![]);
        let output = double_click(&context, &mut viewer, 1.0);
        assert!(viewer.fit);
        assert_eq!(viewer.pan, Vec2::ZERO);
        let bounds = image_bounds(&output, viewer.texture.as_ref().unwrap().id());
        assert!(
            !native_intervals(bounds, 1.5),
            "the fitted photograph is not a hidden native-scale toggle"
        );
        let again = double_click(&context, &mut viewer, 2.0);
        assert!(viewer.fit);
        assert_eq!(
            image_bounds(&again, viewer.texture.as_ref().unwrap().id()),
            bounds
        );
    }
}

#[test]
fn second_click_jitter_does_not_pan_before_the_viewer_fits_on_release() {
    let context = Context::default();
    let mut viewer = fixture(&context, false);
    let at = egui::pos2(350.0, 250.0);
    let events = |point: Pos2, pressed: bool| {
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
    frame(&context, &mut viewer, 1.0, 0.0, vec![]);
    frame(&context, &mut viewer, 1.0, 0.1, events(at, true));
    frame(&context, &mut viewer, 1.0, 0.14, events(at, false));
    let before = viewer.pan;
    frame(&context, &mut viewer, 1.0, 0.59, events(at, true));
    frame(
        &context,
        &mut viewer,
        1.0,
        0.62,
        vec![Event::PointerMoved(at + egui::vec2(8.0, 0.0))],
    );
    assert_eq!(
        viewer.pan, before,
        "a pending reset must not visibly pan the photo"
    );
    frame(
        &context,
        &mut viewer,
        1.0,
        0.64,
        events(at + egui::vec2(8.0, 0.0), false),
    );
    assert!(viewer.fit);
    assert_eq!(viewer.pan, Vec2::ZERO);
}

#[test]
fn progressive_preview_aperture_preserves_full_content_and_canonical_framing() {
    fn geometry(output: &FullOutput, texture: egui::TextureId) -> (Rect, Rect) {
        let meshes: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == texture => Some(mesh),
                _ => None,
            })
            .collect();
        assert_eq!(
            meshes.len(),
            1,
            "the fixture must paint the actual image mesh"
        );
        let points: Vec<_> = meshes[0].vertices.iter().map(|vertex| vertex.pos).collect();
        let uv: Vec<_> = meshes[0].vertices.iter().map(|vertex| vertex.uv).collect();
        (Rect::from_points(&points), Rect::from_points(&uv))
    }
    let context = Context::default();
    let mut viewer = Viewer {
        source_size: [7_008, 4_672],
        overview: true,
        ..Default::default()
    };
    let mut reference: Option<Rect> = None;
    let mut saw_rounding_correction = false;
    // Include the actual medium JPEG geometry, rounded display reductions,
    // another frame's rounded reduction, and the high-resolution cache tier.
    for (step, size) in [
        [240, 160],
        [480, 321],
        [320, 214],
        [640, 427],
        [608, 405],
        [400, 267],
        [1_616, 1_080],
        [1_920, 1_280],
    ]
    .into_iter()
    .enumerate()
    {
        viewer.texture = Some(context.load_texture(
            format!("aperture-frame-{step}"),
            egui::ColorImage::new(size, vec![Color32::WHITE; size[0] * size[1]]),
            egui::TextureOptions::LINEAR,
        ));
        let output = frame(&context, &mut viewer, 1.25, step as f64, vec![]);
        let (bounds, uv) = geometry(&output, viewer.texture.as_ref().unwrap().id());
        if let Some(reference) = reference {
            assert!((bounds.min - reference.min).length() < 0.002);
            assert!(
                (bounds.max - reference.max).length() < 0.002,
                "display aperture changed from {reference:?} to {bounds:?} at {size:?}"
            );
        } else {
            reference = Some(bounds);
        }
        assert_eq!(
            uv,
            Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            "integer resize rounding cannot remove any camera image content"
        );
        assert!(
            (bounds.width() / bounds.height() - 1.5).abs() < 1e-6,
            "full source content must still occupy the canonical3:2 aperture"
        );
        saw_rounding_correction |= (size[0] as f32 / size[1] as f32 - 1.5).abs() > 0.0001;
    }
    assert!(
        saw_rounding_correction,
        "fixture must exercise rounded medium-preview geometry"
    );

    // A genuinely incompatible4:3 thumbnail is not made to look compatible by
    // cropping away substantial content. The source reader must reject it;
    // the generic viewer preserves its full UVs if explicitly given one.
    viewer.texture = Some(context.load_texture(
        "incompatible-four-three",
        egui::ColorImage::new([160, 120], vec![Color32::WHITE; 160 * 120]),
        egui::TextureOptions::LINEAR,
    ));
    let output = frame(&context, &mut viewer, 1.25, 9.0, vec![]);
    let (bounds, uv) = geometry(&output, viewer.texture.as_ref().unwrap().id());
    assert_eq!(uv, Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)));
    assert!(
        (bounds.height() - reference.unwrap().height()).abs() > 10.0,
        "negative control must expose the old4:3/3:2 fit change"
    );
}

fn painted_layers(
    output: &FullOutput,
    ids: &[egui::TextureId],
) -> Vec<(egui::TextureId, Rect, u8)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if ids.contains(&mesh.texture_id) => {
                assert_eq!(mesh.vertices.len(), 4);
                let alpha = mesh.vertices[0].color.a();
                assert!(mesh.vertices.iter().all(|vertex| vertex.color.a() == alpha));
                Some((
                    mesh.texture_id,
                    Rect::from_points(
                        &mesh
                            .vertices
                            .iter()
                            .map(|vertex| vertex.pos)
                            .collect::<Vec<_>>(),
                    ),
                    alpha,
                ))
            }
            _ => None,
        })
        .collect()
}

fn preview_texture(context: &Context, name: &str, size: [usize; 2]) -> TextureHandle {
    context.load_texture(
        name,
        egui::ColorImage::new(size, vec![Color32::WHITE; size[0] * size[1]]),
        egui::TextureOptions::LINEAR,
    )
}

#[test]
fn same_capture_resolution_reveal_advances_smoothly_at_one_fixed_aperture() {
    let context = Context::default();
    let small = preview_texture(&context, "same-frame-overview", [96, 65]);
    let full = preview_texture(&context, "same-frame-high", [960, 641]);
    let ids = [small.id(), full.id()];
    let mut viewer = Viewer::default();
    viewer.install_source(&small, [7_008, 4_672], true, (4, 72));
    let before = frame(&context, &mut viewer, 1.25, 10.0, vec![]);
    let expected = painted_layers(&before, &ids)[0].1;
    viewer.install_source(&full, [7_008, 4_672], true, (4, 72));
    assert!(
        viewer.transitioning(),
        "higher resolution of the same capture must reveal"
    );
    let mut alphas = Vec::new();
    for (step, time) in [10.1, 10.155, 10.21, 10.265, 10.34].into_iter().enumerate() {
        let output = frame(&context, &mut viewer, 1.25, time, vec![]);
        let layers = painted_layers(&output, &ids);
        assert!(
            layers.len() <= 2,
            "a reveal must retain at most two image layers"
        );
        for (_, bounds, _) in &layers {
            assert!((bounds.min - expected.min).length() < 0.002);
            assert!((bounds.max - expected.max).length() < 0.002);
        }
        let alpha = layers
            .iter()
            .find(|(id, _, _)| *id == full.id())
            .map(|(_, _, alpha)| *alpha)
            .unwrap_or(0);
        alphas.push(alpha);
        if step < 4 {
            assert_eq!(layers.first().unwrap().0, small.id());
            assert_eq!(
                layers.first().unwrap().2,
                255,
                "old same-frame base must remain opaque"
            );
        } else {
            assert_eq!(layers.len(), 1);
            assert!(!viewer.transitioning());
        }
        // Re-polling a cached source must not restart an in-progress reveal.
        viewer.install_source(&full, [7_008, 4_672], true, (4, 72));
    }
    assert_eq!(alphas[0], 0);
    assert!((30..=50).contains(&alphas[1]));
    assert!((120..=135).contains(&alphas[2]));
    assert!((205..=225).contains(&alphas[3]));
    assert_eq!(alphas[4], 255);
    assert!(alphas.windows(2).all(|pair| pair[0] < pair[1]));
}

#[test]
fn reveal_never_blends_different_captures_or_import_generations() {
    let context = Context::default();
    let small = preview_texture(&context, "old-overview", [96, 64]);
    let full = preview_texture(&context, "old-high", [960, 640]);
    let next = preview_texture(&context, "different-capture", [960, 640]);
    let new_import = preview_texture(&context, "new-bracket-same-index", [1_920, 1_280]);
    let ids = [small.id(), full.id(), next.id(), new_import.id()];
    let mut viewer = Viewer::default();
    viewer.install_source(&small, [3_000, 2_000], true, (0, 7));
    viewer.install_source(&full, [3_000, 2_000], true, (0, 7));
    frame(&context, &mut viewer, 1.0, 0.0, vec![]);
    let middle = frame(&context, &mut viewer, 1.0, 0.11, vec![]);
    assert_eq!(
        painted_layers(&middle, &ids).len(),
        2,
        "fixture must really interrupt a reveal"
    );
    viewer.install_source(&next, [3_000, 2_000], true, (0, 8));
    let output = frame(&context, &mut viewer, 1.0, 0.12, vec![]);
    let layers = painted_layers(&output, &ids);
    assert_eq!(layers.len(), 1);
    assert_eq!((layers[0].0, layers[0].2), (next.id(), 255));
    assert!(!viewer.transitioning());
    viewer.install_source(&new_import, [3_000, 2_000], true, (1, 8));
    let output = frame(&context, &mut viewer, 1.0, 0.13, vec![]);
    assert_eq!(painted_layers(&output, &ids).len(), 1);
    assert!(
        !viewer.transitioning(),
        "same numeric index from a new import is a different capture"
    );
}

#[test]
fn reveal_preserves_inspection_and_retargeting_retains_only_the_immediate_previous_texture() {
    let context = Context::default();
    let small = preview_texture(&context, "inspection-overview", [96, 64]);
    let mut viewer = Viewer {
        fit: false,
        zoom: 3.5,
        pan: egui::vec2(17.3, -9.2),
        ..Default::default()
    };
    viewer.install_source(&small, [3_000, 2_000], true, (0, 7));
    let original_pan = viewer.pan;
    let initial = frame(&context, &mut viewer, 1.5, 0.0, vec![]);
    let expected = painted_layers(&initial, &[small.id()])[0].1;
    let mut previous = small;
    for (index, side) in [192, 384, 768].into_iter().enumerate() {
        let next = preview_texture(
            &context,
            &format!("inspection-{side}"),
            [side, side * 2 / 3],
        );
        viewer.install_source(&next, [3_000, 2_000], true, (0, 7));
        let output = frame(
            &context,
            &mut viewer,
            1.5,
            0.02 * (index + 1) as f64,
            vec![],
        );
        let layers = painted_layers(&output, &[previous.id(), next.id()]);
        assert_eq!(viewer.pan, original_pan);
        assert_eq!(layers.len(), 2);
        for (_, bounds, _) in layers {
            assert!((bounds.min - expected.min).length() < 0.002);
            assert!((bounds.max - expected.max).length() < 0.002);
        }
        assert_eq!(viewer.reveal.as_ref().unwrap().previous.id(), previous.id());
        previous = next;
    }
    viewer.cancel_reveal();
    assert!(!viewer.transitioning());
    let output = frame(&context, &mut viewer, 1.5, 0.1, vec![]);
    assert_eq!(painted_layers(&output, &[previous.id()]).len(), 1);
}
