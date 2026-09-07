# After the geometric commission: larger-fixture numerical work

2026-09-07, root. **Prospective reasoning only; not a registered experiment or
implemented optimization.** M194e's amendment4 full run and CFA conversion have
now passed independent checks. These notes neither change that fixed fixture
nor admit a larger one.

The source/size audit in `next-production-bridge.md` establishes why a larger
scene is required for the three-band M194d comparison. Simply scaling the
current all-pixel numerical quadrature could make a repeated-noise population
expensive. Expected noiseless frames should be commissioned once, then reused
with separately registered independent noise draws; noise should not trigger
recalculation of the optical integral.

One existing analytic limit can reduce future numerical work away from the
occlusion boundary. `experiments/m25-simulator/src/strehl_sim/optics.py` already
implements the uniform-disc transfer `2*J1(x)/x` and preserves its negative
lobes. M194b independently checked that prior operator within its own scope.
Neither that older tolerance nor M25's failed physical-optics gates transfer
automatically to a tighter M194e-derived fixture.

For a whole sensor cell whose foreground mask is constant over every pupil
ray apart from a zero-area boundary, the coupled integrand reduces exactly
to one layer. With inverse-map linear part M, use n_native=M^T*n_scene and
h=n_scene·T(z_center)-offset. The radius is always the **foreground** pupil
displacement R_f=abs(d_f)*norm(n_native), for both visibility decisions.
The cell half-width is H=(abs(n_x)+abs(n_y))/2 in that same native normal.
A foreground-only integral has h>=R_f+H; a background-only integral has
h<=-R_f-H. At the background equality, the foreground mask may still include
zero-area boundary rays; the equality is integral-equivalent, not a pointwise
claim that every ray is background. A future implementation
would need conservative finite-arithmetic admission and a numerical fallback
at uncertain boundaries; it must never snap coordinates or replace a partly
occluded cell with a separately blurred layer.

For a layer wave A*cos(omega·q+phi), inverse-similarity linear part M, native
wave vector k=M^T*omega, and signed native pupil displacement d, the full-layer
cell mean is the center's wave value multiplied by
`2*J1(abs(d)*norm(k))/(abs(d)*norm(k)) * sinc(k_x/2) * sinc(k_y/2)`,
with sinc(x)=sin(x)/x and the removable zero-frequency limit equal to1.
DC is unchanged; a full-layer affine field averages to its center value.
This follows from independent uniform-disc and square-cell Fourier integrals
once visibility is constant. The even disc transfer does not license taking
absolute defocus signs inside the partly occluded joint-pupil model.

Any future use needs a separately reviewed numerical amendment: real branch
occurrence, both layer signs, negative transfer lobes, zero/near-zero arguments,
nonidentity coordinates, conservative full-coverage boundaries, and agreement
with an independent spatial integral at the new registered accuracy. A disabled
analytic branch must remain a valid whole-domain numerical companion. Compute
cost counts for the actual larger scene and boundary location before setting
new resource budgets. Do not add this change to the current amendment4 run.

The larger quality fixture must put its boundary inside a declared supported
production region, preserve whole-image/sparse adverse readouts, distinguish
ideal pinhole truth from attainable observations, and pair multiple independent
noise realizations with explicit flat controls. Camera calibration and a
real-capture SOTA claim remain separate unanswered questions.
