//! Model-independent infrastructure, not an enabled AI editing profile.
//!
//! Packages contain trusted caller-approved NNEF bytes. Inputs are already prepared
//! FP32 tensors; this crate does not choose photographic color, mask, normalization,
//! exposure, HDR, or rendering semantics. Outputs remain uninterpreted numeric fields.
//! Package preparation and input validation belong on background workers.

mod fields;
mod package;
mod worker;

pub use fields::{HEADS, INPUT_SHAPE, OutputTensor, PreparedInput, RawFields, TensorSpec};
pub use package::{
    ContractIdentity, Digest, MAX_MANIFEST_BYTES, MAX_MODEL_BYTES, PackageIdentity,
    PackageManifest, PredictorPackage, sha256,
};
pub use worker::{
    Backend, Cancellation, Completion, InferenceRequest, InferenceResult, InferenceService,
    RequestIdentity, Ticket,
};

#[cfg(feature = "tract-runtime")]
#[path = "tract-backend.rs"]
pub mod tract_backend;
