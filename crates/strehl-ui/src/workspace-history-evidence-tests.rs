//! Reopening runs whose per-plane maps are in the evidence file beside the
//! log, and the old hex-line runs beside them.
use super::*;
use crate::evidence_file::tests::{header_bytes, record_bytes, support_payload};
use crate::evidence_file::{FILE_NAME, VERSION};
use crate::pipeline::{DiagnosticKind, ShareSource, Stage};
use std::{fs, time::Duration};

struct Folder(PathBuf);
impl Folder {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "strehl-evidence-reopen-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }
    fn run(&self, name: &str, log: &str) -> Run {
        let directory = self.0.join(name);
        fs::create_dir_all(&directory).unwrap();
        let output = directory.join("result.tiff");
        image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
            4,
            4,
            image::Rgb([1000, 2000, 3000]),
        )
        .save(&output)
        .unwrap();
        fs::write(directory.join("render.log"), log).unwrap();
        serde_json::from_value(serde_json::json!({
            "directory": directory, "source": self.0.join("source"), "output": output,
            "log": directory.join("render.log"), "label": name, "created": 1_234_567,
            "status": "Saved", "frames": 3, "settings": {}, "exposure": null, "gate": null,
            "workers": 1, "pinned": false
        }))
        .unwrap()
    }
}
impl Drop for Folder {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

const WROTE: &str = "wrote: stack.tiff (4 x 4, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n";

fn replay(run: Run) -> PipelineProgress {
    reopen(run)
        .receiver
        .recv_timeout(Duration::from_secs(60))
        .unwrap()
        .unwrap()
        .1
}

#[test]
fn a_run_with_an_evidence_file_reopens_with_its_plane_maps() {
    let folder = Folder::new();
    // A stack map stays in the log (sequence 3); the plane maps around it
    // are in the file (sequences 1, 2, 4, 5).
    let log = format!(
        "planes: 4 x 2 per CFA plane\n\
         STREHL_UI_PROGRESS event=evidence-file path={FILE_NAME} version={VERSION}\n\
         STREHL_UI_PROGRESS event=frame-unplaced frame=2 reason=outside-the-reference-component\n\
         STREHL_UI_PROGRESS event=frame-finished index=0 processed=1 accepted=1 total=3\n\
         STREHL_UI_PROGRESS event=diagnostic seq=3 frame=0 level=0 kind=averaging scope=stack scale=linear width=2 height=1 min=0 max=1 folded=1 total=3 sampling=nearest data=ff00\n\
         {WROTE}"
    );
    let run = folder.run("evidence", &log);
    let mut file = header_bytes(&[([2, 1], [4, 2]), ([1, 1], [2, 1])], 3);
    file.extend(record_bytes(0, 0, 0, 1, &support_payload(&[false, true])));
    file.extend(record_bytes(0, 1, 0, 2, &support_payload(&[true])));
    file.extend(record_bytes(1, 0, 0, 4, &support_payload(&[true, true])));
    let mut energy = 0.5f32.to_le_bytes().to_vec();
    energy.extend(9.0f32.to_le_bytes());
    energy.extend([0, 255]);
    file.extend(record_bytes(1, 0, 2, 5, &energy));
    fs::write(run.directory.join(FILE_NAME), &file).unwrap();
    let progress = replay(run);
    assert_eq!(progress.stage, Stage::Complete);
    assert_eq!(
        progress.evidence_file,
        Some((FILE_NAME.to_owned(), VERSION))
    );
    assert_eq!(
        (progress.evidence_records, progress.evidence_refused),
        (4, 0)
    );
    assert_eq!(
        progress.unplaced_frames.get(&2).map(String::as_str),
        Some("outside-the-reference-component")
    );
    let archive = &progress.admission_archive;
    assert_eq!(archive.len(), 3);
    assert_eq!(
        archive.cells(0, 0).unwrap().1.collect::<Vec<_>>(),
        [false, true]
    );
    assert_eq!(archive.counts(1, 0), Some((1, 1)));
    assert_eq!(archive.counts(0, 1), Some((2, 2)));
    assert_eq!(archive.metadata(0, 1).unwrap().extent, [4, 2]);
    // The ring holds both sources in the engine's order.
    let ring: Vec<_> = progress
        .diagnostic_surfaces
        .iter()
        .map(|packet| (packet.sequence, packet.kind))
        .collect();
    assert_eq!(
        ring,
        [
            (1, DiagnosticKind::GateSupport),
            (2, DiagnosticKind::GateSupport),
            (3, DiagnosticKind::Averaging),
            (4, DiagnosticKind::GateSupport),
            (5, DiagnosticKind::FocusEnergy),
        ]
    );
    let share = progress.plane_share(0, 0).unwrap();
    assert_eq!((share.share, share.source), (0.5, ShareSource::Map));
    assert_eq!(
        progress.plane_share(0, 2),
        None,
        "the unplaced frame has no map"
    );
}

#[test]
fn more_than_eight_thousand_plane_maps_reopen_from_the_file() {
    let folder = Folder::new();
    let frames = 1100;
    let log = format!(
        "planes: 4 x 2 per CFA plane\n\
         STREHL_UI_PROGRESS event=evidence-file path={FILE_NAME} version={VERSION}\n{WROTE}"
    );
    let run = folder.run("long", &log);
    let levels: Vec<([u16; 2], [u32; 2])> = (0..8).map(|_| ([2, 1], [4, 2])).collect();
    let mut file = header_bytes(&levels, frames);
    let mut sequence = 0;
    for frame in 0..frames {
        for level in 0..8u8 {
            sequence += 1;
            let on = (frame as usize + level as usize).is_multiple_of(3);
            file.extend(record_bytes(
                frame,
                level,
                0,
                sequence,
                &support_payload(&[on, false]),
            ));
        }
    }
    fs::write(run.directory.join(FILE_NAME), &file).unwrap();
    let progress = replay(run);
    let archive = &progress.admission_archive;
    assert_eq!((archive.len(), archive.dropped()), (frames as usize * 8, 0));
    for level in 0..8 {
        assert_eq!(archive.frames(level).count(), frames as usize);
        let expected = usize::from((1099 + level).is_multiple_of(3));
        assert_eq!(archive.counts(level, 1099), Some((expected, 2)));
    }
    // The history pools the same maps: 1,100 planes into 1,024 bins.
    let history = progress
        .sampled_mask_history
        .iter()
        .find(|history| history.level == 0 && history.kind == DiagnosticKind::GateSupport)
        .unwrap();
    assert_eq!(history.observations(), frames as usize);
}

#[test]
fn a_damaged_evidence_file_costs_its_maps_not_the_reopen_and_hex_runs_still_parse() {
    let folder = Folder::new();
    let named = format!(
        "planes: 2 x 1 per CFA plane\n\
         STREHL_UI_PROGRESS event=evidence-file path={FILE_NAME} version={VERSION}\n\
         STREHL_UI_PROGRESS event=diagnostic seq=1 frame=1 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=3 sampling=nearest data=00ff\n\
         {WROTE}"
    );
    let run = folder.run("damaged", &named);
    fs::write(run.directory.join(FILE_NAME), b"not evidence at all").unwrap();
    let progress = replay(run);
    assert_eq!(progress.stage, Stage::Complete);
    assert_eq!(progress.evidence_records, 0);
    // The log's own hex map (an older engine's form) is still replayed.
    assert_eq!(
        progress
            .admission_archive
            .cells(0, 1)
            .unwrap()
            .1
            .collect::<Vec<_>>(),
        [false, true]
    );
    // A log cannot name a file outside its run.
    let escape = named.replace(&format!("path={FILE_NAME}"), "path=..\\escape.strehl");
    let progress = replay(folder.run("escape", &escape));
    assert_eq!(progress.evidence_file, None);
}

#[test]
fn the_replay_limit_is_lifted_only_for_runs_with_an_evidence_file() {
    let folder = Folder::new();
    let run = folder.run("limits", WROTE);
    assert_eq!(replay_limit(&run), 512 << 20, "an older hex-only run");
    fs::write(run.directory.join(FILE_NAME), b"").unwrap();
    assert_eq!(replay_limit(&run), 4 << 30);
}

#[test]
fn a_run_reopens_with_its_stack_maps_from_the_evidence_and_live_files() {
    use crate::evidence_file::LIVE_FILE_NAME;
    use crate::evidence_file::tests::{live_bytes, preview_pixels, sample_payload};
    let folder = Folder::new();
    let log = format!(
        "planes: 4 x 2 per CFA plane\n\
         STREHL_UI_PROGRESS event=evidence-file path={FILE_NAME} version={VERSION}\n\
         STREHL_UI_PROGRESS event=live-file path={LIVE_FILE_NAME} version=1\n\
         STREHL_UI_PROGRESS event=frame-finished index=1 processed=2 accepted=2 total=3\n\
         {WROTE}"
    );
    let run = folder.run("stack-maps", &log);
    let size = [300, 210];
    // The preview's samples name its pyramid level, which the header lists.
    let mut file = header_bytes(&[([2, 1], [4, 2]), ([1, 1], [2, 1])], 3);
    for (generation, base) in [(1u32, 1u32), (2, 5)] {
        let frame = generation - 1;
        file.extend(record_bytes(
            frame,
            0,
            0,
            base,
            &support_payload(&[true, false]),
        ));
        let mut averaging = generation.to_le_bytes().to_vec();
        averaging.extend(support_payload(&[generation == 2, true]));
        file.extend(record_bytes(frame, 0, 1, base + 1, &averaging));
        let pixels = preview_pixels(generation as usize, size);
        let sample = sample_payload(generation, size, (0.0, 500.0), &pixels);
        file.extend(record_bytes(frame, 1, 6, base + 3, &sample));
    }
    fs::write(run.directory.join(FILE_NAME), &file).unwrap();
    // The newest generation's coefficient map and whole preview.
    let live = live_bytes(
        3,
        &[
            (1, 0, 4, 7, 2, [2, 1], (-3.0, 3.0), vec![0, 255]),
            (1, 1, 5, 8, 2, size, (0.0, 500.0), preview_pixels(2, size)),
        ],
    );
    fs::write(run.directory.join(LIVE_FILE_NAME), &live).unwrap();
    let progress = replay(run);
    assert_eq!(progress.stage, Stage::Complete);
    assert_eq!(progress.live_file, Some((LIVE_FILE_NAME.to_owned(), 1)));
    // Accepted-prefix history of the averaging maps: both generations.
    let averaging = progress
        .sampled_mask_history
        .iter()
        .find(|history| history.kind == DiagnosticKind::Averaging)
        .unwrap();
    assert_eq!(averaging.observations(), 2);
    assert_eq!(
        averaging.bins[0].on_samples + averaging.bins[1].on_samples,
        3
    );
    // The revision trace from the samples: generation 1 to 2.
    let trace: Vec<_> = progress
        .revisions
        .history()
        .iter()
        .map(|r| (r.from, r.to, r.sequence))
        .collect();
    assert_eq!(trace, [(1, 2, 8)]);
    // The live view shows the whole newest preview, not a sample.
    let shown = progress.live_preview.latest.as_ref().unwrap();
    assert_eq!(
        (shown.width, shown.height, shown.folded, shown.sequence),
        (300, 210, 2, 8)
    );
    let ring: Vec<_> = progress
        .diagnostic_surfaces
        .iter()
        .map(|packet| (packet.sequence, packet.kind))
        .collect();
    assert!(ring.contains(&(7, DiagnosticKind::Coefficient)));
    assert!(ring.contains(&(8, DiagnosticKind::Preview)));
    assert!(ring.contains(&(6, DiagnosticKind::Averaging)));
    assert!(
        ring.iter()
            .all(|&(sequence, kind)| kind != DiagnosticKind::Preview || sequence == 8),
        "samples never enter the display ring"
    );
}
