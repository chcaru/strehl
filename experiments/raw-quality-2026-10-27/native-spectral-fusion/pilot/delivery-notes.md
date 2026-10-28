# Native CFA final developer

SOURCE-REVIEW PREPARATION. This standalone file is initially unregistered. Root alone registers, builds and executes it; no existing Rust, Cargo or predecessor source is changed. Formatting only has been checked. Numerical parity and photographic quality remain unverified.

## Input and executable contract

`native-cfa-develop <config.json>` accepts exactly one argument. The JSON object rejects unknown keys and has these fields:

- `schema:1`, `cfa:{path,sha256,bytes}`, `width`, `height`, `active_origin_xy:[x,y]`.
- `physical_pattern:"RGGB"`, `units:"black-subtracted-DN"`.
- `development_receipt:{path,sha256,bytes}`, `expected_executable_sha256`, `out_dir`.
- `parity_reference:null` or `{rgb16:{path,sha256,bytes},linear_rgb32:{path,sha256,bytes}}`.

`cfa` is a headerless row-major native HW little-endian f32 field, not four concatenated phase planes, not original u16 codes and not RGB. All values must be finite. Extents8..8192 per axis and at most40M sensels bound memory; odd or even widths/heights are accepted. The active-native origin must be nonnegative, even/even and at most8192 per axis so local RGGB parity agrees exactly with physical parity. Other phase origins are refused, not silently translated. Current actual output is6896x4596 at(68,46). The source image and source-to-reference placement have already been consumed upstream; this developer performs no geometry fitting, source decoding or source resampling.

The development receipt is the existing strict schema1 `levels_bits`, `wb_bits`, `xyz_to_cam_bits`, `tone_bits`, `exposure_bits`, `source_bindings` object used by the commissioned direct RGB developer. Its provenance files are rehashed. Exposure must be exactly1, green WB exactly1, all parameters finite and tone valid. Current held development is `outputs/raw-quality-2026-10-27/direct-cfa-streamed-delivery-controls-2/output/held-development.json` (SHA26a441851ee4344c78d86ef1f8eeb39002acea01ba93b34319c60992e2a9c7c0). No tone or white balance is estimated from the candidate.

## Literal final image path

The signed CFA input is copied bit-exactly to `final-cfa-dn.f32le`. For the final display boundary, preserve the held native multiplication order: `max(CFA,0)*phase_WB*1/(white-black)`. This explicitly preserves the existing negative-CFA clamp; it does not claim signed CFA survives into the display. Actual `strehl_core::demosaic::demosaic_malvar_row` executes once for every row, creating one final MHC stage with the core's parity-preserving reflection at image edges. Its HWC output is saved as `camera-rgb-normalized.f32le`, including signed MHC estimates, before any camera matrix, highlight handling, tone or quantization. This is genuine final camera RGB, not an inversion of a developed image. It is WB/range normalized, not untouched black-subtracted DN.

The same camera field feeds actual `image_out::develop_pixel` and `write_rgb16_described`, and actual `matrix.develop` plus `strehl_edit::save_linear_tiff`. Outputs are `rgb16-master.tiff` and `linear-master.tiff`; the latter is after camera highlight/matrix development and before tone, so it is not an invertible raw-camera field. Both carry the ordinary held DisplayBaseline/ICC metadata. The helper does not run the complete `write_demosaiced_with_master` again: doing so would recompute MHC for each output. Exact held-CFA replay is the qualification of this factored, one-MHC producing path.

All TIFF pixels are read back at the full output shape and hashed against the buffers actually written. Metadata decoding retains a1MiB minimum for ICC even on tiny controls. Signed CFA and camera files are also rehashed after writing. Inputs/configuration/executable and original file size/mtime are checked again after completion. Fresh outputs are required; failed parity saves `parity.json` and `failure.json` with partial masters retained, and exits nonzero.

## Null and output receipt

The held no-op commissioning run passes a headerless copy of the exact retained CA-off CFA payload plus both held master bindings in `parity_reference`. All four required checks are exact: RGB16 pixels, RGB32 pixels, RGB16 material metadata and RGB32 material metadata. A candidate run has `parity_reference:null`; that alone is no null claim. Root must bind a successful held-CFA replay before interpreting candidate outputs.

Successful `receipt.json` has status `COMPLETE_NATIVE_CFA_DEVELOPMENT`, `complete:true`, all file bindings, development, native dimensions/origin, pixel hashes, material metadata, parity result, negative-input/camera counts, `demosaic_stages:1`, actual row-call count, and preservation flags. `RAW_reads:0`, `source_demosaic_calls:0`, `remosaic_calls:0`, `quality_claim:false`, `photographic_admission:false` remain explicit. This delivery receipt does not certify the upstream299 population, spectral operator, runtime feasibility or faithful photograph. Root's producing-job receipt and independent complete-image review supply that evidence.

## Saved-photo presentation

`views.py --candidate-receipt <native receipt> --uniform-receipt <native receipt> --null-receipt <held-CFA native receipt> --out <fresh directory>` requires both actual6896x4596 native outputs at(68,46), the same held development/executable/materials, and the exact held-CFA no-op hashes. It reads no original captures and performs no reconstruction. Root's upstream full-job receipt must separately establish all299 source consumption and clean process completion; this helper deliberately makes no source-count inference from an image.

The helper publishes candidate/uniform complete JPEG98 with no chroma subsampling, orientation-only overviews and the unchanged ten384x384 witness PNGs using `(RGB16+128)//257` and the same ICC. Every PNG is read back and compared exactly. It binds both full RGB16/float/camera/CFA masters, retains held native/HeliconB4/B8 complete outputs and original mapped witnesses, and rehashes all presentation inputs afterward. Status is `COMPLETE_NATIVE_SPECTRAL_VIEWS_READY_NO_VERDICT`; there is no retone, new crop, quality claim or automatic promotion.
