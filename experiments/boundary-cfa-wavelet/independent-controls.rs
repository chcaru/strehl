// Independent fixed choices. Root alone executes this generated-data screen.
use super::{BoundaryPlan,Complex,Comparison,Subband,compare_generated,extend_four,crop_four,
    forward_real,inverse_complete,gather_known4,original_variances,noisy_source,probe_variance8,subbands};
use crate::align_cmd;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{f64::consts::TAU,path::{Path,PathBuf}};
use strehl_core::{align::Similarity,CfaPlane,noise::{Levels,NoiseModel,PlaneNoise,Provenance},profile};
use strehl_raw::{Frame,Region};

const W:usize=320;
const H:usize=288;
const N:usize=5;
const GAIN:[f32;3]=[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)];
fn region()->align_cmd::CropRect {align_cmd::CropRect{x:7,y:9,width:113,height:101}}
fn levels()->Levels {Levels{black:512.0,white:15360.0}}
fn model(iso:f32)->NoiseModel {profile::noise_model_for("ILCE-7CM2",Some(iso),levels())}
fn cfa(x:usize,y:usize)->CfaPlane {match(x%2,y%2){(0,0)=>CfaPlane::R,(1,0)=>CfaPlane::G1,(0,1)=>CfaPlane::G2,_=>CfaPlane::B}}
fn channel(x:usize,y:usize)->usize {match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1}}
fn hash16(v:&[u16])->String {let mut h=Sha256::new();for x in v {h.update(x.to_le_bytes());}h.finalize().iter().map(|b|format!("{b:02x}")).collect()}
fn hashf(v:&[f32])->String {let mut h=Sha256::new();for x in v {h.update(x.to_bits().to_le_bytes());}h.finalize().iter().map(|b|format!("{b:02x}")).collect()}
fn mix(mut x:u32)->u32 {x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f64 {
    let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x31d59a67;
    let u=(mix(s) as f64+0.5)/4294967296.0;let v=(mix(s^0xa73126bd) as f64+0.5)/4294967296.0;
    (-2.0*u.ln()).sqrt()*(TAU*v).cos()
}
#[derive(Clone,Copy)]
enum Scene {Flat,Weak(f64),Coarse}
impl Scene {fn name(self)->&'static str {match self {Self::Flat=>"flat",Self::Weak(_)=>"weak-red-warm-wb",Self::Coarse=>"coarse-corner-varying-focus"}}}
fn value(scene:Scene,c:usize,x:f64,y:f64,source:Option<usize>)->f64 {
    match scene {
        Scene::Flat=>0.30,
        Scene::Weak(a)=>{
            let sigma=source.map_or(0.0,|k|1.3*(k as f64-2.0).abs());
            0.30+if c==0 {a*(-0.5*(TAU*46.0/256.0*sigma).powi(2)).exp()*(TAU*46.0*x/256.0+0.37).cos()}else{0.0}
        },
        Scene::Coarse=>{
            let depth=2.0+1.5*((x-127.0)/24.0).tanh();
            let blur=source.map_or(0.0,|k|16.0*(k as f64-depth).abs());let var=400.0+blur*blur;
            0.30+0.08*400.0/var*(-((x-18.0).powi(2)+(y-20.0).powi(2))/(2.0*var)).exp()
                +0.06*(-0.5*TAU*TAU*blur*blur*2.0/(384.0*384.0)).exp()*(TAU*(x+y-140.0)/384.0).cos()
        }
    }
}
fn fixture(scene:Scene,k:usize,iso:f32,noise:&NoiseModel,warp:Similarity)->Frame {
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,levels:levels(),iso:Some(iso),
        wb_coeffs:[GAIN[0],GAIN[1],GAIN[2],f32::NAN],xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir().unwrap().join(format!("nonexistent-boundary-wavelet-{k}.ARW"))};
    assert!(!f.path.exists());let p=warp.to_params();let a=1.0+p.g;let b=p.rot;let det=a*a+b*b;
    for y in 0..H {for x in 0..W {
        // Independent inverse of the pull about full native centre(W/2,H/2).
        let sx=x as f64-W as f64/2.0-2.0*p.ax;let sy=y as f64-H as f64/2.0-2.0*p.ay;
        let wx=(a*sx+b*sy)/det+W as f64/2.0;let wy=(-b*sx+a*sy)/det+H as f64/2.0;
        let c=channel(x,y);let signal=(value(scene,c,wx,wy,Some(k))*levels().range() as f64/GAIN[c] as f64) as f32;
        let v=512.0+signal as f64+gaussian(x,y,k)*noise.sigma(cfa(x,y),signal) as f64;
        assert!(v>512.0 && v<15360.0);f.data[(active.y+y)*stride+active.x+x]=v.round() as u16;
    }}f
}
fn save(path:&Path,v:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),v).unwrap();}
fn mag2(z:Complex)->f64 {(z.re as f64).powi(2)+(z.im as f64).powi(2)}
fn wave(frame:&Frame,warp:Similarity,plan:&BoundaryPlan)->Vec<Vec<Complex>> {
    extend_four(&gather_known4(frame,warp,region()).unwrap(),plan).unwrap().iter()
        .map(|p|forward_real(p,plan.padded_width,plan.padded_height).unwrap()).collect()
}
fn wb2()->[f64;4] {[f64::from(GAIN[0]).powi(2),1.0,1.0,f64::from(GAIN[2]).powi(2)]}
fn band_mean(planes:&[Vec<f64>],band:&Subband)->f64 {
    let g=wb2();(0..4).map(|p|g[p]*band.positions.iter().map(|&i|planes[p][i]).sum::<f64>()).sum::<f64>()/band.positions.len() as f64
}
fn mean_se(v:&[f64])->(f64,f64) {let m=v.iter().sum::<f64>()/v.len() as f64;let var=v.iter().map(|x|(x-m).powi(2)).sum::<f64>()/(v.len()-1) as f64;(m,(var/v.len() as f64).sqrt())}

fn boundaries()->Value {
    let p=BoundaryPlan::new(113,101).unwrap();assert_eq!((p.padded_width,p.padded_height,p.left,p.top),(128,128,7,13));
    let independent=|mut i:isize,n:usize|{while i<0 || i>=n as isize {i=if i<0 {-i-1}else{2*n as isize-i-1};}i as usize};
    for (i,&x) in p.x_indices.iter().enumerate(){assert_eq!(x,independent(i as isize-7,113));}
    for (i,&y) in p.y_indices.iter().enumerate(){assert_eq!(y,independent(i as isize-13,101));}
    let src=(0..4).map(|c|(0..113*101).map(|i|(100000*c+113*(i/113)+i%113) as f32).collect::<Vec<_>>()).collect::<Vec<_>>();
    let ext=extend_four(&src,&p).unwrap();let back=crop_four(&ext,&p).unwrap();assert_eq!(src,back);
    for c in 0..4 {for y in 0..128 {for x in 0..128 {assert_eq!(ext[c][y*128+x],src[c][independent(y as isize-13,101)*113+independent(x as isize-7,113)]);}}}
    let mut rows=Vec::new();
    for (w,h) in [(1,1),(1,8),(8,1),(2,4),(8,16),(128,128)] {
        let v=(0..w*h).map(|i|Complex{re:((i*17%53) as f32-26.0)/17.0,im:((i*19%43) as f32-21.0)/29.0}).collect::<Vec<_>>();
        let z=super::transform_complete(&v,w,h).unwrap();let out=inverse_complete(&z,w,h).unwrap();
        let err=v.iter().zip(&out).map(|(a,b)|mag2(Complex{re:a.re-b.re,im:a.im-b.im}).sqrt()).fold(0.0f64,f64::max);
        let a=v.iter().copied().map(mag2).sum::<f64>();let b=z.iter().copied().map(mag2).sum::<f64>();assert!(err<3e-5 && (a-b).abs()/a.max(1.0)<3e-5);
        let bands=subbands(w,h).unwrap();let mut seen=vec![0usize;w*h];seen[0]=1;for b in &bands {for &i in &b.positions {seen[i]+=1;}}assert!(seen.iter().all(|&n|n==1));
        let dc=forward_real(&vec![1.0;w*h],w,h).unwrap();assert!(dc.iter().skip(1).all(|&z|mag2(z)<1e-7));
        rows.push(json!({"shape":[w,h],"roundtrip_max":err,"parseval_relative":(a-b).abs()/a.max(1.0),"complete_packing":true}));
    }
    assert!(BoundaryPlan::new(0,101).is_err());assert!(BoundaryPlan::new(513,101).is_err());
    json!({"extension_exact":true,"planes_distinct":true,"rectangular_transforms":rows})
}

fn literal_covariance()->Value {
    let noise=model(100.0);let warp=super::gatefloor::gpu_warp();let plan=BoundaryPlan::new(113,101).unwrap();
    let base=fixture(Scene::Flat,2,100.0,&noise,warp);let before=hash16(&base.data);
    let mut ext_states=Vec::new();let mut waves=Vec::new();let mut gathered=Vec::new();
    for (a,b) in [(-32i32,-32i32),(-32,32),(32,-32),(32,32)] {
        let mut f=base.clone();for ((x,y),d) in [((16,20),a),((18,20),b)] {let i=(f.active.y+y)*f.stride+f.active.x+x;f.data[i]=(f.data[i] as i32+d) as u16;}
        let g=gather_known4(&f,warp,region()).unwrap();let e=extend_four(&g,&plan).unwrap();
        waves.push(e.iter().map(|v|forward_real(v,128,128).unwrap()).collect::<Vec<_>>());ext_states.push(e);gathered.push(g);
    }
    assert_eq!(hash16(&base.data),before);let n=128*128;let mut overlap=0;let mut transitions=0;
    for p in 0..4 {for i in 0..113*101 {let a=gathered[2][p][i]-gathered[0][p][i];let b=gathered[1][p][i]-gathered[0][p][i];transitions+=(a!=0.0 || b!=0.0) as usize;overlap+=(a!=0.0 && b!=0.0) as usize;}}
    assert!(transitions>4 && overlap>0,"fractional source reuse not exercised");
    let mut rows=Vec::new();let mut wrong_live=false;
    // Fixed coefficients near the reflected source support, plus deep coarse ones.
    for i in [7*128+68,71*128+4,71*128+68,3*128+34,35*128+34,128+3,3] {
        let mut basis=vec![Complex{re:0.0,im:0.0};n];basis[i].re=1.0;let kernel=inverse_complete(&basis,128,128).unwrap();
        for p in 0..4 {
            let mut mu=vec![0.0f64;n];for s in &ext_states {for j in 0..n {mu[j]+=s[p][j] as f64/4.0;}}
            let mean=Complex{re:waves.iter().map(|s|s[p][i].re as f64/4.0).sum::<f64>() as f32,im:waves.iter().map(|s|s[p][i].im as f64/4.0).sum::<f64>() as f32};
            let exact=waves.iter().map(|s|mag2(Complex{re:s[p][i].re-mean.re,im:s[p][i].im-mean.im})/4.0).sum::<f64>();
            let mut contraction=0.0;let mut diagonal=0.0;
            for s in &ext_states {let(mut re,mut im)=(0.0,0.0);for j in 0..n {let d=s[p][j] as f64-mu[j];re+=d*kernel[j].re as f64;im-=d*kernel[j].im as f64;diagonal+=0.25*d*d*mag2(kernel[j]);}contraction+=0.25*(re*re+im*im);}
            assert!((exact-contraction).abs()<=0.03+0.002*exact,"finite covariance contraction differs {i}/{p}: {exact} {contraction}");
            if exact>0.01 && (diagonal-exact).abs()>0.1*exact {wrong_live=true;}
            rows.push(json!({"coefficient":i,"plane":p,"literal_four_state_variance":exact,"inverse_kernel_full_covariance":contraction,"wrong_independent_extended_sites":diagonal}));
        }
    }
    assert!(wrong_live,"diagonal/no-reuse covariance destroyer was not detected");
    json!({"source_sites":[[16,20],[18,20]],"perturbation_dn":32,"changed_outputs":transitions,"shared_output_support":overlap,"wrong_covariance_rejected":wrong_live,"coefficients":rows})
}

fn variance_reference(warp:Similarity,label:&str)->Value {
    let noise=model(100.0);let f=fixture(Scene::Flat,2,100.0,&noise,warp);let before=hash16(&f.data);let plan=BoundaryPlan::new(113,101).unwrap();
    let actual=probe_variance8(&f,warp,region(),&noise,&plan,71,true).unwrap();let bands=subbands(128,128).unwrap();let n=128*128;
    let mut mean=vec![vec![[0.0f64;2];n];4];let mut m2=vec![vec![0.0f64;n];4];let mut previous=None;let mut pair_rows=Vec::new();
    let reference_seeds=(0..64).map(|k|0x5726_0901usize+k*7919).collect::<Vec<_>>();assert!(reference_seeds.iter().all(|s|!actual.seeds.contains(s)));
    for (k,&seed) in reference_seeds.iter().enumerate() {
        let noisy=noisy_source(&f,&actual.original_variance,seed).unwrap();let current=wave(&noisy,warp,&plan);
        for p in 0..4 {for i in 0..n {let z=[current[p][i].re as f64,current[p][i].im as f64];for q in 0..2 {let d=z[q]-mean[p][i][q];mean[p][i][q]+=d/(k+1) as f64;m2[p][i]+=d*(z[q]-mean[p][i][q]);}}}
        if k%2==0 {previous=Some(current);} else {let a:Vec<Vec<Complex>>=previous.take().unwrap();let dif=(0..4).map(|p|(0..n).map(|i|0.5*mag2(Complex{re:a[p][i].re-current[p][i].re,im:a[p][i].im-current[p][i].im})).collect::<Vec<_>>()).collect::<Vec<_>>();pair_rows.push(bands.iter().map(|b|band_mean(&dif,b)).collect::<Vec<_>>());}
    }
    for p in &mut m2 {for v in p {*v/=63.0;}}
    let av=actual.variance4.iter().map(|p|p.iter().map(|&v|v as f64).collect::<Vec<_>>()).collect::<Vec<_>>();let gain=wb2();
    let mut rows=Vec::new();let(mut pooled_a,mut pooled_ref)=(0.0,0.0);
    for (b,band) in bands.iter().enumerate() {
        let a=band_mean(&av,band);let reference=band_mean(&m2,band);
        let own=actual.pair_band_mean4.iter().map(|r|(0..4).map(|p|gain[p]*r[b][p]).sum()).collect::<Vec<f64>>();
        let other=pair_rows.iter().map(|r|r[b]).collect::<Vec<_>>();let(am,ase)=mean_se(&own);let(rm,rse)=mean_se(&other);
        assert!((a-am).abs()<=1e-5*a.max(1.0));let allowance=4.0*ase.hypot(rse)+0.02*rm;let pass=(am-rm).abs()<=allowance;
        assert!(pass,"8-pair band floor outside frozen uncertainty: {label}, band{b}: {am} vs{rm}, allowance{allowance}");
        if band.level<=2 {pooled_a+=a*band.positions.len() as f64;pooled_ref+=reference*band.positions.len() as f64;}
        rows.push(json!({"level":band.level,"direction":band.direction,"actual8":a,"heldout64_sample":reference,"heldout32_pairs":rm,"actual8_se":ase,"reference32_se":rse,"allowance":allowance,"pass":pass}));
    }
    let ratio=pooled_a/pooled_ref;assert!((0.75..=1.33).contains(&ratio),"high-rank floor ratio {ratio}");
    assert!(!(0.75..=1.33).contains(&(2.0*ratio)) && !(0.75..=1.33).contains(&(0.5*ratio)));
    assert_eq!(hash16(&f.data),before);let bias=actual.bias4.as_ref().unwrap().iter().flatten().map(|&v|mag2(v)).sum::<f64>();
    json!({"warp":label,"heldout_realizations":64,"candidate_pairs":8,"seed_disjoint":true,"high_rank_ratio":ratio,"factor_two_destroyer_rejected":true,"bias_total_squared":bias,"bands":rows})
}

#[test]
fn independent_boundary_cfa_00_structure_and_noise() {
    let boundary=boundaries();let literal=literal_covariance();
    let synthetic=NoiseModel::new([0.13,0.31,0.71,0.47].map(|g|PlaneNoise{gain_dn_per_e:g,read_noise_e:2.0,levels:levels()}),100.0,Provenance::Measured);
    let f=fixture(Scene::Flat,2,100.0,&synthetic,Similarity::IDENTITY);let original=original_variances(&f,&synthetic).unwrap();
    for y in 0..H {for x in 0..W {assert_eq!(original[y*W+x].to_bits(),synthetic.variance(cfa(x,y),f.active_row(y)[x] as f32-512.0).to_bits());}}
    let g=gather_known4(&f,Similarity::IDENTITY,region()).unwrap();for(p,(dx,dy))in[(0,0),(1,0),(0,1),(1,1)].into_iter().enumerate(){for y in 0..101{for x in 0..113{assert_eq!(g[p][y*113+x],f.active_row(2*(9+y)+dy)[2*(7+x)+dx] as f32-512.0);}}}
    let frac=gather_known4(&f,super::gatefloor::gpu_warp(),region()).unwrap();assert_ne!(g,frac);
    let refs=[variance_reference(Similarity::IDENTITY,"identity"),variance_reference(super::gatefloor::gpu_warp(),"held-fractional")];
    eprintln!("BOUNDARY_CFA_STRUCTURAL {}",json!({"boundary":boundary,"literal_covariance":literal,"variance_references":refs,"active_original_variance_mapping_exact":true,"identity_original_known4_exact":true,"fractional_differs":true}));
}

struct Score {rgb:f64,chroma:f64,component:[f64;3],edge:f64,corner:f64}
fn score(scene:Scene,rgb:&[f32])->Score {
    let(w,h)=(226,202);assert_eq!(rgb.len(),w*h*3);assert!(rgb.iter().all(|v|v.is_finite()));
    let(mut err,mut chroma,mut edge,mut corner)=(0.0,0.0,0.0,0.0);let(mut ne,mut nc)=(0,0);
    // Demeaned two-basis regression; weak-red uses cos/sin, coarse uses its
    // fixed truth feature plus a zero orthogonal basis and a free intercept.
    let mut sums=[[0.0f64;8];3];
    for y in 0..h {for x in 0..w {
        let(wx,wy)=((14+x) as f64,(18+y) as f64);let is_edge=x<16||x>=w-16||y<16||y>=h-16;
        let is_corner=(x<16||x>=w-16)&&(y<16||y>=h-16);let mut e=[0.0;3];
        for c in 0..3 {
            let v=rgb[(y*w+x)*3+c] as f64;let t=value(scene,c,wx,wy,None);e[c]=v-t;err+=e[c]*e[c];
            if is_edge{edge+=e[c]*e[c];}if is_corner{corner+=e[c]*e[c];}
            let (a,b)=match scene {Scene::Flat=>(0.0,0.0),Scene::Weak(amp)=>{let p=TAU*46.0*wx/256.0+0.37;if c==0{(amp*p.cos(),amp*p.sin())}else{(0.0,0.0)}},Scene::Coarse=>(t-0.30,0.0)};
            for(s,z)in sums[c].iter_mut().zip([a,b,v,a*a,b*b,a*b,a*v,b*v]){*s+=z;}
        }
        chroma+=(e[0]-e[1]).powi(2)+(e[2]-e[1]).powi(2);ne+=is_edge as usize;nc+=is_corner as usize;
    }}
    let mut component=[0.0;3];let n=(w*h) as f64;
    for c in 0..3 {let[a,b,v,aa,bb,ab,av,bv]=sums[c];let xx=aa-a*a/n;let yy=bb-b*b/n;let xy=ab-a*b/n;let xv=av-a*v/n;let yv=bv-b*v/n;
        if xx>1e-15 {component[c]=if yy>1e-15{(xv*yy-yv*xy)/(xx*yy-xy*xy)}else{xv/xx};}
    }
    Score{rgb:(err/(3.0*n)).sqrt(),chroma:(chroma/(2.0*n)).sqrt(),component,edge:(edge/(3*ne) as f64).sqrt(),corner:(corner/(3*nc) as f64).sqrt()}
}
fn score_json(s:&Score)->Value {json!({"rgb_rmse":s.rgb,"chroma_rg_bg_rmse":s.chroma,"truth_component":s.component,"edge16_rgb_rmse":s.edge,"corner16_rgb_rmse":s.corner})}
fn truth(scene:Scene)->Vec<f32> {(0..202).flat_map(|y|(0..226).flat_map(move|x|(0..3).map(move|c|value(scene,c,(14+x) as f64,(18+y) as f64,None) as f32))).collect()}
fn preserved(b:&Score,a:&Score)->bool {(0..3).all(|c|b.component[c]<0.5 || a.component[c].min(1.0)>=0.9*b.component[c].min(1.0))}
fn metric_controls()->Value {
    let s=Scene::Coarse;let t=truth(s);let exact=score(s,&t);assert!(exact.rgb<1e-7 && exact.component.iter().all(|v|(v-1.0).abs()<1e-6));
    let half=score(s,&t.iter().map(|&v|0.30+0.5*(v-0.30)).collect::<Vec<_>>());
    let flat=score(s,&vec![0.30;226*202*3]);let over=score(s,&t.iter().map(|&v|0.30+1.4*(v-0.30)).collect::<Vec<_>>());
    assert!(half.component.iter().all(|v|(v-0.5).abs()<1e-5));assert!(!preserved(&exact,&half) && !preserved(&exact,&flat));
    assert!(preserved(&over,&exact) && over.rgb>exact.rgb && flat.rgb>half.rgb);
    json!({"exact":score_json(&exact),"half_amplitude":score_json(&half),"constant_destroyer":score_json(&flat),"overcontrast":score_json(&over),"truth_capping_live":true})
}
fn direct_rgb(frames:&[Frame],warp:Similarity)->Vec<f32> {
    let mut sum=vec![vec![0.0;113*101];4];for f in frames {let g=gather_known4(f,warp,region()).unwrap();for p in 0..4{for i in 0..113*101{sum[p][i]+=g[p][i];}}}
    for p in &mut sum{for x in p{*x/=frames.len() as f32;}}
    super::camera_rgb(&sum,113,101,levels(),frames[0].wb_coeffs).unwrap()
}
fn evidence(c:&Comparison,frames:&[Frame],hashes:&[String],warp:Similarity,noise:&NoiseModel)->Value {
    assert_eq!((c.native_width,c.native_height),(226,202));assert_eq!(c.baseline_level_sizes,vec![[113,101],[57,51],[29,26],[15,13]]);
    assert_eq!(c.boundary.padded_width,128);assert_eq!(c.boundary.padded_height,128);assert_eq!(c.bands.len(),21);
    assert_eq!(c.candidate_weight_summary.len(),21);assert_eq!(c.candidate_fallback_fraction.len(),21);
    let mut rows=Vec::new();
    for (k,f) in frames.iter().enumerate() {
        assert_eq!(hash16(&f.data),hashes[k]);assert_eq!(c.frames[k].source_sha256,hashes[k]);
        let gathered=gather_known4(f,warp,region()).unwrap();for p in 0..4 {assert_eq!(hashf(&gathered[p]),c.frames[k].gathered_known4_sha256[p]);}
        let guide=gathered[1].iter().zip(&gathered[2]).map(|(&a,&b)|0.5*(a+b)).collect::<Vec<_>>();assert_eq!(hashf(&guide),c.frames[k].guide_sha256);
        for (p,(dx,dy)) in [(0,0),(1,0),(0,1),(1,1)].into_iter().enumerate() {
            let v=(0..H/2).flat_map(|y|(0..W/2).map(move|x|noise.variance(cfa(dx,dy),f.active_row(2*y+dy)[2*x+dx] as f32-512.0))).collect::<Vec<_>>();
            assert_eq!(hashf(&v),c.frames[k].plane_variance_sha256[p]);
        }
        assert_eq!(c.frames[k].known4_original_exact,if warp==Similarity::IDENTITY{Some(true)}else{None});
        assert_eq!(c.frames[k].identity_guide_original_exact,if warp==Similarity::IDENTITY{Some(true)}else{None});
        rows.push(json!({"source_sha256":hashes[k],"gathered_known4_sha256":c.frames[k].gathered_known4_sha256,
            "guide_sha256":c.frames[k].guide_sha256,"baseline_variance_sha256":c.frames[k].variance_sha256,"original_plane_variance_sha256":c.frames[k].plane_variance_sha256,
            "coefficient_variance_sha256":c.frames[k].coefficient_variance_sha256,"probe_seeds":c.frames[k].probe_seeds,"probe_seconds":c.frames[k].probe_seconds,
            "bias_band_mean_square4":c.frames[k].bias_band_mean_square4,"known4_original_exact":c.frames[k].known4_original_exact}));
    }
    for(b,s)in c.bands.iter().zip(&c.candidate_weight_summary){assert_eq!(s.total_coefficients,b.positions.len());assert!(s.min_weight>=0.0 && s.max_weight.is_finite());assert!(s.multi_source_coefficients<=s.total_coefficients);}
    json!({"sources":rows,"baseline_level_sizes":c.baseline_level_sizes,"baseline_averaged_fraction":c.baseline_averaged_fraction,
        "candidate_fallback_fraction":c.candidate_fallback_fraction,"shared_tuple_weights":true,"input_immutable":true})
}
fn coarse_activation(c:&Comparison)->Value {
    let p=&c.boundary;let plane=(0..101).flat_map(|y|(0..113).map(move|x|value(Scene::Coarse,1,(14+2*x) as f64,(18+2*y) as f64,None) as f32)).collect::<Vec<_>>();
    let e=extend_four(&vec![plane;4],p).unwrap();let z=forward_real(&e[0],128,128).unwrap();
    let total=z.iter().skip(1).copied().map(mag2).sum::<f64>();let mut deep=0.0;let mut positive=0;
    for (b,s) in c.bands.iter().zip(&c.candidate_weight_summary) {if b.level>=3 {deep+=b.positions.iter().map(|&i|mag2(z[i])).sum::<f64>();positive+=s.positive_source_coefficients;}}
    let share=deep/total;assert!(share>0.01 && positive>0,"coarse boundary fixture missed new bands");
    json!({"truth_energy_beyond_actual_three_baseline_bands":share,"positive_source_coefficients_in_deeper_bands":positive})
}

#[test]
fn independent_boundary_cfa_10_generated_quality_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_BOUNDARY_CFA_WAVELET_OUT").expect("root-owned output directory"));std::fs::create_dir(&out).unwrap();
    let commission=metric_controls();let mut cases=Vec::new();let mut decisions=Vec::new();let mut neutrality=None;
    for iso in [100.0f32,400.0] {for (label,warp) in [("identity",Similarity::IDENTITY),("held-fractional",super::gatefloor::gpu_warp())] {
        let noise=model(iso);assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let amp=(2.0*noise.sigma(CfaPlane::R,0.30*levels().range()/GAIN[0])*GAIN[0]/levels().range()) as f64;
        let(mut benefit,mut guards,mut exercised)=(false,true,true);
        for scene in [Scene::Flat,Scene::Weak(amp),Scene::Coarse] {
            let frames=(0..N).map(|k|fixture(scene,k,iso,&noise,warp)).collect::<Vec<_>>();let hashes=frames.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>();let warps=vec![warp;N];
            let c=compare_generated(&frames,region(),&warps,&noise,true).unwrap();let ev=evidence(&c,&frames,&hashes,warp,&noise);
            let b=score(scene,&c.baseline_rgb);let a=score(scene,&c.candidate_rgb);let mut witness=None;let mut live=true;
            let pass=match scene {
                Scene::Flat=>{
                    let single=score(scene,&direct_rgb(&frames[2..3],warp));let mean=score(scene,&direct_rgb(&frames,warp));
                    let averaged=c.bands.iter().zip(&c.candidate_fallback_fraction).map(|(b,&f)|b.positions.len() as f64*f).sum::<f64>();live=averaged>100.0;
                    benefit|=a.rgb<=0.95*b.rgb;witness=Some(json!({"fixed_source2":score_json(&single),"direct_mean":score_json(&mean),"averaged_coefficients":averaged}));
                    a.rgb<=1.25*b.rgb && a.chroma<=1.25*b.chroma && a.rgb<=single.rgb && a.chroma<=single.chroma
                },
                Scene::Weak(_)=>{
                    let focused=score(scene,&direct_rgb(&frames[2..3],warp));let own=c.candidate_weight_summary.iter().map(|s|s.own_plane_positive_source_coefficients[0]).sum::<usize>();
                    live=focused.component[0]>=0.5 && own>100;let recovery=a.component[0].min(1.0)>=0.9*focused.component[0].min(1.0);
                    benefit|=a.rgb<=0.95*b.rgb;witness=Some(json!({"fixed_source2":score_json(&focused),"own_red_positive":own,"focused_source_feasible":live,"retains90percent_focused_source":recovery,"true_red_amplitude":amp}));
                    if iso==100.0 && label=="held-fractional" {
                        let off=compare_generated(&frames,region(),&warps,&noise,false).unwrap();let before=[hashf(&c.baseline_rgb),hashf(&c.candidate_rgb)];let after=[hashf(&off.baseline_rgb),hashf(&off.candidate_rgb)];assert_eq!(before,after);
                        for(x,y)in c.baseline_planes4.iter().chain(&c.candidate_planes4).zip(off.baseline_planes4.iter().chain(&off.candidate_planes4)){assert_eq!(hashf(x),hashf(y));}
                        assert!(off.frames.iter().all(|f|f.pair_band_mean4.is_empty() && f.bias_band_mean_square4.is_empty()));
                        assert!(off.candidate_weight_summary.iter().all(|s|s.own_plane_positive_source_coefficients==[0;4]));
                        neutrality=Some(json!({"on_rgb_sha256":before,"off_rgb_sha256":after,"all8_collapsed_planes_exact":true,"diagnostics_disabled":true}));
                    }
                    recovery && preserved(&b,&a) && a.rgb<=1.10*b.rgb && a.edge<=1.10*b.edge && a.corner<=1.10*b.corner
                },
                Scene::Coarse=>{
                    let destroyer=score(scene,&vec![0.30;226*202*3]);let activation=coarse_activation(&c);
                    live=c.frames.windows(2).any(|p|p[0].guide_sha256!=p[1].guide_sha256) && c.baseline_averaged_fraction.iter().any(|&f|f<1.0);
                    witness=Some(json!({"constant_destroyer":score_json(&destroyer),"deeper_activation":activation}));
                    preserved(&b,&a) && a.component.iter().all(|&v|v>=0.5) && a.rgb<=0.70*destroyer.rgb && a.rgb<=1.10*b.rgb && a.edge<=1.10*b.edge && a.corner<=1.10*b.corner
                }
            };
            for(k,f)in frames.iter().enumerate(){assert_eq!(hash16(&f.data),hashes[k]);}guards&=pass;exercised&=live;
            let row=json!({"iso":iso,"warp":label,"scene":scene.name(),"baseline":score_json(&b),"candidate":score_json(&a),"rgb_ratio":a.rgb/b.rgb,"guard_pass":pass,"fixture_exercised":live,"witness":witness,"evidence":ev});
            eprintln!("BOUNDARY_CFA_CASE {}",row);cases.push(row);
        }
        decisions.push(json!({"iso":iso,"warp":label,"benefit":benefit,"guards_pass":guards,"fixtures_exercised":exercised,"admitted":benefit&&guards&&exercised}));
    }}
    assert!(neutrality.is_some());let admitted=decisions.iter().all(|d|d["admitted"]==true);
    let result=json!({"status":"SCREEN_COMPLETE","bounded_photographic_prototype_admitted":admitted,"production_admitted":false,
        "decisions":decisions,"cases":cases,"metric_controls":commission,"observer_neutrality":neutrality,
        "scope":"Five generated u16 originals; actual rounded GPU MHC/Catmull no-CA; fixed113x101 reflection to128; complete7 candidate versus actual3 Laplacian bands; supplied model with8 independent source-noise pairs; full-domain plus16-native boundary/corner truth. No RAW, sensor calibration or SOTA claim."});
    save(&out.join("screen.json"),&result);eprintln!("BOUNDARY_CFA_SCREEN {}",result);
}
