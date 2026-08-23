# M35 — Does the sub-frame fit generalise? (and an audit of M33's margin)

> **NOT INDEPENDENTLY VERIFIED.** Measured by the orchestrator. Rule 12 binds the
> author of this file exactly as it binds any milestone author.

**Milestone:** M35
**Question:** 70 — does M33's log-domain sub-frame fit hold up away from
`coffee-bean`'s optics?
**Data:** three stacks at a fixed 200 mm (the 100 mm GM with the 2× TC), read-only.

| stack | n | marked f | ISO | role |
|---|---|---|---|---|
| `119MSDCF` | 33 | **f/5.6** | 50 | wider aperture, **same ISO as coffee-bean** |
| `coffee-bean` | 105 | f/8 | 50 | M33's stack, **recomputed here, not quoted** |
| `112MSDCF` | 79 | **f/11** | 500 | narrower aperture, **ISO confounded** |

Stated up front: `119` vs `coffee-bean` is a clean aperture-only comparison. `112`
changes aperture *and* ISO together, so any `112`-only finding is
aperture-or-SNR, never aperture.

---

## 1. Headline — the question cannot be answered on existing captures, and the gate that says so is the same one M33 wrote

M33 established that a dense grid is honest ground truth only if its **own**
sampling deficit is much smaller than the one being measured, and set the bar at
its measured **3.87×** headroom while noting a ×4 grid would not have passed.
Applying that gate:

| stack | marked f | true deficit at ×2 | ladder slope | extrapolated deficit at ×1 | **headroom** | |
|---|---|---|---|---|---|---|
| `119MSDCF` | f/5.6 | 5.810% | **1.129** | 2.668% | **2.18×** | ❌ **FAIL** |
| `coffee-bean` | f/8 | 2.876% | **1.818** | 0.795% | **3.62×** | ✅ pass |
| `112MSDCF` | f/11 | 4.981% | **1.094** | 2.369% | **2.10×** | ❌ **FAIL** |

**Two of the three stacks are too coarsely sampled to serve as their own ground
truth.** Their dense grids are already missing peaks badly enough that decimating
them further tells you about the grid, not about the estimator. Question 70 stays
open, and it stays open for a capture reason rather than an analysis reason.

### The ladder slope is a second, independent adequacy diagnostic

Near a smooth peak the sampling deficit should grow roughly as `h²`. The measured
log–log slopes are **1.818** for `coffee-bean` — close to quadratic, as an
adequately-sampled peak must be — and **1.129 / 1.094** for the two failures.

A **sub-quadratic slope is the signature of a ground truth that is itself
under-sampled**: if the reference already misses the peak, decimating further adds
less than `h²` because much of the deficit was there at `h = 1`. The slope and the
headroom test agree on all three stacks while being computed differently, which is
the kind of redundancy worth having in a gate. **The slope is the cheaper of the
two and should be the front-line check**, since it needs no extrapolation.

---

## 2. What survives the failed gate — and why

One comparison is **robust to the ground truth being wrong**: the *ratio* between
two estimators scored against the *same* truth. A multiplicative error in the
reference cancels.

| stack | marked f | parabola | log fit | **log / parabola** |
|---|---|---|---|---|
| `119MSDCF` | f/5.6 | 0.199 | 0.408 | **2.05×** |
| `coffee-bean` | f/8 | 0.549 | 0.841 | **1.53×** |
| `112MSDCF` | f/11 | 0.216 | 0.387 | **1.79×** |

**The log-domain fit beats the parabola on every stack**, across a 2× range of
marked aperture and a 10× range of ISO — and it does so in all eight cells of
section 4's factorial and all four of section 5's. That is the part of M33 that
generalises, and it is the part M18 actually needs.

The *absolute* calibration numbers for `119` and `112` are **not reportable** and
appear here only to make the ratio legible.

---

## 3. M33 reproduces exactly, from independent code

Running M33's published configuration — its 40,000-pixel random sample, its
5th-percentile baseline, its median-of-ratios statistic, its RNG stream — through
a script written from scratch:

| | M33 published | M35 reproduced |
|---|---|---|
| parabola calibration | 0.457 | **0.457** |
| log-baseline calibration | 0.710 | **0.710** |
| log within 2× | 51.2% | **51.2%** |

Three-decimal agreement on all three. **M33's arithmetic is confirmed.** (Its
*design* is a separate question — see section 4.)

This matters because M35 script 02 got **0.549 / 0.841** on the same cached volume,
and the obvious reading of that was that one of the two milestones was wrong.
Neither is: they compute different statistics. Section 4's factorial separates
them.

---

## 4. A real confound in M33's design, found and priced

M33 script 04's real-data arm ran exactly three modes:

```
("parabola", base=0.0)   ("log", base=0.0)   ("log_baseline", base=p5)
```

**There is no `parabola_baseline` arm.** So fact 272's headline compares a **raw**
parabola against a **baseline-subtracted** log fit, and two things change at once.
This is not a nitpick: the relative deficit `1 − a0/peak` is not shift-invariant
for the parabola either, so subtracting a floor rescales precisely the quantity
being reported. Some unknown share of the published margin could have been the
baseline rather than the log domain.

Running the missing cell, on M33's own pixels and statistic:

| ×2 | calibration | within 2× |
|---|---|---|
| parabola, raw | 0.457 | 37.5% |
| **parabola, baseline-subtracted** | **0.479** | **39.4%** |
| log, raw | 0.664 | 49.6% |
| log, baseline-subtracted | 0.710 | 51.2% |

**Decomposition of the published +0.253 margin:**

| | ×2 | ×4 |
|---|---|---|
| attributable to the **baseline** | +0.022 — **9%** | +0.007 — **3%** |
| attributable to the **log domain** | +0.231 — **91%** | +0.246 — **97%** |

**Fact 272 survives, and is better supported than when it was published**, because
the confound that could have explained it has now been measured and is small. The
log domain does 91% of the work at ×2 and 97% at ×4.

**My pre-registered guess was wrong, in the fact's favour.** I predicted the
baseline-subtracted parabola would land near 0.55 — about a third of the margin —
and registered that in the script before running it precisely because I had
already folded fact 272 into SYNTHESIS and a prediction made after seeing the
answer is worthless. It landed at 0.479.

**The generalisable lesson: when an estimator changes in two ways at once, the
comparison prices the pair, not the part you are claiming.** M33 changed the
domain *and* the baseline together. It happened to be right, and it could just as
easily not have been. Every future estimator comparison needs the full factorial,
not the diagonal.

---

## 5. Predictions

Five registered in script 02, one in script 04. **Two confirmed, four falsified.**

| | prediction | outcome |
|---|---|---|
| P1 | every stack passes adequacy with headroom > 3 | ❌ **two of three fail** (2.18×, 2.10×) |
| P2 | parabola calibration < 0.6 on every stack | ✅ 0.199 / 0.549 / 0.216 |
| P3 | log fit beats parabola on every stack | ✅ **2.05× / 1.53× / 1.79×** |
| P4 | log advantage shrinks as aperture closes; 119 > cb > 112 | ❌ measured **119 > 112 > cb**, non-monotone |
| P5 | implied Gaussian width grows as aperture closes | ❌ **1.69 / 2.41 / 1.83** at ×2, non-monotone |
| script 04 | baseline-subtracted parabola ≈ 0.55 (⅓ of margin) | ❌ **0.479 (9% of margin)** |

**P4 and P5 are falsified but uninformative.** Both are read off the two stacks
that failed the adequacy gate, so their non-monotonicity is at least as likely to
be the ground truth's defect as the optics'. Recorded as failed rather than
quietly dropped, but **they must not be cited as evidence that the fit is
aperture-independent** — that is exactly the claim this data cannot support.

---

## 6. What this asks Chris for

To answer question 70, one thing is needed and it is cheap:

> **A denser focus bracket at two apertures, on any static subject.** Same
> subject, same magnification, same lighting, shot twice: once at **f/5.6** and
> once at **f/11**, each with **at least 2.5× the frame count** of a normal
> bracket for that subject (roughly 80–120 frames rather than 33). The subject
> does not matter as long as it has texture and does not move.

The frame count is the whole point: the reference has to out-resolve the thing
being measured, and section 1 is the measurement of how far the existing captures
fall short. Added to `docs/captures-needed.md`.

---

## 7. Unreconciled residual, disclosed

Section 4 accounts for M33's numbers exactly and section 3's factorial accounts for
most of the M33↔M35 gap, but **not all of it**: M35 script 02's baseline-subtracted
parabola reads 0.549 where script 04's reads 0.479 on M33's cell. The remaining
~0.07 is spread across three harness differences that compound — baseline defined
as min-of-dense vs 5th-percentile-of-decimated, all 1,048,576 pixels vs a 40,000
sample, and interior judged by the dense vs the decimated argmax.

**It is a harness difference, not an estimator difference** — the ordering and the
sign of the margin are identical in all twelve cells measured across scripts 03 and
04 — but it is not fully reconciled and is recorded rather than rounded away.
**When quoting a calibration number, quote M33's cell**, which is the one that
reproduces. Flagged to the M36 verifier.

## 8. Open

- Question 70 is **unanswered**, now for a documented capture reason.
- `119MSDCF`'s 7.38% boundary-peak fraction (against `112`'s 2.08% and
  `coffee-bean`'s near-zero) says the 33-frame bracket does not cover its subject's
  depth. Excluded here, but it is independent evidence that stack is unsuitable.
- The implied Gaussian widths (1.69 / 2.41 / 1.83 at ×2) are computed from the same
  contaminated deficits and should be re-derived once adequate captures exist.
