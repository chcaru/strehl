# One direct-pair branch, conditional on actual registration refusal

2026-09-07. SOURCE-ONLY PROPOSAL / DERIVED resource arithmetic. No subject
import, feature extraction, registration, image read or new output is performed.
This is a bounded next implementation choice, not an execution release.

Use this branch only if the independently read coverage result names
`UNMEASURED_INPUT_REGISTRATION_INADEQUATE` in feature extraction or registration.
Keep its actual first traceback, original identity and unvisited prefix intact.
A decode, runtime, resource, metadata or empty-overlap refusal calls for action on
that boundary instead. Do not turn any refusal into an admitted M193b manifest.

## Concrete experiment

Reuse the nine independently admitted CameraLinear registration derivatives,
indexed locally 0..8 with original indices 0,13,26,39,52,65,78,91,104. These remain
development images, not common-merge ProPhoto inputs or unknown-truth calibration.
Keep the frozen mechanical luma/stretch, feature detector, matching, fit and
acceptance thresholds unchanged. Change only the set of direct pairs evaluated.

Let r be the actual coverage reference's local index, authenticated from its
complete byte ordering and original mapping. Before any new image read, persist
the literal union of `(i,i+d)` for d in 1,2,4 and `0 <= i < 9-d`, and every
unordered `(r,j)` for j != r. There are 20 span pairs and eight star pairs; every
possible r has at least three overlaps, hence at most 25 unique real pairs.
These are local rung spans: they correspond to original-index gaps 13,26,52,
not adjacent RAW frames. Never describe this as a 105-frame span-1 test.

For a star edge call `register_to_reference(features[r], features[j])` in the
same direction as the failed constructor. For a nonstar `(i,j)` with i<j, use
i as reference and j as source. Sort the complete literal list by `(min,max)`;
record local/original indices, direction, both TIFF identities and both feature
identities in every row. An unordered duplicate is one fit, not two independent
observations. Reversing the call is not a harmless equivalent: the frozen
matching/split construction uses ordered reference/source values.

Extract each available frame's features once, retaining only its bounded
FeatureSet. Preserve all nine extraction outcomes and all scheduled pair rows.
A scientific extraction refusal produces `FEATURE_UNAVAILABLE` for its incident
pairs; a scientific pair refusal records its exact original exception. Neither
triggers a replacement edge or threshold change. An operational/input failure
stops the campaign and leaves the remaining work explicitly unvisited. A fully
enumerated campaign can therefore contain scientific refusals without becoming
a successful geometry/overlap package.

The old failed pair must appear with its exact original direction. Reproducing
its same exception would support reproducibility, not prove the reason for it.
If unchanged bytes/runtime/features produce a different result, resolve that
disagreement before drawing a topology conclusion. Historical successful prefix
rows are comparisons, not substitutes for fresh scheduled pair observations.

## Reuse that fits the file allowance

The frozen consumer's `decode_input_path` writes a verified temporary copy on
each decode. A second nine-image pass through that helper costs another
1,780,184,403 written bytes, even if each copy is immediately deleted. It does
not fit the remaining global file allowance. Do not recycle the coverage
reservation or reclaim its unused portion after a refusal.

The existing frozen reference already exposes `decode_input_tiff(blob)`, using
`TiffFile(BytesIO(blob))` and the same one-page/uncompressed/orientation/u16 RGB
checks. Prefer that existing helper here. A small new entry reads exactly one
bounded TIFF blob, checks its actual length and SHA256 against the admitted ref,
passes those same bytes to the unchanged decoder, then releases the blob before
feature extraction. Release the RGB after extraction. Retain neither nine RGBs
nor nine TIFF blobs. This changes temporary storage, not TIFF values or matcher
settings, and preserves an actual same-buffer hash rather than a before/after
pathname claim. Refuse a changed/oversize blob before decode.

Nine feature arrays contain at most 9*1024*(2*8+128*2)=2,506,752 bytes of coordinate
and descriptor arrays; Python keys/objects and the live SIFT/pixel intermediates
are additional. One 197,798,267-byte blob may coexist with a BytesIO copy and a
197,796,096-byte RGB array during decode. This is not a complete peak-memory
proof: unchanged full-resolution luma/SIFT allocate more. Use the existing
encompassing 8GiB committed-memory Job and actual terminal accounting; record
the changed storage choice explicitly. No new TIFF files or aligned frames.

Before coverage work, v2 carry is 324.453125 CPU seconds,347.4812478 wall seconds,
2,157,421,716 file bytes and20,967,233 metadata bytes. Its separately reserved
1,785,427,283 bytes puts file charge at3,942,848,999, leaving352,118,297 bytes.
These are upper-bound charges, not a measurement that all reserved bytes were
written. The next branch must add actual coverage terminal/outer work, all
retained coverage artifacts and this proposal/implementation work, without
resetting the original1200CPU/1800wall/4GiB/128MiB limits.

Propose a branch ceiling of300CPU/480wall/8MiB new files and metadata, including
controls, logs and final persistence. Actual launch needs that much remaining
after the independently audited coverage carry, or a separately reviewed lower
scope; never silently raise the global caps. Before coverage, CPU headroom is
875.546875 seconds and wall headroom1452.5187522 seconds. Thus the proposed cap
fits only if intervening charged work leaves at least300/480. No measured cost
estimate establishes that all25 fits finish: the unchanged similarity routine
may test up to8128 hypotheses against128 calibration landmarks per pair, besides
descriptor matching and nine full-resolution SIFT extractions. Reaching a cap
is a preserved incomplete campaign, not evidence that remaining pairs fail.

## Minimal controls and retained evidence

Keep the actual coverage instrument result and its five small TIFFs as upstream
evidence. Do not repeat the ten product-grid/two derivative private renders.
Commission the new pair entry with at most six small matcher calls: the two
actual nonreference registrations from the existing three-image geometric
fixture, a same-image identity positive, and the existing complementary-focus
pair that must refuse, plus count/placebo repetitions of the first geometric
positive if successful-call landmark observation is retained. Bind the known
fixture reference/order and exact stored
Q32/count expectations from `fixtures.json`; require the actual refusal code
and the positive's nonidentity transforms. These are code-path controls on
frozen fixtures, not new physical truth. The real pair ceiling remains25;
the at-most-six small commissioning calls are separately counted in the same budget.

Use metadata/byte mutations, with restored companions, to challenge the new
entry: an altered blob under the original SHA must fail before decoder entry;
swapping the two distinct fixture source associations or their returned maps
must fail the fixed per-source oracle; inverse direction/rotation sign/native
factor2 errors must fail the existing rational gauge expectations. Do not let
an arbitrary exception count as the expected refusal or let identity-only data
claim direction power. Reuse the existing gauge literals rather than adding a
large synthetic geometry population. Register exact IDs/commands only if this
branch becomes necessary.

Save every successful pair's Q32 source-to-reference transform, existing
registration counts/RMS/source guard, and the bounded matched landmark IDs and
coordinates needed to locate its spatial support. Avoid a second matcher pass:
retain these small actual call outputs at the wrapper boundary if the frozen
return does not include them, using failure traceback locals only on refusal.
If such successful-call observations need an observer wrapper, its off/count/
placebo signature must match on the private pair controls before use; otherwise
keep the existing returned metrics and label absent spatial detail unavailable.
Do not edit the frozen matcher to obtain extra diagnostics.

## Interpretation and consumer gauge

The useful output is a table of direct-edge support and a nine-node support
graph, including refused edges. Report every frame's degree, connection to
local4/original52, component membership, bridges and cycle participation. A
single cycle elsewhere does not make a long tree tail independently supported.
Connectivity is not a per-frame placement estimate and a low accepted residual
is not native-image ground truth. Report accepted inlier fractions and spatial
extent alongside RMS so a small in-focus patch is not called whole-frame support.

Each returned map is source native centres -> that edge's reference native
centres. A future global map G_i from source i to a chosen common gauge must be
reported to the merge in anchor52 coordinates: source-to-anchor is
G_52^-1 composed with G_i; the gather reads its inverse G_i^-1 composed with
G_52. Native and quad translations differ by the explicit factor2. Preserve
the existing exact rational sign/order controls. This pair experiment does not
construct G_i by chaining, solve a global graph, mint an overlap denominator,
or claim the separate0.1-pixel product-output mapping bar.

If local accepted edges provide cyclic support to the anchor while the actual
reference-star edges fail, a later direct-edge global-solve implementation is
worth preregistering, with per-frame independent holdouts in that gauge. If
most local edges also fail, investigate the named extraction/matching support
boundary before adding a solver. A tree-only connected result is explicitly
insufficient. Keep short edges; do not treat long edges as truth, delete spans
1-2 unconditionally, or fit a scene-transfer shrinkage correction. The nine
unknown-truth frames can diagnose support, not prove alignment accuracy.

## Source anchors

- `../next-program-decision.md`, registration-refusal branch: topology changes
  before another weighting/system campaign.
- `../../m193b-geometry-consumer/consumer.py:159,199`: verified disk snapshot,
  digest/exact-byte reference order, streaming constructor and first refusal.
- `../../M193-cover-overlap/reference.py:173,218,307,468,538`: existing bounded
  byte decoder, SIFT FeatureSet, ordered mutual matches and unchanged direct fit.
  Source pin c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790.
- `../coverage-sensor-white-run.py:400,451,464,494,723`: refusal observation,
  exact gauge, fixed controls and encompassing nonreset parent accounting.
  Source pin16f9e944673aa58b81727fabddadc7192a082cef149e950cd7dda24f217e51cf.
- `../charter.md:204,244`: original52 consumer gauge and global rehearsal caps.
- `../../../docs/research/SYNTHESIS.md` section3.3 and facts1407-1410:
  endpoint improvements do not establish per-frame placement; short edges are
  biased and load-bearing; nonlinear tracks and named gauges remain required.
