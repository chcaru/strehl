# M135 — D8 adjudication and a truth-referenced detail instrument

Status: **D8 NO-GO AS M1; REPLACEMENT CONDITIONAL GO TO PHYSICAL
COMMISSIONING; M1 REMAINS UNMEASURED**

## 0. D8-versus-blindness ruling

**VERIFIED — D8 does not survive as the M1 detail instrument.** Of the three
possibilities in the brief, outcome 1 is false, outcome 2 governs D8's
absolute-acuity claim, and outcome 3 describes only a narrower auxiliary use:

| D8 quantity | Ruling | Structural reason |
|---|---|---|
| absolute split cross-power `P_sig` | **Reject as M1** | It responds to blur, but a common output gain `K_k` also multiplies it by `|K_k|^2`; USM can buy the same increase. |
| normalized split `R_SNR` | **Retain only as an auxiliary noise-efficiency coordinate** | At each ideal Fourier cell, common gain cancels from signal and half-difference noise. That blocks noise-only sharpening, but makes common post-render blur equally invisible. |
| split-half FRC crossing/map | **Reject as absolute or “certified” acuity** | The same ideal per-cell cancellation applies to normalized coherence; finite windows add unsigned, implementation-dependent leakage with no distribution-free bound, and shared structure can hold the curve high on a flat. |
| half-difference image | **Retain only as a diagnostic** | It omits common-mode artifacts and can be forced to zero by delivering the average of the two halves. |

The apparent conflict is therefore a conflation of estimands, not a
reproducibility dispute. M115's blur result belongs to **absolute `P_sig`**;
its sharpening result belongs to **normalized `R_SNR`**. No M115 scalar owns
both properties. M115's cited evidence also lacked a data-dependent tuner
plant. SPLIT2 later added one: illegal evaluation-pair leakage drove high-band
FRC to exactly `1.0` and moved an externally protected output by `25.002575`,
so the plant went RED. That commissions a **held-out-tuning guard**, not D8's
self-tuning claim (`docs/research/M-PHASE0-SPLIT2.md`, “Commissioning retained,
real FRC forbidden”).

**VERIFIED.** The four D8 headline quantities reproduce from the preserved
byte-pinned rerun of historical M115 commit `77c8d5e9`: eight blur recoveries
span `0.9938215871-0.9973982082`; the largest normalized-SNR movement is
`0.537785%`; the naive gradient reading is `8.2513657x`; and the reported
power-consistency ratios span `0.999999999987-1.000000000000`
(`experiments/M135-detail-instrument/d8-audit.json:3-39`). The source hashes,
plant locations, and algebra also pass an independent M135 audit
(`experiments/M135-detail-instrument/d8-audit.json:40-132`).

Those accurate numbers do **not** prove D8's conclusion:

- M115 C2 Fourier-blurs every already-realized frame before the split
  (`experiments/M115-deconv-headroom/src/m115lib.py`, the C2 Fourier-blur
  implementation; `experiments/M115-deconv-headroom/src/s03_instrument.py`,
  the C2 challenge block). It then
  reads absolute `P_sig`, which necessarily follows the filter's power. It is
  not a fresh-noise optical-improvement control.
- C3 filters the two completed half outputs and reads normalized SNR
  (`experiments/M115-deconv-headroom/src/s03_instrument.py`, the C3
  common-filter challenge block). Its
  `0.54%` stability is the expected cancellation that also hides post-render
  blur. The source's `8.25x` value is specifically an **RMS-gradient** gain
  (`sqrt(gy1/gy0)`), not an energy ratio; the corresponding energy ratio is
  `68.085x`.
- `(P(A)+P(B))/2 = P_sig + P_noise` follows identically from
  `P_noise=P(A-B)/2`; it verifies arithmetic bookkeeping, not scene
  specificity (`experiments/M115-deconv-headroom/src/m115lib.py`, the
  `split_spectrum` power decomposition).
- The exact historical rerun still fails its flat null: `MEAN=0.438734` and
  `WIENER_UNG=3.331288` against `0.25`. A direct common-mode plant reads FRC
  `0.972099`, so the registered D8 phase-0 gate returned
  `KILL — STOP/REMOVE RUST`
  (`docs/research/M-PHASE0-SPLIT.md`, status clause and “Common-mode structure
  plant” result).

**VERIFIED.** The proposal's claimed C6 subtraction is not commissioned
evidence. C6 is labelled `"ARGUED"` and retains unresolved `[bar]`
placeholders; it says the proposed map *would* let D8 subtract fixed pattern
(`docs/proposals/2026-08-sota-path.md`, “C6. In-situ sensor
self-calibration — breathing as the dither”). The later ledger audit
confirms that no axis tests the C6 calibration product
(`docs/research/M133-blocker-audit.md`, clause beginning “No axis tests the C6
calibration product”). Likewise, a repeated bracket
supplies independent temporal noise but does not by itself erase same-sensor
DSNU/PRNU. Repeat-pair FRC still requires independent A/B calibration and a
held-out corrected-flat/dark residual gate
(`docs/research/M-FRC-VIABILITY.md`, “Shared fixed pattern” and
“Independent repeat capture” clauses). SPLIT2 states the point even more
directly: `"repeated exposures share stable sensor structure"`
(`docs/research/M-PHASE0-SPLIT2.md`, conclusion containing that phrase).

**VERIFIED.** SPLIT2 also tested the available repeat-capture substrate and
stopped before reading FRC. The bright pass cleared the `0.10 native px`
non-translation gate at `0.064031`, but the second-light pass failed at
`0.107703`; an independent spatial estimator reproduced the decisions at
`0.070005` and `0.105202`. No real FRC or `P_sig/P_noise` result was retained
(`docs/research/M-PHASE0-SPLIT2.md`, status, geometry-control, and conclusion
clauses;
`experiments/M135-detail-instrument/d8-audit.json:88-132`).

**VERIFIED.** D8 had already been run through its registered phase-0 gate and
killed; it was not an unintegrated solved answer. The proposal prose still
advertises it, but the current scorecard correctly drops same-frame split-half
FRC/SNR (`docs/proposals/2026-09-sota-scorecard.md`, M11 clause beginning
“The old same-frame split-half FRC/SNR evidence is withdrawn”). The scorecard's
present state is therefore exactly as severe as the original brief says: M1
has `"NO ADMISSIBLE BAR — WITHDRAWN"`
(`docs/proposals/2026-09-sota-scorecard.md`, M1 readiness row and “M1 —
WITHDRAWN: no admissible detail instrument” card).

## 0.1 Does an independent repeated bracket rescue D8?

**VERIFIED — no, not as M1.** It repairs one substrate defect and leaves the
estimator defects intact:

| Recorded failure | Effect of two independently captured brackets |
|---|---|
| 1. Common-filter cancellation | **No repair.** At an ideal Fourier cell, applying the same nonzero USM or blur to both completed renders cancels exactly from normalized SNR/FRC. Finite Hann/ring aggregation leaves implementation-dependent residuals with neither a guaranteed sign nor a distribution-free magnitude bound. |
| 2. Failed flat null | **Partial substrate repair only.** Odd/even exposures already had independent temporal noise. A repeated full bracket repairs z-sampling/partitioning, but stable same-sensor DSNU/PRNU, dust, and shared calibration error remain common unless disjoint calibration and a held-out flat/dark ring null prove otherwise. |
| 3. False/end-point FRC crossing | **No estimand repair.** Explicit censoring prevents reporting the last ring as a number, but cannot turn normalized agreement into delivered resolution. |
| 4. `(A+B)/2` averaging adversary | **No repair.** The attack is defined on the two rendered outputs and remains available with independent captures. |
| 5. Selection versus registration | **Harder, not solved.** Two brackets require inter-bracket registration; the available repeat pair failed its second registered geometry gate. |
| 6. Sensitivity loss as shared fraction `rho` rises | **No inherent repair.** Temporal noise was already independent across odd/even exposures; averaging a full repeat can reduce its variance and make stable common pattern a larger fraction. Ideal per-cell common-filter cancellation remains exact. |

**VERIFIED.** M115's source already defines the odd/even halves as independent
noise observations
(`experiments/M115-deconv-headroom/src/m115lib.py`, the odd/even split and
power-estimator functions). The repeat-pair
fixed-pattern model predicts correlation rising, not falling, as temporal
noise is averaged down
(`docs/research/M-FRC-VIABILITY.md`, “7. Shared fixed-pattern noise and
calibration count”).

**VERIFIED.** The statement in the updated brief that two brackets of the same
scene `"do not share"` fixed pattern is therefore too strong. SPLIT2's source
conclusion is the opposite: even after a new stabilization-off capture,
`"repeated exposures share stable sensor structure"`
(`docs/research/M-PHASE0-SPLIT2.md`, conclusion containing that phrase). The
scorecard capture supplies
necessary material for a better-controlled candidate, not a working or
admitted M1 instrument.

## 0.2 Recommended replacement

**VERIFIED.** I recommend a **non-compensating truth-referenced certificate**
with three outputs:

1. `J_TR`, a permutation-corrected, reference/output information coordinate;
2. `T_TR`, independently referenced transfer, which may veto but never create
   a win; and
3. `U_TR`, repeatable output structure unexplained by the reference, which may
   also only veto.

The estimator is defined and commissioned in
`experiments/M135-detail-instrument/`. Its final frozen synthetic battery
passes all 22 gates
(`experiments/M135-detail-instrument/commission.json:1-199,330-399`).

**VERIFIED.** The central structural escape is not to ask one scalar to be both
invariant to and responsive to the same intervention. For any nonzero
post-render LSI gain `K_k`, `J_TR` is exactly unchanged in each registered
frequency/orientation cell. USM therefore cannot manufacture an information
win. Post-render blur is equally unable to change `J_TR`, but it lowers
`T_TR`, so the certificate rejects it. Pre-sensor blur is a different
intervention: it attenuates the latent before fresh downstream noise and
therefore lowers `J_TR`; genuine optical improvement raises it.

**ASSUMED.** This architecture is physically feasible only with a
higher-sampling independent reference, disjoint calibration, a frozen
nonperiodic random-code target, input-only registration, and at least 64
guarded sites. None of the existing development units contains all of those
roles. The estimator is commissioned; the physical instrument is not.

**VERIFIED.** Three points in the briefs require correction or qualification:

1. The quoted impossibility statement was the verdict in the original
   `34cd4063` version of `M-FRC-VIABILITY`
   (`34cd4063:docs/research/M-FRC-VIABILITY.md`, opening verdict beginning
   “A detail metric exactly invariant to a common linear filter”). The current source was
   revised: it calls common **post-noise** filtering an ideal null and says
   explicitly that pre-noise transfer is different
      (`docs/research/M-FRC-VIABILITY.md`, “5. Responsiveness: not generically
      blind, not yet powered for the claim”). “Invariant to a common
   filter implies blind to blur” is correct only when the blur is the same
   post-noise/output transformation covered by the invariance.
2. D8's numerical summary is accurate, but it combines `P_sig`'s
   filter-response control with `R_SNR`'s filter-invariance control as though
   one statistic had demonstrated both. It had not. M115 also contains no
   planted **improvement** control, so it does not meet this lane's
   bidirectional commissioning standard.
3. The burned grid and development slide can commission arithmetic, refusal
   logic, and some extraction controls, but they cannot fully commission this
   reference-dependent physical instrument. The slide rows are explicitly
   distinct geometries and “never an FRC repeat or checker reference for a
   score” (`docs/proposals/2026-09-sota-scorecard.md`, “2.2 Scored and control
   captures”, high-resolution-slide rows), while the M1
   card requires an independent-reference sentinel
   (`docs/proposals/2026-09-sota-scorecard.md`, M1 “Input needed by a future
   replacement” clause). A fresh score is not
   needed to design the statistic, but the missing reference role cannot be
   manufactured from existing pixels.

## 1. Evidence and holdout boundary

**VERIFIED.** No RAW, holdout render, or scorecard outcome was opened in this
lane. The five calibration-grid captures are burned as one
subject/session, and the six high-resolution-slide stacks are development
only (`docs/proposals/2026-09-sota-scorecard.md`, “2.3 Holdout units and burn
log” and “2.2 Scored and control captures” high-resolution-slide rows).

**VERIFIED.** The scorecard permits those units to commission an instrument
but forbids using them for its score:

> “The burned grid and the development-only high-resolution slide may
> commission a new instrument but may never provide its scored value.”

(`docs/proposals/2026-09-sota-scorecard.md`, M1 “Input needed by a future
replacement” clause containing that sentence)

**VERIFIED.** The final campaign uses only synthetic random-code coefficients,
seed `135135`, 128 independent populations, and no frequency above
`0.25 cyc/native px`
(`experiments/M135-detail-instrument/PREREGISTRATION.md:56-92`;
`experiments/M135-detail-instrument/commission.json:1-39`).

## 2. What has already failed

### 2.1 Gradient and energy statistics

**VERIFIED.** The corrected gradient/RMS family failed the scene-free
specificity test. M39's direct statement is:

> “on the FLAT ROI `2272,1344`, where there is no detail to gain”

and the shipped correction credited that ROI with `+35.47%`
(`docs/research/M39-verify-detail-metric.md`, clause containing the quoted
flat-ROI sentence).

**VERIFIED.** This eliminates raw gradient magnitude, Tenengrad, Laplacian
energy, high-band power, and any positive “noise-subtracted energy” that can
turn selection noise or fixed pattern into detail. A lower bound of zero is
not protection: the halo post-mortem says, verbatim,
`"A metric can be BLIND to a defect ... or PERVERSE on it"`
(`experiments/BUILD-TRIAGE/halosens.py`, comment containing that sentence).
That is why this lane includes both a planted defect and a planted improvement.

### 2.2 Split FRC, `sigpow`, and equivalent blur

**VERIFIED.** Same-capture split FRC was defeated by common structure. The
corpus records a flat ROI at `0.63-0.98` of the detail FRC and a 295x-noise arm
at `0.970`; changing threshold or ring count did not repair it
(`docs/research/SYNTHESIS.md`, “FRC says flat regions contain detail” and
295x-noise challenge clauses).

**VERIFIED.** M46's proposed repair, `sigpow = FRC * P_ring`, initially looked
responsive because it recovered common cross-power. M55 then found:

> “`sigpow` remains non-monotone in true resolution”

and

> “remains quadratic in photometric gain”

(`docs/research/M55-sigpow-verification.md`, opening verdict). Its split choice had
`50x` the leverage of the blur signal
(`docs/research/M55-sigpow-verification.md`, split-choice leverage clause). The candidate was not
merely noisy; its nuisance could dominate and reverse the intended quantity.

**VERIFIED.** M57's equivalent-blur statistic `dsig` did recover a planted
blur, but:

> “it fails its own noise null”

and independent noise moved a true zero by up to `0.343 px`
(`docs/research/M57-detail-metric-from-first-principles.md`, opening result
and noise-null clause). M57's
surviving conclusion was:

> “The defensible claim is two-dimensional”

(`docs/research/M57-detail-metric-from-first-principles.md`, conclusion
containing that sentence).

**VERIFIED.** That conclusion directly supports a non-compensating certificate.
Noise and transfer cannot safely be exchanged inside one scalar.

### 2.3 Slanted edge, `S_25`, and `Q25`

**VERIFIED.** Native `S_25` passed a 24-seed USM test and failed the unchanged
bar when expanded to 64 sites: `1.028294x`. It also moved `4.8400x` under
gamma, `18818.9045x` under logistic tone, and changed strongly with noise and
angle (`docs/proposals/2026-09-sota-scorecard.md`, M1 “Current instrument”
clause).

**VERIFIED.** The ordinal replacement did not solve sharpening:

> “licensed Q25 ... **5.560744x RED**”

and a genuine improvement moved in the wrong direction
(`docs/research/M-PHASE0-SLANTEDGE.md`, “Licensed Q25” challenge result).

**VERIFIED.** The reusable result is external, not intrinsic, tone handling:

> “Independent 33-step PCHIP linearisation is the one clean success”

with at most `0.0141%` affine/gamma/logistic movement
(`docs/research/M-PHASE0-SLANTEDGE.md`, conclusion containing that sentence).
The recommendation below uses
that witness and does not ask the detail statistic itself to solve tone.

### 2.4 Candidate 1: finite learned observer

**VERIFIED.** Candidate 1 started from the correct population data-processing
argument but lost it in the finite implementation. Its own report says:

> “The observed increase is a failure of this finite estimator, not of DPI.”

(`docs/research/M-CAND1.md`, “Sharpening challenge” conclusion)

USM raised the estimate from `0.125099` to `0.137075 bits/tile`,
`1.095732x`; the planted degradation and improvement were correctly not run
after the stop (`docs/research/M-CAND1.md`, stopped-outcome clause).

**VERIFIED.** The lesson is narrower than “mutual information cannot work.”
An arm-specific learned decoder, finite feature bottleneck, regularization, and
optimization do not inherit the population theorem. The recommended estimator
uses a fixed closed-form covariance statistic whose USM invariance holds on
the realized sample, including its permutation correction.

### 2.5 Candidate 2: exact congruence without a lawful task

**VERIFIED.** Candidate 2 achieved the strongest prior algebraic result:
unclipped USM ratio `1.0000000000000009`, with covariance residual
`1.25e-15` (`docs/research/M-CAND2.md`, “What worked” clause).

**VERIFIED.** It still died because its protection stopped at linear
transforms. Gamma and logistic moved the score to `0.502893x` and `0.486741x`,
and the report says:

> “Congruence protects only invertible linear transforms”

(`docs/research/M-CAND2.md`, “What failed” clause containing that sentence).

**VERIFIED.** Candidate 2's later optical signs were valid on its supplied
synthetic task, but the natural captures could not instantiate the required
target/covariance/derivative/test populations. Worse, a zero-target input
returned `NUMERIC` in `16/16`, and ratios between null readings spanned
`0.1108` to `9.0270`
(`docs/research/M131-cand2-ruling.md`, zero-target refusal and final-ruling
clauses).

**VERIFIED.** The recommended architecture keeps Candidate 2's exact
congruence lesson, replaces its artificial class labels with an independent
physical reference, uses external PCHIP, and returns typed no-evidence states.

### 2.6 D8/M115 split-stack information and the phase-0 kill

**VERIFIED.** D8 explicitly promotes M115 into three product roles: a
per-stack tuning objective, a per-tile FRC `"certified-resolution map"`, and a
shipped half-difference null
(`docs/proposals/2026-08-sota-path.md`, “D8. NEW — split-stack
self-calibration: the stack contains its own ground truth”). Its supporting numbers are
real, but they belong to different statistics:

> “A tile where the halves agree to `0.35 cyc/px` *measured* that resolution;
> no model assumption can inflate it.”

(`docs/proposals/2026-08-sota-path.md`, D8 “Certified-resolution map” clause)

- absolute `P_sig` recovered the attenuation of an applied Gaussian filter at
  `0.9938-0.9974`;
- normalized `R_SNR` moved at most `0.54%` under common output filters;
- the largest reported naive reading was `8.25x`; and
- the power decomposition was `1.0000` within floating arithmetic
  (`docs/research/M115-deconv-headroom.md`, summary table and power-identity
  clause).

**VERIFIED.** M135 re-derived those claims from
`M-PHASE0-SPLIT`'s exact historical rerun rather than trusting either prose
summary. The source blobs match the pinned manifest; all four headline
quantities reproduce
(`experiments/M135-detail-instrument/d8-audit.json:3-39,132-145`).

**VERIFIED.** The same rerun resolves the apparent contradiction:

```text
common output filter K at Fourier cell k:
P_sig'   = |K|^2 P_sig
P_noise' = |K|^2 P_noise
SNR'     = SNR
FRC'     = FRC
```

`P_sig` is responsive because it is **not** sharpening-invariant. `R_SNR` and
ideal FRC are sharpening-invariant because they are equally blind to common
post-render blur. The M135 structural probe gives `P_sig` ratios `0.25` and
`4.0` under gains `0.5` and `2.0`, while both normalized ratios remain exactly
`1.0` (`experiments/M135-detail-instrument/d8-audit.json:48-70`). The two
desired properties never coexist in one M115 estimand.

**VERIFIED.** M115's finite Hann/ring implementation is only approximately
invariant to a frequency-varying filter because the filter reweights modes
inside a bin and window leakage mixes them. Its measured `0.537785%` residual
therefore does not contradict the per-cell identity, but neither its sign nor
its size is a structural blur response
(`docs/research/M-FRC-VIABILITY.md`, “4.1 Quantifying the implemented
windowing residual”).

**VERIFIED.** M115 itself exposes the operational consequence:

> “`MEAN` — which destroys contrast to 0.24–0.44× and is obviously the wrong
> answer — scores highest.”

(`docs/research/M115-deconv-headroom.md`, conclusion containing that sentence)

The later coherence adversary makes the failure constructive: delivering
`(A+B)/2` produces perfect coherence and zero half-difference while losing
`29.6%` of delivered band power
(`docs/research/V-SOFTCHECK-coherence.md`, `(A+B)/2` adversary clause). Thus
D8 cannot detect the
brief's averaging defeat.

**VERIFIED.** Same-capture specificity also fails. M115 says:

> “nothing that uses one capture of one sensor can separate a static sensor
> pattern from a static scene.”

(`docs/research/M115-deconv-headroom.md`, conclusion containing that sentence)

The published null values in the brief, `MEAN=0.2984` and
`WIENER_UNG=0.4034`, are the **band means**. The registered rule was maximum
mid-band SNR `<0.25`; the exact rerun's maxima are still worse:
`0.438734` and `3.331288`
(`docs/research/M115-deconv-headroom.md`, flat-null and registered-bar clauses;
`experiments/M135-detail-instrument/d8-audit.json:72-87`). The registered D8
phase-0 lane also planted the shared-pattern failure directly: independent
noise plus a shared pattern read low-band FRC `0.972099`; the lane returned:

> “the exact historical M115 numbers reproduce, but their controls do not
> transfer to the common-mode and data-dependent-tuning failures on which D8
> depends.”

(`docs/research/M-PHASE0-SPLIT.md`, status, common-mode plant, and final
verdict clauses)

**VERIFIED.** Changing the FRC readout does not repair it. M41 found the
published `0.4961` crossing was the last-ring fallback, used by `9/12`
run-of-record values; a `4x4x2` sweep repaired `0/32` settings; a flat reached
the same endpoint; and planted-blur sensitivity fell approximately as
`1-rho` with shared-noise fraction
(`docs/research/M41-r3-kill-measured.md`, endpoint-fallback sweep and
shared-noise sensitivity clauses).

**VERIFIED.** D8's remaining confounds are not minor:

- quantisation error had cross-half correlation `+0.5109`, causing the
  difference channel to report `3.937x` noise where matched independent
  dither reported `63.311x`, a `16x` under-report
  (`docs/research/M115-deconv-headroom.md`, quantisation-correlation clause);
- a separately rendered pair can confound selection with registration:
  `bee-1-cpl` had `8.885 px` median field shift and `1.354 px` local residual,
  sufficient for `87.3%` of observed incoherence
  (`docs/research/V-SOFTCHECK-selection-vs-alignment.md`, `bee-1-cpl`
  registration and attribution clauses);
- the proposal's C6 subtraction is only an argued future instrument with
  unresolved bars, not a commissioned correction
  (`docs/proposals/2026-08-sota-path.md`, “C6. In-situ sensor
  self-calibration — breathing as the dither”); and
- M115 commissioned a planted **defect**, not the separately required planted
  **improvement**. Its control therefore cannot distinguish a responsive
  detail metric from one that simply scores every departure downward.

**VERIFIED.** D8's three faces consequently separate as follows:

1. **Per-stack self-tuning:** no-go as commissioned product logic. Normalized
   SNR can remain a diagnostic coordinate, but not the sole objective. SPLIT2
   commissioned the necessary held-out lineage guard by showing that an
   evaluation-leaking tuner can force FRC to `1.0`; it did not retain a real
   tuning result or validate D8's objective.
2. **Empirical acuity map:** refuted. Agreement to `0.35 cyc/px` certifies
   agreement, not delivered resolution.
3. **Shipped null:** useful as a view of differential noise, but incapable of
   exposing common-mode structure and therefore not ground truth.

This is why the recommendation uses an independent, differently sampled
reference and retains transfer and unexplained-repeatability as vetoes.

### 2.7 Revised repeat-pair FRC ruling

**VERIFIED.** The historical no-go said FRC was `"structurally blind to an
arbitrary-strength common linear post-filter, including blur"`
(`34cd4063:docs/research/M-FRC-VIABILITY.md`, opening verdict containing that
phrase).

**VERIFIED.** The current report narrows that statement. It says the measured
blur was a `"post-noise output filter"` and therefore an intended null, while:

> “Pre-noise transfer is different: it attenuates or strengthens the latent
> signal before fresh downstream noise, so repeat correlation should move.”

(`docs/research/M-FRC-VIABILITY.md`, clause containing that sentence)

Its current ruling is:

> “FRC is safe-by-null for common invertible postfilters, but it is responsive
> to pre-noise information transfer.”

(`docs/research/M-FRC-VIABILITY.md`, final ruling containing that sentence)

**VERIFIED.** This does not rehabilitate D8. M115 C2 filters an already
captured noisy cube and reads absolute `P_sig`; it is not the fresh-downstream-
noise experiment on which the revised FRC argument rests. A future
independent-repeat FRC arm could measure pre-sensor information, but it would
still need a separate delivered-transfer veto and independent calibration.
The current repeat-pair report explicitly retains shared fixed pattern as a
structural confound
(`docs/research/M-FRC-VIABILITY.md`, opening verdict and “7. Shared
fixed-pattern noise and calibration count”).

**VERIFIED.** SPLIT2 is the direct test of the proposed repaired substrate. It
commissioned the arithmetic and 17/17 plants, including held-out tuner leakage,
but its second repeat failed the registered geometry gate and therefore
retained no real FRC. More fundamentally, its conclusion says that even a new
capture with stabilization off would leave stable sensor structure shared
between repeats
(`docs/research/M-PHASE0-SPLIT2.md`, “Commissioning retained, real FRC
forbidden” through “Consequence for source”). A second bracket repairs
full-ladder latent matching and odd/even partitioning, but not common
postfilter blindness, averaging, sensor-fixed structure, or inter-bracket
registration.

**VERIFIED.** The BUILD-SHARP claim that its edge statistic was `18,644x` more
responsive than ring FRC is directionally useful but dimensionally invalid as
a ratio: it divides micrometres by dimensionless FRC movement. Normalized to
their baselines, the comparison is about `+191.9%` edge width versus
`+0.1507%` FRC, and the FRC arm was a common post-noise filter
(`docs/research/M-FRC-VIABILITY.md`, BUILD-SHARP dimensional comparison and
pre-noise distinction clauses). It proves FRC cannot stand alone
as presentation resolution; it does not prove pre-noise blindness.

**VERIFIED.** FRC therefore survives only as a possible information/noise
coordinate after fresh-repeat geometry, calibration, null, and power gates.
It cannot by itself supply M1 or the scorecard-authored, **unratified** `98%`
comparator-qualification rule, because a deliberately post-blurred mode can
retain identical ideal FRC.

### 2.8 Governance conflict inherited from M55

**VERIFIED.** M55's older executable contract says
`uses_ground_truth=true` makes a candidate `"inadmissible for shipping"`
(`docs/research/M55-acceptance-spec.md`, `uses_ground_truth` contract clause).
The current scorecard,
however, explicitly requires a common-mode plant absent from an
`"independent reference"`
(`docs/proposals/2026-09-sota-scorecard.md`, M1 “Required controls for any
replacement” clause).

**ASSUMED.** The scorecard's later requirement supersedes that older B0 field
for M1. The owner must revise or version the M55 declaration contract before
this candidate can be mechanically admitted; setting the field false would
hide the architecture rather than resolve the conflict.

### 2.9 The second flat-null failure

**VERIFIED.** M137 independently reproduced a Catmull-Rom-over-bilinear
high-band gap of `0.3403664343410666 dex` on selected detail tiles. Its later
flat arm carried only `13.314850036584688%` of the detailed arm's coarse
structure yet produced a larger `0.3488548829813006 dex` gap. The
flat/detail gap ratio was `1.0249391472947889`, or
`2.4939147294788855%` higher on the flat arm
(`experiments/M134-kernel-frontier/M137-clamped-detail.md`, “Flat/detail
specificity control” result).

**VERIFIED.** The registered flat-gap ceiling was `0.10`; both the main and
independent verifier returned `S7_flat_band_null=false`, while the previous
gates and decomposition remained unchanged. The lane therefore withdrew the
resolved-detail interpretation
(`experiments/M134-kernel-frontier/M137-clamped-detail.md`, flat-arm verdict;
`experiments/M134-kernel-frontier/detail-results.json`, `flat_control` result).

**VERIFIED.** This is the same specificity failure as D8 by a different route.
FRC treated repeatable flat structure as resolution; band power treated
kernel-amplified high-frequency noise as detail. A one-time exact-zero refusal
is therefore insufficient. Every claim-bearing M135 evaluation now requires a
matched featureless sentinel rendered by the same candidate mode and emits
flat/detail information, reference-repeatability, and output-repeatability
ratios. Missing or failed flat evidence suppresses the score
(`experiments/M135-detail-instrument/AMENDMENT-4.md:1-64`).

## 3. The precise impossibility result

### 3.1 What is impossible

**VERIFIED.** Let `Y1` and `Y2` be already realized noisy outputs and let the
same nonzero scalar transfer `K_k` be applied to both at Fourier cell `k`.
For normalized correlation,

```text
rho_k(Y1, Y2)
  = cov(Y1, Y2) / sqrt(var(Y1) var(Y2))

rho_k(KY1, KY2)
  = |K|^2 cov(Y1, Y2)
    / sqrt(|K|^2 var(Y1) |K|^2 var(Y2))
  = rho_k(Y1, Y2).
```

The same congruence extends to canonical correlations under any nonsingular
linear transform of the complete observed feature vector.

**VERIFIED.** Therefore a statistic exactly invariant to a family of common
post-noise linear operators cannot distinguish any member of that family from
identity. If the family contains both USM and blur, the statistic is exactly
blind to both as post-render interventions. Invariance and blindness are the
same property **for that intervention point**.

**VERIFIED.** This is exactly the D8 reconciliation. Normalized split SNR and
ideal FRC divide away `|K_k|^2`; absolute `P_sig` does not. The former are
sharpening-safe but blur-blind, while the latter is blur-responsive but
sharpening-gameable. Combining evidence from the two does not create a scalar
with both properties.

**VERIFIED.** This eliminates the following as stand-alone M1 instruments:

- FRC, FSC, normalized spectral SNR, magnitude-squared coherence, NCC, and
  `C/(C+U)` when asked to distinguish common post-render blur;
- any exact affine/congruence-invariant observer when blur and USM are both
  applied to the already-noisy observation;
- any scalar claiming simultaneous exact post-USM invariance and positive
  response to a nonzero invertible post-render blur;
- any empirical “near invariance” argument without an implementation-level
  bound.

### 3.2 What is not impossible

**VERIFIED.** The theorem does not cover an optical/pre-sensor intervention.
Under

```text
Y = H S + epsilon,
```

changing `H` before drawing fresh `epsilon` changes signal relative to
downstream noise. Applying `K` later gives

```text
Y' = K(H S + epsilon),
```

which scales both terms together. Those are different experiments.

**VERIFIED.** The theorem also does not prohibit a vector certificate in which
one coordinate is postfilter-invariant and another independently measures
transfer. It prohibits pretending that the invariant coordinate itself
measures presentation transfer.

**ASSUMED.** A lawful escape therefore needs all three:

1. an independent reference that identifies scene-linked structure;
2. fresh downstream noise in the optical blur/improvement arms; and
3. non-compensating transfer/artifact vetoes beside the invariant information
   coordinate.

### 3.3 Shared-base-optic reference ruling

**DERIVED — ADMISSIBLE WITH CONDITIONS.** “Independent reference” does not
require a different prime lens. Let the base lens contribute a common
pre-sensor transfer `G`:

```text
R = A G S + eta
Y = H G S + epsilon.
```

With independently exposed and calibrated paths,
`cov(epsilon, eta) = 0`, so:

```text
cov(Y, R) = H G P_S G* A*.
```

The shared optic cannot create reference/output covariance when no
scene-linked term is present. It is also not the common **post-noise** filter
from §3.1: `G` acts before the fresh `epsilon` and `eta` draws. The
invariance/blindness proof is therefore not reintroduced merely because the
prime lens is shared.

The price is a narrower estimand. `J_TR` now measures information about
`G S`, not unconstrained object truth. A shared optical zero is invisible; a
shared lens-specific ghost, halo or aberration can be treated as truth if it
repeats in both paths. Sharing the prime therefore cannot support an absolute
claim beyond its passband. It can support the comparative statement that one
renderer recovers more information present through the frozen shared-lens
path, provided the following predicates all pass:

1. reference and scored arms are separate physical exposures with fresh
   downstream noise;
2. converter-on reference, converter-off output, A and B use the disjoint
   flat/dark lineages registered in §6;
3. the scale change puts common sites on different sensor footprints and
   blank-residual correlation is `<=0.05`;
4. both reference halves pass repeatability and tone/rail eligibility;
5. converter-on object-space transfer is demonstrably stronger in every
   registered cell;
6. `LCB95(M_reference / M_scored) >= 2.0`;
7. no crop, digital zoom, resample or source-derived oracle creates the
   reference; and
8. the reported claim says explicitly that the shared prime's zeros and
   common aberrations are outside the identified truth.

**DERIVED.** Nominal `2.8 / 1.4 = 2.0` has no uncertainty margin and does not
clear predicate 6 on the measured rig. The measured conservative
converter-on value is `2.7015`, so a nominal `1.40x` scored state gives only
`1.9296x`. The existing `1.32x` target with a hard `1.33x` maximum gives a
conservative point ratio of `2.0312x`; it is admissible only if the
pre-registered interval calculation still leaves its one-sided 95% lower
bound at or above `2.0`.

**RULING.** A second macro optic is not required before trying the existing
Sony 100 mm plus Viltrox inversion. The shared-optic correlation narrows what
`J_TR` means; it does not itself fake `J_TR`. Correlated calibration, sensor
pattern or a shared optical artifact would add common structure and can inflate
the statistic, which is why the lineage, footprint, blank, transfer and
claim-scope predicates above are hard refusals rather than caveats.

## 4. Candidate architecture A — per-cell truth-referenced information

### 4.1 Inputs and population

**ASSUMED.** Use a sealed random-phase multisine or equivalent random-code
target. It contains 64 or more disjoint guarded cells. Each cell carries
independently randomized amplitude and phase at four radii
`0.10, 0.15, 0.20, 0.25 cyc/native px` and four orientation sectors
`0, 22.5, 45, 67.5 degrees`. The seed and target are frozen after the
pipeline/comparator versions and before capture.

**ASSUMED.** Each target cell includes a guard wider than the maximum
registered USM support. The scored carrier interior is therefore an
eigenfunction of every registered LSI challenge rather than a crop/window
approximation. This target is globally nonperiodic because each site's code is
independent; knowing the carrier frequencies does not reveal its phases or
amplitudes.

**ASSUMED.** Acquire the following paired evidence streams:

- `Y1`, `Y2`: two complete same-input-role bracket captures, each rendered
  independently by the mode under test;
- `R1`, `R2`: two independently calibrated, fixed-focus, higher-sampling
  reference realizations of the same physical code cells; and
- `F_Y1`, `F_Y2`, `F_R1`, `F_R2`: the corresponding four streams on a
  preregistered featureless sentinel, processed by the same mode.

The reference must use a different sensor footprint and at least `2.0x`
subject sampling, then be low-passed and resampled to the scored native grid.
Input-only fiducials freeze registration before any output is rendered.

**VERIFIED.** The scorecard already requires two `sw4`, two `sw10`, matched
dark/flat inputs, and a nonperiodic independent-reference sentinel
(`docs/proposals/2026-09-sota-scorecard.md`, M1 “Input needed by a future
replacement” clause). It also caps all claim
frequencies at `0.25 cyc/native px`
(`docs/proposals/2026-09-sota-scorecard.md`, M1 “Exact computation” clause).

### 4.2 Information estimator

**VERIFIED.** For site `i`, cell `k`, output realization `a`, and reference
realization `b`, center coefficients across sites and compute:

```text
q_abk = |cov(Y_a,k, R_b,k)|^2
        / (var(Y_a,k) var(R_b,k))

j_abk = max(0,
             -log2(1 - q_abk)
             - Q95_permutation[-log2(1 - q_abk)])

J_TR = min_ab mean_k(j_abk).
```

The 32 site permutations, their seed, the minimum over all four pairings, and
the equal weighting of all 16 cells are fixed
(`experiments/M135-detail-instrument/PREREGISTRATION.md:17-42`).

**VERIFIED.** The population is the set of independently coded physical sites,
not pixels or Fourier bins. The denominator is the product of the output and
reference sample variances in the same cell. The permutation subtraction
provides a finite-sample no-information floor without dividing by a near-zero
detail estimate.

**ASSUMED.** On the engineered proper-complex code population, `-log2(1-q)`
has the Gaussian-channel mutual-information interpretation. On arbitrary
natural texture it is only a covariance information score; the stronger
interpretation must not be claimed.

**VERIFIED.** The public evaluator now refuses a missing flat sentinel. For
arrays `A,B`, define

```text
P_rep(A,B) = mean_k max(0, Re cov(A_k,B_k)).
```

Every otherwise claim-bearing evaluation emits and gates:

```text
J_TR(flat) / J_TR(detail)                         <= 0.10
P_rep(reference_flat) / P_rep(reference_detail)  <= 0.25
P_rep(output_flat) / P_rep(output_detail)        <= 0.10.
```

The flat's own core status must be `NO_DETAIL`; otherwise the top-level result
is `FLAT_NULL_FAILED`. These are certificate fields on every run, not an
offline validation plot
(`experiments/M135-detail-instrument/AMENDMENT-4.md:13-54`;
`experiments/M135-detail-instrument/instrument.py:184-359`).

### 4.3 Transfer and unexplained-repeatability vetoes

**VERIFIED.** Define, per cell:

```text
P_R  = Re cov(R1, R2)
C_YR = mean_ab cov(Ya, Rb)
P_Y  = Re cov(Y1, Y2)

T_k = |C_YR| / P_R
U_k = max(0, P_Y - |C_YR|^2/P_R) / max(P_Y, epsilon).
```

`T_TR` is the geometric mean of `T_k`; `U_TR` is the median of `U_k`.
The committed implementation uses those definitions
(`experiments/M135-detail-instrument/instrument.py:192-245`).

**VERIFIED.** `T_TR` and `U_TR` are veto-only. This is required by the
scorecard's hard-gate rule:

> “Every primary metric is a hard gate. No win compensates for a loss.”

(`docs/proposals/2026-09-sota-scorecard.md`, “0.1 Decision rule” hard-gate
clause containing that sentence)

### 4.4 Exact sharpening argument

**VERIFIED.** For any registered nonzero LSI postfilter `K_k` applied after
output noise:

```text
cov(KY, R) = K cov(Y, R)
var(KY)    = |K|^2 var(Y)
q(KY, R)   = q(Y, R).
```

Every site-permuted `q` is invariant by the same identity, so its 95th
percentile and the corrected `j` are invariant too. The minimum across
pairings and mean across cells preserve equality. This is a realized-sample
identity, not an asymptotic claim.

**VERIFIED.** USM may raise `T_TR`, but `T_TR` cannot create a win and `J_TR`
cannot rise. Post-render blur leaves `J_TR` tied and lowers `T_TR`. Thus neither
can improve the certificate.

**VERIFIED.** The final 64/128/256/512-site battery measured maximum USM ratio
error `3.33e-16` against the unchanged `1.01` bar
(`experiments/M135-detail-instrument/commission.json:335-364`).

### 4.5 Optical response

**VERIFIED.** Under the commissioned model

```text
R = A S + eta
Y = H S + epsilon
```

with independent downstream noises,

```text
q = |H A*|^2 P_S^2
    / ((|H|^2 P_S + P_epsilon)
       (|A|^2 P_S + P_eta)).
```

For fixed positive noise and reference terms, `q` is strictly increasing in
`|H|^2`. Pre-sensor blur lowers `J_TR`; genuine optical improvement raises it.
This is the response that common post-noise invariance does not cancel.

### 4.6 Known-defeat audit

| Defeat | Disposition |
|---|---|
| Sharpening | **VERIFIED.** Exact per-cell invariance means USM cannot raise `J_TR`; transfer is veto-only. |
| Monotone tone | **VERIFIED.** A separate 33-step PCHIP witness linearizes gamma/logistic before scoring; missing or failed witness returns no number. |
| Averaging destroys detail | **VERIFIED.** Averaging may raise `J_TR` by lowering noise, but any transfer loss fails `T_TR`; no compensation is allowed. |
| Shared fixed pattern | **ASSUMED.** Different sensor footprint/scale, disjoint flats/darks, and a blank-residual correlation gate must prove lineage. The pixels alone cannot. |
| Deterministic hallucination | **VERIFIED** when absent from the reference: it raises output variance or `U_TR` without raising reference covariance. **ASSUMED** against a hallucination that predicts the reference: the sealed random code makes such agreement evidence extracted from the input rather than a reusable prior. |
| Periodic checker | **ASSUMED.** Periodic or public targets are ineligible by provenance, even if their covariance looks rich. |
| Flat ROI | **VERIFIED.** The matched flat is mandatory and reports three flat/detail ratios. Independent noise remains near zero; a structured false flat and a common A/B artifact return `FLAT_NULL_FAILED`. **ASSUMED** for physical data until the sentinel and lineage gates are commissioned. |

### 4.7 Failure boundary

**VERIFIED.** The complete certificate, not the score alone, is required. In
the final commissioning run, a flat shared-pattern plant was correctly refused
when its calibration correlation was present. Disabling that witness made the
same flat plant return `OK`, `J_TR=1.830436`. A predictable full-rank cyclic
target with forged lineage returned `OK`, `J_TR=1.799726`
(`experiments/M135-detail-instrument/commission.json:238-329`).

**VERIFIED.** No image-only statistic can distinguish those forged cases from
truth. Independence and unpredictability are facts about acquisition lineage,
not properties inferable from the output pixels. Missing lineage therefore
returns `MISSING_LINEAGE`, never a numeric value
(`experiments/M135-detail-instrument/AMENDMENT-3.md:6-23`;
`experiments/M135-detail-instrument/commission.json:850-937`).

**VERIFIED.** The amended certificate also closes the exact hole exposed by
M137. Across all uncontaminated synthetic arms, the worst single-run
flat/detail ratio was `0.0023196142160268125` for corrected information,
`0.0011493247893537382` for repeatable reference power, and
`0.09619849966263185` for repeatable output power. Passing the detailed target
itself as the alleged flat produced ratios of exactly `1.0` and
`FLAT_NULL_FAILED`; adding a common artifact to both flat outputs failed in
`128 / 128` populations
(`experiments/M135-detail-instrument/commission.json:207-490,859-923`).

## 5. Candidate architecture B — full-covariance canonical information

### 5.1 Definition

**ASSUMED.** Form a real feature vector from all registered carrier
quadratures in a site. With eight complex carriers, `p=16`. Require at least
`N=256` independently coded sites. For each output/reference pairing, compute
unregularized sample covariances and the squared canonical correlations
`lambda_l` of

```text
Sigma_YY^-1 Sigma_YR Sigma_RR^-1 Sigma_RY.
```

Define:

```text
J_CCA = -1/2 sum_l log2(1 - lambda_l),
```

subtract the same 95th-percentile site-permutation floor, and take the minimum
over the four output/reference pairings. Use the same `T_TR`, `U_TR`, lineage,
tone, frequency, and refusal gates as architecture A.

### 5.2 Structural property

**VERIFIED.** For any nonsingular linear transform `K` of the complete output
feature vector,

```text
Sigma_YY -> K Sigma_YY K^T
Sigma_YR -> K Sigma_YR,
```

and the canonical eigenvalues are unchanged by similarity. This protects
against arbitrary invertible linear mixing inside the complete registered
feature space, not only LSI per-cell gains.

### 5.3 Why it is not the recommendation

**VERIFIED.** Exact congruence requires full rank and no regularization.
Regularization, clipping, omitted coordinates, or a transform that imports
energy from outside the feature space breaks the proof. Candidate 2 already
demonstrated both sides: machine-precision USM congruence and catastrophic
nonlinear-tone movement
(`docs/research/M-CAND2.md`, “What worked” and “What failed” clauses).

**ASSUMED.** `N=256` for `p=16` is the minimum acceptable planning ratio, not a
proven physical power result. It quadruples the scorecard's 64-site floor and
the target area. The per-cell candidate gets the exact protection needed for
registered LSI sharpening with far less rank pressure.

### 5.4 Known-defeat audit

| Defeat | Disposition |
|---|---|
| Sharpening | **VERIFIED** for nonsingular linear transforms contained in the feature space. |
| Tone | **ASSUMED** external PCHIP or refusal; CCA itself is not tone-invariant. |
| Averaging | **ASSUMED** same non-compensating transfer veto as architecture A. |
| Shared fixed pattern / hallucination | **ASSUMED** same independent-reference and residual controls; no covariance method can repair shared false truth. |
| Periodic checker | **ASSUMED** same target-provenance refusal. |
| Flat ROI | **ASSUMED** same mandatory paired-flat certificate and three non-compensating ratios as architecture A. |

**VERIFIED.** Architecture B is mathematically broader but operationally less
ready. It is a fallback if real image extraction shows material cross-cell
mixing that invalidates architecture A's LSI carrier model.

## 6. Recommended physical protocol

### 6.1 Target and capture

**ASSUMED.** Replace “any irregular natural patch” with a frozen random-code
target for M1 admission. Natural texture remains useful for generalization,
but it cannot provide the structural anti-prediction argument by itself.

**ASSUMED.** The target must:

1. contain at least 64 independently seeded guarded cells;
2. carry all 16 registered frequency/orientation cells in every site;
3. use random phase and modest random amplitude, with no repeated site;
4. keep the seed unavailable to every renderer until all binaries, settings,
   and hashes are frozen;
5. include input-only fiducials outside scored carriers;
6. include preregistered neutral, featureless sentinel sites at matched tonal
   levels and field positions, with their locations hidden from adaptive
   render tuning; and
7. be photographed by an independently calibrated reference path at at least
   `2.0x` the scored subject sampling.

**ASSUMED.** Two output brackets and two reference halves are mandatory.
Reference and output must not share flat/dark masters. The reference must land
on a different sensor footprint after scale change or dither. A blank-residual
cross-correlation above `0.05` refuses the capture.

**ASSUMED.** The same candidate settings must render both coded and
featureless sites. A separately tuned or recognizably special-cased flat
sentinel is not a valid null. Physical commissioning must randomize or conceal
sentinel locations well enough to test that assumption.

### 6.2 Linearization and geometry

**ASSUMED.** Decode to camera-linear float. Apply the independent 33-step PCHIP
response inverse before registration or Fourier extraction. Refuse:

- rail fraction above `0.1%`;
- effective precision below 12 bits;
- failed or missing tone witness;
- non-finite samples;
- input-only registration residual above `0.10 native px`;
- any reference/scored sampling ratio below `2.0`;
- any reference-transfer band not demonstrably stronger than the scored path.

**ASSUMED.** No image-derived warp may be tuned on a rendered score. Geometry,
site manifests, carrier bins, guards, and exclusions must be frozen from
input/reference data only.

### 6.3 Scored comparison

**ASSUMED.** Use the scorecard's 10,000-draw fixed-seed hierarchical bootstrap
by capture then physical site (`docs/proposals/2026-09-sota-scorecard.md`,
“10,000 fixed-seed (`20260902`) hierarchical bootstrap draws by capture, then
physical site” clause).

**UNRATIFIED (inherited from scorecard rule 4).** A mode is provisionally
information-qualified only if, separately on every capture and pooled:

```text
LCB95(J_mode / J_best_registered) >= 0.98.
```

The scorecard calls this its replacement-M1 comparator-retention rule
(`docs/proposals/2026-09-sota-scorecard.md`, “Once a replacement M1 is
admitted” clause), but that rule and its `98%` value are not traceable to the
owner's plan. M135 has implemented the current interface value; it does **not**
claim owner authority or physical justification for it. A claim-bearing
protocol must either ratify `0.98` explicitly or replace it by preregistered
power/utility reasoning and version the consumer contract.

**UNRATIFIED (M135 proposal).** Call one mode M1-ahead of another only if:

```text
LCB95(J_A / J_B) > 1.02
LCB95(T_A,k / T_B,k) >= 0.98 for every registered cell k
UCB95(U_A - U_B) <= 0.02
```

Ratios in `[0.98,1.02]` are parity. These are non-compensating: an information
gain cannot buy transfer loss or unexplained repeatable structure.

**ASSUMED.** Before any ratio above is claim-bearing, the same run must pass:

```text
status(flat)                                      = NO_DETAIL
J_TR(flat) / J_TR(detail)                         <= 0.10
P_rep(reference_flat) / P_rep(reference_detail)  <= 0.25
P_rep(output_flat) / P_rep(output_detail)         <= 0.10.
```

Omission is `MISSING_FLAT_CONTROL`; any failed condition is
`FLAT_NULL_FAILED`. These are hard gates, not quantities another coordinate
may compensate.

**UNRATIFIED.** The `1.02` superiority margin is M135's symmetric planning
proposal beside the scorecard-authored `0.98` value, not an owner requirement.
It requires a physical power and decision-utility study before adoption. If
the registered 64-site design cannot resolve the ultimately ratified margin,
the outcome is `UNDERPOWERED`, not a relaxed bar.

### 6.4 Owner-facing acquisition specification

> **IMMEDIATE PROCUREMENT SUPERSEDED.** The custom-code specification below
> remains the strongest route to a target-independent anti-prediction claim,
> but it is not the next owner action. Section 6.6 supersedes it for the first
> physical binding attempt: use the confirmed camera, prime and Viltrox in the
> inverted configuration, spend `$0` on optics or target fabrication, and let
> the rehearsal's sampling, transfer, lineage and target-eligibility gates
> decide whether fabrication is needed.

> **OWNER-ACTION DRAFT — do not shoot from this section by itself.** The
> orchestrator owns the executable capture request. This section states what
> M135 needs that request to contain. `M_work`, the physical control offset,
> and the final artwork remain unset until the M147 preflight closes them.

> **Conflict to resolve in the owner-owned request.** Its current “existing
> grid plus a coplanar nonperiodic patch” language says any stable fine
> irregular texture works. That is enough for the narrower natural-target
> result in §6.5(b), but not for M135's full structural anti-prediction claim.
> Full M1 requires the concealed independent-code panels below. M135 records
> the conflict here and does not edit the orchestrator-owned request.

#### What must physically exist

The full M1 claim needs **one concealed-seed random-code target per session**.
The cheapest fabrication is one glass carrier holding two physically separate
panels: `D` for development/rehearsal and `H` for the sealed score. Their seeds
and site layouts must be independent; cover `H` while `D` is used. It does not
need certified absolute scale. It does need enough real optical contrast that
both camera states can recover the same independently randomized coefficients.

Give the fabricator a final 1:1 artwork with these requirements:

- a rigid, flat `25 x 25 mm` glass carrier holding two separately framed
  panels;
- one `D` panel and one `H` panel, each with an active image no larger than
  `12 x 8 mm`, so each whole region remains inside the converter-on reference
  field;
- a `10 x 8` interleaved layout containing **64 unique coded sites** and **16
  featureless sentinel sites** on each panel;
- in each coded site, a `128 x 128`-scored-pixel interior containing all 16
  registered frequency/orientation cells, surrounded on every side by a guard
  equivalent to at least `64` scored native pixels;
- four or more high-contrast fiducials outside the scored interiors;
- a coplanar **33-level neutral tone strip**, with strictly monotone levels,
  large enough that each level has an unclipped uniform interior on each
  panel; and
- no repeated code site within or across panels. Generate the per-site phases
  and amplitudes only after every renderer binary, setting and hash is frozen;
  keep the `H` seed and analytic site manifest sealed until scored outputs are
  complete.

The final physical dimensions of each cell and carrier period must be generated
from M147's accepted `M_work`; **do not let a print shop fit, scale, sharpen,
screen or resample the artwork**. The supplied file is already final-size.
The shortest carrier must map to no more than `0.25 cyc/scored native px` after
the achieved magnification is measured. The target is unusable if the measured
mapping crosses that cap.

The preferred production medium is a high-resolution photographic emulsion or
grayscale photomask on glass. A binary chrome-on-glass mask is acceptable for
the code field only if the 33-level witness is supplied as a separate
coplanar strip. The strip does not need certified absolute reflectance: its
camera-linear patch means become the PCHIP abscissae. It does need 33 neutral,
strictly monotone, spatially uniform and non-clipped levels. Ask for:

- at least `20,000 dpi` addressability or `<=1.25 micrometre` address grid;
- demonstrated contrast at `>=100 line pairs/mm`;
- local feature-placement error `<=1 micrometre` and active-area scale error
  `<=0.25%`;
- a density range that keeps all 33 measured levels separated from both the
  noise floor and clipping at the chosen exposure; and
- no lamination, texture, moire screen, automatic contrast enhancement or
  geometric correction.

Freeze the maximum registered postfilter support before releasing artwork.
The proposed `64`-native-pixel guard is admissible only if every registered
support radius is strictly smaller. Otherwise enlarge the guard/layout or
refuse that mode; do not waive the guard after printing.

Those manufacturing numbers are conservative procurement screens, not an
absolute calibration claim. The **load-bearing acceptance test is optical**:
both reference halves must carry repeatable power in every registered cell,
all 64 coded sites must remain eligible, sentinels must return `NO_DETAIL`, and
the reference/scored sampling and transfer gates must pass. A scratched,
curled, rescaled, screened or insufficiently resolved print is unusable even
if its invoice advertises the requested dpi.

Ordinary desktop printing is not adequate. At `2400 dpi`, nominal address
spacing is about `10.6 micrometres`, already comparable to the shortest
required physical period; marketing dpi is not resolved line-pair contrast.

Commercial targets can help diagnose the rig but do not replace the custom
artifact:

| candidate | useful for | why it is not the full M135 target |
|---|---|---|
| Thorlabs R1DS1P or another USAF 1951 glass target | focus and reference-transfer preflight | sparse, repeated, public bars; no 64 independent codes, concealed seed, sentinels or tone witness |
| Imatest SFRplus or sinusoidal Siemens Star | field/framing and MTF checks | deterministic public geometry; no independent per-site phases and no matched flat population |
| a commercial DIC random-speckle target | cheap anti-repetition rehearsal | random texture, but not the frozen 16-cell spectrum, guarded site population or 33-level witness |

#### Reference optical path

**VERIFIED from the current capture request.** The owner has a Sony A7C II,
Sony FE 100mm F2.8 GM, and 2x Viltrox teleconverter. The cheapest reference
uses that existing rig: converter **on** at the established maximum-reproduction
state for `R1/R2`, then converter **off** at M147's accepted `M_work` for the
scored TC0 brackets. The current conditional geometry is approximately
`2.7015 / 1.33 = 2.0312x`, but that is not permission to dial `1.33x`; the
preflight must establish `LCB95(M_ref / M_work) >= 2.0`
(`docs/capture-requests/2026-09-319-frame-session.md`, stop banner and
“Reproduction ratio” section).

**ASSUMED.** The converter-on path has stronger object-space transfer in every
registered cell. Sampling ratio alone does not prove that. The rehearsal must
measure it; a failed cell is refused, not repaired by resampling.

The reference may share the base lens. What must be independent is the
physical exposure/noise draw, calibration, sensor footprint and measured
transfer. Sharing the base optic limits the statement to detail recoverable
through that reference path: a shared optical zero or aberration cannot be
certified as object truth. A physically closer capture or extension-tube state
could also qualify if it passes the same sampling, transfer, footprint and
calibration gates. A crop, digital zoom or resample of the scored capture
cannot qualify because it creates no new samples or downstream noise.

No repository evidence says the owner has extension tubes or a second suitable
macro optic. Treat either as **unknown**, not available. No new optic should be
bought unless the converter-on rehearsal fails its transfer gate.

#### Shot list

The artifact adds **zero frames** if it replaces the generic nonperiodic patch
in the already planned sessions and remains visible in every subject frame.
The complete M135-dependent bill is:

| sitting and block | frames |
|---|---:|
| preflight: same unmoved grid, converter on then off | `2` unscored setup frames |
| rehearsal TC0 `sw4-A/B` and `sw10-A/B` | `164` |
| rehearsal TC0 reset/start/end witnesses | `60` |
| rehearsal TC0 flat/dark A/B groups | `128` |
| rehearsal converter-on `R1/R2` near/mid/far atlas | `96` |
| rehearsal converter-on flat/dark A/B groups | `128` |
| rehearsal preregistered sharp control, near/mid/far | `96` |
| rehearsal preregistered focus-offset blur control, near/mid/far | `96` |
| **rehearsal total** | **`768`** |
| scored converter-on claim/calibration block | `383` |
| scored converter-on fixed-focus witnesses | `60` |
| scored converter-on `R1/R2` near/mid/far atlas | `96` |
| scored TC0 `sw4-A/B` and `sw10-A/B` | `164` |
| scored TC0 fixed-focus witnesses | `60` |
| scored TC0 flat/dark A/B groups | `128` |
| **scored-session total** | **`891`** |

This restates the current block arithmetic; the orchestrator's capture request
remains authoritative (`docs/capture-requests/2026-09-319-frame-session.md`,
“Frame counts — scored to” and “Physical control arms for the detail
instrument” sections).

Every coded site must have an interior focus peak in both complete A/B passes.
At least 64 must survive clipping, registration, guard and reference-power
eligibility. The focus-offset magnitude for the blur control and the sharp
control's focus position must be fixed by the non-holdout preflight, not chosen
from whichever captured frames give the desired signs.

Calibration separation is mandatory:

- converter-on and TC0 may not share flat or dark masters;
- A and B may not share a master within one optical state;
- rehearsal and scored sessions may not share a reference or calibration;
- reference odd frames use converter-on A masters and even frames use
  converter-on B masters; and
- every candidate mode renders coded and featureless sites with identical
  settings.

#### Cost and lead time

These are planning ranges, **not vendor quotations**:

| item | planning cost | lead time | confidence |
|---|---:|---:|---|
| existing camera, lens, Viltrox converter, support and lighting | `$0` incremental | available | high; repository-confirmed |
| one-off `20,000-25,400 dpi` silver-halide photoplot prototype | `$50-150` delivered | `2-5` business days | medium-low; vendor capability must be checked |
| rigid mount or optical-glass carrier for film | `$20-75` | `1-3` days | medium |
| separate miniature 33-level matte tone strip | `$5-50` | same day to `3` days | medium; measured monotonicity matters, not nominal density accuracy |
| production binary chrome-on-glass mask | `$250-800` | `1-3` weeks | low until quoted |
| integrated grayscale mask instead of a separate strip | `$300-1,000` incremental | `1-3` weeks | low until quoted |
| two-frame preflight, 768-frame rehearsal and 891-frame scored sitting | `$0` incremental hardware | owner scheduling plus analysis | high on frame counts; duration deliberately unpromised |

The recommended procurement sequence is: quote the cheap photoplot first,
inspect its vendor MTF/minimum-feature specification, and use it only if the
rehearsal's optical eligibility tests pass. Order glass only if the film cannot
retain all carriers or remain flat. The required thing is a physically
qualified one-time code artifact, not an expensive brand name.

#### What the owner must not do

1. Do not expose the code seed before renderer binaries, settings and hashes
   are frozen, and do not expose the `H` seed or analytic manifest until all
   scored outputs are complete.
2. Do not print from a viewer, office driver or RIP that scales, screens,
   sharpens or “optimizes” the artwork.
3. Do not substitute a public periodic chart for the concealed random code.
4. Do not derive the reference by cropping or resampling a scored frame.
5. Do not share target panels, flats, darks, reference captures or selected
   sites across rehearsal and score.
6. Do not select blur frames after seeing the ladder, and do not use the truth
   reference itself as the improvement output.
7. Do not combine rehearsal and score in one uninterrupted sitting. The
   rehearsal must be read, accepted, and frozen before the scored sitting.
8. Once the scored sitting starts, do not inspect a render, metric, visual
   verdict or comparator output from any member. The holdout unit is the
   subject plus uninterrupted capture session
   (`docs/proposals/2026-09-sota-scorecard.md`, “2.3 Holdout units and burn
   log”).

### 6.5 Cheapest lawful escape

#### a. Existing equipment and the same optic

**Yes, conditionally; no new optic is presently justified.** The existing
converter-on/bare-lens pair can provide the reference/scored sampling ratio.
Using the same base lens at higher magnification does not violate the
information estimator. It does, however, leave shared lens transfer outside
what the reference can reveal. Therefore the admissible statement is
reference-conditional, and every registered cell must show stronger
converter-on object-space transfer plus the required sampling lower bound.

A physically closer exposure or an extension tube can create a real
higher-sampling reference because it creates new sensor samples and new noise.
A crop, upsample or resample cannot. Extension-tube ownership is not recorded,
and buying one before testing the confirmed converter path would be premature.

#### b. Natural target plus concealed site selection

**Not for the full structural claim.** Concealing the site manifest prevents
result-driven site choice. It does not make a natural patch's high-frequency
coefficients independent of its low-frequency context or of generic texture
priors. A deterministic renderer can predict plausible fibres, veins or grain
that correlate with a natural reference even when it did not recover those
coefficients from the scored input.

The coded target buys the missing fact: independent, one-time phases and
amplitudes in every registered cell, balanced across sites and unknown before
the renderer is frozen. That makes reference agreement evidence about
transferred input information rather than reusable scene prior. It also gives
an exchangeable site population for the permutation floor and guarantees that
all frequency/orientation cells are represented.

A natural target with a concealed manifest is still useful for a narrower
statement: **on this frozen renderer and these concealed natural sites, output
agreement with the higher-sampling reference improved without a transfer or
unexplained-structure regression.** That is an operational generalization
result, not the structurally anti-predictive M1 admission result.

#### c. No-new-capture result

**No scored M1 number is available without a new capture.** The archive has no
bare-lens frame, no same-site independently sampled reference/output pair with
disjoint calibration, and no pre-noise blur plus planted-improvement controls.
The burned grid and development-only slide may commission extraction but may
never provide the scored value
(`docs/proposals/2026-09-sota-scorecard.md`, M1 “Input needed by a future
replacement” clause). A descriptive development result could be reported, but
it would leave M1 `UNMEASURED`; relabelling it “relative” does not restore the
missing lineage.

#### d. Rank by cost to first defensible number

| rank | route | cash cost | first defensible result |
|---:|---|---:|---|
| 1 | existing rig + concealed natural target + planned sessions | `$0` | narrow renderer-and-target-conditional result only; **not scorecard M1** |
| 2 | existing rig + one-off high-resolution random-code photoplot, tone strip and planned sessions | about `$75-275` including mount | cheapest plausible full M1 route if the rehearsal qualifies the print |
| 3 | existing rig + custom glass mask/tone witness + planned sessions | about `$275-1,800` | highest-confidence full M1 route |
| 4 | new reference optic or body | at least several hundred dollars, plausibly much more | unnecessary unless the existing converter-on path fails sampling or transfer |

**Bottom line.** A new camera or lens is not presently required. A new
capture is required. Do not buy or fabricate anything before the `$0`
shared-optic rehearsal in §6.6. A concealed coded artifact remains the
strongest route to the target-independent claim described in §4.6, but it is a
fallback if the one-use stochastic patch cannot pass the physical
predictability, population or transfer gates. Without that stronger
provenance, the first lawful result remains explicitly target-conditional.

### 6.6 Owner-facing `$0` shared-optic capture specification

> **OWNER ACTION — CAPTURE REQUEST DRAFT.** This is the cheapest surviving
> route. It needs no new lens, teleconverter, body or fabricated calibration
> target. The orchestrator's bench sheet remains authoritative and must
> incorporate these requirements before shooting.

#### Physical subject

Use one rigid, stationary plane carrying both:

1. the existing grid or slide marks needed to measure magnification,
   registration and field position; and
2. a coplanar, one-use, nonperiodic stochastic patch large enough to leave at
   least `2048 x 2048` scored native pixels before guards.

The patch may be existing matte fibrous paper, ground-glass texture, random
speckle or another physically stochastic microtexture already on hand. It must
not be a public checker, ruler, Siemens star, repeated textile or semantic
image. Its exact specimen and orientation must be chosen after renderer
binaries and settings are frozen. Site locations are generated from a frozen
seed and input-only geometry; the photographer does not hand-pick sharp
features.

**Equipment assumption:** the repository confirms the camera, lens and
converter, but it does not confirm that the owner already has a suitable
stochastic patch. `$0` is therefore conditional on finding one among ordinary
materials already on hand; otherwise the next-cheapest action is to buy a
commercial random-speckle sheet, not a second optic.

This is not equivalent to the engineered panel in §6.4. It can support the
narrow statement:

> On this frozen renderer and this one-use stochastic target population,
> higher-sampling reference agreement improved without a transfer,
> flat-null or unexplained-structure regression.

It supports the broader anti-prediction claim only if the registered physical
target-eligibility test shows 64 nonduplicated guarded sites, adequate
reference power in all 16 cells and no reusable/repeated pattern. Failure
means `TARGET_INELIGIBLE`; it is a reason to fabricate the §6.4 panel, not to
select friendlier sites.

#### Existing optical path

**Repository-confirmed equipment:** Sony A7C II, Sony FE 100 mm F2.8 Macro GM
and communicating 2x Viltrox teleconverter.

1. Capture `R1/R2` with the converter installed at the measured
   maximum-reproduction state.
2. Remove the converter without moving the subject. Reframe by axial camera
   motion only.
3. Capture the scored A/B brackets at a `1.32x` target and never above
   `1.33x`.
4. Measure both reproduction ratios from common target periods. Proceed only
   if the frozen interval gives
   `LCB95(M_reference / M_scored) >= 2.0`.

Do not use nominal lens labels as the ratio. `2.8 / 1.4 = 2.0` is not an
operational margin; on the measured rig the conservative `2.7015 / 1.40`
ratio is only `1.9296`.

#### Shot list

The surviving inverted block is:

| role | frames |
|---|---:|
| converter-on fixed-focus reference, near/mid/far | `3 x 32 = 96` |
| converter-off `sw4-A/B` | `2 x 55 = 110` |
| converter-off `sw10-A/B` | `2 x 27 = 54` |
| converter-off reset/start/end fixed-focus witnesses | `60` |
| converter-off flat A/B and dark A/B | `4 x 32 = 128` |
| **added inverted block** | **`448`** |

The current wider request totals `891` frames after replacing its superseded
reference block. Do not improvise frame counts from this summary; the
orchestrator-owned capture request defines the complete order and all
converter-on calibration already present in that session.

Reference bursts are fixed-focus exposures, not a stack. Near, middle and far
positions cover the tilted subject without allowing a stacking algorithm to
construct its own truth. Odd and even reference halves use different
converter-on A/B masters. Converter-off A and B each use their own new
flat/dark masters. No master crosses optical state, repeat or sitting.

#### Hard acquisition predicates

The same-prime path is usable only if all hold:

- fresh physical exposures in every output and reference stream;
- IBIS and OSS off, camera-linear 14-bit RAW, fixed ISO/exposure/white balance;
- no shared flat or dark master between reference/output or A/B lineages;
- a different sensor footprint after the physical scale change;
- blank-residual cross-correlation `<=0.05`;
- reference-repeat coherence and tone/rail eligibility;
- stronger reference transfer in every registered cell;
- at least 64 common guarded stochastic sites;
- `LCB95(M_reference / M_scored) >= 2.0`; and
- no crop, digital zoom, upsample, source oracle or output-derived site
  selection.

Any failed predicate returns an explicit non-numeric state. It is not repaired
after inspection.

#### Cost, lead time and owner prohibitions

Incremental optical cost is **`$0`**, high confidence, because all named
camera equipment is repository-confirmed. Target cost is **`$0` if a suitable
ordinary stochastic material is already on hand**, medium-low confidence
because ownership is not recorded. Lead time is one non-holdout rehearsal
plus analysis, then a separate uninterrupted scored sitting; the repository
does not support an honest duration estimate.

Do not:

1. buy a second optic or commission a target before the `$0` rehearsal fails;
2. move the subject between converter-on reference and converter-off scored
   arms;
3. inspect any rendered or metric outcome once the scored sitting begins;
4. reuse rehearsal subjects, flats, darks, references or selected sites in the
   score;
5. let `sw4` serve as both improvement and truth; or
6. report information beyond the shared prime's passband as object truth.

### 6.7 Authorized slide session: what it can and cannot commission

**VERIFIED FROM REPOSITORY INVENTORY, NOT YET FROM `D:\`.** The authorized
development session contains one `tilted-sw4` ladder, one `tilted-sw10`
ladder, one three-exposure flat ladder and one different-geometry all-axis
ladder. The repository records coarse `FocusPosition2` ranges `[57,59]` for
both tilted stacks, but M135 has not yet independently read the files.

**DERIVED.** Real photons and fresh downstream noise make `sw4` versus `sw10`
a valid **pre-sensor intervention arm** if their ranges are in fact matched.
They do not make it a self-contained `J_TR` arm. The session has no registered
higher-sampling fixed-focus `R1/R2`, no two A/B repeats per step width and no
four disjoint calibration lineages. Using `sw4` as its own reference would
mechanically favor the alleged improvement.

The physical run was preregistered before any M135 access in
`experiments/M135-slide-physical-commissioning/PREREGISTRATION.md` at commit
`0d672863`. Its lawful outcomes are separate:

- metadata and image-derived focus ranges match or do not;
- `REAL_OPTICAL_ARM_PRESENT` or absent;
- full `J_TR` is identifiable or `REFERENCE_ROLE_ABSENT`; and
- the flat source diagnostic is quiet or not quiet.

Until the host lock is released and that run completes, no slide outcome is
claimed. If the inventory is as documented, the expected honest result for
the full ratio is `REFERENCE_ROLE_ABSENT`, not an invented
`J_TR(sw4)/J_TR(sw10)` value.

## 7. Frozen challenge battery and outcome

**VERIFIED.** The initial battery was frozen in commit `053ec124`. Three
pre-outcome amendments corrected under-execution and tightened lineage.
Amendment 4 then froze the mandatory matched-flat certificate and
spectrally-shaped noise plant before their first outcomes; amendment 5 fixed
only a four-versus-sixteen-element potency-record shape error after the first
attempt stopped before gate evaluation or artifact write. Amendment 6 then
hardened an invalid-shape refusal without changing valid-input arithmetic; its
replacement artifact was byte-identical. No threshold was relaxed
(`experiments/M135-detail-instrument/AMENDMENT-1.md:1-22`;
`experiments/M135-detail-instrument/AMENDMENT-2.md:1-28`;
`experiments/M135-detail-instrument/AMENDMENT-3.md:1-26`;
`experiments/M135-detail-instrument/AMENDMENT-4.md:1-89`;
`experiments/M135-detail-instrument/AMENDMENT-5.md:1-13`;
`experiments/M135-detail-instrument/AMENDMENT-6.md:1-16`).

| Control | Expected direction | Frozen bar | Final |
|---|---|---|---|
| Identity | tie | max absolute ratio error `<=1e-12` | **VERIFIED PASS**, exact `1.0` |
| Fresh-noise null | tie in expectation | mean-log 95% CI contains 1 and lies in `[0.95,1.05]` | **VERIFIED PASS**, `[0.992500,1.001429]` |
| Pre-noise blur | down | q95 ratio `<0.90` | **VERIFIED PASS**, `0.631511` |
| Genuine optical improvement | up | q05 ratio `>1.10` | **VERIFIED PASS**, `1.241840` |
| Post-render USM | no information win | max ratio `<=1.01`, congruence error `<=1e-10` | **VERIFIED PASS**, max `1.0000000000000007` |
| USM sample-size ladder | same bar at 64/128/256/512 | previous bar unchanged | **VERIFIED PASS**, max error `3.33e-16` |
| Post-render blur | `J` tie, `T` down | `J` error `<=1e-10`, `T` q95 `<0.95` | **VERIFIED PASS**, `J=1`, `T=0.687470` |
| Gamma-3 + PCHIP | tie/refuse | every ratio `[0.99,1.01]` | **VERIFIED PASS**, `[0.999997811,1.000001928]` |
| Logistic + PCHIP | tie/refuse | every ratio `[0.99,1.01]` | **VERIFIED PASS**, `[0.999958140,1.000030663]` |
| Added independent noise | down | q95 ratio `<0.90` | **VERIFIED PASS**, `0.468175` |
| High-band noise-only gain | down, never promote | q95 ratio `<0.90`, zero promotions | **VERIFIED PASS**, q95 `0.549007`, zero promotions |
| Common A/B artifact absent reference | down and residual up | `J` q95 `<0.90`, `U` increase q05 `>0.05` | **VERIFIED PASS**, `0.404241`, `+0.469309` |
| Deterministic hallucination absent reference | down/no promotion | q95 ratio `<0.95` | **VERIFIED PASS**, `0.872049` |
| Averaging trap | possible `J` up, transfer veto | `T` q95 `<0.98`, zero promotions | **VERIFIED PASS**, `J` q05 `1.808783`, `T` q95 `0.832604`, zero wins |
| Angle relabeling | tie | max error `<=1e-10` | **VERIFIED PASS**, `4.44e-16` |
| Flat reference | no number | `NO_DETAIL` 128/128 | **VERIFIED PASS** |
| Matched flat on every valid arm | near-zero first-class ratios | information/output `<=0.10`, reference structure `<=0.25` per run | **VERIFIED PASS**, worst information/output/reference `0.002320 / 0.096199 / 0.001149` |
| Structured false flat / common flat artifact | refuse | `FLAT_NULL_FAILED` | **VERIFIED PASS**, structured ratios `1/1/1`; common artifact 128/128 |
| Missing flat | refuse | `MISSING_FLAT_CONTROL` 128/128 | **VERIFIED PASS** |
| Predictable target | no number | `PREDICTABLE_TARGET` 128/128 | **VERIFIED PASS** |
| Site-permuted reference | no number | no `OK` in 128/128 | **VERIFIED PASS**, `NO_EVIDENCE` 128/128 |
| Clipping | refuse | `NONLINEAR_OUTPUT` | **VERIFIED PASS**, 3.027% rail hits |
| 8-bit quantization | refuse | `LOW_BIT_DEPTH` | **VERIFIED PASS** |
| Shared calibration / flat FPN | refuse | `SHARED_REFERENCE` | **VERIFIED PASS** |
| Checker wrong-answer plants | checker fails | all three mutations rejected | **VERIFIED PASS** |
| Missing provenance | refuse | `MISSING_LINEAGE` | **VERIFIED PASS** |

**VERIFIED.** Full numerical output is in
`experiments/M135-detail-instrument/commission.json:1-1005`; the concise
commissioning account is
`experiments/M135-detail-instrument/RESULTS.md:1-197`.

**VERIFIED.** A read-only independent verifier reran the original battery and
citation audit, reproduced the postfilter identity, checked C0-C21 and the
freeze commits, and reported no defect
(`experiments/M135-detail-instrument/VERIFICATION.md:1-40`).

**VERIFIED.** The amended run passed all 25 gates. Every pre-amendment
information summary, transfer summary, common-residual summary, tone result,
sample-size result, permutation count, checker result, averaging count, and
C0-C21 Boolean reproduced exactly against the preserved prior artifact.
The added noise plant had squared upper-band gain `5.0458`, reduced `J_TR` to
q95 `0.5490065676630667`, and produced zero promotions. Its worst
flat/detail information and output-repeatability ratios were
`0.0023196142160268125` and `0.09619849966263185`
(`experiments/M135-detail-instrument/commission.json:124-133,400-510,980-1005`).

**VERIFIED.** A separately implemented verifier that does not import the
commissioning harness passed 20/20 checks: exact preservation of every
pre-amendment result family, all three flat bars, both positive flat-failure
plants, missing-flat refusal, the M137 source values, noise-plant potency, and
a fresh 128-site direct API probe including malformed-shape refusal
(`experiments/M135-detail-instrument/flat-verification.json:1-82`;
`experiments/M135-detail-instrument/VERIFICATION.md:42-73`).

**VERIFIED.** The battery includes both directions required by the brief.
Defect-only commissioning would have missed the averaging trap: its
information coordinate improved by about `1.87x`, but its transfer fell to
about `0.82x`, so the certificate produced zero promotions
(`experiments/M135-detail-instrument/commission.json:142-180,388-399`).

## 8. Admission decision

**VERIFIED.** **NO-GO for D8 as M1.** Its advertised numbers reproduce, but
its FRC/`R_SNR` channel certifies repeatability rather than delivered
resolution, `P_sig` is sharpening-sensitive, same-capture common mode fails
specificity, and its half-difference can reward averaging. D8 may remain an
offline diagnostic coordinate; it cannot qualify a comparator or produce the
D2 `"certified-acuity"` map.

**VERIFIED.** **GO** for the statistical architecture. It has:

- a realized-sample sharpening theorem;
- correct synthetic null, pre-noise blur, and improvement directions;
- a positive improvement control;
- a ≥64-site sharpening battery with an unchanged bar;
- a mandatory matched flat sentinel with first-class per-run ratios;
- explicit broadband and high-band noise-amplification, angle, clipping,
  quantization, permutation, common-mode, hallucination, periodic-target, and
  checker controls;
- typed refusal rather than near-zero ratios.

**VERIFIED.** **NO-GO** for declaring M1 admitted now. The final synthetic run
commissions the estimator, not the physical reference chain. The scorecard
requires an implementation and audit independent of the renderer
(`docs/proposals/2026-09-sota-scorecard.md`, M1 “Exact computation” clause);
this Python
implementation is independent, but the following physical facts remain
unmeasured.

**ASSUMED.** Admission requires one pre-registered physical rehearsal on
development material or a disposable target, followed by a sealed holdout. The
rehearsal must demonstrate the exact carrier extraction, the reference MTF and
sampling advantage, independent calibration, sensor-coordinate decorrelation,
registration, tone witness, 64-site power, matched featureless sentinels under
the same mode, and all output-format refusals.

**VERIFIED.** If the random-code target, higher-sampling reference, or
independent calibration cannot be acquired, no admissible reference-agreement
instrument exists under the named defeats. The final diagnostics prove why:
shared false truth and predictable truth are indistinguishable from real truth
after provenance is removed.

## 8.1 M138 consumer interface

**VERIFIED.** M138 now requires a bound M135 executable before any
corrected-gate candidate render. It invokes the checker itself under
`python -I`, verifies its transitive bundle and environment, rejects
campaign-supplied Booleans, and requires a complete per-capture state ledger.
Only `DETAIL_PASS` and `DETAIL_FAIL` may have Boolean entries;
`INSTRUMENT_INVALID` must not
(`experiments/M138-w1-gate-audit/corrected-gate-preregistration.md`, “M135
executable interface”;
`experiments/M138-w1-gate-audit/corrected-gate-contract.json`, `m135_detail`
contract object;
`experiments/M138-w1-gate-audit/adjudicate.py`, M135 detail-ledger validation
functions). It correctly reserves
`BLOCKED_DETAIL_INSTRUMENT` for an absent physical binding rather than calling
that a Phase-1 loss.

**VERIFIED.** The earlier M138 interface at commit `7fb925bf` omitted the
mandatory flat roles and accepted supplied Booleans. That historical
incompatibility was reported rather than worked around; M138 repaired its
contract before M135 built the adapter. No M135 threshold or refusal was
weakened to satisfy the consumer.

**VERIFIED.** M135 now supplies the versioned rule
`m135-detail-pass-v1`. It is one-capture-at-a-time and emits:

| status | `detail_pass` | meaning |
|---|---:|---|
| `DETAIL_PASS` | `true` | valid applicable capture; every hard gate passes |
| `DETAIL_FAIL` | `false` | valid applicable capture; at least one preservation gate fails |
| `NOT_APPLICABLE` | `null` | capture absent from the frozen M135 detail ledger |
| `INSTRUMENT_UNBOUND` | `null` | physical M135 rule is not bound |
| `INSTRUMENT_INVALID` | `null` | registered input, lineage, flat, or bootstrap record is invalid |

The consumer may not coerce `null` to `false`
(`experiments/M135-detail-instrument/CONSUMER-PREREGISTRATION.md:24-42`;
`experiments/M135-detail-instrument/comparison-contract.json:1-19`).

**VERIFIED.** On one applicable capture, the checker recomputes its own
one-sided bounds from `10,000` paired-site draws at frozen seed `20260902` and
returns `DETAIL_PASS` only when:

```text
Q05(J_candidate / J_legacy)                        >= 0.98
Q05(T_candidate,k / T_legacy,k)                    >= 0.98 for every cell k
Q95(U_candidate - U_legacy)                        <= 0.02
```

Candidate and legacy must also each pass the mandatory three-ratio flat
certificate. These are preservation bars for Phase 1, not an M1 superiority
claim, and no capture or coordinate may compensate another
(`experiments/M135-detail-instrument/CONSUMER-PREREGISTRATION.md:67-107`;
`experiments/M135-detail-instrument/comparison_checker.py:190-353`).
The checker implements the current scorecard interface exactly; its `0.98`
values remain **UNRATIFIED inherited policy**, not owner-mandated constants.

**VERIFIED.** The frozen checker self-test passed `14 / 14` controls: exact
null, genuine improvement, three independent defects, candidate and legacy
flat failures, malformed payloads, inclusive boundary values, one-step
boundary failures, unbound, and not-applicable states. The rule manifest binds
the contract and checker hashes. A committed post-test amendment then rejected
JSON Boolean and numeric-string coercions without changing a bar; the
replacement self-test again passed `14 / 14`
(`experiments/M135-detail-instrument/comparison-verification.json:1-182`;
`experiments/M135-detail-instrument/comparison-rule-manifest.json:1-42`;
`experiments/M135-detail-instrument/CONSUMER-AMENDMENT-1.md:1-22`).

**VERIFIED.** `m138_adapter.py` implements the current M138 envelope without
changing the frozen core. It hash-verifies the request artifacts, checker
bundle, environment, physical preregistration binding, and comparison rule,
then invokes `comparison_checker.adjudicate` separately for every capture.
Valid pass/fail decisions alone enter `detail_pass_by_capture`; internal
invalidity remains in `detail_state_by_capture` with no Boolean. Request-level
invalidity and an unbound physical rule exit nonzero with no standard-output
verdict
(`experiments/M135-detail-instrument/M138-ADAPTER-PREREGISTRATION.md:18-166`;
`experiments/M135-detail-instrument/m138_adapter.py:313-380,469-685`).

**VERIFIED.** The pre-review implementation history remains available: the
amendment-1 run was `24 / 25` because of a malformed test-only unbound hash;
amendments 2-4 reached `25 / 25`, verified bundle-before-core ordering, and
removed cached-bytecode ambiguity by compiling the then-verified source bytes
directly. The expanded pre-review bootstrap battery passed `10 / 10`
(`experiments/M135-detail-instrument/m138-adapter-verification-run2-failed.json:1`;
`experiments/M135-detail-instrument/m138-adapter-verification-run3-pre-bootstrap.json:1`;
`experiments/M135-detail-instrument/m138-adapter-verification-run4-pre-source-loader.json:1`;
`experiments/M135-detail-instrument/m138-adapter-verification-run5-pre-m149.json:1`;
`experiments/M135-detail-instrument/m138-adapter-bootstrap-verification-run2-pre-m149.json:1`;
`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-1.md:1-24`;
`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-2.md:1-22`;
`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-3.md:1-25`;
`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-4.md:1-23`).

**VERIFIED.** M149's independent fixture review returned `SEND BACK` with two
CRITICAL, one HIGH, and two MEDIUM findings. The two critical findings shared
one root cause: artifact and core files were hashed, closed, and later reopened
for JSON parsing or execution. M149 demonstrated that replacement in that
window could convert registered `INSTRUMENT_INVALID` into `DETAIL_FAIL /
false`, or execute unregistered core bytes while truthfully reporting the
registered bundle hash. Its mutations also showed that the nominal `25 / 25`
suite did not prove 24 individual predicates could turn red. A passing count
was therefore not coverage.

**VERIFIED.** Amendment 5 imposes a read-once invariant. Each request,
artifact, bundle manifest, and bundle member is captured as immutable bytes;
the digest, JSON object, normalized text, and compiled core are all derived
from that same snapshot. The core's own hash and JSON helpers are rebound to
the verified snapshots. A replacement before capture produces a digest
mismatch, and a replacement after capture cannot change the consumed bytes.
That is the structural invariance argument: no scheduling assumption or finite
race campaign is needed
(`experiments/M135-detail-instrument/m138_adapter.py:35-124,315-391,430-477`;
`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-5.md:1-77`).

**VERIFIED.** Amendments 5-7 produced a `51 / 51` ordinary battery and a
`25 / 25` named helper-mutation result. Amendment 6 retains the initial
CRLF-anchor harness failure; amendment 7 retains the initial non-diagnostic
hash mutant. Those exact pre-threshold artifacts remain preserved
(`experiments/M135-detail-instrument/m138-adapter-verification-run6-pre-threshold-fix.json:1`;
`experiments/M135-detail-instrument/m138-adapter-mutation-verification-run1-pre-threshold-fix.json:1`;
`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-6.md:1-16`;
`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-7.md:1-17`).

**VERIFIED.** M149's independent re-attack accepted the read-once mechanism.
Its vulnerable controls first reproduced the artifact and source races; the
repaired tree then ran 512 attempts per race, with both exit paths exercised
and no invalid-to-fail conversion or sentinel execution. M149 independently
reproduced M135's 25/25 mutation and 7/7 race reports. The two CRITICAL TOCTOU
defects are therefore closed
(`experiments/M149-adapter-review/REATTACK-REPORT.md`, “Verdict” and
“Mechanism-level race closure”).

**VERIFIED.** The same re-attack returned a second `SEND BACK`: both
commissioning threshold-key mutations applied and survived all 51 checks.
Blur q95 `0.95` passed after replacing the strict `<0.90` lookup with `1.10`;
improvement q05 `1.00` passed after replacing the strict `>1.10` lookup with
`0.90`. Nineteen other entries in M149's 32-entry manifest hard-refused because
the read-once restructuring had moved their anchors. M149 manually mapped all
19 to still-present predicates; they were confirmed present but not exercised
by the stale automated manifest
(`experiments/M149-adapter-review/REATTACK-REPORT.md`, “HIGH defect —
commissioning threshold wiring is not load-bearing” and “Reconciliation of 19
ANCHOR_ERROR entries”;
`experiments/M149-adapter-review/threshold-mutation-probe-repaired.json`,
discriminating fixture result;
`experiments/M149-adapter-review/mutation-report-repaired.json`, mutation
summary).

**VERIFIED.** Amendment 8 makes both contract-key selectors named production
dependencies, directly probes their exact `0.90` and `1.10` values, and adds a
public-CLI commissioning request at the discriminating `0.95` and `1.00`
values. Both output controls must remain false. It also adds a stale
bundle-member refusal check. The amendment-8 ordinary battery passed `56 / 56`;
the local helper suite killed `27 / 27` substantive mutations and left its
inert mutation green
(`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-8.md:1-84`;
`experiments/M135-detail-instrument/m138-adapter-verification-run7-pre-config-path.json:1`;
`experiments/M135-detail-instrument/m138-adapter-mutation-verification-run2-pre-config-path.json:1`).

**VERIFIED.** Amendment 9 removes the remaining test-only threshold bypass.
The blur and improvement helpers no longer accept caller-supplied numeric bars.
Production and direct probes pass the same complete commissioning config; each
helper invokes its own production contract-key selector. Altered-config probes
detect replacement of either selector with the current numeric literal. The
current ordinary battery passes `58 / 58`; the local suite kills `29 / 29`
substantive mutations and leaves its inert mutation green
(`experiments/M135-detail-instrument/M138-ADAPTER-AMENDMENT-9.md:1-56`;
`experiments/M135-detail-instrument/m138-adapter-verification.json:1`;
`experiments/M135-detail-instrument/m138-adapter-mutation-verification.json:1`).

**VERIFIED.** Every one of M149's 19 stale anchors maps to a current predicate;
none was deleted. With the reanchored manifest, M149's unchanged harness
applied all 32 entries: **31/31 applied substantive mutations killed, 0
unapplied, one inert green**. Each threshold mutant failed four
direction-specific checks: strict-bound helper, exact-key, altered-config, and
marginal public-CLI. The blur and improvement failure sets are disjoint
(`experiments/M135-detail-instrument/m149-mutation-manifest-reanchored.json:1`;
`experiments/M135-detail-instrument/m149-mutation-verification.json:1`).

**VERIFIED.** The post-amendment race rerun was control-first. The vulnerable
artifact fixture reproduced at attempt 5/120; the vulnerable source fixture
reproduced with sentinel execution at attempt 2/120. Against amendment 9, 128
artifact attempts split 68 registered snapshots and 60 refusals, while 128
source attempts split 74 registered snapshots and 54 refusals. The current
M135 race harness also passed 7/7 at 128 attempts per race. No repaired arm
produced an unsafe result
(`experiments/M135-detail-instrument/m149-artifact-race-control.json:1`;
`experiments/M135-detail-instrument/m149-source-race-control.json:1`;
`experiments/M135-detail-instrument/m149-artifact-race-retest.json:1`;
`experiments/M135-detail-instrument/m149-source-race-retest.json:1`;
`experiments/M135-detail-instrument/m138-adapter-race-verification.json:1`).

**VERIFIED.** The checked-in physical binding remains `UNBOUND`; therefore
M135 currently emits no claim-bearing `detail_pass` for M138. Phase 1 remains
machine-readable `BLOCKED_DETAIL_INSTRUMENT` until physical M135 commissioning
passes and M138 binds the contract, checker, payload generator, capture
ledger, physical preregistration, and commissioning hashes. This is the
intended fail-closed outcome, not a detail failure.

**DERIVED.** The more precise program state is now
`BLOCKED_ON_PHYSICAL_COMMISSIONING_AND_FRESH_INVERTED_CAPTURE`. The statistic
and adapter exist, and §3.3 removes a second-optic purchase as a structural
prerequisite. What remains is the physical reference/output lineage, a
successful `$0` rehearsal, and a fresh uninterrupted capture. M138's existing
enum need not change to record that sharper diagnosis.

## 9. Could not determine

- **ASSUMED.** Whether the planned reference optic has stronger object-space
  transfer in every licensed cell.
- **ASSUMED.** Whether the one-use stochastic patch in §6.6 passes the
  nonduplication, 64-site and all-cell reference-power gates. The shared-optic
  ruling does not answer target eligibility.
- **VERIFIED.** Nominal `2.8 / 1.4 = 2.0` is not an admissible uncertainty
  margin on the measured rig. The conservative measured ratio at `1.40x` is
  `1.9296`; the `1.32x` target and `1.33x` hard maximum remain conditional on
  an actual `LCB95 >= 2.0`.
- **ASSUMED.** Whether direct inspection of the authorized slide confirms the
  repository's equal coarse encoder range and whether its image-derived
  coverage passes the frozen equivalence screen. M139's host-quiet lock
  currently forbids that run.
- **DERIVED.** If the authorized slide inventory is exactly the four recorded
  stacks, it cannot identify a full `J_TR(sw4)/J_TR(sw10)` contrast because
  the independent fixed-focus `R1/R2` and disjoint A/B roles are absent.
- **ASSUMED.** Whether 64 physical sites can resolve the proposed 2% M1
  superiority margin under real registration and photon noise.
- **ASSUMED.** Whether a scale/position change plus independent flats/darks
  drives blank-residual correlation below `0.05` on this body.
- **ASSUMED.** Whether the physical random-code print preserves independent
  phase/amplitude through manufacture and illumination.
- **ASSUMED.** Whether a vendor can deliver the dual-panel target and tone
  witness inside the planning cost/lead-time ranges in §6.4. Those figures are
  estimates, not quotations.
- **ASSUMED.** Whether the registered guard is wide enough for every
  comparator's undisclosed internal sharpening support.
- **ASSUMED.** The exact `M_work`, target scale, and focus-offset control
  remain unknowable until M147's real-optics preflight; no value in §6.4
  substitutes for that result.
- **ASSUMED.** Whether the 33-step physical PCHIP witness preserves the
  synthetic `<1%` result after RAW development and resampling.
- **ASSUMED.** Whether a physical target can supply flat sentinels below the
  frozen `0.25` reference-structure and `0.10` output-repeatability ratios at
  all registered tones and field positions.
- **ASSUMED.** Whether an adaptive proprietary renderer can recognize and
  special-case the sentinel. Randomized/concealed placement is required, but
  the synthetic campaign cannot prove concealment.
- **ASSUMED.** Whether the frozen per-run flat bars have adequate false-refusal
  power under real shot noise, residual gradients, and registration. They
  cannot be relaxed after observing the holdout. The per-cell
  `max(0, cross-power)` diagnostic has a finite positive null bias; under the
  synthetic high-band noise plant its worst output-repeatability ratio was
  `0.09619849966263185`, only `3.80150033736815%` below the `0.10` refusal
  bar **VERIFIED**.
- **VERIFIED.** A common post-render filter still ties on `J_TR`; the flat
  sentinel does not turn that invariant coordinate into an absolute
  presentation-sharpness score. `T_TR` remains a mandatory veto.
- **ASSUMED.** Whether the physical payload generator can produce stable
  per-capture `10,000`-draw bounds at the `64`-site floor without becoming
  `UNDERPOWERED`. The comparison checker is frozen; the physical generator is
  not yet implemented or commissioned.
- **ASSUMED.** Whether M149's next separate-author re-attack will find another
  bundle, environment, request-shape, byte-binding, threshold-wiring,
  coverage, or refusal-path defect. Its second review was `SEND BACK`; M135
  repaired the demonstrated threshold and stale-anchor defects and
  commissioned the repair locally, but does not count that as independent
  acceptance.
- **ASSUMED.** Whether `N=256` gives adequate rank and power for architecture B.
- **ASSUMED.** Whether repeat-pair FRC, after independent A/B calibration,
  can drive the held-out flat/dark ring residual below a frozen bar on the
  requested capture.
- **ASSUMED.** Whether normalized split SNR adds useful tuning power once the
  required independent transfer veto is imposed. SPLIT2 commissioned the
  held-out leakage guard, but geometry stopped the real measurement before
  any lawful tuning result existed.
- **ASSUMED.** M115 P18/P19 were source- and report-verified here, but their
  original machine-readable `s09_quanterror.json` was not present, so the
  `16x` quantisation under-report was not independently re-run in M135.
- **ASSUMED.** Whether the M55 executable contract will be revised to permit
  the independent-reference architecture the current scorecard requires.

## 10. Bottom line

**VERIFIED.** D8's normalized FRC/`R_SNR` claim is the family the
common-filter blindness result kills as a stand-alone absolute-detail
instrument. Its numbers reproduce; its inference does not. `P_sig` sees blur
and sharpening alike; ideal per-cell `R_SNR`/FRC sees neither common
post-render intervention, while finite windowed estimates retain uncontrolled,
unsigned implementation residuals. Same-capture common mode and the averaging adversary
independently rule out the claimed acuity certificate.

**VERIFIED.** The best available route is `J_TR` plus veto-only `T_TR` and
`U_TR`, measured against an independently captured, higher-sampling,
unpredictable reference. Sharpening cannot game `J_TR` because common
post-noise LSI gain cancels exactly in every observed and permuted coherence;
any apparent transfer gain cannot promote without an information gain. The
architecture is mathematically and synthetically commissioned. The
claim-bearing API now also requires a matched flat sentinel on every run. In
the amended 128-population battery, a `5.0458x` upper-band noise-power plant
reduced information to q95 `0.549007`, never promoted, and retained a worst
flat/detail information ratio of `0.002320`; structured and common-artifact
flats were refused **VERIFIED**.

**ASSUMED.** Physical feasibility is conditional, not established. The
reference and matched-flat lineages are parts of the instrument. A
shared-base-optic, magnification-differentiated reference is admissible under
the hard predicates in §3.3, so a second optic is not the blocker. The
authorized slide can test range, a real pre-sensor intervention and a flat
diagnostic, but does not contain the complete `R1/R2` and A/B lineage. M1
should remain `UNMEASURED` until the `$0` inverted physical rehearsal and
fresh capture pass without changing the frozen bars.

**VERIFIED.** M138 has a repaired, locally commissioned interface to bind later,
but not an independently re-accepted interface and not a result. The checked-in
rule is hashable, per-capture, and fail-closed, while its physical binding is
explicitly `UNBOUND`. The correct current Phase-1 state is therefore
machine-readable `BLOCKED_DETAIL_INSTRUMENT`, more precisely
`BLOCKED_ON_PHYSICAL_COMMISSIONING_AND_FRESH_INVERTED_CAPTURE`, not
`DETAIL_FAIL` and not `DETAIL_PASS`.
