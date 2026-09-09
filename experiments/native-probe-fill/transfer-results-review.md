# Independent transfer result: 109MSDCF

VERIFIED from saved records: the exact row-parallel probe filler preserves output and transfers its speed gain to the distinct complete 22-frame 109MSDCF stack. No product execution, capture decode or large-file rehash was performed by this reviewer.

The saved manifest contains 22 content-bound inputs, beginning DSC00009.ARW. Independently reconstructing its ordered filename/size FNV gives b70554b8cfd9b93e, matching the existing canonical map. All four live logs resolve sidecar-override, reference 11, 22 placed/zero refused, 22 folded, eight execution threads and coverage scale 0.9870. Each active profile leaf has 22 calls; defect has zero. All four process receipts record exit zero, terminal accounting and no cleanup error.

| Order | Complete process s | Owned CPU s | Probe wall s | Whole-machine busy fraction |
| --- | ---: | ---: | ---: | ---: |
| Original | 20.422 | 84.187500 | 11.6368906 | 0.1644 |
| Candidate | 15.625 | 89.062500 | 6.5143179 | 0.2040 |
| Candidate | 15.625 | 91.828125 | 6.5073120 | 0.2071 |
| Original | 20.344 | 85.171875 | 11.5507481 | 0.1509 |

DERIVED from these MEASURED trials: minima improve from 20.344 to 15.625 seconds, a 23.20% reduction (1.3020x). Forward/reverse comparisons improve 23.49%/23.20%; median comparison improves 23.34%. Owned CPU minima rise 5.79%, so the improvement is wall time through more parallel utilization, not reduced total CPU work. Whole-machine busy includes the job and differs between trials; it is not independent competing-load accounting. The later original is still slower after the forward/reverse ordering. No scalar-control render was scheduled for this transfer; the completed 112 experiment supplies that separate same-build reversion evidence.

Every complete 7032x4688 uint16 RGB TIFF has whole-file SHA-256 84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851 and decoded-payload SHA-256 1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1. The reference was the first original render of this new stack, not an imported 112 baseline. The runner checked full shape, payload and nonconstant content. Logged floor values and acceptance fractions also match at their printed precision; they do not expose full beta-vector bits.

This comparison includes startup, decoding, cached-map load/coverage and complete output writing. No new alignment solve was run, so there is no measured 109 solve price to add and the earlier 112 1.297-second solve is irrelevant here. Probe wall includes filling and the remaining probe work; filling alone was not timed. The result extends the byte-preserving speed evidence to this warmed 22-frame scene; it makes no claim about improved quality, held-out placement accuracy, cold input or comparative SOTA.

Evidence: transfer-plan-109.json, transfer-109/execution.json, results.json and the four invocation/process/profile/log records. Root executed Python312 -I -B experiments/native-probe-fill/run-native.py with the recorded transfer plan; this reviewer used only Python312 -I -S -B arithmetic over saved JSON and log inspection.
