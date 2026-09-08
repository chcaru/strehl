# Independent factor-eight-1 saved-outcome audit

2026-09-07. **VERIFIED saved execution and failed known-rotation control.** The audit passes; the subject remains **REFUSED**, not complete. Nine control groups passed, then `native-rotation-positive` failed. All four later groups and the entire real phase remained unvisited. This is evidence against the tested coordinate/feature path at the fixed native accuracy limit, not a reason to lower that limit.

## The decisive independent check

The private reference is 3072 by 2304 native pixels. Its exact counterclockwise permutation makes a source image 2304 by 3072. Direct image-index reasoning gives source-to-reference centre coordinates `x_ref=3071-y_source`, `y_ref=x_source`. The auditor derives this literal map and evaluates integer Q32 residuals without importing the prototype, matcher, or fitter.

The actual registrar returned **256** captured rows, **128/128 calibration inliers**, **128/128 holdout inliers**, and held-out RMS **0.187776034 native pixels** against its own fitted map. Yet its four source-corner errors against the known permutation are **4.004566385, 4.049269136, 3.975505395, and 4.020531276 native pixels**. The required one-pixel corner bar fails independently at every corner.

**MEASURED, all captured rows against literal truth:** **0 of 256** lie within two native pixels; RMS is **4.003144935 native pixels**, and the median reference-minus-truth offset is **[4.0, 0.0] native pixels**. This uses every captured row, with no fit-selected subset or fitted nuisance constant. The returned map is self-consistent with these correspondences while wrong against known truth. Its small fitted residual is therefore not evidence of physical accuracy. This finding does not identify why the feature coordinates carry that offset.

The actual saved coarse and native arrays each contain **1024** features for reference and source; every native point equals `8*q_coarse+896`. The fault is not a missing lift in those retained arrays. No inference about a detector option, interpolation phase, or library default is certified here; those require a new declared intervention.

Distinct descriptor rows again overstate spatial support: the 256 matches occupy **237 exact joint endpoint groups**, with **10** groups appearing in both calibration and holdout. Independently re-chosen one-native-pixel adjacency gives the same counts, no transitive over-radius components, and 11 direct cross-split row-pair witnesses. Site counts do not establish statistical independence or image coverage. The truth failure remains even though it is assessed across all 256 rows.

## What actually ran and stopped

Saved individual evidence confirms the seven inherited controls and the two new averaging controls passed. Ties-to-even boundaries retained their literal expected integers. Repeated-block and coarse-rotation hashes agree as recorded; their pixel arrays were not decoded independently by this audit. The tenth group retained an actual returned map, its captured coordinates, exact corner fractions, and `passed=false`.

`native-two-pixel-map-destroyer`, `centre-offset-destroyer`, `native-rotation-restored`, and `rotation-observer-null` are **UNVISITED**. In particular, the later active missing-centre call did not run. The auditor's own small arithmetic commissioning of an omitted centre is a different operation and must not be reported as that subject control passing.

The worker recorded **zero real decode attempts and zero completed real decodes**, no real feature or pair files, all 23 pair ordinals unvisited, and no topology. Parent and worker exited **1**, with the named control failure retained. Sources remained unchanged and finalization errors were empty. The owned Job reached terminal accounting with two processes observed and zero active, no kill attempt, and no process-helper or cleanup error. Job CPU was **6.796875 seconds**, wall **7.062 seconds**, and peak committed Job memory **172,728,320 bytes**, within the released limits. These are resource records, not comparative performance claims.

## Authority, inventory and resource carry

The auditor verifies the actual external plan/result/outer/console/exit digests, reconstructs both command arrays independently, checks the closed request and six native-baseline refs, preserves all **170** old source bindings within the expanded closure, and checks the cached **23 native refusals** without rerunning them. Source files, plan, requests, private features, control files and receipts were hash-checked; all **234** consumed metadata/source files were rechecked afterward. TIFF refs received extent/identity checks only. Their live payload hashes were not recomputed; image, descriptor and detector-key digests remain producer witnesses linked through the pinned evidence.

The exact owned output inventory is **17 files / 728,511 bytes**. Independent `Get-ChildItem -Recurse -Force -File` counting agrees. All bytes are charged as new files and metadata; no RAW snapshot or TIFF was written. The earlier 30-CPU-second/60-wall-second/2-MiB preparation reservation and older snapshot charges remain fully carried.

Actual final totals are **460.390625 CPU seconds / 526.1505195999998 internal wall seconds / 3,951,804,048 file bytes / 26,603,402 metadata bytes**. The root outer wall gives the conservative next wall carry **526.2322624 seconds**. All local/global bounds pass, with complete CPU accounting despite the scientific refusal.

## Reproduction and limits

The auditor was completed after root supplied the actual failure notice; this is a disclosed retrospective verification, not a blinded prospective test. Its independent choices are the all-row literal-truth comparison, integer corner arithmetic, and one-pixel site grouping. Ten small commissioning cases ran before reading subject results: correct rotation, missing centre, plus-two-native translation, exact one-pixel boundary, wrong rotation sign, repeated sites, distinct-site companion, chain disclosure, all-row exact truth, and an all-row four-pixel shift. The known shift must change the truth score from all three rows accepted/zero RMS to zero accepted/four RMS.

Actual audit command ran **once**, exit **0**, no stderr:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -B experiments\m193c-output-grid\work\independent-factor-eight-1-audit.py --plan-sha256 3d8b2c4e2e7e21d3bdc59994b2cffef3cf2687e6cf914b4a6992f52357d2e994 --result-sha256 36c8efcacaad8f946c01557788286dca3a7b3b791ed895491a5e2d2f4093e6ce --outer-sha256 b2241f51a4af58cc61060ab919d9fef91d88ffafbbe447ff0b89f41fb4cdc369 --console-sha256 99fae12227b0c502d934c5ddf52963da9fc51d8e3b75b8fcbdfc68aa98d7c110 --exit-sha256 f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04
```

- Audit source `work/independent-factor-eight-1-audit.py`: **42,893 bytes**, SHA256 `4b4736b8a95ef7d347dd2ad98cc66ac4460e1d77d7f735e68f016e8e26912e30`.
- Result `work/independent-factor-eight-1-audit.json`: **18,934 bytes**, SHA256 `386a2c56515041d4c71a63b77876d3f987be1d2993182b9317b68db4ccea7440`.
- Schema `m193c-saved-factor-eight-audit-v1`; status `PASS_SAVED_FACTOR_EIGHT_OUTCOME_AUDIT`; `subject_complete=false`; `refused_control=native-rotation-positive`.
- Audit-internal CPU **0.234375 seconds**, wall **0.2390866 seconds**; enclosing invocation wall **0.3010209 seconds**. The earlier oversized source-writing command was rejected by Windows before process creation; it did not execute an audit or subject.

The auditor includes a complete-population branch, but this actual outcome exercises only its failed-control branch. No image was opened, no subject imported, and no new feature, matching or fitting call occurred. No sharpness/noise metric, merge placement, overlap certificate, consumer manifest, product change or SOTA claim follows. The coarse coordinate guard remains explicitly unqualified.
