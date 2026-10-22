# Frozen learned-profile runtime

2026-10-22. The native compositor and persistence layer are implemented and tested.
They are **not an enabled AI editing profile**. Photographic acceptance and the
application's baseline/Amount integration remain open. A mathematically correct
renderer can still apply an inappropriate treatment to a photograph.

## Native contract

`strehl-edit::learned_profile` accepts linear FP32 BT.709 pixels, full-photograph
coordinates, explicit matrices, a brightness/spatial gain field, optional tone
knots, and background/subject/sky color tables. It does no inference or file I/O.
The caller declares the linear scale and stage ordering; an exposure-like model
output is not interpreted implicitly. Negative channels and HDR offsets survive
the declared gamut-extension operator. This is not an HDR model-table renderer.

The implemented order is source-to-working matrix, explicit scale, gain lookup
and multiplication, explicit tone, normalized semantic color transforms, inverse
matrix, and Amount blending. The gain brightness coordinate uses the number of
points, with the last point as the upper bound. Coordinates remain tied to the
whole photograph during native crop rendering. Missing semantic masks consume
zero weight. Exact Amount zero bypasses all processing.

This order is an original, explicit Strehl composition contract. In particular,
it does not implement a separate camera-dependent nonlinear exposure stage.
Applying it to an already-developed TIFF does not undo that TIFF's baked tone,
color, clipping, or quantization. Scene-linear masters and display photographs
need independently accepted application policies.

## Separate SDR scene contract

`strehl-edit::learned_scene` adds `strehl.scene-sdr-linear.v1` without changing
the existing compositor or its asset reader. `PreparedSceneSdrProfile` holds
immutable gain and color-table fields plus two explicitly supplied inverse color
transforms. Its full-strength `develop_pixel` and `render_region` operations are:

1. Transform scene-linear BT.709 into the declared working primaries, then clamp
   negative working channels to zero.
2. Query the gain map using working RGB multiplied by `gain_query_scale`.
3. Multiply the **unscaled** working RGB by that gain, then `exposure_scale`.
4. Cap the lowest and highest RGB channels at one and reconstruct the middle
   channel at its previous relative position between them. Equal channels remain
   equal. This is different from independently clipping each channel.
5. Apply the supplied color table, with its explicit encoding, interpolation and
   gamut policy, then the supplied inverse working transform.

Both scale factors may be below one; the caller supplies their already-resolved
linear values. The renderer does not infer EV units or camera compensation from
model outputs. Transform pairs, scale ranges, dimensions and finite arithmetic
are checked. Arithmetic overflow fails before the highlight cap can conceal it.
Native crops use full-photograph coordinates, and cancellation can leave an
unpublished partial output. The caller owns the destination buffer; the renderer
does not allocate another full photograph.

This is deliberately **SDR-only**. It discards negative working values and
highlight headroom; a floating-point return value does not make it an HDR
treatment. It currently has a single supplied color table, no semantic-mask
blend, and no nonlinear exposure allocation. No existing asset file is silently
reinterpreted as this contract. Its separate asset codec is described below;
recipe and UI integration remain disabled.

`blend_sdr_scene_pixel` is a separate boundary for Amount. The caller supplies a
**complete developed baseline** and a lazy candidate branch in the same declared
linear presentation domain. At zero, the baseline's exact bits are returned and
the candidate closure is never evaluated, including asset resolution. At one,
the candidate's exact bits are returned; intermediate Amounts use linear
interpolation. The scene primitive alone is not a complete application branch:
baseline placement, existing manual/region edits, contrast and presentation must
still be integrated and tested. Raw-source identity does not prove that Amount
zero preserves the existing application view.

**MEASURED (author commissioning):** fresh compilation and
`cargo test --offline -p strehl-edit --test learned-scene` passed eight synthetic
tests. Controls exercise unequal query/exposure scales, subunit scales, all RGB
permutations through the extrema cap, explicit asymmetric color transforms and
LUT encoding, crop/full bit agreement, rejected crop-local coordinates, finite
overflow, invalid inputs, cancellation, and exact baseline Amount endpoints
with an unevaluated failing candidate. These checks establish code behavior;
full application integration and photographic quality acceptance remain separate
gates.

**MEASURED (independent numerical comparison):** a separately compiled consumer
matched the previously commissioned private renderer bit-for-bit on eight frozen
cases, including a complete 7032 x 4688 photograph. That prior result also matched
the independent Python expression across all 98,898,048 samples at
`rtol=2e-5, atol=2e-6` (maximum absolute difference `1.43e-6`). The local consumer
was built with `cargo build --offline --release --manifest-path
outputs/ai-adaptive-production/scene-public-probe/Cargo.toml --target-dir
outputs/ai-adaptive-production/native-compositor-probe/target` and run against
the frozen specs with eight Rayon threads. Private photos and comparison fixtures
are not distributed; the public synthetic tests above remain reproducible without
them. This establishes the numerical port, not model quality or HDR equivalence.

## Immutable results

`learned_scene_asset::FrozenSceneAsset` persists the exact SDR scene contract in
a distinct `STRHLSC` version-1 envelope. It reuses the bounded identity, origin,
gain and color-table descriptors, but records **both** supplied transforms and
the separate gain-query/exposure factors. It accepts only
`strehl.scene-sdr-linear.v1`, one color table and whole-photograph analysis.
Regional analysis, semantic masks and unknown fields are rejected. Canonical
JSON, exact payload sizes, transform validation, SHA-256 and all finite/range
checks precede decoded FP32 field allocation. Accepted float bits, including
signed zero and subnormals, survive reopening. The asset shares an immutable
`Arc<PreparedSceneSdrProfile>` between consumers.

`LearnedAssetStore::save_scene` and `load_scene` are separate typed entry points
using the existing content-key namespace and atomic publication path. Expected
source, dimensions, input, model and contract identities are all required on
both read and write. Codecs reject each other's envelopes; neither falls back to
another treatment. Existing valid assets are reused without replacement, and
corrupt files, cancellation, competing writers, links and changed directories
retain the same failure behavior as legacy storage. A digest verifies content,
not the truth of caller-supplied provenance.

**VERIFIED (author commissioning):** `cargo test --offline -p strehl-edit` passed
126 tests after fresh compilation. Twelve new tests cover a literal legacy wire
fixture's unchanged bytes, scene-field bit round trips and rendered output,
cross-codec rejection, malformed/duplicate/unknown metadata, every truncated
length, correctly hashed invalid fields, external identity mismatches, missing
or corrupted assets, idempotent/concurrent publication and cancellation after a
complete temporary write. `cargo clippy --offline -p strehl-edit --all-targets
-- -D warnings` also passed. Independent codec/store review remains required
before claiming production integration; no recipe or model is enabled here.

`learned_asset` freezes the exact FP32 fields, matrices, tone, mask geometry,
original dimensions, and source/input/model/contract identities in a versioned
container. A SHA-256 digest detects corruption; it is not authentication or a
publisher signature. Envelope, shape, range, finite-value and matrix checks
precede decoded-field allocation. Assets are bounded to 32 MiB; masks remain
bounded native planes rather than full-resolution RGB images.

`learned_store` publishes these objects into an existing trusted local directory,
using typed content keys and synced, non-replacing publication. Missing, damaged,
wrong-source or unsupported identities return errors. Concurrent identical saves
can reuse an object; conflicting content is not overwritten. Cancellation leaves
no partial published object. Old objects are retained because saved versions,
Undo and recovery may still reference them. Directory identity/link checks detect
ordinary replacement; this API is not a sandbox against hostile concurrent
filesystem mutation.

These modules do not yet resolve assets into UI recipes. Future integration must
freeze one compiled snapshot for preview, native zoom, export and saved versions.
Pan, zoom and Amount changes must reuse fields rather than rerun inference.
Amount zero must match the complete existing application view, including its
baseline, not merely the raw linear input. No-asset behavior must remain unchanged.

## Executed checks

**VERIFIED:** fresh compilation followed by:

```text
cargo test --offline -p strehl-edit
cargo test --offline -p strehl-ui agent_interface::mcp::tests
```

The edit library's 106 unit/integration tests passed. New controls cover asymmetric
matrix/LUT axes, nonlinear ordering, negative/HDR values, overlapping masks,
full-frame/crop agreement, exact zero Amount, finite-overflow errors, cancellation,
malformed containers, wrong identities, concurrent publication and directory
replacement. Windows storage tests use a workspace-local TEMP/TMP directory;
the restricted runner's default temporary directory refused rename operations.

**VERIFIED in local probes:** independent NumPy composition agreed with native
FP32 on nonidentity fixtures and one complete 7032 by 4688 photograph. The latter
maximum absolute difference was 1.43e-6 linear units. Saving and reopening the
frozen asset reproduced the complete native pixel hash. Six complete development
photographs also retained exact input bytes at Amount zero. These are arithmetic
and persistence checks, not photographic preference or vendor-parity tests.

**MEASURED, isolated probe:** three eight-thread native renders of the complete
insect photograph took 0.3953, 0.3935 and 0.3944 seconds. This excludes input
decoding, inference, display conversion, texture upload and application scheduling.
It is not an interaction-latency claim or a cross-platform benchmark.

The local probe commands and private image receipts remain outside the repository:

```text
python outputs/ai-adaptive-production/make-compositor-fixtures.py
python outputs/ai-adaptive-production/verify-native-photo.py
python outputs/ai-adaptive-production/render-six-photo-native.py
```

No private photograph, recovered model, learned checkpoint, or proprietary
implementation is included in these modules. The existing editor is unchanged
until a full photographic and application-level acceptance pass succeeds.
