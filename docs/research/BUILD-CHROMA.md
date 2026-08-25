# BUILD-CHROMA — longitudinal chromatic aberration: measurement, and what it does and does not explain

**Status:** MEASURED (axial offset), MEASURED (defect attribution, both negative)
**Scope:** measurement only. No Rust file was read-modified-written by this agent.
**Instrument:** `experiments/BUILD-CHROMA/src/`, outputs in `C:\dev\strehl-out\BUILD-CHROMA\`.

---

## 0. The one-paragraph answer

The rig has **real, non-trivial longitudinal chromatic aberration**. Red comes to
best focus **0.66–0.90 frames** ahead of green and blue **0.48–0.75 frames** ahead
of green, consistently, on all four stacks measured, against a same-sensor null of
**+0.0005 to +0.0113 frames**. It is unambiguously *longitudinal*, not lateral: the
offset is **−0.85 frames at the optical centre** (95% CI [−0.93, −0.79]), and lateral
CA must be exactly zero on axis. Electing on green therefore costs red **4.2–7.5%**
of its gradient energy and blue **3.5–7.1%**.

**But it does not explain either of the two defects it was recruited to explain.**
The rainbow speckle is not produced by it — adding a second full dose of the measured
offset to the render changes the hair-chroma statistic by less than 2%, while a 10×
dose changes it by a factor of five, so the statistic is responsive and the dose is
simply too small. And the rim is not magenta: it is **pink**, and pink is the one
colour that rules axial CA out, because axial CA on this stack predicts a blue
**excess** of +25% at that rim and the measurement finds a blue **deficit** of −15%.

The capability is real. The bug hunt should go elsewhere.

---

## 1. Prior art — this is a replication, not a discovery

I grepped `SYNTHESIS.md` before measuring, as instructed, and the hypothesis in the
brief is **already established fact in this project**. That changes what this report
is for, so it is stated first rather than buried.

| fact | milestone | what it already established |
|---|---|---|
| **1413** | M107 | Axial CA is real and baked in. Election is computed from `green_luma` alone and the one winning index is reused across all four CFA accumulators. `k_R − k_G` = **−0.67 to −1.07**, `k_B − k_G` = **−0.36 to −0.75**, on 5/5 stacks, null ≤ 0.008. Red forfeits 8.96–14.74% gradient energy. |
| **1414** | M107 | Lateral CA is a one-parameter radial magnification error: **ε_R = −704.5 ppm**, **ε_B = +68.4 ppm** — red ≈10× blue — worth ~3 output px at the corner. Ships **OFF by default**. |
| **1416** | M107 | R and B both sit **before** green (same side, not straddling) — the secondary-spectrum signature of a colour-corrected lens. Any chroma model must not assume symmetric straddling. |
| **1417** | M107 | Per-channel election costs ~2.8× CPU / 4–4.5× wall clock and needs a per-channel noise model first. ORCH's **ARGUED** cheaper alternative: keep the single green election and apply a per-channel focus-index **OFFSET**. |
| **1783** | M113/M114 | The shipped lateral gain does not transfer between scenes (1.0557 vs 1.2496). Default-off is correct. |

So the brief's hypothesis — "elect per channel, or apply a per-channel focus-index
offset" — is **fact 1417's ARGUED proposal**, already on the books. What was genuinely
missing, and what this milestone contributes, is three things:

1. **Independent replication** with a different instrument, different tiling, and two
   stacks M107 never measured (`lavendar-cpl`, `bee-2-cpl`).
2. **The radial discrimination M107 could not perform.** M107 measured *one 512×512
   ROI per stack* and therefore had no radial lever at all. Without it, "axial" was an
   attribution, not a measurement. This work tiles the whole field.
3. **The defect attribution** — which is the part the brief actually cared about, and
   which comes back negative on both counts.

---

## 2. The instrument, and why it should be believed

Full detail in the module docstrings. The load-bearing choices:

- **No demosaic anywhere in the focus path.** Four native CFA lattices (R, G1, G2, B)
  read straight from the ARW. Verified geometry, not assumed: `raw_pattern [[0,1],[3,2]]`,
  `color_desc RGBG` → RGGB; R=(0,0), G1=(1,0), G2=(0,1), B=(1,1); visible 4688×7028 →
  planes 2344×3514; black 512, white 16383.
- **Registration is integer-only** (rule 6). Estimated on **G1 alone** and applied
  identically to all four planes — estimating per-channel shifts would absorb lateral
  CA into registration and contaminate the very question being asked. `map_coordinates`
  appears nowhere in the focus path.
- **The independent statistical unit is the TILE, not the point.** The 27-px box support
  correlates points 10 px apart; pooling ~12 000 points and quoting √n would understate
  the uncertainty roughly tenfold. Tilewise and pooled are printed side by side, always.
- **The gate is reported as a ladder, never as a chosen threshold** (rule 5).
- **The raw statistic is printed beside every excess-over-control, in the same row**
  (rule 3), and the null is evaluated in the same radial bins (rule 4).

### 2.1 The sensor noise was measured, not guessed

The first validation run failed: only 8–18 of 40 804 synthetic points reached confidence.
The cause was a **guessed** noise model carrying 5.1× too much variance (`var = S·2.5`
instead of `var = S/g + r²`). Rather than tune it, I measured it — photon transfer,
`b0b_noise.py`:

> **gain 2.052 e⁻/ADU, read noise ≈ 0–2 ADU, R² = 0.998**, four independent fits agreeing to 1.8%.

This matters beyond bookkeeping: it is what makes the planted-offset recovery below a
real test rather than a test of my own guess.

### 2.2 Two bugs found and fixed, both recorded rather than silently patched

- **Phase correlation fails outright on low-structure tiles.** One tile returned 91 px /
  −51 px on its last three frames while every other tile correctly returned 0 — and true
  drift on that stack is *exactly zero*. A plain median filter does not remove a run of
  outliers at a track's end. Fixed with a Theil–Sen line plus outlier replacement;
  `track_res` now gates tiles.
- **`uniform_filter` preserves its input dtype**, so on a uint16 image the background
  estimate truncates and `G − bg` **wraps around** wherever a pixel is darker than its
  neighbourhood — turning every negative into ~65535. The ridge threshold is then derived
  from that array's own standard deviation, so the failure is *silent and self-consistent*:
  it reported zero ridge pixels rather than raising. This is **rule 1's hazard in a
  different costume** — a dtype quietly degrading a measurement — and it cost a run.
  `hair_chroma` now casts to float64 on entry, with the reason in the docstring.

---

## 3. Headline number

Sub-frame peak by 3-point parabola vertex through the argmax and its two neighbours,
offset clipped to ±1 frame. Uncertainty is the standard error **across tiles**.

| stack | frames | tiles used | dR = k_R − k_G | dB = k_B − k_G | **NULL** = k_G1 − k_G2 |
|---|---:|---:|---:|---:|---:|
| `lavendar-cpl` | 299 | 14 | **−0.8075 ± 0.0321** | −0.7185 ± 0.0381 | **+0.0005 ± 0.0086** |
| `coffee-bean` | 105 | 31 | **−0.8100 ± 0.0125** | −0.4845 ± 0.0131 | **+0.0113 ± 0.0075** |
| `couch-fibers-cpl` | 299 | 3 | **−0.8977 ± 0.0354** | −0.7124 ± 0.1574 | **+0.0004 ± 0.0135** |
| `bee-2-cpl` | 299 | 11 | **−0.6601 ± 0.0287** | −0.7540 ± 0.0222 | **+0.0068 ± 0.0101** |

**Range: dR −0.66 to −0.90 frames; dB −0.48 to −0.75 frames.** Both sit *inside*
M107's independently measured −0.67…−1.07 and −0.36…−0.75. The effect replicates.

**Sign consistency** (a lateral effect must reverse across the centre; an axial one must not):

| stack | dR<0 | dB<0 | NULL<0 (must be ≈50%) | n points |
|---|---:|---:|---:|---:|
| `lavendar-cpl` | **100.0%** | 99.8% | 43.0% | 1 492 |
| `coffee-bean` | **99.9%** | 99.3% | 39.3% | 6 155 |
| `couch-fibers-cpl` | **99.7%** | 100.0% | 47.5% | 297 |
| `bee-2-cpl` | **99.7%** | 99.6% | 46.5% | 789 |

**Cost of electing on green:** R forfeits **4.22 / 6.62 / 7.36 / 7.54%** of its gradient
energy across the four stacks, B forfeits **3.51 / 5.19 / 7.06 / 7.13%**. The null floor
on the same statistic is **0.01–0.02%**. (M107 reported 8.96–14.74% for red on its ROIs;
mine are lower, which is expected — I average over the whole field including tiles with
less structure, M107 measured one chosen ROI.)

**R and B are on the same side of green — both negative, both ahead.** This confirms
fact 1416's secondary-spectrum signature and does **not** contradict it. Nothing here
should be modelled as symmetric straddling.

### 3.1 The gate is not doing the work

| thr | n | dR | dB | NULL | sign dR |
|---:|---:|---:|---:|---:|---:|
| 1.1 | 1492 | −0.8310 | −0.7079 | +0.0110 | 100.0% |
| 2.0 | 1488 | −0.8329 | −0.7090 | +0.0107 | 100.0% |
| 3.0 | 1469 | −0.8311 | −0.7061 | +0.0106 | 100.0% |
| 5.0 | 1447 | −0.8273 | −0.7066 | +0.0109 | 100.0% |

Flat to the fourth decimal over a 4.5× range of threshold. The prominence gate never
binds — the estimator's `interior & unimodal` test rejects a flat curve first — so the
answer is not a property of where a line was drawn.

### 3.2 Physical units — and why I mostly decline to give them

`FocusDistance2` yields only **4 distinct values across 105 frames**. Fact 50 is explicit:
*"`FocusPosition2` is a coarse encoder — never infer a fine sweep from it; measure the
sweep from the pixels."* Any µm-per-frame figure derived from `span/(n−1)` is
DERIVED-UNDER-ASSUMPTION and I will not lead with one.

The defensible physical statement is measured entirely from pixels: the through-focus
gradient-energy curve has **HWHM = 2.50 frames** (FWHM 5.0 frames), so

> **dR = −0.32 HWHM = −16% of the through-focus FWHM; dB = −0.19 to −0.30 HWHM.**

In plain terms: **red is misfocused by about a sixth of the operator's own depth of
focus.** That is small but not negligible — it is the 4–7.5% gradient-energy forfeit,
seen from the other side.

---

## 4. LoCA or lateral CA? — three discriminators, all pointing the same way

### 4.1 Structural: the instrument is blind to lateral CA by construction

This is the strongest argument and it costs nothing. The estimator returns the position
of a maximum **along the frame axis**. A lateral magnification error is a spatial
displacement that is *the same in every frame of the bracket*. Translating a structure
sideways changes which pixels see it; it does not change which frame is sharpest. A
k-independent spatial displacement therefore **cannot move a peak along k**.

The one leak is focus breathing — if magnification changes through the bracket, the
lateral displacement becomes weakly k-dependent. That leak is bounded empirically by 4.2
and 4.3.

### 4.2 The intercept at the optical centre — the decisive test

Lateral CA is a *radial* magnification error: exactly zero on axis, growing with radius.
LoCA has no reason to vanish on axis. So fit the offset against radius and read the
intercept. Bootstrap over **tiles**, 4 000 resamples.

| stack | statistic | tiles | **intercept at r=0** | 95% CI | value at r_max | slope (frames/px) |
|---|---|---:|---:|---|---:|---:|
| `lavendar-cpl` | dR | 14 | **−0.8183** | [−0.976, −0.454] | −0.853 | −2.7e−05 |
| `lavendar-cpl` | dR − NULL | 14 | **−0.8429** | [−1.018, −0.503] | −0.831 | +9.2e−06 |
| `coffee-bean` | dR | 31 | **−0.8765** | [−0.933, −0.822] | −0.758 | +6.2e−05 |
| `coffee-bean` | dR − NULL | 31 | **−0.8473** | [−0.900, −0.793] | −0.820 | +1.4e−05 |
| `lavendar-cpl` | NULL | 14 | +0.0246 | [−0.021, +0.087] | −0.022 | −3.6e−05 |
| `coffee-bean` | NULL | 31 | −0.0293 | [−0.043, −0.018] | +0.062 | +4.8e−05 |

**The whole effect is present on axis.** Lateral CA must be zero there; this is −0.85
frames with a CI that excludes zero by more than twenty standard errors on `coffee-bean`.
The null's intercept, by contrast, is within 0.03 frames of zero on both stacks.

The **null-corrected slope is essentially zero** — +9.2e−06 and +1.4e−05 frames/px, i.e.
0.015–0.023 frames across the entire measured radius against an effect of −0.85. **Flat
to 2%.**

*Caveat, stated because it matters:* on `bee-2-cpl` the intercept CI is [−0.892, +0.070]
and does include zero. That is not evidence of laterality — it is because bee-2's usable
tiles span only r = 820…1312 plane px, so extrapolating to r = 0 is a long throw from a
short lever. `couch-fibers-cpl` retained only 3 tiles and gets no fit at all. The radial
conclusion rests on `lavendar-cpl` and `coffee-bean`, which do have central coverage.

### 4.3 Rule 4 is live, and it changed how I read the radial fit

On `coffee-bean` the **NULL itself trends with radius** (R² 0.5605, perm p 0.0010,
+0.0817 frames centre→corner). Rule 4: *a control that varies systematically along the
axis you are binning on is not a control on that axis.* So the raw radial fit on that
stack is not interpretable on its own, and I report both arms:

| r_mid (plane px) | tiles | dR | dB | NULL | **dR − NULL** | sign dR |
|---:|---:|---:|---:|---:|---:|---:|
| 456 | 6 | −0.8127 | −0.4070 | −0.0065 | **−0.8062** | 100.0% |
| 740 | 6 | −0.8521 | −0.4403 | −0.0066 | **−0.8455** | 99.9% |
| 1020 | 6 | −0.8492 | −0.4895 | +0.0034 | **−0.8526** | 99.8% |
| 1170 | 6 | −0.7711 | −0.4804 | +0.0511 | **−0.8223** | 99.8% |
| 1631 | 7 | −0.7632 | −0.6165 | +0.0542 | **−0.8174** | 100.0% |

The raw column wanders by 0.089 frames and produces a nominally significant slope
(p 0.027). The null-corrected column spans **0.046 frames on a −0.82 effect — 5.6%**, and
its slope is not distinguishable from zero. The apparent radial trend was mostly the
control moving, exactly as rule 4 warns.

**Conclusion: this is longitudinal chromatic aberration.** Flat in radius, non-zero on
axis, sign-consistent at 99.7–100% against a 39–48% null, and structurally out of reach
of a lateral mechanism.

### 4.4 What dB does, honestly

dB shows a genuine radial trend on three stacks (`lavendar-cpl` p 0.0235,
`coffee-bean` p 0.0010, `bee-2-cpl` p 0.0875), growing more negative outward by
0.25–0.34 frames centre→corner. It survives null-correction. Its intercept is still
firmly non-zero (−0.48, −0.30). So **blue is axial with a radial component on top** —
plausibly the lateral/axial cross-term, or field curvature differing by wavelength.
I flag this as real but under-powered (14, 31 and 11 tiles) and would not build on it
without more field coverage. It does not affect the red result or any conclusion below.

---

## 5. Does it explain the rainbow speckle? — **No**, and this is quantitative

### 5.1 Design

Ridges are found on **green alone**, so the selection cannot be biased by the chroma
being measured. Chroma is high-passed against a 25-px local background so subject colour
cannot masquerade as a fringe. Four arms through the identical estimator:

- **MERGE** — the shipped stack output. The defect as observed.
- **SINGLE** — one raw frame, binned to the same composition, no stacking at all. Carries
  the full optical axial CA of the lens and none of the stacker's election behaviour.
- **FORWARD** — the merge with R and B replaced by blurred copies, blurred by *exactly*
  the amount the measured axial offset costs. The blur is **not guessed**: b2 measured
  the gradient-energy forfeit directly (R 6.62%, B 5.19%), so sigma is calibrated by
  bisection until blur(R) loses exactly that much. This is a **dose-matched null in the
  quantity that actually drives the effect** (rule 3), not a magnitude-matched one.
- **FORWARD 10×** — the same construction at ten times the dose, present so that a null
  result at 1× is interpretable. Without it, "nothing happened" could mean the statistic
  is inert.

### 5.2 Result

| arm | structures | rg_sd | bg_sd | **sign-flip rate** | consistency | frac R/G positive |
|---|---:|---:|---:|---:|---:|---:|
| merge (observed defect) | 400 | 0.0816 | 0.0773 | **0.417** | 0.667 | 0.281 |
| single frame, no stacking | 141 | 0.0495 | 0.0462 | **0.448** | 0.636 | 0.419 |
| **forward, measured dose** | 400 | 0.0802 | 0.0761 | **0.400** | 0.699 | 0.247 |
| **forward, 10× dose** | 400 | 0.0913 | 0.0871 | **0.125** | 0.929 | 0.053 |

Blur calibration achieved its target exactly: R σ 0.384 px → 6.62% loss (target 6.62%);
B σ 0.369 px → 5.20% (target 5.19%).

### 5.3 Reading

**Adding a whole second dose of the measured axial CA is almost invisible.** Chroma
amplitude moves by −1.7% (0.0816 → 0.0802); the flip rate moves by 0.017. **Ten doses
move the flip rate by a factor of 3.3** (0.417 → 0.125) and drive sign consistency to
0.929. The statistic is emphatically responsive. The measured dose is simply far too small.

Taking the dose-response as roughly linear in the sign-imbalance statistic
(0.023–0.034 per dose unit, consistent between the 1× and 10× arms), the axial CA
actually present accounts for about **10–16% of the observed departure from chance** —
a modulator, not a cause.

**The mechanism is wrong, not just the magnitude.** A defocus difference is a *low-pass*
operation and cannot create structure at the pixel scale. The observed flip rate of
0.417 means the chroma sign reverses between adjacent ridge pixels nearly half the time.
An analytic check settles it: for a structure with a fraction q of positive signs, a
random ordering gives expected flip rate 2q(1−q). With q = 0.281 that is **0.404** —
against an observed **0.417**. *The observed chroma has no spatial correlation beyond its
own sign imbalance.* Blur produces the opposite: at 10× dose, consistency rises to 0.929
precisely because blur imposes a long correlation length. Confetti is what an
uncorrelated per-pixel process looks like, and blur is not one.

**And 61% of the chroma amplitude is already present in a single unstacked frame**
(rg_sd 0.0495 vs 0.0816), at essentially the same flip rate (0.448 vs 0.417). Whatever
makes the speckle is largely there before the stacker touches it.

> **Verdict: axial CA does not cause the rainbow speckle.** The *sign* is consistent with
> it — 72% of ridge pixels show a red deficit at the crest, which is what a blurred red
> does — but the magnitude is an order of magnitude short and the correlation length is
> wrong. Fixing LoCA will not remove the confetti.

---

## 6. Does it explain the magenta rim? — **No**, and the rim is not magenta

### 6.1 The rim is red-only at every stage of the render

Measured in **linear light at every rung** (the gallery JPEG is pushed back through the
inverse sRGB EOTF first, so all four rows are ratios of linear light and the transfer
curve's non-linearity is not silently folded into the comparison):

| rung | R/G excess | B/G excess | magenta? |
|---|---:|---:|---|
| 1. camera-native linear, binned (byte-frozen measurement output) | +1.43% | **+0.00%** | no |
| 2. + camera colour matrix (`--linear-srgb --binned`) | +2.71% | **+0.20%** | no |
| 3. gallery `--srgb --demosaic`, re-linearised | +3.77% | **−0.04%** | no |

The colour matrix roughly doubles the red excess. **Blue never appears at any rung.**

### 6.2 Rule 7: I went and looked

The pooled statistic above reports saturation 0.05, which is nearly colourless — and the
picture plainly shows a coloured band. Rule 7 says the picture wins, so the statistic was
measuring the wrong population, not refuting the picture. The dilution is that it pools
all 5 267 boundary points including the large fraction where the bean meets a dim or
cluttered surround and there is no visible fringe at all.

Re-measured on the **high-contrast subset** — selected on far-background *brightness*, a
contrast criterion carrying no chroma information, so the selection cannot manufacture the
colour being measured:

> **rim sRGB8 = R 195.9, G 167.8, B 155.5 — hue 18°, saturation 0.21**
> **R/G +42.35%, B/G −14.78%** (n = 1 305 boundary points, at +1.0 px along the outward normal)

That is a **pink / salmon** band, and the 4× crop (`fig/coffee-bean-rim-4x.png`) shows
exactly that: a vivid pink line between the brown bean and the white background. The
number and the picture now agree.

### 6.3 The discriminator, stated before the number was read

Blue is the channel that separates the two mechanisms, because the two make opposite
predictions about it:

| mechanism | predicts B/G at the rim | measured |
|---|---:|---:|
| **axial CA** (dB/dR = 0.60 on this stack) | **+25.4%** | |
| **lateral CA** (ε_B/ε_R = 0.097, fact 1414) | +4.1% | |
| — | | **−14.8%** |

**Axial CA is off by 40 percentage points and gets the sign wrong.** It requires blue to
be in excess; blue is in deficit. This is not a marginal miss.

Two further facts independently exclude axial CA here:

- **The rim is present in a single unstacked frame** at +3.97% R/G on outward normals,
  against the merge's +4.43%. Axial CA is a *stacking* artefact — it arises from electing
  on green and gathering all channels from the elected frame. It cannot exist in a frame
  that was never stacked.
- **The rim is direction-dependent along the radius**: +4.43% on outward normals versus
  −0.10% on inward. Axial CA is an isotropic blur difference and has no radial handedness.
  A radial magnification error does.

### 6.4 The competing hypothesis, tested rather than assumed

Before concluding "not axial, look elsewhere", the obvious alternative had to be excluded:
the rim may not be chromatic at all. If signal from the **subject** leaks outward across
the silhouette — a contamination or halo mechanism, achromatic in itself — the rim is just
background with bean mixed in, and it inherits the bean's colour. The bean is brown:
red-rich, blue-poor. That would produce R up, G down, B down further, which is what was
measured.

The test is falsifiable: fit `rim = (1−f)·background + f·subject` **independently in each
channel**, in linear light. A mixing mechanism is achromatic in f, so all three channels
must return the same f.

> **f = R 0.401, G 0.592, B 0.628** — spread 0.227.

**Green and blue agree to 0.036; red is the outlier by 0.21.** So the rim is *mostly* an
achromatic subject-bleed (f ≈ 0.61 for G and B) with a **red-specific** departure on top.
That is precisely lateral CA's signature: ε_R is ~10× ε_B, so red is displaced radially and
green and blue essentially are not.

Axial CA predicts the opposite structure — it would push B's f away from G's by 0.60× red's
departure, i.e. by 0.12. The measured B−G separation is **+0.036, and in the wrong
direction** (blue is *more* mixed than green, not less).

> **Verdict: the rim is a pink, not magenta, edge produced by an achromatic subject-bleed
> halo carrying the subject's own warm colour, plus a red-only radial displacement
> consistent with the already-characterised lateral CA of fact 1414. Axial CA is excluded
> quantitatively and with the wrong sign.**
>
> The achromatic halo component (f ≈ 0.61) is much the larger term and is **BUILD-HALO's
> territory, not mine** — I flag it rather than claim it. This is also consistent with the
> +11.76% inward-normal luminance excess measured in §3 of `json/b3b_rim.json`.

---

## 7. Negative controls and planted-offset recovery

Both are required by the brief. Both are clean.

### 7.1 Planted-offset recovery (V3 / V3b)

Synthetic stacks with a **known** per-channel offset, at the **measured** sensor noise
(§2.1), through the identical estimator:

| dose planted | noise | recovered dR | recovered NULL | n confident |
|---:|---|---:|---:|---:|
| −0.5 frames | none | **−0.5000** | 0.0000 | all |
| −1.0 frames | none | **−1.0000** | 0.0000 | all |
| −1.0 frames | 0.5× measured | **−1.0179** | −0.0054 | 25 411 |
| −1.0 frames | 1× measured | **−1.0650** | — | 1 876 |
| −1.0 frames | 2× measured | breaks down | — | — |
| **zero dose** | 1× measured | **+0.0928** | +0.1451 | — |

Noise-free recovery is exact to four decimals. At the true sensor noise the recovery is
6.5% high on a 1-frame plant. The **instrument floor** is therefore ≈0.005 frames at high
prominence and ≈0.1 frames at low prominence — comfortably below the −0.66…−0.90 headline.

Supporting checks: **V1** shift convention, 6/6 planted rolls recovered exactly with
correct sign. **V2** parabola vertex, max error 0.0052 frames. **V5** summed-area path vs
`uniform_filter`, max relative error 6.8e−08.

### 7.2 Low-contrast negative control — the instrument declines, and when forced, it guesses

The brief asks for a region where no channel has a well-defined peak. My first attempt
(A1: points passing `interior & unimodal` but failing the prominence gate) came back
**empty** — the prominence gate never binds, because the unimodality test rejects a flat
curve first. *A control that cannot fire is not a control*, so I removed the refusal:
**A3** re-estimates every point the estimator rejected, by the same parabola about its
argmax, with no quality test at all. These are by construction the points where no channel
has a well-defined peak.

| arm | n points | median prominence | dR | dB | NULL | **sign dR<0** |
|---|---:|---:|---:|---:|---:|---:|
| treatment | 1 492 | 39.4 | −0.8310 | −0.7079 | +0.0110 | **100.0%** |
| A2 lowest-prominence tiles | 402 | 19.1 | −0.8877 | −0.7461 | +0.0256 | 100.0% |
| **A3 forced, no peak present** | 9 308 | 1.30 | −0.1491 | −0.4318 | +0.0257 | **50.6%** |

**A3 is the clean result.** Forced to answer where there is no signal, the instrument's
**sign consistency collapses to chance** — 50.6% for dR, 52.8% for dB, 48.8% for the null.
It does not manufacture a confident per-channel offset. (Its pooled *median* is not
identically zero, which is honest: with no peak the argmax is arbitrary and the
distribution is heavy-tailed. The location statistic is meaningless there; the sign
statistic is the one that discriminates, and it is exactly at chance.)

A2 is worth noting separately: at **half** the prominence the effect is undiminished
(−0.89 vs −0.83, still 100% sign-consistent). The result is not prominence-driven.

**Rule 4 check on the controls themselves:** neither control trends on the radius axis —
A3 dR R² 0.0016 (p 0.81), A3 NULL R² 0.0105 (p 0.50); `lavendar-cpl` NULL R² 0.0779
(p 0.34). The `coffee-bean` NULL *does* trend, and §4.3 handles that explicitly rather
than ignoring it.

### 7.3 The G1−G2 null

Present in every table above. Two green sites of the *same* colour on the *same* sensor,
through the *identical* pipeline: it matches the treatment in structure completely and
differs only in that no chromatic effect can exist between them. It reads **+0.0005 to
+0.0113 frames** against a −0.66…−0.90 treatment — a factor of 60–1600 — and its gradient
forfeit is 0.01–0.02% against 3.5–7.5%.

### 7.4 Quantisation dose-response (rule 2)

The algebraic argument says this is safe — the raw quantisation step is 1 ADU while shot
noise at the working level is ~40 ADU, so the input is dithered ~40× over. But rule 5 says
form-based arguments do not survive here, so a dose-response ladder was planted in the
quantisation step (1, 4, 16, 64, 256 ADU) and the measurement re-run at each, sharing one
decode per frame across all five doses.

**Status at time of writing: running** (`b4_controls.py b coffee-bean`, results to
`json/b4_armB_coffee-bean.json`). The headline should be treated as carrying this one
outstanding check. My expectation, stated in advance so it can be wrong: dR is stable to
within the instrument floor up to at least 64 ADU, because it is a *location* statistic on
a curve whose peak-to-median prominence is ~39×, and 256 ADU (a 1/64 of full scale step)
is where the through-focus curve should start to flatten.

---

## 8. The exact Rust change I would want

**I did not make it. No `.rs` file was modified by this agent.** This is a specification
for whoever owns the files.

### 8.1 What to change

**File:** `crates/strehl-core/src/focus.rs` — the election is computed there, from
`gradient_magnitude(luma, …)` then `normalise_by_luma_sigma` using
`noise.green_luma_sigma`. **Do not change the election itself.** It stays green-only.

**File:** the merge gather (`crates/strehl-core/src/merge.rs`) — where the single elected
index is reused across all four CFA accumulators.

**The change:** when gathering channel *c* at a pixel whose elected index is `k`, read
from index `k + off[c]` instead of `k`, where

```
off[R]  = -0.80    // frames; k_R - k_G, measured
off[G1] =  0.00
off[G2] =  0.00
off[B]  = -0.60    // frames; k_B - k_G, measured
```

This is **fact 1417's ARGUED alternative**, and this milestone promotes it to MEASURED and
supplies the coefficients. It costs one extra pass over the bracket at most, not the
2.8× CPU / 4–4.5× wall clock that full per-channel election costs, and it needs no
per-channel noise model.

### 8.2 Details that are not optional

- **The offset is fractional.** Either interpolate between frames `floor(k+off)` and
  `ceil(k+off)`, or round. Rounding to the nearest frame recovers about 60% of the
  available gain at zero extra cost and introduces no resampling; interpolating recovers
  more but blends two frames, which is a photometric change and needs its own check.
  **I would ship rounding first.**
- **Clamp at the bracket ends.** A pixel electing frame 0 has no frame −1. Clamp and
  accept that the correction tapers to zero in the first and last ~1 frame.
- **Sign convention:** negative means *earlier in filename order*. Verified by V1 (§7.1),
  6/6 planted rolls, correct sign. Get this wrong and the change **doubles** the aberration.
- **R and B are on the same side of green.** Do not implement this as a symmetric
  straddle — see fact 1416, which killed M107's registered bar B3 on exactly that clause.

### 8.3 It must ship OFF by default

This is the important part and it is not caution for its own sake. Fact 1783: the shipped
**lateral** coefficient did not transfer between scenes (1.0557 vs 1.2496), and that is why
the existing CA correction is default-off. My dR spans **−0.66 to −0.90 across four
stacks — a 1.36× range** — which is smaller but the same kind of problem. A single baked
constant will be wrong by 20–30% on some scene.

Recommended: a `--axial-ca[=R,B]` flag, off by default, with the measured defaults above,
and a documented note that the coefficients are rig-specific (Sony FE 100mm F2.8 Macro GM
+ 2× Viltrox TC at f/8) and were measured on four stacks.

**Better, and I would rather someone did this instead:** the offset is *measurable from
the bracket itself*, at low cost, using exactly the estimator in `b1_curves.py` — sample a
few hundred high-prominence points, take the median per-channel peak offset, and use that
stack's own value. That removes the transfer problem completely and is the version I would
argue for. It is roughly one extra registration-free pass over a strided subsample.

### 8.4 What this change will and will not do

**Will:** recover the 4.2–7.5% of red gradient energy and 3.5–7.1% of blue that election
on green currently forfeits. That is a genuine, novel capability — correcting LoCA as a
side effect of stacking, from information already in the bracket. As far as I can tell no
shipping stacker does this.

**Will not:** fix the rainbow speckle (§5) or the pink rim (§6). Both were measured against
it and both came back negative. If it ships and someone expects the gallery defects to
disappear, they will be disappointed and will wrongly conclude the change did nothing.

---

## 9. Open questions, logged not blocked on

1. **The quantisation ladder (§7.4) had not finished at the time of writing.** The headline
   carries this one outstanding check.
2. **The dB radial trend (§4.4)** is real but under-powered (14/31/11 tiles). It should not
   be built on without more field coverage.
3. **`couch-fibers-cpl` lost 51 of 54 tiles on registration** — that stack has real drift,
   unlike the other three which have exactly zero. Its dR (−0.8977) rests on 3 tiles. It is
   consistent with the rest but it is the weakest row in the table.
4. **What actually causes the rainbow speckle** is unresolved. §5 excludes axial CA and
   shows 61% of it is pre-stacking. The pixel-scale correlation length points at either a
   per-pixel demosaic artefact or **election instability** — adjacent pixels electing
   different frames. The stacker has an `--index-map` flag that dumps the elected frame
   index per plane pixel; measuring the election's spatial roughness along the hairs would
   settle it directly and cheaply. **I recommend this as the next milestone** and did not
   run it only for time.
5. **The achromatic subject-bleed halo at the rim** (f ≈ 0.61, §6.4) is the dominant term in
   that defect and is BUILD-HALO's territory. Coordinate rather than duplicate.

---

## 10. Reproducing this

```
experiments/BUILD-CHROMA/src/
  common.py          CFA read/split, Sobel energy, summed-area box, phase correlation,
                     Theil-Sen integer track, parabola peak
  b0_validate.py     V1 shift convention, V2 parabola, V5 summed-area equivalence,
                     V3 planted dose ladder, V3b noise-free, V3c noise ladder
  b0b_noise.py       photon-transfer gain / read noise
  b1_curves.py       the measurement: registration pass + focus pass, 9x6 whole-field tiling
  b2_analyse.py      peaks, gate ladder, tilewise vs pooled, radial bins, sign, loss, HWHM
  b2_report.py       printer
  b4_controls.py     arm A negative controls, arm B quantisation ladder
  b5_hair.py         rainbow speckle: merge / single frame / forward model / 10x dose
  b6_discriminate.py LoCA vs lateral: intercept at r=0, bootstrap over tiles
  b3_defects.py      rim + hair primitives; read16 enforces rule 1
  b3b_rim.py         rim: radial bins, outward vs inward normals, single-frame control
  b7_magenta.py      render-ladder attribution, linear light at every rung
  b8_rimcolour.py    what colour the rim actually is; subject-mixing test
```

Order: `b0b_noise` → `b0_validate` → `b1_curves` → `b2_analyse` → `b6_discriminate`,
`b4_controls`, `b5_hair`, `b7_magenta`, `b8_rimcolour`.

Rules observed: 16-bit TIFFs read only via `tifffile` with a dtype assert (1); quantisation
dose-response run rather than argued (2); raw statistic beside every control in the same
row (3); control's own radial trend reported and corrected for (4); gate reported as a
ladder, no triage rule of thumb (5); integer-only registration in the focus path (6);
went and looked when the number disagreed with the picture, and the picture won (7).
