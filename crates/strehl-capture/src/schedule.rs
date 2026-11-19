//! One saved focus stack. A durable claim precedes every scheduled shutter.
use crate::{
    backend::property,
    model::{Phase, Plan},
    receiver::save_json,
    session::Session,
    worker::Action,
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    io::ErrorKind,
    path::PathBuf,
    sync::{Arc, Mutex, mpsc},
    thread,
    time::Duration,
};

#[derive(Clone, Copy, Debug, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct StackPower {
    pub wake_camera: bool,
    pub light_on: bool,
    pub light_off: bool,
    pub camera_off: bool,
}
impl StackPower {
    pub fn managed() -> Self {
        Self {
            wake_camera: true,
            light_on: true,
            light_off: true,
            camera_off: true,
        }
    }
    pub fn uses_plugs(self) -> bool {
        self != Self::default()
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Recipe {
    pub plan: Plan,
    pub model: String,
    pub shots: usize,
    pub iso: u64,
    pub shutter: u64,
    pub aperture: u64,
    pub power: StackPower,
    pub warmup_seconds: u32,
}
impl Recipe {
    pub fn from_live(
        plan: &Plan,
        status: &Value,
        power: StackPower,
        warmup_seconds: u32,
    ) -> Result<Self> {
        plan.validate()?;
        Ok(Self {
            plan: plan.clone(),
            model: status["model"]
                .as_str()
                .context("Camera model unavailable")?
                .into(),
            shots: status["pixel_shift_shots"].as_u64().unwrap_or(1) as usize,
            iso: property(status, "IsoSensitivity").context("ISO unavailable")?,
            shutter: property(status, "ShutterSpeed").context("Shutter speed unavailable")?,
            aperture: property(status, "FNumber").context("Aperture unavailable")?,
            power,
            warmup_seconds,
        })
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Stage {
    Armed,
    Running,
    Complete,
    Cancelled,
    Stopped,
    Failed,
    Missed,
    Interrupted,
}
impl Stage {
    pub fn active(self) -> bool {
        matches!(self, Self::Armed | Self::Running)
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Job {
    pub id: String,
    pub start_at: u64,
    pub stage: Stage,
    pub message: String,
    pub recipe: Recipe,
}
#[derive(Clone, Serialize, Deserialize)]
struct Settings {
    warmup_seconds: u32,
    job: Option<Job>,
}
pub struct Store {
    path: PathBuf,
    settings: Settings,
    pub error: Option<String>,
    pending_result: Option<(Stage, String)>,
}
pub fn now() -> u64 {
    (crate::journal::now_ms() / 1000) as u64
}
impl Store {
    pub fn open(path: PathBuf, default_warmup: u32, now: u64) -> Result<Self> {
        let settings: Settings = match std::fs::read(&path) {
            Ok(bytes) => serde_json::from_slice(&bytes).context("Read saved studio schedule")?,
            Err(e) if e.kind() == ErrorKind::NotFound => Settings {
                warmup_seconds: default_warmup,
                job: None,
            },
            Err(e) => return Err(e.into()),
        };
        ensure!(settings.warmup_seconds <= 300, "Invalid saved light warmup");
        let mut store = Self {
            path,
            settings,
            error: None,
            pending_result: None,
        };
        if let Some(job) = store.job() {
            match job.stage {
                Stage::Running => store.finish(Stage::Interrupted,"Pi restarted during the scheduled stack. Inspect the capture before scheduling another.")?,
                Stage::Armed if job.start_at<=now => store.finish(Stage::Missed,"Pi was offline at the start time.")?,
                _ => (),
            }
        }
        Ok(store)
    }
    pub fn warmup(&self) -> u32 {
        self.settings.warmup_seconds
    }
    pub fn job(&self) -> Option<&Job> {
        self.settings.job.as_ref()
    }
    pub fn public(&self) -> Value {
        json!({"job":self.job(),"error":self.error})
    }
    fn save(&mut self, settings: Settings) -> Result<()> {
        save_json(&self.path, &settings).context("Save studio schedule to the Pi")?;
        self.settings = settings;
        self.error = None;
        Ok(())
    }
    pub fn set_warmup(&mut self, seconds: u32) -> Result<()> {
        ensure!(
            seconds <= 300,
            "Choose a light warmup from 0 to 300 seconds"
        );
        self.save(Settings {
            warmup_seconds: seconds,
            ..self.settings.clone()
        })
    }
    pub fn arm(&mut self, id: String, start_at: u64, recipe: Recipe, now: u64) -> Result<()> {
        ensure!(
            !self.job().is_some_and(|j| j.stage.active()),
            "Cancel the existing schedule first"
        );
        ensure!(start_at > now, "Choose a future local date and time");
        let job = Job {
            id,
            start_at,
            stage: Stage::Armed,
            message: "Waiting for the scheduled start".into(),
            recipe,
        };
        self.save(Settings {
            job: Some(job),
            ..self.settings.clone()
        })
    }
    pub fn cancel(&mut self, id: &str) -> Result<()> {
        ensure!(
            self.job()
                .is_some_and(|j| j.id == id && j.stage == Stage::Armed),
            "That schedule is no longer waiting"
        );
        self.finish(Stage::Cancelled, "Schedule cancelled before start")
    }
    fn finish(&mut self, stage: Stage, message: &str) -> Result<()> {
        let mut settings = self.settings.clone();
        let job = settings.job.as_mut().context("No scheduled stack")?;
        job.stage = stage;
        job.message = message.to_owned();
        self.save(settings)
    }
    fn flush_result(&mut self) -> Result<()> {
        if let Some((stage, message)) = self.pending_result.clone() {
            self.finish(stage, &message)?;
            self.pending_result = None;
        }
        Ok(())
    }
}

pub fn start_clock(session: &Arc<Session>) -> Result<()> {
    let weak = Arc::downgrade(session);
    thread::Builder::new()
        .name("capture-schedule".into())
        .spawn(move || {
            while let Some(session) = weak.upgrade() {
                if let Err(e) = tick(&session, now()) {
                    let error = format!("{e:#}");
                    if let Some(store) = &session.schedule {
                        store.lock().unwrap().error = Some(error);
                    }
                }
                drop(session);
                thread::sleep(Duration::from_millis(250));
            }
        })?;
    Ok(())
}

fn tick(session: &Session, now: u64) -> Result<()> {
    let Some(store) = &session.schedule else {
        return Ok(());
    };
    let rx = {
        // Same lock order as state/dispatch. Cancel and the durable claim cannot cross.
        let mut controls = session.controls.lock().unwrap();
        let mut store = store.lock().unwrap();
        if store.pending_result.is_some() {
            store.flush_result()?;
            controls.revision += 1;
            return Ok(());
        }
        let Some(job) = store
            .job()
            .filter(|j| j.stage == Stage::Armed && now >= j.start_at)
        else {
            return Ok(());
        };
        let s = session.worker.snapshot();
        if s.command_pending
            || s.phase.active()
            || s.failure.is_some()
            || s.exposure_uncertain
            || now - job.start_at > 60
        {
            store.finish(Stage::Missed,"Start time passed or the camera was busy or needed recovery at the scheduled time.")?;
            controls.revision += 1;
            return Ok(());
        }
        let recipe = job.recipe.clone();
        let (tx, rx) = mpsc::channel();
        store.finish(Stage::Running, "Starting the saved stack")?;
        controls.revision += 1;
        if let Err(e) = session.worker.send(
            s.revision,
            Action::Scheduled {
                recipe: Box::new(recipe),
                root: controls.root.clone(),
                reply: tx,
            },
        ) {
            store.pending_result = Some((Stage::Failed, format!("{e:#}")));
            return store.flush_result();
        }
        rx
    };
    // Other controllers can read status and request a stop while the owner works.
    let (stage, message) = match rx.recv() {
        Ok(Ok(Phase::Complete)) => (Stage::Complete, "Stack saved".to_owned()),
        Ok(Ok(Phase::Stopped)) => (Stage::Stopped, "Stack stopped".to_owned()),
        Ok(Err(e)) => (Stage::Failed, e),
        _ => (
            Stage::Interrupted,
            "Camera worker ended before confirming the result".to_owned(),
        ),
    };
    let mut controls = session.controls.lock().unwrap();
    let mut store = store.lock().unwrap();
    store.pending_result = Some((stage, message));
    store.flush_result()?;
    controls.revision += 1;
    Ok(())
}

pub fn store(path: PathBuf, warmup: u32) -> Result<Mutex<Store>> {
    Ok(Mutex::new(Store::open(path, warmup, now())?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        backend::{Camera, Demo},
        session::Controls,
        worker::Worker,
    };
    fn recipe() -> Recipe {
        let plan = Plan {
            start: 30000,
            end: 30001,
            ..Default::default()
        };
        Recipe::from_live(
            &plan,
            &Demo::default().status().unwrap(),
            StackPower::default(),
            5,
        )
        .unwrap()
    }
    #[test]
    fn cancellation_restart_and_claim_never_replay_a_shutter() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("schedule.json");
        let load = |now| Store::open(path.clone(), 5, now).unwrap();
        let mut s = load(100);
        assert!(s.arm("past".into(), 100, recipe(), 100).is_err());
        assert!(s.set_warmup(301).is_err());
        s.set_warmup(0).unwrap();
        s.arm("first".into(), 110, recipe(), 100).unwrap();
        assert!(s.arm("duplicate".into(), 120, recipe(), 100).is_err());
        assert!(s.cancel("stale").is_err());
        let mut s = load(101);
        assert_eq!(s.job().unwrap().stage, Stage::Armed);
        assert_eq!(s.warmup(), 0);
        s.cancel("first").unwrap();
        assert_eq!(load(115).job().unwrap().stage, Stage::Cancelled);
        s.arm("next".into(), 130, recipe(), 115).unwrap();
        let mut s = load(131);
        assert_eq!(s.job().unwrap().stage, Stage::Missed);
        s.arm("claimed".into(), 160, recipe(), 131).unwrap();
        s.finish(Stage::Running, "Claimed").unwrap();
        assert_eq!(load(159).job().unwrap().stage, Stage::Interrupted);
    }
    #[test]
    fn clock_uses_saved_bounds_and_mode_once_after_reopening() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("settings/schedule.json");
        let root = tmp.path().join("runs");
        let mut store = Store::open(path.clone(), 5, 100).unwrap();
        let mut saved = recipe();
        saved.shots = 4;
        store.arm("verify-shot".into(), 110, saved, 100).unwrap();
        let mut session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(root.clone()))),
            true,
        );
        session.schedule = Some(Mutex::new(Store::open(path, 5, 109).unwrap()));
        tick(&session, 109).unwrap();
        assert!(!root.exists());
        tick(&session, 110).unwrap();
        assert_eq!(session.state()["schedule"]["job"]["stage"], "complete");
        tick(&session, 111).unwrap();
        let runs: Vec<_> = std::fs::read_dir(root)
            .unwrap()
            .map(|p| p.unwrap().path())
            .collect();
        assert_eq!(runs.len(), 1);
        let manifest: Value =
            serde_json::from_slice(&std::fs::read(runs[0].join("manifest.json")).unwrap()).unwrap();
        assert_eq!(manifest["focus_positions"], json!([30000, 30001]));
        assert_eq!(manifest["planned_raws"], 8);
        assert!(!session.state()["start_set"].as_bool().unwrap());
    }
}
