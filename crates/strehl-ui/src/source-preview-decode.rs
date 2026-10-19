//! Preview-only reduced IDCT. The existing image decoder remains the native-
//! resolution and unusual-color fallback; this never touches RAW arithmetic.
use super::*;
use std::io::BufReader;

struct Cancellable<'a> {
    cursor: Cursor<&'a [u8]>,
    cancelled: &'a AtomicBool,
}
impl Read for Cancellable<'_> {
    fn read(&mut self, output: &mut [u8]) -> std::io::Result<usize> {
        if self.cancelled.load(Ordering::Relaxed) {
            // Interrupted is retryable by read_exact; use a terminal error so
            // a cancellation cannot spin forever inside a decoder's reader.
            return Err(std::io::Error::other("Camera preview cancelled"));
        }
        self.cursor.read(output)
    }
}

pub(super) fn decode(
    bytes: &[u8],
    max_side: u32,
    cancelled: &AtomicBool,
) -> Result<(DynamicImage, [u32; 2])> {
    check_cancelled(cancelled)?;
    let (width, height) = jpeg_reader(bytes)
        .into_dimensions()
        .context("Reading camera JPEG dimensions")?;
    ensure!(
        width > 0 && height > 0 && u64::from(width) * u64::from(height) <= MAX_IMAGE_PIXELS,
        "The camera preview exceeds the decoded pixel safety limit"
    );
    // Reducing less than twofold cannot reduce this codec's IDCT work. Keep
    // the existing decoder's exact pixels for native and modest reductions.
    if width.max(height) >= max_side.saturating_mul(2)
        && let Ok(Some(image)) = scaled(bytes, max_side, cancelled)
    {
        return Ok((image, [width, height]));
    }
    check_cancelled(cancelled)?;
    Ok((decode_jpeg(bytes)?, [width, height]))
}

fn scaled(bytes: &[u8], max_side: u32, cancelled: &AtomicBool) -> Result<Option<DynamicImage>> {
    let reader = BufReader::with_capacity(
        32 * 1024,
        Cancellable {
            cursor: Cursor::new(bytes),
            cancelled,
        },
    );
    let mut decoder = jpeg_decoder::Decoder::new(reader);
    decoder.set_max_decoding_buffer_size(MAX_DECODE_BYTES as usize);
    decoder.read_info()?;
    let info = decoder
        .info()
        .context("Camera JPEG has no pixel description")?;
    if !matches!(
        info.pixel_format,
        jpeg_decoder::PixelFormat::L8 | jpeg_decoder::PixelFormat::RGB24
    ) {
        return Ok(None);
    }
    let side = max_side.clamp(1, u16::MAX as u32) as u16;
    let (width, height) = decoder.scale(side, side)?;
    let pixels = decoder.decode()?;
    check_cancelled(cancelled)?;
    let image = match info.pixel_format {
        jpeg_decoder::PixelFormat::RGB24 => DynamicImage::ImageRgb8(
            image::RgbImage::from_raw(u32::from(width), u32::from(height), pixels)
                .context("Camera JPEG has incomplete RGB pixels")?,
        ),
        jpeg_decoder::PixelFormat::L8 => DynamicImage::ImageLuma8(
            image::GrayImage::from_raw(u32::from(width), u32::from(height), pixels)
                .context("Camera JPEG has incomplete gray pixels")?,
        ),
        _ => unreachable!("unsupported color formats returned before decode"),
    };
    Ok(Some(image))
}

#[cfg(test)]
#[path = "source-preview-decode-tests.rs"]
mod tests;
