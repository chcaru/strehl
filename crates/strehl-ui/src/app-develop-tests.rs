use super::*;
use crate::jobs::FrameFile;
use strehl_edit::{
    Adjustments, ImageOrigin, LinearImage, RegionAdjustment, RegionShape, SourceRange,
};

fn fixture(dir: &Path) -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    let image = Arc::new(LinearImage {
        width: 64,
        height: 48,
        pixels: (0..64 * 48)
            .flat_map(|i| [0.05 + (i % 64) as f32 * 0.004, 0.12, 0.2])
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    let run = dir.join("run");
    std::fs::create_dir_all(&run).unwrap();
    let path = run.join("result.tiff");
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        coverage: None,
        image: Arc::clone(&image),
        preview: image,
        recipe: Default::default(),
        source: run.join("master.tiff"),
        warnings: Vec::new(),
    });
    app
}

fn paint_repair(app: &mut StrehlApp) {
    app.editor.recipe.regions.push(RegionAdjustment {
        id: "leg".into(),
        name: "Leg joint".into(),
        note: String::new(),
        shape: RegionShape::Stroke {
            points: vec![[0.3, 0.6], [0.35, 0.62]],
            radius: [0.03, 0.04],
        },
        feather: 0.5,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: Some(SourceRange { first: 1, last: 3 }),
    });
    app.editor.recipe.global.exposure = 0.4;
    app.editor.changed();
}

#[test]
fn a_pending_depth_repair_keeps_the_photograph_and_export_enabled() {
    let dir = tempfile::tempdir().unwrap();
    let mut app = fixture(dir.path());
    paint_repair(&mut app);
    assert!(app.editor.repairs_pending());
    // Export is enabled and says what it uses.
    assert!(
        app.develop_can_export(),
        "a pending repair no longer blocks export"
    );
    assert!(
        app.repair_export_note()
            .unwrap()
            .contains("last finished pixels")
    );
    let job = app.editor.freeze_export_job().unwrap();
    let loaded = app.editor.loaded.as_ref().unwrap();
    loaded.image.validate_source_repairs(job.recipe()).unwrap();
    assert_eq!(
        job.recipe().global.exposure,
        0.4,
        "the live tone is exported"
    );
    // The re-stack runs as its own job: no render job, the document stays.
    app.stack = Some(StackScan {
        directory: dir.path().join("captures"),
        frames: (0..5)
            .map(|i| FrameFile {
                path: PathBuf::from(format!("frame-{i}.ARW")),
                bytes: 1,
            })
            .collect(),
        total_bytes: 5,
    });
    app.engine = Some(dir.path().join("no-such-engine.exe"));
    app.output = dir.path().join("out");
    let document = app.editor.path.clone();
    let revision = app.editor.revision;
    app.start_depth_repair().unwrap();
    assert!(app.job.is_none(), "the main render slot stays free");
    assert!(app.edit_pane.develop.repair.is_some());
    assert!(app.editor.loaded.is_some() && app.editor.path == document);
    assert!(
        app.develop_can_export(),
        "export stays enabled while it rebuilds"
    );
    assert!(app.start_depth_repair().is_err(), "one repair at a time");
    // Edits continue while it runs.
    app.editor.recipe.global.contrast = 15.0;
    app.editor.changed();
    // This engine cannot start, so the repair ends; the photograph stays.
    let ctx = egui::Context::default();
    let deadline = Instant::now() + Duration::from_secs(20);
    while app.edit_pane.develop.repair.is_some() {
        app.poll_develop(&ctx);
        assert!(
            Instant::now() < deadline,
            "the failed repair never finished"
        );
        std::thread::sleep(Duration::from_millis(10));
    }
    assert!(app.editor.loaded.is_some() && app.editor.path == document);
    assert_ne!(app.editor.revision, revision);
    assert_eq!(
        app.editor.recipe.global.contrast, 15.0,
        "edits made meanwhile are kept"
    );
    assert!(
        app.edit_pane
            .develop
            .notice
            .as_deref()
            .unwrap_or_default()
            .contains("stopped")
    );
    assert!(app.develop_can_export());
}

#[test]
fn a_depth_repair_rebuilds_the_painted_area_only_and_falls_back_to_the_whole_stack() {
    let dir = tempfile::tempdir().unwrap();
    let mut app = fixture(dir.path());
    paint_repair(&mut app);
    let run_dir = dir.path().join("run");
    for name in ["master.tiff", "result.tiff", "render.log"] {
        std::fs::write(run_dir.join(name), b"original").unwrap();
    }
    std::fs::create_dir_all(run_dir.join("cache")).unwrap();
    std::fs::write(run_dir.join("cache").join("captures-1.warpmap.txt"), b"map").unwrap();
    app.stack = Some(StackScan {
        directory: dir.path().join("captures"),
        frames: (0..5)
            .map(|i| FrameFile {
                path: PathBuf::from(format!("frame-{i}.ARW")),
                bytes: 1,
            })
            .collect(),
        total_bytes: 5,
    });
    app.engine = Some(dir.path().join("no-such-engine.exe"));
    app.output = dir.path().join("out");
    let mut settings = app.controls.settings.clone();
    settings.confidence_map = true;
    app.catalog.add(crate::workspace_history::Run {
        directory: run_dir.clone(),
        source: dir.path().join("captures"),
        output: run_dir.join("result.tiff"),
        log: run_dir.join("render.log"),
        label: "captures".into(),
        created: 1,
        status: "Saved".into(),
        frames: 5,
        sources: Vec::new(),
        settings,
        exposure: None,
        gate: None,
        workers: 4,
        pinned: false,
        imported: None,
    });
    // The open render qualifies: master, photograph, log and its own map.
    let (original, request) = app
        .region_only_source(Path::new("strehl.exe"), &app.editor.recipe)
        .unwrap();
    assert_eq!(original.master, run_dir.join("master.tiff"));
    assert_eq!(original.photo, run_dir.join("result.tiff"));
    assert_eq!(original.log, run_dir.join("render.log"));
    assert_eq!(
        original.warp_map,
        Some(run_dir.join("cache").join("captures-1.warpmap.txt"))
    );
    assert!(
        !request.settings.confidence_map,
        "no second pass over every frame"
    );
    assert_eq!(request.recipe.as_ref(), Some(&app.editor.recipe));
    app.start_depth_repair().unwrap();
    assert_eq!(
        app.edit_pane.develop.repair.as_ref().unwrap().route,
        develop::RepairRoute::Region
    );
    // This engine cannot start: the region-only rebuild stops, the whole
    // stack is tried instead and says why, then that stops too.
    let ctx = egui::Context::default();
    let deadline = Instant::now() + Duration::from_secs(20);
    let mut fell_back = None;
    while let Some(repair) = &app.edit_pane.develop.repair {
        if let develop::RepairRoute::Full(why) = &repair.route {
            fell_back = Some(why.clone());
            assert!(repair.status().starts_with("Re-stacking the whole stack"));
        } else {
            assert!(
                repair
                    .status()
                    .starts_with("Rebuilding the painted area only")
            );
        }
        app.poll_develop(&ctx);
        assert!(Instant::now() < deadline, "the repairs never finished");
        std::thread::sleep(Duration::from_millis(10));
    }
    assert!(
        fell_back
            .as_deref()
            .is_some_and(|why| why.contains("region-only rebuild stopped")),
        "{fell_back:?}"
    );
    assert!(
        app.edit_pane
            .develop
            .notice
            .as_deref()
            .unwrap_or_default()
            .contains("stopped")
    );
    // Without the render in the library, the whole stack is re-stacked.
    app.catalog = Default::default();
    let why = app
        .region_only_source(Path::new("strehl.exe"), &app.editor.recipe)
        .unwrap_err();
    assert!(why.contains("not in the library"), "{why}");
}

#[test]
fn develop_intents_route_to_the_editor_or_the_app() {
    let dir = tempfile::tempdir().unwrap();
    let mut app = fixture(dir.path());
    app.handle_develop_intents(
        vec![
            DevelopIntent::SelectTool(station::DevelopTool::Heal),
            DevelopIntent::Adjust(station::AdjustmentField::Warmth, 30.0),
            DevelopIntent::PickNeutral,
            DevelopIntent::Export,
        ],
        1.0,
    );
    assert_eq!(app.editor.recipe.global.temperature, 30.0);
    assert_eq!(app.editor.develop.tool, station::DevelopTool::WhiteBalance);
    // Export… goes to the Export station.
    assert_eq!(
        app.shell.navigator.station(),
        super::super::studio_route::Station::Export
    );
    // The picker sets warmth and tint from the sampled neutral.
    app.handle_develop_intents(vec![DevelopIntent::SampleNeutral([0.5, 0.5])], 2.0);
    let pick = app
        .editor
        .loaded
        .as_ref()
        .unwrap()
        .image
        .pick_white_balance([0.5, 0.5], 3)
        .unwrap();
    assert_eq!(app.editor.recipe.global.temperature, pick.temperature);
    assert_eq!(app.editor.recipe.global.tint, pick.tint);
    // A canvas gesture reaches the app through the editor's outbox.
    app.editor
        .develop
        .outbox
        .push(DevelopIntent::AddNote([0.2, 0.2]));
    app.poll_develop(&egui::Context::default());
    assert_eq!(app.editor.recipe.regions.len(), 1);
}

#[test]
fn an_export_batch_runs_as_one_job_and_reports_each_file() {
    let dir = tempfile::tempdir().unwrap();
    let mut app = fixture(dir.path());
    let folder = dir.path().join("exports");
    std::fs::create_dir_all(&folder).unwrap();
    let mut library = presets::Library::default();
    for preset in &mut library.presets {
        preset.enabled = matches!(preset.name.as_str(), "Web" | "Print");
    }
    let (key, _, _) = app.develop_subject();
    library.remember_destination(&key, &folder).unwrap();
    app.export_pane.station.library = Some(library);
    paint_repair(&mut app);
    app.start_export_batch(None).unwrap();
    let progress = app
        .export_pane
        .station
        .batch
        .as_ref()
        .unwrap()
        .progress
        .clone();
    assert_eq!(progress.snapshot().files, 2);
    assert!(app.start_export_batch(None).is_err(), "one batch at a time");
    let ctx = egui::Context::default();
    let deadline = Instant::now() + Duration::from_secs(60);
    while app.export_pane.station.batch.is_some() {
        app.poll_export_batch(&ctx);
        assert!(Instant::now() < deadline, "batch did not finish");
        std::thread::sleep(Duration::from_millis(10));
    }
    assert_eq!(progress.snapshot().phase, exporting::BatchPhase::Done);
    let mut names: Vec<String> = std::fs::read_dir(&folder)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    names.sort();
    assert_eq!(names, ["run-result-Print.tiff", "run-result-Web.jpg"]);
    assert_eq!(app.export_pane.station.error, None);
}
