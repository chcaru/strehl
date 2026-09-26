# Free band-weight constructive oracle

Preparation only. This is a truth-assisted diagnostic on all seven formerly
held cases from `learned-band-guide`, not training, validation, a deployable
predictor, a photographic result, or a repair of its failed checkpoint.

Prior content: BUILD-HULL sections14-18 distinguish per-band coefficient
convexity from the reconstructed CFA/RGB hull; section16.4 locates InputRange
before demosaic, section17 retracts the anti-clamp recommendation and section18
corrects octave accounting. None optimizes the permitted weights against truth.
V-ORACLE measures source/merge through-focus power on flowers-cpl, with later
CA/channel qualifications; it constructs no feasible output. BUILD-BLEND's
`blend-truth` oracle copies the nearest known-depth frame: texture RMSE is48.6DN
against134.0DN for that historical blend, but its edge oracle is explicitly not
a valid floor (2198DN against143/240DN). `build-demosaic-truth` substitutes true
RGB planes before gather, outside the measured-source coefficient constraint.
The modern optical-support veto only multiplies canonical weights by supplied
visibility and keeps a no-clean-source fallback; its damaging result does not
solve free weights. Consistent reconstruction holds fused targets and changes
synthesis, also a different feasible set. The mechanical prior-art search was
`prior_art.py oracle convex representability`.

Reuse the frozen, commissioned `learned-band-guide/train.py` loader,
reconstruction, CUDA setup and prediction writer unchanged. Each source/band/
location gets an independent f32 logit; its weight is exp(logit-max_source).
The same nonnegative weight serves all four original linear CFA coefficients.
Source coefficients, current terminal Mean, InputRange, WB/range and final MHC
remain fixed. No source argmax, signed coefficient, learned RGB, width, noise
constant, source set or model change is introduced. Max-normalization gives
positive denominator mass; underflowed zero weights are permitted.
The helper and retained dataset are hard-pinned to their commissioned SHA256s
before import/use; the retained successful native/Python commission must bind
those same hashes. A fresh oracle commission cannot license a changed consumer.

Both commissioning and the oracle use uniform zero logits, Adam learning
rate0.03, exactly1024 updates, equal-case complete-image RGB MSE, f32 deterministic
CUDA, and a180-second optimization cap. Only the final iterate is emitted; no
best-iterate selection, alternate start, sweep or cap rescue. Grouping cases by
source count is batching only; each case has exactly equal loss weight. The
source-set means/features loaded by the existing helper are not consumed by the
free-weight solver. No original RAW or new native export is required.

Prospective numerical conditioning choice, fixed before any run: Adam epsilon
is explicitly1e-15 rather than its default1e-8. Each free coefficient receives
the gradient of a normalized full-image mean, so a small per-pixel gradient
(for example1e-12) would be suppressed by the default denominator despite a
feasible target. Its squared moment (for example1e-24) remains representable in
f32. This is an algebraic conditioning rationale, not a measured gradient claim
or quality tuning result. Both commissioning and oracle use the same epsilon;
it is recorded and bound by the successful commissioning fit.

Before the truth-assisted solve, the independent checker commissions the actual
autograd direction and an opposite-direction foil, then the identical solver
must recover meaningful error reduction toward two explicitly achievable
targets: the retained prescribed-weight RGB outputs for held-flat-n5 and
held-curved-bright-occlusion-n9. Its independent fixed bars and evaluation live
in `independent-plan.md` and `independent-check.py`. Known feasible targets check
the instrument, not all target representability. Seven true-image targets may
still be outside the captured, clamped, demosaiced feasible set.

Outputs use existing `write_prediction`: case-NN directories contain complete
CFA, RGB and three weight arrays; predictions.json binds each case and array.
fit.json records initial/final errors, fixed schedule, bindings and cap/runtime.
The independent checker reuses the frozen quality judgments and labels every
case truth-assisted. A passing actual-consumer witness proves that particular
weights can improve those tiny images; it does not establish learnability,
photographic transfer or noise calibration. An unsuccessful local fit is
inconclusive about the global optimum, never a representability ceiling.

Root owns execution. Commands are `solve.py commission --dataset D --out C`,
`independent-check.py check-commission --commission C --dataset D --out Q`,
`solve.py solve --dataset D --commission Q --out O`, and
`independent-check.py check --dataset D --predictions O/predictions.json --out R`.
The solve requires Q/commission.json to pass and bind its source fit. No build, training
rerun, native photo or production/default modification is commissioned here.
