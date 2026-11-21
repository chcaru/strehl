//! Catalog format 2: subjects, the format-1 migration and its backup, the
//! hierarchy, undo, lifecycle, Locate and interrupted-run reconciliation.
//! Fixtures are synthetic; the owner's catalog is read only by the ignored
//! harness at the end, and only from a copy.
use super::*;
use crate::project_explorer::ProjectExplorer;
use serde_json::{Value, json};
use std::process::{Command, Stdio};

fn run_json(directory: &str, source: &str, status: &str, created: u64) -> Value {
    json!({
        "directory": directory, "source": source,
        "output": format!("{directory}/photograph.tiff"), "log": format!("{directory}/render.log"),
        "label": "render", "created": created, "status": status, "frames": 2,
        "sources": [{"path":format!("{source}/DSC00001.ARW"),"bytes":100},{"path":format!("{source}/DSC00002.ARW"),"bytes":200}],
        "settings": crate::jobs::RenderSettings::default(),
        "exposure": null, "gate": null, "workers": 4
    })
}
fn stack_json(id: u64, parent: u64, name: &str, source: &str, revisions: &[&str]) -> Value {
    json!({
        "id": id, "parent": parent, "name": name, "kind": "Stack",
        "stack": {"source": source, "sources": [{"path":format!("{source}/DSC00001.ARW"),"bytes":100}],
            "settings": crate::jobs::RenderSettings::default(), "exposure": null, "gate": null, "workers": 4},
        "revisions": revisions
    })
}
fn hex(c: char) -> String {
    std::iter::repeat_n(c, 64).collect()
}

/// Modelled on the owner's catalog (2026-11-21): two projects, camera-folder
/// stacks of several specimens, re-imports of one folder, a session named
/// after its camera folder, one specimen split across two projects, and a
/// folder. Format 1: no `format` key and no subjects.
fn owner_shaped_v1() -> Value {
    json!({
        "layout": {},
        "selected": 12,
        "next_node_id": 43,
        "nodes": [
            {"id": 1, "parent": null, "name": "Imported stacks", "kind": "Project"},
            stack_json(2, 1, "input", "/tests/v5-live-sample/input", &[]),
            stack_json(3, 1, "chia-seeds-cpl", "/macro/chia-seeds-cpl", &["/out/strehl-100-1-1", "/out/strehl-200-1-2"]),
            stack_json(4, 1, "tweezers-cpl", "/macro/tweezers-cpl", &[]),
            stack_json(5, 1, "102MSDCF", "/minerals/peacock-ore/102MSDCF", &[]),
            stack_json(6, 1, "chia-seeds-cpl", "/macro/chia-seeds-cpl", &[]),
            stack_json(11, 1, "103MSDCF", "/bugs/bug-1/103MSDCF", &[]),
            stack_json(12, 1, "104MSDCF", "/bugs/bug-1/104MSDCF", &["/out/strehl-300-1-3"]),
            stack_json(13, 1, "100MSDCF", "/bugs/bug-1/100MSDCF", &[]),
            stack_json(19, 1, "119MSDCF", "/macro/119MSDCF", &[]),
            stack_json(24, 1, "107MSDCF", "/bugs/bug-3/107MSDCF", &[]),
            stack_json(27, 1, "Session · 107MSDCF", "/bugs/bug-3/107MSDCF", &["/out/strehl-400-1-4"]),
            {"id": 28, "parent": null, "name": "Bugs", "kind": "Project", "expanded": false},
            stack_json(31, 28, "106MSDCF", "/bugs/bug-3/106MSDCF", &[]),
            stack_json(34, 28, "100MSDCF", "/bugs/bug-6/100MSDCF", &["/out/strehl-500-1-5"]),
            {"id": 40, "parent": 28, "name": "Older", "kind": "Folder"},
            stack_json(41, 40, "100MSDCF", "/bugs/bug-6/100MSDCF", &["/out/strehl-600-1-6"]),
            stack_json(42, 28, "100MSDCF", "/100MSDCF", &[]),
            stack_json(43, 28, "100MSDCF", "/card/DCIM/100MSDCF", &[])
        ],
        "runs": [
            run_json("/out/strehl-600-1-6", "/bugs/bug-6/100MSDCF", "Cancelled", 600),
            run_json("/out/strehl-500-1-5", "/bugs/bug-6/100MSDCF", "Saved", 500),
            run_json("/out/strehl-400-1-4", "/bugs/bug-3/107MSDCF", "Saved", 400),
            run_json("/out/strehl-300-1-3", "/bugs/bug-1/104MSDCF", "Saved", 300),
            run_json("/out/strehl-200-1-2", "/macro/chia-seeds-cpl", "Failed", 200),
            run_json("/out/strehl-100-1-1", "/macro/chia-seeds-cpl", "Saved", 100)
        ],
        "photo_versions": [{
            "id": "0123456789abcdef0123456789abcdef", "name": "Warm", "created": 310,
            "owner": {"stack": 12, "run": "/out/strehl-300-1-3", "output": "/out/strehl-300-1-3/photograph.tiff"},
            "photo": {"canonical_path": "/out/strehl-300-1-3/photograph.tiff", "bytes": 10, "dimensions": [4, 3], "sha256": hex('a')},
            "decoded_source": {"canonical_path": "/out/strehl-300-1-3/photograph.tiff", "bytes": 10, "dimensions": [4, 3], "sha256": hex('b')},
            "loaded_sha256": hex('c')
        }],
        "photo_exports": [{
            "id": "fedcba9876543210fedcba9876543210", "version": "0123456789abcdef0123456789abcdef",
            "path": "/exports/bug-1.png", "created": 320,
            "settings": {"format":"png","color_space":"srgb","hdr":false,"quality":100,"speed":6},
            "bytes": 10, "sha256": hex('d')
        }],
        "export_directories": {}
    })
}

fn write_fixture(directory: &Path, value: &Value) -> (PathBuf, Vec<u8>) {
    let path = directory.join("projects.json");
    let bytes = serde_json::to_vec_pretty(value).unwrap();
    std::fs::write(&path, &bytes).unwrap();
    (path, bytes)
}
fn subject_names(catalog: &Catalog, container: NodeId) -> Vec<String> {
    catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject && n.parent == Some(container))
        .map(|n| n.name.clone())
        .collect()
}
fn subject_name_of(catalog: &Catalog, stack: NodeId) -> String {
    catalog
        .node(
            catalog
                .subject_of(stack)
                .expect("every stack has a subject"),
        )
        .unwrap()
        .name
        .clone()
}
fn backups(directory: &Path) -> Vec<PathBuf> {
    let mut found: Vec<PathBuf> = std::fs::read_dir(directory)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| {
            p.file_name()
                .unwrap()
                .to_string_lossy()
                .starts_with("projects.v1-backup-")
        })
        .collect();
    found.sort();
    found
}
fn draft_at(source: &str) -> StackDraft {
    StackDraft {
        source: PathBuf::from(source),
        sources: Vec::new(),
        settings: crate::jobs::RenderSettings::default(),
        exposure: None,
        gate: None,
        workers: 4,
    }
}

#[test]
fn migration_groups_an_owner_shaped_catalog_into_subjects_and_loses_no_evidence() {
    let directory = tempfile::tempdir().unwrap();
    let original = owner_shaped_v1();
    let (path, _) = write_fixture(directory.path(), &original);
    // The same file read without migration: the evidence to preserve.
    let unmigrated: Catalog = serde_json::from_value(original.clone()).unwrap();
    assert_eq!(unmigrated.format, 1, "absent format reads as 1");
    let catalog = Catalog::load(Some(path));
    assert!(catalog.load_error.is_none(), "{:?}", catalog.load_error);
    assert_eq!(catalog.format, CATALOG_FORMAT);

    assert_eq!(
        subject_names(&catalog, 1),
        [
            "input",
            "chia-seeds-cpl",
            "tweezers-cpl",
            "peacock-ore",
            "bug-1",
            "macro",
            "bug-3"
        ],
        "camera folders take the folder above; re-imports of one folder share a subject; \
         subjects appear in their first stack's order"
    );
    assert_eq!(
        subject_names(&catalog, 28),
        ["bug-3", "bug-6", "100MSDCF", "100MSDCF"],
        "a specimen split across projects keeps one subject per project; a drive root \
         or DCIM names nothing, so those stacks keep their own names"
    );
    assert_eq!(subject_names(&catalog, 40), ["bug-6"]);
    assert_eq!(
        catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Subject)
            .count(),
        12
    );
    for (stack, subject) in [
        (3, "chia-seeds-cpl"),
        (6, "chia-seeds-cpl"),
        (11, "bug-1"),
        (12, "bug-1"),
        (13, "bug-1"),
        (19, "macro"),
        (24, "bug-3"),
        (27, "bug-3"),
        (5, "peacock-ore"),
    ] {
        assert_eq!(subject_name_of(&catalog, stack), subject, "stack {stack}");
    }
    assert_eq!(catalog.subject_of(3), catalog.subject_of(6));
    assert_eq!(catalog.subject_of(24), catalog.subject_of(27));
    assert_ne!(
        catalog.subject_of(24),
        catalog.subject_of(31),
        "Bugs keeps its own bug-3 subject"
    );
    assert_ne!(catalog.subject_of(34), catalog.subject_of(41));
    assert_ne!(catalog.subject_of(42), catalog.subject_of(43));
    // Each subject sits where its stacks were, before its first stack.
    for subject in catalog.nodes.iter().filter(|n| n.kind == NodeKind::Subject) {
        let stacks = catalog.stacks_of(subject.id);
        assert!(!stacks.is_empty());
        let container = unmigrated.node(stacks[0]).unwrap().parent;
        assert_eq!(subject.parent, container);
        for stack in &stacks {
            assert_eq!(unmigrated.node(*stack).unwrap().parent, container);
        }
        let position = |id| catalog.nodes.iter().position(|n| n.id == id).unwrap();
        assert!(position(subject.id) < position(stacks[0]));
    }
    // Subject dates come from their earliest render or recorded capture;
    // with neither the subject has no date, never the migration time.
    let created = |stack| {
        catalog
            .node(catalog.subject_of(stack).unwrap())
            .unwrap()
            .subject
            .as_ref()
            .unwrap()
            .created
    };
    assert_eq!(created(6), 100);
    assert_eq!(created(13), 300);
    assert_eq!(created(41), 600);
    assert_eq!(created(4), 0);

    // No run, version or export changed; every stack keeps its id and renders.
    assert_eq!(
        serde_json::to_value(&catalog.runs).unwrap(),
        serde_json::to_value(&unmigrated.runs).unwrap()
    );
    assert_eq!(catalog.photo_versions, unmigrated.photo_versions);
    assert_eq!(
        serde_json::to_value(&catalog.photo_exports).unwrap(),
        serde_json::to_value(&unmigrated.photo_exports).unwrap()
    );
    for run in &unmigrated.runs {
        assert_eq!(
            catalog.stack_for_run(&run.directory),
            unmigrated.stack_for_run(&run.directory)
        );
    }
    for old in &unmigrated.nodes {
        let new = catalog.node(old.id).unwrap();
        assert_eq!(new.kind, old.kind);
        assert_eq!(new.name, old.name);
        assert_eq!(new.revisions, old.revisions);
        assert_eq!(new.expanded, old.expanded);
        assert_eq!(
            serde_json::to_value(&new.stack).unwrap(),
            serde_json::to_value(&old.stack).unwrap()
        );
    }
    assert_eq!(catalog.selected, Some(12), "selection survives migration");
    assert!(
        !catalog.node(28).unwrap().expanded,
        "a collapsed project stays collapsed"
    );
    assert_eq!(
        catalog.photo_owner(Path::new("/out/strehl-300-1-3/photograph.tiff")),
        catalog.photo_versions[0].owner
    );
    catalog.validate().unwrap();
}

#[test]
fn migration_is_idempotent_and_a_saved_format_two_catalog_reloads_unchanged() {
    let directory = tempfile::tempdir().unwrap();
    let (path, _) = write_fixture(directory.path(), &owner_shaped_v1());
    let mut catalog = Catalog::load(Some(path.clone()));
    let migrated = serde_json::to_vec(&catalog).unwrap();
    catalog.migrate_subjects().unwrap();
    catalog.migrate_runs().unwrap();
    assert_eq!(serde_json::to_vec(&catalog).unwrap(), migrated);
    catalog.save().unwrap();
    let saved: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    assert_eq!(saved["format"], 2);
    assert!(
        saved["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|n| n["kind"] != "Subject")
            .all(|n| n.get("subject").is_none()),
        "only subjects carry subject metadata"
    );
    let reloaded = Catalog::load(Some(path.clone()));
    assert!(reloaded.load_error.is_none());
    assert_eq!(serde_json::to_vec(&reloaded).unwrap(), migrated);
    // A stack placed directly in a project after migration (a format-1
    // placement) joins the subject of its folder instead of founding another.
    let mut later = reloaded;
    let added = later
        .create_stack(1, "105MSDCF", draft_at("/bugs/bug-1/105MSDCF"))
        .unwrap();
    later.save().unwrap();
    let again = Catalog::load(Some(path));
    assert_eq!(again.subject_of(added), again.subject_of(13));
    assert_eq!(
        again
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Subject)
            .count(),
        12
    );
}

#[test]
fn first_format_two_save_writes_one_verified_backup_of_the_exact_format_one_bytes() {
    let directory = tempfile::tempdir().unwrap();
    let (path, original) = write_fixture(directory.path(), &owner_shaped_v1());
    let mut catalog = Catalog::load(Some(path.clone()));
    assert!(
        backups(directory.path()).is_empty(),
        "loading alone writes nothing"
    );
    assert_eq!(std::fs::read(&path).unwrap(), original);
    catalog.save().unwrap();
    let written = backups(directory.path());
    assert_eq!(written.len(), 1);
    assert_eq!(catalog.legacy_backup().as_ref(), Some(&written[0]));
    let backup = std::fs::read(&written[0]).unwrap();
    assert_eq!(
        backup, original,
        "the backup is the format-1 file, byte for byte"
    );
    let reread: Catalog = serde_json::from_slice(&backup).unwrap();
    assert_eq!(reread.format, 1);
    reread.validate().unwrap();
    assert!(
        !reread.nodes.iter().any(|n| n.kind == NodeKind::Subject),
        "the backup holds no subjects"
    );
    // Later saves, in this window or after a reload, never back up again.
    catalog.rename(1, "Imported").unwrap();
    catalog.save().unwrap();
    let mut reloaded = Catalog::load(Some(path.clone()));
    reloaded.rename(1, "Imported again").unwrap();
    reloaded.save().unwrap();
    assert_eq!(backups(directory.path()), written);
    assert!(reloaded.legacy_backup().is_none());
    // A brand-new library has nothing to back up.
    let fresh = tempfile::tempdir().unwrap();
    let mut new = Catalog::load(Some(fresh.path().join("projects.json")));
    new.create_project("First").unwrap();
    new.save().unwrap();
    assert!(backups(fresh.path()).is_empty());
}

#[test]
fn a_backup_that_does_not_read_back_as_a_format_one_library_refuses_the_save() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("projects.json");
    for bytes in [&b"{not json"[..], br#"{"format":2}"#] {
        let error = subjects::write_legacy_backup(&path, bytes).unwrap_err();
        assert!(error.to_string().contains("nothing was saved"), "{error}");
        assert!(
            backups(directory.path()).is_empty(),
            "a failed backup leaves no partial copy"
        );
    }
    let good = br#"{"nodes":[]}"#;
    let backup = subjects::write_legacy_backup(&path, good).unwrap();
    let second = subjects::write_legacy_backup(&path, good).unwrap();
    assert_ne!(backup, second, "an existing backup is never overwritten");
    assert_eq!(std::fs::read(&backup).unwrap(), good);
}

#[test]
fn unknown_kinds_and_newer_formats_fail_to_load_and_the_file_is_never_rewritten() {
    let directory = tempfile::tempdir().unwrap();
    let mut unknown = owner_shaped_v1();
    unknown["nodes"][1]["kind"] = json!("Specimen");
    let mut newer = owner_shaped_v1();
    newer["format"] = json!(3);
    for value in [unknown, newer] {
        let (path, bytes) = write_fixture(directory.path(), &value);
        let catalog = Catalog::load(Some(path.clone()));
        assert!(catalog.load_error.is_some());
        assert!(
            catalog.save().is_err(),
            "an unreadable library is never replaced"
        );
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
        assert!(backups(directory.path()).is_empty());
    }
    // What a format-1 build does with a format-2 file: its NodeKind has no
    // Subject variant, so parsing fails before it could save and strip them.
    #[derive(Deserialize)]
    #[allow(dead_code)]
    enum FormatOneKind {
        Project,
        Folder,
        Stack,
    }
    #[derive(Deserialize)]
    #[allow(dead_code)]
    struct FormatOneNode {
        kind: FormatOneKind,
    }
    #[derive(Deserialize)]
    #[allow(dead_code)]
    struct FormatOneCatalog {
        nodes: Vec<FormatOneNode>,
    }
    let (path, _) = write_fixture(directory.path(), &owner_shaped_v1());
    let catalog = Catalog::load(Some(path.clone()));
    catalog.save().unwrap();
    let error = serde_json::from_slice::<FormatOneCatalog>(&std::fs::read(&path).unwrap())
        .err()
        .expect("a format-1 reader must refuse subjects");
    assert!(error.to_string().contains("Subject"), "{error}");
}

#[test]
fn hierarchy_accepts_collections_folders_subjects_and_stacks_and_rejects_the_rest() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Collection").unwrap();
    let folder = catalog.create_folder(project, "Sub-collection").unwrap();
    let inner = catalog.create_folder(folder, "Inner").unwrap();
    let subject = catalog.create_subject(folder, "Blue weevil").unwrap();
    let stack = catalog
        .create_stack(subject, "Dorsal", draft_at("/captures/weevil/100MSDCF"))
        .unwrap();
    let legacy = catalog
        .create_stack(project, "Placed directly", draft_at("/captures/other"))
        .unwrap();
    catalog.validate().unwrap();
    assert_eq!(catalog.subject_of(stack), Some(subject));
    assert_eq!(catalog.subject_of(legacy), None);
    assert_eq!(catalog.stacks_of(subject), [stack]);
    assert_eq!(catalog.selected_container(), Some(project));
    catalog.selected = Some(stack);
    assert_eq!(
        catalog.selected_container(),
        Some(subject),
        "a new stack beside a stack joins its subject"
    );

    assert!(catalog.create_folder(subject, "Nested").is_err());
    assert!(catalog.create_subject(subject, "Nested").is_err());
    assert!(catalog.create_subject(stack, "Inside a stack").is_err());
    let before = serde_json::to_vec(&catalog).unwrap();
    for (id, parent) in [
        (subject, Some(subject)),
        (folder, Some(subject)),
        (subject, Some(stack)),
        (subject, None),
        (stack, None),
        (project, Some(folder)),
    ] {
        assert!(catalog.move_node(id, parent).is_err(), "{id} → {parent:?}");
        assert_eq!(serde_json::to_vec(&catalog).unwrap(), before);
    }
    let other = catalog.create_subject(project, "Orange weevil").unwrap();
    catalog.move_node(legacy, Some(other)).unwrap();
    catalog.move_node(subject, Some(project)).unwrap();
    catalog.move_node(stack, Some(other)).unwrap();
    catalog.validate().unwrap();

    let corrupt = |change: &dyn Fn(&mut Catalog)| {
        let mut copy: Catalog =
            serde_json::from_slice(&serde_json::to_vec(&catalog).unwrap()).unwrap();
        change(&mut copy);
        copy.validate()
    };
    assert!(corrupt(&|c| c.node_mut(other).unwrap().parent = None).is_err());
    assert!(corrupt(&|c| c.node_mut(subject).unwrap().parent = Some(other)).is_err());
    assert!(corrupt(&|c| c.node_mut(folder).unwrap().parent = Some(other)).is_err());
    assert!(corrupt(&|c| c.node_mut(stack).unwrap().parent = Some(legacy)).is_err());
    assert!(corrupt(&|c| c.node_mut(other).unwrap().subject = None).is_err());
    assert!(corrupt(&|c| c.node_mut(folder).unwrap().subject = Some(SubjectMeta::new(1))).is_err());
    assert!(corrupt(&|c| c.node_mut(project).unwrap().parent = Some(folder)).is_err());
    let cycle = corrupt(&|c| c.node_mut(folder).unwrap().parent = Some(inner));
    assert!(
        cycle
            .as_ref()
            .is_err_and(|e| e.to_string().contains("cycle")),
        "{cycle:?}"
    );
    assert!(
        corrupt(&|c| {
            let scale = &mut c.node_mut(other).unwrap().subject.as_mut().unwrap().scale;
            *scale = Some(ScaleCalibration {
                um_per_px: 2.0,
                source: ScaleSource::Entered {
                    magnification: 2.0,
                    pitch_um: 3.76,
                },
            });
        })
        .is_err(),
        "an entered scale must agree with its pitch and magnification"
    );
}

#[test]
fn subject_metadata_edits_validate_everything_before_changing_anything() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Collection").unwrap();
    let subject = catalog.create_subject(project, "Garnet").unwrap();
    let scale = ScaleCalibration::entered(2.0, 3.76).unwrap();
    assert!((scale.um_per_px - 1.88).abs() < 1e-12);
    catalog
        .set_subject_meta(
            subject,
            SubjectEdit {
                notes: Some("Etched faces; light from the left.".into()),
                hero: Some(Some(PathBuf::from("/out/garnet.tiff"))),
                optics: Some(Some(Optics {
                    camera: " ILCE-7CR ".into(),
                    lens: "90mm macro + 2x".into(),
                })),
                scale: Some(Some(scale.clone())),
            },
        )
        .unwrap();
    let node = catalog.node(subject).unwrap();
    assert_eq!(node.notes, "Etched faces; light from the left.");
    let meta = node.subject.clone().unwrap();
    assert_eq!(meta.optics.as_ref().unwrap().camera, "ILCE-7CR");
    assert_eq!(meta.scale, Some(scale));
    let before = serde_json::to_vec(&catalog).unwrap();
    for bad in [
        SubjectEdit {
            notes: Some("x".repeat(4001)),
            optics: Some(None),
            ..Default::default()
        },
        SubjectEdit {
            optics: Some(Some(Optics {
                camera: "line\nbreak".into(),
                lens: String::new(),
            })),
            ..Default::default()
        },
        SubjectEdit {
            scale: Some(Some(ScaleCalibration {
                um_per_px: f64::NAN,
                source: ScaleSource::Measured {
                    slide: String::new(),
                },
            })),
            ..Default::default()
        },
        SubjectEdit {
            hero: Some(Some(PathBuf::new())),
            ..Default::default()
        },
    ] {
        assert!(catalog.set_subject_meta(subject, bad).is_err());
        assert_eq!(serde_json::to_vec(&catalog).unwrap(), before);
    }
    assert!(
        catalog
            .set_subject_meta(project, SubjectEdit::default())
            .is_err()
    );
    catalog
        .set_subject_meta(
            subject,
            SubjectEdit {
                optics: Some(None),
                scale: Some(Some(
                    ScaleCalibration::measured(0.94, "0.01 mm slide").unwrap(),
                )),
                ..Default::default()
            },
        )
        .unwrap();
    let meta = catalog.node(subject).unwrap().subject.clone().unwrap();
    assert!(meta.optics.is_none(), "null clears");
    assert_eq!(
        meta.hero,
        Some(PathBuf::from("/out/garnet.tiff")),
        "absent keeps"
    );
    let json = serde_json::to_value(&meta).unwrap();
    assert_eq!(json["scale"]["source"]["kind"], "measured");
    assert!(
        serde_json::from_value::<SubjectMeta>(json!({"created":1,"colour":"red"})).is_err(),
        "subject metadata refuses unknown fields rather than dropping them"
    );
}

#[test]
fn undo_never_deletes_a_subject_or_the_containers_that_hold_one() {
    let mut explorer = ProjectExplorer::default();
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Collection").unwrap();
    let first = catalog.create_subject(project, "Bee").unwrap();
    let stack = catalog
        .create_stack(first, "Dorsal", draft_at("/captures/bee/100MSDCF"))
        .unwrap();
    let folder = explorer
        .organize(&mut catalog, |c| c.create_folder(project, "Field trip"))
        .unwrap();
    let second = explorer
        .organize(&mut catalog, |c| c.create_subject(folder, "Wasp"))
        .unwrap();
    explorer
        .organize(&mut catalog, |c| c.move_node(stack, Some(second)))
        .unwrap();
    explorer
        .organize(&mut catalog, |c| {
            c.set_subject_meta(
                second,
                SubjectEdit {
                    notes: Some("Wings folded".into()),
                    optics: Some(Some(Optics {
                        camera: "ILCE-7CR".into(),
                        lens: String::new(),
                    })),
                    ..Default::default()
                },
            )
        })
        .unwrap();
    let empty = explorer
        .organize(&mut catalog, |c| c.create_folder(project, "Empty"))
        .unwrap();

    assert!(explorer.undo(&mut catalog), "undo the empty folder");
    assert!(
        catalog.node(empty).is_none(),
        "an empty folder still undoes as before"
    );
    assert!(explorer.undo(&mut catalog), "undo the metadata");
    let meta = catalog.node(second).unwrap();
    assert!(meta.subject.as_ref().unwrap().optics.is_none());
    assert!(meta.notes.is_empty());
    assert!(explorer.undo(&mut catalog), "undo the move");
    assert_eq!(catalog.node(stack).unwrap().parent, Some(first));
    assert!(explorer.undo(&mut catalog), "undo creating the subject");
    assert!(catalog.node(second).is_some(), "a subject is never deleted");
    assert!(explorer.undo(&mut catalog), "undo creating the folder");
    assert!(
        catalog.node(folder).is_some(),
        "the folder holding a surviving subject is kept"
    );
    assert!(catalog.node(first).is_some());
    catalog.validate().unwrap();
    while explorer.redo(&mut catalog) {}
    assert_eq!(catalog.node(stack).unwrap().parent, Some(second));
    assert_eq!(
        catalog
            .node(second)
            .unwrap()
            .subject
            .as_ref()
            .unwrap()
            .optics,
        Some(Optics {
            camera: "ILCE-7CR".into(),
            lens: String::new()
        })
    );
    assert_eq!(
        catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Subject)
            .count(),
        2,
        "redo does not duplicate a retained subject"
    );
    catalog.validate().unwrap();
}

#[test]
fn default_stack_names_skip_camera_folders() {
    for (source, expected) in [
        ("/captures/bug-3/107MSDCF", "bug-3"),
        ("/captures/bug-3/107msdcf", "bug-3"),
        ("/captures/bug-3/107MSDCF/", "bug-3"),
        ("/captures/macro/chia-seeds-cpl", "chia-seeds-cpl"),
        ("/captures/bug-3/1070MSDCF", "1070MSDCF"),
        ("/captures/bug-3/10AMSDCF", "10AMSDCF"),
        ("/card/DCIM/100MSDCF", "100MSDCF"),
        ("/100MSDCF", "100MSDCF"),
        ("100MSDCF", "100MSDCF"),
        ("", "Capture stack"),
    ] {
        assert_eq!(default_stack_name(Path::new(source)), expected, "{source}");
    }
    #[cfg(windows)]
    for (source, expected) in [
        (r"\\?\D:\StrehlCaptures\bug-9\100MSDCF", "bug-9"),
        (r"D:\personal\macro\119MSDCF", "macro"),
        (r"D:\100MSDCF", "100MSDCF"),
    ] {
        assert_eq!(default_stack_name(Path::new(source)), expected, "{source}");
    }
    assert!(is_camera_folder("100MSDCF"));
    assert!(!is_camera_folder("Session · 107MSDCF"));
}

fn write_frames(directory: &Path, frames: &[(&str, usize)]) {
    std::fs::create_dir_all(directory).unwrap();
    for (name, bytes) in frames {
        std::fs::write(directory.join(name), vec![1u8; *bytes]).unwrap();
    }
}
fn scan(directory: &Path) -> crate::jobs::StackScan {
    crate::jobs::scan_stack(directory.to_path_buf())
        .receiver
        .recv()
        .unwrap()
        .unwrap()
}
fn located_fixture(root: &Path) -> (Catalog, NodeId, PathBuf) {
    let old = root.join("bug-4").join("100MSDCF");
    write_frames(&old, &[("DSC00001.ARW", 2), ("DSC00002.ARW", 3)]);
    let found = scan(&old);
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Collection").unwrap();
    let subject = catalog.create_subject(project, "bug-4").unwrap();
    let draft = StackDraft::from_scan(
        &found,
        crate::jobs::RenderSettings::default(),
        None,
        None,
        4,
    );
    let stack = catalog.create_stack(subject, "bug-4", draft).unwrap();
    let mut run: Run = serde_json::from_value(run_json(
        &root.join("out/strehl-1-1-1").to_string_lossy(),
        "unused",
        "Saved",
        10,
    ))
    .unwrap();
    run.source.clone_from(&found.directory);
    run.sources = source_identities(&found);
    catalog.add_revision(stack, run).unwrap();
    (catalog, stack, old)
}

#[test]
fn sources_present_reads_names_only_and_reports_moved_and_partial_sources() {
    let root = tempfile::tempdir().unwrap();
    let (mut catalog, stack, old) = located_fixture(root.path());
    assert_eq!(catalog.sources_present(stack), Some(SourcesState::Present));
    std::fs::remove_file(old.join("DSC00002.ARW")).unwrap();
    assert_eq!(
        catalog.sources_present(stack),
        Some(SourcesState::Partial {
            found: 1,
            expected: 2
        })
    );
    std::fs::remove_dir_all(&old).unwrap();
    assert_eq!(catalog.sources_present(stack), Some(SourcesState::Missing));
    let draft = catalog.node_mut(stack).unwrap().stack.as_mut().unwrap();
    draft.sources.clear();
    draft.source = root.path().to_path_buf();
    assert_eq!(
        catalog.sources_present(stack),
        Some(SourcesState::Unrecorded)
    );
    assert_eq!(catalog.sources_present(9999), None);
}

#[test]
fn locate_repoints_the_stack_and_its_renders_or_refuses_and_changes_nothing() {
    let root = tempfile::tempdir().unwrap();
    let (mut catalog, stack, old) = located_fixture(root.path());
    let moved = root.path().join("archive").join("bug-4");
    write_frames(&moved, &[("DSC00001.ARW", 2), ("DSC00002.ARW", 3)]);
    std::fs::remove_dir_all(&old).unwrap();
    assert_eq!(catalog.sources_present(stack), Some(SourcesState::Missing));

    let before = serde_json::to_vec(&catalog).unwrap();
    for (name, frames, expect) in [
        (
            "resized",
            vec![("DSC00001.ARW", 2), ("DSC00002.ARW", 4)],
            "differ in size: DSC00002.ARW (3 → 4 bytes)",
        ),
        (
            "missing",
            vec![("DSC00001.ARW", 2)],
            "1 recorded missing: DSC00002.ARW",
        ),
        (
            "extra",
            vec![
                ("DSC00001.ARW", 2),
                ("DSC00002.ARW", 3),
                ("DSC00003.ARW", 1),
            ],
            "1 not recorded: DSC00003.ARW",
        ),
    ] {
        let candidate = root.path().join(name);
        write_frames(&candidate, &frames);
        let error = catalog.relocate_stack(stack, &candidate).unwrap_err();
        let mismatch = error
            .downcast_ref::<RelocateMismatch>()
            .expect("a structured mismatch for the UI");
        assert!(error.to_string().contains(expect), "{error}");
        assert!(error.to_string().ends_with("Nothing was changed"));
        assert_eq!(mismatch.directory, scan(&candidate).directory);
        assert_eq!(
            serde_json::to_vec(&catalog).unwrap(),
            before,
            "{name}: a refusal changes nothing"
        );
    }
    assert!(
        catalog
            .relocate_stack(stack, &root.path().join("no-such-folder"))
            .is_err()
    );

    let report = catalog.relocate_stack(stack, &moved).unwrap();
    let target = scan(&moved);
    assert_eq!(report.directory, target.directory);
    assert_eq!((report.sources, report.runs), (2, 1));
    let draft = catalog.node(stack).unwrap().stack.clone().unwrap();
    assert_eq!(draft.source, target.directory);
    assert_eq!(draft.sources, source_identities(&target));
    let run = catalog.latest_run(stack).unwrap();
    assert_eq!(run.source, target.directory);
    assert!(
        run.matches_scan(&target),
        "the render reopens against the located folder"
    );
    assert_eq!(catalog.sources_present(stack), Some(SourcesState::Present));
    assert_eq!(
        catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Stack)
            .count(),
        1,
        "Locate never creates a second stack"
    );
    catalog.validate().unwrap();

    // A multi-folder session is not relocated as if it were one folder.
    catalog
        .node_mut(stack)
        .unwrap()
        .stack
        .as_mut()
        .unwrap()
        .settings
        .session = Some(crate::session_workspace::SessionDraft::from_directory(
        moved.clone(),
    ));
    let error = catalog.relocate_stack(stack, &moved).unwrap_err();
    assert!(
        error.to_string().contains("several capture folders"),
        "{error}"
    );
}

struct Child(std::process::Child);
impl Drop for Child {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}
fn waiting_process() -> Child {
    #[cfg(windows)]
    let command = Command::new("cmd")
        .args(["/C", "pause"])
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .spawn();
    #[cfg(not(windows))]
    let command = Command::new("sleep").arg("60").stdin(Stdio::null()).spawn();
    Child(command.unwrap())
}
fn exited_process() -> u32 {
    #[cfg(windows)]
    let mut child = Command::new("cmd")
        .args(["/C", "exit", "0"])
        .stdout(Stdio::null())
        .spawn()
        .unwrap();
    #[cfg(not(windows))]
    let mut child = Command::new("true").spawn().unwrap();
    let pid = child.id();
    child.wait().unwrap();
    pid
}

#[test]
fn stacking_runs_left_by_a_killed_desktop_become_interrupted_unless_a_live_job_owns_them() {
    let live = waiting_process();
    let live_pid = live.0.id();
    let dead_pid = exited_process();
    let own = std::process::id();
    let now = timestamp();
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Collection").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let mut stacks = Vec::new();
    for (index, (pid, status, created)) in [
        (dead_pid, "Stacking", now),
        (own, "Stacking", now),
        (own, "Stacking", now),
        (live_pid, "Stacking", now + 5),
        (dead_pid, "Rendering", now),
        (dead_pid, "Saved", now),
        (dead_pid, "Failed", now),
    ]
    .into_iter()
    .enumerate()
    {
        let directory = format!("/out/strehl-1794000000000-{pid}-{index}");
        let run: Run =
            serde_json::from_value(run_json(&directory, "/captures/w", status, created)).unwrap();
        let stack = catalog
            .create_stack(
                subject,
                &format!("stack {index}"),
                StackDraft::from_run(&run),
            )
            .unwrap();
        catalog.add_revision(stack, run).unwrap();
        stacks.push(stack);
    }
    let unnamed: Run = serde_json::from_value(run_json(
        "/out/imported-elsewhere",
        "/captures/w",
        "Stacking",
        now,
    ))
    .unwrap();
    catalog.add(unnamed);
    let active = PathBuf::from(format!("/out/strehl-1794000000000-{own}-2"));
    assert_eq!(catalog.reconcile_interrupted_runs(&[active.as_path()]), 4);
    let status =
        |catalog: &Catalog, index: usize| catalog.latest_run(stacks[index]).unwrap().status.clone();
    assert_eq!(status(&catalog, 0), "Interrupted", "its window exited");
    assert_eq!(
        status(&catalog, 1),
        "Interrupted",
        "this new window owns no job yet"
    );
    assert_eq!(status(&catalog, 2), "Stacking", "the caller's running job");
    assert_eq!(status(&catalog, 3), "Stacking", "another live window's job");
    assert_eq!(
        status(&catalog, 4),
        "Interrupted",
        "older builds wrote Rendering"
    );
    assert_eq!(status(&catalog, 5), "Saved");
    assert_eq!(status(&catalog, 6), "Failed");
    assert_eq!(
        catalog.runs[0].status, "Interrupted",
        "no process id to ask"
    );
    assert_eq!(
        catalog.stack_lifecycle(stacks[0]).unwrap().next_step(),
        NextStep::Check
    );
    assert_eq!(catalog.reconcile_interrupted_runs(&[active.as_path()]), 0);
    #[cfg(windows)]
    {
        // A reused id: the live process started after the run was recorded.
        for run in &mut catalog.runs {
            if run.status == "Stacking" && run.directory != active {
                run.created = 1_000;
            }
        }
        assert_eq!(catalog.reconcile_interrupted_runs(&[active.as_path()]), 1);
        assert_eq!(status(&catalog, 3), "Interrupted");
    }
    drop(live);
}

#[test]
fn lifecycle_follows_renders_versions_and_exports_and_the_index_agrees() {
    let directory = tempfile::tempdir().unwrap();
    let mut fixture = owner_shaped_v1();
    // A render in flight on bug-6 (Bugs) after its saved one.
    fixture["runs"].as_array_mut().unwrap().insert(
        0,
        run_json(
            "/out/strehl-700-1-7",
            "/bugs/bug-6/100MSDCF",
            "Stacking",
            700,
        ),
    );
    assert_eq!(fixture["nodes"][14]["id"], 34);
    fixture["nodes"][14]["revisions"] = json!(["/out/strehl-500-1-5", "/out/strehl-700-1-7"]);
    let (path, _) = write_fixture(directory.path(), &fixture);
    let catalog = Catalog::load(Some(path));
    assert!(catalog.load_error.is_none(), "{:?}", catalog.load_error);
    let life = |stack| catalog.stack_lifecycle(stack).unwrap();
    use StepState::*;
    assert_eq!(life(4).steps(), [Done, NotYet, NotYet, NotYet]);
    assert_eq!(life(4).next_step(), NextStep::Stack);
    assert_eq!(life(3).stacked, NeedsLook, "latest render failed");
    assert!(life(3).needs_a_look());
    assert_eq!(life(3).next_step(), NextStep::Check);
    assert_eq!((life(3).renders, life(3).saved_renders), (2, 1));
    assert_eq!(life(27).next_step(), NextStep::Develop);
    assert_eq!(life(12).steps(), [Done, Done, Done, Done]);
    assert_eq!(life(12).next_step(), NextStep::Done);
    assert_eq!((life(12).versions, life(12).exports), (1, 1));
    assert_eq!(life(12).last_activity, 320);
    assert_eq!(life(34).stacked, Running);
    assert_eq!(life(41).latest, Some(RunState::Cancelled));
    assert!(catalog.stack_lifecycle(1).is_none());

    let bug_1 = catalog.subject_of(12).unwrap();
    let summary = catalog.subject_summary(bug_1).unwrap();
    assert_eq!(summary.stacks, 3);
    assert_eq!((summary.to_stack, summary.exported), (2, 1));
    assert_eq!(summary.steps, [Done, Done, Done, Done]);
    assert_eq!(summary.next_step(), NextStep::Stack);
    let chia = catalog
        .subject_summary(catalog.subject_of(3).unwrap())
        .unwrap();
    assert_eq!((chia.to_check, chia.to_stack), (1, 1));
    assert_eq!(chia.next_step(), NextStep::Check);
    assert_eq!(
        chia.steps,
        [Done, NeedsLook, NotYet, NotYet],
        "the strongest state of each step"
    );

    let index = catalog.library_index();
    for node in &catalog.nodes {
        match node.kind {
            NodeKind::Stack => {
                assert_eq!(index.stacks[&node.id], life(node.id), "stack {}", node.id)
            }
            NodeKind::Subject => assert_eq!(
                index.subjects[&node.id],
                catalog.subject_summary(node.id).unwrap()
            ),
            _ => assert!(!index.stacks.contains_key(&node.id)),
        }
    }
    let mut empty = catalog;
    let lonely = empty.create_subject(1, "Not yet shot").unwrap();
    let summary = empty.subject_summary(lonely).unwrap();
    assert_eq!(summary.stacks, 0);
    assert_eq!(summary.next_step(), NextStep::Stack);
}

#[test]
fn a_six_thousand_plane_stack_with_five_renders_fits_the_catalog_cap() {
    // Measures, rather than assumes, the cost of repeating the source list
    // in the stack's recipe and in every render (implementation plan 6.7).
    let planes = 6_000;
    let source = r"\\?\D:\StrehlCaptures\weevil-blue\100MSDCF";
    let sources: Vec<SourceIdentity> = (0..planes)
        .map(|i| SourceIdentity {
            path: PathBuf::from(format!(r"{source}\DSC{:05}.ARW", i + 1)),
            bytes: 62_914_560 + i as u64,
            modified_ns: Some(1_794_000_000_000_000_000 + i as u128 * 7_000_000_000),
        })
        .collect();
    let mut catalog = Catalog::default();
    let empty = serde_json::to_vec_pretty(&catalog).unwrap().len();
    let project = catalog.create_project("Bugs").unwrap();
    let subject = catalog.create_subject(project, "Blue weevil").unwrap();
    let mut draft = draft_at(source);
    draft.sources.clone_from(&sources);
    let stack = catalog.create_stack(subject, "Dorsal", draft).unwrap();
    for index in 0..5u64 {
        let mut run: Run = serde_json::from_value(run_json(
            &format!(r"C:\Users\owner\Pictures\Strehl\strehl-17943000000{index:02}-51816-{index}"),
            source,
            "Saved",
            1_794_300_000 + index,
        ))
        .unwrap();
        run.sources.clone_from(&sources);
        run.frames = planes;
        catalog.add_revision(stack, run).unwrap();
    }
    let bytes = serde_json::to_vec_pretty(&catalog).unwrap().len() - empty;
    let per_identity = bytes as f64 / (6.0 * planes as f64);
    eprintln!(
        "catalog-size: 6000 planes x (recipe + 5 renders) = {bytes} bytes ({:.2} MiB, {:.1} % of the 32 MiB cap); {per_identity:.1} bytes per source identity",
        bytes as f64 / 1_048_576.0,
        100.0 * bytes as f64 / MAX_CATALOG_BYTES as f64
    );
    assert!(
        bytes < MAX_CATALOG_BYTES / 4,
        "one such stack must leave room for others"
    );
    catalog.validate().unwrap();
}

/// One-off verification on a copy of the owner's catalog. Never the original:
/// `STREHL_P4_CATALOG` must name a copy outside `%LOCALAPPDATA%\Strehl`.
/// `cargo test -p strehl-ui owner_catalog_copy -- --ignored --nocapture`
#[test]
#[ignore = "reads a copy of a private catalog named by STREHL_P4_CATALOG"]
fn owner_catalog_copy_migrates_without_loss() {
    let path = PathBuf::from(std::env::var_os("STREHL_P4_CATALOG").expect("STREHL_P4_CATALOG"));
    if let Some(local) = std::env::var_os("LOCALAPPDATA") {
        let live = PathBuf::from(local).join("Strehl");
        assert!(
            !subjects::path_key(&path).starts_with(&subjects::path_key(&live)),
            "never migrate the live catalog"
        );
    }
    let original = std::fs::read(&path).unwrap();
    let raw: Value = serde_json::from_slice(&original).unwrap();
    let unmigrated: Catalog = serde_json::from_slice(&original).unwrap();
    let catalog = Catalog::load(Some(path.clone()));
    assert!(catalog.load_error.is_none(), "{:?}", catalog.load_error);
    let count = |kind| catalog.nodes.iter().filter(|n| n.kind == kind).count();
    eprintln!(
        "owner-copy: format {:?} -> {}; {} nodes -> {}; stacks {}; subjects {}; runs {}; versions {}; exports {}",
        raw.get("format"),
        catalog.format,
        unmigrated.nodes.len(),
        catalog.nodes.len(),
        count(NodeKind::Stack),
        count(NodeKind::Subject),
        catalog.runs.len(),
        catalog.photo_versions.len(),
        catalog.photo_exports.len()
    );
    for subject in catalog.nodes.iter().filter(|n| n.kind == NodeKind::Subject) {
        eprintln!(
            "owner-copy: subject {:>3} in {:<18} {:<34} stacks {:?}",
            subject.id,
            catalog.node(subject.parent.unwrap()).unwrap().name,
            subject.name,
            catalog.stacks_of(subject.id)
        );
    }
    assert_eq!(
        serde_json::to_value(&catalog.runs).unwrap(),
        serde_json::to_value(&unmigrated.runs).unwrap()
    );
    assert_eq!(catalog.photo_versions, unmigrated.photo_versions);
    assert_eq!(
        serde_json::to_value(&catalog.photo_exports).unwrap(),
        serde_json::to_value(&unmigrated.photo_exports).unwrap()
    );
    for run in &unmigrated.runs {
        assert_eq!(
            catalog.stack_for_run(&run.directory),
            unmigrated.stack_for_run(&run.directory)
        );
    }
    for node in catalog.nodes.iter().filter(|n| n.kind == NodeKind::Stack) {
        assert!(catalog.subject_of(node.id).is_some());
    }
    let index = catalog.library_index();
    let mut states: Vec<_> = index
        .subjects
        .iter()
        .map(|(id, s)| (*id, s.next_step(), s.stacks, s.renders))
        .collect();
    states.sort_by_key(|s| s.0);
    eprintln!("owner-copy: subject next steps {states:?}");
    // Read-only listings of the capture folders the stacks record.
    let mut sources = std::collections::BTreeMap::<String, Vec<NodeId>>::new();
    for node in catalog.nodes.iter().filter(|n| n.kind == NodeKind::Stack) {
        let state = catalog.sources_present(node.id).unwrap();
        sources
            .entry(format!("{state:?}"))
            .or_default()
            .push(node.id);
    }
    eprintln!("owner-copy: sources present {sources:?}");
    let mut stacking = Catalog::load(Some(path.clone()));
    eprintln!(
        "owner-copy: runs reconciled to Interrupted: {}",
        stacking.reconcile_interrupted_runs(&[])
    );
    catalog.save().unwrap();
    let backup = catalog
        .legacy_backup()
        .expect("a backup of the format-1 copy");
    assert_eq!(std::fs::read(&backup).unwrap(), original);
    eprintln!(
        "owner-copy: backup {} re-reads; saved {} -> {} bytes",
        backup.display(),
        original.len(),
        std::fs::metadata(&path).unwrap().len()
    );
    let reloaded = Catalog::load(Some(path));
    assert_eq!(
        serde_json::to_vec(&reloaded).unwrap(),
        serde_json::to_vec(&catalog).unwrap()
    );
}

#[test]
fn an_import_plan_groups_camera_folders_by_parent_and_keeps_others_alone() {
    let path = |p: &str| PathBuf::from(p);
    let plan = import_plan(&[
        path("/captures/bug-3/101MSDCF"),
        path("/captures/macro/chia-seeds"),
        path("/captures/bug-3/100MSDCF"),
        path("/captures/macro/tweezers"),
        path("/captures/bug-3/101MSDCF/"),
        path("/card/DCIM/100MSDCF"),
        path("/100MSDCF"),
        path(""),
    ]);
    let summary: Vec<(String, Vec<PathBuf>)> = plan
        .into_iter()
        .map(|group| (group.subject, group.folders))
        .collect();
    assert_eq!(
        summary,
        [
            (
                "bug-3".to_owned(),
                vec![
                    path("/captures/bug-3/100MSDCF"),
                    path("/captures/bug-3/101MSDCF")
                ]
            ),
            (
                "chia-seeds".to_owned(),
                vec![path("/captures/macro/chia-seeds")]
            ),
            (
                "tweezers".to_owned(),
                vec![path("/captures/macro/tweezers")]
            ),
            ("100MSDCF".to_owned(), vec![path("/card/DCIM/100MSDCF")]),
            ("100MSDCF".to_owned(), vec![path("/100MSDCF")]),
        ],
        "one stack per folder; a repeated folder counts once; DCIM and a root name nothing"
    );
}

/// The owner's catalog (2026-11-21): node 23, `generated-smoke-input`, a
/// test input from a temp folder long gone, never rendered, showed its
/// subject dated "today": migration gave a subject without renders the
/// time of migration. Its own record is the photographs' write time.
#[test]
fn a_subject_without_renders_is_dated_by_its_recorded_capture_never_today() {
    use crate::library_station::LibraryModel;
    // 2026-10-24, the smoke input's recorded modification time.
    const RECORDED_NS: u128 = 1_792_940_742_495_839_900;
    const RECORDED: u64 = 1_792_940_742;
    let dir = tempfile::tempdir().unwrap();
    let mut smoke = stack_json(
        23,
        1,
        "generated-smoke-input",
        "/tmp/gone/generated-smoke-input",
        &[],
    );
    smoke["stack"]["sources"] = json!([
        {"path": "/tmp/gone/generated-smoke-input/a-valid-optical.ARW", "bytes": 100, "modified_ns": RECORDED_NS},
        {"path": "/tmp/gone/generated-smoke-input/b-malformed-optical.ARW", "bytes": 100, "modified_ns": RECORDED_NS}
    ]);
    let v1 = json!({
        "layout": {}, "selected": null, "next_node_id": 30,
        "nodes": [
            {"id": 1, "parent": null, "name": "Imported stacks", "kind": "Project"},
            smoke,
            stack_json(24, 1, "input", "/tmp/gone/input", &[])
        ],
        "runs": [], "photo_versions": [], "photo_exports": [], "export_directories": {}
    });
    let (path, _) = write_fixture(dir.path(), &v1);
    let catalog = Catalog::load(Some(path));
    assert!(catalog.load_error.is_none(), "{:?}", catalog.load_error);
    let subject = catalog.subject_of(23).unwrap();
    let meta = catalog.node(subject).unwrap().subject.clone().unwrap();
    assert_eq!(
        meta.created, RECORDED,
        "the capture's own date, not the migration's"
    );
    // With no recorded time at all the subject has no date (0), not now.
    let undated = catalog.subject_of(24).unwrap();
    assert_eq!(
        catalog
            .node(undated)
            .unwrap()
            .subject
            .as_ref()
            .unwrap()
            .created,
        0
    );
    let now = timestamp();
    let model = LibraryModel::build(&catalog, 0, now);
    let card = |id| model.cards.iter().find(|c| c.id == id).unwrap();
    assert_eq!(card(subject).last, RECORDED);
    assert_ne!(crate::library_paint::day(card(subject).last, now), "today");
    assert_eq!(
        crate::library_paint::day(card(undated).last, now),
        "",
        "no date shown"
    );
    // A catalog an earlier build already saved with the migration's time:
    // the card still reads the stack's own record.
    let mut saved = catalog;
    saved
        .node_mut(subject)
        .unwrap()
        .subject
        .as_mut()
        .unwrap()
        .created = now;
    let model = LibraryModel::build(&saved, 1, now);
    let card = model.cards.iter().find(|c| c.id == subject).unwrap();
    assert_eq!(card.last, RECORDED);
    // The subject page dates the stack row by its capture too.
    let page = crate::subject_page::SubjectModel::build(&saved, subject, 1).unwrap();
    assert_eq!(page.stacks[0].last, RECORDED);
    assert!(
        page.journal
            .iter()
            .any(|line| line.at == RECORDED
                && line.text == "generated-smoke-input captured · 2 planes"),
        "{:?}",
        page.journal
    );
}
