//! Color-managed exports. Settings belong to the export, not the development recipe.
use crate::{DevelopmentRecipe, ImageOrigin, LinearImage, OutputColorSpace};
use anyhow::{Context, Result, ensure};
use image::ImageEncoder;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::{
    io::{BufWriter, Write},
    path::Path,
    sync::atomic::{AtomicBool, Ordering},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum ExportFormat {
    #[default]
    Avif,
    Tiff,
    Png,
    Jpeg,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct ExportSettings {
    pub format: ExportFormat,
    pub color_space: OutputColorSpace,
    pub hdr: bool,
    /// Highest supported codec quality is 100. JPEG/AVIF remain lossy.
    pub quality: u8,
    /// AV1 effort tradeoff: 0 is slowest, 10 is fastest. Can affect quality.
    pub speed: u8,
}
impl Default for ExportSettings {
    fn default() -> Self {
        Self {
            format: ExportFormat::Avif,
            color_space: OutputColorSpace::Rec2020,
            hdr: true,
            quality: 100,
            speed: 6,
        }
    }
}
impl ExportSettings {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            (1..=100).contains(&self.quality),
            "export quality must be 1..100"
        );
        ensure!(self.speed <= 10, "AVIF speed must be 0..10");
        ensure!(
            !self.hdr || self.format == ExportFormat::Avif,
            "HDR export requires AVIF; TIFF, PNG and JPEG exports are SDR"
        );
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportReport {
    pub width: u32,
    pub height: u32,
    pub format: ExportFormat,
    pub color_space: OutputColorSpace,
    pub hdr: bool,
    pub bit_depth: u8,
    pub bytes: u64,
    pub hdr_metadata: Option<crate::HdrExportReport>,
}

pub(crate) fn check_cancel(cancel: &AtomicBool) -> Result<()> {
    ensure!(!cancel.load(Ordering::Relaxed), "export cancelled");
    Ok(())
}

/// Keeps the established SDR preview appearance. This transforms display colors;
/// selecting wider primaries does not manufacture additional source gamut.
pub(crate) fn sdr_pixel(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    space: OutputColorSpace,
    i: usize,
) -> [f32; 3] {
    let p = image.display_pixel(i, recipe);
    if space == OutputColorSpace::Srgb {
        return p;
    }
    space
        .convert_from_linear_srgb(p.map(crate::color::decode_srgb))
        .map(crate::image::srgb_encode)
}

/// Publish a complete new file, never replacing an existing name. Cancellation
/// is checked during development and before publication. Codec calls themselves
/// are not interruptible; their result is discarded if cancellation arrives.
pub fn export_image(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    cancel: &AtomicBool,
) -> Result<ExportReport> {
    export_image_with_coverage(path, image, recipe, settings, cancel, None)
}

/// Preserve an explicit final binary coverage mask as straight alpha. This
/// mask is already the consumer's final support; export performs no erosion.
/// Formats without supported alpha delivery refuse before creating any file.
pub fn export_image_with_coverage(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    cancel: &AtomicBool,
    coverage: Option<&[u8]>,
) -> Result<ExportReport> {
    check_cancel(cancel)?;
    settings.validate()?;
    image.validate()?;
    if let Some(mask) = coverage {
        ensure!(
            mask.len() == image.width as usize * image.height as usize
                && mask.iter().all(|&v| v == 0 || v == 255),
            "Coverage must match the photograph and contain binary 0/255 support"
        );
        ensure!(
            matches!(settings.format, ExportFormat::Tiff | ExportFormat::Png) && !settings.hdr,
            "This photograph has transparent coverage. Choose SDR TIFF or PNG to preserve it; JPEG and AVIF delivery do not currently retain this mask"
        );
    }
    recipe.validate()?;
    image.validate_source_repairs(recipe)?;
    ensure!(
        !settings.hdr || image.origin == ImageOrigin::SceneLinear,
        "HDR export requires a scene-linear master; a clipped SDR photograph cannot recover HDR"
    );
    ensure!(
        !path.try_exists()?,
        "destination already exists: {}",
        path.display()
    );
    let hdr_metadata = if settings.format == ExportFormat::Avif {
        let report = crate::avif::export_avif(path, image, recipe, settings, cancel)?;
        settings.hdr.then_some(report)
    } else {
        save_sdr(path, image, recipe, settings, cancel, coverage)?;
        None
    };
    Ok(ExportReport {
        width: image.width,
        height: image.height,
        format: settings.format,
        color_space: settings.color_space,
        hdr: settings.hdr,
        bit_depth: match settings.format {
            ExportFormat::Avif => 10,
            ExportFormat::Jpeg => 8,
            _ => 16,
        },
        bytes: path.metadata()?.len(),
        hdr_metadata,
    })
}

fn save_sdr(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    cancel: &AtomicBool,
    coverage: Option<&[u8]>,
) -> Result<()> {
    let mut pixels = vec![0u16; image.pixels.len()];
    pixels
        .par_chunks_mut(image.width as usize * 3)
        .enumerate()
        .try_for_each(|(y, row)| -> Result<()> {
            check_cancel(cancel)?;
            for (x, out) in row.as_chunks_mut::<3>().0.iter_mut().enumerate() {
                let p = sdr_pixel(
                    image,
                    recipe,
                    settings.color_space,
                    y * image.width as usize + x,
                );
                ensure!(
                    p.iter().all(|v| v.is_finite()),
                    "development produced non-finite output samples"
                );
                for c in 0..3 {
                    out[c] = (p[c].clamp(0.0, 1.0) * 65535.0 + 0.5) as u16;
                }
            }
            Ok(())
        })?;
    let profile = crate::icc::icc_output_v2(settings.color_space, false);
    crate::publish::new_file_checked(
        path,
        |file| {
            check_cancel(cancel)?;
            let mut buffered = BufWriter::new(file);
            match settings.format {
                ExportFormat::Tiff => {
                    use tiff::{
                        encoder::{TiffEncoder, colortype},
                        tags::Tag,
                    };
                    let description = format!(
                        "{} primaries, D65, sRGB transfer; Strehl development recipe: {}",
                        settings.color_space.label(),
                        serde_json::to_string(recipe)?
                    );
                    macro_rules! write_tiff {
                        ($color:ty, $data:expr) => {{
                            let mut encoder = TiffEncoder::new(&mut buffered)?;
                            let mut output =
                                encoder.new_image::<$color>(image.width, image.height)?;
                            output
                                .encoder()
                                .write_tag(Tag::ImageDescription, description.as_str())?;
                            output
                                .encoder()
                                .write_tag(Tag::Software, "Strehl development v1")?;
                            output
                                .encoder()
                                .write_tag(Tag::IccProfile, crate::image::IccBytes(&profile))?;
                            if coverage.is_some() {
                                output
                                    .encoder()
                                    .write_tag(Tag::ExtraSamples, &[2_u16][..])?;
                            }
                            output.write_data($data)?;
                        }};
                    }
                    if let Some(mask) = coverage {
                        let rgba = rgba16(&pixels, mask);
                        write_tiff!(colortype::RGBA16, &rgba);
                    } else {
                        write_tiff!(colortype::RGB16, &pixels);
                    }
                }
                ExportFormat::Png => {
                    let rgba = coverage.map(|mask| rgba16(&pixels, mask));
                    let bytes: Vec<u8> = rgba
                        .as_deref()
                        .unwrap_or(&pixels)
                        .iter()
                        .flat_map(|v| v.to_ne_bytes())
                        .collect();
                    let mut encoder = image::codecs::png::PngEncoder::new(&mut buffered);
                    encoder.set_icc_profile(profile)?;
                    encoder.write_image(
                        &bytes,
                        image.width,
                        image.height,
                        if coverage.is_some() {
                            image::ExtendedColorType::Rgba16
                        } else {
                            image::ExtendedColorType::Rgb16
                        },
                    )?;
                }
                ExportFormat::Jpeg => {
                    let bytes: Vec<u8> = pixels
                        .iter()
                        .map(|&v| ((u32::from(v) + 128) / 257) as u8)
                        .collect();
                    let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(
                        &mut buffered,
                        settings.quality,
                    );
                    encoder.set_icc_profile(profile)?;
                    encoder.write_image(
                        &bytes,
                        image.width,
                        image.height,
                        image::ExtendedColorType::Rgb8,
                    )?;
                }
                ExportFormat::Avif => unreachable!("AVIF has its own encoder"),
            }
            buffered
                .flush()
                .context("flushing completed image export")?;
            check_cancel(cancel)
        },
        || check_cancel(cancel),
    )
}

fn rgba16(rgb: &[u16], coverage: &[u8]) -> Vec<u16> {
    rgb.chunks_exact(3)
        .zip(coverage)
        .flat_map(|(p, &a)| [p[0], p[1], p[2], u16::from(a) * 257])
        .collect()
}

#[cfg(test)]
#[path = "export-coverage-tests.rs"]
mod coverage_tests;
