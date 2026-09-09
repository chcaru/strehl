// Independent fixed stimulus, metric and refusal choices. Root alone executes.
use super::*;
use super::super::*;
use serde_json::{json,Value};
use strehl_core::pyramid::native_green_cue as cue;
use strehl_core::noise::{PlaneNoise,Provenance as NoiseProvenance};
use strehl_core::align::SimilarityParams;
use strehl_core::demosaic::{Mosaic,demosaic_row};

const W: usize=112;
const H: usize=78;
const SEEDS: [usize;8]=[701,709,719,727,733,739,743,751];
const BLURS: [f64;9]=[1.6,1.2,0.8,0.4,0.0,0.4,0.8,1.2,1.6];
const PHASES: [(usize,usize);4]=[(0,0),(1,0),(0,1),(1,1)];
const TAU: f64=std::f64::consts::TAU;

fn check(fail: &mut Vec<String>, yes: bool, name: impl Into<String>) {
    if !yes { fail.push(name.into()); }
}
fn model(levels: Levels, noisy: bool) -> NoiseModel {
    NoiseModel::new([PlaneNoise {gain_dn_per_e:if noisy {0.25} else {0.0},
        read_noise_e:if noisy {4.0} else {0.0},levels};4],160.0,NoiseProvenance::Fallback)
}
fn direction(d: usize) -> (f64,f64) {
    match d {0=>(1.0,0.0),1=>(0.0,1.0),2=>(0.5f64.sqrt(),0.5f64.sqrt()),_=>panic!("direction")}
}
fn sinc(x: f64) -> f64 { if x==0.0 {1.0} else {x.sin()/x} }
fn amplitude(d: usize, f: f64, a: f64) -> f64 {
    let (dx,dy)=direction(d);
    a*sinc(std::f64::consts::PI*f*dx)*sinc(std::f64::consts::PI*f*dy)
}
fn field(x:f64,y:f64,d:usize,low:bool,high:bool,sigma:f64) -> f64 {
    let (dx,dy)=direction(d);let u=dx*x+dy*y;
    let tone=|f:f64,a:f64,p:f64| amplitude(d,f,a)*(-0.5*(TAU*f*sigma).powi(2)).exp()*(TAU*f*u+p).cos();
    3000.0+if low {tone(0.06,500.0,0.2)} else {0.0}
        +if high {tone(0.30,40.0,1.1)} else {0.0}
}
fn frame(d:usize,low:bool,high:bool,sigma:f64,seed:Option<usize>,k:usize) -> Frame {
    let mut out=super::m194c_independent_tests::green_fixture(274,190,1,k);
    assert_eq!(&out.wb_coeffs[..3],&[1.15,1.0,1.65]);
    let mut draws=out.clone();
    if let Some(seed)=seed {
        let geom=out.geometry();
        fill_probe_noise(&mut draws,geom,32768.0,4096.0,seed.wrapping_add(k.wrapping_mul(0x9e3779b9))).unwrap();
    }
    for y in 0..190 {for x in 0..274 {
        let i=(out.active.y+y)*out.stride+out.active.x+x;
        let wb=[out.wb_coeffs[0],1.0,1.0,out.wb_coeffs[2]][2*(y&1)+(x&1)] as f64;
        let s=field(x as f64,y as f64,d,low,high,sigma)/wb;
        let n=if seed.is_some() {
            let z=(draws.data[i] as f64-32768.0)/4096.0;
            assert!(draws.data[i]>0 && draws.data[i]<65535,"normal generator clipping");
            // Literal injected shot/read law, no estimator or stage-private fit.
            z*(0.25*s+1.0).sqrt()
        } else {0.0};
        let v=(s+n+512.0).round();
        assert!(v>1024.0 && v<14848.0,"fixed unclipped stimulus");
        out.data[i]=v as u16;
    }}
    out
}
fn phase_planes(f:&Frame) -> Vec<Vec<f32>> {
    PHASES.iter().map(|&(dx,dy)| (0..H).flat_map(|y|
        (0..W).map(move |x| f.sample(18+2*x+dx,12+2*y+dy) as f32-f.levels.black)).collect()).collect()
}
fn positions(kind:usize) -> Vec<(usize,usize)> {
    (45..145).flat_map(|y|(87..187).filter_map(move|x|
        (kind==1 || ((x+y)&1)==1).then_some((x,y)))).collect()
}
fn readouts(planes:&[Vec<f32>]) -> [Vec<f32>;2] {
    assert_eq!(planes.len(),4);assert!(planes.iter().all(|p|p.len()==W*H));
    let mut mosaic=vec![0.0;4*W*H];
    for (p,&(dx,dy)) in PHASES.iter().enumerate() {for y in 0..H {for x in 0..W {
        mosaic[(2*y+dy)*(2*W)+2*x+dx]=planes[p][y*W+x]*[1.15f32,1.0,1.0,1.65][p];
    }}}
    let m=Mosaic {data:&mosaic,width:2*W,height:2*H};
    let mut rgb=vec![0.0;6*W];let mut green=vec![0.0;4*W*H];
    for y in 0..2*H {
        demosaic_row(&m,y,&mut rgb);
        for x in 0..2*W {green[y*2*W+x]=rgb[3*x+1];}
    }
    [positions(0).iter().map(|&(x,y)|mosaic[(y-12)*2*W+x-18]).collect(),
     positions(1).iter().map(|&(x,y)|green[(y-12)*2*W+x-18]).collect()]
}
fn truth(kind:usize,d:usize,low:bool,high:bool) -> Vec<f64> {
    positions(kind).iter().map(|&(x,y)|field(x as f64,y as f64,d,low,high,0.0)).collect()
}
// Independent f64 metric fit, not the cue/filter/gather arithmetic.
// Simultaneous two-tone fit removes finite-ROI and diagonal-frequency leakage.
fn coefficients(values:&[f32],kind:usize,d:usize) -> [f64;5] {
    let mut a=[[0.0;6];5];let (dx,dy)=direction(d);
    for (&v,(x,y)) in values.iter().zip(positions(kind)) {
        let u=dx*x as f64+dy*y as f64;
        let r=[1.0,(TAU*0.06*u).cos(),(TAU*0.06*u).sin(),
            (TAU*0.30*u).cos(),(TAU*0.30*u).sin()];
        for i in 0..5 {for j in 0..5 {a[i][j]+=r[i]*r[j];}a[i][5]+=r[i]*(v as f64-3000.0);}
    }
    for k in 0..5 {
        let p=(k..5).max_by(|i,j|a[*i][k].abs().partial_cmp(&a[*j][k].abs()).unwrap()).unwrap();
        a.swap(k,p);assert!(a[k][k].abs()>1e-6,"metric design rank");
        let t=a[k][k];for j in k..6 {a[k][j]/=t;}
        for i in 0..5 {if i!=k {let t=a[i][k];for j in k..6 {a[i][j]-=t*a[k][j];}}}
    }
    std::array::from_fn(|i|a[i][5])
}
#[derive(Clone)]
struct Score {rmse:f64,bias:f64,low:f64,high:f64,coef:[f64;5]}
fn score(values:&[f32],kind:usize,d:usize,low:bool,high:bool) -> Score {
    let ideal=truth(kind,d,low,high);
    assert_eq!(values.len(),ideal.len());assert!(values.iter().all(|v|v.is_finite()));
    let n=values.len() as f64;
    let bias=values.iter().zip(&ideal).map(|(a,b)|*a as f64-b).sum::<f64>()/n;
    let rmse=(values.iter().zip(&ideal).map(|(a,b)|(*a as f64-b).powi(2)).sum::<f64>()/n).sqrt();
    let c=coefficients(values,kind,d);
    let err=|i:usize,f:f64,a:f64,p:f64,present:bool|{
        let target=if present {amplitude(d,f,a)} else {0.0};
        (c[i]-target*p.cos()).hypot(c[i+1]+target*p.sin())/amplitude(d,f,a)
    };
    Score {rmse,bias,low:err(1,0.06,500.0,0.2,low),high:err(3,0.30,40.0,1.1,high),coef:c}
}
fn record(s:&Score) -> Value {
    json!({"rmse_dn":s.rmse,"bias_dn":s.bias,"low_relative_complex_error":s.low,
        "high_relative_complex_error":s.high,"fitted_coefficients_dn":s.coef})
}
fn mean(samples:&[Vec<f32>],omit:Option<usize>) -> Vec<f32> {
    let n=samples.len()-usize::from(omit.is_some());assert!(n>0);
    (0..samples[0].len()).map(|i|samples.iter().enumerate().filter(|(j,_)|Some(*j)!=omit)
        .map(|(_,a)|a[i] as f64).sum::<f64>() as f32/n as f32).collect()
}
fn temporal(samples:&[Vec<f32>],omit:Option<usize>) -> f64 {
    let n=samples.len()-usize::from(omit.is_some());assert!(n>1);
    (0..samples[0].len()).map(|i|{
        let (mut s,mut q)=(0.0,0.0);
        for (j,a) in samples.iter().enumerate() {if Some(j)!=omit {s+=a[i] as f64;q+=(a[i] as f64).powi(2);}}
        (q-s*s/n as f64)/(n-1) as f64
    }).sum::<f64>()/samples[0].len() as f64
}
fn jk_se(values:&[f64]) -> f64 {
    let n=values.len() as f64;let m=values.iter().sum::<f64>()/n;
    ((n-1.0)/n*values.iter().map(|v|(v-m).powi(2)).sum::<f64>()).sqrt()
}
fn literal_controls(fail:&mut Vec<String>) -> Value {
    let mut f=frame(0,false,false,0.0,None,0);let levels=f.levels;
    let noisy=model(levels,true);let quiet=model(levels,false);
    let centre=(24usize,22usize);let mut cases=Vec::new();
    for case in 0..3 {
        for y in 0..190 {for x in 0..274 {
            let p=2*(y&1)+(x&1);
            let s=3000+if case==1 {[0,32,-32,0][p]} else {0}
                +if case==2 {2*x as i32+3*y as i32+[0,32,-32,0][p]} else {0};
            f.data[(f.active.y+y)*f.stride+f.active.x+x]=(512+s) as u16;
        }}
        let out=cue::source_at(&f,levels,&noisy,centre.0,centre.1);
        check(fail,out.is_some(),format!("literal {case} support"));
        if let Some((e,v))=out {
            check(fail,e==0.0,format!("literal {case} rejects DC/imbalance/affine scene"));
            check(fail,v>0.0,format!("literal {case} injected noise live"));
            if case==0 {
                check(fail,(v-3755.0).abs()<0.001,"independent exact unique-sensel price 2.5*(751+751)");
                check(fail,(2.0*v-3755.0).abs()>0.001,"factor-two price destroyer fails same literal gate");
            }
            cases.push(json!({"case":case,"energy":e,"variance":v}));
        }
    }
    for (site,offset,expected) in [(1,(0,0),1.53125f32),(2,(0,0),1.53125),
        (1,(0,1),0.09375),(2,(0,1),0.09375),(0,(0,0),0.0),(3,(0,0),0.0)] {
        let mut p=frame(0,false,false,0.0,None,0);
        let (dx,dy)=PHASES[site];let x=2*(centre.0+offset.0)+dx;let y=2*(centre.1+offset.1)+dy;
        p.data[(p.active.y+y)*p.stride+p.active.x+x]+=4;
        let result=cue::source_at(&p,levels,&quiet,centre.0,centre.1).unwrap();
        check(fail,result.0==16.0*expected,format!("independent impulse site{site} offset{offset:?}"));
        check(fail,result.1==0.0,"noiseless impulse price");
        cases.push(json!({"site":site,"offset":offset,"energy":result.0,"expected":16.0*expected}));
    }
    // Exact affine fields with independent G1/G2 gains; integer source avoids
    // claiming that u16 quantization of arbitrary slopes is annihilated.
    let mut gain=frame(0,false,false,0.0,None,0);
    for y in centre.1-4..=centre.1+4 {for x in centre.0-4..=centre.0+4 {
        let u=(x as i32-centre.0 as i32)+2*(y as i32-centre.1 as i32);
        for (phase,base,slope) in [(1usize,3030,101),(2,2970,99)] {
            let (dx,dy)=PHASES[phase];
            gain.data[(gain.active.y+2*y+dy)*gain.stride+gain.active.x+2*x+dx]=(512+base+slope*u) as u16;
        }
    }}
    let gained=cue::source_at(&gain,levels,&noisy,centre.0,centre.1).unwrap();
    check(fail,gained.0==0.0,"exact affine green gains 1.01/.99 are not noise/detail");
    cases.push(json!({"case":"affine-phase-gain","energy":gained.0,"variance":gained.1}));
    let padded=frame(0,true,true,0.4,None,0);
    let mut packed=padded.clone();
    packed.data=(0..190).flat_map(|y|(0..274).map(move|x|(x,y)))
        .map(|(x,y)|padded.sample(x,y)).collect();
    packed.stride=274;packed.buffer_height=190;packed.active.x=0;packed.active.y=0;
    let p0=cue::source_at(&padded,levels,&noisy,centre.0,centre.1).unwrap();
    let p1=cue::source_at(&packed,levels,&noisy,centre.0,centre.1).unwrap();
    check(fail,p0==p1 && p0.0>0.0,"live padded-origin identity");
    let p=frame(0,false,false,0.0,None,0);
    check(fail,cue::source_at(&p,levels,&quiet,0,0).is_none(),"unsupported source abstains");
    let mut clipped=p.clone();
    clipped.data[(clipped.active.y+2*centre.1)*clipped.stride+clipped.active.x+2*centre.0+1]=15360;
    check(fail,cue::source_at(&clipped,levels,&quiet,centre.0,centre.1).is_none(),"clipped support abstains");
    // Smooth5 and bilinear transport reproduce an affine variance field.
    // Exact noise expectation for both affine green fields: V=5*(.25*Scentre+1).
    let mut affine=p;
    for y in 0..190 {for x in 0..274 {
        affine.data[(affine.active.y+y)*affine.stride+affine.active.x+x]=(512+3000+2*x+4*y) as u16;
    }}
    let t=Similarity::from_params(SimilarityParams {ax:0.375,ay:-0.25,g:0.012,rot:0.006});
    let prepared=cue::prepare(&affine,levels,&noisy,t,[9,6,W,H]);
    let (x,y)=(40usize,30usize);let q=(9.0+x as f64+0.25,6.0+y as f64+0.25);
    // Independent complex affine matrix, not Similarity::apply_at.
    let (cx,cy)=(68.5,47.5);
    let sx=cx+1.012*(q.0-cx)-0.006*(q.1-cy)+0.375;
    let sy=cy+0.006*(q.0-cx)+1.012*(q.1-cy)-0.25;
    let expected=5.0*(0.25*(3000.0+4.0*sx+8.0*sy)+1.0);
    let wrong_origin=5.0*(0.25*(3000.0+4.0*(sx-0.25)+8.0*(sy-0.25))+1.0);
    check(fail,prepared.valid[y*W+x],"interior prepared support");
    check(fail,(prepared.variance[y*W+x] as f64-expected).abs()<0.003,"independent phase-centred affine transport");
    check(fail,(expected-wrong_origin).abs()>1.0,"quarter-quad coordinate destroyer power");
    check(fail,!prepared.valid[0] && !prepared.valid[W*H-1],"strict smoothing-edge fallback");
    let off:Vec<Vec<f32>>=(0..8).map(|i|vec![i as f32-3.5,2.0*(i as f32-3.5)]).collect();
    let bad:Vec<Vec<f32>>=off.iter().map(|a|a.iter().map(|v|2.0*v).collect()).collect();
    check(fail,temporal(&bad,None)>temporal(&off,None)*3.99,"flat metric rejects manufactured noise");
    json!({"cases":cases,"transport_actual":prepared.variance[y*W+x],"transport_expected":expected,
        "transport_wrong_origin":wrong_origin,"flat_destroyer_ratio":temporal(&bad,None)/temporal(&off,None)})
}
fn fallback_controls(fail:&mut Vec<String>) -> Value {
    // Different input textures make ignoring valid=false observably wrong.
    // Both paths call the actual core accumulator/collapse, not a replica.
    let run=|mode:usize| {
        let (w,h)=(32usize,24usize);
        let cfg=MergeConfig {bands:3,..MergeConfig::default()};
        let mut merge=BandMerge::new(w,h,4,cfg);
        let mut work=FrameWorkspace::new(merge.sizes(),4);
        for k in 0..3 {
            let luma:Vec<f32>=(0..w*h).map(|i|3000.0+if k==0 {0.0}
                else {if (i%w+i/w)&1==0 {100.0/k as f32} else {-100.0/k as f32}}).collect();
            let planes=vec![luma.clone();4];let refs:Vec<&[f32]>=planes.iter().map(Vec::as_slice).collect();
            let variance=vec![10.0;w*h];work.next_frame();
            if mode==0 {merge.add_frame_with_gain(&refs,&luma,&variance,Some(&[1.0,1.0]),&mut work);}
            else {
                let supplied=cue::Cue {energy:vec![if k==0 {1e8} else {0.0};w*h],
                    variance:vec![0.0;w*h],valid:vec![mode==2;w*h]};
                merge.add_frame_with_green_cue(&refs,&luma,&variance,Some(&[1.0,1.0]),&mut work,&supplied);
            }
        }
        merge.finish(&mut Workspace::new(merge.sizes())).into_iter().flatten().map(f32::to_bits).collect::<Vec<_>>()
    };
    let old=run(0);let refused=run(1);let accepted=run(2);
    let changed=old.iter().zip(&accepted).filter(|(a,b)|a!=b).count();
    check(fail,old==refused,"all-invalid cue retains exact original core fallback");
    check(fail,changed>0,"same wrong-energy cue with valid=true has live consumer power");
    json!({"fallback_values":old.len(),"fallback_bits_equal":old==refused,"accepted_override_changed_values":changed})
}
fn metric_controls(fail:&mut Vec<String>) -> Value {
    let mut rows=Vec::new();
    for d in 0..3 {
        let f=frame(d,true,true,0.0,None,0);let planes=phase_planes(&f);let outputs=readouts(&planes);
        for kind in 0..2 {
            let s=score(&outputs[kind],kind,d,true,true);
            let a=amplitude(d,0.30,40.0);
            let recovered=s.coef[3].hypot(s.coef[4])/a;
            check(fail,recovered>=0.5 && s.high<=0.25,format!("sharp frequency survives d{d} readout{kind}"));
            rows.push(json!({"direction":d,"readout":kind,"amplitude_ratio":recovered,"score":record(&s)}));
        }
        if d==0 {
            let mut wrong=planes.clone();wrong.swap(1,2);let bad=readouts(&wrong);
            for kind in 0..2 {
                let a=score(&outputs[kind],kind,d,true,true);let b=score(&bad[kind],kind,d,true,true);
                check(fail,b.high>=a.high+0.10,format!("wrong phase metric power readout{kind}"));
            }
        }
    }
    for kind in 0..2 {
        let ideal:Vec<f32>=truth(kind,0,true,true).iter().map(|v|*v as f32).collect();
        let manufactured:Vec<f32>=positions(kind).iter().map(|&(x,y)|
            (field(x as f64,y as f64,0,true,true,0.0)
                +0.5*(field(x as f64,y as f64,0,false,true,0.0)-3000.0)) as f32).collect();
        let a=score(&ideal,kind,0,true,true);let b=score(&manufactured,kind,0,true,true);
        check(fail,b.high>=a.high+0.10,format!("manufactured detail metric power readout{kind}"));
        let wrong:Vec<f32>=positions(kind).iter().map(|&(x,y)|field((x+1) as f64,y as f64,0,true,true,0.0) as f32).collect();
        check(fail,score(&wrong,kind,0,true,true).high>a.high+0.10,"one-native-pixel registration destroyer");
    }
    json!(rows)
}
fn save(path:&std::path::Path, rows:&[Value],literal:&Value,metrics:&Value,fail:&[String],stacks:usize,stage:&str) {
    let result=json!({"schema":"native-green-cue-independent-v1","stage":stage,
        "decision":if fail.is_empty() {"PASS"} else {"REJECT"},
        "failures":fail,"stack_outputs":stacks,"literal_controls":literal,"metric_controls":metrics,
        "rows":rows,"scope":"actual collapsed CFA green samples and current demosaic green kernel; no TIFF/tone/profile or RAW claim"});
    std::fs::write(path,serde_json::to_vec_pretty(&result).unwrap()).unwrap();
}
#[test]
#[ignore = "root-owned fixed native green cue consumer"]
fn native_green_cue_consumer() {
    let path=std::path::PathBuf::from(std::env::var_os("STREHL_GREEN_CUE_OUT").expect("root-owned output path"));
    assert!(!path.exists(),"fresh receipt required");
    let (mut failures,mut rows,mut count)=(Vec::new(),Vec::new(),0usize);
    let literal=json!({"source":literal_controls(&mut failures),"consumer_fallback":fallback_controls(&mut failures)});
    let mut metrics=Value::Null;
    save(&path,&rows,&literal,&metrics,&failures,count,"literal-and-metric-controls");
    assert!(failures.is_empty(),"fixed literal/metric control refusal; see measurement JSON");
    let mut live_changed=0usize;let mut material=[false;3];
    // Flat is first. Detail is not executed if its noise-control gate fails.
    for scene in 0usize..4 {
        let d=scene.saturating_sub(1);let present=scene>0;
        let mut samples:Vec<Vec<Vec<Vec<f32>>>>=(0..2).map(|_|(0..2).map(|_|Vec::new()).collect()).collect();
        let mut quiet_scores:Vec<Vec<Score>>=vec![Vec::new(),Vec::new()];
        let mut per_scores:Vec<Vec<Vec<Score>>>=(0..2).map(|_|vec![Vec::new(),Vec::new()]).collect();
        for state in 0..9 {
            let seed=if state==0 {None} else {Some(SEEDS[state-1])};
            let mut pair=Vec::new();
            let frames:Vec<Frame>=BLURS.iter().enumerate().map(|(k,s)|frame(d,present,present,*s,seed,k)).collect();
            let injected=model(frames[0].levels,true);
            for on in [false,true] {
                let (planes,valid)=super::super::green_cue_consume(frames.clone(),&injected,on);
                count+=1;
                check(&mut failures,if on {valid>0} else {valid==0},format!("actual cue route scene{scene} state{state} on{on}"));
                let output=readouts(&planes);let arm=usize::from(on);
                let scores:Vec<Score>=(0..2).map(|kind|score(&output[kind],kind,d,present,present)).collect();
                rows.push(json!({"type":"stack","scene":scene,"direction":d,"seed":seed,"on":on,"cue_valid_sites":valid,
                    "scores":scores.iter().map(record).collect::<Vec<_>>()}));
                for kind in 0..2 {
                    if state==0 {quiet_scores[arm].push(scores[kind].clone());}
                    else {samples[arm][kind].push(output[kind].clone());per_scores[arm][kind].push(scores[kind].clone());}
                }
                pair.push(output);
            }
            live_changed+=pair[0][0].iter().zip(&pair[1][0]).filter(|(a,b)|a.to_bits()!=b.to_bits()).count();
        }
        let mut gains=[false;2];
        for kind in 0..2 {
            let off=&samples[0][kind];let on=&samples[1][kind];
            let m0=score(&mean(off,None),kind,d,present,present);
            let m1=score(&mean(on,None),kind,d,present,present);
            let loo:Vec<f64>=(0..8).map(|j|score(&mean(on,Some(j)),kind,d,present,present).rmse
                -score(&mean(off,Some(j)),kind,d,present,present).rmse).collect();
            let se=jk_se(&loo);
            let high_loo:Vec<f64>=(0..8).map(|j|score(&mean(on,Some(j)),kind,d,present,present).high
                -score(&mean(off,Some(j)),kind,d,present,present).high).collect();
            let high_se=jk_se(&high_loo);
            if scene==0 {
                let v0=temporal(off,None);let v1=temporal(on,None);
                let vd:Vec<f64>=(0..8).map(|j|temporal(on,Some(j))-temporal(off,Some(j))).collect();
                let vse=jk_se(&vd);
                check(&mut failures,v1<=v0,format!("flat temporal point readout{kind}"));
                check(&mut failures,v1-v0+1.96*vse<=0.05*v0,format!("flat temporal upper95 readout{kind}"));
                check(&mut failures,m1.rmse<=m0.rmse+1e-5,format!("flat mean-field RMSE readout{kind}"));
                check(&mut failures,quiet_scores[1][kind].rmse<=quiet_scores[0][kind].rmse+1e-5,
                    format!("flat noiseoff RMSE readout{kind}"));
                rows.push(json!({"type":"flat","readout":kind,"variance_off_dn2":v0,"variance_on_dn2":v1,
                    "variance_delta_dn2":v1-v0,"paired_jackknife_se_dn2":vse,"variance_loo_delta_dn2":vd}));
            } else {
                for (label,a,b) in [("quiet",&quiet_scores[0][kind],&quiet_scores[1][kind]),("mean",&m0,&m1)] {
                    check(&mut failures,b.rmse<=a.rmse+1e-5,format!("d{d} readout{kind} {label} RMSE"));
                    check(&mut failures,b.high<=a.high+1e-6,format!("d{d} readout{kind} {label} high coefficient"));
                    check(&mut failures,b.low<=a.low+0.002+1e-6,format!("d{d} readout{kind} {label} low coefficient"));
                }
                for j in 0..8 {
                    check(&mut failures,per_scores[1][kind][j].rmse<=1.05*per_scores[0][kind][j].rmse+1e-5,
                        format!("d{d} readout{kind} seed{} worst RMSE",SEEDS[j]));
                }
                gains[kind]=m0.high>=0.02 && m1.high<=0.95*m0.high;
            }
            rows.push(json!({"type":"mean-field","scene":scene,"readout":kind,"off":record(&m0),"on":record(&m1),
                "paired_mean_rmse_delta_dn":m1.rmse-m0.rmse,"paired_jackknife_se_dn":se,"rmse_loo_delta_dn":loo,
                "high_relative_error_delta":m1.high-m0.high,"high_paired_jackknife_se":high_se,"high_loo_delta":high_loo}));
        }
        if scene>0 {material[d]=gains[0]&&gains[1];}
        save(&path,&rows,&literal,&metrics,&failures,count,if scene==0 {"flat"} else {"mixed"});
        if scene==0 {
            assert!(failures.is_empty(),"fixed flat gate rejected; no detail population executed");
            metrics=metric_controls(&mut failures);
            save(&path,&rows,&literal,&metrics,&failures,count,"sharp-reconstruction-and-metric-controls");
            assert!(failures.is_empty(),"fixed metric/survival controls rejected; no mixed population executed");
        }
    }
    for d in 0..3 {
        let mut pair=Vec::new();
        let frames:Vec<Frame>=BLURS.iter().enumerate().map(|(k,s)|frame(d,true,false,*s,None,k)).collect();
        let injected=model(frames[0].levels,true);
        for on in [false,true] {
            let (planes,valid)=super::super::green_cue_consume(frames.clone(),&injected,on);count+=1;
            check(&mut failures,if on {valid>0} else {valid==0},"low-only actual route");
            let r=readouts(&planes);let scores:Vec<Score>=(0..2).map(|kind|score(&r[kind],kind,d,true,false)).collect();
            rows.push(json!({"type":"low-only","direction":d,"on":on,"scores":scores.iter().map(record).collect::<Vec<_>>()}));
            pair.push(scores);
        }
        for kind in 0..2 {
            check(&mut failures,pair[1][kind].rmse<=pair[0][kind].rmse+1e-5,format!("low-only d{d} readout{kind} RMSE"));
            check(&mut failures,pair[1][kind].low<=pair[0][kind].low+0.002+1e-6,format!("low-only d{d} readout{kind} low coefficient"));
            check(&mut failures,pair[1][kind].high<=pair[0][kind].high+1e-6,format!("low-only d{d} readout{kind} manufactured high tone"));
        }
    }
    check(&mut failures,live_changed>0,"candidate changes actual collapsed samples");
    check(&mut failures,material.iter().any(|v|*v),"same-direction >=5% high coefficient-error gain in both readouts");
    check(&mut failures,count==78,"fixed stack population");
    rows.push(json!({"type":"decision-witness","changed_collapsed_samples":live_changed,"material_directions":material}));
    save(&path,&rows,&literal,&metrics,&failures,count,"complete");
    assert!(failures.is_empty(),"fixed candidate rejected; see complete measurements");
}
