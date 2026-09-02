# M-PHASE0-RHO preregistration

**Question:** Estimate the alias-to-baseband scene-power ratio `rho` used by
`M-PHASE0-PHASE`, with an uncertainty interval that includes scene, aperture,
ISO, sensor, noise-floor, fit-band, and sampling-lattice uncertainty.

**Status:** Written before this lane decoded any RAW pixel, inspected any new
capture metadata, fitted any spectrum, or computed any value of `rho`. The lane
is not blind. I read the existing exploratory A7.4 result in
`M-PHASE0-PHASE`, the M5 diffraction report, M129's stored spectral survey, and
`M-PHASE0-QUINCUNX` before writing this document. Those sources point in
opposite directions, as recorded in section 2.

**Owned paths:** `experiments/M-PHASE0-RHO/` and
`docs/research/M-PHASE0-RHO.md` only.

**Read-only capture roots:** all of `D:\`.

## 1. Estimand

Amendment A2.2 defines, for alias component `k`,

```
rho = E |x_k|^2 / E |x_0|^2.
```

The expectation is over scene-frequency neighbourhoods and real scenes. A2.2
then replaces every component by one common scalar. This lane therefore reports
the component distribution first and reduces it to a scalar only at the end.

Let the full sensor Nyquist square be

```
B = { (fx, fy) : -0.5 <= fx, fy < 0.5 }.
```

For green, the sampled lattice is the quincunx. Its first Brillouin zone is

```
Q = { (fx, fy) in B : |fx| + |fy| <= 0.5 }.
```

For red or blue, the sampled lattice is `2 Z^2`. Its base cell is

```
R = { (fx, fy) in B : |fx| <= 0.25 and |fy| <= 0.25 }.
```

The physical one-times alias groups are:

```
G:  f, wrap_B(f + (0.5, 0.5))
RB: f, wrap_B(f + (0.5, 0)),
       wrap_B(f + (0, 0.5)),
       wrap_B(f + (0.5, 0.5))
```

with `f` in `Q` for G and in `R` for RB. `wrap_B` chooses the representative
inside the sensor Nyquist square. Groups are deduplicated before aggregation.

For a captured-scene power model `S(fx, fy)`, the scalar matching A2.2 is

```
rho_G  = sum S(f_alias) / sum S(f_base)

rho_RB = sum S(f_alias) /
         (3 * sum S(f_base)).
```

The sums use the same 8 by 8 frequency grid as `p1_bar.py`, after deduplicating
equivalent groups. Thus a white scene gives exactly `rho = 1`, which is a
mandatory control. The primary headline is `rho_G`, because G-1x is the
least-demanding C1 system and sets the proposal's last surviving case. `rho_RB`
is reported separately. A 16 by 16 and 32 by 32 grid are sensitivity arms.

The scene-level scalar is the ratio of summed powers, not the mean of individual
ratios. The latter diverges when a base component is weak and does not equal the
expectation in A2.2. Component ratios and their 10th to 90th percentile range
are still reported.

## 2. Prior evidence and why it does not answer the question

Rule 40 was run mechanically with `prior_art.py`. The broad search named
`M5-diffraction-measured.md` and `M113-spectral.md`; targeted searches for
"alias-to-baseband scene power" and "green quincunx spectrum" returned no
indexed report. A manual content search also found these directly relevant
sources:

1. `M-PHASE0-PHASE` A7.4 reports `rho` near zero. It is explicitly exploratory.
   Its white-spectrum control expects `rho_G = 9` and `rho_RB = 27` because the
   script sums nine reciprocal-lattice members per alias. A2.2 defines a
   per-component ratio, for which a white spectrum must give 1. That instrument
   therefore does not directly measure the A2.2 scalar.
2. `M-PHASE0-QUINCUNX.md`, reading M129's stored spectra, reports significant
   noise-subtracted power from 0.26 to 0.33 sensor cycles/pixel at four of five
   apertures. That contradicts the broad statement that every real spectrum is
   already gone below 0.26, but it does not separate the two members of a
   quincunx alias pair and uses one fabric subject.
3. `M5-diffraction-measured.md` establishes the frequency units, the GQ
   re-indexing, the diamond support, and a real diffraction roll-off. It does
   not estimate `rho`.
4. `M113-spectral.md` asks whether scene colour explains lateral chromatic
   aberration. Its Spearman `rho` is a correlation coefficient, not this
   quantity, and supplies no numerical prior.

This lane treats A7.4 and M-PHASE0-QUINCUNX as conflicting, unblinded prior
evidence. Neither value is used as a fit target or a control answer.

## 3. What the Bayer lattice can and cannot observe

The separate G1 and G2 planes are square lattices with support
`|fx|, |fy| <= 0.25`. Reading either plane above that support is forbidden.

The union of both greens is a true quincunx. Re-indexing it onto its square
coordinates uses the same no-interpolation map as M5:

```
GQ[u, v] = raw[u + v, u - v + 1].
```

In sensor coordinates its support is the diamond `Q`. It reaches radius
`sqrt(1/8) = 0.353553` in every direction and reaches 0.5 only on the sensor
horizontal and vertical axes. Therefore:

* all orientations are directly constrained through radius 0.353553;
* radii from 0.353553 through 0.5 are constrained only in progressively
  narrower sectors around the sensor axes;
* no green-only single-frame statistic directly observes a Fourier coefficient
  outside `Q`;
* a GQ periodogram inside `Q` contains the sum of the base member and its
  diagonal alias in expectation. It is not an unaliased measurement merely
  because the plotted frequency is inside `Q`.

The primary model fits that aliased sum rather than pretending it is one
component:

```
P_GQ(q) = S(q) + S(wrap_B(q + (0.5, 0.5))) + N(q).
```

For a wide-sense stationary field, distinct Fourier coefficients have zero
expected cross term. Welch averaging over disjoint spatial blocks estimates
that expectation. Synthetic controls include deterministic coherent gratings,
for which the cross term does not vanish, so this assumption can fail loudly.

### 3.1 Why focus-bracket super-resolution is not used

A focus bracket contains sub-pixel offsets, but using those offsets to unfold
the alias pair would assume both the registration accuracy and the
alias-unfolding operation whose viability C1 is trying to establish. It would
make `rho` depend on the proposed solution and is circular for this decision.

No primary or secondary `rho` estimate in this lane may use temporal
super-resolution, a reconstructed image, a demosaiced image, an aligned stack,
or a `strehl` merge. Repeated no-bracket frames may be used only to estimate a
noise cross-spectrum on the original sampling lattice. Any pair requiring more
than a low-band phase ramp to compare is rejected rather than super-resolved.

## 4. Primary spectral estimator

### 4.1 Inputs

The planned capture roles, fixed before inspection, are:

| capture | role |
|---|---|
| `6-11-extended-dark-frames` | read-noise PSD, fixed-pattern PSD, loader cross-check |
| `10-paper-iso-var` | signal-dependent noise and ISO sensitivity |
| `12-bee-iso-var-no-bracket-32-repeat-diff-light` | temporal noise, cross-spectrum, ISO and light sensitivity |
| `19-razor-edge` | broadband edge control and high-frequency transfer check |
| `30-calibration-grid` | frequency-axis and periodic-content control |
| `7-aperture-pairs` | aperture dependence on one fixed subject |
| `8-tilted-planar` | natural planar texture with local focus variation |
| ordinary macro stacks | scene census, secondary to the controlled captures |

Every distinct camera model with at least one usable controlled capture is a
sensor stratum. If only one model qualifies, sensor variation is explicitly
unidentified rather than inferred from ISO or from another directory copy.

### 4.2 RAW loading

Only `rawpy.RawPy.raw_image_visible` is used. The array is copied or converted
inside the `with rawpy.imread(...)` context. Active dimensions, CFA pattern,
black levels, white levels, camera model, ISO, exposure, aperture, and file
hash are recorded. A second independent decode of at least one file per sensor
must reproduce dimensions, CFA pattern, per-plane mean, per-plane standard
deviation, and a pixel checksum.

No file under `D:\` is written.

### 4.3 PSD

The primary PSD is a two-dimensional Welch periodogram of GQ patches:

* primary GQ patch size: 1024 by 1024 samples where geometry permits;
* primary Welch tile: 256 by 256, Hann window, 50 percent overlap;
* sensitivities: tile 128 and 512, and Kaiser-8 window;
* DC and radii below 0.04 sensor cycles/pixel are excluded;
* clipped or black-censored patches are rejected by thresholds recorded in
  output, not silently trimmed;
* a fixed spatial grid is used before looking at high-frequency power;
* ordinary-stack frame choice uses only power below 0.12 cycles/pixel and is
  cross-fitted by spatial block. It may select focus but may not select on the
  band used to measure `rho`.

The PSD keeps `(fx, fy)` for every bin. Radial averaging is a presentation
only. The fit uses the actual diamond support and therefore uses the directly
observable axial reach between radius 0.353553 and 0.5.

### 4.4 Noise measurement and subtraction

Three answers are always produced:

1. `rho_raw`: no noise subtraction;
2. `rho_dark`: temporal read-noise subtraction only;
3. `rho_full`: read plus photon-noise subtraction, the primary answer.

Temporal dark differences estimate read-noise power. Split-half dark means
estimate correlated fixed-pattern power, which is subtracted separately from
scene power and never called temporal noise.

Repeated illuminated frames estimate variance as a function of mean signal.
The primary model is

```
variance_DN = gain_DN_per_e * signal_DN + read_variance_DN.
```

It is fitted per sensor, CFA plane, and ISO mode where the data support that
split. A held-out repeat group must be predicted to within 20 percent in median
variance. If it is not, the full-subtraction result is not licensed and the
cross-spectrum result becomes primary.

For stable repeated frames, the real part of the phase-corrected
cross-periodogram is a second estimator. Independent photon and read noise have
zero expectation there. A low-band phase fit below 0.12 cycles/pixel may remove
a translation. Pairs are rejected if the fitted shift uncertainty exceeds
0.02 sensor pixel or if residual low-band coherence is below 0.95. No magnitude
cross-spectrum is used as a power estimate because magnitude is biased upward.

Negative noise-subtracted bins remain signed in intermediate outputs. They are
not clipped to zero before averaging or fitting. A censored-likelihood fit and
a signed-bin bootstrap are reported; clipping would bias `rho` upward.

### 4.5 Scene-power model

The registered fallback is a power law:

```
S(fx, fy) = A * r^(-beta) * exp(
    c2 cos(2 theta) + s2 sin(2 theta) +
    c4 cos(4 theta) + s4 sin(4 theta)).
```

The angular terms let a directional subject remain directional instead of
being turned into an isotropic scene by radial averaging. The primary fit uses
all GQ bins in the diamond with `0.04 <= r <= 0.46` and estimated power at least
three standard errors above zero. The model prediction compared with data is
the aliased sum in section 3, not `S(q)` alone.

The fit is robust in log power and weighted by independent Welch block count.
It must have at least 40 usable bins, cover at least a 2.5 times frequency
range, and reach at least 0.25 sensor cycles/pixel. Otherwise the ROI produces
no point estimate.

Three predeclared fit-band sensitivities are also run:

```
0.04 to 0.20
0.06 to 0.30
0.08 to the highest significant directly supported bin
```

The highest alias frequency divided by the highest directly supported
same-sector frequency is recorded as the extrapolation factor. `beta`, its
bootstrap interval, model residuals, and the derivative
`d log(rho) / d beta` are mandatory outputs.

The power law is deliberately conservative near a diffraction cutoff. A pure
power law falls more slowly than an optical MTF approaching zero, so extending
it past the observed roll-off overpredicts alias power and biases `rho` upward.
A monotone spline and a power-law times diffraction-MTF-squared model are
reported as sensitivity arms, never substituted silently for the registered
model.

### 4.6 Holdout and refusal

Every fourth angular sector is held out from fitting. Median absolute holdout
error must be at most 0.30 dex and the 90th percentile at most 0.60 dex. A
larger error means one `beta` is not a defensible description of that ROI.

If the corrected alias-band power is not significantly positive, the lane
reports a one-sided 95 percent upper bound. A model extrapolation may still be
shown, but it is labelled MODEL-DEPENDENT and cannot be promoted into a
measured detection.

If fewer than three independent scenes survive the fit and noise gates, no
cross-scene point estimate is reported.

## 5. Independent real-data checks

### 5.1 Razor edge

The razor edge is not a natural-scene estimate. A step edge has amplitude
proportional to `1/f` and power proportional to `1/f^2` before the optical
transfer. A slanted-edge ESF, fitted independently for each CFA plane without
demosaicing, checks:

* sensor-frequency units;
* whether the fitted high-frequency roll-off is physically plausible;
* whether the power-law extrapolation overpredicts rather than underpredicts
  the measured edge transfer;
* whether clipping or bevel structure invalidates the edge.

No edge segment satisfying the registered clipping, straightness, and
repeatability gates means refusal, not segment shopping.

### 5.2 Calibration grid

Known periodic peaks must appear at the predicted sensor frequencies on every
legal lattice. A factor-of-two axis error, a CFA-phase swap, and a use of G1 or
G2 beyond their support must each fail this control.

### 5.3 Achromatic full-mosaic bound

On a patch whose low-frequency R/G and B/G ratios are spatially constant to
within 1 percent, each CFA phase is gain-normalised using a disjoint low-band
region and the full mosaic PSD is computed. This is an upper-bound check only:
residual chroma modulation sits at CFA carriers and can only inflate the
apparent alias power. It may corroborate a high `rho`; it may not establish a
low one.

## 6. Instrument commissioning before real measurement

Commissioning code is split into a truth generator, the estimator, and a
checker. The estimator never imports planted `rho` or `beta`. Truth is written
to a separate manifest and read only by the checker.

### 6.1 Known-answer controls

| ID | control | required result |
|---|---|---|
| C1 | white 2D spectrum | `rho_G = rho_RB = 1` within 10 percent |
| C2 | power laws with `beta` in `{1.5, 2, 2.5, 3, 4}` | fitted `beta` within 0.20 noise-free and 0.35 noisy |
| C3 | planted `rho` in `{1, 0.3, 0.1, 0.03, 0.01}` at exact alias groups | median error within 0.15 dex, worst within 0.30 dex |
| C4 | Bayer sampled synthetic scenes | same gates as C3 after GQ extraction |
| C5 | Poisson plus read noise | full subtraction beats raw and dark-only, and stays within C3 gates |
| C6 | zero alias power | corrected estimate is not significantly positive and the 95 percent interval includes zero |
| C7 | anisotropic power law | angular model beats isotropic holdout error and recovers aggregate `rho` within 0.30 dex |
| C8 | coherent grating | stationarity/cross-term gate rejects or flags it, rather than reporting a false broadband `rho` |
| C9 | translated repeated frames | low-band phase correction restores cross-power for shifts through 0.25 px; uncertainty gate rejects larger ambiguous cases |
| C10 | razor-like step edge | pre-MTF slope is `beta = 2` within 0.25 |
| C11 | flat ROI | no sharpness or scene-power detection after full subtraction |
| C12 | active-area and CFA round trip | exact dimensions, phases, and checksums |

### 6.2 Deliberate defects

Each defect must turn a named control red. The tally uses `CAUGHT` only when the
intended control fails for the intended reason.

| ID | planted defect | intended catcher |
|---|---|---|
| D1 | treat G1/G2 bins above 0.25 as directly observed | C12 and grid control |
| D2 | multiply sensor frequency by two | C10 and grid control |
| D3 | sum nine reciprocal members per alias | C1 |
| D4 | use `abs(cross_spectrum)` as power | C6 and C11 |
| D5 | omit photon noise while retaining dark subtraction | C5 |
| D6 | clip negative corrected bins to zero | C6 |
| D7 | swap G1 and G2 phase geometry | C9 and grid control |
| D8 | use `S(q)` instead of the aliased GQ sum | C3 and C4 |
| D9 | let the estimator read planted `rho` | source-isolation check |
| D10 | make checker totals omit an unverified claim | checker accounting control |

Required commissioning summary:

```
known-answer controls: PASS n / FAIL n
deliberate defects:    CAUGHT n / MISSED n
```

Any `FAIL` or `MISSED` blocks real-data measurement.

## 7. Bias directions declared before measurement

| ID | mechanism | direction on rho |
|---|---|---|
| B1 | photon or read noise left in the high band | upward |
| B2 | over-subtracting a white floor | downward |
| B3 | clipping negative corrected bins to zero | upward; forbidden |
| B4 | low-frequency leakage through a finite window | upward |
| B5 | GQ base bins contain their unresolved alias partner | flattens the slope, usually upward; fitted explicitly |
| B6 | residual CFA gain or scene chroma at carrier frequencies | upward |
| B7 | fixed-pattern or PRNU retained by a repeat cross-spectrum | upward |
| B8 | sub-pixel mismatch between repeated frames | downward through high-frequency decorrelation |
| B9 | selecting a frame or ROI on the same high band being measured | upward; cross-fitting is required |
| B10 | selecting only the sharpest controlled subjects | upward relative to a scene census |
| B11 | using a pure power law through an optical roll-off | upward because it omits the cutoff |
| B12 | radial averaging of anisotropic scenes | either direction; orientation-resolved results are mandatory |
| B13 | censoring base frequencies already at the floor | either direction if dropped; model evaluation and counts are reported |
| B14 | dark-frame exposure or ISO mismatch | under-subtraction is upward, over-subtraction is downward |
| B15 | using focus-bracket shifts to unfold the same aliases | upward and circular; prohibited |
| B16 | spatially coherent periodic texture | can move either way and violates the stationary random-field approximation; grid/grating gate flags it |

The primary estimator is designed so that its largest remaining modelling bias,
the pure-power-law continuation through a roll-off, is upward. Since a larger
`rho` loosens C1's registration bar, this bias favours C1.

## 8. Uncertainty and variation

Uncertainty is hierarchical:

1. Welch blocks within ROI;
2. ROIs within frame;
3. frames or repeat groups within capture;
4. captures within scene;
5. scenes within sensor/aperture stratum.

The primary interval is a scene-cluster bootstrap with 10,000 resamples,
reported as a 95 percent interval in log `rho`. Fit-band, tile, window,
noise-model, and spectral-model arms are not folded into that sampling interval.
Their full envelope is reported separately as systematic uncertainty.

Material variation is predeclared as:

* scene: between-scene 90/10 ratio above 3;
* aperture: paired ratio above 2 with a bootstrap interval excluding 1;
* ISO: paired ratio above 1.5 with an interval excluding 1;
* sensor: paired or matched-scene ratio above 2 with an interval excluding 1.

These are effect-size gates, not p-value fishing. Failure to meet a gate is
reported as "not material at this resolution", not "identical".

For the C1 census, the recommended sweep is the smallest interval covering:

* the 95 percent scene interval;
* every material aperture or sensor stratum;
* the registered power-law fit-band envelope;
* the full-noise and cross-spectrum primary estimators.

ISO is included only if it changes the corrected result. Raw ISO dependence
that disappears after noise subtraction is a noise-floor artifact, not scene
variation.

## 9. Outputs and independent note checker

Machine-readable outputs will include:

* `inventory.json`
* `commission.json`
* `noise-model.json`
* `spectra-index.json`
* `scene-estimates.json`
* `aggregate.json`
* `sensitivity.json`

The research note is `docs/research/M-PHASE0-RHO.md`.

`src/check_note.py` will independently parse the output files and re-derive
every numerical claim in the note. It may contain formulas and tolerances but
not a copy of the expected result. It reports:

```
VERIFIED n
UNVERIFIED n
TOTAL n
```

and asserts `VERIFIED + UNVERIFIED == TOTAL`. A separate commissioning script
will mutate both note claims and output values, including at least one mutation
where note and output agree with each other but are both wrong relative to
lower-level records.

## 10. What would make the final answer "cannot determine"

The lane will decline a point estimate if any of these occurs:

1. commissioning has any failed known-answer control or missed deliberate
   defect;
2. the measured noise model misses held-out temporal variance by more than 20
   percent and no stable cross-spectrum arm exists;
3. fewer than three independent scenes pass the spectral fit;
4. holdout error exceeds section 4.6 on most scenes;
5. corrected alias power is not significantly positive and the model
   extrapolation spans more than one decade over its `beta` interval;
6. the primary and repeat cross-spectrum estimates disagree by more than a
   factor of two without an identified cause;
7. the answer changes by more than a factor of three under legal lattice,
   fit-band, or noise-floor choices.

In that case the deliverable is an upper bound and a capture prescription. The
decisive capture would be a fixed, achromatic, broadband macro target recorded
at the working magnification and aperture as:

* at least 32 repeated frames at each of three exposure levels;
* a matched dark set at the same ISO and exposure duration;
* one fixed-subject aperture ladder;
* one slanted edge in the same session;
* no focus motion, IBIS state recorded, camera fixed;
* enough edge slant or known microtexture to provide within-frame spatial
  phase diversity without temporal super-resolution.

## 11. Relevant house-rule discharge map

* Rule 7: only active/visible RAW pixels enter statistics.
* Rules 8 and 39: every reported claim names MEASURED, VERIFIED, DERIVED,
  ARGUED, or UNVERIFIED, and every separation includes its null uncertainty.
* Rules 9, 20, 35, and 36: controls have named failure inputs, independent
  truth, deliberate defects, and assertions that the exercised case occurred.
* Rule 10: temporal variance and spatial scene power are never compared as the
  same quantity.
* Rule 11: the claimed noise defect has raw, dark-only, full, and cross-spectrum
  placebo arms.
* Rule 12: the author does not certify the result by inspection; the
  independently written checker must re-derive it.
* Rule 17: ROI/frame selection is cross-fitted away from the measured band.
* Rule 18: section 7 fixes every known bias direction.
* Rule 23: all filtering is explicitly two-dimensional.
* Rule 24: verification changes estimator choices, not merely arithmetic.
* Rule 32: RAW buffers are copied before context exit and independently decoded.
* Rule 34: synthetic plants validate the estimator, not the sensor calibration;
  real repeats validate calibration.
* Rule 40: prior-art search and named reports are in section 2.
* Rule 42: every commit uses explicit owned paths.
* Rule 46: command exit codes are captured before any display filtering.

