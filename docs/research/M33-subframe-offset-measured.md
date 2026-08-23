# M33 — the sub-frame focus peak: what it costs, and why the standard estimator cannot report it

> **STATUS: MEASURED BY THE ORCHESTRATOR — NOT INDEPENDENTLY VERIFIED.**
> Rule 12 binds this document's author exactly as it binds any milestone author.
> Every number came out of a script in `experiments/m33-subframe-offset/src/` run
> against the owner's own captures or against synthetic curves with known shape.
> Four defects in this milestone's own scripts and predictions are recorded in §6.

**What this settles.** `B-algorithms-sota.md` §4.4 flagged the choice between
parabolic and Gaussian sub-frame interpolation **UNVERIFIED**, noted that no paper
in the survey measured it on a focus stack, and asked for it to be settled
empirically on our own data. This does that, and answers question 65's candidate
(c) — the sub-frame peak offset, which fact 263 named as the load-bearing
confidence quantity and which nothing in the project estimated.

**Two findings, and the second is the one that generalises beyond this project.**

1. **The offset costs nothing at the median and a great deal in a large
   minority.** At operational ×2 sampling, **48.7%** of pixels miss their peak
   entirely; those lose a median **4.64%** of their focus response, **10.74%** at
   p90 and **17.34%** at p99. That is the exact profile of something that needs a
   per-pixel confidence output and is invisible to a global quality claim.
2. **Three-point parabolic interpolation — standard practice everywhere — gives a
   peak-height estimate that is *anti-correlated* with the quantity it reports.**
   On a synthetic Gaussian its predicted deficit falls **21×** (1.55% → 0.07%)
   while the true deficit rises **8×** (3.08% → 24.57%). The log-domain fit is
   exact. On real data the log fit with baseline subtraction is the difference
   between an unusable confidence estimate and a usable one.

**And the scope limit that keeps finding 2 honest:** this failure is specific to
the peak **height**. For the peak **position**, which is what interpolation is
more often used for, the parabola is *adequate* at operational sampling — 4.03×
better than the trivial argmax, only 9.4% worse than the log fit. §5 gives the
mechanism for why the same fit is fine for one output and disqualifying for the
other.

---

## 0. Ground truth, and whether it is good enough

`coffee-bean`, **all 105 frames**, the same centred 1024×1024 green-sublattice
crop and the same M27 focus measure (box-mean Sobel magnitude, radius 2) used by
M27 and M32. Within the crop the dense argmax spans frames 20–46 (p5–p95) and 30
frames hold more than 1% of pixels.

The operational stack is a **×2 decimation** of that grid — which is exactly the
53-frame stack M32 measured — so every claim is about what an operational stack
loses against a focus axis sampled twice as finely. **Retention** is measured from
real samples only, `f(best sampled frame) / f(best dense frame)`, with no
interpolation anywhere in the truth.

The dense grid is itself sampled, so it misses its own peaks too, and if it missed
them by as much as the ×2 grid does then nothing here would be readable. That was
pre-registered as a falsifying check (**P7**, threshold 3×):

| quantity | value |
| --- | --- |
| dense grid's own estimated deficit | **0.711%** |
| ×2 grid's measured deficit (mean over all pixels) | **2.753%** |
| **ratio** | **3.87×** |

**P7 passes, but not by much.** The ground truth is finer than the effect by a
factor of about four. Every number below should be read with that headroom in
mind, and a ×4 grid would not have been adequate ground truth for a ×2 measurement.

---

## 1. What the offset costs

The distribution is a **mixture** and the median is meaningless on it: a ×2 grid
contains half the dense frames, so a pixel whose peak lands on a sampled frame has
retention *exactly* 1. About half of them do. The quantity with meaning is the
deficit **conditional on missing**.

| sampling | peak sampled exactly | mean deficit, all pixels | **conditional median** | conditional p90 | conditional p99 | median offset (dense frames) |
| --- | --- | --- | --- | --- | --- | --- |
| ×1 (control) | 100% | 0.000% | — | — | — | 0.228 |
| **×2 even (operational)** | **48.7%** | **2.75%** | **4.64%** | **10.74%** | **17.34%** | 0.517 |
| ×2 odd (replication) | 51.3% | 2.59% | 4.60% | 10.75% | 16.65% | 0.483 |
| ×4 | 23.9% | 9.74% | 11.47% | 25.24% | 35.26% | 1.007 |
| ×6 | 15.9% | 19.60% | 21.43% | 45.11% | 58.38% | 1.701 |

The two ×2 phases are two equally legitimate operational stacks and nothing should
distinguish them; they agree to **0.05%** in conditional median deficit and to
**0.01%** at p90. That is the replication null, and it passes cleanly.

Reading the ×2 row: **roughly half of all pixels are rendered from a frame that is
not the sharpest one available even in principle, and they give up about 5% of
their focus response for it, with a tail to 17%.** That is not catastrophic and it
is not nothing. It is precisely the kind of quantity that a per-pixel confidence
map exists to report and that a single global number cannot.

Fitting a Gaussian width to the decimation ladder gives an implied through-focus
σ of **1.68 / 2.04 / 2.45 dense frames** from the ×2 / ×4 / ×6 arms. The drift is
itself informative: a true Gaussian would give one number, so the real response has
**heavier shoulders than a Gaussian**, which matters in §3.

---

## 2. The predictor fails, and fails in a familiar way

The obvious inference-time estimate is free: fit a parabola through the three
decimated samples around the argmax and compare the sampled maximum to the
extrapolated peak. Its rank correlation with the truth is respectable —
**Spearman ρ = 0.583** at ×2 — but rank correlation is not what a confidence output
needs. It needs the **magnitude** to be right.

| sampling | true deficit (mean) | **parabola's predicted deficit** |
| --- | --- | --- |
| ×2 | 2.75% | **1.52%** |
| ×4 | 9.74% | **1.51%** |
| ×6 | 19.60% | **1.46%** |

**The prediction is pinned near 1.5% while the truth changes by 7×.** Calibration,
measured as the median ratio of predicted to true deficit among pixels that miss:
**0.457** at ×2, **0.115** at ×4, **0.042** at ×6, with only **37.5% / 5.0% / 1.9%**
of pixels within a factor of two.

This is the signature discipline 120 describes, in a third independent guise. The
parabola's *relative* deficit depends only on the **shape** of three samples, which
is scale-free, so it barely moves with the spacing that determines the answer.
M27 found it in a curvature ratio, M32 found it in a self-normalised posterior
temperature, and here it is in the most standard piece of sub-pixel machinery in
the field.

---

## 3. The mechanism, tested rather than asserted, and the fix

If the mechanism is "a parabola through widely spaced samples of a shouldered peak
is too flat", then it must reproduce from first principles on a synthetic curve
with no scene in it. It does, and more strongly than on real data:

**Synthetic Gaussian, σ = 2 samples, random offsets, 200k trials:**

| spacing | true deficit | parabola predicted | ratio | log-fit predicted | ratio |
| --- | --- | --- | --- | --- | --- |
| h = 2 | 3.08% | 1.55% | 0.502 | **3.08%** | **1.0000** |
| h = 4 | 11.76% | 0.79% | 0.068 | **11.76%** | **1.0000** |
| h = 6 | 24.57% | **0.07%** | 0.003 | **24.57%** | **1.0000** |

**The parabola's prediction falls 21× while the truth rises 8×.** It is not merely
uncalibrated; over this range it is *anti-correlated* with the quantity it reports.
**P9 confirmed**, by a much wider margin than pre-registered.

The fix follows from the diagnosis. If the response is approximately Gaussian in
defocus then `log f` is exactly a parabola, so the same three-point fit in the log
domain is exact at every spacing — ratio **1.0000** above, error at machine
precision. **P10 confirmed.** It is a one-line change wherever the interpolation is
done.

**The placebo matters here**, because "the log fit wins" would be unfalsifiable if
log simply helped everywhere. On a curve that genuinely *is* a parabola, at h = 2:
the parabola fit is **exact (ratio 1.000)** and the log fit is **3.02× wrong**. The
placebo fires in the right direction. *(The h = 4 and h = 6 placebo cells are
degenerate — the synthetic parabola has compact support, so the outer samples clamp
to the floor and the fit collapses. Only the h = 2 cell is readable, and it is
enough to establish the direction.)*

**On real data**, where the response is Gaussian-*ish* and sits on a non-zero
baseline, the fix is real but partial:

| ×2 sampling | predicted deficit | calibration ratio | within 2× |
| --- | --- | --- | --- |
| true | 4.64% | 1.000 | — |
| parabola | 2.06% | 0.457 | 37.5% |
| log | 3.00% | 0.664 | 49.6% |
| **log + baseline** | **3.24%** | **0.710** | **51.2%** |

**P11 confirmed**: the log-baseline fit beats the parabola on both measures at
every decimation, and at operational ×2 sampling it is the first estimator in this
milestone to clear the pre-registered calibration bar (ratio within [0.5, 2.0] and
more than half of pixels within 2×) — which the parabola failed. Baseline
subtraction matters because `log` is not shift-invariant and the focus measure does
not reach zero when defocused.

At ×4 and ×6 the log fit still under-predicts badly (ratio 0.368, 0.223), so the
honest scope is: **the fix works at operational capture density and degrades under
sparse sampling**, in the same direction as everything else in this milestone.

---

## 4. Position, where the parabola is fine

Interpolation is more commonly used for the peak *position* — the sub-frame depth
estimate — than for its height, and a finding about height does not transfer for
free. Scored against the same dense-grid truth, with the trivial "use the sampled
argmax" estimator as the null:

**Synthetic Gaussian:** the parabola's position estimate is **shrunk toward the
sampled maximum** by a factor **0.403 at h = 4** and **0.110 at h = 6**; the log fit
recovers the offset exactly (shrinkage 1.000, error ~10⁻¹⁷). **P12 confirmed.**

**Real data**, median absolute position error in dense-frame units:

| sampling | null (sampled argmax) | parabola | **log + baseline** | parabola gain | log gain |
| --- | --- | --- | --- | --- | --- |
| ×2 | 0.517 | 0.128 | **0.116** | 4.03× | **4.44×** |
| ×4 | 1.007 | 0.478 | **0.334** | 2.10× | **3.01×** |
| ×6 | 1.701 | 0.920 | **0.638** | 1.85× | **2.67×** |

**P13 confirmed**, but read the sizes. At operational ×2 sampling the parabola
already recovers **4.03×** of the null's error and the log fit improves on it by
only **9.4%**. The parabola is *fine* for position at operational density. The
catastrophic failure in §2–3 is specific to the peak **height**.

**Why the same fit is adequate for one output and disqualifying for the other:**
position is determined by the **asymmetry** of the three samples — a first-order
property that any smooth fit through them captures. Height is determined by
**curvature extrapolated beyond** the samples — a second-order property that is
entirely a consequence of the assumed functional form, about which three points
carry no information. The parabola is not estimating the peak height from the data;
it is reporting its own assumption, evaluated at the data. That is the same
sentence discipline 120 has now been written three times to express.

---

## 5. What to build

1. **Use the log-domain (Gaussian) three-point fit with baseline subtraction**
   wherever sub-frame interpolation happens, and settle `B` §4.4's UNVERIFIED
   marker in its favour. It is a one-line change, it is exact on the modelled
   shape, its placebo confirms it is not universally superior, and on real data at
   operational density it converts an uncalibrated estimator into a calibrated one.
2. **Emit the predicted focus-response deficit as part of the confidence output.**
   It is free once the fit is being done, and question 65's candidate (c) is now
   the only one of the three with a measured magnitude attached: about half of all
   pixels give up ~5% of their response, with a tail to 17%.
3. **Do not use the parabola's peak height for anything**, including gate
   thresholds and quality reporting. §3 measures it as anti-correlated with the
   truth over the operating range.
4. **A capture advisory falls out at no cost.** Deficit grows 2.75% → 9.74% →
   19.60% from ×2 to ×6, so the fraction of pixels missing their peak, and by how
   much, is directly computable from a shot stack and is exactly the "reshoot with
   step ×0.5" recipe the review asked for. It joins M27's coverage criterion and
   M30's clipping trigger in the same advisory.

---

## 6. My errors

**Error 1 — sign error in the parabola vertex value (script 02).** For samples
`(am, a0, ap)` with `dn = am − 2a0 + ap`, the vertex value is
`a0 + 0.25·(ap − am)·x*`; script 02 wrote a minus, putting the predicted peak
*below* the sampled maximum and making every predicted deficit negative. Script 02
is left committed exactly as run per rule 15. Its Spearman figures were still
readable — the two forms are monotone decreasing functions of each other, so its
−0.583 corresponds to +0.583 — but that is an argument, so script 03 **measured**
it rather than asserting it, and recovered +0.5831769 against script 02's
−0.5831769.

**Error 2 — the median was the wrong summary, and I did not notice until the
number looked odd.** Script 02 reported a median deficit of 0.234% for the even
phase and *exactly 0.000%* for the odd phase, which is not a difference between the
stacks but an artefact of a point mass: ~50% of pixels have retention exactly 1, so
the median sits on the boundary of the mass and reports which side of 50% it fell
on. The real quantity, conditional on missing, is 4.64% — **20× larger**. The
general form: *when a statistic can be exactly zero for a large fraction of the
population, the median reports the size of that fraction rather than the size of
the effect.* Check for point masses before choosing a quantile.

**Error 3 — I pre-registered an effect size for a statistic whose distribution I
had not thought about.** P1 predicted ~7% median deficit at ×2, from a Gaussian
argument. The conditional median is 4.64%, so the *physics* was about right; the
all-pixel median is 0.234%, so the prediction was wrong by 30× for the statistic I
actually named. Discipline 142 requires a pre-registered effect size; this is the
failure mode it does not by itself prevent — getting the magnitude right for the
wrong estimator.

**Error 4 — script 03 was edited after running.** It raised an `IndexError` on the
×1 arm, where the set of pixels that miss their peak is empty by construction, and
produced **no output and no results file** before the edit. The edit added an
empty-set guard and changed nothing else. Recorded because rule 15 exists to stop
scripts being retro-fitted to their results, and there were no results to fit to,
but the edit happened and should be visible rather than silent.

**Error 5 — the synthetic parabola placebo is only readable at h = 2.** The
compact-support parabola clamps its outer samples to the floor at h ≥ 4, degenerating
the fit; both estimators return 0.0 there. Disclosed rather than dropped, since the
h = 2 cell is decisive on its own.

---

## 7. Reproducing this

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
$env:PYTHONIOENCODING='utf-8'
python experiments\m33-subframe-offset\src\01-build-dense.py   # ~42 s, writes out/cache/dense_focus.npy (440 MB, gitignored)
python experiments\m33-subframe-offset\src\02-offset.py        # superseded by 03; retained per rule 15
python experiments\m33-subframe-offset\src\03-corrected.py
python experiments\m33-subframe-offset\src\04-logfit.py
python experiments\m33-subframe-offset\src\05-position.py
```

Steps 2–5 draw the same 40,000 pixels from the same seed, so their arms are
directly comparable pixel by pixel.
