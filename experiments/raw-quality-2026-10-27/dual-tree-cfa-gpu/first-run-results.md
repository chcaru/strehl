# First GPU run: numerical qualification refused

2026-10-27. **VERIFIED from retained receipts, not a photographic result.** All planned generated cases and foils finished, but the frozen CPU/GPU coefficient and energy tolerances are violated. `mechanical_pass=false` is correct. Hold the RAW cost checkpoint and full299 run; do not relax the guards or use good output agreement to erase the stage failure.

Root actually ran `outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-build-1/cli-tests.exe merge_cmd::dual_tree_cfa_gpu::independent_controls::generated_controls --ignored --exact --nocapture --test-threads=1`. Executable SHA256 `84b8a52c6027179fd7808f70ceceed721437d26ec3e670146e2beacc9b7ae8a7`. It ended with the intended assertion refusal, exit101 after87.047s, without timeout or cleanup error. Peak job commitment was2,726,502,400bytes. All14 CUDA worker/bridge pairs have complete terminal receipts; peak reported Torch allocation/reservation was14,915,072/35,651,584bytes. This small-case process time includes repeated interpreter sessions and is not a full-workflow performance result. [Invocation](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-screen-1/invocation.json), [process](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-screen-1/process.json), [screen](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-screen-1/output/screen.json) SHA256 `3cf1bc86bb0e133401a13d6e9efe8b6a0edb11d6e672da96587446ad12f198a4`. A successful root completion receipt was correctly not produced.

## Where the fixed agreement contract fails

The two signed/high-DN rectangle inputs fail coefficient agreement on all four repeated forward calls each. These are eight failed calls, not eight independent scenes. All six angular forward calls pass. Coefficient failures concentrate in coarse AC bands; for the64×56 fixture, band41 (last level, HH−) has max0.168457DN and RMS0.126962DN versus its frozen RMS limit0.015486DN; its worst pointwise tolerance ratio is1.559. This is an actual declared-bound violation, not merely a different file hash.

All42 ordinary source-stage observations fail their combined stage check. The components show the scope:

| Producing stage | Passed sources | Failed sources | Meaning |
| --- | ---: | ---: | --- |
| Smoothed energy |28|14|All21 failing band observations are indices36–41, the seventh AC level.|
| Noise floor |42|0|Worst pointwise tolerance ratio0.5412; no failed floor comparison.|
| Raw weight |42|0|Largest log1p max/RMS errors0.000910/0.000849, within0.02/0.002.|
| Phase0 signal coefficients |1|41|Only the constant singleton passes all its coefficient/LL guards.|

The constant singleton is a useful direct example: energy band39 differs by0.031288 in squared-DN/WB units,2.877 times the permitted pointwise bound. It nevertheless has zero selected weights and a passing final reconstruction. The replayed CPU energy/floor/weight hashes match the frozen consumer's actual stage hashes, so this comparison did not silently substitute a differently computed CPU reference.

The coarse-level concentration is consistent with accumulated reduction/cancellation differences, but this report does **not** establish that cause or assert harmlessness on299 sources. A source correction must be tested against the same frozen limits; no wider threshold is proposed.

## What did pass, and its limits

All ten ordinary consumer comparisons pass CPU/GPU pre-hull, delivered and uniform-output limits. Worst pre-hull max/RMS errors are0.005859/0.001738DN, well inside0.10/0.02DN. All supplied-coefficient inverse comparisons pass. Each GPU's own signed transform null remains inside the original0.05/0.01DN limits (worst0.015625/0.006971DN); actual singleton and mean nulls also pass. The six-direction commission and one-sided phase/direction/scale foils pass. Altered-bank and actual five-source floor×2 foils are rejected correctly, with nonzero selected weights present. Canonical output is identical between paired runs, and the eight CPU canonical/candidate images reproduce historical hashes.

The inherited quality outcome remains six passes/two failures: independent-color green error and glint error still fail. Existing complete generated outputs remain saved as50 PPM panels plus float arrays, including the wrong-floor pair. This review reads saved measurements only; it adds no image transformation, model execution or fresh visual quality claim. Tiny canonical two-level versus candidate seven-level comparison, weak-green eligibility and simplified unsaturated-glint limitations remain unchanged.

There is no full-stack GPU candidate or photographic improvement to interpret. Presentation scripts remain prepared, not executed. The failed first run and its sources/receipts must remain available alongside any separately recorded implementation correction.
