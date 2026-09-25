# September 25 pipeline and provenance audit

Read-only source/provenance review by a worker separate from the renderer and
the unfinished coherent-estimator author. No build, test, RAW decode, original
capture edit, or photographic judgment was performed in this audit. The
renderer logs, invocation records, delivery manifests and relevant local source
were read. `AGENTS.md`, the synthesis architecture and camera/profile decisions
were read. No external implementation or restricted source was opened.

## What produced the user's new outputs

**VERIFIED:** all nine base invocations name the same retained executable:
`experiments/native-gpu-gather/build-native-6/strehl.exe`, 17,714,688 bytes,
SHA256 `2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7`.
This file was independently hashed during this audit and agrees. Render logs
identify build `36b91f0e5ced`. The interrupted September 20 candidate was not
used to produce these images.

All base runs use original RAW input, full-resolution rounded GPU gathering,
green-only noise probe, Catmull-Rom, device GPU scheduling, eight threads,
seven-band SoftPower pyramid, gate 2, exponent 2, octave exponent ramp 1.4,
plain-mean terminal band, full-resolution demosaic, sRGB RGB16, and native-pitch
common-coverage crop. The `--pyramid-sharpen` value controls selection exponents;
it is not a post-render sharpening filter. All resolved render banners confirm
the composed `a7c2-fe100gm-2xtc-x4cpl` optical correction, ISO 100 and levels
512/15360. Rawler's unknown-lens warning does not establish missing correction.

The actual pyramid banner says that photometric gain, clipping census, outlier
rejection, occlusion-halo correction and through-focus statistics are **not
applied**. These exist on the separate legacy estimator path; their presence in
the repository does not mean the user's outputs benefit from them. This is
established configuration, not evidence that enabling any old stage is safe.

| Stack | Frames / reference | Native output | Quad crop x,y,w,h | Held-out diagnostic |
|---|---|---|---|---|
| Marigold 1 | 292 / 146 | 6228 x 4152 | 201,134,3114,2076 | unavailable |
| Marigold 2 | 433 / 216 | 6212 x 4140 | 205,137,3106,2070 | 3.2731 |
| Marigold 3 | 339 / 169 | 6268 x 4176 | 191,128,3134,2088 | unavailable |
| Marigold 4 | 488 / 244 | 6268 x 4176 | 191,128,3134,2088 | 4.0590 |
| Mineral 103 | 155 / 77 | 6792 x 4528 | 60,40,3396,2264 | unavailable |
| Mineral 104 | 183 / 91 | 6524 x 4348 | 127,85,3262,2174 | unavailable |
| Mineral 105 | 228 / 114 | 6760 x 4508 | 68,45,3380,2254 | 3.5712 |
| Peacock 100 | 207 / 103 | 6702 x 4468 | 83,55,3351,2234 | 5.2873 |
| Peacock 102 | 216 / 108 | 6694 x 4462 | 85,57,3347,2231 | 4.0913 |

The diagnostic column is the retained median held-out edge corner error in
CFA-plane pixels, not absolute per-frame placement truth. Reference indices
name each output gauge. Every map is `S3-ba-unit`, with spans
1,2,4,8,16,32,64,96,128; logs confirm track prior lambda 1, Huber 1 plane pixel.
Four unavailable diagnostics and five nonzero diagnostics do not prove the
cause of the user's ghosting. Full placement coverage cannot qualify accuracy.
Current `align_cmd.rs::heldout_error` selects long test edges (span >=40,
used >=12); it does not measure independent per-frame truth at the merge.

The final marigolds are -0.5 EV writer variants. Mineral 103 and peacock 102
are -0.3 EV writer variants; the other minerals/peacock 100 are unchanged base
renders. These are exposure renditions, not new merge algorithms. The existing
marigold review itself records 147,253 of 147,456 bright-crop pixels still at an
output channel limit after -0.5 EV. This is a **previously measured** encoded
output statistic read from that report, not a new measurement, RAW clipping
diagnosis, or proof that saturation explains all glare.

**VERIFIED:** mineral originals have since been moved into labelled parent
folders according to `outputs/minerals-september24/final/folder-label-receipt.json`:
103 into `rainbow-opal-cabochon`, 104 into `etched-spessartine-garnet`, and 105
into `rutile-star-on-hematite`. Their retained receipt says all source hashes
were unchanged. New runs must resolve those current paths and bind the existing
input hashes. Blindly rerunning the old `render.py` will reference obsolete
paths. This audit did not rehash the corpus.

**Conclusion:** no configuration regression or wrong capture ordering has been
established. The evidence does establish a known production pipeline with
limited registration qualification and no applied clipping/outlier/occlusion
stages. Existing bounded visual reviews explicitly cannot exclude defects
elsewhere; they do not contradict the user's whole-image judgment.

## Unfinished native coherent estimator: immediate resume requirements

At the audit's initial read, six files exist in
`experiments/native-coherent-estimator`; there are no build/results directories.
The 11,520-byte generated implementation and 28,748-byte independent controls
are complete source units, not stubs. The CLI has both generated and chip
test-only include hooks, but **`chip-implementation.rs` is absent**.

Three mechanical issues block a generated-only run:

1. Remove or explicitly disable only the missing chip module include. Keep the
   generated module and its existing feature guards.
2. `runner.py::LOCAL_SOURCES` currently requires the missing chip file. A
   generated-only runner must bind the extant files and refuse cost/full/
   finalise while the chip adapter is absent. Do not silently manufacture a
   passing photographic route.
3. The driver expects `NATIVE_COHERENT_ESTIMATOR`, while the tests emit
   `NATIVE_COHERENT`, `NATIVE_COHERENT_CASE`, and `NATIVE_COHERENT operator`.
   Match the actual summary prefix and retain the independent two-test,
   twelve-case and SCREEN_COMPLETE checks.

These are driver/include repairs; they require no change to the operator,
fixtures, coefficients, thresholds, or either predeclared decision. Root was
notified before starting a build. Any subsequent root changes supersede this
initial source state and must be bound in that run's own receipt.

**Source-only bridge review:** generated comparison calls the current
`BandWorker::fold` twice, preserving actual rounded GPU gathering, green probe,
injected model and current baseline. It hashes source u16, gathered known-four
planes, guide, variance, beta and regularized focus across replay; verifies
baseline replay; and checks one-source tuple identity. Both current and
candidate use the same camera RGB development. The coherent accumulator
elects regularized Tenengrad27/box17 through the existing FocusStats, uses
Gate4, and gives every admitted source one common four-channel tuple weight.
First contribution copies the sample; subsequent additions occur in generated
source order. All called FocusField/FocusStats/Gate APIs exist in current source.

The independent controls exercise a literal field/count oracle with lower-index
ties, 1/2/3 accepted sources, signed-zero one-source identity, malformed inputs,
a separate ramp focus calculation, actual MeanAll, actual forced wrong donors,
and twelve generated scene/ISO cases. The quality test writes failed decisions
rather than replacing them with Rust test status. Both general and optional
photo admission remain fixed in `independent-plan.md` before results.

Limitations to preserve: the legacy focus-response constant is uncalibrated for
the current gathered guide; the generated arm is not a camera calibration.
The current broad-contact outside signed positive is already known unexercised.
The transparent two-depth and glint cases remain reportable counterexamples
even if optional observation passes. This review is not compilation or runtime
verification.

Two later adapter concerns are bounded and explicit. The accumulator itself
does not enforce ascending replay order (the generated caller does), so a full
adapter must loop the original ascending indices. It currently caps source
count at 299 and area at 3234*2150 quads: three new marigolds exceed the count,
and all five mineral/peacock crops exceed the area. Extending to the new corpus
requires deliberate resource bounds; it cannot simply reuse chip limits.

The missing full adapter must retain canonical current-pyramid chunks, match
the complete retained baseline pixels, use original frame indices/count in
the probe, replay exact gathered evidence, preserve CA/WB/crop/tone, write both
whole native masters, and implement the one-source cost identity against the
literal gathered tuple (not against a one-frame pyramid reconstruction).
The existing runner plan already specifies these contracts. Do not mistake its
written full route for an implemented one.

## Minimal next experiments

**ARGUED:** run the generated coherent screen after the three mechanical
repairs while photographic diagnosis proceeds independently. This cheaply
tests a source-coherent alternative to independent-band mixing on the actual
consumer. It is not sufficient evidence to replace the default or claim
occlusion/glare repair.

**ARGUED:** prioritize a complete marigold baseline/candidate with identical
map, crop, WB and tone if a bounded optional candidate is admitted. Register
visible duplicated petal/hair contours from the user's delivered whole image
before looking at the candidate. Preserve resolved thin hairs, petal texture
and shadows alongside the defect locations. A smoother/less saturated image
alone fails the intended quality claim. Show the full pair and native masters.

For geometry separation, independently examine focused RAW witnesses through
the held map at those defect positions. If their *focused* contours disagree,
test a bounded alternative placement with the current merge; if the focused
contours agree but the merged contour duplicates, test the merge arm with the
held placement. Do not call a lower edge-training residual, smoother index map,
or absent held-out statistic an alignment result. A four-arm geometry/merge
factorial is worthwhile only after both interventions have an independently
qualified effect; otherwise it multiplies full renders without diagnosis.

For mineral glare, separate source clipping, broad defocus spill and output
tone/gamut saturation using a few fixed RAW witnesses at one frozen bright
feature plus a diffuse colored control. Do not infer RAW information loss from
the current TIFF's white region. A writer-only arm can address presentation
and must be labelled that way; it cannot prove spatial restoration or explain
ghosting on the flat slide. The current pipeline's unapplied clipping census
makes this a distinct useful stream rather than another threshold sweep.

## Commands actually used

Read-only commands included `rg --files` on the three output roots and the
coherent experiment; `Get-Content` of invocation/completion/delivery records,
map headers, plans and the relevant source slices; targeted `Select-String`
of render banners; `rg` of alignment log diagnostics; targeted `git diff
--stat -- crates/strehl-cli/src/merge_cmd.rs crates/strehl-core/src/pyramid.rs
experiments/native-coherent-estimator`; and
`Get-FileHash -LiteralPath experiments/native-gpu-gather/build-native-6/strehl.exe
-Algorithm SHA256`. No full working-tree status or original-image sweep was run.
