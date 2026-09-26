# Independent fixed-front quadratic-intercept screen

Frozen before execution, 2026-09-25. This is a tiny standalone falsifier of the
actual f32 operator, with four tests and no original RAW, canonical consumer,
MHC writer, native photograph, parameter search or reconstruction promotion.
Root owns execution. The unchanged Gaussian radiance operator is the comparator.
The old two-band focus-front proxy remains failed. Local polynomial regression
is established arithmetic, not a novel reconstruction or proof of physical PSF.

All frames retain the supplied front, schedule and width. For normalized offset
delta=(t-z)/sigma, fit degree two with q=exp(-delta²/2), reconstruct its intercept,
and apply the same signed equivalent weights to R/G1/G2/B. No clipping, source
subset, alternate degree, width selection or Gaussian fallback is allowed.
Whole-output refusal is required if any pixel has nonfinite quantities, deficient
rank, dimensionless infinity-norm condition >1e4, or less than 1% of Gaussian
mass on either side of the predicted center. These are prospective arithmetic
and support limits, not physical adequacy guarantees. A support failure and a
quality failure must remain distinct in saved results.

The independent noise policy allows the unavoidable polynomial penalty; it
does not demand equality to the Gaussian. At every accepted positive-fixture
site, actual sum(h²) must be <=2.0 times the unchanged Gaussian sum(g²), and
<=0.75 for unit independent source variance. This is intentionally above the
dense interior theoretical ratio 27/16 and still requires averaging benefit
over one source. Both constraints are scientific screening bars, not hidden
operator fallback. Direct summation of exposed actual h² must agree with the
operator's moment-derived variance within relative 0.2%. Original noise draws
are independent across channel/source/pixel, fixed 20-DN standard deviation.
Flat reconstruction runs first, and its observed MSE must lie within 10% of
the actual propagated variance, computed using these same weights and the
independently known injected variance. This validates propagation only, never
camera calibration. No private stage noise estimate is allowed.

Four tests:

1. `b_moments_and_dense_oracle`: independently solved small f64 normal equations,
   plus constant/linear/quadratic reproduction at high DN, commission the actual
   f32 stream within 0.02-DN absolute error. These exact-family fixtures are
   arithmetic controls only. The actual equivalent weights must be signed and
   reproduce moments [1,0,0] within 2e-4. A wrong intercept row is a destroyer.
2. `c_support_refusal`: two-source rank deficiency, one-sided center, negligible
   opposite-side mass, repeated/missing order and invalid samples must refuse.
   No apparently good placeholder image may count as a reconstruction.
3. `a_flat_and_unchanged_nonquadratic`: preserve the prior 33-source, 64x48-plane
   sinusoid, its nonuniform schedule, spatial front, 0.045 width, 0.65+30|t-z|
   local blur and exact fixed noise draws. After flat/noise checks, candidate
   radiance MSE must be <=0.90 of the unchanged Gaussian on this nonquadratic
   signal. Wrong front (both spatial slopes reversed, with center/range held)
   and erased detail must fail that same
   signal's positive criterion; a support refusal is reported explicitly and
   is not counted as successful wrong-front prediction.
   This pre-execution choice replaces the older +0.35 destroyer because that
   shift exceeds source endpoints and would exercise only the new support
   refusal. The unchanged source stimulus is never refitted to the destroyer.
4. `d_contact_depth_and_overshoot`: retain the earlier bright contact rectangle
   at native [108,116]..[140,164], its coloured sinusoidal surround and analytic
   finite-edge CDF. Use 33 fixed frames, front center 0.5, width 0.045 and blur
   0.65+32|t-0.5|. Also retain the near-fine/far-coarse additive structure with
   known distinct focus coordinates 0.3/0.7; the front stays at the known
   fine-detail coordinate 0.3. These are fixed known-depth adversaries, not a
   claim that a planar front represents two surfaces at the same pixel.
   In both cases require per-plane and green/chroma RMSE <=1.05 Gaussian,
   focused-template recovery >=98% Gaussian (clipped to [0,1] only for that
   retention score), and no more than 1% of the known contact step outside the
   analytic radiance bounds. Signed overshoot is measured before any clamp.
   A separate bounded temporal input set to high radiance exactly where h>0
   must exercise overshoot and be rejected by that same range check; this is
   a metric destroyer, not a physical scene or automatic algorithm rejection.

Pre-execution coverage amendment: names are prefixed a/b/c/d so the runner's
single-thread alphabetical order executes the flat control before any detail
test. The same per-site noise policy also applies to both adversary fronts.
Contact no-harm/retention applies separately to the retained native windows
interior [112,120,136,160], edge [92,100,158,180] and outside [142,118,164,162],
in addition to the whole field. The two-depth protection uses the existing
joint two-template regression, including off-diagonal covariance, to require
98% retention of each near/far component in every plane; a larger component
cannot conceal loss of the other. Both baseline component recoveries must be
at least 0.1 and both truth templates must be live and independently resolvable.
These choices were fixed before any measurement, without changing stimuli.

RMSE can reward smoothing, hence noiseless truth, flat first, focused-template
retention, and wrong-front/erased controls are separate. A positive may fit this
analytic local-blur approximation without representing a physical occlusion
PSF. The two-depth adversary asks whether the same reconstruction causes harm
outside its single-surface model; its failure cannot be hidden by the planar
positive. All numerical results and decision booleans are saved before any
scientific failure is returned. Numerical/test completion is not admission.

Root explicitly defers canonical-consumer comparison to keep this falsifier
small. If every present bar passes, unchanged-canonical detail/no-harm and
actual gathered-noise propagation remain **unmet next gates**, before any
separately scoped complete-chip observation. A failure closes this fixed
intercept recipe; no degree, width, support, conditioning or threshold rescue.
