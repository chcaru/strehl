//! Shared desktop/browser controls. The Worker remains the sole camera owner.
use crate::{
    backend::property,
    model::{Phase, Plan, Roi},
    timing,
    worker::{Action, PAUSE, STOP, Snapshot, Worker},
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::VecDeque,
    path::PathBuf,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};

#[derive(Clone, PartialEq)]
pub struct Controls {
    pub revision: u64,
    pub plan: Plan,
    pub start_set: bool,
    pub end_set: bool,
    pub roi: Roi,
    pub root: PathBuf,
    connected_seen: bool,
    connection_generation_seen: u64,
}
impl Controls {
    pub fn new(root: PathBuf) -> Self {
        Self {
            revision: 0,
            plan: Plan::default(),
            start_set: false,
            end_set: false,
            roi: Roi::subject(),
            root,
            connected_seen: false,
            connection_generation_seen: 0,
        }
    }
    pub fn sync_connection(&mut self, snapshot: &Snapshot) {
        if self.connected_seen != snapshot.connected
            || self.connection_generation_seen != snapshot.connection_generation
        {
            self.connected_seen = snapshot.connected;
            self.connection_generation_seen = snapshot.connection_generation;
            self.start_set = false;
            self.end_set = false;
            self.roi = Roi::subject();
            self.revision += 1;
        }
    }
}

pub struct Session {
    pub worker: Arc<Worker>,
    pub controls: Arc<Mutex<Controls>>,
    pub demo: bool,
    pub transfer: Option<crate::transfer::TransferReport>,
    recent: Mutex<VecDeque<String>>,
}
impl Session {
    pub fn new(worker: Arc<Worker>, controls: Arc<Mutex<Controls>>, demo: bool) -> Self {
        Self {
            worker,
            controls,
            demo,
            transfer: None,
            recent: Mutex::new(VecDeque::new()),
        }
    }
    pub fn state(&self) -> Value {
        let mut c = self.controls.lock().unwrap();
        let s = self.worker.snapshot();
        c.sync_connection(&s);
        let editable = s.connected && s.phase.can_edit() && !s.command_pending;
        let fresh = s.preview_error.is_none()
            && s.preview_at
                .is_some_and(|t| t.elapsed() < Duration::from_secs(2));
        let positions = (c.start_set && c.end_set).then(|| c.plan.positions());
        let planned = positions
            .as_ref()
            .and_then(|p| p.as_ref().ok())
            .map(Vec::len);
        let plan_error = positions.and_then(Result::err).map(|e| e.to_string());
        let shots = s.status["pixel_shift_shots"].as_u64().unwrap_or(1);
        let initial = planned.and_then(|n| {
            property(&s.status, "ShutterSpeed")
                .and_then(|speed| timing::initial_cycle(speed, c.plan.settle_ms))
                .map(|cycle| {
                    cycle.mul_f64((n as u64 * shots) as f64)
                        + timing::initial_setup(c.plan.settle_ms)
                })
        });
        let now = Instant::now();
        let timer=s.timing.as_ref().map(|t|json!({"label":t.label(now,s.phase==Phase::Paused),"elapsed":t.elapsed(now).as_secs_f64(),"remaining":t.remaining(now).as_secs_f64(),"finished":t.finished,"paused":s.phase==Phase::Paused}));
        let storage = self
            .transfer
            .as_ref()
            .map(|report| report.lock().unwrap().clone())
            .unwrap_or_else(|| json!({"mode":"camera-sd"}));
        let saved = (s.capture_run && storage["pipelined"] == true).then(|| {
            storage["saved_frames"]
                .as_u64()
                .unwrap_or(0)
                .checked_div(shots)
                .unwrap_or(0)
                .min(s.completed as u64)
        });
        let magnifier = &s.status["properties"]["Focus_Magnifier_Setting"];
        let mut ratios: Vec<u32> = if magnifier["writable"] == true {
            magnifier["allowed"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|v| v.as_u64().map(|n| (n >> 32) as u32))
                .collect()
        } else {
            vec![]
        };
        ratios.sort_unstable();
        ratios.dedup();
        json!({"camera_revision":s.revision,"plan_revision":c.revision,"sequence_id":s.sequence_id,"phase":s.phase,"connected":s.connected,"busy":s.command_pending,"editable":editable,"message":s.message,"demo":self.demo,
            "position":s.position,"plan":c.plan,"start_set":c.start_set,"end_set":c.end_set,"roi":c.roi,"planned":planned,"plan_error":plan_error,"initial_seconds":initial.map(|t|t.as_secs_f64()),
            "completed":s.completed,"saved":saved,"total":s.total,"timer":timer,"pending_control":self.worker.pending(),
            "storage":storage,"shots_per_plane":shots,"camera_model":s.status["model"],
            "failure":s.failure.as_ref().map(|message|json!({"message":message,"exposure_uncertain":s.exposure_uncertain,"can_reconnect":matches!(s.phase,Phase::Fault|Phase::Disconnected)&&!s.command_pending})),
            "battery":property(&s.status,"BatteryRemain").filter(|v|*v<=100),"card_remaining":property(&s.status,"MediaSLOT1_RemainingNumber"),
            "preview":{"available":s.preview.is_some(),"fresh":fresh,"generation":s.preview_generation,"age_seconds":s.preview_at.map(|t|t.elapsed().as_secs_f64()),"error":s.preview_error,"width":s.preview.as_ref().map(|p|p.rgb.width()),"height":s.preview.as_ref().map(|p|p.rgb.height())},
            "magnifier_ratios":ratios,"magnifier_current":property(&s.status,"Focus_Magnifier_Setting").map(|n|n>>32),"suggestion":s.suggestion,"samples":s.samples})
    }
    pub fn dispatch(&self, request: CommandRequest) -> Result<()> {
        ensure!(
            (8..=80).contains(&request.id.len())
                && request
                    .id
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-'),
            "Invalid request identifier"
        );
        let mut c = self.controls.lock().unwrap();
        let mut recent = self.recent.lock().unwrap();
        ensure!(
            !recent.contains(&request.id),
            "Duplicate command ignored; check the current status"
        );
        recent.push_back(request.id);
        if recent.len() > 128 {
            recent.pop_front();
        }
        let s = self.worker.snapshot();
        c.sync_connection(&s);
        if matches!(
            request.command,
            Command::Pause {} | Command::Resume {} | Command::Stop {}
        ) {
            ensure!(
                request.sequence_id == s.sequence_id
                    && matches!(s.phase, Phase::Capturing | Phase::Scanning | Phase::Paused),
                "That sequence is no longer active"
            );
            match request.command {
                Command::Pause {} => {
                    ensure!(self.worker.pending() != STOP, "Stop is already pending");
                    self.worker.request_pause();
                }
                Command::Resume {} => {
                    ensure!(
                        s.phase == Phase::Paused && self.worker.pending() == PAUSE,
                        "The sequence is not paused or is already stopping"
                    );
                    self.worker.request_resume();
                }
                Command::Stop {} => self.worker.request_stop(),
                _ => unreachable!(),
            }
            return Ok(());
        }
        ensure!(
            request.camera_revision == s.revision && request.plan_revision == c.revision,
            "State changed on another controller; review the current values and try again"
        );
        ensure!(
            !s.command_pending && !s.phase.active(),
            "Wait for the active camera operation"
        );
        let mut action = None;
        match request.command {
            Command::Connect {} => {
                ensure!(!s.connected, "Camera is already connected");
                action = Some(Action::Connect);
            }
            Command::Disconnect {} => {
                ensure!(s.connected, "Camera is not connected");
                action = Some(Action::Disconnect);
            }
            Command::Recover {
                acknowledge_uncertain,
            } => {
                action = Some(Action::Recover {
                    acknowledge_uncertain,
                });
            }
            command => {
                ensure!(
                    s.connected && s.phase.can_edit(),
                    "Connect a ready camera first"
                );
                match command {
                    Command::Jog { delta } => {
                        ensure!(
                            [-128, -16, -1, 1, 16, 128].contains(&delta),
                            "Choose one of the supported jog increments"
                        );
                        let position = s.position.context("Camera focus position unavailable")?;
                        let target = u16::try_from(i32::from(position) + delta)
                            .context("Focus move crosses the lens limit")?;
                        action = Some(Action::Move {
                            target,
                            settle_ms: c.plan.settle_ms,
                        });
                    }
                    Command::Mark { start } => {
                        let p = s.position.context("Camera focus position unavailable")?;
                        if start {
                            c.plan.start = p;
                            c.start_set = true;
                        } else {
                            c.plan.end = p;
                            c.end_set = true;
                        }
                    }
                    Command::Go { start } => {
                        ensure!(
                            if start { c.start_set } else { c.end_set },
                            "Mark this boundary first"
                        );
                        let target = if start { c.plan.start } else { c.plan.end };
                        let approach_from = u16::try_from(
                            i32::from(target) - c.plan.direction() * i32::from(c.plan.approach),
                        )
                        .context("Shorten Approach; this mark is too close to the lens limit")?;
                        action = Some(Action::Inspect {
                            target,
                            approach_from,
                            settle_ms: c.plan.settle_ms,
                        });
                    }
                    Command::Settings {
                        step,
                        settle_ms,
                        approach,
                        capture_timeout_s,
                    } => {
                        let mut plan = c.plan.clone();
                        plan.step = step;
                        plan.settle_ms = settle_ms;
                        plan.approach = approach;
                        plan.capture_timeout_s = capture_timeout_s;
                        let mut probe = plan.clone();
                        if !c.start_set || !c.end_set {
                            probe.start = 10000;
                            probe.end = 11000;
                        }
                        probe.validate()?;
                        c.plan = plan;
                    }
                    Command::Roi { roi } => {
                        ensure!(roi.valid(), "Select a valid subject rectangle");
                        c.roi = roi;
                    }
                    Command::Start {} => {
                        ensure!(c.start_set && c.end_set, "Mark both focus bounds first");
                        c.plan.validate()?;
                        self.worker.request_resume();
                        action = Some(Action::Capture {
                            plan: c.plan.clone(),
                            root: c.root.clone(),
                        });
                    }
                    Command::Survey {} => {
                        ensure!(
                            c.start_set && c.end_set && c.plan.start.abs_diff(c.plan.end) >= 8,
                            "Mark wider rough bounds first"
                        );
                        ensure!(
                            s.preview_error.is_none()
                                && s.preview_at
                                    .is_some_and(|t| t.elapsed() < Duration::from_secs(2)),
                            "Survey needs a fresh working preview"
                        );
                        self.worker.request_resume();
                        action = Some(Action::Scan {
                            plan: c.plan.clone(),
                            roi: c.roi,
                        });
                    }
                    Command::ApplyBounds {} => {
                        let suggestion = s.suggestion.context("No suggested bounds yet")?;
                        ensure!(!suggestion.clipped, "Extend rough bounds and survey again");
                        c.plan.start = suggestion.start;
                        c.plan.end = suggestion.end;
                        c.start_set = true;
                        c.end_set = true;
                    }
                    Command::Magnify { ratio, x, y } => {
                        ensure!(
                            ratio <= 1000 && x <= 639 && y <= 479,
                            "Invalid camera magnifier request"
                        );
                        action = Some(Action::Magnify { ratio, x, y });
                    }
                    _ => unreachable!(),
                }
            }
        }
        if let Some(action) = action {
            self.worker.send(s.revision, action)?;
        }
        c.revision += 1;
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandRequest {
    pub id: String,
    pub camera_revision: u64,
    pub plan_revision: u64,
    pub sequence_id: u64,
    pub command: Command,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Command {
    Connect {},
    Disconnect {},
    Recover {
        acknowledge_uncertain: bool,
    },
    Jog {
        delta: i32,
    },
    Mark {
        start: bool,
    },
    Go {
        start: bool,
    },
    Settings {
        step: u16,
        settle_ms: u32,
        approach: u16,
        capture_timeout_s: u32,
    },
    Roi {
        roi: Roi,
    },
    Start {},
    Pause {},
    Resume {},
    Stop {},
    Survey {},
    ApplyBounds {},
    Magnify {
        ratio: u32,
        x: u16,
        y: u16,
    },
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request(session: &Session, id: &str, command: Command) -> CommandRequest {
        let state = session.state();
        CommandRequest {
            id: id.into(),
            camera_revision: state["camera_revision"].as_u64().unwrap(),
            plan_revision: state["plan_revision"].as_u64().unwrap(),
            sequence_id: state["sequence_id"].as_u64().unwrap(),
            command,
        }
    }
    fn until(session: &Session, predicate: impl Fn(&Snapshot) -> bool) -> Snapshot {
        let end = Instant::now() + Duration::from_secs(10);
        loop {
            let s = session.worker.snapshot();
            if predicate(&s) {
                return s;
            }
            assert!(Instant::now() < end, "{:?}: {}", s.phase, s.message);
            std::thread::sleep(Duration::from_millis(10));
        }
    }
    #[test]
    fn two_controllers_cannot_replay_capture_or_overwrite_stale_marks() {
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        session
            .dispatch(request(&session, "connect-01", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        let stale = request(&session, "stale-mark-01", Command::Mark { start: false });
        session
            .dispatch(request(
                &session,
                "mark-start-01",
                Command::Mark { start: true },
            ))
            .unwrap();
        assert!(session.dispatch(stale).is_err());
        let jog = request(&session, "jog-00128", Command::Jog { delta: 128 });
        session.dispatch(jog.clone()).unwrap();
        assert!(session.dispatch(jog).is_err());
        let mut late = request(&session, "double-jog", Command::Jog { delta: 128 });
        assert!(session.dispatch(late.clone()).is_err());
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        session
            .dispatch(request(
                &session,
                "mark-end-01",
                Command::Mark { start: false },
            ))
            .unwrap();
        assert_eq!(session.state()["planned"], 129);
        late.id = "stale-move-02".into();
        assert!(session.dispatch(late).is_err());
        let settings = session.controls.lock().unwrap().plan.clone();
        assert!(
            session
                .dispatch(request(
                    &session,
                    "bad-settings",
                    Command::Settings {
                        step: 0,
                        settle_ms: 100,
                        approach: 128,
                        capture_timeout_s: 120
                    }
                ))
                .is_err()
        );
        assert_eq!(session.controls.lock().unwrap().plan, settings);
        let start = request(&session, "start-run-01", Command::Start {});
        session.dispatch(start.clone()).unwrap();
        assert!(session.dispatch(start).is_err());
        assert!(
            session
                .dispatch(request(&session, "double-start", Command::Start {}))
                .is_err()
        );
        until(&session, |s| s.completed >= 1);
        let mut old_stop = request(&session, "old-stop-01", Command::Stop {});
        old_stop.sequence_id -= 1;
        assert!(session.dispatch(old_stop).is_err());
        session
            .dispatch(request(&session, "pause-run-01", Command::Pause {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Paused);
        let resume = request(&session, "resume-run-01", Command::Resume {});
        session
            .dispatch(request(&session, "stop-run-01", Command::Stop {}))
            .unwrap();
        assert!(session.dispatch(resume).is_err());
        session.worker.request_pause();
        session.worker.request_resume();
        assert_eq!(
            session.worker.pending(),
            STOP,
            "Another controller must not cancel Stop"
        );
        let stopped = until(&session, |s| {
            s.phase == Phase::Stopped && !s.command_pending
        });
        assert!(stopped.completed < 129);
        let journals: Vec<_> = std::fs::read_dir(temp.path()).unwrap().collect();
        assert_eq!(journals.len(), 1, "A duplicate Start created a second run");
        session
            .dispatch(request(&session, "disconnect-01", Command::Disconnect {}))
            .unwrap();
        until(&session, |s| {
            s.phase == Phase::Disconnected && !s.command_pending
        });
        assert_eq!(session.state()["start_set"], false);
        assert_eq!(session.state()["end_set"], false);
    }
    #[test]
    fn no_browser_command_accepts_paths_or_unknown_fields() {
        let envelope = json!({"id":"request-01","camera_revision":0,"plan_revision":0,"sequence_id":0,"command":{"op":"start","root":"C:/remote"}});
        assert!(serde_json::from_value::<CommandRequest>(envelope).is_err());
        let envelope = json!({"id":"request-01","camera_revision":0,"plan_revision":0,"sequence_id":0,"command":{"op":"export","folder":"C:/remote"}});
        assert!(serde_json::from_value::<CommandRequest>(envelope).is_err());
    }
}
