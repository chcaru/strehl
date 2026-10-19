//! Independent witness for the linked filmstrip window: use odd extents and
//! an aperture that separates actual pyramid coefficients from telemetry bins.
use super::*;
use crate::pipeline::{
    DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface, PipelineProgress,
};

fn sample_packet(level: usize) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence: 1,
        frame: 0,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 3,
        height: 3,
        min: 0.0,
        max: 1.0,
        // Only the upper-left and lower-right observations were admitted.
        pixels: vec![255, 0, 0, 0, 0, 0, 0, 0, 255].into(),
        folded: 1,
    }
}

fn input(progress: &PipelineProgress) -> Input<'_> {
    Input {
        progress,
        frame_count: 3,
        selected: 0,
        epoch: 1,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        inspected_pair: None,
        output_size: None,
    }
}

#[test]
fn linked_window_counts_actual_odd_pyramid_locations_not_uniform_telemetry_bins() {
    let progress = PipelineProgress::default();
    let mut archive = AdmissionArchive::default();
    archive.ingest(&sample_packet(2), [9, 9]);
    assert_eq!(archive.cells(2, 0).unwrap().1.len(), 9);
    let mut strip = CaptureParticipation::default();
    // REDUCE twice gives coefficient centres at source pixels 0,4,8.
    // At level 2 each axis therefore has UV centres 0.5/9, 4.5/9, 8.5/9.
    // Uniform 3x3 telemetry-bin centres (1/6,1/2,5/6) are different.
    let cases = [
        (Rect::from_min_max(Pos2::ZERO, egui::pos2(0.1, 0.1)), 1, 1),
        (
            Rect::from_min_max(egui::pos2(0.15, 0.15), egui::pos2(0.18, 0.18)),
            0,
            0,
        ),
        (
            Rect::from_min_max(egui::pos2(0.9, 0.9), egui::pos2(1.0, 1.0)),
            1,
            1,
        ),
        (
            Rect::from_min_max(egui::pos2(0.48, 0.04), egui::pos2(0.52, 0.07)),
            1,
            0,
        ),
    ];
    for (aperture, observed, admitted) in cases {
        strip.update(&input(&progress), &archive, 2, aperture, 1060.0, HEIGHT);
        let evidence = &strip.evidence[&0];
        assert_eq!(
            evidence.scene,
            Area {
                observed: 9,
                admitted: 2
            }
        );
        assert_eq!(
            evidence.window,
            Area { observed, admitted },
            "linked aperture {aperture:?} must count the coefficients drawn on the image"
        );
        assert!(
            !strip.evidence.contains_key(&1),
            "missing capture stays unobserved"
        );
    }
}

#[test]
fn impossible_pyramid_lattice_retains_packet_counts_but_cannot_claim_window_samples() {
    let progress = PipelineProgress::default();
    let mut archive = AdmissionArchive::default();
    // At level 4 a 9x9 plane has only one coefficient per axis, so a 3x3
    // packet cannot establish spatial positions even though its bits are real.
    archive.ingest(&sample_packet(4), [9, 9]);
    assert_eq!(archive.cells(4, 0).unwrap().1.len(), 9);
    let mut strip = CaptureParticipation::default();
    strip.update(
        &input(&progress),
        &archive,
        4,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        1060.0,
        HEIGHT,
    );
    let evidence = &strip.evidence[&0];
    assert_eq!(
        evidence.scene,
        Area {
            observed: 9,
            admitted: 2
        }
    );
    assert_eq!(evidence.window.fraction(), None);
    assert_eq!(evidence.window.label(), "—");
}

#[test]
fn current_analysis_extent_must_match_before_the_window_claims_a_photo_region() {
    let mut progress = PipelineProgress::default();
    progress.analysis_size = Some([9, 9]);
    let mut archive = AdmissionArchive::default();
    archive.ingest(&sample_packet(2), [9, 9]);
    let mut strip = CaptureParticipation::default();
    let region = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.1, 0.1));
    strip.update(&input(&progress), &archive, 2, region, 1060.0, HEIGHT);
    assert_eq!(
        strip.evidence[&0].window,
        Area {
            observed: 1,
            admitted: 1
        }
    );
    // Same aspect ratio, different analysis domain. A visual aspect match
    // cannot certify retained old sample coordinates on this photograph.
    progress.analysis_size = Some([18, 18]);
    strip.update(&input(&progress), &archive, 2, region, 1060.0, HEIGHT);
    assert_eq!(strip.evidence[&0].window, Area::default());
    assert_eq!(
        strip.evidence[&0].scene,
        Area {
            observed: 9,
            admitted: 2
        }
    );
    progress.analysis_size = Some([9, 9]);
    strip.update(&input(&progress), &archive, 2, region, 1060.0, HEIGHT);
    assert_eq!(
        strip.evidence[&0].window,
        Area {
            observed: 1,
            admitted: 1
        }
    );
}
