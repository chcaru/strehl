# Original-CFA level-balanced photographic discriminator

Root allocation 2026-10-27. The user's active goal prioritizes genuine insect detail and color, with complete photographs decisive. This is one changed objective, not an accepted quality improvement or a production release.

## Evidence and changed question

The retained full299 streamed inverse was catastrophically rejected: colored blocks replaced weevil hairs, scales and contours. Its all299 band budget reproduces the saved objective exactly and verifies full-size Haar/measurement controls. AC levels5/6 contain98.972875% of total q, while truncated boundary neighborhoods contain only2.4433% of total q but99.99851% of actual constant-column energy. These are distinct defects; neither more CG nor boundary repair alone addresses both.

Prior work: [measured budget](../direct-cfa-streamed-normal/band-budget-results.md), [independent budget review](../direct-cfa-streamed-normal/band-budget-results-review.md), [whole-image rejection](../direct-cfa-streamed-normal/photographic-review.md), retained generated flat/noise failure, and [earlier color diagnostic design](../../layered-raw-inverse/colour-error-diagnostic-design.md). Root ran research.py search and ORCH prior_art.py for `Haar scale normalization boundary constant` (no matches), then `Haar` with research `--any` (the earlier color design; no indexed reports). These limited searches do not establish absence; the present unindexed experiment reports supply the reopening evidence.

Question: does correcting cross-level precision mass and unequal-support constant leakage restore a useful whole photograph early, with the same original-CFA sensor operator, noise, runtime geometry, sources and fixed development? This is not a claim that the eventual least-squares optimum is physically sharp.

## Single estimator and invariants

Use support-count-aware orthonormal Haar pairs: low=(sqrt(nL)*l+sqrt(nR)*r)/sqrt(nL+nR), high=(sqrt(nR)*l-sqrt(nL)*r)/sqrt(nL+nR). Propagate inverse, squared weights for marginal variances, and Boolean support consistently. Equal support reproduces the original pair; unequal carries must retain constants in LL. Actual A(ones), rather than an idealized LL-only column, still defines nuisance deflation.

For each AC level across all admitted original sources, phases and orientations, Qk=sum(a/max(V,1)), Rk=sum(1/max(V,1)); use q'=q*(Rk/Qk). LL stays1/max(V,1). Preserve within-level source, position, color and orientation preference; do not normalize each frame or channel separately. Empty support is omitted; positive R with nonpositive/nonfinite Q refuses. Freeze these statistics before solving. Statistics and reconstruction arithmetic remain f32, with no learned/private noise estimate, aligned volume, source RGB volume, fitted scale, preconditioner or image prior.

The objective changes. Within-level glints can still dominate; on a flat with identical admission floors, normalization restores1/V and can expose noise/aliasing. Do not call it calibrated likelihood, denoising or guaranteed detail recovery. Two coupled changes are deliberately selected from distinct measured defects; this first test cannot apportion a possible gain between them.

## Owned source and controls

Cfa-residual owns new `bands-gpu.py`, `normal-operator.py`, `solver.py`, `photograph.py` and implementation notes in this directory. Reuse hash-bound existing measurement, paired forward, final-cell delivery and native developer; never edit executed sources. Integration-review owns independent `controls.py`, control notes and source/result audit here. Photo-review owns supporting state documentation and later complete-image review. Root owns this brief, ledger, wrappers and every numerical/build/RAW job.

Controls first: flat/noise and independent-color/mixed-depth cases through the changed producer; full-size constant annihilation, orthonormal roundtrip/dot and variance propagation with an independently written CPU reference; shared-level normalization and preserved within-level ratios including unsupported support. A legacy unequal-support carry is the causal boundary foil; wrong inverse/level scaling must fail the relevant mechanical checks. Frozen no-focus is the focus placebo. These controls validate implementation and expose risks, never photographic truth. Do not relax old flat/noise failures or run a broad synthetic campaign. Root alone may run a bounded300s control job after source review.

## Complete actual photograph

Only after controls and independent source review: one full299 pilot, zero correction, maximum4 CG iterations, complete checkpoints at1,2,4. Restore true constants and use the commissioned final reference-cell integration plus fixed native development at every checkpoint. Save signed f32 camera DN, full6896x4596 RGB16 master, full JPEG and the ten already-fixed384px witnesses. No retone, sharpening, denoise, remosaic or second demosaic. Intermediate recursive residuals are not true objective or convergence evidence; final true full/projected checks retain the unchanged1e-5 bar and an honest refusal. A finite image is still delivered on iteration-cap refusal.

Use all299 original u16 caches and unchanged map/geometry/source order. Four CPU workers, one Torch interop, RTX5090, f32, no TF32/autocast. Root wrapper bounds:1500s wall,6000s CPU,16GiB host Job commitment,8GiB Torch allocated/reserved,32MiB log, fresh workspace output and at least12GiB free space. Record host load and complete bindings. No other root-scheduled GPU/numerical lane overlaps. Retain any failed artifact and process status. Never terminate an unowned process.

Inspect complete checkpoints against previous native, rejected inverse and Helicon B4/B8, followed by all ten native witnesses with the same display transform and established gauge caveats. Stop after this pilot; no automatic64-step extension. A recognizable image or improved residual is insufficient for promotion. Continue only if actual hair/scale/color/contour fidelity warrants it; otherwise choose a materially different direction. The broad SOTA goal remains active regardless of this experiment.
