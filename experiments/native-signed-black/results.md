# Signed RAW comparison: first candidate rejected as a default

MEASURED2026-09-09. The full-signed opt-in improves shadow bias but worsens texture fidelity on the fixed noisy focus-varying fixture. Keep the shipped default. This is a development result, not a SOTA claim, noise-calibration result or physical occlusion benchmark.

Source5694161b; independent reader3e1a97e5. Root ran Python312 `-I -B experiments/native-signed-black/run-comparison.py`, then the recorded independent-read invocation. Fresh CLI compilation completed in10.063s (build-2/compile.log contains Compiling strehl-cli). Both four-case invocations exited0: clamped0.640s, signed0.391s. Independent reading exited0 in0.219s, read1,051,177bytes, and decoded all8native TIFFs. These small debug timings are costs, not speed comparisons; the order was fixed and synthetic-source generation is included.

## Actual outputs

The table reports RMSE against independently specified neutral CFA truth, in RAW DN, read from the corresponding known CFA channel of the native16-bit RGB TIFF. Lower is better on this known-scene error. It can hide local damage when pooled, so fixed narrower texture masks, two boundary widths and maximum errors are retained. Full RGB pixels were decoded, but interpolated-channel or color accuracy is not independently scored.

| Fixed case/mask | Clamped RMSE | Full-signed RMSE |
|---|---:|---:|
| Zero/dim split, whole | 0.985775 | 0.066281 |
| Zero flat, whole | 1.585962 | 0.101989 |
| Low-signal texture, left | 3.033529 | 3.323787 |
| Low-signal texture, right | 3.637479 | 3.683741 |
| Low-signal boundary, width2 | 4.674231 | 4.438417 |
| Low-signal boundary, width12 | 3.645840 | 3.631781 |

The nonnegative focus-varying null has identical collapsed f32 bytes, whole TIFF bytes and decoded pixels in both arms. Every TIFF known-CFA value agrees exactly with the independent writer prediction (zero code difference, despite the reader permitting one rounding code). Actual input hashes match between arms, and signed cases consume negative values.

The zero/dim split reaches the literal collapsed target with signed arithmetic: baseline left/right means1.2/1.8DN become0/1DN. The final dim-1 output differs by ordinary16-bit quantization. This is strong rectification evidence on a deterministic operator fixture, not a sensor-noise measurement.

The spatial zero-flat input uses deliberately anticorrelated perturbations [s,-s,t,-t,0], not five independent sensor exposures. Its signed collapsed mean is-0.030367DN and RMSE0.226094DN; the final clipped and quantized TIFF has mean0.009145DN and RMSE0.101989DN. The baseline TIFF mean/RMSE is1.585962DN. However, maximum absolute TIFF error worsens1.585962 to4.078187DN. Lower average error is not a uniform improvement.

On noisy-depth, full-signed collapsed whole RMSE worsens2.657567 to2.910391DN. The final known-CFA TIFF whole RMSE changes2.662721 to2.681747DN; left/right texture RMSE worsens as shown, while RMSE improves in the fixed boundary strips. Narrow-boundary absolute bias nevertheless worsens0.195539 to0.721242DN. The current prototype therefore fails the intended conjunction of better shadows and preserved detail. No parameter or noise gain is adjusted to hide this.

Configured7bands produces only3actual levels on64x48CFA planes. Each case contains5generated padded u16 frames and uses the actual BandWorker, BandMerge finish and native writer. No real RAW decoder, nonidentity geometry, measured placed-frame probe, physical diffraction or occlusion is exercised here. Synthetic perturbations do not identify calibration. Total stage1 population:4smoke consumer calls plus8comparison calls, exactly12.

## Next bounded candidate

Stage1 is complete; retain all outputs and its rejection. Stage2 explicitly tests a different consumer choice: retain signed CFA reconstruction values, but supply the existing separately clamped G1/G2 mean and its existing variance calculation to focus decisions. This may isolate reconstruction bias from the gate change; it is a hypothesis, not an accepted remedy.

Use mode2, leaving mode0 and mode1 unchanged. Repeat the same4fixed cases in fresh comparison2-clamped/comparison2-values directories,8additional consumer calls total. Reuse the same fixtures, masks, noise coefficients, three actual levels, no-map white beta, and writer. Save and compare hashes of actual consumed luma/variance arrays; preserve the unchanged-input null and independently score actual f32/TIFFs. Do not change core, fit gain/beta or add a new framework. This initial stage is no-map only; the separately generated placed-frame noise probe is not yet covered.


## Stage2 completed: value-only variant also rejected

MEASURED2026-09-09. Source d6ad22c3, independent reader b25a4798. Actual root command was Python312 `-I -B experiments/native-signed-black/run-values-comparison.py`; independent-invocation-2.json retains the exact saved-read arguments. A fresh CLI compile completed in9.844s, then the clamped/value-only four-case invocations completed in0.625/0.391s, all exit0. Independent reading completed once, exit0,0.219s, reading1,065,933bytes and decoding all8native TIFFs.

The actual luma and variance hashes match on all20paired folds. Empty beta prefixes and averaged fractions also match. This restores the joint luma/variance focus input on the no-map fixture; it does not separate their individual contributions or establish a calibrated gate. Signed InputRange bounds remain part of the reconstruction treatment.

The second independent reviewer opened all16 original/new baseline payload files. All four original/new baseline f32 pairs and all four whole-TIFF pairs are byte-identical, with saved extents/hashes matching. The new nonnegative structured null also remains byte-identical across arms. No baseline drift or hidden default correction explains the outcome.

The same known-CFA TIFF metric gives:

| Noisy-depth mask | Clamped RMSE DN | Value-only RMSE DN |
|---|---:|---:|
| whole | 2.662721 | 2.635601 |
| flat-left | 1.265660 | 0.093736 |
| flat-right | 0.386647 | 0.202967 |
| texture-left | 3.033529 | 3.119747 |
| texture-right | 3.637479 | 3.681197 |
| boundary-2 | 4.674231 | 4.649583 |
| boundary-12 | 3.645840 | 3.687833 |

Re-pooling the two disjoint equal-size texture masks by squared error gives3.349146 to3.412040DN, a1.878%regression. Both texture masks and the broad boundary regress in every CFA plane. Whole-image RMSE improves, which is why it cannot stand in for preserved texture. Prewriter whole RMSE still worsens2.657567 to2.841248DN.

The split-offset collapsed target is again exact. The temporally balanced zero-flat fixture now has zero collapsed and TIFF error; that is an operator result for this deliberate anticorrelated input, not zero sensor noise. Flat-right noisy-depth RMSE improves0.386647 to0.202967DN while maximum error worsens0.851621 to1.187472DN. Narrow-boundary RMSE improves, but absolute bias worsens0.195539 to0.400864DN and G1 RMSE worsens.

Decision: reject mode2 as a default too. Stop this four-case variant sweep. Keep modes1/2 explicitly experimental, with their rejection and no-map limits recorded; current default and noise coefficients remain unchanged. No further clamp adjustment or gain fit is identified by these results. This is one development population, not independent physical confirmation.

The existing five crop/extraction/writer unit tests also passed under each of modes0,1,2 (15checks total), using the freshly compiled build-3 executable. These tests do not run BandWorker or add production comparison calls. Stage2 uses exactly8new comparison calls; smoke plus both comparisons totals20. No new native decoder traversal occurred in these comparisons.

## Program continuation

The completed sensor diagnostic and both signed-black comparisons are closed. The next implementation priority is actual default-pipeline performance: measure current decode, gather/probe, pyramid and final-output costs before choosing CPU SIMD or a connected GPU backend. Reuse existing process/timing tools and perform output-preservation checks; no new general runner or provenance framework.

Prior-art command executed, exit0: Python312 -I -S -B experiments/ORCH-drift-check/prior_art.py "phase profiling" "pyramid" "decode". Root read M-PHASE0-PIPE, M-PHASE0-DECODE2 and M8-scratch-measured. The old decode queue was slower and removed; do not rebuild it. Their worker scaling predates today's serial canonical chunks with spatial parallelism, so those numbers are prior evidence, not current throughput. The previously recorded next-quality-speed-decisions.md identifies the current BandWorker/BandMerge consumers and the unmeasured full-native gather/probe shares. Existing M192/runtime campaigns remain closed. No speed win has been measured by this signed-black experiment.
