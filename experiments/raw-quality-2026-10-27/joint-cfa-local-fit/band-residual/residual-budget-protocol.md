# One saved-flat residual budget

Source preparation only. Root executes once after the actual comparator,
120s wall /480 CPU seconds /4GiB /4 CPU workers. No fit, RAW, new fixture,
changed weighting, new image prior, or full photographic adapter.

`residual-budget.py --out <fresh-absolute-output>` pins the frozen operator,
controls and fixture helpers plus original fixture-manifest and failed cost
result SHA256s. The result pins complete latent/output NPY; the manifest pins
all seven original u16 files, maps, phase convention, supplied model and truth.
Require OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=4. Root's wrapper
also binds this script, Python and resources. The entry rebuilds the exact
small A/H/q once and checks all original/geometry/metric hashes against the
saved fit; it does not call `fit`.

Let X0 be the known2048DN continuous flat in all channels including apron,
E=Xsaved-X0, n_i=y_i-A_iX0, and r_i=A_iXsaved-y_i. Evaluate A_iE, n_i, r_i
separately; never conflate signal error with fitted observation residual. Keep
each complete native2D field, H coefficients, original temporal variance,
H marginal variance and frozen q. Record per-source/physical-phase DN RMS and
RMS divided by the supplied temporal sigma. This sigma is not a spatial scene
standard deviation or a residual-derived estimate.

For every phase/level/kind, retain raw squared norms, marginal-sigma units and
contribution to the frozen q-weighted objective, both per source and aggregated
over all seven. Report original sensel count once, global metric scale, objective
at known X0 and at saved X, and complete D(E) plus the pre-existing96x96 support.
The saved full128x128 delivery must reproduce bitwise. Linearity roundoff is
reported, not used to tune quality gates. There are no new quality thresholds.

If original A_iE is small relative to temporal noise while D(E) is large, that
supports poor observation of this particular delivered error direction. If
original error is substantial but its AC contribution is suppressed in the
weighted objective, the fixed admission is implicated in weak consistency.
Both can coexist. Neither observation proves a spectral nullspace, establishes
rank, identifies the exact optimizer cause, or licenses a replacement recipe.
Known truth is used only to diagnose the already rejected output; it is never
used in reconstruction. All input bytes/stats and in-memory original CFA are
rechecked at completion. No frozen source is edited by this observation.
