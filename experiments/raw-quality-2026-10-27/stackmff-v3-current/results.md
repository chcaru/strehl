# Complete weevil comparison: local cleanup, no quality promotion

2026-10-27. **MEASURED complete execution; VERIFIED photographic tradeoff.**
The current pinned StackMFF V3 produces a complete 299-source weevil photograph,
but does not deliver the substantial improvement sought. Root inspected the
complete candidate, previous native output and Helicon B4, then every fixed
native candidate/baseline pair and the relevant B4/B8 comparisons. The separate
[photographic review](photographic-review.md) covers all ten witnesses against
all three vendor arms. The [independent integrity review](full-results-review.md)
verifies the complete output and presentation.

## Photographic decision

Some existing lower leg hairs are easier to separate from their dark background:
the broad gray/cyan haze around them is reduced. Parts of the upper occlusion
contour also look less veiled. This is a limited boundary-rendering difference,
not evidence of new hair shafts or recovered scale topology. Several scale
fields and the diagonal strand remain soft or become softer. The long pale
wing rim and the colored blue/green junction persist. Bright glints remain;
smaller or dimmer glints alone do not establish recovered structure.

The fixed black-background witness loses random-looking speckle but reveals
faint coherent green curves near its left edge and lower right. Root and the
independent reviewer both see them in the unchanged native-size panel; they
are absent in the native/B4/B8 reference panels. Their source origin is not
established, so do not label them generated detail or assign a physical cause.
No extra retone or sharper crop was used to nominate these findings.

**Do not promote this model, optimize this exact implementation for release,
or call it a native RAW fix.** The complete result is useful competitive
evidence and a local haze/detail tradeoff, not SOTA, a generally applicable
insect improvement or a reason to abandon all learned reconstruction. No
temperature, source-subset or count correction follows without new evidence.
The [source-count audit](../stackmff-source-count/source-audit.md) is algebraic
only and does not identify an actual softness mechanism.

## Complete photographs and full-resolution masters

All images below retain their existing sRGB interpretation. Native and V3
share reference149 and delivered origin(68,46), but use different interpolation
and development order. Helicon has its own geometry and a different canvas;
its mapped native crops are locators, not pixel-identical alignment.

| Workflow | Complete image | Full-resolution RGB16 master |
| --- | --- | --- |
| Current V3,6896x4596 | [JPEG](../../../outputs/raw-quality-2026-10-27/stackmff-v3-views-1/output/complete-stack.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-27/stackmff-v3-full-1/output/stack-master.tiff) |
| Previous native CA-off,6896x4596 | [JPEG](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-full.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-master.tiff) |
| Helicon B4/S4,7020x4676 | [JPEG](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-full.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-master.tiff) |
| Helicon B8/S4,7020x4676 | [JPEG](../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/b/stack-full.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/b/stack-master.tiff) |
| Helicon C/S4,7020x4676 | [JPEG](../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/c/stack-full.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/c/stack-master.tiff) |

The full V3 RGB16 TIFF is190,167,088 bytes,
SHA256 `908259e71e6b88d2134c0fb81dcdb257d79d773323c6dd8dbeb579d0306fd1c6`.
The complete JPEG is9,915,406 bytes,
SHA256 `17b4d79982951e7e4a9880922d2a30e8bc1c13537949a8f72610facbeab401c0`.
The [view receipt](../../../outputs/raw-quality-2026-10-27/stackmff-v3-views-1/output/receipt.json)
binds all ten unchanged384-square witnesses. Independent readback confirms
every PNG exactly matches the corresponding full master converted by division
by257 with nearest rounding. These are supplemental inspections; full images
and masters above are the primary deliverables.

## Execution and full-workflow accounting

Commands actually run from the worktree, all exit zero:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/stackmff-v3-current/run.py controls
python -B -X faulthandler experiments/raw-quality-2026-10-27/stackmff-v3-current/run.py cost
python -B -X faulthandler experiments/raw-quality-2026-10-27/stackmff-v3-current/run.py full
python -B -X faulthandler experiments/raw-quality-2026-10-27/stackmff-v3-current/run.py views
```

The frozen [brief](brief.md), [protocol](comparison-protocol.md),
[model review](model-review.md), [input bridge](input-bridge.md) and
[execution decision](execution-decision.md) record the input identities,
controls, source/license/checkpoint hashes and exact defaults. The complete
worker source SHA is `f0515af01f82d9933f80516978d23b9d7239e44949f01f507cada4b9c567c4af`;
runner SHA is `be17f84e6f53ca028f126dbfeff0afd9af71a7026d54255f837c223db32aa705`.
This is the October2026 V3 default two-scale soft model, not the older rejected
three-source hard V4 pilot. No parameters changed after controls or cost.

MEASURED: all299 jointly attended sources in every tile, all486 partition cores,
31,694,016 output pixels, source hashes/order preserved before and after.
Full job2445.797s (40m45.797s), observed CPU1997.5625s, peak host Job committed
memory20,473,892,864 bytes. Torch peak allocated/reserved memory is
15,420,138,496/16,414,408,704 bytes. RTX5090, Torch2.11.0+cu128, OpenCV4.13.0,
four Torch workers and one OpenCV worker, f32/TF32/autocast-off. The separate
24GiB host and Torch bounds pass; neither is a whole-device memory measurement.
The views job takes3.250s. No process was killed, and both jobs are terminal.

Tile wall sums are1769.842s gathering and595.758s after gathering. The latter
includes model inference, transfers and RGB composition, not isolated GPU
kernel time. Preparation35.442s and final input preservation35.439s are inside
the full job. Repeated context gathering is expensive, but a photographic
rejection does not justify first optimizing it.

The complete [workflow accounting](workflow-accounting-review.md) retains all
native and Helicon component receipts. V3's40.8 minutes excludes the prior
212.156s TIFF-development wrapper and128.266s native alignment, plus its
separate views. Native alignment plus CA-off rendering sums357.798s; shared
development plus Helicon B8/B4/C wrappers sums331.500/329.641/314.343s.
Those are DERIVED sums of separately scheduled stages, not controlled
end-to-end measurements. Cache/load, worker counts, extra exports and geometry
differ. The V3 implementation is not competitively fast in this observation;
its isolated neural-call latency or earlier projection must not replace the
complete measured cost.

## Scope and continuation

This comparator consumes already developed RGB, shares one probability across
RGB values, and has no calibrated native noise admission. It cannot satisfy
original-CFA reconstruction by being fed files that originally came from RAW.
Same placement gauge does not isolate fusion: OpenCV cubic, predevelopment,
per-tile u16 quantization and MHC assumptions remain different from native.
The exact-method conclusion is limited to this complete weevil observation.
Mineral glare, marigold ghosting/occlusion and broader insect robustness remain
unresolved. The overall goal remains active; current main was rechecked at
`4813e46bdc9aaf5f9220115911df5cd5aa3fd808` without a remote delta.
