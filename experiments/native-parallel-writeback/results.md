# Exact parallel writeback: native improvement retained

MEASURED 2026-09-09. The new full-resolution destination writeback takes11.156seconds versus12.734seconds for the held previous implementation on the complete22-frame109MSDCF RAW stack:12.392% less minimum completed-render time,1.14145x throughput. Every complete TIFF and decoded pixel payload is identical. The explicit serial mode in the new executable takes12.469seconds, so the parallel candidate is9.52–10.53% faster than that same-build control. Do not attribute the entire old/new difference solely to scheduling.

Only disjoint destination rows execute in parallel. Each sample retains the original f32 inverse-WB/pedestal expression, round/clamp/u16 cast and coverage handling. Coverage reduces exact usize counts. Source demosaic, sampling, native noise, frame order, merge and writer stay unchanged; no image-sized buffer or floating reduction is added. The plane fallback is unchanged. Source:2c452ce0352ff2d2dc85831d01f06831b045d62a. The independent review records acceptance separately.

## Executed commands

Root used C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe:

```text
Python312 -I -B experiments/native-pyramid-profile/build.py --output-dir experiments/native-parallel-writeback/build-1
Python312 -I -B experiments/native-green-probe/run-controls.py --writeback
Python312 -I -B experiments/native-probe-fill/run-native.py --parallel-writeback-109
```

The fresh release compilation contains Compiling strehl-cli, exits0 and takes90.781seconds. CLI SHA256:4fe5443366c628029f9ea64faf6c239bb1769953f5ee505a7d629f5e22f4e2b8; test executable:b6d98624057b7b2f05f49b64859e3ffce2264188de89647bdc78d0f3280570b7. The held reference is native-green-probe/build-2, SHA2562581e0373118bd03577eaaf486bb30898fd8b0e385215ae1c8a1a574d18d2e88. Exact invocations, bindings, environment overrides, process receipts and terminal logs remain under build-1, controls-1 and native. The post-allocation timing of the prior-art search is disclosed in charter.md; it was not a pre-dispatch check.

## Independent exact controls

All eight fresh serial/parallel x Malvar/directional x full-resolution/plane processes pass. Each executes the same2304 independently authored literal-old-loop buffer/count cases across1/2/8threads, four layouts, four CFA sites, coverage patterns, inverse gains and black levels. Covered/uncovered NaNs, signed zero, half-integers, clipping, untouched padding and odd tails are exercised. Literal expected quantization values and deliberately wrong stride/phase/coverage inputs demonstrate power to fail; matching coverage alone would miss wrong addressing.

Each process then reuses the actual green-probe controls:144 warp pairs with six resamplers, corrected analytical source-color impulses, finite/NaN beta bits and actual whole/crop renders. All four serial/parallel measurements and complete tiny TIFF pairs match exactly. Independent review also compares them with retained pre-change green-probe outputs; these match too. The extra writeback receipt records the requested mode, not an internal execution counter. Source dispatch plus native same-build serial reversion supplies the corresponding causal check.

The helper relies on the existing production caller's active-storage/scratch guarantees; arbitrary malformed direct-helper inputs are not a new supported interface. No new renderer, verifier framework or physical fixture was introduced. These controls establish exact behavior within their tested domain, not a noise-calibration or photographic-quality result.

## Native timings and preserved pixels

| Arm | Complete process s | Gather wall s | Probe wall s | Owned CPU s | Peak job commit GiB |
|---|---:|---:|---:|---:|---:|
| Held old1 | 12.734 | 5.013483 | 3.600055 | 70.031250 | 2.791027 |
| Parallel1 | 11.282 | 3.859252 | 3.179791 | 68.765625 | 2.790714 |
| Parallel2 | 11.156 | 3.859933 | 3.170196 | 69.359375 | 2.790016 |
| Held old2 | 12.735 | 5.016595 | 3.590998 | 72.140625 | 2.790710 |
| New executable, serial | 12.469 | 4.750619 | 3.615274 | 68.875000 | 2.790981 |

Forward/reverse improvements are11.403%/12.399%; arm medians improve11.901%. Even the slower candidate beats the faster old arm by11.403%. The single new-serial control is2.08% faster than the held old minimum; this is a real attribution limit, not discarded data. Complete-process intervals include startup, map loading/coverage, fold and finished writing. Phase intervals are wall time, not CPU, and no stitched per-phase minimum substitutes for a run. CPU minima change70.03125→68.765625seconds; peak commit remains about2.791GiB, with no material memory-saving claim.

Host busy fractions are0.1971/0.2240/0.2311/0.2058/0.2003, including the owned job. Timing can be fooled by scheduling and caching; alternating order, the least-favorable comparison and explicit same-executable serial control constrain those alternatives. Two repeats per main arm on warmed development inputs do not establish a cold-cache or universal hardware speedup.

The same22 originals DSC00009.ARW…DSC00030.ARW in D:/personal/macro/109MSDCF and existing canonical map are bound by native-probe-fill/transfer-plan-109.json. Input size/mtime is checked once before the loop; map bytes/hash are checked before each invocation. The CLI validates ordered filename/size identity each time. No new solve or RAW write occurs, and no solve time from another stack is added.

Every full7032x4688RGB16 TIFF has197,798,267bytes and SHA25684f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851. Decoded RGB16 payloads have197,796,096bytes and SHA2561bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1. All five match the original from before both green-probe and writeback changes. Equality can reject any changed output byte; it cannot tell whether the reference image is good.

## Decision

Independent review accepts retaining parallel full-resolution writeback, with STREHL_WARP_WRITEBACK=serial for reversion. Close this fixed candidate comparison. In the actual11.156second candidate, gather is3.859933seconds, probe3.170196 and pyramid-add1.675011. Later speed work should use that distribution, not the old pyramid/GPU estimate.

These serially developed speed results must not be multiplied into a newly measured cumulative benchmark. The current endpoint is11.156seconds on this fixed22-frame render with identical output; comparative SOTA speed, physical quality and deep-stack placement remain unestablished. Next priority is one distinct RAW/optical quality intervention using existing truth, with the prior failed remedies retained. See the bounded primary-source directions in native-green-probe/new-quality-directions.md; oracle geometry is an experimental limitation, not a deployed capability.
