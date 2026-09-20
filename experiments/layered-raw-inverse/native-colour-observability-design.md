# Seven frames versus delivered-colour observability

**DERIVED constraint; standalone measurement retired, not executed.** Seven training frames do not
by themselves demonstrate insufficient colour information. They can leave a
sheet-difference null that cancels exactly in the delivered image. Conversely,
some CFA ambiguities survive arbitrarily many identity-geometry focus positions.
Neither result diagnoses the observed free-flat failure.

Consider constant coverage `0<a<1`, fixed depths1/0, an infinite or periodic
linear scene, and one R or B sublattice. At base frequency w its four aliases
are `w_m=w+pi*m` modulo2pi. Let `x_m=a*deltaN_m`,
`z_m=(1-a)*deltaF_m`, D_m the common-PSF transfer, and gamma_m the known CFA-site
phase. For a symmetric pupil with defocus transfer h(d,w)=h(-d,w),

`y_f = (1/4) sum_m gamma_m D_m [h(1-f,w_m)x_m + h(f,w_m)z_m]`.

Define delivered sums `u_m=D_m(x_m+z_m)` and differences
`v_m=D_m(z_m-x_m)`. The actual training foci
`0,1/8,3/8,1/2,5/8,7/8,1` contain three mirrored pairs plus the midpoint.
Their even combinations give **four equations for four u coefficients**;
the three odd combinations constrain v alone. If the even matrix has rank4,
the compulsory null in the7x8 sheet system is consumer-null. Rank4 is a
condition to measure, not a guarantee. Alpha need not equal.5 for this split.
Numerical pupil/grid rounding may perturb symmetry and must be priced against
noise, not credited as useful information merely because a singular value is
nonzero. Spatially varying coverage/textures couple frequencies, so this block
argument is not a theorem about the complete nonlinear scene.

**A surviving ambiguity.** For radial optics, aliases with equal radial
frequency have identical h at every focus. Along `w_x=w_y`, the swapped aliases
`(w_x-pi,w_y)` and `(w_x,w_y-pi)` have equal transfer and the same R/B CFA phase.
An opposite perturbation to their delivered u values is invisible yet changes
native colour. This degeneracy also holds for a swap-symmetric discrete
bilinear operator; exact radial symmetry is not required. It survives the
common PSF wherever its transfer is nonzero. The finite phase-rotated pupil
need not be exactly swap-symmetric: small quadrature anisotropy can lift an
algebraic null without making it recoverable. Near the diagonal, conditioning
can remain poor even when there is no exact null. Green's denser lattice does
not measure independent red/blue structure; using it to fill those modes is a
colour prior, not additional red/blue observations.

More focus positions can improve the even matrix and noise averaging, and
nonmirrored positions can disentangle sheet differences. They cannot separate
columns that have identical transfer at every focus. In the **analytic continuous
model**, known translation adds factors `exp(i*w_m dot t_k)` before CFA sampling.
Non-collinear phase diversity can separate the equal-radius pair; one common
shift cannot, and diagonal shifts preserve the equality of the axis-pair factors.
This phase-factor formula is **not** the translated discrete bilinear operator:
the latter must sample each near/far/alpha field once at `x+t_k+d*u`. Its transfer
uses tent weights at those combined addresses, and generally cannot be factored
as `exp(i*w_m dot t_k)` times the unshifted transfer. Shifting already rasterized
RGB adds another interpolation and is a different operator. At Nyquist, even
the simple bilinear half-pixel shift can annihilate a sampled cosine.
Real70/259-frame stacks therefore require actual per-source geometry and focus
transfer, not a frame-count argument. Breathing diversity is spatially varying;
registered display images cannot substitute for original CFA sampling phases.

**Retain only as a future motion-consumer regression.** Keep the same seven foci and constant
a=.35. Make two legal positive scene worlds differing only by
`deltaN_R=deltaF_R=A*(cos(pi*x)-cos(pi*y))` (or B), with A below half the
positive sheet DC; leave green and coverage unchanged. The two Nyquist-axis
modes have equal transfer under quarter-turn-symmetric optics and cancel on
both R/B sublattices at every identity focus. Their delivered `B(P)` difference
survives unless the common PSF annihilates those modes. Test expected CFA and
delivered RGB directly, not just matrix rank. The actual dense table may break
exact symmetry through floating-point construction: distinguish the analytic
null from measured numerical leakage relative to injected noise.

For a future actual bilinear implementation, translate the per-ray sample
addresses by fixed half-native-pixel x/y offsets before CFA sampling, and compare
against independent literal tent evaluation; do not assert continuous phase
factors. Use `(.25,.25)` as the fixed diagonal negative, with explicit checks
that **each individual axis mode remains live** in the tested observations;
cancellation is not evidence if both modes were separately erased. Independently
verify that the x/y phase-positive perturbation becomes observable. Evaluate
full96 arrays and only the original16:80 supported interior, so zero-padding
leakage cannot create apparent information. No frames are added, and no fits
are involved. A
small lower-frequency real-colour component is the observable positive, and
zero perturbation is the null. This supplies an explicit unchanged-sensor /
changed-consumer world pair and a phase-diversity positive, not a frame-count
sweep. It is different from an interpolation or demosaic variant.

If a compact Fourier matrix is also reported, use the whitened observation A
and delivered C together: `C*(I-A^+A)` detects consumer-visible nulls, while
`C*A^+` prices noise only on identifiable components. A finite pseudoinverse
covariance alone silently drops unobservable output. These arithmetic
quantities support the explicit two-world forward witness; they cannot replace
it or establish the cause of a saved reconstruction failure. No optimizer,
camera calibration or image-quality admission follows.

**Decision: do not execute this as a new milestone.** Read by content,
`quality-september14/results.md` already records a joint-CFA inverse with
independent alias, duplicate-phase and wrong-map controls. Its improved
synthetic reconstruction and held-source residual did not predict photographic
utility: real rails softened and acquired colour stipple. Better local placement
made the ordinary mean visibly cleaner while reducing apparent R/B phase
diversity; nominal full rank did not establish noise-robust recovery. A subsequent
fixed residual-backprojection update restored colour speckle without a newly
resolved feature. That interpolation/update family remains closed here.

Re-demonstrating the ideal Bayer null cannot decide whether to add frames,
change a radiance prior, or extend the current inverse to actual captures.
The one decision this witness could newly settle is **whether a future implemented
original-CFA motion-aware forward preserves sampling-phase information by applying
translation at each coupled ray address**, rather than silently interpolating
an already integrated image. The algebra cannot establish that implementation
fact. There is no such new consumer to commission in this task, so save the
corrected control for that change; do not spend a separate run on it now.

Prior constraints read by content: SYNTHESIS architecture and section4.1's
unresolved breathing/phase-diversity issue; M70-through-focus-spectrum and
M115-deconv-headroom (more rows/near-scaled transfer did not establish useful
inverse headroom, and inversions amplified noise/ringing); M-PHASE0-QUINCUNX
(energy beyond a plane's Nyquist is not a commissioned reconstruction method).
The saved fine chroma-error decomposition is motivation to test this operator,
not evidence that these modes caused the error.
