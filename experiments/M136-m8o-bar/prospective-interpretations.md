# M136 prospective interpretations: fixture representation and green reduction

**Status:** prospective ambiguity resolution, not a bar amendment
**Written:** 2026-09-04T04:24:45-07:00
**Pre-interpretation repository HEAD:** `67136b7cd32b606be53c767b10aff720b49d4fac`
**Target result at time of writing:** `UNMEASURED`

## 0. Scope and prospective freeze

- **[INHERITED]** M142 stopped before reading or producing a target verdict and
  referred two ambiguities to M136. This document resolves only those
  ambiguities.
- **[VERIFIED]** Before writing this document, a filename-only inspection of
  `experiments/M136-m8o-bar/out/` found no top-level artifact whose name
  contained `m8-o`, `result`, or `state`, and no clamped TIFF. No target TIFF,
  trace block, checker result, or candidate violation count was opened or
  computed by M136.
- **[VERIFIED]** The mechanical rule-40 search
  `python experiments\ORCH-drift-check\prior_art.py "M8-O source hull verifier green G1 G2 representation"`
  returned `NO PRIOR REPORTS. This subject appears genuinely unasked.`
- **[VERIFIED]** The frozen decision remains: “PASS iff every capture has V=0
  and aggregate V=0,” while “FAIL iff aggregate V>=1,” and `V=40` is explicitly
  a failure
  (`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:88-90`).

These interpretations do **not** change the coordinate population, denominator,
per-frame source tolerance, final quantisation tolerance, or decision rule.
They define two operations that the frozen text already requires but did not
specify completely.

## 1. Ruling 1: the eight numeric cases use a fixture-only identity map

### Binding ruling

**[VERIFIED]** The eight entries under `m8_o_numeric_cases` are direct controls
of interval projection and final-code comparison in the normalized,
pre-final-saturation domain. For these eight fixtures only:

1. Interpret the supplied interval as
   `I_fixture = [lo - tau, hi + tau]`.
2. Define the fixture representation map as the identity,
   `P_fixture(z) = z`.
3. Define `F_fixture(z) = clamp(z, 0, 1)`.
4. Therefore
   `L = clamp(lo - tau, 0, 1)` and
   `H = clamp(hi + tau, 0, 1)`.
5. Decode `O = encoded / 65535` and classify a violation exactly when
   `O < L - 1/131070` or `O > H + 1/131070`.

The implementer **must not invent** `g`, `b`, `G`, or `R` for these eight
fixtures and must not send them through the native intermediate-u16 path.
Their omitted representation fields are inapplicable, not defaulted.

### Why this is the unique interpretation supported by the originating code

**[VERIFIED]** The function that generated these cases sets
`projected_lo = min(max(lo, 0.0), 1.0)` and the corresponding projected high
bound, then compares `encoded / 65535` directly against those bounds
(`experiments/M136-m8o-bar/analyze.py:88-99`). It defines the above-one and
below-zero controls with no native representation parameters
(`experiments/M136-m8o-bar/analyze.py:101-111`). That is an explicit direct
normalized-domain fixture, not an underspecified invocation of the target
arithmetic.

**[VERIFIED]** The native integer path has its own separately specified
`intermediate_quantizer_case`, including `g=2`, `b=512`, `G=2`, and `R=16384`
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:190-202`). That
case, every target trace, and no other numeric case exercise the nontrivial
native representation map.

**[ASSUMED]** An implementer could construct a numerically identity-equivalent
native parameter tuple, but doing so would add a contract the fixture never
contained and would make the controls depend on irrelevant arithmetic. It is
therefore non-normative and must not be used.

## 2. Ruling 2: combine G1 and G2 within each frame before reducing frames

### Binding ruling

**[VERIFIED]** For compact coordinate `(x,y)`, pair G1 and G2 by the same
`frame_order`, the same full-plane coordinate
`(X,Y)=(x+crop_x,y+crop_y)`, and their fixed CFA sites:

- G1 is site `(1,0)`.
- G2 is site `(0,1)`.

For each frame `k`:

1. Independently reconstruct each site’s source interval
   `I_k,s=[lo_k,s-tau_R,k,s, hi_k,s+tau_R,k,s]`.
2. Replay each site’s recorded intermediate-u16 path and black removal, but not
   the final output gain, to obtain non-negative intervals
   `A_k,G1` and `A_k,G2`.
3. Form the same-frame green interval, using the candidate’s recorded f32
   operation order and outward interval rounding:

   `B_k,G = max(0.5 * (A_k,G1 + A_k,G2), 0)`.

4. Apply that frame’s common recorded green output gain `G_G` and sensor range
   `R_k`, then the final representable-domain projection:

   `J_k,G = clamp(B_k,G * G_G / R_k, 0, 1)`.

5. Only after step 4 reduce across frames:

   `L_G = min_k inf(J_k,G)` and
   `H_G = max_k sup(J_k,G)`.

The verifier must reject the measurement as `UNMEASURED` if either green site
is missing or duplicated for a frame/coordinate, or if paired blocks disagree
on frame identity, geometry, crop, black level, sensor range, or green output
gain.

It is forbidden to reduce G1 and G2 independently over frames and then average
their extrema. That operation can pair G1 from frame `a` with G2 from frame
`b`, creating an interval no frame supplied. Treating `(frame,site)` as the
frozen text’s frame index `k` is forbidden for the same reason.

### Why this follows the merge rather than the desired verdict

**[VERIFIED]** The Pyramid path constructs each frame’s election luma as
`0.5 * (planes[1][i] + planes[2][i])`
(`crates/strehl-cli/src/merge_cmd.rs:4964-4971`).

**[VERIFIED]** `BandMerge` has one denominator “shared by every plane” because
selection is made on green luma
(`crates/strehl-core/src/pyramid.rs:1314-1324`). During accumulation, the same
`w[i]` is applied to every colour plane
(`crates/strehl-core/src/pyramid.rs:1776-1820`), and fallback selection is
decided once and replayed into every plane
(`crates/strehl-core/src/pyramid.rs:1838-1900`). The regression test
`the_selection_is_shared_across_planes` asserts that invariant
(`crates/strehl-core/src/pyramid.rs:3553-3579`).

**[VERIFIED]** Serialization then computes the output green as the same-pixel
mean of the merged G1 and G2 planes, with the post-mean non-negative clamp
(`crates/strehl-cli/src/merge_cmd.rs:4724-4735`), and passes that single green
value through the common green gain/range encoder
(`crates/strehl-cli/src/merge_cmd.rs:7567-7579`).

Because the merge preserves frame identity across the two green planes, the
source-support certificate must preserve that pairing too. Independent
sitewise extrema are a wider outer bound and can suppress a real M8-O
violation; same-frame reduction is therefore the interpretation that preserves
what a zero-violation pass licenses.

## 3. Unchanged pass licence

**[VERIFIED]** Before and after these interpretations, an M8-O pass licenses
the same claim: at every eligible final `(capture,x,y,R/G/B)` coordinate, the
decoded u16 output lies, within exactly half a final-u16 code, inside the union
of source-supported values that at least one real contributing frame could
produce through the candidate’s recorded representation path.

The fixture ruling changes no target coordinate. The green ruling prevents a
certificate from widening that union with a synthetic cross-frame G1/G2 pair.
Neither ruling can turn a non-zero valid target count into a pass because the
decision remains `V=0`.

## 4. Could not determine before target execution

- The target violation count and verdict remain `UNMEASURED`.
- Whether the post-M130 candidate produces any representation, crop, or
  frame/site inconsistency cannot be known until its trace-v3 evidence exists.
- The future target result cannot be inferred from these interpretations or
  from the commissioning fixtures.
