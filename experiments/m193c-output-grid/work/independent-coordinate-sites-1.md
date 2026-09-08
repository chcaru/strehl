# Independent saved-coordinate site review, version 1

2026-09-07. **VERIFIED saved-coordinate duplication and incompatibility; no accepted registration or image-quality result.** The author's central endpoint findings survive an independent calculation and a larger population. All 23 frozen refusals remain refusals. No TIFF, RAW, feature extractor, matcher, fitting routine, or subject module was opened or invoked by this audit.

## What was re-chosen

The author inspected the eight pairs with at least 24 matches and grouped exact endpoints using dictionaries. This audit reads **all 23 saved pair JSONs**, constructs an explicit adjacency graph, and traverses connected components. It reports source endpoints, reference endpoints, and joint endpoints separately, at exact Q8 equality and at a radius of **one native pixel (256 Q8 units)**. Joint adjacency requires both endpoint distances to be within that radius. Every component retains its row indices, diameter, split membership, and direct cross-split adjacency witnesses.

This is independent implementation and re-chosen grouping/population, not a blinded replication: the author report and endpoint script were read before this work. No robust model or alternative transform is estimated. Distances are between retained native image-centre coordinates within the named source/reference pair, not per-frame placement errors in the merge's original-52 gauge.

Connected-component grouping can merge sites farther apart than its radius through a chain. A pre-data control at 0, 0.75, and 1.5 native pixels deliberately does this; the result must retain a 1.5-pixel component diameter and the actual cross-split adjacency. **No such over-radius component occurred in the real data**, on either individual endpoint side or the joint side. All reported grouping summaries are unchanged between exact equality and the one-pixel alternative.

## Findings

**MEASURED:** Exact joint endpoint groups cross calibration/holdout in **14 of all 23 pairs**, including **7 of the author's 8 pairs with at least 24 matches**. This means some held-out descriptor rows repeat the same retained source and reference coordinates already present in calibration. Distinct digests do not create distinct spatial support. It does not establish statistical independence of the remaining locations, nor prove that the original matcher would accept a false transform.

For the eight pairs that reached the calibration guard, the number of mixed-split exact joint groups is:

| Pair file | Actual source to reference, local | Rows | Mixed joint groups, exact / one pixel |
|---|---|---:|---:|
| pair-1-2 | 2 to 1 | 26 | 2 / 2 |
| pair-3-4 | 4 to 3 | 25 | 0 / 0 |
| pair-4-5 | 4 to 5 | 46 | 3 / 3 |
| pair-4-6 | 6 to 4 | 24 | 1 / 1 |
| pair-5-6 | 6 to 5 | 53 | 2 / 2 |
| pair-5-7 | 7 to 5 | 29 | 1 / 1 |
| pair-6-7 | 7 to 6 | 50 | 2 / 2 |
| pair-7-8 | 8 to 7 | 44 | 2 / 2 |

Local indices 0..8 denote originals 0,13,26,39,52,65,78,91,104. In `pair-6-7`, the nine rows within two native pixels of identity occupy **two** exact reference sites. In `pair-7-8`, nine such rows occupy **three**. The one-pixel grouping leaves both counts unchanged. These counts describe spatial repetition; identity proximity is not a quality score and can be increased by stationary background or erroneous repeated correspondences.

**MEASURED witnesses, DERIVED incompatibility:** There are **nine distinct identical-source-Q8 groups across five pairs** whose reference destinations are more than four native pixels apart. The author-selected pair-3-4 gives separations **1488.913, 928.485, and 2624.619** native pixels; pair-7-8 gives **778.751**. Those numbers reproduce. The expanded population additionally finds two such source groups in pair-2-4, two in pair-2-6, and one in pair-3-7. The result retains all row-pair witnesses, without mistaking several witness combinations inside one group for several distinct source groups.

For example, pair-7-8 rows 0 and 12 share source Q8 `[1777677,1048864]`, but their reference Q8 points are `[1325022,1056474]` and `[1523435,1075884]`. A deterministic map of that retained source point has one prediction. By the triangle inequality it cannot be within two native pixels of both destinations when their separation exceeds four. This is a contradiction in the saved correspondences, not evidence for a common axis or units defect, a physical cause, or an admissible corrective transform. Neither the author's orientation explanation nor sensor/background origin of repeated sites is established by coordinates alone.

## Failure power and limits

Seven pre-data controls passed through the same grouping and contradiction functions: twelve descriptor rows at two sites must yield two mixed groups; twelve distinct sites must yield twelve disjoint groups; a five-pixel conflicting destination must be detected; its four-pixel boundary companion must not be labelled a strict contradiction; the radius-one chain must reveal its 1.5-pixel diameter; a common endpoint translation must preserve the grouping result; and reversing rows must preserve the contradiction count. These controls can reject broken site counting, hidden chaining, and an incorrect strict boundary. They do not certify image decoding or the scientific identity of a landmark.

Each input is read and SHA256-bound, checked for retained Q8 types/bounds, null inlier labels and refused/null-transform disposition, then rehashed after calculation. This is a saved-evidence audit. It does not authenticate coordinate generation from image pixels or re-audit the enclosing Job, source freeze, or complete execution inventory. The separate direct-pair outcome audit owns those claims. Image quality, sharpness, noise, and full-corpus immutability were not measured; no such claims are made. No merge observer was added, so a new on/off render comparison is inapplicable.

**ARGUED next use:** Any future positive should expose distinct site counts and spatial overlap between its fitting and validation populations. More descriptor rows or a low residual alone cannot discharge spatial support. Changing the splitter would be a separately declared method; this audit neither changes the frozen matcher nor predicts that deduplication or coarser features will rescue any refusal.

## Reproduction and exact artifacts

Actual command, once, exit **0**:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -B experiments/m193c-output-grid/work/independent-coordinate-sites-1.py
```

- Source: `work/independent-coordinate-sites-1.py`, **9,064 bytes**, SHA256 `2f65e2cc3dfebaa74cb96b907a5963da47c43e19ca9edc7821991a885462cf9b`.
- Result: `work/independent-coordinate-sites-1.json`, **96,741 bytes**, SHA256 `d7e096fd9c9d59da8db8bf666d5900c1a563ae682a2465dbc279dcfcefc44bd3`.
- Result schema `m193c-independent-coordinate-sites-v1`; status `PASS_SAVED_COORDINATE_REVIEW_ONLY`; all 23 source hashes unchanged. Script-internal measured CPU **0.0625 s**, wall **0.1094783 s**. These are bookkeeping for this bounded calculation, not performance claims and not the enclosing tool latency.
- Reviewed author report: `work/direct-pair-coordinate-diagnosis.md`, **12,370 bytes**, SHA256 `8325027025aa6cac9652dcf631cb25b96926ba7206ee34920836bae6cd415e0e`. The original report, scripts, and results were not edited.

Relevant discipline discharged here: AGENTS 8/11/12/20/24 by labelled scope, seven first-run controls, a different verifier, re-chosen population/grouping and explicit failure inputs; AGENTS 6 and SYNTHESIS 1407/698/699 by refusing to turn within-pair endpoint counts into merge placement evidence. No architectural change, synthesis fold, source-number allocation, RAW decoding, or metric-driven parameter sweep occurs.
