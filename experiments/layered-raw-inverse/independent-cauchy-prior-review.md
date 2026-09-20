# Independent Cauchy-prior source review

SOURCE-REVIEWED, with no reviewer execution. No material blocker remains for the fixed commissioning, two fits, and scoring.

The implementation applies `2*log1p((sum(deltaDN²)+1e-12)/(4*b²))`, with the original fixed `b²=2*V(2048)`, to native RGB sheet differences. Spatial-direction and sheet means, coefficient, original alpha TV/binary and normalized radiance L2 expressions are preserved. There is no signal-dependent scale or detached gradient. The same original160 near/far parameters, true-alpha buffer, injected noise, likelihood, optics, supported interior and L-BFGS limits are bound against visibility-1. Only near/far parameters are optimized. Independent scoring checks the entire initial near/far/alpha/pinhole arrays exactly, beyond relying on the fitting receipt's assertions.

The mathematical claim is appropriately limited. In normalized magnitude s, the derivative is `s/(1+s²/4)`: it peaks at s=2 and decreases afterward. The small-gradient curvature agrees with the original quadratic penalty, subject to the inherited negligible safeguard; the finite-amplitude penalties are not identical. Radial curvature becomes negative beyond s=2, so the new regularity term is nonconvex. Its cost grows logarithmically without bound; redescending influence is not a clipped or bounded cost. Equal local curvature alone does not prove equal flat-noise suppression.

Controls exercise the actual helper against independent literal arithmetic, differentiate both its zero curvature and the original Huber's, and check finite-edge derivatives through s=64. The isolated RGB impulse has four incident edges: the expected mean factor is `1/88+1/90`, giving forces `factor*16/65` and `factor*2` for Cauchy and Huber. This exposes weaker suppression of a possible false edge; it is not a quality success criterion. The brightness-offset witness uses exactly representable integer values, making its bit-exact image-term assertion defensible. That invariance does not extend to the separate radiance L2 term. Distinct near/far amplitudes exercise the sheet average and unchanged remaining terms.

The independent screen runs flat first and retains all original truth/held-out guards, including the bright stratum. Both core and ridge now require RGB **and chroma** error within1.02 of visibility-1, alongside live, truth-capped per-colour component protection. The rejected shot-prior output is descriptive only. A lower differently defined objective cannot replace any of these guards; accepted returned states, stationarity and image quality remain separate. The wrapper CLI matches, commissions before fitting, binds its source/reference chain, and checks immutability between stages.

A pass licenses only the proposed separately frozen stress: one new seed on flat/layered and one weak non-affine chromatic common-sheet pattern, with newly derived training-only initialization and paired Huber. A pure affine ramp would be blur-invariant and inadequate. Fix pattern amplitude/frequency before execution and require a live truth component; one extra seed cannot establish general noise robustness. No implementation of that stress is reviewed here. Unknown visibility and the failed continuum-optics guard remain unresolved; this screen cannot admit photographs.

Reviewed SHA256 bindings:

- `cauchy-prior.py`: `4ab14f613d4155ad5380e56f484bbf405b0616101971eac56bcf967d89970264`
- `cauchy-prior-plan.md`: `a75136d943dff47241f31050c2e8d53763757887c0c380abab356d859c4bc32a`
- `cauchy-prior-controls.py`: `84083ee81caab69d514482795403d4dfdf7248debf40b131d4f440247f9c1c56`
- `cauchy-prior-independent-plan.md`: `d02d67e42986d80386fbe41dcb721d51f746e4cd21feeca6013cc0aa2c43c794`
- `run-cauchy-prior.py`: `95620a93123d0bbd32db41dfaecf9f5675817c46c802bbbbfe0a5b04e4546528`
