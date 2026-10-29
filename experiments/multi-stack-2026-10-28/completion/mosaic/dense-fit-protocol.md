# Correlated FIT constraint commissioning

This research-only diagnostic reuses the completed mixed, focused-only and
augmented measurements. It reads no original image, acquires no new native
measurement and consumes no fresh validation island. The existing negative
production controls remain unchanged. Reused held sites have informed this
hypothesis and are known-scene diagnostics only.

The production selector requires distinct complete physical support for both
FIT and held sites. This arm asks whether overlapping, directly measured FIT
constraints help model geometry without increasing evidence/certificate counts.
Full attempted support still excludes the same held islands.

For each training set separately:

1. Apply the existing exact-point source-alternative coherence bar0.5quad and
   retain one deterministic representative of each coherent site. Keep every
   original and refusal in the bound source artifact; record dropped/conflicting
   groups explicitly. No fitted-model residual is used for this operation.
2. Build connected components from complete original/pass-gauge query footprints
   intersecting in either view. Compute the existing greedy nonoverlapping-site
   count within that training set. A component receives total fitting weight
   equal to that count, distributed equally over its coherent training rows.
   This is a declared total-weight normalization, not exact covariance, Fisher
   information or a statistical effective sample size. Independent counts and
   certification loops remain the original physical-support counts.
3. Use the production joint mesh fitting operator, with tether0.01, Huber0.5,
   six IRLS iterations and all other numerical defaults unchanged. The fixed
   candidate family is native mesh spacing512/256/128 crossed with smoothness
   2/0.2/0.02: nine models. Compute the initial two-view similarity from that
   training set only, using the same declared row weights. Do not reuse a global
   fit made from all current observations inside cross-validation. Original
   per-pass maps and focus fields remain the already frozen upstream condition;
   this is not a new photon-blind assessment of those upstream estimators.

Select among the nine models by exactly five spatial FIT folds:
`(3*floor(x/512)+floor(y/512)) mod5`. Purge every potential training row whose
complete footprint intersects any test row in either view. Only then form
training source coherence, overlap components and fitting weights. Nothing
derived from test target values may change a training coefficient, row or weight.
All test rows remain in scoring, including conflicting alternatives; no
favorable-survivor filtering. Score using a geometry-only total-weight policy
and retain per-row errors and conflict diagnostics. Every candidate must complete
all five folds with at least eight independent training sites, finite predictions
for every predefined test row and successful numerical fitting. Empty or
underconstrained folds are explicit refusals, never silently omitted. Ties use
the declared spacing/smoothness order.

Report both common-gauge residuals and symmetric backward-placement errors in
native pass-quad coordinates; missing/folded inverse predictions refuse the
candidate rather than benefiting from a shrinking coordinate system. Choose
the model using the weighted native-placement FIT-CV error only. The0.5quad
placement/support/hull bars remain unchanged. After selection, evaluate the
known external held sites once, retaining their existing physical independence.
No output map is licensed for photographic blending by these diagnostics.

Controls must show duplicate/overlap weight accounting, isolated components,
complete-footprint fold purging, fixed missing-fold refusal, and actual
test-value poison leaving training weights and fitted vertices unchanged.
Include measured-order curved fields and outlier/depth-jump negatives. These
commission the operator; they do not calibrate real data or prove photography.
At most four workers and4GiB are allowed; root owns process scheduling.
