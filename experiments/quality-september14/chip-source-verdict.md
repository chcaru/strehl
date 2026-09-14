# IC original comparison

**VISUALLY OBSERVED:** The pale-circuit crop supplies a useful focused source and a concrete rendering difference to isolate. The original's LibRaw rendering has cleaner, more continuous blue parallel rails and crossbars. The baseline has more conspicuous cyan/magenta dotted edges and rougher outlines along those same structures. This is not yet a fusion diagnosis: demosaic, colour treatment and tone differ between the two developers. A matched-render comparison can now use the retained original patch without another RAW read.

| Region | Original-versus-baseline finding |
| --- | --- |
| Fine-grid | Reference 149 is strongly defocused. It records the larger grid, but cannot adjudicate the baseline's small repeating diagonal detail or prove missing recoverable separation. |
| Colour-edge | The source is strongly defocused here too. Broad coloured structures are already present in the capture; this region cannot support treating all colour variation as an artifact. |
| Dark-flat | Fine repeating diagonal structure is visible in both original green phases and in the source RGB. This is not a featureless or noise-only control. Its structure is recorded before fusion; this check does not distinguish optical scene detail from sampling effects at every fine frequency. |
| Pale-circuit | The source resolves the parallel rails, crossings and small surface marks. The baseline retains the major structures but looks rougher and more colour-speckled along their edges. No specific completely deleted rail or lost connection is established from the differing developers. |

I inspected the overview only for orientation, then all four baseline crops and matching source RGB crops at native 1:1 display, plus both original green phases for all four regions. The source is `D:/personal/macro/requests/misc-diagnostic/uncapped-IC-chip-cpl/DSC00150.ARW`, zero-based frame 149. Its negligible reference-map residual was checked, and native output origin `(266,178)` was added to every supplied crop origin. Source images were neither warped nor resampled. Raw green displays use one output pixel per same-colour sample at native pitch two.

Command run:

```text
python -X faulthandler experiments/quality-september14/chip-source-review.py
```

**VERIFIED:** rawpy/LibRaw and the existing independent rawler helper agreed byte for byte over the union containing all four regions. The rawpy buffer was copied inside its owning context. The original's size and modification time were unchanged. The one-file check used 3.078125 CPU seconds and 3.187 wall seconds; retained output totalled 21,730,370 bytes when checked, below the 64 MiB limit. `chip-source-review-1/receipt.json` and `process.json` record the checks.

The source colour views use fixed gain 1.050 and gamma 1/2.2; the baseline retains its own product tone. Linear source RGB crops and the original CFA union are retained. No sharpness-quality score or full-stack source locator was run. In particular, no achromatic-colour-suppression assumption is justified by this substantially coloured subject.
