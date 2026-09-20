# Complete chip Helicon references — frozen preparation

Root executes; this author does not build, decode RAW, run Helicon or judge the output. Prepare exactly two full299-source references: Helicon B radius8/smoothing4 and C smoothing4 (radius inactive). No parameter or source-subset search. This is a complete-workflow comparison, not a pure merge or CA-order experiment.

Input is `D:/personal/macro/requests/misc-diagnostic/uncapped-IC-chip-cpl/DSC00001.ARW` through `DSC00299.ARW`, in ascending order. The retained chip-baseline inventory supplies exact paths/metadata. Original files are read-only. No held map is applied to the TIFFs. The full native comparison is `experiments/ca-before-mhc/full-1/current/output/image.tiff`: canonical current ordering,299sources, held map, native crop6468×4300, WB bits `[1070374912,1065353216,1076715520]`, tone `[.004293,.946441,.55]` and its recorded camera matrix.

The old `quality-batch-develop.exe` cannot accept this capture: it hardcodes70 paths DSC94–163 and vitamin-C tone. The new `crates/strehl-cli/examples/chip-batch-develop.rs` is a direct copy of that frozen exporter with only count299, DSC1–299, chip tone and diagnostic/status labels changed. The original remains SHA256 `804107b7910daff699d194414260e7a2750e9128ff77ce5921bf026d2e9fdb70`. Reuse its actual decoder, active-local RGGB normalization, MHC and product writer, plus the exact retained u16-normalization/developer golden. Build this one example once; no fork build or new development pipeline.

Development streams one original at a time and writes7032×4688 RGB16 sRGB TIFFs. Each source must retain camera/ISO100/levels512–15360/normalizedWB/matrix; no per-source tone or exposure fitting. Golden normalized f32 and RGB16 comparisons must be exact. The wrapper checks every TIFF's dimensions, type and ICC against the native master. Explicitly **no CA correction or alignment** is applied to these prepared images, matching the earlier approved vitamin-C workflow. Native Current applies its gear-selected CA during gather. Helicon receives toned colour before fusion; native Current applies development after CFA fusion. These known differences and Helicon's independent alignment/brightness/interpolation state prevent an isolated mechanism claim.

The existing official Helicon executable is SHA256 `29ca62df122163c1295e1e2a416a42acfdf52f20c83d0beed99c4af154d42089`, retained as8.3.11 in the prior run (Windows file metadata says8.3). Prior Sept19 TIFF runs succeeded at full resolution under its trial; the retained startup log says Trial license. No new app launch or license action occurred during preparation. Exact existing CLI:

```text
HeliconFocus.exe -silent -noprogress -i inputs.txt -mp:1 -rp:8 -sp:4 -sort:asc -tif:u -save:whole-stack.tiff -o saved-outputs.txt
HeliconFocus.exe -silent -noprogress -i inputs.txt -mp:2       -sp:4 -sort:asc -tif:u -save:whole-stack.tiff -o saved-outputs.txt
```

The manifest names only the299 developed DSC TIFFs, excluding `golden.tiff`. B precedes C. No settings, registry, license, GPU preference or alignment preference is changed. The unknown persisted application state is disclosed rather than falsely called a measured default.

`resource-evidence.json` preserves the small relevant vendor-log excerpt and local-help binding. Workspace C: had691.7GB free. TIFF pixels require59,141,032,704bytes; reserve80GiB before export. Existing output/master/views add roughly1GB. Helicon's documented recent-image cache was31,516MiB at retained startup, but this is only part of its memory footprint. Root approved one bounded attempt per method with a40GiB Windows Job committed-memory cap,600s wall and12,000s CPU, sequential with no other large render. A failed B preserves its artifacts and blocks C pending separate reassessment; no automatic retry, resize or partial stack is substituted. Development is capped600s/2400sCPU/3GiB; build600s/1800sCPU/8GiB. Prior70-source times suggest minutes, not over30min, but that extrapolation is not a performance claim or guarantee.

Commands from the repository, each an explicit root action:

```text
python -I -B -X faulthandler experiments/chip-competitor/run.py build --out experiments/chip-competitor/run-1
python -I -B -X faulthandler experiments/chip-competitor/run.py develop --out experiments/chip-competitor/run-1
python -I -B -X faulthandler experiments/chip-competitor/run.py b --out experiments/chip-competitor/run-1
python -I -B -X faulthandler experiments/chip-competitor/run.py c --out experiments/chip-competitor/run-1
```

Every stage refuses existing output files. Build sources/executable, original inventory, native master/receipt, exporter golden, prepared TIFFs and vendor executable are hash-bound. Original metadata is checked throughout; the exporter records original full-file hashes, while both external runs verify all prepared hashes before and after. No N-image RGB collection is created by our scripts; proprietary internal memory behavior is controlled only by the documented cache and Job cap, not falsely asserted to be streaming.

Require full7032×4688 RGB16 outputs with the same sRGB ICC. Retain TIFF masters, full native PNGs and clearly labelled overview PNGs, using rounded u16/257 with no additional colour/tone/sharpening. Independent visual review must check trial overlays, then entire fields and corresponding native detail, material-colour, low-detail and scratch controls. Native Current has a different output gauge; later coordinate-only matching must not resample comparison crops or silently elect flattering regions. Differences, sharper-looking grain or fewer colours alone are not gains. No SOTA/default claim follows from these references.
