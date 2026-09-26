# Focused slide2 witnesses and current complete stack

2026-09-26. **MEASURED / VISUALLY REVIEWED:** the new focused originals do not
expose a lost or doubled bar or lettering stroke at the three existing sites.
The merge resolves more of the targets than either nominated source, whose
focus varies across each patch. This is a bounded attribution result, not
evidence that the complete slide is clean or SOTA. No reconstruction changed.
The independent photographic review records the separate visual judgment.

Root commands, using installed Python 3.12 with `-I -B -X faulthandler`:

```
experiments/slide2-focus-witness/locate.py --out experiments/slide2-focus-witness/locate-1
experiments/slide2-focus-witness/render.py --locator experiments/slide2-focus-witness/locate-1 --out experiments/slide2-focus-witness/render-1
```

The locator reads all299 originals once and redecodes six selected originals.
Its unchanged pooled G1 score nominates medium-bars139/141, fine-bars126/128,
and lettering152/154; pale149 remains the control. All seven nominated patches
match the second decoder exactly; all four source149 normalized-CFA checks
match the previous actual observer bit for bit. The flat control runs first
and demonstrates that noise can outscore blurred detail. These scores locate
inspection candidates; they cannot prove image quality or correct geometry.
Originals are copied as u16 inside the decoder lifetime; no aligned image
volume or full source RGB processing is introduced.

The current retained build renders all299 originals with the same map,
reference149, crop[139,93,3238,2158], camera correction and pinned tone.
Observer-off/on complete6476x4316 RGB16 TIFFs are byte-identical; all seven
merged patches and their inner checks equal the full-image slices exactly.
Wrong +2-pixel lookups differ at every structured site. All21 native384-pixel
views share the same development. Raw patches are source-centered and have no
warp/CA correction; only gathered and merged views share exact coordinates.

| Job | Wall seconds | Peak Job committed bytes |
| --- | ---: | ---: |
| Original-frame locator | 122.391 | 177082368 |
| Complete observer-off | 97.484 | 3185991680 |
| Complete observer-on | 109.907 | 3185582080 |

These are single operational observations, not overhead or speed benchmarks.
All jobs terminated normally with no active child processes. All299 original
metadata/order and selected original content remain unchanged. This is not a
fresh full299 content audit. The source/binary/helper/map bindings are retained.

The full master is `render-1/off/output/replay.tiff`, SHA256
`24c66183ae94df908eb4a8662fc4b032532b7721655dfcc867e9a7d59b4f655b`;
decoded RGB16 SHA256 is
`1398f855dee5767b36f4efe11b8999324449fb50baa1e32a57659a2987429fbb`.
`render-1/matched-full.png` and the complete overview retain the whole frame.
The historical automatic output differs at13064783 channel samples, maximum
65535DN, under different binary/numerics and rounded tone. That comparison is
provenance, not a new quality claim or a causal attribution to one code change.

## The actual next defect

After reviewing the frozen witnesses, root selected three additional384-pixel
current-output-only regions before reading any new source there:
QR-upper[3700,490], QR-lower[3900,900], and Siemens-contact[5260,750].
`render-1/broad-artifact-inspection/coordinates.json` records them. These show
conspicuous broad gray polygonal spread around white print in black gaps and
gray fans in nominally dark wedges. Both root and the independent reviewer
see this defect at native size. These are new problem sites, not part of the
original21 views, independent repetitions, or before/after improvement pairs.

The next action is the same focused-source comparison at those actual defects,
under `experiments/slide2-bright-boundary`. Reuse this exact observer-off master
instead of paying for another identical baseline. The existing small-bar
comparison does not justify a geometric correction. The new current-only
views also cannot yet distinguish optical spread, source mixing or geometry.
Do not turn the absence of a lost small stroke into evidence that broad glare,
ghosting or the user's other corpus defects have been solved.
