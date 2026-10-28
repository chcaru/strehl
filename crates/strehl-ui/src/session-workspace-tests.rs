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
