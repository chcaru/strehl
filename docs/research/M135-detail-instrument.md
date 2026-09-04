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
| normalized split `R_SNR` | **Retain only as an auxiliary noise-efficiency coordinate** | Common gain cancels from signal and half-difference noise. That blocks noise-only sharpening, but makes common post-render blur equally invisible. |
| split-half FRC crossing/map | **Reject as absolute or “certified” acuity** | The same common-filter cancellation applies to normalized coherence; shared structure can also hold the curve high on a flat. |
| half-difference image | **Retain only as a diagnostic** | It omits common-mode artifacts and can be forced to zero by delivering the average of the two halves. |

The apparent conflict is therefore a conflation of estimands, not a
reproducibility dispute. M115's blur result belongs to **absolute `P_sig`**;
its sharpening result belongs to **normalized `R_SNR`**. No M115 scalar owns
both properties. D8's self-tuning objective was also never challenged with a
data-dependent tuning plant, so it is not commissioned even for that narrower
role (`docs/research/M-PHASE0-SPLIT.md:85-101`).

**VERIFIED.** The four D8 headline quantities reproduce from the preserved
byte-pinned rerun of historical M115 commit `77c8d5e9`: eight blur recoveries
span `0.9938215871-0.9973982082`; the largest normalized-SNR movement is
`0.537785%`; the naive gradient reading is `8.2513657x`; and the reported
power-consistency ratios span `0.999999999987-1.000000000000`
(`experiments/M135-detail-instrument/d8-audit.json:3-39`). The source hashes,
plant locations, and algebra also pass an independent M135 audit
(`experiments/M135-detail-instrument/d8-audit.json:40-97`).

Those accurate numbers do **not** prove D8's conclusion:

- M115 C2 Fourier-blurs every already-realized frame before the split
  (`experiments/M115-deconv-headroom/src/m115lib.py:461-483`;
  `experiments/M115-deconv-headroom/src/s03_instrument.py:159-211`). It then
  reads absolute `P_sig`, which necessarily follows the filter's power. It is
  not a fresh-noise optical-improvement control.
- C3 filters the two completed half outputs and reads normalized SNR
  (`experiments/M115-deconv-headroom/src/s03_instrument.py:214-244`). Its
  `0.54%` stability is the expected cancellation that also hides post-render
  blur. The source's `8.25x` value is specifically an **RMS-gradient** gain
  (`sqrt(gy1/gy0)`), not an energy ratio; the corresponding energy ratio is
  `68.085x`.
- `(P(A)+P(B))/2 = P_sig + P_noise` follows identically from
  `P_noise=P(A-B)/2`; it verifies arithmetic bookkeeping, not scene
  specificity (`experiments/M115-deconv-headroom/src/m115lib.py:441-458`).
- The exact historical rerun still fails its flat null: `MEAN=0.438734` and
  `WIENER_UNG=3.331288` against `0.25`. A direct common-mode plant reads FRC
  `0.972099`, so the registered D8 phase-0 gate returned
  `KILL — STOP/REMOVE RUST`
  (`docs/research/M-PHASE0-SPLIT.md:3-10,85-101`).

**VERIFIED.** The proposal's claimed C6 subtraction is not commissioned
evidence. C6 is labelled `"ARGUED"` and retains unresolved `[bar]`
placeholders; it says the proposed map *would* let D8 subtract fixed pattern
(`docs/proposals/2026-08-sota-path.md:1189-1214`). The later ledger audit
confirms that no axis tests the C6 calibration product
(`docs/research/M133-blocker-audit.md:1225-1231`). Likewise, a repeated bracket
supplies independent temporal noise but does not by itself erase same-sensor
DSNU/PRNU. Repeat-pair FRC still requires independent A/B calibration and a
held-out corrected-flat/dark residual gate
(`docs/research/M-FRC-VIABILITY.md:470-524`).

**VERIFIED.** D8 had already been run through its registered phase-0 gate and
killed; it was not an unintegrated solved answer. The proposal prose still
advertises it, but the current scorecard correctly drops same-frame split-half
FRC/SNR (`docs/proposals/2026-09-sota-scorecard.md:1119-1124`). The scorecard's
present state is therefore exactly as severe as the original brief says: M1
has `"NO ADMISSIBLE BAR — WITHDRAWN"`
(`docs/proposals/2026-09-sota-scorecard.md:392,489-535`).

## 0.1 Recommended replacement

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
   (`34cd4063:docs/research/M-FRC-VIABILITY.md:5-8`). The current source was
   revised: it calls common **post-noise** filtering an ideal null and says
   explicitly that pre-noise transfer is different
   (`docs/research/M-FRC-VIABILITY.md:381-390,426-430`). “Invariant to a common
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
   score” (`docs/proposals/2026-09-sota-scorecard.md:283-288`), while the M1
   card requires an independent-reference sentinel
   (`docs/proposals/2026-09-sota-scorecard.md:540-553`). A fresh score is not
   needed to design the statistic, but the missing reference role cannot be
   manufactured from existing pixels.

## 1. Evidence and holdout boundary

**VERIFIED.** No RAW, holdout render, or scorecard outcome was opened in this
lane. The five calibration-grid captures are burned as one
subject/session, and the six high-resolution-slide stacks are development
only (`docs/proposals/2026-09-sota-scorecard.md:272-288`).

**VERIFIED.** The scorecard permits those units to commission an instrument
but forbids using them for its score:

> “The burned grid and the development-only high-resolution slide may
> commission a new instrument but may never provide its scored value.”

(`docs/proposals/2026-09-sota-scorecard.md:551-553`)

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
(`docs/research/M39-verify-detail-metric.md:404-417`).

**VERIFIED.** This eliminates raw gradient magnitude, Tenengrad, Laplacian
energy, high-band power, and any positive “noise-subtracted energy” that can
turn selection noise or fixed pattern into detail. A lower bound of zero is
not protection: the halo post-mortem says, verbatim,
`"A metric can be BLIND to a defect ... or PERVERSE on it"`
(`experiments/BUILD-TRIAGE/halosens.py:16-27`). That is why this lane includes
both a planted defect and a planted improvement.

### 2.2 Split FRC, `sigpow`, and equivalent blur

**VERIFIED.** Same-capture split FRC was defeated by common structure. The
corpus records a flat ROI at `0.63-0.98` of the detail FRC and a 295x-noise arm
at `0.970`; changing threshold or ring count did not repair it
(`docs/research/SYNTHESIS.md:1001-1001,1051-1062`).

**VERIFIED.** M46's proposed repair, `sigpow = FRC * P_ring`, initially looked
responsive because it recovered common cross-power. M55 then found:

> “`sigpow` remains non-monotone in true resolution”

and

> “remains quadratic in photometric gain”

(`docs/research/M55-sigpow-verification.md:1-4`). Its split choice had
`50x` the leverage of the blur signal
(`docs/research/M55-sigpow-verification.md:282-297`). The candidate was not
merely noisy; its nuisance could dominate and reverse the intended quantity.

**VERIFIED.** M57's equivalent-blur statistic `dsig` did recover a planted
blur, but:

> “it fails its own noise null”

and independent noise moved a true zero by up to `0.343 px`
(`docs/research/M57-detail-metric-from-first-principles.md:34-64`). M57's
surviving conclusion was:

> “The defensible claim is two-dimensional”

(`docs/research/M57-detail-metric-from-first-principles.md:626-635`).

**VERIFIED.** That conclusion directly supports a non-compensating certificate.
Noise and transfer cannot safely be exchanged inside one scalar.

### 2.3 Slanted edge, `S_25`, and `Q25`

**VERIFIED.** Native `S_25` passed a 24-seed USM test and failed the unchanged
bar when expanded to 64 sites: `1.028294x`. It also moved `4.8400x` under
gamma, `18818.9045x` under logistic tone, and changed strongly with noise and
angle (`docs/proposals/2026-09-sota-scorecard.md:497-510`).

**VERIFIED.** The ordinal replacement did not solve sharpening:

> “licensed Q25 ... **5.560744x RED**”

and a genuine improvement moved in the wrong direction
(`docs/research/M-PHASE0-SLANTEDGE.md:205-219`).

**VERIFIED.** The reusable result is external, not intrinsic, tone handling:

> “Independent 33-step PCHIP linearisation is the one clean success”

with at most `0.0141%` affine/gamma/logistic movement
(`docs/research/M-PHASE0-SLANTEDGE.md:286-290`). The recommendation below uses
that witness and does not ask the detail statistic itself to solve tone.

### 2.4 Candidate 1: finite learned observer

**VERIFIED.** Candidate 1 started from the correct population data-processing
argument but lost it in the finite implementation. Its own report says:

> “The observed increase is a failure of this finite estimator, not of DPI.”

(`docs/research/M-CAND1.md:37-47`)

USM raised the estimate from `0.125099` to `0.137075 bits/tile`,
`1.095732x`; the planted degradation and improvement were correctly not run
after the stop (`docs/research/M-CAND1.md:49-63`).

**VERIFIED.** The lesson is narrower than “mutual information cannot work.”
An arm-specific learned decoder, finite feature bottleneck, regularization, and
optimization do not inherit the population theorem. The recommended estimator
uses a fixed closed-form covariance statistic whose USM invariance holds on
the realized sample, including its permutation correction.

### 2.5 Candidate 2: exact congruence without a lawful task

**VERIFIED.** Candidate 2 achieved the strongest prior algebraic result:
unclipped USM ratio `1.0000000000000009`, with covariance residual
`1.25e-15` (`docs/research/M-CAND2.md:14-20`).

**VERIFIED.** It still died because its protection stopped at linear
transforms. Gamma and logistic moved the score to `0.502893x` and `0.486741x`,
and the report says:

> “Congruence protects only invertible linear transforms”

(`docs/research/M-CAND2.md:28-44`).

**VERIFIED.** Candidate 2's later optical signs were valid on its supplied
synthetic task, but the natural captures could not instantiate the required
target/covariance/derivative/test populations. Worse, a zero-target input
returned `NUMERIC` in `16/16`, and ratios between null readings spanned
`0.1108` to `9.0270`
(`docs/research/M131-cand2-ruling.md:360-385,400-432`).

**VERIFIED.** The recommended architecture keeps Candidate 2's exact
congruence lesson, replaces its artificial class labels with an independent
physical reference, uses external PCHIP, and returns typed no-evidence states.

### 2.6 D8/M115 split-stack information and the phase-0 kill

**VERIFIED.** D8 explicitly promotes M115 into three product roles: a
per-stack tuning objective, a per-tile FRC `"certified-resolution map"`, and a
shipped half-difference null
(`docs/proposals/2026-08-sota-path.md:1694-1745`). Its supporting numbers are
real, but they belong to different statistics:

> “A tile where the halves agree to `0.35 cyc/px` *measured* that resolution;
> no model assumption can inflate it.”

(`docs/proposals/2026-08-sota-path.md:1717-1725`)

- absolute `P_sig` recovered the attenuation of an applied Gaussian filter at
  `0.9938-0.9974`;
- normalized `R_SNR` moved at most `0.54%` under common output filters;
- the largest reported naive reading was `8.25x`; and
- the power decomposition was `1.0000` within floating arithmetic
  (`docs/research/M115-deconv-headroom.md:82-107,130`).

**VERIFIED.** M135 re-derived those claims from
`M-PHASE0-SPLIT`'s exact historical rerun rather than trusting either prose
summary. The source blobs match the pinned manifest; all four headline
quantities reproduce
(`experiments/M135-detail-instrument/d8-audit.json:3-39,88-107`).

**VERIFIED.** The same rerun resolves the apparent contradiction:

```text
common output filter K:
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

**VERIFIED.** M115 itself exposes the operational consequence:

> “`MEAN` — which destroys contrast to 0.24–0.44× and is obviously the wrong
> answer — scores highest.”

(`docs/research/M115-deconv-headroom.md:148-150`)

The later coherence adversary makes the failure constructive: delivering
`(A+B)/2` produces perfect coherence and zero half-difference while losing
`29.6%` of delivered band power
(`docs/research/V-SOFTCHECK-coherence.md:130-159`). Thus D8 cannot detect the
brief's averaging defeat.

**VERIFIED.** Same-capture specificity also fails. M115 says:

> “nothing that uses one capture of one sensor can separate a static sensor
> pattern from a static scene.”

(`docs/research/M115-deconv-headroom.md:109-119`)

The registered D8 phase-0 lane then planted that failure directly: independent
noise plus a shared pattern read low-band FRC `0.972099`; the exact historical
null failed on `MEAN` and `WIENER_UNG`; and the lane returned:

> “the exact historical M115 numbers reproduce, but their controls do not
> transfer to the common-mode and data-dependent-tuning failures on which D8
> depends.”

(`docs/research/M-PHASE0-SPLIT.md:3-10,85-101,176-181,269-274`)

**VERIFIED.** D8's remaining confounds are not minor:

- quantisation error had cross-half correlation `+0.5109`, causing the
  difference channel to report `3.937x` noise where matched independent
  dither reported `63.311x`, a `16x` under-report
  (`docs/research/M115-deconv-headroom.md:320-340`);
- a separately rendered pair can confound selection with registration:
  `bee-1-cpl` had `8.885 px` median field shift and `1.354 px` local residual,
  sufficient for `87.3%` of observed incoherence
  (`docs/research/V-SOFTCHECK-selection-vs-alignment.md:89-97,123-134`);
- the proposal's C6 subtraction is only an argued future instrument with
  unresolved bars, not a commissioned correction
  (`docs/proposals/2026-08-sota-path.md:1189-1214`); and
- M115 commissioned a planted **defect**, not the separately required planted
  **improvement**. Its control therefore cannot distinguish a responsive
  detail metric from one that simply scores every departure downward.

**VERIFIED.** D8's three faces consequently separate as follows:

1. **Per-stack self-tuning:** no-go as commissioned product logic. Normalized
   SNR can remain a diagnostic coordinate, but not the sole objective; no
   data-dependent tuner plant transferred the result.
2. **Empirical acuity map:** refuted. Agreement to `0.35 cyc/px` certifies
   agreement, not delivered resolution.
3. **Shipped null:** useful as a view of differential noise, but incapable of
   exposing common-mode structure and therefore not ground truth.

This is why the recommendation uses an independent, differently sampled
reference and retains transfer and unexplained-repeatability as vetoes.

### 2.7 Revised repeat-pair FRC ruling

**VERIFIED.** The historical no-go said FRC was `"structurally blind to an
arbitrary-strength common linear post-filter, including blur"`
(`34cd4063:docs/research/M-FRC-VIABILITY.md:5-8`).

**VERIFIED.** The current report narrows that statement. It says the measured
blur was a `"post-noise output filter"` and therefore an intended null, while:

> “Pre-noise transfer is different: it attenuates or strengthens the latent
> signal before fresh downstream noise, so repeat correlation should move.”

(`docs/research/M-FRC-VIABILITY.md:381-390`)

Its current ruling is:

> “FRC is safe-by-null for common invertible postfilters, but it is responsive
> to pre-noise information transfer.”

(`docs/research/M-FRC-VIABILITY.md:426-430`)

**VERIFIED.** This does not rehabilitate D8. M115 C2 filters an already
captured noisy cube and reads absolute `P_sig`; it is not the fresh-downstream-
noise experiment on which the revised FRC argument rests. A future
independent-repeat FRC arm could measure pre-sensor information, but it would
still need a separate delivered-transfer veto and independent calibration.
The current repeat-pair report explicitly retains shared fixed pattern as a
structural confound
(`docs/research/M-FRC-VIABILITY.md:6-13,470-524`).

**VERIFIED.** The BUILD-SHARP claim that its edge statistic was `18,644x` more
responsive than ring FRC is directionally useful but dimensionally invalid as
a ratio: it divides micrometres by dimensionless FRC movement. Normalized to
their baselines, the comparison is about `+191.9%` edge width versus
`+0.1507%` FRC, and the FRC arm was a common post-noise filter
(`docs/research/M-FRC-VIABILITY.md:369-390`). It proves FRC cannot stand alone
as presentation resolution; it does not prove pre-noise blindness.

**VERIFIED.** FRC therefore survives only as a possible information/noise
coordinate after fresh-repeat geometry, calibration, null, and power gates.
It cannot by itself supply M1 or the scorecard's `98%` comparator-
qualification rule, because a deliberately post-blurred mode can retain
identical ideal FRC.

### 2.8 Governance conflict inherited from M55

**VERIFIED.** M55's older executable contract says
`uses_ground_truth=true` makes a candidate `"inadmissible for shipping"`
(`docs/research/M55-acceptance-spec.md:102-113`). The current scorecard,
however, explicitly requires a common-mode plant absent from an
`"independent reference"`
(`docs/proposals/2026-09-sota-scorecard.md:568-577`).

**ASSUMED.** The scorecard's later requirement supersedes that older B0 field
for M1. The owner must revise or version the M55 declaration contract before
this candidate can be mechanically admitted; setting the field false would
hide the architecture rather than resolve the conflict.

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

**ASSUMED.** Acquire four independent evidence streams:

- `Y1`, `Y2`: two complete same-input-role bracket captures, each rendered
  independently by the mode under test;
- `R1`, `R2`: two independently calibrated, fixed-focus, higher-sampling
  reference realizations of the same physical code cells.

The reference must use a different sensor footprint and at least `2.0x`
subject sampling, then be low-passed and resampled to the scored native grid.
Input-only fiducials freeze registration before any output is rendered.

**VERIFIED.** The scorecard already requires two `sw4`, two `sw10`, matched
dark/flat inputs, and a nonperiodic independent-reference sentinel
(`docs/proposals/2026-09-sota-scorecard.md:540-553`). It also caps all claim
frequencies at `0.25 cyc/native px`
(`docs/proposals/2026-09-sota-scorecard.md:555-560`).

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
(`experiments/M135-detail-instrument/instrument.py:175-214`).

**VERIFIED.** `T_TR` and `U_TR` are veto-only. This is required by the
scorecard's hard-gate rule:

> “Every primary metric is a hard gate. No win compensates for a loss.”

(`docs/proposals/2026-09-sota-scorecard.md:84-88`)

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
| Flat ROI | **VERIFIED** for independent noise: low reference-repeat coherence returns `NO_DETAIL`. **ASSUMED** for real shared sensor pattern unless the lineage gate passes. |

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
`experiments/M135-detail-instrument/commission.json:328-330`).

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
(`docs/research/M-CAND2.md:14-44`).

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
| Flat ROI | **ASSUMED** same reference-repeat and no-evidence gate. |

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
6. be photographed by an independently calibrated reference path at at least
   `2.0x` the scored subject sampling.

**ASSUMED.** Two output brackets and two reference halves are mandatory.
Reference and output must not share flat/dark masters. The reference must land
on a different sensor footprint after scale change or dither. A blank-residual
cross-correlation above `0.05` refuses the capture.

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
by capture then physical site
(`docs/proposals/2026-09-sota-scorecard.md:99-105`).

**ASSUMED.** A mode is information-qualified only if, separately on every
capture and pooled:

```text
LCB95(J_mode / J_best_registered) >= 0.98.
```

That is the scorecard's existing comparator-retention bar
(`docs/proposals/2026-09-sota-scorecard.md:93-98`), now attached to an explicit
information coordinate.

**ASSUMED.** Call one mode M1-ahead of another only if:

```text
LCB95(J_A / J_B) > 1.02
LCB95(T_A,k / T_B,k) >= 0.98 for every registered cell k
UCB95(U_A - U_B) <= 0.02
```

Ratios in `[0.98,1.02]` are parity. These are non-compensating: an information
gain cannot buy transfer loss or unexplained repeatable structure.

**ASSUMED.** The `1.02` superiority margin is paired with the scorecard's
existing `0.98` retention threshold rather than tuned from a result. It still
requires a physical power study before adoption; if the registered 64-site
design cannot resolve it, the outcome is `UNDERPOWERED`, not a relaxed bar.

## 7. Frozen challenge battery and outcome

**VERIFIED.** The initial battery was frozen in commit `053ec124`. Three
pre-outcome amendments corrected under-execution and tightened lineage; no
threshold was relaxed
(`experiments/M135-detail-instrument/AMENDMENT-1.md:1-22`;
`experiments/M135-detail-instrument/AMENDMENT-2.md:1-28`;
`experiments/M135-detail-instrument/AMENDMENT-3.md:1-26`).

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
| Common A/B artifact absent reference | down and residual up | `J` q95 `<0.90`, `U` increase q05 `>0.05` | **VERIFIED PASS**, `0.404241`, `+0.469309` |
| Deterministic hallucination absent reference | down/no promotion | q95 ratio `<0.95` | **VERIFIED PASS**, `0.872049` |
| Averaging trap | possible `J` up, transfer veto | `T` q95 `<0.98`, zero promotions | **VERIFIED PASS**, `J` q05 `1.808783`, `T` q95 `0.832604`, zero wins |
| Angle relabeling | tie | max error `<=1e-10` | **VERIFIED PASS**, `4.44e-16` |
| Flat reference | no number | `NO_DETAIL` 128/128 | **VERIFIED PASS** |
| Predictable target | no number | `PREDICTABLE_TARGET` 128/128 | **VERIFIED PASS** |
| Site-permuted reference | no number | no `OK` in 128/128 | **VERIFIED PASS**, `NO_EVIDENCE` 128/128 |
| Clipping | refuse | `NONLINEAR_OUTPUT` | **VERIFIED PASS**, 3.027% rail hits |
| 8-bit quantization | refuse | `LOW_BIT_DEPTH` | **VERIFIED PASS** |
| Shared calibration / flat FPN | refuse | `SHARED_REFERENCE` | **VERIFIED PASS** |
| Checker wrong-answer plants | checker fails | all three mutations rejected | **VERIFIED PASS** |
| Missing provenance | refuse | `MISSING_LINEAGE` | **VERIFIED PASS** |

**VERIFIED.** Full numerical output is in
`experiments/M135-detail-instrument/commission.json:1-399`; the concise
commissioning account is
`experiments/M135-detail-instrument/RESULTS.md:1-114`.

**VERIFIED.** A read-only independent verifier reran the battery and citation
audit, reproduced the postfilter identity, checked all 22 gates and freeze
commits, and reported no defect
(`experiments/M135-detail-instrument/VERIFICATION.md:1-36`).

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
- explicit tone, noise, angle, clipping, quantization, flat, permutation,
  common-mode, hallucination, periodic-target, and checker controls;
- typed refusal rather than near-zero ratios.

**VERIFIED.** **NO-GO** for declaring M1 admitted now. The final synthetic run
commissions the estimator, not the physical reference chain. The scorecard
requires an implementation and audit independent of the renderer
(`docs/proposals/2026-09-sota-scorecard.md:555-560`); this Python
implementation is independent, but the following physical facts remain
unmeasured.

**ASSUMED.** Admission requires one pre-registered physical rehearsal on
development material or a disposable target, followed by a sealed holdout. The
rehearsal must demonstrate the exact carrier extraction, the reference MTF and
sampling advantage, independent calibration, sensor-coordinate decorrelation,
registration, tone witness, 64-site power, and all output-format refusals.

**VERIFIED.** If the random-code target, higher-sampling reference, or
independent calibration cannot be acquired, no admissible reference-agreement
instrument exists under the named defeats. The final diagnostics prove why:
shared false truth and predictable truth are indistinguishable from real truth
after provenance is removed.

## 9. Could not determine

- **ASSUMED.** Whether the planned reference optic has stronger object-space
  transfer in every licensed cell.
- **ASSUMED.** Whether 64 physical sites can resolve the proposed 2% M1
  superiority margin under real registration and photon noise.
- **ASSUMED.** Whether a scale/position change plus independent flats/darks
  drives blank-residual correlation below `0.05` on this body.
- **ASSUMED.** Whether the physical random-code print preserves independent
  phase/amplitude through manufacture and illumination.
- **ASSUMED.** Whether the registered guard is wide enough for every
  comparator's undisclosed internal sharpening support.
- **ASSUMED.** Whether the 33-step physical PCHIP witness preserves the
  synthetic `<1%` result after RAW development and resampling.
- **ASSUMED.** Whether `N=256` gives adequate rank and power for architecture B.
- **ASSUMED.** Whether repeat-pair FRC, after independent A/B calibration,
  can drive the held-out flat/dark ring residual below a frozen bar on the
  requested capture.
- **ASSUMED.** Whether normalized split SNR adds useful tuning power once the
  required independent transfer veto is imposed; no data-dependent tuner
  plant has commissioned that use.
- **ASSUMED.** M115 P18/P19 were source- and report-verified here, but their
  original machine-readable `s09_quanterror.json` was not present, so the
  `16x` quantisation under-report was not independently re-run in M135.
- **ASSUMED.** Whether the M55 executable contract will be revised to permit
  the independent-reference architecture the current scorecard requires.

## 10. Bottom line

**VERIFIED.** D8's normalized FRC/`R_SNR` claim is the family the
common-filter blindness result kills as a stand-alone absolute-detail
instrument. Its numbers reproduce; its inference does not. `P_sig` sees blur
and sharpening alike, while `R_SNR`/FRC see neither common post-render
intervention. Same-capture common mode and the averaging adversary
independently rule out the claimed acuity certificate.

**VERIFIED.** The best available route is `J_TR` plus veto-only `T_TR` and
`U_TR`, measured against an independently captured, higher-sampling,
unpredictable reference. Sharpening cannot game `J_TR` because common
post-noise LSI gain cancels exactly in every observed and permuted coherence;
any apparent transfer gain cannot promote without an information gain. The
architecture is mathematically and synthetically commissioned.

**ASSUMED.** Physical feasibility is conditional, not established. The
reference lineage is part of the instrument, and existing development captures
do not contain that role. M1 should remain `UNMEASURED` until the physical
lineage and extraction rehearsal pass without changing the frozen bars.
