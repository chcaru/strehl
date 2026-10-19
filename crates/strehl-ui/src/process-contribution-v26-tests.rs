use super::*;

fn dense(kind: DiagnosticKind, sequence: u64, value: u8) -> DiagnosticSurface {
    let mut packet = packet(kind, sequence);
    packet.width = 128;
    packet.height = 96;
    packet.pixels = vec![value; 128 * 96].into();
    packet
}
fn data<'a>(
    photo: &'a TextureHandle,
    gate: &'a DiagnosticSurface,
    fallback: Option<&'a DiagnosticSurface>,
) -> Context<'a> {
    Context {
        base: Some(photo),
        base_folded: 7,
        admitted: Some(gate),
        fallback,
        level: 2,
        pin: egui::pos2(0.5, 0.5),
        aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        extent: Some(egui::vec2(3516.0, 2344.0)),
    }
}
fn sample_meshes(output: &egui::FullOutput) -> Vec<Arc<egui::Mesh>> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh)
                if mesh.texture_id == egui::TextureId::default() && !mesh.is_empty() =>
            {
                Some(Arc::clone(mesh))
            }
            _ => None,
        })
        .collect()
}

#[test]
fn stable_dense_lenses_reuse_validated_receipts_counts_and_exact_retained_meshes() {
    let ctx = egui::Context::default();
    let photo = base(&ctx);
    let gate = dense(DiagnosticKind::GateSupport, 1, 255);
    let fallback = dense(DiagnosticKind::Averaging, 2, 255);
    let mut lenses = ContributionLenses::default();
    let context = data(&photo, &gate, Some(&fallback));
    let (_, first) = draw(&mut lenses, &ctx, context, 0.0, vec![]);
    let meshes = sample_meshes(&first);
    assert_eq!(
        meshes.len(),
        2,
        "each dense lens submits one actual sparse mesh"
    );
    assert_eq!(lenses.validation_scans, 2);
    for mask in lenses.masks.iter().flatten() {
        assert_eq!(mask.count_reads, 1);
        assert_eq!(mask.draw.builds, 1);
    }
    assert!(
        meshes
            .iter()
            .all(|mesh| mesh.vertices.len() > 300 && mesh.vertices.len() < 320 * 50)
    );
    for step in 1..=50 {
        let (_, output) = draw(
            &mut lenses,
            &ctx,
            context,
            step as f64 * 0.02,
            vec![egui::Event::PointerMoved(egui::pos2(
                4.0 + step as f32,
                78.0,
            ))],
        );
        let painted = sample_meshes(&output);
        assert_eq!(painted.len(), 2);
        for (actual, old) in painted.iter().zip(&meshes) {
            assert!(Arc::ptr_eq(actual, old));
        }
    }
    assert_eq!(
        lenses.validation_scans, 2,
        "unchanged immutable packets are never rescanned"
    );
    for mask in lenses.masks.iter().flatten() {
        assert_eq!(mask.count_reads, 1);
        assert_eq!(mask.draw.builds, 1);
    }
}

#[test]
fn cached_validation_cannot_accept_changed_metadata_foreign_domain_or_new_arc_contents() {
    let ctx = egui::Context::default();
    let photo = base(&ctx);
    let good = dense(DiagnosticKind::GateSupport, 1, 255);
    for bad_case in 0..5 {
        let mut lenses = ContributionLenses::default();
        draw(&mut lenses, &ctx, data(&photo, &good, None), 0.0, vec![]);
        let mut bad = good.clone();
        match bad_case {
            0 => bad.scope = DiagnosticScope::Stack,
            1 => bad.scale = DiagnosticScale::Log,
            2 => bad.pixels = vec![64; 128 * 96].into(),
            _ => {}
        }
        let mut context = data(&photo, &bad, None);
        if bad_case == 3 {
            context.extent = Some(egui::vec2(2.0, 2.0));
        }
        if bad_case == 4 {
            context.extent = Some(egui::vec2(f32::NAN, 2344.0));
        }
        let (_, rejected) = draw(&mut lenses, &ctx, context, 0.1, vec![]);
        assert!(lenses.masks[0].is_none());
        assert!(sample_meshes(&rejected).is_empty());
        let scans = lenses.validation_scans;
        draw(&mut lenses, &ctx, context, 0.2, vec![]);
        assert_eq!(
            lenses.validation_scans, scans,
            "repeated invalid immutable observation is cached as invalid"
        );
    }
}

#[test]
fn replaced_same_sequence_pixels_refresh_the_mask_and_fade_without_rebuilding_geometry_each_paint()
{
    let ctx = egui::Context::default();
    let photo = base(&ctx);
    let first = packet(DiagnosticKind::GateSupport, 1);
    let mut lenses = ContributionLenses::default();
    draw(&mut lenses, &ctx, data(&photo, &first, None), 0.0, vec![]);
    let mut changed = first.clone();
    changed.pixels = Arc::from([255, 0, 0, 0, 0, 0, 0, 0]);
    let (_, begun) = draw(&mut lenses, &ctx, data(&photo, &changed, None), 0.1, vec![]);
    assert!(lenses.masks[0].as_ref().unwrap().previous.is_some());
    assert!(
        !sample_meshes(&begun).is_empty(),
        "old observations remain visible at reveal start"
    );
    draw(
        &mut lenses,
        &ctx,
        data(&photo, &changed, None),
        0.18,
        vec![],
    );
    let mask = lenses.masks[0].as_ref().unwrap();
    assert!(mask.alpha > 0.0 && mask.alpha < 1.0);
    assert_eq!(mask.draw.builds, 1);
    assert_eq!(
        mask.previous_draw.builds, 1,
        "previous geometry is carried into the reveal"
    );
    let (_, settled) = draw(&mut lenses, &ctx, data(&photo, &changed, None), 0.4, vec![]);
    let mask = lenses.masks[0].as_ref().unwrap();
    assert_eq!(
        mask.draw.builds, 1,
        "opacity updates recolor, never reselect glyph geometry"
    );
    assert_eq!(mask.glyphs.len(), 1);
    assert_eq!(glyph_markers(&settled, GREEN).len(), 1);
    assert!(!lenses.transitioning());
}

#[test]
fn local_counts_reuse_sample_membership_but_new_region_recounts_real_centres() {
    let ctx = egui::Context::default();
    let photo = base(&ctx);
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let mut lenses = ContributionLenses::default();
    let mut context = data(&photo, &gate, None);
    context.aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.2, 1.0));
    draw(&mut lenses, &ctx, context, 0.0, vec![]);
    let initial = lenses.masks[0].as_ref().unwrap().local_counts;
    assert_eq!(initial, Some((1, 2)));
    context.aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.21, 1.0));
    draw(&mut lenses, &ctx, context, 0.1, vec![]);
    assert_eq!(lenses.masks[0].as_ref().unwrap().count_reads, 1);
    context.aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.45, 1.0));
    draw(&mut lenses, &ctx, context, 0.2, vec![]);
    let mask = lenses.masks[0].as_ref().unwrap();
    assert_eq!(mask.count_reads, 2);
    assert_eq!(mask.local_counts, Some((2, 4)));
    assert_eq!(mask.whole, (4, 8));
}
