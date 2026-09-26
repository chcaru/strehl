// Independently chosen generated original-u16 data. No original RAW reads.
use crate::align_cmd;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{f32::consts::PI, path::{Path, PathBuf}};
use strehl_core::{CfaPlane, align::{Cx, Similarity}, noise::{Levels, NoiseModel}, profile, pyramid::MergeConfig};
use strehl_raw::{Frame, Region};

const CW: usize = 192;
const CH: usize = 176;
const WB: [f32; 3] = [f32::from_bits(1070374912), 1.0, f32::from_bits(1076715520)];
fn levels() -> Levels { Levels { black: 512.0, white: 15360.0 } }
#[derive(Clone, Copy, Debug, PartialEq)]
enum Family { Flat, Natural, Compound, Fork, Polygon, Thin, Glint, Clipped, Colour, Scale }
impl Family { fn name(self) -> &'static str { match self {
    Self::Flat=>"flat", Self::Natural=>"natural-layers", Self::Compound=>"compound-texture",
    Self::Fork=>"forked-filaments", Self::Polygon=>"serrated-polygon", Self::Thin=>"near-fine-far-coarse",
    Self::Glint=>"unclipped-glint", Self::Clipped=>"clipped-glint", Self::Colour=>"weak-colour", Self::Scale=>"multiscale-gabor"
}}}
#[derive(Clone)]
struct Case { id:String, training:bool, family:Family, variant:usize, iso:f32, n:usize, large:bool }
impl Case {
    fn crop(&self)->align_cmd::CropRect {
        let (w,h)=if self.large { if self.training {(1024,1024)}else{(1031,1029)} }else{(80,72)};
        align_cmd::CropRect{x:8,y:8,width:w,height:h}
    }
    fn size(&self)->(usize,usize){let c=self.crop();(2*c.width+32,2*c.height+32)}
    fn bands(&self)->usize{if self.large{7}else{3}}
    fn focus(&self,k:usize)->f32 {if self.family==Family::Scale{assert_eq!(self.n,5);return [0.0,0.22,0.5,0.78,1.0][k];}
        let u=k as f32/(self.n-1)as f32;if self.variant%2==0{u}else{u*u*(3.0-2.0*u)}}
}
fn cases()->Vec<Case>{
    let mut out=Vec::new();
    let mut add=|training,family:Family,variant,iso,n,large|{
        out.push(Case{id:format!("{}-{}-v{variant}-n{n}-b{}",if training{"train"}else{"fresh"},family.name(),if large{7}else{3}),training,family,variant,iso,n,large});
    };
    for(v,(iso,n))in[(100.0,5),(400.0,9),(1600.0,17),(400.0,5)].into_iter().enumerate(){add(true,Family::Flat,v,iso,n,false);}
    for v in 0..10{add(true,Family::Natural,v,[100.0,400.0,1600.0][v%3],[5,9,17][v%3],false);}
    for v in 0..4{add(true,Family::Compound,v,[100.0,400.0][v%2],[5,9][v%2],false);}
    for(f,v,iso,n)in[(Family::Glint,0,100.0,9),(Family::Clipped,0,400.0,9),(Family::Colour,0,1600.0,17),(Family::Thin,0,400.0,17)]{add(true,f,v,iso,n,false);}
    add(true,Family::Flat,4,100.0,5,true);add(true,Family::Scale,0,400.0,5,true);
    add(false,Family::Flat,0,1600.0,17,false);add(false,Family::Flat,3,400.0,65,false);
    for(f,v,iso,n)in[(Family::Fork,0,100.0,33),(Family::Polygon,0,400.0,17),(Family::Glint,2,1600.0,17),
        (Family::Clipped,2,400.0,17),(Family::Colour,2,100.0,9),(Family::Thin,2,100.0,65)]{add(false,f,v,iso,n,false);}
    add(false,Family::Flat,4,400.0,5,true);add(false,Family::Scale,3,400.0,5,true);
    assert_eq!(out.iter().filter(|c|c.training).count(),24);assert_eq!(out.iter().filter(|c|!c.training).count(),10);out
}
fn sha_bytes(bytes:&[u8])->String {let mut h=Sha256::new();h.update(bytes);h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn hash16(v:&[u16])->String{let mut h=Sha256::new();for x in v{h.update(x.to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn hash32(v:&[f32])->String{let mut h=Sha256::new();for x in v{h.update(x.to_bits().to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn noise_salt(case:&Case)->u32{u32::from_le_bytes(Sha256::digest(case.id.as_bytes())[..4].try_into().unwrap())}
struct Textures { tiles:Vec<Vec<f32>>, manifest:Value, sha:String }
fn textures(path:&Path,training:bool)->Textures{
    let raw=std::fs::read(path).unwrap();let m:Value=serde_json::from_slice(&raw).unwrap();
    assert_eq!(m["split"],if training{"training"}else{"heldout"});assert_eq!(m["resized"],false);assert_eq!(m["raw_reads"],false);
    let rows=m["tiles"].as_array().unwrap();assert_eq!(rows.len(),if training{12}else{4});
    let tiles=rows.iter().map(|r|{assert_eq!(r["shape"],json!([CH,CW,3]));assert_eq!(r["dtype"],"<f4");
        let bytes=std::fs::read(r["file"].as_str().unwrap()).unwrap();assert_eq!(sha_bytes(&bytes),r["sha256"]);
        let a=bytes.chunks_exact(4).map(|b|f32::from_le_bytes(b.try_into().unwrap())).collect::<Vec<_>>();
        assert_eq!(a.len(),CH*CW*3);assert!(a.iter().all(|v|v.is_finite()&&*v>=0.0&&*v<=1.0));a}).collect();
    Textures{tiles,manifest:m,sha:sha_bytes(&raw)}
}
fn phase(x:usize,y:usize)->CfaPlane{match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn channel(x:usize,y:usize)->usize{match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn scramble(mut x:u32)->u32{x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn normal(x:usize,y:usize,k:usize,salt:u32)->f32{let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^salt;
    let u=(scramble(s)as f64+0.5)/4294967296.0;let v=(scramble(s^0xa73126bd)as f64+0.5)/4294967296.0;
    ((-2.0*u.ln()).sqrt()*(std::f64::consts::TAU*v).cos())as f32}
fn mask(b:bool)->f32{if b{1.0}else{0.0}}
fn bump(x:f32,y:f32,cx:f32,cy:f32,sx:f32,sy:f32)->f32{(-0.5*(((x-cx)/sx).powi(2)+((y-cy)/sy).powi(2))).exp()}
fn pupil(case:&Case)->Vec<[f32;2]>{let mut p=Vec::new();for j in 0..32{
    let a=(j as f32+0.5)/32.0;let r=if case.training&&case.variant%3==2{(0.45f32.powi(2)+(1.0-0.45f32.powi(2))*a).sqrt()}else{a.sqrt()};
    let theta=j as f32*PI*(3.0-5.0f32.sqrt())+0.37;let(x,y)=(r*theta.cos(),r*theta.sin());
    for sign in [1.0,-1.0]{let(mut x,mut y)=(x*sign,y*sign);if case.training&&case.variant%3==1{y*=0.55;let(s,c)=0.6f32.sin_cos();(x,y)=(c*x-s*y,s*x+c*y);}
        if case.training||x<=0.45{p.push([x,y]);}}}assert!(p.len()>=32);p}
fn sample(v:&[f32],w:usize,h:usize,channels:usize,x:f32,y:f32,c:usize)->f32{
    let(x,y)=(x.clamp(0.0,(w-1)as f32),y.clamp(0.0,(h-1)as f32));let(ix,iy)=(x.floor()as usize,y.floor()as usize);let(fx,fy)=(x-ix as f32,y-iy as f32);
    let row=|yy|{v[(yy*w+ix)*channels+c]*(1.0-fx)+v[(yy*w+(ix+1).min(w-1))*channels+c]*fx};row(iy)*(1.0-fy)+row((iy+1).min(h-1))*fy
}
// Texture channels are deliberately treated as synthetic camera-linear values, not recovered real radiance.
fn layers(case:&Case,t:&Textures,x:f32,y:f32,c:usize)->(f32,f32,f32,f32,f32){
    let v=case.variant as f32;let tau=2.0*PI;let b=[0.04,0.20,0.60,0.80,0.25][case.variant.min(4)];
    match case.family{
    Family::Flat=>(0.0,b,0.0,b,0.0),
    Family::Natural|Family::Fork|Family::Polygon=>{
        let a=match case.family{
            Family::Fork=>{let center=96.0+0.40*(y-80.0).abs();mask((x-center).abs()<3.5||(x-(192.0-center)).abs()<3.5)},
            Family::Polygon=>{let edge=100.0+8.0*((y/11.0).fract()-0.5);mask(x>edge&&y>39.0&&y<140.0)},
            _=>match case.variant%3{0=>mask(x+(v-4.0)*0.06*(y-88.0)>96.0),1=>mask(((x-96.0)/35.0).powi(2)+((y-88.0)/40.0).powi(2)<1.0),_=>mask((x-96.0-8.0*((y-88.0)/27.0).sin()).abs()<8.0)}
        };
        let nt=&t.tiles[case.variant%t.tiles.len()];let ft=&t.tiles[(case.variant+5)%t.tiles.len()];
        let nd=0.20*sample(nt,CW,CH,3,x,y,c);let fd=0.24*sample(ft,CW,CH,3,x,y,c);
        let (nb,fb)=if case.variant%2==0{(0.08,0.50)}else{(0.45,0.10)};(a,nb,nd,fb,fd)
    },
    Family::Compound=>{let a=mask(x>92.0+12.0*((y-70.0)/(23.0+v)).sin());
        let near=[0.05,0.04,0.06][c]*(tau*(0.014*x+0.00018*x*x+0.019*y)+0.2*v).cos();
        let far=[0.06,0.055,0.04][c]*((tau*(0.009*x+0.00014*y*y)).sin()*(tau*(0.022*y+0.00012*x*y)).cos());(a,0.24,near,0.37,far)},
    Family::Thin=>{let center=94.0+11.0*((y-87.0)/(19.0+v)).sin();let a=mask((x-center).abs()<3.0+v*0.25);
        let near=[0.09,0.07,0.08][c]*if ((y/(3.5+v*0.3)).floor()as i32)%2==0{1.0}else{-1.0};
        let radius=((x-106.0).powi(2)+(y-83.0).powi(2)).sqrt();let far=[0.055,0.065,0.05][c]*(tau*0.025*radius+0.43).cos();(a,0.28,near,0.18,far)},
    Family::Glint|Family::Clipped=>{let a=mask(x>116.0+6.0*((y-80.0)/(17.0+v)).sin());
        let near=[0.045,0.04,0.055][c]*mask((x-20.0).rem_euclid(8.0)<2.1||(y-21.0).rem_euclid(11.0)<2.1);
        let peak=if case.family==Family::Clipped{2.4}else{0.65};let far=peak*bump(x,y,86.0+2.0*v,83.0+v,1.6,1.8);(a,0.22,near,0.17,far)},
    Family::Colour=>{let mut nd=0.0;let centres=if case.training{[[65.0,63.0],[101.0,63.0],[65.0,107.0],[101.0,107.0]]}else{[[59.0,53.0],[82.0,72.0],[100.0,107.0],[71.0,127.0]]};
        for(j,[cx,cy])in centres.into_iter().enumerate(){let(dx,dy)=(x-cx,y-cy);let(s,co)=(0.31*j as f32+0.17*v).sin_cos();
            let amplitude=if case.training{[0.055,0.012,0.038]}else{[0.065,0.004,0.050]};
            nd+=amplitude[c]*(if(j+c)%2==0{1.0}else{-1.0})*bump(co*dx-s*dy,s*dx+co*dy,0.0,0.0,1.6,5.5);}
        (mask(x<113.0),0.18,nd,0.18,[0.025,0.01,0.045][c]*mask((x-124.0).abs()<2.0&&y>51.0&&y<124.0))},
    Family::Scale=>unreachable!()}
}
struct Latent{alpha:Vec<f32>,near:Vec<f32>,far:Vec<f32>,base:Vec<f32>,near_detail:Vec<f32>,far_detail:Vec<f32>}
fn latent(case:&Case,t:&Textures)->Latent{let n=CW*CH;let mut l=Latent{alpha:vec![0.0;n],near:vec![0.0;n*3],far:vec![0.0;n*3],base:vec![0.0;n*3],near_detail:vec![0.0;n*3],far_detail:vec![0.0;n*3]};
    for y in 0..CH{for x in 0..CW{for c in 0..3{let(a,nb,nd,fb,fd)=layers(case,t,x as f32,y as f32,c);let j=y*CW+x;l.alpha[j]=a;l.near[j*3+c]=a*(nb+nd);l.far[j*3+c]=fb+fd;l.base[j*3+c]=a*nb+(1.0-a)*fb;l.near_detail[j*3+c]=a*nd;l.far_detail[j*3+c]=(1.0-a)*fd;}}}l}
fn blur(v:&[f32])->Vec<f32>{let mut k=[0.0;7];let mut mass=0.0;for(i,w)in k.iter_mut().enumerate(){*w=(-0.5*((i as f32-3.0)/0.7).powi(2)).exp();mass+=*w;}for w in &mut k{*w/=mass;}
    let mut tmp=vec![0.0;v.len()];let mut out=vec![0.0;v.len()];for y in 0..CH{for x in 0..CW{for c in 0..3{for(j,w)in k.iter().enumerate(){let xx=(x as isize+j as isize-3).clamp(0,CW as isize-1)as usize;tmp[(y*CW+x)*3+c]+=w*v[(y*CW+xx)*3+c];}}}}
    for y in 0..CH{for x in 0..CW{for c in 0..3{for(j,w)in k.iter().enumerate(){let yy=(y as isize+j as isize-3).clamp(0,CH as isize-1)as usize;out[(y*CW+x)*3+c]+=w*tmp[(yy*CW+x)*3+c];}}}}out}
fn render(case:&Case,l:&Latent,points:&[[f32;2]],focus:f32)->Vec<f32>{let mut out=vec![0.0;CW*CH*3];
    let depth_near=0.78;let depth_far=0.18;let magnitude=if case.variant%2==0{14.0}else{22.0};let ns=magnitude*(focus-depth_near);let fs=magnitude*(focus-depth_far);
    for y in 0..CH{for x in 0..CW{for &[ux,uy]in points{let(nx,ny)=(x as f32+ns*ux,y as f32+ns*uy);let(fx,fy)=(x as f32+fs*ux,y as f32+fs*uy);
        let a=sample(&l.alpha,CW,CH,1,nx,ny,0);for c in 0..3{out[(y*CW+x)*3+c]+=sample(&l.near,CW,CH,3,nx,ny,c)+(1.0-a)*sample(&l.far,CW,CH,3,fx,fy,c);}}
        for c in 0..3{out[(y*CW+x)*3+c]/=points.len()as f32;}}}blur(&out)
}
fn cut(v:&[f32],w:usize,case:&Case)->Vec<f32>{let c=case.crop();let mut out=Vec::with_capacity(4*c.width*c.height*3);for y in 16..16+2*c.height{out.extend_from_slice(&v[(y*w+16)*3..(y*w+16+2*c.width)*3]);}out}
// Exact Gaussian convolution of a Gaussian-windowed sinusoid, no ray loop.
fn gabor(case:&Case,x:f32,y:f32,c:usize,focus:Option<f32>,which:Option<usize>)->f32{
    let(w,h)=case.size();let mut sum=0.0;for j in 0..8{if which.is_some_and(|v|j%2!=v){continue;}
        let cx=w as f32*(0.15+0.23*(j%4)as f32);let cy=h as f32*(if j<4{0.30}else{0.70});
        let lambda=4.0*2.0f32.powi(j as i32);let s=if j<4{70.0}else{170.0};let angle=0.23*j as f32+0.11*case.variant as f32;
        let omega=2.0*PI/lambda;let(wx,wy)=(omega*angle.cos(),omega*angle.sin());let(dx,dy)=(x-cx,y-cy);
        let sigma2=0.7f32.powi(2)+focus.map_or(0.0,|f|(70.0*(f-if j%2==0{0.22}else{0.78})).powi(2));
        let s2=s*s;let broad=s2+sigma2;let ratio=s2/broad;
        let envelope=ratio*(-0.5*(dx*dx+dy*dy)/broad-0.5*sigma2*ratio*(wx*wx+wy*wy)).exp();
        sum+=[0.040,0.034,0.044][c]*envelope*(ratio*(wx*dx+wy*dy)+0.31*j as f32).cos();
    }sum
}
fn transforms(case:&Case)->Vec<Similarity>{(0..case.n).map(|k|{let j=2.0*k as f64/(case.n-1)as f64-1.0;
    Similarity{a:Cx::new(1.0+0.00030*j,0.00020*j),b:Cx::new(0.22*j,-0.14*j)}}).collect()}
struct Generated{frames:Vec<Frame>,transforms:Vec<Similarity>,truth:Vec<f32>,base:Vec<f32>,near_detail:Vec<f32>,far_detail:Vec<f32>,clipped:[usize;4],pupil_samples:usize}
fn generate(case:&Case,t:&Textures)->Generated{
    let(w,h)=case.size();let (truth,base,near_detail,far_detail,latent,points)=if !case.large{
        let l=latent(case,t);let all=l.base.iter().zip(&l.near_detail).zip(&l.far_detail).map(|((b,n),f)|b+n+f).collect::<Vec<_>>();
        (cut(&blur(&all),w,case),cut(&blur(&l.base),w,case),cut(&blur(&l.near_detail),w,case),cut(&blur(&l.far_detail),w,case),Some(l),pupil(case))
    }else{
        let n=4*case.crop().width*case.crop().height*3;let mut a=vec![0.25;n];let b=a.clone();let mut nd=vec![0.0;n];let mut fd=nd.clone();let nw=2*case.crop().width;
        if case.family==Family::Scale{for yy in 0..2*case.crop().height{for xx in 0..nw{for c in 0..3{let j=(yy*nw+xx)*3+c;nd[j]=gabor(case,(xx+16)as f32,(yy+16)as f32,c,None,Some(0));fd[j]=gabor(case,(xx+16)as f32,(yy+16)as f32,c,None,Some(1));a[j]+=nd[j]+fd[j];}}}}
        (a,b,nd,fd,None,Vec::new())
    };
    let ts=transforms(case);let noise=profile::noise_model_for("ILCE-7CM2",Some(case.iso),levels());let mut frames=Vec::new();let mut clipped=[0;4];
    // Independent deterministic draw family per full case ID, not shared variant.
    let salt=noise_salt(case);
    for(k,&transform)in ts.iter().enumerate(){let image=latent.as_ref().map(|l|render(case,l,&points,case.focus(k)));let active=Region{x:7,y:11,width:w,height:h};let stride=w+29;let bh=h+29;
        let mut f=Frame{data:vec![64999;stride*bh],stride,buffer_height:bh,active,levels:levels(),iso:Some(case.iso),wb_coeffs:[WB[0],1.0,WB[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-cross-scale-{}-{k}.ARW",case.id))};assert!(!f.path.exists());
        let det=transform.a.re*transform.a.re+transform.a.im*transform.a.im;
        for y in 0..h{for x in 0..w{let u=x as f64-w as f64/2.0-2.0*transform.b.re;let v=y as f64-h as f64/2.0-2.0*transform.b.im;
            let wx=(w as f64/2.0+(transform.a.re*u+transform.a.im*v)/det)as f32;let wy=(h as f64/2.0+(-transform.a.im*u+transform.a.re*v)/det)as f32;let c=channel(x,y);
            let radiance=if let Some(ref image)=image{sample(image,w,h,3,wx,wy,c)}else if case.family==Family::Flat{0.25}else{0.25+gabor(case,wx,wy,c,Some(case.focus(k)),None)};
            let signal=radiance*levels().range()/WB[c];let value=512.0+signal+normal(x,y,k,salt)*noise.sigma(phase(x,y),signal);
            assert!(value.is_finite());let code=value.round().clamp(0.0,levels().white)as u16;if code>=levels().white as u16{clipped[(y%2)*2+x%2]+=1;}
            f.data[(active.y+y)*stride+active.x+x]=code;
        }}frames.push(f);
    }
    if case.family==Family::Clipped{assert!(clipped.iter().sum::<usize>()>0,"clipped control inactive");}else{assert_eq!(clipped.iter().sum::<usize>(),0,"unexpected clipping");}
    Generated{frames,transforms:ts,truth,base,near_detail,far_detail,clipped,pupil_samples:points.len()}
}
fn metadata(case:&Case,g:&Generated,t:&Textures)->Value{json!({"id":case.id,"training":case.training,"family":case.family.name(),"variant":case.variant,"iso":case.iso,"n":case.n,"bands":case.bands(),"large":case.large,
    "crop_quad_xywh":[case.crop().x,case.crop().y,case.crop().width,case.crop().height],"source_active_wh":case.size(),
    "truth_sha256":hash32(&g.truth),"original_source_sha256":g.frames.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>(),"clipped_original_samples":g.clipped,
    "pupil_samples":g.pupil_samples,"pupil":if case.large{"analytic Gaussian, no finite pupil"}else if !case.training{"clipped disk x<=.45"}else{["circular disk","rotated ellipse","annulus"][case.variant%3]},
    "focus_schedule":(0..case.n).map(|k|case.focus(k)).collect::<Vec<_>>(),"noise_salt":noise_salt(case),"noise_salt_rule":"first four SHA256(case ID) bytes as little-endian u32",
    "synthetic_texture_manifest_sha256":t.sha,"noise_after_signal":true,"calibration_validation":false,
    "seven_band_scope":if case.large{"analytic planar multiscale support test; no occlusion/optical calibration claim"}else{"compact finite-pupil layered radiance; discretization is an augmentation, not calibrated optics"}})}
