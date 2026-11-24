//! A test shot (Studio 2, 7.4): one exposure at the current focus, to judge
//! ISO and shutter on the RAW before a stack.
//!
//! The desktop sends `capture_positions` with one position. A host whose
//! state has `capabilities.test_shot` journals it as `capture_kind` "test"
//! (H2); an older host makes it an ordinary one-position run, which this
//! desktop remembers instead. Either way the run is not followed, not listed
//! among the stacks and not handed to the library. Its RAW is decoded on a
//! worker with the engine's decoder and its levels read against the frame's
//! own black and white levels: these are RAW measurements, unlike the live
//! preview's histogram, which is the camera's JPEG.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::{Duration, Instant},
};

use crate::capture_client::{Snapshot, host::HostPhase};

/// How long a test shot may take beyond any light warmup: the approach, one
/// group of exposures and the PC receiving it.
pub(crate) const TEST_SHOT_TIMEOUT: Duration = Duration::from_secs(120);

/// A test RAW's levels over the decoded active area.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct RawLevels {
    pub path: PathBuf,
    pub camera: String,
    pub iso: Option<f32>,
    pub black: f32,
    pub white: f32,
    /// Active-area samples read.
    pub samples: u64,
    /// Share of the brightest colour's samples at or above the white level
    /// (plan Q4: pooled colours hid a pinned green).
    pub clipped_share: f64,
    /// The 1st percentile above black, as a share of black to white (all
    /// colours).
    pub shadow_level: f64,
    /// The median, the same way (all colours).
    pub median_level: f64,
    /// The brightest colour's 99.9th percentile, the same way.
    pub highlight_level: f64,
    /// Red, green (both sites) and blue on their own.
    pub colours: [ColourLevels; 3],
    /// Which of them is brightest at the 99.9th percentile (0 red, 1 green,
    /// 2 blue); the advice reads that one.
    pub brightest: usize,
    /// Plan S4: the levels are the subject's (its outline's 8 px cells),
    /// not the whole frame's.
    pub in_subject: bool,
}

/// One colour's levels in a test RAW.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct ColourLevels {
    pub clipped_share: f64,
    pub median_level: f64,
    pub highlight_level: f64,
}

/// "red", "green", "blue".
pub(crate) fn colour_name(colour: usize) -> &'static str {
    ["red", "green", "blue"][colour.min(2)]
}

impl RawLevels {
    pub fn public(&self) -> Value {
        json!({"path":self.path,"camera":self.camera,"iso":self.iso,"black":self.black,"white":self.white,
            "samples":self.samples,"clipped_share":self.clipped_share,"shadow_level":self.shadow_level,
            "median_level":self.median_level,"highlight_level":self.highlight_level,
            "brightest":colour_name(self.brightest),
            "colours":self.colours.iter().enumerate().map(|(i,c)|json!({"colour":colour_name(i),
                "clipped_share":c.clipped_share,"median_level":c.median_level,"highlight_level":c.highlight_level})).collect::<Vec<_>>(),
            "basis":"the test RAW's decoded active area per colour (RGGB), against its own black and white levels; clipped share and highlight are the brightest colour's"})
    }
}

/// Pooled levels: samples, clipped share, 1st, 50th and 99.9th percentile.
type Pooled = (u64, f64, f64, f64, f64);

/// Levels of RGGB samples (red at the active area's origin) against `black`
/// and `white`, pooled and per colour (full 16-bit histograms: exact
/// percentiles, no sampling).
#[cfg(test)]
fn levels_of<'a>(
    rows: impl Iterator<Item = &'a [u16]>,
    black: f32,
    white: f32,
) -> Result<(Pooled, [ColourLevels; 3])> {
    levels_in(rows, black, white, None)
}

/// [`levels_of`] over the sites whose 8 px cell is set in `mask` (`cols`
/// cells a row), or over every site.
fn levels_in<'a>(
    rows: impl Iterator<Item = &'a [u16]>,
    black: f32,
    white: f32,
    mask: Option<(&[bool], usize)>,
) -> Result<(Pooled, [ColourLevels; 3])> {
    ensure!(
        white > black,
        "The RAW reports no usable range between black and white"
    );
    let mut histograms = vec![vec![0u64; 65536]; 3];
    for (y, row) in rows.enumerate() {
        for (x, &v) in row.iter().enumerate() {
            if let Some((cells, cols)) = mask
                && !cells.get((y / 8) * cols + x / 8).copied().unwrap_or(false)
            {
                continue;
            }
            let colour = match (y % 2, x % 2) {
                (0, 0) => 0,
                (1, 1) => 2,
                _ => 1,
            };
            histograms[colour][usize::from(v)] += 1;
        }
    }
    let pooled: Vec<u64> = (0..65536)
        .map(|i| histograms.iter().map(|h| h[i]).sum())
        .collect();
    let clip_from = white.ceil().clamp(0.0, 65535.0) as usize;
    let stats = |histogram: &[u64]| {
        let samples: u64 = histogram.iter().sum();
        let clipped: u64 = histogram[clip_from..].iter().sum();
        let level = |share: f64| -> f64 {
            let target = ((share * samples as f64).ceil() as u64).max(1);
            let mut seen = 0;
            let code = histogram
                .iter()
                .position(|n| {
                    seen += n;
                    seen >= target
                })
                .unwrap_or(65535);
            ((code as f64 - f64::from(black)) / f64::from(white - black)).clamp(0.0, 1.0)
        };
        (
            samples,
            clipped as f64 / samples.max(1) as f64,
            level(0.01),
            level(0.5),
            level(0.999),
        )
    };
    let all = stats(&pooled);
    ensure!(all.0 > 0, "The RAW has no active samples");
    let colours = [0, 1, 2].map(|c| {
        let (_, clipped_share, _, median_level, highlight_level) = stats(&histograms[c]);
        ColourLevels {
            clipped_share,
            median_level,
            highlight_level,
        }
    });
    Ok((all, colours))
}

/// The colour the advice reads: the most clipped, else the brightest.
fn brightest_of(colours: &[ColourLevels; 3]) -> usize {
    (0..3)
        .max_by(|&a, &b| {
            let key = |c: &ColourLevels| (c.clipped_share, c.highlight_level);
            key(&colours[a])
                .partial_cmp(&key(&colours[b]))
                .unwrap_or(std::cmp::Ordering::Equal)
        })
        .unwrap_or(1)
}

/// Decodes `path` and reads its levels. Worker thread only: a full decode.
pub(crate) fn read_levels(
    path: &Path,
    subject: Option<&strehl_capture::model::Subject>,
) -> Result<RawLevels> {
    let frame = strehl_raw::decode(path)
        .with_context(|| format!("Decoding {}", crate::display_path::display_path(path)))?;
    // Plan S4: the subject's cells only, when it has an outline that holds
    // enough of the frame to meter.
    let (w, h) = (frame.active.width, frame.active.height);
    let (cols, rows) = (w.div_ceil(8), h.div_ceil(8));
    let cells = subject
        .map(|s| {
            strehl_core::subject::rasterize(&s.rings, cols, rows, [8.0 / w as f64, 8.0 / h as f64])
        })
        .filter(|cells| cells.iter().filter(|c| **c).count() >= 64);
    let ((samples, _, shadow_level, median_level, _), colours) = levels_in(
        (0..frame.active.height).map(|y| frame.active_row(y)),
        frame.levels.black,
        frame.levels.white,
        cells.as_deref().map(|c| (c, cols)),
    )?;
    let brightest = brightest_of(&colours);
    Ok(RawLevels {
        path: path.to_owned(),
        camera: frame.camera.clone(),
        iso: frame.iso,
        black: frame.levels.black,
        white: frame.levels.white,
        samples,
        clipped_share: colours[brightest].clipped_share,
        shadow_level,
        median_level,
        highlight_level: colours[brightest].highlight_level,
        colours,
        brightest,
        in_subject: cells.is_some(),
    })
}

/// The first RAW of a run with a durable receipt, as stored on this PC.
pub(crate) fn first_raw(folder: &Path) -> Result<PathBuf> {
    let text = std::fs::read_to_string(folder.join("transfer-receipts.jsonl"))
        .context("Read the test shot's receipts")?;
    for line in text.lines() {
        let Ok(r) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        let Some(name) = r["logical_name"].as_str().filter(|n| n.ends_with(".ARW")) else {
            continue;
        };
        if r["durable"] != true || r["ok"] != true {
            continue;
        }
        let stored = match r["storage_encoding"].as_str() {
            Some("identity") | None => name.to_owned(),
            Some(_) => format!("{name}.straw"),
        };
        return Ok(folder.join(stored));
    }
    anyhow::bail!("The test shot's RAW has not reached this PC")
}

/// Reads the run's first RAW (worker thread).
fn read_run(folder: &Path, subject: Option<&strehl_capture::model::Subject>) -> Result<RawLevels> {
    read_levels(&first_raw(folder)?, subject)
}

/// The test shot's stages, advanced by the workspace once a frame.
pub(crate) enum TestShot {
    Idle,
    /// Sent; the host is taking it as `sequence`.
    Capturing {
        sequence: u64,
        deadline: Instant,
        /// The run, once seen being written.
        folder: Option<PathBuf>,
    },
    /// Its RAW is decoded on a worker.
    Reading {
        folder: PathBuf,
        task: crate::jobs::Task<RawLevels>,
    },
    Done {
        folder: PathBuf,
        levels: RawLevels,
        /// When its levels were read.
        taken: std::time::SystemTime,
    },
    Failed(String),
}

impl TestShot {
    pub fn running(&self) -> bool {
        matches!(self, Self::Capturing { .. } | Self::Reading { .. })
    }
    pub fn stage(&self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::Capturing { .. } => "capturing",
            Self::Reading { .. } => "reading",
            Self::Done { .. } => "done",
            Self::Failed(_) => "failed",
        }
    }
    /// The sequence the host is taking the test shot as.
    pub fn sequence(&self) -> Option<u64> {
        match self {
            Self::Capturing { sequence, .. } => Some(*sequence),
            _ => None,
        }
    }
    pub fn gives_up_in(&self, now: Instant) -> Option<Duration> {
        match self {
            Self::Capturing { deadline, .. } => Some(deadline.saturating_duration_since(now)),
            _ => None,
        }
    }
    /// Stops waiting: the camera is left as it is, and the run, once it is
    /// seen, is still kept out of the lists.
    pub fn stop(&mut self) {
        if self.running() {
            *self = Self::Failed("Stopped waiting for the test shot".into());
        }
    }
    /// Advances on a fresh state. Returns a run folder the caller must
    /// remember as a test shot (`Connection::mark_test_run`).
    pub fn poll(&mut self, s: &Snapshot, now: Instant) -> Option<PathBuf> {
        let state = std::mem::replace(self, Self::Idle);
        let mut mark = None;
        *self = match state {
            Self::Capturing {
                sequence,
                deadline,
                mut folder,
            } => {
                let host = &s.host;
                let ours = host.sequence_id == Some(sequence);
                if ours
                    && host.phase.capturing()
                    && let Some(run) = &s.in_progress
                    && folder.as_ref() != Some(&run.folder)
                {
                    folder = Some(run.folder.clone());
                    mark = folder.clone();
                }
                if ours && !host.busy && host.phase == HostPhase::Complete {
                    match host.last_receipt_run().or(folder) {
                        Some(run) if host.storage.mode.as_deref() == Some("host-pc") => {
                            mark = Some(run.clone());
                            let worker = run.clone();
                            // Plan S4: metered in the subject's outline.
                            let subject = host.plan.as_ref().and_then(|p| p.subject.clone());
                            Self::Reading {
                                folder: run,
                                task: crate::jobs::spawn_task("strehl-test-shot", move |_| {
                                    read_run(&worker, subject.as_ref())
                                }),
                            }
                        }
                        Some(_) | None if host.storage.mode.as_deref() != Some("host-pc") => {
                            Self::Failed(
                                "The test shot was saved on the camera's card: its levels can be read only from a RAW on this PC".into(),
                            )
                        }
                        _ => Self::Failed("The test shot's folder was not reported".into()),
                    }
                } else if ours
                    && !host.busy
                    && matches!(
                        host.phase,
                        HostPhase::Stopped | HostPhase::Fault | HostPhase::Disconnected
                    )
                {
                    Self::Failed("The test shot did not finish".into())
                } else if now >= deadline {
                    Self::Failed("The test shot did not finish in time; check the camera".into())
                } else {
                    Self::Capturing {
                        sequence,
                        deadline,
                        folder,
                    }
                }
            }
            Self::Reading { folder, task } => match task.receiver.try_recv() {
                Ok(Ok(levels)) => Self::Done {
                    folder,
                    levels,
                    taken: std::time::SystemTime::now(),
                },
                Ok(Err(e)) => Self::Failed(e),
                Err(std::sync::mpsc::TryRecvError::Empty) => Self::Reading { folder, task },
                Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                    Self::Failed("Reading the test shot stopped without a result".into())
                }
            },
            other => other,
        };
        mark
    }
    /// For snapshots (`capture.tools.test_shot`).
    pub fn public(&self, now: Instant) -> Value {
        let (folder, levels, error) = match self {
            Self::Capturing { folder, .. } => (folder.clone(), Value::Null, None),
            Self::Reading { folder, .. } => (Some(folder.clone()), Value::Null, None),
            Self::Done { folder, levels, .. } => (Some(folder.clone()), levels.public(), None),
            Self::Failed(e) => (None, Value::Null, Some(e.clone())),
            Self::Idle => (None, Value::Null, None),
        };
        json!({"stage":self.stage(),"folder":folder,"levels":levels,"error":error,
            "gives_up_seconds":self.gives_up_in(now).map(|d| d.as_secs_f64())})
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    /// Percentiles and the clipped share are exact over the samples, and
    /// measured from black to the frame's own white level.
    #[test]
    fn raw_levels_are_read_against_black_and_white() {
        // 1000 samples: 10 at black, 980 at mid-range, 10 at white or above.
        let mut row = vec![512u16; 10];
        row.extend(std::iter::repeat_n(8448u16, 980));
        row.extend([15360u16; 5]);
        row.extend([16383u16; 5]);
        let ((samples, clipped, shadow, median, highlight), _) =
            levels_of([row.as_slice()].into_iter(), 512.0, 15360.0).unwrap();
        assert_eq!(samples, 1000);
        assert!((clipped - 0.01).abs() < 1e-12);
        assert_eq!(shadow, 0.0, "the 1st percentile is at black");
        let mid = (8448.0 - 512.0) / (15360.0 - 512.0);
        assert!((median - mid).abs() < 1e-12);
        assert_eq!(highlight, 1.0);
        assert!(levels_of([row.as_slice()].into_iter(), 100.0, 100.0).is_err());
        assert!(levels_of(std::iter::empty(), 0.0, 1.0).is_err());
    }

    /// Plan S4: with a subject, only its cells count: a bright backdrop
    /// outside it does not set the exposure.
    #[test]
    fn levels_count_only_the_subjects_cells() {
        // 64 x 64 sites: the left half pinned, the right half dim.
        let rows: Vec<Vec<u16>> = (0..64)
            .map(|_| (0..64).map(|x| if x < 32 { 16383 } else { 3000 }).collect())
            .collect();
        let cols = 8;
        let right: Vec<bool> = (0..64).map(|i| i % cols >= 4).collect();
        let ((_, frame_clipped, ..), _) =
            levels_in(rows.iter().map(Vec::as_slice), 512.0, 15360.0, None).unwrap();
        let ((_, subject_clipped, ..), colours) = levels_in(
            rows.iter().map(Vec::as_slice),
            512.0,
            15360.0,
            Some((&right, cols)),
        )
        .unwrap();
        assert!(frame_clipped > 0.4);
        assert_eq!(subject_clipped, 0.0);
        assert!(colours[1].highlight_level < 0.2);
    }

    /// Plan Q4: a frame whose green pins while red and blue sit low reads
    /// green clipped, at green's own share, not the pooled figure (the
    /// scarab's plane 162 pooled 0.71 with green pinned).
    #[test]
    fn levels_are_per_colour_and_the_brightest_is_named() {
        // RGGB rows: R G / G B. Green at the pin on every third green site.
        let width = 600;
        let rows: Vec<Vec<u16>> = (0..400)
            .map(|y| {
                (0..width)
                    .map(|x| match (y % 2, x % 2) {
                        (0, 0) => 3000,
                        (1, 1) => 2000,
                        _ if (x + y) % 3 == 0 => 16383,
                        _ => 9000,
                    })
                    .collect()
            })
            .collect();
        let ((_, pooled_clipped, ..), colours) =
            levels_of(rows.iter().map(Vec::as_slice), 512.0, 15360.0).unwrap();
        let green = brightest_of(&colours);
        assert_eq!(colour_name(green), "green");
        assert!(colours[1].clipped_share > 0.3, "{:?}", colours[1]);
        assert_eq!(colours[0].clipped_share, 0.0);
        assert_eq!(colours[1].highlight_level, 1.0);
        assert!(colours[1].clipped_share > 1.9 * pooled_clipped);
    }

    #[test]
    fn the_first_durable_raw_is_found_as_stored() {
        let dir = tempfile::tempdir().unwrap();
        let lines = [
            json!({"logical_name":"manifest.json","ok":true,"durable":true}),
            json!({"logical_name":"frame-000001.ARW","ok":true,"durable":false}),
            json!({"logical_name":"frame-000002.ARW","ok":true,"durable":true,"storage_encoding":"strehl-archive-v2"}),
        ]
        .map(|v| v.to_string());
        std::fs::write(dir.path().join("transfer-receipts.jsonl"), lines.join("\n")).unwrap();
        assert_eq!(
            first_raw(dir.path()).unwrap(),
            dir.path().join("frame-000002.ARW.straw")
        );
        std::fs::write(dir.path().join("transfer-receipts.jsonl"), "").unwrap();
        assert!(first_raw(dir.path()).is_err());
    }

    fn snapshot(state: Value) -> Snapshot {
        let mut s = Snapshot {
            online: true,
            observed: Some(Instant::now()),
            ..Default::default()
        };
        s.set_state(state);
        s
    }

    /// The run is remembered as a test shot as soon as it is seen, its RAW
    /// is read once the host completes it, and a card-only shot or another
    /// sequence's end does not read anything.
    #[test]
    fn a_test_shot_marks_its_run_and_reads_its_raw_on_completion() {
        let dir = tempfile::tempdir().unwrap();
        let run = dir.path().join("stack-1");
        std::fs::create_dir(&run).unwrap();
        let now = Instant::now();
        let mut shot = TestShot::Capturing {
            sequence: 5,
            deadline: now + TEST_SHOT_TIMEOUT,
            folder: None,
        };
        let mut s = snapshot(
            json!({"camera_revision":1,"plan_revision":1,"sequence_id":5,"phase":"capturing","busy":true}),
        );
        s.in_progress = Some(crate::capture_client::InProgress {
            folder: run.clone(),
            idle: Duration::ZERO,
            test: false,
        });
        assert_eq!(shot.poll(&s, now), Some(run.clone()));
        assert_eq!(shot.poll(&s, now), None, "marked once");
        // Another sequence completing is not this test shot.
        let other = snapshot(
            json!({"camera_revision":1,"plan_revision":1,"sequence_id":4,"phase":"complete","busy":false}),
        );
        shot.poll(&other, now);
        assert_eq!(shot.stage(), "capturing");
        let done = snapshot(
            json!({"camera_revision":2,"plan_revision":1,"sequence_id":5,"phase":"complete",
            "busy":false,"storage":{"mode":"host-pc","receipt":{"path":run.join("frame-000001.ARW").display().to_string()}}}),
        );
        assert_eq!(shot.poll(&done, now), Some(run.clone()));
        assert_eq!(shot.stage(), "reading");
        // No receipts in the fixture: the worker reports why.
        let end = Instant::now() + Duration::from_secs(10);
        while shot.stage() == "reading" {
            assert!(Instant::now() < end);
            std::thread::sleep(Duration::from_millis(10));
            shot.poll(&done, now);
        }
        match &shot {
            TestShot::Failed(e) => assert!(e.contains("receipts"), "{e}"),
            _ => panic!("{}", shot.stage()),
        }
        // On the card: nothing to read on this PC.
        let mut card = TestShot::Capturing {
            sequence: 5,
            deadline: now + TEST_SHOT_TIMEOUT,
            folder: None,
        };
        let sd = snapshot(
            json!({"camera_revision":2,"plan_revision":1,"sequence_id":5,"phase":"complete",
            "busy":false,"storage":{"mode":"camera-sd"}}),
        );
        card.poll(&sd, now);
        assert!(matches!(&card, TestShot::Failed(e) if e.contains("card")));
        // Giving up, and stopping by hand.
        let mut late = TestShot::Capturing {
            sequence: 9,
            deadline: now,
            folder: None,
        };
        late.poll(&s, now);
        assert!(matches!(&late, TestShot::Failed(e) if e.contains("in time")));
        let mut stopped = TestShot::Capturing {
            sequence: 9,
            deadline: now + TEST_SHOT_TIMEOUT,
            folder: None,
        };
        stopped.stop();
        assert_eq!(stopped.stage(), "failed");
    }
}
