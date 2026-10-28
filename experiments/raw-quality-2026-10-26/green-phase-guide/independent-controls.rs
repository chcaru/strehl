// Independent fixed scene/guard choices. Root owns compilation and execution.
include!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../experiments/raw-quality-2026-10-26/insect-color/fixtures.rs"
));
use super::{Arm, Comparison, GuideFoil, compare_generated, compare_generated_with_foil};

fn arms(c: &Comparison) -> [(&'static str, &Arm); 5] {
    [
        ("canonical", &c.canonical),
        ("canonical-replay", &c.canonical_replay),
        ("matched-mean", &c.matched_green),
        ("phase-energy", &c.joint),
        ("uniform", &c.uniform),
    ]
}

fn severe_component_loss(b: &Score, j: &Score) -> bool {
    (0..3).any(|c| {
        (b.recovery[c] >= 0.5 && j.recovery[c] < 0.8 * b.recovery[c].min(1.0))
            || (b.recovery[c] <= 1.20 && j.recovery[c] > 1.35)
    })
}

fn phase_field_arithmetic() -> Value {
    use strehl_core::pyramid::LevelSize;
    let sizes = [
        LevelSize {
            width: 4,
            height: 4,
        },
        LevelSize {
            width: 2,
            height: 2,
        },
        LevelSize {
            width: 1,
            height: 1,
        },
        LevelSize {
            width: 1,
            height: 1,
        },
        LevelSize {
            width: 1,
            height: 1,
        },
    ];
    let cfg = MergeConfig {
        bands: 4,
        ..MergeConfig::default()
    };
    let canonical = super::consumer::fields_from_energy(
        &sizes,
        cfg,
        sizes[..4].iter().map(|s| vec![25.0; s.pixels()]).collect(),
        sizes[..4].iter().map(|s| vec![2.0; s.pixels()]).collect(),
    );
    let bands = |v| {
        sizes[..2]
            .iter()
            .map(|s| vec![v; s.pixels()])
            .collect::<Vec<_>>()
    };
    let signal = [bands(4.0), bands(0.0), bands(-4.0)];
    // Declared arbitrary propagation values, not independently estimated noise.
    // Mean-G variance differs from mean phase variance because covariance matters.
    let variance = [bands(1.0), bands(0.5), bands(3.0)];
    let phase =
        super::fields_from_green(&canonical, &signal, &variance, &sizes, cfg, true).unwrap();
    let mean =
        super::fields_from_green(&canonical, &signal, &variance, &sizes, cfg, false).unwrap();
    for k in 0..2 {
        assert!(phase.energy[k].iter().all(|v| *v == 16.0));
        assert!(phase.floor[k].iter().all(|v| *v == 4.0));
        assert!(mean.energy[k].iter().all(|v| *v == 0.0));
        assert!(mean.floor[k].iter().all(|v| *v == 1.0));
        assert!(phase.weights[k].iter().all(|v| *v > 0.0));
        assert!(mean.weights[k].iter().all(|v| *v == 0.0));
    }
    for k in 2..4 {
        assert!(exact_slice(&phase.energy[k], &canonical.energy[k]));
        assert!(exact_slice(&phase.floor[k], &canonical.floor[k]));
        assert!(exact_slice(&phase.weights[k], &canonical.weights[k]));
        assert!(exact_slice(&mean.weights[k], &canonical.weights[k]));
    }
    json!({"opposed_phase_bands_keep_energy":16.0,"phase_floor":4.0,
        "mean_green_energy":0.0,"mean_green_floor":1.0,"coarse_exact":true,
        "scope":"literal operator and covariance-sensitive floor routing, not photographic evidence"})
}

fn mechanics(c: &Comparison, frames: &[Frame], ts: &[Similarity]) {
    assert!(exact(&c.canonical.planes4, &c.canonical_replay.planes4));
    assert!(exact_slice(&c.canonical.rgb, &c.canonical_replay.rgb));
    let n = crop().width * crop().height;
    let mut lo = vec![vec![f32::INFINITY; n]; 4];
    let mut hi = vec![vec![f32::NEG_INFINITY; n]; 4];
    for (k, frame) in frames.iter().enumerate() {
        let original = hash(&frame.data);
        let known =
            super::super::boundary_cfa_wavelet::gather_known4(frame, ts[k], crop()).unwrap();
        for ch in 0..4 {
            for p in 0..n {
                lo[ch][p] = lo[ch][p].min(known[ch][p]);
                hi[ch][p] = hi[ch][p].max(known[ch][p]);
            }
        }
        assert_eq!(hash(&frame.data), original);
        if !c.frames.is_empty() {
            assert_eq!(
                c.frames[k]["source_sha256"].as_str(),
                Some(original.as_str())
            );
            assert_eq!(c.frames[k]["coarse_fields_exact"], true);
            assert_eq!(c.frames[k]["reconstruction_planes_per_shared_field"], 4);
        }
    }
    for (_, arm) in arms(c) {
        assert!(arm.terminal_base_exact && arm.rgb.iter().all(|x| x.is_finite()));
        for ch in 0..4 {
            for p in 0..n {
                let v = arm.planes4[ch][p];
                assert!(
                    v.is_finite() && v >= lo[ch][p] && v <= hi[ch][p],
                    "original hull escaped"
                );
            }
        }
    }
}

fn save_image(out: &Path, name: &str, rgb: &[f32]) -> Value {
    use std::io::Write;
    let path = out.join(format!("{name}.f32"));
    let bytes = rgb.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>();
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .unwrap();
    f.write_all(&bytes).unwrap();
    json!({"path":path,"sha256":Sha256::digest(&bytes).iter().map(|v|format!("{v:02x}")).collect::<String>(),
        "width":2*crop().width,"height":2*crop().height,"format":"row-major camera RGB f32 little-endian",
        "complete_generated_output":true})
}

fn save_arms(out: &Path, case: &str, c: &Comparison) -> Value {
    Value::Array(
        arms(c)
            .iter()
            .map(|(name, arm)| {
                json!({"arm":name,
        "master":save_image(out,&format!("{case}-{name}"),&arm.rgb),
        "averaged_fraction":arm.averaged_fraction})
            })
            .collect(),
    )
}

fn commissioned_guards() -> Value {
    let inherited = commission();
    let exact = truth_image(Scene::ThinDepth);
    let mut records = Vec::new();
    for window in [THIN_FAR, THIN_NEAR] {
        let good = score(Scene::ThinDepth, &exact, window);
        let mut erased = exact.clone();
        for y in window.y0..window.y1 {
            for x in window.x0..window.x1 {
                let p = ((y - 2 * crop().y) * (2 * crop().width) + x - 2 * crop().x) * 3;
                erased[p..p + 3].fill(0.25);
            }
        }
        let bad = score(Scene::ThinDepth, &erased, window);
        assert!(!severe_component_loss(&good, &good) && severe_component_loss(&good, &bad));
        records.push(
            json!({"window":window.name,"exact":score_json(&good),"erased":score_json(&bad)}),
        );
    }
    let flat = truth_image(Scene::Flat);
    let mut noisy = flat.clone();
    for (p, v) in noisy.iter_mut().enumerate() {
        *v += 0.03
            * gaussian(
                p / 3 % (2 * crop().width),
                p / 3 / (2 * crop().width),
                p % 3,
            ) as f32;
    }
    let good = score(Scene::Flat, &flat, INTERIOR);
    let bad = score(Scene::Flat, &noisy, INTERIOR);
    assert!(bad.rgb > 1.20 * good.rgb && bad.rgb > 1.25 * good.rgb);
    json!({"inherited_colour_commission":inherited,"erased_depth_components":records,
        "flat_added_noise_rejected":true,"noise":score_json(&bad)})
}

fn diagonal(f: f64, x: f64, y: f64, source: Option<usize>, phase: f64) -> f64 {
    let sigma = 0.65 + 1.1 * source.map_or(0.0, |k| (k as f64 - 2.0).abs());
    0.25 + 0.09
        * (-0.5 * (TAU * f * sigma).powi(2)).exp()
        * (TAU * f * (x - y) / 2.0_f64.sqrt() + 0.31 + phase).cos()
}

fn diagonal_truth(f: f64, phase: f64) -> Vec<f32> {
    (0..2 * crop().height)
        .flat_map(|y| {
            (0..2 * crop().width).flat_map(move |x| {
                [diagonal(
                    f,
                    (x + 2 * crop().x) as f64,
                    (y + 2 * crop().y) as f64,
                    None,
                    phase,
                ) as f32; 3]
            })
        })
        .collect()
}

fn diagonal_frame(f: f64, k: usize, t: Similarity, noise: &NoiseModel) -> Frame {
    // Reuse metadata/padding and overwrite only physical active samples.
    let mut frame = fixture(Scene::Neutral, k, t, 100.0, noise);
    let determinant = t.a.re * t.a.re + t.a.im * t.a.im;
    for y in 0..H {
        for x in 0..W {
            let u = x as f64 - W as f64 / 2.0 - 2.0 * t.b.re;
            let v = y as f64 - H as f64 / 2.0 - 2.0 * t.b.im;
            let wx = W as f64 / 2.0 + (t.a.re * u + t.a.im * v) / determinant;
            let wy = H as f64 / 2.0 + (-t.a.im * u + t.a.re * v) / determinant;
            let signal = (diagonal(f, wx, wy, Some(k), 0.0) * f64::from(levels().range())
                / f64::from(GAIN[channel(x, y)])) as f32;
            let value = 512.0
                + f64::from(signal)
                + gaussian(x, y, k) * f64::from(noise.sigma(cfa(x, y), signal));
            assert!(value > 512.0 && value < 15360.0);
            frame.data[(frame.active.y + y) * frame.stride + frame.active.x + x] =
                value.round() as u16;
        }
    }
    frame
}

fn diagonal_score(f: f64, rgb: &[f32]) -> Score {
    let w = 2 * crop().width;
    assert_eq!(rgb.len(), w * 2 * crop().height * 3);
    let mut sums = [[0.0_f64; 4]; 3];
    let (mut error, mut green, mut chroma) = (0.0, 0.0, 0.0);
    let n = ((INTERIOR.x1 - INTERIOR.x0) * (INTERIOR.y1 - INTERIOR.y0)) as f64;
    for y in INTERIOR.y0..INTERIOR.y1 {
        for x in INTERIOR.x0..INTERIOR.x1 {
            let truth = diagonal(f, x as f64, y as f64, None, 0.0);
            let p = ((y - 2 * crop().y) * w + x - 2 * crop().x) * 3;
            let mut e = [0.0; 3];
            for c in 0..3 {
                let value = f64::from(rgb[p + c]);
                assert!(value.is_finite());
                e[c] = value - truth;
                error += e[c] * e[c];
                for (a, b) in sums[c]
                    .iter_mut()
                    .zip([truth, value, truth * truth, value * truth])
                {
                    *a += b;
                }
            }
            green += e[1] * e[1];
            chroma += (e[0] - e[1]).powi(2) + (e[2] - e[1]).powi(2);
        }
    }
    let mut recovery = [0.0; 3];
    let mut truth_sd = [0.0; 3];
    for c in 0..3 {
        let [st, sv, tt, tv] = sums[c];
        let variance = tt - st * st / n;
        assert!(variance > 0.0);
        recovery[c] = (tv - st * sv / n) / variance;
        truth_sd[c] = (variance / n).sqrt();
    }
    Score {
        rgb: (error / (3.0 * n)).sqrt(),
        green: (green / n).sqrt(),
        chroma: (chroma / (2.0 * n)).sqrt(),
        recovery,
        truth_sd,
    }
}

fn analytic_commission() -> Value {
    let f = 0.18;
    let truth = diagonal_truth(f, 0.0);
    let good = diagonal_score(f, &truth);
    let half = truth
        .iter()
        .map(|v| 0.25 + 0.5 * (v - 0.25))
        .collect::<Vec<_>>();
    let half = diagonal_score(f, &half);
    let shifted = diagonal_score(f, &diagonal_truth(f, TAU * f));
    assert!(good.rgb < 1e-7 && half.recovery.iter().all(|v| (v - 0.5).abs() < 1e-5));
    assert!(severe_component_loss(&good, &half) && shifted.rgb > 0.02);
    json!({"exact":score_json(&good),"half_amplitude":score_json(&half),"one_native_radial_pixel_phase_shift":score_json(&shifted)})
}

#[test]
#[ignore = "root-scheduled generated actual-consumer screen; requires STREHL_GREEN_PHASE_OUT"]
fn fixed_green_phase_actual_consumer_screen() {
    let out = PathBuf::from(
        std::env::var_os("STREHL_GREEN_PHASE_OUT").expect("fresh root-owned output required"),
    );
    assert!(out.is_absolute() && !out.exists());
    std::fs::create_dir(&out).unwrap();
    let noise = profile::noise_model_for("ILCE-7CM2", Some(100.0), levels());
    let cfg = MergeConfig {
        bands: 4,
        ..MergeConfig::default()
    };
    let ts = transforms();
    let mut records = Vec::new();
    let mut severe = false;
    let mut guide_live = false;
    let guard_commission = commissioned_guards();
    let diagonal_commission = analytic_commission();
    let field_arithmetic = phase_field_arithmetic();
    // Flat acquisition/consumer precedes all structured acquisition/consumer cases.
    for scene in [
        Scene::Flat,
        Scene::Neutral,
        Scene::Cofocused,
        Scene::ColourOnly,
        Scene::ThinDepth,
        Scene::Radial,
        Scene::ClippedGlint,
    ] {
        let frames = ts
            .iter()
            .enumerate()
            .map(|(k, &t)| fixture(scene, k, t, 100.0, &noise))
            .collect::<Vec<_>>();
        let before = frames.iter().map(|f| hash(&f.data)).collect::<Vec<_>>();
        let c = compare_generated(&frames, &ts, crop(), &noise, cfg, false, true).unwrap();
        mechanics(&c, &frames, &ts);
        let windows: &[Window] = match scene {
            Scene::ThinDepth => &[THIN_FAR, THIN_NEAR, JUNCTION],
            Scene::ClippedGlint => &[OUTSIDE, NEAR],
            Scene::Radial => &[RADIAL],
            _ => &[INTERIOR],
        };
        let mut rows = Vec::new();
        for &window in windows {
            let b = score(scene, &c.canonical.rgb, window);
            let j = score(scene, &c.joint.rgb, window);
            let u = score(scene, &c.uniform.rgb, window);
            let obvious_flat = scene == Scene::Flat && j.rgb > 1.20 * b.rgb && j.rgb > 1.25 * u.rgb;
            let loss = scene != Scene::Flat && severe_component_loss(&b, &j);
            let false_colour =
                scene == Scene::Neutral && j.chroma > 1.50 * b.chroma && j.chroma > 0.0025;
            let glint_neighbor =
                scene == Scene::ClippedGlint && j.rgb > 1.50 * b.rgb && j.rgb > 0.0025;
            severe |= obvious_flat || loss || false_colour || glint_neighbor;
            rows.push(json!({"window":window.name,"native_xyxy":[window.x0,window.y0,window.x1,window.y1],
                "canonical":score_json(&b),"matched_mean":score_json(&score(scene,&c.matched_green.rgb,window)),
                "candidate":score_json(&j),"uniform":score_json(&u),"severe_flat":obvious_flat,
                "severe_component_loss_or_overshoot":loss,"severe_neutral_false_colour":false_colour,
                "severe_clipped_glint_neighbor_error":glint_neighbor,
                "older_5percent_rgb_guard":j.rgb<=1.05*b.rgb}));
        }
        let mut extras = Value::Null;
        if scene == Scene::ThinDepth {
            guide_live |= !exact_slice(&c.joint.rgb, &c.matched_green.rgb);
            let quiet = compare_generated(&frames, &ts, crop(), &noise, cfg, false, false).unwrap();
            for ((name, a), (other, b)) in arms(&c).into_iter().zip(arms(&quiet)) {
                assert_eq!(name, other);
                assert!(exact(&a.planes4, &b.planes4) && exact_slice(&a.rgb, &b.rgb));
            }
            assert!(quiet.frames.is_empty());
            let mut foils = Vec::new();
            for (name, foil) in [
                ("wrong-source", GuideFoil::NextSource),
                ("wrong-phase", GuideFoil::ShiftG2OneQuad),
            ] {
                let wrong =
                    compare_generated_with_foil(&frames, &ts, crop(), &noise, cfg, foil, true)
                        .unwrap();
                assert!(exact_slice(&wrong.canonical.rgb, &c.canonical.rgb));
                assert!(exact_slice(&wrong.matched_green.rgb, &c.matched_green.rgb));
                let live = !exact_slice(&wrong.joint.rgb, &c.joint.rgb);
                assert!(live, "guide destroyer had no effect");
                foils.push(json!({"name":name,"live":live,"windows":([THIN_FAR,THIN_NEAR,JUNCTION].map(|w|json!({"name":w.name,"score":score_json(&score(scene,&wrong.joint.rgb,w))}))),
                    "master":save_image(&out,&format!("thin-{name}"),&wrong.joint.rgb)}));
            }
            let singleton =
                compare_generated(&frames[2..3], &ts[2..3], crop(), &noise, cfg, false, true)
                    .unwrap();
            mechanics(&singleton, &frames[2..3], &ts[2..3]);
            for (_, a) in arms(&singleton) {
                assert!(exact(&a.planes4, &singleton.canonical.planes4));
            }
            extras = json!({"diagnostics_placebo_exact":true,"one_source_original_hull_identity":true,"foils":foils});
        }
        assert!(frames.iter().zip(&before).all(|(f, h)| hash(&f.data) == *h));
        records.push(
            json!({"scene":scene.name(),"iso":100,"windows":rows,"extras":extras,
            "truth":save_image(&out,&format!("{}-truth",scene.name()),&truth_image(scene)),
            "outputs":save_arms(&out,scene.name(),&c),"source_evidence":c.frames}),
        );
    }
    for (name, f) in [("diagonal-moderate", 0.18), ("diagonal-low", 0.035)] {
        let frames = ts
            .iter()
            .enumerate()
            .map(|(k, &t)| diagonal_frame(f, k, t, &noise))
            .collect::<Vec<_>>();
        let before = frames.iter().map(|v| hash(&v.data)).collect::<Vec<_>>();
        let c = compare_generated(&frames, &ts, crop(), &noise, cfg, false, true).unwrap();
        mechanics(&c, &frames, &ts);
        guide_live |= !exact_slice(&c.joint.rgb, &c.matched_green.rgb);
        let b = diagonal_score(f, &c.canonical.rgb);
        let j = diagonal_score(f, &c.joint.rgb);
        let loss = severe_component_loss(&b, &j);
        let colour = j.chroma > 1.50 * b.chroma && j.chroma > 0.0025;
        severe |= loss || colour;
        assert!(frames.iter().zip(&before).all(|(v, h)| hash(&v.data) == *h));
        records.push(json!({"scene":name,"frequency_cycles_per_native_pixel":f,"direction":[1.0/2.0_f64.sqrt(),-1.0/2.0_f64.sqrt()],
            "canonical":score_json(&b),"matched_mean":score_json(&diagonal_score(f,&c.matched_green.rgb)),
            "candidate":score_json(&j),"uniform":score_json(&diagonal_score(f,&c.uniform.rgb)),
            "severe_component_loss_or_overshoot":loss,"severe_neutral_false_colour":colour,
            "truth":save_image(&out,&format!("{name}-truth"),&diagonal_truth(f,0.0)),
            "outputs":save_arms(&out,name,&c),"source_evidence":c.frames}));
    }
    assert!(
        guide_live,
        "phase-energy intervention never changed the actual consumer"
    );
    let full = MergeConfig::default();
    write(
        &out.join("screen.json"),
        &json!({"status":"SCREEN_COMPLETE","severe_generated_guard":severe,
        "candidate_live":guide_live,"photographic_improvement_claimed":false,"guard_commission":guard_commission,
        "analytic_commission":diagonal_commission,"phase_field_arithmetic":field_arithmetic,"cases":records,"noise_model":format!("{noise:?}"),
        "resolved_screen_config":format!("{cfg:?}"),"screen_exponents":(0..cfg.bands).map(|k|cfg.exponent_at(k,cfg.bands)).collect::<Vec<_>>(),
        "full_config":format!("{full:?}"),"full_exponents":(0..full.bands).map(|k|full.exponent_at(k,full.bands)).collect::<Vec<_>>(),
        "scope":"ISO100 fixed generated actual-consumer screen; root reviews severe loss and whole outputs before complete photograph; no tuning or synthetic SOTA claim"}),
    );
    eprintln!("GREEN_PHASE_SCREEN severe_generated_guard={severe}");
}
