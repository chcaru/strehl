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

---

# V-DILUTE Assignment 2 — ADDENDUM: re-check under ORCH correction #4

**Correction #4** (V-LINEAR `31eda43a`, `docs/research/V-LINEAR-BANDS.md`): the
signal/noise boundary moves by subject, **0.17 → 0.48 cyc/px**, so the fixed
"band 1 = SIGNAL" gate I was instructed to use is not licensed corpus-wide.

**RESULT OF THE RE-CHECK: re-checked, and nothing moves.** The verdict and every
headline number stand. Below is why, measured rather than argued.

## A. Two of my seven subjects were already qualified, and I used them correctly

V-LINEAR §3 measures `119MSDCF` → **0.25** and `113MSDCF` → **0.25**. Both are in
my corpus. On both, band 1 (0.17–0.25) is fully qualified SIGNAL — PASS in
0.17–0.20 *and* 0.20–0.25 (`R` = 5.898/2.790 and 4.874/2.419). So on the two
subjects where the answer is known, my band choice was correct by measurement.

The other five (`coffee-bubbles`, `109MSDCF`, `foam`, `coffee-bean`,
`bee-3-cpl`) are **unmeasured**. `bee-3-cpl`'s sibling `bee-1-cpl` measures
**0.48**, the corpus maximum — ORCH's dangerous direction, where a band I called
NOISE is largely signal.

## B. Why the verdict cannot depend on the boundary: the null is flat in *every* band

The fixed-band error bites when there is a **differential** effect between bands
and you read the wrong one. My result is a null, and a null that is flat across
the whole frequency axis is immune to moving a boundary *within* that axis.

Null-normalised ratio, `--pyramid-base weighted` vs `mean`, `--pyramid-bands 7`,
**every band reported**, EDGE row then FLAT row:

| subject | N | boundary | 0.50 | 0.25 | 0.17 | 0.08 | 0.04 | 0.02 | max dev 0.17–0.50 |
|---|---:|---:|---|---|---|---|---|---|---:|
| coffee-bubbles | 19 | — | 0.9982 | 0.9982 | 0.9982 | 0.9983 | 0.9992 | 1.0000 | **0.0018** |
| | | | 0.9990 | 0.9988 | 0.9987 | 0.9988 | 0.9987 | 0.9987 | |
| 109MSDCF | 22 | — | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **0.0000** |
| | | | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | |
| 119MSDCF | 33 | **0.25** | 1.0001 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **0.0002** |
| | | | 1.0002 | 1.0002 | 1.0002 | 1.0001 | 1.0000 | 1.0000 | |
| 113MSDCF | 63 | **0.25** | 1.0001 | 1.0001 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **0.0004** |
| | | | 1.0004 | 1.0002 | 1.0002 | 1.0002 | 1.0001 | 0.9999 | |
| foam | 100 | — | 1.0002 | 1.0003 | 1.0002 | 1.0001 | 0.9999 | 1.0000 | **0.0003** |
| | | | 1.0001 | 1.0002 | 1.0002 | 1.0000 | 0.9998 | 1.0000 | |
| coffee-bean | 105 | — | 0.9984 | 0.9979 | 0.9975 | 0.9972 | 0.9978 | 1.0000 | **0.1064** |
| | | | 0.8936 | 0.8994 | 0.9170 | 0.9149 | 0.9095 | 0.9209 | (FLAT only) |
| bee-3-cpl | 299 | ~0.48? | 0.9991 | 1.0005 | 1.0017 | 1.0008 | 0.9985 | 1.0000 | **0.0034** |
| | | | 0.9973 | 0.9966 | 0.9948 | 0.9947 | 0.9967 | 0.9974 | |

Bands 0 and 1 together span **0.17–0.50 cyc/px** and therefore contain *every*
boundary V-LINEAR observed. On six of seven subjects the deviation anywhere in
that range, at either site type, is **≤ 0.0034**. **No choice of boundary within
V-LINEAR's measured range changes the verdict on those six.** They need no
per-subject qualification, which is a stronger statement than qualifying them.

## C. The boundary-free restatement of the confinement result

"99.301% below 0.010 cyc/px / 0.035% in the SIGNAL band" used a band label that
is no longer licensed. Restated against **fixed absolute frequencies**, using the
corpus **minimum** boundary 0.17 as a conservative upper bound (every subject's
boundary is ≥ 0.17, so its share above its own boundary is ≤ its share above
0.17):

| subject | N | max abs diff | rms | share ≥ 0.17 cyc/px | share ≥ 0.48 cyc/px |
|---|---:|---:|---:|---:|---:|
| coffee-bubbles | 19 | 213.9 DN | 22.4 | 6.288% | 0.015% |
| 109MSDCF | 22 | **2.1 DN** | 0.308 | 45.727% *(of quantisation)* | 0.132% |
| 119MSDCF | 33 | 13.7 DN | 1.90 | 0.940% | 0.003% |
| 113MSDCF | 63 | 10.0 DN | 1.22 | 2.590% | 0.007% |
| foam | 100 | 149.4 DN | 16.6 | 2.535% | 0.006% |
| coffee-bean | 105 | **1803.7 DN** | 437.0 | **0.425%** | 0.001% |
| bee-3-cpl | 299 | 1188.8 DN | 324.0 | **0.313%** | 0.001% |

**Wherever the base band's contribution has real amplitude, ≤6.3% of it lies
above the corpus-minimum boundary and ≤0.015% above the corpus-maximum.** The
one large high-frequency share (109MSDCF, 45.7%) is a share of **2.1 DN** — the
quantisation floor, whose white spectrum concentrates in the widest annulus.
This row is boundary-free by construction and does not move.

## D. The band-count sweep is band-independent too

The sweep conclusion was also read off band 1. Re-read in every band,
null-normalised, EDGE sites:

**109MSDCF (N=22)**

| bands | 0.50 | 0.25 | 0.17 | 0.08 | 0.04 | null |
|---|---|---|---|---|---|---|
| 3 | 0.9499 | 0.9467 | 0.9475 | 0.9577 | 0.9768 | 0.9875 |
| 5 | 0.9972 | 0.9910 | 0.9861 | 0.9862 | 0.9920 | 0.9953 |
| **7** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 9 | 0.9982 | 0.9988 | 0.9996 | 1.0006 | 1.0013 | 1.0016 |

**bee-3-cpl (N=299)**

| bands | 0.50 | 0.25 | 0.17 | 0.08 | 0.04 | null |
|---|---|---|---|---|---|---|
| 5 | 1.0814 | 1.0790 | 1.0751 | 1.0653 | 1.0455 | **0.9197 VOID** |
| **7** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 9 | 0.9858 | 0.9862 | 0.9868 | 0.9891 | 0.9946 | 1.0121 |

**The ordering of arms is identical in every column.** "Acuity saturates at the
shipping default and does not improve beyond it" reads the same at 0.50, 0.25 and
0.17 cyc/px, so it holds whatever boundary these subjects turn out to have. The
`bands 5` row at N=299 stays void on its null (8% global offset), as before.

## E. The one row that does move, and what it actually is

**`coffee-bean` (N=105)** is the exception and I flag it rather than bury it. Its
FLAT-site ratio is **0.894–0.921 uniformly across all six bands** while its EDGE
ratio is flat at 0.997–0.998. In my original table this appeared only as "noise
corr 0.8936" and I did not comment on it.

**A ratio that is uniform across every band from 0.50 down to 0.02 cyc/px is a
gain change, not a filtering change.** A filter has a frequency response; this
does not. Combined with `coffee-bean` having the **largest** base-band
contribution in the corpus (rms 437 DN) of which only **0.425%** lies above
0.17 cyc/px, the reading is a position-dependent **level/gain** difference in
flat regions — i.e. tone again, the same thing the base band carries everywhere
else in this report. It is not an acuity effect: EDGE is unmoved at every
frequency.

I am **not** claiming that as qualified, because `coffee-bean`'s boundary is
unmeasured. What I can say without qualification is that **whatever band is
signal on `coffee-bean`, its EDGE sites moved by ≤0.28% at every frequency**, so
the base-band verdict holds there too.

## F. What I am withdrawing from the wording of the original section

- The band labels "**NOISE**" (0.25–0.50) and "**SIGNAL**" (0.17–0.25) as used in
  §2, §3 and §4 of the Assignment 2 report were inherited from ORCH's
  instruction and are **not licensed corpus-wide**. Read them as bare frequency
  ranges. The numbers attached to them are unaffected; only the labels are.
- The aggregate "mean 0.9996, spread 0.0026" over seven subjects is a summary of
  **seven independent within-subject nulls**, not a cross-subject band ratio, so
  it does not fall foul of V-LINEAR's "no cross-subject `R`" rule. I state that
  explicitly rather than leave it inferred. Every ratio in this report compares
  two arms **within one subject**.
- Nothing in §5 (`fit_to_cover` separation), §6 (`DEFAULT_MEAN_COARSE`, the
  MTF-1.0 argument), or §7 (guards) touches a band criterion.

## G. Files

```
experiments/V-DILUTE/bandagnostic_recheck.py  null-normalised ratio, every band, 7 subjects
experiments/V-DILUTE/boundary_free.py         energy share above 0.17 and 0.48 cyc/px
experiments/V-DILUTE/sweep_recheck.py         band-count sweep re-read in every band
```

---

# ADDENDUM G — ORCH's noise-correction guard, applied to my own sweep

ORCH, V-NEVERWORSE broadcast: *"Raw band power counts noise as sharpness. One
arm read +0.142 sharper raw and −0.134 softer once noise-corrected — a sign
flip. If your statistic can be inflated by noise, correct it or say plainly it
cannot be trusted in flat regions."*

My section-4 ACUITY column is a **raw** band EDGE std and is exactly that shape.
Instrument: `experiments/V-DILUTE/noisecorrected.py`. EDGE-site variance is
structure + noise; FLAT-site variance is noise alone, at the same tiles chosen
on the reference so the choice is common to every arm. Corrected statistic is
`sqrt(max(edge² − flat², 0))`, then null-normalised as before.

## G.1 The guard PASSES — no sign flip anywhere

| subject | N | bands | raw dev | **corrected dev** | sign |
|---|---|---|---|---|---|
| 109MSDCF | 22 | 3 | −0.0533 | **−0.0564** | same |
| 109MSDCF | 22 | 5 | −0.0090 | **−0.0096** | same |
| 109MSDCF | 22 | 8/9 | −0.0012 | **−0.0011** | same |
| bee-3-cpl | 299 | 5 | +0.0790 | **+0.0785** | same |
| bee-3-cpl | 299 | 9 | −0.0138 | **−0.0139** | same |

Agreement is within **0.0002** at N=299 and within 0.018 at N=22 in the worst
(0.25–0.50) band. **Not one row changes sign, and none changes magnitude
materially.** Reason it survives where V-NEVERWORSE's arm did not: my acuity is
measured at **EDGE sites**, where structure dominates noise, and I reported the
noise column on the same pixels beside every acuity number from the start. The
defect ORCH describes bites hardest on **flat**-region statistics.

## G.2 But the guard exposed a defect of my own — I quoted a row I had voided

Section 4 states *"deeper than 7 buys −0.12% at N=22 and **−1.38% at N=299** —
worse."* The −1.38% is the `bands 9 / N=299` row, and **my own table at line 650
marks that row `NULL VOID (marginal)`** — its instrument null reads **1.0121**,
a deviation of 0.0121 against ORCH's stated 0.005 validity tolerance, **2.4×
over**. I marked it invalid and then quoted its number in the prose conclusion.
That is the same shape as the errors this session keeps turning up: a gate
applied, then bypassed.

**I withdraw the −1.38% figure.** It is not noise-inflated — G.1 proves that —
it is **unlicensed**, which is a different and worse problem.

Checked whether null-normalisation repairs it. My repair is legitimate only when
the null offset is a **pure gain**, i.e. uniform across frequency (Addendum E's
discriminator: uniform across bands = gain, band-selective = filter). Per-band
reading of that row is `0.9858 / 0.9862 / 0.9868 / 0.9891 / 0.9946 / 1.0121` —
a monotone 2.6% drift across frequency, **not** uniform. So it is a genuine
filtering difference *plus* a global offset that a scalar cannot separate.
**Genuinely void. No repair available.**

## G.3 What survives, stated against the gate

- **N=22 rows `bands 6, 8, 9` pass the null gate outright** (0.9979, 1.0016,
  1.0016 — all inside 0.005). Noise-corrected deviations **−0.0010, −0.0011,
  −0.0011**. So *"more bands than the default does not buy acuity"* is licensed
  at N=22, noise-corrected, magnitude ≈ **−0.1%** — indistinguishable from zero
  and certainly not a gain.
- **At N=299 no non-reference sweep row passes the gate** (bands 5 → 0.9197,
  bands 9 → 1.0121). The deep sweep therefore licenses **no acuity number in
  either direction**. I previously read a *number* off it; I should have read
  only *"uninformative."*
- **The corpus result (section 3) is unaffected.** Its four in-tolerance rows
  (coffee-bubbles 0.9975, 109MSDCF 1.0000, 119MSDCF 0.9998, 113MSDCF 0.9980)
  pass outright; the three out-of-tolerance rows (foam 1.0125, coffee-bean
  0.9887, bee-3 1.0130) are repairable because Addendum B showed their residual
  is **flat to ≤0.0034 across every band** — a pure gain, which is exactly the
  condition under which dividing by the null is valid. Verdict unchanged:
  **0.9979–1.0005, no trend in N.**
- **`bands 8 ≡ bands 9` bit-identical** (24,724,512 samples) needs no gate at
  all — it is an equality, not a ratio.

**The headline is unchanged: the base-band blur hypothesis is DEAD.** It never
rested on the voided rows; it rests on the corpus null and on the geometry.
The hypothesis predicted *more bands → sharper, and the gain LARGER on deep
stacks.* At N=22 the gain is −0.1%; at N=299 it is unmeasurable. Neither is the
predicted positive, N-growing gain.

## G.4 Verifier audit — the presence-test defect

ORCH asked every lane to check for verifiers that test the **presence of a
conclusion string**. Audited all **24** V-DILUTE scripts:

- **`assert` statements: 2 total**, both array-shape preconditions
  (`baseband_spectrum.py:66`, `vd_metrics.py:30`). Neither certifies a claim.
- **Conclusion-string tests: zero.** No script tests for or emits `refuted`,
  `confirmed`, `DEAD` or `ALIVE`.

**Clean — but the honest flip side is that this is not a virtue.** My scripts
*print numbers*; every conclusion in this document was drawn by hand from that
output. So I have no verifiers to be fooled **and no machine check on my
conclusions either** — which is precisely how G.2 happened: a row correctly
marked `NULL VOID` by the script, then quoted anyway by the human writing the
prose. **The defect ORCH found in V-NEVERWORSE's verifier and the defect I
found in my own section 4 are the same failure at different stations:** a gate
that fires and is then not honoured downstream.

---

# Addendum H — the candidate-set control: the premium factorises, and only
# one factor is attackable

Assignment: find the candidate-set control that kills the selection premium
(V-NEVERWORSE facts 1843-1845 at `f1f40150`) without losing sharpness.
Offline in NumPy over real aligned stacks; no Rust touched.

Pre-registration at `81ee69fa` (round 1) and `cc0061cd` (round 2), both
committed **before** the arms they score were run.

Gauge inherited verbatim from V-NEVERWORSE. Commissioning gate, every run:
`argmax` premium at N=79 on 112MSDCF must reproduce 240.70. Measured 240.95
(0.1% off) on the primary seed, and 244.93 / 245.51 / 245.37 (1.8-2.0%) on
three further twin seeds.

## H.1 The headline: the premium is a PRODUCT of two things, and candidate-set
## control can only touch the smaller one

    premium(arm, N)  =  floor(N)  x  curse(arm, N)

**`floor(N)` — the cost of copying one frame instead of averaging N.** It is
what the `random` arm pays, and `random` and `oracle` agree to 0.6%, which is
what theory demands: with no focus signal a decorrelated score *is* random.
No control over the candidate set can go below it, because it is not a defect
of *how* a frame is chosen — it is the arithmetic of using one sample where
the mean uses N.

**`curse(arm, N)` — the winner's curse.** In `vn_pyr.merge` the score is
`sq_i = smooth5(lap_i^2)` and the value copied is `lap_i`: **the score
contains the very coefficient it selects** (2D centre tap `(6/16)^2 =
0.1406`). This is the whole of the attackable prize, and it is bounded.

Measured, 112MSDCF:

| N | floor (`random`) | `argmax` | curse | phi measured |
|---|---|---|---|---|
| 19 | 7.23 | 23.12 | **3.20** | 0.611 |
| 39 | 21.60 | 79.63 | **3.69** | 0.385 |
| 79 | 58.43 | 240.95 | **4.12** | 0.160 |

and 119MSDCF, independently:

| N | floor | `argmax` | curse |
|---|---|---|---|
| 16 | 6.66 | 19.41 | **2.92** |
| 32 | 18.84 | 63.41 | **3.37** |

**The consequence ORCH needs before anyone writes Rust: the entire prize
available to candidate-set control at N=79 is 4.12x, not 240x.** The other
58.43x is the floor and is not going anywhere while the merge copies single
frames. An arm that reached the floor exactly would still read 58x above the
mean. This bounds the assignment.

The curse does grow with depth — 3.20 -> 3.69 -> 4.12 on 112MSDCF, 2.92 ->
3.37 on 119MSDCF — so it is a genuine N-dependent defect and worth attacking.
But it grows roughly as `N^0.18`, while the floor grows roughly as `N`.

## H.2 The floor is `N` diluted by gate abstention — measured, not inferred

Round 1 refuted my own prediction that the floor equals `N` (kill condition
#2 fired: measured 58.4, predicted 79). I proposed that pixels where no frame
clears `gate * beta[k] * var` fall back to the unweighted mean, giving
`floor = phi + (1 - phi) * N`. **Solving that for `phi` using the number it
is meant to explain is circular**, so `vd_abstain.py` measures `phi`
independently as the energy-weighted fraction of pixels whose shipping weight
stack sums to zero:

| N | phi measured | floor predicted | floor observed | ratio |
|---|---|---|---|---|
| 19 | 0.611 | 8.00 | 7.23 | 0.904 |
| 39 | 0.385 | 24.37 | 21.60 | 0.886 |
| 79 | 0.160 | 66.51 | 58.43 | 0.879 |

The independently measured abstention reproduces the observed floor to within
a **consistent 12%**, with the correct monotone decline (deeper stacks have
fewer pixels where nothing clears the gate). I regard the mechanism as
confirmed and the residual 12% as unexplained — most likely because
`BETA`-weighting only approximates each level's true energy share, and
abstention is spatially correlated with the low-variance pixels that carry
least power. **Stated as a partial confirmation, not a clean one.**

## H.3 The ranked arms, N=79 on 112MSDCF

Sharpness is noise-corrected (`band(real) - band(twin residual)`) and reported
in **four** bands, pre-committed in round 2 so that a loss pushed out of the
scored band cannot hide. 112MSDCF's signal/noise boundary is **0.25 cyc/px**
(measured in `vd_band.py`; V-LINEAR had not covered this subject), so
0.10-0.15, 0.17-0.20 and 0.20-0.25 are **qualified signal** and **0.25-0.30
is not creditable as acuity on this subject**. "worst" is the minimum over
the three qualified bands.

| arm | premium | curse | worst qualified band | verdict |
|---|---|---|---|---|
| `mean` | 1.00 | — | 0.0072 | control; N-invariant and useless |
| `random` / `oracle` | 58.43 / 58.78 | 1.00 | 0.032 / 0.097 | **the floor** |
| `xpool1` | 61.35 | 1.05 | 0.622 | at floor, −38% |
| `pool2` | 64.83 | 1.11 | 0.708 | at floor, −29% |
| `punctured` = `xpool0` | 64.45 | 1.10 | 0.630 | at floor, −37% |
| `pool1.5` | 74.07 | 1.27 | 0.849 | 3.06x, −15% |
| **`pool1`** | **122.71** | **2.10** | **0.974** | **1.84x, −2.6%** |
| `pool0.5` | 212.64 | 3.64 | 1.028 | 1.06x, no loss |
| `shipping` | 226.39 | 3.87 | 1.000 | reference |
| `argmax` | 240.95 | 4.12 | 0.966 | worse on **both** axes |
| `capK8` / `capK4` | 225.59 / 225.32 | 3.86 | 0.988 / 0.980 | **lever refuted** |
| `coarse1` / `coarse2` | (N=19) 7.45 | 1.03 | 0.405 / 0.399 | a heavy pool in disguise |
| `pwin2_1` / `pwin2_2` | 32.82 / 21.84 | — | 0.192 / 0.109 | below floor by averaging; guts sharpness |
| `lvl0mean` | 1.29 | — | 0.014 | **my round-2 hypothesis, refuted** |

## H.4 Three of ORCH's five levers are refuted, one works, one is a rename

- **"Explicitly cap the effective candidate count" — REFUTED.** `capK4` =
  225.32 and `capK8` = 225.59 against shipping 226.39. Capping the losers
  changes nothing, because the premium is set by *who wins*, not by how many
  frames lose. This is the single most useful negative result here: it is the
  most obvious thing to implement and it does not work.
- **"Pre-smooth the focus measure before the max" — WORKS**, and is the only
  lever that does. It is the `pool<sigma>` family and it traces the entire
  frontier on its own.
- **"Select once at a coarse scale and propagate" — a rename of the above.**
  `coarse1` and `coarse2` land on the same floor as `pool2` with worse
  sharpness (0.405 vs 0.708). Expanding a coarse score *is* a heavy spatial
  pool; it buys nothing extra and costs resolution in the depth map.
- **"Take the max over a sufficient statistic of the through-focus curve" —
  BROKEN AS SPECIFIED.** For a curve peaked at frame `m`, a leave-one-out
  score at `i = m±1` still contains `f(m)` while the score at `i = m` does
  not, so `argmax` of any LOO estimator lands on the **neighbour** of the true
  peak whenever `f(m) > ~2 f(m±1)`. The quadratic correction `(4 m1 − m2)/3`
  does not repair it (0.2742 vs 0.2757). This would have been an expensive
  discovery in Rust.
- **"Restrict candidates to a neighbourhood of a regularised depth estimate"
  — works only via its pooling.** `pwin` and `winavg` go *below* the floor
  (32.8, 21.8, 13.2) because they average several frames, but they pay for it
  exactly where the mean pays: 0.19, 0.11, 0.11 worst-band. They are the mean
  in local clothing.

## H.5 Exact self-exclusion is correct theory and a worse design

The curse is *exactly* the score kernel's centre tap, so `xpool<s>` removes
exactly that — the combined `gauss(s) o smooth5` centre weight, measured by
filtering a delta rather than assumed. **Commissioning: `xpool0` reproduces
`punctured` to ten significant figures (63540349.2089).** The machinery is
right.

And it loses. `xpool1` reaches the floor (curse 1.05) at worst-band 0.622,
while `pool1.5` gets curse 1.27 at 0.849. Removing the centre tap removes the
score's *signal* along with the curse: that tap carries 14% of the focus
evidence, so the depth map degrades faster than the noise does. **The
theoretically exact fix is dominated by the crude one.** I would not have
predicted this and it is the reason to measure before implementing.

## H.6 What I got wrong (round 2, pre-registered at `cc0061cd`)

I predicted that because Laplacian level 0 nominally carries 0.25-0.50 cyc/px
and `vd_signal.py` measured 112MSDCF at `S/y = 0.00` there, **replacing
selection with a plain mean at level 0 would cost nothing** in the qualified
bands. I pre-committed the four-band report specifically so this could not be
scored on a band of its own choosing.

**It is refuted, and not marginally.** `lvl0mean` reads 0.0373 at 0.20-0.25,
0.0872 at 0.17-0.20 and **0.3238 even at 0.10-0.15** — a band it should barely
touch. Level 0 carries most of the reconstructed detail at *every* band I
scored. The error is that a Laplacian level is not a band-pass: level 0 is
`I − expand(reduce(I))` with a 5-tap binomial whose response is `cos^4(pi f)`,
still passing ~27% of amplitude at 0.125 cyc/px. **My level-to-band mapping
was wrong, and every inference I drew from it dies with it.** The "empty band"
finding stands as a statement about the *scene*, but it licenses nothing about
which *level* may be averaged.

## H.7 The recommendation, specified for implementation

**Pool the focus score spatially with a Gaussian of sigma = 1.0 px before the
max, at every pyramid level, and change nothing else.**

    sq_i = smooth5(lap_i^2)                  # unchanged
    sq_i = gaussian(sq_i, sigma = 1.0)       # ADD THIS LINE
    w_i  = select_weight(...)                # unchanged, from pooled score
    out  = sum_i w_i * lap_i / sum_i w_i     # unchanged, copies UNPOOLED lap

The value copied stays `lap_i`; only the score that ranks the frames is
pooled. That is the whole change.

Measured effect, 112MSDCF N=79: premium 226.39 -> 122.71 (**1.84x**), worst
qualified band 0.974. 119MSDCF N=32: 60.53 -> 34.28 (**1.77x**), worst
qualified band 0.940.

`sigma` is the single knob and the frontier is monotone in it: 0.5 -> 1.06x
for nothing, 1.0 -> 1.84x for 2.6%, 1.5 -> 3.06x for 15%, 2.0 -> 3.49x
(at the floor) for 29%. **Anything past sigma = 2 is strictly wasteful** —
pool2, pool4 and pool8 all sit at 63.8-64.8 while sharpness keeps falling
(0.708, 0.421, 0.381). The floor is reached at sigma = 2 and there is nothing
below it.

## H.8 What I could not measure, stated plainly

1. **`pool1` is not free, and I will not round it to free.** Its 0.17-0.20
   deficit is 0.9737 +/- 0.0021 over four independent twin seeds — 12 sigma
   below 1.0, small but real. It gains at 0.20-0.25 (1.037). On 119MSDCF the
   cost is larger, −6.0%. **Under a strict reading of "sharpness must not
   fall", `pool1` fails and only `pool0.5` passes, at 1.06x.** I report the
   frontier rather than nominate a winner that clears the bar by choosing its
   own band.
2. **Pooling does not restore N-invariance and I do not claim it does.**
   `pool1/shipping` is 0.510 / 0.503 / 0.542 at N = 19 / 39 / 79 — a constant
   factor, not a flattening. The premium still grows about `N^1.6` after the
   fix. Per ORCH's own guard, N-invariance is necessary but not sufficient;
   here I have neither, only a constant improvement.
3. **Sharpness cannot be compared across N** and I have not done so.
   `pick(n, k)` decimates over a matched range, so smaller N means a coarser
   focus step and a different merge problem. `pool1`'s worst band rises
   0.858 -> 0.911 -> 0.976 with N, which *suggests* pooling gets cheaper at
   depth, but that comparison is confounded by focus step and I am not
   claiming it.
4. **Two subjects, both ~0.25 boundary.** 112MSDCF and 119MSDCF agree, but
   `bee-1-cpl` (boundary 0.48) and `flower-bud-alone-cpl` (0.17) are not in
   V-NEVERWORSE's bundle and I could not test them. On a subject with real
   content at 0.30-0.35 the pooling trade may differ, and I did not measure
   it.
5. **All of this is on a synthetic twin with no focus signal.** That is
   correct for isolating manufactured noise and it is the inherited gauge, but
   it means the premium numbers are not a claim about any real photograph. The
   sharpness numbers *are* on real pixels.
6. **The `prem_sig` question from round 1 is unresolved.** Shipping recovers
   `6.54e7 > 0` at 0.30-0.35 on real frames, which may qualify the "empty
   band" claim. It does not affect H.1-H.7, because the premium is defined on
   the twin where the band is empty by construction.
---

# Addendum I — coffee-bubbles band qualification, and the deletion of my
# input data

Written in response to ORCH correction #5.

## I.1 What correction #5 does and does not do to Addendum H

**Nothing.** Checked, not assumed, and stated explicitly so "re-checked and
unchanged" can be told from "not re-checked":

- The premium numbers are measured on a **synthetic twin with no focus signal
  by construction**, which is why band qualification cannot bear on them —
  ORCH's own partition says so, and H.8 item 5 already said so before the
  correction arrived.
- The **sharpness** numbers were already qualified per subject. H.3 used
  112MSDCF's measured boundary of **0.25 cyc/px** (`vd_band.py`) and
  explicitly refused to credit 0.25-0.30 as acuity. V-LINEAR's independent
  `depthqual.py` now reports 112MSDCF **R = 1.089 FAIL(noise)** at 0.30-0.40.
  **Two independent methods agree**, so H.3's exclusion was correct and no
  number in Addendum H moves.

## I.2 coffee-bubbles IS band-qualifiable, and it FAILS at 0.30-0.35

ORCH: "`coffee-bubbles` -- the source of the 27.2% -- has never been
band-qualified at all." It can be, and `vd_xsig.py` does it with a statistic
that needs no noise model.

Split the real frames into two **interleaved** halves, run the same operator on
each independently, and take the normalised cross-power per band. Sensor noise
is independent between halves and cancels in the numerator; real static scene
content is common to both and survives. The result is the fraction of a band's
power that is REAL, 0 = noise, 1 = signal.

    coffee-bubbles N=19    0.10-0.15  0.17-0.20  0.20-0.25  0.25-0.30  0.30-0.35
    mean                      0.2710     0.0291     0.0204     0.0018    -0.0035
    shipping                  0.5284     0.1437     0.0775    -0.0060    -0.0209
    pool1                     0.5442     0.1536     0.0922    -0.0033    -0.0043

    null scatter (max |frac| over all bands on a flat field)          0.0222

**At 0.30-0.35 the merged output reads −0.021, inside the instrument's own
null scatter of 0.022. coffee-bubbles carries no measurable real content
there.** Its boundary is about **0.20 cyc/px** — the lowest yet recorded on
this corpus, below `leaf-2-cpl` and level with `flower-bud-alone-cpl`.

So the **27.2%** is measured in a band that is noise on the subject that
carries it, exactly as the **−44.6%** was. I am not extrapolating from the
withdrawal of one to the other; this is a direct measurement of the second.

## I.3 An independent corroboration of H.7 that I did not design

`pool1` is not below `shipping` in any band, and is **above** it in all three
that carry real content: 0.5442 vs 0.5284, 0.1536 vs 0.1437, 0.0922 vs 0.0775.
This is a third subject, a model-free statistic, and a different failure mode
from the noise-corrected band power used in H.3 — and it agrees. It does not
license a cross-subject ratio and I am not quoting one.

## I.4 My input data was deleted mid-lane

`C:\dev\strehl-out\V-NEVERWORSE\bundle\112MSDCF.npz` (0.8 GB) and
`119MSDCF.npz` (0.3 GB) were deleted at **22:48 tonight**, between my last
measurement and my next one. `coffee-bubbles.npz` and all four `.json`
sidecars survive. No `.npz` copy exists anywhere on C: or D:.

Consequences, stated plainly:
- **Addendum H is not currently reproducible.** Its numbers were taken from
  those files and I stand behind them, but the 240.70 commissioning gate
  cannot be re-run until the bundles are rebuilt.
- The same applies to **V-NEVERWORSE facts 1843-1845**, which are measured on
  the same deleted inputs.
- I could not test 112MSDCF with `vd_xsig.py`, so **H.8 item 6 stays open**.
  The `prem_sig = 6.54e7` question is now unresolvable without a rebuild.

Rebuild is possible in principle — `vn_commission.py` builds the bundles and
the surviving `.json` sidecars retain every alignment parameter — but it
requires re-running the align pipeline from `D:\personal\macro`.

**The general lesson, which is the same shape as V-LINEAR declining to delete
`V-LINEAR\lintiff`: a FINISHED lane's outputs may be a RUNNING lane's inputs.**
Ownership of a directory is not the same as exclusive readership of it. The
question to ask before deleting is not "is this lane done" but "does anything
still read this", and it is answered by grepping for the path.

## I.5 Conclusion-flip mutation test of my own gates (ORCH correction #5,
## item 3)

Run on `vd_xsig.py`, the instrument carrying I.2. I predicted **before
running** that the `contiguous` arm would defeat both gates, and wrote the
reason into the arm's docstring: both gates use a *static* synthetic field,
and a static field is invariant to how frames are split, so no static arm can
detect a split that decorrelates focus-varying content.

**The prediction was half right, and I report the wrong half as a miss.**

| arm | NULL | POT | verdict @0.30-0.35 | signal band @0.10-0.15 | outcome |
|---|---|---|---|---|---|
| identity | ok | ok | −0.0209 | 0.5284 | baseline |
| samehalf | FAIL | ok | 1.0000 | 1.0000 | caught by NULL |
| noconj | ok | FAIL | −0.0042 | −0.0054 | caught by POTENCY |
| **contiguous** | **ok** | **ok** | 0.0081 | **0.1617** | **MISSED at green** |

`contiguous` defeated both gates as predicted, but it did **not** flip the
verdict under test, because that verdict is a null and the mutated reading is
also ~0. What it did instead was **collapse the band that actually carries
content by 3.3x — 0.5284 to 0.1617 — at fully green gates.**

That is still a defect of my instrument, and in the dangerous direction: it
understates real content, which would wrongly disqualify a band. Tonight's
claim happens to be immune because tonight's claim is a null. **The next
positive claim would not have been.**

**Repaired.** A third gate, `SWEEP`, plants a tone whose amplitude ramps with
frame index — the one property a focus bracket has that a static field does
not. An interleaved split gives both halves nearly equal mean amplitude and
passes at 0.9958; a contiguous split gives them 0.239 and 0.761 and fails.
All three mutations are now caught, and the coffee-bubbles verdict is
unchanged under the stricter instrument.

I also note the scoring defect this exposed in my *test*, not my instrument:
my first pass scored only "did the headline verdict flip", so it printed
`contiguous` as "green, verdict held" — a pass. It was only because I also
printed a band I was not testing that the corruption was visible. **A
mutation test that checks only the conclusion under test has the same blind
spot as the presence-test it is meant to replace.** The scorer now fails an
arm that corrupts any reported band, not just the one in the headline.
---

# Addendum J — the premium gauge is blind to bands 1-6

Written in response to ORCH's `averaged` tabulation.

## J.1 First, a correction to something I told ORCH ten minutes ago

I reported that my independent implementation disagreed with his band-0
figure — 93.4% against his 36.4% on `coffee-bubbles` — and flagged it as a
discrepancy worth investigating. **It was my defect, and I withdraw the
number.**

`vd_prem_run.py` prints the fitted noise model, and on this subject it reads
`read2 = 8413.89, photon_gain = 0.00000`. The variance fit has collapsed to
pure read noise with no photon term. That puts an enormous constant floor
under the gate, which is exactly what drives level-0 abstention to 93%.
**His 36.4% stands; my 93.4% is void on this subject.**

The gap that let it through is inherited and worth fixing wherever this
harness is reused: the guard is

    if gph < 0:  refuse

which refuses a *negative* photon gain but passes `gph == 0.0`, and zero is
just as degenerate. A fit that has lost its photon term should be refused, not
merely one that has gone negative.

**Bands 1-6, however, are independently CONFIRMED.** On real frames I measure
**0.00% abstention at every level 1 through 6**, against his 0.0-3.1%. That
finding does not depend on the variance fit in the way band 0 does, and it
holds. His design guidance is correct: bands 1-6 are the selecting regime.

## J.2 The finding: an arm aimed at bands 1-6 cannot be scored by the premium

ORCH's point 1 says candidate-set control has to act in bands 1-6. That is a
testable instruction, so I partitioned my recommended arm into the two regimes
he warned must not be conflated:

- `poolhi1` — pool the focus score at levels **1-6 only**, level 0 untouched
- `poollo1` — pool the focus score at level **0 only**, levels 1-6 untouched

`coffee-bubbles`, N=19. Commissioning intact: `argmax` = 24.37 against
V-NEVERWORSE's 24.82 for this subject at this N, 1.8% off.

| arm | premium | vs shipping | 0.20-0.25 band |
|---|---|---|---|
| shipping | 23.19 | — | 1.0000 |
| `argmax` | 24.37 | +5% | 1.0506 |
| `pool1` (all levels) | 11.89 | **1.95x** | — |
| **`poolhi1` (levels 1-6)** | **23.36** | **1.00x — nothing** | 0.9757 |
| **`poollo1` (level 0)** | **11.81** | **1.96x — all of it** | 0.0672 |

**Every bit of the premium reduction comes from level 0. Pooling levels 1-6
moves the premium by 0.7%, which is noise.**

And `poolhi1` is not inert — it changes the picture, moving the 0.20-0.25
band to 0.9757. **It changes the merge in exactly the regime ORCH wants
targeted, and the premium statistic cannot see it.**

## J.3 Why, and what it means for the acceptance criteria

The premium is defined as reconstructed power at **0.30-0.35 cyc/px**. A
Laplacian level is not a band-pass (Addendum H.6), and level 0 dominates that
frequency. So the premium is, in effect, **a level-0 statistic**.

Two independent confirmations, on two subjects:
- `lvl0mean` on 112MSDCF: replacing selection with a plain mean at level 0
  *alone* collapses the premium from 226.39 to **1.29** — to the floor. Levels
  1-6 contribute essentially nothing to it.
- `poolhi1` / `poollo1` on coffee-bubbles, above.

**So two of ORCH's instructions are mutually unsatisfiable as written:**

1. acceptance criterion 1 — "the premium must fall measurably at N=79 against
   the 240.70 baseline"; and
2. the new design guidance — "candidate-set control has to act in bands 1-6".

Any arm that acts only in bands 1-6 will score **no effect** on the premium
gauge, and any arm that scores well on that gauge is, by construction, doing
its work in band 0. This is not an argument that either instruction is wrong.
It is that **the gauge cannot adjudicate the target**, and one of the two has
to give.

This also re-frames facts 1843-1845. The premium — 2.16x/6.79x/24.82x and
23.24x/80.78x/240.70x — is measured at 0.30-0.35 on the reconstruction, so it
is a measurement of **level-0 behaviour**. That is precisely the band ORCH's
own tabulation shows to be atypical: mean 25.8% averaged and a 0.0-72.5%
spread, against a uniform ~0% in bands 1-6. The premium literature describes
the one band that does not behave like the others.

## J.4 What I could not do

- **ORCH's point 3 — the N axis — is blocked.** It needs the bundles deleted
  at 22:48. `coffee-bubbles` at N=19 is the only stack I still hold, so I
  cannot pre-register or test an N-ordering.
- **The J.2 partition needs re-running on a subject with a healthy variance
  fit.** coffee-bubbles' fit is degenerate (J.1), and while the level-0/1-6
  split is corroborated independently by `lvl0mean` on 112MSDCF, I would not
  ship this on the degenerate subject alone.
- **coffee-bubbles sharpness columns are unusable** and I quote none of them
  except 0.20-0.25. The 0.17-0.20 ratios explode (36.94 for `pool1`) because
  the subject's boundary is ~0.20, so the noise-corrected denominator is near
  zero. That is consistent with I.2 and is a property of the subject, not a
  bug, but it makes ratios in that band meaningless here.
---

# Addendum K — the built soft gate is NOT on the default path, and it is not
# my design

## K.1 STOP: `STREHL_SOFT_GATE` cannot affect a default `strehl stack`

Before reconciling anything I checked whether the built gate is on the path my
lane and the whole quality effort actually measure. **It is not.** Evidence
chain, all read rather than inferred:

- `merge_cmd.rs:2868-2869` dispatches
  `MergeBackend::Pyramid => run_pyramid(opts)` and
  `MergeBackend::Estimator => run_estimator(opts)`.
- `MergeBackend::Pyramid` is **the default** — its own doc comment says
  "Reachable, and **the default**."
- `fn run_estimator` begins at `merge_cmd.rs:2937` and contains the **only
  production `Estimator::new` in the repository**, at `merge_cmd.rs:4065`.
  That is the constructor which resolves `SOFT_GATE_ENV`.
- `fn run_pyramid` spans `merge_cmd.rs:5280-5734`. Within it, `SOFT_GATE`,
  `SoftKernel` and `new_soft` are **absent**. `Estimator` appears only in
  comments referring to the *other* arm ("the `--merge estimator` path's",
  "the same resolver the estimator uses"). `soft` appears only as
  `SelectMode::SoftPower`, which is the pyramid's own exponent weighting and a
  different mechanism entirely.
- `crates/strehl-core/src/pyramid.rs` contains **no** reference to
  `Estimator`, `SoftKernel` or `SOFT_GATE`.

**So `STREHL_SOFT_GATE=gaussian` on a default `strehl stack` invocation is a
no-op.** It is reachable only under `--merge estimator`.

**This needs to reach V-KILLB0 before it renders.** If it scores the gate on
`bee-1-cpl` without also selecting the estimator backend, it will measure
exactly zero difference on every axis and may report the gate as harmless, or
as doing nothing — when it was never engaged. That is the same failure family
as ORCH clearing the `--exposure` defect on a file hash when 0 of 98,898,048
samples differed: **a no-op arm reads CLEAN on every structural axis.** The
cheap guard is to confirm the two arms' outputs are not bit-identical before
scoring either.

A second consequence: the estimator backend is a **different merge**, so a
soft-gate result obtained there does not transfer to the shipping pyramid
merge without a further argument.

*Checked and NOT a defect:* the flag table at `main.rs:968-1016` looks
inverted, with `--pyramid-*` tagged `MergeBackend::Estimator`. It is correct —
`main.rs:1076` reads `!(*given && backend == *refused_under)`, so the field is
the backend the flag is **refused under**, not the one it belongs to. I raise
it only because it reads as a bug and someone else will trip over it.

## K.2 My design is not the built kernel, and the difference is the axis

ORCH's point 1 asks me to say plainly if I have re-derived what ships. I have
not, and the resemblance is superficial.

| | built soft gate | my `pool1` |
|---|---|---|
| form | `exp(-0.5 (gap/T)^2)` | `gaussian(sq, sigma)` |
| domain | **response margin**, in units of `Gate::tolerance()` | **image plane**, in pixels |
| acts across | frames at one pixel | neighbouring pixels, per frame |
| changes | how sharply admission decays with score margin | what the score *is*, before any max |
| winner | keeps weight 1.0 at `gap = 0`; raises **losers** | can change **which frame wins** |
| abstention | admits sub-threshold frames, so it **reduces** band 0's 25.8% | leaves it essentially unchanged |

Both are Gaussians; neither is a Gaussian in the other's variable. **They are
orthogonal and composable**, and on ORCH's own framing they treat different
diseases: the soft gate is M111's remedy for the flat-region/abstention defect,
mine is aimed at the winner's curse.

## K.3 The difference stated as a falsifiable prediction

My measurements say admission control is the wrong lever for the premium:

- The premium is a **winner's curse**, not an admission-count effect. `oracle`
  — an independent score, with N and admission **unchanged** — cut it
  240.95 -> 58.78, **4.10x**.
- **Candidate capping is refuted**: `capK4` 225.32 and `capK8` 225.59 against
  shipping 226.39. Changing how many frames are admitted does essentially
  nothing.
- Arms that admit and average more trade premium for sharpness along one
  curve: `pwin2_1` 32.82 at 0.192, `pwin2_2` 21.84 at 0.109, `winavg4` 13.19
  at 0.111, plain mean 1.00 at 0.0072.

**PREDICTION, pre-registered here before V-KILLB0 scores it.** The Gaussian
soft gate will land on the admission/averaging curve above, not on the point
`pool1` occupies:

1. As `T` grows it approaches the plain mean — premium toward 1.0 and fine
   grain toward fact 1844's 0.229x. It is a knob on the select-average
   continuum.
2. It will **not** reach ~1.8-2.0x premium reduction at >=0.97 sharpness,
   because it does not decorrelate the score from the copied coefficient. Every
   admitted frame's weight is still computed from that frame's own noisy
   score, so the 4.12x curse at N=79 is untouched.
3. Its largest effect will be where abstention is high — **band 0**, mean
   25.8% and 0.0-72.5% across subjects — and it will do least in bands 1-6,
   which are 0.00-0.29% averaged. That is the opposite of where ORCH's own
   table says the premium lives.

**If V-KILLB0 measures the soft gate reducing the premium while holding
sharpness above 0.97, prediction 2 is refuted and my design is superseded.**
I will report that as a refutation without widening the interval.

## K.4 What I cannot do

I cannot test any of this myself. V-KILLB0 owns scoring the built gate, and I
would not have the data anyway — 112MSDCF and 119MSDCF were deleted at 22:48
and `coffee-bubbles` has a degenerate variance fit (J.1). K.3 is a prediction,
not a measurement, and it is offered so it can be refused.
---

# Addendum L — K.1 measured on pixels, and a verdict of mine that I withdraw

## L.1 The soft gate is a no-op on the default merge: 0 of 24,724,512 samples

Addendum K.1 argued from source that `STREHL_SOFT_GATE` cannot reach the
default pyramid backend. That verdict lived **only in prose**, which is the
defect ORCH attributes to V-KILLB0 -- no mutation can catch a claim no check
is pinned to. It is now measured. Predictions were committed at `4dca927d`
(`experiments/V-DILUTE/PREREG-SOFTGATE.md`) **before** any arm ran.

Subject `109MSDCF`, N=22, 20 s per render, six arms:

    arm  invocation                                        differing samples vs ref
    A    default backend, no env                           reference
    A'   identical repeat                                  0 / 24,724,512   (0.000%)
    B    default + STREHL_SOFT_GATE=gaussian               0 / 24,724,512   (0.000%)
    C    default + --pyramid-exponent 4.0             14,046,047 / 24,724,512 (56.810%)
    D    --merge estimator                                 reference for E
    E    --merge estimator + STREHL_SOFT_GATE=gaussian 23,980,319 / 24,724,512 (96.990%)

All four pre-registered predictions held:

- **A == A'** -- the writer embeds no timestamp, so byte comparison is a valid
  instrument here. Without this, `A == B` could never have been trusted.
- **A == B** -- **the soft gate changes nothing on the default backend.** Not
  "changes little": zero samples of 24,724,512, max |d| 0.0 DN.
- **A != C** -- sensitivity. The harness sees a change of mean 1.25 DN, which
  is **fifteen times smaller** than the effect the gate has where it is live.
  So B's stillness is not the instrument failing to look.
- **D != E** -- specificity, and this is the arm that makes L.1 mean what it
  says. The env var is **strongly live on the estimator**: 96.99% of samples,
  mean |d| 18.2 DN, max 1012 DN. So `A == B` is *not* explained by a
  misspelled or dead env var. It is explained by the pyramid path never
  consulting it.

**This is the same signature as ORCH's `--exposure` defect cleared on a file
hash when 0 of 98,898,048 samples differed.** Mine is 0 of 24,724,512. A no-op
arm reads CLEAN on every structural axis, and both of us would have shipped
the reading had the potency control been left out.

`experiments/V-DILUTE/vd_softgate_gate.py` now holds this as four gates that
**exit non-zero** when the claim goes stale, so a future wiring of the gate to
the pyramid path breaks a check rather than silently falsifying a document.

## L.2 The trap is conditional, and silent in BOTH directions

`strehl stack --help` states the backend is **inferred from the flags** when
`--merge` is absent, and that `--gate` -- 275 call sites by ORCH's own sweep --
is one of the inferring flags. Confirmed in the run log, which names the
backend and the reason:

    B  ->  merge backend : pyramid (default)
    C  ->  merge backend : pyramid (inferred from --pyramid-exponent; ...)
    D  ->  merge backend : estimator (--merge)

So the outcome depends on flags the caller passed for unrelated reasons:

- a harness with **no** estimator flags gets the pyramid, and the soft gate is
  inert -- it will measure "no difference" and may report the gate harmless;
- a harness that passes `--gate` and **not** `--merge` gets the **estimator**,
  where the gate is live at 18 DN mean -- and it will attribute an
  estimator-backend result to the shipping merge.

Both failures are silent and they point opposite ways. The cheap guard, for
any lane scoring this: **confirm the two arms are not bit-identical before
scoring either**, and read the `merge backend :` line out of the run log rather
than assuming.

## L.3 I WITHDRAW the strong form of my coffee-bubbles verdict

I.2 said coffee-bubbles reads -0.021 at 0.30-0.35 against a 0.022 null
scatter, and I wrote that the 27.2% was "**decided, not merely pending**".
V-LINEAR now measures the same subject at the same slice as
**R = 1.542, CI [1.181, 2.154], MARGINAL** -- a CI that excludes the noise
floor. That is a genuine disagreement between two instruments, and mine is the
one with an untested confound:

**`vd_xsig.py` splits a FOCUS stack into interleaved halves.** Each half
therefore carries **half the focus-sampling density**. At depths falling
between sampled planes the two halves resolve slightly different slices, so
real content decorrelates between halves and my statistic charges it to noise.
**The bias runs low -- the direction of the disagreement.**

My commissioning could not have caught this. The NULL arm was a *flat field*,
which has no focus structure to decorrelate, and the POTENCY arm was a static
tone. Both tested whether I detect signal and reject noise; **neither tested
the focus-stack-specific confound.** That is ORCH's "commissioning sensitivity
is not commissioning specificity" wearing new clothes, in my own harness, one
addendum after I ran a mutation audit and called it repaired.

So: **the word "decided" is withdrawn.** The status is ORCH's -- MARGINAL, and
not quotable as evidence. The operational conclusion is unchanged, because he
and I reach "do not quote the 27.2%" by different routes.

**The check that would settle it, which I cannot run:** point `vd_xsig.py` at
`bee-1-cpl`, which V-LINEAR rates R = 5.311 PASS at this slice. If my
instrument reads a 5.311 PASS subject as noise, it is biased low and I.2 is
refuted outright rather than merely withdrawn. It needs an aligned bundle;
mine were deleted at 22:48 and rebuilding 299 frames is not free. **Offered to
whoever has that bundle already.**

What this does *not* touch: the pool1/shipping band comparison on
coffee-bubbles used bands **0.10-0.25**, well below the disputed slice, and a
low bias would if anything credit *more* bands with real content, extending
the range over which `pool1 >= shipping` rather than reversing it.

## L.4 Re-checked against ORCH's new band rule

His rule: no sharpness, softening or acuity claim is quotable without naming
the band and the subject's qualification at it. Checking my own corpus:

- **Addendum H's sharpness numbers are on `112MSDCF`**, which he now bars for
  acuity claims. They survive, because they were taken as "worst of three
  **qualified** bands", all at or below the **0.25** boundary I measured --
  none in the barred 0.30-0.40 slice. I state the band explicitly rather than
  claim compliance.
- **Addendum H's premium numbers are on the synthetic twin**, which his
  disposition exempts by construction.
- If anything my boundaries are **understated** for the reason in L.3, which
  is the conservative direction: I scored in fewer bands than I was entitled
  to, not more.

---

# Addendum M — reconciling my design against the shipped kernel

ORCH asked two specific questions. Both have measured answers, and neither
answer is the one the code's comments assume.

## M.1 Sharing `Gate::tolerance()` unchanged is NOT behaviourally neutral

The claim in the build is that Gaussian and Exponential "both share
`Gate::tolerance()` exactly, so only the kernel SHAPE varies over an unchanged
calibrated axis". Measured on `109MSDCF`, N=22, one binary, `--merge estimator`,
`--n-eff-map` on both arms:

    n_eff                       hard gate    soft gaussian
    mean                            4.674           19.295
    median                          5.000           22.000
    p10 / p90                    3.0 / 7.0      8.0 / 22.0
    % of plane at n_eff <= 1        3.936            0.023
    % of plane at n_eff >= 20       0.219           79.233

**The tolerance is shared; the behaviour is not.** The same calibrated `T` that
admits a mean of 4.674 frames under a hard decision admits **19.295 of 22**
under the Gaussian — 88% of the stack — and 79.2% of the plane runs at
`n_eff >= 20`. So switching kernel does not vary shape over a fixed axis; it
varies shape *and* effective width together, and the two cannot be attributed
apart.

The reason is structural: `T` was calibrated as the point where a response gap
stops being meaningful **for a boolean admit/reject**. Re-used as a Gaussian
scale it is far too wide, because `exp(-0.5 (gap/T)^2)` is still 0.607 at
`gap = T` and only reaches zero at f32 underflow, near `gap = 13 T`. The
Exponential reaches underflow near `gap = 87 T` and is therefore far wider
again — the heavy-tail direction M111 §15.8 measured destroying the photograph.

**Under my model this is the single most consequential fact about the built
gate, and it is not about the premium at all.** Fact 1844 established the plain
mean as perfectly N-invariant and useless, destroying fine grain to 0.229x. A
kernel running at `n_eff = 19.3 of 22` is **most of the way to that mean**
before anyone scores a pixel. My Addendum K.3 predicted, before this was run,
that the soft gate would trace the admit-more/averaging curve toward the plain
mean rather than reaching `pool1`'s corner. **That prediction is corroborated
at the shipped tolerance, without `T` being widened at all.**

Recommendation, for whoever sequences `merge.rs`: keep one calibrated axis --
forking it would be worse -- but **do not describe equal `T` as a controlled
comparison.** Either match the kernels at a stated moment (equal half-weight
gap, or equal mean `n_eff` on a reference plane) and say which, or report
`n_eff` beside every kernel result so the width difference is visible. I would
also expect a Gaussian scale of roughly `T/3` to reproduce hard-gate `n_eff`,
though I have not measured that and it should not be quoted until someone does.

## M.2 `selection_inflation` on the integer count: inert today, a trap when armed

**First, the correction that matters most: it decides nothing at present.**
`SELECTION_INFLATION = 1.0` (`merge.rs:136`) and both branches of
`selection_inflation` return 1.0 (`:154-156`), which the doc comment states
outright. So the integer-vs-`n_eff` choice cannot currently help or harm any
render. It is a latent decision, not an active one, and ORCH's framing --
"the kind of detail that silently decides whether the fix helps" -- overstates
its present reach. It is worth fixing anyway, for the reason below.

**When it is armed, keying it on the integer count is wrong.** The
justification in the code is that "exactly one frame contributed" is a discrete
fact about selection. That is true on the hard path, where `n` is the admitted
count. On the soft path it silently changes meaning, because `fold_inner`
skips a frame only at `raw <= 0.0` (`:1905`) and increments `self.n[i]`
afterwards (`:1971`). **So `n` counts every frame whose weight merely survives
f32 underflow** — within ~13 T for the Gaussian, ~87 T for the Exponential.

The measured consequence, from the table above: the `n_eff <= 1` population
falls from **3.94%** of the plane to **0.023%**, a **99.4% loss of reach** —
and since the integer count is always `>= n_eff`, the true figure for
`selection_inflation(n)` is that or lower. The term would fire on essentially
nothing, and the pixels it stops firing on are precisely the selecting pixels
it exists to serve. (The map is written as u16, so `<= 1` includes rounding up
from below 1.5 — which inflates the soft figure, making 0.023% conservative.)

This is the *same* hazard the code already fixed one line earlier: `:2634-2639`
moved the `sqrt` divisor from `n` to `eff` precisely because "dividing by the
raw admitted count while `value` divides by `wsum` would report a noise floor
the estimator does not have". That argument applies unchanged to the inflation
factor sitting in the same expression, and it was not applied there.

**Recommendation:** when fact 448's curve is armed — 1.0770, 1.0591, 1.0454,
1.0383, 1.0319, 1.0293, 1.0286, 1.0220 for n = 1..8 — evaluate it at `n_eff`,
not at the integer count. The doc already requires "a decaying function of `n`,
not a two-valued one", and a decaying function takes a fractional argument
natively, so this costs nothing and removes the discontinuity at the same time.
On the hard path `soft_n_eff_at` returns the integer count exactly, so this is
a strict generalisation and changes no hard-path behaviour.

## M.3 Which regime my design acts in — correcting the framing

ORCH: "a design that only moves band 0 touches almost nothing a viewer sees,
and a design aimed at bands 1-6 is aimed at 0.03-0.29% of coefficients."

That reads the `averaged` table as if it bounded every design. It bounds only
designs that change **admission** — what happens where no frame cleared the
floor. `pool1` does not change admission. It changes **which frame wins**, by
pooling the ranking score before the max, and every coefficient in the
selecting regime is eligible. That regime is ~100% of bands 1-6 and ~74% of
band 0 — the complement of his figures, not those figures.

So: **the soft gate is an admission design and is bounded by his table;
`pool1` is a selection design and is not.** They are not competing for the
same coefficients, which is the sharper form of K.2's "orthogonal axes".

His caution is worth restating in my own words because it cuts against me too:
`averaged` says nothing about `n_eff`, and I have not restated it as such. What
M.1 adds is that `n_eff` is now *measured* on one subject, and it is 19.3 of 22
under the soft Gaussian.

## M.4 Liveness control, confirmed for V-KILLB0

`STREHL_SOFT_GATE=gausian` panics at `merge.rs:1457` with
`unknown soft-gate kernel "gausian"; known kernels: gaussian, exponential`,
exit **101**. The typo control V-KILLB0 plans will work as intended on this
build. Note it must be run **with `--merge estimator`**: on the default pyramid
backend the env var is never resolved, so the typo does not fail and the
liveness control silently passes while proving nothing (Addendum L).
