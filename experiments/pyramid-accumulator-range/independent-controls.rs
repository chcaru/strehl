// Include as a test-only child module of crate::pyramid. Root executes.
// The f64 reference shares the actual weights and decomposition deliberately:
// this tests accumulator range, not focus selection or camera calibration.
use super::*;

const W: usize = 256;
const H: usize = 256;
const CHANNELS: usize = 4;

fn config() -> MergeConfig {
    MergeConfig {
        bands: 7, gate: 2.0, exponent: 2.0, sharpen_per_octave: 1.4,
        select: SelectMode::SoftPower, admission: AdmissionMode::HardFloor,
        base: BaseBand::Mean, mean_coarse: 0, hull: Hull::InputRange,
        fallback: Fallback::Mean, significance_scale: 0.0,
        ..MergeConfig::default()
    }
}

fn checker(low: f32, high: f32) -> Vec<Vec<f32>> {
    [0.75_f32, 1.0, 1.0, 0.5].into_iter().map(|gain| {
        (0..W*H).map(|i| gain * if ((i % W) + (i / W)) % 2 == 0 { low } else { high }).collect()
    }).collect()
}

struct Observation {
    actual_nonfinite_num: usize,
    actual_nonfinite_den: usize,
    legacy_nonfinite_num: usize,
    actual_nonfinite_pre_hull: usize,
    actual_nonfinite_output: usize,
    finite_max_error: f32,
    reference: Vec<Vec<f32>>,
    actual: Vec<Vec<f32>>,
}

fn observe(label: &str, frames: &[Vec<Vec<f32>>], physical_variance: bool) -> Observation {
    let cfg = config();
    let sizes = level_sizes(W,H,cfg.bands);
    assert_eq!(sizes.len()-1,5);
    assert!(cfg.exponent_at(0,sizes.len()-1) > 7.6);
    let mut merge = BandMerge::new(W,H,CHANNELS,cfg);
    let mut actual_ws = FrameWorkspace::new(&sizes,CHANNELS);
    let mut num64: Vec<Vec<f64>> = (0..sizes.len()*CHANNELS).map(|k|vec![0.;sizes[k/CHANNELS].pixels()]).collect();
    let mut mean64 = num64.clone();
    let mut legacy32: Vec<Vec<f32>> = num64.iter().map(|v|vec![0.;v.len()]).collect();
    let mut den64: Vec<Vec<f64>> = sizes.iter().map(|s|vec![0.;s.pixels()]).collect();
    let noise = crate::profile::noise_model_for("ILCE-7CM2",Some(100.),crate::noise::Levels{black:512.,white:15360.});
    let mut max_weight = 0_f32;
    let mut max_coefficient = 0_f32;
    for frame in frames {
        assert_eq!(frame.len(),CHANNELS);
        assert!(frame.iter().flatten().all(|v|v.is_finite() && *v >= 0. && *v <= 15871.));
        let refs: Vec<&[f32]> = frame.iter().map(Vec::as_slice).collect();
        let luma: Vec<f32> = frame[1].iter().zip(&frame[2]).map(|(a,b)|(a+b)*0.5).collect();
        let mut variance = vec![4_f32;W*H];
        if physical_variance { luma_variance(&luma,&noise,&mut variance); }
        assert!(variance.iter().all(|v|v.is_finite() && *v > 0.));
        actual_ws.next_frame();
        merge.add_frame(&refs,&luma,&variance,&mut actual_ws);

        // A one-frame consumer exposes exactly its actual denominator (=w).
        // Its possibly overflowed numerator is never used by the reference.
        let mut one = BandMerge::new(W,H,CHANNELS,cfg);
        let mut one_ws = FrameWorkspace::new(&sizes,CHANNELS);
        one_ws.next_frame(); one.add_frame(&refs,&luma,&variance,&mut one_ws);
        let mut decomposed: Vec<Pyramid> = (0..CHANNELS).map(|_|Pyramid::zeros(&sizes)).collect();
        for c in 0..CHANNELS { decomposed[c].build(&frame[c],&mut Workspace::new(&sizes)); }
        for k in 0..sizes.len() {
            for j in 0..sizes[k].pixels() {
                let weight = one.den[k][j];
                assert!(weight.is_finite() && weight >= 0.,"nonfinite individual weight, outside numerator-only hypothesis");
                max_weight = max_weight.max(weight);
                den64[k][j] += f64::from(weight);
                for c in 0..CHANNELS {
                    let idx = k*CHANNELS+c;
                    let coefficient = decomposed[c].level(k)[j];
                    assert!(coefficient.is_finite());
                    max_coefficient = max_coefficient.max(coefficient.abs());
                    num64[idx][j] += f64::from(weight)*f64::from(coefficient);
                    mean64[idx][j] += f64::from(coefficient);
                    legacy32[idx][j] += weight*coefficient;
                }
            }
        }
    }
    assert!(num64.iter().flatten().chain(den64.iter().flatten()).all(|v|v.is_finite()));
    let mut reference = Vec::new();
    for c in 0..CHANNELS {
        let mut p = Pyramid::zeros(&sizes);
        for k in 0..sizes.len() {
            for j in 0..sizes[k].pixels() {
                p.level_mut(k)[j] = (if den64[k][j] > 0. { num64[k*CHANNELS+c][j]/den64[k][j] }
                    else { mean64[k*CHANNELS+c][j]/frames.len() as f64 }) as f32;
            }
        }
        let mut image = p.collapse(&mut Workspace::new(&sizes));
        assert!(image.iter().all(|v|v.is_finite()),"reference reconstruction failed");
        for (j,value) in image.iter_mut().enumerate() {
            let lo = frames.iter().map(|f|f[c][j]).fold(f32::INFINITY,f32::min);
            let hi = frames.iter().map(|f|f[c][j]).fold(f32::NEG_INFINITY,f32::max);
            *value=value.clamp(lo,hi);
        }
        reference.push(image);
    }
    let mut before_hull = merge.clone(); before_hull.cfg.hull=Hull::Unclamped;
    let pre = before_hull.finish(&mut Workspace::new(&sizes));
    let actual = merge.finish(&mut Workspace::new(&sizes));
    let count_bad = |v: &[Vec<f32>]| v.iter().flatten().filter(|v|!v.is_finite()).count();
    let finite_max_error = actual.iter().flatten().zip(reference.iter().flatten())
        .filter(|(a,_)|a.is_finite()).map(|(a,b)|(a-b).abs()).fold(0_f32,f32::max);
    let obs = Observation {
        actual_nonfinite_num:count_bad(&merge.num),actual_nonfinite_den:count_bad(&merge.den),
        legacy_nonfinite_num:count_bad(&legacy32),actual_nonfinite_pre_hull:count_bad(&pre),
        actual_nonfinite_output:count_bad(&actual),finite_max_error,reference,actual,
    };
    println!("PYRAMID_ACCUMULATOR_RANGE {{\"case\":\"{}\",\"frames\":{},\"profile_variance\":{},\"max_weight\":{},\"max_coefficient\":{},\"actual_nonfinite_num\":{},\"actual_nonfinite_den\":{},\"legacy_nonfinite_num\":{},\"actual_nonfinite_pre_hull\":{},\"actual_nonfinite_output\":{},\"finite_max_error_dn\":{}}}",
        label,frames.len(),physical_variance,max_weight,max_coefficient,obs.actual_nonfinite_num,
        obs.actual_nonfinite_den,obs.legacy_nonfinite_num,obs.actual_nonfinite_pre_hull,
        obs.actual_nonfinite_output,obs.finite_max_error);
    obs
}

fn assert_safe(o: &Observation) {
    assert_eq!(o.actual_nonfinite_den,0,"nonfinite denominator");
    assert_eq!(o.actual_nonfinite_num,0,"finite source/weight produced nonfinite numerator before hull");
    assert_eq!(o.actual_nonfinite_pre_hull,0,"nonfinite reconstruction hidden by hull");
    assert_eq!(o.actual_nonfinite_output,0);
    assert!(o.finite_max_error < 0.1,"output differs from f64 accumulation by {} DN",o.finite_max_error);
}

#[test]
fn independent_00_flat_and_midtone_controls() {
    for (label,a,b) in [("flat",checker(700.,700.),checker(900.,900.)),
        ("midtone",checker(800.,1400.),checker(850.,1350.))] {
        let o=observe(label,&[a,b],false);
        assert_eq!(o.legacy_nonfinite_num,0);
        assert_safe(&o);
        if label=="flat" {
            for (c,gain) in [0.75_f32,1.,1.,0.5].into_iter().enumerate() {
                assert!(o.reference[c].iter().all(|v|(*v-800.*gain).abs()<0.01));
                assert!(o.actual[c].iter().all(|v|(*v-800.*gain).abs()<0.01));
            }
        }
    }
}

#[test]
fn independent_10_high_dn_numerator_range_regression() {
    // These are legal finite DN and variance inputs, not a calibration claim.
    // Different frames leave a non-degenerate hull, so a bad mean can be visible.
    let o=observe("camera-range-low-variance-pair",&[checker(100.,15100.),checker(400.,14500.)],false);
    assert!(o.legacy_nonfinite_num>0,"fixture did not exercise the unsafe multiplication/sum");
    assert_safe(&o); // Expected RED before a numerically safe accumulator fix.
}

#[test]
fn independent_20_identical_frame_hull_is_not_safety() {
    let a=checker(100.,15100.);
    let o=observe("identical-high-dn-pair",&[a.clone(),a.clone()],false);
    assert!(o.legacy_nonfinite_num>0,"fixture failed to exercise the range problem");
    // A passing image identity by itself cannot establish finite internal state.
    assert_eq!(o.actual_nonfinite_output,0);
    assert!(o.actual.iter().zip(&a).all(|(out,src)|out.iter().zip(src).all(|(a,b)|a.to_bits()==b.to_bits())));
    assert_safe(&o); // Expected RED even when the final identical image looks right.
}

#[test]
fn independent_30_profile_noise_high_dn_pair() {
    // Distinct calibration-aware control. Do not require overflow to occur here.
    // Whether it occurs on the real stack is a separate upstream census.
    let o=observe("camera-range-profile-variance-pair",&[checker(100.,15100.),checker(400.,14500.)],true);
    assert_safe(&o);
}
