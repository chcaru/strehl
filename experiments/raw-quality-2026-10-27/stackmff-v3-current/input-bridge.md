# Retained developed-image input bridge

2026-10-27. **VERIFIED manifests and source; execution UNVERIFIED.** Use the existing 299 unaligned RGB16 TIFFs through one bounded consumer-tile gather. No RAW development, additional corpus export, aligned full-frame stack, training or upload is needed. This is an external developed-image comparison; it does not satisfy or replace the original-CFA reconstruction contract.

The old [V4 result](../../stackmff-v4-evaluation/results.md) concerned three marigold sources and hard selection. Its rejected patch seams constrain interpretation but do not establish the behavior of this newly pinned V3 soft fusion on a complete insect stack.

## Frozen inputs and development

| Artifact | Identity |
| --- | --- |
| [299-TIFF export receipt](../../../outputs/raw-quality-2026-10-26/weevil-107-tiff-export/receipt.json) | SHA256 `461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0` |
| [Original order](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/input-order.json) | SHA256 `0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f` |
| [Held CA-off map](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off-alignment.txt) | SHA256 `4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225` |
| Common sRGB ICC | SHA256 `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b` |

Files are `weevil-107-tiff-export/frames/DSC00001.tiff` through `DSC00299.tiff`, ascending ordinal 0..298. The receipt pins every complete file hash, size and original identity. Each is uncompressed, interleaved RGB16, 7032x4688, 197,801,325 bytes; original active origin is (0,0). The established [source-view helper](../weevil-through-focus-support/export-source-views.py) already uses read-only `tifffile.memmap` on these files.

These are **toned and sRGB-encoded**, not linear sensor data. The retained native exporter used original MHC, WB [1637/1024,1,2774/1024], levels [512,15360], decoder D65 matrix, exposure 1 and the rounded logged tone [-0.00026,0.27030,0.55], before external fusion. No CA warp was applied. The TIFF bytes retain that prior development and its quantization/clipping; a new comparator cannot recover information it discarded. Native reconstruction applies development at a different point, so this is not a pure merger-only comparison.

## One coordinate and memory route

The [input bridge](input-bridge.py) returns RGB uint16 `[299,h,w,3]` for one requested in-canvas rectangle. For delivered pixel (x,y), set p=(x+68,y+46), C=(3516,2344). The held guide-map complex coefficients give the pull `q=C+a*(p-C)+2*b`. This is the current CPU full-resolution CA-off gauge in `align_cmd.rs`; do not add the research helper's half-pixel center adjustment or coerce source149 to exact identity. Output remains the complete native 6896x4596 crop.

For each source, compute only the bounded f64 coordinates, convert the remap coordinates to f32, copy the minimum source ROI to f32, and call `cv2.remap(INTER_CUBIC)`. Clamp to [0,65535], round with `floor(value+0.5)`, store the tile as u16, and release that source mapping/ROI before continuing. OpenCV cubic interpolation is explicitly distinct from Strehl's Catmull-Rom arithmetic; the claim is the same coordinate gauge, not pixel/kernel parity. Source storage stays RGB; the model adapter must use RGB-to-gray or explicitly reverse to its upstream BGR convention.

The model author's fixed proposal uses core256, halo128 and context512 on its global padded lattice. `tile_spec` requests only the needed in-canvas `read_rect`; the model adapter owns faithful global padding and the two scale phases. The bridge never pads each internal tile or combines scaling with the geometric pull. Its upper safety bound is 1024-square; the current model context uses at most 512-square. A 299-source 512-square u16 tile occupies 470,286,336 bytes; a 1024-square maximum occupies 1,881,145,344 bytes, before model tensors. The complete RGB16 output occupies 190,164,096 bytes. Model feature/device memory remains subject to the separate actual cost run.

## Callable contract and checks

`load_manifest()` validates small pinned records and source order; `check_headers(ctx)` validates every header, literal ICC, memmap layout and four-corner full-canvas source support. Affine extrema make four corners sufficient for the fixed crop; no full coordinate canvas or pixels are read for this preflight. `gather_tile(ctx,rect)` requires that preflight. `ctx.icc` becomes available after headers, and `ctx.metadata` records development, map, coordinate and resampler facts.

`hash_inputs(ctx)` and `verify_inputs(ctx,before)` are explicit root-scheduled full sweeps, never per-tile work. The retained set is about 59.14GB, so before/after hashing reads about 118.29GB per actual job. Overlapping tile gathers add I/O and repeated context; neither source size nor a single-tile inference time proves full-workflow speed. Root's current worker makes both sweeps in cost and full modes. Its tile-only projection must be distinguished from header/hash/startup/write overhead.

`coordinate_controls()` uses continuous labeled RGB ramps through the producing remap path. Exact integer identity, native crop offset, translation, literal nonunit scale/rotation coordinates and tile partitioning must pass. A wrong half-pixel center and RGB/BGR grayscale swap must change the result. These are geometric/channel checks, not image-quality evidence. No actual source or control was executed by this author; only AST parsing passed.

Frozen bridge SHA256: `306f87d6d5ffd2de997cbe4743b7c8d3c238faffbb18324a4e1785f22be2da0c`. Root's worker/runner call signatures match this contract. Full publication still requires all 299 sources, complete output/master, common ICC/display, the fixed ten native witnesses and independent photographic review; no improvement is claimed here.
