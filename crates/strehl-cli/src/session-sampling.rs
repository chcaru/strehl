//! Direct same-color CFA sampling for opt-in sessions.
//!
//! Coordinates are in the alignment guide's green-luma gauge. Guide (x,y)
//! represents active sensor (2*x+0.5,2*y+0.5), not the red photosite. A CFA site
//! has guide coordinate (x+dx/2-0.25,y+dy/2-0.25); after the centered pull and
//! optional source-frame optical composition, subtract that same site offset.
//! Originals remain u16. Only one consuming frame's signed f32 planes exist,
//! with no demosaic, quantization, aligned volume, or disk pixel intermediates.
use anyhow::{Result, ensure};
use rayon::prelude::*;
use strehl_core::CfaPlane;
use strehl_core::align::{PlaneRef, Resampler, Similarity};
use strehl_core::noise::Levels;
use strehl_core::optics::{OpticalProfile, cfa_site_channel};
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::pyramid::{LevelSize, Pyramid, Workspace, level_sizes};

/// Output rectangle in the FULL guide grid. Cropping never recenters a warp.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SamplingDomain {
    pub full: PlaneGeometry,
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}
impl SamplingDomain {
    pub fn full(full: PlaneGeometry) -> Self {
        Self {
            full,
            x: 0,
            y: 0,
            width: full.width,
            height: full.height,
        }
    }
    pub fn validate(self) -> Result<()> {
        ensure!(
            self.full.width > 0 && self.full.height > 0,
            "empty full sampling geometry"
        );
        ensure!(
            self.width > 0 && self.height > 0,
            "empty sampling rectangle"
        );
        ensure!(
            self.x
                .checked_add(self.width)
                .is_some_and(|n| n <= self.full.width)
                && self
                    .y
                    .checked_add(self.height)
                    .is_some_and(|n| n <= self.full.height),
            "sampling rectangle leaves full geometry"
        );
        ensure!(
            self.full
                .width
                .checked_mul(self.full.height)
                .and_then(|n| n.checked_mul(8))
                .is_some()
                && self
                    .width
                    .checked_mul(self.height)
                    .and_then(|n| n.checked_mul(19))
                    .is_some(),
            "sampling allocation overflows"
        );
        Ok(())
    }
    pub fn pixels(self) -> usize {
        self.width * self.height
    }
}

/// Allocation-free checked pixel-buffer estimate for NativeSampler.
pub fn sampling_bytes(domain: SamplingDomain) -> Result<usize> {
    domain.validate()?;
    checked_bytes(&[(domain.full.pixels(), 5), (domain.pixels(), 19)])
}

fn checked_bytes(terms: &[(usize, usize)]) -> Result<usize> {
    let bytes = terms.iter().try_fold(0usize, |total, &(n, width)| {
        n.checked_mul(width)
            .and_then(|term| total.checked_add(term))
            .ok_or_else(|| anyhow::anyhow!("sampling workspace byte count overflows"))
    })?;
    ensure!(
        bytes <= isize::MAX as usize,
        "sampling workspace exceeds addressable size"
    );
    Ok(bytes)
}

/// Checked transient peak for the full-domain operator probe. Includes numeric
/// and mask buffers, but excludes Vec headers, allocator/thread overhead.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProbeMemoryEstimate {
    pub sampler_bytes: usize,
    pub original_cfa_bytes: usize,
    pub pyramid_workspace_bytes: usize,
    pub mask_peak_bytes: usize,
    pub green_bytes: usize,
    pub statistics_bytes: usize,
    pub peak_bytes: usize,
}
impl ProbeMemoryEstimate {
    pub fn estimate(domain: SamplingDomain, bands: usize) -> Result<Self> {
        let sampler_bytes = sampling_bytes(domain)?;
        let sizes = level_sizes(domain.width, domain.height, bands);
        let n = domain.pixels();
        let p = sizes
            .iter()
            .try_fold(0usize, |sum, size| sum.checked_add(size.pixels()))
            .ok_or_else(|| anyhow::anyhow!("probe pyramid sample count overflows"))?;
        let original_cfa_bytes = checked_bytes(&[(domain.full.pixels(), 8)])?;
        let pyramid_workspace_bytes = checked_bytes(&[(p, 4), (n, 8), (domain.width, 4)])?;
        // Gaussian and Laplacian masks coexist during dependency propagation.
        let mask_peak_bytes = checked_bytes(&[(p, 2)])?;
        let green_bytes = checked_bytes(&[(n, 4)])?;
        let statistics_bytes = checked_bytes(&[(
            sizes.len(),
            5 * 8 + std::mem::size_of::<usize>() + 6 * 4 + std::mem::size_of::<LevelSize>(),
        )])?;
        let peak_bytes = checked_bytes(&[
            (sampler_bytes, 1),
            (original_cfa_bytes, 1),
            (pyramid_workspace_bytes, 1),
            (mask_peak_bytes, 1),
            (green_bytes, 1),
            (statistics_bytes, 1),
        ])?;
        Ok(Self {
            sampler_bytes,
            original_cfa_bytes,
            pyramid_workspace_bytes,
            mask_peak_bytes,
            green_bytes,
            statistics_bytes,
            peak_bytes,
        })
    }
}

/// CFA order is R,G1,B,G2, matching CfaPlane::ALL. Values are signed DN.
///
/// Unsupported entries are zero sentinels, NOT observations. Consumers must
/// propagate support through every filter footprint before admitting a result.
/// Clipping is on original raw codes, including negative-weight interpolation
/// taps; it is not inferred from the interpolated value.
#[derive(Debug)]
pub struct SampledCfa {
    pub planes: [Vec<f32>; 4],
    pub coverage: Vec<bool>,
    pub clipped: Vec<bool>,
    pub support: Vec<bool>,
}

/// Reuses one source-plane scratch and four output planes. No source-frame list.
pub struct NativeSampler {
    domain: SamplingDomain,
    source_plane: Vec<f32>,
    source_clipped: Vec<bool>,
    output: SampledCfa,
}
impl NativeSampler {
    pub fn new(domain: SamplingDomain) -> Result<Self> {
        sampling_bytes(domain)?;
        Ok(Self {
            domain,
            source_plane: vec![0.0; domain.full.pixels()],
            source_clipped: vec![false; domain.full.pixels()],
            output: SampledCfa {
                planes: std::array::from_fn(|_| vec![0.0; domain.pixels()]),
                coverage: vec![false; domain.pixels()],
                clipped: vec![false; domain.pixels()],
                support: vec![false; domain.pixels()],
            },
        })
    }
    pub fn domain(&self) -> SamplingDomain {
        self.domain
    }
    /// Pixel-buffer allocation only, excluding Vec headers and allocator costs.
    pub fn working_bytes(&self) -> usize {
        self.domain.full.pixels() * 5 + self.domain.pixels() * 19
    }
    pub fn output(&self) -> &SampledCfa {
        &self.output
    }

    /// Pull samples from a source whose active RGGB geometry equals full.
    /// QuadSource rows retain the decoder's active origin; buffer padding is
    /// never inspected. Optical coordinates are active-area centered, so any
    /// absolute sensor origin cancels identically between point and center.
    pub fn gather<S: QuadSource + ?Sized>(
        &mut self,
        source: &S,
        levels: Levels,
        placement: Similarity,
        profile: Option<&OpticalProfile>,
        resampler: Resampler,
    ) -> Result<&SampledCfa> {
        ensure!(
            source.geometry() == self.domain.full,
            "source geometry differs from full sampling grid"
        );
        ensure!(
            levels.black.is_finite()
                && levels.white.is_finite()
                && levels.white > levels.black
                && levels.white > 0.0
                && levels.white <= 65535.0,
            "invalid source black/white levels"
        );
        validate_placement(placement)?;
        self.output.coverage.fill(true);
        self.output.clipped.fill(false);
        self.output.support.fill(false);
        let geom = self.domain.full;
        let center = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
        for (ci, color) in CfaPlane::ALL.into_iter().enumerate() {
            let (dx, dy) = color.rggb_offset();
            let transform = OpticalProfile::compose(profile, cfa_site_channel(dx, dy), placement);
            validate_placement(transform)?;
            let mut any_clipped = false;
            for y in 0..geom.height {
                let (r0, r1) = source.quad_rows(y);
                let row = if dy == 0 { r0 } else { r1 };
                ensure!(row.len() >= 2 * geom.width, "short active CFA row");
                for x in 0..geom.width {
                    let raw = row[2 * x + dx];
                    let i = y * geom.width + x;
                    self.source_plane[i] = f32::from(raw) - levels.black;
                    self.source_clipped[i] = f32::from(raw) >= levels.white;
                    any_clipped |= self.source_clipped[i];
                }
            }
            let plane =
                PlaneRef::from_geometry(&self.source_plane, geom).expect("validated dimensions");
            let site = (dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25);
            let domain = self.domain;
            let source_clipped = &self.source_clipped;
            let SampledCfa {
                planes,
                coverage,
                clipped,
                ..
            } = &mut self.output;
            // Rows are independent; each sample retains exactly the serial
            // coordinate calculation and core interpolation arithmetic. No
            // caller-supplied QuadSource needs Sync: row access finished above.
            planes[ci]
                .par_chunks_mut(domain.width)
                .zip(coverage.par_chunks_mut(domain.width))
                .zip(clipped.par_chunks_mut(domain.width))
                .enumerate()
                .for_each(|(y, ((values, covered), clipped))| {
                    for (x, value) in values.iter_mut().enumerate() {
                        let (sx, sy) = transform.apply_at(
                            (domain.x + x) as f64 + site.0,
                            (domain.y + y) as f64 + site.1,
                            center.0,
                            center.1,
                        );
                        let (sx, sy) = (sx - site.0, sy - site.1);
                        if let Some(sample) = resampler.sample_checked(plane, sx, sy) {
                            *value = sample;
                            // A clip-free source plane cannot contain a clipped
                            // contributing tap. Otherwise retain the exact
                            // nonzero stencil check, including negative taps.
                            clipped[x] |= any_clipped
                                && footprint_clipped(source_clipped, geom, sx, sy, resampler);
                        } else {
                            *value = 0.0;
                            covered[x] = false;
                        }
                    }
                });
        }
        self.output
            .support
            .par_iter_mut()
            .zip(&self.output.coverage)
            .zip(&self.output.clipped)
            .for_each(|((support, &coverage), &clipped)| *support = coverage && !clipped);
        Ok(&self.output)
    }
}

fn validate_placement(t: Similarity) -> Result<()> {
    ensure!(
        [t.a.re, t.a.im, t.b.re, t.b.im]
            .into_iter()
            .all(f64::is_finite)
            && t.a.norm_sq().is_finite()
            && t.a.norm_sq() > 0.0,
        "nonfinite or singular sampling placement"
    );
    Ok(())
}

/// Enumerates the actual core sampler stencil, including its small-plane
/// fallback and endpoint phase. Values still come ONLY from sample_checked.
/// These weights mirror the owned core implementation solely to decide whether
/// a source tap participates. Tests compare the decision against impulse probes.
#[derive(Clone, Copy)]
struct AxisTaps {
    start: usize,
    len: usize,
    weights: [f32; 6],
}
fn effective_resampler(r: Resampler, g: PlaneGeometry) -> Resampler {
    match r {
        Resampler::Lanczos3 if g.width < 6 || g.height < 6 => {
            effective_resampler(Resampler::CatmullRom, g)
        }
        Resampler::CatmullRom | Resampler::ClampedCatmullRom | Resampler::Lanczos2
            if g.width < 4 || g.height < 4 =>
        {
            effective_resampler(Resampler::Bilinear, g)
        }
        Resampler::Bilinear if g.width < 2 || g.height < 2 => Resampler::Nearest,
        _ => r,
    }
}
fn axis_taps(x: f64, n: usize, r: Resampler) -> AxisTaps {
    let mut out = AxisTaps {
        start: 0,
        len: 1,
        weights: [0.0; 6],
    };
    if r == Resampler::Nearest {
        out.start = (x.round() as isize).clamp(0, n as isize - 1) as usize;
        out.weights[0] = 1.0;
        return out;
    }
    if r == Resampler::Bilinear {
        let x = x.clamp(0.0, (n - 1) as f64);
        out.start = (x.floor() as usize).min(n - 2);
        out.len = 2;
        let f = (x - out.start as f64) as f32;
        out.weights[0] = 1.0 - f;
        out.weights[1] = f;
        return out;
    }
    let radius = if r == Resampler::Lanczos3 { 3 } else { 2 };
    let x = x.clamp((radius - 1) as f64, (n - radius) as f64);
    let cell = (x.floor() as usize).min(n - radius - 1);
    let phase = x - cell as f64;
    out.start = cell - (radius - 1);
    out.len = 2 * radius;
    if matches!(r, Resampler::CatmullRom | Resampler::ClampedCatmullRom) {
        let f = phase as f32;
        let f2 = f * f;
        let f3 = f2 * f;
        out.weights[..4].copy_from_slice(&[
            -0.5 * f3 + f2 - 0.5 * f,
            1.5 * f3 - 2.5 * f2 + 1.0,
            -1.5 * f3 + 2.0 * f2 + 0.5 * f,
            0.5 * f3 - 0.5 * f2,
        ]);
    } else {
        let mut weights = [0.0f64; 6];
        let mut sum = 0.0;
        for (i, w) in weights.iter_mut().take(out.len).enumerate() {
            let t = phase - (i as f64 - (radius - 1) as f64);
            *w = sinc(t) * sinc(t / radius as f64);
            sum += *w;
        }
        let inv = 1.0 / sum;
        for (dst, src) in out.weights.iter_mut().zip(weights) {
            *dst = (src * inv) as f32;
        }
    }
    out
}
fn sinc(x: f64) -> f64 {
    if x.abs() < 1e-12 {
        1.0
    } else {
        let p = std::f64::consts::PI * x;
        p.sin() / p
    }
}
fn footprint_clipped(mask: &[bool], geom: PlaneGeometry, x: f64, y: f64, r: Resampler) -> bool {
    let r = effective_resampler(r, geom);
    let tx = axis_taps(x, geom.width, r);
    let ty = axis_taps(y, geom.height, r);
    let hull = r == Resampler::ClampedCatmullRom;
    for iy in 0..ty.len {
        for ix in 0..tx.len {
            // Do not multiply weights here: a product may underflow although
            // the separable sampler actually uses both nonzero factors.
            if (hull || (tx.weights[ix] != 0.0 && ty.weights[iy] != 0.0))
                && mask[(ty.start + iy) * geom.width + tx.start + ix]
            {
                return true;
            }
        }
    }
    false
}

/// Controls the deterministic operator probe, NOT the injected sensor model.
#[derive(Clone, Copy, Debug)]
pub struct ProbeConfig {
    pub bands: usize,
    pub realizations: usize,
    pub seed: u64,
    pub min_samples_per_band: usize,
}
impl Default for ProbeConfig {
    fn default() -> Self {
        Self {
            bands: 7,
            realizations: 4,
            seed: 0x5354_5248_4c43_4641,
            min_samples_per_band: 256,
        }
    }
}

#[derive(Clone, Debug)]
pub struct WarpBandTransfer {
    /// E[L_k(CFA)^2] / known original photosite variance, by R,G1,B,G2.
    pub cfa_beta: [Vec<f32>; 4],
    /// E[L_k((G1+G2)/2)^2] / (original photosite variance / 2).
    pub luma_beta: Vec<f32>,
    /// Observed maximum of the four CFA beta estimates, not a confidence bound.
    pub max_color_beta: Vec<f32>,
    pub samples_per_band: Vec<usize>,
    pub realizations: usize,
    pub seed: u64,
}

/// Probe the EXACT gather + Laplacian-pyramid operator using independent
/// original u16 Rademacher noise (8192 +/-32, black=8192). Known photosite
/// variance is 1024 DN^2; green luma variance before warping is 512 DN^2.
/// No fitted sensor noise, empirical renormalization, demosaic or u16 writeback.
///
/// This initial correctness path probes the requested full output domain and
/// can be costly. It measures a spatial-average transfer for stationary noise:
/// scalar beta does not exactly model spatially varying phase or shot noise.
/// Nonlinear clamped Catmull-Rom is refused, rather than assigned a false linear
/// variance transfer. Insufficient valid interior is an error, never identity.
pub fn measure_band_transfer(
    domain: SamplingDomain,
    placement: Similarity,
    profile: Option<&OpticalProfile>,
    resampler: Resampler,
    config: ProbeConfig,
) -> Result<WarpBandTransfer> {
    ProbeMemoryEstimate::estimate(domain, config.bands)?;
    ensure!(
        resampler != Resampler::ClampedCatmullRom,
        "nonlinear clamped Catmull-Rom has no content-independent noise transfer"
    );
    ensure!(
        (1..=128).contains(&config.realizations),
        "noise probe realizations must be 1..=128"
    );
    ensure!(
        config.min_samples_per_band > 0,
        "noise probe requires positive minimum sample count"
    );
    let sizes = level_sizes(domain.width, domain.height, config.bands);
    let n = sizes.len();
    let mut sums: [Vec<f64>; 5] = std::array::from_fn(|_| vec![0.0; n]);
    let mut counts = vec![0usize; n];
    let mut source = ProbeSource::new(domain.full);
    let mut sampler = NativeSampler::new(domain)?;
    let mut pyramid = Pyramid::zeros(&sizes);
    let mut workspace = Workspace::new(&sizes);
    let mut green = vec![0.0; domain.pixels()];
    let mut masks = Vec::new();
    for realization in 0..config.realizations {
        source.fill(config.seed, realization);
        let sampled = sampler.gather(&source, PROBE_LEVELS, placement, profile, resampler)?;
        if realization == 0 {
            masks = band_support_masks(&sampled.support, &sizes);
            for (k, mask) in masks.iter().enumerate() {
                counts[k] = mask
                    .iter()
                    .filter(|&&v| v)
                    .count()
                    .checked_mul(config.realizations)
                    .ok_or_else(|| anyhow::anyhow!("noise probe sample count overflows"))?;
                ensure!(
                    counts[k] >= config.min_samples_per_band,
                    "noise probe band {k} has {} valid samples, needs {}",
                    counts[k],
                    config.min_samples_per_band
                );
            }
        }
        for (i, value) in green.iter_mut().enumerate() {
            *value = 0.5 * (sampled.planes[1][i] + sampled.planes[3][i]);
        }
        for (channel, sum) in sums.iter_mut().enumerate() {
            let plane = if channel < 4 {
                &sampled.planes[channel]
            } else {
                &green
            };
            pyramid.build(plane, &mut workspace);
            for k in 0..n {
                for (&value, &valid) in pyramid.level(k).iter().zip(&masks[k]) {
                    if valid {
                        sum[k] += f64::from(value).powi(2);
                    }
                }
            }
        }
    }
    let cfa_beta: [Vec<f32>; 4] = std::array::from_fn(|c| {
        (0..n)
            .map(|k| (sums[c][k] / (counts[k] as f64 * PROBE_VARIANCE)) as f32)
            .collect()
    });
    let luma_beta: Vec<f32> = (0..n)
        .map(|k| (sums[4][k] / (counts[k] as f64 * PROBE_VARIANCE * 0.5)) as f32)
        .collect();
    let max_color_beta = (0..n)
        .map(|k| cfa_beta.iter().map(|b| b[k]).fold(0.0, f32::max))
        .collect();
    for beta in cfa_beta.iter().chain(std::iter::once(&luma_beta)) {
        ensure!(
            beta.iter().all(|b| b.is_finite() && *b > 0.0),
            "nonpositive/nonfinite measured noise transfer"
        );
    }
    Ok(WarpBandTransfer {
        cfa_beta,
        luma_beta,
        max_color_beta,
        samples_per_band: counts,
        realizations: config.realizations,
        seed: config.seed,
    })
}

const PROBE_LEVELS: Levels = Levels {
    black: 8192.0,
    white: 65535.0,
};
const PROBE_VARIANCE: f64 = 32.0 * 32.0;
struct ProbeSource {
    geom: PlaneGeometry,
    data: Vec<u16>,
}
impl ProbeSource {
    fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            data: vec![0; geom.pixels() * 4],
        }
    }
    fn fill(&mut self, seed: u64, realization: usize) {
        let stream = splitmix(seed ^ (realization as u64).wrapping_mul(0xd134_2543_de82_ef95));
        // The stream is a pure function of realization and original sensel
        // index, so scheduling cannot change the original u16 observations.
        self.data.par_iter_mut().enumerate().for_each(|(i, value)| {
            *value = if splitmix(stream.wrapping_add(i as u64)) & 1 == 0 {
                8192 - 32
            } else {
                8192 + 32
            };
        });
    }
}
impl QuadSource for ProbeSource {
    fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let width = 2 * self.geom.width;
        let offset = 2 * y * width;
        (
            &self.data[offset..offset + width],
            &self.data[offset + width..offset + 2 * width],
        )
    }
}
fn splitmix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9e37_79b9_7f4a_7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    x ^ (x >> 31)
}

/// Conservative exact dependency masks for the owned Pyramid's binomial
/// REDUCE and two-phase EXPAND. Any out-of-domain tap is invalid: replicated
/// borders therefore never bias the noise-transfer measurement. Invalid zeros
/// can be changed arbitrarily without affecting an admitted coefficient.
fn band_support_masks(base: &[bool], sizes: &[LevelSize]) -> Vec<Vec<bool>> {
    let mut gaussian = vec![base.to_vec()];
    for k in 1..sizes.len() {
        let prev = sizes[k - 1];
        let next = sizes[k];
        let mut mask = vec![false; next.pixels()];
        for y in 0..next.height {
            for x in 0..next.width {
                let (cx, cy) = (2 * x, 2 * y);
                if cx < 2 || cy < 2 || cx + 2 >= prev.width || cy + 2 >= prev.height {
                    continue;
                }
                mask[y * next.width + x] = ((cy - 2)..=(cy + 2)).all(|sy| {
                    ((cx - 2)..=(cx + 2)).all(|sx| gaussian[k - 1][sy * prev.width + sx])
                });
            }
        }
        gaussian.push(mask);
    }
    let mut bands = Vec::with_capacity(sizes.len());
    for k in 0..sizes.len() {
        let here = sizes[k];
        let mut mask = gaussian[k].clone();
        if k + 1 < sizes.len() {
            let coarse = sizes[k + 1];
            for y in 0..here.height {
                for x in 0..here.width {
                    let (cx, cy) = (x / 2, y / 2);
                    let (xlo, ylo) = (
                        cx as isize - isize::from(x % 2 == 0),
                        cy as isize - isize::from(y % 2 == 0),
                    );
                    let (xhi, yhi) = (cx + 1, cy + 1);
                    let valid = xlo >= 0
                        && ylo >= 0
                        && xhi < coarse.width
                        && yhi < coarse.height
                        && (ylo as usize..=yhi).all(|sy| {
                            (xlo as usize..=xhi).all(|sx| gaussian[k + 1][sy * coarse.width + sx])
                        });
                    mask[y * here.width + x] &= valid;
                }
            }
        } else {
            // A zero-band probe still excludes a perimeter so its statistics
            // mean interior samples, independently of sampler support width.
            for y in 0..here.height {
                for x in 0..here.width {
                    if x == 0 || y == 0 || x + 1 == here.width || y + 1 == here.height {
                        mask[y * here.width + x] = false;
                    }
                }
            }
        }
        bands.push(mask);
    }
    bands
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::align::Cx;
    use strehl_core::optics::A7C2_FE100GM_2XTC_X4CPL;
    use strehl_core::pyramid::BandGain;

    fn shifted(x: f64, y: f64) -> Similarity {
        Similarity {
            a: Cx::ONE,
            b: Cx::new(x, y),
        }
    }
    fn config(bands: usize, realizations: usize) -> ProbeConfig {
        ProbeConfig {
            bands,
            realizations,
            seed: 701,
            min_samples_per_band: 64,
        }
    }
    fn close(actual: f64, expected: f64, tolerance: f64) {
        assert!(
            (actual - expected).abs() <= tolerance,
            "actual {actual}, expected {expected}, tolerance {tolerance}"
        );
    }

    /// First control is independent flat temporal noise; a wrong identity-beta
    /// explanation must fail at half phase before any detail/sharpness test.
    #[test]
    fn a00_flat_independent_noise_identity_half_quarter_and_wrong_beta_foil() {
        let domain = SamplingDomain::full(PlaneGeometry {
            width: 128,
            height: 96,
        });
        for (phase, expected) in [(0.0, 1.0), (0.5, 0.25), (0.25, 0.390625)] {
            let transfer = measure_band_transfer(
                domain,
                shifted(phase, phase),
                None,
                Resampler::Bilinear,
                config(0, 8),
            )
            .unwrap();
            for plane in &transfer.cfa_beta {
                close(f64::from(plane[0]), expected, 0.013);
            }
            close(f64::from(transfer.luma_beta[0]), expected, 0.015);
            if phase == 0.5 {
                // A silent identity-beta fallback predicts four times the
                // observed flat variance and is causally rejected here.
                assert!((transfer.luma_beta[0] - 1.0).abs() > 0.6);
            }
        }
    }

    #[test]
    fn a02_actual_optical_phases_require_distinct_luma_and_color_transfer() {
        let domain = SamplingDomain::full(PlaneGeometry {
            width: 128,
            height: 96,
        });
        // Arbitrary planted operator, NOT an applied camera calibration:
        // alignment gives all sites half/half phase; the channel translation
        // makes only R/B integer again. Green remains half/half.
        let profile = OpticalProfile {
            eps_r: 0.0,
            eps_b: Some(0.0),
            translation: (-0.5, -0.5),
            ..A7C2_FE100GM_2XTC_X4CPL
        };
        let probe = ProbeConfig {
            seed: 94071,
            ..config(0, 8)
        };
        let transfer = measure_band_transfer(
            domain,
            shifted(0.5, 0.5),
            Some(&profile),
            Resampler::Bilinear,
            probe,
        )
        .unwrap();
        for c in [0, 2] {
            close(f64::from(transfer.cfa_beta[c][0]), 1.0, 1e-7);
        }
        for c in [1, 3] {
            close(f64::from(transfer.cfa_beta[c][0]), 0.25, 0.013);
        }
        close(f64::from(transfer.luma_beta[0]), 0.25, 0.015);
        close(f64::from(transfer.max_color_beta[0]), 1.0, 1e-7);
        assert!(transfer.max_color_beta[0] > 3.5 * transfer.luma_beta[0]);
    }

    #[test]
    fn a01_identity_pyramid_agrees_with_existing_white_noise_band_gain() {
        let domain = SamplingDomain::full(PlaneGeometry {
            width: 192,
            height: 160,
        });
        let transfer = measure_band_transfer(
            domain,
            Similarity::IDENTITY,
            None,
            Resampler::CatmullRom,
            config(3, 12),
        )
        .unwrap();
        let white = BandGain::measure(3);
        for k in 0..transfer.luma_beta.len() {
            let expected = white.beta(k);
            close(f64::from(transfer.luma_beta[k] / expected), 1.0, 0.13);
            for channel in &transfer.cfa_beta {
                close(f64::from(channel[k] / expected), 1.0, 0.13);
            }
        }
    }

    /// An active view into a padded sensor buffer. Poison outside active is
    /// deliberately clipped and must never enter the sample or clip mask.
    struct PaddedSource {
        geom: PlaneGeometry,
        origin: (usize, usize),
        stride: usize,
        data: Vec<u16>,
    }
    impl PaddedSource {
        fn new(geom: PlaneGeometry, origin: (usize, usize)) -> Self {
            let stride = origin.0 + geom.width * 2 + 11;
            Self {
                geom,
                origin,
                stride,
                data: vec![65535; stride * (origin.1 + geom.height * 2 + 9)],
            }
        }
        fn set(&mut self, color: usize, x: usize, y: usize, value: u16) {
            let (dx, dy) = CfaPlane::ALL[color].rggb_offset();
            let i = (self.origin.1 + y * 2 + dy) * self.stride + self.origin.0 + x * 2 + dx;
            self.data[i] = value;
        }
        fn fill(&mut self, mut value: impl FnMut(usize, usize, usize) -> u16) {
            for c in 0..4 {
                let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
                for y in 0..self.geom.height {
                    for x in 0..self.geom.width {
                        self.set(
                            c,
                            x,
                            y,
                            value(c, self.origin.0 + 2 * x + dx, self.origin.1 + 2 * y + dy),
                        );
                    }
                }
            }
        }
    }
    impl QuadSource for PaddedSource {
        fn geometry(&self) -> PlaneGeometry {
            self.geom
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let a = (self.origin.1 + y * 2) * self.stride + self.origin.0;
            (
                &self.data[a..a + 2 * self.geom.width],
                &self.data[a + self.stride..a + self.stride + 2 * self.geom.width],
            )
        }
    }
    const LEVELS: Levels = Levels {
        black: 512.0,
        white: 16000.0,
    };

    #[test]
    fn b00_signed_identity_color_separation_and_active_origin_poison() {
        let geom = PlaneGeometry {
            width: 24,
            height: 20,
        };
        let mut source = PaddedSource::new(geom, (7, 5));
        source.fill(|c, _, _| [480, 600, 1200, 1500][c]);
        let mut sampler = NativeSampler::new(SamplingDomain::full(geom)).unwrap();
        let result = sampler
            .gather(
                &source,
                LEVELS,
                Similarity::IDENTITY,
                None,
                Resampler::CatmullRom,
            )
            .unwrap();
        let i = 10 * geom.width + 12;
        assert!(result.support[i]);
        for (c, expected) in [-32.0, 88.0, 688.0, 988.0].into_iter().enumerate() {
            assert_eq!(result.planes[c][i], expected);
        }
        assert!(!result.clipped.iter().any(|&v| v));
        assert!(!result.coverage[0]);
        assert!(!result.support[0]);
    }

    /// The oracle works entirely in absolute SENSOR coordinates, including a
    /// nonzero active origin. It does not reuse the production site conversion.
    fn sensor_oracle(
        source: &PaddedSource,
        x: usize,
        y: usize,
        color: usize,
        transform: Similarity,
        profile: Option<&OpticalProfile>,
    ) -> f64 {
        let (dx, dy) = CfaPlane::ALL[color].rggb_offset();
        let center = (
            source.origin.0 as f64 + source.geom.width as f64 + 0.5,
            source.origin.1 as f64 + source.geom.height as f64 + 0.5,
        );
        let sensor = (
            (source.origin.0 + 2 * x + dx) as f64,
            (source.origin.1 + 2 * y + dy) as f64,
        );
        let (ux, uy) = (sensor.0 - center.0, sensor.1 - center.1);
        // Analytic physical forward location in source sensor units.
        let mut sx = transform.a.re * ux - transform.a.im * uy + 2.0 * transform.b.re;
        let mut sy = transform.a.im * ux + transform.a.re * uy + 2.0 * transform.b.im;
        if let Some(profile) = profile {
            let eps = match color {
                0 => Some(profile.eps_r),
                2 => profile.eps_b,
                _ => None,
            };
            if let Some(eps) = eps {
                sx = (1.0 + eps) * sx + 2.0 * profile.translation.0;
                sy = (1.0 + eps) * sy + 2.0 * profile.translation.1;
            }
        }
        // Each CFA channel encodes a distinct absolute-sensor linear ramp.
        1000.0 * (color + 1) as f64 + 3.0 * (sx + center.0) + 5.0 * (sy + center.1)
    }

    #[test]
    fn b01_scale_rotation_crop_and_ca_match_absolute_sensor_oracle() {
        let geom = PlaneGeometry {
            width: 48,
            height: 40,
        };
        let mut source = PaddedSource::new(geom, (7, 11));
        source.fill(|c, sx, sy| (512 + 1000 * (c + 1) + 3 * sx + 5 * sy) as u16);
        let domain = SamplingDomain {
            full: geom,
            x: 8,
            y: 9,
            width: 24,
            height: 20,
        };
        let mut sampler = NativeSampler::new(domain).unwrap();
        let profile = OpticalProfile {
            eps_r: 0.12,
            eps_b: Some(-0.08),
            translation: (0.4, -0.3),
            ..A7C2_FE100GM_2XTC_X4CPL
        };
        let transforms = [
            Similarity {
                a: Cx::new(1.08, 0.0),
                b: Cx::new(0.0, 0.0),
            },
            Similarity {
                a: Cx::new(0.04f64.cos(), 0.04f64.sin()),
                b: Cx::new(0.0, 0.0),
            },
            Similarity {
                a: Cx::new(0.97, 0.06),
                b: Cx::new(3.0, -2.0),
            },
        ];
        for transform in transforms {
            for ca in [None, Some(&profile)] {
                let result = sampler
                    .gather(&source, LEVELS, transform, ca, Resampler::Bilinear)
                    .unwrap();
                for y in 0..domain.height {
                    for x in 0..domain.width {
                        let i = y * domain.width + x;
                        if !result.support[i] {
                            continue;
                        }
                        for c in 0..4 {
                            close(
                                f64::from(result.planes[c][i]),
                                sensor_oracle(
                                    &source,
                                    domain.x + x,
                                    domain.y + y,
                                    c,
                                    transform,
                                    ca,
                                ),
                                0.002,
                            );
                        }
                    }
                }
            }
        }
        // Full-domain gather must equal its crop bit for bit, including masks.
        let transform = transforms[2];
        let crop = sampler
            .gather(
                &source,
                LEVELS,
                transform,
                Some(&profile),
                Resampler::CatmullRom,
            )
            .unwrap();
        let mut full_sampler = NativeSampler::new(SamplingDomain::full(geom)).unwrap();
        let full = full_sampler
            .gather(
                &source,
                LEVELS,
                transform,
                Some(&profile),
                Resampler::CatmullRom,
            )
            .unwrap();
        for y in 0..domain.height {
            for x in 0..domain.width {
                let i = y * domain.width + x;
                let j = (domain.y + y) * geom.width + domain.x + x;
                assert_eq!(crop.support[i], full.support[j]);
                for c in 0..4 {
                    assert_eq!(crop.planes[c][i].to_bits(), full.planes[c][j].to_bits());
                }
            }
        }
    }

    #[test]
    fn b02_every_color_and_negative_weight_clipped_tap_is_excluded() {
        let geom = PlaneGeometry {
            width: 24,
            height: 20,
        };
        let mut source = PaddedSource::new(geom, (4, 6));
        let mut sampler = NativeSampler::new(SamplingDomain::full(geom)).unwrap();
        let i = 9 * geom.width + 10;
        for color in 0..4 {
            source.fill(|_, _, _| 2000);
            // At half phase (10.5,9.5), x=9 is a NEGATIVE cubic-weight tap.
            source.set(color, 9, 9, 16000);
            let result = sampler
                .gather(
                    &source,
                    LEVELS,
                    shifted(0.5, 0.5),
                    None,
                    Resampler::CatmullRom,
                )
                .unwrap();
            assert!(result.coverage[i]);
            assert!(result.clipped[i]);
            assert!(!result.support[i]);
        }
        source.fill(|_, _, _| 2000);
        source.set(0, 9, 9, 16000);
        let result = sampler
            .gather(
                &source,
                LEVELS,
                Similarity::IDENTITY,
                None,
                Resampler::CatmullRom,
            )
            .unwrap();
        assert!(
            result.support[i],
            "zero-weight neighbor must not clip linear cubic identity"
        );
        let result = sampler
            .gather(
                &source,
                LEVELS,
                Similarity::IDENTITY,
                None,
                Resampler::ClampedCatmullRom,
            )
            .unwrap();
        assert!(
            result.clipped[i],
            "nonlinear hull includes nominally zero-weight taps"
        );
    }

    #[test]
    fn b03_clipping_footprint_matches_core_impulse_response() {
        for geom in [
            PlaneGeometry {
                width: 16,
                height: 15,
            },
            PlaneGeometry {
                width: 5,
                height: 5,
            },
        ] {
            for kernel in [
                Resampler::Nearest,
                Resampler::Bilinear,
                Resampler::CatmullRom,
                Resampler::Lanczos2,
                Resampler::Lanczos3,
            ] {
                for phase in [0.0, 0.25, 0.5, 0.999999] {
                    let (x, y) = if geom.width == 5 {
                        (2.0, 2.0)
                    } else {
                        (7.0 + phase, 6.0 + phase)
                    };
                    let mut values = vec![0.0; geom.pixels()];
                    let mut mask = vec![false; geom.pixels()];
                    if kernel
                        .sample_checked(PlaneRef::from_geometry(&values, geom).unwrap(), x, y)
                        .is_none()
                    {
                        continue;
                    }
                    // Probe axes separately through the actual core sampler.
                    // A 2-D unit impulse can underflow at integer Lanczos
                    // phases despite two nonzero separable weights; that must
                    // not license a clipped original tap to participate.
                    let mut horizontal = vec![false; geom.width];
                    let mut vertical = vec![false; geom.height];
                    for (sx, active) in horizontal.iter_mut().enumerate() {
                        values.fill(0.0);
                        for sy in 0..geom.height {
                            values[sy * geom.width + sx] = 1.0;
                        }
                        *active = kernel
                            .sample_checked(PlaneRef::from_geometry(&values, geom).unwrap(), x, y)
                            .unwrap()
                            != 0.0;
                    }
                    for (sy, active) in vertical.iter_mut().enumerate() {
                        values.fill(0.0);
                        values[sy * geom.width..(sy + 1) * geom.width].fill(1.0);
                        *active = kernel
                            .sample_checked(PlaneRef::from_geometry(&values, geom).unwrap(), x, y)
                            .unwrap()
                            != 0.0;
                    }
                    values.fill(0.0);
                    for i in 0..geom.pixels() {
                        values[i] = 65535.0;
                        mask[i] = true;
                        let response = kernel
                            .sample_checked(PlaneRef::from_geometry(&values, geom).unwrap(), x, y)
                            .unwrap();
                        let clipped = footprint_clipped(&mask, geom, x, y, kernel);
                        assert_eq!(
                            clipped,
                            horizontal[i % geom.width] && vertical[i / geom.width],
                            "kernel {kernel:?} phase {phase} pixel {i}"
                        );
                        assert!(
                            response == 0.0 || clipped,
                            "nonzero actual contribution must clip"
                        );
                        values[i] = 0.0;
                        mask[i] = false;
                    }
                }
            }
        }
    }

    #[test]
    fn b04_missing_and_clipped_zero_sentinels_cannot_pollute_valid_bands() {
        let geom = PlaneGeometry {
            width: 96,
            height: 80,
        };
        let mut source = PaddedSource::new(geom, (3, 9));
        source.fill(|c, sx, sy| (1000 + c * 100 + (sx * 7 + sy * 3) % 800) as u16);
        source.set(0, 48, 40, 16000);
        let mut sampler = NativeSampler::new(SamplingDomain::full(geom)).unwrap();
        let sampled = sampler
            .gather(
                &source,
                LEVELS,
                shifted(0.5, 0.25),
                None,
                Resampler::CatmullRom,
            )
            .unwrap();
        let sizes = level_sizes(geom.width, geom.height, 2);
        let masks = band_support_masks(&sampled.support, &sizes);
        let mut clean = Pyramid::zeros(&sizes);
        let mut poisoned = Pyramid::zeros(&sizes);
        let mut workspace = Workspace::new(&sizes);
        let mut data = sampled.planes[0].clone();
        clean.build(&data, &mut workspace);
        for (v, valid) in data.iter_mut().zip(&sampled.support) {
            if !valid {
                *v = 1_000_000.0;
            }
        }
        poisoned.build(&data, &mut workspace);
        for (k, mask) in masks.iter().enumerate() {
            assert!(mask.iter().any(|&v| v));
            for (i, &valid) in mask.iter().enumerate() {
                if valid {
                    assert_eq!(clean.level(k)[i].to_bits(), poisoned.level(k)[i].to_bits());
                }
            }
        }
    }

    #[test]
    fn b05_probe_refuses_unmeasurable_or_nonlinear_and_preserves_determinism() {
        let domain = SamplingDomain::full(PlaneGeometry {
            width: 48,
            height: 40,
        });
        assert!(
            measure_band_transfer(
                domain,
                Similarity::IDENTITY,
                None,
                Resampler::ClampedCatmullRom,
                config(0, 1)
            )
            .is_err()
        );
        assert!(
            measure_band_transfer(
                domain,
                shifted(100.0, 0.0),
                None,
                Resampler::CatmullRom,
                config(0, 1)
            )
            .is_err()
        );
        let a = measure_band_transfer(
            domain,
            shifted(0.5, 0.25),
            None,
            Resampler::CatmullRom,
            config(1, 2),
        )
        .unwrap();
        let b = measure_band_transfer(
            domain,
            shifted(0.5, 0.25),
            None,
            Resampler::CatmullRom,
            config(1, 2),
        )
        .unwrap();
        assert_eq!(a.cfa_beta, b.cfa_beta);
        assert_eq!(a.luma_beta, b.luma_beta);
        for k in 0..a.luma_beta.len() {
            assert_eq!(
                a.max_color_beta[k],
                a.cfa_beta.iter().map(|v| v[k]).fold(0.0, f32::max)
            );
        }
    }

    #[test]
    fn b08_one_and_sixteen_workers_have_identical_originals_samples_masks_and_betas() {
        fn signature(workers: usize) -> Vec<u64> {
            let pool = rayon::ThreadPoolBuilder::new()
                .num_threads(workers)
                .build()
                .unwrap();
            pool.install(|| {
                assert_eq!(rayon::current_num_threads(), workers);
                let geom = PlaneGeometry {
                    width: 128,
                    height: 96,
                };
                let domain = SamplingDomain {
                    full: geom,
                    x: 5,
                    y: 7,
                    width: 116,
                    height: 82,
                };
                let placement = Similarity {
                    a: Cx::new(0.99, 0.013),
                    b: Cx::new(0.17, -0.29),
                };
                let profile = OpticalProfile {
                    eps_r: 0.01,
                    eps_b: Some(-0.015),
                    translation: (0.12, -0.07),
                    ..A7C2_FE100GM_2XTC_X4CPL
                };
                let mut result = Vec::new();
                let mut original = ProbeSource::new(geom);
                for realization in 0..4 {
                    original.fill(194351, realization);
                    result.extend(original.data.iter().map(|&v| u64::from(v)));
                }
                let mut source = PaddedSource::new(geom, (7, 11));
                let mut sampler = NativeSampler::new(domain).unwrap();
                for clipped in [false, true] {
                    source.fill(|c, sx, sy| (400 + c * 367 + (sx * 17 + sy * 31) % 1100) as u16);
                    if clipped {
                        // Only blue contains clips, so this one call combines
                        // the fast path and the exact stencil path.
                        source.set(2, 15, 15, 16000);
                        source.set(2, 64, 48, 16000);
                    }
                    for kernel in [
                        Resampler::Nearest,
                        Resampler::Bilinear,
                        Resampler::CatmullRom,
                        Resampler::ClampedCatmullRom,
                        Resampler::Lanczos2,
                        Resampler::Lanczos3,
                    ] {
                        let sampled = sampler
                            .gather(&source, LEVELS, placement, Some(&profile), kernel)
                            .unwrap();
                        for plane in &sampled.planes {
                            result.extend(plane.iter().map(|v| u64::from(v.to_bits())));
                        }
                        for mask in [&sampled.coverage, &sampled.clipped, &sampled.support] {
                            result.extend(mask.iter().map(|&v| u64::from(v)));
                        }
                    }
                }
                for kernel in [
                    Resampler::Nearest,
                    Resampler::Bilinear,
                    Resampler::CatmullRom,
                    Resampler::Lanczos2,
                    Resampler::Lanczos3,
                ] {
                    let transfer = measure_band_transfer(
                        domain,
                        placement,
                        Some(&profile),
                        kernel,
                        ProbeConfig {
                            bands: 2,
                            realizations: 4,
                            seed: 194351,
                            min_samples_per_band: 64,
                        },
                    )
                    .unwrap();
                    for beta in transfer
                        .cfa_beta
                        .iter()
                        .chain([&transfer.luma_beta, &transfer.max_color_beta])
                    {
                        result.extend(beta.iter().map(|v| u64::from(v.to_bits())));
                    }
                    result.extend(transfer.samples_per_band.iter().map(|&v| v as u64));
                }
                result
            })
        }
        let one = signature(1);
        let sixteen = signature(16);
        assert_eq!(one.len(), sixteen.len());
        assert!(
            one == sixteen,
            "worker-count bit mismatch at {:?}",
            one.iter().zip(&sixteen).position(|(a, b)| a != b)
        );
    }

    #[test]
    fn b07_allocation_estimates_are_checked_without_allocating() {
        let domain = SamplingDomain::full(PlaneGeometry {
            width: 128,
            height: 96,
        });
        let sampler = NativeSampler::new(domain).unwrap();
        assert_eq!(sampling_bytes(domain).unwrap(), sampler.working_bytes());
        let estimate = ProbeMemoryEstimate::estimate(domain, 3).unwrap();
        assert_eq!(estimate.original_cfa_bytes, 128 * 96 * 8);
        assert!(estimate.peak_bytes > estimate.sampler_bytes + estimate.original_cfa_bytes);
        let enormous = SamplingDomain::full(PlaneGeometry {
            width: usize::MAX / 4,
            height: 1,
        });
        assert!(sampling_bytes(enormous).is_err());
        assert!(ProbeMemoryEstimate::estimate(enormous, 7).is_err());
    }

    #[test]
    fn b06_invalid_geometry_levels_and_placements_refused() {
        let geom = PlaneGeometry {
            width: 8,
            height: 8,
        };
        let mut sampler = NativeSampler::new(SamplingDomain::full(geom)).unwrap();
        let source = PaddedSource::new(geom, (0, 0));
        let singular = Similarity {
            a: Cx::ZERO,
            b: Cx::ZERO,
        };
        assert!(
            sampler
                .gather(&source, LEVELS, singular, None, Resampler::Nearest)
                .is_err()
        );
        assert!(
            sampler
                .gather(
                    &source,
                    Levels {
                        black: 100.0,
                        white: 50.0
                    },
                    Similarity::IDENTITY,
                    None,
                    Resampler::Nearest
                )
                .is_err()
        );
        assert!(
            NativeSampler::new(SamplingDomain {
                full: geom,
                x: 7,
                y: 0,
                width: 2,
                height: 2
            })
            .is_err()
        );
    }
}
