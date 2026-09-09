# Native RAW render time reduced without changing the image

MEASURED and independently reviewed,2026-09-09. Retain the parallel probe fill as the default. On the fixed first eight112MSDCF RAWs, minimum completed render time falls from8.110 to6.375seconds:21.39% less wall time, or1.272x throughput. Both timing directions agree. All five new complete7032x4688 RGB16 TIFFs and decoded pixel payloads exactly match the held original output.

| Run | Complete process, seconds | Combined probe, seconds |
|---|---:|---:|
| Original1 | 8.312 | 4.200 |
| Parallel1 | 6.469 | 2.368 |
| Parallel2 | 6.375 | 2.383 |
| Original2 | 8.110 | 4.272 |
| New binary forced serial | 8.265 | 4.311 |

The first direction improves22.17%, the reverse21.39%; medians improve21.79%. The explicit serial reversion recovers the old timing. This compares new timed runs against contemporaneous originals; it does not compare against the slower earlier morning profile. Complete process measurements include startup, RAW decode, current native processing and finished output-file writing. All runs reuse one direct alignment map; its previously measured1.297second creation cost is separate. Input hashing and complete output verification occur outside timed product intervals.

The implementation distributes complete active rows across existing Rayon workers. Each row jumps to its exact previous SplitMix64 stream position. The original Box-Muller draws, f64 arithmetic and u16 quantization remain; physical noise calibration, gathered values, band floor, merge arithmetic and output are unchanged. It adds no full-frame buffer. STREHL_PROBE_FILL=serial retains the reference path. This is a CPU execution improvement to the existing RAW-native algorithm, without reduced calibration or image work.

Independent controls reconstructed the old scalar stream and passed720 whole-buffer comparisons across1/2/8 threads, five tiny/odd/padded/multirow layouts, four seeds, rounding and clipping cases. A wrong row-start control changes the second row and fails equality. The release gate-floor suite passed10 tests with one pre-existing ignored test, including live probe/beta and complete-writer controls. Existing rounded native floor and acceptance console values also agree; those printed values are not claimed as exact beta-vector dumps. Exact final-image identity is independently reviewed from root's saved full-file/pixel hashes.

Owned CPU work increases7.30% at the per-arm minima; this buys elapsed-time reduction by using more cores. Peak committed Job memory remains approximately2.859GiB. Whole-machine busy fraction increases on the parallel arms and includes their own work; it is not a measure of competing processes. The combined probe still includes clone, fill, synthetic gather, extraction and statistics. Neither its isolated fill time nor a GPU speedup is measured.

Actual commands:
- Python312 -I -B experiments/native-pyramid-profile/build.py --output-dir experiments/native-probe-fill/build-1: release compile94.094seconds, real Compiling strehl-cli.
- Python312 -I -B experiments/native-probe-fill/run-controls.py: all stated regressions pass.
- Python312 -I -B experiments/native-probe-fill/run-native.py: original/parallel/parallel/original/scalar five completed native renders, all payloads equal.
- rustfmt --edition 2024 --check crates/strehl-cli/src/merge_cmd/gatefloor.rs: passes.

Source3c23f692; runner c98e2e96. The build invocation recorded an earlier HEAD because a CRLF check delayed the commit; source-binding.json proves all five recorded compiler inputs match the held build hashes and committed bytes. No source changed during compilation. Independent review: independent-results.md. Evidence lives in build-1, controls-1 and native; large TIFFs/executables remain local with reproducible commands and exact hashes.

This is an accepted development speed improvement on one warmed eight-frame native prefix. It does not establish competitive SOTA, deeper-stack timing, cold-cache speed, alignment quality or a photographic-quality gain. No comparator scorecard bar moves. Earlier sensor-transfer and signed-black populations remain closed. Next verify transfer on a different admitted macro stack with existing placements, then choose further work from the remaining gather/probe costs; continue quality work with independently commissioned truth rather than reopen clamp tuning.

Strict lint validation is not green: cargo clippy -p strehl-cli --bin strehl --locked --offline --jobs 2 --target-dir target/native-pyramid-profile -- -D warnings reports26 diagnostics in untouched strehl-core code, then the180second owned bound ends outstanding build work. The selected core source has no diff against the held baseline. No unrelated lint refactor or arithmetic reassociation was made to obtain a passing check. The failure and bounded termination are retained in default-clippy.json/log.

An additional uninstrumented cargo check exited0 and printed release completion after18.89seconds, but its generic process helper waited on remaining owned descendants until its120second bound; it also did not print a distinct Checking strehl-cli line. It is retained as an unadmitted check, not a second green build claim. A follow-up using the compile-only helper refused cargo check before launch because that helper only allows cargo test --no-run. No helper was modified and no native render was repeated. The accepted executable evidence remains the successful fresh release compilation with the existing observer feature, ten regression tests and five exact native-output comparisons.
