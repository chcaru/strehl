//! Independent v18 workflow witnesses: the commands are found in the rendered
//! UI, and stale saved-run delivery is deliberately sent after changing bracket.
use super::*;
use crate::jobs::FrameFile;

fn test_app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.stack = Some(StackScan {
        directory: PathBuf::from("review-visible-bracket"),
        frames: (0..13)
            .map(|index| FrameFile {
                path: PathBuf::from(format!("review-{index}.arw")),
                bytes: 42,
            })
            .collect(),
        total_bytes: 546,
    });
    app
}

fn draw(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1440.0, 940.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.workspace(ctx);
        },
    )
}

fn find_text(output: &egui::FullOutput, needle: &str) -> Option<egui::Pos2> {
    fn find(shape: &egui::Shape, needle: &str) -> Option<egui::Pos2> {
        match shape {
            egui::Shape::Text(text) if text.galley.text() == needle => {
                Some(text.pos + text.galley.size() * 0.5)
            }
            egui::Shape::Vec(parts) => parts.iter().find_map(|part| find(part, needle)),
            _ => None,
        }
    }
    output
        .shapes
        .iter()
        .find_map(|clipped| find(&clipped.shape, needle))
}

fn pointer(at: egui::Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

#[test]
fn default_process_survives_actual_rail_buttons_and_integrated_source_inspection() {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = test_app();
    assert!(app.process_view, "normal launch starts inside the process");
    let initial = draw(&mut app, &ctx, 0.0, vec![]);
    assert!(find_text(&initial, "READ").is_some());
    for (step, (label, pane)) in [
        ("Adjust", workspace::Sidebar::Adjust),
        ("Review", workspace::Sidebar::Review),
        ("Activity", workspace::Sidebar::Activity),
        ("Projects", workspace::Sidebar::Projects),
    ]
    .into_iter()
    .enumerate()
    {
        let time = step as f64 + 0.1;
        let previous = draw(&mut app, &ctx, time, vec![]);
        let at = find_text(&previous, label).expect("actual rail command must be visible");
        draw(
            &mut app,
            &ctx,
            time + 0.1,
            vec![egui::Event::PointerMoved(at), pointer(at, true)],
        );
        let opened = draw(&mut app, &ctx, time + 0.2, vec![pointer(at, false)]);
        assert!(app.process_view, "{label} navigated away from Process");
        assert!(
            find_text(&opened, "READ").is_some(),
            "{label} replaced Process"
        );
        assert_eq!(app.sidebar, Some(pane), "click must open its actual pane");
    }
    app.inspect_frame(11);
    assert!(app.process_view);
    assert_eq!(
        app.selected, 11,
        "source request must select its actual capture"
    );
    assert_eq!(app.process_space.inspection_frame(), Some(11));
    let inspected = draw(&mut app, &ctx, 5.0, vec![]);
    assert!(find_text(&inspected, "READ").is_some());
    assert!(
        find_text(&inspected, "SOURCE SWEEP").is_none(),
        "source inspection belongs in the primary image and timeline"
    );
    assert_eq!(
        app.sidebar,
        Some(workspace::Sidebar::Projects),
        "source inspection cannot hijack navigation"
    );
}

#[test]
fn importing_a_bracket_discards_late_replay_without_losing_workspace_proportions() {
    let ctx = egui::Context::default();
    let mut app = test_app();
    let prefs = crate::workspace_layout::WorkspaceLayout {
        network: 0.26,
        detail: 0.65,
        final_detail: 0.31,
        lower: 0.08,
        fingerprint: 0.06,
        focus_photo: false,
    };
    app.catalog.layout = prefs;
    app.process_space.set_layout(prefs);
    app.process_space.inspect_frame(8);
    let (send, receive) = mpsc::sync_channel(1);
    app.replay = Some(jobs::spawn_task("independent-delayed-replay", move |_| {
        receive.recv().map_err(anyhow::Error::from)
    }));
    app.import(PathBuf::from("new-bracket-that-does-not-exist"));
    // Isolate the cancelled old replay from this deliberately absent scan.
    app.scan = None;
    assert!(app.replay.is_none());
    let run: crate::workspace_history::Run = serde_json::from_value(serde_json::json!({
        "directory": "old-run", "source": "old-bracket", "output": "old-output.tiff",
        "log": "old-run/activity.log", "label": "Old run", "created": 1,
        "status": "Saved", "frames": 99, "settings": jobs::RenderSettings::default(),
        "exposure": null, "gate": null, "workers": 1, "pinned": false
    }))
    .unwrap();
    let mut old_progress = PipelineProgress::default();
    old_progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=99\n");
    old_progress.mark_complete();
    send.send((run, old_progress)).unwrap();
    for _ in 0..3 {
        app.poll(&ctx);
    }
    assert!(app.result.is_none() && app.image_path.is_none() && app.pending_result.is_none());
    assert_eq!(app.progress.stage, Stage::Preparing);
    assert!(!app.recorded && !app.activity);
    assert_eq!(app.process_space.inspection_frame(), None);
    assert_eq!(app.process_space.layout(), prefs);
    assert!(app.process_view);
}

#[test]
fn replay_keeps_the_event_loop_awake_after_source_work_has_finished() {
    let ctx = egui::Context::default();
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    let (send, receive) = mpsc::sync_channel::<()>(1);
    app.replay = Some(jobs::spawn_task("independent-replay-wake", move |_| {
        let _ = receive.recv_timeout(Duration::from_secs(5));
        anyhow::bail!("review worker released")
    }));
    let mut last = None;
    for frame in 0..5 {
        last = Some(ctx.run(
            egui::RawInput {
                time: Some(frame as f64),
                ..Default::default()
            },
            |ctx| app.poll(ctx),
        ));
    }
    let output = last.unwrap();
    let delay = output
        .viewport_output
        .get(&egui::ViewportId::ROOT)
        .unwrap()
        .repaint_delay;
    send.send(()).unwrap();
    assert!(app.replay.is_some() && app.scan.is_none() && app.job.is_none());
    assert!(
        delay <= Duration::from_millis(70),
        "an idle replay must finish without requiring a pointer event; repaint delay was {delay:?}"
    );
}

#[test]
fn changed_sources_are_withheld_before_or_after_replay_but_saved_participation_remains() {
    for scan_arrives_first in [true, false] {
        let ctx = egui::Context::default();
        theme::install(&ctx);
        let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
        let run: crate::workspace_history::Run = serde_json::from_value(serde_json::json!({
            "directory": "review-old-run", "source": "review-old-source", "output": "review-old-run/stack.tiff",
            "log": "review-old-run/activity.log", "label": "Saved evidence", "created": 1,
            "status": "Saved", "frames": 3, "settings": jobs::RenderSettings::default(),
            "sources": [
                {"path":"review-old-source/a.arw", "bytes":101, "modified_ns":null},
                {"path":"review-old-source/b.arw", "bytes":202, "modified_ns":null},
                {"path":"review-old-source/c.arw", "bytes":303, "modified_ns":null}
            ],
            "exposure":null, "gate":null, "workers":1, "pinned":false
        })).unwrap();
        let changed = StackScan {
            directory: run.source.clone(),
            frames: [("a", 101), ("replacement", 202), ("c", 303)]
                .map(|(name, bytes)| FrameFile {
                    path: run.source.join(format!("{name}.arw")),
                    bytes,
                })
                .to_vec(),
            total_bytes: 606,
        };
        assert!(
            !run.matches_scan(&changed),
            "fixture must have an actual equal-count identity mismatch"
        );
        if scan_arrives_first {
            app.stack = Some(changed.clone());
        }
        let mut progress = PipelineProgress::default();
        progress.ingest("planes: 2 x 2 per CFA plane\nbands: 7 Laplacian levels + 1 base, coarsest 1 x 1\nSTREHL_UI_PROGRESS event=stage name=alignment total=3\nSTREHL_UI_PROGRESS event=diagnostic seq=1 frame=1 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=3 sampling=nearest data=00ff\nwrote: stack.tiff (4 x 4, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
        progress.mark_complete();
        let returned = run.clone();
        app.replay = Some(jobs::spawn_task(
            "independent-source-replay-order",
            move |_| Ok((returned, progress)),
        ));
        let started = Instant::now();
        while app.replay.is_some() && started.elapsed() < Duration::from_secs(5) {
            app.poll(&ctx);
            std::thread::yield_now();
        }
        assert!(app.replay.is_none(), "fixture worker must actually deliver");
        if !scan_arrives_first {
            app.scan = Some(jobs::spawn_task(
                "independent-late-source-scan",
                move |_| Ok(changed),
            ));
            let started = Instant::now();
            while app.scan.is_some() && started.elapsed() < Duration::from_secs(5) {
                app.poll(&ctx);
                std::thread::yield_now();
            }
            assert!(app.scan.is_none());
        }
        assert!(
            app.stack.is_none(),
            "changed source pictures must not claim old mask identities"
        );
        assert!(
            app.error.is_some(),
            "withheld source imagery needs a visible explanation"
        );
        assert_eq!(app.progress.stage, Stage::Complete);
        assert_eq!(app.expected_run.as_ref().unwrap().frames, 3);
        assert!(app.progress.admission_archive.cells(0, 1).is_some());

        // A saved TIFF remains inspectable with its recorded capture axis even
        // when source photos are unavailable. This bypasses only TIFF decoding.
        let photo = ctx.load_texture(
            "review-saved-photo",
            egui::ColorImage::filled([4, 4], Color32::GRAY),
            egui::TextureOptions::LINEAR,
        );
        app.result_viewer.install(&photo, [4, 4], false);
        app.result = Some(run.output.clone());
        app.image_path = Some(run.output);
        app.process_view = true;
        draw(&mut app, &ctx, 1.0, vec![]);
        let saved = draw(&mut app, &ctx, 2.0, vec![]);
        assert!(
            find_text(&saved, "CAPTURE / ADMITTED SAMPLES").is_some(),
            "missing live source files must not erase saved capture participation"
        );
    }
}

#[test]
fn reopening_all_preview_packets_before_first_paint_recovers_the_latest_actual_photograph() {
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut app = test_app();
    app.stack.as_mut().unwrap().frames.pop();
    app.stack.as_mut().unwrap().total_bytes = 12 * 42;
    app.progress.ingest("planes: 131 x 99 per CFA plane\nbands: 7 Laplacian levels + 1 base, coarsest 2 x 1\nSTREHL_UI_PROGRESS event=stage name=merge total=12\n");
    for folded in 1..=12 {
        let data: String = (0..6)
            .map(|cell| format!("{:02x}", folded * 12 + cell * 3))
            .collect();
        app.progress.ingest(&format!(
            "STREHL_UI_PROGRESS event=diagnostic seq={folded} frame={} level=3 kind=preview scope=stack scale=linear width=3 height=2 min=0 max=100 folded={folded} total=12 sampling=nearest data={data}\n",
            folded - 1
        ));
    }
    app.activity = true;
    app.recorded = true;
    // This is the real app coalescer used after the asynchronous replay returns.
    // No intermediate UI paint sees any of the first eleven delivered prefixes.
    app.cache_process_surfaces(&ctx);
    assert!(
        app.process_surfaces
            .iter()
            .any(|surface| surface.kind == DiagnosticKind::Preview),
        "fixture must reach the actual preview consumer"
    );
    draw(&mut app, &ctx, 0.0, vec![]);
    draw(&mut app, &ctx, 0.5, vec![]);
    let recorded = draw(&mut app, &ctx, 1.0, vec![]);
    let latest = app.progress.live_preview.latest.as_ref().unwrap();
    assert_eq!((latest.frame, latest.folded, latest.sequence), (11, 12, 12));
    assert!(
        recorded.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Text(text) if text.galley.text().contains("LIVE STACK / 12 OF 12 FRAMES"))),
        "coalesced replay must promote the actual final observed prefix to the main viewer"
    );
    assert!(recorded.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.vertices.len() >= 4
        && egui::Rect::from_points(&mesh.vertices.iter().map(|v|v.pos).collect::<Vec<_>>()).area() > 10_000.0)),
        "the actual preview must be visibly painted, not merely a status count");
    assert!(find_text(&recorded, "BUILD").is_none());
}

#[test]
fn history_records_clicked_render_settings_even_if_adjust_changes_before_started_delivery() {
    let files = jobs::tests::TestDirectory::new("review-clicked-render-settings");
    let source = files.path().join("source");
    std::fs::create_dir_all(&source).unwrap();
    let mut captures = Vec::new();
    for index in 0..3 {
        let path = source.join(format!("capture-{index:02}.arw"));
        std::fs::write(&path, [index as u8; 42]).unwrap();
        captures.push(FrameFile { path, bytes: 42 });
    }
    let executable = files.path().join("not-an-executable.exe");
    // The worker emits Started before trying this deliberately invalid file.
    // No actual engine or RAW processing runs in this settings-race witness.
    std::fs::write(&executable, b"not executable").unwrap();
    let ctx = egui::Context::default();
    let mut app = test_app();
    app.stack = Some(StackScan {
        directory: source,
        frames: captures,
        total_bytes: 3 * 42,
    });
    app.engine = Some(executable);
    app.output = files.path().join("output");
    app.controls.settings.binned = true;
    app.controls.settings.pyramid_bands = Some(5);
    app.controls.exposure = Some(-0.75);
    app.controls.gate = Some(0.7);
    app.controls.workers = 2;
    let clicked = app.controls.settings.clone();
    app.start_render();
    assert!(app.job.is_some(), "actual owned worker must have started");
    let pending = app.pending_run.as_ref().expect("clicked request is frozen");
    assert_eq!(pending.settings, clicked);
    assert_eq!(
        (pending.exposure, pending.gate, pending.workers),
        (Some(-0.75), Some(0.7), 2)
    );
    assert!(pending.matches_scan(app.stack.as_ref().unwrap()));
    app.controls.settings = jobs::RenderSettings::default();
    app.controls.exposure = Some(1.5);
    app.controls.gate = Some(0.2);
    app.controls.workers = 1;
    let started = Instant::now();
    while app.job.is_some() && started.elapsed() < Duration::from_secs(5) {
        app.poll(&ctx);
        std::thread::yield_now();
    }
    assert!(app.job.is_none(), "deliberately invalid worker must finish");
    let saved = app
        .catalog
        .runs
        .first()
        .expect("Started must create real history metadata");
    assert_eq!(
        saved.settings, clicked,
        "history must record the immutable request, not subsequent Adjust values"
    );
    assert_eq!(
        (saved.exposure, saved.gate, saved.workers),
        (Some(-0.75), Some(0.7), 2)
    );
    assert!(saved.matches_scan(app.stack.as_ref().unwrap()));
}
