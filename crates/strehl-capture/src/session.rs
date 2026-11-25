//! Shared desktop/browser controls. The Worker remains the sole camera owner.
use crate::{
    backend::property,
    model::{LensTravel, Phase, Plan, Roi},
    power::Outlet,
    schedule::{self, Recipe, StackPower, Stage, Store},
    timing,
    worker::{Action, MAX_RETAKES, MAX_RETAKES_LIMIT, PAUSE, STOP, Snapshot, Worker},
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
        // The lens's ends as found (`near`, `far`; null until met).
        state["lens_travel"] = json!(s.lens_travel);
        // A capture's start (light warm-up, approach), while it runs.
        if let Some(starting) = s.starting.as_ref().filter(|_| s.phase.active()) {
            state["starting"] = starting.json();
        }
        // What this controller accepts beyond the original protocol. A
        // desktop reads a flag before sending the field it names; an older
        // controller has no `capabilities`, which means none of them.
        state["capabilities"] = json!({
            // `capture_positions` with `kind: "test"` (H2).
            "test_shot": true,
            // `exposure.mode` and `exposure.problem` (H1).
            "exposure_check": true,
            // `error_correction` with `max_retakes`, and `retakes.max` (h-retake).
            "max_retakes": true,
            // `queue_retakes`, and `retakes.queued`/`retakes.followup` (h-retake).
            "queue_retakes": true,
            // `new_plan`: clear the marks, subject box and survey.
            "new_plan": true,
            // `subject` (plan S1): an outline kept in the plan and manifest.
            "subject": true,
            // Plan X3: `highlight` groups, `shutters` per position and
            // `queue_pass` (impl/tiers.md).
            "exposure_tiers": true,
            // `lens_travel`; a move past an end stops there and the
            // controller stays ready; captures past a known end are refused.
            "lens_travel": true,
        });
        // Retakes (h-retake): the setting, the planes asked for during the
        // capture and not yet taken, and the retakes after it while they run.
        state["retakes"] = json!({
            "max": s.max_retakes,
            "limit": MAX_RETAKES_LIMIT,
            "accepted": s.capture_run && s.retakes_accepted,
            "queued": s.retake_queue,
            "run": s.journal.as_ref().and_then(|d| d.file_name()).and_then(|n| n.to_str()),
            "followup": s.followup.as_ref().map(|f| json!({"planes":f.planes,"taken":f.taken,"skipped":f.skipped})),
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
        if let Command::QueuePass {
            planes,
            tier,
            shutter,
        } = &request.command
        {
            // A pass of another exposure over planes of the capture that has
            // ended (plan X3, R3), into the same run, as retakes after it are.
            ensure!(
                request.sequence_id == s.sequence_id && s.capture_run,
                "That capture is no longer the camera's latest"
            );
            ensure!(
                !s.command_pending && !s.phase.active(),
                "A pass is taken once the capture has ended"
            );
            ensure!(
                (1..=4096).contains(&planes.len()),
                "Choose 1-4096 planes for the pass"
            );
            let total = s.total as u64;
            ensure!(
                planes.iter().all(|p| (1..=total).contains(p)),
                "Choose planes 1-{total}"
            );
            ensure!(
                allowed(&s.status, "ShutterSpeed", *shutter)
                    || s.status["properties"]["ShutterSpeed"].is_null(),
                "The camera does not offer that shutter"
            );
            let tier = crate::worker::Tier::named(tier, *shutter)?;
            self.worker.request_resume();
            self.worker.send(
                s.revision,
                Action::Followup {
                    planes: planes.clone(),
                    pass: Some(crate::worker::Pass { tier }),
                },
            )?;
            c.revision += 1;
            return Ok(());
        }
        if let Command::QueueRetakes { planes } = &request.command {
            // Like Pause and Stop, bound to the capture it names rather than
            // to the latest revision: the state changes with every plane.
            ensure!(
                request.sequence_id == s.sequence_id && s.capture_run,
                "That capture is no longer the camera's latest"
            );
            ensure!(
                (1..=4096).contains(&planes.len()),
                "Choose 1-4096 planes to retake"
            );
            if matches!(s.phase, Phase::Capturing | Phase::Paused) {
                return self.worker.queue_retakes(s.sequence_id, planes);
            }
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
            let total = s.total as u64;
            ensure!(
                planes.iter().all(|p| (1..=total).contains(p)),
                "Choose planes 1-{total}"
            );
            self.worker.request_resume();
            self.worker.send(
                s.revision,
                Action::Followup {
                    planes: planes.clone(),
                    pass: None,
                },
            )?;
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
            Command::ErrorCorrection {
                enabled,
                max_retakes,
            } => {
                ensure!(
                    !s.phase.active() && !s.command_pending,
                    "Change error correction between stacks"
                );
                let max_retakes = usize::from(max_retakes.unwrap_or(MAX_RETAKES as u8));
                ensure!(
                    max_retakes <= MAX_RETAKES_LIMIT,
                    "Choose 0-{MAX_RETAKES_LIMIT} retakes of a plane"
                );
                action = Some(Action::ErrorCorrection {
                    enabled,
                    max_retakes,
                });
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
            Command::NewPlan {} => {
                // With the camera off too: "manage power" turns it off after
                // every capture, and the next one is planned from here.
                ensure!(
                    !s.phase.active() && !s.command_pending,
                    "Start a new plan between stacks"
                );
                c.start_set = false;
                c.end_set = false;
                c.roi = Roi::subject();
                c.plan.subject = None;
                c.plan.highlight = None;
                self.worker.clear_survey();
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
                            target: s.lens_travel.keep_inside(position, target),
                            settle_ms: c.plan.settle_ms,
                        });
                    }
                    Command::Focus { target } => {
                        let target = match s.position {
                            Some(from) => s.lens_travel.keep_inside(from, target),
                            None => target,
                        };
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
                    Command::Highlight { highlight } => {
                        if let Some(h) = &highlight {
                            h.validate()?;
                            ensure!(
                                allowed(&s.status, "ShutterSpeed", h.shutter),
                                "The camera does not offer that shutter"
                            );
                        }
                        c.plan.highlight = highlight;
                    }
                    Command::Subject { subject } => {
                        match &subject {
                            Some(outline) => {
                                outline.validate()?;
                                c.roi = outline.bounding_box();
                            }
                            None => c.roi = Roi::subject(),
                        }
                        c.plan.subject = subject;
                    }
                    Command::Start {} => {
                        ensure!(c.start_set && c.end_set, "Mark both focus bounds first");
                        c.plan.validate()?;
                        within_travel(&s.lens_travel, &c.plan, &c.plan.positions()?)?;
                        self.worker.request_resume();
                        action = Some(Action::Capture {
                            plan: c.plan.clone(),
                            root: c.root.clone(),
                            positions: None,
                            keep_power_on: false,
                            test: false,
                            shutters: None,
                        });
                    }
                    Command::CapturePositions {
                        positions,
                        keep_power_on,
                        kind,
                        shutters,
                    } => {
                        ensure!(
                            kind != PositionsKind::Test || positions.len() == 1,
                            "A test shot is one focus position"
                        );
                        if let Some(shutters) = &shutters {
                            ensure!(
                                shutters.len() == positions.len(),
                                "One shutter for each focus position"
                            );
                            for &shutter in shutters {
                                ensure!(
                                    allowed(&s.status, "ShutterSpeed", shutter),
                                    "The camera does not offer that shutter"
                                );
                            }
                        }
                        // Bursts (one position repeated) and retakes of chosen
                        // planes, with the plan's settle/approach and direction.
                        let mut plan = c.plan.clone();
                        if !c.start_set || !c.end_set {
                            plan.start = positions.first().copied().unwrap_or(0);
                            plan.end = positions.last().copied().unwrap_or(0);
                        }
                        crate::worker::validate_positions(&plan, &positions)?;
                        within_travel(&s.lens_travel, &plan, &positions)?;
                        self.worker.request_resume();
                        action = Some(Action::Capture {
                            plan,
                            root: c.root.clone(),
                            positions: Some(positions),
                            keep_power_on,
                            test: kind == PositionsKind::Test,
                            shutters,
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
        /// Retakes of one plane before it keeps what it has, 0 to
        /// [`crate::worker::MAX_RETAKES_LIMIT`] (h-retake). Omitted: 2, as
        /// before it could be set; send it only to a controller whose state
        /// has `capabilities.max_retakes`.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        max_retakes: Option<u8>,
    },
    /// Take these planes (the numbers their files carry) of the capture
    /// `sequence_id` names again (h-retake): while it runs, between planes
    /// as error correction's retakes are; once it has ended, into the same
    /// run. Send only to a controller whose state has
    /// `capabilities.queue_retakes`.
    QueueRetakes {
        planes: Vec<u64>,
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
        /// A shutter (the camera's property value) per position, for the
        /// Calibrate survey's two exposures (plan X1). Send only to a
        /// controller whose state has `capabilities.exposure_tiers`.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        shutters: Option<Vec<u64>>,
    },
    /// Highlight groups in the plan (plan X3), or `None` for none. Send only
    /// to a controller whose state has `capabilities.exposure_tiers`.
    Highlight {
        highlight: Option<crate::model::Highlight>,
    },
    /// Take these planes of the capture `sequence_id` names again at another
    /// exposure, into the same run, once it has ended (plan X3, R3). Send
    /// only to a controller whose state has `capabilities.exposure_tiers`.
    QueuePass {
        planes: Vec<u64>,
        /// "highlight", "shadow" or "base".
        tier: String,
        shutter: u64,
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
    /// The subject's outline (plan S1), or `None` to clear it. The subject
    /// box becomes its bounding rectangle. Send only to a controller whose
    /// state has `capabilities.subject`.
    Subject {
        subject: Option<crate::model::Subject>,
    },
    /// Start the next capture from nothing: clear the bounds' marks, the
    /// subject box and the survey (the plan's step, settle and approach are
    /// the rig's and stay). Send only to a controller whose state has
    /// `capabilities.new_plan`.
    NewPlan {},
    Magnify {
        ratio: u32,
        x: u16,
        y: u16,
    },
}

/// A capture's positions and its approach move inside the lens's known
/// ends: a plane past one could never be reached, and the capture would
/// stop there.
fn within_travel(travel: &LensTravel, plan: &Plan, positions: &[u16]) -> Result<()> {
    if let Some((p, side, end)) = travel.outside(positions.iter().copied()) {
        anyhow::bail!(
            "Focus {p} is past the lens's {side} end ({end}): move the mark inside the lens's travel"
        );
    }
    if let Some(first) = positions.first()
        && let Ok(from) =
            u16::try_from(i32::from(*first) - plan.direction() * i32::from(plan.approach))
        && let Some((_, side, end)) = travel.outside([from])
    {
        anyhow::bail!(
            "The approach to {first} would start at {from}, past the lens's {side} end ({end}): shorten Approach or move the start mark"
        );
    }
    Ok(())
}

/// Whether the camera offers `value` for property `name` (its `allowed` list).
fn allowed(status: &Value, name: &str, value: u64) -> bool {
    status["properties"][name]["allowed"]
        .as_array()
        .is_some_and(|a| a.contains(&json!(value)))
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
            shutters: None,
        };
        assert_eq!(
            serde_json::to_value(&plain).unwrap(),
            json!({"op":"capture_positions","positions":[1]})
        );
        let kept = Command::CapturePositions {
            positions: vec![1],
            keep_power_on: true,
            kind: PositionsKind::Positions,
            shutters: None,
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
            shutters: None,
        };
        assert_eq!(
            serde_json::to_value(&burst).unwrap(),
            json!({"op":"capture_positions","positions":[5]})
        );
        let test = Command::CapturePositions {
            positions: vec![5],
            keep_power_on: true,
            kind: PositionsKind::Test,
            shutters: None,
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
            shutters: None,
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
            shutters: None,
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
        assert!(manifest["plan"].get("subject").is_none(), "none given");
    }
    /// Plan X3: highlight groups at every second plane are taken after the
    /// base group at the same plane number and focus, at their own shutter,
    /// journalled with `tier` and `exposure`; the camera ends at the base
    /// shutter; the manifest carries the plan.
    #[test]
    fn highlight_groups_and_passes_are_taken_at_their_own_shutter() {
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        assert_eq!(session.state()["capabilities"]["exposure_tiers"], true);
        session
            .dispatch(request(&session, "tiers-connect", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        let state = session.state();
        let base = state["exposure"]["shutter"]
            .as_u64()
            .or_else(|| state["status"]["properties"]["ShutterSpeed"]["value"].as_u64())
            .unwrap_or(65546);
        let short = [393226u64, 65546, 65541]
            .into_iter()
            .find(|v| *v != base)
            .unwrap();
        for (id, command) in [
            ("tiers-focus-a", Command::Focus { target: 60500 }),
            ("tiers-mark-a", Command::Mark { start: true }),
            ("tiers-focus-b", Command::Focus { target: 60503 }),
            ("tiers-mark-b", Command::Mark { start: false }),
        ] {
            session.dispatch(request(&session, id, command)).unwrap();
            until(&session, |s| !s.command_pending);
        }
        let highlight = crate::model::Highlight {
            shutter: short,
            every: 2,
            first_plane: 1,
            last_plane: 4,
            shots: 1,
        };
        session
            .dispatch(request(
                &session,
                "tiers-plan",
                Command::Highlight {
                    highlight: Some(highlight),
                },
            ))
            .unwrap();
        session
            .dispatch(request(&session, "tiers-start", Command::Start {}))
            .unwrap();
        let done = until(&session, |s| {
            s.phase == Phase::Complete && !s.command_pending
        });
        let run = done.journal.unwrap();
        let manifest: Value =
            serde_json::from_slice(&std::fs::read(run.join("manifest.json")).unwrap()).unwrap();
        assert_eq!(manifest["plan"]["highlight"]["every"], 2);
        let events: Vec<Value> = std::fs::read_to_string(run.join("events.jsonl"))
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .collect();
        let groups: Vec<(String, u64, u64, u64)> = events
            .iter()
            .filter(|e| {
                matches!(
                    e["event"].as_str(),
                    Some("capture_buffered" | "capture_complete")
                )
            })
            .map(|e| {
                let d = &e["data"];
                (
                    d["tier"].as_str().unwrap().to_owned(),
                    d["target"].as_u64().unwrap(),
                    d["exposure"]["shutter"].as_u64().unwrap(),
                    d["response"]["files"][0]["plane"].as_u64().unwrap_or(0),
                )
            })
            .collect();
        let tiers: Vec<&str> = groups.iter().map(|g| g.0.as_str()).collect();
        assert_eq!(
            tiers,
            ["base", "highlight", "base", "base", "highlight", "base"],
            "{groups:?}"
        );
        // Each highlight group: its base group's focus and plane number,
        // at the highlight shutter; base groups at the base shutter.
        for pair in [(0, 1), (3, 4)] {
            let (b, h) = (&groups[pair.0], &groups[pair.1]);
            assert_eq!(b.1, h.1, "same focus");
            assert_eq!(b.3, h.3, "same plane number");
            assert_eq!(h.2, short);
            assert_eq!(b.2, base);
        }
        assert!(events.iter().any(|e| e["event"] == "exposure_complete"));
        assert_eq!(
            session.state()["status"]["properties"]["ShutterSpeed"]["value"]
                .as_u64()
                .unwrap_or(base),
            base,
            "the camera ends at the base shutter"
        );
        // A pass of an unknown tier is refused before anything is sent.
        assert!(
            session
                .dispatch(request(
                    &session,
                    "tiers-pass-bad",
                    Command::QueuePass {
                        planes: vec![2],
                        tier: "sideways".into(),
                        shutter: short,
                    }
                ))
                .is_err()
        );
    }
    /// Plan S1: an outline is checked, becomes the subject box's bounding
    /// rectangle, is reported in the plan, and is written into the next
    /// capture's manifest; `None` clears it and `new_plan` forgets it.
    #[test]
    fn a_subject_outline_reaches_the_manifest() {
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        assert_eq!(session.state()["capabilities"]["subject"], true);
        session
            .dispatch(request(&session, "subject-connect", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        let bad = crate::model::Subject {
            rings: vec![vec![[0.1, 0.1], [0.2, 0.1]]],
            ..Default::default()
        };
        assert!(
            session
                .dispatch(request(
                    &session,
                    "subject-bad",
                    Command::Subject { subject: Some(bad) }
                ))
                .is_err()
        );
        let outline = crate::model::Subject {
            rings: vec![vec![[0.30, 0.20], [0.70, 0.25], [0.60, 0.80], [0.35, 0.70]]],
            reference_focus: Some(60600),
            rate_ppm: Some(-13.0),
            provenance: json!({"kind":"manual"}),
        };
        session
            .dispatch(request(
                &session,
                "subject-set",
                Command::Subject {
                    subject: Some(outline.clone()),
                },
            ))
            .unwrap();
        let state = session.state();
        assert_eq!(state["plan"]["subject"]["reference_focus"], 60600);
        let roi = &state["roi"];
        assert!((roi["x"].as_f64().unwrap() - 0.30).abs() < 1e-6);
        assert!((roi["height"].as_f64().unwrap() - 0.60).abs() < 1e-6);
        let one = Command::CapturePositions {
            positions: vec![60600],
            keep_power_on: true,
            kind: PositionsKind::Positions,
            shutters: None,
        };
        session
            .dispatch(request(&session, "subject-capture", one))
            .unwrap();
        let done = until(&session, |s| {
            s.phase == Phase::Complete && !s.command_pending
        });
        let manifest: Value = serde_json::from_slice(
            &std::fs::read(done.journal.unwrap().join("manifest.json")).unwrap(),
        )
        .unwrap();
        let written: crate::model::Subject =
            serde_json::from_value(manifest["plan"]["subject"].clone()).unwrap();
        assert_eq!(written, outline);
        session
            .dispatch(request(&session, "subject-renew", Command::NewPlan {}))
            .unwrap();
        assert!(session.state()["plan"].get("subject").is_none());
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
    /// `new_plan` clears the marks, the subject box and the survey, keeps the
    /// rig's step and settle, works with the camera off, and is announced.
    #[test]
    fn new_plan_clears_marks_box_and_survey_and_keeps_the_rig_settings() {
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        assert_eq!(session.state()["capabilities"]["new_plan"], true);
        session
            .dispatch(request(&session, "newplan-connect", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        for (id, command) in [
            ("newplan-mark-a", Command::Mark { start: true }),
            ("newplan-mark-b", Command::Mark { start: false }),
            (
                "newplan-roi",
                Command::Roi {
                    roi: Roi {
                        x: 0.1,
                        y: 0.2,
                        width: 0.3,
                        height: 0.4,
                    },
                },
            ),
            (
                "newplan-settings",
                Command::Settings {
                    step: 9,
                    settle_ms: 1500,
                    approach: 120,
                    capture_timeout_s: 30,
                },
            ),
        ] {
            session.dispatch(request(&session, id, command)).unwrap();
        }
        session
            .worker
            .set_suggestion(Some(crate::bounds::Suggestion {
                start: 1,
                end: 2,
                supported_tiles: 3,
                clipped: false,
                explanation: String::new(),
            }));
        let before = session.state();
        assert!(before["start_set"] == true && before["end_set"] == true);
        assert!(!before["suggestion"].is_null());
        session
            .dispatch(request(&session, "newplan-clear", Command::NewPlan {}))
            .unwrap();
        let after = session.state();
        assert_eq!(after["start_set"], false);
        assert_eq!(after["end_set"], false);
        assert!(after["suggestion"].is_null());
        assert_eq!(after["samples"], json!([]));
        assert_eq!(after["roi"], json!(Roi::subject()));
        assert_eq!(after["plan"]["step"], 9);
        assert_eq!(after["plan"]["settle_ms"], 1500);
        // The request is a bare op, so it parses as sent.
        assert_eq!(
            serde_json::to_value(Command::NewPlan {}).unwrap(),
            json!({"op":"new_plan"})
        );
    }
    /// h-retake: an older desktop's `error_correction` (no `max_retakes`)
    /// still parses and sets the old two; a newer one's is bounded; the
    /// request serialises without the field unless it is set.
    #[test]
    fn max_retakes_is_optional_bounded_and_reported() {
        let old: Command =
            serde_json::from_value(json!({"op":"error_correction","enabled":true})).unwrap();
        assert!(matches!(
            old,
            Command::ErrorCorrection {
                enabled: true,
                max_retakes: None
            }
        ));
        assert_eq!(
            serde_json::to_value(Command::ErrorCorrection {
                enabled: false,
                max_retakes: None
            })
            .unwrap(),
            json!({"op":"error_correction","enabled":false})
        );
        let temp = tempfile::tempdir().unwrap();
        let session = Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        let state = session.state();
        assert_eq!(state["capabilities"]["max_retakes"], true);
        assert_eq!(state["capabilities"]["queue_retakes"], true);
        assert_eq!(state["retakes"]["max"], 2);
        assert_eq!(state["retakes"]["limit"], 5);
        assert_eq!(state["retakes"]["queued"], json!([]));
        assert!(state["retakes"]["followup"].is_null());
        let set = |id: &str, max: Option<u8>| {
            session.dispatch(request(
                &session,
                id,
                Command::ErrorCorrection {
                    enabled: true,
                    max_retakes: max,
                },
            ))
        };
        set("ec-max-four", Some(4)).unwrap();
        until(&session, |s| s.max_retakes == 4 && !s.command_pending);
        assert!(set("ec-max-six", Some(6)).is_err());
        set("ec-max-zero", Some(0)).unwrap();
        until(&session, |s| s.max_retakes == 0 && !s.command_pending);
        // An older desktop's request: back to two.
        set("ec-older-desk", None).unwrap();
        let s = until(&session, |s| s.max_retakes == 2 && !s.command_pending);
        assert!(s.error_correction);
        assert_eq!(session.state()["retakes"]["max"], 2);
    }
    /// h-retake, end to end on the simulated PC camera through the
    /// controller: a retake queued while the capture is paused is taken when
    /// it resumes; after the capture another is taken into the same run;
    /// a request naming another capture is refused.
    #[test]
    fn retakes_are_queued_during_and_after_a_capture() {
        use crate::backend::sim::{Fail, PcSim};
        let temp = tempfile::tempdir().unwrap();
        let worker = Worker::with_factory(Box::new(|| {
            let mut sim = PcSim::new(vec![((1, 1), Fail::Kept), ((3, 1), Fail::Kept)]);
            sim.demo.delay_ms = 40;
            Ok(Box::new(sim) as Box<dyn crate::backend::Camera>)
        }));
        let session = Session::new(
            Arc::new(worker),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            false,
        );
        session
            .dispatch(request(&session, "connect-rt", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        session
            .dispatch(request(
                &session,
                "ec-on-rt",
                Command::ErrorCorrection {
                    enabled: true,
                    max_retakes: Some(1),
                },
            ))
            .unwrap();
        until(&session, |s| s.error_correction && !s.command_pending);
        for (id, command) in [
            ("focus-rt-a", Command::Focus { target: 60500 }),
            ("mark-rt-a", Command::Mark { start: true }),
            ("focus-rt-b", Command::Focus { target: 60505 }),
            ("mark-rt-b", Command::Mark { start: false }),
        ] {
            session.dispatch(request(&session, id, command)).unwrap();
            until(&session, |s| !s.command_pending && s.phase == Phase::Ready);
        }
        session
            .dispatch(request(&session, "start-rt-01", Command::Start {}))
            .unwrap();
        until(&session, |s| s.completed >= 2);
        session
            .dispatch(request(&session, "pause-rt-01", Command::Pause {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Paused);
        let queue = |id: &str, planes: Vec<u64>| {
            session.dispatch(request(&session, id, Command::QueueRetakes { planes }))
        };
        assert!(queue("queue-rt-bad", vec![99]).is_err(), "beyond the stack");
        queue("queue-rt-mid", vec![1]).unwrap();
        queue("queue-rt-twice", vec![1]).unwrap();
        assert_eq!(session.state()["retakes"]["queued"], json!([1]));
        let mut stale = request(
            &session,
            "queue-rt-old",
            Command::QueueRetakes { planes: vec![1] },
        );
        stale.sequence_id -= 1;
        assert!(session.dispatch(stale).is_err(), "another capture's");
        session
            .dispatch(request(&session, "resume-rt-01", Command::Resume {}))
            .unwrap();
        let done = until(&session, |s| {
            s.phase == Phase::Complete && !s.command_pending
        });
        let journal = done.journal.clone().unwrap();
        let events = || std::fs::read_to_string(journal.join("events.jsonl")).unwrap();
        let manual = |text: &str| {
            text.lines()
                .filter(|l| l.contains("\"retake_intent\"") && l.contains("\"manual\":true"))
                .count()
        };
        assert_eq!(manual(&events()), 1);
        assert_eq!(session.state()["retakes"]["accepted"], true);
        // After the capture: plane 3, into the same run.
        queue("queue-rt-after", vec![3]).unwrap();
        // Pending from the request until the retakes have ended.
        let s = until(&session, |s| {
            s.phase == Phase::Complete && !s.command_pending && s.followup.is_none()
        });
        assert_eq!(s.sequence_id, done.sequence_id, "the same capture");
        let text = events();
        assert_eq!(manual(&text), 2);
        assert!(text.contains("\"followup_finished\""));
        assert_eq!(std::fs::read_dir(temp.path()).unwrap().count(), 1);
        // A newer sequence (a survey) is not that capture any more.
        let mut old = request(
            &session,
            "queue-rt-late",
            Command::QueueRetakes { planes: vec![3] },
        );
        old.sequence_id += 1;
        assert!(session.dispatch(old).is_err());
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
    /// Owner, 2026-11-24: the rail offered focus past the lens's end, and a
    /// move there faulted the controller. The end is found and kept; a
    /// click past it from inside stops at it, and a capture past it is
    /// refused before anything moves.
    #[test]
    fn moves_and_captures_keep_to_the_lens_ends() {
        let temp = tempfile::tempdir().unwrap();
        let worker = Worker::with_factory(Box::new(|| {
            Ok(Box::new(crate::backend::Demo {
                delay_ms: 0,
                travel: (1509, 63487),
                ..crate::backend::Demo::default()
            }))
        }));
        let session = Session::new(
            Arc::new(worker),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        );
        session
            .dispatch(request(&session, "connect-01", Command::Connect {}))
            .unwrap();
        until(&session, |s| s.phase == Phase::Ready && !s.command_pending);
        assert_eq!(session.state()["capabilities"]["lens_travel"], true);
        assert_eq!(session.state()["lens_travel"]["far"], Value::Null);
        let go = |id: &str, command: Command| {
            session.dispatch(request(&session, id, command)).unwrap();
            until(&session, |s| s.phase == Phase::Ready && !s.command_pending)
        };
        go("focus-63400", Command::Focus { target: 63400 });
        let s = go("jog-up-0128", Command::Jog { delta: 128 });
        assert_eq!(s.position, Some(63487));
        assert_eq!(session.state()["lens_travel"]["far"], 63487);
        go("focus-61000", Command::Focus { target: 61000 });
        let s = go("focus-65000", Command::Focus { target: 65000 });
        assert_eq!(s.position, Some(63487));
        assert_eq!(
            s.message, "Focus settled",
            "kept at the end, not sent past it"
        );
        go("focus-63400-b", Command::Focus { target: 63400 });
        let s = go("jog-up-0128-b", Command::Jog { delta: 128 });
        assert_eq!(s.position, Some(63487));
        assert_eq!(s.message, "Focus settled", "a jog is kept at the end too");
        let refused = session.dispatch(request(
            &session,
            "survey-past-end",
            Command::CapturePositions {
                positions: vec![63400, 63500],
                keep_power_on: false,
                kind: PositionsKind::Positions,
                shutters: None,
            },
        ));
        let why = format!("{:#}", refused.unwrap_err());
        assert!(why.contains("past the lens's far end (63487)"), "{why}");
        assert_eq!(session.worker.snapshot().phase, Phase::Ready);
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
