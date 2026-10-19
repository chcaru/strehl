use super::*;

fn context<'a>(photo: &'a TextureHandle, fallback: &'a DiagnosticSurface) -> Context<'a> {
    Context {
        base: Some(photo),
        base_folded: 7,
        admitted: None,
        fallback: Some(fallback),
        level: 2,
        pin: egui::pos2(0.5, 0.5),
        aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        extent: Some(egui::vec2(900.0, 600.0)),
    }
}

fn text(output: &egui::FullOutput) -> String {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.galley.text()),
            _ => None,
        })
        .collect::<Vec<_>>()
        .join("\n")
}

#[test]
fn invalid_missing_or_incompatible_crop_cannot_leave_a_previous_fallback_painted() {
    let ctx = egui::Context::default();
    let photo = base(&ctx);
    let good = packet(DiagnosticKind::Averaging, 2);
    for invalid in 0..7 {
        let mut lenses = ContributionLenses::default();
        let data = context(&photo, &good);
        let (_, before) = draw(&mut lenses, &ctx, data, invalid as f64, vec![]);
        assert_eq!(glyph_markers(&before, AMBER).len(), 4);
        let mut bad = good.clone();
        let mut data = data;
        match invalid {
            0 => bad.pixels = Arc::from([255, 255, 64, 255, 0, 0, 0, 0]),
            1 => bad.scope = DiagnosticScope::Frame,
            2 => bad.folded = 0,
            3 => bad.sequence = 0,
            4 => data.extent = Some(egui::vec2(2.0, 2.0)),
            5 => data.extent = Some(egui::vec2(f32::NAN, 600.0)),
            _ => {}
        }
        data.fallback = (invalid != 6).then_some(&bad);
        let (_, rejected) = draw(&mut lenses, &ctx, data, invalid as f64 + 0.2, vec![]);
        assert!(lenses.masks[1].is_none());
        assert!(glyph_markers(&rejected, AMBER).is_empty());
        assert!(
            images(&rejected, photo.id()).is_empty(),
            "stale fallback photograph must not impersonate current evidence"
        );
    }
}

#[test]
fn every_fold_advances_stack_identity_and_latest_pending_mask_finishes_without_pointer_input() {
    let ctx = egui::Context::default();
    let photo = base(&ctx);
    let mut lenses = ContributionLenses::default();
    let mut mask = packet(DiagnosticKind::Averaging, 2);
    let (_, first) = draw(&mut lenses, &ctx, context(&photo, &mask), 0.0, vec![]);
    let destination = images(&first, photo.id())[0];
    assert!(text(&first).contains("STACK FALLBACK"));
    assert!(text(&first).contains("7 folded"));
    for (time, sequence, frame, folded, values) in [
        (0.1, 3, 7, 8, [255, 0, 255, 0, 0, 255, 0, 255]),
        (0.15, 4, 8, 9, [255, 0, 0, 0, 0, 0, 0, 0]),
        (0.2, 5, 9, 10, [0, 0, 0, 0, 0, 0, 0, 255]),
    ] {
        mask.sequence = sequence;
        mask.frame = frame;
        mask.folded = folded;
        mask.pixels = Arc::from(values);
        let (_, painting) = draw(&mut lenses, &ctx, context(&photo, &mask), time, vec![]);
        assert_eq!(
            images(&painting, photo.id()),
            [destination],
            "every generation shares one stable photographic rectangle"
        );
    }
    assert!(
        lenses.transitioning(),
        "fixture must really queue a newer fold behind a reveal"
    );
    let mut last = None;
    for time in [0.3, 0.31, 0.5, 0.7] {
        let (_, output) = draw(&mut lenses, &ctx, context(&photo, &mask), time, vec![]);
        last = Some(output);
    }
    let current = lenses.masks[1].as_ref().unwrap();
    assert_eq!(
        (
            current.packet.sequence,
            current.packet.frame,
            current.packet.folded
        ),
        (5, 9, 10)
    );
    assert!(current.previous.is_none());
    assert!(!lenses.transitioning());
    let output = last.unwrap();
    let dots = glyph_markers(&output, AMBER);
    assert_eq!(dots.len(), 1);
    let expected = mask_geometry(&mask, [900, 600])
        .unwrap()
        .at(7)
        .unwrap()
        .center;
    assert!(dots[0].distance(destination.min + destination.size() * expected.to_vec2()) < 0.001);
    assert!(text(&output).contains("10 folded"));
    assert!(text(&output).contains("local 1/8 · whole 1/8"));
}

#[test]
fn local_counts_follow_real_sample_centers_and_do_not_promote_telemetry_bins_to_coverage() {
    let mask = packet(DiagnosticKind::Averaging, 2);
    let geometry = mask_geometry(&mask, [900, 600]).unwrap();
    let observed = geometry.at(1).unwrap();
    let around = Rect::from_center_size(observed.center, egui::vec2(0.01, 0.01));
    assert_eq!(
        sample_counts(&mask, Some([900, 600]), around),
        (Some((1, 1)), (4, 8))
    );
    let unobserved = Rect::from_center_size(egui::pos2(0.5, 0.5), egui::vec2(0.02, 0.02));
    assert_eq!(
        sample_counts(&mask, Some([900, 600]), unobserved),
        (Some((0, 0)), (4, 8))
    );
    assert_eq!(sample_counts(&mask, None, around), (None, (4, 8)));
    let negative = geometry.at(0).unwrap();
    assert_eq!(
        sample_counts(
            &mask,
            Some([900, 600]),
            Rect::from_center_size(negative.center, egui::vec2(0.01, 0.01))
        ),
        (Some((0, 1)), (4, 8))
    );
}

#[test]
fn same_texture_handle_advances_accepted_prefix_without_false_image_reveal() {
    let ctx = egui::Context::default();
    let mut photo = base(&ctx);
    let fallback = packet(DiagnosticKind::Averaging, 2);
    let mut lenses = ContributionLenses::default();
    let _ = draw(&mut lenses, &ctx, context(&photo, &fallback), 0.0, vec![]);
    let id = photo.id();
    photo.set(
        egui::ColorImage::new([12, 8], vec![Color32::RED; 96]),
        egui::TextureOptions::LINEAR,
    );
    assert_eq!(photo.id(), id, "fixture must mutate an existing handle");
    let mut data = context(&photo, &fallback);
    data.base_folded = 8;
    let (_, output) = draw(&mut lenses, &ctx, data, 0.1, vec![]);
    assert_eq!(lenses.photo.as_ref().unwrap().folded, 8);
    assert!(lenses.photo.as_ref().unwrap().previous.is_none());
    assert!(text(&output).contains("stack 8"));
}
