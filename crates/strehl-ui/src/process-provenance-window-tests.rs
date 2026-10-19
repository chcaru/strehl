//! Independent rectangle oracle: inspect the original transmitted bytes, with
//! no packed-word arithmetic shared with the production implementation.
use super::*;

fn observation(
    sequence: u64,
    frame: usize,
    size: [usize; 2],
    pixels: Vec<u8>,
) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame,
        level: 2,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: size[0],
        height: size[1],
        min: 0.0,
        max: 1.0,
        pixels: pixels.into(),
        folded: 1,
    }
}

fn oracle(pixels: &[u8], width: usize, columns: [usize; 2], rows: [usize; 2]) -> (usize, usize) {
    let mut admitted = 0;
    let mut observed = 0;
    for row in pixels.chunks_exact(width).take(rows[1]).skip(rows[0]) {
        for &pixel in row.iter().take(columns[1]).skip(columns[0]) {
            observed += 1;
            admitted += usize::from(pixel == 255);
        }
    }
    (admitted, observed)
}

#[test]
fn rectangular_popcounts_match_transmitted_pixels_across_odd_rows_and_word_edges() {
    let mut saw_mixed = false;
    let mut saw_crossing = false;
    let mut saw_partial_odd_row = false;
    for width in [1, 7, 31, 63, 64, 65, 67, 127, 128] {
        let height = 5;
        let pixels: Vec<_> = (0..width * height)
            .map(|index| {
                let x = index % width;
                let y = index / width;
                if (x * 7 + y * 11) % 13 < 5 || [63, 64, 127, 128].contains(&index) {
                    255
                } else {
                    0
                }
            })
            .collect();
        let mut archive = AdmissionArchive::default();
        archive.ingest(
            &observation(1, 17, [width, height], pixels.clone()),
            [997, 613],
        );
        assert_eq!(archive.metadata(2, 17).unwrap().samples, [width, height]);
        let mut edges = vec![0, 1.min(width), width / 2, width.saturating_sub(1), width];
        edges.extend(
            [31, 32, 62, 63, 64, 65, 66, 126, 127]
                .into_iter()
                .filter(|&x| x <= width),
        );
        edges.sort_unstable();
        edges.dedup();
        for &left in &edges {
            for &right in edges.iter().filter(|&&x| x >= left) {
                for top in 0..=height {
                    for bottom in top..=height {
                        let expected = oracle(&pixels, width, [left, right], [top, bottom]);
                        assert_eq!(
                            archive.window_counts(2, 17, [left, right], [top, bottom]),
                            Some(expected),
                            "width={width}, columns={left}..{right}, rows={top}..{bottom}"
                        );
                        saw_mixed |= expected.0 > 0 && expected.0 < expected.1;
                        saw_partial_odd_row |=
                            width % 2 == 1 && left > 0 && right < width && expected.1 > 0;
                        saw_crossing |= (top..bottom).any(|row| {
                            right > left
                                && (row * width + left) / 64 != (row * width + right - 1) / 64
                        });
                    }
                }
            }
        }
    }
    assert!(
        saw_mixed && saw_crossing && saw_partial_odd_row,
        "oracle must exercise mixed evidence, internal word crossings, and partial odd-width rows"
    );
}

#[test]
fn empty_observed_zero_missing_and_invalid_ranges_remain_distinct() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&observation(1, 4, [67, 3], vec![0; 201]), [997, 613]);
    assert_eq!(archive.window_counts(2, 4, [1, 66], [0, 3]), Some((0, 195)));
    for (columns, rows) in [
        ([0, 0], [0, 3]),
        ([67, 67], [0, 3]),
        ([0, 67], [3, 3]),
        ([67, 67], [3, 3]),
    ] {
        assert_eq!(archive.window_counts(2, 4, columns, rows), Some((0, 0)));
    }
    for (columns, rows) in [
        ([9, 8], [0, 3]),
        ([0, 68], [0, 3]),
        ([68, 68], [0, 0]),
        ([0, 67], [2, 1]),
        ([0, 0], [4, 4]),
        ([0, 67], [0, 4]),
        ([usize::MAX, usize::MAX], [0, 0]),
        ([0, 0], [usize::MAX, usize::MAX]),
    ] {
        assert_eq!(archive.window_counts(2, 4, columns, rows), None);
    }
    assert_eq!(archive.window_counts(2, 5, [0, 0], [0, 0]), None);
    assert_eq!(archive.window_counts(3, 4, [0, 0], [0, 0]), None);
}

#[test]
fn replacement_updates_rectangles_without_leaking_old_words_or_other_domains() {
    let mut archive = AdmissionArchive::default();
    let positive = observation(1, 4, [65, 3], vec![255; 195]);
    archive.ingest(&positive, [997, 613]);
    archive.ingest(&observation(2, 5, [65, 3], vec![255; 195]), [997, 613]);
    let mut replacement = vec![0; 195];
    replacement[63] = 255;
    replacement[64] = 255;
    replacement[194] = 255;
    archive.ingest(&observation(3, 4, [65, 3], replacement.clone()), [997, 613]);
    assert_eq!(archive.window_counts(2, 4, [0, 65], [0, 3]), Some((3, 195)));
    for (columns, rows) in [([62, 65], [0, 2]), ([0, 2], [1, 3]), ([64, 65], [0, 3])] {
        assert_eq!(
            archive.window_counts(2, 4, columns, rows),
            Some(oracle(&replacement, 65, columns, rows))
        );
    }
    archive.ingest(&positive, [997, 613]);
    assert_eq!(
        archive.window_counts(2, 4, [0, 65], [0, 3]),
        Some((3, 195)),
        "stale replacement cannot resurrect old bits"
    );
    assert_eq!(
        archive.window_counts(2, 5, [0, 65], [0, 3]),
        Some((195, 195))
    );
    archive.ingest(&observation(4, 4, [7, 2], vec![0; 14]), [999, 611]);
    assert_eq!(archive.window_counts(2, 4, [0, 7], [0, 2]), Some((0, 14)));
    assert_eq!(
        archive.window_counts(2, 5, [0, 7], [0, 2]),
        None,
        "new level lattice cannot retain old capture evidence"
    );
    assert_eq!(archive.window_counts(2, 4, [0, 65], [0, 3]), None);
}
