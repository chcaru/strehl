# Diagnose the rejected Cauchy colour error before another prior

READ-ONLY DESIGN; no array calculation, fit or new quantitative result here.
The retained result establishes improved RGB/held-CFA prediction and substantially
worse R-G/B-G truth error. Near-unit colour-template projections do not exclude
spatial error orthogonal to those templates. The saved layered fit is also
nonstationary, so this is a diagnosis of that output, not its objective's optimum.

The code supplies two plausible mechanisms. First, the Cauchy derivative for
an RGB sheet edge d is `d/[b²*(1+||d||²/(4*b²))]`: a strong edge in one channel
reduces restoring weight on small deviations in every other channel. The
quadratic curvature transverse to a strong colour edge decreases as1/||d||².
This is a real consequence of the shared norm, not evidence that it caused the
measured error. Second, the identity-pregeometry model observes a fixed RGGB
lattice at every focus. Diffraction and defocus can attenuate high-frequency
chromatic modes strongly before CFA sampling. Good sampled predictions can
coexist with poor delivered RGB. Multiple focus kernels may constrain aliases,
so call this possible ill-conditioning, not a proven exact chromatic nullspace.

Recommend ONE saved-array diagnostic, with no objective or forward change.
For truth and the retained original-Huber, shot-prior and Cauchy pinhole arrays,
form the same signed error coordinates used by the colour score:
`e1=(R-G)_output-(R-G)_truth`, `e2=(B-G)_output-(B-G)_truth`.
Use the frozen whole/core/ridge regions. Record signed means and total error
first, then an orthonormal two-level Haar decomposition of every fully contained
native4x4 error window: twelve native2x2 detail coefficients, three4x4 detail
coefficients, and one block-common coefficient per colour-error coordinate.
Sliding windows avoid choosing one favourable CFA/block phase. Report the
four native anchor parities separately as a sensitivity check, with counts.
Each window's squared error exactly equals the sum of its16 coefficient squares;
verify this identity, and disclose overlap rather than treating windows as
independent samples. This is an error decomposition, not a new quality gate.

Commission it with constant colour bias (block-common only), period-two
chromatic checkerboard (fine detail), and a fixed broad colour ramp. Include
zero error and axis reversal to catch sign/layout errors. Keep the original
native image/error views and existing chroma scores; discarded boundary windows
and their support counts must be explicit. No interpolation, tone adjustment,
fitted frequency cutoff or selected-best region is needed.

If the excess is block-common and signed, an alias-only explanation is weakened;
investigate broad colour balance/spatial reconstruction instead of adding a
high-frequency colour penalty. If the excess is predominantly native2x2 detail
and phase-sensitive, it justifies a later sampled-forward sensitivity probe of
those modes, not immediate colour smoothing. Strong true-colour edges can also
produce fine error, so this diagnostic cannot establish a CFA cause or authorize
discarding genuine colour detail. Colour-direction versus magnitude penalties
and matrix-gradient coupling therefore remain unimplemented choices.

Inputs already exist in cauchy-1, shot-prior-1, visibility-1 and the original
screen truth exports; no original camera RAW or new fitting is required.
