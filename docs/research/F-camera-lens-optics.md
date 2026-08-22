# Workstream F — Camera & Lens Model Plugins: what they can know, and what it buys

**Date:** 2026-08-22 · **Scope:** Sony A7C II (ILCE-7CM2) + Sony FE 100mm F2.8 Macro GM OSS
**Label key:** `MEASURED` (real measurement, source named) · `MEASURED-LOCALLY` (I measured it on this machine) · `VERIFIED` (read the primary source) · `DERIVED` (I computed it; formula shown) · `UNVERIFIED`

---

## 0. Headline results

| # | Finding | Label |
|---|---|---|
| 1 | The lens is real. **Sony FE 100mm F2.8 Macro GM OSS, model code `SEL100M28GM`**. It is *not* the 90mm G, and *not* the 100mm STF GM (`SEL100F28GM`, a different lens). | VERIFIED |
| 2 | Max magnification is **1.4×** native, **2.8×** with SEL20TC. Not 1:1. This changes every DoF/diffraction number. | VERIFIED |
| 3 | **LensFun does not contain this lens.** It has the FE 90mm Macro G, not the 100mm Macro GM. External profile DBs are a dead end here. | VERIFIED |
| 4 | The ARW carries **Sony's own distortion / CA / vignetting correction coefficients**. This is the only per-lens profile source that actually covers this lens. | MEASURED-LOCALLY |
| 5 | **`FocusPosition2` is useless as a per-frame focus axis in macro.** Across a real 33-frame stack it takes exactly **two** values (56, 57). One LSB ≈ 3.1 mm ≈ **22× the depth of field**. | MEASURED-LOCALLY |
| 6 | **Inter-frame scale drift is real and large**: −1.012 % across the owner's 33-frame stack, perfectly linear, **≈ 42 px of corner displacement**. Translation-only alignment is broken from frame 2 onward. | MEASURED-LOCALLY |
| 7 | The scale centre is **~400 px from the image centre**. Assuming image centre is wrong. | MEASURED-LOCALLY |
| 8 | A photon-transfer noise model built from photonstophotos data **predicts the locally measured noise to ~2 %**, and independently reproduces the sensor's white level to **0.23 %**. | MEASURED + DERIVED |
| 9 | **ISO 400 is a second base ISO** (dual conversion gain). It has *more* dynamic range than ISO 320. Free quality for a light-starved macro rig. | MEASURED |
| 10 | The A7C II has **no published PDAF pattern**, and LibRaw exposes **no optical-black margin** on this file. Both close off techniques other stackers use. | VERIFIED + MEASURED-LOCALLY |

---

## 1. Lens identification — the owner's "Sony FE 2.8/100 Macro GM"

The owner's shorthand is **correct**, and resolves to a real, current product. This needed care because Sony sells two different 100 mm f/2.8 GM lenses.

| Lens | Sony model code | What it is |
|---|---|---|
| FE 100mm F2.8 **STF** GM OSS | `SEL100F28GM` | Apodisation-element portrait lens. **Not** a macro. 0.25× max. |
| FE 100mm F2.8 **Macro** GM OSS | **`SEL100M28GM`** | The macro. **This is the owner's lens.** |
| FE 90mm F2.8 Macro G OSS | `SEL90M28G` | The older, more common macro. **Not** the owner's lens. |

**Evidence chain (all primary):**

1. The owner's own files say so. Every frame in both local test brackets carries
   `LensModel : FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` and
   `LensType3 : Sony FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`.
   — MEASURED-LOCALLY, `exiftool -a -G1 C:\dev\macro\test\109MSDCF\DSC00024.ARW`
2. ExifTool's lens-ID table distinguishes them explicitly — VERIFIED, local `Sony.pm` (ExifTool 13.58):
   - `Sony.pm:183` → `32893 => 'Sony FE 100mm F2.8 Macro GM OSS'`
   - `Sony.pm:209` → `33094 => 'Sony FE 100mm F2.8 Macro GM OSS + 2X Teleconverter'`
   - `Sony.pm:132` → `32819 => 'Sony FE 100mm F2.8 STF GM OSS'` *(different lens, different ID)*
3. Sony's own product page resolves the model code — VERIFIED:
   - `https://www.sony.jp/ichigan/products/SEL100M28GM/spec.html` → title `FE 100mm F2.8 Macro GM OSS 主な仕様` (HTTP 200)
   - `https://www.sony.jp/ichigan/products/SEL100F28GM/spec.html` → title `FE 100mm F2.8 **STF** GM OSS 主な仕様` (HTTP 200) — confirms these are distinct products.

> Note: `sony.com` / `electronics.sony.com` / `sony.co.uk` all return **HTTP 403** to scripted fetches. Sony Japan (`sony.jp`) serves fine but is **Shift-JIS (cp932)** encoded — decode explicitly or the text is mojibake.

### 1.1 Verified specifications — SEL100M28GM

Source: `https://www.sony.jp/ichigan/products/SEL100M28GM/spec.html` and `.../feature_1.html` — all VERIFIED.

| Property | Value | Consequence for the stacker |
|---|---|---|
| Focal length | 100 mm | — |
| Optical formula | **17 elements / 13 groups** | — |
| Max aperture | f/2.8 | — |
| **Min aperture** | **f/22** | Hard clamp on the DoF/diffraction trade |
| Aperture blades | 11, circular | Smooth bokeh; irrelevant to merge |
| **Min focus distance** | **0.26 m** | — |
| **Max magnification** | **1.4×** (2.8× with SEL20TC) | Drives everything in §4 |
| Filter | 67 mm | — |
| Stabilisation | OSS (in-lens) | **Must be OFF for stacking** — see §2.6 |
| Teleconverters | SEL14TC (1.4×), SEL20TC (2.0×) | Owner uses SEL20TC |
| Focus mechanism | **Floating focus, 4× XD linear motor** | Internal focus → breathing is designed-down but non-zero |
| Focus ring | Sliding, with **magnification/distance scale**, range limiter | See §3.2 — the lens natively thinks in *magnification* |

**Focus breathing: could not confirm a measured figure.** Sony publishes no breathing number on either the spec or feature page (checked both; searched the decoded page text for `ブリージング` / `breathing` — no match). The lens uses a *floating focus* group, which is the design normally chosen to suppress breathing and close-range aberration, but that is an inference, not a measurement. **The tool should measure breathing itself** (§6.2) rather than ship an unverified constant.

---

## 2. The Sony A7C II sensor (ILCE-7CM2)

### 2.1 Raw geometry and levels — MEASURED-LOCALLY

`rawpy` / ExifTool on `C:\dev\macro\test\109MSDCF\DSC00024.ARW`:

| Field | Value | Source |
|---|---|---|
| Raw buffer | 7168 × 5120 | `raw_image.shape` |
| Visible | 7028 × 4688 | `raw_image_visible.shape` |
| `DefaultCropOrigin` / `DefaultCropSize` | 12, 8 / **7008 × 4672** | ExifTool SubIFD |
| CFA | **RGGB**, `raw_pattern = [[0,1],[3,2]]`, `color_desc = RGBG` | rawpy |
| Bit depth | 14 | `BitsPerSample` |
| Black level | **512**, uniform all four channels | `BlackLevel` + `black_level_per_channel` |
| White level | **16383** (SubIFD) / **15360** (SR2SubIFD) | ExifTool — *two different values, see below* |
| Camera WB | R 2930, G 1024, G2 1024, B 1518 | `WB_RGGBLevels` |
| Colour matrix | `1011 −97 111 / 243 937 −156 / 197 −8 835` (÷1024) | SR2SubIFD `ColorMatrix` |
| Pixel pitch | **5.12 µm** | DERIVED: 35.9 mm ÷ 7008 px |

Two notes that matter for a raw-native pipeline:

- **Two white levels.** `SubIFD:WhiteLevel = 16383` (the ADC ceiling) but `SR2SubIFD:WhiteLevel = 15360` (Sony's own "trust nothing above this" level). **Use 15360 for highlight-clipping decisions and 16383 only as the container maximum.** A merger that treats 15360–16383 as valid signal will merge non-linear near-clip data.
- **The noise floor straddles black.** Prior local work recorded a raw minimum of 498 against a black level of 512. Confirmed in principle: the pipeline must subtract black into a **signed** intermediate, never clamp at 0 before averaging, or it will introduce a positive bias in the deepest shadows that defeats cross-frame averaging.

### 2.2 No optical-black margin — MEASURED-LOCALLY (new finding)

`rawpy` reports `top_margin = 0`, `left_margin = 0`. The 140 columns and 432 rows beyond the visible area are **zero-filled padding**, not masked photosites:

```
RIGHT strip (5120,140)  mean 135.7  min 0  max 2504   <- partly image, partly zeros
BOTTOM strip (432,7168) mean 0.0    std 0.0           <- pure padding
```

**Consequence:** per-frame black-level calibration from masked pixels is **not available** through LibRaw on this body. The pipeline must trust the tagged `BlackLevel = 512`, or estimate residual black offset from the image itself. Any design that assumed "we'll just read the optical black" must be revised.

### 2.3 Photon transfer / noise model — MEASURED + DERIVED

**Primary source (MEASURED, Bill Claff, photonstophotos.net).** The chart data is embedded directly in the page HTML; the A7C II series is:

```
{ name: 'Sony ILCE-7CM2_14', fwc: 69634, unityEv: 7.13, loEv: 5.00, hiEv: 14.00, loDeltaEv: 1.00,
  data: [[5.00,2.24],[5.33,2.22],[5.67,2.14],[6.00,2.10],[6.33,2.05],[6.67,2.07],
         [7.00,0.56],[7.33,0.50],[7.67,0.44],[8.00,0.48], ... [14.00,0.18]] }
```
— `https://www.photonstophotos.net/Charts/RN_e.htm` (fetched 2026-08-22)

Decoding the axes (DERIVED, then cross-validated below):
- x is ISO in EV: `ISO = 100 · 2^(x − 5)`. Confirmed by `loEv=5.00 → ISO 100` and `hiEv=14.00 → ISO 51200`, which is exactly the A7C II's native range.
- y is `log2(read noise in e⁻)`, per the page's own tooltip code `Math.pow(2, this.yData[index])`.
- `unityEv = 7.13` is the ISO at which gain = 1 DN/e⁻ → **conversion gain `g(ISO) = ISO / 436.8` DN/e⁻**.
- `fwc = 69634 e⁻` is full-well at base ISO.

**Independent cross-validation (DERIVED).** Predicted saturation in DN at ISO 100:
`69634 e⁻ × 0.2285 DN/e⁻ = 15 908 DN` versus the locally measured `16383 − 512 = 15 871 DN`.
**Agreement: 0.23 %.** Two entirely independent sources (Claff's photon-transfer analysis and this camera's own tags) agree. The model is trustworthy.

#### The calibrated table

`g(ISO) = ISO/436.8` DN/e⁻ · `b = (RN_e · g)²` DN² · `sat_e = 15871/g` · `DR = log2(sat_e / RN_e)`

| ISO | g (DN/e⁻) | RN (e⁻) | RN (DN) | b (DN²) | sat (e⁻) | DR (stops) |
|---|---|---|---|---|---|---|
| 100 | 0.2285 | 4.72 | 1.079 | 1.165 | 69 470 | **13.84** |
| 125 | 0.2872 | 4.66 | 1.338 | 1.790 | 55 266 | 13.53 |
| 160 | 0.3635 | 4.41 | 1.602 | 2.567 | 43 662 | 13.27 |
| 200 | 0.4569 | 4.29 | 1.959 | 3.837 | 34 735 | 12.98 |
| 250 | 0.5743 | 4.14 | 2.378 | 5.657 | 27 633 | 12.70 |
| 320 | 0.7270 | 4.20 | 3.053 | 9.318 | 21 831 | **12.34** ← worst |
| **400** | 0.9138 | **1.47** | 1.347 | 1.815 | 17 368 | **13.52** ← DCG kicks in |
| 500 | 1.1487 | 1.41 | 1.625 | 2.639 | 13 817 | 13.25 |
| 800 | 1.8277 | 1.39 | 2.549 | 6.498 | 8 684 | 12.60 |
| 1600 | 3.6553 | 1.31 | 4.790 | 22.94 | 4 342 | 11.69 |
| 3200 | 7.3107 | 1.37 | 9.987 | 99.73 | 2 171 | 10.63 |
| 6400 | 14.621 | 1.31 | 19.16 | 367.1 | 1 085 | 9.69 |
| 12800 | 29.243 | 1.21 | 35.26 | 1243 | 543 | 8.81 |
| 25600 | 58.485 | 1.16 | 67.65 | 4576 | 271 | 7.87 |
| 51200 | 116.97 | 1.13 | 132.5 | 17560 | 136 | 6.90 |

#### Dual conversion gain and the ISO-invariance breakpoint

- **The DCG switch is between ISO 320 and ISO 400.** Read noise collapses from **4.20 e⁻ → 1.47 e⁻** (a 2.9× drop) in one 1/3-stop step. MEASURED.
- Confirmed independently by the PDR chart, which shows dynamic range *rising* across that step (10.16 → 10.39 EV) despite the ISO increase — `https://www.photonstophotos.net/Charts/PDR.htm`, series `Sony ILCE-7CM2`. MEASURED.
- **Above ISO 400 the camera is effectively ISO-invariant**: read noise in electrons is flat at 1.1–1.5 e⁻ all the way to ISO 51200. Below ISO 400 it is flat at ~4.2–4.7 e⁻.

> **Capture recommendation (actionable, free):** ISO 320 is the worst setting on the camera — 1.2 stops *worse* than ISO 400. For a light-starved macro rig at f/8–f/11, **ISO 400 is a second base ISO**. The tool should warn on ISO 200–320 and suggest 400.

#### Local validation of the model — MEASURED-LOCALLY

I fitted a photon transfer curve directly from `DSC00024.ARW` (ISO 160). Method: green sublattice, second difference along x (`d2 = G[:,2:] − 2G[:,1:−1] + G[:,:−2]`, `var(d2) = 6·var(pixel)`) to null linear gradients, tiled into 16×16 patches, then the **5th percentile** of patch variance per signal bin to reject textured patches.

| mean (DN) | n patches | var 5th pct | var 10th pct |
|---|---|---|---|
| 137 | 1714 | 34.98 | 37.61 |
| 361 | 2544 | 98.62 | 104.89 |
| 627 | 1406 | 177.16 | 187.50 |
| 1186 | 859 | 345.26 | 368.19 |
| 2030 | 15360 | 613.90 | 645.23 |

Fit: **σ² = 0.3055·S − 12.5 DN²**.
Model prediction at ISO 160: **g = 0.3635 DN/e⁻**.

The measured slope is 16 % low, and that is **exactly the expected bias**: taking the 5th percentile of a variance estimate from 256 samples biases low by `1.64 · √(2/255) ≈ 14.6 %`. Bias-correcting: `0.3055 × 1.171 = 0.358` vs predicted `0.3635` — **agreement within 2 %**. The intercept is not identifiable from this frame (no patches below ~130 DN, where the 2.6 DN² read-noise term would show), hence the physically meaningless negative value; this is a limitation of the data, not of the model.

**Verdict: the photon-transfer model is validated. Ship it.**

#### The recommended model

```
σ²(S, ISO) = a·S + b        [DN², S = DN above black]
  a = g(ISO)         = ISO / 436.8                 DN/e⁻
  b = (RN_e(ISO)·g)² = read-noise variance          DN²
```

**Why this matters for a focus stacker — the actual mechanism.** A focus measure is a high-pass energy statistic. On a *textureless* patch, that energy is **pure noise**, and its expected value is a known function of local signal level. A naive "sharpest wins" merger therefore performs *argmax over noise* in flat regions — it systematically selects the noisiest frame, and the merged output ends up **noisier than any single input**. The prior project measured exactly this failure on this camera: stack output was **2.3–4.6× noisier** than the source frames' cross-frame σ in flat zones, and up to **1.82× more spatially noisy than a single source frame** in flat highlights (`C:\dev\macro\research\empirical_findings.md` §2b).

A calibrated `σ²(S, ISO)` fixes this in three concrete places:

1. **Focus-measure normalisation.** Compare `focus_energy / σ²(S,ISO)` instead of raw energy. This is a signal-to-noise ratio, not an energy, so it is comparable across frames *and* across brightness. Patches whose energy is consistent with pure noise get a focus score near 1 and are excluded from selection.
2. **A principled "no signal here" threshold.** Declare a pixel *undecidable* when focus energy fails a χ² test against `σ²`. Undecidable pixels should be **averaged across frames** (√N noise reduction), not selected from. This is the single highest-value use.
3. **Merge weighting.** Weight each frame's contribution by `1/σ²` (inverse-variance / maximum-likelihood weighting), which is the statistically optimal linear combination and automatically down-weights darker or higher-ISO frames.

For denoising and wavelet thresholding, variance-stabilise first with the **generalized Anscombe transform**, which maps the signal-dependent noise to unit variance so that ordinary Gaussian estimators become correct:

```
T(S) = (2/a)·√( a·S + (3/8)a² + b )       →  Var[T] ≈ 1
```

### 2.4 ARW format: compression and whether it damages focus measurement

LibRaw's enum is the authoritative decoder — VERIFIED, `C:\dev\macro\deps\libraw\libraw\libraw_types.h` (`libraw_sony_info_t`):

```c
ushort SonyRawFileType; /* 0 uncompressed 14-bit
                           1 uncompressed 12-bit
                           2 compressed raw (LOSSY)      <- the 11+7 delta scheme
                           3 lossless compressed raw
                           4 lossless compressed raw v.2 (ILCE-1) */
```

**The owner's files are type 4** — MEASURED-LOCALLY:
```
SonyRawFileType : Sony Lossless Compressed RAW 2
RAWFileType     : Lossless Compressed RAW
FileFormat      : ARW 5.0.1
```
The SubIFD is **tiled** (`TileWidth 512`, `TileLength 512`), which is the ARW 5.x lossless-v2 container.

| Setting on camera | `SonyRawFileType` | Lossy? | Use for stacking? |
|---|---|---|---|
| Uncompressed | 0 | No | Fine, but 2× the disk for no gain |
| **Lossless Compressed (L)** | **4** | **No** | ✅ **What the owner already shoots. Correct.** |
| Compressed | 2 | **Yes — 11+7 bit delta** | ❌ Avoid |

**Does the lossy mode damage focus measurement?** The Sony lossy scheme splits each 16-pixel same-colour run into a block, stores the min and max at 11-bit, and encodes the other 14 pixels as 7-bit deltas interpolated between them. Its damage is concentrated at **high-local-contrast edges** — precisely where a focus measure does its work — and it produces the well-known posterisation/"star-eater"-adjacent artefacts on sharp tonal steps. Since a focus stacker's entire signal is high-frequency edge energy, **lossy ARW is the worst possible input format for this application.**

> **Capture recommendation:** Lossless Compressed (or Uncompressed). The owner is already correct; the tool should nonetheless **detect `SonyRawFileType == 2` and warn loudly**, because the setting is easy to trip and the artefact is subtle.

Verified mechanism claim confidence: the *existence* and *values* of the enum are VERIFIED from LibRaw; the *bit layout* of the 11+7 scheme is UNVERIFIED here (I did not read a decoder implementation of it in this session) — but the type-4 status of the owner's files, which is what actually matters, is MEASURED-LOCALLY.

### 2.5 PDAF pixels

**Question 1 — is there a published PDAF mask for this body? No.** VERIFIED against the primary source, RawTherapee's `camconst.json` (dev branch, fetched 2026-08-22, `https://raw.githubusercontent.com/Beep6581/RawTherapee/dev/rtengine/camconst.json`).

Bodies that carry a `pdaf_pattern` entry:
`ILCE-6000`, `ILCE-6100/6400/6600`, `ILCE-6300/6500`, `ILCE-7RM2`+`DSC-RX1RM2`, `ILCE-7M3`, `ILCE-7RM3`, `ILCE-7RM4`, `ILCE-7CR`+`ILCE-7RM5`, `ILCE-9`+`ILCE-9M2`, `ZV-1`, plus Canon 550D, Nikon Z6/Z7/Z50, Fuji GFX100.

- **`ILCE-7CM2` does not appear in `camconst.json` at all.**
- `ILCE-7M4` (same sensor generation) appears, but **without** a `pdaf_pattern`.

So no stacker, darktable, or RawTherapee currently corrects PDAF artefacts on this body — because nobody has mapped it. The prior local investigation reached the same conclusion and then attempted empirical detection, downgrading its own verdict **YELLOW → 🔴 RED** (`C:\dev\macro\research\PROBE10_PDAF_MASK.md`). Its reasoning — that the BIONZ XR generation likely abandoned the simple full-row layout that RawTherapee's `PDAFLinesFilter` can express — is plausible and consistent with the 4-year gap in published patterns, but remains an inference.

**Question 2 (bonus) — can PDAF pixels be read as a depth cue?** In principle yes: the disparity `(left − right)/(left + right)` at matched half-masked pairs is a defocus signal, and this is exactly how the camera focuses. In practice, for this project: **no.**

- You cannot use pixels you cannot locate. The mask is unpublished and the local attempt to recover it empirically failed.
- Even with the mask, PDAF disparity is sparse (a fraction of rows), noisy at macro apertures, and the baseline collapses as you stop down — at the **N_eff = 20–40** the owner actually shoots (§4), the PDAF baseline is essentially gone.
- The stack itself already contains a far denser and more reliable depth cue: the focus measure across 20–60 frames.

**Recommendation: do not pursue PDAF, for either artefact correction or depth.** If PDAF artefacts ever prove visible, handle them as generic outliers — a cross-frame robust rejection step (median/MAD across the aligned stack) removes fixed-pattern anomalies without knowing where they are, which is strictly more general than a hard-coded mask.

### 2.6 One more thing the metadata revealed — MEASURED-LOCALLY

```
ImageStabilization            : On
ElectronicFrontCurtainShutter : On
```

**In-body/in-lens stabilisation was ON for a tripod focus stack.** IBIS parks the sensor at a slightly different position per frame, injecting random sub-pixel-to-multi-pixel translation *and* a small rotation between frames. This is very likely a contributor to the frame-to-frame translation measured in §5.1. A camera-model plugin should **flag `ImageStabilization == On` together with a long exposure and a static release mode as a probable capture error.** This is a zero-cost, high-value check.

`ElectronicFrontCurtainShutter: On` at 1.3 s is harmless (EFCS artefacts appear at short exposures with fast lenses), but is worth recording.

---

## 3. Focus-position metadata — the negative result

### 3.1 What the encoding actually is

ExifTool's `Composite:FocusDistance2` is defined as — VERIFIED, local `Sony.pm`:

```perl
Require => { 0 => 'Sony:FocusPosition2', 1 => 'FocalLengthIn35mmFormat' },
ValueConv => q{
    return undef unless $val;
    return 'inf' if $val >= 255;
    return (2**($val/16-5) + 1) * $val[1] / 1000;
},
```

So:
```
distance_m = ( 2^(FocusPosition2/16 − 5) + 1 ) · FocalLengthIn35mmFormat_mm / 1000
```

**DERIVED check:** `FocusPosition2 = 57`, `FL35 = 200 mm` → `(2^(57/16−5) + 1) × 200/1000 = (0.3691 + 1) × 0.2 = 0.2738 m`. ExifTool reports exactly `0.2738 m`. ✅ Formula confirmed.

**But ExifTool's own source disclaims it** — VERIFIED, verbatim from `Sony.pm`:

> *"(NOTE: This calculation may be wrong. 'Focus Distance 2 is the result of an erroneous user supplied formula to exiftool. It does use data embedded in the raw file, but it is not the data. The actual embedded data seems to be **proportional to magnification** not a focus distance. The camera needs to calculate magnification for translation stabilization.'"*

This disclaimer is **strongly corroborated** by Sony's own description of `SEL100M28GM`, whose focus ring carries a **magnification/distance scale** (`倍率/距離目盛`) — the lens reports magnification natively. So `FocusPosition2` is best understood as a coarse **magnification index**, not a distance.

### 3.2 The killer measurement — MEASURED-LOCALLY

`exiftool -T -FileName -FocusPosition2 -FocusDistance2` over the owner's two real brackets:

| Bracket | Frames | Distinct `FocusPosition2` values |
|---|---|---|
| `109MSDCF` | 22 | **2** — `57` (×19), `58` (×3) |
| `119MSDCF` | 33 | **2** — `56` (×3), `57` (×30) |

**Quantisation vs. what we need:**

| Quantity | Value |
|---|---|
| One LSB of `FocusPosition2` (56→57) | 0.2707 → 0.2738 m = **3.1 mm** |
| DoF at m≈1.4, f/5.6 nominal, CoC = 2 px | **0.140 mm** (§4.3) |
| **Ratio** | **≈ 22× coarser than the DoF** |
| At CoC = 1 px | ≈ 44× coarser |

**Conclusion: `FocusPosition2` cannot resolve a macro focus step. It is off by 1.5 orders of magnitude.** Two values across 33 frames is not a depth axis; it is a constant with a rounding wobble.

It retains exactly two legitimate uses:
- A **sanity check** — a large jump means the focus ring was bumped mid-stack, which is a capture error worth reporting.
- A **coarse magnification prior** (`m ≈ 2^(FP2/16−5)`-ish, uncalibrated) to seed the DoF/step-size advisor in §4, where 20 % accuracy is fine.

It must **not** be used to order frames, to scale them, or to build a metric depth axis.

### 3.3 LibRaw exposure — VERIFIED, with a naming trap

`imgdata.makernotes.sony.FocusPosition` **does exist** in LibRaw 0.22.1 — VERIFIED at `C:\dev\macro\deps\libraw\libraw\libraw_types.h:704`:

```c
ushort FocusLocation[4];
ushort FocusPosition;                    // init in 0xffff
```

**Trap:** the surrounding fields (`Sony0x9400_*`, `AFAreaModeSetting`, `FocusLocation`) place this in Sony's Tag9050 group, which is ExifTool's **`FocusPosition2`** — *not* ExifTool's `FocusPosition` (tag `0x09bb`, which `Sony.pm:~183` restricts to `DSLR-A200…A900` and is absent on this body, confirmed by the `-` in my local dump). So:

> `LibRaw sony.FocusPosition` ≡ `ExifTool FocusPosition2`. Sentinel for "absent" is `0xffff`.

Given §3.2, this is a field worth *reading and recording* but not *relying on*.

---

## 4. Macro optics: diffraction, depth of field, and step size

### 4.1 Formulas (all DERIVED from standard thin-lens/diffraction theory)

```
Effective aperture:      N_eff = N · (1 + m/p)          p = pupil magnification (p=1 if symmetric)
Total depth of field:    DoF   = 2·N·c·(1 + m/p) / m²  =  2·N_eff·c / m²
Airy disk diameter:      d_Airy = 2.44 · λ · N_eff       (first zero, λ = 550 nm)
Diffraction MTF cutoff:  f_c = 1 / (λ · N_eff)           cycles/mm
Sensor Nyquist:          f_N = 1 / (2 · pitch) = 97.7 cy/mm  (pitch = 5.12 µm)
Combined blur:           d_total ≈ √( d_defocus² + d_Airy² )
```
`N` is the **nominal** aperture set on the camera. Note that with the SEL20TC fitted, the camera **already reports the TC-corrected f-number** (`MaxApertureValue = 5.6` = 2.8 × 2), so `N` from EXIF must **not** be doubled again.

### 4.2 Diffraction on a 33 MP full-frame sensor

| N_eff | Airy dia (µm) | Airy / pixel | MTF cutoff (cy/mm) | cutoff ÷ Nyquist |
|---|---|---|---|---|
| 2.8 | 3.76 | 0.73 | 649 | 6.65 |
| 4.0 | 5.37 | 1.05 | 455 | 4.65 |
| 5.6 | 7.52 | 1.47 | 325 | 3.32 |
| **8.0** | **10.74** | **2.10** | 227 | 2.33 |
| 11.0 | 14.76 | 2.88 | 165 | 1.69 |
| 16.0 | 21.47 | 4.19 | 114 | 1.16 |
| **18.6** | 24.9 | 4.87 | **97.7** | **1.00** ← cutoff hits Nyquist |
| 22.0 | 29.52 | 5.77 | 83 | 0.85 |
| 32.0 | 42.94 | 8.39 | 57 | 0.58 |
| 45.0 | 60.39 | 11.79 | 40 | 0.41 |

Three thresholds (DERIVED):
- **N_eff ≈ 3.8** — Airy disk = 1 pixel. Below this the lens outresolves the sensor.
- **N_eff ≈ 7.6** — Airy disk = 2 pixels (Nyquist). **Diffraction begins to dominate here.**
- **N_eff ≈ 18.6** — diffraction MTF cutoff falls *to* Nyquist. Beyond this the sensor is recording nothing at pixel scale; extra megapixels are wasted.

**The macro trap.** `N_eff = N(1+m)` means magnification silently eats aperture:

| m | f/2.8 → | f/5.6 → | f/11 → |
|---|---|---|---|
| 0.25 | 3.5 | 7.0 | 13.8 |
| 0.50 | 4.2 | 8.4 | 16.5 |
| 1.00 | 5.6 | 11.2 | 22.0 |
| **1.40** (lens max) | 6.7 | 13.4 | **26.4** |
| 2.00 | 8.4 | 16.8 | 33.0 |
| **2.80** (with SEL20TC) | 10.6 | **21.3** | **41.8** |

At the owner's 1.4× native max, **f/8 nominal is already N_eff = 19.2** — past the point where the sensor resolves anything. At 2.8× with the TC, **even wide open (f/5.6 nominal with the TC) gives N_eff = 21.3**, which is *already beyond Nyquist cutoff*. The `109MSDCF` bracket was shot at **f/11 nominal**, i.e. **N_eff ≈ 26–42** depending on actual magnification — deep in diffraction.

> This is the most important optical fact for this gear: **at high magnification the owner has no usable aperture range left.** The lens's f/22 minimum is unreachable in practice. Stacking is not a luxury here, it is the only way to get depth, because stopping down cannot buy any.

### 4.3 Depth of field / optimal step size

`DoF = 2·N_eff·c/m²`, in **µm**, `N` = nominal aperture.

**CoC = 1 pixel (5.12 µm)** — aggressive, pixel-sharp:

| m | f/2.8 | f/4 | f/5.6 | f/8 | f/11 | f/16 |
|---|---|---|---|---|---|---|
| 0.25 | 573.4 | 819.2 | 1146.9 | 1638.4 | 2252.8 | 3276.8 |
| 0.50 | 172.0 | 245.8 | 344.1 | 491.5 | 675.8 | 983.0 |
| 0.75 | 89.2 | 127.4 | 178.4 | 254.9 | 350.4 | 509.7 |
| 1.00 | 57.3 | 81.9 | 114.7 | 163.8 | 225.3 | 327.7 |
| 1.40 | 35.1 | 50.2 | 70.2 | 100.3 | 137.9 | 200.6 |
| 2.00 | 21.5 | 30.7 | 43.0 | 61.4 | 84.5 | 122.9 |
| 2.80 | 13.9 | 19.9 | 27.8 | 39.7 | 54.6 | 79.4 |

**CoC = 2 pixels (10.24 µm)** — practical, Nyquist-matched:

| m | f/2.8 | f/4 | f/5.6 | f/8 | f/11 | f/16 |
|---|---|---|---|---|---|---|
| 0.25 | 1146.9 | 1638.4 | 2293.8 | 3276.8 | 4505.6 | 6553.6 |
| 0.50 | 344.1 | 491.5 | 688.1 | 983.0 | 1351.7 | 1966.1 |
| 0.75 | 178.4 | 254.9 | 356.8 | 509.7 | 700.9 | 1019.4 |
| 1.00 | 114.7 | 163.8 | 229.4 | 327.7 | 450.6 | 655.4 |
| 1.40 | 70.2 | 100.3 | 140.4 | 200.6 | 275.9 | 401.2 |
| 2.00 | 43.0 | 61.4 | 86.0 | 122.9 | 169.0 | 245.8 |
| 2.80 | 27.8 | 39.7 | 55.6 | 79.4 | 109.2 | 158.8 |

**The step-size advisor.** The optimum is a genuine two-sided constrained optimisation, and the tool can solve it:

1. Pick the aperture that maximises DoF **subject to** `N_eff ≤ 8` (Airy ≤ 2 px). Stopping down further *increases* the DoF number in the table but the extra depth is blurred by diffraction — you gain depth and lose resolution everywhere.
2. Set `step = DoF(c = 2 px) / k`, `k ≈ 1.3–1.5` for overlap margin.
3. Report `frames = subject_depth / step`.

Worked example at **m = 1.0**: the `N_eff ≤ 8` constraint gives `N = 8/(1+1) = f/4`. DoF(2 px) = **164 µm**. With `k = 1.4`, step ≈ **117 µm**. For a 4 mm subject → **34 frames**. That lands squarely in the owner's stated 20–60 frame envelope, which is a good sign the model is calibrated to reality.

At **m = 2.8** (SEL20TC): `N_eff ≤ 8` is **unreachable** — even wide open `N_eff = 10.6`. The advisor must say so: *"diffraction-limited at all apertures; shoot wide open, expect ~28 µm steps, ~140 frames per mm."*

---

## 5. Registration geometry: rail vs. breathing, telecentricity, optical axis

### 5.1 The measurement that settles it — MEASURED-LOCALLY

I registered frames from the owner's real 33-frame bracket (`119MSDCF`) with OpenCV `findTransformECC` in `MOTION_AFFINE`, on the green Bayer sublattice downsampled 4×, against frame 24:

| Frame Δ | ECC | scale | Δscale | sx | sy |
|---|---|---|---|---|---|
| +3 | 0.99997 | 0.99902 | −0.098 % | 0.99902 | 0.99901 |
| +8 | 0.99985 | 0.99745 | −0.255 % | 0.99746 | 0.99744 |
| +16 | 0.99961 | 0.99488 | −0.512 % | 0.99490 | 0.99485 |
| +24 | 0.99949 | 0.99236 | −0.764 % | 0.99240 | 0.99231 |
| +32 | 0.99941 | 0.98988 | **−1.012 %** | 0.98993 | 0.98982 |

Three things fall straight out:

1. **The drift is large.** −1.012 % over the stack. On a 7008 × 4672 frame the half-diagonal is 4211 px, so this is **≈ 42.6 px of corner displacement** end-to-end, and **≈ 1.33 px per single frame step**. A translation-only aligner is already sub-par between *adjacent* frames and catastrophic across the stack.
2. **The drift is almost perfectly linear** in frame index (−0.0316 %/frame; the five points fit a straight line to within 0.005 %). It is therefore *predictable* — a one-parameter prior can seed alignment and constrain the search, which is both a quality and a speed win.
3. **The drift is isotropic.** `sx` and `sy` agree to 1 × 10⁻⁵ at every baseline. This is a pure **magnification** change about a point, not a shear, not an anisotropic perspective effect.

**Magnitude cross-check against theory (DERIVED).** For a rail, `m = f/(u−f)` gives `d(scale)/dz = m/f` per mm of travel. With `f = 200 mm` (TC fitted) and `m ≈ 1`, 1.012 % implies ≈ 2.0 mm of total rail travel over 32 frames = **63 µm/frame** — entirely sensible for this subject, and consistent with the DoF table (§4.3 gives 140–229 µm at these settings, so the owner is oversampling ~2–3×, which is good practice). Theory and measurement agree.

### 5.2 The two geometries are genuinely different

| | **Focus-driven** (turn the ring / focus bracketing) | **Rail-driven** (move the camera) |
|---|---|---|
| Entrance pupil (viewpoint) | **Fixed** | **Moves** |
| Parallax between depths | **None** | **Yes** — this is the defining difference |
| Occlusion relationships | Constant | **Change** — background is revealed/hidden |
| In-focus slice magnification | **Changes** (focus breathing) | Constant |
| Whole-frame magnification | Changes (breathing) | Changes (`dm/m = −m/f` per mm) |
| Correct alignment model | **Global similarity**: scale about optical axis + translation | **Depth-dependent**: not expressible as any global 2D warp |
| Residual after global fit | ~0 | Parallax at depth discontinuities |
| Effective aperture across stack | **Varies** (`N_eff = N(1+m)`, m changes) | **Constant** |

**The geometric argument favours focus-driven.** Because the viewpoint is fixed, *every* frame is a pure resampling of the same pinhole projection; a global similarity transform is not an approximation, it is exact (modulo distortion and pupil shift). With a rail, no global 2D warp can be correct — points at different depths move by different amounts, by construction. That residual is what produces the classic focus-stacking halo at depth edges.

**But the practical argument is more mixed**, and honesty requires saying so:
- Focus-driven at high magnification has *limited range*: at 1.4× the focus travel between MFD and the end of the useful macro range is short, and the ring's mechanical resolution becomes the limiting factor.
- Focus-driven changes `N_eff` across the stack (because `m` changes), so exposure and diffraction blur drift frame to frame. Rail keeps both constant.
- Rail parallax is **small when the subject depth is small relative to the working distance**, which in macro it usually is (mm of depth at ~260 mm working distance).
- The owner already shoots rail (`FocusMode: Manual`, focus constant across the stack — §3.2).

**What the tool must do:** *detect which one it is* and switch models. That detection is free and reliable:

```
if FocusPosition2 varies across the stack   -> focus-driven -> global similarity model
if FocusPosition2 is constant but scale drifts -> rail-driven -> similarity + depth-aware residual
```
This is, notably, the **one genuinely valuable use of `FocusPosition2`** — as a *classifier*, where its 2-level resolution is sufficient, rather than as a *measurement*, where it is useless.

### 5.3 Telecentricity

A lens is **image-space telecentric** if the exit pupil is at infinity, so chief rays hit the sensor parallel to the axis. Then magnification does **not** depend on the axial position of the image plane, and defocus produces a symmetric blur with **no scale change**.

Real macro lenses, including this one, are **not** telecentric. The exit pupil sits at a finite distance `z_xp` behind the lens, so chief rays land at an angle increasing with field height. Consequences:

1. Defocusing by `Δz` scales the image by approximately `1 + Δz/z_xp` — **defocus and magnification are coupled**. This is the mechanism behind focus breathing.
2. The blur circle is not centred on the in-focus image point; it is displaced radially. This makes the defocus PSF **field-dependent**, so a single global PSF model is wrong toward the corners.
3. Pupil magnification `p ≠ 1` means `N_eff = N(1 + m/p)` genuinely needs `p`. For `p = 1` (assumed in §4) the tables are right; for a retrofocus or telephoto-ish design `p` can be 0.5–2, changing `N_eff` by tens of percent.

**Is the correction a pure scale about the optical axis?** To first order, **yes** — and my measurement supports this: `sx ≈ sy` to 1 × 10⁻⁵, and affine ECC stays ≥ 0.9994. But it is *not exact*, for three reasons:
- Distortion is not scale-invariant: if the lens has residual distortion `r' = r(1 + k1 r² + …)`, then scaling the image and correcting distortion **do not commute**. The right order is *undistort → scale → (re-distort if desired)*.
- Lateral CA scales differently per channel, so the correct scale factor is mildly wavelength-dependent.
- The rail case adds true parallax on top (§5.2), which is not a scale at all.

**Practical model:** undistort to a rectilinear frame using the in-camera coefficients (§6.1), then a **4-DoF similarity (isotropic scale, rotation, tx, ty) about the estimated optical centre** — with a robust/depth-aware residual stage on top for the rail case.

### 5.4 The optical axis / principal point — MEASURED-LOCALLY

Scale-correcting a stack requires the **centre of scaling**. The fixed point of the affine map `x' = Ax + t` is `x* = (I − A)⁻¹ t`; for `A ≈ sI` this is `x* = t/(1−s)`.

Applying that to my §5.1 fits (green-lattice px; lattice centre = (1757, 1172)):

| Frame Δ | 1−s | t (px) | fixed point x* | offset from centre |
|---|---|---|---|---|
| +8 | 0.00255 | (4.4, 2.5) | (1725, 980) | (−32, −192) |
| +16 | 0.00512 | (8.0, 4.8) | (1563, 938) | (−194, −234) |
| +24 | 0.00764 | (12.8, 7.4) | (1675, 969) | (−82, −203) |
| +32 | 0.01012 | (17.1, 9.8) | (1690, 968) | (−67, **−204**) |

The `+3` baseline is omitted: `1−s = 0.00098` makes the division numerically meaningless.

The centre of scaling sits consistently at roughly **(−100, −205) green-lattice px** from the image centre — i.e. **≈ (−200, −410) full-resolution pixels**, and the vertical component is stable to ±20 px across independent baselines. It is **not** the image centre.

**How is the true optical centre obtained?** In order of practicality:

1. **Estimate it from the stack** (recommended). It is the fixed point of the fitted inter-frame similarity, exactly as computed above. Solve for it jointly across all frames — with 20–60 frames and a linear scale ramp, it is very well constrained. **Costs nothing beyond the alignment you already run.**
2. **From a lens profile.** Adobe LCP stores `ImageXCenter`/`ImageYCenter`; DNG `WarpRectilinear` opcodes carry an explicit optical centre. Neither exists for this lens (§6).
3. **From a calibration target.** Accurate but requires user effort; not appropriate as a default.

**Caveat, stated plainly:** with a single rail stack I *cannot* separate the true optical axis from a rail that is slightly tilted or yawed relative to it. A tilted rail contributes a linear translation ramp that biases the apparent fixed point. The 410 px vertical offset is therefore an *apparent* scale centre — which is exactly what the aligner needs — but should **not** be cached and reused as a lens-intrinsic principal point across sessions. **Estimate per stack.**

---

## 6. Lens correction profiles: where they actually come from

### 6.1 Sony's in-camera profile — the winner

The ARW carries Sony's own correction coefficients. MEASURED-LOCALLY from `DSC00024.ARW`:

```
[SubIFD] DistortionCorrParams          : 16 0 -1 -2 -3 -4 -5 -7 -8 -11 -12 -13 -13 -13 -12 -10 -7
[SubIFD] VignettingCorrParams          : 16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
[SubIFD] ChromaticAberrationCorrParams : 32 -2304 -2304 ... 128 128
[Sony]   DistortionCorrParams          : -2 -2 -2 -3 -4 -6 -8 -11 -12 -14 -14 -15 -14 -13 -10 -7
[Sony]   VignettingCorrParams          : 0 0 ... 16 7968
[Sony]   ChromaticAberrationCorrParams : -2242 -2248 ... 237 164
```

Structure — VERIFIED from ExifTool `Sony.pm` (Tag9405b, offsets `0x064a` / `0x066a` / `0x06ca`):

| Tag | Format | Meaning |
|---|---|---|
| `VignettingCorrParams` | `int16s[16]` | 16 radial knots |
| `ChromaticAberrationCorrParams` | `int16s[32]` | **two** 16-knot splines (R and B lateral scale) |
| `DistortionCorrParams` | `int16s[16]` | 16 radial knots; `Sony.pm` gives `PrintConv = sprintf("%.0f%%", $val/10.24)` — **the scale factor is /1024 as a fraction, i.e. units of 1/10.24 percent** |

These are **16-knot radial lookup tables sampled along the image diagonal**, not polynomial coefficients — which is actually *better* for our purposes (no model-fit error, direct interpolation).

**This is a real, working, open-source-validated path.** darktable consumes exactly these tags — VERIFIED, `darktable-org/darktable:src/common/exif.cc`:

```c
/* Sony lens correction data */
if(Exiv2::versionNumber() >= EXIV2_MAKE_VERSION(0, 27, 4)
   && ((_exif_read_exif_tag(exifData, &posd, "Exif.SubImage1.DistortionCorrParams")
        && _exif_read_exif_tag(exifData, &posc, "Exif.SubImage1.ChromaticAberrationCorrParams")
        && _exif_read_exif_tag(exifData, &posv, "Exif.SubImage1.VignettingCorrParams"))
       || (_exif_read_exif_tag(exifData, &posd, "Exif.Image.0x7037") ...)))
{
  img->exif_correction_type = CORRECTION_TYPE_SONY;
  img->exif_correction_data.sony.nc = nc;
  for(int i = 0; i < nc; i++) {
    img->exif_correction_data.sony.distortion[i] = posd->toLong(i + 1);
    img->exif_correction_data.sony.ca_r[i]       = posc->toLong(i + 1);
    ...
```

Note `toLong(i + 1)` — **element 0 is the count (16 or 32), not data.** Our dump shows exactly that: `16 0 -1 -2 ...`. Also note darktable's DNG round-trip mapping: `0x7037` = distortion, `0x7035` = CA, `0x7032` = vignetting.

**Important caveat — MEASURED-LOCALLY.** The camera recorded `DistortionCorrection: Off`, `ChromaticAberrationCorrection: Off`, `VignettingCorrection: Auto (ILCE-1)`, and the vignetting params are **all zero**. So for *this* lens on *this* body, Sony supplied a distortion curve and a CA curve but a null vignetting curve. Two implications:
- Vignetting correction from metadata is a **no-op here** — don't build a feature around it for this lens.
- The distortion curve is small: peak `−15/10.24 ≈ −1.5 %`. Non-trivial at 7008 px (≈ 50 px at the edge) but a smooth, monotonic radial term.

**LibRaw does not decode these.** I grepped `libraw_types.h` for all `Focus*` and inspected `libraw_sony_info_t`; there is no distortion/vignetting/CA correction field. The Rust pipeline must **parse the maker-note tags itself** (via a TIFF/EXIF reader) rather than expecting LibRaw to hand them over. This is a concrete, non-obvious implementation constraint.

### 6.2 LensFun — does not cover this lens

VERIFIED by fetching the database directly (2026-08-22):

| File | Result |
|---|---|
| `data/db/mil-sony.xml` (mirrorless) | Contains `FE 90mm f/2.8 Macro G OSS`, `FE 50mm f/2.8 Macro`, `E 30mm f/3.5 Macro`. **No `FE 100mm` entry of any kind.** |
| `data/db/slr-sony.xml` (A-mount) | Contains only `Minolta/Sony AF 100mm F2.8 Macro (D)` — a different, film-era A-mount lens. |

Exact queries run against the fetched XML: `FE 100mm`, `Macro GM`, `100mm`, `90mm`, `Macro`. The 100 mm Macro GM is **absent**. (This is genuine absence from the file I fetched, not a failed search.)

For reference, what a LensFun entry *would* give us (the 90mm G, `mil-sony.xml:1475–1495`):
```xml
<lens>
  <maker>Sony</maker>
  <model>FE 90mm f/2.8 Macro G OSS</model>
  <mount>Sony E</mount>
  <cropfactor>1</cropfactor>
  <calibration>
    <distortion model="poly3" focal="90" k1="-0.00136"/>
    <tca model="poly3" focal="90" br="0.0000041" vr="0.9999383" bb="-0.0000058" vb="1.0000569"/>
    <vignetting model="pa" focal="90" aperture="2.8" distance="0.28" k1="-0.0913" k2="-0.2538" k3="0.0786"/>
    ... (5 distances × 5 apertures)
  </calibration>
</lens>
```
Note it **is** parameterised by focus distance — LensFun models the distance dependence of vignetting. But `distortion` has a single `k1` with no distance term, so LensFun would **not** model breathing either.

**Verdict: LensFun is not a usable source for this lens.** Support it as a generic fallback for *other* gear, not as the path for the flagship profile.

### 6.3 Adobe LCP — format and availability

- **Format:** LCP files are **XMP/RDF XML** (despite the opaque extension), so they are straightforwardly parseable with any XML reader. Relevant fields include `stCamera:Lens`, `stCamera:FocalLength`, `stCamera:ApertureValue`, `stCamera:FocusDistance`, `stCamera:PerspectiveModel` (with `RadialDistortParam1..3`, `ImageXCenter`, `ImageYCenter`), `stCamera:VignetteModel`, `stCamera:ChromaticGreenGreenModel`. — UNVERIFIED in this session (I did not open an LCP file, because there are none on this machine); reported as background.
- **Location on Windows (checked directly, MEASURED-LOCALLY):**
  - `C:\ProgramData\Adobe\CameraRaw\LensProfiles` — **does not exist** on this machine.
  - `C:\Users\chris\AppData\Roaming\Adobe\CameraRaw\LensProfiles` — **exists but contains 0 `.lcp` files.**

So even the user-scope path is empty here. Adobe also ships built-in profiles inside the application install directory, but that requires Lightroom/ACR to be installed, and redistributing Adobe's profiles with an open-source tool is a **licensing problem**, not just a technical one.

**Verdict: do not build on LCP.** At most, offer an opt-in "point me at your LCP directory" import for users who have Adobe installed.

### 6.4 DNG OpcodeList3 — the right *output* mechanism

The DNG spec defines three opcode lists that a reader applies at different pipeline stages; `OpcodeList3` is applied **after demosaic**, and is where geometric/shading corrections live:
- `WarpRectilinear` — per-channel radial+tangential distortion **and lateral CA**, with an explicit optical centre.
- `FixVignetteRadial` — radial falloff.
- `WarpFisheye`, `FixBadPixelsConstant`, `TrimBounds`, etc.

darktable reads both lists — VERIFIED, `darktable-org/darktable:src/common/exif.cc:948–972, 2940–2941`:
```c
exifData.findKey(Exiv2::ExifKey("Exif.SubImage1.OpcodeList2"));   // line 948
exifData.findKey(Exiv2::ExifKey("Exif.SubImage1.OpcodeList3"));   // line 967
```

**Recommendation:** if the tool writes a DNG, it should **translate Sony's 16-knot radial tables into `WarpRectilinear` + `FixVignetteRadial` opcodes in `OpcodeList3`**, rather than baking the correction into pixels. That keeps the merged output raw-like and lets Lightroom/darktable/RawTherapee apply corrections in their own colour pipeline. This is the cleanest interop story and it reuses the §6.1 parser.

*(Prior local work flagged that DNG output was never validated in Lightroom — `empirical_findings.md` §4k. If we emit opcodes, validating them in at least two readers is mandatory.)*

### 6.5 Field curvature

Field curvature means the sharp surface is a **bowl, not a plane** — so a single "frame *k* is in focus at depth *z*" mapping is wrong off-axis, and the depth map recovered from a stack is systematically distorted toward the corners.

**Does any stacker model it? Not to my knowledge** — Helicon Focus, Zerene Stacker, `focus-stack`, and `enfuse` all treat focus selection as a per-pixel independent choice, which *implicitly and automatically* handles arbitrary field curvature: if the corner is sharp in frame 12 while the centre is sharp in frame 8, per-pixel selection just picks 12 in the corner. **This claim is UNVERIFIED** (I did not audit those codebases in this session), but it follows from how per-pixel focus selection works.

**Should we model it?** **No — and this is the key insight: per-pixel focus selection already absorbs field curvature.** Modelling it explicitly would only matter if we wanted a *metrically correct* depth map (for 3D output or for physically-correct diffraction-aware deconvolution). For producing a sharp merged image, it is redundant. **Recommend: do not model. Rank it last.**

The one place it leaks: if the tool ever reports "your step size was too large" based on a *global* DoF number, field curvature means the effective in-focus band differs centre-vs-corner. That is a second-order refinement to an advisory feature.

---

## 7. The payoff — ranked, with the "not worth it" calls

Ranked by (quality gain) ÷ (implementation cost). "Cost" is rough engineering effort for a Rust implementation.

| Rank | Gear knowledge | Quality gain | Cost | Ratio | How we'd measure that it helped |
|---|---|---|---|---|---|
| **1** | **Photon-transfer noise model** `σ²=aS+b` | **High** — directly fixes the measured 2.3–4.6× noise amplification in flat regions; enables inverse-variance merge + confident "average, don't select" | **Low** — a 2-parameter table keyed on ISO, ~50 LOC + a data file | ★★★★★ | Cross-frame σ in flat patches of the output vs. single-frame σ; target ≥ √N improvement in textureless regions. Already have the baseline numbers. |
| **2** | **Focus-breathing / rail scale prior** (per-frame isotropic scale + solved optical centre) | **High** — measured 42 px corner error; without it the stack edges smear | **Low-Med** — 4-DoF similarity + fixed-point solve; mostly already in any aligner | ★★★★★ | Alignment residual (ECC / MAD of inter-frame difference) as a function of radius. Edge-vs-centre residual ratio should collapse to ~1. |
| **3** | **Capture-parameter validation** (ISO 320 warning, lossy-ARW warning, IBIS-on warning, step-size vs DoF) | **Med-High** — prevents unfixable-in-post errors; ISO 320→400 alone is 1.2 stops of DR | **Very low** — pure metadata checks, ~100 LOC, no math | ★★★★★ | A/B the same scene at ISO 320 vs 400; measure shadow σ. Predicted 1.2 stops. |
| **4** | **DoF / step-size advisor** (§4.3) | **Med** — prevents the #1 user error (under-sampling → focus banding); also bounds frame count | **Low** — the formulas in §4.1, plus `m` estimated from magnification or metadata | ★★★★ | Count depth-banding artefacts (frames where no pixel is selected sharply) vs. predicted step. |
| **5** | **Distortion + lateral CA from in-camera metadata** (§6.1) | **Med** — CA correction genuinely helps focus measurement (colour fringes are false edges); distortion matters because it doesn't commute with scaling | **Med** — must write our own maker-note parser; LibRaw won't help | ★★★ | Focus-measure stability across the frame; CA fringe width at high-contrast edges pre/post. |
| **6** | **Diffraction-aware sharpening** (Airy-matched deconvolution using known `N_eff`) | **Med** — at `N_eff = 20–40` the owner is heavily diffraction-limited, and diffraction PSF is *exactly known* and spatially invariant, which is the ideal deconvolution case | **Med-High** — needs a stable regularised deconv; risk of ringing | ★★★ | MTF50 on a slanted edge pre/post; must show gain without ringing overshoot > 5 %. |
| **7** | **Focus-position metadata** (`FocusPosition2`) **as a stack-type classifier only** | **Low-Med** — the one thing it can do (rail vs focus detection) is genuinely useful and selects the alignment model | **Very low** — read one tag | ★★★ | Does it correctly classify the two local brackets? (Both rail — need a focus-driven bracket to complete the test.) |
| **8** | **Vignetting from in-camera metadata** | **~Zero for this lens** — coefficients are all zero (§6.1); prior local work measured < 0.05 EV | Low | ★ | — |
| — | **PDAF map** | ❌ **NOT WORTH IT** | High (reverse-engineering, unpublished, prior attempt failed) | ✗ | — |
| — | **PDAF as a depth cue** | ❌ **NOT WORTH IT** | Very high | ✗ | — |
| — | **Field curvature model** | ❌ **NOT WORTH IT** — per-pixel selection already absorbs it (§6.5) | Med | ✗ | — |
| — | **`FocusPosition2` as a metric depth axis** | ❌ **NOT WORTH IT** — 22× too coarse (§3.2) | Med | ✗ | — |
| — | **LensFun / Adobe LCP integration** | ❌ **NOT WORTH IT for the flagship lens** — neither covers it (§6.2, §6.3) | Med | ✗ | — |

### The five "not worth it" calls, stated plainly

1. **PDAF, in both forms.** No published mask for ILCE-7CM2 or ILCE-7M4 (verified against RawTherapee's `camconst.json`); a prior local attempt at empirical recovery ended RED; and at `N_eff = 20–40` the disparity baseline is gone anyway. Handle any artefacts with generic cross-frame outlier rejection, which is more general and costs nothing extra.
2. **`FocusPosition2` as a depth axis.** Two distinct values across 33 frames. One LSB is 22× the DoF. ExifTool's own source disclaims the distance formula. Use it as a classifier; never as a measurement.
3. **Field curvature.** Per-pixel focus selection already handles it implicitly and exactly. Explicit modelling adds complexity and buys nothing for image output.
4. **LensFun / Adobe LCP for the flagship lens.** LensFun does not contain the FE 100mm Macro GM (verified by fetching both `mil-sony.xml` and `slr-sony.xml`). No LCPs exist on this machine, and redistributing Adobe's is a licence problem. Sony's in-camera metadata is strictly better *and* requires no database.
5. **Vignetting correction as a headline feature.** For this exact lens+body the in-camera vignetting coefficients are literally all zeros, and prior local measurement put real falloff under 0.05 EV. Plumb the field, ship nothing.

---

## 8. Graceful degradation and the plugin interfaces

The governing principle: **a gear plugin supplies *priors and calibration*, never *capability*.** Every feature must run with a generic default, and the plugin's job is to tighten it. Nothing may become unavailable because a profile is missing.

### 8.1 Degradation matrix

| Feature | With gear profile | Without profile | Strategy |
|---|---|---|---|
| Noise model | Exact `(a,b)` per ISO from calibration table | **Estimate from the data** — the §2.3 patch method works on any raw file, and only needs one frame | **Estimate** |
| Black/white level | From profile + tags | From raw tags (always present in ARW/DNG) | **Metadata** |
| Scale/breathing prior | Seed scale ramp; constrain search | **Estimate from the data** — solve the similarity chain; measurably well-conditioned (§5.1) | **Estimate** |
| Optical centre | From profile if available | **Estimate** — fixed point of the similarity chain (§5.4). *Preferred even when a profile exists*, since rail tilt is session-specific | **Estimate (always)** |
| Distortion / CA | In-camera params → LensFun → profile | **Disable** (identity). Do *not* guess coefficients | **Disable** |
| Vignetting | In-camera params | **Disable**, or estimate a low-order radial from cross-frame flat regions | **Disable** |
| DoF / step advisor | Exact `m`, `p`, sensor pitch | Generic: `p = 1`, `m` from `FocusPosition2` or magnification tag, pitch from raw dimensions + assumed FF/APS-C | **Generic default** |
| Diffraction sharpening | `N_eff` from `N`, `m`, `p` | Use `N` from EXIF with `p=1`; if `m` unknown, **disable** (getting `N_eff` wrong makes it worse than nothing) | **Disable if `m` unknown** |
| Capture validation | Full ruleset | Generic rules only (lossy compression, IBIS) | **Generic default** |
| PDAF | *(not implemented)* | Generic cross-frame outlier rejection | **Always generic** |

Two rules worth stating explicitly:
- **Never guess a geometric correction.** A wrong distortion coefficient is worse than none, because it introduces error that alignment then has to fight. Disable, don't approximate.
- **Prefer estimation over profile for anything session-dependent.** The optical centre is the clearest case: my measurement (§5.4) cannot separate lens axis from rail tilt, so a cached profile value would be actively wrong.

### 8.2 The `CameraModel` interface

```rust
/// Everything a body-specific plugin can contribute. All methods have
/// working defaults derived from raw metadata alone.
pub trait CameraModel {
    fn matches(&self, make: &str, model: &str) -> bool;

    // --- Sensor geometry ---
    fn cfa_pattern(&self, raw: &RawMeta) -> CfaPattern;      // default: from tags
    fn pixel_pitch_um(&self, raw: &RawMeta) -> f32;          // default: sensor dims / raw dims
    fn active_area(&self, raw: &RawMeta) -> Rect;            // DefaultCropOrigin/Size

    // --- Levels ---
    fn black_level(&self, raw: &RawMeta) -> [f32; 4];        // A7C II: [512;4]
    /// Level above which data is untrustworthy. A7C II: 15360, NOT 16383.
    fn usable_white_level(&self, raw: &RawMeta) -> u16;
    /// True if masked photosites are readable. A7C II: false (MEASURED §2.2).
    fn has_optical_black(&self) -> bool { false }

    // --- THE important one ---
    /// sigma^2(S) = a*S + b, S in DN above black.
    /// Return None to force estimation from the image data.
    fn noise_model(&self, iso: f32) -> Option<NoiseModel>;   // { a: f32, b: f32 }

    /// ISO values that are strictly dominated by a higher ISO (dual conversion
    /// gain). A7C II: 200..=320 are dominated by 400.
    fn dominated_isos(&self) -> &[(u32, u32)] { &[] }

    // --- Format validation ---
    fn compression_is_lossy(&self, raw: &RawMeta) -> bool;   // SonyRawFileType == 2
    fn capture_warnings(&self, raw: &RawMeta) -> Vec<Warning>; // IBIS on, ISO 320, lossy, ...

    // --- Optional, low-value ---
    fn pdaf_map(&self, raw: &RawMeta) -> Option<PdafMask> { None }  // A7C II: None
}

pub struct NoiseModel { pub a: f32, pub b: f32 }  // DN/e-, DN^2
impl NoiseModel {
    pub fn variance(&self, signal_dn: f32) -> f32 { self.a * signal_dn + self.b }
    pub fn weight(&self, signal_dn: f32) -> f32 { 1.0 / self.variance(signal_dn) }
    /// Generalized Anscombe VST -> unit variance.
    pub fn stabilize(&self, s: f32) -> f32 {
        (2.0 / self.a) * (self.a * s + 0.375 * self.a * self.a + self.b).max(0.0).sqrt()
    }
}
```

### 8.3 The `LensModel` interface

```rust
pub trait LensModel {
    fn matches(&self, lens_id: u64, lens_model: &str) -> bool;   // Sony LensType3, e.g. 32893

    // --- Static optics (from the vendor spec sheet) ---
    fn focal_length_mm(&self) -> f32;                 // 100.0
    fn max_magnification(&self) -> f32;               // 1.4  (2.8 with SEL20TC)
    fn min_focus_distance_m(&self) -> f32;            // 0.26
    fn pupil_magnification(&self) -> f32 { 1.0 }      // p in N_eff = N(1 + m/p)
    fn is_internal_focus(&self) -> bool { true }
    /// Multiplies focal length, aperture AND magnification.
    fn teleconverter(&self, raw: &RawMeta) -> Option<Teleconverter>;

    // --- Magnification: the axis that actually matters ---
    /// Best-effort magnification. None -> caller must estimate or disable.
    fn magnification(&self, raw: &RawMeta) -> Option<f32>;

    // --- Focus breathing ---
    /// d(log scale)/d(focus step). None => estimate from the image data.
    /// SEL100M28GM: None -- no published measurement (§1.1).
    fn breathing_scale_rate(&self) -> Option<f32> { None }

    // --- Corrections: return None to DISABLE, never to approximate ---
    /// 16-knot radial table from Sony maker notes; units of 1/10.24 percent.
    fn distortion(&self, raw: &RawMeta) -> Option<RadialTable>;
    fn lateral_ca(&self, raw: &RawMeta) -> Option<(RadialTable, RadialTable)>; // R, B
    fn vignetting(&self, raw: &RawMeta) -> Option<RadialTable>;  // SEL100M28GM: all-zero

    /// Optical centre if known. Callers should PREFER estimating this per stack.
    fn optical_centre(&self, raw: &RawMeta) -> Option<(f32, f32)> { None }
}

/// Derived helpers -- pure functions, no plugin needed.
pub fn effective_aperture(n: f32, m: f32, p: f32) -> f32 { n * (1.0 + m / p) }
pub fn dof_um(n_eff: f32, coc_um: f32, m: f32) -> f32 { 2.0 * n_eff * coc_um / (m * m) }
pub fn airy_diameter_um(n_eff: f32) -> f32 { 2.44 * 0.55 * n_eff }
/// Largest nominal aperture keeping the Airy disk within `max_px` pixels.
pub fn diffraction_limited_aperture(m: f32, p: f32, pitch_um: f32, max_px: f32) -> f32 {
    (max_px * pitch_um / (2.44 * 0.55)) / (1.0 + m / p)
}
```

### 8.4 The stack-type classifier (needed by the aligner)

```rust
pub enum StackGeometry {
    /// Viewpoint fixed, magnification varies. Global similarity is EXACT.
    FocusDriven { scale_rate: f32 },
    /// Viewpoint moves. Similarity + depth-dependent parallax residual.
    RailDriven  { scale_rate: f32 },
    Unknown,
}

/// FocusPosition2 varying  -> FocusDriven
/// FocusPosition2 constant -> RailDriven
/// This is the ONLY sound use of FocusPosition2 (§3.2).
pub fn classify(frames: &[RawMeta], fitted_scale_rate: f32) -> StackGeometry;
```

---

## 9. Gaps, uncertainties, and suggested follow-ups

**Verified absences** (I fetched the source and the thing was not in it):
- `FE 100mm f/2.8 Macro GM` in LensFun `mil-sony.xml` and `slr-sony.xml` — absent.
- `ILCE-7CM2` in RawTherapee `camconst.json` — absent entirely; `ILCE-7M4` present but with no `pdaf_pattern`.
- `.lcp` files under both Windows Adobe profile paths — 0 files.
- Focus-breathing figure on Sony's `SEL100M28GM` spec and feature pages — not published (searched decoded page text for `ブリージング`/`breathing`).

**Could not confirm / unverified:**
- **Focus breathing magnitude for SEL100M28GM.** No measured third-party data located. I checked Sony's own pages only; I did **not** exhaustively search third-party measurement sites (e.g. lens-review databases). **Follow-up:** either search those, or — better — just measure it (below).
- **The exact bit layout of Sony's lossy 11+7 scheme.** I verified the *enum* and that the owner's files are lossless type 4, which is what matters operationally, but did not read a decoder.
- **Whether other stackers model field curvature.** Inferred from how per-pixel selection works; not verified by code audit.
- **Adobe LCP internal field names.** Reported from background knowledge; no LCP file was available to open. Flagged UNVERIFIED in §6.3.
- **Pupil magnification `p` for SEL100M28GM.** Not published. All §4 tables assume `p = 1`. For a 17-element floating-focus design this could plausibly be 0.7–1.3, shifting `N_eff` by ±20 %.
- **Sensor physical dimensions.** I assumed 35.9 mm width to derive the 5.12 µm pitch. Not verified against a Sony primary source (their pages were 403 for the body). A ±0.3 % error here is negligible for every conclusion drawn.

**Highest-value follow-up measurements**, in order:

1. **Shoot a focus-driven bracket** (in-camera focus bracketing, camera locked down) on the same subject. This is the single biggest gap: every local stack is rail-driven, so I could measure rail scale drift but **not** breathing, and could not exercise the §8.4 classifier. It would deliver a measured breathing curve *and* validate `FocusPosition2` as a classifier in one capture.
2. **Shoot a flat-field + dark-frame pair at ISO 100, 320, 400, 1600.** Would pin `(a, b)` directly at the DCG breakpoint, verify the ISO-320-is-worse prediction empirically, and give a real read-noise intercept (which §2.3 could not identify from image data alone).
3. **Decode the Sony `DistortionCorrParams` radial table and compare against a shot of a grid target.** Confirms the `/10.24 %` scaling and the knot spacing convention before we build on it.

---

## 10. Appendix — full local metadata dump (key excerpts, MEASURED-LOCALLY)

`exiftool -a -G1 -s C:\dev\macro\test\109MSDCF\DSC00024.ARW` (ExifTool 13.58):

```
[IFD0]    Model                : ILCE-7CM2
[IFD0]    Software             : ILCE-7CM2 v2.00
[SubIFD]  ImageWidth/Height    : 7168 / 5120
[SubIFD]  SonyRawFileType      : Sony Lossless Compressed RAW 2
[SubIFD]  CFAPattern2          : 0 1 1 2            (RGGB)
[SubIFD]  BlackLevel           : 512 512 512 512
[SubIFD]  WhiteLevel           : 16383
[SubIFD]  BitsPerSample        : 14
[SubIFD]  DefaultCropOrigin    : 12 8
[SubIFD]  DefaultCropSize      : 7008 4672
[SubIFD]  TileWidth/Length     : 512 / 512
[SR2SubIFD] WhiteLevel         : 15360 15360 15360   <- usable ceiling
[SR2SubIFD] ColorMatrix        : 1011 -97 111 243 937 -156 197 -8 835
[ExifIFD] ISO                  : 160
[ExifIFD] FNumber              : 11.0
[ExifIFD] ExposureTime         : 1.3
[ExifIFD] FocalLength          : 200.0 mm           (100mm + 2x TC)
[ExifIFD] MaxApertureValue     : 5.6                (2.8 x 2)
[ExifIFD] LensModel            : FE 100mm F2.8 Macro GM OSS + 2X Teleconverter
[Sony]    LensType3            : Sony FE 100mm F2.8 Macro GM OSS + 2X Teleconverter
[Sony]    FocusMode            : Manual
[Sony]    FocusPosition2       : 57
[Sony]    ImageStabilization   : On                 <- capture error for a tripod stack
[Sony]    ElectronicFrontCurtainShutter : On
[Sony]    SonyISO              : 159
[Sony]    StopsAboveBaseISO    : 0.7
[Sony]    LensFirmwareVersion  : Ver.01.001
[Sony]    ShutterCount         : 6295
[Composite] FocusDistance2     : 0.2738 m
[Composite] Megapixels         : 36.7               (7168x5120 raw buffer)
```

### Sources opened (all fetched 2026-08-22)

| Source | URL / path | Used for |
|---|---|---|
| photonstophotos read noise | `https://www.photonstophotos.net/Charts/RN_e.htm` | §2.3 fwc, unityEv, RN curve |
| photonstophotos PDR | `https://www.photonstophotos.net/Charts/PDR.htm` | §2.3 DCG confirmation |
| Sony JP — SEL100M28GM specs | `https://www.sony.jp/ichigan/products/SEL100M28GM/spec.html` | §1.1 |
| Sony JP — SEL100M28GM features | `https://www.sony.jp/ichigan/products/SEL100M28GM/feature_1.html` | §1.1 floating focus, 2.8× |
| Sony JP — SEL100F28GM (STF) | `https://www.sony.jp/ichigan/products/SEL100F28GM/spec.html` | §1 disambiguation |
| LensFun mirrorless DB | `https://raw.githubusercontent.com/lensfun/lensfun/master/data/db/mil-sony.xml` | §6.2 |
| LensFun SLR DB | `https://raw.githubusercontent.com/lensfun/lensfun/master/data/db/slr-sony.xml` | §6.2 |
| RawTherapee camconst | `https://raw.githubusercontent.com/Beep6581/RawTherapee/dev/rtengine/camconst.json` | §2.5 PDAF |
| darktable exif.cc | `https://raw.githubusercontent.com/darktable-org/darktable/master/src/common/exif.cc` | §6.1, §6.4 |
| ExifTool `Sony.pm` (13.58) | `C:\Users\chris\AppData\Local\Programs\ExifTool\exiftool_files\lib\Image\ExifTool\Sony.pm` | §1, §3.1, §6.1 |
| LibRaw 0.22.1 headers | `C:\dev\macro\deps\libraw\libraw\libraw_types.h`, `libraw_version.h` | §2.4, §3.3 |
| Owner's ARW brackets | `C:\dev\macro\test\109MSDCF\` (22 frames), `C:\dev\macro\test\119MSDCF\` (33 frames) | §2, §3.2, §5.1 |
| Prior local findings | `C:\dev\macro\research\empirical_findings.md`, `PROBE10_PDAF_MASK.md`, `PROBE8_FOCUSPOSITION2.md` | context, cross-checked |

> `exiftool.org/TagNames/Sony.html` returned **HTTP 404** (both `web_fetch` and `curl`). I used the locally installed `Sony.pm` instead, which is the authoritative implementation that generates that documentation page — a stronger source than the HTML.
> `sony.com`, `electronics.sony.com`, `sony.co.uk` all returned **HTTP 403** to scripted requests; `sony.jp` served fine.

---

## Follow-up 1

## F1.0 Headline

| # | Question | Verdict | Confidence |
|---|---|---|---|
| 1 | Breathing or rail? | **Focus breathing, via the A7C II's own in-camera Focus Bracket.** Five independent lines of evidence agree. | **High (~85%)** |
| 2 | Is scale-only enough? | **Isotropic scale + translation is enough per adjacent frame (0.06 px corner error) but NOT over a 33-frame baseline (~1.5-2 px).** Use full affine; homography adds nothing. | High |
| 2b | Scale-centre conditioning | **Ill-conditioned by construction: centre = t/(1-s), amplification 1/(1-s) ~ 98x at full baseline, ~1540x per frame step.** y-offset -338 +/- 61 px is real; x-offset consistent with zero. Regularise. | High |
| 3 | Capture advisor | Tables F1.7-F1.13 below. **The 2x TC at high m cannot resolve at Nyquist at any aperture.** | DERIVED |

---

## F1.1 Q1 - Breathing vs rail: SETTLED (high confidence) - focus breathing

### F1.1.1 The A7C II has in-camera focus bracketing - VERIFIED, primary source

Fetched `https://helpguide.sony.net/ilc/2360/v1/en/contents/211h_focus_bracket.html`
(help-guide ID **2360 = ILCE-7CM2**, established by probing IDs 2300-2380 and reading `<title>`;
2320 is ILCE-6700, 2370 is ILCE-7CR, 2380 is ILCE-9M3).

> "Performs continuous shooting automatically while shifting the focus position. This function can be
> used to shoot images for depth-of-field composite images that are in focus at all points (focus
> stacking), or to select the optimum focus position from among multiple images."

| Setting | Value | Source |
|---|---|---|
| Location | Drive Mode -> `Focus Bracket` | VERIFIED |
| `Step Width` | 1-10, **relative** | VERIFIED |
| `Number of Shots` | **2 to 299** | VERIFIED |
| `Focus Bracket Order` | `[0->+]` = current position **toward infinity**; `[0->-->+]` | VERIFIED |
| `Shooting Interval` | set under `Bracket Settings` | VERIFIED |
| `Exposure Smoothing` | set under `Bracket Settings` | VERIFIED |
| Sony's own caveat | "If the camera or lens moves while shooting with the focus bracket, focus stacking may not be successful. Use a tripod." | VERIFIED |

Critical for the tool: **"The [Step Width] value is a relative value, and the focus interval varies
depending on shooting conditions such as the aperture of the lens and the initial focus position."**
(VERIFIED, same page.) Step Width therefore carries **no absolute metric meaning**; a step size in
micrometres can only ever be *estimated from the images*, never read from a setting. This kills any
notion of a lookup table from Step Width to microns.

### F1.1.2 Evidence table

Stack: `C:\dev\macro\test\119MSDCF`, 33 frames DSC00024-DSC00056.
`LensModel = FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, `FocalLengthIn35mmFormat = 200 mm`,
f/5.6, ISO 50 (MEASURED-LOCALLY, ExifTool 13.58).

| # | Observation | Breathing / in-camera bracket predicts | Rail predicts | Verdict |
|---|---|---|---|---|
| 1 | Interval **0.6492 s +- 0.0208 s, CV 3.21%**, no drift; `ShutterCount` 5504->5536 with **no gaps** | Exactly this - `Bracket Settings -> Shooting Interval` is a camera-timed burst | Manual rail: **excluded**. Motorised rail: also possible | **Favours bracket**; excludes manual rail |
| 2 | `FocusPosition2` = 56,56,56,**57**,57,...,57 - it **changed** | Camera refocused - required | MF locked on a rail -> should be **exactly constant** | **Strongly favours breathing** |
| 3 | Magnification decreases **monotonically** (-1.012%) | `Focus Bracket Order [0->+]` shifts toward infinity -> m falls monotonically | Rail retreating also lowers m | Consistent, not decisive alone |
| 4 | Implied focus travel **2.03 mm** vs one `FocusPosition2` LSB = **3.09 mm** -> predicts **0 or 1 ticks; exactly 1 observed** | Quantitatively consistent | Requires an unexplained tick | **Strongly favours breathing** |
| 5 | Exposure jitters 1/6 <-> 1/8 at fixed f/5.6, ISO 50, EC 0 | AE live during an automatic burst; Sony ships `Exposure Smoothing` in `Bracket Settings` precisely for this | A rail controller would normally be used in full M | Favours bracket |
| 6 | Homography perspective terms h20=4.8e-10, h21=-7.5e-8 -> **0.004%** edge effect | Zero | Non-zero for a tilted plane | Favours breathing (**weak** - see caveat) |
| 7 | Regional near/far differential scale: **-0.0232%** (dN=16), **-0.0066%** (dN=32) - *inconsistent with each other*, so noise | Zero | ~0.02-0.04% and should scale with baseline | Null at the ~0.02% floor - favours breathing |
| 8 | Residual anisotropy 3.6e-4, major axis **33.4 deg**, subject depth-gradient axis **133.4 +- 0.3 deg** -> max-shrink axis within **10 deg** of the depth gradient | Not predicted | Predicted (tilted plane + axial translation) | **The one piece of contrary evidence** |
| 9 | `ReleaseMode2 = 23` -> ExifTool prints "Single-frame - Exposure Bracketing" | - | - | **Uninformative**: `Sony.pm` contains **zero** "Focus Bracket" strings, so ExifTool cannot name this mode on this body |

### F1.1.3 The magnitude sanity-check the orchestrator asked for - DERIVED

Thin-lens Newtonian: `m = f/(z-f)`, so `dm/dz = -m^2/f`, giving

```
dm/m = -(m/f) * dz_obj          (identical first-order law for BOTH breathing and rail)
```

This is why **magnitude alone can never discriminate the two** - the same equation governs a
focus-driven and a translation-driven magnification change.

With MEASURED `dm/m = -0.010126` and `f_eff = 200 mm` (100 mm prime x 2.0 TC):

| m_total | implied focus/rail travel `dz = 0.010126 * 200/m` | in `FocusPosition2` LSB (3.09 mm) | ticks expected | ticks observed |
|---|---|---|---|---|
| 0.5 | 4.05 mm | 1.31 | 1-2 | 1 |
| **1.0** | **2.03 mm** | **0.66** | **0-1** | **1** |
| 2.0 | 1.01 mm | 0.33 | 0-1 | 1 |
| 2.8 | 0.72 mm | 0.23 | 0-1 | 1 |

**So -1.012% is entirely consistent with focus breathing** for any plausible macro magnification.
It is *not* too large or too small. Per-frame step = 2.03/32 = **63 um** at m=1, which is
`DoF(2 px, N_eff=11.2)/3.6 = 229 um / 3.6` - a conservatively oversampled stack, exactly what a
sensible focus-bracket Step Width produces.

Independent corroboration: the depth-proxy plane fit (F1.4) spans the full focus sweep, so the
subject depth is ~2.0 mm - matching the 2.03 mm of focus travel derived from the scale drift alone.
Two independent routes to the same number.

### F1.1.4 Confidence, and the one loose end

**~85% focus breathing.** The remaining 15% is item 8: a real, baseline-growing anisotropy whose
axis is locked to the *subject's* depth gradient, which pure breathing does not predict. Competing
benign explanation: on a tilted plane the in-focus band **migrates across the frame** as focus
sweeps, and ECC weights whatever is sharp, so the fit's effective centroid slides along the tilt
direction. I cannot separate that from parallax with this dataset. Note also that the homography
result (item 6) is weak evidence: ECC returned an ECC score *identical* to the affine fit
(1-ECC = 1.45e-3 for both) with perspective terms essentially unmoved from their identity
initialisation, i.e. the optimiser may simply never have explored them.

**What would settle it definitively** (one afternoon):
1. Shoot the same subject twice - once with in-camera `Focus Bracket`, once on a rail with MF locked - and compare (a) `FocusPosition2` constancy, (b) the anisotropy magnitude and axis.
2. Or simply ask the owner which one he used. This is a one-line answer that replaces a day of inference.
3. A flat, frontal, high-texture target (banknote, ruler) removes the depth-gradient confound entirely: with zero depth tilt, breathing gives pure isotropic scale and a rail gives *nothing but* defocus.

### F1.1.5 Why this matters architecturally

If it is breathing, the scale drift is a **lens+focus-distance property** and is therefore
**profilable**: `scale_per_focus_step` becomes a prior the registration solver can be regularised
toward, rather than a free parameter re-solved per stack. If it were a rail, no lens profile could
ever help and the solver would need a full depth-aware homography per frame. **The evidence says
build the prior.**

---

## F1.2 Q2a - Method note: why the first per-block attempt was discarded

Both estimators were validated against synthetic ground truth (frame 24 warped by a known
s = 0.99484 about a known centre):

| Estimator | Recovered scale | Error |
|---|---|---|
| Block phase-correlation (12x8, Hanning) | 0.994834 | **-6e-6** |
| Global ECC affine (/4 downsample) | 0.994857 | **+1.7e-5** |

Both unbiased. Blur was then added to one side (sigma = 1.5 and 3.0 px, either direction): recovery
stayed within **0.4%** of truth, so **defocus difference does not bias phase correlation**.

Yet on real data the two diverge catastrophically, and the divergence tracks the phase-correlation
response:

| Baseline dN | Block-fit scale | ECC scale | ratio | mean block response |
|---|---|---|---|---|
| 2 | -0.0144% | -0.0649% | 4.5x | 0.676 |
| 4 | -0.0366% | -0.1299% | 3.5x | 0.609 |
| 8 | -0.0750% | -0.2548% | 3.4x | 0.456 |
| 16 | -0.0897% | -0.5122% | 5.7x | 0.274 |
| 32 | -0.0645% | -1.0126% | 15.7x | 0.131 |

ECC is self-consistent: composing the 16 adjacent step-2 fits gives **-1.0218%** versus a direct
24->56 fit of **-1.0126%** - agreement to **0.9%**, with a per-step scale flat at
-0.0645% +- 0.0016% across the whole sequence (no drift).

**Conclusion: per-block correlation on a focus-sweep stack is not a valid instrument.** Each block
is tracking the migrating in-focus band across a tilted subject, not geometry. All Q2 answers below
therefore use **masked global ECC**, and scale is taken as `sqrt(det(A))`, which is **independent of
the assumed centre**.

---

## F1.3 Q2b - Model selection: what residual remains

Frames 24->56, green sublattice at /2 (1757x1172), ECC to 1e-9:

| Model | DoF | ECC | 1 - ECC (unexplained) |
|---|---|---|---|
| TRANSLATION | 2 | 0.995683 | 4.32e-3 |
| EUCLIDEAN (rot+trans) | 3 | 0.995707 | 4.29e-3 |
| **AFFINE** | 6 | **0.998546** | **1.45e-3** |
| HOMOGRAPHY | 8 | 0.998546 | 1.45e-3 |

**Affine cuts unexplained variance 3x versus Euclidean. Homography adds literally nothing.**

Affine decomposition vs baseline (corner columns are full-res px at half-diagonal 2112 green-px):

| dN | scale % | anisotropy-1 | rotation deg | 1-s | anisotropy @corner | rotation @corner |
|---|---|---|---|---|---|---|
| 4 | -0.1286 | 5.81e-5 | +0.0008 | 0.00129 | 0.25 px | 0.06 px |
| 8 | -0.2547 | 1.08e-4 | +0.0012 | 0.00255 | 0.46 px | 0.09 px |
| 16 | -0.5114 | 1.93e-4 | +0.0041 | 0.00511 | 0.82 px | 0.31 px |
| 24 | -0.7667 | 3.10e-4 | +0.0053 | 0.00767 | 1.31 px | 0.39 px |
| **32** | **-1.0176** | **3.60e-4** | **+0.0062** | **0.01018** | **1.52 px** | **0.46 px** |

**Answer to "is scale-only sufficient":**

* **Per adjacent frame pair: yes.** Residual beyond isotropic scale is ~0.06 px at the corner - far below the merge tolerance.
* **Across a 33-frame stack: no.** ~1.5 px of anisotropy plus ~0.5 px of rotation accumulate. At 33 MP that is visible as edge softening in the merged corners.
* **Design consequence: chain adjacent-frame similarity transforms rather than fitting every frame to a single reference**, or use full affine to the reference. Do **not** use homography - it buys nothing and adds 2 badly-conditioned parameters.
* The rotation (+0.0062 deg, monotone with baseline) is consistent with the **`ImageStabilization: On`** capture error already flagged in the main report: IBIS injects per-frame sub-pixel rotation/translation.

---

## F1.4 Q2c - Residual structure: is it depth-dependent?

**Depth proxy** (MEASURED-LOCALLY): per-block Laplacian energy across frames 24-56 step 2, 16x24
blocks of 146x146 green-px (square), best-focus frame index refined by parabolic interpolation.

Plane fit `z = 5.429e-3*x - 5.743e-3*y + 36.5` (z in frame index, x,y in green-px):

| Quantity | Value |
|---|---|
| **R^2** | **0.989 - the subject is a tilted plane** |
| Residual RMS | 0.69 frame-index units |
| z range | 25.4 - 56.0 (the full sweep) |
| **Depth-gradient azimuth** | **133.4 deg +- 0.32 deg** (bootstrap, n=1000) |

**Test 1 - masked regional ECC (centre-free, scale from `sqrt(det)`).** Blocks split at the 30th/70th
percentile of depth: 134 near-blocks, 121 far-blocks.

| Baseline | ALL | NEAR-depth | FAR-depth | **near-far differential** |
|---|---|---|---|---|
| 24->40 | -0.5114% | -0.5106% | -0.4876% | **-0.0232%** |
| 24->56 | -1.0176% | -1.0081% | -1.0015% | **-0.0066%** |

A genuine parallax differential must **grow with baseline**. It does the opposite (dN=32 is 3.5x
*smaller* than dN=16), so this is noise. **Detection floor ~0.02%.** The rail prediction from the
main report was ~0.02-0.04%, so this is a **null result sitting right at the prediction** - it
disfavours the rail but does not exclude it.

**Test 2 - anisotropy axis vs depth-gradient axis.** This is the one signal that survives:

| Baseline | singular values | anisotropy-1 | major axis | max-shrink axis | offset from depth gradient (133.4 deg) |
|---|---|---|---|---|---|
| 24->40 | 0.994982 / 0.994790 | 1.93e-4 | 39.7 deg | 129.7 deg | **3.7 deg** |
| 24->48 | 0.992487 / 0.992179 | 3.10e-4 | 36.3 deg | 126.3 deg | 7.1 deg |
| 24->56 | 0.990003 / 0.989646 | 3.60e-4 | 33.4 deg | 123.4 deg | 10.0 deg |

The direction of **maximum shrinkage** lies within **4-10 deg of the subject's depth-gradient
direction** at every baseline. A random axis would fall that close only ~11% of the time.

**Interpretation.** The residual is **subject-dependent**, not a fixed lens property. Whether it is
rail parallax or focus-band migration on a tilted plane cannot be separated here. Either way the
architectural conclusion is the same and is important:

> **The residual beyond isotropic scale must be estimated per-stack from the images. It can never be
> baked into a gear profile.** A lens profile can supply the *isotropic* scale prior (~97.6% of the
> total signal at dN=32); the remaining ~2.4% is subject geometry and belongs to the solver.

---

## F1.5 Q2d - Conditioning of the scale centre

The centre is recovered as `c = (I - A)^-1 * t`. Since `A ~ s*I` with `s -> 1`, this is a
**division by (1-s)** - an intrinsic amplification of every error in the translation estimate:

| dN | 1-s | amplification 1/(1-s) | centre error from a **0.5 px** error in t |
|---|---|---|---|
| 2 | 0.000649 | **1541x** | **770 px** |
| 8 | 0.002548 | 392x | 196 px |
| 32 | 0.010126 | **98x** | **49 px** |

Empirical centre offsets from image centre (full-res px), one per baseline:

| dN | offset x | offset y |
|---|---|---|
| 4 | -1004 | -235 |
| 8 | -72 | -250 |
| 16 | -360 | -387 |
| 24 | -150 | -344 |
| 32 | -120 | -369 |

Excluding dN=4 (amplification >750x, uninformative):

| Axis | Estimate | 1 sigma | Significance |
|---|---|---|---|
| x | **-176 px** | +-127 | **1.4 sigma - consistent with zero** |
| y | **-338 px** | +-61 | **5.5 sigma - real** |

**Answers:**
* The earlier "~400 px off centre" was **half right**. The **y** offset is real and significant (-338 +- 61 px, 7.2% of frame height). The **x** offset is **not** distinguishable from zero.
* A per-stack centre solve is **well-posed only at the full baseline** (dN >= 16), and even then only in one axis. It is **hopeless per frame pair** (1541x amplification).
* **A y-only offset with x ~ 0 is not what a decentred optical axis looks like** - that would be an arbitrary 2-D offset. It looks more like a **systematic vertical translation** across the stack (gravity sag on the tripod/rail, or IBIS drift) being absorbed into the centre estimate. Treat it as such.

**Recommendation - regularise, do not free-solve.**

```
minimise  sum_frames || d_i - s*(x_i - c) - t ||^2  +  lambda * ||c - c_image||^2
lambda chosen so the prior has the weight of ~0.3 px of translation uncertainty
```
Solve **one** centre for the whole stack (never per frame), using the **full baseline**, and shrink
hard toward the image centre. Given the above, defaulting `c = c_image` outright costs at most
`338 px * 0.01018 = 3.4 px` of scale-induced displacement error at the extreme frame - which is
**not** negligible, so the y term is worth keeping, but only as a regularised stack-level parameter.

---

## F1.6 Q3 - Capture advisor: formulas

All **DERIVED**. Constants used:

| Symbol | Value | Provenance |
|---|---|---|
| pixel pitch | **5.12 um** | 35.9 mm / 7008 px (`DefaultCropSize`). Sensor width UNVERIFIED, +-0.3% |
| f_Nyquist | **97.7 cy/mm** | `1/(2*pitch)` |
| lambda | 550 nm | green-weighted visual mean, conventional |
| CoC `c1` | **5.12 um** (1 px) | pixel-level |
| CoC `c2` | **10.24 um** (2 px) | pixel-level, after demosaic MTF |
| legacy CoC | 30 um | **REJECTED** - 5.9 px on this sensor |
| f (prime) | 100 mm | SEL100M28GM, VERIFIED sony.jp |
| f (with SEL20TC) | 200 mm | `FocalLengthIn35mmFormat = 200 mm`, MEASURED-LOCALLY |
| **p** (pupil magnification) | **1.0 assumed** | **UNPUBLISHED for SEL100M28GM.** Searched Sony spec/feature pages; could not confirm. Sensitivity in F1.7b |

```
N_eff   = N * (1 + m/p)                 effective (bellows-corrected) f-number
DoF     = 2 * N_eff * c / m^2           total object-space depth of field
d_Airy  = 2.44 * lambda * N_eff         Airy disk diameter
f_c     = 1 / (lambda * N_eff)          diffraction cutoff, cy/mm
MTF_d(f)= (2/pi) * (acos(s) - s*sqrt(1-s^2)),  s = f/f_c     diffraction MTF
step    = DoF(c2) / K,   K = 1.5        recommended focus step
n       = ceil(depth/step) + 1          frame count
```

**Note on the teleconverter:** the EXIF `FNumber` with the SEL20TC fitted is **already TC-corrected**
(`MaxApertureValue = 5.6` = 2.8 x 2). Do **not** double it again. In the TC tables below, `N` is the
marked/EXIF value and `m` is the *total* magnification.

---

## F1.7 T1 - Effective aperture `N_eff = N(1+m/p)`, p = 1

**Bare SEL100M28GM** (max m = 1.4, VERIFIED sony.jp):

| m | f/2.8 | f/4 | f/5.6 | f/8 | f/11 | f/16 | f/22 |
|---|---|---|---|---|---|---|---|
| 0.25 | 3.5 | 5.0 | 7.0 | 10.0 | 13.8 | 20.0 | 27.5 |
| 0.50 | 4.2 | 6.0 | 8.4 | 12.0 | 16.5 | 24.0 | 33.0 |
| 0.75 | 4.9 | 7.0 | 9.8 | 14.0 | 19.2 | 28.0 | 38.5 |
| 1.00 | 5.6 | 8.0 | 11.2 | 16.0 | 22.0 | 32.0 | 44.0 |
| 1.40 | 6.7 | 9.6 | 13.4 | 19.2 | 26.4 | 38.4 | 52.8 |

**With SEL20TC** (max m = 2.8, VERIFIED sony.jp; `N` is the marked/EXIF value):

| m | f/5.6 | f/8 | f/11 | f/16 | f/22 | f/32 | f/45 |
|---|---|---|---|---|---|---|---|
| 0.50 | 8.4 | 12.0 | 16.5 | 24.0 | 33.0 | 48.0 | 67.5 |
| 1.00 | 11.2 | 16.0 | 22.0 | 32.0 | 44.0 | 64.0 | 90.0 |
| 1.50 | 14.0 | 20.0 | 27.5 | 40.0 | 55.0 | 80.0 | 112.5 |
| 2.00 | 16.8 | 24.0 | 33.0 | 48.0 | 66.0 | 96.0 | 135.0 |
| 2.80 | 21.3 | 30.4 | 41.8 | 60.8 | 83.6 | 121.6 | 171.0 |

### F1.7b Sensitivity to the unknown pupil magnification `p` (bare, f/5.6)

| m | p=0.7 | p=1.0 | p=1.3 | spread |
|---|---|---|---|---|
| 0.25 | 7.6 | 7.0 | 6.7 | +-13% |
| 0.50 | 9.6 | 8.4 | 7.8 | +-22% |
| 0.75 | 11.6 | 9.8 | 8.8 | +-28% |
| 1.00 | 13.6 | 11.2 | 9.9 | **+-33%** |
| 1.40 | 16.8 | 13.4 | 11.6 | **+-38%** |

**This is the dominant uncertainty in the whole advisor.** At m=1.4 the DoF and diffraction numbers
are only good to ~+-38% until `p` is known. Since `DoF` and `d_Airy` are both **linear** in `N_eff`,
they inherit this error directly.

**How to obtain `p` empirically** (worth doing once, then shipping in the lens profile): photograph a
flat target at two known magnifications and measure the *actual* exposure loss versus the
`(1+m/p)^2` prediction; solve for `p`. Or measure entrance/exit pupil diameters directly by
photographing the aperture from the front and the rear. Either is a one-hour bench task and would
remove a +-38% error from every number below.

---

## F1.8 T2 - Depth of field, at pixel-level CoC

**Bare lens, c = 2 px = 10.24 um. DoF in mm (total).**

| m | f/2.8 | f/4 | f/5.6 | f/8 | f/11 | f/16 | f/22 |
|---|---|---|---|---|---|---|---|
| 0.25 | 1.1469 | 1.6384 | 2.2938 | 3.2768 | 4.5056 | 6.5536 | 9.0112 |
| 0.50 | 0.3441 | 0.4915 | 0.6881 | 0.9830 | 1.3517 | 1.9661 | 2.7034 |
| 0.75 | 0.1784 | 0.2549 | 0.3568 | 0.5097 | 0.7009 | 1.0194 | 1.4017 |
| 1.00 | 0.1147 | 0.1638 | 0.2294 | 0.3277 | 0.4506 | 0.6554 | 0.9011 |
| 1.40 | 0.0702 | 0.1003 | 0.1404 | 0.2006 | 0.2759 | 0.4012 | 0.5517 |

**Bare lens, c = 1 px = 5.12 um** (exactly half the above):

| m | f/2.8 | f/4 | f/5.6 | f/8 | f/11 | f/16 | f/22 |
|---|---|---|---|---|---|---|---|
| 0.25 | 0.5734 | 0.8192 | 1.1469 | 1.6384 | 2.2528 | 3.2768 | 4.5056 |
| 0.50 | 0.1720 | 0.2458 | 0.3441 | 0.4915 | 0.6758 | 0.9830 | 1.3517 |
| 0.75 | 0.0892 | 0.1274 | 0.1784 | 0.2549 | 0.3504 | 0.5097 | 0.7009 |
| 1.00 | 0.0573 | 0.0819 | 0.1147 | 0.1638 | 0.2253 | 0.3277 | 0.4506 |
| 1.40 | 0.0351 | 0.0502 | 0.0702 | 0.1003 | 0.1379 | 0.2006 | 0.2759 |

**With SEL20TC, c = 2 px. DoF in mm.**

| m | f/5.6 | f/8 | f/11 | f/16 | f/22 | f/32 | f/45 |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.6881 | 0.9830 | 1.3517 | 1.9661 | 2.7034 | 3.9322 | 5.5296 |
| 1.00 | 0.2294 | 0.3277 | 0.4506 | 0.6554 | 0.9011 | 1.3107 | 1.8432 |
| 1.50 | 0.1274 | 0.1820 | 0.2503 | 0.3641 | 0.5006 | 0.7282 | 1.0240 |
| 2.00 | 0.0860 | 0.1229 | 0.1690 | 0.2458 | 0.3379 | 0.4915 | 0.6912 |
| 2.80 | 0.0556 | 0.0794 | 0.1092 | 0.1588 | 0.2184 | 0.3176 | 0.4467 |

For reference, the legacy 30 um CoC would inflate every one of these by **5.86x** - e.g. at m=1,
f/5.6 it claims 1.34 mm of DoF where the sensor actually delivers **0.23 mm**. That is the entire
reason a naive DoF calculator will under-sample a 33 MP macro stack by ~6x.

---

## F1.9 T3 - Diffraction

| N_eff | 2 | 4 | 6 | 8 | 11 | 16 | 22 | 32 | 45 |
|---|---|---|---|---|---|---|---|---|---|
| d_Airy (um) | 2.68 | 5.37 | 8.05 | 10.74 | 14.76 | 21.47 | 29.52 | 42.94 | 60.39 |
| d_Airy (px) | 0.52 | 1.05 | 1.57 | 2.10 | 2.88 | 4.19 | 5.77 | 8.39 | 11.79 |

| Threshold | `N_eff` | Derivation |
|---|---|---|
| Airy = **1 px** (5.12 um) | **3.82** | `5.12/(2.44*0.55)` |
| Airy = **2 px** (10.24 um) | **7.63** | `10.24/(2.44*0.55)` |
| `f_c` falls to Nyquist (**all** pixel-level detail gone) | **18.6** | `1/(lambda*f_Nyq)` |

**Marked aperture at which each threshold is crossed** (bare lens, p=1):

| m | N at Airy=1 px | N at Airy=2 px |
|---|---|---|
| 0.25 | f/3.1 | f/6.1 |
| 0.50 | f/2.6 | f/5.1 |
| 0.75 | f/2.2 | f/4.4 |
| 1.00 | **f/1.9 (unreachable)** | f/3.8 |
| 1.40 | **f/1.6 (unreachable)** | f/3.2 |
| 2.00 (TC) | **f/1.3 (unreachable)** | **f/2.5 (unreachable)** |
| 2.80 (TC) | **f/1.0 (unreachable)** | **f/2.0 (unreachable)** |

**The macro trap, stated numerically:** at m >= 1 the lens **cannot be opened wide enough** to keep
the Airy disk inside one pixel. At m=1.4 even wide open (f/2.8) `N_eff = 6.7`, giving a 1.75 px Airy
disk. **With the TC at m=2.8, wide open is `N_eff = 21.3` - past the 18.6 Nyquist-extinction point.**

---

## F1.10 T4 - Diffraction MTF at Nyquist: what is actually resolvable

`MTF_d(97.7 cy/mm)` - the contrast surviving at the pixel-level detail scale. **0.000 means
pixel-level detail is gone entirely and the file should be downsampled.**

**Bare lens:**

| m | f/2.8 | f/4 | f/5.6 | f/8 | f/11 | f/16 | f/22 |
|---|---|---|---|---|---|---|---|
| 0.25 | 0.762 | 0.662 | 0.533 | 0.351 | 0.154 | 0.000 | 0.000 |
| 0.50 | 0.715 | 0.597 | 0.446 | 0.240 | 0.045 | 0.000 | 0.000 |
| 0.75 | 0.669 | 0.533 | 0.362 | 0.143 | 0.000 | 0.000 | 0.000 |
| 1.00 | 0.623 | 0.470 | 0.283 | 0.062 | 0.000 | 0.000 | 0.000 |
| 1.40 | 0.551 | 0.374 | 0.169 | 0.000 | 0.000 | 0.000 | 0.000 |

**With SEL20TC:**

| m | f/5.6 | f/8 | f/11 | f/16 |
|---|---|---|---|---|
| 1.00 | 0.283 | 0.062 | 0.000 | 0.000 |
| 2.00 | 0.036 | 0.000 | 0.000 | 0.000 |
| **2.80** | **0.000** | **0.000** | **0.000** | **0.000** |

> **Hard conclusion: the SEL20TC at its maximum 2.8x magnification cannot deliver any Nyquist-level
> detail at any aperture.** The teleconverter buys subject magnification by spending resolution.
> The tool should say so, and should offer to output at reduced resolution rather than pretending
> to 33 MP. This is a genuine, quantitative, gear-specific piece of advice that no generic stacker gives.

---

## F1.11 T5 - Focus step and frame count

`step = DoF(c=2px)/K` with **K = 1.5**, i.e. **33% overlap**.

**Why 33% and not 0%:**
1. **Field curvature** - the in-focus surface is not a plane, so a nominal step under-covers the field edges.
2. **Step quantisation** - `Focus Bracket Step Width` is relative and non-linear (VERIFIED F1.1.1); actual increments vary with aperture and focus distance, so the realised step is never exactly the nominal one.
3. **Merge quality** - >= 2 sharp candidates per depth lets the merger **average** instead of **select**. Given the main report's finding that naive selection amplifies noise 2.3-4.6x, this is the single cheapest noise win available: `sqrt(2)` SNR in the overlap zones.

K=1.5 is a defensible default; K=2 for high-value stacks, K=1.2 when frame count is the binding constraint.

**Bare lens:**

| m | N | DoF (mm) | step (um) | n @5 mm | n @10 mm | n @20 mm |
|---|---|---|---|---|---|---|
| 0.25 | f/2.8 | 1.1469 | 764.6 | 8 | 15 | 28 |
| 0.25 | f/4 | 1.6384 | 1092.3 | 6 | 11 | 20 |
| 0.25 | f/5.6 | 2.2938 | 1529.2 | 5 | 8 | 15 |
| 0.25 | f/8 | 3.2768 | 2184.5 | 4 | 6 | 11 |
| 0.50 | f/2.8 | 0.3441 | 229.4 | 23 | 45 | 89 |
| 0.50 | f/4 | 0.4915 | 327.7 | 17 | 32 | 63 |
| 0.50 | f/5.6 | 0.6881 | 458.8 | 12 | 23 | 45 |
| 0.50 | f/8 | 0.9830 | 655.4 | 9 | 17 | 32 |
| 0.75 | f/2.8 | 0.1784 | 118.9 | 44 | 86 | 170 |
| 0.75 | f/4 | 0.2549 | 169.9 | 31 | 60 | 119 |
| 0.75 | f/5.6 | 0.3568 | 237.9 | 23 | 44 | 86 |
| 0.75 | f/8 | 0.5097 | 339.8 | 16 | 31 | 60 |
| 1.00 | f/2.8 | 0.1147 | 76.5 | 67 | 132 | 263 |
| 1.00 | f/4 | 0.1638 | 109.2 | 47 | 93 | 185 |
| 1.00 | f/5.6 | 0.2294 | 152.9 | 34 | 67 | 132 |
| 1.00 | f/8 | 0.3277 | 218.5 | 24 | 47 | 93 |
| 1.40 | f/2.8 | 0.0702 | 46.8 | 108 | 215 | 429 |
| 1.40 | f/4 | 0.1003 | 66.9 | 76 | 151 | 301 |
| 1.40 | f/5.6 | 0.1404 | 93.6 | 55 | 108 | 215 |
| 1.40 | f/8 | 0.2006 | 133.7 | 39 | 76 | 151 |

**Reality check against the owner's own stack:** 33 frames, m ~ 1, N_eff = 11.2, measured step
63 um. Table says DoF(2px) = 0.2294 mm -> recommended step 153 um. His stack is **2.4x
oversampled**, covering 2.03 mm of depth. Comfortably safe, and 14 frames would have sufficed at
K=1.5. **The advisor would have saved him more than half the frames.**

---

## F1.12 T6 - The sweet spot

Two different questions, two different answers - and the distinction matters:

**Objective A - single frame** (classic DoF/diffraction trade): maximise `Q = DoF * MTF_d(f_Nyq)^2`.

| m | optimum N | N_eff | MTF@Nyq | DoF (mm) |
|---|---|---|---|---|
| 0.25 | **f/4** | 5.0 | 0.662 | 1.638 |
| 0.50 | **f/2.8** | 4.2 | 0.715 | 0.344 |
| 0.75 | **f/2.8** | 4.9 | 0.669 | 0.178 |
| 1.00 | **f/2.8** | 5.6 | 0.623 | 0.115 |
| 1.40 | **f/2.8** | 6.7 | 0.551 | 0.070 |

**Objective B - stacking** (what this tool is for). In a stack, **depth is bought with frames, not
with aperture.** Per-frame sharpness is therefore monotonically improving as you open up, and the
only counter-pressure is frame count. The optimum is simply the **widest aperture whose frame count
fits the budget**:

| m | subject depth | recommended N | frames | N_eff | MTF@Nyq |
|---|---|---|---|---|---|
| 0.25 | 5 mm | **f/2.8** | 8 | 3.5 | 0.762 |
| 0.25 | 10 mm | **f/2.8** | 15 | 3.5 | 0.762 |
| 0.25 | 20 mm | **f/2.8** | 28 | 3.5 | 0.762 |
| 0.50 | 5 mm | **f/2.8** | 23 | 4.2 | 0.715 |
| 0.50 | 10 mm | **f/2.8** | 45 | 4.2 | 0.715 |
| 0.50 | 20 mm | f/5.6 | 45 | 8.4 | 0.446 |
| 0.75 | 5 mm | **f/2.8** | 44 | 4.9 | 0.669 |
| 0.75 | 10 mm | f/4 | 60 | 7.0 | 0.533 |
| 0.75 | 20 mm | f/8 | 60 | 14.0 | 0.143 |
| 1.00 | 5 mm | f/4 | 47 | 8.0 | 0.470 |
| 1.00 | 10 mm | f/8 | 47 | 16.0 | 0.062 |
| 1.00 | 20 mm | f/16 | 47 | 32.0 | **0.000** |
| 1.40 | 5 mm | f/5.6 | 55 | 13.4 | 0.169 |
| 1.40 | 10 mm | f/11 | 56 | 26.4 | **0.000** |
| 1.40 | 20 mm | f/22 | 56 | 52.8 | **0.000** |

(60-frame budget. Caveat: at f/2.8 residual spherical/astigmatic aberration will be worse than the
diffraction-only model predicts, so f/4 is a safer real-world floor until the lens is bench-tested.
The model above is **diffraction-only** - it does not know about the lens's aberrations.)

**The rows marked 0.000 are the important output.** They tell the user their requested combination
is *physically impossible* at full resolution: 20 mm of depth at m=1 within 60 frames means
accepting f/16, which destroys pixel-level detail. The honest advice is: **shoot at lower
magnification and crop, or accept 100+ frames.** A generic stacker will silently let the user do the
wrong thing.

---

## F1.13 What Follow-up 1 changes in the plugin interface

| Change | Reason |
|---|---|
| `LensModel::breathing_scale_prior(focus_step) -> Option<f32>` is **justified** and should be built | F1.1: the drift is breathing, hence a lens property, hence profilable |
| Registration model = **affine**, never homography; **chain adjacent pairs** | F1.3: homography adds nothing; anisotropy accumulates over long baselines |
| `StackGeometry::scale_centre` must be a **single stack-level, regularised** parameter, not per-frame, not free | F1.5: 98x-1541x error amplification; only the y component is significant |
| Residual beyond isotropic scale is **subject-dependent** -> solver-owned, never profile-owned | F1.4: anisotropy axis tracks the subject's depth gradient, not the lens |
| `LensModel::pupil_magnification() -> Option<f32>` needed, default 1.0 with a **+-38% advisory** | F1.7b: dominant uncertainty in the whole advisor |
| Advisor must report `MTF_d(f_Nyq)` and **refuse to promise 33 MP** when it is ~0 | F1.10: SEL20TC at 2.8x cannot resolve at Nyquist at any aperture |
| **Never** map `Focus Bracket Step Width` to microns | F1.1.1: VERIFIED relative and condition-dependent; must be estimated from images |
| Warn on `ImageStabilization: On` for tripod stacks | F1.3: +0.0062 deg rotation and part of the translation is IBIS |

