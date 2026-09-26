# Prospective independent choice review

2026-09-26, before fixture export, optimization or candidate scoring. One fixed
training attempt of at most five GPU minutes; no architecture, seed, checkpoint,
threshold or validation-family search follows a failed result.

The small shared per-band scorer sees per-source energy/floor, floor magnitude,
mean green and two colour differences, plus source-set means in a 3x3 band-grid
neighbourhood. This can express a brightness/context-dependent reliability rule
that the fixed energy ratio cannot. It does not observe signed coefficient phase,
physical depth or complete occlusion support, so it cannot be assumed to identify
every blur/geometry ambiguity. Independent per-band weights permit near-fine and
far-coarse sources to coexist. Original linear CFA coefficients, current terminal
mean, hull and MHC remain the only reconstructed values; this does not by itself
prevent selection-induced false detail, noise or colour errors.

The proposed family split is meaningful: twelve training stacks at ISO100/400 use flat fields,
single-depth sinusoids, straight occlusions with checker/sinusoidal texture, and
Gaussian blobs under a disk-pupil renderer. Held-out scenes contain curved bright
occlusion with stipple, near-fine/far-coarse geometry and distinct motifs, genuine
unclipped/clipped point glints, weak-colour glyphs/dots, and flat controls. Held
ellipse/annular pupil forms must be absent from training, not merely different
seeds or orientations. The frozen held set is seven cases in six families at
ISO100 only, with N=5 and N=9 flats plus N=9 curved occlusion. Changed N exercises
flat/set and one occlusion case, not a 299/488-frame population. There is no held-out ISO400 validation
or high-ISO safety claim. Noise-model reuse tests an operator, not calibration
or actual lens PSFs.

Freeze two positive families before any export: curved bright occlusion and
near-fine/far-coarse at ISO100, at their independently fixed windows. Require at least 5%
lower RGB truth RMSE than the better of canonical and uniform in both nominated
positive witnesses. Uniform and zero-head/no-learning are one comparator, not
two independent arms. A gain supplied entirely by uniform averaging cannot
nominate the learner. Require all fixed RGB/green/chroma error windows, including
flats, to remain within 1.10 of both comparators. Protected component recovery
must retain 90% of each eligible reference, with recovery bounded to [0,1].
Recovery above one is not extra detail; absolute errors remain necessary.

Before training, export the references and commission final admission with
exact truth and known added-noise, erased-detail and wrong-depth destroyers.
Exact truth must be able to pass. Each positive must have reference error above
twice its corresponding flat error and a live baseline/uniform difference;
record absolute errors and signed spill where applicable. Require separately
qualified near-fine, far-coarse, true-bright/glint and weak-colour protection
witnesses. Reference recovery below .5 is unqualified local retention, not a
permanent conjunction failure even for perfect output, nor candidate harm.
Report every remaining unqualified region explicitly. If the fixed witnesses
are not viable, stop before training rather than select replacements afterward.
Truth passing the scorer does not prove exact truth is expressible through
positive source weights plus a held terminal mean/hull; state that limitation.

Use only training IDs in optimization and training-only reconstruction loss.
Held-out arrays must not choose steps, checkpoint, hyperparameters or stopping.
Replay the frozen learned parameters through the actual native consumer for the
decision; differentiable training loss alone is not an admission result. Check
source permutation and changed N without ordinal/index input or truth features.

A full-image route would require a source pass for set-mean context, followed
by bounded passes for logits/max and normalized coefficient accumulation, or an
independently commissioned stable online equivalent. Do not retain all source
feature/plane images or claim one-pass speed. This generated screen alone
supports neither a full-stack resource estimate nor photographic/SOTA status.
