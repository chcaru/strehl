// Independent actual-u16 screen, reusing the frozen phase-packed fixtures.
use super::{compare_generated, coefficient_variance, forward_real, transform_two, inverse_two, Complex, Comparison};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,noise::{Levels,NoiseModel,PlaneNoise,Provenance},profile};
use strehl_raw::{Frame,Region};

const W:usize=320;
const H:usize=288;
const GAIN:[f32;3]=[1.7,1.0,2.3];
const N:usize=5;
const TRIM:usize=56;
fn crop(phase:usize)->align_cmd::CropRect {align_cmd::CropRect{x:7+phase,y:9+phase,width:144,height:124}}
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
struct Scene {name:&'static str,frequency:f64,coloured:bool,defocus:u8,direction:(f64,f64),weak_red_amplitude:Option<f64>}
const SCENES:[Scene;8]=[
    Scene{name:"flat",frequency:0.0,coloured:false,defocus:0,direction:(0.8,0.6),weak_red_amplitude:None},
    Scene{name:"horizontal-wave-vector",frequency:0.18,coloured:false,defocus:1,direction:(1.0,0.0),weak_red_amplitude:None},
    Scene{name:"vertical-wave-vector",frequency:0.18,coloured:false,defocus:1,direction:(0.0,1.0),weak_red_amplitude:None},
    Scene{name:"diagonal-wave-vector",frequency:0.18,coloured:false,defocus:1,direction:(0.8,0.6),weak_red_amplitude:None},
    Scene{name:"colour-mid",frequency:0.18,coloured:true,defocus:0,direction:(0.8,0.6),weak_red_amplitude:None},
    Scene{name:"colour-varying-focus",frequency:0.18,coloured:true,defocus:2,direction:(0.8,0.6),weak_red_amplitude:None},
    Scene{name:"coarse-neutral",frequency:0.06,coloured:false,defocus:3,direction:(0.8,0.6),weak_red_amplitude:None},
    Scene{name:"weak-red-warm-wb",frequency:0.18,coloured:true,defocus:1,direction:(1.0,0.0),weak_red_amplitude:Some(0.0)},
];
fn gains(scene:Scene)->[f32;3] {if scene.weak_red_amplitude.is_some() {[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)]} else {GAIN}}
fn wave(scene:Scene,c:usize,x:f64,y:f64)->(f64,f64,f64) {
    let (dx,dy,phase,base,amplitude)=if let Some(a)=scene.weak_red_amplitude {
        (1.0,0.0,0.37,0.30,if c==0 {a} else {0.0})
    } else if scene.coloured {
        [(0.8,0.6,0.37,0.30,0.09),(1.0,0.0,1.13,0.32,0.07),(-0.6,0.8,2.07,0.28,0.08)][c]
    } else {(scene.direction.0,scene.direction.1,0.37,0.30,0.08)};
    (TAU*scene.frequency*(dx*x+dy*y)+phase,base,amplitude)
}
fn sigma(scene:Scene,x:f64,y:f64,frame:Option<usize>)->f64 {
    if scene.defocus==0 || frame.is_none() {return 0.0;}
    let depth=if scene.defocus==1 || scene.defocus==3 {2.0} else {(4.0*(x-30.0)/260.0+0.3*(y-H as f64/2.0)/H as f64).clamp(0.0,4.0)};
    (if scene.defocus==3 {3.5} else {1.3})*(frame.unwrap() as f64-depth).abs()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,frame:Option<usize>)->f64 {
    if scene.frequency==0.0 {return 0.30;}
    let (phase,base,amplitude)=wave(scene,c,x,y);
    let blur=sigma(scene,x,y,frame);
    base+amplitude*(-0.5*TAU*TAU*blur*blur*scene.frequency*scene.frequency).exp()*phase.cos()
}
fn fixture(scene:Scene,k:usize,iso:f32,noise:&NoiseModel)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;let gain=gains(scene);
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,
        levels:levels(),iso:Some(iso),wb_coeffs:[gain[0],gain[1],gain[2],f32::NAN],
        xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),
        path:std::env::current_dir().unwrap().join(format!("nonexistent-all-cfa-wavelet-{k}.ARW"))};
    assert!(!f.path.exists());
    for y in 0..H {for x in 0..W {
        let wx=x as f64;let wy=y as f64;
        let c=channel(x,y);
        let signal=(radiance(scene,c,wx,wy,Some(k))*f64::from(levels().range())/f64::from(gain[c])) as f32;
        let observed=512.0+f64::from(signal)+gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal));
        assert!(observed>512.0 && observed<15360.0,"unintended clipped synthetic sample");
        f.data[(active.y+y)*stride+active.x+x]=observed.round() as u16;
    }}
    f
}
struct Score {rgb:f64,chroma:f64,inphase:[f64;3],quadrature:[f64;3]}
fn score(scene:Scene,rgb:&[f32],w:usize,h:usize,region:align_cmd::CropRect)->Score {
    assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let mut error=0.0;let mut chroma=0.0;let mut count=0usize;
    // Per channel: sum(cos), sum(sin), sum(v), cos2, sin2, cos*sin, v*cos, v*sin.
    let mut sums=[[0.0f64;8];3];
    for y in TRIM..h-TRIM {for x in TRIM..w-TRIM {
        let gx=(2*region.x+x) as f64;let gy=(2*region.y+y) as f64;
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
        if wave(scene,c,0.0,0.0).2==0.0 {continue;}
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
fn truth(scene:Scene,w:usize,h:usize,region:align_cmd::CropRect)->Vec<f32> {
    (0..h).flat_map(|y|(0..w).flat_map(move |x|(0..3).map(move |c|
        radiance(scene,c,(2*region.x+x) as f64,(2*region.y+y) as f64,None) as f32))).collect()
}
fn commission_metric(w:usize,h:usize,region:align_cmd::CropRect)->Value {
    let s=SCENES[4];let exact=truth(s,w,h,region);let good=score(s,&exact,w,h,region);
    assert!(good.rgb<1e-7 && good.chroma<1e-7);
    assert!(good.inphase.iter().all(|v|(v-1.0).abs()<1e-6));
    let mut grey=exact.clone();for p in grey.chunks_exact_mut(3) {let m=(p[0]+p[1]+p[2])/3.0;p.fill(m);}
    let bad=score(s,&grey,w,h,region);
    assert!(bad.chroma>0.02 && bad.inphase.iter().all(|v|*v<0.5),"colour destruction escaped the metric");
    let mut half=exact.clone();for p in half.chunks_exact_mut(3) {for c in 0..3 {let base=wave(s,c,0.0,0.0).1 as f32;p[c]=base+0.5*(p[c]-base);}}
    let attenuated=score(s,&half,w,h,region);
    assert!(attenuated.inphase.iter().all(|v|(*v-0.5).abs()<1e-6));
    assert!(!preserves_components(&good,&bad) && !preserves_components(&good,&attenuated));
    let mut excess=exact.clone();for p in excess.chunks_exact_mut(3) {for c in 0..3 {let base=wave(s,c,0.0,0.0).1 as f32;p[c]=base+1.4*(p[c]-base);}}
    let overcontrast=score(s,&excess,w,h,region);
    assert!(overcontrast.inphase.iter().all(|v|(*v-1.4).abs()<1e-6));
    assert!(preserves_components(&overcontrast,&good),"removing contrast above truth must not count as detail loss");
    json!({"exact_truth":score_json(&good),"grey_destroyer":score_json(&bad),"half_amplitude_destroyer":score_json(&attenuated),
        "overcontrast_baseline":score_json(&overcontrast),"truth_cap_avoids_false_rejection":true})
}

fn zero_crossing_error(scene:Scene,rgb:&[f32],w:usize,h:usize,region:align_cmd::CropRect)->(f64,usize) {
    let mut sum=0.0;let mut count=0;
    for y in TRIM..h-TRIM {for x in TRIM..w-TRIM {
        let gx=(2*region.x+x) as f64;let gy=(2*region.y+y) as f64;
        if wave(scene,1,gx,gy).0.cos().abs()<=0.15 {
            for c in [0,2] {let d=f64::from(rgb[(y*w+x)*3+c])-radiance(scene,c,gx,gy,None);sum+=d*d;}
            count+=1;
        }
    }}
    assert!(count>500,"truth-green zero-crossing subset was not exercised");
    ((sum/(2*count) as f64).sqrt(),count)
}

fn magnitude(z:Complex)->f64 {f64::from(z.re).hypot(f64::from(z.im))}
fn error(a:Complex,b:Complex)->f64 {(f64::from(a.re)-f64::from(b.re)).hypot(f64::from(a.im)-f64::from(b.im))}
fn roundtrip(input:&[Complex],w:usize,h:usize)->f64 {
    let a=transform_two(input,w,h).unwrap();let b=inverse_two(&a,w,h).unwrap();
    assert_eq!(b.len(),input.len());
    let scale=input.iter().copied().map(magnitude).fold(1.0f64,f64::max);
    let worst=input.iter().zip(&b).map(|(&a,&b)|{assert!(b.re.is_finite() && b.im.is_finite());error(a,b)}).fold(0.0f64,f64::max);
    assert!(worst<=2e-5*scale,"two-level reconstruction error {worst}");worst
}
fn direction_positions(w:usize,h:usize,level:usize,d:usize)->Vec<usize> {
    let (lw,lh)=(w>>level,h>>level);let (bx,by)=[(1,0),(1,1),(0,1)][d];
    (0..lh/2).flat_map(|y|(0..lw/2).map(move |x|(by*lh/2+y)*w+bx*lw/2+x)).collect()
}
fn float_hash(v:&[f32])->String {
    let mut h=Sha256::new();for f in v {h.update(f.to_bits().to_le_bytes());}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}
fn save(path:&Path,v:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),v).unwrap();}
fn naive_recursive_variance(v:&[f32],w:usize,h:usize)->Vec<f32> {
    let mut first=crate::merge_cmd::complex_wavelet_merge::coefficient_variance(v,w,h).unwrap();
    let mut ll=Vec::new();for y in 0..h/2 {ll.extend_from_slice(&first[y*w..y*w+w/2]);}
    let wrong=crate::merge_cmd::complex_wavelet_merge::coefficient_variance(&ll,w/2,h/2).unwrap();
    for y in 0..h/2 {first[y*w..y*w+w/2].copy_from_slice(&wrong[y*(w/2)..(y+1)*(w/2)]);}
    first
}
fn commissioning()->Value {
    let (w,h)=(12usize,16usize);let n=w*h;
    let asymmetric=(0..n).map(|i|Complex{re:(0.31*i as f32).sin()+0.03*(i%7) as f32,
        im:0.7*(0.27*i as f32).cos()-0.02*(i%11) as f32}).collect::<Vec<_>>();
    let initial_error=roundtrip(&asymmetric,w,h);
    let shifted=(0..n).map(|i|asymmetric[((i/w+h-1)%h)*w+(i%w+w-1)%w]).collect::<Vec<_>>();
    let shifted_error=roundtrip(&shifted,w,h);
    let constant=vec![Complex{re:0.37,im:0.0};n];let constant_error=roundtrip(&constant,w,h);
    let dc=transform_two(&constant,w,h).unwrap();
    let mut detail_peak=0.0f64;
    for level in 0..2 {for d in 0..3 {for i in direction_positions(w,h,level,d) {detail_peak=detail_peak.max(magnitude(dc[i]));}}}
    assert!(detail_peak<2e-5*0.37);
    let mut impulse_peak=0.0f64;
    for y in 0..4 {for x in 0..4 {
        let mut a=vec![Complex{re:0.0,im:0.0};n];a[y*w+x]=Complex{re:1.0,im:-0.4};
        impulse_peak=impulse_peak.max(roundtrip(&a,w,h));
        a[y*w+x]=Complex{re:0.0,im:0.0};a[(h-1-y)*w+w-1-x]=Complex{re:1.0,im:-0.4};
        impulse_peak=impulse_peak.max(roundtrip(&a,w,h));
    }}
    // The oracle observes every full-transform impulse, including all
    // repeated and wrapped paths. It never reads composed kernel weights.
    let responses=(0..n).map(|i|{
        let mut a=vec![0.0;n];a[i]=1.0;forward_real(&a,w,h).unwrap()
    }).collect::<Vec<_>>();
    let original=(0..n).map(|i|0.6+((i*17+3)%31) as f32*0.07).collect::<Vec<_>>();
    let mut variance_cases=Vec::new();
    for phase in 0..2 {
        let variances=(0..n).map(|i|original[((i/w+h-phase)%h)*w+(i%w+w-phase)%w]).collect::<Vec<_>>();
        let actual=coefficient_variance(&variances,w,h).unwrap();
        let wrong=naive_recursive_variance(&variances,w,h);
        let expected=(0..n).map(|j|(0..n).map(|i|f64::from(variances[i])*magnitude(responses[i][j]).powi(2)).sum::<f64>()).collect::<Vec<_>>();
        let mut max_error=0.0f64;let mut destroyer_error=0.0f64;
        for i in 0..n {
            assert!(actual[i].is_finite() && actual[i]>=0.0);
            let e=(f64::from(actual[i])-expected[i]).abs();max_error=max_error.max(e);
            assert!(e<=2e-5*expected[i].max(1.0),"composed variance {i}: {} != {}",actual[i],expected[i]);
            if i%w<w/2 && i/w<h/2 {destroyer_error=destroyer_error.max((f64::from(wrong[i])-expected[i]).abs());}
        }
        assert!(destroyer_error>1e-4,"recursive scalar-variance destroyer was not distinguishable");
        variance_cases.push(json!({"one_quad_phase":phase,"impulse_oracle_max_error":max_error,"naive_recursive_max_error":destroyer_error}));
    }
    for (rw,rh) in [(10usize,16usize),(12,14),(8,16)] {
        assert!(forward_real(&vec![0.0;rw*rh],rw,rh).is_err());
        assert!(coefficient_variance(&vec![1.0;rw*rh],rw,rh).is_err());
    }
    let mut bad=original.clone();bad[3]=f32::NAN;assert!(forward_real(&bad,w,h).is_err());
    bad[3]=-1.0;assert!(coefficient_variance(&bad,w,h).is_err());
    json!({"size":[w,h],"complex_roundtrip_max":initial_error,"shifted_roundtrip_max":shifted_error,
        "constant_roundtrip_max":constant_error,"constant_detail_peak":detail_peak,"all_four_residue_impulse_max":impulse_peak,
        "variance_cases":variance_cases,"periodic_effective_support_exceeds_width":true,"invalid_inputs_refused":true})
}
fn ideal_direction_evidence(scene:Scene,region:align_cmd::CropRect)->Value {
    let (w,h)=(region.width,region.height);
    let signal=(0..w*h).map(|i|radiance(scene,1,(2*(region.x+i%w)) as f64,(2*(region.y+i/w)) as f64,None) as f32).collect::<Vec<_>>();
    let coefficients=forward_real(&signal,w,h).unwrap();
    let energy:[[f64;3];2]=std::array::from_fn(|level|std::array::from_fn(|d|direction_positions(w,h,level,d).iter()
        .map(|&i|magnitude(coefficients[i]).powi(2)).sum()));
    for e in &energy {
        let total=e.iter().sum::<f64>();assert!(total>0.0001);
        if scene.direction==(1.0,0.0) {assert!(e[0]/total>0.99999);}
        else if scene.direction==(0.0,1.0) {assert!(e[2]/total>0.99999);}
        else {assert!(e.iter().filter(|&&v|v/total>0.001).count()>=2);}
    }
    if scene.defocus==3 {assert!(energy[1].iter().sum::<f64>()>energy[0].iter().sum::<f64>(),"coarse fixture does not exercise deeper details");}
    json!({"scene":scene.name,"crop_xy":[region.x,region.y],"detail_energy_by_level_hdv":energy})
}
fn original_planes(frame:&Frame,region:align_cmd::CropRect)->Vec<Vec<f32>> {
    [(0,0),(1,0),(0,1),(1,1)].into_iter().map(|(dx,dy)|{
        (0..region.height).flat_map(|y|(0..region.width).map(move |x|{
            let sx=frame.active.x+2*(region.x+x)+dx;let sy=frame.active.y+2*(region.y+y)+dy;
            f32::from(frame.data[sy*frame.stride+sx])-frame.levels.black
        })).collect()
    }).collect()
}
fn direct_mean_rgb(frames:&[Frame],region:align_cmd::CropRect)->Vec<f32> {
    let mut means=vec![vec![0.0;region.width*region.height];4];
    for f in frames {for (m,p) in means.iter_mut().zip(original_planes(f,region)) {for (a,b) in m.iter_mut().zip(p) {*a+=b;}}}
    for p in &mut means {for v in p {*v/=frames.len() as f32;}}
    crate::merge_cmd::phase_packed_rgb::camera_rgb(&means,region.width,region.height,levels(),frames[0].wb_coeffs).unwrap()
}
fn verify(c:&Comparison,frames:&[Frame],hashes:&[String],region:align_cmd::CropRect,noise:&NoiseModel)->Vec<Value> {
    let n=region.width*region.height;
    assert_eq!((c.native_width,c.native_height),(2*region.width,2*region.height));
    assert!(c.known4_original_exact && c.identity_guide_original_exact);assert_eq!(c.frames.len(),frames.len());
    for arm in [&c.baseline_planes4,&c.candidate_planes4] {
        assert_eq!(arm.len(),4);assert!(arm.iter().all(|p|p.len()==n && p.iter().all(|v|v.is_finite())));
    }
    for (k,f) in frames.iter().enumerate() {
        assert_eq!(hash(&f.data),hashes[k]);assert_eq!(c.frames[k].source_sha256,hashes[k]);
        assert!(c.frames[k].known4_original_exact && c.frames[k].identity_guide_original_exact);
        let original=original_planes(f,region);
        let guide=original[1].iter().zip(&original[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
        assert_eq!(float_hash(&guide),c.frames[k].guide_sha256);
        // Explicit sensor-site order, deliberately not CfaPlane::ALL.
        for (p,plane) in [CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B].into_iter().enumerate() {
            let v=original[p].iter().map(|&s|noise.variance(plane,s)).collect::<Vec<_>>();
            assert_eq!(float_hash(&v),c.frames[k].plane_variance_sha256[p],"original plane variance mapping {p}");
        }
    }
    let mut rows=Vec::new();
    for level in 0..2 {for d in 0..3 {
        let s=&c.candidate_weight_summary[level][d];let size=n>>(2*(level+1));
        assert_eq!(s.total_coefficients,size);
        assert!(s.min_weight>=0.0 && s.max_weight.is_finite() && s.min_weight<=s.max_weight);
        assert!(s.positive_source_coefficients<=frames.len()*size && s.multi_source_coefficients<=size);
        assert!((0.0..=1.0).contains(&c.candidate_fallback_fraction[level][d]));
        rows.push(json!({"level":level,"orientation":(["H","D","V"][d]),"min_weight":s.min_weight,"max_weight":s.max_weight,
            "positive_source_coefficients":s.positive_source_coefficients,"multi_source_coefficients":s.multi_source_coefficients,
            "total_coefficients":size,"fallback_fraction":c.candidate_fallback_fraction[level][d],
            "own_plane_positive_source_coefficients":s.own_plane_positive_source_coefficients,
            "own_plane_positive_aggregate_zero":s.own_plane_positive_aggregate_zero}));
    }}rows
}

#[test]
fn independent_all_cfa_00_transform_variance_and_mapping() {
    let operators=commissioning();let mut orientation=Vec::new();
    for phase in 0..2 {for i in [1usize,2,3,6] {orientation.push(ideal_direction_evidence(SCENES[i],crop(phase)));}}
    // Distinct [R,G1,B,G2] model slots ensure an accidental use of ALL order
    // for stored [R,G1,G2,B] planes cannot hide behind identical noise models.
    let model=NoiseModel::new([0.13,0.31,0.71,0.47].map(|g|PlaneNoise{
        gain_dn_per_e:g,read_noise_e:2.0,levels:levels()}),100.0,Provenance::Measured);
    let f=fixture(SCENES[0],0,100.0,&model);let frames=vec![f];
    let hashes=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
    let actual=compare_generated(&frames,crop(0),&model).unwrap();
    verify(&actual,&frames,&hashes,crop(0),&model);
    let v=&actual.frames[0].plane_variance_sha256;
    for i in 0..4 {for j in i+1..4 {assert_ne!(v[i],v[j]);}}
    eprintln!("ALL_CFA_STRUCTURAL {}",json!({"operators":operators,"ideal_orientations_and_coarse":orientation,
        "distinct_plane_mapping_hashes_rg1g2b":v,"injected_model_is_synthetic_mapping_witness":true}));
}

#[test]
fn independent_all_cfa_10_generated_quality_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_ALL_CFA_WAVELET_OUT").expect("root-owned new output path required"));
    std::fs::create_dir(&out).unwrap();let mut cases=Vec::new();let mut decisions=Vec::new();
    let commission=commission_metric(2*crop(0).width,2*crop(0).height,crop(0));
    let mut observer=None;
    for iso in [100.0f32,400.0] {for phase in 0..2 {
        let region=crop(phase);let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());
        assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let mut benefit=false;let mut guards=true;let mut all_exercised=true;
        for mut scene in SCENES {
            if scene.weak_red_amplitude.is_some() {
                let g=gains(scene)[0];let sigma=noise.sigma(CfaPlane::R,0.30*levels().range()/g);
                scene.weak_red_amplitude=Some(f64::from(2.0*sigma*g/levels().range()));
            }
            let frames=(0..N).map(|k|fixture(scene,k,iso,&noise)).collect::<Vec<_>>();
            let hashes=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,region,&noise).unwrap();
            let participation=verify(&c,&frames,&hashes,region,&noise);
            let baseline=score(scene,&c.baseline_rgb,c.native_width,c.native_height,region);
            let candidate=score(scene,&c.candidate_rgb,c.native_width,c.native_height,region);
            let mut mean_placebo=None;let mut weak_witness=None;let mut crossing=None;let mut exercised=true;
            let pass=if scene.frequency==0.0 {
                let averaged=c.candidate_weight_summary.iter().enumerate().map(|(l,s)|s.iter().enumerate()
                    .map(|(d,s)|c.candidate_fallback_fraction[l][d]*s.total_coefficients as f64).sum::<f64>()).sum::<f64>();
                assert!(averaged>100.0,"actual below-floor averaging absent");
                let mean=score(scene,&direct_mean_rgb(&frames,region),c.native_width,c.native_height,region);
                let single=score(scene,&direct_mean_rgb(&frames[2..3],region),c.native_width,c.native_height,region);
                mean_placebo=Some(json!({"source_mean":score_json(&mean),"single_source":score_json(&single),"candidate_rgb_over_mean":candidate.rgb/mean.rgb}));
                benefit|=candidate.rgb<=0.95*baseline.rgb;
                candidate.rgb<=1.25*baseline.rgb && candidate.chroma<=1.25*baseline.chroma
            } else {
                let summaries=c.candidate_weight_summary.iter().flatten().collect::<Vec<_>>();
                let positive=summaries.iter().map(|s|s.positive_source_coefficients).sum::<usize>();
                let multi=summaries.iter().map(|s|s.multi_source_coefficients).sum::<usize>();
                if scene.weak_red_amplitude.is_none() {
                    exercised&=positive>100 && multi>100;
                    if scene.defocus>0 {
                        exercised&=c.baseline_averaged_fraction[0]<1.0;
                        exercised&=c.frames.windows(2).any(|f|f[0].guide_sha256!=f[1].guide_sha256);
                    }
                    if scene.defocus==1 {exercised&=baseline.inphase.iter().all(|&v|v>=0.5);}
                    if scene.defocus==3 {
                        exercised&=c.candidate_weight_summary[1].iter().map(|s|s.positive_source_coefficients).sum::<usize>()>100;
                        exercised&=c.baseline_averaged_fraction[1]<1.0 && baseline.inphase.iter().all(|&v|v>=0.5);
                    }
                }
                let mut ok=preserves_components(&baseline,&candidate) && candidate.rgb<=1.10*baseline.rgb;
                if scene.coloured {benefit|=candidate.rgb<=0.95*baseline.rgb;}
                if scene.defocus==2 {
                    let (b,n)=zero_crossing_error(scene,&c.baseline_rgb,c.native_width,c.native_height,region);
                    let (a,m)=zero_crossing_error(scene,&c.candidate_rgb,c.native_width,c.native_height,region);assert_eq!(n,m);
                    crossing=Some(json!({"pixels":n,"baseline_rb_rmse":b,"candidate_rb_rmse":a,"ratio":a/b,"diagnostic_only":true}));
                }
                if let Some(amplitude)=scene.weak_red_amplitude {
                    let focused=score(scene,&direct_mean_rgb(&frames[2..3],region),c.native_width,c.native_height,region);
                    let own_positive=summaries.iter().map(|s|s.own_plane_positive_source_coefficients[0]).sum::<usize>();
                    let suppressed=summaries.iter().map(|s|s.own_plane_positive_aggregate_zero[0]).sum::<usize>();
                    let live=focused.inphase[0]>=0.5 && own_positive>100;exercised&=live;
                    let retains=candidate.inphase[0].min(1.0)>=0.9*focused.inphase[0].min(1.0);ok&=retains;
                    weak_witness=Some(json!({"truth_red_amplitude":amplitude,"wb_bits":gains(scene).map(f32::to_bits),
                        "predetermined_focused_source":2,"focused_source":score_json(&focused),"own_red_positive_source_coefficients":own_positive,
                        "own_red_positive_but_aggregate_zero":suppressed,"feasibility_exercised":live,
                        "focused_source_component_guard":retains}));
                    if iso==100.0 && phase==0 {
                        let off=super::compare_generated_with_diagnostics(&frames,region,&noise,false).unwrap();
                        let before=[float_hash(&c.baseline_rgb),float_hash(&c.candidate_rgb)];
                        let after=[float_hash(&off.baseline_rgb),float_hash(&off.candidate_rgb)];assert_eq!(before,after);
                        for (a,b) in c.baseline_planes4.iter().chain(&c.candidate_planes4).zip(off.baseline_planes4.iter().chain(&off.candidate_planes4)) {
                            assert_eq!(float_hash(a),float_hash(b));
                        }
                        for level in 0..2 {for d in 0..3 {
                            assert_eq!(off.candidate_weight_summary[level][d].own_plane_positive_source_coefficients,[0;4]);
                            assert_eq!(off.candidate_weight_summary[level][d].positive_source_coefficients,c.candidate_weight_summary[level][d].positive_source_coefficients);
                        }}
                        for (f,h) in frames.iter().zip(&hashes) {assert_eq!(&hash(&f.data),h);}
                        observer=Some(json!({"baseline_candidate_rgb_on":before,"baseline_candidate_rgb_off":after,
                            "all_eight_collapsed_planes_exact":true,"observer_counts_disabled":true}));
                    }
                }ok
            };
            guards&=pass;all_exercised&=exercised;
            let evidence=c.frames.iter().map(|f|json!({"source_sha256":f.source_sha256,"guide_sha256":f.guide_sha256,
                "variance_sha256":f.variance_sha256,"plane_variance_sha256":f.plane_variance_sha256,
                "coefficient_variance_sha256":f.coefficient_variance_sha256})).collect::<Vec<_>>();
            let record=json!({"iso":iso,"crop_phase":phase,"crop_xy":[region.x,region.y],"scene":scene.name,
                "baseline":score_json(&baseline),"candidate":score_json(&candidate),"rgb_ratio":candidate.rgb/baseline.rgb,
                "chroma_ratio":candidate.chroma/baseline.chroma,"guard_pass":pass,"fixture_exercised":exercised,
                "flat_mean_placebo":mean_placebo,"weak_red_witness":weak_witness,"truth_green_zero_crossings":crossing,
                "directional_participation":participation,"baseline_averaged_fraction":c.baseline_averaged_fraction,"sources":evidence});
            eprintln!("ALL_CFA_CASE {}",record);cases.push(record);
        }
        decisions.push(json!({"iso":iso,"crop_phase":phase,"benefit":benefit,"guards_pass":guards,
            "fixtures_exercised":all_exercised,"admitted":benefit && guards && all_exercised}));
    }}
    assert!(observer.is_some());
    let admitted=decisions.iter().all(|v|v["admitted"]==true);
    let result=json!({"status":"SCREEN_COMPLETE","next_composed_check_admitted":admitted,"photographic_replay_admitted":false,
        "iso_phase_decisions":decisions,"metric_commission":commission,"observer_neutrality":observer,"cases":cases,
        "scope":"Identity u16, two complex levels versus actual two-level pyramid. Original-site variance propagated exactly; no fractional, optical, photographic or calibration claim."});
    save(&out.join("screen.json"),&result);eprintln!("ALL_CFA_SCREEN {}",result);
}
