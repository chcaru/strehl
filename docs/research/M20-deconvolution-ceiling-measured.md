# M20 — The deconvolution ceiling: is multi-frame Wiener the right *core* merge?

**Author:** orchestrator. **Date:** 2026-08.
**Status:** MEASURED. **NOT YET INDEPENDENTLY VERIFIED** — see §9.

> Project rule 12 says the author never verifies their own work. This document was
> produced by the orchestrator and therefore carries the weakest provenance in the
> corpus until a verifier has reproduced it. Treat every number below as pending.

---

## 1. The question

An external review (see [`../proposals/2026-08-external-review.md`](../proposals/2026-08-external-review.md))
proposed inverting the project's plan. Today's plan, from `B-algorithms-sota.md` §7.5, is that
deconvolution is *an opt-in PostMerge plugin, never the default*. The review argued the opposite:

> Make the merge itself a multi-frame Wiener deconvolution across the focus axis. […] At this
> rig's magnification, selection cannot produce a sharp image — only reconstruction can. […]
> The project's two crown jewels — the noise model and the measured PSF — are precisely the two
> things that make aggressive deconvolution safe, and the plan never connects them.

The proposed estimator, per frequency:

```
L̂(f) = Σ_k H_k*(f)·Y_k(f) / ( Σ_k |H_k(f)|² + σ²/S(f) )
```

with a claimed SNR gain of "roughly `√(Σ|H|²)`" in the mid-band where the current design counts
off-peak frames as zero.

This is a large architectural decision. It was ARGUED, not measured. This milestone measures it.

---

## 2. Verdict

**The review's mechanism is right, its scope is wrong, and the project's existing plan survives.**

| Claim under test | Verdict |
| --- | --- |
| The estimator formula is the MMSE one | **CONFIRMED** (§4.1) |
| Gain is `√(Σ\|H\|²)` | **CORRECTED** — it is `√(Σ\|H\|²)/max\|H\|` (§4.2) |
| "Only reconstruction can produce a sharp image at this magnification" | **REFUTED at Nyquist** — nothing can (§4.3) |
| Deconvolution should be the core merge | **REFUTED on this rig's data** — it wins on 15.1% of pixels (§7) |
| The merge's prize on detail "isn't noise, it's contrast no single frame contains" | **REFUTED** — the measured benefit is *entirely* noise; detail fidelity gains ≈0 (§6) |
| The `Σ\|H\|²` fallback guard is one of three guards | **PROMOTED** — it is load-bearing; without it the merge is *worse than argmax* (§5) |

**Recommendation: keep deconvolution as an opt-in post-merge stage (plan unchanged).** When
enabled it must be (a) guarded, (b) gated on *local* SNR, and (c) driven by a data-estimated
prior, never a parametric one. The natural gate is the project's own per-pixel confidence map —
which makes this a *use* for confidence rather than a replacement for the merge.

**Separately, and independently of all of the above: §4.4 is the largest actionable finding in
this milestone and it does not depend on deconvolution at all.**

---

## 3. Method and its gates

A 1-D forward model of this rig: latent → per-frame OTF (geometric defocus disc ∘ diffraction at
the bellows-corrected `N_eff`) → CFA-scale sampling → Gaussian noise. Merges compared: argmax
selection on the shipped focus-measure shape (mean |∇| under a 27-wide box), plain mean, unguarded
Wiener, guarded Wiener.

**Gate — the optics model must reproduce the project's own measured facts before it is trusted.**

| Quantity | Model | Corpus | Source |
| --- | --- | --- | --- |
| Cutoff at `N_eff` 33.7 | 0.2762 cyc/px | 0.2762 cyc/px | fact 27 (MEASURED) |
| Extinction `N_eff` at `f_c` = Nyquist | 18.618 | 18.6 | fact 12 |
| MTF@Nyquist, m=2.0, f/5.6 | 0.0361 | 0.036 | fact 12 |
| MTF@Nyquist, m=2.0, f/8 | 0.0000 | 0.000 | fact 12 |
| MTF@Nyquist, m=2.0, f/11 | 0.0000 | 0.000 | fact 12 |
| Critical sampling, marked | f/6.206 | f/6.21 | fact 28 |

All six reproduce to 3–4 digits. **The model is gated.**

**Unplanned corroboration (strengthens the gate).** The simulation was not tuned to fact 24, yet
the plain mean loses **49–51%** of its gradient on this plant, against fact 24's measured
**−58% / −53%** on real detail ROIs. Same sign, same magnitude, from a model built for a different
purpose.

---

## 4. Results — the estimator itself

### 4.1 The formula is correct (CONFIRMED)

Three independent routes to the optimal weights, on complex circular Monte Carlo data, `N` = 3×10⁵:

| trial | proposed closed form | empirical normal equations | Nelder-Mead black box | A/B | A/C |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.228142 | 0.228140 | 0.228140 | 1.0000061 | 1.0000061 |
| 1 | 0.332528 | 0.332526 | 0.332526 | 1.0000071 | 1.0000070 |
| 2 | 0.271281 | 0.271279 | 0.271279 | 1.0000043 | 1.0000043 |

Routes B and C assume nothing about the model — B solves the empirical `R_yy w = r_yL`, C minimises
measured MSE directly over `2K` real parameters. They agree with the proposed estimator to six
decimals. **The review's algebra is right.**

*(First attempt at this control was broken — my reference solver returned MSE 25.7/721/902, worse
than doing nothing, from a mishandled conjugate-transpose. A control that fails is not a control
that passes. Rewritten before use.)*

**Positive control.** Deliberately wrong estimators must lose, and do: inverse-filtered single-best-frame
selection is **2.655×** worse in MSE, gain-matched plain mean **1.124×** worse.

### 4.2 The gain shorthand is wrong (CORRECTED)

Measured amplitude gain of the matched filter over selection: **1.6294**.
`√(Σ|H|²)/max|H|` predicts **1.6140** (0.9% — residual is that the "selection" baseline was
inverse-filtered rather than single-frame Wiener, which is slightly unfair to selection).
`√(Σ|H|²)` alone predicts 1.6140 × 0.9 = **1.4526** — wrong.

**The gain over selection is `√(Σ_k|H_k|²) / max_k|H_k|`, not `√(Σ|H|²)`.** The review's shorthand
is only correct where the best frame is perfect at that frequency, which is nowhere on this rig.

### 4.3 There is a hard ceiling, and this rig is against it (MEASURED)

If `H_k(f) = 0` for every `k` then `Σ|H_k|² = 0` and `L̂(f) = 0/(0 + σ²/S) = 0` **exactly**. No
estimator, linear or otherwise, recovers a frequency that every observation multiplied by zero.

Fact 12: MTF@Nyquist is **0.000** at marked f/8 and f/11 at m=2.0. Therefore **deconvolution
cannot restore Nyquist detail at this rig's habitual working apertures.** It restores the
sub-cutoff band only. The review's "only reconstruction can produce a sharp image" is true of the
sub-cutoff band and false at Nyquist, where the correct answer is *change the aperture*.

### 4.4 THE APERTURE RESULT — largest actionable finding here

Blur-per-step in pixels is invariant across aperture (step in µm ∝ DOF ∝ `N_eff`; CoC growth
∝ 1/`N_eff`), so apertures can be compared at matched focus-axis sampling. Subject depth fixed,
frame count scales as 1/`N_eff`. Detail scale 0.25 cyc/px — the 4-px scale fact 28 uses.

**Budget: fixed total capture time**

| marked | `N_eff` | frames | σ/frame | best-frame MTF@0.25 c/px | SNR selection | SNR matched filter |
| --- | --- | --- | --- | --- | --- | --- |
| f/4 | 12.0 | 113 | 0.603 | 0.5977 | 0.9911 | 2.0626 |
| f/5.6 | 16.8 | 81 | 0.714 | 0.4467 | 0.6261 | 1.3028 |
| f/8 | 24.0 | 56 | 0.853 | 0.2416 | 0.2833 | 0.5895 |
| **f/11** | **33.0** | **41** | **1.000** | **0.0463** | **0.0463** | **0.0963** |
| f/16 | 48.0 | 28 | 1.206 | 0.0000 | 0.0000 | 0.0000 |

**Budget: fixed total light** (harsher; isolates optics from "more photons")

| marked | best-frame MTF@0.25 c/px | SNR selection | SNR matched filter |
| --- | --- | --- | --- |
| f/4 | 0.5977 | 0.3600 | 0.7492 |
| f/5.6 | 0.4467 | 0.3178 | 0.6613 |
| f/8 | 0.2416 | 0.2068 | 0.4301 |
| **f/11** | **0.0463** | **0.0463** | **0.0963** |
| f/16 | 0.0000 | 0.0000 | 0.0000 |

Moving from marked f/11 to marked f/5.6 multiplies best-frame contrast at 4-px detail by
**9.6×**, and matched-filter SNR by **13.5×** (fixed time) or **6.9×** (fixed light), at the cost
of 2× the frames. **This is optics, not software.** It dwarfs every merge-side gain measured
anywhere in this corpus, and it requires no code.

---

## 5. The guard is load-bearing, not optional (MEASURED)

Piecewise-constant depth (5 slabs), oracle depth, oracle prior — an **upper bound** on what any
implementation could do. 4 seeds. RMSE against the latent; lower is better.

| σ | selection | plain mean | Wiener (unguarded) | Wiener (guarded) | winner |
| --- | --- | --- | --- | --- | --- |
| 0.002 | 0.0534 | 0.0840 | 0.0403 | 0.0403 | guarded |
| 0.010 | 0.0543 | 0.0840 | **0.0574** | 0.0469 | guarded |
| 0.020 | 0.0570 | 0.0841 | **0.0711** | 0.0526 | guarded |
| 0.030 | 0.0628 | 0.0843 | **0.0825** | 0.0597 | guarded |
| 0.050 | 0.0826 | 0.0848 | **0.1003** | 0.0805 | guarded |

**Bold cells are where the unguarded Wiener is WORSE than plain argmax selection** — by up to
31%, with oracle depth and oracle prior. The review listed the `Σ|H|²` fallback as one of three
guards. It is not one of three; **it is the thing that makes the estimator usable at all.**

Guard used: blend toward the selected frame with weight `Σ|H|²/(Σ|H|² + τ·σ²/S)`.

**Not a tuning artifact.** τ swept over 24×: guarded/selection = 0.856–0.901 at σ=0.01 (wins at
every τ), and 0.938–0.978 at σ=0.05 for τ ≥ 2. It saturates above τ≈3 and there is a floor at
τ≈1 below which it loses. Broad, flat, not fitted.

**Depth model does not drive this.** Continuous ramp (every pixel a depth boundary — maximally
hostile to a shift-invariant Wiener), 5 slabs, and a single plane give results within 3% of each
other. My initial worry that the ramp was unfairly penalising the Wiener was **wrong**; checked
and discarded.

---

## 6. The prize is noise, not detail — the review's central claim is refuted (MEASURED)

Two detail metrics, because one of them lies.

| σ | mean\|∇\| sel | mean\|∇\| Wiener | ∇-correlation w/ truth, sel | ∇-correlation, Wiener |
| --- | --- | --- | --- | --- |
| 0.002 | 0.0285 | 0.0384 | 0.8750 | 0.8504 |
| 0.010 | 0.0296 | 0.0367 | 0.8595 | 0.7538 |
| 0.020 | 0.0317 | 0.0346 | 0.8072 | 0.7138 |
| 0.030 | 0.0350 | 0.0327 | 0.7340 | 0.6903 |
| 0.050 | 0.0455 | 0.0293 | 0.5592 | 0.6629 |

Ground-truth latent mean|∇| = 0.0392.

Read σ=0.010. The Wiener merge has **24% more gradient magnitude** than selection (0.0367 vs
0.0296; 94% of truth vs 76%) while having **12% less gradient correlation with the truth**
(0.7538 vs 0.8595). **The extra magnitude is ringing and amplified noise sitting where no edge
exists.** A mean-gradient acceptance test scores that as a win.

Worse, at σ=0.050 plain argmax selection reads mean|∇| = **0.0455, above ground truth's 0.0392**.
Pure noise inflates the metric past the true value.

**Consequence, already dispatched to M18 mid-build (it was writing an acceptance test on this
metric):** mean|∇| is valid only as a **one-sided** test against collapse. Fact 24's guard stands;
a gradient *increase* is a flag to investigate, never a pass.

**And the headline.** Across every implementable configuration in §7, the guarded merge's
∇-correlation gain over selection is within **±1.5%** — statistically nothing. Its entire measured
benefit is RMSE, i.e. **noise**. The review's "the prize there isn't noise, it's contrast that no
single frame contains" is **the opposite of what is measured.**

---

## 7. With an implementable prior, on real data, it wins on 15% of pixels

`S(f)` is not knowable a priori. §5's numbers used an oracle. Four priors, τ=3, slabs, 4 seeds;
`gua/sel < 1.0` means the deconvolution merge beats plain selection:

| σ | oracle | `est-sel` (from selected frame, noise-subtracted) | `est-mf` (from matched-filter output) | power-law fit |
| --- | --- | --- | --- | --- |
| 0.010 | 0.865 | **0.859** | 0.871 | 1.069 |
| 0.020 | 0.925 | **0.936** | 0.961 | 1.043 |
| 0.030 | 0.954 | **0.995** | 1.027 | 1.038 |
| 0.050 | 0.978 | **1.042** | 1.053 | 1.042 |

Data-driven estimation works and tracks the oracle to ~1% at low noise; the **parametric power-law
prior fails everywhere** and must not be shipped. The implementable crossover is **σ ≈ 0.03**.

**Where does this rig actually sit?** Measured on all 22 frames of `109MSDCF`, CFA green plane
(2344×3514), local window 9, signal-dependent noise from the project's own model
(`σ²(S) = g·S + (RN·g)²`, `g = ISO/436.8`, ISO 160 from EXIF → per-pixel σ 5.2–29.8 DN). For each
pixel, its **best** frame in the stack:

| percentile | σ_local / signal_local |
| --- | --- |
| p5 | 0.0890 |
| p10 | 0.1795 |
| p25 | 0.7073 |
| **p50** | **1.1279** |
| p75 | 1.3330 |
| p90 | 1.5041 |

**For the median pixel, local noise exceeds local signal structure even in that pixel's own best
frame.** Mapping §7's crossover into these units gives 0.3440:

- **15.1%** of pixels are where the implementable merge wins.
- **21.2%** even under the oracle-prior upper bound.
- The median pixel is **3.3× past** the crossover.

**Robustness of the weakest link.** The 0.3440 mapping crosses a 1-D simulation window to a 2-D
CFA window and is the softest number here. Swept:

| crossover error | % pixels where deconvolution wins |
| --- | --- |
| 0.5× | 9.7% |
| **1.0×** | **15.1%** |
| 2.0× | 24.4% |
| 3.0× | 40.5% |
| 4.0× | 79.6% |

**The verdict survives a 2× calibration error and flips at 3.3×.** Stated as a bound, not a point.

---

## 8. Consequences for the plan

1. **`B-algorithms-sota.md` §7.5 stands unchanged.** Deconvolution is opt-in post-merge. The
   proposed inversion is refuted on this rig's data.
2. **When enabled it must be guarded** (§5) — unguarded it is worse than the selector it replaces.
3. **It must be gated on *local* SNR, not enabled globally.** 15% of pixels want it and 85% do not,
   and the project already plans the per-pixel object that knows which is which. This is a *use*
   for the confidence map, and a good one.
4. **The prior must be estimated from data.** Power-law parametric priors lose everywhere.
5. **mean|∇| is a one-sided metric.** Dispatched to M18 (§6).
6. **The aperture finding (§4.4) is the actionable one** and is independent of everything else here.
7. **The baseline used throughout was argmax selection — the weakest possible.** Against the
   project's actual planned merge (regularised + noise-gated, M18), the margin will be *smaller*
   than measured here. Every number in this document is generous to the deconvolution.

## 9. What is NOT measured here

- **1-D only.** In 2-D the recoverable band area scales as `f_c²`, which likely makes deconvolution
  look worse, not better — but that is ARGUED, not measured.
- **Oracle depth throughout.** Real depth error can only hurt. Upper bound.
- **No occlusion.** The review's two-layer/bimodal occlusion-unmixing proposal is **untouched by
  this milestone** and remains open and interesting. Nothing here argues against it.
- **One subject.** `109MSDCF` only. The σ_rel distribution is subject-dependent; a high-contrast
  subject would move the 15%.
- **∇-correlation weights strong edges heavily.** A perceptual metric may disagree.
- **Not independently verified.** Scripts are in the session workspace, not yet committed as an
  experiment; a verifier should re-derive rather than re-run them.
