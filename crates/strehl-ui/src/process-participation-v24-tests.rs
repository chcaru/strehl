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

#[test]
fn every_current_capture_replaces_one_fixed_slot_without_holes_or_overlap() {
    // This includes a rounded-anchor counterexample: 12 captures /4 slots,
    // capture2 is nearer anchor0 but belongs in visual slot1.
    for count in [12, 23, 130, 299] {
        for width in [580.0, 716.0, 1040.0, 1800.0] {
            let anchors = anchors(count, width);
            let row = CaptureParticipation {
                anchors: anchors.clone(),
                ..Default::default()
            };
            let layout = Layout::new(
                Rect::from_min_size(Pos2::ZERO, egui::vec2(width, HEIGHT)),
                count,
                anchors.len(),
            )
            .unwrap();
            let original: Vec<_> = anchors.iter().map(|&frame| layout.contact(frame)).collect();
            for active in 0..count {
                let contacts = row.contact_frames(Some(active));
                assert!(contacts.contains(&active));
                assert_eq!(contacts.len(), anchors.len());
                let actual: Vec<_> = contacts
                    .iter()
                    .map(|&frame| layout.contact(frame))
                    .collect();
                assert_eq!(
                    actual, original,
                    "count={count}, width={width}, active={active}"
                );
                assert!(
                    actual
                        .windows(2)
                        .all(|pair| pair[0].right() < pair[1].left())
                );
                assert_eq!(
                    layout.index_at(layout.contact(active).center(), &contacts),
                    active
                );
            }
        }
    }
}

#[test]
fn hover_shows_the_actual_between_anchor_capture_and_click_keeps_its_painted_identity() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let photos: Vec<_> = (0..130)
        .map(|index| SourcePhoto {
            epoch: 1,
            index,
            aperture: [60, 40],
            texture: ctx.load_texture(
                format!("current-capture-{index}"),
                egui::ColorImage::filled([60, 40], Color32::from_rgb(index as u8, 80, 120)),
                egui::TextureOptions::LINEAR,
            ),
        })
        .collect();
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, data(&progress, &photos), 0.0, vec![]);
    let (_, initial) = paint(&mut row, &ctx, data(&progress, &photos), 0.1, vec![]);
    let anchors = row.anchors.clone();
    let current = 35;
    assert!(!anchors.contains(&current));
    assert!(image(&initial, photos[current].texture.id()).is_none());
    let layout = Layout::new(bounds(), 130, anchors.len()).unwrap();
    let at = egui::pos2(layout.x(current), layout.contact(0).center().y);
    let (hover, shown) = paint(
        &mut row,
        &ctx,
        data(&progress, &photos),
        0.2,
        vec![egui::Event::PointerMoved(at)],
    );
    assert_eq!(hover.hover_source, Some(current));
    assert!(hover.open_source.is_none());
    let card = image(&shown, photos[current].texture.id()).expect("actual hovered source pixels");
    assert_eq!(card, layout.contact(current));
    assert!(row.indices().contains(&current));
    let shown_images: Vec<_> = photos
        .iter()
        .filter_map(|p| image(&shown, p.texture.id()))
        .collect();
    assert_eq!(
        shown_images.len(),
        anchors.len(),
        "one replacement, no duplicate gallery"
    );
    let (pressed, _) = paint(
        &mut row,
        &ctx,
        data(&progress, &photos),
        0.4,
        vec![
            egui::Event::PointerMoved(card.center()),
            button(card.center(), true),
        ],
    );
    assert_eq!(pressed.open_source, Some(current));
    let (released, _) = paint(
        &mut row,
        &ctx,
        data(&progress, &photos),
        0.5,
        vec![button(card.center(), false)],
    );
    assert_eq!(released.open_source, Some(current));
    let (_, left) = paint(
        &mut row,
        &ctx,
        data(&progress, &photos),
        1.0,
        vec![egui::Event::PointerMoved(egui::pos2(1.0, 1.0))],
    );
    assert_eq!(
        image(&left, photos[current].texture.id()),
        Some(card),
        "leaving cannot lose the current source thumbnail"
    );
}

#[test]
fn band_signature_uses_retained_counts_rejects_foreign_domains_and_selects_real_band() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    progress.analysis_size = Some([8, 4]);
    for (level, pixels, extent) in [
        (0, vec![255, 0, 255, 0, 255, 0, 255, 0], [8, 4]),
        (1, vec![255; 8], [8, 4]),
        (2, vec![255; 8], [16, 8]),
    ] {
        progress.admission_archive.ingest(
            &crate::pipeline::DiagnosticSurface {
                sequence: level as u64 + 1,
                frame: 0,
                level,
                kind: crate::pipeline::DiagnosticKind::GateSupport,
                scope: crate::pipeline::DiagnosticScope::Frame,
                scale: crate::pipeline::DiagnosticScale::Linear,
                width: 4,
                height: 2,
                min: 0.0,
                max: 1.0,
                folded: 1,
                pixels: pixels.into(),
            },
            extent,
        );
    }
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, data(&progress, &[]), 0.0, vec![]);
    paint(&mut row, &ctx, data(&progress, &[]), 0.1, vec![]);
    assert_eq!(
        row.band_evidence[&(0, 0)].1,
        Area {
            admitted: 4,
            observed: 8
        }
    );
    assert_eq!(
        row.band_evidence[&(0, 1)].1,
        Area {
            admitted: 8,
            observed: 8
        }
    );
    assert!(
        !row.band_evidence.contains_key(&(0, 2)),
        "mismatched current analysis is unknown"
    );
    assert!(
        !row.band_evidence.contains_key(&(1, 0)),
        "unrecorded source is unknown"
    );
    let layout = Layout::new(bounds(), 130, row.anchors.len()).unwrap();
    let card = layout.contact(0);
    // Three14px signature cells centered under the card; middle is level1.
    let at = egui::pos2(card.center().x - 1.0, card.bottom() + 16.5);
    paint(
        &mut row,
        &ctx,
        data(&progress, &[]),
        0.3,
        vec![egui::Event::PointerMoved(at), button(at, true)],
    );
    let (selected, _) = paint(
        &mut row,
        &ctx,
        data(&progress, &[]),
        0.4,
        vec![button(at, false)],
    );
    assert_eq!(selected.level, Some(1));
    assert_eq!(selected.open_source, Some(0));
    assert_eq!(selected.frame, Some(0));
}
