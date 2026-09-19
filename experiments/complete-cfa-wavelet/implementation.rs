// Fixed complete periodic128x128 CFA fusion; seven levels end in one DC value.
// Cyclic transform adapted from the frozen commissioned MIT-derived operator:
// ../complex-wavelet-merge/implementation.rs, (c)2019 Petteri Aimonen.
// Full MIT notice and upstream hashes remain in ../complex-wavelet-merge/licence.txt.
// Earlier operators and receipts are unchanged. No natural-image boundary claim.
use super::*;
use sha2::{Digest, Sha256};
use strehl_core::{CfaPlane, align::Similarity};
use strehl_core::pyramid::{correction_variance_diagnostic as kernels, AdmissionMode,
    BaseBand, Fallback, Hull, LevelSize, SelectMode, DEFAULT_BANDS};
pub(crate) use super::complex_wavelet_merge::Complex;
use super::complex_wavelet_merge::analysis_taps;
pub(crate) use super::all_cfa_wavelet::{FrameEvidence, DirectionWeightSummary};
use super::phase_packed_rgb::camera_rgb;
pub(crate) const LEVELS:usize=7;
fn dimensions(w:usize,h:usize,n:usize)->Result<()> {
    ensure!(w==128 && h==128 && n==128*128 && DEFAULT_BANDS==LEVELS,
        "complete periodic screen is fixed128x128 and seven levels to DC");
    Ok(())
}
fn cyclic_dimensions(w:usize,h:usize,n:usize)->Result<()> {
    ensure!(w>=2 && h>=2 && w%2==0 && h%2==0 && w.checked_mul(h)==Some(n)
        && n<=512*512,"cyclic one-level operator needs bounded even axes>=2");
    Ok(())
}
fn squared(v:Complex)->f32 {v.re*v.re+v.im*v.im}
fn multiply(a:Complex,b:Complex)->Complex {
    Complex{re:a.re*b.re-a.im*b.im,im:a.re*b.im+a.im*b.re}
}
fn wrap(pos: isize, length: usize) -> usize { pos.rem_euclid(length as isize) as usize }
fn location(line: usize, pos: usize, width: usize, vertical: bool) -> usize {
    if vertical { pos * width + line } else { line * width + pos }
}

fn analysis_1d(src: &[Complex], w: usize, h: usize, vertical: bool) -> Vec<Complex> {
    let (count, length) = if vertical { (w, h) } else { (h, w) };
    let high = analysis_taps(true);
    let low = analysis_taps(false);
    let mut dst = vec![Complex::default(); src.len()];
    for line in 0..count { for y in (0..length).step_by(2) {
        let (mut lo, mut hi) = (Complex::default(), Complex::default());
        for j in 0..6 {
            let pos = wrap(y as isize + j as isize - 3, length);
            let value = src[location(line, pos, w, vertical)];
            lo.re += value.re * low[j].re - value.im * low[j].im;
            lo.im += value.im * low[j].re + value.re * low[j].im;
            hi.re += value.re * high[j].re - value.im * high[j].im;
            hi.im += value.im * high[j].re + value.re * high[j].im;
        }
        dst[location(line, y / 2, w, vertical)] = lo;
        dst[location(line, y / 2 + length / 2, w, vertical)] = hi;
    }}
    dst
}
fn synthesis_1d(src: &[Complex], w: usize, h: usize, vertical: bool) -> Vec<Complex> {
    let (count, length) = if vertical { (w, h) } else { (h, w) };
    let high = analysis_taps(true);
    let low = analysis_taps(false);
    let mut dst = vec![Complex::default(); src.len()];
    for line in 0..count { for y in 0..length {
        let mut value = Complex::default();
        for j in ((y + 3) % 2..6).step_by(2) {
            let pos = wrap((y as isize - j as isize + 3) / 2, length / 2);
            let lo = src[location(line, pos, w, vertical)];
            let hi = src[location(line, pos + length / 2, w, vertical)];
            // Preserve the source CPU accumulation order and conjugation.
            value.re += lo.re * low[j].re + hi.re * high[j].re;
            value.re += lo.im * low[j].im + hi.im * high[j].im;
            value.im += lo.im * low[j].re + hi.im * high[j].re;
            value.im -= lo.re * low[j].im + hi.re * high[j].im;
        }
        dst[location(line, y, w, vertical)] = value;
    }}
    dst
}
pub(crate) fn transform_one_cyclic(input: &[Complex], width: usize, height: usize) -> Result<Vec<Complex>> {
    cyclic_dimensions(width, height, input.len())?;
    ensure!(input.iter().all(|v| (v.re.is_finite() && v.im.is_finite())), "nonfinite complex input");
    let vertical = analysis_1d(input, width, height, true);
    let result = analysis_1d(&vertical, width, height, false);
    ensure!(result.iter().all(|v| (v.re.is_finite() && v.im.is_finite())), "nonfinite complex analysis");
    Ok(result)
}
pub(crate) fn inverse_one_cyclic(input: &[Complex], width: usize, height: usize) -> Result<Vec<Complex>> {
    cyclic_dimensions(width, height, input.len())?;
    ensure!(input.iter().all(|v| (v.re.is_finite() && v.im.is_finite())), "nonfinite synthesis input");
    let vertical = synthesis_1d(input, width, height, true);
    let result = synthesis_1d(&vertical, width, height, false);
    ensure!(result.iter().all(|v| (v.re.is_finite() && v.im.is_finite())), "nonfinite complex synthesis");
    Ok(result)
}


fn rectangle(input:&[Complex],stride:usize,w:usize,h:usize)->Vec<Complex> {
    (0..h).flat_map(|y|input[y*stride..y*stride+w].iter().copied()).collect()
}
fn replace_rectangle(out:&mut[Complex],inner:&[Complex],stride:usize,w:usize,h:usize) {
    for y in 0..h {out[y*stride..y*stride+w].copy_from_slice(&inner[y*w..(y+1)*w]);}
}
/// Decompose every complex LL rectangle until only its DC coefficient remains.
pub(crate) fn transform_complete(input:&[Complex],w:usize,h:usize)->Result<Vec<Complex>> {
    dimensions(w,h,input.len())?;
    let mut out=input.to_vec();
    for level in 0..LEVELS {
        let (cw,ch)=(w>>level,h>>level);
        let inner=transform_one_cyclic(&rectangle(&out,w,cw,ch),cw,ch)?;
        replace_rectangle(&mut out,&inner,w,cw,ch);
    }
    Ok(out)
}
pub(crate) fn forward_real(input:&[f32],w:usize,h:usize)->Result<Vec<Complex>> {
    transform_complete(&input.iter().map(|&re|Complex{re,im:0.0}).collect::<Vec<_>>(),w,h)
}
pub(crate) fn inverse_complete(input:&[Complex],w:usize,h:usize)->Result<Vec<Complex>> {
    dimensions(w,h,input.len())?;
    let mut out=input.to_vec();
    for level in (0..LEVELS).rev() {
        let (cw,ch)=(w>>level,h>>level);
        let inner=inverse_one_cyclic(&rectangle(&out,w,cw,ch),cw,ch)?;
        replace_rectangle(&mut out,&inner,w,cw,ch);
    }
    Ok(out)
}
/// Original-sample complex filter. Fold every repeated path modulo the ORIGINAL
/// length at every stage, retaining complex phase; square only the final sum.
fn axis_energy(level:usize,high:bool,length:usize)->Vec<(usize,f32)> {
    let mut current=vec![Complex::default();length];current[0].re=1.0;
    for stage in 0..=level {
        let taps=analysis_taps(stage==level && high);
        let mut next=vec![Complex::default();length];
        for (source,&a) in current.iter().enumerate() {
            for (j,&b) in taps.iter().enumerate() {
                let offset=(source as isize+(1isize<<stage)*(j as isize-3))
                    .rem_euclid(length as isize) as usize;
                let v=multiply(a,b);next[offset].re+=v.re;next[offset].im+=v.im;
            }
        }
        current=next;
    }
    current.into_iter().enumerate().map(|(i,v)|(i,squared(v)))
        .filter(|(_,v)|*v>0.0).collect()
}
/// E|W_noise|² from independent original real CFA sites, including the complex
/// LL correlation via exact composed filters. Not scalar LL recursion, energy
/// uncertainty, fractional gather, or a new sensor-noise calibration.
pub(crate) fn coefficient_variance(input:&[f32],w:usize,h:usize)->Result<Vec<f32>> {
    dimensions(w,h,input.len())?;
    ensure!(input.iter().all(|v|v.is_finite() && *v>=0.0),"invalid original-site variance");
    let mut out=vec![0.0;input.len()];
    for level in 0..LEVELS {
        let step=1usize<<(level+1);let (bw,bh)=(w/step,h/step);
        let kx=[axis_energy(level,false,w),axis_energy(level,true,w)];
        let ky=[axis_energy(level,false,h),axis_energy(level,true,h)];
        for by in 0..2 {
            let mut vertical=vec![0.0;bh*w];
            for y in 0..bh {for x in 0..w {
                let mut value=0.0;
                for &(dy,a) in &ky[by] {value+=a*input[((step*y+dy)%h)*w+x];}
                vertical[y*w+x]=value;
            }}
            for bx in 0..2 {for y in 0..bh {for x in 0..bw {
                let mut value=0.0;
                for &(dx,a) in &kx[bx] {value+=a*vertical[y*w+(step*x+dx)%w];}
                out[(by*bh+y)*w+bx*bw+x]=value;
            }}}
        }
    }
    ensure!(out.iter().all(|v|v.is_finite()),"composed variance overflow");
    Ok(out)
}
fn positions(w: usize,h: usize,level: usize,direction: usize) -> impl Iterator<Item=usize> {
    let (bx,by)=[(1,0),(1,1),(0,1)][direction];
    let (bw,bh)=(w>>(level+1),h>>(level+1));
    (0..bh).flat_map(move|y|(0..bw).map(move|x|(by*bh+y)*w+bx*bw+x))
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>,
    pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>,
    pub candidate_rgb:Vec<f32>,
    pub native_width:usize,
    pub native_height:usize,
    pub baseline_level_sizes:Vec<[usize;2]>,
    pub baseline_averaged_fraction:Vec<f64>,
    pub candidate_fallback_fraction:[[f64;3];LEVELS],
    pub candidate_weight_summary:[[DirectionWeightSummary;3];LEVELS],
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

/// Fixed identity generated sources. The actual baseline requests bands=7 but
/// reaches four detail bands and an 8x8 base at this domain size; its exponent
/// ramp uses that reached count. The candidate has seven levels to1x1 DC.
/// Only current-frame transforms plus cumulative fields are retained.
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
    let cfg=MergeConfig::default();
    ensure!(cfg.bands==LEVELS && cfg.gate==2.0 && cfg.mean_coarse==0 && cfg.select==SelectMode::SoftPower
        && cfg.admission==AdmissionMode::HardFloor && cfg.base==BaseBand::Mean
        && cfg.fallback==Fallback::Mean && cfg.hull==Hull::InputRange
        && cfg.significance_scale==0.0,"matched complete defaults changed");
    let domain=PyramidDomain::cropped(full,crop)?;
    let sizes=level_sizes(crop.width,crop.height,LEVELS);
    let baseline_level_sizes=sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>();
    ensure!(baseline_level_sizes==vec![[128,128],[64,64],[32,32],[16,16],[8,8]],
        "actual production baseline geometry changed; requested cap7 reaches four detail bands");
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("complete-cfa-periodic-generated",&entries),
        strategy:"fixed identity only".into(),heldout_px:None,cycle_floor_px:None,reference:0,
        note:"complete periodic generated operator; not full-product quality".into(),
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
    let mut min_weight=[[f32::INFINITY;3];LEVELS];let mut max_weight=[[0.0f32;3];LEVELS];
    let mut positive=[[0usize;3];LEVELS];let mut own_positive=[[[0usize;4];3];LEVELS];
    let mut own_suppressed=[[[0usize;4];3];LEVELS];
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
        for level in 0..LEVELS {for d in 0..3 {
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
                    kernels::soft_weight((e-floor).max(0.0),floor,cfg.exponent_at(level,LEVELS))>0.0
                }).collect::<Vec<_>>();
                own_positive[level][d][c]+=live.iter().filter(|&&v|v).count();
                own_live.push(live);
            }}
            for (j,((&i,&e),&v)) in pos.iter().zip(&energy).zip(&floor).enumerate() {
                ensure!(e.is_finite() && v.is_finite(),"nonfinite supported evidence");
                let floor=cfg.gate*v;
                let weight=kernels::soft_weight((e-floor).max(0.0),floor,cfg.exponent_at(level,LEVELS));
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
        let values=inverse_complete(p,w,h)?;
        Ok(values.iter().enumerate().map(|(i,v)|v.re.clamp(low[c][i],high[c][i])).collect())
    }).collect::<Result<Vec<Vec<f32>>>>()?;
    let rgb=|planes:&[Vec<f32>]|camera_rgb(planes,w,h,frames[0].levels,wb);
    let baseline_rgb=rgb(&baseline_planes4)?;let candidate_rgb=rgb(&candidate_planes4)?;
    Ok(Comparison{baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,native_width:2*w,native_height:2*h,
        baseline_level_sizes,baseline_averaged_fraction,candidate_fallback_fraction,candidate_weight_summary,
        known4_original_exact:true,identity_guide_original_exact:true,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/complete-cfa-wavelet/independent-controls.rs"));
}
