use super::*;
use crate::jobs::{FrameFile, RenderSettings};

fn fixture() -> (tempfile::TempDir, SessionDraft, StackScan) {
    let root = tempfile::tempdir().unwrap();
    let mut directories = Vec::new();
    let mut frames = Vec::new();
    for (segment, count) in [2, 1, 2].into_iter().enumerate() {
        let directory = root.path().join(format!("segment-{segment}"));
        std::fs::create_dir(&directory).unwrap();
        let directory = std::fs::canonicalize(directory).unwrap();
        for i in 0..count {
            let path = directory.join(format!("capture-{i:02}.ARW"));
            std::fs::write(&path, [segment as u8, i as u8, 42]).unwrap();
            frames.push(FrameFile { path, bytes: 3 });
        }
        directories.push(directory);
    }
    let scan = StackScan {
        directory: directories[0].clone(),
        frames,
        total_bytes: 15,
    };
    let draft = SessionDraft {
        manifest: SessionSpec {
            passes: vec![
                PassSpec {
                    name: "Continued pass".into(),
                    directories: directories[..2].to_vec(),
                },
                PassSpec {
                    name: "Repeat".into(),
                    directories: directories[2..].to_vec(),
                },
            ],
            primary_pass: Some(1),
            ..Default::default()
        },
        memory_limit_gib: 24.0,
        precision_weights: false,
        contribution_maps: false,
        focus_evidence: false,
        reproducibility: false,
        original_cfa_reconstruction: false,
        sources: crate::workspace_history::source_identities(&scan),
    };
    (root, draft, scan)
}

#[test]
fn session_workspace_old_recipes_keep_ordinary_defaults_and_no_session_field() {
    let settings: RenderSettings = serde_json::from_str("{}").unwrap();
    assert_eq!(settings, RenderSettings::default());
    assert!(settings.session.is_none());
    assert!(
        serde_json::to_value(&settings)
            .unwrap()
            .get("session")
            .is_none()
    );
    assert!(settings.confidence_map && settings.correct_lateral_ca);
}

#[test]
fn session_workspace_grouping_preserves_continuation_order_and_detects_wrong_scan() {
    let (_root, draft, mut scan) = fixture();
    draft.validate().unwrap();
    let groups = draft.groups(&scan).unwrap();
    assert_eq!(groups[0].range, 0..3);
    assert_eq!(groups[0].segment_ends, vec![2, 3]);
    assert_eq!(groups[1].range, 3..5);
    assert!(groups[1].primary && !groups[0].primary);
    scan.frames.swap(0, 4);
    assert!(draft.groups(&scan).is_err());
}

#[test]
fn session_workspace_primary_follows_reordering_and_removal_never_selects_another_pass() {
    let (_root, mut draft, _) = fixture();
    draft.move_pass(0, 1);
    assert_eq!(draft.manifest.primary_pass, Some(0));
    assert_eq!(draft.manifest.passes[0].name, "Repeat");
    draft.remove_pass(0);
    assert_eq!(draft.manifest.primary_pass, None);
    assert_eq!(draft.manifest.passes[0].name, "Continued pass");
}

#[test]
fn session_workspace_settings_snapshot_keeps_layout_budget_and_sources_immutable() {
    let (_root, draft, _) = fixture();
    let mut next = RenderSettings {
        session: Some(draft),
        ..RenderSettings::default()
    };
    let saved = next.clone();
    let before = serde_json::to_vec(&saved).unwrap();
    let session = next.session.as_mut().unwrap();
    session.manifest.passes[0].directories.reverse();
    session.manifest.primary_pass = None;
    session.memory_limit_gib = 8.0;
    session.sources.clear();
    assert_eq!(serde_json::to_vec(&saved).unwrap(), before);
    let restored: RenderSettings = serde_json::from_slice(&before).unwrap();
    assert_eq!(restored, saved);
    assert_ne!(restored, next);
}

#[test]
fn session_workspace_background_scan_uses_production_manifest_order() {
    let (_root, draft, scan) = fixture();
    let task = crate::jobs::scan_session(draft.clone());
    let actual = task
        .receiver
        .recv_timeout(std::time::Duration::from_secs(5))
        .unwrap()
        .unwrap();
    assert_eq!(
        actual.frames.iter().map(|f| &f.path).collect::<Vec<_>>(),
        scan.frames.iter().map(|f| &f.path).collect::<Vec<_>>()
    );
    assert_eq!(actual.total_bytes, 15);
    assert_eq!(draft.groups(&actual).unwrap()[0].segment_ends, vec![2, 3]);
}

#[test]
fn session_workspace_invalid_budget_and_primary_are_refused() {
    let (_root, mut draft, _) = fixture();
    draft.memory_limit_gib = f64::NAN;
    assert!(draft.validate().is_err());
    draft.memory_limit_gib = 16.0;
    draft.manifest.primary_pass = Some(2);
    assert!(draft.validate().is_err());
}

#[test]
fn session_workspace_new_options_default_off_for_old_saved_sessions() {
    let (_root, draft, _) = fixture();
    let mut old = serde_json::to_value(&draft).unwrap();
    for key in [
        "precision_weights",
        "contribution_maps",
        "focus_evidence",
        "reproducibility",
        "original_cfa_reconstruction",
    ] {
        old.as_object_mut().unwrap().remove(key);
    }
    let restored: SessionDraft = serde_json::from_value(old).unwrap();
    assert_eq!(restored, draft);
    assert!(
        !restored.precision_weights
            && !restored.contribution_maps
            && !restored.focus_evidence
            && !restored.reproducibility
            && !restored.original_cfa_reconstruction
    );
}

#[test]
fn session_workspace_options_are_immutable_and_mode_transitions_clear_invalid_preferences() {
    let (_root, mut draft, _) = fixture();
    draft.manifest.mode = SessionMode::Repeat;
    draft.precision_weights = true;
    draft.contribution_maps = true;
    draft.focus_evidence = true;
    draft.reproducibility = true;
    draft.original_cfa_reconstruction = true;
    draft.validate().unwrap();
    let saved = draft.clone();
    let bytes = serde_json::to_vec(&saved).unwrap();
    draft.manifest.mode = SessionMode::Mosaic;
    assert!(draft.validate().is_err());
    draft.normalize_mode_options();
    draft.validate().unwrap();
    assert_eq!(draft.manifest.primary_pass, None);
    assert!(
        !draft.precision_weights
            && !draft.contribution_maps
            && !draft.focus_evidence
            && !draft.reproducibility
            && !draft.original_cfa_reconstruction
    );
    assert_eq!(serde_json::to_vec(&saved).unwrap(), bytes);
    let mut reduced = saved;
    reduced.remove_pass(1);
    assert!(!reduced.precision_weights && !reduced.reproducibility);
    assert!(reduced.contribution_maps && reduced.focus_evidence);
    assert_eq!(mode_label(SessionMode::Mosaic), "Wider mosaic");
}

#[test]
fn session_workspace_mode_guards_are_explicit_for_first_two_pass_comparison() {
    for mode in MODES {
        assert!(!precision_available(mode, 1));
        assert!(!reproducibility_available(mode, 1));
        assert_eq!(
            precision_available(mode, 2),
            matches!(mode, SessionMode::Repeat | SessionMode::Hdr)
        );
        assert_eq!(
            reproducibility_available(mode, 3),
            matches!(
                mode,
                SessionMode::Combine
                    | SessionMode::Interleave
                    | SessionMode::Repeat
                    | SessionMode::Layers
            )
        );
    }
}

#[test]
fn session_reconstruction_default_guard_preserves_single_and_multi_pass_jobs() {
    let (_root, mut draft, _) = fixture();
    for mode in MODES {
        draft.manifest.mode = mode;
        draft.manifest.primary_pass = None;
        draft.original_cfa_reconstruction = true;
        let supported = matches!(
            mode,
            SessionMode::Combine | SessionMode::Interleave | SessionMode::Repeat | SessionMode::Hdr
        );
        assert_eq!(reconstruction_available(mode), supported);
        assert_eq!(draft.validate().is_ok(), supported);
        let saved = draft.clone();
        draft.normalize_mode_options();
        assert_eq!(draft.original_cfa_reconstruction, supported);
        assert!(saved.original_cfa_reconstruction);
    }
}

#[test]
fn session_workspace_independent_views_clear_cross_view_flags_and_primary() {
    let (_root, mut draft, scan) = fixture();
    draft.manifest.mode = SessionMode::IndependentViews;
    draft.precision_weights = true;
    draft.contribution_maps = true;
    draft.focus_evidence = true;
    draft.reproducibility = true;
    draft.original_cfa_reconstruction = true;
    assert!(draft.validate().is_err());
    draft.normalize_mode_options();
    draft.validate().unwrap();
    assert_eq!(draft.manifest.primary_pass, None);
    assert!(
        !draft.precision_weights
            && !draft.contribution_maps
            && !draft.focus_evidence
            && !draft.reproducibility
            && !draft.original_cfa_reconstruction
    );
    assert_eq!(draft.groups(&scan).unwrap()[1].range, 3..5);
    assert_eq!(output_prefix(draft.manifest.mode), Some("view"));
    assert_eq!(
        serde_json::to_value(draft.manifest.mode).unwrap(),
        "independent_views"
    );
    draft.manifest.passes.pop();
    draft.sources.truncate(3);
    draft.validate().unwrap();
    assert_eq!(draft.manifest.passes.len(), 1);
    assert_eq!(output_prefix(draft.manifest.mode), Some("view"));
}
