# M36 — Independent verification of M32, M33 and M34

**Status: INDEPENDENT VERIFICATION (M36). This document is itself NOT
INDEPENDENTLY VERIFIED.**

I am not the author of M32, M33 or M34. Every number below labelled MEASURED was
produced by code I wrote in `experiments/m36-verification/src/`, run against the
committed data, and **not** by re-running the author's scripts. Where I reused a
cached `.npy` I verified the cache against the ARW files first (V01). Where I
quote one of the author's numbers I say so explicitly.

**What I did check:** the 22 headline numbers listed in section 2; the derivation
of M34's analytic chance level; the tie-break hazard; the reliability-ceiling
protocol (including a synthetic-truth stack with a known answer); fact 281 under
six alternative channel definitions, a spatial block bootstrap, three shift
controls and two other stacks; the vertex algebra behind M34 section 5; the
M33/M34 ground-truth reconciliation to the last digit; and the provenance of
M32's sigma denominator.

**What I did NOT check** — mandatory section, see section 4: the ARW decode path
itself; anything about M18, M20, M27, M35 except where M32–M34 quote them; the
x4 and x6 decimation arms beyond their headline means; M34's C2 perplexity
against an independent entropy implementation; and generality of M33's log fit on
other stacks (the orchestrator is running that separately).

**One error of my own, disclosed:** my first pass at M32's null (`V09`) reported
`H/log n = 0.8275` at `n = 9` and I recorded it as a discrepancy. It was my bug —
I set the softmax temperature to `f.std(0).mean()`, whose expectation at `n = 9`
is 0.914 sigma, not 1. `V12` redoes it correctly and the author's value is right.
I mention this because it is exactly the class of error I am here to catch.

---

## 1. Verdict per milestone

| Milestone | Verdict | Reason in one sentence |
|---|---|---|
| **M32** | **CONFIRMED WITH CORRECTIONS** | Every conclusion survives, but the headline "142–991 sigma" is inflated about 1.7–1.9x by two compounding defects — `scipy.ndimage.sobel` applied to a 3-D cube silently smooths the focus response along the frame axis, and the roughness sigma estimator is biased 21–28% low on exactly that smoothed volume; on the focus measure the rest of the project uses, the correct figure is **84–512 sigma**, which changes nothing qualitative. |
| **M33** | **CONFIRMED WITH CORRECTIONS** | Every measured number reproduces to four decimal places from my own code, but the prose direction of the headline is inverted (48.7% is the fraction that **hits** its peak; 51.3% miss), the two-phase "replication" is complementary by construction for that statistic, and the ground-truth adequacy ratio is **3.10x**, not 3.87x, when computed with the milestone's own preferred estimator. |
| **M34** | **CONFIRMED WITH CORRECTIONS** | Union, Jaccards, ceilings and the 0.89x lift all reproduce exactly and fact 281's *number* survived every attack I could construct on coffee-bean, but "every pairwise overlap sits at chance" is false as a significance statement (z = −25.0 and +18.6 against the milestone's own shuffle null), fact 281's **stated mechanism is refuted by direct measurement**, its sign flips under three reasonable alternative definitions of C1, and C3's specificity does not survive off coffee-bean. |

---

## 2. Every headline number, independently reproduced

All commands run from the repo root with `$env:PYTHONIOENCODING='utf-8'`.
"MINE" is my value; "REPORTED" is the milestone's.

### 2.1 M34

| Quantity | REPORTED | MINE | Command | Match |
|---|---|---|---|---|
| Union of three worst-5% sets | 14.278% | **14.2783%** | `python experiments\m36-verification\src\V02-chance-tiebreak.py` | YES |
| Fraction of the 15.0% disjoint ceiling | 95.19% | **95.19%** | same | YES |
| Jaccard C1 vs C2 | 0.0346 | **0.0346127** | same | YES |
| Jaccard C1 vs C3 | 0.0136 | **0.0135810** | same | YES |
| Jaccard C2 vs C3 | 0.0267 | **0.0266708** | same | YES |
| Analytic chance Jaccard | 0.0256 | **0.0256410** analytic; **0.025624 +- 0.000503** by 200-pair Monte Carlo | same | YES |
| Reliability ceiling C1 / C2 / C3 | 0.7642 / 0.6948 / 0.7352 | **0.7630 / 0.6929 / 0.7332** | `python experiments\m36-verification\src\V03-ceiling.py` | YES (own seeds) |
| True mean sub-frame deficit | 2.876% | **2.8756%** | `python experiments\m36-verification\src\V05-fact281.py` | YES |
| Fraction with zero deficit | 48.92% | **48.9240%** | same | YES |
| C1 worst-5% lift (fact 281) | 0.89x | **0.8885x** | same | YES |
| C1 Spearman vs truth | −0.0726 | **−0.0768** | same | close, see D7 |
| C3 Spearman vs truth | +0.5560 | **+0.5569** | same | YES |
| C2 Spearman vs truth | +0.3349 | **+0.3334** | same | YES |
| Random-channel floor | +0.0014 | **+0.0012** | same | YES |

### 2.2 M33

| Quantity | REPORTED | MINE | Command | Match |
|---|---|---|---|---|
| Fraction at x2-even not sampling its peak | "48.7% miss" | **51.31% miss** (48.69% hit) | `python experiments\m36-verification\src\V07-m33.py` | **NUMBER YES, DIRECTION NO** (D4) |
| Mean deficit over all pixels, x2 | 2.753% | **2.7527%** | same | YES |
| Conditional median | 4.64% | **4.6406%** | same | YES |
| Conditional p90 | 10.74% | **10.7426%** | same | YES |
| Conditional p99 | 17.34% | **17.3433%** | same | YES |
| Synthetic parabola predicted deficit falls | 21x | **21.7x** (ratios 0.5017 / 0.0675 / 0.0029; truth rises **7.9x**) | `python experiments\m36-verification\src\V08-m33-estimators.py` | YES |
| Log-domain fit on synthetic Gaussian | 1.0000 | **1.0000** (err ~1e-17) | same | YES |
| Real x2 log+baseline calibration ratio | 0.710 | **0.7043** | same | YES |
| Real x2 log+baseline within-2x | 51.2% | **50.93%** | same | YES |
| Placebo: parabola on a true parabola / log fit | 1.000 / 3.02x | **1.0000 / 3.0150** | same | YES |
| Position: argmax null / parabola / log | 0.517 / 0.128 / — | **0.5138 / 0.1284 / 0.1175** | same | YES |
| Position gain over null | 4.03x | **4.003x**; log 8.4% better | same | YES |
| Dense grid's own deficit (adequacy) | 0.711% -> 3.87x | **0.8875% -> 3.10x** with log+baseline | same | **NO** (D5) |

### 2.3 M32

| Quantity | REPORTED | MINE | Command | Match |
|---|---|---|---|---|
| Arm S entropy, lowest -> highest texture bin | 0.6480 -> 0.6482, min 0.6085 | **0.6508 -> 0.6487, min 0.6072** on the volume M32 actually built | `python experiments\m36-verification\src\V13-arms.py` | YES |
| Arm S non-monotone | yes | **yes on both volumes** | same | YES |
| Arm S on the project's real focus measure | not reported | **0.5856 -> 0.5950, min 0.5388** | same | new (fact 290) |
| Arm N (calibrated) perplexity | 1.0000 | **1.001075** at the lowest-texture bin, 1.000000 elsewhere | same | YES (1.0000 is a rounding) |
| Peak over noise, MC sigma (fact 260) | 119 -> 728 | **115.5 -> 724.1** | same | YES |
| **Peak over sigma (fact 261 headline)** | **142–991** | **140.9 – 995.2** as the author computes it; **114.3 – 712.3** with the correct sigma on the same volume; **82.6 – 499.6** on the project's real focus measure | `python experiments\m36-verification\src\V11-sigma-audit.py` | **arithmetic YES, quantity NO** (D1, D2) |
| roughness sigma / Monte-Carlo sigma | 0.736–0.806, "MC conservative" | **0.721–0.794** on M32's volume; **1.061–1.128** on an unsmoothed volume | same | YES, interpretation backwards (D2) |
| No-information null, n = 53 -> 9 | 0.8879 -> 0.8503 | **0.887996 +- 0.000112 -> 0.850773 +- 0.000157** (5 seeds x 200k trials) | `python experiments\m36-verification\src\V12-null.py` | YES |
| Null perplexity / n | 0.641 -> 0.720 | **0.6410 -> 0.7204** | same | YES |

**The most important line in this table:** M32's headline sigma count is
arithmetically exactly what the author reports, and it is a count against the
wrong sigma of the wrong focus volume. Details in D1 and D2.

---

## 3. Defects found

### D1 — HIGH (M32). M32's focus measure is not the focus measure it says it is.

`docs/research/M32-posterior-confidence-measured.md:42` states: "Focus measure
throughout is M27's: box-mean of the Sobel magnitude, radius 2." All three
measurement scripts (`02-entropy.py:51`, `03-null.py:66`, `04-temperature.py:40`)
compute it as

    gx = sobel(cube, axis=2, mode="nearest")
    gy = sobel(cube, axis=1, mode="nearest")

on the whole `(53, 1024, 1024)` cube. `scipy.ndimage.sobel` applies the
`[-1, 0, 1]` derivative along `axis` and the `[1, 2, 1]` **smoothing along every
other axis** — which for a 3-D cube includes **axis 0, the frame axis**. M32's
focus response at frame `k` is therefore a `[1,2,1]`-weighted blend of frames
`k-1, k, k+1`, scaled 4x.

MEASURED (`V10-focus3d-check.py`): median ratio `focus3d / focus2d` = **3.587**
(not 4, because the frame blur lowers the peak); median relative deviation from
`4 * focus2d` = **10.4%**; from the explicit 3-frame blend = **11.0%**.

This is isolated to M32 — I grepped every `sobel(` call under
`experiments/*/src/` and M32 scripts 02/03/04 are the **only** three that pass a
cube. M27, M30, M33 (`01-build-dense.py:28`) and M34 (`01-channels.py:53`,
`03-controls.py:75`) all call it per 2-D frame.

**Effect on M32's conclusions: none qualitatively.** Arm S is blind and
non-monotone on both volumes (V13); arm N is a delta on both; the null does not
involve the volume at all. **Effect on M32's numbers: the headline sigma count is
inflated ~1.7x** — see D2 for the remaining factor.

### D2 — HIGH (M32). The 142–991 sigma is referenced to a sigma that is 21–28% too small, and the report says the error runs the other way.

Fact 261 says the two temperature estimates "agree to 1.24x, **the Monte Carlo
conservative as predicted**". MEASURED (`V11-sigma-audit.py`; 16 Monte-Carlo
re-realisations of the M4 noise model, 6000 pixels x 6 texture bins, medians):

| volume | rough_sigma / MC sigma | peak / MC sigma | peak / rough_sigma |
|---|---|---|---|
| M32's frame-smoothed volume | **0.721 – 0.794** | **114.3 – 712.3** | **140.9 – 995.2** |
| the project's per-frame volume | **1.061 – 1.128** | **82.6 – 499.6** | 76.8 – 453.8 |

The roughness estimator is essentially unbiased on an unsmoothed focus volume and
**biased low on M32's** — because the `[1,2,1]` frame smoothing correlates the
noise across `k`, which is precisely the assumption `rough_sigma` relies on when
it divides the robust second-difference sd by `sqrt(6)`. So the Monte Carlo is
not "conservative"; it is **right**, and the headline quotes the optimistic
estimate. The author's own `03-null.py` already contains the correct-sigma figure
(`peak_over_noise` 119.3 -> 728.0, which I reproduce as 115.5 -> 724.1) and fact
260 quotes it; fact 261 quotes the larger number from `04-temperature.py`.

**Honest restatement:** on the focus measure M18 will actually ship, the
through-focus peak stands **84–512 sigma** above its own curve. Fact 263 ("a 142
sigma peak is not signal-to-noise limited") is unaffected — 84 sigma is not
signal-to-noise limited either.

### D3 — MEDIUM (M34, fact 280). "Every pairwise overlap sits at chance" is false as a significance statement.

MEASURED (`V02-chance-tiebreak.py`, 100 repeats of the milestone's own
label-shuffle null): null mean **0.02567**, null **sd = 0.00048**. Against that:

| pair | observed | z |
|---|---|---|
| C1 vs C3 | 0.01357 | **−25.0** |
| C1 vs C2 | 0.03456 | **+18.6** |
| C2 vs C3 | 0.02667 | +2.1 |

The *ratios* 0.53x and 1.35x are correct and the qualitative reading ("the
channels are close to disjoint") is correct and if anything strengthened — C1 and
C3 are **significantly more disjoint than chance**, which is fact 281 showing up
in the overlap table. But the milestone reports a one-number null with no spread
and then calls 0.53x and 1.35x "at chance", and they are 25 and 19 sigma from it.

### D4 — MEDIUM (M33, fact 270). The headline direction is inverted.

`experiments/m33-subframe-offset/out/03-corrected.json` records
`arms.x2even.frac_peak_sampled_exactly = 0.4869095` and `n_missing = 20519` of
40000 = **51.31%**. MEASURED independently (`V07-m33.py`): **48.6910% hit,
51.3090% miss.** Fact 270 and M33 section 1 say "48.7% of pixels **miss** their
focus peak entirely". The correct sentence is "48.7% of pixels sample their focus
peak exactly; **51.3% miss it**."

Consequence beyond wording: fact 270 also claims "Replication across the two x2
phases agrees to 0.05%". The two phases' hit fractions are **0.4869095 and
0.5131283, which sum to 1.0000378** — complementary *by construction*, since the
parity of the dense argmax decides which phase samples it. That statistic cannot
replicate except at exactly 50%. The 0.05% figure is the *conditional median*
(4.6405 vs 4.5957), which is a fair comparison; the all-pixel means differ by
0.162 pp (2.7525 vs 2.5903), 5.9% relative. The replication claim must be scoped
to the conditional statistics.

### D5 — MEDIUM (M33, fact 270 footnote). The ground-truth adequacy ratio is 3.10x, not 3.87x.

The dense 105-frame grid's own residual deficit (0.711%) was estimated with the
**parabolic** peak-height fit — the estimator this very milestone disqualifies in
fact 271. MEASURED (`V07-m33.py`) with the milestone's own preferred estimator
(log domain + baseline subtraction), the dense grid's own deficit is **0.8875%**,
giving adequacy **2.876 / 0.8875 = 3.24x** like-for-like, or **3.10x** against the
2.753% figure fact 270 quotes. Applying the log fit's own measured 0.854
calibration at this spacing pushes it to roughly **2.7–2.8x**. The pre-registered
bar was 3x. This overturns nothing, but the honest statement is "adequate at
about 3x, possibly marginally below", not 3.87x.

### D6 — MEDIUM (M34, fact 281). The stated mechanism is refuted.

Fact 281's mechanism: "photon-starved pixels have **flat** through-focus curves,
so missing the peak costs them little". MEASURED (`V05b-fact281-mechanism.py`):

- Spearman(mean signal, true deficit) = **+0.0000**
- Spearman(peak − baseline, true deficit) = **+0.0147**
- both decile tables flat and non-monotone in true deficit.

Neither dimness nor curve flatness predicts true deficit at all. The number 0.89x
is real; the explanation attached to it is not.

**The real mechanism, MEASURED** (`V05c-acceptance-mechanism.py`): the acceptance
set size `|A|` is the driver. Spearman(`|A|`, true deficit) = **+0.198**. Pixels
with `|A| = 1` (91.94% of the crop) have lift **0.91x**; `|A| = 2` (6.82%) have
lift **2.10x**. C1 is a *decreasing* function of `|A|` because it averages sigma
over the accepted set, so C1's worst-5% is almost entirely `|A| = 1` pixels, whose
lift is 0.91x — which is the observed 0.889x. C1 is anti-informative because **it
is partly a proxy for a small acceptance set, and a small acceptance set means a
well-resolved peak**.

### D7 — MEDIUM (M34, fact 281). The sign flips under three reasonable alternative definitions of C1.

MEASURED (`V05-fact281.py`), same crop, same truth, same worst-5% statistic:

| definition of C1 | worst-5% lift | Spearman |
|---|---|---|
| as shipped (sigma averaged over the 1-sigma acceptance set) | **0.8885x** | −0.0768 |
| same, 2-sigma gate | 0.7624x | −0.1185 |
| same, 3-sigma gate | 0.6804x | −0.1464 |
| **sigma at the argmax frame only** | **1.1177x** | −0.0144 |
| **sigma of a fixed top-3 average** | **1.1251x** | −0.0146 |
| **inverse SNR of the mean image** | **1.1109x** | −0.0015 |

Spatial block bootstrap (64x64 blocks, 400 resamples): the shipped definition
gives lift 0.8885, 95% CI **[0.828, 0.945]**, P(lift >= 1) = **0**. The
argmax-frame and top-3 alternatives give P(lift < 1) = 0.003 and 0.007. Shift
controls (roll 128/256/512 px) return 1.021 / 1.014 / 1.041, as a null must. So
both signs are statistically solid; **which sign you get is a property of the
gate, not of "predicted sigma"**.

On other stacks (`V06-other-stacks.py`) the gated definition stays
anti-informative (119MSDCF 0.504x, 112MSDCF 0.669x) but the alternatives do not
agree in sign across stacks (119MSDCF 0.895 / 0.859; 112MSDCF 1.282 / 1.319).

**Does this change M34's conclusion? No — it strengthens it.** The argument "no
monotone scalar summary is faithful" needs C1's lift to be far from C3's 2.91x,
and it is under every definition. But fact 281 as worded pins a specific sign to
"predicted sigma", and that is not safe to build on. The safe form is: *the
predicted-sigma channel carries no useful information about sub-frame deficit and
its sign depends on the gate.*

### D8 — MEDIUM (M34, fact 282). C3's specificity does not survive off coffee-bean.

MEASURED (`V06-other-stacks.py`, full independent rebuild from ARW):

| stack | n | ISO | C3 Spearman vs truth | C3 worst-5% lift |
|---|---|---|---|---|
| coffee-bean | 105 | 50 | **+0.5569** | 2.914x |
| 119MSDCF | 33 | 50 | **+0.048** | 1.28x |
| 112MSDCF | 79 | 500 | **+0.053** | 1.37x |

Confounds I measured and did **not** remove (`V06b-stack-diagnostics.py`):
119MSDCF has 10.9% of pixels with argmax at a stack boundary and a much coarser
effective focus step; 112MSDCF has a median signal of only 179 DN. So this is not
proof that C3 is coffee-bean-specific — but fact 282's +0.5560 is currently a
one-stack number and neither other stack I could reach reproduces it.

Acceptance-set size, by contrast, is a consistent positive predictor on all three
(worst-5% lift **1.94x / 2.67x / 2.36x**).

### D9 — LOW (M34, fact 280). The reliability ceiling is a lower bound, but not for the stated reason, and only by <0.01.

Fact 280 argues the ceiling is "a conservative lower bound (both arms carry
sqrt(2)x the real noise)". That is one of **two** biases. The other runs upward:
both arms are built on the **same original noise realisation**, which they share,
inflating agreement.

MEASURED (`V04-ceiling-bias.py`) on a synthetic stack with a known noise-free
truth (real all-in-focus composite + real smoothed depth map + blur bank + M4
noise), so that a *true* retest reliability exists:

| | C1 | C2 | C3 |
|---|---|---|---|
| R_true at 1x noise (the quantity of interest) | 0.7420 | 0.7445 | 0.8150 |
| R_true at sqrt(2)x noise | 0.6884 | 0.6941 | 0.7514 |
| R under the author's protocol | 0.7346 | 0.7355 | 0.8113 |
| **net bias** | **−0.0074** | **−0.0090** | **−0.0037** |
| sharing gain / noise penalty | +0.0462 / −0.0536 | +0.0414 / −0.0504 | +0.0599 / −0.0636 |

The conclusion ("it is a lower bound") is **correct**; the margin is **an order of
magnitude smaller** than the stated argument implies, and it holds by
near-cancellation of two large opposing effects rather than by the one-sided
argument given. My own prior algebraic prediction that sharing would dominate and
flip the sign was **falsified** by this measurement.

Also MEASURED: the ceiling is a strong function of the arbitrary extra-noise knob
— C1 runs 0.9256 (x0.25) -> 0.8637 (x0.5) -> 0.7630 (x1.0) -> 0.6347 (x2.0).
"70–76% self-reproducible" is a statement about a choice as much as about the
channels. Controls: identical arms -> 1.0000 for all three; a scene-free cube
under the same protocol -> 0.0322 / 0.0337 / 0.0276 against a chance level of
0.0256.

### D10 — INFORMATIONAL (M34 section 5). The sign-error correction is right, and nothing downstream used the bad value.

VERIFIED (`V07-m33.py`). For samples at x = −1, 0, 1 with b = (ap−am)/2 and
c = (ap−2a0+am)/2, the vertex value a0 − b^2/(4c) is algebraically identical to
`a0 + 0.25*(ap−am)*xstar` with `xstar = −b/(2c)`. Checked against a brute-force
`np.polyfit` on 200k random triples: max error **6e-14**, and **2.7e-15** on the
real data. The sign-flipped form used in `01-channels.py` and M33 `02-*.py` lies
**below the sampled maximum in 100% of cases**, which is what the clamp hid. M34
`02-redundancy.py` uses the correct form.

Downstream: `01-channels.py` writes `C3.npy`; `02-redundancy.py` writes
`C3_fixed.npy`; scripts 02, 03 and 04 all load **`C3_fixed.npy`**. I grepped every
`np.load` in `experiments/m34-confidence-vector/src/`. **No downstream consumer of
the bad `C3.npy` exists.** `kmax.npy` is carried over from script 01 but is an
argmax computed before the vertex step and is unaffected — re-derived from the
cache and confirmed (`V04`, `kmax_cache_ok: true`).

### D11 — INFORMATIONAL (M34). The tie-break perturbation is provably inert.

The hazard raised was that `worst()` adds `rng.uniform(0, 1e-12) * ptp(v)` and
C1's `ptp` might make that non-negligible. MEASURED (`V02-chance-tiebreak.py`) at
each channel's own p95 threshold:

| channel | ptp | eps = 1e-12*ptp | float32 spacing at threshold | eps / spacing | non-tied pixels within eps |
|---|---|---|---|---|---|
| C1 | 0.01752 | 1.75e-14 | 9.31e-10 | **1.9e-5** | **0** |
| C2 | 38.046 | 3.80e-11 | 1.19e-7 | **3.2e-4** | **0** |
| C3 | 0.89699 | 8.97e-13 | 7.45e-9 | **1.2e-4** | **0** |

The union (14.27832%) and all three Jaccards are **bit-identical** across
eps in {1e-18, 1e-12} and with the tie-break removed entirely; at an absurd
eps = 1e-6 the union moves by 0.00003. **Hazard refuted.**

The same test **confirms** fact 284's "free second null": C4 is a binary flag with
99.947% of pixels tied at the threshold, and removing the tie-break moves its
Jaccards from 0.0251 / 0.0281 / 0.0260 (chance) to 0.0036 / 0.0181 / 0.0375 (not
chance). C4's overlaps really are 99% tie-break by construction.

### D12 — INFORMATIONAL (M33/M34). The ground-truth disagreement is fully accounted for — in the mean, and not at all in the fraction.

MEASURED (`V07-m33.py`), one definition changed at a time:

| definition | mean deficit | frac exactly zero |
|---|---|---|
| M33: 40k sample, no baseline subtraction | **2.75274%** | 48.6897% |
| + baseline subtraction | **2.87642%** | **48.6897%** |
| + all 1048576 pixels instead of the 40k sample | **2.87578%** | 48.9098% |
| M34's exact form (script 04) | **2.87559%** | 48.9240% |
| M34 reported | 2.876% | 48.92% |

**The mean gap is 100% baseline subtraction** (0.1237 pp of the 0.1231 pp gap) —
M34's explanation is quantitatively exact, to within the 0.0006 pp contributed by
the pixel population. **The fraction gap is 0% baseline subtraction** — baseline
subtraction changes `frac_exact` by *identically zero*, because it cannot move an
argmax. M34 section 6 attributes a 2.4 pp fraction gap to baseline subtraction;
that gap was an artifact of the D4 inversion (48.7 "miss" and 48.92 "exactly zero"
are the same quantity), and the real population difference is **0.23 pp**. Neither
milestone has a bug here; M34's explanation of the *mean* is exactly right and its
explanation of the *fraction* is wrong.

### D13 — INFORMATIONAL (M33). Undisclosed clamping in one placebo cell.

MEASURED (`V08-m33-estimators.py`): in the h = 2 synthetic placebo cell, **17.2%**
of samples fall outside the three-point support and are clamped. The placebo's
headline (parabola exact at 1.0000, log fit 3.0150x wrong) is unaffected in
direction, but the clamped fraction is not reported.

---

## 4. Claims I could NOT check (mandatory)

1. **The ARW decode path.** I verified the caches reproduce bit-exactly from
   `rawpy.raw_image_visible` with the stated crop, black level and sublattice
   (V01, plus a wrong-file control giving max|d| = 233). I did **not** verify that
   rawpy's visible-area origin, the RGGB phase, or the 512 black level are right —
   those are M4's, and I took them as given.
2. **M34's C2 (perplexity) against an independent entropy implementation.** I
   reproduced `C2.npy` bit-identically from my own re-implementation of the
   milestone's formula, which tests the transcription, not the formula. Fact 283's
   per-pixel perplexity distribution (76.5% within 1% of a delta, p99 = 4.74,
   max = 39.05) I did not recompute at all.
3. **Fact 284's 0.053% / 0.0145% C4 numbers.** I verified C4's overlaps are
   tie-break-dominated (D11) but did not recompute the flag rate or the marginal
   union contribution.
4. **The x4 and x6 decimation arms** beyond their headline means (9.74% / 19.60%),
   and fact 274's Gaussian-width ladder (1.68 / 2.04 / 2.45 dense frames). I
   reproduced the x2 implied sigma (1.6757) only.
5. **Fact 261's "16x SNR degradation" arm** — perplexity rising to 1.206, arm S
   moving 9% while arm N moves 22 orders of magnitude. Not recomputed. This arm
   inherits D1 and D2.
6. **Fact 264 (the M20/M32 reconciliation)** and anything about M20's Wiener
   estimator, its 31% loss or its 15.1% crossover figure. Out of scope.
7. **Whether the 119MSDCF / 112MSDCF C3 collapse (D8) is real or a
   sampling-density artifact.** I measured two confounds and removed neither.
8. **M33's log fit on other stacks.** Deliberately not attempted; the orchestrator
   is running it separately.
9. **Whether my synthetic stack in V04 is realistic enough** to license the
   ceiling-bias sign. Disclosed limitation: synthetic C3 mean 0.0125 vs real
   0.0243, and C2 degenerate fraction 0.853 vs real 0.765 — my synthetic stack is
   *better* sampled than reality, so the bias is measured in a slightly easier
   regime than the one that matters.
10. **Everything about M18, M27 and M35** except where M32–M34 quote them.
11. **Whether M32's frame-smoothed focus volume changes fact 261's "insensitive to
    the noise model being wrong by two orders of magnitude" claim.** I confirmed
    the temperature is model-free (fact 302) but did not re-run the two-orders
    sweep on the corrected volume.

---

## 5. New facts (290+)

| # | Fact | Why it matters | Provenance |
|---|---|---|---|
| 290 | **`scipy.ndimage.sobel` on an N-D cube smooths along every axis except the derivative axis** — so M32's focus response is `[1,2,1]`-blended across adjacent frames and scaled 4x, while M27/M33/M34 use the unsmoothed per-frame measure. Median `focus3d/focus2d` = 3.587; median deviation from a pure 4x scaling 10.4% | M32 is the only milestone affected (I grepped every `sobel(` call under `experiments/*/src/`), but three of its scripts are, and its report claims the opposite at line 42. Any future cube-wise filter call inherits this | M36 (MEASURED, `V10`) |
| 291 | **On the project's actual focus measure the through-focus peak stands 84–512 sigma above its own curve, not 142–991.** Two compounding causes: the frame smoothing of fact 290, and `rough_sigma` being biased **21–28% low** on a frame-smoothed volume (it is unbiased, 1.06–1.13x, on an unsmoothed one) | Fact 261's conclusion is untouched — 84 sigma is still a delta — but the number that "makes M32 and M20 cohere" is 1.7–1.9x smaller than reported, and the report's claim that the Monte Carlo estimate is "conservative" is backwards: the MC estimate is the correct one | M36 (MEASURED, `V11`) |
| 292 | **M34's pairwise overlaps are not at chance.** The milestone's own label-shuffle null has sd 0.00048 over 100 repeats; C1 vs C3 sits at **z = −25.0** and C1 vs C2 at **z = +18.6** | The channels are *more* disjoint than chance in the C1/C3 direction, which is fact 281 appearing in the overlap table. "At chance" understates M34's own result while being technically false | M36 (MEASURED, `V02`) |
| 293 | **48.7% of pixels HIT their focus peak at x2; 51.3% miss it.** The two x2 phases' hit fractions are 0.4869095 and 0.5131283 and sum to 1.0000 — complementary by construction, not an independent replication | Fact 270 states the direction backwards and cites a replication that cannot exist for that statistic. The conditional deficit statistics do replicate (4.6405 vs 4.5957) | M36 (MEASURED, `V07`) |
| 294 | **The dense 105-frame grid's own residual deficit is 0.8875%, not 0.711%**, when measured with the log+baseline fit M33 itself prefers; adequacy is **3.10x** (3.24x like-for-like), not 3.87x, and ~2.7–2.8x after the log fit's own 0.854 calibration | The 0.711% was produced by the parabolic height fit that fact 271 disqualifies. The pre-registered adequacy bar was 3x, so this sits on the edge rather than comfortably above it | M36 (MEASURED, `V07`) |
| 295 | **Fact 281's mechanism is wrong and its number is right.** Spearman(mean signal, true deficit) = **+0.0000**; Spearman(peak − baseline, true deficit) = **+0.0147**; both decile tables flat | The stated causal story ("photon-starved pixels have flat curves so missing the peak costs them little") is refuted by direct measurement, while the 0.89x it was invented to explain survives a block bootstrap, three shift controls and two other stacks | M36 (MEASURED, `V05b`) |
| 296 | **The acceptance-set size is itself a sub-frame-offset detector, and it is the real mechanism behind fact 281.** Spearman(size, true deficit) = +0.198; size 1 (91.94% of pixels) lift 0.91x, size 2 (6.82%) lift **2.10x**; worst-5%-by-size lift **1.94x** on coffee-bean, **2.67x** on 119MSDCF, **2.36x** on 112MSDCF | C1 decreases with acceptance-set size, so its worst-5% is nearly all size-1 pixels whose lift is 0.91x — which *is* the observed 0.889x. And the acceptance-set size is the only channel-like quantity in this study that generalises across all three stacks: **it is a candidate channel in its own right** | M36 (MEASURED, `V05c`, `V06`) |
| 297 | **C1's anti-informativeness is a property of the gate, not of "predicted sigma".** Worst-5% lift: gated 1-sigma **0.889x**, 2-sigma 0.762x, 3-sigma 0.680x; but sigma at the argmax frame alone **1.118x**, fixed top-3 **1.125x**, inverse SNR of the mean image **1.111x**. Block-bootstrap CIs [0.828, 0.945] and [1.035, 1.184] — both signs are solid | Fact 281 is safe as "C1 carries no useful information about sub-frame deficit"; it is **not** safe as "predicted sigma is anti-informative", because a reasonable reimplementation of the same channel flips the sign. M18's output contract should not rest on the sign | M36 (MEASURED, `V05`) |
| 298 | **C3's specificity does not reproduce off coffee-bean.** Spearman vs true deficit: **+0.5569** (coffee-bean, 105 frames, ISO 50) -> **+0.048** (119MSDCF, 33, ISO 50) -> **+0.053** (112MSDCF, 79, ISO 500); worst-5% lift 2.91x -> 1.28x -> 1.37x | Fact 282's +0.5560 is a one-stack number. Confounded with sampling density (119MSDCF has 10.9% boundary-argmax pixels) and signal level (112MSDCF median 179 DN), so this is a warning rather than a refutation — but the confound is exactly the kind that would also *cause* a real collapse | M36 (MEASURED, `V06`, `V06b`) |
| 299 | **M34's reliability protocol has two opposing biases that nearly cancel.** On a synthetic stack with known truth: R_true(1x) = 0.742 / 0.744 / 0.815, R under the author's protocol = 0.735 / 0.735 / 0.811 — **net bias −0.0074 / −0.0090 / −0.0037**, from a sharing gain of +0.041…+0.060 against a noise penalty of −0.050…−0.064 | The "conservative lower bound" conclusion is correct but for a reason the report does not give, and the margin is <0.01 rather than the ~0.05 the sqrt(2) argument implies. The ceiling is also a strong function of an arbitrary knob (C1: 0.926 at x0.25 -> 0.635 at x2) | M36 (MEASURED, `V04`, `V03`) |
| 300 | **The M33/M34 ground-truth gap decomposes exactly: the mean gap is 100% baseline subtraction, the fraction gap is 0%.** 2.75274% (no baseline) -> 2.87642% (baseline) -> 2.87578% (all pixels) -> 2.87559% (M34's form); `frac_exact` is 48.6897% with **and** without baseline subtraction | Baseline subtraction cannot move an argmax, so it cannot change the fraction. M34's explanation of the mean is exactly right and of the fraction is wrong; the apparent 2.4 pp fraction gap was manufactured by fact 293's inversion and is really 0.23 pp of pixel-population difference | M36 (MEASURED, `V07`) |
| 301 | **M34's tie-break perturbation is provably inert for the three real-valued channels and provably dominant for C4.** `1e-12 * ptp` is 1.9e-5 / 3.2e-4 / 1.2e-4 of the float32 spacing at each channel's p95 threshold, with **zero** non-tied pixels inside it; union and all Jaccards are bit-identical across eps in {1e-18, 1e-12} and with no tie-break. Removing it moves C4's Jaccards from 0.0251/0.0281/0.0260 to 0.0036/0.0181/0.0375 | Refutes the tie-break hazard for C1/C2/C3 and independently **confirms** fact 284's claim that C4's overlaps are 99% tie-break by construction | M36 (MEASURED, `V02`) |
| 302 | **M32's roughness temperature is confirmed independent of the noise model.** An analytic delta-method sigma_f (Sobel Jacobian propagated through the box filter, validated against finite differences to 1.4e-6 against typical values 7.8e-2) agrees with `rough_sigma` to **0.967–1.044x** across all six texture bins | The model-free temperature really is model-free, which is the load-bearing part of fact 261's robustness argument — even though the *magnitude* it is used to compute is wrong (fact 291) | M36 (MEASURED, `V09`) |

## 6. New discipline items (200+)

| # | Discipline |
|---|---|
| 200 | **Never quote an extreme-set overlap as "at chance" without the null's standard deviation.** A ratio of 0.53x to an analytic chance level sounds like agreement; it was 25 sigma from the milestone's own empirical null. Report the null's sd alongside its mean, always |
| 201 | **A reliability protocol built by adding noise to already-noisy data has two opposing biases, and neither may be assumed to dominate.** Extra noise pushes reliability down; the shared original noise realisation pushes it up. The only way to know the net is to build a stack whose truth you know and measure it. My own algebraic prediction of which dominates was wrong by measurement |
| 202 | **Never estimate your ground truth's adequacy with an estimator your own milestone disqualifies.** M33 measured the dense grid's residual deficit with the parabolic height fit it had just shown to be anti-correlated with truth, and thereby overstated its own safety margin by 22% |
| 203 | **Filters from `scipy.ndimage` are N-D filters. Calling one on a stacked cube silently filters along the stack axis.** `sobel(cube, axis=2)` smooths with `[1,2,1]` along frames. Either loop per frame or assert the cube result equals the per-frame computation. A one-line assertion in M32's build would have caught this |
| 204 | **Two decimation phases of the same grid are complementary, not independent.** Their agreement is a replication only for statistics not determined by the parity of the underlying argmax; for the "did I sample the peak" fraction it is arithmetically forced |
| 205 | **When a fact bundles a MEASURED number with a DERIVED mechanism, the mechanism needs its own falsification test.** Fact 281's number survived a block bootstrap, three shift controls, six channel redefinitions and two other stacks; its mechanism died to a single two-line Spearman. They were shipped as one fact under one label |
| 206 | **A confidence channel's sign can be an artifact of its gate.** Before shipping "channel X is anti-informative about Y", reimplement X two other reasonable ways. Three of six reasonable definitions of "predicted sigma" flip fact 281's sign |
| 207 | **A noise estimator that assumes independence along an axis is invalidated by any smoothing along that axis, including smoothing you did not intend.** `rough_sigma` divides the second-difference sd by sqrt(6) on the assumption of iid noise along k; the accidental frame smoothing made it read 21–28% low, and the report then interpreted the resulting disagreement with Monte Carlo in exactly the wrong direction |

## 7. New open questions (80+)

| # | Question |
|---|---|
| 80 | **Which definition of "predicted sigma" should M18 ship, given that the gated and ungated forms have opposite signs against sub-frame deficit?** The gated form carries acceptance-set information; the ungated form is what a user would expect from the name. They are different channels and should probably both exist, or the gated one should be renamed |
| 81 | **Should the acceptance-set size ship as a fourth real-valued channel?** It is the only quantity in this study with a consistent worst-5% lift across all three stacks (1.94x / 2.67x / 2.36x), and it is already computed as a by-product of C1 |
| 82 | **Does C3's specificity collapse on 119MSDCF and 112MSDCF because those stacks are coarsely sampled and dim, or because +0.5560 is a coffee-bean artifact?** Separating the two needs a decimated coffee-bean arm matched to 119MSDCF's effective focus step |
| 83 | **Should M32's headline sigma count be restated at 84–512, and does fact 264's reconciliation with M20 survive at the lower figure?** It should — 84 sigma is still overwhelming — but fact 264 quotes "10^2–10^3 sigma" and the honest range is now 10^2 at the low end and barely 5x10^2 at the high end |
| 84 | **Is the dense 105-frame grid adequate?** The pre-registered bar was 3x; the like-for-like measurement is 3.24x and the calibration-corrected one ~2.7–2.8x. If the ground truth is only ~3x better than the thing it judges, how much of the 2.876% "true deficit" is the ground truth's own error? |

---

## 8. What would change my verdicts

- **M32 -> CONFIRMED** if fact 261 is restated at 84–512 sigma on the per-frame
  focus measure, or the measurement is redone per-frame in a new script (rule 15:
  not by editing the existing ones).
- **M33 -> CONFIRMED** if fact 270's direction is corrected, its replication claim
  is scoped to the conditional statistics, and the adequacy ratio is restated at
  ~3.1x.
- **M34 -> CONFIRMED** if fact 280 carries the null's sd, fact 281 drops its
  mechanism and is rescoped to the gated channel, and fact 282 is marked
  one-stack.

None of the defects I found overturns a milestone's conclusion. All of them
change a number a reader would quote.

---

## 9. Scripts

All under `experiments/m36-verification/src/`, all written by me, none of them
modifying anything the milestones produced.

| script | what it establishes |
|---|---|
| `_channels.py` | my independent re-implementation of M34's `channels()` / `worst()` / `J()` |
| `V01-verify-caches.py` | the `.npy` caches are what their filenames claim (bit-exact rebuild from ARW; wrong-file control max\|d\| = 233) |
| `V02-chance-tiebreak.py` | analytic chance level, brute-force Monte Carlo, tie-break inertness, union, Jaccards, the shuffle null's sd |
| `V03-ceiling.py` | reliability ceiling with my own seeds, extra-noise sweep, identical-arm and scene-free controls |
| `V04-ceiling-bias.py` | synthetic-truth stack; measures the ceiling protocol's net bias directly |
| `V05-fact281.py` | fact 281 under six C1 definitions, block bootstrap, shift controls |
| `V05b-fact281-mechanism.py` | refutes fact 281's stated mechanism |
| `V05c-acceptance-mechanism.py` | measures the real mechanism (acceptance-set size) |
| `V06-other-stacks.py` | full rebuild of 119MSDCF and 112MSDCF from ARW; generality of C1 and C3 |
| `V06b-stack-diagnostics.py` | confound disclosure for V06 |
| `V07-m33.py` | vertex algebra, M33's x2 numbers, the 48.7% inversion, the M33/M34 reconciliation, adequacy with the log fit |
| `V08-m33-estimators.py` | parabola vs log fit, synthetic ladder, placebo, position arm |
| `V09-m32.py` | first M32 pass — **contains my own null bug, superseded by V12 for the null**; its roughness positive control and analytic delta-method sigma_f stand |
| `V10-focus3d-check.py` | proves the 3-D sobel frame-smoothing (fact 290) |
| `V11-sigma-audit.py` | the sigma audit behind facts 291 and D2 |
| `V12-null.py` | corrected no-information null, 5 seeds x 200k trials |
| `V13-arms.py` | arm S and arm N on both focus volumes |
