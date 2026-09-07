# Concrete emission interface

2026-09-07. Root owns `schema.py` and `emit-cfa.py`; the numerical author owns
`model.py`, `render.py`, `author-controls.py` and `commission.py`. This closes
receipt details before actual emission/API tests. It does not change the model,
scene, numerical bars or acyclic independent-admission requirement.

The executable closed-key definitions are in `schema.py`. The float package is
`m194e-float-bundle-v1`: schema, status, producer, sensor, scene, ray_model,
numerical_contract, frames, refinements. Status is uncommissioned. Frames are
all five primary records; refinements contains all five angle-refined and all
five cell-refined records. Each record binds its scalar and numerical receipt.
NPY payloads must consume the complete file, have the fixed little-endian float64
shape48×64 and contain finite nonnegative electrons. Integer metadata rejects
booleans and floats; floating model values may be equivalent JSON numbers.

Float producer keys are source_base, sources, designs, command, author_controls.
Sources and author controls resolve from the repository root; design names
resolve from this experiment's source directory. Frame references resolve from
the float-bundle directory. Child references inside a numerical receipt resolve
from that receipt's directory. This last distinction clarifies the earlier
informal blanket description of bundle-relative references and was fixed before
the first API tests. Following numerical amendment3's preregistration at
`2a75e519`, the current numerical contract names
`polar-radial-ladder32-tangent-cell-global-v4`,32 radial crossing levels,
`cell_map: predicate-square-distance-duffy-v1` and
`cell_allocation: global-absolute-leaf-priority-v1`, the three unchanged
integrators and existing whole-cell/pupil/comparison/indicator limits. Design
bindings include all three numerical amendments. The predicate selects a
coordinate map without moving vertices. The new whole-cell allocator explicitly
replaces the former per-leaf proportional admission rule. Earlier source-bound
packages retain their original contract; their results do not commission this
revision.

`work.cell_allocation` has six exact nonnegative-integer fields: cells, leaves,
minimum_depth, maximum_depth, locally_overallocated_leaves and
cells_with_locally_overallocated_leaves. Off/placebo and pre-completion snapshots
have all six zero. Count records completed cells only; full intended frame
receipts require count mode and exactly3072 cells. Depths satisfy0≤min≤max≤6;
the square has at least two root triangles. Complete frontiers and occurrence
of the maximum depth give a lower bound2*cells*2^min+(max-min). The occurrence
of a minimum-depth leaf gives the upper bound8*cells*2^max-(2^(max-min)-1).
Overallocated cells
and leaves must have consistent zero/nonzero counts, with at least one and at
most8*2^max such leaves per affected cell, never more than total cells/leaves.
These are consistency checks on observations, not numerical or quality evidence;
the actual allocator and independent image comparison establish their own
claims. Local proportional over-allocation does not bar admission.

The genuine independent float commission has exact keys schema, status,
author_root, author_bundle, producer_sources, scene, ray_model,
numerical_contract, expected_scalars, numerical_receipts, author_controls,
independent_evidence. Schema is `m194e-float-commission-v1`, status PASS.
expected_scalars/numerical_receipts are keyed0..4 and equal the primary records.
The externally supplied digest binds the entire commission. author_bundle
binds the complete package, including all refinements. Independent evidence
has controls, author_api, reference and comparison repository-relative FileRefs.
The checker is responsible for the meaning of its PASS; self-hashed assertions
are not authentication of an experiment.

author_root records the original repository-relative run location. It is not
a restriction against relocating identical package bytes with unchanged child
paths: author_bundle is resolved from the supplied bundle's current directory.
Repository-relative source/control/evidence references retain their declared
base. The emission API takes absolute bundle/commission paths, a separately
trusted commission digest and a new output directory; input evidence must be
within the repository so the emitted provenance can use that base.

`convert_cfa(scalar, sensor=None)` returns expected-CFA float64 electrons and
little-endian u16 codes. It applies the fixed RGGB factors once, then multiplies
by gain before adding black, in separate float64 operations. Nearest integer
uses ties-to-even. Zero electrons/black512 are valid. Negative/nonfinite values,
unquantized DN at or above15360, or rounding onto15360 refuse. There is no WB,
noise, clipping or optional emission observer. The actual renderer's optional
hook is independently controlled off/count/placebo; `optional_hook_calls` is
zero for off and positive for count/placebo, while only count collects events.

`emit_cfa_bundle(bundle, commission, trusted_sha256, output)` validates authority,
consumes one bound scalar frame at a time and preserves its exact NPY bytes,
indicator and numerical receipt beneath `input/` with the original hierarchy.
It creates one expected-CFA NPY and raw tightly packed u16 CFA per frame. All
source/evidence bindings are checked again before the final manifest is written.
Partial failures retain `EMISSION_REFUSED` diagnostics and no complete manifest.

The emitted manifest has the original eight top-level keys: schema, status,
producer, sensor, scene, ray_model, numerical_contract, frames. Its schema is
`m194e-joint-pupil-v1`, status `float-commissioned-cfa-unverified`. Every frame
contains both expected_cfa and cfa, in addition to original geometry, scalar
and numerical receipt references. Producer retains its five float-stage keys
and adds emission_receipt, an output-relative FileRef to `emission-run.json`.
That receipt binds the repository-relative original float bundle/commission,
separate trusted digest, command/runtime, before/after source bindings and all
five emitted records. It reports `CFA_COMPLETE_AWAITING_INDEPENDENT_REVIEW`;
only a separate independent actual-value check may commission the CFA outputs.

Private fixture PASS records may exercise this boundary but cannot authorize
the final scientific package. Keep their results explicitly fixture-only. No
production bridge or new quality experiment is included.
