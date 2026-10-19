use super::*;

fn packet(sequence: u64, frame: usize, level: usize, value: u8) -> DiagnosticSurface {
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
        pixels: vec![value; 16 * 12].into(),
    }
}
fn unit() -> Rect {
    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
}
fn popup_text(probe: &RegionProbe) -> Vec<String> {
    let ctx = egui::Context::default();
    let mut result = Vec::new();
    let _ = ctx.run(Default::default(), |ctx| {
        result = probe
            .tooltip(ctx, 370.0, 900.0, unit(), 0, [2048, 1536], 130)
            .shapes
            .into_iter()
            .filter_map(|shape| match shape {
                egui::Shape::Text(text) => Some(text.galley.text().to_owned()),
                _ => None,
            })
            .collect();
    });
    result
}

#[test]
fn warm_region_motion_skips_receipt_scans_recounts_and_peer_sort_but_real_refresh_invalidates() {
    let mut archive = AdmissionArchive::default();
    for frame in 0..130 {
        for level in 0..7 {
            archive.ingest(
                &packet((frame * 7 + level + 1) as u64, frame, level, 255),
                [2048, 1536],
            );
        }
    }
    let mut probe = RegionProbe::default();
    probe.set_source_frame(Some(35));
    let region = Rect::from_min_max(egui::pos2(0.40123, 0.40123), egui::pos2(0.53234, 0.53234));
    probe.update(&archive, 0, [2048, 1536], 130, region);
    let before = (
        probe.receipt_scans,
        probe.readings,
        probe.spatial_reads,
        probe.spatial_selections,
    );
    assert!(before.0 > 0 && before.1 > 0 && before.2 > 0 && before.3 > 0);
    for step in 0..100 {
        probe.update(
            &archive,
            0,
            [2048, 1536],
            130,
            region.translate(Vec2::splat(step as f32 * 0.00000001)),
        );
    }
    assert_eq!(
        (
            probe.receipt_scans,
            probe.readings,
            probe.spatial_reads,
            probe.spatial_selections
        ),
        before,
        "same real sample membership needs no full-archive scan, counts, glyph reads, or peer selection"
    );
    let old_len = archive.len();
    archive.ingest(&packet(10000, 35, 0, 0), [2048, 1536]);
    assert_eq!(archive.len(), old_len);
    probe.update(&archive, 0, [2048, 1536], 130, region);
    assert_eq!(probe.receipt_scans, before.0 + 1);
    assert_eq!(
        probe.readings,
        before.1 + 1,
        "only replaced frame/band needs its count recomputed"
    );
    assert_eq!(probe.evidence[&(0, 35)].count.admitted, 0);
    assert_eq!(probe.spatial_key.as_ref().unwrap().sources[0].0, 35);
    assert!(probe.spatial.iter().all(|point| point.sources & 1 == 0));
}

#[test]
fn compared_capture_is_explicit_even_when_zero_or_unknown_and_never_relabels_other_samples() {
    let mut archive = AdmissionArchive::default();
    for frame in 0..5 {
        archive.ingest(
            &packet(frame as u64 + 1, frame, 0, if frame == 4 { 0 } else { 255 }),
            [2048, 1536],
        );
    }
    let mut probe = RegionProbe::default();
    probe.set_source_frame(Some(4));
    probe.update(&archive, 0, [2048, 1536], 130, unit());
    let ids: Vec<_> = probe
        .spatial_key
        .as_ref()
        .unwrap()
        .sources
        .iter()
        .map(|source| source.0)
        .collect();
    assert_eq!(
        ids,
        [4, 0, 1],
        "comparison source precedes tied regional peers"
    );
    assert!(
        probe.spatial.iter().all(|point| point.sources == 0b110),
        "zero admission cannot inherit peers' admitted glyphs"
    );
    assert!(
        popup_text(&probe)
            .iter()
            .any(|text| text == "Comparing 005 · 0/192 samples admitted")
    );
    let scans = probe.receipt_scans;
    let readings = probe.readings;
    probe.set_source_frame(Some(129));
    probe.update(&archive, 0, [2048, 1536], 130, unit());
    assert!(
        popup_text(&probe)
            .iter()
            .any(|text| text == "Comparing 130 · no recorded samples here")
    );
    assert!(
        !probe
            .spatial_key
            .as_ref()
            .unwrap()
            .sources
            .iter()
            .any(|source| source.0 == 129)
    );
    assert_eq!(probe.receipt_scans, scans);
    assert_eq!(
        probe.readings, readings,
        "changing compared source must not re-read observation counts"
    );
    probe.set_source_frame(None);
    probe.update(&archive, 0, [2048, 1536], 130, unit());
    assert!(
        !popup_text(&probe)
            .iter()
            .any(|text| text.starts_with("Comparing"))
    );
}

#[test]
fn receipt_fast_path_invalidates_frame_count_active_band_and_analysis_domain() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 0, 0, 255), [2048, 1536]);
    archive.ingest(&packet(2, 4, 0, 255), [2048, 1536]);
    archive.ingest(&packet(3, 4, 1, 0), [2048, 1536]);
    let mut probe = RegionProbe::default();
    probe.update(&archive, 0, [2048, 1536], 130, unit());
    assert_eq!(probe.spatial_key.as_ref().unwrap().sources.len(), 2);
    probe.update(&archive, 0, [2048, 1536], 1, unit());
    assert_eq!(probe.evidence.len(), 1);
    assert_eq!(probe.spatial_key.as_ref().unwrap().sources.len(), 1);
    probe.update(&archive, 1, [2048, 1536], 130, unit());
    assert_eq!(probe.spatial_key.as_ref().unwrap().level, 1);
    assert!(
        probe.spatial.is_empty(),
        "selected band has observed rejection, never old-band admission"
    );
    probe.update(&archive, 0, [4096, 3072], 130, unit());
    assert!(probe.evidence.is_empty());
    assert!(probe.spatial.is_empty());
}

#[test]
fn binary_membership_partitions_match_actual_coefficient_centres_at_odd_extents_and_boundaries() {
    for (level, samples, extent) in [
        (0, [128, 96], [2048, 1536]),
        (2, [3, 3], [9, 9]),
        (3, [13, 7], [897, 611]),
    ] {
        let meta = AdmissionMeta {
            sequence: 1,
            samples,
            extent,
        };
        let geometry = SampleGeometry::new(level, meta).unwrap();
        for i in [0, samples[0] / 2, samples[0] * samples[1] - 1] {
            let center = geometry.at(i).unwrap().center;
            for region in [
                unit(),
                Rect::from_center_size(center, Vec2::splat(0.003)),
                Rect::from_min_max(Pos2::ZERO, center),
                Rect::from_min_max(center, egui::pos2(1.0, 1.0)),
            ] {
                let window = SampleWindow::new(level, meta, region).unwrap();
                let actual: Vec<_> = window.indices().collect();
                let expected: Vec<_> = (0..samples[0] * samples[1])
                    .filter(|&index| {
                        let point = geometry.at(index).unwrap().center;
                        point.x >= region.left()
                            && point.x < region.right()
                            && point.y >= region.top()
                            && point.y < region.bottom()
                    })
                    .collect();
                assert_eq!(
                    actual, expected,
                    "level={level} index={i} region={region:?}"
                );
            }
        }
    }
}
