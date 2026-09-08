# Independent factor-eight source review

2026-09-07. SOURCE REVIEW ONLY. No prototype import, numerical helper, image decode,
SIFT extraction, matcher, fit or control was executed in this review. This reviews
the compact proposal, not a released runner. Read AGENTS.md and the relevant
SYNTHESIS architecture/profile record and facts 174, 1407-1410 first.

**HOLD for execution until the diagnostic guard qualification and complete runner
are reviewed.** The proposed geometry and integer averaging are coherent by source
inspection. All actual positive/fault outcomes remain UNVERIFIED.

## Exact reviewed sources

- `factor-eight-prototype.py`: 5,790 bytes,
  `86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f`.
- `factor-eight-proposal.md`: 8,659 bytes,
  `c65a94a2ea0378f1bcdded0377392411bcc660bb395450001b37f9648ba8fd1b`.
- `next-registration-diagnostic-decision.md`: read the initial SHA
  `67724433cb1fa30bbfeacc8ec42839c255c7f8af2464c1a520cd8fa5cae71fd1`.
  This review corrected only its +2-native-pixel destroyer wording: it must fail
  the independent known-map corner oracle. The registrar is not called on that
  mutated map, so claiming its held-out RMS gate rejects it was incorrect.
- Frozen `experiments/M193-cover-overlap/reference.py`, symbols
  `extract_features`, `match_features`, `register_to_reference`; and
  `experiments/m193b-geometry-consumer/consumer.py`, `_SUPPORT_RULE` and
  `validate_input_manifest`. These were read, not changed or executed.

## Blocking qualification

The frozen extractor rounds coordinates to coarse Q8. The lift multiplies that
lattice step by eight: one step is 8 native Q8, or 1/32 native pixel. In contrast,
`register_to_reference` still emits `coordinate_quantization_guard_q8 = 1`,
`guard = heldout_max_source_px_ceil_q8 + 1`, and continuous margin `128 + guard`.
The consumer explicitly accepts that same one-Q8 contract. Keeping the native
2-pixel inlier and 1-pixel RMS limits does not repair this support discrepancy.

Do not change frozen source to conceal it or silently multiply its tolerance.
Every new returned pair and its parent report must state: the map and residuals
are native-coordinate registration diagnostics, but the returned guard and support
margin are UNQUALIFIED for the eight-Q8 lattice. No consumer manifest, overlap
rectangle, output-support admission or product map follows. The proposal mentions
the new lattice and forbids overlap in general; it must name this actual field
mismatch explicitly. A future support contract needs separate commissioning.
A JSON qualifier should travel beside every actual map/guard, including private
calls, rather than relying only on an easily detached report paragraph.

## Independent derivations and failure power

AREA8 is a nonoverlapping 8-by-8 sum of the original contiguous u16 RGB, before
the existing projection/stretch. Axis tuple (1, 3) removes only the two within-
block spatial axes; it cannot mix channels or frames. Its uint32 maximum is
64*65535 = 4,194,240. Quotient/remainder rounding increments above 32 and at 32
only for an odd quotient. Thus proposed sums 31,32,33,95,96,97 map to
0,0,1,1,2,2 and can expose wrong half-tie behavior. These are DERIVED expectations,
not results. An all-65535 block exercises the maximum without saturation loss.

For native centres 8j through 8j+7, the block centre is 8j+3.5; native Q8 is
therefore 8*q_coarse+896. For a reference width 3072 and an exact `rot90(k=1)`
source, the inverse pixel-index permutation gives reference coordinates
(3071-y_source, x_source). This agrees with prototype (a,b,tx,ty) = (0,1,3071,0)
and source corners (0,0), (2303,0), (0,3071), (2303,3071). Omitting the shared
centre offset in this rotation produces translation 3064, a 7-native-pixel
error. A translation-only plant would let that error cancel; the nonidentity
choice therefore has power the simpler plant lacks.

`corner_errors` computes its expected positions from literal dimensions and the
integer permutation, independently of the fitted values. Fraction squared-error
comparison decides the one-native-pixel bound; floating display values do not gate
it. It is a full-rectangle oracle only for this known plant, not a justification
for extrapolating a real fit beyond its landmarks.

The +2-native-pixel mutation is 0.25 coarse pixel. Require actual corner rejection,
not merely a changed map or a fabricated RMS value. A baseline within one pixel
does not by itself logically guarantee rejection after +2: a baseline exactly
one pixel in the opposite direction can land on the accepted boundary. The
proposed actual assertion correctly resolves that case; a nonrejecting mutation
must stop the run. Do not assume its result from the planted displacement.

The missing-centre arm also changes match-coordinate digests and hence can change
the alternating fit/holdout split. Requiring an actual returned map that fails the
correct corner oracle is conservative and valid; a registration exception is not
powered evidence of the centre error. Restoring the lift must restore the actual
canonical signature and corner results. Off/count/placebo hash equality checks
the observer on the same pair; it does not validate real-image geometry.

## Runtime and interpretation conditions

Prototype imports only standard-library helpers and receives pinned numerical
objects from its future runner. Actual decode/lifetime, partial-control retention,
source/plan rechecks, bounded Job, carry arithmetic and exact call totals are not
implemented here, so they cannot be cleared by this prototype review. The runner
must select the existing fixture by its frozen FileRef, keep only bounded native
fixture buffers for the integer rotation, and release real native RGB before SIFT.
No TIFF/snapshot write is needed. Actual peak memory remains unmeasured, subject
to the existing 8 GiB limit rather than an estimate from this source.

The same 23 directed pairs and cached native records are the baseline. Descriptor
keys stay coarse; matching coordinates are native. Because hashes include those
coordinates, retaining the frozen splitter does not retain the old split or even
the same capped match subset. Record that intended difference explicitly.

Exact site groups and bounding boxes are descriptive. Near-coincident sites can
still cross splits even with an empty exact intersection; multiple orientations,
spatial independence and whole-frame coverage are not established by counts.
Neither a returned fit nor a connected graph establishes per-frame merge placement.
No graph solve, quality metric or SOTA promotion is cleared by this review.
