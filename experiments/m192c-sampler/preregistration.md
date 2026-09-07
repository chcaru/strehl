# M192c sampler diagnostic commission

Frozen before execution, 2026-09-07. Root review precedes any commit. Freeze is
by transcript/source SHA, not a claimed pre-run commit. No RAW, holdout, product,
M192 campaign, scorecard bar, original harness, or peer process may be changed.

## Consumer, prior evidence, and failure inputs

Consumer: a future systems sampler's ability to locate an observed >100 ms
sampling interruption, including the final poll; not a retrospective cause for
M192's 1163.7/399.4 ms gaps. The inherited M192 certificate remains identity PASS,
memory/scaling/timing UNMEASURED. Read current 2026-09-sota-program, M192 terminal
verification/recovery, review-m192-measurement/findings, M139-m12-campaign,
M172-m12s-closure, M172-memory-planner-handoff, M178-m12s-adjudication,
M182-memory-budget. A mechanical `prior_art.py sampler stall` returns resampler
lexical false positives; the root's memory/campaign search supplies the relevant
reports above. This is the already-proposed diagnostic continuation.

The inherited monitor timestamps loop starts, so a final native call can consume
time without producing a next loop start. Preserve that legacy statistic and
add actual memory-observation end timestamps plus final-closure timestamp. Keep
the numeric 100 ms maximum and 90% scheduled-coverage rules; do not retrospectively
reinterpret archived runs. The prospective fuller endpoint is explicitly new.

Known fail inputs: inject 150 ms before a single native operation within its
timed phase. A diagnostic that omits final accounting or timestamps only starts
must fail the final-phase test. A phase label without delay must remain green.
An intentionally delayed child must be timed slower while producing the same
deterministic output. A one-byte output mutation must fail output identity.
A sampler that never sees a child or allocation must fail their positive arms.

## Frozen implementation design and controls

A separate monitor imports inherited low-level Job membership, accounting,
memory, process counters/table and temp scan functions. Original monitor remains
available for the overhead/control comparison. The diagnostic monitor creates
its own Job without kill-on-close, starts only its own suspended child, resumes
it, and waits for natural completion before closing the Job. No terminate,
kill, affinity/priority adjustment, peer pause or host hold is allowed.

Record QPC timestamps before/after these named phases: sleep-wakeup, job-pids,
process-table, process-counters, job-accounting, job-memory, temp-scan,
telemetry, final-accounting, final-memory, final-poll. Inject 150 ms once into
each named phase in separate runs. The first eligible call receives the delay;
final phases are called only after ordinary polling ends. Each injection must
have a measured phase duration >=140 ms, be retained in the bounded trace,
be the longest phase, and fail the unchanged <=100 ms maximum criterion.
No result is dropped/replaced if an untreated control has a host-induced gap.
That is failed commissioning on this host, not grounds to relax the rule.

Bound the trace: 4096 last phase events, 1000 last memory observations, 32
incidents with 16 preceding and 16 following events around >50 ms triggers.
Retain aggregate maxima/counts and report every drop/overflow. All short
commissioning traces must be complete (zero dropped events/observations/incidents).
Record phase CPU time as well as wall duration; a blocked/sleeping phase need
not have high observer CPU.

Workloads use at most 64 MiB explicit committed allocation plus Python overhead:

- null: deterministic bytes plus 0.55 s sleep;
- pulse: baseline 0.15 s, 64 MiB VirtualAlloc+touch, 0.18 s hold, VirtualFree,
  0.18 s after release; timestamp every transition independently in the child;
- spawn: parent starts a child that commits/touches 24 MiB, holds it 0.08 s,
  frees it and exits; parent waits naturally, then sleeps 0.20 s;
- fixed: 512 SHA-256 passes over a fixed 1 MiB block, with deterministic output;
- fixed-slow: same work/output plus 0.25 s deliberate sleep.

Pulse measured private commit must rise and fall by at least 48 MiB within the
logged plateau/release intervals; Job peak must exceed the sampled peak minus
1 MiB. Short-child PID and creation identity must be observed, Job accounting
must count two processes, and its private peak must include >=24 MiB. This does
not prove detection of every process shorter than 10 ms. Independent receipts
carry actual requested/committed sizes, PIDs, QPC times, CPU times and observed
CPU placement; deterministic output excludes receipt metadata.

Modes are inherited-original, prospective diagnostics-off, diagnostics-on, and
diagnostics-on label-only placebo. On/off/placebo must produce identical bytes
for each null/pulse/spawn/fixed workload. Every command must exit zero. For null,
pulse and spawn, all three prospective modes must retain >=90% coverage and
<=100 ms maximum interval including final accounting; actual control failure
is retained as failure. Product output is a real synthetic file with a known
content digest, not just an asserted hash string.

Overhead: null and fixed controlled-load workloads, four complete sweeps of
all four modes, forward/reverse/forward/reverse. Keep every repetition; report
per-setting minima, matched sweep deltas, wall/observer CPU/product CPU/host CPU.
Treat a near-flat minimum difference as a measured bound, not an exact overhead.
The fixed child is the controlled load, not an external-host exclusivity claim.
No timing acceptance threshold or performance promise is introduced. The slow
control must add >150 ms to fixed-work child wall time and preserve output bytes.

## Telemetry and honest availability

Record host busy CPU counters, Job product CPU, observer process/thread CPU,
per-core cumulative utilization counters, observer sampled CPU number, and
child self-observed CPU number. Query read-only OS-reported per-processor power
information (CurrentMhz/MhzLimit/idle state) and active power scheme. CurrentMhz
is throttle-derived OS telemetry, NOT measured effective frequency. Retain raw
query errors and explicitly unavailable effective-clock, residency, all-thread
migration, ready-queue latency, spin-versus-useful work and thermal telemetry.
Do not infer causality from unavailable quantities or a nominal CPU model.

Sources: Microsoft PROCESSOR_POWER_INFORMATION documentation defines CurrentMhz
as maximum clock times throttle; GetCurrentProcessorNumber reports only the
calling thread at the instant of the call. These are snapshots, not residency.

## Reproducible commands and preservation

From C:\dev\blog\death-of-software\projects\strehl:

    python -B experiments/m192c-sampler/commission.py

No CLI defaults are implicit: all arm settings, commands and environment are
recorded. Numeric-thread environment keys OMP_NUM_THREADS, MKL_NUM_THREADS,
OPENBLAS_NUM_THREADS and NUMEXPR_NUM_THREADS are 1. Outputs go into a new
timestamped directory under this experiment on each invocation. No deletion.
Hash original m12-harness.py, M192 campaign.py/protocol.json/verify.py and the
completed package's 300-file inventory before/after. Hash this preregistration
and all sampler/child/commission sources before/after. Root independently
re-chooses delay placement, child duration/allocation and output mutation before
any diagnostic implementation is accepted. No full campaign is authorized here.
