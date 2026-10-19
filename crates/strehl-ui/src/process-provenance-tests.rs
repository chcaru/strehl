use super::*;
use std::sync::Arc;

#[test]
fn denser_grid_preserves_every_bit_and_remains_bounded() {
    let mut archive = AdmissionArchive::default();
    let mut dense = packet(1, 0, 0, [128, 96]);
    dense.pixels = (0..128 * 96)
        .map(|i| if i % 7 == 0 { 255 } else { 0 })
        .collect::<Vec<_>>()
        .into();
    archive.ingest(&dense, [3516, 2344]);
    let (meta, cells) = archive.cells(0, 0).expect("dense observation accepted");
    assert_eq!(meta.samples, [128, 96]);
    let values: Vec<_> = cells.collect();
    assert_eq!(values.len(), 128 * 96);
    assert_eq!(
        values.iter().filter(|&&value| value).count(),
        (128usize * 96).div_ceil(7)
    );
    for (index, value) in values.iter().enumerate() {
        assert_eq!(*value, index % 7 == 0);
    }
    archive.ingest(&packet(2, 1, 0, [129, 96]), [3516, 2344]);
    assert_eq!(archive.len(), 1, "oversized telemetry remains rejected");
    assert!(archive.allocated_bytes() < 8192);
}

fn packet(sequence: u64, frame: usize, level: usize, samples: [usize; 2]) -> DiagnosticSurface {
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
        pixels: vec![0; samples[0] * samples[1]].into(),
        folded: 1,
    }
}

#[test]
fn observed_zero_and_missing_captures_stay_distinct_at_the_same_pin() {
    let mut archive = AdmissionArchive::default();
    let mut admitted = packet(1, 7, 3, [3, 2]);
    admitted.pixels = Arc::from([0, 255, 0, 255, 0, 255]);
    let rejected = packet(2, 8, 3, [3, 2]);
    archive.ingest(&admitted, [3497, 2341]);
    archive.ingest(&rejected, [3497, 2341]);
    assert_eq!(archive.sample(3, 7, [0.5, 0.1]), Some(true));
    assert_eq!(archive.sample(3, 8, [0.5, 0.1]), Some(false));
    assert_eq!(archive.sample(3, 9, [0.5, 0.1]), None);
    assert_eq!(archive.sample(4, 7, [0.5, 0.1]), None);
    assert_eq!(archive.levels().collect::<Vec<_>>(), [3]);
    assert_eq!(archive.frames(3).collect::<Vec<_>>(), [7, 8]);
    assert_eq!(archive.frames(2).count(), 0);
    assert_eq!(archive.frames(64).count(), 0);
    assert_eq!(
        archive.metadata(3, 7),
        Some(AdmissionMeta {
            sequence: 1,
            samples: [3, 2],
            extent: [3497, 2341],
        })
    );
    // A refused input has no frame admission mask; neither counts nor gaps
    // fabricate one. Even an explicitly malformed folded=0 packet is ignored.
    let mut refused = packet(3, 9, 3, [3, 2]);
    refused.folded = 0;
    archive.ingest(&refused, [3497, 2341]);
    assert_eq!(archive.sample(3, 9, [0.5, 0.1]), None);

    // The packed history owns its evidence, not the caller's later pixel edits.
    Arc::get_mut(&mut admitted.pixels).unwrap().fill(0);
    assert_eq!(archive.sample(3, 7, [0.5, 0.1]), Some(true));
}

#[test]
fn all_grid_centers_and_word_boundaries_have_exact_nearest_sample_coordinates() {
    let mut archive = AdmissionArchive::default();
    let mut grid = packet(1, 11, 0, [13, 7]);
    grid.pixels = (0..91)
        .map(|index| {
            if [0, 12, 63, 64, 90].contains(&index) {
                255
            } else {
                0
            }
        })
        .collect::<Vec<_>>()
        .into();
    archive.ingest(&grid, [897, 611]);
    let mut observed_true = 0;
    let mut observed_false = 0;
    for y in 0..7 {
        for x in 0..13 {
            let expected = grid.pixels[y * 13 + x] == 255;
            let pin = [(x as f32 + 0.5) / 13.0, (y as f32 + 0.5) / 7.0];
            assert_eq!(archive.sample(0, 11, pin), Some(expected));
            if expected {
                observed_true += 1;
            } else {
                observed_false += 1;
            }
        }
    }
    assert_eq!((observed_true, observed_false), (5, 86));
    for pin in [[0.0, 0.0], [-9.0, -2.0], [1.0, 1.0], [9.0, 2.0]] {
        assert_eq!(archive.sample(0, 11, pin), Some(true));
    }
    for pin in [
        [f32::NAN, 0.0],
        [0.0, f32::INFINITY],
        [f32::NEG_INFINITY, 1.0],
    ] {
        assert_eq!(archive.sample(0, 11, pin), None);
    }
}

#[test]
fn coarse_odd_lattice_sample_does_not_switch_identity_when_picked() {
    let mut archive = AdmissionArchive::default();
    let mut grid = packet(1, 0, 1, [64, 47]);
    let mut pixels = vec![0; 64 * 47];
    pixels[11] = 255;
    grid.pixels = pixels.into();
    archive.ingest(&grid, [131, 98]);
    // Coefficient11 is centred at22.5 plane pixels after one reduction;
    // the old uniform-bin lookup instead reads telemetry sample10 here.
    let point = [22.5 / 131.0, 0.5 / 98.0];
    assert_eq!(archive.sample(1, 0, point), Some(true));
    assert_eq!(archive.sample(1, 0, [0.5 / 131.0, 0.5 / 98.0]), Some(false));
}

#[test]
fn invalid_scope_binary_range_dimensions_and_identity_cannot_erase_evidence() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 1, 2, [2, 2]), [40, 30]);
    for defect in 0..17 {
        let mut invalid = packet(2, 1, 2, [2, 2]);
        invalid.pixels = Arc::from([255; 4]);
        let mut extent = [40, 30];
        match defect {
            0 => invalid.kind = DiagnosticKind::Averaging,
            1 => invalid.scope = DiagnosticScope::Stack,
            2 => invalid.scale = DiagnosticScale::Log,
            3 => invalid.folded = 2,
            4 => invalid.sequence = 0,
            5 => invalid.frame = 65_536,
            6 => invalid.level = 64,
            7 => invalid.min = 0.1,
            8 => invalid.max = 2.0,
            9 => invalid.min = f32::NAN,
            10 => invalid.width = 0,
            11 => invalid.height = 0,
            12 => invalid.width = 65,
            13 => invalid.height = 49,
            14 => invalid.pixels = Arc::from([0, 255, 128, 255]),
            15 => invalid.pixels = Arc::from([255; 3]),
            _ => extent = [0, 30],
        }
        archive.ingest(&invalid, extent);
        assert_eq!(archive.len(), 1, "invalid case {defect}");
        assert_eq!(archive.sample(2, 1, [0.5, 0.5]), Some(false));
        assert_eq!(archive.metadata(2, 1).unwrap().sequence, 1);
        assert_eq!((archive.dropped(), archive.resets()), (0, 0));
    }
}

#[test]
fn newest_same_key_wins_but_distinct_captures_can_arrive_out_of_order() {
    let mut archive = AdmissionArchive::default();
    let mut newest = packet(30, 17, 4, [1, 1]);
    newest.pixels = Arc::from([255]);
    archive.ingest(&newest, [30, 20]);
    archive.ingest(&packet(9, 2, 4, [1, 1]), [30, 20]);
    archive.ingest(&packet(20, 10, 4, [1, 1]), [30, 20]);
    for sequence in [30, 29] {
        archive.ingest(&packet(sequence, 17, 4, [1, 1]), [30, 20]);
        assert_eq!(archive.sample(4, 17, [0.5, 0.5]), Some(true));
    }
    archive.ingest(&packet(31, 17, 4, [1, 1]), [30, 20]);
    assert_eq!(archive.sample(4, 17, [0.5, 0.5]), Some(false));
    assert_eq!(archive.metadata(4, 17).unwrap().sequence, 31);
    assert_eq!(archive.frames(4).collect::<Vec<_>>(), [2, 10, 17]);
    assert_eq!(archive.len(), 3);
}

#[test]
fn newer_sampling_domain_resets_only_its_level_and_stale_domains_cannot_return() {
    for drift in 0..3 {
        let mut archive = AdmissionArchive::default();
        archive.ingest(&packet(10, 0, 2, [3, 2]), [900, 600]);
        archive.ingest(&packet(20, 1, 2, [3, 2]), [900, 600]);
        archive.ingest(&packet(21, 1, 3, [3, 2]), [900, 600]);
        let size = match drift {
            0 => [4, 2],
            1 => [3, 3],
            _ => [3, 2],
        };
        let extent = if drift == 2 { [600, 900] } else { [900, 600] };
        archive.ingest(&packet(15, 2, 2, size), extent);
        assert_eq!(
            archive.len(),
            3,
            "an older foreign domain cannot reset history"
        );
        archive.ingest(&packet(30, 3, 2, size), extent);
        assert_eq!(archive.len(), 2);
        assert_eq!(archive.resets(), 1);
        assert_eq!(archive.frames(2).collect::<Vec<_>>(), [3]);
        assert_eq!(archive.sample(3, 1, [0.5, 0.5]), Some(false));
        archive.ingest(&packet(25, 4, 2, [3, 2]), [900, 600]);
        archive.ingest(&packet(29, 5, 2, size), extent);
        assert_eq!(archive.frames(2).collect::<Vec<_>>(), [3]);
        archive.ingest(&packet(31, 6, 2, size), extent);
        assert_eq!(archive.frames(2).collect::<Vec<_>>(), [3, 6]);
        assert_eq!(archive.metadata(2, 6).unwrap().extent, extent);
    }
}

#[test]
fn hundreds_of_captures_remain_queryable_after_packet_payloads_are_gone() {
    let mut archive = AdmissionArchive::default();
    let mut sequence = 0;
    for frame in 0..521 {
        for level in 0..11 {
            sequence += 1;
            let mut observed = packet(sequence, frame, level, [7, 5]);
            let pixels = Arc::get_mut(&mut observed.pixels).unwrap();
            pixels[17] = if (frame * 3 + level) % 5 == 0 { 255 } else { 0 };
            archive.ingest(&observed, [16_384, 12_288]);
        }
    }
    assert_eq!(archive.len(), 521 * 11);
    assert_eq!(archive.dropped(), 0);
    assert_eq!(archive.levels().count(), 11);
    let mut positives = 0;
    for level in 0..11 {
        assert_eq!(archive.frames(level).count(), 521);
        for frame in 0..521 {
            let expected = (frame * 3 + level) % 5 == 0;
            assert_eq!(archive.sample(level, frame, [0.5, 0.5]), Some(expected));
            positives += usize::from(expected);
        }
    }
    assert!(
        positives > 1000 && positives < 1200,
        "both outcomes must occur"
    );
    assert!(archive.allocated_bytes() < 14 * 1024 * 1024);
}

#[test]
fn capacity_is_global_and_explicit_while_existing_keys_and_domain_resets_still_work() {
    let mut archive = AdmissionArchive::default();
    for index in 0..MAX_ENTRIES + 5 {
        let level = index % 16;
        let frame = index / 16;
        let samples = [
            900usize.div_ceil(1 << level).min(64),
            600usize.div_ceil(1 << level).min(48),
        ];
        archive.ingest(&packet(index as u64 + 1, frame, level, samples), [900, 600]);
    }
    assert_eq!(archive.len(), MAX_ENTRIES);
    assert_eq!(archive.dropped(), 5);
    assert_eq!(archive.sample(0, 0, [0.0, 0.0]), Some(false));
    assert_eq!(archive.sample(15, 511, [1.0, 1.0]), Some(false));
    assert_eq!(archive.sample(0, 512, [0.0, 0.0]), None);
    assert!(archive.allocated_bytes() < 14 * 1024 * 1024);
    let capacity = archive.entries.capacity();
    let mut refresh = packet(20_000, 0, 0, [64, 48]);
    refresh.pixels = Arc::from(vec![255; 64 * 48]);
    archive.ingest(&refresh, [900, 600]);
    assert_eq!(archive.sample(0, 0, [0.5, 0.5]), Some(true));
    assert_eq!((archive.len(), archive.dropped()), (MAX_ENTRIES, 5));

    archive.ingest(&packet(20_001, 700, 0, [3, 2]), [800, 600]);
    assert_eq!(archive.len(), MAX_ENTRIES - 512 + 1);
    assert_eq!(archive.resets(), 1);
    assert_eq!(archive.sample(0, 0, [0.5, 0.5]), None);
    assert_eq!(archive.sample(15, 511, [0.5, 0.5]), Some(false));
    archive.ingest(&packet(20_002, 512, 1, [64, 48]), [900, 600]);
    assert_eq!(archive.sample(1, 512, [0.5, 0.5]), Some(false));
    assert_eq!(archive.entries.capacity(), capacity);
    assert_eq!(archive.dropped(), 5);
}
