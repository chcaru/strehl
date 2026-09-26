# Fixed consistent reconstruction of the actual fused coefficients

Generated-only implementation, September25. Root executes; source_trace owns
the actual consumer, opal_headroom owns the operator, and trace_review owns
independent numerical and image controls. No full adapter, RAW original read,
source selector, optical inverse, new noise estimate or production default.

The decision/prior-art record is `../quality-september25/next-consistent-reconstruction.md`.
Current full-chip contact/spill defects and the complete Helicon B/C gap motivate
this test; neither identifies inconsistency as their established cause.

Hold actual canonical coefficients C after every source has passed through the
existing BandWorker exactly once. Let A be the exact finite-domain native
Pyramid::build, including terminal Gaussian and all odd-size/clamped-border
rules. For each CFA plane minimize the ordinary unweighted sum
`||A X-C||_2^2`. No averaging by level size, denominator weighting, cross-colour
weight, regularizer or unknown scene/PSF/depth parameter is added. Existing
collapse S obeys S A=I for realizable coefficients; A S need not equal identity
for independently fused coefficients. That difference must be exercised.

Use the existing S C as the initial image, fixed S S^T preconditioner and
fixed32-iteration numerical cap, all chosen before execution. Admission requires
the independently chosen0.02DN RMS normal-residual error certificate. This is
an exact-linear bound with f32 numerical qualification by the dense oracle;
it is not a rigorous enclosure of every floating-point rounding error.
The exact finite adjoints must be commissioned against a dense independent
matrix; ordinary expansion is not presumed to be the reduction transpose.
The preconditioner leaves the stated objective unchanged. A returned
nonconverged iterate is not a candidate.

The consumer uses the same rounded GPU gather, green probe/beta, injected
NoiseModel, canonical chunk-free generated fold, E/F/weights and output crop.
`donor_consistency_diagnostic::resolved_coefficients` supplies C. Canonical
collapse plus `real_source_contributions::hull` must reproduce the
actual canonical finish bit for bit. Apply that identical InputRange clamp to
a converged reconstructed image, then the existing camera_rgb/final MHC.
The coefficient targets, every exposed accumulator, all source data and hull
must hash unchanged. The final image's finest and terminal coefficients need
not be unchanged; make no such claim.

Off passes the same actual source fold, coefficient/state observations, hull
and final MHC, preserving canonical CFA/RGB exactly. On records all four
solver results before a refusal decision. If any plane refuses, candidate_valid
is false and all candidate image fields are labelled baseline placeholders;
the independent screen must skip their quality scoring and save a numerical
refusal. There is no silent local fallback or partially applied plane mixture.

Independent tests commission actual A/A^T, consistent/inconsistent targets,
solver/refusal behavior, flat first and existing actual-consumer truth scenes.
Coefficient residual, solver objective and changed pixels are only mechanics.
Retain final RGB/green/chroma truth errors, genuine colour/detail amplitudes,
and erased/wrong-source destroyers. Smoothing, contrast exaggeration or a
lower least-squares objective cannot qualify an image. A failure closes this
fixed norm without an iteration, normalization or regularization sweep.

A later complete299-chip observation requires separate root authorization
after this screen, current whole RGB16/ICC identity and exactly pinned tone.
The present source stores one generated input scene and O(image) solver state;
it contains no photographic route or N-aligned-frame collection.
