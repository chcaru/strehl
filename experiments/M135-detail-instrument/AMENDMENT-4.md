# M135 commissioning amendment 4

Status: **FROZEN BEFORE FLAT-NULL OUTCOME GENERATION**

The first final campaign passed the scorecard's then-required flat refusal:
an exact-zero reference returned `NO_DETAIL` in `128 / 128` populations. A
later independent kernel experiment showed why that is not enough. Its
low-structure arm carried `13.314850036584688%` of the detailed arm's coarse
structure, yet its purported detail gap was `1.0249391472947889x` the detailed
gap. The statistic measured kernel-dependent high-band energy rather than
resolved structure
(`experiments/M134-kernel-frontier/M137-clamped-detail.md:207-250`).

This amendment does not alter `J_TR`, `T_TR`, `U_TR`, any prior challenge, or
any prior numeric result. It promotes a matched flat sentinel from an offline
challenge to a mandatory part of every claim-bearing evaluation and adds the
specific noise-amplification adversary exposed by that failure.

## 1. Mandatory paired flat sentinel

The public `evaluate` entry point now requires two `CaptureSet` values:

1. the registered nonperiodic detail target; and
2. a preregistered featureless sentinel rendered by the same candidate mode.

Omission returns `MISSING_FLAT_CONTROL`. The flat sentinel is evaluated on the
same sixteen cells and at the same site count as the detail target. Every
result carries a `flat_control` object, including typed refusals.

Three flat/detail ratios are first-class outputs:

- corrected information:
  `J_TR(flat) / J_TR(detail)`;
- independently repeatable reference power:
  `P_rep(reference_flat) / P_rep(reference_detail)`; and
- independently repeatable output power:
  `P_rep(output_flat) / P_rep(output_detail)`.

For arrays `A,B`, `P_rep(A,B)` is the equal-weight mean over the sixteen
registered cells of
`max(0, Re(cov(A_k, B_k)))`. This is a control diagnostic, not a replacement
detail score.

A claim-bearing result requires all of:

- flat core status `NO_DETAIL`;
- flat/detail corrected-information ratio `<= 0.10`;
- flat/detail repeatable-reference-power ratio `<= 0.25`; and
- flat/detail repeatable-output-power ratio `<= 0.10`.

Failure of any condition returns `FLAT_NULL_FAILED` and suppresses a
claim-bearing top-level score. The nested detail diagnostics remain available
for forensic checks. The `0.10` evidence ceiling matches the independently
registered M137 flat-gap ceiling; the `0.25` selector ceiling matches its
preregistered low-structure ceiling. Neither threshold was chosen from an M135
flat-ratio outcome.

The synthetic campaign applies the same arm transform to its matched flat
output. It requires all uncontaminated claim-bearing arms in all `128`
populations to carry and pass this control. Two positive controls must fail:

- passing a structured detail target as the alleged flat sentinel; and
- adding the same output-only artifact to both flat repeats.

## 2. Spectrally shaped noise-amplification arm

The new arm leaves latent signal and both independent references unchanged and
multiplies only each output-noise realization by

`g(f) = 1 + 1.5 * (f / 0.25)^2`

at the four registered frequencies. Thus the squared noise gain is
`[1.5376, 2.3716, 3.8416, 6.25]`; its upper-two-band mean is `5.0458`, and the
upper/lower mean-gain ratio is approximately `2.5815`. The same operation is
applied to the flat output.

This is not a common post-render filter: it is a planted noise-only mechanism
with no new scene information. It complements the existing common-filter USM
arm, for which `J_TR` must tie structurally.

The new noise arm passes only if:

- the `95th` percentile of `J_TR(noise-amplified) / J_TR(base)` is `< 0.90`;
- no population is promoted over base;
- all flat controls remain valid; and
- the frozen potency values above are emitted.

## 3. Added gates

- **C22 — mandatory flat certificate:** every uncontaminated claim-bearing arm
  carries the three ratios and passes their per-run bars; structured-flat and
  common-artifact plants return `FLAT_NULL_FAILED`.
- **C23 — high-band noise amplification:** the noise-only plant meets its
  potency definition, depresses information below the frozen bar, produces no
  promotion, and does not create flat detail.
- **C24 — missing-flat fail closed:** omission returns
  `MISSING_FLAT_CONTROL` in all `128` populations.

The original C0-C21 outcomes remain historical facts and must reproduce
unchanged at their underlying detail-score fields. The replacement campaign
may begin only after this amendment and its source changes are committed.
