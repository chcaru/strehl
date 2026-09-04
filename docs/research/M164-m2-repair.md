# M164 — repairing M2's blur-rewarding statistic

Status: **NO OUTPUT-ONLY REPAIR; EXTERNAL-REFERENCE CANDIDATE HAS
AUTHOR-GENERATED DEVELOPMENT EVIDENCE; M167 DETAIL BATTERY COMMISSIONED BUT
HAS NOT EVALUATED THIS CANDIDATE; M2 REMAINS `UNMEASURED`**

No holdout was opened. No real image was scored. The commissioning used
synthetic arrays, one process, and one thread. Its elapsed time is operational
only and is not evidence.

## 0. Ruling

**VERIFIED.** The measured `0.571215x` blur reward is not primarily caused by
the local normalization in `R_box9`. It is caused by treating output
high-pass energy as noise without independently measuring the output's
transfer. Removing the local division leaves the same wrong direction.

**DERIVED.** No statistic that sees only two already-rendered outputs can
decide whether reduced high-frequency variation is removed noise or removed
signal. M164 can identify a restricted common-transfer relation, but it
cannot assign quality to that relation and does not cover arbitrary
scene-dependent renderer blur.

**PROPOSAL, INTERNALLY COMMISSIONED ONLY.** Replace the comparative residual
with a truth-normalized equivalent-input-noise coordinate, `Q_EIN`, computed
from two independent output repeats and M1's two independent truth-reference
halves. It is exactly neutral to a nonzero common per-cell transfer, responds
in the correct direction to added noise and genuine improvements, and keeps a
separately commissioned same-output detail/transfer admission gate mandatory.
M1 is the program's current proposed implementation of that gate, not the
unique mathematical route.

This is not an accepted M2 instrument. M167 owns the independent adversarial
battery; none of M164's self-authored gates can substitute for it. The
production cell/channel/bootstrap reduction must also be frozen, M1 must be
commissioned physically, and M165's pattern maps must exist. M2 therefore
remains `UNMEASURED`.

## 1. Diagnosis: why blur improves the current statistic

**DIAGNOSIS.** The measured historical statistic is
`R_box9(a) = sd(a / U9(a) - 1)`, where `U9` is a `9x9` box average. On the
licensed low-contrast ROIs, `U9(a)` is approximately the local mean `mu`, so
the statistic is approximately `sd((I-U9)a) / mu`. For a Gaussian blur `G`,
convolution commutes: `(I-U9)Ga = G(I-U9)a`. Since `|G(f)| <= 1`, blur
contracts the numerator's band energy, including both sensor noise and real
texture. The denominator barely moves. The normalization makes the residual
fractional and gain-insensitive; it is not the mechanism that rewards blur.
The missing quantity is independently anchored transfer.

The new synthetic pixel probe used M159's six-pixel texture construction:

| Probe | Blurred / unblurred |
|---|---:|
| exact fractional `R_box9` | `0.571180x` |
| additive `sd(a-U9(a))/mean(a)` with local division removed | `0.571318x` |
| median local mean | `0.999675x` |

M159's independently frozen realization measured `0.571215x`. The new result
does not replace it; it isolates the cause. Removing normalization changes
the ratio by only `0.000138`, while blur removes roughly `42.9%` of the
measured high-pass amplitude.

The scorecard's later `eta = MAD(BP(O-R))/sigma_ideal` sketch is not a solved
repair. It changes the numerator from output high-pass energy to disagreement
with a same-resolution held-out mean. That can catch blur, but the same
disagreement also charges a genuine transfer improvement because `R` carries
the old capture transfer. Section 5 records the mandatory improvement failure.

## 2. The M164-veto premise: one correction, same conclusion

The statement that M164 “fires on a common transfer applied to both outputs”
is not its exact contract. M164 tests whether one output is predicted by a
frozen common transfer of the other:

```text
B approximately equals K A.
```

A pure global Gaussian-blur relation in the registered family therefore
fires. The orchestrator's substantive conclusion is nevertheless correct.
A renderer can be blurrier through spatially varying selection, nonlinear
denoising, fresh downstream noise, or a transfer outside M164's frozen
family. Then `B` need not equal `K A`. M164 deliberately did not fire on
`48/48` spatially varying blur/sharpen negative controls, contributing to its
overall `0/144` legitimate-difference result.

Therefore M164 is useful defense in depth against post-render common filters,
but gating `R_box9` behind it does not repair M2. It closes one cheat family
and leaves the signal/noise identification problem open.

## 3. Why two rendered outputs are insufficient

Let the observed pair be `(A,B)` with `B=G A` for a smoothing operator `G`.
The identical bytes admit two incompatible explanations:

1. **degradation world:** `A` is faithful scene signal and `B` lost detail
   through blur;
2. **improvement world:** `B` is the faithful scene and `A-B` is unwanted
   noise or artifact removed by the second renderer.

Any deterministic statistic of `(A,B)` receives the same input in both
worlds. It cannot reject `B` in the first and reward `B` in the second without
an assumption or observation outside those outputs. M164 can say that a
restricted `G` relation exists; it cannot say which world is true.

Independent output repeats make temporal output noise identifiable:

```text
P_N = 0.5 E|Y1-Y2|^2.
```

They do not make the quality trade identifiable. Blur genuinely lowers
`P_N`. Calling that reduction “lower output noise” is mathematically true;
calling it a better image requires a separately anchored transfer/detail
condition.

**RULING.** There is no stand-alone, two-render-output repair for the owner's
detail-preserving comparative-noise claim without an assumption or observation
outside those outputs. Admissible identifying information could include an
independently anchored signal/transfer reference; a certified
featureless-target protocol whose scope concedes that spatial smoothing is not
tested; an explicitly validated signal/noise generative prior; or another
validated external transfer constraint. This list is non-exhaustive, and every
route inherits the scope and failure modes of its assumptions. The current
general comparator clause has not commissioned any such route.

## 4. Proposed external-reference statistic

The current proposed repair reuses M1's physical roles rather than inventing
another target. M1 remains the only usable route currently available because
adequate signal power, cross-fit independence, fixed-pattern calibration,
eligible common-render outputs and a commissioned alternative admission rule
are absent; M135 also records no archived same-site reference/output pair with
disjoint calibration. This is a scheduling fact, not a unique algebraic
requirement. At each registered frequency/orientation cell `k`, let:

- `R1`, `R2` be independent calibrated truth-reference observations;
- `Y1`, `Y2` be the coded-site coefficients from independent renders of
  disjoint repeat input blocks;
- `F_Y1`, `F_Y2` be the corresponding coefficients on M135's concealed,
  featureless sentinels in those same output images; and
- covariance be measured across at least 64 input-selected guarded sites.

Define:

```text
P_R(k)   = Re Cov(R1, R2)
C_YR(k)  = mean{Cov(Y1,R1), Cov(Y1,R2), Cov(Y2,R1), Cov(Y2,R2)}
T(k)     = |C_YR(k)| / P_R(k)
P_N(k)   = 0.5 mean |F_Y1-F_Y2|^2
EIN(k)   = sqrt(P_N(k)) / T(k)
q(k)     = EIN_candidate(k) / EIN_comparator(k).
```

`EIN` is equivalent-input noise amplitude: output temporal noise referred
back through independently measured transfer. It is not the old output
residual under another name. The synthetic model uses a signal-bearing pair
for both terms because its additive signal cancels exactly in `Y1-Y2`; the
physical instrument must use the concealed matched sentinels so M2 retains
its flat/defocused-ground scope.

This is deliberately **not** an ordinal or rank construction. The candidate
requires the independently witnessed 33-step PCHIP linearization before
coefficient extraction. That keeps the measured tone-invariance result
without buying it by discarding amplitude—the move already identified as the
leading sharpening risk.

For any nonzero common per-cell postfilter `K(k)`:

```text
P_N' = |K|^2 P_N
T'   = |K| T
EIN' = EIN.
```

Blur, USM and scalar gain therefore cannot improve this coordinate. This is
the same structural cancellation that makes normalized repeat SNR unsuitable
as an absolute detail metric, used here for its valid narrower purpose:
noise efficiency. M135 already retains `noise_to_explained` only as an
auxiliary noise-efficiency coordinate; `EIN` is its amplitude-domain form.

### 4.1 Proposed production reduction

This reduction is a **proposal**, not an owner-ratified bar:

1. use every cell in M2's complete registered `0.15–0.35 cyc/native px` band
   that passes M1's reference-power and alias controls; do not silently stop
   at this synthetic probe's `0.25` ceiling;
2. compute `q(k)` separately for R, G and B;
3. within a channel, use the equal-weight geometric mean of the
   preregistered cell ratios;
4. use the worst channel as the arm result;
5. bootstrap whole sites, preserving all cell/channel dependence;
6. require the simultaneous one-sided 95% upper bound to be `<=0.950`
   against **every** qualifying comparator, rather than selecting a quiet
   comparator after outcomes;
7. define the absolute `eta<=1.10` limb using `EIN` divided by the
   independently estimated ideal-mean input noise in the same reference
   units; and
8. refuse zero/weak transfer, insufficient reference power, failed M165
   calibration, correlated repeats, failed M1, or fewer than 64 sites. Never
   replace a failed denominator with epsilon.

The wording supported by this statistic would be “lower equivalent-input
noise at M1-qualified delivered transfer,” not unqualified lower raw output
variance. If the owner requires the latter literal estimand, blur safety is
impossible because blur truly reduces output variance.

## 5. Synthetic commissioning

The frozen run used `256` trials, `64` sites, three frequencies and four
orientations. All `12/12` preregistered gates passed.

**GOVERNANCE LIMIT.** These are author-generated development checks, not
acceptance evidence. They show that the implementation moves and that its
claimed algebra is present. Only M167's separately frozen battery may decide
whether the candidate survives the program's flat-null, blur, improvement and
sharpening requirements.

### 5.1 Null, degradation and mandatory improvements

| Arm | `Q_EIN` geometric mean | Range or directional count | Ruling |
|---|---:|---:|---|
| fresh equal-noise movable null | `1.000535` | `0.927653–1.077433`; `125` below / `131` above one | non-degenerate and centered |
| added-noise degradation, `1.5x` RMS | `1.499654` | `256/256` worse | correct |
| same-transfer denoising improvement, `0.5x` RMS | `0.499663` | `256/256` better | correct |
| pre-noise optical blur, sigma `1.05 px` | `1.747786` | `256/256` worse | correct |
| genuine pre-noise optical improvement, sigma `0.30 px` | `0.761504` | `256/256` better | correct |

The improvement arm is not post-render sharpening. Its stronger transfer is
applied before fresh downstream noise, matching the distinction M135
requires.

### 5.2 Common-transfer controls

| Arm | Naive output-noise ratio | Transfer ratio | `Q_EIN` |
|---|---:|---:|---:|
| post-render Gaussian blur, sigma `0.75 px` | `0.629621` | `0.629621` | `1.000000000000` |
| post-render USM, amount `0.75`, radius `1 px` | `1.399209` | `1.399209` | `1.000000000000` |
| scalar gain `1.0007x` | `1.000700` | `1.000700` | `1.000000000000` |

Maximum numerical departure from one was
`2.220446049250313e-16`. The omitted-transfer mutation is live: raw output
noise alone calls the blur a `0.629621x` improvement, while `Q_EIN` correctly
returns a tie.

### 5.3 Why a separate admission condition remains mandatory

A blur-plus-denoise arm used sigma `1.05 px` and one-third baseline
downstream-noise RMS. It measured:

```text
Q_EIN                 = 0.583120x
naive output noise    = 0.333398x
transfer              = 0.571748x
```

All `256/256` trials preferred its noise coordinate even though every trial
lost transfer. This is not a defect in the arithmetic: the arm buys enough
noise reduction to improve equivalent-input noise while discarding detail.
A separately commissioned information/transfer condition must decide whether
that trade is admissible. M1 is the program's current proposed implementation
and the only presently usable route for the missing-evidence reasons in
Section 4, not the only mathematical possibility. `Q_EIN` must never be used
as a quality score.

### 5.4 Why unnormalised same-resolution `O-R` is not the repair

The additional `64`-trial probe gave a held-out reference the same sigma
`0.65 px` capture transfer as the baseline:

| Arm | Cross-fit `MAD(BP(O-R))` ratio | Truth-error ratio |
|---|---:|---:|
| physical blur | `8.016759x` | `1.708224x` |
| genuine optical improvement | `10.817811x` | `0.067483x` |
| same-transfer denoising improvement | `0.789695x` | not applicable |

The cross-fit residual catches blur but scores the genuine optical
improvement more than ten times worse, even while its error to physical truth
falls to `0.067483x`. It therefore fails the mandatory improvement arm.
Replacing `R_box9` with this unnormalised same-resolution
`MAD(BP(O-R))` disagreement merely exchanges a loose-direction failure for a
conservative-direction failure.

This result does **not** refute covariance-normalized `Q_EIN` using the same
independent reference. They are different estimators. In the comparative
ratio, the common reference power and transfer cancel; a sufficiently powered,
independent same-resolution reference can therefore normalize relative
transfer. Two independent higher-resolution truth halves remain valuable for
absolute units, bias and power, but they are not algebraically mandatory for
comparative `q`.

### 5.5 M167 interface status

**VERIFIED FROM M167'S SERIALIZED RESULT.** M167's battery is now
`COMMISSIONED`, but it has not evaluated this candidate. Its measured candidate
set is the constructed oracle, D8, M137 band power, and the historical M2
`R_box9`; `Q_EIN` is absent. The frozen M167 input modes expose one completed
image, a completed repeat pair, or a future reference-bearing mode. `Q_EIN`
requires that last mode because it consumes independent truth-reference and
featureless-sentinel coefficients plus their admission lineage.

There is also a semantic boundary that must not be hidden by an adapter.
M167's `P4` is a resolution-instrument predicate: post-render blur must make
the candidate's scalar score strictly worse. `Q_EIN` is deliberately a noise
coordinate and is exactly invariant to the same common postfilter. Submitted
alone as a resolution score, it must fail `P4`; returning M1's refusal would
also fail the frozen predicate. Adding transfer to `Q_EIN` as a compensating
scalar would violate the scorecard's rule that the M1/M2 tuple has no aggregate
axis verdict.

The required independent test is therefore of the non-compensating pair:
M1 decides detail/transfer admission, then `Q_EIN` compares noise only among
admitted outputs. M167 can judge the first component; an independently frozen
reference-bearing M2 adapter/battery must judge the second. M164 did not alter
M167 or reconstruct its private latent truth to manufacture an apparent pass.

## 6. Current M1 dependency and verdict

M2's noise coordinate and M1's admission test have different jobs:

- `Q_EIN` asks how much temporal noise remains after referring it through the
  measured transfer;
- M1 asks whether the output retains enough independently verified real
  information and whether transfer or unexplained structure invalidates the
  comparison;
- M164 additionally refuses the restricted post-render common-transfer
  family.

The same output bytes, settings, calibration lineage and site set must bind
all three. A result may not take M1 from one mode and M2 from another.

**CURRENT VERDICT: `UNMEASURED`.** M1 has no admitted numerical bar or
physical truth capture, so no comparator qualifies through its envelope.
M165 also reports no pattern map. A perfect synthetic M2 statistic cannot
change either fact.

**JUDGEMENT — LAND THE CANDIDATE NOW, NOT THE CLAIM.** The repair is worth
retaining because it removes a known wrong-sign statistic, requires no
additional photons beyond the accepted M1 A/B/reference roles, and can be
presented unchanged to an independent adversary before the expensive capture.
It must not be promoted to the scorecard as commissioned production evidence
until M167 accepts it and the full `0.15–0.35` band, channel/reduction rule,
physical M1 gate, M165 maps and real-renderer controls pass.

## 7. Limits and routed defects

1. The synthetic commissioning uses ideal Fourier cells through
   `0.25 cyc/native px`; it does not license M2's full `0.15–0.35` band.
2. `Q_EIN` is exactly common-filter invariant only under the per-cell linear
   model. Spatially varying and nonlinear processing still require M1.
3. A/B differencing omits repeatable fixed pattern and common hallucination.
   M165 calibration plus M1's unexplained-structure/flat witnesses remain
   mandatory.
4. The current scorecard does not freeze ROI, cross-fit, channel, comparator
   selection or confidence reductions tightly enough for two implementers to
   reproduce one verdict. Section 4.1 is the proposed repair for
   orchestrator review; this lane did not edit the scorecard.
5. M164's existing M2 text calls its veto a “partial unblock.” That remains
   true only for the restricted postfilter refusal; it is not the comparative
   statistic repair.
6. The callable candidate is
   `experiments/M164-m2-repair/instrument.py`. Its fail-closed API requires an
   admitted M1 result, M165 pattern map, external 33-step tone witness,
   independent repeats, complete-band declaration, nonperiodic target
   lineage, and an explicit M164 verdict. Its existence is not acceptance.
7. M167's commissioned result currently covers historical `R_box9`, not this
   reference-bearing candidate. Its strict blur predicate and `Q_EIN`'s
   intended common-filter invariance cannot be made equivalent without
   collapsing M1 and M2 into a forbidden compensating score.

## 8. Reproduction

From the repository root:

```powershell
$env:OMP_NUM_THREADS='1'; $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'; $env:VECLIB_MAXIMUM_THREADS='1'; python -B experiments\M164-m2-repair\commission.py
python -B experiments\M164-m2-repair\verify.py
```

`verify.py` first reruns `commission.py` into a lane-local scratch artifact and
rederives all numerical checks from that fresh result, not from the committed
trial ratios. It separately checks byte identity with committed
`commission.json` and report anchors. It also constructs the finite two-world
witness `A=[0,0,1,0,0]`, `B=G@A`: the identical observation pair has SSE
`(0,0.375)` under degradation truth and `(0.375,0)` under improvement truth.
The output reports `REDERIVATION`, `ARTIFACT-CONSISTENCY` and `TOTAL` counts
separately, including failures and skips. A regeneration failure cannot print
`PASS`, and the scratch artifact is removed in every case. This remains
author-owned development verification, not M167 acceptance.

The verifier's live negative control is:

```powershell
python -B experiments\M164-m2-repair\verify.py --plant-defect theorem-label-collapse
```

It deliberately gives both latent worlds the degradation label. The theorem
check must report `RED`, the category and total counts must still reconcile,
and the process must exit `1`. Its exact commissioned output is retained in
`verifier-red.txt`.

Artifacts:

- `experiments/M164-m2-repair/PREREGISTRATION.md`;
- `experiments/M164-m2-repair/AMENDMENT-1.md`;
- `experiments/M164-m2-repair/commission.py`;
- `experiments/M164-m2-repair/CANDIDATE-CONTRACT.md`;
- `experiments/M164-m2-repair/instrument.py`;
- `experiments/M164-m2-repair/commission.json`;
- `experiments/M164-m2-repair/verify.py`;
- `experiments/M164-m2-repair/verification.json`; and
- `experiments/M164-m2-repair/verifier-red.txt`.

## 9. Sources

- `docs/research/M159-noise-clause.md`, §§3.2 and 5: exact `R_box9`
  definition, `0.571215x` blur challenge, and residual/noise distinction.
- `docs/research/M164-transfer-veto.md`, §§1, 7 and 10: restricted transfer
  family, `0/144` legitimate-difference result, and non-fire limitation.
- `docs/research/M135-detail-instrument.md`, §§0 and 0.2: normalized repeat
  SNR as an auxiliary noise-efficiency coordinate and the independent
  truth-reference architecture.
- `experiments/M135-detail-instrument/instrument.py:229-247`: existing
  `P_R`, cross-transfer, half-difference noise and `noise_to_explained`
  implementation from which `EIN` is derived.
- `docs/research/M166-bar-achievability.md`, M2: missing reduction and
  comparator-selection definitions.
- `docs/proposals/2026-09-sota-scorecard.md`, M2: current void status,
  `eta<=1.10`, comparator `UCB95<=0.950`, and M1 qualification dependency.
