// Small generated adapter. The full photograph uses the existing actual CLI
// consumer and environment mode; there is no second whole-RAW renderer here.
use super::*;
use sha2::{Digest,Sha256};
use strehl_core::align::Similarity;
pub(crate) use strehl_core::pyramid::fine_support_candidate::Mode;
use strehl_core::pyramid::fine_support_candidate as candidate;
use phase_packed_rgb::{camera_rgb,FrameEvidence};

pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,
    pub native_width:usize,pub native_height:usize,pub level_sizes:Vec<[usize;2]>,
    pub frames:Vec<FrameEvidence>,pub non_finest_bit_exact:bool,
    pub baseline_averaged_fraction:Vec<f64>,pub candidate_averaged_fraction:Vec<f64>,
}
fn hash16(values:&[u16])->String {
    let mut h=Sha256::new();for v in values{h.update(v.to_le_bytes());}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}
fn hash32(values:&[f32])->String {
    let mut h=Sha256::new();for v in values{h.update(v.to_bits().to_le_bytes());}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}

/// Both arms share actual original-CFA gather, guide, injected variance and
/// measured probe. Only the candidate's explicit finest-weight mode differs.
/// This bounded gate uses one arithmetic chunk in each arm.
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],
    crop:align_cmd::CropRect,noise:&NoiseModel,cfg:MergeConfig,mode:Mode)->Result<Comparison> {
    ensure!(candidate::environment_mode()==Mode::Off,"generated paired baseline requires environment mode off");
    ensure!(!frames.is_empty() && frames.len()<=32 && frames.len()==transforms.len(),"bounded generated frame count");
    let full=frames[0].geometry();
    ensure!(full.width<=512 && full.height<=512 && frames.iter().all(|f|
        f.geometry()==full && f.levels==frames[0].levels && !f.path.exists()),"generated bounded frames required");
    ensure!(frames.iter().all(|f|f.wb_coeffs[..3]==frames[0].wb_coeffs[..3]),"fixed generated WB required");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded,"actual rounded/probe route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"local placement excluded");
    let domain=PyramidDomain::cropped(full,crop)?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("fine-support-generated",&entries),strategy:"independent supplied geometry".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"bounded generated candidate; no fitted geometry".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);
    impl PyramidFrameSource for Source<'_>{
        fn len(&self)->usize{self.0.len()}
        fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);
    let mut baseline=BandWorker::new(domain,cfg);
    let mut changed=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut changed_ws=FrameWorkspace::new(&sizes,4);
    let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let source_hash=hash16(&frame.data);
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?,"generated frame refused");
        let refs=baseline.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();
        changed_ws.next_frame();
        changed.add_frame_with_fine_support(&refs,&baseline.luma,&baseline.var,
            (!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()),&mut changed_ws,mode);
        ensure!(candidate::non_finest_bit_exact(&baseline.merge,&changed),"candidate changed a coarse/base/fallback/input-hull accumulator");
        ensure!(source_hash==hash16(&frame.data),"original generated CFA changed");
        evidence.push(FrameEvidence{source_sha256:source_hash,guide_sha256:hash32(&baseline.luma),
            variance_sha256:hash32(&baseline.var),beta:baseline.beta.clone()});
    }
    let non_finest_bit_exact=candidate::non_finest_bit_exact(&baseline.merge,&changed);
    let baseline_averaged_fraction=baseline.merge.averaged_fraction();
    let candidate_averaged_fraction=changed.averaged_fraction();
    let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    let candidate_planes4=changed.finish(&mut Workspace::new(&sizes));
    if mode==Mode::Off {
        ensure!(baseline_planes4.iter().zip(&candidate_planes4).all(|(a,b)|a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())),"explicit disabled path changed pixels");
    }
    let baseline_rgb=camera_rgb(&baseline_planes4,crop.width,crop.height,frames[0].levels,frames[0].wb_coeffs)?;
    let candidate_rgb=camera_rgb(&candidate_planes4,crop.width,crop.height,frames[0].levels,frames[0].wb_coeffs)?;
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,
        native_height:2*crop.height,level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),frames:evidence,
        non_finest_bit_exact,baseline_averaged_fraction,candidate_averaged_fraction})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/fine-support-guidance/candidate-independent-controls.rs"));
}
