use super::*;
use crate::pipeline::{FrameObservation, LOG_GAP};
fn context(index: usize, offset: usize, count: usize) -> String {
    format!(
        "STREHL_UI_VIEW {}\n",
        serde_json::json!({"schema":"strehl.ui-view-progress.v1",
        "index":index,"count":2,"name":if index==0 {"Underside"} else {"Top green"},
        "source_offset":offset,"source_count":count,"parent_total":5})
    )
}
#[test]
fn session_view_progress_unequal_children_reset_all_observations_and_map_sources() {
    let mut p = PipelineProgress::default();
    p.ingest(&context(0, 0, 2));
    p.ingest("STREHL_UI_PROGRESS event=frame-started index=1 total=2\n");
    assert_eq!(p.parent_frame(p.processing_frame.unwrap()), Some(1));
    p.ingest("STREHL_UI_PROGRESS event=frame-finished index=1 processed=2 accepted=2 total=2\n");
    p.plane_size = Some([99, 77]);
    p.analysis_origin = Some([3, 4]);
    p.reference_frame = Some(1);
    p.alignment_plane_observations.insert(1);
    p.ingest("STREHL_UI_PROGRESS event=stage name=render total=2\n");
    let epoch = p.diagnostic_epoch;
    p.ingest(&context(1, 2, 3));
    assert_eq!(p.stage, Stage::Preparing);
    assert_eq!(p.frames_total, Some(3));
    assert!(p.frames_processed.is_none() && p.reference_frame.is_none());
    assert!(p.frame_observations.is_empty() && p.alignment_plane_observations.is_empty());
    assert!(p.plane_size.is_none() && p.analysis_origin.is_none());
    assert!(p.diagnostic_epoch > epoch);
    assert_eq!(p.events.len(), 1);
    p.ingest("STREHL_UI_PROGRESS event=frame-started index=1 total=3\n");
    assert_eq!(
        p.frame_observations.get(&1),
        Some(&FrameObservation::Started)
    );
    assert_eq!(p.parent_frame(1), Some(3));
    assert_eq!(p.parent_pair([0, 2]), Some([2, 4]));
    assert_eq!(p.view.as_ref().unwrap().local_frame(3), Some(1));
    assert_eq!(p.parent_frame(3), None);
    assert_eq!(p.view.as_ref().unwrap().local_frame(1), None);
    p.ingest("frames: 5 from parent\nSTREHL_UI_PROGRESS event=frame-started index=4 total=5\n");
    assert_eq!(p.frames_total, Some(3));
    assert_eq!(p.processing_frame, Some(1));
}
#[test]
fn session_view_progress_rejects_malformed_backward_and_overlapping_scopes() {
    for bad in [
        context(1, 1, 3),
        context(1, 2, 4),
        context(0, 0, 2),
        "STREHL_UI_VIEW {broken}\n".into(),
    ] {
        let mut p = PipelineProgress::default();
        p.ingest(&context(0, 0, 2));
        p.ingest(&bad);
        p.ingest("STREHL_UI_PROGRESS event=frame-started index=1 total=2\n");
        assert!(p.view_observations_missing);
        assert!(p.processing_frame.is_none());
    }
}
#[test]
fn session_view_progress_gap_cannot_relabel_second_child_as_first() {
    let mut p = PipelineProgress::default();
    p.ingest(&context(0, 0, 2));
    p.ingest("STREHL_UI_PROGRESS event=frame-started index=1 total=2\n");
    p.ingest(&format!(
        "{LOG_GAP}truncated\nSTREHL_UI_PROGRESS event=frame-started index=0 total=2\n"
    ));
    assert!(p.view_observations_missing && p.processing_frame.is_none());
    p.ingest(&context(1, 2, 3));
    p.ingest("STREHL_UI_PROGRESS event=frame-started index=0 total=3\n");
    assert!(!p.view_observations_missing);
    assert_eq!(p.parent_frame(0), Some(2));
}
#[test]
fn session_view_progress_ordinary_events_keep_their_original_axis() {
    let mut p = PipelineProgress::default();
    p.ingest("STREHL_UI_PROGRESS event=frame-started index=1 total=3\n");
    assert!(p.view.is_none());
    assert_eq!(p.parent_frame(1), Some(1));
    assert_eq!(p.parent_pair([0, 2]), Some([0, 2]));
    assert_eq!(p.frames_total, Some(3));
    assert_eq!(p.processing_frame, Some(1));
}

#[test]
fn session_view_progress_missing_initial_context_is_not_ordinary_evidence() {
    let mut p = PipelineProgress::default();
    p.expect_view_progress();
    p.ingest("STREHL_UI_PROGRESS event=frame-started index=0 total=3\n");
    assert!(p.processing_frame.is_none());
    p.ingest(&context(1, 2, 3));
    p.ingest("STREHL_UI_PROGRESS event=frame-started index=0 total=3\n");
    assert_eq!(p.parent_frame(p.processing_frame.unwrap()), Some(2));
}
