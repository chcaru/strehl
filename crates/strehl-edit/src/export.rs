//! Color-managed exports. Settings belong to the export, not the development recipe.
use crate::{
    DevelopmentRecipe, ExportDateTime, ExportMetadata, ImageOrigin, LinearImage, OutputColorSpace,
    OutputSharpening, Resize,
    export_pipeline::{
        Buffer, Domain, Layout, StageReport, Stages, develop_buffer, run_stages, sdr_value,
    },
    metadata,
    scale_bar::ScaleBarReport,
};
use anyhow::{Context, Result, ensure};
use image::ImageEncoder;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::{
    borrow::Cow,
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

fn is_false(value: &bool) -> bool {
    !*value
}

/// Every field added after the first five is omitted when unused, so settings
/// that use none of them serialize as before (catalog export history, agent
/// snapshot) and earlier builds read them.
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
    /// Write the development recipe into a TIFF's ImageDescription. Off by
    /// default (implementation plan P0 item 11); nothing reads it back.
    #[serde(skip_serializing_if = "is_false")]
    pub embed_recipe: bool,
    /// Artist, copyright and description to write into the file.
    #[serde(skip_serializing_if = "ExportMetadata::is_empty")]
    pub metadata: ExportMetadata,
    /// Fit within a long edge, in linear light. Never enlarges.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resize: Option<Resize>,
    /// Output sharpening after any resize (engineering ledger rules 9, 48).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sharpen: Option<OutputSharpening>,
    /// Burn in the recipe's scale bar; needs the subject's calibration.
    #[serde(skip_serializing_if = "is_false")]
    pub scale_bar: bool,
}
impl Default for ExportSettings {
    fn default() -> Self {
        Self {
            format: ExportFormat::Avif,
            color_space: OutputColorSpace::Rec2020,
            hdr: true,
            quality: 100,
            speed: 6,
            embed_recipe: false,
            metadata: ExportMetadata::default(),
            resize: None,
            sharpen: None,
            scale_bar: false,
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
        ensure!(
            !self.embed_recipe || self.format == ExportFormat::Tiff,
            "the development recipe can be written into TIFF exports only"
        );
        self.metadata.validate()?;
        if let Some(resize) = &self.resize {
            resize.validate()?;
        }
        if let Some(sharpen) = &self.sharpen {
            sharpen.validate()?;
        }
        Ok(())
    }
}

/// Inputs an export needs beyond its settings: none of them is a setting a
/// preset can carry.
#[derive(Debug, Clone, Copy, Default)]
pub struct ExportExtras<'a> {
    /// Final binary coverage (0/255 per source pixel), kept as straight alpha.
    pub coverage: Option<&'a [u8]>,
    /// The subject's scale calibration, micrometres per source pixel.
    pub um_per_px: Option<f64>,
    /// Written as DateTime / xmp:CreateDate when given.
    pub date_time: Option<ExportDateTime>,
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
    /// Size after the crop and before the resize, when a resize ran.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resized_from: Option<[u32; 2]>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub crop: Option<crate::Crop>,
    #[serde(default, skip_serializing_if = "is_false")]
    pub sharpened: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub scale_bar: Option<ScaleBarReport>,
    /// Metadata containers written: `tiff-tags`, `xmp`, `exif`, `png-text`,
    /// `recipe`. PNG, JPEG and AVIF always carry the Strehl stamp (`png-text`
    /// and `xmp`, `exif` and `xmp`, `exif`); a TIFF's is its Software tag.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub metadata: Vec<String>,
}

pub(crate) fn check_cancel(cancel: &AtomicBool) -> Result<()> {
    ensure!(!cancel.load(Ordering::Relaxed), "export cancelled");
    Ok(())
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
    export_image_with(
        path,
        image,
        recipe,
        settings,
        &ExportExtras::default(),
        cancel,
    )
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
    let extras = ExportExtras {
        coverage,
        ..Default::default()
    };
    export_image_with(path, image, recipe, settings, &extras, cancel)
}

/// The full export: crop and straighten from the recipe, the neighbourhood
/// stage, resize, sharpening, scale bar and metadata from the settings.
pub fn export_image_with(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    extras: &ExportExtras<'_>,
    cancel: &AtomicBool,
) -> Result<ExportReport> {
    check_cancel(cancel)?;
    settings.validate()?;
    image.validate()?;
    if let Some(mask) = extras.coverage {
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
    if let Some(date) = &extras.date_time {
        date.validate()?;
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
    let layout = Layout::new(image, recipe.crop.as_ref(), settings.resize.as_ref())?;
    ensure!(
        extras.coverage.is_none() || !layout.resized(),
        "transparent coverage cannot be resized yet; export it at full size"
    );
    let stages = Stages::new(recipe, settings, &layout, extras.um_per_px)?;
    // Heals and backdrop run on the master's samples before development.
    let staged = image.with_neighbourhood(recipe);
    let source: Cow<'_, LinearImage> = staged.map_or(Cow::Borrowed(image), Cow::Owned);
    let job = Job {
        image: &source,
        recipe,
        settings,
        extras,
        layout: &layout,
        stages: &stages,
        cancel,
    };
    let (hdr_metadata, staged, written) = if settings.format == ExportFormat::Avif {
        let (report, staged, written) = crate::avif::export_avif_job(path, &job)?;
        (settings.hdr.then_some(report), staged, written)
    } else {
        let (staged, written) = save_sdr(path, &job)?;
        (None, staged, written)
    };
    Ok(ExportReport {
        width: layout.output[0],
        height: layout.output[1],
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
        resized_from: layout.resized().then_some(layout.developed),
        crop: recipe.crop,
        sharpened: staged.as_ref().is_some_and(|s| s.sharpened),
        scale_bar: staged.and_then(|s| s.scale_bar),
        metadata: written,
    })
}

/// One export's inputs, resolved.
pub(crate) struct Job<'a> {
    pub image: &'a LinearImage,
    pub recipe: &'a DevelopmentRecipe,
    pub settings: &'a ExportSettings,
    pub extras: &'a ExportExtras<'a>,
    pub layout: &'a Layout,
    pub stages: &'a Stages,
    pub cancel: &'a AtomicBool,
}

impl Job<'_> {
    /// The staged buffer when any stage runs; `None` for the fused path.
    pub(crate) fn staged_buffer(&self, domain: Domain) -> Result<Option<(Buffer, StageReport)>> {
        if !self.stages.any(self.layout) {
            return Ok(None);
        }
        let prepared = self.recipe.prepare();
        let coverage = self.extras.coverage;
        let mut buffer = develop_buffer(
            self.image,
            &prepared,
            domain,
            self.layout,
            coverage,
            self.cancel,
        )?;
        let report = run_stages(&mut buffer, self.layout, self.stages, domain, self.cancel)?;
        Ok(Some((buffer, report)))
    }
}

/// The TIFF ImageDescription. Without a description and with the recipe
/// switch on, this is the exact pre-P7 text.
fn tiff_description(settings: &ExportSettings, recipe: &DevelopmentRecipe) -> Result<String> {
    let colour = format!(
        "{} primaries, D65, sRGB transfer",
        settings.color_space.label()
    );
    let described = metadata::ascii_text(&settings.metadata.description.replace('\n', " "));
    Ok(match (described.is_empty(), settings.embed_recipe) {
        (true, false) => colour,
        (true, true) => format!(
            "{colour}; Strehl development recipe: {}",
            metadata::json_ascii(recipe)?
        ),
        (false, false) => described,
        (false, true) => format!(
            "{described}\nStrehl development recipe: {}",
            metadata::json_ascii(recipe)?
        ),
    })
}

fn save_sdr(path: &Path, job: &Job<'_>) -> Result<(Option<StageReport>, Vec<String>)> {
    let settings = job.settings;
    let image = job.image;
    let [width, height] = job.layout.output;
    let domain = Domain::Sdr(settings.color_space);
    let (pixels, alpha, staged) = match job.staged_buffer(domain)? {
        Some((buffer, report)) => {
            let mut pixels = vec![0u16; buffer.pixels.len()];
            pixels
                .par_chunks_mut(buffer.size[0] as usize * 3)
                .enumerate()
                .for_each(|(y, row)| {
                    for (x, out) in row.as_chunks_mut::<3>().0.iter_mut().enumerate() {
                        let p = buffer.coded(y * buffer.size[0] as usize + x);
                        for c in 0..3 {
                            out[c] = (p[c].clamp(0.0, 1.0) * 65535.0 + 0.5) as u16;
                        }
                    }
                });
            (pixels, buffer.alpha, Some(report))
        }
        None => {
            // Fused: development straight into codes, as before P7.
            let prepared = job.recipe.prepare();
            let layout = job.layout;
            let mut pixels = vec![0u16; width as usize * height as usize * 3];
            pixels
                .par_chunks_mut(width as usize * 3)
                .enumerate()
                .try_for_each(|(y, row)| -> Result<()> {
                    check_cancel(job.cancel)?;
                    for (x, out) in row.as_chunks_mut::<3>().0.iter_mut().enumerate() {
                        let (raw, uv) = layout.sample(image, x as u32, y as u32);
                        let p = sdr_value(image, &prepared, settings.color_space, raw, uv);
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
            let alpha = job.extras.coverage.map(|mask| {
                (0..height)
                    .flat_map(|y| (0..width).map(move |x| (x, y)))
                    .map(|(x, y)| mask[layout.nearest(image, x, y)])
                    .collect::<Vec<u8>>()
            });
            (pixels, alpha, None)
        }
    };
    let coverage = alpha.as_deref();
    let meta = &settings.metadata;
    let date = job.extras.date_time.as_ref();
    // Always built: it carries the Strehl stamp (`xmp:CreatorTool`).
    let xmp = metadata::xmp_packet(meta, date)?;
    let described = metadata::has_text(meta, date);
    let mut written = Vec::new();
    let profile = crate::icc::icc_output_v2(settings.color_space, false);
    crate::publish::new_file_checked(
        path,
        |file| {
            check_cancel(job.cancel)?;
            let mut buffered = BufWriter::new(file);
            match settings.format {
                ExportFormat::Tiff => {
                    use tiff::{
                        encoder::{TiffEncoder, colortype},
                        tags::Tag,
                    };
                    let description = tiff_description(settings, job.recipe)?;
                    let artist = metadata::ascii_text(&meta.artist);
                    let copyright = metadata::ascii_text(&meta.copyright);
                    let stamp = date.map(|d| d.tiff());
                    macro_rules! write_tiff {
                        ($color:ty, $data:expr) => {{
                            let mut encoder = TiffEncoder::new(&mut buffered)?;
                            let mut output = encoder.new_image::<$color>(width, height)?;
                            output
                                .encoder()
                                .write_tag(Tag::ImageDescription, description.as_str())?;
                            output
                                .encoder()
                                .write_tag(Tag::Software, "Strehl development v1")?;
                            output
                                .encoder()
                                .write_tag(Tag::IccProfile, crate::image::IccBytes(&profile))?;
                            if !artist.is_empty() {
                                output.encoder().write_tag(Tag::Artist, artist.as_str())?;
                            }
                            if !copyright.is_empty() {
                                output
                                    .encoder()
                                    .write_tag(Tag::Copyright, copyright.as_str())?;
                            }
                            if let Some(stamp) = &stamp {
                                output.encoder().write_tag(Tag::DateTime, stamp.as_str())?;
                            }
                            // Software (305) above is the TIFF's Strehl stamp,
                            // so the packet is written only with text or a date.
                            if described {
                                // TIFF tag 700, XMLPacket, as BYTE.
                                output
                                    .encoder()
                                    .write_tag(Tag::Unknown(700), xmp.as_slice())?;
                            }
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
                    if described {
                        written.push("tiff-tags".to_owned());
                        written.push("xmp".to_owned());
                    }
                    if settings.embed_recipe {
                        written.push("recipe".to_owned());
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
                    let color = if coverage.is_some() {
                        image::ExtendedColorType::Rgba16
                    } else {
                        image::ExtendedColorType::Rgb16
                    };
                    let mut chunks = metadata::png_software_chunk();
                    chunks.extend_from_slice(&metadata::png_xmp_chunk(&xmp));
                    let mut inserter = metadata::PngChunkInserter::new(&mut buffered, chunks);
                    let mut encoder = image::codecs::png::PngEncoder::new(&mut inserter);
                    encoder.set_icc_profile(profile)?;
                    encoder.write_image(&bytes, width, height, color)?;
                    inserter.finish()?;
                    written.push("png-text".to_owned());
                    written.push("xmp".to_owned());
                }
                ExportFormat::Jpeg => {
                    let bytes: Vec<u8> = pixels
                        .iter()
                        .map(|&v| ((u32::from(v) + 128) / 257) as u8)
                        .collect();
                    let mut inserter = metadata::JpegSegmentInserter::new(
                        &mut buffered,
                        metadata::jpeg_xmp_segment(&xmp)?,
                    );
                    let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(
                        &mut inserter,
                        settings.quality,
                    );
                    encoder.set_icc_profile(profile)?;
                    encoder.set_exif_metadata(metadata::exif_block(meta, date))?;
                    encoder.write_image(&bytes, width, height, image::ExtendedColorType::Rgb8)?;
                    inserter.finish()?;
                    written.push("exif".to_owned());
                    written.push("xmp".to_owned());
                }
                ExportFormat::Avif => unreachable!("AVIF has its own encoder"),
            }
            buffered
                .flush()
                .context("flushing completed image export")?;
            check_cancel(job.cancel)
        },
        || check_cancel(job.cancel),
    )?;
    Ok((staged, written))
}

fn rgba16(rgb: &[u16], coverage: &[u8]) -> Vec<u16> {
    rgb.as_chunks::<3>()
        .0
        .iter()
        .zip(coverage)
        .flat_map(|(p, &a)| [p[0], p[1], p[2], u16::from(a) * 257])
        .collect()
}

#[cfg(test)]
#[path = "export-coverage-tests.rs"]
mod coverage_tests;
