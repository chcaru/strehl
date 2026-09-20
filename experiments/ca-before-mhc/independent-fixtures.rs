// Independently generated continuous scene -> original u16 CFA. No author sampler.
use serde_json::{json, Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::PathBuf};
use strehl_core::{align::{Cx,Similarity},noise::{Levels,NoiseModel},CfaPlane};
use strehl_raw::{Frame,Region};
use crate::align_cmd::CropRect;

pub const W:usize=384;
pub const H:usize=320;
pub const N:usize=5;
pub const TRIM:usize=24;
pub const WB:[f32;3]=[1.7,1.0,2.3];
pub fn levels()->Levels {Levels{black:512.0,white:15360.0}}
pub fn crop(phase:bool)->CropRect {CropRect{x:11+usize::from(phase),y:13+usize::from(phase),width:170,height:138}}
pub fn ca_pulls(sign:f64)->[Similarity;3] {
    // Local active centre is the global sensor location (5984,560).
    // The full sensor centre is (3516,2344). This intercept reproduces the
    // global radial map over the local patch; it is not an enlarged slope.
    [-508.4e-6,0.0,174.4e-6].map(|eps| {
        let e=sign*eps;
        Similarity{a:Cx::new(1.0+e,0.0),b:Cx::new(e*2468.0/2.0,e*(-1784.0)/2.0)}
    })
}
pub fn transforms(phase:bool)->Vec<Similarity> {
    let translations=[[-0.46,0.32],[0.37,-0.21],[0.0,0.0],[0.23,0.44],[-0.18,-0.39]];
    (0..N).map(|k|if phase {
        let j=k as f64-2.0;
        Similarity{a:Cx::new(1.0+0.0004*j,0.0003*j),b:Cx::new(translations[k][0]/2.0,translations[k][1]/2.0)}
    } else {Similarity::IDENTITY}).collect()
}
pub fn inverse_native(x:f64,y:f64,t:Similarity)->(f64,f64) {
    let u=x-W as f64/2.0-2.0*t.b.re;let v=y-H as f64/2.0-2.0*t.b.im;
    let d=t.a.re*t.a.re+t.a.im*t.a.im;
    (W as f64/2.0+(t.a.re*u+t.a.im*v)/d,H as f64/2.0+(-t.a.im*u+t.a.re*v)/d)
}
pub fn channel(x:usize,y:usize)->usize {match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane {match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn hash32(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64 {
    let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x6b807415;
    let u=(hash32(s) as f64+0.5)/4294967296.0;let v=(hash32(s^0x3971bc61) as f64+0.5)/4294967296.0;
    (-2.0*u.ln()).sqrt()*(TAU*v).cos()
}
pub fn hash16(v:&[u16])->String {let mut h=Sha256::new();for x in v {h.update(x.to_le_bytes());}h.finalize().iter().map(|b|format!("{b:02x}")).collect()}
#[derive(Clone,Copy,PartialEq,Eq)]
pub enum Scene {Flat,NeutralChip,ColourEdges,ColourFine,ColourFocus,ColourFineHalf,ColourFocusHalf}
pub const SCENES:[Scene;5]=[Scene::Flat,Scene::NeutralChip,Scene::ColourEdges,Scene::ColourFine,Scene::ColourFocus];
impl Scene {
    pub fn name(self)->&'static str {match self {Self::Flat=>"flat",Self::NeutralChip=>"neutral-chip",Self::ColourEdges=>"colour-edges",Self::ColourFine=>"colour-fine",Self::ColourFocus=>"colour-varying-focus",Self::ColourFineHalf=>"colour-fine-half-frequency",Self::ColourFocusHalf=>"colour-varying-focus-half-frequency"}}
    pub fn components(self)->bool {matches!(self,Self::ColourFine|Self::ColourFocus|Self::ColourFineHalf|Self::ColourFocusHalf)}
}
pub fn wave(c:usize,x:f64,y:f64)->(f64,f64,f64,f64) {
    let (frequency,dx,dy,phase,base,amp)=[(0.18,0.8,0.6,0.31,0.30,0.09),(0.14,0.0,1.0,1.17,0.28,0.065),(0.20,-0.6,0.8,2.03,0.32,0.08)][c];
    (TAU*frequency*(dx*x+dy*y)+phase,base,amp,frequency)
}
pub fn wave_for(scene:Scene,c:usize,x:f64,y:f64)->(f64,f64,f64,f64) {
    if matches!(scene,Scene::ColourFineHalf|Scene::ColourFocusHalf) {
        let (p,base,amp,f)=wave(c,x*0.5,y*0.5);(p,base,amp,f*0.5)
    } else {wave(c,x,y)}
}
pub fn radiance(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->f64 {
    match scene {
        Scene::Flat=>0.30,
        Scene::NeutralChip=>{
            let oblique=((x+0.43*y-226.0)/0.9).tanh();
            let line=((y-114.0)/0.8).tanh()-((y-118.0)/0.8).tanh();
            0.29+0.075*oblique+0.025*line+0.025*(TAU*0.14*(0.8*x+0.6*y)+0.31).cos()
        },
        Scene::ColourEdges=>{
            let p=[(1.0,0.4,210.0,0.095),(-0.3,1.0,91.0,-0.065),(0.8,-0.6,64.0,0.08)][c];
            0.30+p.3*((p.0*x+p.1*y-p.2)/1.2).tanh()
        },
        Scene::ColourFine|Scene::ColourFocus|Scene::ColourFineHalf|Scene::ColourFocusHalf=>{
            let (p,base,amp,f)=wave_for(scene,c,x,y);
            let sigma=if matches!(scene,Scene::ColourFocus|Scene::ColourFocusHalf) {k.map_or(0.0,|j|0.6*(j as f64-(2.0+1.7*(TAU*x/W as f64).sin())).abs())} else {0.0};
            base+amp*(-0.5*TAU*TAU*sigma*sigma*f*f).exp()*p.cos()
        }
    }
}
pub fn fixture(scene:Scene,k:usize,t:Similarity,ca:[Similarity;3],iso:f32,noise:&NoiseModel,noisy:bool)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let bh=H+29;
    let mut frame=Frame{data:vec![64999;stride*bh],stride,buffer_height:bh,active,levels:levels(),iso:Some(iso),
        wb_coeffs:[WB[0],WB[1],WB[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:PathBuf::from(format!("C:/nonexistent-ca-before-mhc-{k}.ARW"))};
    assert!(!frame.path.exists());
    for y in 0..H {for x in 0..W {
        let c=channel(x,y);let (sx,sy)=inverse_native(x as f64,y as f64,ca[c]);let (rx,ry)=inverse_native(sx,sy,t);
        let signal=(radiance(scene,c,rx,ry,Some(k))*f64::from(levels().range())/f64::from(WB[c])) as f32;
        let error=if noisy {gaussian(x,y,k)*f64::from(noise.sigma(cfa(x,y),signal))} else {0.0};
        let observed=512.0+f64::from(signal)+error;
        assert!(observed>512.0 && observed<15360.0,"fixture clipping is outside this screen");
        frame.data[(active.y+y)*stride+active.x+x]=observed.round() as u16;
    }}
    frame
}
#[derive(Clone)]
pub struct Score {pub rgb:f64,pub chroma:f64,pub inphase:[f64;3],pub quadrature:[f64;3]}
impl Score {pub fn json(&self)->Value {json!({"rgb_rmse":self.rgb,"chroma_rg_bg_rmse":self.chroma,"inphase_truth_amplitude":self.inphase,"quadrature_truth_amplitude":self.quadrature})}}
pub fn score(scene:Scene,rgb:&[f32],crop:CropRect)->Score {
    let (w,h)=(2*crop.width,2*crop.height);assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let mut error=0.0;let mut chroma=0.0;let mut count=0usize;let mut sums=[[0.0f64;8];3];
    for y in TRIM..h-TRIM {for x in TRIM..w-TRIM {
        let (gx,gy)=((2*crop.x+x) as f64,(2*crop.y+y) as f64);let mut e=[0.0;3];
        for c in 0..3 {
            let value=f64::from(rgb[(y*w+x)*3+c]);e[c]=value-radiance(scene,c,gx,gy,None);error+=e[c]*e[c];
            if scene.components() {let (s,co)=wave_for(scene,c,gx,gy).0.sin_cos();for(o,v)in sums[c].iter_mut().zip([co,s,value,co*co,s*s,co*s,value*co,value*s]) {*o+=v;}}
        }
        chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);count+=1;
    }}
    let mut inphase=[0.0;3];let mut quadrature=[0.0;3];
    if scene.components() {for c in 0..3 {
        let[cs,ss,vs,cc,si,ci,vc,vi]=sums[c];let n=count as f64;let xx=cc-cs*cs/n;let yy=si-ss*ss/n;let xy=ci-cs*ss/n;
        let xv=vc-vs*cs/n;let yv=vi-vs*ss/n;let det=xx*yy-xy*xy;assert!(det>1.0);let amp=wave(c,0.0,0.0).2;
        inphase[c]=(xv*yy-yv*xy)/det/amp;quadrature[c]=(yv*xx-xv*xy)/det/amp;
    }}
    Score{rgb:(error/(3*count) as f64).sqrt(),chroma:(chroma/(2*count) as f64).sqrt(),inphase,quadrature}
}
pub fn truth(scene:Scene,crop:CropRect)->Vec<f32> {
    (0..2*crop.height).flat_map(|y|(0..2*crop.width).flat_map(move|x|(0..3).map(move|c|radiance(scene,c,(2*crop.x+x) as f64,(2*crop.y+y) as f64,None) as f32))).collect()
}
pub fn preserves(a:&Score,b:&Score)->bool {(0..3).all(|c|a.inphase[c]>=0.5 && b.inphase[c].min(1.0)>=0.98*a.inphase[c].min(1.0))}
