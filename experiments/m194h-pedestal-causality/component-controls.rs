// SOURCE ONLY until separately released. Included inside the gated core hook.
use super::*;
use std::panic::{catch_unwind, AssertUnwindSafe};
const W: usize = 80;
const H: usize = 64;
const BASE: f32 = 4096.0;
const TOL: f32 = 0.004;
fn config(arm: Arm) -> MergeConfig {
    MergeConfig { admission: arm.admission(), bands: 3, gate: 2.0, exponent: 2.0,
        sharpen_per_octave: 1.0, select: SelectMode::SoftPower, base: BaseBand::Mean,
        fallback: Fallback::Mean, mean_coarse: 0, significance_scale: 0.0,
        hull: Hull::InputRange, ..MergeConfig::default() }
}
fn field(amplitude: f32) -> Vec<f32> {
    (0..W*H).map(|j| BASE + if (j/W) % 2 == 0 { amplitude } else { -amplitude }).collect()
}
fn run(arm: Arm, observation: Option<Observation>, floor: f32, amplitude: f32) -> (Vec<Vec<f32>>, Option<Snapshot>) {
    assert!(arm != Arm::P0 || observation.is_some());
    let cfg = config(arm); let mut sum = BandMerge::new(W,H,4,cfg);
    let mut ws = FrameWorkspace::new(sum.sizes(),4);
    let session = observation.map(|o| Session::component(arm,o));
    let variance = vec![floor/2.0;W*H];
    // Match the consumer's canonical chunk semantics using two contiguous
    // chunks, actual absorb, then reset the same scratch accumulator.
    let mut scratch = BandMerge::new(W,H,4,cfg);
    for i in 0..5 {
        let f = field(if i == 3 { amplitude } else { 0.0 });
        ws.next_frame();
        scratch.add_frame_with_gain(&[&f,&f,&f,&f],&f,&variance,Some(&[1.0;3]),&mut ws);
        if i == 1 || i == 4 { sum.absorb(&scratch); scratch.reset_for_reuse(); }
    }
    let mut end = Workspace::new(sum.sizes()); let output = sum.finish(&mut end);
    let snapshot = session.map(Session::take);
    if let Some(s) = &snapshot { assert!(s.complete,"component full lifecycle"); }
    (output,snapshot)
}
fn max_error(output: &[Vec<f32>], amplitude: f32) -> f32 {
    let mut error = 0.0f32;
    for p in output { for y in 16..48 { for x in 16..64 {
        let expected = BASE + if y%2 == 0 {amplitude} else {-amplitude};
        error = error.max((p[y*W+x]-expected).abs());
    }}}
    error
}
fn same(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.len()==b.len() && a.iter().zip(b).all(|(x,y)| x.len()==y.len() && x.iter().zip(y).all(|(x,y)|x.to_bits()==y.to_bits()))
}
fn emit(id: &str) { println!("M194H_COMPONENT_PASS {id}"); }

#[test]
#[ignore = "M194h fixed component commission requires source review and release"]
fn fixed_threshold_null_and_observer_controls() {
    // Same actual mutation function as the production band hook. This is a
    // weight-path identity control, not an image quality/participation claim.
    let floor=10.0f32;let energy=[11.0f32,40.0,160.0];
    assert!(energy.iter().all(|&e|e>floor));
    let positive:Vec<f32>=energy.iter().map(|&e|pedestal_weight(e,floor,2.0)).collect();
    assert!(positive.windows(2).all(|w|w[0].to_bits()!=w[1].to_bits()));
    let mut observed=positive.clone();
    for (&e,w) in energy.iter().zip(&mut observed) {cutoff(Arm::P0,e,floor,w);}
    assert!(observed.iter().zip(&positive).all(|(a,b)|a.to_bits()==b.to_bits()));
    cutoff(Arm::P0,floor,floor,&mut observed[1]);
    assert_eq!(observed[1].to_bits(),0.0f32.to_bits());
    assert_ne!(observed[1].to_bits(),positive[1].to_bits());
    observed=positive.clone();
    for (&e,w) in energy.iter().zip(&mut observed) {cutoff(Arm::P0,e,floor,w);}
    assert!(observed.iter().zip(&positive).all(|(a,b)|a.to_bits()==b.to_bits()));
    emit("all-above-floor-weight-identity-exact-floor-destroyer-restoration");
    // Nine actual merges: three frozen floor cases times H/P/P0.
    for floor in [99.9375f32,100.0,100.0625] {
        let a = ((100.0f64-floor as f64).max(0.0))/floor as f64;
        let share = (1.0+a*a)/(5.0+a*a);
        for arm in [Arm::H,Arm::P,Arm::P0] {
            let (out,s) = run(arm,Some(Observation::On),floor,10.0);
            let expected = if arm==Arm::P { (10.0*share) as f32 }
                else if floor<100.0 {10.0} else {2.0};
            assert!(max_error(&out,expected)<=TOL,"registered actual threshold output");
            let mut s=s.unwrap(); assert!(partition_rows_valid(&s));
            // The actual classification bit, not a detached hash, is destroyed.
            let mut at=0; let mut found=None;
            while at<s.words.len() {
                let tag=s.words[at];let n=s.words[at+1] as usize;
                if tag==2 {found=Some(at+2+8);break;} at+=2+n;
            }
            let j=found.expect("actual partition row required");let old=s.words[j];
            s.words[j]^=1;assert!(!partition_rows_valid(&s),"classification destroyer lacked power");
            s.words[j]=old;assert!(partition_rows_valid(&s),"same-record restoration");
        }
    }
    emit("threshold-three-floors-and-actual-partition-fault");
    // Three noise-free flat merges: all four planes and every pixel stay flat.
    let mut nulls=Vec::new();
    for arm in [Arm::H,Arm::P,Arm::P0] {
        let (out,_) = run(arm,Some(Observation::On),99.9375,0.0);
        assert!(out.iter().flatten().all(|x|x.to_bits()==BASE.to_bits()));nulls.push(out);
    }
    assert!(same(&nulls[0],&nulls[1])&&same(&nulls[1],&nulls[2]));
    emit("noise-free-four-plane-flat-null");
    // Eleven merges: unarmed H/P baseline plus off/on/placebo for each arm.
    for arm in [Arm::H,Arm::P,Arm::P0] {
        let reference = if arm==Arm::P0 { None } else {Some(run(arm,None,99.9375,10.0).0)};
        let mut outputs=Vec::new();
        for mode in [Observation::Off,Observation::On,Observation::Placebo] {
            let (out,s)=run(arm,Some(mode),99.9375,10.0);let s=s.unwrap();
            assert_eq!(s.words.is_empty(),mode!=Observation::On);
            assert_eq!(s.observer_records>0,mode==Observation::On);
            assert_eq!(s.placebo_records>0,mode==Observation::Placebo);
            if let Some(reference)=&reference {assert!(same(reference,&out));}
            outputs.push(out);
        }
        assert!(same(&outputs[0],&outputs[1])&&same(&outputs[1],&outputs[2]));
    }
    emit("all-arms-off-on-placebo-and-unarmed-H-P-bit-identity");
    // Three strong-stripe merges. A plain all-frame mean is the fixed destroyer.
    for arm in [Arm::H,Arm::P,Arm::P0] {
        let (out,_) = run(arm,Some(Observation::On),99.9375,96.0);
        assert!(max_error(&out,96.0)<max_error(&out,19.2),"strong-detail control");
    }
    emit("strong-stripe-rejects-plain-mean");
    // No numerical call in these lifecycle faults; only the real RAII API.
    let failed=catch_unwind(AssertUnwindSafe(|| {
        let _session=Session::component(Arm::P,Observation::Off);
        let _nested=Session::component(Arm::H,Observation::Off);
    }));assert!(failed.is_err());
    let restored=Session::component(Arm::H,Observation::Off).take();
    assert!(!restored.complete&&restored.frames==0);
    emit("session-rejects-nesting-and-restores-after-panic");
    // An unsupported configuration must reach the same actual entry guard.
    let failed=catch_unwind(AssertUnwindSafe(|| {
        let mut cfg=config(Arm::H);cfg.base=BaseBand::WeightedFromCoarsest;
        let mut sum=BandMerge::new(W,H,4,cfg);let mut ws=FrameWorkspace::new(sum.sizes(),4);
        let _session=Session::component(Arm::H,Observation::Off);let f=field(0.0);
        sum.add_frame_with_gain(&[&f,&f,&f,&f],&f,&vec![50.0;W*H],Some(&[1.0;3]),&mut ws);
    }));assert!(failed.is_err());
    assert!(!Session::component(Arm::H,Observation::Off).take().complete);
    emit("unsupported-consumer-refused-before-frame-and-restored");
    println!("M194H_COMPONENT_COMPLETE 26-merges 130-frame-folds plus-one-rejected-entry");
}
