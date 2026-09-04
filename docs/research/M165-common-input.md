# M165 — common linear input and Strehl byte-identity boundary

## Verdict

**Infrastructure: commissioned. Competitive package: not yet renderable.**

M165 now provides a frozen LibRaw-based converter, a deterministic minimal TIFF
writer, a strict Rust TIFF adapter, and a fail-closed identity verifier. On the
commissioning fixture, the TIFF pixel bytes, decoded internal `u16` bytes, and the
exact `f32` planes passed to `strehl_core::pyramid::BandMerge::add_frame` all hash to
the same value.

That is not a competitive result. No eligible deterministic-pattern map made from
independent matching dark and flat captures exists. The converter therefore refuses
to emit a common-merge TIFF, and no campaign/common-input identity can yet be tested.
Per the live scorecard, **M1 and M9 remain `UNMEASURED`**. All downstream competitive
work must continue to treat the common-merge package as absent.

The governing text was re-read after its two-track amendment:
`docs/proposals/2026-09-sota-scorecard.md` §1.2. The copy used for the final audit had
SHA-256 `ad223867c20e9abcc0b6b576ec1471fa7a9ff34259c9e64f8fc41c003f9ac03b`;
the hash is independently recorded in
`experiments/M165-common-input/out/independent-hash-audit.json`. Section 1.2 names
common-merge as the sole publication track, makes the missing map fatal to M1/M9,
and requires either a Strehl TIFF adapter or hash identity at the internal pre-merge
boundary (`2026-09-sota-scorecard.md:287-310`).

## What already existed and was reused

1. **A partial LibRaw audit, not a contract renderer.**
   `docs/research/SCORECARD-BASELINE.md:14-17,23-35,68-89` and
   `experiments/SCORECARD-BASELINE/out/INPUT-MANIFEST.json` had already identified
   rawpy/LibRaw, recorded source hashes and explicit linear-development settings,
   found matching bee darks/flats `0/0`, and stated that the ProPhoto TIFF adapter
   was absent. M165 retained its explicit-settings and separate-hash approach.
2. **Manifest shapes.**
   `experiments/M153-m11-harness/staged-input-manifest-template.json` already had
   fields for source, decoder artifacts, settings, deterministic pattern map, TIFF
   hash, and pixel hash.
   `experiments/M153-m11-harness/adapter-identity-template.json` already required
   paired common-pixel/internal-pixel hashes. M165 implemented those fields rather
   than introducing an incompatible evidence vocabulary.
3. **The blocker was independently reproduced.**
   `docs/research/M161-m3-ratification.md:4-9,182-188` records the missing
   common-input package and adapter as an M3 blocker.
4. **Strehl's existing boundary was located rather than replaced.**
   `strehl_raw::decode` returns a mosaiced `u16` CFA `Frame`
   (`crates/strehl-raw/src/lib.rs:74-99,252-343`). The shipping pyramid path then
   extracts four half-resolution CFA planes in
   `crates/strehl-cli/src/merge_cmd.rs:4500-4910`. There was no RGB TIFF input.
   M165 reused the existing generic `BandMerge`, which accepts an arbitrary plane
   count, for the adapter's actual merge-ingestion commissioning.
5. **Flat-field work was useful evidence but not a reusable map.**
   M71 measured PRNU and retained flat-analysis arrays, but did not emit the paired
   dark-offset plus flat-gain map demanded by §1.2. The measured file census is in
   `experiments/M165-common-input/out/pattern-map-audit.json`.

## What was built

| Artifact | Role |
|---|---|
| `experiments/M165-common-input/converter.py` | Fail-closed converter, frozen ICC generator/inspector, deterministic TIFF writer/inspector, pattern-map validator, and manifest writer. |
| `experiments/M165-common-input/settings-v1.json` | Exact v1 conversion settings. |
| `experiments/M165-common-input/converter-freeze-v1.json` | Converter/runtime freeze made before any render attempt. |
| `experiments/M165-common-input/linear-prophoto-d50-v1.icc` | Deterministically generated linear ProPhoto/ROMM RGB D50 ICC v2 profile. |
| `experiments/M165-common-input/pattern-map-manifest-template.json` | Required map/source/capture/estimator contract; deliberately `UNFROZEN`. |
| `crates/strehl-raw/src/common_tiff.rs` | Strict TIFF parser, payload/internal hashing, provenance checks, and RGB merge-plane adapter. |
| `crates/strehl-cli/src/bin/strehl-common-input.rs` | Fail-closed verifier; optionally passes the hashed planes into the actual core `BandMerge`. |
| `experiments/M165-common-input/commission.py` | Null, mutation, repair, malformed-input, pattern degradation, and pattern improvement commissioning. |
| `experiments/M165-common-input/development_probe.py` | One-frame in-memory probe on a burned development RAW; cannot emit a TIFF. |
| `experiments/M165-common-input/out/` | Machine-readable freeze, preflight, commissioning, development-probe, pattern-audit, and independent-hash evidence. |

The renderer is at `converter.py:918`; it validates the frozen converter and map
before pixel development. The TIFF writer and independent Python parser are at
`converter.py:438-637`. The strict Rust parser and identity boundary are at
`common_tiff.rs:97-430`; the actual core-ingestion probe is at
`strehl-common-input.rs:135-165`.

## Converter freeze

`converter-freeze-v1.json` records:

- converter ID/version: `m165-libraw-common-linear` `1.0.0`;
- Python `3.12.10`;
- rawpy `0.27.0`;
- LibRaw `0.22.1`;
- NumPy `2.4.4`;
- ExifTool `13.58`;
- rawpy native extension SHA-256
  `51fecc08ba36294590a9a4b35f0ce246f0349a9b9ee509a13d6589ba7150b897`;
- converter source SHA-256
  `91c5a072a49d61ba603b19cf699cab12d13d54b9831687c73e98a03c095e3043`;
- settings SHA-256
  `a98782442233cfbe567af18d724083a7cdd7c8c85116ac76d71ba87ea49b9587`;
- ICC SHA-256
  `16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef`;
- composite executable-bundle SHA-256
  `f279733cf12053a8d59db297f9e20f18e9d1ee232661c5b0c6d76de0de3f7dd6`.

The bundle digest covers the converter source, Python executable, rawpy Python
module and native extension, NumPy module and native extension, ExifTool executable,
settings, ICC, and all reported versions. `render` recomputes every member and
refuses a mismatch before touching the source pixels.

## Frozen conversion and TIFF contract

### Sensor and development order

For each source, the renderer:

1. hashes the ARW;
2. reads make/model/ISO/exposure/aperture/lens/focal length and available
   serial/focus-distance/temperature fields without consulting an XMP;
3. verifies a frozen pattern-map manifest, disjoint non-empty dark/flat source
   sets, estimator executable hash, capture match, sensor fingerprint, map hash,
   shape, float32 types, finite offsets, and positive gains
   (`converter.py:638-753`);
4. computes, in sensor coordinates,
   `black + clip((raw - black - offset_dn) * gain, 0, white - black)`, with
   `numpy.rint` to `u16` (`converter.py:754-780`);
5. tells LibRaw explicitly that total black is
   `user_black=0 + user_cblack=[camera channel levels]`, and supplies the camera
   white as `user_sat`;
6. applies recorded camera WB, one LibRaw camera-to-ProPhoto conversion, AHD once,
   16-bit output, `gamma=(1,1)`, and no rotation or resize.

Auto WB, auto brightness, exposure shift, maximum auto-adjustment, FBDD/wavelet/
median denoising, chromatic-aberration scaling, bad-pixel repair, and every
sidecar-driven or cosmetic development operation are disabled in
`settings-v1.json` and enforced by `converter.py:782-816`.

### TIFF encoding

The writer emits little-endian classic TIFF with one full-image, row-major,
interleaved RGB strip. The only IFD entries are the structural fields,
`ImageDescription` canonical provenance, and `ICCProfile`. Compression is `1`
(none), `BitsPerSample=[16,16,16]`, `SampleFormat=[1,1,1]`,
`PhotometricInterpretation=2`, and `PlanarConfiguration=1`.

The manifest binds:

- source ARW path/hash and measured capture/sensor metadata;
- converter ID/version, executable-bundle hash, freeze file/hash, complete
  invocation, cwd, settings and settings hash;
- pattern NPZ path/hash, pattern manifest path/hash, capture match, calibration
  source hashes, and estimator identity;
- output dimensions, structural TIFF values, ICC hash, pixel-payload hash, and
  whole-file hash.

The embedded canonical provenance binds source, converter, settings, ICC, map, and
map-manifest hashes. The Rust verifier requires every one of those bindings as well
as the expected file, payload, and ICC hashes.

## Measured TIFF properties

No production/common-merge TIFF exists, so no production property is marked PASS.
The following measurements establish that the implementation emits the required
representation when given admissible inputs:

| Property | Measured result | Evidence |
|---|---|---|
| 16-bit unsigned RGB | `BitsPerSample=[16,16,16]`, `SampleFormat=[1,1,1]` | `out/commission/identity-baseline.json` |
| Linear transfer | ICC `rTRC=gTRC=bTRC=1.0`; development probe uses `gamma=(1,1)` | `converter-freeze-v1.json`, `settings-v1.json` |
| ProPhoto RGB, D50 | ICC data space `RGB`, PCS `XYZ`; header white `[0.9642028809,1,0.8249053955]`; ROMM matrix tags measured from the profile | `converter-freeze-v1.json` |
| Uncompressed | TIFF `Compression=1` | `out/commission/identity-baseline.json` |
| Interleaved | TIFF `PlanarConfiguration=1` | same |
| Native dimensions | burned RAW active dimensions `7028 x 4688`; in-memory output shape `[4688,7028,3]` | `out/development-raw-probe.json` |
| Development tags stripped | strict allowlist accepts exactly 11 structural tags plus provenance and ICC; an unlisted tag is a tested rejection | `common_tiff.rs`, Rust tests |

The one-frame development probe used only the burned calibration-slide source:

`D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\tilted-sw4-cpl\DSC00031.ARW`

Its independently checked source SHA-256 is
`1b9ad0bac914f017aee35dc36ccec9a69d3f8c8284c604ff9bce0cc9bcd2d38a`.
Measured levels were black `[512,512,512,512]`, white
`[15360,15360,15360,15360]`, and as-shot WB
`[2823,1024,1533,1024]`. The no-map in-memory result was contiguous `uint16`
at `7028 x 4688`, with byte SHA-256
`27dbd01c5fcfd15ebbf89b059faca9e015b6aaea06b75ae30210cbea3c4179cf`.
It is explicitly labelled `DEVELOPMENT_ONLY_NONCONTRACT`, wrote no TIFF, and may
not be scored.

## Strehl byte identity

### What is proven

The commissioned 7 x 5 synthetic TIFF has:

- whole-file SHA-256
  `a0a1e64e353d5f916b537e1454385a2a6ac6bf5513c5553517a62ec918009788`;
- pixel-payload SHA-256
  `17258eb77d5692e323acb659ddc1787b275fabf71cd170e503c5d9cb65c5977b`;
- Rust-decoded internal `u16` SHA-256: the same
  `17258eb77d5692e323acb659ddc1787b275fabf71cd170e503c5d9cb65c5977b`;
- hash reconstructed from the exact `f32` RGB plane allocations passed to
  `BandMerge::add_frame`: the same
  `17258eb77d5692e323acb659ddc1787b275fabf71cd170e503c5d9cb65c5977b`.

`core_merge_exercised=true` proves those hashed allocations were accepted by the
actual Strehl core merge, not merely compared inside a standalone TIFF parser. The
commissioned verifier binary SHA-256 is
`32c22234f3e0f11063de77136c99818825a41e78fe6edb646026a45d3181ada0`.
PowerShell/.NET independently recomputed the whole-file and strip-payload hashes;
all cross-checks pass in `out/independent-hash-audit.json`.

### What is not proven

There is no admissible campaign TIFF. Therefore campaign identity is
**NOT YET TESTABLE**, not `PROVEN`. The adapter is a separately invokable
common-input boundary; the shipping `strehl stack` ARW path remains CFA-specific.
Alignment, RGB noise modelling, and a production RGB-output path still need a
frozen common-track integration before a competitive stack can run.

## Commissioning

`experiments/M165-common-input/out/commission/commission.json` is `PASS`.

| Arm | Measured result |
|---|---|
| Valid baseline | PASS; payload, internal `u16`, pre-merge `f32`, and actual core-ingestion hashes identical. |
| Movable null | Undisturbed correction error `0.0 DN`; planted fixed-pattern disturbance with null correction `7.025 DN` mean absolute error. |
| Planted degradation | Wrong-sign/inverse map increased error to `14.1875 DN`. |
| Planted improvement | Correct map reduced error from `7.025 DN` to `0.0 DN`. |
| Single flipped bit | Bit `0x01` at inert TIFF padding byte offset `172`; payload hash stayed `17258e…`, file hash moved to `6716d1f8c8a74f0ae3003d553136baeff3dbd98f2ee05f000c92638b41c36241`; verifier returned `FAIL`. |
| One-LSB pixel change | First sample `1000 -> 1001` at offset `1312`; payload hash moved to `f229a267899a682ab9b4fffd8533c1429aa893d6f236224ee7d1f5cd43abbd68`, file hash to `55b572cf6c5c0ae8db84ef794717413e679f4e1292efcbe7d1a48172611f91e7`; verifier returned `FAIL`. |
| Repaired input | Restoring the baseline bytes returned `PASS`. |
| Malformed TIFF | Exit `1` with structured `status=FAIL`; no throw escaped. |

## Pattern-map finding and required capture

`out/pattern-map-audit.json` records:

- M71: 250 `.npy` arrays, including 72 per-plane flat means, but zero
  dark/bias/DSNU arrays, zero gain arrays, and zero `.npz` correction maps;
- M2 and M16: zero candidate persisted pattern-map artifacts;
- independent baseline preflight: matching 1.6 s darks/flats `0/0`
  (`SCORECARD-BASELINE.md:23-35`).

Those are useful calibration studies, not the required frozen map. Nothing was
substituted or inferred.

To unblock the measured development source, capture independent darks on the same
physical ILCE-7CM2 body at ISO 100, 1 s, and matched sensor temperature, plus
independent spatially uniform flats at ISO 100, 1 s, f/5.6 with the FE 100 mm F2.8
Macro GM OSS + 2x teleconverter at 200 mm and the same focus/optical geometry.
Capture identity must include a physical body identifier because this ARW exposes no
serial number. Use disjoint estimation and held-out validation blocks, freeze the
map estimator before fitting, and retain every source hash. Each scored stack with
different exposure/ISO/temperature or lens/aperture/focus geometry needs its own
matching calibration or an independently validated interpolation rule. No frame
count is invented here; it must be preregistered from the desired held-out residual
precision.

## Validation and operational status

- `cargo test -p strehl-raw common_tiff -- --nocapture`: **4 passed**.
- `cargo build -p strehl-cli --bin strehl-common-input`: **PASS**.
- `cargo clippy -p strehl-raw --lib --no-deps -- -D warnings`: **PASS**.
- CLI clippy could not reach the new binary because an existing warning in
  `crates/strehl-cli/build.rs:101` is promoted to error; the targeted build passes.
- Python `py_compile`: **PASS** for converter, commissioning, and development probe.
- Missing-map render preflight: expected exit `1`,
  `failure_class=PATTERN_MAP_REQUIRED`, and no TIFF created
  (`out/campaign-preflight.json`).
- Independent hash audit: **PASS**.

**Blocked on compute: NO.** The current blocker is missing calibration photons, not
host capacity. Once an eligible map exists, the full-stack common-TIFF render and
per-frame core identity run will be bulk decode/I/O and must wait for a released
quiet window.

## Residual doubt

1. No real common-merge TIFF or common-input stack exists; campaign byte identity is
   unmeasured.
2. The adapter reaches the actual generic `BandMerge`, but the shipping CLI remains
   a four-plane CFA pipeline. Common-track RGB registration, noise variance, output,
   and directory orchestration are not yet integrated.
3. The ARW does not expose body serial or sensor temperature through the available
   metadata. Future calibration must record physical-body identity and temperature
   independently.
4. No comparator has consumed these fixture bytes. The fixture proves the Strehl
   boundary and verifier sensitivity only.
