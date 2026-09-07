# M194e prospective numerical amendment4: cell-consumption pupil target

2026-09-07. Design only; no implementation or trial before independent review
and root's committed release. Keep the model, scenes, three complete arms,
maps, quadrature orders/depths, global acceptance and independent comparison
bars, and all resource ceilings. Add a stricter **inner target for pupil
integration consumed by a cell**. Standalone point admission stays unchanged.

## Measured failure and derived allocation

Full3 remains `UNCOMMISSIONED_NUMERICS` on renderer
`a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460`.
It completes five primary, five angle-refined and two cell-refined arrays, then
refuses at cell-refined frame2/(4,0). All complete/partial arrays, source/design
bindings and the diagnostic remain; no complete bundle or authority exists.

`cell-diagnosis-3/result.json`, SHA
`49902496359b6976776bb765e2228b36409d1df2e20bd405a11d8ece1732093f`,
shows two initial roots with spatial absolute-difference sum 9.09e-13 electrons
but weighted low/high pupil sums 0.000149291049/0.000146044296. At the complete
128-leaf depth6 frontier the spatial sum is still only 2.13e-12, while pupil
sums are 0.000146999508/0.000146920607. Their cell indicator 0.000293920117
exceeds the cell-refined cap 0.0001875 although the separate high-pupil cap
0.00025 passes. Covered area is 1; the high value differs from the frozen
independent reference by 1.64e-11. That truth agreement does not admit a failed
indicator or incomplete run. Spatial refinement does not remove this observed
accepted-pupil-indicator floor.

If each cell point's indicator is at most P and positive native-cell weights
sum to area A, its low and high pupil sums are each at most P*A in exact
arithmetic. Their contribution can therefore reach 2P*A before the spatial
difference. The old implementation checks geometric partition area, not
quadrature weight mass; the relative mass guard below is newly proposed.
The original policy allows:

| Arm | Global cell cap C | Point/global high-pupil cap P | 2P/C |
| --- | ---: | ---: | ---: |
| primary | .00075 | .00025 | 2/3 |
| angle-refined | .00075 | .0000625 | 1/6 |
| cell-refined | .0001875 | .00025 | 8/3 |

The last allocation cannot guarantee any space for spatial error. Root and
author independently proposed the same family-wide remedy: reserve half of
the smallest registered cell budget for both pupil terms. Define
`Cmin=.00075/4=.0001875`, and common target `T=Cmin/4=.000046875` electrons.
Primary and cell-refined use T; angle-refined uses T/4=.00001171875. These
numbers are derived from the existing family budgets, not chosen from a sweep
or fitted to the failed pixel. For the tightest cell arm, the exact-arithmetic
inner allocation is half its cell budget. The existing point-indicator slack,
new relative mass tolerance and existing geometric area tolerance give the
derived contribution bound
`2*T*(1+1e-12)*(1+1e-12)*(1+1e-11)`, before finite dot/summation rounding.
The first factor is the existing point admission slack, the second the new
mass allowance, and the third the existing absolute unit-cell area allowance.
This is approximately `Cmin/2*(1+1.2e-11)`, not literally at most `Cmin/2`.
The mass and coverage factors alone are `(1+1e-12)*(1+1e-11)`.
No rounding reserve waives the actual global tests. This derivation does
**not** add a `spatial_difference <= C/2` admission rule: unused inner allowance
can serve the spatial term. The combined cell indicator and separate high-pupil
cap still decide admission. Low/high differences remain heuristic indicators,
not universal error bounds.

## Exact source and metadata contract

Add `Integrator.cell_point_tolerance` with the exact targets above. This is
separate from `pupil_tolerance`, which retains its old role for standalone
points and the cell's separate global high-pupil cap. Primary and cell-refined
must have identical angular orders and cell-consumption point-target policies;
their cell quadrature orders/tolerance alone differ. The angle arm retains its
original angular order refinement and quarters the new inner target as well.
Do not silently make cell refinement an extra pupil-refinement arm.

Expose `render_points(..., *, point_tolerance=None)`. None selects the existing
standalone `integrator.pupil_tolerance`; an explicit target must be positive,
finite and no larger than that cap. Use the resolved target in **both** the
angular interval budget allocation and final summed point-indicator check.
`evaluate_cell_leaf` supplies `integrator.cell_point_tolerance` explicitly for
both its low and high point batches. `render_point` continues using the default
standalone policy, and its value/indicator bytes must remain unchanged.
The historical local-rule helper remains on its historical point policy and
must retain the archived refusal; it is not a new production arm.

Validate the new configuration target as positive and finite. At actual cell
consumption additionally require it not exceed the standalone cap or one quarter
of that arm's cell tolerance; unsupported custom configurations refuse rather
than secretly loosening a target. All frozen family settings satisfy this
condition. For each actually consumed low/high quadrature rule, require a finite
strictly positive geometric triangle area and finite strictly positive weights.
Using `math.fsum`, require finite positive total weight mass and a finite ratio
with `abs(total_weight / triangle_area - 1) <= 1e-12`; otherwise refuse.
This is a new, prospective **relative engineering mass tolerance**, selected
before any trial and independently tested on arbitrary triangle areas. It is
distinct from the unchanged absolute `1e-11` geometric partition allowance.
Never renormalize weights, snap coordinates, or drop nodes/pieces. Tiny normal
or subnormal areas are not exempt: underflow to zero in area or any weight,
nonfinite mass/ratio, or failure of the same relative check refuses. No minimum
area is silently substituted; a representable tiny rule that meets every
positive/finite/relative check remains admissible. Floating dot/summation
rounding still faces the unchanged actual global indicator tests.

The global frontier, absolute-error sum, separate high-pupil cap, priority,
coverage and optional observer remain amendment3's rule. No counter chooses
the target. Root-owned metadata uses method
`polar-radial-ladder32-tangent-cell-global-inner-v5` and adds
`cell_point_policy=family-min-cell-budget-quarter-v1` to the numerical contract.
Every frame's serialized Integrator must contain the actual new field and
target, and source/array/evidence bindings must reject a stale or rehashed
false target. Root updates schema/emission contract; author updates only
render/author controls. `model.py`, emitter and controller arithmetic stay fixed.

## Work feasibility and unchanged refusals

The geometric cuts, initial triangles and low/high cell nodes are unchanged.
Previously registered nominal pre-adaptation maxima remain 55,707,072 primary,
111,414,144 angle and 223,782,048 cell-refined angular nodes per frame. Thus the
unchanged 600-million cap is not contradicted by the compulsory nominal work.
This is a feasibility lower bound, not an adaptive upper bound or timing claim.
Full3's first cell-refined frame used 300,757,152 nodes under the old target;
that is historical work only and does not predict the new target's cost.

Tighter inner targets may trigger more angular subdivision, while lower pupil
indicators may reduce unnecessary spatial subdivision. Neither effect is
assumed to dominate. Retain angular depth10, cell depth6, four-million point
and 600-million angular-node limits at their existing scopes; retain32MiB
tracked arrays,32768 node pairs,600 CPU/1200wall seconds per five-frame arm.
The complete new run may still refuse at those unchanged limits. No extra
resource headroom, order, partial frame or selected-point replacement is granted.

## Falsifiers and execution after release

On the exact (4,0), frame2 cell-refined case, retain the original global-rule
refusal as historical evidence. The amended cell must return within the same
global/independent bars, with separately reported spatial and pupil terms.
Trace the actual low/high point-call arguments to prove the new target reaches
both consuming batches. A test-only omission/stale-target mutant must recreate
the floor/refusal or fail the target-binding check. No standalone point result
may silently inherit the new cell-only target.

Check standalone point value/indicator byte identity against the frozen source;
the primary/cell equal-target relationship; angle quarter-target relationship;
negative/zero/NaN/infinite or too-large target refusals; missing target on one
batch; and finite positive unit and re-chosen non-unit/native-area quadrature
mass, including tiny normal/subnormal valid-or-explicit-refusal cases. Power the
relative guard with half-mass and biased-mass faults on small-area triangles
that an absolute `1e-11` rule would incorrectly accept. Zero/negative/nonfinite
weights, nonpositive/nonfinite area, and false target metadata must be rejected
or fail the matching independent arithmetic control. Include valid arbitrary-area
companions and actual inner
subdivision/refusal power, not only field-value equality assertions. The
independent verifier re-chooses analytic points and target/mass/metadata faults.

Repeat all registered analytic/textured, map, global allocation and powered
observer/traversal controls on the new source, with actual scalar+indicator
byte nulls and disabled off/placebo statistics. Rebind the strict emission
boundary and independent final reader before any intended array generation.

Regenerate all15 primary/angle/cell arrays from the new frozen source, with no
reuse of full3's twelve returned frames. Keep full/edge max.004e/RMS.0008e,
separate author refinement max.001e and independent refinement max.0005e.
Every failure remains visible. Genuine CFA emission still requires the complete
independent float gate. No physical, noise-calibration, product-quality,
performance, default-promotion or SOTA claim follows from this numerical target.
