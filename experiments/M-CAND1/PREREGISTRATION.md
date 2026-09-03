# M-CAND1 Candidate 1 freeze

**Status: FROZEN.** The identifying commit is supplied to the runner and embedded
in every scientific result. No scientific arm has run at the time of this freeze.

## Scope and unresolved specification ambiguity

This commissions a finite variational observer; it does not score M1 and does not
touch the incoming 319-frame holdout. The common-task contract says alternatives
differ at `f >= 0.25 cyc/native px`, while the scorecard forbids every frequency
above `0.25 cyc/native px`. The intended near-limit reading used here is frozen as
`0.16 <= f <= 0.24 cyc/native px`. This preserves the scorecard cap and avoids
collapsing the task to the few exactly-0.25 Fourier bins. The proposal owner must
resolve the inequality before a scored use.

## Estimator

- Estimand target: balanced binary `X`; class 0 is a random-phase surrogate and
  class 1 is its phase-coupled source. For every trial the alternatives have the
  same Fourier magnitude, zero mean, unit RMS, full-tile support, and no energy
  outside the frozen task band.
- `Y` is the complete `4 x 32 x 32` linear CFA-plane tile. All R/G1/G2/B channels
  enter one observer. No coordinate, filename, frame index, or metadata enters it.
- Observer: 32 fixed random `4 x 5 x 5` zero-DC unit-norm filters, seed
  `0xC1A551F1`. Per filter, the features are spatial mean absolute response and
  second, third, and fourth moments: 128 fixed features total.
- Probabilistic fit: ridge logistic regression, `lambda=0.003`, SciPy L-BFGS-B,
  at most 600 iterations, fixed tolerances in `src/cand1.py`. Features are
  standardized from the training fold only. Probabilities are clipped only for
  finite logarithms at `1e-9`.
- Five leave-one-acquisition-session-out folds. Each macro-tile has eight fresh
  patterns and noises, exactly four per class. A session held out for evaluation
  contributes no training sample to its observer.
- Reported scalar:
  `J = 1 + mean(log2(q(X|Y)))` bits/tile, without a zero floor. Since `H(X)=1`,
  `J` is also the reported `I/H(X)`. Accuracy is diagnostic only.

## Inputs and tile selection

Only the five explicitly hashed development RAW files in `input-manifest.json` are
opened. Each is decoded twice through independent RawPy opens; visible-buffer and
active-area decodes must be byte-equal. The program never scans
`D:\personal\macro`, and writes nothing there.

Every acquisition block contributes a geometry-only `8 x 12` grid of 32-square CFA-plane
tiles. There is no pixel-value eligibility selection. Centres are equally spaced
inside the active area. The fixed 16-pixel guard exceeds the 6-pixel largest
pre-noise blur half-support, 4-pixel USM half-support, and 2-pixel observer-filter
radius; crops do not overlap.

The five selected sessions are the five existing development calibration-grid
stacks, and the selected file is their lexicographic middle frame. The selection,
byte counts, and SHA-256 values are frozen in the manifest.

## Forward task and arms

- Signal amplitude: `0.060` in black/white-normalized RAW units, achromatic with
  fixed channel factors `[1.00, 0.96, 1.04, 0.91]`.
- Fresh independent Gaussian noise: sigma `0.009` per channel.
- Baseline pre-noise optical Gaussian sigma: `0.85` native pixels.
- Planted degradation: pre-noise sigma `1.35`, with its own noise stream.
- Planted improvement: pre-noise sigma `0.35`, with its own noise stream.
- Kill arm: after the complete noisy baseline tile, unclipped float
  `Y + 0.5 * (Y - G_sigma=1.0(Y))`; no quantization or clipping.
- Null: a separate arm name whose generated floats and fitting path are identical
  to baseline by construction.

Pattern, assignment, nuisance, and noise seeds are cryptographic hashes of fixed
names and cluster identities. Training seed is `0x41D3A918`. A development-only
seed `0x09B72CE4` is used for the baseline learning curve. The sealed-test seed is
derived only after this freeze from the freeze commit SHA and the literal
`sealed-test-after-freeze`.

## Frozen order and stopping

1. Run baseline versus USM first. No other scientific arm has been run.
2. If USM fails, declare **CANDIDATE 1 IS DEAD** and run nothing else.
3. Only after a USM pass, run null, degradation, and improvement. No tone, noise,
   clipping, geometry, or scored-capture arm belongs to this lane.

## Numerical decision rules

The paired cluster bootstrap uses 10,000 draws, seed `0x50C1A7E1`, resampling the
five acquisition sessions first and the 96 macro-tiles within each sampled session
second. Pixels and eight within-tile trials are never bootstrap units.

- Base usability: `0.08 <= J_base <= 0.85` bits/tile. Outside is blindness or
  saturation and kills this frozen version.
- USM: `UCB95_one-sided(J_usm / J_base) <= 1.01`. Anything larger, including an
  under-powered bound, kills the candidate with no retune.
- Null: the complete two-sided 95% ratio interval must lie in `[0.99, 1.01]`.
- Degradation: `UCB95_one-sided(J_degraded / J_base) <= 0.70`.
- Improvement: `LCB95_one-sided(J_improved / J_base) >= 1.30`.

The pre-seal baseline learning curve at 24/48/72/96 macro-tiles per session must
place the 96-tile `J` inside the base usability interval and move by at most
`0.02 bits` from 72 to 96. Its baseline-only hierarchical bootstrap must also put
the conservative independent-arm, one-sided alpha-0.05, 90%-power minimum
detectable ratio change at or below the frozen 30% commissioning margin. Failure
permits pre-freeze redesign; after freeze no estimator, task, threshold, feature,
seed, or hyperparameter may change.

Before this freeze, and before generating any USM, null, degradation, or improvement
sample, two baseline-only amplitudes were rejected: `0.032` gave `J=0.050101` bits
and `0.042` gave `J=0.095574` bits. The final `0.060` baseline gave `J=0.149147`
bits with a 72-to-96-tile change of `0.002289` bits. Its arm-blind 90%-power
minimum detectable ratio change is `0.290713`, inside the frozen `0.30` bar.
This history is retained to separate legitimate pre-seal dynamic-range work from
forbidden control tuning.
