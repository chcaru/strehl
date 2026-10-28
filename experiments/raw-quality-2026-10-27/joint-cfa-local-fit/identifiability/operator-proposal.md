# Direct band-functional local fitting: concrete route and limiting obstruction

2026-10-27. **DERIVED / ARGUED, not implemented or run.** The failed global
inverse is not evidence of an original-A nullspace: its saved error was visible
at actual photosites, and deflation subsequently reduced bias but failed the
flat noise/chroma comparison. A new local inverse must specify both its target
and its unsupported-mode completion. A condition number alone cannot do this.

## One precise small operator

The workable distinction from the rejected scalar full-value polynomial fit is
to estimate each **reference pyramid coefficient directly**, with different
source admission for each band. Use the actual product reference pyramid's
linear analysis kernels, including its separately defined base; do not call
polynomial degree a frequency band. The output would be four native Bayer
phase planes reconstructed from these coefficients and demosaiced once. This
is a different output representation from the rejected unrestricted RGB fit.

For a target coefficient at reference native position p and band b, set native
scale h=2^(b+1), support radius3h and local basis
`phi=[1,u,v,u*u,u*v,v*v]`, with `(u,v)=(reference_xy-p)/h`.
For each original same-spectral-color sensel in that radius, form its **area
integrated** design row d under the supplied source-to-reference affine map.
Use exact quadratic moments: transformed square covariance is A*A-transpose/12
in native units, divided by h² in the normalized basis. Both greens may supply
the same spectral G rows only with their actual distinct physical coordinates.
No per-source interpolation, RGB image or MHC guide is permitted.

Define t by applying the actual reference band's signed analysis kernel to
the same six basis functions integrated over reference unit sensels. This is
the target functional, not the polynomial intercept. Use fixed compact spatial
weight `k=(max(1-(u*u+v*v)/9,0))²` and source/band admission a from the already
specified original-phase Haar energy/noise cue; its interpolation to p is only
a guide lookup, never signal reconstruction. Admission is held constant across
this local support and differs by source AND band. Let `w=a*k/sigma²`, using
the one supplied original-sensel noise model. Accumulate

`M=sum w*d*dᵀ`, `r=sum w*d*y`, `Q=sum w²*sigma²*d*dᵀ`.

Where supported, the signed estimate is `c=tᵀ M^-1 r`, with frozen-weight
propagated variance `tᵀ M^-1 Q M^-1 t`. Rank must be checked on the scaled
design; no diagonal-count or ridge fiction. An exact repeated phase remains
repeated even if independent noise reduces variance. Band-specific t and a
avoid the exact one-scalar mixing obstruction, but do NOT guarantee retained
coarse/fine structure: Fourier content leaks across analysis bands and a
quadratic model can miss genuine structure within its support. The original
red alias-cancellation/diverse-phase foil remains essential.

## Why the proposed positive-budget limiter is not yet a selected algorithm

A nonzero DC-annihilating band has signed original-sample influence weights;
it cannot be a positive sample average. A reference formed as a difference of
positive smoothers is also signed, and its variance must include their shared
input cross term. Merely adding their variances would misstate the budget.

More decisively, for the valid restricted case
`h0=Sigma^-1*1/(1ᵀ Sigma^-1*1)`, any DC-preserving detail correction d has
`1ᵀd=0` and `h0ᵀ Sigma d=0`. Hence
`Var(h0+alpha*d)=Var(h0)+alpha²*dᵀ Sigma d`.
A strict ceiling at the positive reference variance forces alpha=0. This can
erase a genuinely observable feature; it is not evidence that the feature is
unidentifiable. A budget multiplier, attenuation prior, different target-aware
reference or explicit quality/noise tradeoff would be an additional algorithm
choice. None is silently selected here. Smoothing into the reference is not a
successful quality outcome.

The covariance above conditions on the realized focus weights. Because those
weights depend on noisy original samples, it is not the estimator's complete
sampling variance. Further, coefficient estimates at different bands/positions
reuse original sensels. Their exact cross covariance is the shared-input sum
of their signed influence-weight products. The eventual synthesis variance
must use that composite influence, or a disclosed conservative triangle bound;
it cannot assume independent bands. A small discriminator can retain influence
vectors and compute all these terms exactly. The current M/r/Q sufficient
statistics alone do not provide the full-image cross-band covariance.

## Cost and decision

Six-dimensional M/Q need21+21+6=48 f32 statistics per coefficient before counts
or fallback state. At roughly4/3 times a32-million-sensel CFA image, that is
about8.2GB for statistics alone. Original-source streaming avoids an aligned
volume but does not make per-source neighborhood work cheap. A claimed one-pass
full path must price these updates, the small solves and composite-noise work;
it cannot equate pass count with competitive speed. Tiles reduce resident state
only if original storage is reread or tile statistics are retained/spilled.

**Recommendation: do not implement the generic positive-variance-capped version.**
Its strict cap has the counterexample above, its rank fallback is not yet a
detail-preserving output rule, and its full-image covariance/cost are not solved.
The six-moment direct band functional is a precise possible next question,
distinct from full-value fitting; it is not currently an admitted estimator.
If root chooses a target-aware reference/explicit completion policy, the first
tiny test should be the existing same-channel near-fine/far-coarse witness plus
its flat and independent-color companions, with exact signed influence and
cross covariance. No new photographic benefit, noise guarantee or native
stacking result follows from this source proposal.
