use super::*;
fn fixture() -> tempfile::TempDir {
    super::super::views::tests::fixture()
}
#[test]
fn session_bundle_export_relocates_exact_bound_artifacts_without_unbound_files() {
    let source = fixture();
    std::fs::write(source.path().join("unbound-private.arw"), b"not exported").unwrap();
    let parent = tempfile::tempdir().unwrap();
    let destination = parent.path().join("relocated");
    let path = export(source.path(), &destination, &AtomicBool::new(false)).unwrap();
    let first = load(source.path(), &AtomicBool::new(false)).unwrap();
    let second = load(&path, &AtomicBool::new(false)).unwrap();
    assert_eq!(
        first.imported.as_ref().unwrap().files,
        second.imported.as_ref().unwrap().files
    );
    assert_eq!(first.sources, second.sources);
    assert!(!path.join("unbound-private.arw").exists());
    assert!(!path.join("bundle-completion.partial.json").exists());
    assert!(second.owns_output(&path.join("view-02/photograph.tiff")));
    assert_eq!(
        std::fs::read(source.path().join("source-identities.json")).unwrap(),
        std::fs::read(path.join("source-identities.json")).unwrap()
    );
}
#[test]
fn session_bundle_export_fresh_destination_cancellation_and_mutation_controls() {
    for kind in [
        "existing",
        "cancel-before",
        "cancel-copy",
        "source-change",
        "inside-source",
    ] {
        let source = fixture();
        let parent = tempfile::tempdir().unwrap();
        let destination = if kind == "inside-source" {
            source.path().join("copy")
        } else {
            parent.path().join("copy")
        };
        if kind == "existing" {
            std::fs::create_dir(&destination).unwrap();
            std::fs::write(destination.join("sentinel"), b"keep").unwrap();
        }
        let cancelled = AtomicBool::new(kind == "cancel-before");
        let mut called = false;
        let result = export_observed(source.path(), &destination, &cancelled, &mut |_| {
            if called {
                return;
            }
            called = true;
            if kind == "cancel-copy" {
                cancelled.store(true, Ordering::Relaxed);
            }
            if kind == "source-change" {
                std::fs::write(source.path().join("view-02/master.tiff"), b"changed").unwrap();
            }
        });
        assert!(result.is_err(), "{kind}");
        assert!(!destination.join("completed.json").exists(), "{kind}");
        if kind == "existing" {
            assert_eq!(
                std::fs::read(destination.join("sentinel")).unwrap(),
                b"keep"
            );
        }
        if kind == "cancel-copy" {
            assert!(called);
            assert!(destination.exists());
        }
    }
}
#[test]
fn session_bundle_export_control_command_has_explicit_grant_and_fresh_name() {
    use crate::agent_interface::AgentCommand;
    let command = AgentCommand::ExportViewBundle {
        grant_id: "folder-1".into(),
        relative_parent: "exports".into(),
        folder_name: "complete-views".into(),
    };
    command.validate().unwrap();
    let encoded = serde_json::to_value(command).unwrap();
    assert_eq!(encoded["operation"], "export_view_bundle");
    for name in ["../escape", "CON", "already/path", ""] {
        assert!(
            AgentCommand::ExportViewBundle {
                grant_id: "folder-1".into(),
                relative_parent: "exports".into(),
                folder_name: name.into()
            }
            .validate()
            .is_err()
        );
    }
}

#[test]
fn session_bundle_export_committed_result_survives_late_cancel() {
    let task = crate::jobs::spawn_reporting_task("bundle-publication-control", |cancelled| {
        cancelled.store(true, Ordering::Relaxed);
        Ok(7usize)
    });
    assert_eq!(
        task.receiver
            .recv_timeout(std::time::Duration::from_secs(5))
            .unwrap()
            .unwrap(),
        7
    );
}
