// Generated actual-consumer counterfactual; no production mode or RAW adapter.
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{LevelSize,reduce,rb_own_guide_diagnostic as core,
    cross_scale_source_prior_diagnostic as invariant,fine_support_candidate as held,Hull,Fallback};
use super::shared_source_field::{hash16,hash32};

#[derive(Clone,Copy,Debug,Eq,PartialEq,serde::Serialize)]
pub(crate) enum Mode {Off,Prior,Neutral}
fn valid(values:&[f32],n:usize)->Result<()> {
    ensure!(values.len()==n && values.iter().all(|v|v.is_finite() && *v>=0.0),"invalid nonnegative field");Ok(())
}
fn gaussian_levels(values:&[f32],sizes:&[LevelSize])->Vec<Vec<f32>> {
    let mut levels=vec![values.to_vec()];
    for k in 1..sizes.len() {
        let mut next=vec![0.0;sizes[k].pixels()];
        reduce(&levels[k-1],sizes[k-1],&mut next,&mut vec![0.0;sizes[k].width*sizes[k-1].height]);
        levels.push(next);
    }levels
}
pub(crate) struct FinestSum {sizes:Vec<LevelSize>,source_count:usize,seen:usize,denominator:Vec<f32>}
impl FinestSum {
    /// Separately scoped observational chip/cost extent. Generated limits below
    /// remain unchanged; accumulation and normalization share the same methods.
    pub(crate) fn full_chip(sizes:&[LevelSize],source_count:usize)->Result<Self> {
        ensure!((source_count==1 || source_count==299)
            && sizes==level_sizes(3234,2150,7).as_slice(),"fixed full chip/cost geometry required");
        Ok(Self{sizes:sizes.to_vec(),source_count,seen:0,denominator:vec![0.0;sizes[0].pixels()]})
    }
    pub(crate) fn new(sizes:&[LevelSize],source_count:usize)->Result<Self> {
        ensure!(source_count>0 && source_count<=70 && sizes.len()>=2
            && sizes[0].width>0 && sizes[0].height>0 && sizes[0].width<=512 && sizes[0].height<=512
            && sizes.windows(2).all(|s|s[1]==s[0].reduced()),"bounded source count/pyramid geometry required");
        Ok(Self{sizes:sizes.to_vec(),source_count,seen:0,denominator:vec![0.0;sizes[0].pixels()]})
    }
    pub(crate) fn add(&mut self,weights0:&[f32])->Result<()> {
        ensure!(self.seen<self.source_count,"too many finest fields");valid(weights0,self.denominator.len())?;
        for (d,&w) in self.denominator.iter_mut().zip(weights0) {*d+=w;ensure!(d.is_finite(),"finest denominator overflow");}
        self.seen+=1;Ok(())
    }
    pub(crate) fn finish(self)->Result<SourcePrior> {
        ensure!(self.seen==self.source_count,"incomplete finest denominator");
        let z=self.denominator.iter().map(|&d|if d>0.0 {1.0}else{0.0}).collect::<Vec<_>>();
        Ok(SourcePrior{supported:gaussian_levels(&z,&self.sizes),sizes:self.sizes,
            source_count:self.source_count,denominator:self.denominator})
    }
}
pub(crate) struct SourcePrior {
    pub sizes:Vec<LevelSize>,pub source_count:usize,pub denominator:Vec<f32>,pub supported:Vec<Vec<f32>>,
}
#[derive(Clone,Debug,serde::Serialize)]
pub(crate) struct WeightChanges {pub changed:Vec<usize>,pub zeroed_positive:Vec<usize>,pub bypassed:Vec<usize>}
impl SourcePrior {
    pub(crate) fn source(&self,weights0:&[f32])->Result<Vec<Vec<f32>>> {
        valid(weights0,self.denominator.len())?;
        ensure!(weights0.iter().zip(&self.denominator).all(|(&w,&d)|w<=d),"source weight exceeds accumulated denominator");
        let uniform=1.0/self.source_count as f32;
        let p=weights0.iter().zip(&self.denominator).map(|(&w,&d)|if d>0.0 {w/d}else{uniform}).collect::<Vec<_>>();
        let levels=gaussian_levels(&p,&self.sizes);
        ensure!(levels.iter().flatten().all(|v|v.is_finite() && *v>=0.0),"invalid source prior");Ok(levels)
    }
    pub(crate) fn apply(&self,fields:&mut core::Fields,mode:Mode)->Result<WeightChanges> {
        let nb=self.sizes.len()-1;ensure!(fields.weights.len()==nb,"AC weight level mismatch");
        for k in 0..nb {valid(&fields.weights[k],self.sizes[k].pixels())?;}
        let mut counts=WeightChanges{changed:vec![0;nb],zeroed_positive:vec![0;nb],bypassed:vec![0;nb]};
        counts.bypassed[0]=self.sizes[0].pixels();
        if mode!=Mode::Prior {
            for k in 1..nb {counts.bypassed[k]=self.sizes[k].pixels();}return Ok(counts);
        }
        let p=self.source(&fields.weights[0])?;
        for k in 1..nb {for j in 0..self.sizes[k].pixels() {
            if self.supported[k][j]==0.0 {counts.bypassed[k]+=1;continue;}
            let old=fields.weights[k][j];let new=old*p[k][j];
            ensure!(new.is_finite() && new>=0.0,"invalid conditioned weight");
            counts.changed[k]+=usize::from(old.to_bits()!=new.to_bits());
            counts.zeroed_positive[k]+=usize::from(old>0.0 && new==0.0);
            fields.weights[k][j]=new;
        }}Ok(counts)
    }
}

#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub known4_sha256:[String;4],pub guide_sha256:String,
    pub variance_sha256:String,pub beta:Vec<f32>,pub energy_sha256:Vec<String>,pub floor_sha256:Vec<String>,
    pub canonical_weight_sha256:Vec<String>,pub candidate_weight_sha256:Vec<String>,
    pub prior_sha256:Vec<String>,pub changes:WeightChanges,pub replay_exact:bool,pub source_unchanged:bool,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,pub native_width:usize,pub native_height:usize,
    pub level_sizes:Vec<[usize;2]>,pub frames:Vec<FrameEvidence>,pub prior:SourcePrior,
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
    ensure!(mode==Mode::Prior && forced_source<frames.len(),"invalid explicit coarse-source destroyer");
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
    let mut sum=FinestSum::new(&sizes,frames.len())?;
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("cross-scale-source-prior-generated",&entries),strategy:"independent supplied geometry".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"coarse-only normalized finest-source prior".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()}fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);let mut baseline=BandWorker::new(domain,cfg);let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let source_sha256=hash16(&frame.data);
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?,"first-pass source refused");
        let fields=core::canonical_fields(&baseline.merge,&baseline.fws,(!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()));
        sum.add(&fields.weights[0])?;ensure!(hash16(&frame.data)==source_sha256,"first pass changed original CFA");
        evidence.push(FrameEvidence{source_sha256,known4_sha256:std::array::from_fn(|c|hash32(&baseline.planes[c])),
            guide_sha256:hash32(&baseline.luma),variance_sha256:hash32(&baseline.var),beta:baseline.beta.clone(),
            energy_sha256:hashes(&fields.energy),floor_sha256:hashes(&fields.floor),canonical_weight_sha256:hashes(&fields.weights),
            candidate_weight_sha256:vec![],prior_sha256:vec![],changes:WeightChanges{changed:vec![],zeroed_positive:vec![],bypassed:vec![]},
            replay_exact:false,source_unchanged:true});
    }
    let prior=sum.finish()?;let baseline_averaged_fraction=baseline.merge.averaged_fraction();
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
        ev.prior_sha256=hashes(&prior.source(&fields.weights[0])?);
        ev.changes=if let Some(forced)=forced_source {
            let mut changes=prior.apply(&mut fields,Mode::Neutral)?;
            for k in 1..fields.weights.len() {
                changes.bypassed[k]=0;let new:f32=if index==forced {1.0}else{0.0};
                for w in &mut fields.weights[k] {
                    changes.changed[k]+=usize::from(w.to_bits()!=new.to_bits());
                    changes.zeroed_positive[k]+=usize::from(*w>0.0 && new==0.0);*w=new;
                }
            }changes
        } else {prior.apply(&mut fields,mode)?};
        ev.candidate_weight_sha256=hashes(&fields.weights);
        ensure!(ev.candidate_weight_sha256[0]==ev.canonical_weight_sha256[0],"finest weight changed");
        core::add_fields(&mut candidate,&replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),&fields,&mut candidate_ws);
        ensure!(invariant::held_state_bit_exact(&replay.merge,&candidate),"candidate changed b0/base/fallback/hull state");
        ensure!(hash16(&frame.data)==ev.source_sha256,"replay changed original CFA");ev.replay_exact=true;
    }
    ensure!(same_planes(&baseline_planes4,&replay.merge.finish(&mut Workspace::new(&sizes))),"baseline differs between passes");
    let held_state_bit_exact=invariant::held_state_bit_exact(&baseline.merge,&candidate);ensure!(held_state_bit_exact,"final held state differs");
    let candidate_averaged_fraction=candidate.averaged_fraction();let candidate_planes4=candidate.finish(&mut Workspace::new(&sizes));
    if mode!=Mode::Prior {ensure!(same_planes(&baseline_planes4,&candidate_planes4),"disabled/neutral output differs");}
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    ensure!(baseline_rgb.iter().chain(&candidate_rgb).all(|v|v.is_finite()),"nonfinite developed output");
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),frames:evidence,prior,held_state_bit_exact,
        baseline_averaged_fraction,candidate_averaged_fraction,forced_source})
}
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/cross-scale-source-prior/independent-controls.rs"));
}
