# Independent source review of the owned Job completion amendment

2026-09-07. Scoped source acceptance: no blocking implementation discrepancy
found against the prospective amendment. This is an independent review of
root's helper and Zeno's process controls, not an independent verification of
this reviewer's amendment prose. No process control, subject import, build,
image, numerical helper or RAW decode was executed in this review. The new
fourteen-case population remains uncommissioned until its separately released
command actually completes and is independently read.

## Exact reviewed bytes

All paths below are in experiments/m193c-output-grid. These are source hashes,
not measured process results. Parent owns the subsequent source commit and
exact command/environment release.

| File | Bytes | SHA256 |
| --- | ---: | --- |
| controller-amendment-3.md | 10792 | 0c4d13c6520512785918661b61daa2a4ada5ab7fcf3fe8cb89f02e8b51e00e7e |
| bounded-process.py | 12664 | 47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b |
| controller-child.py | 4416 | 8944b1387990a262d1ad47c44ee2bbd7de281323185a0758802f1637289d2788 |
| controller-controls.py | 18455 | 217999b5969a29224868fe731284493e04ce0ef33bd225fc4c9f3bc3f8b5b84c |
| private-grid-run.py | 22426 | 9d0c9dcc60e41ca8520152033fd931e50ccc850263f539698a296509cf83f0b4 |

The review read the complete helper, fixture and controller source, the narrow
parent-consumer delta, and their git diff against the retained pre-amendment
revision. It also read the project's M12 Job API and the prior failed launch
metadata. The first failed launch remains at
private-campaign-1/worker/grid/00-plan-launch.json, SHA256
65967fd8f44fac4afbf428d68fe0c5ed0d7711da74df2722874a27139010287d.
The initial positive active count was not retained there; final zero cannot
reconstruct its identity, duration or cause. This review makes no stronger
diagnosis from that receipt.

## Helper and consuming boundary

bounded-process.run retains one started clock, the same Job handle, original
limits and original observe/check functions. After actual pipe EOF and direct
process wait, the new loop observes before deciding completion and calls the
existing external check on each iteration. It neither resets the clock nor
subtracts the direct child's CPU. It waits only while the latest actual active
count is positive, with the same CPU, committed-memory and wall checks. The
five-second termination observation is still failure cleanup, not a successful
grace allowance. The final accounting adds CPU and memory checks beside the
existing final wall check without replacing an earlier failure.

The retained receipt matches the amendment: actual direct-exit/EOF flags;
nullable post_exit_drain; first sixteen timed accounting samples; independently
updated initial/last accounting and unbounded-in-count polling counter; actual
drain completion and elapsed times; and explicit termination attempt, pre-call
accounting and API success. Only the observation list is capped. No completion
decision reads its length. The ordinary completed flag is set after a zero
active observation and remains false if cleanup later kills the owned Job.

The original suspended launch, assignment before resume, bounded log pump,
memory-limit readback, direct exit code and secondary cleanup-error retention
remain. A clean direct nonzero exit remains nonzero; the amended helper does
not turn it into an accepted caller result.

private-grid-run.main changes only its mandatory exact ordered control list:
the previous eleven are followed by drain-finish, drain-persist and
drain-restored. Its existing successful status, empty errors, true case flags,
terminal accounting and zero active predicates remain. Thus the historical
eleven-case PASS cannot alone commission the new helper. A new build is also
required because the prior build's source closure binds the old helper.

## Re-chosen failure and companion paths

The direct child starts a real descendant with DEVNULL streams and no visible
window. Atomic fresh startup JSON records the descendant's actual PID and
parent PID; the parent checks these against Popen and its own PID, checks that
the child is still live, logs the startup hash and exits without waiting. This
separates direct exit/pipe EOF from the descendant's lifetime. The consumer
requires actual positive active accounting after both exit and EOF, so a delay
alone is not mistaken for proof that the intended overlap occurred.

drain-finish and drain-restored use two-second descendants under the original
ten-second helper wall bound. They require the same actual child identity in a
retained completion marker, at least the fixed elapsed delay, a clean ordinary
drain ending at zero, terminal zero accounting and no termination API attempt.
The restored arm uses fresh paths after the negative arm. An unobserved overlap,
startup problem, missing completion or cleanup-forced zero refuses instead of
being relabelled a healthy control.

drain-persist uses a thirty-second descendant under a five-second helper wall
bound. Its pass requires exactly ValueError('child wall bound'), positive last
drain accounting, completed=false, no completion marker, positive pre-kill
accounting, an attempted successful TerminateJobObject call, empty cleanup
errors and terminal zero accounting. An immediate-active exception, startup
refusal, unrelated CPU/memory error, missing accounting or clean completion
does not satisfy that oracle.

These observations reject the retained immediate-refusal implementation,
skipping the Job drain, accepting direct exit as complete, killing children on
the ordinary success path, and losing the persistent descendant's wall bound.
The unchanged original eleven retain their previous log, memory, nonzero,
timeout, nested-process, late-log-read and input-change/restored predicates.
The diff shows their fixture bodies and ordered oracle branches unchanged;
the wall-choice expression adds only drain-persist to the existing five-second
choice. Every new call retains ten CPU seconds, a 65536-byte log and 64 MiB
committed memory. The original complete-controller 120-second check remains.

The result appends each attempted case before evaluating its oracle. The new
artifact inventory retains startup/completion and partial pending markers even
after failure, preserves already recorded hashes, and excludes only the
terminal result from its own recursive digest. The later source, input and
artifact checks remain on the success path through result persistence.

## Scope of acceptance

The three appended controls specifically commission natural completion and
wall refusal after direct exit. They do not independently isolate every
possible post-exit CPU or memory boundary sequence, prove scheduler timing,
or identify the process that caused private-campaign-1's first refusal. The
same-clock CPU/memory checks are supported here by source review and the
existing distinct resource controls. Missed startup or overlap is a retained
control failure; no retries, widened caps or image-bar changes follow from
this source acceptance.

Proceeding means freezing the exact four source revisions, amendment, inputs
and fresh fourteen-case command before execution, then reading the actual full
result. It does not mean the controls passed, build3 exists, the ten private
grid outputs were produced, or either derivative TIFF was admitted.
