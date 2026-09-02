# M-PHASE0-RHO: scene power at the CFA aliases

**Lane:** `experiments/M-PHASE0-RHO/`  
**Status:** measured, with a convention-specific estimate and a universal-scalar
refusal.

## Finding

<!-- claim:verdict -->
**There is no licensed universal point estimate of `rho` from these data.**
The scalar is not stable to a harmless refinement of the frequency grid, so a
single scene-independent and grid-independent constant would imply more than
the experiment measured.

<!-- claim:headline -->
For the exact A2.2 PHASE convention on its `8 by 8` frequency grid, the best
f/5.6 scene estimate is **`rho = 0.0055165`**, with a scene-bootstrap
**95% interval from `0.0018471` to `0.0107793`**.

<!-- claim:rb-counterpart -->
Applying the same fitted scene spectrum to the red/blue alias geometry gives
**`rho_RB = 0.0053034`**, with scene-bootstrap **95% interval
`0.0021422` to `0.0089142`**. Its median is **`0.961x`** the green result, so
the exact-grid common-scalar approximation is adequate at this precision. It is
a model transfer, not a direct R/B high-frequency measurement.

<!-- claim:grid-sensitivity -->
The scene median is **`0.0055165` on the 8 grid, `0.0009659` on the 16 grid,
and `0.0001809` on the 32 grid**. The first-to-last change is **`30.49x`**,
which triggers the preregistered factor-three refusal rule.

<!-- claim:census-range -->
For C1, the defensible replacement for the old five-point sweep is an exact-grid
census spanning **`0.0001` to `0.06`**, at
**`{0.1, 0.03, 0.01, 0.003, 0.001, 0.0003, 0.0001}`**. The `0.1` point remains
as a conservative upper control rather than as a likely scene value.

<!-- claim:bar-mapping -->
Under the current PHASE implementation, the convention-specific headline maps
to a bar of **`0.0340 px`**, and its sampling interval maps to
**`0.0218` to `0.0447 px`**. This uses a fitted tail slope of **`0.40745`**
below PHASE's lowest simulated `rho`, so it is an extrapolation, not a licensed
C1 verdict.

## What was measured

No RAW was demosaiced. The instrument reads `raw.raw_image_visible`, preserves
the Bayer phases, estimates a Welch power spectrum on the green quincunx
lattice, and fits the observed alias-pair sums as scene power plus a measured
noise floor. The scene model is a two-dimensional power law with even angular
terms. It never reads a Fourier bin outside the sampling lattice's support and
never clips a negative noise-corrected bin into a positive detection.

<!-- claim:gq-support -->
The green quincunx support reaches **`0.500000 cyc/sensor-px` on the sensor
axes** and has an isotropic radius of **`0.353553 cyc/sensor-px`**. Those edge
bins are directly sampled, but each is still a sum of a baseband component and
its diagonal CFA alias. Direct reach therefore does not by itself separate the
two powers.

The exact PHASE scalar is the sum of the designated alias-component powers
divided by the mean per-alias base-component power. The implementation uses a
deterministic rule at quincunx-boundary ties and separately reports swapping,
averaging, and excluding those ties.

<!-- claim:power-law-beta -->
Across the six f/5.6 scene clusters, the median fitted exponent is
**`beta = 4.433`**, with scene **p10 to p90 `3.966` to `5.203`**. The median
formal fit error is only **`0.01115`**, but that is conditional on the power-law
model and is not the dominant uncertainty.

<!-- claim:extrapolation -->
The median alias component lies **`1.25x`** beyond directly separable support in
its own direction, and the farthest lies **`1.75x`** beyond it. At the median
fitted exponent, those radial continuations multiply power by **`0.372`** and
**`0.0837`**, respectively.

<!-- claim:beta-sensitivity -->
Holding every fitted angular term fixed but shifting every exponent by
**`-0.5`** raises the scene-median exact-grid result to **`0.0117436`**;
shifting by **`+0.5`** lowers it to **`0.0025648`**. This is why the small
formal exponent error cannot be treated as the uncertainty on `rho`.

<!-- claim:model-sensitivity -->
Changing the fitted frequency band moves the scene median by **`2.136x`**.
Excluding the exact-grid boundary groups gives **`rho = 0.0027832`**, or
**`0.505x`** the primary convention. These are model and definition
sensitivities, not sampling errors.

The focus brackets were not used as temporal super-resolution data. Doing so
would assume that the stack's subpixel translations can unfold the CFA aliases,
which is the same capability the proposal is trying to establish. It would make
the estimate circular. Repeat frames were used only for signed cross-spectra
and empirical noise floors.

## Commissioning and controls

<!-- claim:commission-tally -->
The primary synthetic commissioning tally is **`PASS 12 / FAIL 0`** known-answer
controls and **`CAUGHT 10 / MISSED 0`** deliberate defects.

<!-- claim:commission-accuracy -->
Across the planted exact-`rho` ladder, the median error is **`0.005 dex`** and
the worst is **`0.015 dex`**. In the hardest noise control, full photon-plus-read
subtraction errs by **`0.053 dex`**, the signed repeat cross-fit errs by
**`0.062 dex`**, while omitting photon noise errs by **`3.201 dex`**.

The deliberate faults include doubling the frequency axis, summing the wrong
number of aliases, taking the magnitude of a signed cross-spectrum, dropping
photon noise, clipping negative corrected bins, swapping the green phase
geometry, omitting the alias sum from the forward model, and letting the
estimator see planted truth. All were caught by controls that did not carry the
planted answer.

<!-- claim:geometry-controls -->
The separate physical diagnostics tally is **`PASS 4 / FAIL 0`** and
**`CAUGHT 2 / MISSED 0`**. The calibration grid repeats a fundamental at
**`0.039062 cyc/sensor-px`** on both axes, while the undemosaiced razor edge has
low-band **`beta = 2.379`** against the geometric step's value of two. The
synthetic version of that edge test misses two by only **`0.026`**.

The grid and razor are controls, not members of the natural-scene census. The
grid is deliberately coherent and the razor is not a stationary random field.

<!-- claim:record-accounting -->
The real run contains **`159` records**: **`46` pass**, **`78` fail
capture-quality gates**, and **`35` fail the holdout or commissioned-exponent
gate**.

<!-- claim:direct-detections -->
Among the passing records, **`40 of 46`** have positive corrected high-band
power, but only **`9 of 46`** have high-band scene-to-noise above three. The
median high-band scene-to-noise is **`0.262`**. Most accepted values are
therefore model-dependent continuations rather than direct alias-band
detections.

## Scene, aperture, ISO, and sensor variation

The exact-grid f/5.6 scene-cluster values are:

<!-- claim:scene-bee -->
* `bee-1-cpl`: **`0.0059477`**
<!-- claim:scene-marker -->
* `dry-erase-marker-head-cpl`: **`0.0018191`**
<!-- claim:scene-flower -->
* `flower-inner-edge-cpl`: **`0.0073274`**
<!-- claim:scene-pencil -->
* `pencil-steep-angle-cpl`: **`0.0050853`**
<!-- claim:scene-text -->
* `wrapped-text-1`: **`0.0142313`**
<!-- claim:scene-repeat -->
* independent repeated bee: **`0.0018750`**

<!-- claim:scene-variation -->
The scene **p90/p10 ratio is `5.836x`**, so scene variation is material. A
single corpus constant should not erase that spread.

<!-- claim:aperture-strata -->
On the controlled fabric ladder, accepted medians are **`0.0006648` at f/8,
`0.0003343` at f/11, `0.0002255` at f/14, and `0.0001696` at f/18**.

<!-- claim:aperture-pair -->
The paired **f/8-to-f/18 ratio is `4.510x`**, with bootstrap
**95% interval `3.501` to `6.363`**. Aperture variation is material and has the
expected direction: diffraction lowers alias-frequency scene power as the
aperture closes.

<!-- claim:iso -->
Across the usable ISO arm, **ISO `50` through `200`** spans
**`rho = 0.0004760` to `0.0010424`**. The primary max/min ratio is **`2.190x`**,
but the independent signed-cross ratio is only **`1.452x`**; ISO variation is
therefore not declared material. The higher ISO groups were rejected for
clipping.

<!-- claim:sensor -->
All usable captures identify as **one sensor model, Sony `ILCE-7CM2`**.
Sensor-to-sensor variation is unidentified, not zero.

## Noise-floor sensitivity

<!-- claim:noise-model -->
The commissioned sensor model uses spectral gain **`0.223812 DN/e`** and read
variance **`0.967583 DN^2`**. Its worst held-out median variance error is
**`0.006807`**, and the split response-map correlation is **`0.976884`**.

<!-- claim:noise-sensitivity -->
For the f/5.6 scene headline, no subtraction gives **`rho = 0.108817`**,
subtracting dark/read noise alone gives **`0.108586`**, and subtracting both
photon and read noise gives **`0.0055165`**. Photon subtraction lowers the
median by **`19.73x`**; dark subtraction alone changes almost nothing.

This is the main practical result. The uncorrected high-frequency floor looks
like scene power and would place the C1 input more than an order of magnitude
too high in `rho`. A dark frame alone cannot remove shot noise because shot
noise is set by illuminated signal.

## Bias directions

The remaining important directions are:

* residual photon noise pushes `rho` upward;
* fitting only positive corrected bins pushes `rho` upward;
* a pure power law continued through an optical cutoff pushes `rho` upward;
* coherent target content can push a broadband fit either way and is rejected;
* motion or illumination change in repeat differences inflates the empirical
  floor and pushes corrected `rho` downward;
* selecting visibly textured scenes can push a corpus estimate upward;
* excluding exact boundary groups pushes this convention's scalar downward.

The scene bootstrap is therefore only the sampling interval across the observed
scene clusters. The frequency-grid failure, exponent sensitivity, optical model
form, and single-sensor coverage are larger systematic uncertainties.

## Contradictions and corrections to the PHASE record

<!-- claim:a23-contradiction -->
A2.3's blanket statement that green cannot observe the alias frequencies is too
broad. Green quincunx samples reach the full sensor-axis Nyquist, although the
measurement there is an inseparable alias-pair sum. The fallback model is still
needed, but for separation rather than for lack of lattice reach.

<!-- claim:a22-contradiction -->
A2.2's proposed common scalar is not frequency-grid invariant: the registered
refinement changes the scene median by **`30.49x`**. Any C1 census must state the
grid and boundary convention as part of the definition.

<!-- claim:normalisation-contradiction -->
The exploratory A7.4 nine-member statistic does not implement A2.2's white-power
normalisation. A white scene produces **`9` for green and `27` for red/blue**,
not **`1`**.

<!-- claim:phase-sign-geometry -->
There is also an independent PHASE implementation defect. In the audited G-1x
case, `nu+h` places **`64 of 128` frequency components outside the target
band**, while `nu-h` places **`0 of 128`** outside. The physical translation
control has absolute error **`0.302143`** under `nu+h` and **`0`** under `nu-h`.

<!-- claim:phase-sign-bars -->
With the corrected representative sign, the pooled G-1x bar at
**`rho = 0.1` changes from `0.095635` to `0.123212`**, and at
**`rho = 0.01` from `0.039717` to `0.044721`**. At
**`rho = 0.005` both pooled medians are `0.026943`**, although individual
configurations still move. PHASE should be rerun before using the mapped bar as
a go/no-go decision.

## Bottom line for C1

<!-- claim:bottom-line -->
Use **`rho = 0.0055`** only as shorthand for the exact current PHASE grid and
this f/5.6 scene population. Use **`0.00185` to `0.01078`** for scene sampling
uncertainty, and use the wider **`0.0001` to `0.06`** census for design
decisions. Do not publish a universal scalar, do not use the uncorrected
`0.1088`, and do not settle C1 until the PHASE representative-sign defect is
rerun.

The machine-readable evidence is in `experiments/M-PHASE0-RHO/out/`.
`src/check_note.py` independently rebuilds the derived quantities from the
record-level outputs and reports verified, unverified, and total claim counts.
