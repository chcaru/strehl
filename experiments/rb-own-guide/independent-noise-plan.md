# Independent paired-noise arithmetic witness

Preregistered before execution. This is one helper called before the image truth
screen, not a second experiment campaign. The implementation author does not run
it. It commissions routing and arithmetic; synthetic noise shares the injected
model with the candidate and cannot calibrate that model.

For independent, identically distributed source-noise draws A and B, a linear
coefficient has `E[(L(A)-L(B))^2] = 2 Var(L)`. Eight pairs therefore use a sum
divided by sixteen. The candidate then applies the actual production spatial
energy smoother and multiplies the held gate once. There is no second scalar
beta: the differences have already passed through source gathering and the
actual Laplacian. A deterministic operand test verifies the divisor and routing;
independence of real probe generation remains a separate source/API check.

Fixed operator domain: 89 by 73 quads, production `level_sizes(...,7)` and actual
`Pyramid::build`, including clamped boundaries. Fixed small integer-valued fields
have distinct R/B patterns, deliberately unequal channels, and eight distinct
pairs. The literal independent oracle routes stored `[R,G1,G2,B]` into
`[R,0.5*(G1+G2),B]`, builds each production pyramid, sums the eight squared
coefficient differences, divides by sixteen, and calls the production smoother.
All bands must be live in R/B; otherwise the routing/factor fixture is invalid.

An anti-correlated green case has constant `(G1+G2)/2` despite both green fields
varying: its correct transported green energy is exactly zero. Averaging separate
green variances while dropping their covariance must instead give a positive
answer, explicitly exercising that wrong choice. A positively correlated twin
must give live green energy. Forming mean-green before the transform retains
both possibilities without estimating a covariance parameter.

Doubling every source residual while preserving its constant pedestal must
quadruple the transported energy. A wrong `/8` divisor or a second factor-two
noise multiplier must differ decisively from the literal oracle; these
destroyers are arithmetic sensitivity controls, not tests of camera calibration.
Fewer/more than eight pairs and nonfinite operands must be refused.

Routing compares actual Laplacian fields with the independently routed production
Pyramid fields bit for bit. Energy and scale comparisons require per-value error
at most `1e-5 + 2e-5*max(abs(expected),abs(actual))`, with exact zero for canceled
green. This permits ordinary f32 association while rejecting a factor-two error.
The image screen separately determines photographic benefit. Nothing in this
witness can admit quality, a new noise calibration, or a real-data render.
