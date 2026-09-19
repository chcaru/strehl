# Vitamin-C: independent whole-output comparison

**ARGUED photographic verdict:** the retained MIT fork provides a useful counterexample to the baseline's conspicuous chromatic spokes around highlights, but it is not an overall quality winner in these five fixed windows. The baseline has smoother low-detail areas and generally cleaner visible facet boundaries. The fork replaces many coloured spokes with broader, granular white/blue highlight clusters and adds visible grain. Neither output convincingly restores a new fine facet or internal crystal structure that the other lacks.

This verdict comes from all ten 384×384 native PNGs, viewed individually at original resolution. Both complete overviews were inspected for orientation only. No sharpness, gradient, change-count or noise score was used as quality evidence.

## Native observations

| Frozen region | Specific comparison |
| --- | --- |
| `facet-edges` | At the bright cluster about one-third from the left and below centre, the baseline carries cyan/green/magenta streaks extending around the white centre. The fork greatly reduces the long, coloured-spoke appearance, but the white centre becomes a larger coarse, granular patch. A similar tradeoff occurs at the bright cluster on the right edge. The transparent angular body and lower diagonal rim remain identifiable in both. I do not see a newly separated facet in the fork. |
| `pale-background` | The same broad blue field and dark blurred form remain. The fork is visibly grainier across the pale field and inside the dark form. The baseline is smoother. No new resolved structure accompanies that grain. This is not a calibrated flat target and does not measure temporal sensor noise. |
| `fine-crystals` | Both show the same diagonal crystal boundaries and small bright points. Baseline highlight points and the left-hand sloping edge have more conspicuous separated cyan/pink components; fork points are more compact in colour but more granular. Much of the weak internal structure remains soft in both. The additional fork texture does not establish recovered fine crystals. |
| `bright-facet` | Despite its frozen name, this particular crop contains mostly soft background and the edge of a dark polygon at the top. It is therefore useful as another low-detail/edge check, not the strongest highlight test. Fork background grain is greater, while the principal polygon edge remains in both. Small local geometric differences are visible; there is no clear new internal facet structure. |
| `dark-inclusion` | The lower-left bright area beside the black inclusion has an especially conspicuous multicolour flare/spoke pattern in the baseline. The fork reduces much of the long green/cyan fringe, but retains magenta colouring near the inclusion and produces a wider granular white patch. At the right-hand bright point, the same shift from chromatic spokes to a white/blue cluster occurs. The central angular forms remain shared. The fork does not solve highlight structure outright. |

Both images have a strong blue overall rendering. There is no neutral reference here that establishes correct white balance or proves either rendering more accurate. Less colourful highlight fringing is a photographic observation, not proof that all real crystal colours should be neutralized. Likewise, a broader white patch is not recovered highlight detail; no RAW clipping count was inferred from its appearance.

## Exact comparison and correspondence

**VERIFIED preparation command, no RAW decode or render:**

```powershell
python experiments/quality-september19/vitamin-c-external-review-1/prepare.py
```

The regions were taken unchanged from `vitamin-c-review-1/regions.json`, which root froze on the baseline before seeing this comparator. Every recreated baseline PNG is pixel-identical to its frozen counterpart. The fork windows use integer crop origins around corresponding centres; neither arm's diagnostic crops were resampled, rotated, scaled, sharpened or colour-adjusted. RGB16 was displayed through rounded division by 257 in both arms.

A quarter-size SIFT/similarity fit was used **only to assign crop coordinates**. It found 2029 inliers; the median inlier residual was 0.713 native output pixels in the baseline-output→fork-output mapping, with scale 0.999716 and rotation −0.00904°. These values measure correspondence consistency, not placement truth or image quality. A wrong/unrelated image can fail the correspondence, inlier, extent, scale, rotation and residual checks. Remaining local shape differences are deliberately visible instead of being concealed with crop resampling.

| Region | Baseline native x,y | Fork native x,y | Size |
| --- | --- | --- | --- |
| facet-edges | 2500, 2700 | 2518, 2704 | 384×384 |
| pale-background | 400, 1150 | 419, 1155 | 384×384 |
| fine-crystals | 4200, 1700 | 4218, 1704 | 384×384 |
| bright-facet | 1150, 3850 | 1169, 3854 | 384×384 |
| dark-inclusion | 3050, 1850 | 3068, 1854 | 384×384 |

`receipt.json` binds both original output TIFFs, the frozen window file, helper, matrix and crop coordinates. `baseline-orientation.jpg` and `fork-orientation.jpg` show the complete fields with boxes and are explicitly for orientation.

## Complete outputs and decision

The complete images are available at:

- Baseline: `experiments/quality-september19/full-outputs/vitamin-c-baseline.png`, sourced from `vitamin-c-baseline-1/vitamin-c.tiff` (6920×4612 RGB16).
- Fork: `experiments/quality-september19/full-outputs/vitamin-c-fork.png`, sourced from `vitamin-c-fork-40g-1/fork.tiff` (6958×4626 RGB16).

The fork consumes the same 70 captures developed with the actual product decoder/MHC/colour route, but it applies development/tone before its RGB merge and uses its own alignment. Baseline applies colour/tone after CFA merging and corrects lateral CA during gather; the external export has no CA correction. Tone is pinned to the baseline's six-decimal description, not its original full f32 bits. Consequently this comparison identifies a product-level tradeoff and cannot isolate its cause to merge, demosaic, CA, tone or alignment.

**ARGUED next-fix target:** reduce conspicuous coloured highlight spokes while retaining baseline smoothness and continuous facet boundaries. The fork is useful evidence that these long chromatic patterns can be reduced in a complete workflow using the same RAW captures; its granular highlights and background are costs to avoid. Do not substitute gradient strength or neutralized colour for demonstrated retained structure, and do not promote a change from these crops without also presenting its complete output. No additional RAW work was performed for this review.
