// Generated-only colour projection. One fixed acceptance heuristic, no RAW
// renderer or new noise estimator. The target shares source noise, so the
// 2-sigma scale is NOT a calibrated residual probability or RGB covariance.
use super::*;
use sha2::{Digest, Sha256};
use strehl_core::align::Similarity;
use phase_packed_rgb::{camera_rgb, gather_patch, CfaPatch};

pub(crate) const MODE: &str = "green-match-2sigma-mean";
// Complete A7C II active quad area; generated entry points retain their own
// much smaller source bounds. This changes size admission, not arithmetic.
pub(crate) const MAX_QUADS: usize = 3516 * 2344;

pub(crate) struct AcceptanceEvidence {
    pub accepted_quads: usize,
    pub mask_sha256: String,
}

pub(crate) struct FrameEvidence {
    pub source_index: usize,
    pub source_sha256: String,
    pub guide_sha256: String,
    pub variance_sha256: String,
    pub gathered12_sha256: String,
    pub acceptance_mask_sha256: String,
    pub accepted_quads: usize,
    pub known4_equal: bool,
}

pub(crate) struct Comparison {
    pub baseline_planes4: Vec<Vec<f32>>,
    pub baseline_averaged_fraction: Vec<f64>,
    pub baseline_rgb: Vec<f32>,
    pub candidate_rgb: Vec<f32>,
    pub native_width: usize,
    pub native_height: usize,
    pub target_green: Vec<f32>,
    pub acceptance_counts: Vec<u32>,
    pub fallback_quads: usize,
    pub accepted_samples: usize,
    pub known4_equal: bool,
    pub source_order: Vec<usize>,
    pub frames: Vec<FrameEvidence>,
}

fn digest(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn hash16(values: &[u16]) -> String {
    let mut h = Sha256::new();
    for v in values { h.update(v.to_le_bytes()); }
    digest(h)
}
fn hash32(values: &[f32]) -> String {
    let mut h = Sha256::new();
    for v in values { h.update(v.to_bits().to_le_bytes()); }
    digest(h)
}
fn hash_planes(planes: &[Vec<f32>]) -> String {
    let mut h = Sha256::new();
    for p in planes { for v in p { h.update(v.to_bits().to_le_bytes()); } }
    digest(h)
}

/// Exactly one acceptance decision per quad, shared by its four RGB tuples.
/// Values are black-subtracted source DN. No channel rescaling, clipping,
/// brightness repair, nearest-source fallback, or index tie-breaking occurs.
pub(crate) fn apply_acceptance(
    gathered12: &[Vec<f32>], source_green: &[f32], variance: &[f32], target: &[f32],
    sums: &mut [Vec<f32>], counts: &mut [u32],
) -> Result<AcceptanceEvidence> {
    let n = target.len();
    ensure!(n > 0 && n <= MAX_QUADS && source_green.len() == n && variance.len() == n
        && counts.len() == n && gathered12.len() == 12 && sums.len() == 12
        && gathered12.iter().chain(sums.iter()).all(|p| p.len() == n),
        "green-match acceptance geometry");
    let mut mask = Sha256::new();
    let mut accepted_quads = 0;
    for i in 0..n {
        let (l, t, v) = (source_green[i], target[i], variance[i]);
        ensure!(l.is_finite() && t.is_finite() && v.is_finite() && v >= 0.0,
            "green-match nonfinite guide/target or invalid injected variance");
        let delta = l - t;
        let squared = delta * delta;
        let threshold = 4.0 * v;
        ensure!(squared.is_finite() && threshold.is_finite(), "green-match acceptance overflow");
        let accepted = squared <= threshold;
        mask.update([u8::from(accepted)]);
        for c in 0..12 {
            ensure!(gathered12[c][i].is_finite() && sums[c][i].is_finite(),
                "green-match nonfinite source/sum");
            if accepted {
                sums[c][i] += gathered12[c][i];
                ensure!(sums[c][i].is_finite(), "green-match sum overflow");
            }
        }
        if accepted {
            counts[i] = counts[i].checked_add(1).context("green-match count overflow")?;
            accepted_quads += 1;
        }
    }
    Ok(AcceptanceEvidence { accepted_quads, mask_sha256: digest(mask) })
}

/// Source tuples use the existing twelve-plane camera-RGB reconstruction.
/// The same held developer can consume this camera-linear output. Unsupported
/// quads copy the original baseline RGB bits at all four native sites.
pub(crate) fn finish_projection(
    sums: &[Vec<f32>], counts: &[u32], baseline_rgb: &[f32],
    width: usize, height: usize, levels: Levels, wb: [f32; 4],
) -> Result<Vec<f32>> {
    let n = width.checked_mul(height).context("green-match output size overflow")?;
    ensure!(n > 0 && n <= MAX_QUADS && counts.len() == n && sums.len() == 12
        && sums.iter().all(|p| p.len() == n) && baseline_rgb.len() == 12 * n
        && baseline_rgb.iter().all(|v| v.is_finite()), "green-match output geometry/finite");
    let mut means = sums.to_vec();
    for p in &mut means { for (i, v) in p.iter_mut().enumerate() {
        ensure!(v.is_finite(), "green-match nonfinite accumulated value");
        if counts[i] > 0 { *v /= counts[i] as f32; } else { *v = 0.0; }
    }}
    let mut rgb = camera_rgb(&means, width, height, levels, wb)?;
    for y in 0..height { for x in 0..width {
        if counts[y * width + x] == 0 {
            for dy in 0..2 { for dx in 0..2 {
                let j = ((2 * y + dy) * (2 * width) + 2 * x + dx) * 3;
                rgb[j..j + 3].copy_from_slice(&baseline_rgb[j..j + 3]);
            }}
        }
    }}
    ensure!(rgb.iter().all(|v| v.is_finite()), "green-match nonfinite RGB");
    Ok(rgb)
}

/// The actual four-plane baseline always folds in canonical source order.
/// Only the colour-replay order is reversed by the control switch. Storage
/// retains original u16 fixtures, one source gather, and streaming sums/counts;
/// there is no collection of aligned frames.
pub(crate) fn compare_generated(
    frames: &[Frame], transforms: &[Similarity], crop: align_cmd::CropRect,
    noise: &NoiseModel, cfg: MergeConfig, reverse_sources: bool,
) -> Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len() <= 32 && frames.len() == transforms.len(),
        "green-match bounded generated frame count");
    let full = frames[0].geometry();
    ensure!(full.width <= 512 && full.height <= 512 && frames.iter().all(|f|
        f.geometry() == full && f.levels == frames[0].levels && !f.path.exists()),
        "green-match accepts generated bounded frames only");
    ensure!(frames.iter().all(|f| f.wb_coeffs[..3] == frames[0].wb_coeffs[..3]),
        "green-match requires fixed WB");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded,
        "green-match requires actual rounded fullres/probe route");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .is_ok_and(|v| v.eq_ignore_ascii_case("directional")), "green-match requires Malvar");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(), "green-match excludes local placement");
    #[cfg(feature = "native-correction-variance")]
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()
        == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "green-match requires fine-support candidate off");
    let domain = PyramidDomain::cropped(full, crop)?;
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    let n = crop.width * crop.height;
    let entries = frames.iter().map(|f|
        (f.path.to_string_lossy(), f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map = WarpMap::new(strehl_core::warpmap::Provenance {
        stack: StackIdentity::from_entries("green-match-generated", &entries),
        strategy: "supplied independent truth geometry".into(), heldout_px: None,
        cycle_floor_px: None, reference: 0,
        note: "bounded generated colour projection; no fitted geometry".into(),
    }, full, Resampler::CatmullRom, transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a [Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self) -> usize { self.0.len() }
        fn decode(&self, index: usize) -> Result<Frame> { Ok(self.0[index].clone()) }
    }
    let source = Source(frames);
    let mut baseline = BandWorker::new(domain, cfg);
    let mut evidence = Vec::new();
    for (index, frame) in frames.iter().enumerate() {
        let source_sha256 = hash16(&frame.data);
        ensure!(baseline.fold(&source, index, frame.levels, noise, Some(&map), None)?,
            "green-match baseline frame refused");
        ensure!(source_sha256 == hash16(&frame.data), "green-match original CFA changed");
        evidence.push(FrameEvidence {
            source_index: index, source_sha256, guide_sha256: hash32(&baseline.luma),
            variance_sha256: hash32(&baseline.var), gathered12_sha256: String::new(),
            acceptance_mask_sha256: String::new(), accepted_quads: 0, known4_equal: false,
        });
    }
    let baseline_averaged_fraction = baseline.merge.averaged_fraction();
    let baseline_planes4 = baseline.merge.finish(&mut Workspace::new(&sizes));
    let target_green = baseline_planes4[1].iter().zip(&baseline_planes4[2])
        .map(|(g1, g2)| 0.5 * (g1 + g2)).collect::<Vec<_>>();
    let baseline_rgb = camera_rgb(&baseline_planes4, crop.width, crop.height,
        frames[0].levels, frames[0].wb_coeffs)?;
    let source_order = if reverse_sources { (0..frames.len()).rev().collect::<Vec<_>>() }
        else { (0..frames.len()).collect::<Vec<_>>() };
    let mut sums = vec![vec![0.0; n]; 12];
    let mut counts = vec![0u32; n];
    // Reuse source scratch after finishing the baseline. No second merge is
    // run: this is its exact load_frame + luma_variance path without a probe.
    for &index in &source_order {
        let frame = &frames[index];
        ensure!(load_frame(&source, index, domain, frame.levels, Some(&map), None,
            &mut baseline.warp, None, &mut baseline.planes, &mut baseline.luma)?,
            "green-match replay frame refused");
        luma_variance(&baseline.luma, noise, &mut baseline.var);
        ensure!(hash32(&baseline.luma) == evidence[index].guide_sha256
            && hash32(&baseline.var) == evidence[index].variance_sha256,
            "green-match replay guide/variance differs from actual baseline");
        let packed = gather_patch(&CfaPatch::from_frame(frame), transforms[index], full, crop, None)?;
        ensure!((0..4).all(|c| packed[c].iter().zip(&baseline.planes[c])
            .all(|(a, b)| a.to_bits() == b.to_bits())),
            "green-match known four source slots differ from actual gather");
        let accepted = apply_acceptance(&packed, &baseline.luma, &baseline.var,
            &target_green, &mut sums, &mut counts)?;
        evidence[index].gathered12_sha256 = hash_planes(&packed);
        evidence[index].acceptance_mask_sha256 = accepted.mask_sha256;
        evidence[index].accepted_quads = accepted.accepted_quads;
        evidence[index].known4_equal = true;
        ensure!(hash16(&frame.data) == evidence[index].source_sha256,
            "green-match original CFA changed during replay");
    }
    let candidate_rgb = finish_projection(&sums, &counts, &baseline_rgb,
        crop.width, crop.height, frames[0].levels, frames[0].wb_coeffs)?;
    let fallback_quads = counts.iter().filter(|&&v| v == 0).count();
    let accepted_samples = counts.iter().map(|&v| v as usize).sum();
    Ok(Comparison { baseline_planes4, baseline_averaged_fraction, baseline_rgb, candidate_rgb,
        native_width: 2 * crop.width, native_height: 2 * crop.height, target_green,
        acceptance_counts: counts, fallback_quads, accepted_samples, known4_equal: true,
        source_order, frames: evidence })
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/green-match-rgb/independent-controls.rs"));
}

mod full_stack {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/green-match-rgb/full-stack.rs"));
}
