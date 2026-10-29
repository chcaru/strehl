//! Bounded original-sample pair measurements for one already-prepared ROI.
use super::*;
use local_registration::{OriginalView, PlaneKind, Window, measure_pair_with_footprints};
use local_registration_graph::{Domain, Node, certify};
fn finite_number(x: f64) -> Value {
    if x.is_finite() { json!(x) } else { Value::Null }
}
fn pull_json(t: Similarity) -> Value {
    json!({"a":[t.a.re,t.a.im],"b":[t.b.re,t.b.im],"exact_bits":[t.a.re.to_bits(),t.a.im.to_bits(),t.b.re.to_bits(),t.b.im.to_bits()]})
}
pub(super) struct Measured {
    pub admitted: Vec<bool>,
    pub bound_sensor: Vec<f32>,
    pub report: Value,
    pub consuming_pulls: Vec<[Similarity; 3]>,
}
pub(super) fn measure(
    inputs: &Inputs,
    window_side_quad: usize,
    policy: local_registration::Policy,
    refine: bool,
    patch_diagnostics: bool,
) -> Result<Measured> {
    ensure!(
        (4..=14).contains(&inputs.originals.len()),
        "local pilot expects4..14 selected originals"
    );
    let started = Instant::now();
    let l = inputs.lattice;
    let mut sum = [0f64; 3];
    let mut count = 0usize;
    for (rgb, valid) in inputs.expected.iter().zip(&inputs.fallback_valid) {
        if *valid {
            for c in 0..3 {
                sum[c] += f64::from(rgb[c]);
            }
            count += 1;
        }
    }
    ensure!(count > 0, "no frozen local guide support");
    let expected = sum.map(|v| (v / count as f64) as f32);
    let originals: Vec<_> = inputs
        .originals
        .iter()
        .enumerate()
        .map(|(i, s)| OriginalView {
            acquisition_id: inputs.acquisitions[i] as u64,
            source: s.as_ref(),
            color_pulls: inputs.pulls[i],
            noise: inputs.noise,
            gain: inputs.gains[i],
            frozen_expected_rgb: expected,
        })
        .collect();
    let window = Window {
        full: l.full,
        center_sensor: [
            l.origin_sensor[0] + (l.width - 1) as f64 * l.step_sensor[0] * 0.5,
            l.origin_sensor[1] + (l.height - 1) as f64 * l.step_sensor[1] * 0.5,
        ],
        side_quad: window_side_quad,
    };
    let anchor = 3usize;
    let mut pairs = BTreeSet::new();
    for i in 0..inputs.acquisitions.len() {
        if i != anchor {
            pairs.insert((i.min(anchor), i.max(anchor)));
        }
    }
    // Adjacent non-anchor sources close an independently measured triangle
    // for every leaf, including four-source sets with an interior anchor.
    let neighbors: Vec<_> = (0..inputs.acquisitions.len())
        .filter(|&i| i != anchor)
        .collect();
    for pair in neighbors.windows(2) {
        pairs.insert((pair[0], pair[1]));
    }
    let reserved = local_registration_global::reservation_bytes(
        inputs.acquisitions.len(),
        pairs.len() * 3,
        window.side_quad,
    )
    .map_err(err)?;
    ensure!(
        reserved <= 64 << 20,
        "local corrected graph exceeds reserved64MiB"
    );
    let mut witnessed = Vec::new();
    let mut evidence = Vec::new();
    let mut measurements = Vec::new();
    let mut patch_census = Vec::new();
    for (i, j) in pairs {
        for color in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
            let witness = if patch_diagnostics {
                let diagnosed = local_registration::diagnostics::measure_pair(
                    &originals[i],
                    &originals[j],
                    window,
                    color,
                    policy,
                )
                .map_err(err)?;
                patch_census.push(json!({
                    "acquisitions": diagnosed.witnessed.evidence.acquisitions,
                    "color": format!("{color:?}"),
                    "original_crop_origins_quad": diagnosed.witnessed.evidence.original_crop_origins,
                    "tiles": diagnosed.tiles.iter().map(|t| json!({
                        "index": t.index,
                        "training": t.training,
                        "reference_origin_crop_quad": t.reference_origin_crop_quad,
                        "seed": diagnostic_probe(t.seed),
                        "fitted": t.fitted.map(diagnostic_probe),
                        "retained_heldout": t.retained_heldout,
                    })).collect::<Vec<_>>(),
                }));
                diagnosed.witnessed
            } else {
                measure_pair_with_footprints(&originals[i], &originals[j], window, color, policy)
                    .map_err(err)?
            };
            let result = &witness.evidence;
            measurements.push(json!({"acquisitions":result.acquisitions,"color":format!("{color:?}"),"original_crop_origins_quad":result.original_crop_origins,"input_color_pulls":result.input_color_pulls.map(pull_json),"training_tiles":result.trained_tiles,"heldout":result.heldout_tiles.iter().map(|h|json!({"reference_quad_global":h.reference_quad_global,"measured_moving_quad_global":h.measured_moving_quad_global,"saved_error_anchor_sensor":h.saved_error_anchor_sensor,"refined_error_anchor_sensor":h.refined_error_anchor_sensor,"peak":h.peak,"information_ratio":h.information_ratio})).collect::<Vec<_>>(),"fit_rms_source_quad":finite_number(f64::from(result.raw_fit_rms_source_quad)),"fitted_pair":result.fitted_pair_global.map(pull_json),"maximum_saved_disagreement_sensor":finite_number(result.maximum_saved_disagreement_sensor),"maximum_refined_disagreement_sensor":finite_number(result.maximum_refined_disagreement_sensor),"saved_map_supported":result.saved_map_supported,"refined_map_supported":result.refined_map_supported,"refusal":result.refusal,"reservation_bytes":result.reservation_bytes}));
            evidence.push(result.clone());
            witnessed.push(witness);
        }
    }
    let nodes: Vec<_> = originals
        .iter()
        .map(|s| Node {
            acquisition: s.acquisition_id,
            color_pulls: s.color_pulls,
        })
        .collect();
    let last = l.position(l.width - 1, l.height - 1);
    let origin = l.origin_sensor;
    let domain = Domain {
        full: l.full,
        corners_sensor: [origin, [last[0], origin[1]], [origin[0], last[1]], last],
    };
    let baseline_graph = certify(
        &nodes,
        anchor,
        domain,
        &evidence,
        local_registration_graph::Policy::default(),
    )
    .map_err(err)?;
    let (graph, correction) = if refine {
        let corrected = local_registration_global::solve(
            &nodes,
            anchor,
            domain,
            &witnessed,
            local_registration_graph::Policy::default(),
            64 << 20,
        )
        .map_err(err)?;
        let detail = json!({"source_sha256":hex(&Sha256::digest(include_bytes!("../../../../crates/strehl-core/src/reconstruction-registration-global.rs"))),"graph_wide_original_footprints_disjoint":true,"training_edges_rgb":corrected.training_edges_rgb,"training_cycle_rank_rgb":corrected.training_cycle_rank_rgb,"reservation_bytes":corrected.reservation_bytes,"solver":"direct training fits, fixed unit weights,1IRLS,no smoothness prior; exact original heldout measurements rescored at returned pulls","baseline_passed_edges_rgb":baseline_graph.passed_edges_rgb,"baseline_cycle_rank_rgb":baseline_graph.cycle_rank_rgb,"rescored_pairs":corrected.pairs.iter().map(|e|json!({"acquisitions":e.acquisitions,"color":format!("{:?}",e.plane),"heldout_error_sensor":finite_number(e.maximum_saved_disagreement_sensor),"supported":e.saved_map_supported})).collect::<Vec<_>>()});
        (corrected.certificate, Some(detail))
    } else {
        (baseline_graph, None)
    };
    let admitted: Vec<_> = graph
        .sources
        .iter()
        .map(|s| s.admitted_rgb.iter().all(|v| *v))
        .collect();
    let bound_sensor: Vec<_> = graph
        .sources
        .iter()
        .map(|s| {
            if s.admitted_rgb.iter().all(|v| *v) {
                s.direct_anchor_max_error_sensor
                    .iter()
                    .copied()
                    .fold(0f64, f64::max) as f32
            } else {
                1.
            }
        })
        .collect();
    let report = json!({"schema":"strehl.sr-local-registration-pilot.v1","source_sha256":hex(&Sha256::digest(include_bytes!("local-registration-pilot.rs"))),"measurement_sha256":hex(&Sha256::digest(include_bytes!("../../../../crates/strehl-core/src/reconstruction-registration.rs"))),"footprint_sha256":hex(&Sha256::digest(include_bytes!("../../../../crates/strehl-core/src/reconstruction-registration-footprint.rs"))),"graph_sha256":hex(&Sha256::digest(include_bytes!("../../../../crates/strehl-core/src/reconstruction-registration-graph.rs"))),"correction":correction,"anchor_acquisition":graph.anchor_acquisition,"full_geometry_quad":[l.full.width,l.full.height],"roi_sensor_origin":l.origin_sensor,"roi_output_dimensions":[l.width,l.height],"native_window_center_sensor":window.center_sensor,"native_window_side_sensor":2*window.side_quad,"frozen_guide_expected_camera_rgb":expected,"calibrated_noise":format!("{:?}",inputs.noise),"policy":{"geometry_lowpass_sigma_quad":policy.geometry_lowpass_sigma_quad,"tile_quad":policy.tile_quad,"grid_axis":policy.grid_axis,"radius_quad":policy.radius_quad,"minimum_peak":policy.minimum_peak,"minimum_gradient_variances":policy.minimum_gradient_variances,"minimum_information_ratio":policy.minimum_information_ratio,"minimum_train":policy.minimum_train,"minimum_heldout":policy.minimum_heldout,"maximum_saved_error_sensor":policy.maximum_saved_disagreement_sensor,"maximum_cycle_error_sensor":local_registration_graph::Policy::default().maximum_cycle_error_sensor},"sources":graph.sources.iter().enumerate().map(|(i,s)|json!({"acquisition":s.acquisition,"consuming_color_pulls":s.consuming_color_pulls.map(pull_json),"admitted_rgb":s.admitted_rgb,"admitted_all_rgb":admitted[i],"direct_anchor_max_error_sensor":s.direct_anchor_max_error_sensor.map(finite_number),"passed_anchor_triangles_rgb":s.passed_anchor_triangles_rgb})).collect::<Vec<_>>(),"passed_edges_rgb":graph.passed_edges_rgb,"components_rgb":graph.components_rgb,"cycle_rank_rgb":graph.cycle_rank_rgb,"tested_anchor_triangles_rgb":graph.tested_anchor_triangles_rgb,"passed_anchor_triangles_rgb":graph.passed_anchor_triangles_rgb,"maximum_cycle_error_sensor_rgb":graph.maximum_cycle_error_sensor_rgb,"pair_measurements":measurements,"seconds":started.elapsed().as_secs_f64(),"interpretation":"Anchor-relative heldout pair and cycle consistency under native image model; not calibrated statistical sigma or absolute RGB optical calibration. Uses unaligned original CFA patches; guide predicts noise only. Optional correction returns direct globally fitted local consuming placements; saved session map remains unchanged.","overlap_limitation":"Exact original-site sets include finite Gaussian/clipping dependencies, seed eligibility, all training iterations and final held probes; overlap refuses the entire pair. Independence from historical global alignment tile footprints is not established; temporal focus/photometric mismatch remains a possible correlated bias."});
    let mut report = report;
    if patch_diagnostics {
        report["patch_diagnostics"] = json!({
            "source_sha256": hex(&Sha256::digest(include_bytes!("../../../../crates/strehl-core/src/reconstruction-registration-diagnostics.rs"))),
            "scope": "Post-estimator seed/fitted probes, including previously ineligible patches; never consumed by fit, admission, footprints or certificate. Fitted probes reconstruct local coordinates from the reported full-gauge fit.",
            "pairs": patch_census,
        });
    }
    Ok(Measured {
        admitted,
        bound_sensor,
        report,
        consuming_pulls: graph
            .sources
            .iter()
            .map(|s| s.consuming_color_pulls)
            .collect(),
    })
}

fn diagnostic_probe(p: local_registration::diagnostics::Probe) -> Value {
    json!({
        "reference_derivatives_supported": p.reference_derivatives_supported,
        "original_search_supported": p.original_search_supported,
        "information": p.information.map(|v| json!({
            "minimum_eigenvalue": v.minimum_eigenvalue,
            "maximum_eigenvalue": v.maximum_eigenvalue,
            "minimum_eigenvalue_required": v.minimum_eigenvalue_required,
            "ratio": v.ratio,
            "minimum_ratio": v.minimum_ratio,
            "accepted": v.accepted,
        })),
        "ncc": p.ncc.map(|v| json!({
            "status": format!("{:?}", v.status),
            "contrast": v.contrast,
            "peak": v.peak,
            "displacement_quad": [v.dx, v.dy],
        })),
    })
}
