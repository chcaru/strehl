// Fixed-boundary complete CFA operator; public generated entry points remain bounded.
// A separate explicitly invoked observational adapter has no quality admission.
use super::*;
use sha2::{Digest,Sha256};
use strehl_core::{CfaPlane,align::Similarity};
use strehl_core::optics::OpticalProfile;
use strehl_core::pyramid::{correction_variance_diagnostic as kernels,
    AdmissionMode,BaseBand,Fallback,Hull,LevelSize,SelectMode};
pub(crate) use super::complex_wavelet_merge::Complex;
use super::complex_wavelet_merge::analysis_taps;
pub(crate) use super::all_cfa_wavelet::DirectionWeightSummary;
use super::phase_packed_rgb::camera_rgb;
fn squared(v:Complex)->f32 {v.re*v.re+v.im*v.im}
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/boundary-cfa-wavelet/transform.rs"));
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/boundary-cfa-wavelet/probe.rs"));

pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub guide_sha256:String,pub variance_sha256:String,
    pub gathered_known4_sha256:[String;4],pub plane_variance_sha256:[String;4],
    pub coefficient_variance_sha256:[String;4],pub probe_seeds:[usize;16],
    pub pair_band_mean4:Vec<Vec<[f64;4]>>,pub bias_band_mean_square4:Vec<[f64;4]>,
    pub known4_original_exact:Option<bool>,pub identity_guide_original_exact:Option<bool>,
    pub probe_seconds:f64,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,pub candidate_rgb:Vec<f32>,pub native_width:usize,pub native_height:usize,
    pub boundary:BoundaryPlan,pub bands:Vec<Subband>,pub baseline_level_sizes:Vec<[usize;2]>,
    pub baseline_averaged_fraction:Vec<f64>,pub candidate_fallback_fraction:Vec<f64>,
    pub candidate_weight_summary:Vec<DirectionWeightSummary>,pub frames:Vec<FrameEvidence>,
}
fn hash16(values:&[u16])->String {
    let mut h=Sha256::new();for v in values{h.update(v.to_le_bytes());}h.finalize().iter().map(|b|format!("{b:02x}")).collect()
}
fn hash32(values:&[f32])->String {
    let mut h=Sha256::new();for v in values{h.update(v.to_bits().to_le_bytes());}h.finalize().iter().map(|b|format!("{b:02x}")).collect()
}
fn original_equality(frame:&Frame,crop:align_cmd::CropRect,planes:&[Vec<f32>],guide:&[f32])->Result<()> {
    for (c,(dx,dy)) in [(0,0),(1,0),(0,1),(1,1)].into_iter().enumerate(){
        for y in 0..crop.height {for x in 0..crop.width {
            let v=(frame.active_row(2*(crop.y+y)+dy)[2*(crop.x+x)+dx] as f32-frame.levels.black).max(0.0);
            ensure!(planes[c][y*crop.width+x].to_bits()==v.to_bits(),"identity CFA mismatch");
        }}
    }
    ensure!(guide.iter().enumerate().all(|(i,v)|v.to_bits()==(0.5*(planes[1][i]+planes[2][i])).to_bits()),"identity green mismatch");Ok(())
}
// Shared ordered fusion loop. Moving this code does not change source order,
// f32 association, support, floor, exponent schedule, fallback, or hull.
#[allow(clippy::too_many_arguments)]
fn fold_coefficients(known:&[Vec<f32>],wave:&[Vec<Complex>],variance4:&[Vec<f32>],
    cfg:MergeConfig,gains:[f32;4],depth:usize,bands:&[Subband],
    sums:&mut[Vec<Complex>],means:&mut[Vec<Complex>],den:&mut[f32],counts:&mut[u16],
    low:&mut[Vec<f32>],high:&mut[Vec<f32>],summary:&mut[DirectionWeightSummary],diagnostics:bool)->Result<()> {
    let n=den.len();let native_n=known[0].len();
        for c in 0..4 {for i in 0..n {means[c][i].re+=wave[c][i].re;means[c][i].im+=wave[c][i].im;}
            for i in 0..native_n {low[c][i]=low[c][i].min(known[c][i]);high[c][i]=high[c][i].max(known[c][i]);}}
        for (j,b) in bands.iter().enumerate() {
            let size=LevelSize{width:b.width,height:b.height};let pos=&b.positions;
            let energy=pos.iter().map(|&i|(0..4).map(|c|gains[c]*squared(wave[c][i])).sum()).collect::<Vec<f32>>();
            let variance=pos.iter().map(|&i|(0..4).map(|c|gains[c]*variance4[c][i]).sum()).collect::<Vec<f32>>();
            let energy=kernels::smooth(&energy,size);let variance=kernels::smooth(&variance,size);
            let mut own=Vec::new();
            if diagnostics {for c in 0..4 {
                let e=pos.iter().map(|&i|gains[c]*squared(wave[c][i])).collect::<Vec<_>>();
                let v=pos.iter().map(|&i|gains[c]*variance4[c][i]).collect::<Vec<_>>();
                let e=kernels::smooth(&e,size);let v=kernels::smooth(&v,size);
                let live=e.iter().zip(v).map(|(&e,v)|{
                    let floor=cfg.gate*v;kernels::soft_weight((e-floor).max(0.0),floor,cfg.exponent_at(b.level,depth))>0.0
                }).collect::<Vec<_>>();
                summary[j].own_plane_positive_source_coefficients[c]+=live.iter().filter(|&&v|v).count();own.push(live);
            }}
            for (local,((&i,&e),&v)) in pos.iter().zip(&energy).zip(&variance).enumerate() {
                ensure!(e.is_finite() && v.is_finite(),"nonfinite supported coefficient evidence");
                let floor=cfg.gate*v;
                let weight=kernels::soft_weight((e-floor).max(0.0),floor,cfg.exponent_at(b.level,depth));
                ensure!(weight.is_finite() && weight>=0.0,"invalid shared weight");
                summary[j].min_weight=summary[j].min_weight.min(weight);summary[j].max_weight=summary[j].max_weight.max(weight);
                if weight>0.0 {counts[i]+=1;summary[j].positive_source_coefficients+=1;}
                else if diagnostics {for c in 0..4 {if own[c][local]{summary[j].own_plane_positive_aggregate_zero[c]+=1;}}}
                den[i]+=weight;
                for c in 0..4 {sums[c][i].re+=weight*wave[c][i].re;sums[c][i].im+=weight*wave[c][i].im;}
            }
        }
    Ok(())
}

pub(crate) fn compare_generated(frames:&[Frame],crop:align_cmd::CropRect,warps:&[Similarity],
    noise:&NoiseModel,diagnostics:bool)->Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len()<=32 && frames.len()==warps.len(),"bounded matched source/warp count");
    ensure!(crop.width==113 && crop.height==101,"fixed113x101 boundary quality screen");
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;
    ensure!(wb[..3].iter().all(|v|v.is_finite() && *v>0.0),"invalid WB");
    ensure!(frames.iter().all(|f|f.geometry()==full && f.levels==first.levels
        && f.wb_coeffs[..3]==wb[..3] && f.active==first.active && f.stride==first.stride
        && f.buffer_height==first.buffer_height && !f.path.exists()),"source metadata/layout changed");
    for (frame,&warp) in frames.iter().zip(warps){gather_scope(frame,warp,crop)?;}
    ensure!(gatefloor::enabled(),"actual baseline gatefloor required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()
        ==strehl_core::pyramid::fine_support_candidate::Mode::Off,"fine support excluded");
    let cfg=MergeConfig::default();
    ensure!(cfg.bands==7 && cfg.gate==2.0 && cfg.exponent==2.0 && cfg.sharpen_per_octave==1.4
        && cfg.mean_coarse==0 && cfg.select==SelectMode::SoftPower && cfg.admission==AdmissionMode::HardFloor
        && cfg.base==BaseBand::Mean && cfg.fallback==Fallback::Mean && cfg.hull==Hull::InputRange
        && cfg.significance_scale==0.0,"held default merge configuration differs");
    let plan=BoundaryPlan::new(crop.width,crop.height)?;let depth=plan.depth();
    let (w,h)=(plan.padded_width,plan.padded_height);let n=w*h;let native_n=crop.width*crop.height;
    let bands=subbands(w,h)?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("boundary-cfa-wavelet-generated",&entries),
        strategy:"fixed supplied generated similarities".into(),heldout_px:None,cycle_floor_px:None,reference:0,
        note:"GPU rounded no-CA generated boundary screen; no photographic admission".into()},
        full,Resampler::CatmullRom,warps.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()}
        fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);let mut baseline=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);
    let gains=[wb[0]/wb[1],1.0,1.0,wb[2]/wb[1]].map(|v|v*v);
    ensure!(gains.iter().all(|v|v.is_finite()),"WB squared overflow");
    let mut sums=vec![vec![Complex::default();n];4];let mut means=sums.clone();
    let mut den=vec![0.0f32;n];let mut counts=vec![0u16;n];
    let mut low=vec![vec![f32::INFINITY;native_n];4];let mut high=vec![vec![f32::NEG_INFINITY;native_n];4];
    let mut summary=bands.iter().map(|b|DirectionWeightSummary{min_weight:f32::INFINITY,max_weight:0.0,
        positive_source_coefficients:0,multi_source_coefficients:0,total_coefficients:b.positions.len(),
        own_plane_positive_source_coefficients:[0;4],own_plane_positive_aggregate_zero:[0;4]}).collect::<Vec<_>>();
    let mut evidence=Vec::new();
    for (index,(frame,&warp)) in frames.iter().zip(warps).enumerate() {
        let source_hash=hash16(&frame.data);
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?,"actual baseline refused source");
        let identity=warp==Similarity::IDENTITY;
        if identity{original_equality(frame,crop,&baseline.planes,&baseline.luma)?;}
        let wave=extend_four(&baseline.planes,&plan)?.iter().map(|p|forward_real(p,w,h)).collect::<Result<Vec<_>>>()?;
        let start=Instant::now();
        let probe=probe_from_wave(frame,warp,crop,noise,&plan,index,diagnostics,&wave)?;
        let probe_seconds=start.elapsed().as_secs_f64();
        fold_coefficients(&baseline.planes,&wave,&probe.variance4,cfg,gains,depth,&bands,
            &mut sums,&mut means,&mut den,&mut counts,&mut low,&mut high,&mut summary,diagnostics)?;
        let bias_band_mean_square4=probe.bias4.as_ref().map(|bias|bands.iter().map(|b|
            std::array::from_fn(|c|b.positions.iter().map(|&i|{
                let v=bias[c][i];(v.re as f64).powi(2)+(v.im as f64).powi(2)
            }).sum::<f64>()/b.positions.len() as f64)).collect()).unwrap_or_default();
        let plane_variance_sha256=std::array::from_fn(|c|{
            let(dx,dy)=[(0,0),(1,0),(0,1),(1,1)][c];
            let original=&probe.original_variance;
            let v=(0..full.height).flat_map(|y|(0..full.width).map(move|x|
                original[(2*y+dy)*(2*full.width)+2*x+dx])).collect::<Vec<_>>();hash32(&v)
        });
        evidence.push(FrameEvidence{source_sha256:source_hash.clone(),guide_sha256:hash32(&baseline.luma),
            variance_sha256:hash32(&baseline.var),gathered_known4_sha256:std::array::from_fn(|c|hash32(&baseline.planes[c])),
            plane_variance_sha256,coefficient_variance_sha256:std::array::from_fn(|c|hash32(&probe.variance4[c])),
            probe_seeds:probe.seeds,pair_band_mean4:probe.pair_band_mean4,bias_band_mean_square4,
            known4_original_exact:identity.then_some(true),identity_guide_original_exact:identity.then_some(true),probe_seconds});
        ensure!(hash16(&frame.data)==source_hash,"original generated source changed");
    }
    let baseline_averaged_fraction=baseline.merge.averaged_fraction();
    let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    let fallback=bands.iter().map(|b|b.positions.iter().filter(|&&i|den[i]==0.0).count() as f64/b.positions.len() as f64).collect();
    for (b,s) in bands.iter().zip(&mut summary) {s.multi_source_coefficients=b.positions.iter().filter(|&&i|counts[i]>1).count();}
    for c in 0..4 {for i in 0..n {
        if den[i]>0.0 {sums[c][i].re/=den[i];sums[c][i].im/=den[i];}
        else {sums[c][i].re=means[c][i].re/frames.len() as f32;sums[c][i].im=means[c][i].im/frames.len() as f32;}
    }}drop(means);
    let reconstructed=sums.iter().map(|v|Ok(inverse_complete(v,w,h)?.iter().map(|v|v.re).collect::<Vec<_>>()))
        .collect::<Result<Vec<_>>>()?;
    let mut candidate_planes4=crop_four(&reconstructed,&plan)?;
    for c in 0..4 {for i in 0..native_n {candidate_planes4[c][i]=candidate_planes4[c][i].clamp(low[c][i],high[c][i]);}}
    let baseline_rgb=camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb=camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*crop.width,native_height:2*crop.height,
        boundary:plan,bands,baseline_level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),baseline_averaged_fraction,
        candidate_fallback_fraction:fallback,candidate_weight_summary:summary,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/boundary-cfa-wavelet/independent-controls.rs"));
}

mod full_stack {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/boundary-cfa-wavelet/full-stack.rs"));
}

mod independent_full_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/boundary-cfa-wavelet/independent-full-controls.rs"));
}
