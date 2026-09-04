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

## Frontier-coordinate audit

| statistic / variant | USM ratio | genuine optical improvement ratio | physical blur ratio | sign correct on improvement? |
| --- | ---: | ---: | ---: | --- |
| Candidate 1 finite-observer \(J_q\) | `1.095732` (`experiments/M-CAND1/out/usm.json:88-102`) | **NOT RUN** (`docs/research/M-CAND1.md:57-63`) | **NOT RUN** (`docs/research/M-CAND1.md:57-63`) | **UNKNOWN — NOT RUN** (`docs/research/M-CAND1.md:57-63`) |
| Candidate 2 native full-covariance Hotelling | `1.0000000000000266` (`experiments/M-CAND2/out/unclipped-usm.json:214-231`) | `2.4627494970140926` (post-mortem `improved-result.json:215-237`) | `0.2779204535796564` (post-mortem `degraded-result.json:215-237`) | **YES** (post-mortem `improved-result.json:227-237`) |
| Candidate 2 display-referred Hotelling | `1.0000000000000009` (`experiments/M-CAND2/out/amendment-unclipped-usm.json:210-225`) | `2.4627459325690912` (post-mortem `improved-result.json:143-165`) | `0.27792013119436004` (post-mortem `degraded-result.json:143-165`) | **YES** (post-mortem `improved-result.json:155-165`) |

Candidate 1's optical sign remains unknown. Both Candidate 2 variants read the
separately authorised genuine improvement in the correct direction, while
their USM readings remain unity rather than increasing. Under the audit's
registered rule requiring both USM and improvement to rise, neither variant is
a measured frontier coordinate. Neither Candidate 2 variant is optically
wrong-signed.

### Original optical gap

Candidate 2's blur and improvement paths are already implemented, but the
frozen runner correctly refuses them behind the closed mandatory gate
(`experiments/M-CAND2/src/run_v2.py:524-551,604-630`;
`experiments/M-CAND2/out/amendment-downstream-gate.json:2-5`). The original
campaign and audit therefore recorded both cells as **NOT RUN**. The values now
shown above come only from the separately frozen post-mortem protocol below;
they do not alter or bypass the historical gate.

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

<!-- CAND2-POSTMORTEM-RESULTS -->

## Post-mortem optical-sign results

Authoritative preregistration commit
`e17439485c01713a7cb997700c35e2ae7c539deb` preceded both invocations. The
degraded sigma-`1.35` lock was created and accepted before the improved
sigma-`0.35` lock. The independent checker then recomputed the held-out
statistics and all four 10,000-draw bootstraps from the stored score arrays
without regenerating observations.

The cited artifacts are under the frozen external session directory named in
the preregistration. Native and display variants share observations and are
reported separately rather than pooled.

| Variant / arm | Baseline \(d'^2\) | Arm \(d'^2\) | Ratio \(R\) | Two-sided 95% ratio CI | One-sided LCB95 / UCB95 | Condition-number range, baseline -> arm | Frozen arm disposition |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Native / blur | `6.0122885561019395` | `1.6709379625636285` | `0.2779204535796564` | `[0.23055319880698877, 0.32707789521097985]` | `0.23762270338291042 / 0.31924656354176933` | `[170061.28994016047, 192546.99477967757] -> [152739.90574990198, 211302.7015871064]` | `RESOLVED_NONUNITY`; `blur_meaningfully_nonunity=true` (`degraded-result.json:169-237`) |
| Display / blur | `6.012288528538082` | `1.6709360166296494` | `0.27792013119436004` | `[0.2305493062942622, 0.3270771541765442]` | `0.23762157399178782 / 0.31924900900161624` | `[170061.2899398179, 192546.9947799625] -> [152739.90574989485, 211302.7015868653]` | `RESOLVED_NONUNITY`; `blur_meaningfully_nonunity=true` (`degraded-result.json:79-165`) |
| Native / improvement | `6.0122885561019395` | `14.806760617443636` | `2.4627494970140926` | `[2.130877002324432, 2.830351341335454]` | `2.177137250041903 / 2.7712421495813917` | `[170061.28994016047, 192546.99477967757] -> [165738.71228594956, 197373.84917382186]` | `RESOLVED_NONUNITY`; `improvement_meaningfully_above_one=true` (`improved-result.json:169-237`) |
| Display / improvement | `6.012288528538082` | `14.806739119088967` | `2.4627459325690912` | `[2.1308765706910395, 2.8303506158618172]` | `2.1771378823874796 / 2.7712409599177183` | `[170061.2899398179, 192546.9947799625] -> [165738.71228618408, 197373.84917387666]` | `RESOLVED_NONUNITY`; `improvement_meaningfully_above_one=true` (`improved-result.json:79-165`) |

At the frozen precision, neither blur ratio is `≈1`: each complete CI is
strictly below `[0.99,1.01]`. Both improvement CIs are strictly above that
interval and both one-sided LCB95 values exceed `1.30`. The checker therefore
assigned both variants the mechanical label
`OUTCOME_3_PRIOR_WRONG_NEEDS_ANALYSIS`
(`postmortem-check.json:125-129`). This is the registered disposition, not a
lane adjudication of Candidate 2.

### Artifact identity

- Preregistration-block SHA-256:
  `617c1710b4b972138641523a654d5e78f90777b9170867c0cb14390cda5f9b99`
- Degraded result SHA-256:
  `ca44516f7ea16a7248b6bfad3bb8cf0ef2ab5bf0dec86e5b574be4f2b916ad59`
- Degraded score-array SHA-256:
  `8c45a6b0563ae20006ed6c7b49c64d3d8296d0f630fadca5e9e96f3439e61824`
- Improved result SHA-256:
  `086508fca6f06593049fc218da6465108e10eeafa3aeeabe8d704b5ab539a1b3`
- Improved score-array SHA-256:
  `2b5170d8c3332ec9ea4d79ecb1b899d4c68d43135d108fcce6f11e45a68c7ec4`
- Final independent-check SHA-256:
  `ef9ed89311b18eaf4cd31607d1109a574916ea3909c0c384650c3965e11bd111`

The historical downstream gate remained closed and byte-identical at
`b030945a6cb11ac17895175fee3b1cc03b302b5f2819baa3c0fee423bc551408`.
Candidate 2's historical `DEAD` status was not reopened.

## Post-run operator classification and proposed physical confirmation

### What the frozen improvement arm was

**The arm was synthetic and signal-linear, but it was not a common linear
operator on the complete realised observation.** The generator replaces each
latent template with a periodic Gaussian-filtered template at sigma `0.85`,
`1.35`, or `0.35`; Gaussian filtering is a linear shift-invariant operation
on that planted signal (`experiments/M-CAND2/src/cand2.py:248-253,338-355`).
It then adds the target to an unfiltered nuisance field and draws fresh,
arm-specific noise before rendering
(`experiments/M-CAND2/src/cand2.py:255-335,354-355`).

Thus the improved signal component is produced by a linear operator, but the
arm is not `Y_improved = A Y_base`: applying `A` to the baseline observation
would also transform its nuisance and already-drawn noise, while the actual
arm leaves nuisance unfiltered and replaces the noise draw. Candidate 2's
exact USM congruence theorem therefore does not predict equality for this
fixture. The measured optical response establishes the correct direction for
this pre-noise synthetic forward model; it does not establish transfer to a
denser real focus bracket. Because the signal intervention is synthetic and
linear, the real pair is necessary rather than optional for the requested
acquisition-side confirmation.

### Proposed real-photon confirmation — not executed

Outcome 3 makes a development-only confirmation on
`high-res-calibration-slide-cpl` eligible. This section proposes that work; it
does not authorise or take the reading. No capture under `D:\personal\macro`
was opened for this proposal.

1. **Task-admissibility gate first.** The existing Candidate 2 implementation
   cannot lawfully score two natural renders merely by treating "dense" and
   "sparse" as its classes. It requires a target variable, symmetric target
   alternatives, an independent zero-target covariance population, and
   separate derivative and held-out observations
   (`experiments/M-CAND2/PREREGISTRATION.md:9-50`). Before any render is
   opened, freeze a physical task from a traceable slide design or an
   independent source-side reference with enough guard-separated instances.
   The dense stack may not define its own labels or truth. If the capture
   supplies no such task, report **UNCOMMISSIONED — NO LAWFUL TARGET TASK**
   and stop; substituting an output sharpness proxy would no longer be
   Candidate 2.
2. **Freeze provenance and execution.** Bind the exact read-only RAW
   manifests, `FocusPosition2` inventory, production source and executable
   hashes, linear pre-tone output stage, merge settings, lane-owned warpmaps,
   private output root, target support, 480 disjoint sites, folds, covariance
   dimension, seeds, conditioning gates, interval construction, and effect
   rule before rendering either stack. Do not transfer the synthetic `1.30`
   bar without an arm-blind power calculation.
3. **Prove the intervention and geometry.** Verify that both stacks cover the
   same registered physical depth interval and that the dense bracket
   materially reduces the maximum nearest-focus gap at the scored sites.
   Freeze cross-capture photometric, scale, rotation, and local
   nontranslation gates using input-only fiducials disjoint from scored
   sites. Existing development evidence makes this a real refusal risk: the
   released global maps report held-out errors `12.0952 px` and `8.6621 px`,
   both above the product's `4 px` usability threshold
   (`docs/research/cover-default.md:590-599`). A failed potency or geometry
   gate is **UNCOMMISSIONED**, not a detail loss.
4. **Run two density comparisons in frozen order.** First compare the full
   182-frame `tilted-sw4-cpl` output with a predeclared,
   endpoint-preserving 92-frame subset of that same capture. This isolates
   sampling density from the 100-second cross-capture gap. Only if it is
   admissible, compare full `tilted-sw4-cpl` against independent
   `tilted-sw10-cpl`. Keep native and any separately justified
   display-referred forms separate, and bootstrap acquisition block then
   site as in the synthetic campaign.
5. **Commission null and noise behavior.** An exact-copy scorer null must be
   quiet. The `6 s / 2.5 s / 1 s` flat ladder is a no-target and
   photon-noise guard: no rung may exceed a frozen shuffled/zero-target null,
   and the noisier `1 s` rung may not outrank `6 s`. Because the flat contains
   no target task, a near-zero denominator must produce a refusal rather than
   an unstable ratio.

The proposed confirmation is positive only if the within-capture density arm
and the independent dense-versus-sparse arm both move Candidate 2 in the
preregistered better-detail direction, with the same lawful physical task and
all potency, rank, provenance, and geometry gates passing. A cross-capture
increase without the within-capture result is a capture-confounded finding;
a null or wrong sign in both is a failure of transfer from the synthetic
optical result. In every case the calibration-slide session remains
development material and cannot supply a scored or SOTA result
(`docs/STATUS.md:2496-2547`).
