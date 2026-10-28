# Genuine normalized-camera delivery and saved-field presentation

2026-10-27. **SOURCE PREPARATION ONLY / UNVERIFIED AT RUNTIME.** Root alone
registers, builds and runs this new example after the active full299 job ends.
No existing Rust, Cargo, spectral-pilot source, RAW file or saved field is edited.
The [brief](brief.md) and [photographic constraints](../prior-photo-constraints.md)
remain binding. This is not a quality claim or a second source-fusion run.

## New native writer

[normalized-camera-develop.rs](normalized-camera-develop.rs) is an unregistered
standalone example. Its executable accepts exactly one configuration JSON path.
Each file binding is exactly `{path, sha256, bytes}`; all config/development
structs reject unknown fields. The config is:

```json
{
  "schema": 1,
  "camera_rgb": {"path": "ABSOLUTE", "sha256": "HEX", "bytes": 380328192},
  "source_receipt": {"path": "ABSOLUTE", "sha256": "HEX", "bytes": 1},
  "width": 6896,
  "height": 4596,
  "active_origin_xy": [68, 46],
  "units": "normalized-camera-RGB",
  "development_receipt": {"path": "ABSOLUTE", "sha256": "HEX", "bytes": 1},
  "out_dir": "FRESH_ABSOLUTE_DIRECTORY",
  "expected_executable_sha256": "HEX",
  "parity_reference": null
}
```

The placeholder receipt sizes above must be replaced by actual bindings.
`parity_reference` may instead contain `rgb16` and `linear_rgb32` file bindings.
Supported extents are 4..8192 on each axis and at most 40 million pixels; input
is exactly `width*height*3*4` bytes of finite little-endian HWC f32. Origin is
recorded in active-native pixels. RGB has no phase relabeling operation.

Input is the **actual already-WB-applied, sensor-range-normalized camera field**
produced by either the held MHC or the new completion. The writer makes an exact
signed/above-one copy, then applies only the held native matrix/highlight/tone
path. It performs no WB/range conversion, input clamp, MHC, remosaic or other
completion. Level/WB metadata still configures the existing matrix's saturation
and highlight behavior; that common development is not bypassed. The input
camera field is saved before it. The float TIFF is the actual matrix/highlight
output before tone, not an invertible camera field or an optical truth.

Outputs are `camera-rgb-normalized.f32le`, `rgb16-master.tiff`,
`linear-master.tiff`, `receipt.json`, and `parity.json` when requested. Full TIFF
readback checks dimensions/type/single-page/finiteness/pixel hashes and records
ICC, description and material tags. TIFF decoder metadata allowance is at least
1MiB even for tiny controls. Actual native functions and the pinned development
bits are reused without arithmetic changes. Four Rayon workers are fixed.

Receipt status is `COMPLETE_NORMALIZED_CAMERA_NATIVE_DEVELOPMENT`; key bindings
are `input_camera_rgb`, `source_receipt`, `camera_rgb`, `rgb16`, `linear_rgb32`,
`configuration`, `executable`, and `development_receipt`. It records
`writer_completion_stages=0`, `writer_demosaic_calls=0`,
`normalization_applied=false`, `input_clamp_applied=false`, exact signed camera
copy/readback, negative/above-one counts and preserved input bytes/metadata.
The source receipt is writer-agnostic: the writer never invents an upstream
completion count. Claims and photographic admission remain false.

## Required exact held-camera null

Use the actual camera file from
`outputs/raw-quality-2026-10-27/native-spectral-null-1/output/receipt.json`:
SHA `42429be10904e1c81a95e83fc0d1fed22a1ced1eb211c9d449a20cb0cef2a7cf`.
Its actual MHC receipt binds the signed held CFA SHA
`1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0`.
Pass that receipt as `source_receipt` and request parity with the held CA-off
RGB16 and float masters. RGB16 pixels, float pixels and both material records
must be exact. This is a genuine supplied-camera replay, not an inverse-normalized
surrogate or a copied baseline masquerading as new rendering.

## Saved-field driver

[saved-field.py](saved-field.py) imports only standard-library modules at module
load. The independent controls can reuse:

```python
develop_camera(camera_path=..., width=..., height=..., active_origin_xy=...,
               source_receipt=..., development_receipt=...,
               renderer_binding=..., out_dir=..., parity_reference=None)
```

All arguments after the function name are keyword-only. Renderer binding is a
JSON containing exactly `{path,sha256,bytes}` for the new executable. The helper
returns the native receipt file binding and preserves a sibling config, stdout,
stderr and direct-process record. It inherits root's job boundary; it creates
no independent scheduling or GPU work. It verifies the actual normalized-writer
receipt, source/executable identity, output hashes and input preservation.

The full saved-field CLI is:

```text
python -X faulthandler saved-field.py --input-receipt <ordinary-MHC-native-receipt> --renderer-binding <new-executable.json> --null-receipt <exact-normalized-writer-null> --expected-completion-sha <frozen-SHA> --out <fresh>
```

It accepts one exact complete6896x4596 field at origin68,46. It binds the actual
MHC CFA/camera/masters/development, requires the new writer's exact held null,
copies the signed CFA, and calls the fixed spectral operator once with the same
held normalization. It saves actual normalized CFA and genuine HWC camera,
producer evidence/runtime metadata, then invokes the writer. Before native
delivery it applies the independently frozen pre-restoration bar per color:
max error <=3e-6*max(1, known-color reference maxabs), RMS <=6e-7*max(1,
known-color reference RMS), in normalized-camera units. This uses the actual
normalized CFA sites before restoration, never the overwritten exact null.
Failure saves the finite camera/CFA and diagnostic but blocks native delivery. CUDA arithmetic
and FFT are the author's operator; this driver adds no estimator or retone.
All operator-reported source dependencies are included in the before/after
manifest. Torch fixes four intra-op and one inter-op worker before GPU work.
External synchronized `perf_counter` records full completion time; the full
worker time includes copies, hashes, native writer and readback. Root separately
owns process limits, practical-cost decisions and upstream299 qualification.

Driver receipt status is `COMPLETE_SAVED_FINAL_CFA_COLOR`; `native` binds its
own native receipt, `mhc_reference` the paired unchanged MHC result, `completion`
the actual operator record. Failures preserve partial files and return nonzero.
No missing/failed arm is replaced by a baseline.

## Complete presentation

[views.py](views.py) requires `--held-receipt`, `--candidate-receipt`,
`--uniform-receipt` (three saved-field driver receipts), `--null-receipt`, and
`--out`. The held receipt is the complete full-shape cost output on the exact
held baseline CFA. Its MHC source must be the same actual receipt that supplied
the commissioned null, with the pinned held CFA/camera and RGB16/float pixel
hashes. An arbitrary third field cannot qualify. It verifies all chains, source
field identity, same development/materials and exact null before publishing six
arms: `held-mhc`, `held-color`, `candidate-mhc`, `candidate-color`, `uniform-mhc`,
`uniform-color`. The held pair isolates final color completion on the current
native baseline, independent of the new upstream fusion; the other two pairs
retain their respective fused CFA inputs. Each has a complete JPEG98/subsampling0 with the original ICC,
an orientation-only overview, and all ten frozen native384 PNG witnesses.
Conversion is exactly `(RGB16+128)//257`; no cropped pixel is resized, retuned or
reselected. Every PNG pixel/ICC and full RGB16 pixel hash is checked. Float,
camera and signed CFA masters are linked, not reconstructed from display data.

`views.json` status is `COMPLETE_FINAL_CFA_COLOR_VIEWS_READY_NO_VERDICT` and
`index.md` links all six whole photographs/masters before the sixty witnesses,
plus retained native CA-off and HeliconB4/B8 comparisons with their different
alignment/RGB-before-fusion gauge disclosed. Root verifies terminal source
population/process authority; a delivered image alone does not prove299 inputs.
Review whole photographs first. No synthetic pass, quieter color texture or
restored known-site identity establishes genuine inferred-color fidelity.

## Source checks

New Rust formatting uses `rustfmt --edition 2024 --config skip_children=true`.
The existing `image_out.rs` hash was checked before and after and remained
`ecb0483fce9639f364e9fcb44a85067f8e599bd7aedf94019b276db492ef2e1f`.
Python validation is AST parsing only. No author build, module import, tensor
execution, RAW read or image export qualifies these new sources.
