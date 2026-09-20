# One fixed prior-placement comparison

Prospective, 2026-09-19. The first160-step screen and both numerical
continuations remain recorded. This test changes one image-prior term and
does not recalibrate the optics, sensor or scene. Author executes nothing and
does not score output. Root runs only after independent source and mechanical
review. All previous model, design, controls and continuation files stay frozen.

Restore the same original `screen-1/output/<case>/two-layer` state for each
member of each pair, with cases in order flat, layered, far-only,
angular-mismatch; within each pair run original then composite. All eight
arms remain two-layer models, including the far-only *scene*. The original
objective calls the frozen `state.prior()` literally. The composite objective
replaces only the mean hidden-sheet image Huber with the identical Huber of
`P=alpha*near+(1-alpha)*far` in DN. The fixed2048DN scale, vector norm, image
coefficient, axis normalization, alpha TV/double-well and normalized sheet L2
are unchanged. Rebuild the other terms explicitly rather than subtracting
the old image term and introducing cancellation. The one-layer pure seam
returns `state.prior()` identically; it is a mechanical control, not an extra fit.

Original and composite image values coincide when near=far. Their independent
sheet gradients need not coincide for arbitrary alpha; the original splits
gradients equally, whereas composition distributes them by alpha. Independent
controls must therefore use the one-layer case for complete gradient identity.
Unequal constant sheets with varying alpha expose the old image prior's blind
direction. A compensating constant-composite case tests the opposite direction.
Preserve the `(near-far)*gradient_alpha` term; never detach the matte.

Use one fixed L-BFGS invocation per arm: lr1, max_iter1000, max_eval1400,
history10, tolerance_grad1e-6, tolerance_change1e-11, strong-Wolfe. No restart,
alternative schedule, quality-based state selection or parameter sweep.
The actual-evaluation hard cap1800 includes independent loaded-state and
returned-state monitors; reserve one evaluation for the latter. Each closure
streams the unchanged training indices0,1,3,4,5,7,8 through the frozen
original-CFA model/likelihood, backpropagates each mean loss immediately, then
the selected prior once. Gradients are f32 and converted to contiguous storage
only after exact logical-value equality; conversion counts remain recorded.
The line search receives the detached f64 sum of the same f32 scalar components.

Initial restored parameters and reconstruction must exactly match the saved
checkpoint. A training-only facade refuses held-out/non-scalar reads. Record
all attempted/completed evaluations, objective components, parameter gradient
max/L2, optimizer counts, elapsed time and progress at each100 iterations.
Only accepted finite final states with max-absolute raw parameter gradient
<=1e-6 receive `stationary_gradient`; other normal returns are
`nonstationary_return`, without guessing the internal stopping condition.
Exceptions/cap/nonfinite outcomes are numerical refusals, not successful
stationarity or a physical-family kill. No global optimality is claimed.

After optimization/final monitoring, save fixed final state, reconstruction,
receipt and expected-CFA predictions at held-out optical indices2/6. No held-out
observation is read to produce them. The independent scorer applies the frozen
truth/component/flat/held-out bars and retains the mismatch case's descriptive
scope; smaller training objective alone cannot pass. State/model/observations
and frozen-source hashes are checked before/after, including each arm's
checkpoint receipt. Real-photo admission stays false in the fitting receipt.

CLI: `python composite-prior.py --source screen-1/output --out composite-1/output`
from this directory, using root's bound CUDA runtime. Outputs preserve
`<case>/<original|composite>/receipt.json`, `state.pt`, `reconstruction.npz` and
`predicted-cfa-2.npy`/`predicted-cfa-6.npy`; top `result.json` binds all arms.
Root targets450seconds for all eight fits and may enforce a600second hard cap.
No author run, real RAW decode, full photograph or extra algorithm variant.
