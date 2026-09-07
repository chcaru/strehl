# Wait for completion of the owned Job under the original bounds

2026-09-07. This is a prospective process-only amendment after the retained
private-campaign-1 refusal. It changes no image, coordinate, numerical, noise,
quality or calibration bar. The first private attempt and original11 controller
results remain unchanged and failed/unvisited populations are not admitted by
this amendment. Root owns implementation and execution release; this author
performed source/metadata reads only, with no child, image or RAW execution.

## Actual refusal and limits of diagnosis

The archived attempt was released at f9ee06a4. Its first actual Rust00-plan
launch returned direct exit0 with a complete200-byte log, but the helper refused
on `child left an active descendant`. The later final accounting retained
active_processes0, total_processes2, total_terminated_processes0 and no cleanup
errors. The launch receipt is
private-campaign-1/worker/grid/00-plan-launch.json, SHA256
`65967fd8f44fac4afbf428d68fe0c5ed0d7711da74df2722874a27139010287d`.
The failed release bound the old helper SHA256
`1dba8d87c8818aecf98078d1a926e5ff9c059a7d242cf5c46fcc962f14dfc5ab`.

Source explains the refusal boundary: after direct-process wait and pipe EOF,
the old helper made one Job observation and required immediate zero active
processes. Its finally block overwrote that observation. The recorded positive
active count, its duration and process identity therefore cannot be recovered
from the final zero count. Do not claim a particular descendant, timing race,
or successful unforced termination was proved by this receipt.

Microsoft defines ActiveProcesses as the current Job association count and
TotalProcesses as a lifetime count. TotalTerminatedProcesses counts limit-based
terminations; zero is not a general witness that TerminateJobObject was never
called. Job CPU includes active and terminated processes. These meanings inform
the interpretation, not a new experiment. [Microsoft accounting structure](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).

Children normally inherit Job membership. Parent-process completion does not
establish complete Job completion, and closing the last kill-on-close Job handle
can terminate remaining members. A Job handle is not used here as a generic
wait-for-all-success event; retain explicit accounting polling. [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

## Narrow helper change

Keep the suspended creation, assignment-before-resume, pipe pump, log cap,
observed memory limit/readback, original direct exit code and error cleanup.
After both the direct process has exited and the log pipe reaches EOF, continue
observing the same Job until its actual active_processes is zero. Each waiting
iteration calls the existing observe() and caller check(), then sleeps briefly
if needed. Use the existing started clock and supplied CPU/wall/committed-memory
ceilings. Do not reset any clock or counter, grant a fixed new grace period,
subtract direct-process work, stop at a fixed observation count, or ignore
external source/artifact checks. CPU and committed-memory totals are checked
again after final accounting when no earlier failure already explains refusal.

A finite positive active count during this drain is unfinished work under the
original allowance, not immediate evidence of a leaked or dead child. An
exceeded original bound still refuses and terminates only the owned Job through
the existing cleanup path. Cleanup's bounded five-second termination observation
is failure cleanup, never extra successful-execution allowance. Direct nonzero
exit remains a reported nonzero value: the helper's existing nonzero control is
not silently converted to a helper exception or a successful caller result.

New mandatory receipt fields are exactly:

- direct_exit_observed: bool.
- pipe_eof_observed: bool.
- post_exit_drain: initial_accounting,last_accounting,observations,
  observation_count,completed,started_wall_seconds,ended_wall_seconds.
- termination: attempted,before_accounting,succeeded.

Drain observations are the first at most16 actual `{wall_seconds,accounting}`
records. observation_count continues counting every poll; last_accounting is
updated independently after the list fills. Observation retention never affects
the drain condition. initial_accounting preserves the first actual sample.
completed is true only when zero active was observed on the ordinary drain
path, not when cleanup forced termination. Times are elapsed on the original
helper clock. Before drain entry, post_exit_drain is null. At entry its absent
accounting/times may be null, observations is empty and count is zero.
termination begins attempted=false,
before_accounting=null,succeeded=false; attempted marks the actual API attempt,
succeeded becomes true only for the actual API success return. Final Job and
memory receipts remain separately authoritative observations.

These fields do not prove nonexistent descendants or a universal timing bound.
They expose the exact previously unretained consumer condition. No new observer
callback, completion-port framework, unbounded poll log or process-name heuristic
is required. First failure and secondary cleanup errors remain distinct.

## Fixed process controls: unchanged11 plus appended3

Keep the original ordered11 modes and their settings/predicates exactly:
valid,nonzero,exact-log,overflow-log,timeout,nested-timeout,memory-allowed,memory,
late-log-binding,changed-input,restored. Append exactly drain-finish,
drain-persist,drain-restored, so the new complete population contains14 cases.
No original assertion is excluded. Preserve the original source snapshots and
all earlier results. The updated controller/parent consumer must explicitly
require the fresh complete14-case result bound to the amended helper; the old11
PASS alone cannot commission this new drain behavior.

Each appended parent starts one actual Python descendant with stdin/stdout/stderr
set to DEVNULL and CREATE_NO_WINDOW. This deliberately allows the direct
parent's pipe to reach EOF while the descendant remains live. The descendant
writes a fresh startup JSON marker, at most1024 bytes, naming its actual PID and
the direct parent PID. The parent waits only for bounded startup, checks that
the Popen child is still live, prints exact observed/requested/parent identity
markers, flushes and exits0 without waiting for the descendant. The descendant
later writes a separate fresh completion marker and exits0. All marker paths
are inside the new controller output directory, with exact fixture identity;
old/missing/mismatched/oversized startup files cannot be accepted as readiness.
PID equality must link the requested child to the actual executing descendant,
and both must differ from the direct parent. No inherited stdout handle is used
as the descendant's lifetime witness.

| Appended mode | Descendant delay after startup | Helper original wall | Intended result |
| --- | ---: | ---: | --- |
| drain-finish |2 seconds |10 seconds | Complete naturally after direct exit and pipe EOF |
| drain-persist |30 seconds |5 seconds | Original wall refusal while descendant remains live |
| drain-restored |2 seconds |10 seconds | Same healthy fixture restored and complete |

Each retains the existing10CPU,65536-byte log and64MiB committed-memory call
bounds. The complete controller retains its existing120-second wall ceiling;
no test can reset that complete-population clock. The new14-case release is
finite. Marker/log/receipt artifacts are retained; they are metadata, not three
new images. Startup delay or system load can cause a control refusal; it never
authorizes a retry or cap enlargement.

Both healthy cases must show actual direct exit0, pipe EOF, at least one drain
observation with active_processes>0, eventual ordinary completed=true and final
zero active accounting. Require empty errors/cleanup errors, no termination
attempt, correct actual child identity and the completed descendant's retained
marker. The completion marker plus ordinary zero-active drain distinguishes
natural completion from kill-on-close cleanup. Do not merely sleep and infer
the interesting condition occurred: if observation misses the overlap, the
control is unpowered and must refuse.

The persistent case must show startup and the same direct-exit/EOF/positive-active
drain witness, then exactly `ValueError('child wall bound')`. It requires
completed=false before cleanup, no completion marker, an attempted successful
owned termination, empty cleanup errors, terminal_job_accounting=true and final
active_processes0. A startup timeout, absent identity, unrelated process error,
direct nonzero exit, CPU/memory fault, missing Job accounting or immediate
active-descendant exception is not this negative control's intended pass.
The restored arm follows that refusal using new files and the healthy setting;
it must reach the same actual drain path and complete, with no leaked process
or stale marker carrying across arms.

## Rejection power and release

The old immediate-active refusal loses the first powered healthy companion.
Skipping the drain or treating direct exit/EOF as complete loses the required
active witness/completed marker or persistent timeout. Dropping the original
wall check lets the30-second persistent descendant outlive its5-second bound
and cannot pass the expected refusal. Killing remaining children on the success
path loses termination=false and the completion marker. Returning terminal
active0 after cleanup as ordinary completion loses the completed=false negative
and explicit termination record. Forging a descendant name without executing
one loses the linked startup/Popen identity and actual positive Job observation.
Original memory/log/nonzero/source controls continue exercising their actual
paths; they are not claimed as new isolated post-exit CPU or memory stimuli.

The same original-clock checks are required by source inspection as well as
the actual wall negative. These three controls do not separately prove every
possible CPU/memory boundary sequence; no such universal claim is authorized.
The helper's final accounting still has to satisfy the caller's original caps.

Root will freeze source, exact new14 command and inputs before executing any
process control. The helper belongs to the actual compiled build closure, so
the next intended private attempt requires a new build3 and freshly bound
producer/common releases; do not reuse build2's source authority for changed
helper bytes. The retained private1 plan/refusal is not overwritten or mixed
with that future run. No TIFF, RAW, numerical or quality work is added by this
controller amendment.
