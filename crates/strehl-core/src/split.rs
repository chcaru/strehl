//! Split-stack spectral diagnostics.
//!
//! The two input planes must be independently merged renders of disjoint frame
//! sets.  This module does not make them independent: common sensor structure,
//! a shared registration error, or copying one half into the other all raise
//! FRC.  It therefore reports a correlation curve and an explicitly censored
//! threshold crossing, not a certificate of optical resolution.

use anyhow::{Result, ensure};
use std::f64::consts::PI;

/// D8's conventional FRC threshold.
pub const FRC_THRESHOLD: f64 = 1.0 / 7.0;
/// A ring smaller than this is too sparsely sampled to classify.
pub const MIN_RING_SAMPLES: usize = 16;

#[derive(Clone, Copy, Debug, Default)]
struct Complex {
    re: f64,
    im: f64,
}

impl Complex {
    fn add(self, rhs: Self) -> Self {
        Self {
            re: self.re + rhs.re,
            im: self.im + rhs.im,
        }
    }

    fn sub(self, rhs: Self) -> Self {
        Self {
            re: self.re - rhs.re,
            im: self.im - rhs.im,
        }
    }

    fn mul(self, rhs: Self) -> Self {
        Self {
            re: self.re * rhs.re - self.im * rhs.im,
            im: self.re * rhs.im + self.im * rhs.re,
        }
    }

    fn norm_sqr(self) -> f64 {
        self.re * self.re + self.im * self.im
    }
}

/// Unnormalised sufficient statistics for one Fourier ring.
///
/// Sums, rather than only the final ratio, are public so an external bootstrap
/// can resample tiles without re-running the FFT or averaging ratios with the
/// wrong weights.
#[derive(Clone, Debug, Default)]
pub struct RingSums {
    pub radius: usize,
    pub frequency: f64,
    pub count: usize,
    pub cross: f64,
    pub power_a: f64,
    pub power_b: f64,
}

impl RingSums {
    /// Fourier ring correlation, or `None` for an empty/zero-power ring.
    pub fn frc(&self) -> Option<f64> {
        let den = (self.power_a * self.power_b).sqrt();
        (self.count > 0 && den.is_finite() && den > 0.0).then_some(self.cross / den)
    }

    fn absorb(&mut self, other: &Self) {
        debug_assert_eq!(self.radius, other.radius);
        self.count += other.count;
        self.cross += other.cross;
        self.power_a += other.power_a;
        self.power_b += other.power_b;
    }
}

#[derive(Clone, Debug)]
pub struct TileSpectrum {
    pub tile_x: usize,
    pub tile_y: usize,
    pub origin_x: usize,
    pub origin_y: usize,
    pub rings: Vec<RingSums>,
    pub crossing: Crossing,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Crossing {
    /// First stable downward crossing of 1/7, in cycles per input pixel.
    Measured(f64),
    /// Correlation was still above threshold at the last usable ring.
    CensoredAbove { lower_bound: f64 },
    /// Correlation was already below threshold at the first usable ring.
    CensoredBelow { upper_bound: f64 },
    /// Too few powered, contiguous rings, or an incomplete/gapped transition.
    Insufficient,
}

impl Crossing {
    pub fn label(self) -> &'static str {
        match self {
            Self::Measured(_) => "MEASURED",
            Self::CensoredAbove { .. } => "CENSORED_ABOVE",
            Self::CensoredBelow { .. } => "CENSORED_BELOW",
            Self::Insufficient => "INSUFFICIENT",
        }
    }

    pub fn frequency(self) -> Option<f64> {
        match self {
            Self::Measured(f) => Some(f),
            Self::CensoredAbove { lower_bound } => Some(lower_bound),
            Self::CensoredBelow { upper_bound } => Some(upper_bound),
            Self::Insufficient => None,
        }
    }
}

#[derive(Clone, Debug)]
pub struct SplitAnalysis {
    pub tile_size: usize,
    pub tiles_x: usize,
    pub tiles_y: usize,
    pub start_x: usize,
    pub start_y: usize,
    pub tiles: Vec<TileSpectrum>,
    pub aggregate: Vec<RingSums>,
    pub crossing: Crossing,
}

/// Analyse two same-sized planes on centred, non-overlapping square tiles.
///
/// `tile_size` must be a power of two.  Means are removed before a separable
/// Hann window.  Frequencies are cycles per native input pixel.
pub fn analyse_pair(
    a: &[f32],
    b: &[f32],
    width: usize,
    height: usize,
    tile_size: usize,
) -> Result<SplitAnalysis> {
    analyse_pair_impl(a, b, width, height, tile_size, false, false)
}

fn analyse_pair_impl(
    a: &[f32],
    b: &[f32],
    width: usize,
    height: usize,
    tile_size: usize,
    wrong_conjugate: bool,
    last_bin_fallback: bool,
) -> Result<SplitAnalysis> {
    ensure!(width > 0 && height > 0, "split planes must be non-empty");
    ensure!(
        a.len() == width * height && b.len() == a.len(),
        "split plane dimensions do not match their buffers"
    );
    ensure!(
        tile_size >= 8 && tile_size.is_power_of_two(),
        "split tile size must be a power of two at least 8"
    );
    ensure!(
        width >= tile_size && height >= tile_size,
        "split plane {width}x{height} is smaller than one {tile_size}x{tile_size} tile"
    );

    let tiles_x = width / tile_size;
    let tiles_y = height / tile_size;
    let start_x = (width - tiles_x * tile_size) / 2;
    let start_y = (height - tiles_y * tile_size) / 2;
    let mut tiles = Vec::with_capacity(tiles_x * tiles_y);

    for tile_y in 0..tiles_y {
        for tile_x in 0..tiles_x {
            let origin_x = start_x + tile_x * tile_size;
            let origin_y = start_y + tile_y * tile_size;
            let rings = tile_spectrum(a, b, width, origin_x, origin_y, tile_size, wrong_conjugate);
            let crossing = crossing_impl(&rings, last_bin_fallback, false, false);
            tiles.push(TileSpectrum {
                tile_x,
                tile_y,
                origin_x,
                origin_y,
                rings,
                crossing,
            });
        }
    }

    let mut aggregate = empty_rings(tile_size);
    for tile in &tiles {
        for (dst, src) in aggregate.iter_mut().zip(&tile.rings) {
            dst.absorb(src);
        }
    }
    let crossing = crossing_impl(&aggregate, last_bin_fallback, false, false);

    Ok(SplitAnalysis {
        tile_size,
        tiles_x,
        tiles_y,
        start_x,
        start_y,
        tiles,
        aggregate,
        crossing,
    })
}

fn empty_rings(size: usize) -> Vec<RingSums> {
    (0..=size / 2)
        .map(|radius| RingSums {
            radius,
            frequency: radius as f64 / size as f64,
            ..RingSums::default()
        })
        .collect()
}

fn tile_spectrum(
    a: &[f32],
    b: &[f32],
    stride: usize,
    origin_x: usize,
    origin_y: usize,
    size: usize,
    wrong_conjugate: bool,
) -> Vec<RingSums> {
    let pixels = size * size;
    let mut fa = vec![Complex::default(); pixels];
    let mut fb = vec![Complex::default(); pixels];
    let mut mean_a = 0.0;
    let mut mean_b = 0.0;
    for y in 0..size {
        let row = (origin_y + y) * stride + origin_x;
        for x in 0..size {
            mean_a += f64::from(a[row + x]);
            mean_b += f64::from(b[row + x]);
        }
    }
    mean_a /= pixels as f64;
    mean_b /= pixels as f64;

    let hann: Vec<f64> = (0..size)
        .map(|i| 0.5 - 0.5 * (2.0 * PI * i as f64 / (size - 1) as f64).cos())
        .collect();
    for y in 0..size {
        let row = (origin_y + y) * stride + origin_x;
        for x in 0..size {
            let i = y * size + x;
            let w = hann[x] * hann[y];
            fa[i].re = (f64::from(a[row + x]) - mean_a) * w;
            fb[i].re = (f64::from(b[row + x]) - mean_b) * w;
        }
    }
    fft2(&mut fa, size);
    fft2(&mut fb, size);

    let mut rings = empty_rings(size);
    let max_r = size / 2;
    for y in 0..size {
        let ky = if y <= size / 2 {
            y as isize
        } else {
            y as isize - size as isize
        };
        for x in 0..size {
            let kx = if x <= size / 2 {
                x as isize
            } else {
                x as isize - size as isize
            };
            let radius = (((kx * kx + ky * ky) as f64).sqrt().round()) as usize;
            if radius == 0 || radius > max_r {
                continue;
            }
            let i = y * size + x;
            let av = fa[i];
            let bv = fb[i];
            let ring = &mut rings[radius];
            ring.count += 1;
            ring.power_a += av.norm_sqr();
            ring.power_b += bv.norm_sqr();
            ring.cross += if wrong_conjugate {
                // Commissioning plant P1: A*B, not A*conj(B).
                av.re * bv.re - av.im * bv.im
            } else {
                av.re * bv.re + av.im * bv.im
            };
        }
    }
    rings
}

/// Classify an FRC curve without converting a censored endpoint into a number.
pub fn classify_crossing(rings: &[RingSums]) -> Crossing {
    crossing_impl(rings, false, false, false)
}

fn crossing_impl(
    rings: &[RingSums],
    last_bin_fallback: bool,
    ignore_ring_gaps: bool,
    false_above_tail: bool,
) -> Crossing {
    let usable: Vec<(usize, f64, f64)> = rings
        .iter()
        .filter(|r| r.count >= MIN_RING_SAMPLES)
        .filter_map(|r| {
            r.frc()
                .filter(|v| v.is_finite())
                .map(|v| (r.radius, r.frequency, v))
        })
        .collect();
    if usable.len() < 4 {
        return Crossing::Insufficient;
    }
    if usable[0].2 < FRC_THRESHOLD {
        return Crossing::CensoredBelow {
            upper_bound: usable[0].1,
        };
    }

    for i in 1..usable.len().saturating_sub(2) {
        let (_, f0, y0) = usable[i - 1];
        let (_, f1, y1) = usable[i];
        let consecutive = usable[i - 1..i + 3]
            .windows(2)
            .all(|pair| pair[1].0 == pair[0].0 + 1);
        if y0 >= FRC_THRESHOLD
            && usable[i..i + 3]
                .iter()
                .all(|(_, _, value)| *value < FRC_THRESHOLD)
            && (ignore_ring_gaps || consecutive)
        {
            let dy = y0 - y1;
            let t = if dy.abs() > f64::EPSILON {
                ((y0 - FRC_THRESHOLD) / dy).clamp(0.0, 1.0)
            } else {
                1.0
            };
            return Crossing::Measured(f0 + t * (f1 - f0));
        }
    }

    let (_, last_frequency, last_frc) = *usable.last().expect("checked non-empty");
    if last_bin_fallback {
        // Commissioning plant C1: the historical defect.  This branch is not
        // reachable from the public function.
        Crossing::Measured(last_frequency)
    } else if false_above_tail || last_frc >= FRC_THRESHOLD {
        Crossing::CensoredAbove {
            lower_bound: last_frequency,
        }
    } else {
        Crossing::Insufficient
    }
}

fn fft2(values: &mut [Complex], size: usize) {
    debug_assert_eq!(values.len(), size * size);
    for row in values.chunks_exact_mut(size) {
        fft(row);
    }
    let mut column = vec![Complex::default(); size];
    for x in 0..size {
        for y in 0..size {
            column[y] = values[y * size + x];
        }
        fft(&mut column);
        for y in 0..size {
            values[y * size + x] = column[y];
        }
    }
}

fn fft(values: &mut [Complex]) {
    let n = values.len();
    debug_assert!(n.is_power_of_two());
    let mut j = 0usize;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if i < j {
            values.swap(i, j);
        }
    }

    let mut len = 2;
    while len <= n {
        let angle = -2.0 * PI / len as f64;
        let wlen = Complex {
            re: angle.cos(),
            im: angle.sin(),
        };
        for base in (0..n).step_by(len) {
            let mut w = Complex { re: 1.0, im: 0.0 };
            for offset in 0..len / 2 {
                let u = values[base + offset];
                let v = values[base + offset + len / 2].mul(w);
                values[base + offset] = u.add(v);
                values[base + offset + len / 2] = u.sub(v);
                w = w.mul(wlen);
            }
        }
        len *= 2;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const PLANT_ENV: &str = "STREHL_SPLIT_TEST_PLANT";

    fn noise(state: &mut u64) -> f32 {
        *state ^= *state << 13;
        *state ^= *state >> 7;
        *state ^= *state << 17;
        // Twelve uniforms give a deterministic, approximately Gaussian null
        // without depending on a random-number crate.
        let mut sum = 0.0f32;
        for _ in 0..12 {
            *state ^= *state << 13;
            *state ^= *state >> 7;
            *state ^= *state << 17;
            sum += ((*state >> 40) as u32) as f32 / (1u32 << 24) as f32;
        }
        sum - 6.0
    }

    fn smooth_signal(width: usize, height: usize, seed: u64) -> Vec<f32> {
        let mut state = seed;
        let mut v: Vec<f32> = (0..width * height)
            .map(|_| 18.0 * noise(&mut state))
            .collect();
        let mut tmp = vec![0.0f32; v.len()];
        for _ in 0..5 {
            for y in 0..height {
                for x in 0..width {
                    let mut sum = 0.0;
                    for dy in -1isize..=1 {
                        for dx in -1isize..=1 {
                            let xx = (x as isize + dx).rem_euclid(width as isize) as usize;
                            let yy = (y as isize + dy).rem_euclid(height as isize) as usize;
                            sum += v[yy * width + xx];
                        }
                    }
                    tmp[y * width + x] = sum / 9.0;
                }
            }
            std::mem::swap(&mut v, &mut tmp);
        }
        v
    }

    fn band_mean(rings: &[RingSums], lo: f64, hi: f64) -> f64 {
        let mut cross = 0.0;
        let mut pa = 0.0;
        let mut pb = 0.0;
        for r in rings
            .iter()
            .filter(|r| r.frequency >= lo && r.frequency < hi)
        {
            cross += r.cross;
            pa += r.power_a;
            pb += r.power_b;
        }
        cross / (pa * pb).sqrt()
    }

    fn mean_abs_frc(rings: &[RingSums]) -> f64 {
        let (sum, count) = rings
            .iter()
            .filter(|r| r.count >= MIN_RING_SAMPLES)
            .filter_map(RingSums::frc)
            .fold((0.0, 0usize), |(s, n), v| (s + v.abs(), n + 1));
        sum / count as f64
    }

    fn max_ring_null_t(analysis: &SplitAnalysis) -> f64 {
        let mut max_t = 0.0f64;
        for radius in 1..analysis.aggregate.len() {
            let values: Vec<f64> = analysis
                .tiles
                .iter()
                .filter_map(|tile| {
                    let ring = &tile.rings[radius];
                    (ring.count >= MIN_RING_SAMPLES)
                        .then(|| ring.frc())
                        .flatten()
                })
                .collect();
            if values.len() < 4 {
                continue;
            }
            let mean = values.iter().sum::<f64>() / values.len() as f64;
            let variance = values
                .iter()
                .map(|value| (value - mean).powi(2))
                .sum::<f64>()
                / (values.len() - 1) as f64;
            let se = (variance / values.len() as f64).sqrt();
            let t = if se > 0.0 {
                (mean / se).abs()
            } else if mean == 0.0 {
                0.0
            } else {
                f64::INFINITY
            };
            max_t = max_t.max(t);
        }
        max_t
    }

    fn unsharp(v: &[f32], width: usize, height: usize, amount: f32) -> Vec<f32> {
        let mut out = vec![0.0; v.len()];
        for y in 0..height {
            for x in 0..width {
                let mut sum = 0.0;
                for dy in -1isize..=1 {
                    for dx in -1isize..=1 {
                        let xx = (x as isize + dx).rem_euclid(width as isize) as usize;
                        let yy = (y as isize + dy).rem_euclid(height as isize) as usize;
                        sum += v[yy * width + xx];
                    }
                }
                let blur = sum / 9.0;
                out[y * width + x] = v[y * width + x] + amount * (v[y * width + x] - blur);
            }
        }
        out
    }

    fn gradient_acuity(v: &[f32], width: usize, height: usize) -> f64 {
        let mut sum = 0.0;
        let mut n = 0;
        for y in 1..height - 1 {
            for x in 1..width - 1 {
                let dx = f64::from(v[y * width + x + 1] - v[y * width + x - 1]);
                let dy = f64::from(v[(y + 1) * width + x] - v[(y - 1) * width + x]);
                sum += dx * dx + dy * dy;
                n += 1;
            }
        }
        (sum / n as f64).sqrt()
    }

    #[test]
    fn fixed_external_dft_predicates_match() {
        let n = 8;
        let mut impulse = vec![Complex::default(); n * n];
        impulse[0].re = 1.0;
        fft2(&mut impulse, n);
        assert!(
            impulse
                .iter()
                .all(|v| (v.re - 1.0).abs() < 1e-12 && v.im.abs() < 1e-12)
        );

        let mut constant = vec![Complex { re: 1.0, im: 0.0 }; n * n];
        fft2(&mut constant, n);
        assert!((constant[0].re - 64.0).abs() < 1e-10);
        assert!(constant[1..].iter().all(|v| v.norm_sqr() < 1e-20));

        let mut checker = vec![Complex::default(); n * n];
        for y in 0..n {
            for x in 0..n {
                checker[y * n + x].re = if (x + y) % 2 == 0 { 1.0 } else { -1.0 };
            }
        }
        fft2(&mut checker, n);
        assert!((checker[4 * n + 4].re - 64.0).abs() < 1e-10);
        for (i, v) in checker.iter().enumerate() {
            if i != 4 * n + 4 {
                assert!(v.norm_sqr() < 1e-20, "unexpected checker power at bin {i}");
            }
        }
    }

    /// One test is the acceptance surface the experiment deliberately breaks.
    /// The normal invocation must pass; each named plant must make this exact
    /// test fail with cargo's code 101.
    #[test]
    fn commission_acceptance() {
        let plant = std::env::var(PLANT_ENV).unwrap_or_default();
        assert!(
            ["", "N1", "P1", "S1", "C1", "C2", "C3"].contains(&plant.as_str()),
            "unknown {PLANT_ENV}={plant}"
        );

        let (width, height, tile) = (256, 256, 64);
        let mut sa = 0x1234_5678_9abc_def0;
        let mut sb = 0xfedc_ba98_7654_3210;
        let a: Vec<f32> = (0..width * height).map(|_| noise(&mut sa)).collect();
        let mut b: Vec<f32> = (0..width * height).map(|_| noise(&mut sb)).collect();
        if plant == "N1" {
            b.clone_from(&a);
        }
        let null = analyse_pair_impl(&a, &b, width, height, tile, false, false).unwrap();
        let null_abs = mean_abs_frc(&null.aggregate);
        let null_max_t = max_ring_null_t(&null);
        let null_bands = [
            band_mean(&null.aggregate, 0.02, 0.15),
            band_mean(&null.aggregate, 0.15, 0.30),
            band_mean(&null.aggregate, 0.30, 0.48),
        ];
        println!("NULL mean_abs={null_abs:.6} max_ring_abs_t={null_max_t:.6} bands={null_bands:?}");
        assert!(null_abs < 0.05);
        assert!(
            null_max_t < 4.0,
            "at least one Fourier ring is inconsistent with zero"
        );
        assert!(null_bands.iter().all(|v| v.abs() < 0.08));

        // Same fixed pattern in otherwise independent noise: this must look
        // correlated. It is the cancellation-immune demonstration that FRC
        // cannot distinguish scene signal from common sensor structure.
        let mut common_a = a.clone();
        let mut common_b = b.clone();
        for y in 0..height {
            for x in 0..width {
                let fixed = 2.0 * (2.0 * PI * (5 * x) as f64 / tile as f64).sin() as f32
                    + (2.0 * PI * (3 * y) as f64 / tile as f64).cos() as f32;
                common_a[y * width + x] += fixed;
                common_b[y * width + x] += fixed;
            }
        }
        let common = analyse_pair(&common_a, &common_b, width, height, tile).unwrap();
        let common_low = band_mean(&common.aggregate, 0.02, 0.15);
        println!("COMMON_MODE low_band={common_low:.6} (expected null-bar violation)");
        assert!(
            common_low.abs() >= 0.08,
            "common-mode adversary did not violate the null bar"
        );

        let signal = smooth_signal(width, height, 0xa11c_e55e);
        let mut pa = 0x1357_9bdf_2468_ace0;
        let mut pb = 0x0246_8ace_1357_9bdf;
        let positive_a: Vec<f32> = signal.iter().map(|s| *s + 1.2 * noise(&mut pa)).collect();
        let positive_b: Vec<f32> = signal.iter().map(|s| *s + 1.2 * noise(&mut pb)).collect();
        let positive = analyse_pair_impl(
            &positive_a,
            &positive_b,
            width,
            height,
            tile,
            plant == "P1",
            false,
        )
        .unwrap();
        let low = band_mean(&positive.aggregate, 0.02, 0.10);
        let high = band_mean(&positive.aggregate, 0.35, 0.48);
        let full = analyse_pair(&signal, &signal, width, height, tile).unwrap();
        let max_full_error = full
            .aggregate
            .iter()
            .filter(|r| r.count >= MIN_RING_SAMPLES)
            .filter_map(RingSums::frc)
            .map(|v| (1.0 - v).abs())
            .fold(0.0, f64::max);
        println!("POSITIVE low={low:.6} high={high:.6} full_max_error={max_full_error:.3e}");
        assert!(low >= 0.90);
        assert!(high <= 0.60);
        assert!(low - high >= 0.25);
        assert!(max_full_error <= 1e-4);

        let sharpened_a = unsharp(&positive_a, width, height, 1.5);
        let sharpened_b = unsharp(&positive_b, width, height, 1.5);
        let sharpened = analyse_pair(&sharpened_a, &sharpened_b, width, height, tile).unwrap();
        let max_ring_move = positive
            .aggregate
            .iter()
            .zip(&sharpened.aggregate)
            .filter_map(|(x, y)| Some((x.frc()?, y.frc()?)))
            .map(|(x, y)| (x - y).abs())
            .fold(0.0, f64::max);
        let acuity_before = gradient_acuity(&positive_a, width, height);
        let acuity_after = gradient_acuity(&sharpened_a, width, height);
        let acuity_gain = acuity_after / acuity_before;
        let (crossing_before, crossing_after) = match (positive.crossing, sharpened.crossing) {
            (Crossing::Measured(before), Crossing::Measured(after)) => (before, after),
            other => panic!("sharpening control needs measured crossings, got {other:?}"),
        };
        let crossing_move = if plant == "S1" {
            // Commissioning plant S1: substitute the naive sharpness gain for
            // the correlation crossing, exactly the fakeable metric this
            // control exists to reject.
            acuity_gain - 1.0
        } else {
            crossing_after - crossing_before
        };
        println!(
            "SHARPEN frc_max_move={max_ring_move:.6} naive_acuity_gain={acuity_gain:.6} \
             crossing_before={:?} crossing_after={:?} crossing_move={crossing_move:.6}",
            positive.crossing, sharpened.crossing
        );
        assert!(acuity_gain >= 1.25);
        assert!(
            crossing_move <= 1e-6,
            "identical sharpening improved the reported resolution"
        );
        assert!(
            crossing_move.abs() <= 1.0 / tile as f64,
            "finite-tile crossing moved by more than one ring"
        );

        let broadband = {
            let mut s = 0x55aa_aa55_dead_beef;
            (0..width * height)
                .map(|_| noise(&mut s))
                .collect::<Vec<_>>()
        };
        let censored = analyse_pair_impl(
            &broadband,
            &broadband,
            width,
            height,
            tile,
            false,
            plant == "C1",
        )
        .unwrap()
        .crossing;
        println!("CENSOR crossing={censored:?}");
        assert!(matches!(censored, Crossing::CensoredAbove { .. }));

        // These are the two exact classifier defects found by independent
        // verification. C2 recreates the old compression of missing physical
        // rings; C3 recreates the old false lower bound when a curve falls only
        // in its final one or two rings.
        let curve = |values: &[Option<f64>]| {
            values
                .iter()
                .enumerate()
                .map(|(i, value)| RingSums {
                    radius: i + 1,
                    frequency: (i + 1) as f64 / 10.0,
                    count: value.map_or(0, |_| MIN_RING_SAMPLES),
                    cross: value.unwrap_or(0.0),
                    power_a: value.map_or(0.0, |_| 1.0),
                    power_b: value.map_or(0.0, |_| 1.0),
                })
                .collect::<Vec<_>>()
        };
        let gapped = crossing_impl(
            &curve(&[Some(0.4), Some(0.1), None, Some(0.05), Some(0.04)]),
            false,
            plant == "C2",
            false,
        );
        let short_tail = crossing_impl(
            &curve(&[Some(0.9), Some(0.8), Some(0.1), Some(0.05)]),
            false,
            false,
            plant == "C3",
        );
        println!("EDGE_CASES gapped={gapped:?} short_tail={short_tail:?}");
        assert!(matches!(gapped, Crossing::Insufficient));
        assert!(matches!(short_tail, Crossing::Insufficient));
    }

    #[test]
    fn dimensions_and_tile_size_are_validated() {
        assert!(analyse_pair(&[], &[], 0, 0, 64).is_err());
        assert!(analyse_pair(&[0.0; 64], &[0.0; 64], 8, 8, 7).is_err());
        assert!(analyse_pair(&[0.0; 64], &[0.0; 63], 8, 8, 8).is_err());
    }
}
