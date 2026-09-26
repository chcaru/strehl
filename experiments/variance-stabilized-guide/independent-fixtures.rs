// Independent analytic truth and original-site noise, no measured PSF/calibration claim.
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel,PlaneNoise,Provenance},profile,pyramid::MergeConfig};
use strehl_raw::{Frame,Region};
const W:usize=320;const H:usize=288;const N:usize=5;
const GAIN:[f32;3]=[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)];
fn crop()->align_cmd::CropRect{align_cmd::CropRect{x:7,y:9,width:145,height:125}}
fn levels()->Levels{Levels{black:512.0,white:15360.0}}
fn channel(x:usize,y:usize)->usize{match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane{match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn hash16(v:&[u16])->String{let mut h=Sha256::new();for x in v{h.update(x.to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn hash_f32(v:&[f32])->String{let mut h=Sha256::new();for x in v{h.update(x.to_bits().to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn scramble(mut x:u32)->u32{x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64{let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x31d59a67;
    let u=(scramble(s)as f64+0.5)/4294967296.0;let v=(scramble(s^0xa73126bd)as f64+0.5)/4294967296.0;(-2.0*u.ln()).sqrt()*(TAU*v).cos()}
#[derive(Clone,Copy,Debug,PartialEq)]enum Scene{Flat,Veil,BrightRidge,WeakColour}
impl Scene{fn name(self)->&'static str{match self{Self::Flat=>"flat",Self::Veil=>"bright-defocus-spread",Self::BrightRidge=>"genuine-focused-bright-ridge",Self::WeakColour=>"weak-genuine-colour"}}}
fn elliptical(x:f64,y:f64,angle:f64,sx:f64,sy:f64)->f64{let(s,c)=angle.sin_cos();let u=c*x+s*y;let v=-s*x+c*y;(-0.5*((u/sx).powi(2)+(v/sy).powi(2))).exp()}
// [constant, true component one, true component two]. Veil exactly reuses the prior positive.
fn components(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->[f64;3]{match scene{
    Scene::Flat=>[0.25,0.0,0.0],
    Scene::Veil=>{let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-4.0).abs());
        let texture=[0.065,0.025,-0.050][c]*(-0.5*(TAU*0.06*sigma).powi(2)).exp()*(TAU*0.06*(0.8*x+0.6*y)+0.37).cos();
        let d=k.map_or(0.0,|j|j as f64);let sx=1.8+8.0*d;let sy=1.8+0.15*d;
        let glint=0.65*1.8*1.8/(sx*sy)*elliptical(x-122.0,y-120.0,0.70,sx,sy);
        [[0.24,0.26,0.22][c],texture,glint]},
    Scene::BrightRidge=>{let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-2.0).abs());let sx=(30.0f64.powi(2)+sigma*sigma).sqrt();let sy=(1.4f64.powi(2)+sigma*sigma).sqrt();
        [0.08,0.65*30.0*1.4/(sx*sy)*elliptical(x-148.0,y-138.0,0.70,sx,sy),0.0]},
    Scene::WeakColour=>{let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-3.0).abs());let att=(-0.5*(TAU*0.09*sigma).powi(2)).exp();
        let red=(TAU*0.09*x+0.31).cos()*att;let blue=(TAU*0.09*(0.6*x+0.8*y)+0.7).cos()*att;
        [0.18,[0.035,0.010,0.0][c]*red,[0.0,0.010,0.030][c]*blue]}}}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->f64{components(scene,c,x,y,k).iter().sum()}
fn transforms()->Vec<Similarity>{let shifts=[(-0.46,0.32),(0.37,-0.21),(0.0,0.0),(0.23,0.44),(-0.18,-0.39)];
    (0..N).map(|k|{let j=k as f64-2.0;Similarity{a:Cx::new(1.0+0.0008*j,0.0004*j),b:Cx::new(shifts[k].0/2.0,shifts[k].1/2.0)}}).collect()}
fn fixture(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel)->Frame{
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,levels:levels(),iso:Some(iso),
        wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-independent-vst-{}-{iso}-{k}.ARW",scene.name()))};
    assert!(!f.path.exists());let det=t.a.re*t.a.re+t.a.im*t.a.im;
    for y in 0..H{for x in 0..W{let u=x as f64-W as f64/2.0-2.0*t.b.re;let v=y as f64-H as f64/2.0-2.0*t.b.im;
        let wx=W as f64/2.0+(t.a.re*u+t.a.im*v)/det;let wy=H as f64/2.0+(-t.a.im*u+t.a.re*v)/det;
        let signal=(radiance(scene,channel(x,y),wx,wy,Some(k))*f64::from(levels().range())/f64::from(GAIN[channel(x,y)]))as f32;
        let value=512.0+f64::from(signal)+gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal));
        assert!(value>512.0&&value<15360.0,"unintended original clipping");f.data[(active.y+y)*stride+active.x+x]=value.round()as u16;
    }}f}
#[derive(Clone,Copy)]struct Window{name:&'static str,x0:usize,y0:usize,x1:usize,y1:usize}
const INTERIOR:Window=Window{name:"interior",x0:38,y0:42,x1:280,y1:244};
const SPILL:Window=Window{name:"outside-bright-core",x0:138,y0:133,x1:171,y1:167};
const ADJACENT:Window=Window{name:"focused-adjacent-texture",x0:180,y0:96,x1:224,y1:192};
const CORE:Window=Window{name:"focused-core-joint-components",x0:112,y0:110,x1:133,y1:132};
const RIDGE:Window=Window{name:"genuine-bright-ridge",x0:120,y0:110,x1:178,y1:166};
#[derive(Clone)]struct Score{rgb:f64,green:f64,chroma:f64,recovery:[f64;3],truth_sd:[f64;3],bias:f64}
fn score(scene:Scene,rgb:&[f32],w:Window)->Score{let width=2*crop().width;assert_eq!(rgb.len(),width*2*crop().height*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let(mut err,mut green,mut chroma,mut bias)=(0.0,0.0,0.0,0.0);let mut sums=[[0.0;4];3];let n=((w.x1-w.x0)*(w.y1-w.y0))as f64;
    for y in w.y0..w.y1{for x in w.x0..w.x1{let p=((y-2*crop().y)*width+x-2*crop().x)*3;let mut e=[0.0;3];
        for c in 0..3{let t=radiance(scene,c,x as f64,y as f64,None);let v=f64::from(rgb[p+c]);e[c]=v-t;err+=e[c]*e[c];bias+=e[c];
            for(a,b)in sums[c].iter_mut().zip([t,v,t*t,t*v]){*a+=b;}}
        green+=e[1]*e[1];chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);}}
    let mut recovery=[0.0;3];let mut truth_sd=[0.0;3];for c in 0..3{let[st,sv,tt,tv]=sums[c];let variance=(tt-st*st/n).max(0.0);truth_sd[c]=(variance/n).sqrt();if variance>1e-12{recovery[c]=(tv-st*sv/n)/variance;}}
    Score{rgb:(err/(3.0*n)).sqrt(),green:(green/n).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),recovery,truth_sd,bias:bias/(3.0*n)}}
#[derive(Clone)]struct Joint{coefficients:[[f64;2];3],correlation:[f64;3],relative_determinant:[f64;3]}
fn joint_core(rgb:&[f32])->Joint{let mut result=Joint{coefficients:[[0.0;2];3],correlation:[0.0;3],relative_determinant:[0.0;3]};
    let n=((CORE.x1-CORE.x0)*(CORE.y1-CORE.y0))as f64;
    for c in 0..3{let(mut sa,mut sb,mut sy,mut aa,mut ab,mut bb,mut ay,mut by)=(0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0);
        for y in CORE.y0..CORE.y1{for x in CORE.x0..CORE.x1{let[_,a,b]=components(Scene::Veil,c,x as f64,y as f64,None);let p=((y-2*crop().y)*2*crop().width+x-2*crop().x)*3;
            let value=f64::from(rgb[p+c]);sa+=a;sb+=b;sy+=value;aa+=a*a;ab+=a*b;bb+=b*b;ay+=a*value;by+=b*value;}}
        aa-=sa*sa/n;ab-=sa*sb/n;bb-=sb*sb/n;ay-=sa*sy/n;by-=sb*sy/n;let det=aa*bb-ab*ab;assert!(aa>0.0&&bb>0.0&&det/(aa*bb)>0.05,"CORE templates nearly collinear");
        result.coefficients[c]=[(ay*bb-by*ab)/det,(by*aa-ay*ab)/det];result.correlation[c]=ab/(aa*bb).sqrt();result.relative_determinant[c]=det/(aa*bb);
    }result}
fn score_json(s:&Score)->Value{json!({"rgb_rmse":s.rgb,"green_rmse":s.green,"chroma_rmse":s.chroma,"recovery":s.recovery,"truth_sd":s.truth_sd,"signed_rgb_bias":s.bias})}
fn joint_json(s:&Joint)->Value{json!({"texture_glint_coefficients":s.coefficients,"template_correlation":s.correlation,"relative_determinant":s.relative_determinant,"rank_with_intercept":[3,3,3],"standardized_two_template_condition":s.correlation.map(|r|(1.0+r.abs())/(1.0-r.abs()))})}
fn safe(b:&Score,c:&Score)->bool{c.rgb<=1.10*b.rgb&&c.green<=1.10*b.green&&c.chroma<=1.10*b.chroma}
fn keep(b:&Score,c:&Score)->bool{(0..3).all(|j|b.recovery[j]>=0.5&&c.recovery[j].clamp(0.0,1.0)>=0.90*b.recovery[j].min(1.0))}
fn joint_keep(b:&Joint,c:&Joint)->bool{b.coefficients.iter().flatten().zip(c.coefficients.iter().flatten()).all(|(&b,&c)|b>=0.5&&c.clamp(0.0,1.0)>=0.90*b.min(1.0))}
fn truth_image(scene:Scene)->Vec<f32>{(0..2*crop().height).flat_map(|y|(0..2*crop().width).flat_map(move|x|(0..3).map(move|c|radiance(scene,c,(x+2*crop().x)as f64,(y+2*crop().y)as f64,None)as f32))).collect()}
fn exact_slice(a:&[f32],b:&[f32])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn exact(a:&[Vec<f32>],b:&[Vec<f32>])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|exact_slice(a,b))}
fn write(path:&Path,value:&Value){serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}
