# Literal dual-tree GPU continuation

2026-10-27. Allocation `raw-quality-2026-10-27-dual-tree-cfa-gpu`.
Root alone schedules builds, numerical tests, RAW and vendor jobs.

## Changed question and prior evidence

Can the exact six-direction native-CFA method in
[the fixed CPU design](../dual-tree-cfa/design.md) execute practically on the
available RTX5090, with independently checked CPU/GPU numerical agreement?
This is an execution change, not another filter, source selector or noise model.
CPU build1/screen1 pass mechanics; independent-colour and glint generated quality
failures remain. Full-size source149 cost1 passes the pre-hull nulls but measures
44.696869s/source and10.4336388s finish, projecting13494.7974698s with the fixed
margin; full CPU299 is therefore refused before launch. Peak job commit is
8772075520bytes. No full-stack candidate or photographic gain exists yet.

Prior search actually run: `python scripts/research.py search "dual tree GPU CUDA FIR"`
and `python experiments/ORCH-drift-check/prior_art.py "dual tree GPU CUDA FIR"`
returned no matches in their scope; broader `research.py search --any "dual-tree"
"score-server" "GPU gather"` and `prior_art.py "GPU" "gather"` exposed the existing
GPU work. Read [Device256 results](../../native-gpu-gather/device-results.md),
[M7](../../../docs/research/M7-gpu-focus-measured.md), the existing
`cross-scale-band-guide/score-server.py` transport and
[the current narrow route](../dual-tree-cfa/gpu-route.md).
Device256 is a separately qualified wgpu gather, not CUDA tensor interop.
M7 resident-volume timings cannot predict this complete source/probe workload.
No aligned source volume, learned scorer or RGB reconstruction is imported.

## Owned work and immutable algorithm

- cfa-residual owns `gpu-server.py` and its fixed protocol/API documentation:
  independently written TorchCUDA f32 FIR, packing, weights, accumulation,
  fallback and inverse. No restricted third-party DTCWT source/assets.
- integration-review owns `bridge.rs` and source-only Rust integration with the
  existing full adapter/API. Reuse the frozen full adapter via a new test module
  where feasible; preserve its old source and outputs.
- photo-review owns independent GPU controls and review after finishing CPU
  screen review. Root owns registration, runner, resource dispatch and final
  photographic decision. No agent launches jobs independently.

Original u16 remains in Rust; all signal/probe gathers use the exact held CPU
consumer. Send one gathered four-phase f32 field at a time to one persistent
child. Keep sixteen original-u16 probes, source ordinals/seeds, seven levels,
the published fixed bank, reflection, S5 power smoothing, injected noise and
exponent ladder unchanged. Keep both signal analyses if needed by the fixed
memory strategy; disclose any exact reuse explicitly. Device numerator persists;
no all-source tensors. No f16, autocast, TF32, alternate clipping, reduced probes,
new parameters or implicit CPU fallback. Record runtime/device/source identities,
CUDA synchronization and allocated/reserved high-water marks.

Fixed CPU reference is build1 executable
`a15baca92af120207220ade55fa790a9370a52187f1d6d0c9613fd33e2680957`.
Full source is original299 weevil107, reference149, cropquad34,23,3448,2298,
same map/order/RAW identities and writer in the existing full adapter.
The baseline must reproduce held complete CFA/RGB16/float/material metadata.
The same16-call callback must be counted; keep CPU gather for this allocation.
Any GPU gather extension needs its own explicit qualification and allocation.

## Qualification and bounds

Before RAW, independently freeze bounded generated CPU/GPU comparison controls:
all angular/boundary/phase foils, actual pre-hull singleton and uniform-mean
nulls, multi-source candidate output and meaningful coefficient/floor/weight
agreement. Preserve positive-weight witnesses and all original quality failures.
Numerical thresholds must be declared before results, not tuned to match.
At minimum retain max0.05DN/RMS0.01DN pre-hull reconstruction limits; independently
review any distinct cross-backend coefficient/weight tolerance and its impact.
A wrong one-sided orientation/sign, altered bank and wrong floor scaling must
fail before agreement metrics are relied upon. Tiny canonical band-count
confound and uniform-as-transform-of-mean caveats remain.

Root's generated qualification budget:120s,4CPUthreads,8GiB host,24GiB device.
Before any numerical child, root records an `nvidia-smi` preflight requiring
at least26GiB free on device0 (RTX5090), leaving room beyond the24GiB Torch
allocator cap for runtime overhead. Worker allocator peaks are not total-device
memory measurements. CUDA visibility and deterministic-library environment are
fixed; inherited allocator/TF32 overrides are removed and their key names recorded.
One full-size source149 plus all16probes:300s,4CPUthreads,14GiB host,24GiB device.
Record pipe/copy/gather/probe/synthesis/writer costs; synchronization is included.
Use the same `299*source_phase_seconds+finish_seconds+120<=1200` release gate.
Only a complete mechanically valid source/probe cost permits full299:
1200s,4CPUthreads,14GiB host,24GiB device. No automatic extension on a timeout.
The parent Windows job must own its child; retain artifact completeness and
failure receipts. Device cap is checked during execution as well as reported.

Full299 is a finite photographic observation despite retained generated harms,
not admission. Show complete canonical/candidate output, full-resolution masters,
the existing Helicon workflow comparison and frozen native witnesses. Root and
independent review judge real hairs/scales/boundaries/color; more contrast or
smoothing is insufficient. Any promising result needs another insect and flat
diagnostic before general applicability. No default change or SOTA claim here.
