//! Calibrate and compact, from the Capture screen (round 4, 2026-11-20).
//!
//! - **Calibrate step**: a short single-shot survey around the middle of the
//!   marked range, measured by `strehl focus-step`, suggests the focus step
//!   the subject's depth of field needs; the survey's files are deleted once
//!   measured. MEASURED on the scarab stack: its planes were twice as close as
//!   needed, and a render from every second plane lost nothing measurable.
//! - **Focus step** of a completed capture: the same measurement on the stack.
//! - **Compact**: `strehl compact`, first as an estimate (nothing written),
//!   then, only after an explicit confirmation, for real. Not lossless.
//!
//! Every engine run here is its own process at below-normal priority, with
//! the desktop's shared cache, so a capture or a render beside it keeps the
//! machine.
use anyhow::{Context, Result};
use serde_json::Value;
use std::{
    ffi::OsString,
    path::{Path, PathBuf},
    sync::mpsc,
};

/// One engine command in the background; its `--json` result.
pub(crate) struct EngineJob {
    rx: mpsc::Receiver<Result<Value>>,
}

impl EngineJob {
    pub fn start(engine: &Path, args: Vec<OsString>) -> Result<Self> {
        let json = std::env::temp_dir().join(format!(
            "strehl-capture-tool-{}-{}.json",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0)
        ));
        let mut command = crate::engine::command(engine)?;
        command.args(&args).arg("--json").arg(&json);
        crate::jobs::remove_experimental_overrides(&mut command, std::env::vars_os());
        command.env("STREHL_CACHE_DIR", strehl_cli::default_cache_root());
        command.env_remove("RAYON_NUM_THREADS");
        command
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            // CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS
            command.creation_flags(0x0800_0000 | 0x0000_4000);
        }
        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || {
            let result = (|| -> Result<Value> {
                let out = command.output().context("Start the Strehl engine")?;
                let value = std::fs::read(&json)
                    .ok()
                    .and_then(|b| serde_json::from_slice::<Value>(&b).ok());
                let _ = std::fs::remove_file(&json);
                if !out.status.success() {
                    let err = String::from_utf8_lossy(&out.stderr);
                    let line = err
                        .lines()
                        .rev()
                        .find(|l| !l.trim().is_empty())
                        .unwrap_or("the engine failed");
                    anyhow::bail!("{}", line.trim_start_matches("Error: "));
                }
                value.context("The engine wrote no result")
            })();
            let _ = tx.send(result);
        });
        Ok(Self { rx })
    }
    pub fn poll(&mut self) -> Option<Result<Value>> {
        match self.rx.try_recv() {
            Ok(r) => Some(r),
            Err(mpsc::TryRecvError::Empty) => None,
            Err(mpsc::TryRecvError::Disconnected) => {
                Some(Err(anyhow::anyhow!("The engine stopped without a result")))
            }
        }
    }
}

/// A background job whose last result is kept for display.
#[derive(Default)]
pub(crate) struct Slot {
    pub job: Option<EngineJob>,
    pub result: Option<Result<Value, String>>,
    /// The folder the job or result belongs to.
    pub folder: Option<PathBuf>,
}

impl Slot {
    pub fn start(&mut self, engine: Option<&Path>, folder: &Path, args: Vec<OsString>) {
        self.folder = Some(folder.to_path_buf());
        self.result = None;
        self.job = None;
        match engine {
            Some(engine) => match EngineJob::start(engine, args) {
                Ok(job) => self.job = Some(job),
                Err(e) => self.result = Some(Err(format!("{e:#}"))),
            },
            None => self.result = Some(Err("The Strehl engine was not found".into())),
        }
    }
    pub fn poll(&mut self) {
        if let Some(job) = &mut self.job
            && let Some(r) = job.poll()
        {
            self.result = Some(r.map_err(|e| format!("{e:#}")));
            self.job = None;
        }
    }
    pub fn running(&self) -> bool {
        self.job.is_some()
    }
    /// The result, if it belongs to `folder`.
    pub fn for_folder(&self, folder: &Path) -> Option<&Result<Value, String>> {
        (self.folder.as_deref() == Some(folder))
            .then_some(self.result.as_ref())
            .flatten()
    }
}

/// Survey positions for a step calibration: `n` positions `spacing` apart,
/// centred on the middle of `[start, end]` and kept inside it, in the
/// capture direction.
pub(crate) fn survey_positions(start: u16, end: u16, spacing: u16, n: usize) -> Vec<u16> {
    let (lo, hi) = (start.min(end) as i64, start.max(end) as i64);
    let spacing = i64::from(spacing.max(1));
    let span = spacing * (n as i64 - 1);
    let mid = (lo + hi) / 2;
    let first = (mid - span / 2).max(lo).min((hi - span).max(lo));
    let mut positions: Vec<u16> = (0..n as i64)
        .map(|i| first + i * spacing)
        .filter(|p| *p <= hi.max(first))
        .map(|p| p.clamp(0, 65535) as u16)
        .collect();
    positions.dedup();
    if start > end {
        positions.reverse();
    }
    positions
}

/// The calibration's stages, advanced once a frame by the workspace.
pub(crate) enum Calibration {
    Idle,
    /// Waiting for the camera to take one RAW a plane.
    Switching {
        restore_four: bool,
        positions: Vec<u16>,
        round: u8,
    },
    /// The survey is being captured.
    Capturing {
        restore_four: bool,
        sequence: u64,
        round: u8,
        spacing: u16,
    },
    /// The survey is being measured.
    Measuring {
        restore_four: bool,
        run: PathBuf,
        job: EngineJob,
        round: u8,
        spacing: u16,
    },
    /// Back to four RAWs a plane, then done.
    Restoring {
        result: Value,
    },
    Done(Value),
    Failed(String),
}

/// The survey's first spacing, in focus units. MEASURED sharp widths on the
/// studio rig (2026-11-20): 69-115 units, so 8 samples them several times.
pub(crate) const SURVEY_SPACING: u16 = 8;
/// Positions in one survey: 25 single RAWs, about 55 s at 0.6 s.
pub(crate) const SURVEY_PLANES: usize = 25;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn survey_positions_centre_on_the_range_and_keep_its_direction() {
        let p = survey_positions(1000, 3000, 8, 25);
        assert_eq!(p.len(), 25);
        assert_eq!(p[0], 1904);
        assert!(p.windows(2).all(|w| w[1] == w[0] + 8));
        let r = survey_positions(3000, 1000, 8, 25);
        assert_eq!(r.first(), p.last());
        assert!(r.windows(2).all(|w| w[0] == w[1] + 8));
        // A range shorter than the survey: kept inside it.
        let short = survey_positions(1000, 1100, 8, 25);
        assert!(short.iter().all(|&x| (1000..=1100).contains(&x)));
        assert_eq!(short[0], 1000);
    }
}
