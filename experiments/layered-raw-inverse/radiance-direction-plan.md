# One saved-state radiance direction, plus shifted placebo

Prospective numerical diagnostic only; author does not execute. Use exactly the
accepted visibility-1 layered fixed-alpha checkpoint, restoring all tensors and
reproducing saved reconstructed fields. No optimization, prior coefficient,
solver, optics or radiance-cap change. Root owns the external source/process
binding wrapper; this script does not create another orchestration framework.

Independent controls supply two finite nonnegative native HWC f32 DN vectors:
the true far-sheet glint component and its +20native-x zero-filled translation.
Fitting code reads neither true full sheets nor held-out observations. For each
vector evaluate scalar t=0,+.001,-.001 with near and alpha fixed. Use
`far_normalized + t*(direction_DN/dn_scale)` through the original fields/forward
and original sheet prior, preserving exact t0 fields and the physical-DN
direction in real arithmetic. f32 arithmetic stays explicit. Refuse negative
perturbed far radiance; never clamp it. Values above digital saturation remain
allowed latent radiance under the unchanged censor likelihood.

Stream the original training indices only. At t0 compute autograd derivatives
of mean training NLL and original prior separately, then their sum. Report their
values and central finite differences from the two fixed steps. The saved
final-monitor objective must agree termwise within1e-6 absolute +1e-6 relative.
Predeclared derivative agreement is absolute1e-3 +.002*abs(autograd derivative),
accounting for f32 subtraction at this small step. Report disagreement without
changing step/tolerance; near-zero or disagreeing signs are inconclusive.

If the data derivative is negative but the prior makes the total positive,
the objective locally opposes adding this supplied component. A negative total
offers a local descent direction despite the optimizer's previous stopping.
Neither result identifies all remaining error or a global optimum, and a
lower objective is not itself evidence of better truth. The independent scorer
checks the glint direction's truth action and the shifted placebo. Export base
and plus/minus delivered pinhole images solely for that scoring; no held-out
predictions or new reconstruction selection. Require saved state unchanged.

CLI: `python radiance-direction.py --checkpoint visibility-1/output/layered/fixed-alpha
--source screen-1/output --directions <directory> --out <directory>`. Inputs are `glint-dn.npy` and
`shifted-glint-dn.npy`. Output root contains base-pinhole-rgb-f32.npy and
result.json; each named direction contains minus/plus-pinhole-rgb-f32.npy.
No original camera RAW decode, full photograph or automatic admission.
