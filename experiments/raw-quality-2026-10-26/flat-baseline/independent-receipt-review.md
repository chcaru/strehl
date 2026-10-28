# Independent flat1s receipt review

**VERIFIED, bounded to retained receipts/source and TIFF headers:** this is a complete normal-baseline render of all 60 ordered sources. It is suitable for the separately commissioned whole-photograph review. It establishes neither improvement nor correct placement. No RAW read, pixel decode, fit, build or rerender was performed for this review.

The root's executed wrapper commands are recorded in [the campaign results](../results.md):

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-baseline/inspect-headers.py
python -B -X faulthandler experiments/raw-quality-2026-10-26/render-cpu.py --input D:/personal/macro/requests/misc-diagnostic/high-res-calibration-slide-cpl/flat-sw4-cpl/flat-et1s-sw4-cpl --out outputs/raw-quality-2026-10-26/flat-1s-baseline --exe outputs/raw-quality-2026-10-26/baseline-strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388
```

The exact child argument vectors agree between `invocation.json` and both process receipts. Each child exited zero, with null error, no cleanup errors, terminal job accounting, zero active processes, pipe EOF and no termination attempt. Independent read-only Python checks rehashed the executable, runner, helper, job harness, both logs, map and three optical-header JSON files; every retained binding matched. These checks also joined the 60 input-order entries to the metadata inventory and three sampled source identities. The review did not independently rehash original RAWs or full image payloads.

## Inputs, defaults and geometry

**VERIFIED:** `input-order.json` contains exactly indices 0–59, lexical filenames `DSC00016.ARW` through `DSC00075.ARW`. The header observations are indices 0, 30 and 59, not three adjacent captures. All report ILCE-7CM2 firmware v2.00, FE100mm Macro GM +2X, 200mm, f/5.6, ISO100, one second and coarse focus code57; recorded capture dates span 2026-09-02 20:28:39–20:30:05. These selected fields do not establish shutter mode, stabilization, WB mode, filter or illumination state for the older capture.

The frozen executable is SHA256 `89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388`, identifying itself as `0.1.0-alpha.6 (4813e46bdc9a-dirty)`. This review binds that executable, not the subsequently edited checkout. The runner SHA256 is `b9e424cd37fb99a681b710e0c8ab11c88ef39cf1fb53d89feb1dee840e0dacca`.

The helper clears inherited Strehl/thread-library environment overrides, then sets four Rayon/pyramid workers, alignment and full-resolution gather on; defect, temporal-energy and spatial-noise-floor interventions are off. The command specifies seven Laplacian bands, gate2, exponent2, sharpen1.4, soft selection, mean base, Catmull–Rom, crop cover and sRGB development. The log resolves **CA correction on**, matched profile `a7c2-fe100gm-2xtc-x4cpl`; ISO100 profile noise; black512/working-white15360. Native header white16383 and CA setting0 are separate header facts, not the applied working levels or a claim that production CA is disabled. The decoder's repeated missing-lens-database warning does not contradict the separately logged Strehl profile match.

Development uses as-shot WB (R2.7754, B1.5205), the decoder's D65 matrix and MHC demosaic. No exposure gain was applied; automatic tone **was** applied: black0.008842854, white0.36849296, contrast0.55. The float master is pre-tone BT.709/D65. A later comparison must retain this display contract or explicitly show a common alternative; the exposure log's word “faithful” is not evidence of color accuracy.

The fresh map lives under the output directory and is selected by `STREHL_WARPMAP`. Its 60 contiguous rows are all placed. Reference30 is `DSC00046.ARW`; placements map reference to frame in CFA-plane coordinates. The reference's stored bits are `3fefffffffffffff / 3be0000000000000 / bc80000000000000 / 3cb0000000000000`: numerical identity with roundoff, not exact bit identity. The map/log agree on Catmull–Rom and 3516×2344 planes. The crop `[25,17,3466,2310]` delivers **6932×4620** at decoded reference-native offset **(50,34)**, at unity scale. There is no coverage upsampling. The log records 297 accepted alignment edges and cycle floor0.116 plane pixels; held-out placement error is explicitly **not measured**. These diagnostics do not prove physical registration accuracy.

## Artifacts and limits

**VERIFIED from headers, without reading arrays:** each TIFF has one RGB page, 6932×4620, uncompressed, with every advertised strip within the file. The RGB16 master has a 2716-byte ICC profile; the float32 master has a 696-byte linear ICC profile and the stated pre-tone description. The runner itself decoded/validated the RGB16 master and checked the full JPEG dimensions and identical ICC before completion. The complete JPEG and masters represent the entire emitted crop; the overview is orientation only.

| Retained item | SHA256 |
| --- | --- |
| `completion.json` | `969bc19f2b608fcd2455a83b67c85898bf183d0afd4c8a138d1b333fc9ef8183` |
| `invocation.json` | `051189cf27e1ee2ceaea6396d11b958be9305fbc8e663fe175366a9c70755a8a` |
| `input-order.json` | `7a7f6474eca174c5dd9c9d4cabc6eb1ae15e8385c7395472a793175c59a107fe` |
| Metadata `receipt.json` | `6e04c0c1ef6bb3b4acb09b73f3be0557b3e288f58dc1ac52b5f5d1bdbfddef49` |
| Map, independently rehashed | `658501d70e5623b168bdee327219382952ca0887f5eafec4d02650343f0dd36b` |
| RGB16 master, producer binding | `01e576315fdf8242b9d008c06a0ad9b52f837f84d8d28e05d59d13b97379dbdc` |
| Complete JPEG, producer binding | `4be11fb457c957c542bf06d6c8e0c5204ce232073fc7d5be736ffdbfbd981093` |

The completion receipt follows a successful final comparison of all 60 original byte hashes, sizes, mtimes, filename list and executable binding. This supports **producer-verified unchanged originals**. It does not mean this reviewer reread those originals. Two modest receipt limitations remain: original preservation is checked after the render, rather than between alignment and dependent rendering as the brief requested; the fresh map likewise has no separately retained post-align hash. Also, the runner omits a float-master hash/readback from `completion.json`. The float file exists at 384,314,146 bytes and its header/strip layout is valid, but this review does not infer pixel finiteness or complete-payload identity from that. These are record limitations, not evidence of mutation or malformed output. A float binding can be added separately without repeating the stack.

**MEASURED operationally by root:** alignment30.031s, peak owned-job commitment2,316,210,176bytes; render67.172s, peak2,928,582,656bytes; metadata pass0.219s. Both stack phases used a24GiB commitment cap and3600s wall limit. They overlapped the four-worker/GPU weevil run (`green-phase-full-job-2`, exec session66504) on the32-logical-CPU host. These are neither clean throughput comparisons nor a competitive speed claim. No baseline quality conclusion follows from successful execution, the low cycle floor, numerical bounds or this receipt audit; [the independent photographic plan](photo-plan.md) owns the complete-image and native-witness judgment.
