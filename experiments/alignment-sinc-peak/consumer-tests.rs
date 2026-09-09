// Independent fixed stimulus and decision; root executes after source review.
use crate::align::{AlignConfig, PlaneRef, SimilarityParams, TileMeasurement, TileProbe, TileStatus,
    ncc_tile, ncc_tile_warped};
use crate::align::sinc_peak_diagnostic::{Mode, Outcome, ncc_tile_with_mode, ncc_tile_warped_with_mode};
use serde_json::{json, Value};
use std::{fs::OpenOptions, io::Write, time::Instant};

const N: usize = 256;
const DELTAS: [(f32, f32); 6] = [
    (0.0625,-0.3125),(-0.0625,0.3125),(0.1875,0.4375),
    (-0.1875,-0.4375),(0.375,-0.125),(-0.375,0.125),
];
const BLOCKS: [&str; 4] = ["same-focus","unequal-blur","mixed-depth","noisy-same-focus"];

// Existing M78 xorshift64*/BoxMuller construction, not the peak interpolator.
struct Rng(u64);
impl Rng {
    fn unit(&mut self) -> f64 {
        let mut x=self.0;
        x ^= x>>12; x ^= x<<25; x ^= x>>27; self.0=x;
        ((x.wrapping_mul(0x2545_F491_4F6C_DD1D))>>11) as f64 / 9007199254740992.0
    }
    fn normal(&mut self) -> f32 {
        let u=self.unit().max(1e-12); let v=self.unit();
        ((-2.0*u.ln()).sqrt()*(std::f64::consts::TAU*v).cos()) as f32
    }
}
struct Field(Vec<(f32,f32,f32,f32)>);
impl Field {
    fn new(seed:u64) -> Self {
        let mut rng=Rng(seed); let mut components=Vec::new();
        let (lo,hi)=(1.0f32/40.0,1.0f32/2.6);
        for _ in 0..64 {
            let f=lo*(hi/lo).powf(rng.unit() as f32);
            let theta=std::f32::consts::TAU*rng.unit() as f32;
            let phase=std::f32::consts::TAU*rng.unit() as f32;
            components.push((f*theta.cos(),f*theta.sin(),phase,1.0/f));
        }
        let variance: f32=components.iter().map(|c|0.5*c.3*c.3).sum();
        for c in &mut components {c.3 *= 1.0/variance.sqrt();}
        Self(components)
    }
    fn blurred(&self,x:f32,y:f32,sigma:f32) -> f32 {
        let factor=-2.0*std::f32::consts::PI.powi(2)*sigma*sigma;
        self.0.iter().map(|&(u,v,p,a)| a*(factor*(u*u+v*v)).exp()
            *(std::f32::consts::TAU*(u*x+v*y)+p).cos()).sum()
    }
}
fn matrix(warped:bool) -> (f32,f32) {
    if warped {(1.008f32*0.004f32.cos(),1.008f32*0.004f32.sin())} else {(1.0,0.0)}
}
fn render(fields:&[Field;2],block:usize,case:usize,warped:bool,moving:bool) -> Vec<f32> {
    let (a,b)=matrix(warped); let determinant=a*a+b*b;
    let delta=DELTAS[case]; let mut result=vec![0.0;N*N];
    let seed=if moving {0x51D00000} else {0x51C00000};
    for y in 0..N {
        let mut rng=Rng((seed+case as u64)^((y as u64)<<32)^0x9E37_79B9_7F4A_7C15);
        for x in 0..N {
            // Independent literal inverse of T(p)=c+A(p-c)+A*delta.
            let (sx,sy)=if moving {
                let qx=x as f32-128.0; let qy=y as f32-128.0;
                (128.0+(a*qx+b*qy)/determinant-delta.0,
                 128.0+(-b*qx+a*qy)/determinant-delta.1)
            } else {(x as f32,y as f32)};
            let signal=if block==2 {
                let (s1,s2)=if moving {(1.4,0.35)} else {(0.35,1.4)};
                (fields[0].blurred(sx,sy,s1)+fields[1].blurred(sx,sy,s2))/2.0f32.sqrt()
            } else {fields[0].blurred(sx,sy,if block==1 && moving {1.4} else {0.35})};
            result[y*N+x]=3500.0+250.0*signal+if block==3 {16.0*rng.normal()} else {0.0};
        }
    }
    result
}
fn seed_warp() -> SimilarityParams {
    // Production parameter representation, independently scored in f64 below.
    let (a,b)=matrix(true);
    SimilarityParams {ax:0.0,ay:0.0,g:a as f64-1.0,rot:b as f64}
}
fn probe() -> TileProbe {TileProbe{tx:64,ty:64,size:128,predicted:(0.0,0.0),radius:6}}
fn call(reference:&[f32],moving:&[f32],warped:bool,mode:Mode) -> (TileMeasurement,Option<Outcome>) {
    let reference=PlaneRef::new(reference,N,N).unwrap();
    let moving=PlaneRef::new(moving,N,N).unwrap();
    let mut outcome=None; let cfg=AlignConfig::deep();
    let m=if warped {
        ncc_tile_warped_with_mode(reference,moving,probe(),seed_warp(),&cfg,mode,&mut outcome)
    } else {ncc_tile_with_mode(reference,moving,probe(),&cfg,mode,&mut outcome)};
    (m,outcome)
}
fn ordinary(reference:&[f32],moving:&[f32],warped:bool) -> TileMeasurement {
    let reference=PlaneRef::new(reference,N,N).unwrap();
    let moving=PlaneRef::new(moving,N,N).unwrap(); let cfg=AlignConfig::deep();
    if warped {ncc_tile_warped(reference,moving,probe(),seed_warp(),&cfg)}
    else {ncc_tile(reference,moving,probe(),&cfg)}
}
fn bits(m:TileMeasurement) -> [u32;4] {
    [m.dx.to_bits(),m.dy.to_bits(),m.peak.to_bits(),m.contrast.to_bits()]
}
fn exact(a:TileMeasurement,b:TileMeasurement) -> bool {a.status==b.status && bits(a)==bits(b)}
fn measurement(m:TileMeasurement,o:Option<Outcome>) -> Value {
    json!({"status":format!("{:?}",m.status),"dx":m.dx,"dy":m.dy,"peak":m.peak,
        "contrast":m.contrast,"bits":bits(m),"outcome":o.map(|o|json!({
            "offset":o.offset,"evaluations":o.evaluations,"reason":o.reason,"integer_peak":o.integer_peak}))})
}
fn error(m:TileMeasurement,warped:bool,case:usize) -> f64 {
    if m.status!=TileStatus::Ok || !m.dx.is_finite() || !m.dy.is_finite() {return f64::INFINITY;}
    let (x,y)=(m.dx as f64,m.dy as f64);
    // No renderer, fitted transform, or production inverse supplies scoring truth.
    let (x,y)=if warped {
        let (a,b)=(1.008*0.004f64.cos(),1.008*0.004f64.sin());
        ((a*x+b*y)/(a*a+b*b),(-b*x+a*y)/(a*a+b*b))
    } else {(x,y)};
    (x-DELTAS[case].0 as f64).hypot(y-DELTAS[case].1 as f64)
}
fn rms(v:&[f64]) -> f64 {(v.iter().map(|x|x*x).sum::<f64>()/v.len() as f64).sqrt()}
fn maximum(v:&[f64]) -> f64 {v.iter().copied().fold(0.0,f64::max)}
fn image_bits(v:&[f32]) -> Vec<u32> {v.iter().map(|x|x.to_bits()).collect()}

#[test]
#[ignore="root-owned fixed generated comparison; no original data"]
fn alignment_sinc_peak_fixed_consumer() {
    let path=std::env::var_os("STREHL_SINC_PEAK_CONSUMER_OUT").expect("fresh output path required");
    let mut output=OpenOptions::new().write(true).create_new(true).open(path).expect("fresh output file");
    let fields=[Field::new(0x78F1E1D0),Field::new(0x78F1E1D0^0x9e3779b97f4a7c15)];
    let mut rows=Vec::new(); let mut blocks=Vec::new(); let mut checks=Vec::new();
    let mut failures=Vec::<String>::new(); let mut inconclusive=Vec::<String>::new();
    // Independent literal values challenge the score gauge, not a fitted image.
    let (a,b)=(1.008*0.004f64.cos(),1.008*0.004f64.sin());
    let (dx,dy)=(0.1875f64,0.4375f64);
    let correct=((a*dx-b*dy) as f32,(b*dx+a*dy) as f32);
    let literal=|p:(f32,f32)| TileMeasurement {
        status:TileStatus::Ok,contrast:100.0,peak:1.0,dx:p.0,dy:p.1,
    };
    let correct_error=error(literal(correct),true,2);
    let sign_error=error(literal((-correct.0,-correct.1)),true,2);
    let swapped_error=error(literal((correct.1,correct.0)),true,2);
    let omitted_matrix_error=error(literal((dx as f32,dy as f32)),true,2);
    let gauge_pass=correct_error<=1e-6 && sign_error>0.1 && swapped_error>0.1 && omitted_matrix_error>0.003;
    checks.push(json!({"name":"independent-scoring-gauge","pass":gauge_pass,
        "correct_error":correct_error,"wrong_sign_error":sign_error,
        "swapped_axes_error":swapped_error,"omitted_matrix_error":omitted_matrix_error}));
    if !gauge_pass {failures.push("independent scoring gauge destroyer".into());}
    for warped in [false,true] {
        let route=if warped {"warped"} else {"plain"};
        for (block,&name) in BLOCKS.iter().enumerate() {
            let mut old_errors=Vec::new(); let mut new_errors=Vec::new();
            let (mut active,mut changed)=(0usize,0usize);
            for case in 0..6 {
                let reference=render(&fields,block,case,warped,false);
                let moving=render(&fields,block,case,warped,true);
                assert!(reference.iter().chain(moving.iter()).all(|v|v.is_finite()));
                let before=(image_bits(&reference),image_bits(&moving));
                let (old,old_o)=call(&reference,&moving,warped,Mode::Parabolic);
                let (new,new_o)=call(&reference,&moving,warped,Mode::Lanczos);
                let input_exact=before==(image_bits(&reference),image_bits(&moving));
                let metadata_exact=old.status==new.status && old.peak.to_bits()==new.peak.to_bits()
                    && old.contrast.to_bits()==new.contrast.to_bits()
                    && old_o.map(|o|o.integer_peak)==new_o.map(|o|o.integer_peak);
                let used=new_o.is_some_and(|o|o.offset.is_some() && o.reason=="accepted");
                let bounded=new_o.is_some_and(|o|o.evaluations<=80);
                let fallback_exact=used || exact(old,new);
                let changed_here=old.dx.to_bits()!=new.dx.to_bits() || old.dy.to_bits()!=new.dy.to_bits();
                active+=usize::from(used); changed+=usize::from(changed_here);
                let (oe,ne)=(error(old,warped,case),error(new,warped,case));
                old_errors.push(oe); new_errors.push(ne);
                if !(old.status==TileStatus::Ok && new.status==TileStatus::Ok && metadata_exact
                    && input_exact && bounded && fallback_exact) {
                    failures.push(format!("{route}/{name}/{case}: consumer integrity"));
                }
                if block==0 && case==0 {
                    let normal=ordinary(&reference,&moving,warped);
                    let pass=exact(normal,old);
                    checks.push(json!({"name":format!("{route}-ordinary-default"),"pass":pass,
                        "ordinary":measurement(normal,None),"explicit_old":measurement(old,old_o)}));
                    if !pass {failures.push(format!("{route}: ordinary default differs"));}
                }
                rows.push(json!({"route":route,"block":name,"case":case,"truth_reference":DELTAS[case],
                    "old":measurement(old,old_o),"candidate":measurement(new,new_o),
                    "old_error_reference_px":oe,"candidate_error_reference_px":ne,
                    "input_exact":input_exact,"metadata_exact":metadata_exact,"fallback_exact":fallback_exact,
                    "candidate_active":used,"offset_changed":changed_here}));
            }
            let (or,nr,om,nm)=(rms(&old_errors),rms(&new_errors),maximum(&old_errors),maximum(&new_errors));
            let finite=[or,nr,om,nm].iter().all(|x|x.is_finite());
            let resolved=block!=0 || or>=0.005;
            let accuracy=finite && if block==0 {nr<=0.80*or && nm<=0.075 && nm<=om+0.005}
                else {nr<=or+0.005 && nm<=om+0.02 && nm<=0.25};
            if !resolved {inconclusive.push(format!("{route}/{name}: old RMS below0.005"));}
            if active<4 || changed==0 {inconclusive.push(format!("{route}/{name}: insufficient candidate activity"));}
            if resolved && !accuracy {failures.push(format!("{route}/{name}: accuracy"));}
            blocks.push(json!({"route":route,"block":name,"rows":6,"old_rms":or,"candidate_rms":nr,
                "old_maximum":om,"candidate_maximum":nm,"active":active,"changed":changed,
                "baseline_resolved":resolved,"accuracy_pass":accuracy}));
        }
        // Actual flat/periodic inputs are rejection/fallback controls, not scored extra cases.
        for periodic in [false,true] {
            let levels=[1.0f32,0.0,-1.0,0.0];
            let image:Vec<f32>=(0..N*N).map(|p|if periodic {
                3500.0+250.0*(levels[p%N%4]+levels[p/N%4])
            } else {3500.0}).collect();
            // Identity seed is required for a truly periodic ambiguity in the warped path.
            let mut od=None; let mut nd=None; let p=PlaneRef::new(&image,N,N).unwrap();
            let cfg=AlignConfig::deep();
            let identity=SimilarityParams{ax:0.0,ay:0.0,g:0.0,rot:0.0};
            let old=if warped {ncc_tile_warped_with_mode(p,p,probe(),identity,&cfg,Mode::Parabolic,&mut od)}
                else {ncc_tile_with_mode(p,p,probe(),&cfg,Mode::Parabolic,&mut od)};
            let new=if warped {ncc_tile_warped_with_mode(p,p,probe(),identity,&cfg,Mode::Lanczos,&mut nd)}
                else {ncc_tile_with_mode(p,p,probe(),&cfg,Mode::Lanczos,&mut nd)};
            let pass=exact(old,new) && if periodic {nd.is_none_or(|o|o.offset.is_none())}
                else {new.status==TileStatus::LowContrast};
            checks.push(json!({"name":format!("{route}-{}",if periodic {"periodic-ambiguity"} else {"flat"}),
                "pass":pass,"old":measurement(old,od),"candidate":measurement(new,nd)}));
            if !pass {failures.push(format!("{route}: flat/periodic control"));}
        }
        // Orthogonal exact period-four carriers have live contrast but zero NCC.
        let levels=[1.0f32,0.0,-1.0,0.0];
        let reference:Vec<f32>=(0..N*N).map(|p|3500.0+250.0*levels[p%N%4]).collect();
        let moving:Vec<f32>=(0..N*N).map(|p|3500.0+250.0*levels[p/N%4]).collect();
        let r=PlaneRef::new(&reference,N,N).unwrap(); let m=PlaneRef::new(&moving,N,N).unwrap();
        let cfg=AlignConfig::deep(); let identity=SimilarityParams{ax:0.0,ay:0.0,g:0.0,rot:0.0};
        let (mut od,mut nd)=(None,None);
        let old=if warped {ncc_tile_warped_with_mode(r,m,probe(),identity,&cfg,Mode::Parabolic,&mut od)}
            else {ncc_tile_with_mode(r,m,probe(),&cfg,Mode::Parabolic,&mut od)};
        let new=if warped {ncc_tile_warped_with_mode(r,m,probe(),identity,&cfg,Mode::Lanczos,&mut nd)}
            else {ncc_tile_with_mode(r,m,probe(),&cfg,Mode::Lanczos,&mut nd)};
        let pass=exact(old,new) && new.status==TileStatus::LowPeak && new.contrast>cfg.min_contrast
            && old.peak.abs()<1e-6 && od.is_none() && nd.is_none();
        checks.push(json!({"name":format!("{route}-low-peak"),"pass":pass,
            "old":measurement(old,od),"candidate":measurement(new,nd)}));
        if !pass {failures.push(format!("{route}: LowPeak control"));}
    }
    let mut timing=Vec::new();
    for warped in [false,true] {
        let reference=render(&fields,0,2,warped,false); let moving=render(&fields,0,2,warped,true);
        for mode in [Mode::Parabolic,Mode::Lanczos] {std::hint::black_box(call(&reference,&moving,warped,mode));}
        let mut times=Vec::new();
        for mode in [Mode::Parabolic,Mode::Lanczos,Mode::Lanczos,Mode::Parabolic] {
            let start=Instant::now();
            for _ in 0..16 {std::hint::black_box(call(&reference,&moving,warped,mode));}
            times.push(start.elapsed().as_secs_f64());
        }
        let old=times[0].min(times[3]); let candidate=times[1].min(times[2]);
        let pass=old>0.0 && candidate/old<=1.10;
        timing.push(json!({"route":if warped {"warped"} else {"plain"},"order":["old","new","new","old"],
            "calls_per_block":16,"seconds":times,"minimum_old_seconds":old,"minimum_candidate_seconds":candidate,
            "ratio":candidate/old,"pass":pass,"scope":"local actual NCC calls; not full pair fit"}));
        if !pass {failures.push(format!("timing/{}: above1.10",if warped {"warped"} else {"plain"}));}
    }
    assert_eq!(rows.len(),48); assert_eq!(blocks.len(),8);
    let pass=failures.is_empty() && inconclusive.is_empty();
    let status=if !failures.is_empty() {"GENERATED_COMPARISON_REJECT"}
        else if !inconclusive.is_empty() {"INCONCLUSIVE"} else {"GENERATED_CONTROLS_PASS"};
    let record=json!({"schema":"alignment-sinc-peak-consumer-v1","status":status,
        "proceed_to_raw_ladder":pass,"scope":"consumer comparison only; independent literal controls and explicit root allocation also required",
        "rows":rows,"blocks":blocks,"checks":checks,"timing":timing,"failures":failures,
        "inconclusive":inconclusive,"source_population":{"width":N,"height":N,"components":64,
        "field_seeds":[0x78F1E1D0u64,0x78F1E1D0u64^0x9e3779b97f4a7c15u64],"deltas":DELTAS,
        "noise_sigma_dn":16.0,"reference_noise_seed_base":0x51C00000u64,"moving_noise_seed_base":0x51D00000u64}});
    serde_json::to_writer_pretty(&mut output,&record).expect("write record");
    output.write_all(b"\n").unwrap(); output.sync_all().unwrap();
    println!("ALIGNMENT_SINC_PEAK_CONSUMER status={status} rows=48 blocks=8 proceed={pass}");
}
