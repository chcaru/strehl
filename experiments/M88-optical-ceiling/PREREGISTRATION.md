# M88 — optical-cutoff pre-registration

**Frozen before any spatial-frequency quantity is computed from any real
capture.** At the moment of writing, M88 has: read `AGENTS.md` and the
relevant `SYNTHESIS.md` fact blocks; built and calibrated a slanted-edge SFR
instrument on **synthetic plants only**; run EXIF audits; rendered
downsampled structural previews; and run a **purely geometric** edge search
that reports position, slant angle, contrast and straightness residual. No
ESF, LSF, MTF, PSD, cutoff or noise-floor number has been computed from any
file under `D:\personal\macro`. That is the freeze line.

The question is whether the corpus can supply a **measured** optical cutoff
frequency for the owner's rig, and whether that measurement confirms or
refutes fact 1149's **derived** `f_c = 86.3 cy/mm`. A verdict of
UNIDENTIFIED is an acceptable and complete result if the gates in §7 fail.

## 1. Source facts and assumptions frozen before data

- **DERIVED elsewhere, under test.** Fact 1149: `m = 2.762`, marked `N = 5.6`,
  assumed pupil magnification `p = 1`, hence `N_eff = N(1 + m/p) = 21.07`,
  Airy diameter `2.44 lambda N_eff = 28.3 um = 5.5 sensor px`, and
  `f_c = 1/(lambda N_eff) = 86.3 cy/mm` at `lambda = 550 nm`.
  **M88 has independently checked this arithmetic and it is correct**:
  `5.6 * 3.762 = 21.0672`; `2.44 * 0.55e-3 mm * 21.0672 = 28.27 um`;
  `1/(0.55e-3 mm * 21.0672) = 86.30 cy/mm`. The arithmetic is not the
  question. The *inputs* are.
- **MEASURED elsewhere, not by M88.** M5 measured a radial-PSD diffraction
  knee on the f/11 stack at `f_sig = 0.2762 cyc/px = 53.94 cy/mm`, giving the
  composite bellows factor `B = 1 + m/p <= 3.064`, with bias-corrected point
  estimates 2.93 and 2.63. Fact 1149 requires `B = 3.762`, which is **23%
  above M5's measured upper bound**. This tension exists in the corpus before
  M88 measures anything and is recorded here so that it cannot later look
  like a post-hoc rationalisation of whatever M88 finds.
- **MEASURED elsewhere, not by M88.** M5's best lattice (`GQ`, the re-indexed
  green quincunx, pitch 7.2408 um) has an isotropic radial reach of
  `0.3536 cyc/px = 69.1 cy/mm`. **M5's instrument therefore cannot see
  86.3 cy/mm at all.** Fact 1149 is not testable by the corpus's existing
  spectral tooling. That is why a new instrument is required.
- **VERIFIED elsewhere.** Sensor pitch 5.12 um, RGGB, black level 512, active
  area 7032 x 4688. Sensor Nyquist `1/(2 * 5.12 um) = 97.66 cy/mm`. A single
  CFA colour plane samples at 10.24 um, Nyquist `48.83 cy/mm`. The current
  binned output path has Nyquist 48.83 cy/mm.
- **MEASURED by M88 (EXIF audit, no frequency content).** Every stack in the
  corpus, old and new, was shot with the 2x teleconverter at 200 mm
  (`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`). `109MSDCF` is f/11,
  ISO 160, `FocusDistance2` 0.2738 m, 22 frames. `119MSDCF` is f/5.6, ISO 50,
  0.2707 m, 33 frames, and is the **same physical subject** as `109MSDCF`.
  `tweezers-cpl` is f/5.6, ISO 100, 0.2707 m, 100 frames. This opens an
  aperture ladder the M88 brief did not anticipate.
- **ARGUED assumption.** The pixel aperture is a square of the full 5.12 um
  pitch (microlens fill factor 100%), so `MTF_pixel(f) = sinc(pi f * 5.12um)`
  with first zero at 195.3 cy/mm. A smaller effective aperture would raise
  `MTF_pixel` and lower the fitted `f_c`. Sensitivity is reported, not
  assumed away.
- **ARGUED assumption.** The effective wavelength of the Bayer green channel
  under the capture illuminant is `lambda_eff = 550 nm`. Since
  `f_c = 1/(lambda N_eff)`, a `+/-50 nm` error moves `f_c` by `-/+9%`. This is
  carried as a systematic, and a broadband sensitivity arm is run in §6.4.
  Note that on fact 1149's *own* numbers `f_c` is 105.5 cy/mm at 450 nm and
  73.0 cy/mm at 650 nm, so "the cutoff" is a band, not a line.

## 2. The instrument

A single-plane, no-demosaic, ISO-12233-style slanted-edge SFR estimator.
Implementation is frozen in `src/m88lib.py`.

1. `rawpy.raw_image_visible` is copied inside its context manager (rule 32),
   black level 512 subtracted, active area only (rule 7).
2. **One Bayer green sublattice is used directly.** `G1` is
   `(even row, odd col)`, `G2` is `(odd row, even col)`. Sample values are
   carried together with their **sensor-pixel coordinates**, so the 10.24 um
   sublattice spacing never enters the frequency axis. There is **no
   demosaicing, no white balance, no colour matrix, no sharpening and no
   resampling** anywhere in the chain. Trap 2 is not confounded; it is
   avoided.
3. The edge line is fitted in two stages: argmax of a smoothed row gradient,
   then three windowed-centroid refinements inside `+/-6` samples, with a
   Huber IRLS line fit. **This two-stage form is load-bearing.** A
   single-stage whole-line centroid was measured on a synthetic plant to
   recover **1.21 deg from a planted 1.98 deg** because far-field noise
   samples outnumber signal samples; that bias flattens the slope and
   destroys the supersampling. The two-stage form recovers **2.0003 deg** with
   residual sd 0.0496 px on the same input.
4. Every sample in the ROI is projected onto the edge normal and binned into
   an ESF at **0.64 um** bin width over **+/-192 um**. A two-pass linear
   detrend along the edge direction is applied; it removes variation in the
   along-edge coordinate only and cannot manufacture a transition in the
   normal coordinate.
5. LSF by centred difference, wing pedestal removed, Tukey taper
   `alpha = 0.10`, real FFT. The centred-difference transfer function
   `sin(2 pi f d)/(2 pi f d)` and the bin-box `sinc(pi f d)` are divided out
   analytically.

### 2.1 Why this defeats trap 1

A single green sublattice has Nyquist 48.83 cy/mm, **below** the frequency
under test. The slanted-edge method is nevertheless not limited by it: for a
straight edge the image is a one-dimensional function of the projected normal
distance, and a slanted lattice samples that distance at arbitrarily fine
phase. The lattice pitch limits nothing but the sample count per bin. The
only real band limits are the 5.12 um pixel aperture (known, divided out) and
noise. **This claim is not assumed — it is proved by control C1b in §5.**

### 2.2 Frozen instrument settings

| parameter | value | why frozen here |
| --- | --- | --- |
| ESF bin width | 0.64 um | correction terms stay small (1.7% at 78 cy/mm) |
| ESF half-width | 192 um | Airy-tail truncation bias falls from 3.4% at 96 um to 1.6% at 192 um |
| Tukey alpha | 0.10 | measured to change `f_c` by < 0.1% |
| fit band | 10 to 150 cy/mm | below 10 the detrend acts; above 150 is the noise band |
| noise band | 250 to 380 cy/mm | above the 195.3 cy/mm pixel-aperture zero, so no optical signal can exist there |
| detection rule | 3 consecutive bins above `3 x floor(f)` | M5's rule, reused unchanged |
| green plane | G1 primary, G2 replicate | independent sublattice, same optics |

The noise floor is **frequency-dependent**, not a constant. White ESF-bin
noise gives a flat pre-division magnitude; the MTF divides it by
`corr(f) = sinc-like`, so the floor rises as `1/corr(f)`. The flat level is
estimated in the 250-380 cy/mm band and mapped back to every frequency. Using
a constant floor taken from that band would over-state the floor at 90 cy/mm
by roughly 2x and would make the headline test in §7 artificially hard to
pass; using a constant floor from 150-190 cy/mm would understate it. Neither
is used.

## 3. Estimators

- **E1 — model fit (primary for the number).** Least squares of
  `A * MTF_diff(f; f_c) * MTF_pixel(f) * MTF_gauss(f; sigma)` over the fit
  band, with `f_c` in `[20, 400]` cy/mm, `sigma` in `[0, 30]` um and free
  amplitude `A` in `[0.5, 2]`. `sigma` absorbs residual defocus, aberration
  and object-side edge softness. `A` absorbs the residual `+1.6%` ESF
  truncation scale error, which is measured to be flat across 10-78 cy/mm.
- **E2 — model-free bound (primary for reach, and a lower bound only).** The
  highest frequency carrying 3 consecutive bins above `3 x floor(f)`. Per
  trap 3 this is **not a cutoff**: it is where signal falls under noise, and
  it moves with exposure and averaging. It is quoted only as a lower bound.
  Calibration in §5 shows `E2 / f_c_true = 0.80 to 0.84` at plant SNR; that
  ratio is **not** used to convert E2 into a cutoff on real data, because the
  real SNR differs.
- **E3 — direct model-free reading.** `MTF(f)` and `floor(f)` read at three
  named frequencies: **48.83** (binned-path Nyquist), **86.30** (fact 1149's
  cutoff) and **97.66** (sensor Nyquist). No model, no fit, no extrapolation.

## 4. Locked ROIs, frames, and frame selection

ROIs were chosen from the geometric edge search in `src/s05_find_edges.py`,
on **slant angle, contrast and straightness residual only**. Coordinates are
in green-sublattice indices; each ROI is 160 rows by 400 columns of the
sublattice (320 by 800 sensor pixels).

| id | stack | N | aperture | axis | row0 | col0 | slant | role |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| A1 | `119MSDCF` | 33 | f/5.6 | horizontal | 1280 | 0 | -2.06 deg | primary |
| A2 | `119MSDCF` | 33 | f/5.6 | horizontal | 1280 | 200 | -1.90 deg | primary |
| A3 | `119MSDCF` | 33 | f/5.6 | horizontal | 1280 | 400 | -2.11 deg | primary |
| A4 | `119MSDCF` | 33 | f/5.6 | horizontal | 1280 | 600 | -1.95 deg | primary |
| B1 | `119MSDCF` | 33 | f/5.6 | horizontal | 800 | 0 | -1.92 deg | primary, highest contrast |
| C1 | `109MSDCF` | 22 | f/11 | horizontal | 1280 | 0 | -4.23 deg | ratio arm, matched content |
| C2 | `109MSDCF` | 22 | f/11 | horizontal | 1280 | 200 | -4.04 deg | ratio arm |
| C3 | `109MSDCF` | 22 | f/11 | horizontal | 1200 | 400 | -4.23 deg | ratio arm |
| C4 | `109MSDCF` | 22 | f/11 | horizontal | 1200 | 600 | -4.07 deg | ratio arm |
| D1 | `tweezers-cpl` | 100 | f/5.6 | horizontal | 2080 | 2000 | +1.82 deg | independent subject |
| D2 | `tweezers-cpl` | 100 | f/5.6 | horizontal | 2080 | 2400 | +2.30 deg | independent subject |
| D3 | `tweezers-cpl` | 100 | f/5.6 | horizontal | 2080 | 2600 | +2.72 deg | independent subject |

`109MSDCF` and `119MSDCF` are the **same physical subject** photographed at
f/11 and f/5.6 respectively, at working distances 0.2738 m and 0.2707 m.
ROIs A* and C* sit on the same long extruded ribbon silhouette.

`flat-on-ruler-cpl` and `highly-angled-ruler-mm-cpl` are **deliberately
excluded**. An etched or engraved steel graduation has an edge-quality scale
of roughly 10-25 um, which is comparable to the object-side Airy width
(`28.3 um / 2.762 = 10.2 um`); the object's own edge would be measured, not
the optics'. `coffee-bean` and `foam` contain no straight edges, so there is
**no clean f/8 rung**; the ladder is two-point by necessity.

### 4.1 Frame selection (trap 5, rule 4)

For every ROI, the SFR is computed on **every frame in the stack**. The focus
criterion is `MTF(40 cy/mm)`, a normalised quantity that is contrast-free and
well below any candidate cutoff. The reported frame is the argmax of a
**3-frame moving average** of that criterion, not the bare argmax; the moving
average is the winner's-curse defence. The full through-focus curve is
reported, together with the values at the two neighbouring frames, so that
any reader can see how sharp the peak is and whether the selection mattered.

Residual defocus at the selected frame biases the measured cutoff **down**
(measured in control C3: a 16 um defocus disc drives a planted 110 cy/mm to
75.7 cy/mm). This is stated up front because it sets the direction of every
contaminant: **a measured cutoff above 86.3 cy/mm is a robust refutation of
fact 1149; a measured cutoff below 86.3 cy/mm is ambiguous** between a real
low cutoff and residual blur, and must be reported as an upper-bounded
statement rather than a point measurement.

## 5. Controls — already run, on synthetic data only, results frozen here

All controls in this section were executed before the freeze line, on
synthetic plants containing no information from any real capture. Their
numbers are recorded here so that they cannot be re-run and re-chosen later.
Full output is in `out/s03_controls.json` and `out/s04_instrument_spec.json`.

### C1 — positive control: recover a planted cutoff

A pixel-integrated slanted edge is synthesised from the exact analytic
diffraction step response at a known `f_c`, then given Poisson photon noise
and 1.2392 e- read noise at ISO-100 gain. Ten seeds per planted value.

| planted `f_c` | E1 mean | E1 sd | bias | sd | E2 mean | E2/true |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 60.0 | 60.203 | 0.212 | +0.34% | 0.35% | 50.3 | 0.838 |
| 86.3 | 86.456 | 0.271 | +0.18% | 0.31% | 72.4 | 0.839 |
| 110.0 | 111.769 | 1.255 | +1.61% | 1.14% | 92.7 | 0.843 |
| 140.0 | 143.689 | 2.710 | +2.63% | 1.94% | 112.0 | 0.800 |

Pooled E1 relative error over 60-140 cy/mm: mean **+1.19%**, sd **1.50%**,
range -0.24% to +4.97%. **PASS.** The instrument's known bias is small and
positive; §6.3 subtracts it.

### C1b — reach proof: the instrument sees past the CFA-plane Nyquist

This is the control that discharges trap 1, and it uses **E2, which contains
no optical model at all**.

| planted `f_c` | E2 range over 10 seeds | CFA-plane Nyquist | verdict |
| ---: | --- | ---: | --- |
| 110.0 | 91.1 to 93.8 cy/mm | 48.83 | **PASS** |
| 140.0 | 109.4 to 114.6 cy/mm | 48.83 | **PASS** |

A single 10.24 um green sublattice, with no demosaicing, reports model-free
signal out to 114.6 cy/mm — **2.35x its own naive Nyquist** and above the
97.66 cy/mm sensor Nyquist. Measuring one green sublattice on a regular grid
and reporting "no energy above 48.83" would have been an instrument artifact;
this instrument is not subject to it.

### C2 — bookkeeping self-test

The same planted 110 cy/mm edge measured on G1 and G2, as a horizontal edge
and as a vertical edge: 110.256, 111.572, 113.145, 111.595 cy/mm. Spread
**1.026x**. A factor-of-two error in the frequency axis — the single error
most likely to fake this entire result, because 86.3 and 48.83 differ by
almost exactly 2x when the sublattice pitch is confused with the sensor pitch
— would read 2.00x. **PASS.**

### C3 — mis-specification: the extra blur is a disc, the model is a Gaussian

Real defocus is a uniform disc; E1's nuisance term is a Gaussian. Planting a
disc measures what that mismatch costs.

| planted `f_c` | disc | E1 | error | `sigma_fit` |
| ---: | ---: | ---: | ---: | ---: |
| 86.3 | 0 um | 86.24 | -0.07% | 0.31 um |
| 86.3 | 4 um | 85.82 | -0.55% | 0.90 um |
| 86.3 | 8 um | 85.86 | -0.51% | 1.96 um |
| 86.3 | 16 um | 73.90 | **-14.4%** | 3.35 um |
| 110.0 | 0 um | 112.99 | +2.71% | 0.81 um |
| 110.0 | 4 um | 112.74 | +2.49% | 1.27 um |
| 110.0 | 8 um | 111.12 | +1.02% | 2.11 um |
| 110.0 | 16 um | 75.71 | **-31.2%** | 2.45 um |

Two things are frozen from this. First, unmodelled blur pushes E1 **down**,
never up, so the contaminant direction in §4.1 is confirmed by measurement.
Second, **the `sigma_fit` gate does not catch a 16 um disc** (`sigma_fit` was
2.45 um, inside the gate, while the error was -31%). This is a known,
declared limitation of the instrument and is why a low measurement is
reported as ambiguous.

### C4 — negative control: flat field, no edge

A flat field with photon and read noise. The instrument **refused to
produce a number** ("74 empty ESF bins"), because with no edge the line fit
has nothing to lock to and the projected samples do not fill the ESF window.
E2 is `nan`. **PASS** — it abstains rather than reporting a cutoff.

### C5 — phase-destroying placebo

The real plant's sample **values are randomly permuted** across the ROI while
the fitted edge line, the geometry and the value histogram are all preserved.
This destroys the edge and nothing else. E2 = `nan`, floor 0.2707 (an order
of magnitude above any signal case). **PASS.**

### C6 — defocus placebo

A heavily defocused plant (30 um and 60 um discs on a planted 110 cy/mm
edge). E1 rails to its 400 cy/mm bound with `sigma_fit = 9.4 um`, and gives
63.4 cy/mm with `sigma_fit = 17.6 um`. E2 gives 36.5 and 31.3 cy/mm. Neither
reports anything near 86 cy/mm as a defensible cutoff, and both are caught by
the `sigma_fit < 3 um` validity gate. **PASS.**

### What would have made these controls fail

Recorded per rule 20, before the real measurement. C1 fails if any planted
value is recovered outside `+/-10%`. C1b fails if E2 does not exceed 48.83
cy/mm on the 110 and 140 plants — that failure would mean trap 1 is real for
this instrument and the whole approach must be abandoned. C2 fails if the
spread exceeds 1.10x. C4 and C5 fail if either reports a bound above
50 cy/mm. C6 fails if a 30 um or 60 um defocus passes the validity gate. All
six bars were written down in `src/s03_controls.py` and `src/s04_instrument_spec.py`
before those scripts were run.

## 6. Analysis, frozen

### 6.1 Validity gate

A ROI-frame result is reported as a **cutoff measurement** only if all hold:

1. `sigma_fit < 3.0 um`;
2. edge-fit residual sd `< 0.6` sensor px;
3. no empty ESF bins;
4. fitted amplitude `A` in `[0.8, 1.25]`.

Otherwise the ROI is **ABSTAIN** and only the E2 lower bound is quoted.

### 6.2 Aggregation

The primary f/5.6 cutoff is the **median of E1 over all passing (ROI, frame)
results at best focus**, across stacks `119MSDCF` and `tweezers-cpl`. The
uncertainty is the larger of (a) the between-ROI robust spread (1.4826 x MAD),
and (b) the instrument sd from §5 interpolated to the measured value,
combined in quadrature with the +/-9% wavelength systematic from §1.
The 95% interval is `+/-1.96` of that combined sd.

### 6.3 Bias correction

The instrument's measured bias from §5 (+0.34%, +0.18%, +1.61%, +2.63% at 60,
86.3, 110, 140 cy/mm) is linearly interpolated at the measured value and
subtracted. This correction is small and is applied in the direction that
makes refutation *harder*, not easier.

### 6.4 Sensitivity arms (reported, not primary)

- **Broadband.** The Bayer green channel is not monochromatic. E1 is re-fitted
  with the diffraction MTF averaged over a Gaussian spectral weight centred at
  540 nm with sd 40 nm.
- **Pixel aperture.** E1 is re-fitted with the aperture set to 0.9 x pitch.
- **G2 replicate.** Every primary ROI is re-measured on the other green
  sublattice.

### 6.5 Derived consequences

From the measured f/5.6 cutoff and `lambda_eff = 550 nm`:
`N_eff = 1/(lambda f_c)`; `B = N_eff / 5.6`; and, taking M84b's `m = 2.762` as
given, `p = m / (B - 1)`. All three are reported with intervals. Pinning `p`
is a stated secondary objective: the corpus currently flags it at `+/-38%`.

## 7. Frozen verdict bars

### Bar 1 — clause (a) of fact 1149, model-free and one-sided

Fact 1149 states **"MTF at sensor Nyquist is exactly zero"**.

- **REFUTED** if, at best focus, on **at least two ROIs drawn from at least
  two different stacks**, `MTF(97.66 cy/mm) > 3 x floor(97.66 cy/mm)` with at
  least 3 consecutive bins above threshold.
- **Not refuted** otherwise.

This bar uses E3 and E2 only: no optical model, no fit, no extrapolation. It
is deliberately one-sided and conservative. Residual defocus, object-side edge
softness and aberration all *reduce* `MTF(97.66)`, so a positive detection
cannot be manufactured by contamination. The two remaining ways to fake it are
a frequency-axis error, excluded by C2 at 1.026x, and noise, excluded by the
3-sigma / 3-bin rule and by the abstentions in C4 and C5.

### Bar 2 — the number

- **CONFIRMED** if the 95% interval on the corrected, aggregated f/5.6 cutoff
  **contains 86.3 cy/mm**.
- **REFUTED (upward)** if the interval lies **entirely above** 86.3 cy/mm.
  This is the strong form, because every known contaminant biases downward.
- **REFUTED (downward)** if the interval lies **entirely below** 86.3 cy/mm.
  This is the weak form and must be reported as an upper bound with the C3
  contamination caveat attached, not as a point measurement.

### Bar 3 — model form, free of both `m` and `p`

`f_c = 1/(lambda N(1 + m/p))` predicts
`f_c(f/5.6) / f_c(f/11) = 11 / 5.6 = 1.9643` **exactly, independent of `m`
and of `p`**, provided the two stacks share a magnification. Their working
distances differ by 1.1% (0.2707 vs 0.2738 m), so the prediction is good to
about 1%.

- **PASS** if the measured ratio lies in `[1.67, 2.26]` (`+/-15%`).
- **FAIL** otherwise, which indicts the `N_eff = N(1 + m/p)` model form
  itself rather than any of its constants.

This is a stronger test of the model than the absolute number, because it
needs neither `m` nor `p` to be right. It replaces the weaker
working-distance lever suggested in the M88 brief, which offers only a ~1%
magnification difference against a 96% aperture difference here.

### Bar 4 — UNIDENTIFIED

The verdict is **UNIDENTIFIED**, and the captures are declared unable to
support the measurement, if any of:

- the validity gate in §6.1 fails on **every** ROI at best focus;
- E2 never exceeds **60 cy/mm** on any f/5.6 ROI;
- the between-ROI spread of E1 exceeds **+/-25%** of its median.

In that event M88 states precisely what blocks the measurement and specifies
the capture that would unblock it, for `docs/captures-needed.md` §17.

## 8. Outputs and claim labels

All generated files stay under `experiments/M88-optical-ceiling/`. The report
is `docs/research/M88-optical-ceiling.md`. Every substantive statement is
labelled **MEASURED**, **DERIVED** or **ARGUED**; imported values are
namespaced to their milestone; candidate facts are numbered `P1`, `P2`, ...
and never as absolute fact numbers. `D:\personal\macro`, `C:\dev\macro` and
`D:\macro-dark-frames` are read-only. Nothing is pushed.

M88 does not own and will not modify `crates/`, `experiments/M84b-*`,
`experiments/M86-*`, `experiments/M87-*`, or any `docs/research/M8[4-7]*`
file.
