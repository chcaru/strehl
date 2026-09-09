use std::borrow::Cow;
use std::io::{Cursor, Read, Seek, SeekFrom, Write};

use serde::Serialize;
use tiff::encoder::{TiffEncoder, TiffValue, colortype};
use tiff::tags::{Tag, Type};

use super::files::{self, Result, require};
use super::manifest::Layout;

const DESCRIPTION: &str = "common-tiff-stack-v1; identity common-RGB pixels; linear ProPhoto RGB D50; RGB16 code units; no WB, camera matrix, demosaic, exposure, tone or transfer; finite clamp then round half away from zero; simulation-only noise declaration";
const SOFTWARE: &str = "strehl-common-input common-tiff-stack-v1";
const DESCRIPTION_V2: &str = "common-tiff-stack-v2; identity common-RGB pixels; linear ProPhoto RGB D50; RGB16 code units; no WB, camera matrix, demosaic, exposure, tone or transfer; finite clamp then round half away from zero; simulation-only noise declaration";
const SOFTWARE_V2: &str = "strehl-common-input common-tiff-stack-v2";

struct IccBytes<'a>(&'a [u8]);
impl TiffValue for IccBytes<'_> {
    const BYTE_LEN: u8 = 1;
    const FIELD_TYPE: Type = Type::UNDEFINED;
    fn count(&self) -> usize {
        self.0.len()
    }
    fn data(&self) -> Cow<'_, [u8]> {
        Cow::Borrowed(self.0)
    }
}

struct BoundedCursor(Cursor<Vec<u8>>, usize);
impl Write for BoundedCursor {
    fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
        let end = self.0.position().checked_add(bytes.len() as u64);
        if !end.is_some_and(|n| n <= self.1 as u64) {
            return Err(std::io::Error::other("TIFF encoding capacity"));
        }
        self.0.write(bytes)
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}
impl Seek for BoundedCursor {
    fn seek(&mut self, position: SeekFrom) -> std::io::Result<u64> {
        let next = self.0.seek(position)?;
        if next > self.1 as u64 {
            return Err(std::io::Error::other("TIFF seek capacity"));
        }
        Ok(next)
    }
}
impl Read for BoundedCursor {
    fn read(&mut self, bytes: &mut [u8]) -> std::io::Result<usize> {
        self.0.read(bytes)
    }
}

#[derive(Debug, Serialize)]
pub struct Encoded {
    #[serde(skip)]
    pub bytes: Vec<u8>,
    pub width: u32,
    pub height: u32,
    pub sample_format: &'static str,
    pub color_space: &'static str,
    pub icc_sha256: String,
    pub pixel_sha256: String,
    pub prequantization_f32_sha256: String,
    pub clipped_low: [u64; 3],
    pub clipped_high: [u64; 3],
    pub quantization: &'static str,
}

pub fn encode(planes: &[Vec<f32>], icc: &[u8], layout: &Layout) -> Result<Encoded> {
    let count = layout.pixels;
    require(
        planes.len() == 3 && planes.iter().all(|p| p.len() == count),
        "output plane geometry",
    )?;
    let mut low = [0; 3];
    let mut high = [0; 3];
    let mut samples = Vec::with_capacity(count * 3);
    for i in 0..count {
        for c in 0..3 {
            let v = planes[c][i];
            require(v.is_finite(), "nonfinite RGB output")?;
            low[c] += u64::from(v < 0.0);
            high[c] += u64::from(v > 65535.0);
            samples.push(v.clamp(0.0, 65535.0).round() as u16);
        }
    }
    let payload: Vec<u8> = samples.iter().flat_map(|v| v.to_le_bytes()).collect();
    let mut buffer = BoundedCursor(
        Cursor::new(Vec::with_capacity(layout.output_cap)),
        layout.output_cap,
    );
    {
        let mut encoder =
            TiffEncoder::new(&mut buffer).map_err(|e| format!("TIFF encoder: {e}"))?;
        let mut image = encoder
            .new_image::<colortype::RGB16>(layout.width, layout.height)
            .map_err(|e| format!("TIFF RGB16: {e}"))?;
        image
            .encoder()
            .write_tag(Tag::PlanarConfiguration, 1u16)
            .map_err(|e| format!("TIFF chunky RGB: {e}"))?;
        image
            .encoder()
            .write_tag(
                Tag::ImageDescription,
                if layout.v2 {
                    DESCRIPTION_V2
                } else {
                    DESCRIPTION
                },
            )
            .map_err(|e| format!("TIFF description: {e}"))?;
        image
            .encoder()
            .write_tag(
                Tag::Software,
                if layout.v2 { SOFTWARE_V2 } else { SOFTWARE },
            )
            .map_err(|e| format!("TIFF software: {e}"))?;
        image
            .encoder()
            .write_tag(Tag::IccProfile, IccBytes(icc))
            .map_err(|e| format!("TIFF ICC: {e}"))?;
        image
            .write_data(&samples)
            .map_err(|e| format!("TIFF data: {e}"))?;
    }
    let bytes = buffer.0.into_inner();
    require(bytes.len() <= layout.output_cap, "TIFF final capacity")?;
    Ok(Encoded {
        bytes,
        width: layout.width,
        height: layout.height,
        sample_format: "RGB16",
        color_space: "linear-prophoto-d50",
        icc_sha256: files::hash(icc),
        pixel_sha256: files::hash(&payload),
        prequantization_f32_sha256: files::f32_hash(planes.iter().flatten().copied()),
        clipped_low: low,
        clipped_high: high,
        quantization: "finite-clamp-round-half-away-v1",
    })
}
