# Fixed-domain photographic replay plan

2026-10-27. **VERIFIED source/provenance; proposed execution is UNRUN.** This is conditional on root releasing an actual candidate map after the phase controls. No RAW decode, build, alignment, render or export was run for this plan. A changed map is the only intended reconstruction variable. Neither the phase score nor a better-looking photograph establishes physical placement accuracy.

## Smallest reliable route

Reuse the **normal `BandWorker` arm and writer** of [green-phase/full-adapter.rs](../../raw-quality-2026-10-26/green-phase-guide/full-adapter.rs), in a small new root-built test adapter. Keep its fixed `PyramidDomain::cropped`, arithmetic chunk order, input-range hull, exact held development, master writer and complete baseline identity checks. Remove its two changed guide arms and their extra sixteen-draw guide-variance probes; preserve the canonical normal worker's existing gate-floor/probe path exactly. Do not run the old green-phase experiment. Feed the original and candidate isolated maps to otherwise identical normal workers. One sequential decode can feed both workers; never create an aligned source volume.

This is preferable to pretending the ordinary CLI already exposes a fixed crop and tone. The existing adapter itself hard-pins the old map and therefore cannot accept the candidate unchanged. The new adapter needs two explicit map paths/hashes, the held crop and its normal baseline/candidate outputs, not a new reconstruction or developer. Root must freshly bind/build this narrow adapter; there is no candidate-capable executable claimed here.

The precedent is substantial: the [complete299 receipt review](../../raw-quality-2026-10-26/green-phase-guide/full-receipt-review.md) records exact canonical CFA, RGB16 and RGB32 pixel parity with the retained CA-off run. Reuse the producing normal path, not that experiment's manual-gain common displays.

## Exact retained CLI reference

The executable exists at `outputs/raw-quality-2026-10-26/baseline-strehl.exe`, 13,239,296 bytes, SHA256 `89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388`. The [invocation](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/invocation.json) and [render wrapper](../../raw-quality-2026-10-26/render-ca-off.py) bind this actual command, with absolute output paths substituted below:

```text
baseline-strehl.exe stack D:\personal\macro\insects\bug-3\107MSDCF
  --merge pyramid --pyramid-bands 7 --pyramid-gate 2
  --pyramid-exponent 2 --pyramid-sharpen 1.4
  --pyramid-select soft --pyramid-base mean
  --srgb --demosaic --resampler catmull-rom --cover crop
  --out <fresh-output>/stack-master.tiff
  --linear-master <fresh-output>/linear-master.tiff
```

The clean environment is `RAYON_NUM_THREADS=4`, `STREHL_PYRAMID_WORKERS=4`, `STREHL_ALIGN=1`, `STREHL_FULLRES_GATHER=1`, and `STREHL_WARPMAP=<absolute isolated map>`. `STREHL_FIX_CA`, `STREHL_DEFECT`, `STREHL_TEMPORAL_ENERGY` and `STREHL_SPATIAL_NOISE_FLOOR` are `off`. There is no exposure argument: exposure gain is exactly1, with first-source as-shot WB. Preserve the fixed MHC choice and disable competing experimental environments explicitly.

`--cover crop` computes a map-dependent fusion domain; ordinary `stack` also measures automatic tone. Consequently this command is a reference/replay route, **not by itself the fixed-domain candidate contract**. A post-crop cannot undo a different pyramid domain. The existing `develop` command reads a linear master's own `DisplayBaseline`; its adjustment recipe does not override those anchors. Do not inverse-convert the saved BT.709 linear master to camera RGB: highlight processing has already occurred. The selected adapter avoids both problems by holding the domain and `Develop` before writing.

## Input, map and development contract

- Bind all299 original ARWs, lexical `DSC00001.ARW`–`DSC00299.ARW`, using the existing [input order](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/input-order.json), SHA256 `0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f`. Require exact ordered identities and hashes before/after, not only a source count. Decode with the unchanged native loader and inject its existing ISO100 profile once.
- The held map SHA256 is `4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`. Each map must identify the same stack,299 placed sources,3516×2344 guide geometry, reference149 and Catmull–Rom. Maps encode reference-to-source similarities in guide pixels; native units are twice guide units. Preserve the declared center and reference149's retained tiny roundoff bits. Any candidate gauge conversion must be explicit and commissioned; do not silently reset its anchor transform.
- Candidate pairs are direct fits globally solved in the connected anchor component, with every failure, unplaced source and cycle-rank result retained. This plan cannot admit fewer than299 placed frames as the same full-stack comparison.
- Keep **quad crop `[34,23,3448,2298]`**, native origin `(68,46)`, complete6896×4596. Apply it before plane extraction, focus energy, weights and pyramid synthesis. Check actual `full_source_supported` stencils for every source/map at this rectangle with CA disabled. If the candidate lacks support, explicitly refuse this fixed photographic comparison; neither black padding, dropped frames, a smaller crop nor a larger-domain render followed by cropping is an equivalent substitute. A different automatically suggested rectangle is irrelevant if the held rectangle itself is fully supported.
- Preserve seven AC bands, gate2, exponent2, sharpen-per-octave1.4, SoftPower/HardFloor, mean base/fallback, InputRange hull, mean-coarse0 and significance-scale0. Preserve four arithmetic chunks75/75/75/74 and accumulation order; four execution threads are not permission to reassociate the sum.
- Read exact display anchors from the held linear TIFF as the existing adapter does. [Held development](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-delivery-controls-2/output/held-development.json), SHA256 `26a441851ee4344c78d86ef1f8eeb39002acea01ba93b34319c60992e2a9c7c0`, records tone f32 bits `[3111042816,1049352204,1057803469]` and exposure bits `1065353216`. Bind its WB, levels and camera matrix too. Rounded log values are insufficient. The writer is the actual `write_demosaiced_with_master` path; no second WB/matrix, gain3.434 display substitute, extra sharpening or candidate tone fitting.

Both maps reside under fresh experiment output directories and are hashed before/after. Set `STREHL_WARPMAP` to an isolated map even if the test adapter directly loads both paths. Never call alignment without that isolation or write a capture sidecar. Normal rendering retains the legacy per-source MHC/Catmull–Rom/remosaic consumer; this trial does not fulfill the separate direct-original-CFA/demosaic-once architectural requirement.

## Baseline null and complete deliverables

The newly built adapter must reproduce the entire held baseline before any candidate quality statement. Require exact complete canonical CFA payload, RGB16 pixel and float RGB32 bit hashes, plus dimensions, ICC and material metadata. Historical expected pixel hashes are:

| Payload | SHA256 |
| --- | --- |
| CFA f32 DN | `1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0` |
| RGB16 pixels | `f98cb4d9bc281eb9f28f4e618878607d7e7317eeb7ac20b349f35dfee81c280c` |
| Linear RGB32 bits | `ee2b711bc36e48b9913531e1c615bd265ad06fd395a74f6224ca94392e32be09` |

The held [RGB16 master](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-master.tiff) file SHA is `5dc571cce0d9e310f1f06b6e7f3c78faae8fb4ee4f12c94ff76d1d0c0e3fb655`; [linear master](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/linear-master.tiff) file SHA is `8f3d9ec977f06d8fd44e070f27ab97e398611436cef17271fa6b889067ea1960`. File metadata may make a new TIFF hash differ despite exact pixels: record both without claiming file identity. Retain failed outputs and receipts if the null fails; do not visually promote them.

For each arm save complete RGB16 master, pre-tone RGB32 master, CFA diagnostic payload, complete-resolution JPEG and orientation-only overview. Reuse the existing readback/display pattern: single-page dtype/shape assertions, exact ICC SHA `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`, f32 finiteness, `(u16+128)//257` display conversion, JPEG quality98/subsampling0 and ICC. No resized crop may count as native evidence.

Extract every fixed384×384 witness from the [frozen manifest](../../raw-quality-2026-10-26/photo-review/baseline-witnesses.json), SHA256 `826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888`: background-black, dark-elytron, turquoise-scales, elytron-seam, bright-wing-rim, thorax-texture, upper-leg-hairs, blue-joint, upper-occlusion, eye-and-antenna. Preserve exact origins and lossless PNG/TIFF pixels. Publish an index linking both whole JPEGs and all full masters before crops, plus existing [native/B4/B8 mapped views](../weevil-fine-comparator/photo-review/mapped-witnesses.json). Vendor outputs keep their own alignment/scale and pre-merge RGB development caveat; they are workflow context, not placement truth.

Root owns the fresh build, bounds and release. Record actual command/environment, source/map/executable bindings, full299 consumption, terminal process/child accounting, elapsed and scoped memory. The historical229.532s CA-off render is only an operational reference, not a budget or exclusive speed ranking for a paired adapter. Require independent whole-image-first review of all ten witnesses: improved hair/scale/edge/tonal fidelity can be meaningful without new topology, but displaced contours, missing depths, altered iridescent color, coherent background artifacts or stronger glints remain regressions. No synthetic or local gain completes the goal.
