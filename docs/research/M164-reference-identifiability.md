# M164 — higher-sampling optical-reference identifiability

Status: **CONDITIONAL ROUTE; SAMPLING-ONLY ADMISSION REJECTED; M1 REMAINS
UNMEASURED**

> **FORMAL FOLLOW-UP.** The complete estimator, simultaneous-inference family,
> scored-path witness contract, common-mode charge and commissioning results
> are now frozen in
> `docs/research/M164-reference-dominance.md` and
> `experiments/M164-reference-dominance/`. They supersede the schematic gate
> in section 2 below without changing this document's identifiability ruling.

## 0. Ruling first

**AMBIGUITY SURVIVES for the pair as stated.** A strictly higher subject-space
sampling rate does not by itself identify a post-render transfer `K`. For

```text
Y = K H_S X
R = H_R X,
```

the observed pair identifies only the composite transfer
`K H_S / H_R` on modes carried by the reference. If `H_R` is allowed to vary
over the admissible optical family, the companion world

```text
X'   = K X
K'   = I
H_R' = H_R K^-1
```

produces the identical pair. If `H_R` is physically fixed, the ambiguity still
survives for every nonidentity `K_null` satisfying

```text
H_R (K_null - I) X = 0.
```

The higher-magnification reference therefore breaks the earlier `X <-> KX`
ambiguity **only on an admitted reference-supported subspace**, not globally
and not because its sampling ratio exceeds `2.0x`.

**As written, section 3.1 does not yet discharge the hedge.** It names
reference-transfer and power checks, but it does not provide an executable
relative-information gate or an independently fixed transfer baseline. The
long capture must not be justified as identified by the seven-gate list until
that contract and its required physical witness are frozen.

This does not kill the truth-referenced route. It changes its admission
contract. The route is identified only if, before candidate outputs are read:

1. reference transfer is independently constrained rather than inferred from
   the candidate;
2. every licensed cell has reference support bounded away from the
   reference-noise and common-mode floor;
3. the reference is demonstrably **more informative than the scored physical
   path** in every licensed cell, with a simultaneous uncertainty margin; and
4. any claim that actually labels `K` separately from the scored optics has
   an independently measured baseline for `H_S / H_R`.

A failed cell is not averaged away. It is excluded by a frozen task definition
or makes the result `UNMEASURED`.

**INFERRED BY READING.** The proposal already says in section 0.1 that sampling
alone is insufficient and that the reference optic must have superior
object-space transfer. Section 3.1 gates 3 and 7 name “transfer sufficiency”
and reference power. They do not, however, define a relative
reference-versus-scored information statistic, its uncertainty rule, its
numerical margin, or the scored-path witness used to estimate it. Thus the
necessary idea is present, but the seven listed gates do not yet implement the
identifying condition.

## 1. What the pair can identify

### 1.1 Unknown reference transfer: the gauge merely moves

In one scalar Fourier mode, ignoring noise for the identifiability argument,

```text
Y_k / R_k = K_k H_S,k / H_R,k.
```

The data identify that product. They do not identify its three factors. Even a
full-rank and optically plausible `H_R` leaves the transformation

```text
(X, K, H_R) -> (KX, I, H_R K^-1)
```

unobservable. A sampling-ratio measurement constrains the coordinate grid; it
does not fix `H_R,k`.

**VERIFIED BY RUNNING.** The finite witness uses positive, monotone diagonal
transfer functions

```text
K       = diag(1, 1, 1.2, 1)
H_R     = diag(0.95, 0.80, 0.60, 0.40)
H_R'    = diag(0.95, 0.80, 0.50, 0.40).
```

Both `Y` and `R` agree exactly between the two worlds. The companion reference
transfer remains positive and monotone, so merely calling the reference
“optical” does not exclude it.

### 1.2 Fixed reference transfer: only its observable support is anchored

If the physical reference operator is held fixed across worlds, the companion
reference becomes

```text
R' = H_R K X.
```

The reference distinguishes the worlds exactly when
`H_R(K-I)X != 0`. It cannot distinguish a change in its nullspace. Near a
small singular value it distinguishes the worlds only to the extent that the
change exceeds reference noise, calibration bias, geometry error and finite
sample uncertainty.

**VERIFIED BY RUNNING.** With

```text
K_null = diag(1, 1, 1, 2)
H_R    = diag(0.95, 0.80, 0.60, 0)
```

the candidate and reference pairs are exactly identical under opposite
labels, despite `K_null != I`. Replacing the final reference gain by `1e-4`
moves the reference by only `4e-5`, below the planted `1e-3` uncertainty.
Replacing it by `0.20` moves the same reference coefficient by `0.08`, so the
probe is not frozen: an informative reference exposes the disturbance.

### 1.3 Sharing the objective narrows the truth

Writing the shared prime-lens transfer as `G`,

```text
R = A G X + eta
Y = K H G X + epsilon.
```

Under a validated independence gate, fresh exposures and disjoint calibration
keep independent downstream noise out of scene covariance, but they do not
invert a zero of `G`. Any shared zero, repeatable shared flare, or shared
aberration remains outside the identified object truth. The defensible
estimand is therefore information recoverable through the admitted shared-lens
passband, not unconstrained object detail.

This agrees with the existing M135 qualification. The present result adds the
missing formal consequence: support and information dominance must be
measured per licensed cell, not inferred from magnification.

## 2. Minimum sufficient admission condition

There are two different goals, and they require different conditions.

### 2.1 Reference-conditional comparative detail

For each frozen channel/frequency/orientation cell `k`, use independently
calibrated repeat observations of:

- the higher-magnification reference, `R_1,k` and `R_2,k`; and
- a **pre-render scored-path physical witness**, `S_1,k` and `S_2,k`, acquired
  through the scored optical state and never passed through the candidate.

After common subject-space calibration, estimate repeatable signal and
temporal noise:

```text
P_R,k = Re Cov(R_1,k, R_2,k)
N_R,k = 0.5 E |R_1,k - R_2,k|^2

P_S,k = Re Cov(S_1,k, S_2,k)
N_S,k = 0.5 E |S_1,k - S_2,k|^2.
```

Common-mode control bounds must be removed from, or conservatively charged
against, `P_R,k` and `P_S,k`; negative corrected values are not clipped into
success. One possible per-cell information coordinate is

```text
I_R,k = 0.5 log2(1 + P_R,k / N_R,k)
I_S,k = 0.5 log2(1 + P_S,k / N_S,k).
```

The exact estimator and minimum effect must be frozen on development data.
The admission relation must have this non-compensating shape:

```text
simultaneous LCB95( I_R,k / I_S,k ) > 1 + delta_I,k
AND
simultaneous LCB95( |H_R,k| / |H_S,k| ) > 1 + delta_H,k
AND
reference support and conditioning clear their frozen floors
for every licensed k.
```

`delta_I,k` and `delta_H,k` may be small, but they must be strictly positive
and physically powered. For vector cells, the corresponding requirement is on
the smallest generalized eigenvalue, not on an average eigenvalue. No strong
cell may compensate for a null or inferior one.

Call this gate **REFERENCE_INFORMATION_DOMINANCE**. It must use the frozen
physical witness, not a candidate render; otherwise candidate sharpening
participates in its own admission. Failure means `UNMEASURED`.

An exclusive band that the scored path physically cannot carry is sufficient
evidence of an information advantage, but it is not mathematically required
for lower licensed bands. Better transfer, noise and conditioning on the same
band can also establish strict information dominance. Conversely, additional
reference pixels with no corresponding optical information establish nothing.

Positive reference power is necessary but insufficient. For a unit-power
latent mode and noise power `0.01`, the constructed example has positive
reference information `1.160964` bits while the scored state has `1.660964`
bits, a ratio of `0.698970`, despite assigning the reference the proposal's
`2.031203x` sampling ratio. A second construction with stronger reference
transfer gives `2.350220` bits, a ratio of `1.414973`, proving that the
dominance gate can move.

### 2.2 Identifying `K` itself

Even an information-dominant reference identifies only the composite
`K H_S / H_R`. To call the residual specifically `K`, independently estimate

```text
q_k = H_S,k / H_R,k
```

from the pre-render scored-path witness and the reference, or from another
known-input transfer calibration. Then

```text
K_hat,k = (C_YR,k / C_RR,k) / q_k.
```

The `q_k` estimate, geometry, sites and uncertainty must be frozen before
candidate outputs are read. Without it, the joint `J_TR/F_TR` certificate can
still make a reference-conditional comparative claim because `J_TR` is
post-filter invariant and `F_TR` is veto-only, but it cannot honestly say that
the pair has uniquely estimated a digital `K`.

## 3. Ruling on the proposal's seven gates

**INFERRED BY READING.**

| Proposed gate | What it establishes | Identifiability ruling |
|---|---|---|
| 1. subject-sampling ratio | coordinate density | necessary geometry screen; not information |
| 2. split-reference SNR | absolute reference repeatability | necessary; does not compare reference to scored state |
| 3. reference focus and transfer sufficiency | names the right concern | not executable until it defines a per-cell relative transfer/information bound |
| 4. linear unclipped RAW | valid linear model | necessary |
| 5. reference-half agreement | reproducibility | necessary; agreement can include shared bias |
| 6. geometry/resampler sensitivity | mapping uncertainty | necessary |
| 7. nonperiodic reference power | absolute scene support | necessary; positive power need not dominate the scored state |

Accordingly, nothing in the enumerated seven gates currently **measures an
information ratio**. Gates 3 and 7 can host the repair, but their present prose
does not implement it. The proposal needs:

1. the named scored-path physical witness;
2. a frozen per-cell information/transfer ratio;
3. simultaneous uncertainty and common-mode correction;
4. a strict dominance margin; and
5. `UNMEASURED` on any failed cell.

This is a defect in the proposal contract, not permission for M164 to edit the
proposal or its live implementation.

## 4. The `2.0312x` margin

**DERIVED.**

```text
2.7015 / 1.33 = 2.031203x.
```

That clears the proposed geometric `2.0x` point bar by `0.031203x`: `1.560%`
relative to the bar, or `1.536%` of the achieved ratio. It does **not** clear
REFERENCE_INFORMATION_DOMINANCE. The reference could be defocused,
aberration-limited, noisy, or null in a licensed cell while retaining exactly
the same sampling ratio.

If `2.7015` and `1.33` are not already simultaneous conservative bounds, their
scale and registration uncertainty must fit inside that `0.031203x` margin.
The geometric gate should read `LCB95(ratio) >= 2.0`, not merely
`point_estimate >= 2.0`.

There is no identifiability discontinuity at exactly `2.0x`. Just below it:

- the current protocol may refuse by policy;
- a mode remains identifiable if the reference still has admitted transfer,
  information and conditioning there; and
- a registrar may instead narrow the licensed band so the reference-side
  footprint and antialias uncertainty pass.

Conversely, just above `2.0x` does not rescue a missing-information mode. The
proposal's existing `1.25x-2.0x` conditional band is therefore the right
logical shape. The physical information gate, not the integer-looking
sampling threshold, decides the theorem.

## 5. Odd/even halves are not automatically independent

Separate frames can have independent shot/read noise **conditional on** the
scene and session state. That is weaker than unconditional independence.
Let

```text
R_odd  = H_R X + C + eta_odd
R_even = H_R X + C + eta_even,
```

where `C` is a session-common nuisance such as residual fixed pattern, thermal
drift, focus drift, vibration phase, light drift or calibration leakage.
The law of total covariance gives

```text
Cov(R_odd, R_even)
  = E[ Cov(R_odd, R_even | X, C) ]
  + Cov( E[R_odd | X, C], E[R_even | X, C] ).
```

Independent exposure noise can make the first term zero while the second term
still contains both wanted scene covariance and unwanted `Var(C)`. A
split-reference cross-power estimator counts the latter as signal unless an
external control bounds it.

**VERIFIED BY RUNNING.** An exact 16-state construction has:

```text
conditional exposure-noise covariance     = 0
scene covariance                          = 1.00
shared nuisance covariance                = 0.04
total odd/even cross-covariance            = 1.04
featureless odd/even cross-covariance      = 0.04.
```

Thus separate exposures and disjoint flat/dark master *estimates* do not prove
statistical independence. The same sensor pattern and same-session latent
state can remain correlated after both calibrations.

The minimum operational contract is:

1. state independence conditionally: fresh shot/read noise given the frozen
   scene/session state;
2. test residual odd/even cross-covariance on matched featureless, dark and
   flat controls after applying the disjoint masters;
3. compare odd/even, contiguous-half and lagged/block splits to expose
   temporal autocorrelation or odd/even vibration aliases;
4. propagate a simultaneous upper bound on residual common-mode power into
   `P_R`, the transfer ratio and REFERENCE_INFORMATION_DOMINANCE;
5. resample uncertainty by physical site and burst/session, never as if the
   32 consecutive frames were 32 independent subjects; and
6. fail `UNMEASURED` if the frozen common-mode bound is exceeded.

M164's existing `0.05` blank-residual correlation is a candidate engineering
ceiling, not a theorem. It still requires preregistered power and confidence
handling. One uninterrupted session can support a claim conditional on that
session; odd/even splitting cannot establish between-session generalization.

## 6. Constructed witness and reproduction

No capture, holdout render or file under `D:\personal\macro` or
`D:\edited\macro` was opened.

Run:

```powershell
python experiments\M164-reference-identifiability\witness.py
```

**VERIFIED BY RUNNING.**

```text
PASS: 11/11 checks; verdict=CONDITIONAL_ROUTE_SAMPLING_ALONE_INSUFFICIENT; sampling=2.031203x; captures_opened=0
```

The output is
`experiments/M164-reference-identifiability/results.json`. The witness covers
the unknown-`H_R` gauge, the fixed-reference nullspace, a near-null below
uncertainty, an informative mode that moves, positive-but-inferior reference
information, strict information dominance, and the odd/even
total-covariance counterexample.

The check battery was also forced red by collapsing the informative reference
mode:

```powershell
python experiments\M164-reference-identifiability\witness.py `
  --plant-defect informative-reference-collapse `
  --output experiments\M164-reference-identifiability\planted-defect.json
```

Expected result:

```text
FAIL: 10/11 checks; verdict=CONDITIONAL_ROUTE_SAMPLING_ALONE_INSUFFICIENT; sampling=2.031203x; captures_opened=0
```

The planted artifact is diagnostic only and is not retained.

The independent lane-local verifier re-derives the finite witnesses, regenerates
the artifact byte-for-byte and exercises the red canary:

```powershell
python experiments\M164-reference-identifiability\verify.py
```

**VERIFIED BY RUNNING.**

```text
RE-DERIVATION: PASS 6/6 passed
ARTIFACT CONSISTENCY: PASS 4/4 passed
RED CANARY: PASS 2/2 passed
TOTAL: PASS 12/12 passed; 0 failed; 0 skipped
```

## 7. Final answer to the four questions

1. **Does higher sampling break `X <-> KX`?** Not by itself. Unknown
   reference transfer absorbs `K`; fixed reference transfer breaks the gauge
   only off its null/near-null space. The route survives conditionally on an
   admitted, independently constrained reference subspace.
2. **Minimum sufficient condition?** A genuine information ratio, not merely
   a pixel ratio: strict per-cell reference information and transfer dominance,
   with support, conditioning, common-mode bounds and an independent
   `H_S/H_R` baseline if `K` itself is to be named.
3. **Is `2.0312x` enough?** It passes only the proposed geometric point gate,
   with a small uncertainty margin. It says nothing decisive about optical
   information. Just below `2.0x` is not a theorem failure; it is a policy or
   band-licensing decision.
4. **Are odd/even halves independent?** Their shot/read noise may be
   conditionally independent. Their complete errors are not established
   independent until shared session and calibration covariance is measured,
   bounded and propagated.
