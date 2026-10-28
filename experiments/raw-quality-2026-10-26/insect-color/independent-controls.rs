// Independently chosen prospective companion, not a replacement quality gate.
// Included as controls::independent. Root owns registration/build/execution.
use super::*;

fn green_template_stats(rgb: &[f32]) -> Value {
    let width = 2 * crop().width;
    assert_eq!(rgb.len(), width * 2 * crop().height * 3);
    let mut sums = [0.0_f64; 3]; // count, green residual sum, squared sum
    let mut templates = [[0.0_f64; 3]; 2]; // template, squared, residual product
    let mut maximum = 0.0_f64;
    for y in INTERIOR.y0..INTERIOR.y1 {
        for x in INTERIOR.x0..INTERIOR.x1 {
            let p = ((y - 2 * crop().y) * width + x - 2 * crop().x) * 3;
            let residual = f64::from(rgb[p + 1]) - 0.25;
            assert!(residual.is_finite());
            sums[0] += 1.0;
            sums[1] += residual;
            sums[2] += residual * residual;
            maximum = maximum.max(residual.abs());
            for (slot, channel) in [0, 2].into_iter().enumerate() {
                let t = radiance(Scene::Cofocused, channel, x as f64, y as f64, None) - 0.25;
                templates[slot][0] += t;
                templates[slot][1] += t * t;
                templates[slot][2] += t * residual;
            }
        }
    }
    let projections = templates.map(|[sum, square, product]| {
        let variance_sum = square - sum * sum / sums[0];
        assert!(variance_sum > 0.0);
        let coupling = (product - sum * sums[1] / sums[0]) / variance_sum;
        json!({"coupling_to_true_colour_template":coupling,
            "projected_green_rms":coupling.abs()*(variance_sum/sums[0]).sqrt()})
    });
    json!({"green_residual_mean":sums[1]/sums[0],
        "green_residual_rmse":(sums[2]/sums[0]).sqrt(),
        "green_residual_max_abs":maximum,
        "red_template":projections[0],"blue_template":projections[1],
        "scope":"separate descriptive projections, not a whitened fit or admission threshold"})
}

fn commission_green_template() -> Value {
    let truth = truth_image(Scene::Cofocused);
    let exact = green_template_stats(&truth);
    assert!(exact["green_residual_rmse"].as_f64().unwrap() < 1e-7);
    let mut false_green = truth.clone();
    for pixel in false_green.chunks_exact_mut(3) {
        pixel[1] += 0.25 * (pixel[0] - 0.25);
    }
    let bad = green_template_stats(&false_green);
    let coefficient = bad["red_template"]["coupling_to_true_colour_template"]
        .as_f64()
        .unwrap();
    assert!((coefficient - 0.25).abs() < 1e-5);
    assert!(bad["green_residual_rmse"].as_f64().unwrap() > 0.01);
    json!({"exact_truth":exact,"injected_false_green":bad,
        "injected_red_template_coupling":0.25,"commissioned":true})
}

pub(super) fn noiseless_companion(out: &Path) -> Value {
    let companion = out.join("independent-noiseless-cofocused");
    std::fs::create_dir(&companion).unwrap();
    let metric = commission_green_template();
    let iso = 100.0_f32;
    let noise = profile::noise_model_for("ILCE-7CM2", Some(iso), levels());
    let ts = transforms();
    let cfg = MergeConfig {
        bands: 4,
        ..MergeConfig::default()
    };
    let frames = ts
        .iter()
        .enumerate()
        .map(|(k, &t)| fixture_with_acquisition_noise(Scene::Cofocused, k, t, iso, &noise, 0.0))
        .collect::<Vec<_>>();
    let before = frames
        .iter()
        .map(|frame| hash(&frame.data))
        .collect::<Vec<_>>();
    let c = compare_generated(&frames, &ts, crop(), &noise, cfg, false, true).unwrap();
    let mechanics = check(&c, &frames, &ts, Scene::Cofocused);
    let mut rows = Vec::new();
    for (name, arm) in arm_list(&c) {
        rows.push(
            json!({"arm":name,"score":score_json(&score(Scene::Cofocused,&arm.rgb,INTERIOR)),
            "green_structure":green_template_stats(&arm.rgb)}),
        );
    }
    let focused_planes =
        super::super::super::boundary_cfa_wavelet::gather_known4(&frames[2], ts[2], crop())
            .unwrap();
    let focused = super::super::super::phase_packed_rgb::camera_rgb(
        &focused_planes,
        crop().width,
        crop().height,
        levels(),
        frames[2].wb_coeffs,
    )
    .unwrap();
    let focused_path = companion.join("focused-source-2-camera-rgb.f32");
    let bytes = focused
        .iter()
        .flat_map(|v| v.to_le_bytes())
        .collect::<Vec<_>>();
    std::fs::write(&focused_path, &bytes).unwrap();
    let focused_hash = Sha256::digest(&bytes)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect::<String>();
    for (frame, expected) in frames.iter().zip(&before) {
        assert_eq!(hash(&frame.data), *expected);
    }
    let b = score(Scene::Cofocused, &c.canonical.rgb, INTERIOR);
    let j = score(Scene::Cofocused, &c.joint.rgb, INTERIOR);
    let receipt = json!({"scene":"cofocused-colour-positive","iso":iso,
        "acquisition_noise_amplitude":0.0,"floor_noise_model":"unchanged declared Sony ILCE-7CM2 ISO100",
        "same_u16_quantization_geometry_gather_merge_mhc":true,
        "source_hashes":before,"mechanics":mechanics,"metric_commission":metric,
        "arms":rows,"existing_green_1_05_guard_pass":j.green<=1.05*b.green,
        "green_rmse_ratio_to_canonical":j.green/b.green,
        "focused_source":{"index":2,"camera_rgb_f32":focused_path,"sha256":focused_hash,
            "score":score_json(&score(Scene::Cofocused,&focused,INTERIOR)),
            "green_structure":green_template_stats(&focused)},
        "outputs":store_outputs(&companion,Scene::Cofocused,iso,&c),"source_evidence":c.frames,
        "photographic_quality_admitted":false,"replacement_admission_threshold":false,
        "scope":"deterministic cross-channel diagnostic; never rescues a failed noisy quality guard"});
    write(&companion.join("receipt.json"), &receipt);
    receipt
}
