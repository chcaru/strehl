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
pub fn add_noise(src: &[f32], noise: &NoiseModel, scale: f32, seed: u64, out: &mut [f32]) {
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
        let s = self
            .blur_sigma(0)
            .max(self.blur_sigma(self.frames.saturating_sub(1)));
        (3.0 * s).ceil() as usize
    }
}

/// Build the planted stack from one base plane.
pub fn plant(
    base: &[f32],
    geom: PlaneGeometry,
    noise: &NoiseModel,
    spec: PlantSpec,
) -> Vec<Vec<f32>> {
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
                        .wrapping_mul(0x0100_0000_01B3)
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
/// ever meets a sensor.
///
/// Build the planted stack from one base plane, with a **tilted** depth
/// surface: `w_true(x) = w_true + tilt * (x - x_centre) / 256`.
/// Rendered by layered defocus — the base is blurred once per integer defocus
/// step `d`, and each pixel linearly interpolates between the two bracketing
/// steps. Interpolating *blurred images* rather than resampling geometry keeps
/// SYNTHESIS §5 item 11's trap (resampling artefacts masquerading as signal)
/// out of the design: nothing is ever shifted, only mixed. The mix is exact
/// wherever the depth is locally constant and is a first-order approximation
/// across the ramp, whose gradient is set deliberately small.
///
/// Returns the frames and the per-pixel ground truth over the **ROI**.
#[allow(clippy::too_many_arguments)]
pub fn plant_tilted(
    base: &[f32],
    geom: PlaneGeometry,
    noise: &NoiseModel,
    spec: PlantSpec,
    tilt: f32,
    roi_x0: usize,
    roi_y0: usize,
    roi_w: usize,
    roi_h: usize,
) -> (Vec<Vec<f32>>, Vec<f32>) {
    let n = geom.pixels();
    let xc = 0.5 * geom.width as f32;
    let w_at = |x: usize| -> f32 {
        (spec.w_true as f32 + tilt * (x as f32 - xc) / 256.0).clamp(0.0, spec.frames as f32 - 1.0)
    };

    // The bank of blurs, indexed by integer defocus step.
    let max_d = spec.frames;
    let bank: Vec<Vec<f32>> = (0..=max_d)
        .map(|d| {
            let mut out = vec![0.0f32; n];
            gaussian_blur(base, geom, spec.sigma0 + spec.alpha * d as f32, &mut out);
            out
        })
        .collect();

    let frames = (0..spec.frames)
        .map(|k| {
            let mut frame = vec![0.0f32; n];
            for y in 0..geom.height {
                for x in 0..geom.width {
                    let d = (k as f32 - w_at(x)).abs().min(max_d as f32 - 1e-3);
                    let lo = d.floor() as usize;
                    let f = d - lo as f32;
                    let q = y * geom.width + x;
                    frame[q] = (1.0 - f) * bank[lo][q] + f * bank[lo + 1][q];
                }
            }
            if spec.noise_scale > 0.0 {
                let mut noisy = vec![0.0f32; n];
                add_noise(
                    &frame,
                    noise,
                    spec.noise_scale,
                    spec.seed
                        .wrapping_mul(0x0100_0000_01B3)
                        .wrapping_add(k as u64 + 1),
                    &mut noisy,
                );
                frame = noisy;
            }
            frame
        })
        .collect();

    let truth = (0..roi_h)
        .flat_map(|j| (0..roi_w).map(move |i| (i, j)))
        .map(|(i, _j)| w_at(roi_x0 + i))
        .collect::<Vec<f32>>();
    let _ = roi_y0;
    (frames, truth)
}

/// A deterministic, broadband synthetic texture for the noiseless positive
/// control.
///
/// **Why not a sum of sinusoids.** The first version of this function summed
/// four sinusoid products. It failed its own positive control: a bandpass
/// response at a pixel is `sum_j c_j exp(-sigma^2 k_j^2 / 2)` over the
/// components present there, and with only a handful of components the `c_j`
/// carry coherent signs, so cancellation puts a zero crossing at an interior
/// `sigma` and `|response|` stops being monotone in blur. Whole nodal *lines*
/// of the product texture then vote for the most-defocused frame. That is a
/// defect of the control texture, not of the operator — but it makes the
/// control useless.
///
/// A broadband random field has spatially incoherent component signs, content
/// at every scale a 1 px stencil or a 12 px ring can see, and no nodal
/// structure, so `|response|` is monotone in `sigma` essentially everywhere.
/// The field is generated from a fixed seed, so the control is reproducible.
pub fn synthetic_texture(geom: PlaneGeometry, base_dn: f32, amplitude: f32) -> Vec<f32> {
    let n = geom.pixels();
    let mut rng = Rng::new(0x5EED_0F0C);
    let white: Vec<f32> = (0..n).map(|_| rng.normal()).collect();

    // Octaves from 1 px to ~16 px with 1/f amplitude, which is roughly the
    // spectrum of natural imagery and gives every operator in the set
    // something to see at its own scale.
    let mut acc = vec![0.0f32; n];
    let mut tmp = vec![0.0f32; n];
    for (sigma, w) in [
        (0.0f32, 1.0f32),
        (1.0, 1.4),
        (2.0, 2.0),
        (4.0, 2.8),
        (8.0, 4.0),
    ] {
        if sigma == 0.0 {
            for i in 0..n {
                acc[i] += w * white[i];
            }
        } else {
            gaussian_blur(&white, geom, sigma, &mut tmp);
            // A blurred white field loses variance as ~1/(2*sqrt(pi)*sigma) per
            // axis; rescale so every octave contributes comparably before the
            // 1/f weighting is applied.
            let gain = 2.0 * std::f32::consts::PI.sqrt() * sigma;
            for i in 0..n {
                acc[i] += w * gain * tmp[i];
            }
        }
    }
    let mean = acc.iter().map(|v| *v as f64).sum::<f64>() / n as f64;
    let var = acc
        .iter()
        .map(|v| (*v as f64 - mean) * (*v as f64 - mean))
        .sum::<f64>()
        / n as f64;
    let sd = var.sqrt().max(1e-12) as f32;
    acc.iter()
        .map(|v| base_dn + amplitude * (v - mean as f32) / sd)
        .collect()
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
