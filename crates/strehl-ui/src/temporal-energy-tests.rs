//! Saved-recipe and real command-construction witnesses for the experimental toggle.
use super::*;
use std::ffi::OsStr;
use strehl_edit::{Adjustments, DevelopmentRecipe, RegionAdjustment, RegionShape, SourceRange};

fn request() -> RenderRequest {
    RenderRequest {
        executable: PathBuf::from("strehl"),
        source: PathBuf::from("capture with spaces"),
        output_parent: PathBuf::from("output with spaces"),
        exposure_ev: None,
        pyramid_gate: None,
        worker_threads: Some(3),
        settings: RenderSettings::default(),
        retain_master: true,
        recipe: None,
    }
}

fn recipe(range: Option<SourceRange>) -> DevelopmentRecipe {
    DevelopmentRecipe {
        global: Adjustments {
            exposure: 0.75,
            ..Default::default()
        },
        regions: vec![RegionAdjustment {
            id: "witness".into(),
            name: "Faint feature".into(),
            note: "Keep this saved edit".into(),
            shape: RegionShape::Rectangle {
                min: [0.2, 0.2],
                max: [0.4, 0.4],
            },
            feather: 0.25,
            enabled: true,
            adjustments: Adjustments {
                contrast: 5.0,
                ..Default::default()
            },
            source_range: range,
        }],
        ..Default::default()
    }
}

#[test]
fn temporal_energy_legacy_settings_and_saved_run_drafts_keep_their_own_mode() {
    let legacy: RenderSettings = serde_json::from_str("{}").unwrap();
    assert!(!legacy.temporal_energy);
    let mut settings = legacy;
    settings.temporal_energy = true;
    let run = crate::workspace_history::Run {
        directory: PathBuf::from("run"),
        source: PathBuf::from("capture"),
        output: PathBuf::from("run/result.tiff"),
        log: PathBuf::from("run/render.log"),
        label: "Experimental comparison".into(),
        created: 1,
        status: "Saved".into(),
        frames: 5,
        sources: Vec::new(),
        settings,
        exposure: None,
        gate: None,
        workers: 3,
        pinned: false,
        imported: None,
    };
    let encoded = serde_json::to_value(&run).unwrap();
    assert_eq!(encoded["settings"]["temporal_energy"], true);
    let reopened: crate::workspace_history::Run = serde_json::from_value(encoded.clone()).unwrap();
    assert!(reopened.settings.temporal_energy);
    let mut draft = crate::workspace_history::StackDraft::from_run(&reopened);
    draft.settings.temporal_energy = false;
    let reopened_draft: crate::workspace_history::StackDraft =
        serde_json::from_slice(&serde_json::to_vec(&draft).unwrap()).unwrap();
    assert!(!reopened_draft.settings.temporal_energy);
    assert!(
        reopened.settings.temporal_energy,
        "a new recipe must not rewrite an old run"
    );
    let mut old_run = encoded;
    old_run["settings"]
        .as_object_mut()
        .unwrap()
        .remove("temporal_energy");
    let reopened_old: crate::workspace_history::Run = serde_json::from_value(old_run).unwrap();
    assert!(!reopened_old.settings.temporal_energy);
}

#[test]
fn temporal_energy_worker_environment_comes_from_recipe_even_with_inherited_shift() {
    for enabled in [false, true] {
        let mut request = request();
        request.settings.temporal_energy = enabled;
        let actual = render_command(
            &request,
            &request.source,
            Path::new("output with spaces/result.partial.tiff"),
        )
        .unwrap();
        let expected = OsStr::new(if enabled { "on" } else { "off" });
        assert!(
            actual.get_envs().any(|(name, value)| {
                name == "STREHL_TEMPORAL_ENERGY" && value == Some(expected)
            })
        );
        let mut inherited = Command::new("unused-no-process-started");
        inherited.env("STREHL_TEMPORAL_ENERGY", "shift");
        configure_render_environment(
            &mut inherited,
            &request,
            [
                ("STREHL_TEMPORAL_ENERGY".into(), "shift".into()),
                ("STREHL_SPATIAL_NOISE_FLOOR".into(), "on".into()),
                ("RAYON_NUM_THREADS".into(), "1000".into()),
                ("PATH".into(), "system path".into()),
            ],
        );
        assert!(
            inherited.get_envs().any(|(name, value)| {
                name == "STREHL_TEMPORAL_ENERGY" && value == Some(expected)
            })
        );
        assert!(
            inherited
                .get_envs()
                .any(|(name, value)| { name == "STREHL_SPATIAL_NOISE_FLOOR" && value.is_none() })
        );
        for key in ["RAYON_NUM_THREADS", "STREHL_PYRAMID_WORKERS"] {
            assert!(
                inherited
                    .get_envs()
                    .any(|(name, value)| { name == key && value == Some(OsStr::new("3")) })
            );
        }
        assert!(!inherited.get_envs().any(|(name, _)| name == "PATH"));
    }
}

#[test]
fn temporal_energy_keeps_photo_edits_without_entering_the_inert_repair_consumer() {
    let mut request = request();
    request.settings.temporal_energy = true;
    request.recipe = Some(recipe(None));
    let original = request.recipe.clone();
    validate_settings(&request).unwrap();
    let partial = Path::new("output/result.partial.tiff");
    let command = render_command(&request, &request.source, partial).unwrap();
    assert!(command.get_args().any(|arg| arg == "--linear-master"));
    assert!(!command.get_args().any(|arg| arg == "--region-recipe"));
    assert_eq!(
        request.recipe, original,
        "saved development must remain intact"
    );
    request.settings.temporal_energy = false;
    let ordinary = render_command(&request, &request.source, partial).unwrap();
    assert!(ordinary.get_args().any(|arg| arg == "--region-recipe"));
}

#[test]
fn temporal_energy_refuses_enabled_source_repairs_before_output_creation() {
    let files = tempfile::tempdir().unwrap();
    let mut request = request();
    request.output_parent = files.path().join("must-not-be-created");
    request.settings.temporal_energy = true;
    request.recipe = Some(recipe(Some(SourceRange { first: 0, last: 1 })));
    let expected = "Turn off temporal detail smoothing or disable source-range repairs";
    assert_eq!(
        validate_settings(&request).unwrap_err().to_string(),
        expected
    );
    assert!(
        render_command(
            &request,
            &request.source,
            Path::new("output/result.partial.tiff")
        )
        .is_err()
    );
    let (sender, _) = mpsc::sync_channel(4);
    match run_render(&request, &Arc::new(AtomicBool::new(false)), &sender) {
        RenderOutcome::Failed { directory, message } => {
            assert!(directory.is_none());
            assert_eq!(message, expected);
        }
        other => panic!("unsupported request reached rendering: {other:?}"),
    }
    assert!(!request.output_parent.exists());
    request.recipe.as_mut().unwrap().regions[0].enabled = false;
    validate_settings(&request).unwrap();
    let disabled = render_command(
        &request,
        &request.source,
        Path::new("output/result.partial.tiff"),
    )
    .unwrap();
    assert!(!disabled.get_args().any(|arg| arg == "--region-recipe"));
}

#[test]
fn temporal_energy_reports_gate_and_sampling_conflicts_without_rewriting_them() {
    let mut request = request();
    request.settings.temporal_energy = true;
    for value in [0.0, -1.0, f32::NAN] {
        request.pyramid_gate = Some(value);
        assert_eq!(
            validate_settings(&request).unwrap_err().to_string(),
            "Temporal detail smoothing needs a Noise gate above zero"
        );
    }
    request.pyramid_gate = None;
    request.settings.binned = true;
    assert_eq!(
        validate_settings(&request).unwrap_err().to_string(),
        "Turn off Half-size TIFF to use temporal detail smoothing"
    );
    assert!(request.settings.binned && request.settings.temporal_energy);
    request.settings.binned = false;
    validate_settings(&request).unwrap();
    request.settings.temporal_energy = false;
    request.pyramid_gate = Some(0.0);
    validate_settings(&request).unwrap();
}

fn publication_fixture(directory: &Path) -> (RenderRequest, serde_json::Value) {
    let partial = directory.join("result.partial.tiff");
    image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
        16,
        12,
        image::Rgb([1000, 2000, 3000]),
    )
    .save(&partial)
    .unwrap();
    let master = directory.join("master.partial.tiff");
    strehl_edit::save_linear_tiff(
        &master,
        &strehl_edit::LinearImage {
            width: 16,
            height: 12,
            pixels: vec![0.3; 16 * 12 * 3],
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: Some(strehl_edit::DisplayBaseline {
                black: 0.0,
                white: 1.0,
                contrast: 0.0,
                exposure_gain: 1.0,
            }),
            baked_recipe: None,
        },
    )
    .unwrap();
    let identity = |path: &Path| {
        use sha2::{Digest, Sha256};
        let bytes = fs::read(path).unwrap();
        let sha256: String = Sha256::digest(&bytes)
            .iter()
            .map(|v| format!("{v:02x}"))
            .collect();
        serde_json::json!({"path":path,"bytes":bytes.len(),"sha256":sha256})
    };
    let worker = serde_json::json!({
        "schema":"strehl-experimental-temporal-energy-v1", "mode":"On",
        "completion":"images written and hashed",
        "completed_output":identity(&partial), "completed_linear_master":identity(&master),
    });
    let mut request = request();
    request.settings.temporal_energy = true;
    request.settings.confidence_map = false;
    (request, worker)
}

#[test]
fn temporal_energy_publication_preserves_worker_receipt_and_maps_both_final_names() {
    let files = tempfile::tempdir().unwrap();
    let directory = files.path();
    let (request, worker) = publication_fixture(directory);
    let worker_path = directory.join("result.partial.tiff.temporal-energy.json");
    let worker_bytes = serde_json::to_vec_pretty(&worker).unwrap();
    fs::write(&worker_path, &worker_bytes).unwrap();
    publish_completed_render(
        &request,
        directory,
        &directory.join("result.partial.tiff"),
        &directory.join("result.tiff"),
        &AtomicBool::new(false),
    )
    .unwrap();
    assert_eq!(fs::read(&worker_path).unwrap(), worker_bytes);
    assert!(!directory.join("result.partial.tiff").exists());
    assert!(!directory.join("master.partial.tiff").exists());
    let mapping: serde_json::Value =
        serde_json::from_slice(&fs::read(directory.join("temporal-publication.json")).unwrap())
            .unwrap();
    assert_eq!(mapping["schema"], "strehl-desktop-temporal-publication-v1");
    assert_eq!(mapping["completion"], "images published");
    assert_eq!(
        mapping["worker_receipt"]["path"],
        worker_path.to_string_lossy().as_ref()
    );
    use sha2::{Digest, Sha256};
    let receipt_hash: String = Sha256::digest(&worker_bytes)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect();
    assert_eq!(mapping["worker_receipt"]["sha256"], receipt_hash);
    for (index, key, original, final_name) in [
        (0, "completed_output", "result.partial.tiff", "result.tiff"),
        (
            1,
            "completed_linear_master",
            "master.partial.tiff",
            "master.tiff",
        ),
    ] {
        let entry = &mapping["artifacts"][index];
        assert_eq!(
            entry["worker_path"],
            directory.join(original).to_string_lossy().as_ref()
        );
        assert_eq!(
            entry["published_path"],
            directory.join(final_name).to_string_lossy().as_ref()
        );
        assert_eq!(entry["sha256"], worker[key]["sha256"]);
        assert_eq!(entry["bytes"], worker[key]["bytes"]);
        let actual: String = Sha256::digest(fs::read(directory.join(final_name)).unwrap())
            .iter()
            .map(|v| format!("{v:02x}"))
            .collect();
        assert_eq!(entry["sha256"], actual);
    }
}

#[test]
fn temporal_energy_publication_refuses_missing_or_inconsistent_evidence_before_renaming() {
    let files = tempfile::tempdir().unwrap();
    let directory = files.path();
    let (request, valid) = publication_fixture(directory);
    let worker_path = directory.join("result.partial.tiff.temporal-energy.json");
    let publish = || {
        publish_completed_render(
            &request,
            directory,
            &directory.join("result.partial.tiff"),
            &directory.join("result.tiff"),
            &AtomicBool::new(false),
        )
    };
    assert!(publish().is_err(), "an absent receipt must refuse");
    fs::write(&worker_path, b"{incomplete").unwrap();
    assert!(publish().is_err(), "a malformed receipt must refuse");
    for foil in 0..7 {
        let mut worker = valid.clone();
        match foil {
            0 => worker["schema"] = serde_json::json!("unknown"),
            1 => worker["mode"] = serde_json::json!("ShiftNeighbors"),
            2 => worker["completion"] = serde_json::json!("started"),
            3 => {
                worker["completed_output"]["path"] = serde_json::json!(directory.join("other.tiff"))
            }
            4 => worker["completed_output"]["sha256"] = serde_json::json!("0".repeat(64)),
            5 => worker["completed_linear_master"]["bytes"] = serde_json::json!(1),
            6 => worker["completed_linear_master"] = serde_json::Value::Null,
            _ => unreachable!(),
        }
        fs::write(&worker_path, serde_json::to_vec(&worker).unwrap()).unwrap();
        assert!(
            publish().is_err(),
            "inconsistent receipt foil {foil} must refuse"
        );
        assert!(directory.join("result.partial.tiff").exists());
        assert!(directory.join("master.partial.tiff").exists());
        assert!(!directory.join("result.tiff").exists());
        assert!(!directory.join("master.tiff").exists());
        assert!(!directory.join("temporal-publication.json").exists());
    }
}
