# Exact merged CFA sensor master

`strehl stack INPUT --out photograph.tiff --srgb --sensor-master sensor.tiff`
adds an opt-in signed FP32 CFA export to the pyramid consumer. It writes
`sensor.tiff` and `sensor.tiff.json`. The parent directory must already exist;
neither destination may exist or alias another source/output. The default remains
off, with no source hashing, serialization, or extra image allocation.

`--sensor-master-placebo` is a separate, mutually exclusive mode. It runs the
same serialization against a sink, creates no sensor files, and emits the same
TIFF/payload/per-plane hashes. Both modes emit a machine-readable stderr line
beginning `sensor-master-receipt `. Both require `--out`, the pyramid backend,
and restoration disabled. The sensor file is independent of the chosen display
exposure or color output. Those controls still apply to the normal photograph.

## Pixel contract: strehl-merged-cfa-f32-v1

The input is the original four compact planes returned by pyramid collapse,
after optional region repairs and before white balance, exposure, normalization,
demosaicing, color conversion, or restoration. The observer borrows these planes;
it never calls `Merged::value`, whose nonnegative clamp would lose information.

- Plane order is **R, G1, G2, B**, distinct from `CfaPlane::ALL`.
- Mosaic rows interleave **R/G1** and **G2/B**, with exact original FP32 bits.
- Units are signed, black-subtracted camera DN. Negative values, negative zero,
  and values above the source usable white level are retained. Nonfinite samples
  fail the export; they are never replaced or silently clipped.
- The output dimensions are twice the compact quad domain in each direction.
  The sidecar records the full reference grid, compact quad rectangle, and
  corresponding origin in reference active pixels. `cover scale` remains a
  transformed grid, not a native sensor crop; the resolved warp map and coverage
  fit are recorded separately.
- The TIFF is little-endian, uncompressed, one FP32 CFA sample per pixel. A
  deterministic sequential writer uses one row buffer. It does not allocate an
  extra full mosaic or materialize aligned source frames. Version 1 refuses
  files exceeding the classic TIFF 4 GiB offset range.

This is an interchange/diagnostic master, **not a camera RAW or a DNG**. TIFF-EP
CFA tag values describe the emitted R/G1/G2/B arrangement. The file does not
invent orientation, original camera crop, calibration tags, color profiles,
native black/white tags, or claim compatibility with a particular RAW editor.

## Provenance and publication

The sidecar contains ordered SHA-256 source bindings, the actual first decoded
source metadata, binary hash, relevant environment, source-file settings,
resolved warp map and independent alignment anchor index, coverage, merge/noise
configuration, defect map, applied region recipe, and execution plan. Metadata
that comes from the first sorted source is explicitly identified as such; it is
not relabeled as alignment-anchor metadata. Source and supplied input-file hashes
are checked again before publication. These opt-in checks add I/O.

The sidecar records complete serialized TIFF, mosaic payload, and individual
plane hashes, plus signed range and out-of-range counts. Original wrapper
floating metadata is stored as bit patterns so unsupported/NaN camera fields
are not silently converted to JSON null.

Normal photograph/master/confidence writing completes first. Sensor errors leave
those completed outputs intact. Both sensor files are prepared and flushed before
publication. Each destination is atomically created without replacing an existing
file (Windows move without replacement; Unix hard link). The JSON sidecar is the
commit record: a consumer must require both files and verify the TIFF hash. A
crash or a competing sidecar between the two publications can leave a complete
TIFF without its sidecar; this is an incomplete pair, not a valid master. Files
on filesystems without the required atomic operation fail explicitly.

## Validation boundary

Author tests exercise asymmetric plane/row ordering, exact negative/overshoot
bits, compact crop offsets, invalid samples and dimensions, changed/missing
sources, normalized destination collisions, atomic no-replacement publication,
failed-export preservation of the normal photograph, and exact sink/file
hash agreement. These are implementation tests, not photographic quality claims.

The independent consumer test uses a full stack run with the same binary,
sources, fixed warp map, and options in off/off/on/placebo arms. Primary TIFF,
linear master, and confidence output hashes must agree across all arms; on-file
TIFF/payload hashes must match placebo and an independent TIFF decoder. This
gate passed on a complete 33-frame stack: all three existing outputs were
byte-identical across all four arms. Independent TIFF decoding matched every
stored sample and all four phase hashes; the file and placebo serializer hashes
also matched. Source files were hashed before and after and remained unchanged.
This scene exercised fractional samples but contained no negative values;
independent asymmetric synthetic cases covered negatives, negative zero,
subnormals and finite overshoot separately.

**VERIFIED:** `cargo test --offline -p strehl-cli sensor_master --lib` passed
12 tests after fresh compilation. On Windows the tests use a workspace-local
`TEMP`/`TMP`; the restricted default temporary directory refused publication.
Independent tests additionally exercised short writes, injected write failures,
same-length source changes, competing destination creation and oversized
reference coordinates. A discovered crop-origin overflow was corrected before
rebuilding and repeating the complete four-arm consumer test.

The local read-only consumer commands were:

```text
python outputs/ai-adaptive-production/sensor-master-validation-v2.py prepare --exe target/release/strehl.exe
python outputs/ai-adaptive-production/sensor-master-validation-v2.py run --plan-sha256 e18526b2906c3d27942edb10b13c688400f7069aca38535215e8ecbf060369ef
python outputs/ai-adaptive-production/native-pair-audit/verify-sensor-master-v2.py
```

The private plan binds the exact executable, input files, options and warp map;
its image receipts remain outside the public repository. These checks establish
nonperturbation for that consumer configuration, not photographic quality,
performance, general RAW-editor compatibility or all possible engine modes.
