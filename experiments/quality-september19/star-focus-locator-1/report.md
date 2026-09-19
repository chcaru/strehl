# Detail-bearing star-sand source neighbourhood

**Photographic confirmation:** source ordinals **116–120** show pore rims and granular boundaries that were diffuse in the earlier 129/133 comparison. Ordinal **120, DSC00136.ARW**, is a defensible local anchor for a new fixed placement fit. It is not uniformly best across this sloping surface: some lower portions are at least as resolved in 116/118, while 122/124 begin losing definition. All five nominated native source views were inspected. There is no established individual source structure missing from the full merge yet.

The new local anchor does **not** change the saved map's global reference, which remains **129**. The old local correction test used ordinals 125–133, after the nominated focus peak. Its photographic null result therefore cannot close the general local-refinement direction for this scene.

## One streamed locator pass

**MEASURED** by the command:

```powershell
python -I -B -X faulthandler experiments/quality-september19/star-focus-locator.py
```

The helper ran one sequential pass over all **259** original RAWs, with the existing map SHA-256 `6594d98255383218a3114fd783bfd0e2215b39b202777f1ee2e493f4b287a6a1`. It retains the complete scalar score/coordinate record, but only a rolling patch buffer and the nominated nine-frame neighbourhood in memory. The nine saved original-u16 patches are **116 through 124**, named `frame-116-cfa.npy` through `frame-124-cfa.npy`. There are no full RGB frames or materialised aligned-frame stacks.

The five native source views are **116, 118, 120, 122, 124**. The peak is a nomination from the scalar curve, not an image-quality result. `nomination-curve.png` shows the complete curve for orientation, with the prior window marked; it must not be used as a sharpness-quality improvement chart.

The score is extracted unchanged from `quality-september14/focus-locator.py`, bound to SHA-256 `8c75f1a14fd0024774954a31423f4bf5bcf6bedc9dc5b4840cb0e22d450edb03`: a two-dimensional true-G1 plane is smoothed with Gaussian sigma1.2, followed by pooled gradient energy on its interior. Gaussian sigma2 along the frame axis is applied **only to the resulting scalar curve**. The score support is the mapped, source-centred 328-native-pixel porous-grain core. Source scale and rotation are recorded and not resampled; they are possible score confounds.

The original flat/noise/blur controls ran **before RAW decoding**. The zero-noise flat scores zero; adding noise increases the score; a strongly noisy flat outscores blurred real structure. This demonstrates the failure direction rather than hiding it: noise, contrast, and scale can nominate a misleading frame. The native photographic inspection above is the basis for calling 120 detail-bearing, not the curve maximum.

## Geometry and retained data

Each retained patch covers mapped reference-sensor support **(594,1424,392,392)**, with an even source origin and at least **12 native pixels** beyond all mapped corners. The measured minimum among retained patches is **12.123072 native pixels**. Exact `a`, `b_plane`, source extents, original-file metadata, and u16 hashes are in `receipt.json`. Global geometry is 7032×4688; LibRaw's visible width is 7028, and every extracted patch is inside that visible active domain. Nothing was computed over the synthetic full-decoder padding.

Every RawPy view was copied while its context remained open. The nominated anchor 120 patch was independently decoded by the existing rawler checker and has **zero differing u16 sensels**. This independent decode applies to the anchor, not all nine retained patches. Source-file sizes and last-write timestamps were checked against the prior full-star baseline for all 259 originals and remained unchanged; this is not a full original-file content-hash guarantee.

The stage receipt preserves `reference_index=129`, `local_anchor_nomination=120`, `target_origin_native=[594,1424]`, `target_shape=[392,392]`, original levels/WB/tone bits, and the map hash. The small source-display crops are source-centred and even-rounded like the existing observer; they have no CA correction or geometric gathering. They identify focus and supply original data for the next fit, but are not exactly registered output-grid truth.

## Exact development checks

The prebuilt `saved-rgb-render.exe` accepts camera RGB, not CFA. A small ordered-tap adapter therefore reads the project's existing MHC tap order, uses f32 arithmetic and mirror borders, and feeds the existing actual-product developer. It does not use the M95 SciPy correlation implementation whose rounding differs.

**VERIFIED before the RAW pass:** all **338,688 f32 RGB samples** for each of the actual star 125/129/133 source fixtures match the ordered adapter **bit for bit**. The compiled product developer reproduces the held actual-star baseline RGB16 TIFF with **zero differing samples** before emitting any candidate. It uses the same star WB/tone bits, camera matrix, and saturation handling. The source MHC golden fixtures and exact development check are in `preflight/controls.json` and `preflight/render/receipt.json`.

The streamed extraction also re-encountered frames 125/129/133 and reproduced their saved normalized CFA arrays bit for bit, checking source origin and normalization order against the prior actual observer. Every nominee is developed as a 336×336 patch and trimmed by PAD4 to **328×328 native pixels**, with no spatial resize. `render/receipt.json` retains the final exact-development check. These three golden scenes constrain the adapter used here; they are not a proof of every possible input pattern.

The bounded child tree completed in **133.438 wall seconds / 133.140625 CPU seconds**, with **182,222,848 bytes** peak committed job memory, within the requested 240-second CPU/wall and 2 GiB limits. These are single operational observations, not comparative speed measurements. The process exited normally with terminal job accounting. No full-stack replay, production edit, rebuild, new reconstruction method, or parameter sweep occurred.
