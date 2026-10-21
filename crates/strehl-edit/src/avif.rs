use crate::{DevelopmentRecipe, ExportSettings, ImageOrigin, LinearImage, OutputColorSpace};
use anyhow::{Context as _, Result, bail, ensure};
use rav1e::prelude::*;
use serde::{Deserialize, Serialize};
use std::{
    io::Write,
    path::Path,
    sync::{Arc, atomic::AtomicBool},
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HdrExportReport {
    pub width: u32,
    pub height: u32,
    pub bit_depth: u8,
    pub color_primaries: String,
    pub transfer: String,
    pub reference_white_nits: f32,
    pub peak_nits: f32,
    pub max_content_light_nits: u16,
    pub average_light_nits: u16,
    pub clipped_samples: u64,
    pub bytes: usize,
}

/// SMPTE ST 2084 inverse EOTF: absolute cd/m² to normalized PQ code.
pub fn pq_encode(nits: f32) -> f32 {
    let l = (nits.clamp(0.0, 10_000.0) / 10_000.0).powf(2610.0 / 16384.0);
    ((3424.0 / 4096.0 + (2413.0 / 128.0) * l) / (1.0 + (2392.0 / 128.0) * l)).powf(2523.0 / 32.0)
}

/// Encodes 10-bit 4:4:4 PQ BT.2020 using built-in rav1e. No external executable.
/// Both AV1 sequence header and AVIF nclx carry the same colorimetry.
pub fn export_hdr_avif(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
) -> Result<HdrExportReport> {
    export_avif(
        path,
        image,
        recipe,
        &ExportSettings {
            quality: recipe.hdr.quality,
            speed: recipe.hdr.speed,
            ..Default::default()
        },
        &AtomicBool::new(false),
    )
}

pub(crate) fn export_avif(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    cancel: &AtomicBool,
) -> Result<HdrExportReport> {
    use crate::export::check_cancel;
    use avif_serialize::{Aviffy, constants as c};
    check_cancel(cancel)?;
    settings.validate()?;
    image.validate()?;
    recipe.validate()?;
    image.validate_source_repairs(recipe)?;
    ensure!(
        !settings.hdr || image.origin == ImageOrigin::SceneLinear,
        "HDR export requires a scene-linear master; a clipped SDR photograph cannot recover HDR"
    );
    ensure!(
        image.width >= 16 && image.height >= 16,
        "AVIF encoding requires dimensions of at least 16 pixels"
    );
    let (primaries, container_primaries) = match settings.color_space {
        OutputColorSpace::Srgb => (ColorPrimaries::BT709, c::ColorPrimaries::Bt709),
        OutputColorSpace::DisplayP3 => (ColorPrimaries::SMPTE432, c::ColorPrimaries::DisplayP3),
        OutputColorSpace::Rec2020 => (ColorPrimaries::BT2020, c::ColorPrimaries::Bt2020),
    };
    let (matrix, container_matrix) = if settings.color_space == OutputColorSpace::Rec2020 {
        (
            MatrixCoefficients::BT2020NCL,
            c::MatrixCoefficients::Bt2020Ncl,
        )
    } else {
        (MatrixCoefficients::BT709, c::MatrixCoefficients::Bt709)
    };
    let (transfer, container_transfer) = if settings.hdr {
        (
            TransferCharacteristics::SMPTE2084,
            c::TransferCharacteristics::Smpte2084,
        )
    } else {
        (
            TransferCharacteristics::SRGB,
            c::TransferCharacteristics::Srgb,
        )
    };
    let mut config = EncoderConfig::with_speed_preset(settings.speed);
    config.width = image.width as usize;
    config.height = image.height as usize;
    config.bit_depth = 10;
    config.chroma_sampling = ChromaSampling::Cs444;
    config.pixel_range = PixelRange::Full;
    config.still_picture = true;
    // rav1e does not expose supported lossless coding at quantizer 0. Quality
    // 100 means its lowest supported lossy quantizer, not a lossless promise.
    config.quantizer = ((100 - usize::from(settings.quality)) * 255 / 100).max(1);
    config.min_quantizer = 0;
    config.color_description = Some(ColorDescription {
        color_primaries: primaries,
        transfer_characteristics: transfer,
        matrix_coefficients: matrix,
    });
    let threads = std::thread::available_parallelism()
        .map_or(1, usize::from)
        .min(16);
    config.tiles = threads;
    let mut context: Context<u16> = Config::new()
        .with_encoder_config(config)
        .with_threads(threads)
        .new_context()
        .context("configuring built-in AVIF encoder")?;
    let mut frame = context.new_frame();
    let mut max_light = 0.0f32;
    let mut sum_light = 0.0f64;
    let mut clipped = 0u64;
    let (kr, kb) = settings.color_space.ycbcr_coefficients();
    for y in 0..image.height as usize {
        check_cancel(cancel)?;
        for x in 0..image.width as usize {
            let i = y * image.width as usize + x;
            let p = if settings.hdr {
                let lin = settings
                    .color_space
                    .convert_from_linear_srgb(image.developed_pixel(i, recipe))
                    .map(|v| v * recipe.hdr.reference_white_nits);
                ensure!(
                    lin.iter().all(|v| v.is_finite()),
                    "development produced non-finite HDR output samples"
                );
                clipped += lin
                    .iter()
                    .filter(|&&v| v < 0.0 || v > recipe.hdr.peak_nits)
                    .count() as u64;
                let light = lin.map(|v| v.clamp(0.0, recipe.hdr.peak_nits));
                max_light = max_light.max(light.into_iter().fold(0.0, f32::max));
                sum_light += f64::from(settings.color_space.luminance(light));
                light.map(pq_encode)
            } else {
                crate::export::sdr_pixel(image, recipe, settings.color_space, i)
            };
            ensure!(
                p.iter().all(|v| v.is_finite()),
                "development produced non-finite output samples"
            );
            let yy = kr * p[0] + (1.0 - kr - kb) * p[1] + kb * p[2];
            // H.273 full-range 10-bit chroma has an integer 512 center, not
            // 0.5 * 1023. Round signed chroma before adding that center.
            let codes = [
                (yy * 1023.0).round(),
                ((p[2] - yy) / (2.0 * (1.0 - kb)) * 1023.0).round() + 512.0,
                ((p[0] - yy) / (2.0 * (1.0 - kr)) * 1023.0).round() + 512.0,
            ];
            for (c, code) in codes.into_iter().enumerate() {
                let plane = &mut frame.planes[c];
                let offset = plane.cfg.yorigin * plane.cfg.stride
                    + plane.cfg.xorigin
                    + y * plane.cfg.stride
                    + x;
                plane.data[offset] = code.clamp(0.0, 1023.0) as u16;
            }
        }
    }
    context
        .send_frame(Arc::new(frame))
        .context("sending HDR image to AV1 encoder")?;
    context.flush();
    let payload = loop {
        check_cancel(cancel)?;
        match context.receive_packet() {
            Ok(packet) => break packet.data,
            Err(EncoderStatus::Encoded) => continue,
            Err(status) => bail!("HDR AV1 encoding failed: {status:?}"),
        }
    };
    let max_content_light_nits = max_light.ceil() as u16;
    let average_light_nits =
        (sum_light / (f64::from(image.width) * f64::from(image.height))).ceil() as u16;
    check_cancel(cancel)?;
    let mut container = Aviffy::new();
    container
        .set_color_primaries(container_primaries)
        .set_transfer_characteristics(container_transfer)
        .set_matrix_coefficients(container_matrix)
        .set_full_color_range(true)
        .set_chroma_subsampling((false, false));
    if settings.hdr {
        container.set_content_light_level(max_content_light_nits, average_light_nits);
    }
    let data = container.to_vec(&payload, None, image.width, image.height, 10);
    crate::publish::new_file_checked(
        path,
        |file| {
            check_cancel(cancel)?;
            file.write_all(&data).context("writing completed AVIF")?;
            check_cancel(cancel)
        },
        || check_cancel(cancel),
    )?;
    Ok(HdrExportReport {
        width: image.width,
        height: image.height,
        bit_depth: 10,
        color_primaries: settings.color_space.label().into(),
        transfer: if settings.hdr {
            "SMPTE ST 2084 (PQ)"
        } else {
            "sRGB (IEC 61966-2-1)"
        }
        .into(),
        reference_white_nits: recipe.hdr.reference_white_nits,
        peak_nits: recipe.hdr.peak_nits,
        max_content_light_nits,
        average_light_nits,
        clipped_samples: clipped,
        bytes: data.len(),
    })
}
