# Native GPU coordinates: exact output with a measured rendering gain

MEASURED / independently VERIFIED on the RTX 5090: the current native RAW renderer takes 8.172 seconds with Device256 versus 11.203 seconds on the CPU, using the minimum of two runs per mode in CPU/GPU/GPU/CPU order. That is a 27.0553% reduction in whole-render elapsed time on the 22-frame 109MSDCF subset. All four complete TIFFs and decoded RGB16 images are identical. Even the least favourable pairing gives a 26.0734% reduction.

This supports moving coordinate construction and its transfer to the GPU. The earlier version made coordinate plans on the CPU and uploaded 527,456,256 bytes per RGB or green-probe call, about 1.055 GB across both calls per original frame; its elapsed-time result was near-flat. Device256 makes those plans on the GPU from 96 bytes of transforms per call. The experiment does not isolate transfer cost from CPU coordinate construction. The protected f32 reconstruction/gather shader and native image algorithm are unchanged. One original CFA frame is consumed at a time. Native RAW input, active-area handling, injected noise, camera white balance and channel geometry are retained.

## Executed work and evidence

The implementation is bound to revision 36b91f0e5ced8f09c37d0325c987fe55e4e652cb and the 32 source bindings in build-native-6/invocation.json. The executed native binary SHA256 is 2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7.

Commands actually run, from the repository root with the recorded Python 3.12 interpreter:

~~~text
python -I -B experiments/native-gpu-gather/preflight.py
python -I -B experiments/native-pyramid-profile/build.py --gpu-gather --output-dir experiments/native-gpu-gather/build-native-6
python -I -B experiments/native-gpu-gather/run-device.py
python -I -B experiments/native-gpu-gather/run-device-native.py
python -I -B experiments/native-gpu-gather/run-device-native.py --timing-109
~~~

See [independent controls](device-controls-results.md), [independent native results](device-native-results.md), and [independent constructor preflight](device-preflight-results.md). Reports and process receipts remain alongside the commands; image files and executables remain local with content hashes.

All 192 coefficient guard predicates, the literal intermediate-underflow witness, four paired fallback/device images, 37 independent descriptor requests, four API refusals, and the original 18 CPU/GPU image controls pass. Boundary and rounding cases exercise actual discontinuities. Mutated coordinates and coverage are live falsifiers. An unsafe coefficient uses the existing CPU coordinate planner; the next safe request on the same context returns to Device256. The unchanged strict f32 image module is used in both routes.

The RTX 5090 does not advertise f64 denormal preservation. The admitted finite nonzero transform coefficients are at least 2^-900 in magnitude; the specific half-integer multiply/add/subtract coordinate graph then cannot produce a subnormal intermediate. RTE32/RTE64 and SignedZeroInfNanPreserve64 remain required. This is a domain restriction with an explicit fallback, not a claim of general IEEE arithmetic on that hardware. Naga validates the original coordinate module; the final float-control patch has structural/removal checks, not full patched-module Naga or spirv-val validation.

Three 8-frame 112MSDCF renders with numeric logging off, on and fixed placebo preserve the retained CPU whole-file and decoded hashes. They establish observer nonperturbation. Their 3.969/3.797/3.813-second observations are not a CPU/GPU timing comparison.

## Measured 109 comparison

| Actual order | Whole-render wall seconds | Child CPU seconds | Peak job commit bytes |
| --- | ---: | ---: | ---: |
| CPU | 11.219 | 67.718750 | 2,997,854,208 |
| GPU Device256 | 8.172 | 28.390625 | 3,516,743,680 |
| GPU Device256 | 8.282 | 29.343750 | 3,552,227,328 |
| CPU | 11.203 | 66.750000 | 2,997,579,776 |

DERIVED: forward/reverse reductions are 27.1593%/26.0734%; per-mode minima give 27.0553%. CPU endpoint drift is 0.016 seconds. Combined gather and noise-probe work takes 7.1030-7.1116 wall seconds on the CPU and 4.1081-4.2084 in the Device256 route. Decode differences are only 0.0074-0.0346 seconds, so they do not explain the roughly three-second gain. Startup, RAW decoding, packing, GPU transfers/synchronization, merge and TIFF writing are all included. The existing saved alignment is loaded; solving alignment is excluded.

Every GPU render uses Device256 for all RGB and green-probe calls: 136 actual calls across the five new GPU renders, with no fallback. All seven new images are 7032x4688 uint16 RGB and preserve their retained CPU anchors. The 109 complete TIFF SHA is 84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851; decoded SHA is 1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1.

Elapsed-time measurements can be fooled by order and system load; both directions and the least favourable pairing retain the gain here. Two samples per mode are not a population confidence interval. Exact image identity cannot establish image quality: it preserves the baseline's strengths and defects. No sharpness metric is offered as quality evidence.

## Cost and decision

The seven new renders cost 50.455 summed wall seconds and 230.40625 child CPU seconds. Separately, the fresh full build costs 137.422 wall / 273.328125 CPU seconds; constructor preflight compilation costs 24.406 wall / 45.46875 CPU, and its runtime 0.578 wall / 0.40625 CPU. The fixed controls use 1.719 summed wall / 0.921875 CPU seconds. Earlier hardware, storage-interface and extension refusals are preserved as failed attempts in their own reports.

The GPU uses about 0.52-0.55 GB more peak job commit in the 109 comparison. Child CPU work falls 57.4672% by per-mode minima; this is neither energy consumption nor GPU work. Twenty retained native TIFFs total 3,955,965,340 bytes and represent repeated executions of two subsets, not twenty scenes.

Retain the optional implementation. GPU enablement and Device256 selection remain explicit; no production default changes in this milestone. The finite result is useful rendering acceleration without pixel changes on these inputs. Full-stack output transfer is separately commissioned in execution-coffee.md. General alignment, photographic detail, other hardware, default promotion and a fair competitive SOTA comparison remain open.


## Complete 105-frame output transfer

MEASURED separately after source freeze 5c9b70e074a0aff2a899ce13c7eadc06b4bbf593:

~~~text
python -I -B experiments/native-gpu-gather/run-device-coffee.py
~~~

The saved coffee-bean invocation consumed all 105 originals DSC00016.ARW through DSC00120.ARW, with unchanged saved geometry and rendering settings. One render completed in 34.734 wall seconds / 129.328125 child CPU seconds, peak job commit 3,359,776,768 bytes. All 105 RGB and 105 green-probe calls use Device256; all 210 numeric call records and actual completion markers agree, with no fallback.

The cropped 6784x4524 sRGB uint16 output has decoded SHA e6c8d7ada22b7bd0f944bf8e554600d6c209f37e80dad1e35aa0968c5c8664cb, exactly matching the held CPU photograph. All TIFF tags, including ICC and strip layout, match except Software, which changes from the older build stamp to the independently bound current stamp. Zeroing only the same 28 Software bytes at offset 3360 gives equal whole-file SHA 025499c15cb975393dc7877dc7ab38333eba551829738717b27f8ef5d333ad4c. Thus no unexplained pixel, metadata or container change is excused. The new unmasked file SHA is c72d51b814144514bb1d268a3b7526e1766b60dd6c4e6954483e9f7f1f0b03c0; whole-file byte equality is not claimed.

Original file-set membership, size/mtime records, saved map, baseline image, compiled source and executable bindings remain unchanged before/after. This is a selected-input check, not a global corpus audit. Total retained native TIFF bytes are now 4,140,115,310 across 21 executions of three distinct stacks/subsets, below the fixed 4 GiB bound.

The older 105-frame CPU output came from a different binary and historical run order. Its runtime is not a speed comparator for this trial. This completes the allocated full-stack output check; it does not improve the photograph's baseline alignment or establish competitive quality.
