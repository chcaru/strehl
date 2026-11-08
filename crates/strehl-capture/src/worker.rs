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
    pub total: usize,
    pub journal: Option<PathBuf>,
    pub samples: Vec<Sample>,
    pub suggestion: Option<Suggestion>,
    pub connected: bool,
    pub timing: Option<RunTiming>,
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
            total: 0,
            journal: None,
            samples: vec![],
            suggestion: None,
            connected: false,
            timing: None,
        }
    }
}
pub enum Action {
    Connect,
    Disconnect,
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
        self.tx
            .try_send(Envelope { revision, action })
            .context("Camera command queue unavailable; read the current state before retrying")
    }
    pub fn request_pause(&self) {
        self.control.store(PAUSE, Ordering::SeqCst);
    }
    pub fn request_resume(&self) {
        self.control.store(RUN, Ordering::SeqCst);
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
    update(s, |v| {
        if let Some(timing) = &mut v.timing {
            match p {
                Phase::Paused => timing.pause(Instant::now()),
                Phase::Capturing => timing.resume(Instant::now()),
                Phase::Complete | Phase::Stopped | Phase::Fault => timing.finish(Instant::now()),
                _ => {}
            }
        }
        v.phase = p;
        v.message = message.into();
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
    let mut st = s.lock().unwrap();
    st.position =
        property(&status, "FocusPositionCurrentValue").and_then(|v| u16::try_from(v).ok());
    st.status = status.clone();
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
                                "Connecting · preparing MF, RAW and SD-only saving…",
                            );
                            let mut opened = factory()?;
                            let configured = opened.configure();
                            if let Err(e) = configured {
                                let _ = opened.disconnect();
                                return Err(e);
                            }
                            refresh(opened.as_mut(), &s)?;
                            let identity = opened.identity();
                            update(&s, |v| {
                                v.connected = true;
                                v.identity = identity;
                                v.phase = Phase::Ready;
                                v.message = "Connected · RAW captures stay on the SD card".into();
                                v.suggestion = None;
                                v.timing = None;
                            });
                            camera = Some(opened);
                        }
                        Action::Disconnect => {
                            phase(
                                &s,
                                Phase::Disconnecting,
                                "Disconnecting · restoring camera settings…",
                            );
                            if let Some(mut opened) = camera.take() {
                                let result = opened.disconnect()?;
                                ensure!(
                                    result["restored"] == true,
                                    "Camera settings were not fully restored: {result}"
                                );
                            }
                            update(&s, |v| {
                                v.connected = false;
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
                        } else if v.phase.active() {
                            v.phase = Phase::Fault;
                            if let Some(timing) = &mut v.timing {
                                timing.finish(Instant::now());
                            }
                        }
                        v.connected = camera.is_some();
                        v.message = format!("{error:#}");
                    });
                }
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
    ensure!(
        property(&status, "MediaSLOT1_RemainingNumber")
            .is_some_and(|n| n >= positions.len() as u64),
        "The card does not report enough remaining captures for this plan"
    );
    let initial_exposure = status.clone();
    let cycle = property(&status, "ShutterSpeed")
        .and_then(|shutter| timing::initial_cycle(shutter, plan.settle_ms))
        .context("Cannot estimate timed shutter speed")?;
    let mut log = Journal::create(&root, &plan, c.identity(), status)?;
    update(s, |v| {
        v.phase = Phase::Capturing;
        v.completed = 0;
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
                json!({"ordinal":ordinal,"target":target,"pixel_shift_shots":1,"camera_status":before}),
            )?;
            let response = c.capture(plan.capture_timeout_s)?;
            validate_capture(&response)?;
            log.record(
                "capture_complete",
                json!({"ordinal":ordinal,"target":target,"response":response}),
            )?;
            completed += 1;
            update(s, |v| {
                v.completed = completed;
                if let Some(timing) = &mut v.timing {
                    timing.complete_cycle(Instant::now());
                }
            });
            // Preview failure does not repeat or invalidate a completed exposure.
            if let Err(e) = preview(c, s) {
                s.lock().unwrap().preview_error = Some(e.to_string());
            }
        }
        Ok(true)
    })();
    match result {
        Ok(done) => {
            let outcome = if done { "complete" } else { "stopped" };
            log.finish(
                outcome,
                completed,
                "Camera events acknowledged; RAW files not downloaded or verified",
            )?;
            phase(
                s,
                if done {
                    Phase::Complete
                } else {
                    Phase::Stopped
                },
                format!(
                    "{} · {completed} captures on SD; metadata saved",
                    if done { "Complete" } else { "Stopped" }
                ),
            );
            Ok(())
        }
        Err(e) => {
            let reason = format!("{e:#}");
            let finish = log.finish("uncertain", completed, &reason);
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
    use super::*;
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
    #[test]
    fn state_machine_pause_resume_stop_and_stale_command() {
        let temp = tempfile::tempdir().unwrap();
        let w = Worker::new(PathBuf::new(), true);
        w.send(0, Action::Connect).unwrap();
        let ready = until(&w, |s| s.phase == Phase::Ready);
        w.send(
            0,
            Action::Move {
                target: 100,
                settle_ms: 500,
            },
        )
        .unwrap();
        let ready = until(&w, |s| s.revision > ready.revision);
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
        let stopped = until(&w, |s| s.phase == Phase::Stopped);
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
        let ready = until(&w, |s| s.phase == Phase::Ready);
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
        let fault = until(&w, |s| s.phase == Phase::Fault);
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
        let rejected = until(&w, |s| s.revision > fault.revision);
        assert_eq!(rejected.phase, Phase::Fault);
        assert_eq!(rejected.position, Some(60600));
    }
}
