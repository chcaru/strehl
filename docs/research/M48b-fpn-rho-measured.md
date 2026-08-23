# M48b — the fixed-pattern fraction ρ, measured from darks

**Milestone:** M48b (follow-on to M48). **Date:** 2026-08-23.
**Question addressed:** SYNTHESIS question 142 — M46 obtained ρ = 0.3094 by
*fitting* it to a residual correlation; can it be *measured*?

Facts, disciplines and questions are numbered **locally from 1**. The
orchestrator renumbers on fold. Every claim is labelled MEASURED, DERIVED or
ARGUED.

Scripts: `experiments/m48-noise-floor/src/09-fpn-rho.py`,
`11-fpn-spectrum.py`, `12-rho-confrontation.py` (and `10-…-recheck.py`, which
exists for a defect disclosed in §6). Data in the sibling `data/`.
`D:\macro-dark-frames` was read and never written.

---

## 0. The answer, before the numbers

**Local fact 1 (ARGUED, then MEASURED in §3). The dark-frame ρ and M46's ρ are
not the same quantity, and no rescaling relates them.** The brief asked that
this be settled before any number is quoted, and it settles against
commensurability.

Writing `D` for dark-signal non-uniformity (a fixed *offset* spread, DN), `P`
for photo-response non-uniformity (a fractional *gain* spread), `R` for the
temporal read sigma and `S` for black-subtracted signal at gain `g`:

```
dark frame          var = R² + D²                        <- no photons at all
illuminated frame   var = g·S + R² + D² + (P·S)²

rho_dark = D² / (R² + D²)
rho_M46  = (D² + (P·S)²) / (g·S + R² + D² + (P·S)²)
```

A dark frame contains **no photon shot noise** (so `g·S` is absent from the
denominator) and **no PRNU at all** (so `(P·S)²` is absent from the numerator —
PRNU multiplies a signal that is not there). The two expressions coincide only
in the limit `S → 0`. **ρ is not a property of a sensor; it is a property of a
sensor at a signal level**, and quoting it without one is the same
metric-validity failure this project keeps finding: the arithmetic is right and
the column heading is wrong.

So this milestone does **not** deliver a measured replacement for 0.3094. It
delivers something else, and I think more useful: a measurement of `D`, a hard
bound on what `D` can contribute to any lit frame, and a demonstration that
question 142 **cannot be answered by darks** — which is itself the answer to
question 142.

---

## 1. ρ measured, per ISO

**Local fact 2 (MEASURED). ρ_dark on the green planes, all 11 ISOs, 20 frames
each (the owner's first two per set dropped).** Two independent estimators of
the fixed-pattern variance were computed and agree to 2%: a split-half
cross-covariance `Cov_pix(mean_A, mean_B)` between frames split by index parity
(primary — it carries no bias term because the halves' temporal noise is
independent), and a bias-corrected plug-in `Var_pix(mean) − V_temporal/T`
(cross-check). Their ratio ranged **0.9815–1.0246** across all sets.

| ISO | DSNU `D` (DN) | temporal `R` (DN) | **ρ_dark** | tile SEM | ρ hot-censored | G1−G2 |
|---|---|---|---|---|---|---|
| 50 | 0.3833 | 1.0087 | **0.12616** | 0.00034 | 0.12556 | 0.00095 |
| 100 | 0.3833 | 1.0073 | **0.12647** | 0.00038 | 0.12584 | 0.00106 |
| 200 | 0.3403 | 1.7854 | **0.03506** | 0.00020 | 0.02852 | 0.00945 |
| 250 | 0.4122 | 2.2192 | **0.03335** | 0.00015 | 0.02769 | 0.00774 |
| 400 | 0.3813 | 1.2334 | **0.08725** | 0.00018 | 0.08640 | 0.00097 |
| 500 | 0.4029 | 1.5026 | **0.06707** | 0.00023 | 0.06278 | 0.00643 |
| 640 | 0.3913 | 1.8547 | **0.04261** | 0.00023 | 0.03425 | 0.01204 |
| 800 | 0.4650 | 2.3004 | **0.03925** | 0.00021 | 0.03227 | 0.00946 |
| 1000 | 0.5075 | 2.8750 | **0.03022** | 0.00012 | 0.02180 | 0.01078 |
| 1600 | 0.7204 | 4.5053 | **0.02493** | 0.00013 | 0.01358 | 0.01579 |
| 2000 | 0.8655 | 5.6522 | **0.02291** | 0.00014 | 0.01231 | 0.01404 |

**ρ_dark is the fraction of a DARK frame's variance that is fixed-pattern.**
Its denominator is read noise plus dark-current shot, and nothing else. It is
*not* a fraction of an exposure's noise.

**Local fact 3 (MEASURED — my quoted error bar is the wrong one, and I am
reporting the right one against myself).** The tile SEM above is 0.0001–0.0004,
which would imply ρ is known to four decimals. It is not. The two green planes,
measured on the same frames by the same code, disagree by up to **0.01579** —
at ISO 1600 that is **63% of ρ itself**. G1 and G2 are different physical
photosites with genuinely different fixed patterns, so this is not sampling
error and no amount of pixels will reduce it. **The honest precision on ρ_dark
is ±30% at ISO ≥ 1000 and ~±1% at ISO ≤ 100**, dominated by systematics. A
spatial SEM computed over tiles of one plane measures the wrong thing, and I
would have published it had I not tabulated the second green.

**Local fact 4 (MEASURED). Roughly half the high-ISO fixed pattern is hot
pixels, which this project handles separately.** Censoring pixels above
`median + 5·MAD` of the mean map removes 0.036% of pixels at ISO 50 and 0.251%
at ISO 2000, and moves ρ by **0.5% at ISO 50 but 46% at ISO 1600**
(0.02493 → 0.01358). Since M29 treats static defects as a separate concern and
a hot-pixel map already exists (`experiments/m22-hot-pixels`), **the censored
column is the one that should be compared to any model that also censors**, and
the two columns must never be mixed.

---

## 2. Is ρ constant across ISO? No — but the interesting part is what *is*

**Local fact 5 (MEASURED). ρ_dark is decisively not constant: it spans
0.02291–0.12647, a factor of 5.52.** Against a single shared ρ weighted by the
tile SEMs, **χ² = 235,380 on 10 dof**. Even using the honest systematic error
bar of fact 3 (±30%), the ISO-50 and ISO-2000 values are 5.5σ apart. In the
shape of M48's read-noise test — is the variation larger than the measurement
precision? — the answer is *yes, by orders of magnitude*.

**Local fact 6 (MEASURED). ρ moves almost entirely because its denominator
moves, not its numerator.** Across the same 11 ISOs the temporal `R` spans
1.0087→5.6522 DN (**5.60×**) while the DSNU `D` spans 0.3403→0.8655 DN
(**2.54×**, CV 34.6%). ρ falls with ISO chiefly because read noise in DN grows
with gain while the fixed pattern nearly does not.

**Local fact 7 (DERIVED). The DSNU is mostly, but not entirely, a DN-domain
quantity.** If `D` were a fixed spread in *electrons* it would scale with gain,
which runs 0.229→4.579 DN/e⁻ over this range — a factor of **20**. Measured
growth is **2.26×**. If it were a fixed spread in *DN* (post-amplifier) it would
be flat — measured growth is not flat either. So `D` is dominated by a
DN-domain term with a smaller gain-dependent component, the same *shape* as
M48's temporal noise floor. **This is a structural echo, not the same
quantity**: M48's floor lives in the temporal variance, which by construction
excludes the fixed pattern, and this one lives in the spatial variance, which by
construction excludes the temporal. Their numerical similarity (0.51 DN
against ~0.38 DN at base ISO) is suggestive and is *not* evidence that they are
the same thing. I flag it as local question 3 rather than a finding.

**Consequence for the model (ARGUED).** A ρ that moves 5.5× across ISO is not a
scalar and must not enter a model as one. But fact 6 says the invariant
underneath it — `D`, in DN — very nearly *is* one. If ρ is ever needed, the
parameter to store is `D`, and ρ should be *computed* at the operating point
from `D`, `R`, `g` and `S`. Storing ρ itself bakes in an ISO and a signal level
invisibly.

---

## 3. The confrontation with M46's 0.3094: incommensurable, quantitatively

M46's ρ was solved on the `112MSDCF`/`113MSDCF` pair at **ISO 500**
(`M46-detail-metric-measured.md:98,159`), as
`FRC_flat/(1−FRC_flat)/n_eff = 0.7310/0.2690/8.784`.

My ρ_dark at the same ISO is **0.06707**. The naive ratio is **4.61×**. That
ratio is meaningless, and here is the arithmetic that shows why.

**Local fact 8 (MEASURED + DERIVED). The DSNU accounts for 0.12% of the
fixed-pattern variance M46's number requires, and 0.05% of the lit frame's
total variance.** At ISO 500, `g` = 1.1447 DN/e⁻, and the corpus median
black-subtracted green luma on `113MSDCF` is **271.0 DN** (MEASURED, script 10,
on those very frames). Then:

- shot variance `g·S` = **310.2 DN²**
- temporal read variance `R²` = **2.258 DN²**
- measured DSNU variance `D²` = **0.1623 DN²**
- so `D²` is **0.052%** of the lit frame's non-FPN variance.

For ρ = 0.3094 the total FPN variance must be `0.3094/0.6906 × (310.2+2.258)` =
**140.0 DN²**, i.e. an FPN sd of **11.82 DN**. The measured DSNU supplies
**0.1623 of 140.0 = 0.116%** of it. **Whatever M46 measured, at least 99.88% of
it is something a dark frame does not contain.**

**Local fact 9 (DERIVED). The residual implies a 4.36% signal-proportional
term, which is 4–15× a typical CMOS PRNU — so M46's ρ is probably not purely
PRNU either.** Solving `(P·S)² = 140.0 − 0.16` at S = 271 DN gives
`P·S` = 11.82 DN, i.e. **P = 4.36% of signal**. Published PRNU for CMOS imagers
is typically 0.3–1%. I cannot measure `P` from darks and do not claim a value;
I claim only that 4.36% is too large to be read as PRNU without further
evidence. M46's own P9 offers a candidate for the excess: it measured that the
"flat" ROI **has real content** (rule-10 detector reads 6.43), and residual
scene structure is perfectly common-mode between two captures of the same
subject — indistinguishable, by FRC alone, from a fixed sensor pattern.

**Local fact 10 (DERIVED — robustness). The conclusion does not depend on my
signal-level assumption, across three decades.** I used the frame-median
signal; M46's flat ROI may be darker. Recomputing the DSNU-only ρ at ISO 500:

| assumed flat-ROI signal | ρ from DSNU alone | factor below 0.3094 |
|---|---|---|
| 271 DN (frame median) | 0.000519 | 596× |
| 27.1 DN | 0.004854 | 64× |
| 2.71 DN (essentially black) | 0.02940 | 10.5× |

Even at a signal level of 2.7 DN — below which the frame is not an exposure at
all — the DSNU cannot reach a tenth of 0.3094. **The incommensurability is not
a matter of picking the right operating point.**

**Verdict (ARGUED): incommensurable, and the third of the brief's three options
is the right one.** M46's 0.3094 is not refuted by this work — nothing here
touches PRNU or scene structure, which is where its content lies. It is
*scoped*: it is a fraction of an illuminated flat ROI's variance at ISO 500 at
one signal level, and it should never be quoted as "this body's FPN fraction"
without those qualifiers. Question 142 asked whether ρ could be measured from
darks instead of fitted. **It cannot** — darks measure a different term.

---

## 4. The dark-frame caveat, applied to my own result

The brief asked me to apply my own discipline 326 to my own number. Doing so
substantially devalues it, which is the correct outcome.

**Local fact 11 (MEASURED/DERIVED). ρ_dark does not transfer to lit frames, and
loses two to three orders of magnitude on contact with light.** Evaluating the
DSNU-only ρ at each stack's own measured median signal:

| ISO | corpus median S | ρ at S = 0 | ρ from DSNU at that S | attenuation | S where ρ halves |
|---|---|---|---|---|---|
| 50 | 3253.5 DN | 0.12616 | **0.000197** | 641× | 5.09 DN |
| 500 | 271.0 DN | 0.06707 | **0.000519** | 129× | 2.11 DN |
| 1000 | 191.5 DN | 0.03022 | **0.000576** | 52× | 3.72 DN |

ρ_dark falls to half its zero-signal value by **2–5 DN** of black-subtracted
signal. M48 fact 25 measured that the 0.1st-percentile pixel of a real high-ISO
stack sits at **132 DN**, ~30–60× above that. **No pixel in this corpus is at a
signal level where the dark ρ is even approximately valid.**

**What would have to be true for it to transfer?** Only that the frame carries
no light: `g·S ≪ R²`, i.e. `S ≪ 2 DN` at ISO 500. There is no such regime in
macro photography. The dark ρ is valid for dark frames — bias/dark calibration,
hot-pixel mapping, sensor QA — and for nothing else in this pipeline.

**Local fact 12 (DERIVED — the one genuinely useful consequence). The shipped
noise model is right to omit DSNU entirely.** `PlaneNoise::variance` is
`g·S + (RN_e·g)²`, with no fixed-pattern term, and fact 8 measures the term it
omits at **0.05% of variance** at the working point — a **0.026%** error on
sigma. That is 20× smaller than the read-noise error I corrected in M48 and
~200× smaller than the model's own provenance uncertainty. This is a *positive*
result: an omission that was never justified is now measured to be immaterial,
for illuminated frames.

---

## 5. Is the fixed pattern white to Nyquist? Yes — independently confirmed

M46 fact 612 asserts the common-mode FPN is white to Nyquist, and it is
load-bearing: it is what kills the FRC 1/7 crossing and licenses several
censoring results. It was established on an illuminated pair. Darks test the
fixed pattern directly.

The estimator matters here and is the same trick as §1: the temporal noise
leaking into a mean image is *itself* white, so the spectrum of a single mean
image has a flat pedestal that would **manufacture the conclusion under test**.
The **ring-averaged cross-power of two disjoint half-means** has no such
pedestal, because the halves' temporal noise is independent.

**Local fact 13 (MEASURED). The fixed pattern is white to Nyquist to within
14%, at every one of the 11 ISOs.** Ring-averaged cross-power on a centred
2048² crop of G1, Hann-windowed: the log–log slope is **−0.041 to −0.127**
(mean −0.091) where white is 0, and the ratio of mean power at 0.40–0.50 cyc/px
to that at 0.05–0.15 cyc/px is **0.798–0.964** (mean 0.861) where white is 1.
**M46 fact 612 is confirmed by an independent route on independent data.**

**Local fact 14 (MEASURED). There is no banding on this body.** Decomposing the
fixed pattern into row, column and residual structure — every term a
cross-covariance between halves, so all are pedestal-free — gives a residual
(pixel-independent) share of **97.4%–100.5%** at every ISO, with row shares
between **−1.2% and +1.4%** and column shares between **+0.2% and +1.3%**. The
small negative values are what a true zero looks like under a covariance
estimator. CMOS fixed pattern is frequently part row/column banding, which would
*not* be white; on this sensor it is not present, which is *why* fact 13 holds.

**Refinement, not refutation (ARGUED).** The slope is consistently negative and
the high/low ratio consistently below 1, at all 11 ISOs — a ~14% roll-off toward
Nyquist that is too systematic to be noise. It is small enough that "white" is
the right modelling choice, but "white to within 14%, with a slight roll-off" is
the more precise statement, and anything that divides by FPN power at high
frequency should carry it.

---

## 6. What I got wrong

**Local fact 15 (my own defect, and it crashed).** Script 09 died with
`0xC0000005`. `rawpy`'s `raw_image_visible` returns a **view into libraw's
internal buffer**, freed when the context manager exits; I bound it inside the
`with` and used it outside. A use-after-free.

**The part that matters: script 08, already committed and folded as facts 25 and
28, contains the same defect in a quieter form.** It copies
`raw_image_visible` via `.astype()` (safe) but binds `raw_colors_visible`
without copying and indexes with it after the block closes. It did not crash —
the worst outcome, because its numbers were published.

Per rule 15 I did not modify script 08. `10-shot-dilution-recheck.py`
re-measures the same quantity with correct handling. **The results are
identical**: mean response shift 0.345% / 0.137% / 0.000%, p99 0.482% / 0.335% /
0.000%, median signal 191.5 / 271.0 / 3253.5 DN — every figure matching script
08 exactly. **Facts 25 and 28 stand.** The recheck also verifies an assumption
script 08 made silently: `color_desc` is `RGBG` and every 2×2 site has exactly
**2** greens.

**Local fact 16 (my own defect, caught by tabulating one extra column).** I
first wrote fact 2's error bar as the tile SEM, ~0.0002, and it is wrong by two
orders of magnitude (fact 3). The G1/G2 disagreement — free, since I was
already computing both planes — exposed it. **A precision estimated by
subdividing one measurement cannot see a systematic shared by that
measurement.**

---

## 7. Proposed disciplines (numbered locally from 1)

**Local discipline 1.** *A noise-fraction is a property of a sensor **at a
signal level**, and must be quoted with one.* ρ = 0.3094 and ρ = 0.0671 are both
correct for this body at ISO 500 and differ by 4.6× because one is at S = 271 DN
and the other at S = 0. A fraction whose denominator moves with exposure is not
a sensor constant, and storing it as one hides an operating point inside a
scalar.

**Local discipline 2.** *When an estimator's bias has the same shape as the
effect under test, use a two-sample cross-statistic instead of correcting the
bias.* Temporal noise leaking into a mean image is white, and the question was
whether the fixed pattern is white. A subtracted pedestal would have left the
answer resting on the accuracy of the subtraction; a cross-spectrum between
disjoint halves has no pedestal to subtract. Same trick removed the `V/T` bias
from the variance in §1.

**Local discipline 3.** *Estimate precision from a second independent
realisation, not from subdividing one.* Fact 16: tiles of one plane gave
±0.0002; the second green gave ±0.016. Only the latter can see a systematic that
the whole plane shares.

**Local discipline 4.** *A library object that hands back a view into a foreign
buffer must be copied at the boundary, and the copy must be visible in the
code.* `rawpy` does this for `raw_image_visible`, `raw_colors_visible`,
`black_level_per_channel` and more; `.astype()` copies and looks like a
conversion, plain assignment does not copy and looks identical. One of the two
crashed and one published numbers.

---

## 8. Open questions (numbered locally from 1)

**Local question 1.** **Can `P` (PRNU) be measured on this body at all?** It is
the term that actually carries M46's ρ, and darks cannot see it. The standard
method is a flat-field: two exposures of a uniformly lit surface at different
levels, differenced to remove FPN and ratioed to isolate it. The corpus has no
flat-field. **This is a capture request, and it is small** — a few frames of an
evenly lit blank card at two exposures, at ISO 500. It would convert M46's
fitted 0.3094 into a measured decomposition and settle whether the 4.36% of
fact 9 is PRNU or scene structure.

**Local question 2.** **Is M46's ρ contaminated by residual scene structure?**
M46's own P9 measured that the flat ROI has real content. A cheap discriminator
exists without new captures: FRC between two captures of *different* subjects at
the same ISO. Sensor FPN is common to those; scene structure is not. If the
correlation survives a subject change, it is the sensor; if it collapses, part
of 0.3094 is the coffee.

**Local question 3.** **Is the ~0.4 DN DSNU floor the same physical thing as
M48's ~0.51 DN temporal floor?** They are measured in orthogonal domains
(spatial vs temporal) and cannot be the same *statistic*, but they could share a
cause — an ADC/reference term that contributes both a per-read and a per-pixel
spread. Both sit near 14-bit quantisation's 0.289 DN. Distinguishing them needs
a bias-frame series at varying readout settings, which this corpus does not
have. **Do not conflate them in the meantime.**

**Local question 4.** The ~14% spectral roll-off toward Nyquist (fact 13) is
systematic across all 11 ISOs. Inter-pixel capacitive crosstalk is the usual
cause and would be a genuine sensor characterisation result. Worth naming only
if something downstream divides by FPN power at high frequency.

**Local question 5.** Fact 4 shows hot pixels are ~46% of the ISO-1600 fixed
pattern. Does the M22 map, applied first, change any FRC/censoring result that
currently attributes its behaviour to FPN? Cheap to test and it bears directly
on M46's censoring conclusions.

---

## 9. How to reproduce

```
python experiments/m48-noise-floor/src/09-fpn-rho.py          # ~7 min, 242 darks
python experiments/m48-noise-floor/src/11-fpn-spectrum.py     # ~7 min
python experiments/m48-noise-floor/src/12-rho-confrontation.py
python experiments/m48-noise-floor/src/10-shot-dilution-recheck.py
```

Outputs `data/fpn-rho.json`, `fpn-spectrum.json`, `rho-confrontation.json`,
`shot-dilution-recheck.json`. Black level is never subtracted — variance and
covariance are offset-invariant, so none of this depends on the 512 assumption.
No Rust source was changed by this milestone.
