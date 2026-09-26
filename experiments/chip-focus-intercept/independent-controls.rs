use super::{Front,GaussianStream,Output,Stream};
use serde_json::{json,Value};
use std::f64::consts::TAU;
fn front(n:usize)->Front {Front{frames:n,xy_center:[64.,48.],xy_scale:[64.,48.],plane:[0.17,-0.11,0.5],
    schedule_knots:vec![0.,0.25,0.5,0.75,1.],schedule_values:vec![0.,0.16,0.41,0.70,1.],sigma:0.045}}
fn emit(name:&str,v:Value) {println!("CHIP_FOCUS_INTERCEPT {}",json!({"name":name,"result":v}));
    if let Some(dir)=std::env::var_os("STREHL_CHIP_FOCUS_INTERCEPT_OUT") {let p=std::path::PathBuf::from(dir);
        std::fs::create_dir_all(&p).unwrap();let p=p.join(format!("{name}.json"));assert!(!p.exists());
        std::fs::write(p,serde_json::to_vec_pretty(&v).unwrap()).unwrap();}}
fn run(f:Front,w:usize,h:usize,mut g:impl FnMut(usize)->Vec<Vec<f32>>)->anyhow::Result<Output> {
    let mut s=Stream::new(w,h,f.clone())?;for k in 0..f.frames {s.add(k,&g(k))?;}s.finish()}
fn pair(f:Front,w:usize,h:usize,mut g:impl FnMut(usize)->Vec<Vec<f32>>)->anyhow::Result<(Output,Vec<Vec<f32>>)> {
    let mut s=Stream::new(w,h,f.clone())?;let mut b=GaussianStream::new(w,h,f.clone())?;
    for k in 0..f.frames {let p=g(k);s.add(k,&p)?;b.add(k,&p)?;}Ok((s.finish()?,b.finish()?.planes))}
fn hash(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn noise(k:usize,c:usize,j:usize)->f64 {
    let seed=(k as u32).wrapping_mul(0x9e3779b9)^(c as u32).wrapping_mul(0x85ebca6b)^(j as u32)^0x936a012b;
    let a=(f64::from(hash(seed))+0.5)/4294967296.;let b=(f64::from(hash(seed^0xa341316c))+0.5)/4294967296.;
    (-2.*a.ln()).sqrt()*(TAU*b).cos()}
fn time(k:usize,n:usize)->f64 {let v=[0.,0.16,0.41,0.70,1.];let u=k as f64/(n-1) as f64*4.;
    let i=(u.floor() as usize).min(3);v[i]+(u-i as f64)*(v[i+1]-v[i])}
// Unchanged numerical stimulus from chip-focus-radiance, including channel phases.
fn signal(c:usize,x:usize,y:usize,t:Option<f64>)->f64 {
    let xx=2.*x as f64+0.5;let yy=2.*y as f64+0.5;
    let z=0.5+0.17*(xx-64.)/64.-0.11*(yy-48.)/48.;
    let blur=0.65+t.map_or(0.,|v|30.*(v-z).abs());
    let freq=[0.055,0.07,0.07,0.045][c];let phase=[0.4,1.1,1.1,2.2][c];
    let base=[7000.,9000.,9000.,5000.][c];let amplitude=[1600.,1900.,1900.,1300.][c];
    base+amplitude*(-0.5*(TAU*freq*blur).powi(2)).exp()*(TAU*freq*(0.8*xx+0.6*yy)+phase).cos()}
fn mse(a:&[Vec<f32>],b:&[Vec<f32>])->f64 {a.iter().zip(b).flat_map(|(x,y)|x.iter().zip(y))
    .map(|(x,y)|(f64::from(*x)-f64::from(*y)).powi(2)).sum::<f64>()/(a.len()*a[0].len()) as f64}
fn dense(mut a:[[f64;4];3])->[f64;3] {
    for j in 0..3 {let pivot=(j..3).max_by(|x,y|a[*x][j].abs().total_cmp(&a[*y][j].abs())).unwrap();
        a.swap(j,pivot);let d=a[j][j];assert!(d.abs()>1e-12);for k in j..4 {a[j][k]/=d;}
        for i in 0..3 {if i!=j {let v=a[i][j];for k in j..4 {a[i][k]-=v*a[j][k];}}}}
    [a[0][3],a[1][3],a[2][3]]}

#[test]
fn b_moments_and_dense_oracle() {
    let f=front(33);let(w,h)=(7,5);let data=|k:usize| (0..4).map(|c|(0..w*h).map(|j| {
        let d=f64::from((f.schedule(k).unwrap()-f.centre(j%w,j/w))/f.sigma);
        (10000.+100.*c as f64+(20.+c as f64)*d+3.*d*d) as f32
    }).collect()).collect::<Vec<_>>();
    let out=run(f.clone(),w,h,data).unwrap();let(mut error,mut oracle_error,mut moment_error)=(0.0f64,0.0f64,0.0f64);
    let mut negative=false;let mut wrong_row_rejected=false;
    for j in 0..w*h {let mut moments=[0.;3];
        for k in 0..f.frames {let d=f64::from((f.schedule(k).unwrap()-f.centre(j%w,j/w))/f.sigma);
            let v=f64::from(out.equivalent_weight(k,j).unwrap());negative|=v<0.;
            for p in 0..3 {moments[p]+=v*d.powi(p as i32);}}
        for p in 0..3 {moment_error=moment_error.max((moments[p]-if p==0{1.}else{0.}).abs());}
        for c in 0..4 {let mut a=[[0.;4];3];
            for k in 0..f.frames {let d=f64::from((f.schedule(k).unwrap()-f.centre(j%w,j/w))/f.sigma);
                let q=(-0.5*d*d).exp();let v=[1.,d,d*d];let y=f64::from(data(k)[c][j]);
                for r in 0..3 {for p in 0..3 {a[r][p]+=q*v[r]*v[p];}a[r][3]+=q*v[r]*y;}}
            let expected=dense(a);let actual=f64::from(out.planes[c][j]);
            error=error.max((actual-(10000.+100.*c as f64)).abs());
            oracle_error=oracle_error.max((actual-expected[0]).abs());
            wrong_row_rejected|=(expected[1]-actual).abs()>0.02;
        }}
    emit("arithmetic",json!({"mechanical_pass":error<=0.02&&oracle_error<=0.02&&moment_error<=2e-4&&negative&&wrong_row_rejected,
        "quadratic_max_error_dn":error,"dense_oracle_max_error_dn":oracle_error,"moment_max_error":moment_error,
        "negative_weights_exercised":negative,"wrong_row_rejected":wrong_row_rejected,"exact_family_is_arithmetic_only":true}));
    assert!(error<=0.02&&oracle_error<=0.02&&moment_error<=2e-4&&negative&&wrong_row_rejected);
}

#[test]
fn c_support_refusal() {
    let p=vec![vec![8000.;4];4];let mut f=front(2);f.plane=[0.,0.,0.5];f.sigma=0.5;
    assert!(run(f,2,2,|_|p.clone()).is_err());
    let mut f=front(33);f.plane=[0.,0.,-0.1];assert!(run(f,2,2,|_|p.clone()).is_err());
    let mut f=front(3);f.schedule_knots=vec![0.,1.];f.schedule_values=vec![0.,1.];
    f.plane=[0.,0.,0.01];f.sigma=0.1;assert!(run(f,2,2,|_|p.clone()).is_err());
    let mut s=Stream::new(2,2,front(33)).unwrap();assert!(s.add(1,&p).is_err());
    s.add(0,&p).unwrap();assert!(s.add(0,&p).is_err());assert!(s.finish().is_err());
    let mut s=Stream::new(2,2,front(33)).unwrap();let mut bad=p.clone();bad[0][0]=f32::NAN;
    assert!(s.add(0,&bad).is_err());assert!(s.add(0,&p[..3]).is_err());
    emit("support",json!({"mechanical_pass":true,"rank_deficient_refused":true,
        "one_sided_refused":true,"negligible_opposite_mass_refused":true,
        "order_and_missing_refused":true,"invalid_input_refused":true}));
}

#[test]
fn a_flat_and_unchanged_nonquadratic() {
    const W:usize=64;const H:usize=48;const N:usize=33;
    let generate=|k:usize,flat:bool| (0..4).map(|c|(0..W*H).map(|j| {
        let value=if flat{8000.}else{signal(c,j%W,j/W,Some(time(k,N)))};
        (value+20.*noise(k,c,j)) as f32}).collect()).collect::<Vec<_>>();
    let truth_flat=vec![vec![8000.;W*H];4];
    let (flat,gaussian_flat)=pair(front(N),W,H,|k|generate(k,true)).unwrap();
    let mut variance=0.;let mut direct_disagreement=0.0f64;let mut max_noise_ratio=0.0f64;let mut max_noise_gain=0.0f64;
    for j in 0..W*H {let direct=(0..N).map(|k|f64::from(flat.equivalent_weight(k,j).unwrap()).powi(2)).sum::<f64>();
        variance+=400.*direct;direct_disagreement=direct_disagreement.max((direct-f64::from(flat.noise_gain[j])).abs()/direct);
        max_noise_ratio=max_noise_ratio.max(direct/f64::from(flat.gaussian_noise_gain[j]));max_noise_gain=max_noise_gain.max(direct);}
    variance/=(W*H) as f64;let observed=mse(&flat.planes,&truth_flat);let observed_ratio=observed/variance;
    let noise_pass=(0.9..=1.1).contains(&observed_ratio)&&max_noise_ratio<=2.&&max_noise_gain<=0.75;
    let mechanical=direct_disagreement<=0.002;
    let truth=(0..4).map(|c|(0..W*H).map(|j|signal(c,j%W,j/W,None) as f32).collect()).collect::<Vec<_>>();
    let (good,gaussian)=pair(front(N),W,H,|k|generate(k,false)).unwrap();
    let mut wrong_front=front(N);wrong_front.plane[0]*=-1.;wrong_front.plane[1]*=-1.;
    let wrong=run(wrong_front,W,H,|k|generate(k,false));
    let e=mse(&good.planes,&truth);let b=mse(&gaussian,&truth);let wrong_error=wrong.as_ref().ok().map(|o|mse(&o.planes,&truth));
    let erased=(0..4).map(|c|vec![[7000.,9000.,9000.,5000.][c];W*H]).collect::<Vec<_>>();
    let erased_error=mse(&erased,&truth);let detail_pass=e<=0.90*b;
    let wrong_rejected=wrong_error.is_some_and(|v|v>0.90*b);let erased_rejected=erased_error>0.90*b;
    emit("planar",json!({"mechanical_pass":mechanical,"flat_first":true,"noise_pass":noise_pass,
        "detail_pass":detail_pass,"wrong_front_rejected":wrong_rejected,"wrong_front_numerically_admitted":wrong.is_ok(),
        "wrong_front_refusal":wrong.as_ref().err().map(|e|format!("{e:#}")),"erased_detail_rejected":erased_rejected,
        "scientific_pass":noise_pass&&detail_pass&&wrong_rejected&&erased_rejected,
        "predicted_flat_mse_dn2":variance,"observed_flat_mse_dn2":observed,"observed_to_predicted":observed_ratio,
        "gaussian_flat_mse_dn2":mse(&gaussian_flat,&truth_flat),"max_noise_ratio_to_gaussian":max_noise_ratio,
        "max_noise_gain":max_noise_gain,"direct_vs_moment_variance_relative_max":direct_disagreement,
        "candidate_mse_dn2":e,"gaussian_mse_dn2":b,"wrong_mse_dn2":wrong_error,"erased_mse_dn2":erased_error,
        "canonical_consumer_qualified":false,"photographic_quality_admitted":false}));
    assert!(mechanical,"moment noise propagation disagrees with actual signed weights");
}

fn cdf(z:f64)->f64 {let x=z.abs();let t=1./(1.+0.2316419*x);
    let p=1.-(-0.5*x*x).exp()/TAU.sqrt()*t*(0.319381530+t*(-0.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))));
    if z>=0.{p}else{1.-p}}
fn scene(depth:bool,c:usize,x:f64,y:f64,t:Option<f64>)->f64 {
    let c=if c==3{2}else if c==0{0}else{1};
    if !depth {let s=0.65+t.map_or(0.,|v|32.*(v-0.5).abs());
        let box_value=(cdf((x-108.)/s)-cdf((x-140.)/s))*(cdf((y-116.)/s)-cdf((y-164.)/s));
        let(dx,dy,phase)=[(1.,0.,0.37),(0.8,0.6,1.13),(-0.6,0.8,2.07)][c];
        16000.*(0.18+[0.36,0.40,0.32][c]*box_value+[0.045,0.055,0.050][c]
            *(-0.5*(TAU*0.075*s).powi(2)).exp()*(TAU*0.075*(dx*x+dy*y)+phase).cos())
    }else {let mut v=0.27;
        for which in 0..2 {let focus=if which==0{0.3}else{0.7};let s=0.65+t.map_or(0.,|v|30.*(v-focus).abs());
            let (freq,amp)=if which==0{(0.10,[0.045,0.050,0.040][c])}else{(0.022,[0.090,0.100,0.085][c])};
            let(dx,dy,phase)=if which==0{[(1.,0.,0.37),(0.8,0.6,1.13),(-0.6,0.8,2.07)][c]}
                else{[(0.,1.,0.81),(0.6,-0.8,1.71),(0.8,0.6,2.63)][c]};
            v+=amp*(-0.5*(TAU*freq*s).powi(2)).exp()*(TAU*freq*(dx*x+dy*y)+phase).cos();}
        16000.*v}}
fn scores(output:&[Vec<f32>],truth:&[Vec<f32>])->Value {
    let n=truth[0].len() as f64;let mut rmse=vec![];let mut recovery=vec![];
    for c in 0..4 {let mut sums=[0.;5];for j in 0..truth[0].len(){let t=f64::from(truth[c][j]);let v=f64::from(output[c][j]);
        for(a,b)in sums.iter_mut().zip([t,v,t*t,t*v,(v-t).powi(2)]){*a+=b;}}
        rmse.push((sums[4]/n).sqrt());recovery.push((sums[3]-sums[0]*sums[1]/n)/(sums[2]-sums[0]*sums[0]/n));}
    let mut chroma=0.;for j in 0..truth[0].len(){let e=std::array::from_fn::<_,4,_>(|c|f64::from(output[c][j])-f64::from(truth[c][j]));
        let g=(e[1]+e[2])*0.5;chroma+=(e[0]-g).powi(2)+(e[3]-g).powi(2);}
    json!({"plane_rmse":rmse,"chroma_rmse":(chroma/(2.*n)).sqrt(),"template_recovery":recovery})}
fn no_harm(b:&Value,c:&Value)->bool {
    let planes=(0..4).all(|p|c["plane_rmse"][p].as_f64().unwrap()<=1.05*b["plane_rmse"][p].as_f64().unwrap());
    let retained=(0..4).all(|p|c["template_recovery"][p].as_f64().unwrap().clamp(0.,1.)>=0.98*b["template_recovery"][p].as_f64().unwrap().clamp(0.,1.));
    planes&&retained&&c["chroma_rmse"].as_f64().unwrap()<=1.05*b["chroma_rmse"].as_f64().unwrap()}
fn window(v:&[Vec<f32>],rect:[usize;4])->Vec<Vec<f32>> {
    let[x0,y0,x1,y1]=rect;v.iter().map(|p|(0..144).flat_map(|y|(0..160).filter_map(move|x| {
        let(xx,yy)=(2.*x as f64+0.5,2.*y as f64+0.5);
        (xx>=x0 as f64&&xx<x1 as f64&&yy>=y0 as f64&&yy<y1 as f64).then_some(p[y*160+x])
    })).collect()).collect()}
fn components(v:&[Vec<f32>])->[[f64;4];2] {
    let mut answer=[[0.;4];2];let n=(160*144) as f64;
    for c in 0..4 {let cc=if c==3{2}else if c==0{0}else{1};let mut sums=[0.;8];
        for j in 0..160*144 {let(x,y)=(2.*(j%160) as f64+0.5,2.*(j/160) as f64+0.5);
            let mut templates=[0.;2];for which in 0..2 {
                let(freq,amp)=if which==0{(0.10,[0.045,0.050,0.040][cc])}else{(0.022,[0.090,0.100,0.085][cc])};
                let(dx,dy,phase)=if which==0{[(1.,0.,0.37),(0.8,0.6,1.13),(-0.6,0.8,2.07)][cc]}
                    else{[(0.,1.,0.81),(0.6,-0.8,1.71),(0.8,0.6,2.63)][cc]};
                templates[which]=16000.*amp*(-0.5*(TAU*freq*0.65).powi(2)).exp()*(TAU*freq*(dx*x+dy*y)+phase).cos();}
            let[a,b]=templates;let value=f64::from(v[c][j]);
            for(s,t)in sums.iter_mut().zip([a,b,value,a*a,b*b,a*b,a*value,b*value]){*s+=t;}}
        let aa=sums[3]-sums[0]*sums[0]/n;let bb=sums[4]-sums[1]*sums[1]/n;let ab=sums[5]-sums[0]*sums[1]/n;
        let av=sums[6]-sums[0]*sums[2]/n;let bv=sums[7]-sums[1]*sums[2]/n;let det=aa*bb-ab*ab;
        assert!(aa>1.&&bb>1.&&det>0.1*aa*bb,"templates must be distinct and live");
        answer[0][c]=(av*bb-bv*ab)/det;answer[1][c]=(bv*aa-av*ab)/det;
    }answer}
#[test]
fn d_contact_depth_and_overshoot() {
    const W:usize=160;const H:usize=144;const N:usize=33;
    let mut records=vec![];let mut passes=vec![];
    for depth in [false,true] {let mut f=front(N);f.plane=[0.,0.,if depth{0.3}else{0.5}];
        let make=|k:Option<usize>,noisy:bool|(0..4).map(|c|(0..W*H).map(|j| {
            let value=scene(depth,c,2.*(j%W) as f64+0.5,2.*(j/W) as f64+0.5,k.map(|kk|time(kk,N)));
            (value+if noisy{20.*noise(k.unwrap(),c,j)}else{0.}) as f32}).collect()).collect::<Vec<_>>();
        let truth=make(None,false);let(out,gauss)=pair(f.clone(),W,H,|k|make(Some(k),true)).unwrap();
        let(clean,_)=pair(f,W,H,|k|make(Some(k),false)).unwrap();
        let bs=scores(&gauss,&truth);let cs=scores(&out.planes,&truth);
        let mut overshoot=0.0f64;
        for c in 0..4 {let c3=if c==3{2}else if c==0{0}else{1};let(lo,hi)=if depth {
            let a=[0.045,0.050,0.040][c3]+[0.090,0.100,0.085][c3];(16000.*(0.27-a),16000.*(0.27+a))
        }else{let a=[0.045,0.055,0.050][c3];(16000.*(0.18-a),16000.*(0.18+[0.36,0.40,0.32][c3]+a))};
            for v in &clean.planes[c]{overshoot=overshoot.max((lo-f64::from(*v)).max(f64::from(*v)-hi).max(0.));}}
        let range_pass=overshoot<=0.01*16000.*0.32;
        let noise_ratio=out.noise_gain.iter().zip(&out.gaussian_noise_gain).map(|(a,b)|f64::from(*a)/f64::from(*b)).fold(0.,f64::max);
        let max_gain=out.noise_gain.iter().copied().fold(0.,f32::max);
        let noise_pass=noise_ratio<=2.&&max_gain<=0.75;
        let mut protection=vec![];let mut protection_pass=true;
        if depth {let b=components(&gauss);let c=components(&out.planes);let t=components(&truth);
            assert!(t.iter().flatten().all(|v|(*v-1.).abs()<1e-5),"truth component calibration failed");
            let baseline_live=b.iter().flatten().all(|v|*v>=0.1);
            let retained=(0..2).all(|k|(0..4).all(|ch|c[k][ch].clamp(0.,1.)>=0.98*b[k][ch].clamp(0.,1.)));
            protection_pass=baseline_live&&retained;
            protection.push(json!({"near_far_gaussian_recovery":b,"near_far_candidate_recovery":c,
                "baseline_components_live":baseline_live,"each_component_retained":retained}));
        }else {for(name,rect)in [("contact-interior",[112,120,136,160]),("contact-edge",[92,100,158,180]),("contact-outside-spill",[142,118,164,162])] {
            let truth=window(&truth,rect);let b=scores(&window(&gauss,rect),&truth);let c=scores(&window(&out.planes,rect),&truth);
            let pass=no_harm(&b,&c);protection_pass&=pass;
            protection.push(json!({"window":name,"native_xyxy":rect,"gaussian":b,"candidate":c,"pass":pass}));
        }}
        let pass=no_harm(&bs,&cs)&&range_pass&&noise_pass&&protection_pass;
        records.push(json!({"scene":if depth{"near-fine-far-coarse"}else{"contact"},"gaussian":bs,"candidate":cs,
            "clean_signed_range_excess_dn":overshoot,"range_limit_dn":51.2,"range_pass":range_pass,
            "noise_pass":noise_pass,"max_noise_ratio_to_gaussian":noise_ratio,"max_noise_gain":max_gain,
            "protection_pass":protection_pass,"protections":protection,"pass":pass}));passes.push(pass);
    }
    // Metric commissioning: bounded observations intentionally align with the
    // positive signed kernel. This is a destroyer, not a physical scene.
    let mut f=front(N);f.plane=[0.,0.,0.5];let base=run(f.clone(),1,1,|_|vec![vec![0.];4]).unwrap();
    let negative=(0..N).any(|k|base.equivalent_weight(k,0).unwrap()<0.);assert!(negative);
    let bad=run(f,1,1,|k|vec![vec![if base.equivalent_weight(k,0).unwrap()>0.{6400.}else{0.}];4]).unwrap();
    let excess=f64::from(bad.planes[0][0])-6400.;let destroyer=excess>64.;
    emit("adversary",json!({"mechanical_pass":negative,"contact_pass":passes[0],"depth_pass":passes[1],
        "overshoot_destroyer_exercised":destroyer,"destroyer_excess_dn":excess,"destroyer_limit_dn":64.,
        "scientific_pass":passes.iter().all(|p|*p)&&destroyer,"cases":records,
        "canonical_consumer_qualified":false,"photographic_quality_admitted":false}));
    assert!(negative&&destroyer,"range rejection has not been exercised");
}
