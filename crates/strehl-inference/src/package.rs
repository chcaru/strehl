use crate::fields::{HEADS, INPUT_SHAPE, TensorSpec};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};
use std::{io::Read, sync::Arc};

pub type Digest = [u8; 32];
pub const MAX_MANIFEST_BYTES: usize = 64 * 1024;
pub const MAX_MODEL_BYTES: usize = 128 * 1024 * 1024;

pub fn sha256(bytes: &[u8]) -> Digest {
    Sha256::digest(bytes).into()
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContractIdentity {
    pub id: String,
    pub sha256: Digest,
}

impl ContractIdentity {
    fn validate(&self) -> Result<()> {
        ensure!(
            !self.id.is_empty()
                && self.id.len() <= 128
                && self
                    .id
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b"._-/".contains(&c)),
            "Invalid contract identifier"
        );
        Ok(())
    }
}

/// Exact identities approved by the caller, independently of the incoming manifest.
/// Digests detect changes; an arbitrary self-consistent package is not authenticated.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PackageIdentity {
    pub model: ContractIdentity,
    pub input: ContractIdentity,
    pub render: ContractIdentity,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PackageManifest {
    pub version: u32,
    /// Only "nnef-tar" is supported. This crate never imports ONNX at runtime.
    pub format: String,
    pub identity: PackageIdentity,
    pub model_bytes: u64,
    /// Numerical layout contract only, distinct from photographic input/render contracts.
    pub tensor_contract: String,
    pub input: TensorSpec,
    /// Slot order is authoritative; graph node names are not semantic head names.
    pub outputs: Vec<TensorSpec>,
}

impl PackageManifest {
    pub fn fixed(identity: PackageIdentity, model_bytes: u64) -> Self {
        Self {
            version: 1,
            format: "nnef-tar".into(),
            identity,
            model_bytes,
            tensor_contract: "strehl-predictor-fp32-ten-head-v1".into(),
            input: TensorSpec::new("input", &INPUT_SHAPE),
            outputs: HEADS
                .iter()
                .map(|(name, shape)| TensorSpec::new(name, shape))
                .collect(),
        }
    }

    fn validate(&self, allowed: &[PackageIdentity]) -> Result<()> {
        ensure!(self.version == 1, "Unsupported predictor package version");
        ensure!(self.format == "nnef-tar", "Unsupported model format");
        ensure!(
            self.tensor_contract == "strehl-predictor-fp32-ten-head-v1",
            "Unsupported tensor contract"
        );
        ensure!(
            (1..=MAX_MODEL_BYTES as u64).contains(&self.model_bytes),
            "Model exceeds its byte bound"
        );
        self.identity.model.validate()?;
        self.identity.input.validate()?;
        self.identity.render.validate()?;
        ensure!(
            allowed.contains(&self.identity),
            "Model/input/render contract combination is not approved"
        );
        ensure!(
            self.input == TensorSpec::new("input", &INPUT_SHAPE),
            "Incorrect input declaration"
        );
        ensure!(
            self.outputs.len() == HEADS.len(),
            "Expected exactly ten output slots"
        );
        for (actual, (name, shape)) in self.outputs.iter().zip(HEADS) {
            ensure!(
                *actual == TensorSpec::new(name, shape),
                "Incorrect output slot declaration: {name}"
            );
        }
        Ok(())
    }
}

#[derive(Clone)]
pub struct PredictorPackage {
    manifest: Arc<PackageManifest>,
    model: Arc<[u8]>,
    digest: Digest,
}

impl PredictorPackage {
    /// Reject sizes and declarations before allocating a model copy. Parsing validates
    /// integrity and the caller's exact allowlist; it does not sandbox model execution.
    pub fn from_bytes(manifest: &[u8], model: &[u8], allowed: &[PackageIdentity]) -> Result<Self> {
        ensure!(
            !manifest.is_empty() && manifest.len() <= MAX_MANIFEST_BYTES,
            "Manifest exceeds its byte bound"
        );
        ensure!(
            !model.is_empty() && model.len() <= MAX_MODEL_BYTES,
            "Model exceeds its byte bound"
        );
        let manifest: PackageManifest = serde_json::from_slice(manifest)?;
        manifest.validate(allowed)?;
        ensure!(
            manifest.model_bytes == model.len() as u64,
            "Truncated or surplus model bytes"
        );
        ensure!(
            sha256(model) == manifest.identity.model.sha256,
            "Model digest mismatch"
        );
        Self::validated(manifest, model.into())
    }

    /// Lengths are checked before reading/allocating either payload. Readers must
    /// expose one complete object: both early EOF and surplus bytes are errors.
    pub fn read(
        manifest_length: u64,
        manifest: &mut dyn Read,
        model_length: u64,
        model: &mut dyn Read,
        allowed: &[PackageIdentity],
    ) -> Result<Self> {
        ensure!(
            (1..=MAX_MANIFEST_BYTES as u64).contains(&manifest_length),
            "Manifest exceeds its byte bound"
        );
        ensure!(
            (1..=MAX_MODEL_BYTES as u64).contains(&model_length),
            "Model exceeds its byte bound"
        );
        let header = read_exact_object(manifest, manifest_length as usize)?;
        let descriptor: PackageManifest = serde_json::from_slice(&header)?;
        descriptor.validate(allowed)?;
        ensure!(
            descriptor.model_bytes == model_length,
            "Model length differs from manifest"
        );
        let bytes = read_exact_object(model, model_length as usize)?;
        ensure!(
            sha256(&bytes) == descriptor.identity.model.sha256,
            "Model digest mismatch"
        );
        Self::validated(descriptor, bytes.into())
    }

    fn validated(manifest: PackageManifest, model: Arc<[u8]>) -> Result<Self> {
        // Canonical metadata includes the model digest; whitespace is not identity.
        let digest = sha256(&serde_json::to_vec(&manifest)?);
        Ok(Self {
            manifest: Arc::new(manifest),
            model,
            digest,
        })
    }
    pub fn manifest(&self) -> &PackageManifest {
        &self.manifest
    }
    pub fn model_bytes(&self) -> &[u8] {
        &self.model
    }
    pub fn digest(&self) -> Digest {
        self.digest
    }
}

fn read_exact_object(reader: &mut dyn Read, length: usize) -> Result<Vec<u8>> {
    let mut bytes = vec![0; length];
    reader.read_exact(&mut bytes)?;
    let mut extra = [0];
    ensure!(
        reader.read(&mut extra)? == 0,
        "Surplus bytes after bounded object"
    );
    Ok(bytes)
}

#[cfg(test)]
#[path = "package-tests.rs"]
mod tests;
