//! Measuring and deleting a removed entry's files, on scratch fixtures made
//! here: only attributed files go, a capture folder only once finished, a
//! folder only once empty, and the Recycle Bin only when it can take all.
use super::*;
use crate::library_station::tests::{draft, run};
use crate::workspace_history::{Catalog, NodeKind, OwnedFiles, Run, SourceIdentity, StackDraft};

struct Fixture {
    _root: tempfile::TempDir,
    catalog: Catalog,
    subject: NodeId,
    capture: PathBuf,
    job: PathBuf,
}
fn write(path: &Path, bytes: usize) {
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, vec![7u8; bytes]).unwrap();
}
/// A finished capture folder as the receiver writes it (two RAWs, its
/// records, a stranger file the stack did not record), and one render.
fn fixture() -> Fixture {
    let root = tempfile::tempdir().unwrap();
    let capture = root
        .path()
        .join("captures")
        .join("stack-1795291999414-6430");
    for name in [
        "manifest.json",
        "events.jsonl",
        "result.json",
        "transfer-receipts.jsonl",
    ] {
        write(&capture.join(name), 10);
    }
    write(&capture.join("frame-000001.ARW.straw"), 1000);
    write(&capture.join("frame-000002.ARW.straw"), 1000);
    // A retake the stack does not use: still the capture's own file.
    write(&capture.join("frame-000003.ARW.straw"), 1000);
    write(&capture.join("notes.txt"), 5);
    let job = root.path().join("out").join("strehl-1795292000000-77-0");
    write(&job.join("result.tiff"), 300);
    write(&job.join("render.log"), 20);
    write(&job.join("cache").join("warp.bin"), 50);
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let mut recipe: StackDraft = draft(&capture.to_string_lossy(), 0);
    recipe.sources = ["frame-000001.ARW.straw", "frame-000002.ARW.straw"]
        .iter()
        .map(|name| SourceIdentity {
            path: capture.join(name),
            bytes: 1000,
            modified_ns: None,
        })
        .collect();
    let stack = catalog.create_stack(subject, "Dorsal", recipe).unwrap();
    let mut render: Run = run(
        &job.to_string_lossy(),
        &capture.to_string_lossy(),
        "Saved",
        5,
    );
    render.output = job.join("result.tiff");
    render.log = job.join("render.log");
    catalog.add_revision(stack, render).unwrap();
    Fixture {
        _root: root,
        catalog,
        subject,
        capture,
        job,
    }
}
fn owned(f: &Fixture) -> OwnedFiles {
    f.catalog
        .owned_files(&f.catalog.removal_scope(&[f.subject]))
}
fn never() -> AtomicBool {
    AtomicBool::new(false)
}

#[test]
fn measuring_counts_render_folders_and_the_captures_own_files_and_leaves_strangers() {
    let f = fixture();
    let measured = measure(&owned(&f), &Guard::default(), &never());
    assert!(measured.refused.is_empty(), "{:?}", measured.refused);
    assert_eq!(measured.renders.len(), 1);
    assert_eq!(
        (measured.renders[0].files, measured.renders[0].bytes),
        (3, 370)
    );
    let sources = &measured.sources[0];
    assert!(
        sources.capture,
        "manifest and journal mark a capture folder"
    );
    assert_eq!(sources.photographs, 2);
    assert_eq!(sources.missing, 0);
    // Two recorded RAWs, the retake and four records; notes.txt stays.
    assert_eq!(sources.files.len(), 7, "{:?}", sources.files);
    assert_eq!(sources.bytes, 3040);
    assert_eq!(sources.others, 1);
    assert!(
        !sources.files.iter().any(|p| p.ends_with("notes.txt")),
        "a file the stack did not record is not the stack's"
    );
    assert_eq!(measured.source_total.files, 7);
    assert_eq!(measured.render_total.folders, 1);
}

#[test]
fn a_capture_without_its_result_or_being_written_is_not_deleted() {
    let f = fixture();
    std::fs::remove_file(f.capture.join("result.json")).unwrap();
    let measured = measure(&owned(&f), &Guard::default(), &never());
    assert!(measured.sources.is_empty());
    assert!(
        measured.refused[0].reason.contains("no result yet"),
        "{:?}",
        measured.refused
    );
    write(&f.capture.join("result.json"), 10);
    let guard = Guard {
        capturing: Some(f.capture.clone()),
    };
    let measured = measure(&owned(&f), &guard, &never());
    assert!(measured.sources.is_empty());
    assert!(measured.refused[0].reason.contains("being written now"));
    // A missing folder is reported, not an error.
    std::fs::remove_dir_all(&f.job).unwrap();
    let measured = measure(&owned(&f), &Guard::default(), &never());
    assert!(measured.renders.is_empty());
    assert!(
        measured
            .refused
            .iter()
            .any(|r| r.reason.contains("already gone"))
    );
}

#[test]
fn permanent_deletion_takes_only_owned_files_and_a_folder_only_once_empty() {
    let f = fixture();
    let measured = measure(&owned(&f), &Guard::default(), &never());
    let plan = DeletePlan {
        renders: measured.renders.clone(),
        render_disposal: Some(Disposal::Permanent),
        sources: measured.sources.clone(),
        source_disposal: Some(Disposal::Permanent),
    };
    let done = AtomicUsize::new(0);
    let report = execute(&plan, &Guard::default(), &done);
    assert_eq!(done.load(Ordering::Relaxed), 2);
    assert!(report.failed.is_empty(), "{:?}", report.failed);
    assert!(!f.job.exists(), "the render folder goes whole");
    assert_eq!(report.files, 3 + 7);
    // The stranger keeps its folder.
    assert!(f.capture.join("notes.txt").is_file());
    assert_eq!(std::fs::read_dir(&f.capture).unwrap().count(), 1);
    assert_eq!(report.folders_kept, vec![f.capture.clone()]);
    assert_eq!(report.recycled, 0);
}

#[test]
fn a_folder_holding_only_the_stacks_files_goes_and_a_rechecked_capture_is_kept() {
    let f = fixture();
    std::fs::remove_file(f.capture.join("notes.txt")).unwrap();
    let measured = measure(&owned(&f), &Guard::default(), &never());
    // Between the confirmation and the deletion the capture lost its
    // result (a new run wrote there): nothing is deleted.
    std::fs::remove_file(f.capture.join("result.json")).unwrap();
    let plan = DeletePlan {
        sources: measured.sources.clone(),
        source_disposal: Some(Disposal::Permanent),
        ..Default::default()
    };
    let report = execute(&plan, &Guard::default(), &AtomicUsize::new(0));
    assert_eq!(report.files, 0);
    assert!(
        report.failed[0].contains("not finished"),
        "{:?}",
        report.failed
    );
    assert!(f.capture.join("frame-000001.ARW.straw").is_file());
    // Finished again: everything is the capture's, so the folder goes.
    write(&f.capture.join("result.json"), 10);
    let report = execute(&plan, &Guard::default(), &AtomicUsize::new(0));
    assert!(report.failed.is_empty(), "{:?}", report.failed);
    assert!(!f.capture.exists());
    assert_eq!(report.folders_removed, 1);
    // The render folder was not chosen: it stays.
    assert!(f.job.join("result.tiff").is_file());
}

#[test]
fn a_render_folder_swapped_after_measuring_is_not_deleted() {
    let f = fixture();
    let measured = measure(&owned(&f), &Guard::default(), &never());
    let mut plan = DeletePlan {
        renders: measured.renders.clone(),
        render_disposal: Some(Disposal::Permanent),
        ..Default::default()
    };
    // Only folders named like a job folder, never anything else.
    plan.renders[0].directory = f.capture.clone();
    let report = execute(&plan, &Guard::default(), &AtomicUsize::new(0));
    assert!(report.failed[0].contains("no longer the render folder"));
    assert!(f.capture.join("frame-000001.ARW.straw").is_file());
    assert!(f.job.is_dir());
}

#[test]
fn a_plain_folder_keeps_unrecorded_photographs() {
    let root = tempfile::tempdir().unwrap();
    let folder = root.path().join("bug-1").join("100MSDCF");
    for name in [
        "DSC00001.ARW",
        "DSC00002.ARW",
        "DSC00003.ARW",
        "manifest.json",
    ] {
        write(&folder.join(name), 100);
    }
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "bug-1").unwrap();
    let mut recipe = draft(&folder.to_string_lossy(), 0);
    recipe.sources = ["DSC00001.ARW", "DSC00002.ARW"]
        .iter()
        .map(|n| SourceIdentity {
            path: folder.join(n),
            bytes: 100,
            modified_ns: None,
        })
        .collect();
    catalog.create_stack(subject, "100MSDCF", recipe).unwrap();
    let owned = catalog.owned_files(&catalog.removal_scope(&[subject]));
    let measured = measure(&owned, &Guard::default(), &never());
    let sources = &measured.sources[0];
    assert!(!sources.capture, "a manifest alone is not a capture folder");
    assert_eq!((sources.files.len(), sources.others), (2, 2));
    let plan = DeletePlan {
        sources: measured.sources.clone(),
        source_disposal: Some(Disposal::Permanent),
        ..Default::default()
    };
    execute(&plan, &Guard::default(), &AtomicUsize::new(0));
    let mut left: Vec<String> = std::fs::read_dir(&folder)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    left.sort();
    assert_eq!(left, vec!["DSC00003.ARW", "manifest.json"]);
    let _ = NodeKind::Stack;
}

#[test]
fn the_recycle_bin_is_used_only_when_every_volume_can_take_its_share() {
    let room = |capacity: Option<u64>, disabled: bool| BinRoom {
        volume: "D:".into(),
        capacity,
        used: 0,
        disabled,
    };
    let gib = 1024 * 1024 * 1024;
    let (disposal, why) = disposal_for(&[(room(Some(95 * gib), false), 51 * gib)]);
    assert_eq!((disposal, why), (Disposal::RecycleBin, None));
    let (disposal, why) = disposal_for(&[(room(Some(95 * gib), false), 280 * gib)]);
    assert_eq!(disposal, Disposal::Permanent);
    assert!(why.unwrap().contains("larger than the Recycle Bin on D:"));
    let (disposal, why) = disposal_for(&[(room(Some(95 * gib), true), gib)]);
    assert_eq!(disposal, Disposal::Permanent);
    assert!(why.unwrap().contains("off for D:"));
    let (disposal, why) = disposal_for(&[(room(None, false), gib)]);
    assert_eq!(disposal, Disposal::Permanent);
    assert!(why.unwrap().contains("does not report"));
    // One volume that cannot take its share makes the category permanent.
    let small = BinRoom {
        volume: "C:".into(),
        ..room(Some(gib), false)
    };
    let (disposal, _) = disposal_for(&[(room(Some(95 * gib), false), gib), (small, 2 * gib)]);
    assert_eq!(disposal, Disposal::Permanent);
    assert_eq!(
        disposal_for(&[]).0,
        Disposal::Permanent,
        "nothing to recycle"
    );
}

/// The Recycle Bin path on a scratch folder, by hand: it leaves one small
/// folder named `strehl-f-library-recycle-check` in the Recycle Bin.
/// `STREHL_RECYCLE_SCRATCH` must name a folder under `C:\strehl-scratch`.
#[test]
#[ignore = "moves a scratch folder to the Recycle Bin; run by hand"]
fn recycling_a_scratch_folder_moves_it_to_the_recycle_bin() {
    let scratch = PathBuf::from(std::env::var_os("STREHL_RECYCLE_SCRATCH").expect("set it"));
    assert!(
        path_within(&scratch, Path::new(r"C:\strehl-scratch")),
        "only under C:\\strehl-scratch"
    );
    let folder = scratch.join("strehl-f-library-recycle-check");
    write(&folder.join("a.bin"), 10);
    let room = bin_room(&folder).expect("a bin on this volume");
    eprintln!("{room:?}");
    recycle_paths(&[folder.as_path()]).unwrap();
    assert!(!folder.exists());
}
