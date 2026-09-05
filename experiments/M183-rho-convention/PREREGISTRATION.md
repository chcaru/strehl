# M183-rho-convention preregistration

**Lane:** M183-rho-convention  
**Registered:** 2026-09-04, before this lane computed any new value of rho,
ran the M183 instrument, or inspected the stored per-record boundary-average
values.  
**Owned paths:** `experiments/M183-rho-convention/` and
`docs/research/M183-rho-convention.md` only.

This lane is not outcome-blind. The task supplied the old `rho = 0.0055`,
its `0.00185--0.01078` interval, the C1 verdicts at `rho = 0.0055` and
`rho = 0.01`, and the old `30.49x` 8-to-32-grid sensitivity. The choice below
therefore rests only on the estimand and its consumer, not on which verdict it
will produce.

## 1. Question and estimand

M-PHASE0-PHASE A2.2 defines, for each alias component at output frequency
`nu`,

```text
rho = E |x_alias(nu)|^2 / E |x_base(nu)|^2.
```

The current PHASE simulator then replaces the frequency-dependent ratios by
one common scalar: each base coefficient has variance one and each alias
coefficient has variance `rho`
(`experiments/M-PHASE0-PHASE/src/plib.py:326-339`). Its bar experiment samples
`nu` on an 8 by 8 cell-centred grid
(`experiments/M-PHASE0-PHASE/src/p1_bar.py:40-44`,
`experiments/M-PHASE0-PHASE/src/plib.py:169-185`).

M-PHASE0-RHO fits a continuous scene-power model to green-quincunx Welch
spectra, then reduces the model to the scalar

```text
sum(alias-component power)
---------------------------------
mean aliases per group * sum(base-component power).
```

The scene-level result is the median across scene clusters. Its interval is a
10,000-resample scene-cluster bootstrap
(`experiments/M-PHASE0-RHO/src/aggregate.py:22-23,69-84`).

This lane will pin the convention for that **operational scalar consumed by the
current PHASE bar**, not claim a grid-independent natural-scene constant.

## 2. Candidate frequency conventions found in the corpus

### 2.1 Units and lattice coordinates

1. **Cycles per full-resolution sensor pixel.** This is the unit used by both
   PHASE's coset representatives
   (`experiments/M-PHASE0-PHASE/PREREGISTRATION.md:68-96`) and the RHO
   estimator (`experiments/M-PHASE0-RHO/src/rho_lib.py:1-4`).
2. **Green-quincunx native DFT coordinates `(fu,fv)`.** The RHO estimator maps
   these to sensor coordinates as
   `fx=(fu-fv)/2, fy=(fu+fv)/2`
   (`experiments/M-PHASE0-RHO/src/rho_lib.py:254-260`). Treating `fu,fv`
   directly as sensor cycles/pixel is the factor-two axis defect already
   planted in the original commissioning; it is not an admissible alternative.
3. **Cycles per photosite pitch / cycles per millimetre.** The exploratory
   PHASE A7.4 instrument reports both
   (`experiments/M-PHASE0-PHASE/PREREGISTRATION.md:1016-1029`). Cycles per
   pitch is physically the same unit as cycles per full-resolution sensor
   pixel here; cycles/mm is only a pitch conversion and is not the coordinate
   consumed by PHASE.

### 2.2 Scalar quadrature grid

1. **8 by 8 cell-centred grid over `[-0.5,0.5)^2`.** This is PHASE's actual
   `NU_GRID=8` consumer grid and RHO's original matching grid. Coordinates are
   `-0.5 + (i+0.5)/8`; neither DC nor either Nyquist edge is sampled.
2. **16 by 16 and 32 by 32 cell-centred grids.** RHO registered these as
   sensitivity arms, not as PHASE consumer grids
   (`experiments/M-PHASE0-RHO/PREREGISTRATION.md:70-74`). They change the
   quadrature population while PHASE remains at 8 by 8.
3. **The measured Welch DFT grids.** The primary fit uses 256 by 256 bins with
   128 and 512 tile sensitivities
   (`experiments/M-PHASE0-RHO/PREREGISTRATION.md:193-198`). These bins estimate
   the continuous scene model; they are not the quadrature grid that reduces
   that model to PHASE's scalar.
4. **The exploratory radial-bin grid.** PHASE A7.4 used a Hann-windowed central
   mosaic and linearly spaced radial-bin edges
   (`experiments/M-PHASE0-PHASE/src/p7_rho.py:64-85`). It was exploratory and
   its nine-member normalization was later rejected, so it is not an
   admissible A2.2 scalar.
5. **XSPEC's 64/48/32 Welch ladder.** It is a separate phase statistic; its
   48-bin arm deliberately leaves eight samples unused
   (`experiments/M-PHASE0-XSPEC/PREREGISTRATION.md:111-117`). It confirms that
   a DFT-resolution ladder is distinct from PHASE's output-frequency
   quadrature.

No edge-sampled scalar grid, continuum quadrature, or DC/Nyquist half-weight
rule is specified anywhere in the RHO/PHASE corpus. Introducing one now would
require a new low-frequency loss weighting: the fitted power law is only
licensed from radius 0.04 upward, while scalar-grid refinement introduces
ever-smaller base radii. That decision is absent rather than silently supplied
by this lane.

### 2.3 DFT endpoints

The Welch estimator uses `numpy.fft.fftfreq`: DC and the negative Nyquist bin
exist, the positive Nyquist endpoint does not
(`experiments/M-PHASE0-RHO/src/rho_lib.py:254-260`). The fit excludes DC and
all radii below 0.04
(`experiments/M-PHASE0-RHO/PREREGISTRATION.md:193-198`), retains only one
Hermitian half-plane, and clips no signed noise-corrected bin merely for being
negative (`experiments/M-PHASE0-RHO/src/rho_lib.py:449-478`). These rules
remain fixed; they do not define the scalar quadrature.

## 3. Candidate boundary conventions found in the corpus

### 3.1 Green Brillouin-zone ties

The cell-centred 8 grid has 32 unique green alias pairs, eight exactly on
`|fx|+|fy|=0.5`; the 16 and 32 grids have 16/128 and 32/512 ambiguous groups
(`experiments/M-PHASE0-RHO/PREREGISTRATION.md:532-540`). RHO implements four
choices:

1. **primary:** lower Euclidean radius, then lexicographically smaller
   integerised coordinate on an exact tie;
2. **swap:** the other valid base representative;
3. **average:** average both reciprocal base/alias assignments;
4. **exclude:** omit every ambiguous pair.

They are implemented at
`experiments/M-PHASE0-RHO/src/rho_lib.py:154-193`. RB has no ambiguous group
on these grids.

PHASE itself uses a half-open target band when selecting coset representatives
and the corrected carrier is `nu-h`
(`experiments/M-PHASE0-PHASE/src/plib.py:128-145,189-224`). That convention
selects a Fourier representative; it does not physically distinguish two
members of a green boundary pair as lower- versus higher-frequency scene
power.

### 3.2 Spatial patch boundaries and windows

1. **RHO primary:** fully in-bounds 1024 by 1024 square GQ patches; 256 by 256
   Welch blocks; 50% overlap; per-block mean removal; separable periodic Hann
   (`np.hanning(n+1)[:n]`); no padding. The FFT therefore periodises the
   windowed block
   (`experiments/M-PHASE0-RHO/src/rho_lib.py:215-251`).
2. **RHO sensitivities:** 128 and 512 blocks and Kaiser-8; a rectangular
   (`none`) window exists for controls
   (`experiments/M-PHASE0-RHO/src/rho_lib.py:215-225`).
3. **XSPEC:** separable symmetric Hann, no padding/interpolation/demosaic or
   boundary wrap; the DFT periodises the windowed block
   (`experiments/M-PHASE0-XSPEC/PREREGISTRATION.md:133-136`).
4. **Exploratory PHASE A7.4:** one Hann-windowed square central mosaic
   (`experiments/M-PHASE0-PHASE/src/p7_rho.py:64-85`).
5. **Reflected boundaries** occur in XSPEC synthetic Gaussian-filter plants,
   not in either real RHO estimator
   (`experiments/M-PHASE0-XSPEC/src/truth_factory.py:17-32,67`).
6. **Unwindowed periodic FFT** occurs in RHO's low-pass flat-response-map
   construction, not in the natural-scene PSD
   (`experiments/M-PHASE0-RHO/src/data_lib.py:145-158`).

Zero padding, zero extension, reflected extension, resampling non-square
patches, and power-of-two padding are not real-RHO alternatives in the corpus.
Non-square active extents are handled by taking fixed, fully in-bounds square
GQ patches; no sample is invented.

## 4. Preregistered choice

### 4.1 Frequency grid

**Choose the 8 by 8 cell-centred grid in cycles per full-resolution sensor
pixel over the half-open full-sensor Nyquist square, deduplicate reciprocal
green pairs, and retain the existing DFT fit convention.**

Verdict-independent reason: this is the exact frequency population and unit
the downstream PHASE bar samples. A 16/32 grid would be a new consumer, not a
refinement of the scalar while leaving the consumer unchanged. A continuum
quantity would be scientifically useful but is not identified without a
low-frequency loss weighting/cutoff and a correspondingly refined PHASE run.

### 4.2 Alias boundary

**Choose the reciprocal-assignment average for all exact green-diamond
boundary ties.**

Verdict-independent reason: the two members are equally valid representatives
of the same quincunx coset on the shared boundary. Averaging is invariant to
axis orientation, Fourier representative, and arbitrary lexicographic label;
primary/swap are coordinate-label conventions, while exclusion discards 25%
of the operational 8-grid groups. This is the discrete half-weight analogue
for a shared cell boundary.

### 4.3 Spatial boundary

**Retain the commissioned RHO primary: in-bounds square patches, 256-square
50%-overlap Welch blocks, periodic Hann, no padding or resampling, per-block
demean, and the existing half-open FFT grid.**

Verdict-independent reason: windowing suppresses the artificial seam before
the DFT's unavoidable periodic extension; zero/reflection padding would create
unmeasured pixels and change the already commissioned fitted scene models.
This lane therefore recomputes only the scalar reduction from stored accepted
fit parameters, not the RAW spectra.

## 5. Computation fixed before execution

1. Read `experiments/M-PHASE0-RHO/out/scene-estimates.json`.
2. Use exactly the original PASS records and original primary-fit key.
3. For each accepted fit, evaluate its stored `beta` and four angular terms on
   the chosen 8 grid with boundary averaging. The power floor remains
   `r=max(norm(f),0.02)`, exactly as in the commissioned model.
4. Reproduce the original hierarchy: median records within each of the five
   named ordinary scenes; separately median the accepted bee repeat; then take
   the median of those six scene clusters.
5. Draw 10,000 bootstrap samples of six scene clusters with replacement using
   seed 20260902; report percentile 2.5 and 97.5. No grid, fit-band, model-form,
   or sensor systematic is folded into this sampling interval.
6. Read PHASE `out/p1_bar.json`, restricted exactly as `p8_verdict.py` does:
   G-1x, `zero_mean`, noiseless. Pair each configuration's rho ladder, require
   its bar to be nondecreasing, and interpolate `log(bar)` linearly in
   `log(rho)` between registered rho rungs. At the pinned median and both
   interval endpoints, compute the fraction with `bar > accuracy` for field
   centre 0.0801 px, inner annulus 0.1168 px, and corner 0.2256 px.
7. Apply the filed thresholds unchanged: `<25% KILL`, `25%--<60% NARROWED`,
   and `>=60% SURVIVE`
   (`experiments/M-PHASE0-PHASE/src/p8_verdict.py:108-141`). C1 still flips if
   any field radius changes class anywhere between the two interval endpoints.

No result-dependent convention substitution is allowed. If the PHASE rows
cannot be paired, their bar is nonmonotone, the selected records differ from
the original hierarchy, or a required input hash changes between commissioning
and measurement, the lane reports INDETERMINATE rather than choosing another
rule.

## 6. Commissioning fixed before execution

The instrument must pass all of these before its real result is licensed:

1. **Null/known answer:** a white spectrum returns rho exactly one.
2. **Known planted effect:** synthetic groups with base power one and alias
   power 0.04 return rho 0.04.
3. **Both directions:** changing only alias power to 0.08 raises rho exactly
   2x; changing it to 0.02 lowers rho exactly 0.5x.
4. **Inert arm:** multiplying every base and alias power by seven leaves rho
   bit-close to the 0.04 plant.
5. **Boundary invariance:** exchanging the two powers of every ambiguous
   boundary pair leaves the chosen average unchanged.
6. **Geometry:** an independent rational enumerator obtains 32 unique green
   pairs and eight ambiguous pairs on the chosen grid.
7. **Uncertainty:** a degenerate six-scene fixture has a point and bootstrap
   interval equal to its known constant.
8. **Verdict response:** a synthetic monotone bar ladder has known KILL,
   NARROWED, and SURVIVE reads.

Every deliberate source mutation is an exact, unique full-line replacement;
zero or multiple matches is a hard error. Mutants must be caught for: 8 to 16
grid, cycles/sensor-pixel scale 1 to 2, average to primary boundary labeling,
and numerator/denominator inversion. The commissioning output records whether
each arm fired and whether each mutant was caught.

## 7. What would make this choice wrong

* PHASE's production consumer may not actually use the 8-grid population
  represented by `p1_bar.py`; no production C1 implementation yet exists to
  settle that.
* A future C1 definition may require a continuum/image-loss integral. Then an
  8-grid operational scalar is the wrong estimand, and the corpus must first
  preregister the low-frequency weighting/cutoff and rerun PHASE on the same
  grid.
* Boundary averaging is wrong if one boundary member has a physically defined
  base role independent of coordinate labels. No such role is present in the
  current A2.2 algebra.
* The interval remains only a bootstrap over six selected scene clusters. It
  is not model-form, sensor, or target-population uncertainty.

