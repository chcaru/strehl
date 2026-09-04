# M138 — W1 gate audit

## Verdict

**H2.** `NO_COMMON_K` is a verdict of the legacy-width pre-gate, not a
demonstrated failure of the admission merge's Pareto performance. The frozen
width data make the pre-gate empty before any output is rendered. Phase 1 is
therefore **unvalidated, not rescued**. H1 also contains real defects: the
standardisation is not complete enough to support its claimed global meaning.

Tags: **[V] VERIFIED** means recomputed or read from primary code/artifacts in
this audit. **[I] INHERITED** means quoted from an existing narrative document.
A tag on a table heading applies to every numeric cell in that table. File
names, source-line locations, and hypothesis labels are identifiers rather
than quantitative claims.

## Scope and method

I used only the frozen files under `experiments/PHASE1-DESIGN/results/` and the
checked-in Python/Rust sources. I did not open the quarantine and did not
access either read-only `D:\` tree. The audit script independently recomputes
every stored width ratio and error from candidate and legacy `n_eff`, rebuilds
the admissible grid sets, and cross-checks every failure tuple in `gate.json`.

The script is `audit.py`; machine-readable results are under `out/`.
`verify.ps1` is a second implementation in another language; it does not
import or call the Python audit.

- [V] All frozen hashes named by `results/run.json` matched both before and
  after the audit.
- [V] Maximum disagreement with the stored ratios: `0`.
- [V] Maximum disagreement with the stored width errors: `0`.
- [V] Failure-ledger disagreements against `gate.json`: `0`.
- [V] Instrument commissioning passed in both directions: consistent
  arithmetic and overlapping intervals stayed GREEN; a corrupted stored ratio
  and planted-disjoint intervals went RED. The variance-propagation control
  likewise kept its constant-variance null GREEN and made its
  heteroscedastic plant RED.
- [V] The independent PowerShell implementation reproduced `42` predicates,
  the `16`/`26` split, an empty global intersection, no admissible predicate in
  bands `4`–`6`, no Pareto metrics, and unchanged frozen hashes.

Commands:

```powershell
python experiments\M138-w1-gate-audit\audit.py --self-test
python experiments\M138-w1-gate-audit\audit.py --audit
python experiments\M138-w1-gate-audit\audit.py --verify-report
& experiments\M138-w1-gate-audit\verify.ps1 -SelfTest
& experiments\M138-w1-gate-audit\verify.ps1
```

## Band convention

**[V] Band 0 is the finest, full-native-resolution Laplacian band. Band 6 is
the coarsest scored Laplacian band.** Their frozen score shapes are,
respectively, `512×512`, `256×256`, `128×128`, `64×64`, `32×32`, `16×16`, and
`8×8`. The unscored Gaussian base is the following pyramid element.

That follows directly from `reference.py:473-484`: Gaussian level zero is the
input, each later level is reduced by two, and Laplacian band `k` is
`gauss[k] - expand5(gauss[k + 1])`.

## Full legacy-width profile and each predicate's admissible `k`

**All numeric cells below are [V].** `D` and `F` mean the frozen detail and
flat ROIs. Intervals are inclusive points on the frozen **[V] `0.05`** grid; `∅` means
that predicate has no admissible value in the frozen range.

| capture (`N`) | band | legacy `n_eff`, D | D admissible `k` | legacy `n_eff`, F | F admissible `k` |
|---|---:|---:|---:|---:|---:|
| flat-on-ruler (`79`) | 0 | 2.051 | [1.75, 2.05] | 2.293 | [1.90, 2.20] |
| flat-on-ruler (`79`) | 1 | 3.883 | [6.05, 6.90] | 3.729 | [6.85, 7.90] |
| flat-on-ruler (`79`) | 2 | 7.813 | ∅ | 7.055 | ∅ |
| flat-on-ruler (`79`) | 3 | 18.261 | ∅ | 14.949 | ∅ |
| flat-on-ruler (`79`) | 4 | 37.094 | ∅ | 41.476 | ∅ |
| flat-on-ruler (`79`) | 5 | 66.447 | ∅ | 64.651 | ∅ |
| flat-on-ruler (`79`) | 6 | 77.818 | ∅ | 77.294 | ∅ |
| coffee-bubbles (`19`) | 0 | 4.055 | [1.35, 1.45] | 14.357 | [1.90, 2.20] |
| coffee-bubbles (`19`) | 1 | 3.230 | [2.90, 3.30] | 3.207 | [1.15, 1.25] |
| coffee-bubbles (`19`) | 2 | 6.123 | ∅ | 3.388 | [1.60, 1.70] |
| coffee-bubbles (`19`) | 3 | 12.133 | ∅ | 8.934 | [6.30, 7.15] |
| coffee-bubbles (`19`) | 4 | 15.938 | ∅ | 15.388 | ∅ |
| coffee-bubbles (`19`) | 5 | 15.960 | ∅ | 17.060 | ∅ |
| coffee-bubbles (`19`) | 6 | 16.554 | ∅ | 17.801 | ∅ |
| 113MSDCF (`63`) | 0 | 4.660 | [1.35, 1.40] | 59.806 | [2.10, 8.00] |
| 113MSDCF (`63`) | 1 | 5.569 | [3.35, 3.80] | 50.283 | [2.15, 2.60] |
| 113MSDCF (`63`) | 2 | 10.812 | ∅ | 27.547 | [1.90, 1.95] |
| 113MSDCF (`63`) | 3 | 22.605 | ∅ | 21.728 | [2.40, 2.55] |
| 113MSDCF (`63`) | 4 | 43.388 | ∅ | 51.644 | ∅ |
| 113MSDCF (`63`) | 5 | 59.416 | ∅ | 61.543 | ∅ |
| 113MSDCF (`63`) | 6 | 62.411 | ∅ | 62.565 | ∅ |

The legacy width is emphatically not band-invariant. **[V]** Its
largest/smallest cross-band ratios are:

| capture | ROI | legacy max/min |
|---|---|---:|
| flat-on-ruler | detail | 37.95× |
| flat-on-ruler | flat | 33.71× |
| coffee-bubbles | detail | 5.13× |
| coffee-bubbles | flat | 5.55× |
| 113MSDCF | detail | 13.39× |
| 113MSDCF | flat | 2.88× |

One premise in the charge needs correction: the legacy comparator does **not**
use one fixed soft-power exponent. `measure.py:129-141` computes:

```text
return min(2.0 * 1.4 ** (R.BANDS - 1 - band), 8.0)
```

Thus the comparator's target profile is explicitly band-shaped, in addition
to whatever shape band SNR produces. Its floor is also
**[V]** `4.5 * beta * variance`, whereas the candidate's below-floor branch is decided
at `F = beta * v_A`. The rules therefore have a broad structural regime in
which legacy can take its arithmetic-mean fallback while the candidate remains
an above-floor selector.

## The intersections are empty before Pareto

**All numeric cells below are [V].**

| band | width predicates with any admissible `k` | intersection across all captures/ROIs |
|---:|---:|---:|
| 0 | 6 of 6 | ∅ |
| 1 | 6 of 6 | ∅ |
| 2 | 2 of 6 | ∅ |
| 3 | 2 of 6 | ∅ |
| 4 | 0 of 6 | ∅ |
| 5 | 0 of 6 | ∅ |
| 6 | 0 of 6 | ∅ |

The failure is stronger than “the two ends of the band range want opposite
values”:

- [V] On coffee-bubbles band 0 alone, detail admits `[1.35,1.45]` while flat
  admits `[1.90,2.20]`.
- [V] On coffee-bubbles band 1 alone, detail admits `[2.90,3.30]` while flat
  admits `[1.15,1.25]`.
- [V] On 113MSDCF band 0 alone, detail admits `[1.35,1.40]` while flat admits
  `[2.10,8.00]`.
- [V] On 113MSDCF band 1 alone, detail admits `[3.35,3.80]` while flat admits
  `[2.15,2.60]`.

Those are same-capture, same-band contradictions between the two frozen ROIs.
Across both ROIs, only two capture-band cells have any interval at all:
**[V]** flat-on-ruler band 0 has `[1.90,2.05]`, and band 1 has
`[6.85,6.90]`; those two are themselves disjoint. The other **[V] 19 of 21**
capture-band cells are already empty.

So:

- [V] predicates with some admissible grid value: `16 of 42`;
- [V] predicates with none: `26 of 42`;
- [V] global width intersection: `∅`.

Legacy variation by itself would **not** prove that every conceivable
single-threshold rule must fail; a rule's `k → n_eff` curve can also vary by
band and content. The actual frozen intervals do prove that **this candidate
under this protocol** cannot pass. H2 is therefore established from the data,
not from that over-broad “by construction for any rule” assertion.

## What bands 4–6 failed

**[V] Bands 4–6 failed width only. Pareto was not evaluated.**

Every one of their **[V] 18 of 18** width predicates has an empty admissible
set. Even at the largest frozen grid point, their candidate/legacy width ratios
range only from **[V] 0.01690 to 0.69209**, below the required lower edge
**[V] 0.95**.

The preregistration says (**[I] source text**):

> A value survives only if all 42 pass.

and then (**[I] source text**):

> Only width survivors are rendered.

`measure.py:557-575` implements exactly that control flow with `if survivors:`.
The frozen records confirm **[V]** `width_survivors=[]`, `metrics={}`,
`render_provenance={}`, and `pareto_rendered=false`.

Therefore the banner's phrase “no predicate in bands 4–6 passes at any `k`”
describes width predicates. There are no band-4–6 Pareto results to pass or
fail.

## H2 ruling

The width condition is not a neutral test of whether `k` has one statistical
meaning. It requires a hard-admission/inverse-floor estimator to reproduce,
cell by cell, the Kish width of a different estimator whose:

1. exponent changes by band;
2. signal floor is multiplied by a different constant;
3. zero-weight state falls back to the full arithmetic mean; and
4. continuous weights give a different relation between `admitted frames` and
   Kish `n_eff`.

That is a comparator-equivalence requirement, not an output-quality
requirement. Because it is evaluated first and is empty, the gate never asks
the question it later claims answered: whether any one global candidate
threshold simultaneously preserves detail and reduces flat power.

The sentence in H1 that “if standardisation were correct and complete, one
global `k` would work by definition” is also too strong. Correct
standardisation gives a common **null probability scale**. It does not imply a
common `k` will reproduce another estimator's content-, band-, ROI-, and
stack-size-dependent Kish width.

## H1 audit: the standardisation is not complete

The candidate path in `measure.py:152-205` computes a winner, then

```text
sigw = (2*fw*fw + 4*fw*qw) / nu
sig  = (2*f*f   + 4*f*q)   / nu
threshold = (ew - e) / sqrt(sigw + sig)
```

This is commissioned well enough to show that the arithmetic is wired, but
not well enough to establish a common calibrated distribution on real,
non-null band coefficients.

### What is covered

**All numeric cells below are [V].**

| band | frozen `nu_eff` | measured `nu_eff` | pooled null coverage | worst-frame null coverage |
|---:|---:|---:|---:|---:|
| 0 | 8.0000 | 8.3548 | 95.598% | 94.948% |
| 1 | 10.0000 | 10.4873 | 95.694% | 94.644% |
| 2 | 9.5000 | 9.6358 | 95.464% | 94.263% |
| 3 | 9.0000 | 9.3891 | 95.576% | 93.726% |
| 4 | 9.0000 | 9.3337 | 95.458% | 89.453% |
| 5 | 9.0000 | 9.8293 | 95.858% | 84.766% |
| 6 | 7.5000 | 8.6848 | 95.953% | 78.125% |

The commissioning acceptance in `reference.py:1048-1068` checks pooled
coverage but records without gating on worst-frame coverage. This hides a
clear coarse-band per-frame coverage problem from the pass/fail decision.
Bands 4–6 are also the bands whose per-frame `beta` is replaced by a joint
log-linear fit
(`reference.py:621-650`).

**All numeric cells below are [V].**

| fitted band | maximum absolute log residual | corresponding multiplicative factor |
|---:|---:|---:|
| 4 | 0.05584 | 1.057× |
| 5 | 0.11375 | 1.120× |
| 6 | 0.24188 | 1.274× |

This is direct evidence that the fit departs from its per-frame trace
observations by a frame- and band-dependent amount. The direct coarse traces
are themselves noisy, so this is not a clean estimate of true scale error; it
is an unresolved calibration residual. It is not enough by itself to explain
the whole width gap, but it rules out calling the standardisation complete.

### What is not covered

1. **The noncentral term is not statistically commissioned.** The real
   coverage exercise in `reference.py:675-727` uses zero-mean white noise, so
   **[V]** `q=0`. The hand test checks the algebraic factor multiplying `Fq`; it does
   not check coverage when coherent signal makes **[V]** `q>0`. For correlated
   Gaussian band samples, the central and signal-dependent terms need not
   share one scalar effective sample count.

2. **The Poisson–Gaussian control covers only [V] band 0.**
   `reference.py:1081-1143` builds a one-band pyramid and indexes
   `frozen[0]`. No corresponding Poisson–Gaussian coverage exists for the
   coarse bands that fail worst-frame null coverage.

3. **Spatially varying variance is not propagated exactly.**
   `reference.py` sends `v_A` through the ordinary Gaussian image pyramid and
   multiplies by scalar `beta`. Rust's related path says the same thing
   explicitly in `pyramid.rs:372-384` (**[V] source text**):

   > Used for fields that are not images and must not be differenced: the
   > per-pixel noise variance, and any weight field a caller wants carried to
   > coarser grids.

   For a linear filter, exact variance propagation uses squared filter
   coefficients and covariance terms, not the image filter itself.

   The audit's commissioned one-dimensional control demonstrates the defect
   class. **[V]** With constant input variance, exact and current-form values
   both equal `0.2734375` and the null stays quiet. With a planted local
   variance profile `[1,1,10,1,1]`, exact propagation is `1.5390625`, while
   scalar-beta-times-Gaussian propagation is `1.1962890625`, an error of
   **[V] −22.27%**. This proves the form is not exact in general; it does not
   claim that exact error magnitude for W1's full Laplacian cascade.

4. **Winner selection is missing from the null.** `ew` is the maximum over the
   stack, but the denominator is the variance sum for two unselected frame
   statistics. The committed Rust core already states the problem verbatim:

   ```text
   **A fixed `threshold` is therefore an N-dependent statement**
   ```

   (`crates/strehl-core/src/merge.rs:417-424`). Phase 1's Python candidate
   selects the same kind of maximum and applies no order-statistic correction.

5. **There is no Phase-1 `sigma2_E` implementation in committed Rust core.**
   A committed-tree search found no `BandReference`, `winner_variance`,
   `FROZEN_NU_EFF`, or `sigma2_E` implementation. The production core still
   contains the older scalar-focus-field gate. Consequently there is no
   independent Rust/Python parity result for this proposed standardisation.

Inter-band covariance is not the first missing term: each admission decision
is marginal within one band. It would matter for a joint simultaneous-error
claim across bands, but the direct defects above already prevent a
“complete” ruling.

## Correctly designed gate

This requires two separate gates. Conflating them is what produced the present
verdict.

### A. Commission the statistical instrument independently of legacy

1. Build null and positive-control data with known equal focus and known focus
   offsets, spanning every band, actual warp phase, representative signal
   level/gradient geometry, and preregistered stack sizes.
2. Propagate the full covariance of the warped pyramid energy, or calibrate its
   conditional distribution empirically. Coverage must pass **per stratum and
   per frame**, not only after pooling.
3. Calibrate the selected-winner statistic, not an arbitrary fixed pair.
   Convert each decision to a null tail probability conditional on known
   nuisance variables such as band, warp, and stack size. Then expose one
   global probability threshold. Those nuisance corrections are frozen from
   calibration data; they are not per-capture tuning.
4. Require both directions: equal-focus frames must be retained at the stated
   rate, and planted focus offsets must be rejected with preregistered power.

### B. Test merge performance without legacy-width preselection

Render every preregistered global threshold on every development capture.
Require one unchanged global threshold to satisfy the existing detail
lower-bound and flat-power upper-bound on every applicable capture. Report the
entire `n_eff` profile, singleton census, and below-floor census as diagnostics,
but do not require them to imitate legacy gate-4.5.

This is **not a weaker bar**:

- it does not relax either Pareto threshold;
- it does not permit per-capture or per-band threshold selection;
- it does not widen the grid after outcomes;
- it adds per-stratum calibration and selected-winner controls that W1 lacks;
- it removes only an internal-state equality to a different algorithm, while
  directly testing the quality claims that equality prevented W1 from
  reaching.

An average-everything candidate remains exposed to the unchanged detail bar; a
winner-take-all candidate remains exposed to the unchanged flat-power bar. A
candidate passes only by delivering the claimed output Pareto improvement at
one global, independently calibrated decision probability.

Because this audit is post-outcome, that replacement gate must be
preregistered before use and must not select a threshold from the width
intervals reported here.

## Could not determine

1. Whether any global threshold passes the original Pareto bars. W1 rendered
   none, so the evidence does not exist.
2. Whether repairing only the standardisation would create a common
   legacy-width match. No corrected statistic was run, and this audit did not
   tune or widen the grid.
3. How much of the observed coarse-band width gap comes from normalisation
   error versus the comparator's different floor, exponent, weighting, and
   fallback semantics.
4. The exact per-pixel legacy fallback and candidate below-floor fractions;
   the frozen width artifacts retain means, not those censuses.
5. The effect size of inter-band covariance on a joint all-band error claim.
6. What happens outside the frozen grid. No extrapolation was made.
7. Whether a corrected gate would vindicate Phase 1. The present result removes
   a refutation; it does not supply a positive result.

## Bottom line

The program did **not** establish that the Phase-1 merge law lacks a usable
global threshold. It established that no threshold in the frozen grid makes
that law reproduce legacy gate-4.5's highly band-, ROI-, and capture-dependent
internal Kish widths to the frozen tolerance. Because that precondition
prevented every Pareto render, `NO_COMMON_K` cannot carry the design-level
refutation currently assigned to it.
