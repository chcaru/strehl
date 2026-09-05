# M135 burned-slide physical commissioning results

**DEVELOPMENT — NEVER A SCORE.**

This is an authorized author-executed commissioning run on a deliberately burned development session. It is not an independent verification, does not populate M1, does not bind M138, and makes no score or SOTA claim.

## Verdicts

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

| Question | Evidence class | Frozen outcome | Ruling |
|---|---|---|---|
| Inventory | MEASURED + VERIFIED | `INVENTORY_MATCH` | All 657 regular files are the 657 inventoried/ExifTool-populated ARWs. |
| Coarse encoder range | MEASURED + VERIFIED | `COARSE_ENCODER_RANGE_EQUAL` | Both tilted stacks have complete `FocusPosition2` minima 57 and maxima 59. |
| Image-derived range | COULD NOT DETERMINE | `IMAGE_RANGE_UNDETERMINED` | Both frozen low-pass quadrilateral selectors refused; no range fit or node-density ratio exists. |
| Full `J_TR` identifiability | MEASURED + VERIFIED | `REFERENCE_ROLE_ABSENT` | `j_tr_computed=false`, `j_tr=null`; no ratio is identifiable. |
| Real optical intervention | COULD NOT DETERMINE | `REAL_OPTICAL_ARM_NOT_ESTABLISHED` | The preregistered Stage A/C predicate did not establish equivalent physical range. |
| Flat diagnostics | MEASURED + COULD NOT DETERMINE | `FLAT_DIAGNOSTIC_UNDETERMINED` | 1 s and 2.5 s are structured; 6 s was refused for clipping. |
| Physical binding | VERIFIED | `UNBOUND` | Missing reference/calibration roles and insufficient flat evidence leave the session unbound. |
| Session invariance | VERIFIED | `UNCHANGED` | Before/after `Get-ChildItem -Force` snapshots contain the same 657 records and 26,156,716,032 bytes. |

## Exact command outcomes

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

| Command stage | Exit | Duration (s) | Outcome |
|---|---:|---:|---|
| `build` | 0 | 2.964895 | `CROSSCHECK_BUILD_HASH_MATCH` |
| `pre-data-freeze-check` | 0 | 2.192050 | `PASS` |
| `stage-a-inventory` | 0 | 59.552812 | `INVENTORY_MATCH` |
| `stage-b-decode` | 0 | 795.452102 | `DECODE_CROSSCHECK_PASS` |
| `stage-c-range` | 0 | 20.311192 | `IMAGE_RANGE_UNDETERMINED` |
| `stage-d-roles` | 0 | 17.710770 | `REFERENCE_ROLE_ABSENT` |
| `stage-e-flat` | 0 | 175.452799 | `FLAT_DIAGNOSTIC_UNDETERMINED` |
| `summary` | 0 | 1138.428533 | `DEVELOPMENT_COMPLETE` |

Every frozen command captured `$LASTEXITCODE` immediately after the process and before displaying or filtering output. No frozen command exited 1 or 2. Scientific negatives at exit 0 were retained and the run continued as preregistered.

## Inventory and metadata

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

### Population equality

| Population | Frames | Bytes / evidence |
|---|---:|---|
| Filesystem, `Get-ChildItem -Force`, regular non-reparse files | 657 | 26156716032 bytes; listing SHA-256 `260f05d3342141f7e8698efe684151dfb3a904097c4d678b710912c1c1d5bfee` |
| Stage A inventory | 657 | 26156716032 bytes |
| ExifTool numeric population | 657 | All four per-stack commands exited 0. |
| ExifTool formatted population | 657 | All four per-stack commands exited 0. |

The path populations are exactly equal, `unexpected_arw=[]`, and Stage A's own before/after source snapshot is unchanged.

### Per-stack frames and timestamps

| Stack | Frames | Bytes | First timestamp | Last timestamp |
|---|---:|---:|---|---|
| `tilted-sw4-cpl` | 182 | 7246405632 | `2026:09:02 20:46:50.071-07:00` | `2026:09:02 20:51:13.767-07:00` |
| `tilted-sw10-cpl` | 92 | 3662270464 | `2026:09:02 20:52:52.160-07:00` | `2026:09:02 20:55:04.626-07:00` |
| `flat-sw4-cpl` | 186 | 7561744384 | `2026:09:02 20:13:04.463-07:00` | `2026:09:02 20:30:05.390-07:00` |
| `very-tilted-all-axis-sw10-cpl` | 197 | 7686295552 | `2026:09:02 20:57:12.415-07:00` | `2026:09:02 21:01:58.443-07:00` |

### Focus tags and complete `FocusPosition2` histograms

| Stack | `FocusPosition2` histogram; missing | `FocusDistance2` histogram; missing | Other requested focus tags |
|---|---|---|---|
| `tilted-sw4-cpl` | `57` × 76, `58` × 80, `59` × 26; 0 missing | `0.273841307296975` × 76, `0.277110541270397` × 80, `0.280524516597463` × 26; 0 missing | `FocusPosition` 182 missing; `FocusPosition3` 182 missing; `FocusDistance` 182 missing |
| `tilted-sw10-cpl` | `57` × 38, `58` × 40, `59` × 14; 0 missing | `0.273841307296975` × 38, `0.277110541270397` × 40, `0.280524516597463` × 14; 0 missing | `FocusPosition` 92 missing; `FocusPosition3` 92 missing; `FocusDistance` 92 missing |
| `flat-sw4-cpl` | `57` × 186; 0 missing | `0.273841307296975` × 186; 0 missing | `FocusPosition` 186 missing; `FocusPosition3` 186 missing; `FocusDistance` 186 missing |
| `very-tilted-all-axis-sw10-cpl` | `56` × 10, `57` × 40, `58` × 40, `59` × 41, `60` × 40, `61` × 26; 0 missing | `0.270710678118655` × 10, `0.273841307296975` × 40, `0.277110541270397` × 40, `0.280524516597463` × 41, `0.284089641525371` × 40, `0.287812608018665` × 26; 0 missing | `FocusPosition` 197 missing; `FocusPosition3` 197 missing; `FocusDistance` 197 missing |

### Capture settings

| Stack | Exposure histogram | ISO | f-number | Reported focal length |
|---|---|---|---|---|
| `tilted-sw4-cpl` | `1` × 182 s | `100` × 182 | `5.6` × 182 | `200` × 182 mm |
| `tilted-sw10-cpl` | `1` × 92 s | `100` × 92 | `5.6` × 92 | `200` × 92 mm |
| `flat-sw4-cpl` | `2.5` × 61, `1` × 60, `6` × 65 s | `100` × 186 | `5.6` × 186 | `200` × 186 mm |
| `very-tilted-all-axis-sw10-cpl` | `1` × 197 s | `100` × 197 | `5.6` × 197 | `200` × 197 mm |

All 657 frames report Sony `ILCE-7CM2`, lens `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` (`LensType3=33094`), image stabilization `1` / `On`, raw and camera orientation `1` / `Horizontal (normal)`, release mode `5` / `Exposure Bracketing`, raw buffer dimensions 7168×5120, and EXIF dimensions 7008×4672.

## Decoder crosscheck

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

Stage B is `DECODE_CROSSCHECK_PASS` on 657 of 657 frames. Every RAW SHA-256 matches Stage A; every rawler process returned 0; and every canonical 4688×7028 overlap matched rawpy bit for bit. Rawler's full active area is 4688×7032 inside a 5120×7168 buffer; the four trailing active columns are recorded and excluded from statistics. The frozen executable is 6837248 bytes with SHA-256 `5418b561bc6b091dd5cb290fbb77d22d2d6f03c2a4a28b42b359963108770001`.

## Coarse encoder range

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

`tilted-sw4-cpl`: `57×76, 58×80, 59×26`, zero missing. `tilted-sw10-cpl`: `57×38, 58×40, 59×14`, zero missing. Both minima are 57 and both maxima are 59, so the frozen coarse predicate is `COARSE_ENCODER_RANGE_EQUAL`. This is equality of the reported coarse encoder range only, not image-derived physical equivalence.

## Image-derived range

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

The frozen result is `IMAGE_RANGE_UNDETERMINED`. For each tilted stack the recorded reason is `no low-pass quadrilateral satisfied the frozen selector`. The artifact preserves the fixed 8×8 lattice's 64 normalized coordinates, registration stop 0.06 cyc/native px, focus band [0.06, 0.20] cyc/native px, and the bars: at least 48 joint eligible sites, |a|≤0.02, |b−1|≤0.04, q95(|residual|)≤0.03.

No site curve was emitted because the low-pass quadrilateral prerequisite failed for both stacks. The exact frozen outputs are: eligible count 0, `u4=null`, `u10=null`, `robust_fit=null`, and `node_density=null`. No site, crop, threshold, registration, decoder, or frame subset was changed or imputed.

## Full `J_TR` identifiability

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

Stage D returned `REFERENCE_ROLE_ABSENT` from the unmodified ledger SHA-256 `b03e3e67464800a32f5c336ace0e88b91e9f3b4a92a5e3b6126c3202b9b55cd8`. Missing roles are: `R1`, `R2`, `sw4_Y1`, `sw4_Y2`, `sw10_Y1`, `sw10_Y2`, `flat_R1`, `flat_R2`, `sw4_flat_Y1`, `sw4_flat_Y2`, `sw10_flat_Y1`, `sw10_flat_Y2`.

`j_tr_computed=false`, `j_tr=null`, `sampling_ratio=null`, and `score_callback_called=false`. Therefore no `J_TR(sw4)/J_TR(sw10)` ratio was computed or inferred. Treating sw4 as truth would use the claimed improvement arm as its own reference and is circular.

## Real optical intervention

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

The summary reports `REAL_OPTICAL_ARM_NOT_ESTABLISHED`. Distinct sw4/sw10 files and equal coarse encoder endpoints were measured, but the frozen Stage C physical-range predicate was undetermined. Consequently `REAL_OPTICAL_ARM_PRESENT` is not reported, and no improvement direction is claimed without identifiable `J_TR`.

## Flat diagnostics

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

| Exposure | Frames / splits | Observed statistic | Phase-scramble q99 | Null / p-value | Status |
|---:|---|---:|---:|---|---|
| 1.0 s | 60 / [15, 15, 15, 15] | 0.00012439594192773353 | 6.567461939761921e-05 | `independent-site-carrier-phase-scramble`, 255 draws, `p_upper=0.00390625` | `STRUCTURED_FLAT` |
| 2.5 s | 61 / [16, 15, 15, 15] | 0.00013712247035281376 | 7.046743126431681e-05 | `independent-site-carrier-phase-scramble`, 255 draws, `p_upper=0.00390625` | `STRUCTURED_FLAT` |
| 6.0 s | 65 | not computed | not computed | not computed; clipping refusal | `FLAT_DIAGNOSTIC_UNDETERMINED` |

- 1.0 s frequency power (cyc/native px: mean power): 0.1: 0.0004222455344353578, 0.15: 6.495762773434249e-05, 0.2: 2.8412183067536592e-05, 0.25: 5.051465621235492e-05.
- 2.5 s frequency power (cyc/native px: mean power): 0.1: 0.0004287681619981531, 0.15: 5.536442040398428e-05, 0.2: 2.019236585756765e-05, 0.25: 3.878025256769838e-05.
- 6.0 s: `exposure 6: clipping refusal in 65 frames`; the observed statistic, q99, and p-value are COULD NOT DETERMINE.

The aggregate frozen state is `FLAT_DIAGNOSTIC_UNDETERMINED`. The existing M135 core probe was `NOT_EVALUATED_REFERENCE_ROLE_ABSENT` and was not invoked because the four modulo splits are not independent captures. A quiet flat would be necessary but insufficient; these results cannot bind M138.

## Physical binding

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

The terminal physical binding is `UNBOUND`. The reference/calibration role gate is absent, the 6 s flat group is undetermined, and the quiet-flat condition is explicitly necessary but not sufficient.

## Session and source invariance

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

Before Stage A and after summary, the authorized session contained 657 regular files totaling 26156716032 bytes. Both snapshots have listing SHA-256 `260f05d3342141f7e8698efe684151dfb3a904097c4d678b710912c1c1d5bfee` and all 657 path/size/creation-time/write-time/attribute records compare equal. There were zero reparse files. Stage A independently recorded matching before/after stat digest `1c86099ab7ab8902032d9ff2b6bc179caab5ae11881ccefabad350460f3ab652`, and Stage B rebound every RAW SHA-256 before decoding.

The frozen tracked source closure contains 78 files with aggregate SHA-256 `e59643fcb11f35896cb19457bdc47f294c64d2cae7a227fecbc932ca22009f19` before and after. The shared repository HEAD moved from `2b14eb0399bbe682b4b83910f941ca5c63cf2a0d` to `e93f0bde695961d53cbd66587a060a41552b4a63` during the long run, but the path-scoped frozen source bytes remained identical to the independently authorized commit `0511594d3e31a3f2ef4f204ce1ddf88ac6f147da` and locally unchanged.

A post-processing PowerShell string reconstruction returned a false negative and exit 2 despite identical stored listing digests. Its artifact and output are preserved. A structural comparison of the two already captured JSON snapshots, without a new D:\ enumeration, found every record equal. No scientific stage was rerun or changed.

## Provenance and frozen recomputation

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

Pre-data freeze check: `PASS`; freeze-manifest SHA-256 `aeb758622066bf00ff9e4fedd529ba6c5b0e02be6574b29988481343e3877950`. Crosscheck executable: 5418b561bc6b091dd5cb290fbb77d22d2d6f03c2a4a28b42b359963108770001. Stage artifact SHA-256 values are recorded in `run-manifest.json` and match the terminal `summary.json` links.

The summary recomputed inventory, every-frame dual decode, image range, and flat diagnostics from bound inputs; all four recomputation flags and all eight artifact-link checks are true.

## Unanswered questions

**Label for every result in this section: DEVELOPMENT — NEVER A SCORE.**

1. Whether sw4 and sw10 cover equivalent physical focus range remains undetermined because neither frozen low-pass quadrilateral selector found a valid region.
2. The full `J_TR` contrast, its arm ratio, and any improvement direction remain unidentified until independent same-site R1/R2, Y1/Y2, calibration, and matched-flat evidence exists.
3. The 6 s flat-group repeatability statistic remains undetermined because all 65 frames triggered the frozen clipping refusal.
4. No result here licenses M138 binding, a score, a comparator qualification, or a SOTA statement.
