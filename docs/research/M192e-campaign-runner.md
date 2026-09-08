# M192e — durable systems rehearsal and startup sampling failure

**MEASURED and independently VERIFIED, 2026-09-08:** the new durable runner
completed its fixed three native N33/worker8 invocations with identical whole
TIFF bytes, recoverable checkpoints and complete terminal subject CPU accounting.
**Integration remains failed:** persistence-off's initial observation interval
was 117.8844 ms against the unchanged 100 ms maximum. On and placebo passed the
sampling checks. This result does not certify the full 133-call campaign or
identify the historical timing transition.

The next systems experiment is a five-private-child startup attribution probe.
It retains the old clock and acceptance rules and adds measured startup phases.
No product rerun, full campaign, checkpoint optimization or relaxed bar follows
from this rehearsal.

## Frozen experiment and actual commands

The [preregistration](../../experiments/m192e-campaign-runner/preregistration.md)
and source package were frozen at
`04a353e4d77e46b8e9cf9c2111fd8e111efe6707`; the prepared release is
`ae31343c0aa9a574e7f53b9893e1c71fc2325b56`. The retained non-raster evidence is
archived at `d273ba8437174bb13a6cb86211a7a9105bf1b9b3`. The three large TIFFs
remain at their recorded local paths. Existing M192/M192d artifacts were preserved.

Preparation bound the existing executable, alignment sidecar, 33 input identities,
source closure and seven earlier outputs before any new product invocation.
It did not decode RAWs or TIFFs. The source fixes authenticate the same JSON
bytes that are consumed, bind the complete invocation/environment, retain
bounded checkpoints and refusals, and link final publication to actual process
exit and terminal accounting. See the
[independent source review](../../experiments/m192e-campaign-runner/independent-terminal-source-review.md).

Executed once each, from the repository root, using Python 3.12.10:

```powershell
$python = 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe'
$plan = 'experiments/m192e-campaign-runner/preparation-1/plan.json'
$planSha = '9A8BFCEF7DA8F6BBF1927ADCB99039CD1D679DA851DEB99367C9A1D836A40D73'
& $python -B experiments/m192e-campaign-runner/launch.py --plan $plan --plan-sha256 $planSha
& $python -B experiments/m192e-campaign-runner/verify.py --plan $plan --plan-sha256 $planSha --outer experiments/m192e-campaign-runner/rehearsal-1-outer/outer.json --outer-sha256 58F2505E97F5F2FFB2A2203BD5194F06E993955E25B560E012176B3AFE34D3F5
```

These commands use repository-relative spellings for readability; the actual
absolute argv arrays, exit codes and whole invocation walls are retained in
[launch receipt](../../experiments/m192e-campaign-runner/rehearsal-1-launch-outer.json)
and [verification receipt](../../experiments/m192e-campaign-runner/rehearsal-1-verification-outer.json).
Both exited zero. Whole launch wall was 103.890 seconds; outer verification wall
was 1.640 seconds. A zero verifier exit here authenticates a complete result,
including its explicit failed integration disposition.

The fixed order was off, on, placebo. Each rendered the first 33 sorted RAWs
from `D:\personal\macro\bee-1-cpl`, worker8, Pyramid gate2, Catmull-Rom,
Scale coverage, linear sRGB and full-resolution demosaic, using the pinned
existing native executable and sidecar. The persistence mode controls storage;
the underlying phase observer was enabled in all three calls. No compilation,
new alignment solve, quality comparison or independent timing sweep was run.

## Observed sampling and output results

The unchanged rule includes monitor-start to first observation and final
closure. It requires maximum interval <=100 ms and scheduled coverage >=0.90.
Coverage is samples/(samples + missed scheduled intervals), not a continuously
observed fraction of time. High coverage can coexist with a disqualifying gap.

| Persistence | Samples / missed | Coverage | Maximum interval ms | Completed checkpoints | Sampling |
|---|---:|---:|---:|---:|---|
| off | 3159 / 14 | 0.9955877718 | 117.8844 | 0 | FAIL |
| on | 3161 / 59 | 0.9816770186 | 54.4005 | 31 | PASS |
| placebo | 3156 / 64 | 0.9801242236 | 50.1861 | 31 | PASS |

All three TIFFs are 197,798,956 bytes and have complete-file SHA256
`3309e33318c701fb75c55507bfb49ad279d8950492b592ec247dbe2d1193ac9e`.
An independent reader streamed and hashed each entire file. The authored
verification additionally reports canonical pixel SHA256
`6efc261e892dcdb5d492ad3fd79bdc7e5a208d93d0227a41b258fb3b900f9b89`;
the independent reviewer did not repeat that decode. Whole-file equality alone
establishes byte nonperturbation for this configuration, including placebo.
A changed byte would reject it; equality is not an image-quality criterion.

The seven earlier output identities and before/after input manifests remained
unchanged. On and placebo actually exercised checkpoint writes. Their two
surviving generations have sequences 29/30 and a verified previous-file hash
link. Controlled partial writes, overflow and coherently resealed identity/chain
faults reject and restore as specified. These are exercised storage controls,
not an actual crash or power-loss trial. Every recovery receipt remains
`RECOVERABLE_INCOMPLETE`, with resume and certification forbidden. Evicted
observation/event histories are explicit; the snapshots do not recover a whole
long-run trace.

## What the failed interval locates

The independent review re-chose the observation population by merging final
traces, both surviving checkpoint generations and incident evidence by timestamp
and poll identity. It checked overlapping records for conflict and reproduced
all three maximum intervals. This verifies retained boundaries; it cannot
recreate evicted full histories or turn recorded aggregate counts into continuous
observations.

The off interval runs from QPC 33814477751300 to 33814595635700 ns. Its first
timed phase starts at 33814589750900: **111.9996 ms precedes the first measured
phase**, with 5.8848 ms from that point to the first observation. The union of
measured phases covers only 5.8397 ms within the full interval, including a
5.7187 ms process-table query. The two latter quantities have different
boundaries and are not interchangeable.

The frozen start precedes system counters, memory status, Job creation, log
opening, suspended process creation, assignment and resume. No separate retained
startup brackets distinguish those operations. This locates missing attribution,
not a measured operating-system cause. A suspended process may already hold
memory; its pre-resume interval cannot be silently removed. No production checkpoint write occurred in that failing invocation.

The on/placebo maxima follow their every-hundredth-observation checkpoint
callback. Existing timestamps locate source-compatible untimed work there but
do not separate serialization, hashing, writes, fsync, readback or descheduling.
A single fixed-order run cannot rank mode costs or show that observation improves
cadence. The [saved diagnosis](../../experiments/m192e-campaign-runner/sampling-diagnosis-1.md)
retains the detailed boundaries and selected-tail limitations.

## Complete accounting and independent disposition

Same-parent-handle terminal process counters give 5.40625 CPU seconds. The
worker's terminal Job counters, including descendants, give 425.984375 seconds.
Their sum is **431.390625 seconds**, below the 600-second subject limit. The
enclosing Job independently records the same sum and is not added a second
time. All terminal Jobs are inactive, exit is natural zero and pipe draining is
complete. Whole-parent wall is 103.75 seconds against 240 seconds. The launcher
has a separate sampled CPU reading plus its reserved publication tail; this
report does not claim measured complete launcher CPU.

The independently inventoried subject and outer files total 633,172,322 bytes,
below the 1 GiB retained-storage limit. That limit is separate from RAM; the
observed child committed-memory peak is 3,916,533,760 bytes against its 8 GiB Job
limit. These are scope-limited recorded quantities, not admission of the older
N299 memory or scaling bars. Wrong-total, negative and boolean Job counter
controls reject, with the original witness restored.

The [terminal verification](../../experiments/m192e-campaign-runner/rehearsal-1-verification.json)
(3,086 bytes, SHA256
`a0f4f50e8f2b2c96778966b0714fbe3b6b84b94ace30c11084ba4ea7a784ee10`)
reports `PASS_BOUND_TERMINAL_REHEARSAL_ONLY`, complete subject accounting and
output nonperturbation, while `integration_pass`, `sampling_all_pass` and
`full_campaign_certificate` are all false. The separate
[independent actual-outcome review](../../experiments/m192e-campaign-runner/independent-rehearsal-1-read.md)
(9,509 bytes, SHA256
`4d19117d757fd6e814aeba1cbb747f3e53f9b376c2b4d540d6662809b4387ff8`)
confirms those limits from saved artifacts rather than rerunning the author.

## Next bounded action

SOURCE ONLY at this report's publication: instrument startup call boundaries in
a separate five-private-null-child version, retaining the original start,
missed-interval arithmetic, 100 ms maximum and final closure. Fix off/on/placebo,
a 150 ms pre-creation delay and a 150 ms post-resume delay before execution.
Require the two planted gaps to fail the old bar and appear in their correct
new brackets; preserve any untreated host-induced failure. Require identical
child output across every arm. Review exact sources and the finite release
before running. This adds attribution and does not repair or reinterpret the
completed failed rehearsal. The unresolved full-campaign timing transition
remains a separate question.
## Executed AGENTS rule checklist

This is the checklist for the completed three-run rehearsal and its report,
not a claim that the prospective startup probe has run. Paths below are under
experiments/m192e-campaign-runner unless named otherwise. Function names and
actual artifact contents identify the checked code paths; source/release/archive
SHAs and commands are recorded above. No SYNTHESIS facts were folded.

| Rule | Discharge or inapplicability for this result |
|---|---|
|1|No product arithmetic/storage change; pinned pre-existing native binary and complete TIFF identities are bound by preparation-1/plan.json. |
|2|No new aligned-frame materialization; actual argv uses the unchanged native pipeline. |
|3|No noise-model implementation or estimate is added. |
|4|No merge-reference election or best-frame statistic is introduced. |
|5|No profile, geometry fit or camera constant is changed. |
|6|No alignment chain/solve is run; bound prerecorded sidecar and identical fixed configuration. No placement number is claimed. |
|7|No decoded-buffer statistic is reported; independent outcome read streams whole-file bytes only. |
|8|The exact actual launch and verification arrays, exits and walls are in the two linked outer receipts; measured and derived claims are distinguished. |
|9|No sharpness/detail/quality metric is used; byte identity is scoped to nonperturbation. |
|10|No spatial/temporal noise comparison is made. |
|11|Actual off/on/placebo outputs agree; storage controls and Job-counter corruptions reject/restore. The headline gap is independently reconstructed on the actual retained timestamp path. No individual startup cause is claimed. |
|12|factor_eight_implementation authored the runner; factor_eight_review independently read actual files/timestamps/Jobs and whole TIFF hashes. |
|13|No parameter sweep or optimum is reported. |
|14|Independent output inventory used Get-ChildItem -Recurse -Force -File. Input manifests preserve the named33-file population; no whole-corpus total or mirrored-stack replication claim. |
|15|No unqualified artifact/filter expansion terminology is used. |
|16|The once-only fixed-order rehearsal is explicitly not a timing benchmark or mode-cost ranking. |
|17|Independent review groups by timestamp/poll identity across final/checkpoint/incident evidence; no response-derived bins or scene-quality correlation is used. |
|18|The report states that high scheduled coverage can hide a failed maximum gap, byte identity cannot score quality, and snapshots cannot recover evicted history. |
|19|New experiment directory and helper files use kebab-case; retained historical milestone/report naming is preserved. |
|20|Wrong-total/negative/bool counters and storage faults provide rejecting inputs. Untreated actual off fails100ms despite high coverage; no gate is redefined to make it pass. |
|21|No fitted constant gates its generating model. |
|22|This explicit per-rule checklist names the actual evidence; prospective startup controls remain unexecuted. |
|23|No multidimensional image filter or non-spatial-axis operation is added. |
|24|The independent reviewer re-chose the observation union, whole-file hashing and terminal CPU summation instead of rerunning the author's verifier. |
|25|No facts/disciplines/questions number block or SYNTHESIS edit. |
|26|All three actual complete TIFF files are independently hash-identical, including the persistence placebo. |
|27|All subject runs ended naturally; there was no inference of a dead process from silence or deletion of an active process. |
|28|No report fold or duplicate numerical fact insertion. |
|29|Research report is a fresh file; program update preserved every heading and the user-owned H1, and the entire program file was excluded from commits. |
|30|The known117.8844ms disagreement remains an asserted failed integration, not an excluded interval. |
|31|No fold. Sources were committed before release and outcomes cite exact revisions. |
|31b|No fold script or SYNTHESIS publication; fold_check is inapplicable. |
|32|No new rawpy loader or borrowed decode buffer. Independent read did not decode RAWs or TIFF pixels. |
|33|No Rust compilation/test result claimed; existing executable identity was authenticated and executed. |
|34|No synthetic calibration claim or supplied noise constant. |
|35|Nonempty whole TIFFs, actual timestamps and raw terminal Job counters are independent operands; wrong counter variants reject. |
|36|On/placebo actually wrote31 checkpoints each; storage faults/recovery and the off rejecting interval occurred in retained records. |
|37|No SYNTHESIS insertion, numbered namespace or structural table fold. |
|38|The terminal JSON flags and full independent read were read in context; PASS_BOUND_TERMINAL_REHEARSAL_ONLY is not paraphrased as integration PASS. |
|39|No statistical separation, mode-cost ratio or precision confirmation is claimed. Exact byte identity and deterministic counter arithmetic are identified as such. |
|40|The M192e preregistration/dispatch retained the mechanical prior-art search and M192/M192b/c/d lineage; completed questions were not recommissioned. |
|41|The M192e allocation is in AGENTS.md before this continuation; the startup work is a genuine continuation, not a reused milestone identity. |
|42|Exact NUL path manifests and git commit --only --pathspec-from-file restricted each source/release/evidence/report commit; committed paths were checked with diff-tree. |
|43|The report bounds its absence claims to actual saved traces and source call sites; it does not assert that no prior calibration or method exists. |
|44|No corpus fold, duplicate corroboration or exclusion from a duplicate checker. |
|45|The actual plan/invocation binds the isolated saved sidecar; gathering kernel is fixed, not a swept independent variable. |
|46|Actual execution outputs and exit codes were captured without truncating process pipelines. Display-only reads do not determine a gate exit. |
|47|Plan and invocation receipts bind absolute input/frame range, executable/sidecar/source, environment and actual CLI; independent read checked these associations. |
|48|No visual defect verdict or resized-viewer quality judgment is used. |
|49|Root coordinated execution; only owned Job trees were available to cleanup, none required termination, and no peer hold or process kill was used. |


## Private startup attribution: completed follow-through

**VERIFIED, private diagnostic scope only (2026-09-08).** The second fixed
five-null-child probe and its frozen independent saved checker completed once.
The independent raw-record re-choice is
[the startup2 actual read](../../experiments/m192e-campaign-runner/independent-startup-attribution-2-read.md),
11728 bytes, SHA25643f05f12bffb454ab202285defae154620446c0699397a2d93ccacbaa1f16cdf.
Exact actual argv, exit, whole wall and source/result pins are retained in
startup-attribution-2-launch-outer.json and startup-attribution-2-audit-outer.json.

| Arm | Complete maximum gap, ms | Coverage | Original gate | Control disposition |
|---|---:|---:|---|---|
| off |10.4956|1.0|PASS|PASS|
| on |10.4914|1.0|PASS|PASS|
| placebo |10.6485|1.0|PASS|PASS|
| before-Popen delay |161.3971|0.8125|FAIL|Expected rejection|
| after-resume delay |160.1858|0.7692307692|FAIL|Expected rejection|

The injected phases measure150.1857/150.3644ms. Independent child timestamps
place the first entirely before child entry and the second across actual child
execution. The latter first interval partitions into63.8704ms before child-code
entry and96.3154ms during it. These are actual null-process events, not invented
production timestamps. Final-closure uncertainty stays below the observed
maxima, so the original100ms/90% gate is independently determined.

All five4138-byte nonempty outputs match the literal oracle and each other.
The independent reader checked all49 files/873687 bytes and actual native
return/PID associations. Whole subject wall4.422s; complete owned Job CPU1.1875s
plus sampled parent0.578125s plus0.25s publication reserve is2.015625s. The
reserve is bookkeeping, not measured terminal parent CPU. Peak committed Job
memory821858304 bytes fits1GiB. Saved audit exit0/whole0.203s fits its0.156s
sample plus0.5s tail. These are bounded-run observations, not comparative timings.

Attempt1 remains failed: containing Job peak561917952 bytes exceeded512MiB committed
memory, cleanup completed and all arms remained unvisited. Its one-byte log
does not identify a library cause. Full20CPU/30wall/4MiB subject and10CPU/20wall/
1MiB audit reservations remain charged separately. The source-reviewed second
attempt changed only the worker memory ceiling and bindings. Source/failure
freeze7dce975c and release d4a6ef57 preserve that sequence.

This commissions private startup attribution, not production memory/sampling,
the historical111.9996ms cause, or the133-case scorecard. The next prospective
integration holds persistence ON across one fixed N33/W8 startup-observer
off/on/placebo triplet. Root chooses this over the independent reader's proposed
persistence-OFF branch to exercise durable-trace composition while varying one
instrumentation factor. No new product call is released by this report.

The preceding per-rule checklist remains the inherited rehearsal checklist.
Here, rules8/11/20/24 are discharged by actual outer commands, independently
positioned rejecting delays and literal-output/byte-fault checks;26 by five
unchanged intrinsic hashes;27/49 by retained owned cleanup on attempt1 and
natural completion on attempt2;29 by append-only editing and preserved existing
headings;31/31b/37 by no SYNTHESIS fold;42 by exact source/release/evidence path
manifests. Other architecture/RAW/noise/geometry/quality rules are unchanged or
outside this null-only scope.


## Production startup with persistence on: completed integration

**MEASURED and independently VERIFIED, 2026-09-08, within the bounded
rehearsal contract.** One fixed N33/W8 triplet completed with startup observation
off/on/placebo and persistence ON in all three arms. Its output identity,
terminal accounting and original source sampling gates pass. This is the
completed integration proposed above. It preserves the earlier failed
rehearsal and does not certify a complete retained sampling history.

The held source revision is
2c314d38f20b90d323034253989ec1b3e35946af; the actual triplet plan/release revision is
dc4c5bcaf5b0bb8a9ee2bcf23f2d88e786d237bf. The saved-audit release revision is
c4f40cf6444e31a3739a95a7e1db19592ce7e98f. The plan is 12,473 bytes,
SHA256 23c46b2f76a079352d685c21e90c251b19b50d2c09e9915748cc5eff5ff68811.
Exact absolute invocation arrays, release identities and observed exits are
retained in the [subject release](../../experiments/m192e-campaign-runner/startup-production-release-1.json)
and [actual subject outer receipt](../../experiments/m192e-campaign-runner/rehearsal-startup-production-1-outer.json),
and in the [audit release](../../experiments/m192e-campaign-runner/startup-production-audit-release-1.json)
and [actual audit outer receipt](../../experiments/m192e-campaign-runner/rehearsal-startup-production-1-audit-outer.json).
These are commands that ran once, not authorization to repeat them.

The [saved independent audit](../../experiments/m192e-campaign-runner/rehearsal-startup-production-1-independent-audit/result.json)
is 28,672 bytes, SHA256
45907aa5bdb1269cc4d7061484cbd8d28cfc2fbda0e9a4c8f6592b64b3af972f.
Its raw audit stdout is byte-identical, including the terminal newline.
The actual audit outer is 1,995 bytes, SHA256
46f4668ef2dfaba5d39b92ad523b96b3cc98e79f38dfbdd668175c0d4b33e416.
Its status is PASS_SAVED_STARTUP_PRODUCTION_OUTCOME_AUDIT:
subject_complete, worker_complete_verified, output_nonperturbation,
sampling_all_pass and integration_pass are true; exceptions and unvisited
populations are empty. independent_full_interval_histories and
full_campaign_certificate remain false. Parent and worker retain
COMPLETE_REHEARSAL_EVIDENCE_ONLY, natural exit zero, terminal tails and the
associated first-positive publication evidence. A canonical positive alone
was not the admission test.

The [independent actual outcome read](../../experiments/m192e-campaign-runner/independent-startup-production-1-read.md)
is 11,465 bytes, SHA256
8a08ac66f77d797dfc18de95b38e30252a66e58722f5cb27d2c75fc81d79a08b.
It checked the 39 held source bindings, six relevant committed source blobs,
actual commands and saved identity, checkpoint, timing and accounting choices.
It did not rerun the subject/checker or read TIFF/RAW payloads.

### Sampling passes with an explicitly incomplete retained history

The unchanged gate includes initial, inter-poll and final intervals, with a
100 ms maximum and at least 90% cadence coverage. The source reports:

| Startup observer | Samples | Missed cadence slots | Source cadence coverage | Source maximum gap, ms | Initial interval, ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| off | 3,938 | 85 | 0.978871488938603 | 59.4427 | 9.3711 |
| on | 3,935 | 95 | 0.9764267990074442 | 54.3478 | 22.2327 |
| placebo | 3,961 | 104 | 0.9744157441574416 | 58.9619 | 9.9492 |

These are qualified source-aggregate results. Each reported maximum has a
matching retained interval, but the reader cannot independently exclude a
larger interval from the evicted population. Cadence coverage is the source
sampling ratio; it is not the fraction of full observation payloads retained.
The reader therefore reports passing bound source aggregates while explicitly
refusing a full independent interval-history claim.

Each arm made 39 checkpoint publications; the retained adjacent generations
are 37 and 38. Their sealed overlap and payload identities check. The union of
retained full observations covers poll 2800 through the final poll: 1,138,
1,135 and 1,161 observations respectively. Poll zero has a separate first-poll
scalar witness, not a retained full observation. Intervals for polls 1 through
2799 are missing, and full payloads for polls 0 through 2799 are missing.
The final tails each contain 1,000 observations. Source observation drop counts
are 2,938/2,935/2,961; event drop counts are 16,384/16,369/16,505. Incident and
telemetry drop counts are zero.

Checkpoint recovery remains RECOVERABLE_INCOMPLETE, with resume and
certification false. It preserves recoverable evidence rather than rebuilding
discarded history. The independent final-closure bounds contain the reported
final intervals; they do not fabricate exact missing timestamps or make the
retained histories complete.

### Startup attribution and unchanged outputs

The on/placebo arms retain all eight prescribed native startup brackets,
including suspended creation, assignment and successful resume, associated
with the actual child identity and invocation. Their summed bracket wall
intervals are 5.7118/3.954 ms. Remaining uncovered pre-query time is
0.1076/0.0534 ms; first memory-query time is 16.4133/5.9418 ms.
Together these partition the original 22.2327/9.9492 ms initial intervals
without shifting the sampler origin. The off arm has no added brackets:
its 9.3711 ms initial interval contains 3.6946 ms unpartitioned before the
first query and 5.6765 ms in that query.

The historical 111.9996 ms startup interval did not recur in this triplet.
That observation does not identify its cause. These fixed-order arms do not
measure observer overhead, and their timing differences are not a performance
ranking. Zero bracket CPU at the retained clock resolution does not establish
zero work. No actual production child-code entry timestamp was added; the
suspended process can already consume memory before resume. Startup attribution
and the original sampling exposure remain distinct.

All three TIFFs are byte-identical: 197,798,956 bytes each, shape
4688 x 7032 x 3. Whole-file SHA256 is
3309e33318c701fb75c55507bfb49ad279d8950492b592ec247dbe2d1193ac9e;
pixel-data SHA256 is
6efc261e892dcdb5d492ad3fd79bdc7e5a208d93d0227a41b258fb3b900f9b89.
Their held local extent is 593,396,868 bytes. The independent checker streamed
the TIFF and pixel identities; the later human-facing read checked those
bindings and extents without another TIFF payload pass. The seven historical
output identities were also independently checked. The 33 RAW inputs retain
producer before/after hash witnesses and independent metadata checks, not an
independent full-corpus RAW rehash. Identical outputs establish nonperturbation
in this triplet, not image quality.

### Complete subject accounting and the next consumer

Actual terminal parent CPU is 6.40625 s; terminal worker Job CPU is
569.40625 s. Their sum is 575.8125 s, counted once, leaving 24.1875 s below
the fixed 600 s subject ceiling. The outer containing Job agrees with this
sum and is a cross-check, not another quantity to add. Product CPU is already
inside the worker Job. Typed nonnegative user/kernel/total counters agree,
and terminal active-process counts are zero. Peak committed Job memory stays
within the 8 GiB ceiling; it is not an RSS measurement.

The owned parent's wall interval is 129.56199999999808 s; the actual external
wrapper receipt records 129.7190000000046 s whole wall and exit zero. Across
the paired subject roots, the actual physical census is 60 files /
630,602,104 bytes, below 1 GiB. This is retained extent, not cumulative I/O.
The wrapper's own CPU sample is 0.734375 s plus its separately charged 0.25 s
publication allowance; its 129.67199999999866 s wall sample plus 0.5 s covers
the actual outer interval. Those wrapper samples do not replace measured
terminal subject CPU.

The saved audit ran once with exit zero and 2.25 s whole outer wall. Its own
sample is 2.21875 s CPU / 2.2030000000013388 s wall, plus the declared
0.25 s CPU / 0.5 s publication allowance, within its 30 CPU / 60 wall
reservation. The audit's own final CPU remains sampled plus allowance.
These systems reservations are separate from the geometry campaign; unused
work does not refund or authorize another geometry attempt.

The current composition checks reject trace/telemetry construction before
durable installation and persistence OFF. Current startup metadata faults
alter invocation, child identity, required phase, clock origin and first-poll
identity; their restored originals agree. Independent Job faults reject
wrong component sums, negative values and booleans. These powered metadata
checks accompany the actual off/on/placebo output hashes. The eight earlier
storage controls and six invocation controls are inherited evidence, not
newly commissioned production runs.

Startup instrumentation with durable persistence is now commissioned for
future bounded runs under this qualified sampling contract. The immediate
priority returns to independently checking the already saved geometry data.
This result authorizes neither the full 133-case campaign nor an invented
performance experiment, a changed timing-state policy, or relaxation of the
100 ms/90% sampling and existing 2% timing bars.

For this append, rules 8/12/24 are discharged by actual command receipts and
the independent choices documented above; 11/20/26 by rejecting metadata
faults, restoration and actual output identity; 18/30 by the explicit eviction
limit and preserved historical negative. Rule 29 is discharged by exact
append-only prefix preservation and structural counts. Rules 31/31b/37 need
no fold because SYNTHESIS is unchanged; the exact source/release/evidence
bindings provide the scoped rule 42 record. This append changes no
architecture, RAW implementation, estimator, image-quality/noise claim or
scientific acceptance threshold.
