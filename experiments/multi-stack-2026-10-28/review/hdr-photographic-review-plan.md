# Independent HDR photographic comparison plan

FROZEN before viewing fused HDR or its rendered controls,2026-10-28, by root/independent_review. Root alone schedules engine work. This preparation read saved JSON/text geometry, the existing1s-middle locator, and derived64x64sensor-block clipping counts. It read no RAW/cache pixel arrays, ran no decoder or engine, and did not view any fused HDR photograph.

## Fixed displays and witnesses

MEASURED report-only freeze command, exit0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/freeze-hdr-review.py

hdr-photographic-freeze.json SHA256 012d3809c843d9a5491d89b2c028c0363d6d22d93767d327efeda10869f1b301 binds all inputs and12native384witnesses. Nine chart/field centers were selected from the existing1s-middle locator, including the previously adverse p12flare area, gray ramp, QR grid/corner, radial star, fine bars and bright/faint dot fields. Three additional clipping witnesses were selected from saved6s-middle block-count evidence by maximum aggregate/blue counts and a mixed-clipping boundary, with raster-order tie breaks and512pixel separation. No favorable fused output influenced selection.

The saved global gauge is6s-middle DSC00047.ARW, index32within the long pass, global93in the new126source session and153in the old186source solve. Source hash identity is checked. The old measured map only transports1s locator landmarks into that physical frame; it does not establish pixelwise registration or placement truth. Original6s clipping witnesses already use that sensor. Once the final canvas is saved, subtract twice its plane origin and round full-coordinate center minus191.5 to nearest integer with floor(x+0.5). Require every384square in bounds, no content-driven reposition, no resampling. Reuse exactly this map/domain for all three arms.

Use both predeclared displays identically on all complete linear masters and crops:

| View | Black | White | Exposure gain | Contrast |
| --- | ---: | ---: | ---: | ---: |
| Physical reference | 0 | 4 | 1 | 0.55 |
| Highlight headroom | 0 | 4 | 0.25 | 0.55 |

These constants are chosen before output inspection in the6s sensor-reference master units. They are not a fitted optimal display. The second view is a fixed additional2EV reduction, always applied to every arm, so bright encoded pixels cannot hide recoverable structure merely because the first view saturates. Reuse the independently commissioned common soft-toe/gamut/sRGB/contrast implementation and the frozen display ICC. Transform files are hdr-physical-reference-transform.json and hdr-highlight-headroom-transform.json. Do not use each master embedded auto-tone placement or per-arm exposure matching.

## Required comparisons and input checks

Compare complete126source HDR with complete2.5s-only61sources and6s-only65sources, all on the exact126source alignment envelope and final canvas. Verify original identities, output dimensions, map hash, calibrated gains, selected source counts, zero unsupported output pixels, original clipping receipts and actual output color basis. The accepted measured gains are currently[2.5335414,1] in6s units; do not refit these for review. Keep all refused3pass evidence alongside the successful2pass result: this arm does not validate the excluded1s pass or establish universal HDR robustness.

A specific control confound was found before these images were viewed: current render() chooses only_pass before the session anchor for output WB. Saved2.5s WB is[2.7587890625,1,1.5322265625],6s WB[2.7392578125,1,1.560546875]. Color matrix/levels match, but these WB differences alone change red/blue output. The root was notified before HDR controls. A causal color comparison requires a common session-anchor WB/matrix for non-Layers only-pass controls or another explicit common-WB control; otherwise report that confound and do not attribute color shifts to fusion. Per-pass appearance is appropriate for Layers, a different contract.

Inspect each complete fixed-display output for missing chart fields, crop inconsistency, seams, broad brightness/color transitions, clipped plateaus and large halos before viewing native witnesses. At native384 inspect spoke/line separation, dot boundaries, falsely repeated/colored texture, contrast reversals, halos and the adverse flare region. Mark losses as well as improvements. The chart is patterned rather than a known-noise flat; spatial SD, gradient energy and apparent crispness do not establish temporal-noise reduction or recovered resolution.

## Highlight claims require original and consumer evidence

The existing independent nine-source preflight proves original6s clipping in G1/G2/B and no clipping in its sampled2.5s sources. The frozen6s-middle clipping core has all1024G1,1024G2 and1024Bsites clipped in each64x64sensor block, red0; the selected boundary has1023G1,1024G2,B0. These are original-u16 facts, not display-white inference.

However, registered-highlight-opportunity.json mapped those clipped sites into a1s-middle source, which is not part of this2.5s/6s session. Its98.97-100%coverage cannot certify actual2.5s support here. The9source preflight is also not a census of all126originals. Read the actual completed consumer per-source covered/clipped counts. If all61short sources have full-canvas coverage and zero original-footprint clipping, that establishes uncensored short availability everywhere in the canvas; otherwise require local witness coverage and original nonzero tap masks. Global totals alone do not locate partial support.

Availability still differs from contribution. Before saying recovered highlight detail, require co-located original long clipping, actual unclipped short support, and evidence that eligible short samples contribute to the delivered region/bands rather than a saturated fallback. Preserve spatial/band provenance if available. If the existing reports cannot establish it, ask root to schedule a bounded witness support audit or limit the result to visual differences plus measured clipping opportunity. A white display pixel, brighter output, or a plausible short-only image alone is insufficient.

No runtime/photographic conclusion is entered here. The implementation author is not the sole verifier; this reviewer will independently inspect the complete outputs and native crops after root release. Insect controls remain first priority.
