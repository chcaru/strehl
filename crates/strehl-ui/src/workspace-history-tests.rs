//! Independent catalog/replay witnesses. These use distinct paths and deliberately
//! non-default settings; a catalog that drops settings, conflates labels, or
//! returns success without reading the saved observations must fail.
use super::*;
use crate::{jobs::Resampler, pipeline::Stage};
use std::{fs, time::Duration};

struct Files(PathBuf);
impl Files {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "strehl-workspace-review-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }
    fn catalog(&self) -> PathBuf {
        self.0.join("catalog/workspace.json")
    }
    fn run(&self, name: &str) -> Run {
        let directory = self.0.join(name);
        fs::create_dir_all(&directory).unwrap();
        let output = directory.join("stack.tiff");
        image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
            4,
            4,
            image::Rgb([1000, 2000, 3000]),
        )
        .save(&output)
        .unwrap();
        serde_json::from_value(serde_json::json!({
            "directory": directory, "source": self.0.join("source").join(name), "output": output,
            "log": self.0.join(name).join("activity.log"), "label": "same display label", "created": 1_234_567,
            "status": "Saved", "frames": 3, "settings": {
                "pyramid_bands": 5, "pyramid_exponent": 1.6, "pyramid_sharpen": 0.25,
                "resampler": "Lanczos3", "binned": true, "correct_lateral_ca": false, "crop_to_coverage": true
            }, "exposure": -0.75, "gate": 0.65, "workers": 3, "pinned": false
        })).unwrap()
    }
}
impl Drop for Files {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn catalog_roundtrips_exact_settings_pins_and_layout_and_replaces_an_existing_file() {
    let files = Files::new();
    let mut catalog = Catalog::load(Some(files.catalog()));
    let first = files.run("first");
    let mut second = files.run("second");
    second.pinned = true;
    second.status = "Cancelled".into();
    catalog.layout = WorkspaceLayout {
        network: 0.28,
        detail: 0.70,
        final_detail: 0.31,
        lower: 0.06,
        fingerprint: 0.09,
        focus_photo: true,
    };
    catalog.add(first.clone());
    catalog.save().unwrap();
    catalog.add(second.clone());
    catalog.save().unwrap();
    let restored = Catalog::load(Some(files.catalog()));
    assert_eq!(
        restored.runs.len(),
        2,
        "identical labels do not identify identical runs"
    );
    assert_eq!(restored.layout, catalog.layout);
    assert_eq!(restored.runs[0].directory, second.directory);
    assert_eq!(restored.runs[0].status, "Cancelled");
    assert!(restored.runs[0].pinned);
    let run = &restored.runs[1];
    assert_eq!(run.settings, first.settings);
    assert_eq!(run.settings.resampler, Resampler::Lanczos3);
    assert_eq!(run.source, first.source);
    assert_eq!(run.output, first.output);
    assert_eq!(
        (run.exposure, run.gate, run.workers),
        (Some(-0.75), Some(0.65), 3)
    );
    let entries: std::collections::BTreeSet<_> = fs::read_dir(files.catalog().parent().unwrap())
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();
    assert_eq!(
        entries,
        std::collections::BTreeSet::from([files.catalog(), files.catalog().with_extension("lock")]),
        "Only the completed catalog and persistent lock inode may remain; no temporary publication files"
    );
}

#[test]
fn adding_same_directory_updates_that_run_but_pinned_entries_survive_normal_eviction() {
    let files = Files::new();
    let mut catalog = Catalog::default();
    let mut pinned = files.run("pinned");
    pinned.pinned = true;
    catalog.add(pinned.clone());
    let base = files.run("base");
    for i in 0..130 {
        let mut run = base.clone();
        run.directory = files.0.join(format!("render-{i}"));
        catalog.add(run);
    }
    assert!(
        catalog
            .runs
            .iter()
            .any(|run| run.directory == pinned.directory && run.pinned)
    );
    let latest = catalog.runs[0].directory.clone();
    let mut updated = catalog.runs[0].clone();
    updated.label = "renamed deliberately".into();
    catalog.add(updated);
    assert_eq!(
        catalog
            .runs
            .iter()
            .filter(|run| run.directory == latest)
            .count(),
        1
    );
    assert_eq!(catalog.runs[0].label, "renamed deliberately");
    assert!(catalog.runs.len() <= 128);
}

#[test]
fn a_new_run_cannot_silently_disappear_when_every_previous_run_is_pinned() {
    let files = Files::new();
    let base = files.run("base");
    let mut catalog = Catalog::default();
    for i in 0..128 {
        let mut run = base.clone();
        run.directory = files.0.join(format!("pinned-{i}"));
        run.pinned = true;
        catalog.add(run);
    }
    assert_eq!(
        catalog.runs.iter().filter(|run| run.pinned).count(),
        128,
        "fixture must actually fill the catalog with pins"
    );
    let latest = files.run("latest");
    catalog.add(latest.clone());
    assert!(
        catalog
            .runs
            .iter()
            .any(|run| run.directory == latest.directory),
        "starting a new stack must retain its history entry even at the pin limit"
    );
}

#[test]
fn damaged_catalog_is_recoverable_after_the_next_workspace_save() {
    let files = Files::new();
    let path = files.catalog();
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    let damaged = b"{\"runs\":[{broken-but-recoverable-run-data";
    fs::write(&path, damaged).unwrap();
    let catalog = Catalog::load(Some(path.clone()));
    // A refused save is acceptable; a successful save must preserve the old
    // bytes under a recovery name. Neither case silently destroys the record.
    let _ = catalog.save();
    let retained = fs::read_dir(path.parent().unwrap())
        .unwrap()
        .flatten()
        .any(|entry| fs::read(entry.path()).is_ok_and(|bytes| bytes == damaged));
    assert!(
        retained,
        "unreadable history must remain recoverable before replacement"
    );
}

#[test]
fn reopening_replays_actual_masks_utf8_counts_and_terminal_status_without_writing_assets() {
    let files = Files::new();
    let run = files.run("saved");
    let mut log = vec![b'\n'; 32756];
    log.extend_from_slice("camera: caméra · スタック\nplanes: 2 x 2 per CFA plane\nbands: 7 Laplacian levels + 1 base, coarsest 1 x 1\nSTREHL_UI_PROGRESS event=stage name=alignment total=3\nSTREHL_UI_PROGRESS event=frame-finished index=0 processed=1 accepted=1 total=3\nSTREHL_UI_PROGRESS event=frame-finished index=1 processed=2 accepted=1 total=3\nSTREHL_UI_PROGRESS event=diagnostic seq=1 frame=1 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=3 sampling=nearest data=00ff\nwrote: stack.tiff (4 x 4, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)".as_bytes());
    fs::write(&run.log, &log).unwrap();
    let before = fs::read(&run.output).unwrap();
    let task = reopen(run.clone());
    let (restored, progress) = task
        .receiver
        .recv_timeout(Duration::from_secs(10))
        .unwrap()
        .unwrap();
    assert_eq!(restored.directory, run.directory);
    assert_eq!(progress.camera.as_deref(), Some("caméra · スタック"));
    assert_eq!(
        (progress.frames_processed, progress.frames_accepted),
        (Some(2), Some(1))
    );
    assert_eq!(progress.stage, Stage::Complete);
    assert!(
        progress.output_geometry.is_some(),
        "last non-newline writer receipt must be parsed"
    );
    let (_, cells) = progress
        .admission_archive
        .cells(0, 1)
        .expect("saved mask must be replayed");
    assert_eq!(cells.collect::<Vec<_>>(), [false, true]);
    assert_eq!(fs::read(&run.output).unwrap(), before);
    assert_eq!(fs::read(&run.log).unwrap(), log);
    let mut cancelled = run;
    cancelled.status = "Cancelled".into();
    let task = reopen(cancelled);
    let (_, progress) = task
        .receiver
        .recv_timeout(Duration::from_secs(10))
        .unwrap()
        .unwrap();
    assert_eq!(
        progress.stage,
        Stage::Cancelled,
        "a cancelled history entry must not become a completed stack"
    );
}

#[test]
fn missing_activity_is_an_explicit_replay_error() {
    let files = Files::new();
    let run = files.run("no-log");
    assert!(!run.log.exists());
    let task = reopen(run);
    let result = task.receiver.recv_timeout(Duration::from_secs(10)).unwrap();
    assert!(
        result.is_err(),
        "missing diagnostics cannot silently replay an empty successful run"
    );
}

#[test]
fn saved_status_requires_an_output_and_writer_receipt_not_just_a_catalog_label() {
    let files = Files::new();
    let run = files.run("unpublished");
    fs::write(
        &run.log,
        "STREHL_UI_PROGRESS event=stage name=render total=3\n",
    )
    .unwrap();
    let task = reopen(run.clone());
    let result = task.receiver.recv_timeout(Duration::from_secs(10)).unwrap();
    assert!(
        result.is_err(),
        "a preexisting TIFF plus Saved label cannot fabricate a writer receipt"
    );
    fs::write(&run.log, "wrote: stack.tiff (4 x 4, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n").unwrap();
    fs::remove_file(&run.output).unwrap();
    let task = reopen(run);
    let result = task.receiver.recv_timeout(Duration::from_secs(10)).unwrap();
    assert!(
        result.is_err(),
        "a writer receipt cannot conceal a deleted output"
    );
}
