# M189 noise-colour detail — Amendment 1

Status: **FROZEN BEFORE V2 EXECUTION**

Date: 2026-09-05

## 1. Why v1 is not accepted

V1 measured genuine optical improvement/base `2.893930343x`, but its local
one-sided estimator measured USM/base `1.011364806x`, RED against the frozen
`<= 1.01` ceiling. `V1-RESULT.md` remains the binding v1 disposition.

The failure mechanism was diagnosed only after that result. Under the null,
estimated bin gains fluctuate around one. The local transform charges
excursions above one and ignores excursions below one, depressing the base
denominator. A population calculation gives exact pointwise USM/base
`1.000000000000x` and v1-binned population `0.999863556838x`; the finite v1
result is therefore an estimator/null-bias failure.

## 2. Structural repair

V2 replaces the sum of locally corrected bins with one conservative transfer
envelope:

\[
C_{\rm band}=\sum_{f\in B} C(f),\qquad
G_{\rm sup}=\max_{b\in B} \frac{N_b}{N_{\rm ref}},
\qquad
Q_{\rm sup}=\frac{C_{\rm band}}{\max(1,G_{\rm sup})}.
\]

For a common LSI post-filter with per-bin gain \(k_b^2\),

\[
\sum_b k_b^2 C_b
\le \left(\sup_b k_b^2\right)\sum_b C_b.
\]

Therefore exact noise-transfer knowledge gives
\(Q_{\rm sup}(Kx)\le Q_{\rm sup}(x)\). Unlike the local estimator, the
supremum is allowed to over-penalize frequencies where little scene power
exists. Conservatism is acceptable; rewarding a common sharpening filter is
not.

The v1 result was retrospectively evaluated under this formula while diagnosing
the failure. That value is **not** evidence for v2. V2 uses a new latent and new
noise streams frozen below.

## 3. New held-out synthetic streams

All fixture geometry, optical sigmas, PTC constants, licensed frequencies, and
filters remain exactly as in `PREREGISTRATION.md`, except:

- latent seed: `189101`;
- base repeat streams: `189103` and `189104`;
- adaptive-attack repeat streams: `189105` and `189106`.

These streams were not executed before this amendment was committed.

## 4. V2 outputs and predicates

`metric_v2.py` reports both:

- primary `score = Q_sup`; and
- diagnostic `local_score`, the failed v1 formula.

The frozen predicates remain P0-P3 and P5-P8 from the original preregistration.
P4 is superseded by:

```text
completed-image USM: score/base <= 1.01
```

There is no lower bound. The structural repair is deliberately allowed to make
USM worse.

The adaptive re-noise attack remains expected to score above base while its
noise gain remains in `[0.97, 1.03]`. Passing that attack arm is still a
declared limitation, not candidate acceptance.

V2 is a synthetic common-LSI commissioning. It does not establish robustness
to adaptive signal/noise separation, anisotropic transfer hidden by the radial
bins, PRNU, tone, demosaic, or real comparator outputs.

