//! Bounded viewport development. Source pixels remain f32 and annotations keep
//! their full-photograph coordinates. Native-size requests never resample.
use crate::{DevelopmentRecipe, ImageOrigin, LinearImage};
use anyhow::{Result, ensure};
use rayon::prelude::*;
use std::sync::atomic::{AtomicBool, Ordering};

/// Source rows per band when the neighbourhood stage runs.
const NEIGHBOURHOOD_BAND: u32 = 256;

/// Integer source-pixel rectangle, maximum excluded, and power-of-two stride.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DisplayRegionRequest {
    pub min: [u32; 2],
    pub max: [u32; 2],
    pub stride: u32,
}

pub struct DisplayRegion {
    pub size: [u32; 2],
    pub region: DisplayRegionRequest,
    pub rgb: Vec<u8>,
    /// Developed linear BT.709, relative to reference white, ready for upload.
    pub rgba_linear: Vec<f32>,
    pub source_samples: u64,
}

impl LinearImage {
    pub fn render_display_region(
        &self,
        recipe: &DevelopmentRecipe,
        region: DisplayRegionRequest,
        cancelled: &AtomicBool,
    ) -> Result<DisplayRegion> {
        self.render_display_region_mode(recipe, region, cancelled, true)
    }

    /// SDR-only presentation does not pay for a second development or float buffer.
    pub fn render_display_region_mode(
        &self,
        recipe: &DevelopmentRecipe,
        region: DisplayRegionRequest,
        cancelled: &AtomicBool,
        include_linear: bool,
    ) -> Result<DisplayRegion> {
        recipe.validate()?;
        if let Some(baseline) = self.baseline {
            baseline.validate()?;
        }
        ensure!(
            self.pixels.len() == crate::image::image_samples(self.width, self.height)?,
            "Invalid source image extent"
        );
        ensure!(
            region.stride.is_power_of_two()
                && region.min[0] < region.max[0]
                && region.min[1] < region.max[1]
                && region.max[0] <= self.width
                && region.max[1] <= self.height,
            "Invalid display region"
        );
        let extent = [region.max[0] - region.min[0], region.max[1] - region.min[1]];
        let size = extent.map(|n| n.div_ceil(region.stride));
        let count = u64::from(size[0]) * u64::from(size[1]);
        ensure!(
            count <= 8 * 1024 * 1024,
            "Display patch exceeds 8 million pixels"
        );
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Display refinement cancelled"
        );
        let mut rgb = vec![0; count as usize * 3];
        // A single unused scalar per row keeps paired Rayon rows disjoint in
        // SDR mode, without allocating a full float photograph.
        let linear_row = if include_linear {
            size[0] as usize * 4
        } else {
            1
        };
        let mut rgba_linear = vec![0.0; size[1] as usize * linear_row];
        let prepared = recipe.prepare();
        let source_row = |y: u32| {
            (
                region.min[1] + (u64::from(y) * u64::from(extent[1]) / u64::from(size[1])) as u32,
                region.min[1]
                    + ((u64::from(y) + 1) * u64::from(extent[1]) / u64::from(size[1])) as u32,
            )
        };
        // Heals and backdrop: the stage output for a band of source rows,
        // computed with its halo, so every pixel equals the export's.
        let stage = recipe
            .has_neighbourhood()
            .then(|| crate::neighbourhood::Neighbourhood::new(self, recipe));
        let band_rows = match &stage {
            Some(_) => (NEIGHBOURHOOD_BAND / region.stride).max(1) as usize,
            None => size[1] as usize,
        };
        let row_bytes = size[0] as usize * 3;
        for (band, (rgb_band, linear_band)) in rgb
            .chunks_mut(band_rows * row_bytes)
            .zip(rgba_linear.chunks_mut(band_rows * linear_row))
            .enumerate()
        {
            let first = (band * band_rows) as u32;
            let rows = (rgb_band.len() / row_bytes) as u32;
            let (top, _) = source_row(first);
            let (_, bottom) = source_row(first + rows - 1);
            let staged = stage
                .as_ref()
                .map(|s| s.region([region.min[0], top, region.max[0], bottom]));
            let staged_width = (region.max[0] - region.min[0]) as usize;
            let fetch = |sx: u32, sy: u32| -> [f32; 3] {
                match &staged {
                    None => {
                        let i = (sy as usize * self.width as usize + sx as usize) * 3;
                        [self.pixels[i], self.pixels[i + 1], self.pixels[i + 2]]
                    }
                    Some(values) => {
                        let i = ((sy - top) as usize * staged_width
                            + (sx - region.min[0]) as usize)
                            * 3;
                        [values[i], values[i + 1], values[i + 2]]
                    }
                }
            };
            rgb_band
                .par_chunks_mut(size[0] as usize * 3)
                .zip(linear_band.par_chunks_mut(linear_row))
                .enumerate()
                .try_for_each(|(row, (sdr, linear))| -> Result<()> {
                    let y = first as usize + row;
                    ensure!(
                        !cancelled.load(Ordering::Relaxed),
                        "Display refinement cancelled"
                    );
                    let y0 = region.min[1]
                        + (y as u64 * u64::from(extent[1]) / u64::from(size[1])) as u32;
                    let y1 = region.min[1]
                        + ((y as u64 + 1) * u64::from(extent[1]) / u64::from(size[1])) as u32;
                    for x in 0..size[0] {
                        if x % 64 == 0 {
                            ensure!(
                                !cancelled.load(Ordering::Relaxed),
                                "Display refinement cancelled"
                            );
                        }
                        let x0 = region.min[0]
                            + (u64::from(x) * u64::from(extent[0]) / u64::from(size[0])) as u32;
                        let x1 = region.min[0]
                            + (u64::from(x + 1) * u64::from(extent[0]) / u64::from(size[0])) as u32;
                        let mut raw = [0.0f32; 3];
                        for sy in y0..y1 {
                            if sy % 16 == 0 {
                                ensure!(
                                    !cancelled.load(Ordering::Relaxed),
                                    "Display refinement cancelled"
                                );
                            }
                            for sx in x0..x1 {
                                let p = fetch(sx, sy);
                                for (c, value) in raw.iter_mut().enumerate() {
                                    *value += p[c];
                                }
                            }
                        }
                        let samples = ((x1 - x0) * (y1 - y0)) as f32;
                        raw = raw.map(|v| v / samples);
                        ensure!(
                            raw.iter().all(|v| v.is_finite()),
                            "Non-finite display sample"
                        );
                        let uv = [
                            (x0 as f32 + x1 as f32) * 0.5 / self.width as f32,
                            (y0 as f32 + y1 as f32) * 0.5 / self.height as f32,
                        ];
                        let display = self.display_sample(raw, uv, &prepared);
                        ensure!(
                            display.iter().all(|v| v.is_finite()),
                            "Non-finite SDR display sample"
                        );
                        let extended = if !include_linear {
                            [0.0; 3]
                        } else if self.origin == ImageOrigin::DisplayReferred {
                            display.map(|v| {
                                if v <= 0.04045 {
                                    v / 12.92
                                } else {
                                    ((v + 0.055) / 1.055).powf(2.4)
                                }
                            })
                        } else {
                            self.developed_sample(raw, uv, &prepared)
                        };
                        ensure!(
                            extended.iter().all(|v| v.is_finite()),
                            "Non-finite developed sample"
                        );
                        let x = x as usize;
                        for c in 0..3 {
                            sdr[x * 3 + c] = (display[c] * 255.0 + 0.5) as u8;
                            if include_linear {
                                linear[x * 4 + c] = extended[c];
                            }
                        }
                        if include_linear {
                            linear[x * 4 + 3] = 1.0;
                        }
                    }
                    Ok(())
                })?;
        }
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Display refinement cancelled"
        );
        if !include_linear {
            rgba_linear.clear();
        }
        Ok(DisplayRegion {
            size,
            region,
            rgb,
            rgba_linear,
            source_samples: u64::from(extent[0]) * u64::from(extent[1]),
        })
    }
}

#[cfg(test)]
#[path = "display-region-tests.rs"]
mod tests;
