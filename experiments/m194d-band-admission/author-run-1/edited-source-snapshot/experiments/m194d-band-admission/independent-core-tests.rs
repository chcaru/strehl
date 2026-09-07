// Independent controls frozen by independent-design.md, before candidate runs.
// Included inside pyramid::m194d_independent_tests; no production-copy operator.
use super::*;
use std::panic::{AssertUnwindSafe, catch_unwind};

const W: usize = 80;
const H: usize = 64;
const BASE: f32 = 4096.0;
const TOL: f32 = 0.004;

fn cfg(mode: AdmissionMode, p: f32) -> MergeConfig {
    MergeConfig {
        admission: mode,
        bands: 1,
        gate: 2.0,
        exponent: p,
        sharpen_per_octave: 1.0,
        select: SelectMode::SoftPower,
        base: BaseBand::Mean,
        fallback: Fallback::Mean,
        mean_coarse: 0,
        significance_scale: 0.0,
        hull: Hull::InputRange,
        ..MergeConfig::default()
    }
}

fn stripe(amplitude: f32, base: f32) -> Vec<f32> {
    (0..W * H)
        .map(|j| {
            base + if (j / W) % 2 == 0 {
                amplitude
            } else {
                -amplitude
            }
        })
        .collect()
}

fn interior() -> impl Iterator<Item = usize> {
    (16..48).flat_map(|y| (16..64).map(move |x| y * W + x))
}

// The cutoff arm is a labelled counterfactual: use actual candidate partials,
// erase only their below-floor band numerator/denominator, then actual absorb.
// It is never available to the benchmark or called a production mode.
fn row_merge(
    mode: AdmissionMode,
    floor: f32,
    amplitude: f32,
    reset: bool,
    cutoff: bool,
) -> Vec<f32> {
    let config = cfg(mode, 2.0);
    let mut sum = BandMerge::new(W, H, 1, config);
    let mut work = FrameWorkspace::new(sum.sizes(), 1);
    let variance = vec![floor / 2.0; W * H];
    let mut active_energy_sites = 0;
    for k in 0..5 {
        let field = stripe(if k == 3 { amplitude } else { 0.0 }, BASE);
        if reset {
            work.next_frame();
        }
        let mut part = BandMerge::new(W, H, 1, config);
        part.add_frame_with_gain(&[&field], &field, &variance, Some(&[1.0]), &mut work);
        for j in interior() {
            let expected = if k == 3 { amplitude * amplitude } else { 0.0 };
            assert_eq!(work.sq[j], expected, "registered energy did not occur");
            if k == 3 {
                active_energy_sites += 1;
                let expected_sign = expected.partial_cmp(&floor).unwrap();
                assert_eq!(
                    (work.sq[j] - floor).partial_cmp(&0.0).unwrap(),
                    expected_sign
                );
            }
        }
        if cutoff {
            for j in 0..W * H {
                if work.sq[j] <= floor {
                    part.num[0][j] = 0.0;
                    part.den[0][j] = 0.0;
                }
            }
        }
        sum.absorb(&part);
    }
    assert_eq!(sum.frames(), 5);
    assert_eq!(active_energy_sites, 48 * 32);
    assert!(sum.num.iter().flatten().all(|x| x.is_finite()));
    assert!(sum.den.iter().flatten().all(|x| x.is_finite()));
    let mut work = Workspace::new(sum.sizes());
    sum.finish(&mut work).remove(0)
}

fn residual_error(image: &[f32], amplitude: f64) -> f32 {
    interior()
        .map(|j| {
            let s = if (j / W) % 2 == 0 { 1.0 } else { -1.0 };
            (image[j] as f64 - (BASE as f64 + s * amplitude)).abs() as f32
        })
        .fold(0.0, f32::max)
}

#[test]
fn independent_threshold_cutoff_and_strong_detail() {
    for floor in [99.9375_f32, 100.0, 100.0625] {
        let a = ((100.0_f64 - floor as f64).max(0.0)) / floor as f64;
        let share = (1.0 + a * a) / (5.0 + a * a);
        let candidate = row_merge(AdmissionMode::FloorPedestalV1, floor, 10.0, true, false);
        let legacy = row_merge(AdmissionMode::HardFloor, floor, 10.0, true, false);
        let cutoff = row_merge(AdmissionMode::FloorPedestalV1, floor, 10.0, true, true);
        let error = residual_error(&candidate, 10.0 * share);
        assert!(error <= TOL, "candidate boundary formula error {error}");
        let expected_cutoff = if floor < 100.0 { 10.0 } else { 2.0 };
        assert!(residual_error(&legacy, expected_cutoff) <= TOL);
        assert!(residual_error(&cutoff, expected_cutoff) <= TOL);
        if floor < 100.0 {
            assert!(interior().all(|j| (candidate[j] - cutoff[j]).abs() > 5.0));
        }
        println!(
            "M194D_INDEPENDENT_CORE boundary floor={floor} share={share:.12} max_error={error} candidate_even={} legacy_even={} cutoff_even={}",
            candidate[24 * W + 32],
            legacy[24 * W + 32],
            cutoff[24 * W + 32]
        );
    }
    let floor = 99.9375_f32;
    let a = (96.0_f64.powi(2) - floor as f64) / floor as f64;
    let share = (1.0 + a * a) / (5.0 + a * a);
    assert!(share > 0.999);
    let strong = row_merge(AdmissionMode::FloorPedestalV1, floor, 96.0, true, false);
    assert!(residual_error(&strong, 96.0 * share) <= TOL);
    assert!(residual_error(&strong, 96.0) < residual_error(&strong, 19.2));
    println!(
        "M194D_INDEPENDENT_CORE strong share={share:.12} error={} mean_destroyer_error={}",
        residual_error(&strong, 96.0 * share),
        residual_error(&strong, 19.2)
    );
}

#[test]
#[should_panic(expected = "M194d missing-reset lifecycle control loses the live stripe")]
fn independent_missing_reset_failure_retained() {
    let broken = row_merge(AdmissionMode::FloorPedestalV1, 99.9375, 10.0, false, false);
    assert!(
        residual_error(&broken, 2.0) <= TOL,
        "M194d missing-reset lifecycle control loses the live stripe"
    );
}

fn reference_weight(energy: f64, floor: f64, p: f64) -> f64 {
    let a = (energy - floor).max(0.0) / floor.max(1.0);
    // Independent arithmetic uses squared norm and powf away from overflow;
    // the extremes below explicitly inspect the prescribed log cap.
    ((1.0 + a * a).sqrt() / 64.0).powf(p)
}

#[test]
fn independent_units_order_and_numerical_edges() {
    assert_eq!(MergeConfig::default().admission, AdmissionMode::HardFloor);
    let mut count = 0;
    for p in [1.0_f32, 2.0, 2.8, 3.92, 8.0] {
        let mut last = 0.0;
        for energy in [
            0.0_f32,
            100.0,
            f32::from_bits(100.0_f32.to_bits() + 1),
            100.0625,
            200.0,
            10000.0,
        ] {
            let w = pedestal_weight(energy, 100.0, p);
            let expected = reference_weight(energy as f64, 100.0, p as f64);
            assert!(w.is_finite() && w > 0.0 && w >= last);
            assert!(((w as f64 / expected) - 1.0).abs() < 2.0e-5);
            last = w;
            count += 1;
        }
        assert!(pedestal_weight(0.0, 100.0, p) > f32::MIN_POSITIVE);
        assert_eq!(
            pedestal_weight(0.0, 100.0, p),
            pedestal_weight(1.0, 1000.0, p)
        );
        let w1 = pedestal_weight(160.0, 40.0, p);
        let w2 = pedestal_weight(1440.0, 360.0, p);
        assert!((w1 / w2 - 1.0).abs() < 1.0e-6, "F>=1 unit covariance");
        let clipped_units = pedestal_weight(1.25, 0.25, p);
        let rescaled_units = pedestal_weight(11.25, 2.25, p);
        assert_ne!(
            clipped_units.to_bits(),
            rescaled_units.to_bits(),
            "max(F,1) expected noncovariance lost"
        );
        assert!(pedestal_weight(100.0, 20.0, p) > pedestal_weight(100.0, 80.0, p));
    }
    let saturated = pedestal_weight(16384.0_f32.powi(2), 1.0, 8.0);
    assert!(saturated.is_finite());
    assert!((saturated / 80.0_f32.exp() - 1.0).abs() < 1.0e-6);
    assert!(!(saturated * 16384.0).is_finite());
    for (e, f, p) in [
        (f32::NAN, 1.0, 2.0),
        (f32::INFINITY, 1.0, 2.0),
        (1.0, f32::NAN, 2.0),
        (1.0, f32::INFINITY, 2.0),
        (-1.0, 1.0, 2.0),
        (1.0, -1.0, 2.0),
        (1.0, 1.0, 0.0),
        (1.0, 1.0, 9.0),
    ] {
        assert!(
            catch_unwind(|| pedestal_weight(e, f, p)).is_err(),
            "invalid helper accepted {e}/{f}/{p}"
        );
    }
    println!(
        "M194D_INDEPENDENT_CORE units helper_cases={count} expected_below_one_noninvariance=true cap_product_overflow=true invalid_inputs_refused=8"
    );
}

fn assert_refuses(label: &str, action: impl FnOnce()) {
    let error = catch_unwind(AssertUnwindSafe(action))
        .expect_err(&format!("numeric refusal missing: {label}"));
    let message = error
        .downcast_ref::<String>()
        .map(String::as_str)
        .or_else(|| error.downcast_ref::<&str>().copied())
        .unwrap_or("nontext panic");
    assert!(
        message.contains("FloorPedestalV1") || message.contains("different admission mode"),
        "wrong refusal for {label}: {message}"
    );
    println!("M194D_INDEPENDENT_CORE refused={label} reason={message:?}");
}

#[test]
fn independent_numeric_refusal_before_hull() {
    assert_refuses("finite-input-weighted-product", || {
        let mut merge = BandMerge::new(W, H, 1, cfg(AdmissionMode::FloorPedestalV1, 8.0));
        let mut work = FrameWorkspace::new(merge.sizes(), 1);
        let field = stripe(16384.0, 24576.0);
        assert!(field.iter().all(|x| *x >= 0.0 && *x <= 65535.0));
        for _ in 0..2 {
            work.next_frame();
            merge.add_frame_with_gain(
                &[&field],
                &field,
                &vec![0.5; W * H],
                Some(&[1.0]),
                &mut work,
            );
        }
    });
    assert_refuses("finite-partial-numerator-absorb", || {
        let mut left = BandMerge::new(W, H, 1, cfg(AdmissionMode::FloorPedestalV1, 2.0));
        let mut right = left.clone();
        left.num[0][20 * W + 20] = f32::MAX * 0.75;
        right.num[0][20 * W + 20] = f32::MAX * 0.75;
        left.absorb(&right);
    });
    for field in ["num", "den", "usum"] {
        assert_refuses(&format!("nonfinite-{field}-absorb"), || {
            let mut left = BandMerge::new(W, H, 1, cfg(AdmissionMode::FloorPedestalV1, 2.0));
            let mut right = left.clone();
            let target = match field {
                "num" => &mut right.num,
                "den" => &mut right.den,
                _ => &mut right.usum,
            };
            target[0][0] = f32::NAN;
            left.absorb(&right);
        });
    }
    assert_refuses("finite-state-resolved-division", || {
        let mut merge = BandMerge::new(W, H, 1, cfg(AdmissionMode::FloorPedestalV1, 2.0));
        merge.frames = 1;
        merge.lo[0].fill(1000.0);
        merge.hi[0].fill(2000.0);
        merge.num[0][20 * W + 20] = f32::MAX * 0.5;
        merge.den[0][20 * W + 20] = 0.25;
        let mut work = Workspace::new(merge.sizes());
        let _ = merge.finish(&mut work);
    });
    assert_refuses("finite-coefficients-collapse-before-hull", || {
        let mut merge = BandMerge::new(W, H, 1, cfg(AdmissionMode::FloorPedestalV1, 2.0));
        merge.frames = 1;
        merge.lo[0].fill(1000.0);
        merge.hi[0].fill(2000.0);
        // Both resolved levels are finite; their reconstruction sum is not.
        for k in 0..merge.sizes.len() {
            merge.num[k].fill(f32::MAX * 0.75);
            merge.den[k].fill(1.0);
        }
        let mut work = Workspace::new(merge.sizes());
        let _ = merge.finish(&mut work);
    });
}

#[test]
fn independent_config_refusal_and_storage_bound() {
    let good = cfg(AdmissionMode::FloorPedestalV1, 2.0);
    let mut variants = Vec::new();
    let mut c = good;
    c.gate = 0.0;
    variants.push(c);
    let mut c = good;
    c.gate = f32::NAN;
    variants.push(c);
    let mut c = good;
    c.exponent = 9.0;
    variants.push(c);
    let mut c = good;
    c.exponent = f32::NAN;
    variants.push(c);
    let mut c = good;
    c.significance_scale = 1.0;
    variants.push(c);
    let mut c = good;
    c.mean_coarse = 1;
    variants.push(c);
    let mut c = good;
    c.select = SelectMode::HardMax;
    variants.push(c);
    let mut c = good;
    c.base = BaseBand::WeightedFromCoarsest;
    variants.push(c);
    let mut c = good;
    c.hull = Hull::PerLevel;
    variants.push(c);
    let mut c = good;
    c.fallback = Fallback::Best;
    variants.push(c);
    for (i, bad) in variants.into_iter().enumerate() {
        assert_refuses(&format!("unsupported-config-{i}"), || {
            let _ = BandMerge::new(W, H, 1, bad);
        });
    }
    assert_refuses("mixed-mode-absorb", || {
        let mut a = BandMerge::new(W, H, 1, good);
        let b = BandMerge::new(W, H, 1, cfg(AdmissionMode::HardFloor, 2.0));
        a.absorb(&b);
    });
    for bands in [1, 3] {
        let mut candidate_cfg = good;
        candidate_cfg.bands = bands;
        let mut legacy_cfg = candidate_cfg;
        legacy_cfg.admission = AdmissionMode::HardFloor;
        let candidate = BandMerge::new(W, H, 3, candidate_cfg);
        let legacy = BandMerge::new(W, H, 3, legacy_cfg);
        assert_eq!(candidate.accumulator_floats(), legacy.accumulator_floats());
        assert_eq!(
            FrameWorkspace::new(candidate.sizes(), 3).floats(),
            FrameWorkspace::new(legacy.sizes(), 3).floats()
        );
    }
    println!("M194D_INDEPENDENT_CORE config_refusals=11 unchanged_retained_array_counts=true");
}
