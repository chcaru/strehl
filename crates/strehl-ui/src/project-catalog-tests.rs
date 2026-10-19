//! Project workflows with independent identities and adversarial tree edits.
//! These deliberately exercise duplicate names, failed moves, old catalogs,
//! and recipes changed after rendering; same-value assertions are insufficient.
use super::*;

fn run(directory: &str, source: &str, band_count: usize) -> Run {
    serde_json::from_value(serde_json::json!({
        "directory": directory, "source": source,
        "output": format!("{directory}/photo.tiff"), "log": format!("{directory}/render.log"),
        "label": "same name", "created": 123, "status": "Saved", "frames": 2,
        "sources": [{"path":format!("{source}/one.arw"),"bytes":100},{"path":format!("{source}/two.arw"),"bytes":200}],
        "settings": {"pyramid_bands":band_count,"pyramid_exponent":null,"pyramid_sharpen":null,
            "resampler":"Lanczos3","binned":false,"correct_lateral_ca":true,"crop_to_coverage":false},
        "exposure":null,"gate":0.8,"workers":4,"pinned":false
    })).unwrap()
}
fn draft(source: &str) -> StackDraft {
    StackDraft::from_run(&run("never-rendered", source, 7))
}

#[test]
fn project_evolves_through_new_captures_and_revisions_without_rewriting_evidence() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Bee · October").unwrap();
    let folder = catalog
        .create_folder(project, "Lighting experiments")
        .unwrap();
    let first = catalog
        .create_stack(folder, "First attempt", draft("capture-a"))
        .unwrap();
    let second = catalog
        .create_stack(folder, "Reshoot", draft("capture-b"))
        .unwrap();
    let first_run = run("render-a", "capture-a", 7);
    catalog.add_revision(first, first_run.clone()).unwrap();
    let before = serde_json::to_vec(&catalog.runs[0]).unwrap();
    let mut recipe = catalog.node(first).unwrap().stack.clone().unwrap();
    recipe.settings.pyramid_bands = Some(5);
    recipe.exposure = Some(-0.5);
    catalog.update_stack_draft(first, recipe).unwrap();
    assert_eq!(
        serde_json::to_vec(&catalog.runs[0]).unwrap(),
        before,
        "next recipe must not rewrite the saved render's evidence"
    );
    let mut next = run("render-b", "capture-a", 5);
    next.exposure = Some(-0.5);
    catalog.add_revision(first, next).unwrap();
    catalog
        .add_revision(second, run("render-c", "capture-b", 6))
        .unwrap();
    assert_eq!(
        catalog.node(first).unwrap().revisions,
        [PathBuf::from("render-a"), PathBuf::from("render-b")]
    );
    assert_eq!(
        catalog.node(second).unwrap().revisions,
        [PathBuf::from("render-c")]
    );
    assert_eq!(
        catalog.latest_run(first).unwrap().settings.pyramid_bands,
        Some(5)
    );
    assert_eq!(
        catalog
            .runs
            .iter()
            .find(|r| r.directory == Path::new("render-a"))
            .unwrap()
            .settings
            .pyramid_bands,
        Some(7)
    );
    assert_eq!(catalog.stack_for_run(Path::new("render-c")), Some(second));
    catalog.validate().unwrap();
}

#[test]
fn moving_a_branch_preserves_stacks_revision_identity_and_duplicate_names() {
    let mut catalog = Catalog::default();
    let a = catalog.create_project("Same name").unwrap();
    let b = catalog.create_project("Same name").unwrap();
    let folder = catalog.create_folder(a, "Same name").unwrap();
    let child = catalog.create_folder(folder, "Same name").unwrap();
    let stack = catalog
        .create_stack(child, "Same name", draft("source"))
        .unwrap();
    catalog
        .add_revision(stack, run("saved", "source", 7))
        .unwrap();
    assert_ne!(
        a, b,
        "fixture must use distinct objects with duplicate labels"
    );
    catalog.move_node(folder, Some(b)).unwrap();
    catalog.rename(b, "Another project").unwrap();
    catalog.rename(stack, "任意の名前 🐝").unwrap();
    assert_eq!(catalog.node(folder).unwrap().parent, Some(b));
    assert_eq!(catalog.node(stack).unwrap().parent, Some(child));
    assert_eq!(catalog.node(stack).unwrap().name, "任意の名前 🐝");
    assert_eq!(
        catalog.latest_run(stack).unwrap().output,
        PathBuf::from("saved/photo.tiff")
    );
    assert_eq!(
        catalog.latest_run(stack).unwrap().source,
        PathBuf::from("source")
    );
    assert!(catalog.breadcrumb(stack).starts_with("Another project /"));
    catalog.validate().unwrap();
}

#[test]
fn illegal_moves_are_atomic_and_cannot_make_cycles_or_children_of_stacks() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Project").unwrap();
    let parent = catalog.create_folder(project, "Parent").unwrap();
    let child = catalog.create_folder(parent, "Child").unwrap();
    let leaf = catalog
        .create_stack(child, "Stack", draft("source"))
        .unwrap();
    let before = serde_json::to_vec(&catalog).unwrap();
    for (id, target) in [
        (parent, Some(child)),
        (parent, Some(parent)),
        (child, Some(leaf)),
        (child, Some(999)),
        (leaf, None),
        (project, Some(child)),
    ] {
        assert!(
            catalog.move_node(id, target).is_err(),
            "illegal move {id:?} → {target:?} must fail"
        );
        assert_eq!(
            serde_json::to_vec(&catalog).unwrap(),
            before,
            "failed move must not partially mutate the tree"
        );
    }
    assert!(
        catalog
            .create_stack(leaf, "Nested stack", draft("second-source"))
            .is_err()
    );
    assert!(catalog.create_folder(leaf, "Nested folder").is_err());
    catalog.validate().unwrap();
}

#[test]
fn legacy_run_migration_groups_exact_sources_not_names_and_is_idempotent() {
    let mut catalog = Catalog::default();
    // Same directory basename and run display label must not conflate captures.
    catalog.add(run("oldest", "first/capture", 5));
    catalog.add(run("unrelated", "second/capture", 6));
    catalog.add(run("newest", "first/capture", 7));
    let evidence: Vec<_> = catalog
        .runs
        .iter()
        .map(|r| serde_json::to_vec(r).unwrap())
        .collect();
    catalog.migrate_runs().unwrap();
    assert_eq!(
        catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Project)
            .count(),
        1
    );
    assert_eq!(
        catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Stack)
            .count(),
        2
    );
    let first = catalog.stack_for_run(Path::new("oldest")).unwrap();
    assert_eq!(catalog.stack_for_run(Path::new("newest")), Some(first));
    assert_ne!(catalog.stack_for_run(Path::new("unrelated")), Some(first));
    assert_eq!(
        catalog.node(first).unwrap().revisions,
        [PathBuf::from("oldest"), PathBuf::from("newest")]
    );
    assert_eq!(
        catalog
            .node(first)
            .unwrap()
            .stack
            .as_ref()
            .unwrap()
            .settings
            .pyramid_bands,
        Some(7)
    );
    assert_eq!(
        catalog
            .runs
            .iter()
            .map(|r| serde_json::to_vec(r).unwrap())
            .collect::<Vec<_>>(),
        evidence
    );
    let migrated = serde_json::to_vec(&catalog).unwrap();
    catalog.migrate_runs().unwrap();
    assert_eq!(serde_json::to_vec(&catalog).unwrap(), migrated);
    catalog.validate().unwrap();
}

#[test]
fn project_revisions_do_not_disappear_at_the_old_recent_history_limit() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Long-lived project").unwrap();
    let stack = catalog
        .create_stack(project, "Continuous refinement", draft("source"))
        .unwrap();
    for index in 0..140 {
        catalog
            .add_revision(stack, run(&format!("render-{index}"), "source", 7))
            .unwrap();
    }
    assert_eq!(catalog.node(stack).unwrap().revisions.len(), 140);
    assert_eq!(
        catalog.runs.len(),
        140,
        "128-entry recent history policy cannot erase project evidence"
    );
    assert!(
        catalog
            .runs
            .iter()
            .any(|r| r.directory == Path::new("render-0"))
    );
    let other = catalog
        .create_stack(project, "Separate capture", draft("other"))
        .unwrap();
    let existing = catalog.runs[0].clone();
    assert!(
        catalog.add_revision(other, existing).is_err(),
        "same output cannot acquire a different owner"
    );
    catalog.validate().unwrap();
}

#[test]
fn missing_parent_duplicate_ids_and_cycles_are_not_accepted_as_valid_projects() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Project").unwrap();
    let folder = catalog.create_folder(project, "Folder").unwrap();
    let child = catalog.create_folder(folder, "Child").unwrap();
    catalog.validate().unwrap();
    catalog.node_mut(folder).unwrap().parent = Some(child);
    assert!(
        catalog.validate().is_err(),
        "valid-looking JSON containing a cycle must fail"
    );
    catalog.node_mut(folder).unwrap().parent = Some(7777);
    assert!(catalog.validate().is_err(), "orphaned parent must fail");
    catalog.node_mut(folder).unwrap().parent = Some(project);
    catalog.node_mut(child).unwrap().id = project;
    assert!(catalog.validate().is_err(), "duplicate ids must fail");
}

#[test]
fn invalid_names_do_not_commit_partial_edits_and_unicode_names_roundtrip() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("色 · garden 🐝").unwrap();
    for invalid in [
        String::new(),
        "  ".into(),
        "line\nline".into(),
        "a".repeat(161),
    ] {
        assert!(catalog.rename(project, &invalid).is_err());
        assert_eq!(catalog.node(project).unwrap().name, "色 · garden 🐝");
    }
    let json = serde_json::to_vec(&catalog).unwrap();
    let restored: Catalog = serde_json::from_slice(&json).unwrap();
    assert_eq!(restored.node(project).unwrap().name, "色 · garden 🐝");
    restored.validate().unwrap();
}

#[test]
fn selecting_a_stack_targets_its_parent_for_the_next_capture() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Project").unwrap();
    let folder = catalog.create_folder(project, "Session").unwrap();
    let stack = catalog
        .create_stack(folder, "Capture", draft("source"))
        .unwrap();
    assert_eq!(catalog.selected, Some(stack));
    assert_eq!(catalog.selected_container(), Some(folder));
    catalog.selected = Some(project);
    assert_eq!(catalog.selected, Some(project));
    assert_eq!(catalog.selected_container(), Some(project));
}

#[test]
fn stale_identity_counter_cannot_reuse_existing_object_ids() {
    let mut catalog = Catalog::default();
    let first = catalog.create_project("A").unwrap();
    catalog.next_node_id = 0;
    let second = catalog.create_project("B").unwrap();
    assert_ne!(first, second);
    catalog.validate().unwrap();
}

#[test]
fn limited_render_still_requires_the_full_captures_identity_manifest() {
    let scan = jobs::StackScan {
        directory: PathBuf::from("capture"),
        frames: vec![
            jobs::FrameFile {
                path: PathBuf::from("capture/one.arw"),
                bytes: 100,
            },
            jobs::FrameFile {
                path: PathBuf::from("capture/two.arw"),
                bytes: 200,
            },
        ],
        total_bytes: 300,
    };
    let mut saved = run("limited", "capture", 7);
    saved.settings.frame_limit = Some(1);
    saved.frames = 1;
    assert!(
        saved.matches_scan(&scan),
        "a one-frame render retains the full bracket identity for browsing"
    );
    let mut altered = scan.clone();
    altered.frames[1].bytes += 1;
    assert!(
        !saved.matches_scan(&altered),
        "even an unrendered capture must match before the saved source browser is trusted"
    );
    saved.frames = 2;
    assert!(
        !saved.matches_scan(&scan),
        "stored render count must agree with its actual limit"
    );
}

#[test]
fn project_catalog_roundtrips_and_semantic_corruption_preserves_original_bytes() {
    let directory = std::env::temp_dir().join(format!(
        "strehl-project-roundtrip-{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&directory).unwrap();
    let path = directory.join("workspace.json");
    let mut catalog = Catalog::load(Some(path.clone()));
    let project = catalog.create_project("Field study").unwrap();
    let folder = catalog.create_folder(project, "Morning").unwrap();
    let stack = catalog
        .create_stack(folder, "Capture 1", draft("source"))
        .unwrap();
    catalog.node_mut(project).unwrap().notes =
        "Next capture: move the front focus plane forward.".into();
    catalog
        .add_revision(stack, run("first-render", "source", 7))
        .unwrap();
    catalog.save().unwrap();
    let saved = Catalog::load(Some(path.clone()));
    assert!(saved.load_error.is_none());
    assert_eq!(
        saved.nodes.len(),
        3,
        "reloading must not remigrate linked revisions into duplicates"
    );
    assert_eq!(saved.selected, Some(stack));
    assert_eq!(
        saved.node(project).unwrap().notes,
        catalog.node(project).unwrap().notes
    );
    assert_eq!(
        saved.latest_run(stack).unwrap().directory,
        PathBuf::from("first-render")
    );
    let mut malformed = serde_json::to_value(&saved).unwrap();
    malformed["nodes"][1]["parent"] = serde_json::json!(stack);
    let corrupt = serde_json::to_vec(&malformed).unwrap();
    std::fs::write(&path, &corrupt).unwrap();
    let refused = Catalog::load(Some(path.clone()));
    assert!(
        refused.load_error.is_some(),
        "valid JSON with a stack-parent tree defect must be refused"
    );
    assert!(refused.save().is_err());
    assert_eq!(
        std::fs::read(&path).unwrap(),
        corrupt,
        "a failed load must never overwrite recoverable history"
    );
    std::fs::remove_dir_all(directory).unwrap();
}

#[test]
fn redelivered_revision_cannot_overwrite_saved_recipe_or_user_name() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Project").unwrap();
    let stack = catalog
        .create_stack(project, "Capture", draft("source"))
        .unwrap();
    let original = run("existing-output", "source", 7);
    catalog.add_revision(stack, original.clone()).unwrap();
    catalog.runs[0].label = "Carefully named".into();
    catalog.runs[0].pinned = true;
    let mut replayed = original.clone();
    replayed.status = "Rendering".into();
    catalog.add_revision(stack, replayed).unwrap();
    assert_eq!(catalog.runs[0].label, "Carefully named");
    assert_eq!(catalog.runs[0].status, "Saved");
    assert!(catalog.runs[0].pinned);
    let before = serde_json::to_vec(&catalog).unwrap();
    let mut wrong = original;
    wrong.settings.pyramid_bands = Some(3);
    assert!(
        catalog.add_revision(stack, wrong).is_err(),
        "same output identity with another recipe must fail"
    );
    assert_eq!(serde_json::to_vec(&catalog).unwrap(), before);
}

#[test]
fn catalog_read_and_save_share_the_same_boundary_and_refused_save_is_non_destructive() {
    let directory = std::env::temp_dir().join(format!(
        "strehl-project-boundary-{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&directory).unwrap();
    let path = directory.join("workspace.json");
    let mut catalog = Catalog::load(Some(path.clone()));
    catalog.create_project("Boundary witness").unwrap();
    let exact = serde_json::to_vec_pretty(&catalog).unwrap().len();
    catalog.save_with_limit(exact).unwrap();
    let original = std::fs::read(&path).unwrap();
    assert_eq!(read_catalog_bytes(&path, exact).unwrap(), original);
    assert!(
        read_catalog_bytes(&path, exact - 1).is_err(),
        "read must fail on the first byte beyond the declared limit"
    );
    assert!(
        catalog.save_with_limit(exact - 1).is_err(),
        "write must fail at the same bound as read"
    );
    assert_eq!(std::fs::read(&path).unwrap(), original);
    assert_eq!(
        std::fs::read_dir(&directory).unwrap().count(),
        1,
        "refused publication must not leave a misleading temporary workspace"
    );
    std::fs::remove_dir_all(directory).unwrap();
}

fn migration_directory() -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "strehl-project-migration-{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&path).unwrap();
    path
}

#[test]
fn new_project_library_migrates_legacy_workspace_without_modifying_it() {
    let directory = migration_directory();
    let legacy = directory.join("workspace.json");
    let destination = directory.join("projects.json");
    let old = serde_json::to_vec_pretty(
        &serde_json::json!({"runs":[run("legacy-render","legacy-capture",7)]}),
    )
    .unwrap();
    std::fs::write(&legacy, &old).unwrap();
    let migrated = Catalog::load(Some(destination.clone()));
    assert!(migrated.load_error.is_none());
    assert_eq!(migrated.runs.len(), 1);
    assert!(migrated.stack_for_run(Path::new("legacy-render")).is_some());
    assert_eq!(migrated.path, Some(destination.clone()));
    migrated.save().unwrap();
    assert!(destination.is_file());
    assert_eq!(
        std::fs::read(&legacy).unwrap(),
        old,
        "v18 must retain its original catalog"
    );
    let reopened = Catalog::load(Some(destination));
    assert_eq!(reopened.nodes.len(), migrated.nodes.len());
    assert_eq!(
        reopened.runs.len(),
        1,
        "saved migration must not create another imported project"
    );
    std::fs::remove_dir_all(directory).unwrap();
}

#[test]
fn existing_project_library_takes_precedence_over_later_legacy_writes() {
    let directory = migration_directory();
    let destination = directory.join("projects.json");
    let legacy = directory.join("workspace.json");
    let mut current = Catalog::load(Some(destination.clone()));
    let project = current.create_project("Ongoing project").unwrap();
    current.save().unwrap();
    std::fs::write(
        &legacy,
        serde_json::to_vec(
            &serde_json::json!({"runs":[run("old-app-new-render","other-capture",5)]}),
        )
        .unwrap(),
    )
    .unwrap();
    let loaded = Catalog::load(Some(destination));
    assert_eq!(loaded.node(project).unwrap().name, "Ongoing project");
    assert!(
        loaded.runs.is_empty(),
        "reopening v18 must not replace or reimport into the new project library"
    );
    std::fs::remove_dir_all(directory).unwrap();
}

#[test]
fn corrupt_project_library_never_falls_back_to_legacy_or_overwrites_either_file() {
    let directory = migration_directory();
    let destination = directory.join("projects.json");
    let legacy = directory.join("workspace.json");
    let old =
        serde_json::to_vec(&serde_json::json!({"runs":[run("old-render","capture",7)]})).unwrap();
    let damaged = b"{broken-project-tree-but-recoverable";
    std::fs::write(&legacy, &old).unwrap();
    std::fs::write(&destination, damaged).unwrap();
    let loaded = Catalog::load(Some(destination.clone()));
    assert!(loaded.load_error.is_some());
    assert!(
        loaded.runs.is_empty(),
        "corrupt project library is not permission to substitute old data"
    );
    assert!(loaded.save().is_err());
    assert_eq!(std::fs::read(&destination).unwrap(), damaged);
    assert_eq!(std::fs::read(&legacy).unwrap(), old);
    std::fs::remove_dir_all(directory).unwrap();
}
