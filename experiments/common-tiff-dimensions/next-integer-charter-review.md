# Independent review: integer translation/crop charter

2026-09-08. SOURCE-READ / DERIVED / ARGUED. No new runtime, image, metric,
compiler, product, parser-control or reader execution. This reviews the proposed
contract, not an implementation or the already accepted dimensions result.

Verdict: the narrow supplied-map extension is appropriate after the dimensions
result closes. Already answered by the preceding audit: use a checked integer
conversion from the current u16 frame into the existing per-fold buffers; no
general sampler or real-alignment sidecar is needed. The new consumer itself is
not already implemented. Freeze the concrete points below before its separate
source-only commission. These changes fit the proposed14 calls and eight control
groups; this note does not authorize additional cases or execution.

Reviewed draft: next-integer-charter-draft.md,13,132 bytes,
SHA25682255b9a53477c8b55c10b32a74e17a0a7d6101cab2c1ed035ff96f8d10ee93d.
Preceding audit: next-integer-consumer-audit.md,16,907 bytes,
SHA256578b3257c510748df5efee6f534da225bf05021820cd3cdbbfccb7b97da98815.

## Coordinate sign and independently named gauge

The proposed pull is correct: output local(x,y) -> common coordinate
(origin_x+x,origin_y+y) -> source k by adding(tx[k],ty[k]).
warpmap.rs:16-30 and441-495 already define destination-to-source placement
without inversion. Its f32, equal-geometry, masked interface is not the proposed
u16-to-crop conversion; do not force a crop through it or use its CFA/centered
Similarity machinery merely to implement integer addition.

For input129x97, crop96x64, origin(16,16), the actual required source rectangles
are the following DERIVED address facts, not executed measurements:

| Ordered map | First sampled source | Last sampled source, inclusive | Half-open required rectangle |
|---|---|---|---|
| input0,(-5,3) | (11,19) | (106,82) | [11,107) x [19,83) |
| input1,(4,-2) | (20,14) | (115,77) | [20,116) x [14,78) |
| input2,(0,0) | (16,16) | (111,79) | [16,112) x [16,80) |

One source address applies to all RGB channels, with source row stride129.
For example, input0's red sample at output(0,0) has interleaved-u16 index
3*(19*129+11), not3*(19*96+11). Test the literal address/hash independently;
do not derive the expected coordinate by invoking the mapping implementation.

There is a gauge ambiguity that pixel equality cannot resolve: adding the same
integer delta to origin and subtracting it from every translation leaves every
sample unchanged, while relabeling the common output coordinates. Retain and
independently assert the exact literal origin and ordered maps as metadata.
Do not infer the origin from matching pixels or silently recenter on frame0.

The proposed rectangle lies strictly inside the sources; it does not itself
exercise equality at a coverage boundary. Within the existing half-open-coverage
control group, enumerate legal lower0/upper==source_extent and adjacent illegal
lower-1/upper==source_extent+1 operands on each axis. Freeze exact rejection
categories before running. An out-of-range JSON integer exercises parsing/range
rejection, not a checked-add overflow unreachable under the admitted bounds.

A forgotten origin can cause an early support refusal for the first proposed
map (its x would begin at-5), whereas sign reversal remains in bounds for the
nonzero maps. Label those different detection paths honestly. Do not count an
early refusal as evidence that a wrong but reached consumer array was observed.

## Separate input shape, output shape and refusal order

This is the concrete integration hazard in the present code. Layout.width/
height/pixels currently serve both TIFF preflight and all output allocations.
mod.rs:250-258 builds BandMerge/FrameWorkspace with those dimensions;
manifest.rs:335-382 compares the TIFF's bounded LONG/count1 width/height against
the same fields before CommonTiffFrame::parse allocates pixels.

The new layout must retain both shapes. Source dimensions/cap govern the whole
input file, preflight, parsed frame and u16 row stride. Output dimensions/cap
govern gathered planes, proxy/variance population, four pyramid levels, workspace,
merge and encoded output. A valid129x97 source must not be rejected against its
96x64 crop, and a valid crop must not permit a huge actual TIFF allocation.
Keep the existing small IFD preflight before full decoding.

Freeze the following semantic ordering while retaining old-version ordering:

1. Authenticate and parse the manifest; validate schema/types/cardinality,
   exact input-to-map ID/order association, both layouts and complete translated
   support for all declared inputs. Reject missing-map/unsupported support before
   any TIFF decoding or fold. All unrelated fields in those controls must be
   valid so the intended branch is reached.
2. Complete the existing fixed profile/noise/merge/path/extent checks before
   their dependent operations. Keep byte caps based on their correct source or
   output role, and require the output's three-band/four-level geometry before
   the first TIFF visit.
3. On each actual visit: bounded whole-file read/hash, source-shape IFD
   preflight, full parser/pixel/profile/provenance checks, gather, proxy/variance,
   fold, immutable frame receipt. No clamp, partial coverage or synthetic border
   values reach the dense pyramid.

For the final-input geometry control, bind the changed actual file and pixel
identities correctly so it reaches the geometry predicate; otherwise the earlier
whole-file hash check wins and the alleged geometry control has no power.
For the hash control, bind actual altered bytes in the fixture catalog while
leaving the product manifest's deliberately wrong expected hash distinct.
Both N3 late cases require exactly two immutable folds, stage input-2 and no
admitted output. Copying dimensions' input-4 expectation would be wrong.

There is also a version-label seam to settle: manifest.rs currently requires
the same GEOMETRY literal for grid.coordinates and input.provenance.geometry.
The v3 source-local sampling label must not blindly replace both, since the
zero-map compatibility request is intended to reuse exact held v2 TIFF bytes.
Separate the sampling-coordinate meaning from authenticated stored provenance,
or explicitly freeze the compatibility rule for the retained old label. A
metadata label is not evidence of physical registration. Do not silently rewrite
old input provenance or add null sampling fields to old serialized plans.

## Independent crop oracle and outside-crop invariant

Case4 must contain three independently generated96x64 input TIFFs, one for each
of the three mapped contributors. It is not a merged full-source image cropped
afterward and not a single final-image target. Each crop input is fed through the
existing identity consumer with the same order, settings, output geometry and
noise declaration as the mapped request.

A defensible independent construction starts with a literal crop-domain
asymmetric RGB function G_k(x,y). Write that function directly into oracle k.
Embed its values into source k at the independently fixed source rectangle,
using an inverse source-to-crop construction and explicit endpoint checks.
Do not import integer.rs, call its address helper, or obtain the oracle by
running the new v3 mapper. The actual mapped per-fold hash must equal the
corresponding independently decoded oracle input's entire pixel payload before
any final image comparison. InputRange can conceal an incorrect contributor,
so final output agreement alone remains insufficient.

Case5 changes actual u16 source pixels outside each frame's consumed rectangle,
with whole source pixel/file identities changed and correctly rebound. Require
that this actual change is exercised; a metadata-only change or accidental
rewrite of identical codes is not the control. Keep all gathered/proxy/variance
and passed-gain inputs identical to case3. Assert exact output pixels, dimensions
and ICC/profile. Record whole-TIFF equality without requiring it: the changed
input/manifest identity can legitimately alter truthful v3 metadata. The same
comparison choice applies between mapped and independently represented oracle
requests. Within one mapped request, observer off/on/placebo still requires
whole-TIFF and payload identity.

Outside-crop invariance checks dependence on unused samples; it does not alone
prove a wrong merge-full-then-crop implementation must change on every fixture.
The actual crop-sized arrays/hashes passed to BandMerge, its output-grid
construction and source review establish the stage boundary. Do not claim a
powered wrong-order alternative from an outside fixture whose wrong-order
response was never observed. No extra wrong-order product arm is needed.

## Noise and retained scope

Unique integer indexing is one-to-one between each output rectangle and its
source crop. Conditional on the declared independent-site simulation law, it
preserves each sample and its within-pixel RGB covariance without mixing or
duplicating source sites. The core BandGain contract concerns the operator;
its current white model is memoized by band count, not newly fitted from a crop.
Preserve the actual existing white gains and injected variance. This extension
does not independently calibrate a spatial boundary noise model or real RGB
noise. Fractional sampling would introduce shared-source covariance and requires
a different contract.

Keep the on-mode mixture claim collective across the three Laplacian levels,
excluding the base, unless independently registered otherwise. Zero/positive
census rows, shapes and site counts remain actual per-fold observations; do not
claim every level or fold is mixed from one accumulated sum. The noisy
off/on/placebo population should use distinct per-frame noise fields and an
asymmetric flat/textured crop, with exact gathered-code/proxy/variance checks.
No spatial SD, temporal variance, quality score or new camera calibration follows.

No new product population is requested. A useful choice within the existing
compatibility slots is the held N8/max-shape v2 positive for cases1/2, if root
selects it: it exercises the new version's full ordered map list and full-extent
identity boundary while reusing prior accepted bytes. It is not a request for
another dimensions campaign. The independent spec must enumerate the eight
control groups' finite variants and require their actual intended effects.

## Prior answers and read scope

The preceding audit's already executed query was:

    python -I -S -B experiments/ORCH-drift-check/prior_art.py "integer translation" "known map" "common RGB" gather "resampling noise"

Its principal reports were V-GATHER.md, BUILD-DEMOSAIC.md, V-HEADTOHEAD2.md and
BUILD-GATE.md. Secondary leads were BUILD-SHARP.md, M107b-lateral-correction.md,
ORCH-veiling.md, M95-resample.md, M86-alignment.md and M95-cdiff.md. This review
did not rerun the query or reread those reports. Their bounded discovery record
is already in the audit; no global absence of prior art is claimed.

SYNTHESIS3.1-3.2 confirms u16 storage/current consumption rather than an aligned
stack; fact1407 and discipline699 name the per-frame consumer gauge. The actual
current seam is CommonTiffFrame.pixels:Vec<u16>, then three temporary f32 planes,
proxy and injected variance passed to BandMerge::add_frame_with_gain. Keeping
one frame at a time and output-sized preparation preserves that architecture.

Commands actually used were bounded Get-Content reads of the two named notes;
targeted rg symbol/section searches only in SYNTHESIS, warpmap.rs, pyramid.rs,
manifest.rs and mod.rs; and a stdlib source reader that checked per-file3MiB and
aggregate16MiB caps, printed selected line ranges and same-buffer SHA256s.
No recursive search, prior_art invocation, external repository, GPL/LGPL source,
image payload or candidate function was accessed.

The detailed source pins and selected lines are:

| Source | Bytes | SHA256 | Selected lines |
|---|---:|---|---|
| docs/research/SYNTHESIS.md |2213785|e0448cc278635067dccd004cd8e469a73ad2a2df7bd1232b80a3cf4ccde9e6b0|157-207,255-281; targeted1407/699 matches|
| crates/strehl-core/src/warpmap.rs |54829|9d2198eeab5e8a941e297cf8fcd8a217d2454390220433ae19cc6b07e6fd721b|1-32,430-507|
| crates/strehl-core/src/pyramid.rs |208956|ea0a490d299b156c449b3de8c5633fcaeda2190d1c92d1d9c5356e6a9a92c02e|420-452,1700-1746|
| crates/strehl-cli/src/bin/common-stack/mod.rs |18095|fc55cdaca929b5540901dc246c4294df6fa6c9f3a4407b16799c0de2ecd91452|224-343|
| crates/strehl-cli/src/bin/common-stack/manifest.rs |12421|52e8c0e5ad556b71aaee385fd8caa15b9e57806db08af4cb4222c2859801a628|1-45,142-243,252-301,335-383 selected|
| crates/strehl-cli/src/bin/common-stack/writer.rs |5138|92c47325646d8206a7cf5a840d4bb77ed134caafefbabb81c5bc4410284687a5|10-15,72-94|
| crates/strehl-raw/src/common_tiff.rs |33071|bac1d18f036b8960a8e82d01b610ae945d00d259d4cc3fe7eb9106e8a8077f42|97-131,381-415|

Conservatively charging each named searched/read file's full extent yields
5,126,880 bytes before this note's bounded readback; reserve6MiB in total within
the16MiB authorization. Only this new review file is retained, capped32KiB within
the1MiB retention allowance. The full10CPU/30active-process-wall allowance
remains charged; the source-reader timer sample is not an end-to-end CPU claim.
No commit or mutation of the frozen200 sources was made.
