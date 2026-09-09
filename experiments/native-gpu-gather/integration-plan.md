# Conditional native integration check

Source-only recommendation; no RAW decode, render or timing run here. Proceed only after all18 fixed controls pass, actual adapter eligibility is established, and the native dispatch is implemented and reviewed. The optional crate currently supplies a prototype; a production CPU/GPU environment switch is not yet an established interface.

Reuse `experiments/native-probe-fill/run-native.py` (current SHA256 `b07277d96be60da9479ed478cbd4358f28c591b96e6bdb194e43629f72f8f9ca`). Its bounded process execution, fresh-directory receipts, input checks, TIFF reader and exact payload comparisons already exist. A small explicit arm extension is needed: the current script hardcodes historical executables/output directories and cannot be rerun unchanged for this candidate. Use one new executable for every CPU/GPU arm; keep saved historical TIFFs as independent anchors.

## Smallest existing native population

First use `experiments/native-pyramid-profile/native-plan-1.json`, SHA256 `947b7fba499cf493d19c1c73f1374693256517983909b84e262d4312958ccf29`: exactly `D:/personal/macro/112MSDCF/DSC00001.ARW` through `DSC00008.ARW`,296701952 bytes. This eight-frame prefix already has a matching map and final baseline; trimming it again would require a new map/identity and would lose the saved whole-output anchor.

Map: `experiments/native-pyramid-profile/native/112-eight.warpmap.json` (the contents are the existing text warp-map format), SHA256 `1bc98923196b82699eb62b35bbed7c2b9c7e37b5f4cec9140703c6155050dddc`, plane3516x2344, reference4, ordered identity `5a10ff5ae055e578`.

Held112 baseline: `experiments/native-pyramid-profile/native/1-off.tiff`; whole SHA256 `ba96c63dd56f2729ba2ed25fedc19b291a4a78f9992f6823ce501a1df2a8bdc6`, decoded uint16 RGB SHA256 `d5fd6969b77fc94334995dea771e434f65f2b3cf782e1d683ca2872639595a1a`. These hashes are read from saved receipts, not recomputed from image pixels in this review.

One early integration matrix: CPU/GPU on this same prefix with `STREHL_DIRECT_PLANES=off`, then CPU/GPU with `STREHL_DIRECT_PLANES=rounded`: four outputs, no new frames. Both dispatches matter: `load_frame` calls `warp_frame_in_place` for ordinary remosaic, but rounded mode enters `warp_frame_fullres_into_planes` first and bypasses that call. A GPU hook only in remosaic silently misses the rounded consumer. Require actual route liveness plus exact output against the fresh CPU arm and the held112 anchor. Tiny generated controls alone do not establish native beta or delivered-image identity. Float mode is outside this u16-equivalence allocation.

## Existing full-stack speed population, only after exact integration

Use `experiments/native-probe-fill/transfer-plan-109.json`, SHA256 `3eb75cb702755104623047a38a1a2c13c270681aec7fd1d8a810e0b824f3be59`: all22 originals `D:/personal/macro/109MSDCF/DSC00009.ARW` through `DSC00030.ARW`,836440064 bytes. Its input records already hold individual SHA256,size,mtime. Map `experiments/M-PHASE0-PHASE/out/canon/109MSDCF.warpmap.txt`,3438 bytes,SHA256 `c29cab9c6f944f4d03c4402998e54aad4d4221cc450ac4bef42a453de848434d`, reference11, ordered identity `b70554b8cfd9b93e`.

Held109 anchor: `experiments/native-probe-fill/transfer-109/1-old.tiff`; whole SHA256 `84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851`, decoded SHA256 `1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1`. Native writeback and rounded-direct receipts independently retain those same hashes. Every output is7032x4688 RGB16,197798267 whole-file bytes and197796096 decoded bytes.

Then one CPU/GPU/GPU/CPU sequence on109, same executable and fixed `STREHL_DIRECT_PLANES=rounded` throughout. This compares GPU acceleration against the existing exact rounded option; it does not assign the separate rounded benefit to the GPU. Preserve each whole-file/decoded hash and complete-process wall, ownedCPU, peak job memory and host-load receipt. Report both order comparisons and per-arm minima; no historical percentage multiplication, stitched phase minima or timing claim from this memo.

## Established settings and integration constraints

Reuse each plan's exact command: `stack <dir> --limit 8|22 --merge pyramid --pyramid-bands 7 --pyramid-gate 2 --pyramid-exponent 2 --pyramid-sharpen 1.4 --pyramid-select soft --pyramid-base mean --demosaic --resampler catmull-rom --cover scale --out <fresh TIFF>`. These are camera-linear RGB16 baselines, not the later sRGB product preset.

Existing environment is `RAYON_NUM_THREADS=8`, `STREHL_ALIGN=1`, `STREHL_PYRAMID_WORKERS=8`, `STREHL_WARPMAP=<held map>`, and `STREHL_PYRAMID_PROFILE=on` with a fresh `STREHL_PYRAMID_PROFILE_OUTPUT`. Clean unrelated STREHL/thread-library overrides as the current runner does. Retain current green-probe, parallel-fill and parallel-writeback defaults. Name the future GPU switch only once its actual dispatch is implemented; a requested flag alone is not route evidence. No new solve, exposure, defect, confidence, restoration or private noise fit.

Keep one reusable GPU context on the existing serial canonical fold; one original u16 frame and its temporary MHC planes at a time, dropping them before the next frame. The current library already uses32-row coordinate/output strips; never retain reconstructed RGB for the whole stack. Check native limits BEFORE RAW execution: a7032x4688 RGB f32 buffer is395592192 bytes and must satisfy the actual adapter's storage-binding/buffer limits. Tiny controls do not prove that. Preserve exact f64 geometry preparation, host inverse-WB and packed u16 readback; charge startup, packing, transfers, synchronization, scattering/extraction and writer completion in process time.

Reuse existing per-child ceilings:180s wall,900s ownedCPU,8GiB committed,2MiB log; eight proposed outputs fit the existing2GiB retained-TIFF ceiling. Those are stopping bounds, not predicted costs. If full-size buffers are ineligible or any native byte differs, retain the specific refusal/mismatch and stop the speed comparison; do not silently fall back or relax equality.
