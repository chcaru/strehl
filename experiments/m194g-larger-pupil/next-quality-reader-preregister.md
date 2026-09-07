# Prospective independent quality reader

2026-09-07. **Design/source preparation only.** No target, private instrument,
TIFF decode or quality quantity has been computed. Root review and separately
committed source/commands precede each stage. This concretizes
`next-quality-design.md`; it changes no merge/noise parameter or seed.

## Three separate stages

1. Target: one new native320×240 K=0 scalar expected-electron array and a
   source-bound receipt. Reuse only `clip`, `moments`, `polygon_fourier` and
   `sinc` from frozen M194e `independent-model.py`, SHA
   `0cd8ea2331b269e65befdee110560cbc345e89c12348cbe1dc3144f7c04443f0`.
   A new narrow wrapper specializes the coupled cell integral to K=0; it
   calls no pupil quadrature, author renderer, hybrid or Bessel implementation.
   The source module's imports are not evidence of a quadrature invocation.
   Root independently reviews and checks the target before output scoring.
2. Instruments: fixed private scalar/metric/TIFF fixtures below. This stage
   cannot admit any candidate TIFF or substitute for genuine target/bridge
   authority. Its status names instrument commissioning only.
3. Scoring: the exact independently admitted38-output matrix, after target,
   instrument, noise and bridge commissioning. Its completion status means
   complete diagnostics, never candidate quality acceptance or promotion.

Each stage has one non-resetting120 CPU/240 wall-second budget beginning before
imports,32MiB live named backing ndarrays, and no image volume over repeats.
Target/instrument output ceilings are64MiB; scoring32MiB. These are proposed
engineering refusal limits before computation, not throughput predictions.
The scoring ceiling is256 bounded TIFF decodes, including rereads for
delete-one calculations; no input/output is dropped to meet a cap. Private
instruments have at most128 TIFF decodes. Target covers exactly76800 native
cells; at most128 additional private target cells are permitted. All artifacts
and failed attempts are retained within their stage ceiling.

## K=0 target and independent controls

Use the genuine full-float commission's fixed fixture scene and identity map.
For native centre z, clip the offset square[-.5,.5]^2 by
`n dot u >= offset-n dot z`. Let A,m,C(k) be its area, first moment and Fourier
integral. Foreground uses A,m,C; background uses1-A,-m,C_square-C, where
`C_square=sinc(kx/2)*sinc(ky/2)`. For each layer integrate its constant, affine
term and both declared waves with the native centre phase. Add the two layer
integrals before recording the scalar. No centre-mask or separately averaged
alpha/background approximation is allowed. No coordinates are snapped.

The target receipt binds the registered fixture, genuine full-float authority,
source/runtime identities, exact K=0 model and a C-order NPY `<f8[240,320]>`.
It records expected electrons before CFA/quantization. All values must be
finite/nonnegative. It supplies no adaptive error estimate: this is a closed
cell formula whose floating implementation requires the following controls.

Root's independent check must cover at least the fixed actual scene cells
`(142,0),(142,1),(143,7),(150,53),(151,64),(152,64),(159,117),(160,117),
(169,179),(178,239)`, including boundary-crossing cells. Compare with Socrates'
separate analytic x-integral and one-dimensional y quadrature, split at actual
cell/half-plane crossings, with no polygon or author/hybrid imports. Its fixed
absolute request is1e-7e per cell, epsrel0; warnings or excessive indicators
refuse. Reuse the existing0.004e max/0.0008e RMS comparison bars; target
source and full population remain unchanged if a point fails. Its exact
command and own cost cap need root registration before execution.

Private analytic controls use constant full/empty/mixed cells, square Fourier
transfer including a zero-frequency limit and a negative sinc lobe, and affine
coupling. Two literal coupled examples at native centre(113,117) are:
foreground30, background`10+4*(x-113)`, vertical mask`x>=113.125`, exact17.03125;
and normal(1,1), local threshold.25, same fields, exact15.34375. The latter's
foreground triangle area is.28125 and local x moment.0703125. Direct centre
composition and separate-alpha composition must differ from the correct
target; restoring the original path must recover its bytes. Constant/affine
absolute error must be<=1e-8e; known full-cell Fourier controls<=1e-7e. These
are prospective engineering arithmetic limits. A translated wave with fixed
canonical phase must power a lost-native-offset fault.

## Fixed38 inputs and coordinates

Main matrix follows root's `next-quality-matrix-design.md`: flat then textured;
noise-off then seeds701,709,719,727,733,739,743,751. Both modes use each exact
five-frame bundle; even state ordinals start with HardFloor and odd ordinals
with FloorPedestalV1. Add textured noise-off HardFloor endpoint0 and endpoint4,
for38 RGB files. The root-owned matrix index will bind each actual plan,
receipt, TIFF, successful command log, build and upstream noise admission.
The concrete index schema is a pending adapter interface, not permission to
infer these records from filenames. No intended scoring before its freeze.

Root owns the new independently bounded RGB classic-TIFF parser, preserving
M194f's128-pixel parser unchanged. Require actual unsigned16-bit interleaved
RGB, exact CameraLinear description/software, strips and canonical pixel hash,
with at most1MiB/file and320×240 dimensions. Use its Budget-compatible API
`check_allocation(shape,dtype)`, `watch(array,label)`, `check()`.

All38 actual plans must have the same output crop and integer native offset,
within320×240. Require the actual four level sizes, nonempty measured-floor
prefix and contributing frame count from one anchored terminal banner, actual
identity/no-CA/InputRange configuration, correct original/local/probe indices
and the fixed injected noise/WB. The local probe index for endpoint4 is0.
These requirements are supplied by the independently commissioned bridge;
the quality adapter cross-binds its actual plan/log/receipt, not copied labels.

At every delivered pixel use native z=(output_x+offset_x,output_y+offset_y).
Convert actual TIFF code to post-WB DN by code*14848/65535, with no second
black subtraction. The same-centre ideal is
`T_rgb=.25*S_K0*(.75*WB_R,1*WB_G,.6*WB_B)`, using represented f32 WB values
`[1.3333333730697632,1,1.6666666269302368]` as exact f64 operands. It is an
unquantized ideal RGB field, not a simulated demosaic observation.

## Regions fixed from inputs

Let W be native x[104,216),y[104,136), and h=x-.15*y-142. Every site in W
must be at least74 native pixels from each actual output border. Refuse a
failed guard; do not shrink or move W. Define these seven regions:

- whole delivered output;
- W;
- boundary: W and abs(h)<=8;
- surface-background: W and h< -8;
- surface-foreground: W and h>8;
- endpoint-background: W and h< -(.575+6*sqrt(1.0225)+2);
- endpoint-foreground: W and h>.575+2.

All are nonempty prerequisites; no output-derived mask enters the reader.
Ideal comparisons use all seven. Endpoint0 observation comparisons use only
endpoint-background; endpoint4 only endpoint-foreground. Each endpoint remains
a separate reference. No splice, per-pixel minimum or fitted reference is
permitted. Surface masks are not a claim of boundary-free merge dependencies.
The known invalid background site(150,110) must be excluded, while(149,106)
is admitted; equality at a visibility threshold stays outside.

## Quantities and uncertainty

For each scene/mode/channel/region, retain signed bias, MSE and RMSE for the
noise-off output and every seed against each applicable fixed target. For the
eight noisy frames, use per-pixel Welford mean and sample variance with
denominator7, then aggregate the region. Retain mean-image error, variance,
the squared-bias estimator`mean(error)^2-variance/8` including negative values,
and noise-dependent bias relative to that mode's own noise-off output. The
latter is not a common fidelity target. The finite-repeat decomposition
identity is an arithmetic check with absolute tolerance1e-8DN² plus relative
1e-10; it is not independent evidence.

For paired per-seed MSE differences report all eight values, their mean,
sample SD and SD/sqrt(8). No pixel-independence uncertainty is reported. For
each mode's variance and paired variance difference, delete the same whole
repeat from both modes, recompute the seven-repeat variance, and report all
eight values and jackknife SE`sqrt(7/8*sum((J_k-mean(J))^2))`. Reopen one pair
of actual TIFFs at a time; never store an eight-repeat RGB volume. Variance
ratios with zero denominator are undefined and keep their underlying values.

For each actual seed/noise-off mode pair, and the two eight-repeat mean images,
retain per-channel nearest-rank99.9% and maximum absolute ideal errors over
whole output and W. Nearest rank is ceil(.999*N)-1 in zero-based ascending
order. Retain signed before/after/target values at both modes' worst sites and
at maximum absolute-error worsening, with deterministic native(y,x) tie order.
Count absolute-error worsening>10DN and improvement>10DN at all sites; equality
does not count. Movement alone is not harm. No pooled tail statistic hides
opposing channel/seed changes.

## Wave readout and powered private instruments

On noise-off textured outputs only, fit each surface's two fixed waves on its
surface mask using one matrix `[1,cos(w1),sin(w1),cos(w2),sin(w2)]`. Coordinates
and frequencies are canonical/native identity coordinates as above. Require
rank5 and SVD condition number<=1e6 before solving, without adjusting the mask.
Use the identical matrix for output and ideal. Report intercept, both complex
coefficients`C=cos_coefficient-i*sin_coefficient`, signed amplitude difference,
complex coefficient error, wrapped phase error and residual RMS. Phase is
undefined when either amplitude<=1e-8DN. Never remove a fitted gain or phase
from the target error. Retain full signal RMSE as well as fitted coefficients.

Run the fixed flat instrument first: constant3000DN must yield wave amplitude
and residual<=1e-7DN on both masks. Private two-wave signal has intercept3000,
amplitudes40/25DN and phases.31/-.47 at each surface's actual registered
frequencies. Fit coefficient errors must be<=1e-7DN. Fixed destroyers halve
both amplitudes, shift both phases by.4 radians, multiply amplitudes by1.5,
or add20DN*cos(2*pi*(.117*x+.053*y)+.29). Each must change common-target RMSE
by>1DN; amplitude increase must be recognized as error despite its larger
amplitude. The extra wave must leave fitted residual RMS>1DN. A separate
projected extra-wave residual must have nonzero RMS>1e-6 before use; adding
it at its unscaled20DN amplitude must preserve original coefficients within
1e-7 while raising residual/common-target error>1DN. This explicitly defeats
a coefficient-only quality claim. Restore each input and recover bytes.

Further controls: rank-deficient duplicate columns refuse; missing native
offset changes the actual fitted phase; a64DN single-channel spike is caught
by full-site maxima even outside W; opposing signed errors expose bias
cancellation; a sequence with equal spatial structure but controlled temporal
variation distinguishes temporal variance from spatial SD. Eight repeat
offsets are[-7,-5,-3,-1,1,3,5,7]DN: mean0, sample variance24. A constant biased
stack has variance0. Hand-computed scalar leave-one values and paired MSE
differences check the actual uncertainty functions. No new random draws.

The TIFF instruments use re-chosen11×7 RGB integer ramps, both byte orders and
multiple strips with valid companions. A separate legal193×17 image must be
accepted by the new reader and refused by the held M194f128-pixel predicate.
Coherently changed dtype/shape/tag,
overlap/truncation/trailing data, wrong external hash and a single changed
green code must fail the appropriate actual reader/association boundary.
Malformed complete38 index, mismatched crop/seed/mode/endpoint/probe identity,
missing measured-floor witness and actual changed TIFF are distinct from
numerical metric failures; controls cannot pass through unrelated exceptions.

The >1DN RMSE increase, >2% variance rise and >1DN noise-off wave amplitude loss
are descriptive engineering review triggers on these exact named regions,
targets and channels. Preserve smaller opposing changes and all results. Their
absence is not a quality pass; MSE may reward blur, bias may cancel, and larger
wave amplitude may manufacture contrast. No source/threshold fitting or
candidate execution occurs under this prospective document alone.
