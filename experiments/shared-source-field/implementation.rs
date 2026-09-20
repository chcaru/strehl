// Test-only fixed categorical source field and shared whole-AC reconstruction.
use super::*;
use sha2::{Digest,Sha256};
use strehl_core::pyramid::shared_source_field_diagnostic as core;
use strehl_core::align::Similarity;
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/shared-source-field/costs.rs"));

pub(crate) fn checked_core<T>(value:std::result::Result<T,String>)->Result<T>{value.map_err(anyhow::Error::msg)}
pub(crate) fn hash32(values:&[f32])->String {
    let mut h=Sha256::new();let mut bytes=vec![0u8;65536];
    for chunk in values.chunks(bytes.len()/4){for (dst,v) in bytes.chunks_exact_mut(4).zip(chunk){dst.copy_from_slice(&v.to_bits().to_le_bytes());}
        h.update(&bytes[..chunk.len()*4]);}h.finalize().iter().map(|b|format!("{b:02x}")).collect()
}
pub(crate) fn hash16(values:&[u16])->String {
    let mut h=Sha256::new();let mut bytes=vec![0u8;65536];
    for chunk in values.chunks(bytes.len()/2){for (dst,v) in bytes.chunks_exact_mut(2).zip(chunk){dst.copy_from_slice(&v.to_le_bytes());}
        h.update(&bytes[..chunk.len()*2]);}h.finalize().iter().map(|b|format!("{b:02x}")).collect()
}
fn current_route()->Result<()> {
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual GPU rounded/probed route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        && !std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),
        "held Malvar/no-local-placement route required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()
        ==strehl_core::pyramid::fine_support_candidate::Mode::Off,"other fine support candidate excluded");Ok(())
}
/// One current original source through the identical GPU known-four consumer.
/// Both callers separately enforce their own generated/full source scope.
pub(crate) fn gather_direct(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect)->Result<Vec<Vec<f32>>> {
    current_route()?;validate_pyramid_frame(frame,frame.geometry(),0)?;
    let id=strehl_raw::identity(&frame.path);
    let ca=strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?;
    ensure!(phase_packed_rgb::full_stack::full_source_supported(warp,frame.geometry(),crop,ca),"actual source pull unsupported");
    let mut current=frame.clone();let mut planes=vec![vec![0.0;crop.width*crop.height];4];
    align_cmd::warp_frame_fullres_into_planes::<false>(&mut current,warp,frame.geometry(),Resampler::CatmullRom,
        &mut WarpScratch::new(frame.geometry()),crop,&[(0,0),(1,0),(0,1),(1,1)],&mut planes,align_cmd::DirectPlaneMode::Rounded)?;
    ensure!(planes.iter().flatten().all(|v|v.is_finite()),"nonfinite actual gathered source");Ok(planes)
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum Mode {Off,SharedPotts}
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub known4_sha256:[String;4],pub energy_sha256:String,pub floor_sha256:String,
    pub guide_sha256:String,pub variance_sha256:String,pub beta:Vec<f32>,
    pub source_unchanged:bool,pub replay_known4_exact:bool,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,pub native_width:usize,pub native_height:usize,
    pub level_sizes:Vec<[usize;2]>,pub baseline_averaged_fraction:Vec<f64>,
    pub alpha:Vec<f32>,pub pixel_major_q:Vec<f32>,pub coverage:Vec<f32>,pub membership_evidence:serde_json::Value,
    pub frames:Vec<FrameEvidence>,
}
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode)->Result<Comparison> {
    compare_inner(frames,transforms,crop,noise,cfg,mode,None)
}
pub(crate) fn compare_generated_forced(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced_source:usize)->Result<Comparison> {
    compare_inner(frames,transforms,crop,noise,cfg,mode,Some(forced_source))
}
fn compare_inner(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced:Option<usize>)->Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len()<=70 && frames.len()==transforms.len(),"bounded generated source count required");
    if let Some(k)=forced{ensure!(k<frames.len() && mode==Mode::SharedPotts,"invalid explicit destroyer source");}
    current_route()?;let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
    ensure!(first.active.width<=512 && first.active.height<=512 && wb[..3].iter().all(|v|v.is_finite() && *v>0.0),
        "generated native extent/WB differs");
    for (i,f) in frames.iter().enumerate(){
        ensure!(!f.path.exists() && f.geometry()==full && f.active==first.active && f.stride==first.stride
            && f.buffer_height==first.buffer_height && f.levels==first.levels && f.camera==first.camera && f.iso==first.iso
            && f.wb_coeffs[..3]==wb[..3],"generated metadata drift or real original path");
        validate_pyramid_frame(f,full,i)?;let id=strehl_raw::identity(&f.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated scope has no CA");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),"generated pull unsupported");
    }
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);let pixels=crop.width*crop.height;
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("shared-source-field-generated",&entries),strategy:"fixed supplied generated similarities".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"fixed shared field; no optical alignment claim".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{
        fn len(&self)->usize{self.0.len()}fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);let mut worker=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);
    let mut costs=CostVolume::new(crop.width,crop.height,frames.len())?;let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate(){
        let before=hash16(&frame.data);ensure!(worker.fold(&source,index,first.levels,noise,Some(&map),None)?,"generated baseline source refused");
        let beta=(!worker.beta.is_empty()).then_some(worker.beta.as_slice());
        let fields=checked_core(core::finest_evidence(&worker.merge,&worker.fws,beta))?;
        costs.set_source(index,&fields.energy,&fields.floor)?;
        ensure!(hash16(&frame.data)==before,"generated original changed");
        evidence.push(FrameEvidence{source_sha256:before,known4_sha256:std::array::from_fn(|c|hash32(&worker.planes[c])),
            energy_sha256:hash32(&fields.energy),floor_sha256:hash32(&fields.floor),guide_sha256:hash32(&worker.luma),
            variance_sha256:hash32(&worker.var),beta:worker.beta.clone(),source_unchanged:true,replay_known4_exact:false});
    }
    let baseline_averaged_fraction=worker.merge.averaged_fraction();
    let baseline_planes4=worker.merge.finish(&mut Workspace::new(&sizes));
    let guide=baseline_planes4[1].iter().zip(&baseline_planes4[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
    let raw=costs.normalize()?;let aggregate=aggregate_costs(&raw,&guide)?;let mut membership=memberships(aggregate,&raw)?;drop(raw);
    if mode==Mode::Off{membership.alpha.fill(0.0);membership.pixel_major_q.fill(0.0);}
    if let Some(k)=forced{membership.alpha.fill(1.0);membership.pixel_major_q.fill(0.0);
        for p in 0..pixels{membership.pixel_major_q[p*frames.len()+k]=1.0;}}
    let mut replay=checked_core(core::Replay::new(&sizes,&membership.alpha))?;
    for (index,frame) in frames.iter().enumerate(){
        let planes=gather_direct(frame,transforms[index],crop)?;
        ensure!(std::array::from_fn::<_,4,_>(|c|hash32(&planes[c]))==evidence[index].known4_sha256,
            "generated replay differs from actual first-pass known4");
        let q=membership.source(index);checked_core(replay.add_source(&q,&planes))?;
        ensure!(hash16(&frame.data)==evidence[index].source_sha256,"generated replay changed original");
        evidence[index].replay_known4_exact=true;
    }
    let candidate_planes4=checked_core(replay.finish(&worker.merge,&mut Workspace::new(&sizes)))?;
    let coverage=replay.coverage().to_vec();let membership_evidence=membership.evidence();
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),baseline_averaged_fraction,
        alpha:membership.alpha,pixel_major_q:membership.pixel_major_q,coverage,membership_evidence,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/shared-source-field/independent-controls.rs"));
}
mod full_stack {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/shared-source-field/full-stack.rs"));
}
