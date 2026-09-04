# M164 — reference-information dominance

Status: **FORMAL ROUTE SURVIVES ON QUALIFIED SHARED-OBJECTIVE PASSBAND;
PRODUCTION MARGINS UNFROZEN; M1 REMAINS UNMEASURED**

## 0. Verdict

**SHARED OBJECTIVE SUFFICIENT — formally, on its measured non-null passband.**

Let the common Sony objective contribute transfer `G`, the
reference-specific path contribute `A`, and the scored-specific path
contribute `B`:

```text
H_R = A G
H_S = B G.
```

In a frozen scalar frequency/orientation cell with `G_k != 0`,

```text
|H_R,k| / |H_S,k| = |A_k| / |B_k|.
```

The common objective therefore does not prevent strict reference dominance.
The added converter path may be better or worse; that is an empirical gate,
not an algebraic impossibility.

This cancellation is licensed only after the local shift-invariance and
cross-cell-leakage gates justify the scalar cell model. If `A`, `B` or `G`
materially mix registered cells, M171 must test generalized operator
dominance on `range(G)`; it may not apply the scalar ratio componentwise.
Failure to support either model is `UNMEASURED`.

The exception is exact and non-negotiable:

```text
k in null(G)  =>  H_R,k = H_S,k = 0.
```

No same-objective reference can identify absolute object detail in that
subspace. A near-null cell is operationally equivalent when its signal is
smaller than the simultaneous uncertainty and common-mode bounds. Such a cell
must be excluded by a frozen claim band or make the result `UNMEASURED`.

**No numerical licensed band can be named from the formal model alone.** The
actual Sony-plus-Viltrox and bare-Sony transfers have not been measured by this
lane. Formal analysis therefore neither orders a purchase nor certifies the
current optic. A different reference optic becomes necessary only if physical
measurement shows that the desired licensed family intersects the shared
objective's null/near-null space or the converter path fails strict dominance
there.

## 1. The estimand

### 1.1 What is identified without a known input

For physical site `j` and frozen cell `k`, write

```text
R_a,jk = H_R,k Z_jk + C_R,a,jk + eta_R,a,jk
S_a,jk = H_S,k Z_jk + C_S,a,jk + eta_S,a,jk,
```

where:

- `a in {1,2}` indexes independently calibrated replicate witnesses;
- `Z = G X` is the subject after the shared objective;
- each `S_a` represents the complete scored acquisition available to the
  renderer at that site, reduced only by a frozen candidate-blind sufficient
  linear operator;
- `C` is repeatable non-scene structure; and
- `eta` is zero-mean downstream noise.

With an unknown natural subject, the absolute scale transformation

```text
Z' = c Z
H_R' = H_R / c
H_S' = H_S / c
```

leaves all observations unchanged. Therefore the current optical-reference
design cannot separately estimate absolute `|H_R,k|` and `|H_S,k|`.
It can estimate:

1. information in each observed path about the common site population; and
2. the relative magnitude `|H_R,k| / |H_S,k|`, because the unknown
   `P_Z,k` cancels.

An implementation must report
`ABSOLUTE_TRANSFER_UNIDENTIFIED` unless it receives independently known input
coefficients or input power. It must not silently label a relative transfer as
either absolute transfer.

### 1.2 When absolute transfer is available

For an independently known complex input coefficient `Z_jk`, use the frozen
complex least-squares transfer

```text
P_bar,jk = (P_1,jk + P_2,jk) / 2

H_hat_P,k =
    sum_j P_bar,jk conj(Z_jk)
    -------------------------
          sum_j |Z_jk|^2
```

for `P in {R,S}`. Report `|H_hat_P,k|`; retain phase separately. If only the
known latent power `P_Z,k` is available, magnitude alone is

```text
|H_hat_P,k| = sqrt(P_signal,P,k / P_Z,k).
```

Known target geometry is not enough: the coefficients or calibrated
cell-power reaching the optical input must be known independently of either
image path. Otherwise only the ratio below is identified.

## 2. Frozen estimator for an unknown same-subject input

All definitions are per frozen cell `k`. A cell is the complete registered
tuple of subject region, reference strip, channel, frequency band and
orientation. The implementation flattens every claim-bearing tuple into one
family; no post-result deletion is allowed.

Before extraction:

1. apply the frozen camera-linear and radiometric calibration;
2. normalize path gain with an independent low-frequency/tone witness;
3. keep scored pixels native and apply only the frozen reference-side
   footprint map;
4. center complex coefficients across paired physical sites; and
5. use equal site weights.

For path `P in {R,S}`, define

```text
Q_P,k =
  Re [ sum_j (P_1,jk - mean P_1,k)
             conj(P_2,jk - mean P_2,k) / (n - 1) ]

D_P,k =
  1/4 sum_j |(P_1,jk - P_2,jk)
             - mean(P_1,k - P_2,k)|^2 / (n - 1).
```

`Q_P,k` is split-repeat power. Under conditional independence, `D_P,k` is the
downstream-noise power in the average `(P_1 + P_2)/2`.

The scalar form is licensed only when the frozen reduction is sufficient for
the complete physical acquisition in that cell. If the scored path supplies a
vector of observations with transfer `h_S,k` and noise covariance `N_S,k`,
its input information is instead proportional to

```text
h_S,k* N_S,k^-1 h_S,k.
```

M171 must either preserve that vector form or prove on known-truth development
data that its scalar reduction retains the cell's complete Fisher/NEQ
information. Comparing the reference to one convenient raw frame while the
renderer receives a larger stack is inadmissible.

Let `U_R,k` and `U_S,k` be simultaneous upper confidence bounds on the
absolute repeatable covariance measured in matched featureless, flat and dark
controls. Charge them adversarially:

```text
P_R,k^- = Q_R,k - U_R,k
N_R,k^+ = D_R,k + U_R,k

P_S,k^+ = Q_S,k + U_S,k
N_S,k^- = D_S,k - U_S,k.
```

This lowers reference signal, raises reference noise, raises scored signal and
lowers scored noise. It is deliberately four-way hostile to admission.
Nothing is clipped. Any nonpositive charged signal or noise makes the cell
`UNMEASURED`.

The frozen information estimates for dominance are

```text
I_R,k^- = 0.5 log2(1 + P_R,k^- / N_R,k^+)
I_S,k^+ = 0.5 log2(1 + P_S,k^+ / N_S,k^-).
```

These are Gaussian-equivalent second-order information coordinates. They are
literal mutual information only under the registered scalar Gaussian channel
model; otherwise the paper must call them covariance-information bits.

The relative transfer estimate is

```text
T_RS,k^- = sqrt(P_R,k^- / P_S,k^+).
```

The two point margins are

```text
m_I,k = log(I_R,k^- / I_S,k^+) - log(1 + delta_I,k)
m_H,k = log(T_RS,k^-)           - log(1 + delta_H,k).
```

The gate passes only when simultaneous lower confidence bounds on **every**
`m_I,k` and `m_H,k` are strictly positive.

## 3. Simultaneous inference and common-mode family

The complete confidence contract is:

```text
overall one-sided familywise alpha = 0.05
common-mode family alpha           = 0.025
dominance family alpha             = 0.025
```

The union bound therefore keeps the complete admission family at or below
`0.05`.

### 3.1 Common-mode family

The common-mode family contains both paths and every frozen cell:

```text
{ |Cov(C_R,1,k, C_R,2,k)|,
  |Cov(C_S,1,k, C_S,2,k)| : all k }.
```

Use a one-sided max-`t` cluster bootstrap over physical control sites. The
resulting simultaneous UCBs are `U_R,k` and `U_S,k`. The control family must
include the matched featureless, corrected-flat and corrected-dark classes;
use the maximum UCB across classes for each path/cell.

In addition to the four-way charge, require

```text
U_P,k / max(|Q_P,k|, power_floor) <= epsilon_common
```

for every path/cell. `epsilon_common` is frozen on development data. M164's
current `0.05` is a commissioning value, not yet a claim bar.

### 3.2 Dominance family

Resample paired physical macro-sites together. If the analysis has multiple
independent acquisition blocks, resample blocks outside sites; never
bootstrap individual frames as independent subjects.

The family is

```text
F = {m_I,k for all k} union {m_H,k for all k}.
```

Use `10,000` fixed-seed paired cluster-bootstrap draws. For each family member
`f`, compute bootstrap standard error `se_f`. For draw `b`, compute

```text
t_b = max_f (m_f,b - m_f) / se_f.
```

With `c` the upper `0.975` quantile of `{t_b}`, report

```text
simultaneous_LCB_f = m_f - c se_f.
```

Any invalid draw, zero bootstrap standard error, failed rank/conditioning
check or nonpositive charged term refuses the whole family. The reference
implementation uses seed `164177` and NumPy's `"higher"` quantile rule.

The no-compensation rule is literal:

```text
PASS iff
  common_mode_pass
  AND all_k simultaneous_LCB(m_I,k) > 0
  AND all_k simultaneous_LCB(m_H,k) > 0.
```

There is no mean, median, geometric mean, good-cell fraction or fallback
band. A strong cell cannot compensate for a null one.

## 4. Freezing `delta_I,k` and `delta_H,k`

The deltas are minimum claim-worthy advantages, not estimates from the scored
session. Production code must require a versioned calibration manifest
containing both arrays and refuse a default.

Freeze them using two disjoint development partitions with known planted
ratios:

1. Before reading either partition, freeze a finite positive candidate grid
   for information and transfer margins, the nuisance grid, the family, seed
   policy and selection rule.
2. On the tuning partition, choose the smallest candidate `delta_m,k` whose
   known-ratio estimator bias is no more than half that margin and whose power
   curve reaches the preregistered target for a plant at
   `1 + 2 delta_m,k`.
3. On the untouched validation partition, require:
   - familywise false admission at true ratio `<=1` no greater than `0.05`;
   - lower 95% binomial confidence bound on detection probability at the
     `1 + 2 delta` plant at least `0.90`; and
   - no sign reversal under any registered geometry, gain, tone,
     common-mode or resampler nuisance.
4. Freeze the validated deltas, calibration hashes and all failed cells before
   any scored output is rendered.

If no candidate meets all three validation predicates, that cell is not
licensed. The registrar may narrow the claim family before the holdout is
opened; it may not lower a delta or drop a cell after seeing a scored result.

The synthetic commission below uses `delta_I = delta_H = 0.08` solely to
exercise the gate. Those values are not proposed production bars.

Every choice is falsifiable:

- an equality or inferior plant can falsify specificity;
- a `1 + 2 delta` plant can falsify power;
- a common-mode plant can falsify the charge;
- a single weak cell can falsify no-compensation; and
- a second implementation can reproduce the fixed-seed artifact byte for
  byte.

## 5. Scored-path physical witness

`S_1,k` and `S_2,k` are not candidate or comparator renders. Each must
represent one complete, independently acquired scored-path input set for the
same physical site, before candidate merge, deconvolution, sharpening,
denoising or output resampling. The reduction from that complete set to
`S_a,k` must be frozen, linear, candidate-blind and sufficient for the licensed
cell. A single convenient frame is not a scored-path witness when the renderer
receives additional informative frames.

Formally, they must satisfy:

1. same latent site coefficient `Z_jk` and frozen optical state `H_S,k`;
2. the complete registered acquisition budget made available to the renderer,
   with no shared source frame and no shared flat/dark master estimate between
   replicates;
3. candidate-blind site, focus and geometry selection;
4. conditional zero covariance of downstream residuals after the registered
   scene/session state and calibration terms are removed; and
5. a matched control-derived simultaneous bound on any remaining covariance.

Different exposures are necessary but not sufficient. If consecutive frames
have equal residual-noise power `N` and correlation `rho`, then

```text
Q_S,k = |H_S,k|^2 P_Z,k + rho N

D_S,k = N(1 - rho) / 2

true noise of (S_1 + S_2)/2 = N(1 + rho) / 2.
```

Positive `rho` therefore inflates apparent signal and makes the
half-difference noise estimate too small. A common drift term adds the same
failure even when shot/read noise is conditionally independent.

Two consecutive frames from one burst fail immediately when they stand in for
a larger scored acquisition: they understate the information available to the
renderer. Even when they genuinely are the complete registered acquisition,
they are not independent evidence merely because they have different frame
numbers. They remain admissible only if:

- source-frame disjointness is hash-proven;
- residual autocovariance is bounded on lagged and blocked controls;
- odd/even, contiguous-half and lagged splits agree within a frozen
  tolerance;
- the common-mode UCB is charged as in section 2; and
- inference clusters at the physical site and acquisition-block level.

Failure changes the status to `UNMEASURED`; it does not enlarge an error bar
after the fact.

## 6. Commissioning results

The implementation is:

- `experiments/M164-reference-dominance/dominance.py`;
- `experiments/M164-reference-dominance/commission.py`;
- `experiments/M164-reference-dominance/commission.json`; and
- `experiments/M164-reference-dominance/verify.py`.

No capture, holdout render, M166/M171 artifact, or file under
`D:\personal\macro` or `D:\edited\macro` was opened.

**VERIFIED BY RUNNING.**

```text
PASS: 15/15 checks; legitimate=PASS; weak-cell=UNMEASURED; naive-improvement=PASS; charged-improvement=UNMEASURED; captures_opened=0
```

### 6.1 Legitimate dominance

**VERIFIED BY RUNNING.** A four-cell reference with genuinely stronger
transfer and lower independent noise passed:

```text
status                              PASS
minimum point information ratio     1.178134
minimum point transfer ratio        1.246404
minimum simultaneous log-I margin   0.046439
minimum simultaneous log-H margin   0.134297
cells admitted                      4/4
```

The gate therefore does not reject every reference.

### 6.2 One weak cell

**VERIFIED BY RUNNING.** Three strong cells and one weak cell produced:

```text
mean point transfer ratio            1.162436
weak-cell point transfer ratio       0.596372
cell verdicts                        PASS PASS PASS FAIL
overall status                       UNMEASURED
```

An average-only gate would have cleared the configured `1.08` ratio. The
implemented family refuses it, proving that strong cells cannot compensate.

### 6.3 Improvement-shaped common-mode plant

**VERIFIED BY RUNNING.** A repeatable non-scene term was added to both
reference halves. It moved both apparent quality numbers upward:

```text
                                  clean       contaminated, naive
minimum information ratio        1.226348    1.317332
minimum transfer ratio           1.017313    1.236808
naive overall status             UNMEASURED  PASS
```

The matched-control simultaneous UCB was `0.615261-0.625528` for planted
common-mode power `0.50`. After the four-way charge, the contaminated case
returned:

```text
status   UNMEASURED
failure  COMMON_MODE_BOUND
```

This is the mandatory improvement-shaped failure: a defect raises the numbers
and would pass the naive gate, while the commissioned gate catches it.

### 6.4 Verifier and red canary

Run:

```powershell
python experiments\M164-reference-dominance\verify.py
```

**VERIFIED BY RUNNING.**

```text
TOTAL: PASS 13/13 passed; 0 failed; 0 skipped
```

The verifier independently checks shared-objective cancellation, the common
null, the absolute-transfer scale gauge, byte-identical regeneration, source
hashes, no-compensation and the improvement-shaped rejection.
The committed commission artifact is byte-stable at SHA-256
`962EBEBA2ACCA2BC2964577EA8AAEE1C8A4509793BF31C7FE08E6B7F117CB031`.

Disabling the common-mode charge is the planted defect:

```text
FAIL: 13/15 checks; legitimate=PASS; weak-cell=UNMEASURED; naive-improvement=PASS; charged-improvement=PASS; captures_opened=0
```

It exits `1`; exactly the two charged-common-mode checks fail.

## 7. Exact proposal repair text

M164 does not edit the proposal. The formal defect can be repaired by
replacing gates 2, 3, 5 and 7 in section 3.1 with:

> 2. split-reference temporal SNR after a simultaneous common-mode covariance
> bound from matched featureless, corrected-flat and corrected-dark controls;
>
> 3. `REFERENCE_INFORMATION_DOMINANCE`: for every preregistered
> channel/frequency/orientation/field cell, a simultaneous one-sided 95% lower
> confidence bound must exceed the frozen positive margins for both
> `I_R,k / I_S,k` and `|H_R,k| / |H_S,k|`, using a candidate-blind pre-render
> scored-path physical witness; no cell may compensate for another;
>
> 5. reference-half conditional-independence and agreement, including
> source-frame disjointness, disjoint calibration-master estimates, lagged and
> blocked residual-covariance controls, and explicit charging of the
> simultaneous common-mode bound;
>
> 7. strictly positive, well-conditioned nonperiodic reference power in every
> claim-bearing cell after common-mode charging; any nonpositive, null,
> near-null or invalid-bootstrap cell yields `UNMEASURED`.

Add immediately after the list:

> Sampling density is a geometry screen, not evidence of information
> dominance. With an unknown same-subject input, only relative transfer is
> identified. Absolute `|H_R,k|` and `|H_S,k|` require independently known
> input coefficients or power; otherwise the implementation must report
> `ABSOLUTE_TRANSFER_UNIDENTIFIED`.

## 8. Is qualified `GX` worth publishing?

**Yes, if it is named exactly.** This is not a consolation prize. It is a
stronger and more falsifiable statement than any output-only detail score:

> On the frozen camera, shared objective, reference/scored optical states,
> target class and licensed passband, Strehl preserves more recoverable
> second-order information present through the qualified reference path
> `G X` than each registered comparator, while no truth-relative attenuation,
> overshoot, phase or unexplained-structure component exceeds its frozen
> noninferiority bound.

That can be a publishable conditional SOTA claim if comparator coverage,
holdout discipline and all other scorecard axes pass.

It cannot be shortened to:

- “recovers more absolute object detail”;
- “resolves frequencies beyond the shared objective's passband”;
- “identifies truth in a common optical zero”;
- “proves absence of sharpening”; or
- “generalizes beyond the registered optical state, subject population and
  licensed cells.”

For absolute `X`, the program needs independently known target coefficients or
an independently calibrated reference whose transfer covers the desired
object band. Merely buying a different lens is not sufficient; it is useful
only if its calibrated passband closes the shared null/near-null cells.
