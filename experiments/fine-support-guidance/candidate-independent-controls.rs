// Independent fixed scene screen; root executes, author does not verify.
use super::{compare_generated, Comparison};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},
    profile,pyramid::{MergeConfig,fine_support_candidate::Mode}};
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
enum Scene {Flat,GlintDepth,TrueRadial}
impl Scene {fn name(self)->&'static str {match self {Self::Flat=>"flat",Self::GlintDepth=>"glint-depth-step",Self::TrueRadial=>"true-coloured-radial"}}}

// Continuous Gaussian shapes conserve integral as their covariance changes.
// They are adversarial PSFs, not a fitted model of the user's optical train.
fn elliptical(x:f64,y:f64,angle:f64,sx:f64,sy:f64)->f64 {
    let (s,c)=angle.sin_cos();let u=c*x+s*y;let v=-s*x+c*y;
    (-0.5*((u/sx).powi(2)+(v/sy).powi(2))).exp()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->f64 {
    match scene {
        Scene::Flat=>0.25,
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
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,
        levels:levels(),iso:Some(iso),wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],
        xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),
        path:std::env::current_dir().unwrap().join(format!("nonexistent-independent-fine-{}-{k}.ARW",scene.name()))};
    assert!(!f.path.exists());let determinant=t.a.re*t.a.re+t.a.im*t.a.im;
    for y in 0..H {for x in 0..W {
        // Explicit inverse of the native pull; no interpolated source image.
        let u=x as f64-W as f64/2.0-2.0*t.b.re;let v=y as f64-H as f64/2.0-2.0*t.b.im;
        let wx=W as f64/2.0+(t.a.re*u+t.a.im*v)/determinant;
        let wy=H as f64/2.0+(-t.a.im*u+t.a.re*v)/determinant;
        let signal=(radiance(scene,channel(x,y),wx,wy,Some(k))*f64::from(levels().range())/f64::from(GAIN[channel(x,y)])) as f32;
        let value=512.0+f64::from(signal)+gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal));
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
fn checks(c:&Comparison,frames:&[Frame],original:&[String]) {
    assert_eq!((c.native_width,c.native_height),(2*crop().width,2*crop().height));
    assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert!(c.non_finest_bit_exact,"candidate changed higher-band or base accumulation");
    assert_eq!(c.baseline_planes4.len(),4);assert_eq!(c.candidate_planes4.len(),4);
    assert_eq!(c.frames.len(),frames.len());
    for ((f,h),e) in frames.iter().zip(original).zip(&c.frames) {
        assert_eq!(&hash(&f.data),h,"source u16 storage changed");assert_eq!(&e.source_sha256,h);
        assert!(!e.beta.is_empty() && e.beta.len()<=c.level_sizes.len());
        assert!(e.beta.iter().all(|v|v.is_finite() && *v>0.0));
    }
}
fn write(path:&Path,value:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}

#[test]
fn independent_finest_support_quality_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_FINE_SUPPORT_CANDIDATE_OUT").expect("root-owned unique output required"));
    std::fs::create_dir(&out).unwrap();let commissioned=commission();
    let mut cases=Vec::new();let mut iso_decisions=Vec::new();let ts=transforms();
    for iso in [100.0f32,400.0] {
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());
        assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let mut flat_baseline=0.0;let mut all_pass=true;let mut all_exercised=true;
        for scene in [Scene::Flat,Scene::GlintDepth,Scene::TrueRadial] {
            let frames=ts.iter().enumerate().map(|(k,t)|fixture(scene,k,*t,iso,&noise)).collect::<Vec<_>>();
            let original=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Radius32).unwrap();
            checks(&c,&frames,&original);
            let mut windows=Vec::new();let mut quality_pass=true;let mut exercised=true;
            let regions:&[Window]=match scene {Scene::Flat=>&[FLAT],Scene::GlintDepth=>&[FAN,CORE,EDGE,NEAR],Scene::TrueRadial=>&[RADIAL]};
            for &window in regions {
                let b=score(scene,&c.baseline_rgb,window);let a=score(scene,&c.candidate_rgb,window);
                let pass=match window.name {
                    "flat-interior"=>{flat_baseline=b.rgb;a.rgb<=1.25*b.rgb && a.chroma<=1.25*b.chroma},
                    "fan"=>{exercised&=b.rgb>2.0*flat_baseline;a.rgb<=0.95*b.rgb},
                    "depth-boundary"=>a.rgb<=1.10*b.rgb,
                    "nearer-real-texture"=>{exercised&=b.recovery.iter().all(|v|*v>=0.5);recovery_pass(&b,&a)},
                    "real-coloured-rays"=>{exercised&=b.recovery.iter().all(|v|*v>=0.5);recovery_pass(&b,&a) && a.rgb<=1.10*b.rgb && a.chroma<=1.10*b.chroma},
                    _=>recovery_pass(&b,&a),
                };
                quality_pass&=pass;
                windows.push(json!({"name":window.name,"active_native_bounds":[window.x0,window.y0,window.x1,window.y1],
                    "baseline":score_json(&b),"candidate":score_json(&a),"rgb_ratio":a.rgb/b.rgb,"chroma_ratio":a.chroma/b.chroma,"quality_pass":pass}));
            }
            let mut off_exact=None;let mut fan_input_energy=None;
            if scene==Scene::GlintDepth {
                let off=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Off).unwrap();checks(&off,&frames,&original);
                assert!(exact(&off.baseline_planes4,&off.candidate_planes4),"disabled mode differs from actual baseline");
                assert!(exact(&off.baseline_planes4,&c.baseline_planes4),"baseline differs between paired calls");off_exact=Some(true);
                assert!(!exact(&c.baseline_planes4,&c.candidate_planes4),"active candidate was never exercised");
                assert!(c.frames.windows(2).any(|v|v[0].guide_sha256!=v[1].guide_sha256),"different depths supplied identical actual guides");
                exercised&=c.baseline_averaged_fraction[0]<1.0 && c.candidate_averaged_fraction[0]<1.0;
                let mut e=0.0;let mut n=0;
                for y in FAN.y0..FAN.y1 {for x in FAN.x0..FAN.x1 {for ch in 0..3 {
                    e+=(radiance(scene,ch,x as f64,y as f64,Some(4))-radiance(scene,ch,x as f64,y as f64,None)).powi(2);n+=1;
                }}}
                let rms=(e/n as f64).sqrt();exercised&=rms>2.0*flat_baseline;fan_input_energy=Some(rms);
            }
            all_pass&=quality_pass;all_exercised&=exercised;
            let record=json!({"scene":scene.name(),"iso":iso,"quality_pass":quality_pass,"fixture_exercised":exercised,
                "non_finest_accumulators_bit_exact":c.non_finest_bit_exact,"disabled_exact":off_exact,
                "unmerged_defocused_fan_truth_rmse":fan_input_energy,"baseline_averaged_fraction":c.baseline_averaged_fraction,
                "candidate_averaged_fraction":c.candidate_averaged_fraction,"source_hashes":original,"windows":windows});
            eprintln!("FINE_CANDIDATE_CASE {}",record);cases.push(record);
        }
        iso_decisions.push(json!({"iso":iso,"quality_pass":all_pass,"fixtures_exercised":all_exercised,"admitted":all_pass && all_exercised}));
    }
    let admitted=iso_decisions.iter().all(|v|v["admitted"]==true);
    let result=json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admitted,"iso_decisions":iso_decisions,
        "metric_commission":commissioned,"cases":cases,
        "interpretation":"Only band0 support pooling tested. Structural pass is not quality acceptance; an unexercised fixture refuses admission. No calibration, photographic or SOTA claim."});
    write(&out.join("screen.json"),&result);eprintln!("FINE_CANDIDATE_DECISION {}",json!({"photographic_replay_admitted":admitted}));
}

#[test]
fn independent_finest_support_weight_hook() {
    use strehl_core::pyramid::{LevelSize,fine_support_candidate::weights_from_fields};
    let size=LevelSize{width:129,height:97};let beta=0.875f32;let gate=2.0f32;
    let variance=(0..size.pixels()).map(|i|8.0+((i*7)%31) as f32).collect::<Vec<_>>();
    let energy=(0..size.pixels()).map(|i|if i%size.width<61 {8.0} else {128.0+((i*11)%47) as f32}).collect::<Vec<_>>();
    let floor=variance.iter().map(|v|gate*beta*v).collect::<Vec<_>>();
    let weights=weights_from_fields(&energy,&variance,size,beta,gate,1.0);
    let direct=|a:&[f32],x:usize,y:usize| {
        let mut sum=0.0f64;let mut count=0;
        for yy in y.saturating_sub(32)..=(y+32).min(size.height-1) {
            for xx in x.saturating_sub(32)..=(x+32).min(size.width-1) {sum+=f64::from(a[yy*size.width+xx]);count+=1;}
        }(sum/count as f64) as f32
    };
    let mut zeros=0;let mut positive=0;
    for (x,y) in [(0,0),(32,48),(60,48),(64,48),(97,65),(128,96)] {
        let e=direct(&energy,x,y);let f=direct(&floor,x,y);let expected=(e-f).max(0.0)/f.max(1.0)/64.0;
        let actual=weights[y*size.width+x];assert!((actual-expected).abs()<=2e-6*expected.abs().max(1e-4));
        if expected==0.0 {zeros+=1;} else {positive+=1;}
    }
    assert!(zeros>0 && positive>0,"hook control never exercised both admission states");
    let flat=weights_from_fields(&vec![0.0;size.pixels()],&variance,size,beta,gate,8.0);
    assert!(flat.iter().all(|v|*v==0.0));
    assert!(Mode::parse("radius32").unwrap()==Mode::Radius32 && Mode::parse("off").unwrap()==Mode::Off);
    assert!(Mode::parse("radius16").is_err());
    eprintln!("FINE_CANDIDATE_HOOK direct_box_weights=6, zero_and_positive_admission=true, flat_zero=true");
}
