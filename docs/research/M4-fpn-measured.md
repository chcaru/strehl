# M4 — Dark-frame noise, fixed-pattern floor, and the sqrt(N) pillar (MEASURED)

Date: this session. Machine: Ryzen 9 9950X3D / 64 GB / RTX 5090, Windows 11.
Tool: `experiments/m2-fpn` (Rust 1.98.0 MSVC, `--release`), `rawler` 0.7.2.
Corpus: `D:\macro-dark-frames\{118..128}MSDCF`, 11 folders x 22 ARW.
First 2 frames of each folder discarded as requested (stabilisation), **220
frames analysed**. Whole run: 39.3 s wall, peak working set **2992 MB** and
peak sampled private commit **3001 MB** — the two agree, so the working-set
figure is not inflated by file-backed pages. 20 unit tests, `cargo clippy
--all-targets -- -D warnings` clean.

This is experiment 2 from `SYNTHESIS.md` §8 — the go/no-go on the project's
central design pillar.

---

## 0. Verdict

**Frame averaging buys exactly sqrt(N) on this sensor — but only while the
noise being averaged is temporal, and in the dark that is not true for long.**
Raw N-frame averaging of dark frames follows a slope of **-0.2888** at base
ISO, not -0.5, and the departure is measurable at **N = 2**. The curve
asymptotes at a fixed-pattern floor of **0.377 DN** (ISO 100), reached at
**N ≈ 7**; past that, more frames buy essentially nothing. Subtracting a master
bias built from *disjoint* frames removes **90–100% of that floor's variance**
and restores the slope to **-0.5019** at base ISO and **-0.497 … -0.502 across
all eleven ISOs**, with every individual point within 0.5% of ideal. So the
pillar is sound *conditionally*: either the merge stage subtracts a bias frame,
or it must not claim more than a **2.6x** noise reduction in the darkest parts
of the image no matter how many frames it is given. For normally-exposed
content this never binds — above roughly **12 DN** of signal, photon shot noise
after a 20-frame average still exceeds the fixed-pattern floor (§7). The design
assumption is therefore safe for the image and unsafe only as an unconditional
claim.

**The finding that should actually worry the project is not in this data.**
These are dark frames, so they measure *offset* fixed-pattern noise (DSNU) and
nothing else. **PRNU — the multiplicative, signal-proportional fixed pattern —
is invisible here and is the component that would bite in exactly the lit,
low-contrast regions where M2 showed the argmax defect.** A textbook 0.3–1%
PRNU at 5000 DN would be 15–50 DN of fixed pattern against 7.6 DN of
20-frame-averaged shot noise, and it would not average away. That is
`UNVERIFIED` and unmeasurable without flat fields, which is why
`docs/captures-needed.md` §4 now requests them.

---

## 1. Folder → ISO map (MEASURED, from EXIF)

Discovered, not assumed. Every frame in every folder was read individually.

| Folder | ISO | Exposure | Within-folder consistency |
| --- | --- | --- | --- |
| 122MSDCF | 50 | 1/100 s | uniform (all 22, incl. the 2 discarded) |
| 118MSDCF | 100 | 1/100 s | uniform |
| 123MSDCF | 200 | 1/100 s | uniform |
| 126MSDCF | 250 | 1/100 s | uniform |
| 119MSDCF | 400 | 1/100 s | uniform |
| 125MSDCF | 500 | 1/100 s | uniform |
| 124MSDCF | 640 | 1/100 s | uniform |
| 120MSDCF | 800 | 1/100 s | uniform |
| 127MSDCF | 1000 | 1/100 s | uniform |
| 121MSDCF | 1600 | 1/100 s | uniform |
| 128MSDCF | 2000 | 1/100 s | uniform |

**Status: MEASURED.** No folder is mixed; no averaging across settings was
needed. All 242 files carry `ILCE-7CM2` and 1/100 s. The ISO ladder brackets
the claimed ISO 400 second base densely on both sides (200 / 250 / **400** /
500 / 640), which is what makes §5 possible. The owner was asked for 20 frames
at ISO 100 and 20 at ISO 400 and supplied eleven ISOs; §5 exists only because
of that over-delivery.

---

## 2. Sanity gate — all eleven folders are genuinely dark

Active area only (7032x4688 of the 7168x5120 buffer), all four planes, all 20
frames. The tool counts its own samples and asserts the total equals
`4 * 3516 * 2344 * 20 = 659,320,320`, so a geometry slip that let the synthetic
zero padding in could not pass silently. It matched for all 11 folders.

| ISO | mean | median | min | max | p99.99 | 3x3 grid spread |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | 512.218 | 512 | 487 | 570 | 524 | 0.0316 |
| 100 | 512.231 | 512 | 487 | 567 | 524 | 0.0322 |
| 200 | 512.261 | 512 | 459 | 626 | 535 | 0.0573 |
| 250 | 512.225 | 512 | 442 | 666 | 540 | 0.0768 |
| 400 | 512.190 | 512 | 473 | 710 | 529 | 0.0622 |
| 500 | 512.192 | 512 | 466 | 792 | 533 | 0.0744 |
| 640 | 512.234 | 512 | 448 | 860 | 538 | 0.1033 |
| 800 | 512.167 | 512 | 439 | 921 | 545 | 0.1182 |
| 1000 | 512.158 | 512 | 417 | 1111 | 553 | 0.1585 |
| 1600 | 512.213 | 512 | 346 | 1382 | 577 | 0.2178 |
| 2000 | 512.148 | 512 | 304 | 1717 | 593 | 0.2229 |

**Status: MEASURED. All eleven pass; none excluded.** Every folder sits on the
declared black level with the median exactly 512, deviations running in both
directions, and a 3x3 spatial spread of 0.03–0.22 DN — i.e. below a quarter of
one temporal sigma even at the worst ISO. There is no gradient, no elevated
corner, no amp glow. The p99.99 tail sits 12–81 DN above the median and tracks
ISO, which is the expected behaviour of a handful of warm pixels amplified by
gain, not a leak.

The min/max spread is mildly asymmetric on the high side (ISO 100: -25 / +55).
**ARGUED:** that is the hot-pixel population of §6 showing up in the extremes;
it involves order 10^1–10^2 pixels out of 8.24 million per plane and does not
move any statistic below the 99.99th percentile.

All statistics in this document are computed in `f64`, are never clamped at
zero, and are computed *before* black subtraction — the noise straddles 512 and
roughly half the deviations are negative.

---

## 3. Spatial and temporal sigma are kept separate

A prior claim in this project was retracted for computing a *spatial* sd within
a patch and reporting it as a *temporal* sd across frames, and `AGENTS.md` rule
10 now forbids comparing the two. This document compares them constantly, so it
owes an explanation.

**Rule 10's hazard does not apply to a dark frame, and §2 is the proof.** The
rule exists because a spatial sd over an image region carries scene structure
that a temporal sigma does not. A dark frame has no scene. §2 measured that
directly: the 3x3 grid of cell means spans 0.03–0.22 DN, under a quarter of one
temporal sigma even at the worst ISO, so there is no gradient or structure for a
spatial sd to pick up. What is left in the spatial sd of a dark frame is FPN
plus averaged temporal noise, and separating those two is the entire purpose of
the experiment.

The comparison is then checked rather than assumed. §5 builds a model purely
from the temporal statistics and uses it to predict spatial sds it was never
fitted to; it lands within 0.13%. Had scene structure been present, that
agreement would not exist. **Every place this document sets a spatial quantity
against a temporal one, it does so on dark frames and reports the cross-check.**

The two are also named separately in the code (`spatial_mean_sd` vs
`temporal_stats`), in the struct fields, and in every table below:

- **sigma_temporal** — per-pixel sd across the 20 frames, pooled as
  `sqrt(mean(per-pixel variance))`. Pooling *variances* is what makes it
  unbiased. The tool also prints `mean(per-pixel sd)`, which is biased low by
  the chi distribution (0.9456 vs 1.0048 at ISO 100 plane R) and is explicitly
  labelled "not the number to quote".
- **sigma_spatial** — sd across pixels of a single image, used for the N-frame
  averages and for sigma_FPN.

The unit test `spatial_and_temporal_measure_different_things` exists to stop the
two being silently interchanged.

**Negative control (MEASURED).** Before any real number was believed, the
estimators were run against synthetic data with planted values:

```
 sigma_FPN    sigma_t    N  recovered FPN    recovered t  uncorrected      verdict
      3.00       8.00   20         2.9957         8.0049       3.4897         PASS
      0.50       8.00   20         0.5068         8.0082       1.8610         PASS
      0.00       8.00   20         0.0581         8.0031       1.7905         PASS
     10.00       2.00   20         9.9871         2.0215       9.9973         PASS
      2.00      20.00   20         2.0092        19.9994       4.9026         PASS
      1.00       5.00   10         1.0053         5.0070       1.8755         PASS
```

The third row is the one that matters: with **zero** FPN planted, the
bias-corrected estimator recovers 0.058 DN while the uncorrected estimator
reports a wholly fictitious 1.79 DN "fixed-pattern floor". Every FPN number in
this document is the corrected one.

---

## 4. The sigma-vs-N curve — the go/no-go

Model: `x_i(p) = FPN(p) + n_i(p)`. Averaging N frames leaves
`FPN(p) + (1/N) sum n_i(p)`, so the spatial sd of the N-frame average should
fall as `sqrt(sigma_FPN^2 + sigma_temporal^2 / N)` — 1/sqrt(N) at first, then
asymptotic at sigma_FPN. Disjoint subsets at each N (falling back to 4
overlapping random draws only at N = 12 and 16, where 20 frames cannot supply
two disjoint sets, and flagged as such in the output).

### 4.1 Raw averaging (ISO 100, plane R) — MEASURED

| N | spatial sd (DN) | subset scatter | subsets | ideal 1/sqrt(N) | excess |
| --- | --- | --- | --- | --- | --- |
| 1 | 1.0758 | 0.0044 | 20 | 1.0758 | +0.0000 |
| 2 | 0.8076 | 0.0040 | 10 | 0.7607 | +0.0469 |
| 3 | 0.6965 | 0.0049 | 6 | 0.6211 | +0.0754 |
| 4 | 0.6327 | 0.0032 | 5 | 0.5379 | +0.0948 |
| 6 | 0.5620 | 0.0022 | 3 | 0.4392 | +0.1228 |
| 8 | 0.5237 | 0.0042 | 2 | 0.3804 | +0.1434 |
| 12 | 0.4851 | 0.0013 | 4* | 0.3106 | +0.1746 |
| 16 | 0.4609 | 0.0014 | 4* | 0.2690 | +0.1920 |
| 20 | 0.4468 | — | 1 | 0.2406 | +0.2063 |

\* overlapping draws.

- **Fitted slope: -0.2873** over all N; **-0.3849** over N ≤ 4.
- **Departs from -0.5 at N = 2** — the first N whose excess (0.0469) exceeds its
  own subset scatter (0.0040), by a factor of 12.
- At N = 20 the measured sd is **1.86x** the ideal.

**Status: MEASURED.** The pillar, taken literally and applied to raw dark
frames, **fails, and fails early.**

### 4.2 The same frames with a disjoint master bias subtracted — MEASURED

Master built from frames 0–9; subsets drawn only from frames 10–19, so no frame
is ever both in the master and in the thing being corrected. The master carries
`sigma_t^2/10` of its own noise into every point; that is a constant offset,
not FPN, so it is removed in quadrature to give the "master-free" column.

| N | sd (DN) | scatter | subsets | master-free | ideal 1/sqrt(N) |
| --- | --- | --- | --- | --- | --- |
| 1 | 1.0532 | 0.0046 | 10 | 1.0041 | 1.0041 |
| 2 | 0.7761 | 0.0023 | 5 | 0.7081 | 0.7100 |
| 3 | 0.6586 | 0.0009 | 3 | 0.5769 | 0.5797 |
| 4 | 0.5919 | 0.0007 | 2 | 0.4994 | 0.5020 |
| 6 | 0.5177 | 0.0000 | 1 | 0.4087 | 0.4099 |
| 8 | 0.4753 | 0.0000 | 1 | 0.3535 | 0.3550 |

- **Fitted slope: -0.5017.** Every point is within **0.5%** of ideal.

**Status: MEASURED.** With the fixed pattern removed, the sensor's temporal
noise is independent frame to frame to the limit of this measurement. The
pillar is not wrong about the physics; it is wrong about what is left in a raw
frame.

**This is also the placebo required by rule 11, and it is why the §4.1
asymptote can be attributed to FPN rather than to the estimator.** §4.1 and
§4.2 run the same code on the same frames at the same ISO with the same subset
logic. The only difference is the subtraction of an image built from *other*
frames. If the asymptote were an artifact of `sigma_vs_n_curve` — of the subset
scheme, of the spatial sd, of the log-log fit — subtracting a bias frame could
not remove it. It removes it completely, at all eleven ISOs.

Two further controls back this up:

- **Planted data through the production code path.** The tests
  `the_production_curve_reports_the_planted_slope_and_asymptote`,
  `the_production_curve_gives_minus_half_when_no_fpn_is_planted` and
  `the_production_bias_subtracted_curve_restores_minus_half` call
  `sigma_vs_n_curve` and `sigma_vs_n_bias_subtracted` — the same functions
  `analyse_plane` calls — on synthetic frames with known FPN and temporal
  noise, and assert the reported slope, per-point model agreement and
  deconvolved asymptote. With zero FPN planted the production curve returns
  -0.5; with 3.0 DN planted it returns a flattened slope and recovers 3.0.
- **The self-correction placebo.**
  `split_half_removes_planted_fpn_and_self_correction_fakes_it` shows that
  building the master from the frames it corrects collapses the residual to
  `0.000000` — the spectacular fake result the disjointness rule exists to
  prevent — while the honest disjoint version lands on the predicted temporal
  floor.

### 4.3 Both slopes at every ISO — MEASURED

| ISO | slope, raw | slope, bias-subtracted |
| --- | --- | --- |
| 50 | -0.2911 | -0.4966 |
| 100 | -0.2888 | -0.5019 |
| 200 | -0.4100 | -0.4990 |
| 250 | -0.4163 | -0.5018 |
| 400 | -0.3306 | -0.5020 |
| 500 | -0.3589 | -0.4991 |
| 640 | -0.3949 | -0.5004 |
| 800 | -0.4033 | -0.5018 |
| 1000 | -0.4219 | -0.5010 |
| 1600 | -0.4353 | -0.4991 |
| 2000 | -0.4374 | -0.5010 |

The raw slope is never -0.5 and is worst exactly where the product operates
(base ISO), because that is where temporal noise is smallest relative to the
fixed pattern. The corrected slope is -0.5 to within 0.7% at all eleven ISOs
including both gain modes.

---

## 5. The two components, measured directly

sigma_FPN is bias-corrected: `sigma_FPN^2 = var(temporal_means) -
sigma_temporal^2 / N`. Where that comes out negative the tool reports "below
resolution" rather than a small positive number.

| ISO | sigma_temporal (DN) | sigma_FPN (DN) | FPN/temporal | N at the floor | max achievable reduction |
| --- | --- | --- | --- | --- | --- |
| 50 | 0.9866 | 0.3730 | 0.3781 | 7.0 | 2.64x |
| 100 | 0.9845 | 0.3768 | 0.3828 | 6.8 | 2.61x |
| 200 | 1.7416 | 0.3420 | 0.1968 | 25.8 | 5.08x |
| 250 | 2.1629 | 0.4053 | 0.1877 | 28.4 | 5.33x |
| 400 | 1.1986 | 0.3756 | 0.3137 | 10.2 | 3.19x |
| 500 | 1.4680 | 0.3966 | 0.2705 | 13.7 | 3.70x |
| 640 | 1.8080 | 0.3939 | 0.2184 | 21.0 | 4.58x |
| 800 | 2.2465 | 0.4633 | 0.2066 | 23.4 | 4.84x |
| 1000 | 2.8085 | 0.5036 | 0.1798 | 30.9 | 5.56x |
| 1600 | 4.4054 | 0.6996 | 0.1592 | 39.5 | 6.28x |
| 2000 | 5.5330 | 0.8592 | 0.1558 | 41.2 | 6.42x |

sigma_temporal and sigma_FPN are per-plane means of R/G1/G2/B; "N at the floor"
is `(sigma_temporal/sigma_FPN)^2`, the N at which the two terms are equal.

**Cross-check against §4 (VERIFIED).** The two routes agree. At ISO 100 plane R,
§5 gives sigma_t = 1.0048 and sigma_FPN = 0.3862; the model then predicts a
1-frame spatial sd of `sqrt(0.3862^2 + 1.0048^2) = 1.0764` against the measured
1.0758 (0.06% apart) and a 20-frame sd of `sqrt(0.3862^2 + 1.0048^2/20) =
0.4462` against the measured 0.4468 (0.13% apart). The asymptote of the §4
curve — its limit as N grows, not its N = 20 point — *is* sigma_FPN. The N = 20
point of 0.4468 still carries `sigma_t^2/20` and sits 16% above the 0.3862 floor;
mistaking one for the other overstates the floor, and the test
`the_production_curve_reports_the_planted_slope_and_asymptote` asserts the
distinction on planted data.

**MEASURED:** sigma_FPN grows with ISO in DN (0.373 → 0.859) but far more
slowly than sigma_temporal (0.987 → 5.533), so the *ratio* improves with gain.
**ARGUED:** that is the signature of an offset pattern imposed before or at the
readout amplifier — it is amplified along with everything else, while the read
noise gains a large additive contribution from the high-gain stage.

**MEASURED:** G2 and B — the *bottom* row of the RGGB quad — carry visibly more
FPN than R and G1 at high ISO (ISO 2000: 0.999 and 1.002 against 0.722 and
0.714). At base ISO the four planes agree to within 10%. **ARGUED:** a
row-dependent readout path is the obvious explanation, but this experiment
cannot distinguish that from a colour-filter-dependent dark current and does
not try.

---

## 6. How much of the floor is calibratable

Split-half: master bias from frames 0–9, subtracted from the average of frames
10–19. **Disjoint, and that is the whole point** — a master built from the same
frames it corrects subtracts their temporal noise too. The unit test
`split_half_removes_planted_fpn_and_self_correction_fakes_it` plants known FPN
and shows the self-corrected residual collapsing to `0.000000` while the
honest, disjoint one lands on the predicted temporal floor.

| ISO | un-subtracted sd | bias-corrected sd | pure-temporal floor | residual FPN | FPN variance removed |
| --- | --- | --- | --- | --- | --- |
| 50 | 0.4861 | 0.4409 | 0.4412 | 0.0520 | 98.1% |
| 100 | 0.4898 | 0.4388 | 0.4403 | below resolution | ~100% |
| 200 | 0.6499 | 0.7825 | 0.7789 | 0.1089 | 89.9% |
| 250 | 0.7949 | 0.9647 | 0.9673 | below resolution | ~100% |
| 400 | 0.5347 | 0.5354 | 0.5360 | 0.0468 | 98.4% |
| 500 | 0.6085 | 0.6558 | 0.6565 | 0.0061 | 100.0% |
| 640 | 0.6946 | 0.8081 | 0.8085 | 0.0254 | 99.6% |
| 800 | 0.8479 | 1.0021 | 1.0047 | below resolution | ~100% |
| 1000 | 1.0241 | 1.2535 | 1.2560 | below resolution | ~100% |
| 1600 | 1.5659 | 1.9759 | 1.9702 | 0.1478 | 95.5% |
| 2000 | 1.9533 | 2.4695 | 2.4744 | 0.0421 | 99.8% |

**Status: MEASURED. The master bias removes 90–100% of the fixed-pattern
variance at every ISO, and typically ≥ 98%.** The corrected sd lands on the
predicted pure-temporal floor `sqrt(2 * sigma_t^2 / 10)` to within 0.4% in
every row, which is what "nothing left but temporal noise" looks like.

**But read the third and fourth columns before celebrating.** At nine of the
eleven ISOs the corrected sd is *larger* than the un-subtracted one — at ISO
2000 by 26%. That is not a failure of the correction; it is the master's own
noise. Subtracting an M-frame master injects `sigma_t^2 / M`. The correction is
net-positive only when

```
M > (sigma_temporal / sigma_FPN)^2
```

which is the **same number** as "N at the floor" in §5: **7 frames at ISO 100,
10 at ISO 400, 42 at ISO 2000**. The 10-frame master used here clears the bar at
ISO 50/100 (9–10% improvement) and fails it everywhere else.

**DERIVED, and this is the shippable design rule:** a dark-frame subtraction
feature must build its master from at least `(sigma_t/sigma_FPN)^2` frames for
the ISO in use, or it will make the image worse. A 32-frame master covers every
ISO up to 1600. **ARGUED:** since a master bias is captured once and reused
across many stacks, there is no reason to be stingy — 64 frames costs one
minute of lens-cap time and removes the constraint entirely.

---

## 7. What this means for the merge stage

The M2 baseline showed the argmax selector producing output **1.25x noisier
than a single frame** in a flat region. The proposed fix is to combine frames
rather than select among them, which rests on averaging buying sqrt(N). §4 says
it does, once the fixed pattern is gone. The question is whether the fixed
pattern is even relevant at photographic signal levels.

**DERIVED** (using the assumed `g = ISO/436.8 = 0.229 DN/e-` at ISO 100, so the
absolute level is only as good as that assumption): photon shot noise at a
signal of S DN above black is `sqrt(S * g)` DN. After averaging N frames it is
`sqrt(S * g / N)`. Setting that equal to the measured sigma_FPN of 0.377 DN at
N = 20 gives

```
S = 20 * 0.377^2 / 0.229 = 12.4 DN
```

**So above roughly 12 DN of signal — 0.08% of the 14848 DN usable range — shot
noise after a 20-frame average still exceeds the offset fixed-pattern floor.**
The floor measured in this document does not bind anywhere in a normally
exposed photograph. It binds in the deepest shadows and in astrophotography,
neither of which is this project's subject.

**ARGUED: the pillar holds for `strehl`'s use case, and dark-frame subtraction
is a shadow-quality refinement rather than a prerequisite for the merge stage.**
It should be built, because §6 shows it works and the design rule is simple, but
it does not block experiment 3.

**The real risk is the component this dataset cannot see.** Dark frames measure
offset FPN (DSNU) only. **PRNU** — per-pixel gain variation — is multiplicative,
scales with signal, and does not average away either. At a typical 0.3–1% and a
mid-tone of 5000 DN it would be 15–50 DN of fixed pattern against
`sqrt(5000 * 0.229) / sqrt(20) = 7.6` DN of 20-frame-averaged shot noise: two to
seven times larger than the noise it is competing with, and sitting exactly in
the lit, low-contrast regions where M2 measured the argmax defect.

**Status: UNVERIFIED, and it is the open question this experiment surfaced
rather than settled.** If PRNU on this sensor is at the high end, averaging in
lit regions would asymptote just as §4.1 does in the dark, and the merge stage
would need flat-field correction, not just bias subtraction.
`docs/captures-needed.md` §4 now requests the flat fields that would settle it.

---

## 8. Read noise vs ISO — the dual-gain claim, tested

`SYNTHESIS.md` fact 14 asserts ISO 400 is a second base ISO with read noise
dropping 4.20 → 1.47 e-.

### 8.1 Model-free evidence first (MEASURED)

Raw sigma_temporal in DN, sorted by ISO, no conversion and no assumed gain:

| ISO | R | G1 | G2 | B | mean |
| --- | --- | --- | --- | --- | --- |
| 50 | 1.0079 | 1.0054 | 1.0120 | 0.9211 | 0.9866 |
| 100 | 1.0048 | 1.0042 | 1.0105 | 0.9185 | 0.9845 |
| 200 | 1.7709 | 1.7782 | 1.7929 | 1.6246 | 1.7416 |
| 250 | 2.1927 | 2.2104 | 2.2284 | 2.0201 | 2.1629 |
| **400** | 1.2130 | 1.2266 | 1.2403 | 1.1146 | **1.1986** |
| 500 | 1.4940 | 1.4949 | 1.5105 | 1.3724 | 1.4680 |
| 640 | 1.8308 | 1.8438 | 1.8657 | 1.6914 | 1.8080 |
| 800 | 2.2752 | 2.2872 | 2.3138 | 2.1100 | 2.2465 |
| 1000 | 2.8376 | 2.8582 | 2.8920 | 2.6463 | 2.8085 |
| 1600 | 4.4369 | 4.4702 | 4.5407 | 4.1739 | 4.4054 |
| 2000 | 5.5866 | 5.6165 | 5.6883 | 5.2406 | 5.5330 |

**There is a discontinuity at ISO 400 and it is not subtle.** Noise in DN rises
monotonically from ISO 100 to ISO 250, then **falls by 45%** (2.1629 → 1.1986)
while the ISO setting *rises* by 1.6x, then resumes rising monotonically to ISO
2000. A single-gain sensor cannot do this: raising gain must raise the noise in
DN. **Status: MEASURED, model-free. `SYNTHESIS.md` fact 14 is confirmed.**

The size of the step, still without assuming an absolute gain — only that gain
is proportional to ISO *within* a gain mode, which the flatness of the two
plateaus below independently supports:

| ISO | sigma_DN / ISO |
| --- | --- |
| 50 | 0.019732 |
| 100 | 0.009845 |
| 200 | 0.008708 |
| 250 | 0.008652 |
| 400 | 0.002997 |
| 500 | 0.002936 |
| 640 | 0.002825 |
| 800 | 0.002808 |
| 1000 | 0.002808 |
| 1600 | 0.002753 |
| 2000 | 0.002767 |

Two clean plateaus: **0.008680** across ISO 200–250 and **0.002842** across ISO
400–2000 (spread 0.002753–0.002997, i.e. ±4%). The ratio is

> **3.05x lower read noise in electrons above the ISO 400 switch.**

**Status: DERIVED** (assumes only gain ∝ ISO within a mode). Fact 14's claimed
4.20/1.47 = 2.86x is consistent with this.

### 8.2 ISO 50 is not a real gain step (MEASURED)

ISO 50 and ISO 100 give **the same** sigma in DN — 0.9866 and 0.9845, a ratio of
1.0021. A genuine gain step would halve or double it. ISO 50 is a Sony extended
/ pull setting: the same analogue readout as ISO 100, differently labelled.
**It buys nothing and costs highlight headroom; the product should never
select it.**

### 8.3 The electron conversion, clearly labelled

| ISO | assumed g (DN/e-) | sigma (DN) | RN (e-) |
| --- | --- | --- | --- |
| 50 | 0.11447 | 0.9866 | 8.6189 |
| 100 | 0.22894 | 0.9845 | **4.3004** |
| 200 | 0.45788 | 1.7416 | 3.8037 |
| 250 | 0.57234 | 2.1629 | 3.7790 |
| 400 | 0.91575 | 1.1986 | **1.3089** |
| 500 | 1.14469 | 1.4680 | 1.2824 |
| 640 | 1.46520 | 1.8080 | 1.2339 |
| 800 | 1.83150 | 2.2465 | 1.2266 |
| 1000 | 2.28938 | 2.8085 | 1.2268 |
| 1600 | 3.66300 | 4.4054 | 1.2027 |
| 2000 | 4.57875 | 5.5330 | 1.2084 |

**Status: DERIVED, not measured.** This uses the *assumed* `g = ISO/436.8`
DN/e-, which has never been measured on this sensor. The ISO 50 row (8.62 e-)
is visibly nonsense and is the tell: the assumption breaks wherever ISO is not
a real gain step.

Taking the assumption at face value, fact 14's 4.20 → 1.47 e- measures as
**4.30 → 1.31 e-**: 2.4% off on the low-gain side, 11% off on the high side.

**A photon-transfer curve is not possible from dark frames** — PTC needs signal
variance against signal level and there is no signal here. `g` therefore stays
`DERIVED` and `SYNTHESIS.md` §10 item 6 stays **open**. No gain measurement was
fabricated.

---

## 9. Hot and stuck pixels

Threshold from the plane's own `median + K * 1.4826 * MAD` of the *temporal
mean* image. A median/MAD threshold is used rather than mean/sd because hot
pixels are exactly the outliers that would drag a mean-and-sd threshold up
behind them. K = 6 is justified by size: over 8.24 million pixels a Gaussian
puts fewer than one sample beyond 5.17 sigma.

| ISO | R | G1 | G2 | B | total | % of ISO 100's set | % of this ISO's set |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | 1426 | 1401 | 6016 | 3729 | 12572 | 27.9% | 29.3% |
| 100 | 1567 | 1489 | 6295 | 3862 | 13213 | 100.0% | 100.0% |
| 200 | 6108 | 6124 | 19043 | 14820 | 46095 | 45.7% | 13.1% |
| 250 | 4810 | 5121 | 16054 | 15728 | 41713 | 43.7% | 13.9% |
| 400 | 4901 | 4985 | 15624 | 11297 | 36807 | 42.5% | 15.3% |
| 500 | 5219 | 5260 | 16265 | 11675 | 38419 | 42.8% | 14.7% |
| 640 | 9434 | 9105 | 25106 | 20012 | 63657 | 48.4% | 10.0% |
| 800 | 7972 | 7876 | 22482 | 22745 | 61075 | 47.9% | 10.4% |
| 1000 | 9944 | 10363 | 26628 | 26810 | 73745 | 49.1% | 8.8% |
| 1600 | 12547 | 12466 | 28146 | 25055 | 78214 | 49.9% | 8.4% |
| 2000 | 12907 | 13119 | 28976 | 24917 | 79919 | 50.3% | 8.3% |

**The 6-sigma population is mostly not hot pixels (ARGUED).** At ISO 100 the
robust sd of the temporal-mean image is ~0.22 DN, so the 6-sigma threshold is
**514.3 DN — 2.3 DN above black.** Only 42–50% of ISO 100's flagged set is
flagged at any other ISO, and only 8–15% of a high-ISO set is shared with ISO
100. A genuinely defective pixel is defective at every gain. These sets are
dominated by ordinary pixels sitting a fraction of a DN off the median.

**The census at absolute thresholds is the real answer (MEASURED):**

| Threshold | ISO 100, all 4 planes | ISO 2000, all 4 planes |
| --- | --- | --- |
| median + 50 DN | **0** | 17 |
| median + 100 DN | 0 | 5 |
| median + 200 DN | 0 | 3 |
| median + 500 DN | 0 | 1 |
| 20 * robust sigma | 13 | 1642 |

**Status: MEASURED. At 1/100 s this sensor has essentially no hot-pixel
population — zero pixels anywhere in the frame sit 50 DN above black at base
ISO, and seventeen do at ISO 2000, out of 32.97 million.** Exactly one pixel in
the whole sensor exceeds black + 500 DN, and only at ISO 2000.

**Bearing on `SYNTHESIS.md` §7 risk 8 (ARGUED).** The concern is that defects
fixed in *sensor* coordinates smear into trails once the subject is stabilised,
and that "never materialise aligned frames" makes them hard to spot. On this
evidence the risk is **negligible at short exposures**: there is nothing bright
enough to trail. **This dataset cannot retire the risk**, because dark current
scales with integration time and every frame here is 1/100 s. A stacker used at
1 s or longer would need this re-measured. **Status: UNVERIFIED for long
exposures.**

---

## 10. Black level vs ISO

| ISO | R | G1 | G2 | B | declared | max delta |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | 512.215 | 512.200 | 512.204 | 512.253 | 512 | 0.253 |
| 100 | 512.231 | 512.208 | 512.209 | 512.275 | 512 | 0.275 |
| 200 | 512.245 | 512.241 | 512.263 | 512.296 | 512 | 0.296 |
| 250 | 512.224 | 512.202 | 512.214 | 512.262 | 512 | 0.262 |
| 400 | 512.165 | 512.179 | 512.190 | 512.225 | 512 | 0.225 |
| 500 | 512.171 | 512.172 | 512.194 | 512.232 | 512 | 0.232 |
| 640 | 512.198 | 512.204 | 512.254 | 512.282 | 512 | 0.282 |
| 800 | 512.143 | 512.145 | 512.172 | 512.209 | 512 | 0.209 |
| 1000 | 512.108 | 512.137 | 512.189 | 512.200 | 512 | 0.200 |
| 1600 | 512.204 | 512.176 | 512.213 | 512.258 | 512 | 0.258 |
| 2000 | 512.141 | 512.079 | 512.152 | 512.219 | 512 | 0.219 |

**Status: MEASURED. The metadata's 512 is correct at every ISO to within 0.30
DN.** No ISO disagrees materially and there is no trend with gain.

Two real but tiny effects:

- The measured mean is **always above** 512, by +0.08 to +0.30 DN, at all 11
  ISOs and all 44 plane/ISO combinations. With a standard error of ~0.0002 DN
  on each plane mean this is overwhelmingly significant, not sampling noise.
- **B is the highest plane in 10 of 11 folders**; G1 or R is the lowest in 10 of
  11. The plane-to-plane spread is 0.04–0.14 DN.

**ARGUED:** these are real offsets, and they are also irrelevant to the
product. 0.3 DN is 0.3 of a temporal sigma at base ISO and 0.002% of the 14848
DN usable range. `strehl` should keep subtracting the declared 512. Recording
them matters only so that a future 0.3 DN discrepancy is recognised as known
rather than investigated as a bug.

---

## What this does NOT show

**This document has not been independently verified.** `AGENTS.md` rule 12 says
the author never verifies their own work, and M2 shipped five wrong supporting
numbers despite thorough self-verification. The numbers most worth attacking
first, in order:

1. **The 0.377 DN fixed-pattern floor**, since every other conclusion is scaled
   by it. It is a bias-corrected quantity and the correction is the largest
   single step in the calculation (raw 0.4468 → 0.3862 at ISO 100 plane R).
2. **The 12 DN crossover in §7**, which is `DERIVED` from an unmeasured gain and
   is the number that turns "the pillar fails at N ≈ 7" into "this never matters
   in practice". If it is wrong, the recommendation changes.
3. **The claim that the split-half correction reaches the temporal floor**,
   which rests on the predicted floor `sqrt(2 sigma_t^2 / 10)` being the right
   prediction.

Beyond that:

- **Nothing about PRNU.** Dark frames contain no signal, so multiplicative
  fixed-pattern noise is invisible here. §7 argues it is the more dangerous
  component for this project and it remains `UNVERIFIED`.
- **Nothing about gain.** No PTC is possible without flat fields. Every electron
  figure in §8.3 is `DERIVED` from an unmeasured `g`.
- **Nothing about dark current vs exposure time.** All 242 frames are 1/100 s.
  The near-absence of hot pixels in §9 is a statement about 1/100 s only.
- **Nothing about temperature.** The frames were shot in one session at one
  ambient temperature and the sensor's own temperature during the run is
  unknown. Dark current roughly doubles every 6–7 °C, so §9 could look
  different on a warm day. Frame index within each folder was not tested for a
  warming trend, and it easily could have been — that is a gap in this
  experiment, not in the data.
- **Nothing about whether averaging helps a real focus stack.** These are dark
  frames of a lens cap. M2 measured the argmax defect on real content; joining
  the two requires experiment 3.
- **One sensor, one body, one session.** n=1 at the body level.
- The N = 12 and N = 16 points in §4 use overlapping random draws, because 20
  frames cannot supply two disjoint subsets of those sizes. Their scatter
  understates the true sampling variability and they are flagged in the tool's
  output. The fitted slopes include them.
- **Only the first 20 usable frames per folder were analysed.** The two
  discarded stabilisation frames were checked for ISO and exposure consistency
  but were not otherwise examined.

---

## Reproducing

```
cd experiments/m2-fpn
cargo run --release -- --synthetic                  # negative control, run first
cargo run --release -- D:\macro-dark-frames --map   # folder -> ISO discovery
cargo run --release -- D:\macro-dark-frames         # the measurement, 39 s
```
