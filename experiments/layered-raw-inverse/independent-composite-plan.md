# Independent fixed composite-prior comparison

Only the image Huber term changes: average hidden-sheet regularity versus
regularity of delivered P=alpha*F+(1-alpha)*B. The noise likelihood, supplied
optics, alpha TV/binary terms, radiance L2 and coefficients remain fixed.
This is a new objective comparison; prior failed screens remain failed.

Root first runs `commission --out <newdir>`, then executes both objectives
from identical screen-1 two-layer checkpoints on flat, layered, far-only and
angular-mismatch inputs. Both get the same fixed LBFGS bounds/stopping criteria
(1000 iterations,1400 nominal evaluations,1800 actual cap, gradient1e-6,
change1e-11). The scorer's `score --source <screen-1/output> --comparison
<paired/output> --out <newdir>` mode reads only the prescribed final outputs.
There is no selection of iterations, regularization strength, or fixtures by
truth, heldout observations, or image quality.

Three small mechanical controls precede fitting:

- Constant unequal sheets F=c+d/B=c-d, coverage .5+.02*sin(2*pi*x/8).
  Hidden-sheet image gradients vanish while delivered texture is nonzero.
  The new term must match an independent f32 vector-Huber formula and have
  positive derivative with respect to coverage amplitude.
- Varying coverage .5+.1*sin with F=c+d and B=(c-alpha*F)/(1-alpha) gives
  constant delivered RGB. The new image term must be approximately zero while
  the old hidden-sheet term is live. This is prior algebra only: equal pinhole
  images need not have identical defocused observations.
- One-layer prior value and radiance gradient remain exact. A deliberately
  wrong composite .5*(F+B), which ignores coverage, fails the escape control.
  Two equal sheets are not used to claim independent sheet-gradient identity.

For the image comparison reuse the frozen independent-controls.py unchanged:
same original u16 observations, truth, training7, withheld2, noise, censoring,
valid region, physical-adequacy record and all original image/prediction bars.
Original and composite arms are scored separately. Flat composite RGB/chroma
must each be <=1.05 training mean and <=1.05 paired original objective. Existing
bright-stratum prediction checks remain binding even when global RMS improves.

Add paired protections, without replacing old bars. On structured cases,
composite core/ridge RGB error must be <=1.02 paired original objective. On
layered and angular-mismatch cases, each colour's glint and glint-free ridge
component recovery must retain >=.98 of paired original recovery capped at1;
the original recovery must be >=.5 and template live. The ridge component
remains fixed [39,31,63,41]; whole/ridge/crossing RGB regions remain unchanged.
Flat gain cannot compensate any failed component or prediction stratum.

Angular-mismatch remains descriptive: if heldout prediction fails, report screen
refusal; no claim that the model implements an automatic adequacy gate or must
detect every mild mismatch. Known in-family image/prediction and paired bars
are reported separately from solver stationarity. Nonstationary returned states
cannot establish an objective-level optimum, even with matched budgets.

Input/checkpoint/model/control hashes, same starting state and solver settings
are required for both arms. Missing outputs/numerical refusals are explicit
measurement failures, not image-quality verdicts. The64/1024 physical mismatch
still blocks real-RAW licensing. No calibration, canonical-merge, or SOTA claim.
