use crate::{
    backend::{Camera, Demo, Native, Preview, property},
    bounds::{self, Sample, Suggestion},
    journal::{self, Journal},
    model::{Phase, Plan, Roi},
    power::{Outlet, RigPower},
    schedule::{Recipe, StackPower},
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
    pub manage_power: bool,
    pub power_error: Option<String>,
    pub standby_at: Option<Instant>,
    /// Hold focus after each group until the PC's check arrives, and take a
    /// group that failed for a fault of its exposures again in place.
    pub error_correction: bool,
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
            manage_power: false,
            power_error: None,
            standby_at: None,
            error_correction: false,
        }
    }
}
pub enum Action {
    Connect,
    ReadMark(mpsc::SyncSender<Result<u16, String>>),
    Scheduled {
        recipe: Box<Recipe>,
        root: PathBuf,
        reply: mpsc::Sender<Result<Phase, String>>,
    },
    Power {
        device: Outlet,
        on: bool,
    },
    PowerPlan(bool),
    ErrorCorrection(bool),
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
        /// Explicit focus positions (burst or retake), approached in the plan's
        /// direction. `None` captures the plan's own positions.
        positions: Option<Vec<u16>>,
    },
    Exposure {
        iso: u64,
        shutter: u64,
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
    pub power: Option<Arc<RigPower>>,
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
        Self::with_power(factory, None)
    }
    pub fn with_power(factory: Factory, power: Option<Arc<RigPower>>) -> Self {
        let (tx, rx) = mpsc::sync_channel::<Envelope>(16);
        let state = Arc::new(Mutex::new(Snapshot::default()));
        let control = Arc::new(AtomicU8::new(RUN));
        let s = state.clone();
        let c = control.clone();
        let rig = power.clone();
        let join = thread::spawn(move || run(factory, rx, s, c, rig));
        Self {
            state,
            tx,
            control,
            power,
            join: Some(join),
        }
    }
    pub fn snapshot(&self) -> Snapshot {
        self.state.lock().unwrap().clone()
    }
    pub fn mark_position(&self, revision: u64, start: bool) -> Result<u16> {
        let (tx, rx) = mpsc::sync_channel(1);
        self.send(revision, Action::ReadMark(tx))?;
        let position = rx
            .recv_timeout(Duration::from_secs(2))
            .context("Could not read the current lens position in time; the mark was kept")?
            .map_err(anyhow::Error::msg)?;
        let bound = if start { "Start" } else { "End" };
        self.state.lock().unwrap().message = format!("{bound} marked at {position}");
        Ok(position)
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
        if matches!(action, Action::Power { .. } | Action::PowerPlan(_)) {
            ensure!(self.power.is_some(), "Studio outlets are not configured");
            ensure!(
                !state.phase.active() && !state.exposure_uncertain,
                "Finish or recover the current exposure before switching power"
            );
        }
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
        if matches!(&action, Action::Scheduled { .. }) {
            ensure!(
                !state.phase.active() && !state.exposure_uncertain && state.failure.is_none(),
                "Camera requires attention before scheduled capture"
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
fn connect_camera(
    factory: &Factory,
    camera: &mut Option<Box<dyn Camera>>,
    s: &Shared,
) -> Result<()> {
    ensure!(camera.is_none(), "Camera is already connected");
    phase(
        s,
        Phase::Connecting,
        "Connecting · preparing manual focus and RAW capture…",
    );
    *camera = Some(factory()?);
    let opened = camera.as_mut().unwrap();
    opened.configure()?;
    refresh(opened.as_mut(), s)?;
    let mut identity = opened.identity();
    // The link the camera negotiated (round-3 performance plan, C1): a body
    // that falls back to USB 2.0 still works, at about half the capture
    // speed, and said nothing for four days.
    let usb = crate::ptp::camera_usb_speed_mbps();
    if let Some(speed) = usb {
        identity["usb_speed_mbps"] = json!(speed);
    }
    update(s, |v| {
        v.connected = true;
        v.capture_run = false;
        v.connection_generation += 1;
        v.standby_at = None;
        v.failure = None;
        v.exposure_uncertain = false;
        v.identity = identity;
        v.phase = Phase::Ready;
        v.message = if v.status["capture_destination"] == "host-pc" {
            if v.status["pixel_shift_shots"] == 4 {
                "Connected · A7CR four-shot pixel shift saves to the PC"
            } else {
                "Connected · RAW saves to the PC"
            }
        } else {
            "Connected · RAW captures stay on the SD card"
        }
        .into();
        if let Some(warning) = usb.and_then(usb_link_warning) {
            v.message = format!("{} · {warning}", v.message);
        }
        v.suggestion = None;
        v.timing = None;
    });
    Ok(())
}
/// What to tell the user about a camera link slower than USB 3, or `None`.
pub fn usb_link_warning(speed_mbps: u32) -> Option<String> {
    (speed_mbps < crate::ptp::USB3_MBPS).then(|| {
        format!(
            "Slow camera link: USB {speed_mbps} Mbit/s, not USB 3. Each RAW reaches the Pi {} {}",
            "several times slower and a plane takes about twice as long.",
            "Push the cable fully into a blue port and the camera, or use a USB 3 data cable"
        )
    })
}

fn wake_camera(
    rig: &RigPower,
    factory: &Factory,
    camera: &mut Option<Box<dyn Camera>>,
    s: &Shared,
) -> Result<()> {
    ensure!(camera.is_none(), "Camera is already connected");
    rig.set(Outlet::Camera, true)?;
    phase(
        s,
        Phase::Connecting,
        "Camera supply on · waiting for the A7CR over USB…",
    );
    let end = Instant::now() + Duration::from_secs(30);
    while crate::ptp::a7cr_usb_count()? != 1 {
        ensure!(
            Instant::now() < end,
            "Camera supply is on but the A7CR did not appear over USB. Check its physical switch and USB Remote Shoot mode"
        );
        thread::sleep(Duration::from_millis(200));
    }
    connect_camera(factory, camera, s)
}
fn switch_camera_off(
    rig: &RigPower,
    camera: &mut Option<Box<dyn Camera>>,
    s: &Shared,
) -> Result<()> {
    if let Some(c) = camera.as_mut() {
        ensure!(
            rig.read(Outlet::Camera)?["on"] == true,
            "Camera outlet is already off; check its power source"
        );
        c.standby()?;
        *camera = None;
        update(s, |v| {
            v.standby_at = Some(Instant::now());
            v.connected = false;
            v.preview = None;
            v.preview_at = None;
            v.preview_error = None;
            v.position = None;
            v.connection_generation += 1;
            if !matches!(v.phase, Phase::Complete | Phase::Stopped) {
                v.phase = Phase::Disconnected;
                v.status = Value::Null;
            }
        });
    }
    ensure!(
        s.lock()
            .unwrap()
            .standby_at
            .is_some_and(|t| t.elapsed() < Duration::from_secs(90))
            && crate::ptp::a7cr_usb_count()? == 0,
        "Connect the camera first so Strehl can confirm standby before cutting power"
    );
    rig.set(Outlet::Camera, false)?;
    Ok(())
}
fn run(
    factory: Factory,
    rx: mpsc::Receiver<Envelope>,
    s: Shared,
    control: Arc<AtomicU8>,
    power: Option<Arc<RigPower>>,
) {
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
                if let Action::ReadMark(reply) = envelope.action {
                    let position = (|| {
                        let cam = camera.as_mut().context("Connect a camera to mark focus")?;
                        refresh(cam.as_mut(), &s)?;
                        s.lock()
                            .unwrap()
                            .position
                            .context("Focus position unavailable")
                    })();
                    update(&s, |v| v.command_pending = false);
                    let _ = reply.send(position.map_err(|e| format!("{e:#}")));
                    continue;
                }
                let scheduled_reply = if let Action::Scheduled { reply, .. } = &envelope.action {
                    Some(reply.clone())
                } else {
                    None
                };
                let result = (|| -> Result<()> {
                    match envelope.action {
                        Action::ReadMark(_) => unreachable!(),
                        Action::Connect => {
                            connect_camera(&factory, &mut camera, &s)?;
                        }
                        Action::PowerPlan(enabled) => {
                            ensure!(power.is_some(), "Studio outlets are not configured");
                            update(&s, |v| v.manage_power = enabled);
                        }
                        Action::ErrorCorrection(enabled) => {
                            update(&s, |v| v.error_correction = enabled);
                        }
                        Action::Power { device, on } => {
                            let rig = power
                                .as_deref()
                                .context("Studio outlets are not configured")?;
                            let result = (|| -> Result<()> {
                                match device {
                                    Outlet::Light => {
                                        rig.set(device, on)?;
                                    }
                                    Outlet::Camera if on => {
                                        wake_camera(rig, &factory, &mut camera, &s)?;
                                    }
                                    Outlet::Camera => {
                                        switch_camera_off(rig, &mut camera, &s)?;
                                    }
                                }
                                Ok(())
                            })();
                            update(&s, |v| {
                                v.power_error = result.as_ref().err().map(|e| format!("{e:#}"));
                                if result.is_ok() && device == Outlet::Camera && !on {
                                    v.message = "Camera shut down · supply off".into();
                                }
                            });
                            // An outlet failure is separate from a camera/RAW failure. A rejected
                            // light request must not put a disconnected camera into recovery.
                            let connecting = s.lock().unwrap().phase == Phase::Connecting;
                            if let Err(error) = result
                                && device == Outlet::Camera
                                && (camera.is_some() || connecting)
                            {
                                phase(
                                    &s,
                                    if camera.is_some() {
                                        Phase::Fault
                                    } else {
                                        Phase::Disconnected
                                    },
                                    format!("{error:#}"),
                                );
                                update(&s, |v| v.connected = camera.is_some());
                            }
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
                                if v.power_error == before.failure {
                                    v.power_error = None;
                                }
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
                        Action::Capture {
                            plan,
                            root,
                            positions,
                        } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "A sequence is already active"
                            );
                            let options = if s.lock().unwrap().manage_power {
                                StackPower::managed()
                            } else {
                                StackPower::default()
                            };
                            run_stack(
                                &mut camera,
                                &s,
                                &control,
                                power.as_deref(),
                                StackRun {
                                    plan,
                                    root,
                                    positions,
                                    options,
                                    warmup: power.as_ref().map_or(0, |rig| rig.warmup_seconds()),
                                },
                            )?;
                        }
                        Action::Scheduled { recipe, root, .. } => {
                            if control.load(Ordering::SeqCst) == STOP {
                                phase(
                                    &s,
                                    Phase::Stopped,
                                    "Scheduled stack stopped before starting",
                                );
                                return Ok(());
                            }
                            if camera.is_none() {
                                if recipe.power.wake_camera {
                                    wake_camera(
                                        power.as_deref().context("Camera outlet unavailable")?,
                                        &factory,
                                        &mut camera,
                                        &s,
                                    )?;
                                } else {
                                    connect_camera(&factory, &mut camera, &s)?;
                                }
                            }
                            let c = camera.as_mut().context("Camera missing")?.as_mut();
                            let current = refresh(c, &s)?;
                            ensure!(
                                current["model"] == recipe.model
                                    && property(&current, "FNumber") == Some(recipe.aperture),
                                "Camera model or aperture differs from the scheduled stack"
                            );
                            if current["pixel_shift_shots"].as_u64().unwrap_or(1)
                                != recipe.shots as u64
                            {
                                c.set_pixel_shift(recipe.shots)?;
                            }
                            if property(&current, "IsoSensitivity") != Some(recipe.iso)
                                || property(&current, "ShutterSpeed") != Some(recipe.shutter)
                            {
                                c.set_exposure(recipe.iso, recipe.shutter)?;
                            }
                            let current = refresh(c, &s)?;
                            ensure!(
                                current["pixel_shift_shots"].as_u64().unwrap_or(1)
                                    == recipe.shots as u64
                                    && property(&current, "IsoSensitivity") == Some(recipe.iso)
                                    && property(&current, "ShutterSpeed") == Some(recipe.shutter)
                                    && property(&current, "FNumber") == Some(recipe.aperture),
                                "Scheduled exposure or pixel-shift mode was not confirmed"
                            );
                            run_stack(
                                &mut camera,
                                &s,
                                &control,
                                power.as_deref(),
                                StackRun {
                                    plan: recipe.plan,
                                    root,
                                    positions: None,
                                    options: recipe.power,
                                    warmup: recipe.warmup_seconds,
                                },
                            )?;
                        }
                        Action::Exposure { iso, shutter } => {
                            ensure!(
                                s.lock().unwrap().phase.can_edit(),
                                "Finish the sequence before changing exposure"
                            );
                            let c = camera.as_mut().context("Connect a camera first")?;
                            c.set_exposure(iso, shutter)?;
                            refresh(c.as_mut(), &s)?;
                            update(&s, |v| {
                                v.timing = None;
                                v.message = "Exposure updated".into();
                            });
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
                if let Err(ref error) = result {
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
                if let Some(reply) = scheduled_reply {
                    let _ = reply.send(
                        result
                            .map(|()| s.lock().unwrap().phase.clone())
                            .map_err(|e| format!("{e:#}")),
                    );
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

struct StackRun {
    plan: Plan,
    root: PathBuf,
    positions: Option<Vec<u16>>,
    options: StackPower,
    warmup: u32,
}
fn run_stack(
    camera: &mut Option<Box<dyn Camera>>,
    s: &Shared,
    control: &AtomicU8,
    rig: Option<&RigPower>,
    run: StackRun,
) -> Result<()> {
    let p = run.options;
    ensure!(
        !p.uses_plugs() || rig.is_some(),
        "Studio outlets are not configured"
    );
    if p.camera_off {
        ensure!(
            s.lock().unwrap().identity["hello"]["power_off_protocol"] == 1,
            "This camera cannot confirm an orderly power-off"
        );
    }
    let lamp = rig.filter(|_| p.light_on).map(|r| (r, run.warmup));
    capture(
        camera.as_mut().context("Connect a camera first")?.as_mut(),
        s,
        control,
        run.plan,
        run.root,
        run.positions,
        lamp,
    )?;
    // Both writes follow the final durable journal receipt. Attempt the other
    // requested outlet even if the first reports a fault.
    if let Some(rig) = rig.filter(|_| p.light_off || p.camera_off) {
        let light = if p.light_off {
            rig.set(Outlet::Light, false).map(|_| ())
        } else {
            Ok(())
        };
        let body = if p.camera_off {
            switch_camera_off(rig, camera, s)
        } else {
            Ok(())
        };
        let errors: Vec<_> = [light, body]
            .into_iter()
            .filter_map(|r| r.err().map(|e| format!("{e:#}")))
            .collect();
        update(s, |v| {
            v.power_error = (!errors.is_empty()).then(|| errors.join(". "))
        });
        ensure!(
            errors.is_empty(),
            "Capture saved; studio power needs attention: {}",
            errors.join(". ")
        );
    }
    Ok(())
}
fn capture(
    c: &mut dyn Camera,
    s: &Shared,
    control: &AtomicU8,
    plan: Plan,
    root: PathBuf,
    explicit: Option<Vec<u16>>,
    managed: Option<(&RigPower, u32)>,
) -> Result<()> {
    plan.validate()?;
    let kind = if explicit.is_some() {
        "positions"
    } else {
        "plan"
    };
    let positions = match explicit {
        Some(positions) => {
            validate_positions(&plan, &positions)?;
            positions
        }
        None => plan.positions()?,
    };
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
    let mut log = Journal::create(&root, &plan, &positions, kind, c.identity(), status)?;
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
            timing::initial_setup(plan.settle_ms)
                + Duration::from_secs(managed.map_or(0, |(_, secs)| u64::from(secs))),
            Instant::now(),
        ));
    });
    let mut completed = 0;
    let mut light_requested = false;
    // Error correction needs the PC's checker, so only a run stored there.
    let mut verify = host && s.lock().unwrap().error_correction;
    let result = (|| -> Result<bool> {
        if let Some((rig, warmup)) = managed {
            update(s, |v| {
                v.power_error = None;
                v.message = format!("Studio light on · warming for {warmup} s");
            });
            light_requested = true;
            rig.set(Outlet::Light, true)?;
            let until = Instant::now() + Duration::from_secs(u64::from(warmup));
            while Instant::now() < until {
                if !checkpoint(c, s, control, Phase::Capturing)? {
                    return Ok(false);
                }
                thread::sleep(Duration::from_millis(100));
            }
            // The meter can still show the previous zero for a moment after the relay closes.
            let meter_deadline = Instant::now() + Duration::from_secs(5);
            loop {
                let reading = rig.read(Outlet::Light)?;
                if reading["on"] == true && reading["watts"].as_f64().is_some_and(|w| w > 0.) {
                    break;
                }
                ensure!(
                    reading["on"] == true && Instant::now() < meter_deadline,
                    "Light outlet has no measured load. Switch the KL 1500 LCD on and check its power cord before starting"
                );
                if !checkpoint(c, s, control, Phase::Capturing)? {
                    return Ok(false);
                }
                thread::sleep(Duration::from_millis(200));
            }
        }
        if !checkpoint(c, s, control, Phase::Capturing)? {
            return Ok(false);
        }
        let prestart =
            u16::try_from(i32::from(positions[0]) - plan.direction() * i32::from(plan.approach))
                .context("Shorten Approach; the first position is too close to the lens limit")?;
        log.record("approach_intent", json!({"target":prestart}))?;
        let response = c.focus(prestart, plan.settle_ms)?;
        log.record("approach_complete", response)?;
        if let Some(timing) = &mut s.lock().unwrap().timing {
            timing.approached(Instant::now());
        }
        let targets = positions.clone();
        let ctx = Run {
            s,
            control,
            plan: &plan,
            shots,
            initial: &initial_exposure,
        };
        // Error correction (2026-11-20): the controller does not hold focus
        // for the PC's check. Groups still being checked are collected
        // between planes; a plane the PC asks to retake is visited again
        // through the approach move, and the run goes on. MEASURED: a plane
        // revisited that way lands within about one step of the first visit,
        // far inside the depth a point stays sharp over, and a hold cost
        // 1.5-2 s a plane.
        let mut owed: Vec<Owed> = Vec::new();
        for (ordinal, target) in positions.into_iter().enumerate() {
            if !checkpoint(c, s, control, Phase::Capturing)? {
                return Ok(false);
            }
            if verify {
                let Some(due) = collect_verdicts(c, &ctx, &mut log, &mut owed, &mut verify, false)?
                else {
                    return Ok(false);
                };
                for (o, reason) in due {
                    let next = Some((target, plan.settle_ms));
                    if !retake(c, &ctx, &mut log, &mut owed, o, &reason, next)? {
                        return Ok(false);
                    }
                }
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
            // The lens goes on to the next plane as soon as this group's last
            // exposure is in the camera (MEASURED 2026-11-20: 7.3 s a
            // four-shot plane to 5.65).
            let next = targets.get(ordinal + 1).map(|&n| (n, plan.settle_ms));
            let Some(response) = take_group(c, &ctx, &mut log, ordinal, target, next)? else {
                return Ok(false);
            };
            completed += 1;
            update(s, |v| {
                v.completed = completed;
                if let Some(timing) = &mut v.timing {
                    timing.complete_cycle(Instant::now());
                }
            });
            if verify {
                owed.push(Owed {
                    ordinal,
                    target,
                    plane: plane_of(&response),
                    group: group_key(&response).context("Captured group has no identity")?,
                    retakes: 0,
                    since: Instant::now(),
                });
            }
        }
        // The last planes' checks: wait for them, retaking as asked.
        while verify && !owed.is_empty() {
            update(s, |v| {
                v.message = "Checking the last planes on the PC…".into()
            });
            let Some(due) = collect_verdicts(c, &ctx, &mut log, &mut owed, &mut verify, true)?
            else {
                return Ok(false);
            };
            for (o, reason) in due {
                if !retake(c, &ctx, &mut log, &mut owed, o, &reason, None)? {
                    return Ok(false);
                }
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
            let exposure_known = !s.lock().unwrap().exposure_uncertain;
            if let Some((rig, _)) = managed
                && light_requested
                && exposure_known
                && let Err(power_error) = rig.set(Outlet::Light, false)
            {
                update(s, |v| {
                    v.power_error = Some(format!("Check the light outlet: {power_error:#}"))
                });
            }
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

/// Error correction: retakes of one plane before keeping what it has.
const MAX_RETAKES: usize = 2;
/// How long a group's check may take to arrive. It normally arrives about
/// 1.5-2 s after the group (the last RAW reaches the PC in 1.1-1.3 s and the
/// check takes 0.2-0.4 s), during the next plane; without one, error
/// correction stops for the run.
const VERDICT_WAIT: Duration = Duration::from_secs(15);

/// A captured group's identity as the PC's checker records it: the camera's
/// group id, or for a single shot without one, its frame name.
fn group_key(response: &Value) -> Option<String> {
    let first = response["files"].as_array()?.first()?;
    first["group_id"]
        .as_str()
        .filter(|g| !g.is_empty())
        .or_else(|| first["name"].as_str())
        .map(str::to_owned)
}

/// What a capture run carries into each group.
struct Run<'a> {
    s: &'a Shared,
    control: &'a AtomicU8,
    plan: &'a Plan,
    shots: u64,
    initial: &'a Value,
}

/// A group the PC is still checking (error correction).
struct Owed {
    ordinal: usize,
    target: u16,
    /// The plane number its files carry, when the backend numbers planes.
    plane: Option<u64>,
    group: String,
    retakes: usize,
    since: Instant,
}

/// The plane number a captured group's files carry.
fn plane_of(response: &Value) -> Option<u64> {
    response["files"].as_array()?.first()?["plane"].as_u64()
}

/// One group at the lens's current position: the exposure checked against
/// the run's, the intent recorded before the shutter, room for its RAWs, the
/// capture and its record. `next`: where the lens may go once the group's
/// last exposure is in the camera. `None` when the run was stopped.
fn take_group(
    c: &mut dyn Camera,
    ctx: &Run,
    log: &mut Journal,
    ordinal: usize,
    target: u16,
    next: Option<(u16, u32)>,
) -> Result<Option<Value>> {
    let s = ctx.s;
    let before = refresh(c, s)?;
    validate_exposure(&before)?;
    ensure!(
        before["pixel_shift_shots"].as_u64().unwrap_or(1) == ctx.shots,
        "Capture mode changed during the stack; no next shutter was sent"
    );
    for key in [
        "ExposureProgramMode",
        "IsoSensitivity",
        "ShutterSpeed",
        "FNumber",
    ] {
        ensure!(
            property(&before, key) == property(ctx.initial, key),
            "{key} changed during the run; sequence stopped before the next shutter"
        );
    }
    log.record(
        "capture_intent",
        json!({"ordinal":ordinal,"target":target,"pixel_shift_shots":ctx.shots,"camera_status":before}),
    )?;
    c.sync_journal(&log.directory)?;
    while !c.prepare_capture()? {
        if !checkpoint(c, s, ctx.control, Phase::Capturing)? {
            return Ok(None);
        }
        thread::sleep(Duration::from_millis(100));
    }
    if !checkpoint(c, s, ctx.control, Phase::Capturing)? {
        return Ok(None);
    }
    c.set_next_focus(next);
    s.lock().unwrap().exposure_uncertain = true;
    let response = c.capture(ctx.plan.capture_timeout_s)?;
    ensure!(
        response["pixel_shift_shots"].as_u64().unwrap_or(1) == ctx.shots,
        "Capture mode changed during the stack"
    );
    validate_capture(&response)?;
    s.lock().unwrap().exposure_uncertain = false;
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
    Ok(Some(response))
}

/// Error correction: the PC's verdicts on the groups it is still checking.
/// Returns the groups to retake now (`wait`: until at least one verdict is
/// due or none is owed). A group unanswered for `VERDICT_WAIT`, or a PC that
/// cannot answer, turns error correction off for the run: the capture is
/// never stalled on the PC. `None` when the run was stopped.
fn collect_verdicts(
    c: &mut dyn Camera,
    ctx: &Run,
    log: &mut Journal,
    owed: &mut Vec<Owed>,
    verify: &mut bool,
    wait: bool,
) -> Result<Option<Vec<(Owed, String)>>> {
    let mut due = Vec::new();
    loop {
        let mut i = 0;
        while i < owed.len() {
            let unanswered = match c.verdict(&owed[i].group) {
                Ok(Some(v)) => {
                    let o = owed.remove(i);
                    if v["retake"] == true {
                        let reason = v["reason"].as_str().unwrap_or("check failed").to_owned();
                        if o.retakes < MAX_RETAKES {
                            due.push((o, reason));
                        } else {
                            log.record(
                                "retake_exhausted",
                                json!({"ordinal":o.ordinal,"target":o.target,"group":o.group,"retakes":o.retakes,"reason":reason}),
                            )?;
                        }
                    }
                    continue;
                }
                Ok(None) => (owed[i].since.elapsed() >= VERDICT_WAIT)
                    .then(|| format!("no check from the PC within {} s", VERDICT_WAIT.as_secs())),
                Err(e) => {
                    // A receiver without the verdict store, or a backend
                    // without a PC, will never answer; a dropped request may.
                    let permanent = e.downcast_ref::<reqwest::Error>().is_none_or(|http| {
                        http.status()
                            .is_some_and(|s| matches!(s.as_u16(), 404 | 405))
                    });
                    permanent.then(|| format!("{e:#}"))
                }
            };
            if let Some(why) = unanswered {
                *verify = false;
                log.record(
                    "error_correction_off",
                    json!({"ordinal":owed[i].ordinal,"group":owed[i].group,"reason":why}),
                )?;
                owed.clear();
                return Ok(Some(due));
            }
            i += 1;
        }
        if !wait || owed.is_empty() || !due.is_empty() {
            return Ok(Some(due));
        }
        if !checkpoint(c, ctx.s, ctx.control, Phase::Capturing)? {
            return Ok(None);
        }
        thread::sleep(Duration::from_millis(150));
    }
}

/// Visits a plane again for a retake: below it by the approach move, so it
/// is reached from the capture side as before, then a group recorded under
/// the plane's own number. Its check is owed like any other group's.
fn retake(
    c: &mut dyn Camera,
    ctx: &Run,
    log: &mut Journal,
    owed: &mut Vec<Owed>,
    o: Owed,
    reason: &str,
    next: Option<(u16, u32)>,
) -> Result<bool> {
    let n = o.retakes + 1;
    log.record(
        "retake_intent",
        json!({"ordinal":o.ordinal,"target":o.target,"group":o.group,"retake":n,"reason":reason}),
    )?;
    update(ctx.s, |v| {
        v.message = format!(
            "Plane {} of {} · retaking: {reason}",
            o.ordinal + 1,
            v.total
        )
    });
    let below =
        u16::try_from(i32::from(o.target) - ctx.plan.direction() * i32::from(ctx.plan.approach))
            .context("Retake approach beyond the lens limit")?;
    let first = c.focus(below, ctx.plan.settle_ms)?;
    let at = c.focus(o.target, ctx.plan.settle_ms)?;
    log.record(
        "retake_focus",
        json!({"ordinal":o.ordinal,"target":o.target,"approach":first,"response":at}),
    )?;
    if !checkpoint(c, ctx.s, ctx.control, Phase::Capturing)? {
        return Ok(false);
    }
    c.retake_plane(o.plane);
    let Some(response) = take_group(c, ctx, log, o.ordinal, o.target, next)? else {
        return Ok(false);
    };
    owed.push(Owed {
        ordinal: o.ordinal,
        target: o.target,
        plane: o.plane.or_else(|| plane_of(&response)),
        group: group_key(&response).context("Captured group has no identity")?,
        retakes: n,
        since: Instant::now(),
    });
    Ok(true)
}

/// Explicit positions must keep the plan's approach direction so that every
/// plane is reached from the same side (repeats are allowed: a burst).
pub fn validate_positions(plan: &Plan, positions: &[u16]) -> Result<()> {
    ensure!(
        (1..=4096).contains(&positions.len()),
        "Choose 1-4096 focus positions"
    );
    let direction = plan.direction();
    ensure!(
        positions
            .windows(2)
            .all(|w| (i32::from(w[1]) - i32::from(w[0])) * direction >= 0),
        "Positions must follow the capture direction so each plane is approached from the same side"
    );
    u16::try_from(i32::from(positions[0]) - direction * i32::from(plan.approach))
        .ok()
        .context("Shorten Approach; the first position is too close to the lens limit")?;
    Ok(())
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
    fn marking_reads_the_lens_even_if_the_idle_cache_is_stale() {
        let w = Worker::new(PathBuf::new(), true);
        w.send(0, Action::Connect).unwrap();
        let ready = until(&w, |s| s.phase == Phase::Ready && !s.command_pending);
        w.state.lock().unwrap().position = Some(1);
        assert_ne!(ready.position, Some(1));
        assert_eq!(
            w.mark_position(ready.revision, true).unwrap(),
            ready.position.unwrap()
        );
        assert_eq!(w.snapshot().position, ready.position);
    }
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

    /// A four-shot camera storing to the PC whose checker fails the groups
    /// named in `retake` (or never answers, with `answer: false`).
    struct Checked {
        demo: Demo,
        captures: usize,
        focuses: Vec<u16>,
        repeats: usize,
        asked: Vec<String>,
        retake: Vec<&'static str>,
        answer: bool,
        /// Each group's check is pending for this many asks first.
        late: usize,
        /// Focus moves and verdicts in the order they happened.
        ops: Vec<String>,
    }
    impl Checked {
        fn new(retake: Vec<&'static str>, answer: bool) -> Self {
            Self {
                demo: Demo {
                    shots: 4,
                    ..Demo::default()
                },
                captures: 0,
                focuses: Vec::new(),
                repeats: 0,
                asked: Vec::new(),
                retake,
                answer,
                late: 0,
                ops: Vec::new(),
            }
        }
    }
    impl Camera for Checked {
        fn identity(&self) -> Value {
            self.demo.identity()
        }
        fn status(&mut self) -> Result<Value> {
            let mut s = self.demo.status()?;
            s["capture_destination"] = json!("host-pc");
            s["raw_max_bytes"] = json!(crate::ptp::MEMBER_LIMIT);
            Ok(s)
        }
        fn configure(&mut self) -> Result<()> {
            Ok(())
        }
        fn focus(&mut self, target: u16, settle_ms: u32) -> Result<Value> {
            self.focuses.push(target);
            self.ops.push(format!("focus {target}"));
            self.demo.focus(target, settle_ms)
        }
        fn capture(&mut self, _: u32) -> Result<Value> {
            self.captures += 1;
            self.ops.push(format!("capture ptp-test-{}", self.captures));
            let n = self.captures;
            let files: Vec<_> = (1..=4)
                .map(|k| json!({"name":format!("frame-{:06}.ARW",(n-1)*4+k),"bytes":122_968_064,
                    "sha256":"a".repeat(64),"durable":false,"group_id":format!("ptp-test-{n}"),"member_index":k,"members":4}))
                .collect();
            Ok(
                json!({"destination":"host-pc-queue","completion":"ram-queued-sha256","file_verification":"ram-sha256",
                "raw_compression":"uncompressed","pixel_shift_shots":4,"group_complete":true,"files":files,
                "camera_reply":{"completion":"ptp-group-complete","group_idle":true,"buffer_empty":true}}),
            )
        }
        fn preview(&mut self) -> Result<Preview> {
            self.demo.preview()
        }
        fn magnify(&mut self, _: u32, _: u16, _: u16) -> Result<()> {
            Ok(())
        }
        fn disconnect(&mut self) -> Result<Value> {
            self.demo.disconnect()
        }
        fn verdict(&mut self, group: &str) -> Result<Option<Value>> {
            self.asked.push(group.to_owned());
            if !self.answer {
                bail!("no verdict store");
            }
            if self.asked.iter().filter(|g| *g == group).count() <= self.late {
                return Ok(None);
            }
            self.ops.push(format!("verdict {group}"));
            let retake = self.retake.contains(&group);
            Ok(Some(
                json!({"state":"checked","retake":retake,"reason":if retake {"witness tiles disagree locally"} else {""}}),
            ))
        }
        fn repeat_plane(&mut self) {
            self.repeats += 1;
        }
    }
    fn checked_run(camera: &mut Checked, error_correction: bool) -> (Snapshot, String) {
        let temp = tempfile::tempdir().unwrap();
        let shared = Arc::new(Mutex::new(Snapshot {
            error_correction,
            ..Snapshot::default()
        }));
        let plan = Plan {
            start: 60000,
            end: 60002,
            step: 1,
            ..Plan::default()
        };
        capture(
            camera,
            &shared,
            &AtomicU8::new(RUN),
            plan,
            temp.path().into(),
            None,
            None,
        )
        .unwrap();
        let run = std::fs::read_dir(temp.path())
            .unwrap()
            .next()
            .unwrap()
            .unwrap()
            .path();
        let journal = std::fs::read_to_string(run.join("events.jsonl")).unwrap();
        let s = shared.lock().unwrap().clone();
        (s, journal)
    }
    #[test]
    fn error_correction_retakes_a_failed_plane_later_through_the_approach() {
        let mut camera = Checked::new(vec!["ptp-test-2"], true);
        let (s, journal) = checked_run(&mut camera, true);
        // Plane 2's first group failed. Its check came back while the lens was
        // on the way to plane 3; plane 2 was visited again from below (the
        // approach of 128), retaken, and the run went on to plane 3.
        assert_eq!(camera.captures, 4);
        assert_eq!(camera.repeats, 1);
        assert_eq!(
            &camera.focuses[1..],
            [60000, 60001, 60001 - 128, 60001, 60002],
            "the retake approaches its plane from the capture side"
        );
        assert_eq!(
            camera.asked,
            ["ptp-test-1", "ptp-test-2", "ptp-test-3", "ptp-test-4"]
        );
        assert_eq!(s.completed, 3, "a retake is not a new plane");
        assert_eq!(s.phase, Phase::Complete);
        assert_eq!(journal.matches("\"event\":\"retake_intent\"").count(), 1);
        assert_eq!(journal.matches("\"event\":\"retake_focus\"").count(), 1);
        assert!(journal.contains("\"group\":\"ptp-test-2\""));
        assert_eq!(journal.matches("\"event\":\"capture_buffered\"").count(), 4);
    }
    #[test]
    fn error_correction_never_holds_the_next_plane_for_a_check() {
        // Every check answers only on its third ask: the planes are taken
        // while their predecessors are still being checked.
        let mut camera = Checked::new(vec![], true);
        camera.late = 2;
        let (s, _) = checked_run(&mut camera, true);
        let at = |op: &str| camera.ops.iter().position(|o| o == op).unwrap();
        assert!(at("capture ptp-test-2") < at("verdict ptp-test-1"));
        assert!(at("capture ptp-test-3") < at("verdict ptp-test-2"));
        assert_eq!((camera.captures, s.completed), (3, 3));
        // The run ends only once every check has come back.
        assert!(at("verdict ptp-test-3") > at("capture ptp-test-3"));
        assert_eq!(s.phase, Phase::Complete);
    }
    #[test]
    fn error_correction_gives_up_on_a_plane_and_on_a_silent_pc() {
        // Plane 1 fails three times: two retakes, then it keeps what it has
        // and the stack goes on.
        let mut camera = Checked::new(vec!["ptp-test-1", "ptp-test-2", "ptp-test-4"], true);
        let (s, journal) = checked_run(&mut camera, true);
        assert_eq!(camera.captures, 3 + 2);
        assert_eq!(journal.matches("\"event\":\"retake_intent\"").count(), 2);
        assert_eq!(journal.matches("\"event\":\"retake_exhausted\"").count(), 1);
        assert_eq!(s.completed, 3);
        // A receiver that cannot answer: asked once, then the run carries on.
        let mut camera = Checked::new(vec![], false);
        let (s, journal) = checked_run(&mut camera, true);
        assert_eq!(
            (camera.captures, camera.asked.len(), s.completed),
            (3, 1, 3)
        );
        assert_eq!(
            journal
                .matches("\"event\":\"error_correction_off\"")
                .count(),
            1
        );
        // Off: never asked.
        let mut camera = Checked::new(vec!["ptp-test-1"], true);
        let (s, _) = checked_run(&mut camera, false);
        assert_eq!(
            (camera.captures, camera.asked.len(), s.completed),
            (3, 0, 3)
        );
    }
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
            None,
            None,
        )
        .unwrap_err();
        assert!(error.to_string().contains("Shorten the stack"));
        assert_eq!(std::fs::read_dir(temp.path()).unwrap().count(), 0);
        assert!(!shared.lock().unwrap().exposure_uncertain);
    }
    #[test]
    fn exposure_and_explicit_position_burst_capture() {
        let temp = tempfile::tempdir().unwrap();
        let w = Worker::new(PathBuf::new(), true);
        w.send(0, Action::Connect).unwrap();
        let s = until(&w, |s| s.phase == Phase::Ready && !s.command_pending);
        w.send(
            s.revision,
            Action::Exposure {
                iso: 800,
                shutter: 65546,
            },
        )
        .unwrap();
        let s = until(&w, |s| !s.command_pending);
        assert_eq!(property(&s.status, "IsoSensitivity"), Some(800));
        assert_eq!(property(&s.status, "ShutterSpeed"), Some(65546));
        let plan = Plan {
            start: 60600,
            end: 60620,
            ..Plan::default()
        };
        assert!(validate_positions(&plan, &[60610, 60600]).is_err());
        assert!(validate_positions(&plan, &[]).is_err());
        validate_positions(&plan, &[60600, 60600, 60605]).unwrap();
        w.send(
            s.revision,
            Action::Capture {
                plan,
                root: temp.path().into(),
                positions: Some(vec![60605; 3]),
            },
        )
        .unwrap();
        let done = until(&w, |s| s.phase == Phase::Complete && !s.command_pending);
        assert_eq!(done.completed, 3);
        let journal = done.journal.unwrap();
        let manifest: Value =
            serde_json::from_slice(&std::fs::read(journal.join("manifest.json")).unwrap()).unwrap();
        assert_eq!(manifest["focus_positions"], json!([60605, 60605, 60605]));
        assert_eq!(manifest["capture_kind"], "positions");
        let events = std::fs::read_to_string(journal.join("events.jsonl")).unwrap();
        assert!(events.contains(r#""target":60477"#), "approach from below");
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
                positions: None,
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
                positions: None,
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
                    positions: None,
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
                        root: temp.path().into(),
                        positions: None,
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
                    positions: None,
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

    /// The link warning: USB 2.0 and slower warn, USB 3 and faster do not.
    #[test]
    fn a_camera_link_below_usb3_is_reported() {
        for slow in [12, 480] {
            let warning = super::usb_link_warning(slow).expect("a slow link warns");
            assert!(warning.contains(&format!("USB {slow} Mbit/s")), "{warning}");
            assert!(!warning.contains("  "), "{warning}");
        }
        for fast in [5000, 10000, 20000] {
            assert_eq!(super::usb_link_warning(fast), None);
        }
    }
}
