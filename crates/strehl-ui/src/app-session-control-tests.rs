//! The real application command handler composes imported catalog identities.
use super::*;
use crate::agent_interface::CatalogSessionPass;
use crate::session_workspace::SessionMode;

fn fixture() -> (tempfile::TempDir, StrehlApp, u64, Vec<u64>) {
    let root = tempfile::tempdir().unwrap();
    let mut app = StrehlApp::from_launch(
        4096,
        LaunchOptions {
            catalog: Some(root.path().join("projects.json")),
            ..Default::default()
        },
    );
    app.output = root.path().join("outputs");
    let project = app.catalog.create_project("Session controls").unwrap();
    let mut ids = Vec::new();
    for segment in 0..3 {
        let directory = root.path().join(format!("source-{segment}"));
        std::fs::create_dir(&directory).unwrap();
        let directory = std::fs::canonicalize(directory).unwrap();
        let mut frames = Vec::new();
        for index in 0..2 {
            let path = directory.join(format!("capture-{index}.ARW"));
            std::fs::write(&path, [segment, index, 42]).unwrap();
            frames.push(jobs::FrameFile { path, bytes: 3 });
        }
        let scan = StackScan {
            directory,
            frames,
            total_bytes: 6,
        };
        ids.push(
            app.catalog
                .create_stack(
                    project,
                    &format!("Original {segment}"),
                    crate::workspace_history::StackDraft::from_scan(
                        &scan,
                        jobs::RenderSettings::default(),
                        None,
                        None,
                        2,
                    ),
                )
                .unwrap(),
        );
    }
    (root, app, project, ids)
}

fn command(project: u64, ids: &[u64]) -> AgentCommand {
    AgentCommand::CreateSession {
        name: "Two passes, three folders".into(),
        passes: vec![
            CatalogSessionPass {
                name: "Continued".into(),
                stack_ids: ids[..2].to_vec(),
            },
            CatalogSessionPass {
                name: "Repeat".into(),
                stack_ids: ids[2..].to_vec(),
            },
        ],
        mode: SessionMode::Layers,
        primary_pass: Some(1),
        memory_limit_gib: 12.0,
        precision_weights: false,
        contribution_maps: false,
        focus_evidence: false,
        reproducibility: false,
        original_cfa_reconstruction: false,
        parent_id: Some(project),
    }
}

#[test]
fn session_control_creates_an_explicit_session_without_mutating_original_stacks() {
    let (_root, mut app, project, ids) = fixture();
    let originals: Vec<_> = ids
        .iter()
        .map(|&id| serde_json::to_vec(app.catalog.node(id).unwrap()).unwrap())
        .collect();
    let reply = app.apply_agent_command(command(project, &ids)).unwrap();
    assert_eq!(reply["state"], "queued");
    let ctx = egui::Context::default();
    let started = Instant::now();
    while app.scan.is_some() {
        assert!(
            started.elapsed() < Duration::from_secs(5),
            "session scan did not finish"
        );
        app.poll(&ctx);
        std::thread::sleep(Duration::from_millis(5));
    }
    assert_eq!(app.stack.as_ref().unwrap().frames.len(), 6);
    assert_eq!(app.session_ui.groups.len(), 2);
    assert_eq!(app.session_ui.groups[0].range, 0..4);
    assert_eq!(app.session_ui.groups[0].segment_ends, vec![2, 4]);
    assert_eq!(app.session_ui.groups[1].range, 4..6);
    assert!(app.session_ui.groups[1].primary);
    let active = app.active_stack.unwrap();
    assert!(!ids.contains(&active));
    assert_eq!(
        app.catalog.node(active).unwrap().name,
        "Two passes, three folders"
    );
    assert_eq!(
        app.controls
            .settings
            .session
            .as_ref()
            .unwrap()
            .memory_limit_gib,
        12.0
    );
    assert_eq!(
        app.controls
            .settings
            .session
            .as_ref()
            .unwrap()
            .sources
            .len(),
        6
    );
    assert!(app.session_start_blocker().is_none());
    for (&id, before) in ids.iter().zip(originals) {
        assert_eq!(
            serde_json::to_vec(app.catalog.node(id).unwrap()).unwrap(),
            before
        );
    }
    let snapshot = app.agent_snapshot();
    assert_eq!(snapshot["session"]["primary_pass"], 1);
    assert_eq!(
        snapshot["session"]["capture_groups"][0]["segment_ends"],
        serde_json::json!([2, 4])
    );
}

#[test]
fn session_control_refuses_unknown_and_repeated_catalog_sources_before_mutation() {
    let (_root, mut app, project, ids) = fixture();
    let before = serde_json::to_vec(&app.catalog).unwrap();
    let mut repeated = ids.clone();
    repeated[2] = ids[0];
    assert!(
        app.apply_agent_command(command(project, &repeated))
            .is_err()
    );
    let mut unknown = ids;
    unknown[2] = u64::MAX;
    assert!(app.apply_agent_command(command(project, &unknown)).is_err());
    assert!(app.scan.is_none() && app.controls.settings.session.is_none());
    assert_eq!(serde_json::to_vec(&app.catalog).unwrap(), before);
}

#[test]
fn session_control_layer_outputs_retain_their_own_catalog_owner() {
    let (root, mut app, project, ids) = fixture();
    app.apply_agent_command(command(project, &ids)).unwrap();
    let imported = app
        .scan
        .take()
        .unwrap()
        .receiver
        .recv_timeout(Duration::from_secs(5))
        .unwrap()
        .unwrap();
    app.controls.settings.session.as_mut().unwrap().sources =
        crate::workspace_history::source_identities(&imported);
    app.stack = Some(imported);
    app.ensure_project_stack();
    let stack_id = app.active_stack.unwrap();
    let directory = root.path().join("completed-run");
    let output = directory.join("session-output/layer-02/photograph.tiff");
    let run = crate::workspace_history::Run {
        directory: directory.clone(),
        source: app.stack.as_ref().unwrap().directory.clone(),
        output: output.clone(),
        log: directory.join("render.log"),
        label: "Layers".into(),
        created: 1,
        status: "Saved".into(),
        frames: 6,
        sources: crate::workspace_history::source_identities(app.stack.as_ref().unwrap()),
        settings: app.controls.settings.clone(),
        exposure: None,
        gate: None,
        workers: 2,
        pinned: false,
        imported: None,
    };
    app.catalog.add_revision(stack_id, run).unwrap();
    assert_eq!(app.catalog.photo_owner(&output).stack, Some(stack_id));
    let other = directory.join("session-output/layer-01/photograph.tiff");
    assert_eq!(app.catalog.photo_owner(&other).stack, Some(stack_id));
    assert!(
        app.catalog
            .photo_owner(&directory.join("session-output/layer-03/photograph.tiff"))
            .stack
            .is_none()
    );
    assert!(
        app.catalog
            .photo_owner(&directory.join("unrelated.tiff"))
            .stack
            .is_none()
    );
}

#[test]
fn session_control_restores_ordinary_defaults_and_user_choices_with_identical_command() {
    for ordinary in [
        jobs::RenderSettings::default(),
        jobs::RenderSettings {
            binned: true,
            crop_to_coverage: true,
            frame_limit: Some(4),
            auto_exposure: true,
            pyramid_bands: Some(5),
            pyramid_exponent: Some(3.0),
            pyramid_sharpen: Some(0.4),
            resampler: jobs::Resampler::Lanczos2,
            ..Default::default()
        },
        jobs::RenderSettings {
            temporal_energy: true,
            correct_lateral_ca: false,
            confidence_map: false,
            ..Default::default()
        },
    ] {
        let (root, mut app, project, ids) = fixture();
        app.controls.settings = ordinary.clone();
        app.controls.exposure = (!ordinary.auto_exposure).then_some(-0.5);
        app.controls.gate = Some(2.5);
        app.controls.workers = 3;
        let recipe = history::Recipe::capture(&app.controls);
        let request = |controls: &Controls| jobs::RenderRequest {
            executable: "strehl-test-engine".into(),
            source: root.path().join("source-0"),
            output_parent: root.path().join("outputs"),
            exposure_ev: controls.exposure,
            pyramid_gate: controls.gate,
            worker_threads: Some(controls.workers),
            settings: controls.settings.clone(),
            retain_master: true,
            recipe: None,
        };
        let arguments = |request: jobs::RenderRequest| {
            jobs::render_command(
                &request,
                &request.source,
                &request.output_parent.join("partial.tiff"),
            )
            .unwrap()
            .get_args()
            .map(|value| value.to_owned())
            .collect::<Vec<_>>()
        };
        let before = arguments(request(&app.controls));
        app.apply_agent_command(command(project, &ids)).unwrap();
        assert!(app.controls.settings.session.is_some());
        assert!(!app.controls.settings.binned);
        // Reopening/reloading a session must not replace the remembered ordinary recipe.
        let session = app.controls.settings.session.clone().unwrap();
        app.reload_session(session, false);
        app.controls.settings.pyramid_exponent = Some(9.0);
        app.controls.exposure = Some(1.0);
        app.controls.gate = Some(0.0);
        app.controls.workers = 1;
        app.import(root.path().join("source-2"));
        assert_eq!(app.controls.settings, ordinary);
        assert_eq!(history::Recipe::capture(&app.controls), recipe);
        assert_eq!(arguments(request(&app.controls)), before);
        assert!(app.ordinary_recipe.is_none());
    }
}

#[test]
fn session_control_mosaic_primary_and_incompatible_options_refuse_before_mutation() {
    let (_root, mut app, project, ids) = fixture();
    let before = serde_json::to_vec(&app.catalog).unwrap();
    let mut mosaic = command(project, &ids);
    if let AgentCommand::CreateSession { mode, .. } = &mut mosaic {
        *mode = SessionMode::Mosaic;
    }
    assert!(app.apply_agent_command(mosaic).is_err());
    assert_eq!(serde_json::to_vec(&app.catalog).unwrap(), before);
    assert!(app.scan.is_none());
    let mut incompatible = command(project, &ids);
    if let AgentCommand::CreateSession {
        precision_weights, ..
    } = &mut incompatible
    {
        *precision_weights = true;
    }
    assert!(app.apply_agent_command(incompatible).is_err());
    assert_eq!(serde_json::to_vec(&app.catalog).unwrap(), before);
    assert!(app.scan.is_none());
}

#[test]
fn session_import_receipt_count_does_not_enable_unloaded_originals() {
    let (_root, mut app, _, _) = fixture();
    app.progress.frames_total = Some(182);
    let mut run: crate::workspace_history::Run = serde_json::from_value(serde_json::json!({
        "directory":"saved", "source":"ungranted", "output":"saved/photograph.tiff",
        "log":"saved/log", "label":"Imported", "created":0, "status":"Saved",
        "frames":182, "settings":jobs::RenderSettings::default(), "exposure":null,
        "gate":null, "workers":1, "imported":{"imported_at":0,"renderer_bound":false,
            "renderer_build":null,"diagnostic_warnings":[],"files":{}}
    }))
    .unwrap();
    app.expected_run = Some(run.clone());
    assert_eq!(app.process_capture_count(), 0);
    assert_eq!(app.expected_run.as_ref().unwrap().frames, 182);
    run.imported = None;
    app.expected_run = Some(run);
    assert_eq!(
        app.process_capture_count(),
        182,
        "ordinary saved-run behavior remains"
    );
}

#[test]
fn session_control_reconstruction_rejects_unsupported_mode_before_catalog_mutation() {
    let (_root, mut app, project, ids) = fixture();
    let before = serde_json::to_vec(&app.catalog).unwrap();
    for rejected in [
        SessionMode::Layers,
        SessionMode::Mosaic,
        SessionMode::IndependentViews,
    ] {
        let mut request = command(project, &ids);
        if let AgentCommand::CreateSession {
            mode,
            primary_pass,
            original_cfa_reconstruction,
            ..
        } = &mut request
        {
            *mode = rejected;
            *primary_pass = None;
            *original_cfa_reconstruction = true;
        }
        assert!(app.apply_agent_command(request).is_err());
        assert_eq!(serde_json::to_vec(&app.catalog).unwrap(), before);
        assert!(app.scan.is_none());
    }
}

#[test]
fn session_control_independent_view_primary_refuses_before_mutation() {
    let (_root, mut app, project, ids) = fixture();
    let before = serde_json::to_vec(&app.catalog).unwrap();
    let mut request = command(project, &ids);
    if let AgentCommand::CreateSession { mode, .. } = &mut request {
        *mode = SessionMode::IndependentViews;
    }
    assert!(app.apply_agent_command(request).is_err());
    assert_eq!(serde_json::to_vec(&app.catalog).unwrap(), before);
    assert!(app.scan.is_none());
}
fn completed_view_app() -> (tempfile::TempDir, tempfile::TempDir, StrehlApp) {
    let source = crate::session_import::independent_views_fixture();
    let (state, mut app, _, _) = fixture();
    let run =
        crate::session_import::load(source.path(), &std::sync::atomic::AtomicBool::new(false))
            .unwrap();
    app.catalog.import_completed_run(None, run.clone()).unwrap();
    app.controls.settings = run.settings.clone();
    app.expected_run = Some(run.clone());
    app.result = Some(run.output.clone());
    app.refresh_session_outputs(&run.directory);
    app.catalog.save().unwrap();
    (source, state, app)
}
fn finish_output_selection(app: &mut StrehlApp) {
    let until = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while app.session_output_selection.is_some() && std::time::Instant::now() < until {
        app.poll_session_output_selection();
        std::thread::sleep(std::time::Duration::from_millis(2));
    }
    assert!(app.session_output_selection.is_none());
}
#[test]
fn session_control_selected_output_persists_and_reopens_without_changing_recipe() {
    let (_source, state, mut app) = completed_view_app();
    let before = app.controls.settings.clone();
    let selected = app.session_ui.layers[1].clone();
    app.apply_agent_command(AgentCommand::SelectSessionOutput { index: 1 })
        .unwrap();
    finish_output_selection(&mut app);
    assert!(app.error.is_none(), "{:?}", app.error);
    assert_eq!(app.result.as_ref(), Some(&selected));
    assert_eq!(app.controls.settings, before);
    let catalog = crate::workspace_history::Catalog::load(Some(state.path().join("projects.json")));
    let saved = catalog
        .runs
        .iter()
        .find(|run| run.owns_output(&selected))
        .unwrap()
        .clone();
    assert_eq!(saved.output, selected);
    let reopened = crate::workspace_history::reopen(saved)
        .receiver
        .recv_timeout(std::time::Duration::from_secs(5))
        .unwrap()
        .unwrap()
        .0;
    assert_eq!(reopened.output, selected);
    assert_eq!(reopened.settings, before);
}
#[test]
fn session_control_output_refuses_bad_index_directory_and_changed_pixels_atomically() {
    for kind in ["index", "directory", "pixels"] {
        let (_source, _state, mut app) = completed_view_app();
        let original = app.result.clone();
        let catalog = serde_json::to_vec(&app.catalog).unwrap();
        let mut index = 1;
        if kind == "index" {
            index = 2;
        }
        if kind == "directory" {
            app.session_ui.layers[1] = app.session_ui.layers[0].clone();
        }
        if kind == "pixels" {
            std::fs::write(&app.session_ui.layers[1], b"changed").unwrap();
        }
        let result = app.apply_agent_command(AgentCommand::SelectSessionOutput { index });
        if kind == "pixels" {
            result.unwrap();
            finish_output_selection(&mut app);
            assert!(app.error.is_some());
        } else {
            assert!(result.is_err());
        }
        assert_eq!(app.result, original, "{kind}");
        assert_eq!(serde_json::to_vec(&app.catalog).unwrap(), catalog, "{kind}");
    }
}

#[test]
fn session_control_local_view_actions_target_parent_originals_and_ordinary_is_identity() {
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_VIEW {\"schema\":\"strehl.ui-view-progress.v1\",\"index\":0,\"count\":2,\"name\":\"First\",\"source_offset\":0,\"source_count\":2,\"parent_total\":5}\n");
    progress.ingest("STREHL_UI_VIEW {\"schema\":\"strehl.ui-view-progress.v1\",\"index\":1,\"count\":2,\"name\":\"Second\",\"source_offset\":2,\"source_count\":3,\"parent_total\":5}\n");
    let response = process_space::Response {
        selected: Some(1),
        camera_metadata: Some(2),
        compare_pair: Some([0, 2]),
        ..Default::default()
    };
    let ordinary = StrehlApp::parent_process_response(response, None);
    assert_eq!(ordinary.selected, Some(1));
    assert_eq!(ordinary.compare_pair, Some([0, 2]));
    let mapped = StrehlApp::parent_process_response(ordinary, progress.active_view());
    assert_eq!(mapped.selected, Some(3));
    assert_eq!(mapped.camera_metadata, Some(4));
    assert_eq!(mapped.compare_pair, Some([2, 4]));
    let invalid = StrehlApp::parent_process_response(
        process_space::Response {
            selected: Some(3),
            ..Default::default()
        },
        progress.active_view(),
    );
    assert!(invalid.selected.is_none());
}

#[test]
fn session_control_independent_view_initial_zoom_survives_and_only_gauge_switch_resets() {
    let (_source, _state, mut app) = completed_view_app();
    let set = |app: &mut StrehlApp| {
        app.apply_agent_command(AgentCommand::SetView {
            center: [0.7, 0.4],
            zoom: 8.0,
        })
        .unwrap();
    };
    set(&mut app);
    app.apply_agent_command(AgentCommand::SelectSessionOutput { index: 0 })
        .unwrap();
    finish_output_selection(&mut app);
    assert_eq!(
        app.process_space.requested_photo_view(),
        Some((egui::pos2(0.7, 0.4), 8.0)),
        "Initial async open must retain the explicit viewport"
    );
    app.image_path = app.result.clone();
    set(&mut app);
    app.apply_agent_command(AgentCommand::SelectSessionOutput { index: 1 })
        .unwrap();
    finish_output_selection(&mut app);
    assert!(app.error.is_none(), "{:?}", app.error);
    assert_eq!(
        app.process_space.requested_photo_view(),
        None,
        "A different view has a different gauge"
    );
    app.image_path = app.result.clone();
    set(&mut app);
    app.apply_agent_command(AgentCommand::SelectSessionOutput { index: 1 })
        .unwrap();
    finish_output_selection(&mut app);
    assert_eq!(
        app.process_space.requested_photo_view(),
        Some((egui::pos2(0.7, 0.4), 8.0)),
        "Reopening the same view is not a gauge change"
    );
    app.controls.settings.session = None;
    set(&mut app);
    app.open_result(PathBuf::from("ordinary/photograph.tiff"));
    assert_eq!(
        app.process_space.requested_photo_view(),
        Some((egui::pos2(0.7, 0.4), 8.0)),
        "Ordinary behavior stays unchanged"
    );
}
#[test]
fn session_control_inspection_maps_parent_identity_back_to_active_local_axis() {
    let (_root, mut app, _, _) = fixture();
    app.process_view = true;
    app.progress.ingest("STREHL_UI_VIEW {\"schema\":\"strehl.ui-view-progress.v1\",\"index\":1,\"count\":2,\"name\":\"Second\",\"source_offset\":2,\"source_count\":3,\"parent_total\":5}\n");
    app.inspect_frame(3);
    assert_eq!(app.process_space.inspection_frame(), Some(1));
    assert_eq!(app.process_inspection(), Some(3));
    app.inspect_frame(0);
    assert_eq!(
        app.process_space.inspection_frame(),
        Some(1),
        "Other-view identity cannot label a local observation"
    );
    app.progress = PipelineProgress::default();
    app.inspect_frame(3);
    assert_eq!(app.process_space.inspection_frame(), Some(3));
}
