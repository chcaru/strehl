# M192e rehearsal1 — saved sampling diagnosis and next attribution boundary

READ-ONLY DERIVED diagnosis, 2026-09-08. No source/result was changed, no RAW or
TIFF payload was opened, and no sampler, control or product was rerun. This is
the author's bounded diagnosis; independent actual-outcome review is separate.

The fixed rehearsal has identical outputs but remains integration-failed.
Only the persistence-off arm violates the unchanged100ms maximum. The result
does not support blaming checkpoint serialization or fsync for that rejection.

| Persistence mode | Maximum complete interval ms | Coverage | Samples / missed scheduled intervals | Checkpoints | Sampling |
|---|---:|---:|---:|---:|---|
| off |117.8844 |0.9955877718247715 |3159 /14 |0 |FAIL |
| on |54.4005 |0.9816770186335404 |3161 /59 |31 |PASS |
| placebo |50.1861 |0.9801242236024845 |3156 /64 |31 |PASS |

These are saved observations from the actual once-only run, not a timing
benchmark. Mode order and host state differ, and the persistence placebo does
the same serialization/write work as on; it is not an fsync-removed treatment.
No subtraction, new denominator, relaxed100ms bar or retrospective pass follows.

## The actual rejecting interval

The off monitor's retained incident preserves its initial observation gap:

- monitor start:33814477751300 QPC nanoseconds;
- first recorded phase starts:33814589750900;
- first memory observation ends:33814595635700.

DERIVED:111.9996ms lies between monitor start and the first phase. The remaining
5.8848ms runs from that phase start to the first observation; the recorded
process-table query consumes5.7187ms. These sum to the exact117.8844ms maximum.
This is poll0, when the persistence adapter is not installed and its actual
checkpoint count is zero.

The frozen sampler starts the interval clock before its observer/system CPU
query, host memory status, Job creation, stream opening, suspended Popen,
assignment and resume. Its first timed phase is sleep-wakeup after those steps.
Those startup operations have no individual retained QPC brackets. Therefore
the111.9996ms identifies a source region, not Popen, process creation, disk,
antivirus, scheduling, warmup, Job assignment or any other individual cause.
The previous phase clock cannot explain time before it started.

All three final-closure intervals are small:0.0467,0.5236,0.0322ms respectively.
Each final trace retains exactly one >50ms observation-gap incident and zero
incident evictions. The on/placebo first observations are no longer retained;
absence of a startup incident only bounds their startup interval by the50ms
incident trigger, not an exact startup measurement.

## Checkpoint timing and retention are a separate finding

On's54.4005ms maximum spans polls1999→2000; placebo's50.1861ms spans1899→1900.
Both follow the every100th observation where the adapter synchronously saves
a checkpoint. The saved event context brackets untimed observer work between
the preceding process-counters end and the same poll's job-accounting start:
54.2791ms for on and49.9223ms for placebo. Frozen source places the payload
snapshot, JSON serialization/hash, forced directory check, padded4MiB stage
write/fsync, replace and full readback/hash in that interval.

This is strong timeline localization of the synchronous callback path, but
not a measurement separating JSON, filesystem latency, hash work, directory
scanning and host descheduling. The callback has no own phase/thread-CPU
bracket. Do not name fsync as the measured cause.

Among the additional retained boundary brackets, on has30.1092–34.4685ms and
placebo30.4485–35.3267ms. Ordinary non-boundary brackets in this retained subset
reach0.172ms and0.312ms respectively. The corresponding off subset has no
checkpoint work and boundary brackets0.0075–0.0149ms. These are selected
retained-tail descriptions, not whole-run distributions or an isolated
cross-mode causal estimate.

Only generations29/30 survive for on/placebo. Each carries1000 observations
and4096 events; its last observation is before the write, not a completion
timestamp. On generation29/30 ends at33877231168000/33878250896500; placebo at
33909999314700/33911019157600. Their payloads are approximately989–990KiB
before padding to4MiB. The actual31 completed writes in each arm imply124MiB
stage-write traffic per arm (DERIVED31×4MiB), separate from final retained
extents and from the initial reserved-slot writes.

Final observation/event evictions are off2159/12333, on2161/12345,
placebo2156/12318. Telemetry and incident evictions are zero. Combining surviving
checkpoints with final observations recovers only polls2000–3160 on
(1161 rows),2000–3155 placebo(1156), and2159–3158 off(1000). Incident context
preserves the earlier decisive boundaries, but not every evicted observation
or checkpoint completion time. Recoverable snapshots remain INCOMPLETE and
cannot certify the full history.

## Consumer decision before any new version

M192c's published consumer is attribution of a >100ms observation interruption,
including final closure. Its frozen implementation also counts the interval
from monitor start to first observation; that is a code boundary, not a newly
published exposure definition. Its100ms/90% rules remain unchanged here. Its
phase list omitted startup. M192e now supplies
an actual initial gap the existing phase list cannot attribute. The smallest
next change is to extend attribution, not change the acceptance clock.

There are distinct exposure boundaries. Before Popen creates the owned subject
there is no subject process to sample. CREATE_SUSPENDED prevents the primary
thread from running until resumed; it does not establish zero initial process
memory or justify deleting the entire pre-resume interval from a process-memory
contract. Microsoft documents that primary-thread condition in
[Process Creation Flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags).
Application-thread dynamic allocation exposure begins after resume; process
creation, initial memory and Job membership remain separate quantities.

Any later exposure-specific metric would need its own published consumer,
creation/assignment/resume identity, and actual assigned-suspended baseline
before execution. That is a future contract choice requiring independent
review. It cannot reclassify this run or silently replace its old maximum.

## Smallest prospective attribution change

After the independent reviewer confirms the original boundary, prepare a NEW
version confined to startup instrumentation:

1. Retain the exact old monitor start, last_observation initialization,
   next_sample/missed arithmetic,100ms/90% admission and final closure.
2. Add bounded QPC/thread-CPU entry/exit records for initial system counters,
   host memory status, Job creation, log opening, suspended Popen, assignment,
   and the actual NtResumeProcess call. Preserve actual PID/creation identity,
   requested creation flags, call counts and native return/refusal unchanged.
   The assignment and resume calls need separate observation seams; wrapping
   their combined helper cannot locate the boundary.
3. Use only five bounded private null-child calls: instrumentation off/on/
   label-only placebo, a fixed150ms setup delay immediately before Popen,
   and a fixed150ms delay immediately after actual resume but before first
   observation. Same existing deterministic null child/output each time.
   This does not repeat the old64-arm phase commission or three product calls.
4. Require both planted gaps to fail the unchanged100ms criterion and the
   appropriate new bracket to record at least140ms. Assert the setup delay
   precedes actual process creation and the other follows actual resume.
   Preserve untreated host-induced failure; do not rerun to obtain a green.
   Require byte-identical deterministic child output across the five calls
   and retain each full actual invocation/terminal Job/return outcome.
5. Record old whole-interval metrics plus descriptive startup brackets only.
   No product, RAW, full133 campaign, timing ranking or exposure-specific
   admission metric is added. A proposed10CPU/20wall finite private envelope
   and small metadata family must be independently reviewed before execution.

An explicit checkpoint-save bracket may later improve attribution of the
passing30–54ms intervals, but it is not needed to diagnose the actual off
failure and is not bundled into this smallest startup patch. Changing padding,
checkpoint frequency, serialization, fsync or concurrency now would change a
different mechanism before the rejecting one is identified.

## Evidence and read-only commands

Inputs were the three actual record.json, adapter.json, monitor.json and two
trace slots under rehearsal-1/records/native-n33-w8-{off,on,placebo}; the final
bound result is rehearsal-1-verification.json. The monitor SHA256 values are:

- off:158bf5b795c80911f5a4c50ef5888ae76602a54b53168fe4df1d6d77ed463ca3
- on:d0b8e5827f36b94799a3cc9375f2aa10fd417da04735a1f46897ccad55ec3732
- placebo:c9ef6eb3efe790ad8cf1b7858aba18938dac533d090150b22f181752536338b6

The read-only commands executed used the selected Python with -B and only
stdlib json/pathlib/hashlib. One selected saved scalar fields/incidents; a
second merged retained observation/event dictionaries by poll/timestamp,
checked exact duplicate rows, and subtracted their saved QPC endpoints.
No subject module was imported or evaluated. Source reads inspected
sampler.py monitor/Trace, run.py install_trace and durable.py Checkpoint.save.
The held M192e sources stayed run37090/aedfd86f… and
durable15166/41b97a63…; independent actual source/binding admission is owned
by the non-author reviewer, not this diagnosis.
