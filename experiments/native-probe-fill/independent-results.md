# Independent results: exact parallel probe fill

VERIFIED from the saved execution records: accept this change as an image-preserving speed improvement on the fixed eight-frame 112MSDCF development prefix. No new RAW/test execution or large-file rehash was performed by this reviewer. The root executed the controls and complete native comparison; this review independently re-chose the timing summaries and checked the actual recorded modes, phase counts, logs and payload bindings.

The control log reports 10 passed, zero failed and one explicitly ignored test. It contains the 720 whole-buffer comparisons over independent scalar-reference/layout/thread/edge choices, the live wrong-row destroyer, 80 actual-probe layout comparisons and 20 seed controls, plus existing actual writer and live-operand controls. The ignored duplicate actual-probe author test does not remove the executed independent actual-probe checks. Source-reviewed and held controls are documented in independent-review.md; these runs do not calibrate the physical noise model.

The native order and complete-process costs are:

| Arm, execution order | Process wall s | Owned CPU s | Probe wall s | Whole-machine busy fraction |
| --- | ---: | ---: | ---: | ---: |
| Original, first | 8.312 | 31.593750 | 4.1997804 | 0.1508 |
| Candidate, second | 6.469 | 34.109375 | 2.3684443 | 0.2088 |
| Candidate, third | 6.375 | 33.781250 | 2.3827871 | 0.2062 |
| Original, fourth | 8.110 | 31.484375 | 4.2722353 | 0.1570 |
| New binary forced serial, fifth | 8.265 | 32.796875 | 4.3109682 | 0.1605 |

DERIVED from these MEASURED records: the per-implementation minima are 8.110 versus 6.375 seconds, a 21.39% wall reduction or 1.272x throughput ratio on this prefix. The forward and reverse comparisons improve by 22.17% and 21.39%; the median comparison is 8.211 versus 6.422 seconds, a 21.79% reduction. Even the slower candidate beats the faster original by 20.23%. The same new binary forced serial returns to 8.265 seconds, inside the original's 8.110..8.312 interval. This discriminates the scheduling change from a uniformly faster new build. The first original decode interval was slower than the others; choosing the faster original and both order directions prevents that one interval from defining the result.

The candidate uses more CPU, not fewer total CPU seconds: the minima rise from 31.484375 to 33.781250 seconds, or 7.30%. Peak committed memory across all five is 2927.59..2927.86 MiB, effectively unchanged at this resolution. Higher whole-machine busy fractions during the candidate include its own increased parallel utilization. They must not be interpreted as measured competing load. The host samples include background activity and are not an isolated-machine experiment; both timing directions and the scalar reversion remain favorable despite that limitation.

Each native profile has eight calls to decode/validate, gather, probe, extraction, variance and pyramid-add, and zero defect calls. All five logs show eight placed/folded frames, the same canonical chunks and eight execution threads, identical rounded white gains, identical rounded measured floors (1.0753, 0.0495, 0.0099, 0.0024), and identical rounded acceptance fractions. These console values do not expose the full beta vector bits. The stronger direct observations are the executed scalar-buffer equality controls and root's complete-file/pixel identity checks; do not relabel rounded floor equality as bitwise native beta-vector verification.

All five complete 7032x4688 RGB16 TIFFs match the held original file hash ba96c63dd56f2729ba2ed25fedc19b291a4a78f9992f6823ce501a1df2a8bdc6 and decoded-payload hash d5fd6969b77fc94334995dea771e434f65f2b3cf782e1d683ca2872639595a1a. Each file is 197798267 bytes with 197796096 decoded bytes. The runner verifies one uint16 page, the full shape and nonconstant content before hashing; all five owned processes exit zero with terminal accounting and no cleanup errors. This review read those saved checks and their code; it did not independently decode the large TIFFs again.

The timing includes process startup and completed output writing, with the same saved direct map loaded by every arm. It excludes recomputing alignment: the separate earlier alignment process took 1.297 seconds and is not silently folded into these render results. These are warmed inputs, seven-leaf observers enabled, current coefficients and native output. The probe interval includes cloning, filling, real warp and measurement; filling alone was not timed. Neither leaf minima nor the earlier standalone alignment measurement should be summed into an invented measured complete run. The gain establishes neither better image quality, comparative SOTA status, cold-cache behavior nor deep-stack performance. It licenses retaining the exact parallel default and moving on to the next measured bottleneck.

Evidence: controls-1/tests.log; native/execution.json; all five native/*-invocation.json and *-process.json; native/results.json; corresponding native/*.log. Root commands: Python312 -I -B experiments/native-probe-fill/run-controls.py and Python312 -I -B experiments/native-probe-fill/run-native.py. Numerical re-choice in this review read only the saved JSON/log files using Python312 -I -S -B; no production calls were replayed.
