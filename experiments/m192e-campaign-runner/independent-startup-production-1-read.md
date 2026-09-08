# Independent read of startup production rehearsal 1

VERIFIED SAVED OUTCOME WITH THE LIMITS BELOW, 2026-09-08.
I independently read the actual release/command records, source bindings,
parent/worker/outer evidence, all three metadata populations and their six
checkpoint generations, and the completed independent audit. I did not
author the new startup-production subject or its saved checker. Inherited
durable components and their earlier commissions are reused; this report
does not newly commission them.

No subject/checker/control was re-executed. No RAW or TIFF payload was opened
by this read. I used bounded standard-library metadata reads and source/Git
byte comparisons; the already executed independent checker performed the
streamed TIFF verification.

## Outcome and exact authority

The completed independent audit is
rehearsal-startup-production-1-independent-audit/result.json,28672 bytes,
SHA25645907aa5bdb1269cc4d7061484cbd8d28cfc2fbda0e9a4c8f6592b64b3af972f.
Its raw rehearsal-startup-production-1-audit-stdout.bin is exactly identical,
including padding and final newline. Audit stderr is empty; exit.txt is
exactly 0 followed by LF. The actual audit outer is1995 bytes,
SHA25646f4668ef2dfaba5d39b92ad523b96b3cc98e79f38dfbdd668175c0d4b33e416,
exit0, whole wall2.25 s, stdout28672 bytes, stderr0.

Status is PASS_SAVED_STARTUP_PRODUCTION_OUTCOME_AUDIT, schema
m192e-saved-startup-production-audit-v1. Subject_complete,
worker_records_verified, worker_complete_verified, output_nonperturbation,
sampling_all_pass and integration_pass are true. Exceptions/unvisited are
empty. Independent_full_interval_histories and full_campaign_certificate
are explicitly false. The latter qualifications are load-bearing.

I compared the actual audit command byte-for-byte as parsed argv with
startup-production-audit-release-1.json and audit.command. It binds the
actual plan, root outer/raw streams/exit, exact current checker and actual
parent/worker hashes. The checker is68640 bytes,
SHA2561405b34ad056eea17459300640ed85357d857d440217e50ed988ca7ae575d0c3.

The plan is startup-production-preparation-1/plan.json,12473 bytes,
SHA25623c46b2f76a079352d685c21e90c251b19b50d2c09e9915748cc5eff5ff68811.
All39 current positive source bindings match their FileRefs. The six current
startup-production run/support/verify/launch/protocol/audit files equal their
Git blobs at source revision2c314d38f20b90d323034253989ec1b3e35946af.
The plan and startup-production-release-1.json equal the actual release
revisionc4f40cf6444e31a3739a95a7e1db19592ce7e98f. Release JSON is1769 bytes,
SHA256982795164a70a730987cd638fcecd195b27f72614026c95756df097064e6d230.
It permits exactly off/on/placebo, persistence on, N33/W8, with no retries.

The actual root subject outer is rehearsal-startup-production-1-outer.json,
738 bytes, SHA256e62f66dcee5726bbd458307d4bb10917c48265c45f50878f2a1820d98a5a89a3.
Its exact launcher command matches that release; exit0, whole wall
129.7190000000046 s, stdout296 bytes, stderr0. Raw stdout SHA is
d78f0ef855f2b8c26e135dd26431d8fe072c83bc486472df4d019eae7b7f2d23;
exit is2 bytes/SHA9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa.
The owned outer is rehearsal-startup-production-1-outer/outer.json,8192 bytes,
SHA2564d3748da77d17d613a7d01e19c6e6fcf9f807480bb7e0af841134dee5653e007.

Actual parent canonical is65536 bytes,
SHA256fd95f2290ae9094c2ecb66bcbb4eede2ea2afd2896eea8957ef03c306d14f7b0;
worker canonical is65536 bytes,
SHA256639d18ffe810519699b192830cbbc55ab25f6799cd38dcc8902d25c21d68d6f2.
Both are COMPLETE_REHEARSAL_EVIDENCE_ONLY, with matching retained first
positive and post-publication tail associations. The actual terminal exits
and final outer govern; an earlier positive alone did not supply admission.

## Sampling disposition versus retained history

All three unchanged source gates pass100 ms maximum and90% coverage.
The recorded maximum is also witnessed by a retained interval in each arm.
That does NOT establish an independent upper bound over the evicted history.

| Startup mode | Samples | Missed cadence slots | Reported coverage | Reported max ms | Full payloads in retained union | Interval witnesses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| off | 3938 | 85 | 0.978871488938603 | 59.4427 | 1138 | 1139 |
| on | 3935 | 95 | 0.9764267990074442 | 54.3478 | 1135 | 1136 |
| placebo | 3961 | 104 | 0.9744157441574416 | 58.9619 | 1161 | 1162 |

I re-grouped actual checkpoint/final rows by poll with full overlap equality,
then examined contiguous retained ranges instead of filling missing IDs.
Every full-payload union begins at poll2800 and ends at the arm's final poll.
Thus2800 full process-observation payloads are absent in each arm. A separate
copy of poll0's start/observed scalars restores one interval witness, not its
full payload. Polls1..2799 still lack interval rows. Coverage here is the
recorded sample/(sample+missed) cadence ratio, not the fraction of full
process-observation payloads retained.

The checker correctly does not join poll0 to poll2800 as one interval, nor
claim an exact full maximum or coverage reconstructed from all starts.
Complete interval history and complete full-payload history are false for
every arm. Independent retained-gap lower bounds equal59.4427/54.3478/58.9619
ms, while complete maximum upper bounds and exact full maxima remain null.
A larger evicted gap could escape reconstruction; the original streaming
aggregate is the evidence for its reported absence. I found no retained
failure contradicting that aggregate.

Final closure is separately bounded by the retained final-memory event and
monitor end. Off lower/upper0.0397/0.2178 ms contains reported0.0424;
on0.0368/0.2222 contains0.0398; placebo0.5648/0.7504 contains0.5676.
These bounds do not synthesize an exact close timestamp from the reported
duration. This different choice is more informative than just repeating the
producer's maximum formula.

Final dropped observations are2938/2935/2961; dropped events are
16384/16369/16505. Incidents and telemetry drops are zero. Every arm actually
made39 checkpoints; retained sequence37 and38 is an adjacent two-generation
chain, with canonical payload hashes and same overlapping rows. Recovery
selects38 but remains RECOVERABLE_INCOMPLETE, may_resume=false,
may_certify=false. Two intact latest checkpoints cannot recreate old evictions.

## Startup attribution and observer nonperturbation

Each actual invocation is the fixed33-frame bee-1-cpl input, eight workers,
held binary and sidecar, unchanged sampler on and persistence on.
Only startup observation changes off/on/placebo. On/placebo record the same
actual argv, suspended flag4, actual PID/creation identity, successful
create/assign/resume outcomes and eight disjoint startup brackets. Off has no
extra bracket/PID/AST rows. The original monitor clock remains unchanged;
there is no injected production delay or moved denominator.

Partition the initial interval using actual timestamps:

| Mode | Startup call wall ms | Uncovered before first query ms | First query duration ms | Whole initial interval ms |
| --- | ---: | ---: | ---: | ---: |
| off | 0 (unobserved calls) | 3.6946 | 5.6765 | 9.3711 |
| on | 5.7118 | 0.1076 | 16.4133 | 22.2327 |
| placebo | 3.9540 | 0.0534 | 5.9418 | 9.9492 |

The on Popen bracket is5.1016 ms; placebo3.4187 ms. All recorded startup
thread-CPU deltas are0 at the sampled clock resolution. Zero sampled CPU is
not evidence that a call did no work or that all its wall was waiting.

These runs did not reproduce the earlier111.9996 ms uninstrumented startup
boundary. They cannot assign its cause or partition that historical event.
Call wall includes waiting. The first query follows resume; suspended process
creation can already expose memory. There is no native product code-entry
timestamp. Fixed ordering also cannot estimate observer overhead or speedup.

The independently executed checker streamed all three restricted RGB16 TIFFs:
each197798956 bytes, shape4688x7032x3,196 strips, whole SHA256
3309e33318c701fb75c55507bfb49ad279d8950492b592ec247dbe2d1193ac9e and pixel SHA256
6efc261e892dcdb5d492ad3fd79bdc7e5a208d93d0227a41b258fb3b900f9b89.
All match the held baseline and one another. This read checked those exact
audit/record associations and current file extents, without duplicating the
TIFF payload hashes. The claim is byte nonperturbation, not image quality.
The saved checker also independently rehashed exactly seven old outputs.
RAW preservation is the producer's equal before/after payload-hash witness
plus the checker's current33-file metadata inspection, not independent RAW
payload rereading or a full-corpus preservation statement.

## Current controls and terminal accounting

Current composition evidence changes precisely pre-install Trace identity,
pre-install telemetry identity and persistence on->off. The checker applies
its own predicates to those actual metadata values. Current startup faults
change exactly invocation path, PID, phase-list length, original start or
first-observation poll. I compared those five changed records to actual on
and found only the named field/list-length differences; original/restored
whole hashes match. Wrong Job total, negative user CPU and boolean active
count also reject in the independent checker. These are metadata predicate
commissions, not additional product observations. Eight storage and six
invocation controls remain explicit prior reuse, not new executions.

Terminal child.json is131072 bytes,
SHA256537e47b696e9aee1892fad7e24cc824d6a2569127d6984307fbda7c227926c7e.
The owned parent's same-handle creation identity is preserved through final
GetProcessTimes. Its terminal CPU is6.40625 s. Add terminal worker Job
569.40625 s once: combined575.8125 s,24.1875 s below600. The outer containing
Job independently cross-bounds the same575.8125 s; it is not another addend.
Both Job user/kernel/total/active fields are typed nonnegative integers,
total equals user+kernel and terminal active count is0.

The three product Jobs186.203125/185.484375/185.6875 CPU seconds are already
inside the worker Job. Adding them again would double-count. No elapsed wall
was converted to CPU. Committed worker peak Job memory3917631488 bytes and
peak process3071963136 bytes are distinct from RSS and below8 GiB.
Owned parent wall129.56199999999808 s fits240; whole root launcher
129.7190000000046 s fits its255 s external envelope. There were no terminal
cleanup errors or termination interventions.

Wrapper CPU0.734375 s is a sample plus reserved0.25, not complete wrapper CPU.
Its wall sample129.67199999999866 plus0.5 covers actual129.7190000000046.
Audit CPU2.21875 and own wall2.2030000000013388 are likewise samples;
actual outer2.25 <= own wall+0.5, within30CPU/60wall reservations.
The completed SUBJECT CPU domain is measured; wrapper/audit samples must not
be relabelled complete whole-process totals.

The saved physical inventory is60 files/630602104 bytes under the declared
1 GiB subject families. This read did not recensus all payload bytes or claim
cumulative write traffic from retained extents.

No discrepancy was found in the bounded composition's actual associations,
nonperturbation and source-defined sampling disposition. The qualified
integration pass supports this fixed three-call rehearsal. It does not
certify every unretained interval independently, full133 execution, timing
causality, image quality, scaling or SOTA.

