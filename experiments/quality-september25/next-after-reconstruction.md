# Next different route: illuminant-aware RAW color development

2026-09-25. **ARGUED recommendation; no new image, RAW read, build or quality
measurement.** After the current reconstruction observation, implement one
bounded illuminant-aware camera-to-display transform. This can improve color
separation in the newer warm-light mineral/marigold captures. It cannot repair
spatially duplicated hairs or turn a real reflection into diffuse detail.

The concrete gap is in current code: `Frame::xyz_to_cam_rgb_with_source`
prefers D65, while `color::camera_to_srgb` row-normalizes that daylight matrix
and relies on camera-channel WB for adaptation. `color.rs` explicitly records
the missing illuminant interpolation and XYZ adaptation. The earlier
`green-match-rgb/colour-path-audit.md` found no duplicate WB, but no validation
under the documented 3000 K light either. Its Sony preview was also blue/cyan,
so **a Strehl-only global cast was not established**. This recommendation
addresses a documented approximation exposed by changed capture conditions,
not a proven attribution of the owner's color or glare complaints.

## One recommended implementation and its cheap decision

At the existing final `write_merged`/`image_out` color-matrix seam, derive the
shot white from the retained as-shot camera neutral and available decoder
calibrations; interpolate valid warm/daylight matrices and apply a proper
shot-white-to-display-white adaptation. Fold the inverse of the already
applied WB diagonal into the final matrix: do not white-balance a second time.
Keep CFA merge, MHC, exposure, sensor ceilings, resolved tone and gamut mapping
fixed. Cache metadata must bind the calibration inputs, chosen white and final
matrix. Read the decoder's exposed data only; do not inspect its source.
Actual availability of a second usable matrix on these files is **unverified**;
absence should stop this dual-calibration arm, not manufacture a camera profile.

The primary specification is Adobe's [DNG 1.7.1, pages 100–103](https://helpx.adobe.com/content/dam/help/en/camera-raw/digital-negative/jcr_content/root/content/flex/items/position/position-par/download_section_733958301/download-1/DNG_Spec_1_7_1_0.pdf):
dual calibration interpolates in inverse correlated color temperature;
camera-neutral inversion and the no-ForwardMatrix XYZ adaptation path are
specified separately. Use those equations, not external implementation code.
ARW decoder matrix conventions and normalization must be checked explicitly
before applying this model; being a 3x3 array does not establish DNG semantics.

The small adversarial test is a fixed independently calculated warm/daylight
pair of non-diagonal camera matrices with known off-neutral XYZ patches,
including colored bright gradients and a neutral ramp. Compare actual writer
RGB against a separate f64 transform oracle. A wrong illuminant, transposed
matrix and double-WB mutant must fail on off-neutral patches; a neutral-only
test would be powerless. Add a flat/noise input and true adjacent color edges
to detect amplified chroma/error and hue inversions. This commissions arithmetic,
not Sony spectral calibration; do not generate truth by inverting the candidate.

If the needed calibration data and these controls are sound, replay the saved
complete opal103 and marigold4 CFA caches through exactly one new matrix with
baseline tone pinned. This is a writer-only full-image comparison, no new stack
merge. Require a visible useful color/gradation change with retained real pink,
green/blue play and yellow/petal texture at the existing targets; reject a merely
more saturated rendition or worse fringes. Show complete before/after images
and native masters. Without a physical color reference, report a photographic
tradeoff and the standards correction, not measured absolute color accuracy.

## Why this is not the already rejected work

M85 established matrix orientation/output space, not warm-light accuracy.
M95-CDIFF and September14's quincunx/coherent-green/published residual
interpolation variants lost real color/detail; the joint CFA inverse and
backprojection added stipple/noise. None tested this illuminant transform.
Opal's completed shoulder/rolloff factorial found no useful photographic gain;
the actual writer observer found pin/rolloff inactive. Changing those thresholds
again is excluded. This proposal also leaves rejected source weights, depth
Potts, local blur, signed-black and optical-support rules closed.

## One fallback: transfer the existing photometric correction carefully

If usable warm calibration is absent or the full writer pair is unhelpful,
the fallback is **one gain-only photometric-normalization arm in the native
BandWorker**, using existing `Flux`, fixed-reference `low_detail_mask` and
`PhotometricMap`, with unity exact. Apply the gain to consumed f32 radiance and
its existing injected/probed variance by gain squared; retain u16 originals.
No offset, per-band strength, geometric `1/a²` gain or new selector is proposed.
The current native pyramid explicitly omits this existing legacy facility.
The real through-focus traces show shared late brightening, but do not establish
illumination drift; that is motivation to test, not permission to normalize it.

M91's uniformity tests failed and its correction harmed some stacks; M99 rejected
the scale law and whole-frame gain for background seams; M125's legacy
background-seam result is not native-pyramid photographic qualification. First
use one actual-consumer generated pair with prescribed multiplicative drift and
its identical pure-defocus/no-drift twin, plus a spatially varying illumination
adversary. Require real seam reduction in the drift case and preserved texture,
color and flat noise; the no-drift twin must not be normalized into a gain.
Refuse the scalar model when disjoint fixed source regions disagree. Only then
consider one held-map complete marigold pair. Do not port the old auto threshold
or fund another drift-estimation campaign if these small falsifiers fail.

Read first: current `2026-09-quality-path.md`, September25 pipeline/mineral/
marigold reviews, the named closures, and relevant SYNTHESIS architecture and
color records. Mechanical searches run with `prior_art.py`: `demosaic CFA
chroma interpolation`; `photometric radiance exposure white-balance illuminant`;
`highlight reconstruction censored clipping`. No restricted source was opened.
