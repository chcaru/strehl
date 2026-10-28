# Fixed constant-deflation adapter

Source-only implementation. `sensor-operator.py` imports the frozen parent by
SHA256536aa094... and exposes it as `base`; do not call inherited Parseval
mechanics on the projected operator. No parent file changes. Root owns runs.

Reexports: Config, Query, Source, Measurement, HaarPlan, norm_pair, SquaredNorm,
integrate_reference. `prepare` takes identical arguments/modes/metric override
and returns ProjectedProblem. Its `.original` is the exact base Problem;
`.projection` is ConstantProjection. Other original fields are forwarded.
`.forward/.adjoint/.rhs/.residual/.objective` are producing PB, B-transpose P,
Pb, and the projected correction-coordinate objective. Same source/noise/q.

`ConstantProjection(original)` evaluates actual B(C) for exactly three full
latent constant fields R,G,B, one G shared by both offset green phases. Exposes
`.columns` (three lists of source vectors), `.normalized_columns`,
`.column_norms`, `.gram_diagonal`, `.evidence`. Norms and actual disjoint support
are checked; normalize with actual measured scalar Gram values, not an assumed
analytic LL column or generic inverse. `.project(rows)` returns P rows;
`.coefficients(rows)` returns the three physical-DN constant coefficients;
`.nuisance_coordinates(rows)` gives normalized-column inner products.
`.restore(z,rhs=None)` returns X; `.restore_with_coefficients` returns (X,c).
Optional RHS is only for a frozen-B/q offset mechanical control.

`fit(projected_problem)` runs the exact parent64-step CGLS implementation on
projected coordinates, then restores physical X and independently evaluates
the original objective, full normal, projected normal and nuisance residual.
The denominator is the actual projected initial normal, not the old
brightness-dominated zero-start normal. The latter is reported separately.
Overall numerical pass requires parent projected convergence, both restored
full/projected ratios<=1e-5, and restored original objective no greater than
the constant-only initial solution. A zero denominator only passes a zero
corresponding normal. No tolerance relaxation or extra iterations.

Returned FitResult retains the old public fields x/output/status/converged/
iterations/history/evidence, plus `.correction_z`. x and output are restored
physical fields. History entries are explicitly labeled projected correction z;
they are not falsely represented as physical-X per-iteration objectives. Final
and constant-only initial original objectives are separately evaluated.
`save(fresh_dir)` saves complete latent/output/correction-z NPY plus receipt,
including finite numerical refusals. No truth is accepted by this API.

The usual weighted_forward_calls/weighted_adjoint_calls count the inherited
projected timing seam. Preparation adds three original B(C) calls. Restoration
and independent checks add four original B and four original B-transpose calls
inside fit wall time; these counts are explicit. Parent fitting integrates z
once for its internal return and the adapter integrates restored X once: two
reference-cell deliveries, with only the restored output presented as the fit.

The objective/minimizer set is unchanged in exact arithmetic. Zero-start
minimum correction norm can select a different physical-X minimizer; finite
work and roundoff also change. This is a solver/nuisance test, not a new prior,
optical model, proven reconstruction or photographic release.
