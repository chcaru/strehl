# Star porous-grain source/gather/merge diagnosis

**Photographic result:** none of the three preselected gathered sources, ordinals **125, 129, 133**, shows a clear pore rim or ridge that the merged image loses. All three look softer than the merge. Frame 125 shows the strongest suggestion of pore structure among these three; 129 and 133 look progressively more diffuse. This does **not** identify the best source in the 259-frame stack and does **not** establish an acquisition or optical limit.

This narrows the immediate interpretation of the local-placement null result: the tested local-fit window does not visibly carry the sharp pore structure present in the full merge. Continuing to refine this particular window is unlikely to answer whether merging loses the best available detail. The next source-selection step should locate a genuinely focused contributor for this ROI before claiming a merge defect or acquisition limit.

## What was compared

One authorised full replay used the same **build-3 executable**, all **259 RAWs**, baseline map, processing environment, and pinned tone as the saved observer-disabled star baseline. Local correction was disabled. The only change was enabling the existing observer for three named regions at the same output coordinates **(472,1352,328,328)**, frames 125/129/133. These correspond to DSC00141.ARW, DSC00145.ARW, and DSC00149.ARW.

The same actual developer produced original-source, gathered-source, and merged panels. Every saved native PNG trims the observer's PAD4 from 336×336 to **328×328**, with nearest 16-to-8-bit rounding and no resizing. All nine panels were viewed.

The **gathered-source versus merged** comparison supports the photographic statement above: these share the cropped reference output grid and the actual production correction path. The original-source panels provide context only. They are centred through the map and rounded to an even source origin, and have neither geometric gathering nor CA correction; they are not exact registered counterparts. They also look diffuse, so there is no obvious sharp structure in those context panels that gathering alone visibly destroys, but that is a limited visual observation, not a quantitative gather-quality test.

The merged image has more distinct pore depressions and granular structure than these three sources. That observation does not by itself prove each fine point is genuine or exclude sharpening/speckle. There is no independently sharp ground truth or flat-noise control in these panels, and no gradient-energy quality claim was made.

## Observer integrity

**VERIFIED:** all **90,370,560 final RGB16 samples** exactly match the saved observer-disabled baseline. The entire TIFF file hash also matches:

`5fc6c3ab8e2bcb64ee9d1383586f0c3763d6dbc709968a218bf36b9d654420ae`

The common RGB16 pixel-array SHA-256 is:

`c6a5d6a68bc67950ebfc351ef3130ccd1b84b9bf33a7934f2d40cb1822022df9`

`observer-nonperturbation.json` records both bindings and zero differing samples. Tone bits, white-balance bits, levels, crop domain, reference index, and frame count were also checked against the observer-disabled receipt.

**VERIFIED independently against full-image coordinates:** each saved merged panel's PAD4-trimmed interior exactly equals the full baseline RGB16 slice at `[1352:1680,472:800]`. A second interior choice with a further 16-pixel margin also matches exactly. A deliberately wrong lookup shifted two output pixels right differs in **322,565 RGB16 samples**, proving the location check is capable of failing. No mismatch was excused as a patch-boundary effect. The three merged captures cover the same output field and are duplicates, **not three independent photographic confirmations**. See `merged-patch-verification.json`.

Commands actually run from the repository root using the installed Python 3.12 executable:

```powershell
python -I -B -X faulthandler experiments/quality-september19/star-matched-source-run.py
python -I -B experiments/quality-september19/star-matched-source-verify.py
```

The replay command, full environment, source bindings and job limits are in `invocation.json`, `sources.json`, `preregistration.json`, and `process.json`. The process completed in **92.563 wall seconds / 364.625 child CPU seconds**, with **3,335,864,320 bytes** peak committed job memory. These are single operational observations, not comparative speed results. Terminal job accounting confirmed all child work had exited. Original-file sizes and last-write timestamps remained unchanged for all 259 sources; this is not a full original-file content-hash guarantee.

No production edit, rebuild, sharpening variant, local-correction variant, parameter sweep, or additional observer statistic was introduced.
