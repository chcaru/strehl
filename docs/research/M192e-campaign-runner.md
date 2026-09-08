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
