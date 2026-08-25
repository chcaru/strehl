# M115 — Deconvolution headroom, measured

Status: MEASURED
Agent: M115-deconv-headroom
Experiment: `experiments/M115-deconv-headroom/` (source committed at `77c8d5e`; pre-registration at `0991b55`)
Data: `109MSDCF` (22 frames, ISO 160, marked f/11), `119MSDCF` (33 frames, ISO 50, marked f/5.6), flat-field corpus (360 frames, ISO 100 f/5.6). All read-only from `D:\`; all outputs under `C:\dev\strehl-out\M115-deconv-headroom\`.

---

## 1. The headline

**There is no meaningful headroom. Multi-frame Wiener deconvolution along the focus axis recovers essentially no information that the merge already shipping does not have: at matched contrast its band SNR ratio against the noise-gated average is `1.0014 ± 0.0184` (8 spatial blocks, two stacks, mid band 0.10–0.276 cyc/quad-px).** One and a half parts in a thousand, with a 95 % interval of `[0.965, 1.038]`. The prize the proposal was reaching for is not there.

What *is* there — and this is why the proposal is seductive — is a large **contrast** gain that carries no information with it:

| f (cyc/quad-px) | `G_sig` WIENER | `G_noise` WIENER | **`R_SNR` WIENER** | `G_sig` GATE | `R_SNR` GATE |
| --- | --- | --- | --- | --- | --- |
| 0.105 | 1.261 ± 0.080 | 0.955 ± 0.106 | 1.399 ± 0.143 | 0.749 | 1.662 |
| 0.145 | 1.794 ± 0.135 | 1.436 ± 0.201 | 1.356 ± 0.124 | 0.646 | 1.412 |
| 0.185 | 2.386 ± 0.414 | 1.888 ± 0.380 | 1.354 ± 0.094 | 0.577 | 1.352 |
| 0.205 | 2.514 ± 0.625 | 2.029 ± 0.572 | 1.371 ± 0.102 | 0.547 | 1.311 |
| 0.225 | 2.356 ± 0.738 | 1.759 ± 0.578 | 1.401 ± 0.146 | 0.536 | 1.204 |
| 0.265 | 0.329 ± 0.025 | 0.277 ± 0.023 | 1.216 ± 0.091 | 0.489 | 1.230 |

All relative to `BEST1`, the single globally sharpest frame. Read the columns together. Contrast rises to **2.5×** the sharpest frame at f = 0.205 — and the noise rises to **2.0×** alongside it. The ratio of the two, which is the only quantity a post-sharpening pass cannot manufacture, is flat across the mid band: **band-mean `R_SNR` = 1.3316 ± 0.0261**, per-bin range 1.216–1.401. And the gated average — which already ships — reaches **1.3636 ± 0.0247** by itself.

The estimator does not create information. It *reallocates* information the gate already had, from the noise budget into the contrast budget. That is exactly what a linear filter must do, and control C3 below measures that it is what happens.

Two secondary results sharpen the picture:

- **The ceiling a perfect selector reaches is already essentially the ceiling.** Per-tile election over the whole stack buys `+2.8 % ± 0.6 %` contrast over simply taking the single sharpest frame, at `R_SNR = 0.9917 ± 0.0079` — i.e. nothing. On these regions the depth range is shallow enough that one frame nearly covers it.
- **The deconvolution's apparent sharpness is substantially fabricated.** 29.5–36.4 % of output pixels fall outside the convex hull of every input frame, concentrated in a halo peaking 8–16 px from edges (§4).

The reviewer's premise is sound and the project's own M70 already granted it: off-peak frames do carry mid-band amplitude, and a matched filter does harvest it. The inference is what fails. **Harvesting it is worth ~1.00×, because the shipped gate already harvests it.**

### Where the argument breaks

The proposal's third bullet — "in between is the new part" — assumes that the current gate "counts [off-peak frames] as contributing nothing". It does not. The gate is a *noise-gated average*, not a selector; it already averages the frames within its window, and `G_noise(GATE) = 0.408–0.471` against the per-tile selector shows it collecting exactly the multi-frame noise reduction the matched filter was supposed to introduce. The matched filter's refinement over that — weighting those frames by `H_k` rather than equally — is worth `R_SNR(MF)/R_SNR(GATE) = 0.9844 ± 0.0182`, i.e. nothing, and slightly negative.

This agrees with M70's independent prediction from a different direction (band matrix rank-1 to 0.9959, so matched filtering over near-scaled copies *is* weighted averaging) and with M20's simulation (guarded Wiener wins on 15.1 % of pixels). Three routes, three instruments, one answer.

---

## 2. The metric, and the controls that validate it

### 2.1 The observable

Signal and noise are separated **without a noise model** by splitting the real stack into two interleaved disjoint halves, pushing each through the entire pipeline with every data-dependent weight re-derived inside its own half, and using

```
P_sig(f)   = Re< FFT(O_A) conj(FFT(O_B) ) >     noise independent between halves -> 0
P_noise(f) = P(O_A - O_B) / 2                   signal common to both -> cancels
R_SNR(f)   = sqrt( SNR_arm(f) / SNR_ref(f) )
```

Radially binned, Hann-windowed, on the green quad plane, black-subtracted, frequencies in cyc/quad-px.

The headline is SNR and not contrast **by design**: a linear filter multiplies signal and noise by the same factor at each frequency, so contrast gain is free and anyone can post-sharpen. SNR is the only thing that cannot be bought.

### 2.2 The pre-registered channel FAILED its null, and was replaced

This must be on the record. The pre-registration (`0991b55` §2) specified antithetic noise injection, `D = (pipeline(Y+n) − pipeline(Y−n))/2`. Run on a **real scene-free capture** — 24 flat-field frames through the same optics and sensor — it reported:

| arm | mid-band SNR, injection channel | mid-band SNR, split channel | `P_noise` injection / split |
| --- | --- | --- | --- |
| `FRAME_PIX` | **84.876** | 0.0068 | 0.0137 |
| `MF` | **30.608** | −0.0088 | 0.0262 |
| `WIENER` | **12.005** | −0.0084 | 0.0732 |
| `GATE` | **9.531** | −0.0071 | 0.0949 |
| `MEAN` | 0.544 | 0.2984 | 0.5179 |
| `FRAME*` | 0.0000 | 0.0599 | 1.1112 |
| `WIENER_UNG` | 0.0000 | 0.4034 | 27.9196 |

The injection channel invented mid-band SNR of 85 on an image containing no scene, and under-estimated a per-pixel selector's noise power by **73×**.

**Diagnosed cause, measured:** the tile election differs between `Y+n` and `Y−n` on **100.0 %** of tiles. The antithetic difference is therefore not a derivative of the pipeline at all. The channel measures how *injected* noise propagates given frozen weights, and is structurally blind to noise that a data-dependent election has already converted into *structure* — which on a flat field is all of it. The two exact `0.0000` readings are the same defect with the opposite sign: over-subtraction, not cleanliness.

Had this metric been used, every headline in this report would have been fiction, and the fiction would have favoured the deconvolution arms by an order of magnitude. It is the same class of failure that discarded ORCH's chromatic-aberration table: **a clean-looking number from an instrument that was never shown able to respond.**

### 2.3 C2 — the positive control: planted blur, monotone, right sign, right magnitude

An **exact** Gaussian applied in the Fourier domain, `MTF = exp(−2π²σ_b²f²)` — no kernel truncation, no resampling, because a resampling plant blurs and would have perturbed the very quantity under measurement.

`109MSDCF` detail ROI, recovery ratio = measured log-attenuation ÷ analytic log-attenuation:

| σ_b (px) | `MEAN` P_sig | recovery | `FRAME*` P_sig | recovery |
| --- | --- | --- | --- | --- |
| 0.0 | 8.029e7 | (reference) | 5.380e8 | (reference) |
| 0.5 | 6.886e7 | 0.9964 | 4.500e8 | 0.9974 |
| 1.0 | 4.431e7 | 0.9959 | 2.742e8 | 0.9969 |
| 1.5 | 2.215e7 | 0.9951 | 1.298e8 | 0.9960 |
| 2.0 | 8.795e6 | 0.9938 | 4.931e7 | 0.9951 |

**Monotone decreasing on both arms, all eight recovery ratios in `[0.9938, 0.9974]`.** The metric responds to blur, in the correct direction, at within 0.7 % of the correct magnitude. The sign convention is read directly off this control: *more planted blur ⇒ lower `P_sig`*, and `P_sig` is the numerator of the headline.

### 2.4 C3 — gain invariance: the control that decides whether any of this means anything

A known post-filter is applied to an arm's **output** — information-free by construction — and the headline must not move.

| post-filter | contrast gain | **`R_SNR` ratio** | naive gradient-energy gain |
| --- | --- | --- | --- |
| flat ×3 | 3.0000 | **1.0000** | 3.0000 |
| unsharp 1+2f | 1.9733 | **0.9986** | 1.9371 |
| unsharp 1+6f | 3.9391 | **0.9980** | 4.1854 |
| inverse diffraction taper | 3.7939 | **0.9946** | **8.2514** |

The headline moved by at most **0.54 %** under filters that changed apparent contrast by up to 3.94×. A naive gradient metric — of the kind that would report "the deconvolution looks sharper" — was moved **8.25×** by a filter that added no information whatsoever. This is the measured justification for reporting `R_SNR` rather than contrast, and it is the reason the 2.5× contrast gain in §1 must not be read as a result.

### 2.5 C1′ — the null, on the replacement channel

Same scene-free capture. Five of seven arms read `|SNR| ≤ 0.14`. Two did not, and the pre-registered bar (`max mid-band SNR < 0.25`) is therefore recorded as **FAIL**:

- `MEAN` 0.2984, `WIENER_UNG` 0.4034.

**C6 explains `MEAN` and was registered before it was run.** Fixed-pattern non-uniformity is the *same* pattern in both halves, so it is common-mode and lands in `P_sig` by construction — nothing that uses one capture of one sensor can separate a static sensor pattern from a static scene. The registered discriminator: if that is what the residual is, `P_sig` is invariant in half-size `N` while `SNR ∝ N`.

| N | `MEAN` P_sig | `MEAN` P_noise | `MEAN` SNR |
| --- | --- | --- | --- |
| 2 | 1.005e4 | 3.033e5 | 0.0331 |
| 4 | 1.173e4 | 1.525e5 | 0.0769 |
| 8 | 1.421e4 | 8.213e4 | 0.1730 |
| 12 | 2.067e4 | 6.968e4 | 0.2967 |

Log-log slope of SNR in `N` = **1.215** (registered interval 1.0 ± 0.25); `P_noise` falls as `1/N` across a 4.35× range. It is the sensor floor, not a metric defect. **Scaled to the detail ROIs it is 0.073 % and 0.050 % of the scene signal** — four orders of magnitude below the measurement, so it does not touch any headline.

`WIENER_UNG` is a different matter: its null `P_sig` varies **29.06×** across half-sizes with no scaling law at all. The unguarded inverse filter is simply unstable on a scene-free input. That is a finding about the arm, not about the instrument, and it is the measured argument for the floor guard the brief required.

### 2.6 C9, C10 — the split channel's own assumptions

- **C10, internal consistency:** `(P(A)+P(B))/2` versus `P_sig + P_noise` = **1.0000** on every arm and both stacks.
- **C9, latent mismatch:** the two halves must share a latent. A deliberately-broken split (first half vs second half, genuinely different focus content) was run beside the interleaved one. Interleaved `P_sig` is **1.165×** the broken split's, and `SNR` is **19.09 vs 10.996** (`FRAME*`) and **120.9 vs 2.82** (`MEAN`). The assumption is doing real work and interleaving satisfies it; the residual mismatch attenuates `P_sig` and inflates `P_noise`, i.e. it biases every arm *against* itself, conservatively.
- **C5, noise model:** modelled σ against a temporal σ from flat-field frame pairs, ratios **0.9673–0.9712** (bar ±15 %). Used only for the through-focus noise subtraction in §5, not for the headline.

### 2.7 Two independent routes to the headline agree

The matched-contrast test in `s05` sharpens the `GATE` output to the Wiener's measured contrast per frequency and compares noise directly. Algebraically that must equal `R_SNR(WIENER)/R_SNR(GATE)`, which `s04` measured on different crops by a different route:

- `s04`, 8 blocks of 256², pooled: **0.9795**
- `s05`, full 512² ROIs: `109MSDCF` **0.9400**, `119MSDCF` **1.1439**, mean **1.0419**
- `s07`, per-block ratios with correct SE: **1.0014 ± 0.0184**

Contrast match achieved 1.008 and 1.023, confirming the sharpening landed. The routes agree to 0.062 in absolute ratio and all three straddle 1.00.

---

## 3. Registered decision rule and prediction, scored as they fell

- **Decision rule.** Pre-registered as MEANINGFUL ≥ 1.25 / SMALL < 1.15 on max mid-band `R_SNR` against `FRAME*`. Scored: `WIENER` 1.4499 ± 0.1623 → **AMBIGUOUS**; `MEAN` 3.2936 ± 0.2909 → "MEANINGFUL".
  **The rule as registered is defective and I am reporting it rather than quietly replacing it.** `MEAN` — which destroys contrast to 0.24–0.44× and is obviously the wrong answer — scores highest. `R_SNR` alone rewards blur, the exact mirror of the trap C3 guards against, and taking a `max` over bins selects the lowest-frequency bin where multi-frame averaging trivially wins. The corrected statistic, fixed on principle rather than on outcome, is the **band-mean ratio against the shipped gate** (§1), which compares arms at matched contrast and cannot be gamed in either direction. It returns `1.0014 ± 0.0184` → **SMALL**, and the uncorrected `WIENER` reading was already not MEANINGFUL.
- **Prediction P-M70.** Registered: `max R_SNR(MF) / max R_SNR(GATE) ∈ [1.00, 1.25]`. Measured **0.8341** → outside. Diagnosis: the `max` statistic lands on f = 0.105 for both arms, and my `MEAN`/`GATE` arms span the *whole* depth range whereas M70's comparison was a matched filter against an equal average over the *same narrow window* (±1, ±3 frames). The prediction was mis-specified against my arms, not refuted by them. On the band-mean statistic `R_SNR(MF)/R_SNR(GATE) = 0.9844 ± 0.0182`, which is consistent with M70's central claim that the focus-axis matched filter's prize over an average of the same frames is small. **I flag this as a registration error of mine.**
- **VOID V1** fired: neither stack contains a region flat enough for the pre-registered null (`sd_s/σ_t` = 3.295 and 10.018 against a bar of 3). At 2:1 macro these subjects contain no featureless patch — M41 independently hit the same wall at 8.7×. Deviation declared: the null was sourced from the flat-field corpus instead, a real capture of a featureless scene through the same optics. This is a **stronger** null, not a weaker one.

---

## 4. The ringing control

Ringing is the failure mode that makes deconvolution look good and be wrong, so two instruments were used, both able to fire only on structure present in **no input frame**.

**Out-of-range fraction.** For each output pixel, `[min_k Y_k, max_k Y_k]` over the aligned stack is the convex hull of the evidence. Selection and averaging produce convex combinations and *must* read 0.

`109MSDCF` edge ROI, out-of-range fraction by distance from the nearest strong edge:

| arm | total | p99.9 excess ÷ hull | 0–1 px | 1–2 px | 2–4 px | 4–8 px | **8–16 px** | >16 px |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `BEST1`, `FRAME*`, `FRAME_PIX`, `GATE`, `MEAN` | **0.0000 %** | 0.00000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `MF` | 29.676 % | 18.408 | 4.500 | 16.601 | 26.328 | 53.469 | **70.716** | 27.485 |
| `WIENER` | 29.537 % | 18.038 | 15.599 | 34.392 | 34.925 | 54.559 | **70.281** | 27.000 |
| `WIENER_UNG` | 29.900 % | 18.034 | 19.756 | 32.474 | 33.359 | 54.785 | **70.473** | 27.368 |

`119MSDCF`: `MF` 35.827 %, `WIENER` 35.498 %, `WIENER_UNG` 36.351 %, peaking at 74.7 / 73.7 / 74.1 % in the 8–16 px shell, p99.9 excess 25.4–25.8× hull.

Three things follow.

1. **All five convex arms read exactly 0.0000 %.** This is the control on the control: an instrument that cannot return zero for a convex combination is not measuring manufactured contrast at all. It can.
2. **The excess is a halo, not noise amplification.** It rises from 4.5 % adjacent to the edge to **70.7 % at 8–16 px** and falls to 27.5 % far from any edge. A flat excess everywhere would be amplified noise; a peak at a characteristic distance is ringing. Reporting only the scalar would not have distinguished these. Roughly 27 % of the excess *is* noise amplification, and the rest is halo.
3. **The magnitude is gross.** The 99.9th-percentile excursion is **18–26× the entire width of the stack's convex hull** at that pixel. This is not subtle overshoot.

`MF` — the diffraction-free arm that M41 found *survived* on the noise axis at 0.943×/0.979× — rings at **29.7 % / 35.8 %**, statistically indistinguishable from the full Wiener. M41 never measured ringing and said so. **The focus-axis-only matched filter manufactures edge contrast at essentially the same rate as the full estimator**, which materially qualifies M41's conclusion that arm D′ survives.

---

## 5. Does OTF self-calibration from the through-focus curve work?

**No. It needs an optical model, and the optical model it needs does not fit the data either.**

The reviewer's route — curve FWHM ⇒ blur growth per frame `s` — was implemented (`calibrate_s`) and gives `s = 1.0164` (`109MSDCF`) and `0.7399` (`119MSDCF`) quad-px/frame. The registered discriminator: fit `s` independently in each radial bin; a valid model gives one value everywhere.

| | `109MSDCF` | `119MSDCF` |
| --- | --- | --- |
| curve-width `s` | 1.0164 | 0.7399 |
| per-bin fitted `s` | 0.497 – 0.617 | 0.274 – 0.423 |
| spread | 1.24× | 1.54× |
| slope of `s_fit` in f | **−0.60** | **−0.83** |
| curve-width ÷ mean fitted | **1.87×** | **2.15×** |

Scoring the registered bar literally: `109MSDCF` passes the 1.5× spread test and `119MSDCF` fails it. **But the spread bar is the weaker evidence and both stacks fail on the stronger two.**

- **The level is wrong by ~2× on both stacks, in the same direction.** Curve width over-estimates the defocus scale by 1.87× and 2.15×.
- **`s_fit` falls monotonically with frequency on both stacks** (slope −0.60, −0.83). That is precisely the signature registered in advance for M70's rank-1 alternative: the model can only reproduce a too-flat attenuation at high f by pretending the defocus is small.
- **The model is qualitatively wrong, not merely mis-scaled.** At `109MSDCF`, dk = 3, f = 0.195, the defocus model predicts `|OTF| = 0.021` — the frame is destroyed — while the measurement reads **0.638**. At dk = 4 the model produces non-monotone Bessel side-lobes (0.028 → 0.100 → 0.120 → 0.131 → 0.132 across the band) that the data does not show at all; the measured curve is smooth and monotone throughout.
- **The measured attenuation is far flatter in f than any defocus model can be**: relative spread across the mid band is 1.1 % at dk = 1 and 3.6 % at dk = 2 for `119MSDCF`, 4.9 % and 11.0 % for `109MSDCF`. Off-focus frames are close to *scaled copies* of the focused one over this band, which is M70's rank-1 finding (eigen-share 0.9959) confirmed independently in the output domain on two stacks.

This is the deeper reason the headline is a null. If off-focus frames are near-scaled copies, then `Σ conj(H_k) Y_k / Σ|H_k|²` degenerates to a weighted average, and the weights barely matter — which is exactly what `R_SNR(MF)/R_SNR(GATE) = 0.9844 ± 0.0182` says.

---

## 6. Proposed facts for SYNTHESIS.md

Numbered `P1…` per rule 28; absolute numbers belong to ORCH. I have not edited `SYNTHESIS.md`.

1. **P1 — MEASURED.** At matched contrast, multi-frame Wiener deconvolution along the focus axis delivers a band-SNR ratio of **1.0014 ± 0.0184** against the shipped noise-gated average, mid band 0.10–0.276 cyc/quad-px. (`109MSDCF` + `119MSDCF` detail ROIs, 8 spatial blocks; `s07_summary.json`.)
2. **P2 — MEASURED.** The same estimator raises apparent contrast to **2.51 ± 0.63×** that of the single sharpest frame at f = 0.205, while raising noise to **2.03 ± 0.57×**; band-mean `R_SNR` stays at **1.3316 ± 0.0261** (per-bin range 1.216–1.401) across the mid band. Contrast gain and information gain are decoupled. (Same ROIs.)
3. **P3 — MEASURED.** The focus-axis matched filter without the diffraction term (M41's surviving arm D′) is worth `R_SNR = 0.9844 ± 0.0182` against the shipped gate — no gain, slightly negative. (Same ROIs.)
4. **P4 — MEASURED.** Per-tile election over the full stack buys only **+2.8 % ± 0.6 %** contrast over the single globally sharpest frame, at `R_SNR = 0.9917 ± 0.0079`. On these detail regions a perfect selector is barely better than one frame. (Same ROIs.)
5. **P5 — MEASURED.** The Wiener and matched-filter arms place **29.5–36.4 %** of output pixels outside the convex hull of every input frame, with 99.9th-percentile excursions of **18.0–25.8× the hull width**. All five convex arms read exactly 0.0000 %. (`109MSDCF` and `119MSDCF` edge ROIs.)
6. **P6 — MEASURED.** That excess is a halo, not noise amplification: out-of-range fraction rises from **4.5 %** at 0–1 px from a strong edge to **70.7 %** at 8–16 px, falling to **27.5 %** far from edges. (`109MSDCF` edge ROI; `119MSDCF` peaks at 74.7 %.)
7. **P7 — MEASURED.** The diffraction-free matched filter rings at **29.7 % / 35.8 %** out-of-range, indistinguishable from the full Wiener. M41's arm D′ survives on the noise axis but **not** on the manufactured-contrast axis, which M41 did not measure. (Same edge ROIs.)
8. **P8 — MEASURED.** OTF self-calibration from through-focus curve width over-estimates the defocus scale by **1.87×** and **2.15×** relative to a per-frequency fit, and the fitted `s` falls with frequency (slope −0.60, −0.83) on both stacks. Curve width cannot stand in for the PSF scale. (`109MSDCF`, `119MSDCF` detail ROIs.)
9. **P9 — MEASURED.** Measured through-focus attenuation is nearly flat across the mid band — relative spread **1.1 %** (dk = 1) and **3.6 %** (dk = 2) on `119MSDCF` — where a defocus model predicts steep, sign-changing, frequency-dependent decay (model 0.021 vs measured 0.638 at dk = 3, f = 0.195 on `109MSDCF`). Off-focus frames are near-scaled copies. This confirms M70's rank-1 finding in the output domain on real images.
10. **P10 — MEASURED, instrument.** Antithetic noise injection `D = (pipeline(Y+n) − pipeline(Y−n))/2` is **invalid for any pipeline with a data-dependent election**: on a real scene-free capture it reported mid-band SNR of **84.9** for a per-pixel selector and under-estimated its noise power by **73×**. The tile election differs between `Y+n` and `Y−n` on **100.0 %** of tiles. (Flat-field corpus, 24 frames, ISO 100.)
11. **P11 — MEASURED, instrument.** A split-stack channel (interleaved disjoint halves, cross-spectrum for signal, half-difference for noise) passes the same null at `|SNR| ≤ 0.14` on five of seven arms, needs no noise model, and satisfies `(P(A)+P(B))/2 = P_sig + P_noise` to **1.0000**.
12. **P12 — MEASURED, instrument.** Band-wise `R_SNR` moved by at most **0.54 %** under post-filters changing apparent contrast by up to **3.94×**, while a naive gradient-energy metric was moved **8.25×** by the same information-free filters. Any sharpness claim on this project reported as contrast rather than SNR is unfalsifiable.
13. **P13 — MEASURED.** The fixed-pattern floor is common-mode to any split of one capture and is indistinguishable from static scene by construction. On the flat-field corpus it scales as `SNR ∝ N^1.215` with `P_noise ∝ 1/N`; scaled to the detail ROIs it is **0.073 %** and **0.050 %** of scene signal.
14. **P14 — MEASURED.** Neither `109MSDCF` nor `119MSDCF` contains a region flat enough to serve as a null: best `sd_s/σ_t` = **3.295** and **10.018**. At 2:1 macro these subjects have no featureless patch; nulls must come from the flat-field corpus. (Corroborates M41's independent 8.7×.)
15. **P15 — ARGUED.** Facts 12/27/28 are not overturned: the optics genuinely are destroyed near Nyquist. But the inference that *therefore reconstruction has headroom* does not follow, because the information the estimator would need to reconstruct with is not in the off-focus frames either — they are scaled copies of the same degraded latent (P9), so their sum has the same band-limit.
16. **P16 — MEASURED, instrument, `109MSDCF` detail ROI.** A common additive noise floor does **not** compress an arm-vs-arm SNR ratio toward 1. The ratio factorises exactly into a signal-power factor and a noise factor, and the floor acts only on the latter, so the ratio tends to the **signal-power ratio** of the two arms. Over 42 ordered arm pairs the compression slope `β` fell monotonically 1.0000 → −1.0186 across a dose sweep of 0 → 128× median `P_noise`, with the signal factor invariant at −1.0186.
17. **P17 — MEASURED, `109MSDCF`.** In M115's arm set that asymptote is a **sign reversal, not a compression**: the measured arm ordering inverts and the residual log-ratio spread *widens* from ±1.886 to ±2.810. A large shared degradation yields a confident wrong ranking, not a clean null. The mechanism is that contrast and SNR are anti-correlated across these arms (`MEAN`: highest SNR 182.2, lowest `P_sig` 8.03e7).
18. **P18 — MEASURED, `109MSDCF`, the fleet-relevant one.** **Quantisation error is not noise.** Rounding is a deterministic function of the pixel value, so frames of the same scene receive correlated rounding error: measured cross-half correlation **r = +0.5109**, versus **−0.0007** for an independent dither of identical power. Any paired, split-half or frame-difference noise estimator therefore books roughly half of it as *signal*.
19. **P19 — MEASURED, `109MSDCF`.** Consequence of P18 at matched perturbation power (2.581e4): an 8-bit narrowing raised measured `P_noise` **×3.937** while an independent dither of the *same* power raised it **×63.311** — a **16× under-report**. A narrowed dataset looks *less* noisy than it is, and the difference-based estimator best placed to detect the hazard is disabled by it. This is not in ORCH's current triage list.
20. **P20 — MEASURED.** The narrowing's departure from noise-floor behaviour is not a calibration confound: pinning self-calibrated `s` to its intact value moved `β` by only **0.0071**, while `P_sig` still rose ×1.262 (quantisation) against ×1.022 (matched dither).

---

## 7. What I did not test, and what would falsify this

**Not tested.**

- **Only two stacks and one ROI each.** `bee-3-cpl`, `foam`, `coffee-bean`, `tweezers-cpl` and the rest of the corpus were not touched. The owner's softness complaint may live on subjects with deeper depth ranges than these two, and P4 (+2.8 % for a perfect selector) says these two ROIs have shallow ones.
- **Deep stacks.** Both ROIs are covered by a few frames. A subject spanning 50+ focus planes where no single frame covers the region is exactly where multi-frame reconstruction should look best, and I did not measure one.
- **Spatially-varying and non-defocus PSFs.** One scalar `s` per stack; no field dependence, no aberration, no CA.
- **Iterative and regularised reconstruction.** Only the single-shot linear Wiener the brief specified. Richardson–Lucy, TV, and learned priors are non-linear, are not bound by the `R_SNR` invariance argument in the same way, and could in principle beat this. **This report does not price them.**
- **Alignment error.** Frames were used as-is; misalignment would blur the split-half cross-spectrum and hurt every arm.
- **Perceptual quality.** `R_SNR ≈ 1.00` at matched contrast says the information is equal. It does not say the two images look equally good, and the ringing result (§4) says one of them looks *worse* in a specific, locatable way.
- **The shipped merge itself.** `GATE` is a faithful re-implementation of the noise-gated average (M41's arm A), not the output of `merge.rs`, which is owned by M97 and holds uncommitted work.

**What would falsify the conclusion.**

1. A stack whose detail region is **not** covered by any single frame, on which `R_SNR(WIENER)/R_SNR(GATE)` exceeds 1.15 with the split channel and the same controls. This is the single most likely place for me to be wrong.
2. A demonstration that the split-half channel systematically penalises deconvolution arms — e.g. that latent mismatch between halves attenuates a deconvolved `P_sig` more than a gated one. C9 bounds the effect at 1.165× overall but does not resolve it per arm.
3. A per-frequency fit showing measured through-focus attenuation *is* frequency-dependent in the way a defocus model predicts, on a stack with larger focus steps than these (P8/P9 could be an artefact of steps too fine to resolve the OTF's shape).
4. A non-linear reconstruction beating the gate at matched contrast, which would not contradict P1 — P1 is about the linear estimator the brief specified — but would change the answer to "is a reconstruction merge worth building".

**Recommendation to ORCH: do not build the multi-frame Wiener merge.** The measured prize over what already ships is `1.0014 ± 0.0184`, it manufactures a 29–36 % out-of-range halo, and its OTF cannot be self-calibrated. If softness is the complaint, the measurement says the contrast is available by sharpening the existing gate — that is what `G_sig` 2.5× at `R_SNR` 1.00 means — and that the honest ceiling is set by the optics, not by the merge.

---

## 9. Bit-depth exposure check (ORCH's PIL 16-bit RGB hazard)

**M115 is not exposed.** Every input is camera RAW read through `rawpy.imread`; a full grep of the milestone finds no PIL, imageio, cv2, skimage, tifffile, or any `.tif` path. That is an absence claim, so it is backed by a positive verification (`bitdepth_check.py`, all asserts pass):

| source | dtype at the reader | distinct levels | after `load_cube` |
| --- | --- | --- | --- |
| `109MSDCF` | `uint16` | 2420 | `float32`, 4239 levels |
| `119MSDCF` | `uint16` | 4906 | `float32`, 9379 levels |
| flat-field null | `uint16` | 7367 | — |

The check is commissioned by `negctl_bitdepth.py`, which plants the exact narrowing PIL performs (keep the high byte) into M115's own loader and re-runs the headline on `109MSDCF`. Three results, all measured, all relevant to the fleet triage:

1. **The damage scales with the file's *occupied* range, not the full 16-bit range.** The detail ROI spans ~2100 DN, so the narrowing left **9 distinct levels, not 256**. On low-contrast crops this hazard is far worse than the 241× headline suggests.
2. **Absolute noise and SNR readings are destroyed.** Measured noise power rose **3.5×** (σ off by **1.9×**) and measured band SNR fell to **0.438×** of its true value — a real SNR would read less than half of what it is.
3. **A ratio of two arms on the same data is largely protected by cancellation**: `R_SNR(WIENER)/R_SNR(GATE)` moved only **−1.0 %** (0.9340 → 0.9248). This is the useful triage discriminator — ratio-of-arms statistics survive, absolute noise/sd/SNR/quantisation-limited statistics do not.
4. **The OTF self-calibration in §5 would have been corrupted**: fitted `s` moved 1.0164 → 1.2577, **+23.7 %**.

Since M115's smallest measured quantity is a per-pixel σ of 6.5–14.6 DN, and an 8-bit narrowing imposes a quantisation sd of ~37 DN on a full-range file, every SNR in this report would have been fiction had any input been narrowed. None was.

---

## 10. Testing ORCH's "ratios compress toward 1" claim

ORCH's correction to the PIL notice folded my two measured findings and added a third, adjacent to them:

> *small-over-large ratios compress toward 1 — they fail toward a clean null, the hardest error here to catch, because nobody re-examines an arm that showed no effect.*

That is ARGUED, not measured, and it implicates this report directly: **the M115 headline is a ratio near 1 reporting a null.** If the claim held in the form stated, my result would be the exact shape an artefact takes. Rule 12 applies to ORCH, so I measured it (`s08_ratiocompress.py`, `s09_quanterror.py`).

### 10.1 The law is not compression toward 1

A band SNR here is a power ratio, so a common additive floor `q` factorises the arm ratio **exactly**:

```
SNR_A/SNR_B = (P_sig_A/P_sig_B) · ((P_noise_B + q)/(P_noise_A + q))
              \_____________/     \_________________________/
               SIGNAL factor        NOISE factor → 1 as q → ∞
```

Compression acts **only on the noise factor**. The ratio does not tend to 1; it tends to the **signal-power ratio** of the two arms. Where that lands is a property of the arms being compared, not a general law.

Fitting `log r_measured = β · log r_true` over all 42 ordered arm pairs (the set is symmetric under inversion, so the intercept is identically 0), with the dose sweep as the positive control:

| dose `q` (× median `P_noise`) | 0 | 0.25 | 1.0 | 4.0 | 32 | 128 | → ∞ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **β** | 1.0000 | −0.0697 | −0.5674 | −0.8639 | −0.9966 | −1.0130 | **−1.0186** |

Monotone non-increasing: **PASS**. The signal factor is **invariant at −1.0186** across the entire sweep, as the algebra requires.

**In M115's arm set the asymptote is β = −1.0186 — a sign reversal, not a compression.** The measured arm *ordering inverts*, and the residual log-spread **widens** from ±1.886 to ±2.810. A large shared degradation does not hand you a null here; it hands you a confident, wrong ranking. The reason is specific and already documented in §2: across these arms contrast and SNR are anti-correlated (`MEAN` has the highest SNR at 182.2 and the lowest `P_sig` at 8.03e7), so ranking by signal power is close to the reverse of ranking by SNR.

### 10.2 The real hazard is not a noise floor — quantisation error is not noise

The sweep predicted β = **−0.8515** at the dose the narrowing actually delivers. The narrowing measured β = **+0.5861**. Not the same number, not the same sign. Two candidates, separated:

- **H1, calibration confound** (the narrowing moved self-calibrated `s` by +23.7 %, changing every arm's weights): **ruled out.** Pinning `s` to the intact value moved β by **0.0071**.
- **H2, correlated error: CONFIRMED.** Rounding is a *deterministic function of the pixel value*, not a random draw, so two frames of the same scene receive correlated rounding error. Measured **cross-half correlation r = +0.5109**, against **−0.0007** for an independent dither of *identical* power.

The consequence, at matched perturbation power:

| perturbation (identical power, 2.581e4) | cross-half `r` | `P_sig` | `P_noise` |
| --- | --- | --- | --- |
| quantisation (8-bit narrowing) | **+0.5109** | **×1.262** | **×3.937** |
| random dither (null) | −0.0007 | ×1.022 | **×63.311** |

**Same injected power; the measured noise power differs by 16×.** Any paired, split-half, or frame-difference noise estimator books the correlated half of quantisation error as *signal*. So a narrowed dataset **looks less noisy than it is**, and the instrument best placed to catch the hazard is the one the hazard disables. This is the opposite of the intuitive reading of ORCH's notice, and it is not in the current triage list.

### 10.3 Verdict, and what it does to this report's null

ORCH's claim is **right in sign for the actual PIL hazard** (β = 0.586 < 1) and **wrong as a general rule and wrong in mechanism**. For a genuine shared noise floor it predicts a null where the measured answer is an inversion.

It does not threaten the headline, for three independent reasons:

1. **The inputs are not narrowed** — §9, verified with asserts, commissioned.
2. **Even granting β = 0.586**, a measured 1.0014 back-solves to a true ratio of `exp(log(1.0014)/0.5861)` = **1.0024**. There is no effect hiding under the compression.
3. **The "nobody re-examines an arm that showed no effect" concern is pre-empted by design.** C2 (§2.3) is exactly that re-examination: planted effects are recovered through the same split channel at **0.9938–0.9974**, i.e. β ≈ 0.994 measured on known non-null effects. The null was earned against a positive control, not assumed.

---

## 11. Housekeeping for ORCH

- **`M115` is not in the `AGENTS.md` milestone ledger**, which ends at `M113`. The allocation needs recording.
- **The dispatching brief named no prior research.** M20 (`M20-deconvolution-ceiling-measured.md`), M41 (`M41-r3-kill-measured.md`) and M70 (`M70-through-focus-spectrum.md`) all bear directly on this question — M41 tested this exact proposal and killed it on the noise axis. Rule 43: an assertion of absence is a claim. All three were found by the rule-40 search and are cited throughout.
- Per rule 12 I have not verified my own work. The instrument is committed at `77c8d5e` and every control is re-runnable from `experiments/M115-deconv-headroom/src/`. What I *have* done is guard against transcription error: `verify_report.py` re-derives every quoted number from the raw per-block spectra with a separately-written code path (it does not import `m115lib` or reuse `s07`), and matches it against the literal text of this document — **17/17 claims re-derived and matched**. That verifier is itself commissioned by `negctl_report.py`, which plants six defects anchored on unique full strings and requires a RED for each: **baseline GREEN, 6/6 caught, restored GREEN**. A verifier that has not been shown able to fail is not evidence.
- The claims most worth an independent re-*choice* rather than a re-run are: the split channel's per-arm fairness (§7 falsifier 2), and the ringing edge-mask threshold (99th percentile of gradient magnitude), which I chose without a sensitivity sweep.
