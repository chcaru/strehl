//! Optional Sony A7C II hidden focus metadata, without decoding image pixels.
//!
//! The byte format was recovered from the owner's firmware and checked against
//! independent TIFF geometry in 36 original ARWs. See
//! `experiments/rea-a7c2-2026-10-24/{results,encoding-notes,decoded-notes}.md`.
//! No prohibited decoder implementation was consulted. The permutation below is
//! factual format data, not executable firmware.
//!
//! This reader is deliberately separate from [`crate::decode`]. Missing,
//! unsupported, and malformed metadata cannot silently change RAW decoding or
//! merge decisions. The observed 33 by 23 field is preserved in serialized order;
//! units, spatial orientation, flag meanings, and measurement freshness are not
//! promised. A matching capture sequence does not prove fresh measurements: the
//! firmware has a fallback to an earlier available producer buffer.

use crate::sony_tiff::{Reader, SonyTiffError, u16le, u32le};
#[cfg(test)]
use std::collections::BTreeSet;
use std::fs::File;
#[cfg(test)]
use std::io::SeekFrom;
use std::io::{Read, Seek};
use std::path::Path;

/// Failure to inspect optional focus metadata. Absence is `Ok(None)` instead.
#[derive(Debug, thiserror::Error)]
pub enum SonyFocusError {
    #[error("focus metadata I/O: {0}")]
    Io(#[from] std::io::Error),
    #[error("unsupported focus metadata: {0}")]
    Unsupported(String),
    #[error("malformed focus metadata: {0}")]
    Malformed(String),
}

impl From<SonyTiffError> for SonyFocusError {
    fn from(error: SonyTiffError) -> Self {
        match error {
            SonyTiffError::Io(error) => Self::Io(error),
            SonyTiffError::Unsupported(message) => Self::Unsupported(message),
            SonyTiffError::Malformed(message) => Self::Malformed(message),
        }
    }
}

/// One serialized cell. These fields are observations, not a distance or confidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FocusRecord {
    pub value_bits: u16,
    pub flags: [u8; 2],
}

impl FocusRecord {
    /// Two's-complement presentation of the stored bits, with unknown units.
    /// This conversion alone does not establish the producer's signed arithmetic.
    pub fn signed_display(self) -> i16 {
        self.value_bits as i16
    }
}

/// The declared grid and its raw coordinate-like fields.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FocusGrid {
    pub sequence: u16,
    /// Four observed fields; their mapping to sensor coordinates is unvalidated.
    pub roi_raw: [u16; 4],
    pub width: u16,
    pub height: u16,
    pub origin_raw: [u16; 2],
    pub extent_raw: [u16; 2],
    /// Serialized order, with no transpose, mirror, interpolation, or filtering.
    pub records: Vec<FocusRecord>,
}

/// Section 2, whose values change more finely than ordinary FocusPosition2.
/// Their physical meaning and units remain unvalidated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FocusScalars {
    pub sequence: u16,
    pub status: u16,
    pub values_raw: [u32; 3],
}

/// Decoded metadata from the specifically supported A7C II layout.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SonyFocusMetadata {
    pub model: String,
    pub software: String,
    /// EXIF LensModel, carried verbatim for consumer compatibility checks.
    pub lens_model: Option<String>,
    /// Conventional Sony 0x9402 byte 45; coarse, not a fine motor coordinate.
    pub coarse_focus_position: Option<u8>,
    /// Conventional Sony 0x9402 byte 22, masked with 0x7f; unknown codes preserved.
    pub focus_mode: Option<u8>,
    /// Absolute offset and length of the encoded 0x2045 payload in the input file.
    pub source_offset: u64,
    pub source_length: u32,
    /// Exact encoded payload bytes from the file, including unparsed padding.
    /// Consumers may hash these bytes to identify the complete metadata payload.
    pub encoded_payload: Vec<u8>,
    /// Section 0 as little-endian words. Index 1 is its sequence field.
    pub section0: [u16; 20],
    pub grid: FocusGrid,
    pub section2: FocusScalars,
    /// Decoded trailing bytes after section 2. No semantics assigned.
    pub unknown_tail: Vec<u8>,
}

impl SonyFocusMetadata {
    pub fn sequence_fields(&self) -> [u16; 3] {
        [self.section0[1], self.grid.sequence, self.section2.sequence]
    }

    /// Image dimensions declared by the hidden block, not decoder padding.
    pub fn image_extent(&self) -> [u16; 2] {
        [self.section0[4], self.section0[5]]
    }

    /// TIFF-validated crop origin in the hidden block's image coordinates.
    pub fn crop_origin(&self) -> [u16; 2] {
        [self.section0[6], self.section0[7]]
    }

    /// TIFF-validated crop dimensions, without any resampling.
    pub fn crop_size(&self) -> [u16; 2] {
        [self.section0[8], self.section0[9]]
    }
}

/// Read optional focus metadata using bounded seeks and reads, without loading RAW pixels.
///
/// `Ok(None)` means a recognized Sony file has no hidden focus block. Unsupported
/// cameras, firmware identifiers, and layouts are distinguished from damaged data
/// by [`SonyFocusError`]. Callers choose how to surface these optional outcomes.
pub fn read(path: &Path) -> std::result::Result<Option<SonyFocusMetadata>, SonyFocusError> {
    read_from_reader(&mut File::open(path)?)
}

/// Reader form of [`read`]. The stream position after the call is unspecified.
/// Reads at most 128 KiB; directory counts and individual allocations are bounded.
pub fn read_from_reader<R: Read + Seek>(
    reader: &mut R,
) -> std::result::Result<Option<SonyFocusMetadata>, SonyFocusError> {
    Reader::new(reader)?.inspect()
}

type Result<T> = std::result::Result<T, SonyFocusError>;
const PAYLOAD_BYTES: usize = 8192;
const SUPPORTED_HEADER: [u32; 10] = [3, 0, 40, 40, 1, 3058, 80, 2, 16, 3140];
const HIDDEN_PREFIX: [u8; 12] = [0x55, 0x26, 0x11, 0x05, 0, 0, 0, 0, 0, 0, 0, 0];

// av-cam.bin (firmware 2.01), file offset 0x433b80. SHA-256 of these 256 bytes:
// 19be2ba9cb1caa6cd7493205bfcc305d7643b69846f1a96e64238ff5e46f2ff7.
// Static serializer at file 0x207030 selects this table specifically for 0x2045.
// Encoded byte = ENCODE[plain byte]. This is not the ordinary cube-mod-249 table.
const ENCODE: [u8; 256] = [
    0x00, 0x01, 0x9d, 0xc1, 0x17, 0xf0, 0x6a, 0xd5, 0x89, 0xd0, 0x31, 0xc7, 0xcd, 0x52, 0xb0, 0x5a,
    0xa4, 0x67, 0x04, 0x9f, 0x3f, 0x15, 0xc0, 0x32, 0xdd, 0xbe, 0xe4, 0x3a, 0x27, 0x07, 0xc4, 0xcc,
    0x11, 0xdf, 0xea, 0x9e, 0xac, 0xbd, 0x7d, 0x06, 0xa6, 0x7e, 0xf1, 0x38, 0xb2, 0xa7, 0x8e, 0xb9,
    0x69, 0x0b, 0x5e, 0xf3, 0xb1, 0x7f, 0x03, 0xbb, 0x54, 0x2d, 0x64, 0x8c, 0xa1, 0x55, 0x2c, 0x0d,
    0x9c, 0x83, 0x1a, 0x36, 0x41, 0xec, 0x98, 0x0a, 0x45, 0xce, 0x93, 0x76, 0xd3, 0x5f, 0x72, 0x71,
    0x4c, 0x99, 0xbf, 0x97, 0x91, 0x4f, 0x28, 0x18, 0xb7, 0x92, 0x57, 0x37, 0x66, 0xa0, 0x2b, 0x21,
    0x82, 0x65, 0xca, 0x7a, 0x58, 0x1b, 0x3b, 0xb3, 0xb5, 0x6c, 0xc6, 0x39, 0x4d, 0x24, 0xba, 0x6d,
    0xb8, 0x30, 0x94, 0x79, 0xaf, 0x16, 0xc5, 0x1d, 0xcb, 0x44, 0x14, 0x6b, 0x2f, 0x33, 0xd2, 0x4a,
    0x0c, 0xd8, 0x43, 0xdc, 0x0f, 0xe5, 0x53, 0x62, 0x68, 0x90, 0xe1, 0x0e, 0xad, 0x4b, 0x34, 0xb6,
    0x85, 0x75, 0x10, 0x5c, 0xd7, 0x4e, 0x3e, 0x35, 0xf4, 0x60, 0xe2, 0x74, 0xde, 0x49, 0x9b, 0xa9,
    0x5b, 0xe6, 0xf6, 0x29, 0xbc, 0xe3, 0xdb, 0x70, 0x7b, 0xe7, 0x84, 0x59, 0x8d, 0xd9, 0x3d, 0x2a,
    0xa2, 0x61, 0x6f, 0xcf, 0x56, 0x80, 0xb4, 0xf2, 0x96, 0x73, 0x2e, 0xa5, 0x95, 0x8a, 0x51, 0x22,
    0x9a, 0x78, 0x81, 0xa3, 0xd1, 0x86, 0xe9, 0x8b, 0x77, 0xae, 0xf7, 0xc8, 0x87, 0x63, 0x09, 0x8f,
    0x42, 0x6e, 0x48, 0x25, 0x1e, 0x1f, 0xef, 0x20, 0xd6, 0xe8, 0xeb, 0x19, 0x08, 0x5d, 0x7c, 0x3c,
    0x1c, 0xe0, 0xc3, 0xda, 0x05, 0xee, 0xed, 0x88, 0x46, 0x47, 0xf5, 0x50, 0x23, 0x26, 0xa8, 0xc9,
    0x40, 0xab, 0x02, 0xc2, 0x12, 0xd4, 0x13, 0xaa, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff,
];

const fn inverse_table() -> [u8; 256] {
    let mut inverse = [0; 256];
    let mut i = 0;
    while i < ENCODE.len() {
        inverse[ENCODE[i] as usize] = i as u8;
        i += 1;
    }
    inverse
}
const DECODE: [u8; 256] = inverse_table();

fn malformed(message: impl Into<String>) -> SonyFocusError {
    SonyFocusError::Malformed(message.into())
}

fn unsupported(message: impl Into<String>) -> SonyFocusError {
    SonyFocusError::Unsupported(message.into())
}

impl<R: Read + Seek> Reader<'_, R> {
    fn inspect(&mut self) -> Result<Option<SonyFocusMetadata>> {
        let header = self.bytes(0, 8)?;
        if &header[..2] != b"II" || u16le(&header, 2) != 42 {
            return Err(unsupported("requires little-endian classic TIFF/ARW"));
        }
        let main = self.directory(u32le(&header, 4) as u64, None)?;
        let make = self.text(main.required(0x010f)?)?;
        let model = self.text(main.required(0x0110)?)?;
        if make != "SONY" || model != "ILCE-7CM2" {
            return Err(unsupported(format!("camera {make} {model}")));
        }
        let Some(exif_pointer) = main.get(0x8769) else {
            return Ok(None);
        };
        let exif = self.directory(Self::pointer(exif_pointer)?, None)?;
        let Some(maker_entry) = exif.get(0x927c) else {
            return Ok(None);
        };
        if maker_entry.kind != 7 || maker_entry.count < 6 {
            return Err(malformed("invalid Sony maker-note value"));
        }
        let maker_offset = maker_entry.value as u64;
        self.range(maker_offset, maker_entry.count as u64)?;
        let maker = self.directory(maker_offset, Some((maker_offset, maker_entry.count as u64)))?;
        let Some(hidden_entry) = maker.get(0x2044) else {
            return Ok(None);
        };
        let software = self.text(main.required(0x0131)?)?;
        if software != "ILCE-7CM2 v2.00" && software != "ILCE-7CM2 v2.01" {
            return Err(unsupported(format!("firmware identifier {software}")));
        }
        let lens_model = exif.get(0xa434).map(|entry| self.text(entry)).transpose()?;
        let hidden_info = self.typed_bytes(hidden_entry, 4, 2)?;
        let hidden_offset = u32le(&hidden_info, 0) as u64;
        let hidden_length = u32le(&hidden_info, 4) as u64;
        self.range(hidden_offset, hidden_length)?;
        if hidden_length < 26 {
            return Err(malformed("hidden directory is truncated"));
        }
        let hidden = self.bytes(hidden_offset, 26)?;
        if hidden[..12] != HIDDEN_PREFIX {
            return Err(unsupported("unknown hidden-directory signature"));
        }
        if u16le(&hidden, 12) != 1 {
            return Err(unsupported("unknown hidden-directory entry count"));
        }
        if u16le(&hidden, 14) != 0x2045 {
            return Err(unsupported(
                "hidden directory does not contain supported tag 0x2045",
            ));
        }
        if u16le(&hidden, 16) != 7 {
            return Err(malformed("hidden 0x2045 is not a byte payload"));
        }
        let payload_length = u32le(&hidden, 18);
        if payload_length != PAYLOAD_BYTES as u32 {
            return Err(unsupported(format!(
                "hidden payload length {payload_length}"
            )));
        }
        let payload_offset = u32le(&hidden, 22) as u64;
        let hidden_end = hidden_offset + hidden_length; // checked by range above
        if payload_offset < hidden_offset + 26
            || payload_offset
                .checked_add(payload_length as u64)
                .is_none_or(|end| end > hidden_end)
        {
            return Err(malformed("hidden payload escapes its declared block"));
        }
        let encoded_payload = self.bytes(payload_offset, PAYLOAD_BYTES)?;
        let mut plain = encoded_payload.clone();
        for byte in &mut plain {
            *byte = DECODE[*byte as usize];
        }
        let (section0, grid, section2) = decode_sections(&plain)?;

        // Independent TIFF geometry rejects wrong byte transformations even when
        // their guessed descriptor header happens to match. Never use padding.
        let raw = self.directory(Self::pointer(main.required(0x014a)?)?, None)?;
        let crop_origin = self.pair(raw.required(0xc61f)?)?;
        let crop_size = self.pair(raw.required(0xc620)?)?;
        if section0[6..10] != [crop_origin[0], crop_origin[1], crop_size[0], crop_size[1]] {
            return Err(malformed("decoded hidden crop disagrees with TIFF crop"));
        }
        if let Some(dimensions) = raw.get(0x7038)
            && section0[4..6] != self.pair(dimensions)?
        {
            return Err(malformed("decoded hidden dimensions disagree with TIFF"));
        }
        let (coarse_focus_position, focus_mode) = if let Some(entry) = maker.get(0x9402) {
            let bytes = self.typed_bytes(entry, 7, 400)?;
            (
                Some(crate::identity::DECIPHER[bytes[45] as usize]),
                Some(crate::identity::DECIPHER[bytes[22] as usize] & 0x7f),
            )
        } else {
            (None, None)
        };
        Ok(Some(SonyFocusMetadata {
            model,
            software,
            lens_model,
            coarse_focus_position,
            focus_mode,
            source_offset: payload_offset,
            source_length: payload_length,
            encoded_payload,
            section0,
            grid,
            section2,
            unknown_tail: plain[3156..].to_vec(),
        }))
    }
}

fn decode_sections(plain: &[u8]) -> Result<([u16; 20], FocusGrid, FocusScalars)> {
    if plain.len() != PAYLOAD_BYTES {
        return Err(malformed("decoded payload length is incorrect"));
    }
    let count = u32le(plain, 0);
    if count != 3 {
        return Err(unsupported(format!("unknown hidden section count {count}")));
    }
    let mut ranges = Vec::with_capacity(3);
    for i in 0..3 {
        let length = u32le(plain, 8 + i * 12) as u64;
        let start = u32le(plain, 12 + i * 12) as u64;
        let end = start
            .checked_add(length)
            .ok_or_else(|| malformed("hidden section extent overflow"))?;
        if start < 40 || end > PAYLOAD_BYTES as u64 {
            return Err(malformed("hidden section extends outside payload"));
        }
        if ranges
            .iter()
            .any(|&(other_start, other_end)| start < other_end && end > other_start)
        {
            return Err(malformed("overlapping hidden sections"));
        }
        ranges.push((start, end));
    }
    if SUPPORTED_HEADER
        .iter()
        .enumerate()
        .any(|(i, &expected)| u32le(plain, i * 4) != expected)
    {
        return Err(unsupported("unknown hidden section types or layout"));
    }
    let section0: [u16; 20] = std::array::from_fn(|i| u16le(plain, 40 + 2 * i));
    let [image_width, image_height] = [section0[4], section0[5]];
    let [crop_x, crop_y, crop_width, crop_height] =
        [section0[6], section0[7], section0[8], section0[9]];
    if image_width == 0
        || image_height == 0
        || crop_width == 0
        || crop_height == 0
        || u32::from(crop_x) + u32::from(crop_width) > u32::from(image_width)
        || u32::from(crop_y) + u32::from(crop_height) > u32::from(image_height)
    {
        return Err(malformed("empty or out-of-image hidden crop geometry"));
    }
    let header: [u16; 11] = std::array::from_fn(|i| u16le(plain, 80 + 2 * i));
    if header[5..7] != [33, 23] || header[9..11] != [33, 23] {
        return Err(unsupported("unknown hidden focus grid dimensions"));
    }
    let records = plain[102..3138]
        .as_chunks::<4>()
        .0
        .iter()
        .map(|bytes| FocusRecord {
            value_bits: u16le(bytes, 0),
            flags: [bytes[2], bytes[3]],
        })
        .collect();
    let grid = FocusGrid {
        sequence: header[0],
        roi_raw: [header[1], header[2], header[3], header[4]],
        width: header[5],
        height: header[6],
        origin_raw: [header[7], header[8]],
        extent_raw: [header[9], header[10]],
        records,
    };
    let section2 = FocusScalars {
        sequence: u16le(plain, 3140),
        status: u16le(plain, 3142),
        values_raw: std::array::from_fn(|i| u32le(plain, 3144 + i * 4)),
    };
    Ok((section0, grid, section2))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    const HIDDEN: usize = 1024;
    const PAYLOAD: usize = HIDDEN + 26;

    fn word(bytes: &mut [u8], at: usize, value: u16) {
        bytes[at..at + 2].copy_from_slice(&value.to_le_bytes());
    }
    fn long(bytes: &mut [u8], at: usize, value: u32) {
        bytes[at..at + 4].copy_from_slice(&value.to_le_bytes());
    }
    fn ifd(bytes: &mut [u8], at: usize, entries: &[(u16, u16, u32, u32)]) {
        word(bytes, at, entries.len() as u16);
        for (i, &(tag, kind, count, value)) in entries.iter().enumerate() {
            let p = at + 2 + 12 * i;
            word(bytes, p, tag);
            word(bytes, p + 2, kind);
            long(bytes, p + 4, count);
            long(bytes, p + 8, value);
        }
    }
    fn plain_fixture() -> Vec<u8> {
        let mut plain = vec![0; PAYLOAD_BYTES];
        for (i, value) in SUPPORTED_HEADER.iter().enumerate() {
            long(&mut plain, 4 * i, *value);
        }
        let section0 = [1, 23, 0, 0, 7032, 4688, 12, 8, 7008, 4672];
        for (i, value) in section0.iter().enumerate() {
            word(&mut plain, 40 + i * 2, *value);
        }
        let header = [23, 352, 175, 6329, 4337, 33, 23, 0, 0, 33, 23];
        for (i, value) in header.iter().enumerate() {
            word(&mut plain, 80 + i * 2, *value);
        }
        word(&mut plain, 102, (-32000_i16) as u16);
        plain[104..106].copy_from_slice(&[2, 160]);
        word(&mut plain, 3134, 1234);
        word(&mut plain, 3140, 23);
        word(&mut plain, 3142, 3);
        long(&mut plain, 3144, 18561);
        long(&mut plain, 3148, 18543);
        plain[3156..].fill(0x5a);
        plain
    }
    fn set_plain(file: &mut [u8], plain: &[u8]) {
        for (dst, src) in file[PAYLOAD..PAYLOAD + PAYLOAD_BYTES].iter_mut().zip(plain) {
            *dst = ENCODE[*src as usize];
        }
    }
    fn fixture() -> Vec<u8> {
        let mut bytes = vec![0; HIDDEN + 53248];
        bytes[..4].copy_from_slice(b"II*\0");
        long(&mut bytes, 4, 8);
        ifd(
            &mut bytes,
            8,
            &[
                (0x010f, 2, 5, 100),
                (0x0110, 2, 11, 120),
                (0x0131, 2, 16, 140),
                (0x8769, 4, 1, 200),
                (0x014a, 4, 1, 400),
            ],
        );
        bytes[100..105].copy_from_slice(b"SONY\0");
        bytes[120..131].copy_from_slice(b"ILCE-7CM2\0\0");
        bytes[140..156].copy_from_slice(b"ILCE-7CM2 v2.00\0");
        ifd(
            &mut bytes,
            200,
            &[(0x927c, 7, 760, 240), (0xa434, 2, 13, 280)],
        );
        bytes[280..293].copy_from_slice(b"Fixture lens\0");
        ifd(
            &mut bytes,
            240,
            &[(0x2044, 4, 2, 512), (0x9402, 7, 400, 600)],
        );
        ifd(
            &mut bytes,
            400,
            &[
                (0xc61f, 3, 2, 12 | (8 << 16)),
                (0xc620, 3, 2, 7008 | (4672 << 16)),
                (0x7038, 3, 2, 7032 | (4688 << 16)),
            ],
        );
        long(&mut bytes, 512, HIDDEN as u32);
        long(&mut bytes, 516, 53248);
        bytes[600 + 45] = 71;
        bytes[HIDDEN..HIDDEN + 12].copy_from_slice(&HIDDEN_PREFIX);
        word(&mut bytes, HIDDEN + 12, 1);
        word(&mut bytes, HIDDEN + 14, 0x2045);
        word(&mut bytes, HIDDEN + 16, 7);
        long(&mut bytes, HIDDEN + 18, PAYLOAD_BYTES as u32);
        long(&mut bytes, HIDDEN + 22, PAYLOAD as u32);
        set_plain(&mut bytes, &plain_fixture());
        bytes
    }
    fn parse(bytes: Vec<u8>) -> Result<Option<SonyFocusMetadata>> {
        read_from_reader(&mut Cursor::new(bytes))
    }

    #[test]
    fn relocated_hidden_block_decodes_values_flags_and_independent_geometry() {
        let metadata = parse(fixture()).unwrap().unwrap();
        assert_eq!(metadata.source_offset, PAYLOAD as u64);
        assert_eq!(metadata.source_length, 8192);
        assert_eq!(
            metadata.encoded_payload,
            fixture()[PAYLOAD..PAYLOAD + PAYLOAD_BYTES]
        );
        assert_eq!(metadata.coarse_focus_position, Some(56));
        assert_eq!(metadata.focus_mode, Some(0));
        assert_eq!(metadata.lens_model.as_deref(), Some("Fixture lens"));
        assert_eq!(metadata.sequence_fields(), [23; 3]);
        assert_eq!(metadata.image_extent(), [7032, 4688]);
        assert_eq!(metadata.crop_origin(), [12, 8]);
        assert_eq!(metadata.crop_size(), [7008, 4672]);
        assert_eq!(metadata.grid.roi_raw, [352, 175, 6329, 4337]);
        assert_eq!(metadata.grid.records.len(), 759);
        assert_eq!(metadata.grid.records[0].signed_display(), -32000);
        assert_eq!(metadata.grid.records[0].flags, [2, 160]);
        assert_eq!(metadata.grid.records[758].value_bits, 1234);
        assert_eq!(metadata.section2.values_raw, [18561, 18543, 0]);
        assert_eq!(metadata.unknown_tail, vec![0x5a; 5036]);
    }

    #[test]
    fn absence_is_distinct_from_unknown_camera_and_firmware() {
        let mut absent = fixture();
        word(&mut absent, 242, 0x2043);
        assert!(parse(absent).unwrap().is_none());
        let mut camera = fixture();
        camera[128] = b'3';
        assert!(matches!(parse(camera), Err(SonyFocusError::Unsupported(_))));
        let mut version = fixture();
        version[151] = b'3';
        assert!(matches!(
            parse(version),
            Err(SonyFocusError::Unsupported(_))
        ));
    }

    #[test]
    fn directory_cycles_duplicates_and_excessive_counts_are_rejected() {
        let mut cyclic = fixture();
        long(&mut cyclic, 8 + 2 + 3 * 12 + 8, 8);
        let mut duplicate = fixture();
        word(&mut duplicate, 8 + 2 + 12, 0x010f);
        let mut excessive = fixture();
        word(&mut excessive, 240, u16::MAX);
        for bad in [cyclic, duplicate, excessive] {
            assert!(matches!(parse(bad), Err(SonyFocusError::Malformed(_))));
        }
    }

    #[test]
    fn every_relevant_truncation_and_escaping_payload_is_rejected() {
        let bytes = fixture();
        for at in [0, 7, 20, 203, 250, 516, HIDDEN + 25, PAYLOAD + 8191] {
            assert!(parse(bytes[..at].to_vec()).is_err(), "truncation {at}");
        }
        let mut outside = fixture();
        long(&mut outside, HIDDEN + 22, u32::MAX);
        assert!(matches!(parse(outside), Err(SonyFocusError::Malformed(_))));
        let mut before = fixture();
        long(&mut before, HIDDEN + 22, 100);
        assert!(matches!(parse(before), Err(SonyFocusError::Malformed(_))));
        let mut short_maker = fixture();
        long(&mut short_maker, 200 + 2 + 4, 6);
        assert!(matches!(
            parse(short_maker),
            Err(SonyFocusError::Malformed(_))
        ));
    }

    #[test]
    fn overlapping_sections_and_header_preserving_wrong_geometry_fail() {
        let mut plain = plain_fixture();
        long(&mut plain, 24, 40); // section 1 now overlaps section 0
        assert!(matches!(
            decode_sections(&plain),
            Err(SonyFocusError::Malformed(_))
        ));
        let mut file = fixture();
        let mut wrong = plain_fixture();
        word(&mut wrong, 48, 7033); // header untouched; independent geometry is wrong
        set_plain(&mut file, &wrong);
        assert!(matches!(parse(file), Err(SonyFocusError::Malformed(_))));
    }

    #[test]
    fn internally_impossible_geometry_fails_even_without_independent_image_extent_tag() {
        for (at, value) in [(48, 0), (50, 0), (56, 0), (58, 0), (52, 7032), (54, 4688)] {
            let mut file = fixture();
            word(&mut file, 400 + 2 + 2 * 12, 0x7039); // no tag 0x7038
            let mut plain = plain_fixture();
            word(&mut plain, at, value);
            // Make TIFF crop agree with the corrupted hidden crop, so a simple
            // two-reader equality check alone would accept this input.
            let origin = u16le(&plain, 52) as u32 | ((u16le(&plain, 54) as u32) << 16);
            let size = u16le(&plain, 56) as u32 | ((u16le(&plain, 58) as u32) << 16);
            long(&mut file, 400 + 2 + 8, origin);
            long(&mut file, 400 + 2 + 12 + 8, size);
            set_plain(&mut file, &plain);
            assert!(
                matches!(parse(file), Err(SonyFocusError::Malformed(_))),
                "field {at}"
            );
        }
        let mut ordinary = fixture();
        word(&mut ordinary, 400 + 2 + 2 * 12, 0x7039);
        assert!(parse(ordinary).unwrap().is_some());
    }

    #[test]
    fn optional_lens_identity_is_preserved_or_explicitly_absent() {
        let mut file = fixture();
        word(&mut file, 200 + 2 + 12, 0xa433);
        assert_eq!(parse(file).unwrap().unwrap().lens_model, None);
    }

    #[test]
    fn unknown_layout_is_not_reported_as_absent() {
        let mut file = fixture();
        let mut plain = plain_fixture();
        word(&mut plain, 90, 34);
        set_plain(&mut file, &plain);
        assert!(matches!(parse(file), Err(SonyFocusError::Unsupported(_))));
        let mut legacy = fixture();
        for (dst, src) in legacy[PAYLOAD..PAYLOAD + PAYLOAD_BYTES]
            .iter_mut()
            .zip(plain_fixture())
        {
            let x = src as usize;
            *dst = if x < 249 {
                ((x * x * x) % 249) as u8
            } else {
                src
            };
        }
        assert!(parse(legacy).is_err());
    }

    #[test]
    fn all_record_bits_and_sequence_disagreement_are_preserved() {
        let mut file = fixture();
        let mut plain = plain_fixture();
        word(&mut plain, 102, u16::MAX);
        plain[104..106].copy_from_slice(&[0xff, 0xff]);
        word(&mut plain, 3140, 12);
        set_plain(&mut file, &plain);
        let metadata = parse(file).unwrap().unwrap();
        assert_eq!(metadata.grid.records[0].value_bits, u16::MAX);
        assert_eq!(metadata.grid.records[0].flags, [0xff, 0xff]);
        assert_eq!(metadata.sequence_fields(), [23, 23, 12]);
    }

    #[test]
    fn byte_table_is_bijective_and_matches_independent_header_witnesses() {
        let unique: BTreeSet<_> = ENCODE.iter().copied().collect();
        assert_eq!(unique.len(), 256);
        for (plain, &encoded) in ENCODE.iter().enumerate() {
            assert_eq!(DECODE[encoded as usize], plain as u8);
        }
        for (plain, encoded) in [(2, 157), (3, 193), (40, 166), (80, 76), (242, 2)] {
            assert_eq!(ENCODE[plain], encoded);
        }
    }

    #[test]
    fn bounded_reader_does_not_read_raw_pixel_payload() {
        struct Counted {
            inner: Cursor<Vec<u8>>,
            count: usize,
        }
        impl Read for Counted {
            fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
                let n = self.inner.read(buf)?;
                self.count += n;
                Ok(n)
            }
        }
        impl Seek for Counted {
            fn seek(&mut self, pos: SeekFrom) -> std::io::Result<u64> {
                self.inner.seek(pos)
            }
        }
        let mut reader = Counted {
            inner: Cursor::new(fixture()),
            count: 0,
        };
        assert!(read_from_reader(&mut reader).unwrap().is_some());
        assert!(reader.count < 10 * 1024, "read {} bytes", reader.count);
    }

    #[test]
    #[ignore = "private read-only first witness; set STREHL_SONY_FOCUS_RAW to 119MSDCF/DSC00024.ARW"]
    fn real_first_witness_agrees_with_independent_python_decode() {
        let path = std::env::var_os("STREHL_SONY_FOCUS_RAW").expect("set STREHL_SONY_FOCUS_RAW");
        let metadata = read(Path::new(&path)).unwrap().unwrap();
        assert_eq!(metadata.software, "ILCE-7CM2 v2.00");
        assert_eq!(metadata.sequence_fields(), [23; 3]);
        assert_eq!(metadata.coarse_focus_position, Some(56));
        assert_eq!(metadata.section2.values_raw, [18561, 18543, 0]);
        assert_eq!(metadata.grid.records[0].signed_display(), 32000);
        assert_eq!(metadata.grid.records[2].signed_display(), -1280);
        assert_eq!(metadata.grid.records[758].signed_display(), -2784);
        assert_eq!(metadata.grid.records[758].flags, [2, 128]);
    }
}
