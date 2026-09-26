# Decision: test reconstruction consistency before another depth field

ARGUED proposal, September25; no implementation, build, fit or photograph run.
Recommend **one canonical-dual Laplacian reconstruction** of the existing
native merge's resolved coefficients. Keep every source, focus/noise field,
weight, exponent, fallback and coefficient target unchanged. Replace only
expand-and-add collapse with a global least-squares reconstruction, followed
by the existing input-range limit and exactly pinned development.

**Real motivation and limit.** Complete chip Helicon B has cleaner broad
contact/compartment boundaries than C on identical prepared inputs; native
Current retains swollen contacts and displaced-looking colour bands. The new
finest-only Potts/full-AC photograph instead adds colour islands. Those facts
motivate another reconstruction, but do not establish its cause or identify
Helicon's internals. Vitamin-C's compact sources28/33 versus spread52/69 are
real witnesses; marigold112/152 each contain different genuine hairs. A new
single source/depth label cannot safely replace all their scales. Consistency
cannot remove a physically present veil or correct geometry by itself.

**Exact small change.** Let A be the actual finite-domain `Pyramid::build`
operator, including its terminal Gaussian, odd sizes and clamped boundaries.
Let C be `donor_consistency_diagnostic::resolved_coefficients` from the current
`BandMerge`, before collapse/hull. For each original CFA plane solve
`min_X ||A X - C||_2^2`, with the ordinary unweighted sum over every stored
coefficient, using matrix-free conjugate gradients on `A^T A`. This is one
fixed norm, no spatial/image prior or adjustable scale weight. The terminal
target remains C, but the reconstructed terminal is NOT guaranteed unchanged;
do not claim an exact-base contract. Current collapse is an exact left inverse
on untouched pyramids; arbitrary fused bands need not lie in A's range. The
hypothesis is that reconciling their disagreement reduces ringing/colour
boundaries without deleting a depth. It can instead soften correct detail or
reconcile consistently wrong targets, so a lower objective is not quality.

Reuse `Pyramid::{build,collapse}`, resolved-coefficient access, current hull,
full-chip adapter, fixed seven targets and literal pinned writer. The only new
numerics are exact transposes of the existing finite reduce/expand operations
and a bounded linear solve. Expand is NOT to be assumed to be reduce's
transpose. O(image) storage; no N-source image/cost volume or new optical fit.
F32 arithmetic remains. One fixed32-iteration cap, with independently chosen
accuracy/refusal criteria before execution; no iteration or norm sweep.

**Cheapest rejectable test.** On small odd/even grids, independently enumerate
A and compare the operator/adjoint and solution with dense linear algebra;
wrong border taps and doubled adjoints must fail. A genuine single-image
pyramid must reconstruct unchanged within declared arithmetic bounds. Then
reuse the existing actual-consumer flat, neutral/coloured edge, broad-contact
and fine-near/coarse-far cases, retaining all old image/detail destroyers and
bars. The mixed case must actually contain inconsistent coefficients and a
live output change. Fail on flat/colour/detail harm; objective reduction alone
does not admit a photograph. If it passes, immediately produce one complete
299-chip Current/candidate pair and full views, with all25 fixed native pairs.
No ROI or additional hypothesis search. A null/harmful result closes this norm.
Final-plane caches cannot recover C: one canonical source pass must capture it;
subsequent solver/writer replay can reuse that compact coefficient cache.

**Why this route.** Read SYNTHESIS sections1/3 and the relevant M63/M70/M79
decisions, layered-raw-inverse's initial, free-visibility, in-focus, phase-aware
and pupil results, native-boundary-radiance, optical-support-veto, relative-blur,
BUILD-BLEND/HALO, and the current depth-route/competitor records. Known-optics
in-focus inverse success did not survive free visibility; phase-aware flat
reconstruction also failed. A larger depth/PSF inverse is consequently a poor
next time investment. M63 forbids treating a second focus peak as a second
depth; ordered labels also require a nonuniform focus axis and actual source
support. Prior Jacobi depth smoothing failed to propagate globally, while
generic Poisson compositing remains a surveyed proposal, not an executed
native test. Neither is evidence for another finest-only label field.

The alternative is established reconstruction theory, not an invented novelty:
Do and Vetterli explicitly study improved Laplacian-pyramid reconstruction
after coefficient perturbation. Their noise result is not a focus-fusion
guarantee. Only their author-university abstract/metadata was consulted;
no external implementation source was read.
[Framing pyramids, IEEE TSP2003](https://experts.illinois.edu/en/publications/framing-pyramids/).

Mechanical searches actually run: `prior_art.py radiance reconstruction defocus
inverse visibility focus-response`; `Poisson gradient integrability radiance
reconstruction`; `consistent reconstruction Laplacian least-squares analysis
synthesis`; `depth-map gradient-domain Poisson focus response ordered`. Targeted
repo search found no executed canonical-dual native merge comparison; this is
a bounded search result, not a claim that all prior methods were exhausted.
