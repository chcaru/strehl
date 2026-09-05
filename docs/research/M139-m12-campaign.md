# M139 — registered M12 scorecard campaign

**Status:** the registered campaign is complete. **M12-D PASS.** The measured
M12-S byte property is **FAIL**, while M12-S's required M11 precondition is
**BLOCKED-BY-LICENCE**. Those sub-results are not conflated, and no overall M12
verdict is assigned. The absolute-memory bar is **FAIL**, the observed
N=299/N=33 memory ratio misses its numeric bar but is formally
**UNMEASURED_SAMPLING_COVERAGE**, and the N-mod-4 timing bar is **FAIL**.
**HOST RELEASED.**

The frozen harness's conjunctive adjudication mechanically yields **M12 FAIL**
from the measured hard failures. That value is preserved in the machine
artifacts as `frozen_registration_mechanical_result`. The later binding
orchestrator instruction requires the lane handoff to keep M12-D, the M12-S
byte property, and the blocked M11 term separate and to assign no overall M12
verdict while that term is licence-blocked. The reported overall disposition
is therefore **NOT_ASSIGNED**, with the mechanical **FAIL** retained rather
than erased.

**Measured source:** `8009447e059febb8f9c59fda509f141835d6abdb`. This was the
exact repository `HEAD` frozen at dispatch and contains crop-early commit
`248178b921f98ec1f13ea4c07d30fa68ace787a0` as an ancestor. The release binary
was built from an isolated `git archive` of the measured commit, not from the
subsequently changing shared worktree.

## 1. What the registration says

Everything in this section is **INHERITED** from the scorecard at the measured
commit. The exact source text is also frozen in
`experiments/m12-scorecard/out/campaign-8009447e-m139/registration.json`.

The scorecard's one-line axis definition is:

> Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`;
> every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16
> workers are mutually byte-identical while 16 workers passes M11; N-mod-4
> per-frame spread `<=2%`.

Source:
`docs/proposals/2026-09-sota-scorecard.md@8009447e059febb8f9c59fda509f141835d6abdb:403`.

The governing section registers:

- Native ARWs at N=`33/105/299`, workers=`1/2/4/8/16`, one warm-up and six
  alternating-order scored repetitions per cell
  (`docs/proposals/2026-09-sota-scorecard.md@8009447e059febb8f9c59fda509f141835d6abdb:1044`,
  `:1053-1059`, `:1097-1100`).
- Whole-process-tree private committed bytes and working set sampled every
  10 ms, reporting peak committed bytes (`:1051-1052`, `:1100`).
- Hashes of the highest-precision delivered bytes, not a later 8-bit proxy
  (`:1053-1055`).
- M12-D as distinct hashes within each fixed `(N, worker_count)` six-run cell,
  and M12-S as distinct hashes across workers `1/2/4/8/16` at each N
  (`:1056-1059`).
- `peak_N299/peak_N33` (`:1060`) and a timing arm at
  N=`96/97/98/99`, worker=`16`, with the same warm-up/six-sweep protocol
  (`:1061-1062`, `:1100-1102`).
- Success bars of warm peak `<=6 GiB`, ratio `<=1.10`, one fixed-worker hash
  per cell, one cross-worker hash per N, and N-mod-4 per-frame spread `<=2%`
  (`:1064-1069`).
- A joint M11 condition: the 16-worker output must pass M11 while reproducing
  at fixed width and matching the 1/2/4/8-worker outputs
  (`docs/proposals/2026-09-sota-scorecard.md@8009447e059febb8f9c59fda509f141835d6abdb:122`,
  `:1068-1070`).

A **scored run** is one of the six post-warm-up repetitions at a registered
cell. Warm-ups and commissioning/smoke runs are not scored. The older N=20
workers 1/4/8 sweep is explicitly diagnostic because it is outside the
registered N/worker matrix, lacks workers 2 and 16, and lacks the registered
command/output manifest. The scorecard rules it:

> **diagnostic M12-D PASS / diagnostic M12-S FAIL**, while both formal sub-bars
> and M12 overall remain **UNMEASURED**.

Source:
`docs/proposals/2026-09-sota-scorecard.md@8009447e059febb8f9c59fda509f141835d6abdb:1072-1087`.
Execution attempts rejected by the frozen host gates, or later excluded with
an explicit contamination record, remain evidence in `records.jsonl` but do
not fill a scored position.

### Reconciliation with the dispatch description

The dispatch description was correct about N=`33/105/299`,
workers=`1/2/4/8/16`, six scored repetitions per cell, the `6 GiB` ceiling,
and the N=20 sweep being diagnostic only.

It was incomplete in two ways:

1. M12 does not measure only memory and fixed-worker determinism. It also
   measures cross-worker byte invariance, a 299/33-frame memory ratio, and the
   timing-derived N-mod-4 statistic.
2. The registered campaign includes the additional N=`96/97/98/99`,
   worker=`16` timing arm.

M12 does not have a general throughput-ratio bar of its own. Its direct
clock-dependent quantity is the N-mod-4 spread. M12-S additionally depends on
M11, whose scorecard bar does include comparator throughput.

## 2. Timing dependence and host validity

**INHERITED:** M12 is partly timing-dependent:

> For N=96–99, divide warm wall time by N and compute `(max-min)/min`.

Source:
`docs/proposals/2026-09-sota-scorecard.md@8009447e059febb8f9c59fda509f141835d6abdb:1061-1062`.
Host contention is therefore a validity threat to the modulo arm. It is not a
validity threat to direct byte hashes, and it cannot manufacture a sampled
private-commit value above the memory ceiling.

**VERIFIED:** the registered host gates were never relaxed:

- five-second preload whole-host busy fraction `<=0.15`;
- during-run external busy fraction `<=0.10` of wall capacity across 32
  logical processors.

The self-imposed six-sample `<=0.05` resume precondition was dropped. It added
no registered per-run CPU protection beyond those two gates and was
operationally unreachable while the shared agent runtime itself generated
responses. The registered `<=0.15` and `<=0.10` gates remained unchanged.
Because CPU gates do not directly bound memory bandwidth, page-file activity,
filesystem-cache state, storage contention, thermal state, or turbo state, the
final timing tail also required no named Cargo/Rust/Strehl/ExifTool contender.

The promised 120-minute quiet-host window was not uninterrupted. M130
overlapped the early fixed-matrix campaign; M172 and later Cargo, Rust compiler,
linker, byte-freeze, and external Strehl work overlapped attempted modulo
windows. No timing was adjusted. Every affected observation was retained and
excluded, then rerun:

- `294` total attempts;
- `133` accepted registered positions;
- `97` pure host-load rejections;
- `64` rows carrying explicit external-invalidation metadata;
- `62` previously accepted rows later invalidated: `22` in the M172/one-core
  exclusion, `28` in the conservative full-window exclusion, and `12` in the
  final compiler-overlap tail exclusion;
- `0` invalid process outputs;
- no duplicate accepted position.

The final score-driving timing minima were produced while the shared runtime
was suspended. `runtime-quiesce-final.json` records runtime PID `11336`,
harness PID `7956`, successful suspend/resume status `0`, and a guarded
interval from `2026-09-05T01:52:08.8526539Z` through
`2026-09-05T01:58:50.7554668Z`. All four selected minima start and complete
inside that interval. Their measured external-busy fractions were
`0.0248361` to `0.0299663`.

The campaign boundary samples were `0.0411771` whole-host wall capacity at
start and `0.0204439` at end. The maximum external-busy fraction among all
accepted runs was `0.0991197`, below the registered `0.10` bar.

Small read-only probes between runs can perturb filesystem-cache or I/O state
without crossing a CPU gate. They do not affect the byte verdict, and they
cannot create the observed memory failure. For timing, the registered
alternating sweeps reduce monotone drift, and the actual four minima came from
the contender-free runtime-suspended interval. Residual thermal, turbo, and
cache state was not directly instrumented and remains in the could-not-
determine list.

## 3. Instrument commissioning

All measurements in this section are **VERIFIED**.

### Process-tree memory probe

The final monitor places the target and descendants in a Windows Job Object,
queries that process-tree membership, and samples private committed bytes every
10 ms.

| Control | Requested allocation | Sampled peak | Kernel Job peak | Processes seen | Outcome |
|:--|--:|--:|--:|--:|:--|
| Null | 67,108,864 B | 80,920,576 B | 80,928,768 B | 2 | stayed below 6 GiB |
| 7-GiB plant | 7,516,192,768 B | 7,544,352,768 B | 7,544,406,016 B | 2 | exceeded 6 GiB |

The positive plant therefore made the gate fire, while the null stayed quiet.
Evidence:
`experiments/m12-scorecard/out/campaign-8009447e-m139/memory-commission.json`.

### Determinism probe

The probe hashes both the delivered uncompressed 16-bit RGB TIFF and a
canonical decoded uint16 pixel payload.

- Baseline TIFF:
  `790570CF966ADDF883D1E1BF8CE093A0978676540EAB447D3CFA159A5EE8B8CC`.
- Baseline pixels:
  `5AC84D9E7B5587E629E4B63EB55DE2777947D093DBA065C279015952EA4F0F03`.
- Positive algorithm plant TIFF:
  `8701BB33D55BBFF13878F1C488970429CDB7BE1D73D72A768640AA3AB7BE1CDD`.
- Positive algorithm plant pixels:
  `AAF8B57CD2EF20463503E3A22061690AEF098C4AA593B4A784B566448F5A049C`.
- Null restoration reproduced both baseline hashes exactly.
- The named one-LSB plant changed decoded pixel `[2344,3516,1]` from `6577`
  to `6576` and changed the TIFF hash to
  `15098E47164E77BC1C70D7E2F373631B74537DB999CADCE72E3C9AE250190061`.

The positive defects therefore produced actual hash mismatches, and the null
restoration stayed quiet. Evidence:
`experiments/m12-scorecard/out/campaign-8009447e-m139/determinism-commission.json`.

### End-to-end smoke

The N=3, worker=1 smoke completed one warm-up and two scored-form repeats
through RAW decode, registration, pyramid merge, 16-bit TIFF delivery,
process-tree monitoring, and both hashes. The repeats were byte-identical.
Evidence:
`experiments/m12-scorecard/out/campaign-8009447e-m139/smoke.json`.

## 4. Measured results

All numbers in this section are **VERIFIED** from accepted records at measured
commit `8009447e059febb8f9c59fda509f141835d6abdb`. `Hashes` is the number of
distinct TIFF/pixel hashes in the six-run cell. Full 64-hex hashes for every
cell are in `closeout.json`.

| N | Workers | Scored runs | Hashes | Sampled peak GiB | Job peak GiB | Memory `<=6 GiB` |
|---:|---:|---:|:--:|---:|---:|:--|
| 33 | 1 | 6 | 1 / 1 | 2.246288 | 2.246288 | PASS |
| 33 | 2 | 6 | 1 / 1 | 4.474476 | 4.474667 | PASS |
| 33 | 4 | 6 | 1 / 1 | 8.931198 | 8.931210 | **FAIL** |
| 33 | 8 | 6 | 1 / 1 | 15.610374 | 15.611515 | **FAIL** |
| 33 | 16 | 6 | 1 / 1 | 24.396610 | 24.396667 | **FAIL** |
| 105 | 1 | 6 | 1 / 1 | 2.246090 | 2.246090 | PASS |
| 105 | 2 | 6 | 1 / 1 | 4.475765 | 4.475765 | PASS |
| 105 | 4 | 6 | 1 / 1 | 8.932907 | 8.932907 | **FAIL** |
| 105 | 8 | 6 | 1 / 1 | 17.837124 | 17.837166 | **FAIL** |
| 105 | 16 | 6 | 1 / 1 | 33.181316 | 33.428261 | **FAIL** |
| 299 | 1 | 6 | 1 / 1 | 2.246307 | 2.246307 | PASS |
| 299 | 2 | 6 | 1 / 1 | 4.476284 | 4.476284 | PASS |
| 299 | 4 | 6 | 1 / 1 | 8.935242 | 8.935242 | **FAIL** |
| 299 | 8 | 6 | 1 / 1 | 17.836506 | 17.836559 | **FAIL** |
| 299 | 16 | 6 | 1 / 1 | 35.657242 | 35.657452 | **FAIL** |

### M12-D: PASS

All 15 fixed-worker cells have six accepted repetitions, one TIFF hash, and
one pixel hash. **M12-D PASS.**

### M12-S byte property: FAIL; M11 precondition: BLOCKED-BY-LICENCE

| N | Distinct TIFF hashes across workers | Distinct pixel hashes across workers | Byte property |
|---:|---:|---:|:--|
| 33 | 5 | 5 | **FAIL** |
| 105 | 5 | 5 | **FAIL** |
| 299 | 5 | 5 | **FAIL** |

The cross-worker byte property therefore fails independently at every
registered N.

M12-S also requires the 16-worker output to pass M11. **INHERITED** machine
evidence records Zerene's exact licence line as
`License category = TRIAL`, expiring `Sat Jun 06 20:13:34 PDT 2026`
(`docs/research/M132-blocker-d-routes.md:160-175`), and records the vendor rule
that after trial expiry saving images and projects is disabled
(`docs/research/M132-blocker-d-routes.md:176-182`). The same investigation found
“zero Helicon-named installation, state, log, licence, key, or registry
matches” (`docs/research/M132-blocker-d-routes.md:195-205`).
`docs/OWNER-ACTIONS.md:1560-1562` records that the installed Zerene trial is
consumed and expired and “currently cannot save output at all.”

Accordingly:

- measured M12-S byte property: **FAIL**;
- M12-S M11 precondition: **BLOCKED-BY-LICENCE**;
- formal M12-S status: **BLOCKED-BY-LICENCE**, not manufactured as PASS or
  FAIL;
- overall M12 verdict: **NOT_ASSIGNED**.

Even if a future licensed M11 run passes, the cross-worker byte property at
this measured commit remains a measured failure.

For completeness, the frozen harness's generic conjunctive rule mechanically
records M12 **FAIL** because cross-worker invariance, absolute memory, and
N-mod-4 timing are hard failures. `summary.json` and `closeout.json` preserve
that mechanical value separately from the orchestrator-directed
`NOT_ASSIGNED` program disposition.

### Absolute memory: FAIL

The maximum sampled process-tree private committed value was
`38,286,671,872` bytes (`35.65724182128906 GiB`) at
`scored:N299:W16:R3`. The corresponding maximum Job Object peak for the cell
was `35.65745162963867 GiB`. Both exceed the `6 GiB` bar. **Absolute memory
FAIL.**

### N=299/N=33 memory ratio

| Workers | Sampled-peak ratio | Kernel-Job-peak ratio | Numeric `<=1.10` |
|---:|---:|---:|:--|
| 1 | 1.000008 | 1.000008 | PASS |
| 2 | 1.000404 | 1.000361 | PASS |
| 4 | 1.000453 | 1.000451 | PASS |
| 8 | 1.142606 | 1.142526 | **FAIL** |
| 16 | 1.461565 | 1.461571 | **FAIL** |

The observed maximum is `1.4615654159027742`; the independent Job Object
maximum is `1.461570587793803`. Both miss the `1.10` numeric bar.

The frozen execution adjudication requires every scored run to meet at least
`0.90` sampling coverage before assigning this ratio a formal PASS or FAIL.
Minimum coverage was `0.7957678743186919`; maximum sample gap was
`60.85830001393333 ms`, within the `100 ms` gap limit. The observed miss is
reported, but the formal ratio verdict is
**UNMEASURED_SAMPLING_COVERAGE**.

### N-mod-4 timing: FAIL

The registered statistic uses the minimum warm wall time at each N, divides by
N, then computes `(max-min)/min`.

| N | Selected wall time (s) | Seconds/frame | External busy | Guarded |
|---:|---:|---:|---:|:--|
| 96 | 27.420756500 | 0.285632880 | 0.0269598 | yes |
| 97 | 27.290916300 | 0.281349653 | 0.0271954 | yes |
| 98 | 26.010375700 | 0.265411997 | 0.0248361 | yes |
| 99 | 27.260427500 | 0.275357854 | 0.0299663 | yes |

The spread is `0.07618677189815302` (`7.618677%`) against a `0.02` (`2%`)
bar. **N-mod-4 FAIL.** Every N also retained one TIFF hash and one pixel hash
across its six accepted timing repetitions.

## 5. Input provenance and read-only guarantee

All values are **VERIFIED**.

- Frozen scorecard SHA-256:
  `ADB31AAFD415F042D3C539A11351F70C6C834181C1FDB24C76FE03CFE9B07DB6`.
- Frozen release binary SHA-256:
  `DD5C98C2FF091DFFBF08A580E41C5C5F2C2F6E6996BB831CFC499ED833996A24`.
- Frozen harness SHA-256:
  `6CFB408992F37B225F102DA4D62BA836F9C5B67C92BDD418FF460987866A1BB9`.
- Run manifest SHA-256:
  `BFFFF91C0FB01854E30C0C34481E99FEA524E9BF314EFA8FC198D0B623238DB5`.
- Final records SHA-256:
  `5D6046F5DEA1E2FD64AF25B70F26F1371C7CEEDF1B7D7B83A504B01F3D1AFF26`.

Read-only before/after metadata snapshots match exactly:

| Protected tree | Items | Files | Bytes | Metadata SHA-256 | Result |
|:--|--:|--:|--:|:--|:--|
| `D:\personal\macro` | 10,806 | 10,724 | 487,169,829,957 | `46CD6FE5C018AE4ACEC946170EEEC760DBF5B0C8954CA561368F92B9184A5C42` | unchanged |
| `D:\edited\macro` | 392 | 387 | 141,333,902,406 | `40003B9F15D0AE552AD2947E22C29122664E0BDCD7E690D53FE02341DCA12FD1` | unchanged |

Nothing was written, moved, renamed, or deleted under either protected tree.

## 6. Artifacts

All campaign artifacts record measured commit
`8009447e059febb8f9c59fda509f141835d6abdb` and live under
`experiments/m12-scorecard/out/campaign-8009447e-m139/`.

- `RUN-MANIFEST.json`: immutable commit, binary, harness, flags, input hashes,
  schedule, and host gates.
- `registration.json`: commit-pinned verbatim registration and source lines.
- `input-manifest.json`: per-input provenance.
- `records.jsonl`: all `294` attempts, accepted status, host observations,
  hashes, memory samples, and explicit invalidation metadata.
- `summary.json`: mechanical measurements plus corrected split-verdict
  adjudication and record accounting.
- `closeout.json`: authoritative machine-readable result, all 15 cells, both
  commissioning controls, host conditions, read-only proof, and uncertainty
  ledger.
- `audit.json`: integrity PASS and SHA-256 manifest for every persistent root
  campaign artifact; six ignored local build logs are identified separately
  and are not required to reproduce the adjudication.
- `memory-commission.json`, `determinism-commission.json`, and `smoke.json`:
  bidirectional commissioning and end-to-end smoke.
- `m172-overlap-invalidation.json`,
  `final-modulo-window-invalidation.json`, and
  `final-window-tail-invalidation.json`: retained contamination exclusions.
- `records-before-m172-invalidation.jsonl`,
  `records-before-final-modulo-rerun.jsonl`, and
  `records-before-final-tail-rerun.jsonl`: pre-invalidation checkpoints.
- `final-window-start.json`, `final-window-start-r2.json`,
  `final-window-start-r3.json`, `final-window-start-r4.json`, and
  `runtime-quiesce-final.json`: attempted and final guarded timing windows.
- `host-start.json`, `host-end.json`, `read-only-before.json`, and
  `read-only-after.json`: boundary and protected-tree evidence.

Reproduction and adjudication helpers are in `experiments/m12-scorecard/`:

- `m12-harness.py`;
- `m139-tree-snapshot.ps1`;
- `m139-invalidate-overlap.py`;
- `m139-invalidate-modulo-window.py`;
- `m139-invalidate-final-tail.py`;
- `m139-quiesce-runtime.ps1`;
- `m139-finalize.py`.

## 7. Could not determine

1. **Formal N=299/N=33 memory-ratio verdict.** The numeric sampled and kernel
   ratios are reported, but minimum sampling coverage missed the frozen 90%
   adjudication threshold.
2. **M11 comparator throughput.** The installed Zerene trial cannot save the
   required output, and no Helicon installation is available.
3. **True unsampled instantaneous memory peak.** Sampling can miss a higher
   instantaneous value. It cannot manufacture the observed above-6-GiB
   failure.
4. **Complete process-tree read/write byte totals.** The instrument records
   temp bytes, page faults, CPU, hashes, and memory, but not complete
   process-tree I/O totals.
5. **Calibrated residual thermal, turbo, and cache state.** Those variables
   were not directly instrumented. Alternating sweeps and the guarded
   scoring-minimum interval mitigate them.
6. **Exact lane attribution for every historical host-load rejection.** Named
   contamination incidents were pinned where observed, but not every rejected
   CPU interval can be assigned to one lane.
