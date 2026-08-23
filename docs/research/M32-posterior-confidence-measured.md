# M32 — the per-pixel posterior over depth: what it is good for, and what it is not

> **STATUS: MEASURED BY THE ORCHESTRATOR — NOT INDEPENDENTLY VERIFIED.**
> Rule 12 binds this document's author exactly as it binds any milestone author.
> Every number below came out of a script committed in
> `experiments/m32-posterior/src/` and run against the owner's own captures, but
> nobody other than the author has reproduced any of it. Two of this milestone's
> own pre-registered predictions were falsified by its own controls (§5), which
> is the only reason to trust the rest of it more than the arguments it replaced.

**Review item:** R2, the second-ranked proposal in the external review —
*"per pixel, carry a posterior distribution over frame-of-best-focus; then for
free: merge weights, confidence = posterior entropy, occlusion = bimodality,
'no frame in focus' = mass at the boundary."*

**Scope of this milestone:** the **confidence** limb only. Bimodality was measured
separately in M21 (4.38× enrichment at depth steps). Merge weights are M20's and
M18's. This milestone asks one question: **is posterior entropy admissible as a
confidence output under discipline 120?**

**Answer: no, and the reason is more interesting than the answer.** The
self-normalised form fails exactly as discipline 120 predicts, and now fails with
a number attached. The *correctly calibrated* form does not fail — it is simply
**degenerate**, because focus evidence on this rig is overwhelming: the
through-focus peak stands **142–991 σ** above its own curve. There is nothing for
a confidence statistic to be uncertain about in the frame choice. That relocates
the whole confidence problem, and §6 argues it relocates it somewhere the project
can actually build.

---

## 0. What was measured, and on what

`coffee-bean`, every second frame (**53 of 105**), a centred **1024×1024 crop of
the green sublattice**, native DN above a black level of 512. Median signal 1454
DN, median per-pixel SNR **112.6**, **0.0%** of pixels below SNR 10, and
7.2 × 10⁻⁵ clipped. This is the cleanest stack in the corpus, chosen deliberately:
a confidence statistic that cannot behave on clean data will not be rescued by
dirty data, and degradation can be applied in a controlled sweep afterwards,
which it was.

Focus measure throughout is M27's: box-mean of the Sobel magnitude, radius 2.

**The two arms.** A posterior over frame index needs a temperature, and that
choice *is* the choice discipline 120 is about:

| arm | temperature | character |
| --- | --- | --- |
| **N** | the noise sd of the focus response, from the M4 model via Monte Carlo | **externally referenced** |
| **S** | `std_k(f_k)`, the spread of the observed curve itself | **self-normalised** |

`p_k ∝ exp((f_k − max_k f) / T)`, and the readout is normalised entropy
`H / log n ∈ [0,1]` and its exponential, the **perplexity** `exp(H)` — the
effective number of frames the posterior cannot separate. Perplexity is the same
quantity M27 called `n_eff`, so the posterior's width and the coverage criterion
turn out to be one number, which is the one piece of the review's unification
that survives this milestone intact.

---

## 1. The headline: the self-normalised arm is blind to the evidence, measured

Six texture bins spanning a **9.1× range of scene texture** (11.5 → 104.5 DN
local contrast) and, more to the point, a **6.1× range of actual focus evidence**
— the peak-over-noise ratio rising 119 → 728 in Monte-Carlo units:

| texture bin | texture (DN) | **peak / T (evidence)** | arm N entropy | arm N perplexity | arm S entropy | arm S perplexity |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 11.5 | **119.3** | 2.3 × 10⁻⁴ | 1.0009 | **0.6480** | 13.10 |
| 1 | 21.1 | 223.7 | 2.7 × 10⁻⁸ | 1.0000001 | 0.6111 | 11.31 |
| 2 | 30.3 | 285.8 | 6.7 × 10⁻¹¹ | 1.0000000003 | **0.6085** | 11.20 |
| 3 | 42.6 | 360.1 | 1.9 × 10⁻¹³ | 1.000000000001 | 0.6154 | 11.51 |
| 4 | 63.0 | 467.9 | 4.7 × 10⁻¹⁷ | 1.0000000000000 | 0.6286 | 12.13 |
| 5 | 103.9 | **728.0** | 2.7 × 10⁻²³ | 1.0000000000000 | **0.6482** | 13.11 |

Read the arm S column twice. **At 119 σ of evidence it reports 0.6480. At 728 σ
of evidence — 6.1× more — it reports 0.6482.** A 0.03% change in the statistic
across a six-fold change in the quantity it claims to measure. And it is not even
monotone: it *falls* to 0.6085 in the middle of the range and comes back up, so
there is no order-preserving transformation that rescues it. A statistic that is
non-monotone in the thing it purports to report is disqualified, and this is the
sharpest available form of discipline 120 — M27 could argue it from three
instances, and this measures it.

The mechanism is not subtle once stated: dividing by `std_k(f_k)` divides out the
peak height, which *is* the evidence. What survives the division is the curve's
**shape** — how peaked it is relative to itself — and shape is a property of the
scene's depth structure and the optics, not of how well the measurement was made.
Arm S is a perfectly good statistic. It is a statistic about the *subject*.

### The same thing, on the axis that only means evidence

The texture sweep changes scene content as well as evidence. The SNR sweep does
not: the same 20,000 textured pixels, degraded by adding calibrated noise, so
nothing about the subject changes and only the evidence falls.

| degradation | median SNR | arm N perplexity | arm S perplexity |
| --- | --- | --- | --- |
| ×1 | 134.5 | 1.0000 | 13.05 |
| ×2 | 67.3 | 1.0000000000 | 12.98 |
| ×4 | 33.6 | 1.00002 | 12.79 |
| ×8 | 16.8 | 1.0125 | 12.40 |
| ×16 | **8.4** | **1.2063** | **11.85** |
| *no-information null* | — | *33.97* | *33.97* |

Arm N moves **22 orders of magnitude** in entropy (3.3 × 10⁻²⁴ → 4.7 × 10⁻²).
Arm S moves **9%**, and stays pinned near 12–13 throughout. It approaches neither
the certainty floor of 1 nor the no-information ceiling of 34. **Arm S reports
"about twelve candidate frames" on every pixel of every bin at every signal-to-noise
ratio tested** — which is exactly what a shape statistic does, and exactly why it
cannot be thresholded.

---

## 2. The no-information fixed point is not 1, and it is a pure function of *n*

This is where the milestone's first pre-registered prediction died, and it is
worth stating plainly because the error is an easy one and it is in the review's
proposal too.

Intuition says a posterior carrying no information is uniform, so `H / log n = 1`.
It is not. Taking the **maximum** of *n* noisy values produces a value ≈ 3 sd above
the rest by construction, so even a perfectly calibrated softmax concentrates on
pure noise. The scene-free placebo — a synthetic cube with the right noise and no
subject at all — landed at **0.874** at *n* = 53, drifting to **0.811** at *n* = 9.

Simulating the null directly (softmax over *n* iid unit-variance draws, 200,000
trials) reproduces it:

| *n* | null entropy | step-2 scene-free placebo | null perplexity | null perplexity / *n* |
| --- | --- | --- | --- | --- |
| 53 | 0.8879 | **0.8742** | 33.97 | 0.641 |
| 27 | 0.8747 | 0.8408 | 17.86 | 0.662 |
| 18 | 0.8660 | 0.8467 | 12.22 | 0.679 |
| 14 | 0.8602 | 0.7987 | 9.68 | 0.692 |
| 9 | 0.8503 | 0.8108 | 6.48 | 0.720 |

Agreement at *n* = 53 is 0.0137, inside the pre-registered 0.02 (**P5 confirmed**),
so the null **is** a pure function of *n* and can be tabulated once and stored.
**P6 confirmed**: no-information perplexity is 64–72% of *n* at every *n* tested.

**Consequence, and it is a real one:** any threshold on posterior entropy must be
referenced to this *n*-dependent null rather than to `log n`. A tool that ships
"entropy > 0.9 means unreliable" would call every pixel of a 9-frame stack reliable
and would be wrong by construction, because 9-frame noise tops out at 0.85. This
applies to the review's proposal as written.

---

## 3. Focus evidence is overwhelming, and the number does not depend on the noise model

Everything above rests on `T`, and `T` came from a Monte Carlo that uses the
observed frames as a proxy for the noise-free scene. That proxy already carries
one realisation of noise, so `T_mc` is biased **high** — which flattens the
posterior and *under*-claims information, the safe direction, but a load-bearing
number should not rest on a bias argument.

So `T` was re-estimated with nothing in common with the first method: from the
focus curve's own along-*k* roughness. For a smooth curve plus iid noise the
second difference `f_{k−1} − 2f_k + f_{k+1}` has variance `6σ_f²`; evaluated on the
**defocused tail**, where the through-focus response is flat, the curvature term
is negligible and a robust scale of that difference gives `σ_f` with no noise
model, no Monte Carlo, and no added noise.

| bin | `T_mc` | `T_roughness` | ratio | peak / `T_mc` | **peak / `T_roughness`** |
| --- | --- | --- | --- | --- | --- |
| 0 | 18.07 | 15.36 | 0.806 | 115.1 | **141.9** |
| 1 | 24.23 | 18.05 | 0.779 | 226.8 | 285.9 |
| 2 | 24.86 | 18.75 | 0.774 | 286.1 | 373.9 |
| 3 | 25.67 | 19.46 | 0.772 | 358.4 | 467.3 |
| 4 | 26.41 | 19.69 | 0.755 | 471.7 | 621.1 |
| 5 | 27.67 | 20.44 | 0.736 | 726.3 | **990.8** |

**P8 confirmed** (ratio 0.736–0.806, inside the pre-registered [0.5, 2.0]), and
the disagreement is in the predicted direction and of modest size: the Monte Carlo
over-estimates `T` by about 24%, exactly the conservative bias argued for in
advance. **P9 confirmed**: with the model-free estimate the evidence ratios *rise*,
to **142–991 σ**.

The falsification threshold was set in advance and deliberately loose: the claim
dies only if the two estimates disagree by ~100×, the factor needed to bring the
least-textured bin down to the null. They disagree by 1.24×. **The conclusion is
insensitive to the noise model being wrong by two orders of magnitude.**

---

## 4. What this means: the frame choice is not the uncertain part

Put §1 and §3 together. On this rig, with this sensor, the identity of the
best-focused frame is established at 142–991 σ, and stays established through a
16× degradation of SNR that puts the data below the dimmest stack in the corpus.
**A calibrated posterior over frame index is a delta function on real data.**

That is a falsification of the review's confidence proposal, but it is not a
disappointment, because it says something the project needs to know:

> **The defect in selection is not a noise problem.** M2 measured that argmax is
> defective in lit, low-contrast regions; M27 measured that pixels resolved by
> ≤ 1 sample are common under decimation. Neither of those can be a
> signal-to-noise failure, because there is no plausible sense in which a
> 142 σ peak is noise-limited. They are **sampling and model** failures: the true
> peak lies *between* frames, and the estimator has no term for that.

Which relocates confidence. The uncertain quantity is not *which frame is best* —
that is nearly certain. It is **which frames are equivalent**, i.e. the width of
the acceptance set, which is exactly M27's `n_eff ≈ 3`, and **how far the true
peak sits from the nearest sample**, which is a focus-axis sampling quantity that
no arrangement of the focus curve's own values can report.

This also reconciles cleanly with **M20**, and the two milestones now say the same
thing from opposite directions. M20 found the unguarded Wiener estimator *loses*
to argmax by up to 31% even with oracle depth, and that only 15.1% of real pixels
beat the crossover. M32 explains why: when one frame's evidence stands at 10²–10³ σ
above the rest, the minimum-variance estimator *is* nearly a selector, and the
matched filter has almost nothing to harvest from neighbours. The estimation
content of this project does not live in the frame choice. It lives in **averaging
among the frames that genuinely agree** (M14's 0.534× on flat regions), in the
**sub-frame peak location**, and in the **noise model that says which frames those
are** — not in softening a decision that the data has already made.

The thesis survives and gets sharper. "Estimation, not selection" is a claim about
estimating the **pixel value**, and it is unaffected. It was never a claim about
being unsure which frame won, and this milestone says it should not become one.

---

## 5. My errors

Two of this milestone's own pre-registered predictions were falsified by its own
controls. Both are recorded because they are the reason the surviving results are
worth anything.

**Error 1 — I predicted the wrong null, from an intuition I did not check.**
P1 asserted that a correctly calibrated posterior would read `H / log n ≥ 0.95` on
information-free pixels. The scene-free placebo returned **0.874**, and the
simulated null confirmed it. The intuition "no information ⇒ uniform posterior"
ignores that the statistic is built from a **maximum**, and the maximum of *n*
noise draws is not typical of them. The general form is worth carrying: *any
statistic defined relative to an extremum has a null that depends on the sample
size, and that null must be simulated rather than reasoned about.* Discipline 142
demanded a pre-registered effect size, which I supplied — but I derived it by
argument instead of by simulating the null, which would have cost ten seconds and
caught it before the experiment ran.

**Error 2 — my "information-free" population had 119 σ of information in it.**
Step 2 split pixels into "flat" and "textured" by local contrast and treated flat
as the no-evidence condition. It is not: the texture measure was computed on the
**frame-averaged** image, whose noise is `σ/√53 ≈ 1.1` DN, so a 5.9 DN local
contrast is real scene structure at 5.4× the averaged noise floor. The texture
sweep in §1 shows the least-textured bin in the entire crop still carries 119 σ of
focus evidence. **There is no information-free real population in this data**, and
every "flat vs textured" comparison in step 2 is a comparison of *more evidence
against slightly less*, not of evidence against none. The step-2 flat/textured
numbers are therefore retracted as a null; the synthetic placebo and the SNR sweep
are the two valid references, and §1 and §2 rest only on those.

The general form is the sharper lesson, and it is a near-relative of discipline
130: *a population selected by thresholding a statistic computed on averaged data
is not selected on the property you think — averaging changes the noise floor the
threshold is implicitly referenced to.* I picked the threshold by percentile, which
guaranteed a population existed, and never checked whether it had the property the
experiment needed.

**P7 was also falsified, mildly and honestly.** It predicted perplexity < 1.05
at every point of the SNR sweep including ×16; the measured value at ×16 is
**1.206**. The claim it was testing survives — 1.21 against a null of 33.97 is
still a delta — but the prediction as written was wrong and is recorded as wrong.

---

## 6. What to build, and what not to

**Do not** ship posterior entropy as the confidence output. In its self-normalised
form it is non-monotone in the evidence (§1). In its calibrated form it is a delta
everywhere (§3) and carries no gradation to threshold.

**Do** keep the posterior, for three narrower jobs it is genuinely good at:

1. **Perplexity as `n_eff`.** `exp(H)` with the calibrated temperature is the
   effective number of frames the data cannot separate, which is M27's coverage
   quantity computed in a single pass. One statistic, two uses, and the null curve
   in §2 gives it an absolute reference.
2. **Pathology detection, not confidence grading.** The calibrated posterior does
   cleanly separate "there is a subject here" (perplexity 1.0) from "there is not"
   (33.97). That is a *binary* flag for the genuinely degenerate case, and it should
   be labelled and used as one.
3. **Bimodality**, which M21 already measured at 4.38× enrichment and which this
   milestone does not touch.

**Confidence itself must come from somewhere else**, and §4 says where: the
predicted σ of the merged estimate under the noise model, the width of the
acceptance set, and the distance from the true peak to the nearest sampled frame.
None of those is a function of the focus curve's shape, which is precisely why
discipline 120 disqualified shape statistics in the first place.

---

## 7. Reproducing this

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
$env:PYTHONIOENCODING='utf-8'
python experiments\m32-posterior\src\01-build.py        # ~20 s, writes out/cache/raw.npy (222 MB, gitignored)
python experiments\m32-posterior\src\02-entropy.py      # ~6 min
python experiments\m32-posterior\src\03-null.py         # ~5 min
python experiments\m32-posterior\src\04-temperature.py  # ~5 min
```

Scripts are committed exactly as run and must not be edited (rule 15). Step 2's
`flat`/`textured` populations are retracted as a null per §5 but the script is left
untouched, and its SNR sweep and placebo — the parts §1 and §2 rest on — are
unaffected by that retraction.
