# Independent slide2 photographic attribution

**Observed:** the seven fixed region/frame witnesses do not establish a lost
or doubled printed feature caused by the current merge. They also do not
establish that the complete output is clean. New current-only views selected
by root expose broad gray spread at other, larger printed boundaries; those
are the useful next attribution targets.

I inspected the complete current overview, then pale149 first and every one
of the 21 unresampled384x384 raw/gathered/merged panels listed in
`render-1/native-views.json`. I also inspected both separately displayed green
phases for all seven nominations, without reranking or moving any region.
The complete source is `render-1/off/output/replay.tiff` (6476x4316), SHA256
`24c66183ae94df908eb4a8662fc4b032532b7721655dfcc867e9a7d59b4f655b`;
`render-1/matched-full.png` and the explicitly reduced overview remain saved.
This is current-baseline attribution, not a candidate-improvement comparison.

## Fixed witnesses

| Site and nominated ordinals | Specific observation |
|---|---|
| Pale149 | Raw and gathered show a nearly featureless pale field with a few faint spots. Merged has finer visible granularity and additional faint point structure. There is no printed edge here that can demonstrate doubling. This is not a temporal-noise estimate, and the extra points are not automatically recovered detail or invented defects. |
| Medium139/141 | The upper horizontal and vertical bar groups, left number/bar column and right-side groups remain distinct in merged. Several groups blurred in a nominee become more separated in merged. The tiny central groups remain limited, but I cannot identify a separation present in gathered139 or141 that the merge removes, or a new duplicated stroke. Focus varies within each nominee; neither is an all-in-focus patch truth. |
| Fine126/128 | The short bar groups surrounding the central black square and the longer diagonal leaders are more distinctly separated in merged. Ordinal128 is visibly softer in substantial parts of the source patch than126. Merged does not visibly lose an identifiable short bar from either gathered witness. This does not resolve the finest subgroups beyond available native sampling. |
| Lettering152/154 | The rounded counter near the right, the openings between the multi-stem letters at left, and the lower sloping rule remain present in merged. The rule is narrower and the rounded counter better bounded than in the nominated sources. No unambiguous doubled character or missing opening appears. Ordinal154 is softer around the rounded letter; that neighbor does not reveal a hidden clean source advantage. |

The two green phases support the same qualitative source-focus limitations;
their separate pitch2 displays do not reveal a strong G1-only feature on
which the nomination conclusion depends. They are not interchangeable with
the native product RGB panels. Small color fringes, background texture and
brightness differences alone are not evidence of source-detail retention or
true geometry.

Raw patches are source-centered and even-rounded, without registration or CA
correction. Only gathered and merged share the exact output grid. I therefore
make no positional-error inference from raw/gathered contour displacement.
The merged panel duplicated under two neighboring source labels is the same
fixed output region, not an independent merge replication.

## Separately selected current-output problem sites

After the fixed witnesses, root selected three new384x384 current-only crops
from this same full output, before any new source/candidate evidence:

| Site | Output-native xywh | Visible problem to investigate |
|---|---|---|
| QR upper | [3700,490,384,384] | Broad gray polygonal spread surrounds isolated white squares and intrudes into black corners/gaps. This is much wider than a simple narrow edge fringe. |
| QR lower | [3900,900,384,384] | Gray bands and rounded corner spread fill portions of the dark intervals around the white vertical elements and beneath the wide white rule. |
| Siemens contact | [5260,750,384,384] | Broad gray fans occupy portions of the nominally dark wedges beside bright wedges. The central junction remains recognizable, while the dark-field gradation is the conspicuous issue. |

These views and coordinates are in `render-1/broad-artifact-inspection/`.
They were **not** part of the frozen21 matched witnesses and have no matched
source attribution yet. Their appearance does not prove whether spread was
already captured optically, follows placement error, or is introduced by
reconstruction. A geometry intervention forced from the cleaner small-bar
sites would lack evidence. Target the actual broad-spread sites next, holding
their newly selected coordinates fixed before examining source evidence.

## Evidence scope

Root ran `render.py --locator experiments/slide2-focus-witness/locate-1 --out
experiments/slide2-focus-witness/render-1`. Both complete299-source jobs exit0
with zero active processes, in 97.484s off and 109.907s on. Saved receipts show
zero differing RGB16 samples and identical whole-TIFF hashes off/on. All
seven merged panels equal their complete-output slices exactly, including
the extra interior trim; every structured wrong-origin control differs.
Original metadata and nominated content are unchanged.

Locator controls had already demonstrated that noisy flats can outrank
blurred texture; all seven nominated patches matched an independent rawler
decode and all four source149 actual-CFA goldens matched. This qualifies the
data and addressing, not the scalar peaks as quality truth. The historical
baseline differs from the new output (recorded separately); different binary
and rounded pinned tone prevent attributing those differences to a new gain.
No new scans, metrics, coordinates, registrations or source selection were
performed in this review. These observations do not exonerate the whole slide
or the user's other ghosting and glare complaints.
