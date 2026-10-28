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
