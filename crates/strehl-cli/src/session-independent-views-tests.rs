use super::*;
use crate::session_cmd::Resources;
use crate::session_input::PassSpec;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

struct Fixture {
    root: PathBuf,
    session: ResolvedSession,
    identities: Vec<SourceIdentity>,
    child: PathBuf,
}
impl Fixture {
    fn new() -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let root = std::env::var_os("STREHL_TEST_TMP")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir)
            .join(format!(
                "strehl-independent-views-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
        std::fs::create_dir_all(&root).unwrap();
        let passes: Vec<_> = ["underside", "top"]
            .into_iter()
            .enumerate()
            .map(|(index, name)| {
                let directory = root.join(name);
                std::fs::create_dir(&directory).unwrap();
                std::fs::write(directory.join("one.ARW"), format!("original {index}")).unwrap();
                PassSpec {
                    name: name.into(),
                    directories: vec![directory],
                }
            })
            .collect();
        let session = SessionSpec {
            mode: SessionMode::IndependentViews,
            passes,
            primary_pass: None,
            ..SessionSpec::default()
        }
        .resolve_from(&root)
        .unwrap();
        let identities = session.hash_sources(true).unwrap();
        let child = root.join("view-02");
        std::fs::create_dir_all(child.join("focus/pass-01")).unwrap();
        let own = SessionSpec {
            passes: vec![session.spec.passes[1].clone()],
            ..SessionSpec::default()
        }
        .resolve_from(&root)
        .unwrap();
        write_json_new(&child.join("session.json"), &own).unwrap();
        write_json_new(&child.join("source-identities.json"), &&identities[1..]).unwrap();
        write_json_new(
            &child.join("calibration.json"),
            &json!([{"camera":"fixture"}]),
        )
        .unwrap();
        write_json_new(
            &child.join("render-report.json"),
            &json!({"mode":"combine","canvas":[1,2,4,3],
            "reference_pass":0,"development_reference_pass":0,"invalid_output_pixels":0}),
        )
        .unwrap();
        write_json_new(
            &child.join("alignment.json"),
            &json!({"report":{"geometry_plane_pixels":[16,12],
            "sensor_pixels_per_plane_pixel":2,"reference_frame":0,"binding_sha256":"fixture-binding"}}),
        )
        .unwrap();
        for name in ["photograph.tiff", "master.tiff"] {
            write_tiff(&child.join(name), [8, 6]);
        }
        let mut files = Vec::new();
        for name in [
            "ordinal.tiff",
            "width-frames.tiff",
            "flags.tiff",
            "usable.tiff",
            "raw-coverage.tiff",
            "focus-coverage.tiff",
            "source-rank-1.tiff",
        ] {
            let path = child.join("focus/pass-01").join(name);
            write_tiff(&path, [4, 3]);
            let mut binding = file_binding(&path).unwrap();
            binding["file"] = json!(name);
            files.push(binding);
        }
        write_json_new(&child.join("focus/pass-01/geometry.json"),&json!({
            "pass":0,"full_quad_geometry":[16,12],"origin_quad":[1,2],"dimensions":[4,3],
            "step_quad":[1,1],"ordinal_mapping":[{"ordinal":0,"global_index":0,"acquisition":0}],"files":files})).unwrap();
        write_json_new(
            &child.join("focus/focus-evidence.json"),
            &json!({"schema":"strehl.session-focus.v1","session":own,"sources":identities[1..],
                "alignment_binding":"fixture-binding", "passes":[read(&child.join("focus/pass-01/geometry.json")).unwrap()]}),
        )
        .unwrap();
        crate::session_reproducibility::publish_render_binding(&child).unwrap();
        write_json_new(&child.join("completed.json"),&json!({"schema":"strehl.session-completion.v1",
            "outputs":1,"passes":1,"frames":1,"render_bindings":{
                "render-completion.json":file_binding(&child.join("render-completion.json")).unwrap()["sha256"]}})).unwrap();
        Self {
            root,
            session,
            identities,
            child,
        }
    }
    fn entry(&self) -> Result<Value> {
        child_entry(&self.session, &self.identities, 1, &self.child)
    }
    fn mutate(&self, name: &str, edit: impl FnOnce(&mut Value)) {
        let path = self.child.join(name);
        let mut value = read(&path).unwrap();
        edit(&mut value);
        std::fs::write(path, serde_json::to_vec(&value).unwrap()).unwrap();
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.root);
    }
}
fn write_tiff(path: &Path, size: [u32; 2]) {
    let file = std::fs::File::create(path).unwrap();
    tiff::encoder::TiffEncoder::new(file)
        .unwrap()
        .write_image::<tiff::encoder::colortype::Gray8>(
            size[0],
            size[1],
            &vec![17; (size[0] * size[1]) as usize],
        )
        .unwrap();
}

#[test]
fn session_independent_views_preserve_local_gauges_and_global_source_mapping() {
    let f = Fixture::new();
    let entry = f.entry().unwrap();
    assert_eq!(entry["directory"], "view-02");
    assert_eq!(entry["source_indices"], json!([1]));
    assert_eq!(entry["source_ids"], json!([f.identities[1].sha256]));
    assert_eq!(entry["gauge"]["origin_sensor"], json!([2, 4]));
    assert_eq!(entry["gauge"]["focus_origin_sensor"], json!([2.5, 4.5]));
    assert_eq!(entry["gauge"]["dimensions"], json!([8, 6]));
    assert_eq!(entry["gauge"]["focus_dimensions"], json!([4, 3]));
    assert!(entry["relative_pose"].is_null() && entry["intrinsics"].is_null());
    assert!(entry["files"]["focus/pass-01/usable.tiff"]["sha256"].is_string());
}

#[test]
fn session_independent_views_refuse_changed_focus_gauge_or_original_order() {
    let f = Fixture::new();
    f.mutate("focus/pass-01/geometry.json", |v| {
        v["origin_quad"] = json!([2, 2])
    });
    assert!(f.entry().unwrap_err().to_string().contains("focus gauge"));
    let f = Fixture::new();
    f.mutate("source-identities.json", |v| {
        v[0]["sha256"] = json!("changed")
    });
    assert!(
        f.entry()
            .unwrap_err()
            .to_string()
            .contains("source identities")
    );
    let f = Fixture::new();
    f.mutate("focus/pass-01/geometry.json", |v| {
        v["ordinal_mapping"][0]["global_index"] = json!(1)
    });
    assert!(
        f.entry()
            .unwrap_err()
            .to_string()
            .contains("acquisition ordinals")
    );
}

#[test]
fn session_independent_views_refuse_missing_tampered_or_misdimensioned_maps() {
    let f = Fixture::new();
    std::fs::remove_file(f.child.join("focus/pass-01/usable.tiff")).unwrap();
    assert!(f.entry().is_err());
    let f = Fixture::new();
    write_tiff(&f.child.join("focus/pass-01/usable.tiff"), [3, 4]);
    assert!(
        f.entry()
            .unwrap_err()
            .to_string()
            .contains("dimensions differ")
    );
    let f = Fixture::new();
    f.mutate("focus/pass-01/geometry.json", |v| {
        v["files"][0]["sha256"] = json!("changed")
    });
    assert!(f.entry().unwrap_err().to_string().contains("focus binding"));
    let f = Fixture::new();
    write_tiff(&f.child.join("master.tiff"), [4, 12]);
    assert!(
        f.entry()
            .unwrap_err()
            .to_string()
            .contains("dimensions differ")
    );
    let f = Fixture::new();
    f.mutate("render-report.json", |v| v["unknown"] = json!(1));
    assert!(f.entry().unwrap_err().to_string().contains("image binding"));
}

fn args() -> StackArgs {
    StackArgs {
        manifest: "input.json".into(),
        out_dir: "result".into(),
        alignment: None,
        resources: Resources {
            memory_limit_gib: 4.0,
            threads: 2,
            cache: None,
            resampler: "catmull-rom".into(),
        },
        pyramid_gate: 2.0,
        pyramid_bands: 7,
        pyramid_exponent: 2.0,
        pyramid_sharpen: 1.4,
        exposure: 0.0,
        agreement_sigma: 4.0,
        binned: false,
        precision_weights: false,
        contribution_maps: false,
        focus_evidence: false,
        reproducibility: false,
        original_cfa_reconstruction: false,
        native_single: false,
        no_repeat_grouping: false,
        uncertainty_repeat_proposals: false,
        omit_acquisition: Vec::new(),
        only_pass: None,
    }
}

#[test]
fn session_independent_views_reject_shared_observation_options_and_primary() {
    validate_options(&args()).unwrap();
    for change in 0..7 {
        let mut a = args();
        match change {
            0 => a.precision_weights = true,
            1 => a.reproducibility = true,
            2 => a.original_cfa_reconstruction = true,
            3 => a.alignment = Some("shared.json".into()),
            4 => a.only_pass = Some(0),
            5 => a.binned = true,
            _ => a.contribution_maps = true,
        }
        assert!(validate_options(&a).is_err());
    }
    let mut spec = SessionSpec {
        mode: SessionMode::IndependentViews,
        passes: vec![PassSpec {
            name: "View".into(),
            directories: vec!["input".into()],
        }],
        ..SessionSpec::default()
    };
    spec.validate().unwrap();
    spec.primary_pass = Some(0);
    assert!(spec.validate().is_err());
    assert_eq!(
        serde_json::to_value(SessionMode::IndependentViews).unwrap(),
        "independent_views"
    );
}

#[test]
fn session_independent_view_progress_context_preserves_unequal_parent_ranges() {
    let fixture = Fixture::new();
    std::fs::write(
        fixture.session.passes[0].directories[0].join("two.ARW"),
        b"second original",
    )
    .unwrap();
    let session = fixture.session.spec.resolve_from(&fixture.root).unwrap();
    let first = view_progress_context(&session, 0);
    let second = view_progress_context(&session, 1);
    assert_eq!(first["source_offset"], 0);
    assert_eq!(first["source_count"], 2);
    assert_eq!(second["source_offset"], 2);
    assert_eq!(second["source_count"], 1);
    assert_eq!(second["parent_total"], 3);
    assert_eq!(second["index"], 1);
    assert_eq!(second["name"], "top");
}
