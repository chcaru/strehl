// Independent finite generated scenes. No measured optical or sensor truth.
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::Path};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},profile,pyramid::MergeConfig};
use strehl_raw::{Frame,Region};

const W:usize=384;const H:usize=320;const N:usize=5;const REFERENCE:usize=2;
const WB:[f32;3]=[2.0,1.0,1.5];
const BRIGHTNESS:[f64;N]=[0.85,0.93,1.0,1.07,1.15];
fn crop()->align_cmd::CropRect{align_cmd::CropRect{x:4,y:4,width:184,height:152}}
fn levels()->Levels{Levels{black:512.0,white:15360.0}}
fn channel(x:usize,y:usize)->usize{match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane{match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn hash(v:&[u16])->String{let mut h=Sha256::new();for x in v{h.update(x.to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn hash32(mut x:u32)->u32{x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64{let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x8317591d;
    let u=(hash32(s)as f64+0.5)/4294967296.0;let v=(hash32(s^0xa73126bd)as f64+0.5)/4294967296.0;
    (-2.0*u.ln()).sqrt()*(TAU*v).cos()}
#[derive(Clone,Copy,Debug,PartialEq)]enum Scene{Flat,Texture,BroadDefocus,Unsupported}
impl Scene{fn name(self)->&'static str{match self{Self::Flat=>"flat",Self::Texture=>"two-depth-colour-texture",Self::BroadDefocus=>"flux-conserving-broad-defocus",Self::Unsupported=>"unsupported-fine-texture"}}}
#[derive(Clone,Copy,Debug,PartialEq)]enum Drift{None,Uniform,LeftOnly}
impl Drift{fn name(self)->&'static str{match self{Self::None=>"none",Self::Uniform=>"uniform",Self::LeftOnly=>"left-only"}}}
fn brightness(drift:Drift,x:usize,k:usize)->f64{match drift{Drift::None=>1.0,Drift::Uniform=>BRIGHTNESS[k],Drift::LeftOnly=>if x<W/2{BRIGHTNESS[k]}else{1.0}}}
fn background(scene:Scene,c:usize,x:usize)->f64{[0.30,0.28,0.24][c]+if scene==Scene::Texture{0.12*(x as f64/(W-1)as f64-0.5)}else{0.0}}
fn radiance(scene:Scene,c:usize,x:usize,y:usize,k:Option<usize>)->f64{
    let base=background(scene,c,x);
    match scene{
        Scene::Flat=>base,
        Scene::Texture=>{let side=if(88..184).contains(&x)&&(80..240).contains(&y){Some(0)}else if(200..296).contains(&x)&&(80..240).contains(&y){Some(1)}else{None};
            match side{None=>base,Some(side)=>{let focus=if side==0{0}else{4};let sigma=0.65+k.map_or(0.0,|j|(j as f64-focus as f64).abs());
                let amp=[[0.065,0.040,-0.035],[-0.025,0.055,0.070]][side][c];
                base+amp*(-0.5*(TAU*0.085*sigma).powi(2)).exp()*(TAU*0.085*y as f64+0.37).cos()}}},
        Scene::BroadDefocus=>base+if(x as f64-192.0).powi(2)+(y as f64-160.0).powi(2)<58.0f64.powi(2){[0.32,0.30,0.22][c]}else{0.0},
        Scene::Unsupported=>base+0.04*(TAU*0.14*x as f64).cos()*(TAU*0.13*y as f64).cos(),
    }
}
// Finite periodic separable box blur; full image sum is conserved independently
// of the candidate's selected/eroded mask. Radius80 native > erosion16 quads.
fn flux_sum(values:&[f64])->f64{let(mut sum,mut correction)=(0.0,0.0);for &value in values{
    let adjusted=value-correction;let updated=sum+adjusted;correction=(updated-sum)-adjusted;sum=updated;}sum}
fn blur(src:&[f64],radius:usize)->Vec<f64>{if radius==0{return src.to_vec();}let mut mid=vec![0.0;W*H];let mut out=vec![0.0;W*H];let n=(2*radius+1)as f64;
    for y in 0..H{let mut sum=0.0;for j in 0..=2*radius{sum+=src[y*W+(W+j-radius)%W];}
        for x in 0..W{mid[y*W+x]=sum/n;sum+=src[y*W+(x+radius+1)%W]-src[y*W+(x+W-radius)%W];}}
    for x in 0..W{let mut sum=0.0;for j in 0..=2*radius{sum+=mid[((H+j-radius)%H)*W+x];}
        for y in 0..H{out[y*W+x]=sum/n;sum+=mid[((y+radius+1)%H)*W+x]-mid[((y+H-radius)%H)*W+x];}}
    let a=flux_sum(src);let b=flux_sum(&out);assert!((a-b).abs()/a.abs()<1e-12,"defocus plant changed whole flux");out
}
fn fixture(scene:Scene,k:usize,drift:Drift,noisy:bool,noise:&NoiseModel)->Frame{
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,levels:levels(),iso:Some(100.0),
        wb_coeffs:[WB[0],WB[1],WB[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-photometric-{}-{}-{noisy}-{k}.ARW",scene.name(),drift.name()))};
    assert!(!f.path.exists());
    let broad=if scene==Scene::BroadDefocus{Some((0..3).map(|c|blur(&(0..W*H).map(|j|radiance(scene,c,j%W,j/W,None)).collect::<Vec<_>>(),[80,32,0,32,80][k])).collect::<Vec<_>>())}else{None};
    for y in 0..H{for x in 0..W{let c=channel(x,y);let value=broad.as_ref().map_or_else(||radiance(scene,c,x,y,Some(k)),|v|v[c][y*W+x]);
        let signal=(value*brightness(drift,x,k)*f64::from(levels().range())/f64::from(WB[c]))as f32;
        let value=512.0+f64::from(signal)+if noisy{gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal))}else{0.0};
        assert!(value>512.0&&value<15360.0,"unintended source clipping");f.data[(active.y+y)*stride+active.x+x]=value.round()as u16;
    }}f
}
fn frames(scene:Scene,drift:Drift,noisy:bool,noise:&NoiseModel)->Vec<Frame>{(0..N).map(|k|fixture(scene,k,drift,noisy,noise)).collect()}
// Exact same sampled scene as source for the gain-estimator twin. This operation
// is test truth only; the fitting API never receives BRIGHTNESS or these gains.
fn scaled_twins(input:&[Frame])->Vec<Frame>{input.iter().enumerate().map(|(k,f)|{let mut o=f.clone();
    for y in 0..H{for x in 0..W{let j=(f.active.y+y)*f.stride+f.active.x+x;let v=512.0+(f64::from(f.data[j])-512.0)*BRIGHTNESS[k];assert!(v<15360.0);o.data[j]=v.round()as u16;}}o}).collect()}
fn transforms()->Vec<Similarity>{vec![Similarity{a:Cx::new(1.0,0.0),b:Cx::new(0.0,0.0)};N]}
fn raw_means(f:&Frame)->[f64;4]{let mut sum=[0.0;4];for y in 0..H{for x in 0..W{sum[(y%2)*2+x%2]+=f64::from(f.data[(f.active.y+y)*f.stride+f.active.x+x])-512.0;}}sum.map(|v|v/((W/2)*(H/2))as f64)}
#[derive(Clone,Copy)]struct Window{name:&'static str,x0:usize,y0:usize,x1:usize,y1:usize}
const WHOLE:Window=Window{name:"interior",x0:24,y0:24,x1:360,y1:296};
const FLAT:Window=Window{name:"flat-surround",x0:24,y0:24,x1:72,y1:72};
const LEFT:Window=Window{name:"near-left-coloured-detail",x0:104,y0:100,x1:168,y1:220};
const RIGHT:Window=Window{name:"far-right-coloured-detail",x0:216,y0:100,x1:280,y1:220};
#[derive(Clone)]struct Score{rgb:f64,chroma:f64,green:f64,recovery:[f64;3],truth_sd:[f64;3],mean_error:[f64;3]}
fn score(scene:Scene,rgb:&[f32],window:Window)->Score{let w=2*crop().width;let h=2*crop().height;assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let(mut error,mut chroma,mut green)=(0.0,0.0,0.0);let mut sums=[[0.0;4];3];let mut mean_error=[0.0;3];let n=((window.x1-window.x0)*(window.y1-window.y0))as f64;
    for y in window.y0..window.y1{for x in window.x0..window.x1{let mut e=[0.0;3];let p=((y-2*crop().y)*w+x-2*crop().x)*3;
        for c in 0..3{let truth=radiance(scene,c,x,y,None);let value=f64::from(rgb[p+c]);e[c]=value-truth;error+=e[c]*e[c];mean_error[c]+=e[c]/n;
            // Remove the independently known background before component
            // projection, so keeping its gradient cannot hide erased texture.
            let component=truth-background(scene,c,x);let reconstructed=value-background(scene,c,x);
            for(a,b)in sums[c].iter_mut().zip([component,reconstructed,component*component,reconstructed*component]){*a+=b;}}
        green+=e[1]*e[1];chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);
    }}let mut recovery=[0.0;3];let mut truth_sd=[0.0;3];for c in 0..3{let[st,sv,tt,tv]=sums[c];let variance=(tt-st*st/n).max(0.0);
        truth_sd[c]=(variance/n).sqrt();if variance>1e-12{recovery[c]=(tv-st*sv/n)/variance;}}
    Score{rgb:(error/(3.0*n)).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),green:(green/n).sqrt(),recovery,truth_sd,mean_error}}
fn score_json(s:&Score)->Value{json!({"rgb_rmse":s.rgb,"green_rmse":s.green,"chroma_rg_bg_rmse":s.chroma,
    "truth_template_recovery":s.recovery,"truth_template_sd":s.truth_sd,"mean_error":s.mean_error})}
fn exact(a:&[f32],b:&[f32])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn exact4(a:&[Vec<f32>],b:&[Vec<f32>])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|exact(a,b))}
fn write(path:&Path,value:&Value){serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}
