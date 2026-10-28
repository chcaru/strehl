use super::*;

fn fixture() -> (tempfile::TempDir, RenderRequest) {
    let root = tempfile::tempdir().unwrap();
    let source = root.path().join("source");
    fs::create_dir(&source).unwrap();
    let source = fs::canonicalize(source).unwrap();
    let path = source.join("capture.ARW");
    fs::write(&path, b"unique original").unwrap();
    let scan = StackScan {
        directory: source.clone(),
        frames: vec![FrameFile { path, bytes: 15 }],
        total_bytes: 15,
    };
    let mut draft = SessionDraft::from_directory(source.clone());
    draft.memory_limit_gib = 24.0;
    draft.sources = crate::workspace_history::source_identities(&scan);
    let request = RenderRequest {
        executable: "strehl-external-test-engine".into(),
        source,
        output_parent: root.path().join("output"),
        exposure_ev: Some(-0.5),
        pyramid_gate: Some(2.5),
        worker_threads: Some(7),
        settings: RenderSettings {
            session: Some(draft),
            confidence_map: false,
            correct_lateral_ca: false,
            ..RenderSettings::default()
        },
        retain_master: true,
        recipe: None,
    };
    (root, request)
}

#[test]
fn session_worker_command_binds_resource_settings_and_uses_fresh_output_directory() {
    let (_root, request) = fixture();
    let manifest = request.output_parent.join("manifest with spaces.json");
    let output = request.output_parent.join("fresh session output");
    let command = session_command(&request, &manifest, &output).unwrap();
    let args: Vec<_> = command
        .get_args()
        .map(|arg| arg.to_string_lossy().into_owned())
        .collect();
    assert_eq!(&args[..2], ["session", "stack"]);
    assert_eq!(args[2], manifest.to_string_lossy());
    assert!(
        args.windows(2)
            .any(|pair| pair == ["--out-dir", output.to_str().unwrap()])
    );
    assert!(
        args.windows(2)
            .any(|pair| pair == ["--memory-limit-gib", "24"])
    );
    assert!(args.windows(2).any(|pair| pair == ["--threads", "7"]));
    assert!(
        args.contains(&"--exposure=-0.5".into()) && args.contains(&"--pyramid-gate=2.5".into())
    );
    assert!(!output.exists());
    assert!(!args.iter().any(|arg| {
        ["--out", "--confidence-map", "--region-recipe", "--binned"].contains(&arg.as_str())
    }));
}

#[test]
fn session_worker_refuses_unsupported_settings_instead_of_silently_dropping_them() {
    let (_root, mut request) = fixture();
    request.settings.binned = true;
    assert!(session_command(&request, Path::new("manifest.json"), Path::new("out")).is_err());
    request.settings.binned = false;
    request.settings.frame_limit = Some(1);
    assert!(session_command(&request, Path::new("manifest.json"), Path::new("out")).is_err());
    request.settings.frame_limit = None;
    request.recipe = Some(strehl_edit::DevelopmentRecipe::default());
    assert!(session_command(&request, Path::new("manifest.json"), Path::new("out")).is_err());
}

#[test]
fn session_worker_refuses_changed_snapshot_before_creating_output_or_starting_engine() {
    let (_root, request) = fixture();
    fs::write(
        request.source.join("capture.ARW"),
        b"changed original bytes",
    )
    .unwrap();
    let (sender, _receiver) = mpsc::sync_channel(8);
    let outcome = run_session_render(&request, &Arc::new(AtomicBool::new(false)), &sender);
    match outcome {
        RenderOutcome::Failed {
            directory: None,
            message,
        } => assert!(message.contains("changed since import")),
        other => panic!("unexpected {other:?}"),
    }
    assert!(!request.output_parent.exists());
}

#[test]
fn session_worker_refuses_outputs_inside_any_source_segment() {
    let (_root, mut request) = fixture();
    request.output_parent = request.source.join("forbidden-output");
    let (sender, _receiver) = mpsc::sync_channel(8);
    let outcome = run_session_render(&request, &Arc::new(AtomicBool::new(false)), &sender);
    assert!(matches!(
        outcome,
        RenderOutcome::Failed {
            directory: None,
            ..
        }
    ));
    assert!(!request.output_parent.exists());
    assert_eq!(
        fs::read(request.source.join("capture.ARW")).unwrap(),
        b"unique original"
    );
}

#[test]
fn session_worker_checks_actual_completed_census_before_publication() {
    let (root, request) = fixture();
    let session = request.settings.session.as_ref().unwrap();
    let output = root.path().join("receipts");
    fs::create_dir(&output).unwrap();
    let actual: Vec<_> = session
        .sources
        .iter()
        .map(|source| strehl_cli::session_input::SourceIdentity {
            path: source.path.clone(),
            bytes: source.bytes,
            modified_unix_nanos: source.modified_ns.map(|n| u64::try_from(n).unwrap()),
            sha256: "ab".repeat(32),
        })
        .collect();
    let save = |identities: &[strehl_cli::session_input::SourceIdentity]| {
        fs::write(
            output.join("source-identities.json"),
            serde_json::to_vec(identities).unwrap(),
        )
        .unwrap();
    };
    save(&actual);
    assert!(validate_completed_sources(&output, session).is_err());
    fs::write(
        output.join("completed.json"),
        br#"{"schema":"strehl.session-completion.v1"}"#,
    )
    .unwrap();
    validate_completed_sources(&output, session).unwrap();
    for arm in 0..6 {
        let mut changed = actual.clone();
        match arm {
            0 => changed.push(changed[0].clone()),
            1 => changed.clear(),
            2 => changed[0].path = root.path().join("different.ARW"),
            3 => changed[0].bytes += 1,
            4 => changed[0].modified_unix_nanos = None,
            5 => changed[0].sha256 = "not a whole source hash".into(),
            _ => unreachable!(),
        }
        save(&changed);
        assert!(
            validate_completed_sources(&output, session).is_err(),
            "arm {arm}"
        );
    }
    let mut two = session.clone();
    two.sources.push(two.sources[0].clone());
    two.sources[1].path = root.path().join("second.ARW");
    let mut ordered = actual.clone();
    ordered.push(actual[0].clone());
    ordered[1].path = two.sources[1].path.clone();
    save(&ordered);
    validate_completed_sources(&output, &two).unwrap();
    ordered.reverse();
    save(&ordered);
    assert!(validate_completed_sources(&output, &two).is_err());
    save(&actual);
    let mut overflow = session.clone();
    overflow.sources[0].modified_ns = Some(u128::from(u64::MAX) + 1);
    assert!(validate_completed_sources(&output, &overflow).is_err());
}
