//! A resampler-free synthetic test field.
//!
//! `P1b` plants warps by bilinearly resampling a real frame, which is exactly
//! the trap SYNTHESIS section 5 item 11 records: bilinear resampling plants a
//! sub-pixel-phase sharpness modulation that a correlation estimator reads like
//! defocus. That makes it useless for asking whether the estimator shrinks a
//! *tiny* scale change, because the resampler's own phase-dependent blur is the
//! same size as the effect.
//!
//! This module sidesteps the trap completely. Both frames are point samples of
//! the **same continuous band-limited function**, one on the integer grid and
//! one on the transformed grid. No image is ever resampled, so there is no
//! interpolator anywhere in the loop and any bias found is the estimator's own.
//!
//! The field is a sum of sinusoids with an isotropic, roughly `1/f` amplitude
//! spectrum, band-limited well inside Nyquist so the point samples are alias
//! free. That is not a photograph, but it is a fair test of a shift estimator:
//! it has broadband detail everywhere, no defocus difference between the two
//! frames, and an exactly known transform.

use crate::align::Fit;
use crate::plane::Plane;
use crate::synth::Rng;
use rayon::prelude::*;

pub struct Field {
    /// `(u, v, phase, amp)` per component, frequencies in cycles per plane px.
    comps: Vec<(f32, f32, f32, f32)>,
}

impl Field {
    /// `n_comp` components with `|nu|` log-uniform in `[lo, hi]` cycles/px and
    /// amplitude proportional to `1/|nu|`.
    pub fn new(n_comp: usize, lo: f32, hi: f32, seed: u64) -> Self {
        let mut rng = Rng(seed);
        let mut comps = Vec::with_capacity(n_comp);
        for _ in 0..n_comp {
            let t = rng.next_f32();
            let nu = lo * (hi / lo).powf(t);
            let th = rng.next_f32() * std::f32::consts::TAU;
            comps.push((
                nu * th.cos(),
                nu * th.sin(),
                rng.next_f32() * std::f32::consts::TAU,
                1.0 / nu,
            ));
        }
        // Normalise so the field has unit variance regardless of `n_comp`.
        let p: f32 = comps.iter().map(|c| 0.5 * c.3 * c.3).sum();
        let s = 1.0 / p.sqrt();
        for c in &mut comps {
            c.3 *= s;
        }
        Self { comps }
    }

    fn at(&self, x: f32, y: f32) -> f32 {
        let mut v = 0.0f32;
        for &(u, w, ph, a) in &self.comps {
            v += a * (std::f32::consts::TAU * (u * x + w * y) + ph).cos();
        }
        v
    }

    /// Evaluate the continuous field after an analytic circular Gaussian blur.
    ///
    /// A sinusoid at radial frequency `nu` is attenuated by
    /// `exp(-2*pi^2*sigma^2*nu^2)`. This supplies a defocus mismatch without
    /// putting a geometric interpolator anywhere in the control path.
    fn at_blurred(&self, x: f32, y: f32, sigma: f32) -> f32 {
        if sigma <= 1e-6 {
            return self.at(x, y);
        }
        let mut value = 0.0f32;
        let factor = -2.0 * std::f32::consts::PI.powi(2) * sigma * sigma;
        for &(u, v, phase, amplitude) in &self.comps {
            let attenuation = (factor * (u * u + v * v)).exp();
            value +=
                amplitude * attenuation * (std::f32::consts::TAU * (u * x + v * y) + phase).cos();
        }
        value
    }

    /// Sample the field on the integer grid, optionally transformed by `t`.
    ///
    /// `t` maps reference plane coordinates to moving plane coordinates, so the
    /// moving frame is the field evaluated at `T^-1(p)` — the same convention
    /// `warp_known` uses, but with no interpolation because the field is
    /// continuous.
    ///
    /// `scale` and `offset` put the output in raw ADU, because the estimator's
    /// contrast and peak gates are calibrated for sensor units and a
    /// unit-variance field fails all of them.
    #[allow(clippy::too_many_arguments)]
    pub fn render(
        &self,
        w: usize,
        h: usize,
        t: Option<Fit>,
        scale: f32,
        offset: f32,
        noise: f32,
        rng_seed: u64,
    ) -> Plane {
        self.render_blurred(w, h, t, 0.0, scale, offset, noise, rng_seed)
    }

    /// Point-sample a geometrically transformed, analytically Gaussian-blurred
    /// field. Geometry and blur are both evaluated from the continuous source.
    #[allow(clippy::too_many_arguments)]
    pub fn render_blurred(
        &self,
        w: usize,
        h: usize,
        t: Option<Fit>,
        sigma: f32,
        scale: f32,
        offset: f32,
        noise: f32,
        rng_seed: u64,
    ) -> Plane {
        let (cx, cy) = (w as f32 * 0.5, h as f32 * 0.5);
        let mut d = vec![0f32; w * h];
        d.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
            let mut rng = Rng(rng_seed ^ ((y as u64) << 32) ^ 0x9E37_79B9_7F4A_7C15);
            for (x, o) in row.iter_mut().enumerate() {
                let (sx, sy) = match t {
                    Some(f) => f.inv_at(x as f32, y as f32, cx, cy),
                    None => (x as f32, y as f32),
                };
                let v = offset + scale * self.at_blurred(sx, sy, sigma);
                *o = if noise > 0.0 {
                    v + noise * rng.normal()
                } else {
                    v
                };
            }
        });
        Plane { d, w, h }
    }
}
