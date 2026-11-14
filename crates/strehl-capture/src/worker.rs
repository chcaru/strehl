use crate::{
    backend::{Camera, Demo, Native, Preview, property},
    bounds::{self, Sample, Suggestion},
    journal::{self, Journal},
    model::{Phase, Plan, Roi},
    timing::{self, RunTiming},
};
use anyhow::{Context, Result, bail, ensure};
use serde_json::{Value, json};
use std::{
    path::PathBuf,
    sync::{
        Arc, Mutex,
        atomic::{AtomicU8, Ordering},
        mpsc,
    },
    thread,
    time::{Duration, Instant},
};

pub const RUN: u8 = 0;
pub const PAUSE: u8 = 1;
pub const STOP: u8 = 2;
#[derive(Clone)]
pub struct Snapshot {
    pub revision: u64,
    pub phase: Phase,
    pub position: Option<u16>,
    pub status: Value,
    pub identity: Value,
    pub message: String,
    pub preview: Option<Arc<Preview>>,
    pub preview_generation: u64,
    pub preview_at: Option<Instant>,
    pub preview_error: Option<String>,
    pub completed: usize,
    pub capture_run: bool,
    pub total: usize,
    pub journal: Option<PathBuf>,
    pub samples: Vec<Sample>,
    pub suggestion: Option<Suggestion>,
    pub connected: bool,
    pub timing: Option<RunTiming>,
    pub command_pending: bool,
    pub sequence_id: u64,
    pub connection_generation: u64,
    pub failure: Option<String>,
    pub exposure_uncertain: bool,
}
impl Default for Snapshot {
    fn default() -> Self {
        Self {
            revision: 0,
            phase: Phase::Disconnected,
            position: None,
            status: Value::Null,
            identity: Value::Null,
            message: "Connect your A7C II in USB Remote Shoot mode.".into(),
            preview: None,
            preview_generation: 0,
            preview_at: None,
            preview_error: None,
            completed: 0,
            capture_run: false,
            total: 0,
            journal: None,
            samples: vec![],
            suggestion: None,
            connected: false,
            timing: None,
            command_pending: false,
            sequence_id: 0,
            connection_generation: 0,
            failure: None,
            exposure_uncertain: false,
        }
    }
}
pub enum Action {
    Connect,
    PixelShift {
        shots: usize,
    },
    Disconnect,
    Recover {
        acknowledge_uncertain: bool,
    },
    Move {
        target: u16,
        settle_ms: u32,
    },
    Inspect {
        target: u16,
        approach_from: u16,
        settle_ms: u32,
    },
    Magnify {
        ratio: u32,
        x: u16,
        y: u16,
    },
    Capture {
        plan: Plan,
        root: PathBuf,
    },
    Scan {
        plan: Plan,
        roi: Roi,
    },
    Export {
        folder: PathBuf,
    },
}
struct Envelope {
    revision: u64,
    action: Action,
}
type Shared = Arc<Mutex<Snapshot>>;
pub struct Worker {
    state: Shared,
    tx: mpsc::SyncSender<Envelope>,
    pub control: Arc<AtomicU8>,
    join: Option<thread::JoinHandle<()>>,
}
type Factory = Box<dyn Fn() -> Result<Box<dyn Camera>> + Send>;
impl Worker {
    pub fn new(bridge: PathBuf, demo: bool) -> Self {
        Self::with_factory(Box::new(move || {
            if demo {
                Ok(Box::new(Demo::default()))
            } else {
                Ok(Box::new(Native::connect(&bridge)?))
            }
        }))
    }
    pub fn with_factory(factory: Factory) -> Self {
        let (tx, rx) = mpsc::sync_channel::<Envelope>(16);
        let state = Arc::new(Mutex::new(Snapshot::default()));
        let control = Arc::new(AtomicU8::new(RUN));
        let s = state.clone();
        let c = control.clone();
        let join = thread::spawn(move || run(factory, rx, s, c));
        Self {
            state,
            tx,
            control,
            join: Some(join),
        }
    }
    pub fn snapshot(&self) -> Snapshot {
        self.state.lock().unwrap().clone()
    }
    pub fn send(&self, revision: u64, action: Action) -> Result<()> {
        let mut state = self.state.lock().unwrap();
        ensure!(
            state.revision == revision,
            "Camera state changed; refresh before trying again"
        );
        ensure!(
            !state.command_pending,
            "A camera command is already pending"
        );
        if let Action::Recover {
            acknowledge_uncertain,
        } = &action
        {
            ensure!(
                matches!(state.phase, Phase::Fault | Phase::Disconnected)
                    && state.failure.is_some(),
                "Recovery is available after a camera failure"
            );
            ensure!(
                !state.exposure_uncertain || *acknowledge_uncertain,
                "Check the camera is idle and inspect the SD card before acknowledging the uncertain exposure"
            );
        }
        if matches!(&action, Action::Connect) {
            ensure!(
                !state.exposure_uncertain,
                "Use Reconnect camera and acknowledge the uncertain exposure first"
            );
        }
        if matches!(&action, Action::Capture { .. } | Action::Scan { .. }) {
            ensure!(
                state.connected && state.phase.can_edit(),
                "Connect a ready camera first"
            );
            self.control.store(RUN, Ordering::SeqCst);
        }
        let next = state.revision + 1;
        self.tx
            .try_send(Envelope {
                revision: next,
                action,
            })
            .context("Camera command queue unavailable; read the current state before retrying")?;
        state.revision = next;
        state.command_pending = true;
        Ok(())
    }
    pub fn request_pause(&self) {
        let _ = self
            .control
            .compare_exchange(RUN, PAUSE, Ordering::SeqCst, Ordering::SeqCst);
    }
    pub fn request_resume(&self) {
        let _ = self
            .control
            .compare_exchange(PAUSE, RUN, Ordering::SeqCst, Ordering::SeqCst);
    }
    pub fn request_stop(&self) {
        self.control.store(STOP, Ordering::SeqCst);
    }
    pub fn pending(&self) -> u8 {
        self.control.load(Ordering::SeqCst)
    }
}
impl Drop for Worker {
    fn drop(&mut self) {
        self.request_stop();
        let (tx, _) = mpsc::sync_channel(1);
        let old = std::mem::replace(&mut self.tx, tx);
        drop(old);
        // Retire cooperatively in the owned worker. The GUI closes only after idle.
        if let Some(join) = self.join.take() {
            thread::spawn(move || {
                let _ = join.join();
            });
        }
    }
}
fn update(s: &Shared, f: impl FnOnce(&mut Snapshot)) {
    let mut state = s.lock().unwrap();
    f(&mut state);
    state.revision += 1;
}
fn phase(s: &Shared, p: Phase, message: impl Into<String>) {
    let message = message.into();
    update(s, |v| {
        if let Some(timing) = &mut v.timing {
            match p {
                Phase::Paused => timing.pause(Instant::now()),
                Phase::Capturing => timing.resume(Instant::now()),
                Phase::Complete | Phase::Stopped | Phase::Fault => timing.finish(Instant::now()),
                _ => {}
            }
        }
        if p == Phase::Fault {
            v.failure = Some(message.clone());
        }
        v.phase = p;
        v.message = message;
    });
}
fn preview(camera: &mut dyn Camera, s: &Shared) -> Result<u64> {
    let frame = camera.preview()?;
    let number = frame.frame;
    let mut state = s.lock().unwrap();
    if state
        .preview
        .as_ref()
        .is_some_and(|old| old.frame == number)
    {
        return Ok(number); // Re-reading the SDK cache cannot refresh its age.
    }
    state.preview = Some(Arc::new(frame));
    state.preview_at = Some(Instant::now());
    state.preview_generation += 1;
    state.preview_error = None;
    Ok(number)
}
fn refresh(camera: &mut dyn Camera, s: &Shared) -> Result<Value> {
    let status = camera.status()?;
    let position =
        property(&status, "FocusPositionCurrentValue").and_then(|v| u16::try_from(v).ok());
    let mut st = s.lock().unwrap();
    st.position = position;
    st.status = status.clone();
    drop(st);
    position.context("Camera did not return focus information; check the lens connection and MF mode, then reconnect")?;
    Ok(status)
}
fn run(factory: Factory, rx: mpsc::Receiver<Envelope>, s: Shared, control: Arc<AtomicU8>) {
    let mut camera: Option<Box<dyn Camera>> = None;
    let mut last_status = Instant::now();
    loop {
        match rx.recv_timeout(Duration::from_millis(120)) {
            Ok(envelope) => {
                if envelope.revision != s.lock().unwrap().revision {
                    update(&s, |v| {
                        v.command_pending = false;
                        v.message =
                            "That command used an older state. Check the preview and try again."
                                .into()
                    });
                    continue;
                }
                let result = (|| -> Result<()> {
                    match envelope.action {
                        Action::Connect => {
                            ensure!(camera.is_none(), "Camera is already connected");
                            phase(
                                &s,
                                Phase::Connecting,
                                "Connecting · preparing manual focus and RAW capture…",
                            );
                            camera = Some(factory()?);
                            let opened = camera.as_mut().unwrap();
                            opened.configure()?;
                            refresh(opened.as_mut(), &s)?;
                            let identity = opened.identity();
                            update(&s, |v| {
                                v.connected = true;
                                v.capture_run = false;
                                v.connection_generation += 1;
                                v.failure = None;
                                v.exposure_uncertain = false;
                                v.identity = identity;
                                v.phase = Phase::Ready;
                                v.message = if v.status["capture_destination"] == "host-pc" {
                                    if v.status["pixel_shift_shots"] == 4 {
                                        "Connected · A7CR four-shot pixel shift saves to the PC"
                                    } else {
                                        "Connected · Lossless RAW L saves to the PC"
                                    }
                                } else {
                                    "Connected · RAW captures stay on the SD card"
                                }
                                .into();
                                v.suggestion = None;
                                v.timing = None;
                            });
                        }
                        Action::Disconnect => {
                            phase(
                                &s,
                                Phase::Disconnecting,
                                "Disconnecting · restoring camera settings…",
                            );
                            if let Some(opened) = camera.as_mut() {
                                let result = opened.disconnect()?;
                                // Release is complete even if settings could not
                                // safely be restored. A pending release retains
                                // the owner so another bridge cannot race it.
                                camera = None;
                                ensure!(
                                    result["restored"] == true,
                                    "Camera settings were not fully restored: {result}"
                                );
                            }
                            update(&s, |v| {
                                v.connected = false;
                                v.capture_run = false;
                                v.phase = Phase::Disconnected;
                                v.preview = None;
                                v.preview_at = None;
                                v.position = None;
                                v.status = Value::Null;
                                v.total = 0;
                                v.completed = 0;
                                v.timing = None;
                                v.samples.clear();
                                v.suggestion = None;
                                v.message = "Disconnected".into();
                                if !v.exposure_uncertain {
                                    v.failure = None;
                                }
                            });
                        }
                        Action::Recover {
                            acknowledge_uncertain,
                        } => {
                            let before = s.lock().unwrap().clone();
                            ensure!(
                                !before.exposure_uncertain || acknowledge_uncertain,
                                "Inspect the uncertain exposure before reconnecting"
                            );
                            phase(
                                &s,
                                Phase::Recovering,
                                "Reconnecting camera · releasing the previous connection…",
                            );
                            if let Some(opened) = camera.as_mut() {
                                opened.disconnect()?;
                                camera = None;
                            }
                            camera = Some(factory()?);
                            let opened = camera.as_mut().unwrap();
                            opened.configure()?;
                            refresh(opened.as_mut(), &s)?;
                            let identity = opened.identity();
                            update(&s, |v| {
                                if identity != before.identity {
                                    v.connection_generation += 1;
                                }
                                v.identity = identity;
                                v.connected = true;
                                v.capture_run = false;
                                v.phase = Phase::Ready;
                                v.failure = None;
                                v.exposure_uncertain = false;
                                v.preview = None;
                                v.preview_at = None;
                                v.preview_error = None;
                                v.message = format!(
                                    "Camera reconnected · previous run: {} / {} confirmed. Review A/B marks; Start begins a new stack. RAWs and journal kept.",
                                    v.completed, v.total
                                );
                            });
                            control.store(RUN, Ordering::SeqCst);
                        }
                        Action::PixelShift { shots } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "Finish the sequence before changing capture mode"
                            );
                            let c = camera.as_mut().context("Connect a camera first")?;
                            c.set_pixel_shift(shots)?;
                            refresh(c.as_mut(), &s)?;
                            update(&s, |v| {
                                v.timing = None;
                                v.message = format!(
                                    "{shots} RAW{} per focal plane",
                                    if shots == 1 { "" } else { "s" }
                                );
                            });
                        }
                        Action::Move { target, settle_ms } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "Focus movement is locked while a sequence is active"
                            );
                            phase(&s, Phase::Moving, format!("Moving to {target}…"));
                            let c = camera.as_mut().context("Connect a camera first")?;
                            s.lock().unwrap().preview_at = None;
                            c.focus(target, settle_ms)?;
                            refresh(c.as_mut(), &s)?;
                            if let Err(error) = preview(c.as_mut(), &s) {
                                s.lock().unwrap().preview_error = Some(error.to_string());
                            }
                            phase(&s, Phase::Ready, "Focus settled");
                        }
                        Action::Inspect {
                            target,
                            approach_from,
                            settle_ms,
                        } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "A sequence is already active"
                            );
                            phase(
                                &s,
                                Phase::Moving,
                                "Approaching the focus mark in the capture direction…",
                            );
                            let c = camera.as_mut().context("Connect a camera first")?;
                            s.lock().unwrap().preview_at = None;
                            c.focus(approach_from, settle_ms)?;
                            c.focus(target, settle_ms)?;
                            refresh(c.as_mut(), &s)?;
                            if let Err(error) = preview(c.as_mut(), &s) {
                                s.lock().unwrap().preview_error = Some(error.to_string());
                            }
                            phase(
                                &s,
                                Phase::Ready,
                                "Focus mark approached in the capture direction",
                            );
                        }
                        Action::Magnify { ratio, x, y } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "Camera magnifier is locked during capture"
                            );
                            let c = camera.as_mut().context("Connect a camera first")?;
                            phase(&s, Phase::Moving, "Changing the camera focus magnifier…");
                            c.magnify(ratio, x, y)?;
                            refresh(c.as_mut(), &s)?;
                            phase(&s, Phase::Ready, "Camera focus magnifier updated");
                        }
                        Action::Capture { plan, root } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "A sequence is already active"
                            );
                            capture(
                                camera.as_mut().context("Connect a camera first")?.as_mut(),
                                &s,
                                &control,
                                plan,
                                root,
                            )?;
                        }
                        Action::Scan { plan, roi } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "A sequence is already active"
                            );
                            scan(
                                camera.as_mut().context("Connect a camera first")?.as_mut(),
                                &s,
                                &control,
                                plan,
                                roi,
                            )?;
                        }
                        Action::Export { folder } => {
                            ensure!(
                                !s.lock().unwrap().phase.active(),
                                "Finish the run before exporting metadata"
                            );
                            let source = s
                                .lock()
                                .unwrap()
                                .journal
                                .clone()
                                .context("No run metadata yet")?;
                            let target = journal::export(&source, &folder)?;
                            update(&s, |v| {
                                v.message = format!("Metadata copied to {}", target.display())
                            });
                        }
                    }
                    Ok(())
                })();
                if let Err(error) = result {
                    update(&s, |v| {
                        if camera.is_none() {
                            v.phase = Phase::Disconnected;
                            v.preview = None;
                            v.preview_at = None;
                            v.position = None;
                            v.failure = Some(format!("{error:#}"));
                        } else if v.phase.active() {
                            v.phase = Phase::Fault;
                            v.failure = Some(format!("{error:#}"));
                            if let Some(timing) = &mut v.timing {
                                timing.finish(Instant::now());
                            }
                        }
                        v.connected = camera.is_some();
                        v.message = format!("{error:#}");
                    });
                }
                update(&s, |v| v.command_pending = false);
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
            Err(mpsc::RecvTimeoutError::Timeout) => {
                if let Some(c) = camera.as_mut() {
                    if s.lock().unwrap().phase == Phase::Fault {
                        continue;
                    }
                    if let Err(e) = preview(c.as_mut(), &s) {
                        s.lock().unwrap().preview_error =
                            Some(format!("Live preview unavailable: {e:#}"));
                    }
                    if last_status.elapsed() > Duration::from_secs(2) {
                        if let Err(e) = refresh(c.as_mut(), &s) {
                            phase(&s, Phase::Fault, format!("Camera status failed: {e}"));
                        }
                        last_status = Instant::now();
                    }
                }
            }
        }
    }
    if let Some(mut c) = camera {
        let _ = c.disconnect();
    }
}

fn checkpoint(c: &mut dyn Camera, s: &Shared, control: &AtomicU8, resume: Phase) -> Result<bool> {
    let mut paused = false;
    while control.load(Ordering::SeqCst) == PAUSE {
        if !paused {
            c.finish_transfers()?;
            phase(
                s,
                Phase::Paused,
                "Paused · current operation completed; no further exposures",
            );
            paused = true;
        }
        if let Err(e) = preview(c, s) {
            s.lock().unwrap().preview_error = Some(e.to_string());
        }
        thread::sleep(Duration::from_millis(100));
    }
    if control.load(Ordering::SeqCst) == STOP {
        return Ok(false);
    }
    if paused {
        phase(s, resume, "Resuming from the next operation…");
    }
    Ok(true)
}

fn capture(
    c: &mut dyn Camera,
    s: &Shared,
    control: &AtomicU8,
    plan: Plan,
    root: PathBuf,
) -> Result<()> {
    let positions = plan.positions()?;
    let status = refresh(c, s)?;
    validate_exposure(&status)?;
    let host = status["capture_destination"] == "host-pc";
    let shots = status["pixel_shift_shots"].as_u64().unwrap_or(1);
    ensure!(
        matches!(shots, 1 | 4),
        "Unsupported number of RAWs per plane"
    );
    let frames = positions.len() * shots as usize;
    ensure!(
        host || property(&status, "MediaSLOT1_RemainingNumber").is_some_and(|n| n >= frames as u64),
        "The card does not report enough remaining captures for this plan"
    );
    c.prepare_stack(frames, crate::capacity::raw_limit(&status))?;
    let initial_exposure = status.clone();
    let cycle = property(&status, "ShutterSpeed")
        .and_then(|shutter| timing::initial_plane(shutter, plan.settle_ms, shots))
        .context("Cannot estimate timed shutter speed")?;
    let mut log = Journal::create(&root, &plan, c.identity(), status)?;
    c.sync_journal(&log.directory)?;
    // Validate the registered destination too: another client could have changed
    // the default folder between the initial admission and run registration.
    while !c.prepare_capture()? {
        thread::sleep(Duration::from_millis(100));
    }
    update(s, |v| {
        v.phase = Phase::Capturing;
        v.failure = None;
        v.exposure_uncertain = false;
        v.sequence_id += 1;
        v.completed = 0;
        v.capture_run = true;
        v.total = positions.len();
        v.journal = Some(log.directory.clone());
        v.message = "Approaching the start from the capture direction…".into();
        v.timing = Some(RunTiming::new(
            positions.len(),
            cycle,
            timing::initial_setup(plan.settle_ms),
            Instant::now(),
        ));
    });
    let mut completed = 0;
    let result = (|| -> Result<bool> {
        if !checkpoint(c, s, control, Phase::Capturing)? {
            return Ok(false);
        }
        let prestart = plan.prestart()?;
        log.record("approach_intent", json!({"target":prestart}))?;
        let response = c.focus(prestart, plan.settle_ms)?;
        log.record("approach_complete", response)?;
        if let Some(timing) = &mut s.lock().unwrap().timing {
            timing.approached(Instant::now());
        }
        for (ordinal, target) in positions.into_iter().enumerate() {
            if !checkpoint(c, s, control, Phase::Capturing)? {
                return Ok(false);
            }
            log.record("focus_intent", json!({"ordinal":ordinal,"target":target}))?;
            let response = c.focus(target, plan.settle_ms)?;
            log.record(
                "focus_complete",
                json!({"ordinal":ordinal,"response":response}),
            )?;
            update(s, |v| {
                v.position = Some(target);
                v.message = format!("Plane {} of {} · focus {target}", ordinal + 1, v.total);
            });
            if !checkpoint(c, s, control, Phase::Capturing)? {
                return Ok(false);
            }
            let before = refresh(c, s)?;
            validate_exposure(&before)?;
            ensure!(
                before["pixel_shift_shots"].as_u64().unwrap_or(1) == shots,
                "Capture mode changed during the stack; no next shutter was sent"
            );
            for key in [
                "ExposureProgramMode",
                "IsoSensitivity",
                "ShutterSpeed",
                "FNumber",
            ] {
                ensure!(
                    property(&before, key) == property(&initial_exposure, key),
                    "{key} changed during the run; sequence stopped before the next shutter"
                );
            }
            log.record(
                "capture_intent",
                json!({"ordinal":ordinal,"target":target,"pixel_shift_shots":shots,"camera_status":before}),
            )?;
            c.sync_journal(&log.directory)?;
            while !c.prepare_capture()? {
                if !checkpoint(c, s, control, Phase::Capturing)? {
                    return Ok(false);
                }
                thread::sleep(Duration::from_millis(100));
            }
            if !checkpoint(c, s, control, Phase::Capturing)? {
                return Ok(false);
            }
            s.lock().unwrap().exposure_uncertain = true;
            let response = c.capture(plan.capture_timeout_s)?;
            ensure!(
                response["pixel_shift_shots"].as_u64().unwrap_or(1) == shots,
                "Capture mode changed during the stack"
            );
            validate_capture(&response)?;
            completed += 1;
            update(s, |v| {
                v.exposure_uncertain = false;
                v.completed = completed;
                if let Some(timing) = &mut v.timing {
                    timing.complete_cycle(Instant::now());
                }
            });
            log.record(
                if response["destination"] == "host-pc-queue" {
                    "capture_buffered"
                } else {
                    "capture_complete"
                },
                json!({"ordinal":ordinal,"target":target,"response":response}),
            )?;
            c.sync_journal(&log.directory)?;
            // Preview failure does not repeat or invalidate a completed exposure.
            if let Err(e) = preview(c, s) {
                s.lock().unwrap().preview_error = Some(e.to_string());
            }
        }
        Ok(true)
    })();
    let result = result.and_then(|done| {
        if host {
            update(s, |v| {
                v.message = "Saving remaining RAWs and metadata on the PC…".into()
            });
        }
        c.finish_transfers()?;
        Ok(done)
    });
    match result {
        Ok(done) => {
            let outcome = if done { "complete" } else { "stopped" };
            log.finish(
                outcome,
                completed,
                if host {
                    "RAWs saved on PC with matching SHA-256 and durable write acknowledgements"
                } else {
                    "Camera events acknowledged; RAW files not downloaded or verified"
                },
            )?;
            c.sync_journal(&log.directory)?;
            c.finish_transfers()?;
            phase(
                s,
                if done {
                    Phase::Complete
                } else {
                    Phase::Stopped
                },
                format!(
                    "{} · {completed} planes / {} RAWs on {}; metadata saved",
                    if done { "Complete" } else { "Stopped" },
                    completed as u64 * shots,
                    if host { "PC" } else { "SD" }
                ),
            );
            Ok(())
        }
        Err(e) => {
            let reason = format!("{e:#}");
            let finish = log.finish("uncertain", completed, &reason);
            if finish.is_ok() {
                let _ = c.sync_journal(&log.directory);
            }
            if let Err(log_error) = finish {
                bail!(
                    "{reason}; also could not finalize the journal: {log_error}. Inspect the SD card before restarting."
                );
            }
            Err(e)
        }
    }
}

fn validate_exposure(status: &Value) -> Result<()> {
    ensure!(
        property(status, "ExposureProgramMode") == Some(1),
        "Set the camera to M (manual exposure) before starting a stack"
    );
    ensure!(
        property(status, "IsoSensitivity").is_some_and(|v| v & 0x00ff_ffff != 0x00ff_ffff),
        "Choose fixed ISO before starting a stack"
    );
    ensure!(
        property(status, "ShutterSpeed").is_some_and(|v| v != 0),
        "Choose a timed shutter exposure; Bulb is not supported"
    );
    Ok(())
}
fn validate_capture(reply: &Value) -> Result<()> {
    if reply["destination"] == "host-pc-queue" {
        let shots = reply["pixel_shift_shots"].as_u64().unwrap_or(1);
        ensure!(matches!(shots, 1 | 4), "Unsupported group size");
        let group = reply["camera_reply"]["completion"] == "ptp-group-complete";
        if shots == 4 || group {
            ensure!(
                reply["group_complete"] == true
                    && reply["camera_reply"]["completion"] == "ptp-group-complete"
                    && reply["camera_reply"]["group_idle"] == true
                    && reply["camera_reply"]["buffer_empty"] == true,
                "Incomplete pixel-shift group"
            );
        }
        ensure!(
            reply["completion"] == "ram-queued-sha256"
                && reply["file_verification"] == "ram-sha256"
                && reply["raw_compression"] == if group { "uncompressed" } else { "lossless-l" },
            "RAM capture acknowledgement is incomplete"
        );
        let files = reply["files"]
            .as_array()
            .context("Missing queued RAW binding")?;
        ensure!(files.len() == shots as usize, "Incomplete RAW group");
        let mut names = std::collections::HashSet::new();
        for (index, file) in files.iter().enumerate() {
            ensure!(
                names.insert(file["name"].as_str()),
                "Duplicate RAW group member"
            );
            if shots == 4 {
                ensure!(
                    file["member_index"] == index + 1
                        && file["members"] == 4
                        && file["group_id"].as_str().is_some_and(|v| !v.is_empty())
                        && file["group_id"] == files[0]["group_id"],
                    "Mixed or unordered pixel-shift group"
                );
            }
            ensure!(
                file["durable"] == false
                    && file["bytes"]
                        .as_u64()
                        .is_some_and(|n| (1024..=crate::receiver::MAX_RAW).contains(&n))
                    && file["sha256"]
                        .as_str()
                        .is_some_and(|s| s.len() == 64 && s.bytes().all(|c| c.is_ascii_hexdigit()))
                    && file["name"]
                        .as_str()
                        .is_some_and(crate::receiver::safe_name),
                "Queued RAW binding is invalid"
            );
        }
        return Ok(());
    }
    if reply["destination"] == "host-pc" {
        ensure!(
            reply["completion"] == "pc-durable-sha256"
                && reply["file_verification"] == "sha256"
                && reply["raw_compression"] == "lossless-l",
            "PC capture acknowledgement is incomplete"
        );
        let files = reply["files"]
            .as_array()
            .context("Missing PC file receipt")?;
        ensure!(files.len() == 1, "Expected exactly one RAW per focus plane");
        let file = &files[0];
        ensure!(
            file["durable"] == true
                && file["bytes"].as_u64().is_some_and(|n| n >= 1024)
                && file["sha256"]
                    .as_str()
                    .is_some_and(|s| s.len() == 64 && s.bytes().all(|c| c.is_ascii_hexdigit()))
                && file["path"].as_str().is_some_and(|s| !s.is_empty()),
            "PC file receipt failed durability/checksum checks"
        );
        return Ok(());
    }
    for (key, expected) in [
        ("captured_events", json!(1)),
        ("destination", json!("memory-card")),
        ("card_state", json!("not-writing")),
        ("bracket_idle", json!(true)),
        ("completion", json!("camera-events-and-card-idle")),
        ("file_verification", json!("not-performed")),
        ("files", json!([])),
    ] {
        ensure!(
            reply[key] == expected,
            "Capture acknowledgement mismatch for {key}; no retry or further focus move"
        );
    }
    Ok(())
}

fn scan(
    c: &mut dyn Camera,
    s: &Shared,
    control: &AtomicU8,
    mut plan: Plan,
    roi: Roi,
) -> Result<()> {
    ensure!(roi.valid(), "Select a subject region first");
    ensure!(
        plan.start.abs_diff(plan.end) >= 8,
        "Choose rough start and end marks at least eight units apart"
    );
    let distance = plan.start.abs_diff(plan.end);
    plan.step = (u32::from(distance).div_ceil(32) as u16).max(1);
    let positions = plan.positions()?;
    // Auto survey requires full-frame live view; camera magnification changes the ROI.
    let status = refresh(c, s)?;
    if property(&status, "Focus_Magnifier_Setting").is_some_and(|v| v >> 32 > 10) {
        bail!("Turn camera magnification off before a focus survey");
    }
    validate_exposure(&status)?;
    update(s, |v| {
        v.phase = Phase::Scanning;
        v.capture_run = false;
        v.sequence_id += 1;
        v.samples.clear();
        v.suggestion = None;
        v.completed = 0;
        v.total = positions.len();
        v.message = "Preview survey · no RAW exposures".into();
        v.timing = None;
    });
    if !checkpoint(c, s, control, Phase::Scanning)? {
        phase(s, Phase::Stopped, "Survey stopped · no captures taken");
        return Ok(());
    }
    c.focus(plan.prestart()?, plan.settle_ms)?;
    let mut samples = Vec::new();
    for (i, position) in positions.iter().copied().enumerate() {
        if !checkpoint(c, s, control, Phase::Scanning)? {
            phase(s, Phase::Stopped, "Survey stopped · no captures taken");
            return Ok(());
        }
        let before = c.preview()?.frame;
        c.focus(position, plan.settle_ms)?;
        let mut curves = Vec::new();
        let mut deadline = Instant::now() + Duration::from_secs(5);
        let mut last = before;
        // Discard the first changed frame, then median three distinct previews.
        let mut discard = true;
        while curves.len() < 3 {
            let was_paused = control.load(Ordering::SeqCst) == PAUSE;
            if !checkpoint(c, s, control, Phase::Scanning)? {
                phase(s, Phase::Stopped, "Survey stopped · no captures taken");
                return Ok(());
            }
            if was_paused {
                deadline = Instant::now() + Duration::from_secs(5);
            }
            ensure!(
                Instant::now() < deadline,
                "Live view did not supply distinct fresh frames; use manual focus marks"
            );
            let frame = c.preview()?;
            if frame.frame != last && frame.frame != before {
                last = frame.frame;
                if discard {
                    discard = false;
                } else {
                    curves.push(bounds::scores(&frame.rgb, roi)?);
                }
                let mut v = s.lock().unwrap();
                v.preview = Some(Arc::new(frame));
                v.preview_at = Some(Instant::now());
                v.preview_generation += 1;
            }
            thread::sleep(Duration::from_millis(100));
        }
        let scores = (0..bounds::TILES)
            .map(|tile| {
                let mut values = [curves[0][tile], curves[1][tile], curves[2][tile]];
                values.sort_by(f32::total_cmp);
                values[1]
            })
            .collect();
        samples.push(Sample { position, scores });
        update(s, |v| {
            v.position = Some(position);
            v.completed = i + 1;
            v.samples = samples.clone();
            v.message = format!("Survey {} / {} · no RAW exposures", i + 1, positions.len());
        });
    }
    match bounds::suggest(&samples) {
        Ok(suggestion) => {
            let explanation = suggestion.explanation.clone();
            update(s, |v| {
                v.phase = Phase::Ready;
                v.suggestion = Some(suggestion);
                v.message = explanation;
            });
        }
        Err(e) => phase(s, Phase::Ready, e.to_string()),
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn four_shot_receipts_require_a_complete_ordered_single_group() {
        let files:Vec<_>=(1..=4).map(|n|json!({"name":format!("frame-{n:06}.ARW"),"bytes":122_968_064,
            "sha256":"a".repeat(64),"durable":false,"group_id":"ptp-test-1","member_index":n,"members":4})).collect();
        let good = json!({"destination":"host-pc-queue","completion":"ram-queued-sha256","file_verification":"ram-sha256",
            "raw_compression":"uncompressed","pixel_shift_shots":4,"group_complete":true,"files":files,
            "camera_reply":{"completion":"ptp-group-complete","group_idle":true,"buffer_empty":true}});
        validate_capture(&good).unwrap();
        for n in 0..4 {
            let mut bad = good.clone();
            bad["files"] = json!(files[..n]);
            assert!(validate_capture(&bad).is_err());
        }
        let mut bad = good.clone();
        bad["files"][3]["name"] = bad["files"][0]["name"].clone();
        assert!(validate_capture(&bad).is_err());
        let mut bad = good.clone();
        bad["files"][3]["group_id"] = json!("other-group");
        assert!(validate_capture(&bad).is_err());
        let mut bad = good.clone();
        bad["files"][0]["member_index"] = json!(2);
        assert!(validate_capture(&bad).is_err());
        for field in ["group_idle", "buffer_empty"] {
            let mut bad = good.clone();
            bad["camera_reply"][field] = json!(false);
            assert!(validate_capture(&bad).is_err());
        }
        let mut bad = good.clone();
        bad["pixel_shift_shots"] = json!(16);
        assert!(validate_capture(&bad).is_err());
        let mut bad = good;
        bad["raw_compression"] = json!("lossless-l");
        assert!(validate_capture(&bad).is_err());
    }
    use super::*;
    #[test]
    fn whole_stack_admission_refuses_before_focus_shutter_or_journal() {
        struct FullDisk(Demo);
        impl Camera for FullDisk {
            fn identity(&self) -> Value {
                self.0.identity()
            }
            fn status(&mut self) -> Result<Value> {
                let mut s = self.0.status()?;
                s["capture_destination"] = json!("host-pc");
                s["raw_max_bytes"] = json!(crate::ptp::MEMBER_LIMIT);
                Ok(s)
            }
            fn configure(&mut self) -> Result<()> {
                Ok(())
            }
            fn prepare_stack(&mut self, frames: usize, raw: u64) -> Result<()> {
                crate::capacity::check(Some(1024), frames, raw).map(|_| ())
            }
            fn focus(&mut self, _: u16, _: u32) -> Result<Value> {
                panic!("Must not move focus on a full PC disk")
            }
            fn capture(&mut self, _: u32) -> Result<Value> {
                panic!("Must not release shutter on a full PC disk")
            }
            fn preview(&mut self) -> Result<Preview> {
                self.0.preview()
            }
            fn magnify(&mut self, _: u32, _: u16, _: u16) -> Result<()> {
                Ok(())
            }
            fn disconnect(&mut self) -> Result<Value> {
                self.0.disconnect()
            }
        }
        let temp = tempfile::tempdir().unwrap();
        let shared = Arc::new(Mutex::new(Snapshot::default()));
        let mut camera = FullDisk(Demo {
            shots: 4,
            ..Demo::default()
        });
        let plan = Plan {
            start: 60000,
            end: 60899,
            ..Plan::default()
        };
        let error = capture(
            &mut camera,
            &shared,
            &AtomicU8::new(RUN),
            plan,
            temp.path().into(),
        )
        .unwrap_err();
        assert!(error.to_string().contains("Shorten the stack"));
        assert_eq!(std::fs::read_dir(temp.path()).unwrap().count(), 0);
        assert!(!shared.lock().unwrap().exposure_uncertain);
    }
    #[test]
    fn capture_receipt_and_exposure_fail_closed() {
        let mut demo = Demo {
            delay_ms: 0,
            ..Demo::default()
        };
        let good = demo.capture(120).unwrap();
        validate_capture(&good).unwrap();
        for (key, value) in [
            ("captured_events", json!(2)),
            ("destination", json!("host")),
            ("card_state", json!("writing")),
            ("bracket_idle", json!(false)),
            ("files", json!(["downloaded.arw"])),
        ] {
            let mut bad = good.clone();
            bad[key] = value;
            assert!(validate_capture(&bad).is_err(), "{key}");
        }
        let status = demo.status().unwrap();
        validate_exposure(&status).unwrap();
        for (key, value) in [
            ("ExposureProgramMode", 2),
            ("IsoSensitivity", 0x00ff_ffff),
            ("ShutterSpeed", 0),
        ] {
            let mut bad = status.clone();
            bad["properties"][key]["value"] = json!(value);
            assert!(validate_exposure(&bad).is_err(), "{key}");
        }
    }
    fn until(w: &Worker, predicate: impl Fn(&Snapshot) -> bool) -> Snapshot {
        let end = Instant::now() + Duration::from_secs(8);
        loop {
            let s = w.snapshot();
            if predicate(&s) {
                return s;
            }
            assert!(Instant::now() < end, "Timeout: {:?} {}", s.phase, s.message);
            thread::sleep(Duration::from_millis(5));
        }
    }
    struct DelayedRelease {
        demo: Demo,
        refuse_release: bool,
        missing_focus: bool,
    }
    impl Camera for DelayedRelease {
        fn identity(&self) -> Value {
            self.demo.identity()
        }
        fn status(&mut self) -> Result<Value> {
            let mut value = self.demo.status()?;
            if self.missing_focus {
                value["properties"]["FocusPositionCurrentValue"]["value"] = Value::Null;
            }
            Ok(value)
        }
        fn configure(&mut self) -> Result<()> {
            self.demo.configure()
        }
        fn focus(&mut self, target: u16, settle_ms: u32) -> Result<Value> {
            self.demo.focus(target, settle_ms)
        }
        fn capture(&mut self, timeout_s: u32) -> Result<Value> {
            self.demo.capture(timeout_s)
        }
        fn preview(&mut self) -> Result<Preview> {
            self.demo.preview()
        }
        fn magnify(&mut self, ratio: u32, x: u16, y: u16) -> Result<()> {
            self.demo.magnify(ratio, x, y)
        }
        fn disconnect(&mut self) -> Result<Value> {
            if self.refuse_release {
                self.refuse_release = false;
                bail!("fixture: connection is still releasing");
            }
            self.demo.disconnect()
        }
    }
    #[test]
    fn failed_release_cannot_open_a_second_camera_and_missing_focus_is_not_reused() {
        let shared = Arc::new(Mutex::new(Snapshot {
            position: Some(12345),
            ..Snapshot::default()
        }));
        let mut missing = DelayedRelease {
            demo: Demo::default(),
            refuse_release: false,
            missing_focus: true,
        };
        assert!(refresh(&mut missing, &shared).is_err());
        assert!(shared.lock().unwrap().position.is_none());
        let calls = Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let count = calls.clone();
        let worker = Worker::with_factory(Box::new(move || {
            let first = count.fetch_add(1, Ordering::SeqCst) == 0;
            Ok(Box::new(DelayedRelease {
                demo: Demo {
                    fail_focus_after: first.then_some(0),
                    ..Default::default()
                },
                refuse_release: first,
                missing_focus: false,
            }))
        }));
        worker.send(0, Action::Connect).unwrap();
        let ready = until(&worker, |s| s.phase == Phase::Ready && !s.command_pending);
        worker
            .send(
                ready.revision,
                Action::Move {
                    target: 60620,
                    settle_ms: 100,
                },
            )
            .unwrap();
        let fault = until(&worker, |s| s.phase == Phase::Fault && !s.command_pending);
        worker
            .send(
                fault.revision,
                Action::Recover {
                    acknowledge_uncertain: false,
                },
            )
            .unwrap();
        let refusal = until(&worker, |s| s.phase == Phase::Fault && !s.command_pending);
        assert!(refusal.failure.unwrap().contains("still releasing"));
        assert_eq!(calls.load(Ordering::SeqCst), 1);
        worker
            .send(
                refusal.revision,
                Action::Recover {
                    acknowledge_uncertain: false,
                },
            )
            .unwrap();
        until(&worker, |s| s.phase == Phase::Ready && !s.command_pending);
        assert_eq!(calls.load(Ordering::SeqCst), 2);
    }
    #[test]
    fn failed_initialization_and_recovery_retain_the_connection_until_released() {
        let calls = Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let count = calls.clone();
        let worker = Worker::with_factory(Box::new(move || {
            let failed = count.fetch_add(1, Ordering::SeqCst) < 2;
            Ok(Box::new(DelayedRelease {
                demo: Demo::default(),
                refuse_release: failed,
                missing_focus: failed,
            }))
        }));
        worker.send(0, Action::Connect).unwrap();
        for expected_openings in 1..=2 {
            let fault = until(&worker, |s| s.phase == Phase::Fault && !s.command_pending);
            assert!(fault.failure.unwrap().contains("focus information"));
            assert!(fault.connected && fault.position.is_none());
            assert_eq!(calls.load(Ordering::SeqCst), expected_openings);
            worker
                .send(
                    fault.revision,
                    Action::Recover {
                        acknowledge_uncertain: false,
                    },
                )
                .unwrap();
            let releasing = until(&worker, |s| s.phase == Phase::Fault && !s.command_pending);
            assert!(releasing.failure.unwrap().contains("still releasing"));
            assert_eq!(calls.load(Ordering::SeqCst), expected_openings);
            worker
                .send(
                    releasing.revision,
                    Action::Recover {
                        acknowledge_uncertain: false,
                    },
                )
                .unwrap();
        }
        let ready = until(&worker, |s| s.phase == Phase::Ready && !s.command_pending);
        assert!(ready.failure.is_none());
        assert_eq!(calls.load(Ordering::SeqCst), 3);
    }
    #[test]
    fn state_machine_pause_resume_stop_and_stale_command() {
        let temp = tempfile::tempdir().unwrap();
        let w = Worker::new(PathBuf::new(), true);
        w.send(0, Action::Connect).unwrap();
        let ready = until(&w, |s| s.phase == Phase::Ready && !s.command_pending);
        w.send(
            0,
            Action::Move {
                target: 100,
                settle_ms: 500,
            },
        )
        .unwrap_err();
        assert_eq!(ready.position, Some(60627));
        w.send(
            ready.revision,
            Action::Capture {
                plan: Plan {
                    start: 60600,
                    end: 60620,
                    ..Plan::default()
                },
                root: temp.path().to_owned(),
            },
        )
        .unwrap();
        until(&w, |s| s.completed >= 1);
        w.request_pause();
        let paused = until(&w, |s| s.phase == Phase::Paused);
        thread::sleep(Duration::from_millis(250));
        assert_eq!(w.snapshot().completed, paused.completed);
        w.request_resume();
        until(&w, |s| s.completed > paused.completed);
        w.request_stop();
        let stopped = until(&w, |s| s.phase == Phase::Stopped && !s.command_pending);
        assert!(stopped.completed < stopped.total);
        let journal =
            std::fs::read_to_string(stopped.journal.unwrap().join("events.jsonl")).unwrap();
        assert_eq!(
            journal.matches("\"event\":\"capture_complete\"").count(),
            stopped.completed
        );
        w.send(stopped.revision, Action::Disconnect).unwrap();
        until(&w, |s| s.phase == Phase::Disconnected);
    }
    #[test]
    fn uncertain_shutter_never_retries_or_advances() {
        let temp = tempfile::tempdir().unwrap();
        let w = Worker::with_factory(Box::new(|| {
            Ok(Box::new(Demo {
                fail_capture: true,
                delay_ms: 0,
                ..Demo::default()
            }))
        }));
        w.send(0, Action::Connect).unwrap();
        let ready = until(&w, |s| s.phase == Phase::Ready && !s.command_pending);
        w.send(
            ready.revision,
            Action::Capture {
                plan: Plan {
                    start: 60600,
                    end: 60602,
                    ..Plan::default()
                },
                root: temp.path().to_owned(),
            },
        )
        .unwrap();
        let fault = until(&w, |s| s.phase == Phase::Fault && !s.command_pending);
        assert_eq!(fault.completed, 0);
        let journal = std::fs::read_to_string(fault.journal.unwrap().join("events.jsonl")).unwrap();
        assert_eq!(journal.matches("\"event\":\"capture_intent\"").count(), 1);
        assert!(!journal.contains("capture_complete"));
        w.send(
            fault.revision,
            Action::Move {
                target: 61000,
                settle_ms: 500,
            },
        )
        .unwrap();
        let rejected = until(&w, |s| s.revision > fault.revision && !s.command_pending);
        assert_eq!(rejected.phase, Phase::Fault);
        assert_eq!(rejected.position, Some(60600));
        assert!(rejected.exposure_uncertain);
        assert!(
            w.send(
                rejected.revision,
                Action::Recover {
                    acknowledge_uncertain: false
                }
            )
            .is_err()
        );
    }
    #[test]
    fn recovery_keeps_partial_journal_and_starts_only_on_explicit_new_capture() {
        for uncertain in [false, true] {
            let temp = tempfile::tempdir().unwrap();
            let openings = Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let count = openings.clone();
            let w = Worker::with_factory(Box::new(move || {
                let first = count.fetch_add(1, Ordering::SeqCst) == 0;
                Ok(Box::new(Demo {
                    delay_ms: 0,
                    fail_capture: first && uncertain,
                    fail_focus_after: (first && !uncertain).then_some(3),
                    ..Default::default()
                }))
            }));
            assert!(
                w.send(
                    0,
                    Action::Recover {
                        acknowledge_uncertain: true
                    }
                )
                .is_err()
            );
            w.send(0, Action::Connect).unwrap();
            let ready = until(&w, |s| s.phase == Phase::Ready && !s.command_pending);
            let plan = Plan {
                start: 60600,
                end: 60603,
                ..Plan::default()
            };
            w.send(
                ready.revision,
                Action::Capture {
                    plan: plan.clone(),
                    root: temp.path().into(),
                },
            )
            .unwrap();
            let fault = until(&w, |s| s.phase == Phase::Fault && !s.command_pending);
            assert_eq!(fault.exposure_uncertain, uncertain);
            assert_eq!(fault.completed, if uncertain { 0 } else { 2 });
            let old_journal = fault.journal.clone().unwrap();
            let old_bytes = std::fs::read(old_journal.join("events.jsonl")).unwrap();
            assert!(
                w.send(
                    fault.revision,
                    Action::Capture {
                        plan: plan.clone(),
                        root: temp.path().into()
                    }
                )
                .is_err()
            );
            if uncertain {
                assert!(
                    w.send(
                        fault.revision,
                        Action::Recover {
                            acknowledge_uncertain: false
                        }
                    )
                    .is_err()
                );
            }
            w.send(
                fault.revision,
                Action::Recover {
                    acknowledge_uncertain: uncertain,
                },
            )
            .unwrap();
            let recovered = until(&w, |s| s.phase == Phase::Ready && !s.command_pending);
            assert_eq!(openings.load(Ordering::SeqCst), 2);
            assert_eq!(recovered.completed, fault.completed);
            assert_eq!(recovered.sequence_id, fault.sequence_id);
            assert_eq!(recovered.journal.as_ref(), Some(&old_journal));
            assert_eq!(recovered.connection_generation, fault.connection_generation);
            assert!(recovered.failure.is_none() && !recovered.exposure_uncertain);
            assert_eq!(
                std::fs::read(old_journal.join("events.jsonl")).unwrap(),
                old_bytes
            );
            w.send(
                recovered.revision,
                Action::Capture {
                    plan,
                    root: temp.path().into(),
                },
            )
            .unwrap();
            let complete = until(&w, |s| s.phase == Phase::Complete && !s.command_pending);
            assert_eq!(complete.completed, 4);
            assert!(complete.sequence_id > fault.sequence_id);
            assert_ne!(complete.journal, fault.journal);
            assert_eq!(
                std::fs::read(old_journal.join("events.jsonl")).unwrap(),
                old_bytes
            );
        }
    }
}
