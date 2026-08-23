//! The semi-synthetic deep stack used as control `P4`.
//!
//! One real frame is warped by a **planted** per-frame similarity and blurred by
//! a planted depth-dependent defocus, so that long-baseline pairs decorrelate
//! the way they do on the real 105-frame stack. The transforms are known
//! exactly, so this is the only test in M10 with absolute ground truth for the
//! whole path from ARW to global solution.
//!
//! **Resampler disclosure (SYNTHESIS §5 item 11).** The `Warp` flavour uses
//! bilinear interpolation, whose transfer function depends on sub-pixel phase,
//! so it plants a sharpness modulation nobody asked for. That is why this
//! control is used for *recovery* only and never as evidence about defocus, and
//! why the `IntegerShift` flavour exists: whole-pixel translation touches no
//! interpolator at all, so it bounds the resampler's contribution directly.

use crate::align::Fit;
use crate::plane::{bilinear, Plane};
use rayon::prelude::*;

/// xorshift64*, so the controls are bit-reproducible from a seed.
pub struct Rng(pub u64);

impl Rng {
    pub fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.0 = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    pub fn unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / 9007199254740992.0)
    }
    pub fn next_f32(&mut self) -> f32 {
        self.unit() as f32
    }
    pub fn normal(&mut self) -> f32 {
        let u1 = self.unit().max(1e-12);
        let u2 = self.unit();
        ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
    }
}

fn gauss_blur(p: &Plane, sigma: f32) -> Plane {
    if sigma <= 1e-3 {
        return Plane {
            d: p.d.clone(),
            w: p.w,
            h: p.h,
        };
    }
    let r = (3.0 * sigma).ceil() as isize;
    let k: Vec<f32> = (-r..=r)
        .map(|i| (-0.5 * (i as f32 / sigma).powi(2)).exp())
        .collect();
    let ks: f32 = k.iter().sum();
    let k: Vec<f32> = k.iter().map(|v| v / ks).collect();

    let (w, h) = (p.w, p.h);
    let mut tmp = vec![0f32; w * h];
    tmp.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let mut s = 0f32;
            for (t, kv) in k.iter().enumerate() {
                let xx = (x as isize + t as isize - r).clamp(0, w as isize - 1) as usize;
                s += *kv * p.d[y * w + xx];
            }
            *o = s;
        }
    });
    let mut out = vec![0f32; w * h];
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let mut s = 0f32;
            for (t, kv) in k.iter().enumerate() {
                let yy = (y as isize + t as isize - r).clamp(0, h as isize - 1) as usize;
                s += *kv * tmp[yy * w + x];
            }
            *o = s;
        }
    });
    Plane { d: out, w, h }
}

/// Blur levels the spatially-varying blur interpolates between. Deeper than
/// M6's ladder because a 105-frame sweep puts a tile 100 frames from its own
/// focus, and the point of this control is that far pairs genuinely fail.
const BLUR_LEVELS: [f32; 6] = [0.0, 1.0, 2.2, 4.0, 7.0, 11.0];

/// A smooth depth field in `[0, n-1]`: a diagonal ramp plus three Gaussian
/// blobs, so depth is deliberately **not** an affine function of position.
pub fn depth_field(w: usize, h: usize, n: usize) -> Vec<f32> {
    let blobs = [
        (0.25f32, 0.30f32, 0.22f32, 0.85f32),
        (0.72, 0.62, 0.18, -0.75),
        (0.45, 0.85, 0.26, 0.55),
    ];
    let mut d = vec![0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let (u, v) = (x as f32 / w as f32, y as f32 / h as f32);
            let mut t = 0.30 * u + 0.18 * v;
            for (bx, by, br, ba) in blobs {
                let r2 = ((u - bx).powi(2) + (v - by).powi(2)) / (br * br);
                t += ba * (-r2).exp();
            }
            d[y * w + x] = t;
        }
    }
    let (mut lo, mut hi) = (f32::INFINITY, f32::NEG_INFINITY);
    for v in &d {
        lo = lo.min(*v);
        hi = hi.max(*v);
    }
    let span = (hi - lo).max(1e-6);
    for v in d.iter_mut() {
        *v = (*v - lo) / span * (n - 1) as f32;
    }
    d
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Flavour {
    /// Similarity warp by bilinear resampling. Realistic; carries the resampler.
    Warp,
    /// Whole-pixel translation only. No interpolation anywhere, and the true
    /// scale is exactly zero, so any scale a solver returns is bias.
    IntegerShift,
}

pub struct SynthSpec {
    pub n: usize,
    pub flavour: Flavour,
    /// Total scale change across the stack, e.g. -0.04575 to match `coffee-bean`.
    pub g_total: f32,
    /// Curvature of the magnification law. `0` is linear in frame index; larger
    /// values bend it, because equal focus steps are not equal magnification
    /// steps (M3 §4).
    pub curve: f32,
    /// Per-frame independent wobble on `g`, in units of `g`. Deliberately
    /// non-smooth, so a low-order polynomial in frame index cannot be exactly
    /// right and candidate (c) is not validated by construction.
    pub g_wobble: f32,
    /// Per-frame independent wobble on translation, in plane px.
    pub t_wobble: f32,
    /// Scale centre offset from the plane centre, in plane px.
    pub centre: (f32, f32),
    /// Total rotation across the stack, in radians.
    pub rot_total: f32,
    /// Defocus sigma in plane px per frame of separation from best focus.
    pub blur_per_frame: f32,
    pub gain: f32,
    pub rn_e: f32,
    pub seed: u64,
}

/// The planted transform of frame `k`, taking frame-0 coordinates to frame `k`.
pub fn truth_fit(s: &SynthSpec, k: usize) -> Fit {
    let t = k as f32 / (s.n - 1).max(1) as f32;
    // A saturating, non-polynomial magnification law.
    let shape = if s.curve.abs() < 1e-6 {
        t
    } else {
        (1.0 - (-s.curve * t).exp()) / (1.0 - (-s.curve).exp())
    };
    let mut rng = Rng(s.seed ^ 0xA5A5_5A5A_1234_9876u64.wrapping_mul(k as u64 + 1));
    let g = s.g_total * shape + s.g_wobble * rng.normal();
    let r = s.rot_total * shape;
    if s.flavour == Flavour::IntegerShift {
        // Pure translation, whole pixels: a copy, not a resample.
        let px = (s.g_total * shape * 400.0).round();
        let py = (s.g_total * shape * -260.0).round();
        return Fit {
            ax: px,
            ay: py,
            g: 0.0,
            r: 0.0,
        };
    }
    Fit {
        ax: -g * s.centre.0 + r * s.centre.1 + s.t_wobble * rng.normal(),
        ay: -r * s.centre.0 - g * s.centre.1 + s.t_wobble * rng.normal(),
        g,
        r,
    }
}

/// Build the synthetic focus bracket.
pub fn synth_stack(base: &Plane, depth: &[f32], s: &SynthSpec) -> Vec<Plane> {
    let (w, h) = (base.w, base.h);
    let (cx, cy) = (w as f32 * 0.5, h as f32 * 0.5);
    (0..s.n)
        .map(|k| {
            let truth = truth_fit(s, k);
            let mut warped = vec![0f32; w * h];
            if s.flavour == Flavour::IntegerShift {
                let (sx, sy) = (truth.ax as i64, truth.ay as i64);
                warped.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                    let src_y = (y as i64 - sy).clamp(0, h as i64 - 1) as usize;
                    for (x, o) in row.iter_mut().enumerate() {
                        let src_x = (x as i64 - sx).clamp(0, w as i64 - 1) as usize;
                        *o = base.d[src_y * w + src_x];
                    }
                });
            } else {
                warped.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                    for (x, o) in row.iter_mut().enumerate() {
                        let (sx, sy) = truth.inv_at(x as f32, y as f32, cx, cy);
                        *o = bilinear(base, sx, sy);
                    }
                });
            }
            let warped = Plane { d: warped, w, h };

            let mut out = if s.blur_per_frame <= 0.0 {
                warped
            } else {
                let levels: Vec<Plane> = BLUR_LEVELS
                    .iter()
                    .map(|sg| gauss_blur(&warped, *sg))
                    .collect();
                let mut mixed = vec![0f32; w * h];
                mixed.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                    for (x, o) in row.iter_mut().enumerate() {
                        let i = y * w + x;
                        let sig = (s.blur_per_frame * (k as f32 - depth[i]).abs())
                            .min(BLUR_LEVELS[BLUR_LEVELS.len() - 1]);
                        let mut lo = 0;
                        while lo + 2 < BLUR_LEVELS.len() && BLUR_LEVELS[lo + 1] < sig {
                            lo += 1;
                        }
                        let (a, b) = (BLUR_LEVELS[lo], BLUR_LEVELS[lo + 1]);
                        let t = ((sig - a) / (b - a)).clamp(0.0, 1.0);
                        *o = levels[lo].d[i] * (1.0 - t) + levels[lo + 1].d[i] * t;
                    }
                });
                Plane { d: mixed, w, h }
            };

            // Fresh sensor noise on every frame, so the blurred frames are not
            // also the quiet ones.
            let mut rng = Rng(s.seed ^ (0x9E37_79B9_7F4A_7C15u64.wrapping_mul(k as u64 + 1)));
            let read_dn = s.rn_e * s.gain;
            for v in out.d.iter_mut() {
                let sigma = (0.5 * (s.gain * v.max(0.0) + read_dn * read_dn)).sqrt();
                *v += sigma * rng.normal();
            }
            out
        })
        .collect()
}
