use super::*;

#[test]
fn camera_metadata_timeline_action_uses_selected_capture_without_changing_exploration() {
    for complete in [false, true] {
        let ctx = egui::Context::default();
        let mut space = ProcessSpace::default();
        let mut progress = PipelineProgress::default();
        if complete {
            progress.mark_complete();
        }
        let data = Input {
            selected: 7,
            ..input(&progress)
        };
        let (_, out) = draw(&mut space, &ctx, data, 0.0, vec![]);
        let at = text(&out, "Camera metadata");
        let inspection = space.inspection_frame();
        let response = click(&mut space, &ctx, data, 0.1, at);
        assert_eq!(response.camera_metadata, Some(7));
        assert!(response.selected.is_none() && response.compare_pair.is_none());
        assert!(!response.return_live && !response.open_sources && !response.exit_space);
        assert_eq!(space.inspection_frame(), inspection);
    }
}

#[test]
fn camera_metadata_timeline_action_refuses_empty_capture() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let progress = PipelineProgress::default();
    let data = Input {
        frame_count: 0,
        ..input(&progress)
    };
    let (_, out) = draw(&mut space, &ctx, data, 0.0, vec![]);
    let response = click(&mut space, &ctx, data, 0.1, text(&out, "Camera metadata"));
    assert_eq!(response.camera_metadata, None);
}
