# One objective change: regularize delivered radiance

2026-09-19. Design advice only; no execution or frozen-source changes. The
first screen remains failed. Convergence-2 improves the structured cases but
does not establish their stationarity; the flat arm satisfies the existing
loose parameter-gradient predicate while retaining its noise failure. Those
results do not yet attribute the flat defect to alpha or the bright residual
to the prior.

**Choose prior placement first, not signal-dependent rescaling.** Replace only
the image term
`mean(Huber(near_DN), Huber(far_DN))` with
`Huber(P_DN)`, where `P=alpha*near+(1-alpha)*far` is exactly the delivered
pinhole RGB. Keep the present coefficient, vector-Huber shape, fixed2048DN
reference scale, alpha TV/double-well, weak sheet L2, original-CFA likelihood,
censoring, optics, initialization and solver policy unchanged. Do not add the
new term on top: that would also increase overall regularization strength.

The specific escape direction is algebraic:
`deltaP = alpha*deltaNear + (1-alpha)*deltaFar + (near-far)*deltaAlpha`.
The old image term does not penalize the last contribution when the sheets
stay fixed. Its alpha penalty is not scaled by the resulting DN change.
Regularizing P addresses this directly. It does **not** identify hidden sheets,
which can retain a nullspace; the existing weak coercive L2 stays. It can also
oversmooth real depth/matte edges, so the crossing ridge and glint-core truth
guards remain essential. This is a falsifiable explanation, not a diagnosis
already established by the flat result.

**Small fixed comparison.** Run the old and replaced objectives from the same
saved160-step checkpoints on only flat/two-layer and layered/two-layer, with
the same prospective numerical budget and all original output/held-out bars.
The fixed-far one-layer term is algebraically unchanged: commission exact
objective/gradient equality there rather than spending another full fit.
Also check equality when near=far, and use fixed unequal constant sheets with
a varying alpha to show the replacement sees a real delivered-image edge the
old image term misses. These are operator controls, not quality evidence.
Count a gain only if flat RGB/chroma and the existing whole/core/ridge/detail
and held-out requirements jointly pass; no term-specific favorable metric.

**Numerical adequacy must accompany that comparison.** Freeze one larger
common work ceiling before running; do not sweep budgets or choose a state
using truth. Retain the initial/final actual objective and raw gradients.
As an operational stopping check, require both max-absolute parameter gradient
<=1e-5 and supported-pinhole RMS change<0.1DN over the final20 accepted updates,
recorded without truth or held-out observations. A solver that stops earlier
must explicitly report the missing stability evidence. These are prospective
numerical tolerances, not camera calibration or proof of a global optimum.
Failure means a budget/stagnation-limited comparison, not a physical-family
kill. A lower objective alone remains insufficient.

**Signal-dependent scaling is a separate hypothesis.** Fixed b gives bright
observations less data precision while retaining the same prior scale, so
relative regularization can grow with shot variance. Scaling b with signal
could reduce that imbalance, but cannot guarantee removal of bright-detail
bias. Making b depend on freely optimized latent radiance introduces another
escape: brighten the latent to weaken its penalty. A later detached scale
derived from declared training data and the injected model would still change
the prior, its colour balance and its noise coupling. Do not combine it with
this placement test or claim it explains the current bright residual.

If the fixed replacement passes, stop adding tiny prior variants: the next
engineering gate is adequacy of supplied optics/focus coordinates on an actual
original-CFA patch and a bounded reconstruction there. The current discrete
oracle-optics success, if obtained, cannot itself authorize a full real stack.
