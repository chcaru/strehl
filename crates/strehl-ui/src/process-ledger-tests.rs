use super::*;
use crate::{pipeline::PipelineProgress, workbench::SourcePhoto};

#[test]
fn contribution_and_fallback_rows_render_consistent_photo_or_grid_units() {
    for (writer, unit, first, fallback) in [
        (
            Some("stack.tiff (262 x 198, 16-bit RGB, sRGB, Malvar-He-Cutler demosaic)"),
            "photo px",
            "2",
            "16",
        ),
        (
            Some("stack.tiff (131 x 99, 16-bit RGB, sRGB, binned from one 2x2 quad per pixel)"),
            "photo px",
            "1",
            "8",
        ),
        (None, "grid px", "1", "8"),
    ] {
        let ctx = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.bands = Some(7);
        progress.output_geometry = writer.map(|value| OutputGeometry::parse(value).unwrap());
        let (_, output) = draw(
            &ctx,
            &mut ProcessLedger::default(),
            egui::vec2(340.0, 300.0),
            input(&progress, &[], 2),
            0.0,
            vec![],
        );
        let texts: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) => Some((text.galley.text(), text.pos.y)),
                _ => None,
            })
            .collect();
        assert!(texts.iter().any(|&(text, _)| text == unit));
        assert!(texts.iter().any(|&(text, _)| text == first));
        assert!(
            texts
                .iter()
                .any(|&(text, y)| text == fallback && y >= 270.0),
            "fallback must share the row units: {texts:?}"
        );
        assert!(texts.iter().any(|&(text, _)| text == "broad tone"));
    }
}

fn input<'a>(progress: &'a PipelineProgress, photos: &'a [SourcePhoto], count: usize) -> Input<'a> {
    Input {
        epoch: 1,
        progress,
        frame_count: count,
        selected: 0,
        inspected_pair: None,
        photos,
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}
fn draw(
    ctx: &egui::Context,
    ledger: &mut ProcessLedger,
    size: egui::Vec2,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (LedgerResponse, egui::FullOutput) {
    let mut response = LedgerResponse::default();
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
                    response = ledger.show(ui, ui.max_rect(), &input, 3);
                });
        },
    );
    (response, output)
}
#[allow(clippy::too_many_arguments)] // Keep each recorded event's protocol fields explicit.
fn mask(
    progress: &mut PipelineProgress,
    sequence: usize,
    kind: &str,
    frame: usize,
    folded: usize,
    level: usize,
    total: usize,
    data: &str,
) {
    let scope = if kind == "gate-support" {
        "frame"
    } else {
        "stack"
    };
    progress.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame={frame} level={level} kind={kind} scope={scope} scale=linear width=2 height=1 min=0 max=1 folded={folded} total={total} sampling=nearest data={data}\n"));
}
fn sparse() -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let mut sequence = 0;
    for level in 0..8 {
        for (prefix, frame) in [1, 2, 4, 5].into_iter().enumerate() {
            sequence += 1;
            mask(
                &mut progress,
                sequence,
                "gate-support",
                frame,
                1,
                level,
                6,
                if frame == 1 { "0000" } else { "ffff" },
            );
            sequence += 1;
            mask(
                &mut progress,
                sequence,
                "averaging",
                frame,
                prefix + 1,
                level,
                6,
                "00ff",
            );
        }
    }
    progress.ingest("STREHL_UI_PROGRESS event=merge-step index=0 name=gather state=skipped level=none total=6\n");
    progress.ingest("STREHL_UI_PROGRESS event=merge-step index=3 name=gather state=skipped level=none total=6\n");
    progress
}
fn marks(output: &egui::FullOutput, region: Rect) -> Vec<(Rect, Color32)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(shape)
                if region.contains_rect(shape.rect)
                    && shape.fill != BG
                    && shape.fill != Color32::TRANSPARENT =>
            {
                Some((shape.rect, shape.fill))
            }
            _ => None,
        })
        .collect()
}

#[test]
fn refused_captures_leave_true_gaps_and_fallback_keeps_its_different_prefix_axis() {
    let ctx = egui::Context::default();
    let mut ledger = ProcessLedger::default();
    let mut progress = sparse();
    assert_eq!(
        progress.merge_frame_observations[&0].gather,
        Some(WorkState::Skipped)
    );
    assert_eq!(
        progress.merge_frame_observations[&3].gather,
        Some(WorkState::Skipped)
    );
    let size = egui::vec2(200.0, 180.0);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8).unwrap();
    let (_, before) = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 6),
        0.0,
        vec![],
    );
    let contributions = marks(&before, layout.row(3));
    assert_eq!(contributions.len(), 4);
    for ((rect, _), frame) in contributions.iter().zip([1, 2, 4, 5]) {
        assert!((rect.center().x - frame_x(layout.grid, frame, 6)).abs() < 0.01);
    }
    assert_eq!(
        contributions[0].1,
        GREEN.gamma_multiply(0.22),
        "an observed zero mask is visible, unlike an absent mask"
    );
    assert_eq!(contributions[1].1, GREEN);
    let fallbacks = marks(&before, layout.fallback);
    assert_eq!(fallbacks.len(), 4);
    for ((rect, _), prefix) in fallbacks.iter().zip(0..4) {
        assert!(
            (rect.center().x - frame_x(layout.fallback, prefix, 6)).abs() < 0.01,
            "accepted prefix two must not be drawn at source capture three"
        );
    }
    progress.mark_complete();
    let (_, complete) = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 6),
        1.0,
        vec![],
    );
    assert_eq!(marks(&complete, layout.row(3)), contributions);
    assert_eq!(marks(&complete, layout.fallback), fallbacks);
    assert!(complete.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text() == "Sampled · blank unobserved")));
}

fn click(
    ctx: &egui::Context,
    ledger: &mut ProcessLedger,
    progress: &PipelineProgress,
    count: usize,
    size: egui::Vec2,
    point: Pos2,
    time: f64,
) -> LedgerResponse {
    let _ = draw(
        ctx,
        ledger,
        size,
        input(progress, &[], count),
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
        ledger,
        size,
        input(progress, &[], count),
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
fn only_an_exact_observed_capture_is_returned_and_grouped_or_missing_cells_select_level_only() {
    let ctx = egui::Context::default();
    let mut ledger = ProcessLedger::default();
    let progress = sparse();
    let size = egui::vec2(200.0, 180.0);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8).unwrap();
    let _ = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 6),
        0.0,
        vec![],
    );
    for (frame, expected, time) in [(2, Some(2), 0.1), (3, None, 0.3), (1, Some(1), 0.5)] {
        let point = egui::pos2(frame_x(layout.grid, frame, 6), layout.row(3).center().y);
        assert_eq!(
            click(&ctx, &mut ledger, &progress, 6, size, point, time).clicked,
            Some(LedgerPick {
                frame: expected,
                level: 3
            })
        );
    }
    let mut grouped = PipelineProgress::default();
    grouped.bands = Some(7);
    mask(&mut grouped, 1, "gate-support", 10, 1, 3, 4096, "ffff");
    let item = evidence(&grouped.sampled_mask_history[0], 10).unwrap();
    assert_eq!(item.range, 8..12);
    assert_eq!(item.observed, 1);
    assert!(describe(Some(&item), "captures").contains("Grouped captures 9–12 · 1/4 observed"));
    let point = egui::pos2(frame_x(layout.grid, 10, 4096), layout.row(3).center().y);
    assert_eq!(
        click(&ctx, &mut ledger, &grouped, 4096, size, point, 1.0).clicked,
        Some(LedgerPick {
            frame: None,
            level: 3
        })
    );
    let fallback_point = layout.fallback.center();
    assert_eq!(
        click(&ctx, &mut ledger, &progress, 6, size, fallback_point, 1.3).clicked,
        None,
        "a prefix can never select a source identity"
    );
}

#[test]
fn actual_started_work_has_a_frontier_but_time_and_completion_cannot_invent_one() {
    let ctx = egui::Context::default();
    let mut ledger = ProcessLedger::default();
    let mut progress = sparse();
    let size = egui::vec2(200.0, 180.0);
    let frontier = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Rect(shape) if shape.stroke.color == ACCENT => Some(shape.rect),
                _ => None,
            })
            .collect::<Vec<_>>()
    };
    let (_, empty) = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 6),
        0.0,
        vec![],
    );
    assert!(frontier(&empty).is_empty());
    progress.ingest(
        "STREHL_UI_PROGRESS event=merge-step index=4 name=fold state=started level=3 total=6\n",
    );
    assert_eq!(active(&input(&progress, &[], 6), 8), Some((4, Some(3))));
    let (_, live) = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 6),
        1.0,
        vec![],
    );
    let (_, later) = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 6),
        40.0,
        vec![],
    );
    assert_eq!(frontier(&live).len(), 1);
    assert_eq!(frontier(&live), frontier(&later));
    progress.mark_complete();
    let (_, completed) = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 6),
        41.0,
        vec![],
    );
    assert!(frontier(&completed).is_empty());
}

#[test]
fn screen_grouping_discloses_its_actual_mixed_evidence_without_borrowing_one_capture_value() {
    let ctx = egui::Context::default();
    let mut ledger = ProcessLedger::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    // First displayed column covers four captures: observed zero, missing,
    // observed full, missing. The display is50% of two observations, not25%
    // over four frames and not an assertion that the second capture contributed.
    mask(&mut progress, 1, "gate-support", 0, 1, 0, 521, "0000");
    mask(&mut progress, 2, "gate-support", 2, 1, 0, 521, "ffff");
    let size = egui::vec2(201.0, 180.0);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8).unwrap();
    let history = &progress.sampled_mask_history[0];
    let shown = displayed_evidence(history, layout.grid, 1).unwrap();
    assert_eq!(shown.range, 0..4);
    assert_eq!((shown.observed, shown.on, shown.samples), (2, 2, 4));
    assert_eq!(
        evidence(history, 1).unwrap().samples,
        0,
        "the exact hovered capture is genuinely missing"
    );
    let description = describe(Some(&shown), "captures");
    assert!(description.contains("Grouped captures 1–4 · 2/4 observed"));
    assert!(description.contains("50% of observed nearest samples"));
    let (_, output) = draw(
        &ctx,
        &mut ledger,
        size,
        input(&progress, &[], 521),
        0.0,
        vec![],
    );
    let painted = marks(&output, layout.row(0));
    assert_eq!(painted.len(), 1);
    assert_eq!(painted[0].1, GREEN.gamma_multiply(0.61));
    let diagonals = output.shapes.iter().filter(|shape| matches!(&shape.shape, egui::Shape::LineSegment { points, stroke } if stroke.color == MUTED && layout.row(0).contains(points[0]) && layout.row(0).contains(points[1]) && points[0].x != points[1].x && points[0].y != points[1].y)).count();
    assert_eq!(
        diagonals, 1,
        "partly observed groups need a visible missing-evidence mark"
    );
    let point = egui::pos2(frame_x(layout.grid, 1, 521), layout.row(0).center().y);
    assert_eq!(
        click(&ctx, &mut ledger, &progress, 521, size, point, 1.0).clicked,
        Some(LedgerPick {
            frame: None,
            level: 0
        })
    );
}

#[test]
fn real_photo_contacts_and_all_rows_remain_inside_compact_bounds_at_fixed_capture_positions() {
    for (size, count) in [
        (egui::vec2(200.0, 180.0), 2),
        (egui::vec2(200.0, 180.0), 12),
        (egui::vec2(280.0, 208.0), 259),
    ] {
        let ctx = egui::Context::default();
        let mut ledger = ProcessLedger::default();
        let mut progress = PipelineProgress::default();
        progress.bands = Some(7);
        let indices = contact_indices(count);
        let photos = indices
            .iter()
            .map(|&index| SourcePhoto {
                epoch: 1,
                index,
                aperture: [300, 200],
                texture: ctx.load_texture(
                    format!("ledger-photo-{index}"),
                    egui::ColorImage::filled([6, 4], GREEN),
                    egui::TextureOptions::LINEAR,
                ),
            })
            .collect::<Vec<_>>();
        let (_, initial) = draw(
            &ctx,
            &mut ledger,
            size,
            input(&progress, &photos, count),
            0.0,
            vec![],
        );
        let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8).unwrap();
        assert_eq!(visible_contact_indices(layout.rect, count), indices);
        let images = |output: &egui::FullOutput| {
            output
                .shapes
                .iter()
                .filter_map(|shape| match &shape.shape {
                    egui::Shape::Mesh(mesh)
                        if photos
                            .iter()
                            .any(|photo| photo.texture.id() == mesh.texture_id) =>
                    {
                        Some((
                            mesh.texture_id,
                            Rect::from_points(
                                &mesh
                                    .vertices
                                    .iter()
                                    .map(|vertex| vertex.pos)
                                    .collect::<Vec<_>>(),
                            ),
                        ))
                    }
                    _ => None,
                })
                .collect::<Vec<_>>()
        };
        let shown = images(&initial);
        assert_eq!(shown.len(), indices.len());
        for (slot, (_, bounds)) in shown.iter().enumerate() {
            assert!(layout.photo(slot, indices.len()).contains_rect(*bounds));
            assert!(bounds.bottom() < layout.grid.top());
        }
        let captions = initial
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) => Some(Rect::from_min_size(text.pos, text.galley.size())),
                _ => None,
            })
            .collect::<Vec<_>>();
        assert!(
            captions
                .iter()
                .all(|bounds| layout.rect.contains_rect(*bounds)),
            "every visible label must remain inside the180px compact ledger"
        );
        for (i, a) in captions.iter().enumerate() {
            assert!(
                captions[i + 1..].iter().all(|b| !a.intersects(*b)),
                "ledger labels cannot overlap: {a:?}"
            );
        }
        progress.processing_frame = Some(count - 1);
        progress.mark_complete();
        let (_, done) = draw(
            &ctx,
            &mut ledger,
            size,
            input(&progress, &[], count),
            1.0,
            vec![],
        );
        assert_eq!(
            images(&done),
            shown,
            "photo cache eviction and active frame changes cannot move retained contacts"
        );
        assert!(!ledger.transitioning());
        let mut next = input(&progress, &[], count);
        next.epoch = 2;
        let (_, cleared) = draw(&ctx, &mut ledger, size, next, 2.0, vec![]);
        assert!(
            images(&cleared).is_empty(),
            "a new bracket cannot inherit earlier photo evidence"
        );
    }
    let rect = Rect::from_min_size(Pos2::ZERO, egui::vec2(200.0, 180.0));
    let layout = Layout::new(rect, 64).unwrap();
    assert!(layout.row(63).height() >= 1.0);
    assert!(rect.contains_rect(layout.row(63)));
    assert!(Layout::new(Rect::from_min_size(Pos2::ZERO, egui::vec2(150.0, 90.0)), 8).is_none());
    assert!(
        visible_contact_indices(
            Rect::from_min_size(Pos2::ZERO, egui::vec2(150.0, 90.0)),
            259
        )
        .is_empty()
    );
}
