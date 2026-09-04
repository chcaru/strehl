# M153 - M11 two-arm timing harness

## 2026-09-04 host-contention quarantine and withdrawal

There is no exclusive host lock. The standing program policy permits
deterministic correctness work but quarantines absolute timing until the
instrument itself records a window inside its objective load gates. Three
program-level samples observed `88.6%`, `97.0%`, and `94.1%` whole-host CPU
busy, mean `93.2%`, with the agent host process the leading consumer. That
environment cannot support an admissible M11 absolute wall-clock result.

The earlier M153 development observations did not record background load
alongside their timings. They are absolute wall times, not simultaneous-arm
ratios, and their windows cannot be shown clear of the disclosed 4.1-second
host perturbation. They are preserved below for provenance as
`MEASURED_CONTENDED_WITHDRAWN`, not as valid commissioning or performance
evidence. No formal control or real M11 campaign was run, so no admissible
work must be repeated; the withdrawn development observations would have to be
remeasured before any use. M153 has measured **no admissible M11 product or
comparator number**.

The functional check and mutation counts remain code-behaviour evidence, not
wall-clock evidence. They must not be cited to rehabilitate the withdrawn
timings.

## Verdict

**YES: the M11 instrument remains worth finishing and its operative
computation is buildable. The current M11 common-merge verdict is
`UNMEASURED_COMPARATOR_QUALIFICATION`, not PASS or FAIL.** The harness is
reusable after M1 and comparator availability are repaired; abandoning it
would preserve those blockers and recreate the missing-instrument blocker.
The product-native unit is separately `QUARANTINED_HOST_LOAD`. No capture
timing was run.

The working implementation now separates comparative and product campaign
units, hard-stops unlicensed commercial execution, and implements formal null,
one-second slowdown, one-second speedup, and bidirectional ratio controls.
Those timing controls are implemented but `NOT_RUN_QUARANTINED_HOST_LOAD`.
The `commission` command itself fails closed while the frozen contract's
absolute-timing status is not `ADJUDICABLE`.

The implementation is bound to scorecard v1.10 at SHA-256
`EB5ED446EE06E8842C61E5F90CB1BD4A8E81CA5DFD39EF53988598EF05DCB603`.
The last generated build audit predates these changes and is stale;
`real_run_authorized` remains `false`.

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

### Licence-separated units

The orchestrator has verified that the installed Zerene Stacker is an expired,
consumed trial whose licence prohibits post-trial use and circumvention.
Helicon Focus is not installed. M153 will not launch either product.

- **Unit 1 - product-native:** independent Strehl-only measurement of CPU-16,
  optional hybrid, cold-minus-warm, live first-100, and
  candidate/default-baseline bars. Comparator qualification or availability
  does not gate this unit. An absent hybrid remains
  `UNMEASURED_NOT_IMPLEMENTED`.
- **Unit 2 - comparative:** complete but not run against commercial software.
  Until M1 is admitted and the required licensed arms exist, it is
  `UNMEASURED_COMPARATOR_QUALIFICATION`. Its commissioning target is an
  M153-owned synthetic fixed-delay comparator. No synthetic result may be
  represented as a commercial-comparator result.

`enabled_units` makes the split operational: product validation and execution
do not load comparative settings or quality evidence; comparative validation
does not require a product baseline. A segment whose unit is not enabled is
rejected. A combined campaign still requires one candidate executable bundle
across every enabled Strehl role.

Commercial mode IDs are rejected during campaign validation and again before
executable-artifact access, regardless of their declared role. This prevents a
prohibited Zerene or Helicon binary from bypassing the licence gate through
role mislabelling. A future owner-authorized contract must both admit the mode
and retain its comparator role.

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

M1 is withdrawn with no admitted bar, and the approved checker-bundle
allowlists are intentionally empty. The shipped quality template therefore
returns `UNADJUDICABLE_WITHDRAWN_M1`, as expected. No speed can be credited
until M1 is repaired and the owner binds commissioned checker bundles and real
evidence.

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

- a fixed power plan and objective recorded load gates;
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

## Preregistered contention policy

No lane assertion, queue position, or claimed host lease is evidence of
quietness. A scored invocation is admissible only if it passes every frozen,
instrument-recorded condition gate:

1. fixed power-plan identity and campaign-declared start-temperature interval;
2. a continuous 60-second preflight with scorecard CPU busy `<=0.15`;
3. during-run external busy `<=0.10`, computed as total non-idle CPU less Job
   Object CPU, without subtracting observer CPU;
4. nominal 10 ms CPU, thermal, throttle, GPU-process, and process-tree
   telemetry, with zero missing intervals and no edge/adjacent gap above the
   preregistered 15 ms scheduler tolerance;
5. no throttle flag and no GPU process outside the OS-display plus timed-job
   allowlist;
6. frozen input and executable hashes before and after use; and
7. a complete warm-up plus six alternating-order scored repetitions.

Any miss invalidates the whole campaign. The append-only attempt ledger records
`STARTED`, `COMPLETED`, and `ABORTED` attempts and forbids selective reruns,
record-path changes, truncation, and outlier deletion. A quiet-looking minimum
cannot rescue a campaign whose load telemetry fails or is missing.

The headline is the **minimum of six valid repetitions**, exactly as the
scorecard specifies, not their mean. Contention adds non-negative delay, so a
mean is biased slow and is not the score. The minimum is less sensitive to
residual additive delay, but it is not a contamination correction: all six
members must first pass the condition gates. Median, range, MAD, scaled MAD,
sample standard deviation, and relative range remain mandatory diagnostics.
Alternating forward/reverse order limits monotonic thermal and background-load
drift between settings.

While the contract remains quarantined, `summarize` emits only explicit
`UNMEASURED` adjudication records and non-timing provenance; it removes group
dispersion, wall times, seconds-per-frame values, and pre-adjudication PASS/FAIL
results. A nonempty quarantined input is tagged `QUARANTINED`, never
`MEASURED`.

## Preregistered three-way commissioning

No item in this section will run while absolute timing is quarantined. Each
control uses one warm-up followed by six alternating-order scored pairs and
reports the minimum, every observation, dispersion, paired delta, and
interval.

1. **Movable flat null:** both arms execute the same one-frame synthetic
   shipping-path stand-in with identical executable, input, settings, output
   contract, and in-boundary work. Necessary output paths differ. The paired
   interval for `B-A` must cover zero. The exact same arm-selection and timing
   path is used by the two directional plants; the null is not a hard-coded
   zero.
2. **Planted slowdown:** arm B adds exactly 1.000 seconds inside the timed
   one-frame workload. Measured per-frame `B-A` must be
   `+1.000 +/- 0.050 s`, with positive sign and an interval excluding zero.
3. **Planted speedup:** start from the delayed arm and remove exactly 1.000
   seconds only from the declared improved arm. Measured per-frame
   `improved-baseline` must be `-1.000 +/- 0.050 s`, with negative sign and an
   interval excluding zero. This rejects sign inversion or a reducer that
   systematically flatters the candidate.

Unit 2 additionally uses an M153-owned fixed-delay comparator to exercise the
actual aggregate reducer twice: a preregistered fixture in which every
`R_c` and `R_pool` exceeds 2.00 must pass, and the reversed timing fixture must
fail. Required licensed-product identifiers are never attached to these
synthetic records.

## Measurements collected so far

| Quantity | Recorded value | Status |
|---|---:|---|
| M11 product-native bars | none | `QUARANTINED_HOST_LOAD` |
| M11 common-merge comparator ratio | none | `UNMEASURED_COMPARATOR_QUALIFICATION` |
| Development flat-null `B-A` | `0.003762750 s`, 95% interval `[-0.003273978, 0.010799478] s` | `MEASURED_CONTENDED_WITHDRAWN` |
| Development 0.080 s plant `B-A` | `0.081845017 s`, 95% interval `[0.079610273, 0.084079761] s` | `MEASURED_CONTENDED_WITHDRAWN`; also not the required 1 s plant |
| Development async root-exit-to-drain tail | `0.1182856 s` | `MEASURED_CONTENDED_WITHDRAWN` |
| Formal movable-null control | none | `NOT_RUN_QUARANTINED_HOST_LOAD` |
| Formal 1.000 s slowdown control | none | `NOT_RUN_QUARANTINED_HOST_LOAD` |
| Formal 1.000 s speedup control | none | `NOT_RUN_QUARANTINED_HOST_LOAD` |
| Formal bidirectional ratio control | none | `NOT_RUN_QUARANTINED_HOST_LOAD` |
| Metadata-only capture census | bee 299 ARWs; coffee 105 ARWs | `MEASURED_NON_TIMING`; retained |

The withdrawn development artifacts remain on disk as an audit trail. Their
old `PASS` field means only that they met the then-current development
predicate; it is superseded by this contention finding and cannot authorize a
campaign or support a performance claim.

## Checks and mutation coverage

The committed pre-pivot baseline had these separate results:

- ordinary unit/integration checks: **105/105 PASS**;
- substantive guard mutations: **20/20 killed**, each through its uniquely
  anchored, specifically named test; and
- inert mutation: **1/1 survived** with the suite green.

Every mutation anchor was a unique exact full line, and the commissioner
hard-errors unless it occurs exactly once. The source-bound build audit was
**PASS** for that committed baseline. An independent `gpt-5.6-sol` verifier
reran all 105 tests, Ruff lint, and formatting and returned **CLEAN**.

For the current source, these remain separate results:

- ordinary unit/integration suite: **113 checks reported; 112 PASS and 1
  explicitly `QUARANTINED_HOST_LOAD` process-timing integration skipped**;
- substantive guard mutations: **20/20 killed**;
- substantive runtime-policy mutations: **12/12 killed**;
- all substantive mutations: **32/32 killed**, each through its specifically
  named check; and
- inert mutation: **1/1 survived** with the guard suite green.

The current mutation artifact binds the exact `m11_core.py`, `m11_harness.py`,
mutation commissioner, both test files, and Python executable hashes. These
are functional results only; none validates the withdrawn wall-clock figures.
An independent `gpt-5.6-sol` verifier reran the current 113-test suite and
Ruff, checked every mutation binding/count, and returned **CLEAN**.

Current machine-readable correctness evidence:

- `out/commission/mutation-commission.json`

Historical machine-readable evidence, stale for the current contract/source
and retained only as an audit trail:

- `out/commission/commission.json`
- `out/commission/quality-unbound-check.json`
- `out/commission/audit.json`
- `out/input-census.json` (the metadata census remains factually retained, but
  its old contract binding is stale)

## Explicitly unbound development choices

These are not measured M11 quantities:

1. **UNBOUND DEVELOPMENT CHOICE:** development commissioning uses a two-sided
   paired-mean t interval. M11 does not prescribe an interval estimator.
2. **WITHDRAWN HISTORICAL DEVELOPMENT CHOICE:** the old sub-second development
   plant was 0.080000 s with a +/-0.05 s acceptance tolerance. It does not
   replace the scorecard's formal one-second controls.
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

1. a recorded environment capable of passing the frozen preflight and in-run
   load gates;
2. an admitted M1 bar plus a purchased comparator licence before any
   commercial comparative run;
3. owner-approved quality, adapter-identity, native-dimension, and
   acquisition-trace checker bundles;
4. frozen common TIFFs plus adapter identity;
5. qualified PMax, DMap, fresh fork, Strehl W16, and every obtainable Helicon
   mode;
6. frozen product CPU/hybrid/baseline settings and signed live trace;
7. the formal null, one-second slowdown, one-second speedup, and bidirectional
   ratio commission; and
8. a hash-bound real-run authorization.

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
