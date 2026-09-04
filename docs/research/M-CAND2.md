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
