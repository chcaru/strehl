# M193c registration-derivative design — independent static review

2026-09-07, directional_detail. Reviewed the held
`registration-derivative-design.md`, SHA256
`f503af4c7805f8e4b2f4771b2baaf31599ed9f0ca583d2958a1a6da11a408d68`.
**STATIC SOURCE REVIEW ONLY:** no numerical imports, image/RAW reads, decoding,
builds, hooks, rendering or registrar execution. This review does not verify
its author's implementation; none exists yet. The architectural decisions in
`SYNTHESIS.md` §3 and the accepted M193c charter were read first.

The proposed seam has no architectural blocker for **CameraLinear registration
development inputs**. Root has accepted the two explicit choices: use the
owned decoder with honest post-decode extent checks and a process committed-
memory limit; retain the existing camera-channel intensity projection and
byte-identical relocated registrar. This is not common-TIFF qualification,
known-truth geometry, or a new noise/colour model. The conditions below must
be resolved in the concrete preregistration before execution.

## Actual decode, WB and writer path

The project-owned `strehl_raw::decode` checks the decoder's RGGB camera pattern,
returns an owned u16 allocation, and exposes the active rectangle. Independent
checks must still require contained even active origin/extent, checked
stride×height and full-active agreement. A different padding origin between
decoders is not automatically a pixel defect; mismatched visible arrays or
local phase is a refusal, without an offset search.

One wording correction is necessary: the wrapper already resolves missing
black/white metadata to0/65535 (`strehl-raw/src/lib.rs`, the two `unwrap_or`
expressions before the returned Frame). Frame-only checks cannot distinguish
those defaults from explicitly reported values. State **resolved scalar levels
under the existing wrapper rule**, persist their actual bits, and require the
independent decode agreement. Do not claim that metadata presence was proved
or that no upstream fallback occurred. Root accepted this disclosure without
changing the decoder.

`Frame::wb_gains` reads the first R/G/B coefficients, ignores the fourth,
requires positive finite raw coefficients, then computes R/G and B/G. The
new adapter must also check its returned gains: finite positive inputs alone
do not prevent ratio overflow. Its operation
`((sample-b)*(1/(w-b)))*gain` matches the proposed WB-before-MHC seam. It is
not exactly the multiply/divide expression used by every other writer caller;
freeze this operation order as stated rather than claiming general byte
equivalence to a merge output.

`write_demosaiced` forms the RGB16 output with per-row f32 scratch.
`Develop::measurement(false)` has no tone/matrix/transfer; `resolve_tone`
returns without evaluating its measurement closure. `develop_pixel` applies
the final per-channel clamp and half-up quantization. Thus negative/above-one
mosaic values really can reach MHC. Full native integer centres and the
active-local RGGB phase are the correct grid; there is no extra half-pixel
shift or binned/co-siting operation on this path. The CameraLinear description
is consistent with as-shot green-normalized gains, unlike unity gains under
that unchanged description.

## Re-chosen control checks and remaining literal choices

The proposed30×22 affine field has full-rank R/G Jacobian
`[[1/512,1/256],[1/256,-1/512]]`, determinant`-5/262144`.
All source CFA expressions are integers with the proposed range4096 and gains
2/1/4. For example, R is`64+256+4x+8y`, G is`64+1024+16x-8y`, and B is
`64+384-2x+2y`. Their dyadic normalized values and MHC affine reproduction make
the one-code output tolerance defensible for this literal interior population.
The chosen sites stay within the two-pixel MHC support. It is a useful separate
two-axis instrument, not a repeat of my40-DN/native-pixel warp field.

The non-affine black-clamp witness has power at a different site from its
perturbation. At R source(10,8), changing`b-16` to a premature black clamp
changes normalized R by`1/128` after gain2. At G1 output(11,8), the horizontal
red stencil gives this site weight1/2. Therefore the interpolated red changes
by`1/256`, about256 u16 codes, while remaining positive. The measured R output
at the negative centre can be identically clipped to zero in both arms and
must **not** be used as the only power witness. This result is DERIVED from
the actual MHC support, not an executed comparison.

The four corner impulse codes and padding sentinel are not yet literal in
the held proposal. A defensible fixed choice for the later preregistration is
raw codes`[2368,576,1088,1472]` at top-left/top-right/bottom-left/bottom-right,
on a baseline raw192, with raw48 at(10,8), black64, white4160 and gains2/1/4.
The top-left R and bottom-right B impulses then exceed1 after WB, powering
premature upper-clamp effects at reconstructed neighbours. Padding can use
65000 with a17-valued null replacement. These are proposed prospective
literals; the held design has not been edited or executed.

Before implementation, freeze the complete named metadata/lifecycle/reader
fault inputs and their restored companions, not just categories such as
"invalid geometry". For WB ordering, use the non-affine fixture: affine fields
have zero cross-channel second differences and cannot distinguish gain before
versus after MHC. Actual normalized-mosaic/writer consumers must supply the
values judged by these controls. A model-only wrong-law calculation cannot
stand in for a missing actual callback or stage witness.

The proposed two derivative TIFFs plus my ten geometry TIFFs use **exactly12
small private output slots**. Source-helper mutants and TIFF-byte mutations
can be evaluated in memory or against copies of those two products; they
cannot silently invoke extra product writers. Preserved failed attempts count
against the same invocation envelope. If another actual TIFF is needed, root
must amend the population before that invocation. There is no optional
derivative observer here, so no uncommissioned observer exemption is claimed.

## Independent decoding and source/lifetime authority

The nine original paths/indices and complete byte hashes must be fixed before
the first decode. Both decoders read the same workspace snapshot, one input
at a time, with verified original/snapshot before/after binding. Record all
original identities even if two derivatives have identical bytes. File
deletion concerns only the owned temporary snapshot after both consumers;
corpus paths and failed evidence remain untouched.

The rawpy copy must occur **inside** its context, and every subsequent hash or
row comparison must use that owned copy. A second array made after closing
the context, or `ascontiguousarray` returning the view, would not establish
lifetime safety. Map rawpy public colour labels/visible phases to R/G/B/G
explicitly; do not assume an arbitrary fourth-channel ordering. Compare all
active u16 samples exactly, all reported CFA black levels against the consumed
scalar, and the documented usable-white selection. The WB comparison may use
the proposed fixed relative f32 allowance, but a failed WB or level comparison
is a metadata-agreement refusal, not something to repair with a fitted colour
gain. Record the independent decoder's actual selection convention as well
as its result. Neither agreement nor exact pixels validate physical calibration.

The listed five inspected source hashes match current files. Before execution,
expand them to actual include/build/Cargo.lock/dependency/runtime closure,
including both RAW backends and the loaded Python/OpenCV/NumPy/tifffile modules.
Record the exact interpreter flags and copied executable. The separately
bounded TIFF reader must consume pinned bytes, validate header/strip sizes and
types before allocation, and recheck the final source/output set through
terminal persistence. Avoid treating a source map supplied by a candidate as
its own executable authority.

## Frozen registrar: useful pass, first refusal and relocation

The camera-native proxy interpretation is correctly limited. Frozen
`prophoto_luma_u16` is an integer weighted projection; `registration_u8`
then applies the existing per-image1–99% stretch. Its name does not establish
ProPhoto primaries. Feature extraction fixes OpenCV threads to1 and disables
OpenCL. Passing requires mutual landmarks, calibration/holdout separation,
majority held-out consensus and RMS<=1 reference pixel. This is compatible
landmark support, not absolute per-frame truth or the separate0.1-pixel output
descriptor bar. A common shared bias may survive the fit.

The real constructor **stops at its first inadequate nonreference image**
(`consumer.py::construct_overlap_paths`, its unguarded
`register_to_reference` call). One exception cannot be expanded into nine
per-frame verdicts. Root chose to preserve the frozen first-refusal behaviour:
retain the exact failing call and mark the unvisited remainder unmeasured.
Do not mint `TrustedInputBinding` from the partial prefix. A later separately
registered all-eight-pair diagnostic could reuse the same functions and
reference under the same budget; none is authorized by this review.

Reference order remains minimum byte hash/length/exact bytes, independently of
original input order and the product anchor. Even a description/version-tag
change can alter that byte ordering. Preserve the returned reference's actual
original identity set and the original-to-derivative association; never infer
it from input position. The actual returned manifest's sources/multiplicities
must match the externally pinned nine derivatives.

Relocating **byte-identical** consumer/reference files with their sibling
layout is preferable to monkeypatching `HERE` or a math function. It changes
only the temporary-file root. Pin original and copied files, use a fresh
interpreter/cache, and bind the actual imported copies. Re-run the frozen small
manifest companions and complementary-focus refusal in that relocated path;
the latter is an expected old-algorithm limitation, not proof that these nine
real derivatives must fail. No all-real-coverage or common-merge claim follows
from successful small companions.

## Resource interpretation and disposition

The440,196,608-byte allocation sum is correctly labelled named storage, not RSS
or a bound on native decoder/SIFT scratch. The public decoder allocates before
the new Frame checks; enforce the parent process committed-memory limit from
launch and reject bad extents immediately after decode, before mosaic/output
allocation. The process limiter and observed working set are distinct records.
Include originals/snapshot hashes, both decoders, temporary TIFF, registrar,
all saved artifacts and final persistence in the existing non-resetting
1200CPU/1800wall real envelope and4GiB storage cap. The two derivative controls
share the existing600CPU/1200wall private envelope with the ten grid cases.

Disposition: **ACCEPT_DESIGN_WITH_EXPLICIT_PREREG_CONDITIONS**, limited to the
above scope and root decisions. This clears source preparation after literal
controls/schema freezing. It grants no implementation verification, decode,
build, render, registrar execution, numeric PASS or real-input admission.
