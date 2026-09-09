# Next actual product comparison

2026-09-09. Source/metadata pathfinding; no renderer, competitor, RAW decoder or build executed. Root can allocate exactly two primary renders below to expose the visible remaining gap on the complete coffee-bean capture. This is a RAW-direct versus existing Lightroom-development workflow comparison, not common-input algorithm attribution or a formal SOTA score.

**Inputs and complete geometry.** Current directory listings contain 105 matching stems, DSC00016 through DSC00120, in `D:/personal/macro/coffee-bean/*.ARW` (4,161,077,248 bytes) and `D:/edited/macro/coffee-bean/*.tif` (41,256,483,738 bytes). All 105 TIFF headers were read without loading pixels: each is uncompressed 7008x4672 RGB float32, ICC Linear Rec.2020, profile SHA256 `f1b3be2d97b3d6d4dd29b8d04ed14f7ead4b42ac2625bf46055e2aec0ca4358c`. Matching names do not prove pixel-equivalent development.

The current committed `experiments/M-PHASE0-PHASE/out/canon/coffee-bean.warpmap.txt` has exactly 105 placed rows, indices 0..104, no refusal, reference 52 (DSC00068), quad 3516x2344, Catmull-Rom, strategy S3-ba-unit. Current file SHA256 is `b21b247944c257ab0fd3c767c879b9abf4a5fb1112dded97c87990a7d537274c`; working bytes equal HEAD. Independently recomputing the source implementation's filename/size FNV-1a over today's ordered RAW metadata gives its stored `bb9a2b40eefb65a9`. This is a complete source-matching sidecar, not a prefix. Its recorded held-out 6.6705 plane px and cycle floor 2.2078 are historical alignment diagnostics, not per-frame truth or solved alignment. The old canon_provenance.json carries a different file digest; bind the actual current committed map above, not that historical digest.

Before rendering, root should run the metadata-only product identity check (source `align_cmd.rs::run_check` reads map and file metadata, no RAW decode):

```text
experiments/native-direct-planes/build-1/strehl.exe align D:/personal/macro/coffee-bean --check experiments/M-PHASE0-PHASE/out/canon/coffee-bean.warpmap.txt
```

If it unexpectedly refuses, stop. The smallest replacement is ONE current complete solve, no limit or prefix: `strehl.exe align D:/personal/macro/coffee-bean --reference 52 --threads 8 --resampler catmull-rom --out <fresh-run>/coffee-bean.warpmap.txt`. Require 105 placed rows before the native render; record solve time separately. No solve is needed on the presently verified metadata.

**Freeze one realistic fork preset.** Use the existing MIT fork `experiments/M175-fork-arm/bin/focus-stack.exe`, SHA256 `691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac`, selected source `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6` and its present DLL bundle. Pinned README/manual and source option parsing were read from this MIT subtree; no prohibited source was opened. Use default neighbour alignment, default image-transform/WB/contrast compensation, reference 52, default maximum 2048 alignment resolution, consistency 2, denoise 1, batch 8, eight worker threads, automatic OpenCL enabled. Do not pass no-align, global-align, no-transform, no-whitebalance, no-contrast, no-opencl or the tone sentinel's zero consistency/denoise settings. Record actual selected OpenCL device or CPU fallback from the log; do not silently relabel it GPU.

The child argv is the following flags followed by the 105 absolute TIFF paths in ascending filename order, supplied as individual argv entries rather than a shell wildcard:

```text
experiments/M175-fork-arm/bin/focus-stack.exe
  --output=<fresh-run>/fork-coffee-bean.tiff
  --reference=52 --threads=8 --batchsize=8 --consistency=2 --denoise=1
  --input-colorspace=linear-rec2020 --output-colorspace=srgb --output-bitdepth=16
  --verbose
  D:/edited/macro/coffee-bean/DSC00016.tif ... D:/edited/macro/coffee-bean/DSC00120.tif
```

The ellipsis describes argv expansion, not a literal argument. The actual frozen list must contain every stem once. Default covered-area cropping stays enabled. No depthmap, 3D preview, saved steps or extra render variant.

**Freeze current native product settings.** The already measured build1 CLI is `experiments/native-direct-planes/build-1/strehl.exe`, SHA256 `95e5c82d8940e87dc2e5e790a71aea4f5def69b03abbf1478a93b80087ca0236`, source f290b6145c091b68482b6cbb76fcc1533331c7bf. This avoids another build; the later bridge changes are test-only. Use explicit rounded direct handoff, green-only probe, parallel writeback, full-resolution gather, current noise/profile defaults and gear-guarded CA, defect correction off. Clear other experimental overrides. Root must finish the allocated rounded whole-consumer identity decision before launching this proposed arm.

```text
experiments/native-direct-planes/build-1/strehl.exe stack D:/personal/macro/coffee-bean
  --merge pyramid --pyramid-bands 7 --pyramid-gate 2 --pyramid-exponent 2
  --pyramid-sharpen 1.4 --pyramid-select soft --pyramid-base mean
  --srgb --demosaic --resampler catmull-rom --cover crop
  --out <fresh-run>/native-coffee-bean.tiff
```

Environment: `RAYON_NUM_THREADS=8`, `STREHL_PYRAMID_WORKERS=8`, `STREHL_ALIGN=1`, `STREHL_WARPMAP=<absolute current coffee-bean map>`, `STREHL_DIRECT_PLANES=rounded`, `STREHL_PROBE_GATHER=green`, `STREHL_WARP_WRITEBACK=parallel`, `STREHL_FULLRES_GATHER=1`, `STREHL_DEFECT=off`. Leave STREHL_FIX_CA unset for its current three-valued gear guard. No exposure/auto-exposure, sharpening postpass, confidence or observer. No --limit. Crop preserves the reference scale; do not mix the previous native speed test's cover=scale with this comparison.

**Interpretation and bounds.** Both delivered files are intended sRGB RGB16 viewing outputs, not numerical linear-light evidence. The TIFF inputs have 105 identical relevant XMP settings: zero exposure/sharpness; colour noise reduction 25; Adobe Standard camera profile; enabled lens distortion/vignetting scales 100; HDR edit mode 1. Consequently colour/noise/geometry differences mix development with stacking. The retained fork explicitly converts float linear Rec.2020 to sRGB, clips its range and quantizes internally; it does not preserve all input float/HDR values. Native source active dimensions are 7032x4688 while Lightroom is 7008x4672 with lens correction: equal reference index does not imply equal pixel coordinates or equal crop. Record both actual crops/dimensions and compare common subject regions visually at native sampling. Do not interpret a bare pixel difference or gradient increase as superior fidelity; inspect flat grain, texture continuity, coloured rims and occlusion halos together. No histogram match or output resampling should become an undisclosed image-quality fix.

Use the existing `experiments/m193c-output-grid/bounded-process.py` Windows job helper and pinned `experiments/m12-scorecard/m12-harness.py`, sequential children, fresh outputs only. Proposed root allocation per primary child: wall 600 s, owned CPU 3600 s, peak committed memory 16 GiB, log 4 MiB; at most two TIFFs/512 MiB retained output. These extend the existing native 180 s/900 CPU s/8 GiB small-stack limits to the actual 105-frame workflow; they are prospective caps, not predicted costs. Optional identity check: 15 s/15 CPU s/1 GiB; only if refused, the single full alignment gets 180 s/900 CPU s/8 GiB. Keep failures and stop on a cap; do not rerun a cheaper preset or hidden prefix.

Bind executable/DLL/map hashes and all ordered input filenames/sizes/mtimes before starting; whole-file input hashes can be made once by streaming reads if root wants stronger current-byte provenance. Capture full command/env, whole-process elapsed/owned CPU/peak job commit through writer completion and whole-output/pixel hashes after completion. Native uses an existing solved map, while fork alignment is included in its render. Lightroom development time is unavailable. Report those scopes separately; two outputs cannot establish a robust speed ranking. The intended result is two current photographs and a short, actionable visible-gap diagnosis.
