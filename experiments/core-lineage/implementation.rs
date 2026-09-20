// Generated whole-AC lineage consumer only; root owns execution.
use super::*;
use strehl_core::{CfaPlane,align::Similarity,pyramid::shared_source_field_diagnostic as core};
pub(crate) use super::shared_source_field::{Comparison,FrameEvidence};
use super::shared_source_field::{checked_core,gather_direct,hash16,hash32};
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/core-lineage/lineage.rs"));

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum Mode {Off,CoreLineage}
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
    ensure!(frames.len()>=3 && frames.len()<=16 && frames.len()==transforms.len(),"bounded generated3..16 sources required");
    if let Some(k)=forced{ensure!(k<frames.len() && mode==Mode::CoreLineage,"invalid explicit destroyer source");}
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
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
        stack:StackIdentity::from_entries("core-lineage-generated",&entries),strategy:"fixed supplied generated similarities".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"bounded original-source topology; no ownership admission".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{
        fn len(&self)->usize{self.0.len()}fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);let mut worker=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);
    let mut tracker=Tracker::new(crop.width,crop.height,frames.len());let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate(){
        let before=hash16(&frame.data);ensure!(worker.fold(&source,index,first.levels,noise,Some(&map),None)?,"generated baseline source refused");
        let beta=(!worker.beta.is_empty()).then_some(worker.beta.as_slice());
        let fields=checked_core(core::finest_evidence(&worker.merge,&worker.fws,beta))?;
        let exponent=cfg.exponent_at(0,sizes.len()-1);
        let weights=fields.energy.iter().zip(&fields.floor).map(|(&e,&f)|
            strehl_core::pyramid::correction_variance_diagnostic::soft_weight((e-f).max(0.0),f,exponent)).collect::<Vec<_>>();
        tracker.push(index,analyse_source(frame,transforms[index],crop,noise)?,&weights)?;
        ensure!(hash16(&frame.data)==before,"generated original changed");
        evidence.push(FrameEvidence{source_sha256:before,known4_sha256:std::array::from_fn(|c|hash32(&worker.planes[c])),
            energy_sha256:hash32(&fields.energy),floor_sha256:hash32(&fields.floor),guide_sha256:hash32(&worker.luma),
            variance_sha256:hash32(&worker.var),beta:worker.beta.clone(),source_unchanged:true,replay_known4_exact:false});
    }
    let baseline_averaged_fraction=worker.merge.averaged_fraction();
    let baseline_planes4=worker.merge.finish(&mut Workspace::new(&sizes));
    let mut membership=tracker.finish()?;
    if mode==Mode::Off{membership.alpha.fill(0.0);membership.pixel_major_q.fill(0.0);}
    if let Some(k)=forced{membership.alpha.fill(1.0);membership.pixel_major_q.fill(0.0);
        for p in 0..pixels{membership.pixel_major_q[p*frames.len()+k]=1.0;}}
    let mut replay=checked_core(core::Replay::new(&sizes,&membership.alpha))?;
    for (index,frame) in frames.iter().enumerate(){
        let planes=gather_direct(frame,transforms[index],crop)?;
        ensure!(std::array::from_fn::<_,4,_>(|c|hash32(&planes[c]))==evidence[index].known4_sha256,
            "generated replay differs from actual first-pass known4");
        let q=(0..pixels).map(|p|membership.pixel_major_q[p*frames.len()+index]).collect::<Vec<_>>();
        checked_core(replay.add_source(&q,&planes))?;
        ensure!(hash16(&frame.data)==evidence[index].source_sha256,"generated replay changed original");evidence[index].replay_known4_exact=true;
    }
    let candidate_planes4=checked_core(replay.finish(&worker.merge,&mut Workspace::new(&sizes)))?;
    let coverage=replay.coverage().to_vec();
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),baseline_averaged_fraction,
        alpha:membership.alpha,pixel_major_q:membership.pixel_major_q,coverage,membership_evidence:membership.evidence,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/core-lineage/independent-controls.rs"));
}
