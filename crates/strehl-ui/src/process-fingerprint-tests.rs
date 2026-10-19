use super::*;
use crate::pipeline::{
    DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface, PipelineProgress,
};
use std::sync::Arc;

#[test]
fn pin_rows_render_consistent_photo_or_grid_units() {
    for (writer, unit, first) in [
        (
            Some("stack.tiff (262 x 198, 16-bit RGB, sRGB, Malvar-He-Cutler demosaic)"),
            "photo px",
            "2",
        ),
        (
            Some("stack.tiff (131 x 99, 16-bit RGB, sRGB, binned from one 2x2 quad per pixel)"),
            "photo px",
            "1",
        ),
        (None, "grid px", "1"),
    ] {
        let ctx = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.bands = Some(7);
        progress.output_geometry = writer.map(|value| OutputGeometry::parse(value).unwrap());
        let (_, output) = draw(
            &ctx,
            egui::vec2(680.0, 240.0),
            input(&progress, 2),
            &progress.admission_archive,
            egui::pos2(0.5, 0.5),
            0.0,
            vec![],
        );
        let texts: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) => Some(text.galley.text()),
                _ => None,
            })
            .collect();
        assert!(texts.contains(&unit));
        assert!(texts.contains(&first));
        assert!(texts.contains(&"broad tone"));
        assert_eq!(row_name(0, false, progress.output_geometry), first);
    }
}

fn packet(
    sequence: u64,
    frame: usize,
    level: usize,
    samples: [usize; 2],
    pixels: &[u8],
) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: samples[0],
        height: samples[1],
        min: 0.0,
        max: 1.0,
        pixels: Arc::from(pixels),
        folded: 1,
    }
}
fn input(progress: &PipelineProgress, count: usize) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: count,
        selected: 0,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}
fn draw(
    ctx: &egui::Context,
    size: egui::Vec2,
    input: Input<'_>,
    archive: &AdmissionArchive,
    pin: Pos2,
    time: f64,
    events: Vec<egui::Event>,
) -> (FingerprintResponse, egui::FullOutput) {
    let mut response = FingerprintResponse::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, size)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = show(ui, ui.max_rect(), &input, archive, pin, 3);
                });
        },
    );
    (response, output)
}
fn marks(output: &egui::FullOutput, area: Rect) -> Vec<(Rect, bool)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if area.contains_rect(rect.rect)
                    && (rect.fill == GREEN || rect.stroke.color == GREEN.gamma_multiply(0.5)) =>
            {
                Some((rect.rect, rect.fill == GREEN))
            }
            _ => None,
        })
        .collect()
}
fn archive() -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 1, 0, [2, 1], &[0, 255]), [600, 400]);
    archive.ingest(&packet(2, 3, 0, [2, 1], &[255, 0]), [600, 400]);
    archive.ingest(&packet(3, 5, 3, [1, 2], &[0, 255]), [600, 400]);
    archive
}

#[test]
fn actual_pin_changes_admission_using_each_scales_real_grid_and_missing_stays_blank() {
    let ctx = egui::Context::default();
    let size = egui::vec2(400.0, 110.0);
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let archive = archive();
    assert_eq!(archive.len(), 3);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8, 6).unwrap();
    let (_, first) = draw(
        &ctx,
        size,
        input(&progress, 6),
        &archive,
        egui::pos2(0.75, 0.25),
        0.0,
        vec![],
    );
    assert_eq!(marks(&first, layout.cell(0, 1)).len(), 1);
    assert!(marks(&first, layout.cell(0, 1))[0].1);
    assert!(!marks(&first, layout.cell(0, 3))[0].1);
    assert!(
        !marks(&first, layout.cell(3, 5))[0].1,
        "the tall1×2 map uses its own y coordinate"
    );
    for frame in [0, 2, 4, 5] {
        assert!(
            marks(&first, layout.cell(0, frame)).is_empty(),
            "unknown capture{frame} cannot become observedzero"
        );
    }
    let (_, moved) = draw(
        &ctx,
        size,
        input(&progress, 6),
        &archive,
        egui::pos2(0.25, 0.75),
        1.0,
        vec![],
    );
    assert!(!marks(&moved, layout.cell(0, 1))[0].1);
    assert!(marks(&moved, layout.cell(0, 3))[0].1);
    assert!(marks(&moved, layout.cell(3, 5))[0].1);
    assert_eq!(
        marks(&first, layout.cell(0, 1))[0].0,
        marks(&moved, layout.cell(0, 1))[0].0,
        "changing the pin changes evidence, never capture positions"
    );
    let (_, invalid) = draw(
        &ctx,
        size,
        input(&progress, 6),
        &archive,
        egui::pos2(f32::NAN, 0.5),
        2.0,
        vec![],
    );
    assert!(
        marks(&invalid, layout.grid).is_empty(),
        "invalid coordinates cannot manufacture samples"
    );
    progress.mark_complete();
    let (_, complete) = draw(
        &ctx,
        size,
        input(&progress, 6),
        &archive,
        egui::pos2(0.75, 0.25),
        3.0,
        vec![],
    );
    assert_eq!(marks(&complete, layout.grid), marks(&first, layout.grid));
    let empty = AdmissionArchive::default();
    let (_, cleared) = draw(
        &ctx,
        size,
        input(&progress, 6),
        &empty,
        egui::pos2(0.75, 0.25),
        4.0,
        vec![],
    );
    assert!(marks(&cleared, layout.grid).is_empty());
}

fn click(
    ctx: &egui::Context,
    size: egui::Vec2,
    progress: &PipelineProgress,
    count: usize,
    archive: &AdmissionArchive,
    point: Pos2,
    time: f64,
) -> FingerprintResponse {
    let _ = draw(
        ctx,
        size,
        input(progress, count),
        archive,
        egui::pos2(0.75, 0.25),
        time,
        vec![
            egui::Event::PointerMoved(point),
            egui::Event::PointerButton {
                pos: point,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    draw(
        ctx,
        size,
        input(progress, count),
        archive,
        egui::pos2(0.75, 0.25),
        time + 0.05,
        vec![egui::Event::PointerButton {
            pos: point,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: egui::Modifiers::NONE,
        }],
    )
    .0
}

#[test]
fn pointer_selects_true_and_zero_exact_captures_but_unknown_and_grouped_marks_only_select_detail() {
    let ctx = egui::Context::default();
    let size = egui::vec2(400.0, 110.0);
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let archive = archive();
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8, 6).unwrap();
    let _ = draw(
        &ctx,
        size,
        input(&progress, 6),
        &archive,
        egui::pos2(0.75, 0.25),
        0.0,
        vec![],
    );
    for (index, frame) in [1, 3, 2].into_iter().enumerate() {
        let result = click(
            &ctx,
            size,
            &progress,
            6,
            &archive,
            layout.cell(0, frame).center(),
            1.0 + index as f64,
        );
        assert_eq!(
            result.clicked,
            Some(FingerprintPick {
                frame: if frame == 2 { None } else { Some(frame) },
                level: 0
            })
        );
    }
    let grouped = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8, 521).unwrap();
    assert!(grouped.range(0).len() > 1);
    let result = click(
        &ctx,
        size,
        &progress,
        521,
        &archive,
        grouped.cell(0, 0).center(),
        4.0,
    );
    assert_eq!(
        result.clicked,
        Some(FingerprintPick {
            frame: None,
            level: 0
        }),
        "even a group containing real masks cannot impersonate one source capture"
    );
}

#[test]
fn grouped_columns_report_admitted_over_observed_and_hatch_unknown_members() {
    let ctx = egui::Context::default();
    let size = egui::vec2(400.0, 110.0);
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 0, 0, [1, 1], &[0]), [600, 400]);
    archive.ingest(&packet(2, 2, 0, [1, 1], &[255]), [600, 400]);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8, 521).unwrap();
    let row = cells(layout, &archive, egui::pos2(0.5, 0.5));
    assert_eq!(layout.range(0), 0..5);
    assert_eq!((row[0][0].admitted, row[0][0].observed), (1, 2));
    let detail = description(layout, row[0][0], 0, 0, false, None);
    assert!(detail.contains("Captures 1–5 · grouped at this zoom"));
    assert!(detail.contains("1 admitted / 2 observed · 5 captures"));
    let (_, output) = draw(
        &ctx,
        size,
        input(&progress, 521),
        &archive,
        egui::pos2(0.5, 0.5),
        0.0,
        vec![],
    );
    let area = layout.cell(0, 0);
    let colored = output.shapes.iter().filter(|shape| matches!(&shape.shape, egui::Shape::Rect(rect) if area.contains_rect(rect.rect) && rect.fill == GREEN.gamma_multiply(0.65))).count();
    assert_eq!(
        colored, 1,
        "visible intensity uses half the observed captures, never1/5 of all captures"
    );
    let hatch = output.shapes.iter().filter(|shape| matches!(&shape.shape, egui::Shape::LineSegment { points, stroke } if stroke.color == MUTED && area.contains(points[0]) && area.contains(points[1]) && points[0].x != points[1].x && points[0].y != points[1].y)).count();
    assert_eq!(hatch, 1);
    assert!(row[0].iter().skip(1).all(|cell| cell.observed == 0));
}

#[test]
fn compact_headers_all_eight_grid_labels_and_legends_have_visible_nonoverlapping_bounds() {
    for (size, count) in [
        (egui::vec2(300.0, 110.0), 65536),
        (egui::vec2(350.0, 110.0), 521),
        (egui::vec2(400.0, 110.0), 6),
        (egui::vec2(500.0, 110.0), 6),
        (egui::vec2(400.0, 72.0), 6),
    ] {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let mut progress = PipelineProgress::default();
        progress.bands = Some(7);
        let archive = archive();
        let (_, output) = draw(
            &ctx,
            size,
            input(&progress, count),
            &archive,
            egui::pos2(0.5, 0.5),
            0.0,
            vec![],
        );
        let texts = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) => Some((
                    text.galley.text(),
                    Rect::from_min_size(text.pos, text.galley.size()),
                )),
                _ => None,
            })
            .collect::<Vec<_>>();
        if size.y == 110.0 {
            for name in [
                "grid px",
                "1",
                "2",
                "4",
                "8",
                "16",
                "32",
                "64",
                "broad tone",
            ] {
                assert!(
                    texts.iter().any(|(text, _)| *text == name),
                    "all8 real detail identities must be legible"
                );
            }
        }
        let outer = Rect::from_min_size(Pos2::ZERO, size);
        for (index, (_, bounds)) in texts.iter().enumerate() {
            assert!(outer.contains_rect(*bounds));
            assert!(
                texts[index + 1..]
                    .iter()
                    .all(|(_, other)| !bounds.intersects(*other)),
                "text collision at{size:?}: {bounds:?}"
            );
        }
    }
    let rect = Rect::from_min_size(Pos2::ZERO, egui::vec2(400.0, 110.0));
    let layout = Layout::new(rect, 64, 65536).unwrap();
    assert!(rect.contains_rect(layout.row(63)));
    assert!(layout.columns <= 116);
    assert!(Layout::new(rect, 8, 0).is_none());
}

#[test]
fn maximum_axis_and_64_rows_keep_only_retained_observations_and_bounded_screen_columns() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 0, 0, [1, 1], &[0]), [600, 400]);
    archive.ingest(&packet(2, 65535, 7, [1, 1], &[255]), [600, 400]);
    archive.ingest(&packet(3, 65535, 63, [1, 1], &[255]), [600, 400]);
    let layout = Layout::new(
        Rect::from_min_size(Pos2::ZERO, egui::vec2(400.0, 110.0)),
        64,
        65536,
    )
    .unwrap();
    let sampled = cells(layout, &archive, egui::pos2(0.5, 0.5));
    assert_eq!(sampled.len(), 64);
    assert!(sampled.iter().all(|row| row.len() == 116));
    assert_eq!(
        sampled
            .iter()
            .flatten()
            .map(|cell| cell.observed)
            .sum::<usize>(),
        2
    );
    assert_eq!(sampled[0][0].observed, 1);
    assert_eq!(sampled[0][0].admitted, 0);
    assert_eq!(sampled[7][115].observed, 1);
    assert_eq!(sampled[7][115].admitted, 1);
    assert!(
        archive.cells(63, 65535).is_some(),
        "invalid spatial geometry still retains the actual packet bits"
    );
    assert_eq!(
        sampled[63][115].observed, 0,
        "an impossible 2^63-pixel lattice cannot claim a sampled location at the pin"
    );
    assert_eq!(layout.range(115).end, 65536);
    assert_eq!(pick(layout, &sampled, 63, 115).frame, None);
}
