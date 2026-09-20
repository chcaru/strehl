# One fixed Cauchy sheet prior at the original DN scale

Prospective; no author execution. Only the original sheet image loss changes.
For each horizontal/vertical native RGB difference d in black-subtracted DN,
set `b²=2*(gain*2048+read_variance+1/12)`,
`s²=(sum_RGB(d²)+1e-12)/b²`, and `rho=2*log1p(s²/4)`.
Mean rho over pixels, directions, then sheets with coefficient1. The reference
signal2048DN is the existing chosen regularity scale, not a camera/scene
measurement. Gain/read variance remain supplied once; no learned noise or
brightness-dependent denominator, coefficient fit or parameter sweep.

The loss has the original quadratic curvature at zero and characteristic
scale2; it is not equal to Huber at finite small gradients. Its derivative
`s/(1+s²/4)` redescends at strong edges. Therefore matching curvature does not
guarantee equal flat-noise suppression, and weaker penalties can preserve
spurious edges or create additional local minima. A common DN brightness
offset leaves this image term unchanged, unlike the rejected variance-
stabilized prior; the existing normalized sheet L2 still changes with offset.

Keep alpha TV .02, binary .002, normalized sheet L2 .0001 and all their means
unchanged. Same likelihood, original-CFA/censor conventions, noise, optics,
supported interior and training-only facade. Fixed alpha remains an independently
exported buffer. Flat/layered use identical original screen160 near/far
parameters and visibility-1 alpha/config, checked against retained reference
receipts. No free-alpha update or new optics is combined with this comparison.

Reuse frozen model, FixedVisibility, TrainingOnly and export/hash helpers.
The per-arm solver/export path is a narrow copy of shot-noise-prior.py because
the frozen driver has no prior injection seam; no monkeypatch or previous-file
edit is used. Solver unchanged: one L-BFGS, lr1,1000iterations,1400 nominal
evaluations, history10, gradient1e-6, change1e-11, strong-Wolfe; actual cap1800
includes initial/final monitors. Same contiguous-gradient identity check,
streamed source backprop, progress100, refusal/returned-state handling and
raw-parameter stationarity limits. No restart or truth-dependent state choice.

Pure commissioning APIs are `image_cauchy_dn(image,gain,read_variance)`,
`cauchy_image_prior(state,config)` and `selected_prior(state,config)`; module.model
exposes the frozen operator. Independent controls should distinguish curvature
agreement from finite-amplitude equality, check the actual derivative and strong-
edge redescending behavior, constant/common-offset behavior, and unchanged other
penalties. Truth/flat/held-prediction scoring remains independent. Baseline is
retained visibility-1 with original Huber; shot-prior-1 is descriptive only.

A pass on these two scenes commissions only independently frozen weak-ramp and
new-noise-seed stress tests. It does not admit photographs, calibrate the
camera/pupil, establish automatic visibility, or waive the failed64/1024-ray
resolution check. Nonstationary numerical results retain that limitation.

CLI: `python cauchy-prior.py --source screen-1/output --alpha-root visibility-1/alpha
--out <directory>`. Same `<case>/fixed-alpha` initial/final arrays, state,
held-index2/6 predictions and receipt schema as visibility-oracle; prior_kind
is `cauchy-original-scale-sheets`. Two fits only. Root executes and binds all
inputs; fitting reads no held-out values and no original camera RAW.
