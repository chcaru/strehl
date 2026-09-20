// Bounded generated own-colour guidance. Original production merge remains canonical.
use super::*;
use sha2::{Digest,Sha256};
use strehl_core::align::Similarity;
use strehl_core::pyramid::{LevelSize,correction_variance_diagnostic as kernels,
    rb_own_guide_diagnostic as core};
use super::boundary_cfa_wavelet as source_probe;
use super::shared_source_field::{hash16,hash32};
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-own-guide/probe.rs"));

#[derive(serde::Serialize)]
pub(crate) struct FieldEvidence {
    pub energy_sha256:Vec<String>,pub floor_sha256:Vec<String>,pub weight_sha256:Vec<String>,
    pub positive_weight_counts:Vec<usize>,
}
#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub active_sha256:String,pub probe_seeds:[usize;16],
    pub known4_sha256:[String;4],pub baseline_guide_sha256:String,pub baseline_variance_sha256:String,
    pub baseline_beta:Vec<f32>,pub canonical_fields:FieldEvidence,pub guide_fields:[FieldEvidence;3],
    pub pair_band_means3:Vec<Vec<[f64;3]>>,pub source_unchanged:bool,
}
pub(crate) struct Arm {
    pub planes4:Vec<Vec<f32>>,pub rgb:Vec<f32>,
    pub averaged_fraction_rb:[Vec<f64>;2],pub terminal_base_exact:bool,
}
pub(crate) struct Comparison {
    pub canonical:Arm,pub matched_green:Arm,pub own:Arm,pub identity:Arm,pub swapped:Arm,
    pub native_width:usize,pub native_height:usize,pub level_sizes:Vec<[usize;2]>,
    pub baseline_averaged_fraction:Vec<f64>,pub frames:Vec<FrameEvidence>,
}
fn field_evidence(fields:&core::Fields,diagnostics:bool)->FieldEvidence {
    if !diagnostics {return FieldEvidence {energy_sha256:vec![],floor_sha256:vec![],
        weight_sha256:vec![],positive_weight_counts:vec![]};}
    FieldEvidence {energy_sha256:fields.energy.iter().map(|v|hash32(v)).collect(),
        floor_sha256:fields.floor.iter().map(|v|hash32(v)).collect(),
        weight_sha256:fields.weights.iter().map(|v|hash32(v)).collect(),
        positive_weight_counts:fields.weights.iter().map(|v|v.iter().filter(|&&w|w>0.0).count()).collect()}
}
fn bits_equal(a:&[f32],b:&[f32])->bool {
    a.len()==b.len() && a.iter().zip(b).all(|(x,y)|x.to_bits()==y.to_bits())
}
struct ColourArm {merges:[BandMerge;2],work:[FrameWorkspace;2]}
impl ColourArm {
    fn new(sizes:&[LevelSize],cfg:MergeConfig)->Self {
        Self {merges:std::array::from_fn(|_|BandMerge::new(sizes[0].width,sizes[0].height,1,cfg)),
            work:std::array::from_fn(|_|FrameWorkspace::new(sizes,1))}
    }
    fn add(&mut self,planes:&[Vec<f32>],fields:[&core::Fields;2]) {
        for (i,c) in [0,3].into_iter().enumerate() {
            core::add_fields(&mut self.merges[i],&[&planes[c]],fields[i],&mut self.work[i]);
        }
    }
    fn finish(&self,baseline:&[Vec<f32>],base:&[Vec<f32>],sizes:&[LevelSize],
        levels:Levels,wb:[f32;4])->Result<Arm> {
        let mut planes4=baseline.to_vec();let mut terminal_base_exact=true;
        for (i,c) in [0,3].into_iter().enumerate() {
            let terminal=core::terminal_means(&self.merges[i]);
            terminal_base_exact &= bits_equal(&terminal[0],&base[c]);
            planes4[c]=self.merges[i].finish(&mut Workspace::new(sizes)).remove(0);
        }
        ensure!(planes4.iter().flatten().all(|v|v.is_finite()),"nonfinite own-guide reconstruction");
        let rgb=phase_packed_rgb::camera_rgb(&planes4,sizes[0].width,sizes[0].height,levels,wb)?;
        Ok(Arm {planes4,rgb,averaged_fraction_rb:std::array::from_fn(|i|self.merges[i].averaged_fraction()),terminal_base_exact})
    }
}
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig)->Result<Comparison> {
    compare_generated_with_diagnostics(frames,transforms,crop,noise,cfg,true)
}
pub(crate) fn compare_generated_with_diagnostics(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,diagnostics:bool)->Result<Comparison> {
    ensure!(frames.len()>=2 && frames.len()<=16 && frames.len()==transforms.len(),"bounded generated2..16 sources required");
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
    ensure!(first.active.width<=512 && first.active.height<=512 && wb[..3].iter().all(|v|v.is_finite() && *v>0.0),
        "generated native extent/WB differs");
    ensure!(gatefloor::enabled() && strehl_core::pyramid::fine_support_candidate::environment_mode()
        ==strehl_core::pyramid::fine_support_candidate::Mode::Off,"held baseline probe / no competing candidate required");
    for (i,f) in frames.iter().enumerate() {
        ensure!(!f.path.exists() && f.geometry()==full && f.active==first.active && f.stride==first.stride
            && f.buffer_height==first.buffer_height && f.levels==first.levels && f.camera==first.camera && f.iso==first.iso
            && f.wb_coeffs[..3]==wb[..3],"generated metadata drift or real original path");
        validate_pyramid_frame(f,full,i)?;let id=strehl_raw::identity(&f.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated scope has no CA");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),"generated pull unsupported");
    }
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance {
        stack:StackIdentity::from_entries("rb-own-guide-generated",&entries),strategy:"fixed supplied generated similarities".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"own R/B guide test; no inferred axial offset".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()}fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);let mut worker=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);
    let mut identity_merge=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut identity_ws=FrameWorkspace::new(&sizes,4);
    let mut matched=ColourArm::new(&sizes,cfg);let mut own=ColourArm::new(&sizes,cfg);
    let mut swapped=ColourArm::new(&sizes,cfg);let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let before=hash16(&frame.data);
        ensure!(worker.fold(&source,index,first.levels,noise,Some(&map),None)?,"generated baseline source refused");
        let beta=(!worker.beta.is_empty()).then_some(worker.beta.as_slice());
        let canonical_fields=core::canonical_fields(&worker.merge,&worker.fws,beta);
        core::add_fields(&mut identity_merge,&worker.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),
            &canonical_fields,&mut identity_ws);
        let probes=probe_noise(frame,transforms[index],crop,noise,&sizes,diagnostics)?;
        let signal=guide_laplacians(&worker.planes,&sizes)?;
        let guide_fields:[core::Fields;3]=std::array::from_fn(|c| {
            let energy=signal[c].iter().enumerate().map(|(k,v)|kernels::energy(v,sizes[k])).collect();
            let floor=probes.energy3[c].iter().map(|v|v.iter().map(|x|cfg.gate*x).collect()).collect();
            core::fields_from_energy(&sizes,cfg,energy,floor)
        });
        matched.add(&worker.planes,[&guide_fields[1],&guide_fields[1]]);
        own.add(&worker.planes,[&guide_fields[0],&guide_fields[2]]);
        swapped.add(&worker.planes,[&guide_fields[2],&guide_fields[0]]);
        ensure!(hash16(&frame.data)==before,"generated original changed");
        evidence.push(FrameEvidence {source_sha256:before,active_sha256:probes.active_sha256,probe_seeds:probes.seeds,
            known4_sha256:std::array::from_fn(|c|hash32(&worker.planes[c])),
            baseline_guide_sha256:hash32(&worker.luma),baseline_variance_sha256:hash32(&worker.var),
            baseline_beta:worker.beta.clone(),canonical_fields:field_evidence(&canonical_fields,diagnostics),
            guide_fields:std::array::from_fn(|c|field_evidence(&guide_fields[c],diagnostics)),
            pair_band_means3:probes.pair_band_means3,source_unchanged:true});
    }
    let baseline_averaged_fraction=worker.merge.averaged_fraction();
    let baseline=worker.merge.finish(&mut Workspace::new(&sizes));
    ensure!(baseline.iter().flatten().all(|v|v.is_finite()),"nonfinite canonical output");
    let base=core::terminal_means(&worker.merge);
    let matched_green=matched.finish(&baseline,&base,&sizes,first.levels,wb)?;
    let own=own.finish(&baseline,&base,&sizes,first.levels,wb)?;
    let swapped=swapped.finish(&baseline,&base,&sizes,first.levels,wb)?;
    let identity_planes=identity_merge.finish(&mut Workspace::new(&sizes));
    let identity_base=core::terminal_means(&identity_merge);
    let identity=Arm {rgb:phase_packed_rgb::camera_rgb(&identity_planes,crop.width,crop.height,first.levels,wb)?,
        planes4:identity_planes,averaged_fraction_rb:std::array::from_fn(|_|identity_merge.averaged_fraction()),
        terminal_base_exact:identity_base.iter().zip(&base).all(|(a,b)|bits_equal(a,b))};
    let canonical=Arm {rgb:phase_packed_rgb::camera_rgb(&baseline,crop.width,crop.height,first.levels,wb)?,planes4:baseline,
        averaged_fraction_rb:std::array::from_fn(|_|baseline_averaged_fraction.clone()),terminal_base_exact:true};
    Ok(Comparison {canonical,matched_green,own,identity,swapped,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),baseline_averaged_fraction,frames:evidence})
}
mod independent_noise_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-own-guide/independent-noise-controls.rs"));
}
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-own-guide/independent-controls.rs"));
}
