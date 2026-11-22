use crate::{
    DevelopmentRecipe, ExportSettings, ImageOrigin, LinearImage, OutputColorSpace,
    export_pipeline::{Domain, StageReport, develop_value},
    image::srgb_encode,
};
use anyhow::{Context as _, Result, bail, ensure};
use rav1e::prelude::*;
use rayon::prelude::*;
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

/// Inverse of `pq_encode`: normalized PQ code to absolute cd/m².
pub(crate) fn pq_decode(code: f32) -> f32 {
    let e = code.clamp(0.0, 1.0).powf(32.0 / 2523.0);
    let num = (e - 3424.0 / 4096.0).max(0.0);
    let den = 2413.0 / 128.0 - (2392.0 / 128.0) * e;
    10_000.0 * (num / den).powf(16384.0 / 2610.0)
}

/// Encodes 10-bit 4:4:4 PQ BT.2020 using built-in rav1e. No external executable.
/// Both AV1 sequence header and AVIF nclx carry the same colorimetry.
pub fn export_hdr_avif(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
) -> Result<HdrExportReport> {
    crate::export_image(
        path,
        image,
        recipe,
        &ExportSettings {
            quality: recipe.hdr.quality,
            speed: recipe.hdr.speed,
            ..Default::default()
        },
        &AtomicBool::new(false),
    )?
    .hdr_metadata
    .context("HDR export produced no HDR report")
}

/// Rows developed in parallel before the sequential statistics and coding,
/// which keep the pre-P7 row-major summation order.
const BAND_ROWS: usize = 64;

pub(crate) fn export_avif_job(
    path: &Path,
    job: &crate::export::Job<'_>,
) -> Result<(HdrExportReport, Option<StageReport>, Vec<String>)> {
    use crate::export::check_cancel;
    use avif_serialize::{Aviffy, constants as c};
    let (settings, recipe, image, cancel) = (job.settings, job.recipe, job.image, job.cancel);
    let [width, height] = job.layout.output;
    check_cancel(cancel)?;
    ensure!(
        !settings.hdr || image.origin == ImageOrigin::SceneLinear,
        "HDR export requires a scene-linear master; a clipped SDR photograph cannot recover HDR"
    );
    ensure!(
        width >= 16 && height >= 16,
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
    config.width = width as usize;
    config.height = height as usize;
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
    let domain = if settings.hdr {
        Domain::Hdr(settings.color_space, recipe.hdr.reference_white_nits)
    } else {
        Domain::Sdr(settings.color_space)
    };
    let staged = job.staged_buffer(domain)?;
    let prepared = recipe.prepare();
    let mut frame = context.new_frame();
    let mut max_light = 0.0f32;
    let mut sum_light = 0.0f64;
    let mut clipped = 0u64;
    let (kr, kb) = settings.color_space.ycbcr_coefficients();
    let (w, h) = (width as usize, height as usize);
    let linear_sdr = !settings.hdr && staged.as_ref().is_some_and(|(b, _)| b.linear);
    let mut band = vec![0.0f32; w * 3 * BAND_ROWS.min(h)];
    for top in (0..h).step_by(BAND_ROWS) {
        check_cancel(cancel)?;
        let rows = BAND_ROWS.min(h - top);
        let values: &[f32] = match &staged {
            Some((buffer, _)) => &buffer.pixels[top * w * 3..(top + rows) * w * 3],
            None => {
                let layout = job.layout;
                band[..rows * w * 3]
                    .par_chunks_mut(w * 3)
                    .enumerate()
                    .for_each(|(r, line)| {
                        for (x, out) in line.as_chunks_mut::<3>().0.iter_mut().enumerate() {
                            let (raw, uv) = layout.sample(image, x as u32, (top + r) as u32);
                            *out = develop_value(image, &prepared, domain, raw, uv);
                        }
                    });
                &band[..rows * w * 3]
            }
        };
        for r in 0..rows {
            let y = top + r;
            for x in 0..w {
                let v = &values[(r * w + x) * 3..(r * w + x) * 3 + 3];
                let p = if settings.hdr {
                    let lin = [v[0], v[1], v[2]];
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
                } else if linear_sdr {
                    [srgb_encode(v[0]), srgb_encode(v[1]), srgb_encode(v[2])]
                } else {
                    [v[0], v[1], v[2]]
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
    let average_light_nits = (sum_light / (f64::from(width) * f64::from(height))).ceil() as u16;
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
    // Always: the Exif item carries the Strehl stamp (Software).
    container.set_exif(crate::metadata::exif_block(
        &settings.metadata,
        job.extras.date_time.as_ref(),
    ));
    let written = vec!["exif".to_owned()];
    let data = container.to_vec(&payload, None, width, height, 10);
    crate::publish::new_file_checked(
        path,
        |file| {
            check_cancel(cancel)?;
            file.write_all(&data).context("writing completed AVIF")?;
            check_cancel(cancel)
        },
        || check_cancel(cancel),
    )?;
    let report = HdrExportReport {
        width,
        height,
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
    };
    Ok((report, staged.map(|(_, r)| r), written))
}
