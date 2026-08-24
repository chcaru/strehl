# M95 arm 3 — pre-registration

Frozen before any result was looked at. Written 2026-08-24, after confirming only
two things: that the default render is 3516 x 2344 (8.24 MP) and the `--demosaic`
render is 7032 x 4688 (32.97 MP). No spectral or residual measurement had been run.

## The question

The default binned render collapses each 2x2 RGGB quad to one RGB pixel: red from
the R site, blue from the B site, green from `mean(G1, G2)`. The four sites are four
*different positions* on the sensor. Does the capture actually carry green detail in
the band that this collapse destroys, or does the optical system deliver nothing
there — in which case binning costs nothing and the softness is optical?

## The instrument, and why it needs no interpolation

G1 sits at (even row, odd col) and G2 at (odd row, even col). They are offset by
(+1, -1) full-res px = (+0.5, -0.5) binned px. For two samples at positions `p1`,
`p2`, the mean has transfer `cos(pi * f . (p1-p2))` and the half-difference has
transfer `i * sin(pi * f . (p1-p2))`. So:

* `S = (G1+G2)/2` is exactly what binning keeps.
* `D = (G1-G2)/2` is exactly what binning throws away.

`D` is computed from raw photosites. No demosaic, no resample, no upsample, no
model. That is the whole point: an instrument built on interpolation can be fooled
by the interpolator, and the orchestrator's own attempt failed that way.

`D` carries three things: real above-band optical detail, photon+read noise, and any
fixed G1/G2 sensitivity mismatch. The design separates them:

* **Noise** is matched by comparing regions at the **same mean signal level**, since
  shot noise is set by signal.
* **Sensitivity mismatch** is a fixed pedestal, removed by subtracting each region's
  own mean of `D` before taking variance.
* **Real detail** is then the only term that can differ between an in-focus region
  and a defocused region at matched brightness.

Headline statistic: `E = var(D_focused) / var(D_defocused)` at matched brightness.

## Pre-registered bars

| # | Bar | Threshold | What it decides |
| --- | --- | --- | --- |
| **B1** | `E`, in-focus vs defocused at matched brightness | `E >= 2.0` | Real green detail exists above the binned Nyquist, and binning destroys it |
| **B2** | | `E <= 1.2` | The optics deliver nothing there; binning is free and the softness is optical |
| **B3** | fraction of green sample variance in `D` | reported, no bar | how much of the signal is at stake |

`1.2 < E < 2.0` is an **inconclusive** band and I will report it as such rather than
picking a side.

## Controls, all required before the headline is allowed to stand

| # | Control | Must show |
| --- | --- | --- |
| **K1** *specificity* | synthetic scene band-limited **below** the binned Nyquist, mosaicked to RGGB | `D` variance at the noise floor; `E` near 1. Proves `D` responds to above-band content only, not to detail generally |
| **K2** *sensitivity* | synthetic scene **with** above-band content, same pipeline | `D` variance far above floor. Proves the instrument can say otherwise (discipline 594) |
| **K3** *dose-response* | real frame blurred by sigma = 0, 0.5, 1, 2 px before mosaicking | `E` must fall monotonically to ~1 |
| **K4** *null* | the same region compared against itself | `E = 1` exactly |
| **K5** *power / N-of-1* | run on >= 3 independent frames and >= 2 subject regions | the sign must not depend on which frame or region |

If **K1 fails** the instrument is measuring detail rather than above-band detail and
the headline is void. If **K2 fails** the instrument is deaf and a null means nothing.

## What would falsify the fix

If B1 fires and I then claim `--demosaic` recovers the detail, that claim is
falsified if **any** of these hold:

* **F1** The demosaic render's excess energy above the binned Nyquist is not larger
  than what the same demosaic produces when fed a mosaic built from an image that
  provably has no above-band content. (i.e. it is interpolation artifact, not signal.)
* **F2** The recovered detail does not survive to the eye at 100 %: if the crop shows
  no visible difference, the number is academic.
* **F3** The demosaic path changes which frame wins a pixel. It must not: it reads the
  same four accumulators the binned path reads.

## Scope declared in advance

This arm measures **green** only. Red and blue are sampled once per quad by the
sensor, so binning does not destroy R/B samples — it only mislocates them, which is
the defect arm 2 already fixed. Any resolution claim here is a luminance claim.
