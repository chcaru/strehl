# Independent complete marigold B comparison

MEASURED / VISUALLY REVIEWED, 2026-09-26. This complete B reference does **not** establish an overall photographic improvement over corrected Current. It retains useful hair structure, but introduces conspicuous milky bands and loss of fine structure in bright petal interiors. No production promotion, SOTA claim or new vendor setting sweep follows from this comparison.

I first inspected the complete Current overview from `illuminant-aware-color/views-1/marigold4-current-overview.png` and the complete B overview from `run-2/helicon-b/overview.png`. Current's overview is bound to the earlier exact RGB16/ICC rewrite of the corrected master. I then inspected all six newly extracted native panels described below. The two complete images were shown to the owner by root before this detail review.

## Complete-image observations

No obvious trial text, logo or grid overlay is visible in either complete view. This is a visual observation, not proof that every pixel is overlay-free. B passes the independently checked full 7032x4688 RGB16/ICC output requirement; Current is 6268x4176 because of its held crop.

The main petal junctions, pollen clusters and hair groups are recognizable in both views. B has cleaner-looking portions of some hair boundaries and retains a substantial range of focused anatomy. It also has large gray/milky patches across the upper-left folded cup and flatter, smeared-looking bright interiors, particularly the central-left rounded petal. These are visible at whole-image scale, before any native crop was chosen. Current has its own occlusion spread and ghosting problems; the comparison does not certify Current as a good final stack. B simply is not a generally better answer to those problems in this fixed workflow.

## Three fixed manual counterparts

After the complete-image review, root authorized exactly three native pairs, at most 384 square per image. I froze all six coordinates before extraction. The locations use each image's own overview scale and recognizable anatomy, without fitting or assuming a global transformation. No window moved after its panel was seen. They are semantic counterparts, **not aligned pixel truth**; no difference image, quality score or estimated displacement is reported.

| Landmark | Current native xywh | B native xywh | Independent observation |
| --- | --- | --- | --- |
| Hanging tip and rear hair fan | 3230,3000,384,384 | 3690,3400,384,384 | Correspondence is recognizable through the fan, near reflective tips and descending isolated hair. B retains near and finer extended groups; some near tips appear better separated against its darker background. Both still show diffuse overlapping hair structure. This is mixed/comparable local evidence, not a decisive overall win. |
| Rounded bright petal and orange speck cluster | 1436,1844,384,384 | 1566,2113,384,384 | The cluster is retained, but B is darker/more yellow and changes the bright interior's gradation. A darker patch cannot by itself prove recovered texture or correct highlight response. This pair does not establish a clear detail advantage. |
| Upper-left folded cup | 1448,273,384,384 | 1644,339,384,384 | The fold and specular cluster establish the anatomical counterpart. Current shows a long fine dark diagonal strand and mottled bright surface structure. B replaces much of this with broad gray/milky bands; the strand is strongly weakened/interrupted, with some lower portion still visible. This confirms the adverse whole-view impression. |

`comparison-1/extract.py` makes direct 384-square RGB16 copies from the two complete TIFFs. It preserves exact RGB16 TIFF masters and PNGs with the original ICC, checks PNG channel/code identity through a second codec, and records full master hashes, dimensions, source grids and chosen coordinates in `comparison-1/receipt.json`. There is no resize, registration, exposure normalization or other processing. The existing Current fan window was retained exactly. Failed anatomical correspondence would have been recorded as uninformative rather than repaired by recentering.

## Admission and limits

The saved development receipt has all 488 sources, the old normalization/developer golden and the exact complete Current CFA-cache rewrite. The latter matches corrected Current RGB16 and ICC with the pinned baseline matrix, tone and exposure. Prepared inputs were freshly hashed before and after B; original metadata checks pass. Vendor processing exited 0 with clean terminal accounting in 68.735s, after 253.969s of sequential development. These are bounded job readings for this workflow, not controlled algorithm-speed or SOTA measurements.

Run1's build source guard refusal and subsequent development refusal remain valid historical failures: the reviewer inserted 12 readability spaces into the pre-run report during its binding window. No RAW batch ran from that refused build. Root used a fresh run2 build, preserving the failed provenance rather than reconciling it retrospectively. The frozen pre-run review was not changed for these results.

This external reference uses CA-off, individually developed inputs and independently fitted vendor alignment. Current uses CA-on CFA gathering and development after merging. Vendor brightness/interpolation settings remain unrecovered application state. Identical preparation metadata therefore does not make the final outputs radiometrically equivalent or isolate a merge mechanism. The bands and detail loss are photographic observations, not a diagnosis of which vendor stage caused them. Likewise, this one fixed B radius 8/smoothing 4 run does not establish engine superiority in either direction across the corpus.

The practical result is narrower and useful: an all 488-source external reference does **not** automatically resolve the marigold defects, and the selected workflow has visible regressions. It is unsuitable as a clean target image or source of presumed ground truth. Further program choices must keep the specific bright-interior and hair protections rather than reward smoothing alone.

Commands executed by root:

```text
python experiments/marigold-comparator/run.py build --out experiments/marigold-comparator/run-2
python experiments/marigold-comparator/run.py develop --out experiments/marigold-comparator/run-2
python experiments/marigold-comparator/run.py b --out experiments/marigold-comparator/run-2
```

Reviewer extraction command executed after root authorization:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -I -B -X faulthandler experiments/marigold-comparator/comparison-1/extract.py
```

Corrected Current complete TIFF SHA256: `19e657e419d52adf567ec86472f917ad9b9abfc9b0812131e9bba0eacbae462f`. B complete TIFF SHA256: `30740f1c0c9cd9c5d24112121117b76da8444da0951ba26408dd5f365385cee5`. B RGB16 SHA256: `4bc00a63663e49370b80d59ec4cc0db0c19918021a24ca8fd644c46aec3cfc42`. Shared ICC SHA256: `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`.
