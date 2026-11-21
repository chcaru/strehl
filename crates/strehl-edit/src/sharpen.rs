//! Output sharpening: a conservative unsharp mask on luminance.
//!
//! Engineering ledger rule 9: a sharpening pass raises gradient energy on
//! featureless ground, so it ships with its flat-ROI control
//! (`tests/export-pipeline.rs`, run first) and its default threshold sits
//! above the noise that control plants. Rule 48: judge it only on native
//! crops of 400 px or smaller. Detail is measured on perceptually coded
//! luminance (sRGB coding for SDR, PQ for HDR), cored by `threshold`, and
//! applied as one gain per pixel, so hue and saturation are unchanged.
use anyhow::{Result, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::sync::atomic::AtomicBool;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OutputSharpening {
    /// Fraction of the cored detail added back, 0..=2.
    pub amount: f32,
    /// Gaussian sigma of the detail scale, in output pixels, 0.3..=4.
    pub radius_px: f32,
    /// Coring in coded units (0..=0.25): detail below it is left alone.
    pub threshold: f32,
}

impl Default for OutputSharpening {
    fn default() -> Self {
        Self {
            amount: 0.5,
            radius_px: 0.8,
            // MEASURED (tests/export-pipeline.rs sweep, 2026-11-21): at 0.016 a
            // flat field with 8 % noise gains 0.27 % gradient energy and a
            // 1-2 px edge 6.7 %; at 0.012 the same field gains 4.85 %.
            threshold: 0.016,
        }
    }
}

impl OutputSharpening {
    pub fn validate(&self) -> Result<()> {
        super::recipe_bounded(self.amount, 0.0, 2.0, "sharpening amount")?;
        super::recipe_bounded(self.radius_px, 0.3, 4.0, "sharpening radius")?;
        super::recipe_bounded(self.threshold, 0.0, 0.25, "sharpening threshold")
    }
}

/// Perceptual coding of luminance for the detail measure.
#[derive(Clone, Copy)]
pub(crate) enum Coding {
    /// Display-referred linear 0..1, sRGB-coded.
    Srgb,
    /// Absolute light in nits, PQ-coded.
    Pq,
}

impl Coding {
    fn encode(self, y: f32) -> f32 {
        match self {
            Self::Srgb => crate::image::srgb_encode(y),
            Self::Pq => crate::avif::pq_encode(y),
        }
    }

    fn decode(self, v: f32) -> f32 {
        match self {
            Self::Srgb => crate::image::srgb_decode(v.clamp(0.0, 1.0)),
            Self::Pq => crate::avif::pq_decode(v.clamp(0.0, 1.0)),
        }
    }
}

fn gaussian(sigma: f32) -> Vec<f32> {
    let radius = (3.0 * sigma).ceil().max(1.0) as i32;
    let raw: Vec<f32> = (-radius..=radius)
        .map(|i| (-(i * i) as f32 / (2.0 * sigma * sigma)).exp())
        .collect();
    let sum: f32 = raw.iter().sum();
    raw.into_iter().map(|w| w / sum).collect()
}

fn blur(values: &[f32], width: usize, height: usize, kernel: &[f32]) -> Vec<f32> {
    let r = (kernel.len() / 2) as i64;
    let mut rows = vec![0.0f32; values.len()];
    rows.par_chunks_mut(width).enumerate().for_each(|(y, out)| {
        let src = &values[y * width..(y + 1) * width];
        for (x, o) in out.iter_mut().enumerate() {
            *o = kernel
                .iter()
                .enumerate()
                .map(|(k, w)| {
                    w * src[(x as i64 + k as i64 - r).clamp(0, width as i64 - 1) as usize]
                })
                .sum();
        }
    });
    let mut out = vec![0.0f32; values.len()];
    out.par_chunks_mut(width).enumerate().for_each(|(y, row)| {
        for (k, w) in kernel.iter().enumerate() {
            let sy = (y as i64 + k as i64 - r).clamp(0, height as i64 - 1) as usize;
            for (o, s) in row.iter_mut().zip(&rows[sy * width..(sy + 1) * width]) {
                *o += w * s;
            }
        }
    });
    out
}

/// Sharpen linear RGB in place. `luminance` gives Y in the output primaries.
pub(crate) fn sharpen(
    pixels: &mut [f32],
    size: [u32; 2],
    settings: &OutputSharpening,
    coding: Coding,
    luminance: impl Fn([f32; 3]) -> f32 + Sync,
    cancel: &AtomicBool,
) -> Result<()> {
    let [w, h] = size.map(|v| v as usize);
    ensure!(pixels.len() == w * h * 3, "sharpening extent mismatch");
    if settings.amount <= 0.0 {
        return Ok(());
    }
    crate::export::check_cancel(cancel)?;
    let coded: Vec<f32> = pixels
        .par_chunks(3)
        .map(|p| coding.encode(luminance([p[0], p[1], p[2]]).max(0.0)))
        .collect();
    let blurred = blur(&coded, w, h, &gaussian(settings.radius_px));
    crate::export::check_cancel(cancel)?;
    pixels
        .par_chunks_mut(3)
        .zip(coded.par_iter().zip(&blurred))
        .for_each(|(p, (&l, &b))| {
            let detail = l - b;
            let cored = detail.signum() * (detail.abs() - settings.threshold).max(0.0);
            if cored == 0.0 {
                return;
            }
            let y = luminance([p[0], p[1], p[2]]);
            if y.is_nan() || y <= 1e-6 {
                return;
            }
            let target = coding.decode(l + settings.amount * cored);
            let gain = (target / y).clamp(0.5, 2.0);
            for v in p.iter_mut() {
                *v *= gain;
            }
        });
    Ok(())
}
