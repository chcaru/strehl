// Reviewer-owned addition. Inherit the earlier independently enumerated dense
// oracle; never use the candidate adjoint to construct the reference solution.
use super::*;

fn trace_record(s: &operator::Solve) -> Value {
    json!({"solve": solver_json(s), "restart_applied": s.restart_applied,
        "trace": s.residual_trace})
}

fn trace_consistent(s: &operator::Solve) -> bool {
    let restarts = s.residual_trace.iter().filter(|r| r.restart_applied).collect::<Vec<_>>();
    restarts.len() <= 1
        && s.restart_applied == !restarts.is_empty()
        && restarts.iter().all(|r| r.iteration == 8
            && (r.error_bound_rms > ERROR_DN || r.objective > s.initial_objective))
        && s.residual_trace.iter().all(|r| r.actual_residual_norm.is_finite()
            && r.recursive_residual_norm.is_finite() && r.residual_gap_norm.is_finite()
            && r.error_bound_rms.is_finite() && r.objective.is_finite())
        && s.residual_trace.last().is_some_and(|r| r.iteration == s.iterations)
}

#[test]
fn independent_restart_challenge() {
    let out = PathBuf::from(std::env::var_os("STREHL_RECONSTRUCTION_RESTART_CONTROL_OUT")
        .expect("root output required"));
    std::fs::create_dir(&out).unwrap();
    assert_eq!(operator::MAX_ITERATIONS, 32);
    assert_eq!(operator::RESTART_ITERATION, 8);
    assert_eq!(operator::ERROR_RMS_LIMIT, ERROR_DN);

    // A different high-DN target from the earlier 8192-DN edge/corner fixture.
    // Odd boundaries and signed distributed AC/coarse perturbations make a
    // genuinely inconsistent target, without a model-derived claimed image.
    let (w, h) = (17usize, 19usize);
    let sizes = level_sizes(w, h, 1);
    let oracle = Dense::new(&sizes);
    let truth = (0..w*h).map(|j| {
        let (x, y) = (j % w, j / w);
        14500.0 + ((x*29+y*47)%37) as f32*7.0
            + if 2*x+y > 22 { 631.0 } else { -257.0 }
    }).collect::<Vec<_>>();
    let mut target = direct_analysis(&sizes, &truth);
    for (k, band) in target.iter_mut().enumerate() {
        for (j, value) in band.iter_mut().enumerate() {
            *value += if (j*11+k*7)%13 < 5 { 227.0 } else { -311.0 };
        }
    }
    let target_before = target.clone();
    let initial = direct_collapse(&sizes, &target);
    let expected = oracle.solve(&flat_bands(&target));
    let solved = operator::reconstruct(&sizes, &target, &initial).unwrap();
    let short = operator::reconstruct_with_cap(&sizes, &target, &initial, 1).unwrap();
    let error = (solved.image.iter().zip(&expected)
        .map(|(a,b)| (f64::from(*a)-b).powi(2)).sum::<f64>()/(w*h) as f64).sqrt();
    let challenge_pass = admitted(&solved) && oracle_ok(&solved.image, &expected)
        && max_error(&initial, &expected) > 1.0 && solved.objective < solved.initial_objective
        && exact(&target, &target_before) && trace_consistent(&solved);
    let refusal_pass = !admitted(&short) && !short.converged && short.refusal.is_some()
        && short.iterations == 1 && !short.restart_applied && trace_consistent(&short);
    let record = json!({"status":"NUMERICAL_CHALLENGE_OBSERVED", "dimensions":[w,h],
        "high_dn_inconsistent":trace_record(&solved), "dense_oracle_rms_dn":error,
        "dense_oracle_max_dn":max_error(&solved.image,&expected),
        "initial_oracle_max_dn":max_error(&initial,&expected),
        "target_unchanged":exact(&target,&target_before), "challenge_pass":challenge_pass,
        "one_iteration_foil":trace_record(&short), "insufficient_solve_refused":refusal_pass,
        "scope":"Fixed 32/.02 criteria. Tiny case need not reach restart; full bound cache must exercise it. Dense oracle tests numerical inference, not image quality."});
    write(&out.join("numerical-challenge.json"), &record);
    assert!(challenge_pass, "independent high-DN inconsistent target failed; retained diagnostics");
    assert!(refusal_pass, "actual insufficient solve failed to refuse; retained diagnostics");

    // Exact source null goes through the actual gather, fields, merge, hull and
    // final MHC. It is not a synthetic coefficient-only identity shortcut.
    let noise = profile::noise_model_for("ILCE-7CM2", Some(100.0), levels());
    let t = transforms()[0];
    let frame = fixture(Scene::Radial, 0, t, 100.0, &noise);
    let before = vec![hash(&frame.data)];
    let frames = vec![frame];
    let c = compare_generated(&frames, &[t], crop(), &noise,
        MergeConfig::default(), Mode::Consistent).unwrap();
    let pixels_exact = exact(&c.baseline_planes4, &c.candidate_planes4)
        && exact(&c.baseline_pre_hull_planes4, &c.candidate_pre_hull_planes4)
        && c.baseline_rgb.iter().zip(&c.candidate_rgb).all(|(a,b)|a.to_bits()==b.to_bits());
    let null_pass = c.candidate_valid && pixels_exact && c.held_state_bit_exact
        && before[0] == hash(&frames[0].data)
        && c.solves.iter().all(|s| admitted(s) && trace_consistent(s) && !s.restart_applied);
    write(&out.join("screen.json"), &json!({"status":"RESTART_INDEPENDENT_CONTROLS_OBSERVED",
        "high_dn_challenge":record, "single_source_null":{"pass":null_pass,
        "exact_cfa_pre_and_post_hull_and_final_rgb":pixels_exact,
        "source_sha256":before[0], "source_unchanged":before[0]==hash(&frames[0].data),
        "held_state_bit_exact":c.held_state_bit_exact,
        "solves":c.solves.iter().map(trace_record).collect::<Vec<_>>()},
        "all_pass":challenge_pass && refusal_pass && null_pass,
        "photographic_admission":false}));
    checks(&c, &frames, &before);
    assert!(null_pass, "single-source reconstruction changed actual output; retained diagnostics");
}
