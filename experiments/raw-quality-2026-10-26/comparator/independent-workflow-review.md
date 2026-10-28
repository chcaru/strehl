# Independent review of the complete weevil comparator workflow

**VERIFIED — source/configuration review only.** Export preparation is suitable
for a bounded complete-workflow comparison. This is not a photographic pass,
not an isolated merger experiment and not evidence that the configured Helicon
arms exhaust its achievable quality. The reviewer did not launch the export or
Helicon and did not alter their frozen sources.

Reviewed identities:

| File | SHA256 |
| --- | --- |
| `crates/strehl-cli/examples/weevil-batch-develop.rs` | `36048da273521fe8ef9f1c3ee70ac9b2a443a8c36cdd2b1b1487b0f83485968d` |
| `run-weevil.py` | `588e8ff449fcce0200c9da069e8f26e757195d5901071512e204e28f1b6169c9` |
| `weevil-export-config.json` | `78abddc81bf0b76f11aa0f0926724cc835fa4e8461d261b5397cbbefff15508b` |

Hashes were read with `Get-FileHash -Algorithm SHA256` in the current worktree.
The exporter/configuration hashes match `export-preparation.json`.

## Source ordering and development

The exporter pins the native baseline's complete input manifest, checks all 299
ordinals and exact `DSC00001.ARW` through `DSC00299.ARW` filenames, bounds input
paths to the frozen directory, and checks each original's size/content before
decoding. It validates content and within-run size/mtime again after all outputs.
The list passed to Helicon contains only these 299 developed TIFFs in the same
sequence; the golden fixture is outside that list. `-sort:asc` should still be
verified against the actual application receipt rather than assumed from the
caller list alone.

The product decoder/MHC/writer, fixed manual WB, explicit matrix, levels,
four-worker limit, single-source residency and no-CA/no-alignment export are
visible in the source. Fixed development avoids per-frame automatic tone
changing focus evidence. The frozen vitamin fixture exercises the same
normalization/writer route and can detect path drift; it is consistency evidence,
not a new independent calibration or a photographic quality measurement.

The weevil active-area distinction is now directly observed in the separate
three-source review: rawler reports 7032 × 4688 at `(0,0)` while RawPy exposes
7028 × 4688 at the same top-left. All overlapping u16 values matched exactly for
frames 0, 149 and 298. The exporter correctly preserves the actual product
decoder extent and records it. It must not silently crop to RawPy's width or pad
RawPy's arrays to fake 7032. The native delivered baseline is 6896 × 4596 at
reference-native offset `(68,46)`, not a full-source image with that origin.

## What the comparison can establish

**ARGUED.** A clearly better complete Helicon result would demonstrate a practical
workflow gap for these settings. It would not isolate a deficient merge formula:

- Helicon receives demosaiced, tone-mapped RGB16. Native Strehl merges RAW-domain
  values and develops the result. Tone before a merge changes gradients, scale
  energy, clipping and inter-frame photometry. The exporter uses rounded logged
  tone values, not the native run's exact internal tone bits.
- The exported inputs have no Strehl lateral-CA gather; native reconstruction
  applies its gear-matched correction. Hair color/fringe differences therefore
  cannot automatically be attributed to the merger.
- Helicon performs its own placement and may choose a different reference or
  output crop. Native Strehl uses the retained 299-frame map and crop. The same
  `(x,y)` does not name the same subject site in both final outputs until their
  output gauge is checked. Show both complete outputs first; establish matched
  native subject locations before any local comparison.
- B radius8/smoothing4 and C smoothing4 are useful fixed, reproducible workflow
  arms. They are not a search over Helicon settings or a claim that this is its
  best possible performance. Native flags also remain part of the comparison,
  including its documented pyramid sharpening.

## Evidence needed before a competitive claim

`run-weevil.py` currently checks successful bounded process exit, nonempty ICC,
RGB16 type and an output area greater than four million pixels. That is adequate
to detect some export failures, but is much too weak to establish a complete
299-source stack. It does not yet check `saved-outputs.txt` or parse the actual
application log for the loaded frame count/order, selected method/settings,
alignment behavior and output dimensions/crop.

Before making a competitive claim, root should reconcile those actual application
records with the invocation and intended 299-source list. Capture the relevant
run portion of the shared application log, so stale prior settings or another
run are not mistaken for this one. Preserve the complete output and inspect
coverage, watermark absence, hairs/scales at multiple depths, color and halos.
A clean exit or parseable TIFF cannot replace that inspection. This is an
evidence gate before a claim, not a reason to delay the already-authorized source
preparation.

The runner records host resources and process accounting. Compare complete
workflow cost, including the TIFF preparation and external alignment/merge, with
native alignment plus merge/development. Distinguish process timing from
verification/hash time and report concurrent host load. Preparation time alone
or Helicon merge time alone cannot establish competitive speed.

## Source-neighborhood locator

The forthcoming TIFFs are RGB16, so JPEG artifacts are not a source-locator
confound. Full JPEG overviews and resized contact sheets are orientation aids
only; the native crops come directly from TIFF pixels with ICC retained.

Inverse sRGB transfer of these TIFFs yields **display-linear values after the
fixed tone**, not the original scene-linear radiance. Two-scale energy can be
increased by noise, glints, clipping rims or MHC artifacts. A dark-background
control is useful for new texture but is not calibrated sensor noise, and its
brightness differs from the insect. The locator therefore only proposes a
contiguous neighborhood for visual inspection. Its smoothed score maximum is
not an admitted source, a best-frame ceiling, a merge target or a quality score.
Frame-center mapping through the existing placement preserves native source
sampling but leaves scale/rotation and CA differences visible; it is not a new
alignment solution.

No extra phantom campaign is required for this preparation review. The next
decisive evidence is the completed source set, real native source neighborhoods,
the actual gathered anchor observation, and the complete external stack outputs.
