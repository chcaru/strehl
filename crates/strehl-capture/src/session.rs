//! Shared desktop/browser controls. The Worker remains the sole camera owner.
use crate::{
    backend::property,
    model::{Phase, Plan, Roi},
    power::Outlet,
    schedule::{self, Recipe, StackPower, Stage, Store},
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
    pub schedule: Option<Mutex<Store>>,
    recent: Mutex<VecDeque<String>>,
}
impl Session {
    pub fn new(worker: Arc<Worker>, controls: Arc<Mutex<Controls>>, demo: bool) -> Self {
        Self {
            worker,
            controls,
            demo,
            transfer: None,
            schedule: None,
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
                .and_then(|speed| timing::initial_plane(speed, c.plan.settle_ms, shots))
                .map(|cycle| {
                    let warmup = self
                        .worker
                        .power
                        .as_ref()
                        .filter(|_| s.manage_power)
                        .map_or(0, |rig| rig.warmup_seconds());
                    cycle.mul_f64(n as f64)
                        + timing::initial_setup(c.plan.settle_ms)
                        + Duration::from_secs(warmup.into())
                })
        });
        let now = Instant::now();
        let timer=s.timing.as_ref().map(|t|json!({"label":t.label(now,s.phase==Phase::Paused),"elapsed":t.elapsed(now).as_secs_f64(),"remaining":t.remaining(now).as_secs_f64(),"finished":t.finished,"paused":s.phase==Phase::Paused}));
        let storage = self
            .transfer
            .as_ref()
            .map(|report| report.lock().unwrap().clone())
            .unwrap_or_else(|| json!({"mode":"camera-sd"}));
        let storage_required = planned.and_then(|n| {
            crate::capacity::required(n * shots as usize, crate::capacity::raw_limit(&s.status))
                .ok()
        });
        let storage_error = planned.and_then(|n| {
            if storage["mode"] == "host-pc" {
                crate::capacity::check(
                    storage["free_bytes"].as_u64(),
                    n * shots as usize,
                    crate::capacity::raw_limit(&s.status),
                )
                .err()
                .map(|e| e.to_string())
            } else if !self.demo
                && !property(&s.status, "MediaSLOT1_RemainingNumber")
                    .is_some_and(|free| free >= n as u64 * shots)
            {
                Some("The SD card cannot fit this stack".into())
            } else {
                None
            }
        });
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
        let power = self.worker.power.as_ref().map(|rig| {
            let mut p = rig.status();
            let idle = !s.phase.active() && !s.command_pending && !s.exposure_uncertain;
            p["available"] = json!(idle);
            p["can_start_camera"] = json!(idle && !s.connected);
            p["can_stop_camera"] = json!(
                idle && ((s.connected
                    && s.phase.can_edit()
                    && s.identity["hello"]["power_off_protocol"] == 1)
                    || s.standby_at
                        .is_some_and(|t| t.elapsed() < Duration::from_secs(90))
                        && p["camera"]["on"] != false)
            );
            p["can_manage"] = json!(editable && s.identity["hello"]["power_off_protocol"] == 1);
            p["manage_stack"] = json!(s.manage_power);
            p["error"] = json!(s.power_error);
            p
        });
        let schedule = self
            .schedule
            .as_ref()
            .map(|store| store.lock().unwrap().public());
        let mut state = json!({"camera_revision":s.revision,"plan_revision":c.revision,"sequence_id":s.sequence_id,"phase":s.phase,"connected":s.connected,"busy":s.command_pending,"editable":editable,"message":s.message,"demo":self.demo,"power":power,
            "position":s.position,"plan":c.plan,"start_set":c.start_set,"end_set":c.end_set,"roi":c.roi,"planned":planned,"plan_error":plan_error,"initial_seconds":initial.map(|t|t.as_secs_f64()),
            "completed":s.completed,"saved":saved,"total":s.total,"timer":timer,"pending_control":self.worker.pending(),
            "storage":storage,"storage_required_bytes":storage_required,"storage_error":storage_error,"raw_max_bytes":crate::capacity::raw_limit(&s.status),"shots_per_plane":shots,"pixel_shift_options":s.status["pixel_shift_options"],"camera_model":s.status["model"],
            "failure":s.failure.as_ref().map(|message|json!({"message":message,"exposure_uncertain":s.exposure_uncertain,"can_reconnect":matches!(s.phase,Phase::Fault|Phase::Disconnected)&&!s.command_pending})),
            "battery":property(&s.status,"BatteryRemain").filter(|v|*v<=100),"card_remaining":property(&s.status,"MediaSLOT1_RemainingNumber"),
            "preview":{"available":s.preview.is_some(),"fresh":fresh,"generation":s.preview_generation,"age_seconds":s.preview_at.map(|t|t.elapsed().as_secs_f64()),"error":s.preview_error,"width":s.preview.as_ref().map(|p|p.rgb.width()),"height":s.preview.as_ref().map(|p|p.rgb.height())},
            "magnifier_ratios":ratios,"magnifier_current":property(&s.status,"Focus_Magnifier_Setting").map(|n|n>>32),"suggestion":s.suggestion,"samples":s.samples,
            "exposure":exposure_summary(&s.status)});
        // The camera's negotiated USB speed while connected (round-3
        // performance plan, C1); null when unknown or disconnected.
        state["usb_speed_mbps"] = if s.connected {
            s.identity["usb_speed_mbps"].clone()
        } else {
            Value::Null
        };
        state["schedule"] = json!(schedule);
        state["error_correction"] = json!(s.error_correction);
        // What this controller accepts beyond the original protocol. A
        // desktop reads a flag before sending the field it names; an older
        // controller has no `capabilities`, which means none of them.
        state["capabilities"] = json!({
            // `capture_positions` with `kind: "test"` (H2).
            "test_shot": true,
            // `exposure.mode` and `exposure.problem` (H1).
            "exposure_check": true,
        });
        state
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
        recent.push_back(request.id.clone());
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
        if let Command::CancelSchedule { ref id } = request.command {
            let mut store = self
                .schedule
                .as_ref()
                .context("Scheduling unavailable")?
                .lock()
                .unwrap();
            if store
                .job()
                .is_some_and(|job| job.id == *id && job.stage == Stage::Running)
            {
                self.worker.request_stop();
            } else {
                store.cancel(id)?;
            }
            c.revision += 1;
            return Ok(());
        }
        ensure!(
            request.camera_revision == s.revision && request.plan_revision == c.revision,
            "State changed on another controller; review the current values and try again"
        );
        ensure!(
            !self.schedule.as_ref().is_some_and(|store| store
                .lock()
                .unwrap()
                .job()
                .is_some_and(|j| j.stage == Stage::Running)),
            "A scheduled stack is running"
        );
        ensure!(
            !s.command_pending && !s.phase.active(),
            "Wait for the active camera operation"
        );
        let mut action = None;
        match request.command {
            Command::SetWarmup { seconds } => {
                let rig = self
                    .worker
                    .power
                    .as_ref()
                    .context("Studio outlets are not configured")?;
                self.schedule
                    .as_ref()
                    .context("Warmup settings unavailable")?
                    .lock()
                    .unwrap()
                    .set_warmup(seconds)?;
                rig.set_warmup(seconds);
            }
            Command::ScheduleStack {
                start_at,
                power,
                warmup_seconds,
            } => {
                ensure!(
                    s.connected
                        && s.phase.can_edit()
                        && !s.exposure_uncertain
                        && s.failure.is_none()
                        && c.start_set
                        && c.end_set,
                    "Connect the camera and mark both focus bounds before scheduling"
                );
                let rig = self.worker.power.as_deref();
                ensure!(
                    !power.uses_plugs() || rig.is_some(),
                    "Studio outlets are not configured"
                );
                ensure!(
                    !power.camera_off || s.identity["hello"]["power_off_protocol"] == 1,
                    "Camera does not support verified shutdown"
                );
                let warmup =
                    warmup_seconds.unwrap_or_else(|| rig.map_or(0, |r| r.warmup_seconds()));
                ensure!(warmup <= 300, "Choose a light warmup from 0 to 300 seconds");
                let recipe = Recipe::from_live(&c.plan, &s.status, power, warmup)?;
                let raw_count = c.plan.positions()?.len() * recipe.shots;
                if let Some(report) = &self.transfer {
                    crate::capacity::check(
                        report.lock().unwrap()["free_bytes"].as_u64(),
                        raw_count,
                        crate::capacity::raw_limit(&s.status),
                    )?;
                } else if !self.demo {
                    ensure!(
                        property(&s.status, "MediaSLOT1_RemainingNumber")
                            .is_some_and(|n| n >= raw_count as u64),
                        "The card cannot fit the scheduled stack"
                    );
                }
                self.schedule
                    .as_ref()
                    .context("Scheduling unavailable")?
                    .lock()
                    .unwrap()
                    .arm(request.id, start_at, recipe, schedule::now())?;
            }
            Command::Power { device, on } => {
                if device == Outlet::Camera && on {
                    ensure!(!s.connected, "Camera is already connected");
                }
                ensure!(
                    !s.exposure_uncertain,
                    "Recover the uncertain exposure first"
                );
                if device == Outlet::Camera && !on && s.connected {
                    ensure!(
                        s.phase.can_edit() && s.identity["hello"]["power_off_protocol"] == 1,
                        "Reconnect a ready A7CR before shutting it down"
                    );
                }
                action = Some(Action::Power { device, on });
            }
            Command::PowerPlan { enabled } => {
                ensure!(
                    s.connected
                        && s.phase.can_edit()
                        && (!enabled || s.identity["hello"]["power_off_protocol"] == 1),
                    "Connect a camera that supports verified standby first"
                );
                action = Some(Action::PowerPlan(enabled));
            }
            Command::ErrorCorrection { enabled } => {
                ensure!(
                    !s.phase.active() && !s.command_pending,
                    "Change error correction between stacks"
                );
                action = Some(Action::ErrorCorrection(enabled));
            }
            Command::Connect {} => {
                ensure!(!s.connected, "Camera is already connected");
                action = Some(
                    if self
                        .worker
                        .power
                        .as_ref()
                        .is_some_and(|p| p.status()["camera"]["on"] == false)
                    {
                        Action::Power {
                            device: Outlet::Camera,
                            on: true,
                        }
                    } else {
                        Action::Connect
                    },
                );
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
                    Command::Focus { target } => {
                        action = Some(Action::Move {
                            target,
                            settle_ms: 100,
                        });
                    }
                    Command::PixelShift { shots } => {
                        ensure!(
                            matches!(shots, 1 | 4)
                                && s.status["pixel_shift_options"]
                                    .as_array()
                                    .is_some_and(|a| a.contains(&json!(shots))),
                            "This camera does not offer that capture mode"
                        );
                        action = Some(Action::PixelShift {
                            shots: shots as usize,
                        });
                    }
                    Command::Mark { start } => {
                        let p = self.worker.mark_position(s.revision, start)?;
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
                            positions: None,
                            keep_power_on: false,
                            test: false,
                        });
                    }
                    Command::CapturePositions {
                        positions,
                        keep_power_on,
                        kind,
                    } => {
                        ensure!(
                            kind != PositionsKind::Test || positions.len() == 1,
                            "A test shot is one focus position"
                        );
                        // Bursts (one position repeated) and retakes of chosen
                        // planes, with the plan's settle/approach and direction.
                        let mut plan = c.plan.clone();
                        if !c.start_set || !c.end_set {
                            plan.start = positions.first().copied().unwrap_or(0);
                            plan.end = positions.last().copied().unwrap_or(0);
                        }
                        crate::worker::validate_positions(&plan, &positions)?;
                        self.worker.request_resume();
                        action = Some(Action::Capture {
                            plan,
                            root: c.root.clone(),
                            positions: Some(positions),
                            keep_power_on,
                            test: kind == PositionsKind::Test,
                        });
                    }
                    Command::Exposure { iso, shutter } => {
                        for (name, value) in [("IsoSensitivity", iso), ("ShutterSpeed", shutter)] {
                            ensure!(
                                s.status["properties"][name]["allowed"]
                                    .as_array()
                                    .is_some_and(|a| a.contains(&json!(value))),
                                "The camera does not offer that {name} value"
                            );
                        }
                        action = Some(Action::Exposure { iso, shutter });
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

fn exposure_summary(status: &Value) -> Value {
    let props = &status["properties"];
    match property(status, "IsoSensitivity") {
        None => Value::Null,
        Some(iso) => json!({
            "iso": iso,
            "shutter": property(status, "ShutterSpeed"),
            "f_number": property(status, "FNumber"),
            "iso_options": props["IsoSensitivity"]["allowed"],
            "shutter_options": props["ShutterSpeed"]["allowed"],
            "writable": props["IsoSensitivity"]["writable"] == true
                && props["ShutterSpeed"]["writable"] == true,
            // H1 (Studio 2): the program and the reason the settings cannot
            // start a stack, by the rule every capture checks, so a
            // controller can say so before Start.
            "mode": crate::worker::exposure_mode(status),
            "problem": crate::worker::exposure_problem(status),
        }),
    }
}

/// What a `capture_positions` run is for; its manifest's `capture_kind`.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PositionsKind {
    /// A burst or retakes of chosen planes (`capture_kind` "positions").
    #[default]
    Positions,
    /// One exposure to judge the settings (`capture_kind` "test"). A desktop
    /// does not check it while it is written, list it among the stacks or
    /// hand it to the library, and error correction does not hold it.
    Test,
}
impl PositionsKind {
    pub fn is_positions(&self) -> bool {
        *self == Self::Positions
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
    SetWarmup {
        seconds: u32,
    },
    ScheduleStack {
        start_at: u64,
        power: StackPower,
        warmup_seconds: Option<u32>,
    },
    CancelSchedule {
        id: String,
    },
    Power {
        device: Outlet,
        on: bool,
    },
    PowerPlan {
        enabled: bool,
    },
    /// Hold focus after each group until the PC has checked it, and retake
    /// a group that failed for a fault of its exposures in place.
    ErrorCorrection {
        enabled: bool,
    },
    Connect {},
    Disconnect {},
    Recover {
        acknowledge_uncertain: bool,
    },
    Focus {
        target: u16,
    },
    PixelShift {
        shots: u8,
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
    /// Capture the listed focus positions (repeat one for a burst).
    CapturePositions {
        positions: Vec<u16>,
        /// With "manage power" on, still wake the camera and light but leave
        /// them on afterwards: the step calibration's survey is followed by
        /// more camera work. Omitted when false, so older controllers accept
        /// every other request.
        #[serde(default, skip_serializing_if = "std::ops::Not::not")]
        keep_power_on: bool,
        /// What the run is for (H2, Studio 2). Omitted for an ordinary burst
        /// or retake, so older controllers accept those; send `test` only to
        /// a controller whose state has `capabilities.test_shot`.
        #[serde(default, skip_serializing_if = "PositionsKind::is_positions")]
        kind: PositionsKind,
    },
    /// Manual ISO and shutter as the camera's property values.
    Exposure {
        iso: u64,
        shutter: u64,
    },
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
    #[test]
    fn capture_positions_keeps_power_only_when_asked_and_stays_compatible() {
        let old: Command =
            serde_json::from_value(json!({"op":"capture_positions","positions":[1,2]})).unwrap();
        assert!(matches!(
            old,
            Command::CapturePositions {
                keep_power_on: false,
                ..
            }
        ));
        let plain = Command::CapturePositions {
            positions: vec![1],
            keep_power_on: false,
            kind: PositionsKind::Positions,
        };
        assert_eq!(
            serde_json::to_value(&plain).unwrap(),
            json!({"op":"capture_positions","positions":[1]})
        );
        let kept = Command::CapturePositions {
            positions: vec![1],
            keep_power_on: true,
            kind: PositionsKind::Positions,
        };
        assert_eq!(serde_json::to_value(&kept).unwrap()["keep_power_on"], true);
    }
    /// H2: the test kind is additive. Old requests (no `kind`) still parse as
    /// an ordinary burst, an ordinary burst serialises without the field (so
    /// an older controller, whose commands deny unknown fields, accepts it),
    /// and only a test shot names its kind.
    #[test]
    fn capture_positions_kind_is_omitted_unless_a_test_shot() {
        let old: Command =
            serde_json::from_value(json!({"op":"capture_positions","positions":[5]})).unwrap();
        assert!(matches!(
            old,
            Command::CapturePositions {
                kind: PositionsKind::Positions,
                ..
            }
        ));
        let burst = Command::CapturePositions {
            positions: vec![5],
            keep_power_on: false,
            kind: PositionsKind::Positions,
        };
        assert_eq!(
            serde_json::to_value(&burst).unwrap(),
            json!({"op":"capture_positions","positions":[5]})
        );
        let test = Command::CapturePositions {
            positions: vec![5],
            keep_power_on: true,
            kind: PositionsKind::Test,
        };
        assert_eq!(
            serde_json::to_value(&test).unwrap(),
            json!({"op":"capture_positions","positions":[5],"keep_power_on":true,"kind":"test"})
        );
        let parsed: Command =
            serde_json::from_value(json!({"op":"capture_positions","positions":[5],"kind":"test"}))
                .unwrap();
        assert!(matches!(
            parsed,
            Command::CapturePositions {
                kind: PositionsKind::Test,
                ..
            }
        ));
        assert!(
            serde_json::from_value::<Command>(
                json!({"op":"capture_positions","positions":[5],"kind":"stack"})
            )
            .is_err(),
            "an unknown kind is refused, not taken as a burst"
        );
    }
    /// H1 and H2 in state: the capability flags, and the exposure program
    /// with the problem the pre-capture check would raise.
    #[test]
    fn state_reports_capabilities_and_the_exposure_problem_before_start() {
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        let state = session.state();
        assert_eq!(state["capabilities"]["test_shot"], true);
        assert_eq!(state["capabilities"]["exposure_check"], true);
        assert!(state["exposure"].is_null(), "no camera, no exposure");
        session
            .dispatch(request(&session, "connect-h1", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        let state = session.state();
        assert_eq!(state["exposure"]["mode"], "M");
        assert!(state["exposure"]["problem"].is_null());
        let mut status = session.worker.snapshot().status;
        status["properties"]["ExposureProgramMode"]["value"] = json!(3);
        let summary = exposure_summary(&status);
        assert_eq!(summary["mode"], "A");
        assert_eq!(
            summary["problem"],
            "Set the camera to M (manual exposure) before starting a stack"
        );
        status["properties"]["ExposureProgramMode"]["value"] = json!(1);
        status["properties"]["ShutterSpeed"]["value"] = json!(0);
        assert_eq!(
            exposure_summary(&status)["problem"],
            "Choose a timed shutter exposure; Bulb is not supported"
        );
    }
    /// A test shot is one position, journalled as `capture_kind` "test".
    #[test]
    fn a_test_shot_is_one_position_marked_test_in_its_manifest() {
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        session
            .dispatch(request(&session, "connect-h2", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        let two = Command::CapturePositions {
            positions: vec![60600, 60601],
            keep_power_on: true,
            kind: PositionsKind::Test,
        };
        assert!(
            session
                .dispatch(request(&session, "test-two", two))
                .is_err()
        );
        let one = Command::CapturePositions {
            positions: vec![60600],
            keep_power_on: true,
            kind: PositionsKind::Test,
        };
        session
            .dispatch(request(&session, "test-shot-1", one))
            .unwrap();
        let done = until(&session, |s| {
            s.phase == Phase::Complete && !s.command_pending
        });
        assert_eq!(done.completed, 1);
        let manifest: Value = serde_json::from_slice(
            &std::fs::read(done.journal.unwrap().join("manifest.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(manifest["capture_kind"], "test");
        assert_eq!(manifest["focus_positions"], json!([60600]));
    }
    #[test]
    fn absolute_focus_and_mode_selection_refresh_estimates_and_reject_stale_requests() {
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        session
            .dispatch(request(&session, "connect-focus", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        session
            .dispatch(request(
                &session,
                "focus-direct",
                Command::Focus { target: 60500 },
            ))
            .unwrap();
        until(&session, |s| {
            s.phase == Phase::Ready && !s.command_pending && s.position == Some(60500)
        });
        session
            .dispatch(request(
                &session,
                "mark-start",
                Command::Mark { start: true },
            ))
            .unwrap();
        session
            .dispatch(request(
                &session,
                "mark-ending",
                Command::Mark { start: false },
            ))
            .unwrap();
        let before = session.state();
        let stale = request(&session, "old-focus", Command::Focus { target: 61000 });
        session
            .dispatch(request(
                &session,
                "choose-four",
                Command::PixelShift { shots: 4 },
            ))
            .unwrap();
        until(&session, |s| {
            !s.command_pending && s.status["pixel_shift_shots"] == 4
        });
        assert!(session.dispatch(stale).is_err());
        let after = session.state();
        // Four exposures a plane: MEASURED about 2.6 times a single shot's
        // plane at 0.6 s (5.6 s against 2.15 s, `timing::initial_plane`).
        assert!(
            after["initial_seconds"].as_f64().unwrap()
                > 2.0 * before["initial_seconds"].as_f64().unwrap() - 3.0
        );
        assert!(
            after["storage_required_bytes"].as_u64().unwrap()
                > before["storage_required_bytes"].as_u64().unwrap()
        );
        assert_eq!(after["position"], 60500);
        assert!(
            session
                .dispatch(request(
                    &session,
                    "reject-sixteen",
                    Command::PixelShift { shots: 16 }
                ))
                .is_err()
        );
        session
            .dispatch(request(
                &session,
                "choose-single",
                Command::PixelShift { shots: 1 },
            ))
            .unwrap();
        until(&session, |s| {
            !s.command_pending && s.status["pixel_shift_shots"] == 1
        });
        assert_eq!(
            session.state()["initial_seconds"],
            before["initial_seconds"]
        );
    }
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
