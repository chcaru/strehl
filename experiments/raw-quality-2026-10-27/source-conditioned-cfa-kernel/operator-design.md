# Decision: the proposed telescoping sample estimator is not ready to implement

2026-10-27. **DERIVED / source design only.** No source changes, execution,
training or RAW reads. The paper's absent model is not the reason for this
decision. I considered one explicit new source-conditioned estimator below;
its frequency representation and practical synthesis remain incomplete.
Do not implement it under a claim that these are already solved details.

## The one proposed operator

For output color c, let F_h(p;a) be a local quadratic moving-least-squares
estimate from original same-color u16 samples, with source admission a_i fixed
over that query's support. Coordinates are original unit-square sensels mapped
to the reference through the supplied runtime source-to-reference similarity.
The six basis columns are1,u,v,u²,uv,v² with u,v=(x-p)/h; each design row is
integrated over the transformed original sensel footprint. The target is the
reference unit-square integral, not merely the polynomial intercept. R/B stay
independent; both physical greens may contribute to G with their actual offsets.

For a fixed compact radius3h weight k and original injected variance sigma²,
the normal matrix and data vector are
`M_h=sum_i,j a_i*k_ij*d_ij*d_ij^T/sigma_ij²`,
`r_h=sum_i,j a_i*k_ij*d_ij*y_ij/sigma_ij²`.
Where nonsingular, F_h=t_h^T M_h^-1 r_h is a signed original-sample row.
It constructs no per-source RGB values. The proposed combination was

`X_c(p)=F_H(p;a_base) + sum_b [F_hb(p;a_b)-F_2hb(p;a_b)]`,

with dyadic h and the **same source/band admission in both terms** of each
difference. Different bands may admit different frames. This is genuinely
different from one scalar full-value mixture: near fine and far coarse evidence
are no longer forced to share a source fraction. All rows reproduce each
independent color constant; every difference is exactly DC-zero in exact
arithmetic. Uniform admission telescopes to F_finest, not to measured truth
or an identity resampler. No strict minimum-variance-DC noise cap is proposed.

## The precise missing steps

1. **This does not yet define the claimed frequency bands.** Every F_h above
   reproduces the same quadratic scene at the same reference cell. Therefore
   F_h-F_2h annihilates *all quadratics*, whereas the ordinary Laplacian guide
   does not. Transferring the existing per-band focus/noise fields by matching
   h or a level number would not establish that they admit the signal this
   difference estimates. The earlier native-CFA alias-cancellation example
   also remains: apparent sharpness of a sampled source can favor blur.
2. **The finest reconstruction is still load-bearing.** Telescoping exposes
   F_finest's transfer and noise directly. Source diversity/conditioning does
   not prove faithful fine neutral or independent-color response. This proposal
   supplies no new evidence against the old direct-CFA softening and joint-fit
   chroma failures. A common-moment row alone cannot be advertised as recovery.
3. **The written complete-image operator is prohibitively expensive.** Evaluating
   every scale at every native output pixel makes original-sample support grow
   as h². For h=128, radius384 encloses roughly463000 original sensel locations
   per source before channel separation; across32MP and299 sources this is
   already trillions of neighbor visits even before the smaller scales and
   six-dimensional updates. A dyadically sparse query lattice could reduce
   this substantially, but then prolongation/synthesis enters each row. It
   changes the displayed telescoping identity, the target functional and the
   focus-field interpolation. No such producing rows are fixed here.
4. **A complete uncertainty/fallback rule is absent.** For a frozen composite
   row L, variance is `sum_j L_j² sigma_j²`; cross-band terms must be retained
   because the differences and final sum reuse original sensels. Summing
   individual F variances is wrong. Data-dependent admission makes this only
   conditional propagation. The previous strict DC reference cap can force
   all useful correction to zero and is not reused. Rank refusal can label a
   missing estimate, but filling it with a positive smoother would be an
   additional reconstruction policy, not a numerically harmless fallback.

These are concrete gaps in this candidate, not a mathematical prohibition on
native source-conditioned reconstruction. They cannot be repaired honestly by
calling quadratic degree a band, adding an arbitrary gain/iteration sweep,
interpolating already reconstructed source RGB, or quietly relaxing a noise cap.

## What is and is not reusable

The [earlier direct band-functional audit](../joint-cfa-local-fit/identifiability/operator-proposal.md)
already states the moment, covariance and strict-cap issues. This telescoping
construction adds a clear DC-preserving source-frequency decomposition, but it
does not supply the unresolved practical finest estimator and composite rows.
The [band-residual/deflation outcome](../joint-cfa-local-fit/constant-deflation/results.md)
also prohibits treating a well-behaved objective or finite solver result as
evidence that the missing color/noise behavior is acceptable.

**Close this specific design rather than dispatch another partial prototype.**
There is presently no complete code-ready operator from this proposal to carry
promptly to a299-source photograph. A future release must name actual analysis/
synthesis rows on a practical lattice and their supported target response,
not just a new source-conditioned weight formula. No implementation or
photographic claim is recommended by this report.
