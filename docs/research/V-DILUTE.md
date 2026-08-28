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

### Confidence-map potency AT EVERY FRAME COUNT, in percent-of-samples-moved

So that "flat in N" can never be confused with "not reading", the known-potent brackets were run
at each depth and are restated here in the same units as V-REVIEW's arms:

| N | default vs hard-max (elect floor) | default vs mean-arm (average ceiling) |
| --- | --- | --- |
| 22 | 42.69% moved | 82.96% |
| 63 | 60.97% moved | 91.77% |
| **299** | **80.63% moved** | **98.43%** |

For reference: `--pyramid-gate 8.0` moves it 16.27%, `--pyramid-bands 3` 9.66%,
`--confidence-tail` **0.00% (inert)**. **The instrument is not merely alive at N=299 — it is
the most responsive there**, moving 4 in 5 of all samples, ~5× the gate arm. The flatness
reported below is a measurement.

`--confidence-tail` **was never used in any arm of this lane**; every threshold is applied by me
to the decoded array, so its inertness cannot have touched a result here.

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
| paired per-tile, 32 tiles, bootstrap | mean **1.1144**, 95% CI **[0.9442, 1.3140]** — **includes 1.0** |
| sign test | **20 of 32** tiles favour x2 (p ≈ 0.30) |
| **magnification correction OFF** | ratio **flips to 0.9268** |
| confidence | x2 **417.7** vs x1 **380.2** — the *denser*-sampled arm is **more** committed, **against** the model |

### 5c. The replicate null — B's own noise floor, which B was never measured against

A ratio of 1.11 means nothing without knowing what this design produces when *nothing* differs.
Even-phase (`DSC00001,3,…,299`; N=150) versus **odd-phase** (`DSC00002,4,…,298`; N=149): same
subject, same focus range, same focus step, therefore the same number of frames near focus at
every pixel — the quantity the model actually names. It carries every nuisance of the contrast
(its own alignment solve, its own FOV shrink, its own resample blur) and none of its signal.
Identical tiles, bands, correction and bootstrap.

| band | CONTRAST x2 vs x1 | **REPLICATE x2 vs odd (null)** |
| --- | --- | --- |
| detail 0.30–0.35 | 1.1144, CI [0.944, 1.314] | **1.0158, CI [0.987, 1.045]** |
| detail 0.20–0.25 | 1.1097, CI [0.917, 1.325] | **1.0229, CI [0.994, 1.053]** |
| noise 0.40–0.50 | 1.1750, CI [1.014, 1.370] | **1.0222, CI [0.978, 1.068]** |
| confidence | 417.7 vs 380.2 | **417.7 vs 422.0** (agree to 1.0%) |

**Two things follow, and they point opposite ways.**

*The machinery is sound.* The replicate lands at 1.016 with a tight interval, and the two arms'
confidence agrees to 1%. The magnification correction is also **validated and necessary**: with
it switched off the replicate reads **0.9485, CI [0.920, 0.976], excluding 1.0** — a 5.2%
artifact conjured out of two arms that differ only in which alternate frame they took, because
alignment hands them different FOV scales (0.9228 vs 0.9359) even at identical density.

*The contrast still fails.* Its interval includes 1.0 while the replicate's is tight, so the
contrast's dispersion is not measurement noise — it is genuine tile-to-tile heterogeneity from
the residual focus-range confound the ROI could not fully remove.

### 5d. And then rule 3 reverses it

Detail was never allowed to be quoted alone. Paired with noise on the **same tiles, same bands,
same ROI**:

| | detail 0.30–0.35 | noise 0.40–0.50 | **detail/noise** |
| --- | --- | --- | --- |
| CONTRAST x2/full vs x1/half | 1.1144 | 1.1750 | **0.9484** |
| REPLICATE x2 vs odd | 1.0158 | 1.0222 | 0.9937 |

**The x2 arm's apparent 11% detail gain is more than accounted for by an 18% noise gain.** On a
noise-matched basis the contrast **reverses to 0.948** — the wrong direction for the model.
Rule 3 exists precisely to catch this, and it fires on the experiment ORCH ranked first.

### 5e. Scale — B cannot rescue the hypothesis even if the effect were real

The hypothesis predicts a 299/22 winner-share ratio of **0.083–0.122**, an **8.2×–12.0× collapse**.
B's contrast, taken at face value and noise-paired, offers **0.948×**. Even reading it
generously as the uncorrected 1.11×, it is **9–13× short** of the effect the mechanism requires.
A confounded, non-significant, noise-explained 11% cannot stand in for an order of magnitude.

### 5f. The duplication null — the control that *does* isolate N cleanly (my addition)


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

The reason is structural, and it is the **`--fix-ca` pattern**: a zero from a flag because the
stage is already doing the work. With `sharpen 1.4` over 7 bands the shipped ladder is
`2.0, 2.8, 3.9, 5.5, 7.7, 8, 8` and the two finest levels are **already pinned at the cap**:

| k | band cyc/px | default 2.0/1.4 | uniform 8.0/1.0 | low 0.5/1.4 | uniform/default detail |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.250–0.500 | **8.000** | **8.000** | 3.765 | 0.9967 |
| 1 | 0.125–0.250 | **8.000** | **8.000** | 2.689 | 0.9947 |
| 2 | 0.063–0.125 | 7.683 | 8.000 | 1.921 | 0.9933 |
| 3 | 0.031–0.063 | 5.488 | 8.000 | 1.372 | 1.0081 |
| 4 | 0.016–0.031 | 3.920 | 8.000 | 0.980 | **1.0483** |

My detail bands (0.30–0.35, 0.20–0.25 cyc/px) sit in k=0 and k=1, where the two arms are
**identical by construction**. The **stage is potent** — the metric moves 4.8% at k=4 where the
ladders differ, and the low arm moves every band (0.72–0.90). The **flag is redundant** in the
bands that carry acuity. Exactly `--fix-ca`.

### 6b. Correction: there IS headroom above the cap, it is CLI-reachable, and it is a footgun

I first wrote "no headroom on this axis." **That was wrong**, and following the `--fix-ca`
advice found it. `exponent_at` (`pyramid.rs`, pin `9b05d0b7`) returns **uncapped** on the ramp-off
path:

```rust
if self.sharpen_per_octave == 1.0 || bands == 0 { return self.exponent; }   // NOT capped
(self.exponent * self.sharpen_per_octave.powi(steps)).min(MAX_EXPONENT)     // capped
```

So `--pyramid-sharpen 1.0` bypasses `MAX_EXPONENT` entirely. My uniform arm read 0.997 partly
because I happened to pick **exactly the cap value**. Above it:

| exponent / sharpen | detail 0.30–0.35 | det/def | noise 0.40–0.50 | **noise/def** | confidence mean/p50 | max Δ vs default |
| --- | --- | --- | --- | --- | --- | --- |
| **2.0 / 1.4 SHIPPED** | 561,990 | 1.0000 | 91,085 | 1.0000 | 418.5 / 355 | — |
| 8.0 / 1.0 (= cap) | 560,130 | 0.9967 | 90,878 | 0.9977 | — | 1,558 |
| **12.0 / 1.0 (uncapped)** | 392,512 | **0.6984** | 191,940 | **2.1073** | 158.3 / 0 | **41,711** |
| **16.0 / 1.0 (uncapped)** | 304,993 | **0.5427** | 165,129 | **1.8129** | 75.1 / 0 | **41,711** |

> **CORRECTION — those two detail ratios are measured on a degenerate image and must not be
> read as detail retention.** A clipping audit of all 31 masters in this lane (`clip_audit.py`,
> 0.0000% clipped everywhere, so the `--auto-exposure` regression never touched this lane)
> caught the opposite rail instead: the uncapped arms are crushed to **black**.
>
> | arm | % samples exactly 0 | median | p90 |
> | --- | --- | --- | --- |
> | 2.0/1.4 SHIPPED | 0.000% | 11,082 | 18,701 |
> | 8.0/1.0 | 0.000% | 11,117 | 18,751 |
> | **12.0/1.0** | **46.199%** | 998 | 18,843 |
> | **16.0/1.0** | **61.193%** | **0** | 18,891 |
>
> p90 barely moves while the median falls to zero: the bright regions survive and **over half
> the frame is pure black**. Band power on such an image is not a detail measurement, for the
> same reason ORCH's print-gate axes cannot score a white sheet — **a saturated region has no
> structure, and this is that failure at the black rail.** The correct statement is not
> "detail falls to 0.54"; it is **"the master is 61% black."**
>
> The gate does not explain it: band-0 `averaged` reads only **0.4%** on both arms. The zeros
> are consistent with `f32` **underflow** of `r.powf(p)` — the same clamp-floor arithmetic that
> commit `8a480af9` documented flushing `sum(w²)` to zero below `f32::MIN_POSITIVE` — driving
> the weight sum to zero where the gate did clear. `pyramid.rs`'s own overflow test names the
> symptom exactly, in the other direction: *"one NaN coefficient spreads through the collapse
> into a black hole in the output image."* That test guards `p = 8`; the underflow path above
> `p = 8` is reachable **only** through the `--pyramid-sharpen 1.0` cap bypass and is unguarded.
> I have not proven the mechanism to the coefficient, and say so.

**Raising the exponent past the cap does not recover the bee — it destroys the image.** The
conclusion below is unchanged and strengthened; only the severity was understated. The source predicts this exactly: the ceiling is set by
`f32`, and *"`p` above about 10 can no longer rank the sharpest coefficients against each other:
they all pin to the ceiling and get averaged."* Above p≈10 the merge stops ranking and starts
averaging **the very coefficients it most needs to rank** — a max deviation of 41,711 DN is the
ringing the other lane counted as hull violations (0/72/511 at 1/8/16).

**This is a live footgun and it exits 0.** `--pyramid-exponent 12 --pyramid-sharpen 1.0` silently
emits a master that is **46% pure black**; at 16 it is **61% black**. No warning, no non-zero
exit, and a `p90` that still looks healthy. The cap exists to prevent exactly this and the
ramp-off path opens a hole in it. Worth a lane; not mine to patch.

**So the exponent axis cannot recover the bee in either direction** — saturated below the cap in
the bands that matter, actively destructive above it. `C-KILL` fires on stronger evidence than
I first had, and a higher exponent is emphatically **not** recommended.


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
5. **Alignment is not invariant to the frame subset — even at identical density.** Two arms
   differing only in which alternate frame they took get FOV scales 0.9228 vs 0.9359, worth a
   **5.2% spurious detail difference** if uncorrected. Any future harness comparing frame
   subsets must read `field of view scaled to …` from each run's own log and correct in the
   frequency domain; resampling to match would blur the arms unequally and bias the very
   quantity under test. This nearly inverted Experiment B.
6. **Experiment B's one pro-model number is a noise artifact.** Its 11% detail gain comes with
   an 18% noise gain on the same tiles; noise-matched it reverses to 0.948. Judged on detail
   alone it would have read as support for the hypothesis.
7. **The confidence map reads "maximally committed" exactly when the merge is at its worst.**
   At exponent 16 it reports mean **75.1**, p50 **0**, p90 **7** — as elected as a merge can
   look — while detail has collapsed to **0.54** and noise risen **1.81×**. The rank asks
   whether the output sits at an *extreme* of the observations, and **overshoot past every
   frame is also an extreme**. Confidence near 0 therefore means "elected a frame" *or* "rang
   past all of them", and cannot distinguish them. This is a real limitation of the instrument
   and another reason rule 3 is not optional. My `A` conclusions do not lean on absolute
   confidence — they rest on the bracketed CI and on `n_eff`, a noise-power ratio.
8. **`MAX_EXPONENT` is bypassable from the CLI** (§6b), silently, with exit 0.

### Two corrections to the brief's flag list, found by running `--help` before rendering

- **`--pyramid-confidence-map` does not exist**; the flag is **`--confidence-map`**. I hit this
  before any render and used the correct name throughout — no run is affected.
- The gating table's third column names the backend where a flag is **refused**, not where it is
  accepted. `--confidence-map` is pyramid-only; `--index-map`/`--n-eff-map` are refused under
  `--merge pyramid`. I misread this once in the other direction; stating it plainly here.
- `--confidence-tail <Q>` (default 0.05) is a **per-channel tail fraction for the confidence
  union mask**, not a reporting threshold for the confidence map — there was no house cut for my
  ≥800/≥900 fractions to have overridden. Nothing here depends on that cut regardless: the
  primary statistics are the bracketed CI and `n_eff`.
- `--exposure`/`--auto-exposure` are inert on this binary; **no arm in this lane used either**,
  and no arm needed brightness matching because every comparison is a within-arm band ratio.


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

## 9. Re-verified on HEAD, because the merge moved under this lane

Discipline 34 applies and it bit: the pin is stale. Measured rather than assumed — pin
`9b05d0b7` vs HEAD `c45d0067` (binary sha16 `F1D66AD7220DCC6C`), same subject, same flags:

| | pin | HEAD |
| --- | --- | --- |
| samples differing | — | **71.35%** of 24,724,512, max Δ **881**, mean Δ 15.2 |
| band-0 `averaged` duty cycle, N=299 | 0.4% | **8.4%** |

So `78fed9a1` (noise floor measured from each frame's own warp) changed the **default** path,
not only opt-in ones. I had read the diff as gated behind `--focus` and per-frame beta; the
pixels say otherwise. **A diff is not a pixel gauge either.**

**The verdict transfers anyway.** Re-measuring the load-bearing statistic on HEAD:

| build | N | noise hard-max | noise default | **n_eff** | detail def/hard-max |
| --- | --- | --- | --- | --- | --- |
| pin | 22 | 26,375.7 | 25,892.0 | **1.019** | 1.0047 |
| pin | 299 | 107,982.2 | 91,084.6 | **1.186** | 0.9479 |
| **HEAD** | 22 | 25,988.9 | 25,459.6 | **1.021** | 1.0034 |
| **HEAD** | 299 | 107,736.9 | 91,050.9 | **1.183** | 0.9483 |

`n_eff` agrees between builds to **0.3%** at both ends of a 13.6× depth range. The noise-floor
change moved 71% of samples without changing how *concentrated* the selection is. The merge on
current code is as near winner-take-all as it was on the pin, and the refutation stands on HEAD.

Also confirming ORCH's withdrawal of "the gate never fires above level 0": HEAD at N=22 reads
`averaged: 41.3% 3.6% 0.1% 0.0% …` — band 1 and band 2 are non-zero. Coarse bands do gate.

**Caveat:** the HEAD binary was built from a **dirty** working tree (`d35f9055…-dirty`) shared
with other active lanes, and HEAD moved to `c45d0067` mid-run. The comparison is sound (one
binary rendered both HEAD arms) but is not exactly reproducible from a clean checkout.

## 10. Independent corroboration, and a correction to my own noise reading

Commit **`8a480af9`** ("pyramid: n_eff, and what the frame count actually does to the merge")
tested the same hypothesis from **inside** the merge — reading the weights directly rather than
inferring from output noise — on a **different subject** (113MSDCF, N=63 vs N=32). It concludes
*"The hypothesis is REFUTED in its distinctive form."* Two things are worth recording:

- It converged on **the same statistic** (`n_eff = sum(w)²/sum(w²)`) and **the same confound**
  I raised here: that `max(w)/sum(w)` has null value `1/N` and so "would have confirmed the
  hypothesis by arithmetic". That is the same class of error as the confidence rank's
  `E[v] ≈ 1 − √(2/πN)` bias (831.8 → 953.8) that §1 brackets against. Two lanes, two
  instruments, same trap, caught independently.
- It also excludes bands where `MAX_EXPONENT` caps both arms "rather than scoring FLAT, because
  a band where nothing was planted is not evidence of a dead gauge" — independently the same
  finding as §6 here.

### The max-of-N flat-field result, cross-checked at 13.6× leverage

That commit's unexpected finding is that deepening a stack makes **flat** fields **noisier**
(grain ×1.1697 at N=63 vs N=32), because winner-take-all elects the largest of `N` noisy
candidates and `E[max] ~ σ√(2 ln N)` predicts ×1.0934. Their arms span 2.0× in depth; mine span
**13.6×**, where the predicted effect grows to ×1.358:

| N | 22 | 33 | 63 | 105 | 299 |
| --- | --- | --- | --- | --- | --- |
| flat-site grain, amplitude vs N=22 | 1.000 | 1.149 | 1.428 | 1.618 | **1.846** |
| `√(2 ln N)` prediction | 1.000 | 1.064 | 1.158 | 1.227 | **1.358** |
| measured / predicted | 1.000 | 1.080 | 1.233 | 1.318 | **1.359** |

**Direction and order confirmed on a second subject at 6.8× more leverage.** The measurement
runs above the law by a factor that itself grows, and there is a ready mechanism for the excess
that I measured independently: the band-0 `averaged` duty cycle **falls** with N (30.8% at
N=22 → 3.3% at N=150 on the pin), so a *growing fraction* of coefficients come under
winner-take-all as the stack deepens, on top of each being a max over more candidates. The
`√(2 ln N)` law captures only the second effect; the two are multiplicative.

**This corrects something I told ORCH earlier.** I said fact 1790's noise ratios (11.929 /
15.619 on `bee`) must be explained by the comparators' own noise, since `n_eff = 1.19` refutes
a `√N` averaging signature. The first half stands — `strehl` is not averaging. But there is a
mechanism on `strehl`'s side after all, and it runs the *opposite* way to averaging: **electing
the max of N noisy candidates is itself a noise amplifier that grows with depth.** On flat sites
`bee` at N=299 carries **1.85×** the grain amplitude of N=22. A comparator that averages will
beat that and the gap will widen with depth. This is a far better candidate for `bee`'s deficit
than dilution ever was, and unlike dilution it is measured on two subjects by two lanes.

## Reproduce

```
experiments/V-DILUTE/PREREGISTRATION.md   kill conditions, written before any render
experiments/V-DILUTE/run_queue.ps1        every render, pin binary, --merge pyramid explicit
experiments/V-DILUTE/vd_metrics.py        spectra, tiles, FOV-scale correction, analytic null
experiments/V-DILUTE/analyze.py           A | B | BROI | C
experiments/V-DILUTE/broi_robust.py       paired per-tile bootstrap + correction-off sensitivity
experiments/V-DILUTE/b2_replicate.ps1     odd-phase replicate render (B's noise floor)
experiments/V-DILUTE/b2_analyze.py        contrast vs replicate, same tiles, rule-3 paired
experiments/V-DILUTE/conf_potency.py      confidence-map potency per N, percent-moved
experiments/V-DILUTE/c_saturation.py     per-band ladder + where the exponent has reach
experiments/V-DILUTE/head_recheck.ps1     re-render the n_eff brackets on HEAD
experiments/V-DILUTE/maxn_crosscheck.py   max-of-N flat-field law at 13.6x leverage
experiments/V-DILUTE/clip_audit.py        clipping audit, all 31 masters, 0.0000%
experiments/V-DILUTE/commission.py        null arm, potency arm, analytic rank bias
```

---

# V-DILUTE Assignment 2 — the base-band blur hypothesis

**VERDICT: DEAD.** The base band does not carry acuity at the shipping band
count, so a plain mean over it cannot blur acuity. Flipping the base band
between `mean` and `weighted` changes acuity by **0.00% at N=22** and **+0.05%
at N=299**, and across **7 subjects spanning N = 19 → 299** the null-normalised
acuity ratio spans **0.9979 – 1.0005** (mean 0.9996, spread 0.0026) **with no
trend in N**. The N-corollary is dead with it.

Instrument: `contrast_ms.py` (ORCH's, mandated) plus `nullnorm.py` and
`baseband_spectrum.py` (mine). Binary `CBC0909947CE12F3`, built from HEAD
`5dbfefa1` with `--target-dir target-orch`. All masters linear camera-native:
**no `--auto-exposure`, no `--srgb`** (broadcast case 3). Pre-registration
`experiments/V-DILUTE/PREREG-BASEBAND.md`, committed at `5dbfefa1` **before any
render existed**.

---

## 1. The premise was falsifiable from the source before any pixels existed

The hypothesis needs one precondition: **the base band must carry acuity-band
structure at the default band count.** Four independent sources say it carries
*tone*.

| # | source | what it says |
|---|---|---|
| 1 | `pyramid.rs:129-136` | "Seven octaves takes a 3516 x 2344 quad plane down to a **28 x 19 base**." A 28-wide base over a 3516-wide plane resolves nothing above **~0.008 cyc/px**. Qualified SIGNAL is 0.17-0.25 — **21-31× higher**. |
| 2 | `--pyramid-bands` help, read to its end | ORCH quoted "Too shallow and the base band still holds structure" and stopped. It finishes: "`--pyramid-bands 2` **keeps acuity but loses the darkest densities — grey ink instead of black.**" The stated failure is **density, not softness**, and acuity is explicitly *kept*. |
| 3 | `pyramid.rs:131-136` (design intent) | "That is deliberately deep: the whole point of the exercise is that **the low frequencies must be blended rather than switched**, and stopping at four or five levels leaves a band at ~100 px scale still being selected, **which is visible as exactly the halo this is meant to remove.**" |
| 4 | the flip record ORCH cited, `pyramid.rs:3105-3112` | The quantities measured are "**global level**" and "**position-dependent structure**", both in **DN**, and it records "**with no difference in aura removal**". Those are tone quantities. |

A fifth, from ORCH's own scorer: `contrast_ms.py` uses `SIGMAS` up to 16.0,
cutting at `1/(2π·16)` = **0.00995 cyc/px**, and designates that band the
**INSTRUMENT NULL** — the band that must read ~1.000 or the comparison is void.
**The base band's entire content lies at or below that cut.** The mechanism was
proposed inside the band the instrument reserves for detecting global offsets.

I registered all of this as a premise objection *before* rendering, then
measured anyway, because a documentary argument is not a measurement.

---

## 2. The isolation, and why it needs no source change

The only difference between `--pyramid-base mean` and `--pyramid-base weighted`
at fixed `--pyramid-bands` is how the base band is combined. So the **decoded
difference between those two renders is exactly the base band's contribution**,
isolated by flags. Measuring *where in frequency that difference lives* answers
ORCH's item 1 directly.

### Where the base band's contribution actually lives

| subject | N | bands | max abs diff | rms | **share ≥0.17 cyc/px** | **share <0.010 cyc/px** |
|---|---|---|---|---|---|---|
| 109MSDCF | 22 | **7 (default)** | **2.1 DN** | 0.308 DN | 42.4% *(of quantisation)* | 52.5% |
| 109MSDCF | 22 | 2 (potency) | 1697 DN | 34.2 DN | 0.614% | 20.5% |
| bee-3-cpl | 299 | **7 (default)** | 1189 DN | 324 DN | **0.195%** | **99.301%** |
| bee-3-cpl | 299 | 2 (potency) | **13121 DN** | 1563 DN | **0.055%** | 81.0% |

Two readings, both fatal to the hypothesis:

- At N=22 the entire base-mode difference is **max 2.1 DN out of 65535** — the
  quantisation floor. Its band shares are shares of nothing; band 0 holds 42% of
  it because band 0 is the widest annulus in 2-D frequency, which is the
  signature of rounding noise, not of structure.
- **The larger the base-band perturbation, the smaller its signal-band share**:
  4.38% → 0.23% → 0.035% → 0.019%. A 13,121 DN base-band perturbation on the
  deep stack puts **0.019%** into the acuity band. The base band cannot reach
  the acuity band at any band count or any N.

### Potency — the commissioning the `--fix-ca` lesson demands

`bands 2` puts the base band at a 4 px lowpass reaching to 0.125 cyc/px, so
base-band treatment *can* matter there. It does, by **110.92×** on rms at N=22
and **13,121 DN** peak at N=299. **The null at the default is a measurement, not
a dead gauge.**

---

## 3. Acuity, null-normalised — the corpus answer (ORCH item 3)

`contrast_ms.py` removes tone with a single median scalar. The base band's
disagreement is a position-dependent **bowl**, which a global scalar cannot
remove; what survives appears as the *same* multiplicative offset in **every**
band including the null. Reading band 1 raw then credits a tone artifact as an
acuity gain — the identical error class that carried my Experiment B in
Assignment 1 (a 4% geometry artifact). So acuity is reported **divided by the
null**.

`--pyramid-base weighted` against `mean` (the shipping default), all at
`--pyramid-bands 7`:

| subject | N | raw acuity | null | **ACUITY CORR** | noise corr |
|---|---|---|---|---|---|
| coffee-bubbles | 19 | 0.9957 | 0.9975 | **0.9982** | 0.9990 |
| 109MSDCF | 22 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| 119MSDCF | 33 | 0.9998 | 0.9998 | **1.0000** | 1.0002 |
| 113MSDCF | 63 | 0.9980 | 0.9980 | **1.0001** | 1.0004 |
| foam | 100 | 1.0127 | 1.0125 | **1.0003** | 1.0001 |
| coffee-bean | 105 | 0.9866 | 0.9887 | **0.9979** | 0.8936 |
| bee-3-cpl | 299 | 1.0135 | 1.0130 | **1.0005** | 0.9973 |

**n=7, mean 0.9996, min 0.9979, max 1.0005, spread 0.0026, no trend in N.**

Two things this table earns:

- **The null caught a fabricated win.** On `bee-3-cpl` the raw band-1 number is
  **1.0135**. Quoted raw, that is a "+1.35% acuity gain from weighting the base
  band at N=299" — and it is entirely the 1.0130 global bowl. Corrected:
  **1.0005**. The raw column's spread across the corpus is 0.027, **10× the
  corrected spread**, and all of it is tone.
- **ORCH's fair point about the one-subject default is answered, and the answer
  is "it does not matter."** The default was chosen on `flower-bud-alone-cpl`
  for tonal reasons. On acuity the two base modes are indistinguishable on all
  7 subjects, so the choice cannot be costing acuity anywhere on this corpus.
  Its tonal justification is unaffected by my measurement and I have not
  retested it. (The N=299 level shift, median 11080 → 10958 for weighted, is
  **sign-consistent** with the flip record's "weighting cost −475 DN of global
  level" — corroboration of that record on a *second* subject.)

---

## 4. Band-count sweep (ORCH item 2) — prediction falsified in direction *and* in N

ORCH's prediction to falsify: "more bands → less structure left in the base band
→ sharper output, **with the gain LARGER on deep stacks**."

**N=22 (109MSDCF)** — acuity and noise paired on every row, null shown:

| bands | ACUITY | NULL | **ACUITY/NULL** | NOISE/NULL | verdict |
|---|---|---|---|---|---|
| 3 | 0.9348 | 0.9875 | 0.9467 | 1.0141 | NULL VOID |
| 4 | 0.9637 | 0.9923 | 0.9712 | 1.0095 | NULL VOID |
| 5 | 0.9864 | 0.9953 | **0.9910** | 1.0065 | valid |
| 6 | 0.9971 | 0.9979 | **0.9992** | 1.0030 | valid |
| **7** | 1.0000 | 1.0000 | **1.0000** | 1.0000 | **default** |
| 8 | 1.0004 | 1.0016 | **0.9988** | 0.9981 | valid |
| 9 | 1.0004 | 1.0016 | **0.9988** | 0.9981 | valid |

**N=299 (bee-3-cpl)**:

| bands | ACUITY | NULL | **ACUITY/NULL** | NOISE/NULL | verdict |
|---|---|---|---|---|---|
| 5 | 0.9924 | 0.9197 | 1.0790 | 1.1017 | **NULL VOID** (8% global offset) |
| **7** | 1.0000 | 1.0000 | **1.0000** | 1.0000 | **default** |
| 9 | 0.9981 | 1.0121 | **0.9862** | 0.9871 | NULL VOID (marginal) |

**Acuity saturates exactly at the shipping default and then declines.** Going
deeper than 7 buys **−0.12% at N=22** and **−1.38% at N=299** — worse, and
*more* worse on the deep stack. The prediction is falsified in direction and its
N-scaling is falsified in sign. Noise is flat across the whole valid range
(1.0065 → 0.9981), so nothing here is a noise trade.

**`bands 8` and `bands 9` are bit-identical** — `np.array_equal` True, max abs
diff 0, across all **24,724,512 decoded samples**. Per the `--fix-ca` lesson I
checked whether that zero means "inert flag" or "stage already at its floor":
it is the floor. `pyramid.rs:458` — "`level_sizes` truncates below
`MIN_LEVEL_EXTENT`". The pyramid has decimated as far as the image allows, so
`--pyramid-bands 9` requests a pyramid that cannot exist and receives the
8-level one. **Not a dead flag.**

The `absFLAT` column behaves as ORCH asked me to check: on 109MSDCF it reads
24.42 / 9.88 / 23.66 / 26.21 for bands 0/1/3/5 — falling from band 0 to band 1
(the finest band is noise-elevated, as V-LINEAR qualified) then rising into the
coarse bands (structure). Band 0 is noise on this corpus; band 1 is not.

---

## 5. Separation from `fit_to_cover` (ORCH item 4) — by construction, no arm needed

Fact 1834's mechanism is an N-dependent output resample (`k` = 0.9870 at N=22,
0.9321 at N=299). **Every comparison in this report is within-N**: same subject,
same frame count, same alignment, differing only in `--pyramid-base` or
`--pyramid-bands`. `k` is therefore identical between the two arms of every
comparison and cancels exactly. No result here can be double-counting
`fit_to_cover`, and I do not need BUILD-CROP's unity-scale arm to say so.

---

## 6. What surprised me — and one thing ORCH should know exists

### 6a. There is a *second* plain-mean-across-frames, and it is not the base band

`pyramid.rs:633-676` documents **`DEFAULT_MEAN_COARSE`**: "Number of coarsest
**Laplacian** bands merged as a plain mean across frames rather than by
selection. The base residual is not counted here; it has its own control in
`BaseBand`." Env override `STREHL_PYRAMID_MEAN_COARSE`. **It is `0` today** —
"`0` restores the previous behaviour bit-for-bit" — so it is off and cannot be
causing anything in the shipping merge.

Its docstring adjudicates ORCH's aura fix directly, and independently reaches my
conclusion:

> "**The mechanism is right and the prescribed address was not.** The fix
> proposed was to take the base band from the mean instead of the blend.
> `BaseBand::Mean` is already the default, and it already routes every base
> coefficient through the unweighted fallback, so the base band is a plain mean
> across frames today. The `BaseBand` table records the measurement that settles
> it: **both base arms removed the broad aura equally well, so the base band is
> not what carries it.**"

If ORCH still wants the broad-bowl defect addressed, **this is the knob**, not
`--pyramid-base` — and it is reachable by env var with no source edit. I have
not swept it; it is outside this assignment.

### 6b. The physical reason the premise fails, stated in the source

> "at low spatial frequencies there is nothing for selection to add, because
> **defocus is a low-pass and leaves the low frequencies of every frame near
> MTF 1.0**. There is only position-dependent bias to introduce, which is what a
> bowl is."

This is the sentence that kills the hypothesis cleanly. The premise says a mean
over "every badly defocused frame" must blur. **In the base band those frames
are not defocused** — defocus is a low-pass, so at 0.008 cyc/px every frame is
near MTF 1.0 and they all agree. Averaging agreeing observations does not blur;
it reduces noise. That is why the base band is meaned deliberately, and why
selecting there buys a halo instead of acuity.

### 6c. ORCH was half right, in a specific and useful way

The base band's contribution **does** grow steeply with N — rms **0.308 DN at
N=22 → 324 DN at N=299**, a factor of ~1000. The N-dependence he predicted is
real. It is simply **entirely tonal**: 99.301% of it sits below 0.010 cyc/px and
0.035% in the acuity band. **Right N-dependence, wrong observable.**

### 6d. Shallow pyramids fail catastrophically on deep stacks

`bands 2` at N=299 has a coarsest-EDGE null of **4.0896** — a 4× global tone
offset. That row is void as an acuity measurement and I report it as such, but
it is worth stating on its own: the "grey ink instead of black" failure the help
text warns about scales badly with N. `bands 5` at N=299 already shows an 8%
global offset (null 0.9197) against only 0.5% at N=22 (0.9953).

---

## 7. Guards honoured

- **Both rails on every master**, not just clipping: all 22 masters read
  **0.000% clipped and 0.000% black**, with sane medians (7196–11088). Assignment
  1 caught one of my own errors at the black rail with a healthy-looking p90.
- **No sharpness number without a noise number on the same pixels** — every
  table above pairs them.
- **Decoded arrays, never file digests** — `np.array_equal` over 24,724,512
  samples for the `bands 8 ≡ 9` and cross-run determinism claims.
- **Cross-run determinism verified on the deep stack at HEAD**: `bandsweep/nb7`
  and `baseband/b7.mean` are separate 299-frame runs with equivalent flags and
  are bit-identical, max abs diff 0.
- **No `.rs` file was edited.** `pyramid.rs`, `merge.rs`, `merge_cmd.rs`,
  `align_cmd.rs`, `defect_map.rs` untouched; all source read via `git show`
  through a pipe.
- Renders linear, **no `--auto-exposure`** (broadcast case 3).

## 8. What this does *not* exclude

The bee failure remains unexplained by anything in this report. I have excluded
the base band as a softness mechanism; I have **not** excluded the coarse
*Laplacian* bands (§6a), `fit_to_cover` (fact 1834), or anything in the fine-band
selection. The band-count sweep does show acuity declining slightly beyond the
default at N=299, which is a small effect in the *opposite* direction to the one
sought and is not a candidate for a 0.060 retention ratio.

## 9. Files

```
experiments/V-DILUTE/PREREG-BASEBAND.md    pre-registration + premise objection
experiments/V-DILUTE/baseband_render.ps1   flag-only base-band isolation arms
experiments/V-DILUTE/baseband_spectrum.py  where the base band's contribution lives
experiments/V-DILUTE/bandsweep_render.ps1  --pyramid-bands sweep
experiments/V-DILUTE/bandsweep_score.py    sweep scorer, acuity+noise+null
experiments/V-DILUTE/nullnorm.py           null-normalised acuity, corpus table
```
