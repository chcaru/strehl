//! Independent integration witnesses: source hover reaches the real camera
//! pixels and final admission without becoming a durable selection or edit.
use super::*;
use crate::{pipeline::PipelineProgress, workbench::SourcePhoto};

fn ribbon() -> Rect {
    Rect::from_min_size(egui::pos2(10.0, 620.0), egui::vec2(1180.0, 238.0))
}
fn progress() -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes : 120 x 80 per CFA plane\ncoverage : field of view scaled to 0.9500 so that EVERY frame covers every pixel\nbands : 7 Laplacian levels + 1 base, coarsest 1 x 1\nwrote : result.tiff (240 x 160, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
    progress.mark_complete();
    progress
}
fn source(ctx: &egui::Context, index: usize) -> SourcePhoto {
    SourcePhoto {
        epoch: 1,
        index,
        aperture: [6000, 4000],
        texture: ctx.load_texture(
            format!("hover-camera-{index}"),
            egui::ColorImage::filled([60, 40], Color32::from_gray(30 + index as u8 * 15)),
            egui::TextureOptions::NEAREST,
        ),
    }
}
fn data<'a>(
    progress: &'a PipelineProgress,
    photos: &'a [SourcePhoto],
    result: &'a TextureHandle,
) -> Input<'a> {
    Input {
        epoch: 1,
        progress,
        frame_count: 12,
        selected: 2,
        inspected_pair: None,
        photos,
        inspection_photos: photos,
        surfaces: &[],
        output: Some(result),
        output_size: Some([240, 160]),
    }
}
fn paint(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (Response, egui::FullOutput) {
    let mut response = Response::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1200.0, 880.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.navigation_shortcuts(ui, &mut response);
                    field.show_with_ribbon(
                        ui,
                        Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(1180.0, 600.0)),
                        &input,
                        &mut response,
                        Some(ribbon()),
                    );
                });
        },
    );
    (response, output)
}
fn point(output: &egui::FullOutput, frame: usize) -> Pos2 {
    let label_y = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Full image" => {
                Some(text.visual_bounding_rect().center().y)
            }
            _ => None,
        })
        .expect("actual timeline admission lane");
    let axis = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && points[1].x - points[0].x > 600.0
                    && (label_y + 1.0..label_y + 25.0).contains(&points[0].y) =>
            {
                Some(*points)
            }
            _ => None,
        })
        .unwrap();
    axis[0].lerp(axis[1], frame as f32 / 11.0) - egui::vec2(0.0, 4.0)
}
fn image(output: &egui::FullOutput, texture: egui::TextureId) -> Option<Rect> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == texture && !mesh.vertices.is_empty() => {
                Some(Rect::from_points(
                    &mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>(),
                ))
            }
            _ => None,
        })
        .filter(|rect| rect.bottom() < ribbon().top())
        .max_by(|a, b| a.area().total_cmp(&b.area()))
}
fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}
fn result(ctx: &egui::Context) -> TextureHandle {
    ctx.load_texture(
        "finished-hover-anchor",
        egui::ColorImage::filled([120, 80], Color32::GOLD),
        egui::TextureOptions::NEAREST,
    )
}

#[test]
fn source_hover_uses_actual_camera_pixels_and_never_changes_the_saved_exploration() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    let photos: Vec<_> = (0..12).map(|i| source(&ctx, i)).collect();
    let final_image = result(&ctx);
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![]);
    let clean = paint(&mut field, &ctx, input, 0.5, vec![]).1;
    let before = field.exploration();
    let history = field.history_depths();
    let commits = field.history_commits();
    let at = point(&clean, 7);
    let hovered = paint(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(at)],
    );
    assert!(
        hovered.0.selected.is_none(),
        "hover must not mutate app selection"
    );
    assert_eq!(
        field.inspection_frame(),
        Some(7),
        "existing cache priority must request the hovered capture"
    );
    assert!(field.inspected_source.is_none());
    let settled = paint(&mut field, &ctx, input, 1.1, vec![]).1;
    let photo = image(&settled, final_image.id()).expect("final remains visible");
    let camera =
        image(&settled, photos[7].texture.id()).expect("real hovered camera appears beside it");
    assert!(!photo.intersects(camera));
    assert!(field.exploration() == before);
    assert_eq!(field.history_depths(), history);
    assert_eq!(field.history_commits(), commits);
    paint(
        &mut field,
        &ctx,
        input,
        1.2,
        vec![egui::Event::PointerMoved(egui::pos2(1.0, 1.0))],
    );
    paint(&mut field, &ctx, input, 1.6, vec![]);
    let retained = paint(&mut field, &ctx, input, 1.9, vec![]).1;
    assert_eq!(field.inspection_frame(), Some(7));
    assert!(image(&retained, photos[7].texture.id()).is_some());
    assert!(image(&retained, final_image.id()).is_some());
    assert!(field.exploration() == before);
    assert_eq!(field.history_depths(), history);
    paint(
        &mut field,
        &ctx,
        input,
        2.0,
        vec![egui::Event::Key {
            key: egui::Key::Escape,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        }],
    );
    let restored = paint(&mut field, &ctx, input, 2.8, vec![]).1;
    assert_eq!(field.inspection_frame(), None);
    assert_eq!(
        image(&restored, final_image.id()),
        image(&clean, final_image.id()),
        "explicit Escape restores the clean final viewport"
    );
}

#[test]
fn click_commits_hovered_source_once_and_undo_cannot_rearm_its_stationary_pointer() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    let photos: Vec<_> = (0..12).map(|i| source(&ctx, i)).collect();
    let final_image = result(&ctx);
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![]);
    let clean = paint(&mut field, &ctx, input, 0.5, vec![]).1;
    let at = point(&clean, 7);
    paint(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(at)],
    );
    let baseline = field.history_depths();
    paint(&mut field, &ctx, input, 1.0, vec![button(at, true)]);
    let committed = paint(&mut field, &ctx, input, 1.1, vec![button(at, false)]).0;
    assert_eq!(committed.selected, Some(7));
    assert_eq!(field.inspected_source, Some(7));
    assert_eq!(field.history_depths(), (baseline.0 + 1, 0));
    let across = point(&clean, 3);
    paint(
        &mut field,
        &ctx,
        input,
        1.4,
        vec![egui::Event::PointerMoved(across)],
    );
    assert_eq!(field.inspection_frame(), Some(3));
    assert_eq!(
        field.inspected_source,
        Some(7),
        "transient hover cannot overwrite a held comparison"
    );
    assert!(field.undo());
    let undone = paint(&mut field, &ctx, input, 1.6, vec![]).0;
    assert!(undone.return_live);
    assert_eq!(
        field.inspection_frame(),
        None,
        "undo cancels hover and suppresses the stationary pointer"
    );
    assert!(field.redo());
    let redone = paint(&mut field, &ctx, input, 1.8, vec![]).0;
    assert_eq!(redone.selected, Some(7));
    assert_eq!(field.inspection_frame(), Some(7));
}

#[test]
fn hover_companion_accepts_the_pointer_and_wheel_without_committing_source_selection() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    let photos: Vec<_> = (0..12).map(|i| source(&ctx, i)).collect();
    let final_image = result(&ctx);
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![]);
    let clean = paint(&mut field, &ctx, input, 0.5, vec![]).1;
    let at = point(&clean, 7);
    paint(
        &mut field,
        &ctx,
        input,
        0.8,
        vec![egui::Event::PointerMoved(at)],
    );
    let opened = paint(&mut field, &ctx, input, 1.1, vec![]).1;
    let camera = image(&opened, photos[7].texture.id()).unwrap();
    assert!(
        camera.center().y < ribbon().top() - 40.0,
        "the companion must be genuinely beyond the strip grace band"
    );
    let baseline = field.history_depths();
    paint(
        &mut field,
        &ctx,
        input,
        1.2,
        vec![egui::Event::PointerMoved(camera.center())],
    );
    let inspected = paint(&mut field, &ctx, input, 2.0, vec![]);
    assert_eq!(
        field.inspection_frame(),
        Some(7),
        "the companion remains available while its image is under the pointer"
    );
    assert!(field.inspected_source.is_none() && inspected.0.selected.is_none());
    assert_eq!(field.history_depths(), baseline);
    let camera = image(&inspected.1, photos[7].texture.id()).unwrap();
    paint(
        &mut field,
        &ctx,
        input,
        2.05,
        vec![egui::Event::PointerMoved(camera.center())],
    );
    let zoomed = paint(
        &mut field,
        &ctx,
        input,
        2.1,
        vec![egui::Event::MouseWheel {
            unit: egui::MouseWheelUnit::Point,
            delta: egui::vec2(0.0, 80.0),
            modifiers: egui::Modifiers::NONE,
        }],
    );
    assert_eq!(zoomed.0.selected, None);
    assert_eq!(field.inspected_source, None);
    assert_eq!(field.inspection_frame(), Some(7));
    assert!(
        field.scales.detail_zoom() > 1.0,
        "camera wheel must drive shared final and source magnification"
    );
    assert_eq!(field.history_depths(), (baseline.0 + 1, 0));
    let painted = paint(&mut field, &ctx, input, 2.3, vec![]).1;
    assert!(matching_regions(&painted, final_image.id(), photos[7].texture.id()).width() < 0.99);
    assert!(field.undo());
    paint(&mut field, &ctx, input, 2.4, vec![]);
    assert_eq!(field.inspection_frame(), None);
    assert_eq!(field.source_zoom, 1.0);
}

fn photo_mesh(output: &egui::FullOutput, texture: egui::TextureId) -> (Rect, Rect) {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == texture && !mesh.vertices.is_empty() => {
                let destination =
                    Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
                let uv = Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>());
                (destination.bottom() < ribbon().top()).then_some((destination, uv))
            }
            _ => None,
        })
        .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
        .expect("actual photograph mesh")
}

fn wheel() -> egui::Event {
    egui::Event::MouseWheel {
        unit: egui::MouseWheelUnit::Point,
        delta: egui::vec2(0.0, 130.0),
        modifiers: egui::Modifiers::NONE,
    }
}

fn matching_regions(
    output: &egui::FullOutput,
    final_texture: egui::TextureId,
    camera_texture: egui::TextureId,
) -> Rect {
    let (photo, final_uv) = photo_mesh(output, final_texture);
    let (source, camera_uv) = photo_mesh(output, camera_texture);
    assert!(
        !photo.intersects(source),
        "comparison is two separate photographs"
    );
    assert!(
        (photo.width() - source.width()).abs() < 0.01
            && (photo.height() - source.height()).abs() < 0.01,
        "matching aspect photographs receive equal area"
    );
    assert!(
        (final_uv.min - camera_uv.min).length() < 1e-5
            && (final_uv.max - camera_uv.max).length() < 1e-5,
        "both actual meshes paint the same normalized region"
    );
    if camera_uv.width() < 0.99 {
        assert!(
            output.shapes.iter().any(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh)
                    if mesh.texture_id == camera_texture && !mesh.vertices.is_empty() =>
                {
                    let rect =
                        Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
                    rect.width() <= 112.1
                        && rect.height() <= 78.1
                        && source.contains_rect(rect.expand(4.0))
                }
                _ => false,
            }),
            "the source overview belongs inside the fitted photograph, including its surrounding inset margin"
        );
    }
    final_uv
}

#[test]
fn source_and_final_wheel_and_pan_share_actual_painted_regions_in_both_directions() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    let photos: Vec<_> = (0..12).map(|i| source(&ctx, i)).collect();
    let final_image = result(&ctx);
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![]);
    paint(&mut field, &ctx, input, 0.5, vec![]);
    field.inspect_frame(7);
    for step in 0..=24 {
        paint(
            &mut field,
            &ctx,
            input,
            0.51 + f64::from(step) * 0.02,
            vec![],
        );
    }
    let opened = paint(&mut field, &ctx, input, 1.0, vec![]).1;
    let camera = photo_mesh(&opened, photos[7].texture.id()).0;
    matching_regions(&opened, final_image.id(), photos[7].texture.id());
    assert!(opened.shapes.iter().any(|s| matches!(&s.shape, egui::Shape::Text(t) if t.galley.text() == "LINKED REGION · APPROXIMATE")), "normalized camera correspondence is not called registration");
    let at = camera.min + camera.size() * egui::vec2(0.62, 0.43);
    paint(
        &mut field,
        &ctx,
        input,
        1.1,
        vec![egui::Event::PointerMoved(at)],
    );
    paint(
        &mut field,
        &ctx,
        input,
        1.2,
        vec![egui::Event::PointerMoved(at), wheel()],
    );
    let enlarged = paint(&mut field, &ctx, input, 1.5, vec![]).1;
    let first = matching_regions(&enlarged, final_image.id(), photos[7].texture.id());
    assert!(first.width() < 0.8, "source wheel actually zoomed");
    let before_pin = first.center();
    let delta = egui::vec2(30.0, -16.0);
    paint(&mut field, &ctx, input, 1.7, vec![button(at, true)]);
    paint(
        &mut field,
        &ctx,
        input,
        1.8,
        vec![egui::Event::PointerMoved(at + delta)],
    );
    let panned = paint(
        &mut field,
        &ctx,
        input,
        1.9,
        vec![button(at + delta, false)],
    )
    .1;
    let after = matching_regions(&panned, final_image.id(), photos[7].texture.id());
    let expected = before_pin - delta / camera.size() * first.size();
    assert!(
        (after.center() - expected).length() < 1e-5,
        "camera drag moves the final region by its actual displayed normalized distance"
    );
    let final_rect = photo_mesh(&panned, final_image.id()).0;
    let at = final_rect.center();
    paint(
        &mut field,
        &ctx,
        input,
        2.2,
        vec![egui::Event::PointerMoved(at), wheel()],
    );
    let enlarged = paint(&mut field, &ctx, input, 2.5, vec![]).1;
    let before = matching_regions(&enlarged, final_image.id(), photos[7].texture.id());
    assert!(
        before.width() < after.width(),
        "final wheel changes shared magnification too"
    );
    let delta = egui::vec2(-20.0, 12.0);
    paint(&mut field, &ctx, input, 2.7, vec![button(at, true)]);
    paint(
        &mut field,
        &ctx,
        input,
        2.8,
        vec![egui::Event::PointerMoved(at + delta)],
    );
    let moved = paint(
        &mut field,
        &ctx,
        input,
        2.9,
        vec![button(at + delta, false)],
    )
    .1;
    let after = matching_regions(&moved, final_image.id(), photos[7].texture.id());
    let expected = before.center() - delta / final_rect.size() * before.size();
    assert!(
        (after.center() - expected).length() < 1e-5,
        "final drag moves the camera's normalized region in reverse direction too"
    );
}

#[test]
fn comparison_double_click_fits_both_photos_without_dismissing_the_reference() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    let photos: Vec<_> = (0..12).map(|i| source(&ctx, i)).collect();
    let final_image = result(&ctx);
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![]);
    paint(&mut field, &ctx, input, 0.5, vec![]);
    field.inspect_frame(7);
    for step in 0..=24 {
        paint(
            &mut field,
            &ctx,
            input,
            0.51 + f64::from(step) * 0.02,
            vec![],
        );
    }
    let mut shown = paint(&mut field, &ctx, input, 1.0, vec![]).1;
    for (step, texture) in [photos[7].texture.id(), final_image.id()]
        .into_iter()
        .enumerate()
    {
        let t = 2.0 + step as f64 * 2.0;
        let at = photo_mesh(&shown, texture).0.center();
        paint(
            &mut field,
            &ctx,
            input,
            t - 0.1,
            vec![egui::Event::PointerMoved(at)],
        );
        paint(
            &mut field,
            &ctx,
            input,
            t,
            vec![egui::Event::PointerMoved(at), wheel()],
        );
        shown = paint(&mut field, &ctx, input, t + 0.3, vec![]).1;
        assert!(matching_regions(&shown, final_image.id(), photos[7].texture.id()).width() < 0.8);
        paint(&mut field, &ctx, input, t + 0.4, vec![button(at, true)]);
        paint(&mut field, &ctx, input, t + 0.44, vec![button(at, false)]);
        paint(&mut field, &ctx, input, t + 0.65, vec![button(at, true)]);
        paint(
            &mut field,
            &ctx,
            input,
            t + 0.68,
            vec![egui::Event::PointerMoved(at + egui::vec2(8.0, 0.0))],
        );
        paint(
            &mut field,
            &ctx,
            input,
            t + 0.72,
            vec![button(at + egui::vec2(8.0, 0.0), false)],
        );
        shown = paint(&mut field, &ctx, input, t + 1.0, vec![]).1;
        assert_eq!(
            field.inspection_frame(),
            Some(7),
            "fit preserves the reference being compared"
        );
        assert!(
            (matching_regions(&shown, final_image.id(), photos[7].texture.id()).width() - 1.0)
                .abs()
                < 1e-5,
            "jitter-tolerant double click fits both images"
        );
    }
}

#[test]
fn admission_miniatures_use_only_final_photo_coordinates_and_link_the_selected_detail_size() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = progress();
    for level in 0..8 {
        let width = 120usize.div_ceil(1 << level).min(12);
        let height = 80usize.div_ceil(1 << level).min(8);
        progress.admission_archive.ingest(
            &crate::pipeline::DiagnosticSurface {
                sequence: level as u64 + 1,
                frame: 7,
                level,
                kind: DiagnosticKind::GateSupport,
                scope: crate::pipeline::DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width,
                height,
                min: 0.0,
                max: 1.0,
                pixels: (0..width * height)
                    .map(|i| if i == 0 { 255 } else { 0 })
                    .collect::<Vec<_>>()
                    .into(),
                folded: 1,
            },
            [120, 80],
        );
    }
    let photos: Vec<_> = (0..12).map(|i| source(&ctx, i)).collect();
    let final_image = result(&ctx);
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![]);
    paint(&mut field, &ctx, input, 0.5, vec![]);
    field.inspect_frame(7);
    paint(&mut field, &ctx, input, 0.6, vec![]);
    let shown = paint(&mut field, &ctx, input, 1.0, vec![]).1;
    let companion = field.source_relation_rect.unwrap();
    let footer = Rect::from_min_max(
        companion.left_bottom() + egui::vec2(10.0, -51.0),
        companion.max - egui::vec2(10.0, 1.0),
    );
    let maps: Vec<_> = shown
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == final_image.id() => {
                let rect =
                    Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
                footer.contains_rect(rect).then_some(rect)
            }
            _ => None,
        })
        .collect();
    assert_eq!(
        maps.len(),
        8,
        "every actual detail size and the base are shown together"
    );
    for (level, map) in maps.iter().enumerate() {
        let spacing = 1usize << level;
        let grid = [120usize.div_ceil(spacing), 80usize.div_ceil(spacing)];
        let first_coefficient = [
            grid[0] / (2 * grid[0].min(12)),
            grid[1] / (2 * grid[1].min(8)),
        ];
        let first = map.min
            + egui::vec2(
                (first_coefficient[0] * spacing) as f32 / 120.0 + 0.5 / 120.0,
                (first_coefficient[1] * spacing) as f32 / 80.0 + 0.5 / 80.0,
            ) * map.size();
        assert!(
            shown.shapes.iter().any(|s| matches!(&s.shape,
            egui::Shape::Circle(c) if c.fill == crate::process_sample_glyphs::level_color(level)
                && (c.center - first).length() < 0.001)),
            "only the actual transmitted coefficient is marked at detail size {level}"
        );
    }
    let at = maps[4].center();
    paint(
        &mut field,
        &ctx,
        input,
        1.2,
        vec![egui::Event::PointerMoved(at), button(at, true)],
    );
    paint(&mut field, &ctx, input, 1.24, vec![button(at, false)]);
    assert_eq!(
        field.level, 4,
        "miniature selects the same detail size as the final overlay"
    );
    assert_eq!(field.inspection_frame(), Some(7));
}

#[test]
fn compact_comparison_never_overlaps_detail_labels_or_hides_a_sparse_positive_by_stride_phase() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = progress();
    progress.bands = Some(15);
    let mut pixels = vec![0; 120 * 80];
    pixels[1] = 255; // deliberately misses every old fixed 50th sample
    progress.admission_archive.ingest(
        &crate::pipeline::DiagnosticSurface {
            sequence: 1,
            frame: 7,
            level: 0,
            kind: DiagnosticKind::GateSupport,
            scope: crate::pipeline::DiagnosticScope::Frame,
            scale: DiagnosticScale::Linear,
            width: 120,
            height: 80,
            min: 0.0,
            max: 1.0,
            pixels: pixels.into(),
            folded: 1,
        },
        [120, 80],
    );
    let photos: Vec<_> = (0..12).map(|i| source(&ctx, i)).collect();
    let final_image = result(&ctx);
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![]);
    paint(&mut field, &ctx, input, 0.5, vec![]);
    field.inspect_frame(7);
    paint(&mut field, &ctx, input, 0.6, vec![]);
    paint(&mut field, &ctx, input, 1.0, vec![]);
    let paint_panel = |field: &mut ProcessTheater, height: f32, time: f64| {
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(220.0, 140.0))),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        field.source_relation(
                            ui,
                            Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(180.0, height)),
                            &input,
                            &mut Response::default(),
                        );
                    });
            },
        )
    };
    let hidden = paint_panel(&mut field, 84.0, 1.2);
    assert!(
        !hidden.shapes.iter().any(
            |s| matches!(&s.shape, egui::Shape::Mesh(m) if m.texture_id == photos[7].texture.id())
        ),
        "opening transition must not paint a negative-height image canvas"
    );
    let compact = paint_panel(&mut field, 100.0, 1.4);
    assert!(
        compact
            .shapes
            .iter()
            .any(|s| matches!(&s.shape, egui::Shape::Circle(c)
        if c.radius == 0.7 && c.fill == crate::process_sample_glyphs::level_color(0))),
        "a true positive at index1 must survive drawing-budget thinning"
    );
    let footer_top = 10.0 + 100.0 - 51.0;
    let cell_width = (180.0 - 20.0 - 48.0) / 16.0;
    let labels: Vec<_> = compact
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            egui::Shape::Text(t)
                if t.galley.text().parse::<usize>().is_ok() && t.pos.y > footer_top =>
            {
                Some(t)
            }
            _ => None,
        })
        .collect();
    assert!(
        !labels.is_empty(),
        "single-digit sizes still fit and remain legible"
    );
    assert!(
        labels.iter().all(|t| t.galley.size().x <= cell_width - 2.0),
        "wide detail-size labels must defer to their tooltip instead of colliding with neighbors"
    );
}
