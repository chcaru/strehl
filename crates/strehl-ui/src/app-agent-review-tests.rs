//! Independent checks vary document identity, spatial arrangement, and edits.
//! No user catalog, capture directory, or full RAW render is modified.
use super::*;
use crate::agent_interface::{AgentRequest, Annotation, IssueKind};
use strehl_edit::{
    Adjustments, DevelopmentRecipe, ImageOrigin, LinearImage, RegionAdjustment, SourceRange,
};

fn image() -> LinearImage {
    LinearImage {
        width: 16,
        height: 12,
        pixels: vec![0.2; 16 * 12 * 3],
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}
fn app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default(); // In-memory catalog; never save the real one.
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        image: Arc::new(image()),
        preview: Arc::new(image()),
        recipe: Default::default(),
        source: PathBuf::from("unopened-test-master.tiff"),
        warnings: Vec::new(),
    });
    let path = PathBuf::from("unopened-test-result.tiff");
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path);
    app.result_viewer.source_size = [16, 12];
    app
}
fn region() -> Region {
    Region::Rectangle {
        min: [0.0, 0.0],
        max: [1.0, 0.5],
    }
}

#[test]
fn human_adjustment_invalidates_an_agents_previously_observed_revision() {
    let mut app = app();
    app.sync_agent_revision();
    let observed = app.agent.revision;
    let request = AgentRequest {
        expected_revision: Some(observed),
        command: AgentCommand::SetSettings {
            patch: serde_json::from_value(json!({"pyramid_gate":3.0})).unwrap(),
        },
    };
    assert!(request.check_revision(observed).is_ok());
    app.sync_agent_revision();
    assert_eq!(
        app.agent.revision, observed,
        "A stable workspace must not invalidate requests"
    );
    app.controls.exposure = Some(1.5); // Human moved an unrelated control.
    app.sync_agent_revision();
    assert!(app.agent.revision > observed);
    assert!(request.check_revision(app.agent.revision).is_err());
}

#[test]
fn annotating_an_existing_region_preserves_its_tone_and_source_repair() {
    let mut app = app();
    let adjustments = Adjustments {
        exposure: -1.25,
        ..Default::default()
    };
    let original = RegionAdjustment {
        id: "edge".into(),
        name: "Original".into(),
        note: "Original note".into(),
        shape: region(),
        feather: 0.75,
        enabled: false,
        adjustments,
        source_range: Some(SourceRange { first: 3, last: 7 }),
    };
    app.editor.recipe.regions.push(original.clone());
    app.apply_agent_command(AgentCommand::Annotate {
        annotation: Annotation {
            id: "edge".into(),
            label: "Revised issue".into(),
            kind: IssueKind::BrightSpot,
            region: Region::Ellipse {
                center: [0.5, 0.5],
                radius: [0.2, 0.1],
            },
            note: "Inspect the capture".into(),
        },
    })
    .unwrap();
    assert_eq!(app.editor.recipe.regions.len(), 1);
    let updated = &app.editor.recipe.regions[0];
    assert_eq!(updated.adjustments, original.adjustments);
    assert_eq!(updated.source_range, original.source_range);
    assert_eq!(updated.feather, original.feather);
    assert_eq!(updated.enabled, original.enabled);
    assert_ne!(
        updated.shape, original.shape,
        "The requested shape actually changed"
    );
    assert!(app.editor.undo());
    assert_eq!(app.editor.recipe.regions[0], original);
    assert!(app.editor.redo());
    assert_eq!(app.editor.recipe.regions[0].name, "Revised issue");
}

#[test]
fn invalid_development_never_partially_changes_the_open_recipe() {
    let mut app = app();
    let before = app.editor.recipe.clone();
    let mut invalid = before.clone();
    invalid.global.exposure = 99.0;
    assert!(
        app.apply_agent_command(AgentCommand::SetDevelop { recipe: invalid })
            .is_err()
    );
    assert_eq!(app.editor.recipe, before);
    assert!(
        !app.editor.can_undo(),
        "Rejected edits must not enter the undo journal"
    );
}

#[test]
fn spatial_probe_distinguishes_contribution_areas_missing_evidence_and_zero_admission() {
    use crate::pipeline::DiagnosticScale;
    let mut archive = crate::process_provenance::AdmissionArchive::default();
    for (frame, upper) in [(3, true), (9, false)] {
        archive.ingest(
            &crate::pipeline::DiagnosticSurface {
                sequence: frame as u64 + 1,
                frame,
                level: 0,
                kind: DiagnosticKind::GateSupport,
                scope: DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width: 4,
                height: 4,
                min: 0.0,
                max: 1.0,
                pixels: (0..16)
                    .map(|i| if (i < 8) == upper { 255 } else { 0 })
                    .collect::<Vec<_>>()
                    .into(),
                folded: 1,
            },
            [4, 4],
        );
    }
    assert_eq!(
        archive.len(),
        2,
        "The fixture must retain two distinct source masks"
    );
    let top = probe_region(&archive, &region(), 2, true);
    assert_eq!(top["sources"][0]["frame"], 3);
    assert_eq!(top["sources"][0]["levels"][0]["admitted"], 8);
    assert_eq!(top["sources"][1]["levels"][0]["admitted"], 0);
    assert_eq!(top["sources"][1]["levels"][0]["observed"], 8);
    let bottom = probe_region(
        &archive,
        &Region::Rectangle {
            min: [0.0, 0.5],
            max: [1.0, 1.0],
        },
        1,
        true,
    );
    assert_eq!(bottom["sources"].as_array().unwrap().len(), 1);
    assert_eq!(
        bottom["sources"][0]["frame"], 9,
        "Moving the region must change the leading source"
    );
    let unavailable = probe_region(&archive, &region(), 2, false);
    assert_eq!(unavailable["available"], false);
    assert!(
        unavailable.get("sources").is_none(),
        "Uncertified coordinates must not fabricate attribution"
    );
}

#[test]
fn crop_preserves_global_edit_coordinates_and_changes_only_the_intended_half() {
    let image = image();
    let mut recipe = DevelopmentRecipe::default();
    let adjustments = Adjustments {
        exposure: 1.0,
        ..Default::default()
    };
    recipe.regions.push(RegionAdjustment {
        id: "right".into(),
        name: "Right".into(),
        note: String::new(),
        shape: Region::Rectangle {
            min: [0.5, 0.0],
            max: [1.0, 1.0],
        },
        feather: 0.0,
        enabled: true,
        adjustments,
        source_range: None,
    });
    let full = image.render_sdr8(&recipe).unwrap();
    let (width, height, crop) = image
        .render_region_sdr8(&recipe, [0.5, 0.0], [1.0, 1.0], 64)
        .unwrap();
    assert_eq!((width, height), (8, 12));
    for y in 0..12 {
        assert_eq!(
            &crop[y * 8 * 3..(y + 1) * 8 * 3],
            &full[(y * 16 + 8) * 3..(y + 1) * 16 * 3]
        );
    }
    let neutral = image.render_sdr8(&DevelopmentRecipe::default()).unwrap();
    assert_eq!(
        &full[..8 * 3],
        &neutral[..8 * 3],
        "Unedited control must remain unchanged"
    );
    assert_ne!(
        &full[8 * 3..16 * 3],
        &neutral[8 * 3..16 * 3],
        "The selected half must actually be edited"
    );
}

#[test]
fn camera_source_crop_is_refused_instead_of_claiming_unavailable_registration() {
    let mut app = app();
    app.stack = Some(StackScan {
        directory: PathBuf::from("unused"),
        frames: vec![jobs::FrameFile {
            path: PathBuf::from("never-decoded.ARW"),
            bytes: 1,
        }],
        total_bytes: 1,
    });
    let result = app.agent_read_task(AgentCommand::Preview {
        target: PreviewTarget::Source { frame: 0 },
        region: Some(region()),
        max_side: 256,
    });
    assert!(
        result.is_err(),
        "Do not crop camera coordinates using output coordinates"
    );
}

#[test]
fn same_sized_photographs_cannot_reuse_each_others_diagnostics_or_edits() {
    let mut app = app();
    assert!(app.agent_photo_is_current());
    app.result = Some(PathBuf::from("different-photograph.tiff"));
    assert!(!app.agent_photo_is_current());
    assert!(
        app.agent_read_task(AgentCommand::Preview {
            target: PreviewTarget::Final,
            region: None,
            max_side: 128,
        })
        .is_err()
    );
    assert!(
        app.apply_agent_command(AgentCommand::SetDevelop {
            recipe: DevelopmentRecipe::default(),
        })
        .is_err()
    );
    assert_eq!(app.agent_snapshot()["photo_ready"], false);
}

#[test]
fn direct_handler_rejects_bad_setting_types_without_panicking_or_mutating() {
    let mut app = app();
    let before = app.controls.workers;
    assert!(
        app.apply_agent_command(AgentCommand::SetSettings {
            patch: serde_json::from_value(json!({"workers":"unbounded"})).unwrap(),
        })
        .is_err()
    );
    assert_eq!(app.controls.workers, before);
}

#[test]
fn before_preview_matches_the_human_view_without_changing_export_recipe() {
    let mut app = app();
    let preview = |app: &StrehlApp| {
        let task = app
            .agent_read_task(AgentCommand::Preview {
                target: PreviewTarget::Final,
                region: None,
                max_side: 64,
            })
            .unwrap();
        task.receiver
            .recv_timeout(Duration::from_secs(3))
            .unwrap()
            .unwrap()
    };
    let original = preview(&app).image.unwrap().data;
    app.editor.recipe.global.exposure = 1.0;
    let adjusted = preview(&app).image.unwrap().data;
    assert_ne!(
        original, adjusted,
        "The edit must actually change the image"
    );
    app.sync_agent_revision();
    let edited_revision = app.agent.revision;
    app.editor.before = true;
    app.sync_agent_revision();
    assert!(app.agent.revision > edited_revision);
    let before = preview(&app);
    assert_eq!(before.image.unwrap().data, original);
    assert_eq!(before.data["preview"]["before_preview"], true);
    assert_eq!(app.agent_snapshot()["before_preview"], true);
    assert_eq!(
        app.editor.recipe.global.exposure, 1.0,
        "Before must not erase the export recipe"
    );
    let task = app
        .agent_read_task(AgentCommand::Probe {
            region: region(),
            max_sources: 2,
        })
        .unwrap();
    let probe = task
        .receiver
        .recv_timeout(Duration::from_secs(3))
        .unwrap()
        .unwrap();
    let luminance = probe.data["pixels"]["mean_luminance"].as_f64().unwrap();
    assert!((luminance - 0.2).abs() < 1e-6);
}

#[test]
fn agent_project_edits_enter_the_humans_shared_undo_journal() {
    let mut app = app();
    let context = egui::Context::default();
    let id = app
        .apply_agent_command(AgentCommand::CreateProject {
            name: "Before rename".into(),
            parent_id: None,
        })
        .unwrap()["id"]
        .as_u64()
        .unwrap();
    app.observe_edits(&context);
    app.apply_agent_command(AgentCommand::RenameNode {
        id,
        name: "After rename".into(),
    })
    .unwrap();
    app.observe_edits(&context);
    assert_eq!(app.catalog.node(id).unwrap().name, "After rename");
    app.apply_agent_command(AgentCommand::Undo {}).unwrap();
    assert_eq!(app.catalog.node(id).unwrap().name, "Before rename");
    app.apply_agent_command(AgentCommand::Undo {}).unwrap();
    assert!(app.catalog.node(id).is_none());
    app.apply_agent_command(AgentCommand::Redo {}).unwrap();
    assert_eq!(app.catalog.node(id).unwrap().name, "Before rename");
}

#[test]
fn agent_view_undo_leaves_the_preceding_exposure_edit_intact() {
    let mut app = app();
    let context = egui::Context::default();
    let mut recipe = app.editor.recipe.clone();
    recipe.global.exposure = 1.25;
    app.apply_agent_command(AgentCommand::SetDevelop { recipe })
        .unwrap();
    app.observe_edits(&context);
    app.apply_agent_command(AgentCommand::SetView {
        center: [0.6, 0.35],
        zoom: 3.0,
    })
    .unwrap();
    app.observe_edits(&context);
    assert!(
        app.process_space.can_undo(),
        "The view change must produce its own undo entry"
    );
    app.apply_agent_command(AgentCommand::Undo {}).unwrap();
    assert_eq!(app.editor.recipe.global.exposure, 1.25);
    assert!(app.process_space.can_redo());
    app.apply_agent_command(AgentCommand::Undo {}).unwrap();
    assert_eq!(app.editor.recipe.global.exposure, 0.0);
}

#[test]
fn linear_and_imported_sdr_statistics_name_different_reference_whites() {
    let mut source = image();
    let linear = region_statistics(&source, &DevelopmentRecipe::default(), &region());
    source.origin = ImageOrigin::DisplayReferred;
    let sdr = region_statistics(&source, &DevelopmentRecipe::default(), &region());
    assert_eq!(linear["reference_kind"], "sensor normalization");
    assert_eq!(sdr["reference_kind"], "imported SDR white");
    assert_ne!(linear["units"], sdr["units"]);
    assert_eq!(
        linear["above_source_reference"],
        sdr["above_source_reference"]
    );
}

#[test]
fn closing_waits_for_export_and_only_closes_after_success() {
    for succeeds in [false, true] {
        let mut app = app();
        app.editor.path = None; // No filesystem recipe writes in this state-machine fixture.
        let context = egui::Context::default();
        let (send, receive) = std::sync::mpsc::sync_channel::<()>(1);
        app.editor.exporting = Some(jobs::spawn_task("test-close-export", move |_| {
            receive.recv_timeout(Duration::from_secs(3))?;
            anyhow::ensure!(succeeds, "deliberate export failure");
            Ok(PathBuf::from("successful-test-export.tiff"))
        }));
        let mut input = egui::RawInput::default();
        input
            .viewports
            .entry(egui::ViewportId::ROOT)
            .or_default()
            .events
            .push(egui::ViewportEvent::Close);
        let output = context.run(input, |ctx| app.handle_close(ctx));
        assert!(app.close_after_export);
        assert!(
            output.viewport_output[&egui::ViewportId::ROOT]
                .commands
                .iter()
                .any(|command| matches!(command, egui::ViewportCommand::CancelClose))
        );
        send.send(()).unwrap();
        let deadline = Instant::now() + Duration::from_secs(3);
        while app.editor.exporting.is_some() {
            assert!(Instant::now() < deadline);
            app.editor.poll(&context, 128);
            std::thread::sleep(Duration::from_millis(2));
        }
        let output = context.run(egui::RawInput::default(), |ctx| app.handle_close(ctx));
        let commands = &output.viewport_output[&egui::ViewportId::ROOT].commands;
        assert_eq!(
            commands
                .iter()
                .any(|command| matches!(command, egui::ViewportCommand::Close)),
            succeeds
        );
        if !succeeds {
            assert!(
                commands
                    .iter()
                    .any(|command| matches!(command, egui::ViewportCommand::CancelClose))
            );
            assert_eq!(app.sidebar, Some(workspace::Sidebar::Edit));
            assert!(
                app.editor
                    .error
                    .as_ref()
                    .unwrap()
                    .contains("deliberate export failure")
            );
        }
    }
}
