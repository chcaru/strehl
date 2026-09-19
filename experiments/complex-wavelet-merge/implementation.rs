// Test-only, identity-only, one-level complex-wavelet operator screen.
// Analysis/synthesis and the H/D/V donor vote are adapted from MIT focus-stack
// (c) 2019 Petteri Aimonen; full notice is in adjacent licence.txt.
// Pinned task_wavelet_templates.hh SHA256:
// 98018f5f4ec3e5c74a6107f418a7a6a006dfa31fbc97fc71bea699995a6fc852
// Pinned task_merge.cc SHA256:
// eee52b9269b55eb2158dff2b66fbb7831abaea5a2b0933eb0c85ed10b190957d
// Neither the comparator's 8-bit/PCA development nor its multilevel/batched
// full workflow is reproduced. Hard-max + vote is only an explicit control.
use super::*;
use sha2::{Digest, Sha256};
use strehl_core::align::Similarity;
use strehl_core::pyramid::{correction_variance_diagnostic as kernels, AdmissionMode,
    BaseBand, Fallback, Hull, LevelSize, SelectMode};
use phase_packed_rgb::camera_rgb;

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct Complex { pub re: f32, pub im: f32 }
impl Complex {
    fn squared(self) -> f32 { self.re * self.re + self.im * self.im }
    fn finite(self) -> bool { self.re.is_finite() && self.im.is_finite() }
}
pub(crate) const LOW: [Complex; 6] = [
    Complex { re: -0.0662912607, im: -0.0855816496 },
    Complex { re:  0.1104854346, im: -0.0855816496 },
    Complex { re:  0.6629126074, im:  0.1711632992 },
    Complex { re:  0.6629126074, im:  0.1711632992 },
    Complex { re:  0.1104854346, im: -0.0855816496 },
    Complex { re: -0.0662912607, im: -0.0855816496 },
];
pub(crate) fn analysis_taps(high: bool) -> [Complex; 6] {
    if !high { return LOW; }
    std::array::from_fn(|j| {
        let sign = if j % 2 == 0 { 1.0 } else { -1.0 };
        Complex { re: sign * LOW[j].re, im: -sign * LOW[j].im }
    })
}
fn dimensions(w: usize, h: usize, n: usize) -> Result<()> {
    ensure!(w >= 6 && h >= 6 && w % 2 == 0 && h % 2 == 0
        && w.checked_mul(h) == Some(n) && n <= 512 * 512,
        "complex one-level operator requires bounded even dimensions >=6");
    Ok(())
}
fn wrap(pos: isize, length: usize) -> usize { pos.rem_euclid(length as isize) as usize }
fn location(line: usize, pos: usize, width: usize, vertical: bool) -> usize {
    if vertical { pos * width + line } else { line * width + pos }
}

fn analysis_1d(src: &[Complex], w: usize, h: usize, vertical: bool) -> Vec<Complex> {
    let (count, length) = if vertical { (w, h) } else { (h, w) };
    let high = analysis_taps(true);
    let mut dst = vec![Complex::default(); src.len()];
    for line in 0..count { for y in (0..length).step_by(2) {
        let (mut lo, mut hi) = (Complex::default(), Complex::default());
        for j in 0..6 {
            let pos = wrap(y as isize + j as isize - 3, length);
            let value = src[location(line, pos, w, vertical)];
            lo.re += value.re * LOW[j].re - value.im * LOW[j].im;
            lo.im += value.im * LOW[j].re + value.re * LOW[j].im;
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
    let mut dst = vec![Complex::default(); src.len()];
    for line in 0..count { for y in 0..length {
        let mut value = Complex::default();
        for j in ((y + 3) % 2..6).step_by(2) {
            let pos = wrap((y as isize - j as isize + 3) / 2, length / 2);
            let lo = src[location(line, pos, w, vertical)];
            let hi = src[location(line, pos + length / 2, w, vertical)];
            // Preserve the source CPU accumulation order and conjugation.
            value.re += lo.re * LOW[j].re + hi.re * high[j].re;
            value.re += lo.im * LOW[j].im + hi.im * high[j].im;
            value.im += lo.im * LOW[j].re + hi.im * high[j].re;
            value.im -= lo.re * LOW[j].im + hi.re * high[j].im;
        }
        dst[location(line, y, w, vertical)] = value;
    }}
    dst
}
pub(crate) fn transform_one(input: &[Complex], width: usize, height: usize) -> Result<Vec<Complex>> {
    dimensions(width, height, input.len())?;
    ensure!(input.iter().all(|v| v.finite()), "nonfinite complex input");
    let vertical = analysis_1d(input, width, height, true);
    let result = analysis_1d(&vertical, width, height, false);
    ensure!(result.iter().all(|v| v.finite()), "nonfinite complex analysis");
    Ok(result)
}
pub(crate) fn forward_real(input: &[f32], width: usize, height: usize) -> Result<Vec<Complex>> {
    let input = input.iter().map(|&re| Complex { re, im: 0.0 }).collect::<Vec<_>>();
    transform_one(&input, width, height)
}
pub(crate) fn inverse_one(input: &[Complex], width: usize, height: usize) -> Result<Vec<Complex>> {
    dimensions(width, height, input.len())?;
    ensure!(input.iter().all(|v| v.finite()), "nonfinite synthesis input");
    let vertical = synthesis_1d(input, width, height, true);
    let result = synthesis_1d(&vertical, width, height, false);
    ensure!(result.iter().all(|v| v.finite()), "nonfinite complex synthesis");
    Ok(result)
}

/// Expected squared COMPLEX coefficient from independent real guide samples.
/// One-level identity only: sum |h_y*h_x|² V_input, in DN². This is propagation
/// of the injected authority, not a new fitted sensor model. It is invalid for
/// fractional gathers without their covariance, which this adapter excludes.
pub(crate) fn coefficient_variance(input: &[f32], w: usize, h: usize) -> Result<Vec<f32>> {
    dimensions(w, h, input.len())?;
    ensure!(input.iter().all(|v| v.is_finite() && *v >= 0.0), "invalid injected variance");
    let mut out = vec![0.0; input.len()];
    for by in 0..2 { for bx in 0..2 {
        let (hy, hx) = (analysis_taps(by != 0), analysis_taps(bx != 0));
        for y in 0..h/2 { for x in 0..w/2 {
            let mut variance = 0.0;
            for jy in 0..6 { for jx in 0..6 {
                let coefficient = Complex {
                    re: hy[jy].re * hx[jx].re - hy[jy].im * hx[jx].im,
                    im: hy[jy].im * hx[jx].re + hy[jy].re * hx[jx].im,
                };
                let sy = wrap((2*y + jy) as isize - 3, h);
                let sx = wrap((2*x + jx) as isize - 3, w);
                variance += coefficient.squared() * input[sy*w + sx];
            }}
            out[(by*h/2+y)*w + bx*w/2+x] = variance;
        }}
    }}
    ensure!(out.iter().all(|v| v.is_finite()), "propagated variance overflow");
    Ok(out)
}

/// Exact same-scale H/D/V two-of-three vote from the MIT comparator. All
/// different donors remain different; LL is untouched. This is control only.
pub(crate) fn direction_vote(indices: &mut [u16], w: usize, h: usize) -> Result<usize> {
    dimensions(w, h, indices.len())?;
    let mut changed = 0;
    for y in 0..h/2 { for x in 0..w/2 {
        let p = [y*w+w/2+x, (h/2+y)*w+w/2+x, (h/2+y)*w+x];
        let v = p.map(|i| indices[i]);
        let target = if v[0] == v[1] && v[1] == v[2] { None }
            else if v[1] == v[2] { Some((p[0], v[1])) }
            else if v[0] == v[2] { Some((p[1], v[0])) }
            else if v[0] == v[1] { Some((p[2], v[0])) } else { None };
        if let Some((i, value)) = target { indices[i] = value; changed += 1; }
    }}
    Ok(changed)
}

pub(crate) struct FrameEvidence {
    pub source_sha256: String,
    pub guide_sha256: String,
    pub variance_sha256: String,
    pub coefficient_variance_sha256: String,
    pub known4_original_exact: bool,
    pub identity_guide_original_exact: bool,
}
pub(crate) struct DirectionWeightSummary {
    pub min_weight: f32,
    pub max_weight: f32,
    pub positive_source_coefficients: usize,
    pub multi_source_coefficients: usize,
    pub total_coefficients: usize,
}
pub(crate) struct Comparison {
    pub baseline_planes4: Vec<Vec<f32>>,
    pub candidate_planes4: Vec<Vec<f32>>,
    pub control_planes4: Vec<Vec<f32>>,
    pub baseline_rgb: Vec<f32>,
    pub candidate_rgb: Vec<f32>,
    pub control_rgb: Vec<f32>,
    pub native_width: usize,
    pub native_height: usize,
    pub baseline_averaged_fraction: Vec<f64>,
    pub candidate_fallback_fraction: [f64; 3],
    pub candidate_weight_summary: [DirectionWeightSummary; 3],
    pub known4_original_exact: bool,
    pub identity_guide_original_exact: bool,
    pub control_votes_changed: usize,
    pub frames: Vec<FrameEvidence>,
}
fn hash16(values: &[u16]) -> String {
    let mut h = Sha256::new(); for v in values { h.update(v.to_le_bytes()); }
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn hash32(values: &[f32]) -> String {
    let mut h = Sha256::new(); for v in values { h.update(v.to_bits().to_le_bytes()); }
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn original_equality(frame: &Frame, crop: align_cmd::CropRect, planes: &[Vec<f32>], guide: &[f32]) -> Result<()> {
    for (c, (dx, dy)) in [(0,0),(1,0),(0,1),(1,1)].into_iter().enumerate() {
        for y in 0..crop.height { for x in 0..crop.width {
            let original = frame.active_row(2*(crop.y+y)+dy)[2*(crop.x+x)+dx] as f32 - frame.levels.black;
            ensure!(planes[c][y*crop.width+x].to_bits() == original.to_bits(),
                "identity gather is not original CFA at channel {c}, {x},{y}");
        }}
    }
    for y in 0..crop.height { for x in 0..crop.width {
        let g1 = frame.active_row(2*(crop.y+y))[2*(crop.x+x)+1] as f32 - frame.levels.black;
        let g2 = frame.active_row(2*(crop.y+y)+1)[2*(crop.x+x)] as f32 - frame.levels.black;
        ensure!(guide[y*crop.width+x].to_bits() == (0.5*(g1+g2)).to_bits(),
            "identity guide is not original green-pair mean at {x},{y}");
    }}
    Ok(())
}
fn band_positions(w: usize, h: usize, orientation: usize) -> impl Iterator<Item=usize> {
    let (bx, by) = [(1,0),(1,1),(0,1)][orientation];
    (0..h/2).flat_map(move |y| (0..w/2).map(move |x| (by*h/2+y)*w+bx*w/2+x))
}

/// Explicitly fixed identity geometry and one decomposition level. Baseline
/// is the actual BandWorker with bands=1, not the seven-band product. A second
/// streamed generated-source pass retrieves voted control coefficients; no
/// aligned-frame or coefficient volume is retained.
pub(crate) fn compare_generated(frames: &[Frame], crop: align_cmd::CropRect,
    noise: &NoiseModel) -> Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len() <= 32, "bounded generated frame count required");
    let full = frames[0].geometry();
    ensure!(full.width <= 512 && full.height <= 512 && frames.iter().all(|f|
        f.geometry() == full && f.levels == frames[0].levels && !f.path.exists()
        && f.wb_coeffs[..3] == frames[0].wb_coeffs[..3]), "generated identity fixture scope differs");
    dimensions(crop.width, crop.height, crop.width*crop.height)?;
    // Below-black or clipped samples defeat the independent linear-noise
    // premise. The intended generated fixtures have deliberate headroom.
    for frame in frames { for y in 0..frame.active.height {
        ensure!(frame.active_row(y).iter().all(|&v| (v as f32) > frame.levels.black
            && (v as f32) < frame.levels.white), "identity noise unit screen requires unclipped samples");
    }}
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded,
        "actual rounded fullres/probe route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(), "local placement excluded");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .is_ok_and(|v|v.eq_ignore_ascii_case("directional")), "Malvar required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()
        == strehl_core::pyramid::fine_support_candidate::Mode::Off, "fine support must be off");
    let cfg = MergeConfig { bands: 1, ..MergeConfig::default() };
    ensure!(cfg.gate == 2.0 && cfg.exponent_at(0,1) == 2.0 && cfg.mean_coarse == 0
        && cfg.select == SelectMode::SoftPower && cfg.admission == AdmissionMode::HardFloor
        && cfg.base == BaseBand::Mean && cfg.fallback == Fallback::Mean
        && cfg.hull == Hull::InputRange && cfg.significance_scale == 0.0,
        "matched one-level default constants changed");
    let domain = PyramidDomain::cropped(full, crop)?;
    let sizes = level_sizes(crop.width,crop.height,1);
    ensure!(sizes.len() == 2, "matched one-level baseline geometry");
    let entries = frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map = WarpMap::new(strehl_core::warpmap::Provenance {
        stack: StackIdentity::from_entries("complex-identity-generated",&entries),
        strategy:"fixed identity only".into(),heldout_px:None,cycle_floor_px:None,reference:0,
        note:"one-level generated operator; not full-product quality".into(),
    },full,Resampler::CatmullRom,vec![FrameWarp::Placed(Similarity::IDENTITY);frames.len()]);
    struct Source<'a>(&'a[Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize {self.0.len()}
        fn decode(&self,index:usize)->Result<Frame> {Ok(self.0[index].clone())}
    }
    let source = Source(frames);
    let (w,h) = (crop.width,crop.height);
    let n = w*h;
    let mut baseline = BandWorker::new(domain,cfg);
    let mut sums = vec![vec![Complex::default();n];4];
    let mut means = vec![vec![Complex::default();n];4];
    let mut den = vec![0.0f32;n];
    let mut positive_counts = vec![0u16;n];
    let mut min_weight = [f32::INFINITY;3];
    let mut max_weight = [0.0f32;3];
    let mut positive_source_coefficients = [0usize;3];
    let mut max_energy = vec![-1.0f32;n];
    let mut donors = vec![0u16;n];
    let mut low = vec![vec![f32::INFINITY;n];4];
    let mut high = vec![vec![f32::NEG_INFINITY;n];4];
    let mut evidence = Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let source_sha256 = hash16(&frame.data);
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?, "identity baseline refused frame");
        original_equality(frame,crop,&baseline.planes,&baseline.luma)?;
        let wave = baseline.planes.iter().map(|p|forward_real(p,w,h)).collect::<Result<Vec<_>>>()?;
        let guide = forward_real(&baseline.luma,w,h)?;
        let variance = coefficient_variance(&baseline.var,w,h)?;
        for i in 0..n {
            let energy = guide[i].squared();
            if energy > max_energy[i] { max_energy[i]=energy;donors[i]=index as u16; }
            for c in 0..4 {
                means[c][i].re += wave[c][i].re; means[c][i].im += wave[c][i].im;
                low[c][i] = low[c][i].min(baseline.planes[c][i]);
                high[c][i] = high[c][i].max(baseline.planes[c][i]);
            }
        }
        for orientation in 0..3 {
            let positions = band_positions(w,h,orientation).collect::<Vec<_>>();
            let size = LevelSize{width:w/2,height:h/2};
            let energy = positions.iter().map(|&i|guide[i].squared()).collect::<Vec<_>>();
            let floor = positions.iter().map(|&i|variance[i]).collect::<Vec<_>>();
            let energy = kernels::smooth(&energy,size);
            let floor = kernels::smooth(&floor,size);
            for ((&i,&e),&v) in positions.iter().zip(&energy).zip(&floor) {
                let floor = cfg.gate*v;
                let weight = kernels::soft_weight((e-floor).max(0.0),floor,cfg.exponent_at(0,1));
                ensure!(weight.is_finite() && weight>=0.0, "complex weight invalid");
                min_weight[orientation] = min_weight[orientation].min(weight);
                max_weight[orientation] = max_weight[orientation].max(weight);
                if weight > 0.0 {
                    positive_counts[i] += 1;
                    positive_source_coefficients[orientation] += 1;
                }
                den[i] += weight;
                for c in 0..4 {
                    sums[c][i].re += weight*wave[c][i].re;
                    sums[c][i].im += weight*wave[c][i].im;
                }
            }
        }
        ensure!(hash16(&frame.data)==source_sha256,"original generated CFA changed");
        evidence.push(FrameEvidence {source_sha256,guide_sha256:hash32(&baseline.luma),
            variance_sha256:hash32(&baseline.var),coefficient_variance_sha256:hash32(&variance),
            known4_original_exact:true,identity_guide_original_exact:true});
    }
    let baseline_averaged_fraction = baseline.merge.averaged_fraction();
    let baseline_planes4 = baseline.merge.finish(&mut Workspace::new(&sizes));
    let candidate_fallback_fraction = std::array::from_fn(|d|
        band_positions(w,h,d).filter(|&i|den[i]==0.0).count() as f64 / (n/4) as f64);
    let candidate_weight_summary = std::array::from_fn(|d| DirectionWeightSummary {
        min_weight:min_weight[d],max_weight:max_weight[d],
        positive_source_coefficients:positive_source_coefficients[d],
        multi_source_coefficients:band_positions(w,h,d).filter(|&i|positive_counts[i]>1).count(),
        total_coefficients:n/4,
    });
    for c in 0..4 { for i in 0..n {
        if den[i] > 0.0 {
            sums[c][i].re /= den[i]; sums[c][i].im /= den[i];
        } else {
            sums[c][i].re = means[c][i].re / frames.len() as f32;
            sums[c][i].im = means[c][i].im / frames.len() as f32;
        }
    }}
    drop(means);
    let control_votes_changed = direction_vote(&mut donors,w,h)?;
    let mut control = vec![vec![Complex::default();n];4];
    for (index,frame) in frames.iter().enumerate() {
        ensure!(load_frame(&source,index,domain,frame.levels,Some(&map),None,
            &mut baseline.warp,None,&mut baseline.planes,&mut baseline.luma)?,"control replay refused source");
        original_equality(frame,crop,&baseline.planes,&baseline.luma)?;
        ensure!(hash16(&frame.data)==evidence[index].source_sha256,"control source changed");
        for c in 0..4 {
            let wave = forward_real(&baseline.planes[c],w,h)?;
            for i in 0..n {if donors[i]==index as u16 {control[c][i]=wave[i];}}
        }
    }
    let reconstruct = |waves:&[Vec<Complex>]| -> Result<Vec<Vec<f32>>> {
        waves.iter().enumerate().map(|(c,p)| {
            let values=inverse_one(p,w,h)?;
            // Same input-range guard as the matched baseline. It is not a new
            // gamut/colour repair and applies identically to candidate/control.
            Ok(values.iter().enumerate().map(|(i,v)|v.re.clamp(low[c][i],high[c][i])).collect())
        }).collect()
    };
    let candidate_planes4 = reconstruct(&sums)?;
    let control_planes4 = reconstruct(&control)?;
    let rgb = |planes:&[Vec<f32>]|camera_rgb(planes,w,h,frames[0].levels,frames[0].wb_coeffs);
    let baseline_rgb=rgb(&baseline_planes4)?;
    let candidate_rgb=rgb(&candidate_planes4)?;
    let control_rgb=rgb(&control_planes4)?;
    Ok(Comparison {baseline_planes4,candidate_planes4,control_planes4,baseline_rgb,candidate_rgb,control_rgb,
        native_width:2*w,native_height:2*h,baseline_averaged_fraction,candidate_fallback_fraction,
        candidate_weight_summary,known4_original_exact:true,identity_guide_original_exact:true,
        control_votes_changed,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/complex-wavelet-merge/independent-controls.rs"));
}
