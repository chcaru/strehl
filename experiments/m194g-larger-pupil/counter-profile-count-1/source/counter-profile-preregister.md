# Counter-only diagnostic after intended cost refusal1

2026-09-07, root. Prospective implementation/execution release. This accepts the
independent recommendation in independent-cost-next-action.md. Preserve
preflight-1 as UNCOMMISSIONED_COST; no intended rerun or radiance is released.

Run one fixed private9×6 population from independent-preflight-controls-design.md:
F15000, B12000, depths(1,2), normal(1,.25), offset2, half-plane; similarity
scale2, rotation0, centre(.5,-.5), translation(1.25,-.75); K2, original indices0..4,
inverse foci(.5,.75,1,1.25,1.5); all primary/angle-refined/cell-refined arms.
Use the unchanged checked source preflight.py at
829669612359e5f60a1610fbc36604eb4cef5647911df604124de9e13160b485,
geometry.py at24b812071b8b6189423b9792a22c55abd9a4f4a78921a9d558ab24489f1923b3,
and pinned-loader.py at222fab4a932fe236c120d8a48e4521747474e2ef57ba58781bf5c59f644f4f76.
The original frozen M194e source pins remain unchanged.

Execute off, count and placebo once each in that order, in fresh processes and
fresh cache directories. Off constructs no profiler; count uses cProfile around
the actual count_geometry call; placebo constructs the same profiler but leaves
collection disabled. Each has one10-CPU/20-wall-second budget beginning before
imports/setup, the same strict8-million-point/1.2-billion-node per-frame limits
and32MiB tracked-array scope. No change to time checks inside the counter. A
failure remains partial and ends this diagnostic; do not raise its budget.

Retain complete profile data/function table and source snapshots, exact original
arguments, input records, complete per-row counts, geometry stream digest and
resource receipts. cProfile perturbs runtime; its enabled timings attribute the
instrumented private execution and are not an unprofiled speed estimate. No
alternating timing sweep or speed comparison is intended. Private support need
not represent the intended320×240 cost distribution.

Write a deterministic payload containing all geometry/count/coverage results,
excluding timing, mode, profiler/hook receipts and resource-observer counts.
Require its byte hash and ordered geometry digest to agree across all three
modes. Collection must actually reach count_geometry, point_cuts, angular_cuts,
_stream and Budget.check in count mode; placebo must instantiate the profiler
and yield no collected calls. Existing radiance entry-point traps must be active
and prove no radiance was called. Demonstrate the traps using a separately
labelled intentional direct trap call; do not infer liveness from zero calls.

Power payload/digest comparison with one fourth fresh private execution under
the same separate10CPU/20wall budget: alter one actual angular-cut partition
at the first multi-interval point by removing one interior cut, preserving a
valid sorted partition. Assert the mutation occurs, output work or stream
payload differs, and equality comparison rejects it. The mutation never enters
the full preflight or any original source file. A missing multi-interval witness
or unchanged payload fails commissioning. Preserve failure output and timings.

Freeze diagnostic harness source and command before execution. Independent
review must read every mode's complete population/status/source bindings,
invariant payload and profiler liveness, not merely the author's summary.
After this single diagnostic choose one narrow source-local bookkeeping change
if justified, or a prospectively registered counter-only time allowance.
Do not open a parameter search or substitute inferred counts for actual cuts.
No geometry, model, coverage, work/storage or later float accuracy bar changes.
