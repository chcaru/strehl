# Complete vitamin-C pair: independent photographic review

**ARGUED verdict: photographic null for the intended highlight-colour improvement.** The candidate retains the baseline's smooth backgrounds and principal facet boundaries, but does not convincingly recover a new facet, inclusion, or internal crystal structure in the five frozen windows. The conspicuous coloured highlight fans remain. One bright cluster looks slightly more comb-like in the candidate, so this review does not support promotion as an image-quality improvement.

I inspected all ten native 384×384 baseline/candidate PNGs and both complete overviews. I also rechecked the external fork's `facet-edges`, `pale-background` and `dark-inclusion` native crops to distinguish that workflow's tradeoff. No changed-pixel count, gradient score, or bright-white area was used as quality evidence.

| Frozen window | Concrete observation |
| --- | --- |
| `facet-edges` | The transparent angular body and lower diagonal rim remain similarly resolved. At the white cluster left of centre, the candidate still has strong cyan/green/pink spokes; their leftward tips look slightly more extended and comb-like. The right-edge cluster also retains coloured streaks. There is no convincing new separated facet or cleaner highlight boundary. |
| `pale-background` | The broad pale field and dark blurred form remain smooth. Small texture differences do not reveal structure or establish a meaningful improvement. There is no conspicuous increase resembling the external fork's grain. |
| `fine-crystals` | The same diagonal boundaries and weak internal features remain. Bright points near the upper centre retain separated colour components; slightly different white centres are not recovered detail. No additional crystal boundary becomes convincingly resolved. |
| `bright-facet` | The mostly soft background and upper dark polygon retain essentially the same appearance. I do not see a new internal feature, a clearly sharper edge, or a material background regression. This frozen window is chiefly a background/edge check despite its name. |
| `dark-inclusion` | The lower-left inclusion still sits beside a broad, conspicuously coloured highlight fan. The right-hand bright point still carries coloured radial lines. Their character is much closer to the paired baseline than to the fork's granular white clusters. Central angular crystal forms remain similarly legible. |

The complete overviews preserve the same overall composition and blue rendering; they do not establish fine-detail equivalence. There is no neutral reference supporting a colour-accuracy claim. The small localized increase in comb-like highlight appearance is a visual concern, not a proven universal regression. I found no clear structural benefit to offset it in these frozen views.

## Relationship to the external fork

The external fork reduced the long-spoke appearance at several bright clusters, while adding visibly granular background texture and broader coarse highlights. This candidate retains the baseline's smoother background, but **does not obtain that visible reduction in long coloured spokes**. Neither larger/brighter white areas nor reduced colour alone would count as preserved highlight structure. The external comparison remains a complete-workflow comparison with differing alignment, CA treatment and development ordering; it does not isolate the cause of these differences.

## Bound images and scope

**VERIFIED view preparation:** root ran `python experiments/phase-packed-rgb/photo-compare.py`. `coordinate-receipt.json` binds the TIFFs, exact crop translation, helper and frozen windows. Both images are 6920×4612; initial and effective crop are `[28,19,3460,2306]` in quads, so the native translation is exactly `[0,0]`. Diagnostic crops contain the original samples with rounded RGB16→RGB8 division by 257, without resampling, sharpening or a new tone adjustment. Whole PNGs preserve full extent and ICC.

- Complete baseline: [baseline.png](/C:/dev/blog/death-of-software/projects/strehl/experiments/phase-packed-rgb/full-1/photo-comparison-1/baseline.png), TIFF SHA256 `c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21`.
- Complete candidate: [candidate.png](/C:/dev/blog/death-of-software/projects/strehl/experiments/phase-packed-rgb/full-1/photo-comparison-1/candidate.png), TIFF SHA256 `7e1801d7009bf014e49be84e2f8084d729317cd1c0bf5390ed666536c372e62c`.

The pair's implementation/control results are reported separately. Functional correctness does not supply the missing photographic benefit. Retain this result as a bounded negative finding for this candidate and capture; it neither establishes an acquisition limit nor rules out other colour-preserving reconstruction or fusion methods. No RAW decode, render or parameter search was performed during this review.
