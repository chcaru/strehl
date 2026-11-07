# Original-CFA region preparation optimization

MEASURED: the production RegionSampler replaces full-plane preparation for bounded reconstruction guide and motion windows. On one actual cached calibration-slide original, all four planes and coverage/clipping/support masks were bit-identical to NativeSampler for identity, fractional translation, and scale/rotation placements. The six-resampler numeric/support controls passed separately (5 tests).

| Placement | Full-plane gather ms | Region gather ms | Ratio | Region reserved bytes |
| --- | --- | --- | --- | --- |
| 0 | 24.5175 | 0.3083 | 79.52 | 97600 |
| 1 | 24.4824 | 0.3088 | 79.29 | 98325 |
| 2 | 24.2001 | 0.3113 | 77.74 | 98325 |

Each timing is the mean of two eight-iteration arms in native/region/region/native order, with four CPU workers and reused workspaces. The full-plane workspace reservation was41,280,480bytes; the region workspace was97,600–98,325bytes. Actual original row reads fell from9,376 to224–228 per gather. These are gather preparation measurements only, not full-session timings or photographic-quality evidence. Conditional host-load samples are in the run receipt. One-second process sampling is insufficient for an exact short-run peak-memory claim.

Input: DSC00020.ARW from flat-et2.5s-sw4-cpl, original SHA25609909b486e85617eb6632a4c7eae8ff75afca04432895297d06fae43e3610ace. Full3516×2344quad grid; window[1172,781,80,48]. Black/white levels come from the verified cached original; Catmull-Rom sampler, no optical profile, no RAW decode.

Command actually run:

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/sr-region-benchmark-run-01 --cwd . -- outputs/multi-stack/completion/sr-region-benchmark-build-02/region-sampling-benchmark.exe outputs/multi-stack/completion/hdr-precision-03 outputs/multi-stack/completion/hdr-source-cache-current outputs/multi-stack/completion/sr-region-sampling-benchmark-01.json
```

The executable SHA256 is93fed1074a965e6c2a368a16bafa241807c1a2a51d2174ba5e29f3da86a13ce9. The direct rustc build receipt binds the exact CLI13 default-feature d1b5ff31056b7cf3 library and all dependencies; the failed earlier build against UI12's63ce library remains recorded and was not used for this result.

VERIFIED: `sr-consumer-controls-05` passed12 tests, covering the sampler, exact native final writer fallback, complete source-union subdivision, explicit focus gauge, all-anchor triangle connectivity, and release of broad refused source allocations. No full-scene reconstruction success or optical detail gain is claimed here; those experiments remain required.
