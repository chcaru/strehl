# M88 — the optical ceiling, measured

**Verdict: fact 1149 is REFUTED. M88's own measurement of the cutoff is
UNIDENTIFIED, and the pre-registered model-form bar FAILED.**

Three separate findings, which should not be collapsed into one.

**1. Fact 1149's number is refuted by the corpus, not by M88.** Its
`f_c = 86.3 cy/mm` requires `p = 1`. Fact 1152 **excludes `p = 1` by
measurement**, bracketing `p` in `[1.31, 1.94]`. Recomputing gives
**`f_c` in [106, 135] cy/mm** at 550 nm by two independent routes that agree to
0.6%. The whole interval lies **above** sensor Nyquist, 97.66 cy/mm. Fact
1149's arithmetic is correct; its pupil assumption is not, and fact 1152
pre-dates this milestone's own pre-registration. M88 missed it and says so in
§5.3.

**2. Its clause (a) is therefore refuted outright.** "MTF at sensor Nyquist is
exactly zero" is false at the central wavelength across the entire measured
interval, not merely at the blue end.

**3. M88's own attempt to measure the cutoff returns UNIDENTIFIED, and the
one bar that could fire, fired against the model.** The corpus cannot measure
this: every usable edge in it is dominated by a blur that does not change with
aperture. That is a measured statement, not a shrug. The ISO-12233-style
instrument built here was validated to `+1.19% +/- 1.50%` on planted cutoffs
from 60 to 140 cy/mm, then pointed at the *same physical subject* photographed
at f/11 and at f/5.6. Diffraction says the f/11 edge must be **1.964x** wider.
It is **1.025x**.

Finding 3 is independent of finding 1 by construction: the pre-registered
Bar 3 is a *ratio* at two apertures and is free of both `m` and `p`, so the
pupil correction does not touch it. If anything the correction strengthens it —
a higher true cutoff means a smaller diffraction blur, and so an even more
dominant non-diffraction term.

---

## 1. What was under test

**DERIVED elsewhere (fact 1149).** `m = 2.762`, marked `N = 5.6`, assumed
pupil magnification `p = 1`, hence `N_eff = N(1 + m/p) = 21.07`; Airy diameter
`2.44 lambda N_eff = 28.3 um = 5.5 sensor px`; `f_c = 1/(lambda N_eff) =
86.3 cy/mm` at `lambda = 550 nm`; sensor Nyquist 97.66 cy/mm; binned-output
Nyquist 48.83 cy/mm. Conclusions drawn there: MTF at sensor Nyquist is exactly
zero, and the binned path discards real detail across 48.83-86.3 cy/mm.

**MEASURED (M88, arithmetic check).** The arithmetic is **correct**.
`5.6 x 3.762 = 21.0672`; `2.44 x 0.55e-3 mm x 21.0672 = 28.27 um = 5.522 px`;
`1/(0.55e-3 mm x 21.0672) = 86.30 cy/mm`; `1/(2 x 5.12 um) = 97.656 cy/mm`.
Nothing in fact 1149 fails on arithmetic. Its inputs and its wavelength
assumption are where it fails.

## 2. The instrument, and why it had to be new

**MEASURED (M88).** The corpus's existing spectral tool cannot test fact 1149.
M5's best lattice, the re-indexed green quincunx `GQ` at 7.2408 um pitch, has
an isotropic radial reach of `0.3536 cyc/px = 69.1 cy/mm`. That is **below**
86.3 cy/mm. The question fact 1149 poses was never answerable by the
instrument that produced the numbers fact 1149 leans on.

**MEASURED (M88).** M88 therefore built a slanted-edge SFR estimator that
operates directly on **one Bayer green sublattice with no demosaicing** —
no white balance, no colour matrix, no sharpening, no resampling anywhere in
the chain. Trap 2 is avoided rather than corrected for, so no interpolator
transfer function sits in the measurement band. Implementation is frozen in
`experiments/M88-optical-ceiling/src/m88lib.py`; the design was
pre-registered in that directory's `PREREGISTRATION.md` and committed before
any spatial-frequency quantity was computed from any real capture.

### 2.1 Trap 1, discharged by measurement rather than by argument

A single green sublattice samples at 10.24 um, Nyquist **48.83 cy/mm** —
*below* the frequency under test. Reporting "no energy above 48.83" from such
a lattice would be an instrument artifact. The slanted edge escapes this
because a straight edge makes the image a one-dimensional function of the
projected normal distance, which a slanted lattice samples at arbitrarily fine
phase; the lattice pitch limits only the sample count per bin.

**MEASURED (M88, control C1b).** Using the model-free detector alone — no
optical model, no fit — the instrument reports signal out to **91.1-93.8
cy/mm** on a planted 110 cy/mm cutoff and **109.4-114.6 cy/mm** on a planted
140 cy/mm cutoff. That is **2.35x** the sublattice's own naive Nyquist, and
above the 97.66 cy/mm sensor Nyquist. The instrument can see where it needed
to see.

### 2.2 The two repairs that made it work

**MEASURED (M88).** A per-line centroid of the gradient taken over a whole
line is dominated by far-field noise samples and biases the edge slope toward
zero: it recovered **1.21 deg from a planted 1.98 deg**, residual sd 2.37 px.
That destroys the supersampling the whole method depends on. A two-stage
estimator — argmax of a smoothed gradient, then three windowed-centroid
refinements — recovers **2.0003 deg**, residual sd 0.0496 px, on the identical
input. Any reimplementation of this method must do something equivalent.

**MEASURED (M88).** Truncating the ESF inflates every MTF value, because the
Airy line-spread tail decays as `1/x^2`. The bias measured **+3.4% at a
+/-96 um half-width, +1.6% at +/-192 um, +0.83% at +/-384 um** — halving as
the half-width doubles, exactly as the tail predicts. It is flat in frequency
over 10-78 cy/mm, so a free amplitude in the fit absorbs it.

## 3. Controls

All controls ran on synthetic plants carrying no information from any real
capture, and their results were frozen into the pre-registration before the
real data was touched. Full output in `out/s03_controls.json`,
`out/s04_instrument_spec.json`, `out/s09_deramp_control.json`.

| control | what it plants | result | verdict |
| --- | --- | --- | --- |
| C1 | known cutoff, 4 values x 10 seeds | pooled error **+1.19%**, sd **1.50%**, range -0.24% to +4.97% | **PASS** |
| C1b | cutoffs above the sublattice Nyquist | model-free bound reaches **114.6 cy/mm** from a 48.83 cy/mm lattice | **PASS** |
| C2 | same plant on G1/G2, horizontal/vertical | spread **1.026x**; a factor-2 axis error reads 2.00x | **PASS** |
| C3 | defocus **disc** against a Gaussian model | error is **negative**: -14.4% and -31.2% at a 16 um disc | **PASS, with a declared limitation** |
| C4 | flat field, no edge | instrument **refused** ("74 empty ESF bins") | **PASS** |
| C5 | sample values permuted, geometry kept | bound `nan` | **PASS** |
| C6 | 30 um and 60 um defocus discs | `sigma_fit` 9.4 and 17.6 um, caught by the gate | **PASS** |
| R1 | wing ramps matched to the real ESF | cutoff still recovered to **+0.78%** | **PASS** |
| R2 | clean edge, repair enabled | repair is a **no-op** | **PASS** |
| R3 | ramps with no edge at all | bound `nan` | **PASS** |

**MEASURED (M88, C1 calibration).**

| planted `f_c` | recovered mean | sd | bias |
| ---: | ---: | ---: | ---: |
| 60.0 | 60.203 | 0.212 | +0.34% |
| 86.3 | 86.456 | 0.271 | +0.18% |
| 110.0 | 111.769 | 1.255 | +1.61% |
| 140.0 | 143.689 | 2.710 | +2.63% |

**MEASURED (M88, C3).** Unmodelled real blur biases the fitted cutoff
**downward**, never upward, and a 16 um defocus disc is **not** caught by the
`sigma_fit < 3 um` validity gate (it reported `sigma_fit = 2.45 um` while the
cutoff error was -31%). This is declared, not hidden: it means a *low*
measurement is ambiguous between real and contaminated, while a *high*
measurement would have been robust.

**MEASURED (M88, R1 — a hypothesis of M88's own, killed by its own control).**
The real ESF was found to carry different linear ramps on its two wings: on
119MSDCF ROI A1 the dark wing falls 527 DN over 154 um and the bright wing
climbs 910 DN over 169 um, together 32% of the edge contrast. M88 hypothesised
this was corrupting the measurement, implemented a per-wing deramp, and then
planted ramps of exactly that magnitude to check. **The unrepaired instrument
recovered a planted 86.3 cy/mm as 86.97 cy/mm (+0.78%) anyway.** The ramps are
not the problem. The repair is retained because the real ESF demonstrably needs
it, but it changes nothing, and the low real-capture response is real.

## 4. The measurement

Twelve ROIs were frozen by geometry alone — slant, contrast and straightness
residual — across three stacks, and every frame of every stack was measured.
Best focus per ROI is the argmax of a **3-frame moving average** of
`MTF(40 cy/mm)`, not a bare argmax (rule 4).

### 4.1 The pre-registered gate fails everywhere

**MEASURED (M88).** Twenty-two ROI-plane results were produced, from 11 ROIs
on two green sublattices; a twelfth ROI (119MSDCF B1) failed the edge fit on
every frame and yielded nothing. **All 22 fail the pre-registered validity
gate.** Twenty-one fail condition 1, `sigma_fit < 3.0 um`, with measured values
of **6.3 to 29.1 um**. The twenty-second fails condition 4, `amp in
[0.8, 1.25]`: 119MSDCF A4 on G2 ran to the corner of the parameter box with
`sigma = 0.000`, `f_c = 400.00` and `amp = 2.000`, all three pinned at their
bounds simultaneously. Its apparent `MTF(40) = 0.8809` is a degenerate fit, not
a sharp edge, and the pre-registered gate rejected it on a condition written
down before the data was seen — condition 4 exists precisely to catch this.

The fitted cutoff is therefore not reported as a cutoff anywhere. At this much
unmodelled blur the diffraction term and the nuisance blur trade against each
other and neither is identified.

| stack | aperture | frames | best-focus `sigma_fit` | `MTF(40 cy/mm)` |
| --- | --- | ---: | --- | --- |
| `119MSDCF` | f/5.6 wide open | 33 | 6.3 to 8.2 um | 0.061 to 0.134 |
| `109MSDCF` | f/11 | 22 | 8.8 to 29.1 um | 0.009 to 0.065 |
| `tweezers-cpl` | f/5.6 wide open | 100 | 13.4 to 26.8 um | 0.013 to 0.115 |

Ranges exclude the single degenerate fit. All three stacks are 200 mm with
`MaxApertureValue = 5.6`, confirming the 2x teleconverter is fitted throughout
and that both f/5.6 stacks are wide open.

### 4.2 The model-free result, which needs no fit at all

The 10-90% rise distance of the measured edge-spread function is a pure
measurement: no model, no fit, no cutoff/blur degeneracy.

**MEASURED (M88).** Through this same instrument, a **diffraction-limited**
edge gives:

| planted `f_c` | 10-90% rise |
| ---: | ---: |
| 43.9 cy/mm (f/11 under fact 1149) | 23.98 um |
| 53.9 cy/mm (M5's f/11 knee) | 20.40 um |
| 86.3 cy/mm (fact 1149) | 14.11 um |
| 106.0 cy/mm (M5's bound at f/5.6) | 12.01 um |

**MEASURED (M88).** The real captures, at each ROI's own best focus:

| stack | aperture | rise per ROI | median |
| --- | --- | --- | ---: |
| `119MSDCF` | f/5.6 | 31.75, 31.66, 32.96, 27.83 um | **31.70 um** |
| `109MSDCF` | f/11 | 42.43, 32.34, 32.65, 31.56 um | **32.49 um** |

Both stacks are at genuine best focus inside their brackets. `119MSDCF` ROI A1
runs `MTF(40)` 0.034 -> 0.122 -> **0.124** -> 0.112 -> 0.053 across frames
0/4/6/8/10, a clean interior peak. `109MSDCF` ROI C2 runs a rise of
44.21 -> 35.54 -> **32.34** -> 35.90 -> 42.60 um across frames 0/4/8/10/14, a
clean interior minimum. Trap 5 is discharged: this is not a defocus artifact.

**MEASURED (M88), and this is the strongest form of that discharge.** The
choice of best-focus frame does not matter. Sweeping 119MSDCF ROI A1 across
its entire best-focus plateau, frames 3 through 9, the rise stays within
**30.56 to 34.18 um**:

| frame | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rise (um) | 34.18 | 30.56 | 31.24 | 31.75 | 31.44 | 31.46 | 31.62 |

The **sharpest single frame anywhere in the plateau** is 30.56 um, still
**2.17x** the 14.11 um that a diffraction-limited `f_c = 86.3` gives through
this instrument. No frame-selection rule, however favourable, reaches the
diffraction limit. The `MTF(40)` peak is noisy frame to frame (0.112 to 0.172
over frames 3-8), which is why the pre-registered rule used a 3-frame moving
average per rule 4; the rise distance is visibly the more stable statistic.

### 4.3 The falsifier that fires

**MEASURED (M88).** The aperture ratio of edge width is

> `rise(f/11) / rise(f/5.6) = 32.49 / 31.70 = 1.025`

against a pre-registered prediction of **1.9643**, which is `11/5.6` exactly
and is **independent of both `m` and `p`**. The two stacks are the same
physical subject at working distances differing by 1.1%, so the prediction is
good to about 1%. The measured ratio excludes it by roughly nineteen standard
errors. The same conclusion appears in every other estimator M88 ran:

| estimator | measured ratio | predicted |
| --- | ---: | ---: |
| model-free 10-90 rise | **1.025** | 1.964 |
| fitted cutoff, pre-registered settings | 1.204 | 1.964 |
| fitted cutoff, exploratory settings | 1.088 | 1.964 |

**DERIVED (M88).** Decomposing total blur as `sqrt(diffraction^2 + other^2)`,
a measured ratio of 1.025 implies an aperture-independent blur **7.45x** the
f/5.6 diffraction blur. Even the most generous of the three estimators, 1.204,
implies **2.3x**.

**ARGUED (M88).** These captures are not diffraction-limited, and by a wide
margin. Two candidates are confounded and cannot be separated with these
subjects: the object's own edge softness — the plastic mesh silhouette is the
tangent boundary of a rounded extruded ribbon, which is photometrically soft by
geometry, and the `+5.39 DN/um` bright-wing ramp in the measured ESF is exactly
that geometry — and lens aberration wide open behind a 2x teleconverter. Both
would produce what is observed. Distinguishing them requires a subject whose
own edge is negligible.

### 4.4 What the shortfall costs

**MEASURED (M88).** At 40 cy/mm the f/5.6 captures reach `MTF = 0.1232`
(median of four ROIs). A diffraction-limited system at `f_c = 86.3` reaches
**0.4080 +/- 0.0215** through the identical instrument at the identical
half-width. The shortfall is **3.31x**.

**MEASURED (M88).** The same comparison at f/11 is *uninformative, and is
reported so rather than banked*. A diffraction-limited system at `f_c = 43.9`
reaches only `MTF(40) = 0.0466 +/- 0.0111` through this instrument, because
40 cy/mm is already 91% of that cutoff. The measured f/11 value is 0.0481.
The two are statistically identical, so `MTF(40)` cannot discriminate at f/11 —
it is pinned near the floor whatever the optics do. This is the reason M88's
load-bearing statistic is the 10-90% rise distance of §4.2, which is a
high-signal quantity at both apertures, and it is also why the *fitted*-cutoff
ratios of §4.3 (1.088 and 1.204) sit further from 1.0 than the model-free
ratio (1.025): at f/11 the fit is partly driven by the noise floor.

**MEASURED (M88).** The fitted-cutoff estimator is independently untrustworthy
on this data, which the pre-registered gate already refused. The free amplitude
in the fit is pinned at a bound in **6 of 11 ROIs** — at 0.500 on C1, D1, D2
and D3, and at 1.805 and 2.000 on A4 and C4. The single highest `MTF(40)` in
the corpus, 0.3825 at 119MSDCF ROI A4, carries `amp = 1.805` and a cutoff of
117.57 cy/mm, and is a fit pathology rather than a sharper edge: the same ROI's
model-free rise is 27.83 um, still **1.97x** the 14.11 um that `f_c = 86.3`
would give. No ROI is near diffraction-limited by the model-free measure.

**DERIVED (M88).** Interpolating the reference table of §4.2, a 31.70 um rise
corresponds to the same edge width as a diffraction-limited system at roughly
**31 cy/mm**, and a 32.49 um rise to roughly **30 cy/mm**. Both lie **below**
the binned-output Nyquist of 48.83 cy/mm. This is an equivalence of edge width,
not a cutoff, and it is a property of these subjects rather than of the optics.

### 4.5 Nothing detected above 48.83 cy/mm, and why that proves little

**MEASURED (M88).** On both the pre-registered settings and a
clearly-labelled exploratory arm (64 um half-width, per-wing deramp,
split-half noise floor), **zero ROIs** carry three consecutive bins above three
times the noise floor at either 86.30 or 97.66 cy/mm. The pre-registered Bar 1
therefore returns *not refuted*.

**MEASURED (M88), disclosed against interest.** Two ROIs do exceed 3x the
floor at 97.66 cy/mm in a **single** bin — 119MSDCF A2 at `z = 3.28` and A3 at
`z = 3.47` — without the run of three that the pre-registered criterion
requires. M88 does not claim these; a single bin out of ~13 above 20 cy/mm is
roughly what multiple comparisons produce at that threshold, and both ROIs
carry low pinned-ish fit amplitudes (0.690 and 0.656) indicating a poor edge
model. They are recorded because omitting them would be selective reporting,
and because a future capture should check that band deliberately.

**MEASURED (M88).** That null is not informative about the optics, because the
noise floor is not photon-limited. Per-bin scatter in the ESF wings is
**4.19x and 3.53x** the photon-only prediction on 119MSDCF ROI A1. The floor is
set by the subject's own along-edge texture and by aliasing of scene content
above the sublattice Nyquist, neither of which improves with exposure. Trap 3
applies in its strongest form: this crossing is a property of the subject and
the SNR, not of the lens.

## 5. Fact 1149 is refuted by the corpus's own measurements

### 5.1 The number: `p = 1` is excluded, so 86.3 cy/mm is excluded

Fact 1149 reaches `f_c = 86.3 cy/mm` through `N_eff = N(1 + m/p)` at
**`p = 1`**. Fact 1152 excludes that value.

**MEASURED elsewhere (fact 1152, from M84b and M5).** `p` lies in
`[1.31, 1.94]`. `p = 1` would demand `B = 3.72`, exceeding M5's measured upper
bound of 3.064.

**DERIVED (M88).** Recomputing the cutoff at 550 nm by two routes that share no
input:

| route | inputs | `N_eff` | `f_c` at 550 nm |
| --- | --- | --- | --- |
| A — M5's measured bellows factor `B` in [2.41, 3.06] | needs **neither** `m` **nor** `p` | 13.50 to 17.14 | **106.10 to 134.72 cy/mm** |
| B — fact 1152's measured `p`, M84b's `m = 2.7198` | needs both | 13.45 to 17.23 | **105.54 to 135.17 cy/mm** |
| fact 1149 — assumed `p = 1` | assumption now excluded | 21.07 | 86.30 cy/mm |

The two measured routes agree to **0.6%**, which is a meaningful cross-check
because route A never touches the ruler that M84 and M84b disagree about.
**86.3 cy/mm lies outside both intervals.** Fact 1149's number should be
replaced by `f_c` in **[106, 135] cy/mm** at 550 nm.

### 5.2 Clause (a) collapses with it

**DERIVED (M88).** The entire corrected interval lies **above** sensor Nyquist,
97.66 cy/mm. So "MTF at sensor Nyquist is exactly zero" is false at the central
wavelength, on measured inputs, with no appeal to bandwidth at all.

It is false a second time, independently, on wavelength. Fact 1149's cutoff is
a monochromatic 550 nm figure and the Bayer green channel is not monochromatic:

| `lambda` | `f_c` at `N_eff = 21.07` | MTF at Nyquist | `f_c` at `N_eff = 17.16` | MTF at Nyquist |
| ---: | ---: | ---: | ---: | ---: |
| 450 nm | 105.48 | **0.0240** | 129.51 | **0.1409** |
| 500 nm | 94.93 | 0.0000 | 116.56 | **0.0765** |
| 530 nm | 89.56 | 0.0000 | 109.96 | **0.0442** |
| 550 nm | 86.30 | 0.0000 | 105.96 | **0.0260** |
| 600 nm | 79.11 | 0.0000 | 97.13 | 0.0000 |
| 650 nm | 73.03 | 0.0000 | 89.66 | 0.0000 |

**DERIVED (M88).** Weighting by a Bayer-green passband (Gaussian, centre
535 nm, sd 35 nm):

| assumption | broadband MTF at 97.66 | broadband MTF at 86.30 | highest `f_c` in band |
| --- | ---: | ---: | ---: |
| fact 1149, `N_eff = 21.07` | 0.0005 | 0.0139 | **106.1 cy/mm** |
| M5's measured bound, `N_eff = 17.16` | **0.0437** | 0.1121 | **130.2 cy/mm** |

**ARGUED (M88).** Clause (a) fails three ways, in increasing severity: even on
fact 1149's own `N_eff` the green passband reaches 106.1 cy/mm at its blue end,
so "exactly zero" is already false; on M5's measured bound 4.4% of modulation
survives at Nyquist broadband and 14.1% at 450 nm; and on the corrected pupil
the cutoff is above Nyquist at *every* wavelength in the band. It should be
withdrawn.

### 5.3 What clause (b) becomes

**DERIVED (M88).** Fact 1149 claims the binned path discards real detail across
**48.83 to 86.3 cy/mm**. The *direction* of that claim survives and in fact
strengthens: the band is **48.83 cy/mm to sensor Nyquist, 97.66 cy/mm**, capped
by the sensor rather than by the optics, because the corrected optical cutoff
now sits above Nyquist. The band is **wider** than fact 1149 stated, not
narrower. This is the one part of fact 1149 that comes out ahead.

**ARGUED (M88).** The advice in `docs/captures-needed.md` §17 also survives.
Critical sampling needs an Airy diameter near two pixels; at the corrected
`N_eff` in [13.45, 17.23] it is `2.44 x 0.55e-3 x N_eff` = **18.1 to 23.1 um**,
or **3.5 to 4.5 px**. Still oversampled, so "critical sampling is unreachable
with the converter fitted" holds — on a number roughly 20% smaller than the one
originally used to argue it.

### 5.4 Disclosure: M88 missed fact 1152 at pre-registration

**MEASURED (M88), disclosed against interest.** Fact 1152 was folded into the
corpus at commit `875ad9d`, which precedes M88's own pre-registration
`7e32f7d`. M88's rule-40 prior search found M5's `B` bound and recorded the
23% tension it creates with fact 1149, but did **not** find fact 1152's
explicit `p` bracket, and the pre-registration therefore restates `p = 1`
without challenge. That was an incomplete prior search, and the finding of §5.1
belonged to the corpus before this milestone started.

It changes nothing in the measurement. Bar 3 was pre-registered as a **ratio at
two apertures**, chosen precisely because `f_c(N1)/f_c(N2) = N2/N1` is free of
both `m` and `p`. The pupil correction cannot move it. It moves the *target*
of Bar 2 — from 86.3 to the interval [106, 135] — but Bar 2 returned
UNIDENTIFIED for lack of any gate-passing ROI, and would have returned
UNIDENTIFIED against any target.

## 6. Registered bars and disposition

| registered bar | result | disposition |
| --- | --- | --- |
| Bar 1 — is MTF at sensor Nyquist detectably non-zero? | 0 of 22 ROI-plane results pass 3-sigma / 3-bin | **NOT REFUTED — MEASURED** (uninformative: floor is subject-limited, §4.5) |
| Bar 2 — does the 95% interval contain 86.3 cy/mm? | no ROI passes the validity gate | **UNIDENTIFIED — MEASURED** |
| Bar 3 — is `f_c(f/5.6)/f_c(f/11) = 1.9643`? | **1.025** model-free; 1.088-1.204 fitted; bar was [1.67, 2.26] | **FAIL — MEASURED** |
| Bar 4 — UNIDENTIFIED trigger: gate fails on every ROI | gate fails on all 22 | **TRIGGERED — MEASURED** |
| validity gate, 4 conditions | 21 fail `sigma_fit` (6.3-29.1 um), 1 fails `amp` | **FAIL — MEASURED** |
| C1 positive control within +/-10% | +1.19% +/- 1.50% | **PASS — MEASURED** |
| C1b reach above 48.83 cy/mm | 114.6 cy/mm | **PASS — MEASURED** |
| C2 lattice/orientation spread < 1.10x | 1.026x | **PASS — MEASURED** |
| C4, C5 placebos must not report a bound above 50 cy/mm | both abstain | **PASS — MEASURED** |
| C6 heavy defocus must be gated out | gated | **PASS — MEASURED** |

The pre-registered UNIDENTIFIED trigger fired on its own terms. No threshold
was moved after the data was seen; the exploratory arm of §4.5 is labelled as
post-hoc, changed nothing, and is not used to support any verdict.

## 7. What this means for the milestones that depend on it

**ARGUED (M88). M85's acceptance test must not use 86.3 cy/mm — it is now
known to be the wrong number, not merely an uncertain one.** The falsifier
"any energy above 86.3 cy/mm in the full-resolution output is artifact" is
unsafe on three independent counts:

1. **It rests on an excluded assumption.** `p = 1` is refuted by fact 1152.
   On the measured `p` in [1.31, 1.94], or equivalently on M5's measured `B`,
   the cutoff is **[106, 135] cy/mm** at 550 nm — the entire interval above
   86.3, and above sensor Nyquist. A falsifier set at 86.3 would reject real,
   representable detail across 86.3-97.66 cy/mm as "artifact".
2. **It is monochromatic.** The green channel's passband reaches 130.2 cy/mm
   at its blue end on M5's measured bound; red and blue differ again.
3. **It is not the binding constraint.** A full-resolution output on the sensor
   grid cannot represent anything above **sensor Nyquist, 97.66 cy/mm**,
   whatever the optics do.

**The defensible falsifier is sensor Nyquist, 97.66 cy/mm.** It is physically
binding, independent of `m`, `p` and `lambda`, and — now that the corrected
optical cutoff sits above it — it is also the *tighter* of the two constraints,
so nothing is lost by adopting it. There is no longer any band in which
diffraction limits a full-resolution output before the sensor does.

**ARGUED (M88). The "estimation, not selection" thesis is unharmed and its
band gets wider.** Fact 1149 argued real signal across 48.83-86.3 cy/mm; the
corrected optics give **48.83 cy/mm to Nyquist at 97.66**, a band 43% wider,
now limited by the sensor rather than the lens. What M88's captures cannot do
is *demonstrate* signal in that band, because their subjects are soft: the
achieved system response in them is equivalent to a diffraction-limited system
at about 30-31 cy/mm, below even the binned-output Nyquist. The band is a
property of the optics, which these subjects cannot reveal.

## 8. What would unblock the measurement

**ARGUED (M88).** For `docs/captures-needed.md`. The blocker is the subject,
not the rig, the sensor, or the method. Required:

- **A hard opaque straight edge in the object plane.** A razor blade
  (edge radius ~0.1 um) or a chrome-on-glass slanted-edge target (~0.5 um)
  both qualify. On the corrected `N_eff` in [13.45, 17.23] the image-side Airy
  diameter is 18.1-23.1 um, so the object-side Airy radius at `m = 2.7198` is
  **3.3 to 4.2 um**, and the object's own edge must be well under ~1 um to be
  negligible. A rounded plastic filament and an etched steel ruler graduation
  are both **10-25 um** and are disqualified — this is why M88 did not use the
  ruler stacks.
- **Slant 3-7 degrees** from a sensor axis, edge length at least 800 sensor
  pixels, and **no other structure within 200 um** of the edge on either side.
- **Flat, even illumination on both sides.** The measured `+5.39 DN/um` wing
  ramp is subject geometry; a flat backlight removes it entirely.
- **The same edge shot at f/5.6, f/8 and f/11 without moving the subject.**
  This turns the aperture ratio into a three-point ladder. It is the strongest
  available test because `f_c(N1)/f_c(N2) = N2/N1` exactly, free of both `m`
  and `p`.
- **A fine focus bracket** — enough frames that `MTF(40 cy/mm)` changes by less
  than 5% between adjacent frames near the peak, so residual defocus at the
  chosen frame is negligible.

**ARGUED (M88).** With that one capture, this instrument measures the cutoff to
about `+/-2%` statistical and `+/-9%` systematic on the effective wavelength.
A measured cutoff inverts to `N_eff = 1/(lambda f_c)` and thence, with M84b's
`m`, to `p = m/(N_eff/N - 1)` — **narrowing `p` from fact 1152's factor-1.48
bracket [1.31, 1.94] to a few per cent**, and doing it from a photograph rather
than the bench measurement `captures-needed.md` §18.3 currently asks for. The
three-point aperture ladder additionally checks the `N_eff = N x B` model form
itself, free of both `m` and `p`, which is the check M88 ran and which failed
on subject-limited edges.

## 9. Reproduction

All code and results are under `experiments/M88-optical-ceiling/`.
`D:\personal\macro` was read only. Nothing was pushed.

| script | what it does |
| --- | --- |
| `src/m88lib.py` | the instrument |
| `src/s03_controls.py`, `src/s04_instrument_spec.py` | controls C1-C6 and the calibration table |
| `src/s05_find_edges.py` | geometric ROI selection, no frequency quantity |
| `src/s06_measure.py` | every ROI on every frame of three stacks, both green planes |
| `src/s07_analyse.py` | the pre-registered bars, applied without deviation |
| `src/s09_deramp_control.py` | R1-R3, the repair control that killed M88's own hypothesis |
| `src/s11_exploratory.py` | the labelled post-hoc arm |
| `src/s12_closing.py` | model-free rise distances and the clause (a) arithmetic |
| `src/s13_robustness.py` | reference scales and the best-focus plateau sweep |

**MEASURED (M88).** The instrument is unchanged since pre-registration. The
only edits to `m88lib.py` after `PREREGISTRATION.md` was committed are 50
inserted lines appending two new functions, `deramp_esf` and `sfr_from_sites2`,
with zero deletions and no modification to any pre-registered code path.
Re-running the frozen control battery reproduced `out/s03_controls.json`
byte-identically at SHA-256
`7d08a7eadba3f4b36f5e84bd41a2b632c49d01914d59b5079a2f8da9c2acb950`.

**MEASURED (M88).** Full corpus lint was run as its own command, separately
from any commit, and exited **0 with no violations** across 116 markdown files
and 35 Rust files.

## 10. Candidate facts for owner review

| candidate | claim | class | source |
| --- | --- | --- | --- |
| P1 | **Fact 1149 is refuted at its number.** Its `f_c = 86.3 cy/mm` requires `p = 1`, which fact 1152 excludes by measurement. Recomputing gives `f_c` in **[106, 135] cy/mm** at 550 nm by two routes agreeing to 0.6% -- via M5's measured `B` (needing neither `m` nor `p`) and via fact 1152's measured `p` with M84b's `m`. 86.3 lies outside both intervals. | DERIVED | §5.1 |
| P2 | **Clause (a), "MTF at sensor Nyquist is exactly zero", is refuted.** The whole corrected interval [106, 135] lies above sensor Nyquist 97.66 cy/mm at the central wavelength. Independently, on M5's measured bound the broadband green MTF at Nyquist is 0.0437, and 0.1409 at 450 nm. | DERIVED | `out/s12_closing.json`; §5.2 |
| P3 | **Clause (b) survives and widens.** The band the binned path discards is 48.83 cy/mm to sensor Nyquist 97.66, not 48.83-86.3: 43% wider, and now limited by the sensor rather than by diffraction. `captures-needed.md` §17 also survives -- the corrected Airy diameter is 18.1-23.1 um or 3.5-4.5 px, still oversampled. | DERIVED | §5.3 |
| P4 | Fact 1149's arithmetic is itself correct: `N_eff = 21.0672`, Airy diameter 28.27 um = 5.522 px, `f_c = 86.30 cy/mm`, sensor Nyquist 97.656 cy/mm. It fails on an excluded pupil assumption and on monochromaticity, not on arithmetic. | MEASURED | §1 |
| P5 | On the same physical subject at two apertures, the measured ESF 10-90% rise is 31.70 um at f/5.6 and 32.49 um at f/11, a ratio of 1.025 against the 1.9643 that `N_eff = N(1+m/p)` predicts free of `m` and `p`. The captures are not diffraction-limited. | MEASURED | `out/s12_closing.json`; §4.3 |
| P6 | An aperture-independent blur 7.45x the f/5.6 diffraction blur dominates these captures. Object edge softness and wide-open aberration behind the 2x teleconverter are confounded and cannot be separated with these subjects. | DERIVED / ARGUED | §4.3 |
| P7 | At best focus the f/5.6 captures reach `MTF(40 cy/mm) = 0.1232`, against 0.4080 +/- 0.0215 for a diffraction-limited `f_c = 86.3` system through the same instrument at the same settings: a 3.31x shortfall. At f/11 this statistic cannot discriminate, the diffraction-limited value being 0.0466 +/- 0.0111 against a measured 0.0481. | MEASURED | `out/s11_exploratory.json`; §4.4 |
| P8 | M5's radial-PSD instrument tops out at 69.1 cy/mm on its best lattice and structurally could not have tested an 86.3 cy/mm cutoff. | MEASURED | M5 §2.2; §2 |
| P9 | A slanted-edge SFR estimator on a single 10.24 um Bayer green sublattice, with no demosaicing, resolves planted cutoffs of 60-140 cy/mm to +1.19% +/- 1.50% and reports model-free signal to 114.6 cy/mm, 2.35x that sublattice's Nyquist. | MEASURED | `out/s04_instrument_spec.json`; §3 |
| P10 | A whole-line gradient centroid recovers 1.21 deg from a planted 1.98 deg edge slant under realistic noise; a two-stage windowed estimator recovers 2.0003 deg on the same input. Slanted-edge implementations must use the two-stage form. | MEASURED | §2.2 |
| P11 | ESF truncation inflates MTF by +3.4% / +1.6% / +0.83% at half-widths of 96 / 192 / 384 um, halving as the half-width doubles, and is flat in frequency over 10-78 cy/mm. | MEASURED | §2.2 |
| P12 | The high-frequency noise floor of these captures is 3.5-4.2x the photon-only prediction. It is set by subject texture and aliasing, not photons, so a spectral floor crossing here bounds the subject, not the lens. | MEASURED | `out/s08` diagnostics; §4.5 |
| P13 | None of 22 ROI-plane results across `119MSDCF`, `109MSDCF` and `tweezers-cpl` passes the four-condition validity gate: 21 fail `sigma_fit` at 6.3-29.1 um against a 3.0 um bar, and one is a degenerate corner fit caught by the pre-registered amplitude condition. The corpus contains no edge sharp enough to measure the optical cutoff. | MEASURED | `out/s07_verdict.json`; §4.1 |
| P14 | M85's acceptance falsifier should be sensor Nyquist, 97.66 cy/mm. With the corrected cutoff above Nyquist, diffraction never binds a full-resolution output before the sensor does, and a falsifier at 86.3 would reject real representable detail across 86.3-97.66 cy/mm. | ARGUED | §7 |
| P15 | The unblocking capture is a razor blade or chrome-on-glass slanted edge, 3-7 degrees, backlit flat, at least 800 px long, clear of structure within 200 um, shot at f/5.6, f/8 and f/11 without moving the subject, with a focus bracket fine enough that `MTF(40 cy/mm)` changes under 5% between adjacent frames. It would narrow `p` from a factor-1.48 bracket to a few per cent, from a photograph rather than a bench jig. | ARGUED | §8 |
| P16 | The conclusion is insensitive to frame selection: across the whole best-focus plateau of 119MSDCF A1 (frames 3-9) the ESF rise stays 30.56-34.18 um, and the sharpest single frame is still 2.17x the diffraction-limited 14.11 um. | MEASURED | §4.2 |
| P17 | Two-parameter cutoff-plus-blur fits are unreliable on subject-limited edges: the free amplitude pinned at a bound in 6 of 11 exploratory ROIs, and one pre-registered fit ran to the corner of the box at `sigma = 0`, `f_c = 400`, `amp = 2`. Model-free rise distance should be preferred, and an amplitude-bound condition is a necessary gate. | MEASURED / ARGUED | §4.1, §4.4 |
| P18 | M88's rule-40 prior search was incomplete: it found M5's `B` bound and the 23% tension it creates, but missed fact 1152, which had landed at `875ad9d` before M88's pre-registration `7e32f7d` and already excluded `p = 1`. The pre-registered Bar 3 was `m`- and `p`-free by design, so no measurement was affected. | MEASURED | §5.4 |
