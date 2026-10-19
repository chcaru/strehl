use super::*;
use crate::{pipeline::PipelineProgress, workbench::SourcePhoto};

fn paint(
    row: &mut CaptureParticipation,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (ParticipationResponse, egui::FullOutput) {
    let mut response = ParticipationResponse::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 320.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = row.show(
                        ui,
                        bounds(),
                        &input,
                        &input.progress.admission_archive,
                        0,
                        Rect::from_min_max(Pos2::ZERO, egui::pos2(0.5, 1.0)),
                    );
                });
        },
    );
    (response, output)
}
fn bounds() -> Rect {
    Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(1040.0, HEIGHT))
}
fn image(output: &egui::FullOutput, id: egui::TextureId) -> Option<Rect> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Mesh(mesh) if mesh.texture_id == id && !mesh.vertices.is_empty() => Some(
            Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>()),
        ),
        _ => None,
    })
}
fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}
fn data<'a>(progress: &'a PipelineProgress, photos: &'a [SourcePhoto]) -> Input<'a> {
    Input {
        epoch: 1,
        progress,
        frame_count: 130,
        selected: 0,
        inspected_pair: None,
        photos,
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}

fn photo(ctx: &egui::Context, index: usize, size: [usize; 2]) -> SourcePhoto {
    SourcePhoto {
        epoch: 1,
        index,
        aperture: [600, 400],
        texture: ctx.load_texture(
            format!("pending-contact-{index}-{}", size[0]),
            egui::ColorImage::filled(size, Color32::from_rgb(index as u8, 80, 120)),
            egui::TextureOptions::LINEAR,
        ),
    }
}
fn packet(
    sequence: u64,
    frame: usize,
    level: usize,
    value: u8,
) -> crate::pipeline::DiagnosticSurface {
    crate::pipeline::DiagnosticSurface {
        sequence,
        frame,
        level,
        kind: crate::pipeline::DiagnosticKind::GateSupport,
        scope: crate::pipeline::DiagnosticScope::Frame,
        scale: crate::pipeline::DiagnosticScale::Linear,
        width: 4,
        height: 2,
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: vec![value; 8].into(),
    }
}

#[test]
fn graph_and_contact_row_have_the_same_outer_bounds_at_every_workspace_size() {
    for count in [1, 2, 12, 130, 299, 900] {
        for width in [300.0, 716.0, 1280.0, 1900.0] {
            for height in [120.0, HEIGHT, 340.0] {
                let rect = Rect::from_min_size(egui::pos2(20.0, 30.0), egui::vec2(width, height));
                let anchors = anchors_at_height(count, width, height);
                let mut layout = Layout::new(rect, count, anchors.len()).unwrap();
                for source in [false, true] {
                    layout.source_mode = source;
                    let lane = layout.lane(0);
                    assert_eq!(lane.left(), rect.left() + 6.0);
                    assert_eq!(lane.right(), rect.right() - 6.0);
                    assert_eq!(layout.cell(0, 0).left(), lane.left());
                    assert_eq!(layout.cell(0, layout.columns - 1).right(), lane.right());
                    if count > 1 {
                        assert!((layout.contact(0).left() - lane.left()).abs() < 0.0002);
                        assert!((layout.contact(count - 1).right() - lane.right()).abs() < 0.0002);
                        assert_eq!(layout.x(0), lane.left());
                        assert_eq!(layout.x(count - 1), lane.right());
                    } else {
                        assert_eq!(layout.x(0), lane.center().x);
                    }
                    for frame in 0..count {
                        assert_eq!(layout.index(layout.x(frame)), frame);
                    }
                    for column in 0..layout.columns {
                        let cell = layout.cell(0, column);
                        assert!(cell.left() >= lane.left() && cell.right() <= lane.right());
                        assert!(cell.width() > 0.0);
                        let range = layout.range(column);
                        assert!(
                            (layout.column_x(column)
                                - (layout.x(range.start) + layout.x(range.end - 1)) * 0.5)
                                .abs()
                                < 0.0002,
                            "pooled evidence uses actual capture coordinates rather than clipped bar centres"
                        );
                    }
                }
            }
        }
    }
}

#[test]
fn actual_full_width_graph_points_align_with_outer_photos_and_every130_hover_target() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    progress.analysis_size = Some([800, 600]);
    for frame in 0..130 {
        progress
            .admission_archive
            .ingest(&packet(frame as u64 + 1, frame, 0, 255), [800, 600]);
    }
    let photos: Vec<_> = (0..130).map(|frame| photo(&ctx, frame, [60, 40])).collect();
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, data(&progress, &photos), 0.0, vec![]);
    let (_, output) = paint(&mut row, &ctx, data(&progress, &photos), 0.1, vec![]);
    let first = image(&output, photos[0].texture.id()).unwrap();
    let last = image(&output, photos[129].texture.id()).unwrap();
    let points: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Circle(circle) if circle.fill == GREEN && circle.radius <= 3.0 => {
                Some(circle.center)
            }
            _ => None,
        })
        .collect();
    assert_eq!(
        points.len(),
        130,
        "real observed curve retains every capture"
    );
    assert!((points[0].x - first.left()).abs() < 0.0002);
    assert!((points[129].x - last.right()).abs() < 0.0002);
    assert!(
        first.width() > 100.0,
        "fixture exposes the old half-thumbnail inset defect"
    );
    let layout = Layout::new(bounds(), 130, row.anchors.len()).unwrap();
    assert!(row.anchors.len() < 20, "fixture must use sparse contacts");
    let builds = row.plot_builds;
    for (lane, y) in [layout.lane(0).center().y, first.center().y]
        .into_iter()
        .enumerate()
    {
        for frame in 0..130 {
            // Derive positions from painted photo edges, independent of x().
            let x = egui::lerp(first.left()..=last.right(), frame as f32 / 129.0);
            let (response, painted) = paint(
                &mut row,
                &ctx,
                data(&progress, &photos),
                0.2 + lane as f64 * 3.0 + frame as f64 * 0.02,
                vec![egui::Event::PointerMoved(egui::pos2(x, y))],
            );
            assert_eq!(
                response.hover_source,
                Some(frame),
                "lane{lane} frame{frame}"
            );
            assert_eq!(
                image(&painted, photos[frame].texture.id()),
                Some(layout.contact(frame))
            );
            let cursor=painted.shapes.iter().any(|shape| matches!(&shape.shape,
                egui::Shape::LineSegment{points,stroke} if stroke.color==ACCENT && (points[0].x-x).abs()<0.0002
                    && points[0].x==points[1].x && points[1].y-points[0].y>100.0));
            assert!(
                cursor,
                "cursor and actual selected capture share full-width axis"
            );
        }
    }
    assert_eq!(
        row.plot_builds, builds,
        "moving through260 points must reuse pooled evidence"
    );
}

#[test]
fn graph_edges_and_exact_thumbnail_clicks_distinguish_time_coordinate_from_card_identity() {
    for frame in [0, 129] {
        let ctx = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.mark_complete();
        let photos: Vec<_> = (0..130).map(|frame| photo(&ctx, frame, [60, 40])).collect();
        let mut row = CaptureParticipation::default();
        paint(&mut row, &ctx, data(&progress, &photos), 0.0, vec![]);
        let (_, initial) = paint(&mut row, &ctx, data(&progress, &photos), 0.1, vec![]);
        let card = image(&initial, photos[frame].texture.id()).unwrap();
        let layout = Layout::new(bounds(), 130, row.anchors.len()).unwrap();
        assert_ne!(
            layout.index(card.center().x),
            frame,
            "large edge cards overlap several time coordinates"
        );
        let (pressed, _) = paint(
            &mut row,
            &ctx,
            data(&progress, &photos),
            0.2,
            vec![
                egui::Event::PointerMoved(card.center()),
                button(card.center(), true),
            ],
        );
        assert_eq!(
            pressed.open_source,
            Some(frame),
            "deliberate click chooses the photo actually painted"
        );
        let target = if frame == 0 { 35 } else { 94 };
        let (dragged, _) = paint(
            &mut row,
            &ctx,
            data(&progress, &photos),
            0.3,
            vec![egui::Event::PointerMoved(egui::pos2(
                layout.x(target),
                card.center().y,
            ))],
        );
        assert_eq!(
            dragged.open_source,
            Some(target),
            "drag remains continuous after an exact card click"
        );
        let edge = if frame == 0 {
            layout.left - 40.0
        } else {
            layout.right + 40.0
        };
        let (beyond, _) = paint(
            &mut row,
            &ctx,
            data(&progress, &photos),
            0.4,
            vec![egui::Event::PointerMoved(egui::pos2(edge, card.center().y))],
        );
        assert_eq!(
            beyond.open_source,
            Some(frame),
            "held drag clamps to actual first/last capture"
        );
    }
}
