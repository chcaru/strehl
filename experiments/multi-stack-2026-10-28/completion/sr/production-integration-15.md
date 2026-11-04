# Original-CFA integration checkpoint15

VERIFIED source/control checkpoint, not a completed photographic outcome. Product15 archives1517 implementation files after the successful194.778s CLI/UI build. CLI SHA256 is2db1cea7daf3019185959719c15461c32a80c4535942c9913833ce7323ca69fb; UI SHA256 is5ac09d051022aa78ff1dfb1e7d462871fcaa017c70eec6dbc0610d0a15df4160. Complete build/source bindings are in outputs/multi-stack/completion/product-15/build.json and implementation-source.zip. The ordinary path does not invoke these optional consumers.

## Corrected geometry and original evidence

The direct global registration API now rejects malformed original windows (outside64..192quad or nonfinite center), overflowing/out-of-bounds original crop rectangles, and bitmask padding that names nonexistent original sites. This does not alter measured192quad evidence. The real-signal commissioning example passed38/38 after adding adversarial public-API window/crop controls; full command and immediate status are retained in sr-global-domain-controls-01. Earlier empty/missing-mask, cross-pair overlap and original held-photon replacement controls remain active. The mask-tail check is a structural guard; the current production192quad windows have no tail bits.

## Appearance admission

The previous production motion gate used only green even though reconstruction replaces all three colors together. A red-only or blue-only appearance change can preserve green and normalized geometric correspondence. The new helper uses the minimum confidence across red, averaged green and blue, each in exposure-normalized camera DN, against the same independent guide originals. It retains the existing radius3 (7x7) spatial box filter, uses each color's injected noise model and frozen color-gradient allowance, and bounds averaged-green variance conservatively by max(G1,G2). The guide variance is the sum of individual gain-squared variances divided by guide-count squared. Neither filtering nor source count is described as extra independent photons.

Flat-noise and exposure-normalization controls pass. An actualu16 original CFA plant with nonzero corrected placement retains its unchanged colored edges; isolated red and blue appearance changes refuse while both original green planes remain unchanged to sampling roundoff. The independent read-only review found no blocking mapping/gain/variance error and requested the additional blue-original witness, which was included before the final session test/build. Admission remains adaptive; these controls do not establish unconditional output variance or a photographic improvement.

Exact receipts retain two initial test compilation failures (import path and mutable sampler borrow), followed by15/15 passing reconstruction controls,17/17 after cache/planner controls, and the final129/129 CLI session controls including the blue-original witness. No failed command is counted as a pass.

## Original cache and worker cohorts

The earlier cache cap reserved only MAX_SOURCES plus guide handles for one tile, even when many workers and a larger memory limit were requested. Adjacent tiles could consequently form small cohorts and reread originals while memory remained available. MAX_SOURCES still limits each estimator to64 observations; it no longer caps the union of all concurrent tiles. The original-u16 cache now uses at most half the remaining memory and at most the complete session census plus one transient loading slot. Overflow and small-budget controls remain explicit. A varied two-pass source-union control verifies identical tile rectangles, source IDs, guides, skips and per-estimator bounds when only the larger cohort cache becomes available.

The producer now records cache disk/memory hits, peak resident CFA, cohort-size census and separate loading/compute/publication times. No aligned-frame volume is introduced. The first1024 complete records of the running14c baseline were frozen before any optimization timing, with an11,322,017-byte prefix SHA and a trace SHA c4b326742fe4de5bb4160ffcce8dececc8af2eaefc01e6fbc99aab434a7b3eb0. The bounded69/127/127/69-slot cache replay reads this same trace through the production cache loader and compares original observations. Its timing is preparation only and runs alongside other work; it cannot establish an isolated whole-render speedup. Full photographic and memory validation remains due.

MEASURED ABBA completed: preparation elapsed287.836/6.449/6.217/299.490s. The69-slot arms each read6498 verified cache payloads from disk and use253 cohorts (only nine full16-tile cohorts); the127-slot arms each read126 payloads once and use64 full16-tile cohorts. All four original-observation hashes are2b3014f1d1abaa4db733508f47c8b562a94a4676dd2c72cc093f5ea7c2f6cced, with zero RAW decodes. Actual peak resident CFA is4,549,310,208 versus8,307,436,032bytes; outer sampled private peaks are4.564GB and8.330GB. The resource receipts record concurrent work; the source/preparation result cannot be substituted for full-render speed or numerical-image equivalence. Failed harness compilation01/02 is retained before successful build03 (SHA1e146ffbc6fd0d0b6fcb5e9491ea43aa067c917a6d9c269773aff104909a03b6). Complete receipts are sr-cohort-cache-run-01..04 and sr-cohort-cache-abba-01.json.

Candidate15 was released after ABBA completed, with the same126 originals, native14c alignment,16workers/48GiB and photographic recipe as candidate14c. Its differences are all-color appearance admission, malformed-domain validation and original-cache scheduling. No threshold was fitted to its output; it must complete the same whole-photo/native-witness acceptance. The running14c remains a retained complete comparison, not a canceled slow arm.

MEASURED candidate15 completed1078.010s end-to-end with sampled11,736,682,496 private bytes under concurrent work. The original-CFA stage took749.379s:8.594s original loading,739.777s tile compute and0.488s tile publication. Its cache loaded all126 originals once, served38539 memory hits, decoded no RAW, and retained8,307,436,032 CFA bytes.449 cohorts contain16 tiles and the final cohort contains13. The total reserved working memory was15,076,544,400bytes. These measured whole-run numbers are not an isolated ABBA throughput claim;14c is still running under its original smaller cache and older color gate.

VERIFIED complete native/output readback (`sr-chart-full-readback-15.json`): both6928x4620 TIFFs contain only finite values.149759 of32007360 RGB pixels have coherent support;149636 actually differ from native in both the float master and16-bit photograph. Every unsupported pixel is bit-identical to native. All support/reason maps and tile receipt hashes agree with the producer, their source identities and saved warp match native14c, and all reason census counts reconcile. A4096-tile prefix comparison (`sr-registration-comparison-15-prefix.json`) also verifies unchanged original selection, graph witnesses and exact consuming-pull bits across14c/15, including2947 witnessed tiles; only timings, sampler-memory peaks and intentionally changed replacement counts are excluded. None of these mechanics establish added optical resolution or photographic usefulness. The independent full-image/frozen-witness review remains the acceptance step.

## Native baseline preservation

MEASURED/VERIFIED complete native14c is byte-identical to HDR precision03 for photograph.tiff and master.tiff. Source-identities.json, calibration.json and photometry.json are also byte-identical, and serialized warpmap equality passes. Recipe bands/gate/exponent/sharpen/resampler/precision focus agree; workers changed8 to16 and memory limit32 to48GiB. Receipt sr-chart-native-baseline-comparison-14c-02.json explicitly records those differences. The initial comparison receipt used two absent top-level fields and is superseded by02's explicit recipe paths; no equality claim relies on absent values.

Native14c took330.085s with sampled9,628,233,728 private bytes, including fresh alignment under concurrent work. It is not an isolated speed comparison against187.455s HDR03. Candidate14c is still running and must finish, pass full-output binding/support checks, and receive whole-photo/native-witness review. Supported-pixel counters alone do not close the requested sampling outcome.

Commands actually run:

```powershell
cargo test --locked -p strehl-core --example session-reconstruction-global-controls -- --test-threads=4
cargo test --locked -p strehl-cli --lib session_reconstruction -- --test-threads=4
cargo test --locked -p strehl-cli --lib session_ -- --test-threads=4
cargo build --release --locked -p strehl-cli -p strehl-ui --bin strehl --bin strehl-ui
python experiments/multi-stack-2026-10-28/completion/sr/compare-native-baseline.py outputs/multi-stack/completion/hdr-precision-03 outputs/multi-stack/completion/sr-chart-native-14c outputs/multi-stack/completion/sr-chart-native-baseline-comparison-14c-02.json
```

Each build/test used GIT_WORK_TREE for this isolated checkout and CARGO_BUILD_JOBS=4; run-command receipts retain host load and process resources. Native filesystem publication controls use elevated execution after sandbox AccessDenied failures; the failures remain recorded.
