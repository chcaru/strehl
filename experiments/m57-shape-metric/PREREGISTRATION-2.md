# M57 — second pre-registration: K6 / K7, after PR13 killed K1

**This file is committed before `s6_debias.py` runs, and before either K6 or K7
has been evaluated on any data.** It is a *second* pre-registration because the
candidates in it did not exist when `PREREGISTRATION.md` was written. They were
designed in response to a measured failure, and that makes them **post-hoc**.
Post-hoc is not a synonym for invalid, but it is a synonym for *weaker*, and
this file exists so the weakness is on the record rather than in a footnote.

---

## 1. What killed K1

**MEASURED (S5, `out/s5_real_nulls.log`).** N1 — add independent Gaussian noise
to each of the two real half-merges. The common transfer is untouched, so the
true equivalent-blur difference is **exactly 0 px**, on any scene, at any level.
K1 (`dsig`) read, at 3× the merged temporal sigma:

| cell | dsig px | se | vs the 0.10 px planted signal |
| --- | --- | --- | --- |
| 112MSDCF/flat | −0.11639 | 3.0e−02 | 116% |
| 112MSDCF/detail | +0.05964 | 1.5e−02 | 60% |
| 113MSDCF/flat | −0.06440 | 4.6e−02 | 64% |
| 113MSDCF/centre | +0.05437 | 1.6e−02 | 54% |
| foam/flat | +0.03241 | 2.5e−02 | 32% |
| foam/centre | +0.01585 | 1.7e−02 | 16% |
| 109MSDCF/flat | n/a (ring went non-positive) | — | — |
| 109MSDCF/centre | −0.29126 | 4.4e−02 | **291%** |

The pre-registered threshold was 0.02 px. **PR13 FAILED.**

## 2. Why — DERIVED, and the reason a fix is not a fudge

`C(f)` is a cross-power of two images whose noise is independent, so noise has
zero **mean** contribution: that part of K1's design is correct and S1 measured
it holding on a plant. But noise has non-zero **variance**, and K1 takes a
**logarithm** of the ring mean. To second order

&nbsp;&nbsp;&nbsp;&nbsp;`E[log Ĉ] = log E[C] − Var(Ĉ) / (2 E[C]²) + O(Var²)`

`Var(Ĉ)` is dominated by noise×signal and noise×noise cross terms, which are
roughly flat in `f`, while `E[C]` **falls** towards `f_hi`. So the bias term
`Var/(2C²)` **grows** towards high frequency — which is precisely the shape of a
blur. K1 therefore reports a blur that is not there, in an amount set by the
per-ring SNR. That predicts the worst cell should be the one with the fewest
frames per half and the least common power at `f_hi`; 109MSDCF has 11 frames per
half against 31 for the others, and it is the worst cell. **That agreement was
not used to build the fix and is offered as a check on the mechanism, not as
proof of it.**

## 3. The two candidates

Both are forced by the derivation above. **Neither introduces a tunable
constant**, and that is the only thing that distinguishes them from tuning.

* **K6 `dsig_lin`** — fit `C₂(f) = C₁(f)·exp(−4π²b f²)` in the **linear
  domain**, minimising `Σ [C₂ − C₁e^{−xb}]² / (V₂ + e^{−2xb}V₁)`. There is no
  logarithm, so there is no Jensen term. The weight is the total residual
  variance implied by the model, not a choice. `V` is the leave-one-angular-
  sector-out jackknife variance of the ring mean.
* **K7 `dsig_db`** — K1's log fit with `+V/(2C²)` added back to each log. One
  term, taken directly from the expansion above.

## 4. Kill conditions — written before either was run

* **PR14 — THE NOISE NULL, REPEATED.** On all eight real cells, adding
  independent noise at 1×, 2× and 3× the merged temporal sigma must give
  `|value| ≤ 0.02 px`. Truth is exactly 0. **KILL if any cell exceeds it.**
* **PR15 — THE SIGNAL MUST SURVIVE THE FIX.** The planted 0.10 px blur must
  still be recovered to within ±10% on all eight cells. **KILL otherwise** — a
  statistic that is null-clean because it reads zero for everything is worthless.
* **PR16 — GAIN INVARIANCE MUST SURVIVE.** One-sided λ = 1.30 must move the
  reading by less than 1e−4 px. **KILL otherwise.** (K1 achieves 1e−8. K6 is
  *not* obviously degree 0: the weights `V₁, V₂` scale as λ² and λ⁴, so the
  invariance has to be measured, not assumed. **This is the property I most
  expect K6 to lose**, and it would be a real cost of leaving the log domain.)
* **PR17 — SPLIT LEVERAGE MUST SURVIVE.** With the split common to both
  configurations, spread across measurable split rules < 5% of the planted
  signal. **KILL otherwise.**
* **PR18 — HELD-OUT SEPARATION.** K6/K7 are designed against a failure observed
  on all eight cells, so *no cell in this corpus is held out for them*.
  This is stated as a limitation, not repaired: a pass on PR14–PR17 is
  **provisional** and requires confirmation on a stack not in
  {112MSDCF, 113MSDCF, foam, 109MSDCF} before it can be believed. I commit to
  reporting it as provisional even if every number is clean.

## 5. What I expect

1. K7 removes most but not all of the bias, because the expansion is truncated
   at second order and the residual is `O(Var²)`.
2. K6 removes more of it than K7 and **loses exact gain invariance** (PR16).
3. If K6 passes PR14 and fails PR16, neither is shippable and the correct
   report is that the family fails, with the mechanism named.
4. PR14 at 3× noise on 109MSDCF/centre is the specific cell I expect to decide
   this. It is the hardest and it is not being dropped.
