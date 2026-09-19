// Generated-only, fixed two-level complex fusion with shared all-CFA evidence.
// Reuses the commissioned MIT-derived operator; attribution and exact pin:
// ../complex-wavelet-merge/licence.txt and implementation.rs. No copied filter.
use super::*;
use sha2::{Digest, Sha256};
use strehl_core::{CfaPlane, align::Similarity};
use strehl_core::pyramid::{correction_variance_diagnostic as kernels, AdmissionMode,
    BaseBand, Fallback, Hull, LevelSize, SelectMode};
pub(crate) use super::complex_wavelet_merge::Complex;
use super::complex_wavelet_merge::{analysis_taps, transform_one, inverse_one};
use super::phase_packed_rgb::camera_rgb;

fn dimensions(w: usize, h: usize, n: usize) -> Result<()> {
    ensure!(w >= 12 && h >= 12 && w % 4 == 0 && h % 4 == 0
        && w.checked_mul(h) == Some(n) && n <= 512*512,
        "two-level operator requires bounded dimensions divisible by four and >=12");
    Ok(())
}
fn squared(v: Complex) -> f32 { v.re*v.re + v.im*v.im }
fn multiply(a: Complex, b: Complex) -> Complex {
    Complex { re:a.re*b.re-a.im*b.im, im:a.re*b.im+a.im*b.re }
}
fn ll(input: &[Complex], w: usize, h: usize) -> Vec<Complex> {
    (0..h/2).flat_map(|y|input[y*w..y*w+w/2].iter().copied()).collect()
}
fn replace_ll(output: &mut [Complex], inner: &[Complex], w: usize, h: usize) {
    for y in 0..h/2 { output[y*w..y*w+w/2].copy_from_slice(&inner[y*(w/2)..(y+1)*(w/2)]); }
}
/// Packed outer H/D/V, with the complex LL rectangle recursively decomposed.
pub(crate) fn transform_two(input: &[Complex], w: usize, h: usize) -> Result<Vec<Complex>> {
    dimensions(w,h,input.len())?;
    let mut out=transform_one(input,w,h)?;
    let inner=transform_one(&ll(&out,w,h),w/2,h/2)?;
    replace_ll(&mut out,&inner,w,h);
    Ok(out)
}
pub(crate) fn forward_real(input: &[f32], w: usize, h: usize) -> Result<Vec<Complex>> {
    transform_two(&input.iter().map(|&re|Complex{re,im:0.0}).collect::<Vec<_>>(),w,h)
}
pub(crate) fn inverse_two(input: &[Complex], w: usize, h: usize) -> Result<Vec<Complex>> {
    dimensions(w,h,input.len())?;
    let inner=inverse_one(&ll(input,w,h),w/2,h/2)?;
    let mut outer=input.to_vec();
    replace_ll(&mut outer,&inner,w,h);
    inverse_one(&outer,w,h)
}

/// Compose complex analysis paths onto ORIGINAL real samples before squaring.
/// At level1 (the second transform), offset=(j-3)+2*(k-3), weight=L[j]*B[k].
/// Distinct paths and periodic aliases reaching one sample must add coherently.
fn axis_energy(level: usize, high: bool, length: usize) -> Vec<(usize,f32)> {
    let band=analysis_taps(high);
    let mut combined=vec![Complex::default();length];
    if level==0 {
        for (j,&v) in band.iter().enumerate() {
            let i=(j as isize-3).rem_euclid(length as isize) as usize;
            combined[i].re+=v.re; combined[i].im+=v.im;
        }
    } else {
        assert_eq!(level,1);
        let low=analysis_taps(false);
        for (j,&a) in low.iter().enumerate() { for (k,&b) in band.iter().enumerate() {
            let i=(j as isize-3+2*(k as isize-3)).rem_euclid(length as isize) as usize;
            let v=multiply(a,b); combined[i].re+=v.re; combined[i].im+=v.im;
        }}
    }
    combined.into_iter().enumerate().map(|(i,v)|(i,squared(v))).filter(|(_,v)|*v>0.0).collect()
}
/// E|W_noise|² from independent original CFA variance, including LL covariance
/// through composition. No recursive scalar-LL approximation or new calibration.
/// This is not energy-statistic variance or fractional-gather propagation.
pub(crate) fn coefficient_variance(input: &[f32], w: usize, h: usize) -> Result<Vec<f32>> {
    dimensions(w,h,input.len())?;
    ensure!(input.iter().all(|v|v.is_finite() && *v>=0.0),"invalid original-site variance");
    let mut out=vec![0.0;input.len()];
    for level in 0..2 {
        let step=1usize<<(level+1);
        let (bw,bh)=(w/step,h/step);
        for by in 0..2 { for bx in 0..2 {
            // Outer LL is overwritten by all four inner quadrants below.
            let ky=axis_energy(level,by!=0,h);
            let kx=axis_energy(level,bx!=0,w);
            let mut vertical=vec![0.0;bh*w];
            for y in 0..bh { for x in 0..w {
                let mut value=0.0;
                for &(dy,a) in &ky { value+=a*input[((step*y+dy)%h)*w+x]; }
                vertical[y*w+x]=value;
            }}
            for y in 0..bh { for x in 0..bw {
                let mut value=0.0;
                for &(dx,a) in &kx { value+=a*vertical[y*w+(step*x+dx)%w]; }
                out[(by*bh+y)*w+bx*bw+x]=value;
            }}
        }}
    }
    ensure!(out.iter().all(|v|v.is_finite()),"composed variance overflow");
    Ok(out)
}
fn positions(w: usize,h: usize,level: usize,direction: usize) -> impl Iterator<Item=usize> {
    let (bx,by)=[(1,0),(1,1),(0,1)][direction];
    let (bw,bh)=(w>>(level+1),h>>(level+1));
    (0..bh).flat_map(move|y|(0..bw).map(move|x|(by*bh+y)*w+bx*bw+x))
}
pub(crate) struct FrameEvidence {
    pub source_sha256:String,
    pub guide_sha256:String,
    pub variance_sha256:String,
    pub plane_variance_sha256:[String;4],
    pub coefficient_variance_sha256:[String;4],
    pub known4_original_exact:bool,
    pub identity_guide_original_exact:bool,
}
pub(crate) struct DirectionWeightSummary {
    pub min_weight:f32,
    pub max_weight:f32,
    pub positive_source_coefficients:usize,
    pub multi_source_coefficients:usize,
    pub total_coefficients:usize,
    // Diagnostic only: each colour's own E/V through the identical weight rule.
    pub own_plane_positive_source_coefficients:[usize;4],
    pub own_plane_positive_aggregate_zero:[usize;4],
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,
    pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,
    pub candidate_rgb:Vec<f32>,
    pub native_width:usize,
    pub native_height:usize,
    pub baseline_averaged_fraction:Vec<f64>,
    pub candidate_fallback_fraction:[[f64;3];2],
    pub candidate_weight_summary:[[DirectionWeightSummary;3];2],
    pub known4_original_exact:bool,
    pub identity_guide_original_exact:bool,
    pub frames:Vec<FrameEvidence>,
}
fn hash16(v:&[u16])->String {
    let mut h=Sha256::new();for x in v {h.update(x.to_le_bytes());}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}
fn hash32(v:&[f32])->String {
    let mut h=Sha256::new();for x in v {h.update(x.to_bits().to_le_bytes());}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}
fn original_equality(frame:&Frame,crop:align_cmd::CropRect,planes:&[Vec<f32>],guide:&[f32])->Result<()> {
    for (c,(dx,dy)) in [(0,0),(1,0),(0,1),(1,1)].into_iter().enumerate() {
        for y in 0..crop.height {for x in 0..crop.width {
            let original=frame.active_row(2*(crop.y+y)+dy)[2*(crop.x+x)+dx] as f32-frame.levels.black;
            ensure!(planes[c][y*crop.width+x].to_bits()==original.to_bits(),"identity CFA differs at {c},{x},{y}");
        }}
    }
    for (i,&v) in guide.iter().enumerate() {
        ensure!(v.to_bits()==(0.5*(planes[1][i]+planes[2][i])).to_bits(),"identity green mean differs");
    }
    Ok(())
}

/// Fixed identity generated sources, two complex levels and actual bands=2
/// baseline. Only current-frame transforms plus cumulative fields are retained.
pub(crate) fn compare_generated(frames:&[Frame],crop:align_cmd::CropRect,noise:&NoiseModel)->Result<Comparison> {
    compare_generated_with_diagnostics(frames,crop,noise,true)
}
/// Diagnostic switch affects only the own-plane witness, never aggregate fusion.
pub(crate) fn compare_generated_with_diagnostics(frames:&[Frame],crop:align_cmd::CropRect,
    noise:&NoiseModel,diagnostics:bool)->Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len()<=32,"bounded generated frame count");
    let full=frames[0].geometry();
    ensure!(full.width<=512 && full.height<=512 && frames.iter().all(|f|f.geometry()==full
        && f.levels==frames[0].levels && !f.path.exists()
        && f.wb_coeffs[..3]==frames[0].wb_coeffs[..3]),"generated identity scope differs");
    let wb=frames[0].wb_coeffs;
    ensure!(wb[..3].iter().all(|v|v.is_finite() && *v>0.0),"invalid held WB");
    let gains=[wb[0]/wb[1],1.0,1.0,wb[2]/wb[1]];
    let gain2=gains.map(|v|v*v);
    ensure!(gain2.iter().all(|v|v.is_finite()),"WB squared overflow");
    dimensions(crop.width,crop.height,crop.width*crop.height)?;
    for frame in frames {for y in 0..frame.active.height {
        ensure!(frame.active_row(y).iter().all(|&v|(v as f32)>frame.levels.black
            && (v as f32)<frame.levels.white),"identity screen excludes clipped/below-black samples");
    }}
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded,"actual rounded gather required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"local placement excluded");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"Malvar required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()
        ==strehl_core::pyramid::fine_support_candidate::Mode::Off,"fine support must be off");
    let cfg=MergeConfig{bands:2,..MergeConfig::default()};
    ensure!(cfg.gate==2.0 && cfg.mean_coarse==0 && cfg.select==SelectMode::SoftPower
        && cfg.admission==AdmissionMode::HardFloor && cfg.base==BaseBand::Mean
        && cfg.fallback==Fallback::Mean && cfg.hull==Hull::InputRange
        && cfg.significance_scale==0.0,"matched two-level defaults changed");
    let domain=PyramidDomain::cropped(full,crop)?;
    let sizes=level_sizes(crop.width,crop.height,2);
    ensure!(sizes.len()==3,"matched two-level baseline geometry");
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("all-cfa-two-level-generated",&entries),
        strategy:"fixed identity only".into(),heldout_px:None,cycle_floor_px:None,reference:0,
        note:"two-level generated operator; not full-product quality".into(),
    },full,Resampler::CatmullRom,vec![FrameWarp::Placed(Similarity::IDENTITY);frames.len()]);
    struct Source<'a>(&'a[Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize {self.0.len()}
        fn decode(&self,index:usize)->Result<Frame> {Ok(self.0[index].clone())}
    }
    let source=Source(frames);
    let (w,h)=(crop.width,crop.height);let n=w*h;
    let mut baseline=BandWorker::new(domain,cfg);
    let mut sums=vec![vec![Complex::default();n];4];
    let mut means=vec![vec![Complex::default();n];4];
    let mut den=vec![0.0f32;n];let mut counts=vec![0u16;n];
    let mut min_weight=[[f32::INFINITY;3];2];let mut max_weight=[[0.0f32;3];2];
    let mut positive=[[0usize;3];2];let mut own_positive=[[[0usize;4];3];2];
    let mut own_suppressed=[[[0usize;4];3];2];
    let mut low=vec![vec![f32::INFINITY;n];4];let mut high=vec![vec![f32::NEG_INFINITY;n];4];
    let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let source_sha256=hash16(&frame.data);
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?,"baseline refused source");
        original_equality(frame,crop,&baseline.planes,&baseline.luma)?;
        let wave=baseline.planes.iter().map(|p|forward_real(p,w,h)).collect::<Result<Vec<_>>>()?;
        let mut variance=Vec::with_capacity(4);
        let mut plane_hash=Vec::with_capacity(4);
        for (c,plane) in [CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B].into_iter().enumerate() {
            // The supplied model is evaluated in original, unscaled sample DN.
            let original=baseline.planes[c].iter().map(|&s|noise.variance(plane,s)).collect::<Vec<_>>();
            plane_hash.push(hash32(&original));
            variance.push(coefficient_variance(&original,w,h)?);
        }
        for i in 0..n {for c in 0..4 {
            means[c][i].re+=wave[c][i].re;means[c][i].im+=wave[c][i].im;
            low[c][i]=low[c][i].min(baseline.planes[c][i]);high[c][i]=high[c][i].max(baseline.planes[c][i]);
        }}
        for level in 0..2 {for d in 0..3 {
            let pos=positions(w,h,level,d).collect::<Vec<_>>();
            let size=LevelSize{width:w>>(level+1),height:h>>(level+1)};
            let energy=pos.iter().map(|&i|(0..4).map(|c|gain2[c]*squared(wave[c][i])).sum()).collect::<Vec<f32>>();
            let floor=pos.iter().map(|&i|(0..4).map(|c|gain2[c]*variance[c][i]).sum()).collect::<Vec<f32>>();
            let energy=kernels::smooth(&energy,size);let floor=kernels::smooth(&floor,size);
            let mut own_live=Vec::with_capacity(4);
            if diagnostics {for c in 0..4 {
                let e=pos.iter().map(|&i|gain2[c]*squared(wave[c][i])).collect::<Vec<_>>();
                let v=pos.iter().map(|&i|gain2[c]*variance[c][i]).collect::<Vec<_>>();
                let e=kernels::smooth(&e,size);let v=kernels::smooth(&v,size);
                let live=e.iter().zip(v).map(|(&e,v)| {
                    let floor=cfg.gate*v;
                    kernels::soft_weight((e-floor).max(0.0),floor,cfg.exponent_at(level,2))>0.0
                }).collect::<Vec<_>>();
                own_positive[level][d][c]+=live.iter().filter(|&&v|v).count();
                own_live.push(live);
            }}
            for (j,((&i,&e),&v)) in pos.iter().zip(&energy).zip(&floor).enumerate() {
                ensure!(e.is_finite() && v.is_finite(),"nonfinite supported evidence");
                let floor=cfg.gate*v;
                let weight=kernels::soft_weight((e-floor).max(0.0),floor,cfg.exponent_at(level,2));
                ensure!(weight.is_finite() && weight>=0.0,"invalid complex weight");
                min_weight[level][d]=min_weight[level][d].min(weight);max_weight[level][d]=max_weight[level][d].max(weight);
                if weight>0.0 {counts[i]+=1;positive[level][d]+=1;}
                else if diagnostics {for c in 0..4 {if own_live[c][j] {own_suppressed[level][d][c]+=1;}}}
                den[i]+=weight;
                for c in 0..4 {sums[c][i].re+=weight*wave[c][i].re;sums[c][i].im+=weight*wave[c][i].im;}
            }
        }}
        ensure!(hash16(&frame.data)==source_sha256,"generated source modified");
        evidence.push(FrameEvidence{source_sha256,guide_sha256:hash32(&baseline.luma),variance_sha256:hash32(&baseline.var),
            plane_variance_sha256:std::array::from_fn(|c|plane_hash[c].clone()),
            coefficient_variance_sha256:std::array::from_fn(|c|hash32(&variance[c])),
            known4_original_exact:true,identity_guide_original_exact:true});
    }
    let baseline_averaged_fraction=baseline.merge.averaged_fraction();
    let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    let candidate_fallback_fraction=std::array::from_fn(|level|std::array::from_fn(|d|
        positions(w,h,level,d).filter(|&i|den[i]==0.0).count() as f64/(n>>(2*(level+1))) as f64));
    let candidate_weight_summary=std::array::from_fn(|level|std::array::from_fn(|d|DirectionWeightSummary{
        min_weight:min_weight[level][d],max_weight:max_weight[level][d],positive_source_coefficients:positive[level][d],
        multi_source_coefficients:positions(w,h,level,d).filter(|&i|counts[i]>1).count(),
        total_coefficients:n>>(2*(level+1)),own_plane_positive_source_coefficients:own_positive[level][d],
        own_plane_positive_aggregate_zero:own_suppressed[level][d],
    }));
    for c in 0..4 {for i in 0..n {
        if den[i]>0.0 {sums[c][i].re/=den[i];sums[c][i].im/=den[i];}
        else {sums[c][i].re=means[c][i].re/frames.len() as f32;sums[c][i].im=means[c][i].im/frames.len() as f32;}
    }}
    drop(means);
    let candidate_planes4=sums.iter().enumerate().map(|(c,p)|{
        let values=inverse_two(p,w,h)?;
        Ok(values.iter().enumerate().map(|(i,v)|v.re.clamp(low[c][i],high[c][i])).collect())
    }).collect::<Result<Vec<Vec<f32>>>>()?;
    let rgb=|planes:&[Vec<f32>]|camera_rgb(planes,w,h,frames[0].levels,wb);
    let baseline_rgb=rgb(&baseline_planes4)?;let candidate_rgb=rgb(&candidate_planes4)?;
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*w,native_height:2*h,
        baseline_averaged_fraction,candidate_fallback_fraction,candidate_weight_summary,
        known4_original_exact:true,identity_guide_original_exact:true,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/all-cfa-wavelet/independent-controls.rs"));
}
