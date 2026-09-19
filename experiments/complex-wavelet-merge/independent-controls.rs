// Independent actual-u16 screen, reusing the frozen phase-packed fixtures.
use super::{compare_generated, coefficient_variance, forward_real, transform_one, inverse_one, Complex, Comparison};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,noise::{Levels,NoiseModel},profile};
use strehl_raw::{Frame,Region};

const W:usize=320;
const H:usize=288;
const GAIN:[f32;3]=[1.7,1.0,2.3];
const N:usize=5;
const TRIM:usize=24;
fn crop()->align_cmd::CropRect {align_cmd::CropRect{x:7,y:9,width:144,height:124}}
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
struct Scene {name:&'static str,frequency:f64,coloured:bool,defocus:u8,direction:(f64,f64)}
const SCENES:[Scene;6]=[
    Scene{name:"flat",frequency:0.0,coloured:false,defocus:0,direction:(0.8,0.6)},
    Scene{name:"horizontal-wave-vector",frequency:0.18,coloured:false,defocus:1,direction:(1.0,0.0)},
    Scene{name:"vertical-wave-vector",frequency:0.18,coloured:false,defocus:1,direction:(0.0,1.0)},
    Scene{name:"diagonal-wave-vector",frequency:0.18,coloured:false,defocus:1,direction:(0.8,0.6)},
    Scene{name:"colour-mid",frequency:0.18,coloured:true,defocus:0,direction:(0.8,0.6)},
    Scene{name:"colour-varying-focus",frequency:0.18,coloured:true,defocus:2,direction:(0.8,0.6)},
];
fn wave(scene:Scene,c:usize,x:f64,y:f64)->(f64,f64,f64) {
    let (dx,dy,phase,base,amplitude)=if scene.coloured {
        [(0.8,0.6,0.37,0.30,0.09),(1.0,0.0,1.13,0.32,0.07),(-0.6,0.8,2.07,0.28,0.08)][c]
    } else {(scene.direction.0,scene.direction.1,0.37,0.30,0.08)};
    (TAU*scene.frequency*(dx*x+dy*y)+phase,base,amplitude)
}
fn sigma(scene:Scene,x:f64,y:f64,frame:Option<usize>)->f64 {
    if scene.defocus==0 || frame.is_none() {return 0.0;}
    let depth=if scene.defocus==1 {2.0} else {(4.0*(x-30.0)/260.0+0.3*(y-H as f64/2.0)/H as f64).clamp(0.0,4.0)};
    1.3*(frame.unwrap() as f64-depth).abs()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,frame:Option<usize>)->f64 {
    if scene.frequency==0.0 {return 0.30;}
    let (phase,base,amplitude)=wave(scene,c,x,y);
    let blur=sigma(scene,x,y,frame);
    base+amplitude*(-0.5*TAU*TAU*blur*blur*scene.frequency*scene.frequency).exp()*phase.cos()
}
fn fixture(scene:Scene,k:usize,iso:f32,noise:&NoiseModel)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,
        levels:levels(),iso:Some(iso),wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],
        xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),
        path:std::env::current_dir().unwrap().join(format!("nonexistent-complex-wavelet-{k}.ARW"))};
    assert!(!f.path.exists());
    for y in 0..H {for x in 0..W {
        let wx=x as f64;let wy=y as f64;
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

fn magnitude(z:Complex)->f64 {f64::from(z.re).hypot(f64::from(z.im))}
fn error(a:Complex,b:Complex)->f64 {(f64::from(a.re)-f64::from(b.re)).hypot(f64::from(a.im)-f64::from(b.im))}
fn roundtrip(input:&[Complex],w:usize,h:usize)->f64 {
    let coefficients=transform_one(input,w,h).unwrap();
    assert_eq!(coefficients.len(),input.len());
    let back=inverse_one(&coefficients,w,h).unwrap();assert_eq!(back.len(),input.len());
    let scale=input.iter().copied().map(magnitude).fold(1.0f64,f64::max);
    let worst=input.iter().zip(&back).map(|(&a,&b)|{assert!(b.re.is_finite() && b.im.is_finite());error(a,b)}).fold(0.0f64,f64::max);
    assert!(worst<=2e-5*scale,"complex reconstruction error {worst}, scale {scale}");worst
}
fn commissioning()->Value {
    let (w,h)=(8usize,10usize);let n=w*h;
    let asymmetric=(0..n).map(|i|Complex{re:(0.31*i as f32).sin()+0.03*(i%7) as f32,
        im:0.7*(0.27*i as f32).cos()-0.02*(i%11) as f32}).collect::<Vec<_>>();
    let asymmetric_error=roundtrip(&asymmetric,w,h);
    let constant=vec![Complex{re:0.37,im:0.0};n];let constant_error=roundtrip(&constant,w,h);
    let dc=transform_one(&constant,w,h).unwrap();
    let detail_peak=(0..h).flat_map(|y|(0..w).filter_map(move |x|if x>=w/2 || y>=h/2 {Some(y*w+x)} else {None}))
        .map(|i|magnitude(dc[i])).fold(0.0f64,f64::max);
    assert!(detail_peak<=2e-5*0.37,"constant generated detail {detail_peak}");
    let mut impulse_errors=Vec::new();
    for (x,y) in [(0,0),(1,0),(0,1),(1,1),(w-1,h-1),(w-2,h-1),(3,4),(4,5)] {
        let mut a=vec![Complex{re:0.0,im:0.0};n];a[y*w+x]=Complex{re:1.0,im:-0.4};
        impulse_errors.push(json!({"xy":[x,y],"max_error":roundtrip(&a,w,h)}));
    }
    // A two-sample cyclic translation preserves decimation phase. Check the
    // complex coefficient, not only its magnitude, in all four quadrants.
    let coefficients=transform_one(&asymmetric,w,h).unwrap();
    let mut shift_error=0.0f64;
    for (dx,dy) in [(2usize,0usize),(0,2),(2,2)] {
        let shifted=(0..n).map(|i|asymmetric[((i/w+h-dy)%h)*w+(i%w+w-dx)%w]).collect::<Vec<_>>();
        let got=transform_one(&shifted,w,h).unwrap();
        for y in 0..h {for x in 0..w {
            let bx=x/(w/2)*(w/2);let by=y/(h/2)*(h/2);
            let sx=bx+(x-bx+w/2-dx/2)%(w/2);let sy=by+(y-by+h/2-dy/2)%(h/2);
            shift_error=shift_error.max(error(got[y*w+x],coefficients[sy*w+sx]));
        }}
    }
    assert!(shift_error<=2e-5,"cyclic shift changed complex phase/origin: {shift_error}");
    // Independently sum responses to every source basis vector. This uses
    // the transform as the measured operator and never uses variance-kernel
    // coefficients or addressing from coefficient_variance.
    let variances=(0..n).map(|i|0.6+((i*17+3)%31) as f32*0.07).collect::<Vec<_>>();
    let actual=coefficient_variance(&variances,w,h).unwrap();assert_eq!(actual.len(),n);
    let mut expected=vec![0.0f64;n];
    for i in 0..n {
        let mut basis=vec![0.0;n];basis[i]=1.0;let response=forward_real(&basis,w,h).unwrap();
        for j in 0..n {expected[j]+=f64::from(variances[i])*magnitude(response[j]).powi(2);}
    }
    let variance_error=actual.iter().zip(&expected).map(|(&a,&b)|{
        assert!(a.is_finite() && a>=0.0);let d=(f64::from(a)-b).abs();
        assert!(d<=2e-5*b.max(1.0),"variance propagation {a} != impulse oracle {b}");d
    }).fold(0.0f64,f64::max);
    for (rw,rh) in [(7usize,10usize),(8,9),(4,10)] {
        assert!(forward_real(&vec![0.0;rw*rh],rw,rh).is_err());
        assert!(coefficient_variance(&vec![1.0;rw*rh],rw,rh).is_err());
    }
    let mut bad=vec![0.0;n];bad[3]=f32::NAN;assert!(forward_real(&bad,w,h).is_err());
    let mut bad_v=variances.clone();bad_v[7]=-0.01;assert!(coefficient_variance(&bad_v,w,h).is_err());
    bad_v[7]=f32::INFINITY;assert!(coefficient_variance(&bad_v,w,h).is_err());
    json!({"size":[w,h],"asymmetric_complex_roundtrip_max":asymmetric_error,"constant_roundtrip_max":constant_error,
        "constant_detail_peak":detail_peak,"impulse_roundtrips":impulse_errors,
        "two_pixel_cyclic_shift_max":shift_error,"heteroscedastic_impulse_variance_max_error":variance_error,
        "invalid_shape_and_finite_refusals":true})
}

fn save(path:&Path,v:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),v).unwrap();}

fn direction_positions(w:usize,h:usize,d:usize)->Vec<usize> {
    let (bx,by)=[(1,0),(1,1),(0,1)][d];
    (0..h/2).flat_map(|y|(0..w/2).map(move |x|(by*h/2+y)*w+bx*w/2+x)).collect()
}
fn ideal_direction_evidence(scene:Scene)->Value {
    let (w,h)=(crop().width,crop().height);
    let guide=(0..w*h).map(|i|{
        let x=(2*(crop().x+i%w)) as f64;let y=(2*(crop().y+i/w)) as f64;
        (0.5*(radiance(scene,1,x+1.0,y,None)+radiance(scene,1,x,y+1.0,None))) as f32
    }).collect::<Vec<_>>();
    let coefficients=forward_real(&guide,w,h).unwrap();
    let energy:[f64;3]=std::array::from_fn(|d|direction_positions(w,h,d).iter()
        .map(|&i|magnitude(coefficients[i]).powi(2)).sum());
    let total=energy.iter().sum::<f64>();assert!(total>0.01);
    let share=energy.map(|e|e/total);
    if scene.direction==(1.0,0.0) {
        assert!(share[0]>0.99999 && share[1]+share[2]<0.00001,"horizontal wave was not single-direction: {share:?}");
    } else if scene.direction==(0.0,1.0) {
        assert!(share[2]>0.99999 && share[0]+share[1]<0.00001,"vertical wave was not single-direction: {share:?}");
    } else {
        assert!(share.iter().filter(|&&v|v>0.001).count()>=2,"diagonal fixture did not exercise multiple directions");
    }
    json!({"scene":scene.name,"orientation_order":["H","D","V"],"ideal_detail_energy":energy,"ideal_energy_fraction":share})
}
fn original_guide(frame:&Frame)->Vec<f32> {
    let c=crop();(0..c.height).flat_map(|y|(0..c.width).map(move |x|{
        let sx=frame.active.x+2*(c.x+x);let sy=frame.active.y+2*(c.y+y);
        let g1=f32::from(frame.data[sy*frame.stride+sx+1])-frame.levels.black;
        let g2=f32::from(frame.data[(sy+1)*frame.stride+sx])-frame.levels.black;
        0.5*(g1+g2)
    })).collect()
}
fn float_hash(v:&[f32])->String {
    let mut h=Sha256::new();for f in v {h.update(f.to_bits().to_le_bytes());}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}
fn verify(c:&Comparison,frames:&[Frame],hashes:&[String])->Vec<Value> {
    let pixels=crop().width*crop().height;
    assert_eq!((c.native_width,c.native_height),(2*crop().width,2*crop().height));
    assert!(c.known4_original_exact && c.identity_guide_original_exact);assert_eq!(c.frames.len(),N);
    for arm in [&c.baseline_planes4,&c.candidate_planes4,&c.control_planes4] {
        assert_eq!(arm.len(),4);assert!(arm.iter().all(|p|p.len()==pixels && p.iter().all(|v|v.is_finite())));
    }
    for (k,f) in frames.iter().enumerate() {
        assert_eq!(hash(&f.data),hashes[k]);assert_eq!(c.frames[k].source_sha256,hashes[k]);
        assert!(c.frames[k].known4_original_exact && c.frames[k].identity_guide_original_exact);
        assert_eq!(float_hash(&original_guide(f)),c.frames[k].guide_sha256,
            "actual guide differs from independently addressed original green sites");
    }
    c.candidate_weight_summary.iter().enumerate().map(|(d,s)|{
        assert_eq!(s.total_coefficients,pixels/4);
        assert!(s.min_weight.is_finite() && s.max_weight.is_finite() && s.min_weight>=0.0 && s.min_weight<=s.max_weight);
        assert!(s.multi_source_coefficients<=s.total_coefficients && s.positive_source_coefficients<=N*s.total_coefficients);
        assert!((0.0..=1.0).contains(&c.candidate_fallback_fraction[d]));
        json!({"orientation":(["H","D","V"][d]),"min_weight":s.min_weight,"max_weight":s.max_weight,
            "positive_source_coefficients":s.positive_source_coefficients,"multi_source_coefficients":s.multi_source_coefficients,
            "total_coefficients":s.total_coefficients,"fallback_fraction":c.candidate_fallback_fraction[d]})
    }).collect()
}
fn direct_mean_rgb(frames:&[Frame])->Vec<f32> {
    let c=crop();let mut planes=vec![vec![0.0f32;c.width*c.height];4];
    for f in frames {for y in 0..c.height {for x in 0..c.width {for (p,(dx,dy)) in [(0,0),(1,0),(0,1),(1,1)].into_iter().enumerate() {
        let sx=f.active.x+2*(c.x+x)+dx;let sy=f.active.y+2*(c.y+y)+dy;
        planes[p][y*c.width+x]+=f32::from(f.data[sy*f.stride+sx])-f.levels.black;
    }}}}
    for p in &mut planes {for v in p {*v/=frames.len() as f32;}}
    super::camera_rgb(&planes,c.width,c.height,levels(),frames[0].wb_coeffs).unwrap()
}

#[test]
fn independent_complex_00_transform_and_direction_controls() {
    let result=commissioning();
    let orientation=SCENES[1..4].iter().map(|&s|ideal_direction_evidence(s)).collect::<Vec<_>>();
    // The hard-vote arm is only a comparison; verify its advertised operation
    // without turning donor consensus into a candidate quality criterion.
    let (w,h)=(8usize,10usize);let mut indices=vec![0u16;w*h];
    for y in 0..h/2 {for x in 0..w/2 {indices[y*w+x]=100+(y*w+x) as u16;}}
    let before=indices.clone();let positions=(0..3).map(|d|direction_positions(w,h,d)).collect::<Vec<_>>();
    for (q,values) in [[1u16,2,2],[3,4,3],[5,5,6],[7,8,9],[10,10,10]].iter().enumerate() {
        for d in 0..3 {indices[positions[d][q]]=values[d];}
    }
    assert_eq!(super::direction_vote(&mut indices,w,h).unwrap(),3);
    for (q,expected) in [[2u16,2,2],[3,3,3],[5,5,5],[7,8,9],[10,10,10]].iter().enumerate() {
        for d in 0..3 {assert_eq!(indices[positions[d][q]],expected[d]);}
    }
    for y in 0..h/2 {for x in 0..w/2 {assert_eq!(indices[y*w+x],before[y*w+x]);}}
    eprintln!("COMPLEX_STRUCTURAL {}",json!({"transform":result,"ideal_directional_fields":orientation,"hard_control_vote_witness":true}));
}

#[test]
fn independent_complex_10_generated_quality_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_COMPLEX_WAVELET_OUT").expect("root-owned new output path required"));
    std::fs::create_dir(&out).unwrap();let mut cases=Vec::new();let mut decisions=Vec::new();
    let commission=commission_metric(2*crop().width,2*crop().height);
    for iso in [100.0f32,400.0] {
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());
        assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let mut benefit=false;let mut guards=true;
        // Flat MUST precede every structured quality measurement at each ISO.
        for scene in SCENES {
            let frames=(0..N).map(|k|fixture(scene,k,iso,&noise)).collect::<Vec<_>>();
            let hashes=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,crop(),&noise).unwrap();
            let participation=verify(&c,&frames,&hashes);
            let baseline=score(scene,&c.baseline_rgb,c.native_width,c.native_height);
            let candidate=score(scene,&c.candidate_rgb,c.native_width,c.native_height);
            let control=score(scene,&c.control_rgb,c.native_width,c.native_height);
            let mut mean_placebo=None;let mut crossing=None;
            let pass=if scene.frequency==0.0 {
                let averaged_fallback=c.candidate_fallback_fraction.iter().sum::<f64>()*(crop().width*crop().height/4) as f64;
                assert!(averaged_fallback>100.0,"no actual below-floor source averaging was exercised");
                let mean=score(scene,&direct_mean_rgb(&frames),c.native_width,c.native_height);
                let single=score(scene,&direct_mean_rgb(&frames[2..3]),c.native_width,c.native_height);
                mean_placebo=Some(json!({"direct_source_mean":score_json(&mean),"single_frame":score_json(&single),
                    "candidate_rgb_over_mean":candidate.rgb/mean.rgb,"unsafe_control_rgb_over_mean":control.rgb/mean.rgb}));
                benefit|=candidate.rgb<=0.95*baseline.rgb;
                candidate.rgb<=1.25*baseline.rgb && candidate.chroma<=1.25*baseline.chroma
            } else {
                let positive=c.candidate_weight_summary.iter().map(|s|s.positive_source_coefficients).sum::<usize>();
                let multi=c.candidate_weight_summary.iter().map(|s|s.multi_source_coefficients).sum::<usize>();
                assert!(positive>100 && multi>100,"structured detail weighting/multiple contributors were not exercised");
                if scene.defocus>0 {
                    assert!(!c.baseline_averaged_fraction.is_empty() && c.baseline_averaged_fraction[0]<1.0,
                        "focus fixture did not exercise actual matched baseline selection");
                    assert!(c.frames.windows(2).any(|f|f[0].guide_sha256!=f[1].guide_sha256));
                }
                if scene.defocus==1 {
                    assert!(baseline.inphase.iter().all(|&v|v>=0.5),"orientation fixture baseline cannot recover half the true signal");
                    let directions:Vec<usize>=if scene.direction==(1.0,0.0) {vec![0]} else if scene.direction==(0.0,1.0) {vec![2]} else {vec![0,1,2]};
                    assert!(directions.iter().any(|&d|c.candidate_weight_summary[d].positive_source_coefficients>100));
                }
                if scene.coloured {benefit|=candidate.rgb<=0.95*baseline.rgb;}
                if scene.defocus==2 {
                    let (b,n)=zero_crossing_error(scene,&c.baseline_rgb,c.native_width,c.native_height);
                    let (a,m)=zero_crossing_error(scene,&c.candidate_rgb,c.native_width,c.native_height);assert_eq!(n,m);
                    crossing=Some(json!({"pixels":n,"baseline_rb_rmse":b,"candidate_rb_rmse":a,"ratio":a/b,"reported_not_new_gate":true}));
                }
                preserves_components(&baseline,&candidate) && candidate.rgb<=1.10*baseline.rgb
            };guards&=pass;
            let evidence=c.frames.iter().map(|f|json!({"source_sha256":f.source_sha256,"guide_sha256":f.guide_sha256,
                "variance_sha256":f.variance_sha256,"coefficient_variance_sha256":f.coefficient_variance_sha256,
                "known4_original_exact":f.known4_original_exact,"identity_guide_original_exact":f.identity_guide_original_exact})).collect::<Vec<_>>();
            let record=json!({"iso":iso,"scene":scene.name,"baseline":score_json(&baseline),"candidate":score_json(&candidate),
                "unsafe_hard_control":score_json(&control),"rgb_ratio":candidate.rgb/baseline.rgb,"chroma_ratio":candidate.chroma/baseline.chroma,
                "guard_pass":pass,"flat_mean_placebo":mean_placebo,"truth_green_zero_crossings":crossing,
                "directional_participation":participation,"baseline_averaged_fraction":c.baseline_averaged_fraction,
                "control_votes_changed":c.control_votes_changed,"source_evidence":evidence});
            eprintln!("COMPLEX_CASE {}",record);cases.push(record);
        }
        decisions.push(json!({"iso":iso,"benefit":benefit,"guards_pass":guards,"admitted":benefit && guards}));
    }
    // The linear identity variance premise explicitly rejects clipping. This
    // is domain enforcement, not evidence of a clipping-aware reconstruction.
    let noise=profile::noise_model_for("ILCE-7CM2",Some(100.0),levels());
    let mut clipped=fixture(SCENES[0],0,100.0,&noise);
    clipped.data[clipped.active.y*clipped.stride+clipped.active.x]=levels().white as u16;
    assert!(compare_generated(&[clipped],crop(),&noise).is_err());
    let admitted=decisions.iter().all(|v|v["admitted"]==true);
    let result=json!({"status":"SCREEN_COMPLETE","next_composed_check_admitted":admitted,"photographic_replay_admitted":false,
        "iso_decisions":decisions,"metric_commission":commission,"cases":cases,"clipped_fixture_refused":true,
        "scope":"Identity u16 gather, one complex level versus actual one-level pyramid. No fractional, multilevel, optical or photographic claim."});
    save(&out.join("screen.json"),&result);eprintln!("COMPLEX_SCREEN {}",result);
}
