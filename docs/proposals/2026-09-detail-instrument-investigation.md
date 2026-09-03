> **Status: Investigation.**

# Detail instrument investigation

This proposal ranks exactly three candidate instruments. It commissions none of
them. The purpose is to find out whether any finite implementation preserves the
properties of its population estimand well enough to restore M1.

## Verified from repository sources

- The independent audit measured three slant-edge implementations. Their post-render
  radius-1, amount-0.5 unclipped-float USM ratios were `1.098673`, `1.098679`, and
  `1.092354`, with no detector, even though all three passed identity, physical blur,
  and sigma-1.20 genuine-improvement controls
  (`docs/research/M-PHASE0-SLANTEDGE.md:55-70`, “Independent commissioning”).
- Affine tone was not a sufficient control: gamma-3 raised the three MTF50 readings
  by `17.41%`-`17.67%`, a strictly increasing logistic curve raised them by
  `49.30%`-`50.71%`, and the registered noise arm also defeated every implementation
  (`docs/research/M-PHASE0-SLANTEDGE.md:83-100`, “Tone” and “Noise”).
- In the first survivor follow-up, `S_25` read USM as `0.995819x` but moved
  `4.8400x` under gamma-3 and `18818.9045x` under logistic tone. `Q25` read USM as
  `5.560744x` and the genuine improvement as `0.977981x`, the wrong sign
  (`docs/research/M-PHASE0-SLANTEDGE.md:173-226`, “SCORECARD-BASELINE M1” and
  “V-HEADTOHEAD3 licensed ordinal Q25”).
- The later 64-site hardening run overturned even the apparent native-`S_25`
  sharpening safety: its USM ratio was `1.028294`, and none of six frozen variants
  combined tone invariance, sharpening safety, correct optical direction, noise
  robustness, and the angle contract
  (`docs/research/M-PHASE0-SLANTEDGE.md:231-237,258-290`, “S25 hardening build”).
- Scorecard revision 1.4 withdrew M1's statistic and bar, and that withdrawal remains
  in the current scorecard. M1 is `UNMEASURED`; no detail or matched-information claim
  is licensed until a replacement statistic and numeric bar survive commissioning
  (`docs/proposals/2026-09-sota-scorecard.md:18-22,376-381,431-473`,
  “M1 — WITHDRAWN”).
- The current scorecard requires a future replacement to distinguish pre-sensor blur
  from genuine optical improvement, resist USM and tone challenges, reject
  common-mode agreement, and pre-register its numerical bars before score data are
  read (`docs/proposals/2026-09-sota-scorecard.md:465-485`, “Exact computation”,
  “Success”, “Known defeat”, and “Required controls”).
- The existing repeat route is not an available fallback: the repository records
  spatially varying geometry, data-dependent registration, and stable fixed-pattern
  structure as the three blockers, while same-frame FRC leaves a common-mode
  adversary at `0.972099`
  (`docs/STATUS.md:1423-1448`, “The detail axis has no instrument”).
- The prior survivor battery used `USM <=1.01` and tone movement `<=1%`; the
  scorecard already requires confidence intervals to resample physical sites rather
  than pixels with a fixed-seed hierarchical bootstrap
  (`docs/research/M-PHASE0-SLANTEDGE.md:161-165`;
  `docs/proposals/2026-09-sota-scorecard.md:87-94`, “Decision rule”).

## Reasoned from theory

Everything in this section is a proposal or deduction, not a repository measurement.

### The central distinction: estimand is not estimator

For a target variable \(X\), complete output tile \(Y\), and deterministic
post-processing \(T\), the Markov chain \(X \rightarrow Y \rightarrow T(Y)\)
gives

\[
I(X;T(Y)) \le I(X;Y).
\]

If \(T\) is one-to-one on the observed support, equality holds. The same operational
ordering holds for Bayes-optimal task risk: a decision rule using \(T(Y)\) could
always have been composed with \(T\) and applied to \(Y\). This is the population
data-processing argument [Cover and Thomas, DOI
10.1002/047174882X](https://doi.org/10.1002/047174882X).

**Ideal-observer invariance is theory. It is not evidence that any finite classifier
works.** A finite observer, covariance estimate, copula fit, feature map, or
regularizer can reward USM even when the true estimand cannot. It can fit ringing,
benefit from a representation that suits its restricted model, or exploit target
leakage. Every row below therefore separates a theorem about the estimand from a
claim about the estimator.

The tone claim is also narrow. A fixed pointwise **strictly monotone float**
transform is invertible and therefore preserves the population information. The
guarantee does not extend to clipping, quantization, ties, spatially adaptive tone,
or an unknown non-injective pipeline. Clipping and quantization must make the
reported value lower or trigger an explicit refusal. An upward result is a defeat,
even if a population theorem says that result is estimator bias.

**Binding first-arm rule:** radius-1, amount-0.5 USM is applied after rendering in
unclipped float and is the first arm run against every candidate. A value above the
frozen `1.01` limit, an under-powered equivalence result, or any estimator change
after seeing that result kills that candidate version outright. There is no retune.
A candidate that needs tuning to pass sharpening has failed sharpening.

### Common task and reporting contract

- \(X_f\) is a balanced, hidden target/task variable whose alternatives differ in a
  pre-registered band \(f \le 0.25\) cycles/native pixel and have no lower-frequency,
  position, file-name, or periodic-answer cue.
- \(Y\) is the complete registered output tile, all licensed channels included.
  Cropping to an answer-bearing edge, selecting a favorable cell, or substituting a
  stacker's internal focus/confidence product changes the estimand and is forbidden.
- Every candidate emits a scalar \(J\) for which higher means more task information,
  plus a band/task curve. A positive, non-saturated base response is required.
- Arm comparisons are paired by independent macro-tile. For positive \(J\), report
  \(R=J_{\mathrm{arm}}/J_{\mathrm{base}}\), its paired log ratio, and a one-sided
  95% cluster-bootstrap bound. Do not floor a failed or negative estimate into a
  pass.
- The `1.01` USM ceiling and `0.99`-`1.01` invertible-tone interval are retained.
  A directional optical arm must also exceed a pre-registered minimum effect chosen
  by an arm-blind power calculation; mere sign noise is not usable dynamic range.

### Ranked candidate matrix

| Rank and candidate | Tone argument and exact stopping point | Sharpening argument | Genuine-optics response and usable range | Required estimator and data | First kill arm and honest expectation |
|---|---|---|---|---|---|
| **1. Target-conditional ideal-observer information** | Population \(I(X;Y)\) and Bayes-optimal risk are unchanged by a bijective point transform. This covers strictly monotone float gamma/logistic transforms. Clipping, quantization, ties, or adaptive/non-injective tone must lower the value or refuse. A trained observer does not inherit the theorem. | DPI makes non-increase a theorem about the estimand; injective unclipped USM gives equality. A finite classifier or variational MI estimate can rise because sampling, model fit, and leakage are estimator properties. | For a task whose alternatives differ only in a licensed near-limit band, better pre-noise transfer raises information and lowers Bayes error; added pre-noise blur does the reverse. Report bits/tile, \(I/H(X)\) in `[0,1]`, and task error across bands rather than an edge cutoff. | Prefer an exact or simulation-calibrated likelihood-ratio observer. Otherwise use one frozen cross-fitted probabilistic pipeline to estimate a population variational lower bound. A finite held-out realization is not itself guaranteed to bound MI. It needs many independent random patterns, independent noise/nuisance realizations, and untouched macro-tile test clusters. | **USM r1/a0.5.** Population expectation is equality. Finite-estimator expectation is **UNKNOWN but best of the three** if exact likelihoods are feasible; a learned observer is not presumed GREEN. |
| **2. Full-covariance Fisher information or task-based NEQ** | Exact Fisher information is invariant under an invertible observation transform. Conventional mean/covariance NEQ is exactly invariant to nonsingular linear transforms, not arbitrary nonlinear tone. Gamma/logistic therefore remain empirical kill arms unless the full transformed likelihood and Jacobian are modeled. Clipping/quantization must lower or refuse. | Fisher information obeys a data-processing inequality. For linear USM \(A\), full covariance gives \((A d)^T(AKA^T)^{-1}(A d)=d^TK^{-1}d\). That equality is both an estimand result under the model and a finite-sample algebraic property only for full-rank, unregularized, congruence-equivariant estimation. Diagonal covariance, shrinkage, channel selection, and pseudoinverses lose it. | For a local modulation/detection task, sharper pre-noise transfer increases \(d'^2\), Fisher information, or NEQ in the affected band when downstream sampling/noise is limiting; blur decreases it. Report \(d'^2\), information ratio, and decibels over a task ladder. No sign is promised for a noiseless invertible optical change. | Estimate a score or symmetric finite-difference mean derivative and the entire pixel covariance from independent realizations. Require more independent clusters than dimensions, a frozen conditioning gate, and no outcome-chosen shrinkage. A task-NEQ implementation must state and test its local-linear, stationary-noise assumptions. | **USM r1/a0.5.** Expect **GREEN only** for the full-rank unregularized form, where cancellation is algebraic. If sample count forces shrinkage or projection, expect refusal or RED, not a repair. |
| **3. Rank/copula repeat information** | Population repeat MI and empirical marginal ranks are invariant to coordinatewise strictly monotone float transforms when there are no ties. Clipping and quantization create ties; never jitter them, and require a lower value or `REFUSED_TIES`. Spatially adaptive tone is outside the claim. | True full-vector \(I(Y_A;Y_B)\) cannot increase when deterministic post-processing is applied to either repeat and equals base for invertible USM. Practical per-pixel, band-projected, or Gaussian-copula estimates are not generally invariant to USM's spatial mixing; their resistance is only an estimator property. | With independent repeat noises, improved pre-noise transfer raises shared target SNR and repeat information in the affected band; blur lowers it. For a Gaussian scalar pair, \(I=-\tfrac12\log_2(1-\rho^2)\). Report bits/independent mode and the curve, avoiding \(\rho\) floor and ceiling. Shared FPN can move it upward without target information. | Two genuinely independent repeat outputs for every unseen random pattern; training-fold empirical CDFs; held-out rank transforms; and a frozen multivariate copula/canonical-correlation estimator. Complete-vector estimation is sample hungry. Any dimension reduction changes the estimator and must be frozen before USM. | **USM r1/a0.5.** Population expectation is equality, but the practical estimator has the **highest RED risk** because spatial mixing changes its fitted copula/projection. Expect failure unless the full-vector estimator is demonstrably equivariant. |

### Candidate 1 — target-conditional ideal-observer information

#### Estimand

For each licensed task band, the primary estimand is

\[
J_1(f)=I(X_f;Y),
\]

in bits per complete tile. For a discrete task, the operational companion is
Bayes-optimal error, accuracy, or area under the ROC curve under a fully specified
loss. The task prior is balanced and frozen. Using \(X_f\), rather than agreement
between two images, is important: repeatable FPN that is independent of \(X_f\)
is nuisance, not target information.

The target must vary independently across macro-tiles. Low-frequency envelope,
mean, contrast, support, and position must be matched across target alternatives,
or the observer can solve the wrong task while reporting a valid information
number.

#### Tone, sharpening, and optics

A strictly monotone float transform and injective float USM preserve the sigma
algebra generated by \(Y\), so the true \(J_1\) and Bayes optimum are unchanged.
Non-injective deterministic processing can only reduce them. A genuine optical
change is different: it acts before sampling and independent downstream noise. On
a task placed where detector noise or sampling loses distinctions, stronger optical
transfer separates the conditional distributions and should raise \(J_1\); blur
should merge them and lower it. The expected response must be established on a
forward model before the candidate sees outcomes.

#### Estimator and data burden

The preferred implementation evaluates known likelihoods or a validated generative
forward model by Monte Carlo and computes a likelihood-ratio ideal observer
[Barrett, DOI 10.1364/JOSAA.7.001266](https://doi.org/10.1364/JOSAA.7.001266).
If exact likelihoods are unavailable, freeze a probabilistic observer
\(q(X\mid Y)\). Its **population** variational functional is

\[
J_q=H(X)+E_{p(X,Y)}\log_2 q(X\mid Y)\le I(X;Y).
\]

The held-out sample mean estimates \(J_q\), but a finite realization can exceed both
\(J_q\) and true MI. Only a coverage-qualified one-sided lower confidence bound,
conditional on the already-frozen \(q\), may be described as a probabilistic lower
bound. Neither quantity is true MI or an ideal observer. Separate arm-specific fits
may use the same already-frozen code, architecture, initialization schedule,
training count, and stopping rule; no USM augmentation, inverse-USM preprocessing,
pooled arm training, or post-result hyperparameter choice is allowed. The paired
base-versus-USM test asks whether this concrete finite pipeline inherits the
required behavior. Failure kills it even though the population theorem remains true.

The data requirement is driven by independent pattern, noise, nuisance, and
macro-tile counts, not pixel count. Learning curves must plateau on development
folds before the sealed test is opened. Chance performance, a loose bound, or a
saturated task is a refusal rather than evidence of invariance.

#### First-kill preflight

Analytically, \(J_1(X;U(Y))\le J_1(X;Y)\), with equality expected for unclipped
injective USM. No candidate implementation exists yet, so this is a theoretical
preflight, **not an empirical pass**. A finite learned observer remains genuinely
at risk of reading USM ringing or leakage as useful structure.

### Candidate 2 — full-covariance Fisher information or task-based NEQ

#### Estimand

For a scalar task parameter \(\theta\), exact Fisher information is

\[
J_2(\theta)=E\left[\left(\partial_\theta\log p(Y;\theta)\right)^2\right].
\]

For a local binary task under a Gaussian model, the full-covariance Hotelling form is

\[
d'^2=(\mu_1-\mu_0)^T K^{-1}(\mu_1-\mu_0).
\]

Task-based NEQ is the corresponding frequency/task representation under local
linear, shift-invariant, stationary-noise assumptions
[Wagner and Brown, DOI 10.1088/0031-9155/30/6/001](https://doi.org/10.1088/0031-9155/30/6/001).
Fisher information and task performance are linked but not interchangeable outside
their stated model
[Barrett et al., DOI 10.1364/JOSAA.12.000834](https://doi.org/10.1364/JOSAA.12.000834).

#### Tone, sharpening, and optics

For \(Z=T(Y)\), the transformed score is the conditional expectation of the
original score given \(Z\); taking its variance proves that Fisher information
cannot increase. A bijection gives equality. This covers strictly monotone float
tone for **exact** Fisher information.

The convenient Hotelling/NEQ estimator has a narrower guarantee. If USM is a fixed
nonsingular linear matrix \(A\), sample means and the unregularized sample covariance
transform by congruence, so the quadratic form cancels \(A\) exactly up to arithmetic.
A nonlinear gamma/logistic transform does not preserve a mean/covariance quadratic
form. Calling that approximation “Fisher information” would not repair it; it must
model the full transformed likelihood or survive the tone arms empirically.

For a small modulation at frequency \(f\), the local-linear expectation is
\(J_2(f)\) proportional to squared optical transfer divided by full noise power after
cross-frequency covariance is accounted for. Thus a pre-noise improvement should
raise information and blur should lower it in the designed band. If there is no
downstream noise, sampling loss, or task-relevant null space, an invertible change
of optical blur need not change information; such a fixture has no power.

#### Estimator and data burden

Use symmetric parameter perturbations to estimate the complete-tile mean derivative
and estimate \(K\) from independent realizations not reused for that derivative.
The covariance must include every pixel/channel cross-term used by the task. Require
independent cluster count greater than vector dimension and a frozen eigenvalue/
condition-number refusal gate. A diagonal approximation is not “full covariance.”
Identity shrinkage, outcome-chosen channels, and an ordinary pseudoinverse are
forbidden because they can turn an invertible USM coordinate change into an apparent
gain.

The output is \(d'^2\) or Fisher-information ratio by task band, with uncertainty
from independent macro-tiles. NEQ may be reported only as a local model diagnostic;
failure of stationarity or linearity refuses the NEQ interpretation.

#### First-kill preflight

The unregularized full-rank estimator should survive USM by finite-sample algebra,
which makes this candidate more testable than a learned observer. Its likely
practical failure is data dimensionality: if \(n\le p\), the correct result is
refusal, not a shrinkage retune after USM.

### Candidate 3 — rank/copula repeat information

#### Estimand

Let \(Y_A\) and \(Y_B\) be complete outputs from genuinely independent noise
realizations of the same independently randomized target. The population estimand is

\[
J_3=I(Y_A;Y_B),
\]

reported by target band. Probability-integral transforms expose the copula while
discarding continuous marginal scale. A practical Gaussian-copula estimator may use
normal scores and held-out canonical correlations, following the estimator family in
[Ince et al., DOI 10.1002/hbm.23471](https://doi.org/10.1002/hbm.23471).

#### Tone, sharpening, and optics

Separate bijections of \(Y_A\) and \(Y_B\) preserve their population MI. Empirical
ranks also remain bit-identical under a coordinatewise strictly monotone transform
when evaluated on the same untied samples. This is the strongest estimator-level
tone property among the three candidates.

It is not an estimator-level sharpening theorem. USM mixes spatial coordinates, so
per-pixel ranks, a truncated canonical basis, and a Gaussian-copula approximation can
all change even when complete-vector MI is equal. A claim based on a projection must
survive USM as implemented, not cite the full-vector theorem.

With a shared Gaussian target coefficient of variance \(S\) and independent repeat
noise \(N\), repeat correlation rises with \(|H(f)|^2S/N\), and repeat information
rises with it. This supplies the expected optical sign and a bits/mode dynamic range.
It also exposes the fatal ambiguity: a fixed sensor pattern shared by both repeats
raises the same statistic without conveying target information.

#### Estimator and data burden

Fit every marginal empirical CDF on training macro-tiles only, then transform sealed
tiles without re-ranking them jointly with test data. Fit the joint copula/canonical
correlations on training folds and evaluate a bias-corrected held-out score. The
number of independent pattern pairs must dominate the retained joint dimension. If
that forces dimension reduction, the reduction is a frozen part of the estimator and
receives no theorem beyond what it actually preserves.

An external fixed-pattern model may be applied only if frozen from independent
calibration data. Fitting and subtracting common structure from the same repeat pair
would manufacture the desired answer.

#### First-kill preflight

The complete-vector population value should equal base under injective USM. The
finite rank/copula procedure is the candidate most likely to die on the first arm,
because its tractable projection is unlikely to be equivariant to spatial mixing.
That is a useful early result, not a reason to adjust the basis.

### Leakage firewall

These rules apply to training, covariance estimation, marginal-rank fitting, model
selection, and uncertainty estimation for all three candidates.

1. **Withheld random patterns.** Generate sealed-test target patterns from an
   unrevealed seed after the complete estimator and training pipeline are frozen.
   No test pattern, cyclic shift, mirror, crop, or deterministic derivative may occur
   in training or validation.
2. **Randomized assignment.** Re-randomize the target-to-position assignment for each
   independent repeat and balance classes within macro-tiles. Strip coordinates,
   filenames, sequence indices, metadata, and border conventions from observer input
   unless they are explicitly part of \(Y\).
3. **Guard regions.** No training crop may overlap a test crop. The guard width is at
   least the largest of optical support, estimator receptive field, registration
   uncertainty, and any preprocessing support. The exact width is frozen with the
   eventual acquisition design.
4. **Macro-tile folds.** Every target cell, augmentation, repeat, nuisance arm, and
   neighboring crop from one macro-tile stays in one fold. Entire acquisition
   sessions remain clustered; cells are pseudo-replicates and are never split across
   train and test.
5. **Cluster bootstrap.** Resample acquisition/session first and independent
   macro-tile second, using 10,000 fixed-seed draws. Never bootstrap pixels or target
   cells as independent observations.
6. **Leakage sentinels.** A coordinate/metadata-only observer, a no-target image arm,
   and a held-out label-permutation arm must remain at chance with their one-sided
   bounds. Any success exposes leakage and kills the estimator.
7. **One opening.** The sealed test is evaluated once. Architecture, channels,
   shrinkage, stopping, calibration, thresholds, and refusal gates may not change
   after any test-arm output is read.

**An observer that has memorized the target measures nothing.** High test performance
without unseen random patterns, guards, macro-tile folds, and cluster-level
uncertainty is not an approximation to the ideal observer.

### Commissioning battery — frozen order

No later arm is run until the preceding arm is adjudicated. Every transform operates
on paired data, and arm construction is independent of the candidate code. A RED
kills the frozen candidate. Refusal is a pass only where the row explicitly permits
it.

| Order | Arm | Required behavior |
|---:|---|---|
| **1** | **Post-render USM, radius 1 / amount 0.5** | Apply one fixed unclipped-float implementation to the complete output tile. The one-sided 95% cluster-bootstrap upper bound on \(R\) must be `<=1.01`. Otherwise kill immediately. No retune, augmentation, inverse filter, basis change, covariance change, or threshold change is permitted. |
| **2** | **Gamma-3** | Apply a strictly increasing float point transform with no clipping or quantization. The complete `0.99 <= R <= 1.01` equivalence interval must hold. |
| **3** | **Logistic** | Apply the frozen strictly increasing float logistic transform with no clipping or quantization. Require the same equivalence interval. |
| **4** | **Pre-noise blur** | Degrade optical transfer before fresh independent noise. \(J\) must fall by the pre-registered powered amount; wrong sign, blindness, or an interval crossing the minimum effect is RED. |
| **5** | **Pre-noise genuine improvement** | Improve optical transfer before fresh independent noise without changing the target prior. \(J\) must rise by the pre-registered powered amount. A statistic that survives USM by being blind is RED. |
| **6** | **Common-mode fixed-pattern noise** | Add the same target-independent spatial field to repeats while the independent reference/labels stay fixed. The candidate must not report improvement. Target-conditional candidates must stay equal/lower; a repeat candidate may explicitly refuse violated independence. |
| **7** | **Added noise** | Add independent post-optics noise at frozen levels. Information must decrease monotonically. Any significant improvement or non-monotone powered reversal is RED. |
| **8** | **Clipping/refusal** | Apply registered saturation and quantization challenges. The value must be lower or the checker must emit an explicit clipping/ties refusal before a number. Jittering ties or reporting an increase is RED. |
| **9** | **Geometry** | A lossless whole-tile coordinate permutation is a null. Crop, support loss, scale change, interpolation, or nonrigid mismatch must trigger the geometry refusal rather than a resolution number. Selection after inspecting an output is RED. |
| **10** | **Train/test leakage** | Open only withheld random patterns with guards and macro-tile folds. Coordinate-only, no-target, and label-permutation sentinels must be chance. Bootstrap by session/macro-tile. Any target memorization or pseudo-replicate confidence is RED. |

### Decision after the battery

- Candidate 1 is the only row for which sharpening non-increase and monotone-tone
  invariance are both exact properties of the desired task estimand. It remains first
  because this removes two conceptual failure modes, not because a classifier has
  passed anything.
- Candidate 2 has the cleanest finite-sample USM cancellation if the full covariance
  is estimable without regularization, but nonlinear-tone invariance belongs only to
  exact Fisher information.
- Candidate 3 has exact empirical rank invariance to monotone tone but the weakest
  practical sharpening and nuisance story. Common-mode fixed pattern is an especially
  credible later kill even if USM happens to pass.

It is acceptable for all three to fail. If no frozen estimator passes its own first
USM arm, the conclusion is **NO ADMISSIBLE ESTIMATOR**, not permission to weaken the
arm. If a candidate passes synthetics but the independence, dimensionality, or
leakage requirements cannot be met, M1 remains `UNMEASURED`.

### Literature and DOI-resolution ledger

Each DOI below was sent to `https://doi.org/` on 2026-09-03. The resolver reached the
listed publisher URL; Wiley then returned an automation `403` for two resolved pages,
which does not change the DOI mapping.

| Topic | Reference | DOI and observed resolver destination |
|---|---|---|
| Data-processing inequality | T. M. Cover and J. A. Thomas, *Elements of Information Theory*, 2nd ed., Wiley, 2006 | [10.1002/047174882X](https://doi.org/10.1002/047174882X) -> `onlinelibrary.wiley.com/doi/book/10.1002/047174882X` |
| Ideal observer/task image quality | H. H. Barrett, “Objective assessment of image quality: effects of quantum noise and object variability,” *JOSA A* 7, 1990 | [10.1364/JOSAA.7.001266](https://doi.org/10.1364/JOSAA.7.001266) -> `opg.optica.org/josaa/abstract.cfm?uri=josaa-7-7-1266` |
| Fisher information/task performance | H. H. Barrett, J. L. Denny, R. F. Wagner, and K. J. Myers, “Objective assessment of image quality II: Fisher information, Fourier crosstalk, and figures of merit for task performance,” *JOSA A* 12, 1995 | [10.1364/JOSAA.12.000834](https://doi.org/10.1364/JOSAA.12.000834) -> `opg.optica.org/josaa/abstract.cfm?uri=josaa-12-5-834` |
| Task-based NEQ | R. F. Wagner and D. G. Brown, “Unified SNR analysis of medical imaging systems,” *Physics in Medicine and Biology* 30, 1985 | [10.1088/0031-9155/30/6/001](https://doi.org/10.1088/0031-9155/30/6/001) -> `iopscience.iop.org/article/10.1088/0031-9155/30/6/001` |
| FRC resolution measurement | R. P. J. Nieuwenhuizen et al., “Measuring image resolution in optical nanoscopy,” *Nature Methods* 10, 2013 | [10.1038/nmeth.2448](https://doi.org/10.1038/nmeth.2448) -> `www.nature.com/articles/nmeth.2448` |
| Gaussian-copula MI estimator | R. A. A. Ince et al., “A statistical framework for neuroimaging data analysis based on mutual information estimated via a Gaussian copula,” *Human Brain Mapping* 38, 2017 | [10.1002/hbm.23471](https://doi.org/10.1002/hbm.23471) -> `onlinelibrary.wiley.com/doi/10.1002/hbm.23471` |

FRC is cited as the relevant independent-repeat resolution literature, not introduced
as a fourth candidate
[Nieuwenhuizen et al., DOI 10.1038/nmeth.2448](https://doi.org/10.1038/nmeth.2448).
Its independence requirement is precisely why shared FPN and leakage are explicit
commissioning arms here.

## Capture prescription — placeholder owned by the capture lane
