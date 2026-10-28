# Independent decision: close this incomplete telescoping estimator

2026-10-27. **DERIVED / ARGUED; source-only review.** Reviewed
[operator-design.md](operator-design.md), SHA256
`ab36db195dff73da5348bca68df7f35e6f1cfec3ea636eb035f84ca386fd1d8c`.
No implementation, model execution, numerical experiment or RAW read was done.
This decision concerns the specified estimator, not the general possibility of
original-CFA reconstruction.

**No implementation release is justified by this checkpoint.** Its useful new
algebra is real, but the source admissions, practical analysis/synthesis rows
and complete-output policy are not fixed. Another partial prototype would not
yet test one producing operator that can reach a complete299-source photograph.

## What the proposed algebra does establish

Using different admissions in the terms
`F_h(a_b)-F_2h(a_b)` escapes the earlier single full-value source fraction.
At repeated geometry, a fine term can use one frame and a coarse term another.
Thus the old two-band convex-mixture counterexample is not itself a rejection
of this formula. Within each difference, using the same admission in both
members preserves cancellation of a consistent independent color constant,
assuming the integrated moment systems have full rank. The original physical
green offsets are retained; no source RGB values are accumulated.

These are response properties, not recovery results. Uniform admission
telescopes to the finest local estimator, not to an identity or an unbiased
estimate of arbitrary detail. Repeated same-phase samples add independent noise
observations but do not reveal a sampling-null color component. Independent
R/G/B fits avoid imposing a common color texture; they still can attenuate the
channels differently and produce false color.

## The concrete unresolved requirements

1. **The bands and source decision are not yet specified together.** Both local
   estimates reproduce quadratics, so their difference annihilates quadratics.
   Its response cannot be identified with an ordinary Laplacian level merely
   by assigning the same scale number. The design leaves `a_i,b` symbolic:
   there is no producing source-specific evidence/admission rule to challenge
   on simultaneous near-fine/far-coarse content. Even perfect band admission
   would not remove leakage or attenuation in the finest signed fit. Defocus
   and mixed-depth visibility are still properties of the observations; the
   moment equations are not a calibrated optical inverse.
2. **Noise must follow the complete original-sensel row.** With frozen rows,
   `Var(X)=sum_j L_j^2 variance_j`, where L includes every scale difference and
   final synthesis contribution. Shared-sensel cross terms cannot be dropped.
   Data-dependent admissions make this conditional propagation, not a complete
   sampling-variance guarantee. Correctly abandoning the previous zero-headroom
   minimum-variance DC cap removes that obstruction; it does not supply a new
   noise or rank-fallback policy. Falling back to a coarse positive average
   could pass a flat guard while deleting genuine independent colored detail.
3. **The written full-image route is impractical.** Full-resolution local fits
   at every dyadic scale require support growing quadratically with scale for
   each of299 sources. The author's radius384 example illustrates the problem;
   it is not a measured runtime estimate. Sparse scale lattices could change
   the cost, but require specified prolongation, boundaries and composite rows.
   Those operations alter the stated pointwise telescoping identity. Neither
   original-u16 storage nor source streaming alone makes this work competitive.

The earlier [direct band-functional proposal](../joint-cfa-local-fit/identifiability/operator-proposal.md)
already records the moment/noise completion problem. This version clarifies a
DC-preserving multiscale combination, but does not resolve that problem or the
finest estimator's bandwidth. No generated screen or whole-photo run is
recommended for this incomplete formulation. The photographic objective remains
unresolved; closing this design supplies no quality improvement or rejection of
all source-conditioned native estimators.
