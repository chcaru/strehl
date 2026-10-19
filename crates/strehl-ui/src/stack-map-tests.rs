use super::*;

fn paint(
    context: &egui::Context,
    progress: &PipelineProgress,
    count: usize,
    time: f64,
    events: Vec<egui::Event>,
    previews: &[(usize, &egui::TextureHandle)],
) -> (Response, egui::FullOutput) {
    let mut response = Response::default();
    let output = context.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(740.0, HEIGHT))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |context| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(context, |ui| {
                    response = show(
                        ui,
                        progress,
                        count,
                        0,
                        Some(0),
                        previews,
                        Some([0, count.saturating_sub(1).min(11)]),
                    );
                });
        },
    );
    (response, output)
}

fn button(pos: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

fn text_values(output: &egui::FullOutput) -> Vec<&str> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.galley.text()),
            _ => None,
        })
        .collect()
}

#[test]
fn sparse_read_and_scale_observations_never_fill_a_capture_order_prefix() {
    let context = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest(
        "STREHL_UI_PROGRESS event=stage name=alignment total=10\n\
STREHL_UI_PROGRESS event=align-phase name=planes frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=7 completed=1 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=2 completed=6 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=10 completed=7 frames=10 total=10\n",
    );
    assert_eq!(
        progress
            .alignment_plane_observations
            .iter()
            .copied()
            .collect::<Vec<_>>(),
        [2, 7]
    );
    let (_, output) = paint(&context, &progress, 10, 0.0, vec![], &[]);
    assert!(text_values(&output).contains(&"6/10 RAW READS"));
    let read_marks: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, stroke }
                if stroke.color == GREEN && (points[0].y - 24.0).abs() < 0.1 =>
            {
                Some(points[0].x)
            }
            _ => None,
        })
        .collect();
    let expected = |index: usize| 12.0 + 716.0 * (index as f32 + 0.5) / 10.0;
    assert_eq!(
        read_marks.len(),
        2,
        "six completed reads with two observed indices must paint exactly two read marks"
    );
    for index in [2, 7] {
        assert!(
            read_marks
                .iter()
                .any(|x| (*x - expected(index)).abs() < 0.1)
        );
    }
    assert!(
        !read_marks.iter().any(|x| (*x - expected(0)).abs() < 0.1),
        "the first frame was not observed; aggregate counts cannot manufacture it"
    );
    progress.ingest(
        "STREHL_UI_PROGRESS event=align-phase name=pyramids frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-pyramid index=5 completed=8 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-pyramid index=3 completed=7 frames=10 total=10\n",
    );
    let (_, output) = paint(&context, &progress, 10, 0.1, vec![], &[]);
    assert!(text_values(&output).contains(&"8/10 MULTISCALE"));
    let scale_marks: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, stroke }
                if stroke.color == GREEN && (points[0].y - 38.0).abs() < 0.1 =>
            {
                Some(points[0].x)
            }
            _ => None,
        })
        .collect();
    assert_eq!(scale_marks.len(), 1);
    assert!(
        (scale_marks[0] - expected(5)).abs() < 0.1,
        "only the actually emitted pyramid identity may be marked"
    );
}

#[test]
fn actual_graph_curve_and_contact_axis_have_distinct_pointer_actions() {
    let context = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest(
        "STREHL_UI_PROGRESS event=stage name=alignment total=10000\n\
STREHL_UI_PROGRESS event=align-phase name=pairs frames=10000 total=20000\n\
STREHL_UI_PROGRESS event=align-pair i=100 j=9500 completed=37 accepted=12 frames=10000 total=20000\n\
STREHL_UI_PROGRESS event=align-pair-start i=400 j=7400 started=38 frames=10000 total=20000\n",
    );
    let (_, output) = paint(&context, &progress, 10000, 0.0, vec![], &[]);
    let curve = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Path(path) if path.points.len() == 21 => Some(path.points[10]),
            _ => None,
        })
        .expect("fixture must draw the actually observed connection");
    let _ = paint(
        &context,
        &progress,
        10000,
        0.1,
        vec![egui::Event::PointerMoved(curve), button(curve, true)],
        &[],
    );
    let (response, _) = paint(
        &context,
        &progress,
        10000,
        0.2,
        vec![button(curve, false)],
        &[],
    );
    assert_eq!(
        response,
        Response {
            selected: None,
            compare_pair: Some([100, 9500])
        }
    );
    // The current started edge is visibly cyan, but only completed observed
    // history is a selectable historical comparison.
    let empty = egui::pos2(725.0, 22.0);
    let _ = paint(
        &context,
        &progress,
        10000,
        0.3,
        vec![egui::Event::PointerMoved(empty), button(empty, true)],
        &[],
    );
    let (response, _) = paint(
        &context,
        &progress,
        10000,
        0.4,
        vec![button(empty, false)],
        &[],
    );
    assert_eq!(
        response,
        Response::default(),
        "empty graph space must not invent a comparison or source"
    );
    let at = egui::pos2(12.0 + 716.0 * (2507.5 / 10000.0), 70.0);
    let _ = paint(
        &context,
        &progress,
        10000,
        0.5,
        vec![egui::Event::PointerMoved(at), button(at, true)],
        &[],
    );
    let (response, _) = paint(
        &context,
        &progress,
        10000,
        0.6,
        vec![button(at, false)],
        &[],
    );
    assert_eq!(
        response,
        Response {
            selected: Some(2507),
            compare_pair: None
        },
        "axis selection must retain actual frame precision within a dense stack"
    );
    let at = egui::pos2(12.0 + 716.0 * (7500.5 / 10000.0), 70.0);
    let _ = paint(
        &context,
        &progress,
        10000,
        0.7,
        vec![egui::Event::PointerMoved(at), button(at, true)],
        &[],
    );
    let outside = egui::pos2(739.0, 70.0);
    let (response, _) = paint(
        &context,
        &progress,
        10000,
        0.8,
        vec![egui::Event::PointerMoved(outside)],
        &[],
    );
    assert_eq!(
        response,
        Response::default(),
        "dragging outside the actual axis cannot select a phantom frame"
    );
}

#[test]
fn merge_preserves_observed_frame_identities_and_separates_plan_from_results() {
    let context = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest(
        "bands: 7 Laplacian levels + 1 base\n\
per-band exp: 2 3 4 5 8 8 8 (coarsest -> finest)\n\
base band: plain mean across frames\n\
STREHL_UI_PROGRESS event=stage name=merge total=10\n\
STREHL_UI_PROGRESS event=frame-started index=3 total=10\n\
STREHL_UI_PROGRESS event=frame-finished index=8 processed=6 accepted=4 total=10\n\
STREHL_UI_PROGRESS event=frame-started index=4 total=10\n",
    );
    let (_, output) = paint(&context, &progress, 10, 0.0, vec![], &[]);
    let labels = text_values(&output);
    assert!(labels.contains(&"6/10 PROCESSED / 4 ACCEPTED"));
    assert!(labels.contains(&"BLEND PLAN"));
    assert!(
        !labels.iter().any(|label| label.starts_with('p')),
        "weight powers must not be the primary visual vocabulary"
    );
    let bars: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if rect.fill == RAISED
                    && (rect.rect.top() - 24.0).abs() < 0.1
                    && (rect.rect.height() - 12.0).abs() < 0.1 =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .collect();
    assert_eq!(
        bars.len(),
        8,
        "seven actual detail levels plus the tone base must be shown"
    );
    let stripes = |bar: Rect| {
        output
            .shapes
            .iter()
            .filter(|shape| match &shape.shape {
                egui::Shape::LineSegment { points, stroke } => {
                    stroke.color == MUTED
                        && bar.contains(points[0])
                        && bar.contains(points[1])
                        && (points[0].x - points[1].x).abs() < 0.1
                }
                _ => false,
            })
            .count()
    };
    assert!(
        stripes(bars[0]) > stripes(bars[6]),
        "the actual fine glyph must contain denser line spacing than the coarse glyph"
    );
    let input = output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Text(text) if text.galley.text() == "005" => Some(text.pos),
        _ => None,
    });
    assert_eq!(
        input, None,
        "without a real supplied texture, the input branch must not invent a photograph"
    );
    assert!(
        !labels.iter().any(|label| label.ends_with('%')),
        "planned exponents cannot masquerade as measured averaging"
    );
    let marks: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, stroke }
                if stroke.color == GREEN && (points[0].y - 78.0).abs() < 0.1 =>
            {
                Some(points[0].x)
            }
            _ => None,
        })
        .collect();
    assert_eq!(
        marks.len(),
        1,
        "aggregate processed=6 cannot fill six identities, and accepted=4 cannot identify four admitted frames"
    );
    assert!((marks[0] - (12.0 + 716.0 * 8.5 / 10.0)).abs() < 0.1);
    progress.ingest("averaged: 4.8% 0.0% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0%\n");
    let (_, output) = paint(&context, &progress, 10, 0.1, vec![], &[]);
    let labels = text_values(&output);
    assert!(labels.contains(&"OBSERVED MIX") && labels.contains(&"5%") && labels.contains(&"100%"));
    assert!(!labels.contains(&"BLEND PLAN"));
    assert_eq!(progress.frame_observations.len(), 3);
}

#[test]
fn output_view_uses_real_crop_origin_and_keeps_unknown_coverage_empty() {
    let outer = Rect::from_min_size(egui::pos2(20.0, 40.0), egui::vec2(200.0, 100.0));
    assert_eq!(output_view(outer, None), None);
    assert_eq!(output_view(outer, Some(CoveragePlan::Uncovered)), None);
    assert_eq!(
        output_view(
            outer,
            Some(CoveragePlan::Cropped {
                width: 40,
                height: 30,
                x: 10,
                y: 20,
                grid_width: 100,
                grid_height: 100
            })
        ),
        Some(Rect::from_min_max(
            egui::pos2(40.0, 60.0),
            egui::pos2(120.0, 90.0)
        ))
    );
    assert_eq!(
        output_view(outer, Some(CoveragePlan::Scaled(0.5))),
        Some(Rect::from_center_size(outer.center(), outer.size() * 0.5))
    );
    let context = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=render total=12\n");
    let (_, output) = paint(&context, &progress, 12, 0.0, vec![], &[]);
    assert!(text_values(&output).contains(&"VIEW PENDING"));
    progress.ingest("coverage: CROPPED to the region EVERY frame covers -- 40 x 30 plane px at (10, 20) of 100 x 100\n");
    let (_, output) = paint(&context, &progress, 12, 0.1, vec![], &[]);
    assert!(text_values(&output).contains(&"OUTPUT VIEW"));
    assert_eq!(
        progress.frames_processed, None,
        "render and coverage events cannot invent merge completion"
    );
}

#[test]
fn camera_slices_keep_identity_and_all_phases_fit_the_fixed_height() {
    let context = egui::Context::default();
    let photo = context.load_texture(
        "known-frame",
        egui::ColorImage::new([16, 10], vec![Color32::RED; 160]),
        egui::TextureOptions::LINEAR,
    );
    let stale = context.load_texture(
        "out-of-range-frame",
        egui::ColorImage::new([16, 10], vec![Color32::GREEN; 160]),
        egui::TextureOptions::LINEAR,
    );
    for (time, stage) in ["read", "alignment", "merge", "render"]
        .into_iter()
        .enumerate()
    {
        let mut progress = PipelineProgress::default();
        progress.ingest(&format!(
            "STREHL_UI_PROGRESS event=stage name={stage} total=12\n"
        ));
        let (response, output) = paint(
            &context,
            &progress,
            12,
            time as f64,
            vec![],
            &[(3, &photo), (100, &stale)],
        );
        assert_eq!(response, Response::default());
        assert!(output.shapes.iter().any(
            |shape| matches!(&shape.shape,egui::Shape::Mesh(mesh) if mesh.texture_id==photo.id())
        ));
        assert!(!output.shapes.iter().any(|shape|matches!(&shape.shape,egui::Shape::Mesh(mesh) if mesh.texture_id==stale.id())),"wrong source identity must never be substituted into a missing camera slice");
        for shape in &output.shapes {
            if let egui::Shape::Text(text) = &shape.shape {
                assert!(
                    shape
                        .clip_rect
                        .expand(1.0)
                        .contains_rect(text.visual_bounding_rect()),
                    "{stage} text {} must fit the actual94px ribbon",
                    text.galley.text()
                );
            }
        }
    }
    let (response, _) = paint(&context, &PipelineProgress::default(), 0, 5.0, vec![], &[]);
    assert_eq!(response, Response::default());
}

#[test]
fn a_dense_stack_contact_card_selects_its_real_identity_instead_of_the_covered_axis_cell() {
    let context = egui::Context::default();
    let photo = context.load_texture(
        "dense-contact-120",
        egui::ColorImage::new([30, 20], vec![Color32::RED; 600]),
        egui::TextureOptions::LINEAR,
    );
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=259\n");
    let (_, output) = paint(&context, &progress, 259, 0.0, vec![], &[(120, &photo)]);
    let card = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == photo.id() => {
                let rect = Rect::from_points(
                    &mesh
                        .vertices
                        .iter()
                        .map(|vertex| vertex.pos)
                        .collect::<Vec<_>>(),
                );
                (rect.width() > 20.0 && rect.height() > 10.0).then_some(rect)
            }
            _ => None,
        })
        .expect(
            "a known global anchor must be a recognizable photograph rather than only a3px sliver",
        );
    let at = egui::pos2(card.left() + 3.0, card.center().y);
    let underlying = frame_at(
        Rect::from_min_max(egui::pos2(12.0, 60.0), egui::pos2(728.0, 81.0)),
        259,
        at.x,
    );
    assert_ne!(
        underlying, 120,
        "the adversarial click must cover a neighboring capture-order coordinate"
    );
    let _ = paint(
        &context,
        &progress,
        259,
        0.1,
        vec![egui::Event::PointerMoved(at), button(at, true)],
        &[(120, &photo)],
    );
    let (response, _) = paint(
        &context,
        &progress,
        259,
        0.2,
        vec![button(at, false)],
        &[(120, &photo)],
    );
    assert_eq!(
        response,
        Response {
            selected: Some(120),
            compare_pair: None
        }
    );
}

#[test]
fn visible_window_bracket_uses_the_actual_capture_range_and_rejects_invalid_ranges() {
    let context = egui::Context::default();
    let progress = PipelineProgress::default();
    let draw = |time, range| {
        context.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(740.0, HEIGHT))),
                time: Some(time),
                ..Default::default()
            },
            |context| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(context, |ui| {
                        let _ = show(ui, &progress, 100, 0, None, &[], range);
                    });
            },
        )
    };
    let output = draw(0.0, Some([30, 39]));
    let bracket = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Path(path) if path.points.len() == 4 => Some(&path.points),
            _ => None,
        })
        .expect("the real local filmstrip range must be projected onto the global stack axis");
    assert!((bracket[0].x - (12.0 + 716.0 * 0.30)).abs() < 0.1);
    assert!((bracket[3].x - (12.0 + 716.0 * 0.40)).abs() < 0.1);
    let output = draw(0.1, Some([39, 30]));
    assert!(
        !output
            .shapes
            .iter()
            .any(|shape| matches!(&shape.shape,egui::Shape::Path(path) if path.points.len()==4)),
        "a reversed or stale viewport range must not draw a false stack span"
    );
}

#[test]
fn merge_photo_input_is_above_contacts_and_connected_to_its_true_capture_position() {
    let context = egui::Context::default();
    let photo = context.load_texture(
        "merge-current-4",
        egui::ColorImage::new([30, 20], vec![Color32::RED; 600]),
        egui::TextureOptions::LINEAR,
    );
    let mut progress = PipelineProgress::default();
    progress.ingest("bands: 7 Laplacian levels + 1 base\nper-band exp: 2 3 4 5 8 8 8 (coarsest -> finest)\nSTREHL_UI_PROGRESS event=stage name=merge total=10\nSTREHL_UI_PROGRESS event=frame-started index=4 total=10\n");
    let (_, output) = paint(&context, &progress, 10, 0.0, vec![], &[(4, &photo)]);
    let input=output.shapes.iter().find_map(|shape|match &shape.shape {
        egui::Shape::Mesh(mesh) if mesh.texture_id==photo.id()=>{
            let bounds=Rect::from_points(&mesh.vertices.iter().map(|vertex|vertex.pos).collect::<Vec<_>>());
            (bounds.width()>40.0&&bounds.bottom()<60.0).then_some(bounds)
        }
        _=>None,
    }).expect("the real current capture must be recognizable in the reserved input area above the contact strip");
    assert!(input.right() < 120.0);
    assert!(
        output
            .shapes
            .iter()
            .any(|shape| matches!(&shape.shape,egui::Shape::Path(path)
        if path.points.len()==4&&(path.points[0].x-input.center().x).abs()<0.1
        &&(path.points[3].x-(12.0+716.0*4.5/10.0)).abs()<0.1
        &&(path.points[3].y-81.0).abs()<0.1)),
        "the enlarged photograph needs an explicit leader to its actual capture-order coordinate"
    );
    let at = input.center();
    let _ = paint(
        &context,
        &progress,
        10,
        0.1,
        vec![egui::Event::PointerMoved(at), button(at, true)],
        &[(4, &photo)],
    );
    let (response, _) = paint(
        &context,
        &progress,
        10,
        0.2,
        vec![button(at, false)],
        &[(4, &photo)],
    );
    assert_eq!(
        response,
        Response {
            selected: Some(4),
            compare_pair: None
        }
    );
    for shape in &output.shapes {
        if let egui::Shape::Text(text) = &shape.shape {
            assert!(
                shape
                    .clip_rect
                    .expand(1.0)
                    .contains_rect(text.visual_bounding_rect()),
                "real-input merge labels must stay inside94px: {}",
                text.galley.text()
            );
        }
    }
}
