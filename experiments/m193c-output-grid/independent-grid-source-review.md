# Independent grid reader: root source review

Source review only, before any private image execution. The reader is authored
by Curie; the generated grid is authored by Zeno. Root inspected the complete
reader, its 45 control choices, the proposed protocol, the owned production MHC
and Catmull implementations, and the separately reviewed Rust precision witness.
No numeric result, universal precision claim, or image admission follows from
this review. The exact reader bytes are bound by the subsequent execution release.

The consumer is the native sampling coordinate. Crop must restore twice the
quad crop origin; Scale must compose the cover factor about the native centre
(160,120). The reader intersects all four corner inequalities analytically,
instead of repeating the production cover bisection. Source coordinates use
explicit real inverse matrices. The fixed scale track retains its measured
curvature, while signed imaginary terms and translations exercise both axes.
The 32 R/G1 pairs sample different native sites. Their paired residual norm
is not called a displacement measured at one shared pixel.

The source reconstruction checks all active u16 values, range and little-endian
hash, never decoder padding. It uses the injected source constants to validate
an operator, not to independently establish sensor calibration. Both dyadic MHC
stencils and binary64 Catmull reductions are independent calculations; the f32
companion intentionally follows the owned kernel's operation order. That
companion alone cannot validate its shared arithmetic. The separate binary64
and exact-rational source checks, actual compiled witness values, and actual
full-resolution warp samples provide the other terms. Every admitted stencil
must remain inside active support, with no border reflection or sampler clamp.

The 0.125 DN reserve is tested on all 3712 literal component samples. It remains
a finite-site engineering condition, not a bound for arbitrary images. The
2.75 DN per-axis and 0.1 paired-native-pixel conditions are unchanged. Matching
an affine field can hide nonlinear errors elsewhere, so these conditions do
not qualify full image fidelity, occlusion behaviour, registration coverage,
detail, noise calibration or SOTA quality.

The fixed failures have observable alternatives: changing a sampled R code,
swapping R/B bytes, or substituting the neighbouring spatial green site must
reach and fail the coordinate condition. Wrong map cases must produce actual
images, agree with their independently computed faulty map, and disagree with
the correct map by more than one native pixel. Constant and rank-one fields
must refuse coordinate inversion. Removing an outer interpolation tap and
substituting an opposite channel must change the chosen actual component site
by more than the reserve before their rejection counts. These are prospective
power requirements; source inspection does not assert that they have passed.

All 45 checks run before final population admission, including complete valid
and restored companions. Count/off/placebo and restored map comparisons require
both whole-file and pixel hashes. JSON mutations are coherently rehashed, so a
stale digest is not credited as numerical rejection. The wrapper separately
owns compiler, invocation, ordering, and persistence authority. The reader
explicitly cannot certify those from a subject's own plan.

Root identified one narrow bookkeeping issue: the consumed-file ledger could
replace a prior digest for the same resolved path. Curie repaired it before
execution, preserving the 45 controls and all arithmetic. Root reread the
repair: the key is the case-folded resolved Windows pathname and conflicting
prior hash or extent now refuses. This review does not claim an executed
filesystem race test. The fixed scope has no legitimate same-path rebinding.

Disposition: source suitable for the separately frozen private command after
the launch wrapper and encompassing campaign are independently reviewed.
Actual control, pixel, precision and terminal-budget outcomes remain pending.
