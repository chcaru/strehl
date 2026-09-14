# Checker original comparison

**VISUALLY OBSERVED:** Coloured checker-edge fringes are already present in the original before stacking. The reference LibRaw render has cyan/blue edges in one direction and magenta edges on the opposite side. They appear stronger than in the baseline. This comparison does not isolate an optical cause or quantify the effect of stacking, because demosaic, chromatic-aberration treatment and tone differ between the developers.

**No missing recoverable edge feature was established.** Reference frame 75 (`DSC00076.ARW`) resolves the checker pattern. The baseline preserves the same separated squares, connected corners and continuous diagonals in all three inspected crops. Faint marks inside the middle crop's dark squares also occur in the source, including the small scratch-like marks; their presence is not evidence that stacking invented texture.

I inspected the baseline overview for orientation, all three native 384×384 checker crops and the white control, then their matching native LibRaw source crops. Both raw green phases were inspected for the middle and edge regions, and one phase of the white control. Each source RGB display pixel corresponds to one native image pixel; each raw green display pixel corresponds to one original same-colour sample at native pitch two. Neither comparison was spatially resampled. Source brightness and colour were not fitted to the baseline.

Command run:

```text
python -X faulthandler experiments/quality-september14/checker-source-review.py
```

**VERIFIED:** The source was only `D:/personal/macro/requests/misc-diagnostic/tiny-high-res-calibration-checker-slide-cpl/DSC00076.ARW`. rawpy/LibRaw and the existing independent rawler helper agreed byte for byte over the union containing all four patches. The rawpy data was copied before its owner closed. The source size and modification time were unchanged. Native output offset `(10,8)` and the reference map were checked; the solved reference differs from exact identity only by a negligible floating-point residual, recorded in the receipt.

An initial exact-identity assertion stopped before any RAW decode. Its log is retained. The corrected guard checks the maximum native displacement instead of bitwise identity; the successful child used 3.109375 CPU seconds and 3.172 wall seconds. All retained files totalled 11,881,529 bytes when checked, below the 64 MiB limit. `checker-source-review-1/receipt.json` and `process-retry-1.json` record the successful run. Source linear RGB crops were retained for a later matched-render comparison without another RAW read.

No sharpness-quality metric, frame search or causal model was introduced. The white patch was a visual control, not a temporal-noise measurement. This inspection supports a source-dependent fringe and offers no evidence of gross edge-detail loss from stacking in these three crops.
