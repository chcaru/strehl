# After preflight1: bounded counter diagnosis

2026-09-07, implementation_audit. **Design only; no profile, modified counter or
second full count has run.** This file is outside `source_bindings()`'s bound
Markdown globs. Implementation/profiling needs a prospective root release.

## What the failure establishes

The actual `preflight-1/result.json` is `UNCOMMISSIONED_COST`, SHA
`f23b5b1d24ba3e9516b246dce452c336749a3824c373484018a63c68ba66d010`.
The fixed source and configuration bindings are unchanged. The one global CPU
guard refused at60.015625 seconds, wall60.8280000001, with10 complete frame/arm
rows and821287 complete cells. All primary and angle-refined rows completed;
cell-refined frame0 had53287 completed cells and was working on `(167,166)`.
No full cost admission, radiance or future render permission follows.

At refusal, the counters record5696960 nominal points,2091280512 nominal angular
nodes,8067657 budget checks and91280 peak tracked ndarray bytes. Current-row
work was1780160 points and514394112 angular nodes, below that row's strict work
caps. **No inferred final row count is used:** the actual partial row
records2207 numerical branches entered,5564 roots and maximum50 intervals.
Branches can include the in-progress cell while `visited_cells` counts only
completed cells; do not label their partial totals inconsistent or complete.

This is a counter CPU refusal, not evidence that numerical rendering exceeds
its separate work budget. Completed primary row0 had641280 points and
184139136 nominal nodes; cell-refined uses different8/16 cell rules and cannot
be extrapolated by treating completed-cell fraction as uniform cost. Nor can
two identical sets of cut counts be called two independent confirmations:
primary/angle share cell geometry while their angular orders differ.

## Likely overhead, explicitly ARGUED

Source inspection identifies these candidates, not measured time shares:

1. Each point creates a dictionary in `point_cuts`, then a second merged
   dictionary in `count_geometry`. `_stream` repeatedly encodes the same arm,
   constructs a cut-count-dependent `struct` format and packs small byte strings.
   This occurs millions of times even with no external sink.
2. Every point node charge invokes both OS-backed CPU/wall clocks and several
   invariant checks. The8067657 observed check calls show that this is exercised;
   they do not establish that it dominates60 seconds.
3. The required frozen `angular_cuts` implementation computes signed geometric
   ladder angles for each actual low/high point; point cut validation then scans
   every returned interval again. Changing that geometry is not a free counter
   optimization and is excluded from the first repair.
4. Per-cell exact-integer selector guards, root/rule construction, unique-array
   bookkeeping and row-wise durable progress serialization also consume CPU.
   There are no category timings to rank these contributors. The near-equal
   CPU/wall totals do not identify any one function or justify a disk fix.

## Proposed private profile, before selecting a code change

Use a new diagnostic file under a separately owned `work/counter-profile-*`
directory, loading the exact frozen loader/geometry/preflight and M194e bytes
from snapshots. Do not edit or import an unbound candidate first. The fixed
private population is320×4 native cells, all five original fixed frames and all
three arms, with the registered scene/coordinates unchanged:19200 cells. This
retains far foreground/background, boundary cells, negative/zero defocus, both
cell orders and all angular orders. Add one explicit full-mask320×4, frame0,
primary arm only for the analytic-only path. Neither population is intended
full-image admission; no radiance method may be called.

Run that same private population with profiling off, `cProfile` enabled, and
a no-collection profile-hook placebo. The placebo hook must actually receive
events (a boolean first-event witness is sufficient) while collecting no
function timing table. Preserve exact command, interpreter flags, profile
binary/table and before/after source snapshots. Compare ordered stream digest,
every branch/root/low/high/node count and coordinate coverage across all three;
exclude elapsed time and observer diagnostics from the null comparison. A
profile that perturbs the scientific counter record is not accepted as a
diagnosis. Preserve any first failure.

One global diagnostic allowance:30 process CPU seconds,60 wall seconds across
all three observer arms and setup,32MiB tracked arrays and at most32768 held
point records. Give every inner Budget the same diagnostic start timestamps and
30/60 clock limits; its normal per-cell/rule checks then enforce the global
allowance without resetting it between observer arms. Keep the registered
per-frame point/node guards. It cannot terminate a peer. Profiling overhead may
itself refuse. Such a refusal does not authorize
smaller favorable point subsets or an automatic allowance increase.

Read both cumulative and exclusive function times/call counts for
`angular_cuts`, `Budget.check`, `ExactSelector.classify`, rule/mass helpers,
`point_cuts`, `_stream` and progress output. This is diagnosis, not a performance
claim: instrumentation changes timing. The private profile may omit frequent
full-run progress writes, so retain that stated limitation rather than
attributing an unprofiled disk path to another category.

## Smallest candidate if record construction is material

Only after that diagnosis, propose one mechanical stream-plumbing change:
precompile the fixed `struct.Struct` layouts, cache bounded cut layouts by
actual returned length, cache the arm byte prefix once, and pack a point's
existing fields directly without a second dictionary when no external sink is
installed. With a sink, reconstruct the exact existing event shape/order.
Keep `point_cuts`'s public records, exact selector, frozen geometric calls,
both rule batches, coverage bitmap, mass checks, per-point work charges and
all existing time checks. Cache at most the finite supported cut-layout set;
no cell/frame geometry or cut-result cache and no aligned/expected image arrays.

This avoids changing admission semantics to save bookkeeping. Do not initially
batch away `Budget.check`, pool multiple point charges or remove cut validation.
Those are distinct policies, can alter cap-refusal prefixes and need separate
prospective contracts if later considered. No modification to frozen M194e
functions, rational arithmetic, mask height, angular cuts, counts or budgets
belongs to this stream-only candidate.

Required equivalence controls before a new intended run:

- Exact complete private stream bytes/digest and every scientific count on the
  fixed profile populations; both actual sink-present and sink-absent paths,
  plus a exercised no-collection sink placebo. Every arm/frame remains visited.
- Non-square/nonidentity independent geometry, signed/zero/tangent/ULP/cancelling
  heights and unsupported-rational controls remain passing on the actual path.
- Live mutations of cell coordinates, branch, low/high label, root index,
  signed height, one cut endpoint, arm prefix and omitted/duplicated records
  must change the comparison or refuse. A digest of a stream whose generation
  skipped the interesting point is insufficient.
- Strict point/node cap equality and clock-crossing controls must still refuse
  with their actual partial work prefix; all-analytic time checks, array
  ownership/mass errors and intended completion type/coverage/source guards
  remain live. Successful record equivalence does not waive any refusal.
- Before claiming a speed change, use one frozen pair of private baseline and
  candidate programs, three alternating pair orders (AB,BA,AB), report each
  time and per-setting minima. Bound this optional comparison prospectively to
  30 CPU/60 wall overall; no extrapolated full-run completion promise. Omit speed
  claims if the comparison is too noisy or exceeds its bound.

Then obtain source/control release and perform one entirely fresh intended
three-arm count under the unchanged60CPU/120wall and strict work limits. The
first ten complete rows must also match the archival counts; the full new
ordered digest requires its complete fresh traversal. Wall-time-dependent
refusal coordinates need not match the old failed run, and its partial arrays
or rows cannot fill missing new work. Only a new complete result can pass.

## Decision versus a counter-only budget amendment

A bounded profile is warranted: the implementation does substantial Python
record work beyond the geometry being counted, and the refusal itself cannot
distinguish that from essential cut cost. An optimization is not yet warranted
as a claimed solution. If frozen geometry dominates, or the narrowly equivalent
stream change is immaterial, prefer a plainly prospective **counter-only** CPU
allowance amendment over rewriting the commissioned geometry merely to pass
the counter. Derive its allowance from the retained diagnostic/full-run work,
not from trying successively larger full limits. Keep the original failure,
all point/node/storage limits, complete population and future numerical-render
caps unchanged. A longer cost counter does not imply either faster or successful
numerical rendering. Do not silently raise the current60-second bar.

Inspection for this plan used bounded source reads and JSON field extraction
only. No profile or model/product command was executed.
