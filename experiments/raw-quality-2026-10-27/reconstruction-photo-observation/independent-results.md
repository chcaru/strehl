# Complete flat60: no useful photographic gain

2026-10-27. **VERIFIED visual observation: reject promotion of this unchanged reconstruction.** The complete diagnostic remains very close to the canonical baseline. Across all eight frozen native witnesses, I find no convincing recovered structure, substantial contour cleanup or useful glare improvement. I also find no conspicuous new damage comparable to the earlier direct-pixel candidate's purple inset bands and triangular interiors. Rejection is for insufficient demonstrated benefit, not an invented large regression. No automatic weevil transfer or production promotion follows.

## Complete outputs

Both entire photographs were inspected first through their1617x1078 orientation overviews, followed by every exact384x384 native pair. All use the same held writer tone and ICC; display conversion is `(RGB16+128)//257`. Overviews establish composition, not resolution. The complete images and full-resolution masters remain available even though the candidate is rejected.

| Arm,6932x4620 | Complete JPEG | RGB16 master | FloatRGB master |
| --- | --- | --- | --- |
| Canonical | [Complete](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-views-1/baseline/complete-stack.jpg) | [RGB16](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/baseline-master.tiff) | [RGB32](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/baseline-linear.tiff) |
| Finite reconstruction diagnostic | [Complete](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-views-1/candidate/complete-stack.jpg) | [RGB16](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/candidate-master.tiff) | [RGB32](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/candidate-linear.tiff) |

## Every frozen witness

Coordinates below are delivered-master origins; every rectangle is384x384. No witness was moved, replaced or omitted. All exact PNG/TIFF pairs are bound in the [display receipt](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-views-1/display-receipt.json).

| Witness / origin | Diagnostic versus canonical |
| --- | --- |
| Gray field,1460,400 | Weak vertical step and fine mottling remain essentially unchanged. No visible noise/color improvement or clear new pattern. This is not a calibrated uniform flat. |
| QR boundary,4200,780 | Same blocks, corners and open gaps; broad soft transitions and pale edge shoulders persist. Any edge change is too slight to support a useful cleanup. |
| Central fine bars,2670,2020 | Same larger separated groups and ambiguous smallest groups. No additional defensible bar separation; bright speck/edge artifacts persist. |
| Central micro target,3850,2040 | Same fine groups and radial leader lines, with soft transitions and colored edging. No clear recovery of missing structure or new interior shading. |
| Right bars,5700,1900 | Larger bars/numerals persist; fine center remains soft. No substantial change to the white square's shoulders or surrounding dark field. |
| Upper-right star,5260,20 | Same wedge topology and soft convergence. Existing contour shoulders remain; no convincing added wedge separation or broad color regression. |
| Bottom radial center,1280,4236 | Broad unresolved pale disk and dark central dot remain. No additional center spokes or significant cleanup of outer colored rims. |
| Dot field,4600,3400 | Same circles, soft surrounds and small bright inter-dot speck. No convincing compactness/glint benefit or newly objectionable interior texture. |

## Competitive and source context

After the native pairs I revisited complete B/C/source30 views, B/C QR witnesses, B star/dots, and source30 QR/star/dots/fine bars. The [existing full-workflow comparison](../../raw-quality-2026-10-26/flat-comparator/photographic-review/independent-results.md) still describes the gap: B and source30 show more compact existing QR/dot/wedge boundaries, with stronger red/cyan fringes. C retains broad luminous shoulders. This diagnostic does not visibly close that gap. [Source30 support](../../raw-quality-2026-10-26/flat-comparator/source-support/results.md) still establishes existing contours, not an optical ceiling or extra smallest-bar resolution.

Native reference30 has active origin(50,34); its pair shares geometry, CA and development. Source/vendor full extents are7032x4688 with previously mapped native crops and unmeasured local scale differences. Vendor geometry is independent; source/vendor inputs were developed without CA warp and with tone before fusion. These comparisons therefore do not isolate placement, CA, focus weighting or rendering as the cause of softness. No new registration, source search, crop, retone or metric was performed.

## Execution and scope

Root's recorded command was:

```powershell
outputs/raw-quality-2026-10-27/reconstruction-photo-build-2/cli-tests.exe merge_cmd::reconstruction_restart::photo_observation::flat60_complete_observation --ignored --exact --nocapture --test-threads=1
```

The [process receipt](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/process.json) reports exit0,53.547s and3,574,009,856bytes peak job commitment, four workers/GPU gather, executable SHA`ab776fe4b3b29c8756374f45fb7058e107e0d7723fd8a6c5cdc54bc4d857cdb8`. This is a paired research observation, not a speed benchmark. Source/receipt validation belongs to the independent integration audit; this report's new conclusion is photographic.

All four solves reportedly converge on this flat stack. That does not reverse the historical chip's numerical refusal or the generated focused-glint/far-coarse harms, and it does not establish image quality. The complete photographic observation now answers the previously missing practical question: this fixed coefficient-consistency replacement has no demonstrated useful gain on the current flat60. Preserve the result without parameter rescue or a family-wide rejection.
