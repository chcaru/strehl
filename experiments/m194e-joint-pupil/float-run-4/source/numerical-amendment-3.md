# M194e prospective numerical amendment3: whole-cell error allocation

2026-09-07. Design only until root commits and releases it after independent
review. Replace the registered **per-leaf area-proportional allocation**, not
the whole-cell accuracy requirement. Keep the model, fixed scenes, all three
accuracy arms, quadrature rules/maps/orders, depth ceilings, independent arrays,
comparison bars and work/time/storage caps unchanged.
Low/high quadrature differences remain numerical indicators, not a rigorous
universal error bound. Independent full-array comparisons remain decisive.

## Evidence and boundary

`float-run-2` is terminal `UNCOMMISSIONED_NUMERICS`, source render
`a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5`.
It completes primary frames 0–2 and refuses at frame 3/cell (31,7), after
255 cells. The depth-6 mapped leaf's difference 3.44316831757e-6 electrons
exceeds its area-proportional allocation 3.17449881569e-6. No other frames,
refinements, complete bundle or CFA authority were produced. This failure and
its source snapshots remain; the proposed method does not retroactively pass it.

Root's diagnostic request was executed in `cell-allocation-2/result.json`, SHA
`5b4932da5b6807e3746dab7c8a4c02ad7cea8f899d08c61bbb4e4c5d01f48291`.
All 508 nodes through depth 6 are retained. The original local stopping leaves,
including the depth-6 failure, have aggregate absolute-difference-plus-pupil
indicator 8.85677475546e-5 and separate high-pupil sum 1.46237557330e-6.
Both meet the existing whole-cell limits. Initial roots instead total
0.0208828601 and fail. A diagnostic priority sequence reaches the same limits
after 14 splits/18 leaves. These are one-cell diagnostics, not a general success
or performance prediction. The initial diagnostic JSON serialization failure
and exact source are retained in `cell-allocation-1`.

## Exact proposed rule

Initialize **all** original clipped-cell triangles in their original order.
Evaluate each with the unchanged tangent predicate, Duffy rule, low/high orders,
and angular integrator. A leaf stores its native triangle, depth, immutable
path `(root_index, child_bits)`, low/high integrals, and the separately weighted
low/high pupil error indicators. Define:

```text
delta_l = abs(Qhigh_l - Qlow_l)
e_l     = delta_l + pupil_low_l + pupil_high_l
Ecell   = fsum(e_l for every current disjoint leaf l)
Pupil   = fsum(pupil_high_l for every current disjoint leaf l)
Value   = fsum(Qhigh_l for every current disjoint leaf l)
```

Enumerate leaves in ascending root-index/binary-child-path order for every
sum; use `math.fsum`, never signed cancellation, a parent alongside children,
or an incremental subtract/add total. The reported final indicator remains
`Ecell + Pupil`, as in the registered contract. Check finite low/high values,
nonnegative finite error terms, and finite totals before comparisons.

Return only if `Ecell <= cell_tolerance` **and**
`Pupil <= pupil_tolerance`. The existing 1e-11 partition-area allowance remains
a separate geometry check. Primary limits remain 0.00075/0.00025 electrons;
angle refinement divides its pupil tolerance by 4, cell refinement divides
its cell tolerance by 4. Do not replace these by a single combined allowance.

Otherwise choose the largest `e_l` among leaves with depth below the original
ceiling 6. Break exact ties by the canonical path. Split that leaf along its
original longest native edge, using the original `np.argmax` tie and midpoint
arithmetic. Replace the parent with **both** children in the frontier; evaluate
both before the next total/admission check. Use the existing mapped triangle
rule on every child, including its unchanged tangency predicate. A depth-6
leaf stays in every total; it is never dropped because it cannot be refined.
If the total remains unacceptable and no leaf can be refined, refuse. Existing
point/angular/depth/time/storage guards remain fail-capable and authoritative.
No new fallback accepts an exhausted or partly evaluated frontier.

The old `e_l <= cell_tolerance*area_l` condition becomes a diagnostic only.
Record failures of that condition, including depth-6 cases; they do not select
leaves, allocate tolerance or decide admission under this proposed method.

## Coverage, bounds and source integration

The internal roots remain the existing exact clipped-cell partition. Keep the
positive-area and complete-cell area check. Each split constructs the same two
triangles with its shared midpoint: they cover the parent and have disjoint
interiors. Verify the active frontier is prefix-free and complete for every
root: with maximum depth 6, each path contributes integer weight
`2**(6-depth)` and every root must sum to 64. This check rejects a missing
child, duplicate path, missing root or a parent retained with a child. Check
the canonical positive leaf areas sum to the original cell area within the
existing 1e-11 allowance. The geometric construction and independent component
controls, not area alone, establish actual child coverage.

No pupil or cell sample arrays are retained in the queue. Keep only leaf
triangle coordinates and scalar quadrature/error metadata; point arrays expire
after each evaluation. At most eight roots arise from three parallel clipping
lines of a unit square, giving at most 512 active depth-6 leaves. The triangle
storage alone is at most 512*6*8 = 24,576 bytes, separate from Python object
overhead. Track these retained ndarray coordinates with the existing monitor;
the registered 32 MiB bound remains a tracked-array bound, not an RSS claim.
Keep the four-million point, 600-million angular-node, 600 CPU-second and
1200 wall-second limits at their existing scopes. Nominal pre-adaptation work
is unchanged from amendment2; adaptive cost/success is unknown until the run.

Changes are confined to `render.py` and `author-controls.py`; `model.py` stays
unchanged. Root owns schema/emission-contract updates. Proposed method string:
`polar-radial-ladder32-tangent-cell-global-v4`; retain
`cell_map=predicate-square-distance-duffy-v1`, and add
`cell_allocation=global-absolute-leaf-priority-v1` to the numerical contract.

Persist `work.cell_allocation` with exact integer keys `cells`, `leaves`,
`minimum_depth`, `maximum_depth`, `locally_overallocated_leaves`,
`cells_with_locally_overallocated_leaves`. These summarize completed cells in
the current frame and reset in `new_frame`; all six are zero before any cell
completes. The minimum/maximum cover terminal leaf depths; counts include every
terminal local over-allocation. Collect only in observer `count`, **after**
numerical acceptance. Off/placebo retain all six zero fields; placebo traverses
the optional observation hook without collection, while off disables that hook.
The native numerical frontier/depth state runs identically in all modes.
Collection cannot affect priority, acceptance or returned values/indicators.
Full intended receipts use count and require `cells==3072` plus bounded statistics;
local-overallocation counts never become an image-quality or admission bar.

## Falsifiers before intended arrays

Retain the exact failed cell and original local-rule refusal. Candidate whole
cell must return within the original independent truth/indicator budgets;
the original initial frontier must still fail its aggregate indicator. Require
all leaves/area and the deterministic split trace to be observable. Also retain
the earlier (30,4) control and the entire original analytic/textured population.
The archived local allocator must retain its actual refusal. Previous test-only
no-tangency-map ablations were failures under that local rule; the global rule
may make those same cells admissible. Record their actual new disposition rather
than requiring an unregistered failure or treating a pass as missing power.
Keep the separately powered fractional-moment/geometric map controls. Do not
infer that every preceding coordinate intervention is necessary for the new
allocation method from its historical local-rule ablation.

Component fault injections must reject signed low/high cancellation that hides
an excessive sum of absolute differences; omission of either weighted pupil
term; a high-pupil sum above its own limit despite a passing cell total; negative
or nonfinite indicator terms; an omitted root/child, duplicated path, overlapping
parent/child frontier, biased area or incorrect geometric split; and ignored
depth or work exhaustion. Pair each with a valid companion. Arithmetic fixtures
with synthetic leaf records are labeled component controls, not optical truth.
The independent verifier re-chooses these faults and geometric/priority ties.

Run actual renderer observer off/count/placebo and powered traversal controls
again, checking both scalar and indicator hashes. Assert count's new allocation
statistics are nonzero and exercised, and all six are zero in off/placebo.
A source/scene mutation must remain live. Rebind author controls, all numerical
APIs, emission boundaries and the independent final reader to the new
sources/schema before intended arrays.

Then regenerate **all five primary plus both complete five-frame refinements**
as a fresh run. Compare every pixel and the same edge band against the frozen
independent reference, with unchanged 0.004e maximum/0.0008e RMS and separate
refinement limits. Any refusal or failed comparison remains visible; no array
from earlier runs substitutes into the new bundle. Genuine CFA emission still
requires independent float authority. This amendment claims no physical
calibration, diffraction fidelity, product improvement, default promotion or SOTA.
