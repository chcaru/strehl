# Coupled pupil stencil: bounded next engineering step

DESIGN / DERIVED, not executed. The current 64-ray operator passes its same-ray
implementation check but fails the retained 1024-ray resolution check. Increasing
quadrature accuracy is separate from changing the inverse objective or claiming
camera optics adequacy. Keep the current model and experiments frozen.

For the supplied identity geometry and two constant depths, the interpolation
weights depend on focus and pupil position, not output pixel position. Write
`n_p(u)` and `b_q(u)` for the native bilinear tent weights at near/far integer
offsets. Precompute nonnegative
`J[p,q] = integral_disc n_p(u)*b_q(u) du/pi` and its marginals
`U[p]=sum_q J[p,q]`, `V[q]=sum_p J[p,q]`. Then, before the existing diffraction
floor and RGGB sampling, the exact real-arithmetic operator is

`sum_p U[p]*(alpha*N)[x+p] + sum_pq J[p,q]*(1-alpha[x+p])*B[x+q]`.

This positive form avoids subtracting a large occlusion term from a large far
term. It is algebraically the proposed `near + far - joint` decomposition,
preserves premultiplication before interpolation, and keeps the SAME aperture
ray's visibility coupling. Replacing J by `U outer V` is the already rejected
visibility-after-average operator. For a fixed discrete pupil, replace the
integral by its weighted sum: aggregation is exact in real arithmetic. The
result is polynomial in the latent alpha/radiances and differentiates exactly
through their products; no derivative of a fitted focus/depth is promised.

**Cost/storage bounds for the present supplied geometry.** For focus in [0,1],
near/far displacements have opposite signs and magnitudes a+b=12 native pixels.
Along one pupil axis, each interpolation cell has four active near/far index
pairs; each separate cell-boundary event adds at most two new pairs. This gives
at most `4*(ceil(a)+ceil(b)) <= 52` distinct pairs per axis when both are nonzero,
or at most 25 at an endpoint. Thus at most 2704 joint 2D entries per focus before
disc pruning; at the symmetric midpoint the simultaneous-boundary bound is
37 squared = 1369. Nine tables with four int32 offsets plus f32 weight occupy
at most 486720 bytes for joint entries; marginal/group tables are additional
small setup data. At 96 squared pixels, the worst bound is about 75 million
joint RGB weighted products per forward, independent of the quadrature count
used to construct J. These are conservative operation estimates, not timing.

By comparison, the current fully batched 1024-ray route alone holds sampled
near RGBA plus far RGB at 252 MiB and its two XY grids at 144 MiB for 96 squared
pixels, before other intermediates/gradients. A fused stencil needs latent,
output and gradient planes plus fixed tables; it must NOT materialize
`[joint_entries,H,W,channels]`, which would erase this memory advantage. Ordinary
Python loops over thousands of shifts would introduce many launches/autograd
nodes: a speed claim requires a fused gather/reduction and its adjoint, or a
separately measured grouped implementation. This design does not authorize that
kernel yet. One source remains live at a time.

**Cheapest accuracy-first commissioning.** Build J once on CPU in f64 from an
explicit deterministic dense pupil, aggregate its 16 bilinear products per ray,
then store f32 weights. Construction scales with rays, but each subsequent image
evaluation scales only with unique pairs. First compare an aggregated 64-ray
table to the existing 64-ray forward and gradient on constant, impulse, alpha
endpoint and crossing inputs, with the separate-visibility destroyer retained.
Then check successively resolved, independently generated dense-pupil tables
against the retained 1024-ray result and a higher-resolution reference using
the existing noise-normalized adequacy bar. This is numerical integration
refinement, not an image-quality parameter sweep; 1024 is a reference, not known
truth. No new fit is justified until the forward error is below that fixed bar.

If dense quadrature converges too slowly, the next setup-only alternative is
cell integration: split both pupil axes at the union of near/far interpolation
breaks. Within each rectangle, the joint basis is quadratic in each axis, so
only nine disc-clipped rectangle moments are needed. Deterministic adaptive
one-dimensional integration of those moments avoids image-dependent sampling.
It is more implementation work than aggregated rays and is not the first step.

Limits: the old normalized-coordinate `grid_sample` has position-dependent f32
rounding, so mathematical stencil equivalence is not a bit-identity promise.
Keep its existing supported-interior convention, diffraction kernel, CFA,
censoring and injected noise; require an explicit finite numerical tolerance
and adjoint check. Spatially varying depth, nonidentity geometry, angularly
varying radiance and unknown optics are outside this constant-depth stencil.
Accurate pupil integration alone supplies no reconstruction or real-RAW gain.
