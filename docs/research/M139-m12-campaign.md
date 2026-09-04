# M139 — registered M12 scorecard campaign

**Status:** **formal M12 FAIL**. The accepted observations independently fail
the absolute-memory and cross-worker byte-invariance bars. The full registered
matrix was not completed: sustained shared-host contention stopped progress at
the N=299, worker=16 warm-up after the verdict had become irreversible.

**Measured source:** `8009447e059febb8f9c59fda509f141835d6abdb`. This is the
exact `HEAD` observed at dispatch, and it contains crop-early commit
`248178b921f98ec1f13ea4c07d30fa68ace787a0` as an ancestor. The binary was built
from `git archive` of that commit, not from live working-tree source.

## 1. Governing registration

All values in this section are **INHERITED** from
`docs/proposals/2026-09-sota-scorecard.md` as it exists at the measured commit.
The complete frozen section is embedded verbatim in
`experiments/m12-scorecard/out/campaign-8009447e-m139/registration.json`.

- The axis is explicitly **“M12 — memory, determinism, and scaling invariance”**
  (`docs/proposals/2026-09-sota-scorecard.md:1038`), and its purpose is that
  deep stacks remain “bounded and reproducible” (`:1040-1042`).
- The registered main matrix is “the same N=33/105/299 and worker-count matrix
  as M11” (`:1044`): workers `1/2/4/8/16`, one warm-up, then six scored
  repetitions per cell (`:1052-1058`, `:1098-1100`).
- The native-product bars are peak process-tree private committed memory
  `<=6 GiB`, `peak_N299/peak_N33<=1.10`, one hash in each six-run fixed-worker
  cell, one hash across all five worker counts at each N, and N-mod-4
  per-frame spread `<=2%` (`:1048-1069`).
- The modulo arm is N=`96/97/98/99`, workers=`16`, with the same warm-up and
  six-sweep protocol (`:1098-1102`).
- The older unaligned N=20, workers 1/4/8 sweep lacks workers 2 and 16 and the
  registered command/output manifest. It is explicitly “diagnostic M12-D PASS
  / diagnostic M12-S FAIL”; formal M12 remained `UNMEASURED`
  (`:1073-1087`).
- A scored observation is one of the six post-warm-up repetitions at a
  registered cell that also passes the frozen command/log and host-load gates.
  Warm-ups, smoke controls, retired-monitor records, load-rejected attempts and
  the old N=20 sweep are retained evidence but are not scored
  (`:1052-1058`, `:1073-1087`, `:1098-1100`).

### Prompt reconciliation

The prompt was correct about N=`33/105/299`, workers=`1/2/4/8/16`, six scored
runs per cell, the `6 GiB` ceiling, and the N=20 sweep being diagnostic only.
One point was incomplete: M12 does not score only memory and determinism. It
also scores cross-worker scaling invariance and the timing-derived N-mod-4
spread. In addition, M12-S requires the 16-worker output to pass M11
simultaneously (`:1064-1069`; joint constraint at `:122`).

## 2. Timing and host contention

**INHERITED:** M12 is timing-dependent because its N-mod-4 statistic divides
warm wall time by N and scores `(max-min)/min` (`:1060-1067`). Host contention
therefore threatens validity, not merely precision.

The execution manifest freezes the already documented host gate from
`docs/research/M-PHASE0-PIPE.md:245-257`: five seconds of whole-host sampling
must show `<=15%` busy before an invocation, and measured external busy during
the invocation must be `<=10%` of wall capacity across 32 logical processors.
Rejected attempts are retained but excluded and repeated.

M130's repeated Rust test and byte-freeze work overlapped the early campaign.
That overlap cannot change the TIFF hashes and cannot manufacture an
above-threshold private-byte observation. It could change wall time, but the
only M12 bar that consumes wall time is the separate N=96–99 modulo arm, which
had not started during the disclosed overlap. N=33 wall times are provenance,
not inputs to that bar. Every loaded N=33 attempt was retained as rejected and
excluded; the accepted memory and determinism observations remain admissible.

**VERIFIED:** the final Job Object campaign started on one accepted five-second
sample at `4.1177071%` whole-host busy, with zero rejected preload samples.
Across the retained formal log there are 171 records: 74 accepted and 97
rejected for host load, with zero invalid process outputs. The largest accepted
external-busy fraction is `9.9119748%`; the smallest rejected fraction is
`10.0263334%`. The separation straddles the registered 10% gate rather than
silently admitting loaded attempts.

Before any scored repetition, the first monitor implementation was retired. It
enumerated every host process at each 10 ms sample; even after a separate wait
established six consecutive quiet samples (the last was `7.2190103%` busy with
no named contender), all sixteen N=33/W4 attempts exceeded the during-run gate
(`10.0459982%` to `34.2970027%`). A proposed 100 ms process-discovery revision
was commissioned but rejected before the matrix because it did not satisfy the
registration's explicit 10 ms whole-tree cadence. The final implementation
places the target and descendants in a Windows Job Object, queries membership
and private bytes every 10 ms, and avoids scanning unrelated host processes.
The memory controls and smoke were recommissioned after that change. The full
history is in `monitor-amendment.json`; the retired records are diagnostic only
and contain zero scored repetitions.

The formal Job Object campaign was paused after 23 consecutive valid
N=105/W4 warm-up outputs were rejected by the during-run load gate (minimum
observed external busy `10.1291174%`, threshold `10%`). No rejected attempt is
eligible for a scored position. A two-hour operational wait for six consecutive
five-second samples at or below 3% never completed: its 113 samples ranged from
`4.1365877%` to `61.7045126%` while concurrent Python/agent work remained
visible. After those Python workloads ended, a second six-sample wait at 5%
also remained incomplete. The r6 resume trigger was one five-second
sample at or below 5%, immediately followed by the unchanged registered
15%-preload/10%-during-run gates so the clean window was not lost. The three
wait records are retained as `resume-wait-r4.json`, `resume-wait-r5.json`, and
`resume-wait-r6.json`.

The clean r6/r8 windows completed all scored N=33 and N=105 cells. Progress
stopped again at N=299/W16: fourteen consecutive valid warm-ups were rejected
(`10.113%` minimum external busy). The subsequent r9 wait took 136 five-second
samples without finding one sample at or below 2%; observed busy ranged from
`5.7221268%` to `95.3697247%`. During pauses I found and stopped, by exact PID,
a cancelled lane's recursive ExifTool scan and two stale M130 byte-freeze
process trees whose start times were more than six hours old. This was not an
inference from silence: their command lines still named the recursive scan and
the byte-freeze test, and live `strehl.exe` children were consuming the host.

The final retained end sample was `16.2255786%` busy, dominated by
`copilot.exe`, so the promised exclusive timing window did not exist at
closeout. No N=96–99 modulo invocation ever started. Therefore no formal
timing-derived M12 number was contaminated; there is no timing result to repair
or adjust. N=33/N=105 wall times are retained as provenance only and do not
enter an M12 timing bar. The accepted hashes are protected by direct byte
hashing, and the memory failure is protected by both 10 ms samples and the
independent Windows Job Object peak. No core pinning or timing correction was
used.

Cheap read-only probes should also stop during a future timing arm. They are
unlikely to cross the CPU gate alone, but recursive enumeration or reads can
change filesystem-cache and I/O state without leaving an obvious signature in
the target's wall time. The probes did not contaminate M12 here because the
timing arm never began.

## 3. Instrument commissioning

All values below are **VERIFIED** in this session.

### Process-tree memory

- Null: a 64 MiB child allocation produced peak private committed bytes of
  `80,920,576`, stayed below 1 GiB, and the monitor observed both parent and
  child.
- Positive plant: a 7 GiB child allocation produced peak private committed
  bytes of `7,544,352,768` (kernel job peak `7,544,406,016`), exceeded the
  6 GiB bar, and the 10 ms Job Object monitor observed both processes.
- Artifact:
  `experiments/m12-scorecard/out/campaign-8009447e-m139/memory-commission.json`.

### Byte determinism

- Null: rebuilding after restoring the isolated archived source reproduced the
  baseline whole-TIFF hash
  `790570CF966ADDF883D1E1BF8CE093A0978676540EAB447D3CFA159A5EE8B8CC`
  and the baseline pixel hash exactly.
- Positive algorithm plant: changing the archived
  `significance_scale_default()` unset arm from `0.0` to `1.0` changed both
  whole-TIFF and pixel hashes.
- Positive checker plant: flipping one output LSB changed the whole-TIFF hash
  to
  `15098E47164E77BC1C70D7E2F373631B74537DB999CADCE72E3C9AE250190061`.
- Artifact:
  `experiments/m12-scorecard/out/campaign-8009447e-m139/determinism-commission.json`.

### End-to-end smoke

The N=3, worker=1 diagnostic smoke completed one warm-up and two repeats through
RAW decode, registration, pyramid merge, full-resolution linear-sRGB TIFF
write, process-tree monitoring, and hashing. Both repeats had whole-TIFF hash
`0D1CC91E7715B2723193B7B70EC2E43CB3990C6EA8290C9EAE8FF469DA4875D4`
and pixel hash
`1E8DB3888022EE7A4CC55C0966E30264C860068A5CBCE2E8E520774CF60F5AFD`.
Artifact:
`experiments/m12-scorecard/out/campaign-8009447e-m139/smoke.json`.

## 4. Scored result

All values in this section are **VERIFIED** and come from accepted records in
`records.jsonl`. `Peak GiB` is the larger Windows Job Object peak for each
scored cell. `Hashes` reports distinct whole-TIFF/pixel hashes.

| N | workers | accepted scored | hashes | peak GiB | cell memory |
|---:|---:|---:|---:|---:|:---|
| 33 | 1 | 6 | 1 / 1 | 2.2463 | PASS |
| 33 | 2 | 6 | 1 / 1 | 4.4747 | PASS |
| 33 | 4 | 6 | 1 / 1 | 8.9312 | **FAIL** |
| 33 | 8 | 6 | 1 / 1 | 15.6115 | **FAIL** |
| 33 | 16 | 6 | 1 / 1 | 24.3967 | **FAIL** |
| 105 | 1 | 6 | 1 / 1 | 2.2461 | PASS |
| 105 | 2 | 6 | 1 / 1 | 4.4758 | PASS |
| 105 | 4 | 6 | 1 / 1 | 8.9329 | **FAIL** |
| 105 | 8 | 6 | 1 / 1 | 17.8372 | **FAIL** |
| 105 | 16 | 6 | 1 / 1 | 33.4283 | **FAIL** |
| 299 | 1 | 0 | — | — | UNMEASURED |
| 299 | 2 | 0 | — | — | UNMEASURED |
| 299 | 4 | 0 | — | — | UNMEASURED |
| 299 | 8 | 0 | — | — | UNMEASURED |
| 299 | 16 | 0 | — | — | UNMEASURED |

N=299 warm-ups were accepted for workers 1/2/4/8, but warm-ups are not scored
observations and are therefore excluded from the table's memory values.

- **Absolute memory: FAIL.** The bar is 6 GiB. The strongest accepted scored
  observation was `scored:N105:W16:R2`: sampled private commit
  `32.6777 GiB`, Job Object peak `33.4283 GiB`, accepted external busy
  `9.8763%`. Missing samples can understate a peak, not manufacture one above
  the ceiling.
- **Fixed-worker determinism:** every completed N=33 and N=105 cell produced
  one TIFF hash and one pixel hash across six runs. The full-matrix M12-D
  verdict remains UNMEASURED because N=299 was not scored.
- **Cross-worker scaling invariance: FAIL.** N=33 has five distinct TIFF hashes
  and five distinct pixel hashes across workers 1/2/4/8/16; N=105 independently
  has five of each. Both N values have all six accepted repeats in every worker
  cell.
- **Peak-N299/peak-N33 ratio:** UNMEASURED; no N=299 scored cell completed.
- **N-mod-4 spread:** UNMEASURED; no N=96/97/98/99 run started.
- **Sampling quality:** minimum scored-run coverage was `79.5768%`, below the
  execution preregistration's 90% affirmative-result rule; maximum gap was
  `60.8583 ms`, below its 100 ms limit. This prevents a positive full-matrix
  memory claim. It does not weaken the negative result, because both the
  sampled lower bound and the independent kernel peak exceed 6 GiB by multiples.

**Formal M12 verdict: FAIL.** M12 is conjunctive. Either verified hard failure
is sufficient, and absent N=299/modulo/M11 results cannot reverse it. The
registered descriptive campaign is explicitly incomplete and must not be
reported as a completed sweep. `closeout.json` records both facts.

## 5. Read-only input guarantee

A `Get-ChildItem -Force -Recurse` metadata snapshot was taken before input
hashing or rendering and repeated after closeout. Both protected trees are
unchanged:

- `D:\personal\macro`: 10,806 items, 10,724 files, 487,169,829,957 bytes,
  metadata SHA-256
  `46CD6FE5C018AE4ACEC946170EEEC760DBF5B0C8954CA561368F92B9184A5C42`.
- `D:\edited\macro`: 392 items, 387 files, 141,333,902,406 bytes, metadata
  SHA-256
  `40003B9F15D0AE552AD2947E22C29122664E0BDCD7E690D53FE02341DCA12FD1`.

## 6. Could not determine

1. The full N=299 scored matrix.
2. The registered peak-N299/peak-N33 memory ratio.
3. The N=96/97/98/99 modulo timing spread.
4. The joint M11 requirement.
5. Complete process-tree read/write byte counters; the instrument records CPU,
   page faults, output/temp bytes, and memory, but not complete I/O byte totals.
6. Exact causal attribution of every external-CPU interval to another lane.
7. Exact UTC stop times for stale processes terminated during pauses.

## 7. Artifacts

All campaign artifacts pin measured commit
`8009447e059febb8f9c59fda509f141835d6abdb` and live under
`experiments/m12-scorecard/out/campaign-8009447e-m139/`.

- `RUN-MANIFEST.json` — frozen binary, harness, flags, inputs and host gates.
- `records.jsonl` — append-only per-attempt evidence, including rejected runs.
- `closeout.json` — authoritative machine-readable partial-campaign result and
  formal FAIL rationale.
- `summary.json` — mechanical partial summary; its nonzero generation status
  records that the registered sweep is incomplete.
- `memory-commission.json`, `determinism-commission.json`, `smoke.json` —
  bidirectional commissioning and end-to-end smoke.
- `monitor-amendment.json` — observer revisions and zero-scored-run boundary.
- `resume-wait-r3.json` through `resume-wait-r9.json` — host waits.
- `host-start.json`, `host-end.json` — measured boundary conditions.
- `read-only-before.json`, `read-only-after.json` — protected-tree proof.
- `audit.json` — integrity PASS: no commit mismatches, all commissioning gates
  green, all 171 records pinned to the measured commit, protected trees
  unchanged.
