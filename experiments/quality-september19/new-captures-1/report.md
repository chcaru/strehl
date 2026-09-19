# New diagnostic captures: orientation only

Recommend **star-sand-cpl** as the next independent scene for the local-placement and detail-retention intervention. Its middle embedded preview contains opaque, textured grains with narrow prongs, porous surfaces, a ridged shell, and overlapping boundaries. These offer photographic checks beyond the chip's repeated straight rails. This is an **ARGUED scene-selection recommendation**, not a measured improvement or proof that the proposed correction transfers.

## Inventory and metadata

**MEASURED** by `orient-captures.ps1`, run from the repository root:

```powershell
& 'experiments/quality-september19/new-captures-1/orient-captures.ps1'
```

| Folder | ARW files / all files | Bytes | Filename range | Selected zero-based indices |
| --- | ---: | ---: | --- | --- |
| star-sand-cpl | 259 / 259 | 10,056,556,544 | DSC00016.ARW to DSC00274.ARW | 0, 129, 258 |
| crystalized-vitamin-c-cpl | 70 / 70 | 2,802,286,592 | DSC00094.ARW to DSC00163.ARW | 0, 35, 69 |

Both folders are under `D:\personal\macro\requests\misc-diagnostic`. These are counts of the supplied folders, not an assertion that they contain every frame of an original camera sequence. The inventory uses `Get-ChildItem -Force -Recurse -File`, including hidden/system files. There were no non-ARW files in these two listings.

**MEASURED in the six selected files only:** all report ILCE-7CM2, FE 100mm F2.8 Macro GM OSS + 2X Teleconverter, 200 mm focal length, f/5.6, **1 second, ISO 100**, WhiteBalance `Color Temperature/Color Filter`, ColorTemperature **3000 K**, and ImageStabilization `Off`. Full text and numeric outputs are saved as `metadata.json` and `metadata-numeric.json`.

| Folder | First selected capture time | Middle selected capture time | Last selected capture time |
| --- | --- | --- | --- |
| star-sand-cpl | 2026:09:17 00:10:32 | 2026:09:17 00:13:42 | 2026:09:17 00:16:52 |
| crystalized-vitamin-c-cpl | 2026:09:14 23:48:52 | 2026:09:14 23:49:44 | 2026:09:14 23:50:34 |

Times are the literal `DateTimeOriginal` values, with no timezone inference. All six report ElectronicFrontCurtainShutter `Off`; no `ShutterType` value was returned. EFCS Off does not independently establish an electronic shutter. Tripod, delayed start, light source, polarization, and the actual teleconverter manufacturer were not verified from these tags. The user's capture description remains the source for those settings.

## Photographic orientation

All six images are camera-rendered **1616 × 1080 embedded `PreviewImage` JPEGs**, extracted byte-for-byte by the ExifTool executable. They have not been developed from RAW by this experiment. `previews.json` records filenames, source files, indices, dimensions, and JPEG SHA-256 hashes; `commands.json` records every ExifTool invocation. This follows the earlier September 14 metadata/embedded-preview orientation, using the same installed ExifTool binary and tag set, with a small saved helper for reproduction.

**Star sand:** the middle image, `star-sand-cpl-129-embedded.jpg`, visibly resolves porous grain surfaces, narrow pointed extensions, and ridges on a small shell left of centre. The first and last sampled images are substantially less focused over much of the frame. The middle image still has surfaces at differing focus. Useful regions for subsequent RAW localization include the ridged shell around preview `(390, 330)`, the porous star-shaped grain around `(160, 350)`, and overlapping rims around `(860, 580)`. Coordinates are only approximate positions in the embedded preview, not sensor/output coordinates or frozen evaluation crops. No assertion about RAW focus maxima follows from selecting the middle image.

**Crystallized vitamin C:** the middle image, `crystalized-vitamin-c-cpl-035-embedded.jpg`, resolves many small transparent-looking polygonal facets. The first and last selected images look softer. Bright facet edges and points coexist with a large pale field. Its 70 frames make it a lower-cost complete-stack candidate, but transparent/reflected structure can make a placement residual sensitive to more than geometric error. That interpretation is a reason to prefer star sand for the immediate transfer test, not a measured diagnosis of failure in this stack. Retain the crystals for a later highlight/detail stress test.

Neither JPEG set establishes RAW clipping, sensor noise, true fine-detail accuracy, or the quality of a future merge. The visible pale field in the crystals has not been validated as a flat noise-control region. Photographic selection can favour conspicuous texture; therefore a later success claim must also retain a separately chosen flat control and inspect overlapping boundaries for occlusion artifacts.

## Scope and read-only record

No full RAW pixel decode, alignment, stacking, source edit, production-code edit, or external research was performed. Only the six chosen files were passed to ExifTool for metadata and embedded-JPEG extraction. Corpus paths are command inputs; every output is in this experiment directory.

**VERIFIED listing equality:** `inventory-before.json` and `inventory-after.json` agree on each path, byte length, last-write UTC ticks, and attributes for all **329 files / 12,858,843,136 bytes**. `receipt.json` records the successful comparison. This is a before/after listing check, **not a full corpus content-hash guarantee**; the helper does not claim the stronger property.
