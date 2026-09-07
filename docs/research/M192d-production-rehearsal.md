# M192d — production rehearsal of the prospective observer

**MEASURED:** all seven registered native N33 renders produced byte-identical
complete TIFFs and decoded pixels, matching the archived M192 same-input
worker8 receipt. All seven also passed M192c's prospective complete-interval
and coverage checks. This establishes the observer's non-perturbation for the
named production configuration. **Separate artifact review verified the actual
TIFF strips, both identities, execution bindings and retained CPU/timing evidence.**

The largest complete interval was **42.4173 ms**, below the 100 ms criterion;
minimum scheduled coverage was **0.9990604**, above 0.90. No interval crossed
the 50 ms incident trigger. This short rehearsal therefore supplies no observed
long-stall cause, and cannot identify the cause of M192's earlier stalls or
timing transition. The full M12 certificate remains one PASS and three
UNMEASURED bars. No old reading or bar was changed.

## Frozen scope and command

The [preregistration](../../experiments/m192d-production-rehearsal/preregistration.md)
was written before the runner and execution, following the independently
verified M192c commission. It names the prior-art search and limits.

Executed from the repository root, exit zero:

```powershell
python -B experiments/m192d-production-rehearsal/run.py
```

The complete package is
[`out-20260907-090514-892948`](../../experiments/m192d-production-rehearsal/out-20260907-090514-892948/summary.json),
completed `2026-09-07T09:09:03.529973+00:00`. It retains seven records, actual
stdout/stderr logs, before/after input manifests, source/binary/sidecar freeze,
progress and terminal summary. Each record names the retained local TIFF under
the experiment's ignored `work/` tree. Those images are not committed as heavy
binaries; their byte and canonical pixel hashes are retained.

Product lineage is the existing executable from M192:
`e93f0bde695961d53cbd66587a060a41552b4a63`, binary SHA-256
`89482ACD60C4E39A22F763B2E722754804430E955546EA96F7AE7CA4C7EA1032`.
It was hashed and executed, not rebuilt. The concurrent M194 source change is
not the product tested here.

Input: first 33 filename-sorted ARWs in the already registered development
stack `D:\personal\macro\bee-1-cpl`. The archived N33 sidecar was copied into
this experiment and checked against its frozen SHA. Each render used worker8,
Pyramid gate2, Catmull-Rom, Scale coverage, linear sRGB and full-resolution MHC
demosaic, exactly as registered. All STREHL/thread variables were cleared before
setting the isolated worker, cache, sidecar and temporary paths. Actual argv,
environment, output path and terminal execution markers are recorded.

One off-mode warmup precedes complete off/on/placebo and placebo/on/off sweeps.
All seven outcomes are retained; none was replaced or excluded. Placebo names
the process-table phase and inserts no delay. No peer process, CPU affinity,
priority or power policy was changed. All 33 selected inputs, all 300 original
M192 artifacts and the frozen source files remained byte-identical.

## Output and instrumentation evidence

Each TIFF is 7032x4688 RGB16, **197,798,956 bytes**, with the frozen lineage in
its Software tag. All seven share:

- Complete file SHA-256:
  `3309E33318C701FB75C55507BFB49AD279D8950492B592EC247DBE2D1193AC9E`.
- Canonical decoded pixel SHA-256:
  `6EFC261E892DCDB5D492AD3FD79BDC7E5A208D93D0227A41B258FB3B900F9B89`.

These also match M192's `native-n33-w8-r1` receipt. Independent bit mutations
of actual file/pixel byte copies changed the corresponding digest; the original
files were untouched. A changed output, wrong shape, partial fold or different
terminal configuration could have failed this check. No sharpness or image-
quality inference follows from unchanged bytes.

| Invocation | Mode | Wall seconds | Complete max interval ms |
|---|---|---:|---:|
| warmup | off | 32.721 | 31.862 |
| forward | off | 32.021 | 38.966 |
| forward | on | 32.081 | 33.289 |
| forward | placebo | 32.000 | 32.894 |
| reverse | placebo | 31.920 | 36.824 |
| reverse | on | 31.920 | 42.417 |
| reverse | off | 31.870 | 33.650 |

The final raw host CPU counters reproduce every stored host busy delta, and
raw Job accounting reproduces every product CPU reading. These are explicit
recorded consistency checks, not proof of the accuracy of Windows counters.
The maximum recorded Job peak is **3,072,253,952 bytes**; it describes this
N33/worker8 rehearsal only, not the registered N299 or scaling populations.

Bounded retention behaved as declared. Diagnostic arms evicted 12,494–12,578
phase events and all modes evicted 2,186–2,270 memory observations; none evicted
an incident or telemetry snapshot. The last events alone therefore cannot
reproduce every whole-run maximum. Aggregate phase maxima/counts and raw
boundary counters remain available. Long-run retention with explicit losses
was already independently commissioned in M192c's overflow control.

Largest recorded phase maxima across diagnostic arms were sleep/wakeup
42.2847 ms, telemetry36.2450 ms, temp scan9.9581 ms and process-table7.4567 ms.
These are observed maxima on four diagnostic renders. They are not a ranking
of historical stall causes: phase wall duration also includes descheduling,
and no long incident occurred in this rehearsal.

## Timing limits and next action

**MEASURED descriptive timing:** per-mode minima were off31.870452 s,
on31.920296 s and placebo31.920285 s. The approximately50 ms difference between
these minima is an observed comparison, not a general overhead bound. Paired
on-minus-off differences across the two sweeps have mean54.850 ms and
SEM5.005 ms; placebo-minus-off has mean14.772 ms and SEM35.062 ms. Two sweeps
on a shared host do not establish a precise cost or a speed improvement.
The off-minus-off row is identically zero by construction and is not independent
confirmation. The synthetic known-slow workload in M192c supplies timing power.

No need for another full systems run is established by this rehearsal alone.
The diagnostic now has a native-output non-perturbation check; the prospective
campaign still needs durable adapter/record integration, a frozen protocol
version, and a bounded timing rehearsal that can assess the unresolved
execution-state transition without replacing old repeats. Production truth
commissioning and geometry adapter work proceed alongside that bounded work.

Applicable-rule execution: realizable output/terminal/mutation failures
(11/20/35/36); actual on/off/placebo output hashes (26); selected-input and
original-evidence hashes; isolated sidecar/cache/temp (45/47); opposite complete
sweeps, minima and SEM with descriptive scope (16/39); retained whole outcomes
and honest bounded losses; no peer authority or termination (27/49). No RAW
decoder source, sealed capture, image-quality metric, optical claim, Rust build,
scorecard edit or SYNTHESIS fold was introduced by this rehearsal.

## Independent artifact verification

**VERIFIED BY RUNNING, separate reviewer `directional_detail`.** The independent
choices were written in
[`independent-preregistration.md`](../../experiments/m192d-production-rehearsal/independent-preregistration.md)
while the seven registered calls were still running and before inspecting their
completed records. Outcome validation waited for the final summary. No additional
native call was necessary and no saved command was executed by the reviewer.

```powershell
python -B experiments/m192d-production-rehearsal/independent-verify.py experiments/m192d-production-rehearsal/out-20260907-090514-892948
```

The result is
[`independent-verification.json`](../../experiments/m192d-production-rehearsal/independent-verification.json).
The reviewer uses a separate `struct` TIFF parser, imports neither author runner
nor sampler/harness nor `tifffile`, and checks all 196 raster strips in row order.
All seven actual TIFF files reproduce the complete-file and pixel SHA-256 above,
the 7032x4688 RGB16 geometry, and the archived `native-n33-w8-r1` result. Actual
argv/environment, sidecar and executable hashes, terminal evidence of 33/33
folded frames and eight execution threads, and both raw log files were checked.
The 33 input files, 300 original artifacts, five source/binary freeze members and
local sidecar were independently rehashed and agree with the frozen manifests.

The review changed the stimulus choices as well as the parser. On the **first
diagnostics-on** TIFF, a read-only patched copy of Software byte 998 changes the
file hash but leaves the pixel hash unchanged. A separate patch to the high byte
of blue at `(x=7003,y=4671)`, file offset 197121925, changes both hashes. The empty
patch placebo and an original-file re-read reproduce both original hashes. These
are valid TIFF views, not a header-breaking mutation or the author's selected
offsets. They test why complete-file and pixel identity are separate checks.

Raw CPU verification uses `kernel + user - idle` at each host boundary and
`user + kernel` in final Job accounting, not only the stored redundant total.
Every host/product delta reproduces. Exact observer CPU start/end values were
**not retained**; its boundary difference and interior cumulative snapshots are
available, so that exact observer boundary cannot be independently reconstructed.
Separate changed-CPU-field, changed-phase-duration, inverted-sampling-disposition
and wrong-dimensions controls all reject through the reviewer's checker.

For every run, the maximum complete observation interval is independently
reproduced from the retained final 1,000 observation timestamps, including the
saved closure interval; all seven pass the unchanged 100 ms and 90% coverage
conditions. This does not reconstruct every earlier interval. The enabled arms'
phase event counts plus dropped counts agree exactly, and retained phase durations
match their timestamp endpoints. All three final phases are present in each
enabled trace. The four enabled traces contain no 50 ms incident. Their bounded
tail no longer contains the originating events for some smaller phase maxima,
including every process-table maximum. Those values remain aggregate evidence;
they are not independently reproduced from missing endpoints. The 42.2847 ms
sleep/wakeup maximum and 36.2450 ms telemetry maximum do retain endpoint evidence.

The four enabled runs retain **1,279** telemetry snapshots, with raw per-core CPU
fields for 32 logical processors. Their host arithmetic, product CPU bounds and
cumulative observer counters are consistent. The recorded power query reports
4300 MHz throughout, idle-state values 1/2/3 and a constant scheme GUID
`381b4222-f694-41f0-9685-ff5bb260df2e`. Sampled observer CPU numbers vary. These
are the available OS query values, with the M192c documented semantics; 4300 MHz
is not an effective clock measurement. Effective frequency, residency, complete
thread migration, ready-queue latency, useful work versus spinning, and thermal
telemetry remain explicitly unavailable.

The opposing-sweep timing minima/deltas reproduce the descriptive values above.
This verification establishes native-output non-perturbation and the retained
sampling evidence for these seven calls. It does not identify the cause of the
historical stalls or execution-state change, license a full M12 result, or make
an image-quality, geometry, or SOTA claim.
