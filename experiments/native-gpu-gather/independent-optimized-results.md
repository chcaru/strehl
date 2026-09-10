# Independent optimized GPU results

VERIFIED from saved evidence only: no build, numerical control, RAW decode or render was performed by this reviewer. The optimized candidate preserves the admitted outputs. A reliable whole-process speed gain is not demonstrated.

The build-native-2 invocation names committed cbbb2bfa68dbd0444d7d74e48c685fa420560bbd. I checked all 28 recorded source bindings against that commit: every byte/hash matched, allowing the one recorded CRLF checkout materialization. Later Device256 edits are outside this evidence. The frozen independent tests remain 9ebd1a970b89781314db5349b68cd07df0c7e0bfb25f56dc57471721e93975e3. compile.log contains fresh Compiling lines for both strehl-cli and strehl-native-gpu-gather; the held CLI and test executable hashes were independently rechecked against the invocation chain.

run-4/results.json records Parallel256 on RTX 5090/Vulkan: all 18 primary cases have zero code/coverage/padding differences. The 25 quantizer literals, 2,990 actual ramp half ties, signed overshoot, odd storage, support-boundary cases, all-uncovered case, green-only preservation, three live descriptor destroyers and ordinary/observer/placebo complete-storage hashes remain effective. Re-choosing the formerly failing synthetic-CA case confirms it now passes; the separately labelled undecorated case still produces CPU 3478 versus GPU 3477 from CPU operand 3477.5. Original and decorated shader hashes are unchanged from run-3. This isolates the restriction contrast on this shader/input; it does not prove a particular fused instruction caused the difference. Naga parsing/IR validation and structural checks remain distinct from unavailable spirv-val validation.

The committed scheduling source shares the exact f64 point expression and invalid predicate between Serial32 and Parallel256. Row filling joins before mutation/upload; only boolean validation reduces in parallel. The fixed small controls reach at most 50 rows, so native identity supplies the missing multiple-strip check: 4688 = 18*256 + 80. Uniforms, dispatch, readback and destination extents all use that last 80-row length. No extra pixels are dispatched from stale descriptor capacity. This commissions these native extents, not arbitrary dimensions, thread counts or an optimum batch size.

All 13 native records are exact against their respective held corpus reference: six initial 112 outputs, three optimized 112 outputs, and four 109 outputs. They are 13 complete renders, not 13 GPU renders or 13 independent stacks; nine belong to 112 and four to 109. The corpus hashes differ, as they should. Every record agrees with its per-arm output/profile receipt, command and saved log hash; all process receipts show exit zero, terminal accounting, no cleanup errors and no termination intervention. The initial six retain both remosaic/direct-rounded paths and log off/on/placebo identity. The optimized three exercise CPU rounded, GPU Serial32 rounded and GPU Parallel256 rounded with logging on; the 109 four use rounded and logging off. CPU arms have no GPU completion markers; GPU arms have 8 RGB plus 8 green-only calls for 112 and 22 plus 22 for 109. These establish actual/probe route use, not every intermediate beta bit.

I independently rehashed native-112-2/3-gpu-rounded-on-parallel.tiff and native-109-1/3-gpu-rounded-off-parallel.tiff. Each is 197,798,267 bytes, and each matches its full-file anchor below. Saved independent decoded RGB16 hashes also match all arms at 7032x4688; I did not rerun that reader.

| Corpus | Independently rechecked whole-TIFF SHA256 | Saved decoded RGB16 SHA256 |
| --- | --- | --- |
| 112 | ba96c63dd56f2729ba2ed25fedc19b291a4a78f9992f6823ce501a1df2a8bdc6 | d5fd6969b77fc94334995dea771e434f65f2b3cf782e1d683ca2872639595a1a |
| 109 | 84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851 | 1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1 |

The optimized 112 pilot costs 4.907 s CPU, 8.594 s GPU Serial32, and 4.796 s GPU Parallel256. It supports removal of the measured scheduling bottleneck, but its single order and differing log mode do not establish a small CPU/GPU advantage. The change bundles row parallelism with larger transfers; their individual contributions were not isolated.

| 109 execution order | Whole-process wall seconds | Owned CPU seconds | Peak job commit bytes |
| --- | ---: | ---: | ---: |
| CPU | 11.703 | 68.515625 | 2998943744 |
| GPU Parallel256 | 11.218 | 44.046875 | 3578957824 |
| GPU Parallel256 | 11.234 | 41.593750 | 3580096512 |
| CPU | 11.156 | 67.781250 | 2997882880 |

DERIVED from these fixed receipts: GPU minimum 11.218 s is 0.062 s (0.56%) slower than CPU minimum 11.156 s. The forward pair suggests 4.14% less wall time; the reverse pair instead has GPU 0.70% slower. CPU drift is 0.547 s, compared with GPU spread 0.016 s. Choosing medians would suggest a 1.78% gain, but the first CPU decode-validate interval alone exceeds the final CPU interval by 0.5436863 s, almost the entire drift; that is not evidence of a stable GPU gain or proof of a particular cache mechanism.

Re-choosing the combined consumer cost rather than gather alone gives the same conclusion: final CPU gather+probe is 7.1112 s, versus GPU 7.1740/7.1891 s. Faster RGB gather is offset by slower probe. Owned CPU time nevertheless decreases (minimum 67.78125 to 41.59375 CPU seconds, 38.64%), while peak job commit rises from about 3.00 to 3.58 GB. CPU-seconds are not elapsed speed, and job committed memory is not GPU VRAM or RSS. Whole-host busy measurements include this job and are not an independent contention correction.

Accounting: run-4 costs 0.3125 child CPU seconds and 0.703 s wall; the seven new native renders cost 280.71875 CPU seconds and 63.608 s summed wall. All 13 native renders total 394.8125 CPU seconds, 105.264 s summed wall and 2,571,377,471 retained TIFF bytes. Build-native-2 separately costs 263.703125 CPU seconds and 133.312 s wall; its successful direct compile was followed by explicitly recorded owned-descendant cleanup, not natural exit of every build child. These totals exclude earlier builds/controls and are not whole-program cost totals.

Scope: exact preservation of the existing consumer is not improved photographic quality, calibration validation or SOTA. Native commands reuse saved alignment maps; the actual alignment solve and its quality are excluded. The runner checks the admitted RAW file sizes/mtimes and map bindings before/after, not a global corpus hash audit. Native tests use the selected MHC/Catmull/WB/CA paths, eight 112 inputs and 22 109 inputs, with defects off; they do not establish universal RAW/GPU equivalence. Keep this as a correct experimental route with reduced CPU work, without a default/speed promotion justified by these timings.

Evidence SHA256: run-4/results.json 3980091736a3131d3b5b2f4386b4f89837d9236bb91161e2cae534ece1e523f9; native-112-2/results.json 6f4f05d439d29c6601613ab8ca1ce88664bf2c61e13af14058f0ed287fb63b72; native-109-1/results.json b5a2e97c694cffb5e34547022288e1907aa07bec55445fef1700618dd9eda21d; build-native-2/invocation.json 128ba09ab20e0e9a316b354ee470f76985c6bb35af0c83ac886bf042c9f42c36; strehl.exe f3ac79f4b97f7b29f590b368bf2d0d29dd414a3fd29addc795d4ba971fd079c4; cli-tests.exe 70418700ea6eb59901a1fe137a9ff2aba547f4f76f0016e0e6a4a4fab4de3107.
