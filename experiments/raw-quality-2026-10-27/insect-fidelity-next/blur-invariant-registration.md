# Blur-invariant registration: a specific untested reader

2026-10-27. SOURCE-VERIFIED / DERIVED / ARGUED only. No numerical work, RAW
decode, import, build or implementation. **The named precedents do not test
Ojansivu and Heikkila's even-power estimator. One bounded original-CFA reader
comparison is justified; a replacement map is not yet justified.**

## What is actually new here

The primary [2007 SPL paper](https://doi.org/10.1109/LSP.2006.891338) introduces
blur-invariant phase correlation. The authors' accessible
[2007 EUSIPCO paper, section4/equation6](https://www.eurasip.org/Proceedings/Eusipco/Eusipco2007/Papers/c5p-j01.pdf)
restates its translation operator. For images related by translation and
centrally symmetric shift-invariant PSFs, the PSF Fourier responses are real.
Their phase is0 or pi; squaring the normalized cross-spectrum removes that
sign while doubling the translation phase. The recovered shift must therefore
be divided by two. This is a published algorithmic fact, not an implementation
borrowed from another repository. No external implementation was consulted.

For `I_j(x)=I_i(x-d)` before blur, choose
`p=F_j*conj(F_i)/abs(F_j*conj(F_i))`; inverse-transform `p*p` peaks at2d under
the stated ideal model. Zero-magnitude bins provide no phase information.
An exact Gaussian with positive transfer already cancels in ordinary phase
correlation: the distinctive positive control needs transfer sign inversions,
such as a symmetric finite disk, not Gaussian blur alone. Squaring does not
restore frequencies destroyed by blur and doubles phase noise as well as shift.
Discrete shifts are now ambiguous modulo half the transform period.

## Retained predecessors, with their actual estimators

| Record | Actual producing path and finding | Answers squared spectrum? |
| --- | --- | --- |
| [M-PHASE0-XSPEC](../../../docs/research/M-PHASE0-XSPEC.md), `src/xspec_lib.py::fit_phase_shift` | Welch mean complex cross-spectrum; coherent low-band coarse search followed by weighted **first-order** phase-ramp least squares. It does not square the unit cross-spectrum. Bee/text registration split repeatability0.20053/0.07203 native pixels versus spatial0.07253/0.04244 on grid64. Overall NOT ROBUST, not a scientific family kill. Its `abs(cross)^2` is coherence, not the BIPC phasor. | No |
| [BUILD-CHROMA common.py](../../BUILD-CHROMA/src/common.py), `phase_shift_ref`; [lateral.py](../../BUILD-CHROMA/src/lateral.py), `subpix` | The former inverse-transforms ordinary normalized cross-power and returns an integer shift. The latter deliberately uses unwhitened upsampled correlation (`normalization=None`): ordinary whitening shrank small planted shifts, and weak tiles lost lock. | No |
| [M78](../../../docs/research/M78-blur-equalised-edges.md) | Gaussian cross-blur before inherited spatial correlation, plus a separate half-pixel sampling treatment. Conservation improved while held prediction worsened7.241426 to7.266073/7.244330 plane pixels. Added filtering is an instrument, not evidence of physical correction. | No |
| [M116 geom_check.py](../../M116-promotion/geom_check.py), `shift_of`; [ca_calibrate.py](../../M116-promotion/ca_calibrate.py) | Ordinary normalized cross-power for integer developed-image gauge checks; unwhitened upsampled correlation for colour displacement. Neither estimates squared-spectrum same-colour original-CFA residuals. | No |
| [Current observer](../insect-placement-observer/results.md) and [held field](../insect-field-stability/results.md) | Current spatial NCC has2340 attempted pairs/2314 accepted edges. The three-site constant residual-per-step model fails10/12 held populations; all six replication cells worsen. Residuals and overlap are not physical-error truth. | No; rules out installing that stationary correction |

This is a scoped absence finding from those actual sources, not a claim that
every repository file or every phase method was searched. The current failure
does not establish that contrast inversion causes weevil softness.

## One fixed, direct-original-CFA discriminator

Use the already independently checked original-u16 caches, not MHC, RGB,
green averaging or resampled source frames. Take G1 and G2 separately at their
actual sensel offsets. Each reader uses a128x128 same-phase rectangle
(256x256 native extent), with integer origins selected from the existing
map-predicted patch centres. No geometric interpolation enters this first
reader. Retain the exact physical origins and compare predicted and measured
centres in source-i/source-j native coordinates; the map is an initial gauge,
not truth. No cross-colour geometry assumption is needed.

Freeze the existing sites15/41/56 and source intervals0..95,112..207,224..298.
Within each interval, starts are its first index plus multiples of16; use
spans1,8,32 only when both endpoints remain in the interval. Preserve every
requested pair and refusal. This reuses the observed three distinct subject
regions without pretending that a residual field is stationary in focus.
Span32 is an adverse for changing focus/scale, not a substitute winning cohort.

Compare just two readers on **identical** mean-removed Hann-windowed samples:
ordinary `p` versus squared `p*p`. Fix the band0.02..0.20 cycles/native pixel,
strictly below the same-phase axial Nyquist. Use the same injected NoiseModel
to calculate windowed Fourier noise power `N=sum(w_window^2*variance)` per
source/phase. A shared frequency weight is the product of the two bounded
signal fractions `max(P-N,0)/(max(P-N,0)+N)`; unsupported/zero bins contribute
zero. This is a declared reliability heuristic, not calibrated independent-bin
likelihood. It applies unchanged to p1 and p2. No extra spectral floor is fit.

Search only the fixed residual box+/-2 native pixels around the held centre
prediction, maximizing the real part of the weighted complex sum on a1/64-native-pixel
grid. Retain the entire local score/peak ambiguity, not only its maximum.
For p2, evaluate the doubled phase ramp and divide the inferred same-phase
shift by two before converting its two-native-pixel lattice units. Exact
sign, unit, half-period and physical-G offsets need live wrong-sign/factor-two
foils. Flat/noise or unresolved peaks refuse rather than return zero motion.
The same noise/peak protocol and thresholds must be frozen by independent
controls before the first real reader run; this memo does not authorize it.

**Identifiability limit:** these are unresampled local translation readers.
Real focus breathing leaves scale/rotation across each patch, and sensor
sampling can alias a sharp feature. Known similarity at the centre does not
remove either effect. Cropping/windowing also breaks the global convolution
identity. Thus agreement, a sharper score peak, reverse consistency or lower
NCC residual cannot alone identify physical displacement. G1/G2 are two
sampling phases, not independent copies of one calibrated noise experiment.

## Required failure controls and the complete-image route

Before actual interpretation, use independent continuous, sensel-integrated
same-colour scenes with signed subpixel displacement, source noise after blur,
and the **measured nonlinear focus-breathing track curvature**, not a straight
endpoint chord. Run zero shift/noise first, then a symmetric-disk contrast
inversion positive and Gaussian-positive-transfer companion through these
same readers. Include fixed scale/rotation within a patch and finite-window
edge structure. A zero-geometric-shift asymmetric PSF, changing two-depth
occlusion, and bright specular structure must not yield an accepted confident
physical correction merely because p2 sharpens its peak. A shift and an
asymmetric PSF phase ramp can be observationally indistinguishable; such a
case requires an explicitly ambiguous/refused interpretation, not a claim
that a universal scalar guard can distinguish them. Preserve weak green and
independent colour structures in the eventual complete-image comparison.

If the bounded reader has a useful controlled accuracy/coverage advantage and
the fixed actual populations support it across G phases and held intervals,
the next release is one **direct-edge** map experiment: apply the same reader
to the existing spatial tile population/span graph, fit the existing similarity
model per pair, and use the unchanged robust global solve in anchor149's
connected component. Do not chain corrections, omit short spans wholesale,
extrapolate the three-site field, or turn one-reference residuals into a map.
Preserve failed tiles/edges and selected populations. Check cycle rank before
using cycle consistency; retain held spatial/edge prediction and assess every
frame's placement in the actual merge gauge, not just first-to-last error.
Neither self-consistency nor actual-data residual supplies missing ground truth.

That map, if separately released, feeds **one complete all299 weevil replay**
with unchanged fusion, CA-off, development and baseline replay. Show the full
master/complete image and all ten fixed witnesses against the current map and
HeliconB4/B8. Useful hair/scale/occlusion fidelity with retained colour is the
decision; small phase or graph scores are insufficient. The registration reader
is original-CFA-native, but the unchanged legacy renderer's earlier MHC/remosaic
limitation remains disclosed. No optical-ceiling, corrected-placement or image
quality claim follows from this source audit, and no additional estimator
variant or calibration sweep is selected.
