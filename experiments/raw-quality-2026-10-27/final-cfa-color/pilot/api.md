# Fixed final completion API

Source-only, 2026-10-27. Import `spectral-completion.py` by absolute location.
Import uses only the Python standard library and performs no CUDA/numerical work.
Root alone schedules construction, controls, costs and complete photographs.

```python
SpectralCompletion(torch, device_limit_bytes=8 << 30)

engine.normalize_cfa(cfa_dn, development, physical_origin_xy=(0, 0))
# -> contiguous CUDA0 float32[H,W], native held normalization only.

engine.complete(cfa_dn, development, physical_origin_xy=(0, 0),
                diagnostic_foil=None) -> Completion
# cfa_dn: contiguous finite CUDA0 float32[H,W], black-subtracted signed DN.
# development: held schema1 dict with levels_bits[2], wb_bits[3], exposure_bits.
# Exact WBgreen=1 and exposure=1 required, as in the held native writer.

engine.complete_normalized(normalized_cfa, physical_origin_xy=(0, 0),
                           diagnostic_foil=None) -> Completion
# Same producing completion, no normalization/clamp. Finite signed fields allowed.

Completion.camera_rgb       # contiguous CUDA0 float32[H,W,3], normalized camera RGB
Completion.normalized_cfa   # actual CUDA0 float32[H,W] input to the completion
Completion.pre_restore_rgb # CUDA0 float32 HWC when H*W<=16384; otherwise None
Completion.evidence        # JSON-serializable dict; does not contain tensor data

engine.mask(height, width, color, diagnostic_foil=None)
# Actual producing f32 CUDA0 rFFT multiplier [2(H-1), W], color 'R','G','B'.
# Boundary decisions are integer comparisons. This method is for commissioning;
# normal execution calls it internally once per color and releases each mask.

engine.metadata(strict=True) -> dict
source_dependencies() -> list[Path]
normalization_spec(development) -> dict
```

Physical origin is `(x,y)` in original native sensor coordinates; all four
parities are accepted. The final field is unwarped, so only this origin's parity
enters site classification. H,W>=4, each<=16384 and H*W<=40,000,000. There is no
automatic crop, padding-to-fast-size, tiled fallback or precision switch.
All caller tensors must have `requires_grad=False`; autocast is refused.

Only diagnostic foils `None`, `green-square`, `swap-rb`, `double-gain` exist.
They follow the producing extension/FFT/mask/inverse/restore path. Green-square
substitutes the DC-matched half-square multiplier, `0.5*s(fx)*s(fy)`, only for
green. Swap-RB changes the selected source-color sites while physical known-site
restoration still uses the real requested color. Double-gain doubles all masks.
No foil is a production recipe or an automatic fallback.

`evidence.pre_restore` is a dict keyed R/G/B. Each entry contains `count`,
`max_abs`, `rms` in normalized-camera units. The comparison is made before any
known-site overwrite; the returned small `pre_restore_rgb` permits an independent
full missing-site oracle. `known_sites_restored_bit_exact` checks all physical
known sites after restoration. Neither field claims missing-color fidelity.

Other stable evidence fields: `schema=1`,
`status='COMPLETE_FINAL_CFA_SPECTRAL_COMPLETION'`, `complete=true`, `height`,
`width`, `extension_hw`, `physical_origin_xy`, `camera_layout='HWC'`,
`camera_units='normalized-camera-RGB'`, `final_color_completion_calls=1`,
`source_demosaic_calls=0`, `MHC_calls=0`, `remosaic_calls=0`, `RAW_reads=0`,
`quality_claim=false`, `photographic_admission=false`, `diagnostic_foil`,
`channel_seconds`, `total_seconds`, `memory`. `complete` additionally records
`normalization` with actual f32 bits/order and `negative_input_samples`.

The producer does not write files or invoke a renderer. The driver must preserve
and bind the original signed CFA, save the actual normalized CFA and genuine
camera RGB as little-endian f32, save evidence plus strict runtime metadata,
then pass the camera field to the new normalized-camera native writer. The
writer applies no WB, range division, clamp or completion again. It consumes the
held development for matrix/highlight/tone/ICC exactly once. Source/input byte
preservation is the driver's before/after binding obligation. Tensor mutation
counter checks are supplementary and report null for inference-mode tensors
which intentionally have no such counter.

The constructor compiles three small kernels with our hash-pinned ordered-FIR
NVRTC runtime, privately composing the CUDA source without editing that helper.
The scientific transform is ordinary Torch real FFT/complex64 plus its fixed
real mask. `source_dependencies()` returns this source and the frozen runtime
helper; the caller also binds its driver, controls, notes and native writer.

Memory fields give current/peak Torch allocations and reservations under the
requested allocator cap. Driver/module and FFT plan memory outside that
allocator must be included by root's process/device observation. Metadata also
retains compiler/driver/DLL/PTX source hashes, options and library rechecks from
the pinned runtime. No timing or memory result exists until root runs the exact
complete image shape.
