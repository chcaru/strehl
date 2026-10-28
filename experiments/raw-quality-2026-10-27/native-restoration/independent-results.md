# Complete native restoration: moderate acutance, mixed fidelity

**VERIFIED visual observation:** the fixed bounded restoration makes existing weevil scales/hairs and chart boundaries visibly firmer. This is a real moderate acutance result across the complete images. It also makes insect texture more coarse and angular and glints harder. Soft hair remnants, pale occlusion rims and unresolved fine chart structures remain. No newly resolved structure is demonstrated. **ARGUED decision: retain the diagnostic, but do not promote this recipe as the general default or as a solution to the corpus's core defects.**

Both complete images for each stack were viewed first, followed by all ten weevil and eight flat frozen384px pairs. Overviews establish composition only. Native crops use identical held development, ICC and `(RGB16+128)//257`, without retone or resampling. No new crop, source decode, metric or optimization was run. Root independently reviewed both complete pairs and all18 witnesses.

## Complete outputs

| Stack/arm | Complete JPEG | Full-resolution RGB16 | Linear master |
| --- | --- | --- | --- |
| Weevil baseline,6896x4596 | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1/baseline/complete-stack.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-1/output/baseline-master.tiff) | [Float TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-1/output/baseline-linear.tiff) |
| Weevil restored,6896x4596 | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1/candidate/complete-stack.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-1/output/candidate-master.tiff) | [Float TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-1/output/candidate-linear.tiff) |
| Flat baseline,6932x4620 | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-views-1/baseline/complete-stack.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-1/output/baseline-master.tiff) | [Float TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-1/output/baseline-linear.tiff) |
| Flat restored,6932x4620 | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-views-1/candidate/complete-stack.jpg) | [TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-1/output/candidate-master.tiff) | [Float TIFF](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-1/output/candidate-linear.tiff) |

![Complete weevil baseline](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1/baseline/overview.jpg)
![Complete weevil restored](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1/candidate/overview.jpg)
![Complete flat baseline](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-views-1/baseline/overview.jpg)
![Complete flat restored](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-views-1/candidate/overview.jpg)

## All frozen witnesses

Coordinates below are top-left native pixels; every rectangle is384x384. Complete crop bindings and lossless TIFF siblings are in the [weevil receipt](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1/display-receipt.json) and [flat receipt](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-views-1/display-receipt.json).

| Weevil witness | Origin | Baseline → restored |
| --- | --- | --- |
| Background black |3800,500 | Similar at held display; no conspicuous new trace. Not a noise measurement. |
| Dark elytron |2750,2120 | Stronger coarse stippling and harder bright scales; no additional structure established. |
| Turquoise scales |2120,1340 | Existing contours clearer, but more angular/beaded; glints harder. |
| Elytron seam |2950,1960 | Same seam, now more jagged and contrasted; no seam cleanup. |
| Bright wing rim |4050,1810 | Firmer scales; continuous pale lower contour remains. |
| Thorax texture |4520,2560 | Rounded soft points become harder dots and gaps; no new puncture topology established. |
| Upper-leg hairs |1820,640 | Existing strands are more conspicuous; soft tips and doubled remnants persist. |
| Blue joint |2680,850 | Harder angular surface marks and chalky flecks; junction remains soft. |
| Upper occlusion |3850,1300 | Blue texture firmer; pale/green rim and nearby glints remain conspicuous. |
| Eye/antenna |5350,2920 | Existing bright fibrous detail stronger; no missing depth structure recovered. |

Amplified stippling cannot be classified as invented texture or sensor noise from this pair alone. Whole-image hue is broadly similar; this is not a calibrated color-fidelity result. No gross new extended halo was established, but the existing rims are not repaired.

| Flat witness | Origin | Baseline → restored |
| --- | --- | --- |
| Gray weak step |1460,400 | Step and fine texture remain; no major visible change. |
| QR boundary |4200,780 | Existing edges/corners clearly firmer; soft shoulders remain. |
| Central fine bars |2670,2020 | Larger bars/numerals clearer; smallest groups remain ambiguous. |
| Micro target |3850,2040 | Leaders and existing groups firmer, without established extra separation. |
| Right bars |5700,1900 | Firmer bars/square; mild color edging persists. |
| Upper-right star |5260,20 | Wedges clearer, same convergence; small jagged edge details emphasized. |
| Bottom radial center |1280,4236 | Outer spokes firmer; unresolved pale center and color fringes persist. |
| Dots |4600,3400 | Existing boundaries more compact; no extra dot or surface detail established. |

## Competition, harms and limits

Revisited complete weevil B8/B4 and flat B/C, plus retained native B4 hair/scales and B dot/star correspondences. The restoration moves native toward B's firm-edge appearance without demonstrating a decisive full-workflow win. Flat native retains much weaker red/cyan fringes than B, while C's broad luminous shoulders remain undesirable. The [weevil comparison](../weevil-fine-comparator/photo-review/independent-results.md) and [flat comparison](../../raw-quality-2026-10-26/flat-comparator/photographic-review/independent-results.md) retain all competitive masters and mappings. Vendor geometry/physical scale differs; vendor inputs are developed before fusion, native afterward, with different CA preparation. This is not an isolated merger ranking. No new source-retention or optical-ceiling claim is made.

[Generated visual harms](generated-visual-review.md) remain: seven quality failures, including colored-noise amplification, glint error and fine-component overcontrast. Their photographs are not silently qualified by mechanical success. The [independent receipt audit](independent-photo-receipt-review.md) records exact commands/build identity, no-op parity, unchanged inputs and fixed development. Replay times4.547s/4.640s with four workers cover saved-CFA correction and writing only, not full299/60-source stacking. Both outputs retain `admission=false` and `quality_claim=false`; the observed acutance gain does not resolve ghosting, glare, softness or occlusion across the corpus.
