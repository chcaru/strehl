// Generated actual-consumer test: one unchanged merge, a different synthesis.
use super::*;
use sha2::{Digest,Sha256};
use strehl_core::align::Similarity;
use strehl_core::pyramid::{LevelSize,Pyramid,AdmissionMode,BaseBand,Fallback,Hull,SelectMode,
    donor_consistency_diagnostic as donor,real_source_contributions as retained,
    rb_own_guide_diagnostic as canonical,fine_support_candidate as held};
use super::shared_source_field::{hash16,hash32};
pub(crate) mod operator {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/consistent-reconstruction/operator.rs"));
}
use operator::{analysis,reconstruct,Solve};

#[derive(Clone,Copy,Debug,PartialEq,Eq,serde::Serialize)]
pub(crate) enum Mode { Off, Consistent }

fn consumer_same(a:&[Vec<f32>],b:&[Vec<f32>])->bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.len()==b.len()
        && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits()))
}
fn consumer_hashes(values:&[Vec<f32>])->Vec<String> {values.iter().map(|v|hash32(v)).collect()}
fn coefficient_hashes(values:&[Pyramid])->Vec<Vec<String>> {
    values.iter().map(|p|(0..p.levels()).map(|k|hash32(p.level(k))).collect()).collect()
}
fn consumer_digest(hash:Sha256)->String {hash.finalize().iter().map(|v|format!("{v:02x}")).collect()}
fn accumulator_hash(merge:&BandMerge,sizes:&[LevelSize])->String {
    let mut hash=Sha256::new();
    // All den, corrected scaled numerators, fallback sums and resolved targets,
    // at every reached band including the terminal. The hash is not a score.
    for(k,size)in sizes.iter().enumerate(){for j in 0..size.pixels(){
        for value in retained::state(merge,k,j){hash.update(value.to_bits().to_le_bytes());}
    }}consumer_digest(hash)
}
fn hull_hash(merge:&BandMerge,pixels:usize)->String {
    let mut hash=Sha256::new();for j in 0..pixels{
        for bounds in retained::hull(merge,j){for value in bounds{hash.update(value.to_bits().to_le_bytes());}}
    }consumer_digest(hash)
}
fn apply_input_hull(planes:&mut[Vec<f32>],merge:&BandMerge)->Result<()> {
    ensure!(planes.len()==4&&!planes[0].is_empty()
        &&planes.iter().all(|p|p.len()==planes[0].len()&&p.iter().all(|v|v.is_finite())),"invalid synthesis image");
    for j in 0..planes[0].len(){for(c,[lo,hi])in retained::hull(merge,j).into_iter().enumerate(){
        ensure!(lo.is_finite()&&hi.is_finite()&&lo<=hi,"invalid held input hull");
        planes[c][j]=planes[c][j].clamp(lo,hi);
    }}Ok(())
}
fn image_delta_l2(a:&[Vec<f32>],b:&[Vec<f32>])->Vec<f64> {
    a.iter().zip(b).map(|(a,b)|a.iter().zip(b).map(|(a,b)|{
        let d=*a as f64-*b as f64;d*d
    }).sum::<f64>().sqrt()).collect()
}
fn coefficient_residual_l2(sizes:&[LevelSize],image:&[f32],target:&Pyramid)->f64 {
    let actual=analysis(sizes,image);
    actual.iter().enumerate().map(|(k,p)|p.iter().zip(target.level(k)).map(|(a,b)|{
        let d=*a as f64-*b as f64;d*d
    }).sum::<f64>()).sum::<f64>().sqrt()
}

#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub active_sha256:String,pub known4_sha256:[String;4],
    pub guide_sha256:String,pub variance_sha256:String,pub beta:Vec<f32>,
    pub energy_sha256:Vec<String>,pub floor_sha256:Vec<String>,pub canonical_weight_sha256:Vec<String>,
    pub source_coefficients_sha256:Vec<Vec<String>>,pub source_unchanged:bool,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_pre_hull_planes4:Vec<Vec<f32>>,pub candidate_pre_hull_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,
    pub native_width:usize,pub native_height:usize,pub level_sizes:Vec<[usize;2]>,pub frames:Vec<FrameEvidence>,
    pub mode:Mode,pub candidate_valid:bool,pub solves:Vec<Solve>,
    pub canonical_coefficients_sha256:Vec<Vec<String>>,pub coefficients_after_sha256:Vec<Vec<String>>,
    pub accumulator_before_sha256:String,pub accumulator_after_sha256:String,
    pub hull_before_sha256:String,pub hull_after_sha256:String,pub held_state_bit_exact:bool,
    pub inconsistency_l2:Vec<f64>,pub pre_hull_delta_l2:Vec<f64>,pub final_delta_l2:Vec<f64>,
    pub baseline_averaged_fraction:Vec<f64>,
}

pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode)->Result<Comparison> {
    ensure!((1..=16).contains(&frames.len())&&frames.len()==transforms.len(),"bounded generated source count required");
    ensure!(cfg.select==SelectMode::SoftPower&&cfg.admission==AdmissionMode::HardFloor
        &&cfg.base==BaseBand::Mean&&cfg.fallback==Fallback::Mean&&cfg.hull==Hull::InputRange
        &&cfg.mean_coarse==0&&cfg.significance_scale==0.0,"held canonical merge required");
    ensure!(held::environment_mode()==held::Mode::Off
        &&align_cmd::native_gpu_integration::ca_stage::mode()?==align_cmd::native_gpu_integration::ca_stage::Mode::Current,
        "other candidates must be disabled");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()
        &&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probed route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        &&!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),
        "held Malvar/no-local-placement required");
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
    ensure!(first.active.width<=512&&first.active.height<=512
        &&wb[..3].iter().all(|v|v.is_finite()&&*v>0.0),"bounded generated extent/WB required");
    for(i,frame)in frames.iter().enumerate(){
        ensure!(!frame.path.exists()&&frame.geometry()==full&&frame.active==first.active&&frame.stride==first.stride
            &&frame.buffer_height==first.buffer_height&&frame.levels==first.levels&&frame.camera==first.camera
            &&frame.iso==first.iso&&frame.wb_coeffs[..3]==wb[..3],"generated source metadata differs");
        validate_pyramid_frame(frame,full,i)?;let id=strehl_raw::identity(&frame.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated no-CA scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),"full source support required");
    }
    let domain=PyramidDomain::cropped(full,crop)?;let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("consistent-reconstruction-generated",&entries),strategy:"independent supplied geometry".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"held canonical weights and coefficient targets; synthesis only".into(),
    },full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{
        fn len(&self)->usize{self.0.len()}fn decode(&self,i:usize)->Result<Frame>{Ok(self.0[i].clone())}
    }
    let source=Source(frames);let mut worker=BandWorker::new(domain,cfg);let mut evidence=Vec::new();
    for(i,frame)in frames.iter().enumerate(){
        let source_sha256=hash16(&frame.data);let active_sha256=super::rb_own_guide::active_hash(frame);
        ensure!(worker.fold(&source,i,frame.levels,noise,Some(&map),None)?,"canonical source refused");
        let fields=canonical::canonical_fields(&worker.merge,&worker.fws,(!worker.beta.is_empty()).then_some(worker.beta.as_slice()));
        let source_coefficients_sha256=(0..4).map(|c|(0..sizes.len()).map(|k|
            hash32(retained::coefficients(&worker.fws,k)[c])).collect()).collect();
        ensure!(hash16(&frame.data)==source_sha256,"canonical fold modified original CFA");
        evidence.push(FrameEvidence{source_sha256,active_sha256,known4_sha256:std::array::from_fn(|c|hash32(&worker.planes[c])),
            guide_sha256:hash32(&worker.luma),variance_sha256:hash32(&worker.var),beta:worker.beta.clone(),
            energy_sha256:consumer_hashes(&fields.energy),floor_sha256:consumer_hashes(&fields.floor),
            canonical_weight_sha256:consumer_hashes(&fields.weights),source_coefficients_sha256,source_unchanged:true});
    }
    let accumulator_before_sha256=accumulator_hash(&worker.merge,&sizes);
    let hull_before_sha256=hull_hash(&worker.merge,crop.width*crop.height);
    let targets=donor::resolved_coefficients(&worker.merge);
    let canonical_coefficients_sha256=coefficient_hashes(&targets);
    let baseline_averaged_fraction=worker.merge.averaged_fraction();
    let baseline_planes4=worker.merge.finish(&mut Workspace::new(&sizes));
    let baseline_pre_hull_planes4=targets.iter().map(|p|p.collapse(&mut Workspace::new(&sizes))).collect::<Vec<_>>();
    let mut canonical_check=baseline_pre_hull_planes4.clone();apply_input_hull(&mut canonical_check,&worker.merge)?;
    ensure!(consumer_same(&canonical_check,&baseline_planes4),"resolved target collapse/hull differs from actual finish");
    let inconsistency_l2=targets.iter().zip(&baseline_pre_hull_planes4)
        .map(|(target,image)|coefficient_residual_l2(&sizes,image,target)).collect();
    let mut solves=Vec::new();
    if mode==Mode::Consistent{for(c,target)in targets.iter().enumerate(){
        let bands=(0..target.levels()).map(|k|target.level(k).to_vec()).collect::<Vec<_>>();
        solves.push(reconstruct(&sizes,&bands,&baseline_pre_hull_planes4[c])?);
    }}
    let candidate_valid=mode==Mode::Off||solves.iter().all(|s|s.converged);
    // Refused solves are retained above. Baseline placeholders allow the screen
    // to save every case; candidate_valid=false MUST preclude quality scoring.
    let candidate_pre_hull_planes4=if mode==Mode::Consistent&&candidate_valid{
        solves.iter().map(|s|s.image.clone()).collect()
    }else{baseline_pre_hull_planes4.clone()};
    let mut candidate_planes4=candidate_pre_hull_planes4.clone();apply_input_hull(&mut candidate_planes4,&worker.merge)?;
    if mode==Mode::Off{ensure!(consumer_same(&candidate_planes4,&baseline_planes4),"off CFA identity failed");}
    let coefficients_after_sha256=coefficient_hashes(&donor::resolved_coefficients(&worker.merge));
    ensure!(coefficient_hashes(&targets)==canonical_coefficients_sha256,"solver changed supplied targets");
    let accumulator_after_sha256=accumulator_hash(&worker.merge,&sizes);
    let hull_after_sha256=hull_hash(&worker.merge,crop.width*crop.height);
    let held_state_bit_exact=accumulator_before_sha256==accumulator_after_sha256
        &&hull_before_sha256==hull_after_sha256&&canonical_coefficients_sha256==coefficients_after_sha256;
    ensure!(held_state_bit_exact,"reconstruction changed canonical merge state");
    ensure!(consumer_same(&baseline_planes4,&worker.merge.finish(&mut Workspace::new(&sizes))),"canonical output changed during reconstruction");
    for(frame,ev)in frames.iter().zip(&evidence){ensure!(hash16(&frame.data)==ev.source_sha256,"reconstruction changed original CFA");}
    let pre_hull_delta_l2=image_delta_l2(&baseline_pre_hull_planes4,&candidate_pre_hull_planes4);
    let final_delta_l2=image_delta_l2(&baseline_planes4,&candidate_planes4);
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    ensure!(baseline_rgb.iter().chain(&candidate_rgb).all(|v|v.is_finite()),"nonfinite final MHC RGB");
    if mode==Mode::Off{ensure!(baseline_rgb.iter().zip(&candidate_rgb).all(|(a,b)|a.to_bits()==b.to_bits()),"off final MHC identity failed");}
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_pre_hull_planes4,candidate_pre_hull_planes4,
        baseline_rgb,candidate_rgb,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),frames:evidence,mode,candidate_valid,solves,
        canonical_coefficients_sha256,coefficients_after_sha256,accumulator_before_sha256,accumulator_after_sha256,
        hull_before_sha256,hull_after_sha256,held_state_bit_exact,inconsistency_l2,pre_hull_delta_l2,final_delta_l2,
        baseline_averaged_fraction})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/consistent-reconstruction/independent-controls.rs"));
}
