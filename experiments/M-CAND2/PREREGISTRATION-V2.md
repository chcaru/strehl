# M-CAND2 display-referred adversary amendment

**Status: FROZEN before any amendment arm.** The runner hard-refuses every arm
unless this is the sole status marker.

## Scope and unchanged construction

This amendment does not rescue or reinterpret the invalid first clipped-USM
result. It preserves its raw output. It changes one stimulus fixture before a
new freeze: every observation is mapped through one global display black/white
map before the registered challenge.

The estimator is unchanged: 480 disjoint guarded macro-tile sites, all four CFA
planes over `8x8` pixels (`p=256`), 384 covariance sites per fold (`n/p=1.5`),
four tasks, separate covariance/derivative/test streams, leave-one-acquisition-
block-out cross-fitting, full unregularized covariance, and Cholesky solves.
There is no shrinkage, pseudoinverse, projection, channel selection, diagonal
covariance, or outcome-chosen conditioning repair.

The original scientific task is pinned rather than rerandomized:

- template/noise seed: `1687423341261369299`;
- template SHA-256:
  `f0a719587f7aa39165c7f0fce75835a631306b8b3f21b08e944a137b5a012bfe`.

## Input-only display map

The baseline-only development preflight, SHA-256
`93ee82f26d531908df7c23f2ce4afd7cc4cb268ff1daabb732999b52b9b05aa8`,
recorded the complete simulated output range
`[0.1238397868362581, 0.8139398559872297]`. Those exact input-only extrema,
recorded before the first USM arm, are the fixed global black and white points:

`B = clip((Y - 0.1238397868362581) /
          (0.8139398559872297 - 0.1238397868362581), 0, 1)`.

The same scalar map is applied to every channel, site, sign, stream, task and
optical arm. There is no per-image, per-site, per-channel, percentile, or
outcome-adaptive normalization. Input-map rail counts are reported separately
and never count as post-USM clipping potency.

The registered operator remains exactly float USM Gaussian radius `1.0`, amount
`0.5`, reflect boundary, truncate `4.0`. Its amount is not increased.

The pinned-task display-only preflight ran before this freeze and evaluated no
challenge transform. It retained all 480 sites and reported
`d'^2=6.012288529`, maximum covariance condition number `1.92547e5`, one
input-map low-rail value, zero input-map high-rail values, and no value outside
the display range. Those input-map counts are not post-USM potency.

## Pre-score potency gates

No covariance fit, Hotelling score, or bootstrap may run until the applicable
potency record passes.

For clipped USM, compare `U(B)` directly with `clip(U(B),0,1)`. Require:

1. changed coordinates exactly equal coordinates outside `[0,1]`;
2. at least `0.1%` of all coordinates newly clipped;
3. at least `0.05%` newly clipped at the upper display rail;
4. maximum clipping displacement at least `0.005` display units;
5. at least 64 independent sites and all five acquisition blocks represented
   separately for upper-rail clipping in covariance, derivative and held-out
   test roles; and
6. at least two unequal values above one collapsing to the same upper rail.

Failure is `INVALID_UNPOTENT`, records no score, and does not count as a green.

For gamma-3 and logistic `expit(12*(B-0.5))`, require finite output, at least
`95%` coordinates changed, RMS change at least `0.05`, maximum change at least
`0.10`, no new ties between distinct inputs, and at least `10%` coordinates with
normalized endpoint-chord residual at least `0.05`. Each covariance, derivative
and test role must contain at least 64 materially transformed independent sites
from all five blocks. Failure is invalid, not invariant.

## Frozen order and decision rules

1. Unclipped `U(B)` is an implementation check. The existing algebra gates remain:
   ratio residual `<=1e-8`, held-score residual `<=1e-7`, congruence residual
   `<=1e-10`, positive operator minimum eigenvalue.
2. Run potent clipped USM, gamma-3 and logistic as sibling kill arms after the
   implementation check. Both tones run even if clipping is uncommissioned or
   one tone kills the candidate.
3. A potent clipped-USM result requires one-sided `UCB95(R)<=1.01`. Each potent
   tone requires its complete two-sided 95% ratio interval inside `[0.99,1.01]`.
   A valid failure kills candidate 2. No retuning follows.
4. Only if all three kill arms pass, run direct saturation `[0.10,0.90]`, then
   8-bit quantization. Each must be demonstrably many-to-one before scoring and
   must lower (`R<=1`, `UCB95<=1.01`) or explicitly `REFUSED_RANK`.
5. Only if both loss arms pass, run pre-noise blur sigma `1.35` (`UCB95<=0.70`),
   improvement sigma `0.35` (`LCB95>=1.30`), then exact-copy null (ratio residual
   `<=1e-8`), stopping after the first failure.

All comparisons retain 10,000 paired block-then-site bootstrap draws at seed
`0xC2B0057A`. The `1.01` and optical bars do not move with sample size.

Final precedence is literal: any valid kill-arm failure means **DEAD**; absent a
valid failure, any required potency failure means **UNCOMMISSIONED**; only every
required adversary and commissioning direction passing means **COMMISSIONED**.

## Algebra boundary

The affine part of the display map and unclipped USM are fixed linear coordinate
changes, so the full-rank unregularized sample quadratic remains congruence-
invariant. The theorem does not cover the display clamp, actual USM clipping,
gamma/logistic tone, quantization, rank loss, regularization, channel removal,
common-covariance failure, or the local-linear optical assumption. Spatial
stationarity remains unestablished, so the result is Hotelling task information,
not an NEQ claim.
