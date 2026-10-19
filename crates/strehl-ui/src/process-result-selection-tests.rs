use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};

fn archive() -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    for (frame, pixels) in [
        (0, [255, 255, 0, 0, 0, 0]),
        (1, [0, 0, 255, 0, 0, 0]),
        (3, [0, 255, 0, 255, 0, 0]),
        (4, [0; 6]),
    ] {
        archive.ingest(
            &DiagnosticSurface {
                sequence: frame as u64 + 1,
                frame,
                level: 1,
                kind: DiagnosticKind::GateSupport,
                scope: DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width: 3,
                height: 2,
                min: 0.0,
                max: 1.0,
                pixels: pixels.to_vec().into(),
                folded: 1,
            },
            [117, 81],
        );
    }
    archive
}
fn key(archive: &AdmissionArchive, spans: Vec<SelectionSpan>) -> MaskKey {
    let evidence = archive
        .frames(1)
        .filter(|&frame| spans.iter().any(|span| span.contains(frame)))
        .map(|frame| (1, frame, archive.metadata(1, frame).unwrap()))
        .collect();
    MaskKey {
        level: 1,
        spans,
        evidence,
    }
}
fn colors(samples: &[ColoredSample], cell: [usize; 2]) -> Vec<Color32> {
    let geometry = SampleGeometry::new(
        1,
        AdmissionMeta {
            sequence: 1,
            samples: [3, 2],
            extent: [117, 81],
        },
    )
    .unwrap();
    let observed = geometry.at(cell[1] * 3 + cell[0]).unwrap();
    samples
        .iter()
        .find(|sample| sample.glyph == observed)
        .map_or_else(Vec::new, |sample| sample.colors.to_vec())
}

#[test]
fn span_union_and_overlap_keep_each_sampled_colour_without_inventing_weights() {
    let archive = archive();
    let a = SelectionSpan {
        start: 0,
        end: 1,
        id: 0,
    };
    let b = SelectionSpan {
        start: 3,
        end: 3,
        id: 1,
    };
    let image = admission_samples(&archive, &key(&archive, vec![a, b]));
    assert_eq!(image.len(), 4);
    assert_eq!(colors(&image, [0, 0]), [a.color()]);
    assert_eq!(
        colors(&image, [2, 0]),
        [a.color()],
        "the union must include the second capture's independent pixel"
    );
    let overlap = colors(&image, [1, 0]);
    assert_eq!(
        overlap.len(),
        2,
        "fixture must exercise actual overlap, not disjoint groups"
    );
    assert!(overlap.contains(&a.color()) && overlap.contains(&b.color()));
    assert_eq!(colors(&image, [0, 1]), [b.color()]);
    assert!(colors(&image, [2, 1]).is_empty());
    assert!(
        image.iter().all(|sample| sample.glyph.cell.width() < 0.02),
        "a2px lattice observation must not own the39px telemetry bin"
    );
}

#[test]
fn missing_capture_and_observed_zero_never_darkens_unmeasured_photo_pixels() {
    let archive = archive();
    let partial = SelectionSpan {
        start: 0,
        end: 2,
        id: 0,
    };
    let image = admission_samples(&archive, &key(&archive, vec![partial]));
    assert_eq!(colors(&image, [0, 0]), [partial.color()]);
    assert!(
        colors(&image, [2, 1]).is_empty(),
        "missing capture 2 cannot prove no admission at this cell"
    );
    let zero = SelectionSpan {
        start: 4,
        end: 4,
        id: 1,
    };
    let image = admission_samples(&archive, &key(&archive, vec![zero]));
    assert!(image.is_empty());
    let absent = SelectionSpan {
        start: 2,
        end: 2,
        id: 0,
    };
    assert!(admission_samples(&archive, &key(&archive, vec![absent])).is_empty());
}

#[test]
fn simultaneous_levels_keep_distinct_physical_spacing_and_only_observed_evidence() {
    let mut archive = AdmissionArchive::default();
    for level in [0, 3] {
        archive.ingest(
            &DiagnosticSurface {
                sequence: level as u64 + 1,
                frame: 0,
                level,
                kind: DiagnosticKind::GateSupport,
                scope: DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width: 3,
                height: 2,
                min: 0.0,
                max: 1.0,
                pixels: vec![255, 0, 0, 0, 0, 0].into(),
                folded: 1,
            },
            [117, 81],
        );
    }
    let selection = SelectionSpan {
        start: 0,
        end: 0,
        id: 2,
    };
    let key = MaskKey {
        level: 0,
        spans: vec![selection],
        evidence: [0, 3]
            .into_iter()
            .map(|level| (level, 0, archive.metadata(level, 0).unwrap()))
            .collect(),
    };
    let samples = admission_samples(&archive, &key);
    assert_eq!(
        samples.len(),
        2,
        "no absent intermediate level may acquire a synthetic sample"
    );
    assert_eq!(samples[0].level, 0);
    assert_eq!(samples[1].level, 3);
    assert_eq!(samples[0].spacing, 1);
    assert_eq!(samples[1].spacing, 8);
    assert!((samples[1].glyph.cell.width() / samples[0].glyph.cell.width() - 8.0).abs() < 0.001);
    assert!(
        samples
            .iter()
            .all(|sample| sample.colors == [selection.color()])
    );
}

#[test]
fn single_hover_stays_transient_but_pins_keep_a_distinct_current_trace_inside_and_outside() {
    let held = SelectionSpan {
        start: 4,
        end: 4,
        id: 0,
    };
    assert_eq!(
        effective_spans(&[held], Some(31)),
        [SelectionSpan {
            start: 31,
            end: 31,
            id: 0
        }]
    );
    let span = SelectionSpan {
        start: 4,
        end: 12,
        id: 0,
    };
    assert_eq!(
        effective_spans(&[span], Some(7)),
        [
            span,
            SelectionSpan {
                start: 7,
                end: 7,
                id: usize::MAX
            }
        ]
    );
    assert_eq!(
        effective_spans(&[span], Some(31)),
        [
            span,
            SelectionSpan {
                start: 31,
                end: 31,
                id: usize::MAX
            }
        ]
    );
    assert_eq!(effective_spans(&[span], None), [span]);
    let remaining = SelectionSpan {
        start: 31,
        end: 31,
        id: 3,
    };
    assert_eq!(
        effective_spans(&[remaining], Some(31)),
        [remaining],
        "removing the other groups must not recolour the remaining group"
    );
}
