# M31 — Independent verification of M27, M28, M29, M30

> **Written by a different agent from the one that produced M27–M30.** I did not write the
> milestones, did not run the project before this task, and did not edit any script. Every
> number below came from either (a) my own from-scratch re-implementation of the stated
> method, or (b) reading a committed `out/*.json`. Which one is stated in every case.
> My scripts are in `experiments/m31-verification/src/` (`v01`–`v16`) and are re-runnable.
> Per rule 12 this document is itself unverified by anyone else.

## Method

I did not re-run the authors' scripts as my primary evidence. For each milestone I wrote an
independent implementation from the method description and the sensor facts, and compared.
Where the two agreed exactly I then attacked the *choice* of statistic rather than its
arithmetic: swapped the nuisance-parameter estimator, moved the reference, planted a known
answer and asked whether the estimator returned it, and rebuilt the null from the population
actually being tested.

Decode integrity was established first. All cached inputs are byte-exact decodes of the
originals:

| cache | check | result |
|---|---|---|
| `m28-robustness-scale/out/cache/*.npy` | 3 sampled frames vs my own `rawpy` decode | `max abs diff = 0` |
| `m30-hdr-cobracket` cubes | full cube vs my decode | `max abs diff = 0` |
| `m27` `cb_vol.npy` (from session-state, outside the repo) | my own 53x1500x1500 volume built from `D:\personal\macro\coffee-bean` | `max abs diff = 0` |
| `C:\dev\macro\test\coffee-bean` vs `D:\personal\macro\coffee-bean` | 105 files, names, bytes, and resulting focus volume | identical |

No file under `C:\dev\macro`, `D:\macro-dark-frames` or `D:\personal\macro` was written.

---

## 1. Verdict per milestone

| milestone | verdict | one-sentence reason |
|---|---|---|
| **M28** robustness mask | **CONFIRMED WITH CORRECTIONS** (architectural conclusion stands; the *mechanism* and two headline numbers are REFUTED) | Every published number reproduces to four digits, but the `1.13 -> 12.30` curve is roughly 3x inflated at `dk=16` by the gain estimator M28 §6 itself calls confounded, the residual is photometric rather than geometric, and "predicts to 9.9% with no free parameters" is 1.005/1.099/1.449 depending on tile scale and 1.505 without the 22 fitted per-frame gains. |
| **M30** HDR co-bracket | **CONFIRMED WITH CORRECTIONS**, except fact 242 which is **REFUTED** | The fixed-light neutrality identity is correct — I re-derived it before reading the script and confirmed it by Monte Carlo — but the clipping advantage (0.075% vs 0.177%) is an artefact of an unregularised argmax and converges to the random-frame null under the regularisation rule 4 requires. |
| **M27** coverage gap | **CONFIRMED** | Every number in §1, §3 and §4 reproduces exactly from a focus volume I built myself; the null is robust to null-block location; blindness holds under a stricter test than the author ran; and the fact-213 oracle threshold, which I expected to be load-bearing, is not. |
| **M29** static defects | **CONFIRMED WITH CORRECTIONS** | The `D = 0.999` refutation is right with a >12x margin and the `R ≈ 0.92·(g/blur)` mechanism is exactly right (I re-derived the constant as 0.9148 from the pipeline itself), but the displacement estimator is peak-locked and reports ~0.5x of truth, the disclosure of broken columns is incomplete, the detection limit is quoted from the arm the milestone declares defective, and the flat-field budget omits PRNU. |

**Nothing here overturns a shipped architectural decision.** M28's conclusion (reference
immediate neighbours, so the mask can run pre-alignment) survives, but for a different
reason than the one given, and one supporting number should be withdrawn. M30's fact 242
should be withdrawn or re-measured. M27 needs no change beyond two presentational notes.

---

## 2. M28 — robustness mask, measured

### 2.1 What reproduced exactly

Independently recomputed from the raws (`v01`, `v07`), not from the committed JSON:

| quantity | claimed | mine |
|---|---|---|
| pairwise median tile \|z\|, `dk` = 1 / 2 / 4 / 8 / 16 | 1.1305 / 1.7806 / 3.2365 / 5.6976 / 12.3005 | **identical to 4 dp** |
| radial outer/inner, whole-stack reference | 1.8182 | **1.8182** |
| radial outer/inner, adjacent-frame reference | 0.9798 | **0.9798** |
| tile median \|z\|, clean adjacent | 0.7416 | **0.7416** |
| ratio to half-normal 0.6745 | 1.0995 (9.9% excess) | **1.0995** |
| §3 sensitivity, FPR 1%, `s` = 1/2/4/8/16 | 15.2 / 31.1 / 53.8 / 77.3 / 96.2% | **identical**, 132 tiles |
| §3 placebo `s=0` | 0.0% | **0.0%** — and it is a genuine no-op (byte-identical copy), so it really is the null |
| §4 scale table, `d` = 4 / 8 / 16 | as published | **identical** |

Green sublattice, black level and CFA phase all confirmed independently:
`raw_colors_visible[0::2,1::2]` is uniformly colour index 1; the centred 3072 crop offsets
(808, 1978) are both even, so CFA phase is preserved.

### 2.2 Defect — the `1.13 -> 12.30` headline is mostly photometric, not geometric

`02-identity.py` normalises each frame by `gain = med/median(med)`, the **median-over-crop**
estimator that M28 §6 itself identifies as confounded by the focus sweep (4.28% p-p against
M24's 0.91%). Scripts 03/04/05 use the **mean** estimator, which §6 recommends. Same data,
same tiles, same `d=8`:

| gain estimator | dk=1 | 2 | 4 | 8 | 16 | last/first |
|---|---|---|---|---|---|---|
| median (as script 02 ships) | 1.131 | 1.781 | 3.236 | 5.698 | **12.301** | 10.88x |
| mean (§6's own recommendation) | 0.905 | 1.100 | 1.569 | 2.546 | **4.094** | 4.52x |
| none | 1.212 | 1.613 | 1.929 | 2.632 | **3.760** | 3.10x |

Removing a single least-squares **scalar** per pair drops `dk=16` from 12.301 to 3.288
(-73.3%). A scalar cannot express a displacement, so **at least 73% of the `dk=16` residual
is a brightness difference, not a warp.**

### 2.3 Defect — the "accumulating geometric warp" mechanism is refuted

A displacement residual must be proportional to `|grad|`. It is not (`v04`):

| \|grad\| quartile (median \|grad\|, DN/px) | 5.3 | 24.6 | 60.5 | 149.9 |
|---|---|---|---|---|
| median \|Δ\| at dk=16 (DN) | 48.4 | 47.6 | 29.7 | 80.2 |

Non-monotone, and the *lowest*-gradient quartile beats the third. Split by signal level
instead, the residual is a near-constant **3.5–4.5% fraction of signal** (13.6 / 23.7 / 58.1
/ 70.5 DN as S goes 346 -> 2027 DN) — the multiplicative signature. The fitted per-frame
scalar range is 4.00% p-p, the same size. The breathing prediction `|grad|·r/σ` predicts
`b7/b1 = 0.91` (flat or falling with radius); observed is 1.32. Radial signal level rises
5.1x (393 -> 2010 DN) while `|grad|` *falls* (18.1 -> 12.9).

### 2.4 Defect — "very nearly linear" is an artefact of the confounded estimator

log-log slope of median \|z\| against separation:

| gain estimator | slope |
|---|---|
| median (published) | **0.857** ("very nearly linear") |
| mean | **0.556** |
| none | **0.397** |

This matters because the milestone uses near-linearity to *exclude* defocus ("defocus would
saturate"). Under the estimator §6 recommends, the curve **is** sublinear and saturating —
the very signature used to rule defocus out. The exclusion argument does not survive its own
recommended normalisation.

### 2.5 Defect — the decisive `1.82 vs 0.98` comparison changes two variables at once

Script 02 (whole-stack reference) uses the median gain; script 04 (adjacent reference) uses
the mean gain. Holding the estimator fixed (`v03`, full 3x3 matrix):

| gain estimator | whole-stack ref | adjacent ref |
|---|---|---|
| median | 1.82 | 1.02 |
| mean | 1.71 | 0.98 |
| none | 1.69 | **1.27** |

**The qualitative conclusion survives** — an adjacent reference is radially flatter than a
whole-stack reference under all three estimators. "Perfectly flat, 0.98" holds for only one
of the three, and without any gain fit the adjacent-frame profile is 1.27, not flat.

### 2.6 Defect — "predicts to 9.9% with no free parameters" is three choices deep

The detector is a **second** difference, `z = |a_k − (a_{k−1}+a_{k+1})/2| / (σ√1.5)`, which
structurally cancels everything linear in frame index. Same data, same tile scale (`v05`):

| variant | tile median \|z\| | x 0.6745 |
|---|---|---|
| 2nd diff, mean gain (**published**) | 0.7416 | **1.0995** |
| 2nd diff, median gain | 0.7671 | 1.1373 |
| 2nd diff, **no gain fit** | 1.0152 | **1.5051** |
| 1st diff, mean gain | 0.8394 | 1.2445 |

And the same statistic swept over scale (mean gain, all pixels):

| tile `d` | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| ratio to 0.6745 | 1.0051 | 1.0437 | 1.0936 | **1.1630** | 1.2626 | 1.4486 |

1.099 is a point on a monotonically rising curve, not a scale-invariant validation. The 22
fitted per-frame gains **are** free parameters: without them the number is 1.505, i.e. a 51%
error, not 9.9%.

**The half-normal assumption itself is sound and is not doing the hidden work.** I pushed
simulated pure-Gaussian and Poisson+read data through the identical pipeline: median \|z\| =
0.6744 / 0.6745 at d=1 and 0.6739 / 0.6764 at d=8. So `0.6745` is the right expectation and
the *median* is robust to heavy tails — which means M28 §8's caveat that "heavy tails would
bias the ratio" is backwards for a median.

### 2.7 A genuine noise-model validation the milestone did not do

Robust (MAD) sigma of the per-pixel second difference, binned by signal level, restricted to
the flattest 30% of pixels by `|grad|`, 109MSDCF (`v05`/`v06`):

| | value |
|---|---|
| measured/model sigma ratio across bins | min 0.932, max 1.038, **median 0.966** |
| free-fit gain | `g = 0.3425` vs model 0.3663 (**−6.5%**) |
| free-fit intercept | 2.68 DN² vs model 2.37 DN² -> `RN_e = 4.78 e⁻` vs 4.20 |

The M4 model over-predicts sigma by about 3.4% at pixel scale. This is a stronger and more
honest validation than the tile-scale 1.099 figure, and it is independently corroborated by
M29 (see §5.6): the same −3% bias appears in a completely different statistic.

### 2.8 The FPR calibration is conservative, not honest — but the conclusions survive

Thresholds come from `others` (all *other* frames' tiles, 2508 values); the tested population
is frame `k0`'s 132 tiles. Those two nulls have different tails (`others` p99/p95 = 1.59 /
1.90 / 2.38 at d=4/8/16 vs the tested frame's own 1.28 / 1.37 / 1.63). Consequences:

- Placebo at nominal FPR **5%** reads 9.85 / 8.33 / 10.61% — about 2x inflated.
- Placebo at nominal 1% and 0.1% reads exactly 0.00% at all three scales, because the
  threshold sits far out in a heavier-tailed distribution. So "@FPR 1%" is really an unknown,
  ultra-conservative operating point: 0/132 gives a 95% CI of [0, 2.8%].
- Recalibrating on the tested frame's own null gives detection at a **true** 1% FPR of
  d=4: 18.2/35.6/59.1/84.8/98.5; d=8: 16.7/34.8/56.1/81.1/100.0; d=16: 14.4/28.0/51.5/69.7/92.4.
  Close to published. **The published sensitivities are, if anything, slightly pessimistic.**

Threshold-free AUC (`v07`) at s=1: 0.818 / 0.789 / 0.765 for d=4/8/16; at s=4: 0.978 / 0.969
/ 0.958. Monotone, small decline. **"Tile scale is not a sensitivity knob" is confirmed and
is not a threshold artefact** — it holds under a threshold-free statistic too. The published
spread is 14–41% across scales at fixed `s`, not "within 10%"; fact 223's "near-flat" is fair,
the doc's "flat within 10%" is not.

### 2.9 Undisclosed

The second-difference detector will flag frame *k* when the outlier is at *k±1*. Nothing in
M28 measures or bounds this mislocalisation, and the mask is per-frame.

---

## 3. M30 — HDR co-bracket, measured

### 3.1 Fact 240 (fixed-light neutrality) — CONFIRMED, re-derived before reading the script

My derivation, written down before opening `02-fixed-light.py`. Base frame collects `L`
electrons in one time unit; a +2 EV frame collects `4L` in four time units. With `V = gS + R²`
in DN² and `R = RN_e·g`:

- **Base arm.** `5m` frames at cost `5m` time units. Per-frame variance `V_base = gL + R²`;
  mean of `5m` -> `(gL + R²)/(5m)`.
- **HDR arm.** `m` base + `m` at +2 EV, cost `m·1 + m·4 = 5m` — the same. Scaling the long
  frame back to base exposure divides its variance by 16: `V_p2 = gL/4 + R²/16` per frame.
- Inverse-variance combination gives precision `m/(gL+R²) + m/(gL/4 + R²/16)`, and

  `precision_HDR − precision_base = m·12R² / [(4gL+R²)(gL+R²)] > 0` for `R > 0`.

- Variance ratio `base/HDR = (1/5)·[1 + 16(1+x)/(4+x)]` with `x = R²/(gL)`. At `x = 0` this is
  **exactly 1** — neutral. For small `x`, `≈ 1 + 0.6x`.

So HDR wins by `≈ 0.6·RN_e²·g/S` in **variance** and half that in sd, and is exactly neutral
in the shot-noise limit. **The claim is correct.** Monte Carlo through Poisson + Gaussian read,
N = 400,000 (`v08`):

| L, ISO | simulated sd ratio | my closed form |
|---|---|---|
| 2000 DN, 160 | 1.00394 | 1.00097 |
| 300 DN, 500 | 1.00375 | 1.00247 |
| 50 DN, 50 | 1.01113 | 1.01192 |
| 10 DN, 160 | 1.15660 | 1.15489 |

The identity holds and breaks down at low signal exactly where the algebra says it should.

**Correction 3a.** `02-fixed-light.py` computes `ratio = np.sqrt(var_all / var_hdr)`. That is a
**standard-deviation** ratio. Fact 240 and the doc call it variance. The effect in variance is
double: **0.082% / 0.942% / 0.384%**, not 0.041% / 0.470% / 0.192%. Direction unchanged.

**Correction 3b.** Script 02 performs no simulation. It evaluates the *same closed form* twice
at the measured `S` of `cube[n//2]` — one frame, the middle one. The only empirical content is
the distribution of `S`. Describing it as a measurement overstates it; it is an evaluation.

**Correction 3c.** Pixels that clip at +2 EV are not excluded from the ratio, and script 01
itself reports `new_clip_at_p2 = 7.05%` for coffee-bean at the best-focus frame (script 02
reports 1.89% at the middle frame; the doc quotes only 1.89%).

**Correction 3d (scope).** The neutrality result assumes +2 EV bought with **shutter**. On this
dual-gain sensor +2 EV bought with **ISO** is *not* neutral, because `RN_e` drops 4.20 -> 1.47
across ISO 400. The doc states the dual-gain fact elsewhere but never connects it to the scope
of the neutrality claim.

### 3.2 Fact 241 (nothing is read-noise limited) — implementation defect, conclusion survives

`01-dynamic-range.py` contains

```python
read_limited=float((S < rn_e(iso) ** 2).mean())
```

i.e. it measures `S < RN_e²`, **not** the documented `S < RN_e²·g`:

| stack | documented `RN²·g` | implemented `RN²` | ratio |
|---|---|---|---|
| coffee-bean (ISO 50) | 2.019 DN | 17.640 DN | 8.74x |
| 112MSDCF (ISO 500) | 2.474 DN | 2.161 DN | **0.87x** |
| 109MSDCF (ISO 160) | 6.462 DN | 17.640 DN | 2.73x |

For 112MSDCF the implemented threshold is *smaller* than documented, so the published 0.00%
did not prove the documented claim for that stack. I checked the documented boundary directly
(`v08`): min `S` in the cropped cube = 302 / 19 / 44 DN; min over the **full green plane**
(sampled frames) = 289 / **4.0** / 39 DN; fraction below the documented boundary =
**0.000000% everywhere**. **The conclusion holds.**

Two caveats on how much it is worth:

- The margin on 112MSDCF is only **1.6x**. At its darkest pixel read noise is 12.7% of the
  variance (sigma 6.2% above shot-only). The measured neutrality residual of 0.47% *is* read
  noise. "Not one pixel in three stacks is read-noise limited" is true only at the crossover
  criterion, which is a much weaker bar than "read noise is irrelevant".
- **The boundary definition is right.** `sigma² = gS + (RN_e·g)²`; read noise equals shot noise
  when `gS = RN_e²g²`, i.e. `S = RN_e²·g`. Confirmed algebraically. The doc is right and the
  script is wrong.
- Scope: the cube is a centred 1500x1500 crop of the green plane, i.e. 3000x3000 of 4688x7028
  sensor pixels. The darkest parts of the frame are not necessarily inside it — though I
  checked the full plane on sampled frames and it makes no difference.

### 3.3 Fact 242 (clipping at gathered frames) — **REFUTED**

Reproduced from my own decode: `gathered = 0.0754%`, `clip_global = 0.1769%`. Two things:

1. `clip_global` is the mean over the whole cube, i.e. the **mean per-frame clipped fraction**,
   which *is* the uniform-random-frame null (I measured that null at 0.1710%). The **union**
   over frames is 1.1201%. So the "2.3x" is best-frame vs random-frame, which is the right
   comparison, but it is not "whole-stack" in any other sense.
2. The best-frame index comes from an **unregularised argmax** over a Sobel-magnitude focus
   volume. Rule 4 forbids exactly this for output. Sweeping the regularisation (`v09`,
   coffee-bean, 53 frames):

| best-frame rule | clip @ gathered | clip \| clip-prone px | index speckle |
|---|---|---|---|
| raw argmax (**as published**) | **0.0754%** | 6.73% | 15.39% |
| focus box-smoothed R=7 | 0.0934% | 8.34% | 5.73% |
| **R=15 (31x31, the shipped scale)** | **0.1293%** | 11.55% | 3.02% |
| R=31 | 0.1584% | 14.15% | 2.04% |
| R=61 | 0.1782% | 15.91% | 1.38% |
| median-filtered argmax 9x9 / 25x25 | 0.1097% / 0.1089% | 9.79% / 9.72% | 5.36% / 2.91% |
| **uniform random frame (null)** | **0.1710%** | 15.79% | — |

The claimed 2.3x advantage falls to **~1.4x** at the regularisation scale the project actually
ships (M13/M14's 27x27 window; M15's width-17 regulariser) and to **1.0x — none** under heavier
smoothing. The mechanism is confirmed and is the problem: median focus value at clip-prone
pixels is **262.26 in clipped frames vs 311.11 in unclipped frames** — the argmax *flees* the
clipped frame because clipping flattens the local gradient. That is a selection effect on the
argmax, not a property of focus.

There is partial support for the stated mechanism independent of that: at clip-prone pixels the
best-frame index is median 8, IQR 1–15, against median 15, IQR 12–18 over all pixels. But it
cannot account for the effect once the index is regularised.

**Consequence:** fact 242's number is not what the shipped pipeline would see, and the R19
advisory trigger built on it would read about 2x higher in practice.

### 3.4 Script 01's disclosure — complete in structure, incomplete in one number

The void headline is the `adv_med ≈ 1.415` (`= √2`) comparison. The numbers still consumed
downstream (`clip_best`, `clip_global`, `frac_snr10`, `read_limited`) are read from
`01-dynamic-range.json` by script 02 and are computed independently of the broken arm. So the
disclosure is **structurally complete** — with one exception: `read_limited` is itself computed
with the wrong threshold formula (§3.2). That number survived the disclosure because the
disclosure was about the wrong thing.

---

## 4. M27 — coverage gap, measured

I built my own 53 x 1500 x 1500 focus volume from `D:\personal\macro\coffee-bean`
(`v10`, output at `experiments/m31-verification/out/cb_vol_mine.npy`). It matches the volume
the committed scripts read (from a session-state path *outside the repo*) with
**`max|diff| = 0`**. Everything below is computed from mine.

### 4.1 Everything reproduced exactly

| §1, gap width | 1 | 2 | 4 | 6 | 8 | 12 |
|---|---|---|---|---|---|---|
| curvature ratio (claimed = mine) | 1.879 | 2.463 | 2.672 | 2.805 | 2.757 | 2.408 |
| null | 1.427 | 1.404 | 1.416 | 1.412 | 1.426 | 1.421 |
| **excess** | +0.452 | +1.059 | +1.256 | +1.393 | +1.331 | +0.987 |
| \|δ\| excess | −0.164 | −0.484 | −0.361 | −0.301 | −0.234 | −0.102 |
| positive-band n | 63,942 | 143,672 | 376,467 | 584,778 | 776,356 | 859,400 |

Control band 6,937 px; reliable 1,124,998 px. All identical.

| §3, decimation | x1 | x2 | x3 | x4 | x6 |
|---|---|---|---|---|---|
| curv | 0.5607 | 1.1284 | 1.3908 | 1.5350 | 1.6679 |
| \|δ\| | 0.2005 | 0.1163 | 0.0773 | 0.0522 | 0.0371 |
| `nwide` (own-min) | 3 | 2 | 1 | 1 | 1 |
| `nwide` (full-stack min) | 3 | 2 | 1 | 1 | 1 |
| min/full | 1.0000 | — | — | — | 1.1954 |

| §4, frames | 53 | 27 | 18 | 14 | 9 |
|---|---|---|---|---|---|
| fraction resolved by <=1 sample | 0.01% | 37.46% | 59.91% | 69.06% | 75.76% |

All identical to the published values.

### 4.2 The null is robust

Moving the null block to indices 0, 4, 44, or a random non-overlapping set gives 1.375–1.428
for every gap width where the null block does not touch the positive band (`v11`). My own
null@4 readings of 1.463 (gap 8) and 2.069 (gap 12) are **invalid** — those blocks abut or
overlap the positive band `[12, 12+gw)`; I record them so nobody re-derives them and thinks
the null moved.

### 4.3 Blindness — confirmed by a stricter test than the author ran

The milestone's grouping into "positive" and "control" pixels is defined by the **full-stack**
argmax, which is an oracle label, and the doc does not flag it. I ran a genuinely blind version
(`v11`): bin pixels by the **reduced-stack** argmax, take the median `curv` per bin. The gap
lights up cleanly — background ≈ 0.55, gap bins 11–12 read **0.86** (1-frame gap) and **1.11**
(4-frame gap), and the argmax bin is exactly the gap location in both cases. **"Blindly
detectable" is true**, by a test the author did not run.

### 4.4 Correction — `nwide` is floored at 1 by construction

`f_k >= f_min + 0.5(f_k − f_min)` is satisfied at the peak for every stack, so `nwide >= 1`
always. Measured minimum = 1 and `frac(nwide == 0) = 0.000%` at every decimation, out to step 13
(5 frames). **Three of the five entries in the headline `3/2/1/1/1` column are pinned at the
statistic's floor** and carry no information about how much worse the sampling became. The mean
does keep falling (3.445 / 1.799 / 1.472 / 1.361 / 1.272) and the <=1 fraction keeps rising, so
§4's criterion still discriminates — but `3/2/1/1/1` should not be read as a measurement of
degradation past x3.

### 4.5 Correction checked and **cleared** — fact 213's threshold is not an oracle in practice

Fact 213's "deployable criterion" uses the **full-stack** minimum as the half-height reference,
which does not exist on a genuinely coarse bracket. I expected this to be load-bearing. It is not
(`v12`). Recomputing with the deployable own-stack minimum:

| frames | 53 | 27 | 18 | 14 | 9 |
|---|---|---|---|---|---|
| published (full-stack min) | 0.01% | 37.46% | 59.91% | 69.06% | 75.76% |
| **deployable (own min)** | **0.01%** | **37.56%** | **60.07%** | **69.25%** | **76.22%** |

Essentially identical. The oracle does **not** inflate the result. (Over *all* pixels rather
than the oracle-`reliable` half: 0.02 / 29.80 / 49.86 / 60.32 / 67.69%, so the reliability
filter raises the numbers by about 8 points — that part *is* oracle-conditioned and §6
discloses it.)

### 4.6 Discipline 120's generalisation — sound in conclusion, but built on 2 of its 3 instances

Discipline 120 claims a self-normalised shape statistic measures goodness of fit and never
presence of evidence, from three instances. Taking them one at a time:

- **Fact 73** (monotone untextured edge, `mean|∇|` reads high). `mean|∇|` is an **absolute
  magnitude**. It is not self-normalised and it is not a shape statistic. This instance does not
  belong to the class the discipline names. **Category error.**
- **Fact 203** (clipped pixel, contrast = 1.0000). Mechanism: **denominator degeneracy** —
  85.9% of those pixels have `f_min` exactly 0.
- **Fact 211** (absent best frame, `curv` up and `|δ| -> 0`). Mechanism: **sampling geometry** —
  the surviving frames flank the true peak at near-equal distance, so the sampled parabola reads
  symmetric and sharp. The *numerator* moves; the denominator is fine. The evidence is present in
  the scene, it is simply unsampled.

**So 211 is genuinely a third mechanism** — degenerate stimulus versus unsampled evidence are
different failures — and the question posed to me ("is it the same one twice?") answers *no*.
But the generalisation as worded rests on only **two** of its three instances actually belonging
to the named class, and M27 supplies **one** instance, not two, even though two metrics move on it.

Empirically the word "never" is too strong. On the full stack, median `curv` reads **0.5607** on
information-rich (`reliable`) pixels versus **0.4653** on the dimmest 10% of peaks and **0.4415**
on the dimmest 2%. `curv` is *lower* where evidence is scarcer, so it is not independent of
presence of evidence; its failure mode is confined to the specific degenerate cases cited.
**"Cannot be trusted as confidence" is right. "Never measures presence of evidence" is not what
was measured.**

### 4.7 Reproducibility gap

`00-build-volume.py`, `03`, `04` and `05` read `cb_vol.npy` from
`C:\Users\chris\.copilot\session-state\7a7e4522-.../files/`, a path outside the repository, and
no `out/*.json` is committed for M27. I could only verify M27 because I rebuilt the volume from
the raws and it happened to match bit-for-bit. Had the corpus moved, M27 would have been
**COULD NOT VERIFY**.

---

## 5. M29 — static defects (dust)

### 5.1 Reproduced exactly

Independently recomputed from the raws (`v14`, `v15`, `v16`):

| quantity | claimed | mine |
|---|---|---|
| sep-1 displacement, 109MSDCF, r = 0.15/0.35/0.55/0.75 | 0.146 / 0.183 / 0.187 / 0.217 px | **identical** |
| sep-1 displacement, coffee-bean | 0.117 / 0.107 / 0.123 / 0.075 px | **identical** |
| map rms vs n (109MSDCF), n = 1/2/4/8/16 | 0.14412 / 0.14545 / 0.14841 / 0.15343 / 0.15447 | **identical to 5 dp** |
| pair-difference rms, n = 2/4/8/16 | 0.01609 / 0.01519 / 0.02200 / 0.02951 | **identical** |
| Q10 exponent | +0.025 | **+0.0250** |
| Q11 pair exponent | +0.292 | **+0.2918** |
| flat budget: ISO100/8000 per-frame, n=20, n=64, 5% dust | 0.535% / 0.120% / 0.067% / 42σ | **identical** |
| §2 response table (σ=3/6/12 at 1/4/16%) | 0.342 / 0.324 / 0.254 (etc.) | **identical to 3 dp** |
| script 04 R vs g/blur, 18 (stack, location) pairs | `R ≈ 0.92·(g/blur)` | **R/(g/blur) = 0.916–0.936, median 0.919** |
| raw-conjunction Q9 excess at p0.001 | −0.0001 | **−0.0001** |
| standardised Q9 excess at p0.001 | +0.0006 | **+0.0006** |
| §3 sweep, 4/16/32/50% at three locations | as published | **identical** |

The doc's cross-check "0.274 × 0.50 × 0.8 = 0.11, exactly the measured −0.107 shift" is
**correct**: the sweep starts at 1%, so the right arithmetic is 0.274 × 0.49 × 0.8 = **0.1074**
against a measured −0.5521 − (−0.4448) = **−0.1073**. The 0.8 is `36/(36+9)`, the σ=3 smoothing
loss on a σ=6 shadow. Verified.

### 5.2 Fact 231 (`R ≈ 0.92·g/blur`) — CONFIRMED, and I can state it exactly

The doc says the algebra predicts **0.885** and then adopts **0.92** empirically, leaving a 4%
gap unremarked — in the milestone whose own §7 lesson #5 is "adopting an empirical constant that
disagreed with my own algebra". I resolved it. Running the exact pipeline on a **synthetic flat**
(`g ≡ 3000`, so `g/blur(g) ≡ 1` identically, no scene at all) gives the pure-algebra response:

| plant σ_p | `b = σ_p²/(σ_p²+576)` | doc's linearised `(1−b)²` | **exact numeric** |
|---|---|---|---|
| 3 | 0.0154 | 0.9695 | **0.9776** |
| **6** | 0.0588 | **0.8858** | **0.9148** |
| 12 | 0.2000 | 0.6400 | **0.7168** |

**0.885 is a first-order linearisation error; the exact value is 0.9148.** The empirical 0.92
agrees with the exact algebra to **0.6%**. There is no residual disagreement, and the
milestone's lesson is *stronger* than stated, not weaker.

Dividing script 03's real-data responses by the exact per-σ algebra at the *same* location:

| σ_p | 3 | 6 | 12 |
|---|---|---|---|
| measured R / exact algebra | 0.3499 | 0.3542 | 0.3557 |

Constant to **1.7%** — and I measured `g/blur24(g)` at that pixel on frame 0 as **0.3478**. So
the law is exactly

`R(σ_p, x) = R_flat(σ_p) · (g/blur24(g))(x)` with `R_flat(6) = 0.9148`,

with **no free constant at all**. This also explains the two scripts' different numbers: at
(900,1200) frame 0, `g/blur` = 0.3478 (script 03 -> R = 0.324); the 20-frame mean is
**0.2924**, matching `04-limit.json` exactly (script 04 -> R = 0.2737). The doc's account of
its own error is accurate.

**Correction 5a.** `R_flat` is strongly σ_p-dependent (0.978 / 0.915 / 0.717 at σ_p = 3/6/12).
Fact 231's "0.92" is the value for a σ=6 plant only. Real dust spans 10–40 sensor px, i.e.
σ_p ≈ 2–10 green px, over which `R_flat` varies **0.98 -> 0.79**. Fact 231 should carry the
plant radius.

### 5.3 **Defect — the displacement estimator is peak-locked; the "clean" column is not clean**

`06-dilution.py`'s `shift()` is phase correlation with a parabolic fit around the integer peak.
Below ~0.5 px the peak sits at lag 0 and the parabola is fitted to the DC lobe. I planted a
**known** Fourier subpixel shift into real frame-0 tiles and ran the identical estimator (`v13`):

| true shift (px) | 0.05 | 0.10 | 0.20 | 0.30 | 0.50 | 0.80 | 1.00 | 2.00 |
|---|---|---|---|---|---|---|---|---|
| recovered (109MSDCF, median of 16 tiles) | 0.0251 | 0.0510 | 0.1086 | 0.1827 | 0.4990 | 0.8913 | 1.0000 | 2.0000 |
| **recovered / true** | **0.50** | **0.51** | **0.54** | **0.61** | 1.00 | 1.11 | 1.00 | 1.00 |

**The estimator returns about half of the truth for every shift below 0.3 px** — exactly the
regime the sep-1 column lives in. An independent gradient (Lucas–Kanade) estimator on the same
real adjacent pairs gives 0.246–0.464 px (109MSDCF) and 0.203–0.530 px (coffee-bean), i.e.
**2–5x the phase-correlation values**. De-biasing both estimators against the same plant control,
the true adjacent-frame displacement is roughly **0.15–0.45 green px**, not 0.07–0.22.

The disclosure says "The Q13 result depends on the `sep 1` column alone, **which is clean**".
That sentence is **false**. Fact 230's "0.07–0.22 green px" is low by about 2x.

**The conclusion is unaffected and I want to be plain about that.** `D < 0.7` at `n = 3` requires
a per-step displacement of **5.47 green px** (σ_d = 5):

| d (green px) | 0.22 | 0.45 | 1.0 | 2.0 | 3.0 | 5.0 | **5.47** |
|---|---|---|---|---|---|---|---|
| D, n=3, σ_d=5 | 0.9994 | 0.9974 | 0.9868 | 0.9487 | 0.8902 | 0.7377 | **0.6998** |

The refutation has a margin of **>12x** even against my corrected displacements. **Fact 230's
verdict stands; its supporting number should be restated as "sub-pixel, ~0.15–0.45 green px,
measured with an estimator biased ~2x low".**

### 5.4 **Defect — the disclosure of broken columns is incomplete: `sep 4` is broken too**

The disclosure names `sep 8` and `sep 16`. From `06-dilution.json`:

| stack, radius | sep 1 | sep 2 | **sep 4** | sep 8 | sep 16 |
|---|---|---|---|---|---|
| coffee-bean r=0.15 | 0.117 | 0.203 | **3.381** | 0.103 | 0.056 |
| coffee-bean r=0.35 | 0.107 | 0.135 | **2.653** | 0.081 | 0.105 |
| 109MSDCF r=0.15 | 0.146 | 0.289 | **1.932** | 2.561 | 3.307 |

A displacement cannot be 3.381 px at sep 4 and 0.103 px at sep 8 — a 33x non-monotonicity. The
`n=5 span4` column of the §5 dilution table (`D` = 0.68–1.00 at σ_d = 5) is computed from
`np.interp(4, SEPS, ...)`, i.e. **directly from these numbers**, and is printed in the table with
no caveat. The error is in the conservative direction (a spurious 3.4 px overstates dilution, so
it makes the free-lunch claim look *better* than it is), so nothing downstream breaks — but the
disclosure as written is not sufficient.

### 5.5 **Defect — pre-registered Q12 is never reported, and it fails**

Q12: "displacement grows with radius from the optical centre and with frame separation." The
script's stated model is that breathing is a **scale** change, so `d ∝ r`. Measured (`v16`):

| stack | d(r=0.75)/d(r=0.15) | pure-scale prediction |
|---|---|---|
| 109MSDCF | **1.49** | 4.99 |
| coffee-bean | **0.64** | 4.99 |

Fitting `d = a + b·r` gives an intercept of **0.134 px** (109MSDCF) and **0.130 px**
(coffee-bean) with a *negative* slope on the latter. So the adjacent-frame motion is dominated
by a radius-independent **translation**, not by breathing. Q12 fails and the write-up does not
mention it. This does not affect `D` (a translation displaces dust just as well as a scale
change does), but it contradicts the script's own stated model and the doc's third pre-registered
doubt ("any dilution is therefore radius dependent, and worst exactly where people put the
subject"), which is now unsupported.

Note the Lucas–Kanade estimator *does* show a radial gradient on coffee-bean (0.179 -> 0.530 px
over the same radii), so the radial flatness in the published table is probably itself an
artefact of the peak-locked estimator. Either way Q12 as stated is not established.

### 5.6 **Defect — fact 233's "against −0.5 for shot noise" is not the right alternative**

The Q10 discriminator is stated as "flat means deterministic, `1/√n` means stochastic". I asked
what exponent the *shot-noise* hypothesis actually predicts for this measurement (`v15`):

| | value |
|---|---|
| median green signal, 109MSDCF | 1646 DN |
| M4-model photon term in a 1-frame map | **2.343%** |
| measured (`√2 ×` the n=2 adjacent pair-difference) | **2.275%** |
| measured n=1 map rms | **14.412%** |
| rms(16) under **pure shot noise** | 14.23% |
| -> **exponent under the pure-shot-noise alternative** | **−0.0045** |
| exponent under the pure-scene alternative | 0.0000 |
| **measured** | **+0.0250** |

The map at n=1 is already **97.5% scene by amplitude, 97.4% by variance**. The two hypotheses
Q10 was built to separate are **0.0045 apart** in the measured statistic, and the measurement
landed 0.025 away from *both*. **The exponent had no power to discriminate anything**; it could
not have come out near −0.5 under any hypothesis. The conclusion (the floor is scene) is
correct, but the evidence for it is the **pair-difference** number (1.6% vs 15.4%), which the
doc also cites — not the exponent. Fact 233's phrase "exponent +0.025 ... against −0.5 for shot
noise" should be withdrawn; **−0.0045** is the correct contrast, and it is not a test.

**Incidental corroboration worth keeping.** Model 2.343% vs measured 2.275% is a **no-free-parameter
validation of the M4 noise model at map scale to 3.0%**, with the model over-predicting. That is
the *same sign and size* as the −3.4% over-prediction I measured independently at pixel scale in
M28 (§2.7), from a completely different statistic. Two independent routes agree that M4's
`sigma` is about 3% high.

### 5.7 **Defect — the detection limit is quoted from the arm the milestone declares defective**

Script 04's docstring: "**STATISTIC.** Per-location conjunction on the **RAW** fractional maps...
The standardised variant is reported alongside **for comparison only**", and "positive control: a
50% shadow. If that does not fire, the statistic is broken and no limit derived from it is worth
reporting." From `04-limit.json`:

| depth | raw loc0/1/2 | fires? | standardised loc0/1/2 | fires? |
|---|---|---|---|---|
| 32% | −0.513 / −0.346 / −0.288 | no | −4.52 / −3.99 / −3.33 | no |
| **50%** | −0.552 / −0.471 / −0.420 | **no** | −6.89 / −6.32 / −6.08 | **yes** |

`limit` is `[None, None, None]` for raw and `[0.5, 0.5, 0.5]` for standardised.

**By its own pre-registered criterion, Q7 FAILS for the primary statistic.** The doc says "**Q7
holds** (the 50% positive control fires at all three locations)" without saying which arm, and
fact 232's "the 50% positive control fires at all three planted locations" inherits that. The
headline "detection limit: between 32% and 50%" is the **standardised** conjunction's limit —
the statistic §2 defect (d) declares wrong for exactly this measurement ("standardising makes a
common defect non-common"). The doc explains the raw failure structurally in the next paragraph,
so it is not concealed, but the number is attributed to the wrong arm.

The direction is conservative: the raw statistic's limit is `>50%`, so "dust is undetectable
from subject stacks" is *more* true, not less. **Fact 232's conclusion stands; its "32–50%"
should read "greater than 50% for the primary statistic; 32–50% for the standardised variant".**

### 5.8 **Defect — the flat-field budget omits PRNU, and PRNU is what sets that floor**

§4 computes the flat's map floor as pure photon noise, on the grounds that "a flat has
`g/blur(g) ≡ 1` everywhere by construction". With per-pixel gain variation `p`, a flat gives
`g = F(1+p)`, `blur24(g) ≈ F` (because `p` is zero-mean and high-frequency), so
`g/blur24(g) ≈ 1 + p`, the mean over frames is still `1+p`, and the highpass keeps it. **The
flat's map floor is PRNU, and PRNU does not fall with `n`.**

M4 explicitly declines to measure PRNU and estimates it at 15–50 DN at 5000 DN, i.e. **0.3–1.0%**.
I extracted a bound from M29's own script-01 data (`v14`): for two different-subject stacks the
map cross-correlation gives `common = sqrt(|r|·σ_a·σ_b)`, and the tightest value across all 14
different-subject pairs (including their shift nulls, which set the instrument's own floor) is
**≲ 0.26%**. Re-pricing §4 with a 0.26% PRNU term:

| ISO | S | per frame | n=20 photon (doc) | n=20 with PRNU | 5% dust: doc | with PRNU | n=64: doc | with PRNU |
|---|---|---|---|---|---|---|---|---|
| 100 | 8000 | 0.535% | 0.120% | **0.286%** | 42σ | **17σ** | 75σ | **19σ** |
| 100 | 12000 | 0.437% | 0.098% | **0.278%** | 51σ | **18σ** | 92σ | **19σ** |
| 160 | 8000 | 0.677% | 0.151% | **0.301%** | 33σ | **17σ** | 59σ | **18σ** |

Two design consequences:

1. **The 42–51σ figures are overstated by up to ~2.5x** if PRNU sits anywhere near the bound.
2. **More flats stop helping at n ≈ 4–5.** Photon noise drops below a 0.26% PRNU floor at
   `n > (0.535/0.26)² = 4.2`. The "≥16 flats per working aperture" specification in §6.3 and
   `captures-needed.md` §6 is *not* justified by the dust-detection σ that is used to justify it.
   (It may still be justified by the noise a flat injects into the corrected image, which is a
   different argument and is not the one made.)

The 400x figure in §6.5 ("at a 0.12% floor the same statistic is 400x more sensitive") does not
appear in any script output and I could not derive it; with PRNU at the bound the honest number
is ≤ 144x against the worst stack and ~63x against the median.

### 5.9 Scripts 01 and 02 — the account is accurate; no downstream number depends on them

- `ATTEN = 0.274` (script 01 -> script 02) is refuted by script 03 and **never used again**;
  script 04 measures `R_ij` per (stack, location) directly. Verified by reading all four later
  scripts. ✓
- Script 05 and 06 share no quantity with 01/02. ✓
- §1's retained "incidental result" (Q3, `112 × 113` r = 0.9370 vs shift null 0.0845, versus
  `coffee-bean × coffee-bubbles` r = 0.0001) **is** sound to keep. Defect (a) was about a
  control, defect (b) was that a *global* correlation cannot see a *sparse localised* defect —
  neither invalidates using a global correlation to answer a global scene-dominance question.
  It also yields the PRNU bound in §5.8, which the author did not extract. ✓

**Two accuracy notes on §1.** The doc reports "cross-stack `r` = 0.002–0.016 against shift nulls
of 0.001–0.008". The actual ranges in `01-static.json` are `r` from **−0.0502** to 0.0164 and
nulls from **−0.0481** to **+0.0164**; the largest-magnitude different-subject pair
(`109 × 119`, `r = −0.0502`, null `−0.0481`) is omitted from both ranges. Its excess is
−0.0021, so the null verdict is unaffected, but the quoted ranges are the positive subset only.
And fact 234's "same-ish median 0.4685 ... a 271.92x ratio" is the median of a **two-element**
set spanning 0.0001 to 0.9370; the midpoint of those is not a meaningful statistic and the
271.92x derived from it should not be quoted.

Finally, script 01's shift null is a **16-px roll on the green sublattice**. The maps are
highpassed at σ=24, so structure has a correlation length longer than the roll — the null retains
real signal (`112 × 113` null = 0.0845, not ~0). That makes the null too *high*, i.e.
conservative for a null result, so it does not threaten the conclusion.

---

## 6. Numbers I could NOT reproduce independently

Nothing I attempted came out *different* from the published value. The list below is what I
did **not** independently recompute — read from a committed `out/*.json` only, or not checkable
at all. Per rule 12 these remain hypotheses.

| number | status |
|---|---|
| M28 §5 transfer table (109 / coffee-bubbles / foam at 5.00/1.01/0.10, 27.70/8.33/1.59, 51.58/17.88/3.43) | **read from committed JSON only.** Not recomputed. It also inherits every choice in §2.6 (second difference, mean-gain fit), and the three stacks confound stability with contrast — the author discloses this. |
| M28 §6's four-estimator gain table | I independently confirmed the two that matter (median 4.28% p-p vs M24's 0.91%; mean is flatter) but did **not** recompute all four rows. |
| M30 `frac_snr10` | not checked. |
| M29 script 01's `259.6σ` / `0.074σ` / `1.096%` plant figures | read from JSON only. They are declared void by the milestone, so this is not load-bearing. |
| M29 script 02's sweep (−3.923 / −3.924 / −3.928 over a 32x depth range) | read from JSON only. Also declared void. |
| M29 §6.5's "**400x** more sensitive" | **does not appear in any script output and I could not derive it.** With PRNU at the §5.8 bound the honest figure is ≤144x (worst stack) or ~63x (median stack). Treat 400x as unsourced. |
| M29 §4's PRNU-free flat floor | I have a **bound** (≲0.26%), not a measurement. PRNU cannot be measured on this corpus; that is exactly why flats are needed. |
| Anything about the **shipped Rust pipeline** | Not touched. Every number in all four milestones is measured on a Python proxy of a statistic, not on `crates/**`. No Rust was compiled or run in this verification. |

---

## 7. Errors found, ranked by how much they would change a design decision

**1. M30 fact 242 is an artefact of a rule-4-forbidden argmax. (REFUTED — withdraw or re-measure.)**
The 0.075% vs 0.177% clipping advantage is 2.3x with a raw argmax, **1.4x** at the 31x31
regularisation scale the project ships, and **1.0x** under heavier smoothing, converging to the
uniform-random-frame null (0.1710%). The R19 advisory trigger sized on this number would fire at
about half the rate it should. `experiments/m30-hdr-cobracket/src/01-dynamic-range.py`, `bi`
argmax; reproduce with `experiments/m31-verification/src/v09-m30-argmax-bias.py`.

**2. M28's stated mechanism is wrong and one of its headline curves is ~3x inflated.**
The architectural decision (reference immediate neighbours; the mask can run pre-alignment)
**survives** — the adjacent-frame reference is radially flatter under all three gain estimators.
But the reason given ("accumulating geometric warp, near-linear in separation") is refuted: the
residual is a near-constant 3.5–4.5% *fraction of signal*, is non-monotone in `|grad|`, and its
log-log slope against separation is 0.40–0.56, not 0.86. Anyone who later builds a
displacement-scaled mask from fact 220's numbers will be scaling a brightness difference.
`experiments/m28-robustness-scale/src/02-identity.py` (median gain) vs `04-sensitivity.py`
(mean gain); reproduce with `v02`, `v03`, `v04`.

**3. M28 §2's "predicts to 9.9% with no free parameters" should not be cited as a noise-model
validation.** It is 1.005 / 1.099 / 1.449 at tile scales 1 / 8 / 32, 1.245 for a first
difference, and **1.505** without the 22 fitted per-frame gains. M29 §5 cites it; M28 §7 leans
on it. My §2.7 and §5.6 give two genuine no-free-parameter validations instead (model
over-predicts sigma by ~3.0–3.4% at two different scales), which is a better result than the one
being claimed. Reproduce with `v05`, `v06`, `v15`.

**4. M29's flat-field specification is priced without PRNU, and PRNU is the binding term.**
"≥16 flats per working aperture ... 42–51σ" becomes ~17–19σ and stops improving at n ≈ 4–5 if
PRNU sits at the ≲0.26% bound. This is the only error in the set that changes what the owner is
being asked to *shoot*. `experiments/m29-static-defects/src/05-floor.py`; reproduce with `v14`
(bound) and `v15` (re-pricing).

**5. M28's "@FPR 1%" is an unknown, ultra-conservative operating point.** Thresholds are taken
from a different population (`others`) than the one tested. The placebo reads 9.85/8.33/10.61%
at nominal 5% and exactly 0.00% at nominal 1% and 0.1%. A mask shipped at "FPR 1%" would run far
stricter than advertised. Recalibrated on the tested frame's own null the sensitivities barely
move, so **the conclusions survive** — but the operating point does not mean what it says.
`experiments/m28-robustness-scale/src/04-sensitivity.py`; reproduce with `v07`.

**6. M29's detection limit is quoted from the arm the milestone declares defective.** Q7 fails
for the primary (raw) statistic — the 50% positive control fires at none of the three locations —
and the "32–50%" limit is the standardised variant's. Conservative direction, so fact 232's
conclusion holds; the number should be restated. `04-limit.py`; see `out/04-limit.json`,
`result.raw.limit = [null, null, null]`.

**7. M30's `read_limited` implements `S < RN_e²`, not `S < RN_e²·g`.** Off by 8.7x / 0.87x /
2.7x across the three stacks. The documented boundary is the algebraically correct one, and the
conclusion holds when I evaluate it directly (0.000000% everywhere, checked on the full green
plane) — but the committed script does not prove what it is cited for, and on 112MSDCF it was a
*weaker* test than documented. `01-dynamic-range.py`; reproduce with `v08`.

**8. M29's displacement estimator is peak-locked and reports ~0.5x of truth below 0.3 px.**
The disclosure's claim that the sep-1 column "is clean" is false. Fact 230's 0.07–0.22 px should
read ~0.15–0.45 px. `D < 0.7` needs 5.47 px, so **the refutation survives with >12x margin**.
`06-dilution.py`; reproduce with `v13`, `v16`.

**9. M29's disclosure of broken columns omits `sep 4`** (coffee-bean reads 3.381 px at sep 4 and
0.103 px at sep 8), and the `n=5 span4` column of the §5 table is computed from it without
caveat. Conservative direction.

**10. M29 fact 233's stated alternative ("against −0.5 for shot noise") is wrong.** The
shot-noise hypothesis predicts **−0.0045** for this measurement, because the n=1 map is already
97.4% scene by variance. The exponent had no discriminating power; the pair-difference number
did the work.

**11. M27's `nwide` is floored at 1 by construction**, so three of the five entries in the
headline `3/2/1/1/1` column are at the statistic's floor and measure nothing. The mean
(3.445/1.799/1.472/1.361/1.272) and §4's ≤1-sample fraction still discriminate.

**12. M27 discipline 120's three instances are two.** Fact 73's `mean|∇|` is an absolute
magnitude, not a self-normalised shape statistic, so it does not instantiate the named class.
Fact 211 **is** a genuine third *mechanism* (unsampled evidence, numerator-driven) distinct from
fact 203 (denominator degeneracy) — the specific worry raised to me does not hold. But "never
measures presence of evidence" is stronger than what was measured: `curv` reads 0.5607 on
information-rich pixels and 0.4415 on the dimmest 2%, so it is not independent of evidence.

**13. M30 fact 240 calls an sd ratio a variance ratio.** The effect in variance is
0.082/0.942/0.384%, double the quoted figures. Direction unchanged.

**14. Reporting accuracy, M29 §1.** Quoted cross-stack `r` range 0.002–0.016 and null range
0.001–0.008 are the positive subset; the actual ranges are −0.0502..0.0164 and −0.0481..0.0164.
Fact 234's `271.92x` is derived from the median of a two-element set spanning 0.0001 to 0.9370.

**15. M27 reads its input from `C:\Users\chris\.copilot\session-state\...`, outside the repo,
and commits no `out/*.json`.** M27 was verifiable only because I rebuilt the volume from the raws
and it matched bit-for-bit. This is a rule-14 mirror-directory hazard.

---

## 8. Claims I believe are true but could not check

- **M28 §5's transfer table.** The 109 / coffee-bubbles / foam ordering is physically sensible and
  `foam` is the designed instability control, but I read the numbers from JSON. Note that whatever
  the table says, it inherits §2.6's estimator choices.
- **M28 §6's full gain-estimator comparison.** I confirmed the two rows the argument depends on.
- **M30's neutrality generalising to real captures.** No co-bracketed exposure pair exists in the
  corpus. The identity is exact algebra and I confirmed it by Monte Carlo, but nothing has been
  measured on a real +2 EV frame, and §3.1d's ISO-vs-shutter distinction is untested.
- **M29's PRNU.** I have an upper bound of ≲0.26% from cross-stack correlation. The true value
  needs flats and cannot be obtained from this corpus.
- **M29's "no dust is present".** Correct as a bound, and the bound is weak (>50% shadow for the
  primary statistic). It is consistent with a clean sensor and equally consistent with 15% dust.
- **M27 generalising past `coffee-bean`.** Every M27 number is from one stack, 53 frames. The
  curvature-ratio excess and the ≤1-sample criterion are untested on 112/113/119/109.
- **All four milestones as descriptions of the shipped pipeline.** Every statistic is a Python
  proxy. None of `crates/**` was exercised.

---

## 9. What should have been measured and was not

**M28.** (a) A resampler-free plant control on the *residual* — plant a known displacement and
check that the statistic responds proportionally to it. That single control would have caught the
photometric confound immediately. (b) The residual split by `|grad|` and by level (I did both;
they refute the mechanism). (c) The separation curve under the mean-gain estimator §6 recommends,
which is a two-line change and moves the headline from 12.30 to 4.09. (d) The FPR calibrated on
the tested frame's own null. (e) The **mislocalisation rate** — the second-difference detector
flags frame `k` when the outlier is at `k±1`, and the mask is per-frame.

**M30.** (a) The clipping figure under a **regularised** best-frame index, which rule 4 requires
and which is the whole result. (b) The union-over-frames clipping (1.12%), which is what a
selector that can pick any frame actually risks. (c) Exclusion of pixels that clip at +2 EV from
the neutrality ratio. (d) The neutrality claim restricted to shutter-bought EV, with the ISO
route priced separately given dual gain.

**M27.** (a) A blind grouping — the published positive/control split uses a full-stack argmax
oracle. (I ran it; it passes.) (b) The `nwide` floor. (c) The deployable own-min version of fact
213. (I ran it; it passes.) (d) A second stack.

**M29.** (a) **PRNU.** It is the term that decides the flat specification, it is named as unmeasured
in M4, and M29 quotes a σ that assumes it away. (b) A plant control on the displacement estimator —
a four-line Fourier shift would have shown the 2x peak-lock bias and the sep-4 breakage in the same
run. (c) The raw-arm detection limit, or an explicit statement that the primary statistic has none.
(d) The **power** of the Q10 exponent before using it as a discriminator: two lines of algebra
show the two hypotheses differ by 0.0045. (e) Q12, which was pre-registered and is unreported.

**Cross-cutting.** Three of the four milestones state a headline that depends on a nuisance-parameter
choice made differently in different scripts of the same milestone (M28: median vs mean gain; M29:
raw vs standardised conjunction; M30: documented vs implemented read-noise boundary). A single
convention block shared across each milestone's scripts would have prevented all three.

---

## 10. Numbering

I have deliberately reserved **no** fact, discipline or question numbers. Everything above is a
correction to, or a confirmation of, an existing numbered claim, and is written so the orchestrator
can fold it at whatever numbers are current. The claims that need a wording change if folded are
**220, 221, 222 (M28)**, **230, 231, 232, 233, 234 (M29)**, **240, 241, 242 (M30)** and
**120 (discipline, M27)**; the one that should be **withdrawn or re-measured** is **242**.

## 11. Files

All under `experiments/m31-verification/` (mine; nothing else in the repository was created or
modified by me):

| script | covers |
|---|---|
| `src/v01-m28-core.py` | independent decode; M28 §1/§2 core statistics |
| `src/v02-m28-gain-confound.py` | gain-estimator sensitivity of the separation curve |
| `src/v03-m28-radial-matrix.py` | 3x3 gain x reference-type radial matrix |
| `src/v04-m28-mechanism.py` | breathing vs photometric vs defocus discrimination |
| `src/v05-m28-noisemodel.py`, `src/v06-m28-model-refit.py` | noise-model validation, simulation controls, CFA/ISO sanity |
| `src/v07-m28-sensitivity.py` | independent sensitivity, honest FPR, threshold-free AUC |
| `src/v08-m30-checks.py` | M30 boundary, Monte-Carlo neutrality, clipping nulls |
| `src/v09-m30-argmax-bias.py` | rule-4 regularisation test of fact 242 |
| `src/v10-m27-volume.py` | independent focus volume; M27 table reproduction |
| `src/v11-m27-adversarial.py` | M27 null stability, blindness, discipline 120, `nwide` floor |
| `src/v12-m27-oracle.py` | M27 fact 213 oracle-threshold check |
| `src/v13-m29-peaklock.py` | Fourier-shift plant control on M29's displacement estimator |
| `src/v14-m29-atten.py` | exact pipeline algebra on a synthetic flat; PRNU bound |
| `src/v15-m29-floor.py` | M29 n-sweep, Q10 power analysis, PRNU re-pricing |
| `src/v16-m29-sep1.py` | exact sep-1 reproduction; radial/scale test |
| `out/cb_vol_mine.npy` | my independently built 53x1500x1500 focus volume |
