# M194e prospective numerical amendment1: geometric radial-crossing ladder

2026-09-07. Proposal before implementation of the amendment. Original model
source `a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8`
and numerical source `2320d2a24a8678da7d50795662bb34b54a41c5200abdc8d111d9457c86d599a5`
remain preserved. Root review and commit are required before changing the
integrator. The physical equation, intended scene, independent alternatives,
all accuracy bars, quadrature orders, adaptive depths and work/time/storage
ceilings are unchanged.

## Observed limitation, not an omitted failure

The first independent API run stops at the transformed affine cell. The
separate continue-through-refusals map checks all340 registered cases:170/170
points return within tolerance;56/170 cells refuse at angular depth10, and
all284 returned results meet their applicable comparison bars. This is
`UNCOMMISSIONED_NUMERICS`, not a successful subset. The original method has
not generated or commissioned the intended complete five-frame set.

`angle-diagnosis-1/result.json` records the exact first failing node. At native
`(37.205640692083165,24.129460847876985)`, mask height is
`-0.00018694746088954162` and pupil-projected radius3.07989. The unit-circle
crossing is only0.0000606993954 radians from a normal-projection zero. All
registered crossings are present. After10 midpoint bisections, the adjacent
interval is still0.00306784302 radians wide; its16/32 difference is
0.00005016477e against its allocated0.0000001220656e budget. Near the focused
edge, radial visibility changes on angular scale `abs(h)/radius`; the original
long-interval bisection does not necessarily resolve this boundary layer within
depth10. No disagreement with the geometric equation is established.

## One deterministic change

Keep the same exact radial primitive and angular16/32 (refined32/64) integration.
For each partial-visibility point define `eta=abs(h)/radius`. In addition to
the existing projection-zero and unit-circle crossings, add angular crossings
where the foreground boundary meets each **fixed radial level**
`r_j=2^(-j), j=1..32`, but only when `0<eta<r_j`. The same fixed ladder applies
to every arm and scene; it is independent of observed radiance, quadrature
error, selected pixels or previous failures. No sweep selects its length.

Solve these crossings as angular distances `asin(eta/r_j)` from the relevant
normal-perpendicular direction, with side set by the sign of h. Use the same
periodic interval as before. The unit-circle crossing is the j0 case. Clamp
only the ratio to its mathematical interval[0,1] against floating rounding;
do not snap nonzero h to zero or discard a nonzero radial domain. Sort and
deduplicate **exactly equal represented angular endpoints**; zero-width
intervals contribute zero. If a positive-width interval cannot be bisected to
a distinct floating midpoint while still missing its budget, refuse rather
than accepting it. Fully visible/hidden domains still use one interval.

Compute the point's mask height once from its inverse-mapped chief ray and
reuse that exact value for both cuts and radial crossings. This prevents two
algebraically equivalent floating evaluations from placing the same boundary
on different sides near zero; it does not change the equation or add a
geometric tolerance. h exactly zero needs only projection-zero intervals.

The fixed32-level limit is finite. It spaces crossings geometrically down to
radius2^-32, rather than allowing data-driven insertion without a bound. It
does not license dropping the remaining radius or its error: the original
adaptive comparison still evaluates each complete interval, and can still
refuse at its unchanged depth/error ceiling. Each interval receives its
length-proportional share of the original point tolerance. All positive cell
weights and weighted low/high pupil-error propagation remain unchanged.

## Feasibility under the existing work ceiling

`amendment-work-count.py` was run before changing numerical code:

```text
python -X utf8 experiments/m194e-joint-pupil/amendment-work-count.py experiments/m194e-joint-pupil/amendment-work-count-2
```

It evaluates only fixed cell clipping, Gauss positions and proposed cut counts;
it evaluates no radiance or numerical pupil integral. The retained source-bound
`amendment-work-count-2/result.json` counts every nominal low/high cell node of
all five frames in all three arms. The maximum nominal counts per frame are:

| Arm | Point calls | Proposed angular nodes | Ceiling remaining |
|---|---:|---:|---:|
| Primary |518240|55707072|544292928|
| Angle-refined |518240|111414144|488585856|
| Cell-refined |2072960|223782048|376217952|

Count1 is retained as the first algebraically equivalent native-mask-height
calculation. Count2 uses the same inverse-chief-ray height expression proposed
for cuts and radial evaluation. Every resulting count is identical. Both
directories contain their exact counter/model/render sources, checked against
the hashes in their respective original result records.

All fit the unchanged4m-point/600m-angular-node ceilings **before adaptation**.
The largest encountered nominal point has50 intervals; the finite worst case
is at most68 (original4 plus64 additional crossings). Per-node batching still
caps32768 evaluated point/angle pairs, independently of interval count. These
are geometry-derived operation counts, not measured runtime or a guarantee
that adaptation,600CPU/1200wall seconds or32MiB tracked arrays will pass.

## Falsifiers and execution order

1. Preserve the original source, first API refusal,340-case map and detailed
   diagnosis. Re-run the same failed affine cell and complete independent
   API/control set on the new source, with no reduced domain.
2. Add author geometry-only checks that the exact diagnosed point has its
   registered radial crossings, and that constant/DC, sign symmetry and
   identity cases are unchanged within their original accuracy bars. A
   deliberately removed ladder must retain the original refusal on the
   archived method; it is a limitation control, not a candidate passing arm.
   Also run a test-only common-height/no-ladder ablation on that fixed cell:
   this separates the added ladder from the simultaneous equivalent-expression
   consistency change. If it unexpectedly resolves the refusal, report that
   result and do not attribute the improvement uniquely to the ladder.
3. The independent reviewer reuses its already commissioned Cartesian method
   and re-chosen cases. Any new refusal or discrepant returned value remains
   visible. No observer/source-change mismatch is a numerical pass.
4. Run all five intended frames in each of primary, separate angle refinement
   and separate cell refinement. Compare every pixel and the original edge
   band with the same independent refined arrays and unchanged error bars.
   The first intended frame set will be from the amended source; all three
   arms must complete, with no acceptance based on a more favorable arm.
5. CFA emission still requires the genuine external float/model commission.
   A failure at any unchanged resource or accuracy bar withholds it. No
   product, camera, quality, calibration, default or SOTA claim follows.
