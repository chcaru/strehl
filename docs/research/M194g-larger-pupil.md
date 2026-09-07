# M194g — larger shared-pupil expected images

2026-09-07. **IN PROGRESS: fixed38 diagnostics complete; separate numerical
verification pending.** The full expected arrays, specified software noise,
saved90 CFA files and larger production bridge have independently passed their
staged commissions. All38 registered production outputs and the frozen quality
reader completed. The experimental weighting remains experimental; no default,
physical-camera calibration or SOTA claim changes. Earlier phase statuses below
are historical observations, superseded only by the later explicit releases.

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
120372 integrand calls and the launch log's post-persistence reading of
8.890625CPU/8.937000000034459wall seconds do not
approach the declared allowance. This is a numerical completeness failure,
not a cost refusal, and the272-value subset cannot authorize expected images.

**ARGUED diagnosis, not yet an observed failing-interval proof:** independently
reading the saved inputs and frozen interval construction identifies topology
cuts only a few binary64 steps from a pupil endpoint. The next task is a
bounded diagnostic and prospectively specified integration correction if that
mechanism is confirmed. Keep the first population, all inputs, accuracy bars
and original helper source. No warning suppression or omitted case is released.

## Independent payload/resource controls and interval diagnosis

**MEASURED, scoped private-control pass:** source/command commit `1f6db1d0`
preceded the first independent private-control run. The exact release is
`independent-component-controls-release-1.json`, SHA256
`7cc77389df8a55f016e73b2c584a176b72cdf3fbaccc0f3a19a4f4283893e0a9`.
Root collected exit0; the terminal result is
`258d5b9de1966a346581ac4329bd2fbdaecf83a2f904e74473e73c326b6dfce1`.
All145 controls pass:94 payload/reader checks,36 actual resource checks and15
entry checks. This includes independent consumption of all331 saved author
call rows and60 completed observer frames, coherently rehashed private
metadata/array mutations, cumulative limits and original/secondary failure
retention. The deliberately refused private author invocation printed
`UNCOMMISSIONED_NUMERICS` before the successful controller terminal line.
It is a powered negative control, not a failed private-control run.
Source bytes are unchanged. These checks admit their instruments and saved
author payload semantics; they supply none of the28 missing reference values.

**MEASURED diagnostic support:** source/command commit `2c0563f6` preceded the
first96-call interval diagnostic. Its exact release is
`reference-interval-diagnostic-release-1.json`, SHA256
`cec6cb4fcb803b57b04b736777e8160264ce45e0e8e5b4fb8fb49048bbcca6e1`.
Root collected exit0, with result
`194dbdb0454a02db985b4e28305c9f5a0f5f42fe4223829b3ea8db0f21e5e1f0`.
The14 refused cases and two fixed successful companions were replayed at both
original targets in off/count/placebo modes. Each mode's full numerical
signature, including refusal/scalar receipts and actual integrand counts,
is byte-identical to the original signature, SHA256
`0a3e0c9732216609e94d0605f55eb7c9c21dc598fa196f9492c8e9b0ec644375`.
All11 diagnostic checks pass, including reopened callback correspondence,
stale-bound and coherently changed sample-range faults and restored companions.

All28 warning intervals touch exactly one pupil endpoint and span5,13 or16
binary64 steps, inside the prospectively fixed256-step diagnostic class.
Each made63 callback evaluations at6,14 or17 distinct coordinates; repeated
coordinates are directly retained. No warning lies outside the declared
class; all four ordinary-width positive-companion intervals are warning-free.
The cumulative diagnostic used31878 actual integrand calls and its persisted
receipt records2.25CPU/2.405999999959022wall seconds. It changed no integration
formula, tolerance, split or warning disposition. This localizes the warning
mechanism; it does not measure a true scalar error or admit expected images.
The next work is a separately specified and commissioned normalized-interval
adapter, followed by complete component populations under unchanged bars.

## Complete second component producer runs

The exact normalized-interval amendment was committed at1477e677 after
independent artifact/design review. Numeric source/command release4fbe56d7
then fixed both complete commands before execution. Root verified its exact
six changed paths, all27 numerical source bindings against current bytes and
raw committed Git blobs, all14 inputs and both new output destinations.
`numerical-components-release-2.json` has SHA256
`4941a294ca69f8c7a20d70a67e1bf65858d7823748df340cfe7defebabbc701b`.
The independent reader/private-driver sources are separately versioned
consumers; neither numerical process imports them. Their later source freeze
cannot change these numerical inputs or outputs.

**MEASURED producer completion; independent comparison pending:** root
collected exit0 from the actual reference session11696 and author session57446.
The second reference result is2200686 bytes, SHA256
`bbeda46abd41a3fb604e787cbaf0d598cc01b70230175fd1cefe96242e1f997d`.
All300 ordinary rows return values; all66 producer checks pass, including
the11 new interval groups. All150 refinement and52 oracle comparisons are
present, along with14 existing optical fault/restored groups. Sources are
unchanged, with no exception or finalization error. The persisted result
records129974 integrand calls,13.78125CPU/14.016000000061467wall seconds and
24576 tracked ndarray bytes. The launch log's later post-write budget reads
13.84375CPU/14.077999999979511wall seconds; neither is a speed comparison.

The additive controls include72 direct polynomial/mode calls and12 active
Jacobian/interpolation/request faults. Root read the actual fault magnitudes:
the ordinary-width missing/repeated Jacobian errors are1.0/0.5; the two
interpolation errors are0.7812499999999996 and0.16276041666666688, each above
its fixed rational-oracle bar. Both endpoint slivers also reject the
Jacobian faults. The four request-scaling faults change the actual delegated
request while their scalar errors are zero: they commission a call contract,
not a demonstrated accuracy loss. Restored signatures and the original
disabled-adapter warning are retained. No warning was suppressed in the
successful reference method.

The second author result is1253975 bytes, SHA256
`91af8579a12b73de17548b5a72a20ab5922272b7550b522684c6d2f8b54243ee`.
It completes331 calls and511 passing producer checks under the unchanged
operator, with1082883 points,270801888 angular nodes,6832758 tracked ndarray
bytes and82.9375CPU/83.85999999998603wall seconds. The source/capture error
fields are null. The61 started-frame count still includes the deliberate
coverage failure; it is not61 completed normal frames.

The next released consumer sequence is the current-source private controls
and complete cross-method reader using both actual second results. Its
prospective suite now contains193 checks: the original145,38 v2 metadata and
source controls, and10 controls of actual direct-interval evidence. The latter
were added before any v2 consumer execution so a self-reported passing group
cannot substitute for reading its scalar errors, requests and restored data.
The earlier source-review note's183 was the then-current prospective count.
No private193 pass or full expected-image authority is claimed here.

## Independent complete component admission

**MEASURED:** private193 passed under74a470cb, but the first complete reader
under4a613525 refused before comparison: it attempted JSON parsing on the
correctly pinned Markdown amendment. Its actual failed result and traceback
are preserved at `independent-component-verification-2/result.json`, SHA256
`10d980673b7510f9ba9f7d4961ab7ec03dc29fa99dfe55d43eaf4c271bb9b5ee`.
The193 controls had tested individual consumers and the author's entry, not
this reader entry. This was a reader defect, not missing numerical evidence.

The narrow input-type repair and four powered entry controls were frozen
at15ece1f1. Root collected exit0 from the new197-control command, result
`dcae9307a2e3e5a7c9ac81d71e7ccf6e71cfee867fd9d08d26b9f60918019348`.
All146 payload/reader,36 resource and15 entry checks pass, including139
intended refusals and58 valid/restored companions. The new entry checks
reproduce the old JSON failure, reject a false amendment pin, and show genuine
Markdown/result reads reaching their explicitly private downstream boundary.
That sentinel does not claim the complete comparison ran.

**MEASURED independent admission:** the subsequent actual complete command
was frozen at6e4ca40d and returned exit0. Result
`independent-component-verification-3/result.json` is472315 bytes, SHA256
`a652837ff7f7db4b6ca21ca1c5afedfc2f572920bd2f626aca29679faca8c139`.
Both wrapper and nested result report `PASS_COMPONENTS_AND_OBSERVER_ONLY`;
exception/traceback are null and inputs are unchanged. It reopens781 deciding
input bindings and both source closures, including the current197 controls.
All598 component comparisons pass, with largest absolute discrepancy
8.387360139749944e-9 expected electrons at geometry-034, disabled analytic
author versus refined reference. All150 independent refinements pass with
maximum1.0068106348626316e-8. The52 literal-oracle comparisons have maximum
1.0186340659856796e-10. All14 optical fault/restored groups are read, with
minimum active discrepancy1.9515361838148237e against the strict>.004e bar.
The72 direct interval records and12 scalar/request interventions are read;
request interventions remain call-contract evidence rather than scalar error.
All60 observer-frame packages retain their required byte identities and
complete metadata. These are fixed component and small-frame results, not a
physical-model, all-image, camera-noise, production-quality or SOTA claim.

The next commands render all25 complete scalar images across three author
and two independent reference arms. The separate full-array reader must
consume every frame under the unchanged numerical bars before noise emission.

## Complete expected-image production, first release

Source/command commit9663ec61 froze the two scope-specific releases before
all image work: `full-author-release-1.json`, SHA256
`fc369e4c48fdd67dec32dbd22b9467e64ad89665961b1f422ae8abd484ce16c9`,
and `full-reference-release-1.json`, SHA256
`66ef6ee72eeba61a5c8dedf616339d606fb75ff4570514be89e01bdc6bf0c31e`.
Root checked all30 source bindings against current and raw committed bytes,
all24 inputs, the exact391-path evidence commit and all fresh destinations.
The three author arms run in order in one process family; the two independent
reference arms run in order in another. At most one arm per family runs at
once. The existing limits and complete original frame populations apply.

**MEASURED reference producer completion, full comparison pending:** root
collected exit0 from the reference family session20314. Both arms report
`PASS_COMPLETE_REFERENCE_ARM_ONLY`, all five frames complete at76800 cells
each, sources unchanged, null exception/traceback and no finalization errors.
Primary result SHA256 is
`0c34069b97c98f11b3c419450406ea725b72153e9ab8126fdbf57bd7c52ce476`
(25899 bytes); refined is
`77e47cfd83bb447d3ba74d00d998ee879d5f0a4f92b218dfb82d6bab2d66b617`
(25935 bytes). Primary records5996256 integrand evaluations,
53.5CPU/53.65700000000652wall seconds; refined records6415668 evaluations,
56.109375CPU/56.34400000004098wall seconds. Both track1382400 peak named
ndarray bytes and zero live scalar frames at terminal. These are completed
arm readings under their allowances, not a speed comparison. The producer's
values and receipts still require the complete independent array consumer;
successful reference arms alone do not grant full float or noise authority.

## Independent complete expected-image admission

**MEASURED:** the author family also completed all three five-frame arms,
with root collecting exit0 from session87903. Primary, angle-refined and
cell-refined result hashes are respectively
`bdb95d23eb4eb97802557bf9683e6e7e95ea1ff32cd951d495efe43c675a0f19`,
`dab51375c68bb5f7fa42ec7933368e3b53f15537d0b1d44d818074e928949a6b`,
and `a385f8e070cbc9019e798ee13e9c2dead2fae50f84a27de386333fc84daa538f`.
All have complete frames, unchanged source snapshots and null errors. Their
recorded CPU/wall seconds are306.703125/307.344000000041,
421.53125/422.31199999991804 and587.578125/588.688000000082.
These are completion/resource readings, not comparative performance results.
The completed author artifacts and independently authored reader/control
sources were committed atd0647ce9.

**MEASURED private reader commissioning:** the actual command in
`independent-full-array-controls-release-1.json`, SHA256
`d1c7fce1c5a639e003e98add5e619905682436d90e729c4870d27dec95f1d558`,
returned exit0 with79 passed checks:51 intended refusals and28 valid/restored
companions. Result SHA256 is
`e549d13cd6acfa40d186c8cc33bfa7c9a420c0abf93aa54588ae2daae3aa988d`.
Actual shared comparison loops reject errors confined to one frame or arm,
and actual payload consumers reject stale/rehashed bad arrays, incorrect
diagnostics, reset/cumulative-work defects and file-identity aliasing.
The genuine full entry is exercised through the complete component authority;
private downstream stops remain explicitly private. Persistence controls
revoke authority after a final check fails. Source closure and all expected
exception types/boundaries were reread by root.

**MEASURED independent full admission:** command/source commit01ded5d8
released `independent-full-array-reader-release-1.json`, SHA256
`bad71e7b1bebe66ae8ddba45fa917d59820079fc865c49c92c5e35e58ecf520d`.
The actual command returned exit0. Its344512-byte result is SHA256
`042893c976ecc99845c98e894afd359852d428a8a87d4028d09c03bef3dfcedb`,
status `PASS_COMPLETE_FLOAT_MODEL`, null error, no finalization errors and
unchanged sources. All25 arrays and1178 deciding file bindings were read.
Each of the30 external comparisons independently meets max<=.004e and
RMS<=.0008e on its own whole-image or fixed-band population. The fixed band
contains3852 sites and its complement72948. Largest external max/RMS across
these separately admitted rows are1.0743797247414477e-5e and
3.966221413918554e-7e. These are expected-electron discrepancies, not quality
scores; agreeing implementations could share a physical-model error.

All15 whole-image refinement comparisons independently pass. Maximum absolute
changes are4.261892172507942e-9e for angle refinement,
1.025840720103588e-5e for cell refinement, and2.5234567146981135e-6e
for independent-reference refinement. The existing bars are respectively
.001e,.001e and.0005e. Author fallback and independent boundary masks retain
separate descriptive counts/discrepancies; neither changes admission or
claims mask agreement. The reader records7.515625CPU/7.734000000054948wall
seconds and7609704 peak live named-array bytes under120/240seconds/32MiB.

The2981-byte `float-commission.json`, SHA256
`3f18d8954347382b2dffe0ca501f93ef8da54c3b966a1a606851323d86277a2b`,
binds the five original primary expected arrays and the acyclic comparison
authority. This admits the fixed continuous shared-pupil numerical population
only. Software noise, final CFA files, the production bridge and the38-output
quality matrix remain separate consumers with their own controls.

The next software-noise command is released against the frozen contract and
the actual runtime snapshot. Runtime capture imported core, authority helper
and independent private-noise reader in actual runner startup order, with no
sampling/encoding calls. It returned exit0; `runtime.json` is10162 bytes,
SHA256 `5785be482f28d097e0fb9bd7111b2655502485951fc52b08b6cc2ac01d9d49c3`.
This snapshot authenticates the runtime bytes used by the next command; it
does not itself commission a noise law.

## Fixed software-noise private commission

**MEASURED:** the exact command in
`software-noise-commission-release-1.json`, SHA256
`3ab62bf38a05e2e46d57255071555714ecdaa428a0984d2d3a137b89f6fb5a3b`,
was frozen at561f58f3 and returned exit0 (root session99412). Its result is
6571 bytes, SHA256
`5ce444627af4787b404318bc4d78f4b9332f0081234e107ab597d269849a81c7`,
status `PASS_SOFTWARE_NOISE_COMMISSION`, null error, no finalization errors,
and identical initial/final source and input bindings. The fixed1186 noisy
calls,17 deterministic records and independent reader all ran within the
original shared budget. There was no changed seed, resampling or bar revision.

The independent394120-byte read, SHA256
`363dd1e91c45cf4ede50607f1a18a1df5b959de80fa08b73e8945abe71a39a0c`,
passes all four baseline levels, all seven restored groups and all seven
named fault instruments. It retains18 temporal groups,1976 replay checks,
all10 healthy and10 deliberately shared-key cross-frame comparisons, and
the17 deterministic outcomes. Actual final rereads cover1186 records,
5000 noisy arrays and25 deterministic arrays. Baseline nonzero P/R/E/X
temporal variance ratios span0.9941588455971452 to1.0081427742460436;
the all10 healthy pooled cross-frame maximum absolute correlation is
0.009195148986548198. The shared-key fault's minimum pooled correlation is
0.32563818966869973. The .02 healthy correlation and2% variance bars remain
fixed engineering checks, not universal-independence or physical-calibration
proofs. Zero-photon ratios/correlations remain undefined with exact-zero
photon checks, rather than being counted as independence passes.

The separate5178-byte reader-control result, SHA256
`92886d9cb9afb3b7913361c28dbbb69f8dae000931a78796495203176cc45040`,
passes36 controls:29 intended reader refusals and7 valid/restored companions.
They exercise actual complete-entry/index, consumed trace, typed payload,
override, rounding, runtime and key-interpretation paths without new draws.
The bound wrapper is SHA256
`5aae94ee1d4d4e99db60a065d7bb6e3bbd7e63579715aea5a3ac10fdf5b1bb01`.
Independent source review also re-chose the quantized-normal oracle,
per-site temporal estimator, exact pair populations and consumed fault stages;
see `next-noise-statistical-source-review.md` for that separate review scope.

The stage requested exactly29147136 variates through2372 generator
constructions. Its last pre-terminal receipt records45.4375CPU and
73.67051520000678wall seconds,2826240 peak live named-array bytes,1195
started and1194 completed frames (the difference is the registered
pre-draw refused-key case). These counts include private deterministic calls,
so they are not the1186 trace population. Recorded pre-terminal output is
412562043 bytes; the actual final6261-file package is412568614 bytes,
including the6571-byte terminal result. The controller checks the complete
extent, runtime, inputs and elapsed budget after that terminal write.

This commissions the specified software noise law and private reader only.
Before intended emission, the actual `FloatAuthority` constructor/scalar/final
read paths need their own controlled failures. The final90 emitted CFAs also
need their separate independent reader and five-reference admission record.
Neither gate is supplied by this private-trace pass. Those implementations
and the larger production adapter are the current next work.

## Intended sensor files, larger build and quality instruments

**MEASURED / independently VERIFIED:** the committed actual-authority command
(85415e4e, independent-noise-authority-controls-release-1.json) returned exit0.
Its38 checks pass, including two distinct hardlinked scalar paths reaching the
actual alias refusal, incomplete ancestor records, malformed NPY inputs and
changed final inputs. No sampler call, generator construction or variate was
used. The result SHA256 is
`d7b5bd9a321dff4fc5e9b51e2d9f58c4c726dbca7954f7e32f8bb4a607f24435`.

The intended emission was frozen at48f69d82 with exactly the same ten source
bindings as the private software-noise commission. The command in
software-noise-intended-release-1.json, SHA256
`2f4a8d2aa426854b4c87fd3a31975bf19581048620175fc3433997b345865744`,
returned exit0. It completed90/90 original frames,160 generators and12288000
variates (6144000 each photon/read), with no changed seeds or retries. The
result SHA256 is
`c9549335951b630d90ed6bd893391905575e38b0bcab3308ff8fd36063dfd02a`;
actual manifest is noise-manifest.json,35052 bytes, SHA256
`80007e235c58c0cdee5549ffd3e3173a9e39886a35fb458cf0670a8ac5a47a67`.
The final203-file package is14551113 bytes. Last pre-terminal counters record
3.265625CPU/4.10207210003864wall seconds and5683200 peak live named-array bytes.
These concurrent-run times are budget observations, not performance comparisons.

The independent actual-file command was frozen at06ea2f4a, release SHA256
`dea6a22722831390125dadd1cafefeef29c9a36b9335191996fc2a4c0feb70a9`,
and returned exit0. It reads all90 saved CFAs and audits, independently checks
all ten noise-off encodings, and passes37 private controls. The80 noisy rows
check saved Q, source/key/audit associations and rails; unretained noisy
intermediate samples cannot be recovered from quantized Q and are not claimed
as newly observed. No new draws were made. Its result SHA256 is
`1089a1b5a6cb6e1fdb9fbe01937e057ff029f95e34aae4afe1e454bbe73bce34`.
The acyclic five-reference noise-admission.json is1082 bytes, SHA256
`088272bfbeca6d00a816a5de72eeaf7aac8f8ca6e0ef68941ab236655fa298e7`,
status PASS_SOFTWARE_NOISE_FILES_ONLY. All source/input finalization checks pass.

**MEASURED build failure retained:** the first larger Rust build under85415e4e
returned cargo exit101 after an actual Compiling strehl-cli line. Two bridge
helper functions omitted their required Ok(()) tails. Its original log/result
are archived in bridge-build-1; this was a compile defect, not an image result.
The minimal repair adds those two returns. Independent review of the root
build driver checked the separate fresh target directory, with the first
failed artifacts retained. The replacement exact build release752c1397... was
frozen at48f69d82 and returned exit0 with an actual rebuilt CLI and all eight
registered test names listed. bridge-build-2/result.json has SHA256
`04e7cf3915e77b83dbe8e7183249445e48ff451292bb16d4d926b3d6346f9be0`;
the copied12767744-byte test executable has SHA256
`1a96f3a472288c1c057e16df4cd8a4d04ed6a4a5a1cc2c80adbd67d69df2ccd1`.
This command compiled/listed tests only. Production render/test claims require
the subsequent actual invocations.

**MEASURED / independently VERIFIED instruments:** the exact target and
private-instrument releases563c9159... and420ba445... were frozen at06ea2f4a.
Both returned exit0. The target produced all76800 K=0 expected-electron cells
and16 ordered local controls (15 valid numerical calls plus two pre-call
geometry/radiance refusals). The distinct instrument run passed69 checks:46
metric controls and23 TIFF entry checks, including both byte orders, multiple
strips and a legal193x17 image refused by the historical128 bound. Flat controls
ran before wave controls; phase errors, amplitude inflation, extra residual
energy, outside-window spikes, temporal/spatial separation and repeat-wise
uncertainty controls were exercised. The instrument result SHA256 is
`cdb596da485a49acf835024bea6e44b21f55922dac804b14d56f26de61bd8ac4`.

The separately released K=0 verifier (3f6c851c; releasef4da2c57...) returned
exit0 after eight literal oracles and four live/restored fault groups (20
private integrations). Its analytic-x/split-y integration uses no polygon,
pupil or producer helpers. All ten fixed cells pass max.004e/RMS.0008e: actual
maximum6.002665031701326e-11e and RMS2.7569843395909545e-11e. It checks the entire
array for file/type/finite-value integrity, but independently integrates only
these ten cells; this is not a whole-array second integration. All geometry,
source, original command, target association and finalization checks pass.

Independent ten-cell result SHA256 `a79b885524963a164506365fcccaa571fb7abd652cb43ec4d817b7085d6437c7`.

No candidate quality metric or production-default change follows from these
passes. The subsequent bridge and comparison stages are recorded below.

## Production bridge commissioning and retained verifier refusal

**MEASURED / independently VERIFIED:** the frozen launcher controls first
passed23 live cases (release2,66ce5e8b). A later source review found that its
standalone final publication rechecked the build receipt but did not repeat
the actual executable/include-file closure at that last boundary. Per-child
and matrix closure already checked the actual build. The minimal amendment
adds Build.finish to standalone publication. Its separately frozen release3
(d8738438) passes the original23 plus three actual publication controls:
valid copied executable, a private one-byte post-write executable change
refused by the real build checker, and restored-byte success. The original
successful record is retained as rejected in the live fault arm. The actual
release1 bootstrap had earlier refused a changed review-document hash before
creating its output directory; its refusal record is also retained. Neither
failure is an image-quality result. See the exact release files and
production-controller-amendment-1-review.md for the distinct scopes.

The actual copied Rust executable then ran six private tests, with6 passed,
0 failed and1 deliberately ignored output test. The exact command is in
production-private-controls-release-1.json, frozen58da1e56; result SHA256
`eff686d8dcbf7346d09f9682d132d6b3ce958e145bf20e8ef758b0a81d99f6f9`.
The separate ignored output invocation (release1,350041c7) produced all six
private colour TIFFs and the controlled decode failure. Its result SHA256 is
`965438745b4288e852aa63d39dff99d22557d9d46bb175e6d599b96ec4415bbe`.

The independent private-output command (release4e97f4d0...,f643c957) returned
exit0, PASS_PRIVATE_PRODUCTION_BRIDGE_READ, with9 passing controls and all
six actual TIFFs decoded. Every output is300x226 at native origin(10,8).
The constant oracle's maximum error is0.10229648279550929 post-WB DN;
the affine/changed-green maximum is0.11383500356350851 DN, below the fixed
0.25DN criterion. These analytical checks cover60 predeclared native sites
per image, not a whole-image exact-ramp claim. All pixels are independently
parsed and hashed. Observer off/count/placebo match both complete file and
pixel hashes; the controlled decode error retains the observed read counts
and emits no output. Result SHA256 is
`26cbbaf4d138eb3f87f7d52b8042294ab6b50fa83c7864bdfdafe7959e37fe80`.

The intended12 controller's exact releasefe32ddc6... was frozenfefcb7e4.
It returned exit0 and COMPLETE_12_RGB_OUTPUTS_UNSCORED, with all12 actual
plans completed before any rendering. Each407403-byte TIFF uses the same
300x226/native(10,8) gauge. Its index SHA256 is
`c6ef5ba4ea15f09d7a0fa53f22cc184d9a4239c99ad850c2ec9747542ac90353`.
This rehearsal population supplies bridge commissioning, not candidate scores.

**MEASURED verifier failure, retained:** independent intended-read release1
(frozen6dc536bf) returned exit1 on the first actual plan, after its population
check and before any TIFF decode. The verifier confused the package-only
image software string with the executable's revision-bearing string. The
retained actual compiler log independently identifies package0.0.0 and
STREHL_BUILD_ID=48f69d82b419. The scoped repair requires the exact string
`strehl 0.0.0 (48f69d82b419)` for plans while retaining `strehl 0.0.0` for
TIFFs. It changes no image, control population, numerical limit or parameter.
The original full result and source snapshots remain in the first directory.

The replacement exact intended-read release091b1eda... was frozen877386aa
and returned exit0. It passes all59 association/reducer controls and decodes
all12 actual TIFFs. These59 comprise actual12-entry/population checks,
wrong plan/floor/endpoint controls, private38 schema failures and complete
private18-output reductions for half-noise, pure bias and an outside-window
spike. Each private reduction loads34 callback arrays; those102 private
loads are distinct from the12 actual TIFF decodes. The spike is consumed at
native(23,19) with67.5DN actual error. Controls do not stand in for candidate
outputs. Child result SHA256 is
`a28f2022b146bd1433dd135c14340c118d9ad46cf671de4a57c1c4500ed08fac`.

The complete independent intended-read result is1799058 bytes, SHA256
`69dc4b40673aec0b25fd4d900350bd2a4b4b905c81187559188e16bfa378f7f4`,
PASS_PRODUCTION_BRIDGE_ONLY. It has null error, empty finalization errors,
matching source/input closures,12 TIFF decodes and no optical cells. The
same-run off/count/placebo file hash is
`1b7624c24e0c99d57f1e0c1abea4e85cdc9f8c917f175d2587a18ece4210d440`;
the independently reconstructed pixel hash is
`cf5d699d84dd2393ea900e0e3a9b9ff86ab0ffeedf1b7954d6b0d47a48b3a966`.
The acyclic bridge-commission.json is168417 bytes, SHA256
`58ea0340b2961b72d5e489b6945b6eb9363c7f05a3e2980b26916a61095dfa79`.
This issues only production-bridge admission.

The fixed38 quality matrix source and exact release43b216da... are frozen
at61452547. Its actual command has now been launched, after the bridge gate
above. Completion, candidate diagnostics and their independent review remain
pending; neither a candidate-quality pass nor a default change is claimed.

## Fixed38 complete diagnostics; independent verification pending

**MEASURED:** the exact matrix command in production-matrix-release-1.json
(frozen61452547) returned exit0 and COMPLETE_38_RGB_OUTPUTS_UNSCORED. All38
plans preceded38 renders, with no missing row, retry or selected-subset result.
Its66801-byte index has SHA256
`03e7ffe9028cca5d56266603db09fbadd3f7f3cc19e95db609007a96914d55ca`.
It retains the exact alternating global-state order and separate endpoints.

The source-reviewed quality command was frozen at9a825936 in
independent-quality-score-release-1.json, SHA256
`28ae3b1917d647c19503016b808370aeb113e1d3da4746ad5559981d2b916ef7`.
It returned exit0 and COMPLETE_FIXED_QUALITY_DIAGNOSTICS after38 initial TIFF
reads plus34 flat and36 textured rereads,0 optical calls and both full scene
readouts. Every checked output entry is retained separately; the terminal
result is444640 bytes, SHA256
`7477f1553ac53dc87d554cee04117c536f7e5d3476b97ce9fde8f5d3b42b95df`.
Errors are null, finalization errors empty, source/input closures unchanged.

The fixed native window has3584 sites, boundary513 sites, and whole output
67800 sites. Initial recorded window readings are below. These are complete
reader results pending the separate numerical verification, not independent
verification merely because this table reproduces them.

| Scene/channel | HardFloor temporal variance DN² | Pedestal temporal variance DN² | Candidate/baseline | Paired ideal MSE change DN² | Eight-repeat SE DN² |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat R | 297.2417385439432 | 193.55885476999492 | 0.6511832951797241 | -104.03087335262919 | 9.533453644748079 |
| flat G | 268.7922138740406 | 130.5680610279353 | 0.4857583452514779 | -138.06011936019777 | 8.42754309212918 |
| flat B | 326.4576054816631 | 211.43342730811386 | 0.6476596769622203 | -115.17467443511576 | 6.783805636272118 |
| textured R | 619.0867739705876 | 618.6550847074219 | 0.9993026999100675 | -0.3404101619928497 | 0.07886166691000986 |
| textured G | 429.54135775854 | 428.9944978023048 | 0.9987268747319493 | -0.4703148335042897 | 0.18661817070174666 |
| textured B | 671.0461646199662 | 670.9376894780958 | 0.9998383492111427 | -0.16352554177001366 | 0.13795137779766117 |

Variance can reward blur or bias; ideal error and wave/residual readings remain
paired with it. The flat noise-off outputs match between modes and have about
0.040DN window RMSE from representation/quantization. Textured noise-off window
RMSE remains about62–63DN in both modes against the unquantized ideal; a small
candidate-minus-baseline change does not establish accurate reconstruction.

All486 descriptive review flags are false. Their absence is not a quality
pass. The maximum absolute-error worsening still reaches43.64672741937602DN
inside W on flat R/seed743 at native(202,104), and53.469565880827304DN over the
whole flat output at(31,231). Textured maximum worsening is4.984451056687249DN
inside W on G/seed743 at(210,107), and12.007995727473826DN over the whole output
on B/seed727 at(307,86). These movements are measured against the same ideal
at each native site, with signed before/after values retained in the readout.
They are not claimed defect causes. No output-derived region or reference is
used to select these extreme values.

**Current disposition: retain experimental weighting and current HardFloor
default.** The first completed reading supports substantial flat-region noise
reduction, much smaller textured-region changes and retained sparse costs.
The new model can express a depth boundary, but this one fixed scene is not a
physical or cross-capture generalization. A separate decoder, temporal estimator
and least-squares implementation will verify the full fixed diagnostics before
the milestone is declared complete. No parameter sweep or new quality bar has
been introduced after these readings.
