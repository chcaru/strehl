# Saved-coordinate diagnosis after direct-pair-1

2026-09-07. **MEASURED saved-coordinate summaries; DERIVED incompatibility witnesses; ARGUED next action.** This is a diagnostic of existing JSON, not a new registration or an independent audit of the enclosing run. The separate saved-outcome audit owns execution/resource authority. No subject module was imported, no frozen fitter/matcher was called, and no TIFF or RAW was opened. No held file was changed.

**The data do not demonstrate a shared axis, scale-unit, or transform-direction defect. They do demonstrate inconsistent descriptor correspondences, repeated physical locations counted as separate landmarks, and a large shift in feature support across the sweep.** Several late pairs also contain a plausible small-motion population. Its existence is insufficient to admit a transform at the frozen tolerance. Keep all 23 refusals. The next useful experiment is a small real-content known-coordinate replay, followed by a spatial-support challenge, rather than a threshold reduction or a graph solve.

## Data and independently chosen calculation

The population is all eight saved pairs with at least 24 matches, all of which stopped at `choose_similarity`'s initial calibration-consensus guard. The other 15 never reached that guard. Native centres use width 7032, height 4688, with saved Q8 coordinates divided by 256. Local indices 0..8 correspond to originals 0,13,26,39,52,65,78,91,104. Directions below are **source → reference**. No per-frame placement in the merge's original-52 gauge has been produced.

The first script fixed, before its execution, unfit identity/axis-swap/reflection/factor-two checks; edge bands of 64/128/256 pixels; a 4×4 spatial table; and a calibration-only model formed by the componentwise median of complex slopes over source baselines ≥512 pixels, then the median intercept. Holdout residuals were evaluated without fitting to holdout. This re-chooses the estimator instead of invoking or reproducing the frozen maximum-consensus fitter. Its 2/8/32/128-pixel residual counts are descriptive scales, **not replacement acceptance bars**. A follow-up selected after that summary retained exact endpoint duplicates and contradictions. No significance or preregistered causal claim is attached to that exploratory follow-up.

Sources/results:

- [First calculation](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/work/direct-pair-coordinate-diagnosis.py) and [its exact result](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/work/direct-pair-coordinate-diagnosis.json), SHA256 `78c9a4556876cb4aa52f1af2961b4fa71d619c5645a8a065a328f7d9ec6c2510`.
- [Endpoint follow-up](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/work/direct-pair-coordinate-details.py) and [its exact result](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/work/direct-pair-coordinate-details.json), SHA256 `7d95a121b81bacc77540722175612b5e5e9cbf6018d84e1547719df71aab5182`.

Both results bind the exact bytes of the eight pair JSONs and nine feature JSONs. Actual commands, each exit 0, were:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -B experiments/m193c-output-grid/work/direct-pair-coordinate-diagnosis.py
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -B experiments/m193c-output-grid/work/direct-pair-coordinate-details.py
```

## What the frozen refusal means

Text-only inspection of [reference.py](C:/dev/blog/death-of-software/projects/strehl/experiments/M193-cover-overlap/reference.py:468), SHA256 `c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790`, finds: at least 24 total mutual matches; alternating digest-ordered calibration/holdout split; hypotheses from calibration pairs separated by at least 32 pixels in both images; allowed scale 0.5..2; 2-pixel calibration radius; at least 12 calibration inliers **and at least half** the calibration population. Despite the error's word “majority”, equality at half is accepted. Only after this guard do refitting and the distinct ≥12/at-least-half holdout and ≤1-pixel RMS checks occur.

| Source→reference local | Total | Calibration | Required calibration inliers | Raw displacement median, native px | Identity ≤2 px |
|---|---:|---:|---:|---:|---:|
| 2→1 | 26 | 13 | 12 | 1120.87 | 0 |
| 4→3 | 25 | 13 | 12 | 1352.72 | 0 |
| 4→5 | 46 | 23 | 12 | 24.70 | 3 |
| 6→4 | 24 | 12 | 12 | 49.32 | 3 |
| 6→5 | 53 | 27 | 14 | 25.33 | 3 |
| 7→5 | 29 | 15 | 12 | 60.65 | 3 |
| 7→6 | 50 | 25 | 13 | 24.51 | 9 |
| 8→7 | 44 | 22 | 12 | 31.17 | 9 |

Thus the minimum count is stringent for the sparse pairs: 12/12 or 12/13, not merely a half-majority. But the saved observer did not retain the winning rejected hypothesis or its support count. **The exact distance from the frozen gate remains unmeasured.** The independent model's residual counts are not that missing statistic, and do not establish that increasing a radius would make any full registration pass.

The six simple unfit coordinate alternatives do not give a convincing common explanation. In the four later adjacent pairs, identity's median displacement is roughly 25–31 pixels, versus thousands for an axis swap, reflection, halving or doubling. This is a limited gross check, not proof that every coordinate association is correct.

## Direct inconsistency and spatial evidence

**A model-independent contradiction:** [pair-3-4.json](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/direct-pair-1/worker/pair-3-4.json) contains three groups with an identical source Q8 point and different reference destinations. Their reference separations are 1488.913, 928.485 and 2624.619 native pixels. [pair-7-8.json](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/direct-pair-1/worker/pair-7-8.json) gives source Q8 `[1777677,1048864]` two reference points `[1325022,1056474]` and `[1523435,1075884]`, 778.751 pixels apart. Any deterministic source-to-reference mapping predicts one destination for one source point. By the triangle inequality, both errors cannot be ≤2 pixels when the destinations are more than 4 pixels apart. This cannot be repaired by choosing a better global scale, rotation, translation or affine map; at least one correspondence in each group is wrong.

**Descriptor rows are not distinct spatial evidence.** File `pair-6-7` has actual direction **7→6**. Its nine identity-near matches occupy only two exact reference locations, approximately `(6405.08,237.32)` and `(4913.23,546.00)`. The 8→7 pair's nine occupy three. Exact joint endpoint groups cross calibration/holdout in seven of the eight investigated pairs, with 1–3 such groups per affected pair. SIFT's multiple descriptors/orientations at a location are a plausible explanation; the saved coordinate/key hashes do not expose orientation metadata to prove it. The frozen matcher enforces mutuality between descriptors, not injectivity or disjointness between physical locations. A digest split therefore does not guarantee spatially independent holdout. This threatens a future positive interpretation; it is not evidence that deduplication alone would rescue the present refusals.

**Support changes across the image.** Among 1024 retained features, local1/original13 has 873 in the upper half and only 2 in the lower quarter. Local5/original65 has 18 in the upper half and 994 in the lower quarter; locals6–8 have only 14–18 in the upper half. Later pair matches are also concentrated low: 34/46, 39/53, 26/50 and 27/44 lie in the reference lower quarter for directions 4→5, 6→5, 7→6, 8→7. Those regions were selected as fixed fractions, with full 4×4 counts retained. This supports changing spatial availability. It does not identify the physical subject, prove defocus as the cause, or show global coverage even if a small lower-image model were to pass. Fixed 256-pixel edge bands do not account for all these points; call this lower-image concentration, not a proven border artifact. The nearly stationary upper-image sites may be scene, sensor or representation features; coordinates alone cannot decide.

**Some later displacement is structured.** The independently chosen calibration model gives scale/rotation approximately `0.987793/+0.046°`, `1.007657/+0.025°`, `1.004194/−0.022°`, `1.004894/−0.0003°` on 4→5, 6→5, 7→6 and 8→7. Corresponding holdout median residuals are 6.30, 13.79, 15.28 and 15.31 native pixels, with respectively 1,0,0,1 holdout points within 2 pixels. These are exploratory descriptions of a small-motion population plus outliers, **not accepted camera magnifications or model-error estimates**. For two early pairs this estimator collapses to implausibly small scales with hundreds/thousands of pixels of residual; those values describe estimator failure on inconsistent matches, not optical shrinkage. Neither the median model nor its inability to reach 2 pixels proves the frozen optimal hypothesis cannot do better.

## One next experiment and its decision

**First isolate the real-content coordinate/representation path with two bounded same-frame crop replays, using one early and one late admitted derivative, before testing a new matcher.** Freeze a small integer-coordinate crop pair for each (for example an upper-image crop on local1 and a lower-image crop on local5). Each second crop is displaced by a literal nonzero `(37,−19)` native offset; the exact source→reference crop-coordinate map is `x_ref=x_src+37`, `y_ref=y_src−19`. The underlying native map is identity after restoring crop origins. Crops must be array slices of the same authenticated decoded image: no interpolation, extra blur, rescale, tone remapping or noise. Keep the frozen detector, matcher, hypothesis limits and acceptance criteria. Include same-crop identity, wrong-direction/crop-origin oracle and restored companions; a positive must return enough actual support and satisfy the independent literal-coordinate oracle. A crop without enough support is a recorded diagnostic failure, not permission to search crops until one passes. This tests real-content coordinate handling at the selected crop scope, not cross-focus robustness or full-native detector memory behavior.

Add one cheap, separately named **spatial-evidence control**: repeated descriptor identities at two physical sites must not be reported as twelve spatially independent landmarks or a disjoint spatial holdout. A companion with distinct, spread-out locations must pass that evidence check. Preserve the frozen registrar's raw returned/refused disposition separately; this control does not silently change its algorithm. If a later experiment adopts location-grouped splitting, it needs a new explicit method and the former digest split as a comparison. Reversing a real pair changes the digest split and is not a placebo.

If known-coordinate real-content replays fail, fix the demonstrated seam/representation failure first. If they pass while the existing cross-focus pairs remain inconsistent, test one bounded alternative support representation or local area-based observation on fixed early/late real pairs, with the same real-content replay and independent spatial holdout. Require predictive improvement in the merge's per-frame gauge, not just more matches, lower training residuals or a connected graph. The current evidence does not justify selecting a specific alternative descriptor, filtering the nearly fixed sites, changing the radius, or fitting a graph.

This ordering follows the corrected local history: [SYNTHESIS facts 45/172–174](C:/dev/blog/death-of-software/projects/strehl/docs/research/SYNTHESIS.md:964) withdraw the attribution of a bilinear plant's effect to defocus; the resampler-free self-pair is deliberate. [M78 facts 1097–1099](C:/dev/blog/death-of-software/projects/strehl/docs/research/SYNTHESIS.md:1655) show that blur equalization can improve conservation while worsening held-out prediction. [M103 facts 1407–1410](C:/dev/blog/death-of-software/projects/strehl/docs/research/SYNTHESIS.md:1965) require a named per-frame consumer gauge and invalidate unconditional short-edge deletion. None licenses treating these new descriptive residuals as physical truth.
