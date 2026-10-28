//! Pass navigation uses the actual process canvas and global frame indices.
use super::*;
use crate::session_workspace::CaptureGroup;

fn paint(
    space: &mut ProcessSpace,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> (egui::FullOutput, Response) {
    let mut response = Response::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1060.0, 720.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                response = space.show(
                    ui,
                    Input {
                        epoch: 1,
                        progress: &PipelineProgress::default(),
                        frame_count: 6,
                        selected: 0,
                        inspected_pair: None,
                        photos: &[],
                        inspection_photos: &[],
                        surfaces: &[],
                        output: None,
                        output_size: None,
                    },
                );
            });
        },
    );
    (output, response)
}

#[test]
fn session_timeline_paints_passes_and_selects_the_clicked_pass_in_global_coordinates() {
    let mut space = ProcessSpace::default();
    space.set_capture_groups(&[
        CaptureGroup {
            pass_index: 0,
            name: "Continued".into(),
            range: 0..4,
            segment_ends: vec![2, 4],
            primary: false,
        },
        CaptureGroup {
            pass_index: 1,
            name: "Repeat".into(),
            range: 4..6,
            segment_ends: vec![6],
            primary: true,
        },
    ]);
    let ctx = egui::Context::default();
    let (first, _) = paint(&mut space, &ctx, 1.0, Vec::new());
    let label = first
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text().contains("★ Repeat") => {
                Some(text.visual_bounding_rect())
            }
            _ => None,
        })
        .expect("the primary pass must be visible above the timeline");
    let at = label.center();
    let event = |pressed| {
        vec![
            egui::Event::PointerMoved(at),
            egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed,
                modifiers: egui::Modifiers::NONE,
            },
        ]
    };
    let _ = paint(&mut space, &ctx, 1.1, event(true));
    let (_, response) = paint(&mut space, &ctx, 1.2, event(false));
    assert_eq!(response.selected, Some(5));
    assert_eq!(space.inspection_frame(), Some(5));
}

#[test]
fn session_timeline_groups_survive_epoch_transition_but_clear_for_an_ordinary_stack() {
    let mut space = ProcessSpace::default();
    let group = CaptureGroup {
        pass_index: 0,
        name: "Only pass".into(),
        range: 0..6,
        segment_ends: vec![6],
        primary: false,
    };
    space.set_capture_groups(std::slice::from_ref(&group));
    let ctx = egui::Context::default();
    let _ = paint(&mut space, &ctx, 1.0, Vec::new());
    assert_eq!(space.capture_groups, vec![group]);
    space.set_capture_groups(&[]);
    let _ = paint(&mut space, &ctx, 2.0, Vec::new());
    assert!(space.capture_groups.is_empty());
}

fn saved_summary(root: &std::path::Path) -> crate::session_workspace::SessionSummary {
    use crate::session_workspace::{PassSpec, SessionDraft, SessionMode};
    let first = root.join("first");
    let second = root.join("second");
    let mut draft = SessionDraft::from_directory(first.clone());
    draft.manifest.mode = SessionMode::Layers;
    draft.manifest.primary_pass = Some(1);
    draft.manifest.passes[0].name = "Wide pass".into();
    draft.manifest.passes.push(PassSpec {
        name: "Primary pass".into(),
        directories: vec![second.clone()],
    });
    for i in 0..6 {
        draft
            .sources
            .push(crate::workspace_history::SourceIdentity {
                path: if i < 4 { &first } else { &second }.join(format!("{i}.ARW")),
                bytes: 1,
                modified_ns: Some(1),
            });
    }
    std::fs::create_dir_all(root.join("session-output")).unwrap();
    std::fs::write(
        root.join("session-recipe.json"),
        serde_json::to_vec(&draft).unwrap(),
    )
    .unwrap();
    std::fs::write(root.join("session-output/completed.json"), br#"{"schema":"strehl.session-completion.v1","frames":6,"passes":2,"outputs":2,"primary_pass":1}"#).unwrap();
    std::fs::write(root.join("session-output/alignment.json"), br#"{"report":{"frames":6,"measured_edges":9,"anchor_component_cycle_rank":4,"passes":[{"pass_index":0,"frames":4,"placed":4,"refused":0},{"pass_index":1,"frames":2,"placed":2,"refused":0}]}}"#).unwrap();
    crate::session_workspace::SessionSummary::load(root, &draft)
}

#[test]
fn session_completed_canvas_uses_saved_counts_and_omits_ordinary_pending_instruments() {
    let root = tempfile::tempdir().unwrap();
    let summary = saved_summary(root.path());
    assert!(summary.completed && summary.report_error.is_none());
    assert_eq!(summary.geometry.as_ref().unwrap().measured_edges, 9);
    let mut space = ProcessSpace::default();
    space.set_session_summary(Some(&summary));
    space.set_output_path(Some(&summary.outputs[1]));
    let ctx = egui::Context::default();
    let texture = ctx.load_texture(
        "saved-layer",
        egui::ColorImage::filled([32, 24], egui::Color32::WHITE),
        Default::default(),
    );
    // Deliberately inconsistent ordinary last-layer counters must not leak.
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Complete;
    progress.frames_total = Some(6);
    progress.frames_processed = Some(2);
    progress.frames_accepted = Some(2);
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1060.0, 720.0),
            )),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                space.show(
                    ui,
                    Input {
                        epoch: 1,
                        progress: &progress,
                        frame_count: 6,
                        selected: 4,
                        inspected_pair: None,
                        photos: &[],
                        inspection_photos: &[],
                        surfaces: &[],
                        output: Some(&texture),
                        output_size: Some([7008, 4672]),
                    },
                );
            });
        },
    );
    let labels = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.galley.text()),
            _ => None,
        })
        .collect::<Vec<_>>()
        .join("\n");
    for text in [
        "SESSION SAVED",
        "2 passes · 6 captures",
        "6 / 6 captures placed",
        "9 measured pair fits",
        "Layer 2 of 2 · Primary pass · 2 captures",
        "admission overlays unavailable",
    ] {
        assert!(labels.contains(text), "missing {text}: {labels}");
    }
    for text in [
        "awaiting observation",
        "Scale plan pending",
        "frames processed",
        "accepted into stack",
        "ADMITTED SAMPLES",
    ] {
        assert!(
            !labels.contains(text),
            "ordinary placeholder leaked: {text}"
        );
    }
    assert!(!space.session_contacts.is_empty());
    space.set_session_summary(None);
    let _ = paint(&mut space, &ctx, 2.0, Vec::new());
    assert!(space.session_contacts.is_empty());
}

#[test]
fn session_saved_summary_refuses_mismatched_geometry_counts_without_inventing_zero_fits() {
    let root = tempfile::tempdir().unwrap();
    let valid = saved_summary(root.path());
    let draft: crate::session_workspace::SessionDraft =
        serde_json::from_slice(&std::fs::read(root.path().join("session-recipe.json")).unwrap())
            .unwrap();
    std::fs::write(root.path().join("session-output/alignment.json"), br#"{"report":{"frames":6,"measured_edges":999,"anchor_component_cycle_rank":4,"passes":[{"pass_index":0,"frames":4,"placed":4,"refused":0},{"pass_index":1,"frames":2,"placed":3,"refused":0}]}}"#).unwrap();
    let invalid = crate::session_workspace::SessionSummary::load(root.path(), &draft);
    assert!(invalid.completed && invalid.geometry.is_none() && invalid.report_error.is_some());
    assert!(invalid.passes.iter().all(|pass| pass.placed.is_none()));
    assert_eq!(invalid.frames, valid.frames);
    // A modified next-render draft must not rename the immutable saved result.
    let mut changed = draft;
    changed.manifest.passes[0].name = "Next render only".into();
    let saved = crate::session_workspace::SessionSummary::load(root.path(), &changed);
    assert_eq!(saved.passes[0].name, "Wide pass");
}
