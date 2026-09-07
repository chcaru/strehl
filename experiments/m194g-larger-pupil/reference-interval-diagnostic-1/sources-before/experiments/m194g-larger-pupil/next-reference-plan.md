# Later independent spatial-reference release

2026-09-07. **Prospective design only, outside the first geometry source set.**
Root explicitly authorized this bounded plan while geometry controls are being
prepared. No radiance code, numerical integral, expected array, noise draw or
product comparison has been run. A separately committed later release is
required before implementing/executing this plan. The already committed
M194g mathematical model and external error bars remain authoritative.

## Scope and dependencies

Produce two independently computed reference arms for the one registered
textured320x240 scene, five original indices0..4, identity placements,
depths(1,2), K12, foci(.5,.625,.75,.875,1), mask normal(1,-.15), offset142.
The two-wave fields are exactly the M194e source records, reserialized and
externally bound. Canonical radians per pixel become native wave vectors
through M^T. Reusing those input records does not mean importing the author's
inverse, selector, Bessel result, integration code or error estimator.

The frozen independent Cartesian/chord and analytic clipped-cell equations
remain the reference's numerical fallback. They need a separately versioned
adapter for this extent, source-bound to the original independent model, not
edits to M194e. A new independent full-layer transfer cache is a numerical
implementation change and must itself be commissioned. The old small-array
reference results do not constitute the new full-array reference.

Prerequisites: successful geometry/cost controls and complete cost result;
committed author/reference sources and exact component populations; strict
input/source readers with actual mutation power; explicit final interpreter
arguments, fresh cache prefixes, budgets and source snapshots. This plan is
not authority to bypass any prerequisite because the model is already known.

## Full-layer spatial cache and error allocation

Evaluate the normalized full-disc characteristic by

```text
D(a)=(4/pi) integral_0^(pi/2) cos(theta)^2*cos(a*sin(theta)) dtheta.
```

Evaluate each square factor by its own integral
`S(k)=integral_(-.5)^(.5) cos(k*t)dt`. This is an independent spatial
formulation, without SciPy j1, the author's sinc implementation or its polar
radial primitive. Use zero relative tolerance and bounded adaptive quadrature.
The removable-zero result is1; the evaluator and its independent constant
control must both reach that case. Report actual quadrature indicators and
refinement, not a nominal zero because a transfer was cached.

Let T=.000125e for the primary independent reference and
T=.0000078125e for its once-refined arm. Let A_sum be the sum of absolute wave
amplitudes for a layer, bounded from its actual input record. For each of the
three normalized factors D,Sx,Sy request absolute error at most
`epsilon=T/(16*max(1,A_sum))`. Convert that normalized request to the raw
quadrature interval's normalization; do not pass an electron target directly
as a dimensionless transfer tolerance. With true factor magnitudes<=1,
the product error conditional on factor error bounds is at most
`3*epsilon+3*epsilon^2+epsilon^3`; multiply by each |A| and sum.
The first-order total is at most3T/16, leaving margin within a reserved T/2
for transfer integration and its product arithmetic. Quadrature indicators
are estimates, so this accounting is conditional, not a rigorous universal
error proof. Preserve the complete empirical refinement and analytic controls.

Reserve the other T/2 for finite phase/affine evaluation, summation and any
remaining quadrature accounting. Explicitly bound the evaluated coordinates,
phase arguments, amplitudes and radiance domain. If a rigorous operation-level
roundoff bound is not supplied, label this second part an engineering
reservation and expose actual discrepancy to the independent component
oracles; never print it as a measured or certified error. All output values
remain subject to the fixed full-image comparison, irrespective of indicators.

The cache key binds the actual finite inverse coefficients, field identity,
canonical wave vector, signed layer defocus, integration target and method
version. The disc value is even in d, but the key must not leak an unsigned
choice into the partly visible fallback. Cache at most20 full-layer tuples
per complete five-frame reference arm. A source/configuration hash alone is
not proof that the correct tuple was consumed; changed-frequency/layer/target
faults and the actual emitted-array comparison must detect a stale entry.

For interior selection use the independently derived conservative bound
`abs(h) > (abs(dF)+1.5)*(abs(n'x)+abs(n'y))`, with exact finite-coefficient
or outward-interval arithmetic. This uses a pupil-enclosing box and a fixed
one-native-cell guard beyond the native sensor half-cell. It deliberately
differs from the author's tight circular-support predicate. The rest of the
image is integrated by the independent clipped-cell/chord method. The guard
does not exclude any pixel from truth or scoring and cannot be enlarged after
observing a difficult cell.

## Fixed independent component family for later release

These choices precede implementation. Every applicable actual author enabled
and disabled cell method must meet the registered.004e maximum error against
the commissioned independent reference; the complete textured component set
also meets.0008e RMS. Independent reference refinement is at most.0005e.
Any looser historical analytic check is diagnostic only and cannot grant
the new float authority. Refusals remain failures, not missing rows.

1. **Disc/square transfer.** DC10000e, cosine amplitude1000e, zero centre
   phase, native direction(3/5,4/5), disc arguments4.75,6.25,8.75. Use a
   full or absent foreground state with absolute selected-layer d2, produced
   by depths(1,2), K8, inverse-focus3/4. Set the canonical frequency from
   the stated argument and direction before any output. The first two
   transfers are negative; the third is positive. An exact-rational
   disc-moment series with descending alternating-tail enclosure can certify
   these signs independently of floating j1. Spatial quadrature supplies the
   values. Abs, clamp, missing pupil normalization and missing square factor
   each need a named live >.004e destroyer. Exact zero and arguments
   2^-20,2^-8,1/8 test finite limits; use1/8 to reject an always1 shortcut.
   Tiny arguments cannot be called powerful merely because their bits differ.
2. **Coordinates.** Full-mask, K0, DC10000e and amplitude1000e,
   omega=(2.4,.8), native centre(7,11), forward scale.8 and rotation atan2(4,3),
   centre(2.25,-1.5), translation(.375,-.625). Record the actual finite M;
   its intended dyadic limit is((.75,1),(-1,.75)). Choose phase analytically
   from the registered correct centre mapping to make centre phase0, without
   looking at an output. The k-only transpose fault must exceed.004e through
   the square factor; the isotropic disc magnitude is inert to that rotation
   error. Repeat with literal phase.37 to power a wrong chief-ray map, and
   with an affine component on an explicitly positive local footprint.
3. **Visibility/tangency.** Retain all112 exact identity/scale2 tangent,
   nextafter, mask-scaling and translated-origin records from
   independent-geometry-preregister.md, plus its rotated bracket records.
   For translated canonical origins, transform radiance constants/phases
   consistently if claiming scene equivalence; otherwise name it a different
   input. Require branch dispositions and independent whole-cell values
   separately. Use the fixed h=±12/±16, n=(3,4), dF=-3/dB=1 constant-layer
   cases to power wrong background radius and omitted sensor-cell support.
   Equal F/B12000 is the scalar null, not a visibility-error detector.
4. **Joint sample and sign.** At native origin, identity, n=(3,4), offset0,
   dF=-3/dB=1, F12000 and local B=10000+360x+480y, the continuous point
   oracle is11000+400/pi. Changing only the foreground sign gives11000-400/pi.
   B is9400..10600 over this pupil footprint. A global sign reversal is an
   inert coordinate gauge. For a separate actual cell oracle at K0, square
   [-.5,.5]^2, foreground x>=-.2, F16000 and B9000+800x, the mean is13816e;
   separately averaging cell visibility/background instead gives13900e.
   Neither local affine law is emitted over an unbounded scene.
5. **Preserved numerical failures.** On their original M194e scenes, retain
   the whole-cell references at(30,4),(31,7) and(4,0), plus the original
   archived-source refusals as historical controls. Do not infer new tiny-leaf
   truth from the previously refused local reference. Current full-cell
   comparisons and current-source helper controls govern the new method.
6. **Consumption and accounting.** A stale transfer cache, wrong phase,
   swapped layer, omitted sensor factor, duplicated/missing cell and source
   mismatch must fail actual consuming checks. A count-only observer, placebo
   and different complete tile orders preserve the same algorithm's scalar
   and numerical payload bytes. Mode-dependent counters/digests are not
   invariant payloads. Trap radiance access during geometry-only stages and
   show the later optical traversal really visits analytic and partial cells.

Each component receives a literal source-bound record before execution. A
failed or inert destroyer is preserved and withholds the affected assertion;
there is no phase/threshold/coordinate search to rescue it. New source/API
adaptations are documented separately from these fixed mathematical choices.

## Complete arrays, finite budget and authority

The independent reference must generate all384000 cells in each of its two
arms, including every transition cell. Compare every one of the author's
1152000 values from all15 images with the refined reference. Require each
whole frame and the fixed input-defined `|x-.15y-142|<=8` band to pass
max.004e/RMS.0008e. Independently report the author's fallback-selected and
the broader reference-boundary populations. No output-error-selected ROI,
missing frame or successful subset can substitute for these domains.

Primary versus each author refinement remains max.001e. Primary versus
refined independent reference remains max.0005e over all five complete
frames. Analytic interiors identical across author refinement settings are
an expected consequence, not extra evidence. Reference cell integration is
analytic; its factor16 change refines the remaining spatial quadrature, not
an invented cell-sampling setting.

Freeze these **independent** resource caps before launch:30000000 actual
normal/chord or transfer-integrand evaluations,600 process-CPU seconds and
1200 wall seconds per complete five-frame reference arm; same separate caps
for the component batch. Quadrature limit128 per interval, zero relative
tolerance, one worker, common numerical-library thread limits<=2,32MiB
tracked explicit arrays. Transfer-cache setup counts against its own arm.
No arm borrows unused calls/time from another. Check time during analytic-only
rows and before accepting the final complete frame. Keep one current scalar
and indicator frame plus bounded comparison scratch, never all five frames
or repeats in RAM. The array accounting excludes hidden temporaries, Python
objects and RSS; record its exact scope.

The wider reference guard allows at most12960 candidate numerical cells per
arm under the proposed identity geometry. This makes a finite reference
plausible; it does not prove these budgets suffice. Any work, warning, precision
or time failure returns an incomplete uncommissioned result with all prior
outputs and snapshots preserved. No timeout stops a peer. A proposed budget
change must be reviewed prospectively before a new attempt, without altering
the mathematical scene or silently waiving the failed run.

The final comparison reader must be independently commissioned with actual
array/source/receipt mutations, externally pinned author completion and bundle
digests, every emitted reference file and before/after source bindings. Record
the actual executable, sys.orig_argv, fresh cache prefix, Python/NumPy/SciPy
versions and environment. Only a complete independent float gate releases a
later emitter. This plan supplies no noise, physical-calibration, production
quality, attainable-error-floor or SOTA authority.
