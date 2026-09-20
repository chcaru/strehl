# Shot-prior assessment: flat variance, not brightness drift

**Decision:** retain the layered gain as a bounded result, retain the overall
rejection, and keep any next image-prior test separate from the visibility
update. Recommend ONE fixed Cauchy vector-gradient prior on the **original
2048-DN scale**, as proposed by root, rather than the TV alternative considered
below. It preserves the successful local flat curvature while weakening the
large-edge shrinkage implicated by the earlier direction probe. This is an
unverified prior-family change, not coefficient tuning or a local flat selector.

## What the current result actually establishes

**MEASURED by the retained root run**, not rerun here: flat RGB/chroma error is
6.33864/9.12643 DN, versus mean6.01845/8.36762 and visibility1 5.67202/7.92557.
Mean per-colour error remains only `[+.117,-.244,-.039]` DN, essentially unchanged
from the reference. The visible failure is increased variation, especially G:
its signed p01/p99 changes from `[-14.00,+12.09]` to `[-17.43,+15.48]` DN.
R also widens; B scarcely changes. The commissioned bright-offset incentive is
real, but these flat results do **not** establish a substantial mean-brightness
escape. Adding a brightness/Jacobian correction is therefore not the identified
remedy for this failure.

**DERIVED from the actual prior:** near a constant channel value mu, the new
quadratic gradient penalty is `dS²/[4 V(mu)]`, while the old one is
`dS²/[4 V(2048)]`. At the fixture's RGB `[2500,3200,2000]`, the new/old curvature
is approximately `[.82,.64,1.02]`. Its weaker R/G smoothing has the same ordering
as the observed flat tails. This is a specific explanatory prediction, not
proof that optimizer progress and latent coupling have no contribution.
Both final states remain nonstationary; shot-flat stops at gradient8.92e-6
versus the declared1e-6, so no optimum comparison is established.

The structured gain must remain protected: all fixed layered bars pass,
held bright error is1.46860 supplied sigma, glint recovery is
`[.98519,.96849,.98546]`, and the true glint-free filament remains intact by
the existing component test. A flat-only fix can readily destroy that result.

## Representation and identifiability

With constant known coverage a, observations have the form
`y_k = CFA[a K_near,k F + (1-a) K_far,k B] + noise` on supported pixels.
Constants in the two sheets have an exact data ambiguity:
`F -> F+(1-a)c`, `B -> B-a c` leaves their delivered mixture and every blurred
observation unchanged. Spatially varying modes need not be exactly ambiguous:
different focal kernels can separate them, while some are weakly observed or
unsampled through CFA. Do not promote this exact DC statement into an asserted
nullspace for every spatial frequency.

The mean estimates the constant delivered mixture without estimating two sharp
colour fields or undoing blur. The inverse must regularize those additional
degrees of freedom. A small training-likelihood reduction can therefore buy
unwanted reconstructed variation while the held views still look noise-like:
flat held RMS1.003/1.011 passes. Neither good held prediction nor fixed alpha
alone protects the pinhole image. Merely reparameterizing into common and
difference fields leaves the estimator unchanged if its objective is unchanged;
forcing F=B everywhere would erase legitimate depth separation. Neither is the
recommended correction.

## One fixed, rejectable next prior

**ARGUED, not implemented:** let
`s=sqrt(sum_RGB((S2-S1)^2)+1e-12)/sqrt(2*V(2048))`, exactly the original
fixed-DN norm. Use `rho(s)=2*log1p(s^2/4)` instead of Huber, retaining the existing
spatial/sheet averaging and every other objective term. No new scale,
coefficient, threshold, local switch or variance estimate is introduced.

Its expansion is `.5*s^2 + O(s^4)`, so the local quadratic penalty is exactly
the visibility1 reference's, including G, rather than the weakened shot-prior
curvature above. Its derivative is `s/(1+s^2/4)`, asymptotically `4/s`, versus
Huber's constant2 above s2. This directly separates the two observed needs:
retain the stronger small-gradient constraint, reduce the large-gradient force.
The norm scale2 is retained, but Cauchy is already softer near it: its derivative
at s2 is1, not Huber's2. Do not claim identical moderate-edge behaviour.

The alternative vector-TV limit on the stabilized norm has constant slope2
above its tiny numerical epsilon. Although it could suppress flat noise, it
also strongly penalizes weak real gradients and makes the numerical objective
stiff near zero. SYNTHESIS fact405 (line989) already records TV losing on a
non-piecewise-constant object. Cauchy is the more direct next falsifier for the
measured local-curvature/bright-shrinkage split; this is not a claim it is safe.

Its explicit danger is nonconvexity: `rho''` changes sign above s2, and a large
spurious edge can receive little restoring force. Weak latent modes, isolated
bad-pixel evidence and initialization may therefore produce false sharp colour
or different local minima. Unchanged radiance L2 prevents an unconstrained
infinite-amplitude direction; it does not establish correct latent radiance.

Commission the local slope and large-edge derivative against independent
literal calculus, including an isolated impulse which demonstrates the weaker
restoring force rather than pretending it is suppressed. Then use one fixed
known-alpha flat/layered pair from the same160-step sheets and solver budget.
Keep every original and paired image, bright-heldout and coloured-component
bar. A fixed weak smooth coloured ramp is the cheapest added image falsifier
for loss of ordinary gradual structure; a fixed single-observation impulse on
flat is a useful model-mismatch refusal check if this route proceeds. Neither
may be scored as true recovered detail. Stop on failure, no strength or epsilon
sweep. Numerical failure remains distinct from a model-quality rejection.

No real-RAW admission follows even from success; known visibility and the
failed64/1024 optical-adequacy guard remain unresolved.

Sources: `shot-prior-1/scored/result.json`, `shot-prior-1/commission/result.json`,
and the exact executed commands in `shot-prior-1/{fit-process,scoring-process}/invocation.json`.
Code locations: `shot-noise-prior.py:22` (image prior), `:41` (remaining terms),
`:120` (training likelihood); `model.py:84` (coupled-ray forward), `:176`
(original fixed-scale Huber). This assessment read saved JSON and source only;
no numerical experiment, refit, model forward or source edit was performed.
