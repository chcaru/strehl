// Generated actual-consumer adapter reused from cross-scale-source-prior.
// Only the coarse-weight intervention differs; root owns build/execution.
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{cross_scale_source_prior_diagnostic as invariant,
    fine_support_candidate as held,Hull,Fallback};
use super::shared_source_field::{hash16,hash32};
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/band-source-agreement/operator.rs"));

#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub known4_sha256:[String;4],pub guide_sha256:String,
    pub variance_sha256:String,pub beta:Vec<f32>,pub energy_sha256:Vec<String>,pub floor_sha256:Vec<String>,
    pub canonical_weight_sha256:Vec<String>,pub candidate_weight_sha256:Vec<String>,
    pub membership_sha256:Vec<String>,pub changes:WeightChanges,pub replay_exact:bool,pub source_unchanged:bool,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,pub native_width:usize,pub native_height:usize,
    pub level_sizes:Vec<[usize;2]>,pub frames:Vec<FrameEvidence>,pub agreement:BandAgreement,
    pub held_state_bit_exact:bool,pub baseline_averaged_fraction:Vec<f64>,pub candidate_averaged_fraction:Vec<f64>,
    pub forced_source:Option<usize>,
}
fn same(a:&[f32],b:&[f32])->bool {a.len()==b.len() && a.iter().zip(b).all(|(x,y)|x.to_bits()==y.to_bits())}
fn same_planes(a:&[Vec<f32>],b:&[Vec<f32>])->bool {a.len()==b.len() && a.iter().zip(b).all(|(x,y)|same(x,y))}
fn hashes(v:&[Vec<f32>])->Vec<String>{v.iter().map(|p|hash32(p)).collect()}
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode)->Result<Comparison> {
    compare_inner(frames,transforms,crop,noise,cfg,mode,None)
}
/// Commissioning destroyer only: coarse weights become a supplied one-hot source.
pub(crate) fn compare_generated_forced(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced_source:usize)->Result<Comparison> {
    ensure!(mode==Mode::Agreement && forced_source<frames.len(),"invalid explicit coarse-source destroyer");
    compare_inner(frames,transforms,crop,noise,cfg,mode,Some(forced_source))
}
fn compare_inner(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced_source:Option<usize>)->Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len()<=70 && frames.len()==transforms.len(),"bounded generated source count");
    ensure!(cfg.select==SelectMode::SoftPower && cfg.admission==AdmissionMode::HardFloor
        && cfg.base==BaseBand::Mean && cfg.fallback==Fallback::Mean && cfg.hull==Hull::InputRange
        && cfg.mean_coarse==0 && cfg.significance_scale==0.0,"held coarse-only merge configuration");
    ensure!(held::environment_mode()==held::Mode::Off
        && align_cmd::native_gpu_integration::ca_stage::mode()?==align_cmd::native_gpu_integration::ca_stage::Mode::Current,
        "other candidate modes must be disabled");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probed route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        && !std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),
        "held Malvar/no local placement required");
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
    ensure!(first.active.width<=512 && first.active.height<=512
        && wb[..3].iter().all(|v|v.is_finite() && *v>0.0),"small generated extent/WB required");
    for (index,frame) in frames.iter().enumerate() {
        ensure!(!frame.path.exists() && frame.geometry()==full && frame.active==first.active
            && frame.stride==first.stride && frame.buffer_height==first.buffer_height
            && frame.levels==first.levels && frame.camera==first.camera && frame.iso==first.iso
            && frame.wb_coeffs[..3]==wb[..3],"generated scope or metadata drift");
        validate_pyramid_frame(frame,full,index)?;let id=strehl_raw::identity(&frame.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated no-CA scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[index],full,crop,None),"generated source pull unsupported");
    }
    let domain=PyramidDomain::cropped(full,crop)?;let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let mut sum=AgreementSum::new(&sizes,frames.len())?;
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("band-source-agreement-generated",&entries),strategy:"independent supplied geometry".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"own-band stationary-identity harmonic source agreement".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()}fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);let mut baseline=BandWorker::new(domain,cfg);let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let source_sha256=hash16(&frame.data);
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?,"first-pass source refused");
        let fields=core::canonical_fields(&baseline.merge,&baseline.fws,(!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()));
        sum.add(&fields.weights)?;ensure!(hash16(&frame.data)==source_sha256,"first pass changed original CFA");
        evidence.push(FrameEvidence{source_sha256,known4_sha256:std::array::from_fn(|c|hash32(&baseline.planes[c])),
            guide_sha256:hash32(&baseline.luma),variance_sha256:hash32(&baseline.var),beta:baseline.beta.clone(),
            energy_sha256:hashes(&fields.energy),floor_sha256:hashes(&fields.floor),canonical_weight_sha256:hashes(&fields.weights),
            candidate_weight_sha256:vec![],membership_sha256:vec![],changes:WeightChanges{changed:vec![],zeroed_positive:vec![],bypassed:vec![],rounding_fallback:vec![]},
            replay_exact:false,source_unchanged:true});
    }
    let agreement=sum.finish()?;let baseline_averaged_fraction=baseline.merge.averaged_fraction();
    let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    let mut replay=BandWorker::new(domain,cfg);let mut candidate=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut candidate_ws=FrameWorkspace::new(&sizes,4);
    for (index,frame) in frames.iter().enumerate() {
        ensure!(replay.fold(&source,index,frame.levels,noise,Some(&map),None)?,"replay source refused");let ev=&mut evidence[index];
        ensure!(ev.known4_sha256==std::array::from_fn(|c|hash32(&replay.planes[c]))
            && ev.guide_sha256==hash32(&replay.luma) && ev.variance_sha256==hash32(&replay.var)
            && same(&ev.beta,&replay.beta),"actual source replay differs");
        let mut fields=core::canonical_fields(&replay.merge,&replay.fws,(!replay.beta.is_empty()).then_some(replay.beta.as_slice()));
        ensure!(ev.energy_sha256==hashes(&fields.energy) && ev.floor_sha256==hashes(&fields.floor)
            && ev.canonical_weight_sha256==hashes(&fields.weights),"actual E/F/weight replay differs");
        ev.membership_sha256=hashes(&agreement.memberships(&fields.weights)?);
        ev.changes=if let Some(forced)=forced_source {
            let mut changes=agreement.apply(&mut fields,Mode::Neutral)?;
            for k in 1..fields.weights.len() {
                changes.bypassed[k]=0;let new:f32=if index==forced {1.0}else{0.0};
                for w in &mut fields.weights[k] {
                    changes.changed[k]+=usize::from(w.to_bits()!=new.to_bits());
                    changes.zeroed_positive[k]+=usize::from(*w>0.0 && new==0.0);*w=new;
                }
            }changes
        } else {agreement.apply(&mut fields,mode)?};
        ev.candidate_weight_sha256=hashes(&fields.weights);
        ensure!(ev.candidate_weight_sha256[0]==ev.canonical_weight_sha256[0],"finest weight changed");
        core::add_fields(&mut candidate,&replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),&fields,&mut candidate_ws);
        ensure!(invariant::held_state_bit_exact(&replay.merge,&candidate),"candidate changed b0/base/fallback/hull state");
        ensure!(hash16(&frame.data)==ev.source_sha256,"replay changed original CFA");ev.replay_exact=true;
    }
    ensure!(same_planes(&baseline_planes4,&replay.merge.finish(&mut Workspace::new(&sizes))),"baseline differs between passes");
    let held_state_bit_exact=invariant::held_state_bit_exact(&baseline.merge,&candidate);ensure!(held_state_bit_exact,"final held state differs");
    let candidate_averaged_fraction=candidate.averaged_fraction();let candidate_planes4=candidate.finish(&mut Workspace::new(&sizes));
    if mode!=Mode::Agreement {ensure!(same_planes(&baseline_planes4,&candidate_planes4),"disabled/neutral output differs");}
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    ensure!(baseline_rgb.iter().chain(&candidate_rgb).all(|v|v.is_finite()),"nonfinite developed output");
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),frames:evidence,agreement,held_state_bit_exact,
        baseline_averaged_fraction,candidate_averaged_fraction,forced_source})
}
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/band-source-agreement/independent-controls.rs"));
}
