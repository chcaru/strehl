// Independent fixed screen. Root executes; independent-plan.md owns the bars.
use super::{camera_rgb, compare_generated, gather_patch, CfaPatch, Comparison};
use crate::{align_cmd, image_out};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{f64::consts::TAU, fs::File, path::{Path,PathBuf}};
use strehl_core::{CfaPlane, align::{Cx,Similarity}, noise::{Levels,NoiseModel},
    optics::{OpticalProfile,A7C2_FE100GM_2XTC_X4CPL}, plane::PlaneGeometry,
    profile, pyramid::MergeConfig};
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
fn verify_actual_writer(c:&Comparison,out:&Path)->Value {
    let domain=super::super::PyramidDomain::cropped(geometry(),crop()).unwrap();
    let path=out.join("actual-baseline-writer.tiff");
    super::super::write_merged(super::super::Merged::Bands{domain,planes:&c.baseline_planes4},levels(),Some(GAIN),None,
        image_out::OutputSpace::CameraLinear,true,super::super::Exposure::None,None,&path).unwrap();
    let dev=image_out::OutputSpace::CameraLinear.develop(None);
    let manual=c.baseline_rgb.chunks_exact(3).flat_map(|p|image_out::develop_pixel([p[0],p[1],p[2]],&dev)).collect::<Vec<_>>();
    let mut decoder=tiff::decoder::Decoder::new(File::open(&path).unwrap()).unwrap();
    assert_eq!(decoder.dimensions().unwrap(),(c.native_width as u32,c.native_height as u32));
    let tiff::decoder::DecodingResult::U16(actual)=decoder.read_image().unwrap() else {panic!("actual writer did not emit RGB16")};
    assert_eq!(actual,manual,"comparison baseline differs from actual product writer");
    json!({"all_u16_samples_exact":true,"samples":actual.len(),"tiff":path})
}
fn save(path:&Path,value:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}

#[test]
fn independent_phase_packed_generated_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_PHASE_PACKED_OUT").expect("root-owned output required"));
    std::fs::create_dir(&out).unwrap();
    let mut records=Vec::new();let mut flat_ok=true;let mut components_ok=true;let mut iso_gains=[false;2];
    let mut metric_commission=None;let mut writer=None;
    for (iso_slot,iso) in [100.0f32,400.0].into_iter().enumerate() {
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());
        assert!(noise.is_trustworthy() && noise.prnu().is_none());
        for fractional in [false,true] {
            let transforms=transforms(fractional);
            for scene in SCENES {
                let frames=transforms.iter().enumerate().map(|(k,t)|fixture(scene,k,*t,iso,&noise)).collect::<Vec<_>>();
                let original=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
                let comparison=compare_generated(&frames,&transforms,crop(),&noise,MergeConfig::default()).unwrap();
                assert_eq!((comparison.native_width,comparison.native_height),(2*crop().width,2*crop().height));
                assert_eq!(comparison.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
                assert_eq!(comparison.baseline_planes4.len(),4);assert_eq!(comparison.packed_planes12.len(),12);
                for c in 0..4 {assert!(comparison.baseline_planes4[c].iter().zip(&comparison.packed_planes12[c]).all(|(a,b)|a.to_bits()==b.to_bits()));}
                for (i,f) in frames.iter().enumerate() {assert_eq!(original[i],hash(&f.data));assert_eq!(original[i],comparison.frames[i].source_sha256);}
                assert!(comparison.frames.iter().all(|f|!f.beta.is_empty() && f.beta.iter().all(|v|v.is_finite())));
                let baseline=score(scene,&comparison.baseline_rgb,comparison.native_width,comparison.native_height);
                let candidate=score(scene,&comparison.candidate_rgb,comparison.native_width,comparison.native_height);
                let flat_pass=if scene.frequency==0.0 {
                    let ok=candidate.rgb<=1.25*baseline.rgb && candidate.chroma<=1.25*baseline.chroma;flat_ok&=ok;Some(ok)
                } else {None};
                let mut component_pass=None;
                if scene.coloured {
                    // Contrast above truth is not recovered signal. Removing
                    // baseline overshoot must not fail a detail-preservation bar.
                    let ok=preserves_components(&baseline,&candidate);
                    components_ok&=ok;component_pass=Some(ok);
                    if candidate.rgb<=0.95*baseline.rgb || candidate.chroma<=0.95*baseline.chroma {iso_gains[iso_slot]=true;}
                }
                if metric_commission.is_none() {metric_commission=Some(commission_metric(comparison.native_width,comparison.native_height));}
                if writer.is_none() && scene.coloured {writer=Some(verify_actual_writer(&comparison,&out));}
                if scene.defocus {
                    assert!(sigma(scene,40.0,144.0,Some(0))<sigma(scene,40.0,144.0,Some(4)));
                    assert!(sigma(scene,280.0,144.0,Some(4))<sigma(scene,280.0,144.0,Some(0)));
                    assert!(!comparison.averaged_fraction.is_empty() && comparison.averaged_fraction[0]<1.0,
                        "varying-focus fixture never selected any finest-band signal");
                    assert!(comparison.frames.windows(2).any(|p|p[0].guide_sha256!=p[1].guide_sha256),
                        "varying-focus fixture fed identical guides to every frame");
                }
                let frame_evidence=comparison.frames.iter().map(|f|json!({"source_sha256":f.source_sha256,
                    "guide_sha256":f.guide_sha256,"variance_sha256":f.variance_sha256,"beta":f.beta})).collect::<Vec<_>>();
                let record=json!({"scene":scene.name,"iso":iso,"fractional":fractional,"baseline":score_json(&baseline),"candidate":score_json(&candidate),
                    "rgb_ratio":candidate.rgb/baseline.rgb,"chroma_ratio":candidate.chroma/baseline.chroma,
                    "flat_pass":flat_pass,"component_pass":component_pass,"averaged_fraction":comparison.averaged_fraction,
                    "level_sizes":comparison.level_sizes,"frames":frame_evidence});
                eprintln!("PHASE_CASE {}",record);records.push(record);
            }
        }
    }
    let admitted=flat_ok && components_ok && iso_gains.iter().all(|v|*v);
    let result=json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admitted,"flat_guard_pass":flat_ok,
        "colour_component_guard_pass":components_ok,"truth_gain_by_iso_100_400":iso_gains,
        "metric_commission":metric_commission,"actual_writer":writer,"cases":records,
        "interpretation":"Root-approved fixed admission screen. Structural tests passing does not mean candidate quality is accepted. No SOTA/default claim."});
    save(&out.join("screen.json"),&result);
    eprintln!("PHASE_DECISION {}",json!({"photographic_replay_admitted":admitted,"flat_guard_pass":flat_ok,"colour_component_guard_pass":components_ok,"truth_gain_by_iso":iso_gains}));
}

#[test]
fn independent_phase_packed_all_channel_phase_ca_and_support() {
    let noise=profile::noise_model_for("ILCE-7CM2",Some(100.0),levels());
    let t=Similarity{a:Cx::new(1.0023,0.0037),b:Cx::new(0.183,-0.271)};
    let frame=fixture(SCENES[4],0,t,100.0,&noise);let original=hash(&frame.data);
    let profile=OpticalProfile{eps_r:0.012,eps_b:Some(-0.009),translation:(0.13,-0.09),
        key:"INDEPENDENT-PHASE-PACKED",..A7C2_FE100GM_2XTC_X4CPL};
    let patch=CfaPatch::from_frame(&frame);
    let packed=gather_patch(&patch,t,geometry(),crop(),Some(&profile)).unwrap();
    assert_eq!(packed.len(),12);
    let native_sites=[(0usize,0usize),(1,0),(0,1),(1,1)];
    let observed_sites=[(0usize,0usize),(1,0),(1,1)];
    let mut checked=0usize;
    for (site,&(dx,dy)) in native_sites.iter().enumerate() {for (c,&(kx,ky)) in observed_sites.iter().enumerate() {
        // Move the existing oracle's known destination site to the desired
        // phase through an input-coordinate translation. CA remains the
        // existing oracle's colour-specific pull, with no second interpolation.
        let sx=(dx as f64-kx as f64)*0.5;let sy=(dy as f64-ky as f64)*0.5;
        let shifted=Similarity{a:t.a,b:Cx::new(t.b.re+t.a.re*sx-t.a.im*sy,t.b.im+t.a.im*sx+t.a.re*sy)};
        let mut copy=frame.clone();
        let oracle=align_cmd::gpu_cpu_oracle(&mut copy,shifted,geometry(),Some(profile),false).unwrap();
        for y in 0..crop().height {for x in 0..crop().width {
            let j=(2*(crop().y+y)+ky)*W+2*(crop().x+x)+kx;
            assert!(oracle.coverage[j] && oracle.sensor_values[j].is_finite());
            let expected=(oracle.sensor_values[j].round().clamp(0.0,65535.0) as u16 as f32-levels().black).max(0.0);
            assert_eq!(packed[PACK[site][c]][y*crop().width+x].to_bits(),expected.to_bits(),
                "channel {c}, site {site}, crop {x},{y}");checked+=1;
        }}
    }}
    let wrong_phase=packed[PACK[0][0]].iter().zip(&packed[PACK[1][0]]).filter(|(a,b)|a.to_bits()!=b.to_bits()).count();
    let wrong_colour=packed[PACK[0][0]].iter().zip(&packed[PACK[0][2]]).filter(|(a,b)|a.to_bits()!=b.to_bits()).count();
    assert!(wrong_phase>10000 && wrong_colour>10000);
    let reconstructed=camera_rgb(&packed,crop().width,crop().height,levels(),frame.wb_coeffs).unwrap();
    for y in 0..2*crop().height {for x in 0..2*crop().width {for c in 0..3 {
        let slot=PACK[(y%2)*2+x%2][c];let expected=packed[slot][(y/2)*crop().width+x/2].max(0.0)*GAIN[c]*1.0/levels().range();
        assert_eq!(reconstructed[(y*2*crop().width+x)*3+c].to_bits(),expected.to_bits());
    }}}
    let mut unsupported=CfaPatch::from_frame(&frame);unsupported.origin_native=[1,0];
    assert!(gather_patch(&unsupported,t,geometry(),crop(),Some(&profile)).is_err());
    let far=Similarity{a:Cx::ONE,b:Cx::new(-20.0,0.0)};
    assert!(gather_patch(&patch,far,geometry(),crop(),None).is_err());
    let nonfinite=Similarity{a:Cx::new(f64::NAN,0.0),b:Cx::ZERO};
    assert!(gather_patch(&patch,nonfinite,geometry(),crop(),None).is_err());
    assert_eq!(hash(&frame.data),original);
    eprintln!("PHASE_GEOMETRY checked={checked}, wrong-phase={wrong_phase}, wrong-colour={wrong_colour}, source unchanged");
}

#[test]
fn independent_phase_packed_full_source_and_twelve_pull_support() {
    let noise=profile::noise_model_for("ILCE-7CM2",Some(100.0),levels());
    let t=Similarity{a:Cx::new(1.0023,0.0037),b:Cx::new(0.183,-0.271)};
    let frame=fixture(SCENES[4],1,t,100.0,&noise);let original=hash(&frame.data);
    let ca=OpticalProfile{eps_r:0.012,eps_b:Some(-0.009),translation:(0.13,-0.09),
        key:"INDEPENDENT-FULL-PHASE",..A7C2_FE100GM_2XTC_X4CPL};
    let patch=CfaPatch::from_frame(&frame);
    let retained=gather_patch(&patch,t,geometry(),crop(),Some(&ca)).unwrap();
    assert!(super::full_stack::full_source_supported(t,geometry(),crop(),Some(&ca)));
    let full=super::full_stack::gather_full_source(&frame,t,geometry(),crop(),Some(&ca),0).unwrap();
    let missing=super::full_stack::gather_full_source(&frame,t,geometry(),crop(),Some(&ca),4).unwrap();
    assert_eq!(full.len(),12);assert_eq!(missing.len(),8);
    let mut interior_checked=0usize;
    for slot in 0..12 {
        assert_eq!(full[slot].len(),crop().width*crop().height);
        for (a,b) in full[slot].iter().zip(&retained[slot]) {
            assert_eq!(a.to_bits(),b.to_bits(),"full source versus retained patch slot {slot}");
            interior_checked+=1;
        }
        if slot>=4 {assert!(full[slot].iter().zip(&missing[slot-4]).all(|(a,b)|a.to_bits()==b.to_bits()));}
    }
    // Deliberately touch real MHC sensor-edge stencils. A retained patch must
    // refuse these, while the full-source route uses the existing reflection.
    let edge=align_cmd::CropRect{x:1,y:1,width:W/2-2,height:H/2-2};
    let edge_t=Similarity{a:Cx::ONE,b:Cx::new(-0.125,-0.125)};
    let edge_ca=OpticalProfile{eps_r:0.0005,eps_b:Some(-0.0004),translation:(0.03,-0.02),
        key:"INDEPENDENT-FULL-PHASE-EDGE",..A7C2_FE100GM_2XTC_X4CPL};
    assert!(gather_patch(&patch,edge_t,geometry(),edge,Some(&edge_ca)).is_err());
    assert!(super::full_stack::full_source_supported(edge_t,geometry(),edge,Some(&edge_ca)));
    let edge_planes=super::full_stack::gather_full_source(&frame,edge_t,geometry(),edge,Some(&edge_ca),0).unwrap();
    let sites=[(0usize,0usize),(1,0),(0,1),(1,1)];
    let known=[(0usize,0usize),(1,0),(1,1)];
    let mut edge_checked=0usize;
    for (site,&(dx,dy)) in sites.iter().enumerate() {for (c,&(kx,ky)) in known.iter().enumerate() {
        let sx=(dx as f64-kx as f64)*0.5;let sy=(dy as f64-ky as f64)*0.5;
        let shifted=Similarity{a:edge_t.a,b:Cx::new(edge_t.b.re+edge_t.a.re*sx-edge_t.a.im*sy,
            edge_t.b.im+edge_t.a.im*sx+edge_t.a.re*sy)};
        let oracle=align_cmd::gpu_cpu_oracle(&mut frame.clone(),shifted,geometry(),Some(edge_ca),false).unwrap();
        for y in 0..edge.height {for x in 0..edge.width {
            let j=(2*(edge.y+y)+ky)*W+2*(edge.x+x)+kx;
            assert!(oracle.coverage[j] && oracle.sensor_values[j].is_finite());
            let expected=(oracle.sensor_values[j].round().clamp(0.0,65535.0) as u16 as f32-levels().black).max(0.0);
            assert_eq!(edge_planes[PACK[site][c]][y*edge.width+x].to_bits(),expected.to_bits(),
                "real sensor edge colour {c}, phase {site}, crop {x},{y}");edge_checked+=1;
        }}
    }}
    // Negative control: known B@11 is covered, but B@00 is not. Four-site
    // coverage alone is therefore incapable of admitting this RGB crop.
    let narrow=align_cmd::CropRect{x:1,y:2,width:10,height:9};
    let expand_blue=OpticalProfile{eps_r:0.0,eps_b:Some(0.005),translation:(0.0,0.0),
        key:"INDEPENDENT-MISSING-BLUE-SUPPORT",..A7C2_FE100GM_2XTC_X4CPL};
    let oracle=align_cmd::gpu_cpu_oracle(&mut frame.clone(),Similarity::IDENTITY,geometry(),Some(expand_blue),false).unwrap();
    for y in 0..narrow.height {for x in 0..narrow.width {for (dx,dy) in sites {
        assert!(oracle.coverage[(2*(narrow.y+y)+dy)*W+2*(narrow.x+x)+dx],"known CFA site unexpectedly uncovered");
    }}}
    let missing_blue=align_cmd::gpu_cpu_oracle(&mut frame.clone(),Similarity{a:Cx::ONE,b:Cx::new(-0.5,-0.5)},
        geometry(),Some(expand_blue),false).unwrap();
    let missing_uncovered=(0..narrow.height).flat_map(|y|(0..narrow.width).map(move |x|(x,y)))
        .filter(|&(x,y)|!missing_blue.coverage[(2*(narrow.y+y)+1)*W+2*(narrow.x+x)+1]).count();
    assert!(missing_uncovered>0,"additional-colour support failure never exercised");
    assert!(!super::full_stack::full_source_supported(Similarity::IDENTITY,geometry(),narrow,Some(&expand_blue)));
    assert!(super::full_stack::gather_full_source(&frame,Similarity::IDENTITY,geometry(),narrow,Some(&expand_blue),0).is_err());
    assert!(super::full_stack::gather_full_source(&frame,Similarity::IDENTITY,geometry(),narrow,Some(&expand_blue),4).is_err());
    let exact=Similarity{a:Cx::ONE,b:Cx::new(-0.25,-0.25)};
    let outside=Similarity{a:Cx::ONE,b:Cx::new(-0.2500001,-0.25)};
    assert!(super::full_stack::full_source_supported(exact,geometry(),edge,None),"inclusive 1.5-pixel sampler edge refused");
    assert!(super::full_stack::gather_full_source(&frame,exact,geometry(),edge,None,0).is_ok());
    assert!(!super::full_stack::full_source_supported(outside,geometry(),edge,None));
    assert!(super::full_stack::gather_full_source(&frame,outside,geometry(),edge,None,0).is_err());
    let bad=Similarity{a:Cx::new(f64::NAN,0.0),b:Cx::ZERO};
    assert!(!super::full_stack::full_source_supported(bad,geometry(),crop(),None));
    assert!(super::full_stack::gather_full_source(&frame,bad,geometry(),crop(),None,0).is_err());
    assert_eq!(hash(&frame.data),original);
    eprintln!("PHASE_FULL_SOURCE interior_exact={interior_checked}, edge_oracle_exact={edge_checked}, missing_blue_uncovered={missing_uncovered}, original_CFA_unchanged");
}

#[test]
fn independent_phase_packed_full_adapter_chunks_and_held_writer() {
    use super::super::{BandMerge,BandWorker,FrameWorkspace,Workspace,PyramidDomain,PyramidFrameSource,level_sizes};
    use strehl_core::{align::Resampler,warpmap::{WarpMap,StackIdentity,FrameWarp,Provenance}};
    let cfg=MergeConfig::default();let sizes=level_sizes(crop().width,crop().height,cfg.bands);
    let noise=profile::noise_model_for("ILCE-7CM2",Some(400.0),levels());let ts=transforms(true);
    let frames=ts.iter().enumerate().map(|(k,t)|fixture(SCENES[6],k,*t,400.0,&noise)).collect::<Vec<_>>();
    let hashes=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(Provenance{stack:StackIdentity::from_entries("independent-full-source-chunks",&entries),
        strategy:"independent generated coordinate truth".into(),heldout_px:None,cycle_floor_px:None,reference:2,
        note:"three chunks, unequal final extent".into()},geometry(),Resampler::CatmullRom,ts.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a [Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()}
        fn decode(&self,index:usize)->anyhow::Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(&frames);let domain=PyramidDomain::cropped(geometry(),crop()).unwrap();
    let mut base=BandWorker::new(domain,cfg);let mut packed=BandMerge::new(crop().width,crop().height,12,cfg);
    let mut explicit=BandMerge::new(crop().width,crop().height,4,cfg);
    let mut packed_ws=FrameWorkspace::new(&sizes,12);let mut explicit_ws=FrameWorkspace::new(&sizes,4);
    let (mut base_total,mut packed_total,mut explicit_total):(Option<BandMerge>,Option<BandMerge>,Option<BandMerge>)=(None,None,None);
    let mut chunk_lengths=Vec::new();
    for (chunk_index,indices) in (0..N).collect::<Vec<_>>().chunks(2).enumerate() {
        chunk_lengths.push(indices.len());
        for &index in indices {
            assert!(base.fold(&source,index,levels(),&noise,Some(&map),None).unwrap());
            let all=super::full_stack::gather_full_source(&frames[index],ts[index],geometry(),crop(),None,0).unwrap();
            for c in 0..4 {assert!(base.planes[c].iter().zip(&all[c]).all(|(a,b)|a.to_bits()==b.to_bits()));}
            let refs=base.planes.iter().chain(all[4..].iter()).map(Vec::as_slice).collect::<Vec<_>>();
            packed_ws.next_frame();explicit_ws.next_frame();
            let beta=(!base.beta.is_empty()).then_some(base.beta.as_slice());
            packed.add_frame_with_gain(&refs,&base.luma,&base.var,beta,&mut packed_ws);
            explicit.add_frame_with_gain(&refs[..4],&base.luma,&base.var,beta,&mut explicit_ws);
        }
        super::full_stack::absorb_chunk(&mut base_total,&mut base.merge,crop().width,crop().height,4,cfg);
        super::full_stack::absorb_chunk(&mut packed_total,&mut packed,crop().width,crop().height,12,cfg);
        // Independent direct public-API reduction, without adapter helper.
        if let Some(total)=explicit_total.as_mut() {total.absorb(&explicit);}
        else {explicit_total=Some(std::mem::replace(&mut explicit,BandMerge::new(crop().width,crop().height,4,cfg)));}
        if chunk_index<2 {base.reset_chunk();packed.reset_for_reuse();explicit.reset_for_reuse();}
    }
    assert_eq!(chunk_lengths,vec![2,2,1]);
    let base_total=base_total.unwrap();let packed_total=packed_total.unwrap();let explicit_total=explicit_total.unwrap();
    assert_eq!(base_total.frames(),N as u32);assert_eq!(packed_total.frames(),N as u32);
    let fraction=base_total.averaged_fraction();assert!(fraction[0]<1.0,"chunk test never selected detail");
    assert!(fraction.iter().zip(packed_total.averaged_fraction()).all(|(a,b)|a.to_bits()==b.to_bits()));
    let baseline=base_total.finish(&mut Workspace::new(&sizes));
    let candidate=packed_total.finish(&mut Workspace::new(&sizes));
    let expected=explicit_total.finish(&mut Workspace::new(&sizes));
    for c in 0..4 {for ((a,b),e) in baseline[c].iter().zip(&candidate[c]).zip(&expected[c]) {
        assert_eq!(a.to_bits(),b.to_bits());assert_eq!(a.to_bits(),e.to_bits());
    }}
    // Arithmetic contract witness only: these formulas do not validate noise
    // or image quality. Twelve-plane planning is an explicit wrong alternative.
    let full=PlaneGeometry{width:3516,height:2344};let frame_bytes=7168*5120*2;
    let plan=super::full_stack::chunk_plan(full,frame_bytes,70,cfg);
    let budget_sizes=level_sizes(full.width,full.height,cfg.bands);
    let bytes=|planes|4*(BandMerge::planning_accumulator_floats(full.width,full.height,planes,cfg)
        +FrameWorkspace::planning_floats(&budget_sizes,planes)+(planes+2)*full.pixels())+frame_bytes;
    assert_eq!(plan.planning_bytes,bytes(4));
    let groups=|n:usize| (super::super::MEMORY_BUDGET_BYTES/n).max(1).min(70);
    assert_eq!(plan.canonical_chunks,groups(bytes(4)));assert_eq!(plan.per_chunk,70usize.div_ceil(plan.canonical_chunks));
    assert_ne!(groups(bytes(4)),groups(bytes(12)),"wrong plane-count planner was not distinguished");
    let out=PathBuf::from(std::env::var_os("STREHL_PHASE_PACKED_OUT").unwrap()).with_extension("full-adapter");
    std::fs::create_dir(&out).unwrap();
    let mut dev=image_out::OutputSpace::CameraLinear.develop(None);
    dev.tone=Some(image_out::Tone{black:0.090420,white:0.914606,contrast:0.55});
    let mut written=0usize;
    for (name,planes) in [("baseline",&baseline),("candidate",&candidate)] {
        let path=out.join(format!("{name}.tiff"));
        super::full_stack::write_planes(&path,planes,crop(),levels(),frames[0].wb_coeffs,&dev).unwrap();
        let camera=camera_rgb(planes,crop().width,crop().height,levels(),frames[0].wb_coeffs).unwrap();
        let expected=camera.chunks_exact(3).flat_map(|p|image_out::develop_pixel([p[0],p[1],p[2]],&dev)).collect::<Vec<_>>();
        let untone=image_out::OutputSpace::CameraLinear.develop(None);
        assert!(camera.chunks_exact(3).any(|p|image_out::develop_pixel([p[0],p[1],p[2]],&dev)
            !=image_out::develop_pixel([p[0],p[1],p[2]],&untone)),"held-tone witness did not exercise tone");
        let mut decoder=tiff::decoder::Decoder::new(File::open(&path).unwrap()).unwrap();
        assert_eq!(decoder.dimensions().unwrap(),((2*crop().width) as u32,(2*crop().height) as u32));
        let tiff::decoder::DecodingResult::U16(actual)=decoder.read_image().unwrap() else {panic!("full adapter writer was not RGB16")};
        assert_eq!(actual,expected,"full adapter {name} writer changed held development");written+=actual.len();
    }
    for (i,f) in frames.iter().enumerate() {assert_eq!(hash(&f.data),hashes[i]);}
    eprintln!("PHASE_FULL_ADAPTER chunks={chunk_lengths:?}, known4_and_explicit_absorb_exact={}, held_writer_samples_exact={written}, four_plane_plan={plan:?}, wrong_twelve_chunks={}",
        4*crop().width*crop().height,groups(bytes(12)));
}
