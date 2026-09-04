# M138 corrected W1 gate preregistration

Status: **PREREGISTERED BEFORE CORRECTED-GATE OUTCOME GENERATION.**

This is a specification, not a campaign result. No corrected admission arm,
physical detail score, or replacement-gate verdict was generated while writing
it. The first path-scoped commit containing this document,
`corrected-gate-contract.json`, and `adjudicate.py` is the design seal. A
separate lane must review that seal before activation.

I am both the author of the M138 audit and this replacement specification. That
conflict is not waived. The specification is therefore accompanied by pinned
source hashes, explicit source anchors, a machine-readable contract, and a
reference adjudicator. Author self-checks do not count as the required
independent review.

## Evidence tags

- **[VERIFIED]**: read or computed directly in this work.
- **[INHERITED]**: taken from an existing committed source.
- **[VERIFIED—PREREGISTERED]**: fixed here before corrected-gate outcomes; this
  is a design value, not a measurement.
- **[VERIFIED—ESTIMATE]**: calculated scheduling estimate, not measured campaign
  runtime.

A tag on a heading or table applies to every numeric value beneath it. File
line locations, hashes, schema versions, identifiers, and mathematical
subscripts are identifiers rather than quantitative findings.

## Actual goal and chosen approach

The goal is to test whether one globally meaningful admission setting produces
a real output Pareto improvement, not whether it reproduces another
algorithm's internal width.

Two approaches were considered:

1. repair the analytic variance and retain a globally interpreted raw `k`; or
2. calibrate the complete selected-winner gap onto a common null-compatibility
   quantile and expose one global quantile threshold.

The second is specified. The first loses because even a better pairwise
variance does not remove the order statistic induced by choosing the maximum
over the stack. The current core itself records that a fixed threshold against
a maximum is stack-size dependent
(`crates/strehl-core/src/merge.rs:421-427`). End-to-end calibration can include
the exact stack size, winner selection, warp, signal level, and residual
non-Gaussianity without pretending that a pairwise denominator solved them.

What would make this specification wrong is explicit:

- the calibrated coordinate still fails per-stratum null coverage;
- its power does not increase with a known focus separation;
- the physical M135 path cannot produce an eligible certificate;
- the temporal-noise instrument cannot distinguish injected noise from known
  averaging; or
- no global output-quality operating point survives development and sealed
  confirmation.

The first four are instrument failures and leave Phase 1 untested. The last is
a design refutation.

## Existing behavior this specification replaces

The existing candidate chooses a raw-energy maximum and divides each
winner-to-frame gap by the square root of two plug-in variance terms
(`experiments/PHASE1-DESIGN/measure.py:171-180`). Its legacy comparator changes
soft-power exponent by band
(`experiments/PHASE1-DESIGN/measure.py:129-141`). The candidate and legacy
variance fields are ordinary Gaussian pyramids multiplied by scalar transfer
factors (`experiments/PHASE1-DESIGN/measure.py:235-250`); the corresponding
Rust helper explicitly carries variance with the image Gaussian reducer
(`crates/strehl-core/src/pyramid.rs:372-384`).

The old preregistration applied a per-band/per-ROI width predicate, then stated
that only width survivors were rendered
(`experiments/PHASE1-DESIGN/PREREGISTRATION.md:167-203`). The implementation
does exactly that with a conditional render
(`experiments/PHASE1-DESIGN/measure.py:568-575`). The proposal likewise
defines width before the output bars
(`docs/proposals/2026-09-phase1-design.md:312-316`) and maps an empty width
intersection directly to `NO_COMMON_K`
(`docs/proposals/2026-09-phase1-design.md:340-350`).

The current calibration fits coarse-band transfer factors jointly
(`experiments/PHASE1-DESIGN/reference.py:625-633`), records per-frame coverage
but gates on pooled coverage
(`experiments/PHASE1-DESIGN/reference.py:666-727`;
`experiments/PHASE1-DESIGN/reference.py:1052-1064`), and runs its
Poisson–Gaussian exercise through a one-band pyramid
(`experiments/PHASE1-DESIGN/reference.py:1080-1134`).

Those are source facts, not recollections from the audit conversation. The
exact source bytes are pinned in `corrected-gate-contract.json`.

## Corrected gate rule

### Width is diagnostic, never dispositive

`n_eff`, singleton fraction, below-floor fraction, and candidate/legacy width
ratios must still be emitted for every capture, band, ROI, and threshold. They
may diagnose mechanism, unexpected collapse, or product behavior. They do not
remove an arm from rendering, alter a confidence interval, choose the global
threshold, or change a verdict.

This is a demotion, not deletion. The old **[INHERITED] ±5%** comparator-width
condition is retained in the result file as a labelled historical diagnostic.
It has no Boolean field consumed by the adjudicator.

### The globally meaningful coordinate

**[VERIFIED—PREREGISTERED]** For every non-winner frame, retain the observed
energy gap:

```text
D_i = E_w - E_i
```

Do not claim that `D_i / sqrt(sigma2_Ew + sigma2_Ei)` is already pivotal.
Instead, build a calibration distribution from independent equal-focus trials
that execute the complete decision path, including source-level
Poisson–Gaussian draws, affine pull, shared-green construction, variance
stabilisation, every Laplacian band, energy smoothing, and selection of the
winner from the exact stack size.

For the applicable frozen stratum, let `D^(1)...D^(M)` be the calibration
gaps. The non-winner compatibility coordinate is:

```text
u_i = (1 + count(D^(j) <= D_i)) / (M + 1)
```

Equal scores use the conservative upper rank. The winner is admitted
explicitly. The existing below-floor arithmetic-mean fallback remains
unchanged (`experiments/PHASE1-DESIGN/measure.py:407-422`).
Calibration rows for a frame role retain only trials in which that role is not
the winner; generation continues until the registered non-winner count is
reached. Winner observations never enter the non-winner empirical CDF.

Admit a non-winner iff:

```text
u_i <= tau
```

`tau` is the only product operating parameter. Band, exact stack size, frame
warp, sensor-noise mode, signal stratum, and positive-signal stratum are
nuisance coordinates of the frozen calibration bank, not independently
selectable thresholds.

For an implementation that must expose a sigma-like name, the equivalent
interior coordinate is **[VERIFIED—PREREGISTERED]**
`k_cal=Phi_inverse(tau)`. It is a reparameterisation of the same one global
probability threshold, not permission for a per-band or per-capture `k`.
The raw `k` from the withdrawn gate is not retained because its denominator
never established that common probability meaning.

The bank generator is one frozen algorithm. Capture identity is provenance,
not a fitted feature: only predeclared physical nuisance inputs may change its
distribution. No candidate image, quality score, width result, or legacy
comparison may enter calibration. This is standardisation conditional on known
measurement geometry, not a per-capture operating threshold.

### Frozen threshold family — [VERIFIED—PREREGISTERED]

```text
tau = 0.00, 0.01, 0.02, ..., 1.00
```

`tau=0.00` admits only the winner outside the below-floor fallback.
`tau=1.00` admits every finite frame. Every arm is rendered and scored.
There is no width preselection, interpolation, post-outcome extension, or
per-capture/per-band `tau`.

An arm is robustly passing only when it and its immediate
**[VERIFIED—PREREGISTERED] 0.01** neighbors all pass. Thus an isolated grid
point cannot become the product setting. Among robustly passing centers,
select the greatest `tau`, which is the most averaging compatible with every
output-quality bar. The endpoints are controls and cannot be selected as
centers.

## Standardisation repairs

Every listed defect is **blocking**. A failure here returns
`INSTRUMENT_INVALID`; it is not evidence against Phase 1.

### Pooled-only coverage gating — BLOCKING

**Fix.** Validate each frozen stratum separately. A stratum key contains:

- capture-manifest hash;
- band;
- exact stack size;
- candidate frame ordinal;
- sensor gain mode;
- input-only signal quartile; and
- positive-signal anchor.

The pair signal coordinate is
`r=(q_w+q_i)/(F_w+F_i)`. **[VERIFIED—PREREGISTERED]** Assign it without
interpolation to the left-closed bins
`[0,0.25)`, `[0.25,1)`, `[1,4)`, `[4,16)`, and `[16,+infinity)`, represented
by calibration anchors `[0,0.5,2,8,32]`. The calibration generator targets
each anchor, then retains simulated observations by their resulting bin.

The calibration simulation uses every actual frozen affine transform in the
capture manifest. It separates **[VERIFIED—PREREGISTERED] two** sensor gain
modes and **[VERIFIED—PREREGISTERED] four** input-only signal quantiles. A
missing or under-populated key is an instrument failure; it may not be repaired
by pooling with another frame, band, or capture.

**[VERIFIED—PREREGISTERED]** Use `4,095` calibration trials and an independent
`8,192` validation trials per generated calibration cell. One simulated stack
supplies the winner and every frame-role gap for that cell; frame-role
validation does not rerun the stack. At compatibility
checkpoints
`[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]`, every non-winner frame's
empirical admission rate must differ from the checkpoint by no more than
`0.03`. Report the maximum error and the full curve for every key. No pooled
summary can substitute for a failed key.

Synthetic calibration alone is insufficient. The static-repeat physical deck
must also expose at least **[VERIFIED—PREREGISTERED] 256** non-overlapping
support-separated sites in every band/gain/session stratum. At every registered
compatibility checkpoint, a simultaneous
**[VERIFIED—PREREGISTERED] 99%** binomial interval for physical admission must
contain the nominal rate. Bands, gain modes, and sessions are judged
separately; a pooled pass cannot rescue one failed stratum.
Use two-sided Clopper–Pearson intervals with Bonferroni allocation
**[VERIFIED—PREREGISTERED] `alpha_cell=0.01/C`**, where `C` is the complete
pre-output count of physical stratum/checkpoint predicates.

### Positive-`q` commissioning — BLOCKING

**Fix.** Equal-focus trials must contain coherent signal shared by every frame,
not only zero-mean noise. **[VERIFIED—PREREGISTERED]** The frozen
`q/F` anchors are `[0, 0.5, 2, 8, 32]`. Each anchor is generated before fresh
frame noise is drawn and is validated under the same per-stratum coverage rule.

Power is separate from calibration. **[VERIFIED—PREREGISTERED]** Give one
non-winner a true focus deficit of `[0, 1, 2, 4]` unselected standard
deviations while leaving all nuisance variables fixed. Its admission
probability must decrease strictly at each step, with independently bootstrapped
**[VERIFIED—PREREGISTERED] 99%** intervals that do not overlap between adjacent
steps. A statistic with calibrated nulls but no separation power fails.

### All-band Poisson–Gaussian control — BLOCKING

**Fix.** Generate noise before the warp and decision transform, using the
registered sensor model and both sensor gain modes. Run the complete
**[VERIFIED—PREREGISTERED] seven-band** path and report each band separately.
Exercise all **[VERIFIED—PREREGISTERED] four** CFA planes for propagated
variance and shared green for the admission decision. Each input-only signal
quartile and every actual warp lattice must appear in the result ledger.

The current one-band control is not reusable as evidence for the other bands;
its one-band construction is visible at
`experiments/PHASE1-DESIGN/reference.py:1080-1134`.

### Approximate variance propagation — BLOCKING

**Chosen fix.** Remove analytic `sigma2_E` from the load-bearing definition of
the global threshold. The authoritative standardisation is the independently
validated empirical rank of the complete selected gap `D_i`. Because each
calibration draw goes through the actual warp, transform, pyramid, and energy
operator, filter-induced covariance and spatially varying noise are present in
the reference distribution rather than represented by a scalar `beta`.

The existing analytic value may be retained only as
`sigma2_E_approx` in diagnostics. It may not select a calibration stratum or
enter the verdict.

**Advisable, not blocking once the empirical calibration passes:** implement a
fast moment predictor using squared filter coefficients and covariance
propagation, and compare it with the empirical bank. It may replace the bank
only under a new preregistration that meets the same per-stratum calibration
bar. This avoids making an unverified analytic shortcut load-bearing again.

### Selected-winner and stack-size calibration — BLOCKING

**Fix.** Every calibration trial creates all frames for the exact manifest
stack size, runs the same winner tie-break as the candidate, and forms gaps
only after that maximum is selected. Calibration is indexed by exact stack
size; interpolation or reuse from a different `N` is forbidden in this gate.
A new holdout stack size therefore requires its bank to be generated and
sealed before its candidate output is rendered.

Coverage of an arbitrary unselected pair is not an accepted substitute. This
directly addresses the maximum-over-stack behavior documented at
`crates/strehl-core/src/merge.rs:421-427`.

## Output-quality instruments

### Capture roles

The captures already consumed by the withdrawn W1 may be rerendered as
development diagnostics. They may contribute width, singleton, fallback,
finite-value, and hull records, but they cannot manufacture the independent
truth/reference roles required below.

The scored development deck requires a disposable physical M135 rehearsal
family and an independently captured static-repeat family. The scored holdout
requires fresh subject/session families for both roles. Exact paths, frame
counts, and family identities are deliberately not guessed here; they become
binding only through the pre-output capture-ledger amendment. If those inputs
do not exist, the gate is blocked rather than weakened onto the old natural
ROIs.

### Detail: hard dependency on M135

This gate does not invent another detail statistic.

The required provider is the M135 non-compensating truth-referenced
certificate. Its registered estimator consumes two independent reference
realisations and two independent output realisations
(`experiments/M135-detail-instrument/PREREGISTRATION.md:26-53`) and emits an
eligibility status, information, transfer, unexplained-repeatability, and noise
coordinates (`experiments/M135-detail-instrument/instrument.py:152-218`).
Its synthetic battery already specifies both a blur defect and a genuine
optical improvement
(`experiments/M135-detail-instrument/PREREGISTRATION.md:127-149`).

The present M135 preregistration explicitly limits itself to synthetic
estimator commissioning and does not qualify a physical reference path
(`experiments/M135-detail-instrument/PREREGISTRATION.md:7-12`). Therefore this
contract is deliberately `UNBOUND`.

Before any corrected-gate candidate render, an amendment must freeze:

1. the physical M135 preregistration commit and file hash;
2. the physical commissioning artifact and PASS state;
3. the M135 comparison-checker hash;
4. the exact output-quality comparison rule returning `detail_pass`; and
5. the development/holdout capture-family ledger.

That amendment may bind a rule already frozen by M135. It may not invent,
relax, or tune a detail margin from Phase-1 output. Without the binding, the
only verdict is `BLOCKED_DETAIL_INSTRUMENT`. The binding must also revise the
reference adjudicator to recompute `detail_pass` through the bound checker; a
Boolean supplied by a result file is not admissible evidence.

This document deliberately does not transplant the withdrawn
**[INHERITED] `0.95`** cross-power ratio onto `J_TR`, `T_TR`, or `U_TR`.
Those coordinates have different units and failure directions. The physical
M135 lane must derive and freeze its comparison rule from its own
commissioning and power analysis before seeing any Phase-1 candidate output.
That is a dependency, not discretion available after the run
(`experiments/PHASE1-DESIGN/measure.py:29-31`).

The same pre-output amendment must change `capture_ledgers.binding_state` to
`BOUND` and list every development and holdout capture ID under its detail,
noise, and hull roles. The adjudicator requires exact equality with those
lists; a result cannot omit a difficult capture by redefining its own ledger.

### Noise: paired-static-repeat temporal power

**[VERIFIED—PREREGISTERED]** The noise instrument uses two independently
captured static-repeat bursts of the same latent and acquisition settings.
Candidate and legacy each render both bursts from identical inputs. For mode
`m`, site `s`, and CFA plane `c`:

```text
P_m,s,c = 0.5 * mean((Y_m,1 - Y_m,2)^2)
R_s,c   = P_candidate,s,c / P_legacy,s,c
```

The scene cancels in the repeat difference. This measures temporal output
power rather than spatial texture. The arithmetic rationale for a static
burst and its known averaging truth is established independently in
`docs/research/M62-sqrt-n.md:32-45`. That report also states that its physical
real-capture branch was not run
(`docs/research/M62-sqrt-n.md:64-70`), so a new physical repeat deck remains a
required input rather than inherited evidence.

**[VERIFIED—PREREGISTERED]** Each deck must contain at least `64` guarded,
non-overlapping sites. **[INHERITED]** For every capture family and each of
`R`, `G1`, `G2`, and `B`, the paired-site bootstrap
`upper95(P_candidate/P_legacy)` must be `<=0.90`. The value is inherited from
the original output bar, not chosen from corrected outcomes; the old constants
are visible at `experiments/PHASE1-DESIGN/measure.py:29-31`.

Input-only registration, clipping, exposure, frame count, and site eligibility
are frozen before either output. A failed repeat-geometry check returns an
instrument error, never a favorable low-noise value.

### Output integrity

Every arm must also:

- contain only finite outputs and metric inputs;
- use the same linear-DN reconstruction and output pipeline as legacy;
- apply no arm-specific postfilter; and
- remain within **[INHERITED] 1 DN** of the independently recomputed
  aligned-input hull.

These are hard gates, not compensating scores.

## Preregistered pass/fail rule

### Freeze order

1. Commit this specification, contract, and adjudicator.
2. Obtain independent design review.
3. Bind and hash the physically commissioned M135 rule.
4. Freeze standardisation seeds, capture manifests, all transforms, static
   repeat sites, M135 sites, exclusions, decoder versions, and output hashes.
5. Commission standardisation and both output instruments.
6. Render every development `tau` arm.
7. Select and commit the one global `tau`.
8. Open the sealed holdout once and render only legacy plus the selected
   candidate.

No candidate output may exist before step 4. No holdout output may exist before
step 7.

### Development arm

For one `tau`, `OUTPUT_PASS(tau)` is true iff all of these are true on every
applicable development capture:

1. the bound M135 checker returns `detail_pass`;
2. every CFA-plane temporal-power `upper95` is
   **[INHERITED] `<=0.90`**;
3. maximum hull excess is **[INHERITED] `<=1 DN`**;
4. all required values are finite; and
5. candidate and legacy output-pipeline hashes identify the same
   non-postfiltered pipeline.

There is no averaging across captures or criteria. One win cannot compensate
for one loss.

Let `j` index the **[VERIFIED—PREREGISTERED] 101-point** threshold grid.
A robust center is:

```text
ROBUST(j) = OUTPUT_PASS(j-1) and OUTPUT_PASS(j) and OUTPUT_PASS(j+1)
```

Only **[VERIFIED—PREREGISTERED] indices 1 through 99** can be centers.
If at least one robust center exists, select the greatest center and freeze it.

### Holdout arm

The holdout receives only the selected global `tau`; it is not swept. It passes
iff the same `OUTPUT_PASS` rule passes on every sealed holdout capture. A
different threshold, changed site, changed metric, added exclusion, or changed
instrument hash is `INSTRUMENT_INVALID`.

### Deterministic verdict table

| Condition | Verdict | Meaning |
|---|---|---|
| Seal, input, standardisation, or bidirectional commissioning failure | `INSTRUMENT_INVALID` | No Phase-1 inference |
| Physical M135 binding absent or invalid | `BLOCKED_DETAIL_INSTRUMENT` | No Phase-1 inference |
| Instruments valid; no robust development center | `PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT` | Phase-1 candidate family refuted |
| Robust center selected; holdout not yet opened | `AWAITING_HOLDOUT` | No final verdict |
| Selected center fails any holdout output bar | `PHASE1_REFUTED_HOLDOUT` | Phase-1 version refuted |
| Selected center passes every holdout output bar | `PHASE1_GO` | Phase-1 may proceed to integration |

These are the only scientific verdicts. A failure of calibration cannot be
reported as a merge failure.

### What genuinely refutes Phase 1

After every instrument is valid and frozen, either of these results is a
genuine refutation:

1. no three-adjacent-arm interval satisfies all development output-quality
   requirements; or
2. the single selected global threshold fails any sealed holdout
   output-quality requirement.

The refutation is scoped to the frozen implementation, calibration method,
threshold family, and capture ledger. It does not claim a theorem about every
real-valued threshold outside that registered family.

## Why this is not a weaker gate

- The **[INHERITED] `0.90`** temporal-noise power ceiling is unchanged.
- The old synthetic-only detail cross-power check is retired. The gate is
  fail-closed until a physically commissioned truth-referenced certificate is
  bound
  (`experiments/PHASE1-DESIGN/reference.py:1143-1185`).
- One threshold still serves every capture, band, and ROI.
- Every arm is rendered; none is excused by width.
- An isolated pass is rejected by the **[VERIFIED—PREREGISTERED] ±0.01**
  robustness requirement.
- A development pass must survive a separately sealed holdout.
- Winner selection, exact stack size, positive signal, all bands, and
  Poisson–Gaussian noise become blocking calibration requirements.

An average-everything arm can win the temporal-noise coordinate but remains
exposed to M135's detail/transfer veto. A winner-take-all arm can preserve
detail but remains exposed to temporal-noise power. Removing legacy-width
equality removes a comparator-equivalence condition; it does not lower either
output-quality requirement.

## Commissioning in both directions

No instrument or checker may pass with only a degradation plant.

### Standardisation coordinate — [VERIFIED—PREREGISTERED]

- **Null:** equal-focus trials must meet the per-stratum admission error
  `<=0.03`.
- **Defect:** use the wrong stack-size calibration bank and separately omit
  warp-induced correlation; each plant must make at least one registered
  stratum fail.
- **Improvement:** apply the registered selected-winner calibration to those
  same plants. Define calibration score
  `S_cal = 0.03 - maximum_absolute_admission_error`; it must increase relative
  to each defective arm and become nonnegative.
- **Power:** the `[0,1,2,4]` focus-deficit ladder must be strictly ordered.

### Detail coordinate

The bound M135 physical campaign must preserve its own bidirectional contract.
At minimum, pre-noise blur must lower its information coordinate and planted
optical improvement must raise it. The existing estimator preregistration
already makes both mandatory
(`experiments/M135-detail-instrument/PREREGISTRATION.md:127-149`).

### Temporal-noise coordinate — [VERIFIED—PREREGISTERED]

Define `S_noise = -log(P_candidate/P_legacy)`, so higher is better.

- **Null:** identical noise laws and merge laws must bracket zero.
- **Defect:** add fresh independent noise to each candidate repeat;
  `S_noise` must decrease with non-overlapping `99%` intervals.
- **Improvement:** replace each candidate repeat by the mean of two independent
  realizations before differencing; `S_noise` must increase with
  non-overlapping `99%` intervals.
- **Common-scene placebo:** add the same deterministic scene term to both
  repeats; the score must remain inside the null interval.

### Adjudicator

The reference checker must observe:

- a fully passing synthetic result reaching `PHASE1_GO`;
- missing improvement evidence reaching `INSTRUMENT_INVALID`;
- no robust development interval reaching
  `PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT`;
- a holdout bar miss reaching `PHASE1_REFUTED_HOLDOUT`; and
- arbitrary width-diagnostic corruption leaving the verdict unchanged.

`python experiments\M138-w1-gate-audit\adjudicate.py --self-test` performs
those non-campaign controls.

## Result contract

`corrected-gate-contract.json` is normative. A campaign result must contain:

- all source, program, manifest, calibration-bank, M135, and site hashes;
- development and holdout role ledgers exactly matching the bound contract;
- the complete standardisation ledger, including every failed stratum;
- all **[VERIFIED—PREREGISTERED] 101** development arms;
- raw M135 inputs or the independently reproducible certificate payload;
- paired static-repeat site powers for every CFA plane;
- hull and finite-value checks;
- every width diagnostic; and
- the selected threshold and holdout record, if reached.

`adjudicate.py --result <file>` is the reference verdict implementation.
Another implementation is required for independent review; agreement with
this script alone is not independent verification.

## Wall-clock and contention

The frozen old width-only run took **[VERIFIED] 263.6871026 seconds** over
**[VERIFIED] 161 frames** and rendered no Pareto output
(`experiments/PHASE1-DESIGN/results/gate.json:1`;
`experiments/PHASE1-DESIGN/results/run.json:1`).
The authoring host reports **[VERIFIED] 16 physical cores**, **[VERIFIED] 32
logical processors**, and **[VERIFIED] 61.6 GiB** of RAM.

After the physical M135 and static-repeat inputs exist, reserve:

| Work | Exclusive-host estimate |
|---|---:|
| Standardisation bank plus disjoint validation | **[VERIFIED—ESTIMATE] 10 hours** |
| Development rendering and scoring | **[VERIFIED—ESTIMATE] 4 hours** |
| Selected-threshold holdout | **[VERIFIED—ESTIMATE] 2 hours** |
| Total | **[VERIFIED—ESTIMATE] 16 hours** |

On the shared five-lane host, schedule **[VERIFIED—ESTIMATE] 24 wall-hours**,
assuming **[VERIFIED—ESTIMATE] 50%** contention overhead. Reserve
**[VERIFIED—ESTIMATE] 8 CPU threads** and
**[VERIFIED—ESTIMATE] 16 GiB** committed memory. Render no more than
**[VERIFIED—ESTIMATE] 8 thresholds** per batch and discard full images after
site statistics and hashes are durable.

The campaign contends for CPU, memory bandwidth, RAM, and RAW-read bandwidth.
It does not require GPU or network service. Do not co-schedule its calibration
bank or RAW decode phases with another full-resolution experiment or release
build. Physical capture/acquisition time is not included.

## Could not determine

1. Whether M135's physical path will commission or what comparison rule it
   will freeze.
2. Whether the required physical random-code and static-repeat capture
   families already exist.
3. Whether any registered global `tau` will pass.
4. The actual campaign runtime; the cost above is a scheduling estimate based
   on the frozen width-only runtime and the specified workload.
5. Whether the calibration bank is cheap enough for a production
   implementation. This preregistration tests the merge law; product
   acceleration may follow only without changing decisions.
6. Performance outside the registered stack sizes and capture families.

## Source-anchor checklist

The companion checker verifies all of these ranges against the pinned source
hashes:

- `experiments/PHASE1-DESIGN/measure.py:29-31`
- `experiments/PHASE1-DESIGN/measure.py:129-141`
- `experiments/PHASE1-DESIGN/measure.py:171-180`
- `experiments/PHASE1-DESIGN/measure.py:235-250`
- `experiments/PHASE1-DESIGN/measure.py:407-422`
- `experiments/PHASE1-DESIGN/measure.py:568-575`
- `experiments/PHASE1-DESIGN/reference.py:625-633`
- `experiments/PHASE1-DESIGN/reference.py:666-727`
- `experiments/PHASE1-DESIGN/reference.py:1052-1064`
- `experiments/PHASE1-DESIGN/reference.py:1080-1134`
- `experiments/PHASE1-DESIGN/reference.py:1143-1185`
- `crates/strehl-core/src/pyramid.rs:372-384`
- `crates/strehl-core/src/merge.rs:421-427`
- `experiments/M135-detail-instrument/PREREGISTRATION.md:7-12`
- `experiments/M135-detail-instrument/PREREGISTRATION.md:26-53`
- `experiments/M135-detail-instrument/PREREGISTRATION.md:127-149`
- `experiments/M135-detail-instrument/instrument.py:152-218`
- `docs/research/M62-sqrt-n.md:32-45`
- `docs/research/M62-sqrt-n.md:64-70`
- `docs/proposals/2026-09-phase1-design.md:312-316`
- `docs/proposals/2026-09-phase1-design.md:340-350`
- `experiments/PHASE1-DESIGN/PREREGISTRATION.md:167-203`
- `experiments/PHASE1-DESIGN/results/gate.json:1-1`
- `experiments/PHASE1-DESIGN/results/run.json:1-1`
