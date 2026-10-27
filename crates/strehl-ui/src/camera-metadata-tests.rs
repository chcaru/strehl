use super::*;
use serde_json::json;
use std::sync::{Arc, atomic::AtomicUsize};

fn report(source: &Path, stamp: &SourceStamp) -> Value {
    json!({"schema":"strehl-sony-focus-audit-v1","file_count":1,"records_included":true,"comparison_breaks":[],"frames":[{
        "index":0,"path":source,"file_identity":{"byte_length":stamp.bytes,"modified_unix_ns":stamp.modified_ns},
        "status":"absent","optical":{"schema":"strehl-sony-optical-facts-v1","status":"present","facts":{
            "model":{"value":"ILCE-7CM2"},"software":{"value":"test firmware"},"lens_model":{"value":"macro lens"},
            "distortion":{"setting":{"value":0},"table":{"samples":[0,-1,-2,-3,-4,-5,-6,-7,-8,-9,-10,-11,-12,-13,-14,-15]}},
            "maker_distortion_setting":{"value":4294967295_i64},
            "shading":{"setting":null,"table":null},"chromatic_aberration":{"setting":null,"table":null}
        }}
    }]})
}

#[test]
fn camera_metadata_keeps_optical_independent_of_af_and_zero_setting() {
    let source = Path::new("frame.ARW");
    let stamp = SourceStamp {
        bytes: 1024,
        modified_ns: Some("1234".into()),
    };
    let summary = parse_report(&report(source, &stamp), source, &stamp).unwrap();
    assert_eq!(summary.camera, "ILCE-7CM2");
    assert_eq!(summary.focus.label, "Not recorded");
    assert_eq!(summary.optical.label, "Available");
    let row = &summary.optical_rows[2];
    assert_eq!(row.raw_setting, "0");
    assert_eq!(row.maker_setting, "4294967295");
    assert_eq!(row.table, "16 samples: -15 to 0 raw");
    assert!(summary.focus_rows.is_empty());
    assert_eq!(summary.optical_rows[0].raw_setting, "Not recorded");
}

#[test]
fn camera_metadata_preserves_outcomes_and_raw_af_units() {
    let source = Path::new("frame.ARW");
    let stamp = SourceStamp {
        bytes: 1,
        modified_ns: None,
    };
    for (code, label) in [
        ("absent", "Not recorded"),
        ("unsupported", "Unsupported layout"),
        ("malformed", "Malformed metadata"),
        ("io_error", "File read error"),
    ] {
        let mut value = report(source, &stamp);
        value["frames"][0]["status"] = json!(code);
        value["frames"][0]["reason"] = json!("retained reason");
        value["frames"][0]["optical"]["status"] = json!(code);
        value["frames"][0]["optical"]["facts"] = Value::Null;
        let summary = parse_report(&value, source, &stamp).unwrap();
        assert_eq!(summary.focus.label, label);
        assert_eq!(summary.focus.reason.as_deref(), Some("retained reason"));
        assert_eq!(summary.optical.label, label);
        assert!(summary.optical_rows.is_empty());
    }
    let mut value = report(source, &stamp);
    value["frames"][0]["status"] = json!("present");
    value["frames"][0]["metadata"] = json!({"scalars_raw":[65536,131072,0],"coarse_focus_position":73,
        "grid":{"width":33,"height":23,"record_count":759},"section_sequences_agree":false});
    let summary = parse_report(&value, source, &stamp).unwrap();
    assert_eq!(
        summary.focus_rows[1],
        ("Scalars A / B (raw units)", "65536 / 131072".into())
    );
    assert_eq!(summary.focus_rows[2].1, "33 × 23 · 759 records");
    assert!(summary.focus_rows[3].1.contains("freshness unknown"));
}

#[test]
fn camera_metadata_refuses_wrong_schema_source_count_stamp_and_engine() {
    let source = Path::new("frame.ARW");
    let stamp = SourceStamp {
        bytes: 1024,
        modified_ns: Some("1234".into()),
    };
    let base = report(source, &stamp);
    for (pointer, replacement) in [
        ("/schema", json!("other")),
        ("/file_count", json!(2)),
        ("/frames/0/path", json!("other.ARW")),
        ("/frames/0/index", json!(1)),
        ("/frames/0/file_identity/byte_length", json!(1025)),
        ("/frames/0/file_identity/modified_unix_ns", json!("1235")),
        ("/frames/0/optical/schema", json!("old engine")),
        ("/frames/0/status", json!("success")),
        (
            "/frames/0/optical/facts/distortion/table/samples/0",
            json!(32768),
        ),
    ] {
        let mut value = base.clone();
        *value.pointer_mut(pointer).unwrap() = replacement;
        assert!(parse_report(&value, source, &stamp).is_err(), "{pointer}");
    }
    let mut duplicate = base.clone();
    duplicate["frames"]
        .as_array_mut()
        .unwrap()
        .push(base["frames"][0].clone());
    assert!(parse_report(&duplicate, source, &stamp).is_err());
}

#[test]
fn camera_metadata_bounds_report_reads() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("report");
    fs::write(&path, [0; 17]).unwrap();
    assert!(bounded_read(&path, 16).is_err());
    assert_eq!(bounded_read(&path, 17).unwrap().len(), 17);
}

fn child(mode: &str, source: &Path, json: &Path) -> Command {
    let mut command = Command::new(std::env::current_exe().unwrap());
    command
        .args([
            "--exact",
            "camera_metadata::tests::metadata_child_fixture",
            "--nocapture",
        ])
        .env("STREHL_TEST_METADATA_MODE", mode)
        .env("STREHL_TEST_METADATA_SOURCE", source)
        .env("STREHL_TEST_METADATA_JSON", json);
    command
}
// Runs normally as a no-op; the parent invokes this exact one test in a child.
#[test]
fn metadata_child_fixture() {
    let Ok(mode) = std::env::var("STREHL_TEST_METADATA_MODE") else {
        return;
    };
    let source = PathBuf::from(std::env::var_os("STREHL_TEST_METADATA_SOURCE").unwrap());
    let json = PathBuf::from(std::env::var_os("STREHL_TEST_METADATA_JSON").unwrap());
    if mode == "failure" {
        std::process::exit(7);
    }
    if mode == "wait" {
        fs::write(json, b"child started").unwrap();
        std::thread::sleep(Duration::from_secs(15));
        return;
    }
    let value = if source.is_dir() {
        let mut paths = fs::read_dir(&source)
            .unwrap()
            .map(|e| e.unwrap().path())
            .collect::<Vec<_>>();
        paths.sort();
        let frames = paths
            .iter()
            .enumerate()
            .map(|(index, path)| {
                let stamp = SourceStamp::read(path).unwrap();
                let mut value = report(path, &stamp)["frames"][0].clone();
                value["index"] = json!(index);
                with_grid(&mut value, index as u32);
                value
            })
            .collect::<Vec<_>>();
        json!({"schema":"strehl-sony-focus-audit-v1","file_count":frames.len(),"records_included":true,"comparison_breaks":[],"frames":frames})
    } else {
        let stamp = SourceStamp::read(&source).unwrap();
        report(&source, &stamp)
    };
    fs::write(json, serde_json::to_vec(&value).unwrap()).unwrap();
    if mode == "mutate" {
        fs::write(source, b"changed source size").unwrap();
    }
    println!("camera-metadata-child-completed");
}

#[test]
fn camera_metadata_worker_success_failure_mutation_and_cancellation() {
    let dir = tempfile::tempdir().unwrap();
    let captures = dir.path().join("captures");
    fs::create_dir(&captures).unwrap();
    let source = captures.join("spaces & symbols ' source.ARW");
    let output = dir.path().join("reports");
    let target = Target {
        frame: FrameFile {
            path: source.clone(),
            bytes: 4,
        },
        output,
    };
    for mode in ["success", "failure", "mutate"] {
        fs::write(&source, b"test").unwrap();
        let result = inspect_using(&target, &AtomicBool::new(false), |source, json| {
            Ok(child(mode, source, json))
        });
        if mode == "success" {
            let result = result.unwrap();
            assert_eq!(result.summary.optical.label, "Available");
            let log =
                fs::read_to_string(result.json.parent().unwrap().join("metadata.log")).unwrap();
            assert!(log.contains("1 passed; 0 failed"), "{log}");
            assert!(log.contains("camera-metadata-child-completed"));
            assert!(!result.json.starts_with(&captures));
        } else {
            let error = format!("{:#}", result.unwrap_err());
            assert!(
                error.contains(if mode == "mutate" {
                    "Source changed"
                } else {
                    "Metadata inspection failed"
                }),
                "{error}"
            );
        }
    }
    let ready = dir.path().join("ready");
    let log = dir.path().join("cancel.log");
    let cancelled = Arc::new(AtomicBool::new(false));
    let flag = Arc::clone(&cancelled);
    let ready_in = ready.clone();
    let thread =
        std::thread::spawn(move || run_child(child("wait", &source, &ready_in), &flag, &log));
    let start = std::time::Instant::now();
    while !ready.exists() && start.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(10));
    }
    assert!(
        ready.exists(),
        "Cancellation must interrupt an actually running child"
    );
    cancelled.store(true, Ordering::Relaxed);
    assert!(format!("{:#}", thread.join().unwrap().unwrap_err()).contains("cancelled"));
}

#[test]
fn camera_metadata_output_guard_and_prelaunch_stamp_refuse_without_child() {
    let dir = tempfile::tempdir().unwrap();
    let source = dir.path().join("frame.ARW");
    fs::write(&source, b"source").unwrap();
    let launched = AtomicUsize::new(0);
    let mut target = Target {
        frame: FrameFile {
            path: source,
            bytes: 6,
        },
        output: dir.path().join("forbidden"),
    };
    let inspect = |target: &Target| {
        inspect_using(target, &AtomicBool::new(false), |_, _| {
            launched.fetch_add(1, Ordering::Relaxed);
            bail!("must not launch")
        })
    };
    assert!(format!("{:#}", inspect(&target).unwrap_err()).contains("outside the input stack"));
    assert!(!target.output.exists());
    target.frame.bytes = 7;
    assert!(format!("{:#}", inspect(&target).unwrap_err()).contains("changed since import"));
    assert_eq!(launched.load(Ordering::Relaxed), 0);
}

#[test]
fn camera_metadata_old_delivery_cannot_populate_another_capture_or_import() {
    let ctx = egui::Context::default();
    let mut state = CameraMetadata {
        token: 2,
        target: Some(BracketTarget {
            epoch: 2,
            directory: "bracket".into(),
            frames: vec![FrameFile {
                path: "new.ARW".into(),
                bytes: 1,
            }],
            output: "outside".into(),
        }),
        ..Default::default()
    };
    state.work = Some(Work {
        token: 1,
        epoch: 1,
        task: jobs::spawn_task("metadata-stale-fixture", |_| bail!("stale error")),
    });
    let start = std::time::Instant::now();
    while state.work.is_some() && start.elapsed() < Duration::from_secs(5) {
        state.poll(&ctx);
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(state.work.is_none());
    assert!(state.error.is_none());
    assert!(state.result.is_none());
    state.work = Some(Work {
        token: 2,
        epoch: 2,
        task: jobs::spawn_task("metadata-reset-fixture", |_| bail!("old bracket error")),
    });
    state.reset();
    let start = std::time::Instant::now();
    while state.work.is_some() && start.elapsed() < Duration::from_secs(5) {
        state.poll(&ctx);
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(state.work.is_none());
    assert!(state.target.is_none() && state.error.is_none() && !state.open);
}

#[test]
fn camera_metadata_command_uses_bundled_worker_and_exact_selected_file_arguments() {
    let source = Path::new("selected & literal ' frame.ARW");
    let json = Path::new("report space/report.json");
    let command = command(source, json).unwrap();
    let args: Vec<_> = command
        .get_args()
        .map(|s| s.to_string_lossy().into_owned())
        .collect();
    assert_eq!(
        args,
        [
            "--engine-worker",
            "focus",
            "inspect",
            "selected & literal ' frame.ARW",
            "--optical",
            "--records",
            "--out",
            "report space/report.json"
        ]
    );
    assert!(
        !args
            .iter()
            .any(|arg| arg == "stack" || arg == "--limit" || arg == "--html")
    );
}

#[test]
fn camera_metadata_cancel_retires_lane_and_drops_old_delivery() {
    let ctx = egui::Context::default();
    let mut state = CameraMetadata {
        token: 7,
        target: Some(BracketTarget {
            epoch: 2,
            directory: "bracket".into(),
            frames: vec![FrameFile {
                path: "current.ARW".into(),
                bytes: 1,
            }],
            output: "outside".into(),
        }),
        ..Default::default()
    };
    state.work = Some(Work {
        token: 7,
        epoch: 2,
        task: jobs::spawn_task("metadata-cancel-fixture", |_| {
            bail!("discard this completion")
        }),
    });
    state.cancel();
    assert!(
        state.work.is_some(),
        "Do not free a lane before the owned worker retires"
    );
    assert_ne!(state.token, 7);
    let start = std::time::Instant::now();
    while state.work.is_some() && start.elapsed() < Duration::from_secs(5) {
        state.poll(&ctx);
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(state.work.is_none() && state.result.is_none() && state.error.is_none());
}

#[test]
fn agent_metadata_returns_the_exact_saved_report_and_refuses_changed_source() {
    let dir = tempfile::tempdir().unwrap();
    let captures = dir.path().join("captures");
    fs::create_dir(&captures).unwrap();
    let source = captures.join("metadata & source.ARW");
    let frame = FrameFile {
        path: source.clone(),
        bytes: 4,
    };
    let output = dir.path().join("reports");
    fs::write(&source, b"test").unwrap();
    let payload = read_agent_report_using(
        frame.clone(),
        output.clone(),
        &AtomicBool::new(false),
        |source, json| Ok(child("success", source, json)),
    )
    .unwrap();
    let saved: Value =
        serde_json::from_slice(&fs::read(payload["reports"]["json"].as_str().unwrap()).unwrap())
            .unwrap();
    assert_eq!(payload["report"], saved);
    assert_eq!(payload["source"], json!(fs::canonicalize(&source).unwrap()));
    assert_eq!(
        payload["source_identity"],
        saved["frames"][0]["file_identity"]
    );
    assert_eq!(
        payload["report"]["frames"][0]["optical"]["facts"]["distortion"]["table"]["samples"],
        json!([
            0, -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15
        ])
    );
    for kind in ["json", "log"] {
        let path = Path::new(payload["reports"][kind].as_str().unwrap());
        assert!(path.is_file());
        assert!(!path.starts_with(&captures));
    }
    assert_eq!(fs::read(&source).unwrap(), b"test");
    let error = read_agent_report_using(
        frame.clone(),
        output.clone(),
        &AtomicBool::new(false),
        |source, json| Ok(child("mutate", source, json)),
    )
    .unwrap_err();
    assert!(format!("{error:#}").contains("Source changed"));
    let error = read_agent_report_using(frame, output, &AtomicBool::new(true), |_, _| {
        panic!("pre-cancelled agent read must not launch")
    })
    .unwrap_err();
    assert!(format!("{error:#}").contains("cancelled"));
}

#[test]
fn agent_metadata_refuses_oversized_inline_report_with_saved_paths() {
    let source = PathBuf::from("source.ARW");
    let stamp = SourceStamp {
        bytes: 4,
        modified_ns: None,
    };
    let mut full_report = report(&source, &stamp);
    let summary = parse_report(&full_report, &source, &stamp).unwrap();
    full_report["extra"] = json!("x".repeat(MAX_AGENT_REPORT_BYTES));
    let inspection = Inspection {
        summary,
        report: full_report,
        source,
        stamp,
        json: PathBuf::from("saved/camera-metadata.json"),
    };
    let error = format!("{:#}", agent_report_payload(inspection).unwrap_err());
    assert!(error.contains("exceeds 2 MiB"));
    assert!(error.contains("camera-metadata.json") && error.contains("metadata.log"));
}

fn with_grid(frame: &mut Value, value: u32) {
    frame["status"] = json!("present");
    frame["metadata"] = json!({"model":"ILCE-7CM2","software":"fixture","coarse_focus_position":56+value,
        "scalars_raw":[100+value,1000+value,0],"section_sequences_agree":true,
        "grid":{"width":33,"height":23,"record_count":759,"records":(0..759).map(|i|json!({"value_bits":i,"signed_display":i,"flags":[0,32]})).collect::<Vec<_>>()}});
}

#[test]
fn bracket_metadata_reads_once_and_selection_uses_the_cached_frame() {
    let dir = tempfile::tempdir().unwrap();
    let captures = dir.path().join("captures");
    fs::create_dir(&captures).unwrap();
    let mut frames = Vec::new();
    for name in ["a.ARW", "b.ARW"] {
        let path = captures.join(name);
        fs::write(&path, b"test").unwrap();
        frames.push(FrameFile { path, bytes: 4 });
    }
    let target = BracketTarget {
        epoch: 4,
        directory: captures.clone(),
        frames,
        output: dir.path().join("metadata"),
    };
    let launched = AtomicUsize::new(0);
    let result = inspect_bracket_using(&target, &AtomicBool::new(false), |source, json| {
        launched.fetch_add(1, Ordering::Relaxed);
        Ok(child("success", source, json))
    })
    .unwrap();
    assert_eq!(result.view.frame(0).unwrap().values[2], Some(1000.0));
    assert_eq!(result.view.frame(1).unwrap().values[2], Some(1001.0));
    assert_eq!(
        result
            .view
            .frame(1)
            .unwrap()
            .grid
            .as_ref()
            .unwrap()
            .cells
            .len(),
        759
    );
    assert!(result.view.frame(2).is_none());
    assert_eq!(launched.load(Ordering::Relaxed), 1);
    assert!(!result.json.with_extension("html").exists());
    let mut state = CameraMetadata {
        target: Some(target.clone()),
        result: Some(result),
        ..Default::default()
    };
    state.open_bracket(
        4,
        captures.clone(),
        target.frames.clone(),
        dir.path().join("new-output"),
        &egui::Context::default(),
    );
    assert!(state.result.is_some() && state.work.is_none() && state.pending.is_none());
    let ctx = egui::Context::default();
    for selected in [0, 1] {
        let output = ctx.run(egui::RawInput::default(), |ctx| {
            assert!(state.show(ctx, selected).is_none());
        });
        assert!(
            !output.shapes.is_empty(),
            "Native panel should paint the actual selected-frame cache"
        );
        assert_eq!(
            state
                .result
                .as_ref()
                .unwrap()
                .view
                .frame(selected)
                .unwrap()
                .values[2],
            Some(1000.0 + selected as f64)
        );
        assert!(
            state.work.is_none(),
            "Changing selection must not launch another reader"
        );
    }
    assert!(!state.is_loading());
    assert_eq!(
        state.target.as_ref().unwrap().output,
        dir.path().join("new-output/metadata")
    );
    state.refresh();
    assert!(state.is_loading());
    assert_eq!(
        state.pending.as_ref().unwrap().target.output,
        dir.path().join("new-output/metadata")
    );
    assert!(state.result.is_none());
    state.reset();
    let mut changed = target.clone();
    changed.epoch += 1;
    assert!(!target.same_sources(&changed));
    changed = target.clone();
    changed.frames.reverse();
    assert!(!target.same_sources(&changed));
}

#[test]
fn bracket_model_refuses_wrong_source_order_and_incomplete_grids() {
    let source = PathBuf::from("a.ARW");
    let stamp = SourceStamp {
        bytes: 4,
        modified_ns: None,
    };
    let mut valid = report(&source, &stamp);
    with_grid(&mut valid["frames"][0], 0);
    let sources = vec![(source, stamp)];
    assert!(view::BracketView::from_report(&valid, &sources).is_ok());
    for (pointer, value) in [
        ("/records_included", json!(false)),
        ("/file_count", json!(2)),
        ("/frames/0/index", json!(1)),
        ("/frames/0/path", json!("other.ARW")),
        ("/frames/0/file_identity/byte_length", json!(5)),
        ("/frames/0/metadata/grid/width", json!(0)),
        ("/frames/0/metadata/grid/height", json!(4097)),
        ("/frames/0/metadata/grid/record_count", json!(758)),
        (
            "/frames/0/metadata/grid/records/0/signed_display",
            json!(-1),
        ),
        ("/frames/0/metadata/grid/records/0/flags", json!([0, 256])),
        (
            "/frames/0/optical/facts/distortion/table/samples",
            json!([0, 1]),
        ),
        ("/comparison_breaks", json!([{"from_index":0,"to_index":1}])),
    ] {
        let mut invalid = valid.clone();
        *invalid.pointer_mut(pointer).unwrap() = value;
        assert!(
            view::BracketView::from_report(&invalid, &sources).is_err(),
            "{pointer}"
        );
    }
    let mut unavailable = valid;
    unavailable["frames"][0]["status"] = json!("malformed");
    unavailable["frames"][0]["metadata"] = Value::Null;
    let parsed = view::BracketView::from_report(&unavailable, &sources).unwrap();
    assert!(parsed.frame(0).unwrap().grid.is_none());
    assert_eq!(parsed.frame(0).unwrap().values, [None; 3]);
    assert!(
        !parsed.frame(0).unwrap().curves.is_empty(),
        "AF failure must not hide independent optical values"
    );
}

#[test]
fn reopening_cancelled_bracket_waits_for_retiring_worker_then_restarts() {
    let target = BracketTarget {
        epoch: 3,
        directory: "bracket".into(),
        frames: vec![FrameFile {
            path: "a.ARW".into(),
            bytes: 4,
        }],
        output: "outside".into(),
    };
    let mut state = CameraMetadata {
        token: 7,
        target: Some(target.clone()),
        work: Some(Work {
            token: 7,
            epoch: 3,
            task: jobs::spawn_task("metadata-retiring", |_| bail!("retiring")),
        }),
        ..Default::default()
    };
    state.cancel();
    // Use the same source identity; the cancelled worker must not count as a current cache.
    // poll may retire it immediately, so inspect the pending/current token rather than timing.
    state.open_bracket(
        3,
        target.directory,
        target.frames,
        "outside".into(),
        &egui::Context::default(),
    );
    assert!(
        state.pending.is_some()
            || state
                .work
                .as_ref()
                .is_some_and(|work| work.token == state.token)
    );
    state.reset();
}

#[test]
fn metadata_final_retirement_waits_for_the_running_child_and_worker() {
    let dir = tempfile::tempdir().unwrap();
    let ready = dir.path().join("child-ready");
    let log = dir.path().join("retirement.log");
    let ready_in = ready.clone();
    let finished = Arc::new(AtomicBool::new(false));
    let finished_in = Arc::clone(&finished);
    let target = BracketTarget {
        epoch: 7,
        directory: dir.path().to_owned(),
        frames: Vec::new(),
        output: dir.path().join("unused"),
    };
    let mut state = CameraMetadata {
        token: 3,
        pending: Some(Request { token: 3, target }),
        work: Some(Work {
            token: 3,
            epoch: 7,
            task: jobs::spawn_task("metadata-retire-fixture", move |cancelled| {
                let result = run_child(
                    child("wait", Path::new("unused.ARW"), &ready_in),
                    &cancelled,
                    &log,
                );
                // The owned child has already been reaped. Keep the completion
                // marker after a short finishing phase to catch cancel-only teardown.
                std::thread::sleep(Duration::from_millis(50));
                finished_in.store(true, Ordering::SeqCst);
                result?;
                bail!("fixture was expected to be cancelled")
            }),
        }),
        ..Default::default()
    };
    let started = std::time::Instant::now();
    while !ready.exists() && started.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(10));
    }
    assert!(
        ready.exists(),
        "Retirement must cancel an actually running child"
    );
    assert!(!finished.load(Ordering::SeqCst));
    state.retire();
    assert!(
        finished.load(Ordering::SeqCst),
        "Teardown returned before worker completion"
    );
    assert!(!state.is_loading());
    assert!(state.pending.is_none() && state.work.is_none());
}

#[test]
fn metadata_window_fits_small_viewport_and_keeps_title_below_native_chrome() {
    let source = PathBuf::from("a.ARW");
    let stamp = SourceStamp {
        bytes: 4,
        modified_ns: None,
    };
    let mut report = report(&source, &stamp);
    with_grid(&mut report["frames"][0], 0);
    let sources = vec![(source, stamp)];
    let view = view::BracketView::from_report(&report, &sources).unwrap();
    let mut panel = CameraMetadata {
        open: true,
        result: Some(BracketInspection {
            view,
            sources,
            json: "metadata.json".into(),
        }),
        ..Default::default()
    };
    let ctx = egui::Context::default();
    // A fresh small window and a large-to-small resize both use the real panel,
    // including its long metadata details, rather than only testing a rectangle helper.
    for size in [
        egui::vec2(1060.0, 720.0),
        egui::vec2(1440.0, 940.0),
        egui::vec2(1060.0, 720.0),
    ] {
        let screen = egui::Rect::from_min_size(egui::Pos2::ZERO, size);
        for _ in 0..3 {
            let _ = ctx.run(
                egui::RawInput {
                    screen_rect: Some(screen),
                    ..Default::default()
                },
                |ctx| {
                    assert!(panel.show(ctx, 0).is_none());
                },
            );
        }
        let window = ctx
            .memory(|memory| memory.area_rect(egui::Id::new("camera-metadata")))
            .expect("metadata window is present");
        let safe = metadata_window_safe_rect(&ctx);
        assert!(
            safe.expand(1.0).contains_rect(window),
            "window {window:?} escaped safe area {safe:?} at {size:?}"
        );
        let chrome = crate::window_chrome::dock_rect(screen);
        assert!(
            window.top() > chrome.bottom(),
            "title/close must remain below custom native chrome"
        );
        assert!(window.bottom() <= screen.bottom() - 15.0);
    }
}
