// Independent fixed scene screen; root executes, author does not verify.
use super::{compare_generated, compare_generated_forced, Comparison, Mode};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},
    profile,pyramid::{MergeConfig,level_sizes,Pyramid,Workspace,FrameWorkspace,BandMerge,
        shared_source_field_diagnostic::Replay,donor_consistency_diagnostic::resolved_coefficients}};
use strehl_raw::{Frame,Region};

const W:usize=320;
const H:usize=288;
const N:usize=5;
const GAIN:[f32;3]=[1.7,1.0,2.3];
fn crop()->align_cmd::CropRect {align_cmd::CropRect{x:7,y:9,width:145,height:125}}
fn levels()->Levels {Levels{black:512.0,white:15360.0}}
fn channel(x:usize,y:usize)->usize {match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane {match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn hash(v:&[u16])->String {let mut h=Sha256::new();for x in v {h.update(x.to_le_bytes());}h.finalize().iter().map(|v|format!("{v:02x}")).collect()}
fn hash32(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64 {
    let s=(x as u32)^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x31d59a67;
    let u=(hash32(s) as f64+0.5)/4294967296.0;
    let v=(hash32(s^0xa73126bd) as f64+0.5)/4294967296.0;
    (-2.0*u.ln()).sqrt()*(TAU*v).cos()
}
#[derive(Clone,Copy,Debug,PartialEq)]
enum Scene {Flat,GlintDepth,TrueRadial,ThinDepth,ColourOnly}
impl Scene {fn name(self)->&'static str {match self {Self::Flat=>"flat",Self::GlintDepth=>"glint-depth-step",Self::TrueRadial=>"true-coloured-radial",Self::ThinDepth=>"equal-mean-thin-depth",Self::ColourOnly=>"constant-green-colour"}}}

// Continuous Gaussian shapes conserve integral as their covariance changes.
// They are adversarial PSFs, not a fitted model of the user's optical train.
fn elliptical(x:f64,y:f64,angle:f64,sx:f64,sy:f64)->f64 {
    let (s,c)=angle.sin_cos();let u=c*x+s*y;let v=-s*x+c*y;
    (-0.5*((u/sx).powi(2)+(v/sy).powi(2))).exp()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->f64 {
    match scene {
        Scene::Flat=>0.25,
        Scene::ColourOnly=>if c==1 {0.25} else {let d=k.map_or(0.0,|j|(j as f64-2.0).abs());
            0.25+0.07*(-0.5*(TAU*0.075*(0.65+1.1*d)).powi(2)).exp()
                *(TAU*0.075*(if c==0{x}else{y})+0.3).cos()},
        Scene::ThinDepth=>{
            let far_sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-1.0).abs());
            let sx=(30.0f64.powi(2)+far_sigma*far_sigma).sqrt();
            let sy=(1.3f64.powi(2)+far_sigma*far_sigma).sqrt();
            let far=0.25+[0.10,0.12,0.09][c]*30.0*1.3/(sx*sy)
                *elliptical(x-152.0,y-140.0,TAU/4.0,sx,sy);
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-4.0).abs());
            let width=(1.2f64.powi(2)+sigma*sigma).sqrt();
            let line=[0.12,0.14,0.11][c]*1.2/width*(-0.5*((y-138.0)/width).powi(2)).exp();
            let radius=(3.0*sigma).ceil() as i32;
            let mut mass=0.0;let mut coverage=0.0;let mut premult=0.0;
            for dx in -radius..=radius {let ww=(-0.5*(dx as f64/sigma).powi(2)).exp();mass+=ww;
                let xx=x+dx as f64;if xx>=164.0 {coverage+=ww;
                    premult+=ww*(0.25+line*(1.0+0.2*(TAU*0.035*xx).cos()));}}
            premult/mass+(1.0-coverage/mass)*far
        },
        Scene::TrueRadial=>{
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-3.0).abs());
            let sx=(24.0f64.powi(2)+sigma*sigma).sqrt();
            let sy=(1.6f64.powi(2)+sigma*sigma).sqrt();
            [0.24,0.26,0.22][c]+0.14*24.0*1.6/(sx*sy)
                *elliptical(x-148.0,y-138.0,[0.0,TAU/6.0,TAU/3.0][c],sx,sy)
        },
        Scene::GlintDepth=>{
            let d=k.map_or(0.0,|j|j as f64);
            let sx=1.8+8.0*d;let sy=1.8+0.15*d;
            let glint=[0.50,0.52,0.48][c]*1.8*1.8/(sx*sy)
                *elliptical(x-122.0,y-120.0,[0.48,0.70,0.92][c],sx,sy);
            let far=[0.16,0.17,0.19][c]+glint+0.01
                *(-0.5*(TAU*0.02*(0.65+1.1*d)).powi(2)).exp()
                *(TAU*0.02*(0.8*x+0.6*y)+0.37).cos();
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-4.0).abs());
            let r=(3.0*sigma).ceil() as i32;
            let mut sum=0.0;let mut coverage=0.0;let mut premultiplied=0.0;
            let (dx,dy,phase)=[(0.8,0.6,0.37),(1.0,0.0,1.13),(-0.6,0.8,2.07)][c];
            let attenuation_y=(-0.5*(TAU*0.14*dy*sigma).powi(2)).exp();
            for offset in -r..=r {
                let w=(-0.5*(offset as f64/sigma).powi(2)).exp();sum+=w;
                let xx=x+offset as f64;
                if xx>=176.0 {
                    coverage+=w;
                    premultiplied+=w*([0.24,0.26,0.30][c]+[0.065,0.075,0.055][c]
                        *attenuation_y*(TAU*0.14*(dx*xx+dy*y)+phase).cos());
                }
            }
            // M13 near-over-far composition: blur premultiplied radiance and
            // its mask together. The near blur actually crosses the depth edge.
            premultiplied/sum+(1.0-coverage/sum)*far
        }
    }
}
fn transforms()->Vec<Similarity> {
    let shifts=[(-0.46,0.32),(0.37,-0.21),(0.0,0.0),(0.23,0.44),(-0.18,-0.39)];
    (0..N).map(|k| {let j=k as f64-2.0;Similarity{a:Cx::new(1.0+0.0008*j,0.0004*j),
        b:Cx::new(shifts[k].0/2.0,shifts[k].1/2.0)}}).collect()
}
fn fixture(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel)->Frame {
    fixture_noise(scene,k,t,iso,noise,true)
}
fn fixture_noise(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel,add_noise:bool)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,
        levels:levels(),iso:Some(iso),wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],
        xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),
        path:std::env::current_dir().unwrap().join(format!("nonexistent-independent-shared-{}-{k}.ARW",scene.name()))};
    assert!(!f.path.exists());let determinant=t.a.re*t.a.re+t.a.im*t.a.im;
    for y in 0..H {for x in 0..W {
        // Explicit inverse of the native pull; no interpolated source image.
        let u=x as f64-W as f64/2.0-2.0*t.b.re;let v=y as f64-H as f64/2.0-2.0*t.b.im;
        let wx=W as f64/2.0+(t.a.re*u+t.a.im*v)/determinant;
        let wy=H as f64/2.0+(-t.a.im*u+t.a.re*v)/determinant;
        let signal=(radiance(scene,channel(x,y),wx,wy,Some(k))*f64::from(levels().range())/f64::from(GAIN[channel(x,y)])) as f32;
        let value=512.0+f64::from(signal)+if add_noise {gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal))}else{0.0};
        assert!(value>512.0 && value<15360.0,"fixture clipped at {x},{y}, frame{k}");
        f.data[(active.y+y)*stride+active.x+x]=value.round() as u16;
    }}f
}
#[derive(Clone,Copy)]
struct Window {name:&'static str,x0:usize,y0:usize,x1:usize,y1:usize}
const FAN:Window=Window{name:"fan",x0:138,y0:133,x1:171,y1:167};
const CORE:Window=Window{name:"core",x0:112,y0:110,x1:133,y1:132};
const EDGE:Window=Window{name:"depth-boundary",x0:160,y0:80,x1:192,y1:208};
const NEAR:Window=Window{name:"nearer-real-texture",x0:180,y0:96,x1:224,y1:192};
const RADIAL:Window=Window{name:"real-coloured-rays",x0:84,y0:72,x1:232,y1:216};
const THIN_FAR:Window=Window{name:"thin-far",x0:141,y0:92,x1:163,y1:188};
const THIN_NEAR:Window=Window{name:"thin-near",x0:168,y0:130,x1:222,y1:147};
const JUNCTION:Window=Window{name:"thin-junction",x0:148,y0:112,x1:184,y1:166};
const FLAT:Window=Window{name:"flat-interior",x0:38,y0:42,x1:280,y1:244};
#[derive(Clone)]
struct Score {rgb:f64,chroma:f64,recovery:[f64;3],truth_sd:[f64;3]}
fn score(scene:Scene,rgb:&[f32],window:Window)->Score {
    let w=2*crop().width;let h=2*crop().height;
    assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    assert!(window.x0>=2*crop().x && window.y0>=2*crop().y && window.x1<=2*crop().x+w && window.y1<=2*crop().y+h);
    let mut error=0.0;let mut chroma=0.0;let mut sums=[[0.0;5];3];
    let n=((window.x1-window.x0)*(window.y1-window.y0)) as f64;
    for y in window.y0..window.y1 {for x in window.x0..window.x1 {
        let mut e=[0.0;3];let index=((y-2*crop().y)*w+x-2*crop().x)*3;
        for c in 0..3 {
            let truth=radiance(scene,c,x as f64,y as f64,None);let value=f64::from(rgb[index+c]);
            e[c]=value-truth;error+=e[c]*e[c];
            for (a,b) in sums[c].iter_mut().zip([truth,value,truth*truth,value*truth,value*value]) {*a+=b;}
        }
        chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);
    }}
    let mut recovery=[0.0;3];let mut truth_sd=[0.0;3];
    for c in 0..3 {let [st,sv,tt,tv,_]=sums[c];let variance=(tt-st*st/n).max(0.0);
        truth_sd[c]=(variance/n).sqrt();if variance>1e-12 {recovery[c]=(tv-st*sv/n)/variance;}}
    Score{rgb:(error/(3.0*n)).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),recovery,truth_sd}
}
fn recovery_pass(b:&Score,c:&Score)->bool {(0..3).all(|j|b.recovery[j]<0.5 || c.recovery[j].max(0.0).min(1.0)>=0.9*b.recovery[j].min(1.0))}
fn score_json(s:&Score)->Value {json!({"rgb_rmse":s.rgb,"chroma_rg_bg_rmse":s.chroma,"truth_template_recovery":s.recovery,"truth_template_sd":s.truth_sd})}
fn truth_image(scene:Scene)->Vec<f32> {
    let w=2*crop().width;let h=2*crop().height;
    (0..h).flat_map(|y|(0..w).flat_map(move |x|(0..3).map(move |c|
        radiance(scene,c,(x+2*crop().x) as f64,(y+2*crop().y) as f64,None) as f32))).collect()
}
fn commission()->Value {
    let scene=Scene::TrueRadial;let exact=truth_image(scene);let good=score(scene,&exact,RADIAL);
    assert!(good.rgb<1e-7 && good.chroma<1e-7 && good.recovery.iter().all(|v|(*v-1.0).abs()<1e-5));
    let mut half=exact.clone();let mut excess=exact.clone();let mut grey=exact.clone();
    for ((h,e),g) in half.chunks_exact_mut(3).zip(excess.chunks_exact_mut(3)).zip(grey.chunks_exact_mut(3)) {
        let mean=(g[0]+g[1]+g[2])/3.0;g.fill(mean);
        for c in 0..3 {let base=[0.24,0.26,0.22][c];h[c]=base+0.5*(h[c]-base);e[c]=base+1.4*(e[c]-base);}
    }
    let half=score(scene,&half,RADIAL);let excess=score(scene,&excess,RADIAL);let grey=score(scene,&grey,RADIAL);
    assert!(half.recovery.iter().all(|v|(*v-0.5).abs()<1e-5) && !recovery_pass(&good,&half));
    assert!(excess.recovery.iter().all(|v|(*v-1.4).abs()<1e-5) && recovery_pass(&excess,&good));
    assert!(grey.chroma>0.01 && grey.rgb>0.01,"colour destroyer escaped absolute truth error");
    json!({"exact":score_json(&good),"half_amplitude_destroyer":score_json(&half),
        "neutralized_colour_destroyer":score_json(&grey),"overcontrast_baseline":score_json(&excess),"all_commission_checks_pass":true})
}
fn exact(a:&[Vec<f32>],b:&[Vec<f32>])->bool {a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits()))}

fn worst(a:&[f32],b:&[f32])->f32 {assert_eq!(a.len(),b.len());a.iter().zip(b).map(|(a,b)|{
    assert!(a.is_finite() && b.is_finite());(a-b).abs()}).fold(0.0,f32::max)}
fn write(path:&Path,value:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new()
    .write(true).create_new(true).open(path).unwrap(),value).unwrap();}
fn independent_paths(raw:&super::RawCosts,guide:&[f32])->Vec<f32> {
    let (w,h,n)=(raw.width,raw.height,raw.frames);let mut total=vec![0.0;w*h*n];
    for direction in 0..4 {
        let horizontal=direction<2;let reverse=direction%2==1;
        for line in 0..if horizontal{h}else{w} {
            let length=if horizontal{w}else{h};let mut previous=vec![0.0f32;n];let mut previous_pixel=0;
            for step in 0..length {let t=if reverse{length-1-step}else{step};
                let p=if horizontal{line*w+t}else{t*w+line};let mut current=vec![0.0;n];
                let m=previous.iter().copied().fold(f32::INFINITY,f32::min);
                let edge=(guide[p]-guide[previous_pixel]).abs()/(guide[p].abs()+guide[previous_pixel].abs()+1.0);
                let penalty=0.25/(1.0+(edge/0.05).powi(2));
                for k in 0..n {let d=raw.costs[p*n+k];
                    if step==0 {current[k]=d;}else{
                        let alternative=(0..n).map(|j|previous[j]+if j==k{0.0}else{penalty})
                            .fold(f32::INFINITY,f32::min);
                        current[k]=d+alternative-m;
                    }
                    total[p*n+k]+=current[k];
                }previous=current;previous_pixel=p;
            }
        }
    }
    for (a,d) in total.iter_mut().zip(&raw.costs){*a-=3.0*d;}total
}
fn independent_memberships(raw:&super::RawCosts,a:&[f32])->(Vec<f32>,Vec<f32>) {
    let n=raw.frames;let mut q=vec![0.0;a.len()];let mut alpha=vec![0.0;raw.width*raw.height];
    let h=|x:f32|{let u=x.clamp(0.0,1.0);u*u*(3.0-2.0*u)};
    for p in 0..alpha.len() {let amin=a[p*n..(p+1)*n].iter().copied().fold(f32::INFINITY,f32::min);
        let mut sum=0.0;for k in 0..n {q[p*n+k]=(1.0-(a[p*n+k]-amin)/0.125).max(0.0);sum+=q[p*n+k];}
        alpha[p]=h((raw.rmax[p]-1.0)/3.0)*h((raw.spread[p]-0.125)/0.125);
        for k in 0..n {q[p*n+k]=alpha[p]*(q[p*n+k]/sum);}
    }(q,alpha)
}
fn categorical_controls()->Value {
    let (w,h,n)=(9usize,7usize,3usize);let pixels=w*h;
    let energies=(0..n).map(|k|(0..pixels).map(|p|{
        let x=p%w;let y=p/w;let r=if x==0 {0.5} else if x==4 && y==3 {12.0}
            else {let winner=if y<3 {usize::from(x>5)}else{2};if k==winner {12.0}else{2.0+(k as f32)*0.1}};
        8.0*(r+1.0)
    }).collect::<Vec<_>>()).collect::<Vec<_>>();let floor=vec![8.0;pixels];
    let build=|order:[usize;3]| {let mut v=super::CostVolume::new(w,h,n).unwrap();
        for (k,old) in order.into_iter().enumerate(){v.set_source(k,&energies[old],&floor).unwrap();}v.normalize().unwrap()};
    let raw=build([0,1,2]);let guide=(0..pixels).map(|p|if p%w<6 {900.0+p as f32}else{1800.0+p as f32}).collect::<Vec<_>>();
    let a=super::aggregate_costs(&raw,&guide).unwrap();let expected=independent_paths(&raw,&guide);
    assert!(worst(&a,&expected)<2e-6);assert!(worst(&a,&raw.costs)>0.1,"spatial paths inactive");
    let (q,alpha)=independent_memberships(&raw,&expected);let m=super::memberships(a.clone(),&raw).unwrap();
    assert!(worst(&m.pixel_major_q,&q)<2e-5 && worst(&m.alpha,&alpha)<2e-6);
    let equal=3*w+4;assert_eq!(m.alpha[equal],0.0);assert!((0..h).all(|y|m.alpha[y*w]==0.0));
    assert!(m.alpha.iter().any(|v|*v==1.0));
    let perm=build([2,0,1]);let pa=super::aggregate_costs(&perm,&guide).unwrap();let pm=super::memberships(pa,&perm).unwrap();
    for p in 0..pixels {for (k,old) in [2usize,0,1].into_iter().enumerate(){
        assert!((pm.pixel_major_q[p*n+k]-m.pixel_major_q[p*n+old]).abs()<2e-5);}}
    let mut strong=super::CostVolume::new(1,1,2).unwrap();strong.set_source(0,&[101.0],&[1.0]).unwrap();
    strong.set_source(1,&[1001.0],&[1.0]).unwrap();let strong=strong.normalize().unwrap();
    assert!((strong.costs[0]-0.9).abs()<1e-6 && strong.costs[1]==0.0);
    let old_gap=(1000.0f32/1002.0-100.0/102.0).abs();assert!(old_gap<0.125 && strong.costs[0]>0.125);
    let mut tied=super::CostVolume::new(3,2,3).unwrap();
    for (k,r) in [10.0f32,10.0,0.0].into_iter().enumerate(){tied.set_source(k,&vec![r+1.0;6],&[1.0;6]).unwrap();}
    let tied=tied.normalize().unwrap();let tm=super::memberships(super::aggregate_costs(&tied,&[100.0;6]).unwrap(),&tied).unwrap();
    assert!(tm.alpha.iter().all(|v|*v==1.0));for p in 0..6 {assert_eq!(&tm.pixel_major_q[3*p..3*p+3],&[0.5,0.5,0.0]);}
    for bad in [f32::NAN,f32::INFINITY,-1.0] {let mut v=super::CostVolume::new(1,1,1).unwrap();
        assert!(v.set_source(0,&[bad],&[1.0]).is_err());let mut v=super::CostVolume::new(1,1,1).unwrap();assert!(v.set_source(0,&[1.0],&[bad]).is_err());}
    assert!(super::CostVolume::new(0,2,3).is_err());let mut v=super::CostVolume::new(1,1,2).unwrap();
    assert!(v.set_source(0,&[],&[1.0]).is_err());
    json!({"path_oracle_max_error":worst(&a,&expected),"membership_oracle_max_error":worst(&m.pixel_major_q,&q),
        "local_equal_and_low_evidence_exact_fallback":true,"label_permutation":true,"strong_ratio_separated":true,
        "equal_best_two_plus_bad_third_activates":true,"interpretation":"Arithmetic controls; activation is not ambiguity recognition"})
}
fn replay_controls()->Value {
    use strehl_core::pyramid::Hull;
    let (w,h)=(89usize,73usize);let size=w*h;let sizes=level_sizes(w,h,3);
    let cfg=MergeConfig{bands:3,hull:Hull::InputRange,mean_coarse:0,significance_scale:0.0,..MergeConfig::default()};
    let frames=(0..3).map(|s|(0..4).map(|c|(0..size).map(|i|{
        let x=i%w;let y=i/w;let phase=x as f64*(c+1) as f64/9.0+y as f64*(4-c) as f64/13.0+s as f64*1.4;
        let value=if x==w/2 && y==h/2 {1800.0+140.0*c as f64}else{
            1000.0+600.0*s as f64+140.0*c as f64+(80.0+23.0*c as f64)*phase.sin()+0.75*x as f64+1.2*y as f64};
        f32::from((512.0+value).round() as u16)-512.0
    }).collect::<Vec<_>>()).collect::<Vec<_>>()).collect::<Vec<_>>();let original=frames.clone();
    let mut merge=BandMerge::new(w,h,4,cfg);let mut ws=FrameWorkspace::new(&sizes,4);
    for f in &frames {ws.next_frame();let guide=f[1].iter().zip(&f[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
        merge.add_frame(&f.iter().map(Vec::as_slice).collect::<Vec<_>>(),&guide,&vec![16.0;size],&mut ws);}
    let base=merge.finish(&mut Workspace::new(&sizes));let resolved=resolved_coefficients(&merge);
    let pyramids=frames.iter().map(|f|f.iter().map(|v|{let mut p=Pyramid::zeros(&sizes);
        p.build(v,&mut Workspace::new(&sizes));p}).collect::<Vec<_>>()).collect::<Vec<_>>();
    let ac=|p:&Pyramid|{let mut t=p.clone();t.level_mut(3).fill(0.0);t.collapse(&mut Workspace::new(&sizes))};
    let source_ac=pyramids.iter().map(|f|f.iter().map(ac).collect::<Vec<_>>()).collect::<Vec<_>>();
    let bac=resolved.iter().map(ac).collect::<Vec<_>>();let pre=resolved.iter().map(|p|p.collapse(&mut Workspace::new(&sizes))).collect::<Vec<_>>();
    let shared=resolved.iter().map(|p|{let mut t=Pyramid::zeros(&sizes);t.level_mut(3).copy_from_slice(p.level(3));t.collapse(&mut Workspace::new(&sizes))}).collect::<Vec<_>>();
    for c in 0..4 {let expected=(0..sizes[3].pixels()).map(|i|{let mut v=0.0;for ps in &pyramids {v+=ps[c].level(3)[i];}v*(1.0/3.0)}).collect::<Vec<_>>();
        assert_eq!(expected.iter().map(|v|v.to_bits()).collect::<Vec<_>>(),resolved[c].level(3).iter().map(|v|v.to_bits()).collect::<Vec<_>>());
        assert!(worst(pyramids[0][c].level(3),pyramids[2][c].level(3))>100.0);}
    let clamp=|v:f32,c:usize,i:usize|v.clamp(frames.iter().map(|f|f[c][i]).fold(f32::INFINITY,f32::min),frames.iter().map(|f|f[c][i]).fold(f32::NEG_INFINITY,f32::max));
    let alpha=(0..size).map(|i|if i%w<11 || i/w<7 || i%w>=w-9 || i/w>=h-12 {0.0}else{0.5+0.5*((i%w)%3) as f32/2.0}).collect::<Vec<_>>();
    let mut replay=Replay::new(&sizes,&alpha).unwrap();let mut expected_sum=vec![vec![0.0;size];4];
    for k in 0..3 {let q=alpha.iter().map(|a|a*[0.25,0.5,0.25][k]).collect::<Vec<_>>();replay.add_source(&q,&frames[k]).unwrap();
        for c in 0..4 {for i in 0..size{expected_sum[c][i]+=q[i]*source_ac[k][c][i];}}}
    let output=replay.finish(&merge,&mut Workspace::new(&sizes)).unwrap();let mut error=0.0f32;let mut changed=0;let mut outside=0;
    for c in 0..4 {assert!(worst(&expected_sum[c],&replay.detail_sums()[c])<0.003);for i in 0..size{
        let expected=if alpha[i]==0.0{base[c][i]}else{clamp(pre[c][i]+(expected_sum[c][i]-alpha[i]*bac[c][i]),c,i)};
        error=error.max((output[c][i]-expected).abs());if alpha[i]==0.0{assert_eq!(output[c][i].to_bits(),base[c][i].to_bits());outside+=1;}
        else{changed+=usize::from(output[c][i].to_bits()!=base[c][i].to_bits());}}}
    assert!(error<=0.003 && changed>100 && outside>100);assert!(worst(replay.coverage(),&alpha)<8e-6);
    let zero=Replay::new(&sizes,&vec![0.0;size]).unwrap();assert!(exact(&zero.finish(&merge,&mut Workspace::new(&sizes)).unwrap(),&base));
    let mut all_outputs=Vec::new();let mut ones_error=0.0f32;let mut signs=[0usize;2];let pin=(h/2)*w+w/2;
    for (arm,k) in [0usize,2].into_iter().enumerate(){let mut one=Replay::new(&sizes,&vec![1.0;size]).unwrap();one.add_source(&vec![1.0;size],&frames[k]).unwrap();
        let out=one.finish(&merge,&mut Workspace::new(&sizes)).unwrap();for c in 0..4 {for i in 0..size{
            ones_error=ones_error.max((out[c][i]-clamp(source_ac[k][c][i]+shared[c][i],c,i)).abs());}
            let pin_pre=pre[c][pin]+(source_ac[k][c][pin]-bac[c][pin]);
            if arm==0{assert!(pin_pre-frames[0][c][pin]>100.0);}else{assert!(pin_pre-frames[0][c][pin]< -100.0);}
            assert_eq!(out[c][pin].to_bits(),frames[0][c][pin].to_bits());signs[arm]+=1;
        }all_outputs.push(out);}
    assert!(ones_error<=0.02 && !exact(&all_outputs[0],&all_outputs[1]));assert_eq!(signs,[4,4]);
    assert_eq!(frames,original);assert!(exact(&merge.finish(&mut Workspace::new(&sizes)),&base));
    assert!(Replay::new(&sizes,&vec![f32::NAN;size]).is_err());assert!(Replay::new(&sizes,&vec![-0.1;size]).is_err());
    json!({"actual_replay_max_error_dn":error,"allones_shared_base_error_dn":ones_error,"changed_samples":changed,
        "exact_zero_samples":outside,"clamp_signs":signs,"mean_base_exact":true,"wrong_source_live":true,"inputs_unchanged":true})
}

#[test]
fn independent_shared_source_mechanical() {
    let categorical=categorical_controls();let replay=replay_controls();
    eprintln!("SHARED_SOURCE_MECHANICAL {}",json!({"status":"PASS","categorical":categorical,"replay":replay}));
}

fn checks(c:&Comparison,frames:&[Frame],before:&[String]) {
    assert_eq!((c.native_width,c.native_height),(2*crop().width,2*crop().height));
    assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert_eq!(c.baseline_planes4.len(),4);assert_eq!(c.candidate_planes4.len(),4);
    assert_eq!(c.frames.len(),frames.len());assert_eq!(c.alpha.len(),crop().width*crop().height);
    assert!(c.alpha.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v)));
    assert_eq!(c.pixel_major_q.len(),c.alpha.len()*frames.len());
    for p in 0..c.alpha.len(){let q=&c.pixel_major_q[p*frames.len()..(p+1)*frames.len()];
        assert!(q.iter().all(|v|v.is_finite() && *v>=0.0));assert!((q.iter().sum::<f32>()-c.alpha[p]).abs()<=8e-6);
        if c.alpha[p]==0.0 {for ch in 0..4 {assert_eq!(c.candidate_planes4[ch][p].to_bits(),c.baseline_planes4[ch][p].to_bits());}}}
    for ((frame,old),e) in frames.iter().zip(before).zip(&c.frames){
        assert_eq!(&hash(&frame.data),old);assert_eq!(&e.source_sha256,old);assert!(e.source_unchanged && e.replay_known4_exact);
        assert!(!e.beta.is_empty() && e.beta.iter().all(|v|v.is_finite() && *v>0.0));
    }
}
fn evidence(c:&Comparison)->Value {
    json!({"alpha_positive":c.alpha.iter().filter(|v|**v>0.0).count(),"alpha_one":c.alpha.iter().filter(|v|**v==1.0).count(),
        "alpha_zero":c.alpha.iter().filter(|v|**v==0.0).count(),"level_sizes":c.level_sizes,
        "baseline_averaged_fraction":c.baseline_averaged_fraction,
        "source_evidence":c.frames.iter().map(|f|json!({"source_sha256":f.source_sha256,
            "guide_sha256":f.guide_sha256,"variance_sha256":f.variance_sha256,"beta":f.beta})).collect::<Vec<_>>()})
}

#[test]
fn independent_shared_source_quality_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_SHARED_SOURCE_FIELD_OUT").expect("root-owned unique output required"));
    std::fs::create_dir(&out).unwrap();let commissioned=commission();let ts=transforms();
    let mut cases=Vec::new();let mut decisions=Vec::new();let mut wrong_source_exercised=false;
    for iso in [100.0f32,400.0] {
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let mut flat_error=0.0;let mut iso_pass=true;let mut iso_exercised=true;
        for scene in [Scene::Flat,Scene::GlintDepth,Scene::TrueRadial,Scene::ThinDepth] {
            let frames=ts.iter().enumerate().map(|(k,t)|fixture(scene,k,*t,iso,&noise)).collect::<Vec<_>>();
            let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::SharedPotts).unwrap();checks(&c,&frames,&before);
            let regions:&[Window]=match scene {Scene::Flat=>&[FLAT],Scene::GlintDepth=>&[FAN,CORE,EDGE,NEAR],
                Scene::TrueRadial=>&[RADIAL],Scene::ThinDepth=>&[THIN_FAR,THIN_NEAR,JUNCTION],_=>unreachable!()};
            let mut windows=Vec::new();let mut pass=true;let mut exercised=true;
            for &window in regions {
                let b=score(scene,&c.baseline_rgb,window);let a=score(scene,&c.candidate_rgb,window);
                let mut bar=if scene==Scene::Flat {flat_error=b.rgb;a.rgb<=1.25*b.rgb && a.chroma<=1.25*b.chroma}
                    else {a.rgb<=1.10*b.rgb && recovery_pass(&b,&a)};
                if window.name=="fan" {bar&=a.rgb<=0.95*b.rgb;exercised&=b.rgb>2.0*flat_error;}
                if window.name=="real-coloured-rays"{bar&=a.chroma<=1.10*b.chroma;}
                if matches!(window.name,"nearer-real-texture"|"real-coloured-rays"|"thin-far"|"thin-near") {
                    exercised&=b.recovery.iter().all(|v|*v>=0.5);
                }
                pass&=bar;windows.push(json!({"name":window.name,"active_native_bounds":[window.x0,window.y0,window.x1,window.y1],
                    "baseline":score_json(&b),"candidate":score_json(&a),"rgb_ratio":a.rgb/b.rgb,
                    "chroma_ratio":a.chroma/b.chroma,"quality_pass":bar}));
            }
            let mut placebo=Value::Null;
            if scene!=Scene::Flat {exercised&=c.alpha.iter().any(|v|*v>0.0) && !exact(&c.baseline_planes4,&c.candidate_planes4);
                exercised&=c.frames.windows(2).any(|e|e[0].guide_sha256!=e[1].guide_sha256);}
            if scene==Scene::GlintDepth {
                let mut e=0.0;let mut count=0;for y in FAN.y0..FAN.y1{for x in FAN.x0..FAN.x1{for ch in 0..3{
                    e+=(radiance(scene,ch,x as f64,y as f64,Some(4))-radiance(scene,ch,x as f64,y as f64,None)).powi(2);count+=1;
                }}}
                let wrong_fan_rms=(e/count as f64).sqrt();exercised&=wrong_fan_rms>2.0*flat_error;
                if iso==100.0 {
                    let off=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Off).unwrap();checks(&off,&frames,&before);
                    assert!(exact(&off.baseline_planes4,&off.candidate_planes4) && exact(&off.baseline_planes4,&c.baseline_planes4));
                    let wrong=compare_generated_forced(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::SharedPotts,4).unwrap();checks(&wrong,&frames,&before);
                    assert!(exact(&wrong.baseline_planes4,&c.baseline_planes4));
                    let bfan=score(scene,&c.baseline_rgb,FAN);let wfan=score(scene,&wrong.candidate_rgb,FAN);
                    let bcore=score(scene,&c.baseline_rgb,CORE);let wcore=score(scene,&wrong.candidate_rgb,CORE);
                    wrong_source_exercised=!exact(&wrong.candidate_planes4,&c.candidate_planes4)
                        && (wfan.rgb>1.10*bfan.rgb || !recovery_pass(&bcore,&wcore));
                    placebo=json!({"off_exact":true,"forced_last_source":4,"forced_fan":score_json(&wfan),
                        "forced_core":score_json(&wcore),"wrong_source_destroyer_exercised":wrong_source_exercised,
                        "unmerged_wrong_fan_truth_rmse":wrong_fan_rms});
                }else{placebo=json!({"unmerged_wrong_fan_truth_rmse":wrong_fan_rms});}
            }
            iso_pass&=pass;iso_exercised&=exercised;
            let record=json!({"scene":scene.name(),"iso":iso,"sources":N,"warp":"fixed fractional similarity",
                "quality_pass":pass,"fixture_exercised":exercised,"windows":windows,"consumer":evidence(&c),"placebo":placebo});
            eprintln!("SHARED_SOURCE_CASE {}",record);cases.push(record);
        }
        decisions.push(json!({"iso":iso,"quality_pass":iso_pass,"fixtures_exercised":iso_exercised,"admitted":iso_pass && iso_exercised}));
    }
    let iso=100.0;let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());let identity=Similarity{a:Cx::new(1.0,0.0),b:Cx::new(0.0,0.0)};
    let ts70=vec![identity;70];let frames=(0..70).map(|k|fixture(Scene::Flat,k,identity,iso,&noise)).collect::<Vec<_>>();
    let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
    let c=compare_generated(&frames,&ts70,crop(),&noise,MergeConfig::default(),Mode::SharedPotts).unwrap();checks(&c,&frames,&before);
    let b=score(Scene::Flat,&c.baseline_rgb,FLAT);let a=score(Scene::Flat,&c.candidate_rgb,FLAT);
    let flat70_pass=a.rgb<=1.25*b.rgb && a.chroma<=1.25*b.chroma;
    let flat70=json!({"scene":"flat70","iso":iso,"sources":70,"warp":"identity","quality_pass":flat70_pass,
        "baseline":score_json(&b),"candidate":score_json(&a),"rgb_ratio":a.rgb/b.rgb,"chroma_ratio":a.chroma/b.chroma,"consumer":evidence(&c)});
    eprintln!("SHARED_SOURCE_CASE {}",flat70);cases.push(flat70);drop(c);drop(frames);
    let mut fallbacks=Vec::new();
    for scene in [Scene::Flat,Scene::ColourOnly] {
        let frames=(0..N).map(|k|fixture_noise(scene,k,identity,iso,&noise,false)).collect::<Vec<_>>();
        let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
        let c=compare_generated(&frames,&vec![identity;N],crop(),&noise,MergeConfig::default(),Mode::SharedPotts).unwrap();checks(&c,&frames,&before);
        assert!(c.alpha.iter().all(|v|*v==0.0),"constant green unexpectedly activated");
        assert!(exact(&c.baseline_planes4,&c.candidate_planes4));assert!(c.baseline_rgb.iter().zip(&c.candidate_rgb).all(|(a,b)|a.to_bits()==b.to_bits()));
        if scene==Scene::ColourOnly {
            assert!(score(scene,&c.baseline_rgb,FLAT).recovery[0]>0.1,"fallback colour structure not exercised");
        }else{for ch in 0..3 {let values=c.baseline_rgb.chunks_exact(3).map(|v|v[ch]).collect::<Vec<_>>();
            let span=values.iter().copied().fold(f32::NEG_INFINITY,f32::max)-values.iter().copied().fold(f32::INFINITY,f32::min);assert!(span<1e-6);}}
        fallbacks.push(json!({"scene":scene.name(),"literal_alpha_zero":true,"baseline_planes_and_rgb_exact":true,"consumer":evidence(&c)}));
    }
    let admitted=decisions.iter().all(|v|v["admitted"]==true) && flat70_pass && wrong_source_exercised;
    let result=json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admitted,"iso_decisions":decisions,
        "flat70_pass":flat70_pass,"wrong_source_destroyer_exercised":wrong_source_exercised,"metric_commission":commissioned,
        "fallback_placebos":fallbacks,"cases":cases,
        "interpretation":"Fixed categorical source-field plus full-AC replay only. Arithmetic pass is not quality admission. No calibration, ownership, photographic or SOTA claim."});
    write(&out.join("screen.json"),&result);eprintln!("SHARED_SOURCE_DECISION {}",json!({"photographic_replay_admitted":admitted}));
}
