# One fixed matrix-Cauchy sheet prior

Prospective; no author execution or change to any existing experiment. For each
native RGB sheet, form forward differences right and down, with an exactly zero
rightmost dx column and bottom dy row. Divide by the original
`b=sqrt(2*(gain*2048+read_variance+1/12))`; multiply dx by sqrt(W/(W-1)) and dy by
sqrt(H/(H-1)). For these two RGB columns use

`log1p((sum(dx²)+sum(dy²))/4 + sum((dx cross dy)²)/16)`.

Average over the entire HxW domain, then sheets, with coefficient1. This is
logdet(I+J-transpose*J/4), evaluated without SVD or subtraction of nearly equal
Gram products. No norm square root is needed, so no additional epsilon is
introduced; a constant image has exactly zero image loss. No coefficient,
direction, noise or rotation is fitted. Noise remains supplied once.

The dimension factors preserve the **global small-gradient quadratic term** of
the original per-direction means in real arithmetic. They also change finite-
edge behavior; do not claim exact finite-loss equality. The construction is
invariant under orthogonal RGB-axis transforms at the gradient level; that
algebra is not a claim that arbitrary RGB-rotated radiances remain physical.

For a strong rank-one edge A*c*u-transpose and a weak perturbation
epsilon*d*v-transpose with c perpendicular d and u perpendicular v, loss splits
into log(1+A²/4)+log(1+epsilon²/4). Independent weak-singular-direction curvature
is therefore .5 at zero. This improves on separate direction-Cauchy only when
the strong edge occupies both discrete spatial directions; an axis-aligned
example already has an unpenalized-by-the-strong-edge second column.

The decisive limitation is a same-spatial-direction perturbation
epsilon*d*u-transpose. It stays rank one and its weak-colour curvature is still
suppressed by1/(1+A²/4). Such colour error is not repaired by this mechanism.
A genuine weak rank-two coloured crossing instead receives stronger restoring
force and may be erased. The saved fine-error decomposition establishes neither
which situation dominates nor a CFA-null cause. Additional local minima and
spurious rank-one detail remain risks of the redescending family.

Pure seams: `edge_matrix_loss(dx,dy)` returns an unreduced tensor for matching
leading dimensions and final RGB axis3; `image_matrix_cauchy_dn(image,gain,read_variance)`,
`matrix_image_prior(state,config)` and `selected_prior(state,config)` return
scalar means. Module.model exposes the frozen forward. Independent commission
uses direct f64 Gram/eigenvalue arithmetic, oblique rank-one/independent-rank-two
curvature, same-direction counterexample, RGB rotation, actual AD/finite
differences and rectangular global quadratic/boundary tests.

The remaining objective is unchanged: alpha TV .02, binary .002, normalized
sheet L2 .0001, likelihood, CFA/censor conventions, optics and supported domain.
Flat/layered start from the same screen160 sheets and fixed visibility-1 alpha;
hash/config guards require identity with the retained baseline. Only near/far
radiance parameters are optimized. No alpha update or new pupil is combined.

Same one-call L-BFGS: lr1,1000iterations,1400 nominal evaluations, history10,
gradient1e-6, change1e-11, strong-Wolfe and hard1800 actual evaluations including
initial/final monitors. Stream training-only frames, retain exact gradient
storage repair and unchanged state/export/status handling. No restart, sweep
or truth-selected stopping. Driver is a narrow copy of frozen Cauchy plumbing;
frozen helper modules are reused without monkeypatching them.

Primary quality reference is visibility-1 original Huber; Cauchy is descriptive.
All strict flat/RGB/chroma/component/held-prediction guards remain unchanged.
A two-case pass licenses only separately fixed new-seed/weak-ramp/crossing
stress tests, never photographs or automatic visibility/calibration claims.
Known-alpha, discrete64-ray optics and nonstationary-result limits remain.

CLI: `python matrix-cauchy-prior.py --source screen-1/output --alpha-root visibility-1/alpha
--out <directory>`. Same case/fixed-alpha outputs and receipt schema; prior_kind
is `matrix-cauchy-original-scale-sheets`. Root executes and independently scores.
