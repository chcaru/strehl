// Explicit legacy election/admission on the current gathered f32 CFA tuple.
use super::*;
use strehl_core::align::Similarity;
use strehl_core::focus::FocusField as LegacyFocus;
use strehl_core::merge::{FocusStats as LegacyStats,Gate as LegacyGate};
use super::shared_source_field::{hash16,hash32};

#[derive(Clone,Copy,Debug,Eq,PartialEq,serde::Serialize)]
pub(crate) enum Mode {Coherent,MeanAll}
pub(crate) struct FocusWorkspace {field:LegacyFocus,scratch:Vec<f32>,reg:Vec<f32>}
impl FocusWorkspace {
    pub(crate) fn new(geom:PlaneGeometry)->Self {
        assert_eq!(strehl_core::focus::WINDOW_RADIUS,13);
        assert_eq!(strehl_core::merge::REGULARISER_RADIUS,8);
        assert_eq!(strehl_core::merge::DEFAULT_GATE.to_bits(),4.0f32.to_bits());
        Self{field:LegacyFocus::new(geom),scratch:vec![0.;geom.pixels()],reg:vec![0.;geom.pixels()]}
    }
    pub(crate) fn compute(&mut self,luma:&[f32],noise:&NoiseModel)->Result<&[f32]> {
        ensure!(luma.len()==self.reg.len()&&luma.iter().all(|v|v.is_finite()),"invalid gathered guide");
        self.field.compute_at_radius(luma,noise,13);
        strehl_core::merge::regularise(self.field.values(),self.field.geometry(),&mut self.scratch,&mut self.reg);
        ensure!(self.reg.iter().all(|v|v.is_finite()),"nonfinite legacy response");Ok(&self.reg)
    }
}
pub(crate) struct CoherentAccumulator {
    geom:PlaneGeometry,expected:usize,best:Vec<f32>,winners:Vec<u16>,gate:LegacyGate,mode:Mode,
    forced:Option<usize>,sums:Vec<Vec<f32>>,counts:Vec<u16>,seen:Vec<usize>,max_index:usize,
}
impl CoherentAccumulator {
    pub(crate) fn new(stats:&LegacyStats,mode:Mode)->Result<Self>{Self::construct(stats,mode,None)}
    pub(crate) fn new_forced(stats:&LegacyStats,source:usize)->Result<Self>{Self::construct(stats,Mode::Coherent,Some(source))}
    fn construct(stats:&LegacyStats,mode:Mode,forced:Option<usize>)->Result<Self>{
        let geom=stats.geometry();let expected=stats.frames_folded()as usize;
        ensure!(expected>0&&expected<=299&&geom.width>0&&geom.height>0&&geom.pixels()<=3234*2150
            &&stats.best_focus().iter().all(|v|v.is_finite()),"invalid completed focus statistics");
        ensure!(forced.is_none_or(|i|i<=stats.max_index()as usize),"wrong-source index outside pass1 extent");
        Ok(Self{geom,expected,best:stats.best_focus().to_vec(),winners:stats.best_index().to_vec(),
            gate:LegacyGate::new(4.0),mode,forced,sums:vec![vec![0.;geom.pixels()];4],counts:vec![0;geom.pixels()],
            seen:Vec::new(),max_index:stats.max_index()as usize})
    }
    pub(crate) fn add(&mut self,index:usize,planes:&[Vec<f32>],regularised:&[f32])->Result<usize>{
        ensure!(self.seen.len()<self.expected&&index<=self.max_index&&!self.seen.contains(&index),"duplicate/unknown replay source");
        let n=self.geom.pixels();ensure!(planes.len()==4&&planes.iter().all(|p|p.len()==n&&p.iter().all(|v|v.is_finite()))
            &&regularised.len()==n&&regularised.iter().all(|v|v.is_finite()),"invalid native tuple/response");
        let mut accepted=0;
        for j in 0..n {
            let admit=match self.forced{Some(i)=>i==index,None=>self.mode==Mode::MeanAll
                ||self.winners[j]as usize==index||self.gate.admits(regularised[j],self.best[j])};
            if admit {
                for c in 0..4 {if self.counts[j]==0{self.sums[c][j]=planes[c][j];}else{self.sums[c][j]+=planes[c][j];}
                    ensure!(self.sums[c][j].is_finite(),"native mean overflow");}
                self.counts[j]+=1;accepted+=1;
            }
        }self.seen.push(index);Ok(accepted)
    }
    pub(crate) fn counts(&self)->&[u16]{&self.counts}
    pub(crate) fn finish(&self)->Result<Vec<Vec<f32>>>{
        ensure!(self.seen.len()==self.expected&&self.counts.iter().all(|&n|n>0),"incomplete/undecided coherent estimate");
        let out=self.sums.iter().map(|p|p.iter().zip(&self.counts).map(|(&s,&n)|s/n as f32).collect::<Vec<_>>()).collect::<Vec<_>>();
        ensure!(out.iter().flatten().all(|v|v.is_finite()),"nonfinite coherent estimate");Ok(out)
    }
}
#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub known4_sha256:Vec<String>,pub guide_sha256:String,pub variance_sha256:String,
    pub beta:Vec<f32>,pub regularised_focus_sha256:String,pub accepted_pixels:usize,pub replay_exact:bool,pub source_unchanged:bool,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,
    pub native_width:usize,pub native_height:usize,pub level_sizes:Vec<[usize;2]>,pub baseline_averaged_fraction:Vec<f64>,
    pub counts:Vec<u16>,pub best_index:Vec<u16>,pub best_focus:Vec<f32>,pub frames:Vec<FrameEvidence>,
    pub exact_coherent_replay:bool,pub one_source_mean_exact:Option<bool>,pub forced_source:Option<usize>,
}
fn same(a:&[f32],b:&[f32])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn hashes(v:&[Vec<f32>])->Vec<String>{v.iter().map(|p|hash32(p)).collect()}
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode)->Result<Comparison>{compare_inner(frames,transforms,crop,noise,cfg,mode,None)}
pub(crate) fn compare_generated_forced(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced_source:usize)->Result<Comparison>{
    ensure!(mode==Mode::Coherent&&forced_source<frames.len(),"invalid explicit wrong donor");
    compare_inner(frames,transforms,crop,noise,cfg,mode,Some(forced_source))
}
fn compare_inner(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,mode:Mode,forced_source:Option<usize>)->Result<Comparison>{
    ensure!(!frames.is_empty()&&frames.len()<=70&&frames.len()==transforms.len(),"bounded generated source count");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()&&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probe route required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off
        &&align_cmd::native_gpu_integration::ca_stage::mode()?==align_cmd::native_gpu_integration::ca_stage::Mode::Current,"other candidates must be off");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        &&!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"held Malvar/no local placement required");
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
    ensure!(first.active.width<=512&&first.active.height<=512&&wb[..3].iter().all(|v|v.is_finite()&&*v>0.),"small generated extent/WB required");
    for(i,f)in frames.iter().enumerate(){ensure!(!f.path.exists()&&f.geometry()==full&&f.active==first.active&&f.stride==first.stride
        &&f.buffer_height==first.buffer_height&&f.levels==first.levels&&f.camera==first.camera&&f.iso==first.iso&&f.wb_coeffs[..3]==wb[..3],"generated metadata drift");
        validate_pyramid_frame(f,full,i)?;let id=strehl_raw::identity(&f.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated no-CA scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),"unsupported generated pull");}
    let domain=PyramidDomain::cropped(full,crop)?;let geom=PlaneGeometry{width:crop.width,height:crop.height};let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{stack:StackIdentity::from_entries("native-coherent-estimator-generated",&entries),
        strategy:"independent supplied geometry".into(),heldout_px:None,cycle_floor_px:None,reference:0,note:"fixed legacy gate on current f32 tuple".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{fn len(&self)->usize{self.0.len()}
        fn decode(&self,i:usize)->Result<Frame>{Ok(self.0[i].clone())}}
    let source=Source(frames);let mut baseline=BandWorker::new(domain,cfg);let mut work=FocusWorkspace::new(geom);let mut stats=LegacyStats::new(geom);let mut evidence=Vec::new();
    for(i,f)in frames.iter().enumerate(){let original=hash16(&f.data);ensure!(baseline.fold(&source,i,f.levels,noise,Some(&map),None)?,"first-pass source refused");
        let reg=work.compute(&baseline.luma,noise)?;stats.fold(i as u16,reg)?;ensure!(hash16(&f.data)==original,"original CFA changed");
        evidence.push(FrameEvidence{source_sha256:original,known4_sha256:hashes(&baseline.planes),guide_sha256:hash32(&baseline.luma),
            variance_sha256:hash32(&baseline.var),beta:baseline.beta.clone(),regularised_focus_sha256:hash32(reg),
            accepted_pixels:0,replay_exact:false,source_unchanged:true});}
    let baseline_averaged_fraction=baseline.merge.averaged_fraction();let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    let mut replay=BandWorker::new(domain,cfg);let mut estimator=match forced_source{Some(i)=>CoherentAccumulator::new_forced(&stats,i)?,None=>CoherentAccumulator::new(&stats,mode)?};
    for(i,f)in frames.iter().enumerate(){ensure!(replay.fold(&source,i,f.levels,noise,Some(&map),None)?,"second-pass source refused");let ev=&mut evidence[i];
        let reg=work.compute(&replay.luma,noise)?;ensure!(hashes(&replay.planes)==ev.known4_sha256&&hash32(&replay.luma)==ev.guide_sha256
            &&hash32(&replay.var)==ev.variance_sha256&&same(&replay.beta,&ev.beta)&&hash32(reg)==ev.regularised_focus_sha256,"actual source/focus replay differs");
        ev.accepted_pixels=estimator.add(i,&replay.planes,reg)?;ensure!(hash16(&f.data)==ev.source_sha256,"original CFA changed");ev.replay_exact=true;}
    ensure!(hashes(&replay.merge.finish(&mut Workspace::new(&sizes)))==hashes(&baseline_planes4),"current baseline replay differs");
    let candidate_planes4=estimator.finish()?;let one_source_mean_exact=if frames.len()==1 {
        ensure!(candidate_planes4.iter().zip(&replay.planes).all(|(a,b)|same(a,b))&&estimator.counts().iter().all(|&n|n==1),"one-source native mean differs");Some(true)
    }else{None};
    let baseline_rgb=phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    ensure!(baseline_rgb.iter().chain(&candidate_rgb).all(|v|v.is_finite()),"nonfinite developed RGB");
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),baseline_averaged_fraction,counts:estimator.counts().to_vec(),
        best_index:stats.best_index().to_vec(),best_focus:stats.best_focus().to_vec(),frames:evidence,exact_coherent_replay:true,one_source_mean_exact,forced_source})
}
mod independent_controls {include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/native-coherent-estimator/independent-controls.rs"));}
