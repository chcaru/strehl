use crate::package::{Digest, sha256};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};
use std::sync::Arc;

pub const INPUT_SHAPE: [usize; 4] = [1, 5, 384, 512];
pub const INPUT_VALUES: usize = 5 * 384 * 512;
pub const HEADS: [(&str, &[usize]); 10] = [
    ("pgtm", &[1, 16, 96, 128]),
    ("rgbt_0", &[1, 3, 32, 32, 32]),
    ("rgbt_1", &[1, 3, 32, 32, 32]),
    ("rgbt_2", &[1, 3, 32, 32, 32]),
    ("exposure", &[1, 1]),
    ("pgtm_hdr", &[1, 16, 96, 128]),
    ("rgbt_0_hdr", &[1, 3, 32, 32, 32]),
    ("rgbt_1_hdr", &[1, 3, 32, 32, 32]),
    ("rgbt_2_hdr", &[1, 3, 32, 32, 32]),
    ("exposure_hdr", &[1, 1]),
];

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TensorSpec {
    pub name: String,
    pub dtype: String,
    pub shape: Vec<usize>,
}
impl TensorSpec {
    pub fn new(name: &str, shape: &[usize]) -> Self {
        Self {
            name: name.into(),
            dtype: "float32-le".into(),
            shape: shape.into(),
        }
    }
}

/// Immutable caller-prepared input. Construction validates/hash-scans about 4 MiB;
/// call it off the UI thread. This is not image preprocessing or mask generation.
#[derive(Clone)]
pub struct PreparedInput {
    values: Arc<[f32]>,
    digest: Digest,
}
impl PreparedInput {
    pub fn from_values(values: Vec<f32>) -> Result<Self> {
        ensure!(
            values.len() == INPUT_VALUES,
            "Expected exact FP32 [1,5,384,512] input"
        );
        ensure!(
            values
                .iter()
                .all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
            "Input must be finite and in [0,1]"
        );
        let digest = values_digest(&values);
        Ok(Self {
            values: values.into(),
            digest,
        })
    }
    pub fn from_le_bytes(bytes: &[u8]) -> Result<Self> {
        ensure!(
            bytes.len() == INPUT_VALUES * 4,
            "Incorrect input byte length"
        );
        // Validate before allocating decoded numeric storage.
        ensure!(
            bytes.chunks_exact(4).all(|c| {
                let v = f32::from_le_bytes(c.try_into().unwrap());
                v.is_finite() && (0.0..=1.0).contains(&v)
            }),
            "Input must be finite and in [0,1]"
        );
        let values: Vec<f32> = bytes
            .chunks_exact(4)
            .map(|c| f32::from_le_bytes(c.try_into().unwrap()))
            .collect();
        Ok(Self {
            values: values.into(),
            digest: sha256(bytes),
        })
    }
    pub fn values(&self) -> &[f32] {
        &self.values
    }
    pub fn digest(&self) -> Digest {
        self.digest
    }
}

/// Backend output before validation. Fixed slot order is part of the package.
pub struct OutputTensor {
    pub shape: Vec<usize>,
    pub values: Vec<f32>,
}

/// Exact immutable FP32 outputs. Names identify numerical slots, not an accepted
/// photographic interpretation. In particular, exposure values have no inferred units.
pub struct RawFields {
    values: [Arc<[f32]>; 10],
    digests: [Digest; 10],
}
impl RawFields {
    pub fn validate(outputs: Vec<OutputTensor>) -> Result<Self> {
        ensure!(
            outputs.len() == HEADS.len(),
            "Expected exactly ten output tensors"
        );
        for (slot, (output, (name, shape))) in outputs.iter().zip(HEADS).enumerate() {
            ensure!(
                output.shape == shape,
                "Wrong output shape at slot {slot} ({name})"
            );
            let count: usize = shape.iter().product();
            ensure!(
                output.values.len() == count,
                "Wrong output sample count at slot {slot}"
            );
            ensure!(
                output.values.iter().all(|v| v.is_finite()),
                "Nonfinite output at slot {slot}"
            );
            if slot == 0 || slot == 5 {
                ensure!(
                    output.values.iter().all(|v| *v > 0.0),
                    "Nonpositive gain at slot {slot}"
                );
            } else if slot != 4 && slot != 9 {
                ensure!(
                    output
                        .values
                        .iter()
                        .all(|v| (-2e-6..=1.0 + 2e-6).contains(v)),
                    "Color table out of range at slot {slot}"
                );
            }
        }
        let digests = std::array::from_fn(|i| values_digest(&outputs[i].values));
        let values: Vec<Arc<[f32]>> = outputs.into_iter().map(|v| v.values.into()).collect();
        let values = values
            .try_into()
            .map_err(|_| anyhow::anyhow!("Incorrect field count"))?;
        Ok(Self { values, digests })
    }
    pub fn values(&self, slot: usize) -> Option<&[f32]> {
        self.values.get(slot).map(AsRef::as_ref)
    }
    pub fn digests(&self) -> &[Digest; 10] {
        &self.digests
    }
}

fn values_digest(values: &[f32]) -> Digest {
    let mut hash = Sha256::new();
    let mut bytes = [0u8; 4096];
    for chunk in values.chunks(1024) {
        for (i, value) in chunk.iter().enumerate() {
            bytes[i * 4..i * 4 + 4].copy_from_slice(&value.to_le_bytes());
        }
        hash.update(&bytes[..chunk.len() * 4]);
    }
    hash.finalize().into()
}

#[cfg(test)]
#[path = "fields-tests.rs"]
mod tests;
