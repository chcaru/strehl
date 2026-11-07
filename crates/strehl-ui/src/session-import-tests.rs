use super::*;
use serde_json::json;
fn write(root: &Path, name: &str, value: Value) {
    std::fs::write(root.join(name), serde_json::to_vec_pretty(&value).unwrap()).unwrap();
}
pub(super) fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let raw = root.join("unavailable-captures");
    let path = raw.join("one.arw");
    write(
        root,
        "session.json",
        json!({"spec":{"version":1,"mode":"combine","passes":[{"name":"First","directories":[raw]}],"primary_pass":null},
        "passes":[{"name":"First","directories":[raw],"global_range":{"start":0,"end":1},"segment_ranges":[{"start":0,"end":1}]}],
        "frames":[{"global_index":0,"pass_index":0,"segment_index":0,"pass_frame_index":0,"segment_frame_index":0,"path":path,"bytes":13,"modified_unix_nanos":null}]}),
    );
    write(
        root,
        "source-identities.json",
        json!([{"path":path,"bytes":13,"modified_unix_nanos":null,"sha256":"ab".repeat(32)}]),
    );
    write(
        root,
        "completed.json",
        json!({"schema":"strehl.session-completion.v1","frames":1,"passes":1,"outputs":1,"primary_pass":null}),
    );
    write(
        root,
        "render-report.json",
        json!({"build":"fixture","canvas":[0,0,2,2],"recipe":{"bands":7,"exponent":2.,"sharpen_per_octave":1.4,"gate":2.,"exposure_ev":0.,"memory_limit_gib":2.,"workers":1,"resampler":"CatmullRom"}}),
    );
    let image = strehl_edit::LinearImage {
        width: 4,
        height: 4,
        pixels: vec![0.25; 48],
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: Some(strehl_edit::DisplayBaseline {
            black: 0.,
            white: 1.,
            contrast: 0.55,
            exposure_gain: 1.,
        }),
        baked_recipe: None,
    };
    strehl_edit::save_linear_tiff(&root.join("master.tiff"), &image).unwrap();
    image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
        4,
        4,
        image::Rgb([32000, 24000, 16000]),
    )
    .save(root.join("photograph.tiff"))
    .unwrap();
    dir
}
#[test]
fn session_import_legacy_is_explicit_and_never_opens_missing_raws() {
    let dir = fixture();
    let run = load(dir.path(), &AtomicBool::new(false)).unwrap();
    assert!(!run.source.exists());
    assert_eq!(run.frames, 1);
    assert!(!run.imported.as_ref().unwrap().renderer_bound);
    assert!(
        run.imported
            .as_ref()
            .unwrap()
            .scope()
            .contains("original output binding unavailable")
    );
    let (reopened, progress) = crate::workspace_history::reopen(run.clone())
        .receiver
        .recv()
        .unwrap()
        .unwrap();
    assert_eq!(reopened.output, run.output);
    assert_eq!(progress.stage, crate::pipeline::Stage::Complete);
    std::fs::write(dir.path().join("photograph.tiff"), b"changed").unwrap();
    assert!(
        verify(
            &run.directory,
            run.imported.as_ref().unwrap(),
            &AtomicBool::new(false)
        )
        .is_err()
    );
}
#[test]
fn session_import_checks_renderer_receipt_and_aggregate_without_legacy_downgrade() {
    let dir = fixture();
    let root = dir.path();
    let cancelled = AtomicBool::new(false);
    write(
        root,
        "alignment.json",
        json!({"report":{"frames":1,"measured_edges":0,"anchor_component_cycle_rank":0,"passes":[{"pass_index":0,"frames":1,"placed":1,"refused":0}]}}),
    );
    let mut files = serde_json::Map::new();
    for name in ["master.tiff", "photograph.tiff", "render-report.json"] {
        files.insert(
            name.into(),
            json!(hash(&root.join(name), &cancelled).unwrap()),
        );
    }
    let mut session = serde_json::Map::new();
    for name in ["session.json", "source-identities.json", "alignment.json"] {
        session.insert(
            name.into(),
            json!(hash(&root.join(name), &cancelled).unwrap()),
        );
    }
    write(
        root,
        "render-completion.json",
        json!({"schema":"strehl.session-render-completion.v1","files":files,"session_files":session}),
    );
    assert!(load(root, &cancelled).is_err());
    let mut completion: Value =
        serde_json::from_slice(&std::fs::read(root.join("completed.json")).unwrap()).unwrap();
    completion["render_bindings"] = json!({"render-completion.json":hash(&root.join("render-completion.json"),&cancelled).unwrap()});
    write(root, "completed.json", completion);
    assert!(
        load(root, &cancelled)
            .unwrap()
            .imported
            .unwrap()
            .renderer_bound
    );
    std::fs::write(root.join("master.tiff"), b"wrong master").unwrap();
    assert!(load(root, &cancelled).is_err());
}
#[test]
fn session_import_rejects_census_canvas_cancel_and_path_escape() {
    for kind in ["census", "canvas", "cancel", "escape"] {
        let dir = fixture();
        let root = dir.path();
        let cancelled = AtomicBool::new(kind == "cancel");
        if kind == "census" {
            let mut value: Value =
                serde_json::from_slice(&std::fs::read(root.join("session.json")).unwrap()).unwrap();
            value["passes"][0]["global_range"]["end"] = json!(2);
            write(root, "session.json", value);
        }
        if kind == "canvas" {
            let mut value: Value =
                serde_json::from_slice(&std::fs::read(root.join("render-report.json")).unwrap())
                    .unwrap();
            value["canvas"][2] = json!(3);
            write(root, "render-report.json", value);
        }
        if kind == "escape" {
            let evidence = ImportedSession {
                imported_at: 0,
                renderer_bound: false,
                renderer_build: None,
                diagnostic_warnings: vec![],
                files: BTreeMap::from([("../outside".into(), "00".repeat(32))]),
            };
            assert!(verify(root, &evidence, &cancelled).is_err());
        } else {
            assert!(load(root, &cancelled).is_err(), "{kind}");
        }
    }
}
#[test]
fn session_import_catalog_failure_is_transactional_and_provenance_immutable() {
    let dir = fixture();
    let run = load(dir.path(), &AtomicBool::new(false)).unwrap();
    let mut catalog = crate::workspace_history::Catalog::default();
    let before = serde_json::to_vec(&catalog).unwrap();
    assert!(
        catalog
            .import_completed_run(Some(999), run.clone())
            .is_err()
    );
    assert_eq!(before, serde_json::to_vec(&catalog).unwrap());
    let id = catalog.import_completed_run(None, run.clone()).unwrap();
    assert_eq!(catalog.stack_for_run(&run.directory), Some(id));
    let mut changed = run;
    changed.imported.as_mut().unwrap().renderer_bound = true;
    assert!(catalog.add_revision(id, changed).is_err());
}

#[test]
fn session_import_mosaic_bindings_require_explicit_geometry_and_all_coverage_artifacts() {
    let dir = tempfile::tempdir().unwrap();
    let canonical = std::fs::canonicalize(dir.path()).unwrap();
    let root = canonical.as_path();
    let cancelled = AtomicBool::new(false);
    let mut output = serde_json::Map::new();
    for name in [
        "master.tiff",
        "photograph.tiff",
        "render-report.json",
        "sensor-master.tiff",
        "coverage.tiff",
        "join-confidence.tiff",
        "view-owner.tiff",
        "mosaic-report.json",
    ] {
        std::fs::write(root.join(name), name.as_bytes()).unwrap();
        output.insert(
            name.into(),
            json!(hash(&root.join(name), &cancelled).unwrap()),
        );
    }
    let mut session = serde_json::Map::new();
    for name in [
        "session.json",
        "source-identities.json",
        "mosaic-geometry.json",
    ] {
        std::fs::write(root.join(name), name.as_bytes()).unwrap();
        session.insert(
            name.into(),
            json!(hash(&root.join(name), &cancelled).unwrap()),
        );
    }
    let receipt = json!({"schema":"strehl.session-render-completion.v1", "geometry_kind":"mosaic", "files":output,"session_files":session});
    let check = |value: Value, mode| {
        write(root, "render-completion.json", value);
        let completion = json!({"render_bindings":{"render-completion.json":hash(&root.join("render-completion.json"),&cancelled).unwrap()}});
        bindings(
            root,
            &completion,
            &[String::new()],
            mode,
            &mut BTreeMap::new(),
            &cancelled,
        )
    };
    assert!(check(receipt.clone(), SessionMode::Mosaic).unwrap());
    assert!(check(receipt.clone(), SessionMode::Combine).is_err());
    for kind in [
        "absent",
        "wrong",
        "missing-coverage",
        "missing-geometry",
        "extra-file",
        "tampered-owner",
    ] {
        let mut wrong = receipt.clone();
        match kind {
            "absent" => {
                wrong.as_object_mut().unwrap().remove("geometry_kind");
            }
            "wrong" => wrong["geometry_kind"] = json!("session-alignment"),
            "missing-coverage" => {
                wrong["files"]
                    .as_object_mut()
                    .unwrap()
                    .remove("coverage.tiff");
            }
            "missing-geometry" => {
                wrong["session_files"]
                    .as_object_mut()
                    .unwrap()
                    .remove("mosaic-geometry.json");
            }
            "extra-file" => wrong["files"]["unclaimed.tiff"] = json!("00".repeat(32)),
            "tampered-owner" => wrong["files"]["view-owner.tiff"] = json!("00".repeat(32)),
            _ => unreachable!(),
        }
        assert!(check(wrong, SessionMode::Mosaic).is_err(), "{kind}");
    }
}

fn native_sensor_fixture(root: &Path) -> Value {
    write(
        root,
        "alignment.json",
        json!({"report":{"frames":1,"measured_edges":0,
        "anchor_component_cycle_rank":0,"passes":[{"pass_index":0,"frames":1,"placed":1,"refused":0}]}}),
    );
    std::fs::write(
        root.join("sensor-master.tiff"),
        b"signed native CFA fixture",
    )
    .unwrap();
    let mut report: Value =
        serde_json::from_slice(&std::fs::read(root.join("render-report.json")).unwrap()).unwrap();
    report["native_sensor_master"] = json!({
        "schema":"strehl.session-native-sensor-master.v1", "file":"sensor-master.tiff",
        "stage":"native-merge-before-demosaic", "cfa":"RGGB", "storage":"signed-f32",
        "reconstruction_applied":false, "photograph_has_later_reconstruction":true
    });
    report
}
fn publish_native_sensor_binding(root: &Path, names: &[&str], wrong_sensor_hash: bool) {
    let cancelled = AtomicBool::new(false);
    let mut output = serde_json::Map::new();
    for &name in names {
        let digest = if wrong_sensor_hash && name == "sensor-master.tiff" {
            "00".repeat(32)
        } else {
            hash(&root.join(name), &cancelled).unwrap()
        };
        output.insert(name.into(), json!(digest));
    }
    let mut session = serde_json::Map::new();
    for name in ["session.json", "source-identities.json", "alignment.json"] {
        session.insert(
            name.into(),
            json!(hash(&root.join(name), &cancelled).unwrap()),
        );
    }
    write(
        root,
        "render-completion.json",
        json!({
            "schema":"strehl.session-render-completion.v1", "geometry_kind":"session-alignment",
            "files":output,"session_files":session
        }),
    );
    let mut completion: Value =
        serde_json::from_slice(&std::fs::read(root.join("completed.json")).unwrap()).unwrap();
    completion["render_bindings"] = json!({"render-completion.json":hash(&root.join("render-completion.json"),&cancelled).unwrap()});
    write(root, "completed.json", completion);
}
#[test]
fn session_import_optional_native_sensor_is_bound_and_verified_on_reopen() {
    let dir = fixture();
    let root = dir.path();
    let report = native_sensor_fixture(root);
    write(root, "render-report.json", report);
    publish_native_sensor_binding(
        root,
        &[
            "master.tiff",
            "photograph.tiff",
            "render-report.json",
            "sensor-master.tiff",
        ],
        false,
    );
    let cancelled = AtomicBool::new(false);
    let run = load(root, &cancelled).unwrap();
    let provenance = run.imported.as_ref().unwrap();
    assert!(provenance.renderer_bound);
    assert_eq!(
        provenance.files["sensor-master.tiff"],
        hash(&root.join("sensor-master.tiff"), &cancelled).unwrap()
    );
    let (reopened, _) = crate::workspace_history::reopen(run.clone())
        .receiver
        .recv()
        .unwrap()
        .unwrap();
    assert_eq!(reopened.imported, run.imported);
    std::fs::write(root.join("sensor-master.tiff"), b"changed native values").unwrap();
    assert!(verify(&run.directory, provenance, &cancelled).is_err());
    assert!(load(root, &cancelled).is_err());
}
#[test]
fn session_import_native_sensor_rejects_untyped_unbound_missing_and_extra_artifacts() {
    for case in [
        "schema",
        "file",
        "stage",
        "cfa",
        "storage",
        "reconstructed",
        "untyped-bool",
        "missing-bool",
        "null",
        "missing-file",
        "unbound",
        "undeclared",
        "undeclared-unbound",
        "wrong-hash",
        "extra-file",
        "replaced-report",
        "legacy-unbound",
    ] {
        let dir = fixture();
        let root = dir.path();
        let mut report = native_sensor_fixture(root);
        let mut names = vec![
            "master.tiff",
            "photograph.tiff",
            "render-report.json",
            "sensor-master.tiff",
        ];
        match case {
            "schema" => report["native_sensor_master"]["schema"] = json!("unknown"),
            "file" => report["native_sensor_master"]["file"] = json!("../sensor-master.tiff"),
            "stage" => report["native_sensor_master"]["stage"] = json!("post-reconstruction"),
            "cfa" => report["native_sensor_master"]["cfa"] = json!("BGGR"),
            "storage" => report["native_sensor_master"]["storage"] = json!("uint16"),
            "reconstructed" => {
                report["native_sensor_master"]["reconstruction_applied"] = json!(true)
            }
            "untyped-bool" => {
                report["native_sensor_master"]["reconstruction_applied"] = json!("false")
            }
            "missing-bool" => {
                report["native_sensor_master"]
                    .as_object_mut()
                    .unwrap()
                    .remove("reconstruction_applied");
            }
            "null" => report["native_sensor_master"] = Value::Null,
            "unbound" => {
                names.pop();
            }
            "undeclared" => {
                report
                    .as_object_mut()
                    .unwrap()
                    .remove("native_sensor_master");
            }
            "undeclared-unbound" => {
                report
                    .as_object_mut()
                    .unwrap()
                    .remove("native_sensor_master");
                names.pop();
            }
            "extra-file" => {
                std::fs::write(root.join("unclaimed.tiff"), b"extra").unwrap();
                names.push("unclaimed.tiff");
            }
            "replaced-report" => {
                std::fs::write(root.join("unclaimed.tiff"), b"extra").unwrap();
                names[2] = "unclaimed.tiff";
            }
            "missing-file" | "wrong-hash" | "legacy-unbound" => {}
            _ => unreachable!(),
        }
        write(root, "render-report.json", report);
        if case != "legacy-unbound" {
            publish_native_sensor_binding(root, &names, case == "wrong-hash");
        }
        if case == "missing-file" {
            std::fs::remove_file(root.join("sensor-master.tiff")).unwrap();
        }
        assert!(load(root, &AtomicBool::new(false)).is_err(), "{case}");
    }
}
