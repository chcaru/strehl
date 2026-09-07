# After larger-float admission: boundary and noise comparison

2026-09-07, root. **Prospective design notes only.** This is not part of M194g's
released geometry count or a registered quality population. No noise draw,
reference image, production output or score was generated for these notes.

The immediate question after M194g should be whether the fixed M194d positive
floor weight trades boundary detail for its measured flat-noise benefit. Keep
HardFloor and FloorPedestalV1 exactly fixed; do not search the constant, exponent,
gate, focus count or seeds. M194d already found lower temporal variance together
with small detail costs and sparse worsening on its one-plane plant. The new
test changes the scene to a coupled depth boundary, so its old pixel hashes and
geometry are historical comparisons, not byte expectations for the new scene.

## Input and production population to register later

After genuine complete M194g float admission, reuse those five primary expected
frames for textured noise generation. The paired flat scene has both surfaces
at constant12000 electrons, with the identical geometry and focus records;
its exact expected value needs a powered emitter control, not an unnecessary
optical rerender for every seed. Retain noise-off and the eight existing seeds
701,709,719,727,733,739,743,751 in each scene. Commission independent Poisson
photoelectrons and Gaussian4-electron read noise, then gain.25 DN/e, black512,
white15360, declared CFA factors and ties-to-even quantization. Inspect rails
before clipping; do not mistake a post-clip histogram for an unclipped law.
The supplied law tests software behavior and does not validate calibration.

Specify the channel order before random draws: for scalar expected S electrons,
the photosite mean is c*S with c=.75/1/.6 for R/G/B. Draw Poisson(c*S), add
independent Gaussian read noise with SD4 electrons, multiply the sum by.25,
add512, then round and encode with the registered rail policy. Applying c after
the Poisson draw has a different shot variance and must be a live destroyer.
Use separately named, explicitly bound photo/read substreams per scene, seed
and original frame; define fixed native row-major site consumption. Reusing
the historical seed numbers does not promise historical random arrays.
The concrete generator/version and stream key encoding still need freezing.
Require repeat/frame/component-stream liveness, same-key replay, traversal
independence at the declared frame level and deliberate shared-stream faults.
Check temporal moments separately on all four CFA parities, including dark
read-noise/quantization controls and changed-gain, absent-read and correlated
noise destroyers. Bright quantization variance is an approximation unless
its lattice error is independently bounded; label it rather than silently
assuming an exact1/12 contribution at every signal level.

This produces90 CFA files (2 scenes ×9 bundles ×5 frames), streamed from one
expected frame at a time. Pair both production modes on these exact files,
giving36 main RGB TIFFs. Two additional noise-off textured single-input RGB
diagnostics, original frame0 and original frame4 under HardFloor, would make
38 delivered files. Declare those extra files prospectively if retained.
They expose attainable *local observations*; neither is whole-scene truth.
Single-input probe index0 differs from the original frame's index in the
five-frame stack and must remain visible in the plan.

Use the admitted M194f bounded source/authority/coordinate semantics through a
new versioned reader for the actual larger noisy manifest. Explicit identity
placements, reference2, actual cover/domain, Catmull-Rom, MHC, CameraLinear,
exposure0, f32 WB and one injected NoiseModel remain pinned. Bind actual
admission mode in prepared state. Read the real level sizes: three Laplacian
bands and a nonempty measured-floor prefix are prerequisites, not assumptions
from requested bands3. Preflight before pixels must establish a common domain
for paired modes and name any different single-input behavior. No default
promotion, profile fit or real RAW claim follows from this software fixture.

## Two meanings of reference must stay separate

**Ideal geometric target:** the same continuous shared-pupil model with K=0,
integrated over the native unit sensor cell. Foreground visibility must still
vary within a boundary-crossing cell; evaluating only its centre is wrong even
with zero pupil displacement. Convert the scalar target into post-WB DN using
the declared sensor factors and represented f32 WB. Its per-site RGB meaning
and CFA/demosaic limitation must be explicit before scoring. It is an ideal
geometric target, not proof that the five defocused inputs or MHC can attain it.
The independent clipped-cell/polygon method can supply the target after its
own fixed K=0 controls; shared fields do not permit shared untested arithmetic.

**Actual optical observations:** noise-free original frame0 focuses the
background; frame4 focuses the foreground. Read any such reference from its
actual single-input production TIFF, with the same output coordinate convention.
Only score its intended layer on input-defined fully visible cells. Do not
splice these two outputs at an argmax, label the splice attainable, or choose
the smaller per-pixel error. At the depth boundary the references remain two
different observations. Report both separately where used. A closer match to
a blurred observation cannot erase a larger ideal-target error.

Also report the difference between each mode's repeat mean and its own
noise-off output. This measures noise-dependent algorithm bias, not fidelity;
its reference changes with the mode and cannot rank the modes' scene accuracy.
Keep it alongside common ideal-target bias and temporal variance rather than
substituting it for either. Noisy mean-squared error can improve through blur.

## Masks, quantities and ways they can fail

The proposed supported window x[104,216), y[104,136) must pass the actual plan's
74-native-pixel local support guard on every side under identity/fixed-beta
conditions. Measured beta is global, so this local guard does not prove domain
invariance. The fixed boundary band uses algebraic height
`abs(x-.15*y-142)<=8`, not an eight-pixel Euclidean-distance claim. Define layer
detail masks prospectively outside that band within the supported window.
Masks come from the input geometry, never a focus winner or output error.
Retain whole-output and all-site sparse diagnostics, even when the guarded
window passes; the window cannot hide large adverse changes elsewhere.

- Read every actual TIFF with the independently commissioned16-bit decoder
  and explicit native offset. Preserve per-RGB bias, MSE and RMSE against
  each declared target, by whole output, supported window, boundary band
  and named surface where meaningful. Mean error can cancel opposing errors;
  MSE can reward blur on noisy data. No pooled scalar decides admission.
- On noise-off textured outputs only, use fixed sine/cosine components for
  each surface's registered two waves on its fixed mask. Compare complex
  coefficients with the corresponding target coefficients, including phase
  and residual error. More amplitude is not automatically better. Run the
  same readout on a flat field first, and commission blur, phase shift and
  extra-wave destroyers. A local fitted wave readout is a restricted detail
  diagnostic, not a general texture-quality score or a licence to ignore
  boundary error.
- Estimate temporal variance across eight independent draws at each pixel,
  then aggregate the fixed region. Never call a spatial region SD temporal
  noise. Report paired candidate-minus-baseline per-repeat MSE, repeat-level
  uncertainty and delete-one-repeat variance uncertainty. Eight repeats are
  eight independent draws, not millions of independent pixel observations.
  Preserve finite-repeat bias estimates, including negative estimates where
  an unbiased decomposition gives them; do not clip them into zero.
- Retain per-channel nearest-rank99.9th-percentile and maximum absolute truth
  errors, signed worst-site before/after/target values, and counts of absolute
  error worsening by>10 DN and improving by>10 DN. Movement alone is not harm;
  smaller mean error cannot excuse an unreported worse tail. These are
  descriptive diagnostics, not newly fitted quality thresholds.

M194d's>1 DN RMSE increase,>2% temporal-variance rise and>1 DN noise-off wave
loss can remain engineering review triggers only if their new mask/target
scope is fixed prospectively. Their absence is not a quality pass. Retain
smaller opposing changes, each channel, each scene and both reference meanings.
If one of these proposed wave readouts proves unpowered, retain its failed
commission and revise the instrument before any candidate output is scored.

## Practical release boundary

Next work needs one compact noise/emission commission, a strict larger-input
production adapter, a frozen complete matrix and an independent actual-output
comparison. Reuse the existing prepared merge, candidate enum, input-to-writer
checks and scoped TIFF reader where their contracts genuinely match. Do not
rewrite core merge arithmetic merely to establish the new baseline, weaken old
schemas, or build a general evidence framework. A quality result should name
the fixed candidate's gains and losses and guide the next implementation.
These development inputs cannot establish real-capture SOTA while physical
reference, transfer/noise and deep-alignment questions remain open.

Sources read: M194b-known-scene.md; M194d-band-admission.md;
m194d-band-admission/independent-comparison-design.md; M194e's next-production-
bridge.md support audit; the admitted M194f result; current M194g preregistration
and independent larger-fixture math/design reviews. No new numerical evidence
is claimed by this design.
