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

## Immutable results

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
