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

The first invocation stopped before RAW loading because the byte verifier confused
CRLF checkout bytes with Git blob bytes; only that verifier changed before the
scientific freeze (`experiments/M-CAND1/PREREGISTRATION.md:111-119`).

**Correction:** the frozen prose at
`experiments/M-CAND1/PREREGISTRATION.md:8-14` misread the proposal's `f <= 0.25`
as `>=`. The specification is unambiguous
(`docs/proposals/2026-09-detail-instrument-investigation.md:93-95`).
The executed band was `0.168286-0.237993 cyc/native px`, so the arm itself obeyed
the cap (`experiments/M-CAND1/out/usm.json:2401-2412`).

## Decisive first arm

The frozen rule was `UCB95(J_USM/J_base) <= 1.01`; otherwise kill immediately
(`experiments/M-CAND1/PREREGISTRATION.md:81-93`;
`docs/proposals/2026-09-detail-instrument-investigation.md:347`).

Baseline was `0.125099` bits/tile; unclipped float USM radius `1.0`, amount `0.5`
was `0.137075`. Effect: `R=1.095732` (**+9.573%**), paired log ratio `0.091423`,
and `+0.011976` bits, with two-sided delta CI
`[+0.008036,+0.015904]`. The one-sided 95% ratio upper bound was `1.129895`
(`experiments/M-CAND1/out/usm.json:79-102`). The frozen checker reproduced the
verdict and caught 10/10 literal-gate mutations
(`experiments/M-CAND1/out/checks.txt:1-10`).

## Commissioning directions

- Planted degradation: **NOT RUN**.
- Planted improvement: **NOT RUN**.
- Identical-input null: **NOT RUN**.

No lawful observer numbers exist for those arms: the preregistration requires an
immediate stop after a USM failure (`experiments/M-CAND1/PREREGISTRATION.md:74-79`),
and the runner hard-refused commissioning before data loading
(`experiments/M-CAND1/out/checks.txt:11-23`). No retune was attempted.
