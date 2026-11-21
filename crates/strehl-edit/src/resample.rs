//! Export resampling in linear light.
//!
//! The `image` crate's `resize` was not used: for `f32` pixels it clamps every
//! output sample to 0..1 (`imageops/sample.rs`, `clamp(t, min, max)` with the
//! `f32` default range), which would clip HDR light and highlight headroom.
//! This is a separable filter whose support widens with the reduction ratio,
//! so downscaling is anti-aliased; samples are never clamped.
use anyhow::{Result, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::sync::atomic::AtomicBool;

/// The reconstruction filter. Mitchell-Netravali (B = C = 1/3) is the default:
/// a downscale with Lanczos 3 adds edge overshoot the master does not contain
/// (engineering ledger rule 48 measured a 5x Lanczos inventing +33 DN halos).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ResizeFilter {
    #[default]
    Mitchell,
    Lanczos3,
}

impl ResizeFilter {
    fn support(self) -> f64 {
        match self {
            Self::Mitchell => 2.0,
            Self::Lanczos3 => 3.0,
        }
    }

    fn weight(self, x: f64) -> f64 {
        let x = x.abs();
        match self {
            Self::Mitchell => {
                let (b, c) = (1.0 / 3.0, 1.0 / 3.0);
                if x < 1.0 {
                    ((12.0 - 9.0 * b - 6.0 * c) * x.powi(3)
                        + (-18.0 + 12.0 * b + 6.0 * c) * x * x
                        + (6.0 - 2.0 * b))
                        / 6.0
                } else if x < 2.0 {
                    ((-b - 6.0 * c) * x.powi(3)
                        + (6.0 * b + 30.0 * c) * x * x
                        + (-12.0 * b - 48.0 * c) * x
                        + (8.0 * b + 24.0 * c))
                        / 6.0
                } else {
                    0.0
                }
            }
            Self::Lanczos3 => {
                if x < 1e-12 {
                    1.0
                } else if x < 3.0 {
                    let px = std::f64::consts::PI * x;
                    3.0 * px.sin() * (px / 3.0).sin() / (px * px)
                } else {
                    0.0
                }
            }
        }
    }
}

/// Fit within a long edge; never enlarges.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Resize {
    pub long_edge: u32,
    #[serde(default)]
    pub filter: ResizeFilter,
}

impl Resize {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            (16..=65_535).contains(&self.long_edge),
            "resize long edge must be 16..65535 pixels"
        );
        Ok(())
    }

    /// Output size for a developed size, or `None` when no reduction is due.
    pub fn target(&self, size: [u32; 2]) -> Option<[u32; 2]> {
        let long = size[0].max(size[1]);
        if long <= self.long_edge {
            return None;
        }
        let scale = f64::from(self.long_edge) / f64::from(long);
        Some(size.map(|n| ((f64::from(n) * scale).round() as u32).max(1)))
    }
}

struct Taps {
    start: usize,
    weights: Vec<f64>,
    /// Exact sum of `weights`; dividing by it keeps a constant exactly constant.
    sum: f64,
}

fn taps(source: usize, target: usize, filter: ResizeFilter) -> Vec<Taps> {
    let ratio = source as f64 / target as f64;
    let scale = ratio.max(1.0);
    let support = filter.support() * scale;
    (0..target)
        .map(|o| {
            let centre = (o as f64 + 0.5) * ratio;
            let left = ((centre - support).floor().max(0.0) as usize).min(source - 1);
            let right = ((centre + support).ceil() as usize).clamp(left + 1, source);
            let raw: Vec<f64> = (left..right)
                .map(|i| filter.weight((i as f64 + 0.5 - centre) / scale))
                .collect();
            let sum: f64 = raw.iter().sum();
            let weights = if sum.abs() > 1e-12 {
                raw
            } else {
                // Degenerate window: nearest sample.
                let mut w = vec![0.0; raw.len()];
                let nearest = ((centre - 0.5).round().max(0.0) as usize).clamp(left, right - 1);
                w[nearest - left] = 1.0;
                w
            };
            let sum = weights.iter().sum();
            Taps {
                start: left,
                weights,
                sum,
            }
        })
        .collect()
}

/// Resample interleaved RGB from `from` to `to` pixels.
pub(crate) fn resize_rgb(
    pixels: &[f32],
    from: [u32; 2],
    to: [u32; 2],
    filter: ResizeFilter,
    cancel: &AtomicBool,
) -> Result<Vec<f32>> {
    let [sw, sh] = from.map(|v| v as usize);
    let [dw, dh] = to.map(|v| v as usize);
    ensure!(
        pixels.len() == sw * sh * 3 && dw > 0 && dh > 0,
        "resize extent mismatch"
    );
    let horizontal = taps(sw, dw, filter);
    let vertical = taps(sh, dh, filter);
    let mut rows = vec![0.0f32; sh * dw * 3];
    rows.par_chunks_mut(dw * 3)
        .enumerate()
        .try_for_each(|(y, out)| -> Result<()> {
            crate::export::check_cancel(cancel)?;
            let src = &pixels[y * sw * 3..(y + 1) * sw * 3];
            for (o, tap) in horizontal.iter().enumerate() {
                let mut acc = [0.0f64; 3];
                for (k, &w) in tap.weights.iter().enumerate() {
                    let i = (tap.start + k) * 3;
                    for c in 0..3 {
                        acc[c] += w * f64::from(src[i + c]);
                    }
                }
                for c in 0..3 {
                    out[o * 3 + c] = (acc[c] / tap.sum) as f32;
                }
            }
            Ok(())
        })?;
    let mut out = vec![0.0f32; dw * dh * 3];
    out.par_chunks_mut(dw * 3)
        .zip(vertical.par_iter())
        .try_for_each(|(row, tap)| -> Result<()> {
            crate::export::check_cancel(cancel)?;
            let mut acc = vec![0.0f64; row.len()];
            for (k, &w) in tap.weights.iter().enumerate() {
                let src = &rows[(tap.start + k) * dw * 3..(tap.start + k + 1) * dw * 3];
                for (v, s) in acc.iter_mut().zip(src) {
                    *v += w * f64::from(*s);
                }
            }
            for (v, a) in row.iter_mut().zip(acc) {
                *v = (a / tap.sum) as f32;
            }
            Ok(())
        })?;
    Ok(out)
}

/// Catmull-Rom sample at continuous index coordinates (pixel `i` has its centre
/// at `i`), with edge pixels repeated. Exact at pixel centres.
pub(crate) fn catmull_rom(pixels: &[f32], width: u32, height: u32, x: f64, y: f64) -> [f32; 3] {
    let weights = |t: f64| {
        let t2 = t * t;
        let t3 = t2 * t;
        [
            (-t3 + 2.0 * t2 - t) * 0.5,
            (3.0 * t3 - 5.0 * t2 + 2.0) * 0.5,
            (-3.0 * t3 + 4.0 * t2 + t) * 0.5,
            (t3 - t2) * 0.5,
        ]
    };
    let (fx, fy) = (x.floor(), y.floor());
    let (wx, wy) = (weights(x - fx), weights(y - fy));
    let (ix, iy) = (fx as i64, fy as i64);
    let clamp = |v: i64, n: u32| v.clamp(0, i64::from(n) - 1) as usize;
    let mut acc = [0.0f64; 3];
    for (j, wyj) in wy.iter().enumerate() {
        let row = clamp(iy + j as i64 - 1, height) * width as usize;
        for (i, wxi) in wx.iter().enumerate() {
            let at = (row + clamp(ix + i as i64 - 1, width)) * 3;
            let w = wxi * wyj;
            for c in 0..3 {
                acc[c] += w * f64::from(pixels[at + c]);
            }
        }
    }
    acc.map(|v| v as f32)
}

#[cfg(test)]
#[path = "resample-tests.rs"]
mod tests;
