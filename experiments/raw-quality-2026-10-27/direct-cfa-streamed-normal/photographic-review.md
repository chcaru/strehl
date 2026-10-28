# Complete direct-CFA weevil photographic review

2026-10-27. **VERIFIED visual result: catastrophic photographic failure; reject this finite result. No improvement is demonstrated.** Large green, cyan, purple and black rectangles replace the insect's contours, scales, hair shafts and shading. The failure is obvious in the complete photograph and occurs in every frozen witness. Native CA-off and Helicon B4 retain recognizable material, fine features and color throughout; this candidate is substantially worse than both.

The [prospective priorities](pending-review-priorities.md) were frozen before the candidate existed. Better edge shape or tonal fidelity could have counted without new topology. This result fails that permissive standard: previously visible structures and tonal transitions are absent from the delivered image, rather than merely failing to reveal additional detail.

## Complete result and references

I opened the complete candidate first, then the complete native CA-off and B4 references, followed by all ten unchanged 384x384 candidate/native/B4 triplets, with background first. No new crop, retone, reconstruction or numerical experiment was run. Whole images shown fitted to a page are orientation views; the native witnesses confirm that the block pattern is also present at native resolution.

![Complete direct original-CFA reconstruction, rejected](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-views-2/output/complete-stack.jpg)

![Previous complete native CA-off photograph](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-full.jpg)

| Workflow | Complete photograph | Full-resolution master |
| --- | --- | --- |
| Direct original-CFA finite result, 6896x4596 | [JPEG](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-views-2/output/complete-stack.jpg) | [RGB16 TIFF](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/output/native/rgb16-master.tiff) |
| Native CA-off, 6896x4596 | [JPEG](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-full.jpg) | [RGB16 TIFF](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-master.tiff) |
| Helicon B4/S4, 7020x4676 | [JPEG](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-full.jpg) | [RGB16 TIFF](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-master.tiff) |

The [view index](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-views-2/output/index.md) links all thirty native-size crops. The [signed camera-DN master](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/output/delivery/camera-rgb-dn.f32le) and latent remain available for separate diagnosis; they were not transformed or analyzed in this visual review.

## All ten fixed witnesses

Each origin is in the delivered native reference149 image. All rectangles remain 384x384. B4 uses its previously recorded corresponding origin and its own scale, without resampling.

| Witness; native origin | Candidate finding against both references |
| --- | --- |
| Background-black; 3800,500 | Green background pedestal, large rectangular boundaries and bright horizontal/vertical lines replace the nearly black reference field. This is not quieter background rendering. |
| Dark-elytron; 2750,2120 | Dark ridges, fine surface texture and nearby scales are replaced by broad black/cyan blocks. |
| Turquoise-scales; 2120,1340 | Individual rounded scales, gaps and compact glints are absent; broad cyan/green columns with colored seams remain. |
| Elytron-seam; 2950,1960 | The diagonal continuous strand and adjoining material disappear into vertical rectangles and black regions. Multidepth structure is not preserved. |
| Bright-wing-rim; 4050,1810 | The curved rim, glints and textured surface are replaced by square green/black fields. Apparent removal of the pale contour cannot count as halo cleanup when the surface itself is lost. |
| Thorax-texture; 4520,2560 | Rounded scales and winding dark gaps disappear into a nearly featureless dark field with a rectangular step. |
| Upper-leg-hairs; 1820,640 | Hair shafts, the limb boundary and surface texture disappear; broad horizontal green bands remain. No improvement in continuity or separation. |
| Blue-joint; 2680,850 | Blue material, local surface marks and the curved junction are replaced by green/cyan/black rectangles. Independent color and shading are not retained. |
| Upper-occlusion; 3850,1300 | Raised blue surface, dark cavity and overlap contour cannot be followed; rectilinear blocks and colored seams dominate. |
| Eye-and-antenna; 5350,2920 | Fine strands and the elongated dark gap's textured surround disappear into black, green and purple blocks. The historical label does not certify anatomy. |

There is no favorable tradeoff to balance here. Glints are largely absent together with genuine surrounding structure; that is not glare reduction. The milder prior V3 haze/softness/background tradeoffs do not alter this rejection.

## Provenance, numerical status and next decision

**VERIFIED from saved receipts:** the [full receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/output/receipt.json) records all 299 sources consumed and a complete 6896x4596 image at reference-native origin (68,46). The [views2 receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-views-2/output/receipt.json) records exact RGB16 readback, original ICC, all ten exact unresized crops and unchanged bindings. Display is the existing native RGB16 rounded by `(value+128)//257`, without retone. Master SHA256: `6620ab28b2ab78a9f9db84ff89fa67ea8f28c0a27a378f595f212d4bdd0506af`. Thus the block pattern is not merely an overview-scaling impression. This review does not independently locate its first producing stage.

The [fit receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/output/fit/result.json) retains `refused-iteration-cap`, 64 iterations, and restored full/projected normal ratio **0.08320654183626175** against **1e-5**. That numerical refusal and the prior generated flat/noise failure remain separate evidence; neither proves the visual failure's mechanism. No extra iterations, changed tolerances or rerun are justified by this review.

**MEASURED operational run:** [actual command/process record](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/process.json) reports clean exit0 in 6517.141 seconds, peak host job commitment 10,279,055,360 bytes; the full receipt reports peak CUDA allocation 5,437,533,696 bytes and reservation 6,664,749,056 bytes. This is the saved-CFA reconstruction/delivery job, excluding the earlier RAW export and alignment, not a competitive complete-workflow speed ranking. Cache bytes/metadata and original RAW metadata were unchanged; original byte identity comes from the verified export, not a fresh RAW byte rehash by this worker.

**ARGUED next dominant failure:** establish why this producing path delivers blockwise color fields instead of continuous scene structure before another complete solve. The immediate problem is wholesale structural/color failure, not a narrow halo, hair-width or contrast deficit. A bounded causal check of retained stages is appropriate if separately allocated; the appearance alone cannot choose among representation, weighting, solve, restoration or delivery causes. Do not resume an iteration campaign or promote this recipe. This negative result does not reject all direct original-CFA reconstruction approaches.

Helicon's roughly 1.02 scale and premerge development, and the native baseline's legacy MHC/remosaic consumer, remain comparison differences. They preclude isolated solver/alignment attribution but cannot plausibly explain the candidate's wholesale loss of recognizable material. No claim extends to marigold, minerals or other insects, and the user's quality goal remains unresolved.
