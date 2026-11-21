//! The window's activity adapters, on an in-memory app.
use super::*;
use crate::activity::ActivityState;

fn app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default(); // In-memory catalog; never the real one.
    app
}
fn report(app: &StrehlApp) -> Activities {
    let mut activities = Activities::default();
    activities.begin();
    app.report_activities(&mut activities, None);
    activities.end(Instant::now(), 1);
    activities
}

#[test]
fn an_idle_window_reports_nothing() {
    assert!(report(&app()).statuses().is_empty());
}

#[test]
fn imports_and_bundle_copies_report_while_their_workers_run() {
    let mut app = app();
    let (release, wait) = mpsc::channel::<()>();
    app.session_import = Some((
        4,
        None,
        jobs::spawn_task("import-test", move |_| {
            let _ = wait.recv();
            anyhow::bail!("released")
        }),
    ));
    let (bundle_release, bundle_wait) = mpsc::channel::<()>();
    app.view_bundle_export = Some(jobs::spawn_reporting_task("bundle-test", move |_| {
        let _ = bundle_wait.recv();
        anyhow::bail!("released")
    }));
    let activities = report(&app);
    let kinds: Vec<ActivityKind> = activities.statuses().iter().map(|s| s.kind).collect();
    assert_eq!(kinds, [ActivityKind::ViewBundle, ActivityKind::Import]);
    assert!(
        activities
            .statuses()
            .iter()
            .all(|s| s.lane == Lane::Background && s.cancel == CancelMode::Cooperative)
    );
    app.activity_hub.activities = activities;
    let value = StrehlApp::activities_value(&app.activity_hub);
    assert_eq!(value["queue_paused"], false);
    assert_eq!(value["current"][1]["kind"], "import");
    assert_eq!(value["current"][1]["state"], "running");
    let _ = (release.send(()), bundle_release.send(()));
}

#[test]
fn a_finished_render_leaves_a_history_note_with_its_next_step() {
    let done = StrehlApp::render_outcome_note(
        Some(3),
        "Stack · Weevil",
        &jobs::RenderOutcome::Completed {
            directory: PathBuf::from("run"),
            output: PathBuf::from("run/photograph.tiff"),
            log: PathBuf::from("run/render.log"),
        },
        Some(Duration::from_secs(157)),
        10,
    );
    assert_eq!(done.outcome, "done");
    assert_eq!(
        done.action,
        Some(ActionId::Reveal {
            path: PathBuf::from("run/photograph.tiff")
        })
    );
    assert_eq!(done.took_seconds, Some(157.0));
    let failed = StrehlApp::render_outcome_note(
        Some(3),
        "Stack · Weevil",
        &jobs::RenderOutcome::Failed {
            directory: None,
            message: "Out of memory".into(),
        },
        None,
        11,
    );
    assert_eq!(
        (failed.outcome.as_str(), failed.action),
        ("needs_you", Some(ActionId::Retry { stack: 3 }))
    );
    let cancelled = StrehlApp::render_outcome_note(
        None,
        "Stack",
        &jobs::RenderOutcome::Cancelled {
            directory: PathBuf::from("run"),
        },
        None,
        12,
    );
    assert_eq!(cancelled.outcome, "stopped");
}

/// An app with a three-photo stack and an engine that cannot start: every
/// render ends at once with Failed, which is all the queue needs to move.
fn queue_fixture() -> (StrehlApp, jobs::tests::TestDirectory) {
    let files = jobs::tests::TestDirectory::new("p5-stack-queue");
    let source = files.path().join("camera-bracket");
    std::fs::create_dir(&source).unwrap();
    let frames = (0..3)
        .map(|index| {
            let path = source.join(format!("photo-{index:02}.arw"));
            std::fs::write(&path, [index as u8; 42]).unwrap();
            jobs::FrameFile { path, bytes: 42 }
        })
        .collect();
    let engine = files.path().join("deliberately-invalid.exe");
    std::fs::write(&engine, b"This is not an executable").unwrap();
    let mut app = app();
    app.stack = Some(StackScan {
        directory: source,
        frames,
        total_bytes: 126,
    });
    app.engine = Some(engine);
    app.output = files.path().join("results");
    app.controls.exposure = Some(0.75);
    app.ensure_project_stack();
    app.catalog
        .node_mut(app.active_stack.unwrap())
        .unwrap()
        .name = "Petal study".into();
    // Whatever is in front of this machine, Quiet never holds a test.
    app.shell.prefs.quiet = false;
    (app, files)
}
/// Poll frames until `done`, at most five seconds.
fn poll_until(app: &mut StrehlApp, mut done: impl FnMut(&StrehlApp) -> bool) {
    let ctx = egui::Context::default();
    let deadline = Instant::now() + Duration::from_secs(5);
    while !done(app) {
        assert!(Instant::now() < deadline, "timed out: {}", app.status);
        let _ = ctx.run(egui::RawInput::default(), |ctx| app.poll(ctx));
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[test]
fn start_while_a_stack_renders_queues_a_variant_once_and_it_starts_after() {
    let (mut app, _files) = queue_fixture();
    app.start_render();
    assert!(app.job.is_some() && app.activity_hub.queue.is_empty());
    // A repeated Start is not a second copy of the running render.
    app.start_render();
    assert!(app.activity_hub.queue.is_empty());
    assert_eq!(
        app.status,
        "This stack is already rendering with these settings"
    );
    // A changed recipe queues once.
    app.controls.exposure = Some(1.25);
    app.start_render();
    assert_eq!(app.activity_hub.queue.len(), 1, "{}", app.status);
    app.start_render();
    assert_eq!(app.activity_hub.queue.len(), 1, "queued once");
    assert_eq!(
        app.status,
        "This stack already waits in the queue with these settings"
    );
    let queued = app.activity_hub.queue.items().next().unwrap().id;
    // The first render ends; the queue starts the variant with its recipe.
    poll_until(&mut app, |app| {
        app.activity_hub.running_queue == Some(queued)
    });
    assert!(app.activity_hub.queue.is_empty());
    assert!(app.job.is_some(), "the queued render runs");
    assert_eq!(app.controls.exposure, Some(1.25));
    let first = &app.activity_hub.activities.history()[0];
    assert_eq!(
        (first.title.as_str(), first.outcome.as_str()),
        ("Stack · Petal study", "needs_you")
    );
    // It ends too, and the queue is idle.
    poll_until(&mut app, |app| {
        app.job.is_none() && app.activity_hub.running_queue.is_none()
    });
    assert_eq!(app.activity_hub.activities.history().len(), 2);
    assert!(app.activity_hub.queue.running().is_none());
}

#[test]
fn queued_stacks_wait_for_the_workspace_and_quiet_and_show_in_the_tray_list() {
    let (mut app, _files) = queue_fixture();
    let stack = app.active_stack.unwrap();
    let id = app.queue_stack(stack).unwrap();
    // A file dialog in front: the stack waits and says why.
    let (_sender, receiver) = mpsc::channel();
    app.dialog = Some(receiver);
    let ctx = egui::Context::default();
    let _ = ctx.run(egui::RawInput::default(), |ctx| app.activities_frame(ctx));
    assert!(app.job.is_none());
    let waiting: Vec<_> = app.activity_hub.activities.waiting().collect();
    assert_eq!(waiting.len(), 1);
    assert_eq!(waiting[0].queued, Some(id));
    assert!(
        matches!(&waiting[0].state, ActivityState::Waiting { for_what, .. } if for_what == "the file dialog to close")
    );
    // Removed from the tray, it is gone.
    let status_id = waiting[0].id;
    app.activity_action(crate::activity_tray::TrayAction::Cancel(status_id));
    assert!(app.activity_hub.queue.is_empty());
    // The Quiet switch is the Preferences one.
    app.activity_action(crate::activity_tray::TrayAction::SetQuiet(true));
    assert!(app.shell.prefs.quiet && app.shell.prefs_dirty);
}

#[test]
fn a_restored_queue_waits_paused_and_offscreen_pictures_never_read_it() {
    let (mut app, files) = queue_fixture();
    let stack = app.active_stack.unwrap();
    app.queue_stack(stack).unwrap();
    let path = files.path().join("activities.json");
    crate::activity_queue::save(
        &path,
        &app.activity_hub.queue,
        app.activity_hub.activities.history(),
    )
    .unwrap();
    app.catalog.path = Some(files.path().join("projects.json"));
    let restored = ActivityHub::load(&mut app.catalog, &LaunchOptions::default());
    assert_eq!(restored.queue.len(), 1);
    assert!(restored.queue.paused, "heavy work never starts by itself");
    app.activity_hub = restored;
    let ctx = egui::Context::default();
    let _ = ctx.run(egui::RawInput::default(), |ctx| app.activities_frame(ctx));
    assert!(app.job.is_none());
    let waiting = app.activity_hub.activities.waiting().next().unwrap();
    assert!(
        matches!(&waiting.state, ActivityState::Waiting { for_what, .. } if for_what == "you to resume the queue")
    );
    assert_eq!(
        StrehlApp::activities_value(&app.activity_hub)["queue_paused"],
        true
    );
    let offscreen = LaunchOptions {
        offscreen: true,
        ..LaunchOptions::default()
    };
    assert!(
        ActivityHub::load(&mut app.catalog, &offscreen)
            .queue
            .is_empty()
    );
}

#[test]
fn stop_in_the_tray_reaches_each_owner_and_never_stops_a_capture_unasked() {
    let mut app = app();
    let mut activities = Activities::default();
    activities.begin();
    let capture = ActivityStatus::new(ActivityKind::Capture, "sequence:4", "Capture", Lane::Camera)
        .with_cancel(CancelMode::Cooperative);
    let compaction = ActivityStatus::running(ActivityKind::CompactApply, "Compacting", Lane::Heavy);
    let (capture_id, compaction_id) = (capture.id, compaction.id);
    activities.report(capture);
    activities.report(compaction);
    activities.end(Instant::now(), 1);
    app.activity_hub.activities = activities;
    app.activity_action(crate::activity_tray::TrayAction::Cancel(compaction_id));
    assert_eq!(app.capture.confirm, None);
    app.activity_action(crate::activity_tray::TrayAction::Cancel(capture_id));
    assert_eq!(
        app.capture.confirm,
        Some(crate::capture_workspace::Confirm::Stop),
        "the capture asks first, on its own screen"
    );
    assert_eq!(
        app.shell.navigator.station(),
        super::super::studio_route::Station::Capture
    );
}
