# M153 - M11 two-arm timing harness

## Verdict

**YES: the operative M11 computation is buildable, and the instrument is
built. M11 itself remains UNMEASURED.** No capture timing was run.

The implementation is bound to scorecard v1.10 at SHA-256
`D72160F57494ED1B3A07807EA0D7D6451B5E50D4630E0E6EEB093CED7D74CB28`.
The final build audit passes, `real_run_authorized` remains `false`, and the
scorecard-required one-second commissioning plant was deliberately not run
while M139 owns the host.

### Scorecard defect and exact target

Scorecard v1.10 contains no M11 paragraph labelled `**Success.**`; therefore
there is no verbatim M11 Success clause to quote. This is a specification
defect, not something M153 silently repaired. The operative comparative bar,
quoted verbatim, is:

> The fastest-mode tie is product ID then mode ID. Strehl must have `R_c>=2.00` for each
> of `C33`, `C105`, and `C299`, and `R_pool>=2.00`. The per-capture envelope is
> intentional: no slow capture or favourable global mode can hide a miss.

The immediately preceding scorecard text defines:

- `S_c`: Strehl's minimum valid 16-worker common-merge wall time;
- `T_mc`: quality-qualified comparator mode `m`'s minimum valid wall time;
- `T_c=min_m T_mc`;
- `R_c=T_c/S_c`; and
- `R_pool=sum_c(T_c)/sum_c(S_c)`.

M153 computes exactly those quantities. It does not substitute native-RAW
timing, a merge-kernel time, an average, or a favourable global mode. Equal
comparator minima tie by product ID and then mode ID.

M11's publication verdict also retains the M12 cross-worker anti-cheat
component: at each N, canonical common-merge TIFF and decoded-pixel hashes
must each be identical across workers 1/2/4/8/16. Product-native CPU, hybrid,
baseline, cold, and live values are separately reported disclosures and
cannot rescue or fail the common-merge publication verdict.

## Holdout ruling and input census

The governing rule was recorded before any capture access:

> The holdout unit is **subject plus uninterrupted capture session**, not a directory or
> step width. Rendering, tuning, or reading an outcome on any member burns every member
> of that unit.

- `D:\personal\macro\bee-1-cpl` is a registered performance **HOLDOUT**.
- `D:\personal\macro\coffee-bean` is a fixed historical benchmark and
  **NOT HOLDOUT**.
- Development used no capture. The only access was a read-only metadata
  census; no RAW was decoded and no output, metric, or visual result was read.
- Nothing was written, moved, renamed, or deleted under
  `D:\personal\macro` or `D:\edited\macro`.

The fresh metadata-only census found:

| Stack | Verified source | ARWs | Range | Missing / unexpected | ARW bytes |
|---|---|---:|---|---:|---:|
| `bee-1-cpl` | `D:\personal\macro\bee-1-cpl` | 299 | `DSC00001.ARW`-`DSC00299.ARW` | 0 / 0 | 11,328,233,472 |
| `coffee-bean` | `D:\personal\macro\coffee-bean` | 105 | `DSC00016.ARW`-`DSC00120.ARW` | 0 / 0 | 4,161,077,248 |

Before/after directory snapshots match. Machine-readable evidence is in
`experiments/M153-m11-harness/out/input-census.json`.

## Instrument design

### Common-merge comparative arm

Every program receives the same ordered, byte-identified, uncompressed 16-bit
linear ProPhoto RGB D50 TIFFs from the same volume, at the same native
dimensions, ICC, crop, output contract, cache class, sweep position, host, and
power plan. The only changed factor is the program plus its frozen mode.

The arm times Strehl common-input mode at workers 1/2/4/8/16 and all admitted
comparator modes. Licensed Zerene PMax, licensed Zerene DMap, and the fresh
best-known-source fork are mandatory. Helicon A/B/C must each be declared
available or unavailable with a reason; every obtainable mode enters the
quality envelope. A missing or quality-failed mandatory mode makes the
campaign unmeasured.

After one unscored warm-up, each setting has six scored repetitions in
alternating forward/reverse sweeps. The score uses each mode's minimum, while
the artifact retains all observations, median, maximum, range, MAD, scaled
MAD, sample standard deviation, and relative range. A missing or invalid
member invalidates the campaign; no selective rerun or outlier deletion is
allowed.

### Product-native disclosure arm

This arm starts from byte-identified owned copies of the original ARWs and
times the complete shipping path: decode, registration, fold, colour, write,
descendants, close, validation, and hashing. It separately measures:

- candidate CPU at 16 workers;
- one frozen candidate hybrid mode;
- one frozen default-baseline build;
- six actual-reboot cold/warm pairs per N and product mode; and
- six signed 100-frame live replays after one warm-up.

Ordered ARW bytes, dimensions, output contract, host, power plan, cache class,
non-acceleration settings, and sweep positions are held fixed. Candidate
versus baseline may differ only by build hash. CPU versus hybrid may differ
only by the registered acceleration mode. Any additional changed factor is a
declared confound and is rejected.

This arm reports the scorecard's CPU, hybrid, baseline, cold, and live
disclosures. Its values never enter `T_c`, `S_c`, `R_c`, or `R_pool`.

### Quality qualification

The quality criterion is scorecard-defined, not invented by M153. It is bound
as `scorecard-v1.10-m11-quality-corpus-and-timed-output-v1` and comes from the
scorecard's common-input transfer/geometry contract, M1, M2, M3, M8, retained
M4 flat-power-plus-transfer component, and M11 comparator qualification text.

For Strehl W16 and every mandatory comparator, one frozen
binary/executable-bundle/settings fingerprint must pass that criterion on
hash-bound quality-corpus outputs for all three cells. Every timed output must
also pass its applicable controls. A required mode that is merely present but
quality-failed cannot be dropped to improve the speed envelope; the quality
manifest becomes `UNMEASURED`.

The approved checker-bundle allowlists are intentionally empty. The shipped
quality template therefore returns `UNMEASURED`, as expected. No speed can be
credited until the owner binds commissioned checker bundles and real evidence.

## Timing boundary, controls, and failure durability

For each ordinary invocation:

1. Frozen input and executable artifacts are hash-verified and locked before
   timing. Cold preflight uses Windows unbuffered reads.
2. Integer QPC begins immediately before suspended root-process creation.
3. The root is assigned to a kill-on-close Windows Job Object before resume.
4. The whole process tree is sampled nominally every 10 ms. The initial
   QPC-to-root-sample gap is included. Every observed process image must match
   a preverified member of the locked executable bundle; executable contents
   are not reread inside the timed boundary.
5. Timing stops only after the Job Object reaches zero live processes, the
   final TIFF is flushed/reopened/structurally validated/hashed, and the
   invocation manifest is flushed/closed/hashed.

Records retain raw QPC ticks and frequency, process-tree CPU and memory, I/O,
page faults, stage banners, process lifetimes, output hashes, and the complete
campaign/authorization/artifact identity.

Formal campaigns also require:

- a fixed power plan and dedicated host;
- a hash-bound persistent hardware probe;
- a 60-second preflight with CPU busy `<=0.15`;
- during-run external busy `<=0.10`, computed without subtracting observer
  CPU;
- nominal 10 ms CPU, thermal, throttle, GPU-process, and process-tree samples;
- no missing interval, no throttle flag, and no unapproved GPU process;
- a campaign-predeclared start-temperature interval;
- input hashes before and after every invocation; and
- one warm-up plus six complete alternating scored sweeps.

A campaign-hash-keyed append-only attempt ledger freezes one records path and
chains before/after record hashes and counts. `STARTED` without `COMPLETED`, or
any `ABORTED` attempt, permanently invalidates that campaign. This prevents
discarding a failed attempt and rerunning into a preferred record file.

Cold cells require six distinct actual Windows BootIds, with cold before its
warm mate. Live replay requires a commissioned signed acquisition trace,
prestarts the stacker, holds future source files under exclusive read locks,
atomically hard-links each verified frame into a private spool only at its
availability offset, then releases that frame's lock. The scoring epoch is
frame-100 shutter close, and the live statistic is the maximum of six scored
latencies.

These controls do not eliminate ambient-temperature drift, scheduler and
interrupt noise, firmware boost behaviour, vendor-internal concurrency, or
observer overhead. They freeze or measure exposed conditions, reject known
violations, and preserve dispersion instead of treating residual variation as
an effect.

## Synthetic commissioning

This commissioning used only a generated 4x4 uint16 TIFF and trivial Python
workloads. It is instrument evidence, not an M11 timing result. Every
invocation completed in less than one second.

### Flat null

The two arms were identical except for necessary per-run output paths. Across
six paired scored sweeps:

- estimated `B-A`: **0.003762750 s**;
- paired 95% interval: **[-0.003273978, 0.010799478] s**;
- arm A range / sample SD: **0.0901231-0.1067594 s /
  0.005628284 s**;
- arm B range / sample SD: **0.1026105-0.1131417 s /
  0.004152118 s**; and
- decision: **NO_DETECTED_DIFFERENCE / PASS** because the interval covers
  zero.

### Planted effect

The arms were identical except that arm B received a registered
**0.080000 s** in-boundary sleep. Across six paired scored sweeps:

- recovered `B-A`: **0.081845017 s**;
- paired 95% interval: **[0.079610273, 0.084079761] s**;
- recovery error: **+0.001845017 s**;
- arm A range / sample SD: **0.1003970-0.1049759 s /
  0.001743098 s**;
- arm B range / sample SD: **0.1830725-0.1888803 s /
  0.002183529 s**; and
- decision: **PASS** with the correct sign, the plant inside the interval,
  and zero excluded.

The asynchronous-child control also passed: two processes were observed, and
the timer remained open **0.1182856 s** after root exit until tree drain and
finalization.

The scorecard's separate `1.000+/-0.050 s` formal plant is implemented but
**NOT RUN** under the host-contention prohibition. A development commission
cannot authorize a real campaign.

## Checks and mutation coverage

These are separate results:

- ordinary unit/integration checks: **105/105 PASS**;
- substantive guard mutations: **20/20 killed**, each through its uniquely
  anchored, specifically named test; and
- inert mutation: **1/1 survived** with the suite green.

Every mutation anchor is a unique exact full line, and the commissioner
hard-errors unless it occurs exactly once. The final source-bound build audit
is **PASS**. An independent `gpt-5.6-sol` verifier reran all 105 tests, Ruff
lint, and formatting and returned **CLEAN**.

Machine-readable evidence:

- `out/commission/commission.json`
- `out/commission/mutation-commission.json`
- `out/commission/quality-unbound-check.json`
- `out/commission/audit.json`
- `out/input-census.json`

## Explicitly unbound development choices

These are not measured M11 quantities:

1. **UNBOUND DEVELOPMENT CHOICE:** development commissioning uses a two-sided
   paired-mean t interval. M11 does not prescribe an interval estimator.
2. **UNBOUND DEVELOPMENT CHOICE:** the sub-second development plant is
   0.080000 s with a +/-0.05 s acceptance tolerance. It does not replace the
   scorecard's formal one-second control.
3. **UNBOUND DEVELOPMENT CHOICE:** nominal 10 ms telemetry permits at most a
   15 ms edge or adjacent-sample gap. The scorecard demands 10 ms sampling and
   rejects missing samples but does not specify scheduler tolerance.
4. **UNBOUND DEVELOPMENT CHOICE:** every timed Strehl W16/comparator
   repetition must exactly match the qualified whole-output and decoded-pixel
   hashes. This is stricter than merely rerunning applicable controls.
5. **UNBOUND DEVELOPMENT CHOICE:** live availability is enforced with a fresh
   same-volume spool, exclusive source locks, atomic hard links, and strict
   rejection of source-directory arguments. The signed trace supplies the
   measured shutter/file times, but these enforcement mechanics are M153's.
6. **UNBOUND CAMPAIGN INPUTS:** the exact thermal interval, probe bundles,
   power-plan identity, signed acquisition trace, commercial binaries,
   fresh-fork build, candidate/hybrid/baseline builds, and their settings
   still require owner binding.

## M11 and M12 readiness

The instrument removes M11's missing-instrument blocker, but no formal M11
score exists. Before measurement it still needs:

1. M139 host release and a quiet dedicated host;
2. owner-approved quality, adapter-identity, native-dimension, and
   acquisition-trace checker bundles;
3. frozen common TIFFs plus adapter identity;
4. qualified PMax, DMap, fresh fork, Strehl W16, and every obtainable Helicon
   mode;
5. frozen product CPU/hybrid/baseline settings and signed live trace;
6. the formal one-second commission; and
7. a hash-bound real-run authorization.

M12 is no longer structurally forced to fail for lack of an M11 instrument.
The `m12-bridge` and `m12-join` paths recompute M11 and accept only the exact
worker-16 settings, records hash, and six output/pixel hash vectors from a
passing campaign. Today, however, M12 remains **UNMEASURED**, not PASS: it
still needs the joint M11 PASS and common-merge 1/2/4/8/16 canonical identity,
plus its native-product peak-memory, fixed-worker six-repeat determinism,
N=33/105/299 scaling, and N=96-99 modulo campaign.

## Defect reported to the orchestrator

No orchestrator-owned file was edited. The concrete defect is that scorecard
v1.10 calls M11 well-defined but contains no M11 `**Success.**` paragraph.
M153 records `success_clause_verbatim: null` and binds the quoted operative
comparative bar instead. The lane brief's cited line numbers are also stale
after scorecard growth; the controlling text was reread by content and hash.
