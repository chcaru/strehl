# M171 truth-reference admission gates - preregistration

Status: **FROZEN BEFORE SYNTHETIC OUTCOME EXECUTION**

Written: **2026-09-04T14:25:21.553-07:00**

## 1. Scope and ruling

This experiment commissions the seven eligibility gates in
`docs/proposals/2026-09-truth-referenced-detail.md` section 3.1 and adds the
eighth gate required by `docs/research/M164-reference-identifiability.md`:
`REFERENCE_INFORMATION_DOMINANCE`.

The capture ruling is **ANALYSIS ONLY**. The registered full capture already
contains the required higher-magnification reference halves, pre-render TC0
A/B physical witnesses, disjoint calibration lineages, and matched controls.
No new magnification, optical state, or calibration exposure is requested.
The pending two-frame preflight remains a geometry-only sampling-ratio check.

This experiment consumes synthetic evidence only. It does not read, list, or
decode a capture and it cannot emit an M1 score.

## 2. Authority and unresolved specification boundary

The controlling gate-8 noise convention is the one in M164 commit
`a78a901eca2a2e3caaf79f68387439e54884be3f`:

```text
N_P,k = 0.5 E |P_1,k - P_2,k|^2.
```

The initial v1 `contract.json` SHA-256 was
`5DBE0382EB1D80A557CF0DB2D592E5D72BA7553D947D0E6BD5E575FF1050AB7B`.
Amendment 1 below supersedes it before the replacement campaign.

A later M164 report defines `0.25` times the split-difference variance when
the estimand is the noise in the average of the two repeats. M171 does not
silently reconcile these different estimands. The synthetic commission uses
the required `0.5` convention. Production admission remains `UNMEASURED`
until the authority freezes the target estimand and convention in a
versioned calibration manifest.

The proposal does not freeze production values for the information and
transfer margins, support floor, licensed cells, split-SNR floor,
common-mode allowance, half-agreement tolerance, resampler allowance, or RAW
response calibration. Values in this preregistration are synthetic
commissioning values only. They must never become production defaults.

Gate 4 can detect clipping and can verify a supplied known-input response
series. A fixed-exposure subject capture cannot establish arbitrary RAW
linearity by itself. Production Gate 4 therefore requires independent
response-calibration provenance or returns `UNMEASURED`.

## 3. Frozen sample and cell family

The synthetic family contains:

- one green channel;
- frequencies `0.10`, `0.15`, `0.20`, and `0.25` cycles per native output
  pixel;
- orientations `0`, `22.5`, `45`, and `67.5` degrees;
- all 16 frequency/orientation cells in one non-compensating family;
- 64 physical macro-sites in four sessions, two bursts per session, and
  eight sites per burst; and
- one two-dimensional cell at `0.25` cycles/pixel and `67.5` degrees to
  commission the smallest-generalized-eigenvalue rule. The other cells are
  scalar.

The candidate output is absent from every admission calculation. `R1/R2`
are independently calibrated higher-magnification reference repeats.
`S1/S2` are complete candidate-blind reductions of independent pre-render
scored-path physical acquisitions. A convenient single frame is not a valid
substitute for a scored acquisition.

## 4. Status and integrity contract

Each gate returns exactly:

```text
status        PASS | UNMEASURED
evaluated     true
reason_codes  [] for PASS, nonempty for UNMEASURED
claim_value   null for UNMEASURED
diagnostics   retained, including negative corrected quantities
```

There is no `SKIPPED` state and no degraded numeric score. Malformed schema,
hash mismatch, non-finite input, wrong shape, duplicate identifier, or a
mutation anchor that is missing or non-unique is `HARNESS_ERROR`, exit code
`2`, rather than a scientific result.

Every sealed JSON artifact is read once into bytes. The implementation hashes
those bytes, verifies the expected SHA-256, and parses those same bytes. It
does not hash a path and reopen it.

For every examined case:

```text
PASS + UNMEASURED = 8
```

The complete campaign has 11 cases and 88 gate evaluations. Its counted
partitions must sum exactly to 88.

## 5. Frozen gate definitions

### G1 - subject-sampling ratio

Use common input-only fiducials and a paired physical-site bootstrap.
Synthetic admission requires the lower 95% bound on
`M_reference / M_scored` to be at least `2.0`. Production without an admitted
M147 geometry artifact and optical-systematic bound is `UNMEASURED`.

### G2 - split-reference SNR

For every cell, use centered `R1/R2` coefficients and the M164 `0.5`
split-difference noise convention. Apply the common-mode charge. The
simultaneous lower 95% bound on `P_R/N_R` must exceed the synthetic floor
`4.0`. No cell may be averaged away. The production floor is unratified.

### G3 - reference focus and transfer sufficiency

Every cell must have a unique interior maximum in a five-position known-input
focus probe, a lower 95% bound on the smallest reference-transfer singular
value above `0.50`, condition number at most `100`, and cross-cell leakage at
most `0.05`. These are synthetic values. Natural same-subject power does not
identify absolute transfer; production requires known-input transfer
calibration and reduction-sufficiency evidence.

### G4 - unclipped linear RAW transfer

Require zero rail hits and a positive affine fit to an independently known
33-level response series. Fit the even-index levels and require the maximum
held-out normalized residual on odd-index levels to be at most `1e-6`.
Known-input provenance is mandatory. Clipping may be diagnosed without it,
but production linearity may not pass without it.

### G5 - reference-half agreement and common-mode control

Require disjoint source and calibration-master hashes. Compare odd/even,
contiguous-half, and alternating four-frame-block splits. Synthetic limits
are relative magnitude disagreement at most `0.10`, phase disagreement at
most `0.05` radians, and common-mode fraction at most `0.05`. Matched
featureless, corrected-flat, and corrected-dark controls are mandatory.

### G6 - geometry and reference-resampler sensitivity

Scored pixels must remain native; geometry must use input-only evidence.
Require scale disagreement at most `0.10%`, rotation disagreement at most
`0.02` degrees, nontranslation residual at most `0.10` native output pixels
RMS, the correct planted transform sign, and at most `1%` change between two
frozen reference-side kernels in every cell. Production resampler allowance
is unratified.

### G7 - nonperiodic reference power

Require concealed nonperiodic lineage, unique sites with maximum duplicate
correlation below `0.95`, a simultaneous charged reference-power lower bound
above `0.25`, and condition number at most `100` in every cell. No cell
deletion or cross-cell compensation is allowed. Production bands and power
floors are unratified.

### G8 - REFERENCE_INFORMATION_DOMINANCE

For every frozen cell `k`, after common subject-space calibration:

```text
P_R,k = Re Cov(R1,k, R2,k)
N_R,k = 0.5 E |(R1,k - R2,k) - mean(R1,k - R2,k)|^2

P_S,k = Re Cov(S1,k, S2,k)
N_S,k = 0.5 E |(S1,k - S2,k) - mean(S1,k - S2,k)|^2.
```

Let `U_R,k` and `U_S,k` be simultaneous upper bounds on absolute repeatable
covariance from the maximum across matched featureless, corrected-flat, and
corrected-dark controls. Charge them adversarially:

```text
P_R,k^- = P_R,k - U_R,k
N_R,k^+ = N_R,k + U_R,k
P_S,k^+ = P_S,k + U_S,k
N_S,k^- = N_S,k - U_S,k.
```

Nothing is clipped. Any nonpositive charged signal or noise is
`UNMEASURED`. Define:

```text
I_R,k^- = 0.5 log2(1 + P_R,k^- / N_R,k^+)
I_S,k^+ = 0.5 log2(1 + P_S,k^+ / N_S,k^-)
T_RS,k^- = sqrt(P_R,k^- / P_S,k^+).
```

The synthetic-only margins are `delta_I = 0.08` and `delta_H = 0.08`.
The gate requires simultaneous lower 95% bounds strictly above zero for:

```text
log(I_R,k^- / I_S,k^+) - log(1 + delta_I)
log(T_RS,k^-)           - log(1 + delta_H).
```

For a vector cell, Hermitian signal and noise matrices must be positive
definite and have condition number at most `100`. Information operators use
`0.5 log2(I + N^-1/2 P N^-1/2)`. The two comparisons use the smallest
generalized eigenvalue and are recomputed in every bootstrap draw. Ridge,
pseudoinverse, PCA, clipping, averaging eigenvalues, and scalar fallback are
forbidden.

The common-mode and dominance families each receive one-sided alpha `0.025`;
their union is at most `0.05`. The dominance family uses 10,000 fixed-seed
hierarchical paired bootstrap draws, seed `164177`, and NumPy's `higher`
quantile rule. Sessions are resampled outside bursts, bursts outside sites,
and frames are never treated as independent subjects. Invalid draws, zero
bootstrap standard error, or a failed rank/conditioning check make the whole
gate `UNMEASURED`.

Gate 8 passes only if every information and transfer lower bound is strictly
positive, every support and conditioning floor passes, and every common-mode
fraction is at most `0.05`. A strong cell cannot compensate for a weak cell.

The commissioned scope is `GX_REFERENCE_CONDITIONAL`. If a future request
names digital `K`, a separate hash-bound baseline for `q_k = H_S,k/H_R,k` is
mandatory; absent that baseline the result is `UNMEASURED`.

## 6. Frozen synthetic fixtures

The fixture seed is `17120260904`. Baseline latent coefficients are proper
complex, with reference transfer `1.50`, scored transfer `0.80`, reference
noise sigma `0.15`, scored noise sigma `0.45`, fresh downstream noise,
disjoint synthetic hashes, a five-position focus probe, and complete matched
controls.

The exact source mutation anchors and replacements are sealed in
`contract.json`. The scientific cases are:

1. baseline, expected `8/8 PASS`;
2. low sampling ratio, requiring G1 `UNMEASURED`;
3. high reference noise, requiring G2 `UNMEASURED`;
4. endpoint focus peak, requiring G3 `UNMEASURED`;
5. gamma-3 RAW response, requiring G4 `UNMEASURED`;
6. alternating four-frame drift missed by parity, requiring G5
   `UNMEASURED`;
7. wrong-sign rotation, requiring G6 `UNMEASURED`;
8. one cell with zero nonperiodic power, requiring G7 `UNMEASURED`;
9. one vector cell with favorable mean transfer but an inferior direction,
   requiring G8 `UNMEASURED`;
10. a planted genuine improvement from that weak G8 control, requiring every
    per-cell information and transfer margin to increase and G8 to pass; and
11. an improvement-shaped common-mode plant whose naive values rise but whose
    charged Gate 8 is `UNMEASURED`.

The commissioner must catch all eight targeted gate mutations and the
common-mode false improvement, record two expected green cases, and hard-error
on both a missing anchor and a deliberately duplicated full-line anchor.

## 7. Freeze, execution, and commit order

This file and `contract.json` are committed first. No synthetic outcome is
read before that commit.

After the first commit:

1. implement the evaluator, fixture generator, commissioner, tests, and
   independent verifier against the immutable contract hash;
2. run the 11-case campaign;
3. require the exact 88-result partition, nine caught RED cases, two green
   cases, both anchor hard errors, and zero capture reads;
4. write the report with every claim labelled `VERIFIED BY RUNNING` or
   `INFERRED BY READING`; and
5. commit implementation, evidence, and report under M171-owned paths only.

Changing a scientific threshold, cell, mutation, expected reason, seed, or
arm after the first outcome requires a new preregistration commit and a new
campaign. It may not be hidden in the implementation commit.

## 8. Amendment 1 - max-t direction and DIGITAL_K refusal

Status: **FROZEN AFTER INVALIDATION AND BEFORE REPLACEMENT EXECUTION**

Written: **2026-09-04T19:28:53.3637072-07:00**

An independent read-only verifier found that the first implementation used
the opposite max-t numerator from the source contract. It computed
`(observed - bootstrap) / se`; the required lower-bound construction is:

```text
t_b = max_f (bootstrap_f,b - observed_f) / se_f
LCB_f = observed_f - quantile_0.975(t_b) * se_f.
```

The affected commission SHA-256
`2B9A6A2DD1D1321C63F202FA8615BB466CD255D3BC52BAD2140ACBD71A24132E`
and verification SHA-256
`7627BDC0D42E3DDD011DEE2EF06CDD6BDA72471630919F02ABE96F282D0F68FE`
are invalidated in full. Their stored `COMMISSIONED` and `PASS` labels have no
standing. No result from that campaign may be cited as commissioning
evidence.

The defect exposed an unfrozen coordinate choice in G2. A raw-scale normal
bound on a strictly positive SNR ratio can cross below zero under a skewed
cluster bootstrap even when every draw is positive. Before replacement
execution, G2 is now frozen on the natural-log SNR coordinate:

```text
z_k = log(P_R,k / N_R,k)
t_b = max_k (z_k,b - z_k) / se(z_k)
LCB_SNR,k = exp(z_k - quantile_0.975(t_b) * se(z_k)).
```

The pass predicate remains unchanged:

```text
every LCB_SNR,k > 4.0.
```

This transformation preserves positivity, scale invariance, ordering, the
same familywise alpha, hierarchy, seed, cells, fixture, threshold, and
no-compensation rule. No fixture value or expected scientific arm changes.
The amendment is driven by the independently identified sign error, not by
selection among candidate results.

The verifier also showed that a finite, hash-bound but singular all-zero
`q_k` baseline could pass a `DIGITAL_K` request. This harness has not frozen
or commissioned the required `q_k` rank, conditioning, simultaneous
uncertainty, geometry, and site contract. It therefore refuses every
`DIGITAL_K` claim with
`DIGITAL_K_IDENTIFICATION_NOT_COMMISSIONED`, whether or not a matrix payload
is supplied. `GX_REFERENCE_CONDITIONAL` remains the only commissioned scope.

The amended v2 `contract.json` SHA-256 is
`E881BE8B28B12C58157133650B4B5405971C01B23A2D9E6743D14C411D691114`.
The v2 contract also freezes:

- max-t numerator `bootstrap_minus_observed`;
- G2 coordinate `natural_log_reference_snr`;
- G2 reported bound `exp_coordinate_lower_bound`;
- the existing log information and log transfer coordinates for G8; and
- fail-closed `DIGITAL_K` policy with the four categories of evidence a
  future preregistration must add.

The replacement implementation and campaign may begin only after this
amendment and the v2 contract are committed together.

## 9. Amendment 2 - checkout-stable seals

Status: **FROZEN AFTER V2 INVALIDATION AND BEFORE V3 EXECUTION**

Written: **2026-09-04**

A second independent verifier found that the v2 source and contract seals
were computed over CRLF worktree bytes while generated JSON artifacts used
LF. No Git attribute fixed either representation, so no clean checkout could
reproduce all active hashes under both LF and CRLF checkout settings.

The affected v2 commission SHA-256
`D1C862E12BCD967D9B3FB29BECA48CEB4939233B0758B84D725E4341AB1B78B1`
and verification SHA-256
`2773F392B7C51A4930300DFE7777D8ABF328CF6AED583245FACFC2A5A0A81449`
are invalidated in full. Their `COMMISSIONED` and `PASS` labels have no active
evidentiary standing.

Before replacement execution, the experiment now freezes:

```text
experiments/M171-reference-admission/.gitattributes
* text eol=lf
```

Every text source, contract, preregistration, and generated JSON artifact in
the experiment is stored and checked out as UTF-8 without BOM and LF line
endings. Source hashes and artifact hashes are computed over those exact LF
bytes. Verification must compare each worktree hash to the corresponding Git
blob from a clean, attribute-normalized index and must fail on any mismatch.

The v3 contract changes no scientific threshold, seed, cell, fixture,
mutation, estimator, pass predicate, or expected outcome from v2. It changes
only schema identities, explicit line-ending provenance, and invalidation
history. Its SHA-256 is
`6916517B7098BBD2EF7A4F9DF2B02E3D1DA22890F125CD3A4B4C5E444CD023CF`.

The replacement implementation and campaign may begin only after this
amendment, the v3 contract, and the lane-local `.gitattributes` are committed
together.
