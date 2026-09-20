# Free visibility: fixed independent utility screen

Prospective. Root runs; controls author and model author do not execute their
own tests. Four cases, two priors, one final state per fit, no intermediate
selection and no solver/threshold search. Previous pinhole failures stay failed.

Both arms restore the exact original screen-1 160-step two-layer checkpoint for
each of flat, layered, far-only and angular-mismatch. All three original
parameters near, far and alpha_logit must be present, trainable and restored
bit-exactly; all four initial exported fields must match both each other and
that checkpoint. No known alpha, truth sheets, source labels or held-out pixels
may enter fitting. Original seven training indices and two held-out indices
remain. The original forward, CFA likelihood, saturation rule, noise and all
non-image prior terms are unchanged. Arms are original Huber and the already
frozen matrix-Cauchy prior. Both have identical LBFGS1000/1400/history10,
strong-Wolfe, gradient1e-6/change1e-11 and hard1800 evaluation caps.

## Commission and receipt checks

Reuse the frozen in-focus instrument commission including half-colour loss,
extra fixed PSF, full context, composed-image filtering and wrong-colour
destroyers. It must still pass before any fit. No redefinition of its0.98
ideal-reference detail bar. A small nonconstant trainable state additionally
checks actual wrapper restoration and requires_grad, exact dispatch to the old
Huber/matrix objectives, and the nonzero alpha_logit gradient of unchanged
alpha-TV plus binary terms against an independently enumerated derivative.
A detached/fixed alpha or a changed remainder must fail. This is arithmetic
commissioning, not evidence of successful visibility inference.

Receipts must bind original source/model/prior, checkpoint, actual training
reads, initial parameter/field equality, all three gradient names and accepted
final state. Every completed closure preserves logical gradient values through
layout conversion. Final state and held predictions are hash bound. Source and
output files remain unchanged through scoring. Missing or refused output is an
incomplete arm, never silently converted to an image-quality verdict.

## Prospective delivered image and guards

Primary target is B(P): the same supplied f32 sigma0.7 radius3 PSF applied once
to the composed full96x96 pinhole, before extracting the unchanged16:80 whole
support and static core/ridge/crossing boxes. Verify actual exported images
against independent full-context filtering. No oracle alpha or mask-accuracy
metric can admit an arm. The old pinhole target is scored separately with its
old metrics and cannot be retrospectively promoted.

For flat and layered, retain every frozen in-focus-2 guard versus filtered
fixed-alpha visibility1, unchanged observed mean and retained training-only
donor, and filtered historical far-only inverse. Donor images are never
reselected or filtered again; their component projections use B(template) and
separately B(absent), not old pinhole recovery values. Both RGB and chroma are
protected. Add the same paired guard against this run's same-budget free-alpha
Huber: flat whole RGB/chroma <=1.05; layered core/ridge RGB/chroma <=1.02;
glint/core and glint-free ridge-detail per-colour capped recovery >=0.98 of
the free-Huber reference, which must remain live and >=0.5. Retain the old
absolute component floor0.8 and donor comparison. No failed region/colour is
averaged away. Fixed alpha-reference guards may not be weakened after results.

Far-only is an explicit image-damage null. Its historical comparator is the
actual single-depth `screen-1/output/far-only/far-only/reconstruction.npz`, not
the old top-level case-quality record or a two-layer output. Whole/core/ridge
RGB AND chroma must be <=1.05 of that once-filtered single-depth inverse and
<=1.02 of same-budget free Huber. Its glint is live and gets the same0.8 absolute,
retained-donor and0.98 free-Huber component guards. The ridge template is
mathematically zero here, so no nonexistent ridge recovery is claimed: fixed
ridge-region RGB/chroma checks penalize invented foreground colour/detail.
No threshold on inferred alpha is substituted for delivered-image protection.

Angular mismatch retains the fixed truth, static boxes and component records,
but is not required to reconstruct successfully. Its held-out failure is an
adequacy refusal, not an implemented automatic gate. It can be called selective
only if all three matched in-family cases have passed; otherwise it is merely
another failed fit. Do not require a failure by changing its stimulus or bars.

Original raw held-out prediction bars remain: whole uncensored RMS<=1.5sigma,
each present CFA/bright/dim stratum<=1.75, censor shortfall<=2. Predictions are
made only after fitting and never select an iteration. Static truth variance
is used only in independent scoring. Nonstationarity is reported separately,
not hidden by image quality. Matrix in-family qualification requires all fixed
target and held-out checks for flat, layered and far-only. No camera/RAW/photo
admission follows; the supplied-optics1024-pupil failure remains unresolved.

Noise-only flat is evaluated first. RGB error can improve through smoothing;
live component destroyers address that failure direction. Components can
credit correlated error; strict RGB/chroma and held-out bars remain alongside
them. Observed mean and donor are image baselines, not calibrated optical
truth. The far-only arm is restricted to its supplied far depth, not the best
possible one-layer method.

Root CLI:

```text
python free-visibility-controls.py commission --out <run/commission>
python free-visibility.py --source screen-1/output --out <run/output>
python free-visibility-controls.py score --source screen-1/output --candidate <run/output> --out <run/scored>
```

Commission requires `passed:true` before fitting. No numerical execution by
the independent controls author.
