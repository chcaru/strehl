// Independent retained u16 fixture family, extended before this screen runs.
// Root executes. The numerical operator author does not verify these controls.
use super::{compare_generated,compare_generated_forced,Comparison,Mode,AgreementSum,core};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},
    profile,pyramid::{MergeConfig,LevelSize}};
use strehl_raw::{Frame,Region};
const W:usize=320;const H:usize=288;const N:usize=5;
const GAIN:[f32;3]=[1.7,1.0,2.3];
fn crop()->align_cmd::CropRect {align_cmd::CropRect{x:7,y:9,width:145,height:125}}
fn levels()->Levels {Levels{black:512.0,white:15360.0}}
fn channel(x:usize,y:usize)->usize {match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane {match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn hash(v:&[u16])->String {let mut h=Sha256::new();for x in v {h.update(x.to_le_bytes());}h.finalize().iter().map(|v|format!("{v:02x}")).collect()}
fn scramble(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64 {
    let s=(x as u32)^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x31d59a67;
    let u=(scramble(s) as f64+0.5)/4294967296.0;
    let v=(scramble(s^0xa73126bd) as f64+0.5)/4294967296.0;
    (-2.0*u.ln()).sqrt()*(TAU*v).cos()
}
#[derive(Clone,Copy,Debug,PartialEq)]
enum Scene {Flat,Contact,GlintNeutral,GlintColour,NearFar,Radial}
impl Scene {fn name(self)->&'static str {match self {
    Self::Flat=>"flat",Self::Contact=>"broad-bright-contact",Self::GlintNeutral=>"neutral-glint-depth",
    Self::GlintColour=>"chromatic-glint-depth",Self::NearFar=>"near-fine-far-coarse",Self::Radial=>"true-coloured-thin-rays"}}}
fn elliptical(x:f64,y:f64,angle:f64,sx:f64,sy:f64)->f64 {
    let(s,c)=angle.sin_cos();(-0.5*(((c*x+s*y)/sx).powi(2)+((-s*x+c*y)/sy).powi(2))).exp()
}
// Fixed analytic normal-CDF approximation, absolute error <8e-8. No sampled
// source image is interpolated by the fixture; only the consumer gathers it.
fn cdf(z:f64)->f64 {
    let x=z.abs();let t=1.0/(1.0+0.2316419*x);
    let p=1.0-(-0.5*x*x).exp()/TAU.sqrt()*t*(0.319381530+t*(-0.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))));
    if z>=0.0 {p} else {1.0-p}
}
fn component(which:usize,c:usize,x:f64,y:f64,k:Option<usize>)->f64 {
    let focus=if which==0 {0.0}else{4.0};
    let sigma=0.65+3.0*k.map_or(0.0,|j|(j as f64-focus).abs());
    let (f,amplitude)=if which==0 {(0.10,[0.045,0.050,0.040][c])}else{(0.022,[0.090,0.100,0.085][c])};
    let (dx,dy,phase)=if which==0 {[(1.0,0.0,0.37),(0.8,0.6,1.13),(-0.6,0.8,2.07)][c]}
        else {[(0.0,1.0,0.81),(0.6,-0.8,1.71),(0.8,0.6,2.63)][c]};
    amplitude*(-0.5*(TAU*f*sigma).powi(2)).exp()*(TAU*f*(dx*x+dy*y)+phase).cos()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->f64 {
    match scene {
        Scene::Flat=>0.25,
        Scene::NearFar=>0.27+component(0,c,x,y,k)+component(1,c,x,y,k),
        Scene::Contact=>{
            let sigma=0.65+3.2*k.map_or(0.0,|j|j as f64);
            let box_value=(cdf((x-108.0)/sigma)-cdf((x-140.0)/sigma))
                *(cdf((y-116.0)/sigma)-cdf((y-164.0)/sigma));
            let (dx,dy,phase)=[(1.0,0.0,0.37),(0.8,0.6,1.13),(-0.6,0.8,2.07)][c];
            0.18+[0.36,0.40,0.32][c]*box_value+[0.045,0.055,0.050][c]
                *(-0.5*(TAU*0.075*sigma).powi(2)).exp()*(TAU*0.075*(dx*x+dy*y)+phase).cos()
        },
        Scene::Radial=>{
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-3.0).abs());
            let sx=(24.0f64.powi(2)+sigma*sigma).sqrt();let sy=(1.6f64.powi(2)+sigma*sigma).sqrt();
            [0.24,0.26,0.22][c]+0.14*24.0*1.6/(sx*sy)*elliptical(x-148.0,y-138.0,[0.0,TAU/6.0,TAU/3.0][c],sx,sy)
        },
        Scene::GlintNeutral|Scene::GlintColour=>{
            let d=k.map_or(0.0,|j|j as f64);let sx=3.0+8.0*d;let sy=3.0+0.15*d;
            let (peak,angle)=if scene==Scene::GlintNeutral {(0.52,0.70)}else{([0.50,0.52,0.48][c],[0.48,0.70,0.92][c])};
            let glint=peak*9.0/(sx*sy)*elliptical(x-122.0,y-120.0,angle,sx,sy);
            let far=[0.16,0.17,0.19][c]+glint+0.01*(-0.5*(TAU*0.02*(0.65+1.1*d)).powi(2)).exp()
                *(TAU*0.02*(0.8*x+0.6*y)+0.37).cos();
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-4.0).abs());let r=(3.0*sigma).ceil() as i32;
            let(mut sum,mut coverage,mut premult)=(0.0,0.0,0.0);
            let(dx,dy,phase)=[(0.8,0.6,0.37),(1.0,0.0,1.13),(-0.6,0.8,2.07)][c];
            let ay=(-0.5*(TAU*0.14*dy*sigma).powi(2)).exp();
            for offset in -r..=r {let ww=(-0.5*(offset as f64/sigma).powi(2)).exp();sum+=ww;let xx=x+offset as f64;
                if xx>=176.0 {coverage+=ww;premult+=ww*([0.24,0.26,0.30][c]+[0.065,0.075,0.055][c]
                    *ay*(TAU*0.14*(dx*xx+dy*y)+phase).cos());}}
            premult/sum+(1.0-coverage/sum)*far
        }
    }
}
fn transforms()->Vec<Similarity> {
    let shifts=[(-0.46,0.32),(0.37,-0.21),(0.0,0.0),(0.23,0.44),(-0.18,-0.39)];
    (0..N).map(|k|{let j=k as f64-2.0;Similarity{a:Cx::new(1.0+0.0008*j,0.0004*j),b:Cx::new(shifts[k].0/2.0,shifts[k].1/2.0)}}).collect()
}
fn fixture(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,levels:levels(),iso:Some(iso),
        wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-band-agreement-{}-{k}.ARW",scene.name()))};
    assert!(!f.path.exists());let determinant=t.a.re*t.a.re+t.a.im*t.a.im;
    for y in 0..H {for x in 0..W {
        let u=x as f64-W as f64/2.0-2.0*t.b.re;let v=y as f64-H as f64/2.0-2.0*t.b.im;
        let wx=W as f64/2.0+(t.a.re*u+t.a.im*v)/determinant;let wy=H as f64/2.0+(-t.a.im*u+t.a.re*v)/determinant;
        let signal=(radiance(scene,channel(x,y),wx,wy,Some(k))*f64::from(levels().range())/f64::from(GAIN[channel(x,y)])) as f32;
        let dn=512.0+f64::from(signal)+gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal));
        assert!(dn>512.0 && dn<15360.0,"generated sample clipped");f.data[(active.y+y)*stride+active.x+x]=dn.round() as u16;
    }}f
}
#[derive(Clone,Copy)]
struct Window {name:&'static str,x0:usize,y0:usize,x1:usize,y1:usize,protect:bool}
const WHOLE:Window=Window{name:"whole-supported-interior",x0:38,y0:42,x1:280,y1:244,protect:false};
const SPILL:Window=Window{name:"contact-outside-spill",x0:142,y0:118,x1:164,y1:162,protect:false};
const CONTACT:Window=Window{name:"contact-interior",x0:112,y0:120,x1:136,y1:160,protect:true};
const CONTACT_EDGE:Window=Window{name:"contact-edge",x0:92,y0:100,x1:158,y1:180,protect:false};
const FAN:Window=Window{name:"glint-extension",x0:138,y0:126,x1:170,y1:152,protect:false};
const CORE:Window=Window{name:"glint-core",x0:112,y0:110,x1:133,y1:132,protect:true};
const EDGE:Window=Window{name:"depth-boundary",x0:160,y0:80,x1:192,y1:208,protect:false};
const NEAR:Window=Window{name:"near-real-texture",x0:180,y0:96,x1:224,y1:192,protect:true};
const RADIAL:Window=Window{name:"genuine-thin-radial",x0:84,y0:72,x1:232,y1:216,protect:true};
#[derive(Clone)]
struct Score {rgb:f64,chroma:f64,recovery:[f64;3],truth_sd:[f64;3],bias:[f64;3]}
fn pixel(x:usize,y:usize)->usize {((y-2*crop().y)*2*crop().width+x-2*crop().x)*3}
fn score(scene:Scene,rgb:&[f32],window:Window)->Score {
    assert_eq!(rgb.len(),2*crop().width*2*crop().height*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let(mut error,mut chroma)=(0.0,0.0);let mut sums=[[0.0;4];3];let mut bias=[0.0;3];
    let n=((window.x1-window.x0)*(window.y1-window.y0)) as f64;
    for y in window.y0..window.y1 {for x in window.x0..window.x1 {let mut e=[0.0;3];
        for c in 0..3 {let truth=radiance(scene,c,x as f64,y as f64,None);let value=f64::from(rgb[pixel(x,y)+c]);
            e[c]=value-truth;error+=e[c]*e[c];bias[c]+=e[c];
            for(a,b)in sums[c].iter_mut().zip([truth,value,truth*truth,value*truth]){*a+=b;}}
        chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);
    }}
    let mut recovery=[0.0;3];let mut truth_sd=[0.0;3];
    for c in 0..3 {let[st,sv,tt,tv]=sums[c];let variance=(tt-st*st/n).max(0.0);truth_sd[c]=(variance/n).sqrt();
        if variance>1e-12 {recovery[c]=(tv-st*sv/n)/variance;}bias[c]/=n;}
    Score{rgb:(error/(3.0*n)).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),recovery,truth_sd,bias}
}
fn retained(b:f64,c:f64)->bool {c.clamp(0.0,1.0)>=0.98*b.clamp(0.0,1.0)}
fn protected(b:&Score,c:&Score)->bool {(0..3).all(|j|retained(b.recovery[j],c.recovery[j]))}
fn live(s:&Score)->bool {(0..3).all(|j|s.recovery[j]>=0.5 && s.truth_sd[j]>1e-4)}
fn no_harm(b:&Score,c:&Score)->bool {c.rgb<=1.05*b.rgb && c.chroma<=1.05*b.chroma}
fn sj(s:&Score)->Value {json!({"rgb_rmse":s.rgb,"chroma_rg_bg_rmse":s.chroma,"template_recovery":s.recovery,"truth_sd":s.truth_sd,"signed_rgb_bias":s.bias})}
fn truth_image(scene:Scene)->Vec<f32> {
    (0..2*crop().height).flat_map(|y|(0..2*crop().width).flat_map(move|x|(0..3).map(move|c|
        radiance(scene,c,(x+2*crop().x)as f64,(y+2*crop().y)as f64,None)as f32))).collect()
}
// Joint centred regression against two independently defined true components.
// Off-diagonal covariance is retained, so finite-window leakage cannot make one
// component's loss look like retention of the other.
fn two_components(rgb:&[f32])->[[f64;3];2] {
    let mut answer=[[0.0;3];2];let n=((WHOLE.x1-WHOLE.x0)*(WHOLE.y1-WHOLE.y0))as f64;
    for c in 0..3 {let mut s=[0.0;8];
        for y in WHOLE.y0..WHOLE.y1 {for x in WHOLE.x0..WHOLE.x1 {
            let a=component(0,c,x as f64,y as f64,None);let b=component(1,c,x as f64,y as f64,None);let v=f64::from(rgb[pixel(x,y)+c]);
            for(p,q)in s.iter_mut().zip([a,b,v,a*a,b*b,a*b,a*v,b*v]){*p+=q;}
        }}
        let aa=s[3]-s[0]*s[0]/n;let bb=s[4]-s[1]*s[1]/n;let ab=s[5]-s[0]*s[1]/n;
        let av=s[6]-s[0]*s[2]/n;let bv=s[7]-s[1]*s[2]/n;let det=aa*bb-ab*ab;
        assert!(det>0.1*aa*bb && aa>1e-4 && bb>1e-4,"component templates are not independent/live");
        answer[0][c]=(av*bb-bv*ab)/det;answer[1][c]=(bv*aa-av*ab)/det;
    }answer
}
fn commission()->Value {
    let scene=Scene::Radial;let truth=truth_image(scene);let good=score(scene,&truth,RADIAL);
    assert!(good.rgb<1e-7 && good.chroma<1e-7 && live(&good));
    let(mut half,mut over,mut grey)=(truth.clone(),truth.clone(),truth.clone());
    for((h,o),g)in half.chunks_exact_mut(3).zip(over.chunks_exact_mut(3)).zip(grey.chunks_exact_mut(3)) {
        let m=(g[0]+g[1]+g[2])/3.0;g.fill(m);
        for c in 0..3 {let base=[0.24,0.26,0.22][c];h[c]=base+0.5*(h[c]-base);o[c]=base+1.4*(o[c]-base);}}
    let h=score(scene,&half,RADIAL);let o=score(scene,&over,RADIAL);let g=score(scene,&grey,RADIAL);
    assert!(!protected(&good,&h) && protected(&o,&good));assert!(g.chroma>0.01 && !no_harm(&good,&g));
    let exact=truth_image(Scene::NearFar);let coefficients=two_components(&exact);
    assert!(coefficients.iter().flatten().all(|v|(*v-1.0).abs()<1e-5));
    let mut half_far=exact.clone();for y in 2*crop().y..2*(crop().y+crop().height) {for x in 2*crop().x..2*(crop().x+crop().width) {
        for c in 0..3 {half_far[pixel(x,y)+c]-=(0.5*component(1,c,x as f64,y as f64,None))as f32;}}}
    let half_components=two_components(&half_far);
    assert!(half_components[0].iter().all(|v|(*v-1.0).abs()<1e-5));
    assert!(half_components[1].iter().all(|v|(*v-0.5).abs()<1e-5 && !retained(1.0,*v)));
    json!({"exact_radial":sj(&good),"half_radial":sj(&h),"neutralized_colour":sj(&g),"overcontrast":sj(&o),
        "joint_exact":coefficients,"joint_half_far":half_components,"passed":true})
}
fn exact(a:&[Vec<f32>],b:&[Vec<f32>])->bool {a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.len()==b.len() && a.iter().zip(b).all(|(x,y)|x.to_bits()==y.to_bits()))}
fn checks(c:&Comparison,frames:&[Frame],original:&[String]) {
    assert_eq!((c.native_width,c.native_height),(290,250));assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert!(c.held_state_bit_exact);assert_eq!(c.frames.len(),N);
    for((f,h),e)in frames.iter().zip(original).zip(&c.frames) {
        assert_eq!(&hash(&f.data),h);assert_eq!(&e.source_sha256,h);assert!(e.source_unchanged && e.replay_exact);
        assert_eq!(e.canonical_weight_sha256[0],e.candidate_weight_sha256[0]);assert_eq!(e.changes.changed[0],0);
        assert!(!e.beta.is_empty() && e.beta.iter().all(|v|v.is_finite() && *v>0.0));
    }
}
fn changed(c:&Comparison)->usize {c.frames.iter().map(|e|e.changes.changed.iter().skip(1).sum::<usize>()).sum()}
fn write(path:&Path,value:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}

#[test]
fn independent_quality_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_BAND_SOURCE_AGREEMENT_OUT").expect("root-owned output required"));
    std::fs::create_dir(&out).unwrap();let commissioned=commission();let ts=transforms();let mut cases=Vec::new();let mut decisions=Vec::new();
    for iso in [100.0f32,400.0] {
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let(mut flat_rms,mut iso_quality,mut iso_exercised,mut iso_safety)=(0.0,true,true,true);
        for scene in [Scene::Flat,Scene::Contact,Scene::GlintNeutral,Scene::GlintColour,Scene::NearFar,Scene::Radial] {
            let frames=ts.iter().enumerate().map(|(k,t)|fixture(scene,k,*t,iso,&noise)).collect::<Vec<_>>();let original=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Agreement).unwrap();checks(&c,&frames,&original);
            let regions:&[Window]=match scene {Scene::Flat=>&[WHOLE],Scene::Contact=>&[SPILL,CONTACT,CONTACT_EDGE,WHOLE],
                Scene::GlintNeutral|Scene::GlintColour=>&[FAN,CORE,EDGE,NEAR,WHOLE],Scene::NearFar=>&[WHOLE],Scene::Radial=>&[RADIAL,WHOLE]};
            let(mut quality,mut exercised,mut safety)=(true,true,true);let mut windows=Vec::new();
            for &window in regions {
                let b=score(scene,&c.baseline_rgb,window);let a=score(scene,&c.candidate_rgb,window);
                let mut pass=no_harm(&b,&a);if scene==Scene::Flat {flat_rms=b.rgb;}
                if window.protect {exercised&=live(&b);pass&=protected(&b,&a);safety&=live(&b);}
                safety&=pass; // Preserve no-harm separately from the old positive spill requirement below.
                let mut input_rms=None;
                if window.name==SPILL.name {
                    let(mut sum,mut count)=(0.0,0);for y in window.y0..window.y1 {for x in window.x0..window.x1 {for ch in 0..3 {
                        sum+=(radiance(scene,ch,x as f64,y as f64,Some(4))-radiance(scene,ch,x as f64,y as f64,None)).powi(2);count+=1;
                    }}}let rms=(sum/count as f64).sqrt();input_rms=Some(rms);
                    exercised&=b.rgb>2.0*flat_rms && b.bias.iter().sum::<f64>()/3.0>flat_rms && rms>2.0*flat_rms;
                    pass&=a.rgb<=0.95*b.rgb;
                }
                quality&=pass;windows.push(json!({"name":window.name,"active_native_bounds":[window.x0,window.y0,window.x1,window.y1],
                    "baseline":sj(&b),"candidate":sj(&a),"rgb_ratio":a.rgb/b.rgb,"chroma_ratio":a.chroma/b.chroma,
                    "protected_component":window.protect,"component_live":!window.protect || live(&b),"unmerged_source4_truth_rmse":input_rms,"quality_pass":pass}));
            }
            let mut joint=Value::Null;let mut placebo=Value::Null;
            if scene==Scene::NearFar {
                let b=two_components(&c.baseline_rgb);let a=two_components(&c.candidate_rgb);
                let component_live=b.iter().flatten().all(|v|*v>=0.5);let component_pass=(0..2).all(|j|(0..3).all(|ch|retained(b[j][ch],a[j][ch])));
                quality&=component_pass;exercised&=component_live;safety&=component_pass && component_live;
                joint=json!({"order":["near-fine","far-coarse"],"baseline":b,"candidate":a,"live":component_live,"retention_pass":component_pass});
                for mode in [Mode::Off,Mode::Neutral] {
                    let p=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),mode).unwrap();checks(&p,&frames,&original);
                    assert!(exact(&p.baseline_planes4,&p.candidate_planes4) && exact(&p.baseline_planes4,&c.baseline_planes4));
                    assert!(p.baseline_rgb.iter().zip(&p.candidate_rgb).all(|(x,y)|x.to_bits()==y.to_bits()));assert_eq!(changed(&p),0);
                }
                let wrong=compare_generated_forced(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Agreement,0).unwrap();checks(&wrong,&frames,&original);
                assert_eq!(wrong.forced_source,Some(0));assert!(exact(&wrong.baseline_planes4,&c.baseline_planes4));
                let wr=two_components(&wrong.candidate_rgb);let bscore=score(scene,&c.baseline_rgb,WHOLE);let wscore=score(scene,&wrong.candidate_rgb,WHOLE);
                let wrong_live=changed(&wrong)>0 && !exact(&wrong.baseline_planes4,&wrong.candidate_planes4);
                let wrong_rejected=(0..3).any(|ch|!retained(b[1][ch],wr[1][ch])) || !no_harm(&bscore,&wscore);
                exercised&=wrong_live && wrong_rejected;safety&=wrong_live && wrong_rejected;
                placebo=json!({"off_exact":true,"neutral_exact":true,"forced_source":0,"wrong_live":wrong_live,"wrong_rejected":wrong_rejected,
                    "wrong_components":wr,"wrong_score":sj(&wscore),"wrong_coarse_weights_changed":changed(&wrong)});
            }
            if scene!=Scene::Flat {
                exercised&=changed(&c)>0 && !exact(&c.baseline_planes4,&c.candidate_planes4)
                    && c.baseline_averaged_fraction.iter().skip(1).any(|v|*v<1.0);
            }
            iso_quality&=quality;iso_exercised&=exercised;iso_safety&=safety;
            let row=json!({"scene":scene.name(),"iso":iso,"quality_pass":quality,"fixture_exercised":exercised,"observation_safety_pass":safety,"windows":windows,
                "joint_components":joint,"placebos":placebo,"held_state_bit_exact":c.held_state_bit_exact,"coarse_weights_changed":changed(&c),
                "baseline_averaged_fraction":c.baseline_averaged_fraction,"candidate_averaged_fraction":c.candidate_averaged_fraction,
                "sources":c.frames});eprintln!("BAND_SOURCE_AGREEMENT_CASE {}",row);cases.push(row);
        }
        decisions.push(json!({"iso":iso,"quality_pass":iso_quality,"fixtures_exercised":iso_exercised,"admitted":iso_quality && iso_exercised,"observation_safety_pass":iso_safety}));
    }
    let admitted=decisions.iter().all(|v|v["admitted"]==true);
    let safety=decisions.iter().all(|v|v["observation_safety_pass"]==true);
    let result=json!({"status":"SCREEN_COMPLETE","legacy_general_qualification":admitted,"observation_safety_pass":safety,"photographic_replay_admitted":false,"root_review_required":true,"iso_decisions":decisions,
        "metric_commission":commissioned,"cases":cases,"scope":"One fixed same-band harmonic observation; inherited general failure remains explicit. Safety is not quality or automatic photographic admission. Shared plant noise cannot validate calibration."});
    write(&out.join("screen.json"),&result);eprintln!("BAND_SOURCE_AGREEMENT {}",json!({"legacy_general_qualification":admitted,"observation_safety_pass":safety,"photographic_replay_admitted":false}));
}

// A literal 2-D stencil, with no call to the implementation's separable kernel.
fn direct_smooth(v:&[f32],s:LevelSize)->Vec<f32> {
    let a=[1.0f64,4.0,6.0,4.0,1.0];let mut out=vec![0.0;s.pixels()];
    for y in 0..s.height {for x in 0..s.width {let mut sum=0.0;
        for dy in 0..5 {for dx in 0..5 {
            let xx=(x as isize+dx as isize-2).clamp(0,s.width as isize-1)as usize;
            let yy=(y as isize+dy as isize-2).clamp(0,s.height as isize-1)as usize;
            sum+=a[dx]*a[dy]*f64::from(v[yy*s.width+xx])/256.0;
        }}out[y*s.width+x]=sum as f32;
    }}out
}
fn fields(v:Vec<Vec<f32>>)->core::Fields {
    core::Fields{energy:v.clone(),floor:v.clone(),weights:v}
}
fn sizes()->Vec<LevelSize> {vec![LevelSize{width:17,height:13},LevelSize{width:9,height:7},
    LevelSize{width:5,height:4},LevelSize{width:3,height:2}]}
fn agreement(s:&[LevelSize],weights:&[Vec<Vec<f32>>])->super::BandAgreement {
    let mut sum=AgreementSum::new(s,weights.len()).unwrap();
    for w in weights {sum.add(w).unwrap();}sum.finish().unwrap()
}

#[test]
fn independent_stationary_unequal_memberships_are_identity() {
    let s=sizes();
    // Nondyadic, unequal source preferences catch w*q/exponent changes that
    // equal-source fields cannot. Test every border and each coarse band.
    let weights=[0.1f32,0.2,0.7].iter().map(|v|s[..s.len()-1].iter()
        .enumerate().map(|(k,z)|vec![*v*(k+1)as f32;z.pixels()]).collect()).collect::<Vec<Vec<Vec<f32>>>>();
    let a=agreement(&s,&weights);
    for w in &weights {
        let mut f=fields(w.clone());let count=a.apply(&mut f,Mode::Agreement).unwrap();
        assert!(exact(&f.weights,w));assert_eq!(count.changed.iter().sum::<usize>(),0);
        assert!(exact(&f.energy,w) && exact(&f.floor,w));
    }
    // A constant stationary field is not the only exercised case.
    let mut impulse=vec![vec![1.0;s[0].pixels()],vec![0.0;s[1].pixels()],vec![0.0;s[2].pixels()]];
    let centre=3*s[1].width+4;impulse[1][centre]=1.0;
    let mut other=impulse.clone();other[1].fill(1.0);other[1][centre]=0.0;
    let a=agreement(&s,&[impulse.clone(),other]);let mut f=fields(impulse.clone());
    let changes=a.apply(&mut f,Mode::Agreement).unwrap();
    // 5x5 central binomial tap is 36/256. Harmonic multiplier is 18/73.
    assert!((f.weights[1][centre]-18.0/73.0).abs()<1e-7);
    assert_eq!(changes.changed[1],1);
    assert!(f.weights[1].iter().enumerate().all(|(j,v)|j==centre || *v==0.0));
}

#[test]
fn independent_same_band_border_zero_and_finest_controls() {
    let s=sizes();
    let weights=(0..3).map(|source|s[..s.len()-1].iter().enumerate().map(|(k,z)|
        (0..z.pixels()).map(|j|if k>0 && (j%z.width<3 || (j+source*3)%11==0) {0.0}
            else {1.0+((j*(source+3)+source*7+k)%19)as f32}).collect()).collect()).collect::<Vec<Vec<Vec<f32>>>>();
    let a=agreement(&s,&weights);let mut missing_uniform_live=false;let mut normalization_order_live=false;
    let mut changed=0;let mut preserved_zero=0;let mut maximum_error=0.0f32;
    for (source,w) in weights.iter().enumerate() {
        let p=a.memberships(w).unwrap();let mut f=fields(w.clone());let count=a.apply(&mut f,Mode::Agreement).unwrap();
        changed+=count.changed.iter().sum::<usize>();
        assert!(exact(&f.energy,w) && exact(&f.floor,w));assert_eq!(f.weights[0],w[0]);
        for k in 1..w.len() {
            let denominator=(0..s[k].pixels()).map(|j|(weights[0][k][j]+weights[1][k][j])+weights[2][k][j]).collect::<Vec<_>>();
            assert_eq!(a.denominator[k],denominator);
            let expected_p=w[k].iter().zip(&denominator).map(|(&v,&d)|if d>0.0{v/d}else{1.0/3.0}).collect::<Vec<_>>();
            assert_eq!(p[k],expected_p);let q=direct_smooth(&expected_p,s[k]);
            let stripped=expected_p.iter().zip(&denominator).map(|(&p,&d)|if d>0.0{p}else{0.0}).collect::<Vec<_>>();
            let stripped=direct_smooth(&stripped,s[k]);let smooth_w=direct_smooth(&w[k],s[k]);let smooth_d=direct_smooth(&denominator,s[k]);
            for j in 0..w[k].len() {
                missing_uniform_live|=(q[j]-stripped[j]).abs()>0.01;
                if smooth_d[j]>0.0 {normalization_order_live|=(q[j]-smooth_w[j]/smooth_d[j]).abs()>0.001;}
                if w[k][j]==0.0 {preserved_zero+=1;assert_eq!(f.weights[k][j].to_bits(),w[k][j].to_bits());}
                let expected=if w[k][j]==0.0 || expected_p[j]==q[j] {w[k][j]}else{w[k][j]*(2.0*(q[j]/(expected_p[j]+q[j])))};
                let error=(f.weights[k][j]-expected).abs()/expected.abs().max(1.0);maximum_error=maximum_error.max(error);
            }
        }
        for mode in [Mode::Off,Mode::Neutral] {let mut off=fields(w.clone());a.apply(&mut off,mode).unwrap();assert!(exact(&off.weights,w));}
        // Changing only finest-band source evidence cannot affect any coarse membership.
        let mut different=weights.clone();different[source][0].fill(777.0);
        let b=agreement(&s,&different);let mut other=fields(different[source].clone());b.apply(&mut other,Mode::Agreement).unwrap();
        assert!(exact(&other.weights[1..],&f.weights[1..]));assert_eq!(other.weights[0],different[source][0]);
    }
    assert!(changed>0 && preserved_zero>0 && missing_uniform_live && normalization_order_live && maximum_error<3e-6);
    eprintln!("BAND_SOURCE_AGREEMENT independent border relative_error={maximum_error}, changed={changed}, zero_preserved={preserved_zero}");
}

#[test]
fn independent_unsupported_underflow_and_invalid_controls() {
    let s=sizes();let zero=s[..s.len()-1].iter().map(|z|vec![0.0;z.pixels()]).collect::<Vec<_>>();
    let a=agreement(&s,&[zero.clone(),zero.clone(),zero.clone()]);
    let mut f=fields(zero.clone());let count=a.apply(&mut f,Mode::Agreement).unwrap();
    assert!(exact(&f.weights,&zero));assert_eq!(count.changed.iter().sum::<usize>(),0);
    for p in a.memberships(&zero).unwrap().iter().skip(1) {assert!(p.iter().all(|v|*v==1.0/3.0));}
    let mut tiny=zero.clone();tiny[1][3*s[1].width+4]=f32::from_bits(1);
    let mut large=zero.clone();large[1].fill(1e30);
    let a=agreement(&s,&[tiny.clone(),large]);let mut f=fields(tiny.clone());let count=a.apply(&mut f,Mode::Agreement).unwrap();
    assert!(exact(&f.weights,&tiny));
    // p and q both underflow here: this must be counted before the p==q
    // neutral branch, and a positive canonical coefficient must stay positive.
    assert_eq!(f.weights[1][3*s[1].width+4].to_bits(),1);
    assert_eq!(count.rounding_fallback[1],1);
    assert_eq!(count.zeroed_positive.iter().sum::<usize>(),0);
    assert!(AgreementSum::new(&s,0).is_err());assert!(AgreementSum::new(&s,3).unwrap().finish().is_err());
    for bad in [-1.0,f32::NAN,f32::INFINITY] {let mut w=zero.clone();w[1][7]=bad;assert!(AgreementSum::new(&s,1).unwrap().add(&w).is_err());}
    let mut one=AgreementSum::new(&s,1).unwrap();one.add(&zero).unwrap();assert!(one.add(&zero).is_err());
    let mut huge=zero.clone();huge[1].fill(f32::MAX);let mut two=AgreementSum::new(&s,2).unwrap();two.add(&huge).unwrap();assert!(two.add(&huge).is_err());
}
