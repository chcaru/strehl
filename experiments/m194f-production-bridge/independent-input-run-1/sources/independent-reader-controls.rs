// M194f independently selected input controls. Private mutants confer no authority.
use super::*;
use std::time::{SystemTime, UNIX_EPOCH};

const INDEPENDENT_MANIFEST_SHA: &str =
    "f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299";
const INDEPENDENT_GATE_SHA: &str =
    "706462ad18a5a3846cadd99e1ef24d6b92b77e064df2e34cbe72e45907fc06a6";
const INDEPENDENT_FLOAT_SHA: &str =
    "4bd57b896be0b68c42fb1384a468a4f29cc54139a18a046a678dd97bad408217";
const INDEPENDENT_RESULT_SHA: &str =
    "8901be629a789d2959482baed15bef3e8cf23ba5f13418f66afdfb9fbf8bacdd";

fn independent_repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

fn independent_e() -> PathBuf {
    independent_repo().join("experiments/m194e-joint-pupil")
}

struct IndependentAudit {
    root: PathBuf,
    checks: Vec<Value>,
}

impl IndependentAudit {
    fn new(label: &str) -> Self {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = independent_repo()
            .join("experiments/m194f-production-bridge")
            .join(format!(
                "independent-input-{label}-{}-{stamp}",
                std::process::id()
            ));
        fs::create_dir(&root).unwrap();
        Self {
            root,
            checks: Vec::new(),
        }
    }

    fn record(&mut self, name: &str, pass: bool, evidence: Value) {
        let row = json!({"name": name, "pass": pass, "evidence": evidence});
        eprintln!("M194F_INDEPENDENT_INPUT {}", row);
        self.checks.push(row);
        fs::write(
            self.root.join("checks.json"),
            serde_json::to_vec_pretty(&self.checks).unwrap(),
        )
        .unwrap();
    }

    fn rejects<T>(&mut self, name: &str, result: Result<T>) {
        match result {
            Ok(_) => self.record(name, false, json!({"unexpected_acceptance": true})),
            Err(error) => self.record(name, true, json!({"refusal": format!("{error:#}")})),
        }
    }

    fn finish(self) {
        let pass = self.checks.iter().all(|row| row["pass"] == true);
        fs::write(self.root.join("result.json"), serde_json::to_vec_pretty(&json!({
            "schema": "m194f-independent-input-controls-v1", "pass": pass,
            "scope": "private API and genuine input parsing; no optical or TIFF quality authority",
            "check_count": self.checks.len(), "checks": self.checks,
        })).unwrap()).unwrap();
        assert!(
            pass,
            "independent input controls failed; retained at {}",
            self.root.display()
        );
    }
}

fn independent_records() -> (Value, Value, Value) {
    let e = independent_e();
    let manifest = read_json_bound(
        &e.join("cfa-emission-1/manifest.json"),
        INDEPENDENT_MANIFEST_SHA,
    )
    .unwrap();
    let gate = read_json_bound(
        &e.join("independent-cfa-verification-1/cfa-commission.json"),
        INDEPENDENT_GATE_SHA,
    )
    .unwrap();
    let result = read_json_bound(
        &e.join("independent-cfa-verification-1/result.json"),
        INDEPENDENT_RESULT_SHA,
    )
    .unwrap();
    (manifest, gate, result)
}

#[test]
fn m194f_independent_bounded_json_and_payload() {
    let mut audit = IndependentAudit::new("bounded");
    let exact = audit.root.join("exact.cfa");
    let bytes: Vec<u8> = (0..6144).map(|i| (i % 251) as u8).collect();
    fs::write(&exact, &bytes).unwrap();
    audit.record(
        "exact-cfa-limit-buffer",
        read_bounded(&exact, 6144).unwrap() == bytes,
        json!({"bytes": 6144}),
    );
    let appended = audit.root.join("appended.cfa");
    let mut larger = bytes.clone();
    larger.push(19);
    fs::write(&appended, &larger).unwrap();
    audit.rejects("appended-cfa-bounded-read", read_bounded(&appended, 6144));

    let limit = 1_048_576;
    let mut exact_json = br#"{"valid":[0,false,null,{"nested":"ok"}]}"#.to_vec();
    exact_json.resize(limit, b' ');
    let json_path = audit.root.join("exact-limit.json");
    fs::write(&json_path, &exact_json).unwrap();
    let parsed = read_json_bound(&json_path, &digest(&exact_json)).unwrap();
    audit.record(
        "exact-json-limit-valid",
        parsed["valid"][3]["nested"] == "ok",
        json!({"bytes": limit}),
    );
    exact_json.push(b' ');
    fs::write(&json_path, &exact_json).unwrap();
    audit.rejects(
        "rehash-oversize-json",
        read_json_bound(&json_path, &digest(&exact_json)),
    );

    for (name, raw) in [
        ("duplicate-root", r#"{"same":1,"same":1}"#),
        (
            "duplicate-deep-array-map",
            r#"{"a":[{"hash":"a","hash":"b"}]}"#,
        ),
        ("trailing-json", r#"{"a":1}{"b":2}"#),
        ("nonfinite-literal", r#"{"a":NaN}"#),
        ("infinite-exponent", r#"{"a":1e999}"#),
        ("truncated-json", r#"{"a":[1,2"#),
    ] {
        let path = audit.root.join(format!("{name}.json"));
        fs::write(&path, raw).unwrap();
        audit.rejects(name, read_json_bound(&path, &digest(raw.as_bytes())));
    }
    fs::write(&json_path, b"{}").unwrap();
    audit.rejects(
        "wrong-json-hash",
        read_json_bound(&json_path, &"0".repeat(64)),
    );
    audit.rejects("malformed-json-hash", read_json_bound(&json_path, "abc"));
    audit.rejects(
        "directory-as-json",
        read_json_bound(&audit.root, &"0".repeat(64)),
    );
    audit.finish();
}

#[test]
fn m194f_independent_gate_and_child_semantics() {
    let mut audit = IndependentAudit::new("authority");
    let (_, gate, result) = independent_records();
    audit.record(
        "genuine-gate-validator",
        validate_gate(&gate, INDEPENDENT_MANIFEST_SHA, INDEPENDENT_FLOAT_SHA).is_ok(),
        Value::Null,
    );
    audit.record(
        "genuine-child-validator",
        validate_verification(
            &result,
            &gate,
            INDEPENDENT_MANIFEST_SHA,
            INDEPENDENT_FLOAT_SHA,
        )
        .is_ok(),
        Value::Null,
    );
    let e = independent_e();
    audit.record(
        "complete-genuine-load",
        BridgeInputs::load(
            &e.join("cfa-emission-1/manifest.json"),
            INDEPENDENT_MANIFEST_SHA,
            &e.join("independent-cfa-verification-1/cfa-commission.json"),
            INDEPENDENT_GATE_SHA,
        )
        .is_ok(),
        Value::Null,
    );

    for (name, pointer, value) in [
        ("gate-schema", "/schema", json!("m194b-known-scene-v1")),
        ("gate-status", "/status", json!("UNCOMMISSIONED")),
        ("gate-sample-count", "/sample_count", json!(15359)),
        ("gate-float-sample-type", "/sample_count", json!(15360.0)),
        ("gate-bool-sample-type", "/sample_count", json!(true)),
        (
            "gate-manifest-binding",
            "/manifest/sha256",
            json!("0".repeat(64)),
        ),
        (
            "gate-float-binding",
            "/float_commission/sha256",
            json!("0".repeat(64)),
        ),
        (
            "gate-scope",
            "/scope",
            json!("all optics and production quality passed"),
        ),
    ] {
        let mut changed = gate.clone();
        *changed.pointer_mut(pointer).unwrap() = value;
        audit.rejects(
            name,
            validate_gate(&changed, INDEPENDENT_MANIFEST_SHA, INDEPENDENT_FLOAT_SHA),
        );
    }
    for (name, pointer, value) in [
        ("child-schema", "/schema", json!("m194e-fixture-v1")),
        ("child-status", "/status", json!("PASS_FIXTURE_READER_ONLY")),
        ("child-fixture", "/fixture_only", json!(true)),
        ("child-fixture-integer", "/fixture_only", json!(0)),
        ("child-count", "/sample_count", json!(15359)),
        ("child-count-float", "/sample_count", json!(15360.0)),
        (
            "child-manifest-binding",
            "/externally_trusted_manifest_sha256",
            json!("0".repeat(64)),
        ),
        (
            "child-float-binding",
            "/externally_trusted_float_commission_sha256",
            json!("0".repeat(64)),
        ),
        ("child-source-changed", "/source_unchanged", json!(false)),
        ("child-source-boolean-type", "/source_unchanged", json!(1)),
        ("child-source-before-missing", "/source_before", json!({})),
    ] {
        let mut changed = result.clone();
        *changed.pointer_mut(pointer).unwrap() = value;
        audit.rejects(
            name,
            validate_verification(
                &changed,
                &gate,
                INDEPENDENT_MANIFEST_SHA,
                INDEPENDENT_FLOAT_SHA,
            ),
        );
    }
    for (name, field) in [
        ("gate-missing-child", "independent_verification"),
        ("gate-missing-status", "status"),
    ] {
        let mut changed = gate.clone();
        changed.as_object_mut().unwrap().remove(field);
        audit.rejects(
            name,
            validate_gate(&changed, INDEPENDENT_MANIFEST_SHA, INDEPENDENT_FLOAT_SHA),
        );
    }
    let mut extra_gate = gate.clone();
    extra_gate["candidate_authority"] = json!(true);
    audit.rejects(
        "gate-unknown-key",
        validate_gate(&extra_gate, INDEPENDENT_MANIFEST_SHA, INDEPENDENT_FLOAT_SHA),
    );
    let mut extra_result = result.clone();
    extra_result["candidate_authority"] = json!(true);
    audit.rejects(
        "child-unknown-key",
        validate_verification(
            &extra_result,
            &gate,
            INDEPENDENT_MANIFEST_SHA,
            INDEPENDENT_FLOAT_SHA,
        ),
    );
    let mut missing_sources = result.clone();
    missing_sources["source_before"]
        .as_object_mut()
        .unwrap()
        .remove("model.py");
    missing_sources["source_after"]
        .as_object_mut()
        .unwrap()
        .remove("model.py");
    audit.rejects(
        "child-coherent-omitted-source",
        validate_verification(
            &missing_sources,
            &gate,
            INDEPENDENT_MANIFEST_SHA,
            INDEPENDENT_FLOAT_SHA,
        ),
    );
    // Pure schema validates hash syntax/key closure; actual current-file binding
    // is a separate consumed boundary. Do not claim private JSON is authority.
    let mut bindings = Bindings::default();
    let model = independent_e().join("model.py");
    let model_bytes = fs::read(&model).unwrap();
    audit.record(
        "actual-source-binding-companion",
        bindings
            .read(
                &model,
                &digest(&model_bytes),
                Some(model_bytes.len() as u64),
                JSON_LIMIT,
            )
            .is_ok(),
        Value::Null,
    );
    audit.rejects(
        "actual-source-false-hash",
        bindings.read(
            &model,
            &"0".repeat(64),
            Some(model_bytes.len() as u64),
            JSON_LIMIT,
        ),
    );
    audit.finish();
}

#[test]
fn m194f_independent_manifest_semantics() {
    let mut audit = IndependentAudit::new("manifest");
    let (manifest, _, _) = independent_records();
    audit.record(
        "genuine-manifest-validator",
        validate_manifest(&manifest).is_ok(),
        Value::Null,
    );
    for (name, pointer, value) in [
        ("manifest-schema", "/schema", json!("m194b-known-scene-v1")),
        ("manifest-status", "/status", json!("PASS")),
        ("manifest-index-bool", "/frames/0/index", json!(false)),
        ("manifest-index-float", "/frames/2/index", json!(2.0)),
        ("manifest-duplicate-index", "/frames/3/index", json!(2)),
        ("manifest-width-float", "/sensor/width", json!(64.0)),
        ("manifest-noise-integer", "/sensor/noise", json!(0)),
        ("manifest-noise-on", "/sensor/noise", json!(true)),
        ("manifest-cfa", "/sensor/cfa", json!("GRBG")),
        ("manifest-origin", "/sensor/active_origin", json!([2, 0])),
        ("manifest-black", "/sensor/black", json!(0)),
        ("manifest-white", "/sensor/white", json!(65535)),
        ("manifest-gain", "/sensor/gain_dn_per_e", json!(0.5)),
        ("manifest-rounder", "/sensor/rounding", json!("half-up")),
        ("manifest-size", "/frames/1/cfa/bytes", json!(6143)),
        ("manifest-size-float", "/frames/1/cfa/bytes", json!(6144.0)),
        ("manifest-dtype", "/frames/1/cfa/dtype", json!(">u2")),
        (
            "manifest-shape-bool",
            "/frames/1/cfa/shape",
            json!([true, 64]),
        ),
        (
            "manifest-shape-swapped",
            "/frames/1/cfa/shape",
            json!([64, 48]),
        ),
        (
            "manifest-transform",
            "/frames/2/forward_similarity/translation",
            json!([0.5, 0.0]),
        ),
        (
            "manifest-signed-focus",
            "/frames/1/inverse_focus",
            json!(-0.625),
        ),
        (
            "manifest-model",
            "/ray_model/visibility",
            json!("separately-blurred-means"),
        ),
        (
            "manifest-diffraction",
            "/ray_model/diffraction",
            json!(true),
        ),
        (
            "manifest-scalar-unit-dtype",
            "/frames/1/expected_scalar/dtype",
            json!("<u2"),
        ),
    ] {
        let mut changed = manifest.clone();
        *changed.pointer_mut(pointer).unwrap() = value;
        audit.rejects(name, validate_manifest(&changed));
    }
    for (name, value) in [
        ("manifest-null", Value::Null),
        ("manifest-array", json!([])),
        ("manifest-string", json!("PASS")),
    ] {
        audit.rejects(name, validate_manifest(&value));
    }
    let mut swapped = manifest.clone();
    swapped["sensor"]["width"] = json!(48);
    swapped["sensor"]["height"] = json!(64);
    audit.rejects(
        "manifest-same-count-wrong-geometry",
        validate_manifest(&swapped),
    );
    let mut missing = manifest.clone();
    missing["frames"].as_array_mut().unwrap().pop();
    audit.rejects("manifest-missing-frame", validate_manifest(&missing));
    let mut reordered = manifest.clone();
    reordered["frames"].as_array_mut().unwrap().swap(1, 3);
    audit.rejects(
        "manifest-reordered-original-indices",
        validate_manifest(&reordered),
    );
    let mut unknown = manifest.clone();
    unknown["sensor"]["iso"] = json!(160);
    audit.rejects("manifest-unknown-sensor-key", validate_manifest(&unknown));
    let mut missing_source = manifest.clone();
    missing_source["producer"]["sources"]
        .as_object_mut()
        .unwrap()
        .remove("experiments/m194e-joint-pupil/model.py");
    audit.rejects(
        "manifest-missing-producer-source",
        validate_manifest(&missing_source),
    );
    for (name, path) in [
        ("path-parent", "../frame-00.cfa"),
        ("path-absolute", "C:/frame-00.cfa"),
        ("path-drive-relative", "C:frame-00.cfa"),
        ("path-unc", "//server/share/frame-00.cfa"),
        ("path-backslash-parent", "..\\frame-00.cfa"),
        ("path-empty", ""),
        ("path-embedded-parent", "safe/../../frame-00.cfa"),
    ] {
        audit.rejects(
            name,
            relative_path(&independent_e().join("cfa-emission-1"), path),
        );
    }
    audit.record(
        "valid-nested-relative-companion",
        relative_path(
            &independent_e().join("cfa-emission-1"),
            "input/primary/frame-00-scalar.npy",
        )
        .is_ok(),
        Value::Null,
    );
    audit.finish();
}

fn independent_copy_inputs(root: &Path) -> (PathBuf, PathBuf) {
    let e = independent_e();
    let original = e.join("cfa-emission-1");
    let (manifest, _, _) = independent_records();
    let bundle = root.join("bundle");
    let authority = root.join("authority");
    fs::create_dir(&bundle).unwrap();
    fs::create_dir(&authority).unwrap();
    fs::copy(original.join("manifest.json"), bundle.join("manifest.json")).unwrap();
    let mut names = vec![
        manifest["producer"]["emission_receipt"]["path"]
            .as_str()
            .unwrap()
            .to_owned(),
    ];
    for frame in manifest["frames"].as_array().unwrap() {
        for key in [
            "cfa",
            "expected_cfa",
            "expected_scalar",
            "numerical_receipt",
        ] {
            names.push(frame[key]["path"].as_str().unwrap().to_owned());
        }
    }
    for name in names {
        let destination = bundle.join(&name);
        fs::create_dir_all(destination.parent().unwrap()).unwrap();
        fs::copy(original.join(name), destination).unwrap();
    }
    fs::copy(
        e.join("independent-cfa-verification-1/cfa-commission.json"),
        authority.join("cfa-commission.json"),
    )
    .unwrap();
    fs::copy(
        e.join("independent-cfa-verification-1/result.json"),
        authority.join("result.json"),
    )
    .unwrap();
    (
        bundle.join("manifest.json"),
        authority.join("cfa-commission.json"),
    )
}

#[test]
fn m194f_independent_relocated_chain_and_live_corruption() {
    let mut audit = IndependentAudit::new("chain");
    let (manifest, gate) = independent_copy_inputs(&audit.root);
    let load = || {
        BridgeInputs::load(
            &manifest,
            INDEPENDENT_MANIFEST_SHA,
            &gate,
            INDEPENDENT_GATE_SHA,
        )
    };
    audit.record(
        "unchanged-relocated-genuine-chain",
        load().is_ok(),
        Value::Null,
    );
    audit.rejects(
        "unregistered-external-manifest",
        BridgeInputs::load(&manifest, &"0".repeat(64), &gate, INDEPENDENT_GATE_SHA),
    );
    audit.rejects(
        "unregistered-external-gate",
        BridgeInputs::load(&manifest, INDEPENDENT_MANIFEST_SHA, &gate, &"0".repeat(64)),
    );
    let cfa = manifest.parent().unwrap().join("frame-03.cfa");
    let original = fs::read(&cfa).unwrap();
    let mut changed = original.clone();
    changed[37] ^= 1;
    fs::write(&cfa, &changed).unwrap();
    audit.rejects("same-length-copied-cfa-corruption", load());
    fs::write(&cfa, &original).unwrap();
    audit.record("restored-cfa-valid-companion", load().is_ok(), Value::Null);
    let child = gate.parent().unwrap().join("result.json");
    let child_original = fs::read(&child).unwrap();
    let mut child_value: Value = serde_json::from_slice(&child_original).unwrap();
    child_value["fixture_only"] = json!(true);
    let child_changed = serde_json::to_vec(&child_value).unwrap();
    fs::write(&child, &child_changed).unwrap();
    audit.rejects("copied-child-substitution-old-gate", load());
    let gate_original = fs::read(&gate).unwrap();
    let mut gate_value: Value = serde_json::from_slice(&gate_original).unwrap();
    gate_value["independent_verification"]["sha256"] = json!(digest(&child_changed));
    fs::write(&gate, serde_json::to_vec(&gate_value).unwrap()).unwrap();
    audit.rejects("rehashed-child-and-gate-old-external-pin", load());
    let revised_gate_sha = digest(&fs::read(&gate).unwrap());
    audit.rejects(
        "rehashed-child-and-untrusted-new-external-pin",
        BridgeInputs::load(
            &manifest,
            INDEPENDENT_MANIFEST_SHA,
            &gate,
            &revised_gate_sha,
        ),
    );
    fs::write(&gate, gate_original).unwrap();
    fs::write(&child, child_original).unwrap();
    audit.record("restored-entire-chain-valid", load().is_ok(), Value::Null);
    audit.finish();
}

fn independent_source_files(root: &Path) -> (Vec<PathBuf>, Vec<String>, Vec<Vec<u16>>) {
    let mut paths = Vec::new();
    let mut hashes = Vec::new();
    let mut decoded = Vec::new();
    for index in 0..5 {
        let bytes =
            fs::read(independent_e().join(format!("cfa-emission-1/frame-{index:02}.cfa"))).unwrap();
        let path = root.join(format!("private-frame-{index:02}.cfa"));
        fs::write(&path, &bytes).unwrap();
        decoded.push(
            bytes
                .chunks_exact(2)
                .map(|p| u16::from_le_bytes([p[0], p[1]]))
                .collect(),
        );
        hashes.push(digest(&bytes));
        paths.push(path);
    }
    (paths, hashes, decoded)
}

#[test]
fn m194f_independent_source_observer_and_second_file_read() {
    let mut audit = IndependentAudit::new("source");
    let (paths, hashes, expected) = independent_source_files(&audit.root);
    for mode in [
        ObserverMode::Off,
        ObserverMode::Count,
        ObserverMode::Placebo,
    ] {
        let source = BridgeSource::new(paths.clone(), hashes.clone(), mode).unwrap();
        for (position, index) in [3, 0, 4, 1, 2].into_iter().enumerate() {
            let frame = source.decode(index).unwrap();
            audit.record(
                &format!("{mode:?}-actual-frame-{index}"),
                frame.data == expected[index]
                    && frame.geometry() == PlaneGeometry::from_active(64, 48)
                    && frame.stride == 64
                    && frame.buffer_height == 48
                    && frame.active.x == 0
                    && frame.active.y == 0,
                json!({"position": position, "index": index, "samples": frame.data.len()}),
            );
            let mut counts = vec![0; 5];
            if mode == ObserverMode::Count {
                for seen in [3, 0, 4, 1, 2].into_iter().take(position + 1) {
                    counts[seen] = 1;
                }
            }
            audit.record(
                &format!("{mode:?}-identity-indexed-count-{position}"),
                source.success_counts() == counts
                    && source.hook_calls()
                        == if mode == ObserverMode::Off {
                            0
                        } else {
                            position + 1
                        },
                json!({"counts": source.success_counts(), "hooks": source.hook_calls()}),
            );
        }
        for index in [2, 1, 4, 0, 3] {
            assert_eq!(source.decode(index).unwrap().data, expected[index]);
        }
        audit.record(
            &format!("{mode:?}-second-complete-pass"),
            source.success_counts() == vec![if mode == ObserverMode::Count { 2 } else { 0 }; 5]
                && source.hook_calls() == if mode == ObserverMode::Off { 0 } else { 10 },
            json!({"counts": source.success_counts(), "hooks": source.hook_calls()}),
        );
        audit.rejects(&format!("{mode:?}-out-of-range-index"), source.decode(5));
    }
    let source = BridgeSource::new(paths.clone(), hashes.clone(), ObserverMode::Count).unwrap();
    assert_eq!(source.decode(3).unwrap().data, expected[3]);
    let original = fs::read(&paths[3]).unwrap();
    let mut changed = original.clone();
    changed[0] ^= 1;
    fs::write(&paths[3], &changed).unwrap();
    audit.rejects("second-read-actual-file-corruption", source.decode(3));
    audit.record(
        "failed-read-not-success",
        source.success_counts() == vec![0, 0, 0, 1, 0] && source.hook_calls() == 1,
        json!({"counts": source.success_counts(), "hooks": source.hook_calls()}),
    );
    let mut revised_hashes = hashes.clone();
    revised_hashes[3] = digest(&changed);
    let new_private =
        BridgeSource::new(paths.clone(), revised_hashes, ObserverMode::Count).unwrap();
    audit.record(
        "changed-private-source-live-with-private-binding",
        new_private.decode(3).unwrap().data != expected[3],
        json!({"scope": "private source API, not new optical admission"}),
    );
    fs::write(&paths[3], &original).unwrap();
    audit.record(
        "restored-second-read-companion",
        source.decode(3).unwrap().data == expected[3] && source.success_counts()[3] == 2,
        Value::Null,
    );

    for (name, bytes) in [
        (
            "short-rehashed-cfa",
            original[..original.len() - 1].to_vec(),
        ),
        (
            "appended-rehashed-cfa",
            [original.as_slice(), &[0]].concat(),
        ),
        ("below-black-rehashed-cfa", {
            let mut b = original.clone();
            b[..2].copy_from_slice(&511u16.to_le_bytes());
            b
        }),
        ("white-endpoint-rehashed-cfa", {
            let mut b = original.clone();
            b[..2].copy_from_slice(&15360u16.to_le_bytes());
            b
        }),
    ] {
        fs::write(&paths[3], &bytes).unwrap();
        let mut h = hashes.clone();
        h[3] = digest(&bytes);
        let source = BridgeSource::new(paths.clone(), h, ObserverMode::Count).unwrap();
        audit.rejects(name, source.decode(3));
        audit.record(
            &format!("{name}-no-success"),
            source.success_counts() == vec![0; 5] && source.hook_calls() == 0,
            Value::Null,
        );
    }
    fs::write(&paths[3], original).unwrap();
    audit.rejects(
        "short-source-count",
        BridgeSource::new(
            paths[..4].to_vec(),
            hashes[..4].to_vec(),
            ObserverMode::Count,
        ),
    );
    audit.rejects(
        "bad-source-hash-syntax",
        BridgeSource::new(paths, vec!["invalid".into(); 5], ObserverMode::Count),
    );
    audit.finish();
}

#[test]
fn m194f_independent_plan_and_actual_confidence_reread() {
    let mut audit = IndependentAudit::new("plan-reread");
    let (manifest_path, gate_path) = independent_copy_inputs(&audit.root);
    let inputs = BridgeInputs::load(
        &manifest_path,
        INDEPENDENT_MANIFEST_SHA,
        &gate_path,
        INDEPENDENT_GATE_SHA,
    )
    .unwrap();
    let environment = BTreeMap::from([
        ("STREHL_DEFECT".to_owned(), "off".to_owned()),
        ("STREHL_FIX_CA".to_owned(), "off".to_owned()),
        ("STREHL_FULLRES_GATHER".to_owned(), "1".to_owned()),
        ("STREHL_PYRAMID_WORKERS".to_owned(), "2".to_owned()),
        ("RAYON_NUM_THREADS".to_owned(), "2".to_owned()),
    ]);
    let settings = BridgeSettings {
        observer: ObserverMode::Count,
        confidence: true,
        exposure: 0,
    };
    let (domain, fit, plan) = prepare_bridge(&inputs, &settings, &environment).unwrap();
    audit.record("actual-recomputed-plan-valid", validate_plan(&plan, &plan).is_ok(),
        json!({"crop": plan["crop_quad"], "levels": plan["level_sizes"], "offset": plan["canonical_native_offset"]}));
    for (name, pointer, value) in [
        (
            "same-size-wrong-native-offset",
            "/canonical_native_offset/0",
            json!(plan["canonical_native_offset"][0].as_u64().unwrap() + 2),
        ),
        ("changed-exposure-plan", "/config/exposure_stops", json!(1)),
        ("changed-observer-plan", "/observer/mode", json!("off")),
        (
            "changed-effective-levels-plan",
            "/level_sizes/0/0",
            json!(plan["level_sizes"][0][0].as_u64().unwrap() + 1),
        ),
        (
            "changed-authority-plan",
            "/authority/manifest_sha256",
            json!("0".repeat(64)),
        ),
    ] {
        let mut saved = plan.clone();
        *saved.pointer_mut(pointer).unwrap() = value;
        let raw = serde_json::to_vec(&saved).unwrap();
        let path = audit.root.join(format!("{name}.json"));
        fs::write(&path, &raw).unwrap();
        let resealed = read_json_bound(&path, &digest(&raw)).unwrap();
        audit.rejects(name, validate_plan(&resealed, &plan));
    }
    let mut unknown = plan.clone();
    unknown["candidate_override"] = json!(true);
    audit.rejects("unknown-plan-key", validate_plan(&unknown, &plan));
    let mut stale = plan.clone();
    stale.as_object_mut().unwrap().remove("input_bindings");
    audit.rejects("missing-plan-source-binding", validate_plan(&stale, &plan));
    let mut changed_source = plan.clone();
    let key = changed_source["input_bindings"]
        .as_object()
        .unwrap()
        .keys()
        .next()
        .unwrap()
        .to_owned();
    changed_source["input_bindings"][&key]["sha256"] = json!("0".repeat(64));
    audit.rejects(
        "coherent-looking-plan-source-substitution",
        validate_plan(&changed_source, &plan),
    );

    let hashes: Vec<_> = inputs
        .manifest
        .frames
        .iter()
        .map(|f| f.cfa.sha256.clone())
        .collect();
    let healthy =
        BridgeSource::new(inputs.paths.clone(), hashes.clone(), ObserverMode::Count).unwrap();
    for index in [3, 0, 4, 1, 2] {
        healthy.decode(index).unwrap();
    }
    let luma = vec![3000.0; domain.analysis().pixels()];
    let confidence = confidence_pass(
        &healthy,
        &inputs.paths,
        domain,
        bridge_levels(),
        None,
        None,
        &luma,
        2,
    )
    .unwrap();
    audit.record("actual-confidence-second-decode-valid", healthy.success_counts() == vec![2; 5] && healthy.hook_calls() == 10
        && confidence.seen.iter().all(|n| *n == 5), json!({"counts": healthy.success_counts(), "hooks": healthy.hook_calls(), "sites": confidence.seen.len(),
        "first_pass": "manual decode companion; separate failed arm below uses the real fold"}));

    let mut failed = BridgeSource::new(inputs.paths.clone(), hashes, ObserverMode::Count).unwrap();
    failed.fail_on_attempt = Some((3, 2));
    let output = audit.root.join("refused-second-read-rgb.tif");
    let auxiliary = audit.root.join("refused-second-read-confidence.tif");
    let opts = bridge_options(output.clone(), settings, Some(auxiliary.clone())).unwrap();
    let result = run_bridge_source(&opts, &failed, domain, fit);
    let error = result
        .as_ref()
        .err()
        .map(|e| format!("{e:#}"))
        .unwrap_or_default();
    audit.record("actual-fold-confidence-second-attempt-refuses", result.is_err() && error.contains("index 3, attempt 2")
        && failed.success_counts()[3] == 1 && failed.attempt_counts()[3] == 2,
        json!({"error": error, "successes": failed.success_counts(), "attempts": failed.attempt_counts(), "hooks": failed.hook_calls(),
        "partial_rgb_exists": output.exists(), "partial_gray_exists": auxiliary.exists(), "scope": "private injected second-read fault, not intended render"}));
    audit.finish();
}
