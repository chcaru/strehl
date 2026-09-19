// Independent actual-u16 screen, reusing the frozen phase-packed fixtures.
use super::{compare_generated, apply_acceptance, finish_projection, Comparison};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},
    plane::PlaneGeometry,profile,pyramid::MergeConfig};
use strehl_raw::{Frame,Region};

const W:usize=320;
const H:usize=288;
const GAIN:[f32;3]=[1.7,1.0,2.3];
const N:usize=5;
const TRIM:usize=24;
const PACK:[[usize;3];4]=[[0,4,5],[6,1,7],[8,2,9],[10,11,3]];
fn geometry()->PlaneGeometry {PlaneGeometry{width:W/2,height:H/2}}
fn crop()->align_cmd::CropRect {align_cmd::CropRect{x:7,y:9,width:145,height:125}}
fn levels()->Levels {Levels{black:512.0,white:15360.0}}
fn channel(x:usize,y:usize)->usize {match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane {match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn hash(values:&[u16])->String {
    let mut h=Sha256::new();for v in values {h.update(v.to_le_bytes());}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}
fn hash32(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64 {
    let seed=(x as u32)^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x31d59a67;
    let u=(hash32(seed) as f64+0.5)/4294967296.0;
    let v=(hash32(seed^0xa73126bd) as f64+0.5)/4294967296.0;
    (-2.0*u.ln()).sqrt()*(TAU*v).cos()
}
#[derive(Clone,Copy)]
struct Scene {name:&'static str,frequency:f64,coloured:bool,defocus:bool}
const SCENES:[Scene;7]=[
    Scene{name:"flat",frequency:0.0,coloured:false,defocus:false},
    Scene{name:"neutral-low",frequency:0.08,coloured:false,defocus:false},
    Scene{name:"colour-low",frequency:0.08,coloured:true,defocus:false},
    Scene{name:"neutral-mid",frequency:0.18,coloured:false,defocus:false},
    Scene{name:"colour-mid",frequency:0.18,coloured:true,defocus:false},
    Scene{name:"neutral-high-diagnostic",frequency:0.30,coloured:false,defocus:false},
    Scene{name:"colour-varying-focus",frequency:0.18,coloured:true,defocus:true},
];
fn wave(scene:Scene,c:usize,x:f64,y:f64)->(f64,f64,f64) {
    let (dx,dy,phase,base,amplitude)=if scene.coloured {
        [(0.8,0.6,0.37,0.30,0.09),(1.0,0.0,1.13,0.32,0.07),(-0.6,0.8,2.07,0.28,0.08)][c]
    } else {(0.8,0.6,0.37,0.30,0.08)};
    (TAU*scene.frequency*(dx*x+dy*y)+phase,base,amplitude)
}
fn sigma(scene:Scene,x:f64,y:f64,frame:Option<usize>)->f64 {
    if !scene.defocus || frame.is_none() {return 0.0;}
    let depth=(4.0*(x-30.0)/260.0+0.3*(y-H as f64/2.0)/H as f64).clamp(0.0,4.0);
    1.3*(frame.unwrap() as f64-depth).abs()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,frame:Option<usize>)->f64 {
    if scene.frequency==0.0 {return 0.30;}
    let (phase,base,amplitude)=wave(scene,c,x,y);
    let blur=sigma(scene,x,y,frame);
    base+amplitude*(-0.5*TAU*TAU*blur*blur*scene.frequency*scene.frequency).exp()*phase.cos()
}
fn transforms(fractional:bool)->Vec<Similarity> {
    let shifts=[(-0.46,0.32),(0.37,-0.21),(0.0,0.0),(0.23,0.44),(-0.18,-0.39)];
    (0..N).map(|k|if fractional {
        let j=k as f64-2.0;Similarity{a:Cx::new(1.0+0.0008*j,0.0004*j),b:Cx::new(shifts[k].0/2.0,shifts[k].1/2.0)}
    } else {Similarity::IDENTITY}).collect()
}
fn fixture(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,
        levels:levels(),iso:Some(iso),wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],
        xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),
        path:std::env::current_dir().unwrap().join(format!("nonexistent-phase-packed-{k}.ARW"))};
    assert!(!f.path.exists());
    let denominator=t.a.re*t.a.re+t.a.im*t.a.im;
    for y in 0..H {for x in 0..W {
        // Independent explicit inverse of the native pull, not a resampled image.
        let u=x as f64-W as f64/2.0-2.0*t.b.re;
        let v=y as f64-H as f64/2.0-2.0*t.b.im;
        let wx=W as f64/2.0+(t.a.re*u+t.a.im*v)/denominator;
        let wy=H as f64/2.0+(-t.a.im*u+t.a.re*v)/denominator;
        let c=channel(x,y);
        let signal=(radiance(scene,c,wx,wy,Some(k))*f64::from(levels().range())/f64::from(GAIN[c])) as f32;
        let observed=512.0+f64::from(signal)+gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal));
        assert!(observed>512.0 && observed<15360.0,"unintended clipped synthetic sample");
        f.data[(active.y+y)*stride+active.x+x]=observed.round() as u16;
    }}
    f
}
struct Score {rgb:f64,chroma:f64,inphase:[f64;3],quadrature:[f64;3]}
fn score(scene:Scene,rgb:&[f32],w:usize,h:usize)->Score {
    assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let mut error=0.0;let mut chroma=0.0;let mut count=0usize;
    // Per channel: sum(cos), sum(sin), sum(v), cos2, sin2, cos*sin, v*cos, v*sin.
    let mut sums=[[0.0f64;8];3];
    for y in TRIM..h-TRIM {for x in TRIM..w-TRIM {
        let gx=(2*crop().x+x) as f64;let gy=(2*crop().y+y) as f64;
        let mut e=[0.0;3];
        for c in 0..3 {
            let value=f64::from(rgb[(y*w+x)*3+c]);
            e[c]=value-radiance(scene,c,gx,gy,None);error+=e[c]*e[c];
            if scene.frequency>0.0 {
                let (phase,_,_)=wave(scene,c,gx,gy);let (s,co)=phase.sin_cos();
                for (o,v) in sums[c].iter_mut().zip([co,s,value,co*co,s*s,co*s,value*co,value*s]) {*o+=v;}
            }
        }
        chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);count+=1;
    }}
    let mut inphase=[0.0;3];let mut quadrature=[0.0;3];
    if scene.frequency>0.0 {for c in 0..3 {
        let [cs,ss,vs,cc,si,ci,vc,vi]=sums[c];let n=count as f64;
        let xx=cc-cs*cs/n;let yy=si-ss*ss/n;let xy=ci-cs*ss/n;
        let xv=vc-vs*cs/n;let yv=vi-vs*ss/n;let det=xx*yy-xy*xy;
        assert!(det>1.0);let amplitude=wave(scene,c,0.0,0.0).2;
        inphase[c]=(xv*yy-yv*xy)/det/amplitude;
        quadrature[c]=(yv*xx-xv*xy)/det/amplitude;
    }}
    Score{rgb:(error/(3*count) as f64).sqrt(),chroma:(chroma/(2*count) as f64).sqrt(),inphase,quadrature}
}
fn score_json(s:&Score)->Value {json!({"rgb_rmse":s.rgb,"chroma_rg_bg_rmse":s.chroma,"inphase_truth_amplitude":s.inphase,"quadrature_truth_amplitude":s.quadrature})}
fn preserves_components(baseline:&Score,candidate:&Score)->bool {
    (0..3).all(|c|baseline.inphase[c]<0.5 || candidate.inphase[c].min(1.0)>=0.9*baseline.inphase[c].min(1.0))
}
fn truth(scene:Scene,w:usize,h:usize)->Vec<f32> {
    (0..h).flat_map(|y|(0..w).flat_map(move |x|(0..3).map(move |c|
        radiance(scene,c,(2*crop().x+x) as f64,(2*crop().y+y) as f64,None) as f32))).collect()
}
fn commission_metric(w:usize,h:usize)->Value {
    let s=SCENES[4];let exact=truth(s,w,h);let good=score(s,&exact,w,h);
    assert!(good.rgb<1e-7 && good.chroma<1e-7);
    assert!(good.inphase.iter().all(|v|(v-1.0).abs()<1e-6));
    let mut grey=exact.clone();for p in grey.chunks_exact_mut(3) {let m=(p[0]+p[1]+p[2])/3.0;p.fill(m);}
    let bad=score(s,&grey,w,h);
    assert!(bad.chroma>0.02 && bad.inphase.iter().all(|v|*v<0.5),"colour destruction escaped the metric");
    let mut half=exact.clone();for p in half.chunks_exact_mut(3) {for c in 0..3 {let base=wave(s,c,0.0,0.0).1 as f32;p[c]=base+0.5*(p[c]-base);}}
    let attenuated=score(s,&half,w,h);
    assert!(attenuated.inphase.iter().all(|v|(*v-0.5).abs()<1e-6));
    assert!(!preserves_components(&good,&bad) && !preserves_components(&good,&attenuated));
    let mut excess=exact.clone();for p in excess.chunks_exact_mut(3) {for c in 0..3 {let base=wave(s,c,0.0,0.0).1 as f32;p[c]=base+1.4*(p[c]-base);}}
    let overcontrast=score(s,&excess,w,h);
    assert!(overcontrast.inphase.iter().all(|v|(*v-1.4).abs()<1e-6));
    assert!(preserves_components(&overcontrast,&good),"removing contrast above truth must not count as detail loss");
    json!({"exact_truth":score_json(&good),"grey_destroyer":score_json(&bad),"half_amplitude_destroyer":score_json(&attenuated),
        "overcontrast_baseline":score_json(&overcontrast),"truth_cap_avoids_false_rejection":true})
}

fn zero_crossing_error(scene:Scene,rgb:&[f32],w:usize,h:usize)->(f64,usize) {
    let mut sum=0.0;let mut count=0;
    for y in TRIM..h-TRIM {for x in TRIM..w-TRIM {
        let gx=(2*crop().x+x) as f64;let gy=(2*crop().y+y) as f64;
        if wave(scene,1,gx,gy).0.cos().abs()<=0.15 {
            for c in [0,2] {let d=f64::from(rgb[(y*w+x)*3+c])-radiance(scene,c,gx,gy,None);sum+=d*d;}
            count+=1;
        }
    }}
    assert!(count>1000,"truth-green zero-crossing subset was not exercised");
    ((sum/(2*count) as f64).sqrt(),count)
}
fn bits_equal(a:&[f32],b:&[f32])->bool {a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn verify(c:&Comparison,frames:&[Frame],original:&[String])->Vec<usize> {
    assert_eq!((c.native_width,c.native_height),(2*crop().width,2*crop().height));
    assert!(c.known4_equal);assert_eq!(c.frames.len(),N);assert_eq!(c.baseline_planes4.len(),4);
    assert_eq!(c.target_green.len(),crop().width*crop().height);
    let mut histogram=vec![0;N+1];
    for (i,&n) in c.acceptance_counts.iter().enumerate() {
        assert!(n<=N as u32);histogram[n as usize]+=1;
        let target=0.5*(c.baseline_planes4[1][i]+c.baseline_planes4[2][i]);
        assert_eq!(target.to_bits(),c.target_green[i].to_bits());
    }
    assert_eq!(histogram[0],c.fallback_quads);
    assert_eq!(c.acceptance_counts.iter().map(|n|*n as usize).sum::<usize>(),c.accepted_samples);
    assert!(c.accepted_samples>0 && c.accepted_samples<N*crop().width*crop().height,
        "actual fixture did not exercise both acceptance and rejection");
    assert!(histogram[2..].iter().sum::<usize>()>100,"no real multi-source averaging occurred");
    for (i,(frame,h)) in frames.iter().zip(original).enumerate() {
        assert_eq!(&hash(&frame.data),h);assert_eq!(&c.frames[i].source_sha256,h);
        assert_eq!(c.frames[i].source_index,i);assert!(c.frames[i].known4_equal);
    }
    histogram
}
fn verify_reversal(a:&Comparison,b:&Comparison)->f32 {
    assert_eq!(a.source_order,(0..N).collect::<Vec<_>>());assert_eq!(b.source_order,(0..N).rev().collect::<Vec<_>>());
    assert!(bits_equal(&a.baseline_rgb,&b.baseline_rgb) && bits_equal(&a.target_green,&b.target_green));
    assert_eq!(a.acceptance_counts,b.acceptance_counts);assert_eq!(a.fallback_quads,b.fallback_quads);
    for (x,y) in a.frames.iter().zip(&b.frames) {
        assert_eq!(x.source_index,y.source_index);assert_eq!(x.acceptance_mask_sha256,y.acceptance_mask_sha256);
        assert_eq!(x.accepted_quads,y.accepted_quads);assert_eq!(x.guide_sha256,y.guide_sha256);
        assert_eq!(x.variance_sha256,y.variance_sha256);assert_eq!(x.gathered12_sha256,y.gathered12_sha256);
    }
    let max=a.candidate_rgb.iter().zip(&b.candidate_rgb).map(|(a,b)|(a-b).abs()).fold(0.0f32,f32::max);
    assert!(max<=1e-6,"source replay order moved normalized RGB by {max}");max
}
fn save(path:&Path,v:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),v).unwrap();}

#[test]
fn independent_green_match_generated_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_GREEN_MATCH_OUT").expect("root-owned new output path required"));
    std::fs::create_dir(&out).unwrap();let ts=transforms(true);let mut cases=Vec::new();let mut decisions=Vec::new();
    let commission=commission_metric(2*crop().width,2*crop().height);
    for iso in [100.0f32,400.0] {
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());
        assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let mut benefit=false;let mut guards=true;
        // These original phase-packed scenes/phases are retained verbatim.
        for scene in [SCENES[0],SCENES[3],SCENES[4],SCENES[6]] {
            let frames=ts.iter().enumerate().map(|(k,t)|fixture(scene,k,*t,iso,&noise)).collect::<Vec<_>>();
            let hashes=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),false).unwrap();
            let counts=verify(&c,&frames,&hashes);
            let reverse=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),true).unwrap();
            verify(&reverse,&frames,&hashes);let reversed_max=verify_reversal(&c,&reverse);
            let baseline=score(scene,&c.baseline_rgb,c.native_width,c.native_height);
            let candidate=score(scene,&c.candidate_rgb,c.native_width,c.native_height);
            let mut crossing=None;
            let pass=if scene.frequency==0.0 {
                benefit|=candidate.rgb<=0.95*baseline.rgb;
                candidate.rgb<=1.25*baseline.rgb && candidate.chroma<=1.25*baseline.chroma
            } else {
                if scene.coloured {benefit|=candidate.rgb<=0.95*baseline.rgb;}
                let mut ok=preserves_components(&baseline,&candidate) && candidate.rgb<=1.10*baseline.rgb;
                if scene.defocus {
                    assert!(!c.baseline_averaged_fraction.is_empty() && c.baseline_averaged_fraction[0]<1.0,
                        "depth fixture did not exercise actual pyramid selection");
                    assert!(c.frames.windows(2).any(|v|v[0].guide_sha256!=v[1].guide_sha256));
                    let (b,n)=zero_crossing_error(scene,&c.baseline_rgb,c.native_width,c.native_height);
                    let (a,m)=zero_crossing_error(scene,&c.candidate_rgb,c.native_width,c.native_height);assert_eq!(n,m);
                    let crossing_pass=a<=1.10*b;ok&=crossing_pass;
                    crossing=Some(json!({"pixels":n,"baseline_rb_rmse":b,"candidate_rb_rmse":a,"ratio":a/b,"pass":crossing_pass}));
                }ok
            };guards&=pass;
            let evidence=c.frames.iter().map(|f|json!({"source_index":f.source_index,"source_sha256":f.source_sha256,
                "guide_sha256":f.guide_sha256,"variance_sha256":f.variance_sha256,"gathered12_sha256":f.gathered12_sha256,
                "acceptance_mask_sha256":f.acceptance_mask_sha256,"accepted_quads":f.accepted_quads})).collect::<Vec<_>>();
            let record=json!({"iso":iso,"scene":scene.name,"baseline":score_json(&baseline),"candidate":score_json(&candidate),
                "rgb_ratio":candidate.rgb/baseline.rgb,"chroma_ratio":candidate.chroma/baseline.chroma,"guard_pass":pass,
                "truth_green_zero_crossings":crossing,"acceptance_count_histogram":counts,"fallback_quads":c.fallback_quads,
                "accepted_samples":c.accepted_samples,"reverse_replay_max_rgb_difference":reversed_max,
                "baseline_averaged_fraction":c.baseline_averaged_fraction,"frames":evidence});
            eprintln!("GREEN_MATCH_CASE {}",record);cases.push(record);
        }
        decisions.push(json!({"iso":iso,"benefit":benefit,"guards_pass":guards,"admitted":benefit && guards}));
    }
    let admitted=decisions.iter().all(|v|v["admitted"]==true);
    let result=json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admitted,"iso_decisions":decisions,
        "metric_commission":commission,"cases":cases,"scope":"Generated-only test. Correlated green target and injected source variance do not calibrate residual probability or RGB covariance. No clipping/colour safety or optical claim."});
    save(&out.join("screen.json"),&result);eprintln!("GREEN_MATCH_DECISION {}",json!({"photographic_replay_admitted":admitted}));
}

#[test]
fn independent_green_match_acceptance_tuple_fallback_and_ambiguities() {
    let n=6;let a=(0..12).map(|s|(0..n).map(|q|(100+20*s+q) as f32).collect::<Vec<_>>()).collect::<Vec<_>>();
    let b=a.iter().map(|p|p.iter().map(|v|v+40.0).collect()).collect::<Vec<Vec<f32>>>();
    let mut sums=vec![vec![0.0;n];12];let mut counts=vec![0;n];let target=vec![10.0;n];
    let first=apply_acceptance(&a,&[14.0,14.0001,6.0,5.9999,20.0,10.0],&vec![4.0;n],&target,&mut sums,&mut counts).unwrap();
    assert_eq!(first.accepted_quads,3);assert_eq!(counts,vec![1,0,1,0,0,1]);
    apply_acceptance(&b,&[10.0,10.0,30.0,30.0,30.0,30.0],&vec![0.0;n],&target,&mut sums,&mut counts).unwrap();
    assert_eq!(counts,vec![2,1,1,0,0,1]);
    let baseline=(0..12*n).map(|i|if i%11==0 {-0.0}else{0.2+i as f32*0.001}).collect::<Vec<_>>();
    let rgb=finish_projection(&sums,&counts,&baseline,3,2,Levels{black:0.0,white:1000.0},[1.0,1.0,1.0,f32::NAN]).unwrap();
    let mut fallback_checked=0;let mut tuple_checked=0;
    for y in 0..2 {for x in 0..3 {let q=y*3+x;for dy in 0..2 {for dx in 0..2 {for c in 0..3 {
        let index=((2*y+dy)*6+2*x+dx)*3+c;let slot=PACK[2*dy+dx][c];
        if counts[q]==0 {assert_eq!(rgb[index].to_bits(),baseline[index].to_bits());fallback_checked+=1;}
        else {let expected=match q {0=>(a[slot][q]+b[slot][q])/2.0,1=>b[slot][q],_=>a[slot][q]}/1000.0;
            assert_eq!(rgb[index].to_bits(),expected.to_bits());tuple_checked+=1;}
    }}}}}
    assert_eq!((fallback_checked,tuple_checked),(24,48));
    // Information-limit witnesses, through the same actual acceptance loop.
    // Every site's G is100, while R/B swap. Both are unavoidably accepted.
    let mut one=vec![vec![0.0;1];12];let mut two=one.clone();
    for slots in PACK {one[slots[0]][0]=800.0;one[slots[1]][0]=100.0;one[slots[2]][0]=200.0;
        two[slots[0]][0]=200.0;two[slots[1]][0]=100.0;two[slots[2]][0]=800.0;}
    let mut mix=vec![vec![0.0;1];12];let mut number=vec![0];
    apply_acceptance(&one,&[100.0],&[1.0],&[100.0],&mut mix,&mut number).unwrap();
    apply_acceptance(&two,&[100.0],&[1.0],&[100.0],&mut mix,&mut number).unwrap();assert_eq!(number,vec![2]);
    let amb=finish_projection(&mix,&number,&[0.0;12],1,1,Levels{black:0.0,white:1000.0},[1.0,1.0,1.0,f32::NAN]).unwrap();
    for pixel in amb.chunks_exact(3) {assert_eq!(pixel,&[0.5,0.1,0.5]);}
    for slots in PACK {one[slots[0]][0]=1000.0;}
    let mut clipped=vec![vec![0.0;1];12];let mut clipped_count=vec![0];
    apply_acceptance(&one,&[100.0],&[1.0],&[100.0],&mut clipped,&mut clipped_count).unwrap();
    assert_eq!(clipped_count,vec![1]);
    let clipped_rgb=finish_projection(&clipped,&clipped_count,&[0.0;12],1,1,Levels{black:0.0,white:1000.0},[1.0,1.0,1.0,f32::NAN]).unwrap();
    for pixel in clipped_rgb.chunks_exact(3) {assert_eq!(pixel[0],1.0);}
    assert!(apply_acceptance(&one,&[f32::NAN],&[1.0],&[100.0],&mut vec![vec![0.0;1];12],&mut [0]).is_err());
    eprintln!("GREEN_MATCH_OPERATOR inclusive_boundary=true, zero_variance_equal=true, fallback_samples_exact={fallback_checked}, tuple_samples_exact={tuple_checked}, equal_green_incompatible_colour_averaged=true, clipped_red_matching_green_admitted=true");
}
