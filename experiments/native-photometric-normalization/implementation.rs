// Generated native port of the existing fixed-window photometric estimator.
// No RAW IO, alternate gather, noise calibration, focus measure or merge.
use super::*;
use sha2::{Digest,Sha256};
use strehl_core::align::Similarity;
use strehl_core::pyramid::{Hull,Fallback,fine_support_candidate as held};
use super::shared_source_field::{hash16,hash32};

#[derive(Clone,Copy,Debug,PartialEq,Eq,serde::Serialize)]
pub(crate) enum Mode { Off, Unity, Estimated }

#[derive(Clone,Debug,serde::Serialize)]
pub(crate) struct FluxEvidence {
    pub mean:Option<f64>,pub count:u64,pub clipped_fraction:f64,
}
#[derive(Clone,Debug,serde::Serialize)]
pub(crate) struct Fit {
    pub status:String,pub reference:usize,pub mask_count:usize,pub mask_sha256:String,
    pub gains:Vec<f32>,pub flux:Vec<FluxEvidence>,pub refusals:Vec<Option<String>>,
    pub reason:Option<String>,
}
#[derive(Debug,serde::Serialize)]
pub(crate) struct SampleEvidence {
    pub index:usize,pub before_planes:[f32;4],pub after_planes:[f32;4],
    pub before_luma:f32,pub after_luma:f32,pub before_variance:f32,pub after_variance:f32,
}
#[derive(Debug,serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub active_sha256:String,pub known4_sha256:[String;4],
    pub guide_sha256:String,pub variance_sha256:String,pub beta:Vec<f32>,
    pub candidate_known4_sha256:[String;4],pub candidate_guide_sha256:String,
    pub candidate_variance_sha256:String,pub applied_gain:f32,
    pub replay_exact:bool,pub source_unchanged:bool,pub samples:Vec<SampleEvidence>,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,
    pub native_width:usize,pub native_height:usize,pub mode:Mode,
    pub fit:Fit,pub applied_gains:Vec<f32>,pub frames:Vec<FrameEvidence>,
}

fn same(a:&[f32],b:&[f32])->bool {
    a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())
}
fn same_planes(a:&[Vec<f32>],b:&[Vec<f32>])->bool {
    a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|same(a,b))
}
fn mask_hash(mask:&[bool])->String {
    let mut h=Sha256::new();for &v in mask {h.update([u8::from(v)]);}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}

/// Apply to existing black-subtracted radiance and its PRE-SCALE variance.
/// Exact unity is a bypass. The injected model/probe is not recomputed here.
pub(crate) fn scale_inputs(planes:&mut[Vec<f32>],luma:&mut[f32],variance:&mut[f32],gain:f32)->Result<()> {
    ensure!(planes.len()==4&&!luma.is_empty()&&variance.len()==luma.len()
        &&planes.iter().all(|p|p.len()==luma.len()),"invalid photometric input sizes");
    ensure!(gain.is_finite()&&gain>0.0&&planes.iter().flatten().chain(luma.iter()).all(|v|v.is_finite())
        &&variance.iter().all(|v|v.is_finite()&&*v>=0.0),"invalid photometric input values");
    if gain==1.0{return Ok(());}
    let gain2=gain*gain;ensure!(gain2.is_finite(),"photometric gain squared overflow");
    for p in planes.iter_mut(){photometric::apply_to_plane(p,gain);}
    photometric::apply_to_plane(luma,gain);photometric::apply_to_plane(variance,gain2);
    ensure!(planes.iter().flatten().chain(luma.iter()).chain(variance.iter()).all(|v|v.is_finite()),
        "nonfinite scaled native inputs");Ok(())
}

struct Source<'a>(&'a[Frame]);
impl PyramidFrameSource for Source<'_>{
    fn len(&self)->usize{self.0.len()}
    fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
}
fn setup(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,reference:usize,
    cfg:MergeConfig)->Result<(PyramidDomain,WarpMap)> {
    ensure!((1..=16).contains(&frames.len())&&frames.len()==transforms.len()&&reference<frames.len(),
        "bounded generated source count/reference required");
    ensure!(std::env::var_os(strehl_core::focus::WINDOW_RADIUS_ENV).is_none()
        &&strehl_core::focus::window_radius()==strehl_core::focus::WINDOW_RADIUS,
        "fixed legacy focus window required; no cached or active override");
    ensure!(cfg.select==SelectMode::SoftPower&&cfg.admission==AdmissionMode::HardFloor
        &&cfg.base==BaseBand::Mean&&cfg.fallback==Fallback::Mean&&cfg.hull==Hull::InputRange
        &&cfg.mean_coarse==0&&cfg.significance_scale==0.0,"held native merge required");
    ensure!(held::environment_mode()==held::Mode::Off
        &&align_cmd::native_gpu_integration::ca_stage::mode()?==align_cmd::native_gpu_integration::ca_stage::Mode::Current,
        "other candidate modes must be disabled");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()
        &&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probed route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        &&!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),
        "held MHC/no-local-placement required");
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
    ensure!(first.active.width<=512&&first.active.height<=512
        &&wb[..3].iter().all(|v|v.is_finite()&&*v>0.0),"small generated extent/WB required");
    for(i,f)in frames.iter().enumerate(){
        ensure!(!f.path.exists()&&f.geometry()==full&&f.active==first.active&&f.stride==first.stride
            &&f.buffer_height==first.buffer_height&&f.levels==first.levels&&f.camera==first.camera
            &&f.iso==first.iso&&f.wb_coeffs[..3]==wb[..3],"generated metadata differs");
        validate_pyramid_frame(f,full,i)?;let id=strehl_raw::identity(&f.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),
            "generated no-CA scope required");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),
            "complete fixed gather support required");
    }
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("native-photometric-normalization-generated",&entries),
        strategy:"independent supplied geometry".into(),heldout_px:None,cycle_floor_px:None,reference,
        note:"existing fixed-window photometric estimate; no geometric gain law".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    Ok((PyramidDomain::cropped(full,crop)?,map))
}

fn estimate(source:&Source<'_>,domain:PyramidDomain,map:&WarpMap,reference:usize,
    noise:&NoiseModel,cfg:MergeConfig)->Result<(Fit,BandWorker,Vec<FrameEvidence>)> {
    let first=&source.0[0];let geom=PlaneGeometry{width:domain.rect.width,height:domain.rect.height};
    let original_hashes=source.0.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>();
    let mut reference_worker=BandWorker::new(domain,cfg);
    ensure!(reference_worker.fold(source,reference,first.levels,noise,Some(map),None)?,"reference refused");
    let mut field=FocusField::new(geom);field.compute(&reference_worker.luma,noise);
    let mut scratch=vec![0.0;geom.pixels()];let mut reg=vec![0.0;geom.pixels()];
    regularise(field.values(),geom,&mut scratch,&mut reg);
    let mut raw=vec![false;geom.pixels()];let mut mask=raw.clone();
    photometric::low_detail_mask(&reg,&reference_worker.luma,PHOTOMETRIC_DETAIL_Q,PHOTOMETRIC_LUMA_Q,&mut raw);
    let mask_count=photometric::erode_mask(&raw,geom.width,PHOTOMETRIC_ERODE_PX,&mut mask);
    drop(reference_worker);drop(field);drop(scratch);drop(reg);drop(raw);
    let mut baseline=BandWorker::new(domain,cfg);let mut flux=Vec::new();let mut evidence=Vec::new();
    for(index,frame)in source.0.iter().enumerate(){
        let source_sha256=original_hashes[index].clone();let active_sha256=super::rb_own_guide::active_hash(frame);
        ensure!(hash16(&frame.data)==source_sha256,"reference preparation changed original CFA");
        ensure!(baseline.fold(source,index,first.levels,noise,Some(map),None)?,"fit source refused");
        let mut f=Flux::new();f.fold_covered(&baseline.luma,&mask,f32::from(CONTAINER_MAX_DN)-first.levels.black);
        flux.push(f);ensure!(hash16(&frame.data)==source_sha256,"fit modified original CFA");
        evidence.push(FrameEvidence{source_sha256,active_sha256,known4_sha256:std::array::from_fn(|c|hash32(&baseline.planes[c])),
            guide_sha256:hash32(&baseline.luma),variance_sha256:hash32(&baseline.var),beta:baseline.beta.clone(),
            candidate_known4_sha256:std::array::from_fn(|_|String::new()),candidate_guide_sha256:String::new(),
            candidate_variance_sha256:String::new(),applied_gain:1.0,replay_exact:false,source_unchanged:true,samples:vec![]});
    }
    let fitted=if mask_count<PHOTOMETRIC_MIN_PX {Err(format!("eroded region {mask_count} below existing minimum {PHOTOMETRIC_MIN_PX}"))}
        else{PhotometricMap::from_flux(&flux,reference).map_err(|e|e.to_string())};
    let (status,gains,refusals,reason)=match fitted{
        Ok(map)=>(if map.refused_count()==0{"AVAILABLE"}else{"PARTIAL_REFUSAL"}.to_string(),map.gains().to_vec(),
            (0..map.len()).map(|i|map.refusal(i).map(str::to_string)).collect(),None),
        Err(reason)=>("UNAVAILABLE".to_string(),PhotometricMap::unity(source.len(),reference)?.gains().to_vec(),
            vec![Some(reason.clone());source.len()],Some(reason)),
    };
    let fit=Fit{status,reference,mask_count,mask_sha256:mask_hash(&mask),gains,
        flux:flux.iter().map(|f|FluxEvidence{mean:f.mean(),count:f.count(),clipped_fraction:f.clipped_fraction()}).collect(),
        refusals,reason};
    Ok((fit,baseline,evidence))
}

pub(crate) fn estimate_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    reference:usize,noise:&NoiseModel,cfg:MergeConfig)->Result<Fit> {
    let(domain,map)=setup(frames,transforms,crop,reference,cfg)?;
    Ok(estimate(&Source(frames),domain,&map,reference,noise,cfg)?.0)
}

pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    reference:usize,noise:&NoiseModel,cfg:MergeConfig,mode:Mode)->Result<Comparison> {
    let(domain,map)=setup(frames,transforms,crop,reference,cfg)?;let source=Source(frames);
    let (fit,baseline,mut evidence)=estimate(&source,domain,&map,reference,noise,cfg)?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    drop(baseline);
    let applied_gains=if mode==Mode::Estimated{fit.gains.clone()}
        else{PhotometricMap::unity(frames.len(),reference)?.gains().to_vec()};
    let mut replay=BandWorker::new(domain,cfg);let mut candidate=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut ws=FrameWorkspace::new(&sizes,4);
    for(index,frame)in frames.iter().enumerate(){
        ensure!(replay.fold(&source,index,frame.levels,noise,Some(&map),None)?,"replay source refused");
        let ev=&mut evidence[index];
        ensure!(ev.known4_sha256==std::array::from_fn(|c|hash32(&replay.planes[c]))
            &&ev.guide_sha256==hash32(&replay.luma)&&ev.variance_sha256==hash32(&replay.var)
            &&same(&ev.beta,&replay.beta),"actual native source replay differs");
        let sites=[0,replay.luma.len()/3,replay.luma.len()/2,replay.luma.len()-1];
        ev.samples=sites.iter().map(|&j|SampleEvidence{index:j,before_planes:std::array::from_fn(|c|replay.planes[c][j]),
            after_planes:[0.0;4],before_luma:replay.luma[j],after_luma:0.0,
            before_variance:replay.var[j],after_variance:0.0}).collect();
        let gain=applied_gains[index];
        scale_inputs(&mut replay.planes,&mut replay.luma,&mut replay.var,gain)?;
        for sample in &mut ev.samples {let j=sample.index;
            sample.after_planes=std::array::from_fn(|c|replay.planes[c][j]);sample.after_luma=replay.luma[j];
            sample.after_variance=replay.var[j];
        }
        ev.candidate_known4_sha256=std::array::from_fn(|c|hash32(&replay.planes[c]));
        ev.candidate_guide_sha256=hash32(&replay.luma);ev.candidate_variance_sha256=hash32(&replay.var);
        ev.applied_gain=gain;ev.replay_exact=true;
        let refs=replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();
        ws.next_frame();candidate.add_frame_with_gain(&refs,&replay.luma,&replay.var,
            (!replay.beta.is_empty()).then_some(replay.beta.as_slice()),&mut ws);
        ensure!(hash16(&frame.data)==ev.source_sha256,"candidate modified original CFA");
    }
    ensure!(same_planes(&baseline_planes4,&replay.merge.finish(&mut Workspace::new(&sizes))),
        "unmodified merge changed across fitting/replay");
    let candidate_planes4=candidate.finish(&mut Workspace::new(&sizes));
    if applied_gains.iter().all(|&g|g==1.0){
        ensure!(same_planes(&baseline_planes4,&candidate_planes4),"unity final CFA identity failed");
    }
    let first=&frames[0];
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,first.wb_coeffs)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,first.wb_coeffs)?;
    ensure!(baseline_rgb.iter().chain(&candidate_rgb).all(|v|v.is_finite()),"nonfinite final MHC RGB");
    if applied_gains.iter().all(|&g|g==1.0){ensure!(same(&baseline_rgb,&candidate_rgb),"unity final MHC identity failed");}
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,
        native_height:2*crop.height,mode,fit,applied_gains,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/native-photometric-normalization/independent-controls.rs"));
}
