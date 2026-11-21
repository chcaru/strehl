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
//! machine. The desktop owns that process (Studio 2, 6.6): a job can be
//! cancelled, reports how long it has run, and dropping it ends the engine.
//!
//! Every wait here gives up after a named time and can be stopped by hand
//! (Studio 2 P0 item 10): [`Calibration::gives_up_in`], [`ConnectWait`].
use anyhow::{Context, Result};
use serde_json::{Value, json};
use std::{
    ffi::OsString,
    path::{Path, PathBuf},
    sync::{
        Arc, Mutex,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    time::{Duration, Instant},
};

use crate::capture_client::{Snapshot, host::HostPhase};
use crate::jobs::OwnedChild;

/// How often the job's thread checks the engine for its exit or a cancel.
const JOB_POLL: Duration = Duration::from_millis(50);

/// One engine command in the background; its `--json` result.
pub(crate) struct EngineJob {
    rx: mpsc::Receiver<Result<Value>>,
    /// The running engine, shared with the job's thread, which reaps it.
    child: Arc<Mutex<Option<OwnedChild>>>,
    cancelled: Arc<AtomicBool>,
    started: Instant,
}

impl EngineJob {
    pub fn start(engine: &Path, args: Vec<OsString>) -> Result<Self> {
        let stamp = format!(
            "{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0)
        );
        let json = std::env::temp_dir().join(format!("strehl-capture-tool-{stamp}.json"));
        let errors = std::env::temp_dir().join(format!("strehl-capture-tool-{stamp}.err"));
        let mut command = crate::engine::command(engine)?;
        command.args(&args).arg("--json").arg(&json);
        crate::jobs::remove_experimental_overrides(&mut command, std::env::vars_os());
        command.env("STREHL_CACHE_DIR", strehl_cli::default_cache_root());
        command.env_remove("RAYON_NUM_THREADS");
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            // CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS
            command.creation_flags(0x0800_0000 | 0x0000_4000);
        }
        let child = Arc::new(Mutex::new(None::<OwnedChild>));
        let cancelled = Arc::new(AtomicBool::new(false));
        let (tx, rx) = mpsc::channel();
        let (slot, stop) = (child.clone(), cancelled.clone());
        std::thread::Builder::new()
            .name("strehl-engine-job".into())
            .spawn(move || {
                let result = run_engine(command, &json, &errors, &slot, &stop);
                let _ = std::fs::remove_file(&json);
                let _ = std::fs::remove_file(&errors);
                let _ = tx.send(result);
            })
            .context("Start the engine job")?;
        Ok(Self {
            rx,
            child,
            cancelled,
            started: Instant::now(),
        })
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
    /// Ends the engine: it is killed now and reaped by the job's thread,
    /// whose result is then "Cancelled". Never blocks.
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::SeqCst);
        if let Ok(mut child) = self.child.lock()
            && let Some(child) = child.as_mut()
        {
            let _ = child.0.kill();
        }
    }
    #[allow(dead_code)]
    pub fn cancelled(&self) -> bool {
        self.cancelled.load(Ordering::SeqCst)
    }
    pub fn elapsed(&self) -> Duration {
        self.started.elapsed()
    }
}

impl Drop for EngineJob {
    /// A job nobody holds ends its engine: the desktop never leaves one
    /// running unseen.
    fn drop(&mut self) {
        self.cancel();
    }
}

/// The message of a job ended by [`EngineJob::cancel`].
pub(crate) const CANCELLED: &str = "Cancelled";

/// Runs the engine to its exit or a cancel, on the job's thread.
fn run_engine(
    mut command: std::process::Command,
    json: &Path,
    errors: &Path,
    slot: &Mutex<Option<OwnedChild>>,
    cancelled: &AtomicBool,
) -> Result<Value> {
    let stderr = std::fs::File::create(errors).context("Create the engine's error log")?;
    command
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(stderr);
    {
        let mut guard = slot.lock().unwrap();
        anyhow::ensure!(!cancelled.load(Ordering::SeqCst), CANCELLED);
        *guard = Some(OwnedChild(
            command.spawn().context("Start the Strehl engine")?,
        ));
    }
    let status = loop {
        {
            let mut guard = slot.lock().unwrap();
            let child = guard.as_mut().context("The engine was released")?;
            if let Some(status) = child.0.try_wait().context("Check the engine")? {
                guard.take();
                break status;
            }
            if cancelled.load(Ordering::SeqCst) {
                // Dropping the owned child kills it and waits for it.
                guard.take();
                anyhow::bail!(CANCELLED);
            }
        }
        std::thread::sleep(JOB_POLL);
    };
    anyhow::ensure!(!cancelled.load(Ordering::SeqCst), CANCELLED);
    let value = std::fs::read(json)
        .ok()
        .and_then(|b| serde_json::from_slice::<Value>(&b).ok());
    if !status.success() {
        let err = std::fs::read_to_string(errors).unwrap_or_default();
        let line = err
            .lines()
            .rev()
            .find(|l| !l.trim().is_empty())
            .unwrap_or("the engine failed");
        anyhow::bail!("{}", line.trim_start_matches("Error: "));
    }
    value.context("The engine wrote no result")
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
    /// Ends the running job, if any; its result reads "Cancelled".
    pub fn cancel(&mut self) {
        if let Some(job) = self.job.take() {
            // Dropping the job kills the engine; its thread reaps it.
            drop(job);
            self.result = Some(Err(CANCELLED.into()));
        }
    }
    /// How long the running job has run.
    pub fn elapsed(&self) -> Option<Duration> {
        self.job.as_ref().map(EngineJob::elapsed)
    }
    /// The result, if it belongs to `folder`.
    pub fn for_folder(&self, folder: &Path) -> Option<&Result<Value, String>> {
        (self.folder.as_deref() == Some(folder))
            .then_some(self.result.as_ref())
            .flatten()
    }
    /// For snapshots: running, elapsed seconds, folder and result.
    pub fn public(&self) -> Value {
        json!({"running":self.running(),"folder":self.folder,
            "elapsed_seconds":self.elapsed().map(|d| d.as_secs_f64()),
            "result":match &self.result {Some(Ok(v))=>v.clone(),Some(Err(e))=>json!({"error":e}),None=>Value::Null}})
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

/// The calibration's stages, advanced once a frame by the workspace. Every
/// waiting stage holds the instant it gives up (`deadline`).
pub(crate) enum Calibration {
    Idle,
    /// Waiting for the camera to take one RAW a plane.
    Switching {
        restore_four: bool,
        positions: Vec<u16>,
        round: u8,
        deadline: Instant,
    },
    /// The survey is being captured.
    Capturing {
        restore_four: bool,
        sequence: u64,
        round: u8,
        spacing: u16,
        deadline: Instant,
    },
    /// The survey is being measured.
    Measuring {
        restore_four: bool,
        run: PathBuf,
        job: EngineJob,
        round: u8,
        spacing: u16,
        deadline: Instant,
        /// Why the measurement was ended early (a stop or the deadline);
        /// the calibration fails with it once the engine is reaped.
        ended: Option<String>,
    },
    /// Back to four RAWs a plane, then done.
    Restoring {
        result: Value,
        deadline: Instant,
    },
    Done(Value),
    Failed(String),
}

/// Waiting for the camera to switch between one and four RAWs a plane: one
/// property write on the host (seconds).
pub(crate) const SWITCH_TIMEOUT: Duration = Duration::from_secs(45);
/// The survey's capture, beyond any light warmup: 25 single RAWs (about
/// 55 s at 0.6 s), the approach, and the PC receiving every RAW (about
/// 100 s for 25 RAWs at 30 MB/s on Wi-Fi), with room to spare.
pub(crate) const SURVEY_TIMEOUT: Duration = Duration::from_secs(360);
/// `strehl focus-step` on the survey: 25 decodes and the measurement.
pub(crate) const MEASURE_TIMEOUT: Duration = Duration::from_secs(300);

impl Calibration {
    /// Whether a calibration is under way (not idle, done or failed).
    pub fn running(&self) -> bool {
        !matches!(self, Self::Idle | Self::Done(_) | Self::Failed(_))
    }
    /// The stage name snapshots report.
    pub fn stage(&self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::Switching { .. } => "switching",
            Self::Capturing { .. } => "capturing",
            Self::Measuring { .. } => "measuring",
            Self::Restoring { .. } => "restoring",
            Self::Done(_) => "done",
            Self::Failed(_) => "failed",
        }
    }
    /// How long the current stage still waits before it gives up.
    pub fn gives_up_in(&self, now: Instant) -> Option<Duration> {
        match self {
            Self::Switching { deadline, .. }
            | Self::Capturing { deadline, .. }
            | Self::Measuring { deadline, .. }
            | Self::Restoring { deadline, .. } => Some(deadline.saturating_duration_since(now)),
            _ => None,
        }
    }
    /// The survey's sequence on the host while it is being captured.
    pub fn survey_sequence(&self) -> Option<u64> {
        match self {
            Self::Capturing { sequence, .. } => Some(*sequence),
            _ => None,
        }
    }
    /// Stops waiting, at any stage. Switching and capturing fail at once
    /// (the camera is left as it is; a survey still capturing finishes on
    /// the host and is not followed); a measurement ends its engine first
    /// and fails once it is reaped, so the survey's files can be deleted;
    /// restoring keeps the measured result.
    pub fn stop(&mut self, why: &str) {
        let state = std::mem::replace(self, Self::Idle);
        *self = match state {
            Self::Switching { .. } => Self::Failed(why.into()),
            Self::Capturing { .. } => Self::Failed(format!(
                "{why}. The survey may still be running on the camera; it is not checked or listed as a stack"
            )),
            Self::Measuring {
                restore_four,
                run,
                job,
                round,
                spacing,
                deadline,
                ended,
            } => {
                job.cancel();
                Self::Measuring {
                    restore_four,
                    run,
                    job,
                    round,
                    spacing,
                    deadline,
                    ended: ended.or_else(|| Some(why.into())),
                }
            }
            Self::Restoring { mut result, .. } => {
                let summary = result["summary"].as_str().unwrap_or("").to_owned();
                result["summary"] = json!(format!(
                    "{summary} Four-shot was not confirmed: set it again before the next stack."
                ));
                Self::Done(result)
            }
            other => other,
        };
    }
    /// Gives up a stage whose deadline has passed.
    pub fn expire(&mut self, now: Instant) {
        let Some(left) = self.gives_up_in(now) else {
            return;
        };
        if !left.is_zero() || matches!(self, Self::Measuring { ended: Some(_), .. }) {
            return;
        }
        let why = match self {
            Self::Switching { .. } => format!(
                "The camera did not switch to one RAW a plane within {} s",
                SWITCH_TIMEOUT.as_secs()
            ),
            Self::Capturing { .. } => "The survey did not finish in time".to_owned(),
            Self::Measuring { .. } => format!(
                "Measuring the survey took longer than {} s",
                MEASURE_TIMEOUT.as_secs()
            ),
            _ => "Stopped waiting".to_owned(),
        };
        self.stop(&why);
    }
}

/// The time a camera connection may take on the host before the desktop
/// stops waiting: a camera switched on by its outlet has 30 s to appear over
/// USB (`worker.rs`, `wake_camera`), then the session opens.
pub(crate) const CONNECT_TIMEOUT: Duration = Duration::from_secs(60);

/// What became of a [`ConnectWait`].
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum ConnectOutcome {
    Connected,
    /// The host reported why (its failure or message).
    Failed(String),
    /// [`CONNECT_TIMEOUT`] passed.
    TimedOut,
}

/// The desktop waiting for the camera to connect after "Connect camera" or
/// "Power on & connect". Nothing is sent while waiting or on giving up: the
/// host keeps its own limits, and Stop waiting only ends the desktop's wait.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct ConnectWait {
    pub since: Instant,
    pub deadline: Instant,
    /// The host took the request up (busy, or connecting) at least once.
    seen_busy: bool,
}

impl ConnectWait {
    pub fn new(now: Instant) -> Self {
        Self {
            since: now,
            deadline: now + CONNECT_TIMEOUT,
            seen_busy: false,
        }
    }
    pub fn gives_up_in(&self, now: Instant) -> Duration {
        self.deadline.saturating_duration_since(now)
    }
    /// Advances the wait on a fresh state; `Some` ends it.
    pub fn poll(&mut self, s: &Snapshot, now: Instant) -> Option<ConnectOutcome> {
        if let Some(e) = &s.command_error {
            return Some(ConnectOutcome::Failed(e.clone()));
        }
        let host = &s.host;
        if host.connected {
            return Some(ConnectOutcome::Connected);
        }
        if host.busy || host.phase == HostPhase::Connecting {
            self.seen_busy = true;
        } else if self.seen_busy && !s.pending {
            // The host finished trying without connecting.
            let why = host
                .failure
                .as_ref()
                .and_then(|f| f.message.clone())
                .or_else(|| host.message.clone())
                .unwrap_or_else(|| "The camera did not connect".into());
            return Some(ConnectOutcome::Failed(why));
        }
        (now >= self.deadline).then_some(ConnectOutcome::TimedOut)
    }
}

/// The survey's first spacing, in focus units. MEASURED sharp widths on the
/// studio rig (2026-11-20): 69-115 units, so 8 samples them several times.
pub(crate) const SURVEY_SPACING: u16 = 8;
/// Positions in one survey: 25 single RAWs, about 55 s at 0.6 s.
pub(crate) const SURVEY_PLANES: usize = 25;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capture_client::Snapshot;

    /// A stand-in engine that runs until killed (Windows `cmd`): the
    /// arguments the job appends are commented out by `rem`.
    #[cfg(windows)]
    fn sleeper() -> EngineJob {
        EngineJob::start(
            Path::new("cmd"),
            vec!["/c".into(), "ping -n 6 127.0.0.1 >nul & rem".into()],
        )
        .unwrap()
    }

    /// The desktop owns the engine: cancel ends it at once, reports
    /// "Cancelled", and the job knows how long it ran.
    #[cfg(windows)]
    #[test]
    fn a_cancelled_engine_job_ends_its_process() {
        let mut job = sleeper();
        let start = Instant::now();
        while job.child.lock().unwrap().is_none() {
            assert!(start.elapsed() < Duration::from_secs(10), "never spawned");
            std::thread::sleep(Duration::from_millis(10));
        }
        assert!(job.poll().is_none(), "still running");
        job.cancel();
        assert!(job.cancelled());
        let result = loop {
            if let Some(r) = job.poll() {
                break r;
            }
            assert!(start.elapsed() < Duration::from_secs(10), "not ended");
            std::thread::sleep(Duration::from_millis(10));
        };
        assert_eq!(result.unwrap_err().to_string(), CANCELLED);
        assert!(job.child.lock().unwrap().is_none(), "reaped");
        assert!(job.elapsed() < Duration::from_secs(10));
        // A slot's cancel answers at once; dropping a job ends its engine.
        let mut slot = Slot {
            job: Some(sleeper()),
            ..Default::default()
        };
        assert!(slot.running() && slot.elapsed().is_some());
        slot.cancel();
        assert!(!slot.running());
        assert_eq!(slot.result, Some(Err(CANCELLED.into())));
        assert_eq!(slot.public()["result"]["error"], CANCELLED);
    }

    #[cfg(windows)]
    #[test]
    fn a_failed_engine_reports_its_last_error_line() {
        let mut job = EngineJob::start(
            Path::new("cmd"),
            vec![
                "/c".into(),
                "echo Error: no capture here 1>&2 & exit 3 & rem".into(),
            ],
        )
        .unwrap();
        let start = Instant::now();
        let result = loop {
            if let Some(r) = job.poll() {
                break r;
            }
            assert!(start.elapsed() < Duration::from_secs(10));
            std::thread::sleep(Duration::from_millis(10));
        };
        assert_eq!(
            result.unwrap_err().to_string().trim_end(),
            "no capture here"
        );
    }

    /// Every waiting stage gives up at its deadline; stopping keeps a
    /// measured result while restoring and fails the others.
    #[test]
    fn calibration_stages_give_up_and_stop() {
        let now = Instant::now();
        let mut c = Calibration::Switching {
            restore_four: true,
            positions: vec![1000],
            round: 0,
            deadline: now + SWITCH_TIMEOUT,
        };
        assert!(c.running());
        assert_eq!(c.gives_up_in(now), Some(SWITCH_TIMEOUT));
        c.expire(now + Duration::from_secs(1));
        assert_eq!(c.stage(), "switching");
        c.expire(now + SWITCH_TIMEOUT);
        assert!(matches!(&c, Calibration::Failed(e) if e.contains("45 s")));
        let mut c = Calibration::Capturing {
            restore_four: false,
            sequence: 7,
            round: 0,
            spacing: 8,
            deadline: now + SURVEY_TIMEOUT,
        };
        assert_eq!(c.survey_sequence(), Some(7));
        c.stop("Calibration stopped");
        assert!(matches!(&c, Calibration::Failed(e) if e.contains("not checked")));
        let mut c = Calibration::Restoring {
            result: json!({"summary":"Sharp over 80 units.","suggested_step":20}),
            deadline: now,
        };
        c.expire(now);
        match &c {
            Calibration::Done(v) => {
                assert_eq!(v["suggested_step"], 20);
                assert!(v["summary"].as_str().unwrap().contains("not confirmed"));
            }
            _ => panic!("{}", c.stage()),
        }
        assert!(!c.running() && c.gives_up_in(now).is_none());
    }

    /// Measuring is stopped by ending its engine first; the stage fails once
    /// the engine is reaped, with the reason it was stopped.
    #[cfg(windows)]
    #[test]
    fn a_stopped_measurement_ends_its_engine_before_failing() {
        let now = Instant::now();
        let mut c = Calibration::Measuring {
            restore_four: false,
            run: PathBuf::from("survey"),
            job: sleeper(),
            round: 0,
            spacing: 8,
            deadline: now + MEASURE_TIMEOUT,
            ended: None,
        };
        c.expire(now + MEASURE_TIMEOUT);
        match &mut c {
            Calibration::Measuring { ended, job, .. } => {
                assert!(ended.as_deref().unwrap().contains("300 s"));
                assert!(job.cancelled());
            }
            _ => panic!("{}", c.stage()),
        }
        c.expire(now + MEASURE_TIMEOUT * 2);
        assert_eq!(
            c.stage(),
            "measuring",
            "an ended measurement waits for its reaping"
        );
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

    #[test]
    fn the_connect_wait_ends_connected_failed_or_timed_out() {
        let now = Instant::now();
        let mut wait = ConnectWait::new(now);
        let idle = snapshot(json!({"phase":"disconnected","connected":false,"busy":false}));
        assert_eq!(wait.poll(&idle, now), None, "not yet taken up");
        let busy = snapshot(json!({"phase":"connecting","connected":false,"busy":true}));
        assert_eq!(wait.poll(&busy, now), None);
        let up = snapshot(json!({"phase":"ready","connected":true,"busy":false}));
        assert_eq!(wait.poll(&up, now), Some(ConnectOutcome::Connected));
        let mut wait = ConnectWait::new(now);
        wait.poll(&busy, now);
        let failed = snapshot(json!({"phase":"fault","connected":false,"busy":false,
            "failure":{"message":"Camera supply is on but the A7CR did not appear over USB"}}));
        assert!(
            matches!(wait.poll(&failed, now), Some(ConnectOutcome::Failed(e)) if e.contains("USB"))
        );
        let mut wait = ConnectWait::new(now);
        assert_eq!(wait.gives_up_in(now), CONNECT_TIMEOUT);
        assert_eq!(
            wait.poll(&busy, now + CONNECT_TIMEOUT),
            Some(ConnectOutcome::TimedOut)
        );
        let mut refused = snapshot(json!({"phase":"disconnected"}));
        refused.command_error = Some("Camera is already connected".into());
        assert!(matches!(
            ConnectWait::new(now).poll(&refused, now),
            Some(ConnectOutcome::Failed(_))
        ));
    }

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
