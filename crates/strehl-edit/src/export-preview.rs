//! The pixels an SDR export will contain, for the desktop's Export view.
//!
//! This runs the export's own staged buffer (`Job::staged_buffer`: crop and
//! straighten, heals and backdrop, development, resize, output sharpening,
//! burned-in scale bar), then codes it exactly as the SDR encoders do: 16-bit
//! codes, reduced to 8 bits as the JPEG path reduces them. It always renders
//! sRGB primaries, which a display shows directly; for an sRGB export the
//! values equal the file's, for Display P3 or Rec.2020 they are the same
//! colours before the export's primaries conversion. Codec loss (JPEG, AVIF)
//! is not simulated.
use crate::{
    DevelopmentRecipe, ExportExtras, ExportSettings, LinearImage, OutputColorSpace,
    export::{Job, check_cancel},
    export_pipeline::{Domain, Layout, Stages},
};
use anyhow::Result;
use rayon::prelude::*;
use std::{borrow::Cow, sync::atomic::AtomicBool};

pub struct ExportPreview {
    /// Output size: the crop, then any resize.
    pub size: [u32; 2],
    /// sRGB-coded 8-bit RGB, row-major.
    pub rgb: Vec<u8>,
    /// Size after the crop, before any resize.
    pub developed: [u32; 2],
}

/// The output pixels of an SDR export whose stages change them, or `None`
/// when the export is the development itself (no resize, sharpening or
/// burned-in scale bar), so a development of the photograph is already exact.
pub fn render_export_preview(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    extras: &ExportExtras<'_>,
    cancel: &AtomicBool,
) -> Result<Option<ExportPreview>> {
    check_cancel(cancel)?;
    settings.validate()?;
    image.validate()?;
    recipe.validate()?;
    let layout = Layout::new(image, recipe.crop.as_ref(), settings.resize.as_ref())?;
    let stages = Stages::new(recipe, settings, &layout, extras.um_per_px)?;
    if !stages.any(&layout) {
        return Ok(None);
    }
    // Heals and backdrop run on the master's samples before development.
    let staged = image.with_neighbourhood(recipe);
    let source: Cow<'_, LinearImage> = staged.map_or(Cow::Borrowed(image), Cow::Owned);
    let extras = ExportExtras {
        coverage: None,
        ..*extras
    };
    let job = Job {
        image: &source,
        recipe,
        settings,
        extras: &extras,
        layout: &layout,
        stages: &stages,
        cancel,
    };
    let Some((buffer, _)) = job.staged_buffer(Domain::Sdr(OutputColorSpace::Srgb))? else {
        return Ok(None);
    };
    check_cancel(cancel)?;
    let mut rgb = vec![0u8; buffer.pixels.len()];
    rgb.par_chunks_mut(buffer.size[0] as usize * 3)
        .enumerate()
        .for_each(|(y, row)| {
            for (x, out) in row.as_chunks_mut::<3>().0.iter_mut().enumerate() {
                let p = buffer.coded(y * buffer.size[0] as usize + x);
                for c in 0..3 {
                    // `save_sdr`'s 16-bit code, then its JPEG reduction.
                    let code = (p[c].clamp(0.0, 1.0) * 65535.0 + 0.5) as u16;
                    out[c] = ((u32::from(code) + 128) / 257) as u8;
                }
            }
        });
    Ok(Some(ExportPreview {
        size: buffer.size,
        rgb,
        developed: layout.developed,
    }))
}

#[cfg(test)]
#[path = "export-preview-tests.rs"]
mod tests;
