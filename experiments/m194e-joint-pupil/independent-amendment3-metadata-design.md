# M194e amendment3 receipt checks

2026-09-07. Prospective independent input choices after release`2a75e519`,
before executing the new APIs. Root owns schema/emission-contract changes;
Curie owns the allocator and meter; Zeno owns independent numerical/frontier
checks. This lane checks recorded metadata consistency and actual emission
lineage, not whether a forged experiment really occurred. No CFA oracle,
accuracy threshold, scene, noisy quality population or production code changes.

## Contract and independent choice points

The contract adds method`polar-radial-ladder32-tangent-cell-global-v4`,
`cell_allocation=global-absolute-leaf-priority-v1`, and six integer fields:
`cells`, `leaves`, `minimum_depth`, `maximum_depth`,
`locally_overallocated_leaves`, `cells_with_locally_overallocated_leaves`.
Counts describe terminal leaves of completed cells in the current frame.
Local over-allocation is permitted; it is not a numerical or image-quality
admission bar. Whole-cell accuracy belongs to the separate numerical checks.

The helper `validate_cell_allocation(work, full_frame=False)` permits count's
all-zero pre-cell state and off/placebo's all-zero allocation records. A full
intended receipt deliberately requires observer`count` and exactly3072 cells.
An off/placebo full bundle therefore refuses even when its six counters are
correctly zero. Test helper acceptance separately from full-bundle refusal;
do not force a contradictory positive companion through the latter interface.

The first static schema review used source
`378b90c9d40da0a3003188a2cbdc7518c159bbe146475b8bd89bbcd7d193e1b6`.
No new API was run at that revision. Three necessary geometric count relations
were raised before final source freeze:

- Every original unit-square cell partition has at least two positive triangles,
  even without clipping. One leaf at depth0 cannot represent a complete cell.
- A terminal maximum depth must occur. Starting with all leaves at the reported
  minimum depth, reaching a larger maximum requires additional binary splits,
  hence additional leaves. A complete cell with two leaves cannot report depth6.
- Local-overallocation counts within affected cells are bounded by their
  depth-dependent leaf capacity, `8 * 2^maximum_depth` per cell, rather than an
  unconditional512 when maximum depth is smaller.

A fourth static extrema issue was raised against the subsequent source, also
before execution: a reported minimum-depth leaf must actually occur. Relative
to the all-maximum-depth population, one such leaf excludes
`2^(maximum-minimum)-1` descendants. The necessary upper bound is therefore
`8*cells*2^maximum - (2^(maximum-minimum)-1)`. Root accepted the four repairs;
the released schema is
`578f403ed7167c6c0988d927691fa91e5deec7010407f90999e12a0328bbaf8b`.
The lower bound is `2*cells*2^minimum + maximum-minimum`; the affected-cell
bound remains depth dependent. No further metadata requirement is inferred
without a concrete executed falsifier.

These are consistency requirements, not proof of the actual frontier. For
example, aggregate counts cannot identify arbitrary missing/duplicated paths;
the allocator's prefix-free complete-root check and Zeno's fault controls own
that property. No generic per-pixel certificate engine is being added here.

## Positive companions and refusal populations

Use the same helper and then complete private-bundle path where their domains
apply. Work data are explicitly synthetic fixture metadata. Complete input
arrays/gates remain private and ineligible for genuine float authority.

| Choice | Required observation |
| --- | --- |
| Empty observer state | All six zeros passes the helper for count/off/placebo. A nonzero field in an empty/inactive record refuses. |
| Full intended population | Count with3072 cells passes;3071,3073,zero, or an off/placebo full record refuses. |
| Small complete frontier | Three cells, six depth0 leaves, no local over-allocation passes. This gives a non-square-domain-sized helper companion independent of3072. |
| Mixed frontier | Three cells,15 leaves, depths0..2, five local-overallocated leaves across two cells passes. One cell may have two unsplit leaves, one eight depth2 leaves, and one five leaves; this makes both extrema possible. Counts alone do not assert radiance values. |
| Positive diagnostic | Keep a valid positive local-overallocation example in the helper and complete private-bundle tests. Never require that count to be zero. Give the illustrative indicator arrays a nonzero value within the unchanged budgets, rather than pairing positive error diagnostics with an exact-zero indicator. |
| Exact types | Each of the six integers is tested as bool, integral float and negative; missing/unknown fields and non-dict allocation records refuse. No truthy/rounded coercion. |
| Depth/population | Min greater than max, max7, zero leaves with completed cells, fewer than two depth0 leaves for one cell, and two leaves while claiming max6 refuse. Include a live maximum-depth occurrence fault, not only a depth-range check. |
| Capacity | More than eight depth0 leaves in one cell refuses. Declaring a shallow minimum while using the absolute all-depth6 maximum is also impossible because the reported shallow leaf must exist. |
| Affected cells | Affected cells cannot exceed completed cells or overallocated leaves; zero affected cells iff zero overallocated leaves. Overallocated leaves cannot exceed all leaves or the depth-dependent capacity of affected cells. At max0, nine overallocated leaves in a single affected cell is a powered refusal. |
| Rehashed receipts | Update the numerical receipt FileRef, complete bundle and private gate consistently before the metadata test. Separately keep the externally fixed real-authority boundary tests; a stale checksum alone is not this control. |

The helper's valid upper-cap metadata examples are only arithmetic population
controls. They do not assert that this exact scene produces the extremal root
population, that every local error allocation is feasible under the real budget,
or that aggregate counters establish numerical truth.

## Existing controls and final execution sequence

The original109 API expectations remain, with their private receipt constructor
updated to the new counted full-frame contract. Two old mutations must preserve
their intended failure mechanism: the count-with-no-hook case will explicitly
zero the hook count, and the off-observer case will explicitly select off. Merely
setting a baseline that is already count to count would be an inert mutation.
The new helper cases and complete-frame refusals are additive, with their count
reported separately from the original109 population.

Run actual renderer off/count/placebo again on the independently chosen small
non-square scene. Require count's new completed-cell/leaf observations to occur,
all six allocation fields zero in off/placebo, and scalar/indicator byte
identity. Confirm per-frame reset on a second complete small frame; a cumulative
cell total must not masquerade as a current-frame count. Numerical leaf/frontier
state and its admission must still execute in every observer mode.

Only after final six-source/design freeze and the actual new author-control
record are supplied: refresh exact pins/count, run the original plus additive
API controls in a new directory/cache, then refresh final-reader bindings and
repeat its26 controls plus the new relevant allocation corruption through the
complete receipt path. Repeat genuine-CLI refusal of fixture authority. Keep all
earlier source snapshots, failures and results. No genuine CFA verification can
run without externally supplied real manifest and admitted float-gate digests.
