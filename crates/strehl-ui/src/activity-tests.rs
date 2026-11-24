//! The activity model: the registry's frame cycle and history, Quiet mode's
//! cadence, and the adapters for crate-level owners.
use super::*;
use crate::capture_workspace::tools::{Calibration, Slot};
use std::sync::atomic::{AtomicUsize, Ordering};

fn running(key: &str, lane: Lane) -> ActivityStatus {
    ActivityStatus::new(ActivityKind::Stack, key, format!("Stack · {key}"), lane)
}

#[test]
fn ids_are_stable_per_kind_and_key() {
    assert_eq!(
        activity_id(ActivityKind::Stack, "a"),
        activity_id(ActivityKind::Stack, "a")
    );
    assert_ne!(
        activity_id(ActivityKind::Stack, "a"),
        activity_id(ActivityKind::Export, "a")
    );
    assert_ne!(
        activity_id(ActivityKind::Stack, "a"),
        activity_id(ActivityKind::Stack, "b")
    );
}

#[test]
fn the_registry_reports_a_frame_and_changes_revision_only_on_change() {
    let mut activities = Activities::default();
    let now = Instant::now();
    activities.begin();
    activities.report(running("one", Lane::Heavy).with_progress(Some(1), Some(10)));
    activities.report(running("two", Lane::Background));
    activities.end(now, 1_000);
    let first = activities.revision();
    assert_eq!(activities.statuses().len(), 2);
    assert!(activities.heavy_busy());
    assert_eq!(activities.running().count(), 2);
    // An identical frame changes nothing.
    activities.begin();
    activities.report(running("one", Lane::Heavy).with_progress(Some(1), Some(10)));
    activities.report(running("two", Lane::Background));
    activities.end(now, 1_000);
    assert_eq!(activities.revision(), first);
    // Progress changes the revision; a frame without reports empties the list.
    activities.begin();
    activities.report(running("one", Lane::Heavy).with_progress(Some(2), Some(10)));
    activities.end(now, 1_001);
    assert_ne!(activities.revision(), first);
    assert_eq!(activities.statuses().len(), 1);
    assert!(
        activities.history().is_empty(),
        "running work is not history"
    );
    activities.begin();
    activities.end(now, 1_002);
    assert!(activities.statuses().is_empty());
    assert!(!activities.heavy_busy());
}

#[test]
fn a_terminal_state_kept_on_screen_is_recorded_once_and_history_is_bounded() {
    let mut activities = Activities::default();
    let started = Instant::now();
    let done = |summary: &str| {
        let mut status = running("export", Lane::Background).with_state(ActivityState::Done {
            summary: summary.into(),
            next: Some(ActionId::Reveal {
                path: PathBuf::from("out.png"),
            }),
        });
        status.started = Some(started);
        status
    };
    for _ in 0..30 {
        activities.begin();
        activities.report(done("Exported out.png"));
        activities.end(started + Duration::from_secs(5), 2_000);
    }
    assert_eq!(activities.history().len(), 1);
    let entry = &activities.history()[0];
    assert_eq!(
        (entry.outcome.as_str(), entry.summary.as_str()),
        ("done", "Exported out.png")
    );
    assert_eq!(entry.took_seconds, Some(5.0));
    assert_eq!(
        entry.action,
        Some(ActionId::Reveal {
            path: PathBuf::from("out.png")
        })
    );
    // The same owner finishing again with another result is a new entry.
    activities.begin();
    activities.report(done("Exported other.png"));
    activities.end(started, 2_001);
    assert_eq!(activities.history().len(), 2);
    assert_eq!(activities.history()[0].summary, "Exported other.png");
    for n in 0..(MAX_HISTORY + 20) {
        activities.record(HistoryEntry {
            kind: ActivityKind::Export,
            title: format!("Export {n}"),
            stack: None,
            outcome: "done".into(),
            summary: String::new(),
            finished: 3_000 + n as u64,
            took_seconds: None,
            action: None,
            log: None,
        });
    }
    assert_eq!(activities.history().len(), MAX_HISTORY);
    assert_eq!(
        activities.history()[0].title,
        format!("Export {}", MAX_HISTORY + 19)
    );
}

#[test]
fn the_public_value_carries_each_states_obligation() {
    let mut activities = Activities::default();
    let now = Instant::now();
    activities.begin();
    activities.report(
        running("waiting", Lane::Heavy).with_state(ActivityState::Waiting {
            for_what: "the stack before it".into(),
            gives_up: Some(now + Duration::from_secs(30)),
        }),
    );
    activities.report(
        running("failed", Lane::Heavy).with_state(ActivityState::NeedsYou {
            message: "Out of memory".into(),
            action: Some(ActionId::Retry { stack: 4 }),
        }),
    );
    activities.end(now, 10);
    let value = activities.public(now, 16);
    assert_eq!(value["current"][0]["state"], "waiting");
    assert_eq!(value["current"][0]["waiting_for"], "the stack before it");
    assert_eq!(value["current"][0]["gives_up_seconds"], 30.0);
    assert_eq!(value["current"][1]["state"], "needs_you");
    assert_eq!(value["current"][1]["action"]["action"], "retry");
    assert_eq!(value["history"][0]["outcome"], "needs_you");
    assert_eq!(value["history_total"], 1);
}

static PROBES: AtomicUsize = AtomicUsize::new(0);
fn busy_probe() -> bool {
    PROBES.fetch_add(1, Ordering::SeqCst);
    true
}

#[test]
fn quiet_mode_reads_the_foreground_on_a_timer_and_only_while_on() {
    let mut quiet = QuietMode::with_probe(busy_probe);
    let start = Instant::now();
    let before = PROBES.load(Ordering::SeqCst);
    for frame in 0..120 {
        // Two seconds of 60 Hz frames probe once.
        assert!(quiet.holds(start + Duration::from_millis(frame * 16)));
    }
    assert_eq!(PROBES.load(Ordering::SeqCst) - before, 1);
    quiet.holds(start + QUIET_POLL);
    assert_eq!(PROBES.load(Ordering::SeqCst) - before, 2);
    assert!(quiet.full_screen());
    assert!(quiet.reason().unwrap().contains("full-screen"));
    // Off: no hold and no reading of the foreground.
    let mut off = QuietMode::with_probe(busy_probe);
    off.enabled = false;
    let probes = PROBES.load(Ordering::SeqCst);
    assert!(!off.holds(start + Duration::from_secs(60)));
    assert_eq!(PROBES.load(Ordering::SeqCst), probes);
    assert_eq!(off.reason(), None);
    let mut idle = QuietMode::with_probe(|| false);
    assert!(!idle.holds(start), "nothing in front, nothing held");
    // The real probe answers without failing on this machine.
    let _ = full_screen_in_front();
}

#[test]
fn engine_tool_slots_report_running_and_their_kept_results() {
    let folder = PathBuf::from("captures/bug-9/100MSDCF");
    let mut slot = Slot {
        folder: Some(folder),
        ..Slot::default()
    };
    assert!(tool_status(ActivityKind::FocusStep, &Slot::default(), Lane::Background).is_none());
    assert!(
        tool_status(ActivityKind::FocusStep, &slot, Lane::Background).is_none(),
        "nothing ran yet"
    );
    slot.result = Some(Ok(serde_json::json!({"summary": "Step 7 suggested"})));
    let status = tool_status(ActivityKind::FocusStep, &slot, Lane::Background).unwrap();
    assert_eq!(status.title, "Measure focus step · 100MSDCF");
    assert_eq!(
        status.state,
        ActivityState::Done {
            summary: "Step 7 suggested".into(),
            next: None
        }
    );
    slot.result = Some(Err(crate::capture_workspace::tools::CANCELLED.into()));
    assert!(matches!(
        tool_status(ActivityKind::FocusStep, &slot, Lane::Background)
            .unwrap()
            .state,
        ActivityState::Stopped { .. }
    ));
    slot.result = Some(Err("The engine failed".into()));
    assert!(matches!(
        tool_status(ActivityKind::CompactApply, &slot, Lane::Heavy)
            .unwrap()
            .state,
        ActivityState::NeedsYou { .. }
    ));
    #[cfg(windows)]
    {
        slot.job = Some(
            crate::capture_workspace::tools::EngineJob::start(
                std::path::Path::new("cmd"),
                vec!["/c".into(), "ping -n 6 127.0.0.1 >nul & rem".into()],
            )
            .unwrap(),
        );
        let status = tool_status(ActivityKind::FocusStep, &slot, Lane::Background).unwrap();
        assert_eq!(status.state, ActivityState::Running);
        assert_eq!(status.cancel, CancelMode::Kill);
        let compaction = tool_status(ActivityKind::CompactApply, &slot, Lane::Heavy).unwrap();
        assert_eq!(
            (compaction.cancel, compaction.lane),
            (CancelMode::None, Lane::Heavy),
            "compaction runs to its end"
        );
        assert!(status.started.is_some());
        slot.cancel();
    }
}

#[test]
fn calibration_stages_wait_with_their_deadlines_and_end_as_done_or_needs_you() {
    let now = Instant::now();
    assert!(calibration_status(&Calibration::Idle, "c").is_none());
    let switching = Calibration::Switching {
        restore_four: true,
        positions: vec![1, 2],
        round: 0,
        deadline: now + Duration::from_secs(45),
        shutters: None,
    };
    let status = calibration_status(&switching, "c").unwrap();
    assert_eq!(status.lane, Lane::Camera);
    assert_eq!(status.cancel, CancelMode::Cooperative);
    match status.state {
        ActivityState::Waiting { for_what, gives_up } => {
            assert!(for_what.contains("one RAW a plane"));
            assert_eq!(gives_up, Some(now + Duration::from_secs(45)));
        }
        other => panic!("{other:?}"),
    }
    let done = Calibration::Done(serde_json::json!({"summary": "Step 7 suggested"}));
    assert_eq!(
        calibration_status(&done, "c").unwrap().state,
        ActivityState::Done {
            summary: "Step 7 suggested".into(),
            next: Some(ActionId::OpenCapture)
        }
    );
    let failed = Calibration::Failed("The survey did not finish in time".into());
    let status = calibration_status(&failed, "c").unwrap();
    assert!(matches!(status.state, ActivityState::NeedsYou { .. }));
    assert_eq!(status.cancel, CancelMode::None);
}

#[test]
fn a_render_reports_its_stage_frames_and_time_left() {
    let mut progress = crate::pipeline::PipelineProgress::default();
    progress.frames_total = Some(299);
    progress.frames_processed = Some(120);
    let started = Instant::now();
    let status = render_status(
        "run",
        "Stack · Blue weevil",
        Some(7),
        &progress,
        false,
        Some(started),
        Some(Duration::from_secs(90)),
        Some(PathBuf::from("run/render.log")),
    );
    assert_eq!((status.done, status.total), (Some(120), Some(299)));
    assert_eq!(status.phase, progress.stage.title());
    assert_eq!(
        (status.lane, status.cancel),
        (Lane::Heavy, CancelMode::Kill)
    );
    assert!((status.fraction().unwrap() - 120.0 / 299.0).abs() < 1e-6);
    let stopping = render_status("run", "x", None, &progress, true, None, None, None);
    assert_eq!(
        (stopping.phase.as_str(), stopping.cancel),
        ("Stopping", CancelMode::None)
    );
    assert!(metadata_status(&crate::camera_metadata::CameraMetadata::default()).is_none());
}

#[test]
fn a_frame_costs_the_same_with_a_full_history() {
    let frame = |activities: &mut Activities| {
        activities.begin();
        for n in 0..12 {
            activities.report(
                running(&format!("job-{n}"), Lane::Background).with_progress(Some(n), Some(100)),
            );
        }
        activities.end(Instant::now(), 1);
    };
    let mut timings = Vec::new();
    for history in [0, MAX_HISTORY] {
        let mut activities = Activities::default();
        for n in 0..history {
            activities.record(HistoryEntry {
                kind: ActivityKind::Export,
                title: format!("Export {n}"),
                stack: None,
                outcome: "done".into(),
                summary: String::new(),
                finished: n as u64,
                took_seconds: None,
                action: None,
                log: None,
            });
        }
        let revision = activities.history_revision();
        let started = Instant::now();
        for _ in 0..2_000 {
            frame(&mut activities);
        }
        timings.push(started.elapsed() / 2_000);
        assert_eq!(
            activities.history_revision(),
            revision,
            "running work never touches history"
        );
    }
    eprintln!(
        "activity-frame: 12 activities, history 0: {:?} per frame; history {MAX_HISTORY}: {:?} (debug build)",
        timings[0], timings[1]
    );
}
