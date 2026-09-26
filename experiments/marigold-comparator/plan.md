# One complete marigold4 B reference

PREREGISTERED, 2026-09-25. Root executes one complete488-source Helicon B radius8/smoothing4 attempt. This is a whole-workflow headroom comparison, not a merge-cause or SOTA claim. No tuning, subset, resizing, C arm or automatic retry. A vendor trial refusal or resource failure is retained and stops this attempt; no license, date, preferences or application-state changes.

Use the frozen `full-stack-source-prior/recipes/marigold-4.json` chronology:279 sources DSC00021–00299 in stack4.1, then209 DSC00001–00209 in stack4.2. Unique ordinal filenames `frame-00000.tiff`…`frame-00487.tiff` avoid duplicate-basename collisions. Compare the exact serde source-order hash with the corrected Current cache. Read original content only for its recorded SHA256 and actual native decode; preserve originals and check metadata after every stage.

The new example reuses the native decoder, active7032×4688 area, MHC and current TIFF writer. Before exporting, require the existing independent u16/f32/RGB16 golden and an exact complete Current RGB16+ICC rewrite from its actual CFA cache. Fixed development is `illuminant-aware-color/cached-1/output/marigold4-receipt.json::baseline_resolved`: exact WB, D65 matrix, saturation ceilings, sensor top, −0.5EV exposure and tone bits `[1008079930,1049460607,1057803469]`. Every source must agree with the cache's camera/ISO/levels/WB/matrix. Current reference244, crop[191,128,3134,2088] and map SHA are held as comparison provenance; external TIFFs remain unaligned and CA-off.

Build only the new example, not the CLI test suite. The runner reuses the established chip comparator's clean Windows Job helper and bounded source inventory, adding its exact new files/inputs. It does not glob unrelated experimental Rust. Require a fresh `Compiling strehl-cli` line and non-fresh compiler artifact; copy/hash the executable. Sequential stages only, with root ensuring no other large job is running.

Reserve120GiB before development (RGB16 pixel payload alone96,524,494,848B), and20GiB before B. Immediately before B, require48GiB available system commit and46GiB physical memory, then cap the entire job at40GiB. Limits: build600s wall/1800CPU-s/8GiB; development600s/2400CPU-s/3GiB; B600s/12000CPU-s/40GiB. Prior chip299 timings/resource observations and the read-only feasibility snapshot are in resource-evidence.json; they are not a marigold performance guarantee.

Root commands, in order, after independent source review:

```text
python experiments/marigold-comparator/run.py build
python experiments/marigold-comparator/run.py develop
python experiments/marigold-comparator/run.py b
```

Require exactly488 unchanged prepared inputs, full7032×4688 RGB16 single-page output and exact expected ICC. Dimensions do not prove absence of trial overlays: independent whole-image review must check. Preserve native master/full PNG and whole-field overview and show complete Current and B outputs first. Native corresponding detail claims require actual correspondence; no automatic geometry match is assumed.

Predevelopment, CA-off inputs, independently fitted vendor alignment and unrecovered persisted alignment/brightness/interpolation settings remain confounds. Current is6268×4176 because of its held crop. The comparison can establish visible workflow headroom; it cannot prove a physical cause or calibrated photographic truth. No production default changes.
