use super::*;
use std::panic::{AssertUnwindSafe, catch_unwind};

fn cfg(mode: AdmissionMode, p: f32) -> MergeConfig {
    MergeConfig {
        bands: 1,
        gate: 2.0,
        exponent: p,
        sharpen_per_octave: 1.0,
        admission: mode,
        hull: Hull::Unclamped,
        significance_scale: 0.0,
        mean_coarse: 0,
        ..MergeConfig::default()
    }
}

fn checker(width: usize, height: usize, amplitude: f32, background: f32) -> Vec<f32> {
    (0..width * height)
        .map(|i| {
            background
                + if (i % width + i / width) % 2 == 0 {
                    amplitude
                } else {
                    -amplitude
                }
        })
        .collect()
}

fn fold(
    mode: AdmissionMode,
    n: usize,
    active: usize,
    amplitude: f32,
    floor: f32,
    p: f32,
    background: f32,
) -> Vec<f32> {
    let (width, height) = (96, 80);
    let config = cfg(mode, p);
    let mut merge = BandMerge::new(width, height, 1, config);
    let mut workspace = FrameWorkspace::new(merge.sizes(), 1);
    let variance = vec![floor / config.gate; width * height];
    for index in 0..n {
        let a = if index == active { amplitude } else { 0.0 };
        let luma = checker(width, height, a, 0.0);
        let plane = checker(width, height, a, background);
        workspace.next_frame();
        merge.add_frame_with_gain(&[&plane], &luma, &variance, Some(&[1.0]), &mut workspace);
    }
    merge.finish(&mut Workspace::new(merge.sizes())).remove(0)
}

#[test]
fn author_weight_formula_domain_and_caps() {
    for p in [1.0, 2.0, 3.92, 8.0] {
        for floor in [0.0_f32, 0.25, 1.0, 64.0, 1e12] {
            let mut previous = 0.0;
            for a in [0.0_f32, 1.0 / 1024.0, 0.5, 1.0, 4.0, 32.0, 1000.0] {
                let energy = floor + a * floor.max(1.0);
                let observed = pedestal_weight(energy, floor, p);
                let excess = (f64::from(energy) - f64::from(floor)).max(0.0);
                let r = (excess / f64::from(floor.max(1.0))).hypot(1.0) / 64.0;
                let expected = (f64::from(p) * r.ln()).clamp(-80.0, 80.0).exp();
                assert!((f64::from(observed) / expected - 1.0).abs() < 8e-6);
                assert!(observed.is_finite() && observed > 0.0 && observed >= previous);
                previous = observed;
            }
        }
    }
    let saturated = pedestal_weight(f32::MAX, 0.0, 8.0);
    assert_eq!(saturated, 80.0_f32.exp());
    assert_eq!(pedestal_weight(0.0, 1.0, 8.0), (-8.0 * 64.0_f32.ln()).exp());
    let a = 1000.0_f32;
    let ratio = pedestal_weight(1.0 + a, 1.0, 2.0) / select_weight(a, 1.0, 2.0, 0.0);
    assert!((ratio - (1.0 + 1.0 / (a * a))).abs() < 2e-6);
    for (e, f, p) in [
        (f32::NAN, 1.0, 2.0),
        (f32::INFINITY, 1.0, 2.0),
        (-1.0, 1.0, 2.0),
        (1.0, f32::NAN, 2.0),
        (1.0, -1.0, 2.0),
        (1.0, 1.0, 0.0),
        (1.0, 1.0, 9.0),
    ] {
        assert!(catch_unwind(|| pedestal_weight(e, f, p)).is_err());
    }
}

#[test]
fn author_actual_near_threshold_and_high_contrast() {
    let floor = 64.0 / (1.0 + 2.0_f32.powi(-10));
    let legacy = fold(AdmissionMode::HardFloor, 9, 0, 8.0, floor, 2.0, 3000.0);
    let near = fold(
        AdmissionMode::FloorPedestalV1,
        9,
        0,
        8.0,
        floor,
        2.0,
        3000.0,
    );
    let high = fold(
        AdmissionMode::FloorPedestalV1,
        9,
        0,
        128.0,
        floor,
        2.0,
        3000.0,
    );
    let r = 1.0 + ((64.0_f64 - f64::from(floor)) / f64::from(floor)).powi(2);
    let share = r / (8.0 + r);
    let high_r = 1.0 + ((128.0_f64.powi(2) - f64::from(floor)) / f64::from(floor)).powi(2);
    let high_share = high_r / (8.0 + high_r);
    assert!(high_share > 0.99);
    let mut changed = false;
    for y in 16..64 {
        for x in 16..80 {
            let i = y * 96 + x;
            let sign = if (x + y) % 2 == 0 { 1.0 } else { -1.0 };
            assert!((f64::from(legacy[i]) - (3000.0 + sign * 8.0)).abs() <= 0.002);
            assert!((f64::from(near[i]) - (3000.0 + sign * 8.0 * share)).abs() <= 0.002);
            assert!((f64::from(high[i]) - (3000.0 + sign * 128.0 * high_share)).abs() <= 0.002);
            changed |= (legacy[i] - near[i]).abs() > 1.0;
            assert!(
                (f64::from(high[i]) - (3000.0 + sign * 128.0)).abs()
                    < (f64::from(high[i]) - (3000.0 + sign * 128.0 / 9.0)).abs()
            );
        }
    }
    assert!(changed, "singleton intervention was inert");
}

#[test]
fn author_equal_below_floor_mean_and_bounded_state() {
    let (width, height) = (96, 80);
    let mut merge = BandMerge::new(width, height, 1, cfg(AdmissionMode::FloorPedestalV1, 2.0));
    let mut workspace = FrameWorkspace::new(merge.sizes(), 1);
    let luma = vec![0.0; width * height];
    let capacity = |m: &BandMerge| {
        m.num
            .iter()
            .chain(&m.den)
            .chain(&m.usum)
            .chain(&m.lo)
            .chain(&m.hi)
            .map(Vec::capacity)
            .sum::<usize>()
    };
    let initial_capacity = capacity(&merge);
    for index in 0..17 {
        let plane = checker(width, height, index as f32, 3000.0);
        let variance = vec![1.0 + index as f32; width * height];
        workspace.next_frame();
        merge.add_frame_with_gain(&[&plane], &luma, &variance, Some(&[1.0]), &mut workspace);
        assert_eq!(capacity(&merge), initial_capacity);
    }
    let output = merge.finish(&mut Workspace::new(merge.sizes())).remove(0);
    for y in 16..64 {
        for x in 16..80 {
            let expected = 3000.0 + if (x + y) % 2 == 0 { 8.0 } else { -8.0 };
            assert!((output[y * width + x] - expected).abs() <= 0.002);
        }
    }
    assert_eq!(merge.frames, 17);
    let small = pedestal_weight(100.0, 50.0, 2.0);
    let large = pedestal_weight(100.0, 90.0, 2.0);
    assert!(small > large);
    assert_eq!(
        pedestal_weight(0.0, 50.0, 2.0),
        pedestal_weight(0.0, 90.0, 2.0)
    );
}

#[test]
fn author_overflow_refuses_before_clamp_and_configuration_is_explicit() {
    assert!(
        catch_unwind(|| fold(
            AdmissionMode::FloorPedestalV1,
            3,
            2,
            10000.0,
            1.0,
            8.0,
            20000.0
        ))
        .is_err()
    );
    let make = || {
        let mut m = BandMerge::new(
            32,
            32,
            1,
            MergeConfig {
                hull: Hull::InputRange,
                ..cfg(AdmissionMode::FloorPedestalV1, 2.0)
            },
        );
        m.frames = 1;
        m.den.iter_mut().for_each(|v| v.fill(1.0));
        m.lo.iter_mut().for_each(|v| v.fill(0.0));
        m.hi.iter_mut().for_each(|v| v.fill(65535.0));
        m
    };
    let mut a = make();
    let mut b = make();
    a.num[0][0] = f32::MAX * 0.75;
    b.num[0][0] = f32::MAX * 0.75;
    assert!(catch_unwind(AssertUnwindSafe(|| a.absorb(&b))).is_err());
    let mut m = make();
    m.num.iter_mut().for_each(|v| v.fill(f32::MAX * 0.75));
    assert!(catch_unwind(AssertUnwindSafe(|| m.finish(&mut Workspace::new(m.sizes())))).is_err());
    let mut m = make();
    m.num[0][0] = f32::MAX;
    m.den[0][0] = f32::MIN_POSITIVE;
    assert!(catch_unwind(AssertUnwindSafe(|| m.finish(&mut Workspace::new(m.sizes())))).is_err());
    let bad = [
        MergeConfig {
            significance_scale: 1.0,
            ..cfg(AdmissionMode::FloorPedestalV1, 2.0)
        },
        MergeConfig {
            select: SelectMode::HardMax,
            ..cfg(AdmissionMode::FloorPedestalV1, 2.0)
        },
        MergeConfig {
            hull: Hull::PerLevel,
            ..cfg(AdmissionMode::FloorPedestalV1, 2.0)
        },
        MergeConfig {
            gate: 0.0,
            ..cfg(AdmissionMode::FloorPedestalV1, 2.0)
        },
    ];
    for config in bad {
        assert!(catch_unwind(|| BandMerge::new(32, 32, 1, config)).is_err());
    }
    let mut off = BandMerge::new(32, 32, 1, cfg(AdmissionMode::HardFloor, 2.0));
    assert!(catch_unwind(AssertUnwindSafe(|| off.absorb(&make()))).is_err());
    assert_eq!(MergeConfig::default().admission, AdmissionMode::HardFloor);
}
