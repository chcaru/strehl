# Independent build1 control results

2026-09-09. **VERIFIED: the twelve fixed generated controls pass.** This admits the rounded route to the separately allocated native speed comparison and the precision route to the fixed M194b fidelity decision; it establishes neither outcome. Source author did not execute controls. Root executed once; this reviewer read saved artifacts and small delivered TIFFs without rerendering or running a numerical quality metric.

## Provenance and process identity

Build1 invocation binds source f290b6145c091b68482b6cbb76fcc1533331c7bf. compile.log contains `Compiling strehl-cli` and a completed release profile; build-result.json records clean exit0 and92.062 s wall. The test executable is13274624 bytes, SHA-256 a9dfbaa53f13bb777ad8c63d910883ce68b9e13e99cb22f08028f6b1b69bcd40; CLI is10225664 bytes, SHA-256 95e5c82d8940e87dc2e5e790a71aea4f5def69b03abbf1478a93b80087ca0236. The command actually run was `Python312/python.exe -I -B experiments/native-green-probe/run-controls.py --direct-planes`, invoking the exact independent test filter in twelve fresh processes. Runner revision53f22d4 retains the run logic.

The reviewer explicitly checked each saved result.mode against its arm: malvar/directional, fullres true/false, and green=true. All twelve requested direct modes agree with off/rounded/float. Invocation environments agree and bind the same test executable. All process receipts have exit0, no error or cleanup error, terminal job accounting, and no attempted termination. Each saved log digest matches its receipt and records exactly one passing independent test. This post-run validation discharges the runner's missing direct mode-field assertions without replay.

controls-1/results.json is SHA-256 3aea26e0faf519a48ad2f6638b6bfb3531d345c60452ec0d3272fe622b47d1b3. Every per-arm result/direct-result/log/process/invocation remains under controls-1. Aggregate cost is3.439 s summed child wall,8.015625 s owned CPU, and8,998,912 bytes maximum job committed memory. These are tiny control costs, not throughput comparisons.

## Independent choices exercised

Each process passes1,308 scalar comparisons, the existing2,304 whole-buffer scalar writeback comparisons with the new compact sink observers, and all144 real generated RGB/green warp fixture cases. Exact IEEE literals include signed zero, NaN cast disposition, fractional/negative/high black, saturation and inverse-WB cancellation. Old storage checks retain padded/odd-tail and wrong-address/coverage witnesses. The direct observer checks whole and interior crops, complete coverage counts, output guards and serial/parallel schedules in1/2/8-thread pools. Actual direct calls preserve the original complete u16 source buffer and compare consumed rounded bits against legacy remosaic/extract, including green-only compact output.

The separately specified float witness is live in both demosaicers:2,858 changed gathered colour sites for Malvar and2,857 for directional, out of3,036. Its whole/crop comparison preserves full-grid geometry, all values stay finite/nonnegative and each rounded-versus-float difference is at most0.5 input DN on this valid fixture. The uncovered fractional-black and f32 cancellation witnesses also pass; replacing uncovered output with zero or simplifying the pedestal arithmetic would fail. This does not bound post-merge differences.

The reused actual Probe retains eight whole/crop, WB and seed cases, empty certified-band behavior and the invalid-black NaN fault. The source-R/B impulse, WB, coverage and seed witnesses pass. Explicit direct helper calls execute both policies independently of the requested process mode, so their live fractional count cannot by itself prove that load_frame selected the new branch.

## Output and beta comparisons

The reviewer retained each group's original off arm as the anchor, rather than comparing adjacent rounded/float outputs. All four rounded groups have identical complete measurements, all beta bits, and both complete TIFFs versus off. Both float plane-fallback groups also match off exactly. Existing `m194b-known-scene/score.py::read_tiff` was used only to validate delivered TIFF metadata and compare decoded samples; its source hash is d292c8623827eb960bc28dc341398c7e164f5c14cd31af74663ee24c1ff5b5dd. No target or quality metric was evaluated. Recorded whole/crop file hashes and lengths match actual files. Whole outputs are274x190 RGB16; cropped outputs are224x156 RGB16.

| Comparison against matching off | Changed beta cases | Changed decoded channel samples, whole / crop | Required equality |
| --- | ---: | ---: | --- |
| Malvar fullres rounded | 0/8 | 0 / 0 | Passed |
| Directional fullres rounded | 0/8 | 0 / 0 | Passed |
| Both demosaicers, plane fallback rounded | 0/8 each | 0 / 0 each | Passed |
| Both demosaicers, plane fallback float | 0/8 each | 0 / 0 each | Passed |
| Malvar fullres float | 8/8 | 56,027 / 27,301 | Changes allowed |
| Directional fullres float | 8/8 | 60,792 / 33,229 | Changes allowed |

These float changes are delivered pixel changes, not metadata-only differences. They demonstrate that the precision request is not globally inert and that actual Probe measurements change under that policy. They do not prove beneficial fidelity or separately count each load_frame/probe branch; build1 has no such counter.

## Remaining limits

Build1 supplies explicit rounded sink plane-bit equality and actual beta/TIFF equality on the fixed generated population. A final TIFF can hide differences through writer quantization, so it does not prove whole collapsed-f32 identity. Requested-mode metadata is also not a branch-execution counter. Those two evidence gaps are retained; the next existing M194b bridge adds minimal actual/probe branch counts and a pre-writer collapsed digest, with independent assertions. No twelve-process replay is required solely for those additions.

The native old/rounded/rounded/old/same-build-off timing and the independently frozen M194b precision fidelity/noise population remain separate decisions. The generated controls contain no known photographic target, calibrated optical truth or measured native speed. A rounding removal that changes delivered pixels can still worsen fidelity through nonlinear fusion. Do not claim precision quality, SOTA alignment, improved RAW calibration or native acceleration from these controls alone.

## Completed native rounded comparison

MEASURED and independently reviewed from the five saved native records: the rounded route preserves the retained full output and shows a modest local timing improvement. Keep this as bounded speed evidence; the full consumer/collapsed digest controls remain pending and the float quality decision is separate. No native render, RAW decode, large TIFF rehash or alignment solve was repeated by this reviewer.

Root ran `Python312/python.exe -I -B experiments/native-probe-fill/run-native.py --direct-planes-109` once from execution revision128feccdb1a0ff3b5cdd4d33de7cd1a10d1244ef. The runner hash is b07277d96be60da9479ed478cbd4358f28c591b96e6bdb194e43629f72f8f9ca. It used held writeback binary4fe5443366c628029f9ea64faf6c239bb1769953f5ee505a7d629f5e22f4e2b8 and the build1 candidate95e5c82d8940e87dc2e5e790a71aea4f5def69b03abbf1478a93b80087ca0236. Native results.json SHA-256 is1f5369db59d08d4177b56712f6ac578c744ea5833cc66526a4992bcdd22a530f.

The independent receipt check found all five jobs cleanly completed with exit0, no error, terminal job accounting and no attempted termination. Invocation routing matches old/candidate/candidate/old/off-control; only candidate uses rounded and same-build control explicitly uses off. All logs match their saved digests, report22/22 folded frames,22 placed/0 refused and complete7032x4688 RGB16 output. Every non-defect phase has22 calls. This is the actual development109MSDCF stack with the previously admitted canonical map (file SHA-256 c29cab9c6f944f4d03c4402998e54aad4d4221cc450ac4bef42a453de848434d, digest b70554b8cfd9b93e), under the held22-input manifest and warmed-input protocol.

All five recorded complete TIFFs are197,798,267 bytes, SHA-25684f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851. All decoded RGB16 payloads are197,796,096 bytes, shape4688x7032x3, SHA-2561bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1. Both identities match the earlier retained original, not merely one new candidate output. Root computed complete hashes during the fixed run; this review verified their binding to execution and each process/output record.

| Actual order | Completed process wall, s | Owned CPU, s | Peak job commit, bytes |
| --- | ---: | ---: | ---: |
| Held old | 11.157 | 69.796875 | 2,996,076,544 |
| Rounded | 10.890 | 66.265625 | 2,996,756,480 |
| Rounded | 10.860 | 67.093750 | 2,996,375,552 |
| Held old | 11.266 | 70.703125 | 2,996,273,152 |
| Same-build off | 11.000 | 67.125000 | 2,997,374,976 |

DERIVED from those saved records: old/candidate minima are11.157/10.860 s, a2.66201% wall reduction; medians are11.2115/10.875 s, a3.00138% reduction. Forward and reverse comparisons show2.39312% and3.60376%, respectively. Even the slower candidate versus fastest old is2.39312% lower in this window.

The independently re-chosen same-build control materially narrows attribution. Same-build off is already1.40719% below the old minimum. Rounded is only0.110-0.140 s, or1.00000-1.27273%, below that one off run. Old/candidate minimum CPU declines5.05932%, but against same-build off the two candidate CPU reductions are1.28026% and0.04655%; the latter is only0.03125 s. Thus the complete old/new change cannot be credited to the destination policy. Peak memory is effectively unchanged near3.0 GB, with no material memory reduction established. Whole-host busy fractions span22.25-25.27%; these include the job and cannot be read as exclusive competing load or proof against clock/cache drift. No additional timing run was selected to improve this small result.

The phase profile supports the narrower mechanism without isolating a sink-only timer. Extract/luma wall falls from0.270021-0.273767 s in held old and0.269239 s in same-build off to0.127939-0.134411 s rounded. Some destination arithmetic is now included in gather, so this phase change alone is not an end-to-end saving. Gather is3.741133-3.764288 s rounded versus3.758282 s same-build off: approximately unchanged. Probe is3.044930-3.053474 s rounded versus3.117750 s same-build off. Decode, pyramid-add and final collapse/write remain close; rounded collapse/write is0.309002-0.311787 s versus0.312742 s same-build off. These are recorded wall intervals, not owned CPU or independent kernel timings, and their sum omits startup, allocation, bookkeeping and publication. Completed process wall is the deciding cost.

The reported alignment interval0.000368-0.000678 s is cached map handling/coverage in this run, not an alignment-quality solve. No112MSDCF solve cost is transferred into this109MSDCF comparison. This bounded rounded speed evidence can support retaining an opt-in implementation while the explicit branch/collapsed controls finish; it does not establish a broad throughput percentage, cold-cache improvement, precision fidelity, native alignment accuracy or SOTA. No cumulative percentage is multiplied with earlier optimization windows.
