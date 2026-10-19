//! Bounded, background decoding of developed images. This module never decodes RAW.

use std::path::{Path, PathBuf};
use std::sync::atomic::Ordering;

use anyhow::{Context, Result, ensure};
use image::{DynamicImage, ImageFormat, ImageReader, imageops::FilterType};

use crate::jobs::{Task, spawn_task};

const MAX_IMAGE_SIDE: u32 = 32_768;
const MAX_IMAGE_PIXELS: u64 = 80_000_000;
const MAX_DECODE_BYTES: u64 = 512 * 1024 * 1024;

pub struct PreviewImage {
    pub path: PathBuf,
    /// Canonical display aperture in source pixels. For developed images this
    /// is their decoded size; source browsing uses the largest embedded JPEG's
    /// dimensions even when a compatible smaller camera preview supplies pixels.
    pub source_size: [u32; 2],
    pub size: [usize; 2],
    pub rgba: Vec<u8>,
    /// True only when the device texture limit required a smaller overview.
    pub is_overview: bool,
}

pub fn load_preview(path: PathBuf, max_texture_side: u32) -> Task<PreviewImage> {
    spawn_task("strehl-preview", move |cancelled| {
        ensure!(
            max_texture_side > 0,
            "The graphics device has no usable texture size"
        );
        ensure!(!cancelled.load(Ordering::Relaxed), "Preview cancelled");
        let image = decode_developed(&path, None)?;
        ensure!(!cancelled.load(Ordering::Relaxed), "Preview cancelled");
        let source_size = [image.width(), image.height()];
        let is_overview = source_size.iter().any(|&side| side > max_texture_side);
        let rgba = if is_overview {
            image
                .resize(max_texture_side, max_texture_side, FilterType::Triangle)
                .into_rgba8()
        } else {
            image.into_rgba8()
        };
        ensure!(!cancelled.load(Ordering::Relaxed), "Preview cancelled");
        Ok(PreviewImage {
            path,
            source_size,
            size: [rgba.width() as usize, rgba.height() as usize],
            rgba: rgba.into_raw(),
            is_overview,
        })
    })
}

/// A successful child exit alone cannot certify a completed image: a fake or
/// failing writer can exit zero with an empty or truncated TIFF. Decode it fully
/// before publication, using the same allocation bounds as the image viewer.
pub(crate) fn validate_tiff(path: &Path) -> Result<()> {
    decode_developed(path, Some(ImageFormat::Tiff)).map(drop)
}

fn reader(path: &Path) -> Result<ImageReader<std::io::BufReader<std::fs::File>>> {
    let mut reader = ImageReader::open(path)
        .with_context(|| format!("Opening {}", path.display()))?
        .with_guessed_format()
        .context("Recognising the image format")?;
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(MAX_IMAGE_SIDE);
    limits.max_image_height = Some(MAX_IMAGE_SIDE);
    limits.max_alloc = Some(MAX_DECODE_BYTES);
    reader.limits(limits);
    Ok(reader)
}

fn decode_developed(path: &Path, required_format: Option<ImageFormat>) -> Result<DynamicImage> {
    let image_reader = reader(path)?;
    let format = image_reader
        .format()
        .context("The image format is unknown")?;
    ensure!(
        matches!(
            format,
            ImageFormat::Png | ImageFormat::Jpeg | ImageFormat::Tiff
        ),
        "Open a developed TIFF, PNG or JPEG image"
    );
    if let Some(required) = required_format {
        ensure!(
            format == required,
            "The render did not produce a TIFF image"
        );
    }
    let (width, height) = image_reader
        .into_dimensions()
        .context("Reading image dimensions")?;
    validate_dimensions(width, height)?;
    reader(path)?
        .decode()
        .context("Decoding the complete image")
}

fn validate_dimensions(width: u32, height: u32) -> Result<()> {
    ensure!(width > 0 && height > 0, "The image has no pixels");
    ensure!(
        width <= MAX_IMAGE_SIDE && height <= MAX_IMAGE_SIDE,
        "The image exceeds the viewer's {MAX_IMAGE_SIDE}-pixel side limit"
    );
    ensure!(
        u64::from(width) * u64::from(height) <= MAX_IMAGE_PIXELS,
        "The image exceeds the viewer's {MAX_IMAGE_PIXELS}-pixel allocation limit"
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::jobs::tests::TestDirectory;

    #[test]
    fn zero_and_oversized_dimensions_are_rejected_before_rgba_allocation() {
        // Adversaries: an empty dimension, a long narrow image, and a square
        // that fits the side limit but exceeds the independent pixel limit.
        assert!(validate_dimensions(0, 10).is_err());
        assert!(validate_dimensions(MAX_IMAGE_SIDE + 1, 1).is_err());
        assert!(validate_dimensions(10_000, 10_000).is_err());
        assert!(validate_dimensions(7_032, 4_688).is_ok());
    }

    #[test]
    fn native_preview_preserves_pixel_values_and_device_limit_marks_overview() {
        let directory = TestDirectory::new("preview");
        let path = directory.path().join("reference.png");
        let mut pixels = image::RgbaImage::new(5, 3);
        pixels.put_pixel(4, 2, image::Rgba([12, 89, 241, 255]));
        pixels.save(&path).unwrap();
        let native = load_preview(path.clone(), 8)
            .receiver
            .recv()
            .unwrap()
            .unwrap();
        assert!(!native.is_overview);
        assert_eq!(native.size, [5, 3]);
        assert_eq!(&native.rgba[56..60], &[12, 89, 241, 255]);
        let overview = load_preview(path, 4).receiver.recv().unwrap().unwrap();
        assert!(overview.is_overview);
        assert_eq!(overview.source_size, [5, 3]);
        assert!(overview.size.iter().all(|&side| side <= 4));
    }

    #[test]
    fn render_validation_rejects_truncated_tiff_and_png_disguised_as_tiff() {
        let directory = TestDirectory::new("invalid-preview");
        let truncated = directory.path().join("truncated.tiff");
        std::fs::write(&truncated, b"II*\0\x08\0\0\0").unwrap();
        assert!(validate_tiff(&truncated).is_err());
        let disguised = directory.path().join("disguised.tiff");
        image::RgbaImage::new(2, 2)
            .save_with_format(&disguised, ImageFormat::Png)
            .unwrap();
        assert!(validate_tiff(&disguised).is_err());
        let valid = directory.path().join("valid.tiff");
        image::RgbImage::new(2, 2).save(&valid).unwrap();
        validate_tiff(&valid).unwrap();
    }
}
