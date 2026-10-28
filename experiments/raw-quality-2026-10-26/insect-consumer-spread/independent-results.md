# Independent consumer-spread result review

2026-10-27. **VERIFIED receipt/source review only:** no new fit, original RAW read, pixel extraction or build by this reviewer. **Recommendation: close this fixed transfer measurement and proceed to a bounded native-RAW restoration/fusion photograph trial.** Do not retune its windows, thresholds, references or kernel. The observation rejects its particular image-transfer description; it does not establish absent blur, a capture ceiling or an optical correction.

## Execution and controls

Root's exact command, environment and source binding are in [invocation.json](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-job-1/invocation.json):

```powershell
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -I -B -X faulthandler C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-26\insect-consumer-spread\discriminate.py --out C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-26\insect-consumer-spread-1
```

Source SHA-256 `487b2987b2cf291661346c32736b63891d8def9ace912a40030441863b8f40de` matches the reviewed source. OMP/OpenBLAS/MKL/NumExpr threads were each1. [Process receipt](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-job-1/process.json) records exit0, 0.640s wall, 63,688,704 bytes peak job commitment, no termination or remaining child. These are operational costs, not a controlled speed benchmark. The result binds the complete299-source CA-off sensor output, frozen map/order, nomination, actual gathers and independent source143 decode receipt; its final input-hash checks passed.

**MEASURED controls:** generated noisy flats refused first; all six actual background comparisons refused source support. The actual background is the fixed center of a previously visually dark witness, not a certified uniform scene or a noise-calibration target. Identity recovered zero error. Analytic added sigma1 blur produced effective spreads1.146–1.154 native pixels with near-zero centroid.

Two control qualifications are decisive. A pure0.5px shift produced centroid0.515px **and apparent spread1.091px**, almost the blur control's spread. The sharpening placebo was admitted as a supported transfer with gain about1.235, offset about−64DN and zero spread. Thus the controls passed their specified tests, but neither spread alone nor `SUPPORTED_LOCAL_TRANSFER` certifies physical blur, fidelity or photographic improvement. All four eight-column-shift actual destroyers refused.

## Photographic observation

Each fit uses22 training and22 held sensels per phase on the same nominated bristle. G1/G2 are separate sampling phases, not independent statistical replicates. All actual references passed source-support and design-rank checks; their conditions2.71–9.81 are well below the preset refusal boundary. Nevertheless **all four final-image fits refused held transfer**:

| Fixed gathered reference | Phase | Train RMSE, DN | Held RMSE, DN | Held RMSE/source SD |
| --- | --- | --- | --- | --- |
| 143 | G1 | 45.10 | 64.52 | 1.357 |
| 143 | G2 | 44.60 | 64.48 | 1.376 |
| 149 | G1 | 10.82 | 29.15 | 0.635 |
| 149 | G2 | 11.96 | 24.81 | 0.553 |

The permitted final column was at most0.10; these are not marginal failures of the unpropagated noise reference. All four best candidates use only the center tap. Their zero centroid/spread values are parameters of **failed fits**, not measured zero motion or blur. Source143 was compared after its actual production gather into reference149 coordinates; its original samples were not falsely treated as already registered. Source149 remains partly focused and is not elected as sharp truth merely because its residual is lower.

The source149 original/gather green null is exact before clamping, and its fitted null has zero train/held error in both phases. That excludes this source's first green gather as the cause of its observed source-to-final difference. It does not exclude other sources' gather behavior, placement, changing visibility/focus, or multiframe reconstruction. The final shape is incompatible with this frozen three-tap/gain/offset family on held support, not with every possible blur model.

## Next decision

**ARGUED:** this is enough to stop narrow transfer metrology. It gives no defensible PSF to invert, and enlarging the fit would risk explaining away the structure. A bounded general RAW restoration/fusion trial is justified by the unresolved complete photographs, not by a positive causal diagnosis here. Preserve the original CFA observations, injected noise model, streaming gathers and runtime geometry; compare complete weevil outputs and full-resolution masters, then representative transfer including bug2. Test genuine hair/scale/color preservation and ringing alongside apparent sharpness. No photograph improved in this lane.

Evidence: [controls](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-1/controls.json), [actual background](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-1/actual-flat-first.json), [full result](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-1/result.json). Independently rehashed result SHA-256: `b3779473d0eb484b4acd433bda3401ef040dd58eec9fccfcae93a42cedcc5660`.
