# M194g — larger shared-pupil expected images

2026-09-07. **IN PROGRESS; first numerical reference population is uncommissioned.** The fixed
320×240 fixture needs a complete geometry-only cost pass, independently
commissioned radiance components, and complete independently admitted expected
arrays before it can feed any noise or production comparison. The geometry cost
prerequisite passes; numerical component work is active. No full expected-image
population, noise population or larger production output has been released.

## Consumer and decision

M194f completed its eleven actual-TIFF checks, but its 64×48 fixture has only
one Laplacian band plus a base. M194g supplies a larger two-depth boundary
fixture for a later fixed HardFloor/FloorPedestalV1 comparison. The immediate
consumer is a noise emitter reading complete expected-electron arrays. The
mathematical model remains scalar radiance through one uniform pupil shared by
foreground visibility and both surface intersections. It is not measured
physical optics, a sharp real-capture reference, or evidence of improved merge
quality. The fixed five frames use identity placements in native reference-2
coordinates; no alignment fit is being scored.

The [prospective protocol](../../experiments/m194g-larger-pupil/preregister.md)
was committed at `a59a1c47` before implementation. It retains the M194e fields,
depths, foci and K=12, with extent320×240 and mask offset142. Each of three
arms contains five complete frames: 1,152,000 arm/frame/cells in total. The
exact-rational full-layer selector and actual rounded numerical cut geometry
have different meanings and are separately checked. No partial population can
admit the next phase.

## First-phase implementation and controls

The pinned loader executes checked M194e source bytes; those sources remain
unchanged. The selector bounds exact finite-coefficient rational intermediates
and falls back at equality or unsupported arithmetic. The counter enumerates
every actual low/high cell-rule point and its actual angular cuts, without
evaluating radiance or integrals. Its common-height calculation follows the
rounded consumer inverse map, not an algebraically precombined substitute.
The clock covers all cells and all fifteen traversals without resetting.
Unique reachable ndarray backing allocations are tracked; this is not RSS or
an accounting of Python objects and hidden helper temporaries.

Final source checkpoint `dbf997d9` includes the following independently exercised
controls; release `0e125df2` committed their results and the exact intended
command before the run. Root checked that both commits contain exactly their
explicit owned path sets, with no unexpected or missing paths.

| Instrument | Retained result | Meaning and limits |
| --- | --- | --- |
| Author controls2 | 41/41 | Source, selector, actual cuts, work/storage/clock and completion controls. |
| Independent geometry2 | 373/373 | Different tangent/ULP/transformation choices, wrong-radius and missing-cell-support destroyers, rounded-height cancellation control. |
| Independent preflight3 | 94/94 | Different non-square/nonidentity fixtures, actual helper counts, coverage, work/clock/storage, source and metadata controls. |

These are component passes, not evidence that the intended count fits its
resource limits. Their exact hashes, source hashes and commands are bound in
[cost-release-1.json](../../experiments/m194g-larger-pupil/cost-release-1.json).
The independent geometry review checks112 tangent/scaling/origin cases,
eight rotated brackets,1482 lattice cells and81 point-cut records. Its small
control timer begins after imports; it cannot corroborate intended whole-run
startup cost. The independent preflight reads810 distinct cells and167040
point calls across its controls. Its row-order null compares numerical counts;
last-coordinate and ordered-stream receipts legitimately depend on traversal.

Failure history remains authoritative. Author controls1 passed36 checks on an
older source. Independent preflight1 stopped after49 checks because its own
height variable shadowed grid height. Independent preflight2 passed86/91: four
completion-type false accepts were real author defects (float width/count,
boolean frame index, float visited count); the fifth was the verifier's
overbroad row-order equality assumption. The author added strict integer checks,
and the independent verifier corrected its expectation and added more type and
negative-work destroyers. The final41/373/94 runs bind the corrected source.
Original failures, source snapshots and logs are preserved. See the
[independent preflight report](../../experiments/m194g-larger-pupil/independent-preflight-report.md).

## Intended cost run1: measured refusal

The exact released command was run once:

```powershell
python -X utf8 -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-preflight-1 experiments/m194g-larger-pupil/preflight.py --output experiments/m194g-larger-pupil/preflight-1
```

Root observed operating-system exit1 in launch session83512; the separately
stored launch receipt attributes that observation to root. The terminal record
is `UNCOMMISSIONED_COST`, SHA256
`f23b5b1d24ba3e9516b246dce452c336749a3824c373484018a63c68ba66d010`.
It began16:51:21.596748 UTC and ended16:52:21.989309 UTC. The resource clock starts
before the recorded start timestamp, so subtracting those timestamps does not
reconstruct whole-run elapsed time.

| Quantity | MEASURED terminal value | Fixed requirement |
| --- | --- | --- |
| Complete frame/arm rows | 10 | All15 |
| Complete cells | 821287 | All1152000 |
| Whole-run CPU | 60.015625 seconds | At most60; deciding refusal |
| Whole-run wall | 60.828000000095926 seconds | At most120 |
| Partial current-frame points | 1780160 | Strictly below8000000 per frame |
| Partial current-frame nominal angular nodes | 514394112 | Strictly below1200000000 per frame |
| Tracked peak ndarray backing storage | 91280 bytes | At most33554432; restricted scope above |

All five primary and five angle-refined rows completed. Cell-refined frame0
stopped at native(167,166), after53287 completed cells. That failing cell had
already been classified, so its partial row has53288 branch records. Point
work is charged before cuts are completed and angular-node records emitted;
partial point and node totals do not imply a completed numerical population.
The retained partial-stream digest is not a full-stream digest. Four remaining
cell-refined frames were never started.

Complete primary row counts were:

| Original frame | Foreground | Background | Numerical | Roots | Low points | High points | Nominal angular nodes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 36708 | 36912 | 3180 | 8016 | 128256 | 513024 | 184139136 |
| 1 | 37068 | 37272 | 2460 | 6576 | 105216 | 420864 | 149075712 |
| 2 | 37428 | 37632 | 1740 | 5136 | 82176 | 328704 | 113300352 |
| 3 | 37800 | 38004 | 996 | 3648 | 58368 | 233472 | 74874240 |
| 4 | 38160 | 38364 | 276 | 1104 | 17664 | 70656 | 4239360 |

Angle-refined rows have the same branches, roots and cell points and twice
these nominal nodes. The doubling follows the registered angular orders;
it is arithmetic, not independent replication. Total partial-run work is
5696960 points and2091280512 nominal nodes, summed across frames rather than
compared to a per-frame ceiling. The old M194e limits inside each integrator
configuration describe frozen helper settings; the active counter ceilings
are the separate fixture/work limit record. No optical integral was evaluated.

The [independent terminal review](../../experiments/m194g-larger-pupil/independent-cost-1-review.md)
checks all deciding rows and source/configuration/control/Git/snapshot bindings.
Its different exact row-boundary search reproduces branch counts for the ten
complete rows and the classified partial prefix. The twelve local source
records are unchanged before/after; all fourteen released local/frozen sources
match current and saved bytes. The reader's initial mistaken uniform control
schema assumption and corrected schema-specific read are both retained.

**Decision:** this instrument exceeded its time ceiling. It does not establish
that the optical model failed, that remaining rows satisfy their work limits,
or that later radiance is affordable. No runtime extrapolation or speedup claim
is made. Preserve the refusal and independently review a prospective
counter-only repair before another intended count.

## Bounded diagnostic stopped before profiling

The counter-only diagnostic was preregistered at76b255db and its reviewed
harness/commands committed at25a223f6. The fixed private9×6, five-frame,
three-arm input has810 cells. Four separate fresh-process modes were planned:
off, count, placebo and an actual cut mutation, each with10CPU/20wall and the
unchanged work/storage bounds. The schedule stops at a failed mode.

Off1 completed all15 rows and810 cells with167040 points and39819840 nominal
angular nodes. Its result hash is
`c4d3298dd64df03f092e5904b3dbf08c6ebbb8284f5e7ddb5e142d0193f75762`;
canonical geometry payload hash is
`b05e5f7f4b5d9d86c69cee4fd6eb7ba116781d7b997b49611b884d566df2e78a`.
Eleven checks pass. Seven explicit direct radiance-trap calls prove those traps
are active; all seven actual-counter radiance call counts are zero. Root
observed exit0. Its1.546875-CPU/1.547-wall-second receipt is one diagnostic
observation, not a speed comparison or intended-population estimate.

Count1 then refused before any geometry work or profiler construction:
`ValueError('baseline is not the same-source completed off mode')`.
Its result hash is
`d80f9f77b9bcb415eee5c423c30b4f114b6ecaaec6fcadc478bc7f7994c78bea`;
root observed exit1. The actual saved input records and source bindings agree.
The harness compares JSON-loaded lists directly with tuple fields preserved
by the live dataclass serialization. The same representation mismatch exists
at its later payload-input boundary. This is a diagnostic consumer defect,
not changed geometry or a source mutation. The pre-execution source review
did not catch it. Original source, both runs, exact arguments and failures are
preserved; placebo and mutation were not launched.

No profile attribution, profiling observer null or mutation-control pass was
obtained. The diagnostic has ended rather than beginning an optimization loop.
Amendment1 proposes one fresh intended count with180CPU/240wall as a finite
resource allowance the program is willing to spend, preserving all geometry,
coverage, work/storage and later accuracy requirements. It needs independent
review, committed implementation and affected controls before that launch.
The original60-second refusal will remain a refusal under its original bar.

## Amendment1 and complete cost run2

Amendment1 and its independent control design were committed at01d4e52b,
before the implementation/driver release5eb0968d. All53 affected independent
checks passed on their first invocation. They verify the exact allowed source
changes, unchanged function/class bodies, actual constructor/check/traversal
boundaries at180CPU/240wall, old-policy destroyers, persistent clocks across
cells/frames/arms, unchanged strict work/storage limits and actual copied
input/amendment entry refusals. Their injected clocks and private exception
sentinels are controls, not measured full coverage. Result hash:
`e1d308f95eea671a665529aebc891595e14c2be0cbe8aca8a82d36870c449e95`.
The [independent report](../../experiments/m194g-larger-pupil/independent-budget-report.md)
states the precise recording-versus-acceptance scope of its source-change case.

The new complete-run release44d2670d binds21 source files, the affected result,
the historical controls at their original sources, the actual fixture and this
exact command before execution:

```powershell
python -X utf8 -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-preflight-2 experiments/m194g-larger-pupil/preflight.py --output experiments/m194g-larger-pupil/preflight-2
```

**MEASURED:** run2 completed all15 rows and1152000 cells, returning
PASS_COST_ONLY; root collected exit0 from launch session9359. It started
17:32:35.001326 UTC and ended17:34:30.242347 UTC. Whole-run resource samples are
113.9375CPU and115.68799999996554wall seconds, within180/240. These remain
cooperative samples before final terminal serialization, not process-exit
timing. No speed comparison or radiance runtime prediction follows.

Result SHA256 is
`c9e9154fd395a06a5d1cbb28123ac84f92ee1ac61b1a97216f8904b8b6261677`;
complete ordered geometry digest is
`74827222370a9d733c520adbe0515b71a3ca545e31e2d7e1c9457cf9de547e70`.
Every row has76800 completed cells and ends at(319,239). The five primary and
five angle-refined rows match the corresponding retained complete run1 counts.
The newly complete cell-refined rows have the same input-defined branches and
root counts, with their own actually enumerated point/cut work:

| Original frame | Low points | High points | Nominal angular nodes | Maximum intervals |
| --- | --- | --- | --- | --- |
| 0 | 513024 | 2052096 | 741288960 | 50 |
| 1 | 420864 | 1683456 | 601070976 | 48 |
| 2 | 328704 | 1314816 | 457909632 | 48 |
| 3 | 233472 | 933888 | 304189056 | 46 |
| 4 | 70656 | 282624 | 16957440 | 1 |

Maximum per-frame work is2565120 points and741288960 nominal nodes, strictly
below8000000/1200000000. Total work across all rows is11750400 points and
3698302464 nominal nodes; totals are not per-frame quantities. Tracked peak
ndarray backing storage is91280 bytes across18 owners under the32MiB scope.
The recorded local sources are unchanged before/after. The independent terminal
review verifies all21 actual release/current/snapshot/Git bindings, all fifteen
rows and different exact row-boundary branch counts. Its read result is
`a29b4fb9d95e668ebda8da14d97afc9e5a24875e58bb9858f017db95ca006715`;
see [the complete independent review](../../experiments/m194g-larger-pupil/independent-cost-2-review.md).
The cost prerequisite is discharged; numerical implementation and component
commissioning are next. No radiance integral or expected array is admitted yet.
The first60-second refusal and failed profiling instrument remain failures.

## Onward design, not released experiments

The independent spatial-reference plan avoids the author's Bessel primitive
and retains clipped-cell integration near the boundary. It requires its own
component and resource commission before radiance release. Future quality
notes distinguish an ideal K=0 cell-integrated RGB target from actual endpoint
TIFF observations, with eight paired noise repeats and flat controls first.

An independent source-support review rejected the proposed background endpoint
mask outside height8: native(150,110), height−8.5, passes that mask while a
nonzero MHC tap reaches partial foreground visibility. Prospective notes now
require strict background height below−(.575+6*sqrt(1.0225)+2) and foreground
height above2.575, conditional on actual identity gather and single-input hull
preservation. The separate74-native border guard does not isolate multi-frame
output from the depth boundary. This correction is a derived support result,
not a scored optical or production population.

No core merge, noise model, product default or camera profile changed in this
milestone. No SYNTHESIS fact/discipline/question fold is being attempted.

## First numerical component execution

Implementation/specification release9b5ca1dc was followed by source/command
release98748490, before either numerical batch. Root checked all24 committed
source bindings and12 input bindings against current bytes and the exact
eight-path commit. The execution release is
`numerical-components-release-1.json`, SHA256
`99895afd4cd99151708b7fa0e462297a273bd5fceabf205c0228f0bb197847fa`.
It contains both exact original interpreter argument arrays. The
[pre-execution source review](../../experiments/m194g-larger-pupil/numerical-source-review-1.md)
records corrections made before any numerical call, including input reopening,
array order, restored fault phases, consumed cache factors and resource tracking.

**MEASURED producer result, independent admission pending:** the author batch
started18:12:47.6381192 UTC and returned exit0 at18:14:08.0065778 UTC; root
collected completion from session50422. Its result hash is
`358aebe2292a8c1aa920763481cae36ce43ebe2d756a5d2e0b8e8fde20fb080e`.
It has331 planned and331 actual rows:299 ordinary calls,15 deliberate faults,
15 restored companions and2 cache primes. The one refused numerical row is
the intended zero-over-zero fault. All511 producer checks report pass. All60
normal observer frames are present, covering3240 sites; the additional failed
coverage traversal is retained separately. These are the author's completed
checks, not yet an independently admitted optical comparison.

The same cumulative author allowance recorded1082883 actual point calls,
270801888 angular nodes,79.203125CPU/80.25wall seconds,6832758 tracked ndarray
bytes and32768 simultaneous node pairs. The latter reaches its inclusive
ceiling. Peak live scalar frames is1. Off collected no hook activity; count
and placebo each reached4338 hybrid and204813 fallback hooks per normal
execution, with optional collection only in count. The saved records retain
the actual scalar/branch/sparse diagnostic payloads and their deliberate
corruptions; independent file/equality/resource checks remain required.

**MEASURED refusal, retained:** the independent reference started
18:12:47.8333379 UTC and returned exit1 at18:12:56.8972312 UTC. Its result hash is
`514520ee73ea4504be17f0520791c174d11f202c371cd1ce9f6b11a4a8da7b0b`.
All300 ordinary rows were attempted, but272 returned values and28 refused.
Each of14 geometry cases refused in both primary and refined arms:
004,006,011,013,015,022,060,062,067,069,071,078,116,117. Every refusal came from
the unchanged Cartesian reference's quadrature-warning boundary, with
`Extremely bad integrand behavior` on a near-tangent case. There was no process
exception or finalization error, and its recorded sources stayed unchanged.

All52 separately recorded literal/series/retained-array oracle comparisons and
all14 deliberate fault/restored comparisons report pass. Of150 required
reference refinement comparisons,136 have values and pass;14 lack values.
The completed-values requirement is the one failing check among55. Its
120372 integrand calls and8.890625CPU/8.937000000034459wall seconds do not
approach the declared allowance. This is a numerical completeness failure,
not a cost refusal, and the272-value subset cannot authorize expected images.

**ARGUED diagnosis, not yet an observed failing-interval proof:** independently
reading the saved inputs and frozen interval construction identifies topology
cuts only a few binary64 steps from a pupil endpoint. The next task is a
bounded diagnostic and prospectively specified integration correction if that
mechanism is confirmed. Keep the first population, all inputs, accuracy bars
and original helper source. No warning suppression or omitted case is released.
