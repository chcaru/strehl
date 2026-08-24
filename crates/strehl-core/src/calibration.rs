//! Per-stack calibration of the merge gate.
//!
//! M70's spectral effective frame count is deliberately independent of the
//! spatial merge gate. [`SpectralAccumulator`] measures that target from fixed
//! green-quincunx patches. [`AdmissionHistogram`] then measures the gate each
//! spatial sample would require and selects the threshold whose realised mean
//! admitted count is nearest the spectral target.
//!
//! Neither object retains a focus volume. The spectrum keeps 24 small records
//! per frame; the admission solve keeps a fixed histogram independent of frame
//! count.

use std::cmp::Ordering;

use anyhow::{Result, bail, ensure};

use crate::CfaPlane;
use crate::merge::{FOCUS_NOISE_SD, FocusStats};
use crate::noise::NoiseModel;
use crate::plane::{PlaneGeometry, QuadSource};

/// M70's green-quincunx patch side, in GQ samples.
pub const SPECTRAL_PATCH: usize = 256;
/// M70's Welch tile side, in GQ samples.
pub const SPECTRAL_TILE: usize = 128;
/// Number of fixed-grid patches in M70's instrument.
pub const SPECTRAL_PATCHES: usize = 24;
/// The texture-classification threshold in the low band.
pub const TEXTURE_SNR_MIN: f64 = 10.0;

const PATCH_TILES: usize = 3;
const WELCH_TILES: usize = PATCH_TILES * PATCH_TILES;
const RADIAL_BINS: usize = SPECTRAL_TILE / 2;
const BANDS: [(f64, f64); 4] = [
    (0.025, 0.050),
    (0.100, 0.150),
    (0.150, 0.200),
    (0.200, 0.2762),
];
const MID_BANDS: std::ops::Range<usize> = 1..4;
const ROW_FRAC: [f64; 4] = [0.20, 0.40, 0.60, 0.80];
const COL_FRAC: [f64; 6] = [0.15, 0.32, 0.49, 0.66, 0.83, 0.95];

/// Exact spatial configuration of M70's spectral instrument.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SpectralConfig {
    /// Width of the decoder intersection used to place the fixed grid.
    pub analysis_width: usize,
    /// Height of the decoder intersection used to place the fixed grid.
    pub analysis_height: usize,
}

impl SpectralConfig {
    pub fn new(analysis_width: usize, analysis_height: usize) -> Result<Self> {
        ensure!(
            analysis_width >= 2 * SPECTRAL_PATCH + 2 && analysis_height >= 2 * SPECTRAL_PATCH + 2,
            "the spectral estimator needs at least {}x{} sensor samples, got \
             {analysis_width}x{analysis_height}",
            2 * SPECTRAL_PATCH + 2,
            2 * SPECTRAL_PATCH + 2
        );
        Ok(Self {
            analysis_width,
            analysis_height,
        })
    }

    fn centres(self) -> [(usize, usize); SPECTRAL_PATCHES] {
        let mut out = [(0usize, 0usize); SPECTRAL_PATCHES];
        let half = SPECTRAL_PATCH - 1;
        let mut i = 0;
        for rf in ROW_FRAC {
            for cf in COL_FRAC {
                let rc = (rf * self.analysis_height as f64)
                    .round_ties_even()
                    .clamp(half as f64, (self.analysis_height - 1 - half) as f64)
                    as usize;
                let cc = (cf * self.analysis_width as f64)
                    .round_ties_even()
                    .clamp(half as f64, (self.analysis_width - 1 - half) as f64)
                    as usize;
                out[i] = (rc - rc % 2, cc - cc % 2);
                i += 1;
            }
        }
        out
    }
}

#[derive(Debug, Clone)]
struct SpectrumObservation {
    frame_index: u16,
    power: [[f64; BANDS.len()]; SPECTRAL_PATCHES],
    noise_variance: [f64; SPECTRAL_PATCHES],
}

/// Gate-free spectral information measured from one stack.
#[derive(Debug, Clone, PartialEq)]
pub struct SpectralTarget {
    pub frames: usize,
    pub noise_scale: f64,
    pub textured_patches: usize,
    pub per_band_n_eff: [f64; 3],
    pub n_eff: f64,
}

/// M70's corrected, unclipped gate-free spectral estimator.
pub struct SpectralAccumulator {
    config: SpectralConfig,
    centres: [(usize, usize); SPECTRAL_PATCHES],
    observations: Vec<SpectrumObservation>,
    analyser: PatchAnalyser,
}

impl SpectralAccumulator {
    pub fn new(config: SpectralConfig) -> Self {
        Self {
            config,
            centres: config.centres(),
            observations: Vec::new(),
            analyser: PatchAnalyser::new(),
        }
    }

    pub fn config(&self) -> SpectralConfig {
        self.config
    }

    pub fn frames(&self) -> usize {
        self.observations.len()
    }

    /// Measure all 24 fixed patches in one CFA frame.
    pub fn observe<S: QuadSource + ?Sized>(
        &mut self,
        frame_index: u16,
        source: &S,
        black: f32,
        noise: &NoiseModel,
    ) -> Result<()> {
        let geom = source.geometry();
        let sensor_width = 2 * geom.width;
        let sensor_height = 2 * geom.height;
        ensure!(
            self.config.analysis_width <= sensor_width
                && self.config.analysis_height <= sensor_height,
            "spectral analysis area {}x{} exceeds frame active area {}x{}",
            self.config.analysis_width,
            self.config.analysis_height,
            sensor_width,
            sensor_height
        );
        ensure!(
            !self
                .observations
                .iter()
                .any(|observation| observation.frame_index == frame_index),
            "spectral frame index {frame_index} was folded twice"
        );

        let mut power = [[0.0; BANDS.len()]; SPECTRAL_PATCHES];
        let mut noise_variance = [0.0; SPECTRAL_PATCHES];
        for patch_index in 0..SPECTRAL_PATCHES {
            extract_gq_patch(
                source,
                self.centres[patch_index],
                black,
                &mut self.analyser.patch,
            )?;
            let (p, level) = self.analyser.measure();
            power[patch_index] = p;
            noise_variance[patch_index] = f64::from(noise.variance(CfaPlane::G1, level as f32));
        }
        self.observations.push(SpectrumObservation {
            frame_index,
            power,
            noise_variance,
        });
        Ok(())
    }

    /// Merge a worker's observations. Frame order is restored explicitly.
    pub fn absorb(&mut self, mut other: Self) -> Result<()> {
        ensure!(
            self.config == other.config,
            "cannot merge spectral accumulators with configurations {:?} and {:?}",
            self.config,
            other.config
        );
        self.observations.append(&mut other.observations);
        self.observations.sort_by_key(|o| o.frame_index);
        for pair in self.observations.windows(2) {
            ensure!(
                pair[0].frame_index != pair[1].frame_index,
                "spectral frame index {} occurred in two workers",
                pair[0].frame_index
            );
        }
        Ok(())
    }

    /// Compute M70's target after multiplying the model variance by `noise_scale`.
    pub fn target(&self, noise_scale: f64) -> Result<SpectralTarget> {
        ensure!(
            noise_scale.is_finite() && noise_scale > 0.0,
            "noise scale must be finite and positive, got {noise_scale}"
        );
        ensure!(
            !self.observations.is_empty(),
            "cannot estimate spectral n_eff without frames"
        );

        let mut textured = [false; SPECTRAL_PATCHES];
        for (patch, is_textured) in textured.iter_mut().enumerate() {
            let mut nvar: Vec<f64> = self
                .observations
                .iter()
                .map(|o| noise_scale * o.noise_variance[patch])
                .collect();
            let median_noise = median(&mut nvar).unwrap_or(f64::NAN);
            let peak_low = self
                .observations
                .iter()
                .map(|o| o.power[patch][0] - noise_scale * o.noise_variance[patch])
                .fold(f64::NEG_INFINITY, f64::max);
            *is_textured = median_noise > 0.0 && peak_low / median_noise >= TEXTURE_SNR_MIN;
        }
        let textured_patches = textured.iter().filter(|&&v| v).count();
        ensure!(
            textured_patches > 0,
            "no spectral patch passed the low-band texture threshold"
        );

        let mut per_band_n_eff = [0.0; 3];
        for (out_band, band) in MID_BANDS.enumerate() {
            let mut patch_values = Vec::with_capacity(textured_patches);
            for (patch, &use_patch) in textured.iter().enumerate() {
                if !use_patch {
                    continue;
                }
                let mut signal = Vec::with_capacity(self.observations.len());
                for observation in &self.observations {
                    signal.push(
                        observation.power[patch][band]
                            - noise_scale * observation.noise_variance[patch],
                    );
                }
                let sum: f64 = signal.iter().copied().sum();
                let peak = signal
                    .iter()
                    .copied()
                    .fold(f64::NEG_INFINITY, f64::max)
                    .max(1e-30);
                // Deliberately no max(0) on each term. M70 measured that such a
                // clip rectifies noise into a false frame count growing with N.
                patch_values.push(sum / peak);
            }
            per_band_n_eff[out_band] =
                median(&mut patch_values).ok_or_else(|| anyhow::anyhow!("empty band"))?;
        }
        let n_eff = per_band_n_eff.iter().sum::<f64>() / per_band_n_eff.len() as f64;
        Ok(SpectralTarget {
            frames: self.observations.len(),
            noise_scale,
            textured_patches,
            per_band_n_eff,
            n_eff,
        })
    }
}

fn median(values: &mut Vec<f64>) -> Option<f64> {
    values.retain(|v| v.is_finite());
    if values.is_empty() {
        return None;
    }
    values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));
    let m = values.len() / 2;
    Some(if values.len().is_multiple_of(2) {
        0.5 * (values[m - 1] + values[m])
    } else {
        values[m]
    })
}

fn extract_gq_patch<S: QuadSource + ?Sized>(
    source: &S,
    (rc, cc): (usize, usize),
    black: f32,
    dst: &mut [f64],
) -> Result<()> {
    ensure!(
        dst.len() == SPECTRAL_PATCH * SPECTRAL_PATCH,
        "GQ patch destination has {} samples, expected {}",
        dst.len(),
        SPECTRAL_PATCH * SPECTRAL_PATCH
    );
    let geom = source.geometry();
    let (sensor_width, sensor_height) = (2 * geom.width, 2 * geom.height);
    let u0 = ((rc + cc) / 2) as isize;
    let v0 = (rc as isize - cc as isize) / 2;
    let half = (SPECTRAL_PATCH / 2) as isize;

    for pu in 0..SPECTRAL_PATCH {
        for pv in 0..SPECTRAL_PATCH {
            let u = u0 + pu as isize - half;
            let v = v0 + pv as isize - half;
            let r = u + v;
            let c = u - v + 1;
            if r < 0 || c < 0 || r >= sensor_height as isize || c >= sensor_width as isize {
                bail!("GQ patch centred at ({rc},{cc}) leaves the active area at ({r},{c})");
            }
            let r = r as usize;
            let c = c as usize;
            let (row0, row1) = source.quad_rows(r / 2);
            let row = if r.is_multiple_of(2) { row0 } else { row1 };
            dst[pu * SPECTRAL_PATCH + pv] = f64::from(row[c]) - f64::from(black);
        }
    }
    Ok(())
}

struct PatchAnalyser {
    patch: Vec<f64>,
    re: Vec<f64>,
    im: Vec<f64>,
    col_re: Vec<f64>,
    col_im: Vec<f64>,
    hann: [f64; SPECTRAL_TILE],
    window_norm: f64,
    band_for_bin: Vec<i8>,
    band_counts: [usize; BANDS.len()],
}

impl PatchAnalyser {
    fn new() -> Self {
        let hann = std::array::from_fn(|i| {
            0.5 - 0.5 * (2.0 * std::f64::consts::PI * i as f64 / SPECTRAL_TILE as f64).cos()
        });
        let sum_w2: f64 = hann.iter().map(|w| w * w).sum();
        let window_norm = sum_w2 * sum_w2;
        let mut band_for_bin = vec![-1i8; SPECTRAL_TILE * SPECTRAL_TILE];
        let mut band_counts = [0usize; BANDS.len()];
        let rmax = 0.5 / 2.0f64.sqrt();
        for u in 0..SPECTRAL_TILE {
            let fu = fft_frequency(u, SPECTRAL_TILE);
            for v in 0..SPECTRAL_TILE {
                let fv = fft_frequency(v, SPECTRAL_TILE);
                let fx = 0.5 * (fu - fv);
                let fy = 0.5 * (fu + fv);
                let r = fx.hypot(fy);
                if r > rmax {
                    continue;
                }
                let radial_bin = (r / rmax * RADIAL_BINS as f64).floor() as usize;
                if radial_bin == 0 || radial_bin >= RADIAL_BINS {
                    continue;
                }
                let centre = (radial_bin as f64 + 0.5) * rmax / RADIAL_BINS as f64;
                if let Some((band, _)) = BANDS
                    .iter()
                    .enumerate()
                    .find(|(_, (lo, hi))| centre >= *lo && centre < *hi)
                {
                    band_for_bin[u * SPECTRAL_TILE + v] = band as i8;
                    band_counts[band] += 1;
                }
            }
        }
        assert!(band_counts.iter().all(|&n| n > 0));
        Self {
            patch: vec![0.0; SPECTRAL_PATCH * SPECTRAL_PATCH],
            re: vec![0.0; SPECTRAL_TILE * SPECTRAL_TILE],
            im: vec![0.0; SPECTRAL_TILE * SPECTRAL_TILE],
            col_re: vec![0.0; SPECTRAL_TILE],
            col_im: vec![0.0; SPECTRAL_TILE],
            hann,
            window_norm,
            band_for_bin,
            band_counts,
        }
    }

    fn measure(&mut self) -> ([f64; BANDS.len()], f64) {
        let starts = [0usize, SPECTRAL_TILE / 2, SPECTRAL_TILE];
        let mut band_power = [0.0; BANDS.len()];
        let mut level = 0.0;

        for y0 in starts {
            for x0 in starts {
                let mut mean = 0.0;
                for y in 0..SPECTRAL_TILE {
                    let lo = (y0 + y) * SPECTRAL_PATCH + x0;
                    mean += self.patch[lo..lo + SPECTRAL_TILE].iter().sum::<f64>();
                }
                mean /= (SPECTRAL_TILE * SPECTRAL_TILE) as f64;

                for y in 0..SPECTRAL_TILE {
                    let wy = self.hann[y];
                    for x in 0..SPECTRAL_TILE {
                        let wx = self.hann[x];
                        let p = self.patch[(y0 + y) * SPECTRAL_PATCH + x0 + x];
                        let i = y * SPECTRAL_TILE + x;
                        self.re[i] = (p - mean) * wy * wx;
                        self.im[i] = 0.0;
                        level += p.max(0.0) * wy * wy * wx * wx / self.window_norm;
                    }
                }
                fft2(
                    &mut self.re,
                    &mut self.im,
                    &mut self.col_re,
                    &mut self.col_im,
                );
                for i in 0..self.re.len() {
                    let band = self.band_for_bin[i];
                    if band >= 0 {
                        let band = band as usize;
                        band_power[band] +=
                            (self.re[i] * self.re[i] + self.im[i] * self.im[i]) / self.window_norm;
                    }
                }
            }
        }

        for (band, power) in band_power.iter_mut().enumerate() {
            *power /= (WELCH_TILES * self.band_counts[band]) as f64;
        }
        level /= WELCH_TILES as f64;
        (band_power, level)
    }
}

fn fft_frequency(i: usize, n: usize) -> f64 {
    if i < n / 2 {
        i as f64 / n as f64
    } else {
        (i as isize - n as isize) as f64 / n as f64
    }
}

fn fft2(re: &mut [f64], im: &mut [f64], col_re: &mut [f64], col_im: &mut [f64]) {
    debug_assert_eq!(re.len(), SPECTRAL_TILE * SPECTRAL_TILE);
    debug_assert_eq!(im.len(), re.len());
    for y in 0..SPECTRAL_TILE {
        let lo = y * SPECTRAL_TILE;
        fft(
            &mut re[lo..lo + SPECTRAL_TILE],
            &mut im[lo..lo + SPECTRAL_TILE],
        );
    }
    for x in 0..SPECTRAL_TILE {
        for y in 0..SPECTRAL_TILE {
            col_re[y] = re[y * SPECTRAL_TILE + x];
            col_im[y] = im[y * SPECTRAL_TILE + x];
        }
        fft(col_re, col_im);
        for y in 0..SPECTRAL_TILE {
            re[y * SPECTRAL_TILE + x] = col_re[y];
            im[y * SPECTRAL_TILE + x] = col_im[y];
        }
    }
}

fn fft(re: &mut [f64], im: &mut [f64]) {
    let n = re.len();
    debug_assert!(n.is_power_of_two());
    debug_assert_eq!(im.len(), n);
    let mut j = 0;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if i < j {
            re.swap(i, j);
            im.swap(i, j);
        }
    }

    let mut len = 2;
    while len <= n {
        let angle = -2.0 * std::f64::consts::PI / len as f64;
        let (wlen_im, wlen_re) = angle.sin_cos();
        for base in (0..n).step_by(len) {
            let (mut wr, mut wi) = (1.0, 0.0);
            for offset in 0..len / 2 {
                let a = base + offset;
                let b = a + len / 2;
                let br = re[b] * wr - im[b] * wi;
                let bi = re[b] * wi + im[b] * wr;
                let ar = re[a];
                let ai = im[a];
                re[a] = ar + br;
                im[a] = ai + bi;
                re[b] = ar - br;
                im[b] = ai - bi;
                let next_wr = wr * wlen_re - wi * wlen_im;
                wi = wr * wlen_im + wi * wlen_re;
                wr = next_wr;
            }
        }
        len <<= 1;
    }
}

/// Number of low `f32` bits discarded by the mergeable admission histogram.
///
/// The retained exponent plus nine mantissa bits gives at most about 0.2%
/// relative threshold quantisation, inside M81's registered 1% target-hit bar.
const HISTOGRAM_SHIFT: u32 = 14;
const MAX_FINITE_F32_BITS: u32 = f32::MAX.to_bits();
const HISTOGRAM_BUCKETS: usize = (MAX_FINITE_F32_BITS >> HISTOGRAM_SHIFT) as usize + 1;

/// Fixed-memory distribution of the gate required by every frame/pixel pair.
pub struct AdmissionHistogram {
    geom: PlaneGeometry,
    zero: u64,
    positive: Vec<u64>,
    unreachable: u64,
    frames: u32,
}

/// Result of matching a spectral target to the spatial admission distribution.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct GateCalibration {
    pub gate: f32,
    pub target_n_eff: f64,
    pub realised_n_eff: f64,
    pub lower_n_eff: f64,
    pub upper_n_eff: f64,
    pub unreachable: u64,
}

impl AdmissionHistogram {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            zero: 0,
            positive: vec![0; HISTOGRAM_BUCKETS],
            unreachable: 0,
            frames: 0,
        }
    }

    pub fn frames_folded(&self) -> u32 {
        self.frames
    }

    /// Mean admissions at gate zero and at a gate wider than every finite gap.
    pub fn admission_range(&self) -> (f64, f64) {
        let px = self.geom.pixels() as f64;
        if px == 0.0 {
            return (0.0, 0.0);
        }
        let positive: u64 = self.positive.iter().sum();
        (self.zero as f64 / px, (self.zero + positive) as f64 / px)
    }

    /// Fold one frame's regularised field against the completed pass-one winner.
    pub fn fold(
        &mut self,
        frame_index: u16,
        stats: &FocusStats,
        regularised: &[f32],
    ) -> Result<()> {
        ensure!(
            stats.geometry() == self.geom,
            "admission histogram geometry {:?} differs from winner geometry {:?}",
            self.geom,
            stats.geometry()
        );
        ensure!(
            regularised.len() == self.geom.pixels(),
            "admission field has {} pixels, expected {}",
            regularised.len(),
            self.geom.pixels()
        );
        let unit = std::f32::consts::SQRT_2 * FOCUS_NOISE_SD;
        for (i, &focus) in regularised.iter().enumerate() {
            if frame_index == stats.best_index()[i] {
                self.zero += 1;
                continue;
            }
            let best = stats.best_focus()[i];
            if !(best.is_finite() && focus.is_finite()) {
                self.unreachable += 1;
                continue;
            }
            let required = ((best - focus) / unit).max(0.0);
            if required == 0.0 {
                self.zero += 1;
            } else if required.is_finite() {
                let bucket = (required.to_bits() >> HISTOGRAM_SHIFT) as usize;
                self.positive[bucket] += 1;
            } else {
                self.unreachable += 1;
            }
        }
        self.frames += 1;
        Ok(())
    }

    pub fn absorb(&mut self, other: Self) -> Result<()> {
        ensure!(
            self.geom == other.geom,
            "cannot merge admission histograms with geometries {:?} and {:?}",
            self.geom,
            other.geom
        );
        self.zero += other.zero;
        self.unreachable += other.unreachable;
        self.frames += other.frames;
        for (a, b) in self.positive.iter_mut().zip(other.positive) {
            *a += b;
        }
        Ok(())
    }

    pub fn solve(&self, target_n_eff: f64) -> Result<GateCalibration> {
        ensure!(
            target_n_eff.is_finite(),
            "target n_eff must be finite, got {target_n_eff}"
        );
        let px = self.geom.pixels() as f64;
        ensure!(px > 0.0, "cannot calibrate an empty plane");
        let (min_n, max_n) = self.admission_range();
        ensure!(
            target_n_eff >= min_n && target_n_eff <= max_n,
            "target n_eff {target_n_eff:.6} is outside the measured admission bracket \
             [{min_n:.6}, {max_n:.6}]"
        );

        let mut best_gate = 0.0f32;
        let mut best_count = self.zero;
        let mut best_error = (min_n - target_n_eff).abs();
        let mut cumulative = self.zero;
        let mut lower = min_n;
        let mut upper = min_n;
        let mut bracketed = target_n_eff == min_n;

        for (bucket, &count) in self.positive.iter().enumerate() {
            if count == 0 {
                continue;
            }
            let before = cumulative as f64 / px;
            cumulative += count;
            let after = cumulative as f64 / px;
            if !bracketed && target_n_eff >= before && target_n_eff <= after {
                lower = before;
                upper = after;
                bracketed = true;
            }
            let error = (after - target_n_eff).abs();
            if error < best_error {
                let upper_bits =
                    ((((bucket as u32) + 1) << HISTOGRAM_SHIFT) - 1).min(MAX_FINITE_F32_BITS);
                best_gate = f32::from_bits(upper_bits);
                best_count = cumulative;
                best_error = error;
            }
        }
        ensure!(
            bracketed,
            "target was not bracketed by non-empty histogram bins"
        );
        Ok(GateCalibration {
            gate: best_gate,
            target_n_eff,
            realised_n_eff: best_count as f64 / px,
            lower_n_eff: lower,
            upper_n_eff: upper,
            unreachable: self.unreachable,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::merge::Gate;

    #[test]
    fn radix_two_fft_matches_a_direct_dft() {
        let input = [0.25, -1.0, 3.5, 2.0, -0.75, 0.5, 4.0, -2.0];
        let mut re = input;
        let mut im = [0.0; 8];
        fft(&mut re, &mut im);
        for k in 0..8 {
            let (mut want_re, mut want_im) = (0.0, 0.0);
            for (j, &x) in input.iter().enumerate() {
                let a = -2.0 * std::f64::consts::PI * (j * k) as f64 / 8.0;
                want_re += x * a.cos();
                want_im += x * a.sin();
            }
            assert!((re[k] - want_re).abs() < 1e-10, "real bin {k}");
            assert!((im[k] - want_im).abs() < 1e-10, "imag bin {k}");
        }
    }

    #[test]
    fn a_constant_patch_has_zero_band_power_and_the_right_weighted_level() {
        let mut analyser = PatchAnalyser::new();
        analyser.patch.fill(1234.5);
        let (power, level) = analyser.measure();
        assert!((level - 1234.5).abs() < 1e-9, "level {level}");
        assert!(power.iter().all(|v| v.abs() < 1e-18), "{power:?}");
    }

    fn observation(frame: u16, mid_signal: f64) -> SpectrumObservation {
        let mut power = [[0.0; BANDS.len()]; SPECTRAL_PATCHES];
        for patch in &mut power {
            patch[0] = 110.0;
            patch[1] = 10.0 + mid_signal;
            patch[2] = 10.0 + mid_signal;
            patch[3] = 10.0 + mid_signal;
        }
        SpectrumObservation {
            frame_index: frame,
            power,
            noise_variance: [10.0; SPECTRAL_PATCHES],
        }
    }

    #[test]
    fn the_static_spectral_plant_recovers_all_41_frames() {
        let config = SpectralConfig::new(1024, 1024).unwrap();
        let mut a = SpectralAccumulator::new(config);
        a.observations = (0..41).map(|k| observation(k, 50.0)).collect();
        let t = a.target(1.0).unwrap();
        assert_eq!(t.textured_patches, SPECTRAL_PATCHES);
        assert!((t.n_eff / 41.0 - 1.0).abs() < 1e-12, "{t:?}");
    }

    #[test]
    fn summing_before_clipping_returns_zero_on_the_noise_plant() {
        let config = SpectralConfig::new(1024, 1024).unwrap();
        let mut a = SpectralAccumulator::new(config);
        a.observations = (0..41)
            .map(|k| observation(k, if k % 2 == 0 { -1.0 } else { 1.0 }))
            .collect();
        let t = a.target(1.0).unwrap();
        assert!(t.n_eff.abs() <= 1.0, "{t:?}");

        let signal: Vec<f64> = (0..41)
            .map(|k| if k % 2 == 0 { -1.0 } else { 1.0 })
            .collect();
        let clipped = signal.iter().map(|s| s.max(0.0)).sum::<f64>()
            / signal.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        assert!(
            clipped > 10.0,
            "the planted clip did not manufacture a false frame count: {clipped}"
        );
    }

    #[test]
    fn admission_histogram_solves_the_measured_monotone_ladder() {
        let geom = PlaneGeometry {
            width: 2,
            height: 1,
        };
        let fields = [[10.0, 10.0], [9.0, 8.0], [7.0, 6.0]];
        let mut stats = FocusStats::new(geom);
        for (k, field) in fields.iter().enumerate() {
            stats.fold(k as u16, field).unwrap();
        }
        let mut h = AdmissionHistogram::new(geom);
        for (k, field) in fields.iter().enumerate() {
            h.fold(k as u16, &stats, field).unwrap();
        }
        let solved = h.solve(2.0).unwrap();
        let gate = Gate::new(solved.gate);
        let realised = fields
            .iter()
            .flat_map(|field| field.iter().enumerate())
            .filter(|(i, focus)| gate.admits(**focus, stats.best_focus()[*i]))
            .count() as f64
            / geom.pixels() as f64;
        assert!((realised - solved.realised_n_eff).abs() < 1e-12);
        assert!((realised - 2.0).abs() / 2.0 < 0.01, "{solved:?}");
        assert_eq!(h.admission_range(), (1.0, 3.0));
    }

    #[test]
    fn admission_histogram_refuses_extrapolation() {
        let geom = PlaneGeometry {
            width: 1,
            height: 1,
        };
        let mut stats = FocusStats::new(geom);
        stats.fold(0, &[1.0]).unwrap();
        let mut h = AdmissionHistogram::new(geom);
        h.fold(0, &stats, &[1.0]).unwrap();
        assert!(h.solve(0.9).is_err());
        assert!(h.solve(1.1).is_err());
    }
}
