# Complete SR15 photographic review

**MEASURED / independently inspected.** The complete SR15 output is coherent and the reviewed native crops show no new obvious holes, seams, or broad color change. This review does **not** establish a recognizable-detail or photographic-noise improvement. Only149,759 of32,007,360 RGB pixels (0.468%) reconstruct; most frozen witnesses remain exact native fallback. The reconstruction outcome remains a limited supported replacement, not demonstrated whole-image super-resolution.

## Fixed comparison and complete readback

The reference is `outputs/multi-stack/completion/sr-chart-native-14c`, previously verified byte-identical to HDR precision03. Candidate is `sr-chart-full-15`. Both have6928×4620 pixels and quad canvas `[26,17,3464,2310]`; saved warp maps and original-source identities agree exactly. Root's complete-file mechanics receipt, `outputs/multi-stack/completion/sr-chart-full-readback-15.json`, passes finite pixels, bound maps/tiles, coherent support counts and **every photograph/master pixel bit outside support exactly native**.149,636 master pixels actually change. This mechanical result does not certify their quality.

The [frozen review selection](sr-full-review-frozen.json) reuses the original twelve HDR384 witnesses and physical display: black0, white4, contrast0.55, exposure gain1. No histogram, alignment, crop, display, or contrast was fitted to the candidate. The earlier chart192 dot ROI at full-sensor `[4105,3245]` has the exact same saved warp gauge and maps by integer canvas subtraction to native `[4053,3211]`. Its earlier ROI-specific display was not reused: all full-output comparisons use the fixed HDR transform.

Both complete images were opened individually. The tool displayed the full6928×4620 images resized to1919×1279 for orientation; they are not native-detail evidence. All thirteen native pair boards were inspected without resampling:384×384 images pasted into792×416 boards, plus192×192 into408×224. The existing384 viewer commissioning image was reopened: single-pixel stripes/checker and colored edge/column markers are distinguishable. Saved PNG readback equals the encoded native slice.

## Every frozen witness retained

| Witness | Native origin | Side | Reconstructed pixels | Observation |
| --- | --- | --- | --- | --- |
| Gray ramp middle |957,416|384|0|Inherited soft gray field/dust; exact fallback.|
| Adverse flare p12 |4157,1565|384|0|Inherited border/flare witness unchanged.|
| QR white/black grid |3957,415|384|60|No new corner detail established; tiny changed support.|
| QR corner boundary |4657,1165|384|0|Inherited edge softness/color unchanged.|
| Large radial star |5857,615|384|0|Exact fallback, no reconstruction-resolution evidence.|
| Fine resolution bars |5157,1815|384|6|No newly separated bars observed.|
| Bright dot field |558,2015|384|1,115|Dot contours/color fringes broadly unchanged; no clear gain.|
| Low-contrast dot field |3957,3115|384|4,726|Faint dots and background remain coherent; no clear additional structure.|
| Lower radial spokes |1257,4115|384|0|Inherited colored edges unchanged.|
| Clipped core |44,894|384|0|No new reconstruction-based highlight recovery.|
| Blue clipped core |556,894|384|0|No new reconstruction-based highlight recovery.|
| Clipped boundary |1580,830|384|0|Inherited broad intensity transition unchanged.|
| Prior physical dot ROI |4053,3211|192|1,922|No purple pits or obvious replacement seam; no recognizable detail gain established.|

Eight of the twelve HDR witnesses have zero reconstructed pixels. Unchanged appearance there demonstrates fallback preservation only. A lack of visible change at these locations cannot validate the supported estimator or exclude artifacts elsewhere.

## Supplemental support-boundary witnesses

The frozen protocol allowed two mask-only diagnostics: the first raster-order horizontal support transition, centered/clamped into384; and maximal `min(supported,unsupported)` on a384 window sampled at stride192, ties in raster order. Selection read only the support map, never photograph differences. The selected origins are `[5248,0]` with589 supported pixels and `[2688,1920]` with6,641. Both native pairs and their masks were inspected. The first contains a small star center; the second contains fine bars/digits. Neither shows an obvious hole/seam or a confidently recognizable extra resolved feature. These are diagnostic supplements, not replacements for the thirteen frozen witnesses.

## Commands, evidence, and claim boundary

The full producer command and exact executable identity are retained in `outputs/multi-stack/completion/sr-chart-full-run-15/receipt.json`: product15 CLI SHA`2db1cea7daf3019185959719c15461c32a80c4535942c9913833ce7323ca69fb`,16 workers,48GiB limit, precision weights, contribution maps, saved native14c alignment, and original-CFA reconstruction. It completed in1078.010s with11,736,682,496 sampled private bytes. Other owned work ran concurrently; this is a completion/resource receipt, not a comparative benchmark.

[Preparation helper](prepare-full-sr-review.py) wrote displays under `outputs/multi-stack/completion/independent-photographs/sr-native14c` and `sr-full15`; exact commands are in `sr-independent-native-display-15/receipt.json` and `sr-independent-display-15/receipt.json`. The helper requires the complete mechanics receipt and rechecks source hashes before candidate rendering. [Boundary helper](prepare-sr-boundary-diagnostics.py) and `sr-boundary-display-15/receipt.json` retain the supplemental selection and execution. The native boards' `layout.json` records each source digest and paste origin.

**VERIFIED:** full files complete, exact fallback, fixed-transform full-scene/native review, no conspicuous reviewed artifact. **UNVERIFIED:** improved recognizable detail, full-scene photographic noise reduction, or a measured resolution increase. Prior held-original-sensel prediction controls remain separate conditional evidence; they do not turn this sparse visual result into a photographic improvement. The intended SR benefit remains open.

## Complete14c baseline follow-up

After root completed and validated14c, I opened its complete6928×4620 fixed-display image and all thirteen frozen native pair boards against the same native14c reference. Preparation used the unchanged helper and freeze; command receipt is `sr-independent-display-14c`, mechanics receipt `sr-chart-full-readback-14c.json`, images `independent-photographs/sr-full14c`. Full viewing was again resized1919×1279 for orientation;384/192 crop boards were unresampled. No new location or display parameter was selected.

The result has150455 supported pixels and exact native fallback per the complete readback. The frozen support counts match15 except bright-dot-field1116 versus1115; the prior192 ROI remains1922. I see the same coherent full scene and no new obvious hole/seam in these witnesses, but no established recognizable-detail advantage over native. These observations do not establish all-image14c/15 numeric equality; the root retains their source/geometry/pull comparison separately. The optical/photographic improvement conclusion remains unresolved for both builds.
