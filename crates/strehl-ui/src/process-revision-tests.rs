use super::*;
use std::sync::Arc;

fn conservative(actual: f32, nominal: f32) {
    assert_eq!(actual.signum(), nominal.signum());
    assert!(actual.abs() <= nominal.abs());
    assert!(
        (actual - nominal).abs() < 0.002,
        "{actual} should only differ from {nominal} by conservative floating-point padding"
    );
}

fn packet(
    sequence: u64,
    folded: usize,
    range: [f32; 2],
    size: [usize; 2],
    pixels: Vec<u8>,
) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame: folded + 2,
        level: 3,
        kind: DiagnosticKind::Preview,
        scope: DiagnosticScope::Stack,
        scale: DiagnosticScale::Linear,
        width: size[0],
        height: size[1],
        min: range[0],
        max: range[1],
        pixels: Arc::from(pixels),
        folded,
    }
}

#[test]
fn physical_intervals_reject_display_range_changes_but_find_real_equal_byte_changes() {
    let extent = [900, 600];
    let first = packet(1, 1, [0.0, 255.0], [2, 1], vec![100, 100]);
    // Physical100 lies in both bins, despite bytes100 and50 looking different.
    let rescaled = packet(2, 2, [0.0, 510.0], [2, 1], vec![50, 50]);
    let mut field = RevisionField::default();
    field.observe(&first, extent);
    assert!(field.latest().is_none());
    field.observe(&rescaled, extent);
    let revision = field.latest().unwrap();
    assert_eq!(revision.changed_samples, 0);
    assert_eq!(revision.signed_dn, [0.0, 0.0]);
    assert_ne!(
        first.pixels, rescaled.pixels,
        "raw-byte subtraction must really fail this control"
    );

    let shifted = packet(3, 3, [10.0, 520.0], [2, 1], vec![50, 50]);
    field.observe(&shifted, extent);
    let revision = field.latest().unwrap();
    assert_eq!(rescaled.pixels, shifted.pixels);
    for value in revision.signed_dn.iter().chain(&revision.range_dn) {
        conservative(*value, 8.0);
    }
    assert_eq!(revision.changed_samples, 2);
    assert_eq!((revision.from, revision.to), (2, 3));
    assert_eq!((revision.from_frame, revision.to_frame), (4, 5));
    assert_eq!(field.history().len(), 2);
}

#[test]
fn touching_bins_are_unresolved_and_flat_ranges_preserve_exact_signs() {
    let first = packet(1, 1, [0.0, 255.0], [3, 1], vec![100, 100, 100]);
    let next = packet(2, 2, [0.0, 255.0], [3, 1], vec![101, 102, 98]);
    let mut field = RevisionField::default();
    field.observe(&first, [90, 60]);
    field.observe(&next, [90, 60]);
    let revision = field.latest().unwrap();
    assert_eq!(revision.signed_dn[0], 0.0);
    conservative(revision.signed_dn[1], 1.0);
    conservative(revision.signed_dn[2], -1.0);
    assert_eq!(field.latest().unwrap().changed_samples, 2);
    conservative(revision.range_dn[0], -1.0);
    conservative(revision.range_dn[1], 1.0);
    assert_eq!(separation([99.5, 100.5], [100.0, 102.0]), Some(0.0));
    assert_eq!(separation([100.0, 100.0], [100.0, 100.0]), Some(0.0));
    assert_eq!(separation([100.0, 100.0], [98.0, 98.0]), Some(-2.0));

    let mut flat = RevisionField::default();
    flat.observe(&packet(1, 1, [100.0, 100.0], [1, 1], vec![0]), [5, 5]);
    flat.observe(&packet(2, 2, [100.0, 100.0], [1, 1], vec![255]), [5, 5]);
    assert_eq!(flat.latest().unwrap().signed_dn, [0.0]);
    flat.observe(&packet(3, 3, [97.0, 97.0], [1, 1], vec![0]), [5, 5]);
    assert_eq!(flat.latest().unwrap().signed_dn, [-3.0]);
}

#[test]
fn actual_f32_quantization_near_half_bins_cannot_turn_constant_physical_signal_into_change() {
    let mut field = RevisionField::default();
    let mut codes = std::collections::BTreeSet::new();
    for index in 0..81 {
        let minimum = (index as f32 - 40.0) * 0.000_01;
        let maximum = 255.0 + (index % 3) as f32 * 0.000_01;
        let physical = [minimum, 100.5, maximum];
        // Execute the producer's real f32 encode path, with extrema actually
        // present in the packet. Only the middle physical sample stays fixed.
        let pixels: Vec<_> = physical
            .into_iter()
            .map(|value| {
                (((value - minimum) / (maximum - minimum)).clamp(0.0, 1.0) * 255.0).round() as u8
            })
            .collect();
        codes.insert(pixels[1]);
        field.observe(
            &packet(
                index + 1,
                index as usize + 1,
                [minimum, maximum],
                [3, 1],
                pixels,
            ),
            [9, 3],
        );
        if let Some(revision) = field.latest() {
            assert_eq!(
                revision.signed_dn[1], 0.0,
                "normalization arithmetic cannot invent a change at the fixed physical sample"
            );
        }
    }
    assert!(
        codes.len() > 1,
        "the fixture must actually cross a rounded byte boundary"
    );

    // A separately chosen f32 boundary case: subtracting this tiny minimum
    // rounds the physical middle sample back to100.5 before quantization.
    // The nominal f64 bin alone then excludes the actual producing sample.
    let minimum = 0.000_001_f32;
    let maximum = 255.0_f32;
    let code = (((100.5_f32 - minimum) / (maximum - minimum)) * 255.0).round() as u8;
    let boundary = packet(2, 2, [minimum, maximum], [3, 1], vec![0, code, 255]);
    let nominal_low = f64::from(minimum)
        + ((f64::from(code) - 0.5) / 255.0) * (f64::from(maximum) - f64::from(minimum));
    assert!(
        nominal_low > 100.5,
        "the unpadded-bin negative control must exclude the real sample"
    );
    let corrected = interval(&boundary, 1);
    assert!(corrected[0] <= 100.5 && corrected[1] >= 100.5);
    let mut boundary_field = RevisionField::default();
    boundary_field.observe(&packet(1, 1, [100.5, 100.5], [3, 1], vec![0; 3]), [9, 3]);
    boundary_field.observe(&boundary, [9, 3]);
    assert_eq!(
        boundary_field.latest().unwrap().signed_dn[1],
        0.0,
        "removing the arithmetic pad must make this control fail"
    );
}

#[test]
fn nondivisible_geometry_uses_the_same_centered_samples_and_stays_bounded() {
    let size = [131, 99];
    let first = packet(1, 1, [0.0, 255.0], size, vec![100; size[0] * size[1]]);
    let next_pixels: Vec<_> = (0..size[0] * size[1])
        .map(|index| {
            let (x, y) = (index % size[0], index / size[0]);
            if x < 57 {
                110
            } else if y < 43 {
                90
            } else {
                100
            }
        })
        .collect();
    let next = packet(2, 2, [0.0, 255.0], size, next_pixels);
    let mut field = RevisionField::default();
    field.observe(&first, [3497, 2341]);
    field.observe(&next, [3497, 2341]);
    let revision = field.latest().unwrap();
    assert_eq!((revision.width, revision.height), (63, 48));
    assert_eq!(revision.total_samples, 63 * 48);
    assert_eq!(revision.extent, [3497, 2341]);
    for y in 0..revision.height {
        for x in 0..revision.width {
            // Independent floating-point pixel-centre mapping, rather than
            // repeating the integer indexing formula from the implementation.
            let source_x = (((x as f64 + 0.5) / 63.0) * 131.0).floor() as usize;
            let source_y = (((y as f64 + 0.5) / 48.0) * 99.0).floor() as usize;
            let expected = if source_x < 57 {
                9.0
            } else if source_y < 43 {
                -9.0
            } else {
                0.0
            };
            let actual = revision.signed_dn[y * revision.width + x];
            if expected == 0.0 {
                assert_eq!(actual, 0.0);
            } else {
                conservative(actual, expected);
            }
        }
    }
    assert!(
        revision.signed_dn.iter().any(|value| *value > 8.99)
            && revision.signed_dn.iter().any(|value| *value < -8.99)
            && revision.signed_dn.contains(&0.0)
    );
    let samples = 512 * 384;
    let mut maximum = RevisionField::default();
    maximum.observe(
        &packet(1, 1, [1.0, 1.0], [512, 384], vec![0; samples]),
        [7032, 4688],
    );
    maximum.observe(
        &packet(2, 2, [2.0, 2.0], [512, 384], vec![0; samples]),
        [7032, 4688],
    );
    assert_eq!(maximum.latest().unwrap().total_samples, 64 * 48);
}

#[test]
fn skipped_prefixes_keep_real_identities_and_geometry_changes_start_a_new_scope() {
    let first = packet(10, 4, [10.0, 10.0], [2, 1], vec![0; 2]);
    let second = packet(11, 7, [20.0, 20.0], [2, 1], vec![0; 2]);
    let mut field = RevisionField::default();
    field.observe(&first, [900, 600]);
    field.observe(&second, [900, 600]);
    assert_eq!(
        (field.latest().unwrap().from, field.latest().unwrap().to),
        (4, 7)
    );
    for ignored in [
        packet(10, 8, [30.0, 30.0], [2, 1], vec![0; 2]),
        packet(12, 6, [30.0, 30.0], [2, 1], vec![0; 2]),
        packet(13, 7, [30.0, 30.0], [2, 1], vec![0; 2]),
    ] {
        field.observe(&ignored, [900, 600]);
        assert_eq!(field.latest().unwrap().sequence, 11);
    }
    for drift in 0..4 {
        let mut field = RevisionField::default();
        field.observe(&first, [900, 600]);
        field.observe(&second, [900, 600]);
        let mut changed = packet(12, 8, [30.0, 30.0], [2, 1], vec![0; 2]);
        let mut extent = [900, 600];
        match drift {
            0 => {
                changed.width = 3;
                changed.pixels = Arc::from(vec![0; 3]);
            }
            1 => {
                changed.height = 2;
                changed.pixels = Arc::from(vec![0; 4]);
            }
            2 => changed.level += 1,
            _ => extent = [600, 900],
        }
        field.observe(&changed, extent);
        assert!(field.latest().is_none() && field.history().is_empty());
        changed.sequence += 1;
        changed.folded += 1;
        changed.frame += 1;
        changed.min += 1.0;
        changed.max += 1.0;
        field.observe(&changed, extent);
        assert_eq!(
            (field.latest().unwrap().from, field.latest().unwrap().to),
            (8, 9)
        );
    }
}

#[test]
fn history_is_bounded_and_invalid_or_final_image_packets_cannot_erase_actual_work() {
    let mut field = RevisionField::default();
    for index in 0..4110 {
        field.observe(
            &packet(
                index + 1,
                index as usize + 1,
                [index as f32, index as f32],
                [1, 1],
                vec![0],
            ),
            [9, 6],
        );
        if index == 258 {
            assert_eq!(field.history().len(), 258);
            assert_eq!(
                field.history().front().unwrap().from,
                1,
                "a deep bracket must retain its first revision"
            );
        }
    }
    assert_eq!(field.history().len(), 4096);
    let oldest = field.history().front().unwrap();
    assert_eq!((oldest.from, oldest.to), (14, 15));
    let latest = field.history().back().unwrap();
    assert_eq!(
        (latest.sequence, latest.from, latest.to),
        (4110, 4109, 4110)
    );
    assert_eq!((latest.from_frame, latest.to_frame), (4111, 4112));
    assert_eq!(
        (
            latest.changed_samples,
            latest.total_samples,
            latest.range_dn
        ),
        (1, 1, [1.0, 1.0])
    );
    for defect in 0..7 {
        let mut invalid = packet(4111, 4111, [4110.0, 4110.0], [1, 1], vec![0]);
        match defect {
            0 => invalid.kind = DiagnosticKind::Reconstructed,
            1 => invalid.scale = DiagnosticScale::Log,
            2 => invalid.scope = DiagnosticScope::Frame,
            3 => invalid.min = f32::NAN,
            4 => invalid.min = 4111.0,
            5 => invalid.pixels = Arc::from([]),
            _ => invalid.width = 513,
        }
        field.observe(&invalid, [9, 6]);
        assert_eq!(field.latest().unwrap().sequence, 4110);
        assert_eq!(field.history().len(), 4096);
    }
    let invalid_extent = packet(4111, 4111, [4110.0, 4110.0], [1, 1], vec![0]);
    field.observe(&invalid_extent, [0, 6]);
    assert_eq!(field.latest().unwrap().sequence, 4110);
    assert_eq!(
        separation([-f64::from(f32::MAX); 2], [f64::from(f32::MAX); 2]),
        None
    );
    for gap in [0.1, -0.1, 1.0e-46, -1.0e-46] {
        let resolved = separation([0.0, 0.0], [gap, gap]).unwrap();
        assert!(
            f64::from(resolved).abs() <= gap.abs(),
            "conversion must never overstate resolved movement"
        );
    }
}
