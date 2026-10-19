use super::*;

fn packet(frame: usize, level: usize, value: u8, sequence: u64) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 16,
        height: 12,
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: vec![value; 192].into(),
    }
}
fn unit() -> Rect {
    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
}

#[test]
fn region_heatmap_distinguishes_rejection_missing_and_support_and_reuses_membership() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(0, 0, 255, 1), [2048, 1536]);
    archive.ingest(&packet(1, 0, 0, 2), [2048, 1536]);
    let mut probe = RegionProbe::default();
    probe.update(&archive, 0, [2048, 1536], 3, unit());
    let bounds = Rect::from_min_size(egui::pos2(10.0, 20.0), egui::vec2(300.0, 20.0));
    let first = probe.heatmap(bounds, 20.0, 3);
    assert_eq!(
        first.vertices.len(),
        8,
        "positive and zero are drawn; absent frame has no invented cell"
    );
    assert_eq!(first.vertices[0].color, level_color(0));
    assert_eq!(first.vertices[4].color, level_color(0).gamma_multiply(0.1));
    assert!(first.vertices[..4].iter().all(|v| v.pos.x <= 110.0));
    assert!(
        first.vertices[4..]
            .iter()
            .all(|v| (110.0..=210.0).contains(&v.pos.x))
    );
    probe.update(&archive, 0, [2048, 1536], 3, unit().shrink(0.00001));
    let unchanged = probe.heatmap(bounds, 20.0, 3);
    assert!(
        std::sync::Arc::ptr_eq(&first, &unchanged),
        "sub-sample movement must retain heatmap"
    );
    archive.ingest(&packet(1, 0, 255, 100), [2048, 1536]);
    probe.update(&archive, 0, [2048, 1536], 3, unit());
    let changed = probe.heatmap(bounds, 20.0, 3);
    assert!(!std::sync::Arc::ptr_eq(&first, &changed));
    assert_eq!(
        changed.vertices[4].color,
        level_color(0),
        "real refreshed evidence must change actual paint"
    );
}

#[test]
fn footprint_cards_share_final_uv_preserve_aspect_and_keep_sparse_source_visible() {
    let mut archive = AdmissionArchive::default();
    // Both pass, but source1 has only one positive interleaved among source0.
    let size = [128, 96];
    for frame in 0..2 {
        let mut p = packet(frame, 0, 255, frame as u64 + 1);
        p.width = size[0];
        p.height = size[1];
        p.pixels = (0..size[0] * size[1])
            .map(|i| if frame == 0 || i == 129 { 255 } else { 0 })
            .collect::<Vec<_>>()
            .into();
        archive.ingest(&p, [2048, 1536]);
    }
    let mut probe = RegionProbe {
        texture: Some(egui::TextureId::User(87)),
        ..Default::default()
    };
    probe.set_source_frame(Some(1));
    probe.update(&archive, 0, [2048, 1536], 2, unit());
    let ctx = egui::Context::default();
    let mut meshes = Vec::new();
    let _ = ctx.run(Default::default(), |ctx| {
        meshes = probe
            .tooltip(ctx, 370.0, 800.0, unit(), 0, [4096, 3072], 2)
            .shapes
            .into_iter()
            .filter_map(|s| match s {
                egui::Shape::Mesh(m) => Some(m),
                _ => None,
            })
            .collect();
    });
    let images: Vec<_> = meshes
        .iter()
        .filter(|m| m.texture_id == egui::TextureId::User(87))
        .collect();
    assert_eq!(
        images.len(),
        2,
        "actual photographic cards, not blank diagnostics"
    );
    for image in images {
        let painted = Rect::from_points(&image.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
        let uv = Rect::from_points(&image.vertices.iter().map(|v| v.uv).collect::<Vec<_>>());
        assert_eq!(uv, unit());
        assert!((painted.aspect_ratio() - 4.0 / 3.0).abs() < 0.0001);
    }
    assert!(
        meshes
            .iter()
            .any(|mesh| mesh.texture_id == egui::TextureId::default()
                && mesh.vertices.len() == 4
                && mesh.vertices.iter().all(|v| v.color == capture_ink(1))),
        "thin AFTER selecting positive sites: a sparse positive source must keep its actual mark"
    );
}

#[test]
fn compact_region_legend_preserves_real_capture_identity_when_cards_cannot_fit() {
    let mut archive = AdmissionArchive::default();
    // Include a genuinely observed zero-support current source. It must remain
    // identifiable beside two positive peers; an absent source must not appear.
    for (frame, value) in [(7, 0), (54, 255), (129, 255)] {
        archive.ingest(&packet(frame, 2, value, frame as u64 + 1), [2048, 1536]);
    }
    archive.ingest(&packet(54, 0, 255, 200), [2048, 1536]);
    let mut probe = RegionProbe {
        texture: Some(egui::TextureId::User(93)),
        ..Default::default()
    };
    probe.set_source_frame(Some(7));
    probe.update(&archive, 2, [2048, 1536], 130, unit());
    assert_eq!(probe.evidence[&(2, 7)].count.admitted, 0);
    assert!(probe.evidence[&(2, 7)].count.observed > 0);
    let ctx = egui::Context::default();
    let _ = ctx.run(Default::default(), |ctx| {
        for (width, height) in [(200.0, 800.0), (370.0, 220.0)] {
            let content = probe.tooltip(ctx, width, height, unit(), 2, [4096, 3072], 130);
            assert!(
                !content.shapes.iter().any(|shape| matches!(shape,
                egui::Shape::Mesh(mesh) if mesh.texture_id == egui::TextureId::User(93))),
                "both the width-limited and height-limited cases must actually hide crop cards"
            );
            let mut legend = Vec::new();
            for (frame, id) in [(7, "008"), (54, "055"), (129, "130")] {
                let text = content
                    .shapes
                    .iter()
                    .find_map(|shape| match shape {
                        egui::Shape::Text(text) if text.galley.text() == id => Some(text),
                        _ => None,
                    })
                    .unwrap_or_else(|| {
                        panic!("capture {id} must remain named when cards are hidden")
                    });
                assert_eq!(text.fallback_color, capture_ink(frame));
                let rect = text.visual_bounding_rect();
                assert!(
                    rect.left() >= 8.0
                        && rect.right() <= width - 8.0
                        && rect.top() >= 0.0
                        && rect.bottom() < height,
                    "actual legend must fit its visible popup: {rect:?}"
                );
                legend.push(rect);
            }
            assert!(
                legend
                    .windows(2)
                    .all(|pair| pair[0].right() < pair[1].left()),
                "capture labels must not overlap"
            );
            assert!(
                !content.shapes.iter().any(|shape| matches!(shape,
                egui::Shape::Text(text) if text.galley.text() == "092")),
                "an unrecorded capture cannot acquire a support identity"
            );
            assert!(
                content.shapes.iter().any(|shape| matches!(shape,
                egui::Shape::Rect(rect) if rect.stroke.width == 0.7
                    && rect.stroke.color == level_color(2).gamma_multiply(0.65)
                    && rect.rect.width() > width * 0.5)),
                "the active detail band must remain linked across the heatmap row"
            );
        }
        let full = probe.tooltip(ctx, 370.0, 800.0, unit(), 2, [4096, 3072], 130);
        assert!(full.shapes.iter().any(|shape| matches!(shape,
            egui::Shape::Text(text) if text.galley.text().contains("4px grid")
                && text.galley.text().contains("8px photo"))),
            "a level2 coefficient spans4 analysis pixels and8 photograph pixels in this2× output; the card must name both domains");
        assert!(full.shapes.iter().any(|shape| matches!(shape,
            egui::Shape::Text(text) if text.galley.text().contains("PHOTOGRAPH PX"))),
            "heatmap row units must identify their photograph domain rather than imply the matrix grid");
        assert_eq!(
            full.shapes
                .iter()
                .filter(|shape| matches!(shape,
            egui::Shape::Mesh(mesh) if mesh.texture_id == egui::TextureId::User(93)))
                .count(),
            3,
            "roomy positive control must actually show the three photographed cards"
        );
    });
}
