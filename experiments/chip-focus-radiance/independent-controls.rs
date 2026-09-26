// Independent controls of the actual streaming operator. Root owns execution.
use super::{Front, Output, Stream};
use serde_json::json;

fn front(n: usize) -> Front {
    Front { frames:n, xy_center:[64.,48.], xy_scale:[64.,48.],
        plane:[0.17,-0.11,0.5], schedule_knots:vec![0.,0.25,0.5,0.75,1.],
        schedule_values:vec![0.,0.16,0.41,0.70,1.], sigma:0.045 }
}
fn run(f: Front, w: usize, h: usize, mut source: impl FnMut(usize)->Vec<Vec<f32>>) -> Output {
    let mut stream=Stream::new(w,h,f.clone()).unwrap();
    for k in 0..f.frames { stream.add(k,&source(k)).unwrap(); }
    stream.finish().unwrap()
}
fn emit(name: &str, value: serde_json::Value) {
    println!("CHIP_FOCUS_RADIANCE_CONTROL {}",json!({"name":name,"result":value}));
    if let Some(dir)=std::env::var_os("STREHL_CHIP_FOCUS_RADIANCE_OUT") {
        let p=std::path::PathBuf::from(dir);std::fs::create_dir_all(&p).unwrap();
        let file=p.join(format!("{name}.json"));assert!(!file.exists());
        std::fs::write(file,serde_json::to_vec_pretty(&value).unwrap()).unwrap();
    }
}

#[test]
fn address_gauge_and_destroyers() {
    let mut f=front(5);f.xy_center=[10.5,20.5];f.xy_scale=[8.,20.];
    f.plane=[0.24,-0.30,0.45];
    // Quad (7,14) -> delivered-native (14.5,28.5), normalized (.5,.4).
    assert!((f.centre(7,14)-0.45).abs()<1e-7);
    assert!((f.centre(9,9)-0.72).abs()<1e-7);
    let expected_schedule=[0.,0.16,0.41,0.70,1.];
    for (k,t) in expected_schedule.iter().enumerate() {
        assert_eq!(f.schedule(k).unwrap().to_bits(),(*t as f32).to_bits());
    }
    let half_factor=[(7.5f64-10.5)/8.*0.24-(14.5-20.5)/20.*0.30+0.45,
        (9.5f64-10.5)/8.*0.24-(9.5-20.5)/20.*0.30+0.45];
    let half_factor_error=[(half_factor[0]-0.45).abs(),(half_factor[1]-0.72).abs()];
    let added_crop=(14.5f64+266.-10.5)/8.*0.24-(28.5+178.-20.5)/20.*0.30+0.45;
    // The first original point cancels this wrong-factor error. Retain that
    // degeneracy; require detection across the two already registered points.
    assert!(half_factor_error[0]<1e-12);
    assert!(half_factor_error.iter().any(|e|*e>0.01) && (added_crop-0.45).abs()>0.01);
    let q=(-0.5f64*((0.41f64-0.45)/0.045).powi(2)).exp();
    assert!((f64::from(f.weight(2,7,14).unwrap())-q).abs()<2e-6);
    // All four outputs use the same spatial weights, checked by affine source codes.
    let out=run(f.clone(),10,15,|k| (0..4).map(|c|vec![(8*k+c) as f32;150]).collect());
    assert_eq!(out.centre[14*10+7].to_bits(),f.centre(7,14).to_bits());
    for j in 0..150 { for c in 1..4 {
        assert!((out.planes[c][j]-out.planes[0][j]-c as f32).abs()<1e-4);
    }}
    emit("address",json!({"mechanical_pass":true,"factor_mutant_rejected":true,
        "factor_mutant_values":half_factor,"factor_mutant_absolute_errors":half_factor_error,
        "first_factor_point_degenerate":true,"factor_rejection_scope":"at least one of two original points",
        "crop_mutant_rejected":true,"channel_weights_shared":true}));
}

#[test]
fn constants_source_and_uniform_mean() {
    let values=[10000.,14000.,2500.,-32.5];let n=299usize;
    let out=run(front(n),17,13,|_| values.iter().map(|v|vec![*v;221]).collect());
    // Standard f32 accumulation/division bound, not a claimed quality tolerance.
    let u=f64::from(f32::EPSILON)/2.;let gamma=((2*n+4) as f64*u)/(1.-(2*n+4) as f64*u);
    let mut max_error=0.0f64;
    for c in 0..4 {for v in &out.planes[c] {
        let e=(f64::from(*v)-f64::from(values[c])).abs();max_error=max_error.max(e);
        assert!(e<=gamma*f64::from(values[c]).abs().max(1.));
    }}
    assert_eq!(out.source_count,299);assert!(out.mass.iter().all(|v|v.is_finite()&&*v>0.));
    let mut f=front(2);f.plane=[0.,0.,0.];f.sigma=0.01;
    assert_eq!(f.weight(0,0,0).unwrap(),1.);assert_eq!(f.weight(1,0,0).unwrap(),0.);
    let supplied=vec![vec![-8.,2.,301.25,12345.];4];
    let single=run(f,2,2,|k|if k==0 {supplied.clone()}else{vec![vec![17000.;4];4]});
    assert_eq!(single.planes,supplied);assert!(single.mass.iter().all(|v|*v==1.));
    let mut f=front(17);f.sigma=1e8;
    let uniform=run(f,7,5,|k|(0..4).map(|c|(0..35).map(|j|(4*k+c) as f32+j as f32*0.125).collect()).collect());
    assert!(uniform.mass.iter().all(|d|*d==17.));
    for c in 0..4 {for j in 0..35 {
        assert_eq!(uniform.planes[c][j],32.+c as f32+j as f32*0.125);
    }}
    emit("identities",json!({"mechanical_pass":true,"constant_sources":299,
        "constant_max_absolute_error_dn":max_error,"constant_relative_rounding_bound":gamma,
        "single_supported_source_exact":true,"uniform_mean_exact":true}));
}

fn hash(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn noise(k:usize,c:usize,j:usize)->f64 {
    let seed=(k as u32).wrapping_mul(0x9e3779b9)^(c as u32).wrapping_mul(0x85ebca6b)^(j as u32)^0x936a012b;
    let a=(f64::from(hash(seed))+0.5)/4294967296.;
    let b=(f64::from(hash(seed^0xa341316c))+0.5)/4294967296.;
    (-2.*a.ln()).sqrt()*(std::f64::consts::TAU*b).cos()
}
// Independent analytic schedule used by the fixture; no calls to Front::schedule.
fn time(k:usize,n:usize)->f64 {
    let v=[0.,0.16,0.41,0.70,1.];let u=k as f64/(n-1) as f64*4.;
    let i=(u.floor() as usize).min(3);v[i]+(u-i as f64)*(v[i+1]-v[i])
}
fn signal(c:usize,x:usize,y:usize,t:Option<f64>)->f64 {
    let xx=2.*x as f64+0.5;let yy=2.*y as f64+0.5;
    let z=0.5+0.17*(xx-64.)/64.-0.11*(yy-48.)/48.;
    let blur=0.65+t.map_or(0.,|v|30.*(v-z).abs());
    let freq=[0.055,0.07,0.07,0.045][c];let phase=[0.4,1.1,1.1,2.2][c];
    let base=[7000.,9000.,9000.,5000.][c];let amplitude=[1600.,1900.,1900.,1300.][c];
    base+amplitude*(-0.5*(std::f64::consts::TAU*freq*blur).powi(2)).exp()
        *(std::f64::consts::TAU*freq*(0.8*xx+0.6*yy)+phase).cos()
}
fn mse(a:&[Vec<f32>],b:&[Vec<f32>])->f64 {
    a.iter().zip(b).flat_map(|(x,y)|x.iter().zip(y)).map(|(x,y)|(f64::from(*x)-f64::from(*y)).powi(2)).sum::<f64>()/(a.len()*a[0].len()) as f64
}
#[test]
fn planar_focus_and_flat_noise() {
    const W:usize=64;const H:usize=48;const N:usize=33;
    let generate=|k:usize,flat:bool| (0..4).map(|c|(0..W*H).map(|j| {
        let value=if flat {8000.}else{signal(c,j%W,j/W,Some(time(k,N)))};
        (value+20.*noise(k,c,j)) as f32
    }).collect::<Vec<_>>()).collect::<Vec<_>>();
    // Flat is tested before the structured positive. No sensor calibration claim:
    // the known independent 20-DN draw simply exercises the averaging operator.
    let flat_truth=vec![vec![8000.;W*H];4];
    let flat=run(front(N),W,H,|k|generate(k,true));
    let flat_error=mse(&flat.planes,&flat_truth);
    let single_error=(0..N).map(|k|mse(&generate(k,true),&flat_truth)).sum::<f64>()/N as f64;
    let mut uniform_front=front(N);uniform_front.sigma=1e8;
    let flat_mean=run(uniform_front.clone(),W,H,|k|generate(k,true));
    let flat_mean_error=mse(&flat_mean.planes,&flat_truth);
    assert!(flat_error<0.75*single_error,"flat average did not reduce independent noise");
    assert!(flat_error>flat_mean_error,"narrow weighting noise cost unexpectedly unexercised");
    let truth=(0..4).map(|c|(0..W*H).map(|j|signal(c,j%W,j/W,None) as f32).collect()).collect::<Vec<_>>();
    let candidate=run(front(N),W,H,|k|generate(k,false));
    let mean=run(uniform_front,W,H,|k|generate(k,false));
    let mut bad=front(N);bad.plane[2]+=0.35;
    let wrong=run(bad,W,H,|k|generate(k,false));
    let e=mse(&candidate.planes,&truth);let m=mse(&mean.planes,&truth);let w=mse(&wrong.planes,&truth);
    let positive=e<=0.75*m;let wrong_rejected=w>0.75*m;
    let erased=(0..4).map(|c|vec![[7000.,9000.,9000.,5000.][c];W*H]).collect::<Vec<_>>();
    let erased_error=mse(&erased,&truth);let erased_rejected=erased_error>0.75*m;
    emit("planar",json!({"mechanical_pass":true,"positive_exercised":positive,
        "wrong_front_rejected":wrong_rejected,"erased_detail_rejected":erased_rejected,
        "flat_first":true,"flat_mse_dn2":flat_error,"single_source_mean_mse_dn2":single_error,
        "uniform_flat_mse_dn2":flat_mean_error,"candidate_mse_dn2":e,
        "uniform_mse_dn2":m,"wrong_front_mse_dn2":w,"erased_mse_dn2":erased_error,
        "actual_native_quality_qualified":false}));
    assert!(positive,"fixed front has no known-planar radiance benefit");
    assert!(wrong_rejected,"shifted smooth front passed the same positive bar");
    assert!(erased_rejected,"erased detail passed the same positive bar");
}

#[test]
fn refusal_and_order() {
    let p=vec![vec![1.;4];4];
    let mut stream=Stream::new(2,2,front(2)).unwrap();assert!(stream.add(1,&p).is_err());
    stream.add(0,&p).unwrap();assert!(stream.add(0,&p).is_err());assert!(stream.finish().is_err());
    let mut stream=Stream::new(2,2,front(2)).unwrap();let mut bad=p.clone();bad[2][1]=f32::NAN;
    assert!(stream.add(0,&bad).is_err());assert!(stream.add(0,&p[..3]).is_err());
    let mut f=front(2);f.plane=[0.,0.,100.];f.sigma=0.01;
    let mut stream=Stream::new(2,2,f).unwrap();stream.add(0,&p).unwrap();stream.add(1,&p).unwrap();
    assert!(stream.finish().is_err(),"zero-mass candidate must refuse, not fall back");
    let mut f=front(2);f.sigma=1e8;
    let mut stream=Stream::new(2,2,f).unwrap();let huge=vec![vec![f32::MAX;4];4];
    stream.add(0,&huge).unwrap();stream.add(1,&huge).unwrap();
    assert!(stream.finish().is_err(),"finite-input accumulator overflow must refuse");
    let mut f=front(2);f.sigma=f32::NAN;assert!(Stream::new(2,2,f).is_err());
    emit("refusal",json!({"mechanical_pass":true,"order_duplicate_missing_rejected":true,
        "nonfinite_or_wrong_planes_rejected":true,"zero_mass_whole_candidate_refused":true,
        "finite_input_sum_overflow_rejected":true,"invalid_model_rejected":true}));
}
