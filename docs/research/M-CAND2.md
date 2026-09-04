# M-CAND2 — full-covariance Hotelling information

**VERDICT: CANDIDATE 2 IS DEAD.**

Scientific amendment freeze
`3f0f7ac2b6725af5db9251dda84d01e30386c130` preceded every new arm. It
preserved 480 independent macro-tile sites, all four CFA channels, `p=256`,
`n_K=384/fold`, the original sealed task, full unregularized covariance,
Cholesky solves, 10,000 block-then-site bootstrap draws, and USM r1.0/a0.5
(`experiments/M-CAND2/PREREGISTRATION-V2.md:13-25,77-95`). The only fixture
change was the preregistered global display map whose black/white points were
the original baseline-only extrema; its pinned-task preflight retained
`d'^2=6.012288529` and maximum condition number `1.92547e5`
(`PREREGISTRATION-V2.md:27-49`).

Mapped unclipped USM again proved implementation congruence:
`R=1.0000000000000009`, CI
`[0.9999999999996845,1.0000000000003315]`; maximum covariance residual was
`1.25e-15`, score residual `1.93e-11`
(`experiments/M-CAND2/out/amendment-unclipped-usm.json:3-11,221-225`).

Clipped USM remained **UNCOMMISSIONED**, not green. Only `114/2,088,960`
coordinates changed (`0.00546%`) against the frozen `0.1%` gate; only 22 hit
the upper rail (`0.00105%`) against `0.05%`. Upper-rail coverage was 0
covariance, 12 derivative, and 5 test sites, below 64/role, so scoring never ran
(`experiments/M-CAND2/out/amendment-clipped-usm.json:2293-2346,2396`).

Both independent tone arms were potent and decisive. Gamma-3 changed
`99.99995%` of values, materially transformed all 480 sites/role, introduced
no ties, and moved `d'^2` from `6.012289` to `3.023536`:
`R=0.502893`, CI `[0.443972,0.557901]`
(`experiments/M-CAND2/out/amendment-gamma3.json:200-215,2503-2520,2531-2561`).
Logistic changed `100%`, materially transformed all 480 sites/role with no
ties, and moved `d'^2` to `2.926425`: `R=0.486741`, CI
`[0.414213,0.565049]`
(`experiments/M-CAND2/out/amendment-logistic.json:200-215,2503-2520,2531-2561`).
Both intervals miss the frozen `[0.99,1.01]` equivalence region by orders of
magnitude. A free monotone tone curve nearly halves this estimator.

The literal gate therefore recorded `DEAD` and ran no saturation, quantization,
optical, or null arm
(`experiments/M-CAND2/out/amendment-downstream-gate.json:2-5,22-39`).
Congruence protects only invertible linear transforms; it stops at nonlinear
tone, clipping, quantization, rank loss, regularization, channel removal, and
local-model failure (`PREREGISTRATION-V2.md:101-108`).

## Frontier-coordinate audit — existing measurements only

| statistic / variant | USM ratio | genuine optical improvement ratio | physical blur ratio | sign correct on improvement? |
| --- | ---: | ---: | ---: | --- |
| Candidate 1 finite-observer \(J_q\) | `1.095732` (`experiments/M-CAND1/out/usm.json:88-102`) | **NOT RUN** (`docs/research/M-CAND1.md:57-63`) | **NOT RUN** (`docs/research/M-CAND1.md:57-63`) | **UNKNOWN — NOT RUN** (`docs/research/M-CAND1.md:57-63`) |
| Candidate 2 native full-covariance Hotelling | `1.0000000000000266` (`experiments/M-CAND2/out/unclipped-usm.json:214-231`) | **NOT RUN** (`experiments/M-CAND2/PREREGISTRATION.md:67-75,92-95`) | **NOT RUN** (`experiments/M-CAND2/PREREGISTRATION.md:67-75,92-95`) | **UNKNOWN — NOT RUN** (`experiments/M-CAND2/PREREGISTRATION.md:67-75,92-95`) |
| Candidate 2 display-referred Hotelling | `1.0000000000000009` (`experiments/M-CAND2/out/amendment-unclipped-usm.json:210-225`) | **NOT RUN** (`experiments/M-CAND2/out/amendment-downstream-gate.json:2-5,22-39`) | **NOT RUN** (`experiments/M-CAND2/out/amendment-downstream-gate.json:2-5,22-39`) | **UNKNOWN — NOT RUN** (`experiments/M-CAND2/out/amendment-downstream-gate.json:2-5,22-39`) |

Therefore this lane has **no measured viable frontier coordinate and no
wrong-signed optical result**. The universal-sign question remains unanswered:
every lane-owned optical arm was stopped upstream, so Candidate 1's \(J_q\) has
no lawful improvement or blur reading to recover.

### Highest-value missing cells

Candidate 2's blur and improvement paths are already implemented, but the
frozen runner correctly refuses them behind the closed mandatory gate
(`experiments/M-CAND2/src/run_v2.py:524-551,604-630`;
`experiments/M-CAND2/out/amendment-downstream-gate.json:2-5`). Filling those two
cells requires a separate preregistration/freeze that authorizes a post-mortem
optical-sign measurement, followed by two existing 480-site arm invocations and
their checker/report. Scope estimate: one short dedicated lane; compute should
take minutes, while the new freeze and review are the substantive work. No new
capture is required. Neither arm was run for this audit.

## Post-mortem optical-sign preregistration

<!-- CAND2-POSTMORTEM-PREREG-START -->

**Status: FROZEN before either optical arm.** The freeze is the latest
path-scoped Git commit containing this block. It supersedes preregistration
`c4b29080174e47643ca17284551f63112f8c0bc5` before any arm because that
version did not bind the output directory to its exclusive locks. No result
artifact or invocation lock existed. The historical `DEAD` verdict and
downstream gate remain closed; this is a separately authorised sign
measurement, not a rescue.

### Registered prior and outcomes

The orchestrator predicts blur will read approximately `1.0`, because unclipped
USM and Gaussian blur are both linear shift-invariant filters. The measurement
will report unrounded values rather than fit that prediction.

For each native and display-referred variant, `R≈1` means the complete two-sided
95% ratio CI lies inside inclusive `[0.99,1.01]`. `R` is meaningfully non-unity
only when that CI is strictly disjoint from `[0.99,1.01]`. Genuine improvement
is meaningfully above one only when its original one-sided `LCB95>=1.30`.

1. Blur `≈1` and improvement `≈1`: `OUTCOME_1_STRUCTURALLY_BLIND`.
2. Blur `≈1` and improvement meaningfully above one:
   `OUTCOME_2_PRIZE`.
3. Blur meaningfully non-unity:
   `OUTCOME_3_PRIOR_WRONG_NEEDS_ANALYSIS`.
4. Every other interval configuration: `UNRESOLVED_OUTSIDE_REGISTERED_CASES`.

These labels are mechanical frozen-predicate dispositions, not this lane's
adjudication. Native and display results are not pooled.

### Frozen implementation and provenance

- Runner SHA-256: `14d634dc5c14caf5786957156f6318509bc2faedf4e999419fce56b3fcc1281e`
- Checker SHA-256: `00c4a97b9efde97656656181e836c291d0d3c3ae9fc98da67fb0727a293c7d39`
- Session directory:
  `C:\Users\chris\.copilot\session-state\841ddf83-8ef0-40bd-a341-d2c66d487731\files\cand2-postmortem-optics`
- CAND1 manifest SHA-256:
  `b956763f023c319b7e4c16344bddfe54d2337221bf9105216342b7be957e7cdc`
- CAND1 loader SHA-256:
  `6f0cb891593d3bdaa81391580727526ee2d3292279b87c7d111af1a16943a63d`
- Candidate 2 core SHA-256:
  `f40249d01d7dffc7eb4aba3bf82bdf6980dcc163c125d7a51eb19b9bf07f2f98`
- Display-map implementation SHA-256:
  `7be4233d7113a5a1bd9f472401afb844c9295901fea75d2f5e8c7fab38ab5c26`
- Closed historical gate SHA-256:
  `b030945a6cb11ac17895175fee3b1cc03b302b5f2819baa3c0fee423bc551408`

The pinned task seed remains `1687423341261369299`. Both variants retain 480
sites, four tasks, five leave-one-block-out folds, `p=256`, 384 covariance
training sites/fold, and the frozen 10,000-draw block-then-site bootstrap at
`0xC2B0057A`. Before constructing either optical arm, native and display
baselines must reproduce `6.0122885561019395` and `6.012288528538082`
respectively within absolute and relative `1e-12`.

Exactly two invocations are authorised, in order: degraded sigma `1.35`, then
improved sigma `0.35`. Each invocation reports native and display variants.
Improved cannot start until the independent checker accepts degraded. Permanent
exclusive invocation locks in the exact registered session directory forbid
reruns; both scripts reject every alternate output directory. No USM, tone,
clipping, quantisation, null, alternate seed, threshold change, or statistic
retuning is authorised. All six numerical thread variables are fixed at eight.

The checker independently recomputes held-out `d'^2`, all four 10,000-draw
bootstraps and every disposition from stored score arrays without regenerating
observations. It also verifies this commit changed only this report, this block
remains byte-identical, dependency/script hashes match, the historical gate is
unchanged, and artifacts remain outside the repository.

**Prior caveat frozen before measurement:** registered USM acts on the complete
realised observation after noise, whereas these existing optical arms change
only the target before nuisance and arm-specific noise. Thus the orchestrator's
generic-LSI prediction is a prediction to test, not an algebraic consequence of
this fixture. This caveat cannot change the registered outcome labels.

<!-- CAND2-POSTMORTEM-PREREG-END -->
