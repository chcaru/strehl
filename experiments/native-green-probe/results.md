# Native probe output specialization: exact speed gain retained

MEASURED 2026-09-09. On the complete 22-frame 109MSDCF RAW stack, skipping unused synthetic-probe color outputs reduces the minimum completed render time from 15.609 to 12.781 seconds: 18.118% less wall time, or 1.2213x throughput over the already retained row-parallel implementation. All five complete 7032x4688 RGB16 TIFFs and decoded pixel payloads match the held pre-change original exactly. The explicit RGB switch restores the prior cost. Independent actual-result review accepts this scoped result; retain the green-probe default.

This is CPU work omission inside the sensor-noise probe. Every source CFA channel remains present, including red/blue contributions to reconstructed green. Actual photographs still use the full RGB gather. Sensor calibration, generated noise samples, geometry, demosaic choice, merge weights, band floors and output math remain unchanged. It establishes preserved outputs and a development speed improvement on this stack, not better photographic quality or competitive SOTA standing.

## Commands and retained revisions

Production source: 8e1732112394c4fcb19b2e956b0f6cc051b30011. Independently repaired falsifier fixture and final driver: 6222aef4269538ab61f2a95150a196e200f215b3. The production arithmetic is identical between these two revisions.

Root executed, in order:

```text
Python312 -I -B experiments/native-pyramid-profile/build.py --output-dir experiments/native-green-probe/build-1
Python312 -I -B experiments/native-green-probe/run-controls.py
Python312 -I -B experiments/native-pyramid-profile/build.py --output-dir experiments/native-green-probe/build-2
Python312 -I -B experiments/native-green-probe/run-controls.py --revised-power
Python312 -I -B experiments/native-probe-fill/run-native.py --green-probe-109
```

Here Python312 is C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe. Exact build, control and native invocations, environment overrides, process receipts and terminal logs are retained in build-1, build-2, controls-1, controls-2 and native. Build 1 compiled strehl-core and strehl-cli; build 2 compiled strehl-cli after the test-only change. Build 2 CLI SHA256 is 2581e0373118bd03577eaaf486bb30898fd8b0e385215ae1c8a1a574d18d2e88, and test executable SHA256 is ebf4f91443425254c157241ad6538d1d470152d0697c4300daa1fc7bace1dccc. No generic check/clippy helper failure is represented as a passed check.

## Whole-process result

The fixed order alternates old/candidate and candidate/old, followed by the explicit RGB reversion in the new executable. Eight Rayon threads, the existing phase observer enabled, the same native product settings and the same held placements apply throughout.

| Arm | Complete process s | Probe wall s | Actual image gather wall s | Owned CPU s | Peak job commit GiB |
|---|---:|---:|---:|---:|---:|
| Old 1 | 15.609 | 6.513884 | 4.996619 | 90.281250 | 2.859570 |
| Green 1 | 12.875 | 3.595523 | 5.024012 | 71.578125 | 2.791130 |
| Green 2 | 12.781 | 3.603093 | 5.051969 | 71.921875 | 2.790096 |
| Old 2 | 15.704 | 6.537662 | 5.025413 | 90.343750 | 2.859230 |
| New executable, RGB control | 15.687 | 6.538952 | 5.016940 | 92.828125 | 2.859554 |

The two timing directions show 17.516% and 18.613% less wall time; comparison of arm medians shows 18.066%. These are complete owned-process intervals, not a sum of separately selected phase minima. Owned CPU minima decrease 20.716%; maximum observed job commit decreases about 0.06844 GiB. Probe cost falls by about 2.9 seconds while actual image gathering stays near 5 seconds. Leaf phase times are wall intervals, not CPU measurements.

Host busy fractions are 0.2017/0.2078/0.2278/0.2180/0.2173. They include this job and do not isolate competing work. This is a warm development comparison with two repetitions per primary arm, not a cold-cache or hardware-saturation benchmark. Runtime could be fooled by scheduling/cache changes; alternating directions, whole-process receipts and same-executable RGB reversion constrain that explanation here without proving a universal speedup.

Inputs are the existing 22 originals D:/personal/macro/109MSDCF/DSC00009.ARW through DSC00030.ARW, 836,440,064 bytes. The previously authenticated transfer-plan-109.json and canonical 109MSDCF.warpmap.txt bind the files and map; the runner checks input size/mtime bindings once before the arm loop and rechecks map bytes/hash before each invocation. The CLI separately validates ordered filename/size identity for each invocation. No new alignment solve runs. Render timing includes map load and coverage only. The prior 112MSDCF solve time is not assigned to 109. The map is a held coordinate choice, not ground-truth alignment.

All five TIFFs are 197,798,267 bytes with SHA256 84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851. All decoded RGB16 arrays are 197,796,096 bytes with SHA256 1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1. These match the original from the earlier transfer, as well as the held old executable in this run. Equality against that separate executable addresses the limitation of new RGB/green tests sharing a refactored helper. Hash equality proves preservation here; it does not judge whether the original image is good.

## Independent controls, including the failed first falsifier

The initial execution passed four Malvar processes (two RGB/green pairs), then failed an independently required red/blue-source perturbation in directional mode. The old modulo fixture was exactly constant down columns: 27*37+11 = 10*101. Directional green could choose an unchanged vertical response. No RGB/green equality failed. controls-1 retains that failed assertion, prior successful receipts and outputs; the three later environments were not run.

The verifier retained this inert fixture with its expected behavior and added an analytical two-dimensional impulse. A +32 red/blue center above a constant 64 background must reconstruct green 80 under both demosaicers. A separate +320 source impulse with quarter-plane fractional bilinear sampling must change consumed G1/G2 from 2512 to 2592. These give the destroyer a real ability to fail without weakening exact equality or changing production source.

All eight revised processes pass: Malvar/directional x full-resolution/plane gather x RGB/green probe. Each actual test exercises 144 direct warp pairs, six resamplers, geometry changes, small/odd/padded layouts, WB variants, covered/uncovered destinations and unchanged skipped storage. Generated green rows, consumed green samples, beta bits including the explicitly injected nonphysical NaN case, and complete whole/crop TIFFs match. Finite beta seed/WB sensitivity and mode differences demonstrate live routes. The NaN case tests error propagation, not physical calibration. Plane fallback retains the prior four-site behavior.

Independent controls re-choose analytical impulses, layouts, resamplers and source references. Saved-result review also checks live mode differences and the least favorable timing pairing rather than merely recalculating a published headline. See independent-tests.rs and independent-review.md for actual populations and limitations. CA composition for green is identity in this implementation, so changing CA is not presented as a live green-quality test. The original observer's off/on/placebo hash controls remain the evidence that phase instrumentation itself preserves output; this run keeps it enabled throughout.

## Decision and continuation

Retain the independently accepted green-only synthetic-probe output specialization, with STREHL_PROBE_GATHER=rgb available for exact reversion. Both exact speed steps now have actual native evidence. The completed row-fill 112/109 populations and this fixed green-probe 109 comparison are closed; do not rerender them merely for publication or tune a physical coefficient from these timings.

Actual image gathering is now the largest measured leaf on this native stack (about 5 seconds), followed by the probe (about 3.6 seconds); pyramid-add is about 1.67 seconds. That evidence will guide any later CPU/GPU work. The immediate program priority returns to a small photographic-quality intervention using an existing native known-truth consumer and independently chosen detail, flat-region and boundary controls. The rejected signed-black variants and completed sensor-transfer population stay closed. No comparative scorecard bar moves from this experiment.
