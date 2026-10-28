# Independent audit of controls 1

**VERIFIED:** the root-run controls completed mechanically, and every generated quality arm failed its unchanged quality gate. This permits the allocated four-step complete-photograph discriminator only as a bounded observation. It does not justify a quality claim, a production change, or automatic extension to a longer solve.

The actual command, from the saved process and invocation records, was:

```powershell
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -B -X faulthandler C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-27\direct-cfa-level-balanced\controls.py --out C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-27\direct-cfa-level-balanced-controls-1\output
```

The owned job exited 0 in 57.734 seconds, with 56.375 CPU seconds, peak host job commitment 5,761,998,848 bytes, and zero remaining or terminated processes and cleanup errors. Torch peak allocated/reserved memory was 1,067,520,512 / 1,245,708,288 bytes. Four CPU threads, one interop thread, f32, TF32 off, and autocast off were recorded. This is a bounded control cost, not a full-workflow speed comparison.

I freshly rehashed all 50 completion artifacts and all 44 input/dependency references: 94 references, 9,366,210 bytes, no mismatches. Before/after dependency lists are equal. Complete 128-square camera-DN outputs and previews, 144-square latent/correction fields, all failed scores, and actual product-baseline references are retained. No fit, RAW decode, or model execution was repeated for this audit.

## Mechanical evidence

- Full 4688-by-7032 count-aware Haar: all 88 bands and independent inverse agree exactly with the independent NumPy control. The unit-constant maximum AC is 0.0000026974, below the prospective 0.0009765625 bound; the actual legacy carry produces approximately 16 and fails. Signed roundtrip normalized max/RMS errors are 7.63e-7 / 2.84e-7. Dot error is 6.17e-12; Parseval error 2.22e-7. Odd-origin 19-by-23 controls also pass. Variance and clipping/admission support checks pass; the wrong inverse fails strongly.
- Independent Q/R, shared multipliers, balanced masses, per-source metrics, and unchanged LL checks pass. Across the four arms the largest listed Q/R/multiplier/mass relative error is 6.67e-7 against the fixed 3e-5 bar. Wrong-level producing foils have relative errors 5.89 to 7.00 and fail the same bar. No-focus multipliers are exactly one at populated levels. Positive-R/zero-Q and nonfinite-Q cases refuse; actual all-clipped input is omitted.
- The actual solver callback visits 1, 2, and 4. Deliberately overwriting its cloned field and copied entry leaves returned field bytes, history, and status exact. This checks callback isolation with a deterministic algebra normal; it does not assert bit determinism for CUDA atomic sensor adjoints.
- All five retained quality-gate destroyers fail: added flat noise, erased far component, erased weak green, false green, and overcontrast.

## Retained negative quality evidence

| Complete arm | Material failure |
| --- | --- |
| Flat neutral, candidate | Chroma RMSE 12.541 DN exceeds 10.199; actual baseline is 8.817 DN. Lower RGB RMSE alone does not pass. |
| Independent color, candidate | Independent 8-DN green recovery is 0.00001937 versus baseline 0.4926. Lower overall RGB/chroma errors do not excuse erasing that structure. |
| Fine/far, candidate | Near/far recovery 0.3922 / 0.4493 is below 0.6444 / 0.4789; RGB/chroma RMSE 244.252 / 227.407 DN also fail 176.601 / 94.018. |
| Fine/far, no-focus placebo | Near/far recovery 0.0954 / 0.3374 and RGB/chroma RMSE 289.133 / 105.699 DN fail. The focus candidate changes behavior but does not meet the quality requirements. |

All four solves retain `refused-iteration-cap`, four iterations, and no convergence. True full-normal ratios are respectively 0.333984, 0.137347, 0.0719794, and 0.00267212, all above 1e-5; each objective is no greater than its constant initialization. Mechanical success means the specified changed calculation ran, not that the inverse succeeded. The actual product comparator uses its supported 96-square crop and a different effective band ladder; this is not a transform-only comparison.

**ARGUED decision:** the controls remove the specific constant-carry and implementation doubts underlying the diagnosed complete-photo failure. They do not establish recovery of fine or colored structures. The root's separate, preallocated complete 1/2/4-image observation is defensible for deciding whether the actual catastrophic scale/block failure responds at all, because it changes the implicated objective and makes every intermediate photograph reviewable. The generated evidence provides no basis to expect satisfactory image quality or to extend work solely because the new photograph is less catastrophic. Whole images and original-scale witnesses must decide the next step.

## Audit bindings

- Completion SHA-256: `2c9a7c2eaae914786581fc92188ba4f66ea18e2045a0bf99349abbe5dcd27e91`.
- Scientific receipt SHA-256: `5a8e654bf5813e888bba1d348da796d46fe7afde26096ab83c6e779f7820e3b3`.
- Process receipt SHA-256: `baa786fe620cf44f68273ad7da50c61c4f07d0a656d5efcffe8b8b20b6f1a018`.
- Source identities and boundaries are recorded in [the independent source review](independent-source-review.md); prospective bars remain in the unchanged [control notes](control-notes.md).
