# M70 — PRE-REGISTRATION B: through-focus **symmetry**

**Written and committed BEFORE the corpus symmetry measurement was run.**
Commission: the owner's follow-up turn, item 2, and `docs/research/M67-focus-correctness.md` §7.3.

This is a second pre-registration inside one milestone, after the pattern of M63.
`PREREGISTRATION.md` in this directory governs the primary question (Criteria A–D) and is
already discharged in `docs/research/M70-through-focus-spectrum.md`. Nothing here amends it.

---

## 0. Why this exists

M67 registered, before running, that its forward model's PSF is **symmetric and monotone in
`|F−k|` by construction**, and declared every accuracy number an upper bound in consequence.
Its §7.3 then **withdrew its own supporting claim** that real through-focus curves are
"measured asymmetric", and named three prerequisites for whoever measures it properly:

- **(a)** report **skew and kurtosis separately** — corpus fact 274 is *kurtosis*, not skew,
  and is flagged NOT INDEPENDENTLY VERIFIED;
- **(b)** M25 **question 33**'s depth-range confound is live, so **one stack is not enough**;
- **(c)** fact 471's FWHM agrees with the model on **two** stacks, so any real deviation must
  live in the **tails**, not the core.

The owner's instruction is explicit: *"do not treat M67's fact 19 as established; that is
precisely what I am asking you to check."*

I hold 12 stacks of real through-focus curves already measured (`out/tfs-*.npz`, 1,568 frames).
The symmetry question is pure post-processing of material already on disk. It is cheap, so it
is in scope.

---

## 1. The estimator, fixed in advance

Operating on the corrected (unclipped) through-focus response `S_k` of `src/s07_unclipped.py`,
per patch, per band:

**Half-widths.** `half_widths(S, frac)` returns the interpolated offsets, in frames, at which
the `[1,2,1]`-smoothed curve first falls to `frac × peak` searching **outward from the peak** on
each side. If a side reaches a stack end without falling to `frac`, that side is **censored**
and returned as such. **Censored sides are never imputed** — M41's detail metric died of
silent right-censoring.

**Asymmetry index.**

    A_f  =  (w_far − w_near) / (w_far + w_near)   ∈ [−1, +1]

evaluated at `f ∈ {0.50, 0.25, 0.10}`. `A50` is directly comparable with fact 471's FWHM;
`A25` and `A10` probe the tails, per M67's prerequisite (c).

**Sign convention, stated now because it is load-bearing:** *positive means the response decays
more slowly toward **higher frame index***. Frame index maps to physical near/far only through
each stack's sweep direction, which I do not reliably know. **This is declared in advance as a
limitation, not discovered afterwards.** Consequently the *magnitude* `|A|` is the load-bearing
quantity for M67's purpose (an asymmetric PSF family is asymmetric whichever side is which),
and the sign is reported as secondary.

**Moments.** `moments(S, window=10)` returns standardised skew `g1` and **excess** kurtosis `g2`
of `w_k = max(S_k, 0)` over a ±10-frame window about the peak, with a `trunc` flag when the
window hits a stack end. The clip is **required** here — a weight must be non-negative — unlike
in the primary question's *sum*, where the identical clip was the defect (see report §4.4). Its
consequences are bounded by control, not assumed away.

---

## 2. Controls, run and read BEFORE these criteria were written

`src/s14_asym_controls.py`, log `out/s14_asym_controls.log`, JSON `out/s14_asym_controls.json`.
The plant is built on a **real latent patch** (`D:\personal\macro\119MSDCF` centre, high-band
power 1716.1, mean 882.8 DN), not on synthetic texture — rule 3, and the exact failure mode M63
caught.

| control | what it plants | result |
| --- | --- | --- |
| **NULL-SYM** | symmetric ladder, δ ∈ {0.25, 0.5, 1.0} px/step, 216 draws | bias `A50` **+0.0001**, **sd 0.0039**; `A25` sd 0.0030; `A10` sd 0.0039 |
| **NULL-NOISE** | flat latent + calibrated noise, no curve, 144 draws | `A50` median −0.038, **sd 0.3055**; **34/144 censored** |
| **POWER-ASYM** | genuinely asymmetric, 5 rate pairs | sign correct 5/5; magnitude **0.965–0.977× of ideal** at \|A\|≤0.33 |
| **CONFOUND** | two depths, unequal weights, **symmetric PSF**, noiseless | \|A50\| up to **0.0726**, \|A10\| up to **0.1451**, \|g1\| up to **0.4457** |
| **REVERSAL** | frame order reversed | worst \|forward + reversed\| = **1.5e−14** (exact) |

Three consequences, all of which change the criteria I would otherwise have written:

1. **The null band is not the binding constraint.** 3×null_sd on `A50` is **0.0117**. A
   threshold set from the null alone would be far too permissive.
2. **The scene-geometry confound is the binding constraint.** A *symmetric* PSF over a
   two-depth scene produces `|A50|` up to **0.073** and `|A10|` up to **0.145** with no PSF
   asymmetry whatsoever. **My originally-intended 0.10 bar sat inside this envelope** and would
   have been unsound. It is raised below.
3. **`g2` is not a tail-weight statistic.** On a plant that is **symmetric by construction**,
   `g2` runs **−0.63 (δ=0.25) → +0.86 (δ=0.50) → +6.13 (δ=1.00)**, pooled sd **4.77**. It is
   measuring curve width relative to the moment window, i.e. **focus-step density**, not shape.
   Criterion F is rewritten accordingly.

**Measurable range, declared now:** at the extreme plant (ideal `A50` = −0.600) the estimator
returns only −0.106, rising to −0.217 at `A10`. The estimator **compresses large asymmetries**
because the fast side falls below half-peak inside one frame and the half-width hits the
sampling floor. So: **`|A|` is trustworthy to ≈0.33 and under-reads beyond it.** The bias runs
*against* declaring asymmetry, never toward it.

---

## 3. Pre-registered criteria

### Criterion E — is the real through-focus response symmetric in frame index?

Statistic: **stack-median of signed `A_f`** over textured patches × mid bands
(`b3_mid`, `b4_mid`, `b5_mid`), plus **within-stack sign-agreement fraction**.

| verdict | condition |
| --- | --- |
| **SYMMETRIC** | `|median A_f| < 0.05` on **≥9/12** stacks at **every** `f ∈ {0.50, 0.25, 0.10}` |
| **ASYMMETRIC (beyond confound)** | `|median A_f| ≥ 0.15` with consistent sign on **≥9/12** stacks at **any** `f` |
| **INDETERMINATE** | anything between — including the case where the reading lies inside the CONFOUND envelope and therefore cannot be attributed to the PSF |

0.05 sits above 3×null_sd (0.0117) and **below** the worst confound `A50` (0.073).
0.15 sits **above** the worst confound `A10` (0.145). The gap between them is honest: readings
in it are real but not attributable. **I commit now to reporting an INDETERMINATE as
INDETERMINATE.**

### Criterion F — skew and kurtosis, reported separately (M67 prerequisite (a))

`g1` and `g2` are reported separately and never combined.

- **`g1`:** testable. Null sd 0.290 on the symmetric plant; confound reaches 0.446.
  Threshold: `|median g1| ≥ 0.45` with consistent sign on ≥9/12 → **SKEWED**;
  `< 0.15` on ≥9/12 → **UNSKEWED**; else INDETERMINATE.
- **`g2`:** **pre-registered as NOT TESTABLE against fact 274 by this instrument.** The
  symmetric-by-construction plant spans −0.63…+6.13 purely as a function of focus-step density.
  I will report the corpus `g2` **and its correlation with focus-step density**, and will state
  that a positive `g2` is **not** evidence for fact 274. If the corpus `g2` tracks step density
  the way the null plant does, that is a finding about **fact 274**, not about the corpus.

### Criterion G — could any reading be scene geometry rather than the PSF? (M25 q33)

- **PSF-LIKE:** within-stack sign agreement **≥75%** AND the same sign on **≥9/12** stack medians.
- **SCENE-LIKE:** sign agreement **≤60%**, or the stack medians split.
- **Stated in advance: neither outcome proves the mechanism.** PSF-LIKE is consistent with a real
  asymmetric PSF *and* with a corpus of scenes that happen to share a geometry and a sweep
  direction. This criterion bounds, it does not identify.

---

## 4. VOID conditions

Any of these fires ⇒ the affected reading is void, reported as void, and **not reinterpreted**.

- **VOID 5** — null sd on the symmetric plant `> 0.03` ⇒ the SYMMETRIC clause of E is unusable.
  **Pre-checked: 0.0039. Does not fire.**
- **VOID 6** — the **reversal placebo on real corpus data** fails to flip every statistic's sign
  to within 0.02 ⇒ **all** asymmetry readings VOID. (On plants it is exact to 1.5e−14; it has
  not yet been run on real data.)
- **VOID 7** — POWER-ASYM not recovered with correct sign and ≥0.5× planted magnitude ⇒ the
  SYMMETRIC branch is unsupportable. **Pre-checked: 5/5 sign, 0.97× magnitude at |A|≤0.33.
  Does not fire.** (At |ideal| = 0.60 recovery is 0.18×; this is recorded as compression, and
  is why the ASYMMETRIC branch is one-sided.)
- **VOID 8** — CONFOUND `|A|` ≥ the corpus median `|A|` ⇒ the confound is not separable and
  **G is INDETERMINATE regardless of sign agreement**.
- **VOID 9** — the **frame-shuffle placebo** on real data (frames randomly permuted, destroying
  the through-focus curve) returns `|median A|` **greater than** the intact corpus median ⇒ the
  corpus reading is not distinguishable from the noise floor and E is VOID.
- **VOID 10** — more than **25%** of patch×band curves are censored on a side at a given `f`
  ⇒ `A_f` at that `f` is reported as unusable rather than as a number.

---

## 5. What this measurement cannot see, declared in advance

1. **Sweep direction.** Frame index → physical near/far is unknown per stack. Signs are
   reported in frame-index terms only.
2. **Scene geometry is not separable from PSF asymmetry** on found footage. The CONFOUND
   control bounds it; it does not remove it. This is M25 question 33, still open.
3. **Five-band spectral resolution.** Same limit as the primary question.
4. **No phase.** `|H|` only. An asymmetric PSF with symmetric modulus is invisible here —
   and defocus PSFs on opposite sides of focus differ in *phase* (sign of the wavefront error)
   before they differ in modulus. **This measurement is blind to precisely the most likely form
   of through-focus asymmetry**, and that blindness is declared before the run, not after.
5. **A per-patch reading is meaningless** (NULL-NOISE sd 0.306). Only stack medians over
   ≥24 patches × 3 bands are interpreted.
6. **`g2` cannot test fact 274** (see Criterion F).

---

## 6. The incumbent re-pricing (owner's item 3) — declared scope, not a criterion

Separately and without a pass/fail criterion, I will re-index the primary question's already-
measured price list by **admitted-set size**, so the matched filter's value can be read against
**the gated average as it actually behaves** rather than against a 3-frame average. M67's
`n_eff = 6.84` at `K = 25` is a **simulator** figure and **will not be imported as a corpus
figure**; it is used only to point at a row of a table measured on the corpus. This is
arithmetic on existing measurements and carries no new claim.
