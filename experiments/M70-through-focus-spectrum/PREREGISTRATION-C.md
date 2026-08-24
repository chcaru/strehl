# M70 PRE-REGISTRATION C — where does the through-focus shape depart from a Gaussian?

**Written after running `src/s20_shape_controls.py` and reading its output, and
BEFORE running `src/s21_shape_corpus.py` on any real stack.** Same discipline as
`PREREGISTRATION.md` and `PREREGISTRATION-B.md`: the controls set the bars, the
corpus is then read once against bars that are already fixed.

Commit order is the evidence. This file is committed before `s21` produces a
number.

---

## 0. Why there is a third pre-registration

The owner's third turn withdrew the claim that sent me after asymmetry ("real
through-focus curves are measured asymmetric") and rescoped the question to:

> **are real through-focus curves symmetric, and where does their shape depart
> from a Gaussian?**

§16 answered the first half (symmetric to ±0.077; M67's fact 19 NOT SUPPORTED).
This pre-registration covers the second half, which §16 did **not** answer,
because §16.4 established that the statistic conventionally used for it —
excess kurtosis `g2` — **cannot** answer it on this corpus. On a plant that is
symmetric *by construction*, `g2` ran −0.63 … +6.13 purely as focus-step density
varied. It measures curve width relative to the moment window, not shape. It was
pre-registered NOT TESTABLE and it stays that way.

**A defect of my own, found while preparing this and corrected here.** §16.7 as
committed claimed fact 471's "FWHM 10/9 and 17/17" corroborated my symmetry
result, converting them to |A| = 0.053 and 0.000. **That is a misreading.** Read
at source (`M67-focus-correctness.md:520`), 10/9 is **FWHM measured versus FWHM
modelled** — a model-agreement check — not near-side versus far-side half-widths.
It is not an asymmetry measurement at all, and M67 says so in the same row:
"FWHM is a symmetric summary … Neither confirms nor refutes skew." I took the
number from SYNTHESIS fact 1006's compressed rendering and did not open the
source. That is precisely the failure the owner has now been caught by three
times this week, committed by me inside the section that discusses it. §19.1
retracts it in the report. **The §16 conclusion does not depend on it** — it was
offered as corroboration, and corroboration is what is withdrawn.

Fact 471 **does** carry something I can use correctly, which is why the
misreading was costly: `s = 0.6017 px/frame` on `119MSDCF` and `1.1856` on
`109MSDCF` are **measured real blur-growth rates**. They are used below to prove
the plant covers the real regime rather than assuming it.

---

## 1. The statistic, and why this one

**Half-width ratios at two fractions of peak.** For a curve `S(k)` with peak at
`k*`, let `w(f)` be the half-width where the curve falls to fraction `f` of peak,
averaged over the near and far sides. Define

    R10_50 = w(0.10) / w(0.50)          (primary)
    R25_50 = w(0.25) / w(0.50)          (secondary)

For a Gaussian `exp(−x²/2σ²)`, `w(f) = σ·√(−2 ln f)` and **σ cancels exactly**:

| ratio | Gaussian value |
| --- | --- |
| `R25_50` | `√(ln4/ln2)` = **1.414214** |
| `R10_50` | `√(ln10/ln2)` = **1.822616** |
| `R10_25` | `√(ln10/ln4)` = **1.288784** |

No free parameter. Three properties make this the right instrument here, and
each is **measured in `s20`, not assumed**:

1. **It is scale-free.** `s20` Tier 1b: over a **10.5× range of curve width**
   (`w50` 2.38 → 24.73 frames) the same Gaussian returns `R10_50` spanning
   **1.0121×**, sd **0.0090**. `g2` over a 4× density range spanned −0.63…+6.13,
   pooled sd **4.77**. **The confound that killed `g2` cannot reach this
   statistic**, and that is a measurement, not an argument.
2. **It is a TAIL statistic, which is M67's instruction (c).** It is read at
   0.10 of peak. **No parabola and no Gaussian is fitted near the peak anywhere
   in M70** — a near-peak fit excludes by construction the region where fact 471
   implies any deviation lives.
3. **It cannot manufacture a reading from noise.** `s20` Tier 3 (NULL-NOISE,
   flat latent, calibrated noise, no curve): **144/144 draws UNDEFINED**. Unlike
   `A₅₀`, which returned a spurious ±0.077 on pure noise, this statistic
   *refuses to report* where there is no curve. The cost is censoring, which is
   returned and never imputed.

**Declared limitation, in advance:** `R10_50` is blind to asymmetry by
construction — it averages the near and far half-widths. That is deliberate;
asymmetry is §16's question and was answered there. These two statistics are
therefore **independent by design**, which is M67's instruction (a): kurtosis and
skew are reported separately and cannot be confused.

---

## 2. The comparators, both measured in `s20`

| comparator | `R10_50` | source |
| --- | --- | --- |
| **Gaussian, analytic** | **1.8226** | closed form; estimator reproduces it to **0.034%** |
| **Real-texture defocus ladder** | **1.729 – 1.837**, median **1.766** | `s20` Tier 2, 36 curves per δ, δ ∈ {0.25, 0.50, **0.6017**, 1.0, **1.1856**, 2.0} px/step |
| sech² (mildly heavy) | 2.066 (1.134× Gaussian) | analytic |
| Lorentzian (heavy) | 3.000 (1.646×) | analytic |
| triangle | 1.800 (0.988×) | analytic |
| boxcar (no tails) | 1.024 (0.562×) | analytic |

Two things follow and both are pre-registered as expectations, not results:

- **The physical comparator is not the analytic one.** A genuine defocus curve
  on real texture reads **≈1.766, i.e. 0.97× Gaussian** — very slightly
  sub-Gaussian. The corpus must be compared against **both**.
- **The plant covers the real regime.** The δ sweep contains fact 471's two
  measured rates exactly, and brackets them 4.8× on either side. `R10_50` moves
  **1.062×** across the whole 8× sweep — the physical plant confirms
  scale-freeness on real texture, not just on analytic curves.

**Known estimator bias, declared in advance.** `s20` Tier 1b shows narrow curves
read **high**: `w50` = 2.38 → +1.2%, `w50` = 5.89 → +0.25%, `w50` ≥ 9.4 →
≤0.04%. Discretisation. **This bias pushes toward "heavier than Gaussian"**, so
a sub-Gaussian finding is conservative and a super-Gaussian finding must be
checked against per-stack `w50`. Recorded now so it cannot be discovered later.

---

## 3. The bar

**±0.11 absolute on `R10_50`.** Derivation, fixed before the run: the physical
plant's full span across an 8× range of focus-step density is 1.729 → 1.837 =
**0.108 absolute**. The bar is that span, rounded to 0.11 — i.e. **an effect must
exceed everything step density alone can do to a curve that is Gaussian-ish by
construction.** It is not tuned to any corpus reading.

**Headline population: the seven POWERED stacks** (K ≥ 100), per §16.5's
per-stack shuffle null table. All twelve are reported; only the powered seven
carry a criterion. This is fixed in advance and is the same population §16 used.

---

## 4. Pre-registered criteria

Evaluated on the median of per-patch `R10_50` within a stack, then across the
seven powered stacks.

**Criterion H — GAUSSIAN-TO-RESOLUTION.**
Powered-stack median `R10_50` within **±0.11** of **1.8226**, **and** at least
**6 of 7** powered stacks individually within that band.
⇒ *The through-focus tail shape is Gaussian to the resolution of this
instrument. Fact 274's heavier-shoulders claim is NOT reproduced by an
independent route.*

**Criterion I — HEAVIER THAN GAUSSIAN (fact 274's direction).**
Powered-stack median `R10_50` ≥ **1.9326** (= 1.8226 + 0.11), **and** at least
**6 of 7** powered stacks individually ≥ 1.9326.
⇒ *Fact 274 is corroborated by an independent statistic on an independent
population, and the defocus PSF has heavier tails than Gaussian — which a
matched filter would have to model.*

**Criterion J — LIGHTER THAN GAUSSIAN.**
Powered-stack median ≤ **1.7126**, **and** ≥ 6/7 individually ≤ 1.7126.
⇒ *Sub-Gaussian tails; defocus energy is more concentrated than a Gaussian
family assumes.*

**If none of H, I, J is met: INDETERMINATE, reported as such.** §16's Criterion E
missed its 9/12 bar by a single stack and was reported failed rather than
reinterpreted. Same standard applies here and is expected to be applied.

**Fact 274 predicts a SIGN only, not a value.** Its numbers (fitted Gaussian σ =
1.68 / 2.04 / 2.45 from the ×2 / ×4 / ×6 decimation arms) are widths fitted on
*different decimations*, not at different fractions of one curve. Converting them
to a predicted `R10_50` needs an assumption I cannot check on this corpus, so
**no predicted value is registered** — only the direction: heavier shoulders ⇒
`R10_50` above Gaussian. Registered now so that no value can be back-fitted.

---

## 5. VOID conditions

**VOID 11 — censoring.** If the undefined-`R10_50` rate exceeds **50%** of
patches on a majority of powered stacks, the reading is not trustworthy and the
result is INDETERMINATE regardless of which criterion the surviving patches meet.
Per-stack undefined rates are reported for all twelve either way.

**VOID 12 — the statistic is not reading curve shape.** Per-stack shuffle null
(frame order permuted within patch, 100 reps, the `s16` construction). If the
shuffle null median lands within **0.11** of the intact reading on a majority of
powered stacks, `R10_50` is not responding to the through-focus curve and the
result is VOID.

**VOID 13 — estimator bug.** `R10_50` is symmetric in near/far by construction,
so reversing frame order must return the **identical** value. Any deviation
beyond 1e-12 is a bug and voids the run. (§16's VOID 6 exercised this and
returned 0.000000.)

**VOID 14 — σ dependence.** `FOCUS_NOISE_SD` is under active investigation by
M69 and the noise floor enters through the subtraction. If the powered-stack
median `R10_50` moves by more than **0.11** across σ ∈ {0.91, 1.00, 1.09, 1.25}×,
the reading is a function of an unsettled constant and is reported as such.

---

## 6. The named pairing, and what I expect to have to report

M67's instruction (b) names **`109MSDCF` (blur growth 1.1856 px/frame) against
`coffee-bean` (fit at the 12.0 px/frame grid edge)** as the minimum pairing to
separate M25's question 33 — defocus non-linearity versus subject depth range.

**I already know from §16.5 that `109MSDCF` is one of five UNPOWERED stacks on
the asymmetry statistic**: K = 22, shuffle null sd **0.0766**, z = **0.1**. If it
is likewise unpowered on `R10_50`, **the named pairing cannot be run on this
instrument, and I will report that rather than produce a reading from it.**
Registered in advance so that a null on `109MSDCF` cannot later be presented as
a finding, and so that the alternative — that `R10_50` *is* powered where `A₅₀`
was not — is equally reportable. Power is determined by the per-stack shuffle
null, which is computed for all twelve stacks whatever the outcome.

**`coffee-bean` is not anchored on alone**, per instruction (b). It is one of
seven powered stacks and carries one vote.

---

## 7. What this measurement cannot see, stated before it is made

1. **Modulus only.** Every M70 measurement is `|H|`. A defocus PSF departs from
   Gaussian in **phase** first, and phase is invisible here. Whatever is found,
   it is a statement about the through-focus power envelope, not the PSF.
2. **Five-band resolution** in frequency; `R10_50` is read per band and pooled
   over the three mid bands.
3. **It is blind to asymmetry** by construction (§1). That is §16's question.
4. **It cannot separate scene from optics.** A patch spanning two depths has a
   two-lobed curve whose tails are scene geometry. §16's CONFOUND control showed
   this reaches |A| = 0.073–0.145 on the asymmetry statistic; its effect on
   `R10_50` is measured in `s21` as a control, not assumed away.
5. **The corpus is 75.3% f/5.6 by frame count** (§2's scoping discovery), so
   this is primarily an f/5.6 result, whatever fact 27 measured at f/11.
6. **`coffee-bean`'s 12.0 px/frame is a saturated grid edge**, not a measured
   rate. It is used as a label, never as a number.

---

*Committed before `s21_shape_corpus.py` was run against any real stack.*
