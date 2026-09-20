# Visibility update: an exact ambiguity must be separated from image failure

DERIVED / ARGUED, read-only. No proposed visibility update is presently justified
as addressing both flat noise and the observed reconstruction failure without
additional assumptions. Do not implement a new free-alpha rule on the strength
of the large hidden radiances alone. The current shot-noise prior also failed
the fixed-alpha flat guard; it is not a settled replacement to combine with a
visibility change.

**Exact global ambiguity.** In the supported interior of the current shared-ray
forward, choose any constant `0<a<1` and transform the sheets by

`alpha' = 1-a*(1-alpha); F' = F/a; N' = alpha*N/alpha'`.

Premultiplied near radiance is unchanged. Bilinear partition of unity gives
`sample(alpha')=1-a*(1-sample(alpha))`, so each ray's transmitted far radiance is
also unchanged. Therefore every focus prediction, diffraction/CFA observation,
predicted noise variance/censor likelihood, and pinhole RGB are unchanged in
real arithmetic, while alpha approaches1 and far radiance becomes arbitrarily
large as a decreases. This statement concerns the fully supported interior;
zero padding outside the latent array does not preserve the constant term.
The radiance/alpha priors change under this transformation, so they choose a
representation that the data itself cannot select. True alpha is extra oracle
information, even with perfectly supplied depth/optics.

A naive quotient `P=alpha*N, T=1-alpha, B=F` with `max(T)=1` also needs care:
at a maximizing pixel, alpha becomes0, so nonzero P there would require infinite
N. Dropping that constraint enlarges the finite-radiance model. An equivalent
representation retains a scalar s: `T=s*tau`, max(tau)=1, `Q=s*B`, with0<s<1;
data/pinhole use P,tau,Q, while the old prior uses
`alpha=1-s*tau, N=P/alpha, B=Q/s`. The scalar is selected only by the prior.
This isolates the exact ambiguity but supplies no new data evidence. Alternating
or profiling it is a numerical-conditioning experiment, not a justified
automatic visibility update; it is not commissioned here.

This does **not** prove sharp radiance is unidentifiable: the exact ambiguity
preserves it. Nor does it explain the rejected composite image by itself.
That saved fit changes the pinhole dramatically and worsens data NLL, so it
also moved in directions outside this equivalence. Treating alpha near1 or
hidden far80kDN as proof of a data-detectable visibility error would conflate
those two effects. The saved inspection remains valid about its lost image.

**Local sensitivity.** For fixed sheets, the response to coverage perturbation
v is the pupil average of `sample_near(v*N) - sample_near(v)*sample_far(F)`.
When both sheets are the same constant colour, this is exactly zero. Joint
radiance changes create further compensating directions. An alpha gradient
computed after freezing noisy sheet estimates can nevertheless be nonzero:
it is not independently supplied evidence for real visibility. Alternating
sheet/alpha optimization or changing sigmoid to projected [0,1] coordinates
does not remove this ambiguity. Binary/TV preferences supply decisions rather
than measurements. An arbitrary opacity or HDR cap would merely hide it.

The only defensible next **numerical consumer**, if later commissioned, is a
conditional data-sensitivity diagnostic: project the alpha response away from
responses attainable by refitting the sheets, rather than trusting the raw
alpha gradient. Implement it matrix-free with the existing forward/JVP/VJP,
fixed supplied noise weighting, and the already chosen sheet regularity; never
materialize an aligned stack or dense Jacobian. This is not yet a selection or
update rule: choosing which residual directions warrant a finite alpha change
still needs a falsifiable uncertainty/stopping contract. Each inner linear
iteration costs additional forward/adjoint passes over the training sources;
state storage stays O(native pixels), but the present per-evaluation timing
does not establish practical full-RAW cost.

Its cheapest necessary controls are an exact equal-colour flat (zero coverage
response), the explicit representation transformation above (unchanged data
and pinhole despite large hidden radiance), and a depth crossing whose coverage
change cannot be reproduced by the allowed sheet refit. The last must show a
live residual response before an update is even considered. Shifted/noise-only
sheet texture must not become an ownership label. Any eventual free-alpha
candidate must preserve the old radiance prior unchanged for the comparison,
use no truth masks or donors, and pass delivered flat noise, true component,
crossing and held-out prediction controls; map smoothness or likelihood alone
cannot admit it.

Decision: preserve this ambiguity and source-sensitivity finding; no automatic
visibility implementation is recommended yet. Accurate pupil integration also
cannot remove the algebraic ambiguity. References read: SYNTHESIS architecture
and storage constraints; composite-latent-inspection.md, the fixed-visibility
and directional records, and independent-shot-noise-prior-results.md. No new
measurement or execution was performed.
