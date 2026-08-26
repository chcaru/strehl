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

All checks the brief required are complete and clean: planted offsets recover exactly
noise-free (−0.5000, −1.0000); the instrument's sign consistency collapses to **50.6%**
(chance) when forced to answer where no peak exists; the G1−G2 null is 60–1600× smaller
than the effect; and the headline survives a **256× quantisation coarsening** with a shift
of 0.0048 frames.

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

### 5.4 So what does? Two more suspects, both also excluded

Having excluded axial CA I went after the two mechanisms that *can* produce a pixel-scale
process, because "not LoCA" is only half an answer and the brief asks for the search to be
redirected.

**Election instability.** The merge elects one frame per pixel. If neighbouring pixels
along a hair elect frames far apart in the bracket, the merge is stitched from samples at
different focus depths and different noise realisations — genuinely pixel-scale, with no
smoothness constraint. The stacker can be asked directly: `strehl stack --index-map` dumps
the elected 0-based frame index per plane pixel. Roughness is measured as the mean absolute
difference to the 4-neighbours — a first difference, deliberately, because the elected
index has a real and wanted large-scale gradient across a tilted subject that any windowed
variance would misread as roughness.

| | median | p90 | n |
|---|---:|---:|---:|
| on hair | **0.000** | 0.500 | 103 617 |
| off hair (background beside it) | **0.000** | 0.500 | 666 321 |
| whole field | 0.000 | — | — |

**The election field is smooth at the pixel scale**, and no rougher on the hairs than
beside them. There is a tail — 22% of ridge pixels sit at roughness > 0.5 frames, with
excursions to 191 frames — and it does carry more chroma, but only **1.15×** between the
smoothest and roughest bins. Election jitter is a real but minor contributor.

**CFA co-siting.** In this binned output each pixel is one 2×2 sensor quad, and R, G and
B are *not co-sited* inside it: R sits at (0,0) and B at (1,1), a full sensel apart on the
diagonal. For a hair one or two sensels wide the R site and the B site are looking at
different parts of the structure, and binning asserts they are the same point — ordinary
Bayer aliasing on detail above Nyquist. It has the right correlation length, exists before
stacking, and is untouched by defocus dose. It makes a sharp prediction nothing else here
makes: chroma must scale **inversely with structure width** and vanish for structures
several sensels wide.

| structure width | n | median &#124;R/G high-pass&#124; |
|---|---:|---:|
| 2–3 px | 94 554 | 0.0448 |
| 4–6 px | 9 063 | 0.0417 |

**1.08×.** Essentially flat. The prediction fails, so this is not the dominant term either
— though I note the width estimator only populated two bins and is coarse, so this
exclusion is weaker than the other two.

### 5.5 What is left, stated as ARGUED not measured

Three stratifications — defocus dose, election roughness, structure width — all come back
nearly flat, at |R/G high-pass| ≈ 0.043–0.049 across every bin. **A quantity that does not
respond to any structural covariate looks like a noise floor, not an artefact.**

The arithmetic is at least consistent with shot noise. A chroma ratio carries ~√2 times a
single channel's relative noise, so 4.5% chroma implies ~3.2% per channel, i.e. ~980 e⁻,
i.e. ~480 ADU above black at gain 2.052 e⁻/ADU (§2.1) — an entirely plausible signal level
for a thin, dim hair. And it would explain the one number that otherwise looks backwards:
the merge shows *more* chroma than a single frame (0.0816 vs 0.0495) when stacking ought to
reduce noise. Electing on `argmax` of gradient energy is a **selection on noise** — it
preferentially picks the frame where noise happened to inflate the gradient — so a
max-selecting stacker can amplify chroma noise rather than average it down.

**This is ARGUED, not MEASURED, and I am labelling it that way rather than claiming it.**
The decisive test is cheap and I did not have time for it: re-render with the election
replaced by a fixed frame index (removing the selection-on-noise bias while keeping
everything else), or compare chroma against the per-pixel photon count predicted by the
measured gain. Either would settle it in one run.

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
quantisation step and the measurement re-run at each dose, sharing one decode per frame
across all five so that quantisation is the *only* thing varying. The registration track
was reused from `b1_curves`, so the integer-shift discipline of rule 6 is inherited
unchanged.

`coffee-bean`, 105 frames, 31 tiles:

| quantisation step | n confident | dR | dB | NULL |
|---:|---:|---:|---:|---:|
| **1 ADU** (native) | 6 154 | **−0.8187** | −0.4791 | +0.0170 |
| 4 ADU | 6 154 | −0.8189 | −0.4789 | +0.0170 |
| 16 ADU | 6 156 | −0.8173 | −0.4780 | +0.0176 |
| 64 ADU | 6 143 | −0.8221 | −0.4817 | +0.0171 |
| **256 ADU** | 5 821 | **−0.8216** | −0.4788 | +0.0151 |

**dR moves by 0.0048 frames across a 256× coarsening of the input** — well inside the
instrument floor of ≈0.005 frames, and 170× smaller than the effect. dB moves by 0.0037,
the null by 0.0025. The pre-registered expectation in §7.4's earlier draft was "stable to
at least 64 ADU"; it is in fact stable at 256, where a 14-bit sensor has only 64 levels
left. **The headline is not a quantisation artefact.**

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

1. **The dB radial trend (§4.4)** is real but under-powered (14/31/11 tiles). It should not
   be built on without more field coverage.
2. **`couch-fibers-cpl` lost 51 of 54 tiles on registration** — that stack has real drift,
   unlike the other three which have exactly zero. Its dR (−0.8977) rests on 3 tiles. It is
   consistent with the rest but it is the weakest row in the table.
3. **What actually causes the rainbow speckle** is narrowed but not closed. §5 excludes
   axial CA, election instability and CFA co-siting, and leaves shot noise amplified by
   selection-on-noise as the surviving candidate — **ARGUED, not measured** (§5.5). The
   decisive test is one render with the election replaced by a fixed index.
4. **The achromatic subject-bleed halo at the rim** (f ≈ 0.61, §6.4) is the dominant term in
   that defect and is BUILD-HALO's territory. Coordinate rather than duplicate.
5. **The election index map contains excursions of up to 191 frames between adjacent
   pixels** (§5.4). The median is 0.000 so this is a thin tail, but a 191-frame jump across
   one pixel is a large number and nobody appears to have looked at it. It may be benign —
   two genuinely different depths meeting at an occlusion edge — or it may be an election
   pathology. Worth someone's time; it is not mine to chase.

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
  b9_election.py     election roughness from --index-map; chroma vs roughness and width
```

Order: `b0b_noise` → `b0_validate` → `b1_curves` → `b2_analyse` → `b6_discriminate`,
`b4_controls`, `b5_hair`, `b7_magenta`, `b8_rimcolour`, `b9_election`.

Rules observed: 16-bit TIFFs read only via `tifffile` with a dtype assert (1); quantisation
dose-response run rather than argued (2); raw statistic beside every control in the same
row (3); control's own radial trend reported and corrected for (4); gate reported as a
ladder, no triage rule of thumb (5); integer-only registration in the focus path (6);
went and looked when the number disagreed with the picture, and the picture won (7).

---

# PHASE 2 — Lateral CA, measured from each bracket itself

**Commission:** measure the lateral-CA coefficient from each bracket, with no transferred
profile, so that the transfer objection that keeps the shipped correction off by default
no longer applies. Commission it, compare it against the shipped profile in-sample and
out-of-sample, and give an edge-chroma-with-flat-placebo number per stack.

**I did all of that. The answer is not the one the commission expected, and I am reporting
what I measured rather than what was hoped for.**

## 11. Headline: self-measurement is NOT warranted. A one-line profile fix is.

Three findings, in descending order of how much they should change what ships.

**11.1 — `eps_b: None` is the entire remaining defect, and it is worth more than
everything else on the table combined.** Blue is an exact no-op in the shipped record.
I measure blue lateral CA at **+101 to +223 ppm** across six stacks, worth **0.363 px of
uncorrected displacement at the plane corner**, and *any* reasonable fixed blue
coefficient removes about 84% of it. This is the change to make.

**11.2 — the shipped `eps_r = −704.5 ppm` is already correct, and my Phase-2 draft
claiming it over-corrects by 7–26% was wrong.** That draft was built on raw estimates
which are attenuated by a stack-dependent factor of 0.69–0.94. Correcting for the
attenuation (§15) moves my six red measurements from a 39%-spread band that excludes
−704.5 into a 16%-spread band **centred on it**. A fixed −704.5 leaves 0.071 px of
corner residual; a *perfect* per-stack measurement could only reach 0.063 px. The
difference is 0.008 px and nobody will ever see it.

**11.3 — naive self-measurement is 3.6× WORSE than the shipped fixed profile for red.**
Raw self-measured red leaves **0.259 px** of corner residual against the fixed profile's
**0.071 px**, precisely because the estimator under-reads on exactly the low-structure
stacks where it is least able to check itself. Shipping a self-measured coefficient
without an attenuation correction would make red worse on four of my six stacks.

So the transfer objection dissolves, but not the way the commission proposed. It
dissolves because **with six stacks instead of two, transfer works**: leave-one-out, a
coefficient fitted on five stacks and applied to the sixth removes 93% of red and 84% of
blue. The 54.1% reverse-direction figure in `optics.rs` that keeps the correction off is
**not reproduced** by a commissioned estimator (§16.3).

### 11.4 What I am asking for, in one sentence

Set `eps_b` to a measured value, leave `eps_r` alone, and ship the profile **on by
default** on the strength of a six-stack leave-one-out result rather than a two-stack
in-sample one. Full spec in §19. No new code path, no per-render measurement cost, and
no risk of a bad self-measurement on a low-structure stack.

## 12. The instrument, and the two bugs I had to fix to get one

`experiments/BUILD-CHROMA/src/lateral.py`. The model matches `optics.rs` in form:
`d_c(u) = eps_c * u + T_c`, with `u` and `d` in plane px and `eps` dimensionless.

**Design decisions that are load-bearing:**

- **No registration at all.** Every comparison is between two channels *inside a single
  frame*, so frame-to-frame drift cancels identically rather than approximately. The only
  sub-pixel resampling anywhere is `plant_scale`, which manufactures synthetic doses and
  never touches a measured quantity. Rule 6 is satisfied by construction rather than by
  care.
- **CFA native, never demosaiced** — R sites, B sites and the two G sites, as in Phase 1.
- **The structure gate is computed on GREEN ONLY.** Selection on an input that carries no
  chromatic information cannot select for or against the effect. Swept as a ladder, not
  chosen (rule 5).
- **The independent statistical unit is the tile**, and the bootstrap resamples tiles.
- **G1 vs G2 is the null**, carried through the identical path. G1 and G2 come to focus at
  the same distance and have no lateral CA between them, so whatever the null reads is the
  instrument's floor. Reported in the same table as the treatment, every time (rule 3).

### 12.1 Bug one: phase whitening has a magnitude-dependent gain

`phase_cross_correlation(normalization='phase')` — the default, and what I started with —
does not have unit gain. Measured transfer, planted dose against read dose:

| planted | 0.25 px | 0.50 px | 0.75 px | 1.30 px |
|---|---|---|---|---|
| **gain** | **0.60** | 0.94 | 1.09 | 0.92 |

A 200 ppm dose read back as 122 ppm. The shrinkage is independent of tile size (0.588 at
128 px, 0.623 at 448 px), so it is intrinsic to the whitening rather than to windowing.

This is **specifically** disqualifying here and not merely inconvenient: ε_R is about 10×
ε_B, so the two channels sit at opposite ends of that transfer curve and whitening would
read the two arms **on two different scales**. `normalization=None` is flat at 0.995–1.000
across the whole range. That is what the instrument uses.

### 12.2 Bug two: an ungated fit is a measurement of its worst tiles

The green null (truth = 0) initially returned **8.05 plane px** rms with 35% of tiles more
than 3 px out. The failure was entirely low-structure tiles: top structure quintile median
residual **0.054 px**, bottom quintile **8.0 px**. Phase correlation on a featureless tile
does not return a noisy answer, it returns an arbitrary one. Gating on green gradient
energy fixed it; robust IRLS sits behind the gate as a second line of defence and never as
a substitute, because no downweighting rescues a fit whose majority is garbage.

## 13. Commissioning (`c0_lateral.py`) — passes

| test | what it plants | result |
|---|---|---|
| T1b planted ladder | ±2000 ppm radial scale, band-limited synthetic | slope **0.9959**, worst error **10.15 ppm**, rms 0.003 px |
| T2 zero dose | exact copy, and resample-at-zero | **exactly 0** |
| T3 green null, real sky | nothing — truth is 0 | **+12…+23 ppm**, rms 0.03–0.05 px |
| T3b lattice offset | known CFA site offset | recovered to **0.01 px** |
| T5 dose ladder on real R | on top of the real aberration | slope **0.975** |

Both arms the commission asked for are present and clean: a planted dose is recovered to
four decimals, and forced where no aberration exists the instrument returns zero rather
than a confident wrong answer.

## 14. The six-stack measurement (`c1_lateral.py`)

Every tile is measured at *its own* best-focus frame — the idea that turned a 60-tile
single-frame fit into 100–250 tiles and made the gate ladder flat. Gate 2e5,
null-corrected, ppm, with the raw statistic and the null beside it (rule 3):

| stack | n | ε_R raw | null | ε_R corr | 95% CI | R² | ε_B raw | ε_B corr | R² |
|---|---|---|---|---|---|---|---|---|---|
| tweezers-cpl * | 177 | −647.0 | 3.8 | **−650.8** | [−661, −631] | 0.976 | 169.1 | **165.3** | 0.755 |
| bee-3-cpl * | 162 | −500.9 | 19.0 | **−519.9** | [−542, −460] | 0.781 | 174.8 | **155.9** | 0.437 |
| coffee-bean | 209 | −650.7 | 2.4 | **−653.2** | [−659, −643] | 0.988 | 182.8 | **180.4** | 0.876 |
| lavendar-cpl | 103 | −546.1 | 5.9 | **−552.0** | [−573, −518] | 0.888 | 148.9 | **143.1** | 0.498 |
| couch-fibers-cpl | 246 | −651.9 | 2.6 | **−654.5** | [−665, −639] | 0.956 | 94.3 | **91.7** | 0.591 |
| bee-2-cpl | 174 | −518.4 | 30.0 | **−548.4** | [−552, −485] | 0.765 | 144.2 | **114.2** | 0.315 |

`*` = the two stacks the shipped profile was fitted on.

**Read naively, this says the shipped −704.5 over-corrects every stack by 7–26%.** That
reading is wrong, and §15 is why. I am leaving the table in because it is what the
instrument actually reports before correction, and because the correction is the
interesting part.

ε_B is the weaker arm and must be reported as such: its gate-ladder spread is 26–85% on
five of six stacks against ~5% for red, and its R² runs 0.32–0.88.

### 14.1 A trap I fell into and climbed out of

My first radial-bin diagnostic computed a local coefficient as `(d·r̂)/r`. That carries a
spurious `1/r` term from the fitted translation, and it manufactured a convincing
higher-order radial trend — −820 ppm at r=504 against −633 at r=1565 on `tweezers-cpl` —
which was **entirely** accounted for by the fitted `T = (−0.196, +0.035)`. The tool now
reports raw and de-translated side by side. Anyone reading a per-radius coefficient out of
a fit that also has a translation should check this first.

## 15. The attenuation correction, which inverts the story (`c4_attenuation.py`)

The six raw red values fall into two tight clusters, −650…−655 and −520…−552. The clusters
track the null (2–4 ppm vs 6–30 ppm) and R² (0.96–0.99 vs 0.77–0.89) **exactly**. Two
explanations: the optics genuinely differ between scenes, or the instrument under-reads on
the noisier stacks. These have opposite consequences, so I planted a known dose on each
stack and asked for it back.

| stack | ε undosed | ε dosed | delta | **recovery** | ε corrected |
|---|---|---|---|---|---|
| tweezers-cpl | −618.8 | 316.2 | 935.0 | **0.935** | −661.8 |
| bee-3-cpl | −415.7 | 284.4 | 700.0 | **0.700** | −593.8 |
| coffee-bean | −614.6 | 322.9 | 937.5 | **0.938** | −655.6 |
| lavendar-cpl | −499.6 | 332.3 | 831.9 | **0.832** | −600.6 |
| couch-fibers-cpl | −634.4 | 270.9 | 905.3 | **0.905** | −700.7 |
| bee-2-cpl | −467.6 | 224.0 | 691.6 | **0.692** | −676.1 |

Planted 1000 ppm each time. **Correlation between recovery and |ε_R|: r = +0.941.**
Spread before correction **39%**, after **16%**.

That correlation is exactly what "constant optics, varying attenuation" predicts and it is
not what "genuinely different optics" predicts. If the estimator attenuates by a factor
`a`, then dosed reads `a(ε+1000)`, undosed reads `aε`, delta reads `a·1000`, so recovery
*is* `a` and `undosed/recovery` returns `ε` exactly. The mechanism is ordinary regression
dilution: noise in the tile displacements biases the fitted slope toward zero.

**The physical argument is stronger than the statistical one, and it does not depend on
trusting these numbers quantitatively.** All six stacks are the same lens at 200 mm
through the same 2× teleconverter at focus distances spanning 0.2707–0.2771 m (EXIF, all
six, checked). Lateral CA is a chief-ray property, so it is essentially independent of the
f/5.6-vs-f/8 difference too. **There is no mechanism by which a lens changes its lateral
CA because you pointed it at a different insect.** The 39% raw spread therefore *must* be
instrumental, whatever one thinks of the dose ladder — and the dose ladder independently
recovers the same conclusion.

This is the finding that inverts the commission, and I want to be plain that it inverts my
own earlier draft too. I had written the "shipped over-corrects by 7–26%" table before I
ran this test.
## 16. Transfer, leave-one-out (`c5_transfer.py`)

**The statistic is a displacement, not a coefficient.** Applying `e_app` to a stack whose
true coefficient is `e_true` leaves a residual scale error `e_true − e_app`, worth
`|e_true − e_app| · r` plane px at field radius `r`. That is the thing a reader can see at
100%, it is linear in the error, and it does not flatter a small coefficient the way a
percentage would. Reported at the plane corner, r = 2112 px = normalised field height 1.0.

**Every fixed arm is leave-one-out.** A "best fixed coefficient" chosen using the target
stack's own measurement is a self-measured coefficient wearing a disguise and would win by
construction, so each LOO column is computed from the *other five* stacks only.

**What self-measurement's residual actually is.** Self-measurement is not exact and I will
not score it zero. `self naive` carries the full attenuation error — it is what shipping
the raw number would really do. `self de-att` carries the bootstrap CI half-width, which
makes it a statement about its own precision rather than its accuracy; the independent
evidence for its accuracy is §13 and §15, not this table.

### 16.1 RED — residual displacement at the corner, plane px, lower is better

| target | e_true | off | shipped | LOO med | LOO worst | self naive | self de-att |
|---|---|---|---|---|---|---|---|
| tweezers-cpl | −696.0 | 1.470 | 0.018 * | 0.057 | 0.205 | 0.096 | 0.034 |
| bee-3-cpl | −742.7 | 1.569 | 0.081 * | 0.097 | 0.167 | 0.471 | 0.124 |
| coffee-bean | −696.7 | 1.471 | **0.016** | 0.056 | 0.203 | 0.092 | 0.019 |
| lavendar-cpl | −663.5 | 1.401 | **0.087** | 0.126 | 0.273 | 0.236 | 0.070 |
| couch-fibers-cpl | −723.0 | 1.527 | **0.039** | 0.056 | 0.148 | 0.145 | 0.030 |
| bee-2-cpl | −793.0 | 1.675 | **0.187** | 0.203 | 0.273 | 0.516 | 0.103 |
| **mean, all six** | | **1.519** | **0.071** | 0.099 | 0.212 | **0.259** | 0.063 |
| **mean, 4 out-of-sample** | | 1.519 | **0.082** | 0.110 | — | **0.247** | 0.055 |

`*` in-sample for the shipped profile.

**The shipped coefficient is right.** 0.071 px mean residual against a best-possible 0.063
px. **Naive self-measurement is 3.6× worse than doing nothing new**, and worse
out-of-sample too (0.247 vs 0.082). This is the result that kills the commission's
proposal for red.

### 16.2 BLUE — the same table, and the reason this report exists

| target | e_true | off | shipped | LOO med | LOO worst | self naive | self de-att |
|---|---|---|---|---|---|---|---|
| tweezers-cpl | 176.8 | 0.373 | 0.373 | 0.010 | 0.159 | 0.024 | 0.024 |
| bee-3-cpl | 222.7 | 0.470 | 0.470 | 0.107 | 0.256 | 0.141 | 0.102 |
| coffee-bean | 192.4 | 0.406 | 0.406 | 0.043 | 0.192 | 0.025 | 0.022 |
| lavendar-cpl | 172.0 | 0.363 | 0.363 | 0.010 | 0.149 | 0.061 | 0.110 |
| couch-fibers-cpl | 101.3 | 0.214 | 0.214 | 0.159 | 0.256 | 0.020 | 0.017 |
| bee-2-cpl | 165.1 | 0.349 | 0.349 | 0.025 | 0.135 | 0.108 | 0.083 |
| **mean, all six** | | **0.363** | **0.363** | **0.059** | 0.191 | 0.063 | 0.060 |

The shipped column *equals* the off column, exactly, on every row, because `eps_b: None`
makes blue an exact no-op. **0.363 px of blue lateral CA is shipping uncorrected today**,
and a single fixed LOO coefficient removes 84% of it — indistinguishably from
self-measurement (0.059 vs 0.060). Blue is where the win is, and it does not need a new
instrument in the renderer to collect it.

### 16.3 The pair `optics.rs` names, redone

`optics.rs` records tweezers→bee-3 at 95.0% and bee-3→tweezers at 54.1% against a 60% bar,
and that asymmetry is the stated reason the correction is off. With a commissioned
estimator:

| channel | direction | aberration removed | residual at corner |
|---|---|---|---|
| R | tweezers → bee-3 | **93.7%** | 0.099 px |
| R | bee-3 → tweezers | **93.3%** | 0.099 px |
| B | tweezers → bee-3 | 79.4% | 0.097 px |
| B | bee-3 → tweezers | 74.1% | 0.097 px |

**The asymmetry is not reproduced.** Both directions transfer at ~93% for red. I cannot
say from here whether M107's 54.1% was an artefact of its estimator or of its ROI set, and
I am not claiming M107 was wrong — I am reporting that the measurement that keeps the
correction off does not survive re-measurement with an instrument that has a planted-dose
ladder and a green null behind it. That is the evidential basis for §19's request to flip
the default, and it should be weighed as such.

## 17. Withdrawn: the focus dependence of ε (`c6_focusdep.py`, `c7_focusdep2.py`)

I chased a real question here and did not land it. Recording it as a failure rather than
burying it, because the next person will otherwise chase it too.

**The question.** Each stack is a *bracket* — focus distance sweeps across it, and lateral
CA is a function of focus distance. If ε drifts across a bracket then no single scalar per
channel is the right *model*, whatever its source, and the correction would need to be
depth-dependent. That is a much larger change than anything else here, so it needs
settling.

**What c6 found.** Regressing the per-elected-frame coefficient on frame index gave a
sign-consistent red slope on five of six stacks, t = 2.2–4.3, worth **0.26 px at the
corner** across a bracket — which would be 3.6× the residual a good fixed coefficient
leaves, i.e. the dominant remaining error term.

**Why I withdrew it.** c6's control was the green null, and by rule 4 **that is not a
control on this axis**. Tiles do not elect frames at random: near subject matter sits at
one end of the bracket and far at the other, and in these scenes that correlates with
field radius. So a purely *radial* mis-fit would print as focus dependence — and the green
null cannot reveal that, because the null's ε is ~0, so there is no radial term there to
mis-fit. A control that cannot exhibit the failure mode is not a control for it.

**What c7 tried, and how it failed.** Two estimators, both commissioned on each stack's
own real tile geometry and real elected frames so the confound was present in full:

| estimator | planted zero | planted radial-only confound | planted ladder | measured |
|---|---|---|---|---|
| per-tile joint fit | ±14.2 ppm/frame | — | recovery **−1.02** | 8.4 |
| grouped, robust | ±56.1 | **±132.2** | slope **−0.74** | 27.3 |

Both fail their own planted-zero arm: the false-positive ceiling **exceeds** the measured
value in both cases, and neither recovers a planted ladder. The measured/false-positive
ratio is 0.21–0.36×, where anything below ~1× means the instrument is reading itself.

**Conclusion: unproven, in both directions.** I have not shown ε drifts with focus, and I
have not shown it does not. What I *have* shown is that neither of my two estimators for it
is fit to answer. It changes no recommendation in this report — a per-stack scalar cannot
fix a within-bracket drift either, so it does not favour self-measurement over a fixed
profile — which is exactly why I stopped rather than spending the rest of the night on it.

A third attempt should probably not regress on frame index at all, and should instead
compare ε between two *disjoint depth populations at matched radius*, which removes the
confound by construction rather than by modelling it.
## 18. Edge chroma with a flat placebo (`c3_chroma.py`)

The statistic the commission asked for, per stack, four arms plus two diagnostics.
Normalised chroma `(max − min)/max` over the linear channels, averaged over pixel sets
**frozen on the off arm** so every arm is judged on the same pixels: EDGE is the top 1% of
the luma gradient, FLAT the bottom 50%.

FLAT is a built-in placebo rather than a separate experiment. A geometric per-channel
rescale can only move colour where there is structure to move, so it must act on EDGE and
must not act on FLAT. Raw values sit beside every difference, in the same table (rule 3).

**Renders are `--linear-srgb --gate 2.0`, deliberately NOT `--demosaic`.** A
Malvar-He-Cutler demosaic interpolates colour from neighbouring sites, which spatially
mixes the channels at exactly the high-gradient pixels EDGE selects — it would both
manufacture and mask chroma there. The binned output is one real sensor quad per pixel
with no spatial mixing, and it is the same plane grid ε was measured on.

### 18.1 The emulation check, which bounds everything below it

I may not edit a `.rs` file, so a self-measured coefficient cannot be fed to the renderer;
it is applied post hoc in Python on the merged image. That is an approximation — Rust
applies the correction per frame at gather time, *before* the election picks a winner, and
the two commute only where the elected index is constant over the ~1.5 px the correction
moves. `shipped (python)` exists solely to measure the size of that approximation, by
running the same Python path with the same coefficient the Rust arm used.

**It reproduces 75.8–97.9% of the Rust effect, mean 87.2%.** So the Python arms
systematically under-read, and **only Python-vs-Python comparisons in this section are
fair.** The Rust arm is included for scale, not for ranking against Python arms.

### 18.2 The full table

| stack | arm | EDGE | dEDGE | FLAT | dFLAT | edge/flat |
|---|---|---|---|---|---|---|
| **coffee-bean** | off | 0.363353 | -- | 0.199782 | -- | -- |
|  | shipped (rust) | 0.325389 | −10.45% | 0.199092 | −0.35% | 30x |
|  | shipped (python) | 0.331859 | −8.67% | 0.199491 | −0.15% | 60x |
|  | self R only (python) | 0.333650 | −8.17% | 0.199493 | −0.14% | 57x |
|  | self B only (python) | 0.354515 | −2.43% | 0.199811 | +0.01% | 166x |
|  | self R+B (python) | 0.325099 | −10.53% | 0.199522 | −0.13% | 81x |
|  | self/atten 0.938 | 0.323152 | −11.06% | 0.199523 | −0.13% | 85x |
| **tweezers-cpl** | off | 0.302503 | -- | 0.055267 | -- | -- |
|  | shipped (rust) | 0.198053 | −34.53% | 0.054197 | −1.94% | 18x |
|  | shipped (python) | 0.223280 | −26.19% | 0.054265 | −1.81% | 14x |
|  | self R only (python) | 0.229318 | −24.19% | 0.054261 | −1.82% | 13x |
|  | self B only (python) | 0.289121 | −4.42% | 0.054986 | −0.51% | 9x |
|  | self R+B (python) | 0.215247 | −28.84% | 0.053914 | −2.45% | 12x |
|  | self/atten 0.935 | 0.209432 | −30.77% | 0.053905 | −2.46% | 12x |
| **bee-3-cpl** | off | 0.298434 | -- | 0.195633 | -- | -- |
|  | shipped (rust) | 0.257691 | −13.65% | 0.195028 | −0.31% | 44x |
|  | shipped (python) | 0.258542 | −13.37% | 0.194540 | −0.56% | 24x |
|  | self R only (python) | 0.266416 | −10.73% | 0.194720 | −0.47% | 23x |
|  | self B only (python) | 0.290794 | −2.56% | 0.195587 | −0.02% | 108x |
|  | self R+B (python) | 0.259348 | −13.10% | 0.194682 | −0.49% | 27x |
|  | self/atten 0.700 | 0.248743 | −16.65% | 0.194476 | −0.59% | 28x |
| **lavendar-cpl** | off | 0.245642 | -- | 0.075781 | -- | -- |
|  | shipped (rust) | 0.187107 | −23.83% | 0.075837 | +0.07% | 322x |
|  | shipped (python) | 0.195565 | −20.39% | 0.075825 | +0.06% | 357x |
|  | self R only (python) | 0.204766 | −16.64% | 0.075779 | −0.00% | 5176x |
|  | self B only (python) | 0.239066 | −2.68% | 0.075748 | −0.04% | 61x |
|  | self R+B (python) | 0.198892 | −19.03% | 0.075750 | −0.04% | 458x |
|  | self/atten 0.832 | 0.191368 | −22.09% | 0.075777 | −0.01% | 4240x |
| **couch-fibers-cpl** | off | 0.282893 | -- | 0.196172 | -- | -- |
|  | shipped (rust) | 0.225869 | −20.16% | 0.195802 | −0.19% | 107x |
|  | shipped (python) | 0.232849 | −17.69% | 0.195845 | −0.17% | 106x |
|  | self R only (python) | 0.235805 | −16.65% | 0.195845 | −0.17% | 100x |
|  | self B only (python) | 0.280256 | −0.93% | 0.196148 | −0.01% | 77x |
|  | self R+B (python) | 0.233985 | −17.29% | 0.195827 | −0.18% | 98x |
|  | self/atten 0.905 | 0.230008 | −18.69% | 0.195824 | −0.18% | 105x |
| **bee-2-cpl** | off | 0.312988 | -- | 0.207187 | -- | -- |
|  | shipped (rust) | 0.260910 | −16.64% | 0.206617 | −0.27% | 61x |
|  | shipped (python) | 0.264409 | −15.52% | 0.205795 | −0.67% | 23x |
|  | self R only (python) | 0.273279 | −12.69% | 0.206004 | −0.57% | 22x |
|  | self B only (python) | 0.306172 | −2.18% | 0.207136 | −0.02% | 89x |
|  | self R+B (python) | 0.266524 | −14.85% | 0.205956 | −0.59% | 25x |
|  | self/atten 0.692 | 0.251806 | −19.55% | 0.205653 | −0.74% | 26x |

**The placebo holds.** Every arm moves EDGE by 1–35% and FLAT by at most 2.5%, with
edge-over-flat ratios of 9× to 5176×. The correction acts where there is structure, which
is what a geometric rescale must do and what a colour-space or exposure artefact would not.

**One honest exception.** On `tweezers-cpl` the FLAT arm moves −1.8 to −2.5%, giving ratios
of only 12–18× — the weakest separation in the table. `tweezers-cpl` has by far the lowest
FLAT chroma (0.055 against 0.20 for the bee stacks), so a small absolute change reads as a
large relative one. I do not think it indicates a different mechanism, but it is the one
row where I would not lean on the placebo hard.

### 18.3 Red: the render domain confirms §16, independently and 6/6

| stack | emulation | shipped-py R | self-py R only | winner |
|---|---|---|---|---|
| coffee-bean | 83.0% | **−8.67%** | −8.17% | shipped |
| tweezers-cpl | 75.8% | **−26.19%** | −24.19% | shipped |
| bee-3-cpl | 97.9% | **−13.37%** | −10.73% | shipped |
| lavendar-cpl | 85.6% | **−20.39%** | −16.64% | shipped |
| couch-fibers-cpl | 87.8% | **−17.69%** | −16.65% | shipped |
| bee-2-cpl | 93.3% | **−15.52%** | −12.69% | shipped |

**The fixed shipped red coefficient beats the self-measured one on every stack, including
the four it was never fitted on.** This is measured on rendered pixels, by a statistic with
a built-in placebo, and it is a completely independent route to §16.1's arithmetic
conclusion. Rule 7 is satisfied in the direction that matters: the pictures and the number
agree, and they agree against the hypothesis I was commissioned to confirm.

### 18.4 Blue: the win, placebo-controlled

| stack | blue alone dEDGE | blue alone dFLAT | blue adds on top of red |
|---|---|---|---|
| coffee-bean | −2.43% | +0.01% | −2.35 pp |
| tweezers-cpl | −4.42% | −0.51% | −4.65 pp |
| bee-3-cpl | −2.56% | −0.02% | −2.37 pp |
| lavendar-cpl | −2.68% | −0.04% | −2.39 pp |
| couch-fibers-cpl | −0.93% | −0.01% | −0.64 pp |
| bee-2-cpl | −2.18% | −0.02% | −2.16 pp |

Blue **alone** removes 0.93–4.42% of edge chroma while moving the flat placebo by 0.01–0.51%
— a ratio of 9× to 166×. It is a real, structure-localised reduction that is shipping
uncorrected today, on every stack, and it costs one literal in `optics.rs` to collect.

Note also that these are the *attenuated* Python numbers. Applied in-pipeline at the mean
87.2% emulation recovery, the blue-only figures would be roughly 1.15× larger.

### 18.5 De-attenuation, confirmed a third time

`self/atten` beats plain `self` on **6 of 6** stacks (e.g. bee-2 −19.55% vs −14.85%,
bee-3 −16.65% vs −13.10%). Dividing the raw coefficient by the c4 recovery factor improves
the picture every time. That is a third independent line of evidence for §15, after the
dose ladder itself and the physical argument, and this one is in the render domain where a
reader can look at it.

### 18.6 Rule 7: I went and looked at the blue fringe

Section 19.1 asks for a change to `optics.rs` on the strength of a chroma statistic, so the
statistic does not get to stand unless someone has looked. `c9_look.py` crops the
worst-blue-fringe neighbourhood out of the outer field — chosen on the OFF arm by green
gradient and B−G swing, beyond 0.75 of the corner radius, so the choice of location is
independent of whether the correction helps — and writes off and blue-corrected side by
side at 6x with one shared exposure.

`C:\dev\strehl-out\BUILD-CHROMA\look\blue_tweezers-cpl.png`, crop at r = 0.78 of the
corner, where the applied `eps_b` = +165.3 ppm is worth 0.27 plane px.

The off panel shows exactly the signature lateral CA must produce: the specular highlights
along the tweezer edge carry distinct blue-cyan fringing on one side and orange-yellow on
the other, and the fibres at lower right are edged in cyan. In the corrected panel those
same highlights are visibly closer to neutral and the cyan edging is muted. Nothing else
about the crop changes.

| | mean chroma | B−G swing sd |
|---|---|---|
| off | 0.2407 | 0.1617 |
| blue-corrected | 0.2298 | **0.1373** |

A 15% reduction in the blue-minus-green swing, in a crop selected before the correction was
applied. **The picture and the number agree**, and they agree on the one recommendation
this report actually makes.

## 19. The exact Rust change I want

I have not touched a `.rs` file. This is the spec; route it to whoever owns `optics.rs`.
It is three independent changes and they can land separately, in the order given. **§19.1
is worth more than §19.2 and §19.3 combined.**

### 19.1 Set `eps_b`. This is the whole finding.

In `A7C2_FE100GM_2XTC_X4CPL` (`crates/strehl-core/src/optics.rs:320`):

```rust
eps_b: None,
```
becomes
```rust
eps_b: Some(174.4e-6),
```

- **Value:** `+174.4e-6`, the leave-one-out median of six de-attenuated per-stack
  measurements (§16.2). Range across stacks 101.3–222.7 ppm; the LOO median leaves 0.059 px
  mean corner residual against 0.363 px today.
- **Sign is positive, and red's is negative.** That opposition is not something I imposed —
  the two channels were fitted independently against green — and it is what lateral CA
  must do, since red and blue displace in opposite radial directions about green. Treat a
  same-sign pair as a bug.
- **Convention:** identical to `eps_r`. `compose` does `s = 1.0 + eps`, PULL,
  `dst(p) = src(s*p)` about the plane centre. My estimator's sign was pinned by a planted
  ladder (§13), not asserted. Note that shipping this inverted would make blue *worse*, in
  the same way `optics.rs` records the inverted red shipping once and costing 7.2%.
- **Confidence:** blue is my weaker arm and I want that on the record. Gate-ladder spread
  26–85% against red's ~5%; R² 0.32–0.88 against red's 0.77–0.99. But the *direction* is
  unambiguous, six of six, and the value need only be roughly right to collect most of the
  0.363 px — a coefficient anywhere in 140–200 ppm beats zero comfortably.
- Update `measured_from` to name this work and the six stacks.

### 19.2 Do NOT change `eps_r`

`−704.5e-6` is correct. My six de-attenuated measurements span −663.5 to −793.0 with a
median of −709.9, and the shipped value sits inside that. It leaves 0.071 px of mean
corner residual where the best possible per-stack number reaches 0.063 px. **The 7–26%
over-correction I reported in an earlier draft of this document was estimator attenuation,
not optics** (§15). If you have that draft, discard the red half of it.

### 19.3 Default-on, guarded by EXIF — and `optics.rs` is wrong about why it can't be

`optics.rs` states that the profile names a 2× teleconverter and that **"there is no way to
detect that from the frames."** That is not correct. It is true of what strehl currently
*reads*, not of what the ARW *contains*. Straight out of `coffee-bean`'s first frame:

```
Model      : ILCE-7CM2
LensModel  : FE 100mm F2.8 Macro GM OSS + 2X Teleconverter
LensSpec   : FE 200mm F5.6 Macro OSS
FocalLength: 200.0 mm
```

The teleconverter is named explicitly in `LensModel`, and `LensSpec` independently reports
the composite as a 200 mm f/5.6. So the safety property that blocks default-on is
available:

- Add `body: &str` and `lens: &str` match keys to `OpticalProfile`, set to `"ILCE-7CM2"`
  and `"FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"`.
- `active_profile()` selects a profile only on an **exact** match of both, and otherwise
  returns `Ok(None)` — the existing silent exact no-op. Unknown gear keeps today's
  behaviour exactly.
- `STREHL_FIX_CA` keeps its current meaning as a manual override, including `"0"`/`"off"`
  to force the correction off.

**The honest limit on this arm:** all 26 stacks in `D:\personal\macro` are the same body,
the same lens, the same teleconverter and the same 200 mm, so **the corpus contains no
counter-example and I cannot demonstrate the guard rejecting anything.** It is correct by
construction, not by test. If that is not good enough, ship §19.1 with the correction still
behind the env var and flip the default later — §19.1 does not depend on §19.3.

**The evidence for flipping the default** is §16.3: the 54.1% reverse-transfer figure that
justifies default-off is not reproduced. Leave-one-out over six stacks, a fixed coefficient
removes 93% of red and 84% of blue on a stack it was not fitted on.

### 19.4 What I am explicitly NOT asking for

**Do not build per-stack self-measurement into the renderer.** That was the commission and
the measurement declined it. Naive self-measurement is 3.6× worse than the fixed profile
for red (§16.1) because the estimator under-reads by 6–31% on exactly the low-structure
stacks that can least afford it. Making it safe would mean shipping the attenuation
correction of §15 — a planted-dose ladder *per render* — which is a large amount of machine
work and new failure surface to buy 0.008 px that nobody can see. The blue coefficient is
free by comparison.

**Do not add a translation term.** The shipped record is applied radial-only and should
stay that way; `optics.rs` already records that adding the fitted translation leaves 12×
the residual on `bee-3-cpl`. My own per-stack translations are 0.10–0.20 plane px, an order
of magnitude below M107's `(+0.629, −0.424)`, and my translation floor is ~0.1 px, so I can
say M107's translation is **not reproduced** but I cannot resolve a term of that size well
enough to argue about it.

**Do not make the correction depth-dependent** on the strength of §17. That is unproven in
both directions and my instruments for it failed their own controls.
## 20. The four things I was asked for, answered directly

**1. Estimate per-channel radial scale from the bracket itself, with null correction.**
Done, six stacks, `c1_lateral.py`, table in §14. ε_R −520 to −655 ppm raw, ε_B +92 to +180
ppm raw, each null-corrected against G1−G2 carried through the identical path, with the raw
statistic and the null in the same row. De-attenuated values in §15.

**2. Commission it — plant a known scale and require exact recovery; force it where no
aberration exists and require zero.** Done, `c0_lateral.py`, §13. Planted ladder slope
0.9959 with worst error 10.15 ppm over ±2000 ppm. Zero dose returns exactly zero, in both
the exact-copy and resample-at-zero forms. On-sky green null +12…+23 ppm. Both arms clean.
Commissioning also *found two bugs that would have silently poisoned the result*: the
phase-whitening transfer function (§12.1) and the low-structure tile domination (§12.2).

**3. Compare self-measured against the shipped profile in-sample and out-of-sample.**
Done, §16 arithmetically and §18.3 in the render domain. **The result is negative for the
commission's thesis.** Out-of-sample, the fixed shipped red coefficient leaves 0.082 px of
corner residual against naive self-measurement's 0.247 px, and beats it on rendered edge
chroma 6/6. The transfer objection does dissolve — leave-one-out transfer over six stacks
removes 93% of red and 84% of blue, and `optics.rs`'s 54.1% reverse-direction figure is not
reproduced — but it dissolves in favour of *a better fixed profile*, not self-measurement.

**4. Edge chroma with flat placebo, per stack, self vs shipped vs off.** Done, §18.2, six
stacks, six arms each, raw values beside every difference.

### 20.1 What I would tell the owner in one paragraph

The shipped lateral-CA correction is good and should be on. Its red coefficient is already
right — my draft claiming otherwise was my instrument under-reading, and I caught it with a
planted dose. Its blue coefficient is `None`, which means 0.36 px of blue fringing at the
frame corner is in every print, and setting one literal removes 84% of it. Do not build
per-bracket self-measurement: I built it, commissioned it, and it loses to the fixed number
it was supposed to replace, because the estimator is weakest on exactly the low-structure
scenes where you would most want to trust it.

### 20.2 Things I could not settle, logged

- **Focus dependence of ε** (§17). Unproven in both directions; two estimators, both failed
  their own planted-zero arm. A third attempt should compare matched-radius depth
  populations rather than regress on frame index.
- **M107's translation** `(+0.629, −0.424)` is not reproduced — mine are 0.10–0.20 plane px
  — but my translation floor is ~0.1 px, so this is "not reproduced", not "refuted".
- **Blue's radial profile is not a pure linear scale.** On `coffee-bean` the de-translated
  per-annulus ε_B falls monotonically from 242 ppm at r=451 to 164 ppm at r=1431. A single
  scale under-fits blue in a way it does not under-fit red. §19.1's coefficient is still a
  large improvement on zero, but a second-order blue term may be worth measuring later.
- **The EXIF guard of §19.3 is untested**, because all 26 corpus stacks are the same body,
  lens, teleconverter and focal length. There is no negative case available to me.
- **Python post-hoc emulation recovers only 87.2% of the in-pipeline effect** (§18.1), so
  every Python-arm magnitude in §18 is a lower bound.

### 20.3 Reproducing phase 2

```
python c0_lateral.py                        # commissioning, must pass first
python c1_lateral.py <stack> --frames N      # the measurement, per stack
python c4_attenuation.py --frames 12 --workers 8
python c2_compare.py
python c5_transfer.py
python c3_chroma.py <stack> ...              # renders, then the chroma table
python c8_table.py                           # emits the section 18 tables
python c6_focusdep.py ; python c7_focusdep2.py   # the withdrawn arm
```

Rules observed in phase 2: `tifffile` with a dtype assert, never PIL (1); attenuation
established by a planted dose ladder rather than argued from clustering (2, 5); raw
statistic beside every control in the same row throughout §14, §16 and §18 (3); the green
null explicitly rejected as a control for the focus axis because it cannot exhibit that
failure mode, and the claim withdrawn rather than defended (4); no triage rule of thumb —
the structure gate is swept as a ladder (5); no registration anywhere in the measurement
path, so rule 6 holds by construction; the render-domain table run as an independent check
on the arithmetic, and it agreed against my own hypothesis (7); `git add` of explicit paths
only, never `-A`, and every commit verified to contain zero `.rs` files (8).

---

## 21. Note for BUILD-ELECT, and a contamination check on my own numbers

Written at ORCH's request during phase 2, out of band. **I did not investigate the
election defect** — this is only what I already had, plus one check that is mine to run.

### 21.1 First, a correction: my intent line overstated what I have

**I have not seen blocky election seams.** I want that plain before anything else in this
section is used, because a second lane "independently confirming" something it did not
actually observe is worse than no confirmation at all.

What I have is not a visual observation. It is a **direct 1:1 read of the winner field
itself**, from phase 1 — and it says the field is *smooth*, with a tail.

The one crop I emitted in phase 2, `look/blue_tweezers-cpl.png`, is **6× nearest-neighbour
magnified** (`np.repeat`), so it is blocky by construction. It is not evidence of anything
about the election and must not be read as such.

### 21.2 What I actually have, and it may still save time

`b9_election.py`, phase 1, §5.4 of this report.

1. **Subject and render.** `lavendar-cpl`. The election index map was dumped by the binary
   itself via `--election-map`, on the **plane grid** (half sensor resolution, one election
   per 2×2 CFA quad), alongside a binned linear merge on the same grid. Not `--srgb`, no
   tone curve, no downsampling.
2. **It is the winner field, not an inference from the image.** I read the elected frame
   index per pixel directly. Values are the literal 0-based frame index.
3. **The artifact is still on disk** — `C:\dev\strehl-out\BUILD-CHROMA\render\lavendar-index.tif`,
   15.7 MB, plus `lavendar-cpl-merge.tif` on the matching grid. BUILD-ELECT can read both
   without re-rendering. **That is the part likely to save hours.**
4. **1:1 on linear data: yes.** Full plane-grid resolution, no resampling, no tone map. So
   this is the confirmation ORCH could not give from a 3× downsampled JPEG — *for the
   statistic below*, and only for it.
5. **What it found.** Roughness = mean absolute difference of the elected index to its four
   neighbours, deliberately a first difference so the real, wanted large-scale gradient
   across a tilted subject is not counted as roughness. Result: **the election field is
   smooth at the pixel scale**, and no rougher on the hairs than beside them. But there is
   a tail — **22% of ridge pixels above 0.5 frames, with excursions to 191 frames between
   adjacent pixels.**

**What I did NOT measure, and it is exactly what BUILD-ELECT needs.** I characterised the
*magnitude* of the excursions and never their *shape*. I do not know whether the
high-roughness pixels form extended straight or scalloped boundaries or are scattered
speckle. ORCH's argument — that straight and scalloped boundaries do not occur in defocus —
turns entirely on that shape, and my statistic is blind to it. A 4-neighbour first
difference would report a long straight seam and an isolated bad pixel identically.

So: **corroboration on magnitude and on 1:1 linear provenance, none on morphology.** The
excursions are real, they are large, and they are in a file BUILD-ELECT can open right now.
Whether they are seams is untested.

One caveat that cuts against over-reading this. In phase 1 I asked whether election jitter
drove the rainbow speckle and concluded it was a **minor** contributor: chroma rose only
**1.15×** between the smoothest and roughest roughness bins. Large excursions exist and are
rare; do not assume a large excursion count implies a large image-domain effect without
measuring the link.

### 21.3 Could a blocky election be contaminating MY numbers? No, and here is why

ORCH raised this and it deserved a real answer rather than a reassurance.

**The structural reason it cannot.** Two independent barriers.

1. **My coefficient never touches a merged image.** `c1_lateral.py` decodes each RAW frame
   and measures on its native CFA planes (`common.planes_of(cfa)`), comparing two channels
   *inside a single frame*. There is no merge, no election and no registration anywhere in
   the estimation path. The premise of the concern — "a lateral-CA estimate made on a
   merged image" — does not describe this instrument.
2. **Even on a merged image it would be common-mode.** Fact 1413: the election is computed
   from `green_luma` alone and **the one winning index is reused across all four CFA
   accumulators**. R and G at a given pixel therefore come from the *same* frame whatever
   that frame is, so an election error displaces both identically and cancels exactly in a
   channel difference. There is no channel-dependence in the focus measure for it to act
   through.

**The measured reason, because a structural argument is a claim about code** (`c10_blocky.py`):

| | mean R² of the radial model | mean Moran's I of the residual | significant at p<0.05 |
|---|---|---|---|
| R | **0.892** (0.976 and 0.988 on the two cleanest stacks) | +0.076 | 3/6 |
| B | 0.579 | +0.093 | 4/6 |
| **G2 (null)** | — | **+0.103** | 3/6 |

A blocky artifact cannot be fitted by a smooth one-parameter radial function, so
**R² = 0.988 on `coffee-bean` directly bounds how much blockiness can be hiding in the
measurement at ~1%.**

The residual that remains *is* mildly spatially clustered, and I am reporting that rather
than burying it — but **the G1−G2 null shows the same clustering or more** (mean I +0.103
against red's +0.076; on `coffee-bean`, G2 I = 0.275 against red's 0.199). G1 and G2 are the
same colour read from two sites in the same quad of the same frame: there is no lateral CA
between them and no chromatic content whatsoever. The clustering is therefore a property of
the tile geometry and the scene — some regions are simply harder to register, and
neighbouring tiles in them err together — and not of anything chromatic or electoral. It is
common-mode, matched by a null that has the same structure and no treatment (rule 3).

Moran's I is tested against a permutation null that reshuffles the residuals over the same
tile lattice, holding the residual distribution exactly fixed and destroying only the
spatial arrangement.

(G2's R² is low and is not comparable: its ε is ~0, so there is essentially no signal to
explain and the ratio is meaningless. Only the Moran column is meaningful for the null.)

**Conclusion: the CA coefficients in §14–§19 stand unchanged.** The check was worth running
and it changed nothing.
---

## 22. What was landed in `optics.rs`, and what was not

ORCH lifted the no-Rust restriction for `crates/strehl-core/src/optics.rs` only, having
checked it was clean in the working tree and last touched by `e8d74c7` (M107b, paused, no
live agent). Everything below is in that one file. **I have not verified this myself and
am not claiming it verified** — project rule; an independent checker is being sent.

### 22.1 The blast radius was checked before anything was written

Three facts made this safe to do while five other agents hold the tree:

- **`OpticalProfile` is constructed in exactly nine places and all nine are inside
  `optics.rs`** — the struct definition, the two shipped consts, and six test locals. Every
  test local uses `..A7C2_FE100GM_2XTC_X4CPL` struct-update syntax, so adding fields cannot
  break them.
- **`eps_b` and `Channel::Blue` appear in no other file in the workspace.** The one
  apparent hit outside `optics.rs` was a substring collision in `softgate.rs`.
- **`strehl-raw` depends on `strehl-core`, not the reverse.** That is why the guard takes
  plain scalars instead of a `CaptureIdentity`: naming that type here would invert the
  dependency graph. `strehl-cli` depends on both and is the correct place to bridge.

`cargo check --workspace --all-targets` is clean, so nothing downstream broke.

### 22.2 Changes

| # | Change | Note |
|---|---|---|
| 1 | `eps_b: None` → `Some(174.4e-6)` | LOO median of six de-attenuated stacks; 0.363 px → 0.059 px at the corner |
| 2 | `fit_b: Option<FitStats>` added | blue's evidence kept **separate** from red's, because merging them would average a strong arm with a weak one |
| 3 | `body_model` + `lens_type3` added | `"ILCE-7CM2"` / `33094`, the two fields `CaptureIdentity::same_gear_as` compares |
| 4 | `GearMatch` + `matches_gear` | three-valued, mirroring `same_gear_as`; `Unknown` never collapses to `Match` |
| 5 | `profile_for_capture` / `_env` | the default-on resolver |
| 6 | 54.1 % transfer figure corrected | old number **stated, not deleted** |
| 7 | "cannot be detected from the frames" corrected | it can; `LensType3` 33094 vs 32893 |
| 8 | Both `eps_b` caveats written into the field docs | weaker arm; possible second-order term |
| 9 | Four existing tests updated, nine added | see below |

**`active_profile()` is behaviourally untouched.** `merge.rs` documents it and
`align_cmd.rs:324` calls it to fail fast on a typo'd override; both keep working exactly as
before. The new function sits alongside rather than replacing it, so nothing live moved.

### 22.3 The two corrections, as they now read in the file

Neither old number was overwritten. The file states M107's figure, states mine, and says
which is which:

- **Transfer.** M107: 95.0 % one way, **54.1 %** the other, against a 60 % bar. Mine, LOO
  over six stacks and 1071 tiles: **93.7 % and 93.3 %** — symmetric. The file records this
  as **unreproduced, not refuted**, because nobody has re-run M107's instrument, and the
  likeliest reading — that 54.1 % was small-sample scatter — is an inference and is labelled
  as one.
- **Teleconverter detection.** The file asserted there was "no way to detect that from the
  frames". `LensModel` names it in plain text and `LensType3` reads 33094 composed against
  32893 bare. `strehl_raw::identity` already parsed both. The capability existed the whole
  time the comment denied it.

### 22.4 Tests: 24 optics tests pass, 432 in `strehl-core`

Four existing tests asserted `eps_b.is_none()` and had to change. One is worth recording,
because the fix improved the test:

`the_cfa_site_map_touches_only_the_red_gather` required that **exactly one** of the four CFA
gathers moved. That was a proxy. The invariant actually worth protecting is that **both
green gathers stay bitwise frozen** — green is what the focus measure and the election run
on, so a green that moved would change which frame wins and shift every merge number in the
corpus. Renamed to `the_cfa_site_map_leaves_both_greens_bitwise_frozen` and rewritten to
assert the real thing: greens frozen, red and blue move, count is 2.

Nine tests added. The three synthetic negatives are `the_guard_declines_the_bare_lens`,
`the_guard_declines_an_unreadable_file` (including both half-known cases), and
`the_guard_declines_a_different_body`.

**One test caught a real Rust subtlety in my own code.** I first pinned profile identity
with `std::ptr::eq`. It failed. `A7C2_FE100GM_2XTC_X4CPL_RADIAL` is a `const`, not a
`static`, so `&CONST` is const-promoted independently at each use site and two references
to the same constant need not compare equal by pointer. The behaviour was correct; the
assertion was meaningless. Replaced with value equality and the reason written into the
test, since the next person to reach for `ptr::eq` on these consts will hit it too.

### 22.5 What did NOT land: the default is not yet on

**The correction is still off in the render path, and I want that stated rather than
implied.** `profile_for_capture_env` exists, is tested and is ready, but nothing calls it.
The render path still calls `active_profile()`, which is env-only.

Turning it on is **one line**, in a file I am not authorised to touch —
`crates/strehl-cli/src/align_cmd.rs:1393`, inside `warp_frame_in_place`:

```rust
// now
let ca = strehl_core::optics::active_profile()?;

// wanted
let id = strehl_raw::identity::identity(&frame.path);
let ca = strehl_core::optics::profile_for_capture_env(
    id.model.as_deref(),
    id.lens_type3,
)?;
```

`frame.path` is already in scope (it is used in the geometry `bail!` twenty lines above),
and `strehl-cli` already depends on `strehl-raw`, so no `Cargo.toml` change is needed.

Two notes for whoever lands it. **`align_cmd.rs:324` should be left alone** — it validates a
typo'd override early, and that is still correct under default-on. And `identity()` opens
the file, so at `1393` it runs **once per frame**; it is documented as cheap (a few hundred
bytes, no pixel decode) and the existing `active_profile()` call is already per-frame, so
this is not a regression — but the identity is constant across a bracket and hoisting it to
the stack level would be strictly better.

### 22.6 The guard is correct by construction, not by experiment

Written into the code, not just here. **All 26 corpus stacks are the same body, same lens,
same teleconverter**, so the guard has never declined a real file and its negative path has
no natural test case.

The synthetic negatives are real as far as they go — the matcher takes plain scalars
precisely so a negative costs nothing to construct — but they exercise the **matcher**, not
the **parse**. What is untested is whether a genuine non-TC ARW yields
`lens_type3 == Some(32893)` rather than `None`. `strehl_raw::identity` has its own synthetic
bare-lens fixture, but no real file has been through the whole path.

The guard also cannot see the **Breakthrough X4 polariser** named in the profile's optical
path. A filter is invisible to EXIF and always will be. The guard bounds the risk; it does
not eliminate it, and the code says so.

**Capture ask, for the morning:** *a short bracket shot without the teleconverter.* It would
exercise the guard's negative path end to end and give the corpus its first non-TC optical
sample. I have **not** written this into `docs/captures-needed.md` — that file is ORCH's and
they said they are actively collecting asks into it tonight, so editing it is exactly the
collision I have avoided all night. Handing it over instead.

## 23. V-CA follow-up: the inverted status line, blue's arm, and aperture

Three items from V-CA's audit (`docs/research/V-ca.md`, `ec5ec9e`). Item 1 landed
at `48d3acb`; items 2 and 3 are below. **I did not verify any of this myself** —
project rule — so everything here is "what I ran", not "what passed".

### 23.1 Item 1 (P0) — reproduced, then fixed at the decision rather than the label

I reproduced the inversion before patching, at HEAD `e718c46`, and it was **not**
where V-CA said it was. `merge_cmd.rs:3842` had already been fixed by another
lane at `3a22fd2`. The identical defect was still live, verbatim, in
`crates/strehl-cli/examples/blend-render.rs:296-302` — which matters more than it
sounds, because `blend-render` **is the A/B harness**. The instrument that lies
about which arm is on was the one everybody measures with.

Actual stdout, `coffee-bean`, `--limit 2`:

```
##### ARM 1: STREHL_FIX_CA UNSET #####
lateral CA      : off (STREHL_FIX_CA unset)
##### ARM 2: STREHL_FIX_CA=off #####
lateral CA      : CORRECTING, profile "off"
```

Both rows are wrong, and I byte-proved the labels are backwards rather than
trusting the text. `--chunks` is not exposed on `blend-render`, so I carried a
re-run of the same arm as the determinism control:

| render | sha256 (first 16) |
| --- | --- |
| `br_unset` | `13C89646A9655F42` |
| `br_unset2` (control, same arm) | `13C89646A9655F42` — deterministic |
| `br_off` | `3DBAED9940C3C235` — differs |

The arm labelled `off` is the one that moved the pixels.

**The fix relocates the decision instead of inverting a second reconstruction.**
`optics.rs` gained `CaReason`, `CaDecision`, `resolve_for_capture` and
`resolve_for_capture_env`, and `profile_for_capture` became a one-line
*projection* of the resolver — so the reported profile and the applied profile
are now literally the same value, not two values that agree. `CaDecision`'s
`Display` takes the CORRECTING/off word from `self.profile` and **never** from
the reason, so a disagreement prints as visibly odd rather than confidently
wrong. After:

```
ARM 1 (unset): CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl" (gear matched "ILCE-7CM2" / lens 33094; default on)
ARM 2 (off):   off (operator asked for "off")
ARM 3 (named): CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl" (operator asked for "a7c2-fe100gm-2xtc-x4cpl")
```

Pixels are untouched by the log fix: `fx_unset == br_unset` and `fx_off ==
br_off`, byte-identical.

**Stating which A/B this was, per the cross-build rule.** The three-row hash
table above is a **same-binary** A/B — one `blend-render` binary, three env
settings — so the cross-build hazard does not apply to it. The `fx_* == br_*`
identity immediately above **is** cross-build (pre-fix vs post-fix binary), a
category the project holds void unless restricted to green, and I did not label
it as such when I first reported it. It survives anyway, for a reason worth
spelling out rather than assuming: the cross-build hazard *injects spurious
differences* (red moving up to 3902 DN), and no mechanism that injects
differences can manufacture byte-identity. The null is therefore robust in the
one direction that matters, and is itself evidence the hazard was absent for
this pair. The control against the opposite failure — a stale binary making
identity trivially true, which is exactly the mtime trap recorded above — is
that the post-fix **stdout demonstrably changed** (new reason strings), proving
the binary rebuilt. Both renders came from genuinely different binaries.

Three tests added where there were zero, and **I commissioned them** rather than
trusting green: `c11_commission_status.py` plants both directions of the original
inversion and requires RED. 2/2 caught. `cargo test -p strehl-core --lib optics`
→ 27 passed.

> **A trap worth recording.** The first commissioning run went green *after*
> restore for the wrong reason. `shutil.copy2` preserves mtime, so a restored
> file looked **older** than the artifact cargo had just built from the mutated
> source; cargo skipped the rebuild and re-ran the mutated binary against
> restored source. The tell was the failure text quoting a string that provably
> no longer existed in the file. Fixed with `os.utime(path, None)` after every
> restore. This generalises to any mtime-based build system.

### 23.2 Item 2 (a) — **REFUTED**. `eps_b` is signal, not noise.

ORCH asked me to settle a confound in their own numbers: blue's radial (0.039)
and tangential (0.030) are both ≈2.6× green's, they scale *together*, and a
radial warp cannot raise the tangential component — so perhaps blue's estimator
is simply noisier and the *ratio* is the right normalised statistic.

The prescribed test is the right one and I ran it exactly: **split the tiles in
half at random, fit independently, and let the half-to-half disagreement BE the
noise floor.** 400 random splits per stack, robust IRLS fit, green (G1–G2)
carried as the null on the same tiles.

| stack | ch | n | eps ppm | noise ppm | \|eps\|/noise |
| --- | --- | --- | --- | --- | --- |
| bee-2-cpl | R | 174 | 518.4 | 17.1 | 30.3 |
| bee-2-cpl | B | 174 | −144.2 | 13.4 | **10.8** |
| bee-2-cpl | G2 | 174 | −30.0 | 9.2 | 3.3 ← null |
| bee-3-cpl | B | 162 | −174.8 | 17.6 | **9.9** |
| bee-3-cpl | G2 | 162 | −19.0 | 6.0 | 3.2 ← null |
| coffee-bean | B | 209 | −182.8 | 4.9 | **37.0** |
| coffee-bean | G2 | 209 | −2.4 | 0.5 | 4.6 ← null |
| couch-fibers-cpl | B | 246 | −94.3 | 3.9 | **24.3** |
| couch-fibers-cpl | G2 | 246 | −2.6 | 2.0 | 1.3 ← null |
| lavendar-cpl | B | 103 | −148.9 | 20.8 | **7.2** |
| lavendar-cpl | G2 | 103 | −5.9 | 4.1 | 1.4 ← null |
| tweezers-cpl | B | 177 | −169.1 | 5.3 | **32.0** |
| tweezers-cpl | G2 | 177 | −3.8 | 0.6 | 6.2 ← null |

Blue stands **7.2–37.0** of its own error bars from zero, on all six stacks, with
**the same sign every time** (−94 to −183 ppm). The green null on the identical
tiles scores 1.3–6.2. Blue is not fitting noise.

**ORCH's confound resolves in ORCH's favour on the mechanism and against them on
the conclusion.** They were right that blue's per-tile radial and tangential rms
scale together and that this is a noise-scale effect — blue has less texture in
these scenes. But that is a statement about *per-tile scatter*, and `eps` is
fitted from the systematic radial component, which survives averaging while the
tangential does not. A noisier estimator gets a wider error bar, and I measured
the error bar. Blue clears it by a factor of 7 at worst.

So the fix is **not** a per-channel skip guard and **not** a coefficient repair.
There is nothing here to repair.

### 23.3 Item 2 (b) — the second resample is **CONFIRMED to exist**, and it is not mine

Counting resamples on a blue pixel, from the code:

1. the alignment gather — CA is *composed into* this transform, so it changes an
   existing resample's phase and does not add one;
2. `image_out.rs:956-957`, `develop_binned` — a **second** Keys resample, red by
   `(+0.25,+0.25)` and blue by `(−0.25,−0.25)`, for CFA co-siting.

**Green is not resampled here at all** — `image_out.rs:1293` calls green "the
null: it is not resampled". So green takes one resample and R/B take two, the
second at phase 0.25, which is the "large phase" ORCH's hypothesis required.

At f=0.35 the co-site costs 0.8254 per axis and **0.6813 on both** — 31.9% of
blue's amplitude, before CA is considered at all.

**BUILD-SHARP reached this independently and it is already routed** (`049589f`,
`ORCH-veiling.md`). I am not claiming it and not acting on it. What I can add is
an arithmetic cross-check from a different direction: their figures are 69%
retained for green and 47% for R/B; my co-site-only figure is 0.6813, and
**0.69 × 0.6813 = 0.470**. Two lanes, different routes, agreeing to three
figures on the composition.

**But it does not explain the 9.36%,** and I want that stated plainly: the
co-site runs in *both* CA arms, so it cancels in any CA-on-minus-CA-off
difference. What it does do is attenuate R and B but not G, which biases every
blue-vs-green HF comparison in the corpus — including `caprice.py`'s.

### 23.4 What actually explains the 9.36%: BUILD-SHARP priced the wrong displacement

BUILD-SHARP's refutation prices blue's cost at a single **0.039 px**. The
correction does not apply 0.039 px. It applies `eps_b · r` — **zero on axis and
0.368 plane px at the corner**:

| field r | r plane px | blue shift px | MTF f=.35 | amp loss |
| --- | --- | --- | --- | --- |
| 0.00 | 0 | 0.0000 | 1.0000 | 0.00% |
| 0.20 | 422 | 0.0737 | 0.9809 | 1.91% |
| 0.40 | 845 | 0.1473 | 0.9299 | 7.01% |
| 0.60 | 1267 | 0.2210 | 0.8573 | 14.27% |
| 1.00 | 2112 | 0.3683 | 0.6998 | 30.02% |

Losing 9.36% **energy** needs 0.1199 px = 0.33 of the corner radius; 9.36%
**amplitude** needs 0.1731 px = 0.47 of the corner. Both sit squarely inside the
field. The 9.36% is not anomalous and needs no extra mechanism — it is the
correction doing what it is designed to do, at the magnitude it actually applies.

My kernel is commissioned against two independent anchors before I use it:
`restore.rs:573`'s recorded 0.9402 / 0.7425 / 0.6251 all **MATCH**, and
BUILD-SHARP's own "0.1731 px at f=0.35" reproduces to four decimals.

> **A correction to the brief.** Those three constants are quoted in the brief as
> f = 0.25 / **0.35** / 0.50. `restore.rs:573` records the middle one at
> **f = 0.40**. My first run flagged a MISMATCH at 0.35 (0.8211 vs 0.7425) while
> matching exactly at 0.25 and 0.50 — the signature of a mislabelled abscissa,
> not a wrong kernel. Nothing downstream depended on it, but the label is wrong
> wherever it is repeated.

**The honest limit on this, which I did not close.** Because CA is composed into
the alignment gather, the cost is `MTF(φ+s) − MTF(φ)`, not `MTF(s)`. If the
elected frames' alignment phases were uniform on [0,1) that difference would be
**identically zero** — shifting a uniform distribution returns a uniform
distribution, and I computed that column as 0.00% at every radius as a structural
control. The reference frame is exactly phase 0 so the true distribution is not
uniform and the cost is not zero, but **I did not measure the distribution**.
The table above is therefore an **upper bound, not a prediction**. Closing it
means histogramming the per-pixel elected-frame phase, which is BUILD-HALO's
file, not mine.

**Verdict — (a) REFUTED** (blue's coefficient is real signal at 7–37σ, on all six
stacks, one sign). **(b) CONFIRMED as a mechanism that exists** — blue really is
resampled twice, green once — **but REFUTED as the explanation for the
differential**, since it is common to both arms. The 9.36% is explained instead
by BUILD-SHARP having priced a radially-varying shift at a single small value.
**No code change is recommended for blue.**

I also want the weak instrument flagged rather than leaned on: `caprice.py`
cannot distinguish "removed a fringe" from "blurred the channel", and my
conclusion deliberately does not rest on its 9.36%. It rests on the split-half,
which is a different instrument with its own null.

### 23.5 Item 3 (P2) — record the aperture, do **not** gate on it

The corpus does not span aperture the way the brief assumed. Reading the ARWs of
the six stacks the blue arm was fitted on: **five at f/5.6, one at f/8**, all at
200 mm effective. No f/11. A correlation across six points with 5-vs-1 grouping
is not a measurement, and I have not reported one as if it were.

But those six do contain one clean datum. The two largest per-stack `eps_r` are
**651.9 ppm (couch-fibers-cpl, f/5.6)** and **650.7 ppm (coffee-bean, f/8)** —
**1.2 ppm apart, 0.2%, across a full stop** — while the spread among the five
stacks that *share* f/5.6 is 500.9–651.9 ppm, or 151 ppm. Subject-to-subject
variation exceeds the only aperture difference available by two orders of
magnitude.

So: **the comment is not wrong, but the response to it was.** `measured_at:
None` was a recording failure, not a modelling one. I set it to what was actually
measured and wrote the reasoning — including the n=1-at-f/8 and nothing-at-f/11
limitation — into the code, and deliberately did **not** make the guard decline
on aperture, because declining would switch off a correction that measurably
works for a difference this corpus cannot detect.

`cargo test -p strehl-core --lib optics` → 27 passed, 0 failed.

### 23.6 Not done, and asks

- **The render-domain freeze test** on V-CA's `20D895F2…` / `4CFA8F25…` is still
  not written. It is worth more than the unit tests and I did not get to it.
- **`merge_cmd.rs` still has its own `ca_status_line`** (behaviourally correct
  since `3a22fd2`). There are now two implementations that can drift. It should
  call `resolve_for_capture_env`; I did not touch it because the file is dirty
  with another lane's work.
- **The elected-frame phase distribution** is unmeasured, which is what makes
  §23.4's table a bound rather than a number. BUILD-HALO's files.
- **Captures wanted:** a short bracket **without the teleconverter** (exercises
  the guard's negative path, which has never once declined on a real file), and
  **an f/11 bracket of an already-shot subject** (the aperture gap above).


## 24. ORCH's `foam` corroboration — **declined, and then refuted on magnitude**

ORCH offered a fourth reading in support of §4.4's blue radial term and asked me
to retire it if I judged the confounds fatal. I judge them fatal, but not for the
reason offered: the direction agreement is real and it is worth nothing, because
the magnitudes are two orders of magnitude apart.

### 24.1 My instrument declines `foam` outright

| stack | tiles ≤2 px | track_res med | max | confident points |
| --- | --- | --- | --- | --- |
| **foam** | **0/54** | **9.00** | 28.00 | **0** ← declined |
| lavendar-cpl | 48/54 | 0.00 | 9.00 | 1492 |
| coffee-bean | 52/54 | 0.00 | 8.50 | 6155 |
| bee-2-cpl | 26/54 | 4.50 | 14.00 | 789 |
| couch-fibers-cpl | 3/54 | 8.00 | 13.00 | 297 |

Not a marginal decline and **not drift**. On `coffee-bean` the per-tile frame
shifts are mostly exactly zero with rare outliers; on `foam` *every* tile-frame
shift is a large random value (±30–90 px) with no structure. Foam's self-similar
bubble texture gives the per-tile matcher no unique correlation peak, so it locks
a different match in every frame.

**I did not loosen the gate to produce a number.** A randomly-tracked tile still
has a maximum along the frame axis, and a parabola fitted to it returns a
confident-looking per-channel offset computed from different scene content in
each frame. That is exactly the failure the original brief made a mandatory
negative control — an instrument reporting a confident offset where there is
none. The gate firing *is* that control working, so this is the instrument
passing, not failing.

### 24.2 What §4.4 actually predicts for their statistic — **103–160× too small**

This is answerable without `foam`, and it is the useful half.

The chain uses the dose-response I **measured** in §5 rather than a
blur-to-edge-colour formula I would have to invent. §5's forward arms give
`bg_sd` 0.0761 at 1× dose and 0.0871 at 10×, so one full dose of the measured
axial offset moves edge chroma by **1.61%**. §4.4's radial component is 0.25–0.34
frames against intercepts of 0.48/0.30, so the radial part is **0.34–0.53 of one
dose**.

| | centre→corner blue edge-colour elevation |
| --- | --- |
| **predicted from §4.4** | **0.55% – 0.85%** |
| **ORCH observed** | **87.8%** (0.0672 → 0.1262) |
| ratio | **103× – 160×** |

So §4.4's radial term cannot be the mechanism. And the direction agreement
carries no evidential weight against a gap this size: a two-sided quantity agrees
in direction half the time by chance.

> **A wrong route I ran and discarded, recorded because it is seductive.** Going
> directly from 0.30 frames → σ ≈ 0.148 px → edge colour gives ~3–6%, which is
> the same order as their 5.9-point elevation and would have looked like
> agreement. It is wrong. It assumes edge chroma is *produced by* the channel
> blur, whereas §5's forward arm measured that a full σ = 0.369 px blue blur
> moves the statistic by only ~1.6% — edge chroma here is dominated by sources
> that are not axial CA. I nearly reported a confirmation from arithmetic that
> ignored my own measurement.

### 24.3 A duller explanation, entirely inside my lane, that needs no axial term

Both of ORCH's blue observations follow from the shipped profile alone:

- corner displacement applied: red `704.5 ppm × 2112 px` = **1.488 px**; blue
  `174.4 ppm × 2112 px` = **0.368 px**; ratio **4.04×**.
- ORCH sees red 0.758× (24.2% of corner edge colour removed) and blue 0.988×
  (1.2% removed).

Their observation 1 — "lateral correction barely touches blue at the corner" — is
not a puzzle. Blue's correction is 4× smaller than red's **by construction**. And
because it removes so little, most of blue's *native radial* edge colour survives
it, which is their observation 2: a radially elevated blue residual after
correction, with no axial term anywhere in the story.

Note this is a statement about the residual, not a retraction of `eps_b`. §23.2's
split-half puts `eps_b` at 7.2–37.0σ on six stacks with one consistent sign; it
is real and it works. It is simply *small*, and a small correction leaves a large
residual.

### 24.4 Verdict

**NOT CORROBORATING — retire it.** My instrument cannot measure `foam` at all, so
there is no fourth reading; and the reading that exists is 103–160× larger than
§4.4 predicts, so the excess is ORCH's own named confounds (clipping at 0.76%
blown pixels, corner demosaic error, genuine thin-film iridescence) and not a
shared mechanism. §4.4 stands exactly where it was — real, under-powered, three
stacks, **not** to be built on — and it has not gained field coverage tonight.


## 25. `foam`'s corner blue: **clipping**, and the "radial" framing was never radial

ORCH asked one narrow product question — can the clipping confound be separated
from demosaic error and iridescence, because clipping is the only one of the
three that is a defect this tool could be fixing and could be corrupting other
subjects silently. Answer: **yes, and it is clipping.**

### 25.1 A false green I produced first, and why it looked like a pass

My first gate thresholded on fractions of 65535. The master's maximum DN is
**52239**, so every threshold sat *above the image maximum* and the gate removed
**zero** pixels on all eight rows. The script then printed "the elevation
survives removal of every near-clip pixel". Two controls had already fired and
the verdict logic simply did not read them: an identical kept-count on every row,
and a matched-count random control reporting **sd 0.000 over 20 trials**. v2
asserts that the gate removes a non-zero count and that the random control's sd
is non-zero, and the v1 script is deleted rather than kept.

This is the same lesson from the other end: I had a working control and drew a
conclusion without looking at it.

### 25.2 There is no clipping *plateau* — which does not acquit clipping

No pile-up at the top (`>=0.999*max` is 0.0000% in every channel) and the
per-channel maxima are far apart (R 42213, G 38921, B 52239). p99 is ~9,400
against a max of 52,239: a long thin highlight tail, the opposite of a clipped
histogram. But ORCH's 0.76% blown is a **raw/scene** statistic, and raw clipping
happens before a *monotonic* tone curve, which maps it to high-but-unclipped
master values. So the gate has to be defined by **percentile of this master**,
not by an absolute ceiling.

### 25.3 The elevation is carried entirely by the brightest 0.76%

| drop top | DN | dilate | edges removed | centre | corner | corner/centre |
| --- | --- | --- | --- | --- | --- | --- |
| — (baseline) | — | — | 0 | 0.0672 | 0.1262 | **1.878** |
| 0.76% | 10438 | 0 | 14,765 | 0.0671 | 0.0692 | **1.031** |
| 0.76% | 10438 | 3 | 19,070 | 0.0670 | 0.0709 | 1.058 |
| 5% | 7293 | 3 | 41,231 | 0.0676 | 0.0781 | 1.156 |
| 25% | 4963 | 3 | 72,593 | 0.0783 | 0.0929 | 1.185 |

Removing ORCH's own 0.76% collapses 1.878 → **1.031**, i.e. **96% of the
elevation is gone**. Matched-count random removal leaves it intact at
**1.856 ± 0.088** — the level gate stands **7.6 sd** from the size-matched
control, so the change is attributable to level and not to sample size.

### 25.4 It was never radial — it is composition

| band | edge px | hot (top 0.76%) | hot frac | \|B−G\|/G **hot** | \|B−G\|/G **cool** |
| --- | --- | --- | --- | --- | --- |
| 0 (centre) | 2,369 | 16 | **0.68%** | 0.0783 | 0.0671 |
| 3 | 18,659 | 1,199 | 6.43% | 0.0516 | 0.0649 |
| 5 (corner) | 17,027 | 8,853 | **51.99%** | 0.1788 | 0.0692 |

**The cool column is flat across the whole field** — 0.0671 at the centre against
0.0692 at the corner. The corner band is 52% bright highlights against the
centre's 0.68%, a 76× composition difference, and bright pixels carry high blue
colour *wherever they sit*. The radial signal was the radial distribution of
highlights, not a radial optical term.

**This eliminates the demosaic confound outright:** corner demosaic error would
still be radius-dependent at matched level, and at matched level there is no
radial trend left.

### 25.5 Clipping, not iridescence — two independent discriminators

Level-dependence alone does not name a cause, because foam's thin-film
iridescence lives on exactly the bright specular films the gate removed. These
separate them:

1. **Hue consistency.** Among the 14,765 hot edge pixels, `B−G` is positive on
   **88.9%** and `R−G` negative on 69.4% — one-sided blue-excess/red-deficit.
   Thin-film interference cycles hue with film thickness (ORCH's own note
   describes "orange, cyan and magenta" rims) and would populate both signs.
2. **Monotonicity in level.** `B/G` climbs **1.0257 → 1.2903 across all 9 decile
   steps**, a 25.8% divergence. A fixed white-balance gain makes `B/G` a
   *constant* multiple independent of level and cannot produce this; only a
   nonlinear channel-dependent effect at the top of the range can. Green's
   ceiling (38921) also sits well below blue's (52239).

Green runs out before blue, so `B/G` climbs with brightness and the brightest
pixels acquire a one-sided blue excess.

### 25.6 Verdict

**Clipping is the explanation.** By ORCH's own decision rule this is a
channel-asymmetric highlight-saturation defect and a build task, not a chroma
question — and because it is a function of level rather than of field position,
**it will affect any subject with blown specular highlights**, which is what
ORCH was worried about. It has nothing to do with lateral CA, and nothing here
touches §23.2's `eps_b` or revives §4.4.

