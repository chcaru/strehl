# M193c private campaign 1: independent refusal read

**VERIFIED by readback: incomplete, not admitted.** The first plan test returned
zero and saved a plan, but its process helper refused the immediate post-exit
Job observation. The refusal propagated through producer, worker and owner.
There are no product TIFFs, precision results, independent reader runs, native
RAW reads, or derivative admission gate from this attempt. A passing Rust test
line is not a passing bounded process or private campaign.

This reviewer read actual retained JSON/logs, compared commands and intervals,
rehash-checked sources/inputs/artifacts and inspected the frozen helper source.
No subject module was imported, no experimental process or numerical helper was
run, and no image was rerendered. The prospective audit checklist remains
`independent-private-campaign-result-audit-plan.md`; its twelve-image pixel read
does not apply to a population of zero images.

## Release and original terminal observation

Root froze revision `f9ee06a40c2dbcc2b6404bd96b9a9383bcefc409` before launch.
`private-campaign-release-1.json` is 31,180 bytes, SHA256
`ab81a017f159e411e0fdcea1f65c248ff575cc23f7aa16b42b6a112df35923a0`.
The grid-specific release remains SHA256
`e690478aab676eb1d7b4d5f508665c3bbd796c48683314ee9cf888b42f2cf8fc`.

Root's original PowerShell invocation record is
`work/private-campaign-1-outer.json`, 1,039 bytes, SHA256
`eff50d3570c79f04683e48506b281372fc164a7d31467878f4e1a50a17198ef2`.
It records **OS exit 1 and 4.9988203 seconds** of direct invocation wall time.
Root separately reported approximately 5.09 seconds for the enclosing tool
call. The former is the stored launch observation; the latter includes tool
scope. This reviewer inspected those retained observations and did not perform
the original OS wait.

The actual command is recorded in full in that outer JSON. Readback verified
exact equality with the root release's owner argv after its single actual
release-SHA substitution: the pinned Python312 interpreter, `-B`, faulthandler,
owned cache prefix, `private-campaign.py`, absolute release path/external SHA,
and fresh `private-campaign-1` output. The owner result command equals that
original invocation. The recorded worker command matches its separately
released `--worker` argv. The actual grid-producer command matches both the
campaign release and its own separate release after the permitted substitution.

## Actual refusal chain

| Boundary | Actual outcome |
| --- | --- |
| `00-plan` Rust test | One exact named test passed; exit 0; 9,824-byte plan saved. |
| `00-plan` helper | Refused with `ValueError('child left an active descendant')`; final terminal accounting true, active 0, cleanup errors empty. |
| Grid producer | Exit 1; `UNCOMMISSIONED_PRIVATE_OUTPUTS`; first plan launch recorded as failed; no committed entry or precision result. |
| Worker | Exit 1; `REFUSED_PRIVATE_WORKER`; only `grid_producer` attempted; `grid_reader`, `derivative_producer`, `derivative_reader` unvisited. |
| Owner | Exit 1; `REFUSED_PRIVATE_CAMPAIGN`; no products or independent reads admitted, no derivative gate. |

The exact Rust log has a single named
`merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case`
success and a summary of one passed, zero failed/ignored/measured, 161 filtered,
finished in 0.34 seconds. The plan is `PLAN_ONLY`, case `identity-nine`, ordinal
0. It is retained evidence of the test body, not an admitted plan launch.

The first test's actual argv equals the launch argv and names the copied build2
test executable. Its monotonic interval is
`[794934062000000,794934421000000]` ns, contained within the observed grid-producer
interval `[794932656000000,794935453000000]` ns. There is no later successful
stage to pool with this failure. All three actual log files were read and their
hashes/extents matched the referenced observations.

Key retained records:

| Record | Bytes | SHA256 |
| --- | ---: | --- |
| `private-campaign-1/result.json` | 30,532 | `415b2b6032bd59bf81b7e2e499e430ddbabc7d8395f1aaa1858af05b9eee15d4` |
| `private-campaign-1/artifact-index.json` | 2,088 | `54b0dd15c32756d0d5e1d75264297575ea6f14687addb0a550ca6602665d869a` |
| `worker/result.json` | 3,151 | `1d216511cc4f55da6d8a2cb26624fc96c8dbbfc6bae222220ba6f784696d2140` |
| `worker/grid_producer-launch.json` | 4,928 | `644d46a122f6afc29d764c1fcec9ffdb7add5c3f02fc95af4162994d0c4fa7ea` |
| `worker/grid/run-index.json` | 116,697 | `c3285bcbf9c427b4e7de6eb6809897b65f854d1dd21fec7a27e4f3c2278bcad4` |
| `worker/grid/00-plan-launch.json` | 3,506 | `65967fd8f44fac4afbf428d68fe0c5ed0d7711da74df2722874a27139010287d` |
| `worker/grid/00-plan.json` | 9,824 | `e26d8a6f57a1f22b69dc8112e75c126283bc52938b7b5462f1810bd81c094371` |
| `worker/grid/00-plan.log` | 200 | `f9fe8648b414f63050f7613c9b36af551efeb6fc7a3be5733914a0ad95f9ad0d` |

Worker-relative entries in this table resolve under `private-campaign-1`.
The final root stdout receipt in `work/private-campaign-1-console.txt` names the
actual result/index hashes above, with refused status and empty secondary errors.

## Resource and source accounting

The owner Job has terminal user CPU 23,437,500 ticks and kernel CPU 15,000,000
ticks, summing to 38,437,500 100-ns ticks, or **3.84375 seconds**. Owner CPU is
**1.046875 seconds**. The independent sum is therefore **4.890625 CPU seconds**,
matching both the stored work and final stdout. Nested stage totals are not
added again. The worker Job includes eight lifetime process associations; the
grid-producer Job includes six and the first Rust Job includes two. These are
accounting populations, not independently identified process executables.

The owner's final stdout wall observation is **4.937999999965541 seconds**, with
173,079 bytes of cumulative observed per-path high-water artifacts. Independent
`Get-ChildItem -Recurse -Force -File` readback within `private-campaign-1` finds
**ten retained files totaling 173,078 bytes**: eight indexed files (140,458 bytes), the 2,088-byte index and
the 30,532-byte terminal result. The one-byte excess of the observed high-water
counter over final retained size is not forced into equality; the contracts
measure different things. The result's earlier artifact observation is 142,547
bytes, before its own final 30,532-byte publication. The outer work stays below
600 CPU seconds, 1,200 wall seconds and 128 MiB, but that does not waive the
process refusal.

The encompassing Job recorded flags 8,704, configured committed memory
8,589,934,592 bytes, peak Job committed usage 1,627,049,984 bytes, zero final active
processes, terminal accounting true and empty cleanup errors. The first Rust
Job recorded 0.359375 CPU seconds and approximately 0.359 wall seconds, peak Job
committed usage 2,457,600 bytes, two lifetime associations and zero final active
processes. Neither memory number is labelled RSS.

Readback independently rehashed all **133 released sources**, **19 release
inputs**, and **eight indexed artifacts**, with no mismatch. A scoped Git diff
against `f9ee06a4` over those released source/input paths was empty at inspection.
Both original compiler executable and copied executable still have 29,488,640
bytes and SHA256
`8ecf5dfbb9270eef5ab99a9306bd1edb8cd0180e6128e86ad1bb18420b09b0e1`.

**Post-terminal source chronology:** after those checks, root declared an
unexecuted helper repair. The working `bounded-process.py` then changed to
SHA256 `47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b`.
It was not the helper used by campaign 1. This audit rechecked the old 10,522-byte
`1dba8d87…` source in
`controller-controls-3/sources/experiments/m193c-output-grid/bounded-process.py`
and reads the failing line/finally sequence from that retained source. The
current-source equality above describes the earlier readback, not equality after
the prospective repair. Root reports no source change during the actual run;
all original campaign artifacts remain untouched.

The grid producer retained 123 matching before/after source bindings and 153
matching before/after input bindings. The owner **did not reach** its normal
successful source/input finalization: its `sources_after` and `inputs_after`
are null. The current independent rehash is later readback, not a replacement
for those missing success fields. Likewise its `worker_result`, admitted reads
and products remain empty/null even though the failed worker files were retained
and available for this audit. No source-snapshot population is invented.

## What the helper actually established

The executed helper is `bounded-process.py`, 10,522 bytes, SHA256
`1dba8d87c8818aecf98078d1a926e5ff9c059a7d242cf5c46fcc962f14dfc5ab`.
After stdout EOF and direct-child wait, it samples Job accounting and immediately
asserts `active_processes == 0` at line 161. That assertion produced the recorded
error. The `finally` block subsequently overwrites `job_accounting` while
performing conditional owned-Job termination and terminal observation.

Consequently the retained record does **not** contain the original nonzero
active count, its process IDs, a drain interval, or an explicit record of whether
`TerminateJobObject` was attempted. It establishes a nonzero sample followed by
final zero; it cannot distinguish natural shutdown from explicit cleanup or
identify a shim. Its diagnostic phrase “active descendant” should not be promoted
to a verified identity or lasting leak.

Microsoft defines `TotalTerminatedProcesses` as **“The total number of processes
terminated because of a limit violation.”** Therefore its zero value is not an
audit trail proving that no cleanup termination occurred. The same primary page
describes `ActiveProcesses` as current Job association accounting, including
temporary increments on failed limit association and decrement on exit/reference
release. It does not promise that an immediate query after the direct child's
wait must already be zero. See
[JOBOBJECT_BASIC_ACCOUNTING_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).
The nested-parent sum used above follows Microsoft's
[Nested Jobs accounting](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs),
not a sum of overlapping local receipts.

A healthy short shutdown interval and a persistent live descendant can both
produce the instantaneous nonzero observation retained only as an error here.
This is a diagnostic limitation, not proof that this particular failure was
benign. The conservative refusal must remain in history.

## Bounded prospective disposition

The smallest defensible next action is a separately reviewed process-only
amendment: retain the pre-drain observation, poll for terminal zero within a
fixed small drain interval and the original remaining CPU/wall/memory/log/input
bounds, and record explicit cleanup termination attempt/return plus final
accounting. It must not accept a child while active associations remain or count
forced cleanup as natural completion.

The corresponding positive control needs an actual descendant that outlives
the direct parent and closes the parent's captured output stream, then exits
within the registered interval; it must prove the nonzero pre-drain case
occurred. A persistent companion must remain active beyond that interval and
cause refusal/owned cleanup. The existing eleven process controls remain
separate evidence. Root and Curie are preparing those controls; this review did
not run them, change a time allowance, amend a metric bar, or retry the images.

**Disposition: preserve campaign 1 as refused and incomplete.** The 45 grid
controls, ten grid cases, 3,712 precision samples, 32+41 derivative checks and
twelve product images were not reached, so none obtains new measured support
from this attempt. Any later private execution needs the repaired source,
reviewed controls and a new frozen release.
