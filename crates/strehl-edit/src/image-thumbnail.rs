//! Bounded photograph thumbnails. This is a navigation derivative, never an
//! editing source or a replacement for the full-resolution decoder.
use super::*;
use std::io::{Read, Seek, SeekFrom};
use std::sync::atomic::{AtomicBool, Ordering};

/// Read a small, color-managed photograph without decoding its full pixel
/// buffer. Ordinary uncompressed RGB TIFFs read at most two rows per thumbnail
/// row and average four samples per cell. Compressed/tiled files use the full
/// validated decoder as a compatibility fallback. The returned aperture is the
/// original photograph's dimensions; the image is only a navigation preview.
pub fn load_tiff_thumbnail(
    path: &Path,
    max_edge: u32,
    cancelled: &AtomicBool,
) -> Result<(LinearImage, [u32; 2])> {
    ensure!(
        (1..=1024).contains(&max_edge),
        "thumbnail edge must be 1–1024 pixels"
    );
    check(cancelled)?;
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = 2 * 1024 * 1024;
    limits.ifd_value_size = 2 * 1024 * 1024;
    let mut decoder = Decoder::new(BufReader::new(File::open(path)?))?.with_limits(limits);
    let (width, height) = decoder.dimensions()?;
    image_samples(width, height)?;
    ensure!(
        width <= 32_768 && height <= 32_768 && u64::from(width) * u64::from(height) <= 80_000_000,
        "photograph exceeds the bounded thumbnail aperture"
    );
    let (description, color, input_space) = tiff_metadata(&mut decoder)?;
    let uncompressed = decoder
        .find_tag_unsigned::<u16>(Tag::Compression)?
        .unwrap_or(1)
        == 1;
    let chunky = decoder
        .find_tag_unsigned::<u16>(Tag::PlanarConfiguration)?
        .unwrap_or(1)
        == 1;
    let direct = decoder
        .find_tag_unsigned::<u16>(Tag::Predictor)?
        .unwrap_or(1)
        == 1;
    let float = color == ColorType::RGB(32);
    let formats = decoder.find_tag_unsigned_vec::<u16>(Tag::SampleFormat)?;
    let supported_samples = formats
        .as_ref()
        .is_none_or(|v| v.iter().all(|&n| n == if float { 3 } else { 1 }))
        && (!float || formats.is_some());
    let strips = decoder.find_tag_unsigned_vec::<u64>(Tag::StripOffsets)?;
    let lengths = decoder.find_tag_unsigned_vec::<u64>(Tag::StripByteCounts)?;
    if !uncompressed
        || !chunky
        || !direct
        || !supported_samples
        || strips.is_none()
        || lengths.is_none()
    {
        check(cancelled)?;
        let image = load_tiff(path)?;
        check(cancelled)?;
        return Ok((image.preview(max_edge), [width, height]));
    }
    let little = decoder.byte_order() == tiff::tags::ByteOrder::LittleEndian;
    let strips = strips.unwrap();
    let lengths = lengths.unwrap();
    let rows_per_strip = decoder
        .find_tag_unsigned::<u32>(Tag::RowsPerStrip)?
        .unwrap_or(height);
    ensure!(rows_per_strip > 0, "TIFF has empty strips");
    let count = height.div_ceil(rows_per_strip) as usize;
    ensure!(
        strips.len() == count && lengths.len() == count,
        "TIFF strip count does not match its aperture"
    );
    let bytes_per_sample = color.bit_depth() as usize / 8;
    let row_bytes = width as usize * 3 * bytes_per_sample;
    let mut file = File::open(path)?;
    let file_bytes = file.metadata()?.len();
    for (strip, (&offset, &bytes)) in strips.iter().zip(&lengths).enumerate() {
        let rows = rows_per_strip.min(height - strip as u32 * rows_per_strip);
        let expected = u64::from(rows) * row_bytes as u64;
        ensure!(
            bytes >= expected
                && offset
                    .checked_add(bytes)
                    .is_some_and(|end| end <= file_bytes),
            "TIFF strip exceeds its file or is truncated"
        );
    }
    let scale = width.max(height) as f32 / max_edge as f32;
    let tw = (width as f32 / scale.max(1.0)).round().max(1.0) as u32;
    let th = (height as f32 / scale.max(1.0)).round().max(1.0) as u32;
    let mut pixels = vec![0.0; tw as usize * th as usize * 3];
    let mut row = vec![0u8; row_bytes];
    for y in 0..th {
        check(cancelled)?;
        // Two symmetric subcell samples limit aliasing without reading every
        // row of a hundred-megabyte source just to paint a 22-pixel icon.
        for sy in samples(y, height, th) {
            let strip = sy / rows_per_strip;
            let offset = strips[strip as usize] + u64::from(sy % rows_per_strip) * row_bytes as u64;
            file.seek(SeekFrom::Start(offset))?;
            file.read_exact(&mut row)?;
            for x in 0..tw {
                for sx in samples(x, width, tw) {
                    let p = sx as usize * 3 * bytes_per_sample;
                    let mut rgb = [0.0; 3];
                    for (channel, value) in rgb.iter_mut().enumerate() {
                        let at = p + channel * bytes_per_sample;
                        *value = match bytes_per_sample {
                            1 => srgb_decode(row[at] as f32 / 255.0),
                            2 => {
                                let bytes = [row[at], row[at + 1]];
                                srgb_decode(
                                    if little {
                                        u16::from_le_bytes(bytes)
                                    } else {
                                        u16::from_be_bytes(bytes)
                                    } as f32
                                        / 65535.0,
                                )
                            }
                            4 => {
                                let bytes = row[at..at + 4].try_into().unwrap();
                                if little {
                                    f32::from_le_bytes(bytes)
                                } else {
                                    f32::from_be_bytes(bytes)
                                }
                            }
                            _ => unreachable!("metadata rejects unsupported sample sizes"),
                        };
                    }
                    if !float {
                        rgb = input_space.to_linear_srgb(rgb);
                    }
                    let at = (y * tw + x) as usize * 3;
                    for c in 0..3 {
                        pixels[at + c] += rgb[c] * 0.25;
                    }
                }
            }
        }
    }
    check(cancelled)?;
    Ok((
        tiff_image(
            tw,
            th,
            pixels,
            if float {
                ImageOrigin::SceneLinear
            } else {
                ImageOrigin::DisplayReferred
            },
            &description,
        )?,
        [width, height],
    ))
}

fn samples(i: u32, source: u32, target: u32) -> [u32; 2] {
    [1, 3].map(|quarter| {
        ((u64::from(i) * 4 + quarter) * u64::from(source) / (u64::from(target) * 4))
            .min(u64::from(source - 1)) as u32
    })
}
fn check(cancelled: &AtomicBool) -> Result<()> {
    ensure!(!cancelled.load(Ordering::Relaxed), "thumbnail cancelled");
    Ok(())
}

#[cfg(test)]
#[path = "image-thumbnail-tests.rs"]
mod tests;
