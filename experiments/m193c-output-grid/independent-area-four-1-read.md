# Independent fixed AREA4 outcome audit, attempt 1

**VERIFIED: PASS_SAVED_AREA_FOUR_OUTCOME_AUDIT.** All 14 controls, nine feature observations and 23 real pairs completed, with no unvisited pair. All 23 real fits refused. The measured development outcome is `ZERO_RETURNED_EDGES_AT_FIXED_AREA4`: this fixed representation did not obtain a diagnostic real map under the unchanged gates.

The [prospective audit source](work/independent-area-four-1-audit.py) was frozen before subject execution in `fb955db0ed2d3b35af306b518050817296a6c215`. Root released the actual references, then the frozen auditor ran **once**, exited 0 with empty stderr, and wrote the [held audit result](work/independent-area-four-1-audit.json). No source repair or audit retry was needed. The audit reads metadata only: no image payload/stat, feature extraction, matching, fit, numerical subject import or skipped computation.

## Complete paired result

The comparator is the exact completed AREA8+precise population, not the historical native/default-false arm. The same nine authenticated image references and 23 pair directions are retained. AREA4 changes sampled image content, detector support, candidates, descriptors, associations and resulting splits; any difference is a representation-pipeline effect with precise=true fixed.

Every AREA4 pair has fewer tentative matches than its AREA8 counterpart: 14-102 versus 29-252. AREA4 feature counts are 510 at original frame 0 and 1024 at all eight other frames; AREA8 counts were 487,1024,1024,1024,1024,1024,1024,910,734. More retained features did not produce more matches or any returned real map. Counts do not measure physical accuracy.

| Local pair | AREA8 matches | AREA4 matches | AREA4 exact joint sites | Actual AREA4 refusal |
|---|---:|---:|---:|---|
| 0-1 | 154 | 76 | 64 | calibration consensus |
| 0-2 | 90 | 37 | 32 | calibration consensus |
| 0-4 | 74 | 35 | 30 | calibration consensus |
| 0-5 | 63 | 22 | 19 | too few matches |
| 1-2 | 237 | 88 | 72 | held-out consensus |
| 1-3 | 115 | 37 | 35 | calibration consensus |
| 1-5 | 81 | 30 | 28 | calibration consensus |
| 2-3 | 252 | 96 | 84 | held-out RMS |
| 2-4 | 131 | 50 | 45 | calibration consensus |
| 2-5 | 63 | 28 | 27 | calibration consensus |
| 2-6 | 43 | 34 | 30 | calibration consensus |
| 3-4 | 231 | 78 | 72 | calibration consensus |
| 3-5 | 70 | 29 | 29 | calibration consensus |
| 3-7 | 29 | 14 | 14 | too few matches |
| 4-5 | 232 | 74 | 65 | calibration consensus |
| 4-6 | 91 | 41 | 34 | calibration consensus |
| 4-8 | 37 | 20 | 17 | too few matches |
| 5-6 | 242 | 79 | 69 | held-out consensus |
| 5-7 | 90 | 45 | 36 | calibration consensus |
| 5-8 | 47 | 26 | 18 | calibration consensus |
| 6-7 | 213 | 91 | 82 | calibration consensus |
| 6-8 | 89 | 39 | 32 | calibration consensus |
| 7-8 | 178 | 102 | 84 | held-out consensus |

Local indices correspond to original capture indices 0,13,26,39,52,65,78,91,104. Every full record and exact AREA8 FileRef is preserved in the audit.

The reason totals are 16 calibration-consensus refusals, three too-few-match refusals (0-5,3-7,4-8), three held-out-consensus refusals (1-2,5-6,7-8), and held-out RMS refusal at 2-3: `1.238896564 px exceeds 1.0`. The AREA8 reason totals were 21 calibration, one held-out consensus at 3-4 and one RMS at 2-3 (`1.035343942`). Several paths change stage; this is not evidence that real geometry improved. Refused AREA4 outcomes do not retain candidate maps, so this audit does not reconstruct their internal residuals or silently rerun a registrar to obtain them. RMS values in refusal messages remain exact saved registrar observations.

Re-chosen exact joint-coordinate groups number 14-84 per real pair. Eighteen pairs have a joint site shared across calibration and holdout. Independent radius-one-native connected components add no merges for any real pair, on either endpoint or jointly; their diameters are zero because merged rows are exact duplicates. Counts, distinct sites and broad extents do not establish independent physical support. The union-find rule could chain points farther than one pixel; a 1.5-pixel chain control proves the audit detects and discloses that case.

The complete returned-edge graph has zero edges, nine singleton components, cycle rank zero and no bridges. The anchor (local 4/original 52) and matching reference (local 5/original 65) remain separate singletons. Graph checks use independent components and edge-removal bridges, commissioned on empty/tree/cycle cases. This is topology only; no graph solve, placement, support, overlap or merge was produced.

## Private physical truth and retained controls

The native fixture is unchanged: source 2304x3072 into reference 3072x2304, with literal x'=3071-y, y'=x. The verifier checks integer corner errors against that oracle and independently scores **all** saved match coordinates, rather than only fitted inliers.

AREA4 has 256/256 private matches within two native reference pixels of literal truth, all-match RMS 0.066750029 and median truth offset [0,0]. The same native fixture under audited AREA8 has 255/256 and RMS 0.201947836. These are different retained association populations; this finite fixture comparison does not establish a universal localization improvement or cross-defocus accuracy. AREA4's four corner errors are 0.010343-0.024370 native pixels, all below the one-native-pixel bar. Its retained-map held-out RMS is 0.034915426 over all 128 held-out rows, independently checked with integer residual arithmetic.

The +2-native-pixel map mutation has corner errors 1.987567-2.013046 and is rejected by the one-pixel oracle. Omitting +384 Q8 from both endpoint lifts produces an actual returned wrong map with corner errors 2.995222-3.007447 native pixels. That map still has selected held-out RMS 0.052247805, demonstrating why good fitted residuals cannot admit physical geometry. The earlier false-option four-pixel counterexample remains in the inherited authority.

The restored outcome is directly equal as a complete canonical value to the fresh AREA4 positive. The restored feature record is not separately saved: its complete canonical byte-count/hash witness equals the saved positive feature record (195,111 bytes), and the audit labels that retention limit. Actual observer off/count/placebo signatures are directly reconstructed from the saved outcomes and have identical canonical hashes; no new extraction is involved. The seven legacy controls remain unchanged. AREA4 half-tie arithmetic and repeated-block null pass with their independently constructed expected values/hashes.

Two private and nine real factory witnesses each record exactly one constructor call with the five original arguments plus explicit precise=true, no error and successful restoration. All nine real feature records returned. Actual coarse/native arrays obey `4q+384` in Q8, with native shapes 7032x4688 and coarse 1758x1172; private arrays are also checked. Coarse-image, descriptor and detector-key hashes are opaque producer witnesses, not independently decoded values. All new outcomes carry the four-Q8 lattice qualifier: the inherited one-Q8 support guard remains **unqualified**.

## Authority, execution and accounting

The audit checks the closed seven-key plan, all 210 source bindings including the entire previous 203, trace/AREA8/native authority and all 23 native refusals, exact parent/worker argv and requests, compact parent versus full worker control records, runtime, final restoration, terminal Job accounting, final error fields and output inventory. Earlier source and audit artifacts remain unchanged.

Parent and worker exit 0 with COMPLETE_AREA_FOUR_DIAGNOSTIC_ONLY. Finalization/helper/cleanup errors are empty; no kill was attempted. Terminal Job has two total processes, zero active or terminated, CPU 27.1875 seconds, wall 27.610000000000582 seconds and peak committed memory 783,155,200 bytes. Every local/global/child CPU, wall, byte, memory and log cap passes. Independent inventory including hidden files is 53 files / 3,305,129 bytes; 382 metadata files were hashed. These are budget receipts, not timing benchmarks.

Final cumulative work: 639.9375 CPU seconds, 757.8720860000012 internal-wall seconds, 3,969,447,612 file bytes, 44,246,966 metadata bytes. Outer 30.34399999999914 yields conservative next-wall `757.91908599999914`. The prior charged the complete old trace plus 20 CPU/30 wall seconds and one MiB, with the old wall rounded upward to a microsecond before addition; nothing is refunded. Audit CPU was 1.328125 seconds, internal wall 1.4304938999994192, launcher outer 1.5023803000003682.

| Actual binding | Bytes | SHA256 |
|---|---:|---|
| console | 392 | `97acc2bf4ee22cf5bbabf74aac2195019c87f6de03630777e3c4410a6631081f` |
| exit | 3 | `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` |
| outer | 1038 | `100799bc98357a610b210b2ca8d4d970e427d1e7c3cce3385d50057bd1808991` |
| plan | 39877 | `7c83db049cc869b2428b7e0aa321ece23b91c0b05c6143c3414591479afa41d6` |
| result | 74216 | `188c0f304e1abcc0a60b65db420e16fe22d9e5a51a3b267aef8cb2b2451047ce` |
| worker | 515559 | `c07aef266dc1a7e75f5a8a7c99f7c7075bf9952e681b26d5e984db69e15e3675` |

Audit source: 47,147 bytes, SHA256 `7826aa80ded536c1383d04232f99fd14c97f67667105bf6f0b142e180e0793ae`. Audit JSON: 97,082 bytes, SHA256 `02c97674a2128fc1d31ba687aa0fe3e98648e5a0604783ad4006166b29814adc`. Complete actual paths and worker argv are in the JSON.

Actual audit command, once from repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B 'C:\dev\blog\death-of-software\projects\strehl\experiments\m193c-output-grid\work\independent-area-four-1-audit.py' --plan-sha256 7c83db049cc869b2428b7e0aa321ece23b91c0b05c6143c3414591479afa41d6 --result-sha256 188c0f304e1abcc0a60b65db420e16fe22d9e5a51a3b267aef8cb2b2451047ce --outer-sha256 100799bc98357a610b210b2ca8d4d970e427d1e7c3cce3385d50057bd1808991 --console-sha256 97acc2bf4ee22cf5bbabf74aac2195019c87f6de03630777e3c4410a6631081f --exit-sha256 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354
```

**ARGUED research decision:** reject this fixed AREA4 arm as a route to obtaining diagnostic maps on this population. The experiment does not justify a threshold relaxation or another unregistered scale sweep. A new correspondence method may now be considered through an independently reviewed, bounded comparison preserving these complete failures. Private rigid-rotation success, tentative counts, fitted residuals and connected graphs can each favor the wrong physical interpretation; none authorizes SOTA, real placement or consumer support admission.
