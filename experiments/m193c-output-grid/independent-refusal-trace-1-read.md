# Independent saved refusal-trace audit, attempt 1

**VERIFIED: PASS_SAVED_REFUSAL_TRACE_OUTCOME_AUDIT.** Four private controls, all 23 real records and 77 saved-match registrar calls completed. All 23 real results remain refusals: 21 at calibration consensus, local 2-3 at held-out RMS and local 3-4 at held-out consensus. This is a complete diagnostic observation, not usable geometry or a quality admission.

The [prospective audit source](work/independent-refusal-trace-1-audit.py) was frozen in release `f43b966e0a37eb3e66f4bae48050bd7b97a40935` before subject output existed. After root supplied the actual references, it ran once, exited 0 and wrote the [held result](work/independent-refusal-trace-1-audit.json). No image payload/stat was read, no detector or matcher ran, no numerical subject module was imported, and no unvisited fit or second exhaustive search was performed.

## Independent choices and scope

The verifier derives each selected two-endpoint seed with exact integer ratios and signed ties-to-even rounding. Actually visited least-squares refinements use independent pair-difference identities. It checks every retained signed/squared residual, split, native two-pixel boundary, fixed CDF/quantile, coordinate census, selected-row update, caller state, visited gate and exact original refusal message. Integer arithmetic checks the RMS bar before floating summaries.

The alternative population is **every held-out row**, alongside selected inliers. The independent median is the conventional median of residual magnitudes, averaging both central magnitudes at even N. The producer's predeclared nearest-rank p=0.5 selects the lower one. Local 1-2 seed holdout therefore has conventional 1.919144069 versus nearest-rank 1.888268691; local 2-3 final holdout has 1.711824340 versus 1.677666912. These definitions intentionally differ. All distances here are native reference-image pixel-centre residuals for the source-to-reference map.

Selected-seed score arithmetic, seed counts and frozen loop/key semantics were checked; **global seed optimality was not independently re-enumerated**. Eligible counts 89-7609 are producer witnesses. Pinned loop coverage and actual nonperturbation hashes supply partial assurance, not a second search.

Commissioning covers signed ties, inclusive baseline/scale/residual limits, a scale destroyer, exact rotation, singular refinement, separate minimum/half gates, all-row selection, wrong rotation sign, missing centre, +2-native map shift, repeated/distinct/chained sites and all-landmark truth/shift checks. It demonstrates power to reject without rerunning the subject.

## Real paths: near misses and broad disagreement

| Actual path | Pairs | Independent finding |
|---|---:|---|
| Seed fails minimum 12 and half | 13 | Both predicates fail |
| Seed meets minimum 12 but fails half | 8 | Minimum alone is insufficient |
| Seed passes; held-out RMS refuses | 1: local 2-3 | Three refinements, then 1.035343942 > 1.0 |
| Seed passes; held-out count refuses | 1: local 3-4 | One refinement, then 54/115 needs 58 |

Every pair has an eligible selected seed. All 21 seed refusals visit zero refinements. Local indices correspond to original frames 0,13,26,39,52,65,78,91,104; the complete fixed population and directions remain in the result.

Local **1-2** is one calibration row short: 59/119 needs 60. Its unrefined seed has 60/118 held-out rows within two native pixels, but no refinement or held-out gate was visited. This does not establish an unvisited refined outcome. Among the 21 seed refusals, required support deficits extend to 26 rows and conventional all-held-out medians span 1.919144-99.797452 native pixels. Failures are not uniformly narrow.

Local **2-3** performs three successful refinements with calibration subsets 77 -> 73 -> 74 -> 74, then stabilizes. Final calibration is 74/126; held-out is 67/126. Independent inlier RMS 1.035343941561068 reproduces the cached 1.035343942 message. All-held-out RMS is 225.102193759; conventional median 1.711824340; nearest-rank p90 6.217130847, p95 10.129417887, maximum 2270.892082447. Held-out counts at 0.25,0.5,1,2,4,8,16,32 native pixels are 4,12,38,67,97,117,120,122 of 126.

Local **3-4** performs one successful refinement, preserving 61 calibration inliers. Final held-out is 54/115, a four-row half deficit despite passing minimum 12. Conventional/nearest-rank median is 2.077655126; all-held-out RMS 786.934278973; p90 25.571613181, p95 1134.248945903, maximum 4520.308317828. Counts at the same thresholds are 0,2,25,54,80,94,100,106 of 115. Its descriptive inlier RMS 1.242583303 is not an actual RMS-gate rejection: that gate was unvisited.

All four real refinement calls succeed; no failed fit, cycle or fallback occurs. Coordinate grouping limits support interpretation: local 1-2 seed calibration has 59 supported rows in 57 exact joint-coordinate groups; local 1-5 has five rows in three groups. Local 2-3 final calibration/holdout has 74/67 rows in 67/61 groups; local 3-4 has 61/54 rows in 57/49 groups. Distinct sites and broad extents do not prove independent physical support. The preceding real audit's exact/radius-one-native re-choice found no additional near-site merges on this population.

## Private truth and observer controls

The independently literal map is x'=3071-y, y'=x from native source 2304x3072 to reference 3072x2304. It scores all 256 matches and all four source corners.

| Private arm | All matches within 2 native pixels of truth | All-match truth RMS | Actual result |
|---|---:|---:|---|
| False-option counterexample | 0/256 | 4.003144935 | Returns; all corners fail one-native-pixel bar |
| True-option known map | 255/256 | 0.201947836 | Returns; all corners pass |
| Within-split association destroyer | 1/256 | 1681.081621167 | Refuses at calibration: 3/128; no fit |
| Restored true | Same as complete true trace | Same as true | Entire trace canonical equality |

False has calibration/holdout 128/128 and held-out inlier RMS 0.187776034, yet literal median offset [4,0] native pixels. True has calibration 127/128 and holdout 128/128, offset [0,0]; its one truth outlier stays in the population. Excellent fitted residuals can accompany a wrong map. This finite example is not a universal detector-bias claim.

The declared SHA-based within-split permutation was independently reconstructed: 255 pairings change, preserving source-coordinate marginals within each split, reference coordinates, digests, row order and split labels. Restoration reproduces the complete true trace, including maps, caller states, residuals and signature.

Recorded canonical hashes agree off/on/placebo for the 23 real refusals and two cached private returns: 25 triplets / 75 calls. Permutation and restored-true each add one traced call, totaling 77. Off/placebo full values were not separately saved, so this audit checks retained actual execution hash witnesses. Complete on-results were compared to cached originals, and complete restored/true traces were directly compared. No independent registrar rerun was performed.

## Authority and accounting

The audit checks the seven-key closed plan, full source closure and baseline ancestry, exact request/argv, native authority, prior carry, terminal Job receipt, inventories and error fields. It hashes 275 metadata files. Parent/worker exit 0 with COMPLETE_SAVED_REFUSAL_TRACE_ONLY; nothing is unvisited. Independent recursive inventory including hidden files agrees on 31 files / 1,922,639 bytes.

Job CPU is 12.109375 s, wall 12.234000000000378 s, peak committed memory 31,592,448 bytes; two total processes, zero active or terminated. Helper, cleanup and finalization errors are empty; no kill was attempted. All global/local/child CPU, wall, memory, log and byte caps pass. These are budget receipts, not performance benchmarks.

Final cumulative work: 591.234375 CPU seconds, 697.5280849999999 internal-wall seconds, 3,965,093,907 file bytes, 39,893,261 metadata bytes. Outer 13.54700000000048 gives conservative next-wall `697.57508500000048`; no refund. Audit CPU was 0.28125 s, internal wall 0.27359749999959604 s, launcher outer 0.3464203000003181 s.

| Actual binding | Bytes | SHA256 |
|---|---:|---|
| console | 397 | `570f7669d507ba85f8110061b6d5db6dda37891ab68d5e6199c0e875e9b2e86b` |
| exit | 3 | `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` |
| outer | 1051 | `5335077f1f96a283d9caa9024cf13b4d537b615e8be13418e71ed702f4317a59` |
| plan | 38628 | `327ffd9e27270542e8f7c93ee37827a4beb5eb9291394924f66590dcf3baaeef` |
| result | 55306 | `cca664d2941581463966707aec16236998bd670058deaa7f6d4ebd1d11d3ba9d` |
| worker | 51744 | `551aad07138995c44b00c51af0a590c07da2a3d99e98d64c1e11961c30086a85` |

Complete paths and actual worker argv are in the JSON. Audit source: 43,271 bytes, SHA256 `18093725797dea574ada23053fb3cebaff22734811d48ff41276a1908f6389ac`. Result: 118,456 bytes, SHA256 `eed8b4949d7f1ec4def3defccb7cad24f8ef971e34e027b5247b618273c15428`.

Actual audit command, once from repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B 'C:\dev\blog\death-of-software\projects\strehl\experiments\m193c-output-grid\work\independent-refusal-trace-1-audit.py' --plan-sha256 327ffd9e27270542e8f7c93ee37827a4beb5eb9291394924f66590dcf3baaeef --result-sha256 cca664d2941581463966707aec16236998bd670058deaa7f6d4ebd1d11d3ba9d --outer-sha256 5335077f1f96a283d9caa9024cf13b4d537b615e8be13418e71ed702f4317a59 --console-sha256 570f7669d507ba85f8110061b6d5db6dda37891ab68d5e6199c0e875e9b2e86b --exit-sha256 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354
```

The consumer is the saved registrar rejection path. The 8-Q8 coordinate lattice does not qualify the inherited 1-Q8 support guard; every candidate remains NONADMISSIBLE_DIAGNOSTIC_CANDIDATES. Selected residuals can hide false maps; all-row RMS can be dominated by gross outliers; medians can hide tails; counts can repeat sites. None distinguishes correspondence, localization or model error on real images without independent truth. The evidence supports a bounded representation comparison, not relaxed gates, physical placement, support, graph solving, merge quality or SOTA admission.
