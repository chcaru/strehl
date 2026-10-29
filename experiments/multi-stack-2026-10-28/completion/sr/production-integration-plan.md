# Production integration design for direct original-CFA reconstruction

Status: ARGUED implementation contract, pending the bounded photographic pilot.
Root assigned core/CLI reconstruction integration to the corpus/SR agent; root owns the narrow image_out writer seam. This file does not authorize a full-scene run or
change ordinary stacking. Source storage remains original u16 CFA; reconstruction
arithmetic is f32 and geometry retains the saved full-guide fitting origin.

## Preserve the native white-balanced MHC fallback before display treatment

The production fallback comes directly from completed native fusion. The existing
writer normalizes and white-balances the final CFA, performs one MHC demosaic,
then applies camera-to-BT709/highlight treatment. White balance must remain before
MHC because its cross-color FIR terms do not commute with separate channel gains.
Do not invert the saved developed master in production.

Root's additive writer seam is NativeCameraImage { width,height,pixels,develop }:
pixels are existing normalized-WB MHC RGB, and Develop has tone frozen from the
unchanged native mosaic. prepare_native_camera_image preflights memory then creates
this one final RGB buffer. write_reconstructed_camera_image consumes it for
photograph/master through the same display path, with no second demosaic.

The SR consumer overwrites a pixel only when all three direct original-CFA color
estimates qualify. Candidate camera DN uses the exact existing normalization
expression v*WB*exposure/range. Every unsupported normalized-WB native triple stays
bit-identical; no inverse/reapply round trip is needed. The ordinary writer path
is untouched. Disabled and unavailable-everywhere controls must match complete
native TIFF/master pixels and tone metadata. Core per-channel diagnostics remain
separate from coherent delivered values/variance.

Suggested seam types, owned by core/orchestration rather than the UI:

- NativeCameraTile: full sensor lattice, borrowed signed camera RGB, validity,
  optional propagated variance. Missing variance stays unknown.
- ReconstructionTileInputs: original identities and CFA handles, exact R/G/B
  pulls, injected plane noise/gain, frozen guide halo, local focus/motion and
  per-color registration support.
- ReconstructionTileResult: camera RGB, per-channel source/reconstruction status,
  conditional variance-valid flags and diagnostics. A physical-coordinate lattice
  accompanies every tile; cropping does not recenter its transforms.

For a finer output grid, sample the native camera-RGB fallback onto that grid
once using an explicit tested display/output resampler. That fallback is labelled
upsampled native support. Candidate pixels remain direct original-CFA estimates;
there is no gather-then-resize candidate and no second demosaic. Output dimensions
alone are never a resolution claim.

## Obtain a useful local source set without weakening the focus gate

The initial148-152/437-441 central arm was photographically rejected, and full-track
focus placed its real modes near74/69. Off-center three-region census selected
left-elytron globals107-113/397-403, guides106/114/396/404. ROI04 replaced2265/36864
pixels coherently without the earlier purple pits; independent review found no
new recognizable resolved structure. This is an artifact-control checkpoint,
not a demonstrated quality gain. Local heldout registration and prediction, then
an affine/MHC causal comparison, remain necessary. No focus/phase gate was lowered.

For general tiles, take the union of original acquisition neighborhoods supported
by the full per-pass focus evidence. Bound it before loading. Keep acquisition
order, uncertainty, modes and missing coverage; filename order is not a focus
measurement. A tile crossing many depths may need subdivision to keep its union
within MAX_SOURCES. If even the minimum useful tile cannot fit, retain native
there and report the reason. Never silently discard a competing depth layer.

A frozen guide may use withheld acquisitions. When the ordinary focus/motion
prepass shares target photons, reported variance remains conditional on those
fixed decisions; the independent-guide control does not eliminate selection bias.
The current target-position shot-variance approximation must eventually become
a frozen guide-halo lookup at each original sample's anchor position, or remain
explicitly labelled and bounded around colored edges.

## Local geometric certificate before full rendering

Use the direct local graph and held-out original-patch procedure in
local-registration-plan.md. A saved global map, an edge RMS and an assumed0.10
sensor bound are insufficient. Record actual displacement residuals in the full
anchor sensor gauge, directional conditioning, cycles and refusal reasons.
Per-color support includes optical-profile uncertainty; a green measurement is
not an RGB certificate. Train and score disjoint patches, exercise wrong-map and
aperture-problem negatives, and score the actual consuming placements.

Keep the candidate behind this certificate for full-scene work. The diagnostic
assumption remains useful only to inspect operator behavior and locate a real
usable region. A measured improvement in the full image is also insufficient to
establish placement improvement without the coordinate-level witness.

## Bounded full-scene scheduling

Do not rerun all598 sources for every tiny tile: the initial ROI's streaming
focus pass is a diagnostic convenience and would multiply cache I/O disastrously
across a complete photograph. Compute full per-pass focus evidence once (or
reuse the exact bound shared focus export) and write its bounded confidence/mode
maps outside captures. These are confidence maps, not aligned pixel volumes.
Reuse the ordinary native fusion and original-CFA cache.

Retain the native fused CFA/result needed by the writer and process reconstruction
in bounded output tiles. With a256x64 tile, MAX_SOURCES64 and current accounting,
operator/output/borrowed confidence storage is approximately15MiB; 16 such tiles
reserve roughly240MiB, not a full-frame diagnostic volume. Actual checked
memory_estimate values remain authoritative. The original cache is separate:
one 7032x4688 active u16 frame is about62.9MiB, so64 originals require about4GiB.
Overlapping tile jobs share Arc-backed original frames. Reserve the union of
pinned identities before dispatch; cap concurrency if it cannot fit. A8GiB
original cache plus explicit native/focus/output reservations is plausible on
this64GiB host, but the measured reservation and peak govern the final setting.

Write diagnostics tile-by-tile or aggregate their counts. Do not allocate the
current73-byte/pixel TileResult over the whole32MP image (over2GiB) merely to
make a report. Native fallback RGB for a tile is generated with its demosaic
plugin halo, then released. Preserve fixed per-pixel source order for deterministic
CPU tiles; scalar/parallel RGB, variance and diagnostics must remain bit-identical.

Measure before optimizing further. Safe exact CPU opportunities are precomputing
per-source/color inverse pulls and scale, hoisting four predicted plane variances
per source/pixel, and iterating only the matching CFA parity while retaining sample
order. The current independent-tile parallelism is the first benchmark. GPU work
can consume bounded packed original-u16 patches with their true full sensor origin
and one pixel/color work item looping sources in order; shader precision and
phase/clip support require independent controls before deployment. No GPU path
may reconstruct a full aligned-frame volume.

## Full photograph and UI outcome

After one useful measured region, render the same complete photograph with native
fallback everywhere the local reconstruction is unsupported. Keep the float master,
source/map/profile/guide identities, resource receipt, reconstructed support maps
and identical display transform. Review complete outputs and native crops; colored
alias truth, optical-lowpass nulls and temporal variance controls remain separate
from photographic evidence. Sparse candidate support or a fully native result is
reported honestly, but is not the desired useful-region milestone.

The UI should expose an optional reconstruction outcome and output sampling size,
with a visible support preview and ordinary stacking as the default. It should
explain when a region uses native fallback and show a finished full photograph,
not require the user to assemble crops or understand internal kernel parameters.
