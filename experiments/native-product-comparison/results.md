# Actual coffee-bean comparison

The current stacker produced a complete105-frame RAW photograph in50.063seconds using its existing alignment map. The retained MIT fork produced a corresponding photograph from105 existing Lightroom TIFFs in99.766seconds, including its own alignment. Both photographs are available. These single workflow observations do not establish a fair speed ranking or SOTA quality.

| Completed workflow | Input | Output | OwnedCPU seconds | Peak job commit |
| --- | --- | --- | ---: | ---: |
| strehl, current merge with exact rounded handoff | 105originalRAWs,4.161GB; existing ref52map | 6784×4524 RGB16, tagged sRGB | 305.078125 | 2,838,089,728B |
| MIT fork, neighbour alignment, OpenCL RTX5090 | 105developed float32LinearRec2020 TIFFs,41.256GB | 7008×4672 RGB16, explicitly requested sRGB, untagged | 802.312500 | 25,536,389,120B |

The native image uses current seven-band/noise-aware merge and automatic tone rendering, with black0.020049/white1.165917/contrast0.550. Its full-frame Crop starts at quad(62,41), corresponding to native(124,82), and preserves reference scale. Lightroom already applied camera colour/chroma-noise/lens corrections before the fork received its inputs. Colour, contrast, crop and geometry are consequently different upstream workflows; the brighter fork background can hide marks. Native's historical map solve and prior Lightroom development are excluded from the two render costs.

The first fork attempt was still completing tasks when OUR16GiB memory cap stopped it after16.203seconds and128.90625CPU-seconds. It was not an engine crash. We preserved that attempt and explicitly amended our own resource budget once to40GiB, with independent review and at least48GiB available RAM required before launch. Only the fork output path and cap changed; inputs, binary/DLLs and all quality/worker/alignment settings remained exactly bound. The native image was not repeated. The amended fork completed normally within40GiB. This failed attempt remains part of the development cost.

![Native RAW overview](C:/dev/blog/death-of-software/projects/strehl/experiments/native-product-comparison/run-1/native-overview.png)

![MIT fork overview](C:/dev/blog/death-of-software/projects/strehl/experiments/native-product-comparison/fork-2/fork-overview.png)

The overviews are for composition only. Four exploratory pairs of512×512 native-sampling crops are recorded in view-1/regions.json: gray background, front texture, central crack, outer boundary. Both delivered files were converted to8bit by rounded division by257 for viewing; no tone matching, output registration, sharpening or noise removal was applied. The native ICC explicitly describes sRGB; the untagged fork was interpreted according to its explicit sRGB invocation. Both files omit orientation, so normal top-left orientation is used.

A distinct elongated dark mark is visible in the native gray-background crop; faint diffuse marking is also visible in the fork's gray crop. This supports investigating the native marks but does NOT establish that the fork removes them. Texture contrast differs, the central-crack crop landmarks are offset, and both outer edges are soft. These four pairs do not support a clear structural-quality winner or a cause for the marks.

![Gray-background crops at one pixel per output pixel](C:/dev/blog/death-of-software/projects/strehl/experiments/native-product-comparison/view-1/background.png)

The next concrete task is a small source-coordinate diagnosis of one frozen native stroke and a nearby clean gray patch. next-rois.json fixes output rectangles before any original-frame crop read. Compare a few original RAW observations in sensor coordinates versus scene coordinates under the existing map, with an independent decode route and a control that can reject the proposed explanation. A captured scene feature, a sensor-fixed mark stretched by gathering, and a fusion artifact remain different hypotheses. No dust, alignment or merge cause has been proved, and no cleanup is applied to these photographs.

Reproducibility: run.py under sourceb46eafb453632a5fa919d7d72ef1f88c8e7f3612 produced run-1; its completed native output and intervened fork stop are preserved. Amendment41f5a638259e10f8f520b9f60ed04198b927c578 and run.py --fork-memory-40g produced fork-2. Plans bind all210input metadata records, full argv, executable/DLL/map digests and budgets. All primary files, logs and viewing metadata remain local. Native TIFF SHA411f3bb79fcee3aecbf27899d036e785b92469e53b21b0b339e82d65cd5c6e87; fork TIFF SHA137ab09a78af02594afe360b77a52fa2f1c3096bc5fb0a6ac16b50a667b019d4. The corresponding pixel hashes and exact byte counts are in their output receipts. No new solver, renderer, calibration model or merge algorithm was introduced by this comparison.
