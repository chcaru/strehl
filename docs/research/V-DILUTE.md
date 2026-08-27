# V-DILUTE — is the pyramid merge's selection diluted by stack depth?

**Binary:** pin `9b05d0b7`, `C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe`,
sha256 `44C2F2CD2E5B2894…` — verified before use. Every run named `--merge pyramid`
explicitly. **Subject:** `bee-3-cpl`, 299 frames — the stack SYNTHESIS fact 1790 (V-LINEAR)
measured `0.180`/`0.060` on. Pre-registration with kill conditions was committed **before any
render**: `experiments/V-DILUTE/PREREGISTRATION.md`.

---

## VERDICT

**The dilution hypothesis is DEAD.** The merge does not lose selection as the stack deepens.
On `bee-3-cpl` it becomes *more* committed with depth, not less, and at N=299 it is still
within 19% of a pure argmax in the bands that carry acuity. Five independent instruments agree,
two of them pre-registered as kill conditions, and both kill conditions fired.

The arithmetic in fact 1794 is correct. Its **input assumption is not**: it evaluates
`SUM (e_k/e_winner)^p` as though all `N-1` frames sit at ratio `r ≈ 0.5–0.7`. Measured, the
effective ratio in the fine bands is **`r ≈ 0.36`**, because the gate zeroes almost every
competitor outright. At that ratio the winner's share is **0.92 at N=299**, not 0.055 — the
predicted collapse never starts.

**Do not build a fix for this mechanism.**

---

## 1. Commissioning (nothing below was believed before this passed)

| check | result |
| --- | --- |
| **Null** — identical flags twice, decoded arrays | **bit-identical**, 0 of 24,724,512 samples differ |
| **Potency** — `--pyramid-exponent 4.0` vs default | **84.94%** of samples moved, max Δ **1208 DN** |
| **Confidence-map potency** — hard-max vs default vs mean-arm, N=22 | **409.8 / 463.3 / 811.8** — cleanly separated |

ORCH's quoted potency figure is 90.98%; I measure **84.94%** on `beeN22`, presumably a
different subject/frame-set. Potency is established either way.

### The instrument has a large N-dependent bias, and it points the hypothesis's way

`--confidence-map` writes `v = 1 − 2·|below/seen − 0.5|` (`merge_cmd.rs:4695`). The rank is
estimated from `N` observations, so for a merge that averages **identically at every depth**,
`below/seen → Binomial(N,½)/N` and `E[v] ≈ 1 − √(2/πN)`:

| N | 22 | 33 | 63 | 105 | 150 | 299 |
| --- | --- | --- | --- | --- | --- | --- |
| E[v], no change in merge behaviour | 831.8 | 860.1 | 899.1 | 921.9 | 935.0 | **953.8** |

**A raw rise of confidence with N is not evidence.** Every N is therefore bracketed by a
committed floor (`--pyramid-select hard-max`) and an averaged ceiling
(`--pyramid-exponent 0.05 --pyramid-sharpen 1.0`) at that same N.

---

## 2. Experiment A — confidence vs N (`bee-3-cpl`, fixed focus range, stride varied)

All stacks span frames 1–299, so N is proportional to the number of frames simultaneously near
focus at a pixel: this is a **competitor-density sweep**, the axis the model actually names.

| N | arm | mean | p10 | p50 | p90 | ≥800 | ≥900 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 22 | default | 463.3 | 91 | 364 | 909 | 29.6% | 23.1% |
| 33 | default | 446.3 | 61 | 364 | 909 | 26.3% | 21.9% |
| 63 | default | 427.8 | 32 | 349 | 921 | 25.9% | 14.7% |
| 105 | default | 418.9 | 19 | 343 | 933 | 26.4% | 13.9% |
| **299** | **default** | **418.5** | **7** | **355** | **930** | **25.4%** | **14.3%** |
| 22 / 63 / 299 | hard-max | 409.8 / 370.5 / 352.0 | | | | | |
| 22 / 63 / 299 | mean-arm | 811.8 / 820.0 / 830.1 | | | | | |

**Confidence FALLS with N — 463.3 → 418.5 — while the sampling bias says a merge that changed
nothing would RISE to ≈954.** `bee` at N=299 does not sit at the averaging end: its median is
355 and only **14.3%** of pixels read ≥900.

**Normalised commitment index** `CI = (default − hardmax)/(meanarm − hardmax)`:

| N | 22 | 63 | 299 |
| --- | --- | --- | --- |
| **CI** | **0.133** | **0.128** | **0.139** |

**Flat.** `A-KILL-1` fires as written.

---

## 3. The strongest instrument: effective frames averaged

Hard-max inherits one frame's noise in the fine bands; the default averages whatever clears the
gate. Measured at 0.40–0.50 cyc/px on **textured** tiles — high frequency, so it lives in the
selecting bands, not the base band. `n_eff = noise_hardmax / noise_default` is a power ratio,
immune to the rank-sampling bias entirely.

| N | noise hard-max | noise default | **n_eff** | detail default / hard-max |
| --- | --- | --- | --- | --- |
| 22 | 26375.7 | 25892.0 | **1.019** | 1.0047 |
| 63 | 63177.8 | 60037.4 | **1.052** | 0.9994 |
| **299** | 107982.2 | 91084.6 | **1.186** | **0.9479** |

At N=299 the shipped merge averages the equivalent of **1.19 frames** and keeps **94.8%** of a
pure argmax's detail. The hypothesis needs share ≈ 0.055, i.e. `n_eff ≈ 18`. **Measured is off
by a factor of 15.**

Inverting for the effective competitor ratio at the finest band (p=8, M=298):
`M·r^8 = 0.089` ⟹ **`r ≈ 0.36`**, **`share_winner ≈ 0.92`**. That is the whole story.

> **A methodological correction others should take.** My first noise number used *flat* tiles
> and read `n_eff = 1.00` at every depth. Flat tiles are exactly where **no frame clears the
> gate**, so the merge falls back to the same unweighted mean under every select mode and the
> statistic is structurally blind. The run log says so for free: `averaged: 30.8% …` at N=22.
> Noise must be measured on the same textured tiles as the detail.

---

## 4. Detail and noise vs N — deeper is SHARPER, at fixed range

| N | fov s | detail 0.30–0.35 | detail, no magnif. corr. | noise HF | detail/noise |
| --- | --- | --- | --- | --- | --- |
| 22 | 0.9021 | 163,098 | 90,127 | 25,892 | 6.299 |
| 33 | 0.9198 | 211,608 | 136,535 | 35,620 | 5.941 |
| 63 | 0.9208 | 367,472 | 236,395 | 60,037 | 6.121 |
| 105 | 0.9174 | 501,782 | 317,363 | 84,308 | 5.952 |
| **299** | 0.9321 | **561,990** | 380,763 | 91,085 | 6.170 |

Detail rises **3.4×** from N=22 to N=299 at matched range and matched bandwidth, and
detail/noise is **flat at ~6.0–6.3**. Deeper stacks are not softer on this subject.

**This contradicts V-SOFTCHECK (fact 1789).** That lane measured 63 frames as `0.114` *softer*
than 32 at 0.30–0.35 cyc/px at matched range. On `bee-3-cpl` I measure N=63 as **1.74× sharper**
than N=33 at the same band and range. If V-SOFTCHECK was on another subject that should be
stated; as a general claim about depth it does not replicate here.

---

## 5. Experiment B — the equal-N decimation

### 5a. ORCH's two arms as specified — confounded, and I flagged this before running

Pre-registered objection: the *first-150* arm **contains no in-focus observation for the far
half of the subject**. Every model, including "no dilution at all", predicts the full-range arm
wins globally. Measured global x2/x1 detail ratio **1.9497** — and it means nothing.

### 5b. The repaired comparison — common-focus ROI, where both arms own the in-focus frame

48.7% of pixels have best-focus frame < 150 (per an **independent** estimator `--index-map`).
Images are never resampled; every sample is addressed in a common **sensor frame**, because the
arms differ in alignment FOV scale (x2 0.9228, x1 0.9595 — 4.2% differential magnification).

| arm (N=150 both) | detail 0.30–0.35 | detail 0.20–0.25 | noise HF, same tiles | confidence |
| --- | --- | --- | --- | --- |
| x2 step, FULL range | 577,663 | 2,722,017 | 99,699 | 243.5 |
| x1 step, HALF range | 513,479 | 2,526,917 | 84,258 | 224.1 |

Pooled ratio **1.1250** (1.1136 after noise subtraction) — the model's direction. **But it does
not survive scrutiny:**

| test | result |
| --- | --- |
| paired per-tile, 32 tiles, bootstrap | mean **1.0506**, 95% CI **[0.8866, 1.2488]** — **includes 1.0** |
| sign test | **19 of 32** tiles favour x2 (p ≈ 0.38) |
| **magnification correction OFF** | ratio **flips to 0.8736** |
| confidence | x2 **243.5** vs x1 **224.1** — x2 is *less* committed, **against** the model |

**Experiment B cannot be made decisive on this data.** Equal N forces the two arms to differ in
focus range, which forces different alignment drift, which forces both differential
magnification *and* differential interpolation blur — artifacts the same size as the effect.
The one number that mildly favoured the model is carried by a 4% geometry correction and fails
its own significance test. It is not evidence, in either direction.

### 5c. The duplication null — the control that *does* isolate N (my addition)

Merge the first 150 frames; then merge those same 150 frames **each present twice** (N=300).
Focus sampling, range and subject identical; only the frame count doubles. Run with
`STREHL_ALIGN=0` so both arms share exact geometry — necessary, because alignment re-solves
differently on a duplicated stack (reference frame 75 → 150, FOV 0.9595 → 0.9856/0.9494) and
contaminated my first attempt.

| | N=150 | N=300 (each frame twice) |
| --- | --- | --- |
| confidence mean | **0.4201** | **0.4201** |
| decoded-array difference | — | **0.0588% of samples, max Δ 1 DN** |

**Doubling the frame count with focus sampling held fixed changes nothing** (1 DN is
float summation order). Damage cannot track raw `N`. Whatever else is wrong with `bee`, it is
not the number of frames.

---

## 6. Experiment C — exponent sweep on `bee-3-cpl`, N=299

Every row pairs detail with noise on the same tiles (rule 3).

| exponent / sharpen | ladder | detail 0.30–0.35 | detail 0.20–0.25 | noise | det/def | noise/def | pixels moved vs default |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 / 1.4 | 0.5→5.4 | 499,725 | 2,698,034 | 27,247 | **0.889** | **0.866** | 97.7%, max Δ4041 |
| 1.0 / 1.4 | 1.0→8.0 | 560,249 | 2,976,377 | 31,598 | 0.997 | 1.005 | 94.0%, max Δ2012 |
| **2.0 / 1.4 (SHIPPED)** | 2.0→8.0 | **561,990** | **3,002,895** | **31,446** | 1.000 | 1.000 | — |
| 4.0 / 1.4 | 4.0→8.0 | 560,457 | 2,990,857 | 31,185 | 0.997 | 0.992 | 89.8%, max Δ1259 |
| **8.0 / 1.0 (uniform cap)** | 8.0 flat | 560,130 | 2,987,089 | 31,056 | **0.997** | 0.988 | 90.1%, max Δ1620 |

**`C-KILL` fires. The uniform-high arm does not recover the bee — 0.997, no change.** This is a
genuine null and not a dead metric: those arms move **90–98% of all samples**, up to 4041 DN,
and the same metric registers the low arm at 0.889/0.866.

The reason is structural: with `sharpen 1.4` over 7 bands the default ladder is
`2.0, 2.8, 3.9, 5.5, 7.7, 8, 8` and is **already pinned at `MAX_EXPONENT = 8.0` in the fine
bands** where the measured detail lives (`exponent_at`, `pyramid.rs`). Raising
`--pyramid-exponent` only lifts the *coarse* bands. **There is no headroom on this axis**, which
is also why the other lane's hull violations (0/72/511 at exponent 1/8/16) buy ringing and
nothing else.

---

## 7. What surprised me / what contradicts the framing

1. **The bee is not veiled by averaging.** At N=299 it reads `n_eff = 1.19` and median
   confidence 355. It is nearly argmax. Whatever destroys `0.180`/`0.060` of the detail, the
   merge's *selection* is not hedging.
2. **Confidence moves the wrong way with N** (463→419) while the statistic's own bias pushes the
   other way (832→954). The merge gets *more* decisive as the stack deepens.
3. **The exponent axis is saturated.** Half the tuning surface (`--pyramid-exponent` from 1.0 to
   8.0) is inert on measured detail.
4. **Deeper is sharper at fixed range** (3.4× from N=22 to N=299), contradicting fact 1789.
5. **Alignment is not invariant to duplicating frames** — reference frame and FOV scale both
   move. Any future harness comparing frame subsets must read `field of view scaled to …` out of
   each run's own log; two arms with different frame sets are at different magnifications, and
   comparing a spectral band across them without correcting is wrong. This nearly inverted my
   Experiment B result.

## 8. Where the real failure is not excluded

This lane kills one mechanism; it does not explain `bee`. Untouched and still live: the
alignment residual on a 299-frame bracket (`bee-3-cpl` at N=299 reports `field of view scaled to
0.9321 … 6.8% of width dropped, then upsampled to keep the output dimensions` — every output
pixel on this stack is an interpolated resample, and the shrink grows with N: 0.9021 at N=22),
the differential interpolation blur that implies, and the base band, which
is an unweighted **mean** at every depth by default (`BaseBand::Mean`) and which no experiment
here disturbs. The measured `n_eff = 1.19` says the fine bands are committed; it says nothing
about whether they are committed to the *right* frame.

---

## Reproduce

```
experiments/V-DILUTE/PREREGISTRATION.md   kill conditions, written before any render
experiments/V-DILUTE/run_queue.ps1        every render, pin binary, --merge pyramid explicit
experiments/V-DILUTE/vd_metrics.py        spectra, tiles, FOV-scale correction, analytic null
experiments/V-DILUTE/analyze.py           A | B | BROI | C
experiments/V-DILUTE/broi_robust.py       paired per-tile bootstrap + correction-off sensitivity
experiments/V-DILUTE/commission.py        null arm, potency arm, analytic rank bias
```
