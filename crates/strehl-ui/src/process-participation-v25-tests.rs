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
fn texts(output: &egui::FullOutput) -> Vec<&str> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.galley.text()),
            _ => None,
        })
        .collect()
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
fn cold_scrub_retains_real_pixels_and_identity_until_latest_request_is_ready() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let mut row = CaptureParticipation::default();
    let anchors = anchors_at_height(130, bounds().width(), bounds().height());
    let native: Vec<_> = anchors
        .iter()
        .map(|&index| photo(&ctx, index, [60, 40]))
        .collect();
    paint(&mut row, &ctx, data(&progress, &native), 0.0, vec![]);
    let (_, initial) = paint(&mut row, &ctx, data(&progress, &native), 0.1, vec![]);
    let layout = Layout::new(bounds(), 130, anchors.len()).unwrap();
    let requested = 35;
    let latest = 36;
    assert!(!anchors.contains(&requested) && !anchors.contains(&latest));
    let slot = contact_slot(requested, 130, anchors.len());
    assert_eq!(contact_slot(latest, 130, anchors.len()), slot);
    let shown = anchors[slot];
    let old_id = native[slot].texture.id();
    let original = image(&initial, old_id).unwrap();
    for (step, frame) in [requested, latest, requested, latest]
        .into_iter()
        .enumerate()
    {
        let at = egui::pos2(layout.x(frame), original.center().y);
        let (response, output) = paint(
            &mut row,
            &ctx,
            data(&progress, &[]),
            0.2 + step as f64 * 0.1,
            vec![egui::Event::PointerMoved(at)],
        );
        assert_eq!(
            response.hover_source,
            Some(frame),
            "continuous request survives cold pixels"
        );
        assert!(
            row.indices().contains(&frame),
            "decoder still receives the requested frame"
        );
        assert_eq!(
            image(&output, old_id),
            Some(original),
            "no empty flash or size jump"
        );
        assert!(texts(&output).contains(&format!("{:03} · SHOWN", shown + 1).as_str()));
        assert!(texts(&output).contains(&format!("Waiting {:03}", frame + 1).as_str()));
        assert!(!texts(&output).contains(&format!("{:03} · SOURCE", frame + 1).as_str()));
    }
    let obsolete = photo(&ctx, requested, [60, 40]);
    let (_, late) = paint(
        &mut row,
        &ctx,
        data(&progress, std::slice::from_ref(&obsolete)),
        0.7,
        vec![],
    );
    assert_eq!(image(&late, old_id), Some(original));
    assert!(
        image(&late, obsolete.texture.id()).is_none(),
        "late obsolete pixels cannot replace the pending card"
    );
    let ready = photo(&ctx, latest, [60, 40]);
    let (_, committed) = paint(
        &mut row,
        &ctx,
        data(&progress, std::slice::from_ref(&ready)),
        0.8,
        vec![],
    );
    assert_eq!(image(&committed, ready.texture.id()), Some(original));
    assert!(image(&committed, old_id).is_none());
    assert!(texts(&committed).contains(&"037 · SOURCE"));
    assert!(
        !texts(&committed)
            .iter()
            .any(|text| text.starts_with("Waiting"))
    );
    assert!(row.contacts.len() <= MAX_CONTACTS * 2);
}

#[test]
fn clicking_pending_card_chooses_the_shown_photo_even_when_new_pixels_arrive_on_press() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let anchors = anchors_at_height(130, bounds().width(), bounds().height());
    let native: Vec<_> = anchors
        .iter()
        .map(|&index| photo(&ctx, index, [60, 40]))
        .collect();
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, data(&progress, &native), 0.0, vec![]);
    paint(&mut row, &ctx, data(&progress, &native), 0.1, vec![]);
    let layout = Layout::new(bounds(), 130, anchors.len()).unwrap();
    let requested = 35;
    let shown = anchors[contact_slot(requested, 130, anchors.len())];
    let card = layout.contact(shown);
    paint(
        &mut row,
        &ctx,
        data(&progress, &[]),
        0.2,
        vec![egui::Event::PointerMoved(egui::pos2(
            layout.x(requested),
            card.center().y,
        ))],
    );
    assert_eq!(
        row.presented_contacts[contact_slot(requested, 130, anchors.len())],
        shown
    );
    let ready = photo(&ctx, requested, [60, 40]);
    let (pressed, output) = paint(
        &mut row,
        &ctx,
        data(&progress, std::slice::from_ref(&ready)),
        0.3,
        vec![
            egui::Event::PointerMoved(card.center()),
            button(card.center(), true),
        ],
    );
    assert_eq!(pressed.open_source, Some(shown));
    assert!(
        image(
            &output,
            native[contact_slot(shown, 130, anchors.len())].texture.id()
        )
        .is_some()
    );
    assert!(image(&output, ready.texture.id()).is_none());
    let target = 38;
    let (dragged, _) = paint(
        &mut row,
        &ctx,
        data(&progress, &[]),
        0.4,
        vec![egui::Event::PointerMoved(egui::pos2(
            layout.x(target),
            card.center().y,
        ))],
    );
    assert_eq!(
        dragged.open_source,
        Some(target),
        "drag continues along every real capture"
    );
}

#[test]
fn canonical_only_contact_survives_browser_eviction_without_extra_texture_or_wrong_epoch() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, data(&progress, &[]), 0.0, vec![]);
    let layout = Layout::new(bounds(), 130, row.anchors.len()).unwrap();
    let canonical = photo(&ctx, 35, [600, 400]);
    let allocations = ctx.tex_manager().read().num_allocated();
    let at = egui::pos2(layout.x(35), layout.contact(35).center().y);
    let (_, visible) = paint(
        &mut row,
        &ctx,
        Input {
            inspection_photos: std::slice::from_ref(&canonical),
            ..data(&progress, &[])
        },
        0.1,
        vec![egui::Event::PointerMoved(at)],
    );
    let card = image(&visible, canonical.texture.id()).unwrap();
    assert_eq!(
        ctx.tex_manager().read().num_allocated(),
        allocations,
        "retaining a known handle allocates no duplicate photo texture; font atlas updates are independent"
    );
    let (_, evicted) = paint(&mut row, &ctx, data(&progress, &[]), 0.5, vec![]);
    assert_eq!(image(&evicted, canonical.texture.id()), Some(card));
    assert_eq!(row.refinements[&35].bytes, 600 * 400 * 4);
    assert!(row.refinements.values().map(|v| v.bytes).sum::<usize>() <= CONTACT_REFINEMENT_BYTES);
    let native = photo(&ctx, 35, [60, 40]);
    let (_, derivative) = paint(
        &mut row,
        &ctx,
        data(&progress, std::slice::from_ref(&native)),
        0.8,
        vec![],
    );
    assert_eq!(
        image(&derivative, canonical.texture.id()),
        Some(card),
        "native derivative never downgrades the chosen canonical contact"
    );
    let (_, next_epoch) = paint(
        &mut row,
        &ctx,
        Input {
            epoch: 2,
            ..data(&progress, &[])
        },
        1.0,
        vec![],
    );
    assert!(image(&next_epoch, canonical.texture.id()).is_none());
    assert!(row.refinements.is_empty());
}

#[test]
fn cached_curves_and_band_signatures_do_no_recount_for_pointer_motion_without_new_evidence() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    progress.analysis_size = Some([800, 600]);
    for frame in 0..130 {
        for level in 0..8 {
            progress.admission_archive.ingest(
                &packet((frame * 8 + level + 1) as u64, frame, level, 255),
                [800, 600],
            );
        }
    }
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, data(&progress, &[]), 0.0, vec![]);
    let layout = Layout::new(bounds(), 130, row.anchors.len()).unwrap();
    let at = egui::pos2(layout.x(35), layout.lane(0).center().y);
    paint(
        &mut row,
        &ctx,
        data(&progress, &[]),
        0.1,
        vec![egui::Event::PointerMoved(at)],
    );
    let before = (
        row.evidence_refreshes,
        row.band_count_reads,
        row.plot_builds,
        row.tooltip_builds,
    );
    assert!(
        before.0 > 0 && before.1 > 0 && before.2 > 0,
        "the fixture must actually exercise all caches"
    );
    for step in 0..100 {
        paint(
            &mut row,
            &ctx,
            data(&progress, &[]),
            0.2 + step as f64 * 0.01,
            vec![egui::Event::PointerMoved(
                at + egui::vec2((step % 3) as f32 * 0.1, 0.0),
            )],
        );
    }
    assert_eq!(
        (
            row.evidence_refreshes,
            row.band_count_reads,
            row.plot_builds,
            row.tooltip_builds
        ),
        before,
        "100 pointer paints within one capture do not scan masks, pool curves, or format off-hover band tips"
    );
    // Same key and length, newer real observation: generation must invalidate all views.
    let length = progress.admission_archive.len();
    progress
        .admission_archive
        .ingest(&packet(10_000, 35, 0, 0), [800, 600]);
    assert_eq!(progress.admission_archive.len(), length);
    paint(&mut row, &ctx, data(&progress, &[]), 2.0, vec![]);
    assert_eq!(row.evidence[&35].scene.admitted, 0);
    assert_eq!(row.band_evidence[&(35, 0)].1.admitted, 0);
    assert_eq!(row.evidence_refreshes, before.0 + 1);
    assert_eq!(row.plot_builds, before.2 + 1);
    assert_eq!(row.band_count_reads, before.1 + 1);
}

#[test]
fn regional_cache_tracks_real_sample_membership_and_expected_analysis_extent() {
    let mut progress = PipelineProgress::default();
    progress.analysis_size = Some([800, 600]);
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 0, 0, 255), [800, 600]);
    let mut row = CaptureParticipation::default();
    // Four transmitted columns sample actual coefficients at100.5/800,
    // 300.5/800,500.5/800,700.5/800. The first two windows include precisely
    // the first column; the third crosses the second real sample centre.
    let first = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.20, 1.0));
    let same_samples = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.21, 1.0));
    let next_sample = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.45, 1.0));
    row.update(&data(&progress, &[]), &archive, 0, first, 1040.0, HEIGHT);
    let observed = row.evidence[&0].window.observed;
    assert_eq!(observed, 2, "one real column across two sample rows");
    let refreshes = row.evidence_refreshes;
    row.update(
        &data(&progress, &[]),
        &archive,
        0,
        same_samples,
        1040.0,
        HEIGHT,
    );
    assert_eq!(
        row.evidence_refreshes, refreshes,
        "continuous motion within a sample gap does not recount"
    );
    row.update(
        &data(&progress, &[]),
        &archive,
        0,
        next_sample,
        1040.0,
        HEIGHT,
    );
    assert_eq!(
        row.evidence[&0].window.observed, 4,
        "crossing the second centre adds exactly two observations"
    );
    assert_eq!(row.evidence_refreshes, refreshes + 1);
    progress.analysis_size = Some([1600, 1200]);
    row.update(
        &data(&progress, &[]),
        &archive,
        0,
        next_sample,
        1040.0,
        HEIGHT,
    );
    assert_eq!(
        row.evidence[&0].window.observed, 0,
        "same aspect with foreign analysis pixels remains unknown"
    );
    assert_eq!(
        row.evidence[&0].scene.observed, 8,
        "unmapped source observation remains recorded"
    );
}

#[test]
fn full_canonical_budget_can_replace_the_same_visible_slot_atomically() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let mut row = CaptureParticipation::default();
    paint(&mut row, &ctx, data(&progress, &[]), 0.0, vec![]);
    let old = row.anchors[2];
    let new = 35;
    assert_eq!(
        contact_slot(old, 130, row.anchors.len()),
        contact_slot(new, 130, row.anchors.len())
    );
    assert_ne!(old, new);
    // Two legal2048-square handles exhaust32MiB without exceeding egui's
    // default maximum texture side. Only the requested slot is disposable.
    let mut old_photo = photo(&ctx, old, [2048, 2048]);
    old_photo.aperture = [2048, 2048];
    let mut other = photo(&ctx, row.anchors[0], [2048, 2048]);
    other.aperture = [2048, 2048];
    let full = [old_photo.clone(), other.clone()];
    let layout = Layout::new(bounds(), 130, row.anchors.len()).unwrap();
    let (_, shown) = paint(
        &mut row,
        &ctx,
        Input {
            inspection_photos: &full,
            ..data(&progress, &[])
        },
        0.1,
        vec![],
    );
    assert_eq!(
        row.refinements
            .values()
            .map(|value| value.bytes)
            .sum::<usize>(),
        CONTACT_REFINEMENT_BYTES
    );
    let before = image(&shown, old_photo.texture.id()).unwrap();
    let replacement = photo(&ctx, new, [600, 400]);
    let (_, replaced) = paint(
        &mut row,
        &ctx,
        Input {
            inspection_photos: std::slice::from_ref(&replacement),
            ..data(&progress, &[])
        },
        0.2,
        vec![egui::Event::PointerMoved(egui::pos2(
            layout.x(new),
            before.center().y,
        ))],
    );
    assert_eq!(image(&replaced, replacement.texture.id()), Some(before));
    assert!(image(&replaced, old_photo.texture.id()).is_none());
    assert!(!row.refinements.contains_key(&old));
    assert!(
        image(&replaced, other.texture.id()).is_some(),
        "unrelated visible canonical contact survives"
    );
    assert_eq!(
        row.refinements
            .values()
            .map(|value| value.bytes)
            .sum::<usize>(),
        2048 * 2048 * 4 + 600 * 400 * 4
    );
}
