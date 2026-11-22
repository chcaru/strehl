//! Library removal: what leaves with a subject or stack, exact restoration,
//! the undo journal, merging, and which files a removed entry owns.
use super::*;
use crate::library_station::tests::{catalog as library_catalog, draft, run};
use crate::project_explorer::ProjectExplorer;
use crate::workspace_history::{SourceIdentity, StackDraft};

fn subject_named(catalog: &Catalog, name: &str) -> NodeId {
    catalog
        .nodes
        .iter()
        .find(|n| n.kind == NodeKind::Subject && n.name == name)
        .map(|n| n.id)
        .unwrap()
}
/// Everything removal touches, comparable.
fn state(catalog: &Catalog) -> serde_json::Value {
    serde_json::json!({
        "nodes": catalog.nodes,
        "runs": catalog.runs,
        "versions": catalog.photo_versions,
        "exports": catalog.photo_exports,
        "directories": catalog.export_directories,
        "descriptions": catalog.photo_descriptions,
        "selected": catalog.selected,
    })
}

#[test]
fn a_removed_subject_takes_its_stacks_renders_versions_and_exports_and_comes_back_exactly() {
    // Subject 003 has a saved render, a version and an export.
    let mut catalog = library_catalog(8, None);
    let subject = subject_named(&catalog, "Subject 003");
    let stack = catalog.stacks_of(subject)[0];
    let output = catalog
        .runs
        .iter()
        .find(|r| catalog.stack_for_run(&r.directory) == Some(stack))
        .unwrap()
        .output
        .clone();
    catalog
        .export_directories
        .insert(output.clone(), PathBuf::from("/exports/elsewhere"));
    // The photograph's export description (h-develop) leaves and returns too.
    catalog
        .photo_descriptions
        .insert(output.clone(), "Weevil on moss".into());
    catalog.selected = Some(stack);
    let before = state(&catalog);
    let scope = catalog.removal_scope(&[subject]);
    assert_eq!(scope.subjects, vec![subject]);
    assert_eq!(scope.stacks, vec![stack]);
    let counts = catalog.removal_counts(&scope);
    assert_eq!(
        (
            counts.subjects,
            counts.stacks,
            counts.renders,
            counts.versions,
            counts.exports
        ),
        (1, 1, 1, 1, 1)
    );
    let records = catalog.remove_nodes(&scope.ids()).unwrap();
    assert_eq!((records.subjects(), records.stacks()), (1, 1));
    assert!(catalog.node(subject).is_none() && catalog.node(stack).is_none());
    assert!(!catalog.runs.iter().any(|r| r.output == output));
    assert!(
        !catalog
            .photo_versions
            .iter()
            .any(|v| v.owner.stack == Some(stack))
    );
    assert_eq!(catalog.photo_exports.len(), 1, "subject 007's export stays");
    assert!(!catalog.export_directories.contains_key(&output));
    assert!(!catalog.photo_descriptions.contains_key(&output));
    // The selection falls back to the removed item's container.
    assert!(
        catalog
            .selected
            .is_some_and(|id| catalog.node(id).is_some())
    );
    catalog.validate().unwrap();
    catalog.restore_nodes(&records).unwrap();
    assert_eq!(state(&catalog), before, "restored exactly, order included");
    // A second restore is refused and changes nothing.
    assert!(catalog.restore_nodes(&records).is_err());
    assert_eq!(state(&catalog), before);
}

#[test]
fn a_subject_cannot_leave_without_its_stacks_and_a_refusal_changes_nothing() {
    let mut catalog = library_catalog(4, None);
    let subject = subject_named(&catalog, "Subject 001");
    let before = state(&catalog);
    let error = catalog.remove_nodes(&[subject]).unwrap_err().to_string();
    assert!(error.contains("without its subject"), "{error}");
    let collection = catalog.nodes[0].id;
    assert!(
        catalog.remove_nodes(&[collection]).is_err(),
        "collections are not removed here"
    );
    assert!(catalog.remove_nodes(&[]).is_err());
    assert_eq!(state(&catalog), before);
    // A kept stack keeps its subject in the library too.
    let stack = catalog.stacks_of(subject)[0];
    let scope = catalog.removal_scope(&[subject]);
    let kept = catalog.scope_without(&scope, &[stack]);
    assert!(kept.is_empty(), "{kept:?}");
}

#[test]
fn removed_renders_do_not_come_back_as_imported_stacks_on_the_next_load() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("projects.json");
    let mut catalog = library_catalog(8, None);
    let subject = subject_named(&catalog, "Subject 002");
    let scope = catalog.removal_scope(&[subject]);
    let runs_before = catalog.runs.len();
    catalog.remove_nodes(&scope.ids()).unwrap();
    assert_eq!(
        catalog.runs.len(),
        runs_before - 2,
        "both renders of subject 002"
    );
    std::fs::write(&path, serde_json::to_vec(&catalog).unwrap()).unwrap();
    let reloaded = Catalog::load(Some(path));
    assert!(reloaded.load_error.is_none(), "{:?}", reloaded.load_error);
    assert!(
        !reloaded.nodes.iter().any(|n| n.name == "Imported stacks"),
        "no render is left without its stack"
    );
    assert_eq!(reloaded.nodes.len(), catalog.nodes.len());
}

#[test]
fn undo_puts_a_removal_back_and_redo_takes_it_out_again_without_ending_the_history() {
    let mut catalog = library_catalog(6, None);
    let mut explorer = ProjectExplorer::default();
    // An ordinary edit first: the removal must not end its history.
    let first = subject_named(&catalog, "Subject 000");
    explorer
        .organize(&mut catalog, |c| c.rename(first, "Renamed"))
        .unwrap();
    let before = state(&catalog);
    let subject = subject_named(&catalog, "Subject 003");
    let ids = catalog.removal_scope(&[subject]).ids();
    let (_, records) = explorer
        .organize_removing(&mut catalog, |_| Ok(((), ids.clone())))
        .unwrap();
    assert_eq!(records.stacks(), 1);
    assert_eq!(explorer.history_depths(), (2, 0));
    let removed = state(&catalog);
    assert!(explorer.undo(&mut catalog));
    assert_eq!(state(&catalog), before);
    assert_eq!(explorer.history_depths(), (1, 1));
    assert!(explorer.redo(&mut catalog));
    assert_eq!(state(&catalog), removed);
    assert!(explorer.undo(&mut catalog));
    assert_eq!(state(&catalog), before);
    // The rename beneath is still undoable.
    assert!(explorer.undo(&mut catalog));
    assert_eq!(catalog.node(first).unwrap().name, "Subject 000");
    // An outside change to the stacks (a new render) still ends the history.
    assert!(explorer.redo(&mut catalog));
    let stack = catalog.stacks_of(first)[0];
    catalog
        .add_revision(
            stack,
            run("/out/strehl-90-1-1", "/captures/s000/100MSDCF", "Saved", 9),
        )
        .unwrap();
    assert!(
        !explorer.undo(&mut catalog),
        "history ended by the new render"
    );
}

#[test]
fn merging_moves_the_stacks_appends_notes_fills_metadata_and_undoes_in_one_step() {
    let mut catalog = library_catalog(8, None);
    let into = subject_named(&catalog, "Subject 001");
    let other = subject_named(&catalog, "Subject 007");
    let moved = catalog.stacks_of(other);
    let mut explorer = ProjectExplorer::default();
    let before = state(&catalog);
    let (count, records) = explorer
        .organize_removing(&mut catalog, |c| {
            let emptied = c.merge_subjects(into, &[other, into])?;
            Ok((emptied.len(), emptied))
        })
        .unwrap();
    assert_eq!(count, 1, "the subject itself is skipped");
    assert_eq!(records.subjects(), 1);
    assert!(catalog.node(other).is_none());
    for stack in &moved {
        assert_eq!(catalog.subject_of(*stack), Some(into));
    }
    let node = catalog.node(into).unwrap();
    assert!(node.notes.contains("Found under the oak bark."));
    assert_eq!(
        node.subject
            .as_ref()
            .unwrap()
            .optics
            .as_ref()
            .unwrap()
            .camera,
        "ILCE-7CR",
        "optics the target lacked"
    );
    catalog.validate().unwrap();
    assert!(explorer.undo(&mut catalog));
    assert_eq!(state(&catalog), before);
    assert!(explorer.redo(&mut catalog));
    assert!(catalog.node(other).is_none());
    assert_eq!(catalog.subject_of(moved[0]), Some(into));
    // Merging into a stack, or nothing, is refused.
    assert!(catalog.merge_subjects(moved[0], &[into]).is_err());
    assert!(catalog.merge_subjects(into, &[into]).is_err());
}

fn recorded(folder: &Path, names: &[&str]) -> StackDraft {
    let mut draft = draft(&folder.to_string_lossy(), 0);
    draft.sources = names
        .iter()
        .map(|name| SourceIdentity {
            path: folder.join(name),
            bytes: 10,
            modified_ns: None,
        })
        .collect();
    draft
}
fn job_run(directory: &Path, source: &Path) -> Run {
    let mut run = run(
        &directory.to_string_lossy(),
        &source.to_string_lossy(),
        "Saved",
        5,
    );
    run.output = directory.join("result.tiff");
    run.log = directory.join("render.log");
    run
}

#[test]
fn owned_files_are_strehl_job_folders_and_recorded_photographs_and_nothing_shared() {
    let root = tempfile::tempdir().unwrap();
    let root = root.path();
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let captures = root.join("captures");
    let out = root.join("out");
    // Owned: its own folder, recorded photographs inside it, a job folder.
    let own = catalog
        .create_stack(
            subject,
            "Dorsal",
            recorded(&captures.join("dorsal"), &["a.ARW", "b.ARW"]),
        )
        .unwrap();
    catalog
        .add_revision(
            own,
            job_run(&out.join("strehl-100-1-1"), &captures.join("dorsal")),
        )
        .unwrap();
    // A render folder not named like a job folder.
    catalog
        .add_revision(
            own,
            job_run(&out.join("my renders"), &captures.join("dorsal")),
        )
        .unwrap();
    // Records a photograph outside its folder.
    let mut outside = recorded(&captures.join("lateral"), &["a.ARW"]);
    outside.sources.push(SourceIdentity {
        path: captures.join("elsewhere").join("x.ARW"),
        bytes: 10,
        modified_ns: None,
    });
    let stray = catalog.create_stack(subject, "Lateral", outside).unwrap();
    // Shares its photographs with a stack that stays.
    let shared = catalog
        .create_stack(
            subject,
            "Wing",
            recorded(&captures.join("wing"), &["a.ARW"]),
        )
        .unwrap();
    let other = catalog.create_subject(project, "Other").unwrap();
    catalog
        .create_stack(
            other,
            "Wing again",
            recorded(&captures.join("wing"), &["a.ARW"]),
        )
        .unwrap();
    let scope = catalog.removal_scope(&[own, stray, shared]);
    let owned = catalog.owned_files(&scope);
    assert_eq!(
        owned.renders,
        vec![OwnedRender {
            stack: own,
            directory: out.join("strehl-100-1-1")
        }]
    );
    assert_eq!(owned.sources.len(), 1, "{owned:?}");
    assert_eq!(owned.sources[0].folder, captures.join("dorsal"));
    assert_eq!(owned.sources[0].files.len(), 2);
    let reasons: Vec<&str> = owned.refused.iter().map(|r| r.reason.as_str()).collect();
    assert!(
        reasons
            .iter()
            .any(|r| r.contains("not named like a Strehl render folder")),
        "{reasons:?}"
    );
    assert!(
        reasons.iter().any(|r| r.contains("outside its folder")),
        "{reasons:?}"
    );
    assert!(
        reasons
            .iter()
            .any(|r| r.contains("also the sources of \"Wing again\"")),
        "{reasons:?}"
    );
    // Removing both stacks of the shared folder makes it theirs: one claim.
    let both = catalog.removal_scope(&[shared, other]);
    let owned = catalog.owned_files(&both);
    assert_eq!(owned.sources.len(), 1, "{owned:?}");
    assert_eq!(owned.sources[0].folder, captures.join("wing"));
}

#[test]
fn a_render_folder_holding_another_stacks_record_or_an_imported_session_is_refused() {
    let root = tempfile::tempdir().unwrap();
    let root = root.path();
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let job = root.join("out").join("strehl-100-1-1");
    let leaving = catalog
        .create_stack(subject, "Dorsal", recorded(&root.join("a"), &["a.ARW"]))
        .unwrap();
    catalog
        .add_revision(leaving, job_run(&job, &root.join("a")))
        .unwrap();
    // A stack that stays records photographs inside that job folder.
    catalog
        .create_stack(subject, "Odd", recorded(&job.join("copies"), &["a.ARW"]))
        .unwrap();
    let mut imported = job_run(&root.join("out").join("strehl-200-1-2"), &root.join("b"));
    imported.imported = Some(crate::session_import::ImportedSession {
        imported_at: 1,
        renderer_bound: false,
        renderer_build: None,
        files: Default::default(),
        diagnostic_warnings: Vec::new(),
    });
    let session = catalog
        .create_stack(subject, "Session", recorded(&root.join("b"), &["a.ARW"]))
        .unwrap();
    catalog.add_revision(session, imported).unwrap();
    let owned = catalog.owned_files(&catalog.removal_scope(&[leaving, session]));
    assert!(owned.renders.is_empty(), "{owned:?}");
    let reasons: Vec<&str> = owned.refused.iter().map(|r| r.reason.as_str()).collect();
    assert!(
        reasons
            .iter()
            .any(|r| r.contains("holds photographs of \"Odd\"")),
        "{reasons:?}"
    );
    assert!(
        reasons.iter().any(|r| r.contains("imported session")),
        "{reasons:?}"
    );
}

#[test]
fn exports_inside_a_deleted_render_folder_are_counted_apart_from_those_kept() {
    let root = tempfile::tempdir().unwrap();
    let root = root.path();
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let job = root.join("out").join("strehl-100-1-1");
    let stack = catalog
        .create_stack(subject, "Dorsal", recorded(&root.join("a"), &["a.ARW"]))
        .unwrap();
    let mut render = job_run(&job, &root.join("a"));
    // `develop` records the photograph as `photograph.tiff`.
    render.output = job.join("photograph.tiff");
    catalog.add_revision(stack, render).unwrap();
    crate::library_station::tests::develop(&mut catalog, stack, &job.to_string_lossy(), 1, 50);
    let mut inside = catalog.photo_exports[0].clone();
    inside.id = format!("{:031x}f", 77);
    inside.path = job.join("export.png");
    catalog.photo_exports.push(inside);
    let owned = catalog.owned_files(&catalog.removal_scope(&[subject]));
    assert_eq!(owned.renders.len(), 1, "{owned:?}");
    assert_eq!((owned.exports_inside, owned.exports_kept), (1, 1));
}

/// How long the confirmation's catalog work takes on the UI thread, per
/// subject of a copy of the owner's catalog (`STREHL_P4_CATALOG`). Nothing is
/// removed from the file: the copy is loaded, planned against and dropped.
#[test]
#[ignore = "reads a copy of the owner's catalog named by STREHL_P4_CATALOG"]
fn owner_catalog_copy_delete_plans_are_cheap() {
    let path = PathBuf::from(std::env::var_os("STREHL_P4_CATALOG").expect("STREHL_P4_CATALOG"));
    let catalog = Catalog::load(Some(path));
    assert!(catalog.load_error.is_none(), "{:?}", catalog.load_error);
    let subjects: Vec<NodeId> = catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject)
        .map(|n| n.id)
        .collect();
    let mut worst = std::time::Duration::ZERO;
    let mut owned_renders = 0;
    let mut owned_sources = 0;
    let mut refused = 0;
    let mut reasons = std::collections::BTreeMap::<String, usize>::new();
    for &subject in &subjects {
        let started = std::time::Instant::now();
        let scope = catalog.removal_scope(&[subject]);
        let _ = catalog.removal_counts(&scope);
        let owned = catalog.owned_files(&scope);
        worst = worst.max(started.elapsed());
        owned_renders += owned.renders.len();
        owned_sources += owned.sources.len();
        refused += owned.refused.len();
        for refusal in &owned.refused {
            *reasons.entry(refusal.reason.clone()).or_default() += 1;
        }
    }
    eprintln!("owner-copy: refusals by reason {reasons:?}");
    let started = std::time::Instant::now();
    let all = catalog.removal_scope(&subjects);
    let owned = catalog.owned_files(&all);
    let everything = started.elapsed();
    eprintln!(
        "owner-copy: {} subjects; worst single plan {:?}; all at once {:?} ({} render folders, {} source folders, {} refused); per subject: {} render folders, {} source folders, {} refused",
        subjects.len(),
        worst,
        everything,
        owned.renders.len(),
        owned.sources.len(),
        owned.refused.len(),
        owned_renders,
        owned_sources,
        refused
    );
}
