# Bounded two-layer original-CFA inverse

Author freeze before execution, 2026-09-19. This is an **oracle-optics generated
reconstruction screen**, not a calibrated camera model, native product change,
general inverse-family verdict or SOTA claim. Root executes; an independent
agent supplies observations, controls and truth. No real RAW decoding occurs.
The complete canonical stacker comparison is deferred, not implied by beating
the deliberately narrower single-layer comparator.

`model.py` accepts original uint16 RGGB arrays `[N,H,W]`, three to nine frames,
native dimensions at most96. Only declared training indices are read, hashed,
interpolated for initialization or fitted. Array shape/dtype is inspected
globally; held-out values are not. Predictions on held-out focus settings use
only the supplied configuration. The likelihood does not demosaic observations.
Original storage remains u16; latent, current observation and arithmetic are
f32. There is no aligned-frame volume, mixed precision or silent CUDA-to-CPU
fallback. The pure forward seam can operate on CPU for independent mechanics.
CUDA convolution TF32 is disabled explicitly.

The latent is near/far nonnegative camera-linear RGB radiance, represented by
softplus, and a sigmoid near-layer coverage matte. Radiance may exceed digital
saturation. Inverse depths `(near,far)` are ordered and supplied, default `(1,0)`.
For source focus `f`, pupil point `p` samples each layer at
`(x,y) + defocus_scale*(f-depth)*p`, in native pixel-centre coordinates, with
identity pregeometry. This is a two-valued depth field, not inferred metric
depth. The first screen does not fit focus positions, pupil, diffraction,
alignment, per-frame gain or camera constants.

The fixed pupil has64 equal-weight points:32 golden-angle equal-area nodes
and their antipodes. Controls supply these locations explicitly through
`Config.pupil_points` to both the model and the independent SciPy generator.
The utility screen therefore tests the same declared discrete operator with
independent forward code. A separate1024-ray truth-forward comparison assesses
continuum adequacy; failure there leaves discrete-operator utility interpretable
but blocks an actual-optics/RAW license. Neither agreement calibrates the camera.
Bilinear `grid_sample(align_corners=True)` samples
premultiplied `alpha*nearRGB` and alpha at the near intersection, and farRGB
at the far intersection. For **each same ray**, output is
`sample(alpha*nearRGB) + (1-sample(alpha))*sample(farRGB)`. Average rays only
after this operation. Independently blurring alpha and radiance then composing
would be a different, wrong-visibility control.
The64 rays are batched into two `grid_sample` calls, retaining only one
observation's graph; this is not an aligned multi-frame volume. Apply the supplied common
Gaussian diffraction-floor PSF afterwards: sigma defaults.7 native pixels,
discrete normalized support radius `ceil(4*sigma)`, separable convolution.
This floor is a supplied approximation, not measured diffraction physics.
Finally sample native RGGB. No WB, camera matrix, tone or post-sharpening enters.

Common valid margin is the ceiling of the largest absolute ray displacement
over all supplied foci/depths, plus PSF radius plus one bilinear support pixel.
Training and independent truth scoring use that interior; outside predictions
have zero-padding semantics and no observational authority. No target-dependent
crop or learned support is allowed.

Predicted means include black512. Variance in DN² is injected
`gain*max(predictedDN-black,0)+read_variance+1/12`; neither parameter is fitted.
Uncensored observations use half of `log(V)+(observed-predicted)^2/V`.
Only digital16383 is upper-censored, using
`-log_ndtr((predictedDN-(16383-.5))/sqrt(V))`. Development white15360 has no
role; codes15361..16382 remain ordinary observations. Codes above16383 refuse.
This conditional Gaussian/tail approximation does not calibrate the physical
sensor or claim Poisson-exact tails. The1/12DN² term is an independent uniform
quantization approximation, not an exact clipped/quantized likelihood.
Lower-code clipping is outside this screen.

Optimization is fixed160 Adam steps with the same predeclared cosine learning
rate in both arms: `.001 + .5*(.03-.001)*(1+cos(pi*step/159))`, from.03 to.001.
This prospective schedule is not a measured tuning result. There is no
early-convergence claim. Each step immediately backpropagates each training
frame's **interior mean** NLL divided by training count; no multi-frame graph
is retained. This is a normalized penalized likelihood, not a summed-likelihood
MAP claim: the fixed relative prior does not shrink as more training frames
are supplied. Both model arms use this convention. Priors are applied once
per step. The RGB vector-Huber penalty is
dimensionless: `t=norm(delta_RGB_DN)/b`, `rho(t)=.5*t²` below2 and `2*t-2`
above2, with `b=sqrt(2*(gain*2048+read_variance+1/12))` DN. The2048DN signal is
a chosen prior reference, not a fitted scene constant or camera calibration.
Its small-gradient precision is1/b² in DN, so unlike an arbitrary tiny penalty
on unit-normalized intensities it competes with the DN likelihood precision.
Average horizontal/vertical edge penalties, then average radiance sheets,
with coefficient1. Alpha absolute spatial differences
average both axes, weight.02. Mean `alpha*(1-alpha)` has weight.002. Mean
squared radiance normalized by15871DN, averaged equally over sheets, has weight.0001.
The latter makes radiance/coverage compensation coercive, not identifiable.
No alpha-recovery claim follows from reconstruction success.

Initialization bilinearly interpolates training CFA only. Near/far start from
the highest/lowest supplied-focus training observations; alpha starts at.5.
The one-layer arm starts from the training mean and is fixed at supplied FAR
depth, with the same optics, NLL, image prior and optimizer. It is not the
best possible single-layer fit and cannot represent a near layer. A matched
far-only fixture is required. `optimize=False` exposes initialization only;
`forward`, `cfa` and `observation_nll` expose the mechanical paths.

FitResult returns camera-linear pinhole RGB `alpha*near+(1-alpha)*far` in
black-subtracted DN, both radiance sheets, alpha, persisted state and prediction
methods. History records training likelihood, prior, pre-update gradient norm,
learning rate and elapsed time each step. `iteration_limit` means exactly that. Adequacy,
optimization progress, held-out prediction, output truth and flat noise must
be interpreted separately; low fit residual cannot certify the latent image.
