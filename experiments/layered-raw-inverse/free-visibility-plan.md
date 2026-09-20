# Free visibility: paired original and matrix priors

Prospective generated test; author does not execute. Root runs one fixed pair
on each of flat, layered, far-only and angular-mismatch. The observed success
of the matrix prior with known alpha and an in-focus target licenses this test,
not an automatic-opacity or real-RAW success claim.

`free-visibility.py --source screen-1/output --out <new/output>` restores the
original160-step **free-alpha** two-layer state independently for each arm.
All three original parameters, `near`, `far`, `alpha_logit`, remain trainable.
Every stored parameter and initial near/far/alpha/pinhole field must reproduce
the original checkpoint exactly. No oracle-alpha directory or ground truth is
an input; the `TrainingOnly` facade permits only the original training indices
0,1,3,4,5,7,8. Held-out settings2/6 are predicted only after optimization.
The imported frozen matrix module defines helpers but its known-alpha runner
is never called; no supplied alpha is read or retained.

The only paired objective change is the image prior. `original` calls the
original state's `prior()` verbatim. `matrix` calls the frozen matrix-Cauchy
`selected_prior(state,config)` verbatim, including its original2048DN scale,
rectangular forward-gradient normalization and unchanged alphaTV, binary and
sheet-L2 terms. This does not implement the deferred projected-opacity or
L-BFGS-B proposal. Both arms retain original sigmoid/softplus parameters,
same-ray visibility before pupil integration, supplied64 rays/depths/foci,
common PSF, original u16 CFA observations, injected noise and digital16383
censoring. The optical/continuum discrepancy remains unresolved.

Both use the already commissioned Torch LBFGS settings: lr1, max_iter1000,
max_eval1400, history_size10, tolerance_grad1e-6, tolerance_change1e-11,
strong-Wolfe. The hard1800 actual-evaluation cap includes initial and final
monitors and failed closure attempts; one evaluation is the same seven-source
stream plus one prior. Backpropagate one original source immediately, retaining
no aligned-frame or multi-observation graph. Keep f32 image/gradient arithmetic
and the proven contiguous-gradient repair with exact logical equality. The
driver copies the frozen composite continuation mechanics rather than changing
or monkeypatching frozen code. No restart, parameter sweep, best-truth state
choice or quality-dependent stopping is allowed. Progress is printed every
100 optimizer iterations. Only the returned final state is scored.

Primary delivery is prospectively `B(alpha*N+(1-alpha)*F)`: apply the exact
frozen `in-focus-consumer.apply_in_focus` once to the complete96x96 composed
pinhole. The PSF is supplied f32 sigma0.7/radius3; the independent scorer uses
the same fixed64-square supported interior and frozen detail regions. Export
the unfiltered pinhole separately and preserve its independent verdict.
No observed mean or retained donor comparator is filtered again or reselected
by this fitter. In-focus success cannot rewrite the old pinhole failures.

Output `<case>/<original|matrix>/` contains initial-reconstruction.npz,
reconstruction.npz, state.pt, pinhole-rgb-f32.npy, in-focus-rgb-f32.npy,
predicted-cfa-2.npy, predicted-cfa-6.npy and receipt.json. Receipts bind original
states/config/observations and frozen code, exact initial fields, all trainable
parameter names, actual training reads, full closure history and final-state
monitor, source immutability and output hashes. Top-level bindings-before/after
and result.json cover all eight arms. A finite accepted return is not a
stationary or globally optimal solution; the gradient threshold refers only
to normalized softplus/logit parameters. The visibility/radiance gauge remains
and no alpha-truth recovery claim follows from good output images.

Independent controls must commission original-prior exactness, matrix-helper
reuse with live alpha gradients, unchanged initial fields/read scope and one
application of the PSF. Existing in-focus detail destroyers and fixed flat,
RGB/chroma, component and held-out guards retain rejection power. The paired
Huber result is the same-budget non-oracle comparator. The independent screen
also retains its stricter fixed-alpha visibility1 reference guards; using that
result as a required quality bar supplies no alpha information to either fit.
Far-only can expose invented near structure, and
angular mismatch can expose a low-residual but incorrect visibility explanation.
No likelihood decrease, smooth alpha or large hidden radiance alone admits the
method. Scoring and photographic permission remain outside the author script.
