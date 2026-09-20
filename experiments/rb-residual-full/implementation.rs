// Explicit full observational scope; the generated residual-guard rejection stays frozen.
use super::*;
use sha2::{Digest,Sha256};
use serde_json::json;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{LevelSize,Hull,Fallback,rb_own_guide_diagnostic as core,
    rb_residual_guard_diagnostic as residual_core,correction_variance_diagnostic as kernels};
use super::rb_own_guide::{GuideBands,guide_laplacians,active_hash,source_seeds};
use super::shared_source_field::hash32;

// Only gather scope changes; original variances/draw arithmetic remain frozen.
mod source_probe {
    use super::*;
    pub(crate) use super::super::boundary_cfa_wavelet::{original_variances,noisy_source};
    pub(crate) fn gather_known4(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect)->Result<Vec<Vec<f32>>> {
        full_binding(frame,warp,crop)?;
        super::super::shared_source_field::gather_direct(frame,warp,crop)
    }
}
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-residual-guard/probe.rs"));
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-residual-guard/guard.rs"));
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-residual-full/writer.rs"));

pub(crate) fn full_binding(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect)->Result<()> {
    ensure!(frame.geometry()==PlaneGeometry{width:3516,height:2344}
        && [crop.x,crop.y,crop.width,crop.height]==[28,19,3460,2306]
        && frame.camera=="ILCE-7CM2" && frame.iso==Some(100.0)
        && frame.levels==Levels{black:512.0,white:15360.0},"held full sensor/domain scope");
    let id=strehl_raw::identity(&frame.path);
    let ca=strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?;
    ensure!(ca.is_some_and(|p|p.key=="a7c2-fe100gm-2xtc-x4cpl"),"held full optical profile required");
    ensure!(phase_packed_rgb::full_stack::full_source_supported(warp,frame.geometry(),crop,ca),"full pull unsupported");
    Ok(())
}
pub(crate) struct Accumulator {
    sizes:Vec<LevelSize>,cfg:MergeConfig,cost:bool,seen:usize,in_chunk:usize,chunks:Vec<usize>,
    own:[BandMerge;2],work:[FrameWorkspace;2],total:[Option<BandMerge>;2],activation:Activation,
}
impl Accumulator {
    pub(crate) fn new(sizes:&[LevelSize],cfg:MergeConfig,cost:bool)->Result<Self> {
        ensure!(sizes==level_sizes(3460,2306,7).as_slice() && cfg.bands==7
            && cfg.select==SelectMode::SoftPower && cfg.admission==AdmissionMode::HardFloor
            && cfg.base==BaseBand::Mean && cfg.fallback==Fallback::Mean && cfg.hull==Hull::InputRange
            && cfg.mean_coarse==0 && cfg.significance_scale==0.0,"fixed full native band scope");
        // Explicit full-only constructor around the unchanged included update implementation.
        let activation=Activation {sizes:sizes.to_vec(),n:70,q:threshold_f32(70,sizes.len()-1)?,
            masks:std::array::from_fn(|_|sizes[..sizes.len()-1].iter().map(|s|vec![0.0;s.pixels()]).collect()),
            source_triggers:Vec::new()};
        Ok(Self {sizes:sizes.to_vec(),cfg,cost,seen:0,in_chunk:0,chunks:vec![],activation,
            own:std::array::from_fn(|_|BandMerge::new(3460,2306,1,cfg)),
            work:std::array::from_fn(|_|FrameWorkspace::new(sizes,1)),total:[None,None]})
    }
    pub(crate) fn fold(&mut self,frame:&Frame,index:usize,warp:Similarity,crop:align_cmd::CropRect,
        noise:&NoiseModel,known:&[Vec<f32>])->Result<serde_json::Value> {
        ensure!(if self.cost {self.seen==0 && index==35} else {self.seen<70 && index==self.seen},"full source order/count");
        full_binding(frame,warp,crop)?;
        let started=Instant::now();let signal=guide_laplacians(known,&self.sizes)?;
        let signal_seconds=started.elapsed().as_secs_f64();let start=Instant::now();
        let probe=probe_noise(frame,warp,crop,noise,&self.sizes,false)?;
        let probe_seconds=start.elapsed().as_secs_f64();let start=Instant::now();
        self.activation.add_source(&signal,&probe.coefficient_variance3)?;
        let mut counts=Vec::new();
        for (i,c) in [0,2].into_iter().enumerate() {
            let energy=signal[c].iter().enumerate().map(|(k,v)|kernels::energy(v,self.sizes[k])).collect();
            let floor=probe.energy3[c].iter().map(|v|v.iter().map(|x|self.cfg.gate*x).collect()).collect();
            let fields=core::fields_from_energy(&self.sizes,self.cfg,energy,floor);
            counts.push(fields.weights.iter().map(|v|v.iter().filter(|&&x|x>0.0).count()).collect::<Vec<_>>());
            core::add_fields(&mut self.own[i],&[&known[[0,3][i]]],&fields,&mut self.work[i]);
        }
        let weight_seconds=start.elapsed().as_secs_f64();self.seen+=1;self.in_chunk+=1;
        Ok(json!({"source_index":index,"signal_transform_seconds":signal_seconds,"probe_seconds":probe_seconds,
            "weights_seconds":weight_seconds,"probe_pairs":PROBE_PAIRS,"probe_seeds":probe.seeds,
            "source_active_u16_sha256":probe.active_sha256,
            "coefficient_variance_sha256":probe.coefficient_variance3.iter().map(|g|g.iter().map(|v|hash32(v)).collect::<Vec<_>>()).collect::<Vec<_>>(),
            "coefficient_variance_min_max":probe.coefficient_variance3.iter().map(|g|g.iter().map(|v|[
                v.iter().copied().fold(f32::INFINITY,f32::min),v.iter().copied().fold(0.0,f32::max)]).collect::<Vec<_>>()).collect::<Vec<_>>(),
            "source_trigger_counts_rb":self.activation.source_triggers.last(),"positive_weight_counts_rb":counts,
            "threshold":threshold(70,self.sizes.len()-1)?,"threshold_f32":self.activation.q}))
    }
    pub(crate) fn close_chunk(&mut self)->Result<()> {
        let expected=if self.cost {1}else if self.chunks.len()<3 {18}else {16};
        ensure!(self.in_chunk==expected && self.chunks.len()<if self.cost{1}else{4},"canonical candidate chunk differs");
        for i in 0..2 {
            phase_packed_rgb::full_stack::absorb_chunk(&mut self.total[i],&mut self.own[i],3460,2306,1,self.cfg);
            self.own[i]=BandMerge::new(3460,2306,1,self.cfg);
            self.work[i].next_frame();
        }
        self.chunks.push(self.in_chunk);self.in_chunk=0;Ok(())
    }
    pub(crate) fn finish(self,canonical:&BandMerge,ws:&mut Workspace)->Result<(Vec<Vec<f32>>,serde_json::Value)> {
        ensure!(self.seen==if self.cost{1}else{70} && self.in_chunk==0
            && self.chunks==if self.cost{vec![1]}else{vec![18,18,18,16]},"candidate sources/chunks incomplete");
        let own0=self.total[0].as_ref().context("missing red accumulator")?;
        let own1=self.total[1].as_ref().context("missing blue accumulator")?;
        let counts=self.activation.masks.iter().map(|g|g.iter().map(|v|v.iter().filter(|&&x|x!=0.0).count()).collect::<Vec<_>>()).collect::<Vec<_>>();
        let masks_hash=self.activation.masks.iter().map(|g|g.iter().map(|v|hash32(v)).collect::<Vec<_>>()).collect::<Vec<_>>();
        let output=residual_core::finish_guarded(canonical,[own0,own1],&self.activation.masks,ws);
        let summary=json!({"threshold_population":70,"observed_sources":self.seen,"candidate_chunks":self.chunks,
            "activation_counts_rb":counts,"activation_mask_sha256":masks_hash,
            "band_dimensions":self.sizes[..self.sizes.len()-1].iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
            "threshold":threshold(70,self.sizes.len()-1)?,"threshold_f32":self.activation.q,
            "candidate_averaged_fraction_rb":[own0.averaged_fraction(),own1.averaged_fraction()],
            "terminal_base_exact":true,"camera_green_preserved_by_writer":true});
        Ok((output,summary))
    }
}
mod full_stack {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-residual-full/full-stack.rs"));
}
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-residual-full/independent-controls.rs"));
}
