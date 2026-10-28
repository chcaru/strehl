# Fixed saved-alpha diagnostic — source prepared, execution held

2026-10-26. Allocation raw-quality-2026-10-26-visibility. This lane owns only this directory. The user has now prioritized generally applicable weevil/insect improvements; root instructed this preparation to finish and execution to remain held. No GPU work, forward evaluation, fit or image generation was executed here.

## Exact changed question

The rejected marigold-constrained-raw result contains a strong CFA-frequency coverage lattice. Its saved-field analysis attributes most returned high-frequency error to changed alpha multiplying the separation between relatively smooth radiance sheets. Test the report's single proposed counterfactual: one separable3×3 binomial average of final alpha, nearest extension at the outer latent boundary, then restore all15 foreground and39 background seeds. Leave both final f32 radiance sheets exactly unchanged. This is a diagnostic of the frozen model's use of that coverage mode, not a repair or an admitted photographic improvement.

The actual saved arrays are300×336; output is the full144×108 saved patch at delivered-native[3480,3324,144,108], reference244. Source NPZ headers were read without numerical computation and are recorded in preparation.json. Source/preparation metadata and32 immutable input files are pinned. All nine original-u16 saved patches are streamed through the existing physical-sensel inverse-colour-pull query; no original RAW is reopened. Frozen source split is train96/112/128/144/160 and held104/120/136/152. The existing same-ray pupil uses16384 points, saved near/far shifts, and common sigma0.7. Rebuilt table metadata must exactly match the retained tables before use.

## Source and command

diagnose.py has passed Python source compilation without importing or executing it. The exact prepared invocation, **NOT RUN**, is:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-26\structured-visibility\diagnose.py' --out 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-26\structured-visibility-1'
```

Root must explicitly release the hold before scheduling. If released later, use the established bounded-process wrapper with a120s wall/CPU bound and4GiB host commitment, one numerical CPU worker, and4GiB Torch allocator cap. Driver/NVRTC memory is outside that Torch cap and is reported as such. Existing implementation is imported from the original workspace, never modified. The script requires a fresh output directory and a CUDA device; there is no CPU fallback. It does not train, refit sheets, change optics, adjust parameters, or sweep.

## Controls and interpretation

Before the saved-field perturbation, the existing operator must pass a supported equal-colour flat null and the known500DN response to a constant coverage change between unequal constant sheets. A constant alpha field is unchanged by the3-tap filter. The exact global alpha/radiance gauge is then checked on the frozen fields for held104 and the pinhole composite, with0.02DN numerical tolerance. Gauge transformation `alpha'=1-0.5*(1-alpha), F'=F/0.5, N'=alpha*N/alpha'` preserves supported predictions and pinhole output, but changes hard background seeds: it is a forward-representation control, not a feasible constrained fit. The actual blur counterfactual keeps the sheets and seeds fixed and changes the returned image, so it is not that harmless gauge.

All four held sources must replay their previously saved final predictions within0.01DN on exactly the saved sensel coordinates/phases/values. This is an execution consistency check, not independent validation of the model. For each training/held phase report baseline/changed RMSE, bias and NLL, plus prediction-change RMS in DN and in the single existing noise model's sigma. Noise weights for the latter are frozen at original prediction; no new noise estimate is fitted. These statistics may reward model mismatch or erased real detail, so there is no score-based quality verdict or threshold selection.

The outputs include original and altered complete144×108 RGB16+ICC masters, PNGs, alpha maps, original-sensel prediction arrays, and384×384 research contexts with all exterior pixels unchanged. The original failed patch and Current must replay exactly under the retained renderer/developer before any display comparison. A384 context is not a full-stack reconstruction. High-pass changes are attribution only: real structure can also decrease. A large composite change alongside small held changes supports conditional weak observability; large held changes show that the frozen objective uses the mode to explain data or mismatch. Neither establishes physical alpha, general visibility identifiability, or a photographic repair. This does not test the source160 upper strands outside the saved patch.

## Prior evidence checked

Read actual marigold-constrained-raw/results.md, saved-field-analysis.py, run.py, model.py, pupil.py, saved run receipts and array headers, plus layered-raw-inverse/visibility-update-design.md and its imported model/pupil definitions. The latter warns that the exact gauge preserves the image and cannot alone explain its failure; conditional fixed-sheet sensitivity differs from sensitivity after allowed sheet refitting. Read the current occlusion-survey.md: membership-pyramid, fine-detail transfer and source-ownership failures prevent treating this as a new generic smoothing recipe.

Executed searches returned0: `python scripts/research.py search structured visibility alpha --limit 10`; `python experiments/ORCH-drift-check/prior_art.py visibility alpha`. Relevant older hits include M87-occlusion (its rim score rewarded destroyed hair), M79-edof-verification/survey (oracle assumptions), M92-null-averaging and M75-rb-asymmetry. These are navigation/context, not replications. No forbidden implementation was consulted.

## Stop

Preparation is complete. Execution remains held. Do not extend this marigold lane or use it to delay the user's weevil/insect priority. No further architectural recommendation is made before new evidence or root allocation.
