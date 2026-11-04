//! Bounded scalar TIFF inspection; no display normalization or invented validity.
use anyhow::{Context, Result, ensure};
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{BufReader, Read, Seek, SeekFrom},
    path::Path,
};
use tiff::decoder::{Decoder, DecodingResult};

#[derive(Debug)]
pub enum ScalarSamples {
    U8(Vec<u8>),
    U16(Vec<u16>),
    F32(Vec<f32>),
}
impl ScalarSamples {
    pub fn into_f32(self) -> Vec<f32> {
        match self {
            Self::U8(v) => v.into_iter().map(f32::from).collect(),
            Self::U16(v) => v.into_iter().map(f32::from).collect(),
            Self::F32(v) => v,
        }
    }
}
#[derive(Debug)]
pub struct ScalarImage {
    pub size: [u32; 2],
    pub samples: ScalarSamples,
}

/// The budget limits the decoded scalar allocation; callers additionally reserve
/// any conversion and display buffers. Optional SHA-256 binds the exact stored
/// TIFF bytes. Dimensions and channel type are checked before pixel allocation.
pub fn read_scalar_tiff(
    path: &Path,
    expected: [u32; 2],
    max_decoded_bytes: usize,
    expected_sha256: Option<&str>,
) -> Result<ScalarImage> {
    ensure!(
        expected.iter().all(|&n| n > 0 && n <= 32_768),
        "Invalid scalar-map dimensions"
    );
    let count = (expected[0] as usize)
        .checked_mul(expected[1] as usize)
        .context("Scalar dimensions overflow")?;
    let mut file = File::open(path)?;
    let before = file.metadata()?;
    ensure!(
        before.len()
            <= (max_decoded_bytes as u64)
                .saturating_mul(4)
                .saturating_add(1024 * 1024),
        "Scalar TIFF file exceeds its bounded envelope"
    );
    if let Some(expected) = expected_sha256 {
        ensure!(
            expected.len() == 64 && expected.bytes().all(|v| v.is_ascii_hexdigit()),
            "Invalid scalar TIFF SHA-256 receipt"
        );
        let mut hash = Sha256::new();
        let mut buffer = [0u8; 65536];
        loop {
            let n = file.read(&mut buffer)?;
            if n == 0 {
                break;
            }
            hash.update(&buffer[..n]);
        }
        let actual = hash
            .finalize()
            .iter()
            .map(|v| format!("{v:02x}"))
            .collect::<String>();
        ensure!(
            actual.eq_ignore_ascii_case(expected),
            "Scalar TIFF checksum does not match its saved receipt"
        );
        file.seek(SeekFrom::Start(0))?;
    }
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = max_decoded_bytes;
    limits.intermediate_buffer_size = max_decoded_bytes;
    limits.ifd_value_size = 1024 * 1024;
    let mut decoder = Decoder::new(BufReader::new(file))?.with_limits(limits);
    ensure!(
        decoder.dimensions()? == (expected[0], expected[1]),
        "Scalar TIFF dimensions differ from the saved geometry"
    );
    let bytes = match decoder.colortype()? {
        tiff::ColorType::Gray(8) => 1usize,
        tiff::ColorType::Gray(16) => 2,
        tiff::ColorType::Gray(32) => 4,
        _ => anyhow::bail!(
            "Diagnostic TIFF must contain a single Gray8, Gray16 or Gray32Float channel"
        ),
    };
    ensure!(
        count
            .checked_mul(bytes)
            .is_some_and(|n| n <= max_decoded_bytes),
        "Scalar TIFF decoded payload exceeds its budget"
    );
    let samples = match decoder.read_image()? {
        DecodingResult::U8(v) if v.len() == count => ScalarSamples::U8(v),
        DecodingResult::U16(v) if v.len() == count => ScalarSamples::U16(v),
        DecodingResult::F32(v) if v.len() == count => {
            ensure!(
                v.iter().all(|v| !v.is_infinite()),
                "Scalar TIFF contains infinite values"
            );
            ScalarSamples::F32(v)
        }
        _ => anyhow::bail!("Scalar TIFF storage differs from the supported contract"),
    };
    let after = std::fs::metadata(path)?;
    ensure!(
        before.len() == after.len() && before.modified()? == after.modified()?,
        "Scalar TIFF changed while loading"
    );
    Ok(ScalarImage {
        size: expected,
        samples,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn scalar_reader_retains_nan_and_checks_hash_geometry_type_and_budget() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("map.tiff");
        tiff::encoder::TiffEncoder::new(File::create(&path).unwrap())
            .unwrap()
            .write_image::<tiff::encoder::colortype::Gray32Float>(2, 2, &[0.0, f32::NAN, 2.5, -1.0])
            .unwrap();
        let hash = Sha256::digest(std::fs::read(&path).unwrap())
            .iter()
            .map(|v| format!("{v:02x}"))
            .collect::<String>();
        let image = read_scalar_tiff(&path, [2, 2], 16, Some(&hash)).unwrap();
        let values = image.samples.into_f32();
        assert_eq!(values[0], 0.0);
        assert!(values[1].is_nan());
        assert_eq!(values[2], 2.5);
        assert!(read_scalar_tiff(&path, [1, 4], 16, Some(&hash)).is_err());
        assert!(read_scalar_tiff(&path, [2, 2], 15, Some(&hash)).is_err());
        assert!(read_scalar_tiff(&path, [2, 2], 16, Some(&"0".repeat(64))).is_err());
        tiff::encoder::TiffEncoder::new(File::create(&path).unwrap())
            .unwrap()
            .write_image::<tiff::encoder::colortype::RGB8>(2, 2, &[0; 12])
            .unwrap();
        assert!(read_scalar_tiff(&path, [2, 2], 16, None).is_err());
    }
    #[test]
    fn scalar_reader_preserves_exact_integer_masks() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("mask.tiff");
        tiff::encoder::TiffEncoder::new(File::create(&path).unwrap())
            .unwrap()
            .write_image::<tiff::encoder::colortype::Gray8>(2, 1, &[0, 255])
            .unwrap();
        assert!(
            matches!(read_scalar_tiff(&path,[2,1],2,None).unwrap().samples,ScalarSamples::U8(v) if v==[0,255])
        );
    }
}
