// Independent retained u16 fixture family, extended before this screen runs.
// Root executes. The numerical operator author does not verify these controls.

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
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-consistent-reconstruction-{}-{k}.ARW",scene.name()))};
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
struct Score {rgb:f64,green:f64,chroma:f64,recovery:[f64;3],truth_sd:[f64;3],bias:[f64;3]}
fn pixel(x:usize,y:usize)->usize {((y-2*crop().y)*2*crop().width+x-2*crop().x)*3}
fn score(scene:Scene,rgb:&[f32],window:Window)->Score {
    assert_eq!(rgb.len(),2*crop().width*2*crop().height*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let(mut error,mut green,mut chroma)=(0.0,0.0,0.0);let mut sums=[[0.0;4];3];let mut bias=[0.0;3];
    let n=((window.x1-window.x0)*(window.y1-window.y0)) as f64;
    for y in window.y0..window.y1 {for x in window.x0..window.x1 {let mut e=[0.0;3];
        for c in 0..3 {let truth=radiance(scene,c,x as f64,y as f64,None);let value=f64::from(rgb[pixel(x,y)+c]);
            e[c]=value-truth;error+=e[c]*e[c];bias[c]+=e[c];
            for(a,b)in sums[c].iter_mut().zip([truth,value,truth*truth,value*truth]){*a+=b;}}
        green+=e[1]*e[1];chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);
    }}
    let mut recovery=[0.0;3];let mut truth_sd=[0.0;3];
    for c in 0..3 {let[st,sv,tt,tv]=sums[c];let variance=(tt-st*st/n).max(0.0);truth_sd[c]=(variance/n).sqrt();
        if variance>1e-12 {recovery[c]=(tv-st*sv/n)/variance;}bias[c]/=n;}
    Score{rgb:(error/(3.0*n)).sqrt(),green:(green/n).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),recovery,truth_sd,bias}
}
fn retained(b:f64,c:f64)->bool {c.clamp(0.0,1.0)>=0.98*b.clamp(0.0,1.0)}
fn protected(b:&Score,c:&Score)->bool {(0..3).all(|j|retained(b.recovery[j],c.recovery[j]))}
fn live(s:&Score)->bool {(0..3).all(|j|s.recovery[j]>=0.5 && s.truth_sd[j]>1e-4)}
fn no_harm(b:&Score,c:&Score)->bool {c.rgb<=1.05*b.rgb && c.green<=1.05*b.green && c.chroma<=1.05*b.chroma}
fn sj(s:&Score)->Value {json!({"rgb_rmse":s.rgb,"green_rmse":s.green,"chroma_rg_bg_rmse":s.chroma,"template_recovery":s.recovery,"truth_sd":s.truth_sd,"signed_rgb_bias":s.bias})}
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
