// Fixed, bounded original-u16 corpus. Pupil equation reused from layered-raw-inverse.
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f32::consts::PI,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},profile,pyramid::MergeConfig};
use strehl_raw::{Frame,Region};
const W:usize=192;const H:usize=176;const NW:usize=160;const NH:usize=144;
const WB:[f32;3]=[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)];
fn levels()->Levels{Levels{black:512.0,white:15360.0}}
fn crop()->align_cmd::CropRect{align_cmd::CropRect{x:8,y:8,width:80,height:72}}
#[derive(Clone,Copy,Debug,PartialEq)]enum Family{Flat,Sine,Straight,Blobs,Curved,Thin,Glint,Clipped,Colour}
impl Family{fn name(self)->&'static str{match self{Self::Flat=>"flat",Self::Sine=>"single-depth-cosine",Self::Straight=>"straight-checker-layers",Self::Blobs=>"gaussian-blobs",Self::Curved=>"curved-bright-occlusion",Self::Thin=>"near-fine-far-coarse",Self::Glint=>"unclipped-point-glint",Self::Clipped=>"clipped-point-glint",Self::Colour=>"weak-colour-dots"}}}
#[derive(Clone)]struct Case{id:String,training:bool,family:Family,variant:usize,iso:f32,n:usize}
fn cases()->Vec<Case>{let mut out=Vec::new();for(family,count)in[(Family::Flat,2),(Family::Sine,4),(Family::Straight,4),(Family::Blobs,2)]{for v in 0..count{out.push(Case{id:format!("train-{}-{v}",family.name()),training:true,family,variant:v,iso:if v%2==0{100.0}else{400.0},n:5});}}
    for(family,n)in[(Family::Flat,5),(Family::Flat,9),(Family::Curved,9),(Family::Thin,5),(Family::Glint,5),(Family::Clipped,5),(Family::Colour,5)]{out.push(Case{id:format!("held-{}-n{n}",family.name()),training:false,family,variant:0,iso:100.0,n});}out}
fn channel(x:usize,y:usize)->usize{match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn cfa(x:usize,y:usize)->CfaPlane{match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn scramble(mut x:u32)->u32{x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn random_normal(x:usize,y:usize,k:usize,salt:u32)->f32{let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^salt;
    let u=(scramble(s)as f64+0.5)/4294967296.0;let v=(scramble(s^0xa73126bd)as f64+0.5)/4294967296.0;((-2.0*u.ln()).sqrt()*(std::f64::consts::TAU*v).cos())as f32}
fn hash16(v:&[u16])->String{let mut h=Sha256::new();for x in v{h.update(x.to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn hash_f32(v:&[f32])->String{let mut h=Sha256::new();for x in v{h.update(x.to_bits().to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn pupil(case:&Case)->Vec<[f32;2]>{let mut points=Vec::new();for j in 0..32{let area=(j as f32+0.5)/32.0;let annular=!case.training&&matches!(case.family,Family::Glint|Family::Clipped|Family::Colour);
    let r=if annular{(0.45f32.powi(2)+(1.0-0.45f32.powi(2))*area).sqrt()}else{area.sqrt()};let theta=j as f32*PI*(3.0-5.0f32.sqrt())+0.37;
    let(mut x,mut y)=(r*theta.cos(),r*theta.sin());if !case.training&&!annular{y*=0.55;let(s,c)=0.60f32.sin_cos();(x,y)=(c*x-s*y,s*x+c*y);}
    points.push([x,y]);points.push([-x,-y]);}points}
fn pupil_name(case:&Case)->&'static str{if case.training{"circular-disc64"}else if matches!(case.family,Family::Glint|Family::Clipped|Family::Colour){"annulus-inner-radius-.45-64"}else{"elliptical-.55-rotated-.60-64"}}
fn bump(x:f32,y:f32,cx:f32,cy:f32,sx:f32,sy:f32)->f32{(-0.5*(((x-cx)/sx).powi(2)+((y-cy)/sy).powi(2))).exp()}
fn mask(v:bool)->f32{if v{1.0}else{0.0}}
fn sign(v:bool)->f32{if v{1.0}else{-1.0}}
// Returns alpha, near base/detail, far base/detail; no selected-source labels.
fn layers(case:&Case,x:f32,y:f32,c:usize)->(f32,f32,f32,f32,f32){let v=case.variant as f32;let tau=2.0*PI;match case.family{
    Family::Flat=>{let b=if case.training{0.16+0.16*v}else{0.25};(0.0,b,0.0,b,0.0)},
    Family::Sine=>{let angle=0.35*v;let carrier=(tau*(0.035+0.012*v)*(x*angle.cos()+y*angle.sin())+0.31*v).cos();(0.0,0.22,0.0,0.22,[0.06,0.045,0.05][c]*carrier)},
    Family::Straight=>{let a=mask(x+(v-1.5)*0.18*(y-88.0)>=96.0);let near=0.045*(tau*0.075*x+v).cos()*(tau*0.045*y+0.2*v).cos();let far=[0.05,0.035,0.045][c]*(tau*0.032*(0.8*x+0.6*y)+v).cos();(a,0.18,near,0.32,far)},
    Family::Blobs=>{let d=[0.35,0.28,0.25][c]*bump(x,y,80.0+20.0*v,72.0,7.0+3.0*v,12.0)+0.12*bump(x,y,126.0,114.0,13.0,8.0);(0.0,0.12,0.0,0.12,d)},
    Family::Curved=>{let a=mask(((x-94.0)/32.0).powi(2)+((y-87.0)/36.0).powi(2)<=1.0);let px=(x-62.0).rem_euclid(9.0)-4.5;let py=(y-53.0).rem_euclid(11.0)-5.5;
        let near=[0.038,0.032,0.028][c]*(-0.5*(px*px+py*py)/1.2f32.powi(2)).exp();let far=[0.07,0.06,0.05][c]*bump(x,y,123.0,87.0,1.5,21.0);(a,0.09,near,0.66,far)},
    Family::Thin=>{let centre=96.0+10.0*((y-88.0)/21.0).sin();let a=mask((x-centre).abs()<4.0);let near=[0.09,0.07,0.08][c]*sign(((y/4.0).floor()as i32)%2==0);
        let radius=((x-101.0).powi(2)+(y-89.0).powi(2)).sqrt();let far=[0.055,0.065,0.05][c]*(tau*0.026*radius+0.43).cos();(a,0.28,near,0.18,far)},
    Family::Glint|Family::Clipped=>{let a=mask(x>117.0+5.0*((y-88.0)/17.0).sin());let px=(x-18.0).rem_euclid(8.0)-4.0;let py=(y-25.0).rem_euclid(10.0)-5.0;let near=[0.045,0.04,0.055][c]*mask(px.abs()<1.3||py.abs()<1.3);
        let peak=if case.family==Family::Clipped{2.4}else{0.65};let far=peak*bump(x,y,88.0,84.0,1.6,1.6);(a,0.22,near,0.17,far)},
    Family::Colour=>{let mut near=0.0;for (j,[cx,cy])in[[65.0,63.0],[101.0,63.0],[65.0,107.0],[101.0,107.0]].into_iter().enumerate(){near+=[0.055,0.012,0.038][c]*sign((j+c)%2==0)*bump(x,y,cx,cy,1.6,5.5);}
        let far=[0.025,0.010,0.045][c]*mask((x-124.0).abs()<2.0&&y>51.0&&y<124.0);let a=mask(x<113.0);(a,0.18,near,0.18,far)}
}}
struct Latent{alpha:Vec<f32>,near:Vec<f32>,far:Vec<f32>,base:Vec<f32>,near_detail:Vec<f32>,far_detail:Vec<f32>}
fn latent(case:&Case)->Latent{let n=W*H;let mut l=Latent{alpha:vec![0.0;n],near:vec![0.0;n*3],far:vec![0.0;n*3],base:vec![0.0;n*3],near_detail:vec![0.0;n*3],far_detail:vec![0.0;n*3]};
    for y in 0..H{for x in 0..W{for c in 0..3{let(a,nb,nd,fb,fd)=layers(case,x as f32,y as f32,c);let p=y*W+x;l.alpha[p]=a;l.near[p*3+c]=a*(nb+nd);l.far[p*3+c]=fb+fd;l.base[p*3+c]=a*nb+(1.0-a)*fb;l.near_detail[p*3+c]=a*nd;l.far_detail[p*3+c]=(1.0-a)*fd;}}}l}
fn sample(v:&[f32],channels:usize,x:f32,y:f32,c:usize)->f32{let x=x.clamp(0.0,(W-1)as f32);let y=y.clamp(0.0,(H-1)as f32);let ix=x.floor()as usize;let iy=y.floor()as usize;let fx=x-ix as f32;let fy=y-iy as f32;
    let row=|yy|{let a=v[(yy*W+ix)*channels+c];let b=v[(yy*W+(ix+1).min(W-1))*channels+c];a*(1.0-fx)+b*fx};row(iy)*(1.0-fy)+row((iy+1).min(H-1))*fy}
fn blur(v:&[f32])->Vec<f32>{let mut kernel=[0.0f32;7];let mut mass=0.0;for(i,w)in kernel.iter_mut().enumerate(){*w=(-0.5*((i as f32-3.0)/0.7).powi(2)).exp();mass+=*w;}for w in &mut kernel{*w/=mass;}
    let mut tmp=vec![0.0;v.len()];let mut out=vec![0.0;v.len()];for y in 0..H{for x in 0..W{for c in 0..3{for(k,w)in kernel.iter().enumerate(){let xx=(x as isize+k as isize-3).clamp(0,W as isize-1)as usize;tmp[(y*W+x)*3+c]+=w*v[(y*W+xx)*3+c];}}}}
    for y in 0..H{for x in 0..W{for c in 0..3{for(k,w)in kernel.iter().enumerate(){let yy=(y as isize+k as isize-3).clamp(0,H as isize-1)as usize;out[(y*W+x)*3+c]+=w*tmp[(yy*W+x)*3+c];}}}}out}
fn render(l:&Latent,points:&[[f32;2]],focus:f32,wrong_visibility:bool)->Vec<f32>{let mut out=vec![0.0;W*H*3];let ns=10.0*(focus-1.0);let fs=10.0*focus;
    for y in 0..H{for x in 0..W{let(mut a_sum,mut near_sum,mut far_sum)=(0.0,[0.0;3],[0.0;3]);for &[ux,uy] in points{let nx=x as f32+ns*ux;let ny=y as f32+ns*uy;let fx=x as f32+fs*ux;let fy=y as f32+fs*uy;
        let a=sample(&l.alpha,1,nx,ny,0);a_sum+=a;for c in 0..3{let n=sample(&l.near,3,nx,ny,c);let f=sample(&l.far,3,fx,fy,c);near_sum[c]+=n;far_sum[c]+=f;out[(y*W+x)*3+c]+=n+(1.0-a)*f;}}
        for c in 0..3{let inv=1.0/points.len()as f32;out[(y*W+x)*3+c]=if wrong_visibility{near_sum[c]*inv+(1.0-a_sum*inv)*far_sum[c]*inv}else{out[(y*W+x)*3+c]*inv};}
    }}blur(&out)}
fn cut(v:&[f32])->Vec<f32>{let mut out=Vec::with_capacity(NW*NH*3);for y in 16..160{out.extend_from_slice(&v[(y*W+16)*3..(y*W+176)*3]);}out}
fn transforms(n:usize)->Vec<Similarity>{(0..n).map(|k|{let j=k as f64-(n-1)as f64/2.0;Similarity{a:Cx::new(1.0+0.00015*j,0.00010*j),b:Cx::new(0.11*j,-0.07*j)}}).collect()}
struct Generated{frames:Vec<Frame>,transforms:Vec<Similarity>,truth:Vec<f32>,base:Vec<f32>,near_detail:Vec<f32>,far_detail:Vec<f32>,clipped:[usize;4]}
fn generate(case:&Case)->Generated{let l=latent(case);let points=pupil(case);let all=l.base.iter().zip(&l.near_detail).zip(&l.far_detail).map(|((b,n),f)|b+n+f).collect::<Vec<_>>();let truth=cut(&blur(&all));
    let ts=transforms(case.n);let noise=profile::noise_model_for("ILCE-7CM2",Some(case.iso),levels());let mut frames=Vec::new();let mut clipped=[0;4];let salt=if case.training{0x51d982a7^(case.variant as u32).wrapping_mul(0x217983)}else{0xa2310bc5};
    for(k,&t)in ts.iter().enumerate(){let image=render(&l,&points,k as f32/(case.n-1)as f32,false);let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let bh=H+29;
        let mut frame=Frame{data:vec![64999;stride*bh],stride,buffer_height:bh,active,levels:levels(),iso:Some(case.iso),wb_coeffs:[WB[0],WB[1],WB[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-learned-guide-{}-{k}.ARW",case.id))};assert!(!frame.path.exists());let det=t.a.re*t.a.re+t.a.im*t.a.im;
        for y in 0..H{for x in 0..W{let u=x as f64-W as f64/2.0-2.0*t.b.re;let v=y as f64-H as f64/2.0-2.0*t.b.im;let wx=(W as f64/2.0+(t.a.re*u+t.a.im*v)/det)as f32;let wy=(H as f64/2.0+(-t.a.im*u+t.a.re*v)/det)as f32;let c=channel(x,y);
            let signal=sample(&image,3,wx,wy,c)*levels().range()/WB[c];let value=512.0+signal+random_normal(x,y,k,salt)*noise.sigma(cfa(x,y),signal);assert!(value>0.0);let code=value.round().clamp(0.0,levels().white)as u16;
            if code>=levels().white as u16{clipped[(y%2)*2+x%2]+=1;}frame.data[(active.y+y)*stride+active.x+x]=code;
        }}frames.push(frame);
    }
    if case.family==Family::Clipped{assert!(clipped.iter().sum::<usize>()>0,"clipped original control not exercised");}else{assert_eq!(clipped.iter().sum::<usize>(),0);}
    Generated{frames,transforms:ts,truth,base:cut(&blur(&l.base)),near_detail:cut(&blur(&l.near_detail)),far_detail:cut(&blur(&l.far_detail)),clipped}
}
#[derive(Clone,Copy)]struct Window{name:&'static str,x0:usize,y0:usize,x1:usize,y1:usize}
const WHOLE:Window=Window{name:"interior",x0:30,y0:30,x1:162,y1:146};
const CURVED:Window=Window{name:"curved-bright-boundary-positive",x0:55,y0:43,x1:135,y1:130};
const THIN:Window=Window{name:"near-fine-far-coarse-positive",x0:66,y0:42,x1:130,y1:138};
const GLINT:Window=Window{name:"genuine-unclipped-glint",x0:77,y0:73,x1:100,y1:96};
const ADJACENT:Window=Window{name:"glint-adjacent-near-detail",x0:127,y0:49,x1:156,y1:134};
const SPILL:Window=Window{name:"unclipped-spread-outside-core",x0:98,y0:69,x1:113,y1:110};
const COLOUR:Window=Window{name:"weak-colour-components",x0:49,y0:43,x1:136,y1:128};
fn windows(f:Family)->Vec<Window>{match f{Family::Curved=>vec![WHOLE,CURVED],Family::Thin=>vec![WHOLE,THIN],Family::Glint=>vec![WHOLE,GLINT,ADJACENT,SPILL],Family::Clipped=>vec![ADJACENT,SPILL],Family::Colour=>vec![WHOLE,COLOUR],_=>vec![WHOLE]}}
fn index(x:usize,y:usize,c:usize)->usize{((y-16)*NW+x-16)*3+c}
#[derive(Clone)]struct Score{rgb:f64,green:f64,chroma:f64,bias:f64,coeff:[[Option<f64>;2];3],template_sd:[[f64;2];3],condition:[Option<f64>;3]}
fn score(g:&Generated,rgb:&[f32],w:Window)->Score{assert_eq!(rgb.len(),NW*NH*3);let n=((w.x1-w.x0)*(w.y1-w.y0))as f64;let(mut error,mut green,mut chroma,mut bias)=(0.0,0.0,0.0,0.0);let mut sums=[[0.0f64;8];3];
    for y in w.y0..w.y1{for x in w.x0..w.x1{let mut e=[0.0;3];for c in 0..3{let p=index(x,y,c);let value=f64::from(rgb[p]);e[c]=value-f64::from(g.truth[p]);error+=e[c]*e[c];bias+=e[c];let a=f64::from(g.near_detail[p]);let b=f64::from(g.far_detail[p]);let val=value-f64::from(g.base[p]);for (s,v)in sums[c].iter_mut().zip([a,b,val,a*a,a*b,b*b,a*val,b*val]){*s+=v;}}green+=e[1]*e[1];chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);}}
    let mut coeff=[[None;2];3];let mut template_sd=[[0.0;2];3];let mut condition=[None;3];for c in 0..3{let[sa,sb,sy,mut aa,mut ab,mut bb,mut ay,mut by]=sums[c];aa-=sa*sa/n;ab-=sa*sb/n;bb-=sb*sb/n;ay-=sa*sy/n;by-=sb*sy/n;template_sd[c]=[(aa.max(0.0)/n).sqrt(),(bb.max(0.0)/n).sqrt()];let la=template_sd[c][0]>=0.001;let lb=template_sd[c][1]>=0.001;
        if la&&lb{let r=ab/(aa*bb).sqrt();let det=aa*bb-ab*ab;if det/(aa*bb)>0.05{coeff[c]=[Some((ay*bb-by*ab)/det),Some((by*aa-ay*ab)/det)];condition[c]=Some((1.0+r.abs())/(1.0-r.abs()));}}
        else if la{coeff[c][0]=Some(ay/aa);condition[c]=Some(1.0);}else if lb{coeff[c][1]=Some(by/bb);condition[c]=Some(1.0);}}
    Score{rgb:(error/(3.0*n)).sqrt(),green:(green/n).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),bias:bias/(3.0*n),coeff,template_sd,condition}
}
fn score_json(s:&Score)->Value{json!({"rgb_rmse":s.rgb,"green_rmse":s.green,"chroma_rmse":s.chroma,"signed_rgb_bias":s.bias,"near_far_coefficients":s.coeff,"template_sd":s.template_sd,"standardized_condition":s.condition})}
fn safe(reference:&Score,candidate:&Score)->bool{candidate.rgb<=1.10*reference.rgb&&candidate.green<=1.10*reference.green&&candidate.chroma<=1.10*reference.chroma}
fn retained(reference:&Score,candidate:&Score)->bool{(0..3).all(|c|(0..2).all(|d|match reference.coeff[c][d]{Some(r)if r>=0.5=>candidate.coeff[c][d].is_some_and(|a|a.clamp(0.0,1.0)>=0.9*r.min(1.0)),_=>true}))}
fn read_f32(path:&Path)->Vec<f32>{let bytes=std::fs::read(path).unwrap();assert_eq!(bytes.len()%4,0);bytes.chunks_exact(4).map(|b|f32::from_le_bytes(b.try_into().unwrap())).collect()}
fn write(path:&Path,value:&Value){serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}
