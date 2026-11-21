//! The stack queue and the activity file.
use super::*;
use crate::workspace_history::StackDraft;

fn request(source: &str) -> RenderRequest {
    RenderRequest {
        executable: PathBuf::from("strehl-cli.exe"),
        source: PathBuf::from(source),
        output_parent: PathBuf::from("out"),
        exposure_ev: Some(-0.5),
        pyramid_gate: None,
        worker_threads: Some(12),
        settings: RenderSettings::default(),
        retain_master: true,
        recipe: Some(strehl_edit::DevelopmentRecipe::default()),
    }
}
fn run(source: &str) -> Run {
    serde_json::from_value(serde_json::json!({
        "directory": "", "source": source, "output": "", "log": "",
        "label": "100MSDCF", "created": 5, "status": "Stacking", "frames": 299,
        "settings": RenderSettings::default(), "exposure": null, "gate": null, "workers": 12
    }))
    .unwrap()
}
fn entry(stack: NodeId, title: &str, planes: usize, estimate_seconds: Option<f64>) -> QueueEntry {
    QueueEntry {
        stack,
        title: title.into(),
        planes,
        estimate_seconds,
    }
}
fn queue_of(n: usize) -> StackQueue {
    let mut queue = StackQueue::default();
    for i in 0..n {
        queue
            .enqueue(
                entry(
                    i as u64 + 10,
                    &format!("Stack · subject {i}"),
                    299,
                    Some(25.0 * (i + 1) as f64),
                ),
                &request(&format!("captures/{i}")),
                run(&format!("captures/{i}")),
                1_000 + i as u64,
            )
            .unwrap();
    }
    queue
}

#[test]
fn a_frozen_request_round_trips_through_the_file_format() {
    let original = request("captures/weevil");
    let frozen = FrozenRequest::from(&original);
    let json = serde_json::to_string(&frozen).unwrap();
    let back: FrozenRequest = serde_json::from_str(&json).unwrap();
    assert_eq!(back, frozen);
    let restored = RenderRequest::from(back);
    assert_eq!(FrozenRequest::from(&restored), frozen);
    assert!(
        serde_json::from_str::<FrozenRequest>(
            &json.replace("\"retain_master\"", "\"x\":1,\"retain_master\"")
        )
        .is_err(),
        "unknown fields are refused, not dropped"
    );
}

#[test]
fn the_heavy_lane_starts_one_stack_at_a_time_in_order() {
    let mut queue = queue_of(3);
    let ids: Vec<u64> = queue.items().map(|i| i.id).collect();
    assert_eq!(ids.len(), 3);
    assert!(ids.windows(2).all(|w| w[0] < w[1]));
    let free = StartGate::default();
    assert!(
        queue
            .take_next(
                StartGate {
                    heavy_busy: true,
                    quiet: false,
                    workspace: None
                },
                1
            )
            .is_none(),
        "another heavy activity holds the lane"
    );
    assert!(
        queue
            .take_next(
                StartGate {
                    heavy_busy: false,
                    quiet: true,
                    workspace: None
                },
                1
            )
            .is_none(),
        "Quiet holds the lane"
    );
    let first = queue.take_next(free, 2).unwrap();
    assert_eq!(first.id, ids[0]);
    assert_eq!(queue.running().unwrap().id, ids[0]);
    assert!(queue.take_next(free, 3).is_none(), "serial: one at a time");
    queue.finish(ids[0]);
    assert!(queue.running().is_none());
    // Reorder and remove waiting stacks.
    assert!(queue.move_to(ids[2], 0));
    assert_eq!(queue.items().next().unwrap().id, ids[2]);
    assert!(queue.remove(ids[1]).is_some());
    assert!(queue.remove(ids[1]).is_none());
    assert_eq!(queue.take_next(free, 4).unwrap().id, ids[2]);
    assert!(queue.is_empty());
    let revision = queue.revision();
    queue.finish(999);
    assert_eq!(
        queue.revision(),
        revision,
        "finishing another id changes nothing"
    );
}

#[test]
fn waiting_stacks_say_what_they_wait_for() {
    let mut queue = queue_of(2);
    let mut activities = Activities::default();
    let report = |queue: &StackQueue, activities: &mut Activities, gate| {
        activities.begin();
        queue.report(
            activities,
            gate,
            Some("the full-screen program in front to close (Quiet)"),
        );
        activities.end(std::time::Instant::now(), 1);
        activities
            .waiting()
            .map(|s| match &s.state {
                ActivityState::Waiting { for_what, .. } => (s.queued.unwrap(), for_what.clone()),
                _ => unreachable!(),
            })
            .collect::<Vec<_>>()
    };
    let waiting = report(&queue, &mut activities, StartGate::default());
    assert_eq!(waiting[0].1, "its turn");
    assert_eq!(waiting[1].1, "the stack before it");
    let quiet = StartGate {
        heavy_busy: false,
        quiet: true,
        workspace: None,
    };
    assert_eq!(
        report(&queue, &mut activities, quiet)[0].1,
        "the full-screen program in front to close (Quiet)"
    );
    queue.paused = true;
    assert_eq!(
        report(&queue, &mut activities, quiet)[0].1,
        "you to resume the queue"
    );
    let status = activities.waiting().next().unwrap();
    assert_eq!((status.lane, status.total), (Lane::Heavy, Some(299)));
    assert_eq!(status.eta, Some(Duration::from_secs(25)));
    assert_eq!(status.phase, "299 planes · about 25 s");
    queue.resume();
    assert!(!queue.paused);
}

#[test]
fn queue_and_history_survive_a_restart_through_an_atomic_file() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("activities.json");
    let mut queue = queue_of(2);
    queue.take_next(StartGate::default(), 50);
    let mut activities = Activities::default();
    for n in 0..(MAX_HISTORY + 5) {
        activities.record(HistoryEntry {
            kind: ActivityKind::Export,
            title: format!("Export {n}"),
            stack: None,
            outcome: "done".into(),
            summary: "Exported".into(),
            finished: n as u64,
            took_seconds: Some(1.5),
            action: Some(ActionId::Reveal {
                path: PathBuf::from("a.png"),
            }),
            log: None,
        });
    }
    let mut store = ActivityStore::new(Some(path.clone()));
    store.save_if_changed(&queue, &activities);
    assert!(store.error.is_none(), "{:?}", store.error);
    let written = std::fs::metadata(&path).unwrap().modified().unwrap();
    store.save_if_changed(&queue, &activities);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        written,
        "nothing changed, nothing written"
    );
    assert_eq!(
        std::fs::read_dir(directory.path()).unwrap().count(),
        1,
        "no temporary left"
    );
    let (loaded, history, error) = load(&path);
    assert!(error.is_none());
    assert_eq!(loaded.len(), 1);
    assert_eq!(loaded.running().unwrap().title, "Stack · subject 0");
    assert_eq!(history.len(), MAX_HISTORY);
    assert_eq!(history[0].title, format!("Export {}", MAX_HISTORY + 4));
    // A later enqueue never reuses a stored id.
    let mut loaded = loaded;
    let stored = loaded.items().next().unwrap().id;
    let new = loaded
        .enqueue(entry(3, "x", 1, None), &request("c"), run("c"), 9)
        .unwrap();
    assert!(new > stored);
}

#[test]
fn an_unreadable_or_newer_file_starts_empty_and_is_left_as_it_was() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("activities.json");
    assert!(load(&path).2.is_none(), "no file is not an error");
    for bytes in [
        &b"{not json"[..],
        br#"{"format":9,"queue":[],"history":[]}"#,
    ] {
        std::fs::write(&path, bytes).unwrap();
        let (queue, history, error) = load(&path);
        assert!(queue.is_empty() && history.is_empty());
        assert!(error.unwrap().contains("could not be read"));
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
    }
}

#[test]
fn reconciling_after_a_restart_records_the_interrupted_stack_and_pauses_the_rest() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Bugs").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let draft = StackDraft::from_run(&run("captures/0"));
    let kept = catalog
        .create_stack(subject, "Dorsal", draft.clone())
        .unwrap();
    let mut queue = StackQueue::default();
    for (stack, title) in [
        (kept, "Stack · kept"),
        (kept, "Stack · running"),
        (9_999, "Stack · gone"),
    ] {
        queue
            .enqueue(entry(stack, title, 10, None), &request("c"), run("c"), 1)
            .unwrap();
    }
    queue.take_next(StartGate::default(), 2);
    let notes = queue.reconcile(&catalog, 100);
    assert_eq!(notes.len(), 2);
    assert_eq!(notes[0].title, "Stack · kept", "the one that was running");
    assert_eq!(notes[0].action, Some(ActionId::Retry { stack: kept }));
    assert!(notes[1].summary.contains("no longer in the library"));
    assert!(queue.running().is_none());
    assert_eq!(queue.len(), 1);
    assert!(
        queue.paused,
        "heavy work never starts by itself after a restart"
    );
    assert!(queue.take_next(StartGate::default(), 3).is_none());
    queue.resume();
    assert_eq!(
        queue.take_next(StartGate::default(), 4).unwrap().title,
        "Stack · running"
    );
}
