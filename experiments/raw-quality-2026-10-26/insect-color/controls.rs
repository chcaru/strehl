// Author-prepared actual-consumer falsifier; independent choice review precedes root run.
include!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../experiments/raw-quality-2026-10-26/insect-color/fixtures.rs"
));
use super::{Arm, Comparison, compare_generated};
use strehl_core::pyramid::{LevelSize, rb_own_guide_diagnostic as core};

mod independent {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-26/insect-color/independent-controls.rs"
    ));
}

fn error_guard(reference: &Score, candidate: &Score, ratio: f64) -> bool {
    candidate.rgb <= ratio * reference.rgb
        && candidate.green <= ratio * reference.green
        && candidate.chroma <= ratio * reference.chroma
}
fn flat_guard(canonical: &Score, uniform: &Score, candidate: &Score) -> bool {
    error_guard(canonical, candidate, 1.05) && error_guard(uniform, candidate, 1.10)
}
fn structured_guard(reference: &Score, candidate: &Score) -> bool {
    error_guard(reference, candidate, 1.05) && recovery_pass(reference, candidate)
}
fn focused_component_guard(reference: f64, candidate: f64) -> bool {
    reference >= 0.5 && candidate.clamp(0.0, 1.0) >= 0.90 * reference.min(1.0)
}
fn guard_commission() -> Value {
    let flat = truth_image(Scene::Flat);
    let good = score(Scene::Flat, &flat, INTERIOR);
    assert!(flat_guard(&good, &good, &good));
    let mut damaged = flat;
    for (p, v) in damaged.iter_mut().enumerate() {
        *v += 0.03
            * gaussian(
                p / 3 % (2 * crop().width),
                p / 3 / (2 * crop().width),
                p % 3,
            ) as f32;
    }
    let damaged = score(Scene::Flat, &damaged, INTERIOR);
    assert!(
        !flat_guard(&good, &good, &damaged),
        "flat noise destroyer escaped actual guard"
    );
    let exact = truth_image(Scene::ThinDepth);
    let mut hair = Vec::new();
    for window in [THIN_FAR, THIN_NEAR] {
        let good = score(Scene::ThinDepth, &exact, window);
        assert!(good.recovery.iter().all(|v| *v >= 0.5) && structured_guard(&good, &good));
        let mut erased = exact.clone();
        for y in window.y0..window.y1 {
            for x in window.x0..window.x1 {
                let p = ((y - 2 * crop().y) * (2 * crop().width) + x - 2 * crop().x) * 3;
                erased[p..p + 3].fill(0.25);
            }
        }
        let bad = score(Scene::ThinDepth, &erased, window);
        assert!(
            !recovery_pass(&good, &bad) && !structured_guard(&good, &bad),
            "erased hair escaped actual guard"
        );
        hair.push(json!({"window":window.name,"exact":score_json(&good),"erased":score_json(&bad),"rejected":true}));
    }
    assert!(focused_component_guard(0.8, 0.8) && !focused_component_guard(0.8, 0.4));
    json!({"flat_exact_pass":true,"flat_added_noise_rejected":true,"flat_added_noise":score_json(&damaged),"erased_hair":hair,"focused_component_destroyer_rejected":true})
}

fn arm_list(c: &Comparison) -> [(&'static str, &Arm); 5] {
    [
        ("canonical", &c.canonical),
        ("canonical-replay", &c.canonical_replay),
        ("matched-green", &c.matched_green),
        ("joint", &c.joint),
        ("uniform", &c.uniform),
    ]
}

fn normalizer_controls() -> Value {
    let cfg = MergeConfig {
        bands: 1,
        ..MergeConfig::default()
    };
    let sizes = [
        LevelSize {
            width: 2,
            height: 2,
        },
        LevelSize {
            width: 1,
            height: 1,
        },
    ];
    let build = |energy: f32, variance: f32| {
        core::fields_from_energy(
            &sizes,
            cfg,
            vec![vec![energy; 4]],
            vec![vec![cfg.gate * variance; 4]],
        )
    };
    let a = [build(4.0, 1.0), build(8.0, 2.0), build(12.0, 3.0)];
    let joined = super::guide::shared_snr_fields(&sizes, cfg, [&a[0], &a[1], &a[2]]).unwrap();
    assert_eq!(joined.energy, vec![vec![12.0; 4]]);
    assert_eq!(joined.floor, vec![vec![6.0; 4]]);
    assert!(joined.weights[0].iter().all(|v| *v > 0.0));
    let scaled = [build(16.0, 4.0), build(128.0, 32.0), build(768.0, 192.0)];
    let same =
        super::guide::shared_snr_fields(&sizes, cfg, [&scaled[0], &scaled[1], &scaled[2]]).unwrap();
    assert_eq!(
        joined.weights, same.weights,
        "consistent channel gain did not cancel"
    );
    let wrong = [build(4.0, 3.0), build(8.0, 2.0), build(12.0, 1.0)];
    let wrong =
        super::guide::shared_snr_fields(&sizes, cfg, [&wrong[0], &wrong[1], &wrong[2]]).unwrap();
    assert_ne!(
        joined.weights, wrong.weights,
        "wrong channel-floor mapping was not exercised"
    );
    let null = [build(1.0, 1.0), build(2.0, 2.0), build(3.0, 3.0)];
    let null =
        super::guide::shared_snr_fields(&sizes, cfg, [&null[0], &null[1], &null[2]]).unwrap();
    assert!(null.weights[0].iter().all(|v| *v == 0.0));
    let zero = build(1.0, 0.0);
    assert!(super::guide::shared_snr_fields(&sizes, cfg, [&zero, &a[1], &a[2]]).is_err());
    json!({"status":"PASS","known_energy":12.0,"known_floor":6.0,
        "consistent_channel_gain_exact":true,"wrong_floor_mapping_live":true,
        "noise_expectation_energy_has_zero_weight":true,"zero_floor_refused":true,
        "scope":"deterministic arithmetic only; not stochastic null calibration"})
}

fn check(c: &Comparison, frames: &[Frame], ts: &[Similarity], scene: Scene) -> Value {
    assert_eq!(
        c.sizes,
        vec![[145, 125], [73, 63], [37, 32], [19, 16], [10, 8]]
    );
    assert!(exact(&c.canonical.planes4, &c.canonical_replay.planes4));
    assert!(exact_slice(&c.canonical.rgb, &c.canonical_replay.rgb));
    let n = crop().width * crop().height;
    let mut lo = vec![vec![f32::INFINITY; n]; 4];
    let mut hi = vec![vec![f32::NEG_INFINITY; n]; 4];
    let mut focused = Vec::new();
    for (k, frame) in frames.iter().enumerate() {
        let before = hash(&frame.data);
        let known =
            super::super::boundary_cfa_wavelet::gather_known4(frame, ts[k], crop()).unwrap();
        for ch in 0..4 {
            for p in 0..n {
                lo[ch][p] = lo[ch][p].min(known[ch][p]);
                hi[ch][p] = hi[ch][p].max(known[ch][p]);
            }
        }
        let take = match scene {
            Scene::Cofocused | Scene::Weak => k == 2,
            Scene::ColourOnly => k == 1 || k == 3,
            _ => false,
        };
        if take {
            let rgb = super::super::phase_packed_rgb::camera_rgb(
                &known,
                crop().width,
                crop().height,
                levels(),
                frame.wb_coeffs,
            )
            .unwrap();
            focused.push(json!({"source":k,"score":score_json(&score(scene, &rgb, INTERIOR))}));
        }
        assert_eq!(before, hash(&frame.data));
        if !c.frames.is_empty() {
            assert_eq!(c.frames[k]["source_sha256"].as_str(), Some(before.as_str()));
        }
    }
    for (_, arm) in arm_list(c) {
        assert!(arm.terminal_base_exact && arm.rgb.iter().all(|v| v.is_finite()));
        for ch in 0..4 {
            for p in 0..n {
                assert!(
                    arm.planes4[ch][p] >= lo[ch][p] && arm.planes4[ch][p] <= hi[ch][p],
                    "original input hull escaped"
                );
            }
        }
    }
    json!({"canonical_replay_exact":true,"terminal_means_exact":true,"input_hull":true,
        "four_planes_one_weight_call":true,"focused":focused})
}

fn store_outputs(out: &Path, scene: Scene, iso: f32, c: &Comparison) -> Value {
    let mut rows = Vec::new();
    for (name, arm) in arm_list(c) {
        let path = out.join(format!("{}-iso{iso}-{name}.f32", scene.name()));
        let mut bytes = Vec::with_capacity(4 * arm.rgb.len());
        for value in &arm.rgb {
            bytes.extend_from_slice(&value.to_le_bytes());
        }
        std::fs::write(&path, &bytes).unwrap();
        let digest = Sha256::digest(&bytes)
            .iter()
            .map(|v| format!("{v:02x}"))
            .collect::<String>();
        rows.push(json!({"arm":name,"camera_rgb_f32":path,"sha256":digest,
            "width":2*crop().width,"height":2*crop().height,"whole_generated_output":true,
            "averaged_fraction_by_band":arm.averaged_fraction}));
    }
    Value::Array(rows)
}

fn screen_result(
    out: &Path,
    status: &str,
    admitted: bool,
    normalizer: &Value,
    noise: &Value,
    metric: &Value,
    cases: &[Value],
    foil: bool,
    companion: &Value,
) {
    let cfg = MergeConfig {
        bands: 4,
        ..MergeConfig::default()
    };
    let full = MergeConfig::default();
    write(
        &out.join("screen.json"),
        &json!({"status":status,
        "preliminary_full_observation_controls_admitted":admitted,
        "photographic_quality_admitted":false,"requires_one_source_cost_before_full":true,
        "normalizer_controls":normalizer,"retained_noise_controls":noise,"metric_controls":metric,
        "cyclic_source_foil_rejected":foil,"cases":cases,"independent_noiseless_companion":companion,
        "resolved_config_debug":format!("{cfg:?}"),"ac_exponents":(0..4).map(|k|cfg.exponent_at(k,4)).collect::<Vec<_>>(),
        "prospective_full_config_debug":format!("{full:?}"),"prospective_full_ac_exponents":(0..full.bands).map(|k|full.exponent_at(k,full.bands)).collect::<Vec<_>>(),
        "full_fine_band_behavior_validated":false,
        "scope":"fixed generated actual-consumer screen; no RAW photograph, calibration or SOTA claim"}),
    );
    eprintln!(
        "INSECT_COLOR_DECISION {}",
        json!({"status":status,"controls_admitted":admitted})
    );
}

#[test]
fn fixed_shared_snr_actual_consumer_screen() {
    let out = PathBuf::from(
        std::env::var_os("STREHL_INSECT_COLOR_OUT").expect("root-owned fresh output required"),
    );
    std::fs::create_dir(&out).unwrap();
    let normalizer = normalizer_controls();
    let noise_control = super::noise_controls::check_noise_floor().unwrap();
    let commissioned =
        json!({"retained_metric":commission(),"actual_guard_destroyers":guard_commission()});
    let ts = transforms();
    let cfg = MergeConfig {
        bands: 4,
        ..MergeConfig::default()
    };
    let mut records = Vec::new();
    // Both flat ISO guards precede any structured scene. Refusal is an explicit
    // scientific result, not a panic or an invitation to tune another probe count.
    for iso in [100.0_f32, 400.0] {
        let noise = profile::noise_model_for("ILCE-7CM2", Some(iso), levels());
        let frames = ts
            .iter()
            .enumerate()
            .map(|(k, &t)| fixture(Scene::Flat, k, t, iso, &noise))
            .collect::<Vec<_>>();
        let c = compare_generated(&frames, &ts, crop(), &noise, cfg, false, true).unwrap();
        let structure = check(&c, &frames, &ts, Scene::Flat);
        let b = score(Scene::Flat, &c.canonical.rgb, INTERIOR);
        let m = score(Scene::Flat, &c.matched_green.rgb, INTERIOR);
        let u = score(Scene::Flat, &c.uniform.rgb, INTERIOR);
        let j = score(Scene::Flat, &c.joint.rgb, INTERIOR);
        let pass = flat_guard(&b, &u, &j);
        records.push(json!({"scene":"flat","iso":iso,"pass":pass,"canonical":score_json(&b),
            "matched_green":score_json(&m),"uniform":score_json(&u),"joint":score_json(&j),
            "mechanics":structure,"outputs":store_outputs(&out,Scene::Flat,iso,&c),"source_evidence":c.frames}));
        if !pass {
            screen_result(
                &out,
                "FLAT_REFUSAL",
                false,
                &normalizer,
                &noise_control,
                &commissioned,
                &records,
                false,
                &Value::Null,
            );
            return;
        }
    }
    let companion = independent::noiseless_companion(&out);
    let mut admitted = true;
    let mut foil_rejected = false;
    for iso in [100.0_f32, 400.0] {
        let noise = profile::noise_model_for("ILCE-7CM2", Some(iso), levels());
        for scene in [
            Scene::Cofocused,
            Scene::Neutral,
            Scene::ThinDepth,
            Scene::Weak,
            Scene::ColourOnly,
        ] {
            let frames = ts
                .iter()
                .enumerate()
                .map(|(k, &t)| fixture(scene, k, t, iso, &noise))
                .collect::<Vec<_>>();
            let before = frames.iter().map(|f| hash(&f.data)).collect::<Vec<_>>();
            let c = compare_generated(&frames, &ts, crop(), &noise, cfg, false, true).unwrap();
            let structure = check(&c, &frames, &ts, scene);
            let windows: &[Window] = if scene == Scene::ThinDepth {
                &[THIN_FAR, THIN_NEAR, JUNCTION]
            } else {
                &[INTERIOR]
            };
            let mut pass = true;
            let mut windows_out = Vec::new();
            for &window in windows {
                let b = score(scene, &c.canonical.rgb, window);
                let m = score(scene, &c.matched_green.rgb, window);
                let j = score(scene, &c.joint.rgb, window);
                let mut gate = structured_guard(&b, &j);
                if scene == Scene::Cofocused {
                    gate &= j.rgb <= 0.95 * b.rgb
                        && j.rgb <= 0.95 * m.rgb
                        && j.chroma <= 0.95 * b.chroma
                        && j.chroma <= 0.95 * m.chroma;
                    let focused = &structure["focused"][0]["score"]["truth_template_recovery"];
                    for ch in [0, 2] {
                        let reference = focused[ch].as_f64().unwrap();
                        gate &= focused_component_guard(reference, j.recovery[ch]);
                    }
                }
                if scene == Scene::Weak {
                    let reference = structure["focused"][0]["score"]["truth_template_recovery"][0]
                        .as_f64()
                        .unwrap();
                    gate &= focused_component_guard(reference, j.recovery[0]);
                }
                if scene == Scene::ColourOnly {
                    // Fixed source1 R/source3 B witnesses, never an output argmax.
                    for (witness, ch) in [(0, 0), (1, 2)] {
                        let reference =
                            structure["focused"][witness]["score"]["truth_template_recovery"][ch]
                                .as_f64()
                                .unwrap();
                        gate &= focused_component_guard(reference, j.recovery[ch]);
                    }
                }
                if scene == Scene::ThinDepth && window.name != "thin-junction" {
                    gate &= b.recovery.iter().all(|v| *v >= 0.5);
                }
                pass &= gate;
                windows_out.push(json!({"name":window.name,"native_xyxy":[window.x0,window.y0,window.x1,window.y1],
                    "pass":gate,"green_1p05_guard":j.green<=1.05*b.green,"rgb_1p05_guard":j.rgb<=1.05*b.rgb,
                    "chroma_1p05_guard":j.chroma<=1.05*b.chroma,"canonical_component_guard":recovery_pass(&b,&j),
                    "canonical":score_json(&b),"matched_green":score_json(&m),"joint":score_json(&j)}));
            }
            let mut extras = Value::Null;
            if scene == Scene::Cofocused && iso == 100.0 {
                let wrong =
                    compare_generated(&frames, &ts, crop(), &noise, cfg, true, true).unwrap();
                assert!(wrong.joint_uses_next_source_weights);
                assert!(exact_slice(&wrong.canonical.rgb, &c.canonical.rgb));
                assert!(exact_slice(&wrong.matched_green.rgb, &c.matched_green.rgb));
                let j = score(scene, &c.joint.rgb, INTERIOR);
                let f = score(scene, &wrong.joint.rgb, INTERIOR);
                foil_rejected = f.rgb > 1.10 * j.rgb || !recovery_pass(&j, &f);
                let live = c
                    .frames
                    .iter()
                    .any(|f| f["joint_weight_sha256"] != f["matched_green_weight_sha256"])
                    && !exact_slice(&c.joint.rgb, &c.matched_green.rgb);
                let quiet =
                    compare_generated(&frames, &ts, crop(), &noise, cfg, false, false).unwrap();
                for ((an, a), (bn, b)) in arm_list(&c).into_iter().zip(arm_list(&quiet)) {
                    assert_eq!(an, bn);
                    assert!(exact(&a.planes4, &b.planes4) && exact_slice(&a.rgb, &b.rgb));
                }
                assert!(quiet.frames.is_empty());
                pass &= foil_rejected && live;
                extras = json!({"joint_guide_live":live,"wrong_source":score_json(&f),
                    "cyclic_source_foil_rejected":foil_rejected,"diagnostics_all_outputs_exact":true});
            }
            for (frame, expected) in frames.iter().zip(&before) {
                assert_eq!(hash(&frame.data), *expected);
            }
            admitted &= pass;
            records.push(json!({"scene":scene.name(),"iso":iso,"pass":pass,"windows":windows_out,
                "mechanics":structure,"extras":extras,"outputs":store_outputs(&out,scene,iso,&c),"source_evidence":c.frames}));
        }
    }
    screen_result(
        &out,
        "SCREEN_COMPLETE",
        admitted && foil_rejected,
        &normalizer,
        &noise_control,
        &commissioned,
        &records,
        foil_rejected,
        &companion,
    );
}
