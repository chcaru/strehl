//! Optional repeated-structure diagnostics. Correlation describes shared image
//! content; it cannot distinguish true detail from shared processing or fixed
//! pattern. No fixed correlation cutoff is presented as a resolution estimate.
use std::collections::BTreeSet;

#[derive(Clone, Copy, Default, Debug)]
struct Complex {
    re: f32,
    im: f32,
}
impl Complex {
    fn power(self) -> f32 {
        self.re * self.re + self.im * self.im
    }
}

#[derive(Clone, Debug)]
pub struct IndependentPair {
    a: Vec<u64>,
    b: Vec<u64>,
}
impl IndependentPair {
    /// IDs must identify original acquisitions, including aliases. The caller
    /// binds these IDs to original content hashes in the saved evidence envelope.
    pub fn new(a: &[u64], b: &[u64]) -> Result<Self, &'static str> {
        let aa: BTreeSet<_> = a.iter().copied().collect();
        let bb: BTreeSet<_> = b.iter().copied().collect();
        if aa.is_empty()
            || bb.is_empty()
            || aa.len() != a.len()
            || bb.len() != b.len()
            || !aa.is_disjoint(&bb)
        {
            return Err("reproducibility requires disjoint original acquisitions");
        }
        Ok(Self {
            a: a.to_vec(),
            b: b.to_vec(),
        })
    }
    pub fn acquisitions(&self) -> (&[u64], &[u64]) {
        (&self.a, &self.b)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Qualification {
    Supported,
    MissingCoverage,
    FocusUnverified,
    NoStructure,
}

#[derive(Clone, Debug)]
pub struct Ring {
    /// Cycles per input pixel. Divide by physical distance per pixel for cycles
    /// per distance; never infer an optical scale from image width.
    pub frequency: f32,
    /// One half-plane of the real-image spectrum. Windowing still correlates bins.
    pub samples: u32,
    pub power_a: f32,
    pub power_b: f32,
    pub correlation: Option<f32>,
}
#[derive(Clone, Debug)]
pub struct PatchEvidence {
    pub qualification: Qualification,
    pub rings: Vec<Ring>,
    /// Aggregate normalized cross-power in the explicitly selected frequency band.
    pub band_correlation: Option<f32>,
    pub frequency_band: [f32; 2],
    /// Includes DC difference, exposing lighting/exposure changes hidden by FRC.
    pub relative_rms_difference: Option<f32>,
    pub band_amplitude_ratio: Option<f32>,
    pub independent_acquisitions: [usize; 2],
}

pub struct ReproducibilityWorkspace {
    side: usize,
    a: Vec<Complex>,
    b: Vec<Complex>,
    column: Vec<Complex>,
    window: Vec<f32>,
}
impl ReproducibilityWorkspace {
    pub fn reservation_bytes(side: usize) -> Result<usize, &'static str> {
        if !(16..=128).contains(&side) || !side.is_power_of_two() {
            return Err("patch side must be a power of two in 16..128");
        }
        Ok(side * side * (2 * std::mem::size_of::<Complex>() + 4) + side * 128 + 4096)
    }
    pub fn new(side: usize, budget: usize) -> Result<Self, &'static str> {
        if Self::reservation_bytes(side)? > budget {
            return Err("reproducibility patch exceeds memory budget");
        }
        let window = (0..side * side)
            .map(|i| {
                let x = i % side;
                let y = i / side;
                let h = |p: usize| {
                    0.5 - 0.5 * (std::f32::consts::TAU * p as f32 / (side - 1) as f32).cos()
                };
                h(x) * h(y)
            })
            .collect();
        Ok(Self {
            side,
            a: vec![Complex::default(); side * side],
            b: vec![Complex::default(); side * side],
            column: vec![Complex::default(); side],
            window,
        })
    }
    /// All input pixels in a patch must have genuine support. Focus compatibility
    /// is a separate caller-owned qualification, not inferred from correlation.
    #[allow(clippy::too_many_arguments)]
    pub fn compare(
        &mut self,
        a: &[f32],
        b: &[f32],
        valid_a: &[bool],
        valid_b: &[bool],
        focus_compatible: bool,
        pair: &IndependentPair,
        band: [f32; 2],
    ) -> Result<PatchEvidence, &'static str> {
        let n = self.side * self.side;
        if a.len() != n
            || b.len() != n
            || valid_a.len() != n
            || valid_b.len() != n
            || !band[0].is_finite()
            || !band[1].is_finite()
            || band[0] < 0.0
            || band[0] >= band[1]
            || band[1] > 0.5
        {
            return Err("invalid reproducibility patch or band");
        }
        let mut out = PatchEvidence {
            qualification: if focus_compatible {
                Qualification::Supported
            } else {
                Qualification::FocusUnverified
            },
            rings: Vec::new(),
            band_correlation: None,
            frequency_band: band,
            relative_rms_difference: None,
            band_amplitude_ratio: None,
            independent_acquisitions: [pair.a.len(), pair.b.len()],
        };
        if !valid_a.iter().all(|v| *v) || !valid_b.iter().all(|v| *v) {
            out.qualification = Qualification::MissingCoverage;
            return Ok(out);
        }
        if a.iter().chain(b).any(|v| !v.is_finite()) {
            return Err("nonfinite supported diagnostic sample");
        }
        let weight = self.window.iter().sum::<f32>();
        // Subtract a fixed origin before summation: a constant nonzero image
        // must remain exactly zero after DC removal despite f32 sum rounding.
        let ma = a
            .iter()
            .zip(&self.window)
            .map(|(v, w)| (v - a[0]) * w)
            .sum::<f32>()
            / weight;
        let mb = b
            .iter()
            .zip(&self.window)
            .map(|(v, w)| (v - b[0]) * w)
            .sum::<f32>()
            / weight;
        let mut difference = 0.0;
        let mut intensity = 0.0;
        for i in 0..n {
            self.a[i] = Complex {
                re: ((a[i] - a[0]) - ma) * self.window[i],
                im: 0.0,
            };
            self.b[i] = Complex {
                re: ((b[i] - b[0]) - mb) * self.window[i],
                im: 0.0,
            };
            difference += (a[i] - b[i]).powi(2) * self.window[i];
            intensity += (a[i] * a[i] + b[i] * b[i]) * self.window[i];
        }
        if ![ma, mb, difference, intensity]
            .iter()
            .all(|v| v.is_finite())
        {
            return Err("diagnostic arithmetic overflow");
        }
        out.relative_rms_difference =
            (intensity > 0.0).then(|| (2.0 * difference / intensity).sqrt());
        fft2(&mut self.a, self.side, &mut self.column);
        fft2(&mut self.b, self.side, &mut self.column);
        let mut bins = vec![[0.0_f32; 3]; self.side / 2 + 1];
        let mut counts = vec![0u32; bins.len()];
        for y in 0..=self.side / 2 {
            for x in 0..self.side {
                if y == 0 && (x == 0 || x > self.side / 2) {
                    continue;
                }
                if y == self.side / 2 && x > self.side / 2 {
                    continue;
                }
                let sx = if x <= self.side / 2 {
                    x as f32
                } else {
                    x as f32 - self.side as f32
                };
                let sy = y as f32;
                let radius = (sx * sx + sy * sy).sqrt();
                if radius > self.side as f32 * 0.5 {
                    continue;
                }
                let ring = radius.round() as usize;
                let aa = self.a[y * self.side + x];
                let bb = self.b[y * self.side + x];
                bins[ring][0] += aa.power();
                bins[ring][1] += bb.power();
                bins[ring][2] += aa.re * bb.re + aa.im * bb.im;
                counts[ring] += 1;
            }
        }
        let mut aggregate = [0.0_f32; 3];
        for k in 1..bins.len() {
            let v = bins[k];
            if !v.iter().all(|v| v.is_finite()) {
                return Err("nonfinite diagnostic spectrum");
            }
            let frequency = k as f32 / self.side as f32;
            if frequency >= band[0] && frequency <= band[1] {
                for j in 0..3 {
                    aggregate[j] += v[j];
                }
            }
            out.rings.push(Ring {
                frequency,
                samples: counts[k],
                power_a: v[0],
                power_b: v[1],
                correlation: correlation(v),
            });
        }
        out.band_correlation = correlation(aggregate);
        out.band_amplitude_ratio = (aggregate[0] > 0.0 && aggregate[1] > 0.0)
            .then(|| (aggregate[1] / aggregate[0]).sqrt());
        if out.band_correlation.is_none() {
            out.qualification = Qualification::NoStructure;
        }
        Ok(out)
    }
}
fn correlation(v: [f32; 3]) -> Option<f32> {
    if v[0] > 0.0 && v[1] > 0.0 {
        let denominator = v[0].sqrt() * v[1].sqrt();
        (denominator.is_finite() && denominator > 0.0)
            .then(|| (v[2] / denominator).clamp(-1.0, 1.0))
    } else {
        None
    }
}
fn fft2(data: &mut [Complex], side: usize, column: &mut [Complex]) {
    for row in data.chunks_exact_mut(side) {
        fft(row);
    }
    for x in 0..side {
        for y in 0..side {
            column[y] = data[y * side + x];
        }
        fft(column);
        for y in 0..side {
            data[y * side + x] = column[y];
        }
    }
}
fn fft(data: &mut [Complex]) {
    let n = data.len();
    let mut j = 0;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if i < j {
            data.swap(i, j);
        }
    }
    let mut len = 2;
    while len <= n {
        let angle = -std::f32::consts::TAU / len as f32;
        let wr = angle.cos();
        let wi = angle.sin();
        for start in (0..n).step_by(len) {
            let mut ur = 1.0;
            let mut ui = 0.0;
            for k in 0..len / 2 {
                let a = data[start + k];
                let b = data[start + k + len / 2];
                let br = b.re * ur - b.im * ui;
                let bi = b.re * ui + b.im * ur;
                data[start + k] = Complex {
                    re: a.re + br,
                    im: a.im + bi,
                };
                data[start + k + len / 2] = Complex {
                    re: a.re - br,
                    im: a.im - bi,
                };
                let next = ur * wr - ui * wi;
                ui = ur * wi + ui * wr;
                ur = next;
            }
        }
        len *= 2;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn noise(seed: u64, n: usize) -> Vec<f32> {
        let mut s = seed;
        (0..n)
            .map(|_| {
                s = s.wrapping_mul(6364136223846793005).wrapping_add(1);
                ((s >> 40) as f32 / (1u32 << 24) as f32 - 0.5) * 3.0_f32.sqrt() * 2.0
            })
            .collect()
    }
    fn compare(a: &[f32], b: &[f32]) -> PatchEvidence {
        let n = a.len();
        ReproducibilityWorkspace::new(64, 1 << 20)
            .unwrap()
            .compare(
                a,
                b,
                &vec![true; n],
                &vec![true; n],
                true,
                &IndependentPair::new(&[1], &[2]).unwrap(),
                [0.08, 0.4],
            )
            .unwrap()
    }
    #[test]
    fn a_flat_and_independent_noise_do_not_become_repeated_detail() {
        for value in [0.0, 100.0, -1.5, 12345.0] {
            let flat = vec![value; 4096];
            assert_eq!(
                compare(&flat, &flat).qualification,
                Qualification::NoStructure
            );
        }
        let values: Vec<_> = (0..32)
            .map(|i| {
                compare(&noise(4 * i + 2, 4096), &noise(4 * i + 3, 4096))
                    .band_correlation
                    .unwrap()
            })
            .collect();
        assert!(values.iter().all(|v| v.abs() < 0.15));
        assert!(values.iter().sum::<f32>().abs() / 32.0 < 0.02);
    }
    #[test]
    fn shared_structure_survives_independent_noise_and_displacement_reduces_agreement() {
        let signal = noise(91, 4096);
        let a: Vec<_> = signal
            .iter()
            .zip(noise(123, 4096))
            .map(|(v, n)| v * 5.0 + n)
            .collect();
        let b: Vec<_> = signal
            .iter()
            .zip(noise(221, 4096))
            .map(|(v, n)| v * 5.0 + n)
            .collect();
        let same = compare(&a, &b);
        assert!(same.band_correlation.unwrap() > 0.9);
        let shifted: Vec<_> = (0..4096)
            .map(|i| b[(i / 64) * 64 + (i % 64 + 1) % 64])
            .collect();
        assert!(
            compare(&a, &shifted).band_correlation.unwrap() < same.band_correlation.unwrap() - 0.3
        );
    }
    #[test]
    fn shared_fixed_pattern_and_common_gain_are_explicit_blind_spots() {
        let pattern = noise(817, 4096);
        let same = compare(&pattern, &pattern);
        assert!(same.band_correlation.unwrap() > 0.9999);
        let gain: Vec<_> = pattern.iter().map(|v| v * 3.0).collect();
        let changed = compare(&pattern, &gain);
        assert!(changed.band_correlation.unwrap() > 0.9999);
        assert!((changed.band_amplitude_ratio.unwrap() - 3.0).abs() < 1e-4);
        assert!(changed.relative_rms_difference.unwrap() > 0.8);
    }
    fn blur(input: &[f32]) -> Vec<f32> {
        (0..4096)
            .map(|i| {
                let x = i % 64;
                let y = i / 64;
                let mut sum = 0.0;
                for dy in 0..3 {
                    for dx in 0..3 {
                        let weight = [1.0, 2.0, 1.0][dx] * [1.0, 2.0, 1.0][dy] / 16.0;
                        sum += weight * input[((y + 63 + dy) % 64) * 64 + (x + 63 + dx) % 64];
                    }
                }
                sum
            })
            .collect()
    }
    #[test]
    fn common_filtering_cannot_be_certified_as_optical_detail() {
        let truth = noise(777, 4096);
        let a: Vec<_> = truth
            .iter()
            .zip(noise(3, 4096))
            .map(|(v, n)| v * 5.0 + n)
            .collect();
        let b: Vec<_> = truth
            .iter()
            .zip(noise(5, 4096))
            .map(|(v, n)| v * 5.0 + n)
            .collect();
        let ba = blur(&a);
        let bb = blur(&b);
        let common = compare(&ba, &bb);
        assert!(common.band_correlation.unwrap() > 0.85);
        let one = compare(&a, &bb);
        assert!(one.band_amplitude_ratio.unwrap() < 0.6);
        let energy = |a: &[f32]| a.iter().map(|v| v * v).sum::<f32>();
        assert!(energy(&ba) < energy(&a) * 0.3);
        // High repeatability persists after deliberately discarding most signal
        // energy. The UI must keep power/transfer alongside correlation.
    }
    #[test]
    fn identity_coverage_focus_and_memory_qualifications_are_independent() {
        assert!(IndependentPair::new(&[1, 2], &[2, 3]).is_err());
        assert!(IndependentPair::new(&[1, 1], &[2]).is_err());
        assert!(ReproducibilityWorkspace::new(64, 4).is_err());
        let a = noise(13, 4096);
        let pair = IndependentPair::new(&[1], &[2]).unwrap();
        let mut w = ReproducibilityWorkspace::new(64, 1 << 20).unwrap();
        let mut valid = vec![true; 4096];
        assert_eq!(
            w.compare(&a, &a, &valid, &valid, false, &pair, [0.08, 0.4])
                .unwrap()
                .qualification,
            Qualification::FocusUnverified
        );
        valid[43] = false;
        assert_eq!(
            w.compare(&a, &a, &valid, &valid, true, &pair, [0.08, 0.4])
                .unwrap()
                .qualification,
            Qualification::MissingCoverage
        );
    }
    #[test]
    fn fft_is_commissioned_against_direct_transform_and_parseval() {
        let values = noise(1, 16);
        let mut data: Vec<_> = values.iter().map(|&re| Complex { re, im: 0.0 }).collect();
        fft(&mut data);
        for (k, got) in data.iter().enumerate() {
            let mut expected = Complex::default();
            for (i, &v) in values.iter().enumerate() {
                let angle = -std::f32::consts::TAU * (i * k) as f32 / 16.0;
                expected.re += v * angle.cos();
                expected.im += v * angle.sin();
            }
            assert!((got.re - expected.re).abs() < 0.0001);
            assert!((got.im - expected.im).abs() < 0.0001);
        }
        assert!(
            (data.iter().map(|v| v.power()).sum::<f32>() / 16.0
                - values.iter().map(|v| v * v).sum::<f32>())
            .abs()
                < 0.0001
        );
    }
}
