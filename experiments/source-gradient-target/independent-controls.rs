// Independent target-only controls. No source image is reconstructed.
use super::{consumer,operator};
use operator::Gradient;
use serde_json::{json,Value};
use strehl_core::pyramid::{level_sizes,LevelSize,MergeConfig,Pyramid,Workspace};
use std::f64::consts::TAU;

const W:usize=160;
const H:usize=144;
const N:usize=5;
const DN:f64=14848.;
const GAIN:[f64;4]=[1.7,1.,1.,2.3];
const PHASE:[(usize,usize);4]=[(0,0),(1,0),(0,1),(1,1)];
type Targets=Vec<Vec<Gradient>>;
#[derive(Clone,Copy,Debug)]
enum Scene {Flat,Contact,NearFar}
#[derive(Clone,Copy)]
struct Window {name:&'static str,b:[usize;4]}
const WHOLE:Window=Window{name:"whole-interior",b:[38,42,280,244]};
const CORE:Window=Window{name:"contact-interior",b:[112,120,136,160]};
const SPILL:Window=Window{name:"contact-outside-spill",b:[142,118,164,162]};

fn emit(name:&str,mut value:Value) {
    value["canonical_consumer_qualified"]=json!(false);
    value["photographic_quality_admitted"]=json!(false);
    println!("SOURCE_GRADIENT_TARGET {}",json!({"name":name,"result":value}));
    if let Some(dir)=std::env::var_os("STREHL_SOURCE_GRADIENT_TARGET_OUT") {
        let dir=std::path::PathBuf::from(dir);std::fs::create_dir_all(&dir).unwrap();
        let file=std::fs::OpenOptions::new().write(true).create_new(true)
            .open(dir.join(format!("{name}.json"))).unwrap();
        serde_json::to_writer_pretty(file,&value).unwrap();
    }
}
fn scramble(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn noise(k:usize,c:usize,j:usize)->f64 {
    let s=(j as u32)^(k as u32).wrapping_mul(0x9e3779b9)
        ^(c as u32).wrapping_mul(0x85ebca6b)^0x31d59a67;
    let u=(f64::from(scramble(s))+0.5)/4294967296.;
    let v=(f64::from(scramble(s^0xa73126bd))+0.5)/4294967296.;
    (-2.*u.ln()).sqrt()*(TAU*v).cos()
}
fn cdf(z:f64)->f64 {
    let x=z.abs();let t=1./(1.+0.2316419*x);
    let p=1.-(-0.5*x*x).exp()/TAU.sqrt()*t*(0.319381530+t*(-0.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))));
    if z>=0. {p}else{1.-p}
}
fn component(which:usize,c:usize,x:f64,y:f64,k:Option<usize>)->f64 {
    let focus=if which==0 {0.}else{4.};
    let sigma=0.65+3.*k.map_or(0.,|j|(j as f64-focus).abs());
    let(f,a)=if which==0 {(0.10,[0.045,0.050,0.040][c])}else{(0.022,[0.090,0.100,0.085][c])};
    let(dx,dy,phase)=if which==0 {[(1.,0.,0.37),(0.8,0.6,1.13),(-0.6,0.8,2.07)][c]}
        else{[(0.,1.,0.81),(0.6,-0.8,1.71),(0.8,0.6,2.63)][c]};
    a*(-0.5*(TAU*f*sigma).powi(2)).exp()*(TAU*f*(dx*x+dy*y)+phase).cos()
}
fn radiance(scene:Scene,c:usize,x:f64,y:f64,k:Option<usize>)->f64 {
    match scene {
        Scene::Flat=>0.25,
        Scene::NearFar=>0.27+component(0,c,x,y,k)+component(1,c,x,y,k),
        Scene::Contact=>{
            let s=0.65+3.2*k.map_or(0.,|j|j as f64);
            let rect=(cdf((x-108.)/s)-cdf((x-140.)/s))*(cdf((y-116.)/s)-cdf((y-164.)/s));
            let(dx,dy,p)=[(1.,0.,0.37),(0.8,0.6,1.13),(-0.6,0.8,2.07)][c];
            0.18+[0.36,0.40,0.32][c]*rect+[0.045,0.055,0.050][c]
                *(-0.5*(TAU*0.075*s).powi(2)).exp()*(TAU*0.075*(dx*x+dy*y)+p).cos()
        }
    }
}
fn planes(scene:Scene,k:Option<usize>,noisy:bool)->Vec<Vec<f32>> {
    (0..4).map(|c|(0..W*H).map(|j|{
        let(ox,oy)=PHASE[c];let x=(2*(j%W)+ox)as f64;let y=(2*(j/W)+oy)as f64;
        let rgb=[0,1,1,2][c];let signal=radiance(scene,rgb,x,y,k)*DN/GAIN[c];
        let v=signal+if noisy {20.*noise(k.unwrap(),c,j)}else{0.};
        assert!(v>0.&&v<DN,"fixed source clipped");v as f32
    }).collect()).collect()
}
fn guides(frames:&[Vec<Vec<f32>>])->Vec<Vec<f32>> {
    frames.iter().map(|p|p[1].iter().zip(&p[2]).map(|(a,b)|0.5*(a+b)).collect()).collect()
}
fn fixture(scene:Scene,noisy:bool)->consumer::Comparison {
    let frames=(0..N).map(|k|planes(scene,Some(k),noisy)).collect::<Vec<_>>();
    let variance=vec![vec![if noisy {200.}else{0.};W*H];N];
    let out=consumer::compare(W,H,&frames,&guides(&frames),&variance,MergeConfig::default()).unwrap();
    assert_eq!(out.source_count,N);assert!(out.terminal_unchanged);
    assert_eq!(out.sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        vec![[160,144],[80,72],[40,36],[20,18],[10,9]]);
    assert_eq!(out.baseline.len(),4);assert_eq!(out.candidate.len(),4);
    for c in 0..4 {assert_eq!(out.baseline[c].len(),out.sizes.len());
        assert_eq!(out.candidate[c].len(),out.sizes.len());
        for k in 0..out.sizes.len() {
            assert_eq!(max_difference(&out.baseline[c][k],
                &difference(out.canonical_coefficients[c].level(k),out.sizes[k])),0.);
        }}
    out
}
// Independent row/column indexing; deliberately does not call operator::forward.
fn difference(v:&[f32],s:LevelSize)->Gradient {
    assert_eq!(v.len(),s.pixels());
    let mut dx=vec![0.;v.len()];let mut dy=dx.clone();
    for row in 0..s.height {for col in 0..s.width-1 {
        dx[row*s.width+col]=v[row*s.width+col+1]-v[row*s.width+col];
    }}
    for row in 0..s.height-1 {for col in 0..s.width {
        dy[row*s.width+col]=v[(row+1)*s.width+col]-v[row*s.width+col];
    }}Gradient{dx,dy}
}
fn pyramids(planes:&[Vec<f32>],sizes:&[LevelSize])->Vec<Pyramid> {
    let mut ws=Workspace::new(sizes);planes.iter().map(|v|{
        let mut p=Pyramid::zeros(sizes);p.build(v,&mut ws);p
    }).collect()
}
fn target(planes:&[Vec<f32>],sizes:&[LevelSize])->Targets {
    pyramids(planes,sizes).iter().map(|p|sizes.iter().enumerate()
        .map(|(k,s)|difference(p.level(k),*s)).collect()).collect()
}
fn max_difference(a:&Gradient,b:&Gradient)->f64 {
    a.dx.iter().zip(&b.dx).chain(a.dy.iter().zip(&b.dy))
        .map(|(a,b)|(f64::from(*a)-f64::from(*b)).abs()).fold(0.,f64::max)
}
fn edges(s:LevelSize,k:usize,c:usize,w:Window)->Vec<(usize,usize)> {
    let step=1usize<<(k+1);let(ox,oy)=PHASE[c];let[x0,y0,x1,y1]=w.b;
    let mut out=Vec::new();
    for y in 0..s.height {for x in 0..s.width {
        let xx=step*x+ox;let yy=step*y+oy;
        if xx<x0||xx>=x1||yy<y0||yy>=y1 {continue;}
        if x+1<s.width&&xx+step<x1 {out.push((0,y*s.width+x));}
        if y+1<s.height&&yy+step<y1 {out.push((1,y*s.width+x));}
    }}assert!(!out.is_empty(),"empty predeclared edge window");out
}
fn value(g:&Gradient,d:usize,j:usize)->f64 {f64::from(if d==0 {g.dx[j]}else{g.dy[j]})}
fn rms(a:&Gradient,t:&Gradient,e:&[(usize,usize)])->f64 {
    (e.iter().map(|&(d,j)|(value(a,d,j)-value(t,d,j)).powi(2)).sum::<f64>()/e.len()as f64).sqrt()
}
fn recovery(a:&Gradient,t:&Gradient,e:&[(usize,usize)])->(f64,f64) {
    let n=e.len()as f64;let(mut sy,mut st,mut tt,mut ty)=(0.,0.,0.,0.);
    for &(d,j)in e {let(y,t)=(value(a,d,j),value(t,d,j));sy+=y;st+=t;tt+=t*t;ty+=t*y;}
    let var=(tt-st*st/n).max(0.);if var<=1e-12 {(0.,0.)}else{((ty-st*sy/n)/var,(var/n).sqrt())}
}
fn retain(b:f64,c:f64)->bool {c.clamp(0.,1.)>=0.98*b.clamp(0.,1.)}
fn no_harm(b:f64,c:f64)->bool {c<=1.05*b+0.02}
fn errors(out:&consumer::Comparison,truth:&Targets,w:Window)->(Vec<Value>,bool) {
    let mut rows=Vec::new();let mut pass=true;
    for c in 0..4 {for k in 0..out.sizes.len()-1 {
        let e=edges(out.sizes[k],k,c,w);
        let b=rms(&out.baseline[c][k],&truth[c][k],&e);let a=rms(&out.candidate[c][k],&truth[c][k],&e);
        let good=no_harm(b,a);pass&=good;
        rows.push(json!({"channel":c,"level":k,"window":w.name,"edge_count":e.len(),
            "baseline_rmse_dn":b,"candidate_rmse_dn":a,"no_harm":good}));
    }}(rows,pass)
}

#[test]
fn a_target_identities() {
    for(w,h)in [(3,4),(4,3)] {
        let size=LevelSize{width:w,height:h};let v=(0..w*h).map(|j|(10*(j/w)+(j%w).pow(2))as f32).collect::<Vec<_>>();
        let actual=operator::forward(&v,&size).unwrap();let expected=difference(&v,size);
        assert_eq!(max_difference(&actual,&expected),0.);let masks=operator::edge_masks(&size);
        for j in 0..w*h {assert_eq!(masks[0][j],j%w<w-1);assert_eq!(masks[1][j],j/w<h-1);}
        let mut wrong=expected.clone();wrong.dx[0]=-wrong.dx[0];
        assert!(max_difference(&wrong,&expected)>0.02);
        wrong=expected.clone();wrong.dy[w+1]=0.;assert!(max_difference(&wrong,&expected)>0.02);
    }
    let sizes=level_sizes(32,32,7);let probs=[0.125f32,0.25,0.625];
    let images=(0..3).map(|i|(0..4).map(|c|(0..1024).map(|j|
        128.+((j*(i+1)+c*7)%31)as f32*0.125).collect()).collect::<Vec<Vec<f32>>>()).collect::<Vec<_>>();
    let mut accumulator=operator::Accumulator::new(&sizes,3).unwrap();
    let mut mixed=(0..4).map(|_|Pyramid::zeros(&sizes)).collect::<Vec<_>>();
    for i in 0..3 {
        let p=pyramids(&images[i],&sizes);
        let weights=sizes[..sizes.len()-1].iter().map(|s|vec![probs[i];s.pixels()]).collect::<Vec<_>>();
        accumulator.add(i,&p,&weights).unwrap();
        for c in 0..4 {for k in 0..sizes.len()-1 {for(v,a)in mixed[c].level_mut(k).iter_mut().zip(p[c].level(k)) {*v+=probs[i]*a;}}}
    }
    let actual=accumulator.finish().unwrap();let mut err=0.0f64;
    for c in 0..4 {for k in 0..sizes.len()-1 {err=err.max(max_difference(&actual.gradients[c][k],&difference(mixed[c].level(k),sizes[k])));}}
    assert!(err<=0.02);
    let repeated=vec![images[0].clone();3];let var=vec![vec![0.;1024];3];
    let same=consumer::compare(32,32,&repeated,&guides(&repeated),&var,MergeConfig::default()).unwrap();
    assert!(same.terminal_unchanged);
    for c in 0..4 {for k in 0..sizes.len() {assert!(max_difference(&same.baseline[c][k],&same.candidate[c][k])<=0.02);}}
    let flat=vec![vec![vec![2048.;1024];4];3];
    let unsupported=consumer::compare(32,32,&flat,&guides(&flat),&var,MergeConfig::default()).unwrap();
    assert!(unsupported.denominator.iter().flatten().all(|v|*v==0.));
    assert!(unsupported.candidate.iter().flatten().all(|g|g.dx.iter().chain(&g.dy).all(|v|*v==0.)));
    emit("arithmetic",json!({"mechanical_pass":true,"finite_edges_exact":true,"wrong_sign_and_missing_edge_rejected":true,
        "constant_unequal_membership_max_error_dn":err,"equal_source_target_identity":true,
        "natural_unsupported_mean_exercised":true,"reconstructed_image_identity_claimed":false}));
}

#[test]
fn b_flat_target_noise() {
    let mut cases=Vec::new();let mut all=true;
    for noisy in [false,true] {
        let out=fixture(Scene::Flat,noisy);let truth=target(&planes(Scene::Flat,None,false),&out.sizes);
        if !noisy {assert!(out.baseline.iter().flatten().chain(out.candidate.iter().flatten())
            .all(|g|g.dx.iter().chain(&g.dy).all(|v|*v==0.)));}
        let(rows,pass)=errors(&out,&truth,WHOLE);all&=pass;
        cases.push(json!({"noise_sigma_dn":if noisy{20.}else{0.},"levels":rows,"scientific_pass":pass}));
    }
    emit("flat",json!({"mechanical_pass":true,"flat_first":true,"scientific_pass":all,"cases":cases,
        "noise_scope":"known independent source draws; gradient target error, not sensor calibration"}));
}

#[test]
fn c_contact_join_screen() {
    let mut cases=Vec::new();let mut all=true;
    for noisy in [false,true] {
        let out=fixture(Scene::Contact,noisy);let truth=target(&planes(Scene::Contact,None,false),&out.sizes);
        let(whole,wh)=errors(&out,&truth,WHOLE);let(core,ch)=errors(&out,&truth,CORE);
        let mut joins=Vec::new();let mut recoveries=Vec::new();let(mut eligible,mut benefit,mut protected)=(true,true,true);
        for c in 0..4 {for k in [0,1] {
            let e=edges(out.sizes[k],k,c,SPILL);let mut je=0.;let mut jj=0.;let mut ee=0.;
            for &(d,j)in &e {
                let b=value(&out.baseline[c][k],d,j);let a=value(&out.candidate[c][k],d,j);let t=value(&truth[c][k],d,j);
                let join=b-a;let error=b-t;je+=join*error;jj+=join*join;ee+=error*error;
            }
            let b=(ee/e.len()as f64).sqrt();let j=(jj/e.len()as f64).sqrt();
            let alignment=if jj>0.&&ee>0. {je/(jj*ee).sqrt()}else{0.};
            let a=rms(&out.candidate[c][k],&truth[c][k],&e);
            let live=b>0.2&&j>0.05*b&&alignment>0.2;let gain=a<=0.95*b;
            eligible&=live;benefit&=gain;
            joins.push(json!({"channel":c,"level":k,"edge_count":e.len(),"baseline_error_dn":b,
                "candidate_error_dn":a,"join_rms_dn":j,"join_error_alignment":alignment,
                "spurious_join_exercised":live,"benefit_pass":gain}));
            let e=edges(out.sizes[k],k,c,CORE);let(rb,sd)=recovery(&out.baseline[c][k],&truth[c][k],&e);
            let(ra,_)=recovery(&out.candidate[c][k],&truth[c][k],&e);
            let live=rb>=0.5&&sd>1e-6;let pass=live&&retain(rb,ra);protected&=pass;
            recoveries.push(json!({"channel":c,"level":k,"baseline":rb,"candidate":ra,"truth_sd_dn":sd,"live":live,"retention_pass":pass}));
        }}
        let pass=wh&&ch&&eligible&&benefit&&protected;all&=pass;
        cases.push(json!({"noise_sigma_dn":if noisy{20.}else{0.},"whole":whole,"core":core,"joins":joins,
            "recoveries":recoveries,"positive_exercised":eligible,"benefit_pass":benefit,
            "preservation_pass":wh&&ch&&protected,"scientific_pass":pass}));
    }
    emit("contact",json!({"mechanical_pass":true,"scientific_pass":all,"cases":cases}));
}

fn component_target(which:usize,sizes:&[LevelSize])->Targets {
    let p=(0..4).map(|c|(0..W*H).map(|j|{
        let(ox,oy)=PHASE[c];let x=(2*(j%W)+ox)as f64;let y=(2*(j/W)+oy)as f64;
        (component(which,[0,1,1,2][c],x,y,None)*DN/GAIN[c])as f32
    }).collect()).collect::<Vec<Vec<f32>>>();target(&p,sizes)
}
fn joint(y:&Gradient,a:&Gradient,b:&Gradient,e:&[(usize,usize)])->[f64;2] {
    let mut s=[0.;8];let n=e.len()as f64;
    for &(d,j)in e {let(a,b,y)=(value(a,d,j),value(b,d,j),value(y,d,j));
        for(p,v)in s.iter_mut().zip([a,b,y,a*a,b*b,a*b,a*y,b*y]){*p+=v;}}
    let aa=s[3]-s[0]*s[0]/n;let bb=s[4]-s[1]*s[1]/n;let ab=s[5]-s[0]*s[1]/n;
    let ay=s[6]-s[0]*s[2]/n;let by=s[7]-s[1]*s[2]/n;let det=aa*bb-ab*ab;
    assert!(aa>1e-8&&bb>1e-8&&det>0.1*aa*bb,"joint component fixture is singular/unexercised");
    [(ay*bb-by*ab)/det,(by*aa-ay*ab)/det]
}
fn combination(a:&Gradient,b:&Gradient,scale:f32)->Gradient {
    Gradient{dx:a.dx.iter().zip(&b.dx).map(|(a,b)|a+scale*b).collect(),
        dy:a.dy.iter().zip(&b.dy).map(|(a,b)|a+scale*b).collect()}
}
#[test]
fn d_near_far_retention() {
    let mut cases=Vec::new();let mut all=true;
    for noisy in [false,true] {
        let out=fixture(Scene::NearFar,noisy);let truth=target(&planes(Scene::NearFar,None,false),&out.sizes);
        let a=component_target(0,&out.sizes);let b=component_target(1,&out.sizes);
        let wrong=target(&planes(Scene::NearFar,Some(0),noisy),&out.sizes);
        let(rows,no_harm_pass)=errors(&out,&truth,WHOLE);
        let mut components=Vec::new();let(mut protected,mut wrong_rejected,mut erased_rejected,mut half_far_rejected)=(true,false,true,true);
        for c in 0..4 {for(k,which)in [(0,0),(2,1)] {
            let e=edges(out.sizes[k],k,c,WHOLE);
            let rb=joint(&out.baseline[c][k],&a[c][k],&b[c][k],&e);
            let ra=joint(&out.candidate[c][k],&a[c][k],&b[c][k],&e);
            let rw=joint(&wrong[c][k],&a[c][k],&b[c][k],&e);
            let exact=combination(&a[c][k],&b[c][k],1.);let re=joint(&exact,&a[c][k],&b[c][k],&e);
            assert!(re.iter().all(|v|(*v-1.).abs()<1e-5));
            let half=combination(&a[c][k],&b[c][k],0.5);let rh=joint(&half,&a[c][k],&b[c][k],&e);
            assert!((rh[0]-1.).abs()<1e-5&&(rh[1]-0.5).abs()<1e-5);
            let zero=Gradient{dx:vec![0.;out.sizes[k].pixels()],dy:vec![0.;out.sizes[k].pixels()]};
            let rz=joint(&zero,&a[c][k],&b[c][k],&e);erased_rejected&=!retain(1.,rz[which]);
            if which==1 {half_far_rejected&=!retain(1.,rh[1]);
                wrong_rejected|=!retain(rb[1],rw[1])||!no_harm(rms(&out.baseline[c][k],&truth[c][k],&e),rms(&wrong[c][k],&truth[c][k],&e));}
            let live=rb[which]>=0.5;let pass=live&&retain(rb[which],ra[which]);protected&=pass;
            components.push(json!({"channel":c,"level":k,"protected_component":which,"baseline_joint":rb,
                "candidate_joint":ra,"wrong_depth_joint":rw,"truth_joint":re,"half_far_joint":rh,
                "live":live,"retention_pass":pass}));
        }}
        let pass=no_harm_pass&&protected&&wrong_rejected&&erased_rejected&&half_far_rejected;all&=pass;
        cases.push(json!({"noise_sigma_dn":if noisy{20.}else{0.},"levels":rows,"components":components,
            "component_retention_pass":protected,"wrong_depth_rejected":wrong_rejected,
            "erased_rejected":erased_rejected,"half_far_rejected":half_far_rejected,"scientific_pass":pass}));
    }
    emit("depth",json!({"mechanical_pass":true,"scientific_pass":all,"cases":cases}));
}
