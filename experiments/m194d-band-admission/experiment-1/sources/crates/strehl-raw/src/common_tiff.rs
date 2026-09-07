//! Strict adapter for the scorecard's common-merge TIFF contract.
//!
//! The adapter accepts only little-endian classic TIFFs whose image samples are
//! uncompressed, interleaved RGB16 with unsigned integer samples. Optional
//! development metadata is rejected: outside the structural TIFF fields, the
//! only accepted tags are one canonical provenance string and one frozen ICC
//! profile.
//!
//! The payload hash is over the concatenated strip bytes in image order. The
//! internal hash is recomputed from the decoded `u16` buffer in little-endian
//! interleaved RGB order. Equality therefore proves that parsing did not move,
//! scale, clip, byte-swap, or otherwise alter a sample before the merge-facing
//! boundary.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::path::Path;

const TAG_IMAGE_WIDTH: u16 = 256;
const TAG_IMAGE_LENGTH: u16 = 257;
const TAG_BITS_PER_SAMPLE: u16 = 258;
const TAG_COMPRESSION: u16 = 259;
const TAG_PHOTOMETRIC: u16 = 262;
const TAG_IMAGE_DESCRIPTION: u16 = 270;
const TAG_STRIP_OFFSETS: u16 = 273;
const TAG_SAMPLES_PER_PIXEL: u16 = 277;
const TAG_ROWS_PER_STRIP: u16 = 278;
const TAG_STRIP_BYTE_COUNTS: u16 = 279;
const TAG_PLANAR_CONFIGURATION: u16 = 284;
const TAG_SAMPLE_FORMAT: u16 = 339;
const TAG_ICC_PROFILE: u16 = 34_675;

const TYPE_BYTE: u16 = 1;
const TYPE_ASCII: u16 = 2;
const TYPE_SHORT: u16 = 3;
const TYPE_LONG: u16 = 4;
const TYPE_UNDEFINED: u16 = 7;

const ALLOWED_TAGS: [u16; 13] = [
    TAG_IMAGE_WIDTH,
    TAG_IMAGE_LENGTH,
    TAG_BITS_PER_SAMPLE,
    TAG_COMPRESSION,
    TAG_PHOTOMETRIC,
    TAG_IMAGE_DESCRIPTION,
    TAG_STRIP_OFFSETS,
    TAG_SAMPLES_PER_PIXEL,
    TAG_ROWS_PER_STRIP,
    TAG_STRIP_BYTE_COUNTS,
    TAG_PLANAR_CONFIGURATION,
    TAG_SAMPLE_FORMAT,
    TAG_ICC_PROFILE,
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommonTiffError {
    message: String,
}

impl CommonTiffError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl fmt::Display for CommonTiffError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}

impl std::error::Error for CommonTiffError {}

pub type Result<T> = std::result::Result<T, CommonTiffError>;

#[derive(Debug, Clone, Default)]
pub struct ExpectedIdentity {
    pub file_sha256: Option<String>,
    pub pixel_payload_sha256: Option<String>,
    pub icc_sha256: Option<String>,
    pub source_sha256: Option<String>,
    pub converter_sha256: Option<String>,
    pub settings_sha256: Option<String>,
    pub pattern_map_sha256: Option<String>,
    pub pattern_manifest_sha256: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Strip {
    pub offset: u32,
    pub byte_count: u32,
}

#[derive(Debug, Clone)]
pub struct CommonTiffFrame {
    pub width: u32,
    pub height: u32,
    pub pixels: Vec<u16>,
    pub provenance: String,
    pub strips: Vec<Strip>,
    pub file_sha256: String,
    pub pixel_payload_sha256: String,
    pub internal_pixel_sha256: String,
    pub icc_sha256: String,
}

impl CommonTiffFrame {
    pub fn read(path: &Path) -> Result<Self> {
        let bytes = std::fs::read(path)
            .map_err(|e| CommonTiffError::new(format!("reading {}: {e}", path.display())))?;
        Self::parse(&bytes)
    }

    pub fn parse(bytes: &[u8]) -> Result<Self> {
        if bytes.len() < 8 {
            return Err(CommonTiffError::new(
                "TIFF is shorter than its 8-byte header",
            ));
        }
        if &bytes[0..2] != b"II" {
            return Err(CommonTiffError::new(
                "only little-endian TIFF is admitted by the common-input contract",
            ));
        }
        if le_u16(bytes, 2)? != 42 {
            return Err(CommonTiffError::new("invalid classic-TIFF magic"));
        }
        let ifd_offset = usize::try_from(le_u32(bytes, 4)?)
            .map_err(|_| CommonTiffError::new("IFD offset does not fit this host"))?;
        let count = usize::from(le_u16(bytes, ifd_offset)?);
        let table_start = checked_add(ifd_offset, 2, "IFD table start")?;
        let table_bytes = checked_mul(count, 12, "IFD table size")?;
        let next_ifd_at = checked_add(table_start, table_bytes, "next-IFD field")?;
        require_range(bytes, next_ifd_at, 4, "next-IFD field")?;
        if le_u32(bytes, next_ifd_at)? != 0 {
            return Err(CommonTiffError::new(
                "multi-image TIFF is forbidden by the common-input contract",
            ));
        }

        let allowed: BTreeSet<u16> = ALLOWED_TAGS.into_iter().collect();
        let mut entries = BTreeMap::new();
        for i in 0..count {
            let at = checked_add(table_start, checked_mul(i, 12, "IFD entry")?, "IFD entry")?;
            require_range(bytes, at, 12, "IFD entry")?;
            let entry = Entry {
                tag: le_u16(bytes, at)?,
                kind: le_u16(bytes, at + 2)?,
                count: le_u32(bytes, at + 4)?,
                value_or_offset: [bytes[at + 8], bytes[at + 9], bytes[at + 10], bytes[at + 11]],
            };
            if !allowed.contains(&entry.tag) {
                return Err(CommonTiffError::new(format!(
                    "TIFF tag {} is not structural, provenance, or ICC; development tags are forbidden",
                    entry.tag
                )));
            }
            if entries.insert(entry.tag, entry).is_some() {
                return Err(CommonTiffError::new(format!(
                    "duplicate TIFF tag {}",
                    entry.tag
                )));
            }
        }

        for tag in ALLOWED_TAGS {
            if !entries.contains_key(&tag) {
                return Err(CommonTiffError::new(format!(
                    "required TIFF tag {tag} is absent"
                )));
            }
        }

        let width = scalar_u32(bytes, entry(&entries, TAG_IMAGE_WIDTH)?)?;
        let height = scalar_u32(bytes, entry(&entries, TAG_IMAGE_LENGTH)?)?;
        if width == 0 || height == 0 {
            return Err(CommonTiffError::new("TIFF dimensions must be non-zero"));
        }

        let bits = short_values(bytes, entry(&entries, TAG_BITS_PER_SAMPLE)?)?;
        if bits != [16, 16, 16] {
            return Err(CommonTiffError::new(format!(
                "BitsPerSample must be [16,16,16], got {bits:?}"
            )));
        }
        require_scalar(bytes, entry(&entries, TAG_COMPRESSION)?, 1, "Compression")?;
        require_scalar(
            bytes,
            entry(&entries, TAG_PHOTOMETRIC)?,
            2,
            "PhotometricInterpretation",
        )?;
        require_scalar(
            bytes,
            entry(&entries, TAG_SAMPLES_PER_PIXEL)?,
            3,
            "SamplesPerPixel",
        )?;
        require_scalar(
            bytes,
            entry(&entries, TAG_PLANAR_CONFIGURATION)?,
            1,
            "PlanarConfiguration",
        )?;
        let sample_format = short_values(bytes, entry(&entries, TAG_SAMPLE_FORMAT)?)?;
        if sample_format != [1, 1, 1] {
            return Err(CommonTiffError::new(format!(
                "SampleFormat must be unsigned integer [1,1,1], got {sample_format:?}"
            )));
        }

        let rows_per_strip = scalar_u32(bytes, entry(&entries, TAG_ROWS_PER_STRIP)?)?;
        if rows_per_strip == 0 {
            return Err(CommonTiffError::new("RowsPerStrip must be non-zero"));
        }
        let offsets = unsigned_values(bytes, entry(&entries, TAG_STRIP_OFFSETS)?)?;
        let counts = unsigned_values(bytes, entry(&entries, TAG_STRIP_BYTE_COUNTS)?)?;
        let expected_strips = height.div_ceil(rows_per_strip) as usize;
        if offsets.len() != expected_strips || counts.len() != expected_strips {
            return Err(CommonTiffError::new(format!(
                "strip table has offsets={} counts={}, expected {expected_strips}",
                offsets.len(),
                counts.len()
            )));
        }

        let row_bytes = u64::from(width)
            .checked_mul(6)
            .ok_or_else(|| CommonTiffError::new("row byte count overflow"))?;
        let expected_payload = row_bytes
            .checked_mul(u64::from(height))
            .ok_or_else(|| CommonTiffError::new("pixel payload size overflow"))?;
        let mut payload = Vec::with_capacity(
            usize::try_from(expected_payload)
                .map_err(|_| CommonTiffError::new("pixel payload does not fit this host"))?,
        );
        let mut strips = Vec::with_capacity(expected_strips);
        for i in 0..expected_strips {
            let first_row = u64::try_from(i)
                .ok()
                .and_then(|v| v.checked_mul(u64::from(rows_per_strip)))
                .ok_or_else(|| CommonTiffError::new("strip row offset overflow"))?;
            let rows = u64::from(height)
                .saturating_sub(first_row)
                .min(u64::from(rows_per_strip));
            let expected_count = rows
                .checked_mul(row_bytes)
                .ok_or_else(|| CommonTiffError::new("strip byte count overflow"))?;
            if u64::from(counts[i]) != expected_count {
                return Err(CommonTiffError::new(format!(
                    "strip {i} has {} bytes, expected {expected_count}",
                    counts[i]
                )));
            }
            let at = usize::try_from(offsets[i])
                .map_err(|_| CommonTiffError::new("strip offset does not fit this host"))?;
            let len = usize::try_from(counts[i])
                .map_err(|_| CommonTiffError::new("strip length does not fit this host"))?;
            require_range(bytes, at, len, "pixel strip")?;
            payload.extend_from_slice(&bytes[at..at + len]);
            strips.push(Strip {
                offset: offsets[i],
                byte_count: counts[i],
            });
        }
        if payload.len() as u64 != expected_payload {
            return Err(CommonTiffError::new(format!(
                "pixel payload has {} bytes, expected {expected_payload}",
                payload.len()
            )));
        }

        let mut pixels = Vec::with_capacity(payload.len() / 2);
        let (pairs, remainder) = payload.as_chunks::<2>();
        if !remainder.is_empty() {
            return Err(CommonTiffError::new("RGB16 payload has an odd byte count"));
        }
        for pair in pairs {
            pixels.push(u16::from_le_bytes(*pair));
        }
        let mut internal = Sha256::new();
        for sample in &pixels {
            internal.update(&sample.to_le_bytes());
        }

        let provenance_bytes = entry_data(bytes, entry(&entries, TAG_IMAGE_DESCRIPTION)?)?;
        if entry(&entries, TAG_IMAGE_DESCRIPTION)?.kind != TYPE_ASCII {
            return Err(CommonTiffError::new(
                "ImageDescription provenance must use TIFF ASCII",
            ));
        }
        if provenance_bytes.last() != Some(&0) {
            return Err(CommonTiffError::new(
                "ImageDescription provenance must be NUL-terminated ASCII",
            ));
        }
        let provenance = std::str::from_utf8(&provenance_bytes[..provenance_bytes.len() - 1])
            .map_err(|e| CommonTiffError::new(format!("provenance is not UTF-8: {e}")))?
            .to_string();

        let icc_entry = entry(&entries, TAG_ICC_PROFILE)?;
        if icc_entry.kind != TYPE_UNDEFINED && icc_entry.kind != TYPE_BYTE {
            return Err(CommonTiffError::new(format!(
                "ICC profile has TIFF type {}, expected UNDEFINED or BYTE",
                icc_entry.kind
            )));
        }
        let icc = entry_data(bytes, icc_entry)?;
        if icc.len() < 128 || &icc[36..40] != b"acsp" {
            return Err(CommonTiffError::new(
                "embedded ICC profile is absent or malformed",
            ));
        }

        Ok(Self {
            width,
            height,
            pixels,
            provenance,
            strips,
            file_sha256: sha256_hex(bytes),
            pixel_payload_sha256: sha256_hex(&payload),
            internal_pixel_sha256: hex(&internal.finish()),
            icc_sha256: sha256_hex(&icc),
        })
    }

    pub fn verify(&self, expected: &ExpectedIdentity) -> Result<()> {
        compare_hash(
            "pixel payload",
            &self.pixel_payload_sha256,
            expected.pixel_payload_sha256.as_deref(),
        )?;
        compare_hash(
            "ICC profile",
            &self.icc_sha256,
            expected.icc_sha256.as_deref(),
        )?;
        if self.pixel_payload_sha256 != self.internal_pixel_sha256 {
            return Err(CommonTiffError::new(format!(
                "internal pre-merge bytes diverge from TIFF payload: payload {} internal {}",
                self.pixel_payload_sha256, self.internal_pixel_sha256
            )));
        }
        compare_provenance(
            &self.provenance,
            "source_sha256",
            expected.source_sha256.as_deref(),
        )?;
        compare_provenance(
            &self.provenance,
            "converter_executable_sha256",
            expected.converter_sha256.as_deref(),
        )?;
        compare_provenance(
            &self.provenance,
            "settings_sha256",
            expected.settings_sha256.as_deref(),
        )?;
        compare_provenance(
            &self.provenance,
            "pattern_map_sha256",
            expected.pattern_map_sha256.as_deref(),
        )?;
        compare_provenance(
            &self.provenance,
            "pattern_manifest_sha256",
            expected.pattern_manifest_sha256.as_deref(),
        )?;
        compare_hash(
            "whole TIFF",
            &self.file_sha256,
            expected.file_sha256.as_deref(),
        )?;
        Ok(())
    }

    /// The three full-resolution planes presented to an RGB merge.
    pub fn merge_planes(&self) -> [Vec<f32>; 3] {
        let count = self.pixels.len() / 3;
        let mut planes: [Vec<f32>; 3] = std::array::from_fn(|_| Vec::with_capacity(count));
        let (rgb_pixels, remainder) = self.pixels.as_chunks::<3>();
        debug_assert!(remainder.is_empty());
        for rgb in rgb_pixels {
            planes[0].push(f32::from(rgb[0]));
            planes[1].push(f32::from(rgb[1]));
            planes[2].push(f32::from(rgb[2]));
        }
        planes
    }

    /// Reconstruct the canonical interleaved payload from the exact `f32`
    /// samples that a merge receives.
    pub fn merge_sample_sha256(&self) -> Result<String> {
        let planes = self.merge_planes();
        Self::hash_merge_planes(&planes)
    }

    /// Hash merge-facing planes back into canonical interleaved RGB16 order.
    ///
    /// A caller can hash the exact allocations it is about to pass to the core
    /// merge, rather than asking the adapter to create a second equivalent set.
    pub fn hash_merge_planes(planes: &[Vec<f32>]) -> Result<String> {
        if planes.len() != 3 {
            return Err(CommonTiffError::new(format!(
                "common RGB input requires three merge planes, got {}",
                planes.len()
            )));
        }
        let count = planes[0].len();
        if planes.iter().any(|plane| plane.len() != count) {
            return Err(CommonTiffError::new("merge plane length mismatch"));
        }
        let mut hash = Sha256::new();
        for i in 0..count {
            for plane in planes {
                let value = plane[i];
                if !value.is_finite()
                    || value < 0.0
                    || value > f32::from(u16::MAX)
                    || value.fract() != 0.0
                {
                    return Err(CommonTiffError::new(format!(
                        "merge sample {value} is not an exact RGB16 integer"
                    )));
                }
                hash.update(&(value as u16).to_le_bytes());
            }
        }
        Ok(hex(&hash.finish()))
    }
}

#[derive(Debug, Clone, Copy)]
struct Entry {
    tag: u16,
    kind: u16,
    count: u32,
    value_or_offset: [u8; 4],
}

fn entry(entries: &BTreeMap<u16, Entry>, tag: u16) -> Result<&Entry> {
    entries
        .get(&tag)
        .ok_or_else(|| CommonTiffError::new(format!("required TIFF tag {tag} is absent")))
}

fn type_size(kind: u16) -> Result<usize> {
    match kind {
        TYPE_BYTE | TYPE_ASCII | TYPE_UNDEFINED => Ok(1),
        TYPE_SHORT => Ok(2),
        TYPE_LONG => Ok(4),
        _ => Err(CommonTiffError::new(format!(
            "unsupported TIFF field type {kind}"
        ))),
    }
}

fn entry_data(bytes: &[u8], entry: &Entry) -> Result<Vec<u8>> {
    let len = checked_mul(
        usize::try_from(entry.count)
            .map_err(|_| CommonTiffError::new("TIFF value count does not fit this host"))?,
        type_size(entry.kind)?,
        "TIFF value size",
    )?;
    if len <= 4 {
        return Ok(entry.value_or_offset[..len].to_vec());
    }
    let offset = usize::try_from(u32::from_le_bytes(entry.value_or_offset))
        .map_err(|_| CommonTiffError::new("TIFF value offset does not fit this host"))?;
    require_range(bytes, offset, len, "TIFF value")?;
    Ok(bytes[offset..offset + len].to_vec())
}

fn short_values(bytes: &[u8], entry: &Entry) -> Result<Vec<u16>> {
    if entry.kind != TYPE_SHORT {
        return Err(CommonTiffError::new(format!(
            "TIFF tag {} must use SHORT, got type {}",
            entry.tag, entry.kind
        )));
    }
    let data = entry_data(bytes, entry)?;
    let (values, remainder) = data.as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(CommonTiffError::new("SHORT value has an odd byte count"));
    }
    Ok(values.iter().map(|v| u16::from_le_bytes(*v)).collect())
}

fn unsigned_values(bytes: &[u8], entry: &Entry) -> Result<Vec<u32>> {
    let data = entry_data(bytes, entry)?;
    match entry.kind {
        TYPE_SHORT => {
            let (values, remainder) = data.as_chunks::<2>();
            if !remainder.is_empty() {
                return Err(CommonTiffError::new("SHORT value has an odd byte count"));
            }
            Ok(values
                .iter()
                .map(|v| u32::from(u16::from_le_bytes(*v)))
                .collect())
        }
        TYPE_LONG => {
            let (values, remainder) = data.as_chunks::<4>();
            if !remainder.is_empty() {
                return Err(CommonTiffError::new(
                    "LONG value byte count is not divisible by four",
                ));
            }
            Ok(values.iter().map(|v| u32::from_le_bytes(*v)).collect())
        }
        _ => Err(CommonTiffError::new(format!(
            "TIFF tag {} must use SHORT or LONG, got type {}",
            entry.tag, entry.kind
        ))),
    }
}

fn scalar_u32(bytes: &[u8], entry: &Entry) -> Result<u32> {
    let values = unsigned_values(bytes, entry)?;
    if values.len() != 1 {
        return Err(CommonTiffError::new(format!(
            "TIFF tag {} must be scalar, got {} values",
            entry.tag,
            values.len()
        )));
    }
    Ok(values[0])
}

fn require_scalar(bytes: &[u8], entry: &Entry, expected: u32, name: &str) -> Result<()> {
    let got = scalar_u32(bytes, entry)?;
    if got != expected {
        return Err(CommonTiffError::new(format!(
            "{name} must be {expected}, got {got}"
        )));
    }
    Ok(())
}

fn compare_hash(label: &str, actual: &str, expected: Option<&str>) -> Result<()> {
    if let Some(expected) = expected {
        let expected = normalise_hash(expected)?;
        if actual != expected {
            return Err(CommonTiffError::new(format!(
                "{label} SHA-256 mismatch: expected {expected}, got {actual}"
            )));
        }
    }
    Ok(())
}

fn compare_provenance(provenance: &str, key: &str, expected: Option<&str>) -> Result<()> {
    if let Some(expected) = expected {
        let expected = normalise_hash(expected)?;
        let needle = format!("\"{key}\":\"{expected}\"");
        if !provenance.to_ascii_lowercase().contains(&needle) {
            return Err(CommonTiffError::new(format!(
                "embedded provenance does not bind {key} SHA-256 {expected}"
            )));
        }
    }
    Ok(())
}

fn normalise_hash(value: &str) -> Result<String> {
    let value = value.trim().to_ascii_lowercase();
    if value.len() != 64 || !value.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(CommonTiffError::new(format!(
            "invalid SHA-256 value {value:?}"
        )));
    }
    Ok(value)
}

fn checked_add(a: usize, b: usize, label: &str) -> Result<usize> {
    a.checked_add(b)
        .ok_or_else(|| CommonTiffError::new(format!("{label} overflow")))
}

fn checked_mul(a: usize, b: usize, label: &str) -> Result<usize> {
    a.checked_mul(b)
        .ok_or_else(|| CommonTiffError::new(format!("{label} overflow")))
}

fn require_range(bytes: &[u8], at: usize, len: usize, label: &str) -> Result<()> {
    let end = checked_add(at, len, label)?;
    if end > bytes.len() {
        return Err(CommonTiffError::new(format!(
            "{label} range {at}..{end} exceeds file size {}",
            bytes.len()
        )));
    }
    Ok(())
}

fn le_u16(bytes: &[u8], at: usize) -> Result<u16> {
    require_range(bytes, at, 2, "u16 read")?;
    Ok(u16::from_le_bytes([bytes[at], bytes[at + 1]]))
}

fn le_u32(bytes: &[u8], at: usize) -> Result<u32> {
    require_range(bytes, at, 4, "u32 read")?;
    Ok(u32::from_le_bytes([
        bytes[at],
        bytes[at + 1],
        bytes[at + 2],
        bytes[at + 3],
    ]))
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut hash = Sha256::new();
    hash.update(bytes);
    hex(&hash.finish())
}

fn hex(bytes: &[u8; 32]) -> String {
    let mut out = String::with_capacity(64);
    for byte in bytes {
        use std::fmt::Write as _;
        let _ = write!(out, "{byte:02x}");
    }
    out
}

struct Sha256 {
    state: [u32; 8],
    buffer: [u8; 64],
    used: usize,
    bytes: u64,
}

impl Sha256 {
    const K: [u32; 64] = [
        0x428a_2f98,
        0x7137_4491,
        0xb5c0_fbcf,
        0xe9b5_dba5,
        0x3956_c25b,
        0x59f1_11f1,
        0x923f_82a4,
        0xab1c_5ed5,
        0xd807_aa98,
        0x1283_5b01,
        0x2431_85be,
        0x550c_7dc3,
        0x72be_5d74,
        0x80de_b1fe,
        0x9bdc_06a7,
        0xc19b_f174,
        0xe49b_69c1,
        0xefbe_4786,
        0x0fc1_9dc6,
        0x240c_a1cc,
        0x2de9_2c6f,
        0x4a74_84aa,
        0x5cb0_a9dc,
        0x76f9_88da,
        0x983e_5152,
        0xa831_c66d,
        0xb003_27c8,
        0xbf59_7fc7,
        0xc6e0_0bf3,
        0xd5a7_9147,
        0x06ca_6351,
        0x1429_2967,
        0x27b7_0a85,
        0x2e1b_2138,
        0x4d2c_6dfc,
        0x5338_0d13,
        0x650a_7354,
        0x766a_0abb,
        0x81c2_c92e,
        0x9272_2c85,
        0xa2bf_e8a1,
        0xa81a_664b,
        0xc24b_8b70,
        0xc76c_51a3,
        0xd192_e819,
        0xd699_0624,
        0xf40e_3585,
        0x106a_a070,
        0x19a4_c116,
        0x1e37_6c08,
        0x2748_774c,
        0x34b0_bcb5,
        0x391c_0cb3,
        0x4ed8_aa4a,
        0x5b9c_ca4f,
        0x682e_6ff3,
        0x748f_82ee,
        0x78a5_636f,
        0x84c8_7814,
        0x8cc7_0208,
        0x90be_fffa,
        0xa450_6ceb,
        0xbef9_a3f7,
        0xc671_78f2,
    ];

    fn new() -> Self {
        Self {
            state: [
                0x6a09_e667,
                0xbb67_ae85,
                0x3c6e_f372,
                0xa54f_f53a,
                0x510e_527f,
                0x9b05_688c,
                0x1f83_d9ab,
                0x5be0_cd19,
            ],
            buffer: [0; 64],
            used: 0,
            bytes: 0,
        }
    }

    fn update(&mut self, mut input: &[u8]) {
        self.bytes = self.bytes.wrapping_add(input.len() as u64);
        if self.used > 0 {
            let take = (64 - self.used).min(input.len());
            self.buffer[self.used..self.used + take].copy_from_slice(&input[..take]);
            self.used += take;
            input = &input[take..];
            if self.used < 64 {
                return;
            }
            let block = self.buffer;
            self.compress(&block);
            self.used = 0;
        }
        let (blocks, rest) = input.as_chunks::<64>();
        for block in blocks {
            self.compress(block);
        }
        self.buffer[..rest.len()].copy_from_slice(rest);
        self.used = rest.len();
    }

    fn finish(mut self) -> [u8; 32] {
        let bits = self.bytes.wrapping_mul(8);
        self.update(&[0x80]);
        while self.used != 56 {
            self.update(&[0]);
        }
        let mut block = self.buffer;
        block[56..].copy_from_slice(&bits.to_be_bytes());
        self.compress(&block);
        let mut out = [0u8; 32];
        for (i, word) in self.state.iter().enumerate() {
            out[i * 4..i * 4 + 4].copy_from_slice(&word.to_be_bytes());
        }
        out
    }

    fn compress(&mut self, block: &[u8; 64]) {
        let mut words = [0u32; 64];
        for (i, word) in words.iter_mut().take(16).enumerate() {
            *word = u32::from_be_bytes([
                block[4 * i],
                block[4 * i + 1],
                block[4 * i + 2],
                block[4 * i + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = words[i - 15].rotate_right(7)
                ^ words[i - 15].rotate_right(18)
                ^ (words[i - 15] >> 3);
            let s1 = words[i - 2].rotate_right(17)
                ^ words[i - 2].rotate_right(19)
                ^ (words[i - 2] >> 10);
            words[i] = words[i - 16]
                .wrapping_add(s0)
                .wrapping_add(words[i - 7])
                .wrapping_add(s1);
        }
        let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = self.state;
        for (i, word) in words.iter().enumerate() {
            let upper = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choose = (e & f) ^ (!e & g);
            let t1 = h
                .wrapping_add(upper)
                .wrapping_add(choose)
                .wrapping_add(Self::K[i])
                .wrapping_add(*word);
            let lower = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let t2 = lower.wrapping_add(majority);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        for (slot, value) in self.state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *slot = slot.wrapping_add(value);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn align4(value: usize) -> usize {
        (value + 3) & !3
    }

    fn fixture(pixels: &[u16], description: &str, icc: &[u8]) -> Vec<u8> {
        let width = 3u32;
        let height = u32::try_from(pixels.len() / 9).unwrap();
        let entries = 13usize;
        let ifd_bytes = 2 + entries * 12 + 4;
        let bits_at = align4(8 + ifd_bytes);
        let sample_at = align4(bits_at + 6);
        let desc_at = align4(sample_at + 6);
        let mut desc = description.as_bytes().to_vec();
        desc.push(0);
        let icc_at = align4(desc_at + desc.len());
        let payload_at = align4(icc_at + icc.len());
        let payload: Vec<u8> = pixels.iter().flat_map(|v| v.to_le_bytes()).collect();

        let mut out = vec![0u8; payload_at + payload.len()];
        out[0..2].copy_from_slice(b"II");
        out[2..4].copy_from_slice(&42u16.to_le_bytes());
        out[4..8].copy_from_slice(&8u32.to_le_bytes());
        out[8..10].copy_from_slice(&(entries as u16).to_le_bytes());

        let mut at = 10usize;
        let mut put = |tag: u16, kind: u16, count: u32, value: u32| {
            out[at..at + 2].copy_from_slice(&tag.to_le_bytes());
            out[at + 2..at + 4].copy_from_slice(&kind.to_le_bytes());
            out[at + 4..at + 8].copy_from_slice(&count.to_le_bytes());
            out[at + 8..at + 12].copy_from_slice(&value.to_le_bytes());
            at += 12;
        };
        put(TAG_IMAGE_WIDTH, TYPE_LONG, 1, width);
        put(TAG_IMAGE_LENGTH, TYPE_LONG, 1, height);
        put(TAG_BITS_PER_SAMPLE, TYPE_SHORT, 3, bits_at as u32);
        put(TAG_COMPRESSION, TYPE_SHORT, 1, 1);
        put(TAG_PHOTOMETRIC, TYPE_SHORT, 1, 2);
        put(
            TAG_IMAGE_DESCRIPTION,
            TYPE_ASCII,
            desc.len() as u32,
            desc_at as u32,
        );
        put(TAG_STRIP_OFFSETS, TYPE_LONG, 1, payload_at as u32);
        put(TAG_SAMPLES_PER_PIXEL, TYPE_SHORT, 1, 3);
        put(TAG_ROWS_PER_STRIP, TYPE_LONG, 1, height);
        put(TAG_STRIP_BYTE_COUNTS, TYPE_LONG, 1, payload.len() as u32);
        put(TAG_PLANAR_CONFIGURATION, TYPE_SHORT, 1, 1);
        put(TAG_SAMPLE_FORMAT, TYPE_SHORT, 3, sample_at as u32);
        put(
            TAG_ICC_PROFILE,
            TYPE_UNDEFINED,
            icc.len() as u32,
            icc_at as u32,
        );
        out[at..at + 4].copy_from_slice(&0u32.to_le_bytes());
        out[bits_at..bits_at + 6].copy_from_slice(&[16, 0, 16, 0, 16, 0]);
        out[sample_at..sample_at + 6].copy_from_slice(&[1, 0, 1, 0, 1, 0]);
        out[desc_at..desc_at + desc.len()].copy_from_slice(&desc);
        out[icc_at..icc_at + icc.len()].copy_from_slice(icc);
        out[payload_at..payload_at + payload.len()].copy_from_slice(&payload);
        out
    }

    fn icc_fixture() -> Vec<u8> {
        let mut icc = vec![0u8; 128];
        icc[0..4].copy_from_slice(&128u32.to_be_bytes());
        icc[36..40].copy_from_slice(b"acsp");
        icc
    }

    #[test]
    fn sha256_matches_published_nist_vectors() {
        assert_eq!(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn payload_internal_and_merge_boundary_hashes_are_identical() {
        let source = sha256_hex(b"fixture source");
        let description = format!("{{\"source_sha256\":\"{source}\"}}");
        let pixels: Vec<u16> = (0..18).map(|v| 1000 + v).collect();
        let bytes = fixture(&pixels, &description, &icc_fixture());
        let frame = CommonTiffFrame::parse(&bytes).unwrap();
        assert_eq!(frame.pixels, pixels);
        assert_eq!(frame.pixel_payload_sha256, frame.internal_pixel_sha256);
        assert_eq!(
            frame.pixel_payload_sha256,
            frame.merge_sample_sha256().unwrap()
        );
    }

    #[test]
    fn one_lsb_change_fails_against_the_frozen_identity() {
        let source = sha256_hex(b"fixture source");
        let description = format!("{{\"source_sha256\":\"{source}\"}}");
        let pixels: Vec<u16> = (0..18).map(|v| 1000 + v).collect();
        let baseline = fixture(&pixels, &description, &icc_fixture());
        let parsed = CommonTiffFrame::parse(&baseline).unwrap();
        let expected = ExpectedIdentity {
            file_sha256: Some(parsed.file_sha256.clone()),
            pixel_payload_sha256: Some(parsed.pixel_payload_sha256.clone()),
            icc_sha256: Some(parsed.icc_sha256.clone()),
            source_sha256: Some(source),
            ..ExpectedIdentity::default()
        };
        let mut changed = baseline;
        let payload_at = parsed.strips[0].offset as usize;
        let sample = u16::from_le_bytes([changed[payload_at], changed[payload_at + 1]]) + 1;
        changed[payload_at..payload_at + 2].copy_from_slice(&sample.to_le_bytes());
        let changed = CommonTiffFrame::parse(&changed).unwrap();
        let err = changed.verify(&expected).unwrap_err().to_string();
        assert!(err.contains("pixel payload SHA-256 mismatch"));
        assert_ne!(
            changed.pixel_payload_sha256,
            expected.pixel_payload_sha256.unwrap()
        );
    }

    #[test]
    fn an_unlisted_development_tag_is_refused() {
        let source = sha256_hex(b"fixture source");
        let description = format!("{{\"source_sha256\":\"{source}\"}}");
        let pixels: Vec<u16> = (0..18).map(|v| 1000 + v).collect();
        let mut bytes = fixture(&pixels, &description, &icc_fixture());
        // Rewrite ImageDescription's tag id as Software (305), preserving the
        // rest of the valid TIFF. The failure must be the allowlist, not parse.
        let description_entry = 10 + 5 * 12;
        bytes[description_entry..description_entry + 2].copy_from_slice(&305u16.to_le_bytes());
        let err = CommonTiffFrame::parse(&bytes).unwrap_err().to_string();
        assert!(err.contains("development tags are forbidden"));
    }
}
