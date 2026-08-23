# M38 — the estimation merge on real frames, and a confounded metric

**Status:** MEASURED. **NOT INDEPENDENTLY VERIFIED** — measured by the orchestrator, who also
wrote the code under test. Rule 12 binds this document exactly as it binds any milestone.

**Artifacts:** `experiments/m38-detail-metric/src/01-gradient-conventions.py`,
`out/01-gradient-conventions.json`, `out/02-merge-roi-pair-A.txt`, `out/03-merge-roi-pair-B.txt`,
`out/04-gate-transfer.txt`. Code: `crates/strehl-cli/src/merge_cmd.rs`.

---

## 0. What this milestone was for

M37 built the estimation merge and proved things about it in unit tests. It had never seen a
photograph. This milestone wires it to real brackets and measures the two acceptance invariants
the project has been holding it to since M2: **flat-ROI noise ratio ≤ 1.0** and **detail not
collapsed**. Both, on the same frames, in the same run, through the same code path that produced
the numbers being compared against.

The headline is not the merge working. It is that **the second invariant was measuring the wrong
thing, in the direction that flatters whatever you already believe**, and that correcting it
reversed the verdict.

---

## 1. Invariant 1 — flat-ROI noise

`109MSDCF`, 22 frames, ISO 160, 2.9 s end to end for a six-gate sweep including two full decode
passes. Two ROI pairs, both chosen by M2 on structural grounds long before this code existed, so
neither was selected by this outcome.

| gate | mean `n_eff` | flat ROI `2272,1344` | flat ROI `2352,1408` |
|---|---|---|---|
| 0.00 | 1.000 | **1.074x** | 1.087x |
| 0.50 | 1.414 | 1.027x | 1.036x |
| 1.00 | 1.884 | **0.973x** | 0.979x |
| 2.00 | 2.891 | **0.890x** | 0.879x |
| 4.00 | 4.987 | 0.788x | 0.765x |
| 8.00 | 10.469 | 0.678x | 0.648x |

The naive argmax baseline is **1.253x** on the first of these ROIs (fact 19). The merge passes
from gate 1.0 upward and the two ROIs agree to within 0.6% at every gate.

### 1.1 The structural check that matters more than the result

**Gate 0 is pure regularised selection with no averaging at all, and it lands on 1.074x where
M2-verification independently measured 1.075x for the same operation** (fact 23). Different
language, different author, different harness, a year of intervening design — 0.1% apart.

That is worth more than the pass. It says the pass-one chain — decode, black subtraction, green
luma, Tenengrad against the injected noise model, 17x17 box regularisation, argmax — reproduces a
separately measured number end to end. Nothing in the merge is trusted because it looks right.

---

## 2. Invariant 2 — and the confound that inverted it

### 2.1 The first reading was a disaster, and it was an artifact

Measured as mean |∇| in fact 24's own convention, detail fell **45%** across the gate sweep on
both ROIs. That is fact 24's −58% collapse, arriving on schedule. Taken at face value it says the
merge buys its noise reduction by destroying detail, and the thesis is wrong.

It is an artifact. **Noise contributes gradient.** A merge that reduces σ reduces mean |∇| *with
zero blur*, so an uncorrected reading charges the merge for doing precisely the thing it exists to
do. The confound has the **same sign** as the effect the metric is used to detect, which is the
worst possible arrangement: the metric cannot distinguish success from failure.

The same confound runs backwards through fact 24 itself. Argmax "raises" gradient there — and
argmax also raises noise by 1.253x (fact 19). Part of that flattering gradient number is the
defect the project exists to remove, scored as sharpness.

### 2.2 The correction

The absolute form does not decompose. The squared form does:
`E[dx²] = E[dx_signal²] + E[dx_noise²]`. With forward differences and per-pixel σ from the
calibrated model, the noise contribution at pixel `i` is exactly
`2σ_i² + σ_{i+1}² + σ_{i+w}²`, so

```
corrected = sqrt( max(0, raw_rms² − model_rms²) )
```

The model term is not free-floating. On the single reference frame it returns **17.1412 DN**
against a hand calculation of `2σ = 2 × 12.12/√2 = 17.14` at that signal level, using
`g = ISO/436.8` and `RN = 4.20 e-`. The project's calibrated noise model is doing the work.

### 2.3 What the correction does

| ROI | uncorrected (fact 24's convention) | corrected |
|---|---|---|
| `1630,1044` | 12.65 → 6.90 (**−45%**) | 23.54 → 22.46 (**−4.6%**) |
| `64,800` | 19.53 → 10.81 (**−45%**) | 39.14 → 37.74 (**−3.6%**) |

**About 90% of the apparent detail loss was noise removal being scored as blur**, and the finding
replicates on two independent ROIs to within a percentage point.

Against pure selection at gate 0 rather than against a single frame, averaging at gate 2.0 costs
**0.2%** and **3.8%** of signal gradient while buying **11–12%** noise reduction.

### 2.4 Where this is bounded, honestly

`predicted_sigma` divides by `√n`. Fixed-pattern noise does not obey that, so merged noise is
**underestimated at large n**, the subtracted term is too small, and corrected retention at wide
gates is an **upper bound** rather than an estimate. The −4.6% and −3.6% figures are therefore
best cases at gate 8. They are not load-bearing: the design conclusion rests on gate 2.0, where
`n_eff` is 2.9 and the correction is small.

---

## 3. Fact 24's gradient convention, identified by measurement

M2's harness is not preserved in the repository. Rather than assume a definition, §1 computed
seven candidate conventions on the same ROIs with an **independent numpy implementation** sharing
no code with the Rust pipeline, and asked which reproduced the published 11.89 and 18.58.

| convention | ROI `1630,1044` | ROI `64,800` |
|---|---|---|
| `mean(hypot(dx,dy))` | 18.4576 | 29.7240 |
| `mean(\|dx\|)` | 12.1183 | 15.3247 |
| `mean(\|dy\|)` | 11.6631 | 21.8434 |
| **`mean(0.5(\|dx\|+\|dy\|))`** | **11.8907** | **18.5840** |
| `sqrt(mean(dx²+dy²))` | 25.3920 | 49.1005 |
| Sobel/8 | 10.0299 | 16.2319 |
| *M2 published* | *11.89* | *18.58* |

**`mean(0.5(|dx|+|dy|))`, to 0.01% and 0.02% on both ROIs.** Identified, not guessed.

### 3.1 The pre-registered guess was wrong, and the way it died is the point

The hypothesis going in was single-axis `|dx|`, from the exact ratio `π/2 = 1.5708` between an
isotropic gradient magnitude and one component of an isotropic Gaussian field — which the observed
ratios of **1.552** and **1.600** appeared to bracket.

It matched ROI `1630,1044` to 1.9% and missed ROI `64,800` by **17.5%**. The reason is visible in
the table: that ROI is **1.43x anisotropic** (`|dy|` 21.84 against `|dx|` 15.32), so the isotropy
the π/2 argument assumes does not hold and the ratio is not a constant at all.

Right family, wrong member, killed by the second ROI. **A single-ROI check would have confirmed
it.** This is the same shape as facts 73, 203 and 211 — a quantity reading confidently while the
thing it assumes is absent.

### 3.2 Two consequences

- **There is no constant conversion between the two harnesses.** 1.552 and 1.600 are
  ROI-dependent because real detail is anisotropic. Any comparison against fact 24 must be made in
  fact 24's convention, which the merge now reports as its own column.
- **The independent numpy implementation reproduces the new Rust metric at ratio 1.0000** on both
  ROIs. That is an independent-implementation check on code written tonight.

---

## 4. The gate does not transfer, and that changes the design

Question 90 asked for the gate threshold. `mean n_eff` is a whole-image statistic requiring no ROI
choice, so it can be measured on every stack in the corpus with nothing selected by outcome.

| stack | frames | ISO | gate 0.5 | gate 1.0 | gate 2.0 | gate 4.0 | `n_eff`/N at 2.0 |
|---|---|---|---|---|---|---|---|
| `119MSDCF` | 33 | 50 | 1.275 | 1.581 | **2.258** | 3.654 | 0.068 |
| `109MSDCF` | 22 | 160 | 1.414 | 1.884 | **2.891** | 4.987 | 0.131 |
| `113MSDCF` | 63 | 500 | 1.433 | 2.198 | **4.774** | 8.590 | 0.076 |
| `112MSDCF` | 79 | 500 | 1.554 | 2.572 | **6.226** | 12.065 | 0.079 |
| `coffee-bean` | 105 | 50 | 1.516 | 2.570 | **7.422** | 24.700 | 0.071 |

**At one fixed threshold, `n_eff` spans 2.26 to 7.42 — a 3.3x range.** A fixed gate is not a
calibration; it is a different estimator on every stack.

The mechanism is visible in the last column: `n_eff/N` clusters at **0.068–0.079** for four of the
five stacks. The acceptance set is roughly **a fixed fraction of the bracket, not a fixed count**,
which is what a through-focus peak of fixed optical width sampled at varying density should do —
and is consistent with fact 213's finding that `coffee-bean` is 2–4x denser than it needed to be.
`109MSDCF` at 0.131 is the exception and is not explained.

Solving each stack for `n_eff = 3` gives thresholds of roughly **2.9, 2.1, 1.3, 1.1, 1.1** — a
2.6x range.

### 4.1 The design conclusion

**The threshold must be solved per stack against a target `n_eff`, not fixed as a constant.** The
merge already reports `mean_n_eff()`, so the solve is a few evaluations of pass two — or, since
pass two folds many accumulators for the price of one decode, a single sweep that picks its own
operating point. This is §4.1's "profiles as data, not constants" arriving in a new place, and it
would have shipped wrong: gate 2.0 was the honest reading of `109MSDCF` and is a **2.6x error**
on `coffee-bean`.

### 4.2 A discrepancy to check, not a contradiction

`at_bracket_boundary` reports **7.60%** on `coffee-bean` and **2.02%** on `119MSDCF`. Fact 300
(M35) reports 7.38% boundary peaks for `119MSDCF`. The definitions differ — this one is "the
regularised winner index is 0 or N−1" over all pixels, M35's was a parabola-fit peak over a
reliable subset — so the denominators are not the same quantity and this is not yet a conflict.
But the numbers are close enough, and attached to the wrong stacks, that one of the two should be
re-derived before either is cited. Logged as question 95.

---

## 5. What this milestone did not do

- **No independent verification.** The author of `merge.rs` and `merge_cmd.rs` measured them.
- **No alignment.** Every number here is on unaligned frames, which fact 19 established is
  precisely what makes the flat-ROI ratio interpretable — drift pushes it *below* 1.0, so some of
  the reduction credited to the gate may be drift. The gate-0 control bounds this: pure selection
  sits at 1.074x with the same drift, so drift is not producing the sub-1.0 readings.
- **One stack for the invariants.** The gate sweep covers five; invariants 1 and 2 cover one.
- **No outlier rejection, no deconvolution, no occlusion handling.** The merge is the merge.
