# Actual product baseline fixture schema

Source preparation only. Root registers `baseline-bridge.rs` as a child of
`merge_cmd` named `joint_cfa_band_residual_baseline`. The sole ignored entry is
`merge_cmd::joint_cfa_band_residual_baseline::actual_product_fixture_baseline`.
It reads `STREHL_JOINT_CFA_BASELINE_CONFIG`; no environment is mutated by the test.
Root builds/runs it separately from Python fixture generation and fitting.
Registration requires the existing `native-direct-planes` and
`native-gpu-gather` feature APIs, with both routes disabled at runtime as below.

Config, with absolute paths and no additional fields:

```json
{
  "schema": 1,
  "fixture_manifest": "C:/.../fixtures.json",
  "fixture_manifest_sha256": "64 lowercase hex characters",
  "out_dir": "C:/.../fresh-output",
  "expected_test_executable_sha256": "64 lowercase hex characters"
}
```

Manifest, one to32 cases and one to7 sources per case:

```json
{
  "schema": 1,
  "cases": [{
    "id": "flat-neutral",
    "width": 128,
    "height": 128,
    "black": 512,
    "white": 15360,
    "wb_rgb": [2, 1, 1.5],
    "iso": 100,
    "source_to_reference_center": [64, 64],
    "noise": {
      "phase_order": ["R", "G1", "G2", "B"],
      "gain_dn_per_e4": [0.15, 0.13, 0.17, 0.21],
      "read_noise_e4": [20, 21.7571317, 19.5095576, 17.1692918]
    },
    "sources": [{
      "source_id": 0,
      "path": "C:/.../source-0.u16le",
      "sha256": "64 lowercase hex characters",
      "bytes": 32768,
      "source_to_reference": [1, 0, 0, 0]
    }]
  }]
}
```

The read-noise values above illustrate the schema; the manifest supplies the
author's actual frozen values, not rounded values copied from this example.
Each file is exactly128x128 row-major little-endian u16 active CFA, integer
physical pixel centres, RGGB at origin(0,0), no header, padding or hidden crop.
IDs are unique within a case. Literal duplicate arrays may have separate IDs
for a declared duplicate control; that does not establish independent noise.

`source_to_reference=[a_re,a_im,tx,ty]` means complex multiplication a about
native centre(64,64), then translation(tx,ty) in native pixels. The bridge uses
the exact inverse, then divides its translation by2 for the actual quad-domain
reference-to-source pull about(32,32). Every phase's crop corners are recorded
and round-tripped. It never fits geometry or changes the fixture transforms.

The single injected model is the exact f32 `NoiseModel` represented by the
gain/read coefficients. Its variance is
`gain*max(signal_dn,0)+(gain*read_noise_e)^2`, with no PRNU or added1/12.
Core storage order is R,G1,B,G2; the bridge explicitly permutes the manifest's
physical order R,G1,G2,B. Acquisition rounding may add quantization error;
that is a disclosed limitation, not a separately fitted noise model.
Receipts expose the consumed f32 gain/read coefficients and bits plus the actual
read-variance values/bits. The candidate derives its read variance from that
same f32 product, rather than substituting ideal decimal variance constants.

Root-selected baseline output is the complete **96x96 actual consumer crop**,
native origin(16,16), quad crop(8,8,48,48). Each original source must cover every
Catmull stencil in that crop. It is not padded/resized to128. Compare precisely
against candidate reference cells `[16:112,16:112]`; retain the candidate's
complete128x128 and144x144 latent field separately. The baseline's actual ladder
is48,24,12: two AC bands plus base, versus the candidate's six Haar levels per
64x64 source phase. This is a product comparison, not an isolated basis swap.
The final baseline MHC reflects at its96 output boundary; the scored candidate96
is interior to its128 output. Source-gather support does not erase this boundary
operator difference. Preserve that limitation in interpretation.

Per-case output files are `camera-rgb-dn.f32le`,
`camera-rgb-normalized.f32le` (HWC96x96x3), `cfa-planes.f32le`
(physical R,G1,G2,B, each48x48), and `source0-camera-rgb-dn.f32le`.
The normalized output is the actual existing camera-RGB/MHC rendering helper,
including its nonnegative sensor normalization and WB. Camera DN is that result
times `(white-black)` divided by relative WB, per channel, with no subsequent
clamp. No CCM, exposure, tone curve, ICC encoding or export quantization is
applied. Independent controls own the common display; this is not the full TIFF
writer and its differences must remain visible in comparisons.

Each case receipt binds original bytes before/after, supplied and converted
maps, physical offsets, full-active warp coverage and fully covered crop,
actual gathered-plane parity, one-source InputRange exactness, actual measured
beta values, effective levels/exponents, defaults, output hashes and units.
`receipt.json` has status `COMPLETE_ACTUAL_PRODUCT_BASELINES`, mechanical_pass,
case_count, `cases:[{case_id,receipt:{path,sha256,bytes}}]`, original_inputs_unchanged, RAW_reads:0,
admission:false and quality_claim:false. No automatic quality decision follows.

Required frozen runtime:4 Rayon workers; ALIGN=1, FULLRES_GATHER=1,
DIRECT_PLANES=off, GPU_GATHER=off, FIX_CA=off, DEFECT=off,
TEMPORAL_ENERGY=off, SPATIAL_NOISE_FLOOR=off, DEMOSAIC=malvar,
PROBE_GATHER=green and WARP_WRITEBACK=parallel (all STREHL-prefixed except
RAYON_NUM_THREADS). Leave STREHL_GATE_FLOOR unset for actual measured defaults.
No source registration or execution is authorized by this schema alone.
