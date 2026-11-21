//! The window's activity adapters, on an in-memory app.
use super::*;

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
    let value = StrehlApp::activities_value(&activities);
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
