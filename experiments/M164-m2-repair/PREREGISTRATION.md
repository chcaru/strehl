# M164 M2 repair — synthetic preregistration

Status: **FROZEN BEFORE EXECUTION; DEVELOPMENT ONLY; NO M2 SCORE**

## Question

Can the blur-rewarding output residual used by M2 be replaced by a comparative
noise statistic that is neutral to a common post-render transfer, responsive
to added noise, and responsive to a genuine improvement?

This experiment does not claim that an output-only repair exists. It tests a
candidate that deliberately uses the independent truth-reference roles
already required by M1.

## Estimand

For each registered Fourier cell `k`, two independent truth-reference
observations are `R1`, `R2`, and two independently rendered output repeats are
`Y1`, `Y2`. Covariance is taken across 64 independent sites after subtracting
the site mean:

```text
P_R(k) = Re Cov(R1, R2)
C_YR(k) = mean{Cov(Y1,R1), Cov(Y1,R2), Cov(Y2,R1), Cov(Y2,R2)}
T(k) = |C_YR(k)| / P_R(k)
P_N(k) = 0.5 mean |Y1 - Y2|^2
EIN(k) = sqrt(P_N(k)) / T(k)
```

`EIN` is equivalent-input noise amplitude, not raw output residual. For a
candidate `C` and comparator `B` on the same reference, the synthetic primary
ratio is

```text
Q_EIN = exp(mean_k(log(EIN_C(k) / EIN_B(k)))).
```

The cells are the 12 equal-weight frequency/orientation cells formed by
frequencies `{0.15, 0.20, 0.25}` cycles/native pixel and orientations
`{0, 22.5, 45, 67.5}` degrees. `Q_EIN < 1` means lower transfer-normalized
noise. A real instrument must refuse any cell that fails the M1 reference,
transfer, unexplained-structure, calibration, or power gates; it may not use
an epsilon denominator to manufacture a value.

For a nonzero common post-render transfer `K(k)`:

```text
P_N' = |K|^2 P_N
T' = |K| T
EIN' = EIN.
```

The invariant is intentional: post-render blur or sharpening cannot buy an
M2 win. It also cannot establish image quality. M1 remains the required
truth-based admission gate.

## Synthetic population

- seed: `164200`;
- trials: `256`;
- sites per trial: `64`;
- latent per-cell coefficients: circular complex Gaussian, unit RMS;
- independent truth-reference noise: `0.10` RMS;
- baseline output noise: `0.45` RMS;
- baseline optical Gaussian sigma: `0.65 px`;
- all BLAS thread variables fixed to `1`.

Every non-postfilter arm receives fresh downstream noise. Postfilter arms are
computed from the realized baseline outputs so the claimed algebraic
invariance is tested directly.

## Frozen arms and gates

| Gate | Arm | Frozen requirement |
|---|---|---|
| G0 | identity | maximum `|Q_EIN-1| <= 1e-12` |
| G1 | movable null: fresh equal-noise output | minimum `<1<` maximum and geometric mean in `[0.98,1.02]` |
| G2 | planted noise degradation: `1.5x` output-noise RMS | every trial `>1`; q05 `>1.20` |
| G3 | planted denoising improvement: `0.5x` output-noise RMS at unchanged transfer | every trial `<1`; q95 `<0.75` |
| G4 | pre-noise optical blur: sigma `1.05 px`, fresh unchanged downstream noise | every trial `>1`; q05 `>1.20` |
| G5 | genuine pre-noise optical improvement: sigma `0.30 px`, fresh unchanged downstream noise | every trial `<1`; q95 `<0.90` |
| G6 | post-render Gaussian blur: sigma `0.75 px` | maximum `|Q_EIN-1| <= 1e-12`, while the unnormalized output-noise ratio is `<0.90` |
| G7 | post-render USM: amount `0.75`, radius `1.0 px` | maximum `|Q_EIN-1| <= 1e-12` |
| G8 | post-render scalar gain: `1.0007x` | maximum `|Q_EIN-1| <= 1e-12` |
| G9 | actual M159-form pixel probe | Gaussian blur must reduce both fractional `R_box9` and the same high-pass RMS with local division removed to `<0.90`; the local-mean ratio must remain in `[0.99,1.01]` |

G9 distinguishes the suspected mechanism. If both normalized and
non-normalized high-pass residuals fall while the denominator barely moves,
local normalization is not the cause of the blur reward.

## Interpretation frozen before outcomes

Passing these gates commissions only the arithmetic and directional behavior
of `Q_EIN` on this synthetic model. It does not commission a production M2
bar, prove nonlinear-renderer completeness, or make M2 measurable without M1.

The candidate is rejected as a stand-alone M2 instrument even if all gates
pass. A production decision must bind the same output bytes and settings to:

1. M165's common linear input and deterministic-pattern-map contract;
2. M1's independent reference, `J_TR`, transfer and unexplained-structure
   admission;
3. independent A/B output repeats; and
4. a frozen ROI/cell/channel/bootstrap/comparator reduction.

