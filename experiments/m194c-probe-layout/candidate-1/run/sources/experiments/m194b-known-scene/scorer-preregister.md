# M194b scorer: frozen first scope

2026-09-07. Written before implementing or running this scorer and before
viewing production benchmark outputs. Author: root. Independent verifier:
roadmap_audit. Baseline source: M194 commit
`19e230fbd44f58badd0959906ae1f1eb5519c60a`.

The committed `review-production-truth/forward-model-plan.md` defines the
flat/plane/color scenes and the distinction between ideal latent target,
in-focus observation target and available single-frame algorithm comparator.
This implementation covers those first three scenes only. No occlusion or
physical PSF claim is licensed by it. M25 source will not be imported by the
scorer; target equations are evaluated directly on the declared canonical grid.

## Fixed mapping and normalization

Decode actual RGB16 TIFF pixels. Convert to black-subtracted camera-linear DN
by multiplying by `(15360-512)/65535`; never subtract black again and never fit
an output gain/offset. Check the declared output mode, exact dimensions,
finite coordinates, three channels and all input/plan/output bindings. Pixel
`(u,v)` maps to canonical native `(u+2*crop_x,v+2*crop_y)`. The fixed main window
is x in `[64,256)` and y in `[64,176)` on the 320x240 native grid. Refuse if it
does not survive the recorded actual crop. No image registration or ROI moving.

For the scalar scenes account for the explicitly consumed f32 WB multipliers:
target channel factors are channel_scale times WB. Target ideal aperture is
continuous unit-cell integration. The producer's S=4 in-focus observation
target uses the exact finite midpoint aperture sum and independently evaluated
circular pupil overlap diffraction formula. Include both targets by name; an
ideal target is not an attainable floor. The analytic color target uses its
declared continuous aperture with exact frozen coefficients, and the producer
must record which convention it consumes.

## Quantities and how they can mislead

Report channel-wise RMSE, signed bias and MSE against each named deterministic
target. Noise can obscure lost signal and blur can improve noisy MSE, so MSE
alone does not establish preservation of texture. For the textured plane,
report amplitude and phase of both frozen waves by joint least squares with
a constant and sine/cosine terms on the same fixed mask. This is a readout of
specified waves, never a fitted normalization of the scored image.

For eight independent noisy repeats, compute sample temporal variance per
pixel (`ddof=1`) and pool over the same mask. Report repeat MSE mean and its
standard error across the eight entire-image observations. Image pixels are
not independent samples for uncertainty. Report error of the repeat mean and
verify the algebraic identity
`mean_repeat_MSE = mean_image_error^2 + 7/8 * pooled_sample_variance`.
Label this identity arithmetic rather than independent evidence. Also report
the finite-repeat subtraction `pooled_sample_variance/8` and the untruncated
estimate of squared bias; a negative estimate remains negative.

Do not use spatial standard deviation as temporal noise. A single noise-off
render has no temporal variance estimate. Per-repeat and overall rail counts
are disclosed separately; the normal fixtures must have no clipped rails.

## Commissioning before baseline

Use a different 144x112 aspect ratio and nonzero integer coordinate origin for
scorer component controls. Unchanged exact target and empty mutation have zero
error. A +20 DN channel offset must read +20 bias and 400 MSE in that channel
within 1e-8. R/B swap on a target with distinct spatial chroma must have positive
error; a known phase shift must change recovered phase without changing the
specified target. A 0.6-pixel Gaussian on a noise-free nonconstant periodic
target must reduce the known wave amplitude and increase target MSE; the same
operation on a constant flat target must preserve it. These controls do not
imply every blur worsens every noisy production MSE.

Independent zero-mean Gaussian noise of sigma=8 DN, seed 81271, on 64 flat
repeats must have pooled temporal variance within 3% of 64 DN^2. Average
16 independent copies per repeat using seed 92147; variance must agree with
4 DN^2 within 3%. The ratio is accompanied by per-repeat MSE standard errors
and the absolute null/control values. Deliberately identical noisy repeats
must have zero temporal variance while retaining nonzero MSE. Spatially
structured noiseless repeats must likewise have zero temporal variance.
Malformed/nonfinite inputs and an empty ROI are refusals, not scored zeros.

Changing a output pixel, a metadata-only TIFF byte, a crop origin or a same-size
false map must be caught by the appropriate file/pixel/mapping binding rather
than assumed harmless from dimensions. Those end-to-end controls depend on
the final consumer schema and will be commissioned before publishing a
baseline. The independent verifier re-chooses scene and coordinate settings.

All tolerances above precede outputs. Retain every failed invocation. No SOTA
bar or historical score is changed. A control that fails withholds its
dependent measurement; it is not repaired by changing the acceptance sign.

## Paired-summary addition before production outputs

After the first scorer component controls, but before paired-summary code or
any production benchmark output: compare full9 and single4 with per-repeat MSE
differences using the same seed. Report their mean and SEM across the eight
paired whole-image observations. Do not sum independent-arm uncertainties for
these paired inputs. Temporal-variance differences use a delete-one-repeat
jackknife standard error, with the raw leave-one-out values retained; it is a
small-sample diagnostic rather than a precision certificate. No acceptance
threshold or baseline setting changes. An identical pair must yield zero
difference and uncertainty; independent noisy versus constant repeats must
have a positive variance difference. Neither arm is called a truth oracle.
