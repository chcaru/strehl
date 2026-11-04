//! Conditional incremental-noise experiment through the actual session consumer.
//! The fixed original-CFA texture is a fixture, not estimated scene truth.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};
use strehl_core::{CfaPlane, noise::{Levels, NoiseModel, PlaneNoise, Provenance},
    pyramid::{MergeConfig, session_fusion::{FrozenPrediction, GroupMode, GroupPolicy, GroupFocusReference,
        GroupWorkspace, PreparedSource, SessionMerge}}};

type Planes = [Vec<f32>;4];
#[derive(Clone, Copy)]
enum Arm { Short, Long, Combined, Equal, Precision, NoisyGuide, FrozenFocus, FrozenFocusNoisy, MissingGuide }
impl Arm {
    fn name(self)->&'static str {match self {Self::Short=>"short",Self::Long=>"long",Self::Combined=>"combined",Self::Equal=>"equal",Self::Precision=>"precision",Self::NoisyGuide=>"noisy-guide",Self::FrozenFocus=>"frozen-focus",Self::FrozenFocusNoisy=>"frozen-focus-noisy",Self::MissingGuide=>"missing-guide"}}
}
fn uniform(state:&mut u64)->f32 {
    *state ^= *state << 13; *state ^= *state >> 7; *state ^= *state << 17;
    (((*state >> 40) as u32) as f32 + 0.5) / 16777216.0
}
fn gaussian(state:&mut u64)->f32 {(-2.0*uniform(state).ln()).sqrt()*(std::f32::consts::TAU*uniform(state)).cos()}
fn sha(bytes:&[u8])->String {Sha256::digest(bytes).iter().map(|b|format!("{b:02x}")).collect()}
fn frozen_noisy_guide(truth:&Planes,noise:&NoiseModel,w:usize,h:usize,gain:f32,slice:usize)->(Planes,Vec<bool>) {
    let mut rng=765492551+slice as u64;
    let mut measured=truth.clone();
    for c in 0..4 {for v in &mut measured[c] {let original=*v/gain;*v=(original+gaussian(&mut rng)*noise.variance(CfaPlane::ALL[c],original).sqrt())*gain;}}
    let mut mean=std::array::from_fn(|_|vec![0.;w*h]);let mut support=vec![false;w*h];
    for y in 8..h-8 {for x in 8..w-8 {support[y*w+x]=true;
        for c in 0..4 {let mut sum=0_f64;for yy in y-8..=y+8 {for xx in x-8..=x+8 {sum+=f64::from(measured[c][yy*w+xx]);}}mean[c][y*w+x]=(sum/289.) as f32;}
    }}
    (mean,support)
}
fn render(groups:&[Planes], noise:&NoiseModel, w:usize,h:usize,gain:f32,arm:Arm,trial:Option<u64>)->Result<(Planes,Value)> {
    let config=MergeConfig {bands:7,gate:2.0,exponent:2.0,sharpen_per_octave:1.4,..MergeConfig::default()};
    let policy=GroupPolicy {mode:if matches!(arm,Arm::Combined) {GroupMode::Combine}else{GroupMode::Repeat},..GroupPolicy::default()};
    let precision=matches!(arm,Arm::Precision|Arm::NoisyGuide|Arm::FrozenFocus|Arm::FrozenFocusNoisy|Arm::MissingGuide);
    let mut group=GroupWorkspace::new_with_precision(w,h,config,policy,precision)?;
    let mut merge=SessionMerge::new(w,h,config)?;
    let mut source=PreparedSource::new(w,h,config)?;
    let n=w*h;let coverage=vec![true;n];let mut support=vec![true;n];
    for (slice,truth) in groups.iter().enumerate() {
        let noisy_guide=matches!(arm,Arm::NoisyGuide|Arm::FrozenFocusNoisy).then(||frozen_noisy_guide(truth,noise,w,h,gain,slice));
        for bracket in 0..2 {
            if matches!((arm,bracket),(Arm::Short,1)|(Arm::Long,0)) {continue;}
            let scale=if bracket==0 {gain}else{1.0};
            let prediction:Planes=std::array::from_fn(|c|truth[c].iter().map(|v|v/scale).collect());
            let mut measured=prediction.clone();
            let mut random=1+0x75e416db83_u64.wrapping_mul(trial.unwrap_or(0)+1)+0xa975_u64.wrapping_mul((slice*2+bracket+1) as u64);
            support.fill(true);
            for c in 0..4 {
                let plane=CfaPlane::ALL[c];let range=noise.plane(plane).levels.range();
                for (i,v) in measured[c].iter_mut().enumerate() {
                    if trial.is_some() {*v+=gaussian(&mut random)*noise.variance(plane,prediction[c][i]).sqrt();}
                    support[i] &= *v < range;
                    *v=(*v).min(range);
                }
            }
            source.prepare_with_masks(strehl_core::pyramid::session_fusion::SourceKey {acquisition:(slice*2+bracket) as u64,bracket},
                std::array::from_fn(|c|measured[c].as_slice()),noise,None,None,&coverage,&support,scale)?;
            if matches!(arm,Arm::Precision|Arm::NoisyGuide|Arm::FrozenFocus|Arm::FrozenFocusNoisy) {
                // Deliberately ideal, frozen and disjoint guide isolates the
                // weighting operator. Real noisy guide quality is not inferred.
                let noisy_prediction=noisy_guide.as_ref().map(|(p,_)|std::array::from_fn::<Vec<f32>,4,_>(|c|p[c].iter().map(|v|v/scale).collect()));
                let (predicted,predicted_support)=if let (Some(p),Some((_,s)))=(&noisy_prediction,&noisy_guide) {(p,s)}else{(&prediction,&coverage)};
                source.predict_precision(FrozenPrediction {acquisition:(100+slice) as u64,
                    signal:std::array::from_fn(|c|predicted[c].as_slice()),support:predicted_support},noise,scale,None,None)?;
            }
            merge.add_source(&mut group,&source)?;
        }
        if matches!(arm,Arm::FrozenFocus|Arm::FrozenFocusNoisy) {
            merge.fold_group_with_focus_reference(&mut group,GroupFocusReference::EqualObservation)?;
        } else { merge.fold_group(&mut group)?; }
    }
    let out=merge.finish()?;
    let counts:Vec<_>=out.diagnostics.iter().map(|v|json!({"precision":v.precision_averaged_coefficients,"missing_prediction":v.missing_prediction_coefficients})).collect();
    Ok((out.planes,json!(counts)))
}
fn write_f32(path:&Path,planes:&Planes)->Result<()> {
    let mut f=fs::OpenOptions::new().create_new(true).write(true).open(path)?;
    for p in planes {for v in p {f.write_all(&v.to_le_bytes())?;}}f.sync_all()?;Ok(())
}
fn main()->Result<()> {
    let args:Vec<_>=std::env::args().collect();ensure!(args.len()==3,"expected fixture.json fresh-output-directory");
    let input=Path::new(&args[1]);let output=Path::new(&args[2]);ensure!(!output.exists(),"output exists");
    let bytes=fs::read(input)?;let fixture:Value=serde_json::from_slice(&bytes)?;
    ensure!(fixture["schema"]=="strehl.incremental-noise-fixture.v1","wrong input schema");
    let w=fixture["width"].as_u64().context("width")? as usize;let h=fixture["height"].as_u64().context("height")? as usize;
    ensure!(w==128&&h==128,"only bounded 128-quad fixtures accepted");
    let gain=fixture["gain_short_to_common"].as_f64().context("gain")? as f32;
    let model:Vec<_>=fixture["noise_planes"].as_array().context("noise")?.iter().map(|p|PlaneNoise {
        gain_dn_per_e:p["gain_dn_per_e"].as_f64().unwrap() as f32,read_noise_e:p["read_noise_e"].as_f64().unwrap() as f32,
        levels:Levels {black:p["black"].as_f64().unwrap() as f32,white:p["white"].as_f64().unwrap() as f32}}).collect();
    let noise=NoiseModel::new(model.try_into().map_err(|_|anyhow::anyhow!("four planes required"))?,100.,Provenance::Profile);
    let pool=rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    fs::create_dir(output)?;let mut results=Vec::new();
    // Flat is always exercised first. No output-derived region selection.
    for scene in ["flat","original-texture"] {
        let mut groups=Vec::new();
        for row in fixture["files"].as_array().unwrap().iter().filter(|v|v["scene"]==scene) {
            let name=row["file"].as_str().unwrap();ensure!(!name.contains(['/', '\\']),"fixture file must be basename");
            let payload=fs::read(input.parent().unwrap().join(name))?;
            ensure!(row["sha256"].as_str()==Some(sha(&payload).as_str()),"fixture hash changed");
            ensure!(payload.len()==w*h*4*4,"fixture shape differs");
            let values:Vec<_>=payload.chunks_exact(4).map(|v|f32::from_le_bytes(v.try_into().unwrap())).collect();
            ensure!(values.iter().all(|v|v.is_finite()),"nonfinite fixture");
            groups.push(std::array::from_fn(|c|values[c*w*h..(c+1)*w*h].to_vec()));
        }
        ensure!(groups.len()==if scene=="flat" {1}else{3},"fixture groups differ");
        let valid:Vec<_>=(0..w*h).map(|i|(0..4).all(|c|groups[0][c][i]>100.&&groups[0][c][i]<12000.)).collect();
        ensure!(valid.iter().filter(|&&v|v).count()>w*h/4,"insufficient predeclared midtones");
        for arm in [Arm::Short,Arm::Long,Arm::Combined,Arm::Equal,Arm::Precision,Arm::NoisyGuide,Arm::FrozenFocus,Arm::FrozenFocusNoisy,Arm::MissingGuide] {
            let (clean,_)=pool.install(||render(&groups,&noise,w,h,gain,arm,None))?;
            let mut mean=[vec![0_f64;w*h],vec![0.;w*h],vec![0.;w*h],vec![0.;w*h]];
            let mut m2=mean.clone();let mut counts=json!(null);let trials=48;
            for trial in 0..trials {
                let (image,diagnostics)=pool.install(||render(&groups,&noise,w,h,gain,arm,Some(trial)))?;counts=diagnostics;
                for c in 0..4 {for i in 0..w*h {let delta=f64::from(image[c][i])-mean[c][i];mean[c][i]+=delta/(trial+1) as f64;m2[c][i]+=delta*(f64::from(image[c][i])-mean[c][i]);}}
            }
            let delivered:Planes=std::array::from_fn(|c|mean[c].iter().map(|v|*v as f32).collect());
            let variance:Planes=std::array::from_fn(|c|m2[c].iter().map(|v|(*v/(trials-1) as f64) as f32).collect());
            let stats:Vec<_>=(0..4).map(|c| {
                let ids:Vec<_>=valid.iter().enumerate().filter_map(|(i,&v)|v.then_some(i)).collect();
                let n=ids.len() as f64;let baseline=ids.iter().map(|&i|f64::from(clean[c][i])).sum::<f64>()/n;
                let den=ids.iter().map(|&i|(f64::from(clean[c][i])-baseline).powi(2)).sum::<f64>();
                json!({"temporal_variance":ids.iter().map(|&i|f64::from(variance[c][i])).sum::<f64>()/n,
                    "mean_bias":ids.iter().map(|&i|mean[c][i]-f64::from(clean[c][i])).sum::<f64>()/n,
                    "mean_rmse_to_clean_same_arm":(ids.iter().map(|&i|(mean[c][i]-f64::from(clean[c][i])).powi(2)).sum::<f64>()/n).sqrt(),
                    "signal_projection_gain":(den>0.01).then(||ids.iter().map(|&i|(f64::from(clean[c][i])-baseline)*(mean[c][i]-baseline)).sum::<f64>()/den)})
            }).collect();
            write_f32(&output.join(format!("{scene}-{}-mean.f32",arm.name())),&delivered)?;
            write_f32(&output.join(format!("{scene}-{}-variance.f32",arm.name())),&variance)?;
            write_f32(&output.join(format!("{scene}-{}-clean.f32",arm.name())),&clean)?;
            let report=json!({"scene":scene,"arm":arm.name(),"trials":trials,"predeclared_midtone_pixels":valid.iter().filter(|&&v|v).count(),"planes":stats,"last_trial_diagnostics":counts});
            println!("{report}");results.push(report);
        }
    }
    fs::write(output.join("report.json"),serde_json::to_vec_pretty(&json!({"schema":"strehl.incremental-noise-controls.v1","fixture_sha256":sha(&bytes),"source_sha256":sha(include_bytes!("noise-transfer-controls.rs")),"workers":4,"recipe":{"bands":7,"gate":2.,"exponent":2.,"sharpen_per_octave":1.4},"scope":"Actual production coefficient consumer under conditional simulated temporal noise. Identity geometry, ideal withheld guides, planted defocus, fixed original CFA texture. No camera calibration or real-photograph quality validation.","results":results}))?)?;
    Ok(())
}
