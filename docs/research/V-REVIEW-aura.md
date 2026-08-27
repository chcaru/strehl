# V-REVIEW-aura: independent re-measurement of the estimator-vs-pyramid halo

**VERDICT: CONFIRMED IN DIRECTION, NOT IN MAGNITUDE, AND NOT GENERAL.**

The claim under test, from the shipping binary's own `stack --help`: on
`flower-bud-alone-cpl`, camera-linear, one binary, one mask, *the estimator's
backdrop sits 4739 DN below its own far field across the 80-200 px aura zone;
the pyramid sits 166 DN below* -- a ratio of 28.5x.

**The exact sentence that is safe to say:**

> On `flower-bud-alone-cpl` the estimator does put a markedly stronger dark aura
> around the subject than the pyramid does, and the pyramid is the current
> default, so that specific complaint is addressed. The 28.5x multiplier is not
> a number to quote: it is specific to that subject and to one choice of mask
> and zone. On a second subject the two merges differ by **1.02x**, and on the
> original subject the ratio moves between **1.24x and 17.70x** as the mask and
> zone are varied, because the quantity it divides by passes through zero.

## 1. What reproduces

I rendered both merges from one pinned binary, `--linear-srgb`, same raster
3520x2344, and built the mask from the **mean of both arms** so it cannot favour
either. Photometric check first, because a self-referenced statistic is only the
right shape if you have confirmed you need it: median level ratio
estimator/pyramid is **0.9831**, a 1.7% difference. Small, and the
depression-below-own-far-field form absorbs it.

**Direction reproduces.** In all eight mask/zone configurations on
`flower-bud-alone-cpl` the estimator's aura depression exceeds the pyramid's.
That part of the claim is sound and I could not break it.

**Units reconcile.** The claim's *80-200 px* is full-resolution pixels;
`--linear-srgb` emits binned 3520x2344, so the matching zone is 40-100 binned px.
At a tight mask and that zone I measure pyramid **212.3 DN** and estimator
**3757.9 DN** against the claim's 166 and 4739 -- the same order, by an
independent mask.

## 2. What does not reproduce: the multiplier

| mask pctl | aura zone | pyramid depr DN | estimator depr DN | ratio |
|---|---|---|---|---|
| 20 | 40-100 | 212.3 | 3757.9 | **17.70x** |
| 20 | 80-200 | **-137.2** | 1307.3 | -9.53x |
| 30 | 40-100 | 150.4 | 1709.4 | 11.37x |
| 30 | 80-200 | 241.9 | 775.4 | 3.21x |
| 40 | 40-100 | 904.6 | 1883.5 | 2.08x |
| 40 | 80-200 | 872.2 | 1136.9 | 1.30x |
| 50 | 40-100 | 856.0 | 1482.9 | 1.73x |
| 50 | 80-200 | 883.4 | 1091.8 | 1.24x |

**The denominator crosses zero.** The pyramid's depression runs from +904.6 DN to
**-137.2 DN** across choices that are all defensible: at one setting the
pyramid's aura is *brighter* than its far field, not darker. A ratio whose
denominator passes through zero is not a stable statistic, and 28.5x is a
reading of that ratio near its pole. The absolute difference is better behaved in
sign -- the estimator is worse in every row -- but it still spans **208.4 to
3545.6 DN**, a factor of 17.

## 3. What kills the general form: a second subject

`lead-1-cpl`, identical treatment:

| mask pctl | aura zone | pyramid depr DN | estimator depr DN | ratio |
|---|---|---|---|---|
| 20 | 40-100 | 601.0 | 611.4 | 1.02x |
| 20 | 80-200 | 543.2 | 554.0 | 1.02x |
| 30 | 40-100 | 434.7 | 444.5 | 1.02x |
| 30 | 80-200 | 330.1 | 337.7 | 1.02x |
| 40 | 40-100 | 292.0 | 296.5 | 1.02x |
| 40 | 80-200 | 168.5 | 175.4 | 1.04x |
| 50 | 40-100 | 95.4 | 100.4 | 1.05x |
| 50 | 80-200 | 0.2 | 6.9 | 33.32x |

**1.02x, stable across seven of eight settings.** The two merges are
indistinguishable here. Note also what the depression *is* on this subject: about
600 DN in **both** arms. A feature both merges reproduce equally is inherited
from the optics and the subject, not manufactured by either -- the same logic
that acquitted nine subjects earlier.

The eighth row is the instability made visible: **33.32x on a denominator of
0.2 DN**. It is not a large effect; it is a small number in the wrong place. Any
report of this ratio that does not print its denominator is unreadable.

Between subjects, the estimator's excess over the pyramid is **208-3546 DN** on
`flower-bud-alone-cpl` and **4.5-10.8 DN** on `lead-1-cpl` -- two orders of
magnitude apart. The effect is strongly subject-dependent, which is exactly the
property that makes a single-subject multiplier unsafe to quote.

## 4. Limits

Two subjects is not a corpus. `lead-1-cpl` may not present the dark-subject-on-
bright-ground geometry the claim names, and I did not verify that it does; if it
does not, it bounds the claim's generality rather than refuting its mechanism.
Either way the multiplier remains a one-subject number.

I did not commission a planted aura. The denominator sweep in sections 2 and 3
does the work a plant would have done, and does it on real data: it shows the
statistic's reference term changing sign under defensible choices, which is a
stronger disqualification than a successful recovery would have been a licence.

## 5. Scripts

`experiments/V-REVIEW/vh2_aura.py` and `vh2_sweep.py`. Renders under
`C:\dev\strehl-out\V-REVIEW\halo2` from a binary pinned by copy before the run,
so a concurrent rebuild could not change arms mid-experiment.
