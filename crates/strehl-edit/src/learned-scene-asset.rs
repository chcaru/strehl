//! Version 1 immutable SDR scene treatment. This distinct magic/schema never
//! reinterprets a legacy learned-profile asset. Numeric payloads are little-endian
//! FP32, preceded by canonical JSON and followed by SHA-256 of all preceding
//! bytes. The digest is corruption detection, not authentication or provenance.
//! No source access, model inference, UI state, or file I/O occurs here.
use crate::{
    learned_asset::{
        AssetDigest, AssetIdentities, GainDescriptor, MAX_ASSET_BYTES, MAX_HEADER_BYTES,
        ProfileOrigin, TableDescriptor, TableEncoding,
    },
    learned_profile::{
        ColorEncoding, ColorLut, GainMap, GainMapParameters, MAX_GAIN_SAMPLES, Matrix3,
        validate_matrix,
    },
    learned_scene::{
        PreparedSceneSdrProfile, SCENE_SDR_LINEAR_V1, SceneSdrParameters, validate_scene_parameters,
    },
};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::sync::Arc;

const MAGIC: &[u8; 8] = b"STRHLSC\0";
const VERSION: u16 = 1;
const PREFIX_BYTES: usize = 20;
const DIGEST_BYTES: usize = 32;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FrozenSceneDescriptor {
    pub identities: AssetIdentities,
    /// Version 1 accepts whole-photograph analysis only (`region: None`).
    pub origin: ProfileOrigin,
    pub gain: GainDescriptor,
    /// Single color table; this version has no semantic-mask fields or blend.
    pub table: TableDescriptor,
    pub linear_709_to_working: Matrix3,
    pub working_to_linear_709: Matrix3,
    pub gain_query_scale: f32,
    pub exposure_scale: f32,
}

impl FrozenSceneDescriptor {
    pub fn parameters(&self) -> SceneSdrParameters {
        SceneSdrParameters {
            linear_709_to_working: self.linear_709_to_working,
            working_to_linear_709: self.working_to_linear_709,
            gain_query_scale: self.gain_query_scale,
            exposure_scale: self.exposure_scale,
        }
    }
}

/// Gain layout [brightness,y,x], table layout [channel,R,G,B]. Encoding retains
/// each accepted FP32 bit pattern, including signed zero and subnormals.
pub struct FrozenSceneData {
    pub gain: Vec<f32>,
    pub table: Vec<f32>,
}

#[derive(Clone)]
pub struct FrozenSceneAsset {
    descriptor: Arc<FrozenSceneDescriptor>,
    gain: Arc<[f32]>,
    table: Arc<[f32]>,
    prepared: Arc<PreparedSceneSdrProfile>,
    digest: AssetDigest,
    encoded_bytes: usize,
}

struct Layout {
    gain: usize,
    table: usize,
}
impl Layout {
    fn floats(&self) -> usize {
        self.gain + self.table
    }
}

fn layout(d: &FrozenSceneDescriptor) -> Result<Layout> {
    ensure!(
        d.identities.contract_id == SCENE_SDR_LINEAR_V1,
        "Unsupported frozen scene contract"
    );
    ensure!(
        d.origin.region.is_none(),
        "Regional scene analysis is unsupported"
    );
    ensure!(
        d.origin
            .full_size
            .iter()
            .all(|v| (1..=(1 << 20)).contains(v)),
        "Invalid original photograph extent"
    );
    validate_scene_parameters(d.parameters())?;
    let [n, h, w] = d.gain.dimensions;
    ensure!(
        (1..=64).contains(&n) && (1..=512).contains(&h) && (1..=512).contains(&w),
        "Invalid frozen scene gain dimensions"
    );
    // The per-axis bounds above make these products safe on 32-bit platforms.
    let gain = n as usize * h as usize * w as usize;
    ensure!(
        gain <= MAX_GAIN_SAMPLES,
        "Frozen scene gain exceeds sample bound"
    );
    ensure!(
        d.gain
            .origin_yx
            .iter()
            .chain(&d.gain.input_weights)
            .all(|v| v.is_finite()),
        "Nonfinite frozen scene gain parameters"
    );
    ensure!(
        d.gain.spacing_yx.iter().all(|v| v.is_finite() && *v > 0.)
            && d.gain.gamma.is_finite()
            && d.gain.gamma > 0.,
        "Invalid frozen scene gain spacing or gamma"
    );
    ensure!(
        (2..=32).contains(&d.table.size),
        "Invalid frozen scene table edge"
    );
    validate_matrix(d.table.source_to_table)?;
    if let TableEncoding::Power { gamma } = d.table.encoding {
        ensure!(
            gamma.is_finite() && (0.01..=16.).contains(&gamma),
            "Unsupported frozen scene table gamma"
        );
    }
    let table = 3 * (d.table.size as usize).pow(3);
    Ok(Layout { gain, table })
}

fn canonical_header(d: &FrozenSceneDescriptor) -> Result<Vec<u8>> {
    let bytes = serde_json::to_vec(d)?;
    ensure!(
        bytes.len() <= MAX_HEADER_BYTES,
        "Frozen scene header exceeds byte budget"
    );
    Ok(bytes)
}

fn prefix(header_bytes: usize, floats: usize) -> Result<[u8; PREFIX_BYTES]> {
    ensure!(
        header_bytes <= MAX_HEADER_BYTES
            && floats <= MAX_ASSET_BYTES / 4
            && PREFIX_BYTES + header_bytes + floats * 4 + DIGEST_BYTES <= MAX_ASSET_BYTES,
        "Frozen scene asset exceeds byte budget"
    );
    let mut result = [0; PREFIX_BYTES];
    result[..8].copy_from_slice(MAGIC);
    result[8..10].copy_from_slice(&VERSION.to_le_bytes());
    // Reserved bytes 10..12 remain zero.
    result[12..16].copy_from_slice(&(header_bytes as u32).to_le_bytes());
    result[16..20].copy_from_slice(&(floats as u32).to_le_bytes());
    Ok(result)
}

fn prepare(
    d: &FrozenSceneDescriptor,
    gain: Arc<[f32]>,
    table: Arc<[f32]>,
) -> Result<PreparedSceneSdrProfile> {
    let map = GainMap::new(
        gain,
        GainMapParameters {
            dimensions: d.gain.dimensions,
            origin_yx: d.gain.origin_yx,
            spacing_yx: d.gain.spacing_yx,
            input_weights: d.gain.input_weights,
            gamma: d.gain.gamma,
        },
    )?;
    let encoding = match d.table.encoding {
        TableEncoding::Linear => ColorEncoding::Linear,
        TableEncoding::Srgb => ColorEncoding::Srgb,
        TableEncoding::Power { gamma } => ColorEncoding::Power { gamma },
    };
    let table = ColorLut::new(
        d.table.size,
        table,
        d.table.source_to_table,
        encoding,
        d.table.gamut_extension,
    )?;
    PreparedSceneSdrProfile::new(map, table, d.parameters())
}

impl FrozenSceneAsset {
    pub fn freeze(descriptor: FrozenSceneDescriptor, data: FrozenSceneData) -> Result<Self> {
        let layout = layout(&descriptor)?;
        let header = canonical_header(&descriptor)?;
        let prefix = prefix(header.len(), layout.floats())?;
        ensure!(
            data.gain.len() == layout.gain && data.table.len() == layout.table,
            "Incorrect frozen scene field length"
        );
        ensure!(
            data.gain.iter().all(|v| v.is_finite() && *v >= 0.),
            "Frozen scene gains must be finite and nonnegative"
        );
        ensure!(
            data.table
                .iter()
                .all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
            "Frozen scene SDR table values must lie in 0..1"
        );
        let gain: Arc<[f32]> = data.gain.into();
        let table: Arc<[f32]> = data.table.into();
        let prepared = Arc::new(prepare(&descriptor, gain.clone(), table.clone())?);
        let mut hash = Sha256::new();
        hash.update(prefix);
        hash.update(&header);
        for value in gain.iter().chain(table.iter()) {
            hash.update(value.to_le_bytes());
        }
        Ok(Self {
            descriptor: Arc::new(descriptor),
            gain,
            table,
            prepared,
            digest: hash.finalize().into(),
            encoded_bytes: PREFIX_BYTES + header.len() + layout.floats() * 4 + DIGEST_BYTES,
        })
    }

    pub fn descriptor(&self) -> &FrozenSceneDescriptor {
        &self.descriptor
    }
    pub fn prepared(&self) -> Arc<PreparedSceneSdrProfile> {
        self.prepared.clone()
    }
    pub fn digest(&self) -> AssetDigest {
        self.digest
    }
    pub fn content_id(&self) -> String {
        self.digest.iter().map(|v| format!("{v:02x}")).collect()
    }
    pub fn encoded_len(&self) -> usize {
        self.encoded_bytes
    }

    pub fn encode(&self) -> Result<Vec<u8>> {
        let layout = layout(&self.descriptor)?;
        let header = canonical_header(&self.descriptor)?;
        let mut bytes = Vec::with_capacity(self.encoded_bytes);
        bytes.extend_from_slice(&prefix(header.len(), layout.floats())?);
        bytes.extend_from_slice(&header);
        for value in self.gain.iter().chain(self.table.iter()) {
            bytes.extend_from_slice(&value.to_le_bytes());
        }
        bytes.extend_from_slice(&self.digest);
        Ok(bytes)
    }

    /// Validate envelope, digest, canonical metadata, dimensions, transform pair
    /// and all numeric samples before allocating decoded FP32 field buffers.
    /// Unknown/duplicate header fields and trailing bytes are errors.
    pub fn decode(bytes: &[u8]) -> Result<Self> {
        ensure!(
            (PREFIX_BYTES + DIGEST_BYTES..=MAX_ASSET_BYTES).contains(&bytes.len()),
            "Invalid frozen scene byte length"
        );
        ensure!(&bytes[..8] == MAGIC, "Invalid frozen scene magic");
        ensure!(
            u16::from_le_bytes(bytes[8..10].try_into().unwrap()) == VERSION,
            "Unsupported frozen scene version"
        );
        ensure!(bytes[10..12] == [0, 0], "Unsupported frozen scene flags");
        let header_len = u32::from_le_bytes(bytes[12..16].try_into().unwrap()) as usize;
        let floats = u32::from_le_bytes(bytes[16..20].try_into().unwrap()) as usize;
        prefix(header_len, floats)?;
        ensure!(
            PREFIX_BYTES + header_len + floats * 4 + DIGEST_BYTES == bytes.len(),
            "Frozen scene length mismatch or trailing bytes"
        );
        let digest_at = bytes.len() - DIGEST_BYTES;
        let recorded: AssetDigest = bytes[digest_at..].try_into().unwrap();
        let calculated: AssetDigest = Sha256::digest(&bytes[..digest_at]).into();
        ensure!(recorded == calculated, "Frozen scene digest mismatch");
        let header = &bytes[PREFIX_BYTES..PREFIX_BYTES + header_len];
        let descriptor: FrozenSceneDescriptor = serde_json::from_slice(header)?;
        let layout = layout(&descriptor)?;
        ensure!(
            layout.floats() == floats,
            "Frozen scene descriptor does not match payload size"
        );
        ensure!(
            canonical_header(&descriptor)? == header,
            "Noncanonical frozen scene header"
        );
        let body = &bytes[PREFIX_BYTES + header_len..digest_at];
        for (i, chunk) in body.as_chunks::<4>().0.iter().enumerate() {
            let value = f32::from_le_bytes(*chunk);
            ensure!(
                value.is_finite() && value >= 0. && (i < layout.gain || value <= 1.),
                "Invalid frozen scene field value"
            );
        }
        let read = |data: &[u8]| {
            data.as_chunks::<4>()
                .0
                .iter()
                .map(|v| f32::from_le_bytes(*v))
                .collect()
        };
        let result = Self::freeze(
            descriptor,
            FrozenSceneData {
                gain: read(&body[..layout.gain * 4]),
                table: read(&body[layout.gain * 4..]),
            },
        )?;
        ensure!(
            result.digest == recorded,
            "Frozen scene roundtrip identity mismatch"
        );
        Ok(result)
    }
}

#[cfg(test)]
#[path = "learned-scene-asset-tests.rs"]
pub(crate) mod tests;
