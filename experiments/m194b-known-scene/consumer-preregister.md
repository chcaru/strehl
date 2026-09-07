# M194b known-scene consumer preregistration

2026-09-07, before consumer/dependency edits. M194 accepted source is
`19e230fbd44f58badd0959906ae1f1eb5519c60a`; M194b was allocated and committed
before dispatch. This follows `review-production-truth/forward-model-plan.md`
and its named prior-art/refusal record. No M25 or production arithmetic changes.

## Contract fixed with the producer before implementation

The strict JSON manifest is `m194b-known-scene-v1`, with exactly these top-level
keys: `schema`, `scene`, `noise_enabled`, `repeat`, `sensor`, `geometry`, `frames`,
`producer`. The producer owns the exact specimen and model commissioning.

- `sensor`: width, height, active_origin, stride, buffer_height, black, white,
  iso, wb, noise_gain_dn_per_e, read_noise_e, cfa. The registered run is active
  320x240 RGGB, origin (2,4), stride327/storage height247, levels512/15360,
  ISO160, WB(4/3,1,5/3), gain0.25 DN/e and RN4 e.
- `geometry`: reference_index4, scale_centre_native(183,101), and nine entries
  `{index, focus, scale}`. Scale is canonical-to-frame, not its inverse; native
  centre and production quad-plane centre are translated explicitly.
- `frames`: nine `{index, path, bytes, sha256}` entries. Each file is exactly
  153600 bytes of active-area u16 little-endian CFA. Relative normal paths only;
  canonical resolution must stay below the manifest directory. Decoding checks
  SHA-256 again on every read and copies rows into poisoned u16 padded storage.
- `producer`: preregistration_sha256, source_sha256 map, expected_electrons_sha256,
  command. These bind the declared producer; they do not independently validate
  its physical or numerical model.

Unknown/duplicate JSON fields, invalid types/counts/nonfinite values, malformed
digests, unsafe paths, lengths/hashes, unsupported CFA/noise/configuration, bad
reference or unplaceable geometry must fail before producing a successful TIFF.
Serde and SHA-256 are approved test-only dependencies; no private JSON parser
or copied digest implementation is introduced.

## Trust and two-stage execution

An external trusted expected manifest SHA-256 is required on every invocation.
Plan mode validates the manifest/files, constructs the real WarpMap and actual
`cover_or_explain(Crop)` / `pyramid_domain`, and writes a receipt before any
image decode/fold/writer. The receipt includes exact consumed f32 noise/WB,
placements in native and quad coordinates, full/domain dimensions, source
bindings, merge settings and the fixed output-to-canonical coordinate map.

Render mode requires the earlier plan plus its external expected SHA-256,
recomputes and compares the whole plan, then invokes `run_pyramid_prepared`.
Thus a candidate-rehashed false map/crop or same-size translated descriptor
cannot authorize its own geometry. This is a test-local trusted fixture
boundary, not a general M193 real-output adapter or authenticity protocol.

Both the nine-frame stack and the single original frame4 use the frozen
nine-frame crop/full-plane gauge. The single source reindexes original4 to
local0 only for source access; the receipt explicitly preserves original
reference4 and records local reference0. No cropped single-frame re-solve.

## Falsifiers before checks

1. Wrong pull direction/scale centre/CFA offsets or crop origin must disagree
   with independently computed per-site coordinates and delivered TIFF checks.
   Every map must use every frame's own transform; endpoint agreement alone is
   insufficient. The reference and curved interior must actually occur.
2. One changed file byte, truncation, wrong hash, malformed count/schema/path,
   or an altered trusted plan must refuse with no successful output receipt.
   Corresponding unchanged controls must succeed.
3. Gain0.25/RN4/levels512/15360 are injected once as `NoiseModel::new`, with
   explicit synthetic-known receipt and `Provenance::Fallback`; no camera
   profile lookup or stage-specific noise estimate may replace them. At signal
   3000 DN, the declared per-site variance is751 DN²; the independent verifier
   must check model injection and a wrong-model refusal.
4. Plan-only emits no TIFF and freezes actual Crop before candidate pixels.
   Full9 and single4 must share that domain, normalization, WB and writer config.
   The receipt binds actual TIFF SHA/dimensions/channels and decode counts.
5. The real writer remains CameraLinear, full-resolution demosaic, three bands,
   gate2, Catmull-Rom, with CA/defect/restoration off. All other resolved merge
   settings and environment are recorded. Any unexpected override is refused.
6. If confidence is enabled as a control, its main TIFF must be byte identical
   and the source must be reread. Confidence is not needed for baseline scoring.
7. All new code visibly compiles; tests are opt-in/ignored and serial, with no
   real RAW path or solver. No change to product arithmetic or M194 artifacts.

Producer optics/noise commissioning and root's independently derived scorer
are separate required checks. This consumer does not certify camera constants,
physical defocus/occlusion, live alignment, native resource admission, or SOTA.
