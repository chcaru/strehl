// Test-only bounded generated adapter to the actual BandWorker and gate probe.
use super::*;
use sha2::{Digest,Sha256};
use strehl_core::align::Similarity;
use crate::align_cmd::native_gpu_integration::ca_stage;
pub(crate) use ca_stage::Mode;

fn hash16(v:&[u16])->String{let mut h=Sha256::new();for x in v{h.update(x.to_le_bytes());}h.finalize().iter().map(|b|format!("{b:02x}")).collect()}
fn hash32(v:&[f32])->String{let mut h=Sha256::new();for x in v{h.update(x.to_bits().to_le_bytes());}h.finalize().iter().map(|b|format!("{b:02x}")).collect()}
fn route()->Result<()>{
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?,"CA controls require actual rounded GPU/probe route");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        && !std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"CA controls require unmodified Malvar consumer");
    Ok(())
}
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub known4_sha256:[String;4],pub guide_sha256:String,
    pub variance_sha256:String,pub beta:Vec<f32>,pub source_unchanged:bool,
}
pub(crate) struct Arm {pub planes4:Vec<Vec<f32>>,pub rgb:Vec<f32>,pub frames:Vec<FrameEvidence>,pub averaged_fraction:Vec<f64>}
pub(crate) struct Comparison {pub current:Arm,pub before:Arm,pub staged_after:Arm,
    pub native_width:usize,pub native_height:usize,pub level_sizes:Vec<[usize;2]>}

pub(crate) fn gather_single(frame:&Frame,t:Similarity,crop:align_cmd::CropRect,
    ca_pulls:[Similarity;3],mode:Mode)->Result<Vec<Vec<f32>>>{
    route()?;ensure!(!frame.path.exists() && frame.active.width<=512 && frame.active.height<=512,"generated scope only");
    validate_pyramid_frame(frame,frame.geometry(),0)?;
    ca_stage::with_explicit(mode,ca_pulls,||{
        let mut cloned=frame.clone();let mut planes=vec![vec![0.;crop.width*crop.height];4];
        align_cmd::warp_frame_fullres_into_planes::<false>(&mut cloned,t,frame.geometry(),Resampler::CatmullRom,
            &mut WarpScratch::new(frame.geometry()),crop,&[(0,0),(1,0),(0,1),(1,1)],&mut planes,align_cmd::DirectPlaneMode::Rounded)?;
        ensure!(planes.iter().flatten().all(|v|v.is_finite()),"nonfinite gathered CFA");Ok(planes)
    })
}
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,ca_pulls:[Similarity;3])->Result<Comparison>{
    route()?;ensure!(!frames.is_empty() && frames.len()<=16 && frames.len()==transforms.len(),"bounded generated frame count required");
    let first=&frames[0];let full=first.geometry();
    ensure!(first.active.width<=512 && first.active.height<=512,"bounded generated source extent required");
    for(i,f)in frames.iter().enumerate(){
        ensure!(!f.path.exists() && f.geometry()==full && f.active==first.active && f.stride==first.stride
            && f.buffer_height==first.buffer_height && f.levels==first.levels && f.camera==first.camera && f.iso==first.iso
            && f.wb_coeffs[..3]==first.wb_coeffs[..3],"generated metadata drift or real original");
        validate_pyramid_frame(f,full,i)?;
    }
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("ca-before-mhc-generated",&entries),strategy:"explicit supplied common/colour pulls".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"fixed CA ordering; no calibration claim".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{
        fn len(&self)->usize{self.0.len()}fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}}
    let arm=|mode|->Result<Arm>{ca_stage::with_explicit(mode,ca_pulls,||{
        let source=Source(frames);let mut worker=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);let mut evidence=Vec::new();
        for(index,frame)in frames.iter().enumerate(){let before=hash16(&frame.data);
            ensure!(worker.fold(&source,index,first.levels,noise,Some(&map),None)?,"source refused");
            ensure!(hash16(&frame.data)==before,"original u16 source mutated");
            evidence.push(FrameEvidence{source_sha256:before,known4_sha256:std::array::from_fn(|c|hash32(&worker.planes[c])),
                guide_sha256:hash32(&worker.luma),variance_sha256:hash32(&worker.var),beta:worker.beta.clone(),source_unchanged:true});
        }
        let averaged_fraction=worker.merge.averaged_fraction();let planes4=worker.merge.finish(&mut Workspace::new(&sizes));
        let rgb=phase_packed_rgb::camera_rgb(&planes4,crop.width,crop.height,first.levels,first.wb_coeffs)?;
        ensure!(rgb.iter().all(|v|v.is_finite()),"nonfinite developed generated RGB");
        Ok(Arm{planes4,rgb,frames:evidence,averaged_fraction})
    })};
    Ok(Comparison{current:arm(Mode::Current)?,before:arm(Mode::Before)?,staged_after:arm(Mode::StagedAfter)?,
        native_width:2*crop.width,native_height:2*crop.height,level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect()})
}
mod independent_controls {include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/ca-before-mhc/independent-controls.rs"));}
