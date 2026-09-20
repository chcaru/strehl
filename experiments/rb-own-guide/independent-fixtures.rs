// Independent analytic image truth. No camera calibration or measured PSF claim.
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},profile,pyramid::MergeConfig};
use strehl_raw::{Frame,Region};

const W:usize=320;const H:usize=288;const N:usize=5;
const GAIN:[f32;3]=[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)];
fn crop()->align_cmd::CropRect{align_cmd::CropRect{x:7,y:9,width:145,height:125}}
fn levels()->Levels{Levels{black:512.0,white:15360.0}}
fn channel(x:usize,y:usize)->usize{match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane{match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn hash(v:&[u16])->String{let mut h=Sha256::new();for x in v{h.update(x.to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn hash32(mut x:u32)->u32{x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64{
    let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x31d59a67;
    let u=(hash32(s)as f64+0.5)/4294967296.0;let v=(hash32(s^0xa73126bd)as f64+0.5)/4294967296.0;
    (-2.0*u.ln()).sqrt()*(TAU*v).cos()
}
#[derive(Clone,Copy,Debug,PartialEq)]
enum Scene{Flat,Offset,ColourOnly,Neutral,ThinDepth,Radial,ClippedGlint}
impl Scene{fn name(self)->&'static str{match self{Self::Flat=>"flat",Self::Offset=>"rgb-focus-offset",
    Self::ColourOnly=>"colour-only",Self::Neutral=>"zero-offset-neutral",Self::ThinDepth=>"crossed-thin-depths",
    Self::Radial=>"genuine-coloured-rays",Self::ClippedGlint=>"clipped-glint-adjacent-detail"}}}
fn elliptical(x:f64,y:f64,angle:f64,sx:f64,sy:f64)->f64{
    let(s,c)=angle.sin_cos();let u=c*x+s*y;let v=-s*x+c*y;(-0.5*((u/sx).powi(2)+(v/sy).powi(2))).exp()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->f64{
    match scene{
        Scene::Flat=>0.25,
        Scene::Offset|Scene::ColourOnly|Scene::Neutral=>{
            if scene==Scene::ColourOnly && c==1{return 0.25;}
            let focus=if scene==Scene::Neutral{2}else{[1,2,3][c]};
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-focus as f64).abs());
            let (f,dx,dy,phase)=if scene==Scene::ColourOnly && c==2{(0.09,0.6,0.8,0.7)}else{(0.11,1.0,0.0,0.31)};
            0.25+0.09*(-0.5*(TAU*f*sigma).powi(2)).exp()*(TAU*f*(dx*x+dy*y)+phase).cos()
        },
        Scene::Radial=>{
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-3.0).abs());
            let sx=(24.0f64.powi(2)+sigma*sigma).sqrt();let sy=(1.6f64.powi(2)+sigma*sigma).sqrt();
            [0.24,0.26,0.22][c]+0.14*24.0*1.6/(sx*sy)*elliptical(x-148.0,y-138.0,[0.0,TAU/6.0,TAU/3.0][c],sx,sy)
        },
        Scene::ThinDepth=>{
            let far_sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-1.0).abs());
            let sx=(30.0f64.powi(2)+far_sigma*far_sigma).sqrt();let sy=(1.3f64.powi(2)+far_sigma*far_sigma).sqrt();
            let far=0.25+[0.10,0.12,0.09][c]*30.0*1.3/(sx*sy)*elliptical(x-152.0,y-140.0,TAU/4.0,sx,sy);
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-4.0).abs());let width=(1.2f64.powi(2)+sigma*sigma).sqrt();
            let line=[0.12,0.14,0.11][c]*1.2/width*(-0.5*((y-138.0)/width).powi(2)).exp();
            let radius=(3.0*sigma).ceil()as i32;let(mut mass,mut coverage,mut premult)=(0.0,0.0,0.0);
            for dx in -radius..=radius{let ww=(-0.5*(dx as f64/sigma).powi(2)).exp();mass+=ww;
                let xx=x+dx as f64;if xx>=164.0{coverage+=ww;premult+=ww*(0.25+line*(1.0+0.2*(TAU*0.035*xx).cos()));}}
            premult/mass+(1.0-coverage/mass)*far
        },
        Scene::ClippedGlint=>{
            let d=k.map_or(0.0,|j|j as f64);let sx=1.8+8.0*d;let sy=1.8+0.15*d;
            let glint=[2.00,2.08,1.92][c]*1.8*1.8/(sx*sy)*elliptical(x-122.0,y-120.0,[0.48,0.70,0.92][c],sx,sy);
            let far=[0.16,0.17,0.19][c]+glint+0.01*(-0.5*(TAU*0.02*(0.65+1.1*d)).powi(2)).exp()
                *(TAU*0.02*(0.8*x+0.6*y)+0.37).cos();
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-4.0).abs());let r=(3.0*sigma).ceil()as i32;
            let(mut mass,mut coverage,mut premult)=(0.0,0.0,0.0);
            let(dx,dy,phase)=[(0.8,0.6,0.37),(1.0,0.0,1.13),(-0.6,0.8,2.07)][c];
            let attenuation=(-0.5*(TAU*0.14*dy*sigma).powi(2)).exp();
            for offset in -r..=r{let w=(-0.5*(offset as f64/sigma).powi(2)).exp();mass+=w;let xx=x+offset as f64;
                if xx>=176.0{coverage+=w;premult+=w*([0.24,0.26,0.30][c]+[0.065,0.075,0.055][c]*attenuation
                    *(TAU*0.14*(dx*xx+dy*y)+phase).cos());}}
            premult/mass+(1.0-coverage/mass)*far
        }
    }
}
fn transforms()->Vec<Similarity>{let shifts=[(-0.46,0.32),(0.37,-0.21),(0.0,0.0),(0.23,0.44),(-0.18,-0.39)];
    (0..N).map(|k|{let j=k as f64-2.0;Similarity{a:Cx::new(1.0+0.0008*j,0.0004*j),b:Cx::new(shifts[k].0/2.0,shifts[k].1/2.0)}}).collect()}
fn fixture(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel)->Frame{
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,levels:levels(),iso:Some(iso),
        wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-independent-rb-{}-{iso}-{k}.ARW",scene.name()))};
    assert!(!f.path.exists());let determinant=t.a.re*t.a.re+t.a.im*t.a.im;
    for y in 0..H{for x in 0..W{let u=x as f64-W as f64/2.0-2.0*t.b.re;let v=y as f64-H as f64/2.0-2.0*t.b.im;
        let wx=W as f64/2.0+(t.a.re*u+t.a.im*v)/determinant;let wy=H as f64/2.0+(-t.a.im*u+t.a.re*v)/determinant;
        let signal=(radiance(scene,channel(x,y),wx,wy,Some(k))*f64::from(levels().range())/f64::from(GAIN[channel(x,y)]))as f32;
        let value=512.0+f64::from(signal)+gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal));
        assert!(value>512.0);if scene!=Scene::ClippedGlint{assert!(value<15360.0,"unintended source clipping");}
        f.data[(active.y+y)*stride+active.x+x]=value.round().min(16383.0)as u16;
    }}f
}
#[derive(Clone,Copy)]struct Window{name:&'static str,x0:usize,y0:usize,x1:usize,y1:usize}
const INTERIOR:Window=Window{name:"interior",x0:38,y0:42,x1:280,y1:244};
const RADIAL:Window=Window{name:"real-coloured-rays",x0:84,y0:72,x1:232,y1:216};
const THIN_FAR:Window=Window{name:"thin-far",x0:141,y0:92,x1:163,y1:188};
const THIN_NEAR:Window=Window{name:"thin-near",x0:168,y0:130,x1:222,y1:147};
const JUNCTION:Window=Window{name:"thin-junction",x0:148,y0:112,x1:184,y1:166};
const OUTSIDE:Window=Window{name:"outside-clipped-core",x0:138,y0:133,x1:171,y1:167};
const NEAR:Window=Window{name:"unsaturated-adjacent-texture",x0:180,y0:96,x1:224,y1:192};
#[derive(Clone)]struct Score{rgb:f64,chroma:f64,green:f64,recovery:[f64;3],truth_sd:[f64;3]}
fn score(scene:Scene,rgb:&[f32],window:Window)->Score{
    let w=2*crop().width;let h=2*crop().height;assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    assert!(window.x0>=2*crop().x && window.y0>=2*crop().y && window.x1<=2*crop().x+w && window.y1<=2*crop().y+h);
    let(mut error,mut chroma,mut green)=(0.0,0.0,0.0);let mut sums=[[0.0;4];3];let n=((window.x1-window.x0)*(window.y1-window.y0))as f64;
    for y in window.y0..window.y1{for x in window.x0..window.x1{let mut e=[0.0;3];let p=((y-2*crop().y)*w+x-2*crop().x)*3;
        for c in 0..3{let truth=radiance(scene,c,x as f64,y as f64,None);let value=f64::from(rgb[p+c]);e[c]=value-truth;error+=e[c]*e[c];
            for(a,b)in sums[c].iter_mut().zip([truth,value,truth*truth,value*truth]){*a+=b;}}
        green+=e[1]*e[1];chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);
    }}let mut recovery=[0.0;3];let mut truth_sd=[0.0;3];for c in 0..3{let[st,sv,tt,tv]=sums[c];let variance=(tt-st*st/n).max(0.0);
        truth_sd[c]=(variance/n).sqrt();if variance>1e-12{recovery[c]=(tv-st*sv/n)/variance;}}
    Score{rgb:(error/(3.0*n)).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),green:(green/n).sqrt(),recovery,truth_sd}
}
fn recovery_pass(b:&Score,c:&Score)->bool{(0..3).all(|j|b.recovery[j]<0.5 || c.recovery[j].clamp(0.0,1.0)>=0.9*b.recovery[j].min(1.0))}
fn score_json(s:&Score)->Value{json!({"rgb_rmse":s.rgb,"green_rmse":s.green,"chroma_rg_bg_rmse":s.chroma,"truth_template_recovery":s.recovery,"truth_template_sd":s.truth_sd})}
fn truth_image(scene:Scene)->Vec<f32>{let w=2*crop().width;let h=2*crop().height;
    (0..h).flat_map(|y|(0..w).flat_map(move|x|(0..3).map(move|c|radiance(scene,c,(x+2*crop().x)as f64,(y+2*crop().y)as f64,None)as f32))).collect()}
fn commission()->Value{
    let exact=truth_image(Scene::ColourOnly);let good=score(Scene::ColourOnly,&exact,INTERIOR);assert!(good.rgb<1e-7 && good.chroma<1e-7);
    let mut half=exact.clone();let mut noise=exact.clone();for(p,(h,n))in half.chunks_exact_mut(3).zip(noise.chunks_exact_mut(3)).enumerate(){
        for c in [0,2]{h[c]=0.25+0.5*(h[c]-0.25);n[c]+=0.03*gaussian(p%(2*crop().width),p/(2*crop().width),c)as f32;}}
    let half=score(Scene::ColourOnly,&half,INTERIOR);let noise=score(Scene::ColourOnly,&noise,INTERIOR);
    assert!([0,2].iter().all(|&c|(half.recovery[c]-0.5).abs()<1e-5) && !recovery_pass(&good,&half));
    assert!(noise.rgb>0.02 && noise.chroma>0.025,"added colour noise destroyer escaped");
    json!({"exact":score_json(&good),"half_amplitude":score_json(&half),"added_colour_noise":score_json(&noise)})
}
fn exact(a:&[Vec<f32>],b:&[Vec<f32>])->bool{a.len()==b.len() && a.iter().zip(b).all(|(a,b)|exact_slice(a,b))}
fn exact_slice(a:&[f32],b:&[f32])->bool{a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn write(path:&Path,value:&Value){serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}
