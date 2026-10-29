use super::*;
use serde_json::json;
fn write(root: &Path, name: &str, v: &Value) {
    std::fs::write(root.join(name), serde_json::to_vec_pretty(v).unwrap()).unwrap();
}
fn value(root: &Path, name: &str) -> Value {
    serde_json::from_slice(&std::fs::read(root.join(name)).unwrap()).unwrap()
}
fn digest(root: &Path, name: &str) -> String {
    hash(&root.join(name), &AtomicBool::new(false)).unwrap()
}
pub(crate) fn fixture() -> tempfile::TempDir {
    let temp = tempfile::tempdir().unwrap();
    let root = temp.path();
    let mut parent_passes = Vec::new();
    let mut resolved_passes = Vec::new();
    let mut frames = Vec::new();
    let mut ids = Vec::new();
    let mut views = Vec::new();
    let mut root_bindings = serde_json::Map::new();
    for i in 0..2 {
        let original = super::super::tests::fixture();
        let dir = format!("view-{:02}", i + 1);
        let child = root.join(&dir);
        std::fs::create_dir(&child).unwrap();
        for entry in std::fs::read_dir(original.path()).unwrap() {
            let entry = entry.unwrap();
            if entry.file_type().unwrap().is_file() {
                std::fs::copy(entry.path(), child.join(entry.file_name())).unwrap();
            }
        }
        let mut session = value(&child, "session.json");
        let name = format!("View {i}");
        session["spec"]["passes"][0]["name"] = json!(name);
        session["passes"][0]["name"] = json!(name);
        write(&child, "session.json", &session);
        let mut identities = value(&child, "source-identities.json");
        identities[0]["sha256"] = json!(if i == 0 {
            "ab".repeat(32)
        } else {
            "cd".repeat(32)
        });
        write(&child, "source-identities.json", &identities);
        parent_passes.push(session["spec"]["passes"][0].clone());
        let mut p = session["passes"][0].clone();
        p["global_range"] = json!({"start":i,"end":i+1});
        p["segment_ranges"] = json!([{"start":i,"end":i+1}]);
        resolved_passes.push(p);
        let mut f = session["frames"][0].clone();
        f["global_index"] = json!(i);
        f["pass_index"] = json!(i);
        frames.push(f);
        ids.push(identities[0].clone());
        let (x, y, w, h) = if i == 0 {
            (1u32, 2u32, 2u32, 3u32)
        } else {
            (3, 1, 3, 2)
        };
        let linear = strehl_edit::LinearImage {
            width: 2 * w,
            height: 2 * h,
            pixels: vec![0.25; (2 * w * 2 * h * 3) as usize],
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: Some(strehl_edit::DisplayBaseline {
                black: 0.,
                white: 1.,
                contrast: 0.55,
                exposure_gain: 1.,
            }),
            baked_recipe: None,
        };
        strehl_edit::save_linear_tiff(&child.join("master.tiff"), &linear).unwrap();
        image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
            2 * w,
            2 * h,
            image::Rgb([32000, 24000, 16000]),
        )
        .save(child.join("photograph.tiff"))
        .unwrap();
        let mut report = value(&child, "render-report.json");
        report["mode"] = json!("combine");
        report["canvas"] = json!([x, y, w, h]);
        report["reference_pass"] = json!(0);
        report["development_reference_pass"] = json!(0);
        report["invalid_output_pixels"] = json!(0);
        write(&child, "render-report.json", &report);
        write(
            &child,
            "alignment.json",
            &json!({"report":{"geometry_plane_pixels":[16,12],"sensor_pixels_per_plane_pixel":2,"reference_frame":0,"binding_sha256":"binding-fixture","frames":1,"measured_edges":0,"anchor_component_cycle_rank":0,"passes":[{"pass_index":0,"frames":1,"placed":1,"refused":0}]}}),
        );
        write(&child, "calibration.json", &json!({"fixture":true}));
        std::fs::create_dir_all(child.join("focus/pass-01")).unwrap();
        let mut maps = Vec::new();
        for leaf in [
            "ordinal.tiff",
            "width-frames.tiff",
            "flags.tiff",
            "usable.tiff",
            "raw-coverage.tiff",
            "focus-coverage.tiff",
            "source-rank-1.tiff",
        ] {
            let path = format!("focus/pass-01/{leaf}");
            image::GrayImage::from_pixel(w, h, image::Luma([1]))
                .save(child.join(&path))
                .unwrap();
            maps.push(json!({"file":leaf,"bytes":child.join(&path).metadata().unwrap().len(),"sha256":digest(&child,&path)}));
        }
        let focus = json!({"pass":0,"full_quad_geometry":[16,12],"origin_quad":[x,y],"dimensions":[w,h],"step_quad":[1,1],"ordinal_mapping":[{"ordinal":0,"global_index":0,"acquisition":0}],"files":maps});
        write(&child, "focus/pass-01/geometry.json", &focus);
        write(
            &child,
            "focus/focus-evidence.json",
            &json!({"schema":"strehl.session-focus.v1","session":session,"sources":identities,"alignment_binding":"binding-fixture","passes":[focus]}),
        );
        let output_bindings: serde_json::Map<String, Value> =
            ["master.tiff", "photograph.tiff", "render-report.json"]
                .into_iter()
                .map(|s| (s.into(), json!(digest(&child, s))))
                .collect();
        let session_bindings: serde_json::Map<String, Value> =
            ["session.json", "source-identities.json", "alignment.json"]
                .into_iter()
                .map(|s| (s.into(), json!(digest(&child, s))))
                .collect();
        write(
            &child,
            "render-completion.json",
            &json!({"schema":"strehl.session-render-completion.v1","geometry_kind":"session-alignment","files":output_bindings,"session_files":session_bindings}),
        );
        let render_sha = digest(&child, "render-completion.json");
        write(
            &child,
            "completed.json",
            &json!({"schema":"strehl.session-completion.v1","frames":1,"passes":1,"outputs":1,"primary_pass":null,"render_bindings":{"render-completion.json":render_sha}}),
        );
        let mut files = serde_json::Map::new();
        for leaf in [
            "session.json",
            "source-identities.json",
            "completed.json",
            "render-completion.json",
            "alignment.json",
            "calibration.json",
            "master.tiff",
            "photograph.tiff",
            "render-report.json",
            "focus/focus-evidence.json",
            "focus/pass-01/geometry.json",
        ] {
            files.insert(leaf.into(),json!({"bytes":child.join(leaf).metadata().unwrap().len(),"sha256":digest(&child,leaf)}));
        }
        for m in maps {
            let path = format!("focus/pass-01/{}", m["file"].as_str().unwrap());
            files.insert(path, json!({"bytes":m["bytes"],"sha256":m["sha256"]}));
        }
        views.push(json!({"index":i,"name":name,"directory":dir,"source_indices":[i],"source_ids":[identities[0]["sha256"]],"source_count":1,
            "render_completion_sha256":render_sha,"completed_sha256":digest(&child,"completed.json"),"alignment_sha256":digest(&child,"alignment.json"),
            "gauge":{"full_quad_geometry":[16,12],"origin_sensor":[2*x,2*y],"dimensions":[2*w,2*h],"step_sensor":[1,1],"reference_frame":0,"focus_origin_sensor":[2.*x as f64+0.5,2.*y as f64+0.5],"focus_dimensions":[w,h],"focus_step_sensor":[2,2]},
            "focus_semantics":"Local ordinal, not metric depth","relative_pose":null,"intrinsics":null,"files":files}));
        root_bindings.insert(format!("{dir}/render-completion.json"), json!(render_sha));
    }
    write(
        root,
        "session.json",
        &json!({"spec":{"version":1,"mode":"independent_views","passes":parent_passes,"primary_pass":null},"passes":resolved_passes,"frames":frames}),
    );
    write(root, "source-identities.json", &json!(ids));
    write(
        root,
        "bundle.json",
        &json!({"schema":"strehl.independent-views.v1","views":views,"source_count":2,"relative_pose":null,"intrinsics":null,"session_sha256":digest(root,"session.json"),"source_identities_sha256":digest(root,"source-identities.json")}),
    );
    let mut parent_recipe = value(&root.join("view-01"), "render-report.json")["recipe"].clone();
    parent_recipe["focus_evidence"] = json!(true);
    write(
        root,
        "render-report.json",
        &json!({"mode":"independent_views","view_bundle":"bundle.json","build":"view-fixture","recipe":parent_recipe}),
    );
    write(
        root,
        "completed.json",
        &json!({"schema":"strehl.session-completion.v1","pipeline":"independent-views","frames":2,"passes":2,"outputs":2,"primary_pass":null,"bundle_sha256":digest(root,"bundle.json"),"report_sha256":digest(root,"render-report.json"),"render_bindings":root_bindings}),
    );
    temp
}
#[test]
fn session_import_independent_views_preserves_distinct_gauges_and_both_outputs() {
    let temp = fixture();
    let run = super::super::load(temp.path(), &AtomicBool::new(false)).unwrap();
    assert_eq!(run.frames, 2);
    assert!(run.imported.as_ref().unwrap().renderer_bound);
    assert_eq!(
        run.settings.session.as_ref().unwrap().manifest.mode,
        SessionMode::IndependentViews
    );
    assert!(run.owns_output(&run.directory.join("view-02/photograph.tiff")));
    assert!(!run.owns_output(&run.directory.join("layer-02/photograph.tiff")));
    assert!(
        run.imported
            .unwrap()
            .files
            .contains_key("view-02/focus/pass-01/usable.tiff")
    );
}
#[test]
fn session_import_independent_views_rejects_gauge_identity_escape_and_changed_pixels() {
    for kind in ["gauge", "identity", "escape", "pixel", "missing", "cancel"] {
        let temp = fixture();
        let root = temp.path();
        let mut b = value(root, "bundle.json");
        match kind {
            "gauge" => b["views"][1]["gauge"]["focus_origin_sensor"] = json!([6., 2.]),
            "identity" => b["views"][1]["source_ids"] = json!(["ab".repeat(32)]),
            "escape" => {
                b["views"][1]["files"]["../view-01/master.tiff"] =
                    b["views"][1]["files"]["master.tiff"].clone()
            }
            "pixel" => std::fs::write(root.join("view-02/master.tiff"), b"wrong").unwrap(),
            "missing" => {
                b["views"][1]["files"]
                    .as_object_mut()
                    .unwrap()
                    .remove("focus/pass-01/usable.tiff");
            }
            "cancel" => {}
            _ => unreachable!(),
        }
        write(root, "bundle.json", &b);
        let mut c = value(root, "completed.json");
        c["bundle_sha256"] = json!(digest(root, "bundle.json"));
        write(root, "completed.json", &c);
        assert!(
            super::super::load(root, &AtomicBool::new(kind == "cancel")).is_err(),
            "{kind}"
        );
    }
}
