# M139 — registered M12 scorecard campaign

**Status:** the registered campaign is complete. **M12-D PASS. M12-S FAIL.
M12 overall FAIL.** The absolute-memory bar is **FAIL**, the observed
N=299/N=33 memory ratio misses its numeric bar but is formally
**UNMEASURED_SAMPLING_COVERAGE**, and the N-mod-4 timing bar is **FAIL**.
**HOST RELEASED.**

The frozen harness's conjunctive adjudication yields **M12 FAIL** from the
measured hard failures. The scorecard's reverse dependency making M12-S wait
for all of M11 is an unratified addition not present in the governing proposal;
under plan precedence it does not withhold the measured M12-S result.

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
- The frozen scorecard's added M11 condition: the 16-worker output must pass
  M11 while reproducing at fixed width and matching the 1/2/4/8-worker outputs
  (`docs/proposals/2026-09-sota-scorecard.md@8009447e059febb8f9c59fda509f141835d6abdb:122`,
  `:1068-1070`).

The last clause is faithfully retained because it was in the registration at
the measured commit. It is not, however, a plan-level M12 requirement. The
governing plan registers:

> memory ≤6 GiB warm; bytes invariant to worker count (D9a); the staircase
> gone (per-frame cost flat in N mod 4).

Source: `docs/proposals/2026-08-sota-path.md:1973-1985`. M178 traced the reverse
M11 dependency to a later scorecard edit, classified it
**UNRATIFIED_ADDITION**, and retained only the forward anti-cheat rule: an M11
production-speed output must match the worker ladder
(`docs/research/M178-m12s-adjudication.md:1-16,20-45`). The current scorecard
records the same correction at
`docs/proposals/2026-09-sota-scorecard.md:11-24`.

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
clock-dependent quantity is the N-mod-4 spread. The frozen scorecard added a
reverse M11 dependency to M12-S, but the plan-precedence adjudication above
rules that addition inapplicable to the formal M12-S verdict.

## 2. Timing dependence and host validity

**INHERITED:** M12 is partly timing-dependent:

> For N=96–99, divide warm wall time by N and compute `(max-min)/min`.

Source:
`docs/proposals/2026-09-sota-scorecard.md@8009447e059febb8f9c59fda509f141835d6abdb:1061-1062`.
Host contention is therefore a validity threat to the modulo arm. It is not a
validity threat to direct byte hashes, and it cannot manufacture a sampled
private-commit value above the memory ceiling.

**INHERITED POST-CAMPAIGN POLICY:** `docs/STATUS.md:6234-6256` records three
whole-host samples of `88.6%`, `97.0%`, and `94.1%`, mean `93.2%`, and places
absolute wall-clock timing under a standing quarantine until it is reproduced
on a genuinely quiet host or restated as a within-run ratio in which host load
cancels. The M12 modulo statistic compares wall times across separate runs, so
its completed observation is retained as diagnostic evidence but is not a
formal score under that later policy.

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

The final observed timing minima were produced while the shared runtime was
suspended. `runtime-quiesce-final.json` records runtime PID `11336`, harness
PID `7956`, successful suspend/resume status `0`, and a guarded interval from
`2026-09-05T01:52:08.8526539Z` through
`2026-09-05T01:58:50.7554668Z`. All four selected minima start and complete
inside that interval, with measured external-busy fractions of `0.0248361` to
`0.0299663`. These facts make the observation useful diagnostics; they do not
override the later program-wide quarantine.

An earlier stalled N=299/W16 window produced 14 consecutive load-gate
rejections. The minimum external-busy fraction was
`0.10108949790738624` (`10.10895%`) against the registered `10%` limit. These
are gate-behavior measurements, not timing results. Later accepted runs prove
that this episode does not establish that the gate was mathematically
unsatisfiable; it establishes that indefinite waiting was not a schedulable
protocol.

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

The concrete precondition for a formal rerun is the registered uninterrupted
120-minute window on a **physically quiesced host**, not a nominal lane lock:
stop the agent fleet and unrelated editors/processes, record the boundary and
during-run host telemetry, retain the `<=15%` preload and `<=10%` external-busy
gates, and rerun all four warm-ups plus 24 scored modulo positions. M139 needs
no additional capture, hardware, or product build for that rerun.

### Admission-gate ruling and replacement protocol

The self-imposed `<=5%` resume precondition is **INSTRUMENT VOID on this
shared host**. It was specified as a desirable quiet condition without first
showing that the orchestration runtime and editor baseline could satisfy it.
At several points the agent runtime alone consumed nearly the entire allowance,
so waiting for repeated qualifying samples coupled progress to whether any
other agent happened to be generating a response. That is an operational
deadlock, not a measurement strategy. It was not part of the registered M12
bar, and dropping it did not relax the registered per-invocation gates.

A future contention-robust protocol should be scoped by measurement type:

- **Determinism:** no timing estimator is needed. Hash the highest-precision
  output directly across the registered repetitions. Host contention may
  lengthen a run, but it cannot be repaired or summarized by minimum-of-N and
  does not turn unequal bytes into equal bytes.
- **Memory:** retain whole-process-tree Job Object accounting, 10 ms samples,
  maximum peak across scored repetitions, sampling-coverage rules, and the
  planted over-allocation. Minimum-of-N is wrong for this quantity: selecting
  the smallest observed peak would reward an under-observed or
  pressure-dependent run, and external pressure can change paging and cache
  behavior in either direction.
- **Timing:** minimum-of-N plus an interleaved calibration witness is a
  defensible replacement for an absolute idle-host prerequisite, but only
  after commissioning. The witness must exercise the same relevant CPU,
  memory-bandwidth, and storage resources, run adjacent to every target
  invocation, and reject deviations on both sides of its commissioned range.
  A null must remain admitted, a planted slowdown must be rejected, and a
  planted speedup must also be rejected. This guards against both additive
  contention and flattering cache, turbo, affinity, or calibration failures.
  Sweep order remains alternating, and the registered minimum is taken only
  over witness-admitted repetitions.

For the M12 modulo arm, that replacement adds one calibration invocation beside
each of four warm-ups and 24 scored target runs, plus null, slowdown, and
speedup commissioning. It requires no hardware or new capture. If the witness
is target-length, the timed arm costs roughly twice its target-only runtime;
determinism and memory should not pay that cost because the calibration
estimator does not adjudicate their bars. This design is a proposal for the
next campaign and was not applied retroactively to M139.

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

The 64-MiB null peaked at `80,920,576` bytes in the sampled process-tree
measurement. The positive plant therefore made the gate fire, while the null
stayed quiet.

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

### Registered-bar decomposition

| Registered bar | Acceptance | Measured value | Verdict |
|:--|:--|:--|:--|
| Absolute memory | warm process-tree peak `<=6 GiB` | sampled private commit `35.65724182128906 GiB`; Job Object peak `35.65745162963867 GiB` | **FAIL** |
| N=299/N=33 memory ratio | `<=1.10` | `1.4615654159027742` sampled; `1.461570587793803` kernel; minimum coverage `0.7957678743186919` (`79.5768%`) | **UNMEASURED_SAMPLING_COVERAGE** |
| M12-D fixed-worker determinism | one TIFF hash and one pixel hash across six repeats in every fixed `(N, workers)` cell | one of each in all 15 cells | **PASS** |
| M12-S cross-worker invariance | one TIFF hash and one pixel hash across workers 1/2/4/8/16 at every N | five of each at N=33, 105, and 299 | **FAIL** |
| N-mod-4 per-frame spread | `<=2%` | `0.07618677189815302` (`7.618677%`) | observed **FAIL**; formal **UNMEASURED_HOST_QUARANTINE** |

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

The earlier four-decimal per-cell pins were not withdrawn. They are the same
Job Object peaks above, rounded: N33/W2 `4.4747`, N33/W16 `24.3967`,
N105/W1 `2.2461`, N105/W2 `4.4758`, N105/W8 `17.8372`, and N105/W16
`33.4283` GiB.

### M12-D: PASS

All 15 fixed-worker cells have six accepted repetitions, one TIFF hash, and
one pixel hash. **M12-D PASS.** This is the first registered sub-property in
the program to pass anything
(`docs/proposals/2026-09-sota-scorecard.md:11-15`). It is not an axis PASS, a
cross-worker claim, or a claim about any later binary. It is pinned to measured
commit `8009447e059febb8f9c59fda509f141835d6abdb`; the D9 reduction-lattice
change modifies the measured code path, so M12-D must be reverified on the
post-D9 build rather than inherited.

### M12-S: FAIL

| N | Distinct TIFF hashes across workers | Distinct pixel hashes across workers | Byte property |
|---:|---:|---:|:--|
| 33 | 5 | 5 | **FAIL** |
| 105 | 5 | 5 | **FAIL** |
| 299 | 5 | 5 | **FAIL** |

At three independent `N` values, the campaign found five distinct TIFF hashes
and five distinct pixel hashes across workers 1/2/4/8/16. The cross-worker byte
property therefore fails independently at every registered N.

The scorecard additionally says that the 16-worker output must pass all of M11.
That reverse dependency is an unratified scorecard addition, not a validity
precondition in the governing proposal. The plan-faithful forward rule remains:
any production-speed M11 output must be byte-identical across worker counts.

Accordingly:

- measured and formal M12-S status: **FAIL**;
- overall M12 verdict: **FAIL**.

A future licensed M11 run cannot change the cross-worker byte failure at this
measured commit. The frozen harness's generic conjunctive rule independently
records M12 **FAIL** because cross-worker invariance, absolute memory, and
N-mod-4 timing are hard failures.

### Absolute memory: FAIL

The maximum sampled private commit `35.65724182128906 GiB`
(`38,286,671,872` bytes) occurred at `scored:N299:W16:R3`. The corresponding
Job Object peak `35.65745162963867 GiB` also exceeds the `6 GiB` bar.
**Absolute memory FAIL.**

The partial-campaign close at `2ba256aa` remains a valid observation, but it is
no longer the campaign maximum: `scored:N105:W16:R2` had sampled private commit
`32.6777 GiB`, Job Object peak `33.4283 GiB`, and accepted external busy
`9.8763%`. Completing N=299 superseded its role as the strongest observation
with the N299/W16 values above. The accepted-run campaign-wide external-busy
maximum is `0.0991197` (`9.91197%`). None of the earlier numbers was
contradicted or withdrawn.

### N=299/N=33 memory ratio

| Workers | Sampled-peak ratio | Kernel-Job-peak ratio | Numeric `<=1.10` |
|---:|---:|---:|:--|
| 1 | 1.000008 | 1.000008 | PASS |
| 2 | 1.000404 | 1.000361 | PASS |
| 4 | 1.000453 | 1.000451 | PASS |
| 8 | 1.142606 | 1.142526 | **FAIL** |
| 16 | 1.461565 | 1.461571 | **FAIL** |

The observed maxima are `1.4615654159027742` sampled and
`1.461570587793803` kernel. Both miss the `1.10` numeric bar.

The frozen execution adjudication requires every scored run to meet at least
`0.90` sampling coverage before assigning this ratio a formal PASS or FAIL.
Minimum coverage was `0.7957678743186919` (`79.5768%`); maximum sample gap was
`60.85830001393333 ms`, within the `100 ms` gap limit. This prevents a positive
full-matrix memory-scaling claim. It does not weaken the negative
absolute-memory result, because both the sampled lower bound and independent
kernel peak exceed 6 GiB by multiples. The observed ratio miss is reported,
but the formal ratio verdict is **UNMEASURED_SAMPLING_COVERAGE**.

### N-mod-4 timing: observed FAIL, formally UNMEASURED_HOST_QUARANTINE

The registered statistic uses the minimum warm wall time at each N, divides by
N, then computes `(max-min)/min`.

| N | Selected wall time (s) | Seconds/frame | External busy | Guarded |
|---:|---:|---:|---:|:--|
| 96 | 27.420756500 | 0.285632880 | 0.0269598 | yes |
| 97 | 27.290916300 | 0.281349653 | 0.0271954 | yes |
| 98 | 26.010375700 | 0.265411997 | 0.0248361 | yes |
| 99 | 27.260427500 | 0.275357854 | 0.0299663 | yes |

The spread is `0.07618677189815302` (`7.618677%`) against a `0.02` (`2%`)
bar. The numerical observation is **FAIL**, but the formal timing verdict is
**UNMEASURED_HOST_QUARANTINE** under `docs/STATUS.md:6234-6256`. Every N also
retained one TIFF hash and one pixel hash across its six accepted timing
repetitions.

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

1. **Formal N-mod-4 timing verdict.** The completed observations are retained,
   but the later host policy requires quiet-host reproduction before they can
   enter the scorecard.
2. **Formal N=299/N=33 memory-ratio verdict.** The numeric sampled and kernel
   ratios are reported, but minimum sampling coverage missed the frozen 90%
   adjudication threshold.
3. **M11 comparator throughput.** The installed Zerene trial cannot save the
   required output, and no Helicon installation is available. This does not
   withhold the formal M12-S verdict under the plan-precedence adjudication.
4. **True unsampled instantaneous memory peak.** Sampling can miss a higher
   instantaneous value. It cannot manufacture the observed above-6-GiB
   failure.
5. **Complete process-tree read/write byte totals.** The instrument records
   temp bytes, page faults, CPU, hashes, and memory, but not complete
   process-tree I/O totals.
6. **Calibrated residual thermal, turbo, and cache state.** Those variables
   were not directly instrumented. Alternating sweeps and the guarded
   scoring-minimum interval mitigate them.
7. **Exact lane attribution for every historical host-load rejection.** Named
   contamination incidents were pinned where observed, but not every rejected
   CPU interval can be assigned to one lane.
