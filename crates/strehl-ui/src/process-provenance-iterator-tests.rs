use super::*;

#[test]
fn borrowed_mask_skips_read_only_requested_bits_and_preserve_iterator_contract() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(
        &DiagnosticSurface {
            sequence: 1,
            frame: 0,
            level: 0,
            kind: DiagnosticKind::GateSupport,
            scope: DiagnosticScope::Frame,
            scale: DiagnosticScale::Linear,
            width: 16,
            height: 8,
            min: 0.0,
            max: 1.0,
            folded: 1,
            pixels: (0..128)
                .map(|index| if index % 7 == 0 { 255 } else { 0 })
                .collect::<Vec<_>>()
                .into(),
        },
        [160, 80],
    );
    let mut cells = archive.cells(0, 0).unwrap().1;
    assert_eq!(cells.len(), 128);
    assert_eq!(cells.next(), Some(true));
    assert_eq!(
        cells.nth(62),
        Some(true),
        "bit63 crosses to the end of the first word"
    );
    assert_eq!(cells.len(), 64);
    assert_eq!(cells.next(), Some(false), "bit64 starts the next word");
    assert_eq!(
        cells.nth(62),
        Some(false),
        "last bit127 remains addressable"
    );
    assert_eq!(cells.size_hint(), (0, Some(0)));
    assert_eq!(cells.bit_reads(), 4, "skipped bits are never loaded");
    assert_eq!(cells.next(), None);
    assert_eq!(cells.nth(usize::MAX), None);
    assert_eq!(cells.bit_reads(), 4);
    let mut overflow = archive.cells(0, 0).unwrap().1;
    assert_eq!(overflow.next(), Some(true));
    assert_eq!(overflow.nth(usize::MAX), None);
    assert_eq!(overflow.len(), 0);
    assert_eq!(
        overflow.next(),
        None,
        "exhaustion is fused after an overflowing skip"
    );
    let all = archive.cells(0, 0).unwrap().1.collect::<Vec<_>>();
    assert_eq!(
        all,
        (0..128).map(|index| index % 7 == 0).collect::<Vec<_>>()
    );
}

#[test]
fn counts_use_exact_tail_length_and_keep_unrecorded_masks_unknown() {
    let mut archive = AdmissionArchive::default();
    let mut packet = DiagnosticSurface {
        sequence: 1,
        frame: 7,
        level: 2,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 13,
        height: 7,
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: (0..91)
            .map(|i| {
                if [0, 12, 63, 64, 90].contains(&i) {
                    255
                } else {
                    0
                }
            })
            .collect::<Vec<_>>()
            .into(),
    };
    archive.ingest(&packet, [897, 611]);
    assert_eq!(archive.counts(2, 7), Some((5, 91)));
    assert_eq!(archive.counts(2, 8), None);
    assert_eq!(archive.counts(1, 7), None);
    packet.sequence = 2;
    packet.pixels = vec![0; 91].into();
    archive.ingest(&packet, [897, 611]);
    assert_eq!(
        archive.counts(2, 7),
        Some((0, 91)),
        "observed zero differs from unknown"
    );
}

#[test]
fn retained_revision_tracks_same_key_refresh_and_domain_reset_but_not_rejected_packets() {
    let mut archive = AdmissionArchive::default();
    let mut packet = DiagnosticSurface {
        sequence: 1,
        frame: 7,
        level: 2,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 4,
        height: 2,
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: vec![255; 8].into(),
    };
    let initial = archive.revision();
    archive.ingest(&packet, [800, 600]);
    let inserted = archive.revision();
    assert!(inserted > initial);
    packet.sequence = 2;
    packet.pixels = vec![0; 8].into();
    archive.ingest(&packet, [800, 600]);
    let refreshed = archive.revision();
    assert!(refreshed > inserted);
    assert_eq!(archive.len(), 1);
    assert_eq!(archive.counts(2, 7), Some((0, 8)));
    archive.ingest(&packet, [800, 600]);
    packet.sequence = 1;
    packet.pixels = vec![255; 8].into();
    archive.ingest(&packet, [800, 600]);
    packet.sequence = 3;
    packet.pixels = vec![128; 8].into();
    archive.ingest(&packet, [800, 600]);
    assert_eq!(
        archive.revision(),
        refreshed,
        "duplicate, stale, and invalid masks do not invalidate readers"
    );
    assert_eq!(archive.counts(2, 7), Some((0, 8)));
    packet.sequence = 4;
    packet.frame = 8;
    packet.pixels = vec![255; 8].into();
    archive.ingest(&packet, [1600, 1200]);
    assert!(archive.revision() > refreshed);
    assert_eq!(archive.counts(2, 7), None);
    assert_eq!(archive.counts(2, 8), Some((8, 8)));
}
