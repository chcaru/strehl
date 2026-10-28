# Persistent CUDA worker protocol

2026-10-27. Source-only contract; no execution or parity claim. The Rust bridge
owns original u16 sources, the one injected NoiseModel, original ordinal/seed
generation and the exact sixteen CPU gather calls. Python has no RAW loader.

Launch `gpu-server.py --receipt <fresh-json> --device-limit-bytes 25769803776`.
The bridge pins the interpreter and server SHA256. The child inherits the
parent Windows job; no detached service or separate source queue exists.

Each message is u32 little-endian JSON length (1..262144), UTF-8 JSON, followed
by the declared number of little-endian f32 values. Replies use the same
framing, echo op/index/draw where applicable, declare `floats`, and then send
that payload. Every request completes before the next is sent. JSON forbids
NaN/Infinity; all payloads must be finite and correctly shaped. Diagnostics
only go to stderr. Malformed/failed work aborts, never silently falls back.

1. `start`: schema1, width,height (phase extent,1..4096), `wb` containing the
   first three finite positive native WB coefficients, `exponents` containing
   the seven exact CPU f32 values, device_limit_bytes, debug. Optional
   `floor_foil` defaults false and is legal only in bounded debug mode.
   Levels7, gate2, bank, reflection and source limit299 are fixed in code.
   CPU measured exponent bits are
   `[1090519040,1090519040,1089854661,1085250994,1081794887,1077097267,1073741824]`.
   The bridge also supplies pinned cpu_transform_sha256 and
   cpu_consumer_sha256 facts; the worker checks them against the frozen source.
   Return runtime/device/bank settings and geometry; payload0.
2. `source`: index0..298, floats=4*width*height, then phase-major R,G1,G2,B.
   Ordinals must be unique. Worker retains only this current four-phase field,
   computes signal energy, then acknowledges. It analyzes the signal again
   after the probes, preserving the CPU two-analysis policy.
3. Sixteen `probe` messages: same index, draw0..15 in exact order, same payload
   shape. Even draws retain pair-A coefficients; odd draws accumulate the
   pair difference divided by16. Only one gathered probe is resident. Echo
   index/draw and acknowledge each message; no ordinary return payload.
4. `end-source`: same index, no payload. Require all16 probes, apply the fixed
   energy/floor/weights, accumulate complex numerators, mean and actual hull,
   then release this signal/probe state. Return `source_evidence`, including
   source_index, probe_pairs8, probe_draws16, signal_analyses_per_phase2,
   probe_analyses_per_phase16, timing, counts and memory high water.
5. `finish`: caller supplies the exact source_ids census in completed order.
   Return evidence followed by16*width*height f32 values in four arm groups:
   planes4 (InputRange), pre_hull_planes4, uniform_planes4, mean_planes4. Within
   each group, phases are R,G1,G2,B. Uniform is the actual transform/inverse of
   the spatial mean, as in the frozen CPU consumer. Write the terminal receipt
   and exit after sending the complete payload.

Debug is allowed only when both phase dimensions are <=128. It has no full-size
coefficient export. Additional operations:

- `transform`: floats=width*height, optional bank_foil=false, then one plane.
  Return `coefficient_floats`, `low_floats`, `inverse_floats`, `band_shapes`,
  and total floats. Payload is all AC coefficients level-major, directions
  LH+,LH-,HL+,HL-,HH+,HH-, each pixel interleaved real/imaginary; then four LL
  arrays AA,AB,BA,BB; then inverse image. bank_foil=true multiplies only
  first-stage a-low tap3 by1.01 for this operation's forward and inverse. The
  ordinary bank/state is unchanged.
- `inverse`: floats=coefficient_floats+low_floats, then the same AC+LL format.
  Return one inverse image. This exercises supplied one-sided phase/direction
  mutations without redefining the producing inverse.
- Debug `end-source` returns `arrays:[{name,floats}]` and a payload in this
  order: energy, floor, raw_weights (each seven levels/six directions/row-major),
  signal_coefficients_phase0 (AC then four LL). These are the actual producing
  fields. With debugfalse, end-source has floats0. The independent wrong-floor
  foil doubles the actual floor only when debugstart floor_foil=true.
- `close`: no active source; terminal receipt plus acknowledgement, then exit.
  This supports a transform-only session with source_count0.

The terminal status is `COMPLETE_DUAL_TREE_CUDA_WORKER`, with complete=true,
backend=`torch-cuda-f32`, source_count/source_ids, device_limit_bytes,
peak_allocated_bytes and peak_reserved_bytes. Failed sessions use
`FAILED_DUAL_TREE_CUDA_WORKER`, complete=false and retain the reason. A receipt
is never overwritten. Memory accounting covers the Torch CUDA allocator;
the root separately checks host/job and available device memory.

All tensors and arithmetic are f32. Autograd, autocast, f16, TF32 and cuDNN
benchmarking are disabled. Deterministic algorithms are required. Separable
grouped conv2d/conv_transpose2d with explicit periodic extension/folding replace
the CPU per-tap loops; their reduction/FMA order and device log/exp can differ
from CPU. Bank constants, phase convention, smoothing, gate, mean/fallback,
running-scale algebra and hull do not change. No bit-exact cross-backend claim
is made. Independent coefficient/field/output tolerances must be frozen before
the first run. Synchronization brackets measured commands; high-water checks
also occur inside each transform stage.
