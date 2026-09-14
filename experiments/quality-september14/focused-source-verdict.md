# Focused originals located

**VISUALLY OBSERVED:** The focused original for the winding fibre is around frame 39 (`DSC00040.ARW`); frame 41 supplies a nearby comparison. The junction's lower bright edge is focused around frame 41 (`DSC00042.ARW`), with frame 43 nearby. These originals resolve the relevant fine structures and replace the earlier, defocused sparse sample as the useful source comparison.

I inspected all four selected native RGB crops and both raw green phases for the fibre at frame 39 and junction at frames 41 and 43. **No clearly separated or continuous source feature was found that the baseline deletes or doubles.** This is a visual finding limited to two selected regions. It is not evidence that the whole stack is optimal, and the source developer and product tone differ.

The baseline junction's cyan/magenta bright-point fringes appear more pronounced than in the focused LibRaw render. The source already contains coloured point structure, and the development paths differ, so this remains a candidate for a matched-render comparison rather than a proven fusion defect. There is now an actual focused source available for that comparison: `focus-locator-1/frame-41-junction-libraw.png`, with its raw patch and native coordinates retained.

Command run:

```text
python -X faulthandler experiments/quality-september14/focus-locator.py
```

The locator first demonstrated that adding noise to a flat patch raises its score and can outrank blurred structure. Accordingly, the score is **only a frame locator**, never image-quality evidence. Spatial smoothing operated on individual two-dimensional green planes; optional smoothing along frames was explicitly applied to the two resulting scalar curves. No per-pixel frame argmax, sharpness gain, or temporal-noise estimate was used.

The pass covered all 105 originals, reusing the four prior cached patches and decoding the remaining 101. Only two 300×300 native CFA patches per original were retained. The same fixed reference-frame regions and existing reference-to-source map determined integer crop centres; neither source scale nor rotation was corrected in the images. `focus-locator-1/locator.json` records all coordinates and source scales, and `focus-neighbourhoods.png` shows the nominated neighbourhoods. The curve is not a quality result.

**VERIFIED:** The selected patches agree byte for byte with the existing independent rawler decoder, and their re-read rawpy values agree with the locator cache. Source directory file metadata was identical before and after. The owned process tree finished in 45.75 wall seconds and 44.6875 CPU seconds, with 40,148,387 bytes retained when checked; configured bounds were 180 wall seconds, 120 CPU seconds and 64 MiB of output. `focus-locator-1/process.json` and `completion.json` record these checks. No further source reads are needed to locate these two features.
