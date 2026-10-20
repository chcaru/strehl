use crate::{DevelopmentRecipe, ImageOrigin, LinearImage};
use anyhow::{Context as _, Result, bail, ensure};
use rav1e::prelude::*;
use serde::{Deserialize, Serialize};
use std::{io::Write, path::Path, sync::Arc};

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

fn bt2020(rgb: [f32; 3]) -> [f32; 3] {
    // D65-to-D65 linear BT.709 -> BT.2020, derived from their published primaries.
    [
        0.627404 * rgb[0] + 0.329283 * rgb[1] + 0.043313 * rgb[2],
        0.069097 * rgb[0] + 0.919540 * rgb[1] + 0.011362 * rgb[2],
        0.016391 * rgb[0] + 0.088013 * rgb[1] + 0.895595 * rgb[2],
    ]
}

/// Encodes 10-bit 4:4:4 PQ BT.2020 using built-in rav1e. No external executable.
/// Both AV1 sequence header and AVIF nclx carry the same colorimetry.
pub fn export_hdr_avif(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
) -> Result<HdrExportReport> {
    image.validate()?;
    recipe.validate()?;
    image.validate_source_repairs(recipe)?;
    ensure!(
        image.origin == ImageOrigin::SceneLinear,
        "HDR export requires a scene-linear master; a clipped SDR photograph cannot recover HDR"
    );
    ensure!(
        image.width >= 16 && image.height >= 16,
        "AVIF encoding requires dimensions of at least 16 pixels"
    );
    let mut config = EncoderConfig::with_speed_preset(recipe.hdr.speed);
    config.width = image.width as usize;
    config.height = image.height as usize;
    config.bit_depth = 10;
    config.chroma_sampling = ChromaSampling::Cs444;
    config.pixel_range = PixelRange::Full;
    config.still_picture = true;
    config.quantizer = ((100 - usize::from(recipe.hdr.quality)) * 255 / 100).max(1);
    config.min_quantizer = 0;
    config.color_description = Some(ColorDescription {
        color_primaries: ColorPrimaries::BT2020,
        transfer_characteristics: TransferCharacteristics::SMPTE2084,
        matrix_coefficients: MatrixCoefficients::BT2020NCL,
    });
    let threads = std::thread::available_parallelism()
        .map_or(1, usize::from)
        .min(16);
    config.tiles = threads;
    let mut context: Context<u16> = Config::new()
        .with_encoder_config(config)
        .with_threads(threads)
        .new_context()
        .context("configuring built-in HDR AVIF encoder")?;
    let mut frame = context.new_frame();
    let mut max_light = 0.0f32;
    let mut sum_light = 0.0f64;
    let mut clipped = 0u64;
    for y in 0..image.height as usize {
        for x in 0..image.width as usize {
            let i = y * image.width as usize + x;
            let lin = bt2020(image.developed_pixel(i, recipe))
                .map(|v| v * recipe.hdr.reference_white_nits);
            clipped += lin
                .iter()
                .filter(|&&v| v < 0.0 || v > recipe.hdr.peak_nits)
                .count() as u64;
            let light = lin.map(|v| v.clamp(0.0, recipe.hdr.peak_nits));
            max_light = max_light.max(light.into_iter().fold(0.0, f32::max));
            sum_light += f64::from(0.2627 * light[0] + 0.6780 * light[1] + 0.0593 * light[2]);
            let p = light.map(pq_encode);
            let yy = 0.2627 * p[0] + 0.6780 * p[1] + 0.0593 * p[2];
            // H.273 full-range 10-bit chroma has an integer 512 center, not
            // 0.5 * 1023. Round signed chroma before adding that center.
            let codes = [
                (yy * 1023.0).round(),
                ((p[2] - yy) / (2.0 * (1.0 - 0.0593)) * 1023.0).round() + 512.0,
                ((p[0] - yy) / (2.0 * (1.0 - 0.2627)) * 1023.0).round() + 512.0,
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
        match context.receive_packet() {
            Ok(packet) => break packet.data,
            Err(EncoderStatus::Encoded) => continue,
            Err(status) => bail!("HDR AV1 encoding failed: {status:?}"),
        }
    };
    let max_content_light_nits = max_light.ceil() as u16;
    let average_light_nits =
        (sum_light / (f64::from(image.width) * f64::from(image.height))).ceil() as u16;
    use avif_serialize::{Aviffy, constants as c};
    let data = Aviffy::new()
        .set_color_primaries(c::ColorPrimaries::Bt2020)
        .set_transfer_characteristics(c::TransferCharacteristics::Smpte2084)
        .set_matrix_coefficients(c::MatrixCoefficients::Bt2020Ncl)
        .set_full_color_range(true)
        .set_chroma_subsampling((false, false))
        .set_content_light_level(max_content_light_nits, average_light_nits)
        .to_vec(&payload, None, image.width, image.height, 10);
    crate::publish::new_file(path, |file| {
        file.write_all(&data).context("writing completed HDR AVIF")
    })?;
    Ok(HdrExportReport {
        width: image.width,
        height: image.height,
        bit_depth: 10,
        color_primaries: "BT.2020".into(),
        transfer: "SMPTE ST 2084 (PQ)".into(),
        reference_white_nits: recipe.hdr.reference_white_nits,
        peak_nits: recipe.hdr.peak_nits,
        max_content_light_nits,
        average_light_nits,
        clipped_samples: clipped,
        bytes: data.len(),
    })
}
