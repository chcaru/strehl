# Independent scoring of the fixed convergence diagnostic

Root executes this scoring script after the separate optimizer completes. The
scorer never fits, changes a latent state, chooses an iteration, or uses truth
to select a checkpoint. Only the prescribed final flat/two-layer,
far-only/far-only and layered/two-layer outputs are read. The original160-step
screen remains failed, and its data, model, controls and checkpoints stay frozen.

Reuse the original independent-controls.py by file import: same pinhole truth,
seven training indices, two heldout observations, sensor variance,16-pixel
valid margin, digital censor semantics, bright/dim and four-CFA strata, full
RGB/component definitions and glint-free ridge-detail bounds[39,31,63,41].
Expected heldout CFA is recomputed only from the frozen independent truth
generator; model predictions are final exported values, produced after fitting.
No withheld observation influences the continuation or this choice of output.

Flat/two-layer retains the strict original1.05 mean RGB/chroma bars. Layered/
two-layer retains every original truth/component and prediction bar against
the original fixed mean, oracle and far-only outputs. A reduced global heldout
residual never overrides increased flat noise, the bright stratum, or ridge
loss. Every failed bar is retained separately.

The continued far-only/far-only arm diagnoses the correct single-plane solver.
Its final truth RGB/chroma is compared with the frozen original far-only output
using the existing1.05 nonregression factor, and the unchanged heldout prediction
bars apply. This is not the old two-layer-versus-far-only quality comparison;
it is never compared with itself or silently substituted for a layered reference.

Stationarity comes from the optimizer's fixed final gradient/status, reported
separately from quality. A low objective or small gradient does not imply useful
image reconstruction. Only final outputs are scored, even if an earlier iterate
would have looked better. Source input/model/control/checkpoint file hashes must
match old bindings and remain unchanged across scoring; continuation bindings
must match those same sources. New output hashes are retained as well.

The known64 versus resolved1024 physical-adequacy failure is carried forward.
This diagnostic cannot authorize real RAW processing, canonical consumer
promotion, camera calibration, or SOTA claims even if the fixed final truth
scores improve. It distinguishes insufficient optimization from a failed
unchanged objective on the existing small generated inputs.
