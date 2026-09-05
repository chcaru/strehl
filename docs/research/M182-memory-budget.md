# M182 — M12 process-tree memory attribution

**Status: MEASURED AT THE FAILING REVISION; DIAGNOSTICALLY RE-MEASURED AT THE
CURRENT MEMORY IMPLEMENTATION.** No production source was changed. This lane
does not adjudicate M12-S and does not promote a two-run diagnostic into a
formal scorecard rerun.

**INERT COMMISSION ANCHOR:** This sentence carries no measured value; changing it must stay green.

## 1. The bar, before the optimisation

The governing proposal says, verbatim at
`docs/proposals/2026-08-sota-path.md:1981`:

> memory ≤6 GiB warm; bytes invariant to worker count (D9a); the staircase gone

Its section heading is “D13. Scaling — all sixteen cores inside the same six
gigabytes,” and the body says workers each carried about 1.3 GB “against the
6 GiB budget.” The scorecard says, verbatim at
`docs/proposals/2026-09-sota-scorecard.md:817`:

> Warm peak process-tree memory `<=6 GiB`

**CANONICAL BAR RULING:** The documents do not disagree: this is one 6-GiB process-tree budget, including the 16-worker cell, not 6 GiB per process or per worker.

“Warm” excludes the dedicated warm-up invocation, not allocations at the
beginning of every scored invocation. The scorecard specifies one warm-up and
then six scored repetitions. The harness creates each scored process suspended
(`m12-harness.py:934-944`), assigns the whole tree to a Job Object, starts
sampling immediately, and stops only after the tree exits. Startup, the
prologue decode, and the first frame therefore remain in scope. M139 retained
15 separate warm-up invocations and 90 separate scored invocations.

The peak W16 run contained one `strehl.exe`, not sixteen child processes:
“workers” were Rayon threads. Process-tree and per-process happened to coincide
for that run, but the registered definition remains process-tree so future
children cannot escape it.

**CANONICAL M139 PEAK:** At N299/W16, sampled private commit reached `38,286,671,872 B = 35.657241821 GiB` (`scored:N299:W16:R3`); the cell's independent kernel Job peak was `38,286,897,152 B = 35.657451630 GiB`, only `225,280 B` higher.

The agreement of independent counters makes the failure real, not a 10-ms
sampling artefact. A missed sample can hide a larger peak, but cannot invent
the allocation already observed.

## 2. Reproduction and scaling law

I reran the frozen `8009447e059f` binary (SHA-256
`DD5C98C2FF091DFFBF08A580E41C5C5F2C2F6E6996BB831CFC499ED833996A24`)
on the registered native-ARW product path with the validated N33 sidecar.
Inputs were only read; outputs, caches, and temp files were under the owned
experiment path.

| workers | fresh Job peak | M139 N33 cell maximum | fresh/canonical delta |
|---:|---:|---:|---:|
| 1 | `2,411,413,504 B` | `2,411,933,696 B` | `-0.021567%` |
| 2 | `4,804,800,512 B` | `4,804,636,672 B` | `+0.003410%` |
| 4 | `9,586,323,456 B` | `9,589,813,248 B` | `-0.036391%` |

All three runs exited zero with valid full-resolution linear-RGB TIFF witnesses
before those large outputs were removed. Their fitted marginal cost is
`2.227269 GiB/worker` (`R²=0.999999926`).

The full 15-cell M139 matrix reveals the exact staircase. With
\(C(N,W)=\lceil N/\lceil N/W\rceil\rceil\) simultaneously active chunks, W16
uses 11 chunks at N33, 15 at N105, and 16 at N299.

**CANONICAL SCALING LAW:** `peak = 25,181,904 B + 2,389,457,520.495 B * active_chunks`, with `R²=0.999992392` across all 15 M139 cells.

Thus the peak is controlled by retained whole-worker bundles, not primarily by
N. N matters only because the old `par_chunks(ceil(N/W))` sometimes creates
fewer chunks than requested workers.

## 3. Allocation attribution

The registered plane is 3516×2344 (`8,241,504` samples); its eight pyramid
levels total `10,988,941` samples. I counted the exact vector lengths in
`8009447e` and checked their sum against the empirical slope.

| rank | simultaneously allocated consumer | exact bytes per active chunk | N299/W16 bytes |
|---:|---|---:|---:|
| 1 | `BandMerge`: 9 pyramids plus 8 level-0 input-hull planes | `659,330,004 B (628.786 MiB)` | `10,549,280,064 B (9.825 GiB)` |
| 2 | `FrameWorkspace`: two operator workspaces, seven pyramids, four level-0 fields | `571,460,668 B (544.987 MiB)` | `9,143,370,688 B (8.515 GiB)` |
| 3 | full-resolution gather: mosaic plus R/G/B f32 planes | `527,456,256 B (503.021 MiB)` | `8,439,300,096 B (7.860 GiB)` |

The remaining per-chunk allocations are the gate-floor probe
(`208,799,908 B`), extracted planes/luma/variance (`197,796,096 B`), warp
scratch (`74,173,536 B`), and the real plus cloned probe frames
(`146,800,640 B`).

**CANONICAL ATTRIBUTION CHECK:** Source accounting totals `2,385,817,108 B = 2.221965332 GiB` per active chunk, `99.847647%` of the fitted `2.225355730 GiB` slope; the unexplained remainder is `3,640,412 B` per chunk.

This also explains why the banner's “1328 MB per worker” was not a memory
measurement: `FrameWorkspace::floats()` omitted `ghull` and the plane-cache
workspace, and the plan omitted the full-resolution gather, gate probe, and
probe-frame clone.

## 4. Concrete reduction and present state

The necessary change is bounded; tiling is not required. The fold already
streams frames. Its defect was equating execution threads with simultaneously
resident full-frame states.

| step | files/functions | allocation change | estimated N299/W16 saving |
|---:|---|---|---:|
| 1 | `merge_cmd.rs::run_pyramid`, `BandWorker::reset_chunk` | run canonical chunks serially through one reusable frame worker; keep a 16-thread pool for spatial work | `25,897,306,560 B (24.119 GiB)` from 15 duplicate non-accumulator bundles |
| 2 | `pyramid.rs::BandMerge::reset_for_reuse` | retain the result plus one resettable scratch accumulator instead of 16 partials, preserving chunk boundaries and absorb order | `9,230,620,056 B (8.597 GiB)` from 14 accumulators |
| 3 | pyramid row operators plus `extract_planes`/`load_frame` | parallelise disjoint rows and planes inside that one worker | no direct byte saving; this preserves 16-thread execution without restoring the allocations |

While this investigation was running, M172 independently landed exactly that
shape at `a97275817c58e164f75c7cd3d80ca99444a2a145`; it is still the last commit
touching both memory-owning files, with no worktree diff. I did not alter or
extend it.

| frozen `a9727581` diagnostic | kernel Job peak | bar relation |
|---|---:|---:|
| N33/W16 | `3,074,424,832 B = 2.863281250 GiB` | pass |
| N299/W16 | `3,074,797,568 B = 2.863628387 GiB` | pass |

**CANONICAL BOUNDED VERDICT:** The current memory implementation is `12.451843x` below M139's N299/W16 peak, leaves `3,367,653,376 B = 3.136371613 GiB` headroom, and measures `peak_N299/peak_N33 = 1.000121238`.

These are one diagnostic run per N, not the registered six-repeat matrix.
Their host timing gates failed because of unrelated load, so their wall times
are not evidence. Job-private commit excludes that load; both sample gaps
remained below 100 ms and the unsampled kernel peak supplies the memory result.
A formal current-commit M12 campaign is still required before changing the
scoreboard.

### 4.1 Prior-work boundary and N7

I audited the committed M172 material after the bounded-memory handoff:
`a9727581`, `measure_memory.py`, its committed campaign and negative-control
summaries, and both M172 reports. The compact M172 campaign is a throughput and
worker-semantics protocol, and `measure_memory.py` is a Job Object wrapper; they
do not contain a ranked source-allocation ledger. M172 therefore did not answer
step 3's top-three-consumer question. Its retained throughput campaign has zero
warm-ups and zero timed runs, so it supplies no throughput result to accept.
M172 did answer the architectural half of step 4 by landing the
reusable-worker/two-accumulator design at `a9727581`. I independently checked
that source shape and measured its memory, rather than inventing or re-deriving
a competing design.

The addendum requesting this explicit audit arrived after the first M182 report
commit, so that ordering cannot be made retroactive. The `a9727581` diff and
M172 meter wrapper had nevertheless already been read during the initial
investigation before I treated that candidate as the concrete step-4 answer.

**CANONICAL M172 BOUNDARY:** M172 supplied the `a9727581` bounded-memory candidate and its M12-S and prequantization evidence; M182 independently established the bar semantics, unrepaired failure/scaling, allocation ledger, fresh pre-repair W1/W2/W4 peaks, `a9727581` N33/N299 W16 memory, and meter commissioning; no unrerun M172 M12-S finding enters this memory verdict.

The M172 N33 cross-worker result and f32 negative control are accepted as
M172-owned findings but were not independently rerun or extended here. The
unfinished throughput protocol makes no result claim. These are adjacent
artifacts, not inputs to the memory verdict. The superseding
`M172-m12s-closure.md` is downstream rather than prior memory evidence: it was
committed after this M182 report's first commit and explicitly declines to
assess the memory repair. No M179 output was opened or used.

**CANONICAL N7 RULING:** the certifying unrepaired M139 campaign at `8009447e` was already RED at `38,286,897,152 B > 6,442,450,944 B`, and M182 independently reproduced a RED unrepaired W4 cell; the `a9727581` readings remain diagnostic and are not cashed as a pass before M179's certifying rerun.

## 5. Probe commissioning and correction to the briefing

The same Job Object meter saw both parent and child and was commissioned in
both directions from a uniquely anchored 256-MiB fixture:

**CANONICAL PROBE COMMISSION:** baseline `282,509,312 B`; planted allocation `551,432,192 B` (`+268,922,880 B`); planted saving `80,834,560 B` (`-201,674,752 B`); inert label-only arm `282,673,152 B` (`|delta|=163,840 B`); all five gates passed.

**CANONICAL CHECK COMMISSION:** `44/44` baseline checks passed; `44/44` uniquely anchored planted defects were caught; `0` were missed; `2/2` inert arms survived; both allocation-up and saving-down positive controls remained discriminating.

The assignment's N-mod-4 statement is arithmetically wrong; the repository
documents are already correct, so I changed none. Exact replacement text:

**CANONICAL BRIEFING CORRECTION:** Replace “N-mod-4 per-frame spread passes at `0.07618677189815302%` against `<=2%`” with “the fraction is `0.07618677189815302`, i.e. `7.618677189815302%`, so the numeric bar fails; M139 formally records `UNMEASURED_HOST_QUARANTINE`.”

The prohibited holdout was never listed or opened. No path under either
read-only RAW tree was written, moved, or deleted.

## 6. Commands and observed dispositions

Executed from the repository root; every command exited `0`:

```powershell
python experiments/M182-memory-budget/probe.py commission
python experiments/M182-memory-budget/probe.py run --name pre-n33-w1 --exe experiments/m12-scorecard/work/campaign-8009447e-m139/bin/strehl.exe --commit 8009447e059febb8f9c59fda509f141835d6abdb --limit 33 --workers 1 --cache-source experiments/m12-scorecard/out/campaign-8009447e-m139/cache/n33
python experiments/M182-memory-budget/probe.py run --name pre-n33-w2 --exe experiments/m12-scorecard/work/campaign-8009447e-m139/bin/strehl.exe --commit 8009447e059febb8f9c59fda509f141835d6abdb --limit 33 --workers 2 --cache-source experiments/m12-scorecard/out/campaign-8009447e-m139/cache/n33
python experiments/M182-memory-budget/probe.py run --name pre-n33-w4 --exe experiments/m12-scorecard/work/campaign-8009447e-m139/bin/strehl.exe --commit 8009447e059febb8f9c59fda509f141835d6abdb --limit 33 --workers 4 --cache-source experiments/m12-scorecard/out/campaign-8009447e-m139/cache/n33
python experiments/M182-memory-budget/probe.py run --name post-n33-w16 --exe experiments/M172-worker-memory/out/builds/post/bin/strehl.exe --commit a97275817c58e164f75c7cd3d80ca99444a2a145 --limit 33 --workers 16 --cache-source experiments/m12-scorecard/out/campaign-8009447e-m139/cache/n33
python experiments/M182-memory-budget/probe.py run --name post-n299-w16 --exe experiments/M172-worker-memory/out/builds/post/bin/strehl.exe --commit a97275817c58e164f75c7cd3d80ca99444a2a145 --limit 299 --workers 16 --cache-source experiments/m12-scorecard/out/campaign-8009447e-m139/cache/n299
python experiments/M182-memory-budget/analyze.py
python experiments/M182-memory-budget/verify.py --json
python experiments/M182-memory-budget/commission.py
```

The five product probes printed `valid: true`, `returncode: 0`, their Job
peaks shown in §§2 and 4, and non-null TIFF and pixel hashes. `analyze.py`
printed a summary consistent with the canonical rows above. `verify.py` printed
`PASS`; `commission.py` printed `COMMISSIONED`, with both directional controls
preserved. Machine-readable stdout fields and complete run metadata are
retained beside the scripts.
