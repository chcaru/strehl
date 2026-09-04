# M135 truth-referenced detail certificate: commissioning preregistration

Status: **FROZEN BEFORE OUTCOME GENERATION**

The freeze is the first path-scoped Git commit containing this file,
`instrument.py`, and `commission.py`. Syntax compilation is permitted before
that commit. No challenge output may be generated before the freeze.

This is a synthetic, estimator-level commissioning campaign. It does not read
RAW data, does not produce an M1 score, and does not qualify a physical
reference capture. Its purpose is to determine whether the proposed statistic
has the algebraic and directional behavior required to justify a physical
commissioning campaign.

## 1. Candidate under test

The candidate is the **truth-referenced information/transfer certificate**
implemented in `instrument.py`.

Each of `n >= 64` independent target sites contributes one complex coefficient
in each of 16 registered cells: four radial frequencies
`{0.10, 0.15, 0.20, 0.25}` cycles/native pixel crossed with four orientation
sectors `{0, 22.5, 45, 67.5}` degrees. No frequency exceeds
`0.25 cycles/native pixel`.

The inputs are two independently calibrated reference realizations `R1, R2`
and two independently captured/rendered output realizations `Y1, Y2`.

For each cell and each of the four `(Ya, Rb)` pairings, the implementation
computes the squared complex sample coherence

```
rho2 = |cov(Y, R)|^2 / (var(Y) var(R))
J_raw = -log2(1 - rho2).
```

The finite-sample chance floor is the 95th percentile of the same statistic
after 32 deterministic site permutations of `R`. The cell score is
`max(0, J_raw - J_perm95)`. A pair score is the equal-weight mean over the 16
cells. The reported `J_TR` is the minimum of the four pair scores. Thus no
single favorable output/reference pairing can carry the result.

The non-compensating coordinates are:

- `T_TR`: geometric mean magnitude of the output/reference cross-transfer,
  estimated from all four cross-pair covariances and the reference-repeat
  cross-power;
- `U_TR`: median positive repeatable output power not linearly explained by
  the independent reference, divided by repeatable output power;
- reference eligibility and lineage statuses.

`T_TR` and `U_TR` may veto or demote. They may never create a win. A candidate
mode may be promoted over a comparator only when `J_TR` rises and neither
veto coordinate regresses.

## 2. Frozen synthetic population

- Master seed: `135135`.
- Independent Monte Carlo populations: `128`.
- Registered site count: `64`.
- Sharpening sample-size ladder: `64, 128, 256, 512`, with the same bar at
  every size.
- Sixteen independent proper-complex Gaussian target coefficients per site.
- Reference transfer: unity.
- Reference noise standard deviation: `0.10`.
- Baseline optical transfer:
  `exp(-2*pi^2*0.65^2*f^2)`.
- Output noise standard deviation: `0.45`, drawn after optical transfer.
- Degraded optical transfer:
  `exp(-2*pi^2*1.05^2*f^2)`.
- Improved optical transfer:
  `exp(-2*pi^2*0.30^2*f^2)`.
- Information-free USM: radius `1.0`, amount `0.75`, applied to the complete
  realized output including noise.
- Information-free post-blur: sigma `0.75`, applied to the complete realized
  output including noise.
- Added-noise arm: independent output noise with standard deviation `0.70`.
- Common-mode output-only plant: proper-complex standard deviation `0.80`,
  identical in `Y1/Y2`, absent from `R1/R2`.
- Deterministic hallucination: an output-only high-band term derived from an
  independent lower-band coefficient, identical in `Y1/Y2`, absent from the
  matching high-band reference coefficient.
- Averaging trap: baseline optical transfer followed by sigma-`0.55` blur,
  with output noise reduced from `0.45` to `0.18`.
- Tone witness: 33 equally spaced steps. Gamma-3 and normalized logistic
  (`k=8`) are independently inverted with PCHIP before scoring.
- Clipping challenge: component rails chosen to clip at least 1% of output
  coordinates; any rail fraction above `0.1%` is a typed refusal.
- Quantization challenge: 8-bit output; fewer than 12 effective bits is a
  typed refusal.
- Shared-reference calibration challenge: output/reference blank-residual
  correlation `0.20`; absolute correlation above `0.05` is a typed refusal.

All arm comparisons except the fresh-noise null reuse the same latent target
and underlying noise draws. The fresh-noise null independently redraws output
noise at unchanged transfer. This separates algebraic invariance from
statistical repeatability.

## 3. Frozen eligibility rules

The candidate returns no numeric score unless all are true:

1. exactly two output and two reference realizations are present;
2. every registered cell is at or below `0.25 cycles/native pixel`;
3. every array has at least 64 sites and finite values;
4. minimum reference-repeat coherence across cells is at least `0.50`;
5. the 32-real-coordinate reference covariance has full sample rank and
   condition number no greater than `100`;
6. output clipping fraction is no greater than `0.001`;
7. effective output precision is at least 12 bits;
8. absolute output/reference calibration-residual correlation is no greater
   than `0.05`;
9. `J_TR >= 0.10 bits/site`.

Failures return one of `NO_DETAIL`, `ILL_CONDITIONED_REFERENCE`,
`NONLINEAR_OUTPUT`, `LOW_BIT_DEPTH`, `SHARED_REFERENCE`, or `NO_EVIDENCE`.
A non-`OK` status carries no score.

## 4. Frozen admission battery

All numerical intervals below are inclusive.

| ID | Challenge | Required result |
|---|---|---|
| C0 | Exact identity | Maximum absolute `J_TR` ratio error `<= 1e-12`. |
| C1 | Fresh-noise untuned null | 95% CI for mean log ratio contains zero and lies wholly inside ratio `[0.95, 1.05]`. |
| C2 | Pre-noise blur | 95th percentile `J_TR` ratio `< 0.90`. |
| C3 | Planted optical improvement | 5th percentile `J_TR` ratio `> 1.10`. |
| C4 | USM, 64 sites | Maximum ratio `<= 1.01`; exact-congruence residual `<= 1e-10`. |
| C5 | USM sample-size ladder | C4 holds separately at `n=64,128,256,512`; the `1.01` bar never changes. |
| C6 | Information-free post-blur | `J_TR` exact-congruence residual `<= 1e-10`, and 95th percentile `T_TR` ratio `< 0.95`; no promotion. |
| C7 | Gamma-3 after 33-step PCHIP | Every `J_TR` ratio in `[0.99,1.01]`; no promotion. |
| C8 | Logistic tone after 33-step PCHIP | Every `J_TR` ratio in `[0.99,1.01]`; no promotion. |
| C9 | Added independent noise | 95th percentile `J_TR` ratio `< 0.90`. |
| C10 | Common-mode A/B plant absent reference | 95th percentile `J_TR` ratio `< 0.90` and 5th percentile `U_TR` increase `> 0.05`. |
| C11 | Deterministic hallucination absent reference | 95th percentile `J_TR` ratio `< 0.95`; no promotion. |
| C12 | Averaging trap | 95th percentile `T_TR` ratio `< 0.98` and zero certificate promotions, regardless of `J_TR`. |
| C13 | Edge-angle relabeling | Maximum absolute `J_TR` ratio error `<= 1e-10`. |
| C14 | Flat reference | `NO_DETAIL` in 128/128 populations; never numeric. |
| C15 | Repeated periodic template | `NO_DETAIL` in 128/128 populations; never numeric. |
| C16 | Site-permuted independent reference | No `OK` result in 128/128 populations. |
| C17 | Clipping | `NONLINEAR_OUTPUT`; never numeric. |
| C18 | 8-bit quantization | `LOW_BIT_DEPTH`; never numeric. |
| C19 | Shared reference/output calibration pattern | `SHARED_REFERENCE`; never numeric. |
| C20 | Checker mutation controls | A forced USM promotion, a reversed blur sign, and a suppressed improvement must each make the checker fail. |

`C2` and `C3` are respectively the required planted defect and planted
improvement. The campaign is inadmissible if either is absent, even if all
null and refusal arms pass.

## 5. Interpretation frozen before results

- Passing every arm commissions only the estimator and its declared synthetic
  model. It does not admit M1 and does not establish physical reference
  eligibility.
- Failure of C4/C5 kills the recommended architecture because sharpening
  safety is its reason to exist.
- Failure of C2 or C3 means the statistic is blind or wrong-signed and kills
  it even if all adversarial refusals pass.
- Failure of C10, C14, C15, C16, or C19 means independent-reference lineage is
  not doing the required work and kills it.
- Failure only of C7/C8 permits no unlinearized use; it does not permit moving
  the 1% bar.
- No threshold may be changed after outcome generation. A code defect requires
  a committed amendment that explains the defect before any replacement run.
