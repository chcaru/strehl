//! Optional Sony optical metadata as exact header facts.
//!
//! No radial law, units, correction strength, native working levels, or decoded
//! active geometry are inferred here. Off does not erase a table. Unknown
//! setting codes remain raw integers. This module does not call decode or select
//! an optical profile. Source hashes and any correction hypothesis belong to the
//! caller; the offsets/bytes here describe only the inspected metadata.
use std::fs::File;
use std::io::{Read, Seek};
use std::path::Path;

use crate::sony_tiff::{Directory, Entry, Reader, SonyTiffError, u16le, u32le};

#[derive(Debug, thiserror::Error)]
pub enum SonyOpticalError {
    #[error("optical metadata I/O: {0}")]
    Io(#[from] std::io::Error),
    #[error("unsupported optical metadata: {0}")]
    Unsupported(String),
    #[error("malformed optical metadata: {0}")]
    Malformed(String),
}
impl From<SonyTiffError> for SonyOpticalError {
    fn from(error: SonyTiffError) -> Self {
        match error {
            SonyTiffError::Io(error) => Self::Io(error),
            SonyTiffError::Unsupported(message) => Self::Unsupported(message),
            SonyTiffError::Malformed(message) => Self::Malformed(message),
        }
    }
}
type Result<T> = std::result::Result<T, SonyOpticalError>;
fn malformed(message: impl Into<String>) -> SonyOpticalError {
    SonyOpticalError::Malformed(message.into())
}
fn unsupported(message: impl Into<String>) -> SonyOpticalError {
    SonyOpticalError::Unsupported(message.into())
}

/// Absolute location and declared TIFF representation; no optical interpretation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TagSource {
    pub tag: u16,
    pub tiff_type: u16,
    pub count: u32,
    pub value_offset: u64,
}
/// Exact field bytes plus the lossless integer/string presentation.
/// A missing optional field is None, never a guessed plausible value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HeaderValue<T> {
    pub value: T,
    pub source: TagSource,
    pub raw_bytes: Vec<u8>,
}
impl<T> HeaderValue<T> {
    fn map<U>(self, f: impl FnOnce(T) -> U) -> HeaderValue<U> {
        HeaderValue {
            value: f(self.value),
            source: self.source,
            raw_bytes: self.raw_bytes,
        }
    }
}

/// A valid signed-16 table. Prefix is retained and must equal N.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SignedTable<const N: usize> {
    pub prefix: i16,
    pub samples: [i16; N],
    pub source: TagSource,
    pub raw_bytes: Vec<u8>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CorrectionMetadata<const N: usize> {
    /// Raw SHORT/LONG/SSHORT value. Unknown codes and Off are preserved losslessly.
    pub setting: Option<HeaderValue<i64>>,
    pub table: Option<SignedTable<N>>,
}

/// Header geometry in the tag's native coordinate convention.
/// In particular sony_image_size is not a newly measured decoder active area.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SonyRawGeometry {
    pub stored_width: Option<HeaderValue<u32>>,
    pub stored_height: Option<HeaderValue<u32>>,
    pub bits_per_sample: Option<HeaderValue<u32>>,
    pub compression: Option<HeaderValue<u32>>,
    pub cfa_repeat: Option<HeaderValue<[u32; 2]>>,
    pub cfa_pattern: Option<HeaderValue<[u8; 4]>>,
    pub default_crop_origin: Option<HeaderValue<[u32; 2]>>,
    pub default_crop_size: Option<HeaderValue<[u32; 2]>>,
    pub sony_image_size: Option<HeaderValue<[u32; 2]>>,
    pub sony_crop_origin: Option<HeaderValue<[u32; 2]>>,
    pub sony_crop_size: Option<HeaderValue<[u32; 2]>>,
    /// TIFF ActiveArea order is top,left,bottom,right, if actually present.
    pub active_area: Option<HeaderValue<[u32; 4]>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SonyOpticalMetadata {
    pub make: HeaderValue<String>,
    pub model: HeaderValue<String>,
    pub software: Option<HeaderValue<String>>,
    pub orientation: Option<HeaderValue<u32>>,
    pub lens_model: Option<HeaderValue<String>>,
    /// Deciphered owned identity.rs format, with original encoded block retained.
    /// Present zero is preserved as an unpopulated slot, not a usable gear ID.
    pub lens_type3: Option<HeaderValue<u16>>,
    pub iso: Option<HeaderValue<u32>>,
    pub capture_date: Option<HeaderValue<String>>,
    /// Numerator,denominator pairs; no float conversion or exposure adjustment.
    pub exposure_time: Option<HeaderValue<[u32; 2]>>,
    pub aperture: Option<HeaderValue<[u32; 2]>>,
    pub focal_length: Option<HeaderValue<[u32; 2]>>,
    pub shading: CorrectionMetadata<16>,
    pub chromatic_aberration: CorrectionMetadata<32>,
    pub distortion: CorrectionMetadata<16>,
    /// Raw maker-note settings are retained separately from RAW IFD settings.
    pub maker_shading_setting: Option<HeaderValue<i64>>,
    pub maker_ca_setting: Option<HeaderValue<i64>>,
    pub maker_distortion_setting: Option<HeaderValue<i64>>,
    pub geometry: SonyRawGeometry,
    /// Header-only levels, not Frame::levels or the injected noise model.
    pub header_black: Option<HeaderValue<[u32; 4]>>,
    pub header_white: Option<HeaderValue<u32>>,
    pub raw_ifd_offset: u64,
    pub source_file_bytes: u64,
    pub metadata_bytes_read: usize,
}

/// Read exact optional optical facts. No image pixels are decoded or modified.
/// Ok(None): supported camera with no optical fields in the selected RAW IFD.
/// Partial fields stay explicitly None. Malformed fields refuse rather than
/// becoming absent; unsupported camera/container/layout remains a distinct error.
pub fn read(path: &Path) -> Result<Option<SonyOpticalMetadata>> {
    read_from_reader(&mut File::open(path)?)
}
/// Bounded to 128KiB reads, 8MiB header addresses and four distinct directories.
/// Does not require, read or decode Sony's hidden focus payload.
pub fn read_from_reader<R: Read + Seek>(stream: &mut R) -> Result<Option<SonyOpticalMetadata>> {
    let mut r = Reader::new(stream)?;
    r.limit_address(8 * 1024 * 1024);
    inspect(&mut r)
}

fn field<T>(entry: Entry, raw_bytes: Vec<u8>, value: T) -> HeaderValue<T> {
    let value_offset = if raw_bytes.len() <= 4 {
        entry.inline_offset
    } else {
        u64::from(entry.value)
    };
    HeaderValue {
        value,
        source: TagSource {
            tag: entry.tag,
            tiff_type: entry.kind,
            count: entry.count,
            value_offset,
        },
        raw_bytes,
    }
}
fn text<R: Read + Seek>(
    r: &mut Reader<'_, R>,
    dir: &Directory,
    tag: u16,
) -> Result<Option<HeaderValue<String>>> {
    let Some(e) = dir.get(tag) else {
        return Ok(None);
    };
    if e.kind != 2 || e.count == 0 || e.count > 256 {
        return Err(malformed(format!("invalid text tag 0x{tag:04x}")));
    }
    let bytes = r.typed_bytes(e, 2, e.count)?;
    let end = bytes.iter().rposition(|&b| b != 0).map_or(0, |n| n + 1);
    if end == 0 || !bytes[..end].is_ascii() || bytes[..end].contains(&0) {
        return Err(malformed(format!("invalid ASCII tag 0x{tag:04x}")));
    }
    let value = std::str::from_utf8(&bytes[..end])
        .map_err(|_| malformed("invalid ASCII"))?
        .to_owned();
    Ok(Some(field(e, bytes, value)))
}
fn unsigned<const N: usize, R: Read + Seek>(
    r: &mut Reader<'_, R>,
    dir: &Directory,
    tag: u16,
) -> Result<Option<HeaderValue<[u32; N]>>> {
    let Some(e) = dir.get(tag) else {
        return Ok(None);
    };
    if !matches!(e.kind, 3 | 4) || e.count as usize != N {
        return Err(malformed(format!(
            "invalid unsigned tag 0x{tag:04x} type/count"
        )));
    }
    let bytes = r.typed_bytes(e, e.kind, N as u32)?;
    let value = std::array::from_fn(|i| {
        if e.kind == 3 {
            u32::from(u16le(&bytes, 2 * i))
        } else {
            u32le(&bytes, 4 * i)
        }
    });
    Ok(Some(field(e, bytes, value)))
}
fn scalar<R: Read + Seek>(
    r: &mut Reader<'_, R>,
    dir: &Directory,
    tag: u16,
) -> Result<Option<HeaderValue<u32>>> {
    Ok(unsigned::<1, _>(r, dir, tag)?.map(|v| v.map(|a| a[0])))
}
fn rational<R: Read + Seek>(
    r: &mut Reader<'_, R>,
    dir: &Directory,
    tag: u16,
) -> Result<Option<HeaderValue<[u32; 2]>>> {
    let Some(e) = dir.get(tag) else {
        return Ok(None);
    };
    let bytes = r.typed_bytes(e, 5, 1)?;
    let value = [u32le(&bytes, 0), u32le(&bytes, 4)];
    // Preserve zero-denominator header facts; consumers cannot turn them into a usable float.
    Ok(Some(field(e, bytes, value)))
}
fn setting<R: Read + Seek>(
    r: &mut Reader<'_, R>,
    dir: &Directory,
    tag: u16,
) -> Result<Option<HeaderValue<i64>>> {
    let Some(e) = dir.get(tag) else {
        return Ok(None);
    };
    if !matches!(e.kind, 3 | 4 | 8) || e.count != 1 {
        return Err(malformed(format!("invalid setting tag 0x{tag:04x}")));
    }
    let bytes = r.typed_bytes(e, e.kind, 1)?;
    let value = match e.kind {
        4 => i64::from(u32le(&bytes, 0)),
        8 => i64::from(u16le(&bytes, 0) as i16),
        _ => i64::from(u16le(&bytes, 0)),
    };
    Ok(Some(field(e, bytes, value)))
}
fn correction<const N: usize, R: Read + Seek>(
    r: &mut Reader<'_, R>,
    dir: &Directory,
    setting_tag: u16,
    table_tag: u16,
) -> Result<CorrectionMetadata<N>> {
    let setting = setting(r, dir, setting_tag)?;
    let table = if let Some(e) = dir.get(table_tag) {
        let bytes = r.typed_bytes(e, 8, (N + 1) as u32)?;
        let prefix = u16le(&bytes, 0) as i16;
        if usize::try_from(prefix).ok() != Some(N) {
            return Err(malformed(format!(
                "invalid table prefix for 0x{table_tag:04x}"
            )));
        }
        let samples = std::array::from_fn(|i| u16le(&bytes, 2 + 2 * i) as i16);
        let raw = field(e, bytes, ());
        Some(SignedTable {
            prefix,
            samples,
            source: raw.source,
            raw_bytes: raw.raw_bytes,
        })
    } else {
        None
    };
    Ok(CorrectionMetadata { setting, table })
}
fn payloads<R: Read + Seek>(r: &mut Reader<'_, R>, raw: &Directory) -> Result<Vec<(u64, u64)>> {
    let mut ranges = Vec::new();
    for (offset_tag, count_tag) in [(0x0111, 0x0117), (0x0144, 0x0145)] {
        match (raw.get(offset_tag), raw.get(count_tag)) {
            (None, None) => {}
            (Some(a), Some(b)) => {
                if !matches!(a.kind, 3 | 4)
                    || !matches!(b.kind, 3 | 4)
                    || a.count == 0
                    || a.count > 4096
                    || b.count != a.count
                {
                    return Err(malformed("invalid image payload table"));
                }
                let offsets = r.typed_bytes(a, a.kind, a.count)?;
                let counts = r.typed_bytes(b, b.kind, b.count)?;
                for i in 0..a.count as usize {
                    let at = u64::from(if a.kind == 3 {
                        u32::from(u16le(&offsets, 2 * i))
                    } else {
                        u32le(&offsets, 4 * i)
                    });
                    let len = u64::from(if b.kind == 3 {
                        u32::from(u16le(&counts, 2 * i))
                    } else {
                        u32le(&counts, 4 * i)
                    });
                    if len == 0 {
                        return Err(malformed("empty image payload"));
                    }
                    r.range(at, len)?;
                    ranges.push((at, at + len));
                }
            }
            _ => return Err(malformed("unpaired image payload tags")),
        }
    }
    if ranges.is_empty() {
        return Err(unsupported("missing declared image payload ranges"));
    }
    Ok(ranges)
}

fn inspect<R: Read + Seek>(r: &mut Reader<'_, R>) -> Result<Option<SonyOpticalMetadata>> {
    let head = r.bytes(0, 8)?;
    if &head[..2] != b"II" || u16le(&head, 2) != 42 {
        return Err(unsupported("requires little-endian classic TIFF/ARW"));
    }
    let main = r.directory(u64::from(u32le(&head, 4)), None)?;
    let make = text(r, &main, 0x010f)?.ok_or_else(|| unsupported("missing camera make"))?;
    let model = text(r, &main, 0x0110)?.ok_or_else(|| unsupported("missing camera model"))?;
    if make.value != "SONY" || model.value != "ILCE-7CM2" {
        return Err(unsupported(format!(
            "camera {} {}",
            make.value, model.value
        )));
    }
    let Some(raw_pointer) = main.get(0x014a) else {
        return Ok(None);
    };
    if raw_pointer.kind != 4 || raw_pointer.count != 1 {
        return Err(unsupported("requires one scalar RAW SubIFD pointer"));
    }
    let raw_ifd_offset = Reader::<R>::pointer(raw_pointer)?;
    let raw = r.directory(raw_ifd_offset, None)?;
    if scalar(r, &raw, 0x0106)?.map(|v| v.value) != Some(32803) {
        return Err(unsupported("selected SubIFD is not CFA"));
    }
    if ![0x7031, 0x7032, 0x7034, 0x7035, 0x7036, 0x7037]
        .iter()
        .any(|&tag| raw.get(tag).is_some())
    {
        return Ok(None);
    }
    let ranges = payloads(r, &raw)?;
    r.protect(ranges)?;
    let software = text(r, &main, 0x0131)?;
    let orientation = scalar(r, &main, 0x0112)?;
    let exif = main
        .get(0x8769)
        .map(|e| -> Result<_> { Ok(r.directory(Reader::<R>::pointer(e)?, None)?) })
        .transpose()?;
    let maker = if let Some(exif) = &exif {
        if let Some(e) = exif.get(0x927c) {
            if e.kind != 7 || e.count < 6 {
                return Err(malformed("invalid Sony maker note"));
            }
            let at = u64::from(e.value);
            r.range(at, u64::from(e.count))?;
            Some(r.directory(at, Some((at, u64::from(e.count))))?)
        } else {
            None
        }
    } else {
        None
    };
    let (lens_model, iso, capture_date, exposure_time, aperture, focal_length) =
        if let Some(d) = &exif {
            (
                text(r, d, 0xa434)?,
                scalar(r, d, 0x8827)?,
                text(r, d, 0x9003)?,
                rational(r, d, 0x829a)?,
                rational(r, d, 0x829d)?,
                rational(r, d, 0x920a)?,
            )
        } else {
            (None, None, None, None, None, None)
        };
    let lens_type3 = if let Some(e) = maker.as_ref().and_then(|d| d.get(0x940c)) {
        if e.kind != 7 || e.count < 11 || e.count > 65536 {
            return Err(malformed("invalid LensType3 block"));
        }
        let bytes = r.typed_bytes(e, 7, e.count)?;
        let id = u16::from_le_bytes([
            crate::identity::DECIPHER[bytes[9] as usize],
            crate::identity::DECIPHER[bytes[10] as usize],
        ]);
        Some(field(e, bytes, id))
    } else {
        None
    };
    let (maker_shading_setting, maker_ca_setting, maker_distortion_setting) =
        if let Some(d) = &maker {
            (
                setting(r, d, 0x2011)?,
                setting(r, d, 0x2012)?,
                setting(r, d, 0x2013)?,
            )
        } else {
            (None, None, None)
        };
    let cfa_pattern = if let Some(e) = raw.get(0x828e) {
        let bytes = r.typed_bytes(e, 1, 4)?;
        let value = [bytes[0], bytes[1], bytes[2], bytes[3]];
        Some(field(e, bytes, value))
    } else {
        None
    };
    let geometry = SonyRawGeometry {
        stored_width: scalar(r, &raw, 0x0100)?,
        stored_height: scalar(r, &raw, 0x0101)?,
        bits_per_sample: scalar(r, &raw, 0x0102)?,
        compression: scalar(r, &raw, 0x0103)?,
        cfa_repeat: unsigned(r, &raw, 0x828d)?,
        cfa_pattern,
        default_crop_origin: unsigned(r, &raw, 0xc61f)?,
        default_crop_size: unsigned(r, &raw, 0xc620)?,
        sony_image_size: unsigned(r, &raw, 0x7038)?,
        sony_crop_origin: unsigned(r, &raw, 0x74c7)?,
        sony_crop_size: unsigned(r, &raw, 0x74c8)?,
        active_area: unsigned(r, &raw, 0xc68d)?,
    };
    let shading = correction(r, &raw, 0x7031, 0x7032)?;
    let chromatic_aberration = correction(r, &raw, 0x7034, 0x7035)?;
    let distortion = correction(r, &raw, 0x7036, 0x7037)?;
    let header_black = unsigned(r, &raw, 0x7310)?;
    let header_white = scalar(r, &raw, 0xc61d)?;
    Ok(Some(SonyOpticalMetadata {
        make,
        model,
        software,
        orientation,
        lens_model,
        lens_type3,
        iso,
        capture_date,
        exposure_time,
        aperture,
        focal_length,
        shading,
        chromatic_aberration,
        distortion,
        maker_shading_setting,
        maker_ca_setting,
        maker_distortion_setting,
        geometry,
        header_black,
        header_white,
        raw_ifd_offset,
        source_file_bytes: r.file_bytes(),
        metadata_bytes_read: r.bytes_read(),
    }))
}

#[cfg(test)]
#[path = "sony-optical-tests.rs"]
mod tests;
