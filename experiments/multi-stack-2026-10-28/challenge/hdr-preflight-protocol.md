# Bounded HDR feasibility preflight

PREPARED / UNEXECUTED. Root must release execution after the active full-session
geometry lane. This document does not enable an HDR product mode, authorize a
186-frame render, or establish photographic gain. No RAW pixels were read while
preparing it. The ordinary Combine contract currently refuses mixed exposure;
that refusal remains correct until radiometry and variance handling are tested.

## Frozen sample and resource boundary

Use hdr-preflight-manifest.json, derived from the existing corpus census. All
paths begin D:/personal/macro/requests/misc-diagnostic/high-res-calibration-slide-cpl/flat-sw4-cpl/.

| Directory | Exposure | Count | Zero-based sample indices | Filenames |
| --- | ---: | ---: | --- | --- |
| flat-et1s-sw4-cpl | 1 s | 60 | 0, 30, 59 | DSC00016.ARW, DSC00046.ARW, DSC00075.ARW |
| flat-et2.5s-sw4-cpl | 2.5 s | 61 | 0, 30, 60 | DSC00020.ARW, DSC00050.ARW, DSC00080.ARW |
| flat-et6s-sw4-cpl | 6 s | 65 | 0, 32, 64 | DSC00015.ARW, DSC00047.ARW, DSC00079.ARW |

The census records ISO100, f/5.6, Sony ILCE-7CM2 and the same lens family. The
6 s pass was acquired first, then 2.5 s, then 1 s; time and exposure are therefore
confounded. These are first/middle/last coverage probes, NOT same-focus triples.
Unequal counts or normalized file rank cannot prove matched optical state.
The manifest binds all nine previously measured whole-file SHA256 identities.

Stage A is nine sequential rawpy decodes, one worker, at most one full active
copy and bounded row/tile temporaries resident. Reserve 1 GiB process memory;
stop and report if the actual decode footprint exceeds it. Do not infer a
hard process cap from this estimate. Save at most nine original u16 active CFA
arrays and receipts (under 1 GiB total), never an aligned float frame volume.
No cache eviction, capture sidecars, production render or full-stack alignment.
Write only to a fresh outputs/multi-stack/hdr-preflight directory. Record exact
command, Python/rawpy/LibRaw/NumPy versions, code hash, worker/environment values,
wall time, sampled owned-process memory, exit status and artifact completeness.
Use python -X faulthandler for the eventual helper invocation.

## Stage A: source, decoder and clipping commission

1. Before each decode, hash the entire RAW in bounded chunks and compare the
   frozen expected SHA256. Record length and modification time before and after
   hashing/decoding; abort on an identity change. Reject duplicate full hashes.
2. Inside a rawpy context, copy raw_image_visible into an owned C-contiguous
   uint16 array. Copy active dimensions/origin, raw dimensions, visible 2x2 CFA
   color indices, black levels, scalar and per-channel white levels, color
   description and relevant camera calibration metadata before closing it.
   No white balance, demosaic, normalization, gamma or automatic brightening.
   Assert the owned array survives the closed context and retains its checksum.
3. Hash the entire active payload with explicit little-endian u16 row-major
   order, dimensions and absolute active origin. Read back any saved original
   active array and require bit-exact equality. Preserve below-black values;
   clipping tests use original integers before subtraction or exposure gain.
4. Check the independent decode against the production decoder's untouched
   source cache for the same whole-file identity. Root must separately release
   cache population if these nine sources are not cached. Match absolute sensor
   coordinates and CFA color labels, not array shape alone; report differing
   active rectangles. Compare all overlapping u16 samples exactly, with mismatch
   count/max and per-color summaries. A disagreement blocks cross-decoder numeric
   claims until explained; a second read with the same decoder is not independent.
   Reading Strehl's owned cache format is allowed; do not inspect rawler source.
5. For each of four CFA sites report sample count, original min/max, exact upper
   histogram bins, black-subtracted p0.1/p1/p50/p99/p99.9, and count/fraction at
   or above the recorded site white level. Also report within 1/4/16 DN of white
   as separate proximity diagnostics. Do not relabel those proximity bands as
   confirmed clipping or infer sensor clipping from an encoded white pixel.
6. Save a complete low-resolution spatial map of measured clipped-site fraction
   from fixed 64x64 sensor blocks, plus per-color block means/counts. These are
   orientation/coverage diagnostics; no detail claim from a resized overview.
   Record all original coordinates. Fix the display from the 1 s pass alone and
   reuse it for all exposure-normalized views. Disable per-image autolevels.

Exercise the evidence helper before source conclusions: a known u16 array with
per-color black/white differences, negative black-subtracted samples and exact
white/white-1/white+1 samples must produce exact counts. Swapping CFA phase or
using a wrong active offset must fail the independent-decoder check. A copied
file under a new path must fail duplicate independence. These bounded synthetic
controls commission decoding/measurement mechanics, not the camera response.

## Stage B: bounded radiometric and coverage screen

Only after Stage A identities/decodes pass, and only within the same nine copied
original arrays, inspect whether a useful HDR comparison is possible. No new RAW
selection is allowed merely because an unfavorable sample was observed.

The fixed nominal reference is 1 s. Black-subtracted source value z_j maps to
reference units as y_j=g_j*z_j with g=(1, 0.4, 1/6). For an injected source noise
model V_j(z), the normalized variance is g_j^2*V_j(z), followed by the actual
warp/filter propagation. Evaluating a shared noise curve at y_j alone is wrong.
Different exposure time may add dark current/hot pixels; this corpus has no
same-focus temporal repeats or dark series that independently calibrate them.
Do not fit a private per-stage noise model from spatial chart variation.

First establish broad common geometry using bounded block guides and direct
pairwise placement, with coordinate/gauge/scale receipts. It may be impossible
for first/middle/last samples to share useful in-focus detail. Do not pair solely
by rank or reuse a transform from a different exposure pair. This preflight
requires only large uniform chart interiors for photometry; they must be far
from edges, glints, clipping and the measured alignment uncertainty. A visually
flat chart patch can still have reflectance/illumination structure.

Freeze at least twelve disjoint broad interior patches spanning positions and
signal levels from the 1 s view, before exposing residuals. Reserve half by a
fixed spatial split as validation patches; separate them from any alignment
fit tile plus its complete filter/warp footprint. Fit at most one scalar ratio
per exposure pair on the calibration patches, using robust per-color interior
means/medians. Report per-color and per-position residuals on held-out patches,
as well as nominal shutter-ratio residuals. Never validate the scalar using the
same values that fitted it. If a channel/position-dependent gain is needed, the
proposed scalar exposure model has failed; expose layers until a justified
calibration model and independent controls exist.

A provisional engineering screen is held-out median relative residual <=1% and
95th percentile <=3%, with denominator bounded away from black. These are
explicit product tolerances, not a calibrated statistical test. Report the
entire distributions and sensitivity at 0.5/2% and 2/5%; do not tune thresholds
on these nine images to declare success. Compare first/middle/last independently
within each exposure to expose drift/focus confounding. Failing or lacking enough
independent flat patches yields INCONCLUSIVE/DECLINE, not a calibration success.

Negative controls must fail the screen: a 10% wrong nominal exposure multiplier,
a planted spatial half-field gain, and a channel-specific gain. The scalar fit
could hide a uniform wrong multiplier, so its placebo is checked against the
fixed nominal shutter ratio before any refit. A copied reference passed through
the same gain arithmetic is the positive no-change control. Registration shift,
blur and lighting changes must not be interpreted as noise reduction.

Report highlight opportunity only where the longer source has measured original
clipping and a shorter source covers the same broad region with unclipped,
above-noise signal. List color-specific coverage: an unclipped green sample does
not recover clipped red or blue. Without subpixel placement and compatible focus,
this is only potential recoverable area, not recovered detail. If no such overlap
is present, these nine frames cannot validate HDR recovery. If every exposure
clips a location, preserve honest primary/coverage fallback with no recovery claim.

## Advancement decision and later implementation controls

Advance to a separate root allocation only if the exposure model is supported,
useful complementary unclipped coverage exists, and geometry/focus mismatch can
be bounded. Otherwise retain aligned layers and a precise reason to decline.
The screen cannot certify independence, temporal noise gain, native resolution,
full-stack focus coverage or photographic quality.

An eventual HDR consumer needs exposure-normalized source coefficients AND
absolute variance, original per-color clipping eligibility, coverage-only honest
fallback, and focus-aware compatibility. Equal-weight Repeat fusion is not a
variance-optimal HDR estimator. Inverse-variance averaging is valid only within
accepted compatible same-focus observations; applying it across different focus
states can prefer sharpness loss. Optional primary remains the framing/appearance
anchor and disagreement fallback, not permission to suppress valid complementary
focus or pretend clipped primary values contain detail.

Before a real HDR claim, require planted exposure/noise/clipping controls with
known radiance, exact no-op equal-exposure/single-source controls, wrong-exposure
and motion/focus rejection, copied-source refusal, all-clipped coverage fallback,
actual output-domain variance checks, and complete full-resolution masters under
one fixed display transform with independent native-crop review. Do not claim a
noise gain from spatial standard deviation, gradient energy or shared-bias FRC.
