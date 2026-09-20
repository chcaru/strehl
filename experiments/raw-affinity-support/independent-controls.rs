// Independently adapted retained u16 truth fixtures; no execution by this author.
use super::{compare_generated, compare_generated_forced, Comparison, Mode};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{CfaPlane,align::{Cx,Similarity},noise::{Levels,NoiseModel},
    profile,pyramid::MergeConfig};
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
enum Scene {Flat,GlintDepth,NoGlintDepth,TrueRadial,ThinDepth,ColourOnly,GlintThin,NoGlintThin}
impl Scene {fn name(self)->&'static str {match self {Self::Flat=>"flat",Self::GlintDepth=>"glint-depth-step",Self::NoGlintDepth=>"no-glint-depth-twin",Self::TrueRadial=>"true-coloured-radial",Self::ThinDepth=>"equal-mean-thin-depth",Self::ColourOnly=>"constant-green-colour",Self::GlintThin=>"glint-thin-depth",Self::NoGlintThin=>"no-glint-thin-twin"}}}

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
        Scene::GlintThin|Scene::NoGlintThin=>{
            let d=k.map_or(0.0,|j|j as f64);
            let sx=1.8+8.0*d;let sy=1.8+0.15*d;
            let glint=if scene==Scene::NoGlintThin {0.0} else {[0.50,0.52,0.48][c]*1.8*1.8/(sx*sy)
                *elliptical(x-122.0,y-120.0,[0.48,0.70,0.92][c],sx,sy)};
            let far=[0.16,0.17,0.19][c]+glint+0.01
                *(-0.5*(TAU*0.02*(0.65+1.1*d)).powi(2)).exp()
                *(TAU*0.02*(0.8*x+0.6*y)+0.37).cos();
            let sigma=0.65+1.1*k.map_or(0.0,|j|(j as f64-4.0).abs());
            let width=(1.2f64.powi(2)+sigma*sigma).sqrt();
            let line=[0.12,0.14,0.11][c]*1.2/width*(-0.5*((y-138.0)/width).powi(2)).exp();
            let radius=(3.0*sigma).ceil() as i32;
            let mut mass=0.0;let mut coverage=0.0;let mut premult=0.0;
            for dx in -radius..=radius {let ww=(-0.5*(dx as f64/sigma).powi(2)).exp();mass+=ww;
                let xx=x+dx as f64;if xx>=164.0 {coverage+=ww;
                    premult+=ww*([0.24,0.26,0.30][c]+line*(1.0+0.2*(TAU*0.035*xx).cos()));}}
            premult/mass+(1.0-coverage/mass)*far
        },
        Scene::GlintDepth|Scene::NoGlintDepth=>{
            let d=k.map_or(0.0,|j|j as f64);
            let sx=1.8+8.0*d;let sy=1.8+0.15*d;
            let glint=if scene==Scene::NoGlintDepth {0.0} else {[0.50,0.52,0.48][c]*1.8*1.8/(sx*sy)
                *elliptical(x-122.0,y-120.0,[0.48,0.70,0.92][c],sx,sy)};
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
    fixture_world(scene,k,t,iso,noise,add_noise,false)
}
fn fixture_world(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel,add_noise:bool,same_world:bool)->Frame {
    fixture_variant(scene,k,t,iso,noise,add_noise,same_world,false)
}
fn nuisance(c:usize,k:Option<usize>)->f64 {
    let h=k.map_or(0.5,|j|{let u=j as f64/4.0;u*u*(3.0-2.0*u)});
    [0.10,0.12,0.09][c]*h
}
fn fixture_variant(scene:Scene,k:usize,t:Similarity,iso:f32,noise:&NoiseModel,add_noise:bool,same_world:bool,ramp:bool)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,
        levels:levels(),iso:Some(iso),wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],
        xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),
        path:std::env::current_dir().unwrap().join(format!("nonexistent-independent-raw-affinity-{}-{k}.ARW",scene.name()))};
    assert!(!f.path.exists());let determinant=t.a.re*t.a.re+t.a.im*t.a.im;
    for y in 0..H {for x in 0..W {
        // Explicit inverse of the native pull; no interpolated source image.
        let u=x as f64-W as f64/2.0-2.0*t.b.re;let v=y as f64-H as f64/2.0-2.0*t.b.im;
        let wx=W as f64/2.0+(t.a.re*u+t.a.im*v)/determinant;
        let wy=H as f64/2.0+(-t.a.im*u+t.a.re*v)/determinant;
        let signal=((radiance(scene,channel(x,y),wx,wy,if same_world {None} else {Some(k)})+if ramp {nuisance(channel(x,y),Some(k))}else{0.0})*f64::from(levels().range())/f64::from(GAIN[channel(x,y)])) as f32;
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
const INTERIOR:Window=Window{name:"whole-interior",x0:40,y0:44,x1:280,y1:244};
const FLAT:Window=Window{name:"flat-interior",x0:38,y0:42,x1:280,y1:244};
#[derive(Clone)]
struct Score {rgb:f64,chroma:f64,recovery:[f64;3],truth_sd:[f64;3]}
fn score(scene:Scene,rgb:&[f32],window:Window)->Score {score_at(scene,rgb,window,false,crop())}
fn score_at(scene:Scene,rgb:&[f32],window:Window,ramp:bool,rect:align_cmd::CropRect)->Score {
    let w=2*rect.width;let h=2*rect.height;
    assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    assert!(window.x0>=2*rect.x && window.y0>=2*rect.y && window.x1<=2*rect.x+w && window.y1<=2*rect.y+h);
    let mut error=0.0;let mut chroma=0.0;let mut sums=[[0.0;5];3];
    let n=((window.x1-window.x0)*(window.y1-window.y0)) as f64;
    for y in window.y0..window.y1 {for x in window.x0..window.x1 {
        let mut e=[0.0;3];let index=((y-2*rect.y)*w+x-2*rect.x)*3;
        for c in 0..3 {
            let truth=radiance(scene,c,x as f64,y as f64,None)+if ramp {nuisance(c,None)}else{0.0};let value=f64::from(rgb[index+c]);
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
fn recovery_pass(b:&Score,c:&Score)->bool {(0..3).all(|j|b.recovery[j]>=0.5 && c.recovery[j].max(0.0).min(1.0)>=0.98*b.recovery[j].min(1.0))}
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

// Independent f64 literal enumeration: this is an arithmetic oracle, not a
// second image algorithm or an independent physical noise calibration.
fn allowed(a:[usize;4],b:[usize;4])->bool {
    let ca=[a[0] as f64+(a[2]-1) as f64/2.0,a[1] as f64+(a[3]-1) as f64/2.0];
    let cb=[b[0] as f64+(b[2]-1) as f64/2.0,b[1] as f64+(b[3]-1) as f64/2.0];
    (ca[0]-cb[0]).abs()<=32.0 && (ca[1]-cb[1]).abs()<=32.0
}
fn literal_affinity(means:&[Vec<[f32;4]>],p:usize,q:usize)->f64 {
    if p==q{return 1.0;}
    let mut dot=0.0;let mut np=0.0;let mut nq=0.0;
    for k in 1..means.len(){for c in 0..4{
        let a=f64::from(means[k][p][c])-f64::from(means[k-1][p][c]);
        let b=f64::from(means[k][q][c])-f64::from(means[k-1][q][c]);
        dot+=a*b;np+=a*a;nq+=b*b;
    }}
    if np==0.0 || nq==0.0{0.0}else{(dot/(np*nq).sqrt()).clamp(0.0,1.0).powi(2)}
}
fn operator_controls()->Value {
    use super::{BlockGrid,block_means4,build_affinity,pool_fields};
    let (w,h)=(83usize,57usize);let g=BlockGrid::new(w,h).unwrap();
    let rects=(0..8).flat_map(|by|(0..11).map(move|bx|[8*bx,8*by,8.min(w-8*bx),8.min(h-8*by)])).collect::<Vec<_>>();
    assert_eq!(g.rects,rects);assert_eq!((g.width,g.height,g.cols,g.rows),(w,h,11,8));
    assert_eq!(g.areas,rects.iter().map(|r|r[2]*r[3]).collect::<Vec<_>>());
    let planes=(0..4).map(|c|(0..w*h).map(|i|((i%w) as f32-31.0)*(c+1) as f32-0.25*(i/w) as f32).collect()).collect::<Vec<Vec<f32>>>();
    let untouched=planes.clone();let m=block_means4(&planes,&g).unwrap();
    for (p,&[x,y,bw,bh]) in rects.iter().enumerate(){for c in 0..4{
        let mut sum=0.0f64;for yy in y..y+bh{for xx in x..x+bw{sum+=f64::from(planes[c][yy*w+xx]);}}
        assert!((f64::from(m[p][c])-sum/(bw*bh) as f64).abs()<1e-6);
    }}assert_eq!(planes,untouched);
    let means=(0..5).map(|k|(0..rects.len()).map(|p|{
        let t=k as f32;let v=match p%5{0=>[t,2.0*t,0.0,-t],1=>[2.0*t,4.0*t,0.0,-2.0*t],
            2=>[-t,-2.0*t,0.0,t],3=>[t,0.0,0.0,t],_=>[0.0;4]};
        std::array::from_fn(|c|100.0+p as f32+v[c])
    }).collect::<Vec<_>>()).collect::<Vec<_>>();
    let original=means.clone();let a=build_affinity(&g,&means,Mode::Affinity).unwrap();
    let rev=build_affinity(&g,&means.iter().rev().cloned().collect::<Vec<_>>(),Mode::Affinity).unwrap();
    let all=build_affinity(&g,&means,Mode::AllAffinity).unwrap();let mut err=0.0f64;
    for p in 0..rects.len(){
        let expected=(0..rects.len()).filter(|&q|allowed(rects[p],rects[q])).collect::<Vec<_>>();
        assert_eq!(a.neighbors[p].iter().map(|v|v.0).collect::<Vec<_>>(),expected);
        assert_eq!(all.neighbors[p].iter().map(|v|v.0).collect::<Vec<_>>(),expected);
        for ((&(q,v),&(qr,vr)),&(_,va)) in a.neighbors[p].iter().zip(&rev.neighbors[p]).zip(&all.neighbors[p]){
            assert_eq!(q,qr);err=err.max((f64::from(v)-literal_affinity(&means,p,q)).abs());
            assert!((v-vr).abs()<2e-6);assert_eq!(va,1.0);
        }
    }
    assert!(err<2e-6);assert_eq!(means,original);
    let lookup=|p:usize,q:usize|a.neighbors[p].iter().find(|v|v.0==q).unwrap().1;
    assert!((lookup(0,1)-1.0).abs()<2e-6);assert_eq!(lookup(0,2),0.0);
    assert_eq!(lookup(0,3),0.0);assert_eq!(lookup(0,4),0.0);assert_eq!(lookup(4,4),1.0);
    let e=(0..w*h).map(|i|1.0+(i%w) as f32*0.75+(i/w) as f32*0.125).collect::<Vec<_>>();
    let f=(0..w*h).map(|i|2.0+((i*17)%31) as f32*0.25).collect::<Vec<_>>();
    let (pe,pf)=pool_fields(&a,&e,&f).unwrap();let mut pooled_error=0.0f64;
    for p in 0..rects.len(){let mut es=0.0;let mut fs=0.0;let mut denominator=0.0;
        for q in 0..rects.len(){if !allowed(rects[p],rects[q]){continue;}
            let weight=literal_affinity(&means,p,q);let [x,y,bw,bh]=rects[q];
            for yy in y..y+bh{for xx in x..x+bw{es+=weight*f64::from(e[yy*w+xx]);fs+=weight*f64::from(f[yy*w+xx]);denominator+=weight;}}
        }
        let [x,y,bw,bh]=rects[p];for yy in y..y+bh{for xx in x..x+bw{
            pooled_error=pooled_error.max((f64::from(pe[yy*w+xx])-es/denominator).abs());
            pooled_error=pooled_error.max((f64::from(pf[yy*w+xx])-fs/denominator).abs());
        }}
    }assert!(pooled_error<1e-4);
    let (se,sf)=pool_fields(&a,&e.iter().map(|v|7.0*v).collect::<Vec<_>>(),&f.iter().map(|v|7.0*v).collect::<Vec<_>>()).unwrap();
    assert!(worst(&se,&pe.iter().map(|v|7.0*v).collect::<Vec<_>>())<0.001);
    assert!(worst(&sf,&pf.iter().map(|v|7.0*v).collect::<Vec<_>>())<0.001);
    let constant=vec![vec![[100.0;4];rects.len()];5];let zero=build_affinity(&g,&constant,Mode::Affinity).unwrap();
    assert!(zero.neighbors.iter().enumerate().all(|(p,row)|row.iter().all(|&(q,v)|v==if p==q{1.0}else{0.0})));
    let (self_e,_)=pool_fields(&zero,&e,&f).unwrap();assert!(worst(&self_e,&e)>1.0,"zero temporal norm still self-block-pools");
    let small=BlockGrid::new(16,8).unwrap();let profiles=[[0.0f32,4.0,0.0,0.0,0.0],[0.0,0.0,0.0,4.0,0.0]];
    let plain=(0..5).map(|k|(0..2).map(|p|[100.0+profiles[p][k];4]).collect::<Vec<_>>()).collect::<Vec<_>>();
    let ramps=[0.0f32,0.0,40.0,160.0,400.0];
    let common=(0..5).map(|k|(0..2).map(|p|[100.0+profiles[p][k]+ramps[k];4]).collect::<Vec<_>>()).collect::<Vec<_>>();
    let p=build_affinity(&small,&plain,Mode::Affinity).unwrap();let c=build_affinity(&small,&common,Mode::Affinity).unwrap();
    let before=p.neighbors[0].iter().find(|v|v.0==1).unwrap().1;let after=c.neighbors[0].iter().find(|v|v.0==1).unwrap().1;
    assert_eq!(before,0.0);assert!(after>0.9,"common temporal nuisance destroyer inactive");
    for bad in [f32::NAN,f32::INFINITY,-1.0]{let mut broken=e.clone();broken[3]=bad;assert!(pool_fields(&a,&broken,&f).is_err());
        let mut broken=f.clone();broken[7]=bad;assert!(pool_fields(&a,&e,&broken).is_err());}
    let mut bad_means=means.clone();bad_means[2][3][0]=f32::NAN;assert!(build_affinity(&g,&bad_means,Mode::Affinity).is_err());
    assert!(BlockGrid::new(0,h).is_err());assert!(pool_fields(&a,&e[..10],&f).is_err());
    let mut bad_planes=planes.clone();bad_planes[0][2]=f32::INFINITY;assert!(block_means4(&bad_planes,&g).is_err());
    json!({"affinity_oracle_max_abs":err,"pooled_oracle_max_abs":pooled_error,"odd_partial_grid":[w,h],
        "descriptor_reversal_only":true,"zero_norm_still_self_block_pools":true,
        "different_focus_profiles_common_ramp_affinity":[before,after],"source_means_unchanged":true,
        "interpretation":"Literal arithmetic/routing controls only; no calibration or source-ownership evidence"})
}

#[test]
fn independent_raw_affinity_operator_controls(){eprintln!("RAW_AFFINITY_OPERATOR {}",operator_controls());}

fn checks(c:&Comparison,frames:&[Frame],before:&[String],rect:align_cmd::CropRect){
    assert_eq!((c.native_width,c.native_height),(2*rect.width,2*rect.height));
    assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert!(c.non_finest_bit_exact);assert_eq!(c.frames.len(),frames.len());
    assert_eq!(c.baseline_planes4.len(),4);assert_eq!(c.candidate_planes4.len(),4);
    for p in c.baseline_planes4.iter().chain(&c.candidate_planes4){assert_eq!(p.len(),rect.width*rect.height);assert!(p.iter().all(|v|v.is_finite()));}
    assert_eq!(c.affinity.source_count,frames.len());assert_eq!((c.affinity.grid.width,c.affinity.grid.height),(rect.width,rect.height));
    for ((f,b),e) in frames.iter().zip(before).zip(&c.frames){
        assert_eq!(&hash(&f.data),b);assert_eq!(&e.source_sha256,b);assert!(e.source_unchanged && e.replay_exact);
        assert!(!e.beta.is_empty() && e.beta.iter().all(|v|v.is_finite() && *v>0.0));
        for h in e.known4_sha256.iter().chain([&e.guide_sha256,&e.variance_sha256,&e.descriptor_sha256,
            &e.canonical_energy_sha256,&e.canonical_floor_sha256,&e.pooled_energy_sha256,&e.pooled_floor_sha256,&e.weight_sha256]){assert_eq!(h.len(),64);}
    }
}
fn evidence(c:&Comparison)->Value{
    let mut nonself=0usize;let mut positive=0usize;let mut weight_sum=0.0f64;
    for (p,row) in c.affinity.neighbors.iter().enumerate(){for &(q,v) in row{if p!=q{nonself+=1;positive+=usize::from(v>0.0);weight_sum+=f64::from(v);}}}
    json!({"level_sizes":c.level_sizes,"non_finest_bit_exact":c.non_finest_bit_exact,
        "baseline_averaged_fraction":c.baseline_averaged_fraction,"candidate_averaged_fraction":c.candidate_averaged_fraction,
        "source_evidence":c.frames,"nonself_pairs":nonself,"positive_nonself_pairs":positive,"nonself_weight_sum":weight_sum,
        "changed_cfa_samples":c.baseline_planes4.iter().flatten().zip(c.candidate_planes4.iter().flatten()).filter(|(a,b)|a.to_bits()!=b.to_bits()).count()})
}
fn evaluate(scene:Scene,ramp:bool,rect:align_cmd::CropRect,c:&Comparison,flat:f64)->(Value,bool,bool){
    let windows:&[Window]=match scene{Scene::Flat=>&[FLAT],Scene::GlintThin=>&[FAN,CORE,EDGE,THIN_NEAR,JUNCTION,INTERIOR],
        Scene::NoGlintThin=>&[EDGE,THIN_NEAR,JUNCTION,INTERIOR],Scene::TrueRadial=>&[RADIAL,INTERIOR],_=>unreachable!()};
    let mut records=Vec::new();let mut pass=true;let mut exercised=true;
    for &window in windows{
        let b=score_at(scene,&c.baseline_rgb,window,ramp,rect);let a=score_at(scene,&c.candidate_rgb,window,ramp,rect);
        let component=matches!(window.name,"core"|"thin-near"|"real-coloured-rays");
        let live=!component || b.recovery.iter().all(|v|*v>=0.5);
        let mut bar=a.rgb<=1.02*b.rgb && (!component || recovery_pass(&b,&a));
        if scene==Scene::Flat || window.name=="real-coloured-rays"{bar &= a.chroma<=1.02*b.chroma;}
        if window.name=="fan"{bar &= a.rgb<=0.95*b.rgb;exercised &= b.rgb>2.0*flat;}
        pass &= bar && live;exercised &= live;
        records.push(json!({"name":window.name,"active_native_bounds":[window.x0,window.y0,window.x1,window.y1],
            "baseline":score_json(&b),"candidate":score_json(&a),"rgb_ratio":a.rgb/b.rgb,"chroma_ratio":a.chroma/b.chroma,
            "mandatory_component":component,"component_exercised":live,"quality_pass":bar && live}));
    }
    if scene!=Scene::Flat{
        exercised &= c.baseline_averaged_fraction[0]<1.0 && c.frames.windows(2).any(|e|e[0].guide_sha256!=e[1].guide_sha256);
    }
    if scene==Scene::GlintThin{
        exercised &= !exact(&c.baseline_planes4,&c.candidate_planes4)
            && c.affinity.neighbors.iter().enumerate().any(|(p,row)|row.iter().any(|&(q,v)|p!=q && v>0.0));
        let mut e=0.0;let mut count=0;for y in FAN.y0..FAN.y1{for x in FAN.x0..FAN.x1{for ch in 0..3{
            e+=(radiance(scene,ch,x as f64,y as f64,Some(4))-radiance(scene,ch,x as f64,y as f64,None)).powi(2);count+=1;
        }}}
        let error=(e/count as f64).sqrt();exercised &= error>2.0*flat;
        records.push(json!({"name":"unmerged_late_fan_commission","late_noiseless_ac_truth_rms":error,
            "same_iso_flat_baseline_rms":flat,"exercised":error>2.0*flat}));
    }
    (json!(records),pass,exercised)
}

#[test]
fn independent_raw_affinity_actual_truth_screen(){
    let out=PathBuf::from(std::env::var_os("STREHL_RAW_AFFINITY_SUPPORT_OUT").expect("root-owned unique output required"));
    std::fs::create_dir(&out).unwrap();let metric=commission();let ts=transforms();
    let mut records=Vec::new();let mut flat_errors=[0.0f64;2];let mut admitted=true;
    // Both flat controls precede every structure result.
    for (i,iso) in [100.0f32,400.0].into_iter().enumerate(){
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let frames=ts.iter().enumerate().map(|(k,&t)|fixture_variant(Scene::Flat,k,t,iso,&noise,true,false,false)).collect::<Vec<_>>();
        let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
        let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Affinity).unwrap();checks(&c,&frames,&before,crop());
        flat_errors[i]=score_at(Scene::Flat,&c.baseline_rgb,FLAT,false,crop()).rgb;
        let (windows,pass,exercised)=evaluate(Scene::Flat,false,crop(),&c,flat_errors[i]);admitted &= pass && exercised;
        let row=json!({"scene":"flat","iso":iso,"common_brightening":false,"crop":[7,9,145,125],
            "windows":windows,"quality_pass":pass,"fixture_exercised":exercised,"consumer":evidence(&c)});
        eprintln!("RAW_AFFINITY_CASE {}",row);records.push(row);
    }
    let mut placebo=Value::Null;let mut wrong_source_exercised=false;
    for (i,iso) in [100.0f32,400.0].into_iter().enumerate(){
        let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());
        for (scene,ramp) in [(Scene::GlintThin,false),(Scene::GlintThin,true),(Scene::NoGlintThin,false),
            (Scene::NoGlintThin,true),(Scene::TrueRadial,false)]{
            let frames=ts.iter().enumerate().map(|(k,&t)|fixture_variant(scene,k,t,iso,&noise,true,false,ramp)).collect::<Vec<_>>();
            let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Affinity).unwrap();checks(&c,&frames,&before,crop());
            let (windows,pass,exercised)=evaluate(scene,ramp,crop(),&c,flat_errors[i]);admitted &= pass && exercised;
            let row=json!({"scene":scene.name(),"iso":iso,"common_brightening":ramp,"crop":[7,9,145,125],
                "windows":windows,"quality_pass":pass,"fixture_exercised":exercised,"consumer":evidence(&c)});
            eprintln!("RAW_AFFINITY_CASE {}",row);records.push(row);
            if iso==100.0 && scene==Scene::GlintThin && ramp{
                let off=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Off).unwrap();checks(&off,&frames,&before,crop());
                assert!(exact(&off.baseline_planes4,&off.candidate_planes4) && exact(&off.baseline_planes4,&c.baseline_planes4));
                assert!(off.baseline_rgb.iter().zip(&off.candidate_rgb).all(|(a,b)|a.to_bits()==b.to_bits()));
                assert!(off.frames.iter().all(|e|e.canonical_energy_sha256==e.pooled_energy_sha256 && e.canonical_floor_sha256==e.pooled_floor_sha256));
                let all=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::AllAffinity).unwrap();checks(&all,&frames,&before,crop());
                assert!(exact(&all.baseline_planes4,&c.baseline_planes4));
                let all_live=!exact(&all.candidate_planes4,&c.baseline_planes4) && all.frames.iter().any(|e|e.pooled_energy_sha256!=e.canonical_energy_sha256);
                let (all_windows,all_pass,all_exercised)=evaluate(scene,ramp,crop(),&all,flat_errors[i]);
                let wrong=compare_generated_forced(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Affinity,4).unwrap();checks(&wrong,&frames,&before,crop());
                assert!(exact(&wrong.baseline_planes4,&c.baseline_planes4));
                let bc=score_at(scene,&c.baseline_rgb,CORE,ramp,crop());let wc=score_at(scene,&wrong.candidate_rgb,CORE,ramp,crop());
                let bf=score_at(scene,&c.baseline_rgb,FAN,ramp,crop());let wf=score_at(scene,&wrong.candidate_rgb,FAN,ramp,crop());
                wrong_source_exercised=!exact(&wrong.candidate_planes4,&c.baseline_planes4)
                    && (wc.rgb>1.02*bc.rgb || wf.rgb>1.02*bf.rgb || !recovery_pass(&bc,&wc));
                admitted &= all_live && wrong_source_exercised;
                placebo=json!({"off_planes_and_rgb_exact":true,"all_affinity_live":all_live,"all_affinity_windows":all_windows,
                    "all_affinity_quality_pass_not_admission":all_pass,"all_affinity_exercised":all_exercised,
                    "all_affinity_consumer":evidence(&all),"forced_source":4,"forced_core":score_json(&wc),"forced_fan":score_json(&wf),
                    "forced_consumer":evidence(&wrong),"wrong_source_destroyer_exercised":wrong_source_exercised});
                let shifted=align_cmd::CropRect{x:8,y:9,width:145,height:125};
                let phase=compare_generated(&frames,&ts,shifted,&noise,MergeConfig::default(),Mode::Affinity).unwrap();checks(&phase,&frames,&before,shifted);
                let (windows,pass,exercised)=evaluate(scene,ramp,shifted,&phase,flat_errors[i]);admitted &= pass && exercised;
                let row=json!({"scene":"glint-thin-depth-block-phase","iso":iso,"common_brightening":ramp,"crop":[8,9,145,125],
                    "windows":windows,"quality_pass":pass,"fixture_exercised":exercised,"consumer":evidence(&phase),
                    "interpretation":"Grid anchored to cropped output; one-quad crop translation moves physical block boundaries"});
                eprintln!("RAW_AFFINITY_CASE {}",row);records.push(row);
            }
        }
    }
    assert_eq!(records.len(),13);
    let result=json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admitted,"sources":N,"metric_commission":metric,
        "cases":records,"placebos":placebo,"wrong_source_destroyer_exercised":wrong_source_exercised,
        "failure_rule":"Every scene, ISO, nuisance state and block phase must independently pass; no retuning or averaging failures",
        "interpretation":"Bounded known-truth falsifier. Shared injected noise validates the operator, not calibration. Common brightening is not depth ownership; no photographic or SOTA claim."});
    write(&out.join("screen.json"),&result);eprintln!("RAW_AFFINITY_SCREEN {}",json!({"photographic_replay_admitted":admitted}));
}
