# Independent fixed-visibility source review

2026-09-19. **Ready for the prescribed two-case diagnostic.** This is a source
and choice review only; no export, model fitting, scoring, RAW read or rendering
was executed by this reviewer or either author. Root owns execution. Earlier
screens and prior replacements remain rejected and frozen.

The intervention matches the causal question. FixedVisibility clones the
original saved near/far parameter tensors exactly, keeps their softplus mapping,
and stores independently supplied alpha as a cloned buffer. Only near and far
are optimizer parameters. Alpha is neither an optimized logit nor a value held
approximately by a learning-rate choice. The original sheet prior is reused
as the literal frozen method; image Huber, DN/noise scale, sheet L2 and alpha
terms remain. The last two coverage penalties become constants, as required.
The forward operator, CFA, likelihood, censoring, support and training order
are unchanged. No radiance ceiling or truth radiance is introduced.

The independent exporter writes exactly two alpha arrays and their manifest
from the frozen generated scenes. Its output carries no radiance or held-out
observation values. Fitting reads only these arrays, the retained checkpoint,
configuration and seven permitted observations. The original state is restored
strictly before copying the sheets; initial sheet values are checked against
saved arrays. Replacing alpha deliberately changes the initial pinhole image.
The scorer directly verifies that recomposition and reports `initial_quality`
using the same frozen metrics and references. Therefore an immediate oracle
recomposition benefit will not be misreported entirely as a fitting gain.

The fixed1000-iteration/1400-nominal-evaluation L-BFGS recipe, tolerances and
1800 actual cap match the retained free-alpha original-prior reference. Initial
and returned-state objectives are evaluated separately. Logical gradient
contiguity, finite-state acceptance, actual evaluation counts and training-only
read indices remain checked. Alpha must remain byte-exact after fitting and
in the saved final arrays. Held optical-index predictions are produced only
after optimization; their observed values enter only independent scoring.

References are composite-1's original-prior arms, not its failed replacement
or a truth-selected iteration. Flat absolute mean and paired-reference bars
remain, as do layered image, bright/CFA held-out and component requirements.
Paired core/ridge RGB <=1.02 and truth-capped component retention >=.98 protect
real detail while permitting removal of reference overshoot. A non-live or
weak reference component fails its bar rather than being silently skipped.
Missing/refused numerical arms remain incomplete; `initial_quality` is still
reported. Fixed-arm and free-arm stationarity/status are available separately.

Any improvement establishes bounded oracle-visibility headroom, not a method
to estimate visibility from photographs. Same budgets need not yield equally
converged solves, so nonstationarity still limits optimum-level attribution.
Correct alpha is not uniquely meaningful on the constant flat scene; the
relevant evidence is whether removing its spatial freedom changes delivered
radiance error. A failure would show that known alpha is insufficient under
this recipe, not prove that all layered inverses fail. The independent64/1024
pupil inadequacy and real-photo refusal remain explicit.

The wrapper correctly calls positional `prepare`, then the fitter with
`--source/--alpha-root/--out`, then positional `score` with the saved reference.
It binds all imported experiment helpers, plans, this review, both starting
checkpoints and both reference arms; generated alpha files are bound before
fitting and checked after fitting/scoring. The fitting process has a180second
hard cap. No further implementation or controls are requested before this run.

Reviewed SHA256 bindings:

| File | SHA256 |
| --- | --- |
| visibility-oracle.py | `b2b718df8b13be042c8f51a07287ebbe2872936baacfd5b52c8a83dbaf91d6a9` |
| visibility-oracle-plan.md | `5bfcdde9a931798be00c7c8dc18c7aa2b4845096075516c05d60d6d6dab9e043` |
| visibility-oracle-controls.py | `ee9912c5b9d415f5013e473eba0228af39082b27051873a3da1ad97733769922` |
| visibility-oracle-independent-plan.md | `9602a949ba085067eb26f38f0147f5cf8602b29d307ec8ffff740de8c870411d` |
| run-visibility-oracle.py | `e86904d8c5c2b3faba4e6054816a1b590fabd6277a840b9c7e501de5d461856f` |
