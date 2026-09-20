# Independent review of the numerical continuation

2026-09-19. Source/choice review only; no optimizer, test, RAW read, or scoring
execution by this reviewer. **Ready for the one prescribed diagnostic run.**
The original 160-step screen remains rejected. Nothing here licenses a real
photograph or resolves the separate 64-versus-1024 pupil inadequacy.

The three arms answer different live questions: flat/two-layer tests whether
further descent reduces the measured latent compensation and output noise;
far-only/far-only tests the bright prediction failure without requiring layered
visibility; layered/two-layer tests whether the existing reconstruction benefit
and failed bright residual survive better optimization. There is no new model,
prior, noise constant, pupil, training set, or truth-selected iterate.

The continuation restores each exact saved parameter state and requires its
four reconstructed fields to equal the old saved arrays. It measures the loaded
checkpoint independently, rather than treating Adam's last pre-update history
entry as its objective. Its streamed likelihood, valid margin, source order,
single-layer depth and once-per-objective prior match frozen model.py. The f64
scalar is only the sum reported to line search; image operations and gradients
retain the existing f32 arithmetic. The training facade rejects held-out and
non-scalar reads; held-out optical predictions are exported only after fitting.

The fixed L-BFGS call and hard 200 attempted-evaluation cap are bounded and do
not select by quality. Failed attempts count, one evaluation is reserved for the
actual returned-state monitor, and numerical/export failures mark the state
unaccepted. A normal return with a large gradient is accurately named
`nonstationary_return`: it is not assumed to have reached an iteration limit.
Only accepted final raw-parameter max-gradient <=1e-4 receives the stationarity
label. Softplus/logit stationarity can conceal weak radiance sensitivity and is
neither latent uniqueness nor a guarantee of image quality. A decreasing
objective without this predicate leaves optimization unresolved.

The independent scorer uses only those three final checkpoints. Flat and
layered retain the original truth, mean/oracle/far-only references, protected
components and bright/per-CFA held-out bars. The continued far-only arm instead
has the explicitly approved 1.05 nonregression comparison to its own frozen
historical far-only reconstruction, plus the original prediction bars; it does
not replace the old two-layer qualification. Missing/refused numerical outputs
remain incomplete measurements. Global residual improvement cannot override
flat harm or a failed bright stratum. Source and continuation hashes are checked
and retained, and real-photo admission is unconditionally false.

Interpretation must follow the final data: improved truth and bright prediction
with lower objective would implicate unfinished optimization in the first run;
continued flat harm at a stationary state would implicate this unchanged
objective/parameterization, without proving an exact nullspace. A nonstationary
return cannot settle prior bias versus incomplete optimization. None of these
outcomes repairs the independent physical-quadrature failure.

Reviewed SHA256 bindings:

| File | SHA256 |
| --- | --- |
| model.py (unchanged) | `5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512` |
| convergence.py | `5f60810974fb791819d78402530a42b516f90cc14acf8ec489c03619df2c88e0` |
| convergence-plan.md | `85b6b28d067b1448257b5b46a447d10476846bc22a2636f9f0463200dbc62de6` |
| independent-convergence-score.py | `ed396953a185a545733192588230e81eb458cb517e1b405f1fd7fe87ace7ff94` |
| independent-convergence-plan.md | `2d4be0b667dfd17c8fe641fd28099ca6bd579e6b21bca1bae6e941fed7430597` |
