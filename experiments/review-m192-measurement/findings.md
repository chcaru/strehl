# Completed M192 measurement — diagnostic continuation

The existing certificate remains **identity PASS; memory, memory scaling, and
timing UNMEASURED**. This review changes no threshold and selects no replacement
repetitions. The completed 133-record package is intact. All observations below
come from the frozen results directory, not a new product run or RAW access.

Prior reports supplied by the root's topic search: `M139-m12-campaign.md`,
`M172-m12s-closure.md`, `M172-memory-planner-handoff.md`,
`M178-m12s-adjudication.md`, `M182-memory-budget.md`, and
`M192-campaign-recovery.md`. This is a continuation of that measurement work,
not a new milestone or a rediscovery of the repaired reduction topology.

## Memory: two maximum-gap failures, not low overall coverage

**MEASURED from frozen records:**

| scored run | maximum gap | median gap | coverage | Job peak | sampled peak |
|---|---:|---:|---:|---:|---:|
| N299/W8/R3 | 1163.6997 ms | 10.0030 ms | 0.9903924 | 3,072,663,552 B | 3,072,614,400 B |
| N299/W8/R6 | 399.4340 ms | 10.0026 ms | 0.9971401 | 3,072,536,576 B | 3,072,507,904 B |

The other 88 scored native runs have maximum gaps at or below 41.064 ms.
Every scored native coverage ratio exceeds 0.99, comfortably above 0.90.
The unfulfilled requirement is the separate **100-ms maximum-gap** limit;
the verifier's combined `UNMEASURED_SAMPLING_COVERAGE` label does not mean
that the observed 99% coverage was rejected against a 90% threshold.

The global Job peak is 3,077,963,776 B. Across all 90 native scored runs the
largest Job-versus-sampled peak difference is only 65,536 B. This corroborates
the bounded-memory observation, but does not retire the frozen sampling rule.
Both failed runs report one process, zero observed temp-file bytes, and low
mean external busy fractions (2.697% and 1.878%). Means cannot rule out brief
stalls. Neither record identifies another process as their cause.

**VERIFIED code limitation:** `m12-harness.py::monitor_command` retains maximum
and median gap statistics, but neither the timestamp of the bad gap nor its
duration split by operation. The loop timestamps before calling
`job_process_ids`, potentially `process_table`, `process_counters` (which opens
and closes a process handle on every poll), `job_accounting`, `job_memory`,
and every tenth poll `tree_bytes`. It then sleeps on the same thread. A long
wait for scheduling and a slow native/filesystem call both appear as a late
next iteration. The record cannot distinguish them. Native runs have only
boundary host counters; their per-second trace exists only for the later
modulo sweeps. No causal assignment to sleep, scanning, handle open, GC, host
load, or power state is supported by these records.

## Timing: an abrupt performance change contaminates one reversal pair

The independently recomputed raw-minimum spread is **0.3556937%**. The three
paired upper spreads are **5.6879101%, 0.4991099%, 0.7972423%**. The first
pair therefore makes the registered answer inconclusive; dropping it would
be outcome-based selection.

**MEASURED by reading a different evidence path:** between N97/R2 and N96/R2,
wall seconds/frame drops **10.3272%**, from 0.8805188 to 0.7895860.
The product's own fold log moves from 84.9 seconds/97 frames to 75.3/96, so
this is not merely an outer-monitor wall-clock artifact. Product CPU
seconds/frame drops from 6.3115335 to 4.9261068, while the external busy
fraction rises slightly, 1.6905% to 1.9879%.

Comparing identical N across repetitions gives the same result without changing
the input extent: N96/R1 to N96/R2 speeds up **10.2537%** in wall/frame and
**21.1638%** in product CPU/frame. The first seven scored modulo invocations
are near 0.880 seconds/frame; the remaining seventeen are near 0.788–0.800.
The performance transition occurs inside the reverse sweep, which a reversal
pair cannot cancel as though it were smooth drift. All four frame counts are
subsequently observed in the faster state.

The per-second sweep traces are valid, with their largest observed gap below
1.017 seconds. This is not missing CPU telemetry. The telemetry does not record
effective clock rate, per-core residency, thread migration, power mode, or
spin-versus-useful CPU time. **UNRESOLVED:** processor scheduling/frequency,
power behavior, cache behavior, or another execution-state change. These are
possible explanations, not measured causes. `UNMEASURED_HOST_CONTENTION` is
the registered disposition, not proof that contention caused the change.

## Next concrete engineering action

Commission an instrumented copy of the sampler on synthetic child workloads
before spending another full product campaign. Keep the existing sampler and
completed evidence unchanged. Register the following before the experiment:

1. Timestamp every polling interval and retain a bounded trace around any gap
   above a diagnostic trigger below 100 ms. Bracket sleep/wakeup, Job queries,
   process-counter calls, process-table refresh, temp-tree scan, and final
   accounting separately. Record observation timestamps as well as iteration
   starts, so a slow final poll cannot disappear when the loop exits.
2. Supply a null child plus known allocation/release pulses and a child-spawn
   case. Inject a 150-ms delay into each named measurement phase in turn.
   Every injection must be localized and fail the unchanged 100-ms criterion;
   the untreated and label-only arms must retain coverage. Preserve the Job
   counter and independent child pulse log to expose missed peaks.
3. Record co-timed host CPU plus product and observer CPU separately. Where
   accessible, record actual per-core frequency/utilization, scheduling/core
   placement, and power-state changes. Assert missing telemetry explicitly;
   a nominal CPU specification is not a measurement of the run.
4. Use short, repeated fixed-work controls to separate clock/scheduling changes
   from changing N. Verify timing on an intentionally slowed control and keep
   every registered repetition. Compare instrumented versus original sampler
   overhead and output hashes under a null and a controlled load generated by
   this experiment itself, never by terminating or pausing a peer.

Only after localizing the stall should implementation change. If temp scanning
is responsible, decouple that scan; if process-handle operations are responsible,
test retained handles with lifetime/PID-reuse controls; if observer scheduling is
responsible, commission placement or a helper-process design. **Isolation is a
hypothesis to test, not an established remedy.** A new full M12 run must still
contain all registered repetitions and use unchanged acceptance bars. Its
observer version, deployment settings, and workload protocol must be frozen
before measurement. The current campaign cannot be repaired retroactively.

## Reproduce this review

```powershell
python -B experiments/review-m192-measurement/diagnose.py
```

`diagnosis.json` includes every modulo row, same-N temporal changes, the failed
sampling rows, pair calculations, and SHA-256 values for every input read.
The script re-hashes those inputs after analysis and asserts equality. Its
constant-series and planted-step controls distinguish no change from a 10%
change, and its sampling controls reject both an excessive gap and insufficient
coverage while accepting a valid pair. These are diagnostic checks; re-reading
the same bytes is consistency evidence, not independent certification.

No original campaign, product source, protocol, corpus file, or peer process was
modified. Nothing from this review was committed by its author.
