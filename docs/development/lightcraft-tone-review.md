# Lightcraft tone and profile review

Reviewed 2026-10-20. Reference revision: [`abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d`](https://github.com/storytold/lightcraft/tree/abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d).

**VERIFIED — source/document inspection, not an image-quality comparison.**
Lightcraft's own code is offered under MIT or Apache-2.0. Its
[NOTICE](https://github.com/storytold/lightcraft/blob/abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d/NOTICE)
also lists separately licensed material. This review inspected only the named
first-party modules and documentation below; no vendored, GPL, or rawler source
was opened. No implementation was copied into Strehl.

## Relevant independent algorithms

- [`local.rs`](https://github.com/storytold/lightcraft/blob/abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d/crates/pipeline/src/local.rs)
  derives a highlights/shadows base from log luminance with a guided filter.
  Its fast path computes coefficients on a smaller plane and reconstructs with
  full-resolution guidance. This is a useful example of separating broad tone
  placement from the image's fine detail.
- [Process version V2](https://github.com/storytold/lightcraft/blob/abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d/docs/process-versions.md)
  adds a separable median before that base filter: radius 0.15% of the long
  edge, capped at 24 pixels. The stated purpose is to let narrow structures
  share their surroundings' tone shift while preserving their contrast.
  This is a design rationale, not photographic validation for Strehl.
- [`profiles.rs`](https://github.com/storytold/lightcraft/blob/abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d/crates/pipeline/src/profiles.rs)
  implements its own looks as scaled deltas beneath the displayed controls.
  The profile is separate from the user's slider positions.

## What this does not establish

The targeted modules did not expose an implementation of Adobe Adaptive or a
reverse-engineered equivalent. Lightcraft's
[`local_tone.rs`](https://github.com/storytold/lightcraft/blob/abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d/crates/pipeline/src/local_tone.rs)
evaluates an embedded DNG camera gain map, including position and color
dependence. Consuming such camera-authored data is distinct from inferring an
Adaptive treatment for an arbitrary photograph.

Its [XMP interoperability documentation](https://github.com/storytold/lightcraft/blob/abb49bdd76e64acd20afe2e4d7bb1cf71c548d1d/docs/xmp-interop.md)
also distinguishes imported settings from Adobe rendering: a camera-profile
name alone does not carry rendering data, and its own approximate starting
looks do not reproduce Adobe profiles. Unsupported AI fields are reported.

**ARGUED — implication for Strehl:** retain a separate image-dependent
treatment, recompute it when applying a portable preset to another photo,
and preserve the user's explicit controls. A guided base is a possible future
comparison arm. This inspection does not justify claiming Adobe equivalence,
recovered clipped texture, or better photographic quality.
