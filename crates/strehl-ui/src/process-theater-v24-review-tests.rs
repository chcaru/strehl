//! Independent final-workspace witnesses: real wheel events and actual painted
//! photograph meshes, including transitions that can cross a layout boundary.
use super::*;
use crate::{pipeline::PipelineProgress, workbench::SourcePhoto};

fn data<'a>(
    progress: &'a PipelineProgress,
    photos: &'a [SourcePhoto],
    final_image: &'a TextureHandle,
) -> Input<'a> {
    Input {
        epoch: 3,
        progress,
        frame_count: 12,
        selected: 4,
        inspected_pair: None,
        photos,
        inspection_photos: photos,
        surfaces: &[],
        output: Some(final_image),
        output_size: Some([240, 160]),
    }
}
fn progress() -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes : 120 x 80 per CFA plane\ncoverage : field of view scaled to 0.9500 so that EVERY frame covers every pixel\nbands : 7 Laplacian levels + 1 base, coarsest 1 x 1\nwrote : result.tiff (240 x 160, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
    progress.mark_complete();
    progress
}
fn paint(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
    modifiers: egui::Modifiers,
) -> (egui::FullOutput, Option<Rect>) {
    let mut region = None;
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1200.0, 900.0))),
            time: Some(time),
            events,
            modifiers,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.show_with_ribbon(
                        ui,
                        Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(1180.0, 600.0)),
                        &input,
                        &mut Response::default(),
                        Some(Rect::from_min_size(
                            egui::pos2(10.0, 620.0),
                            egui::vec2(1180.0, 260.0),
                        )),
                    );
                    region = field.result_photo.hover_region(ui, field.scales.aperture());
                });
        },
    );
    (output, region)
}
fn photograph(output: &egui::FullOutput, id: egui::TextureId) -> Option<Rect> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == id && !mesh.vertices.is_empty() => {
                Some(Rect::from_points(
                    &mesh
                        .vertices
                        .iter()
                        .map(|vertex| vertex.pos)
                        .collect::<Vec<_>>(),
                ))
            }
            _ => None,
        })
        .filter(|rect| rect.bottom() < 620.0)
        .max_by(|a, b| a.area().total_cmp(&b.area()))
}
fn texture(ctx: &egui::Context, name: &str, color: Color32) -> TextureHandle {
    ctx.load_texture(
        name,
        egui::ColorImage::filled([60, 40], color),
        egui::TextureOptions::NEAREST,
    )
}
fn wheel(ctrl: bool, at: Pos2) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(at),
        egui::Event::MouseWheel {
            unit: egui::MouseWheelUnit::Point,
            delta: egui::vec2(0.0, 60.0),
            modifiers: egui::Modifiers {
                ctrl,
                command: ctrl,
                ..Default::default()
            },
        },
    ]
}

#[test]
fn probe_resize_does_not_zoom_or_prime_the_next_real_zoom_undo_transaction() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    let final_image = texture(&ctx, "review-final-control", Color32::GOLD);
    let input = data(&progress, &[], &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![], egui::Modifiers::NONE);
    let settled = paint(&mut field, &ctx, input, 0.5, vec![], egui::Modifiers::NONE).0;
    let at = photograph(&settled, final_image.id())
        .expect("real final image mesh")
        .center();
    let small = paint(
        &mut field,
        &ctx,
        input,
        0.7,
        vec![egui::Event::PointerMoved(at)],
        egui::Modifiers::NONE,
    )
    .1
    .expect("real hover region before resize");
    let before = field.exploration();
    let history = field.history_depths();
    let larger = paint(
        &mut field,
        &ctx,
        input,
        1.0,
        wheel(true, at),
        egui::Modifiers {
            ctrl: true,
            command: true,
            ..Default::default()
        },
    )
    .1
    .expect("resize keeps region active");
    assert!(larger.width() > small.width() && larger.height() > small.height());
    assert!(
        field.exploration() == before,
        "Ctrl-wheel only resizes the transient observer"
    );
    assert_eq!(field.history_depths(), history);
    let mut saw_derived_tail = false;
    for step in 1..=5 {
        paint(
            &mut field,
            &ctx,
            input,
            1.0 + f64::from(step) * 0.016,
            vec![],
            egui::Modifiers::NONE,
        );
        saw_derived_tail |= ctx.input(|state| (state.zoom_delta() - 1.0).abs() > 1e-6);
        assert!(
            field.exploration() == before,
            "consumed Ctrl-wheel must not zoom on a later idle frame"
        );
        assert_eq!(field.history_depths(), history);
    }
    assert!(
        saw_derived_tail,
        "fixture must exercise egui's actual private zoom tail"
    );
    // A real zoom100ms later must not be absorbed into the preceding non-edit.
    paint(
        &mut field,
        &ctx,
        input,
        1.1,
        wheel(false, at),
        egui::Modifiers::NONE,
    );
    paint(&mut field, &ctx, input, 1.5, vec![], egui::Modifiers::NONE);
    assert!(
        field.scales.aperture().width() < 0.99,
        "ordinary wheel negative control actually zooms"
    );
    assert_eq!(field.history_depths().0, history.0 + 1);
    assert!(field.undo());
    assert!(
        field.exploration() == before,
        "undo restores the actual photograph view"
    );
}

#[test]
fn automatic_inspection_expansion_keeps_one_comparison_axis_for_every_visible_frame() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let progress = progress();
    let final_image = texture(&ctx, "review-final-morph", Color32::GOLD);
    let source_image = texture(&ctx, "review-camera-morph", Color32::LIGHT_BLUE);
    let photos = [SourcePhoto {
        epoch: 3,
        index: 4,
        aperture: [6000, 4000],
        texture: source_image.clone(),
    }];
    let input = data(&progress, &photos, &final_image);
    paint(&mut field, &ctx, input, 0.0, vec![], egui::Modifiers::NONE);
    paint(&mut field, &ctx, input, 0.5, vec![], egui::Modifiers::NONE);
    let before = field.exploration();
    field.hover_source = Some(4);
    let mut axes = Vec::new();
    let mut saw_transition = false;
    for step in 0..=20 {
        let output = paint(
            &mut field,
            &ctx,
            input,
            0.52 + f64::from(step) * 0.02,
            vec![],
            egui::Modifiers::NONE,
        )
        .0;
        saw_transition |= field.inspection_mix > 0.01 && field.inspection_mix < 0.99;
        if let (Some(final_rect), Some(camera_rect)) = (
            photograph(&output, final_image.id()),
            photograph(&output, source_image.id()),
        ) {
            assert!(!final_rect.intersects(camera_rect));
            let separation = camera_rect.center() - final_rect.center();
            axes.push(separation.x.abs() > separation.y.abs());
        }
    }
    assert!(
        saw_transition,
        "fixture must actually paint intermediate focus geometry"
    );
    assert!(
        axes.len() > 5,
        "both real images must be present across the transition"
    );
    assert!(
        axes.iter().all(|axis| *axis == axes[0]),
        "automatic expansion must not flip Rows/Columns halfway through: {axes:?}"
    );
    assert!(
        field.exploration() == before,
        "sticky hover remains a modifier, not a durable edit"
    );
    assert!(
        field.inspecting(),
        "local timeline controls must reflect the visible source comparison"
    );
}
