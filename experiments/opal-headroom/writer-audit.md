# Opal current-writer audit before stage execution

Read-only source/receipt audit. No stage-activation or photographic quality
claim is inferred from a code path merely existing. The actual observer run is
specified separately in stage-design.md.

## Where distinctions can disappear

| Stage, in actual order | Verified operation and possible loss | Existing evidence for this opal |
| --- | --- | --- |
| Current pyramid collapse/hull | Band synthesis and final InputRange bounds precede the cache. They can already have mixed away distinctions; a later curve cannot recover them. | cache-1/output/receipt.json binds all155 actual source fields and the complete current collapsed4-plane object, but records no pre/post-hull loss census. |
| Merged value and normalization | merge_cmd::Merged::value clips negative band values to zero. write_merged then applies as-shot WB, explicit exposure gain and division by the noise-model range, with NO upper clamp. Shadow sign loss is possible; this is not an upper highlight cut. | Current cache and production RGB16/ICC identity in cache-1/completion.json; source audit at merge_cmd.rs::value and write_merged. No per-pixel negative-value census yet. |
| Full-context MHC | Signed5x5 stencils can overshoot or change colour even when each merged CFA input is below its own ceiling. The function does not clamp its result. This is a possibility, not an opal diagnosis. | Default MHC is bound by invocation; no existing opal post-MHC stage receipt. The proposed actual-MHC positive control demonstrates possible predicate activation, not photographic causation. |
| Pin protection | Render::clip_highlights tests whether ANY post-MHC camera channel>=its own container/WB/exposure ceiling. If true, ALL three components are capped at the minimum of the three ceilings. This can remove distinctions before the shoulder. The predicate is not an original-RAW clipping census. | Current production uses with_saturation and actual camera metadata. Every four-arm result retains this protection. No opal pin/changed-mask activation receipt exists before stage execution. |
| Sensor chroma rolloff | highlight::desaturate blends camera RGB toward neutral above u=.60, completing at usable white as a fraction of the container. It preserves its chosen luminance but can remove valid chroma before the shoulder; interpolation, merging and actual original clipping are not distinguished by this predicate. | replay-1/output/receipt.json: Current and sensor-rolloff-off TIFF hashes are IDENTICAL; Shoulder and Both hashes are IDENTICAL. This proves zero delivered-pixel effect for the bypass on this complete opal. It does not prove every internal f32 change was zero. |
| Matrix | A linear camera-to-sRGB matrix can place real colour outside the display gamut; by itself it has no clamp or tone shoulder. | Actual matrix f32 bits in the factorial receipt agree across all arms. Source specifies actual Render::develop. No invertibility/colour-fidelity claim is made from this alone. |
| Tone anchor and gain | Tone::from_luminance chooses effective black from p.1*.85 and white from p99.9 mapped to.90, on a subsampled2x2-quad approximation. Tone::gain scales RGB by one luminance-dependent gain and does not hard-cap bright luminance. The full MHC pixels may exceed the sampled white anchor. | Production log prints rounded black−.00017/white.20977/contrast.55; factorial receipt stores the exact tone/exposure bits and verifies identical development across arms. It does not record which pixels exceed display range. |
| Existing fixed shoulder | Located AFTER tone placement/exposure and BEFORE gamut_map. It calls the already commissioned fixed .75 luminance shoulder. Thus it can prevent downstream display clipping, but cannot restore distinctions removed by pin protection, rolloff, MHC or merging. | Four generated controls passed under the executed binary; actual complete Shoulder master and exact shared development in replay-1. Neither is photographic admission. |
| Gamut map | Out-of-range RGB is blended toward neutral luminance clamped to[0,1]. When positive luminance>=1, any channel>1 drives full white. With luminance<1, out-of-gamut chroma can still be reduced. Final component clamp removes residual roundoff. | Source at image_out::gamut_map. Current/Shoulder masters expose the final difference but no existing opal per-stage count locates the lossy event. Stage observer will compare actual post-tone/post-shoulder/post-gamut triples at the same pixels. |
| sRGB, contrast, RGB16 | Actual transfer then per-channel S curve at.55, then16-bit rounding. On[0,1], transfer/S curve are monotone; quantization can collapse small distinctions. These stages are after the proposed shoulder and do not recover earlier losses. | Same actual helpers and ICC are held in all arms; final RGB16 hashes bind their combined result. |

Because the recorded black is negative, for positive luminance the mathematical
Tone::gain expression is capped by its white-point scale rather than by a
highlight ceiling. This is DERIVED from the actual formula and the recorded
sign, not a per-pixel floating-point measurement. It explains why blaming an
earlier tone hard-clamp would target an operation that is not present.

The tone pre-pass samples quads in14-native-pixel steps, as the actual loops
advance by2*TONE_STRIDE. Some older comments describe a seven-pixel stride;
the loop governs. A quad-based percentile and a full-MHC pixel distribution
are different consumers. That mismatch is a possible reason for outliers,
not permission to tune the percentile without a measured defect.

## What is established and what follows

MEASURED by root's completed receipts: all155-source current cache reproduces
the new production RGB16 and ICC; the observer-only factorial does not perturb
whole TIFF bytes; disabling sensor chroma rolloff changes no complete opal
output byte. Shared development is held exactly; the shoulder's existence is
potent on commissioned generated ramps. Photographic admission remains root's
independent decision.

If no fixed arm gives a clear gain, the next action is the read-only actual
stage observer, not another shoulder value. It separates pin-triggered loss,
rolloff, downstream gamut loss and distinctions already missing in the cache.
The frozen two regions and whole-image hashes prevent a new normalization or
regional-tone path from manufacturing a diagnosis. A null pin mask closes
that specific branch. Only demonstrated preclip/postclip loss at the relevant
locations warrants tracing its source headroom; preserved real reflection
structure must never be treated as an artifact merely because it is bright.
