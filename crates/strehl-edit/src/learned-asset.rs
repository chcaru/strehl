//! Strehl's own frozen-treatment container, independent of any model layout.
//! The versioned envelope contains a canonical JSON descriptor, little-endian
//! FP32 blocks and SHA-256 of the preceding bytes. The digest detects corruption;
//! it is not a publisher signature or proof of identity metadata's provenance.
//!
//! No file I/O occurs here. A caller atomically publishes encoded bytes, keys a
//! prepared-object cache by content digest, and verifies source/input identities.
//! A region origin records provenance; application opacity remains caller-owned.
use crate::learned_profile::{
    ColorEncoding, ColorLut, GainMap, GainMapParameters, Matrix3, PreparedLearnedProfile,
    ProfileParameters, ProfileToneCurve,
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::sync::Arc;

const MAGIC: &[u8; 8] = b"STRHLPF\0";
const VERSION: u16 = 1;
const PREFIX_BYTES: usize = 20;
const DIGEST_BYTES: usize = 32;
pub const MAX_ASSET_BYTES: usize = 32 * 1024 * 1024;
pub const MAX_HEADER_BYTES: usize = 256 * 1024;
pub const MAX_MASK_SAMPLES: usize = 1_048_576;

pub type AssetDigest = [u8; 32];

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AssetIdentities {
    /// Identifies the preprocessing/render contract, independently of model weights.
    pub contract_id: String,
    pub contract_sha256: AssetDigest,
    pub model_sha256: AssetDigest,
    pub input_sha256: AssetDigest,
    pub source_sha256: AssetDigest,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProfileOrigin {
    pub full_size: [u32; 2],
    /// None means analysis of the complete photograph. This does not rescale
    /// gain/mask coordinates or imply an application-selection mask.
    pub region: Option<RegionOrigin>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RegionOrigin {
    pub id: String,
    /// Integer source bounds [min_x,min_y,max_x,max_y], maximum excluded.
    pub bounds: [u32; 4],
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GainDescriptor {
    pub dimensions: [u32; 3],
    pub origin_yx: [f32; 2],
    pub spacing_yx: [f32; 2],
    pub input_weights: [f32; 5],
    pub gamma: f32,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum TableEncoding {
    Linear,
    Srgb,
    Power { gamma: f32 },
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TableDescriptor {
    pub size: u32,
    /// Maps the declared post-tone RIMM domain to the table's linear primaries.
    pub source_to_table: Matrix3,
    pub encoding: TableEncoding,
    pub gamut_extension: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ToneDescriptor {
    Identity,
    /// Monotone knots [input,output]; unit-slope tails preserve offsets outside
    /// the domain. This explicit policy is part of container version 1.
    PiecewiseLinear {
        knots: Vec<[f32; 2]>,
    },
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MaskDescriptor {
    pub size: [u32; 2],
    /// Normalized full-photograph bounds, not coordinates rebased to an ROI.
    pub origin_xy: [f32; 2],
    pub extent_xy: [f32; 2],
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FrozenProfileDescriptor {
    pub identities: AssetIdentities,
    pub origin: ProfileOrigin,
    pub gain: GainDescriptor,
    /// Background, subject, sky, in that order. Missing semantic slots consume
    /// no mask weight in the compositor; missing background is identity.
    pub tables: [Option<TableDescriptor>; 3],
    pub linear_709_to_rimm: Matrix3,
    pub pre_gain_scale: f32,
    pub tone_curve: ToneDescriptor,
    /// Subject and sky planes, in that order. Missing masks mean zero weight.
    pub masks: [Option<MaskDescriptor>; 2],
}

/// Caller-supplied FP32 data. Gain layout is [brightness,y,x]; table layout is
/// [channel,R,G,B]; masks are [y,x]. Every float's bit pattern survives encoding.
pub struct FrozenProfileData {
    pub gain: Vec<f32>,
    pub tables: [Option<Vec<f32>>; 3],
    pub masks: [Option<Vec<f32>>; 2],
}

#[derive(Clone)]
struct StoredData {
    gain: Arc<[f32]>,
    tables: [Option<Arc<[f32]>>; 3],
    masks: [Option<Arc<[f32]>>; 2],
}

/// Clone shares fields and the prepared compositor; it does not clone image data.
#[derive(Clone)]
pub struct FrozenLearnedAsset {
    descriptor: Arc<FrozenProfileDescriptor>,
    data: StoredData,
    prepared: Arc<PreparedLearnedProfile>,
    digest: AssetDigest,
    encoded_bytes: usize,
}

struct Layout {
    gain: usize,
    tables: [Option<usize>; 3],
    masks: [Option<usize>; 2],
    floats: usize,
}

fn product(values: &[u32], maximum: usize) -> Result<usize> {
    let size = values.iter().try_fold(1usize, |a, &b| {
        ensure!(b > 0, "Empty frozen-field dimension");
        a.checked_mul(b as usize)
            .context("Frozen-field extent overflow")
    })?;
    ensure!(size <= maximum, "Frozen field exceeds sample bound");
    Ok(size)
}

fn layout(descriptor: &FrozenProfileDescriptor) -> Result<Layout> {
    let identities = &descriptor.identities;
    ensure!(
        !identities.contract_id.is_empty()
            && identities.contract_id.len() <= 128
            && identities
                .contract_id
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"._-/:".contains(&c)),
        "Invalid frozen-profile contract identifier"
    );
    ensure!(
        descriptor
            .origin
            .full_size
            .iter()
            .all(|v| (1..=(1 << 20)).contains(v)),
        "Invalid original photograph extent"
    );
    if let Some(region) = &descriptor.origin.region {
        let [x0, y0, x1, y1] = region.bounds;
        ensure!(
            !region.id.is_empty()
                && region.id.len() <= 256
                && x0 < x1
                && y0 < y1
                && x1 <= descriptor.origin.full_size[0]
                && y1 <= descriptor.origin.full_size[1],
            "Invalid profile origin region"
        );
    }
    let [n, h, w] = descriptor.gain.dimensions;
    ensure!(
        (1..=64).contains(&n) && (1..=512).contains(&h) && (1..=512).contains(&w),
        "Invalid frozen gain dimensions"
    );
    let gain = product(
        &descriptor.gain.dimensions,
        crate::learned_profile::MAX_GAIN_SAMPLES,
    )?;
    ensure!(
        descriptor
            .gain
            .origin_yx
            .iter()
            .chain(&descriptor.gain.input_weights)
            .all(|v| v.is_finite()),
        "Nonfinite frozen gain parameters"
    );
    ensure!(
        descriptor
            .gain
            .spacing_yx
            .iter()
            .all(|v| v.is_finite() && *v > 0.)
            && descriptor.gain.gamma.is_finite()
            && descriptor.gain.gamma > 0.,
        "Invalid frozen gain spacing or gamma"
    );
    ensure!(
        descriptor
            .linear_709_to_rimm
            .iter()
            .flatten()
            .all(|v| v.is_finite()),
        "Nonfinite frozen color matrix"
    );
    crate::learned_profile::validate_matrix(descriptor.linear_709_to_rimm)?;
    ensure!(
        descriptor.pre_gain_scale.is_finite() && descriptor.pre_gain_scale > 0.,
        "Invalid frozen pre-gain scale"
    );
    let mut tables = [None; 3];
    for (i, table) in descriptor.tables.iter().enumerate() {
        if let Some(table) = table {
            ensure!((2..=32).contains(&table.size), "Invalid frozen table edge");
            ensure!(
                table
                    .source_to_table
                    .iter()
                    .flatten()
                    .all(|v| v.is_finite()),
                "Nonfinite frozen table matrix"
            );
            crate::learned_profile::validate_matrix(table.source_to_table)?;
            if let TableEncoding::Power { gamma } = table.encoding {
                ensure!(
                    gamma.is_finite() && (0.01..=16.).contains(&gamma),
                    "Unsupported frozen table gamma"
                );
            }
            tables[i] = Some(product(
                &[3, table.size, table.size, table.size],
                3 * 32usize.pow(3),
            )?);
        }
    }
    if let ToneDescriptor::PiecewiseLinear { knots } = &descriptor.tone_curve {
        ensure!(
            (2..=crate::learned_profile::MAX_TONE_KNOTS).contains(&knots.len()),
            "Invalid frozen tone knot count"
        );
        ensure!(
            knots.iter().flatten().all(|v| v.is_finite()),
            "Nonfinite frozen tone knot"
        );
        for pair in knots.windows(2) {
            ensure!(
                pair[1][0] > pair[0][0] && pair[1][1] >= pair[0][1],
                "Invalid frozen tone ordering"
            );
            let slope = ((f64::from(pair[1][1]) - f64::from(pair[0][1]))
                / (f64::from(pair[1][0]) - f64::from(pair[0][0]))) as f32;
            ensure!(slope.is_finite(), "Unrepresentable frozen tone slope");
        }
    }
    let mut masks = [None; 2];
    for (i, mask) in descriptor.masks.iter().enumerate() {
        if let Some(mask) = mask {
            ensure!(
                mask.size.iter().all(|v| (1..=2048).contains(v)),
                "Invalid semantic mask dimensions"
            );
            for axis in 0..2 {
                let origin = mask.origin_xy[axis];
                let extent = mask.extent_xy[axis];
                ensure!(
                    origin.is_finite()
                        && extent.is_finite()
                        && origin >= 0.
                        && extent > 0.
                        && origin + extent <= 1.,
                    "Semantic mask bounds must lie in full-image 0..1 coordinates"
                );
            }
            masks[i] = Some(product(&mask.size, MAX_MASK_SAMPLES)?);
        }
    }
    let floats =
        gain + tables.iter().flatten().sum::<usize>() + masks.iter().flatten().sum::<usize>();
    ensure!(
        floats <= (MAX_ASSET_BYTES - PREFIX_BYTES - DIGEST_BYTES) / 4,
        "Frozen payload exceeds byte budget"
    );
    Ok(Layout {
        gain,
        tables,
        masks,
        floats,
    })
}

fn canonical_header(descriptor: &FrozenProfileDescriptor) -> Result<Vec<u8>> {
    let bytes = serde_json::to_vec(descriptor)?;
    ensure!(
        bytes.len() <= MAX_HEADER_BYTES,
        "Frozen header exceeds byte budget"
    );
    Ok(bytes)
}

fn envelope_prefix(header_bytes: usize, floats: usize) -> Result<[u8; PREFIX_BYTES]> {
    ensure!(
        header_bytes <= MAX_HEADER_BYTES
            && PREFIX_BYTES + header_bytes + floats * 4 + DIGEST_BYTES <= MAX_ASSET_BYTES,
        "Frozen asset exceeds byte budget"
    );
    let mut prefix = [0u8; PREFIX_BYTES];
    prefix[..8].copy_from_slice(MAGIC);
    prefix[8..10].copy_from_slice(&VERSION.to_le_bytes());
    // Bytes 10..12 are reserved, and must be zero for v1.
    prefix[12..16].copy_from_slice(&(header_bytes as u32).to_le_bytes());
    prefix[16..20].copy_from_slice(&(floats as u32).to_le_bytes());
    Ok(prefix)
}

fn hash_blocks(prefix: &[u8], header: &[u8], data: &StoredData) -> AssetDigest {
    let mut hash = Sha256::new();
    hash.update(prefix);
    hash.update(header);
    for block in std::iter::once(data.gain.as_ref())
        .chain(data.tables.iter().flatten().map(|v| v.as_ref()))
        .chain(data.masks.iter().flatten().map(|v| v.as_ref()))
    {
        for value in block {
            hash.update(value.to_le_bytes());
        }
    }
    hash.finalize().into()
}

fn prepare(
    descriptor: &FrozenProfileDescriptor,
    data: &StoredData,
) -> Result<PreparedLearnedProfile> {
    let gain = GainMap::new(
        data.gain.clone(),
        GainMapParameters {
            dimensions: descriptor.gain.dimensions,
            origin_yx: descriptor.gain.origin_yx,
            spacing_yx: descriptor.gain.spacing_yx,
            input_weights: descriptor.gain.input_weights,
            gamma: descriptor.gain.gamma,
        },
    )?;
    let mut tables: [Option<ColorLut>; 3] = [None, None, None];
    for (i, spec) in descriptor.tables.iter().enumerate() {
        if let Some(spec) = spec {
            let encoding = match spec.encoding {
                TableEncoding::Linear => ColorEncoding::Linear,
                TableEncoding::Srgb => ColorEncoding::Srgb,
                TableEncoding::Power { gamma } => ColorEncoding::Power { gamma },
            };
            tables[i] = Some(ColorLut::new(
                spec.size,
                data.tables[i]
                    .as_ref()
                    .context("Missing frozen table")?
                    .clone(),
                spec.source_to_table,
                encoding,
                spec.gamut_extension,
            )?);
        }
    }
    let tone_curve = match &descriptor.tone_curve {
        ToneDescriptor::Identity => ProfileToneCurve::identity(),
        ToneDescriptor::PiecewiseLinear { knots } => {
            ProfileToneCurve::piecewise_linear(knots.clone().into())?
        }
    };
    let [background, subject, sky] = tables;
    PreparedLearnedProfile::new(
        gain,
        background,
        subject,
        sky,
        ProfileParameters {
            linear_709_to_rimm: descriptor.linear_709_to_rimm,
            pre_gain_scale: descriptor.pre_gain_scale,
            tone_curve,
        },
    )
}

impl FrozenLearnedAsset {
    /// Validate and prepare once. No model inference or source-file access occurs.
    pub fn freeze(descriptor: FrozenProfileDescriptor, data: FrozenProfileData) -> Result<Self> {
        let layout = layout(&descriptor)?;
        let header = canonical_header(&descriptor)?;
        let prefix = envelope_prefix(header.len(), layout.floats)?;
        ensure!(
            data.gain.len() == layout.gain,
            "Incorrect frozen gain sample count"
        );
        ensure!(
            data.gain.iter().all(|v| v.is_finite() && *v >= 0.),
            "Frozen gains must be finite and nonnegative"
        );
        for i in 0..3 {
            ensure!(
                data.tables[i].as_ref().map(Vec::len) == layout.tables[i],
                "Incorrect frozen table presence or sample count"
            );
            if let Some(table) = &data.tables[i] {
                ensure!(
                    table
                        .iter()
                        .all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
                    "Frozen SDR table values must lie in 0..1"
                );
            }
        }
        for i in 0..2 {
            ensure!(
                data.masks[i].as_ref().map(Vec::len) == layout.masks[i],
                "Incorrect frozen mask presence or sample count"
            );
            if let Some(mask) = &data.masks[i] {
                ensure!(
                    mask.iter()
                        .all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
                    "Frozen semantic mask values must lie in 0..1"
                );
            }
        }
        let data = StoredData {
            gain: data.gain.into(),
            tables: data.tables.map(|v| v.map(Arc::from)),
            masks: data.masks.map(|v| v.map(Arc::from)),
        };
        let prepared = Arc::new(prepare(&descriptor, &data)?);
        let digest = hash_blocks(&prefix, &header, &data);
        let encoded_bytes = PREFIX_BYTES + header.len() + layout.floats * 4 + DIGEST_BYTES;
        Ok(Self {
            descriptor: Arc::new(descriptor),
            data,
            prepared,
            digest,
            encoded_bytes,
        })
    }

    pub fn descriptor(&self) -> &FrozenProfileDescriptor {
        &self.descriptor
    }
    pub fn prepared(&self) -> Arc<PreparedLearnedProfile> {
        self.prepared.clone()
    }
    pub fn digest(&self) -> AssetDigest {
        self.digest
    }
    pub fn content_id(&self) -> String {
        self.digest.iter().map(|b| format!("{b:02x}")).collect()
    }
    pub fn encoded_len(&self) -> usize {
        self.encoded_bytes
    }

    /// Additional input/model/contract checks remain the cache caller's duty.
    pub fn matches_source(&self, sha256: AssetDigest, size: [u32; 2]) -> bool {
        self.descriptor.identities.source_sha256 == sha256
            && self.descriptor.origin.full_size == size
    }

    pub fn encode(&self) -> Result<Vec<u8>> {
        let layout = layout(&self.descriptor)?;
        let header = canonical_header(&self.descriptor)?;
        let prefix = envelope_prefix(header.len(), layout.floats)?;
        let mut encoded = Vec::with_capacity(self.encoded_bytes);
        encoded.extend_from_slice(&prefix);
        encoded.extend_from_slice(&header);
        for block in std::iter::once(self.data.gain.as_ref())
            .chain(self.data.tables.iter().flatten().map(|v| v.as_ref()))
            .chain(self.data.masks.iter().flatten().map(|v| v.as_ref()))
        {
            for value in block {
                encoded.extend_from_slice(&value.to_le_bytes());
            }
        }
        encoded.extend_from_slice(&self.digest);
        Ok(encoded)
    }

    /// Checks envelope bounds/digest/canonical header and every declared extent
    /// before allocating decoded FP32 blocks. Trailing bytes are not accepted.
    pub fn decode(encoded: &[u8]) -> Result<Self> {
        ensure!(
            (PREFIX_BYTES + DIGEST_BYTES..=MAX_ASSET_BYTES).contains(&encoded.len()),
            "Invalid frozen asset byte length"
        );
        ensure!(&encoded[..8] == MAGIC, "Invalid frozen asset magic");
        ensure!(
            u16::from_le_bytes(encoded[8..10].try_into().unwrap()) == VERSION,
            "Unsupported frozen asset version"
        );
        ensure!(encoded[10..12] == [0, 0], "Unsupported frozen asset flags");
        let header_bytes = u32::from_le_bytes(encoded[12..16].try_into().unwrap()) as usize;
        let floats = u32::from_le_bytes(encoded[16..20].try_into().unwrap()) as usize;
        ensure!(
            header_bytes <= MAX_HEADER_BYTES && floats <= MAX_ASSET_BYTES / 4,
            "Frozen header or payload exceeds bounds"
        );
        let expected = PREFIX_BYTES + header_bytes + floats * 4 + DIGEST_BYTES;
        ensure!(
            expected == encoded.len(),
            "Frozen asset length mismatch or trailing bytes"
        );
        let digest_at = encoded.len() - DIGEST_BYTES;
        let recorded: AssetDigest = encoded[digest_at..].try_into().unwrap();
        let calculated: AssetDigest = Sha256::digest(&encoded[..digest_at]).into();
        ensure!(recorded == calculated, "Frozen asset digest mismatch");
        let header = &encoded[PREFIX_BYTES..PREFIX_BYTES + header_bytes];
        let descriptor: FrozenProfileDescriptor = serde_json::from_slice(header)?;
        let layout = layout(&descriptor)?;
        ensure!(
            layout.floats == floats,
            "Frozen descriptor does not match payload size"
        );
        ensure!(
            canonical_header(&descriptor)? == header,
            "Noncanonical frozen header"
        );
        let mut cursor = PREFIX_BYTES + header_bytes;
        // Validate the entire payload before allocating any FP32 field. Every
        // block after gain is either an SDR table or a semantic weight plane.
        for (index, bytes) in encoded[cursor..digest_at]
            .as_chunks::<4>()
            .0
            .iter()
            .enumerate()
        {
            let value = f32::from_le_bytes(*bytes);
            ensure!(
                value.is_finite() && value >= 0. && (index < layout.gain || value <= 1.),
                "Invalid frozen field value"
            );
        }
        let mut block = |count: usize| -> Result<Vec<f32>> {
            let bytes = &encoded[cursor..cursor + count * 4];
            let data = bytes
                .as_chunks::<4>()
                .0
                .iter()
                .map(|b| f32::from_le_bytes(*b))
                .collect();
            cursor += count * 4;
            Ok(data)
        };
        let gain = block(layout.gain)?;
        let mut tables: [Option<Vec<f32>>; 3] = [None, None, None];
        for (i, n) in layout.tables.into_iter().enumerate() {
            if let Some(n) = n {
                tables[i] = Some(block(n)?);
            }
        }
        let mut masks: [Option<Vec<f32>>; 2] = [None, None];
        for (i, n) in layout.masks.into_iter().enumerate() {
            if let Some(n) = n {
                masks[i] = Some(block(n)?);
            }
        }
        let result = Self::freeze(
            descriptor,
            FrozenProfileData {
                gain,
                tables,
                masks,
            },
        )?;
        ensure!(
            result.digest == recorded,
            "Frozen roundtrip identity mismatch"
        );
        Ok(result)
    }

    /// Bilinear pixel-center sampling of frozen semantic planes. No file access,
    /// allocation, or implicit rescaling to a selected region occurs here.
    pub fn semantic_weights(&self, uv: [f32; 2]) -> Result<[f32; 2]> {
        ensure!(
            uv.iter().all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
            "Invalid full-image mask coordinates"
        );
        let mut weights = [0.; 2];
        for (i, result) in weights.iter_mut().enumerate() {
            let (Some(spec), Some(values)) = (&self.descriptor.masks[i], &self.data.masks[i])
            else {
                continue;
            };
            if (0..2).any(|axis| {
                uv[axis] < spec.origin_xy[axis]
                    || uv[axis] > spec.origin_xy[axis] + spec.extent_xy[axis]
            }) {
                continue;
            }
            let w = spec.size[0] as usize;
            let h = spec.size[1] as usize;
            let x = ((uv[0] - spec.origin_xy[0]) / spec.extent_xy[0] * w as f32 - 0.5)
                .clamp(0., (w - 1) as f32);
            let y = ((uv[1] - spec.origin_xy[1]) / spec.extent_xy[1] * h as f32 - 0.5)
                .clamp(0., (h - 1) as f32);
            let x0 = x as usize;
            let y0 = y as usize;
            let x1 = (x0 + 1).min(w - 1);
            let y1 = (y0 + 1).min(h - 1);
            let fx = x - x0 as f32;
            let fy = y - y0 as f32;
            let top = values[y0 * w + x0] * (1. - fx) + values[y0 * w + x1] * fx;
            let bottom = values[y1 * w + x0] * (1. - fx) + values[y1 * w + x1] * fx;
            *result = (top * (1. - fy) + bottom * fy).clamp(0., 1.);
        }
        Ok(weights)
    }
}

#[cfg(test)]
#[path = "learned-asset-tests.rs"]
mod tests;
