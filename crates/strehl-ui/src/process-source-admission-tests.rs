use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};

fn packet(sequence: u64, frame: usize, level: usize, yes: bool) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 128,
        height: 96,
        min: 0.0,
        max: 1.0,
        pixels: vec![if yes { 255 } else { 0 }; 128 * 96].into(),
        folded: 1,
    }
}

#[test]
fn stationary_source_and_changing_viewports_do_no_repeated_archive_bit_reads() {
    let mut archive = AdmissionArchive::default();
    for level in 0..4 {
        archive.ingest(&packet(level as u64 + 1, 7, level, true), [3516, 2344]);
    }
    let mut cache = SourceAdmissionCache::default();
    let bands = cache.bands(&archive, [4, 2], 7, [3516, 2344], 4);
    assert_eq!(bands.len(), 4);
    for band in bands {
        assert_eq!(band.counts, Some((128 * 96, 128 * 96)));
        assert_eq!(band.points.len(), 192);
    }
    let reads = cache.bit_reads;
    assert_eq!(
        reads,
        4 * 128 * 96,
        "first paint must actually inspect every real bit"
    );
    for _ in 0..120 {
        cache.bands(&archive, [4, 2], 7, [3516, 2344], 4);
    }
    assert_eq!(
        cache.bit_reads, reads,
        "pointer/zoom paints reuse counts and point geometry"
    );
    // A newly delivered zero is observed data, not absent or a retained yes.
    archive.ingest(&packet(100, 7, 1, false), [3516, 2344]);
    let bands = cache.bands(&archive, [4, 2], 7, [3516, 2344], 4);
    assert_eq!(bands[1].counts, Some((0, 128 * 96)));
    assert!(bands[1].points.is_empty());
    assert_eq!(bands[0].counts, Some((128 * 96, 128 * 96)));
    assert_eq!(cache.bit_reads, reads * 2);
}

#[test]
fn source_and_domain_changes_cannot_reuse_stale_admission_or_invent_unknown_pixels() {
    let mut archive = AdmissionArchive::default();
    let mut packet = packet(1, 7, 0, false);
    // A lone admitted bit off a conventional index-stride must remain visible.
    let mut pixels = packet.pixels.to_vec();
    pixels[1] = 255;
    packet.pixels = pixels.into();
    archive.ingest(&packet, [3516, 2344]);
    let mut cache = SourceAdmissionCache::default();
    let band = &cache.bands(&archive, [4, 2], 7, [3516, 2344], 1)[0];
    assert_eq!(band.counts, Some((1, 128 * 96)));
    assert_eq!(band.points.len(), 1);
    let point = band.points[0];
    let meta = archive.metadata(0, 7).unwrap();
    assert_eq!(
        point,
        SampleGeometry::new(0, meta).unwrap().at(1).unwrap().center
    );
    assert!(
        cache.bands(&archive, [4, 2], 8, [3516, 2344], 1)[0]
            .counts
            .is_none()
    );
    assert!(
        cache.bands(&archive, [4, 2], 7, [3515, 2344], 1)[0]
            .counts
            .is_none()
    );
    let empty = AdmissionArchive::default();
    assert!(
        cache.bands(&empty, [4, 3], 7, [3516, 2344], 1)[0]
            .counts
            .is_none()
    );
}
