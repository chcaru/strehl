# Complete weevil Helicon comparison: useful local differences, no clean SOTA target

2026-10-26. **VERIFIED by independent visual inspection:** Helicon B is broadly close to the native baseline on the rounded scale texture, with cleaner separation of some upper-leg hairs. It is not uniformly better: conspicuous soft cyan/blue fringes remain at the blue joint and occlusion contour. Helicon C adds substantially broader bright cyan/white spill around glints and edges, plus colored traces in the dark background. Its stronger contrast is not a clean quality gain. Neither configured result demonstrates a general cure for the user's softness/halo complaints.

The three complete compositions were inspected before the native comparisons. Then the existing384-square commissioning pattern and all ten frozen subject sites were viewed individually in native, B and C. The vertical/horizontal one-pixel stripes, diagonal and checker pattern were distinguishable. No crop was moved after seeing a local outcome. No RAW decode, merge, reconstruction or source-neighborhood re-analysis was performed by this reviewer.

## Complete outputs and masters

These are complete299-source workflow outputs, not native algorithm improvements. Root separately reconciled B's598 forward/reverse processing rows and C's299 ascending rows with the299 intended source names and settings. This review did not independently repeat that log census. B uses method1/radius8/smoothing4; C uses method2/smoothing4. The retained invocation and application logs remain the operational authority.

| Arm | Complete image | Full-resolution RGB16 master | Dimensions |
| --- | --- | --- | --- |
| Native baseline | [Full JPEG](../../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/stack-full.jpg) | [Master](../../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/stack-master.tiff) | 6896×4596 |
| Helicon B | [Full JPEG](../../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/b/stack-full.jpg) | [Master](../../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/b/stack-master.tiff) | 7020×4676 |
| Helicon C | [Full JPEG](../../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/c/stack-full.jpg) | [Master](../../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/c/stack-master.tiff) | 7020×4676 |

The tool displayed the whole native image at1920×1280 and B/C at1921×1280. Those views establish complete composition and conspicuous broad differences, not native sharpness. No watermark or missing large region was visible in these complete views or the thirty native witness images; this is not an exhaustive every-pixel watermark certification. An attempted combined full-resolution image call exceeded the IPC frame limit and returned no usable images; only the subsequent successful individual views are credited.

Independently rehashed masters: native `ecfae13e937f44445f3fe2a83a2e72861c4cd6cd9f56f02139f3f5e3dc0f9665`; B `56e6f5be1c98f7670b81dfe458d734d0bd782e0bc2a801bb7cd1dcf30a89165a`; C `cadccec36051a9ade00800b8e8d2b9caf186e50846329dab787f566d8dbb2a45`. All use ICC SHA256 `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`.

## Correspondence and display limits

The native gauge is reference149 with delivered reference-native offset `(68,46)`. Helicon's reference/internal geometry is not assumed to be that gauge. A bounded SIFT/similarity locator mapped subject centers from native to each vendor output; a local median of existing inlier offsets refined a center only where at least three nearby matched features existed. Background has no reliable local landmark and uses only the global locator. This does not fit or change a reconstruction map.

**MEASURED locator only:** B scale1.01902450, rotation0.005862degrees, translation `(-11.51669,-17.05644)` native pixels; C scale1.02012943, rotation0.003574degrees, translation `(-15.38056,-19.52750)`. Median/P95 inlier discrepancies are1.264/3.279pixels for B and2.145/4.349pixels for C. A deliberate100pixel shift in both axes yields median error above141pixels in each arm, exercising the rejection control. These are locator diagnostics, not alignment-quality or image-quality scores.

No vendor pixels were resampled. Every delivered crop is an original384×384 subarray, with an exact RGB16 TIFF and a PNG computed only by `(value+128)//257`, retaining the master ICC. Reopening verified every TIFF/PNG against the corresponding master subarray. The vendor crop therefore covers approximately1.9–2.0% less physical width than the native crop; residual geometry and depth effects remain. Fine differences are described conservatively; no equal-footprint resolution ranking or pixelwise aggregate score is asserted. [Correspondence receipt](correspondence.json) binds matrices, inliers, all origins, hashes and exact-pixel checks.

All origins below are native output pixels and all extents are384×384. The visible diagonal strand, curved rim, scale clusters, leg-hair arrangement and cavity boundaries were checked to confirm corresponding subject content in the displayed triples.

| Frozen witness | Native origin | B origin | C origin | Independent visible finding |
| --- | --- | --- | --- | --- |
| background-black | 3800,500 | 3864,497 | 3865,495 | Native and B are nearly black with very faint speckle. C contains conspicuous fine colored diagonal traces and green angular/polygonal traces. The traces are present in exact TIFF pixels, not JPEG ringing or a resized viewer. Their physical/source cause is not identified here. |
| dark-elytron | 2750,2120 | 2795,2147 | 2795,2147 | B retains the same dark material texture and adjacent scale clusters, with slightly more distinct fine texture. C has a brighter/grainier dark field and much broader cyan glow at bright points. No new true structure is established. |
| turquoise-scales | 2120,1340 | 2152,1353 | 2152,1353 | B remains close to native: the same rounded cyan/green clusters and dark gaps are identifiable; this is not a substantial recovery of scale boundaries. C adds brighter cyan spill and spreads glints into neighboring material. |
| elytron-seam | 2950,1960 | 2998,1984 | 2998,1984 | The pale diagonal strand remains continuous in all three, with similar broad/colored outline. B is close to native. C adds halos around nearby glints and brightens the strand surroundings; stronger contrast does not establish better continuity. |
| bright-wing-rim | 4050,1810 | 4118,1831 | 4118,1831 | Native/B retain nearly the same curved pale rim and soft cyan edge; B does not clearly resolve it. C brightens/spreads multiple glints and gives the rim a stronger luminous surround. |
| thorax-texture | 4520,2560 | 4597,2595 | 4597,2595 | B makes some small bead-like boundaries and dark gaps a little more distinct, but the general rounded structure is shared. C's much larger bright halos fill surrounding gaps at several glints; no additional countable scale structure is demonstrated. |
| upper-leg-hairs | 1820,640 | 1846,638 | 1844,637 | B more clearly separates several lower hair tips and retains the thin upper hairs; this is the most useful local comparator target. Native has a softer colored surround. C preserves much of the hair layout but adds diffuse bright haze around the body and hairs. Color fringes remain, and source truth is not supplied by this comparison. |
| blue-joint | 2680,850 | 2722,853 | 2722,853 | B shows fairly distinct blue surface texture but a conspicuous soft blue plume along the upper-right boundary; it is not a clean halo correction. C retains this and produces stronger bright/yellow-green spill near the lower joint. Native's boundary is also imperfect. |
| upper-occlusion | 3850,1300 | 3914,1312 | 3915,1311 | B keeps the small blue texture but retains/strengthens the lower cyan/green fringe. C has a larger green highlight bloom and additional faint streaks in the dark upper-left cavity. Whether every faint streak has a real source counterpart is unverified. |
| eye-and-antenna | 5350,2920 | 5445,2963 | 5447,2964 | The same dark elongated gap, upper fine strands and surrounding surfaces remain. B is close to native, with somewhat broader gap specks. C adds broad luminous edge haze and larger colored specks. This historical label does not establish an anatomical eye. |

Native witness PNGs remain in [the frozen review](../../photo-review/baseline-review.md). Corresponding vendor PNG/TIFF pairs are in [B](b/) and [C](c/); filenames are the unchanged witness names above.

## Interpretation and next useful hypothesis

**ARGUED:** the useful target is B's local hair separation while retaining native's more restrained glint rendering, not C's apparent punch. Because B and native share many rounded scale forms, this comparison alone does not establish a large native-only scale-detail loss that a different merger would recover. It also cannot establish a source-information ceiling: both workflows share this exporter's MHC development, and these settings do not exhaust Helicon's possible quality or other RAW development choices.

The workflows differ in pre-merge versus post-merge tone, CA treatment, internal placement, crop and merge. Similar input colors and exact shared ICC do not remove those causal confounds. A halo or sharper hair in B cannot be assigned to one algorithm component from these images. The separate actual source149/gather/stack mechanism review is therefore the right next discriminator. This reviewer did not duplicate its source inspections. There is no evidence here supporting a fresh high-frequency boost, a generic inverse retry or a claim that more sparkle equals more detail.

C's background traces and glint spreading are concrete regression witnesses for any future native candidate: apparent local contrast can improve while the full image gains contamination. Keep the complete output and all ten fixed witnesses in the next comparison. No overall numerical ranking, default change, SOTA claim or native photographic improvement follows from this review.

## Executed commands and accounting

`python -X faulthandler experiments/raw-quality-2026-10-26/comparator/photo-review/export-corresponding.py` exited0 and completed its own locator/export work in2.5seconds, with OpenCV4.13.0 restricted to two threads. It reads only the three completed TIFFs and frozen manifest, then writes owned review artifacts. This operational observation is not stack speed. The script and [receipt](correspondence.json) retain exact settings and artifacts; no parameter search or prolonged image registration occurred. Individual `view_image(detail="original")` calls inspected all thirty384-square images and the commissioning image; successful whole-image calls used `detail="high"`. No image quality metric was computed.
