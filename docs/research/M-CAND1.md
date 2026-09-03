# M-CAND1 — target-conditional observer

**Status: complete. Verdict: CANDIDATE 1 IS DEAD.**

## Freeze

Scientific freeze `613eaf1af9d65a56796474bd53df27caf05cd032` fixed the
`4x32x32` complete-CFA input, 128 random-convolution moment features, ridge-logistic
observer, five acquisition-block folds, 480 macro-tile clusters, seeds, transforms,
and literal gates before any arm output (`experiments/M-CAND1/PREREGISTRATION.md:16-93`;
`experiments/M-CAND1/out/usm.json:131-139`). The baseline-only learning curve ended
at `J=0.149147` bits, moved `0.002289` bits from 72 to 96 tiles, and powered the
frozen 30% optical bar with MDE `0.290713`
(`experiments/M-CAND1/out/preflight.json:2218-2259`).

**Correction:** frozen prose misread the proposal's `f <= 0.25` as `>=`
(`experiments/M-CAND1/PREREGISTRATION.md:8-14`;
`docs/proposals/2026-09-detail-instrument-investigation.md:93-95`). The executed
`0.168286-0.237993 cyc/native px` band nevertheless obeyed the cap
(`experiments/M-CAND1/out/usm.json:2401-2412`).

## Decisive first arm

The frozen rule was `UCB95(J_USM/J_base) <= 1.01`; otherwise kill immediately
(`experiments/M-CAND1/PREREGISTRATION.md:81-93`;
`docs/proposals/2026-09-detail-instrument-investigation.md:347`).

### Site independence and structural boundary

Scorecard v1.6 requires at least 64 independent sites without moving the frozen bar
as sample size grows (`docs/proposals/2026-09-sota-scorecard.md:519-521`). The arm
used 480 guarded macro-tile sites, each with eight balanced trials, across five
acquisition blocks. A site has disjoint sensor support and separately hashed target,
assignment, nuisance and noise draws (`experiments/M-CAND1/src/cand1.py:227-240`;
`experiments/M-CAND1/src/cand1.py:393-437`). Trials stay inside their site;
block dependence is resampled above sites (`experiments/M-CAND1/src/cand1.py:648-670`).
Thus `n=480`, not 3,840 pseudo-sites or unchanged crops. The `1.01` bar never moved.

Structurally, deterministic USM gives
`I(X;T(Y)) <= I(X;Y)`, with equality expected when invertible. That statement stops
at the estimand. This implementation estimates `J_q` through a non-invertible
128-moment feature map, finite ridge-logistic fits and arm-specific optimization;
capacity limits, finite optimization error, residual target leakage, and
USM-artifact fitting need not be equivariant
(`docs/proposals/2026-09-detail-instrument-investigation.md:139-173`;
`experiments/M-CAND1/PREREGISTRATION.md:16-35`). The observed increase is a failure
of this finite estimator, not of DPI.

Baseline was `0.125099` bits/tile; unclipped float USM radius `1.0`, amount `0.5`
was `0.137075`. Effect: `R=1.095732` (**+9.573%**), paired log ratio `0.091423`,
and `+0.011976` bits, with two-sided delta CI
`[+0.008036,+0.015904]`. The one-sided 95% ratio upper bound was `1.129895`
(`experiments/M-CAND1/out/usm.json:79-102`).

## Commissioning directions

- Planted degradation: **NOT RUN**.
- Planted improvement: **NOT RUN**.
- Identical-input null: **NOT RUN**.

No lawful observer numbers exist for those arms: the preregistration requires an
immediate stop after a USM failure (`experiments/M-CAND1/PREREGISTRATION.md:74-79`),
and the runner hard-refused commissioning before data loading
(`experiments/M-CAND1/out/checks.txt:11-23`). No retune was attempted.
