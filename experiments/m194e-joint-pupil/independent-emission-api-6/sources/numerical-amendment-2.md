# M194e prospective numerical amendment2: tangent-aware cell coordinates

2026-09-07. Proposal before numerical implementation. The source at failure is
model`a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8` and
render`ef52c45d28ec2dda5aa897cfd57dacc4b4a3e300d3a581c35f305c76e2dd03f8`.
Root must review/commit before implementation. Keep the model, fixed intended
and independent scenes, comparison/indicator bars, Gauss orders, adaptive
depths, work/time/storage ceilings and all three arms unchanged.

## New full-run failure

`float-run-1` completes primary frames0,1,2, then terminates
`UNCOMMISSIONED_NUMERICS` at primary frame3, inverse focus.875, pixel(30,4),
after230 completed cells in tile8 order. The partial array, completed arrays,
source snapshots, commands and traceback remain. No full bundle, remaining
frames, refinement arms or CFA authority is claimed. This is a cell-error
refusal, not a runtime overrun; arm CPU was79.25 seconds against600.

`cell-diagnosis-1/result.json` reproduces the frozen failure without numerical
edits. Its depth6 leaf has area.002855699588816. Two vertices lie on the
foreground pupil tangency `h=R=1.51678113121175`, and the third has
`h=1.4579198105110152`. The4/8 cell difference3.8487843738721494e-6e exceeds
the area-proportional allocation2.141774691612002e-6e. Weighted pupil indicators
are only3.06e-15e and4.13e-15e. Thus refining the pupil is not the relevant
intervention. Near a uniform-disc tangency the vanishing cap contribution
has leading normal-distance power3/2; a linear cell coordinate leaves this
fractional-power endpoint in the Gauss integral even after exact clipping.

The independent Cartesian refined value at this complete cell is
15204.412150777305e. It is a diagnostic reference, not permission to accept
the currently refused cell or tune a tolerance to its value.

## One coordinate substitution, with explicit Jacobian

Retain exact clipping by `h=0,-R,+R` and the original triangulation. For
triangles incident to a nonzero-radius pupil tangency, substitute `r=t²`,
with t,u in[0,1]. A is the native area of the triangle:

```text
Tangent EDGE a,b; opposite vertex c:
  p=(1-r)*[(1-u)*a+u*b] + r*c
  Jacobian=4*A*t*(1-t²)

Tangent VERTEX c; other vertices a,b:
  p=(1-r)*c + r*[(1-u)*a+u*b]
  Jacobian=4*A*t³
```

The relevant normal distance becomes t² times a smooth positive factor;
its3/2 power becomes t³. These are ordinary changes of integration variables,
not radiance approximations, blur changes or visible-area renormalization.
Both Jacobians are nonnegative and integrate to A. The constant and affine
polynomial moments fit within the existing4-point one-dimensional Gauss
exactness; no numeric area correction or extra normalization is used.
Neither tangent present: execute the original Duffy rule unchanged. K0/R0
uses the existing focused-mask split, without this pupil-tangency substitution.

Use fixed lexicographic order for the two edge endpoints or the two non-tangent
vertices. Do not choose orientation by computed error. All six vertex
permutations and clockwise/counterclockwise inputs must integrate the same
geometric triangle within the original analytic tolerance; unselected inputs
retain their old arithmetic path rather than gaining an unsolicited reorder.

## A coordinate-map predicate, not geometric snapping

Both substitutions are exact bijections for **any** nondegenerate triangle,
with their stated Jacobians. A near-tangent triangle is therefore safe to map:
a classifier mistake changes convergence/efficiency, not the integration domain
or model. Root identified this distinction during prospective review, allowing
a simpler predicate in place of the first draft's polygon-tag infrastructure.
No native coordinate is moved, no narrow piece is discarded and no area is
renormalized. The existing clipping/triangulation remains unchanged.

For each vertex v use the fixed deterministic roundoff-scale predicate:

```text
h_v = dot(n_native,v)-offset_native
tau_v = 64*float64_epsilon*(abs(n_x*x_v)+abs(n_y*y_v)
                          +abs(offset_native)+R)
candidate for sign s in {-1,+1}: abs(h_v-s*R) <= tau_v
```

The multiplier64 is fixed before candidate evaluation; there is no threshold
sweep or radiance-dependent choice. It is an engineering roundoff allowance,
not a proved bound on every platform's elementary functions. Among signs with
candidates choose the smallest absolute candidate distance, with minus first
on an exact tie. Rank that sign's candidate vertices by distance, then their
lexicographic native coordinates. One candidate selects the vertex map; two
or three candidates use the nearest two as the edge. No candidates selects the
original rule. R0 bypasses the predicate. Recompute this selection on adaptive
child triangles; no provenance object, snap or special midpoint arithmetic is
introduced. Nonfinite predicate quantities refuse.

The h0 split ordinarily makes only one distinct ±R line relevant to a piece,
but even near-coalesced lines or three near-collinear candidates cannot change
the integration domain under this rule. Keep every nonzero-area triangle.
Explicit near-but-not-on controls on both sides of the predicate must validate
constant/affine/Fourier integrals and unchanged coordinates; they must not
claim that near incidence is exact physical tangency. Error/work refusals and
independent complete-array checks remain the actual numerical admission bars.

## Work and evidence requirements

The geometry-only prospective calculation was run without evaluating radiance:

```text
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-cell-work-2 experiments/m194e-joint-pupil/cell-amendment-work-count.py experiments/m194e-joint-pupil/cell-amendment-work-count-2
```

It counts every nominal low/high node for all five frames and all three arms
using the proposed predicate and maps. Tangency substitution changes no triangle or
point count. Primary maxima remain518240 points/55707072 angular nodes;
angle-refined518240/111414144; cell-refined2072960/223782048. Frames0..3 each
have192 vertex-incident triangles and220 or222 edge-incident triangles;
frame4 has neither. The largest nominal point still has50 angular intervals.
`cell-amendment-work-count-2/result.json` and exact source copies bind these
counts. They fit the unchanged4m/600m ceilings before adaptation. They are not
runtime measurements or a guarantee of passing600CPU/1200wall seconds or the
32MiB tracked-array bound. No extra refinement is authorized. The first
tag-based geometry-only count and its exact source remain separately retained;
it generated no radiance or candidate image.

After release, the author must pair the actual corrected map with a test-only
linear-Duffy ablation on the exact failed cell, preserving the original
failure. Constant/affine area and first-moment oracles, positive weights,
permutations, tangent edge/vertex and near-but-not-on incidence decisions, and
unselected byte-null controls must pass. An independently integrated Fourier
triangle and the same point/cell API population must exercise the map beyond
polynomial moments. The independent reviewer may re-choose triangle geometry
and textured controls, but must retain the registered intended full scene.

Then rerun all five primary frames and both complete five-frame refinements
from the new source; do not mix the first run's returned frames into the new
bundle. Compare all pixels and the same edge band with unchanged independent
arrays and budgets. Any new refusal remains visible. No CFA emission follows
without the genuine external float/model commission.

Proposed metadata is `polar-radial-ladder32-tangent-cell-v3`, with cell map
`predicate-square-distance-duffy-v1`. Root owns corresponding schema/contract
updates and adds this amendment to design bindings after release. The author
owns render/controls changes. `model.py` and sensor/ray/scene constants remain
unchanged. This amendment makes no production, quality, default, performance,
calibration or SOTA claim.
