# M-PHASE0-XSPEC — preregistration

**State at registration:** no XSPEC control or outcome statistic has been run.
The only reads made before this document were metadata/file-layout inspection and
the prior-corpus search below.  This document governs the first run.

## 1. What C10 actually says

C10 is **not** a colour-channel-sharing proposal.  In
`docs/proposals/2026-08-sota-path.md`, under “C10. NEW — the phase channel,” it
proposes registration-aligned **complex through-focus cross-spectra**.  The four
reads are:

1. a linear phase ramp for sub-pixel registration;
2. odd-in-defocus phase for the sign of defocus;
3. phase-diversity pupil/aberration retrieval; and
4. a phase-coherence guard against contrast inversion.

The proposal's phase-0 gate asks for about 200 strong-texture tiles on two stacks,
each read against its elected-peak frame over `±5` focus steps.  If odd phase is
below the phase floor everywhere, reads 2 and 3 die together and C10 narrows to
registration and the inversion guard.  The proposal gives read 1 an approximately
`0.1 sensor-px` bar; it does not give reads 2–4 numerical bars.  Sections 5 and 6
below close those degrees of freedom now.

## 2. Corpus search, before new decoding

The mechanically commissioned rule-40 search was run first:

```text
python experiments/ORCH-drift-check/prior_art.py --commission
python experiments/ORCH-drift-check/prior_art.py phase cross spectrum defocus
python experiments/ORCH-drift-check/prior_art.py phase registration inversion coherence
```

The search found:

* `M70-through-focus-spectrum.md` measured modulus only.  Its §14 explicitly
  calls aligned complex cross-spectra the highest-value unmeasured follow-up.
  Its powered f/5.6 stacks and bands are reused, but none of its saved NPZ files
  contains complex coefficients.
* `M-PHASE0-PHASE/PREREGISTRATION.md` prices C1's alias-unfolding registration
  bar.  Its first KILL was retracted after three load-bearing defects; the final
  result is NOT ROBUST.  In particular, its cycle floor is not truth and its
  averaging proxy is capped.  This lane therefore does not reuse either as a
  truth label.
* `M-PHASE0-RHO.md` uses signed repeat cross-spectra and supplies the exact
  green-quincunx geometry.  Its scalar moves `30.49x` over an 8/16/32 frequency
  grid ladder.  That is why XSPEC fixes its grid and repeats on two alternate
  grids.
* `M-PHASE0-QUINCUNX.md` establishes measurable scene energy above plane Nyquist
  at four of five apertures, but it answers C12's kill gate, not C10.
* `M78-blur-equalised-edges.md` shows a bilinear half-shift can masquerade as a
  phase effect through its low-pass action.  XSPEC never resamples its primary
  RAW tiles.

The question is therefore not already answered in the corpus.

## 3. Data and fixed population

### 3.1 Outcome stacks

The two primary stacks are fixed before decoding:

| label | absolute directory | frames | setting | reason fixed in advance |
| --- | --- | ---: | --- | --- |
| `bee-1-cpl` | `D:\personal\macro\bee-1-cpl` | 299 | ISO 100, f/5.6 | M70-powered, deep subject with occlusions |
| `wrapped-text-1` | `D:\personal\macro\wrapped-text-1` | 130 | ISO 100, f/5.6 | M70-powered, different scene geometry |

No file under `D:\personal\macro` is written.  The first and last names, counts,
geometry, levels, and source checksums used by the run are recorded in
`out/inventory.json`.

### 3.2 External phase-floor capture

`D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light`
contains 64 ISO-100 repeats at fixed focus: the first 32 in time under the
`bright` light and the second 32 under the `warm` light, as independently
established by M-PHASE0-RHO.  Adjacent frames form 16 disjoint pairs per light.

The bright arm calibrates one overlap multiplier per Fourier grid.  The warm arm
is held out and must predict.  The outcome stacks never set this multiplier.
This is the mandatory external-data predicate: the code under test did not
generate or alter these fixed-scene RAWs.

### 3.3 Tiles and election

RAW is read with `rawpy.raw_image_visible.copy()` and kept undemosaiced.  The
green quincunx is extracted at even sensor centres.  Candidate centres are a
fixed `14 by 18` regular grid inside the 4,688 by 7,028 rawpy-visible area, with
the complete 128-by-128 quincunx crop inside bounds: 252 candidates.

For every candidate and frame, a single 128-by-128 symmetric-Hann DFT supplies:

* the election score: mean power over
  `0.10 <= radius < 0.22` cycles per full-resolution sensor pixel;
* the independent occlusion selector: mean power over
  `0.02 <= radius < 0.06`.

Each curve is smoothed only along frame index with `[1,2,1]/4`; its argmax is the
peak.  A candidate is eligible when the peak has all `±5` frames and peak
election-band signal-to-predicted sensor-noise is at least 5.  The 200 highest
eligible SNRs are selected per stack, with sensor row then column as the fixed
tie-break.  Fewer than 160 eligible tiles on either stack makes all population
claims INDETERMINATE; no weaker tile is substituted.

Selection on modulus can make phase easier to detect and therefore biases
**toward SURVIVE**.  That is deliberate: failure on the proposal's own
strong-texture population is the conservative KILL direction.

## 4. Fourier grid and boundary convention

The primary Welch sub-tile is `n=64` quincunx samples inside each 128 sample
patch, at 50% overlap.  Starts are `0, n/2, ...` while `start+n <= 128`.
Alternate grids are `n=48` and `n=32` under the same rule; the 48 grid leaves
the final eight samples unused on each axis.  These are a robustness ladder, not
selectable alternatives.

For unshifted DFT coordinates `(fu,fv) = numpy.fft.fftfreq(n)`, physical sensor
frequencies are exactly:

```text
fx = (fu - fv) / 2
fy = (fu + fv) / 2
```

in cycles per full-resolution sensor pixel.  A bin is legal when
`abs(fx)+abs(fy) <= 0.5`.  Radial intervals are lower-inclusive and
upper-exclusive.  Hermitian duplicates are removed with
`fy > 0 OR (fy == 0 AND fx > 0)`.  `fy == 0` means exact DFT-grid zero, not a
tolerance-selected neighbourhood.

Every Welch block has its own mean removed and is multiplied by the separable
**symmetric** Hann
`w[j] = 0.5 - 0.5*cos(2*pi*j/(n-1))`.  There is no padding, interpolation,
demosaic, or boundary wrap.  The DFT treats the windowed block as periodic.

Fixed bands:

* registration: `0.02 <= r < 0.12`;
* odd-phase: `0.06 <= r < 0.22`;
* inversion census: `[0.06,0.12)`, `[0.12,0.18)`, `[0.18,0.26)`.

Any overall verdict that changes on `n=48` or `n=32` is **NOT ROBUST**, even if
the primary grid is decisive.

## 5. Exact statistics

For moving tile `a` and reference tile `b`, each Welch block contributes

```text
C = FFT(a) * conj(FFT(b))
Pa = abs(FFT(a))^2
Pb = abs(FFT(b))^2
```

and blocks are averaged before fitting.  Coherence is
`gamma2 = abs(mean(C))^2 / (mean(Pa)*mean(Pb))`.

### 5.1 Read 1 — registration

A coarse integer search maximises the weighted real cross-spectrum over
`dx,dy in [-8,+8]` sensor pixels.  Iterated weighted least squares then fits
the residual phase to `2*pi*(fx*dx + fy*dy + intercept)` in the registration
band.  At least 20 legal bins with `gamma2 >= 0.20` are required.

Welch blocks are split by the fixed checkerboard of block coordinates.  Both
the phase-ramp estimator and an independently implemented spatial
normalised-cross-correlation/parabolic-peak solver are fit on each half.
Per-pair full-estimator precision is

```text
p = norm(estimate_half_0 - estimate_half_1) / 2
```

in sensor pixels.  The `/2`, rather than `/sqrt(2)`, maps the difference of two
equal half estimators to the precision of their full-data average.  This is a
precision statistic, not truth accuracy.

For each stack, report the tile-cluster-bootstrap median `p_phase`, median
`p_spatial`, and their paired ratio.  Read 1 passes only if, on both stacks,
the 95% upper bound for `p_phase` is below `0.100 sensor px` **and** the 95%
upper bound for `median(p_phase)/median(p_spatial)` is below `1.0`.

The statistic can be fooled low by a systematic shift common to both halves.
The fixed-crop absolute control in §7 catches sign, axis, and scale, but no
claim of sub-pixel truth accuracy is made.

### 5.2 Reads 2/3 — odd phase above the external floor

For tile peak `k0` and `d in {1,...,5}`, form the direct cross-spectrum of
`k0+d` against `k0-d`, fit and remove its linear phase ramp, and define

```text
theta_odd(f) = angle(C_derotated(f)) / 2
A = sqrt(weighted_mean(theta_odd^2))
```

over the odd-phase band, with weights
`sqrt(Pa*Pb)*gamma2` and `gamma2 >= 0.20`.  Pairing `+d` directly with `-d`
cancels the elected reference and even-in-z transfer; swapping the pair must
negate the coefficient field.

The nominal Welch phase floor is

```text
F0 = 0.5 * sqrt(weighted_mean((1-gamma2)/(2*M*gamma2)))
```

where `M` is the number of Welch blocks.  The bright repeats set
`q = median(A/F0)` per grid.  The predicted floor is `F=q*F0`; warm repeats are
held out.  The floor is commissioned only if warm
`median(A/F)` lies in `[0.75,1.33]` and at least 80% of warm records lie within
a factor of two.

For each outcome stack:

```text
R = median(A/F)
E = median(sqrt(max(A^2-F^2, 0)))
```

with a 10,000-draw bootstrap that resamples tiles and keeps all five offsets of
a tile together.  The one number governing reads 2/3 is the smaller of the two
stackwise 95% lower bounds for `R`.

* both stacks have point `R >= 2.0` and lower bound `>= 1.5`:
  reads 2/3 **SURVIVE**;
* exactly one stack passes: reads 2/3 are **NARROWED** to a scene-dependent
  effect;
* neither passes: reads 2/3 **KILL** at this phase-0 sensitivity.

`E` is reported in radians but does not gate.  Equal-area inner/middle/outer
field-annulus values are reported without selection.  Positive RMS can be
fooled upward by unmodelled local deformation or scene change; the repeat floor
and grid ladder control noise, not those physical confounds.  Therefore this
lane establishes existence, not attribution to a particular Zernike term and
not a recovered pupil.

### 5.3 Read 4 — inversion census

Each of the ten off-peak tiles is also crossed against the elected peak.  After
linear-ramp removal, a band correlation is

```text
rho_band = sum(real(C)) / sqrt(sum(Pa)*sum(Pb)).
```

A tile/band/side is inverted only when point `rho_band <= -0.20`, its
Welch-block bootstrap 95% upper bound is below zero, median coherence is at
least 0.20, and at least 12 legal bins enter.

The occlusion mask never reads this statistic.  On the fixed 14-by-18 grid a
selected tile is an occlusion candidate when its **low-band** peak differs by at
least 10 frames from a four-neighbour.  A fixed toroidal mask shift of
`(+3 rows,+5 columns)` is the placebo.

Read 4 passes only with at least 20 eligible occlusion tiles, at least five
independent inverted occlusion tiles, Wilson lower 95% inversion fraction above
1%, and tile-bootstrap lower 95% occlusion/placebo risk ratio above 2.  With
adequate coverage but no pass it KILLs; with fewer than 20 eligible occlusion
tiles it is INDETERMINATE.

The census can be fooled upward if a low-band depth jump and high-band phase
failure share scene geometry despite disjoint bands.  The shifted-mask placebo
measures that exposure; it does not turn the mask into ground truth.

## 6. Lane verdict

The four-read mapping is fixed:

* **SURVIVE** — reads 2/3 pass on both stacks;
* **NARROWED** — reads 2/3 do not pass both stacks, but read 1 or read 4 passes,
  or odd phase passes on only one stack;
* **KILL** — reads 2/3 fail on both stacks, reads 1 and 4 fail with adequate
  coverage, and all mandatory controls pass;
* **NOT ROBUST** — the above classification changes on either Fourier-grid
  ladder, the held-out floor calibration fails, fewer than 160 strong tiles are
  available, or a mandatory commissioning control/plant fails.

No post-hoc statistic can promote the verdict.  A failure may narrow it.

## 7. Commissioning before outcomes

`src/commission.py` runs before `src/measure.py`.  Its controls are fixed:

1. an untouched real RAW patch read through two integer-offset crops; the
   external coordinate difference fixes sensor `(dx,dy)` without any image
   generator;
2. a SciPy spatially shifted real patch at a fixed sub-pixel displacement;
3. an independently generated Hermitian phase-only odd transfer;
4. an independently generated even Gaussian-blur ladder, which must read null;
5. a full contrast inversion, whose estimator ceiling must read `-1`, not merely
   “negative”;
6. exact frequency-grid/boundary bin counts against an independent enumerator;
7. analytic Gaussian-noise phase-floor coverage;
8. rawpy geometry/levels against the shipping Rust/rawler `strehl probe`.

The planted defects are: shift sign; axis swap; sensor/GQ unit conversion;
frequency scale ×2; omitted phase-ramp removal; magnitude-only cross-spectrum;
negative-correlation clipping; and phase floor ×0.5.  Each plant must be shown
to land and make its target control RED.  A green control that has never fired
does not count.

The fixed-crop control and Rust probe are cancellation-immune: their predicates
come from coordinates or a decoder the estimator never touches.  Synthetic
controls are separately generated and never import `xspec_lib`.

## 8. Bias declaration (rule 18)

| choice / failure | direction |
| --- | --- |
| selecting the strongest 200 modulus tiles | falsely large phase; favours SURVIVE |
| residual translation/deformation after ramp fit | falsely large odd phase; favours SURVIVE |
| scene evolution between `-d` and `+d` | falsely large odd phase; favours SURVIVE |
| coherence threshold | drops noisy coefficients and can make phase falsely small; favours KILL |
| principal-angle wrapping | caps large phase at `pi/2` after halving; favours KILL |
| repeat motion or lighting drift | inflates the floor; favours KILL |
| fitted ramp absorbing real linear odd phase | makes residual phase small; favours KILL, but read 1 reports the ramp separately |
| low-band occlusion mask sharing scene geometry | can enrich inversion spuriously; favours SURVIVE |
| fixed shifted-mask placebo landing on real boundaries | reduces enrichment; favours KILL |
| one camera/lens/TC | cannot identify hardware generality in either direction |

The expected researcher bias is **toward SURVIVE**: C10 is the proposal's
highest-value unmeasured channel and a positive result is more interesting.
The registered bars therefore demand replication across both scenes and across
all three fixed frequency grids.

## 9. Rust consequence to be decided, not assumed

No Rust is edited in this lane.  A robust SURVIVE would justify a later,
separately gated complex phase observer beside
`crates/strehl-core/src/through_focus.rs`, wired from
`crates/strehl-cli/src/merge_cmd.rs`; read 4 would then need an admission hook
in the shipping `crates/strehl-core/src/pyramid.rs` path.  NARROWED permits only
the passing read.  KILL means none of those source changes should be made.

The final report must name the exact surviving module change, or explicitly say
why Rust remains unchanged.

