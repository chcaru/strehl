# Draft: integer translation and crop at common-RGB consumption

2026-09-08. SOURCE-READ / DERIVED / ARGUED proposal for root review.
This is a next-task draft, not an execution grant. It is outside the current
200-source recovery map. Keep those bindings unchanged through controls,
admission, render, verification and the final independent source check.
Implementation begins only after that software-integration result is accepted.
No current recovery result is inferred here.

## Question, prior answer and consumer

Commission the smallest supplied-map extension of the existing common-TIFF
consumer: signed integer translations and one explicit common crop. The
question is whether each fold consumes exactly the declared source samples on
that output grid while preserving the established identity modes.

The completed next-integer-consumer-audit.md already ran the mandatory query:

    python -I -S -B experiments/ORCH-drift-check/prior_art.py "integer translation" "known map" "common RGB" gather "resampling noise"

It returned V-GATHER.md, BUILD-DEMOSAIC.md, V-HEADTOHEAD2.md and BUILD-GATE.md;
secondary names were BUILD-SHARP.md, M107b-lateral-correction.md,
ORCH-veiling.md, M95-resample.md, M86-alignment.md and M95-cdiff.md, under
docs/research. The audit records the query, scope and prior context. Those
ranked hits are leads, not new verification of every report. This draft uses
that already-completed search, rather than making an absence-of-prior-work
claim. M165's PROPHOTO_DISPROVED qualification and M103's per-frame consuming
gauge remain binding.

SYNTHESIS sections3.1-3.2 were reread before this proposal. The actual consumer
is BandMerge::add_frame_with_gain in
crates/strehl-cli/src/bin/common-stack/mod.rs:308. It receives three f32 planes,
the (R+2G+B)/4 proxy, an injected variance array and explicit BandGain values.
The input storage is CommonTiffFrame.pixels, interleaved RGB u16. Read one
decoded frame at a time and fill the already-required current-frame f32 buffers
directly from its integer source addresses. Do not first convert the full
source to f32 and then allocate another mapped copy; retain no prepared stack.

The general checked gather API uses destination-to-source maps but requires
equal source/destination geometry and an f32 source plane. It is not a
drop-in crop adapter. No core sampler, native CFA half-grid convention, real
sidecar, interpolation kernel or parser change is required for this task.

## Proposed closed request and coordinate convention

Keep the existing CLI grammar. Add a separately admitted
common-tiff-stack-v3 request with the seven existing top-level fields plus
one required sampling object. Versions1 and2 must reject that new field and
keep their existing schema-specific count, geometry, profile, output metadata
and byte behavior. A version-specific parse/serialization branch must not add
null fields to old plans or descriptions.

For v3, grid names the shared input shape, RGB order and source-local RGB
pixel centers; use a new literal coordinate label instead of describing a
nonidentity request as identity. The supplied maps define the common output
grid, which is distinct from the input shape. Retain2..8 exact ordered inputs
and shared input axes64..512. sampling has a fixed model name, a crop
{origin_x,origin_y,width,height}, and one ordered {input_id,tx,ty} entry per
input. The final implementation/spec will freeze spelling and exact error
strings before execution. Require each map input_id to equal the corresponding
already-file-bound input id; no sorting, missing-map default or duplicate map
admission.

Proposed finite domain: output axes64..512; actual JSON signed integers for
origin_x,origin_y,tx,ty, each in[-512,512]. Reject bool, fractional, nonfinite,
out-of-range and unrepresentable integers. Use checked signed addition and
checked allocation/index arithmetic even though these finite bounds make
integer overflow unreachable for admitted requests. A huge-integer refusal
does not prove an internal checked-add overflow branch ran.

Define the half-open rectangle and direction literally:

    q = (origin_x + x, origin_y + y),  0 <= x < width, 0 <= y < height
    source k = (q.x + tx[k], q.y + ty[k])

Coordinates denote full-resolution RGB pixel centers. All three channels use
the same source index. There is no CFA factor of two, half-pixel offset,
transform inversion, implicit frame-zero anchor or origin recentering.
Translations are supplied truth, not fitted values.

Before decoding any TIFF, validate the complete translated rectangle for every
declared input shape. Require its lower endpoint>=0 and exclusive upper
endpoint<=the source extent on both axes. Refuse unsupported coverage;
do not clamp, wrap, round, pad, shrink the crop or admit a partially covered
frame. On each visit, still authenticate the whole source/pixel/profile and
actual parsed shape before gathering and folding. A late actual shape/hash
failure must retain the exact earlier folded prefix and no admitted output.
Known invalid manifest support can refuse early; it need not waste earlier
folds to manufacture a late failure.

## Crop before pyramids and unchanged numerical contract

Create BandMerge and FrameWorkspace for the output crop shape. Gather that
crop before proxy construction, pyramid construction, election, accumulation
and InputRange. Merging full frames and cropping the result is a different
operation near pyramid boundaries; it is not the reference implementation.

Keep RGB16 code values, the exact ICC/profile contract, three Laplacian bands
plus base, explicit HardFloor/fixed merge settings, quantization and the existing
two simulation-only noise laws. Carry the same injected variance and white
operator gains for the admitted integer reindexing. A translation restricts to
a one-to-one correspondence between the output grid and one source rectangle;
it is not a bijection onto the entire larger source image.

DERIVED conditional statement: unique integer reindexing introduces no sample
mixing or repeated source site, so it preserves the declared independent-site
noise law and its within-pixel RGB covariance. It does not establish that
developed real RGB follows that law. Fractional interpolation generally changes
variance and inter-output covariance; marginal variance alone would not
justify reusing the white gains. Fractional/affine maps, real placement,
heterogeneous source shapes and physical calibration are separate tasks.

Keep the authenticated full-source pixel hash. Add a distinctly named hash of
the actual gathered values passed to each fold, before and after consumption;
a crop hash cannot be asserted equal to the full-source hash. Retain actual
proxy/variance before-after hashes and values, actual passed gains, ordered
fold counts, input/output shape, origin, translation and covered rectangle.
Reuse existing hash machinery and per-frame receipts. Mandatory address
metadata does not inspect the merge; any newly added merge observation must
participate in the same existing off/on/placebo mode.

The v3 TIFF must state its output dimensions, profile, RGB16 units and truthful
crop/map convention. Bind its common-grid origin and manifest identity in the
final receipt; freeze exact description/metadata bytes before running.
Old v1/v2 TIFF descriptions/software/profile behavior stay byte-identical.
Cross-version oracle comparisons use exact pixel payload plus dimensions and
profile, because truthful v3 metadata can differ. Within one v3 request,
observer off/on/placebo still requires whole-TIFF and pixel equality.

## Bounded candidate evidence for independent registration

Propose14 product invocations, not a sweep. A different author must freeze
the literal generator, expected source addresses, integer truth and saved
reader before any execution. Reuse the admitted TIFF subset, actual process
wrapper and file/refusal interfaces.

| Cases | Candidate purpose and independently rejecting observation |
|---|---|
| 0-1 | One exact held v1 and one exact held v2 compatibility request. Require their archived whole TIFFs and unchanged admission semantics. Bind actual accepted prior outputs only after current verification closes. |
| 2 | v3 zero translations/full extent on the chosen v2 inputs. Exact pixels/profile/dimensions match case1; test new branch identity without requiring false metadata equality. |
| 3-5 | Mapped asymmetric RGB address fixture; independently generated identity-oracle crop; mapped fixture changed only outside every consumed rectangle. Require all per-fold gathered/proxy hashes, oracle output pixels and outside-change output invariance. |
| 6 | Distinct constant contributors with nonzero translations. Independently rounded output mean and actual ordered fold identities must both match. Show every selected omission/duplicate fault changes the expected rounded value. |
| 7-9 | One mapped flat/textured Rademacher population, observer off/on/placebo. Require whole-TIFF/pixel equality, actual gathered noise/proxy/variance/gains, and both accumulated-denominator populations in Laplacian levels for on. The base level alone cannot supply the positive population. |
| 10-11 | Missing map and one translated rectangle outside declared support. Both refuse before decode/fold, with exact reason and no admitted TIFF. |
| 12-13 | Final input actual geometry and final input actual whole-file-hash faults. Retain the first two successful folds and refuse final output. |

For mapped cases3 and5-13 the proposed shared input shape is129x97, N=3,
crop96x64 with origin(16,16) and ordered translations(-5,3),(4,-2),(0,0).
Case4 is the independently generated96x64 identity-oracle crop. These include both
signs and a nonzero origin. Independently verify the address fixture is
asymmetric enough that sign reversal, forgotten origin, wrong row stride,
channel swap and a duplicated source index each change the actual expected
consumer values. A wrong but in-bounds supplied map cannot be rejected as
physically wrong by this program; the independent literal truth must expose it.

Before release, register eight small metadata/checker-control groups covering:
zero-map identity; signed direction/origin; stride/channel/index destroyers;
type/field rejection; integer and crop bounds; exact map count/id/order;
half-open coverage edges; restored valid operands. Enumerate exact variants
and require their branches/differences to be exercised; this draft does not
authorize an open-ended fuzz pass. Type/bounds controls can use the actual
manifest parser without rendering. They must not be mislabeled numerical
coverage. Full output agreement alone is insufficient because InputRange can
hide a wrong prepared contributor.

No thresholds may be tuned after observing the candidate results. If a
direction destroyer is identical on its fixture, repair the prospective
fixture before release; do not count a vacuous positive. A passing study
establishes only this bounded supplied-map common-RGB software consumption.

## Minimal implementation and release boundary

Expected edits, after the current source audit closes:

- common-stack/manifest.rs: versioned sampling schema, separate input/output
  layout, exact map associations, bounds and complete support preflight.
- common-stack/integer.rs (new): checked indexed conversion from public decoded
  u16 pixels directly into current-frame output planes; no sampler dispatch.
- common-stack/mod.rs: select the versioned preparation path, build pyramids
  on output dimensions, bind actual gathered inputs and preserve failure prefix.
- common-stack/writer.rs: v3 truthful output metadata and crop shape, retaining
  exact old writer branches.

Do not alter core align/warpmap/pyramid, native image_out/main, RAW parsing,
merge coefficients/defaults or old study artifacts. The existing bin can keep
its argument grammar; no independent alignment command is needed.

Retain input/output allocation guards: source/output pixels<=262144,
per-input and per-output encoded cap6*pixels+64KiB<=1,638,400B, at most eight
input extents,64KiB manifest, one decoded u16 frame plus output-sized f32
preparation and reusable core workspace. Map metadata is O(N), not O(pixels).
The existing192KiB bounded v2-style detailed receipt is a proposed v3 ceiling,
not a demonstrated complete-record bound; the final source contract must size
the new N8 normal receipt, stages and refusal transport before freeze.

Root must separately adopt finite build,14-case render, independent-checker
and metadata resource ledgers after source sizing. Reuse existing compatible
owned-process tools and fresh outputs; retain every earlier charge/refusal.
This draft grants no build, decode, fixture generation, simulation, test,
product invocation or source mutation.

A negative or incomplete result stops this extension at the failed consumer
contract. Do not compensate by fitting real geometry, relaxing support, choosing
a content-dependent crop, changing noise gains or opening a larger campaign.
PROPHOTO_DISPROVED, fractional covariance, real-alignment accuracy and SOTA
remain outside the claim.
