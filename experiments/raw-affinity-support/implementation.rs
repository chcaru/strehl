// Generated actual-consumer falsifier only. No full RAW adapter or core mutation.
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{rb_own_guide_diagnostic as core,fine_support_candidate as held,Hull,Fallback};
use super::shared_source_field::{hash16,hash32};
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/raw-affinity-support/affinity.rs"));

#[derive(Clone,Debug,serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub known4_sha256:[String;4],pub guide_sha256:String,
    pub variance_sha256:String,pub beta:Vec<f32>,pub descriptor_sha256:String,
    pub canonical_energy_sha256:String,pub canonical_floor_sha256:String,
    pub pooled_energy_sha256:String,pub pooled_floor_sha256:String,pub weight_sha256:String,
    pub replay_exact:bool,pub source_unchanged:bool,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,
    pub native_width:usize,pub native_height:usize,pub level_sizes:Vec<[usize;2]>,
    pub frames:Vec<FrameEvidence>,pub non_finest_bit_exact:bool,
    pub baseline_averaged_fraction:Vec<f64>,pub candidate_averaged_fraction:Vec<f64>,
    pub affinity:Affinity,pub forced_source:Option<usize>,
}
fn same_planes(a:&[Vec<f32>],b:&[Vec<f32>])->bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.len()==b.len()
        && a.iter().zip(b).all(|(x,y)|x.to_bits()==y.to_bits()))
}
fn descriptor_hash(values:&[[f32;4]])->String {
    hash32(&values.iter().flatten().copied().collect::<Vec<_>>())
}
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode)->Result<Comparison> {
    compare_inner(frames,transforms,crop,noise,cfg,mode,None)
}
/// Explicit commissioning destroyer only. No algorithm chooses this source.
pub(crate) fn compare_generated_forced(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced_source:usize)->Result<Comparison> {
    ensure!(mode==Mode::Affinity && forced_source<frames.len(),"invalid explicit finest-source destroyer");
    compare_inner(frames,transforms,crop,noise,cfg,mode,Some(forced_source))
}
fn compare_inner(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced_source:Option<usize>)->Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len()<=70 && frames.len()==transforms.len(),"bounded generated source count");
    ensure!(cfg.select==SelectMode::SoftPower && cfg.admission==AdmissionMode::HardFloor
        && cfg.base==BaseBand::Mean && cfg.fallback==Fallback::Mean && cfg.hull==Hull::InputRange
        && cfg.mean_coarse==0 && cfg.significance_scale==0.0,"held finest-only merge configuration");
    ensure!(held::environment_mode()==held::Mode::Off,"other fine-support mode must be disabled");
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
        validate_pyramid_frame(frame,full,index)?;
        let id=strehl_raw::identity(&frame.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated no-CA scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[index],full,crop,None),"generated source pull unsupported");
    }
    let domain=PyramidDomain::cropped(full,crop)?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);ensure!(sizes.len()>1,"at least one actual AC band required");
    let grid=BlockGrid::new(crop.width,crop.height)?;
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("raw-affinity-support-generated",&entries),strategy:"independent supplied geometry".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"small scalar temporal-affinity falsifier; no fitted geometry".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()}
        fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);let mut baseline=BandWorker::new(domain,cfg);
    let mut means=Vec::with_capacity(frames.len());let mut evidence=Vec::with_capacity(frames.len());
    // Retain only four scalar block means per original source. Actual CFA stays u16.
    for (index,frame) in frames.iter().enumerate() {
        let source_sha256=hash16(&frame.data);
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?,"generated first-pass source refused");
        let descriptor=block_means4(&baseline.planes,&grid)?;
        let fields=core::canonical_fields(&baseline.merge,&baseline.fws,
            (!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()));
        ensure!(hash16(&frame.data)==source_sha256,"first pass changed original CFA");
        evidence.push(FrameEvidence{source_sha256,known4_sha256:std::array::from_fn(|c|hash32(&baseline.planes[c])),
            guide_sha256:hash32(&baseline.luma),variance_sha256:hash32(&baseline.var),beta:baseline.beta.clone(),
            descriptor_sha256:descriptor_hash(&descriptor),canonical_energy_sha256:hash32(&fields.energy[0]),
            canonical_floor_sha256:hash32(&fields.floor[0]),pooled_energy_sha256:String::new(),
            pooled_floor_sha256:String::new(),weight_sha256:String::new(),replay_exact:false,source_unchanged:true});
        means.push(descriptor);
    }
    let affinity=build_affinity(&grid,&means,mode)?;drop(means);
    let baseline_averaged_fraction=baseline.merge.averaged_fraction();
    let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    let mut replay=BandWorker::new(domain,cfg);
    let mut candidate=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut candidate_ws=FrameWorkspace::new(&sizes,4);
    for (index,frame) in frames.iter().enumerate() {
        ensure!(replay.fold(&source,index,frame.levels,noise,Some(&map),None)?,"generated replay source refused");
        let ev=&mut evidence[index];
        ensure!(ev.known4_sha256==std::array::from_fn(|c|hash32(&replay.planes[c]))
            && ev.guide_sha256==hash32(&replay.luma) && ev.variance_sha256==hash32(&replay.var)
            && ev.beta.len()==replay.beta.len() && ev.beta.iter().zip(&replay.beta).all(|(a,b)|a.to_bits()==b.to_bits())
            && ev.descriptor_sha256==descriptor_hash(&block_means4(&replay.planes,&grid)?),"actual source replay differs");
        let mut fields=core::canonical_fields(&replay.merge,&replay.fws,
            (!replay.beta.is_empty()).then_some(replay.beta.as_slice()));
        ensure!(ev.canonical_energy_sha256==hash32(&fields.energy[0])
            && ev.canonical_floor_sha256==hash32(&fields.floor[0]),"actual E/F replay differs");
        if mode!=Mode::Off {
            let (e,f)=pool_fields(&affinity,&fields.energy[0],&fields.floor[0])?;
            fields.energy[0]=e;fields.floor[0]=f;
            fields=core::fields_from_energy(&sizes,cfg,fields.energy,fields.floor);
        }
        if let Some(forced)=forced_source {fields.weights[0].fill(if index==forced {1.0}else{0.0});}
        ev.pooled_energy_sha256=hash32(&fields.energy[0]);ev.pooled_floor_sha256=hash32(&fields.floor[0]);
        ev.weight_sha256=hash32(&fields.weights[0]);
        let refs=replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();
        core::add_fields(&mut candidate,&refs,&fields,&mut candidate_ws);
        ensure!(held::non_finest_bit_exact(&replay.merge,&candidate),"candidate changed nonfinest/base/fallback/hull state");
        ensure!(ev.source_sha256==hash16(&frame.data),"replay changed original CFA");ev.replay_exact=true;
    }
    let repeated_baseline=replay.merge.finish(&mut Workspace::new(&sizes));
    ensure!(same_planes(&baseline_planes4,&repeated_baseline),"complete actual baseline changed between passes");
    let non_finest_bit_exact=held::non_finest_bit_exact(&baseline.merge,&candidate);
    ensure!(non_finest_bit_exact,"final nonfinest state differs from original baseline");
    let candidate_averaged_fraction=candidate.averaged_fraction();
    let candidate_planes4=candidate.finish(&mut Workspace::new(&sizes));
    if mode==Mode::Off {ensure!(same_planes(&baseline_planes4,&candidate_planes4),"disabled output differs");}
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,
        native_width:2*crop.width,native_height:2*crop.height,level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),
        frames:evidence,non_finest_bit_exact,baseline_averaged_fraction,candidate_averaged_fraction,affinity,forced_source})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/raw-affinity-support/independent-controls.rs"));
}
