# Complete-stack source prior observation

This is a new photographic observation of the unchanged cross-scale source prior. The retained generated screen fails general quality qualification; its `photographic_replay_admitted=false` remains false, with all real thin-detail and glint counterexamples retained. A successful run does not imply a default change, general safety, SOTA, or an improvement. Root authorized this limited question after the full-chip observation. Complete photographs and preserved genuine source structure decide usefulness.

## Consumer and exact baseline

`adapter.rs` is included only as `merge_cmd::full_stack_source_prior` under the existing test/GPU/direct-plane/correction-variance feature guard. Explicit JSON supplies the complete ordered originals, original SHA256/length and map identity names, complete retained map/reference, expected actual common crop, camera/ISO and full delivered historical RGB16 baseline. Identity names allow original capture paths to replay a map whose original producer staged the same bytes under sequential names; original bytes are SHA256 checked before decoding.

No hard-coded chip frame count, chip crop or rounded tone constants survive. Dynamic `chunk_plan` is the current four-plane full-geometry planner, with original frame-count canonical boundaries and first-move/left-absorb arithmetic. All source indices are used in full mode. The cost phase uses exactly reference-1/reference/reference+1 but probes those sources with their original indices and full stack count.

First pass calls actual BandWorker::fold with injected profile, normal composed optical CA, rounded native GPU gather, green probe, unchanged map and crop. The historical whole RGB16 pixel hash is required before second-pass candidate work. `write_merged(Merged::Bands, ..., Srgb, true, Exposure::resolve(true, requested_stops, false), None, path)` is the actual product writer. It resolves automatic tone from the complete collapsed image; no logged rounded constant is used. Candidate uses the same automatic policy and requested exposure, so any exact automatic-tone difference is part of this full-workflow comparison, not falsely described as fixed anchors. Writer-only experiments can use the cached same current planes to isolate rendering separately.

The existing all-twelve-site support diagnostic is reported only. It does not inset or replace the user's actual product crop, and no zero unsupported-sample claim is made. Actual BandWorker boundary policy is unchanged.

## Unchanged prior and bounded storage

First pass accumulates canonical finest weights in original source order into one f32 denominator. A separately checked constructor permits at most 1024 sources and at most 3516x2344 quad pixels, with checked multiplication and exact existing seven-band dimensions. The retained generated and fixed-chip constructors are untouched. A small constructor test compares the new denominator and reduced support bit for bit with the existing constructor on mixed supported/unsupported pixels; it also rejects invalid extents/counts and incomplete input.

Second pass repeats the actual worker. Per-source active u16, known4, green, variance, beta, energy, floor, canonical weights are bound to the first pass. Existing `SourcePrior::source/apply` is reused, unchanged: normalize finest weights across sources before Gaussian reduction; multiply only coarser AC weights; preserve finest weights, terminal mean, zero-denominator fallback and input-range hull. Per-frame/chunk and final held accumulator equality are asserted; repeated current collapsed planes must hash-identically to first-pass current. Frame storage stays u16; f32 current source and sufficient-statistic buffers are bounded. No N-aligned-frame volume exists.

`mode=current` retains the one-pass actual baseline/cache and exits, for independent writer work. It does not run or claim a source-prior candidate. `mode=prior` completes both passes and retains both full masters.

## Cache handoff

Each arm writes one plane-major little-endian f32 file, order R/G1/G2/B, each plane exactly crop.width*crop.height. It is the signed collapse output **before** Merged::value's max(0), writer WB/exposure/matrix/tone/demosaic. Only two final merged objects are cached, not per-frame volumes. Each object is about 100 MB at these output sizes.

`baseline-cache.json` and `candidate-cache.json` contain schema, full geometry, crop, levels/WB/matrix/exposure exact f32 bits, matrix source, tone policy, complete source count/reference/map and ordered-input digest, phase, arm, binary basename/length/hash and every plane hash. `read_cache` rejects bad dimensions/count/reference/phase, nonfinite values, bad lengths/hash and invalid metadata. A cost cache is explicitly marked `phase=cost`; it is never a full-source cache. The writer replay requires `phase=full` and exact baseline agreement independently. No original RAW is needed for that replay.

## Root execution and resource gate

Author does not compile or execute this adapter. Independent reviewer reads the actual code and root runs it. `runner.py build` requires fresh CLI and core compilation, binds include sources and driver, and retains binaries. `controls` requires semantic JSON identity with the retained failed twelve-case screen, and the new constructor test. It never changes general quality admission to true.

Cost execution: 24 GiB job cap, 300 wall seconds, 1200 CPU seconds. Full execution: 24 GiB, 1800 wall seconds, 12000 CPU seconds. Admission is resource-only: `1.25 * full_count/3 * measured_variable_source_seconds + observed_fixed_seconds + 120 <= 1500` and cost peak below 18 GiB. Variable time sums both actual per-source loop timers plus the first decode; fixed time excludes that variable work, avoiding multiplying one-time allocation/hash/write setup by frame count. This extrapolation is not a guarantee or speed claim. The triple's coarse prior has three sources, so its image is not quality evidence.

Commands (root substitutes fresh output names and an explicit recipe):

```
python -I -B -X faulthandler experiments/full-stack-source-prior/runner.py build --out experiments/full-stack-source-prior/build-1
python -I -B -X faulthandler experiments/full-stack-source-prior/runner.py controls --build experiments/full-stack-source-prior/build-1 --out experiments/full-stack-source-prior/controls-1
python -I -B -X faulthandler experiments/full-stack-source-prior/runner.py cost --build experiments/full-stack-source-prior/build-1 --screen experiments/full-stack-source-prior/controls-1 --recipe RECIPE.json --out experiments/full-stack-source-prior/subject-cost-1
python -I -B -X faulthandler experiments/full-stack-source-prior/runner.py full --build experiments/full-stack-source-prior/build-1 --screen experiments/full-stack-source-prior/controls-1 --recipe RECIPE.json --cost experiments/full-stack-source-prior/subject-cost-1 --out experiments/full-stack-source-prior/subject-full-1
python -I -B -X faulthandler experiments/full-stack-source-prior/runner.py views --build experiments/full-stack-source-prior/build-1 --screen experiments/full-stack-source-prior/controls-1 --run experiments/full-stack-source-prior/subject-full-1 --out experiments/full-stack-source-prior/subject-views-1
```

`views` creates complete max-1617 neutral ICC-preserving previews and links full-resolution masters. Fine visual judgments require separate unresampled tiles no larger than 400 pixels per AGENTS; previews establish whole-image appearance only. Marigold witnesses are already recorded in `experiments/quality-september25/marigold`, including a withdrawn gross-placement hypothesis and explicit uncertainty about actual occlusion excess. Neither a cleaner smooth region nor reduced highlight clipping alone earns quality acceptance.
