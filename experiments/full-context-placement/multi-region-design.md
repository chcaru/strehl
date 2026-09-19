# At most four disjoint local placement supports

Status: proposed, not implemented. This document inspects the existing consumer
only. The next-scene transfer result should decide whether to implement it.

The smallest extension is a wrapper around the existing single-region
configuration and prepared patch. Keep the version-1 parser,
`prepare_with_config`, `Configuration::weight_at` and `Prepared::apply` intact.
The direct-plane integration continues to call one `prepare` and one `apply`;
the returned value can contain a short list of the current `Prepared` values.
This avoids changing the tested CFA, CA, sampling and rounded-store arithmetic.

## Schema and compatibility

Continue accepting the current version-1 JSON unchanged. Add version 2 only as
an envelope:

```json
{
  "schema_version": 2,
  "regions": [
    {
      "id": "pale-circuit",
      "anchor_file": "DSC00150.ARW",
      "configuration": "THE COMPLETE EXISTING VERSION-1 OBJECT GOES HERE"
    }
  ]
}
```

The placeholder denotes an object, not a runtime string. Repeating the small
stack header in up to four objects is intentional: each object is accepted by
the unchanged version-1 parser and can be run by the current binary on its own.
No sidecar files or new feature flags are necessary. Parse the envelope with
unknown fields denied, then pass each embedded object through the current
`Configuration::from_json`.

The envelope must contain one to four regions, unique nonempty IDs, and exactly
the same canonical source directory, full native geometry and expected frame
count in all regions. Each region independently binds its configured frames to
the original global-map transform bits. A file may occur in several regions,
with different deltas; its original transform bits must still match the same
map. An anchor must name an existing entry in that region, with exact zero
delta. A malformed region refuses the complete configuration rather than
silently dropping that region.

A version-1 document becomes a one-element runtime wrapper. Its existing
validation, weighting, sample order, patch bounds and conversion operations stay
unchanged. In particular, no extra resampling or summation appears in the
single-region case. Preserve the explicit `prepare_with_config` API so the
existing independent controls need no fixture migration.

## Overlap policy

Reject any intersection of destination support rectangles, even if an overlap
would currently contain only zero entries or zero taper weights. Use integer
half-open rectangles `[x, x+w) x [y, y+h)` and the ordinary strict intersection
test on both axes. Touching half-open rectangles are allowed; they contain no
shared destination CFA site. The taper retains its present first/last-site
zero convention inside each rectangle.

This makes region order irrelevant at the gather output. There is no averaging
of displacement estimates, nearest-region selection, blended image, or hidden
precedence rule. Source stencils may overlap: reading the same immutable CFA
samples is valid and needs no conflict resolution.

Do not combine distant source bounding boxes into one enormous patch. Prepare
up to four small coordinate lists, then reconstruct each current unaligned
patch in turn. This preserves a one-patch RGB working set. The actual frame and
synthetic probe both traverse the same region list through the existing direct
entry point. No additional RAW decode or full-image GPU gather is needed.

The current `Prepared::apply` validates all computed values before modifying
its region. Sequential application preserves that per-region guarantee; a
later unexpected reconstruction failure still aborts the render, with no final
TIFF written by the consumer. Configuration, stack identity and stencil support
must be validated for every region before the base gather modifies planes.
If whole-group in-memory transactional assignment becomes a separate
requirement, factor out value evaluation and retain up to four small value
vectors before assignment. That is not necessary to establish the proposed
image comparison and should not be bundled into this extension.

## Independent local anchors and a common coordinate gauge

Each region may choose its own locally focused source frame and its own small
set of neighbouring frames. Fits must be direct to that region's fixed anchor;
they must not compose consecutive displacements. A given frame can therefore
receive different local corrections in two disjoint parts of the photograph.

The consumer still reads one fixed global reference grid. For a native
reference site `p`, let `T_k(p)` be the existing global map's source-native
coordinate for frame `k`. A region anchored at frame `r` fits frame `k` against
the anchor values sampled at `T_r(p)`, while varying only
`T_k(p) + delta_k`. Set `delta_r = 0`. This fixes each region to the anchor's
*existing placement in the original global map*. A nonidentity anchor is valid;
pretending its sensor pixels are already reference-grid pixels is not.

Consequently, pairwise translations estimated in the anchor's sensor grid
cannot be copied directly into this JSON without transforming their sampling
coordinates into the original map's reference grid. Different per-frame
anchors within one support would introduce another gauge problem; do not add
that freedom in this bounded extension. One fixed anchor per support is enough
to test four local regions while keeping each frame fit independent.

Anchor choice does not prove absolute placement. It leaves that anchor's
original local error intact and corrects only inconsistency relative to it.
Frozen focus windows, the existing fit/validation split and independently
examined photographs remain necessary. A lower residual alone does not select
an accepted correction, and search-bound hits keep the existing fallback.

## Exact implementation locations

All substantive changes can stay in
`experiments/full-context-placement/implementation.rs`:

| Current location | Proposed change |
| --- | --- |
| Lines 12–30, current `Configuration` and `Entry` | Leave these single-region structures unchanged; add the envelope/runtime wrapper beside them. |
| Lines 42–79, `Configuration::from_json` | Reuse unchanged for every embedded version-1 object. |
| Lines 93–116, `Configuration::validate_stack` | Reuse for each region. Wrapper adds common-header, anchor and disjoint-support checks. |
| Lines 132–152, cached `configuration()` | Cache the runtime wrapper and dispatch versions 1/2 during parsing. |
| Lines 154–160, `preflight` and `enabled` | Forward over the wrapper; absent environment still returns immediately. |
| Lines 168–241, `Prepared` and `prepare_with_config` | Preserve the current implementation and test seam. |
| Lines 243–255, runtime `prepare` | Resolve CA once, prepare every matching region, and return a small prepared group; absent/zero/outside cases remain absent. |
| Lines 257–290, `Prepared::apply` | Preserve arithmetic; group application invokes it once per nonempty region. |

The direct integration at
`experiments/native-direct-planes/implementation.rs:84` needs no new branch if
the group's method keeps the existing `apply(frame, planes, mode)` signature.
The actual/probe distinction, GPU fallback and confidence reread remain in
their existing owners. These are line references to the inspected source and
will move when the wrapper is added.

## Bounded verification and run

One code change and one build should suffice after the transfer decision.
Retain the existing independent controls and add a small generated group test
covering four disjoint supports, differing frame subsets/anchors, a frame
appearing in two supports, reordered regions, an overlapping negative control,
and a malformed fourth region. Compare version-1 and a one-region version-2
document bit-for-bit. Compare a disjoint group against the corresponding
individual corrected **gather inputs**, and assert unchanged samples outside
the union. This exercises changed routing while reusing the already-tested
numerical kernel. It does not require another algorithm sweep.

For the photographic run, preselect no more than four chip supports, including
the existing pale-circuit support unchanged. Stage only the bounded source
patches needed to fit new regions; bind the same full 299-frame map and output
tone. Make one complete-stack candidate after all regions pass their frozen
fit refusals and independent input checks. Compare with a matched baseline
and inspect both each support and its taper boundary at native scale. Record
the actual run time; do not infer a speedup from the small support sizes.

Full seven-band outputs can interact beyond a support through the pyramid and
the image-wide noise-floor estimate. Therefore unchanged gather samples
outside the union do **not** promise byte-identical final pixels there, and a
multi-region final crop need not equal a separately rendered single-region
crop. The group controls must compare at the gather input; photographs decide
whether downstream interactions are acceptable.

## Remaining blockers

The code wrapper is not the limiting uncertainty. Three things must be settled
before implementation is useful: transfer must justify further investment;
new supports must contain enough common focused structure to fit without
hitting the existing four-pixel limit; and nonreference anchors must be sampled
in the original map's gauge. No new global solve, widened search, overlap
interpolator or reconstruction method is needed for this four-support test.
