//! Actual geometry-proposal -> native CFA gather -> core fusion commissioning.
//! Identity image geometry is supplied, not estimated. No optical-resolution claim.
pub use strehl_cli::session_align;
#[path="../../../../crates/strehl-cli/src/session-repeat-proposals.rs"]
mod proposals;
use anyhow::{Result,ensure};
use serde_json::{Value,json};
use std::path::Path;
use strehl_cli::session_sampling::{NativeSampler,SamplingDomain};
use strehl_core::{align::{Similarity,Cx,Resampler},noise::{NoiseModel,PlaneNoise,Levels,Provenance},
    plane::{QuadSource,PlaneGeometry},pyramid::{MergeConfig,session_fusion::{SessionMerge,
        GroupWorkspace,GroupPolicy,PreparedSource,SourceKey}}};
const W:usize=128;
const FULL:usize=134;
struct Raw(Vec<u16>);
impl QuadSource for Raw {
    fn geometry(&self)->PlaneGeometry {PlaneGeometry{width:FULL,height:FULL}}
    fn quad_rows(&self,y:usize)->(&[u16],&[u16]) {
        let i=y*FULL*4;(&self.0[i..i+2*FULL],&self.0[i+2*FULL..i+4*FULL])
    }
}
fn model(case:&str,pass:usize)->NoiseModel {
    NoiseModel::new([PlaneNoise{gain_dn_per_e:if case=="unequal-variance" && pass==1 {0.8}else{0.2},
        read_noise_e:5.,levels:Levels{black:512.,white:15360.}};4],100.,Provenance::Measured)
}
fn true_signal(case:&str,index:usize,c:usize,x:f32,y:f32)->f32 {
    let pass=index/4;let ordinal=index%4;
    let dc=if case=="flat-low" {20.}else{1200.+c as f32*80.};
    if case.starts_with("flat") {return dc;}
    if case.starts_with("psf-") {
        let sigma=if case=="psf-focus-sweep" || case=="psf-fine-focus-offset" {
            let z=if x<64. {0.5}else{2.5};
            let offset=if case=="psf-fine-focus-offset" && pass==1 {0.25}else{0.};
            0.8*(ordinal as f32+offset-z).abs()
        }else if pass==1 && (case=="psf-blur" || (case=="psf-blue-blur" && c==2)) {0.8}else{0.};
        // Exact Gaussian convolution response of each continuous sine component.
        // The two-depth focus fixture prescribes local Gaussian PSFs; it does
        // not model physical occlusion at their shared depth discontinuity.
        let g=|kx:f32,ky:f32|(-0.5*sigma*sigma*(kx*kx+ky*ky)).exp();
        return dc+100.*(g(0.73,0.)*(x*0.73).sin()+g(0.,0.41)*(y*0.41).cos()
            +0.5*g(0.31,0.83)*(x*0.31+y*0.83).sin());
    }
    let x=if case=="shift" && pass==1 {x+0.5}else{x};
    let mut amplitude=100.;
    if case=="focus-sweep" || case=="fine-focus-offset" {
        let z=if x<64. {0.5}else{2.5};
        let offset=if case=="fine-focus-offset" && pass==1 {0.25}else{0.};
        amplitude*=(-0.5*((ordinal as f32+offset-z)/0.8).powi(2)).exp();
    }
    if (case=="blur" || (case=="blue-blur" && c==2)) && pass==1 {amplitude*=0.8;}
    let signal=dc+amplitude*((x*0.73).sin()+(y*0.41).cos()+0.5*(x*0.31+y*0.83).sin());
    if case=="brightness" && pass==1 {signal+20.}else{signal}
}
fn next(state:&mut u64)->f32 {
    *state^=*state<<13;*state^=*state>>7;*state^=*state<<17;
    (((*state>>40) as f32)+0.5)/16777216.
}
fn raw(case:&str,index:usize,seed:Option<u64>)->Raw {
    let noise=model(case,index/4);let mut state=0x75a7_7193_59e8_bbb1_u64
        ^(index as u64+1).wrapping_mul(0x9e37_79b9_7f4a_7c15)^seed.unwrap_or(0);
    Raw((0..FULL*FULL*4).map(|i| {
        let x=i%(2*FULL);let y=i/(2*FULL);
        let plane=strehl_core::CfaPlane::rggb_at(x,y);
        let c=match plane {strehl_core::CfaPlane::R=>0,strehl_core::CfaPlane::G1=>1,
            strehl_core::CfaPlane::B=>2,strehl_core::CfaPlane::G2=>3};
        let signal=true_signal(case,index,c,(x/2) as f32-3.,(y/2) as f32-3.);
        let perturb=if seed.is_some() {
            let u=next(&mut state);let v=next(&mut state);
            (-2.*u.ln()).sqrt()*(std::f32::consts::TAU*v).cos()*noise.sigma(plane,signal)
        }else{0.};
        if case=="clipped" && index/4==1 && x>FULL {15360}
        else{(512.+signal+perturb).round().clamp(0.,65535.) as u16}
    }).collect())
}
struct Output {planes:[Vec<f32>;4],diagnostics:Value}
fn render(case:&str,groups:&[Vec<usize>],seed:Option<u64>,primary:Option<usize>)->Result<Output> {
    let cfg=MergeConfig{bands:7,gate:2.,exponent:2.,sharpen_per_octave:1.4,..Default::default()};
    let policy=GroupPolicy{primary,..Default::default()};
    let domain=SamplingDomain{full:PlaneGeometry{width:FULL,height:FULL},x:3,y:3,width:W,height:W};
    let mut sampler=NativeSampler::new(domain)?;
    let mut prepared=PreparedSource::new(W,W,cfg)?;
    let mut group=GroupWorkspace::new(W,W,cfg,policy)?;
    let mut merge=SessionMerge::new(W,W,cfg)?;
    for members in groups {
        for &index in members {
            let original=raw(case,index,seed);
            let noise=model(case,index/4);
            let measured=sampler.gather(&original,Levels{black:512.,white:15360.},
                Similarity{a:Cx::new(1.,0.),b:Cx::new(0.,0.)},None,Resampler::CatmullRom)?;
            prepared.prepare_with_masks(SourceKey{acquisition:index as u64,bracket:index/4},
                std::array::from_fn(|c|measured.planes[c].as_slice()),&noise,None,None,
                &measured.coverage,&measured.support,1.)?;
            merge.add_source(&mut group,&prepared)?;
        }
        merge.fold_group(&mut group)?;
    }
    let out=merge.finish()?;
    ensure!(out.valid.iter().all(|&v|v) && out.planes.iter().flatten().all(|v|v.is_finite()),"invalid actual consumer output");
    let diagnostics=out.diagnostics.iter().map(|d|json!({"averaged":d.averaged_coefficients,
        "single":d.single_source_coefficients,"ordinary_fallback":d.ordinary_fallback_coefficients,
        "primary_fallback":d.primary_fallback_coefficients,"saturated_fallback":d.saturated_fallback_coefficients})).collect::<Vec<_>>();
    Ok(Output{planes:out.planes,diagnostics:json!(diagnostics)})
}
fn groups()->Result<proposals::Plan> {
    use session_align::{EdgeReceipt,PairPurpose};
    let sources:Vec<_>=(0..8).map(|i|proposals::Source{index:i,pass:i/4,sha256:format!("{:064x}",i+1),
        log_scale:(i%4) as f64*0.0001}).collect();
    let mut edges=Vec::new();
    for i in 0..8 {for j in i+1..8 {
        edges.push(EdgeReceipt{i,j,purpose:PairPurpose::CrossProbe,stage:"native".into(),accepted:true,
            transform_bits:Some([(sources[j].log_scale-sources[i].log_scale).exp().to_bits(),0,0,0]),
            rms_plane_px:Some(0.1),lever_plane_px:Some(1000.),used:8,attempted:8,correlated:8,
            peak_mean:Some(0.99),refusal:None});
    }}
    proposals::plan(&sources,&edges,0.000025,proposals::RESERVATION_BYTES)
}
fn stats(a:&[f32],reference:&[f32])->Value {
    let indices:Vec<_>=(24..104).flat_map(|y|(24..104).map(move|x|y*W+x)).collect();
    let n=indices.len() as f64;
    let ma=indices.iter().map(|&i|f64::from(a[i])).sum::<f64>()/n;
    let mr=indices.iter().map(|&i|f64::from(reference[i])).sum::<f64>()/n;
    let mse=indices.iter().map(|&i|f64::from(a[i]-reference[i]).powi(2)).sum::<f64>()/n;
    let power=indices.iter().map(|&i|(f64::from(reference[i])-mr).powi(2)).sum::<f64>()/n;
    let cross=indices.iter().map(|&i|(f64::from(a[i])-ma)*(f64::from(reference[i])-mr)).sum::<f64>()/n;
    json!({"mse":mse,"mean_difference":ma-mr,"reference_ac_power":power,
        "centered_amplitude_transfer":if power>1e-9 {Some(cross/power)}else{None}})
}
fn main()->Result<()> {
    let args:Vec<_>=std::env::args().collect();ensure!((2..=3).contains(&args.len()),"fresh output path [psf] required");
    let out=Path::new(&args[1]);ensure!(!out.exists(),"output exists");
    rayon::ThreadPoolBuilder::new().num_threads(4).build_global()?;
    let plan=groups()?;
    ensure!(plan.groups==vec![vec![0,4],vec![1,5],vec![2,6],vec![3,7]],"unexpected proposed assignment");
    let singles:Vec<_>=(0..8).map(|i|vec![i]).collect();
    let legacy=vec![vec![0,4],vec![1],vec![2],vec![3],vec![5],vec![6],vec![7]];
    let pass_a:Vec<_>=(0..4).map(|i|vec![i]).collect();let pass_b:Vec<_>=(4..8).map(|i|vec![i]).collect();
    let arms=[("proposal",&plan.groups,None),("legacy-partial",&legacy,None),("all-single",&singles,None),
        ("proposal-primary-a",&plan.groups,Some(0)),("pass-a",&pass_a,None),("pass-b",&pass_b,None)];
    let original_cases=["flat-low","flat-bright","stationary","focus-sweep","fine-focus-offset",
        "blur","blue-blur","shift","brightness","clipped","unequal-variance"];
    let psf_cases=["flat-low","flat-bright","psf-blur","psf-blue-blur","psf-focus-sweep","psf-fine-focus-offset","clipped"];
    let cases:&[&str]=if args.get(2).is_some_and(|s|s=="psf") {&psf_cases}else{&original_cases};
    let mut rows=Vec::new();let mut temporal=Vec::new();
    for case in cases {
        let clean:Vec<_>=arms.iter().map(|(_,g,p)|render(case,g,None,*p)).collect::<Result<_>>()?;
        let unclipped=if *case=="clipped" {Some(render("stationary",&singles,None,None)?)}else{None};
        let mut mean:Vec<[Vec<f32>;4]>=(0..arms.len()).map(|_|std::array::from_fn(|_|vec![0.;W*W])).collect();
        let mut m2=mean.clone();
        for (a,(name,_,_)) in arms.iter().enumerate() {
            rows.push(json!({"case":case,"arm":name,"seed":null,"diagnostics":clean[a].diagnostics,
                "against_clean_all_single":(0..4).map(|c|stats(&clean[a].planes[c],&clean[2].planes[c])).collect::<Vec<_>>(),
                "against_clean_passes":(4..6).map(|r|(0..4).map(|c|stats(&clean[a].planes[c],&clean[r].planes[c])).collect::<Vec<_>>()).collect::<Vec<_>>(),
                "against_unclipped_consumer_sentinel":unclipped.as_ref().map(|r|(0..4).map(|c|stats(&clean[a].planes[c],&r.planes[c])).collect::<Vec<_>>())}));
        }
        for seed in 160..168 {
            for (a,(name,g,p)) in arms.iter().enumerate() {
                let measured=render(case,g,Some(seed),*p)?;
                let count=(seed-159) as f32;
                for c in 0..4 {for i in 0..W*W {
                    let delta=measured.planes[c][i]-mean[a][c][i];mean[a][c][i]+=delta/count;
                    m2[a][c][i]+=delta*(measured.planes[c][i]-mean[a][c][i]);
                }}
                rows.push(json!({"case":case,"arm":name,"seed":seed,"diagnostics":measured.diagnostics,
                    "against_clean_all_single":(0..4).map(|c|stats(&measured.planes[c],&clean[2].planes[c])).collect::<Vec<_>>(),
                    "against_clean_passes":(4..6).map(|r|(0..4).map(|c|stats(&measured.planes[c],&clean[r].planes[c])).collect::<Vec<_>>()).collect::<Vec<_>>(),
                    "against_unclipped_consumer_sentinel":unclipped.as_ref().map(|r|(0..4).map(|c|stats(&measured.planes[c],&r.planes[c])).collect::<Vec<_>>())}));
            }
        }
        for (a,(name,_,_)) in arms.iter().enumerate() {
            let variance:Vec<_>=(0..4).map(|c|(24..104).flat_map(|y|(24..104).map(move|x|y*W+x))
                .map(|i|f64::from(m2[a][c][i])/7.).sum::<f64>()/6400.).collect();
            temporal.push(json!({"case":case,"arm":name,"realizations":8,"sample_temporal_variance":variance,
                "mean_against_clean_all_single":(0..4).map(|c|stats(&mean[a][c],&clean[2].planes[c])).collect::<Vec<_>>(),
                "mean_against_clean_passes":(4..6).map(|r|(0..4).map(|c|stats(&mean[a][c],&clean[r].planes[c])).collect::<Vec<_>>()).collect::<Vec<_>>()}));
        }
        eprintln!("completed {case}");
    }
    let result=json!({"schema":"strehl.repeat-proposal-consumer-controls.v1","plan":plan,"rows":rows,"temporal_summary":temporal,
        "workers":4,"original_storage":"u16 active RGGB; one source at a time",
        "scope":"Synthetic identity-image-geometry actual NativeSampler/PreparedSource/SessionMerge path. Proposal graph is supplied mechanical input, not an alignment calibration. Gaussian temporal plant uses injected affine noise then u16 rounding; quantization is not fitted away. Clean pass/all-single references are actual noise-gated consumers, not per-band argmax. Centered80x80 per-CFA transfer/risk only; no real optical or photographic quality follows.","command":args});
    std::fs::write(out,format!("{}\n",serde_json::to_string_pretty(&result)?))?;Ok(())
}
