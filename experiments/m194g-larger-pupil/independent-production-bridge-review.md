# Independent larger noisy-CFA bridge design review

2026-09-07. Source/design review only; no module import, decoder, render,
noise draw or metric execution. Reviewed root's
`next-production-bridge-design.md` at SHA256
`544ea5cc555ed72648198f1ad1ff1ef7545728841f89d9f3220216a5073e5896`
against the frozen software-noise interface
`98048ba64d9f984e6dbba17607b40d6c5899057aa88708b9354e98a40fa131c2`
and the actual production consumers named below. M194f sources remain unchanged.

The proposed reuse boundary is appropriate. A new test-local input adapter can
feed `run_pyramid_prepared` without copying the merge, gather, noise estimator,
demosaic or writer. Approval is conditional on the two precise clarifications
below and freezing the small concrete bridge/control command set before runs.
Neither successful source construction nor these design arguments admit the
later38-output quality matrix.

## Required clarifications

1. **The missing-RAW sentinel is not a universal file-read trap.**
   `align_cmd::warp_frame_in_place_fullres` calls
   `strehl_raw::identity(&frame.path)` before resolving the CA profile, including
   the CA-off path. The local `strehl-raw/src/identity.rs::identity` explicitly
   returns `CaptureIdentity::EMPTY` when `File::open` fails; it does not propagate
   failure and never decodes pixels. Therefore change “unintended RAW reads
   fail explicitly” to the narrower guarantee: the source never delegates
   pixel decoding to RAW, sentinel paths cannot supply RAW pixels, and existing
   metadata lookups may attempt and harmlessly fail to open those paths. Keep
   CA explicitly off. No production edit is needed to make this honest.

2. **Persist the endpoint's actual probe index separately from provenance.**
   `run_pyramid_prepared` passes the selected list's local index through
   `BandWorker::fold` and `load_frame` to `Probe::measure`; that index seeds its
   deterministic noise. For original frame4 alone the original index is4,
   local source/reference index is0, and actual probe seed index is0. For
   original frame0 alone all are0. Record both the original reference2
   coordinate gauge and the selected source's local reference0 without
   pretending reference2 remains a member of a one-source map. Source bytes,
   frame provenance, local placement and probe seed need distinct explicit
   plan fields. A coherent relabel of original4 as0 must fail selection; a
   plan falsely claiming probe seed4 must fail the configuration reader.

## Scope and economical control conditions

- **Three Laplacian bands is not three measured floors.**
  `gatefloor::Probe::run` sets the eligible count to
  `min(4, level_sizes.len().saturating_sub(2))`, so four levels permit at most
  two measured beta values. `BandWorker::fold` truncates at the first nonfinite
  value, increments `beta_n` only for a nonempty prefix, and passes that actual
  prefix into `add_frame_with_gain`. The existing terminal banner and its
  contributing count are a sufficient bounded witness of that narrow claim.
  They cannot prove exact beta values, all-band measurement, or calibrated
  noise. Keep the nonempty-prefix wording; persist its actual length and name
  the remaining white-floor fallback. Require exactly one matching measured
  banner/count pair from the bound successful command log. Missing, duplicated,
  nonfinite or altered-count private log companions must refuse. Explicitly
  clear `STREHL_GATE_FLOOR_SCALE` and the white/debug override, since scaling
  can extend a list past the genuinely measured prefix and choices are cached.

- **The new decoded rail interval must be tested before downstream clamps.**
  The old M194f source requires `[512,15360)`, which is deliberately wrong here.
  Use private actual bytes containing0,511,512 and15360; require exact returned
  u16 values from the new source and refuse15361. A black-clamped source mutant
  must fail that direct check even if a later TIFF looks plausible.
  `PlaneNoise::variance` separately clamps negative signal for its variance,
  and the production writer has its own nonnegative conversion. Neither
  behavior proves that the input reader preserved below-black samples.
  This does not replace the generator's independently checked pre-clipping
  excursions or authorize clipped intended files.

- **Keep the actual Crop and fixed support guard.**
  `cover_or_explain(Crop)` derives `k` with `COVER_MARGIN_PX=3` and calls
  `cover_rect`; `pyramid_domain` uses that rectangle before luma, variance and
  fold. Store the returned rectangle/level sizes and compare endpoint and
  five-frame plans, rather than copying M194f dimensions or assuming a maximal
  covered rectangle. The proposed74-native-pixel window guard still requires
  an actual plan check before quality admission. Identity placement does not
  independently commission deep-focus alignment or physical optics.

- **Use the actual noise-admission DAG, not repeated pass strings.**
  The interface's outer five FileRefs are repository-relative; the manifest's
  CFA/audit/contract/runtime children are manifest-relative, while its two
  upstream commissions remain repository-relative. Cross-bind the exact
  generation manifest, independent read and two prerequisite references.
  Require the complete ordered18-bundle/90-frame record and select by actual
  scene/noise/seed/original-index tuple. Hash/check all declared payloads with
  bounded streaming and end-of-command bindings; decode only the selected
  five or one. Coherently rehashed wrong tuple/child/path/header metadata and
  same-length changed CFA companions test this boundary, without inventing
  successful independent authority. Equal bytes in distinct flat/noise-off
  files remain legal; path aliases and the same actual file used twice do not.

- **Do not inherit irrelevant auxiliary-output work.**
  The proposed38 quality outputs are RGB only. Keep confidence off in this
  bridge unless a separate explicit need is registered. M194f's rank/Gray
  controls remain historical evidence for that unchanged consumer; repeating
  them does not test the newly changed dimensions, rails or noise authority.
  Larger private constant/affine/channel controls should instead reach the
  actual four-level fold and writer. Decode off/count/placebo checks need
  actual hook/count liveness and equal file/pixel bytes, with a named decode
  fault distinct from a stale hash or unsupported exposure refusal.

These are prospective consumer conditions, not observed passes. The fixed
noise law supplies the injected coefficients and cannot validate their physical
calibration. The full-float admission and software-noise admission must exist
before any intended bridge input is accepted; neither grants product-quality
or SOTA authority.
