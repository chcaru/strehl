# Complete299 green-phase result: reject this recipe

**VERIFIED photographic decision:** the fixed phase-energy candidate does not provide a useful complete-image improvement. Both it and the matched-mean variance-control arm strengthen colored curved traces in the frozen black background. Scale softness, glint spill and broad pale occlusion contours remain. Some fine highlights/hairs become slightly more emphatic, without convincing newly resolved structure. Phase separation has no clear useful advantage over matched mean-green. Root independently inspected all three whole views and all30 frozen native views and concurs with [the independent photographic review](photographic-review.md).

Do not promote, optimize or run bug2/flat candidates for this exact recipe. Preserve all outputs and failed controls. This finding does not refute every phase-aware guide, optical restoration or original-CFA inverse method. The substantial softness, glare, ghosting and occlusion-halo objective remains unresolved.

## Actual complete run and identity

**MEASURED:** root ran:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase.py build 4
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase.py screen 4
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase-photo.py cost 4 2
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase-photo.py full 4 2
python -B -X faulthandler experiments/raw-quality-2026-10-26/green-phase-guide/prepare-photo-review.py --input outputs/raw-quality-2026-10-26/green-phase-full-job-2/output --out outputs/raw-quality-2026-10-26/green-phase-full-review-2
```

Frozen test executable SHA256 `d89b20091cd425ea546da3234657ed3c99de85781cc4d0cdad19132c68ec67f6`; current main base4813e46bdc9aaf5f9220115911df5cd5aa3fd808 plus recorded experiment sources. All299 ordered weevil107 originals, map SHA256 `4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`, reference149, full6896x4596 output, CA-off held condition, four workers, rounded GPU gathering,16 source-space noise draws and finest two changed bands. Full source/config/environment bindings are in the [invocation](../../../outputs/raw-quality-2026-10-26/green-phase-full-job-2/invocation.json); no source-specific tuning was introduced.

All299 before/after original content and metadata checks passed, every source appeared exactly once, and coarse fields/terminal means remained unchanged. The canonical merged CFA payload and decoded RGB16/RGB32 pixels exactly reproduce the prior complete CPU CA-off output. TIFF file bytes need not match because metadata differs. [Independent receipt audit](full-receipt-review.md) distinguishes these checks from independent RAW decoding and quality review. The complete producer receipt SHA256 is `4eaa7e1d9cdfbf98244e87835d103daa5e66d35c789c3f38dee9b22bfc13c0df`.

The native job exited0 with clean terminal Job accounting:2261.063seconds,7,961,710,592bytes peak committed Job memory. It used the GPU gather path; sampled GPU figures are whole-device observations, not process-exclusive peak memory. The flat baseline, small retained-output observation, separate exporter build and flat TIFF development overlapped parts of this run. Timing is operational and includes research variance probes/three outputs, not a competitive production-speed benchmark. The display/export verification took14.094seconds. No performance optimization follows a photographically rejected recipe.

## Complete retained evidence

All three displays use the same float gain3.434, clamp, sRGB transfer, ICC and RGB16 rounding, with no per-arm tone fit or sharpening. Full outputs and masters:

| Arm | Complete photograph | Full-resolution RGB16 master | Master SHA256 |
| --- | --- | --- | --- |
| Canonical baseline | [Complete](../../../outputs/raw-quality-2026-10-26/green-phase-full-review-2/baseline/complete-stack.jpg) | [Master](../../../outputs/raw-quality-2026-10-26/green-phase-full-review-2/baseline/common-display-master.tiff) | `2bb624d6f299f500636040065d17c5601a3c87d4bddb27b554ca6e726ed24b0a` |
| Matched mean-green variance control | [Complete](../../../outputs/raw-quality-2026-10-26/green-phase-full-review-2/matched-mean/complete-stack.jpg) | [Master](../../../outputs/raw-quality-2026-10-26/green-phase-full-review-2/matched-mean/common-display-master.tiff) | `b15ea6ea8365b7005ee246bc0cdc39f3aece3b5e09cd0ffb7214b9d274aaaa11` |
| Separate phase-energy candidate | [Complete](../../../outputs/raw-quality-2026-10-26/green-phase-full-review-2/phase-energy/complete-stack.jpg) | [Master](../../../outputs/raw-quality-2026-10-26/green-phase-full-review-2/phase-energy/common-display-master.tiff) | `a02a25333f51cbf479d02cefe28703c9149a7407552b7db4a073a8d1af4d3dbf` |

All original float-linear masters and exact CFA payloads remain under [the complete output receipt](../../../outputs/raw-quality-2026-10-26/green-phase-full-job-2/output/completion.json). The [display receipt](../../../outputs/raw-quality-2026-10-26/green-phase-full-review-2/common-display-receipt.json) binds complete files and all30 exact384-square witnesses. Crops supplement the complete photographs; resized overviews supplied orientation only.

The independent photographic report also includes the already completed all299-source Helicon B/C whole-workflow images and masters. B retains some preferable hair separation but has rounded scales/fringes; C shows glint bloom and colored background traces. Their premerge development, CA treatment, placement, gauge and tone differ from the native route, so they are credible full-workflow context, not an isolated merge experiment or ground truth. This new native recipe does not establish a competitive gain.

The generated screen's low-frequency loss, essentially unchanged moderate diagonal, persistent glint streaks and different-color tradeoff remain recorded in [independent-results.md](independent-results.md). All56 build4 payloads reproduced build3 exactly after the TIFF reader buffer fix. Those controls justified observing one full photograph, and did not predict photographic success. Cost1's decoder-limit failure and all earlier builds remain preserved.
