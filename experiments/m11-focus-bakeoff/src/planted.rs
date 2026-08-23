//! Planted focus surfaces, and the noise injection both selectivity probes use.
//!
//! # Why a planted stack, and what it is allowed to prove
//!
//! Noise excess is easy to measure because a flat ROI supplies its own ground
//! truth. Selectivity does not: on a real stack nobody knows which frame is
//! genuinely sharpest at a pixel, so every "selectivity" statistic computed on
//! real frames alone is a proxy validated against nothing. Project rule 11
//! requires the opposite order — prove the statistic recovers a **known**
//! answer before pointing it at an unknown one.
//!
//! So the ground-truth half of M11 is a stack whose correct answer is planted:
//! one real frame, blurred by a defocus ladder about a chosen best frame
//! `w_true`, with fresh calibrated noise added per frame. Every pixel's correct
//! winner is `w_true` by construction.
//!
//! # The three things that could make that dishonest, and what is done about
//! each
//!
//! 1. **Resampling.** SYNTHESIS §5 item 11: bilinear interpolation plants a
//!    sharpness modulation that a correlation estimator reads as defocus. So
//!    **nothing here resamples.** The defocus ladder is a symmetric Gaussian
//!    blur applied on the pixel lattice; there are no sub-pixel shifts anywhere
//!    in this module.
//! 2. **Seams from a spatially varying blur.** A planted *depth ramp* would
//!    need a different blur radius per pixel, and a pixel blurred at radius `d`
//!    reads neighbours that "should" have been blurred at some other radius.
//!    So `w_true` is **constant over the tile** — a fronto-parallel subject —
//!    and the blur for each frame is spatially uniform and therefore exactly
//!    correct everywhere.
//! 3. **The in-focus frame being noisier than the defocused ones.** Blurring a
//!    real frame also blurs the sensor noise it already carries, by
//!    `1/sqrt(4*pi*sigma_blur^2)`, so a naive ladder starting at `sigma_blur =
//!    0` hands the in-focus frame more noise than its neighbours and biases
//!    every operator away from the right answer. The ladder therefore starts at
//!    `sigma0 > 0` — the reference stacks are diffraction-limited and genuinely
//!    soft anyway (SYNTHESIS fact 28: marked f/11 is optically f/33) — and the
//!    realised per-frame noise sd is **measured and reported** by
//!    `selftest`/`plant`, not assumed away.

use strehl_core::noise::NoiseModel;
use strehl_core::plane::PlaneGeometry;

/// `splitmix64`, so a run is reproducible from its seed alone and no crate
/// dependency decides what "random" means.
pub struct Rng {
    state: u64,
    spare: Option<f32>,
}

impl Rng {
    pub fn new(seed: u64) -> Self {
        Self {
            state: seed.wrapping_add(0x9E37_79B9_7F4A_7C15),
            spare: None,
        }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Uniform in `(0, 1)`.
    fn unit(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64 + 0.5) / (1u64 << 53) as f64
    }

    /// Standard normal, Box-Muller with the second variate cached.
    pub fn normal(&mut self) -> f32 {
        if let Some(v) = self.spare.take() {
            return v;
        }
        let (u1, u2) = (self.unit(), self.unit());
        let r = (-2.0 * u1.ln()).sqrt();
        let theta = 2.0 * std::f64::consts::PI * u2;
        self.spare = Some((r * theta.sin()) as f32);
        (r * theta.cos()) as f32
    }
}

/// Separable Gaussian blur, replicate-clamped, truncated at 3 sigma.
///
/// No resampling: the kernel is evaluated on the integer lattice and the output
/// grid is the input grid.
pub fn gaussian_blur(src: &[f32], geom: PlaneGeometry, sigma: f32, out: &mut [f32]) {
    if sigma <= 1e-4 {
        out.copy_from_slice(src);
        return;
    }
    let radius = (3.0 * sigma).ceil() as isize;
    let taps: Vec<f32> = (-radius..=radius)
        .map(|d| (-(d as f32 * d as f32) / (2.0 * sigma * sigma)).exp())
        .collect();
    let sum: f32 = taps.iter().sum();
    let taps: Vec<f32> = taps.iter().map(|t| t / sum).collect();

    let (w, h) = (geom.width, geom.height);
    let mut tmp = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut s = 0.0f32;
            for (i, t) in taps.iter().enumerate() {
                let sx = (x as isize + i as isize - radius).clamp(0, w as isize - 1) as usize;
                s += t * src[y * w + sx];
            }
            tmp[y * w + x] = s;
        }
    }
    for y in 0..h {
        for x in 0..w {
            let mut s = 0.0f32;
            for (i, t) in taps.iter().enumerate() {
                let sy = (y as isize + i as isize - radius).clamp(0, h as isize - 1) as usize;
                s += t * tmp[sy * w + x];
            }
            out[y * w + x] = s;
        }
    }
}

/// Add an independent realisation of the calibrated sensor noise.
///
/// `scale` multiplies the model sigma. The sigma is evaluated at the *local
/// signal*, so the injected noise is signal-dependent exactly as shot noise is.
pub fn add_noise(
    src: &[f32],
    noise: &NoiseModel,
    scale: f32,
    seed: u64,
    out: &mut [f32],
) {
    let mut rng = Rng::new(seed);
    for (o, s) in out.iter_mut().zip(src.iter()) {
        let sigma = noise.green_luma_sigma(*s);
        *o = (*s + scale * sigma * rng.normal()).max(0.0);
    }
}

/// A planted defocus ladder.
#[derive(Clone, Copy, Debug)]
pub struct PlantSpec {
    pub frames: usize,
    /// The frame index that is correct at every pixel.
    pub w_true: usize,
    /// Blur sigma of the in-focus frame, in plane px. Must be > 0 — see the
    /// module docs, point 3.
    pub sigma0: f32,
    /// Extra blur sigma per frame of defocus mismatch, in plane px.
    /// `alpha = 0` plants **no** focus information and is the null.
    pub alpha: f32,
    /// Multiplier on the model sigma for the injected noise. `0` is noiseless.
    pub noise_scale: f32,
    pub seed: u64,
}

impl PlantSpec {
    pub fn blur_sigma(&self, k: usize) -> f32 {
        self.sigma0 + self.alpha * (k as isize - self.w_true as isize).unsigned_abs() as f32
    }

    /// Widest blur in the ladder, which is what a tile margin has to clear.
    pub fn max_blur_radius(&self) -> usize {
        let s = self.blur_sigma(0).max(self.blur_sigma(self.frames.saturating_sub(1)));
        (3.0 * s).ceil() as usize
    }
}

/// Build the planted stack from one base plane.
pub fn plant(base: &[f32], geom: PlaneGeometry, noise: &NoiseModel, spec: PlantSpec) -> Vec<Vec<f32>> {
    let mut blurred = vec![0.0f32; geom.pixels()];
    (0..spec.frames)
        .map(|k| {
            let mut frame = vec![0.0f32; geom.pixels()];
            gaussian_blur(base, geom, spec.blur_sigma(k), &mut blurred);
            if spec.noise_scale <= 0.0 {
                frame.copy_from_slice(&blurred);
            } else {
                add_noise(
                    &blurred,
                    noise,
                    spec.noise_scale,
                    spec.seed
                        .wrapping_mul(0x1000_0000_1B3)
                        .wrapping_add(k as u64 + 1),
                    &mut frame,
                );
            }
            frame
        })
        .collect()
}

/// A deterministic multi-scale texture with no sensor noise in it at all.
///
/// Used for the noiseless positive control: an operator that cannot recover a
/// planted focus surface *here* has no focus discrimination to trade away, and
/// a selectivity statistic that cannot see the answer here is broken before it
/// ever meets a sensor. Constructed by summing sinusoids on the lattice, so no
/// resampling and no interpolation is involved.
pub fn synthetic_texture(geom: PlaneGeometry, base_dn: f32, amplitude: f32) -> Vec<f32> {
    let (w, h) = (geom.width, geom.height);
    let mut v = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let (xf, yf) = (x as f32, y as f32);
            let mut s = 0.0f32;
            // Octaves from ~1.5 px to ~40 px, so a wide-support bandpass and a
            // 3x3 stencil both have something to see.
            for (fx, fy, amp) in [
                (2.11f32, 1.87f32, 1.00f32),
                (0.97, 1.29, 0.80),
                (0.41, 0.33, 0.60),
                (0.157, 0.211, 0.45),
            ] {
                s += amp * (xf * fx + 0.7 * yf * fy).sin() * (yf * fy - 0.3 * xf * fx).cos();
            }
            v[y * w + x] = base_dn + amplitude * s;
        }
    }
    v
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blur_preserves_the_mean_of_a_constant_field() {
        let geom = PlaneGeometry {
            width: 33,
            height: 33,
        };
        let src = vec![1234.0f32; geom.pixels()];
        let mut out = vec![0.0f32; geom.pixels()];
        gaussian_blur(&src, geom, 2.5, &mut out);
        assert!(out.iter().all(|v| (v - 1234.0).abs() < 1e-2));
    }
}
