//! Depth signatures: the rail's definition, pooling, the cache and the
//! worker that fills it.
use super::*;
use crate::depth_rail::DepthRail;
use crate::workspace_history::{Run, StackDraft};

/// A render log: one merge stage over `planes`, then a level-0 gate-support
/// map per listed plane (`data` is two sites, `ff` set and `00` clear).
fn log_text(planes: usize, maps: &[(usize, &str)]) -> String {
    let mut text = format!("STREHL_UI_PROGRESS event=stage name=merge total={planes}\n");
    for (sequence, (frame, data)) in maps.iter().enumerate() {
        text.push_str(&format!(
            "STREHL_UI_PROGRESS event=diagnostic seq={} frame={frame} level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total={planes} sampling=nearest data={data}\n",
            sequence + 1
        ));
    }
    text
}
fn progress_of(text: &str) -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    progress.ingest(text);
    progress
}

#[test]
fn a_signature_is_the_rails_series_and_missing_planes_are_never_zeros() {
    let progress = progress_of(&log_text(
        6,
        &[(0, "ffff"), (1, "ff00"), (2, "0000"), (5, "ff00")],
    ));
    assert_eq!(progress.frames_total, Some(6));
    let signature = from_progress(&progress);
    assert_eq!(signature.planes, 6);
    // The rail on the same progress, at its default level.
    let mut rail = DepthRail::default();
    rail.update(
        &progress.admission_archive,
        &progress.sampled_mask_history,
        6,
        0,
        evidence_revision(&progress),
    );
    for plane in 0..6 {
        let expected = rail.share(plane).unwrap_or(-1.0);
        assert_eq!(signature.values[plane], expected, "plane {plane}");
    }
    assert_eq!(signature.values, [1.0, 0.5, 0.0, -1.0, -1.0, 0.5]);
}

#[test]
fn many_planes_pool_by_the_ratio_of_sums_and_no_evidence_means_no_signature() {
    // 300 planes into 128 columns; every plane half admitted, except plane 0.
    let mut maps: Vec<(usize, &str)> = (1..300).map(|frame| (frame, "ff00")).collect();
    maps.push((0, "ffff"));
    let signature = from_progress(&progress_of(&log_text(300, &maps)));
    assert_eq!(
        (signature.planes, signature.values.len()),
        (300, MAX_VALUES)
    );
    // Column 0 holds planes 0 and 1: (2 + 1) / (2 + 2).
    assert_eq!(signature.values[0], 0.75);
    assert!(signature.values[1..].iter().all(|&v| v == 0.5));
    // Planes but no maps: nothing to show.
    let empty = from_progress(&progress_of(&log_text(40, &[])));
    assert_eq!(
        empty,
        Signature {
            planes: 40,
            values: Vec::new()
        }
    );
    assert_eq!(
        from_progress(&PipelineProgress::default()),
        Signature::default()
    );
}

#[test]
fn compute_replays_a_saved_run_as_a_reopen_does() {
    let files = jobs::tests::TestDirectory::new("depth-signature-compute");
    let log = files.path().join("render.log");
    std::fs::write(&log, log_text(3, &[(0, "ff00"), (2, "ffff")])).unwrap();
    let signature = compute(files.path(), &log, &AtomicBool::new(false)).unwrap();
    assert_eq!(signature.values, [0.5, -1.0, 1.0]);
    let cancelled = compute(files.path(), &log, &AtomicBool::new(true));
    assert!(cancelled.is_err(), "a cancelled replay yields nothing");
}

fn catalog_with_runs(root: &Path) -> (Catalog, NodeId, NodeId, NodeId) {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Bugs").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let make = |name: &str, created: u64, maps: &[(usize, &str)]| {
        let directory = root.join(name);
        std::fs::create_dir_all(&directory).unwrap();
        let log = directory.join("render.log");
        std::fs::write(&log, log_text(2, maps)).unwrap();
        Run {
            directory,
            source: root.join("captures").join(name),
            output: PathBuf::new(),
            log,
            label: name.into(),
            created,
            status: "Saved".into(),
            frames: 2,
            sources: Vec::new(),
            settings: Default::default(),
            exposure: None,
            gate: None,
            workers: 1,
            pinned: false,
            imported: None,
        }
    };
    let older = make("dorsal-1", 10, &[(0, "0000"), (1, "0000")]);
    let newer = make("dorsal-2", 20, &[(0, "ffff"), (1, "ff00")]);
    let lateral = make("lateral-1", 15, &[(0, "ff00")]);
    let dorsal = catalog
        .create_stack(subject, "Dorsal", StackDraft::from_run(&older))
        .unwrap();
    let side = catalog
        .create_stack(subject, "Lateral", StackDraft::from_run(&lateral))
        .unwrap();
    for (stack, run) in [(dorsal, older), (dorsal, newer), (side, lateral)] {
        catalog
            .node_mut(stack)
            .unwrap()
            .revisions
            .push(run.directory.clone());
        catalog.runs.push(run);
    }
    (catalog, subject, dorsal, side)
}

fn settle(signatures: &mut DepthSignatures, allowed: bool) {
    let deadline = Instant::now() + Duration::from_secs(10);
    signatures.poll(allowed, 100);
    while signatures.pending() && allowed {
        assert!(Instant::now() < deadline, "timed out");
        std::thread::sleep(Duration::from_millis(5));
        signatures.poll(allowed, 100);
    }
}

#[test]
fn rows_on_screen_are_computed_once_on_a_worker_cached_and_reloaded() {
    let files = jobs::tests::TestDirectory::new("depth-signature-cache");
    let (catalog, subject, dorsal, side) = catalog_with_runs(files.path());
    let path = files.path().join(FILE_NAME);
    let mut signatures = DepthSignatures::opened_at(Some(path.clone()));
    settle(&mut signatures, true);
    signatures.refresh(&catalog, 1);
    assert!(signatures.stacks().is_empty(), "nothing asked for yet");
    // While a stack renders nothing starts.
    signatures.want_stacks([dorsal]);
    signatures.poll(false, 100);
    assert_eq!(signatures.computed, 0);
    assert!(signatures.pending());
    settle(&mut signatures, true);
    signatures.refresh(&catalog, 1);
    // The newest saved render, not the older one.
    assert_eq!(signatures.stacks().get(&dorsal), Some(&vec![1.0, 0.5]));
    assert_eq!(signatures.subjects().get(&subject), Some(&vec![1.0, 0.5]));
    assert!(!signatures.stacks().contains_key(&side));
    // Asked again, a cached row costs nothing.
    signatures.want_stacks([dorsal, dorsal]);
    signatures.want_subjects([subject]);
    assert!(!signatures.pending());
    signatures.want_stacks([side]);
    settle(&mut signatures, true);
    signatures.refresh(&catalog, 1);
    assert_eq!(signatures.stacks().get(&side), Some(&vec![0.5, -1.0]));
    assert_eq!(signatures.computed, 2);
    signatures.flush();
    signatures.save();
    signatures.flush();
    // A new session reads the file and computes nothing.
    let mut again = DepthSignatures::opened_at(Some(path.clone()));
    settle(&mut again, true);
    again.refresh(&catalog, 1);
    again.want_stacks([dorsal, side]);
    assert!(!again.pending());
    assert_eq!(again.stacks().len(), 2);
    assert_eq!(again.computed, 0);
    // An unreadable file starts empty and is left until the next save.
    std::fs::write(&path, b"{ not json").unwrap();
    let mut broken = DepthSignatures::opened_at(Some(path.clone()));
    settle(&mut broken, true);
    broken.refresh(&catalog, 1);
    assert!(broken.stacks().is_empty());
    assert_eq!(std::fs::read(&path).unwrap(), b"{ not json");
}

#[test]
fn a_moved_run_shows_nothing_and_offscreen_keeps_its_cache_in_memory() {
    let files = jobs::tests::TestDirectory::new("depth-signature-missing");
    let (catalog, _, dorsal, _) = catalog_with_runs(files.path());
    std::fs::remove_file(files.path().join("dorsal-2").join("render.log")).unwrap();
    let mut signatures = DepthSignatures::opened_at(None);
    assert!(signatures.opened());
    signatures.refresh(&catalog, 1);
    signatures.want_stacks([dorsal]);
    settle(&mut signatures, true);
    signatures.refresh(&catalog, 1);
    assert!(signatures.stacks().is_empty());
    signatures.want_stacks([dorsal]);
    assert!(!signatures.pending(), "not retried");
    signatures.save();
    assert!(!files.path().join(FILE_NAME).exists());
}
