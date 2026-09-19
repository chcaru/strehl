# Prepared full-star comparison

This directory was configured but **no full-star paired replay has been run by the preparation agent**. Root will execute after the generated Rust checks pass, without overlapping another full RAW render.

The baseline and candidate use all **259** star-sand RAWs, the same reference-129 map, **seven Laplacian bands plus the base**, the same rounded pinned tone `(0.01566, 0.51099, 0.55)`, and `observe=false`. The only candidate intervention is the already frozen porous-grain local displacement for ordinals 125–133, within sensor support `(594,1424,392,392)` and taper 32. The reference row is forced to exact zero displacement. Original map transform bits are bound to the fit receipt; fitted photometric gain/bias is not used.

After root's Rust checks, the prepared commands are:

```powershell
python -I -B experiments/quality-september19/star-full-context-placement.py baseline
python -I -B experiments/quality-september19/star-full-context-placement.py candidate
python -I -B experiments/quality-september19/star-full-context-compare.py
```

The default executable is `experiments/full-context-placement/build-2/cli-tests.exe`, with the build's source and executable hashes checked before replay. Each arm uses the existing common job bounds: 600 wall seconds, 3600 observed child CPU seconds, 16 GiB committed memory, eight workers. These are resource limits, not speed predictions. Output directories must be fresh.

The core output crop is `(472,1352,328,328)`. Four narrow transition views straddle the correction's support and taper. The far control is the ridged-shell interior `(1392,1168,328,328)`, outside the local support. All crop locations are frozen in `frozen-comparison.json` before either arm. Native TIFF samples are preserved; PNGs use nearest 16-to-8-bit rounding without resizing. A comparison script reports exact pixel changes and far-control identity, but no gradient-energy or noise-quality score. A change count is intervention liveness/locality, not image quality.

Success still requires independent photographic review showing preserved pore separation without new structure, stronger coloured speckle, or visible transition artifacts. The unchanged-region check is not a flat-noise control; generated controls handle that separate question. A null full-stack result is still possible despite the guide's held-out residual improvement.
