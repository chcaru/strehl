# Independent terminal review of numerical component run 1

2026-09-07. **READ/VERIFIED artifact status and file bindings; complete numerical
comparison is not admitted.** This review directly read the terminal JSON
records and catalog. It did not execute an optical helper or rerun either
batch. The independent strict reader and private-control sources are prepared
but had not executed when this note was written; their results must not be
inferred from this source/data review.

The independently re-read file hashes are:

- `author-components-1/result.json`:
  `358aebe2292a8c1aa920763481cae36ce43ebe2d756a5d2e0b8e8fde20fb080e`.
- `independent-reference-components-1/result.json`:
  `514520ee73ea4504be17f0520791c174d11f202c371cd1ce9f6b11a4a8da7b0b`.
- `numerical-components-release-1.json`:
  `99895afd4cd99151708b7fa0e462297a273bd5fceabf205c0228f0bb197847fa`.

Root reports that the source/commands were committed at `98748490` before the
runs, that the actual author process exited 0 and the reference process exited
1, and that the artifacts were committed at `fda7002c`. Those OS exit facts
are attributed to root's collected launch sessions, not independently observed
process exits in this lane. The explicit release contains two actual Python
commands with `-X utf8`, `-X faulthandler` and distinct cache prefixes. It does
not contain `-B`; the reader's unexecuted draft requirement for that additional
flag was removed after reading the actual release. Exact released arguments
and fresh cache provenance are the contract.

## Deciding failure and its scope

The reference record is `UNCOMMISSIONED_REFERENCE_COMPONENTS`, with 300
attempted ordinary rows and 272 returned values. The 28 refusals occur in
both reference arms for these 14 IDs:

`geometry-004`, `geometry-006`, `geometry-011`, `geometry-013`,
`geometry-015`, `geometry-022`, `geometry-060`, `geometry-062`,
`geometry-067`, `geometry-069`, `geometry-071`, `geometry-078`,
`geometry-116`, `geometry-117`.

Each row records the same class of quadrature warning: extremely bad integrand
behavior at points of the integration interval. These rows have no returned
scalar or branch receipt. The actual failed top-level check is
`complete-300-reference-values`, with `{rows:300, values:272}`. The 14 affected
reference-refinement records are also not successful comparisons: one cannot
assign a discrepancy to a missing scalar.

Re-choosing representative input records confirms that this is not merely one
identity-coordinate example counted repeatedly. `geometry-004` uses the
identity tangent map and offset 46.50000000000001; `geometry-060` uses the
scale-two tangent map and offset 20.500000000000004; `geometry-116` and
`geometry-117` use the rotated bracket at offsets 94.46874999999999 and
94.46875. All four retain the declared constant foreground/background fields
15000/9000 e and native location (7,11). These are different registered
representations/edge phases, not 28 independent random observations. The
constant fields do not make the partially visible integral constant.

The failure is not an observed resource-cap crossing. The terminal reference
record reports 120372 integrand evaluations, split into 4788 factor and
115584 chord evaluations, 8.84375 process-CPU seconds, 8.906000000075437 wall
seconds and 24576 tracked explicit ndarray bytes, with no finalization errors.
These are recorded work/elapsed figures, not a throughput comparison or a proof
of full process memory use. The warning proves refusal of the attempted
calculation; this review does not infer a true scalar error or prove the
tiny-topology-interval causal diagnosis from that warning alone.

The passing 52 oracle comparisons and 14 fault groups do not fill those 28
missing reference values. Nor can the author's 299 ordinary values supply its
own missing independent reference. The catalog fixes the complete population;
neither a successful subset nor an analytic interior can release all-image
execution. Any numerical amendment must retain these failed records and be
prospectively released, with the original model, cases and bars still named.

## Author completion and remaining verification

The author terminal record is `PASS_AUTHOR_COMPONENTS`. Its 331 planned and
attempted calls consist of 299 baselines, 15 faults, 15 restored companions and
two cache primes; the zero-over-zero fault is supposed to refuse. Root reports
511 passing author checks and 60 completed observer frame packages. These are
author/source completion facts, not an independent complete-model pass.

The recorded `frames_started` value is 61, not 60: the additional started
frame belongs to the intentional omission/duplicate coverage refusal. Do not
describe that value as 61 completed observer frames. The terminal author work
records 1082883 cumulative points, 270801888 angular nodes, 6832758 tracked
explicit bytes, 79.203125 CPU seconds and 80.25 wall seconds. This is one
component/control batch, not a full 320-by-240 image run or a performance race
against the reference, which uses a different method and did not complete.

The independent reader's fixed design still requires every author
case/arm/method against both complete references, all actual observer payloads,
strict source/array bindings, literal/refinement/fault checks and private
consumer controls. Its first permitted control command will use these real
author files as a valid payload companion and private coherently rehashed
metadata mutations. It will not fabricate a successful reference population.

## Read commands

From the repository root, `Get-FileHash -Algorithm SHA256` was run on the three
files listed above. The terminal records were read with
`Get-Content -Raw | ConvertFrom-Json`; the reference `baseline` was filtered
by `status -eq 'REFUSED'`, and `checks` by `-not $_.passed`. The `budget`,
`finalization_errors`, author `runtime` and selected terminal `work` fields
were read directly. The four named catalog cases were selected by their IDs
from `component-population.json` and read as complete scene/frame/coordinate
records. No source, input array, terminal result or original snapshot was
modified by these reads.
