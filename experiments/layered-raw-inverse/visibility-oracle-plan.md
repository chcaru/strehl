# Fixed-visibility oracle diagnostic

Prospective; no author execution. Keep model, earlier controls, continuations
and paired-prior experiments frozen. The paired composite prior failed; this
test changes visibility authority, not optics, priors, radiance bounds or noise.

For flat and layered only, the independent controls agent exports the exact
generated alpha to `<alpha-dir>/<case>-alpha-f32.npy`. The fitting script accepts
only finite 96x96 f32 alpha in [0,1], binds its file hash, and never imports truth
radiances. Start each arm from its original screen160 two-layer checkpoint,
requiring exact original near/far parameters and initial sheet images. Replacing
alpha intentionally changes the initial delivered pinhole; record that change
and save the initial reconstruction rather than claiming whole-state identity.

Only near/far softplus parameters enter the optimizer. Exact alpha is a buffer,
not a saturated logit or a parameter with a small learning rate. Reuse the
frozen `_State.prior` method verbatim: original hidden-sheet vector Huber with
fixed2048DN noise reference, sheet L2 and alpha terms unchanged. The alpha TV
and binary terms are constant for this experiment. The same coupled-pupil
forward, original-CFA noise/censor likelihood, supported interior and training
facade remain in force. Whole held-out observations cannot be read by fitting.

One L-BFGS invocation per arm: lr1, max_iter1000, max_eval1400, history10,
tolerance_grad1e-6, tolerance_change1e-11, strong-Wolfe. Hard1800 actual objective
evaluations includes initial/final monitors. No restart, truth selection,
coefficient change, opacity clamp or HDR cap. Stream one current frame backward;
retain exact logical gradient-contiguity conversion. Report raw softplus
parameter gradient max/L2 and all attempted/completed evaluations; only finite
normal returns below1e-6 are stationary in that limited parameterization.

Compare to the already retained `composite-1/output/<case>/original` results,
which use the same original initialization/prior and solver settings but learn
alpha. Independent scoring retains flat, rendered-pinhole truth and held-out
prediction guards; no new acceptance metric. Inspect stationarity in both arms
before attributing a difference solely to unknown visibility. Fixed alpha makes
the forward linear in physical radiance, but the predicted-variance likelihood,
softplus coordinates and censoring do not license a convex/global-solve claim.
Success demonstrates oracle-visibility headroom on this fixture, not an
automatic opacity estimator. Failure with adequate stationarity leaves the
radiance/objective model under suspicion; numerical refusal is not a family kill.

CLI: `python visibility-oracle.py --source screen-1/output --alpha-root <dir>
--out visibility-1/output`. Outputs `<case>/fixed-alpha/` contain initial and
final reconstruction, final state, held optical-index2/6 expected CFA arrays,
and a receipt compatible with the prior independent scorer. Predictions are
exported only after fitting and final monitoring. Root binds source files,
checkpoint/alpha manifests and process limits externally; each arm also checks
its immutable inputs before/after. Progress every100 optimizer iterations.
Two fits only, target under90seconds; no RAW decode or photographic admission.
