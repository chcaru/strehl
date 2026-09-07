# M192c — phase timing for the systems sampler

**MEASURED, prospective synthetic commission passes after one disclosed launch
correction.** The complete second run contains 64 arms and passes all 60 frozen
checks. All 11 injected 150 ms stalls are localized to their intended phases and
fail the unchanged 100 ms maximum criterion. The ordinary and label-only arms
retain sampling coverage and deterministic output bytes. **Independent synthetic
review passes within this scope; production rehearsal remains the next step.**

The most useful result is the final-poll control: its old loop-start maximum is
`10.4026 ms`, but the added final-closure measurement is `150.1322 ms`. Coverage
is `1.0` in that arm. The prospective diagnostic exposes this planted tail delay;
the archived M192 aggregate could not. This does **not** establish what caused
M192's historical stalls or its timing transition.

M192's certificate remains identity PASS, memory/scaling/timing UNMEASURED.
There was no product or acceptance-bar change, RAW or holdout access, full M192
rerun, process termination, peer pause, or host reservation.

## 1. Prior decisions and consumer

Read the current [program plan](../proposals/2026-09-sota-program.md),
[measurement diagnosis](../../experiments/review-m192-measurement/findings.md),
[M192 terminal verification](M192-terminal-verification.md),
[campaign recovery](M192-campaign-recovery.md), M139-m12-campaign,
M172-m12s-closure, M172-memory-planner-handoff, M178-m12s-adjudication, and
M182-memory-budget. This is the diagnostic continuation already requested by
those records, not another memory-reduction implementation.

The mechanical `prior_art.py sampler stall` search returned lexical matches
on *resampler*. Those are not sampler-stall evidence; the root's campaign/memory
topic search and named reports supply the relevant history.

The consumer is a future observer's ability to identify **which measurement
phase contained a long interval**, while retaining memory observations and Job
peaks. It is not yet a remedy for an identified slow phase. No trace here
identifies sleep scheduling, filesystem work, or handle queries as the historical
M192 cause. A phase's elapsed time includes time descheduled while executing it;
localization alone does not separate kernel work from scheduling delay.

## 2. Reproduce and inspect

From `C:\dev\blog\death-of-software\projects\strehl`:

```text
python -B experiments/m192c-sampler/commission.py
```

Each invocation creates a fresh timestamped directory and retains all arms.
Python `3.12.10`, psutil `7.2.2`. `OMP_NUM_THREADS`, `MKL_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS` are `1`. Every child command,
launch flag, output path, relevant environment value, and receipt is recorded.
The controlled load is the experiment's own fixed-work child; no host exclusivity
is claimed. The inherited low-level native queries are imported read-only.

- [Initial preregistration](../../experiments/m192c-sampler/preregistration.md)
  froze before the first run: SHA-256
  `83008526B72263FEF81F1772103DFAB17DAB66E9D15C447EC96EB9DA06B21EB8`.
- [Amendment 1](../../experiments/m192c-sampler/amendment-1.md) froze before the
  complete second run: SHA-256
  `6A0E1C00F46884859112EE1B79A88F424DE2E964108E5A7B510A485D2C6958E3`.
- [Passing summary](../../experiments/m192c-sampler/out-20260907-084722-251062/summary.json),
  with all gates, pulse/child checks, every arm ID, minima and paired deltas.
- [Source freeze and preserved-input inventory](../../experiments/m192c-sampler/out-20260907-084722-251062/source-freeze.json).
- [Diagnostic implementation](../../experiments/m192c-sampler/sampler.py),
  [synthetic child](../../experiments/m192c-sampler/child.py), and
  [commission runner](../../experiments/m192c-sampler/commission.py).

The root requested review before commit. The registrations are frozen by tool
transcript and source hashes, **not claimed pre-run git commits**. The second
run's sampler source SHA is
`3E5F8D45201176F904AC9C14177108D409D3C6E24A7AB6EAD60C1655FC662AA6`.
All five experiment sources and all **304 original inputs** were byte-identical
before/after: the 300-file completed M192 result package plus its external
campaign/verify/protocol files and the inherited `m12-harness.py`.

## 3. What was built

`sampler.py::monitor` uses the existing Job PID, Job accounting, Job memory,
process-counter, process-table and temp-scan query functions. The sampler loop
is a separate prospective implementation; it leaves the inherited monitor,
M192 runner, protocol, verifier, and completed results untouched.

The trace brackets sleep/wakeup, Job PID query, process-table refresh, each
process-counter query, Job accounting, Job memory, temp scan, telemetry, and
the three final phases. Every event records QPC start/end, poll index, wall
duration and observer-thread CPU duration. Actual memory-observation endpoints
and final-closure time supplement the old loop-start maximum. The numeric
100 ms/90% criteria stay fixed; this is explicitly a prospective endpoint
definition, not a retroactive replacement for the certificate's timestamps.

Storage is bounded: 4096 phase events, 1000 memory observations, 1000 telemetry
snapshots, and 32 incident windows with 16 preceding/following events around
50 ms triggers. Aggregate maxima and counts survive ring eviction; every
eviction is reported. **MEASURED:** no event, observation, telemetry, or incident
was dropped in the complete commissioning run. Overflow must remain visible
on longer uses; this run does not commission long-duration retention capacity.

Diagnostics-off keeps the prospective observer's ordinary memory records but
omits phase tracing and added per-poll telemetry. The separate original mode
runs inherited `monitor_command`. The label placebo uses the diagnostics path
and names an injection phase but inserts no delay. These are explicit different
observer arrangements, not synonyms for an entirely absent observer.

The prospective Job has no kill-on-close flag. It resumes its own initially
suspended child and waits for the finite workload to exit naturally before
closing the Job. The inherited original mode retains its original cleanup code;
all measured invocations completed normally, so it did not terminate a process.
No priority, affinity, power-policy, or peer-process state was changed.

## 4. First run failed; the launch fixture was wrong

The first complete 64-arm run remains
[COMMISSIONING_FAILED](../../experiments/m192c-sampler/out-20260907-084426-145611/summary.json).
Only three checks failed: Job count was four where the preregistration required
two for the parent plus short child. The intended child PID, creation identity,
and allocation had all been observed. Calling this a missed child would have
misdiagnosed the evidence.

The new launcher used `CREATE_NO_WINDOW`; the inherited observer shared its
existing console. A separately frozen
[launch attribution](../../experiments/m192c-sampler/launch-attribution.md) test
varied that flag independently at both generations. The
[observed process names and counts](../../experiments/m192c-sampler/launch-attribution.json)
were:

| Parent flag | Child flag | Job process count | Additional named processes |
|---|---|---:|---|
| inherited console | inherited console | 2 | none |
| inherited console | CREATE_NO_WINDOW | 3 | one `conhost.exe` |
| CREATE_NO_WINDOW | inherited console | 3 | one `conhost.exe` |
| CREATE_NO_WINDOW | CREATE_NO_WINDOW | 4 | two `conhost.exe` |

Command: `python -B experiments/m192c-sampler/launch-attribution.py`, exit `0`.
This identifies a **launch-arrangement confound**, not a native Job-counter
defect. The first prospective record omitted process names; the attribution
script records them, and the amended sampler retains them.

Amendment 1 matches the inherited launch arrangement at both generations.
The original exact-two-process rule is unchanged. All 64 arms were rerun; no
old row was substituted. Original v1 source files are retained byte-for-byte
under `preserved-v1/`, verified against their first-run source hashes. First-run
overhead comparisons are not used below because they included different helpers.

## 5. Stall/null controls and final accounting

**MEASURED:** all eleven single-phase 150 ms injections were the longest timed
phase, retained in an incident window, and rejected by the unchanged 100 ms
maximum rule. Each had its own label-only placebo, and every placebo passed.

| Injected phase | Measured phase ms |
|---|---:|
| sleep/wakeup | 150.2810 |
| Job PIDs | 150.3550 |
| process table | 157.2954 |
| process counters | 150.2508 |
| Job accounting | 150.4657 |
| Job memory | 150.1228 |
| temp scan | 150.6028 |
| telemetry | 151.0349 |
| final accounting | 150.3168 |
| final memory | 150.5122 |
| final poll | 150.0497 |

These are single planted observations, not latency-distribution estimates.
The corresponding interval includes adjacent work and can exceed the timed
injection itself. Untreated/label-only arms have a largest observed complete
interval of `23.0335 ms`, including the slow child; minimum clean coverage is
`0.9791667`. A zero-delay phase label does not manufacture a rejection.

The final-phase distinction has demonstrated power:

| Injected final phase | Old loop-start max ms | New final-closure interval ms | Coverage |
|---|---:|---:|---:|
| accounting | 10.5004 | 150.3859 | 1.0 |
| memory | 10.4191 | 150.5772 | 1.0 |
| poll | 10.4026 | 150.1322 | 1.0 |

The old statistic would accept each interval while the prospective complete
interval rejects it. This exposes an observer blind spot on a known input.
It does not claim that an archived final poll caused M192's bad gaps; those
archived gaps already had subsequent loop starts.

## 6. Allocation, short-child and output controls

The synthetic child independently records allocation/touch/release QPC times,
requested/committed bytes, process identity, CPU time and sampled CPU number.
The pulse commits and touches **64 MiB** for 180 ms between 150/180 ms baseline
and post-release intervals. Off/on/placebo each recorded 15/18/18 observations
in those three intervals, and private commit rose and fell by **67,239,936 B**.
That is total process-private change, including allocation overhead, not an
assertion that VirtualAlloc requested that many bytes. The requested allocation
is 67,108,864 B. Kernel Job peaks independently satisfy the frozen check.

The short child's active receipt span was `99.05–99.63 ms`; its 24 MiB allocation
was held for 80 ms. All three modes observed its PID, creation identity and
allocation, and final Job accounting counted exactly two processes. These are
useful short-child controls, **not a guarantee for lifetimes shorter than one
10 ms poll**. Kernel peaks and independent receipts remain necessary when
polling can miss short activity.

**MEASURED:** output files were byte-identical across off/on/placebo for null,
pulse and spawn; all four observer modes agreed for fixed work and null in
every timing sweep. The deliberate slow child produced the same fixed-work
output. A one-byte output mutation was rejected. Receipts contain nondeterministic
timestamps and are deliberately separate from the actual deterministic product
file; hashes are computed over that file's bytes, not an asserted digest string.

| Synthetic output | Bytes | SHA-256 |
|---|---:|---|
| null | 4138 | `9A49C14C5D46F8D541FC6B6629D1728294FDFA999D64FBE8405A4170CA489BAA` |
| pulse | 4139 | `E14063CF692EDB8376C3772A8B1A7B0CA11865660D577FA7D9238C9AEC142F01` |
| spawn parent | 4139 | `994DB4B69F6CC3F367A7289A3ADB873C063376E0653F1F8432EAF48E8FE5FAD2` |
| fixed work | 4139 | `4E3CD88D39AE552476B55487DEE31D29DB1A76FE5638E9C3BD0BC0D4FBD83B9A` |

These prove observer non-perturbation for the named synthetic files only.
No byte-identity claim about a new strehl render follows.

## 7. Observer cost and available execution telemetry

**MEASURED**, four whole forward/reverse/forward/reverse sweeps; every repetition
retained. The fixed workload performs 512 SHA-256 passes over the same 1 MiB
block. It changes neither N nor algorithm between runs.

| Workload | Original minimum wall s | Off minimum s | On minimum s | Placebo minimum s |
|---|---:|---:|---:|---:|
| null | 0.6404301 | 0.6401825 | 0.6402316 | 0.6403443 |
| fixed work | 0.2803436 | 0.2903154 | 0.2804150 | 0.2804440 |

The on-minus-original minimum differences are within **0.2 ms** in this run;
this is an observed comparison bound, **not a precise overhead estimate or
universal upper bound**. Matched sweep deltas swing by approximately one 10 ms
poll: null mean `-5.061 ms`, SEM `3.025 ms`; fixed mean `+5.147 ms`, SEM
`2.930 ms`, four paired sweeps each. Neither justifies claiming a small exact
positive or negative overhead. The intentionally slow child adds `252.280 ms`
to its own fixed-work wall time and preserves output, clearing the frozen
`>150 ms` timing-sensitivity bar. This tests an imposed wait, not thermal slowdown.

Minimum recorded observer CPU is 15.625/31.250 ms for original/on in the null
case, and 0/15.625 ms for fixed work. These counters move on coarse increments;
the zero does not mean zero observer work. Job product CPU and full host busy
CPU are recorded separately, both at boundaries and co-timed with telemetry
on diagnostic polls. Per-setting CPU minima can come from different repetitions;
they are not an additive budget. The full rows retain contemporaneous host
activity and the remaining-host fraction after product and observer subtraction.
Unlike M192's sweep aggregate, the prospective records retain exact raw
`host_start`/`host_end` CPU counters and final raw Job accounting, so those
boundary deltas can be independently re-derived. Observer cumulative
process/thread counters are retained at diagnostic snapshots, but its dedicated
boundary pair is reduced to `observer_cpu_seconds`; the exact observer boundary
delta cannot be independently reconstructed from this artifact alone.

The diagnostic retained **262 telemetry snapshots**. Available observations:

- Per-core cumulative CPU-time fields for all 32 logical processors, usable
  with successive snapshot timestamps to derive utilization.
- Actual sampled observer CPU number (15 different logical CPU numbers across
  this run), and child self-observed placement at receipt events. These are
  point observations, not an all-thread migration or residency history.
- Read-only processor-power queries all succeeded. `CurrentMhz` was 4300 in
  every recorded processor snapshot; returned current idle-state values included
  1, 2 and 3. No effective-frequency conclusion follows from the constant MHz.
- One active power-scheme GUID throughout:
  `381b4222-f694-41f0-9685-ff5bb260df2e`. No policy change was made.

Microsoft defines [CurrentMhz](https://learn.microsoft.com/en-us/windows/win32/power/processor-power-information-str)
in terms of specified maximum and throttle, and
[GetCurrentProcessorNumber](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getcurrentprocessornumber)
reports the calling thread at the instant of the call. The sampler explicitly
marks **effective frequency, per-core residency, all-thread migration history,
ready-queue latency, spin-versus-useful work and thermal sensors unavailable**.
The trace cannot assign M192's execution-state transition to any of them.

## 8. Independent verification and disposition

**VERIFIED by the root reviewer, separately from the author:**
`python -B experiments/review-m192c/verify.py` exited zero. The final result is
[`verification.json`](../../experiments/review-m192c/verification.json); every
raw record and deterministic file is retained in its named output directory.
The reviewer wrote a different child, requesting 36 MiB for a 60 ms plateau,
and ran placebo/on/off/on. All four runs observed the child's creation identity,
exactly two Job processes, and at least 32 MiB of private-memory rise and fall.
Their largest complete interval was 17.3173 ms. All four 32,768-byte outputs
had SHA-256 `E11360251D1173650CDCD20F111D8F1CA2E412F572E8B36A4DC067121C1799B8`;
an independently located bit mutation changed the digest.

The reviewer delayed native helpers directly, without the sampler's injection
flag: a 125 ms sleeping process-table call, a 125 ms CPU-active process-table
call, and a 125 ms final-memory call after both empty observations. All three
were localized, retained as incidents, and failed the maximum-interval bar;
the final-memory complete interval was 125.5665 ms. The sleeping calls recorded
zero thread-CPU fraction at the available counter resolution; the active call
recorded 0.9475. These single observations show discrimination of the planted
wait and CPU work, not their historical cause or a latency distribution.

A 5,000-event overflow fixture retained exactly the specified ring capacities
and reported 904 evicted events, 4,000 observations and 18 incidents. Incident
context remained bounded to 16 events on either side. This checks bounded
retention and honest drop counts; it does not guarantee every long-run incident
survives. All 300 original campaign files and the checked source files remained
byte-identical. An earlier passing independent invocation tested the first
empty-Job memory call; it is retained, and the final invocation deliberately
moved that delay to final accounting to exercise the missing-next-poll case.

**ARGUED:** accept the scoped diagnostic and proceed to a bounded production
rehearsal before another full campaign. Synthetic output non-perturbation does
not establish production output non-perturbation.

A bounded rehearsal can observe actual
query tails and decide whether retained handles, decoupled scans, or observer
scheduling changes deserve their own intervention. None is established as a
fix here. Effective-frequency attribution would require an independently
commissioned measurement path; reporting nominal MHz does not supply it.

Rules discharged: predeclared realizable failures and label/null controls
(11/20/24/35/36); full native Job/child consumer, no temporal/spatial confusion
(7/10); source/output byte hashes including placebo (26/47); alternating whole
sweeps and bounds plus SEM (16/39); intact failed lineage/amendment (30/31);
allocated scope and prior art (40/41); no peer authority or termination (27/49).
No SYNTHESIS fold, numerical namespace allocation, Rust rebuild, capture decode,
image-quality metric, visual verdict, or production diagnostic was introduced.
All gate output was read with exact process exit codes and without a truncating
pipeline (46). The author has not independently verified their own new code (12).
