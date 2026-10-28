# Actual baseline bridge: independent source review

2026-10-27. **VERIFIED source inspection; numerical behavior UNVERIFIED.** No
fixture import, RAW read, build, registration or numerical job was performed.
Reviewed `baseline-bridge.rs` SHA256
`42e241f4a5b2e8626a1c2d060a4db32a7f2f16361d27f9d6e28de3197e8e270b`
and `fixture-schema.md` SHA256
`fa19940474f8eecb1bbe323f1965043ee25098340b4def01545fa02b5e7abf68`.
These are source checkpoints, not assumed final author freezes.

## Findings

The producing route is the actual `BandWorker::fold` and merge, followed by
`phase_packed_rgb::camera_rgb`, not a Python approximation. It preserves original
128x128 little-endian u16 arrays, active origin(0,0), and verifies file/hash/stat
and in-memory original bytes after processing. A separate call to the same
production warp/extraction must reproduce each fold's four planes bitwise;
the actual one-source InputRange collapse must equal the held gathered planes.
These checks do not bypass the gather or assert identity against unwarped RAW.

The map direction and units are correct by algebra: invert the supplied
source-to-reference complex similarity about native centre(64,64), halve its
translation for a quad pull about(32,32), then evaluate each physical CFA
offset. This yields the same native inverse. All four corner/phase round trips
are checked; the actual full-source Catmull support check covers the fixed
96x96 output. The original seven-source order is retained, no alignment is fit,
and every source must be placed and folded. Unsupported source stencils refuse;
there is no fabricated source padding or resized baseline.

Physical R,G1,G2,B planes follow `BAND_PLANE_OFFSETS` exactly. The noise model
explicitly permutes these to core R,G1,B,G2 slots with `[0,1,3,2]`; no extra
quantization variance or PRNU is introduced. The generated model is honestly
identified as synthetic despite using the production `Measured` enum.

**One comparison binding must be closed before numerical comparison:** the
manifest's gain and read-electron coefficients are parsed as f32, and product
`PlaneNoise::variance` computes `read_dn=read_e*gain`, then `read_dn*read_dn` in
f32. Passing the ideal generator READ constants directly as candidate `read4`
does not guarantee identical consumed coefficients. The control must derive
candidate read variance by those same two f32 operations from the manifest,
and assert the bridge's recorded gain/read-variance bits. This does not require
changing the generating noise draw, adding1/12, or changing either algorithm.
The bridge author and independent control author were notified before runs.

The returned DN image has the correct camera-RGB signal units for comparison:
actual MHC result after per-channel relative WB/normalization, multiplied by
sensor range and divided by the same relative WB. This does **not** undo
cross-channel MHC errors or the upstream sensor clamp/quantization; it is the
actual product estimate expressed back in camera DN. The candidate delivers
reference-cell integrals directly. MHC's interpolation of already integrated
sensels is therefore a comparator representation difference, not an additional
integration that the bridge should silently add or remove. No CCM, tone, ICC
or full TIFF writer is being claimed.

## Required interpretation limits

- Compare baseline96x96 origin(16,16) only with candidate `[16:112,16:112]`;
  retain the complete128x128 candidate and144x144 latent separately. The bridge
  neither reconstructs nor validates a complete128x128 product output.
- Actual final MHC reflects at the **96x96 output crop boundary**. This remains
  true even though all source Catmull stencils are supported. The candidate's
  compared region is interior to its128x128 output, so outer baseline pixels do
  not share identical reconstruction context. Keep this confound explicit;
  do not redefine support or move score windows after seeing results.
- The actual baseline ladder is48,24,12, with two AC bands and base; the
  original-phase candidate has six Haar levels on64x64 phases. A product
  comparison is useful, but cannot isolate the basis or prove a full-image
  seven-versus-seven advantage.
- The bridge folds seven small sources as one arithmetic chunk and records
  that choice. It is a real consumer comparison, not byte reproduction of a
  multiworker complete-photo accumulation. The root runner must verify its
  actual recorded Rayon worker count and frozen executable/runtime bindings.

No source blocker was found in the map, phase, crop, actual gather, hull or
camera-DN conversion. The consumed-noise coefficient equality above remains a
concrete pre-run contract requirement. No mechanical pass, image-quality gain
or native-RAW-contract compliance is inferred from this source review; the
baseline explicitly remains MHC/Catmull/remosaiced CFA.
