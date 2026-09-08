# Independent read of the real AREA8 + precise-SIFT attempt

2026-09-07. **VERIFIED saved-outcome audit PASS; all 23 real registrations remain REFUSED.** The subject completed its fixed observation, not a geometry or quality admission. No parameter change, second real arm, image read, new extraction, matching, fit, or numerical-subject import belongs to this audit.

The held audit source was committed in `5a3739f7` before the subject ran. A separate source reader checked its helper wiring/cache associations without execution and found no blocker. Root supplied the actual terminal digests after one parent/worker run. The unchanged auditor then ran once: exit 0, empty stderr, 1.09375 CPU seconds / 1.0935755000009522 internal wall seconds; outer launch wall 1.155354599999555 seconds. A preceding transient launch wrapper had a Python syntax error before executing any statement: it launched no auditor, wrote no file and caused no subject rerun.

## What completed and what failed

All fourteen inherited control rows passed. The positive and restored rows additionally passed four complete canonical cache comparisons; they are predicates within existing rows, not extra controls. Nine real TIFFs were decoded, nine feature records returned, all 23 ordered pairs were visited once and every scientific refusal was retained. No pair was unavailable or unvisited.

The saved failure reasons are **21 calibration-consensus refusals**, **one held-out RMS refusal**, and **one held-out-consensus refusal**. For pair 2-3, source original 39 to reference 26, the matcher error reports held-out RMS **1.035343942 native reference pixels**, exceeding the unchanged 1.0 bar. Pair 3-4, source 52 to reference 39, reports no held-out majority. The other 21 report no majority landmark consensus. These are exact saved error witnesses. Refused outcomes retain no map/metrics; the auditor does not reconstruct their failed fits, independently recompute that RMS, or infer how many true matches exist.

All 23 now contain 29-252 descriptor rows versus 7-53 in their exact native baseline, with more rows in every pair. This combined AREA8 + precise-SIFT path still returns **zero real maps**. The native comparison changes both representation and detector option; there is no real AREA8/default-false arm because the prior factor-eight attempt stopped at its private control. The real difference cannot be assigned solely to the detector option. More matches are not evidence of physical correctness.

## Re-chosen locations and complete pair inventory

Re-group all saved rows by exact source/reference coordinates, independently of descriptors and inlier selection. Then use radius 1 native pixel separately at each endpoint; joint adjacency requires both endpoint Euclidean distances to be at most 1. Components are transitive: a chain can have diameter greater than 1, so the auditor explicitly reports diameters/chaining. A three-point 0/0.75/1.5 native pixel commission confirms that this alternative can merge and chain. All actual real endpoint/joint groups here have diameter 0: radius 1 makes no additional merges.

Exact joint groups number 28-221 per pair. **21/23 pairs** contain exact joint locations on both calibration and holdout; exceptions are 1-5 and 2-5. Repeated locations are not independent support, and a radius that leaves groups unchanged does not certify their independence or correspondence truth. The complete endpoint memberships were checked against saved rows; only compact summaries are repeated here.

All rows below are REFUSED. C = saved calibration no-majority; R = saved held-out RMS above 1.0; H = saved held-out no-majority. Directions use original frame indices; the pair ID uses local indices. Counts are descriptive, not accuracy scores.

| Local pair | Reference <- source | Native / new descriptor rows | Exact joint groups | Joint groups shared across splits | Reason |
| --- | --- | ---: | ---: | ---: | --- |
| 0-1 | 0 <- 13 | 7 / 154 | 147 | 6 | C |
| 0-2 | 0 <- 26 | 7 / 90 | 84 | 2 | C |
| 0-4 | 0 <- 52 | 15 / 74 | 69 | 3 | C |
| 0-5 | 65 <- 0 | 17 / 63 | 57 | 3 | C |
| 1-2 | 13 <- 26 | 26 / 237 | 208 | 18 | C |
| 1-3 | 13 <- 39 | 14 / 115 | 109 | 2 | C |
| 1-5 | 65 <- 13 | 7 / 81 | 79 | 0 | C |
| 2-3 | 26 <- 39 | 14 / 252 | 221 | 10 | R |
| 2-4 | 26 <- 52 | 18 / 131 | 119 | 3 | C |
| 2-5 | 65 <- 26 | 16 / 63 | 62 | 0 | C |
| 2-6 | 26 <- 78 | 21 / 43 | 42 | 1 | C |
| 3-4 | 39 <- 52 | 25 / 231 | 214 | 5 | H |
| 3-5 | 65 <- 39 | 15 / 70 | 66 | 2 | C |
| 3-7 | 39 <- 91 | 18 / 29 | 28 | 1 | C |
| 4-5 | 65 <- 52 | 46 / 232 | 204 | 10 | C |
| 4-6 | 52 <- 78 | 24 / 91 | 79 | 4 | C |
| 4-8 | 52 <- 104 | 17 / 37 | 32 | 3 | C |
| 5-6 | 65 <- 78 | 53 / 242 | 219 | 8 | C |
| 5-7 | 65 <- 91 | 29 / 90 | 79 | 4 | C |
| 5-8 | 65 <- 104 | 22 / 47 | 41 | 3 | C |
| 6-7 | 78 <- 91 | 50 / 213 | 190 | 13 | C |
| 6-8 | 78 <- 104 | 22 / 89 | 78 | 7 | C |
| 7-8 | 91 <- 104 | 44 / 178 | 155 | 13 | C |

The returned-edge graph independently has **nine singleton components, zero edges, cycle rank 0 and no bridges**. Edge-removal checks, rather than the producer's bridge choice, determine bridges; a tree, ring and empty nine-node graph commission their power. Reporting anchor local 4/original 52 and matching reference local 5/original 65 remain distinct singleton components. No chain or graph solve was run. This is the topology of returned diagnostic edges, not a per-frame placement or physical-geometry measurement.

## Controls, option evidence and coordinate gauge

Exactly 11 applicable factory witnesses exist: two private and nine real, each with one actual constructor call, explicit boolean `enable_precise_upscale=True`, unchanged five baseline constructor arguments, restoration true and no error. Every real witness agrees with the copy attached to its feature receipt before extraction. Parent witness arrays are empty. Factory identities themselves are opaque producer witnesses interpreted alongside the pinned scoped wrapper; this metadata audit cannot independently observe the past live Python object.

The 9 real feature counts, in original-index order 0,13,26,39,52,65,78,91,104, are **487,1024,1024,1024,1024,1024,1024,910,734**. All actual coarse/native arrays obey `q_native=8*q_coarse+896`; emitted match coordinates belong to their associated native feature arrays. Shapes remain 7032x4688 -> 879x586; coarse-image, descriptor and key hashes remain opaque authenticated receipts, not newly recomputed payload hashes.

The complete private feature receipt and complete positive outcome canonically equal the audited prior true arm. Restored outcome equals both fresh positive and cached true, without omitted fields or tolerance. Its literal source-to-reference native map is `x'=3071-y,y'=x`. Independent integer corner errors are 0.0007681312112573364-0.0015512533203470358 native pixels. Against that literal map, **all 256 captured rows** give 255 within 2 native pixels, RMS 0.20194783600424362 and median reference-minus-truth offset [0,0]. This keeps the one outlier and differs from the fit-selected held-out RMS.

The actual +2-native-tx destroyer gives 1.999124068977266-2.0014086707849903-native corner errors and fails the 1 native pixel bar. The actual missing-centre arm uses 8q+0 and gives 6.981661349069731-7.006810077034233-native corner errors; restored full records return to the cached truth-positive result. Off/count/placebo signatures hash identically. The seven legacy controls remain on their frozen unwrapped path. These are private known-fixture checks; they neither certify cross-focus real coordinates nor establish a universal detector-bias mechanism.

Every real record retains lattice step 8 Q8 with inherited guard quantum 1 Q8 and **UNQUALIFIED_FOR_COARSE_LATTICE**. Residuals can reward physically biased maps; here they are consistency/error witnesses only. No support, overlap, common-crop, geometry manifest, render-quality or SOTA acceptance follows from this observation.

## Authority, accounting and reproducibility

The audit checked the closed new plan, entire inherited source closure including the original 170 bindings, six completed private baseline FileRefs, original native 23 FileRefs/refusals, exact parent/worker argv with only declared hash substitutions, request population/directions, saved environment/runtime, terminal log/exit associations and final source rechecks. It uses only the pinned independent factor-eight standard-library audit helper; it never imports numerical subject modules. Every consumed metadata source was rehashed after the audit; TIFF extents/identities were stat-checked without opening payloads.

Actual subject terminal Job: 25.875 CPU seconds, 26.171000000000276 wall seconds, peak committed 509616128 bytes, two processes and zero active at completion. No termination attempt, helper error, cleanup error or finalization error occurred; parent/worker CPU accounting is complete. All local/global/Job limits passed. Inventory is 54 files / 5,578,203 bytes, independently confirmed with `Get-ChildItem -Recurse -Force -File`; 300 metadata files were hash-checked. No snapshots were created.

No-refund prior: 530.46875 CPU, 626.5200758 wall,3,956,544,489 file bytes,31,343,843 metadata bytes. Final actual work:557.75 CPU,653.9890757999983 internal wall,3,962,122,692 file bytes,36,922,046 metadata bytes. Conservative next wall is **654.0280850** = 626.5200758 + actual outer 27.5080092. The new 20 CPU seconds / 30 wall seconds / 1 MiB preparation allowance includes this audit reservation; nothing from the failed earlier attempts is refunded.

| Actual artifact | Bytes | SHA256 |
| --- | ---: | --- |
| console | 393 | `b65bc49f17044d719060737bf7d78aeba1d48b9b9cf005163f3ec04bc3000658` |
| exit | 3 | `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` |
| outer | 1048 | `c2fd17007ed7e18e6ba0d9199f1e9df0399f38b40237bf4117d9d43245f26280` |
| plan | 37546 | `4364546cdade4133946b81f3a241839f280306bf7ac1a056174a46788da5f1d4` |
| result | 43505 | `82cc275d4fc78b43a1b63752e763e085a1d211a8a2b2e6686291315d806b013b` |
| worker | 894809 | `f040d2a2826b1e3df46da0c8b10bdd1d10b50a545acb03605be0a57784ffae11` |

Audit source: 33,051 bytes, SHA256 `10c0b84b51b5ae45f116fc1265b9a32b182ac30e44e62b0512e04d38964eabe5`. Result `work/independent-real-precise-1-audit.json`:78,821 bytes, SHA256 `7920f885e0cea2bcfbe2ac4f9af9ffc519212495274798cee23b79aa2e179ccc`. Helper: 42,893 bytes, SHA256 `4b4736b8a95ef7d347dd2ad98cc66ac4460e1d77d7f735e68f016e8e26912e30`. New source/result/report together stay below the reserved 196 KiB; old audit artifacts are unchanged.

The exact audit command launched from the repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B 'C:\dev\blog\death-of-software\projects\strehl\experiments\m193c-output-grid\work\independent-real-precise-1-audit.py' --plan-sha256 4364546cdade4133946b81f3a241839f280306bf7ac1a056174a46788da5f1d4 --result-sha256 82cc275d4fc78b43a1b63752e763e085a1d211a8a2b2e6686291315d806b013b --outer-sha256 c2fd17007ed7e18e6ba0d9199f1e9df0399f38b40237bf4117d9d43245f26280 --console-sha256 b65bc49f17044d719060737bf7d78aeba1d48b9b9cf005163f3ec04bc3000658 --exit-sha256 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354
```

Disposition: the combined real pipeline supplies more retained candidate rows but still fails the unchanged direct registration criteria on every pair. Retain the failure as evidence for the next decision; do not relax a threshold to convert it into an admission.
