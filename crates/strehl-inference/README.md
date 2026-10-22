# Predictor infrastructure

This standalone crate is infrastructure only. It does not enable an AI profile,
include model weights, prepare photographs, infer semantic masks, or establish
photographic quality or equivalence with another application's rendering.

Its separate workspace and optional `tract-runtime` feature keep inference
dependencies out of Strehl's ordinary UI/CLI build. The default build validates
packages, prepared inputs and raw outputs, and supplies a backend-neutral worker.
No Python process, ONNX importer, GPU runtime or external runtime DLL is needed by
the optional pure Rust NNEF backend.

## Boundaries

- The caller approves exact model, input-contract and render-contract identities.
  An incoming manifest cannot declare itself supported. SHA-256 provides integrity,
  not publisher authentication. Model execution is not a sandbox for hostile graphs.
- JSON metadata is bounded to 64 KiB; model bytes to 128 MiB. Declared sizes are
  rejected before payload allocation. Unexpected fields, duplicate fields, partial
  objects, surplus bytes, hash mismatches and wrong tensor declarations fail.
- Inputs are exact FP32 `[1,5,384,512]`, with finite values in `[0,1]`. Preparing
  that tensor, including scene normalization and two semantic mask planes, is the
  caller's separate accepted contract. An input hash identifies exact little-endian
  FP32 bits. It does not prove that preprocessing was photographically appropriate.
- Ten raw FP32 output slots retain exact values and content hashes. Gains must be
  positive, tables bounded within the declared FP32 tolerance, scalars finite.
  Names including `exposure` and `_hdr` do not assign units or select a rendering
  branch. No fields are converted into a `FrozenLearnedAsset` here.
- One lazy worker retains one runtime and one replaceable queued request. Later
  requests cancel older work and invalidate old completions. A synchronous backend
  retains its occupied lane until it returns; cancellation cannot interrupt its
  kernel. Backend failures/panics discard runtime state and permit a later retry.
- Drop/close signal cancellation without joining a worker on the UI thread.
  `join` is an explicit blocking drain for tests or process shutdown. Keep the
  same service for successive requests; opening new services does not provide a
  process-wide inference-concurrency limit.
- Submission moves already-validated immutable tensors. Package reads, tensor
  preparation and hashing must run off the UI thread. Pan, zoom and Amount changes
  should reuse a later frozen treatment rather than submit inference requests.

`InferenceResult` binds raw fields to source dimensions/hash, revision/scope,
input tensor hash and package/contract identities. The consumer must still verify
that the current document matches before publishing any UI or recipe change.
Frozen asset publication, recipe references, baseline/Amount semantics, semantic
mask generation, and photographic acceptance remain separate integration work.

## Validation commands

Run from the repository root. These commands describe validation; this README does
not claim that a particular run passed.

```text
cargo test --manifest-path crates/strehl-inference/Cargo.toml
cargo check --manifest-path crates/strehl-inference/Cargo.toml --features tract-runtime
```

Default tests use a deliberately fake backend and no model data. Blocking channels
prove that superseded queued requests never run, cancelled calls retain their lane,
stale successes/errors/panics cannot publish, and errors do not strand later work.
Optional-backend compilation checks are not native/model numerical parity tests.
The existing `experiments/adaptive-distillation/native-probe` remains the separate
model compatibility instrument until this service receives independent parity and
application-latency validation.
