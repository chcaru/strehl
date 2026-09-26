# Fixed planar focus-front proxy

ARGUED, frozen before photographic extraction. This experiment asks whether one
spatial focus front predicts through-focus contrast at withheld chip locations.
It does not infer metric depth, noise calibration, a lens PSF, or image quality
from a smooth fit. M67/M73 support structural falsification but retain smooth
wrong-field blind spots; M70 retains multimodality and off-peak information.
M145 does not authorize affine frame index for camera bracketing. V-DILUTE and
the rejected chip finest-source, harmonic and flat2 arms remain closed.

Input API: `fit_model(xy_native[P,2], contrast[K,P,2], train_mask[P])`.
Positions are normalized by the full fixed grid's coordinate extent, not by
image values. Sources remain in the original ascending frame order. The model
fits every frame of each training curve; no local peak or raw argmax is used.
All curves are toned, two-dimensional band-power proxies, not RAW-noise units.
The old M70 noise subtraction is not applicable to these developed TIFFs.

The response is `offset[p,b] + amplitude[p,b] * exp(-0.5*((t[k]-z[p])/s[b])^2)`,
with `z=a*x+b*y+c`, nonnegative amplitude and unconstrained offset. The single
monotone schedule `t` interpolates seven fixed uniformly spaced ordinal knots.
Its six positive increments are normalized to sum one; five log ratios in
[-2,2] and one fixed zero determine them. Endpoints zero/one fix translation and
scale gauges. The plane bounds are a,b in [-2,2], c in [-1,2]. Width is between
half a frame in the normalized schedule and 0.5. This finite family can fail on
actual optics and schedules; no additional knot, width-family or restart sweep
is permitted. A curved surface that is merely a monotone warp of one planar
projection is observationally confounded with the schedule; a genuinely
two-dimensional bowl is a required independent adversary.

Primary band alone fits the plane, schedule and primary width. At each optimizer
evaluation, training amplitudes/offsets are analytically profiled using all
training frames. Residuals are divided by each training curve's temporal RMS;
this is numerical scaling, not a noise estimate or eligibility criterion.
One deterministic initializer uses baseline-subtracted full-curve moments and
an ordinary least-squares plane. Positive clipping is confined to initialization;
the objective consumes the original signed residuals. This moment is not truth.
There is one bounded `least_squares` call, maximum300 evaluations, 1e-8 stopping
tolerances. One bounded scalar width fit (maximum96 iterations, tolerance1e-8)
then uses band1 training sites with the geometry/schedule frozen. No band1
observation can modify the learned front. These small parameter fits and
diagnostic reductions use f64; they do not change native f32 image arithmetic.

`predict_profiles(model, xy)` returns the two unit-response profiles.
`evaluate_profiles(model, xy, contrast)` fits only each site's amplitude/offset
on even ordinals and reports predictions/errors on disjoint odd ordinals. It
also reports an even-fitted constant predictor. A caller may supply explicit
disjoint calibration/scoring masks, which are returned in the result. Held-out
sites never fit a location, width or schedule. A second-band width learned on
training sites is prediction at held-out sites, not independent PSF calibration.
Optimizer completion, boundary flags and fit residuals are diagnostics only.

Independent controls own fixed predictive bars, planar nonuniform positive,
flat/noisy null, two-dimensional curvature, bimodal occlusion, shifted-front
destroyer and actual modulation/support eligibility. Weak or flat curves cannot
qualify merely because the absolute residual is small. A failure is retained;
there is no threshold, source, mask, initializer or model rescue sweep.

Source reuse is limited to saved299 same-developer TIFFs, held chip warp map,
the fixed sparse spatial extraction and existing bounded root runner. No
original RAW is read by this stage, no aligned image stack is materialized and
no candidate photograph is emitted. Even a successful proxy would need an
actual native coefficient consumer with fixed tone and whole-image inspection;
it cannot reverse the prior photographic failures by itself.
